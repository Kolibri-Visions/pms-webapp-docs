# Channel Manager & Sync Engine Architecture

## Executive Summary

The Channel Manager & Sync Engine is a critical component of the PMS-Webapp that integrates PMS-Core with 5 external booking platforms (Airbnb, Booking.com, Expedia, FeWo-direkt, Google Vacation Rentals) and maintains bidirectional synchronization of bookings, availability, and pricing.

**Key Design Principles:**
- **PMS-Core as Source of Truth**: All booking data flows through PMS-Core
- **Event-Driven Sync**: Core emits events, Channel Manager reacts
- **Idempotent Operations**: All sync operations are idempotent with deduplication
- **Resilient Design**: Rate limiting, circuit breakers, and retry mechanisms
- **Multi-Tenant Isolation**: Strict tenant separation at all layers

---

## 1. System Context

```
                    +-----------------------+
                    |    Property Owner     |
                    +-----------+-----------+
                                |
                    +-----------v-----------+
                    |   PMS-Webapp (UI)     |
                    +-----------+-----------+
                                |
+---------------------------+   |   +---------------------------+
|   Direct Booking Engine   |<--+-->|    Admin Dashboard         |
+---------------------------+       +---------------------------+
                |                               |
                v                               v
        +-----------------------------------------------+
        |              PMS-Core (FastAPI)               |
        |  - Booking Engine                             |
        |  - Availability Engine                        |
        |  - Pricing Engine                             |
        |  - Guest Management                           |
        +-------+---------------+-----------------------+
                |               |
        +-------v-------+       +-------v-------+
        |  Event Bus    |       |   Supabase    |
        | (Redis/RMQ)   |       |  PostgreSQL   |
        +-------+-------+       +---------------+
                |
        +-------v-----------------------+
        |   Channel Manager & Sync      |
        |  (Celery Workers)             |
        +--+------+------+------+-------+
           |      |      |      |
     +-----v--+ +-v--+ +-v--+ +-v--+ +-v--+
     |Airbnb  | |B.c | |Exp | |FeWo| |Goo |
     +--------+ +----+ +----+ +----+ +----+
```

---

## 2. Component Architecture

### 2.1 Channel Manager Components

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **OAuth Manager** | Manage OAuth flows, token storage, refresh | FastAPI + Redis |
| **Outbound Sync Worker** | Push availability/pricing to channels | Celery + httpx |
| **Inbound Sync Worker** | Import bookings from channels | Celery + httpx |
| **Webhook Handler** | Receive real-time updates from channels | FastAPI endpoints |
| **Polling Service** | Fallback polling for unreliable webhooks | Celery Beat |
| **Rate Limiter** | Per-platform rate limiting | Redis sliding window |
| **Circuit Breaker** | Protect against platform outages | Redis state machine |
| **Reconciliation Engine** | Daily sync verification | Celery Beat |

### 2.2 Data Flow Architecture

```
OUTBOUND FLOW (PMS-Core -> Channels):
=====================================

[PMS-Core Event]
     |
     v
[Event Bus (Redis Streams)]
     |
     v
[Outbound Sync Worker (Celery)]
     |
     +---> [Rate Limiter Check]
     |           |
     |           v
     |     [Circuit Breaker Check]
     |           |
     |           v
     +---> [Platform Adapter (Airbnb/Booking.com/etc)]
     |           |
     |           v
     +---> [Log Sync Result]
                 |
                 v
        [channel_sync_logs]


INBOUND FLOW (Channels -> PMS-Core):
====================================

[Webhook from Platform] or [Polling Result]
     |
     v
[Webhook Handler / Polling Worker]
     |
     v
[Signature Verification]
     |
     v
[Idempotency Check (Redis)]
     |
     v
[Inbound Sync Worker (Celery)]
     |
     v
[Data Mapping (Channel -> PMS Schema)]
     |
     v
[Create/Update Booking in PMS-Core]
     |
     v
[Emit Internal Event (triggers outbound to OTHER channels)]
     |
     v
[Log Sync Result]
```

---

## 3. Platform Integration Matrix

| Platform | API Type | Auth | Webhooks | Rate Limit | Sync Features |
|----------|----------|------|----------|------------|---------------|
| **Airbnb** | REST | OAuth 2.0 (Auth Code) | Yes | 10 req/s | Availability, Pricing, Bookings |
| **Booking.com** | REST + XML | OAuth 2.0 / Basic | Push Notifications | Variable | Availability, Bookings |
| **Expedia** | REST | OAuth 2.0 (Client Creds) | Limited | 50 req/s | Availability, Pricing, Bookings |
| **FeWo-direkt** | REST | OAuth 2.0 | Yes | 30 req/s | Calendar, Pricing, Instant Booking |
| **Google VR** | REST + XML | API Key / OAuth | Limited | 100 req/s | Pricing, Availability |

---

## 4. Technology Stack

### 4.1 Core Technologies

```yaml
Backend Framework: FastAPI (Python 3.11+)
Database: Supabase PostgreSQL 15+
Task Queue: Celery 5.x
Message Broker: Redis 7.x (also used for caching/locks)
Event Bus: Redis Streams (with RabbitMQ option)
HTTP Client: httpx (async)
Encryption: cryptography (Fernet)
```

### 4.2 Key Dependencies

```python
# requirements.txt (channel-manager section)
celery[redis]==5.3.4
redis==5.0.1
httpx==0.25.2
cryptography==41.0.7
pydantic==2.5.2
tenacity==8.2.3  # For retries
circuitbreaker==2.0.0  # Circuit breaker pattern
prometheus-client==0.19.0  # Metrics
structlog==23.2.0  # Structured logging
```

---

## 5. Database Schema Integration

The Channel Manager uses these existing tables from the PMS-Core schema:

### 5.1 channel_connections Table

```sql
CREATE TABLE channel_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

    channel_type TEXT NOT NULL CHECK (
        channel_type IN ('airbnb', 'booking_com', 'expedia', 'fewo_direkt', 'google', 'vrbo')
    ),

    -- OAuth credentials (ENCRYPTED at application layer)
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,

    -- Platform identifiers
    channel_property_id TEXT NOT NULL,
    channel_account_id TEXT,
    channel_listing_url TEXT,

    -- Sync configuration
    sync_enabled BOOLEAN NOT NULL DEFAULT true,
    sync_direction TEXT NOT NULL DEFAULT 'bidirectional' CHECK (
        sync_direction IN ('bidirectional', 'inbound_only', 'outbound_only')
    ),
    sync_availability BOOLEAN DEFAULT true,
    sync_pricing BOOLEAN DEFAULT true,
    sync_bookings BOOLEAN DEFAULT true,

    -- Pricing configuration
    price_adjustment_type TEXT,
    price_adjustment_value NUMERIC(10,2),

    -- Sync status
    last_sync_at TIMESTAMPTZ,
    last_successful_sync_at TIMESTAMPTZ,
    sync_frequency_minutes INT DEFAULT 15,

    -- Status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'active', 'paused', 'error', 'disconnected', 'expired')
    ),
    error_message TEXT,
    error_count INT DEFAULT 0,
    last_error_at TIMESTAMPTZ,

    -- Webhook configuration
    webhook_url TEXT,
    webhook_secret TEXT,

    UNIQUE(property_id, channel_type)
);
```

### 5.2 channel_sync_logs Table

```sql
CREATE TABLE channel_sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_connection_id UUID NOT NULL REFERENCES channel_connections(id) ON DELETE CASCADE,

    sync_type TEXT NOT NULL CHECK (
        sync_type IN (
            'booking_import', 'booking_export',
            'availability_import', 'availability_export',
            'price_import', 'price_export',
            'content_sync', 'webhook', 'full_sync'
        )
    ),

    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),

    status TEXT NOT NULL CHECK (
        status IN ('started', 'success', 'partial_success', 'failure', 'skipped')
    ),

    records_processed INT DEFAULT 0,
    records_created INT DEFAULT 0,
    records_updated INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    records_skipped INT DEFAULT 0,

    error_message TEXT,
    error_details JSONB,

    request_data JSONB,
    response_data JSONB,

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INT
);
```

### 5.3 Bookings Table (Channel-Relevant Fields)

```sql
-- Within bookings table
source TEXT NOT NULL CHECK (
    source IN ('direct', 'airbnb', 'booking_com', 'expedia', 'fewo_direkt', 'google', 'other')
),
channel_booking_id TEXT,  -- External platform booking ID
channel_guest_id TEXT,    -- External platform guest ID
channel_data JSONB DEFAULT '{}'::jsonb,  -- Full channel payload

-- Unique constraint prevents duplicate imports
CONSTRAINT check_channel_id UNIQUE NULLS NOT DISTINCT (source, channel_booking_id)
```

---

## 6. Event-Driven Architecture

### 6.1 Events Emitted by PMS-Core

| Event | Trigger | Payload | Channel Manager Action |
|-------|---------|---------|----------------------|
| `booking.confirmed` | Booking created/confirmed | `{booking_id, property_id, check_in, check_out}` | Block dates on all channels |
| `booking.cancelled` | Booking cancelled | `{booking_id, property_id, check_in, check_out}` | Unblock dates on all channels |
| `booking.updated` | Dates/details changed | `{booking_id, old_dates, new_dates}` | Update availability on channels |
| `availability.updated` | Manual block/unblock | `{property_id, date_range, available}` | Sync to all channels |
| `pricing.updated` | Price change | `{property_id, date_range, new_prices}` | Sync prices to all channels |

### 6.2 Event Publishing (Redis Streams)

```python
# Event publishing from PMS-Core
import redis.asyncio as redis

async def publish_event(event_type: str, payload: dict):
    """Publish event to Redis Stream for Channel Manager consumption."""
    r = await redis.from_url("redis://localhost:6379")

    await r.xadd(
        "pms:events",
        {
            "type": event_type,
            "payload": json.dumps(payload),
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": payload.get("tenant_id")
        },
        maxlen=100000  # Keep last 100K events
    )
```

### 6.3 Event Consumption (Celery Worker)

```python
# Event consumer in Channel Manager
@celery.task
async def process_pms_event_stream():
    """Continuously consume events from Redis Stream."""
    r = await redis.from_url("redis://localhost:6379")

    last_id = "0"
    while True:
        events = await r.xread(
            {"pms:events": last_id},
            count=10,
            block=5000  # Block for 5 seconds
        )

        for stream, messages in events:
            for message_id, data in messages:
                event_type = data[b"type"].decode()
                payload = json.loads(data[b"payload"])

                # Route to appropriate handler
                await route_event(event_type, payload)

                last_id = message_id
```

---

## 7. Sync Strategies

### 7.1 Outbound Sync Strategy

```
1. Event Received (e.g., booking.confirmed)
2. Load property's channel connections (WHERE sync_enabled = true)
3. For each connection:
   a. Check rate limit (skip if exceeded)
   b. Check circuit breaker (skip if OPEN)
   c. Call platform adapter
   d. Log result (success/failure)
   e. On failure: retry with exponential backoff
```

### 7.2 Inbound Sync Strategy

```
1. Webhook Received / Polling Result
2. Verify signature (if applicable)
3. Check idempotency key (skip if already processed)
4. Map channel data to PMS schema
5. Create/update booking in PMS-Core
6. Emit internal event (triggers outbound to OTHER channels)
7. Mark as processed in Redis
```

### 7.3 Reconciliation Strategy

```
Daily Job (2 AM tenant timezone):
1. For each active channel connection:
   a. Fetch channel availability (next 90 days)
   b. Fetch PMS availability
   c. Compare and detect drift
   d. If drift > threshold:
      - Auto-correct (if confidence high)
      - Alert property owner (if ambiguous)
   e. Log reconciliation result
```

---

## 8. Resilience Patterns

### 8.1 Rate Limiting

```
Platform-specific limits:
- Airbnb: 10 requests/second/host
- Booking.com: Variable (based on tier)
- Expedia: 50 requests/second
- FeWo-direkt: 30 requests/second
- Google: 100 requests/second

Implementation: Redis sliding window counter per (channel_type, connection_id)
```

### 8.2 Circuit Breaker States

```
CLOSED  -> [5 consecutive failures] -> OPEN
OPEN    -> [60 seconds timeout]     -> HALF_OPEN
HALF_OPEN -> [2 consecutive successes] -> CLOSED
HALF_OPEN -> [1 failure]              -> OPEN
```

### 8.3 Retry Strategy

```python
# Exponential backoff with jitter
retry_delays = [
    2 + random.uniform(0, 1),   # ~2s
    4 + random.uniform(0, 2),   # ~4s
    8 + random.uniform(0, 4),   # ~8s
    16 + random.uniform(0, 8),  # ~16s
    32 + random.uniform(0, 16)  # ~32s (max)
]
```

---

## 9. Security Architecture

### 9.1 Token Encryption

```python
from cryptography.fernet import Fernet

class TokenEncryption:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, token: str) -> str:
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()
```

### 9.2 Webhook Signature Verification

Each platform has its own signature scheme:

| Platform | Signature Header | Algorithm |
|----------|-----------------|-----------|
| Airbnb | `X-Airbnb-Signature` | HMAC-SHA256 |
| Booking.com | `X-Booking-Signature` | HMAC-SHA256 |
| Expedia | `X-Expedia-Signature` | HMAC-SHA256 |
| FeWo-direkt | `X-Vrbo-Signature` | HMAC-SHA256 |
| Google | Standard OAuth verification | JWT |

### 9.3 Multi-Tenant Isolation

```
- All channel_connections scoped by tenant_id
- RLS policies enforce tenant isolation
- Worker tasks include tenant_id context
- Logs tagged with tenant_id for audit
```

---

## 10. Monitoring & Observability

### 10.1 Key Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `channel_sync_duration_seconds` | Histogram | channel_type, sync_type | Sync operation latency |
| `channel_sync_total` | Counter | channel_type, status | Total sync operations |
| `channel_api_errors_total` | Counter | channel_type, error_code | API errors by type |
| `circuit_breaker_state` | Gauge | channel_type | Current CB state (0=closed, 1=open, 2=half-open) |
| `rate_limit_hits_total` | Counter | channel_type | Rate limit exceeded count |
| `webhook_received_total` | Counter | channel_type, event_type | Webhooks received |

### 10.2 Alerting Rules

```yaml
# Prometheus Alerting Rules
groups:
  - name: channel_manager
    rules:
      - alert: HighSyncFailureRate
        expr: rate(channel_sync_total{status="failure"}[5m]) / rate(channel_sync_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Channel sync failure rate > 10%"

      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker OPEN for {{ $labels.channel_type }}"

      - alert: TokenExpiringCritical
        expr: (channel_token_expires_at - time()) < 86400
        labels:
          severity: critical
        annotations:
          summary: "OAuth token expires in < 24 hours"
```

---

## 11. File Structure

```
channel-manager/
├── channel-manager-architecture.md    # This document
├── oauth-flows.md                     # OAuth implementation for all platforms
├── conflict-resolution.md             # Conflict resolution strategies
├── monitoring.md                      # Metrics, dashboards, alerting
├── sync-workflows.mmd                 # Mermaid diagrams
├── sync-engine.py                     # Celery task implementations
├── webhook-handlers.py                # FastAPI webhook endpoints
├── rate-limiter.py                    # Distributed rate limiting
├── circuit-breaker.py                 # Circuit breaker implementation
└── platform-adapters/
    ├── base_adapter.py                # Abstract base class
    ├── airbnb_adapter.py
    ├── booking_com_adapter.py
    ├── expedia_adapter.py
    ├── fewo_direkt_adapter.py
    └── google_adapter.py
```

---

## 12. Deployment Architecture

```
Production Environment:
=======================

┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ FastAPI Pod │  │ FastAPI Pod │  │ FastAPI Pod │  (HPA)  │
│  │ (API + WH)  │  │ (API + WH)  │  │ (API + WH)  │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └─────────────┬──┴─────────────────┘               │
│                       │                                     │
│  ┌────────────────────▼────────────────────────────┐       │
│  │              Redis Cluster (HA)                  │       │
│  │  - Event Stream  - Rate Limits  - Locks         │       │
│  └──────────────────────────────────────────────────┘       │
│                       │                                     │
│  ┌─────────────┐  ┌───┴─────────┐  ┌─────────────┐         │
│  │ Celery Beat │  │ Celery Wrkr │  │ Celery Wrkr │  (HPA)  │
│  │ (Scheduler) │  │ (Outbound)  │  │ (Inbound)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
┌──────────────────────┐  ┌─────────────────────┐
│   Supabase Cloud     │  │  External Channels  │
│   (PostgreSQL)       │  │  (Airbnb, B.com..)  │
└──────────────────────┘  └─────────────────────┘
```

---

## 13. Success Criteria Checklist

| Requirement | Status | Notes |
|------------|--------|-------|
| OAuth 2.0 flows for all 5 platforms | Documented | See oauth-flows.md |
| Bidirectional sync engine | Implemented | See sync-engine.py |
| Platform-specific adapters | Implemented | See platform-adapters/ |
| Rate limiting per platform | Implemented | See rate-limiter.py |
| Circuit breaker protection | Implemented | See circuit-breaker.py |
| Conflict resolution rules | Documented | See conflict-resolution.md |
| Idempotency guarantees | Implemented | Redis + DB constraints |
| Reconciliation jobs | Implemented | Daily Celery Beat task |
| Monitoring metrics | Defined | See monitoring.md |
| Sync logging to channel_sync_logs | Implemented | All operations logged |

---

## 14. References

- [Airbnb API Documentation](https://www.airbnb.com/partner)
- [Booking.com Connectivity Partner API](https://developers.booking.com/)
- [Expedia Partner Central API](https://developers.expediagroup.com/)
- [Vrbo/FeWo-direkt API](https://developer.vrbo.com/)
- [Google Hotel Ads API](https://developers.google.com/hotels)
- [Redis Streams Documentation](https://redis.io/docs/data-types/streams/)
- [Celery Documentation](https://docs.celeryq.dev/)

---

*Document Version: 1.0.0*
*Last Updated: 2024-12-21*
*Author: channel-manager-architect*
