# Inventory Contract (Bookings + Availability Blocks)

**Purpose:** Single source of truth for inventory/availability semantics, edge cases, and guarantees.

**Audience:** Backend developers, integration teams, QA engineers.

**Last Updated:** 2025-12-27 (Phase 30.5)

---

## A) Definitions

### Date Semantics: End-Exclusive

**Rule:** Date ranges use **end-exclusive** semantics.

- `start_date` (or `check_in`): **Inclusive** — first day of occupancy/block
- `end_date` (or `check_out`): **Exclusive** — day after last day (NOT occupied)

**Example:**
```json
{
  "check_in": "2026-01-01",
  "check_out": "2026-01-05"
}
```

**Meaning:**
- Occupied days: Jan 1, 2, 3, 4 (4 nights)
- Jan 5 is **free** (check-out day is NOT occupied)

**Visual:**
```
Jan:  1  2  3  4  5  6
      [========]  <-- Occupied
                  ^ check_out (free for next check-in)
```

**Validation:** Confirmed via Phase 30 Test 9 (B2B_TEST) — back-to-back bookings succeed when booking B's check-in equals booking A's check-out.

### Occupied vs Free

**Occupied (blocks inventory):**
- Booking with `status` in: `confirmed`, `pending`, `checked_in`, `checked_out`
- Availability block (active, not deleted)

**Free (does NOT block inventory):**
- Booking with `status=cancelled`
- Deleted availability blocks (soft or hard deleted)
- Dates outside any range

**Current Behavior:** Cancelled bookings immediately free inventory (validated via Phase 20 smoke tests).

### Availability Blocks vs Bookings

| Aspect | Availability Blocks | Bookings |
|--------|---------------------|----------|
| **Purpose** | Manual blocking (maintenance, owner use, etc.) | Guest reservations |
| **Priority** | Same as bookings (both prevent overlaps) | Same as blocks |
| **Source** | `availability_blocks` table | `bookings` table |
| **State** | `blocked` (active) or deleted | `status` (confirmed, pending, cancelled, etc.) |
| **Cleanup** | DELETE `/api/v1/availability/blocks/{id}` | PATCH `/api/v1/bookings/{id}` with `status=cancelled` |
| **Note** | DELETE supported for blocks | DELETE **NOT supported** for bookings (returns 405) |

**Unified View:** Both appear in `GET /api/v1/availability` response as `ranges[]` with `kind=block` or `kind=booking`.

---

## B) API Contracts (Normative)

### Contract 1: Overlap Detection

**Rule:** Creating a booking that overlaps an existing booking or block returns HTTP 409.

**Overlap Formula (end-exclusive):**
```
overlap = (start1 < end2) AND (start2 < end1)
```

**Response:**
```json
{
  "conflict_type": "inventory_overlap"
}
```
or (nested under detail):
```json
{
  "detail": {
    "conflict_type": "inventory_overlap"
  }
}
```

**HTTP Status:** `409 Conflict`

**Examples:**

| Range 1 | Range 2 | Overlap? |
|---------|---------|----------|
| Jan 1-5 | Jan 3-6 | ✅ Yes (Jan 3-4 overlap) |
| Jan 1-5 | Jan 5-10 | ❌ No (Jan 5 is free if end-exclusive) |
| Jan 1-3 | Jan 2-4 | ✅ Yes (Jan 2 overlaps) |

**Validation:** Confirmed via Phase 30 Test 8 (AVAIL_BLOCK_TEST) — overlapping booking attempt rejected with 409.

### Contract 2: Back-to-Back Bookings Allowed

**Rule:** Creating booking B where `B.check_in == A.check_out` is **valid** (no conflict).

**Rationale:** End-exclusive semantics mean check-out day is NOT occupied.

**Example:**
```
Booking A: Jan 1-3 (occupies Jan 1, 2)
Booking B: Jan 3-5 (occupies Jan 3, 4)
           ^ check-in = A's check-out (valid)
```

**HTTP Status:** `201 Created` for both bookings

**Validation:** Confirmed via Phase 30 Test 9 (B2B_TEST) — both bookings returned HTTP 201.

---

## C) Edge Cases Checklist

| Scenario | Expected Behavior | HTTP Status | Notes |
|----------|-------------------|-------------|-------|
| **Exact overlap** (same dates) | Reject | 409 `inventory_overlap` | Both start/end match existing range |
| **Partial overlap** (start or end inside existing range) | Reject | 409 `inventory_overlap` | Any day overlap triggers conflict |
| **Back-to-back** (B.check_in = A.check_out) | Allow | 201 Created | End-exclusive: check-out day is free |
| **Block overlaps pending booking** | Reject | 409 `inventory_overlap` | Blocks and bookings have same priority |
| **Booking overlaps existing block** | Reject | 409 `inventory_overlap` | Validated in Test 8 |
| **Cancelled booking** | Does NOT block | 200 OK (for new booking) | Cancelled bookings removed from inventory |
| **Same-day check-in/check-out** | Depends on minimum stay | 422 Validation Error | Observed: minimum stay = 2 nights |
| **Timezone handling** | Date-only (no time) | N/A | Dates treated as local property dates |

**Timezone Approach:** Dates are stored and compared as **date-only** values (YYYY-MM-DD). No time component or timezone conversion. Assumes all dates are in the property's local timezone context.

---

## D) DB Guarantees (Now vs Later)

### Now (Phase 30 — Service Layer)

**Enforcement:**
- Service layer checks for overlaps before INSERT/UPDATE
- Transactions ensure atomicity (block/booking creation + overlap check)
- API layer returns 409 on conflict

**Limitations:**
- Race conditions possible under high concurrency (two simultaneous booking requests for same dates)
- No database-level constraint enforcement

**Mitigation:**
- Transaction isolation (database default: READ COMMITTED)
- Service-layer validation runs within transaction

### Later (Recommended Roadmap — Database Constraints)

**Option 1: PostgreSQL Exclusion Constraint**

Example (pseudocode):
```sql
-- On inventory_ranges view or materialized view
ALTER TABLE inventory_ranges
ADD CONSTRAINT no_overlap_active_ranges
EXCLUDE USING GIST (
  property_id WITH =,
  daterange(start_date, end_date, '[)') WITH &&
)
WHERE (state IN ('occupied', 'blocked'));
```

**Benefits:**
- Database-level guarantee (no race conditions)
- Uses GiST index for efficient range overlap detection
- `daterange(start_date, end_date, '[)')` = start-inclusive, end-exclusive
- `WITH &&` = overlaps operator

**Prerequisites:**
- Requires `btree_gist` extension
- `inventory_ranges` must be a real table or materialized view (not just a VIEW)

**Option 2: Advisory Locks**

Use PostgreSQL advisory locks during booking creation:
```sql
SELECT pg_advisory_xact_lock(hashtext(property_id::text));
-- Perform overlap check + INSERT within transaction
```

**Benefits:**
- Prevents race conditions without schema changes
- Works with existing VIEW structure

**Trade-offs:**
- Serializes booking creation per property (lower throughput)
- Lock released at transaction end

**Recommendation:** Start with Option 2 (advisory locks) for immediate safety, migrate to Option 1 (exclusion constraint) when schema evolution allows.

**Status:** Not implemented as of Phase 30. Service layer enforcement validated via smoke tests.

---

## E) Test Evidence (Phase 30 Validation)

### Test 8: AVAIL_BLOCK_TEST (Availability Block Conflict)

**What was tested:**
1. Create availability block (2026-01-25 to 2026-01-28, 3 days)
2. Verify block appears in `GET /api/v1/availability` response
   - Expected: `kind=block`, `state=blocked`, `block_id` present
3. Attempt to create overlapping booking (same dates)
   - Expected: HTTP 409 with `conflict_type=inventory_overlap`
4. Delete block for cleanup
   - Expected: HTTP 204

**Result:** ✅ PASS

**Evidence:**
```
ℹ️  Block created: def-456...
ℹ️  ✓ Block found in availability response
ℹ️  ✓ Booking correctly rejected with 409 (conflict_type: inventory_overlap)
ℹ️  ✓ Block deleted successfully
```

**Validates:** Contract 1 (overlap detection returns 409)

### Test 9: B2B_TEST (Back-to-Back Booking Boundary)

**What was tested:**
1. Scan for 4-day free gap (2026-02-26 to 2026-03-02 found)
2. Create booking A: 2026-02-26 to 2026-02-28 (2 nights)
   - Expected: HTTP 201
3. Create booking B: 2026-02-28 to 2026-03-02 (check-in = A's check-out)
   - Expected: HTTP 201 (no conflict)
4. Cancel both bookings via PATCH `status=cancelled`
   - Expected: HTTP 200 for each

**Result:** ✅ PASS

**Evidence:**
```
ℹ️  ✓ Booking A created: abc-123... (2026-02-26 to 2026-02-28)
ℹ️  ✓ Booking B created: def-456... (2026-02-28 to 2026-03-02)
ℹ️  ✅ PASS - Back-to-back bookings succeeded (confirms end-exclusive date semantics)
```

**Validates:**
- Contract 2 (back-to-back bookings allowed)
- End-exclusive date semantics (check-out day is free)

### How to Re-run Validation

**Location:** HOST-SERVER-TERMINAL

```bash
# SSH to host server
ssh root@your-host

# Load environment (SB_URL, ANON_KEY, EMAIL, PASSWORD, API)
source /root/pms_env.sh

# Enable opt-in tests
export AVAIL_BLOCK_TEST=true  # Test 8: block conflict
export B2B_TEST=true          # Test 9: back-to-back boundary

# Run smoke script
bash backend/scripts/pms_phase23_smoke.sh
```

**Safety:** Tests use future dates (30-60+ days out) and clean up automatically via trap.

---

## Summary

| Contract | Rule | Status | Evidence |
|----------|------|--------|----------|
| **End-exclusive dates** | check-out day is free | ✅ Validated | Test 9 (B2B_TEST) |
| **Overlap detection** | HTTP 409 `inventory_overlap` | ✅ Validated | Test 8 (AVAIL_BLOCK_TEST) |
| **Back-to-back allowed** | B.check_in = A.check_out → 201 | ✅ Validated | Test 9 (B2B_TEST) |
| **Cancelled bookings** | Do NOT block inventory | ✅ Validated | Phase 20 smoke tests |
| **DB constraints** | Service layer (now), constraints (roadmap) | 🔄 Planned | See section D |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-27 | Initial inventory contract (Phase 30.5) | Claude Code |
