# Guests Management (Admin UI)

This runbook chapter covers the Admin UI for guest management (Gästeverwaltung).

**When to use:** Troubleshooting guest CRUD operations, understanding the UI flow, or verifying the guests API.

## Overview

The guests feature allows agencies to manage guest profiles with full CRUD operations:

- **List & Search** — Paginated guest list with search across name, email, phone
- **Create** — Add new guest profiles with contact info and notes
- **View** — Detail page with contact info, booking stats, and timeline
- **Edit** — Update guest information, VIP status, and blacklist status

## Page Locations

| Feature | Route | Purpose |
|---------|-------|---------|
| Guest List | `/guests` | Search and manage all guests |
| Guest Detail | `/guests/[id]` | View/edit single guest + booking history |

## Guest List Page (/guests)

### Access

Navigate to: Admin → Sidebar → "Gäste"

### Features

- **Table columns**: Name, E-Mail, Telefon, Ort, Status, Buchungen, Letzte Buchung
- **Search** (debounced 300ms): Filter by name, email, or phone
- **Pagination**: 25 guests per page
- **Row click** → Navigate to guest detail page
- **"Neuer Gast" button** → Open create modal

### Data-TestIDs

- `guests-page` — Page container
- `guests-search` — Search input
- `guests-create` — Create button
- `guests-row-{id}` — Table row for guest
- `guests-create-modal` — Create modal container
- `guests-create-first-name` / `guests-create-last-name` / `guests-create-email` — Form fields
- `guests-create-submit` — Submit button

## Guest Detail Page (/guests/[id])

### Access

Navigate to: Admin → Gäste → [Gast auswählen]

### Features

- **Contact info**: Email, phone, city, country
- **Booking stats**: Total bookings, total spent, last booking date
- **Status badges**: VIP, Gesperrt (blacklisted), Marketing OK
- **Timeline tab**: Booking history with links to booking details
- **Edit button** → Open edit modal

### Data-TestIDs

- `guest-detail-page` — Page container
- `guests-edit-{id}` — Edit button
- `guests-edit-modal` — Edit modal container
- `guests-edit-first-name` / `guests-edit-last-name` / `guests-edit-email` — Form fields
- `guests-edit-vip` / `guests-edit-blacklist` — Status checkboxes
- `guests-edit-submit` — Save button

## API Endpoints

| Action | Endpoint | Method |
|--------|----------|--------|
| List guests | `/api/v1/guests?limit=25&offset=0&q=search` | GET |
| Get guest | `/api/v1/guests/{id}` | GET |
| Create guest | `/api/v1/guests` | POST |
| Update guest | `/api/v1/guests/{id}` | PATCH |
| Get timeline | `/api/v1/guests/{id}/timeline?limit=20&offset=0` | GET |

**RBAC**: admin, manager, staff can create/update. All authenticated roles can read.

## Common Errors

### 401 Unauthorized

**Error**: "Sitzung abgelaufen. Bitte erneut anmelden."

**Cause**: JWT token expired or invalid.

**Resolution**: Log out and log in again.

### 403 Forbidden

**Error**: "Keine Berechtigung für diese Aktion."

**Cause**: User role doesn't have permission (owner/accountant trying to create/edit).

**Resolution**: Contact admin for role upgrade.

### 409 Conflict

**Error**: "Ein Gast mit dieser E-Mail existiert bereits."

**Cause**: Email address already registered for another guest in this agency.

**Resolution**: Use a different email or find and update the existing guest.

### 400 Bad Request

**Error**: "Ungültige Eingabe. Bitte überprüfen Sie die Daten."

**Cause**: Invalid field values (e.g., malformed phone number, invalid country code).

**Resolution**:
- Phone: Must be 7-15 digits, optionally starting with +
- Country: Must be 2-letter ISO code (e.g., DE, AT, CH)

## Smoke Test

**Location**: `backend/scripts/pms_guests_crud_smoke.sh`

**EXECUTION LOCATION**: HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage (requires JWT_TOKEN)
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_guests_crud_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_guests_crud_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT with admin/manager/staff role |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |

### What It Tests

1. Create guest with " - Smoke" suffix
2. List guests with search filter
3. Get guest by ID
4. Update guest (phone, notes)
5. Get guest timeline
6. Verify update persisted

### Expected Result

```
RESULT: PASS
Summary: PASS=6, FAIL=0, SKIP=0
```

### Cleanup

The smoke test creates a guest with email `smoke.test.{timestamp}@example.com`. This guest can be deleted manually via the Admin UI or left for future reference.

## Debugging

### Check API Response

```bash
API="https://api.fewo.kolibri-visions.de"
TOKEN="eyJhbG..."

# List guests
curl -sS "${API}/api/v1/guests?limit=5&offset=0" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Get single guest
GUEST_ID="123e4567-..."
curl -sS "${API}/api/v1/guests/${GUEST_ID}" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Create Test Guest

```bash
curl -sS -X POST "${API}/api/v1/guests" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "Gast - Debug",
    "email": "test.debug@example.com",
    "phone": "+49 170 1234567",
    "city": "Berlin",
    "country": "DE"
  }' | jq .
```

## Related Documentation

- [Backend Guests Routes](../../api/guests.md) — API endpoint details
- [Scripts README](../../../scripts/README.md#pms_guests_crud_smokesh) — Smoke test documentation
