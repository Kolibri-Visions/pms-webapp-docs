# Channel Manager Operations

This chapter covers channel integrations, sync operations, and troubleshooting.

## Overview

The Channel Manager synchronizes availability, pricing, and bookings with external platforms (Airbnb, Booking.com, etc.).

## Key Concepts

- **Sync Engine**: Celery-based async task processing
- **Connection Health**: OAuth token validity, API connectivity
- **Conflict Resolution**: Handles overlapping bookings

## Common Operations

### Check Connection Health

```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api.fewo.kolibri-visions.de/api/v1/channel-connections/{id}/test
```

### Trigger Manual Sync

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  https://api.fewo.kolibri-visions.de/api/v1/channel-connections/{id}/sync
```

## Troubleshooting

See main runbook sections:
- Sync failures
- OAuth token refresh
- Rate limiting

---

*For detailed procedures, see the legacy runbook.md.*
