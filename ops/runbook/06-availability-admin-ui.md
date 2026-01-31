# Availability / Sperrzeiten (Admin UI)

This runbook chapter covers the Admin UI for availability management (Sperrzeiten/blocking dates).

## Overview

The Availability page (`/availability`) allows staff to manage property availability blocks:
- View availability calendar with bookings and blocks
- Create, edit, and delete availability blocks (Sperrzeiten)
- Navigate between months
- Select properties to view

## Page Location

- **Admin UI Route**: `/availability`
- **Navigation**: Sidebar → "Verfügbarkeit"
- **Roles**: All authenticated roles can view; admin, manager, owner can edit

## Features

### Calendar View
- Month grid showing availability status per day
- Color coding:
  - **Gray (bg-gray-50)**: Available - can be blocked
  - **Amber (bg-amber-100)**: Blocked (Sperrzeit)
  - **Blue (bg-blue-100)**: Booked (existing booking)
- Today highlighted with blue ring
- Click available day → Create block modal
- Click blocked day → Edit block modal

### Property Selector
- Dropdown of all active properties
- Auto-selects first property on load
- Shows property name and internal name

### Month Navigation
- Previous/Next month buttons
- "Heute" button to jump to current month
- Refresh button to reload data

### Blocks List
- List of all blocks in the current month
- Shows date range and reason
- Click to edit

## API Endpoints Used

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

**Cause**: Attempting to create a block that overlaps with an existing block or booking.

**Resolution**:
1. Check the calendar for existing blocks/bookings in the date range
2. Adjust the date range to avoid overlap
3. Delete the conflicting block first if needed

### 401 Unauthorized
**Error**: "Sitzung abgelaufen. Bitte melden Sie sich erneut an."

**Cause**: JWT token expired or invalid.

**Resolution**: Log out and log in again to refresh the session.

### 403 Forbidden
**Error**: "Keine Berechtigung für diese Aktion."

**Cause**: User role doesn't have permission to create/delete blocks.

**Resolution**: Contact an admin to grant appropriate permissions. Only admin, manager, and owner roles can modify blocks.

### 400 Bad Request
**Error**: "Das Enddatum muss nach dem Startdatum liegen."

**Cause**: end_date is not after start_date.

**Resolution**: Ensure end_date is at least one day after start_date. Note that end_date is exclusive (the last blocked day is the day before end_date).

## Smoke Test

**Location**: `backend/scripts/pms_availability_blocks_smoke.sh`

**EXECUTION LOCATION**: HOST-SERVER-TERMINAL

### Usage

```bash
# With JWT token (auto-detects property)
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_availability_blocks_smoke.sh

# With explicit property
JWT_TOKEN="eyJhbG..." PROPERTY_ID="550e8400-..." ./backend/scripts/pms_availability_blocks_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJabc..." ./backend/scripts/pms_availability_blocks_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT token with admin/manager role |
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
# Query availability for a property
API="https://api.fewo.kolibri-visions.de"
TOKEN="eyJabc..."
PROPERTY_ID="550e8400-..."

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
    "reason": "Test Block"
  }' | jq .
```

### Delete a Block

```bash
BLOCK_ID="123e4567-..."
curl -sS -X DELETE "${API}/api/v1/availability/blocks/${BLOCK_ID}" \
  -H "Authorization: Bearer $TOKEN"
# Expect HTTP 204 No Content
```

## Data-TestIDs (QA)

The page includes stable data-testids for automated testing:

| Element | data-testid |
|---------|-------------|
| Page container | `availability-page` |
| Property selector | `availability-property-select` |
| Previous month button | `availability-month-prev` |
| Next month button | `availability-month-next` |
| Create block button | `availability-create-block` |
| Block list item | `availability-block-item-{id}` |
| Modal container | `availability-modal` |
| Save button | `availability-save` |
| Delete button | `availability-delete` |

## Related Documentation

- [Backend Availability Router](../../api/availability.md) - API endpoint details
- [Phase 21 — Availability Hardening](../runbook.md#phase-21--availability-hardening-verification) - Original availability API implementation
- [Scripts README](../../../scripts/README.md#pms_availability_blocks_smokesh) - Smoke test documentation
