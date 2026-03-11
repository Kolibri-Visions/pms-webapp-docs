# Observability

> Source of Truth: `backend/app/core/metrics.py`, `backend/app/core/event_bus.py`, `backend/app/core/logging_config.py`, `backend/app/core/exceptions.py`

## Stack-Uebersicht

| Bereich | Technologie | Status |
|---------|-------------|--------|
| Error Tracking | Sentry (sentry-sdk 2.8.0) | Aktiv |
| Metriken | Prometheus (prometheus-client 0.19.0) | Aktiv |
| Logging | structlog 24.1.0 (JSON) | Aktiv |
| Tracing | OpenTelemetry (0.43b0) | Installiert, nicht aktiviert |

## Prometheus Metriken

**Endpoint:** `GET /metrics`

### HTTP

| Metrik | Typ | Labels |
|--------|-----|--------|
| `pms_http_requests_total` | Counter | method, endpoint, status_code |
| `pms_http_request_duration_seconds` | Histogram | method, endpoint |

### Business

| Metrik | Typ | Labels |
|--------|-----|--------|
| `pms_bookings_created_total` | Counter | source, agency_id |
| `pms_active_agencies` | Gauge | — |
| `pms_active_users` | Gauge | — |

### Database Pool

| Metrik | Typ |
|--------|-----|
| `pms_db_pool_size` | Gauge |
| `pms_db_pool_free` | Gauge |
| `pms_db_pool_used` | Gauge |

### Event Bus

| Metrik | Typ | Labels |
|--------|-----|--------|
| `pms_events_emitted_total` | Counter | event_type |
| `pms_event_handler_errors_total` | Counter | event_type, handler |

## Sentry

Konfiguration via Env-Vars:

| Variable | Default | Zweck |
|----------|---------|-------|
| `SENTRY_DSN` | — | Project DSN |
| `SENTRY_ENVIRONMENT` | `development` | Environment Tag |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | 10% Sampling |

Integration: FastAPI + Celery. Headers `sentry-trace`, `baggage`, `traceparent` werden durchgereicht.

## Structured Logging (structlog)

**Datei:** `app/core/logging_config.py`

| Umgebung | Format | Output |
|----------|--------|--------|
| Production | JSON | stdout |
| Development | Colored Console | stdout |

Setup via `setup_logging(environment, log_level)` in `main.py`.

Unterdrueckte Logger: `uvicorn.access`, `httpcore`, `httpx`, `hpack`.

## Event Bus (In-Process)

**Datei:** `app/core/event_bus.py`

Synchroner In-Process Event Bus (kein Redis Streams, kein externes Queue).

### API

```python
from app.core.event_bus import event_bus

# Handler registrieren
@event_bus.on("booking.created")
async def on_booking(event):
    ...

# Event emittieren
await event_bus.emit("booking.created", {"booking_id": "..."})
```

### Features

- Wildcard-Handler: `booking.*` matcht `booking.created`, `booking.updated`, etc.
- Fire-and-Forget: Handler laufen als Background Tasks
- Error Isolation: Ein fehlender Handler stoppt andere nicht
- History: Letzte 100 Events (konfigurierbar)
- Disable/Enable: `event_bus.disable()` / `event_bus.enable()`

### Event-Types (app/core/event_types.py)

| Kategorie | Events |
|-----------|--------|
| Booking | `booking.created`, `.updated`, `.cancelled`, `.confirmed`, `.checked_in`, `.checked_out` |
| Guest | `guest.created`, `.updated`, `.deleted` |
| Property | `property.created`, `.updated`, `.deleted` |
| Pricing | `pricing.updated`, `rate_plan.created`, `rate_plan.updated` |
| Availability | `availability.updated`, `availability.blocked` |
| Team | `team.member_added`, `team.member_removed` |
| Wildcards | `*`, `booking.*`, `guest.*`, `property.*` |

## Error Handling (app/core/exceptions.py)

### Error Codes

| Code | HTTP | Klasse |
|------|------|--------|
| `BOOKING_CONFLICT` | 409 | `BookingConflictError` |
| `PROPERTY_NOT_FOUND` | 404 | `PropertyNotFoundError` |
| `NOT_AUTHORIZED` | 403 | `NotAuthorizedError` |
| `RESOURCE_NOT_FOUND` | 404 | `NotFoundException` |
| `FORBIDDEN` | 403 | `ForbiddenException` |
| `RESOURCE_CONFLICT` | 409 | `ConflictException` |
| `VALIDATION_ERROR` | 422 | `ValidationException` |
| `BAD_REQUEST` | 400 | — |
| `INTERNAL_SERVER_ERROR` | 500 | — |
| `SERVICE_UNAVAILABLE` | 503 | — |
| `DATABASE_ERROR` | 503 | — |

### Typed Exceptions

Basis: `AppError(Exception)` mit `code`, `message`, `status_code`.

```python
from app.core.exceptions import BookingConflictError

raise BookingConflictError(
    message="Property ist vom 01.01. bis 05.01. bereits gebucht"
)
```

Zusaetzlich: `NotFoundException`, `ForbiddenException`, `ConflictException`, `ValidationException`
(erben von `HTTPException`, nicht von `AppError`).

## OpenTelemetry (nicht aktiviert)

Installierte Packages:
- `opentelemetry-api==1.22.0`
- `opentelemetry-sdk==1.22.0`
- `opentelemetry-instrumentation-fastapi==0.43b0`

Keine Initialisierung in `main.py`. Kann bei Bedarf aktiviert werden.
