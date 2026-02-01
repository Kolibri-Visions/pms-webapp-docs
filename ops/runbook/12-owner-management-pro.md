# Owner Management Pro (Admin)

This runbook chapter covers the Owner Management Pro features for administrators.

**When to use:** Managing owner profiles, invitations, commission rates, and statements.

## Overview

Owner Management Pro provides comprehensive owner administration:

1. **Owner Profiles** — Create, update, deactivate/reactivate owners
2. **Commission Configuration** — Set commission rates per owner
3. **Owner Invitations** — Invite owners via email
4. **Statements Pro** — Finalize, send via email, download PDF

**Access:** Admin/Manager role required.

## Features

### 1. Owner Profile Management

**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/owners` | List owners (with active filter) |
| POST | `/api/v1/owners` | Create owner profile |
| PATCH | `/api/v1/owners/{id}` | Update owner (incl. is_active, commission) |

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Owner email |
| `first_name` | string | First name |
| `last_name` | string | Last name |
| `is_active` | boolean | Active status (false = deactivated) |
| `commission_rate_bps` | int | Commission rate in basis points (100 = 1%) |
| `phone` | string | Phone number (owner-editable) |
| `address` | string | Address (owner-editable) |
| `notes` | string | Internal notes (staff only) |

**Deactivate/Reactivate Owner:**

```bash
# Deactivate owner
curl -X PATCH "${API}/api/v1/owners/${OWNER_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# Reactivate owner
curl -X PATCH "${API}/api/v1/owners/${OWNER_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true}'
```

### 2. Commission Configuration

Commission rates are specified in **basis points** (bps):
- 100 bps = 1%
- 1000 bps = 10%
- 1500 bps = 15%

**Set Commission Rate:**

```bash
curl -X PATCH "${API}/api/v1/owners/${OWNER_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"commission_rate_bps": 1500}'
```

Commission is automatically applied when generating statements.

### 3. Owner Invitations

**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/owners/invites` | Create invitation |
| GET | `/api/v1/owners/invites` | List invitations |
| POST | `/api/v1/owners/invites/{id}/revoke` | Revoke invitation |
| POST | `/api/v1/owners/invites/accept?token=...` | Accept invitation |

**Create Invitation:**

```bash
curl -X POST "${API}/api/v1/owners/invites" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@example.com",
    "first_name": "Max",
    "last_name": "Mustermann",
    "commission_rate_bps": 1000
  }'
```

**Invitation Flow:**
1. Admin creates invitation (email + optional details)
2. System queues email via outbox (if EMAIL_NOTIFICATIONS_ENABLED)
3. Owner receives email with accept link
4. Owner logs in and accepts invitation
5. Owner profile is created and linked to auth user

**Invitation Status:**
- `pending` — Awaiting acceptance
- `accepted` — Owner accepted
- `revoked` — Admin revoked
- `expired` — 7-day expiry passed

### 4. Statements Pro

**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/owners/{id}/statements/generate` | Generate statement |
| POST | `/api/v1/owner-statements/{id}/finalize` | Lock statement |
| GET | `/api/v1/owner-statements/{id}/pdf` | Download PDF |
| POST | `/api/v1/owner-statements/{id}/send-email` | Send via email |

**Statement Status Flow:**

```
generated → finalized → sent
```

**Finalize Statement:**

```bash
curl -X POST "${API}/api/v1/owner-statements/${STATEMENT_ID}/finalize" \
  -H "Authorization: Bearer $TOKEN"
```

**Send Statement Email:**

```bash
curl -X POST "${API}/api/v1/owner-statements/${STATEMENT_ID}/send-email" \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting

### 403 Forbidden on Owner Operations

**Symptom:** Cannot access owner endpoints

**Cause:** User does not have admin/manager role.

**Resolution:**
1. Verify user's role in `team_members` table
2. Only admin/manager can manage owners

### "Owner profile already exists"

**Symptom:** 409 Conflict when creating owner

**Cause:** Owner with same `auth_user_id` already exists in agency.

**Resolution:**
1. Search existing owners for duplicate
2. Update existing profile instead of creating new

### Commission Not Applied to Statement

**Symptom:** Statement shows 0 commission despite rate configured

**Cause:** Commission rate was set after statement generation.

**Resolution:**
1. Verify owner's `commission_rate_bps` is set
2. Re-generate statement for new period
3. Existing statements are not retroactively updated

### Invitation Email Not Sent

**Symptom:** Owner invite created but no email received

**Cause:** `EMAIL_NOTIFICATIONS_ENABLED=false` (default)

**Resolution:**
1. Check email_outbox for entry with status='skipped'
2. Enable SMTP and set `EMAIL_NOTIFICATIONS_ENABLED=true`
3. Or manually provide accept link to owner

### /owners Returns 503 After Deploy

**Symptom:** Admin UI owners page shows "Service vorübergehend nicht verfügbar" and GET `/api/v1/owners` returns HTTP 503.

**Cause:** Migration `20260201200000_owner_management_pro.sql` not applied, or applied with wrong user (ownership issue).

**Resolution:**
1. Apply migration as `supabase_admin` (table owner):
   ```bash
   # Via Supabase Studio SQL Editor (recommended)
   # Or via psql as supabase_admin user
   ```
2. Verify migration applied:
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'owners' AND column_name IN ('commission_rate_bps', 'phone', 'address', 'notes');
   ```
3. If migration is applied but still 503, check backend logs for schema drift errors.
4. Backend fallback: The list endpoint should automatically use legacy query if "pro" columns are missing. Ensure backend is deployed with latest code.

**Smoke Test:**
```bash
JWT_TOKEN="eyJ..." ./backend/scripts/pms_owners_list_smoke.sh
```

## Database Schema

### owners table (updated)

```sql
ALTER TABLE owners ADD COLUMN commission_rate_bps INT NOT NULL DEFAULT 0;
ALTER TABLE owners ADD COLUMN phone TEXT NULL;
ALTER TABLE owners ADD COLUMN address TEXT NULL;
ALTER TABLE owners ADD COLUMN notes TEXT NULL;
```

### owner_invites table (new)

```sql
CREATE TABLE owner_invites (
    id UUID PRIMARY KEY,
    agency_id UUID NOT NULL,
    email TEXT NOT NULL,
    first_name TEXT NULL,
    last_name TEXT NULL,
    commission_rate_bps INT NOT NULL DEFAULT 0,
    token_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ NOT NULL,
    created_by_user_id UUID NULL,
    accepted_at TIMESTAMPTZ NULL,
    created_owner_id UUID NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

### owner_statements table (updated)

```sql
ALTER TABLE owner_statements ADD COLUMN finalized_at TIMESTAMPTZ NULL;
ALTER TABLE owner_statements ADD COLUMN sent_at TIMESTAMPTZ NULL;
ALTER TABLE owner_statements ADD COLUMN sent_to_email TEXT NULL;
```

## Migration ohne Supabase CLI (Studio SQL Editor)

Wenn `supabase db push` nicht verfügbar ist:

### Schritte

1. **Supabase Studio öffnen**
   - Dashboard: https://supabase.com/dashboard
   - Projekt auswählen → SQL Editor

2. **Migration-Datei einfügen**
   - Inhalt von `supabase/migrations/20260201200000_owner_management_pro.sql` kopieren
   - In SQL Editor einfügen und ausführen

3. **Verifizierung**
   ```sql
   -- Check owners columns
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'owners' AND column_name IN ('commission_rate_bps', 'phone', 'address');

   -- Check owner_invites table
   SELECT to_regclass('public.owner_invites');
   ```

## Smoke Test

**Script:** `backend/scripts/pms_owner_management_pro_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_owner_management_pro_smoke.sh
```

### What It Tests

1. Health check
2. List owners (verifies commission_rate_bps field exists)
3. List owner invites endpoint
4. Statement finalize endpoint
5. Statement PDF endpoint
6. Owner dashboard endpoint
7. Owner calendar endpoint

### Expected Result

```
RESULT: PASS
Summary: PASS=X, FAIL=0, SKIP=Y
```

## Related Documentation

- [Owner Portal Pro](./13-owner-portal-pro.md) — Owner self-service portal
- [Email Notifications](./09-email-notifications.md) — Email outbox system
- [Scripts README](../../../scripts/README.md#pms_owner_management_pro_smokesh)
