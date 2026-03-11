# ADR-004: Event-System — In-Process Event Bus + Celery

**Status:** Accepted (implementiert)
**Datum:** 2025-12-21

---

## Entscheidung

**In-Process Event Bus** fuer synchrone interne Events + **Celery/Redis** fuer asynchrone Background Tasks.

## Ist-Stand

### Event Bus (synchron, in-process)

**Datei:** `app/core/event_bus.py`

```python
# Handler registrieren
@event_bus.on("booking.created")
async def handle_booking_created(payload):
    await update_availability(payload["property_id"])

# Event emittieren
await event_bus.emit("booking.created", {
    "booking_id": booking.id,
    "property_id": booking.property_id
})
```

- Synchrone Ausfuehrung im selben Request-Context
- Event-History (letzte 100 Events) fuer Debugging
- Wildcard-Handler moeglich (`booking.*`, `*`)
- **Kein Redis Streams**, kein externes Message-Broker

### Event-Types (definiert)

**Datei:** `app/core/event_types.py`

| Kategorie | Events |
|-----------|--------|
| Booking | `booking.created`, `.updated`, `.cancelled`, `.confirmed`, `.checked_in`, `.checked_out` |
| Guest | `guest.created`, `.updated`, `.deleted` |
| Property | `property.created`, `.updated`, `.deleted` |
| Pricing | `pricing.updated`, `rate_plan.created`, `rate_plan.updated` |
| Availability | `availability.updated`, `availability.blocked` |
| Team | `team.member_added`, `team.member_removed` |

### Celery (asynchrone Tasks)

| Eigenschaft | Wert |
|-------------|------|
| Broker | Redis |
| Result Backend | Redis |
| Pool | Threads (default) |
| Concurrency | 4 (default) |
| Deployment | Separater Docker-Container (`Dockerfile.worker`) |
| Feature-Gate | `ENABLE_CELERY_HEALTHCHECK` |

## Was NICHT implementiert ist

- Kein Redis Streams (`XADD`/`XREAD`)
- Keine per-Channel Celery Queues (airbnb, booking_com, etc.)
- Keine Webhook-Handler Endpoints (`/webhooks/{platform}`)
- Kein Redis Distributed Locking fuer Buchungen

## Konsequenzen

- Events sind nur innerhalb eines Requests sichtbar (kein Cross-Service)
- Bei Server-Restart gehen Event-History verloren
- Celery-Tasks muessen explizit dispatched werden (kein Auto-Dispatch ueber Event Bus)
