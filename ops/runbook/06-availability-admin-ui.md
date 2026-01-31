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
- **Property search**: Filter by name, internal name, or city
- **Click property row** → Deep link to property calendar tab

### Data-TestIDs (Global Overview)

- `availability-overview-page` — Page container
- `availability-overview-grid` — Timeline grid
- `availability-overview-prev` / `availability-overview-next` — Navigation
- `availability-overview-today` — Today button
- `availability-overview-search` — Search input

## API Endpoints

| Action | Endpoint | Method |
|--------|----------|--------|
| List properties | `/api/v1/properties?limit=100&is_active=true` | GET |
| Query availability | `/api/v1/availability?property_id=X&from_date=X&to_date=X` | GET |
| Create block | `/api/v1/availability/blocks` | POST |
| Get block | `/api/v1/availability/blocks/{id}` | GET |
| Delete block | `/api/v1/availability/blocks/{id}` | DELETE |

**Note**: No PATCH endpoint exists. Editing is implemented as delete + create.

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

## Smoke Test

**Location**: `backend/scripts/pms_availability_blocks_smoke.sh`

**EXECUTION LOCATION**: HOST-SERVER-TERMINAL

### Usage

```bash
# With JWT token (auto-detects property)
JWT_TOKEN="eyJabc..." ./backend/scripts/pms_availability_blocks_smoke.sh

# With explicit property ID
JWT_TOKEN="eyJabc..." PROPERTY_ID="550e8400-..." ./backend/scripts/pms_availability_blocks_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJabc..." ./backend/scripts/pms_availability_blocks_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT with admin/manager role |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |
| `PROPERTY_ID` | No | Auto-detected | Property ID to test with |

### Expected Result

```
RESULT: PASS
Summary: PASS=8, FAIL=0, SKIP=0
```

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
