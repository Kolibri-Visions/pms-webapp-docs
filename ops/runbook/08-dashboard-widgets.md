# Dashboard Widgets (Admin UI)

This runbook chapter covers the Admin UI Dashboard with KPI widgets.

**When to use:** Troubleshooting dashboard data, understanding metric calculations, or verifying the dashboard API.

## Overview

The dashboard provides at-a-glance KPIs for agency administrators:

- **Heute (Today)** — Check-ins and check-outs scheduled for today
- **Buchungsanfragen offen** — Pending booking requests with age buckets (SLA indicator)
- **Belegung** — Occupancy percentage for the next 30 days
- **Umsatz** — Revenue totals for current week and month

## Page Location

| Feature | Route | Purpose |
|---------|-------|---------|
| Dashboard | `/dashboard` | Main admin landing page with KPI widgets |

## Dashboard Widgets

### Today: Check-ins / Check-outs

**Calculation:**
- **Check-ins**: Count of bookings where `check_in = today` AND `status IN ('confirmed', 'checked_in')`
- **Check-outs**: Count of bookings where `check_out = today` AND `status IN ('checked_in', 'checked_out')`

**RBAC:**
- Owner role: Only sees their properties' bookings
- All other roles: Agency-wide counts

### Buchungsanfragen offen (Pending Booking Requests)

**Calculation:**
- Count of bookings where `status = 'requested'` AND `confirmed_at IS NULL`
- Age buckets based on `created_at`:
  - **0-3 days**: Green badge (fresh)
  - **4-7 days**: Yellow badge (aging)
  - **8+ days**: Red badge (urgent)

**SLA Hint:**
- If oldest pending request is >= 7 days, shows warning: "Älteste Anfrage: X Tage"

### Belegung (Occupancy)

**Calculation:**
```
occupancy_percent = (total_booked_days / total_available_days) * 100
```

Where:
- `total_booked_days`: Sum of overlapping booking days in the window (confirmed/checked_in status)
- `total_available_days`: property_count × window_days

**Window:** Default 30 days (configurable via `window_days` query param)

**Edge Cases:**
- No properties: Shows 0.0% with reason "Keine Unterkünfte vorhanden"
- Empty bookings: Shows 0.0%

### Umsatz (Revenue)

**Calculation:**
- **Week**: Sum of `total_price` where `check_in` within last 7 days AND `status IN ('confirmed', 'checked_in', 'checked_out')`
- **Month**: Sum of `total_price` where `check_in` within last 30 days AND `status IN ('confirmed', 'checked_in', 'checked_out')`

**Currency:** Always EUR (hardcoded)

**Edge Cases:**
- No revenue data: Shows "—" with hint "Noch keine Daten"

## API Endpoint

| Action | Endpoint | Method |
|--------|----------|--------|
| Get dashboard summary | `/api/v1/dashboard/summary?window_days=30` | GET |

### Response Schema

```json
{
  "today": {
    "check_ins": 0,
    "check_outs": 0
  },
  "booking_requests": {
    "pending": 0,
    "oldest_pending_days": null,
    "by_age_bucket": {
      "0-3": 0,
      "4-7": 0,
      "8+": 0
    }
  },
  "occupancy": {
    "window_days": 30,
    "percent": 0.0,
    "reason": null
  },
  "revenue": {
    "week": 0.0,
    "month": 0.0,
    "currency": "EUR"
  }
}
```

**RBAC**: admin, manager, staff, accountant, owner can access.

## Data-TestIDs

- `dashboard-page` — Page container
- `dashboard-today` — Today's check-ins/outs card
- `dashboard-requests` — Booking requests card
- `dashboard-occupancy` — Occupancy card
- `dashboard-revenue` — Revenue card

## Common Errors

### 401 Unauthorized

**Error**: "Sitzung abgelaufen. Bitte erneut anmelden."

**Cause**: JWT token expired or invalid.

**Resolution**: Log out and log in again.

### 403 Forbidden

**Error**: "Keine Berechtigung für diese Seite."

**Cause**: User role doesn't have permission.

**Resolution**: Contact admin for role assignment.

### 503 Service Unavailable

**Error**: "Service vorübergehend nicht verfügbar."

**Cause**: Database connection issue.

**Resolution**: Check database connectivity, retry after a few seconds.

## Smoke Test

**Location**: `backend/scripts/pms_dashboard_smoke.sh`

**EXECUTION LOCATION**: HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage (requires JWT_TOKEN)
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_dashboard_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_dashboard_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT with admin/manager/staff role |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |

### What It Tests

1. GET /api/v1/dashboard/summary returns HTTP 200
2. JSON has required top-level keys (today, booking_requests, occupancy, revenue)
3. Numeric fields are valid numbers
4. Occupancy percent is in valid range (0-100)

### Expected Result

```
RESULT: PASS
Summary: PASS=5, FAIL=0, SKIP=0
```

## Debugging

### Check API Response

```bash
API="https://api.fewo.kolibri-visions.de"
TOKEN="eyJhbG..."

# Get dashboard summary
curl -sS "${API}/api/v1/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN" | jq .

# With custom window
curl -sS "${API}/api/v1/dashboard/summary?window_days=60" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Verify Data Queries

```sql
-- Today's check-ins (run in DB)
SELECT COUNT(*) FROM bookings
WHERE agency_id = '<agency_id>'
  AND check_in = CURRENT_DATE
  AND status IN ('confirmed', 'checked_in')
  AND deleted_at IS NULL;

-- Pending booking requests
SELECT COUNT(*), MAX(EXTRACT(DAY FROM (CURRENT_TIMESTAMP - created_at))) as oldest
FROM bookings
WHERE agency_id = '<agency_id>'
  AND status = 'requested'
  AND confirmed_at IS NULL
  AND deleted_at IS NULL;
```

## Performance Notes

- Single API call fetches all KPIs (no N+1 storms)
- Uses efficient SQL aggregations with COUNT, SUM, FILTER
- Frontend uses AbortController to cancel in-flight requests on unmount
- No polling/auto-refresh (manual page refresh only)

## Related Documentation

- [Booking Requests Runbook](05-direct-booking-hardening.md) — For pending request workflow
- [Scripts README](../../../scripts/README.md#pms_dashboard_smokesh) — Smoke test documentation
