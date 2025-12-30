"""
Webhook Handlers
================

FastAPI endpoints for receiving webhooks from all integrated booking platforms.
Handles signature verification, idempotent processing, and event routing.

Endpoints:
- POST /api/v1/webhooks/airbnb
- POST /api/v1/webhooks/booking_com
- POST /api/v1/webhooks/expedia
- POST /api/v1/webhooks/fewo_direkt
- POST /api/v1/webhooks/google
"""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Header, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from pydantic import BaseModel

from .platform_adapters.airbnb_adapter import AirbnbAdapter
from .platform_adapters.booking_com_adapter import BookingComAdapter
from .platform_adapters.expedia_adapter import ExpediaAdapter
from .platform_adapters.fewo_direkt_adapter import FeWoDirektAdapter
from .platform_adapters.google_adapter import GoogleVacationRentalsAdapter
from .sync_engine import import_channel_booking, generate_idempotency_key
from .config import settings

logger = structlog.get_logger(__name__)

# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

WEBHOOK_RECEIVED = Counter(
    "channel_webhook_received_total",
    "Total webhooks received",
    ["channel_type", "event_type"]
)

WEBHOOK_PROCESSED = Counter(
    "channel_webhook_processed_total",
    "Total webhooks processed",
    ["channel_type", "status"]  # status: success, duplicate, error
)

WEBHOOK_LATENCY = Histogram(
    "channel_webhook_processing_seconds",
    "Webhook processing latency",
    ["channel_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# =============================================================================
# ROUTER SETUP
# =============================================================================

router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["Channel Webhooks"]
)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class WebhookResponse(BaseModel):
    status: str
    message: Optional[str] = None
    event_id: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def get_redis() -> aioredis.Redis:
    """Get Redis client."""
    return await aioredis.from_url(settings.REDIS_URL)


async def is_already_processed(idempotency_key: str) -> bool:
    """Check if webhook has already been processed."""
    redis = await get_redis()
    return await redis.exists(f"webhook:{idempotency_key}")


async def mark_as_processed(idempotency_key: str, ttl: int = 86400) -> None:
    """Mark webhook as processed with TTL."""
    redis = await get_redis()
    await redis.setex(f"webhook:{idempotency_key}", ttl, "processed")


async def get_connection_by_channel_property(
    channel_type: str,
    channel_property_id: str
) -> Optional[dict]:
    """Get channel connection by platform property ID."""
    from .database import get_async_session
    from .models import channel_connections
    from sqlalchemy import select, and_

    async with get_async_session() as session:
        result = await session.execute(
            select(channel_connections).where(
                and_(
                    channel_connections.c.channel_type == channel_type,
                    channel_connections.c.channel_property_id == channel_property_id,
                    channel_connections.c.status == "active"
                )
            )
        )
        return result.first()


def verify_hmac_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256"
) -> bool:
    """Verify HMAC signature."""
    if algorithm == "sha256":
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
    elif algorithm == "sha1":
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha1
        ).hexdigest()
    else:
        return False

    return hmac.compare_digest(expected, signature)


# =============================================================================
# AIRBNB WEBHOOK
# =============================================================================

@router.post("/airbnb", response_model=WebhookResponse)
async def airbnb_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_airbnb_signature: str = Header(None, alias="X-Airbnb-Signature")
):
    """
    Handle Airbnb webhook notifications.

    Events:
    - reservation.created
    - reservation.updated
    - reservation.cancelled
    """
    start_time = datetime.utcnow()

    # Read payload
    payload = await request.body()

    # Verify signature
    if x_airbnb_signature:
        if not verify_hmac_signature(
            payload,
            x_airbnb_signature,
            settings.AIRBNB_WEBHOOK_SECRET
        ):
            logger.warning("Invalid Airbnb webhook signature")
            WEBHOOK_PROCESSED.labels(
                channel_type="airbnb",
                status="invalid_signature"
            ).inc()
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = data.get("event_type", "unknown")
    WEBHOOK_RECEIVED.labels(
        channel_type="airbnb",
        event_type=event_type
    ).inc()

    # Generate idempotency key
    idempotency_key = generate_idempotency_key("airbnb", data)

    # Check if already processed
    if await is_already_processed(idempotency_key):
        WEBHOOK_PROCESSED.labels(
            channel_type="airbnb",
            status="duplicate"
        ).inc()
        return WebhookResponse(
            status="already_processed",
            event_id=data.get("event_id")
        )

    logger.info(
        "Received Airbnb webhook",
        event_type=event_type,
        event_id=data.get("event_id")
    )

    # Process based on event type
    try:
        if event_type in ["reservation.created", "reservation.accepted"]:
            reservation = data.get("reservation", {})
            listing_id = str(reservation.get("listing_id", ""))

            # Get connection
            connection = await get_connection_by_channel_property(
                "airbnb", listing_id
            )
            if not connection:
                logger.warning(
                    "No connection found for Airbnb listing",
                    listing_id=listing_id
                )
                return WebhookResponse(
                    status="skipped",
                    message="Listing not connected"
                )

            # Queue import task
            background_tasks.add_task(
                import_channel_booking.delay,
                channel_type="airbnb",
                connection_id=str(connection.id),
                booking_data=_map_airbnb_reservation(reservation),
                idempotency_key=idempotency_key
            )

        elif event_type in ["reservation.cancelled", "reservation.cancelled_by_host", "reservation.cancelled_by_guest"]:
            reservation = data.get("reservation", {})
            background_tasks.add_task(
                _process_airbnb_cancellation,
                reservation=reservation,
                idempotency_key=idempotency_key
            )

        elif event_type == "reservation.updated":
            reservation = data.get("reservation", {})
            background_tasks.add_task(
                _process_airbnb_update,
                reservation=reservation,
                idempotency_key=idempotency_key
            )

        # Mark as processed
        await mark_as_processed(idempotency_key)

        WEBHOOK_PROCESSED.labels(
            channel_type="airbnb",
            status="success"
        ).inc()

        # Record latency
        latency = (datetime.utcnow() - start_time).total_seconds()
        WEBHOOK_LATENCY.labels(channel_type="airbnb").observe(latency)

        return WebhookResponse(
            status="accepted",
            event_id=data.get("event_id")
        )

    except Exception as e:
        logger.error(
            "Error processing Airbnb webhook",
            error=str(e),
            event_type=event_type
        )
        WEBHOOK_PROCESSED.labels(
            channel_type="airbnb",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="Processing error")


def _map_airbnb_reservation(reservation: dict) -> dict:
    """Map Airbnb reservation to standard format."""
    guest = reservation.get("guest", {})
    pricing = reservation.get("pricing_quote", {})

    return {
        "channel_booking_id": str(reservation.get("confirmation_code")),
        "channel_guest_id": str(guest.get("id", "")),
        "listing_id": str(reservation.get("listing_id")),
        "guest_first_name": guest.get("first_name", ""),
        "guest_last_name": guest.get("last_name", ""),
        "guest_email": guest.get("email", ""),
        "guest_phone": guest.get("phone"),
        "check_in": reservation.get("start_date"),
        "check_out": reservation.get("end_date"),
        "num_guests": reservation.get("number_of_guests", 1),
        "num_adults": reservation.get("number_of_adults", 1),
        "num_children": reservation.get("number_of_children", 0),
        "num_infants": reservation.get("number_of_infants", 0),
        "total_price": pricing.get("total", {}).get("amount", 0),
        "currency": pricing.get("total", {}).get("currency", "EUR"),
        "status": reservation.get("status"),
        "booked_at": reservation.get("created_at"),
        "special_requests": reservation.get("guest_message"),
        "channel_data": reservation
    }


async def _process_airbnb_cancellation(reservation: dict, idempotency_key: str):
    """Process Airbnb cancellation."""
    from .sync_engine import handle_channel_cancellation

    await handle_channel_cancellation.delay(
        channel_type="airbnb",
        channel_booking_id=str(reservation.get("confirmation_code")),
        cancellation_reason=reservation.get("cancellation_reason"),
        cancelled_by=reservation.get("cancelled_by"),
        idempotency_key=idempotency_key
    )


async def _process_airbnb_update(reservation: dict, idempotency_key: str):
    """Process Airbnb reservation update."""
    from .sync_engine import handle_channel_booking_update

    await handle_channel_booking_update.delay(
        channel_type="airbnb",
        channel_booking_id=str(reservation.get("confirmation_code")),
        update_data=_map_airbnb_reservation(reservation),
        idempotency_key=idempotency_key
    )


# =============================================================================
# BOOKING.COM WEBHOOK
# =============================================================================

@router.post("/booking_com", response_model=WebhookResponse)
async def booking_com_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_booking_signature: str = Header(None, alias="X-Booking-Signature")
):
    """
    Handle Booking.com push notifications.

    Booking.com uses push notifications rather than webhooks.
    The format is slightly different from other platforms.
    """
    start_time = datetime.utcnow()
    payload = await request.body()

    # Verify signature
    if x_booking_signature:
        if not verify_hmac_signature(
            payload,
            x_booking_signature,
            settings.BOOKING_COM_WEBHOOK_SECRET
        ):
            logger.warning("Invalid Booking.com webhook signature")
            WEBHOOK_PROCESSED.labels(
                channel_type="booking_com",
                status="invalid_signature"
            ).inc()
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Determine event type from payload
    event_type = _determine_booking_com_event_type(data)
    WEBHOOK_RECEIVED.labels(
        channel_type="booking_com",
        event_type=event_type
    ).inc()

    idempotency_key = generate_idempotency_key("booking_com", data)

    if await is_already_processed(idempotency_key):
        WEBHOOK_PROCESSED.labels(
            channel_type="booking_com",
            status="duplicate"
        ).inc()
        return WebhookResponse(status="already_processed")

    logger.info(
        "Received Booking.com webhook",
        event_type=event_type,
        reservation_id=data.get("reservation_id")
    )

    try:
        hotel_id = str(data.get("hotel_id", ""))
        connection = await get_connection_by_channel_property("booking_com", hotel_id)

        if not connection:
            return WebhookResponse(
                status="skipped",
                message="Property not connected"
            )

        if event_type == "new":
            background_tasks.add_task(
                import_channel_booking.delay,
                channel_type="booking_com",
                connection_id=str(connection.id),
                booking_data=_map_booking_com_reservation(data),
                idempotency_key=idempotency_key
            )
        elif event_type == "cancelled":
            background_tasks.add_task(
                _process_booking_com_cancellation,
                reservation=data,
                idempotency_key=idempotency_key
            )
        elif event_type == "modified":
            background_tasks.add_task(
                _process_booking_com_modification,
                reservation=data,
                idempotency_key=idempotency_key
            )

        await mark_as_processed(idempotency_key)

        WEBHOOK_PROCESSED.labels(
            channel_type="booking_com",
            status="success"
        ).inc()

        latency = (datetime.utcnow() - start_time).total_seconds()
        WEBHOOK_LATENCY.labels(channel_type="booking_com").observe(latency)

        return WebhookResponse(status="accepted")

    except Exception as e:
        logger.error("Error processing Booking.com webhook", error=str(e))
        WEBHOOK_PROCESSED.labels(
            channel_type="booking_com",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="Processing error")


def _determine_booking_com_event_type(data: dict) -> str:
    """Determine Booking.com event type from payload."""
    status = data.get("status", "").lower()
    if status == "new":
        return "new"
    elif status == "cancelled":
        return "cancelled"
    elif status == "modified":
        return "modified"
    elif status == "no_show":
        return "no_show"
    return "unknown"


def _map_booking_com_reservation(reservation: dict) -> dict:
    """Map Booking.com reservation to standard format."""
    guest = reservation.get("guest", {})
    room = reservation.get("room", {})

    return {
        "channel_booking_id": str(reservation.get("reservation_id")),
        "channel_guest_id": str(guest.get("guest_id", "")),
        "listing_id": str(reservation.get("hotel_id")),
        "guest_first_name": guest.get("first_name", ""),
        "guest_last_name": guest.get("last_name", ""),
        "guest_email": guest.get("email", ""),
        "guest_phone": guest.get("telephone"),
        "check_in": reservation.get("arrival_date"),
        "check_out": reservation.get("departure_date"),
        "num_guests": room.get("number_of_guests", 2),
        "num_adults": room.get("adults", 2),
        "num_children": room.get("children", 0),
        "num_infants": 0,
        "total_price": reservation.get("total_price", 0),
        "currency": reservation.get("currency_code", "EUR"),
        "status": reservation.get("status"),
        "booked_at": reservation.get("booked_at"),
        "special_requests": reservation.get("remarks"),
        "channel_data": reservation
    }


async def _process_booking_com_cancellation(reservation: dict, idempotency_key: str):
    from .sync_engine import handle_channel_cancellation

    await handle_channel_cancellation.delay(
        channel_type="booking_com",
        channel_booking_id=str(reservation.get("reservation_id")),
        cancellation_reason=reservation.get("cancellation_reason"),
        idempotency_key=idempotency_key
    )


async def _process_booking_com_modification(reservation: dict, idempotency_key: str):
    from .sync_engine import handle_channel_booking_update

    await handle_channel_booking_update.delay(
        channel_type="booking_com",
        channel_booking_id=str(reservation.get("reservation_id")),
        update_data=_map_booking_com_reservation(reservation),
        idempotency_key=idempotency_key
    )


# =============================================================================
# EXPEDIA WEBHOOK
# =============================================================================

@router.post("/expedia", response_model=WebhookResponse)
async def expedia_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_expedia_signature: str = Header(None, alias="X-Expedia-Signature")
):
    """
    Handle Expedia webhook notifications.

    Events:
    - BOOKING_CREATED
    - BOOKING_MODIFIED
    - BOOKING_CANCELLED
    """
    start_time = datetime.utcnow()
    payload = await request.body()

    if x_expedia_signature:
        if not verify_hmac_signature(
            payload,
            x_expedia_signature,
            settings.EXPEDIA_WEBHOOK_SECRET
        ):
            WEBHOOK_PROCESSED.labels(
                channel_type="expedia",
                status="invalid_signature"
            ).inc()
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = data.get("eventType", "unknown")
    WEBHOOK_RECEIVED.labels(
        channel_type="expedia",
        event_type=event_type
    ).inc()

    idempotency_key = generate_idempotency_key("expedia", data)

    if await is_already_processed(idempotency_key):
        WEBHOOK_PROCESSED.labels(
            channel_type="expedia",
            status="duplicate"
        ).inc()
        return WebhookResponse(status="already_processed")

    logger.info(
        "Received Expedia webhook",
        event_type=event_type,
        booking_id=data.get("bookingId")
    )

    try:
        property_id = str(data.get("propertyId", ""))
        connection = await get_connection_by_channel_property("expedia", property_id)

        if not connection:
            return WebhookResponse(
                status="skipped",
                message="Property not connected"
            )

        if event_type == "BOOKING_CREATED":
            background_tasks.add_task(
                import_channel_booking.delay,
                channel_type="expedia",
                connection_id=str(connection.id),
                booking_data=_map_expedia_booking(data),
                idempotency_key=idempotency_key
            )
        elif event_type == "BOOKING_CANCELLED":
            background_tasks.add_task(
                _process_expedia_cancellation,
                booking=data,
                idempotency_key=idempotency_key
            )
        elif event_type == "BOOKING_MODIFIED":
            background_tasks.add_task(
                _process_expedia_modification,
                booking=data,
                idempotency_key=idempotency_key
            )

        await mark_as_processed(idempotency_key)

        WEBHOOK_PROCESSED.labels(
            channel_type="expedia",
            status="success"
        ).inc()

        latency = (datetime.utcnow() - start_time).total_seconds()
        WEBHOOK_LATENCY.labels(channel_type="expedia").observe(latency)

        return WebhookResponse(status="accepted")

    except Exception as e:
        logger.error("Error processing Expedia webhook", error=str(e))
        WEBHOOK_PROCESSED.labels(
            channel_type="expedia",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="Processing error")


def _map_expedia_booking(booking: dict) -> dict:
    """Map Expedia booking to standard format."""
    guest = booking.get("primaryGuest", {})
    stay = booking.get("stayDates", {})
    payment = booking.get("payment", {})
    guest_counts = booking.get("guestCounts", {})

    return {
        "channel_booking_id": str(booking.get("bookingId")),
        "channel_guest_id": str(guest.get("guestId", "")),
        "listing_id": str(booking.get("propertyId")),
        "guest_first_name": guest.get("firstName", ""),
        "guest_last_name": guest.get("lastName", ""),
        "guest_email": guest.get("email", ""),
        "guest_phone": guest.get("phone", {}).get("number"),
        "check_in": stay.get("checkIn"),
        "check_out": stay.get("checkOut"),
        "num_guests": guest_counts.get("adults", 1) + guest_counts.get("children", 0),
        "num_adults": guest_counts.get("adults", 1),
        "num_children": guest_counts.get("children", 0),
        "num_infants": guest_counts.get("infants", 0),
        "total_price": payment.get("totalAmount", {}).get("amount", 0),
        "currency": payment.get("totalAmount", {}).get("currency", "EUR"),
        "status": booking.get("status"),
        "booked_at": booking.get("createdDateTime"),
        "special_requests": booking.get("specialRequests"),
        "channel_data": booking
    }


async def _process_expedia_cancellation(booking: dict, idempotency_key: str):
    from .sync_engine import handle_channel_cancellation

    await handle_channel_cancellation.delay(
        channel_type="expedia",
        channel_booking_id=str(booking.get("bookingId")),
        cancellation_reason=booking.get("cancellationReason"),
        idempotency_key=idempotency_key
    )


async def _process_expedia_modification(booking: dict, idempotency_key: str):
    from .sync_engine import handle_channel_booking_update

    await handle_channel_booking_update.delay(
        channel_type="expedia",
        channel_booking_id=str(booking.get("bookingId")),
        update_data=_map_expedia_booking(booking),
        idempotency_key=idempotency_key
    )


# =============================================================================
# FEWO-DIREKT (VRBO) WEBHOOK
# =============================================================================

@router.post("/fewo_direkt", response_model=WebhookResponse)
async def fewo_direkt_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_vrbo_signature: str = Header(None, alias="X-Vrbo-Signature")
):
    """
    Handle FeWo-direkt (Vrbo) webhook notifications.

    Events:
    - RESERVATION_CREATED
    - RESERVATION_MODIFIED
    - RESERVATION_CANCELLED
    - INSTANT_BOOK_CREATED
    """
    start_time = datetime.utcnow()
    payload = await request.body()

    if x_vrbo_signature:
        if not verify_hmac_signature(
            payload,
            x_vrbo_signature,
            settings.FEWO_DIREKT_WEBHOOK_SECRET
        ):
            WEBHOOK_PROCESSED.labels(
                channel_type="fewo_direkt",
                status="invalid_signature"
            ).inc()
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = data.get("eventType", "unknown")
    WEBHOOK_RECEIVED.labels(
        channel_type="fewo_direkt",
        event_type=event_type
    ).inc()

    idempotency_key = generate_idempotency_key("fewo_direkt", data)

    if await is_already_processed(idempotency_key):
        WEBHOOK_PROCESSED.labels(
            channel_type="fewo_direkt",
            status="duplicate"
        ).inc()
        return WebhookResponse(status="already_processed")

    logger.info(
        "Received FeWo-direkt webhook",
        event_type=event_type,
        reservation_id=data.get("reservationId")
    )

    try:
        listing_id = str(data.get("listingId", ""))
        connection = await get_connection_by_channel_property("fewo_direkt", listing_id)

        if not connection:
            return WebhookResponse(
                status="skipped",
                message="Property not connected"
            )

        if event_type in ["RESERVATION_CREATED", "INSTANT_BOOK_CREATED"]:
            background_tasks.add_task(
                import_channel_booking.delay,
                channel_type="fewo_direkt",
                connection_id=str(connection.id),
                booking_data=_map_fewo_direkt_reservation(data),
                idempotency_key=idempotency_key
            )
        elif event_type == "RESERVATION_CANCELLED":
            background_tasks.add_task(
                _process_fewo_direkt_cancellation,
                reservation=data,
                idempotency_key=idempotency_key
            )
        elif event_type == "RESERVATION_MODIFIED":
            background_tasks.add_task(
                _process_fewo_direkt_modification,
                reservation=data,
                idempotency_key=idempotency_key
            )

        await mark_as_processed(idempotency_key)

        WEBHOOK_PROCESSED.labels(
            channel_type="fewo_direkt",
            status="success"
        ).inc()

        latency = (datetime.utcnow() - start_time).total_seconds()
        WEBHOOK_LATENCY.labels(channel_type="fewo_direkt").observe(latency)

        return WebhookResponse(status="accepted")

    except Exception as e:
        logger.error("Error processing FeWo-direkt webhook", error=str(e))
        WEBHOOK_PROCESSED.labels(
            channel_type="fewo_direkt",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="Processing error")


def _map_fewo_direkt_reservation(reservation: dict) -> dict:
    """Map FeWo-direkt reservation to standard format."""
    guest = reservation.get("guest", {})
    stay = reservation.get("stayDetails", {})
    pricing = reservation.get("pricing", {})
    guest_counts = stay.get("guests", {})

    return {
        "channel_booking_id": str(reservation.get("reservationId")),
        "channel_guest_id": str(guest.get("guestId", "")),
        "listing_id": str(reservation.get("listingId")),
        "guest_first_name": guest.get("firstName", ""),
        "guest_last_name": guest.get("lastName", ""),
        "guest_email": guest.get("email", ""),
        "guest_phone": guest.get("phone"),
        "check_in": stay.get("checkIn"),
        "check_out": stay.get("checkOut"),
        "num_guests": guest_counts.get("adults", 1) + guest_counts.get("children", 0),
        "num_adults": guest_counts.get("adults", 1),
        "num_children": guest_counts.get("children", 0),
        "num_infants": guest_counts.get("infants", 0),
        "total_price": pricing.get("total", {}).get("amount", 0),
        "currency": pricing.get("total", {}).get("currency", "EUR"),
        "status": reservation.get("status"),
        "booked_at": reservation.get("createdAt"),
        "special_requests": reservation.get("guestMessage"),
        "channel_data": reservation
    }


async def _process_fewo_direkt_cancellation(reservation: dict, idempotency_key: str):
    from .sync_engine import handle_channel_cancellation

    await handle_channel_cancellation.delay(
        channel_type="fewo_direkt",
        channel_booking_id=str(reservation.get("reservationId")),
        cancellation_reason=reservation.get("cancellationReason"),
        idempotency_key=idempotency_key
    )


async def _process_fewo_direkt_modification(reservation: dict, idempotency_key: str):
    from .sync_engine import handle_channel_booking_update

    await handle_channel_booking_update.delay(
        channel_type="fewo_direkt",
        channel_booking_id=str(reservation.get("reservationId")),
        update_data=_map_fewo_direkt_reservation(reservation),
        idempotency_key=idempotency_key
    )


# =============================================================================
# GOOGLE VACATION RENTALS WEBHOOK
# =============================================================================

@router.post("/google", response_model=WebhookResponse)
async def google_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """
    Handle Google Vacation Rentals webhook notifications.

    Google uses Cloud Pub/Sub for notifications, which are delivered
    as HTTP POST requests with JWT authentication.
    """
    start_time = datetime.utcnow()
    payload = await request.body()

    # Verify JWT token
    if authorization:
        token = authorization.replace("Bearer ", "")
        try:
            import jwt
            # Verify against Google's public keys
            # In production, use proper JWT verification
            decoded = jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            logger.warning("Invalid Google JWT", error=str(e))
            WEBHOOK_PROCESSED.labels(
                channel_type="google",
                status="invalid_signature"
            ).inc()
            raise HTTPException(status_code=401, detail="Invalid token")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Google Pub/Sub message format
    message = data.get("message", {})
    message_data = message.get("data", {})

    # Decode base64 data if present
    if isinstance(message_data, str):
        import base64
        try:
            message_data = json.loads(base64.b64decode(message_data).decode())
        except Exception:
            message_data = {}

    event_type = message_data.get("eventType", "unknown")
    WEBHOOK_RECEIVED.labels(
        channel_type="google",
        event_type=event_type
    ).inc()

    idempotency_key = message.get("messageId", generate_idempotency_key("google", data))

    if await is_already_processed(idempotency_key):
        WEBHOOK_PROCESSED.labels(
            channel_type="google",
            status="duplicate"
        ).inc()
        return WebhookResponse(status="already_processed")

    logger.info(
        "Received Google webhook",
        event_type=event_type,
        message_id=message.get("messageId")
    )

    try:
        property_id = str(message_data.get("propertyId", ""))
        connection = await get_connection_by_channel_property("google", property_id)

        if not connection:
            return WebhookResponse(
                status="skipped",
                message="Property not connected"
            )

        if event_type == "BOOKING_CREATED":
            background_tasks.add_task(
                import_channel_booking.delay,
                channel_type="google",
                connection_id=str(connection.id),
                booking_data=_map_google_booking(message_data),
                idempotency_key=idempotency_key
            )
        elif event_type == "BOOKING_CANCELLED":
            background_tasks.add_task(
                _process_google_cancellation,
                booking=message_data,
                idempotency_key=idempotency_key
            )

        await mark_as_processed(idempotency_key)

        WEBHOOK_PROCESSED.labels(
            channel_type="google",
            status="success"
        ).inc()

        latency = (datetime.utcnow() - start_time).total_seconds()
        WEBHOOK_LATENCY.labels(channel_type="google").observe(latency)

        return WebhookResponse(status="accepted")

    except Exception as e:
        logger.error("Error processing Google webhook", error=str(e))
        WEBHOOK_PROCESSED.labels(
            channel_type="google",
            status="error"
        ).inc()
        raise HTTPException(status_code=500, detail="Processing error")


def _map_google_booking(booking: dict) -> dict:
    """Map Google booking to standard format."""
    guest = booking.get("guest", {})
    stay = booking.get("stay", {})
    pricing = booking.get("pricing", {})

    return {
        "channel_booking_id": str(booking.get("bookingId")),
        "channel_guest_id": str(guest.get("guestId", "")),
        "listing_id": str(booking.get("propertyId")),
        "guest_first_name": guest.get("firstName", ""),
        "guest_last_name": guest.get("lastName", ""),
        "guest_email": guest.get("email", ""),
        "guest_phone": guest.get("phone"),
        "check_in": stay.get("checkIn"),
        "check_out": stay.get("checkOut"),
        "num_guests": stay.get("numberOfGuests", 2),
        "num_adults": stay.get("numberOfAdults", 2),
        "num_children": stay.get("numberOfChildren", 0),
        "num_infants": 0,
        "total_price": pricing.get("totalPrice", {}).get("amount", 0),
        "currency": pricing.get("totalPrice", {}).get("currency", "EUR"),
        "status": booking.get("status"),
        "booked_at": booking.get("createdTime"),
        "special_requests": booking.get("specialRequests"),
        "channel_data": booking
    }


async def _process_google_cancellation(booking: dict, idempotency_key: str):
    from .sync_engine import handle_channel_cancellation

    await handle_channel_cancellation.delay(
        channel_type="google",
        channel_booking_id=str(booking.get("bookingId")),
        idempotency_key=idempotency_key
    )


# =============================================================================
# HEALTH CHECK ENDPOINT
# =============================================================================

@router.get("/health")
async def webhook_health_check():
    """Health check endpoint for webhook handlers."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": [
            "/api/v1/webhooks/airbnb",
            "/api/v1/webhooks/booking_com",
            "/api/v1/webhooks/expedia",
            "/api/v1/webhooks/fewo_direkt",
            "/api/v1/webhooks/google"
        ]
    }
