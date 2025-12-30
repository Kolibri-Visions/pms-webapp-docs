# PMS-Webapp System Architecture

**Version:** 1.0.0
**Last Updated:** 2025-12-21
**Status:** Approved

---

## Executive Summary

PMS-Webapp is an all-in-one vacation rental booking software designed to serve as the single source of truth for property management. The system integrates a Property Management System Core (PMS-Core), a Direct Booking Engine, and a Channel Manager that synchronizes with five major booking platforms.

### Key Architectural Principles

1. **PMS-Core as Source of Truth**: All booking, availability, and pricing data originates from and is validated by PMS-Core
2. **Event-Driven Architecture**: Channel Manager reacts to Core events, enabling loose coupling and scalability
3. **Equal Treatment**: Direct bookings and channel bookings are treated identically within the Core
4. **Zero Double-Bookings**: Distributed locking and conflict resolution ensure calendar integrity
5. **Multi-Tenant by Design**: Row-Level Security (RLS) isolates property owner data from day one

---

## 1. Technology Stack

### 1.1 Backend Framework: FastAPI (Python)

**Selected:** FastAPI 0.110+

**Rationale:**
- Native async/await support for high-concurrency webhook handling
- Automatic OpenAPI documentation generation
- Pydantic v2 for robust data validation
- Excellent performance (comparable to Node.js/Go)
- Rich ecosystem for background tasks (Celery, ARQ)
- Strong typing support with Python 3.11+

**Alternatives Considered:**
- NestJS: Strong TypeScript support but heavier runtime
- Django: Mature but less async-native, slower for high-volume webhooks

*See [ADR-001: Backend Framework Choice](./ADRs/ADR-001-backend-framework.md)*

### 1.2 Database: Supabase PostgreSQL

**Selected:** Supabase (managed PostgreSQL 15+)

**Rationale:**
- Built-in Row-Level Security (RLS) for multi-tenancy
- Real-time subscriptions for live updates
- Integrated authentication (Supabase Auth)
- Edge Functions for serverless logic
- Automatic backups and point-in-time recovery
- PostgREST for direct database API access

**Schema Highlights:**
- `properties` - Property definitions with owner isolation
- `bookings` - Unified booking table (all sources)
- `availability` - Calendar blocks and pricing
- `channel_connections` - OAuth tokens per platform
- `sync_events` - Event sourcing for audit trail

*See [ADR-002: Database Choice](./ADRs/ADR-002-database-choice.md)*

### 1.3 Caching & Queue: Redis + Celery

**Selected:**
- Redis 7+ (caching, distributed locks, rate limiting)
- Celery 5+ (task queue with Redis broker)

**Rationale:**
- Redis provides sub-millisecond latency for availability checks
- Distributed locks prevent double-bookings
- Celery handles async sync tasks with retry logic
- Redis Streams for event publishing (lightweight alternative to Kafka)

**Use Cases:**
- Availability cache (TTL: 60 seconds)
- Calendar locks during booking flow (TTL: 10 minutes)
- Rate limiting per channel API
- Background sync tasks with priority queues

*See [ADR-004: Event-Driven Sync Architecture](./ADRs/ADR-004-event-driven-sync.md)*

### 1.4 Frontend Framework: Next.js 14+

**Selected:** Next.js 14 with App Router

**Rationale:**
- Server Components for fast initial page loads
- React Server Actions for form handling
- Built-in API routes (optional, can proxy to FastAPI)
- Excellent SEO for direct booking pages
- Vercel deployment with edge caching
- shadcn/ui for consistent component library

**Key Pages:**
- `/` - Landing & property search
- `/properties/[id]` - Property detail with booking widget
- `/dashboard` - Property owner admin (protected)
- `/bookings/[id]` - Booking confirmation & management

*See [ADR-006: Frontend Framework Choice](./ADRs/ADR-006-frontend-framework.md)*

### 1.5 Infrastructure

| Component | Technology | Provider |
|-----------|------------|----------|
| Frontend Hosting | Vercel Edge Network | Vercel |
| Backend Hosting | Cloud Run / Fly.io | GCP / Fly |
| Database | Supabase PostgreSQL | Supabase |
| Cache/Queue | Upstash Redis | Upstash |
| File Storage | Supabase Storage (S3) | Supabase |
| CDN | Vercel Edge | Vercel |
| Monitoring | Sentry + Grafana Cloud | SaaS |
| Logging | Loki + Grafana | Grafana Cloud |

---

## 2. System Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              PMS-Webapp                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Next.js   │  │   FastAPI   │  │  PMS-Core   │  │  Channel    │    │
│  │  Frontend   │──│   Backend   │──│   Engine    │──│  Manager    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│         │                │                │                │            │
│         ▼                ▼                ▼                ▼            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Supabase PostgreSQL                          │   │
│  │                    (Source of Truth)                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Redis (Cache + Queue)                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
        ┌───────────────────────────────────────────────────────┐
        │                 External Platforms                     │
        ├───────────┬───────────┬───────────┬───────────┬───────┤
        │  Airbnb   │ Booking   │  Expedia  │ FeWo-     │ Google│
        │           │  .com     │           │ direkt    │  VR   │
        └───────────┴───────────┴───────────┴───────────┴───────┘
```

### 2.2 Core Components

#### PMS-Core (Source of Truth)
- **Booking Engine**: Creates, updates, cancels bookings from any source
- **Availability Engine**: Manages calendar blocks, pricing rules
- **Guest Manager**: Unified guest profiles across all channels
- **Financial Engine**: Revenue tracking, owner statements

#### Direct Booking Engine
- **Search & Discovery**: Property search with filters
- **Booking Widget**: Embeddable availability calendar
- **Checkout Flow**: Multi-step booking with payment
- **Guest Portal**: Booking management for guests

#### Channel Manager
- **Sync Engine**: Event-driven outbound sync to platforms
- **Webhook Handlers**: Inbound sync from platform notifications
- **Rate Limiters**: Per-platform request throttling
- **Connection Manager**: OAuth token lifecycle

---

## 3. Data Model

### 3.1 Core Entities

```sql
-- Properties (multi-tenant with RLS)
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES auth.users(id) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    address JSONB NOT NULL,
    amenities TEXT[],
    max_guests INT NOT NULL,
    bedrooms INT NOT NULL,
    bathrooms DECIMAL(3,1) NOT NULL,
    base_price DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'EUR',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Owners can manage their properties"
    ON properties FOR ALL
    USING (auth.uid() = owner_id);

-- Bookings (unified for all sources)
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id) NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('direct', 'airbnb', 'booking_com', 'expedia', 'fewo_direkt', 'google_vr')),
    external_id TEXT, -- Platform booking ID
    guest_id UUID REFERENCES guests(id),
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    guests INT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('inquiry', 'reserved', 'confirmed', 'checked_in', 'checked_out', 'cancelled')),
    total_price DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'EUR',
    payment_status TEXT DEFAULT 'pending',
    special_requests TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT no_overlap EXCLUDE USING gist (
        property_id WITH =,
        daterange(check_in, check_out) WITH &&
    ) WHERE (status NOT IN ('cancelled', 'inquiry'))
);

-- Channel Connections (encrypted tokens)
CREATE TABLE channel_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id) NOT NULL,
    platform TEXT NOT NULL,
    external_property_id TEXT,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    sync_enabled BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    sync_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(property_id, platform)
);

-- Sync Events (event sourcing)
CREATE TABLE sync_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    payload JSONB NOT NULL,
    source TEXT NOT NULL,
    processed_at TIMESTAMPTZ,
    error TEXT,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sync_events_unprocessed ON sync_events(created_at) WHERE processed_at IS NULL;
```

### 3.2 Availability Model

```sql
-- Availability blocks (overrides base pricing)
CREATE TABLE availability_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    block_type TEXT NOT NULL CHECK (block_type IN ('available', 'blocked', 'maintenance')),
    price_override DECIMAL(10,2),
    min_stay INT,
    max_stay INT,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pricing rules
CREATE TABLE pricing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id) NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('weekend', 'seasonal', 'last_minute', 'length_of_stay')),
    adjustment_type TEXT NOT NULL CHECK (adjustment_type IN ('percentage', 'fixed')),
    adjustment_value DECIMAL(10,2) NOT NULL,
    conditions JSONB,
    priority INT DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Event-Driven Architecture

### 4.1 Event Types

| Event | Source | Trigger | Consumers |
|-------|--------|---------|-----------|
| `booking.created` | PMS-Core | New booking (any source) | Channel Manager, Notifications |
| `booking.updated` | PMS-Core | Status/details change | Channel Manager, Notifications |
| `booking.cancelled` | PMS-Core | Cancellation | Channel Manager, Refund Service |
| `availability.updated` | PMS-Core | Block added/modified | Channel Manager |
| `pricing.updated` | PMS-Core | Price/rule change | Channel Manager |
| `channel.booking_received` | Channel Manager | Inbound webhook | PMS-Core (validation) |
| `sync.completed` | Channel Manager | Sync finished | Logging, Alerts |
| `sync.failed` | Channel Manager | Sync error | Alerts, Retry Queue |

### 4.2 Event Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           EVENT FLOW                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  OUTBOUND (Core → Channels)                                              │
│  ─────────────────────────                                               │
│  PMS-Core                                                                │
│     │                                                                     │
│     ├──▶ booking.created ──▶ Redis Stream ──▶ Celery Workers            │
│     │                                              │                      │
│     │                           ┌──────────────────┼──────────────────┐  │
│     │                           ▼                  ▼                  ▼  │
│     │                      Airbnb Sync      Booking.com Sync    ... Sync │
│     │                           │                  │                  │  │
│     │                           ▼                  ▼                  ▼  │
│     │                      Airbnb API      Booking.com API    ... API    │
│     │                                                                     │
│  INBOUND (Channels → Core)                                               │
│  ─────────────────────────                                               │
│  External Platforms                                                       │
│     │                                                                     │
│     ├──▶ Webhook ──▶ FastAPI Handler ──▶ Validate ──▶ PMS-Core         │
│     │                                         │                          │
│     │                                         ▼                          │
│     │                              channel.booking_received              │
│     │                                         │                          │
│     │                                         ▼                          │
│     │                              Core validates & commits              │
│     │                                         │                          │
│     │                                         ▼                          │
│     │                               booking.created (from channel)       │
│     │                                         │                          │
│     │                                         ▼                          │
│     │                           Sync to OTHER channels (not source)      │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Idempotency

All event processing is idempotent:

1. **Event IDs**: Each event has a unique UUID
2. **Deduplication Table**: Processed event IDs stored in Redis (TTL: 24h)
3. **Booking IDs**: External booking IDs prevent duplicate imports
4. **Atomic Operations**: Database transactions ensure consistency

```python
async def process_event(event: SyncEvent) -> bool:
    # Check if already processed
    if await redis.exists(f"event:processed:{event.id}"):
        logger.info(f"Event {event.id} already processed, skipping")
        return True

    try:
        # Process with transaction
        async with db.transaction():
            result = await handle_event(event)
            await mark_event_processed(event.id)

        # Mark in Redis for fast dedup
        await redis.setex(f"event:processed:{event.id}", 86400, "1")
        return result
    except Exception as e:
        await handle_event_failure(event, e)
        raise
```

---

## 5. Sync Architecture

### 5.1 Outbound Sync (PMS-Core → Platforms)

```python
# Outbound sync triggered by Core events
@celery.task(bind=True, max_retries=5)
def sync_to_channel(self, booking_id: str, channel: str):
    """Sync booking state to external channel."""
    try:
        booking = get_booking(booking_id)
        connection = get_channel_connection(booking.property_id, channel)

        # Rate limiting
        with rate_limiter(channel, connection.property_id):
            adapter = get_channel_adapter(channel)
            adapter.sync_booking(booking, connection)

        log_sync_success(booking_id, channel)
    except RateLimitExceeded:
        # Retry with exponential backoff
        raise self.retry(countdown=2 ** self.request.retries * 60)
    except CircuitBreakerOpen:
        # Channel is down, queue for later
        queue_for_retry(booking_id, channel)
    except Exception as e:
        log_sync_failure(booking_id, channel, e)
        raise self.retry(exc=e)
```

### 5.2 Inbound Sync (Platforms → PMS-Core)

```python
# Webhook handler with validation
@app.post("/webhooks/{platform}")
async def handle_webhook(platform: str, request: Request):
    """Handle inbound webhook from channel platform."""
    # Verify webhook signature
    if not verify_webhook_signature(platform, request):
        raise HTTPException(403, "Invalid signature")

    payload = await request.json()

    # Parse platform-specific format
    adapter = get_channel_adapter(platform)
    booking_data = adapter.parse_webhook(payload)

    # Acquire lock for property calendar
    lock_key = f"calendar:lock:{booking_data.property_id}"
    async with redis_lock(lock_key, timeout=10):
        # Validate no conflicts
        if has_conflict(booking_data):
            # Reject booking on platform
            adapter.reject_booking(booking_data.external_id)
            return {"status": "rejected", "reason": "conflict"}

        # Create/update in PMS-Core
        booking = await pms_core.upsert_booking(booking_data)

        # Emit event for other channels
        await emit_event("booking.created", booking, source=platform)

    return {"status": "accepted", "booking_id": booking.id}
```

### 5.3 Reconciliation (Daily Full Sync)

```python
@celery.task
def daily_reconciliation():
    """Daily full sync to detect drift between PMS and channels."""
    for property in get_all_properties():
        for connection in property.channel_connections:
            try:
                adapter = get_channel_adapter(connection.platform)

                # Fetch all bookings from channel
                channel_bookings = adapter.fetch_all_bookings(connection)

                # Fetch our bookings for this channel
                our_bookings = get_bookings_by_source(
                    property.id,
                    connection.platform
                )

                # Compare and reconcile
                differences = compare_bookings(channel_bookings, our_bookings)

                for diff in differences:
                    if diff.type == "missing_in_core":
                        # Import missing booking
                        await pms_core.create_booking(diff.channel_booking)
                    elif diff.type == "status_mismatch":
                        # Channel wins for channel bookings
                        await pms_core.update_booking_status(
                            diff.our_booking.id,
                            diff.channel_booking.status
                        )
                    elif diff.type == "missing_in_channel":
                        # Re-sync to channel
                        sync_to_channel.delay(diff.our_booking.id, connection.platform)

                log_reconciliation_result(property.id, connection.platform, differences)
            except Exception as e:
                alert_reconciliation_failure(property.id, connection.platform, e)
```

---

## 6. Conflict Resolution

### 6.1 Simultaneous Booking Conflict

**Scenario**: Guest A books dates Dec 20-25 via Direct, Guest B books Dec 22-27 via Airbnb simultaneously.

**Resolution Strategy**:

```python
async def create_booking(booking_data: BookingCreate) -> Booking:
    """Create booking with distributed lock to prevent double-booking."""

    # Generate lock key for property + date range
    lock_key = f"booking:lock:{booking_data.property_id}:{booking_data.check_in}:{booking_data.check_out}"

    # Attempt to acquire lock (10 second timeout)
    lock = await redis.lock(lock_key, timeout=10, blocking_timeout=5)

    try:
        if not await lock.acquire():
            raise ConflictError("Another booking is being processed for these dates")

        # Double-check availability (lock held)
        if not await check_availability(
            booking_data.property_id,
            booking_data.check_in,
            booking_data.check_out
        ):
            raise ConflictError("Dates no longer available")

        # Create booking in database
        booking = await db.bookings.create(booking_data)

        # Emit event
        await emit_event("booking.created", booking)

        return booking
    finally:
        await lock.release()
```

**Outcome**: First commit wins, second receives immediate rejection with clear message.

### 6.2 Status Update Conflict

**Rule**: Platform data wins for channel-originated bookings, Core wins for direct bookings.

```python
def resolve_status_conflict(
    our_booking: Booking,
    channel_status: str,
    update_source: str
) -> str:
    """Determine winning status in conflict."""

    # If booking originated from this channel, channel wins
    if our_booking.source == update_source:
        return channel_status

    # If booking is direct, Core wins
    if our_booking.source == "direct":
        return our_booking.status

    # Cross-channel conflict: use most restrictive
    status_priority = {
        "cancelled": 1,
        "checked_out": 2,
        "checked_in": 3,
        "confirmed": 4,
        "reserved": 5,
        "inquiry": 6
    }

    if status_priority.get(channel_status, 99) < status_priority.get(our_booking.status, 99):
        return channel_status
    return our_booking.status
```

### 6.3 Availability Drift

**Rule**: Apply most restrictive availability, alert on mismatch.

```python
async def reconcile_availability(property_id: str, channel: str):
    """Reconcile availability between Core and channel."""

    adapter = get_channel_adapter(channel)

    # Get availability from both sources
    core_availability = await get_core_availability(property_id)
    channel_availability = await adapter.fetch_availability(property_id)

    for date in get_date_range(core_availability, channel_availability):
        core_status = core_availability.get(date)
        channel_status = channel_availability.get(date)

        if core_status != channel_status:
            # Log mismatch
            log_availability_mismatch(property_id, date, core_status, channel_status)

            # Apply most restrictive (blocked wins over available)
            if core_status == "blocked" or channel_status == "blocked":
                final_status = "blocked"
            else:
                final_status = "available"

            # Update both to match
            if core_status != final_status:
                await update_core_availability(property_id, date, final_status)
            if channel_status != final_status:
                await adapter.update_availability(property_id, date, final_status)

            # Alert if frequent mismatches
            await check_alert_threshold(property_id, channel)
```

---

## 7. Direct Booking Engine

### 7.1 Frontend Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIRECT BOOKING FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. PROPERTY SEARCH                                             │
│     ┌─────────────────────────────────────────────────────┐    │
│     │  Location  │  Dates  │  Guests  │  [Search]        │    │
│     └─────────────────────────────────────────────────────┘    │
│                           │                                     │
│                           ▼                                     │
│  2. SEARCH RESULTS                                              │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│     │ Property │  │ Property │  │ Property │                  │
│     │   Card   │  │   Card   │  │   Card   │                  │
│     └──────────┘  └──────────┘  └──────────┘                  │
│                           │                                     │
│                           ▼                                     │
│  3. PROPERTY DETAIL                                             │
│     ┌─────────────────────────────────────────────────────┐    │
│     │  Gallery  │  Description  │  Amenities  │  Reviews  │    │
│     ├─────────────────────────────────────────────────────┤    │
│     │  ┌─────────────────────────────────────────────┐    │    │
│     │  │         AVAILABILITY CALENDAR               │    │    │
│     │  │  ┌───┬───┬───┬───┬───┬───┬───┐             │    │    │
│     │  │  │ S │ M │ T │ W │ T │ F │ S │             │    │    │
│     │  │  ├───┼───┼───┼───┼───┼───┼───┤             │    │    │
│     │  │  │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │ ← Select   │    │    │
│     │  │  └───┴───┴───┴───┴───┴───┴───┘   dates     │    │    │
│     │  └─────────────────────────────────────────────┘    │    │
│     │  Guests: [2 ▼]    Total: €1,200    [Book Now]       │    │
│     └─────────────────────────────────────────────────────┘    │
│                           │                                     │
│                           ▼                                     │
│  4. CHECKOUT FLOW                                               │
│     ┌─────────────────────────────────────────────────────┐    │
│     │  Step 1: Guest Details                              │    │
│     │  ┌─────────────────────────────────────────────┐   │    │
│     │  │ Name: [____________]  Email: [____________] │   │    │
│     │  │ Phone: [__________]   Country: [__________] │   │    │
│     │  └─────────────────────────────────────────────┘   │    │
│     │                                                     │    │
│     │  Step 2: Special Requests (optional)               │    │
│     │  ┌─────────────────────────────────────────────┐   │    │
│     │  │ Early check-in, late checkout, etc.         │   │    │
│     │  └─────────────────────────────────────────────┘   │    │
│     │                                                     │    │
│     │  Step 3: Payment                                   │    │
│     │  ┌─────────────────────────────────────────────┐   │    │
│     │  │        [Stripe Payment Element]             │   │    │
│     │  └─────────────────────────────────────────────┘   │    │
│     │                                                     │    │
│     │  [◀ Back]                    [Confirm & Pay €1,200]│    │
│     └─────────────────────────────────────────────────────┘    │
│                           │                                     │
│                           ▼                                     │
│  5. CONFIRMATION                                                │
│     ┌─────────────────────────────────────────────────────┐    │
│     │  ✓ Booking Confirmed!                               │    │
│     │  Booking #: PMS-2024-12345                          │    │
│     │  Check-in: Dec 20, 2024 @ 3:00 PM                   │    │
│     │  Check-out: Dec 25, 2024 @ 11:00 AM                 │    │
│     │                                                     │    │
│     │  [View Booking]  [Add to Calendar]  [Print]        │    │
│     └─────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Backend Booking Flow

```python
# Direct booking API flow
@app.post("/api/bookings/direct")
async def create_direct_booking(
    booking: DirectBookingCreate,
    background_tasks: BackgroundTasks
):
    """Create a direct booking with full validation and payment."""

    # Step 1: Validate property exists and is active
    property = await get_property(booking.property_id)
    if not property or property.status != "active":
        raise HTTPException(404, "Property not available")

    # Step 2: Acquire calendar lock
    lock_key = f"calendar:lock:{booking.property_id}"
    lock = await redis.lock(lock_key, timeout=600)  # 10 min for checkout

    if not await lock.acquire(blocking_timeout=5):
        raise HTTPException(409, "Property is being booked, please try again")

    try:
        # Step 3: Verify availability
        if not await check_availability(
            booking.property_id,
            booking.check_in,
            booking.check_out
        ):
            raise HTTPException(409, "Selected dates are no longer available")

        # Step 4: Calculate pricing
        pricing = await calculate_booking_price(
            property,
            booking.check_in,
            booking.check_out,
            booking.guests
        )

        # Step 5: Create booking in RESERVED state
        db_booking = await create_booking({
            **booking.dict(),
            "source": "direct",
            "status": "reserved",
            "total_price": pricing.total,
            "currency": property.currency
        })

        # Step 6: Create Stripe PaymentIntent
        payment_intent = await stripe.PaymentIntent.create(
            amount=int(pricing.total * 100),
            currency=property.currency.lower(),
            metadata={"booking_id": str(db_booking.id)},
            automatic_payment_methods={"enabled": True}
        )

        # Step 7: Store payment intent ID
        await update_booking_payment(db_booking.id, payment_intent.id)

        return {
            "booking_id": db_booking.id,
            "client_secret": payment_intent.client_secret,
            "pricing": pricing
        }

    except Exception as e:
        await lock.release()
        raise


@app.post("/api/bookings/{booking_id}/confirm")
async def confirm_booking(booking_id: UUID):
    """Confirm booking after successful payment."""

    booking = await get_booking(booking_id)
    if not booking or booking.status != "reserved":
        raise HTTPException(400, "Invalid booking state")

    # Verify payment succeeded
    payment_intent = await stripe.PaymentIntent.retrieve(booking.payment_intent_id)
    if payment_intent.status != "succeeded":
        raise HTTPException(400, "Payment not completed")

    # Update to confirmed
    await update_booking_status(booking_id, "confirmed", payment_status="paid")

    # Release calendar lock (dates now permanently blocked)
    lock_key = f"calendar:lock:{booking.property_id}"
    await redis.delete(lock_key)

    # Emit event for channel sync
    await emit_event("booking.created", booking, source="direct")

    # Send confirmation email
    await send_booking_confirmation(booking)

    return {"status": "confirmed", "booking_id": booking_id}
```

### 7.3 Booking Lifecycle States

```
                                    ┌─────────────┐
                                    │   INQUIRY   │ (Optional)
                                    │  (No hold)  │
                                    └──────┬──────┘
                                           │ Convert to reservation
                                           ▼
┌───────────────────────────────────────────────────────────────────────┐
│                              RESERVED                                  │
│                     (Dates held, payment pending)                      │
│                                                                        │
│  • Calendar lock active (10 min timeout)                              │
│  • Stripe PaymentIntent created                                       │
│  • Guest completing checkout                                          │
│                                                                        │
│  Timeout (10 min) → Release lock, cancel PaymentIntent → CANCELLED   │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │ Payment succeeded
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                             CONFIRMED                                  │
│                     (Dates permanently blocked)                        │
│                                                                        │
│  • Confirmation email sent                                            │
│  • Calendar blocked in PMS-Core                                       │
│  • Synced to all connected channels                                   │
│  • Guest can view/manage booking                                      │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │ Check-in date + guest action
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                            CHECKED_IN                                  │
│                        (Guest in property)                             │
│                                                                        │
│  • Optional: Smart lock code activated                                │
│  • Optional: Welcome message sent                                     │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │ Check-out date + guest action
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                           CHECKED_OUT                                  │
│                        (Booking completed)                             │
│                                                                        │
│  • Review request sent                                                │
│  • Cleaning task created (optional)                                   │
│  • Financial records finalized                                        │
└───────────────────────────────────────────────────────────────────────┘

                              CANCELLED
                        (At any point before check-in)
                                 │
                                 │
┌───────────────────────────────────────────────────────────────────────┐
│  • Dates released to calendar                                         │
│  • Refund processed (based on policy)                                 │
│  • Channels notified to unblock                                       │
│  • Cancellation confirmation sent                                     │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 8. Security Architecture

### 8.1 Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION FLOWS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PROPERTY OWNERS (Supabase Auth)                                │
│  ────────────────────────────────                               │
│  ┌────────┐    ┌──────────┐    ┌────────────┐                  │
│  │ Owner  │───▶│ Supabase │───▶│ JWT Token  │                  │
│  │ Login  │    │   Auth   │    │ (Access +  │                  │
│  └────────┘    └──────────┘    │  Refresh)  │                  │
│                                 └─────┬──────┘                  │
│                                       ▼                         │
│                              RLS Policies Applied               │
│                              (owner_id = auth.uid())            │
│                                                                  │
│  GUESTS (Optional Account or Guest Checkout)                    │
│  ───────────────────────────────────────────                    │
│  ┌────────┐    ┌──────────┐    ┌────────────┐                  │
│  │ Guest  │───▶│ Supabase │───▶│ JWT Token  │ (If registered) │
│  │ Signup │    │   Auth   │    │ (Limited)  │                  │
│  └────────┘    └──────────┘    └────────────┘                  │
│       OR                                                        │
│  ┌────────┐    ┌──────────┐    ┌────────────┐                  │
│  │ Guest  │───▶│ Booking  │───▶│ Magic Link │ (Email access)  │
│  │Checkout│    │  Token   │    │ (Per book) │                  │
│  └────────┘    └──────────┘    └────────────┘                  │
│                                                                  │
│  CHANNEL APIs (OAuth 2.0)                                       │
│  ────────────────────────                                       │
│  ┌────────┐    ┌──────────┐    ┌────────────┐                  │
│  │Platform│───▶│  OAuth   │───▶│ Encrypted  │                  │
│  │ OAuth  │    │  Flow    │    │  Tokens    │                  │
│  └────────┘    └──────────┘    └─────┬──────┘                  │
│                                       ▼                         │
│                           Stored in channel_connections         │
│                           (AES-256-GCM encrypted)               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Row-Level Security Policies

```sql
-- Properties: Owner isolation
CREATE POLICY "property_owner_access" ON properties
    FOR ALL USING (auth.uid() = owner_id);

-- Bookings: Owner can see all bookings for their properties
CREATE POLICY "booking_owner_access" ON bookings
    FOR ALL USING (
        property_id IN (
            SELECT id FROM properties WHERE owner_id = auth.uid()
        )
    );

-- Channel connections: Owner only
CREATE POLICY "channel_connection_owner_access" ON channel_connections
    FOR ALL USING (
        property_id IN (
            SELECT id FROM properties WHERE owner_id = auth.uid()
        )
    );

-- Guests: Can only see their own bookings
CREATE POLICY "guest_booking_access" ON bookings
    FOR SELECT USING (
        guest_id = auth.uid() OR
        property_id IN (
            SELECT id FROM properties WHERE owner_id = auth.uid()
        )
    );
```

### 8.3 Data Protection

| Data Type | Protection | Storage |
|-----------|------------|---------|
| OAuth Tokens | AES-256-GCM | `channel_connections.access_token_encrypted` |
| Guest PII | Column encryption | `guests` table with pgcrypto |
| Payment Data | Never stored | Stripe handles all card data |
| API Keys | Vault/Secrets Manager | Environment variables |
| Session Tokens | HttpOnly, Secure, SameSite | Supabase Auth |

### 8.4 GDPR Compliance

```python
# Data export endpoint
@app.get("/api/gdpr/export")
async def export_user_data(current_user: User = Depends(get_current_user)):
    """Export all user data for GDPR compliance."""

    data = {
        "user": await get_user_profile(current_user.id),
        "properties": await get_user_properties(current_user.id),
        "bookings": await get_user_bookings(current_user.id),
        "guests": await get_user_guests(current_user.id),
        "channel_connections": await get_user_connections(current_user.id, redact_tokens=True)
    }

    return StreamingResponse(
        generate_json_export(data),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=pms_data_export.json"}
    )


# Data deletion endpoint
@app.delete("/api/gdpr/delete")
async def delete_user_data(current_user: User = Depends(get_current_user)):
    """Delete all user data for GDPR right to erasure."""

    # Disconnect all channels first
    await disconnect_all_channels(current_user.id)

    # Archive bookings (legal requirement)
    await archive_bookings(current_user.id)

    # Delete personal data
    await delete_user_profile(current_user.id)
    await delete_guest_pii(current_user.id)

    # Delete Supabase Auth account
    await supabase.auth.admin.delete_user(current_user.id)

    return {"status": "deleted"}
```

---

## 9. Observability

### 9.1 Metrics

| Metric | Type | Description | Alerting |
|--------|------|-------------|----------|
| `sync_latency_seconds` | Histogram | Time from Core event to channel sync | p99 > 30s |
| `sync_error_rate` | Counter | Failed syncs per channel | > 10% / 5min |
| `booking_conversion_rate` | Gauge | Bookings / Search sessions | < 1% |
| `api_request_duration` | Histogram | API response times | p99 > 500ms |
| `calendar_lock_duration` | Histogram | Lock hold times | p99 > 60s |
| `webhook_processing_time` | Histogram | Webhook handler latency | p99 > 5s |
| `channel_api_errors` | Counter | Errors by channel & type | > 5 / min |

### 9.2 Logging

```python
# Structured logging with correlation
import structlog

logger = structlog.get_logger()

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))

    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method
    )

    logger.info("request_started")

    try:
        response = await call_next(request)
        logger.info("request_completed", status_code=response.status_code)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception as e:
        logger.error("request_failed", error=str(e))
        raise
```

### 9.3 Distributed Tracing

```python
# OpenTelemetry setup
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

async def sync_booking_to_channel(booking_id: str, channel: str):
    with tracer.start_as_current_span(
        "sync_booking",
        attributes={"booking_id": booking_id, "channel": channel}
    ) as span:
        try:
            # Sync logic
            result = await do_sync(booking_id, channel)
            span.set_attribute("sync_status", "success")
            return result
        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise
```

### 9.4 Dashboards

**Channel Manager Dashboard:**
- Sync queue depth per channel
- Sync success/failure rates (last 24h)
- Average sync latency by channel
- Circuit breaker status per channel

**Booking Funnel Dashboard:**
- Search → View → Book conversion
- Booking sources (direct vs channels)
- Revenue by channel
- Average booking value

**API Health Dashboard:**
- Request rate and error rate
- Response time percentiles
- Active connections
- Database connection pool status

---

## 10. Scalability Considerations

### 10.1 Current Target

- 1,000+ properties
- 10,000+ bookings/month
- 5 channel platforms

### 10.2 Scaling Strategy

| Component | Horizontal Scaling | Vertical Scaling |
|-----------|-------------------|------------------|
| Frontend | Vercel Edge (auto) | N/A |
| Backend API | Cloud Run (auto-scale 1-10) | Up to 4 vCPU, 8GB |
| Celery Workers | Scale by queue depth | Per worker memory |
| PostgreSQL | Read replicas | Supabase Pro (8GB+) |
| Redis | Upstash serverless | Auto-scales |

### 10.3 Database Partitioning (Future)

```sql
-- Partition bookings by year for performance
CREATE TABLE bookings_2024 PARTITION OF bookings
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE bookings_2025 PARTITION OF bookings
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

---

## Appendix A: Technology Stack Summary

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Frontend | Next.js | 14+ | SSR, App Router |
| UI Components | shadcn/ui | Latest | Design system |
| State Management | TanStack Query | 5+ | Server state |
| Backend | FastAPI | 0.110+ | REST API |
| ORM | SQLAlchemy | 2.0+ | Database access |
| Task Queue | Celery | 5+ | Background jobs |
| Database | Supabase PostgreSQL | 15+ | Primary storage |
| Cache | Redis (Upstash) | 7+ | Caching, locks |
| Auth | Supabase Auth | Latest | User authentication |
| Payments | Stripe | Latest | Payment processing |
| Monitoring | Sentry | Latest | Error tracking |
| Observability | Grafana Cloud | Latest | Metrics, logs, traces |
| Hosting (FE) | Vercel | Latest | Edge deployment |
| Hosting (BE) | Cloud Run / Fly.io | Latest | Container hosting |

---

## Appendix B: Related Documents

- [C4 Context Diagram](./c4-context.mmd)
- [C4 Container Diagram](./c4-container.mmd)
- [C4 Component Diagram](./c4-component.mmd)
- [OpenAPI Specification](./openapi-spec.yaml)
- [Sync Workflows](./sync-workflows.mmd)
- [Failure Modes Analysis](./failure-modes.md)
- [ADR-001: Backend Framework Choice](./ADRs/ADR-001-backend-framework.md)
- [ADR-002: Database Choice](./ADRs/ADR-002-database-choice.md)
- [ADR-003: Multi-Tenancy Strategy](./ADRs/ADR-003-multi-tenancy.md)
- [ADR-004: Event-Driven Sync Architecture](./ADRs/ADR-004-event-driven-sync.md)
- [ADR-005: Conflict Resolution Strategy](./ADRs/ADR-005-conflict-resolution.md)
- [ADR-006: Frontend Framework Choice](./ADRs/ADR-006-frontend-framework.md)
- [ADR-007: Direct Booking Engine Design](./ADRs/ADR-007-direct-booking-engine.md)
- [ADR-008: Observability Stack](./ADRs/ADR-008-observability.md)
