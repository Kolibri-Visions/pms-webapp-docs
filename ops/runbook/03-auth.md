# Authentication & Authorization Operations

**When to use:** JWT token issues, apikey header problems, CORS errors, fresh token generation.

---

## Table of Contents

- [Token Validation (apikey Header)](#token-validation-apikey-header)
- [Fresh JWT (Supabase)](#fresh-jwt-supabase)
- [CORS Errors (Admin Console Blocked)](#cors-errors-admin-console-blocked)
- [Booking Requests Approve/Decline](#booking-requests-approvedecline)
- [Admin UI Tab Count Issues](#admin-ui-tab-count-issues)
- [Public Booking vs Direct Booking](#public-booking-vs-direct-booking-definitionen--datenfluss)
- [Booking Requests: Details, Export, Manuelle Buchung](#booking-requests-details-drawer-csv-export-manuelle-buchung)
- [Booking Requests: Workflow Consistency (P2.21.4.8k)](#booking-requests-workflow-consistency-p221-4-8k)
- [Booking Requests: SLA/Notifications/Filters (P2.21.4.8l)](#booking-requests-slanotificationsfilters-p221-4-8l)
- [Booking Requests: SLA/Overdue Ops-Grade Consistency (P2.21.4.8m)](#booking-requests-slaoverdue-ops-grade-consistency-p221-4-8m)
- [Booking Requests: Detail/CSV Consistency + Review Queue UX (P2.21.4.8n)](#booking-requests-detailcsv-consistency--review-queue-ux-p221-4-8n)
- [Booking Requests: Review Queue Zero + Bulk Actions (P2.21.4.8o)](#booking-requests-review-queue-zero--bulk-actions-p221-4-8o)
- [Idempotency-Key Support (P3.1)](#idempotency-key-support-p31)

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
# Expected: Test Results: 12/12 passed (RC=0)
```

**PROD-Safe Behavior (P2.21.4.8k):**
If PROD has only real booking_overlap conflicts (different guests), approve-success tests (2-3) are **skipped** instead of failed. This is valid PROD state - conflict behavior is still validated. Set `REQUIRE_APPROVE_SUCCESS=true` for strict mode (staging).

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

### Troubleshooting: Approve Returns 409 Overlap but Request Status Stays "requested"

**Symptom**
- POST /api/v1/booking-requests/{id}/approve returns HTTP 409 `booking_overlap`
- GET /api/v1/booking-requests/{id} still shows `status=requested` (not `confirmed`)
- Smoke test Test 3 fails: "Unexpected status 'requested' after approve"

**Root Cause**
The booking request overlaps with an existing confirmed booking for the SAME guest, but:
1. The old code tried to heal by setting `status='confirmed'` which triggered the exclusion constraint again
2. No healing was possible, so status remained `requested`

**Schema Reality (P2.21.4.8e)**
- PROD uses single `public.bookings` table for both bookings and booking requests
- `to_regclass('public.booking_requests')` returns NULL (table doesn't exist)
- Booking requests are rows in `bookings` with `status='requested'`
- Exclusion constraint prevents multiple confirmed bookings on same property/dates

**Fix (commit 2026-01-29)**
The approve endpoint now uses **soft healing** for overlap-same-guest:

1. **Detect same-guest overlap**: Query for existing confirmed booking with same guest_id
2. **Soft heal**: Set `confirmed_at` WITHOUT changing `status` (avoids constraint)
3. **Effective status**: API returns `status='confirmed'` based on `confirmed_at` presence
4. **List filter**: `status=requested` filter excludes rows with `confirmed_at` set

**Evidence Type in Response**
When soft-healed, response includes: `message: "healed: fulfilled_by_overlap_same_guest"`

**Verify Fix**
```bash
# Check if booking has confirmed_at set (soft-healed)
SELECT id, status, confirmed_at, internal_notes
FROM bookings
WHERE id = '<booking_request_uuid>';

# If status='requested' but confirmed_at IS NOT NULL, it's soft-healed
# API will return effective status='confirmed'

# Test with GET endpoint
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>"
# Should return status=confirmed (effective status)

# Verify not in requested list
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests?status=requested"
# Soft-healed requests should NOT appear here
```

**Effective Status Logic**
```
effective_status = 'confirmed' if (
    db_status == 'confirmed' OR
    confirmed_at IS NOT NULL OR
    approved_booking_id IS NOT NULL
) else db_status
```

---

### Legacy Single-Table Mode (booking_requests table missing)

**Context**

In PROD, `public.booking_requests` table does NOT exist. Booking requests are stored as rows in `public.bookings` with `status='requested'`.

```sql
-- Verify: booking_requests table doesn't exist
SELECT to_regclass('public.booking_requests');
-- Returns: NULL
```

**Approve Behavior**

When approving a booking request in legacy single-table mode:

1. The endpoint updates the **same row** in `bookings` table (in-place update)
2. Sets `status='confirmed'`, `confirmed_at=now()`, `approved_by=user_id`
3. Returns HTTP 200 with `message: "Booking request approved (in-place update)"`
4. `booking_id` in response equals `booking_request_id` (same row)

**No Overlap Self-Conflict**

Since we UPDATE the existing row (not INSERT a new one), the `no_double_bookings` exclusion constraint is not triggered for self-overlap.

**Smoke Test**

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh
# Expected: 6/6 passed, RC=0
```

---

### Troubleshooting: 409 booking_overlap vs 200 Idempotent Fulfillment (P2.21.4.8g)

**Context**

When approving a booking request, the endpoint may encounter an overlap conflict due to the `no_double_bookings` exclusion constraint. The behavior depends on whether the overlap is with the SAME guest or a DIFFERENT guest.

**Scenario A: Same Guest Overlap (Idempotent Fulfillment)**

If the overlapping booking is for the **same guest**:
- The request is effectively fulfilled (same person, same dates)
- API returns **HTTP 200** with `status=confirmed`
- Message includes: `"healed: fulfilled_by_overlap_same_guest"`
- The booking request is soft-healed: `confirmed_at` is set, effective status becomes `confirmed`

**Scenario B: Different Guest Overlap (Real Conflict)**

If the overlapping booking is for a **different guest**:
- This is a genuine double-booking attempt
- API returns **HTTP 409** with `conflict_type=booking_overlap`
- Message does NOT include "idempotent" or "healed"
- The booking request remains `status=requested` (not healed)

**Smoke Script Behavior (P2.21.4.8g)**

The smoke script now correctly distinguishes these cases:
1. On 409 with `conflict_type=booking_overlap` and no "healed" message → tries next candidate
2. Iterates up to 5 candidates looking for an approvable request
3. Only fails if ALL candidates have real conflicts

**Verify in Logs**

```bash
# Same guest healing (expected: 200)
grep "Soft-healing booking request" /var/log/pms/backend.log
# Real conflict (expected: 409)
grep "Real booking conflict on approve" /var/log/pms/backend.log
```

**Active Statuses in Constraint**

The `no_double_bookings` constraint applies to bookings with:
```sql
status NOT IN ('cancelled', 'declined', 'no_show')
```

This includes: confirmed, checked_in, checked_out, pending, inquiry, requested.

---

## Admin UI Tab Count Issues

**When to use:** Badge counts on Buchungsanfragen tabs ("Alle", "Neu", "Läuft bald ab", "In Bearbeitung") show inconsistent or changing values.

### Symptoms

- Switching tabs causes other tab counts to change unexpectedly
- "Alle" count equals the currently selected tab's count
- Counts flicker or show stale values

### Root Cause (Fixed in P2.21.4.8h + P2.21.4.8i)

**Phase 1 (P2.21.4.8h):** Tab counts were computed from the `requests` state, which was already filtered by the active tab.

**Phase 2 (P2.21.4.8i):** "Läuft bald ab" tab used client-side filtering on paginated results:
- Footer showed "von 168" (all total) instead of "von 3" (expiring total)
- Client filtering couldn't see items beyond the current page

### Fix Applied

**Backend (P2.21.4.8i):** Added `expiring_soon=true` query parameter to `/api/v1/booking-requests`:
- Filters to: `status IN ('requested', 'under_review')` AND deadline within 0-3 days
- Deadline = check_in - 48 hours
- Returns accurate `total` for pagination

**Frontend (P2.21.4.8h + P2.21.4.8i):**
- Tab counts fetched via lightweight parallel API calls (`limit=1`) using server-side filters
- Each tab's total comes from server response, not client-side computation
- "Läuft bald ab" tab uses `expiring_soon=true` for both list AND count
- Footer uses active tab's server-returned `total` (not "all" total)
- Race condition handling via `countsRequestId` prevents stale responses

### Manual Verification

1. Open Admin UI: https://admin.fewo.kolibri-visions.de/booking-requests
2. Note the badge counts on each tab
3. Click "Läuft bald ab" tab
4. Verify: Badge count matches table row count AND footer "von X" shows same number
5. Click each other tab and verify footer total matches that tab's badge count
6. Approve or decline a request and verify all counts refresh correctly

### Smoke Test

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh
# Test 7 validates expiring_soon filter
```

### Related Files

```
backend/app/api/routes/booking_requests.py
  - Lines 294: expiring_soon query parameter
  - Lines 341-348: Server-side expiring filter logic

frontend/app/booking-requests/page.tsx
  - Lines 75-81: stableTabCounts state
  - Lines 151-154: expiring_soon param for list fetch
  - Lines 199-246: fetchTabCounts() with parallel server calls
  - Lines 269: tabCounts = stableTabCounts assignment
```

---

## Public Booking vs Direct Booking (Definitionen + Datenfluss)

**When to use:** Understanding the difference between booking requests and direct bookings.

### Definitionen

**Public Booking (Buchungsanfrage)**
- Originates from public booking widget or external channels
- Initial status: `requested` (neu)
- Requires manual review before confirmation
- Stored in `bookings` table with `status='requested'`
- Workflow: requested → under_review (In Bearbeitung) → approved/declined

**Direct Booking (Manuelle Buchung)**
- Created directly by staff via Admin UI or API
- Initial status: `confirmed`
- No review workflow required
- Source field: `manual`
- Stored in `bookings` table with `status='confirmed'`

### Datenfluss

```
Public Booking:
  Widget → POST /api/v1/public/booking-requests → bookings(status=requested)
         → Admin Review → POST /approve → bookings(status=confirmed)

Direct Booking:
  Admin UI → POST /api/v1/bookings (source=manual) → bookings(status=confirmed)
```

### Status-Definitionen (Tab Filters)

| Tab | API Filter | DB Status | Bedeutung |
|-----|------------|-----------|-----------|
| Alle | (none) | * | All booking requests |
| Neu | status=requested | requested | New, unreviewed |
| In Bearbeitung | status=under_review | inquiry | Being reviewed |
| Läuft bald ab | expiring_soon=true | requested/inquiry + deadline ≤3d | Urgent action needed |

**Note:** "In Bearbeitung" maps to DB status `inquiry` due to legacy constraint.

---

## Booking Requests: Details Drawer, CSV Export, Manuelle Buchung

**When to use:** Admin UI /booking-requests features troubleshooting.

### Features (P2.21.4.8j)

**Details Drawer**
- Click row actions → "Details anzeigen"
- Fetches full detail from GET /api/v1/booking-requests/{id}
- Shows loading state while fetching
- Actions: "In Bearbeitung setzen" (only for status=requested), "Genehmigen", "Ablehnen"

**CSV Export**
- Button: "CSV exportieren"
- Respects active tab filter (status, expiring_soon)
- Exports ALL matching rows (not just current page)
- Filename includes tab hint: `buchungsanfragen_expiring_2026-01-29.csv`

**Manuelle Buchung**
- Button: "Manuelle Buchung"
- Opens modal with form fields: property_id, dates, guest info, price
- Creates direct booking via POST /api/v1/bookings with source=manual
- On 409: overlap conflict with existing booking

### Troubleshooting

**CSV Export Empty**
- Check: Tab filter may be too restrictive
- Check: Network/auth error (console)
- Verify: API returns 200 with proper Content-Type: text/csv

**409 Overlap on Manual Booking**
- Cause: Property already booked for the requested dates
- Check: GET /api/v1/bookings?property_id=X&check_in=Y to see conflicts
- Solution: Choose different dates or cancel conflicting booking

**"In Bearbeitung" Count Mismatch**
- Definition: status=under_review (DB: inquiry)
- Tab uses server-side filter, not client-side
- Counts fetched via parallel limit=1 API calls

### Smoke Test

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh
# Tests 8-9 validate detail endpoint and CSV export
```

---

## Booking Requests: Workflow Consistency (P2.21.4.8k)

**When to use:** Ensuring consistent behavior across booking request workflow components.

### Status Mapping (API ↔ DB)

Due to PROD database constraint, the API and DB use different status values:

| API Status | DB Status | UI Label | Meaning |
|------------|-----------|----------|---------|
| `requested` | `requested` | "Neu" | New booking request, not yet reviewed |
| `under_review` | `inquiry` | "In Bearbeitung" | Staff is reviewing the request |
| `confirmed` | `confirmed` | "Bestätigt" | Approved and confirmed |
| `cancelled` | `cancelled` | "Storniert" | Declined or cancelled |

**Key Mapping Functions (booking_requests.py):**
- `to_api_status(db_status)`: DB → API (inquiry → under_review)
- `to_db_status(api_status)`: API → DB (under_review → inquiry)
- `compute_effective_status()`: Handles soft-healed rows (confirmed_at set but status unchanged)

### Review Endpoint (/review)

**Purpose:** Transition request from `requested` to `under_review` (In Bearbeitung)

**Endpoint:** `POST /api/v1/booking-requests/{id}/review`

**Body:**
```json
{
  "internal_note": "Optional note about review"
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "under_review",
  "reviewed_at": "2026-01-29T...",
  "reviewed_by": "user_uuid",
  "message": "Booking request marked as under review"
}
```

**Valid Transitions:**
- `requested` → `under_review` ✓
- `under_review` → `under_review` ✓ (idempotent, updates note)
- `confirmed` → `under_review` ✗ (409 conflict)
- `cancelled` → `under_review` ✗ (409 conflict)

### CSV Export with UTF-8 BOM (P2.21.4.8k)

**Purpose:** Ensure Excel properly detects UTF-8 encoding for German umlauts.

**Implementation:**
```python
output = io.StringIO()
output.write('\ufeff')  # UTF-8 BOM
writer = csv.DictWriter(output, fieldnames=[...])
```

**Verification:**
```bash
# Check first 3 bytes are EF BB BF (UTF-8 BOM)
curl -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/booking-requests/export" | head -c 3 | xxd -p
# Expected: efbbbf
```

### Tab Filter Consistency

All tabs use server-side filters to ensure accurate counts:

| Tab | API Parameters | Backend Logic |
|-----|----------------|---------------|
| Alle | (none) | All non-deleted |
| Neu | `status=requested` | `status = 'requested' AND confirmed_at IS NULL` |
| In Bearbeitung | `status=under_review` | `status = 'inquiry'` (DB mapping) |
| Läuft bald ab | `expiring_soon=true` | `status IN ('requested', 'inquiry') AND deadline <= 3d` |

**Note:** "Neu" tab excludes effectively-confirmed rows (those with confirmed_at set).

### Smoke Test Coverage (Tests 10-12)

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh

# Test 10: Review endpoint (requested → under_review)
# Test 11: CSV export UTF-8 BOM detection
# Test 12: under_review filter consistency
```

### Troubleshooting

**Review Returns 409 but Status is Still "requested"**
- Check: Request may already be confirmed via another path
- Verify: `GET /api/v1/booking-requests/{id}` and check effective status
- If confirmed_at is set, effective status is "confirmed"

**CSV Opens with Garbled Characters in Excel**
- Cause: UTF-8 BOM missing or stripped
- Verify: First 3 bytes should be EF BB BF
- Fix: Check CSV export endpoint includes BOM write

**"In Bearbeitung" Count Different from Displayed Rows**
- Cause: Client/server mismatch or stale counts
- Fix: Tab counts are fetched via parallel limit=1 API calls
- Verify: Network tab shows 5 parallel requests on page load (incl. overdue)

---

## Booking Requests: SLA/Notifications/Filters (P2.21.4.8l)

**When to use:** Understanding SLA deadlines, overdue detection, and notification banners.

### Policy Endpoint

Get current SLA configuration:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/booking-requests/policy"
# Returns: {"sla_hours": 24, "expiring_soon_days": 3, "computed_at": "...", "server_now": "..."}
```

**Note (P2.21.4.8m):** The `server_now` field was added for debugging and clock-sync verification.

**Environment Variables:**
- `BOOKING_REQUEST_SLA_HOURS=24` - Hours after creation before overdue
- `BOOKING_REQUEST_EXPIRING_SOON_DAYS=3` - Days before deadline for 'expiring soon'

### SLA State Values

Each booking request has a computed `sla_state` field:

| State | Meaning | Deadline Status |
|-------|---------|-----------------|
| `on_track` | Normal processing time | deadline > now + expiring_days |
| `expiring_soon` | Approaching deadline | now < deadline <= now + expiring_days |
| `overdue` | Deadline has passed | deadline < now |
| `closed` | No action needed | Status is confirmed/cancelled/declined |

### Filter Query Parameters

| Parameter | Tab | Meaning |
|-----------|-----|---------|
| `status=requested` | Neu | Open requests not yet reviewed |
| `status=under_review` | In Bearbeitung | Under review (DB: inquiry) |
| `expiring_soon=true` | Läuft bald ab | Deadline within 0-3 days |
| `overdue=true` | Überfällig | Deadline has passed |

**Filter Combinability (P2.21.4.8m):**

When multiple filter parameters are provided, they combine using AND (intersection semantics):
- `status=requested&overdue=true` → Only overdue items with status=requested
- `expiring_soon=true&overdue=true` → Intersection (usually empty, rare edge case)
- `status=under_review&expiring_soon=true` → Under review AND expiring soon

**Example Queries:**

```bash
# Overdue requests
curl -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/booking-requests?overdue=true&limit=10"

# Expiring soon
curl -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/booking-requests?expiring_soon=true&limit=10"

# Combined filter (intersection)
curl -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/booking-requests?status=under_review&overdue=true&limit=10"
```

### Admin UI Notification Banners

Banners show in priority order (only one at a time):

1. **RED** (overdue > 0): "X Anfragen überfällig" → "Jetzt anzeigen"
2. **ORANGE** (expiring > 0): "X Anfragen laufen bald ab" → "Jetzt anzeigen"
3. **BLUE** (new > 0): "X neue Anfragen" → "Jetzt anzeigen"

Clicking CTA switches to the relevant tab.

### Smoke Test Coverage (Tests 13-15)

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh

# Test 13: Policy endpoint returns expected keys
# Test 14: Overdue filter consistency (SKIP if no overdue in PROD)
# Test 15: Tab totals diagnostic summary
```

**PROD-Safe Behavior:**
- Test 14 SKIPs if no overdue items exist (valid PROD state)
- Test 15 prints tab totals for diagnostic visibility

### Troubleshooting

**Count Mismatch Between Tabs and Table**
- Root cause: Fixed in P2.21.4.8h/i via server-side totals
- Tab counts fetched via parallel `limit=1` API calls
- Each tab uses its own server-side filter

**Overdue Tab Shows 0 but Requests Exist**
- Check: Are requests already closed (confirmed/cancelled)?
- Verify: Only open statuses (requested, inquiry) can be overdue
- Check: `confirmed_at IS NULL` filter excludes effectively-confirmed

**Banner Not Appearing**
- Cause: Counts are 0 for all priority levels
- Or: Currently viewing that tab (banner hidden when tab active)
- Verify: Network tab shows 5 parallel count requests on load

---

## Booking Requests: SLA/Overdue Ops-Grade Consistency (P2.21.4.8m)

**When to use:** Understanding combined filter semantics, SLA block in details drawer, and debugging server time.

### Policy Endpoint: server_now Field

The policy endpoint now includes `server_now` for debugging and client-server clock synchronization:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/booking-requests/policy"
# Returns: {
#   "sla_hours": 24,
#   "expiring_soon_days": 3,
#   "computed_at": "2026-01-29T21:30:00.000000Z",
#   "server_now": "2026-01-29T21:30:00.000000Z"
# }
```

Use `server_now` to verify:
- Client-server clock drift
- Timezone handling (always UTC)
- SLA computation correctness

### Combined Filter Semantics (AND/Intersection)

When multiple filter parameters are provided, they combine with AND (intersection):

| Parameters | Result |
|------------|--------|
| `status=requested&overdue=true` | Overdue items with status=requested only |
| `status=under_review&expiring_soon=true` | Expiring items under review |
| `overdue=true&expiring_soon=true` | Intersection (rare, usually empty) |

**Why this matters for Ops:**
- UI tabs use single filters (one filter per tab)
- Custom queries can combine filters for specific use cases
- Export endpoint respects combined filters

### Admin UI: SLA Block in Details Drawer

The details drawer shows an "SLA Status" block with:

- **Frist:** Decision deadline timestamp (check_in - 48h)
- **Status:** SLA state badge (on_track/expiring_soon/overdue/closed)

Badge colors:
- `on_track` → Gray
- `expiring_soon` → Orange
- `overdue` → Red
- `closed` → Green

### Admin UI: Überfällig Tab Tooltip

The "Überfällig" tab has a tooltip explaining:
> "Anfragen, deren Frist (48h vor Check-in) abgelaufen ist"
> (Requests whose deadline (48h before check-in) has expired)

### Smoke Test Coverage (Tests 16-17)

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh

# Test 16: Combined filter (overdue + under_review) returns valid JSON
# Test 17: Policy endpoint includes server_now field
```

### Troubleshooting

**server_now differs from local time by hours**
- Expected: Server uses UTC, client may use local timezone
- Verify: `date -u` on server vs local system
- Not a bug unless difference exceeds seconds

**Combined filter returns empty but individual filters have items**
- Expected: Intersection semantics means fewer matches
- Example: `overdue=true` has 5 items, `status=under_review` has 3 items, but intersection may be 0

**SLA block not appearing in drawer**
- Check: Network tab for detail endpoint response
- Verify: Response includes `decision_deadline_at` and `sla_state`
- If missing: Check backend routes compute these fields

---

## Booking Requests: Detail/CSV Consistency + Review Queue UX (P2.21.4.8n)

**When to use:** Understanding CSV export columns, detail endpoint fields, and operator workflow features.

### Detail Endpoint Fields

GET `/api/v1/booking-requests/{id}` returns all fields needed by Admin drawer:

| Field | Type | Description |
|-------|------|-------------|
| `decision_deadline_at` | string (ISO) | check_in - 48h, when decision is needed |
| `sla_state` | string | on_track, expiring_soon, overdue, closed |
| `reviewed_at` | string | Always null (not tracked separately) |
| `approved_at` | string | ISO timestamp when approved (from confirmed_at) |
| `declined_at` | string | ISO timestamp when declined (from cancelled_at) |
| `cancelled_at` | string | ISO timestamp when cancelled |

**Note:** `reviewed_at` is always null because the P1 workflow doesn't track review timestamp separately.

### CSV Export Columns

GET `/api/v1/booking-requests/export` includes these columns:

```
id, booking_reference, property_name, guest_name, guest_email,
check_in, check_out, num_adults, num_children,
status, source, total_price, currency, created_at,
decision_deadline_at, sla_state, approved_at, declined_at
```

**CSV Features:**
- UTF-8 BOM for Excel compatibility
- Respects active tab filter (status, expiring_soon, overdue)
- Exports ALL matching rows (no pagination limit in export)
- Filename includes tab hint: `buchungsanfragen_expiring_2026-01-29.csv`

### Admin UI: Request-ID Copy

The detail drawer includes a "ID kopieren" button that copies the booking request UUID to clipboard. Useful for:
- Sharing specific requests with colleagues
- Debugging API calls
- Internal notes and references

### Admin UI: Nächster Quick-Action

The "Nächster" button in the drawer opens the next actionable request:

**Priority order:**
1. Requests with `sla_state=expiring_soon`
2. Requests with `sla_state=overdue`
3. Requests with `status=requested`
4. Remaining `under_review` requests

**Workflow tip:** Use "Nächster" to process the review queue efficiently:
1. Open any request
2. Review and decide (Approve/Decline)
3. Click "Nächster" to move to next priority item
4. Repeat until "Keine weiteren Anfragen" message appears

### Smoke Test Coverage (Tests 18-19)

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh

# Test 18: Detail endpoint field completeness (decision_deadline_at, sla_state, timestamps)
# Test 19: CSV export includes SLA columns
```

### Troubleshooting

**CSV missing SLA columns**
- Check: Export endpoint at `/api/v1/booking-requests/export`
- Verify: Header row includes `decision_deadline_at`, `sla_state`, `approved_at`, `declined_at`
- If missing: Backend may not be updated (check commit)

**"Nächster" button not appearing**
- Cause: No actionable requests in current list (all confirmed/cancelled)
- Verify: Check other tabs for pending requests
- Button only shows when `status=requested` or `status=under_review`

**declined_at vs cancelled_at**
- `declined_at`: Set when request is explicitly declined (status becomes cancelled)
- `cancelled_at`: General cancellation timestamp (may be same value)
- Both map to DB column `cancelled_at` but `declined_at` only populated if status indicates decline

---

## Booking Requests: Review Queue Zero + Bulk Actions (P2.21.4.8o)

**When to use:** Processing multiple booking requests efficiently with bulk operations.

### Bulk Endpoints

**POST /api/v1/booking-requests/bulk/review**

Set multiple requests to `under_review` status:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["uuid1", "uuid2"], "internal_note": "Bulk review"}' \
  "$API_BASE_URL/api/v1/booking-requests/bulk/review"
```

Response:
```json
{
  "total": 2,
  "succeeded": 2,
  "failed": 0,
  "results": [
    {"id": "uuid1", "success": true, "status": "under_review"},
    {"id": "uuid2", "success": true, "status": "under_review"}
  ],
  "message": "Bulk review completed: 2 succeeded, 0 failed"
}
```

**POST /api/v1/booking-requests/bulk/decline**

Decline multiple requests with a single reason:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["uuid1", "uuid2"], "decline_reason": "Property unavailable", "internal_note": "Bulk decline"}' \
  "$API_BASE_URL/api/v1/booking-requests/bulk/decline"
```

### Limits and Constraints

| Parameter | Limit | Notes |
|-----------|-------|-------|
| Max batch size | 50 | Request fails if >50 IDs |
| Valid status transitions | requested → under_review | For bulk review |
| Valid status transitions | requested/under_review → cancelled | For bulk decline |

**PROD-Safe:** No bulk-approve endpoint (too risky for accidental confirmations).

### Admin UI: Multi-Select

The Admin UI provides checkboxes for bulk selection:

1. **Select individual items**: Click checkbox on each row
2. **Select all actionable**: Click header checkbox (selects all requested/under_review)
3. **Action bar appears**: Shows count and bulk action buttons
4. **Actions**:
   - "In Bearbeitung setzen" → Bulk review
   - "Ablehnen" → Opens modal for decline reason

### Admin UI: Refresh Button

The refresh button (↻) in header reloads:
- Current tab's request list
- All tab counts (badges)

No page flicker - data updates in-place.

### Smoke Test Coverage (Tests 20-21)

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh

# Test 20: Bulk review endpoint (>=2 IDs else SKIP)
# Test 21: Bulk decline endpoint (>=2 IDs else SKIP)
```

### Troubleshooting

**Bulk action returns partial success**
- Check `results` array for per-item errors
- Common errors: "Not found", "Invalid status: confirmed"
- Partial success is intentional (one bad ID doesn't fail entire batch)

**Checkbox not appearing for a row**
- Cause: Only `requested` and `under_review` items are selectable
- Confirmed/cancelled items show disabled checkbox

**Refresh button not updating**
- Check: Network tab for API calls
- Verify: No errors in console
- May take a moment if many requests in queue

---

## Idempotency-Key Support (P3.1)

### Overview

The `Idempotency-Key` header prevents duplicate bookings when clients retry requests (network issues, timeouts, user double-clicks).

**Supported Endpoints:**
- `POST /api/v1/bookings` (authenticated booking creation)
- `POST /api/v1/public/booking-requests` (public booking requests)

### How It Works

| Scenario | Result |
|----------|--------|
| Same key + same payload | Returns cached response (no duplicate created) |
| Same key + different payload | Returns `409 idempotency_conflict` |
| No key provided | Normal request (no idempotency protection) |

Keys expire after **24 hours**.

### Usage

```bash
# Create booking with idempotency key
curl -X POST "$HOST/api/v1/bookings" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-client-request-id-123" \
  -d '{"property_id": "...", "check_in": "2026-02-01", ...}'

# Retry same request (returns same booking, no duplicate)
curl -X POST "$HOST/api/v1/bookings" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-client-request-id-123" \
  -d '{"property_id": "...", "check_in": "2026-02-01", ...}'
```

### Client Implementation Guidelines

1. **Generate unique keys**: Use UUID or `{user_id}-{timestamp}-{random}` format
2. **Scope keys appropriately**: Include action context (e.g., `booking-create-{uuid}`)
3. **Persist keys locally**: Store until response confirmed to enable retries
4. **Never reuse keys**: Each unique operation needs its own key

### Common Failure Modes

**409 idempotency_conflict**

```json
{
  "detail": {
    "error": "idempotency_conflict",
    "message": "Idempotency key 'xyz' was already used with different request data...",
    "idempotency_key": "xyz",
    "entity_id": "existing-booking-uuid"
  }
}
```

**Resolution:**
- Client sent different payload with same key
- Generate new key for the new request
- The `entity_id` field shows what was created with the original request

**Audit Log Entry**

Successful booking creates emit `booking_created` audit events with:
- `idempotency_key`: The key used (if provided)
- `entity_id`: The created booking UUID
- `actor_user_id`: The authenticated user

### Smoke Test

```bash
# Run idempotency smoke test (PROD-safe)
export HOST="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="$(./backend/scripts/get_fresh_token.sh)"
./backend/scripts/pms_booking_idempotency_smoke.sh
```

### Smoke Test Environment Variables (P3.1a)

The smoke script searches for free date windows to handle PROD environments with heavy booking load.

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_DAYS` | 30 | Start searching this many days in the future |
| `NIGHTS` | 3 | Booking duration in nights |
| `SEARCH_STEP_DAYS` | 7 | Days to advance on each retry |
| `MAX_ATTEMPTS` | 30 | Maximum windows to try before giving up |
| `REQUIRE_CREATE_SUCCESS` | false | If true, fail on no free window; else PROD-safe skip |

**Date Window Search Algorithm:**
```
For attempt i in [0..MAX_ATTEMPTS-1]:
  check_in  = today + (BASE_DAYS + i*SEARCH_STEP_DAYS) days
  check_out = check_in + NIGHTS days

  On 409 double_booking/inventory_overlap → try next window
  On 201 success → proceed with idempotency tests
```

**PROD-safe SKIP Behavior (default):**

When `REQUIRE_CREATE_SUCCESS=false` (default) and no free window is found after MAX_ATTEMPTS:
- Script exits with **rc=0** (success)
- Logs `[SKIP] PROD-SAFE SKIP` message
- This is expected in PROD with heavy booking load or inventory_ranges blocking windows

**Strict Mode:**

```bash
# Require successful booking creation (fail if no free window)
REQUIRE_CREATE_SUCCESS=true ./backend/scripts/pms_booking_idempotency_smoke.sh
```

When `REQUIRE_CREATE_SUCCESS=true` and no free window is found:
- Script exits with **rc=1** (failure)
- Logs `[FAIL] No free window found` error

### Database Cleanup

Idempotency keys auto-expire after 24 hours. For manual cleanup:

```sql
-- View recent idempotency records
SELECT idempotency_key, endpoint, created_at, expires_at
FROM idempotency_keys
WHERE agency_id = '<agency_uuid>'
ORDER BY created_at DESC
LIMIT 20;

-- Delete expired records (normally automatic)
DELETE FROM idempotency_keys WHERE expires_at < NOW();
```

---
