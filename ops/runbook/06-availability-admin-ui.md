# Availability / Sperrzeiten (Admin UI)

This runbook chapter covers the Admin UI for availability management (Sperrzeiten/blocking dates).

**When to use:** Troubleshooting availability calendar issues, understanding CRUD flow, or verifying blocks API.

## Overview

The availability feature has two parts:

1. **Property Calendar Tab** (`/properties/[id]/calendar`) — Per-property calendar with CRUD for blocks
2. **Global Overview** (`/availability`) — Disposition view showing all properties in a timeline

## Page Locations

| Feature | Route | Purpose |
|---------|-------|---------|
| Property Calendar | `/properties/[id]/calendar` | Manage blocks for a single property |
| Global Overview | `/availability` | View all properties in a timeline |

## Property Calendar Tab

### Access

Navigate to: Admin → Objekte → [Objekt auswählen] → Tab "Kalender"

### Features

- **Month calendar grid** showing availability status per day
- **Color coding:**
  - **Green (bg-green-50)**: Frei - can be blocked
  - **Amber (bg-amber-100)**: Gesperrt (block)
  - **Red (bg-red-100)**: Belegt (booking, read-only)
- **Today** highlighted with blue ring
- **Click free day** → Create block modal
- **Click blocked day** → Edit block modal

### CRUD Operations

| Action | Method | Notes |
|--------|--------|-------|
| Create | Click "Sperrzeit erstellen" or click free day | Opens modal |
| Edit | Click blocked day | Delete + create (no PATCH endpoint) |
| Delete | Edit modal → "Löschen" → Confirm | In-page confirm dialog |

### Data-TestIDs (Property Calendar)

- `properties-tab-calendar` — Tab link
- `property-calendar-page` — Page container
- `availability-calendar-grid` — Calendar grid
- `availability-month-prev` / `availability-month-next` — Navigation
- `availability-today` — Today button
- `availability-block-create` — Create button
- `availability-block-modal` — Modal container
- `availability-block-save` — Save button
- `availability-block-delete` — Delete button
- `availability-block-delete-confirm` — Confirm delete button

## Global Overview (/availability)

### Access

Navigate to: Admin → Sidebar → "Verfügbarkeit"

### Features

- **Timeline view**: rows = properties, columns = days
- **Color coding**: Same as property calendar
- **Date range controls**: Default 4 weeks, quick buttons for 4 Wochen / 3 Monate
- **Property search**: Filter by name, internal name, or city (debounced 300ms)
- **Pagination**: 25 properties per page
- **Click property row** → Deep link to property calendar tab
- **AbortController**: Cancels in-flight requests when user changes filters

### Data-TestIDs (Global Overview)

- `availability-overview-page` — Page container
- `availability-overview-grid` — Timeline grid
- `availability-overview-prev` / `availability-overview-next` — Navigation
- `availability-overview-today` — Today button
- `availability-overview-search` — Search input

### Bulk Endpoint (N+1 Prevention)

The global overview uses a **bulk endpoint** to fetch availability for multiple properties in a single request:

```
GET /api/v1/availability/overview?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD&limit=25&offset=0&q=search
```

This replaces the previous N+1 pattern that made one request per property.

**Response structure**:
```json
{
  "from_date": "2026-02-01",
  "to_date": "2026-03-01",
  "limit": 25,
  "offset": 0,
  "total": 42,
  "items": [
    {
      "property_id": "...",
      "property_name": "Strandhaus Sylt",
      "internal_name": "SH-001",
      "segments": [
        { "start_date": "2026-02-01", "end_date": "2026-02-08", "status": "booked", "source": "booking" },
        { "start_date": "2026-02-08", "end_date": "2026-02-15", "status": "blocked", "source": "block" },
        { "start_date": "2026-02-15", "end_date": "2026-03-01", "status": "free", "source": "none" }
      ]
    }
  ]
}
```

## API Endpoints

| Action | Endpoint | Method |
|--------|----------|--------|
| **Bulk overview** | `/api/v1/availability/overview?from_date=X&to_date=X&limit=25&offset=0&q=search` | GET |
| Query single property | `/api/v1/availability?property_id=X&from_date=X&to_date=X` | GET |
| Create block | `/api/v1/availability/blocks` | POST |
| Get block | `/api/v1/availability/blocks/{id}` | GET |
| Delete block | `/api/v1/availability/blocks/{id}` | DELETE |

**Note**: No PATCH endpoint exists. Editing is implemented as delete + create.

**Important**: The global overview (`/availability`) uses the bulk endpoint. The property calendar tab uses the single-property endpoint.

## Common Errors

### 409 Conflict

**Error**: "Konflikt: Dieser Zeitraum kollidiert mit einer bestehenden Sperrzeit oder Buchung."

**Cause**: Block overlaps with existing block or booking.

**Resolution**:
1. Check calendar for conflicts
2. Adjust date range
3. Delete conflicting block first if needed

### 401 Unauthorized

**Error**: "Sitzung abgelaufen. Bitte melden Sie sich erneut an."

**Resolution**: Log out and log in again.

### 403 Forbidden

**Error**: "Keine Berechtigung für diese Aktion."

**Resolution**: Contact admin for role permissions. Only admin, manager, owner roles can modify blocks.

### 400 Bad Request

**Error**: "Das Enddatum muss nach dem Startdatum liegen."

**Resolution**: end_date must be after start_date (end_date is exclusive).

### net::ERR_INSUFFICIENT_RESOURCES (Request Storm)

**Error**: Browser shows "net::ERR_INSUFFICIENT_RESOURCES" or "Failed to fetch" in the UI.

**Cause**: N+1 request pattern — the old implementation made one request per property (100+ properties = 100+ concurrent requests).

**Resolution**: This was fixed by the bulk overview endpoint (`/api/v1/availability/overview`). If you see this error:

1. Check DevTools Network tab — should show only 1-2 requests per page interaction, not hundreds
2. Verify the frontend is using `/api/v1/availability/overview` (not per-property `/api/v1/availability?property_id=X`)
3. If many requests are firing, the frontend may have regressed to the old N+1 pattern

**Verification**:
```bash
# Open /availability in browser
# Open DevTools → Network tab
# Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)
# Should see: 1 request to /api/v1/availability/overview
# Should NOT see: Many requests to /api/v1/availability?property_id=...
```

## Smoke Tests

**EXECUTION LOCATION**: HOST-SERVER-TERMINAL

### 1. Blocks CRUD Smoke Test

**Location**: `backend/scripts/pms_availability_blocks_smoke.sh`

Tests block create/read/delete operations.

```bash
# With JWT token (auto-detects property)
JWT_TOKEN="eyJabc..." ./backend/scripts/pms_availability_blocks_smoke.sh

# With explicit property ID
JWT_TOKEN="eyJabc..." PROPERTY_ID="550e8400-..." ./backend/scripts/pms_availability_blocks_smoke.sh
```

**Expected Result**:
```
RESULT: PASS
Summary: PASS=8, FAIL=0, SKIP=0
```

### 2. Overview Bulk Endpoint Smoke Test

**Location**: `backend/scripts/pms_availability_overview_smoke.sh`

Tests the bulk overview endpoint that prevents N+1 request storm.

```bash
# Basic usage
JWT_TOKEN="eyJabc..." ./backend/scripts/pms_availability_overview_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJabc..." ./backend/scripts/pms_availability_overview_smoke.sh
```

**Expected Result**:
```
RESULT: PASS
Summary: PASS=6, FAIL=0, SKIP=0
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT with admin/manager role |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |
| `PROPERTY_ID` | No | Auto-detected | Property ID (blocks smoke only) |

## Debugging

### Check API Response

```bash
API="https://api.fewo.kolibri-visions.de"
TOKEN="eyJabc..."
PROPERTY_ID="550e8400-..."

# Query availability for a property
curl -sS "${API}/api/v1/availability?property_id=${PROPERTY_ID}&from_date=2026-02-01&to_date=2026-03-01" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Create a Test Block

```bash
curl -sS -X POST "${API}/api/v1/availability/blocks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "'$PROPERTY_ID'",
    "start_date": "2026-02-15",
    "end_date": "2026-02-17",
    "reason": "Test Block - Smoke"
  }' | jq .
```

### Delete a Block

```bash
BLOCK_ID="123e4567-..."
curl -sS -X DELETE "${API}/api/v1/availability/blocks/${BLOCK_ID}" \
  -H "Authorization: Bearer $TOKEN"
# Expect HTTP 204 No Content
```

## Related Documentation

- [Backend Availability Router](../../api/availability.md) — API endpoint details
- [Phase 21 — Availability Hardening](../runbook.md#phase-21--availability-hardening-verification) — Original availability API
- [Scripts README](../../../scripts/README.md#pms_availability_blocks_smokesh) — Smoke test documentation
