# Authentication & Authorization Operations

**When to use:** JWT token issues, apikey header problems, CORS errors, fresh token generation.

---

## Table of Contents

- [Token Validation (apikey Header)](#token-validation-apikey-header)
- [Fresh JWT (Supabase)](#fresh-jwt-supabase)
- [CORS Errors (Admin Console Blocked)](#cors-errors-admin-console-blocked)
- [Booking Requests Approve/Decline](#booking-requests-approvedecline)

---

## Golden Commands

```bash
# Get fresh JWT token
TOKEN="$(./backend/scripts/get_fresh_token.sh)"

# Test token with API
curl -H "Authorization: Bearer $TOKEN" \
  https://api.fewo.kolibri-visions.de/api/v1/me

# Test CORS preflight
curl -X OPTIONS https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Origin: https://admin.fewo.kolibri-visions.de" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" -v

# Test Supabase auth (requires both headers)
curl -X GET "https://sb-pms.kolibri-visions.de/auth/v1/user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "apikey: $ANON_KEY"
```

---

## Token Validation (apikey Header)

### Symptom

- JWT token fetched successfully (200 from Supabase auth)
- API requests with `Authorization: Bearer <token>` return `401 Unauthorized`
- Logs show: `"Invalid JWT"` or `"Unauthorized"`

### Root Cause

**IMPORTANT: apikey header scope depends on which service you're calling:**

1. **Supabase Kong endpoints** (e.g., `https://sb-pms.../auth/v1/...`) require **two headers**:
   - `Authorization: Bearer <jwt>`
   - `apikey: <anon_key>`

2. **PMS Backend API** (e.g., `https://api.fewo.../api/v1/...`) requires **only**:
   - `Authorization: Bearer <jwt>`
   - **NO apikey header needed**

**Why does Supabase Kong require both?**
- `Authorization` header contains user's JWT (specific user identity)
- `apikey` header contains project's anon key (project identification for rate limiting/routing)

**Why doesn't PMS Backend need apikey?**
- PMS Backend validates JWT directly using the JWT_SECRET
- No Kong gateway in front of PMS Backend
- apikey is only needed for Supabase services

### Verify

```bash
# Test Supabase Kong endpoint (requires both headers)
# Example: Fetch current user profile
curl -X GET "https://sb-pms.kolibri-visions.de/auth/v1/user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "apikey: $ANON_KEY"
# Returns: 200 OK (user profile)

# Test without apikey (FAILS on Kong)
curl -X GET "https://sb-pms.kolibri-visions.de/auth/v1/user" \
  -H "Authorization: Bearer $TOKEN"
# Returns: 401 Unauthorized

# Test PMS Backend API (only Authorization needed)
curl -X GET "https://api.fewo.kolibri-visions.de/api/v1/properties?limit=1" \
  -H "Authorization: Bearer $TOKEN"
# Returns: 200 OK (no apikey needed)
```

### Fix

**For Supabase Kong API Clients:**

When calling Supabase services (auth, storage, etc.), include both headers:

```python
# Python example - Supabase Kong endpoint
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "apikey": anon_key,  # Required for Kong
    "Content-Type": "application/json"
}
response = requests.get(f"{supabase_url}/auth/v1/user", headers=headers)
```

**For PMS Backend API Clients:**

When calling PMS Backend, only Authorization header is needed:

```python
# Python example - PMS Backend API
headers = {
    "Authorization": f"Bearer {jwt_token}",
    # NO apikey needed
    "Content-Type": "application/json"
}
response = requests.get(f"{api_url}/api/v1/properties", headers=headers)
```

**For Smoke Scripts:**

Our smoke scripts call both:
- Supabase Kong for auth (`fetch_token()` includes apikey)
- PMS Backend API for tests (only Authorization header)

### Prevention

- Document apikey requirement in API docs
- Add example requests showing both headers
- Test authentication flow in CI/CD

---

## Fresh JWT (Supabase)

### Quick Token Generation

Use the `get_fresh_token.sh` helper script to obtain Supabase JWT tokens for testing, debugging, or manual API calls:

```bash
# Get token to variable
TOKEN="$(./backend/scripts/get_fresh_token.sh)"

# Export to environment
source <(./backend/scripts/get_fresh_token.sh --export)

# Verify token metadata
./backend/scripts/get_fresh_token.sh --check

# Test token against /auth/v1/user
./backend/scripts/get_fresh_token.sh --user
```

**Required environment variables:**
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SB_EMAIL` - User email for authentication
- `SB_PASSWORD` - User password for authentication
- `SB_URL` (optional) - Supabase URL (defaults to https://sb-pms.kolibri-visions.de)

**Exit codes:**
- `0` - Success
- `1` - Missing required environment variables
- `2` - Authentication failed (invalid credentials)
- `3` - Empty or invalid JSON response
- `4` - Token verification failed (--user flag)

For detailed usage, integration examples, and troubleshooting, see **[backend/scripts/README.md - Get Fresh JWT Token](../scripts/README.md#get-fresh-jwt-token-get_fresh_tokensh)**.

---

## CORS Errors (Admin Console Blocked)

### Symptom

- Admin UI at `https://admin.fewo.kolibri-visions.de` shows CORS error in browser console
- Browser error: `Access to fetch at 'https://api.fewo.kolibri-visions.de/...' has been blocked by CORS policy`
- Preflight request (OPTIONS) fails with missing `Access-Control-Allow-Origin` header
- API returns 403 or connection refused for cross-origin requests

### Root Cause

CORS (Cross-Origin Resource Sharing) middleware not configured to allow admin console origin:
- Default CORS origins only include localhost (development)
- Production domains not added to `ALLOWED_ORIGINS` environment variable
- Missing `Authorization` header in allowed headers (rare, default allows all)

### Verify

Check current CORS configuration:

```bash
# Check environment variable on backend container
docker exec pms-backend env | grep ALLOWED_ORIGINS
# Should show: ALLOWED_ORIGINS=https://admin.fewo.kolibri-visions.de,https://fewo.kolibri-visions.de,...

# Or check backend logs on startup for CORS origins
docker logs pms-backend | grep -i cors
```

Test CORS preflight manually:

```bash
# Send OPTIONS preflight request
curl -X OPTIONS https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Origin: https://admin.fewo.kolibri-visions.de" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  -v

# Should return:
# Access-Control-Allow-Origin: https://admin.fewo.kolibri-visions.de
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH
# Access-Control-Allow-Headers: *
```

### Fix

**Option 1: Set Environment Variable** (Recommended)

Add `ALLOWED_ORIGINS` to backend environment:

```bash
# In Coolify or deployment config
ALLOWED_ORIGINS=https://admin.fewo.kolibri-visions.de,https://fewo.kolibri-visions.de,http://localhost:3000
```

Restart backend:

```bash
docker restart pms-backend
```

**Option 2: Update Default in Code** (Already Done)

The default in `backend/app/core/config.py` now includes:
- `https://admin.fewo.kolibri-visions.de` (admin console)
- `https://fewo.kolibri-visions.de` (public site)
- `http://localhost:3000` (local dev)

If env var is not set, these defaults will be used.

### Prevention

- Always include admin and frontend origins in `ALLOWED_ORIGINS`
- Test CORS with `curl -X OPTIONS` before deploying frontend changes
- Document required origins in deployment checklist

---

## Booking Requests Approve/Decline

### Symptom

- Admin UI "Genehmigen" (Approve) or "Ablehnen" (Decline) buttons return error
- HTTP 409 Conflict when trying to approve/decline
- HTTP 422 Validation Error on decline action

### Root Cause

**409 Conflict** - Invalid state transition:
- Request already approved/declined (idempotent - same response returned)
- Trying to approve a cancelled request
- Trying to decline an already confirmed request

**422 Validation Error** - Missing required fields:
- Decline requires `decline_reason` field (non-empty string)

### Verify

```bash
# Check current status of booking request
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>"

# Test approve (only for requested/under_review status)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"internal_note": "Approved via ops"}' \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>/approve"

# Test decline (requires decline_reason)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decline_reason": "Property unavailable", "internal_note": "Declined via ops"}' \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>/decline"
```

### Valid State Transitions

| From Status | Approve → | Decline → |
|-------------|-----------|-----------|
| `requested` | `confirmed` | `declined` |
| `under_review` | `confirmed` | `declined` |
| `confirmed` | ❌ (already approved) | ❌ (cannot decline) |
| `declined` | ❌ (cannot approve) | ❌ (already declined) |
| `cancelled` | ❌ (cannot approve) | ❌ (cannot decline) |

### Smoke Test

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh
# Expected: Test Results: 6/6 passed
```

### Troubleshooting: Approve Returns 409 but GET Shows status=requested

**Symptom**
- Smoke test passes Test 2 (approve returns 409 "idempotent")
- Test 3 fails: GET shows status=requested instead of confirmed

**Root Cause**
Inconsistent DB state: `confirmed_at` is set (booking was previously approved) but `status` is still "requested". This can happen from:
- Partial transaction commit during previous approval
- Manual DB fixes that updated confirmed_at but forgot status
- Migration issues

**Fix**
The approve endpoint now includes healing logic (commit 2026-01-29):
- Detects: `confirmed_at IS NOT NULL AND status != 'confirmed'`
- Heals: Updates status to 'confirmed'
- Returns: 200 with message "Booking request already approved (idempotent, state healed)"

**Verify Healing**
```bash
# Check for inconsistent state in DB
SELECT id, status, confirmed_at
FROM bookings
WHERE confirmed_at IS NOT NULL AND status != 'confirmed' AND deleted_at IS NULL;

# Test healing via API
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>/approve"
# Should return 200 with "state healed" in message

# Verify healed state
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>"
# Should show status=confirmed
```

### Troubleshooting: Approve Idempotent but GET Shows status=requested (inventory_ranges exists)

**Symptom**
- Approve returns 409 (smoke interprets as "idempotent")
- GET shows status=requested instead of confirmed
- There's an active `inventory_ranges` entry for this booking

**Root Cause**
The booking was previously "activated" (via booking_service or channel manager) which created an `inventory_ranges` entry with state='active', but the `bookings.status` wasn't updated to 'confirmed'. This can happen from:
- Partial transaction failure
- booking_service creating inventory_ranges but bookings.status update failing
- Manual DB intervention

**Fix**
The approve endpoint now checks for inventory_ranges evidence BEFORE the UPDATE (commit 2026-01-29):
- Detects: `inventory_ranges` entry with `kind='booking'`, `source_id=<booking_id>`, `state='active'`
- Heals: Updates bookings.status to 'confirmed', sets confirmed_at if null
- Returns: 200 with message "Booking request already approved (idempotent, state healed from inventory)"

**Verify Healing**
```bash
# Check for inventory_ranges evidence
SELECT ir.source_id, ir.state, b.status, b.confirmed_at
FROM inventory_ranges ir
JOIN bookings b ON b.id = ir.source_id
WHERE ir.kind = 'booking' AND ir.state = 'active' AND b.status = 'requested';

# Test healing via API
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>/approve"
# Should return 200 with "inventory" in message

# Verify healed state
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>"
# Should show status=confirmed
```

### Troubleshooting: Approve Returns 409 but GET Shows status=requested (related booking exists)

**Symptom**
- Approve returns 409 (interpreted as "idempotent" by smoke)
- GET shows status=requested instead of confirmed
- Exclusion constraint fires because there's an overlapping confirmed booking

**Root Cause**
A related booking exists for the same guest/property/dates that's already confirmed. This can happen when:
- Channel manager created a booking from a different source
- The request was manually approved via DB but status wasn't updated
- A separate booking flow created a confirmed booking

**Fix**
The approve endpoint now performs comprehensive healing (commit 2026-01-29):

**5 Evidence Types Checked:**
1. `confirmed_at` is set but status != confirmed
2. Status is already confirmed (no healing needed)
3. `approved_booking_id` points to a confirmed booking
4. `inventory_ranges` entry exists with state='active'
5. Related confirmed booking exists (same guest/property/dates)

**Healing Behavior:**
- Returns HTTP 200 (not 409) with status=confirmed
- Message includes evidence type: "healed: confirmed_at_set", "healed: related_booking_confirmed", etc.
- Subsequent GET shows status=confirmed

**Verify Healing**
```bash
# Check for related bookings in DB
SELECT b1.id AS request_id, b1.status AS request_status,
       b2.id AS related_id, b2.status AS related_status
FROM bookings b1
JOIN bookings b2 ON b1.property_id = b2.property_id
                AND b1.guest_id = b2.guest_id
                AND b1.check_in = b2.check_in
                AND b1.check_out = b2.check_out
                AND b1.id != b2.id
WHERE b1.status = 'requested' AND b2.status = 'confirmed';

# Test healing via API
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>/approve"
# Should return 200 with "healed" in message

# Verify healed state
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>"
# Should show status=confirmed
```

---

### Troubleshooting: Approve Returns HTTP 500 "Database error occurred"

**Symptom**
- POST /api/v1/booking-requests/{id}/approve returns HTTP 500
- Error detail: "Database error occurred" (generic)
- Booking status remains unchanged

**Root Cause**
The approve endpoint encountered a PostgresError that wasn't properly mapped:

1. **CHECK constraint violation** - Status value 'requested' or 'confirmed' not in allowed list
2. **Schema drift** - `approved_booking_id` column doesn't exist in PROD
3. **Other constraint violation** - FK, unique, or exclusion constraint

**Fix**

**Step 1: Check if migration is pending**
```bash
# List applied migrations
supabase migration list

# Check if 20260129000000_fix_bookings_status_constraint_for_requested.sql exists
ls -la supabase/migrations/ | grep 20260129
```

**Step 2: Apply migration if missing**
```bash
# Apply the migration
supabase db push

# Or manually run on PROD database:
psql $DATABASE_URL -f supabase/migrations/20260129000000_fix_bookings_status_constraint_for_requested.sql
```

**Step 3: Verify constraint allows 'requested'**
```sql
-- Check current CHECK constraint
SELECT con.conname, pg_get_constraintdef(con.oid)
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
WHERE rel.relname = 'bookings'
  AND con.contype = 'c'
  AND pg_get_constraintdef(con.oid) ILIKE '%status%';

-- Should show: status IN ('inquiry', 'pending', 'requested', 'confirmed', ...)
```

**Step 4: Verify approved_booking_id column exists**
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'bookings' AND column_name = 'approved_booking_id';

-- Should return 1 row with uuid type
```

**Step 5: Retry the approve**
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>/approve"
# Should return 200 with status=confirmed
```

**Error Code Reference (P2.21.4.8d)**

| HTTP Code | Error Code | Meaning |
|-----------|------------|---------|
| 422 | CHECK_VIOLATION | Status value not allowed by constraint |
| 422 | FK_VIOLATION | Referenced record doesn't exist |
| 409 | UNIQUE_VIOLATION | Duplicate record conflict |
| 503 | SCHEMA_DRIFT | Column/table missing (migration pending) |
| 500 | DB_ERROR | Other database error (check logs) |

---
