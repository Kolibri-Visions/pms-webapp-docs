# Owner Portal Pro

This runbook chapter covers the Owner Portal Pro features for property owners.

**When to use:** Troubleshooting owner self-service, dashboard, calendar, and statement access.

## Overview

Owner Portal Pro provides self-service capabilities for owners:

1. **Profile Management** — Edit own contact details
2. **Dashboard** — View KPIs and statistics
3. **Calendar** — View property bookings
4. **Statements** — View and download statements

**Access:** Owner role required (via invite acceptance).

## Features

### 1. Owner Profile (Self-Edit)

**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/owner/me` | Get own profile |
| PATCH | `/api/v1/owner/me` | Update own profile |

**Editable Fields:**
- `first_name` — First name
- `last_name` — Last name
- `phone` — Phone number
- `address` — Address

**Non-Editable Fields:**
- `email` — Managed by auth system
- `is_active` — Managed by admin
- `commission_rate_bps` — Managed by admin
- `notes` — Internal, not visible to owner

**Update Profile:**

```bash
curl -X PATCH "${API}/api/v1/owner/me" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Max",
    "last_name": "Mustermann",
    "phone": "+49 123 456789",
    "address": "Musterstraße 1, 12345 Berlin"
  }'
```

### 2. Dashboard

**Endpoint:** `GET /api/v1/owner/dashboard`

**KPIs Returned:**

| Field | Description |
|-------|-------------|
| `revenue_cents_month` | Revenue this month (cents) |
| `revenue_cents_year` | Revenue this year (cents) |
| `occupancy_rate_month` | Occupancy rate this month (0-100) |
| `upcoming_checkins` | Check-ins in next 7 days |
| `pending_statements` | Statements with status='generated' |
| `total_properties` | Total properties owned |
| `total_bookings_month` | Bookings this month |

**Example Response:**

```json
{
  "revenue_cents_month": 250000,
  "revenue_cents_year": 1500000,
  "occupancy_rate_month": 65.5,
  "upcoming_checkins": 3,
  "pending_statements": 1,
  "total_properties": 2,
  "total_bookings_month": 8
}
```

### 3. Calendar

**Endpoint:** `GET /api/v1/owner/calendar`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_date` | date | First of month | Start date |
| `to_date` | date | +31 days | End date |
| `property_id` | UUID | All | Filter by property |

**Example:**

```bash
curl "${API}/api/v1/owner/calendar?from_date=2026-02-01&to_date=2026-02-28" \
  -H "Authorization: Bearer $OWNER_TOKEN"
```

**Response:**

```json
[
  {
    "date": "2026-02-15",
    "property_id": "abc123...",
    "property_name": "Strandhaus Usedom",
    "status": "booked",
    "booking_id": "def456...",
    "guest_name": "Hans Meier"
  }
]
```

**Status Values:**
- `booked` — Confirmed/approved booking
- `pending` — Requested/under review
- `cancelled` — Cancelled/declined

### 4. Statements

**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/owner/statements` | List statements |
| GET | `/api/v1/owner/statements/{id}` | Statement detail |
| GET | `/api/v1/owner/statements/{id}/download` | Download CSV |

Owners can view their own statements and download as CSV.
PDF download available if admin has generated PDF.

## Troubleshooting

### 403 Forbidden on Owner Endpoints

**Symptom:** "Must be owner" error

**Cause:** User does not have owner role or owner profile not linked.

**Resolution:**
1. Verify user accepted owner invitation
2. Check `owners` table for `auth_user_id` match:
   ```sql
   SELECT * FROM owners WHERE auth_user_id = '<user_uuid>';
   ```
3. Verify `is_active = true`

### Owner Cannot See Dashboard/Calendar

**Symptom:** Empty dashboard or 403 error

**Cause:** Owner role not in JWT claims.

**Resolution:**
1. User must re-login after invite acceptance
2. JWT must contain `role: "owner"` and `owner_id` claim
3. Check Supabase auth user metadata

### No Properties Visible

**Symptom:** Owner sees no properties in portal

**Cause:** No properties assigned to owner.

**Resolution:**
1. Admin must assign properties to owner:
   ```bash
   curl -X PATCH "${API}/api/v1/properties/${PROPERTY_ID}/owner" \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"owner_id": "'${OWNER_ID}'"}'
   ```

### Statement Shows Wrong Commission

**Symptom:** Commission amount incorrect in statement

**Cause:** Commission rate changed after statement generation.

**Resolution:**
- Existing statements are not retroactively updated
- Generate new statement for correct period
- Or admin manually adjusts in database (not recommended)

## Owner Authentication Flow

### Invite Acceptance

```
1. Admin creates invite (POST /api/v1/owners/invites)
2. Owner receives email with token
3. Owner navigates to /owner/invite/accept?token=...
4. If not logged in: Owner logs in / signs up
5. POST /api/v1/owners/invites/accept?token=...
6. System creates owner profile with auth_user_id
7. Owner re-logins to get updated JWT claims
8. Owner can now access /owner/* endpoints
```

### JWT Claims for Owner

After accepting invite, owner's JWT should contain:

```json
{
  "role": "owner",
  "agency_id": "uuid",
  "owner_id": "uuid"
}
```

If claims are missing, user must re-authenticate.

## UI Routes

| Route | Purpose |
|-------|---------|
| `/owner` | Owner dashboard |
| `/owner/properties` | View owned properties |
| `/owner/bookings` | View bookings |
| `/owner/statements` | View/download statements |
| `/owner/profile` | Edit profile |
| `/owner/invite/accept` | Accept invitation |

## Smoke Test

The owner portal endpoints are tested as part of:

**Script:** `backend/scripts/pms_owner_management_pro_smoke.sh`

Tests verify endpoints exist and respond appropriately:
- Dashboard endpoint (expects 403 with admin token)
- Calendar endpoint (expects 403 with admin token)

For full owner portal testing, use owner JWT token.

## Related Documentation

- [Owner Management Pro](./12-owner-management-pro.md) — Admin management
- [Team Management](./11-team-management-admin-ui.md) — Similar invite pattern
