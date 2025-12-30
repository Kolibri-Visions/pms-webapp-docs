# ADR-004: Event-Driven Sync Architecture

**Status:** Accepted
**Date:** 2025-12-21
**Decision Makers:** System Architecture Team

---

## Context

The PMS-Webapp Channel Manager must synchronize booking and availability data bidirectionally with 5 external platforms (Airbnb, Booking.com, Expedia, FeWo-direkt, Google Vacation Rentals). We need an architecture that:

- Ensures PMS-Core remains the source of truth
- Propagates changes to all connected channels reliably
- Handles inbound bookings from channels with validation
- Manages different rate limits and API formats per platform
- Recovers gracefully from failures
- Supports eventual consistency with minimal latency

## Decision Drivers

1. **Source of Truth**: PMS-Core must be authoritative for all booking data
2. **Reliability**: Changes must eventually reach all channels
3. **Performance**: Low latency from change to sync (< 30 seconds)
4. **Resilience**: Handle platform outages gracefully
5. **Scalability**: Process thousands of sync events per day
6. **Observability**: Track sync status per channel per booking

## Options Considered

### Option 1: Direct Synchronous Sync

**Description:**
When a booking is created, immediately call all channel APIs synchronously.

**Pros:**
- Simple implementation
- Immediate feedback

**Cons:**
- Slow (waits for all APIs)
- Any API failure fails the whole operation
- Poor user experience
- No retry mechanism

### Option 2: Queue-Based Async with Redis + Celery

**Description:**
PMS-Core publishes events to Redis. Celery workers consume events and sync to channels asynchronously.

**Pros:**
- Decoupled from API latency
- Built-in retry with backoff
- Priority queues for urgent events
- Mature, well-documented
- Easy to scale workers

**Cons:**
- Eventual consistency
- Need to track sync status
- More infrastructure

### Option 3: Event Sourcing with Kafka/EventBridge

**Description:**
Full event sourcing with Kafka or AWS EventBridge for durable event storage.

**Pros:**
- Complete event history
- Event replay capability
- Strong durability guarantees

**Cons:**
- Significant complexity
- Higher cost
- Overkill for current scale
- Steeper learning curve

### Option 4: Webhook-Only (No Outbound Sync)

**Description:**
Only handle inbound webhooks; let channels poll for availability.

**Pros:**
- Simplest implementation

**Cons:**
- Not all platforms support polling
- Stale data on channels
- Poor guest experience
- Against platform best practices

## Decision

**We choose Queue-Based Async with Redis + Celery** for the following reasons:

1. **Proven Pattern**: Redis + Celery is battle-tested for async task processing in Python applications.

2. **Built-in Resilience**: Celery provides retry with exponential backoff, dead letter queues, and task timeouts.

3. **Scalability**: Workers can be scaled independently based on queue depth.

4. **Observability**: Celery integrates with Flower for monitoring and Sentry for error tracking.

5. **Right-Sized**: Provides reliability without the complexity of Kafka for our scale.

6. **Consistent with Stack**: Integrates seamlessly with FastAPI and Redis (already used for caching/locking).

## Consequences

### Positive

- Non-blocking booking creation (fast UX)
- Reliable delivery with automatic retries
- Per-channel rate limiting and circuit breaking
- Easy to add new channels
- Comprehensive sync logging

### Negative

- Eventual consistency (changes take seconds to propagate)
- Need to manage Celery worker infrastructure
- Complexity in tracking sync status
- Potential for event ordering issues

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Events lost in Redis crash | Redis persistence (AOF), task acknowledgment after completion |
| Worker crashes mid-task | `task_acks_late=True` re-queues unfinished tasks |
| Event ordering issues | Use timestamps, sequence numbers, or accept last-write-wins |
| Queue backlog | Auto-scale workers, priority queues, backpressure alerts |

## Architecture

### Event Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EVENT FLOW                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  OUTBOUND SYNC (Core → Channels)                                    │
│  ═══════════════════════════════                                    │
│                                                                      │
│  ┌──────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────────┐ │
│  │ PMS-Core │───▶│  Event  │───▶│  Redis  │───▶│ Celery Workers  │ │
│  │ (CRUD)   │    │Publisher│    │  Queue  │    │ (per channel)   │ │
│  └──────────┘    └─────────┘    └─────────┘    └────────┬────────┘ │
│                                                          │          │
│                          ┌───────────────────────────────┼──────┐  │
│                          ▼           ▼           ▼       ▼      ▼  │
│                      Airbnb    Booking.com   Expedia  FeWo   Google│
│                                                                      │
│  INBOUND SYNC (Channels → Core)                                     │
│  ═══════════════════════════════                                    │
│                                                                      │
│  ┌──────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────────┐ │
│  │ Webhook  │───▶│ Validate│───▶│ PMS-Core│───▶│ Event Publisher │ │
│  │ Handler  │    │ & Lock  │    │ (CRUD)  │    │ (sync to others)│ │
│  └──────────┘    └─────────┘    └─────────┘    └─────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Event Types

```python
class EventType(str, Enum):
    # Core Events (from PMS-Core)
    BOOKING_CREATED = "booking.created"
    BOOKING_UPDATED = "booking.updated"
    BOOKING_CANCELLED = "booking.cancelled"
    AVAILABILITY_UPDATED = "availability.updated"
    PRICING_UPDATED = "pricing.updated"

    # Channel Events (from Channel Manager)
    CHANNEL_BOOKING_RECEIVED = "channel.booking_received"
    SYNC_COMPLETED = "sync.completed"
    SYNC_FAILED = "sync.failed"
```

### Event Schema

```python
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class SyncEvent(BaseModel):
    id: UUID
    event_type: EventType
    entity_type: str  # "booking", "property", "availability"
    entity_id: UUID
    payload: dict
    source: str  # "direct", "airbnb", "booking_com", etc.
    timestamp: datetime
    idempotency_key: str  # For deduplication
```

### Celery Configuration

```python
from celery import Celery

app = Celery('pms_webapp')

app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',

    # Task routing
    task_routes={
        'tasks.sync.airbnb.*': {'queue': 'airbnb'},
        'tasks.sync.booking_com.*': {'queue': 'booking_com'},
        'tasks.sync.expedia.*': {'queue': 'expedia'},
        'tasks.sync.fewo_direkt.*': {'queue': 'fewo_direkt'},
        'tasks.sync.google_vr.*': {'queue': 'google_vr'},
        'tasks.notify.*': {'queue': 'notifications'},
    },

    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Rate limiting (global)
    worker_prefetch_multiplier=4,

    # Timeouts
    task_soft_time_limit=120,
    task_time_limit=180,
)
```

### Sync Task Example

```python
from celery import Task
from tenacity import retry, stop_after_attempt, wait_exponential

class ChannelSyncTask(Task):
    autoretry_for = (ChannelAPIError, RateLimitError)
    retry_backoff = True
    retry_backoff_max = 3600  # Max 1 hour between retries
    retry_jitter = True
    max_retries = 10

@app.task(bind=True, base=ChannelSyncTask)
def sync_booking_to_airbnb(self, booking_id: str):
    """Sync a booking to Airbnb."""

    # Idempotency check
    if is_already_processed(self.request.id):
        logger.info(f"Task {self.request.id} already processed")
        return

    # Rate limiting
    with rate_limiter("airbnb", limit=10, period=1):

        # Circuit breaker
        with circuit_breaker("airbnb"):

            # Get booking and connection
            booking = get_booking(booking_id)
            connection = get_channel_connection(booking.property_id, "airbnb")

            # Sync via adapter
            adapter = AirbnbAdapter(connection)
            result = adapter.sync_booking(booking)

            # Log success
            log_sync_event(booking_id, "airbnb", "success", result)
            mark_processed(self.request.id)

            return result
```

### Event Publishing

```python
async def publish_event(event_type: EventType, entity: BaseModel, source: str = "direct"):
    """Publish an event to the sync queue."""

    event = SyncEvent(
        id=uuid4(),
        event_type=event_type,
        entity_type=type(entity).__name__.lower(),
        entity_id=entity.id,
        payload=entity.dict(),
        source=source,
        timestamp=datetime.utcnow(),
        idempotency_key=f"{event_type}:{entity.id}:{datetime.utcnow().isoformat()}"
    )

    # Store event in database for audit
    await db.sync_events.create(event)

    # Publish to Redis
    await redis.xadd("events:sync", event.dict())

    # Trigger Celery tasks for each connected channel
    connections = await get_active_connections(entity.property_id)
    for conn in connections:
        # Don't sync back to source channel
        if conn.platform != source:
            task = get_sync_task(conn.platform)
            task.delay(str(entity.id))
```

### Webhook Handler (Inbound)

```python
@app.post("/webhooks/{platform}")
async def handle_webhook(platform: str, request: Request):
    """Handle inbound webhook from channel platform."""

    # Verify signature
    if not verify_webhook_signature(platform, request):
        raise HTTPException(403, "Invalid signature")

    payload = await request.json()

    # Parse platform-specific format
    adapter = get_channel_adapter(platform)
    booking_data = adapter.parse_webhook(payload)

    # Acquire lock to prevent race conditions
    lock_key = f"calendar:lock:{booking_data.property_id}"
    async with redis_lock(lock_key, timeout=10) as lock:
        if not lock:
            raise HTTPException(409, "Resource locked")

        # Validate no conflicts with Core
        if await has_conflict(booking_data):
            # Reject on platform
            await adapter.reject_booking(booking_data.external_id)
            return {"status": "rejected", "reason": "conflict"}

        # Create/update in PMS-Core
        booking = await pms_core.upsert_booking(booking_data)

        # Publish event (will sync to OTHER channels)
        await publish_event(EventType.BOOKING_CREATED, booking, source=platform)

    return {"status": "accepted"}
```

## Observability

### Metrics

```python
# Prometheus metrics
sync_tasks_total = Counter(
    'pms_sync_tasks_total',
    'Total sync tasks',
    ['platform', 'event_type', 'status']
)

sync_latency = Histogram(
    'pms_sync_latency_seconds',
    'Sync task latency',
    ['platform']
)

queue_depth = Gauge(
    'pms_queue_depth',
    'Queue depth',
    ['queue_name']
)
```

### Logging

```python
logger.info(
    "Sync completed",
    extra={
        "booking_id": booking_id,
        "platform": "airbnb",
        "latency_ms": latency,
        "correlation_id": correlation_id
    }
)
```

## References

- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Streams](https://redis.io/docs/data-types/streams/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [ADR-005: Conflict Resolution Strategy](./ADR-005-conflict-resolution.md)
