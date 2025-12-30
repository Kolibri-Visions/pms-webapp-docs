# Status Review v3 - Start Here

**Review Type**: Code-derived comprehensive scan (read-only, evidence-first)
**Scope**: Backend + Frontend + Worker + Scripts + Docs + Migrations
**Method**: Evidence-based with strict verification (no speculation, no code execution)

---

## Repository Snapshot

- **Reviewed Commit**: `3490c89b829704d10b87a2b42b739f1efd7ae5fd`
- **Generated At**: `2025-12-30 21:01:55 UTC`
- **Branch**: `main` (synced with `origin/main`)
- **Scope**: Full codebase scan (backend + frontend + migrations + tests)

---

## What's New in v3?

### Changes from v2 (2025-12-30 20:48:06 UTC, commit 1c42e95)

**v3 Improvements**:
- ✅ **Fresh evidence scan**: Re-verified all claims against current commit
- ✅ **Stricter evidence citations**: All claims cite exact file paths and line ranges in MANIFEST
- ✅ **Migration analysis**: Documented 16 database migrations with EXCLUSION constraint evidence
- ✅ **Channel Manager structure**: Documented adapters, sync engine, webhooks
- ✅ **Test coverage inventory**: Unit, integration, security, smoke tests
- ✅ **Documentation reorganization proposal**: New docs-reorg-v1 folder with restructuring plan

**Time Delta**: 0 hours 53 minutes since v2

---

## Critical Findings

### 1. Backend API Routes

**All API routes mount under `/api/v1` prefix** (verified):
- Properties: `/api/v1/properties/*`
- Bookings: `/api/v1/bookings/*`
- Availability: `/api/v1/availability/*`

**Health endpoint**: `/health` (NO `/api/v1` prefix)

**Evidence**:
- `backend/app/main.py:134-136` (fallback router mounting)
- `backend/app/modules/bootstrap.py:119-131` (module system mounting)

### 2. Ops Router Status: DEAD CODE

**Backend `/ops/*` router**:
- ❌ EXISTS: `backend/app/routers/ops.py` (2 endpoints: current-commit, env-sanity)
- ❌ NOT MOUNTED: Zero imports found via `rg "from.*ops.*router"`
- ❌ NOT in module system: `backend/app/modules/bootstrap.py` doesn't import it
- ❌ NOT accessible via HTTP

**Recommendation**: Mount OR delete dead code

### 3. Frontend Ops Console

**Frontend `/ops/*` pages**:
- ✅ IMPLEMENTED: `frontend/app/ops/layout.tsx` (SSR admin check)
- ✅ PROTECTED: Server-side session check (lines 27-40)
- ✅ RBAC: Admin role check via `team_members` table (lines 46-92)
- ✅ FEATURE FLAG: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` required (lines 95-140)

**Middleware**: `frontend/middleware.ts:77-82` applies to `/ops/:path*`, `/channel-sync/:path*`, `/login`

### 4. Database Migrations

**16 migrations found** in `supabase/migrations/`:
- Initial schema: `20250101000001_initial_schema.sql` (18KB)
- Availability/inventory: `20251225190000_availability_inventory_system.sql` (8KB)
- **EXCLUSION constraint**: `20251229200517_enforce_overlap_prevention_via_exclusion.sql` (6.7KB)

**Concurrency Protection**:
- Table: `inventory_ranges`
- Constraint: `inventory_ranges_no_overlap`
- Type: PostgreSQL EXCLUSION constraint using GiST index
- Prevents overlapping active bookings per property

**Evidence**: `supabase/migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql`

### 5. Module System

**Feature flags** (from `backend/app/core/config.py` and usage):
1. **MODULES_ENABLED**: Default `true`, enables module system (`backend/app/main.py:117`)
2. **CHANNEL_MANAGER_ENABLED**: Default `false`, gates channel manager module (`backend/app/modules/bootstrap.py:86`)
3. **NEXT_PUBLIC_ENABLE_OPS_CONSOLE**: Frontend ops console feature flag (`frontend/app/ops/layout.tsx:95`)

**Graceful degradation**:
- If module import fails, logs warning and continues
- If DB unavailable at startup, app runs in degraded mode (503 for DB endpoints)

### 6. Channel Manager

**Structure**:
- Adapters: `backend/app/channel_manager/adapters/` (Airbnb, base adapter, factory)
- Sync engine: `backend/app/channel_manager/core/sync_engine.py`
- Rate limiting: `backend/app/channel_manager/core/rate_limiter.py`
- Circuit breaker: `backend/app/channel_manager/core/circuit_breaker.py`
- Webhooks: `backend/app/channel_manager/webhooks/handlers.py`
- Monitoring: `backend/app/channel_manager/monitoring/metrics.py`

**Status**: Gated by `CHANNEL_MANAGER_ENABLED=false` (default OFF)

### 7. RBAC Implementation

**5 roles defined** (from `backend/app/api/deps.py` docstring):
- `admin`
- `manager`
- `staff`
- `owner`
- `accountant`

**Dependencies**:
- `get_current_user`: JWT validation (`backend/app/core/auth.py`)
- `get_current_agency_id`: Multi-tenant context extraction (`backend/app/api/deps.py:53-90`)
- `get_current_role`: Role extraction from JWT/DB
- `require_roles(*roles)`: RBAC enforcement decorator

**Multi-tenancy**:
- Agency context from: X-Agency-Id header OR profiles.last_active_agency_id OR team_members.agency_id

### 8. Test Coverage

**Test files discovered** (15+):
- **Unit tests**: JWT verification, RBAC helpers, agency deps, database generator, channel sync log service
- **Integration tests**: Availability, bookings, RBAC, auth DB priority
- **Security tests**: Token encryption, Redis client, webhook signature
- **Smoke tests**: Channel manager smoke test

**Evidence**: `backend/tests/{unit,integration,security,smoke}/`

---

## Documentation Inventory

**80+ documentation files** found in `backend/docs/`:

### Active Documentation
- `architecture/error-taxonomy.md` - Error codes, typed exceptions ✅
- `ops/runbook.md` - Production deployment guide ✅
- `roadmap/phase-{1-5}.md` - Phase planning documents
- `tickets/phase-{1-5}.md` - Phase ticket tracking
- `database/data-integrity.md`, `database/index-strategy.md`
- `direct-booking-engine/stripe-integration.md`, `edge-cases.md`

### Staging Reviews
- `_staging/status-review-v1/` - First review (2025-12-30 17:34 UTC)
- `_staging/status-review-v2/` - Second review (2025-12-30 20:48 UTC)
- `_staging/status-review-v3/` - **THIS REVIEW** (2025-12-30 21:01 UTC)
- `_staging/docs-reorg-v1/` - Documentation reorganization proposal

---

## Files in This Review (status-review-v3)

1. **START_HERE.md** (this file) - Navigation, critical findings, v2→v3 changes
2. **DOCS_MAP.md** - Complete inventory of existing documentation
3. **MANIFEST.md** - Evidence citations, scan methodology, verification checklist
4. **DRIFT_REPORT.md** - Docs vs code mismatches, v2 vs v3 drift analysis
5. **PROJECT_STATUS.md** - Code-derived status with 3-axis matrix (Implemented/Wired/Verified)

---

## Companion: Documentation Reorganization Proposal (docs-reorg-v1)

**New folder**: `backend/docs/_staging/docs-reorg-v1/`

**Purpose**: Analyze 80+ existing docs and propose reorganization to reduce duplication, fill gaps

**Files**:
1. `START_HERE.md` - Proposal overview
2. `DOC_STRUCTURE_PROPOSAL.md` - Recommended folder structure
3. `CONTENT_SUMMARY.md` - What each doc contains
4. `DUPLICATES_AND_OVERLAPS.md` - Redundant content identification
5. `MISSING_DOCS_GAPS.md` - Documentation gaps vs code

---

## How to Use This Review

### Quick Status Check
1. Read **PROJECT_STATUS.md** summary table
2. Check **DRIFT_REPORT.md** for known gaps

### Evidence Verification
1. Review **MANIFEST.md** for all evidence citations
2. All claims cite `file_path:line_range`

### Documentation Updates
1. Compare **DRIFT_REPORT.md** findings with existing docs
2. Use **docs-reorg-v1/** proposal to restructure docs
3. Fill gaps identified in `MISSING_DOCS_GAPS.md`

---

## v2 → v3 Changes Summary

| Area | v2 Status | v3 Status | Change |
|------|-----------|-----------|--------|
| Evidence citations | File paths in doc text | File paths in MANIFEST.md | Stricter verification |
| Migration analysis | Not included | 16 migrations documented | New evidence |
| Channel Manager | Mentioned | Full structure documented | Deeper scan |
| Test coverage | Not documented | 15+ test files inventoried | New scan |
| Docs reorganization | Not proposed | New docs-reorg-v1 folder | New deliverable |
| Time since v2 | N/A | 53 minutes | Fresh snapshot |

---

## Next Steps

1. **Review MANIFEST.md**: Verify all evidence citations
2. **Review PROJECT_STATUS.md**: Understand implementation status
3. **Review DRIFT_REPORT.md**: Identify docs vs code gaps
4. **Review docs-reorg-v1/**: Consider documentation restructuring
5. **Decision on ops router**: Mount OR delete dead code
6. **Document feature flags**: Update deployment docs with required env vars

---

**Last Updated**: 2025-12-30 21:01:55 UTC
**Review Owner**: Backend Team
**Status**: Add-only (no code changes, no existing doc edits)
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd
