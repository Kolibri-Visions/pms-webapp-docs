# Documentation Map

**Purpose**: Inventory of existing PMS-Webapp documentation
**Last Scanned**: 2025-12-30 20:48:06 UTC

---

## Directory Structure

```
backend/docs/
├── _staging/
│   ├── status-review-v1/          ⬅️ Previous review (2025-12-30 17:34)
│   └── status-review-v2/          ⬅️ THIS REVIEW (2025-12-30 20:48)
├── architecture/
│   ├── error-taxonomy.md          ✅ Phase 1 - Accurate
│   └── modules-and-entitlements.md (Referenced but not verified)
├── database/
│   ├── data-integrity.md
│   └── index-strategy.md
├── direct-booking-engine/
│   ├── stripe-integration.md
│   ├── edge-cases.md
│   └── email-templates/README.md
├── ops/
│   └── runbook.md                 ✅ Production ops guide
├── roadmap/
│   ├── overview.md
│   ├── phase-1.md                 ⚠️ Partially accurate (see DRIFT_REPORT)
│   ├── phase-2.md
│   ├── phase-3.md
│   ├── phase-4.md
│   └── phase-5.md
├── tickets/
│   ├── phase-1.md
│   ├── phase-2.md
│   ├── phase-3.md
│   ├── phase-4.md
│   └── phase-5.md
├── architecture.md                (Root architecture doc)
├── github-setup.md
├── phase7-qa-security.md
├── phase8.index.md
├── phase9.index.md
├── phase9-release-plan.md
├── phase10a-ui-ux.md
├── phase10a.index.md
├── phase10b-10c-visual-design.md
├── phase15-16-direct-booking-eigentuemer.md
├── phase17b-database-schema-rls.md
├── phase18a-preflight.md
└── phase19-core-booking-flow-api.md
```

---

## Key Documentation Files

### 1. Operations & Deployment

#### `ops/runbook.md` ✅ Verified
**Status**: Accurate production guide
**Content**:
- DB DNS troubleshooting (Coolify network attachment)
- Token validation fixes
- Schema drift resolution
- Smoke script debugging
- Auto-heal cron setup (`pms_ensure_supabase_net.sh`)

**Evidence**: File read confirms deployment procedures, network names, script paths

**Deployment Facts Sourced**:
- Network: `bccg4gs4o4kgsowocw08wkw4` (Supabase network)
- Default network: `coolify`
- Container names: `pms-backend`, `pms-worker-v2`
- Cron schedule: Every 2 minutes
- Log paths: `/var/log/pms_ensure_supabase_net.log`

---

### 2. Architecture Documentation

#### `architecture/error-taxonomy.md` ✅ Accurate
**Status**: Perfectly aligned with code
**Content**:
- Error code constants
- Base `AppError` class
- Typed exceptions (BookingConflictError, PropertyNotFoundError, NotAuthorizedError)
- **Explicitly states**: P1-06 done (error codes), P1-07 pending (response format)

**Why This Is the Gold Standard**:
- Clear phase separation (P1-06 vs P1-07)
- No speculation about unimplemented features
- Matches code exactly

**Evidence**: `backend/app/core/exceptions.py`, doc lines 128-168

#### `architecture.md` (Root)
**Status**: Not verified in this scan
**Assumed Content**: High-level architecture overview

---

### 3. Roadmap & Planning

#### `roadmap/phase-1.md` ⚠️ Partially Accurate
**Status**: Some drift detected (see DRIFT_REPORT.md)
**Content**:
- RBAC finalization (P1-01) ✅ Implemented
- Tenant isolation audit (P1-02) ⚠️ Partial
- Mandatory migrations workflow (P1-03) ❌ Not started
- Error taxonomy (P1-06) ✅ Implemented
- Error response format (P1-07) ❌ Not started
- Ops runbook endpoints (P1-08, P1-09) ⚠️ Stub (router not mounted)

**Drift**:
- Doc lists ops endpoints as deliverable, but router NOT mounted
- Doc combines P1-06 and P1-07, but error-taxonomy.md separates them correctly

**Evidence**: Compared with code scan results

#### `roadmap/phase-2.md` - `phase-5.md`
**Status**: Not verified (future phases)

#### `roadmap/overview.md`
**Status**: Not read in this scan

---

### 4. Tickets & Backlog

#### `tickets/phase-1.md` - `phase-5.md`
**Status**: Not read (assume they mirror roadmap phases)

---

### 5. Phase-Specific Documentation

#### `phase17b-database-schema-rls.md`
**Content**: Database schema + RLS policies documentation
**Status**: Not verified against current schema

#### `phase19-core-booking-flow-api.md`
**Content**: Booking API specification
**Status**: Not verified against current implementation

#### `phase7-qa-security.md`, `phase8.index.md`, `phase9.index.md`, etc.
**Status**: Not read in this scan

---

### 6. Database Documentation

#### `database/data-integrity.md`
**Assumed Content**: Data integrity constraints, validation rules

#### `database/index-strategy.md`
**Assumed Content**: Database indexing strategy

**Status**: Not read in this scan

---

### 7. Direct Booking Engine

#### `direct-booking-engine/stripe-integration.md`
**Assumed Content**: Stripe payment integration

#### `direct-booking-engine/edge-cases.md`
**Assumed Content**: Edge cases for direct booking

#### `direct-booking-engine/email-templates/README.md`
**Assumed Content**: Email template documentation

**Status**: Not read (future feature)

---

## Documentation Quality Assessment

### ✅ Accurate & Up-to-Date
1. **ops/runbook.md** - Production deployment guide
2. **architecture/error-taxonomy.md** - Perfect code alignment

### ⚠️ Partially Accurate
1. **roadmap/phase-1.md** - Some deliverables ahead of reality

### ❓ Unknown / Not Verified
1. **architecture.md** - Root architecture doc
2. **database/** docs - Schema and indexing docs
3. **phase17b-database-schema-rls.md** - RLS documentation
4. **phase19-core-booking-flow-api.md** - Booking API spec
5. **roadmap/overview.md** - Roadmap overview
6. **tickets/** - Phase tickets

---

## Missing Documentation

Based on code scan, these areas lack documentation:

### 1. Module System
- **What**: FastAPI module registry, graceful degradation, feature flags
- **Why Missing**: v2 discovery (not documented in v1)
- **Impact**: Deployment config unclear
- **Recommendation**: Create `architecture/module-system.md`

**Evidence**: `backend/app/modules/bootstrap.py`, `backend/app/main.py:117-136`

### 2. Frontend Authentication
- **What**: Supabase SSR, middleware, admin role checks
- **Why Missing**: Frontend docs not in backend/docs/
- **Impact**: Frontend deployment unclear
- **Recommendation**: Create `frontend/docs/authentication.md`

**Evidence**: `frontend/middleware.ts`, `frontend/app/ops/layout.tsx`

### 3. API Prefix Convention
- **What**: All API routes under `/api/v1`
- **Why Missing**: Not explicitly documented
- **Impact**: API client examples incorrect
- **Recommendation**: Update `architecture.md` with API versioning section

**Evidence**: `backend/app/main.py:134-136`

### 4. Feature Flags
- **What**: MODULES_ENABLED, CHANNEL_MANAGER_ENABLED, NEXT_PUBLIC_ENABLE_OPS_CONSOLE
- **Why Missing**: No centralized feature flag documentation
- **Impact**: Deployment configuration missing
- **Recommendation**: Create `ops/feature-flags.md`

**Evidence**: `backend/app/main.py:117`, `backend/app/modules/bootstrap.py:86`, `frontend/app/ops/layout.tsx:95`

### 5. Channel Manager Architecture
- **What**: Sync engine, adapters, Celery tasks
- **Why Missing**: Implementation exists but no architecture doc
- **Impact**: Channel manager unclear to new developers
- **Recommendation**: Create `architecture/channel-manager.md`

**Evidence**: `backend/app/channel_manager/` directory structure

---

## Documentation Conventions

### File Naming
- Roadmap: `roadmap/phase-{N}.md`
- Tickets: `tickets/phase-{N}.md`
- Architecture: `architecture/{topic}.md`
- Ops: `ops/{topic}.md`

### Cross-References
- Relative links: `../roadmap/phase-1.md`
- Internal anchors: `#section-name`

### Status Markers
- ✅ Completed/Accurate
- ⚠️ Partial/In Progress
- ❌ Not Started/Inaccurate
- ❓ Unknown/Not Verified

---

## Related Reviews

- **status-review-v1/** - Previous review (3.25 hours earlier, same commit)
- **status-review-v2/** - This review (current)

---

## How to Update This Map

When adding new documentation:
1. Add entry to Directory Structure tree
2. Add summary in Key Documentation Files section
3. Update Quality Assessment
4. Update Missing Documentation if gap filled
5. Commit with message: `docs: update documentation map`

---

**Last Updated**: 2025-12-30 20:48:06 UTC
**Next Review**: After Phase 1 completion
