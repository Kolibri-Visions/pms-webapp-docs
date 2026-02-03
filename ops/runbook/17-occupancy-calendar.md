# Belegungskalender (Occupancy Calendar) Admin UI

This runbook chapter covers the Belegungskalender feature in the Admin UI.

**When to use:** Viewing property availability across all properties, understanding booking status, checking pending requests.

## Overview

The Belegungskalender (formerly "Verfügbarkeit") provides:

1. **Multi-property timeline view** — See all properties' availability in one place
2. **Guest name display** — Booked segments show truncated guest names
3. **Pending request markers** — Amber dots indicate open booking requests
4. **3-month view** — Extended view with month headers

**Access:** All authenticated roles can view.

## Navigation / Wo finde ich das?

| Menüpunkt | Pfad | Beschreibung |
|-----------|------|--------------|
| Betrieb → Belegungskalender | `/availability` | Multi-property calendar overview |

## Features

### Timeline View

**UI Location:** Betrieb → Belegungskalender (`/availability`)

**Color Coding:**
| Color | Status | Description |
|-------|--------|-------------|
| Green (`bg-green-200`) | Frei | Available for booking |
| Amber (`bg-amber-400`) | Gesperrt | Manually blocked |
| Red (`bg-red-400`) | Belegt | Has a confirmed booking |
| Amber dot | Offene Anfrage | Pending booking request |

**View Modes:**
- **4 Wochen:** Default view, shows 28 days with guest names visible
- **3 Monate:** Extended view (84 days) with month headers and separators

### Guest Name Display

In 4-week view, booked segments show the guest's last name (truncated for privacy):
- Full tooltip on hover: "Property · Date · Status · Gast: [Name]"
- Truncated in cell: First 5 characters + "…"

**Privacy:** Names are sourced from `guests.last_name` via backend join.

### Pending Request Markers

Pending booking requests (`status = 'requested'` or `'inquiry'`) appear as:
- **4-week view:** Amber dot with count badge at request start date
- **3-month view:** Small amber dot in corner

Click shows tooltip with request details.

## API Endpoints

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| List overview | `/api/v1/availability/overview` | GET | auth |

### Query Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `from_date` | Yes | - | Start date (inclusive) |
| `to_date` | Yes | - | End date (exclusive) |
| `limit` | No | 25 | Properties per page (max 100) |
| `offset` | No | 0 | Pagination offset |
| `q` | No | - | Search by property name |
| `sort_by` | No | `name` | Sort field |
| `sort_order` | No | `asc` | Sort direction |

### Response Schema

```typescript
interface AvailabilityOverviewResponse {
  from_date: string;
  to_date: string;
  limit: number;
  offset: number;
  total: number;
  items: PropertyAvailabilityItem[];
}

interface PropertyAvailabilityItem {
  property_id: string;
  property_name: string;
  internal_name?: string;
  segments: AvailabilitySegment[];
  pending_requests: PendingRequestMarker[];
}

interface AvailabilitySegment {
  start_date: string;
  end_date: string;
  status: "free" | "blocked" | "booked";
  source: "none" | "block" | "booking";
  label?: string;  // Guest last name for bookings, reason for blocks
  booking_id?: string;
  block_id?: string;
}

interface PendingRequestMarker {
  booking_id: string;
  check_in: string;
  check_out: string;
  guest_name?: string;
  status: string;
}
```

## Verification (PROD)

### Deploy Verification

```bash
# HOST-SERVER-TERMINAL
source /root/.pms_env
export API_BASE_URL="https://api.fewo.kolibri-visions.de"

# 1. Verify deploy
EXPECT_COMMIT=<sha> ./backend/scripts/pms_verify_deploy.sh

# 2. Get JWT token
export JWT_TOKEN="$(curl -k -sS -X POST "${SB_URL}/auth/v1/token?grant_type=password" \
  -H "apikey: ${SB_ANON_KEY}" \
  -H "Content-Type: application/json" \
  --data-binary "$(jq -nc --arg e "$SB_EMAIL" --arg p "$SB_PASSWORD" '{email:$e,password:$p}')" \
  | jq -r '.access_token // empty')"

# 3. Run smoke test
JWT_TOKEN="${JWT_TOKEN}" ./backend/scripts/pms_occupancy_calendar_smoke.sh

echo "occupancy_calendar_rc=$?"
```

### Quick API Test

```bash
# Get availability overview (4 weeks)
FROM=$(date +%Y-%m-%d)
TO=$(date -v+28d +%Y-%m-%d)

curl -sS \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  "${API_BASE_URL}/api/v1/availability/overview?from_date=${FROM}&to_date=${TO}&limit=5" \
  | jq '.items[0]'
```

## Troubleshooting

### Guest Names Not Showing

**Symptom:** Booked segments appear but no guest name in tooltip.

**Cause:** Booking has no linked guest, or guest has no `last_name`.

**Resolution:**
1. Check booking in database: `SELECT guest_id FROM bookings WHERE id = '<booking_id>'`
2. If `guest_id` is NULL, the booking was created without a guest link
3. If guest exists, check `guests.last_name` is not NULL

### Pending Requests Not Showing

**Symptom:** Known pending requests don't appear as amber markers.

**Cause:** Request status is not `requested` or `inquiry`, or dates don't overlap view range.

**Resolution:**
1. Check booking status: `SELECT status FROM bookings WHERE id = '<booking_id>'`
2. Verify dates overlap with current view range
3. Only status='requested' or 'inquiry' appear as pending markers

### 3-Month View Performance

**Symptom:** Slow load times on 3-month view with many properties.

**Cause:** Large DOM grid with 84 days × N properties.

**Resolution:**
1. Use search filter to reduce properties
2. Pagination limits to 25 properties by default
3. Consider narrower date range if needed

## Smoke Test

**Script:** `backend/scripts/pms_occupancy_calendar_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_occupancy_calendar_smoke.sh
```

### What It Tests

1. **Health check:** GET /health → HTTP 200
2. **Availability overview:** GET /api/v1/availability/overview → HTTP 200
3. **Guest display name:** Check for `label` in booked segments
4. **Pending requests:** Check for `pending_requests` field in response

### Expected Result

```
RESULT: PASS
Summary: PASS=3, FAIL=0, SKIP=1
```

Note: SKIP is acceptable when no bookings or pending requests exist in the date range.

## Related Documentation

- [Availability API](../../api/availability.md) — Block management
- [Booking Requests](./11-booking-requests.md) — Request workflow
