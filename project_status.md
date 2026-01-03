# PMS-Webapp Project Status

**Last Updated:** 2026-01-03
**Current Phase:** Phase 21 - Inventory/Availability Production Hardening

## Overview

This document tracks the current state of the PMS-Webapp project, including completed phases, ongoing work, and next steps.

## Current Status Summary

| Area | Status | Notes |
|------|--------|-------|
| **Core Inventory** | ✅ STABLE | Phase 20 validated, concurrency tested |
| **Availability API** | ✅ STABLE | Contract validated, schema migrations applied |
| **Channel Manager** | ✅ OPERATIONAL | Sync batches history, admin UI complete |
| **Database Schema** | ✅ UP-TO-DATE | Guests metrics + timeline columns migrated |
| **Admin Console** | ✅ DEPLOYED | Sync monitoring, batch details UI live |
| **Production Readiness** | 🟡 IN PROGRESS | Phase 21 hardening in progress |

## Completed Phases

### Phase 20: Inventory/Availability Final Validation ✅

**Date Completed:** 2025-12-27 to 2026-01-03

**Key Achievements:**
- ✅ Manual blocks prevent bookings (409 conflict enforcement)
- ✅ Deleting blocks unblocks inventory immediately
- ✅ Cancel frees inventory instantly
- ✅ Idempotent cancellation (safe retry)
- ✅ Cancelled bookings don't prevent rebooking
- ✅ Race-safe concurrency validated (1 success, rest 409)

**Validation Tools:**
- `pms_phase20_final_smoke.sh` - Core inventory mechanics
- `pms_booking_concurrency_test.sh` - Parallel booking race conditions

**Database Migrations:**
- `20260103120000_ensure_guests_metrics_columns.sql` - Metrics columns (total_bookings, total_spent, last_booking_at)
- `20260103123000_ensure_guests_booking_timeline_columns.sql` - Timeline columns (first_booking_at, average_rating, updated_at, deleted_at)

**Documentation:**
- Runbook troubleshooting sections for schema drift
- Scripts README updated with auto-pick logic
- Frontend README updated with batch details UI

### Channel Manager Admin UI ✅

**Date Completed:** 2026-01-02 to 2026-01-03

**Key Features:**
- ✅ Sync batches history table with pagination
- ✅ Batch details modal with operation breakdown
- ✅ Direction indicators (→ outbound, ← inbound)
- ✅ Task ID and error message display
- ✅ Auto-refresh for running batches
- ✅ Status filter dropdown (All | Running | Failed | Success)

**API Enhancements:**
- Extended `BatchOperation` model with direction, task_id, error, duration_ms, log_id
- Fixed `list_batch_statuses()` to include all required fields
- Response validation errors resolved

## Current Phase

### Phase 21: Inventory/Availability Production Hardening 🟡

**Date Started:** 2026-01-03
**Status:** In Progress (Docs + Scaffolding)

**Goals:**
- Document common gotchas and operational guidance
- Validate availability API contract (negative tests)
- Plan modular architecture improvements
- Create minimal scaffolds (non-invasive, not wired in)

**Completed in Phase 21:**
- ✅ Runbook section: Phase 21 production hardening guide
  - What Phase 20 proved
  - Common gotchas checklist (422 errors, schema drift)
  - Minimum production checklist
  - Edge cases roadmap
- ✅ Smoke script: `pms_phase21_inventory_hardening_smoke.sh`
  - Negative test: Missing query params → 422
  - Positive test: Valid availability query → 200
  - Read-only (no side effects)
- ✅ Scripts README documentation for Phase 21 smoke
- ✅ Architecture doc: `modular_monolith_phase21.md`
  - ModuleSpec pattern definition
  - Example module specs (inventory, channel_manager)
  - Registry pattern design
  - Migration strategy (Phase 21-24 timeline)
- ✅ Code scaffold: `backend/app/modules/module_spec.py`
  - ModuleSpec dataclass with validation
  - Example module definitions (docs only)
  - NOT wired into runtime (Phase 22+)
- ✅ Phase 21 smoke validation hardening
  - Robust JSON extraction from mixed output
  - Fallback to raw string checks
  - Handles both PMS custom and FastAPI error envelopes

**Completed in Phase 21A (DB Operations):**
- ✅ Migration runner: `backend/scripts/ops/apply_supabase_migrations.sh`
  - Idempotent migration application with tracking table
  - Dry-run and status modes
  - Production safety guards (CONFIRM_PROD flag)
  - Transaction-based execution
- ✅ Runbook section: "DB Migrations (Production)"
  - Complete usage guide with examples
  - Failure modes and troubleshooting
  - Production workflow recommendations
- ✅ Scripts README: Production Database Migrations section
  - Usage examples and output samples
  - Production workflow steps

**Completed in Phase 21B (Booking Concurrency Hardening):**
- ✅ Advisory lock serialization for concurrent bookings
  - Transaction-scoped PostgreSQL advisory locks per property_id
  - Prevents deadlocks from exclusion constraint checks
  - Located in `booking_service.py:510-520` (updated after hotfix)
- ✅ Deadlock retry wrapper with exponential backoff
  - Automatic retry up to 3 attempts (100ms, 200ms backoff)
  - Only retries deadlocks, other errors propagate immediately
  - Located in `booking_service.py:84-121`
- ✅ Route-level error mapping (503, not 500)
  - Maps exhausted deadlock retries to HTTP 503
  - Client-friendly message: "Database deadlock detected. Please retry your request."
  - Located in `bookings.py:288-298`
- ✅ Concurrency script auto-finds free date windows
  - Queries availability API to find free windows (+1, +7, +14 days)
  - Fallback to +60 days if all attempts fail
  - Prevents test failures from existing bookings
- ✅ Unit tests for deadlock handling
  - Tests retry logic, exponential backoff, error propagation
  - Located in `tests/unit/test_booking_deadlock.py`
- ✅ Documentation updates
  - Runbook section: "Booking Concurrency Deadlocks"
  - Scripts README: Free window auto-detection
  - Project status: Phase 21B completion

**Production Hotfix (2026-01-03) - Phase 21B Follow-up:**
- ❗ **Bug:** NameError in advisory lock code (property_id not defined)
  - Symptom: POST /api/v1/bookings returned HTTP 500 for all requests
  - Root cause: Advisory lock referenced property_id before extraction from booking_data
  - Impact: All booking creation broken in production
- ✅ **Fix Applied:**
  - Added property_id extraction before transaction start (line 511)
  - Advisory lock now uses correctly extracted property_id
  - Transaction scope preserved (xact lock, auto-released)
- ✅ **Verification:**
  - Added unit test: `test_advisory_lock_uses_property_id_from_request()`
  - Expected behavior restored: 1x201 + 9x409 on concurrency test
- ✅ **Documentation:**
  - Runbook: Added "Hotfix Note (2026-01-03)" section
  - Project status: This entry

**API Consistency Fix (2026-01-03) - Inquiry Bookings Policy:**
- ❗ **Issue:** Availability API vs Booking Creation inconsistency
  - GET /api/v1/availability showed inquiry bookings as "free" (ranges=[])
  - POST /api/v1/bookings treated inquiry bookings as blocking (returned 409)
  - Concurrency script auto-window mode picked "free" windows with inquiry bookings, got all 409s (false fails)
- ✅ **Fix Applied (Phase 1 - Status Exclusion):**
  - Updated `BookingService.check_availability()` to exclude inquiry from blocking statuses (line 1565)
  - Non-blocking statuses: cancelled, declined, no_show, inquiry
  - Blocking statuses: confirmed, pending, checked_in, checked_out
- ✅ **Fix Applied (Phase 2 - inventory_ranges Source of Truth):**
  - Replaced bookings table query with `inventory_ranges` query in `check_availability()` (line 1567)
  - Both availability API and booking creation now use same source: `inventory_ranges` with `state='active'`
  - Inquiry bookings do NOT create `inventory_ranges` entries (non-blocking by design)
  - Confirmed/pending bookings and blocks create active `inventory_ranges` entries (blocking)
  - Ensures perfect consistency: if availability shows free, booking creation succeeds (no false 409s)
  - Exclusion constraint on `inventory_ranges` provides final race-safe guard
- ✅ **Testing:**
  - Added unit test: `test_inquiry_booking_does_not_block_confirmed_booking()`
  - Verifies confirmed booking succeeds even when inquiry overlaps (inventory_ranges has no conflict)
- ✅ **Script Improvements:**
  - Extended auto-window search from 3 to 7 windows (+1, +7, +14, +21, +30, +45, +60 days)
  - Improved diagnostic messages for 0 successes + all 409s scenario
  - Fallback increased to +90 days (from +60)
- ✅ **Documentation:**
  - Runbook: Added "Source of Truth for Availability" and troubleshooting sections
  - Scripts README: Updated common issues with "Free Window but All 409" guidance
  - Documented inventory_ranges architecture (source_id, kind, state fields)
- ✅ **Expected Behavior:**
  - Inquiry bookings do NOT block availability checks or booking creation
  - Perfect API consistency: availability free → booking creation succeeds
  - Concurrency script robust to inquiry-blocked windows

**Database Constraint Fix (2026-01-03 Follow-up):**
- ❗ **Second Production Bug:** After OCCUPYING_STATUSES fix, inquiry still blocked at DB level
  - Symptom: Availability showed free (0 inventory_ranges), but ALL booking requests got 409
  - Root cause: `bookings.no_double_bookings` exclusion constraint had `WHERE (status NOT IN ('cancelled', 'declined', 'no_show'))` which included inquiry
  - When trying to INSERT confirmed booking, constraint blocked due to overlapping inquiry
- ✅ **Fix Applied (Migration 20260103140000):**
  - Dropped old `no_double_bookings` constraint
  - Recreated with positive filter: `WHERE (status IN ('pending', 'confirmed', 'checked_in'))`
  - Inquiry bookings now excluded from database-level overlap check
  - Aligns with OCCUPYING_STATUSES and inventory_ranges policy
- ✅ **Diagnostic Logging Enhanced:**
  - Added detailed ExclusionViolationError handling in `booking_service.py:731-760`
  - Logs which constraint triggered 409: bookings.no_double_bookings vs inventory_ranges.inventory_ranges_no_overlap
  - Includes property_id, dates, status, and conflicting booking details
- ✅ **Regression Test Added:**
  - `test_bookings_exclusion_constraint_allows_inquiry_overlap()` in `test_booking_deadlock.py`
  - Verifies inquiry can be created, then confirmed booking overlaps inquiry (succeeds), then second confirmed fails
  - Tests database constraint behavior at unit level

**What's Next:**
- Edge cases validation:
  - Back-to-back bookings (end-exclusive semantics)
  - Timezone boundaries (DST, UTC midnight)
  - Min stay constraints
  - Booking window rules (max future days)
  - Malformed date handling

## Test Coverage Status

### Smoke Scripts

| Script | Purpose | Status | Last Run |
|--------|---------|--------|----------|
| `pms_phase20_final_smoke.sh` | Core inventory validation | ✅ PASS | 2026-01-03 |
| `pms_booking_concurrency_test.sh` | Race-safe concurrency | ✅ PASS | 2026-01-03 |
| `pms_phase21_inventory_hardening_smoke.sh` | API contract validation | ✅ NEW | 2026-01-03 |
| `pms_phase23_smoke.sh` | Quick confidence check | ✅ PASS | 2025-12-27 |

### Integration Tests

- Backend integration tests: ✅ Passing (pytest)
- Frontend build: ✅ Passing (npm run build)
- Database migrations: ✅ Up-to-date (Supabase)

## Database Schema Status

### Current Schema Version

- Supabase migrations: Up-to-date
- Last migration: `20260103140000_fix_bookings_exclusion_inquiry_non_blocking.sql`

### Recent Schema Changes

**Guests Table Enhancements:**
- Metrics columns: `total_bookings`, `total_spent`, `last_booking_at`
- Timeline columns: `first_booking_at`, `average_rating`, `updated_at`, `deleted_at`
- Indexes: `idx_guests_last_booking_at`, `idx_guests_first_booking_at`, `idx_guests_deleted_at`

**Exclusion Constraints:**
- `bookings.no_double_bookings` - Race-safe overlap prevention (GIST)

## Known Issues / Tech Debt

### Phase 21 Tech Debt

- [ ] Module bootstrap is still manual (routers mounted in main.py)
  - **Mitigation:** ModuleSpec scaffold created, registry pattern designed
  - **Timeline:** Integration planned for Phase 22

- [ ] No automated tests for availability API edge cases yet
  - **Mitigation:** Smoke scripts provide basic coverage
  - **Timeline:** Integration tests planned for Phase 21.5

### Monitoring Gaps

- [ ] No production metrics dashboard yet
  - **Impact:** Low (logs provide visibility)
  - **Priority:** Medium (Phase 22+)

- [ ] Admin console lacks WebSocket support (polling instead)
  - **Impact:** Low (3-second polling acceptable)
  - **Priority:** Low (future enhancement)

## Next Steps (Phase 21+)

### Immediate (Phase 21 Completion)

1. Run Phase 21 smoke script in production to validate contract
2. Review modular architecture design with team
3. Document any additional edge cases discovered
4. Update runbook with production deployment experience

### Short-term (Phase 22)

1. Wire ModuleSpec registry into `main.py` bootstrap
2. Create module specs for all existing features
3. Add module dependency resolution
4. Add lifecycle hooks (on_startup, on_shutdown)

### Medium-term (Phase 23-24)

1. Split large modules based on bounded contexts
2. Add module health checks
3. Consider dynamic module loading (hot reload for dev)
4. Implement min_stay and booking_window validation

### Long-term (Phase 25+)

1. Module marketplace consideration (third-party plugins)
2. Selective deployment (disable unused modules)
3. Gradual microservices migration (if needed)

## Deployment Status

### Production Environment

- **Backend API:** Deployed on Coolify
- **Frontend Admin:** Deployed on Coolify
- **Database:** Supabase (managed PostgreSQL)
- **Workers:** Celery + Redis (deployed)

### Environment Variables

All required environment variables configured:
- ✅ `DATABASE_URL`
- ✅ `JWT_SECRET`
- ✅ `ALLOWED_ORIGINS` (CORS configured)
- ✅ `CHANNEL_MANAGER_ENABLED=true`

## References

- [Runbook](./ops/runbook.md) - Operational troubleshooting guide
- [Scripts README](../scripts/README.md) - Smoke script documentation
- [Modular Monolith Phase 21](./architecture/modular_monolith_phase21.md) - Architecture planning
- [Channel Manager](./architecture/channel-manager.md) - Channel integration docs

## Changelog

| Date | Phase | Change |
|------|-------|--------|
| 2026-01-03 | Phase 21 | Added Phase 21 hardening docs, smoke script, ModuleSpec scaffold |
| 2026-01-03 | Phase 20 | Applied guests timeline columns migration (first_booking_at, etc.) |
| 2026-01-03 | Phase 20 | Applied guests metrics columns migration (total_bookings, etc.) |
| 2026-01-03 | Admin UI | Fixed PID auto-pick in booking concurrency test |
| 2026-01-02 | Admin UI | Added sync batches history view with direction indicators |
| 2026-01-02 | API | Extended BatchOperation model with detailed fields |
| 2025-12-27 | Phase 30 | Inventory final validation (blocks, B2B, concurrency) PASS |
