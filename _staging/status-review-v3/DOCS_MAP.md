# Documentation Map - v3

**Purpose**: Complete inventory of existing PMS-Webapp documentation
**Last Scanned**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd

---

## Directory Structure

```
backend/docs/
├── _staging/
│   ├── status-review-v1/          (2025-12-30 17:34 UTC, commit 393ba8da)
│   ├── status-review-v2/          (2025-12-30 20:48 UTC, commit 1c42e95)
│   ├── status-review-v3/          ⬅️ THIS REVIEW (2025-12-30 21:01 UTC)
│   └── docs-reorg-v1/             ⬅️ Documentation reorganization proposal
├── architecture/
│   ├── error-taxonomy.md          ✅ Phase 1 - Accurate (P1-06 done, P1-07 pending)
│   └── modules-and-entitlements.md
├── database/
│   ├── data-integrity.md
│   └── index-strategy.md
├── direct-booking-engine/
│   ├── stripe-integration.md
│   ├── edge-cases.md
│   └── email-templates/README.md
├── ops/
│   └── runbook.md                 ✅ Production ops guide (deployment, DB DNS, auto-heal)
├── roadmap/
│   ├── overview.md
│   ├── phase-1.md                 ⚠️ Partially accurate (ops router drift, see DRIFT_REPORT)
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
├── channel-manager/
│   └── (various .md files, not fully inventoried)
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

**Total Files**: 80+ markdown files

---

## Key Documentation Files

### 1. Operations & Deployment

#### `ops/runbook.md` ✅ Verified Accurate

**Status**: Accurate production deployment guide
**Content**:
- DB DNS troubleshooting (Coolify network attachment)
- Token validation fixes (JWT secret configuration)
- Schema drift resolution (migration procedures)
- Smoke script debugging
- Auto-heal cron setup (`pms_ensure_supabase_net.sh`)
- Container names: `pms-backend`, `pms-worker-v2`
- Network names: `bccg4gs4o4kgsowocw08wkw4` (Supabase), `coolify` (default)

**Evidence**: MANIFEST.md cites `backend/docs/ops/runbook.md`

**Deployment Facts Sourced**:
- Cron schedule: Every 2 minutes
- Log paths: `/var/log/pms_ensure_supabase_net.log`
- Health endpoint: `/health`
- Smoke test script: `backend/scripts/ops/smoke.py`

---

### 2. Architecture Documentation

#### `architecture/error-taxonomy.md` ✅ Gold Standard

**Status**: Perfectly aligned with code implementation
**Content**:
- Error code constants (defined in `backend/app/core/exceptions.py`)
- Base `AppError` class
- 3 typed exceptions: `BookingConflictError`, `PropertyNotFoundError`, `NotAuthorizedError`
- **Phase separation**: P1-06 done (error codes + typed exceptions), P1-07 pending (unified response format)

**Why This Is the Gold Standard**:
- Clear phase separation (no feature mixing)
- No speculation about unimplemented features
- Matches code exactly (verified against `backend/app/core/exceptions.py`)

**Evidence**: MANIFEST.md cites `backend/docs/architecture/error-taxonomy.md`

#### `architecture/modules-and-entitlements.md`

**Status**: Not verified in this scan
**Assumed Content**: Module system, entitlements, feature flags

#### `architecture.md` (Root)

**Status**: Not read in this scan
**Assumed Content**: High-level architecture overview

---

### 3. Roadmap & Planning

#### `roadmap/phase-1.md` ⚠️ Partially Accurate

**Status**: Some drift detected (see DRIFT_REPORT.md)
**Content**:
- RBAC finalization (P1-01) ✅ Implemented
- Tenant isolation audit (P1-02) ⚠️ Partial
- Mandatory migrations workflow (P1-03) ❌ Not started
- Error taxonomy (P1-06) ✅ Implemented (error codes + typed exceptions)
- Error response format (P1-07) ❌ Not started (unified response format pending)
- Ops runbook endpoints (P1-08, P1-09) ⚠️ DEAD CODE (router exists but NOT mounted)

**Known Drift**:
- Doc lists ops endpoints as "implemented", but router NOT mounted (see DRIFT_REPORT.md)
- Doc may combine P1-06 and P1-07, but error-taxonomy.md correctly separates them

**Evidence**: Compared with code scan results in MANIFEST.md

#### `roadmap/phase-2.md` - `phase-5.md`

**Status**: Not verified (future phases)
**Assumed Content**: Future phase planning

#### `roadmap/overview.md`

**Status**: Not read in this scan
**Assumed Content**: Roadmap overview, phase timeline

---

### 4. Tickets & Backlog

#### `tickets/phase-1.md` - `phase-5.md`

**Status**: Not read (assume they mirror roadmap phases)
**Assumed Content**: Phase ticket tracking, task breakdown

---

### 5. Phase-Specific Documentation

#### `phase17b-database-schema-rls.md`

**Content**: Database schema + RLS policies documentation
**Status**: Not verified against current schema in this scan
**Assumed Topics**: Multi-tenancy, RLS policies, schema structure

#### `phase19-core-booking-flow-api.md`

**Content**: Booking API specification
**Status**: Not verified against current implementation in this scan
**Assumed Topics**: Booking endpoints, RBAC, multi-tenancy

#### Other Phase Docs

- `phase7-qa-security.md` - QA and security practices
- `phase8.index.md`, `phase9.index.md` - Phase 8/9 planning
- `phase9-release-plan.md` - Release planning
- `phase10a-ui-ux.md`, `phase10a.index.md` - UI/UX design
- `phase10b-10c-visual-design.md` - Visual design system
- `phase15-16-direct-booking-eigentuemer.md` - Direct booking feature
- `phase18a-preflight.md` - Preflight checks

**Status**: Not read in this scan

---

### 6. Database Documentation

#### `database/data-integrity.md`

**Assumed Content**: Data integrity constraints, validation rules, foreign key relationships
**Status**: Not read in this scan

#### `database/index-strategy.md`

**Assumed Content**: Database indexing strategy, query optimization
**Status**: Not read in this scan

**Related Evidence**: MANIFEST.md documents 16 database migrations in `supabase/migrations/`

---

### 7. Direct Booking Engine

#### `direct-booking-engine/stripe-integration.md`

**Assumed Content**: Stripe payment integration, webhook handling
**Status**: Not read (future feature)

#### `direct-booking-engine/edge-cases.md`

**Assumed Content**: Edge cases for direct booking flow
**Status**: Not read (future feature)

#### `direct-booking-engine/email-templates/README.md`

**Assumed Content**: Email template documentation, transactional emails
**Status**: Not read (future feature)

---

### 8. Channel Manager Documentation

**Directory**: `backend/docs/channel-manager/`
**Status**: Not fully inventoried in this scan
**Assumed Content**: Channel Manager architecture, adapters, sync engine, webhooks

**Related Evidence**: MANIFEST.md documents Channel Manager code structure at `backend/app/channel_manager/`

---

### 9. Staging Reviews

#### `_staging/status-review-v1/` (2025-12-30 17:34 UTC)

**Commit**: 393ba8da51b67fdd832b92232c43c524c3edec88
**Files**: 5 markdown files
**Issues**: API prefix errors, ops router not mounted (discovered in v2)

#### `_staging/status-review-v2/` (2025-12-30 20:48 UTC)

**Commit**: 1c42e9598044a0928462522f58e1a8019ad1737e
**Files**: 5 markdown files
**Improvements**: Corrected API prefixes, documented ops router dead code, frontend ops console

#### `_staging/status-review-v3/` ⬅️ THIS REVIEW (2025-12-30 21:01 UTC)

**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd
**Files**: 5 markdown files
**Improvements**: Stricter evidence citations in MANIFEST, migration analysis, channel manager structure, test coverage

#### `_staging/docs-reorg-v1/` ⬅️ NEW: Documentation Reorganization Proposal

**Purpose**: Analyze 80+ existing docs and propose reorganization
**Files**: 5 markdown files (START_HERE, DOC_STRUCTURE_PROPOSAL, CONTENT_SUMMARY, DUPLICATES_AND_OVERLAPS, MISSING_DOCS_GAPS)

---

## Documentation Quality Assessment

### ✅ Accurate & Up-to-Date

1. **ops/runbook.md** - Production deployment guide (verified against code)
2. **architecture/error-taxonomy.md** - Perfect code alignment (P1-06 done, P1-07 pending)

### ⚠️ Partially Accurate

1. **roadmap/phase-1.md** - Some deliverables ahead of reality (ops router dead code)

### ❓ Unknown / Not Verified

1. **architecture.md** - Root architecture doc (not read)
2. **database/** docs - Schema and indexing docs (not read)
3. **phase17b-database-schema-rls.md** - RLS documentation (not read)
4. **phase19-core-booking-flow-api.md** - Booking API spec (not read)
5. **roadmap/overview.md** - Roadmap overview (not read)
6. **tickets/** - Phase tickets (not read)
7. **channel-manager/** docs - Channel Manager documentation (not fully inventoried)

---

## Missing Documentation

Based on code scan (see MANIFEST.md for evidence), these areas lack documentation:

### 1. Module System

- **What**: FastAPI module registry, graceful degradation, feature flags
- **Code Evidence**: `backend/app/modules/bootstrap.py`, `backend/app/main.py:117-136`
- **Why Missing**: Discovered in v2, not documented in roadmap/architecture
- **Impact**: Deployment config unclear (MODULES_ENABLED flag undocumented)
- **Recommendation**: Create `architecture/module-system.md`

### 2. Frontend Authentication

- **What**: Supabase SSR, middleware, admin role checks
- **Code Evidence**: `frontend/middleware.ts`, `frontend/app/ops/layout.tsx:27-92`
- **Why Missing**: Frontend docs not in `backend/docs/`
- **Impact**: Frontend deployment unclear (SSR session handling undocumented)
- **Recommendation**: Create `frontend/docs/authentication.md`

### 3. API Prefix Convention

- **What**: All API routes under `/api/v1` prefix
- **Code Evidence**: `backend/app/main.py:134-136`
- **Why Missing**: Not explicitly documented in architecture.md
- **Impact**: API client examples incorrect, API documentation incomplete
- **Recommendation**: Update `architecture.md` with "API Versioning" section

### 4. Feature Flags

- **What**: 3 feature flags controlling deployment behavior
  1. `MODULES_ENABLED` (default: true) - Module system vs fallback
  2. `CHANNEL_MANAGER_ENABLED` (default: false) - Channel Manager module
  3. `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` - Frontend ops console
- **Code Evidence**:
  - `backend/app/main.py:117` (MODULES_ENABLED)
  - `backend/app/modules/bootstrap.py:86` (CHANNEL_MANAGER_ENABLED)
  - `frontend/app/ops/layout.tsx:95` (NEXT_PUBLIC_ENABLE_OPS_CONSOLE)
- **Why Missing**: No centralized feature flag documentation
- **Impact**: Deployment configuration incomplete, ops staff unaware of toggles
- **Recommendation**: Create `ops/feature-flags.md`

### 5. Channel Manager Architecture

- **What**: Sync engine, adapters (Airbnb), webhooks, rate limiting, circuit breaker
- **Code Evidence**: `backend/app/channel_manager/` (12 files)
- **Why Missing**: Implementation exists but no architecture doc
- **Impact**: Channel Manager unclear to new developers, no design decisions documented
- **Recommendation**: Create `architecture/channel-manager.md`

### 6. Database Migrations Guide

- **What**: Migration workflow, how to create migrations, naming conventions
- **Code Evidence**: 16 migrations in `supabase/migrations/`
- **Why Missing**: No guide on migration best practices
- **Impact**: Developers uncertain about migration workflow
- **Recommendation**: Create `database/migrations-guide.md`

### 7. EXCLUSION Constraint Documentation

- **What**: PostgreSQL EXCLUSION constraint for double-booking prevention
- **Code Evidence**: `supabase/migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql`
- **Why Missing**: Critical concurrency control mechanism undocumented
- **Impact**: Developers unaware of database-level double-booking protection
- **Recommendation**: Create `database/exclusion-constraints.md` OR add section to `database/data-integrity.md`

### 8. Test Coverage Documentation

- **What**: Test organization, how to run tests, test fixtures
- **Code Evidence**: 15+ test files in `backend/tests/{unit,integration,security,smoke}/`
- **Why Missing**: No testing guide for contributors
- **Impact**: Contributors uncertain about test structure, how to add tests
- **Recommendation**: Create `testing/README.md`

---

## Documentation Conventions

### File Naming

- Roadmap: `roadmap/phase-{N}.md`
- Tickets: `tickets/phase-{N}.md`
- Architecture: `architecture/{topic}.md`
- Ops: `ops/{topic}.md`
- Database: `database/{topic}.md`

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

- **status-review-v1/** - First review (2025-12-30 17:34 UTC, commit 393ba8da)
- **status-review-v2/** - Second review (2025-12-30 20:48 UTC, commit 1c42e95)
- **status-review-v3/** - **THIS REVIEW** (2025-12-30 21:01 UTC, commit 3490c89)
- **docs-reorg-v1/** - Documentation reorganization proposal (NEW)

---

## How to Update This Map

When adding new documentation:
1. Add entry to Directory Structure tree
2. Add summary in Key Documentation Files section
3. Update Quality Assessment
4. Update Missing Documentation if gap filled
5. Commit with message: `docs: update documentation map`

---

**Last Updated**: 2025-12-30 21:01:55 UTC
**Next Review**: After Phase 1 completion or major architectural changes
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd
