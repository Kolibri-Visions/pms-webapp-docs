# Inventory & Availability Rules

**Purpose**: Document PMS inventory/availability data model, conflict detection rules, and validation guarantees.

**Audience**: Ops engineers, QA, integration developers.

**Last Updated**: 2025-12-26

---

## Purpose & Scope

This document defines:
- **Availability range types** (bookings vs blocks)
- **Date semantics** (inclusive/exclusive behavior - based on observed behavior)
- **Conflict detection rules** (when 409 is returned)
- **API field requirements** (verified in practice)
- **Test examples** (runnable curl commands for validation)

**Out of Scope:**
- Pricing logic
- Channel manager sync rules
- RLS policies (see database schema docs)

---

## Data Model Terms

### Availability Range Kinds

The PMS tracks two types of availability ranges in the `inventory_ranges` view:

1. **Booking Ranges** (`kind=booking`)
   - Represents a confirmed or pending reservation
   - Occupies inventory (prevents other bookings)
   - Source: `bookings` table
   - Statuses: `confirmed`, `pending`, `checked_in`, `checked_out`, `cancelled`

2. **Block Ranges** (`kind=block`)
   - Represents manual blocking (maintenance, owner use, etc.)
   - Prevents bookings during blocked period
   - Source: `availability_blocks` table
   - State: `blocked` (active), or deleted (removed from inventory)

**Unified View:** Both types appear in `/api/v1/availability` response as `ranges[]` with:
- `kind`: `"booking"` or `"block"`
- `state`: `"occupied"` (booking) or `"blocked"` (block)
- `start_date`: First day of range
- `end_date`: Last day boundary (see Date Semantics for interpretation)
- `booking_id` or `block_id`: Reference to source record

---

## Date Semantics

### Expected Interpretation (End-Exclusive)

**Note:** Based on observed API behavior, dates appear to use **end-exclusive** semantics, but this should be verified in your environment.

**Assumed Behavior:**
- `start_date`: **Inclusive** (first day of occupancy/block)
- `end_date`: **Exclusive** (day after last day)

**Example (Assumed):**
```json
{
  "start_date": "2026-01-01",
  "end_date": "2026-01-05"
}
```

**Expected Meaning:**
- Occupied/blocked days: Jan 1, 2, 3, 4 (4 nights)
- Jan 5 is **free** (end_date is NOT occupied)

**Visual:**
```
Jan:  1  2  3  4  5  6
      [========]  <-- Occupied/blocked
                  ^ end_date (expected free)
```

### Verification Test (Back-to-Back Bookings)

To confirm date semantics in your environment, run this back-to-back booking test:

**Note:** Observed in our environment: API enforces **minimum stay = 2 nights** (422 "Minimum stay is 2 nights" if violated).

**Location:** HOST-SERVER-TERMINAL

```bash
# Test hypothesis: end_date is exclusive
# Create booking A: Jan 1-3 (2 nights)
# Then create booking B: Jan 3-5 (check-in = previous check-out)
# If booking B succeeds → end_date is exclusive (no boundary overlap)
# If booking B fails with 409 → end_date is inclusive (Jan 3 occupied by both)

# Setup (assumes TOKEN and PID already set)
export API="https://api.fewo.kolibri-visions.de"

# Booking A: Jan 1-3 (2 nights - meets minimum stay)
BOOKING_A=$(curl -s -X POST "$API/api/v1/bookings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\nHTTP:%{http_code}" \
  -d '{
    "property_id": "'$PID'",
    "check_in": "2026-01-01",
    "check_out": "2026-01-03",
    "num_adults": 2,
    "source": "direct",
    "guest": {
      "email": "test1@example.com",
      "first_name": "Test",
      "last_name": "One"
    }
  }')

BOOKING_A_ID=$(echo "$BOOKING_A" | sed '/HTTP:/d' | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
echo "Booking A created: $BOOKING_A_ID (Jan 1-3)"

# Booking B: Jan 3-5 (check-in = previous check-out - tests boundary)
BOOKING_B=$(curl -s -X POST "$API/api/v1/bookings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\nHTTP:%{http_code}" \
  -d '{
    "property_id": "'$PID'",
    "check_in": "2026-01-03",
    "check_out": "2026-01-05",
    "num_adults": 2,
    "source": "direct",
    "guest": {
      "email": "test2@example.com",
      "first_name": "Test",
      "last_name": "Two"
    }
  }')

HTTP_B=$(echo "$BOOKING_B" | grep "HTTP:" | cut -d: -f2)

# Verify result
if [[ "$HTTP_B" == "201" ]]; then
    echo "✓ Booking B succeeded (HTTP 201)"
    echo "✓ CONFIRMED: end_date is exclusive (Jan 3 available for check-in)"
    BOOKING_B_ID=$(echo "$BOOKING_B" | sed '/HTTP:/d' | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
    echo "Booking B created: $BOOKING_B_ID (Jan 3-5)"
elif [[ "$HTTP_B" == "409" ]]; then
    echo "✗ Booking B failed with 409 conflict"
    echo "✗ UNEXPECTED: end_date may be inclusive (Jan 3 blocked by booking A)"
else
    echo "? Booking B returned HTTP $HTTP_B (unexpected)"
fi

# Cleanup: Cancel both bookings (see cleanup section for details)
# Note: DELETE /bookings not supported (405), use PATCH status=cancelled
```

### Overlap Detection (Assumed Formula)

Based on end-exclusive assumption, two ranges **overlap** if:

```
overlap = (start1 < end2) AND (start2 < end1)
```

**Examples (assuming end-exclusive):**

| Range 1 | Range 2 | Expected Overlap? |
|---------|---------|-------------------|
| `2026-01-01` to `2026-01-05` | `2026-01-03` to `2026-01-06` | ✅ Yes (Jan 3-4 overlap) |
| `2026-01-01` to `2026-01-05` | `2026-01-05` to `2026-01-10` | ❌ No (Jan 5 free if end-exclusive) |
| `2026-01-01` to `2026-01-03` | `2026-01-02` to `2026-01-04` | ✅ Yes (Jan 2 overlaps) |

---

## Conflict Rules

### Rule 1: Booking Overlapping Block

**When:** Creating a booking that overlaps an active availability block

**Result:** HTTP 409 with `conflict_type=inventory_overlap`

**Example:**
```json
// Existing block: Jan 10-15
{
  "kind": "block",
  "start_date": "2026-01-10",
  "end_date": "2026-01-15",
  "reason": "maintenance"
}

// Attempt booking: Jan 12-14 (overlaps)
POST /api/v1/bookings
{
  "check_in": "2026-01-12",
  "check_out": "2026-01-14",
  ...
}

// Response: 409 Conflict
{
  "conflict_type": "inventory_overlap"
}
```

### Rule 2: Booking Overlapping Booking

**When:** Creating a booking that overlaps another active booking

**Result:** HTTP 409 with `conflict_type=inventory_overlap`

**Example:**
```json
// Existing booking: Jan 20-25
{
  "kind": "booking",
  "start_date": "2026-01-20",
  "end_date": "2026-01-25",
  "status": "confirmed"
}

// Attempt booking: Jan 22-27 (overlaps)
POST /api/v1/bookings
{
  "check_in": "2026-01-22",
  "check_out": "2026-01-27",
  ...
}

// Response: 409 Conflict
{
  "conflict_type": "inventory_overlap"
}
```

### Rule 3: Cancelled Bookings Do NOT Block

**When:** Booking with `status=cancelled` exists

**Result:** Cancelled booking does **not** occupy inventory (can rebook same dates)

**Example:**
```json
// Cancelled booking: Jan 30 - Feb 5
{
  "kind": "booking",
  "start_date": "2026-01-30",
  "end_date": "2026-02-05",
  "status": "cancelled"  // Does NOT appear in inventory_ranges
}

// New booking: Jan 30 - Feb 5 (same dates)
POST /api/v1/bookings
{
  "check_in": "2026-01-30",
  "check_out": "2026-02-05",
  ...
}

// Response: 201 Created (success - cancelled booking ignored)
```

---

## API Field Requirements

### POST /api/v1/availability/blocks

**Required Fields (verified in practice):**
| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `property_id` | UUID | `"123e4567-..."` | Property to block |
| `start_date` | Date | `"2026-01-10"` | First blocked day |
| `end_date` | Date | `"2026-01-15"` | Last day boundary |
| `reason` | String | `"maintenance"` | Human-readable reason |

**Response (HTTP 201):**
```json
{
  "id": "block-uuid",
  "property_id": "property-uuid",
  "start_date": "2026-01-10",
  "end_date": "2026-01-15",
  "reason": "maintenance"
}
```

### POST /api/v1/bookings

**Required Fields (verified in live tests):**
| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `property_id` | UUID | `"123e4567-..."` | Property to book |
| `check_in` | Date | `"2026-01-20"` | Check-in date |
| `check_out` | Date | `"2026-01-25"` | Check-out date |
| `num_adults` | Integer | `2` | **Verified required** (422 if missing) |
| `source` | String | `"direct"` | Booking source |
| `guest` | Object | See below | Guest information |

**Optional Fields (may be required depending on schema version):**
- `num_guests`: Total guest count (not verified as strictly required)
- `status`: Booking status (may have server default if omitted)

**Guest Object (required):**
```json
{
  "email": "guest@example.com",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Minimal Working Payload:**
```json
{
  "property_id": "your-property-uuid",
  "check_in": "2026-01-20",
  "check_out": "2026-01-25",
  "num_adults": 2,
  "source": "direct",
  "guest": {
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User"
  }
}
```

**Response (HTTP 201):**
```json
{
  "id": "booking-uuid",
  "property_id": "property-uuid",
  "check_in": "2026-01-20",
  "check_out": "2026-01-25",
  "num_adults": 2,
  ...
}
```

### GET /api/v1/availability

**Query Parameters:**
| Parameter | Type | Required | Example | Notes |
|-----------|------|----------|---------|-------|
| `property_id` | UUID | Yes | `"123e4567-..."` | Property to query |
| `from_date` | Date | Yes | `"2026-01-01"` | Query start |
| `to_date` | Date | Yes | `"2026-01-31"` | Query end |

**Max Range:** 365 days (anti-abuse protection)

**Response (HTTP 200):**
```json
{
  "ranges": [
    {
      "kind": "booking",
      "state": "occupied",
      "start_date": "2026-01-10",
      "end_date": "2026-01-15",
      "booking_id": "booking-uuid"
    },
    {
      "kind": "block",
      "state": "blocked",
      "start_date": "2026-01-20",
      "end_date": "2026-01-25",
      "block_id": "block-uuid"
    }
  ]
}
```

---

## HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| `200 OK` | Success (read operation) | GET /availability, booking cancellation |
| `201 Created` | Resource created | POST /blocks, POST /bookings |
| `204 No Content` | Deleted successfully | DELETE /blocks/{id} |
| `400 Bad Request` | Invalid input | Date range > 365 days, invalid UUID |
| `401 Unauthorized` | Missing/invalid JWT | No Authorization header |
| `403 Forbidden` | Insufficient permissions | User lacks RBAC role |
| `404 Not Found` | Resource doesn't exist | Block/booking ID not found |
| `405 Method Not Allowed` | Unsupported operation | DELETE /bookings (observed - not supported) |
| `409 Conflict` | Inventory overlap | Booking conflicts with block/booking |
| `422 Validation Error` | Missing required field | Missing `num_adults`, `guest`, etc. |
| `503 Service Unavailable` | Database degraded | Connection pool failed |

---

## Test Examples

### Setup: Environment Variables

**Location:** HOST-SERVER-TERMINAL

```bash
# SSH to host server
ssh root@your-host

# Set required environment variables
export SB_URL="https://sb-pms.kolibri-visions.de"
export ANON_KEY="your-anon-key"
export EMAIL="admin@example.com"
export PASSWORD="your-password"
export API="https://api.fewo.kolibri-visions.de"
```

### Step 1: Fetch JWT Token

**Location:** HOST-SERVER-TERMINAL

```bash
TOKEN=$(curl -s -X POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"'$EMAIL'","password":"'$PASSWORD'"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# Verify token (should print length, not content)
echo "Token length: ${#TOKEN}"
```

### Step 2: Derive Property ID

**Location:** HOST-SERVER-TERMINAL

```bash
PID=$(curl -s -X GET "$API/api/v1/properties?limit=1" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['items'][0]['id'] if d.get('items') else '')")

# Verify PID
echo "Property ID: $PID"
```

### Step 3: Create Availability Block

**Location:** HOST-SERVER-TERMINAL

```bash
# Block future dates (today + 30 days, 5 nights)
BLOCK_START=$(date -d "+30 days" "+%Y-%m-%d" 2>/dev/null || date -v+30d "+%Y-%m-%d")
BLOCK_END=$(date -d "+35 days" "+%Y-%m-%d" 2>/dev/null || date -v+35d "+%Y-%m-%d")

BLOCK_RESPONSE=$(curl -s -X POST "$API/api/v1/availability/blocks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "'$PID'",
    "start_date": "'$BLOCK_START'",
    "end_date": "'$BLOCK_END'",
    "reason": "test-manual-block"
  }')

# Extract block ID
BLOCK_ID=$(echo "$BLOCK_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")

echo "Block created: $BLOCK_ID ($BLOCK_START to $BLOCK_END)"
```

### Step 4: Verify Availability Shows Blocked Range

**Location:** HOST-SERVER-TERMINAL

```bash
# Query availability for next 60 days
QUERY_START=$(date -d "today" "+%Y-%m-%d" 2>/dev/null || date "+%Y-%m-%d")
QUERY_END=$(date -d "+60 days" "+%Y-%m-%d" 2>/dev/null || date -v+60d "+%Y-%m-%d")

AVAIL_RESPONSE=$(curl -s -X GET "$API/api/v1/availability?property_id=$PID&from_date=$QUERY_START&to_date=$QUERY_END" \
  -H "Authorization: Bearer $TOKEN")

# Check if block appears
echo "$AVAIL_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data.get('ranges', []):
    if r.get('block_id') == '$BLOCK_ID':
        print(f\"✓ Block found: {r['start_date']} to {r['end_date']} (kind={r['kind']}, state={r['state']})\")
        break
else:
    print('✗ Block NOT found in availability response')
"
```

### Step 5: Attempt Overlapping Booking (Expect 409)

**Location:** HOST-SERVER-TERMINAL

```bash
# Try to book dates overlapping the block
OVERLAP_IN=$(date -d "+32 days" "+%Y-%m-%d" 2>/dev/null || date -v+32d "+%Y-%m-%d")
OVERLAP_OUT=$(date -d "+34 days" "+%Y-%m-%d" 2>/dev/null || date -v+34d "+%Y-%m-%d")

BOOKING_RESPONSE=$(curl -s -X POST "$API/api/v1/bookings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -w "\nHTTP_CODE:%{http_code}" \
  -d '{
    "property_id": "'$PID'",
    "check_in": "'$OVERLAP_IN'",
    "check_out": "'$OVERLAP_OUT'",
    "num_adults": 2,
    "source": "direct",
    "guest": {
      "email": "test@example.com",
      "first_name": "Test",
      "last_name": "User"
    }
  }')

# Extract HTTP code and conflict_type
HTTP_CODE=$(echo "$BOOKING_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
CONFLICT_TYPE=$(echo "$BOOKING_RESPONSE" | sed '/HTTP_CODE:/d' | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('conflict_type', data.get('detail', {}).get('conflict_type', 'unknown')))
except:
    print('parse_error')
" 2>/dev/null)

echo "Booking attempt: HTTP $HTTP_CODE (conflict_type: $CONFLICT_TYPE)"

# Verify
if [[ "$HTTP_CODE" == "409" && "$CONFLICT_TYPE" == "inventory_overlap" ]]; then
    echo "✓ PASS - Conflict detected correctly"
else
    echo "✗ FAIL - Expected HTTP 409 with conflict_type=inventory_overlap"
fi
```

### Step 6: Cleanup - Delete Block

**Location:** HOST-SERVER-TERMINAL

```bash
# Delete the test block
DELETE_CODE=$(curl -s -X DELETE "$API/api/v1/availability/blocks/$BLOCK_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -w "%{http_code}" \
  -o /dev/null)

if [[ "$DELETE_CODE" == "204" ]]; then
    echo "✓ Block deleted successfully"
else
    echo "✗ Block deletion failed - HTTP $DELETE_CODE"
fi
```

---

## Smoke Script Integration

### Automated Testing

The Phase 23 smoke script includes an **opt-in** inventory conflict test.

**Location:** Coolify Terminal (pms-backend container)

```bash
# SSH to host server first
ssh root@your-host

# Enter Coolify container terminal (via dashboard or docker exec)
docker exec -it pms-backend bash

# Inside container:
export ENV_FILE=/root/pms_env.sh
export AVAIL_BLOCK_TEST=true
bash /app/scripts/pms_phase23_smoke.sh
```

**Alternative (one-liner from host):**

**Location:** HOST-SERVER-TERMINAL

```bash
docker exec pms-backend bash -c '
export ENV_FILE=/root/pms_env.sh
export AVAIL_BLOCK_TEST=true
bash /app/scripts/pms_phase23_smoke.sh
'
```

**Expected Output:**
```
ℹ️  Test 8: Availability block conflict test (opt-in via AVAIL_BLOCK_TEST=true)
ℹ️  Creating availability block: 2026-01-25 to 2026-01-28 (PID: abc-123...)
ℹ️  Block created: def-456...
ℹ️  Verifying block appears in /api/v1/availability...
ℹ️  ✓ Block found in availability response
ℹ️  Attempting to create overlapping booking (expect 409 conflict)...
ℹ️  ✓ Booking correctly rejected with 409 (conflict_type: inventory_overlap)
ℹ️  Deleting block def-456...
ℹ️  ✓ Block deleted successfully
ℹ️  ✅ PASS - Availability block conflict test complete

Summary:
  ✓ Health endpoints accessible
  ✓ OpenAPI schema available
  ✓ JWT authentication successful
  ✓ Properties API accessible
  ✓ Bookings API accessible
  ✓ Availability API accessible (PID: abc-123...)
  ✓ Availability block conflict test passed
```

**What It Tests:**
- Block creation with future dates (avoids prod conflicts)
- Block visibility in availability API
- Conflict detection (409 inventory_overlap)
- Cleanup guarantee (trap ensures deletion)

**When to Use:**
- After schema migrations affecting `availability_blocks` or `inventory_ranges`
- After deployment of conflict detection logic changes
- Pre-production validation before go-live

**Documentation:**
- Script details: `/app/scripts/README.md` (in container)
- Troubleshooting: `/app/docs/ops/runbook.md` (in container)

---

## Database Constraints (If Implemented)

**Note:** The following describes a recommended database-level conflict prevention mechanism. Verify if this is implemented in your schema.

### Recommended: Exclusion Constraint

A PostgreSQL **EXCLUSION constraint** on `inventory_ranges` can enforce non-overlapping ranges at the database level:

```sql
-- Example (verify if present in your schema)
EXCLUDE USING GIST (
  property_id WITH =,
  daterange(start_date, end_date, '[)') WITH &&
)
WHERE (state IN ('occupied', 'blocked'))
```

**If Implemented:**
- Uses GiST index for efficient range overlap detection
- `daterange(start_date, end_date, '[)')` = start-inclusive, end-exclusive
- `WITH &&` = overlaps operator
- Only active ranges (`occupied`, `blocked`) participate
- Provides database-level guarantee (backup if API validation fails)

**Verification:**

**Location:** Coolify Terminal (pms-backend container) OR HOST-SERVER-TERMINAL with psql access

```bash
# Check if exclusion constraint exists
docker exec pms-backend psql "$DATABASE_URL" -c "
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'inventory_ranges'::regclass
  AND contype = 'x';
"
```

---

## Troubleshooting

### "Conflict detected but block doesn't exist"

**Symptom:** Booking rejected with 409, but `/api/v1/availability` shows no blocks.

**Possible Causes:**
1. Another booking exists in the range (check `kind=booking` in ranges)
2. Cached response (try with different date range or wait 60s)
3. RLS policy hiding the block (check user's agency_id matches block owner)

**Debug:**

**Location:** Coolify Terminal (pms-backend container)

```bash
# Check inventory_ranges directly (requires DB access)
docker exec pms-backend psql "$DATABASE_URL" -c "
SELECT kind, state, start_date, end_date, booking_id, block_id
FROM inventory_ranges
WHERE property_id = 'your-property-uuid'
  AND start_date < 'your-end-date'
  AND end_date > 'your-start-date'
ORDER BY start_date;
"
```

### "422 Validation Error: Field required"

**Symptom:** POST /bookings returns 422 with missing field error.

**Solution:** Ensure verified required fields are present:
- `num_adults` (**verified required** - 422 if missing)
- `guest` object with `email`, `first_name`, `last_name`
- `property_id`, `check_in`, `check_out`, `source`

**Optional fields** (may be required depending on schema):
- `num_guests`
- `status`

See [API Field Requirements](#api-field-requirements) for complete list.

### "Cannot delete booking - HTTP 405 Method Not Allowed"

**Symptom:** Attempting to DELETE a booking returns 405 with `Allow: GET, HEAD, OPTIONS, POST, PATCH`.

**Cause:** Observed in our environment - `DELETE /api/v1/bookings/{id}` is not supported by the API.

**Solution:** Use PATCH to cancel the booking instead of deleting it:

**Location:** HOST-SERVER-TERMINAL

```bash
# ✓ Correct: Cancel booking via PATCH (recommended cleanup)
curl -X PATCH "$API/api/v1/bookings/$BOOKING_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "cancelled",
    "cancellation_reason": "test cleanup"
  }'
# Returns: HTTP 200 (booking updated with status=cancelled)

# ✗ Wrong: DELETE is not supported
curl -X DELETE "$API/api/v1/bookings/$BOOKING_ID" \
  -H "Authorization: Bearer $TOKEN"
# Returns: HTTP 405 Method Not Allowed
```

**Why PATCH is the Best Practice:**
- Preserves booking history (audit trail)
- Frees inventory immediately (cancelled bookings don't block)
- Allows idempotent cancellation (can cancel multiple times safely)
- Prevents accidental data loss (soft delete vs hard delete)

**Effect on Inventory:**
- Cancelled booking (status=cancelled) does NOT appear in `inventory_ranges`
- Same dates immediately become available for rebooking
- See [Rule 3: Cancelled Bookings Do NOT Block](#rule-3-cancelled-bookings-do-not-block)

---

## Additional Resources

- **Smoke Scripts**: `/app/scripts/README.md` (in container)
- **Ops Runbook**: `/app/docs/ops/runbook.md` (database DNS, token validation)
- **Database Schema**: `supabase/migrations/` (check for EXCLUSION constraint)
- **Architecture Docs**: `/app/docs/architecture/` (modular monolith, module boundaries)

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-26 | Initial inventory rules documentation (Phase 26) | Claude Code |
| 2025-12-27 | Phase 27: Document minimum stay (2 nights), HTTP 405 for DELETE /bookings, PATCH cancellation cleanup | Claude Code |
