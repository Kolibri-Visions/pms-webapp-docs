# Channel Manager Architecture

**Purpose**: Document Channel Manager design (adapters, sync engine, feature gating)

**Audience**: Backend developers, architects

**Source of Truth**: `backend/app/channel_manager/` directory structure

---

## Overview

The Channel Manager enables multi-channel synchronization (Airbnb, Booking.com, etc.) with a **pluggable adapter pattern**.

**Status**: Implemented but **disabled by default** (`CHANNEL_MANAGER_ENABLED=false`)

**Feature Flag**: `CHANNEL_MANAGER_ENABLED` (default: `false`)
- If `true`: Channel Manager module imported and endpoints mounted
- If `false`: Channel Manager module NOT imported (disabled)

**Where Used**: `backend/app/modules/bootstrap.py:86-94`

---

## Architecture Components

### 1. Adapters (Pluggable Pattern)

**Location**: `backend/app/channel_manager/adapters/`

**Purpose**: Channel-specific integration logic (API calls, data mapping, auth)

**Components**:
- **Base Adapter** (`adapters/base_adapter.py`): Abstract interface all adapters must implement
- **Airbnb Adapter** (`adapters/airbnb/adapter.py`): Airbnb-specific implementation
- **Adapter Factory** (`adapters/factory.py`): Factory pattern for adapter selection

**Example**:
```python
# Factory selects adapter based on channel type
adapter = AdapterFactory.get_adapter(channel_type="airbnb")
result = await adapter.sync_availability(property_id, date_range)
```

---

### 2. Sync Engine

**Location**: `backend/app/channel_manager/core/sync_engine.py`

**Purpose**: Orchestration of sync operations (pull/push availability, bookings, pricing)

**Responsibilities**:
- Coordinate adapter calls
- Handle sync scheduling (Celery tasks)
- Manage sync state (sync logs, conflict resolution)

**Pattern**: Async sync operations via Celery workers

---

### 3. Resilience Components

#### Rate Limiter

**Location**: `backend/app/channel_manager/core/rate_limiter.py`

**Purpose**: Prevent API throttling from channel APIs (e.g., Airbnb rate limits)

**Strategy**: Token bucket or sliding window (check implementation)

#### Circuit Breaker

**Location**: `backend/app/channel_manager/core/circuit_breaker.py`

**Purpose**: Protect against downstream channel API failures (fail fast, auto-recovery)

**States**:
- **Closed**: Normal operation (requests pass through)
- **Open**: Circuit tripped (requests fail fast, no API calls)
- **Half-Open**: Testing recovery (limited requests allowed)

---

### 4. Webhooks

**Location**: `backend/app/channel_manager/webhooks/handlers.py`

**Purpose**: Handle inbound events from channel APIs (booking created, availability changed, etc.)

**Pattern**: FastAPI router with webhook endpoints (e.g., `/webhooks/airbnb`)

**Security**: Webhook signature validation (check `backend/tests/security/test_webhook_signature.py`)

---

### 5. Monitoring & Metrics

**Location**: `backend/app/channel_manager/monitoring/metrics.py`

**Purpose**: Track sync operations (success/failure rates, latency, etc.)

**Assumed Metrics** (check implementation):
- Sync success/failure counts
- Sync duration (latency)
- API error rates per channel

---

## Directory Structure

```
backend/app/channel_manager/
├── adapters/
│   ├── __init__.py
│   ├── base_adapter.py       # Abstract adapter interface
│   ├── factory.py            # Adapter factory pattern
│   └── airbnb/
│       └── adapter.py        # Airbnb-specific implementation
├── core/
│   ├── sync_engine.py        # Sync orchestration
│   ├── rate_limiter.py       # Rate limiting
│   └── circuit_breaker.py    # Circuit breaker pattern
├── webhooks/
│   └── handlers.py           # Webhook endpoints
├── monitoring/
│   └── metrics.py            # Metrics collection
├── config.py                 # Channel Manager configuration
└── __init__.py
```

---

## Feature Gating

### CHANNEL_MANAGER_ENABLED Flag

**Default**: `false` (disabled)

**Why Disabled**:
- Channel Manager not production-ready yet
- Requires additional testing, API credentials
- Avoids accidental activation in production

**How to Enable**:
1. Set environment variable: `CHANNEL_MANAGER_ENABLED=true`
2. Restart backend service
3. Verify logs: `"Channel Manager module enabled via CHANNEL_MANAGER_ENABLED=true"`

**Related Docs**: [Feature Flags](../ops/feature-flags.md#channel_manager_enabled)

---

## Sync Strategy

**Pull Sync** (assumed, check code):
- Periodic pull from channel APIs (e.g., every 15 minutes)
- Update local database with channel data

**Push Sync** (assumed, check code):
- Push local changes to channel APIs (e.g., availability updates)
- Handle conflicts (local vs channel state)

**Conflict Resolution** (assumed, check code):
- Last-write-wins OR
- Manual conflict resolution via ops console

---

## Celery Integration

**Worker**: Channel Manager sync operations run as Celery tasks (async, background)

**Broker**: Redis (same broker as other Celery tasks)

**Tasks** (assumed, check code):
- `sync_availability_task` - Sync availability for a property
- `sync_bookings_task` - Sync bookings from channel
- `push_pricing_task` - Push pricing updates to channel

**Where**: `backend/app/channel_manager/tasks.py` (assumed, check code)

---

## Code References

**Adapters**:
- `backend/app/channel_manager/adapters/base_adapter.py` - Abstract interface
- `backend/app/channel_manager/adapters/airbnb/adapter.py` - Airbnb implementation
- `backend/app/channel_manager/adapters/factory.py` - Adapter selection

**Sync Engine**:
- `backend/app/channel_manager/core/sync_engine.py` - Orchestration logic

**Resilience**:
- `backend/app/channel_manager/core/rate_limiter.py` - Rate limiting
- `backend/app/channel_manager/core/circuit_breaker.py` - Circuit breaker

**Webhooks**:
- `backend/app/channel_manager/webhooks/handlers.py` - Webhook routes

**Monitoring**:
- `backend/app/channel_manager/monitoring/metrics.py` - Metrics

**Configuration**:
- `backend/app/core/config.py` - Zentrale Konfiguration (inkl. Channel Manager Settings)

**Module Registration**:
- `backend/app/modules/channel_manager.py` - Module definition (assumed)
- `backend/app/modules/bootstrap.py:86-94` - Conditional import

---

## Testing

**Security Tests**:
- `backend/tests/security/test_webhook_signature.py` - Webhook signature validation

**Smoke Tests**:
- `backend/tests/smoke/test_channel_manager_smoke.py` - Channel Manager smoke test

**Unit Tests** (assumed, check code):
- Adapter tests (mock API calls)
- Rate limiter tests (token bucket logic)
- Circuit breaker tests (state transitions)

---

## Related Documentation

- [Feature Flags](../ops/feature-flags.md#channel_manager_enabled) - How to enable Channel Manager
- [Module System](module-system.md) - Module registration pattern
- [Runbook](../ops/runbook.md) - Production troubleshooting (if Channel Manager issues)

---

## Future Enhancements

**Planned Channels** (check roadmap):
- Booking.com adapter
- Expedia adapter
- Vrbo adapter

**Planned Features** (check roadmap):
- Bidirectional sync (full two-way sync)
- Real-time webhooks (replace polling)
- Conflict resolution UI (ops console)

---

**Last Updated**: 2025-12-30
**Maintained By**: Backend Team
