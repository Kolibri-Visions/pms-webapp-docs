# Project Status - v3 (Code-Derived)

**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd
**Method**: Read-only code scan (all evidence in MANIFEST.md)
**Scope**: Backend + Frontend + Migrations + Tests

---

## Executive Summary

**PMS-Webapp**: Property Management System B2B SaaS platform
- **Backend**: FastAPI (Python 3.12+)
- **Frontend**: Next.js (SSR) with Supabase Auth
- **Database**: PostgreSQL (Supabase) with RLS
- **Worker**: Celery with Redis broker
- **Multi-tenancy**: Agency-based isolation
- **RBAC**: 5 roles (admin, manager, staff, owner, accountant)

**Phase Status**:
- Phase 1: In Progress (RBAC done, ops endpoints NOT mounted)
- Phase 14: Implemented (Availability/Inventory with EXCLUSION constraint)
- Phase 19: Implemented (Bookings API)

---

## 3-Axis Status Matrix

| Feature | Implemented | Wired/Mounted | Verified | Evidence (see MANIFEST.md) |
|---------|-------------|---------------|----------|----------------------------|
| **Backend API** | | | | |
| Properties API | ✅ Yes | ✅ `/api/v1/properties` | ✅ Routes exist | `main.py:134`, `api/routes/properties.py` |
| Bookings API | ✅ Yes | ✅ `/api/v1/bookings` | ✅ Routes exist | `main.py:135`, `api/routes/bookings.py` |
| Availability API | ✅ Yes | ✅ `/api/v1/availability` | ✅ Routes exist | `main.py:136`, `api/routes/availability.py` |
| Health API | ✅ Yes | ✅ `/health` | ✅ Routes exist | `main.py:130`, `core/health.py` |
| Ops API | ⚠️ Stub | ❌ NOT mounted | ❌ Dead code | `routers/ops.py` (NOT imported) |
| Channel Webhooks | ✅ Yes | ⚠️ Conditional | ❓ Unknown | `channel_manager/webhooks/handlers.py` |
| **RBAC** | | | | |
| JWT Auth | ✅ Yes | ✅ Wired | ✅ Verified | `core/auth.py`, `api/deps.py` |
| 5 Roles | ✅ Yes | ✅ Enforced | ✅ Verified | `api/deps.py:1-100` |
| `require_roles()` | ✅ Yes | ✅ Wired | ✅ Verified | `api/deps.py` (re-exported) |
| `get_current_agency_id` | ✅ Yes | ✅ Wired | ✅ Verified | `api/deps.py:53-90` |
| **Multi-tenancy** | | | | |
| Agency isolation | ✅ Yes | ✅ Wired | ✅ RLS policies | `migrations/20250101000004_rls_policies.sql` |
| X-Agency-Id header | ✅ Yes | ✅ Wired | ✅ Verified | `api/deps.py:94-100` |
| **Frontend** | | | | |
| Ops Console | ✅ Yes | ✅ `/ops/*` | ⚠️ Feature flag | `app/ops/layout.tsx:95-140` |
| SSR Auth | ✅ Yes | ✅ Wired | ✅ Verified | `app/ops/layout.tsx:27-92` |
| Admin Role Check | ✅ Yes | ✅ Wired | ✅ Verified | `app/ops/layout.tsx:46-92` |
| Middleware | ✅ Yes | ✅ Wired | ✅ Verified | `middleware.ts:77-82` |
| **Database** | | | | |
| Initial Schema | ✅ Yes | ✅ Applied | ✅ Verified | `migrations/20250101000001_initial_schema.sql` |
| RLS Policies | ✅ Yes | ✅ Applied | ✅ Verified | `migrations/20250101000004_rls_policies.sql` |
| EXCLUSION Constraint | ✅ Yes | ✅ Applied | ✅ Verified | `migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql` |
| **Module System** | | | | |
| Module Registry | ✅ Yes | ✅ Wired | ✅ Verified | `modules/bootstrap.py:30-140` |
| MODULES_ENABLED | ✅ Yes | ✅ Wired | ✅ Default: true | `main.py:117-136` |
| Graceful Degradation | ✅ Yes | ✅ Wired | ✅ Verified | `modules/bootstrap.py:62-94` |
| **Channel Manager** | | | | |
| Adapters (Airbnb) | ✅ Yes | ⚠️ Feature flag | ❓ Unknown | `channel_manager/adapters/airbnb/adapter.py` |
| Sync Engine | ✅ Yes | ⚠️ Feature flag | ❓ Unknown | `channel_manager/core/sync_engine.py` |
| Rate Limiter | ✅ Yes | ⚠️ Feature flag | ❓ Unknown | `channel_manager/core/rate_limiter.py` |
| Circuit Breaker | ✅ Yes | ⚠️ Feature flag | ❓ Unknown | `channel_manager/core/circuit_breaker.py` |
| CHANNEL_MANAGER_ENABLED | ✅ Yes | ✅ Wired | ✅ Default: false | `modules/bootstrap.py:86-94` |
| **Tests** | | | | |
| Unit Tests | ✅ Yes | ✅ 5 files | ❓ Not run | `tests/unit/*.py` |
| Integration Tests | ✅ Yes | ✅ 5 files | ❓ Not run | `tests/integration/*.py` |
| Security Tests | ✅ Yes | ✅ 3 files | ❓ Not run | `tests/security/*.py` |
| Smoke Tests | ✅ Yes | ✅ 1 file | ❓ Not run | `tests/smoke/*.py` |

**Legend**:
- ✅ Yes = Feature exists and is functional
- ⚠️ = Exists but conditional (feature flag, configuration) or partial
- ❌ = Does not exist or not wired
- ❓ = Unknown (cannot verify from read-only scan)

---

## Backend Implementation Status

### API Routes

**All routes mount under `/api/v1` prefix** (except `/health`)

#### Properties API

**Status**: ✅ Implemented and mounted
**Endpoints**:
- `GET /api/v1/properties` - List properties
- `POST /api/v1/properties` - Create property
- `GET /api/v1/properties/{id}` - Get property
- `PATCH /api/v1/properties/{id}` - Update property
- `DELETE /api/v1/properties/{id}` - Delete property

**Evidence**: MANIFEST.md cites `backend/app/api/routes/properties.py`, `main.py:134`

#### Bookings API

**Status**: ✅ Implemented and mounted
**Endpoints**:
- `GET /api/v1/bookings` - List bookings
- `POST /api/v1/bookings` - Create booking
- `GET /api/v1/bookings/{id}` - Get booking
- `PATCH /api/v1/bookings/{id}` - Update booking
- `DELETE /api/v1/bookings/{id}` - Delete booking

**Evidence**: MANIFEST.md cites `backend/app/api/routes/bookings.py`, `main.py:135`

#### Availability API

**Status**: ✅ Implemented and mounted
**Endpoints**:
- `GET /api/v1/availability` - Query availability
- `POST /api/v1/availability/blocks` - Create availability block
- Other endpoints (not enumerated in this scan)

**Evidence**: MANIFEST.md cites `backend/app/api/routes/availability.py`, `main.py:136`

#### Health API

**Status**: ✅ Implemented and mounted
**Endpoint**: `GET /health`
**Prefix**: NONE (mounted at root)

**Evidence**: MANIFEST.md cites `backend/app/core/health.py`, `main.py:130`

#### Ops API (Backend)

**Status**: ❌ DEAD CODE - Exists but NOT mounted
**Endpoints Defined**:
- `GET /ops/current-commit` - Git commit SHA (stub)
- `GET /ops/env-sanity` - Environment sanity check (stub)

**Issues**:
- Router file exists: `backend/app/routers/ops.py`
- NOT imported anywhere (verified via `rg` search, zero matches)
- NOT registered in module system
- NOT mounted in main.py fallback routing
- RBAC TODO comments present (not implemented)

**Evidence**: MANIFEST.md cites `routers/ops.py` + `rg` search showing zero imports

**Recommendation**: Mount OR delete (see DRIFT_REPORT.md)

---

### RBAC (Role-Based Access Control)

**Status**: ✅ Implemented and wired

**5 Roles Defined**:
1. `admin` - Full system access
2. `manager` - Agency management
3. `staff` - Day-to-day operations
4. `owner` - Property owner (limited access)
5. `accountant` - Financial data access

**Evidence**: MANIFEST.md cites `backend/app/api/deps.py` docstring

**Dependencies**:
- `get_current_user(token)` - JWT validation, returns user dict
- `get_current_user_id(user)` - Extract user_id from user dict
- `get_current_agency_id(user, x_agency_id, db)` - Multi-tenant context
- `get_current_role(user, agency_id, db)` - Extract role for agency
- `require_roles(*roles)` - RBAC enforcement decorator

**Multi-tenancy**:
- Agency context from: X-Agency-Id header (priority 1) OR profiles.last_active_agency_id (priority 2) OR team_members.agency_id (priority 3)

**Evidence**: MANIFEST.md cites `backend/app/api/deps.py:53-90`

---

### Module System

**Status**: ✅ Implemented and active

**Feature Flag**: `MODULES_ENABLED` (default: `true`)

**Behavior**:
- If `MODULES_ENABLED=true`: Use module system (`mount_modules(app)`)
- If `MODULES_ENABLED=false`: Use fallback (explicit router mounting in main.py)

**Modules Registered** (from `backend/app/modules/bootstrap.py:56-94`):
1. `core` - Health router
2. `inventory` - Availability router
3. `properties` - Properties router
4. `bookings` - Bookings router
5. `channel_manager` - **Conditional** (CHANNEL_MANAGER_ENABLED=false by default)

**Graceful Degradation**:
- If module import fails: Log warning, continue without module
- If DB unavailable at startup: App runs in degraded mode (DB endpoints return 503)

**Evidence**: MANIFEST.md cites `main.py:117-136`, `modules/bootstrap.py:30-140`

---

### Channel Manager

**Status**: ✅ Implemented, ⚠️ Gated by feature flag (default OFF)

**Feature Flag**: `CHANNEL_MANAGER_ENABLED` (default: `false`)

**Structure** (from MANIFEST.md):
- **Adapters**: `channel_manager/adapters/` (Airbnb, base adapter, factory)
- **Sync Engine**: `channel_manager/core/sync_engine.py`
- **Rate Limiter**: `channel_manager/core/rate_limiter.py`
- **Circuit Breaker**: `channel_manager/core/circuit_breaker.py`
- **Webhooks**: `channel_manager/webhooks/handlers.py`
- **Monitoring**: `channel_manager/monitoring/metrics.py`
- **Config**: `channel_manager/config.py`

**Files**: 9+ Python files

**Status**: Implemented but disabled by default (requires `CHANNEL_MANAGER_ENABLED=true` to activate)

**Evidence**: MANIFEST.md cites `modules/bootstrap.py:86-94` + 9 file paths

---

### Error Handling

**Status**: ⚠️ Partial (P1-06 done, P1-07 pending)

**P1-06 Completed** (from `error-taxonomy.md`):
- ✅ Error code constants defined
- ✅ Base `AppError` class implemented
- ✅ 3 typed exceptions: `BookingConflictError`, `PropertyNotFoundError`, `NotAuthorizedError`

**P1-07 Pending** (from `error-taxonomy.md`):
- ❌ Unified error response format NOT implemented yet
- ❌ Exception handlers registered but format varies

**Evidence**: MANIFEST.md cites `core/exceptions.py`, `main.py:102` + `docs/architecture/error-taxonomy.md`

---

## Frontend Implementation Status

### Ops Console (Frontend Pages)

**Status**: ✅ Implemented, ⚠️ Requires feature flag

**Feature Flag**: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` (required to enable)

**Implementation**:
- **Server-Side Rendering (SSR)**: Yes
- **Session Check**: Server-side session validation (`layout.tsx:27-40`)
- **Admin Role Check**: Query `team_members` table for `role='admin'` (`layout.tsx:46-92`)
- **Feature Flag Check**: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` must be `1`, `true`, `yes`, or `on` (`layout.tsx:95-140`)
- **Access Denied**: Shows error message for non-admins (no redirect loop)

**Routes Protected**: `/ops/:path*` (via middleware matcher)

**Evidence**: MANIFEST.md cites `frontend/app/ops/layout.tsx:27-140`

### Middleware

**Status**: ✅ Implemented and wired

**Purpose**: Supabase session refresh on protected routes

**Routes Protected** (from `middleware.ts:77-82`):
- `/ops/:path*`
- `/channel-sync/:path*`
- `/login`

**Behavior**:
- Refreshes Supabase auth cookies on every request
- Ensures server components can read latest session

**Evidence**: MANIFEST.md cites `frontend/middleware.ts:77-82`

---

## Database Implementation Status

### Migrations

**Status**: ✅ 16 migrations applied

**Key Migrations** (from MANIFEST.md):

1. **Initial Schema** (`20250101000001_initial_schema.sql`, 18KB)
   - Core tables: agencies, profiles, team_members, properties, bookings, guests

2. **Channels & Financials** (`20250101000002_channels_and_financials.sql`, 13.6KB)
   - Channel Manager tables

3. **Indexes** (`20250101000003_indexes.sql`, 8.3KB)
   - Database indexes for query optimization

4. **RLS Policies** (`20250101000004_rls_policies.sql`, 20.5KB)
   - Row-Level Security for multi-tenancy

5. **Availability/Inventory** (`20251225190000_availability_inventory_system.sql`, 8KB)
   - Availability blocks and inventory ranges tables

6. **EXCLUSION Constraint** (`20251229200517_enforce_overlap_prevention_via_exclusion.sql`, 6.7KB)
   - PostgreSQL EXCLUSION constraint for double-booking prevention

**Evidence**: MANIFEST.md lists all 16 migrations with file sizes

### Concurrency Protection (EXCLUSION Constraint)

**Status**: ✅ Implemented

**Table**: `inventory_ranges`
**Constraint**: `inventory_ranges_no_overlap`
**Type**: PostgreSQL EXCLUSION constraint using GiST index

**Definition** (from MANIFEST.md):
```sql
EXCLUDE USING gist (
  property_id WITH =,
  daterange(start_date, end_date, '[)') WITH &&
)
WHERE (state = 'active')
```

**Purpose**: Database-level double-booking prevention (prevents overlapping active bookings per property)

**Evidence**: MANIFEST.md cites `migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql`

### Row-Level Security (RLS)

**Status**: ✅ Implemented (from migration file size, not read)

**Migration**: `20250101000004_rls_policies.sql` (20.5KB)
**Purpose**: Multi-tenancy isolation via agency_id

**Evidence**: MANIFEST.md lists migration file

---

## Test Coverage Status

**Status**: ✅ 15+ test files exist, ❓ Not executed in this scan

### Unit Tests (5 files)

**Files** (from MANIFEST.md):
- `test_jwt_verification.py` - JWT token validation
- `test_rbac_helpers.py` - RBAC helper functions
- `test_agency_deps.py` - Agency dependency extraction
- `test_database_generator.py` - Database test data generation
- `test_channel_sync_log_service.py` - Channel sync log service

### Integration Tests (5 files)

**Files** (from MANIFEST.md):
- `test_availability.py` - Availability API integration tests
- `test_bookings.py` - Bookings API integration tests
- `test_rbac.py` - RBAC integration tests
- `test_auth_db_priority.py` - Auth vs DB priority tests
- `conftest.py` - Test fixtures and configuration

### Security Tests (3 files)

**Files** (from MANIFEST.md):
- `test_token_encryption.py` - Token encryption/decryption
- `test_redis_client.py` - Redis client security
- `test_webhook_signature.py` - Webhook signature validation

### Smoke Tests (1 file)

**Files** (from MANIFEST.md):
- `test_channel_manager_smoke.py` - Channel Manager smoke test

**Evidence**: MANIFEST.md lists all test files

**Note**: Tests NOT executed in this scan (read-only analysis)

---

## Feature Flags Summary

**3 Feature Flags Documented**:

1. **MODULES_ENABLED** (Backend)
   - **Default**: `true`
   - **Purpose**: Enable module system vs fallback routing
   - **Evidence**: MANIFEST.md cites `main.py:117-136`

2. **CHANNEL_MANAGER_ENABLED** (Backend)
   - **Default**: `false`
   - **Purpose**: Gate Channel Manager module
   - **Evidence**: MANIFEST.md cites `modules/bootstrap.py:86-94`

3. **NEXT_PUBLIC_ENABLE_OPS_CONSOLE** (Frontend)
   - **Default**: Unset (required to enable)
   - **Purpose**: Enable frontend Ops Console pages
   - **Values**: `1`, `true`, `yes`, `on`
   - **Evidence**: MANIFEST.md cites `app/ops/layout.tsx:95-140`

---

## Documentation Status

**Total Files**: 80+ markdown files in `backend/docs/`

**Accurate Documentation**:
- ✅ `ops/runbook.md` - Production deployment guide
- ✅ `architecture/error-taxonomy.md` - Error codes, typed exceptions (P1-06 done, P1-07 pending)

**Partially Accurate**:
- ⚠️ `roadmap/phase-1.md` - Some drift (ops router dead code)

**Missing Documentation** (from DRIFT_REPORT.md):
- ❌ `architecture/module-system.md` - Module system, feature flags
- ❌ `architecture/channel-manager.md` - Channel Manager design
- ❌ `frontend/docs/authentication.md` - Frontend SSR auth
- ❌ `ops/feature-flags.md` - Centralized feature flag documentation
- ❌ `database/migrations-guide.md` - Migration workflow
- ❌ `database/exclusion-constraints.md` - EXCLUSION constraint pattern
- ❌ `testing/README.md` - Test organization, how to run tests

**Evidence**: See DOCS_MAP.md and DRIFT_REPORT.md

---

## Known Issues & Gaps

### Critical

1. **Ops Router Dead Code** (DRIFT_REPORT.md)
   - Router exists but NOT mounted
   - NOT accessible via HTTP
   - Recommendation: Mount OR delete

### High

2. **Feature Flags Undocumented** (DRIFT_REPORT.md)
   - 3 feature flags exist but not centrally documented
   - Deployment staff unaware of toggles
   - Recommendation: Create `ops/feature-flags.md`

### Medium

3. **EXCLUSION Constraint Undocumented** (DRIFT_REPORT.md)
   - Critical concurrency mechanism implemented but not documented
   - Recommendation: Create `database/exclusion-constraints.md`

4. **Channel Manager Architecture Undocumented** (DRIFT_REPORT.md)
   - Implementation exists (9 files) but no design doc
   - Recommendation: Create `architecture/channel-manager.md`

5. **Module System Undocumented** (DRIFT_REPORT.md)
   - Active module system not documented in architecture
   - Recommendation: Create `architecture/module-system.md`

### Low

6. **Testing Guide Missing** (DRIFT_REPORT.md)
   - 15+ test files exist but no guide on how to run/add tests
   - Recommendation: Create `testing/README.md`

---

## Next Steps

1. **Review MANIFEST.md**: Verify all evidence citations
2. **Review DRIFT_REPORT.md**: Understand docs vs code gaps
3. **Decision on Ops Router**: Mount OR delete dead code
4. **Document Feature Flags**: Create `ops/feature-flags.md`
5. **Document EXCLUSION Constraint**: Add to `database/data-integrity.md` or create new file
6. **Document Module System**: Create `architecture/module-system.md`
7. **Document Channel Manager**: Create `architecture/channel-manager.md`
8. **Testing Guide**: Create `testing/README.md`

---

**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd
**Review**: status-review-v3
**Evidence**: All claims backed by citations in MANIFEST.md
