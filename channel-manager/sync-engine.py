"""
Channel Manager Sync Engine
===========================

Celery-based bidirectional sync engine for the PMS-Webapp Channel Manager.
Handles outbound sync (PMS-Core -> Channels) and inbound sync (Channels -> PMS-Core).

Technology Stack:
- Celery 5.x with Redis broker
- httpx for async HTTP calls
- Redis Streams for event consumption
- Structured logging with structlog
"""

import asyncio
import json
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from celery import Celery, Task
from celery.schedules import crontab
from pydantic import BaseModel
from sqlalchemy import and_, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

# Import platform adapters
from .platform_adapters.airbnb_adapter import AirbnbAdapter
from .platform_adapters.booking_com_adapter import BookingComAdapter
from .platform_adapters.expedia_adapter import ExpediaAdapter
from .platform_adapters.fewo_direkt_adapter import FeWoDirektAdapter
from .platform_adapters.google_adapter import GoogleVacationRentalsAdapter

# Import local modules (assuming these exist in the project)
from .rate_limiter import ChannelRateLimiter, RateLimitExceeded
from .circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from .models import (
    ChannelConnection,
    ChannelSyncLog,
    Booking,
    Guest,
    CalendarAvailability,
    channel_connections,
    channel_sync_logs,
    bookings,
    guests,
    calendar_availability
)
from .database import get_async_session
from .encryption import TokenManager
from .config import settings

# Configure structured logging
logger = structlog.get_logger(__name__)

# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

celery = Celery(
    "channel_manager",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes
    worker_prefetch_multiplier=1,  # One task at a time for rate limiting
    task_acks_late=True,  # Ack after task completes
    task_reject_on_worker_lost=True,
)

# Celery Beat schedule for periodic tasks
celery.conf.beat_schedule = {
    "refresh-expiring-tokens": {
        "task": "channel_manager.sync_engine.refresh_expiring_tokens",
        "schedule": crontab(minute=0),  # Every hour
    },
    "poll-channel-bookings": {
        "task": "channel_manager.sync_engine.poll_all_channel_bookings",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "daily-reconciliation": {
        "task": "channel_manager.sync_engine.run_daily_reconciliation",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
    "process-event-stream": {
        "task": "channel_manager.sync_engine.process_pms_event_stream",
        "schedule": 10.0,  # Every 10 seconds
    },
}

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SyncType(str, Enum):
    BOOKING_IMPORT = "booking_import"
    BOOKING_EXPORT = "booking_export"
    AVAILABILITY_IMPORT = "availability_import"
    AVAILABILITY_EXPORT = "availability_export"
    PRICE_IMPORT = "price_import"
    PRICE_EXPORT = "price_export"
    CONTENT_SYNC = "content_sync"
    WEBHOOK = "webhook"
    FULL_SYNC = "full_sync"


class SyncDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class SyncStatus(str, Enum):
    STARTED = "started"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    SKIPPED = "skipped"


class ChannelBookingData(BaseModel):
    """Standardized booking data from any channel."""
    channel_booking_id: str
    channel_guest_id: Optional[str] = None
    listing_id: str
    guest_first_name: str
    guest_last_name: str
    guest_email: str
    guest_phone: Optional[str] = None
    check_in: date
    check_out: date
    num_guests: int
    num_adults: int = 1
    num_children: int = 0
    num_infants: int = 0
    total_price: Decimal
    currency: str = "EUR"
    status: str
    booked_at: datetime
    special_requests: Optional[str] = None
    channel_data: Dict[str, Any] = {}


class PMSEvent(BaseModel):
    """Event emitted by PMS-Core."""
    event_type: str
    tenant_id: UUID
    property_id: UUID
    payload: Dict[str, Any]
    timestamp: datetime


# =============================================================================
# ADAPTER FACTORY
# =============================================================================

class AdapterFactory:
    """Factory for creating platform-specific adapters."""

    @staticmethod
    async def create_adapter(connection: ChannelConnection) -> Any:
        """Create an adapter instance for the given connection."""
        token_manager = TokenManager()
        access_token = token_manager.decrypt_token(connection.access_token_encrypted)

        adapters = {
            "airbnb": AirbnbAdapter,
            "booking_com": BookingComAdapter,
            "expedia": ExpediaAdapter,
            "fewo_direkt": FeWoDirektAdapter,
            "google": GoogleVacationRentalsAdapter,
        }

        adapter_class = adapters.get(connection.channel_type)
        if not adapter_class:
            raise ValueError(f"Unknown channel type: {connection.channel_type}")

        return adapter_class(access_token=access_token)


# =============================================================================
# SYNC LOGGING
# =============================================================================

async def log_sync_start(
    connection_id: UUID,
    sync_type: SyncType,
    direction: SyncDirection
) -> UUID:
    """Log the start of a sync operation."""
    async with get_async_session() as session:
        result = await session.execute(
            insert(channel_sync_logs).values(
                channel_connection_id=connection_id,
                sync_type=sync_type.value,
                direction=direction.value,
                status=SyncStatus.STARTED.value,
                started_at=datetime.utcnow()
            ).returning(channel_sync_logs.c.id)
        )
        await session.commit()
        return result.scalar()


async def log_sync_complete(
    log_id: UUID,
    status: SyncStatus,
    records_processed: int = 0,
    records_created: int = 0,
    records_updated: int = 0,
    records_failed: int = 0,
    records_skipped: int = 0,
    error_message: Optional[str] = None,
    error_details: Optional[Dict] = None,
    request_data: Optional[Dict] = None,
    response_data: Optional[Dict] = None
) -> None:
    """Log the completion of a sync operation."""
    async with get_async_session() as session:
        started_at = await session.execute(
            select(channel_sync_logs.c.started_at).where(channel_sync_logs.c.id == log_id)
        )
        started_at = started_at.scalar()
        duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000) if started_at else None

        await session.execute(
            update(channel_sync_logs)
            .where(channel_sync_logs.c.id == log_id)
            .values(
                status=status.value,
                records_processed=records_processed,
                records_created=records_created,
                records_updated=records_updated,
                records_failed=records_failed,
                records_skipped=records_skipped,
                error_message=error_message,
                error_details=error_details,
                request_data=request_data,
                response_data=response_data,
                completed_at=datetime.utcnow(),
                duration_ms=duration_ms
            )
        )
        await session.commit()


# =============================================================================
# OUTBOUND SYNC (PMS-Core -> Channels)
# =============================================================================

@celery.task(bind=True, max_retries=5)
def handle_booking_confirmed_event(self, event_data: dict) -> dict:
    """
    Handle booking.confirmed event from PMS-Core.
    Block dates on ALL connected channels for the property.
    """
    return asyncio.get_event_loop().run_until_complete(
        _handle_booking_confirmed_event(self, event_data)
    )


async def _handle_booking_confirmed_event(task: Task, event_data: dict) -> dict:
    """Async implementation of booking confirmed handler."""
    event = PMSEvent(**event_data)
    logger.info(
        "Processing booking.confirmed event",
        property_id=str(event.property_id),
        booking_id=event.payload.get("booking_id")
    )

    # Get all active channel connections for this property
    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(
                and_(
                    channel_connections.c.property_id == event.property_id,
                    channel_connections.c.sync_enabled == True,
                    channel_connections.c.status == "active",
                    channel_connections.c.sync_availability == True,
                    channel_connections.c.sync_direction.in_(["bidirectional", "outbound_only"])
                )
            )
        )
        connections = result.fetchall()

    # Skip if booking is from a channel (to avoid double-update)
    source_channel = event.payload.get("source")

    results = {"success": [], "failed": [], "skipped": []}

    for conn in connections:
        # Skip the source channel (it already knows about this booking)
        if source_channel and conn.channel_type == source_channel:
            results["skipped"].append({
                "channel": conn.channel_type,
                "reason": "source_channel"
            })
            continue

        # Queue availability update for each channel
        try:
            update_channel_availability.delay(
                connection_id=str(conn.id),
                check_in=event.payload["check_in"],
                check_out=event.payload["check_out"],
                available=False
            )
            results["success"].append(conn.channel_type)
        except Exception as e:
            results["failed"].append({
                "channel": conn.channel_type,
                "error": str(e)
            })

    return results


@celery.task(bind=True, max_retries=5)
def handle_booking_cancelled_event(self, event_data: dict) -> dict:
    """
    Handle booking.cancelled event from PMS-Core.
    Unblock dates on ALL connected channels for the property.
    """
    return asyncio.get_event_loop().run_until_complete(
        _handle_booking_cancelled_event(self, event_data)
    )


async def _handle_booking_cancelled_event(task: Task, event_data: dict) -> dict:
    """Async implementation of booking cancelled handler."""
    event = PMSEvent(**event_data)
    logger.info(
        "Processing booking.cancelled event",
        property_id=str(event.property_id),
        booking_id=event.payload.get("booking_id")
    )

    # Get all active channel connections for this property
    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(
                and_(
                    channel_connections.c.property_id == event.property_id,
                    channel_connections.c.sync_enabled == True,
                    channel_connections.c.status == "active",
                    channel_connections.c.sync_availability == True,
                    channel_connections.c.sync_direction.in_(["bidirectional", "outbound_only"])
                )
            )
        )
        connections = result.fetchall()

    results = {"success": [], "failed": [], "skipped": []}

    for conn in connections:
        try:
            update_channel_availability.delay(
                connection_id=str(conn.id),
                check_in=event.payload["check_in"],
                check_out=event.payload["check_out"],
                available=True  # Unblock dates
            )
            results["success"].append(conn.channel_type)
        except Exception as e:
            results["failed"].append({
                "channel": conn.channel_type,
                "error": str(e)
            })

    return results


@celery.task(bind=True, max_retries=5)
def handle_availability_updated_event(self, event_data: dict) -> dict:
    """
    Handle availability.updated event from PMS-Core.
    Sync availability changes to all connected channels.
    """
    return asyncio.get_event_loop().run_until_complete(
        _handle_availability_updated_event(self, event_data)
    )


async def _handle_availability_updated_event(task: Task, event_data: dict) -> dict:
    """Async implementation of availability update handler."""
    event = PMSEvent(**event_data)

    # Get all active channel connections
    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(
                and_(
                    channel_connections.c.property_id == event.property_id,
                    channel_connections.c.sync_enabled == True,
                    channel_connections.c.status == "active",
                    channel_connections.c.sync_availability == True,
                    channel_connections.c.sync_direction.in_(["bidirectional", "outbound_only"])
                )
            )
        )
        connections = result.fetchall()

    results = {"success": [], "failed": []}

    for conn in connections:
        try:
            update_channel_availability.delay(
                connection_id=str(conn.id),
                check_in=event.payload["start_date"],
                check_out=event.payload["end_date"],
                available=event.payload["available"]
            )
            results["success"].append(conn.channel_type)
        except Exception as e:
            results["failed"].append({
                "channel": conn.channel_type,
                "error": str(e)
            })

    return results


@celery.task(bind=True, max_retries=5)
def handle_pricing_updated_event(self, event_data: dict) -> dict:
    """
    Handle pricing.updated event from PMS-Core.
    Sync pricing changes to all connected channels.
    """
    return asyncio.get_event_loop().run_until_complete(
        _handle_pricing_updated_event(self, event_data)
    )


async def _handle_pricing_updated_event(task: Task, event_data: dict) -> dict:
    """Async implementation of pricing update handler."""
    event = PMSEvent(**event_data)

    # Get all active channel connections
    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(
                and_(
                    channel_connections.c.property_id == event.property_id,
                    channel_connections.c.sync_enabled == True,
                    channel_connections.c.status == "active",
                    channel_connections.c.sync_pricing == True,
                    channel_connections.c.sync_direction.in_(["bidirectional", "outbound_only"])
                )
            )
        )
        connections = result.fetchall()

    results = {"success": [], "failed": []}

    for conn in connections:
        try:
            update_channel_pricing.delay(
                connection_id=str(conn.id),
                date_prices=event.payload["date_prices"]  # Dict[date_str, Decimal]
            )
            results["success"].append(conn.channel_type)
        except Exception as e:
            results["failed"].append({
                "channel": conn.channel_type,
                "error": str(e)
            })

    return results


@celery.task(bind=True, max_retries=5, default_retry_delay=2)
def update_channel_availability(
    self,
    connection_id: str,
    check_in: str,
    check_out: str,
    available: bool
) -> dict:
    """
    Update availability on a specific channel.
    Includes rate limiting and circuit breaker protection.
    """
    return asyncio.get_event_loop().run_until_complete(
        _update_channel_availability(self, connection_id, check_in, check_out, available)
    )


async def _update_channel_availability(
    task: Task,
    connection_id: str,
    check_in: str,
    check_out: str,
    available: bool
) -> dict:
    """Async implementation of channel availability update."""
    connection_uuid = UUID(connection_id)

    # Get connection details
    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(channel_connections.c.id == connection_uuid)
        )
        conn = result.first()

    if not conn:
        logger.error("Channel connection not found", connection_id=connection_id)
        return {"status": "error", "message": "Connection not found"}

    # Start sync log
    log_id = await log_sync_start(
        connection_uuid,
        SyncType.AVAILABILITY_EXPORT,
        SyncDirection.OUTBOUND
    )

    # Rate limiting
    rate_limiter = ChannelRateLimiter()
    circuit_breaker = CircuitBreaker(channel_type=conn.channel_type)

    try:
        # Check rate limit
        if not await rate_limiter.acquire(conn.channel_type, connection_id):
            logger.warning(
                "Rate limit exceeded",
                channel=conn.channel_type,
                connection_id=connection_id
            )
            # Retry with backoff
            raise task.retry(
                exc=RateLimitExceeded(conn.channel_type),
                countdown=calculate_retry_delay(task.request.retries)
            )

        # Check circuit breaker
        if not await circuit_breaker.can_execute():
            logger.warning(
                "Circuit breaker open",
                channel=conn.channel_type
            )
            await log_sync_complete(
                log_id,
                SyncStatus.SKIPPED,
                error_message="Circuit breaker is OPEN"
            )
            return {"status": "skipped", "reason": "circuit_breaker_open"}

        # Create adapter and update availability
        adapter = await AdapterFactory.create_adapter(conn)

        await adapter.update_availability(
            property_id=conn.channel_property_id,
            start_date=date.fromisoformat(check_in),
            end_date=date.fromisoformat(check_out),
            available=available
        )

        # Record success
        await circuit_breaker.record_success()
        await log_sync_complete(
            log_id,
            SyncStatus.SUCCESS,
            records_processed=1,
            records_updated=1
        )

        # Update last_sync_at
        async with get_async_session() as session:
            await session.execute(
                update(channel_connections)
                .where(channel_connections.c.id == connection_uuid)
                .values(
                    last_sync_at=datetime.utcnow(),
                    last_successful_sync_at=datetime.utcnow()
                )
            )
            await session.commit()

        logger.info(
            "Availability updated successfully",
            channel=conn.channel_type,
            property_id=conn.channel_property_id,
            check_in=check_in,
            check_out=check_out,
            available=available
        )

        return {"status": "success"}

    except RateLimitExceeded:
        raise

    except CircuitBreakerOpen as e:
        await log_sync_complete(
            log_id,
            SyncStatus.SKIPPED,
            error_message=str(e)
        )
        return {"status": "skipped", "reason": "circuit_breaker_open"}

    except Exception as e:
        await circuit_breaker.record_failure()
        await log_sync_complete(
            log_id,
            SyncStatus.FAILURE,
            error_message=str(e),
            error_details={"exception": type(e).__name__}
        )

        # Update error count
        async with get_async_session() as session:
            await session.execute(
                update(channel_connections)
                .where(channel_connections.c.id == connection_uuid)
                .values(
                    error_count=channel_connections.c.error_count + 1,
                    last_error_at=datetime.utcnow(),
                    error_message=str(e)
                )
            )
            await session.commit()

        logger.error(
            "Failed to update availability",
            channel=conn.channel_type,
            error=str(e),
            retries=task.request.retries
        )

        # Retry with exponential backoff
        raise task.retry(
            exc=e,
            countdown=calculate_retry_delay(task.request.retries)
        )


@celery.task(bind=True, max_retries=5, default_retry_delay=2)
def update_channel_pricing(
    self,
    connection_id: str,
    date_prices: dict  # {date_str: price}
) -> dict:
    """
    Update pricing on a specific channel.
    """
    return asyncio.get_event_loop().run_until_complete(
        _update_channel_pricing(self, connection_id, date_prices)
    )


async def _update_channel_pricing(
    task: Task,
    connection_id: str,
    date_prices: dict
) -> dict:
    """Async implementation of channel pricing update."""
    connection_uuid = UUID(connection_id)

    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(channel_connections.c.id == connection_uuid)
        )
        conn = result.first()

    if not conn:
        return {"status": "error", "message": "Connection not found"}

    log_id = await log_sync_start(
        connection_uuid,
        SyncType.PRICE_EXPORT,
        SyncDirection.OUTBOUND
    )

    rate_limiter = ChannelRateLimiter()
    circuit_breaker = CircuitBreaker(channel_type=conn.channel_type)

    try:
        if not await rate_limiter.acquire(conn.channel_type, connection_id):
            raise task.retry(
                exc=RateLimitExceeded(conn.channel_type),
                countdown=calculate_retry_delay(task.request.retries)
            )

        if not await circuit_breaker.can_execute():
            await log_sync_complete(log_id, SyncStatus.SKIPPED, error_message="Circuit breaker OPEN")
            return {"status": "skipped", "reason": "circuit_breaker_open"}

        adapter = await AdapterFactory.create_adapter(conn)

        # Apply channel-specific price adjustments if configured
        adjusted_prices = apply_price_adjustments(
            date_prices,
            conn.price_adjustment_type,
            conn.price_adjustment_value
        )

        for date_str, price in adjusted_prices.items():
            await adapter.update_pricing(
                property_id=conn.channel_property_id,
                date=date.fromisoformat(date_str),
                price=Decimal(str(price))
            )

        await circuit_breaker.record_success()
        await log_sync_complete(
            log_id,
            SyncStatus.SUCCESS,
            records_processed=len(date_prices),
            records_updated=len(date_prices)
        )

        return {"status": "success", "records_updated": len(date_prices)}

    except Exception as e:
        await circuit_breaker.record_failure()
        await log_sync_complete(log_id, SyncStatus.FAILURE, error_message=str(e))
        raise task.retry(exc=e, countdown=calculate_retry_delay(task.request.retries))


def apply_price_adjustments(
    date_prices: dict,
    adjustment_type: Optional[str],
    adjustment_value: Optional[Decimal]
) -> dict:
    """Apply channel-specific price adjustments."""
    if not adjustment_type or not adjustment_value:
        return date_prices

    adjusted = {}
    for date_str, price in date_prices.items():
        price = Decimal(str(price))
        if adjustment_type == "percentage":
            # e.g., +10% for Airbnb
            adjusted[date_str] = price * (1 + adjustment_value / 100)
        elif adjustment_type == "fixed_amount":
            # e.g., +$10 per night
            adjusted[date_str] = price + adjustment_value
        else:
            adjusted[date_str] = price
    return adjusted


def calculate_retry_delay(retries: int) -> float:
    """Calculate exponential backoff with jitter."""
    base_delays = [2, 4, 8, 16, 32]
    base = base_delays[min(retries, len(base_delays) - 1)]
    jitter = random.uniform(0, base / 2)
    return base + jitter


# =============================================================================
# INBOUND SYNC (Channels -> PMS-Core)
# =============================================================================

@celery.task(bind=True, max_retries=3)
def import_channel_booking(
    self,
    channel_type: str,
    connection_id: str,
    booking_data: dict,
    idempotency_key: str
) -> dict:
    """
    Import a booking from a channel into PMS-Core.
    This task is idempotent - duplicate imports are safely ignored.
    """
    return asyncio.get_event_loop().run_until_complete(
        _import_channel_booking(self, channel_type, connection_id, booking_data, idempotency_key)
    )


async def _import_channel_booking(
    task: Task,
    channel_type: str,
    connection_id: str,
    booking_data: dict,
    idempotency_key: str
) -> dict:
    """Async implementation of channel booking import."""
    redis = await aioredis.from_url(settings.REDIS_URL)
    connection_uuid = UUID(connection_id)

    # Check idempotency
    if await redis.exists(f"imported:{idempotency_key}"):
        logger.info(
            "Booking already imported",
            idempotency_key=idempotency_key
        )
        return {"status": "already_imported"}

    # Get connection
    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(channel_connections.c.id == connection_uuid)
        )
        conn = result.first()

    if not conn:
        return {"status": "error", "message": "Connection not found"}

    log_id = await log_sync_start(
        connection_uuid,
        SyncType.BOOKING_IMPORT,
        SyncDirection.INBOUND
    )

    try:
        # Map channel data to PMS schema
        channel_booking = ChannelBookingData(**booking_data)

        # Create or get guest
        guest_id = await create_or_get_guest(
            tenant_id=conn.tenant_id,
            first_name=channel_booking.guest_first_name,
            last_name=channel_booking.guest_last_name,
            email=channel_booking.guest_email,
            phone=channel_booking.guest_phone,
            source=channel_type
        )

        # Create booking in PMS-Core
        async with get_async_session() as session:
            try:
                result = await session.execute(
                    insert(bookings).values(
                        tenant_id=conn.tenant_id,
                        property_id=conn.property_id,
                        guest_id=guest_id,
                        source=channel_type,
                        channel_booking_id=channel_booking.channel_booking_id,
                        channel_guest_id=channel_booking.channel_guest_id,
                        check_in=channel_booking.check_in,
                        check_out=channel_booking.check_out,
                        num_adults=channel_booking.num_adults,
                        num_children=channel_booking.num_children,
                        num_infants=channel_booking.num_infants,
                        nightly_rate=channel_booking.total_price / (channel_booking.check_out - channel_booking.check_in).days,
                        subtotal=channel_booking.total_price,
                        total_price=channel_booking.total_price,
                        currency=channel_booking.currency,
                        status=map_channel_status_to_pms(channel_type, channel_booking.status),
                        payment_status="external",  # Channel handles payment
                        special_requests=channel_booking.special_requests,
                        channel_data=channel_booking.channel_data,
                        confirmed_at=datetime.utcnow() if channel_booking.status in ["confirmed", "accepted"] else None
                    ).returning(bookings.c.id)
                )
                await session.commit()
                new_booking_id = result.scalar()

                logger.info(
                    "Booking imported successfully",
                    booking_id=str(new_booking_id),
                    channel=channel_type,
                    channel_booking_id=channel_booking.channel_booking_id
                )

                # Mark as imported
                await redis.setex(f"imported:{idempotency_key}", 86400, "done")

                await log_sync_complete(
                    log_id,
                    SyncStatus.SUCCESS,
                    records_processed=1,
                    records_created=1
                )

                # Fan-out: Sync to OTHER channels (not the source)
                sync_to_other_channels.delay(
                    booking_id=str(new_booking_id),
                    property_id=str(conn.property_id),
                    exclude_channel=channel_type
                )

                return {
                    "status": "success",
                    "booking_id": str(new_booking_id)
                }

            except IntegrityError as e:
                await session.rollback()
                # Duplicate prevented by UNIQUE(source, channel_booking_id)
                logger.info(
                    "Duplicate booking prevented by DB constraint",
                    channel_booking_id=channel_booking.channel_booking_id
                )
                await log_sync_complete(
                    log_id,
                    SyncStatus.SKIPPED,
                    records_skipped=1,
                    error_message="Duplicate booking"
                )
                return {"status": "duplicate"}

    except Exception as e:
        logger.error(
            "Failed to import booking",
            error=str(e),
            channel=channel_type
        )
        await log_sync_complete(
            log_id,
            SyncStatus.FAILURE,
            error_message=str(e)
        )
        raise task.retry(exc=e, countdown=calculate_retry_delay(task.request.retries))


@celery.task
def sync_to_other_channels(
    booking_id: str,
    property_id: str,
    exclude_channel: str
) -> dict:
    """
    After importing a booking from one channel, sync availability
    to all OTHER connected channels for the same property.
    """
    return asyncio.get_event_loop().run_until_complete(
        _sync_to_other_channels(booking_id, property_id, exclude_channel)
    )


async def _sync_to_other_channels(
    booking_id: str,
    property_id: str,
    exclude_channel: str
) -> dict:
    """Async implementation of cross-channel sync."""
    property_uuid = UUID(property_id)

    # Get booking details
    async with get_async_session() as session:
        result = await session.execute(
            select(bookings).where(bookings.c.id == UUID(booking_id))
        )
        booking = result.first()

        # Get other channel connections
        result = await session.execute(
            select(channel_connections).where(
                and_(
                    channel_connections.c.property_id == property_uuid,
                    channel_connections.c.channel_type != exclude_channel,
                    channel_connections.c.sync_enabled == True,
                    channel_connections.c.status == "active",
                    channel_connections.c.sync_availability == True,
                    channel_connections.c.sync_direction.in_(["bidirectional", "outbound_only"])
                )
            )
        )
        connections = result.fetchall()

    results = {"success": [], "failed": []}

    for conn in connections:
        try:
            update_channel_availability.delay(
                connection_id=str(conn.id),
                check_in=booking.check_in.isoformat(),
                check_out=booking.check_out.isoformat(),
                available=False
            )
            results["success"].append(conn.channel_type)
        except Exception as e:
            results["failed"].append({
                "channel": conn.channel_type,
                "error": str(e)
            })

    return results


async def create_or_get_guest(
    tenant_id: UUID,
    first_name: str,
    last_name: str,
    email: str,
    phone: Optional[str],
    source: str
) -> UUID:
    """Create a new guest or return existing guest ID."""
    async with get_async_session() as session:
        # Try to find existing guest by email (within tenant)
        result = await session.execute(
            select(guests.c.id).where(
                and_(
                    guests.c.tenant_id == tenant_id,
                    guests.c.email == email
                )
            )
        )
        existing = result.first()

        if existing:
            return existing.id

        # Create new guest
        result = await session.execute(
            insert(guests).values(
                tenant_id=tenant_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                source=source
            ).returning(guests.c.id)
        )
        await session.commit()
        return result.scalar()


def map_channel_status_to_pms(channel_type: str, channel_status: str) -> str:
    """Map channel-specific status to PMS booking status."""
    status_maps = {
        "airbnb": {
            "pending": "pending",
            "accepted": "confirmed",
            "denied": "declined",
            "cancelled": "cancelled",
            "cancelled_by_host": "cancelled",
            "cancelled_by_guest": "cancelled"
        },
        "booking_com": {
            "new": "pending",
            "modified": "confirmed",
            "cancelled": "cancelled",
            "no_show": "no_show"
        },
        "expedia": {
            "PENDING": "pending",
            "CONFIRMED": "confirmed",
            "CANCELLED": "cancelled",
            "COMPLETED": "checked_out"
        },
        "fewo_direkt": {
            "booked": "confirmed",
            "tentative": "pending",
            "cancelled": "cancelled"
        },
        "google": {
            "CONFIRMED": "confirmed",
            "CANCELLED": "cancelled"
        }
    }

    channel_map = status_maps.get(channel_type, {})
    return channel_map.get(channel_status, "pending")


# =============================================================================
# POLLING (Fallback for Unreliable Webhooks)
# =============================================================================

@celery.task
def poll_all_channel_bookings() -> dict:
    """
    Poll all channels for new/updated bookings.
    Runs every 5 minutes as a fallback when webhooks fail.
    """
    return asyncio.get_event_loop().run_until_complete(
        _poll_all_channel_bookings()
    )


async def _poll_all_channel_bookings() -> dict:
    """Async implementation of polling all channels."""
    # Get all active connections that haven't synced recently
    cutoff_time = datetime.utcnow() - timedelta(minutes=5)

    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(
                and_(
                    channel_connections.c.sync_enabled == True,
                    channel_connections.c.status == "active",
                    channel_connections.c.sync_bookings == True,
                    channel_connections.c.sync_direction.in_(["bidirectional", "inbound_only"]),
                    (
                        (channel_connections.c.last_sync_at < cutoff_time) |
                        (channel_connections.c.last_sync_at.is_(None))
                    )
                )
            )
        )
        connections = result.fetchall()

    results = {"queued": [], "skipped": []}

    for conn in connections:
        poll_single_channel.delay(str(conn.id))
        results["queued"].append({
            "connection_id": str(conn.id),
            "channel": conn.channel_type
        })

    return results


@celery.task(bind=True, max_retries=3)
def poll_single_channel(self, connection_id: str) -> dict:
    """Poll a single channel for new bookings."""
    return asyncio.get_event_loop().run_until_complete(
        _poll_single_channel(self, connection_id)
    )


async def _poll_single_channel(task: Task, connection_id: str) -> dict:
    """Async implementation of single channel polling."""
    connection_uuid = UUID(connection_id)

    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(channel_connections.c.id == connection_uuid)
        )
        conn = result.first()

    if not conn:
        return {"status": "error", "message": "Connection not found"}

    rate_limiter = ChannelRateLimiter()
    circuit_breaker = CircuitBreaker(channel_type=conn.channel_type)

    try:
        if not await rate_limiter.acquire(conn.channel_type, connection_id):
            raise task.retry(
                exc=RateLimitExceeded(conn.channel_type),
                countdown=calculate_retry_delay(task.request.retries)
            )

        if not await circuit_breaker.can_execute():
            return {"status": "skipped", "reason": "circuit_breaker_open"}

        adapter = await AdapterFactory.create_adapter(conn)

        # Fetch bookings since last sync
        since = conn.last_sync_at or (datetime.utcnow() - timedelta(days=30))
        channel_bookings = await adapter.get_bookings(
            property_id=conn.channel_property_id,
            since=since
        )

        await circuit_breaker.record_success()

        # Queue import for each booking
        imported = 0
        for booking in channel_bookings:
            idempotency_key = f"{conn.channel_type}:{booking['channel_booking_id']}:{booking.get('updated_at', '')}"

            import_channel_booking.delay(
                channel_type=conn.channel_type,
                connection_id=connection_id,
                booking_data=booking,
                idempotency_key=idempotency_key
            )
            imported += 1

        # Update last_sync_at
        async with get_async_session() as session:
            await session.execute(
                update(channel_connections)
                .where(channel_connections.c.id == connection_uuid)
                .values(last_sync_at=datetime.utcnow())
            )
            await session.commit()

        return {
            "status": "success",
            "bookings_found": len(channel_bookings),
            "queued_for_import": imported
        }

    except Exception as e:
        await circuit_breaker.record_failure()
        logger.error(
            "Polling failed",
            channel=conn.channel_type,
            error=str(e)
        )
        raise task.retry(exc=e, countdown=calculate_retry_delay(task.request.retries))


# =============================================================================
# EVENT STREAM PROCESSOR
# =============================================================================

@celery.task
def process_pms_event_stream() -> dict:
    """
    Consume events from Redis Stream and route to appropriate handlers.
    This is a recurring task that processes batches of events.
    """
    return asyncio.get_event_loop().run_until_complete(
        _process_pms_event_stream()
    )


async def _process_pms_event_stream() -> dict:
    """Async implementation of event stream processing."""
    redis = await aioredis.from_url(settings.REDIS_URL)

    # Consumer group setup (once)
    try:
        await redis.xgroup_create(
            "pms:events",
            "channel_manager",
            id="0",
            mkstream=True
        )
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    # Read pending events (for recovery) + new events
    events = await redis.xreadgroup(
        groupname="channel_manager",
        consumername=f"worker-{settings.WORKER_ID}",
        streams={"pms:events": ">"},  # > means only new messages
        count=10,
        block=1000  # 1 second block
    )

    processed = 0

    for stream, messages in events:
        for message_id, data in messages:
            try:
                event_type = data.get(b"type", b"").decode()
                payload = json.loads(data.get(b"payload", b"{}").decode())
                tenant_id = data.get(b"tenant_id", b"").decode()

                event_data = {
                    "event_type": event_type,
                    "tenant_id": tenant_id,
                    "property_id": payload.get("property_id"),
                    "payload": payload,
                    "timestamp": data.get(b"timestamp", b"").decode()
                }

                # Route to handler
                await route_event(event_type, event_data)

                # Acknowledge message
                await redis.xack("pms:events", "channel_manager", message_id)
                processed += 1

            except Exception as e:
                logger.error(
                    "Failed to process event",
                    message_id=message_id,
                    error=str(e)
                )
                # Message will be retried via pending entries recovery

    return {"processed": processed}


async def route_event(event_type: str, event_data: dict) -> None:
    """Route event to appropriate Celery task."""
    handlers = {
        "booking.confirmed": handle_booking_confirmed_event,
        "booking.cancelled": handle_booking_cancelled_event,
        "availability.updated": handle_availability_updated_event,
        "pricing.updated": handle_pricing_updated_event,
    }

    handler = handlers.get(event_type)
    if handler:
        handler.delay(event_data)
    else:
        logger.warning(f"No handler for event type: {event_type}")


# =============================================================================
# DAILY RECONCILIATION
# =============================================================================

@celery.task
def run_daily_reconciliation() -> dict:
    """
    Daily job to detect and fix sync drift between PMS-Core and channels.
    Runs at 2 AM in tenant timezone.
    """
    return asyncio.get_event_loop().run_until_complete(
        _run_daily_reconciliation()
    )


async def _run_daily_reconciliation() -> dict:
    """Async implementation of daily reconciliation."""
    # Get all active connections
    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(
                and_(
                    channel_connections.c.sync_enabled == True,
                    channel_connections.c.status == "active"
                )
            )
        )
        connections = result.fetchall()

    results = {"reconciled": [], "mismatches": [], "errors": []}

    for conn in connections:
        try:
            mismatch = await reconcile_single_connection(conn)
            if mismatch:
                results["mismatches"].append(mismatch)
            else:
                results["reconciled"].append(str(conn.id))
        except Exception as e:
            results["errors"].append({
                "connection_id": str(conn.id),
                "error": str(e)
            })

    return results


async def reconcile_single_connection(conn) -> Optional[dict]:
    """Reconcile a single channel connection."""
    adapter = await AdapterFactory.create_adapter(conn)

    # Fetch channel availability (next 90 days)
    start_date = date.today()
    end_date = start_date + timedelta(days=90)

    channel_availability = await adapter.get_availability(
        property_id=conn.channel_property_id,
        start_date=start_date,
        end_date=end_date
    )

    # Fetch PMS availability
    async with get_async_session() as session:
        result = await session.execute(
            select(calendar_availability).where(
                and_(
                    calendar_availability.c.property_id == conn.property_id,
                    calendar_availability.c.date >= start_date,
                    calendar_availability.c.date <= end_date
                )
            )
        )
        pms_availability = {
            row.date: row.available
            for row in result.fetchall()
        }

    # Compare and detect mismatches
    mismatches = []
    for cal_date, channel_available in channel_availability.items():
        pms_available = pms_availability.get(cal_date, True)
        if channel_available != pms_available:
            mismatches.append({
                "date": cal_date.isoformat(),
                "channel_available": channel_available,
                "pms_available": pms_available
            })

    if mismatches:
        # Log the drift
        logger.warning(
            "Availability drift detected",
            connection_id=str(conn.id),
            channel=conn.channel_type,
            mismatch_count=len(mismatches)
        )

        # Auto-correct (PMS is source of truth)
        for mismatch in mismatches:
            update_channel_availability.delay(
                connection_id=str(conn.id),
                check_in=mismatch["date"],
                check_out=(date.fromisoformat(mismatch["date"]) + timedelta(days=1)).isoformat(),
                available=mismatch["pms_available"]
            )

        return {
            "connection_id": str(conn.id),
            "channel": conn.channel_type,
            "mismatches": mismatches
        }

    return None


# =============================================================================
# TOKEN REFRESH
# =============================================================================

@celery.task
def refresh_expiring_tokens() -> dict:
    """
    Refresh OAuth tokens that are expiring within 7 days.
    """
    return asyncio.get_event_loop().run_until_complete(
        _refresh_expiring_tokens()
    )


async def _refresh_expiring_tokens() -> dict:
    """Async implementation of token refresh."""
    expiry_threshold = datetime.utcnow() + timedelta(days=7)

    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(
                and_(
                    channel_connections.c.token_expires_at < expiry_threshold,
                    channel_connections.c.status == "active",
                    channel_connections.c.refresh_token_encrypted.isnot(None)
                )
            )
        )
        connections = result.fetchall()

    results = {"refreshed": [], "failed": []}

    for conn in connections:
        try:
            await refresh_connection_token(conn)
            results["refreshed"].append(str(conn.id))
        except Exception as e:
            results["failed"].append({
                "connection_id": str(conn.id),
                "error": str(e)
            })
            # Mark as expired after multiple failures
            if conn.error_count >= 3:
                async with get_async_session() as session:
                    await session.execute(
                        update(channel_connections)
                        .where(channel_connections.c.id == conn.id)
                        .values(status="expired")
                    )
                    await session.commit()

    return results


async def refresh_connection_token(conn) -> None:
    """Refresh OAuth token for a connection."""
    from .oauth_flows import refresh_token_for_channel

    token_manager = TokenManager()
    refresh_token = token_manager.decrypt_token(conn.refresh_token_encrypted)

    new_tokens = await refresh_token_for_channel(
        channel_type=conn.channel_type,
        refresh_token=refresh_token
    )

    expires_at = datetime.utcnow() + timedelta(seconds=new_tokens["expires_in"])

    await token_manager.save_tokens(
        connection_id=conn.id,
        access_token=new_tokens["access_token"],
        refresh_token=new_tokens.get("refresh_token", refresh_token),
        expires_at=expires_at
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def generate_idempotency_key(channel_type: str, payload: dict) -> str:
    """Generate a unique idempotency key for a webhook payload."""
    import hashlib

    # Use channel-specific unique identifiers
    unique_parts = [
        channel_type,
        payload.get("reservation_id", ""),
        payload.get("booking_id", ""),
        payload.get("updated_at", ""),
        payload.get("event_id", "")
    ]

    key_string = ":".join(filter(None, unique_parts))
    return hashlib.sha256(key_string.encode()).hexdigest()[:32]
