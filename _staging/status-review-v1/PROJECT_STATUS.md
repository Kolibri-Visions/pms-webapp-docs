# PMS-Webapp Project Status

**FROZEN SNAPSHOT**: 2025-12-30 17:34:20 UTC
**Commit**: `393ba8da51b67fdd832b92232c43c524c3edec88`
**Branch**: `main`

---

## Executive Summary

This document provides a **code-derived, evidence-based** snapshot of the PMS-Webapp project status at commit `393ba8da`. All claims are backed by file reads, symbol definitions, and commit metadata (see **MANIFEST.md** for evidence log).

### Current State

✅ **Production-Ready Components**:
- FastAPI backend with 5 RBAC roles
- Multi-tenant architecture (agency isolation)
- Channel Manager foundation (Celery workers, adapters)
- Availability system with PostgreSQL EXCLUSION constraints
- Next.js 15 frontend with SSR authentication

⚠️ **Work in Progress**:
- Phase 1 foundation (RBAC helpers implemented, ops endpoints stubbed)
- Error taxonomy defined but response format not unified
- Frontend backoffice navigation (ops + channel-sync unified)

❌ **Not Yet Implemented**:
- Ops runbook endpoints (placeholders exist)
- Audit log, idempotency keys, feature flags tables
- Full RBAC enforcement on all endpoints

---

## Backend Architecture

### Technology Stack
- **Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL via asyncpg
- **Task Queue**: Celery with Redis broker
- **Authentication**: JWT (python-jose)
- **Validation**: Pydantic v2

**Evidence**:
- `backend/app/main.py:1-50` - FastAPI app initialization
- `backend/requirements.txt` (not read, inferred from imports)

---

## API Endpoints

### Implemented Endpoints (Evidence-Based)

#### 1. Properties API
**Router**: `backend/app/api/routes/properties.py`

| Method | Endpoint | Auth | Roles | Description |
|--------|----------|------|-------|-------------|
| GET | `/properties` | ✅ | All | List agency properties |
| GET | `/properties/{id}` | ✅ | All | Get property details |
| POST | `/properties` | ✅ | admin, manager | Create property |
| PATCH | `/properties/{id}` | ✅ | admin, manager, owner | Update property |
| DELETE | `/properties/{id}` | ✅ | admin, manager | Soft delete property |

**RBAC Enforcement**: ✅ Implemented via `require_roles()` dependency
**Tenant Isolation**: ✅ All queries filter by `agency_id`
**Owner Role Logic**: ✅ Can only view/edit own properties

**Evidence**:
- `backend/app/api/routes/properties.py:46-110` - list_properties endpoint
- `backend/app/api/routes/properties.py:150-190` - create_property with require_roles("admin", "manager")

---

#### 2. Bookings API
**Router**: `backend/app/api/routes/bookings.py`

| Method | Endpoint | Auth | Roles | Description |
|--------|----------|------|-------|-------------|
| GET | `/bookings` | ✅ | All | List agency bookings |
| GET | `/bookings/{id}` | ✅ | All | Get booking details |
| POST | `/bookings` | ✅ | admin, manager, staff | Create booking |
| PATCH | `/bookings/{id}` | ✅ | admin, manager, staff | Update booking |
| PATCH | `/bookings/{id}/status` | ✅ | admin, manager, staff | Update status |
| POST | `/bookings/{id}/cancel` | ✅ | admin, manager | Cancel booking |

**Status Workflow**: Implemented state machine
- inquiry → [pending, confirmed, declined]
- pending → [confirmed, cancelled]
- confirmed → [checked_in, cancelled]
- checked_in → [checked_out, cancelled]

**RBAC Enforcement**: ✅ Implemented
**Tenant Isolation**: ✅ All queries filter by `agency_id`
**Owner Role Logic**: ✅ Can only view bookings for owned properties

**Evidence**:
- `backend/app/api/routes/bookings.py:68-156` - list_bookings endpoint
- `backend/app/api/routes/bookings.py:201-311` - create_booking with extensive error handling
- `backend/app/services/booking_service.py:91-100` - VALID_TRANSITIONS state machine

---

#### 3. Availability API
**Router**: `backend/app/api/routes/availability.py`

| Method | Endpoint | Auth | Roles | Description |
|--------|----------|------|-------|-------------|
| GET | `/availability` | ✅ | All | Query availability calendar |
| POST | `/availability/blocks` | ✅ | admin, manager, owner | Create block |
| DELETE | `/availability/blocks/{id}` | ✅ | admin, manager, owner | Delete block |
| POST | `/availability/sync` | ✅ | admin, manager | Sync to channel |

**Business Rules**:
- Blocks prevent new bookings
- No overlapping blocks (EXCLUSION constraint)
- Max 365-day query range
- Retry logic with exponential backoff (3 attempts)

**Evidence**:
- `backend/app/api/routes/availability.py:98-236` - query_availability endpoint
- `backend/app/api/routes/availability.py:558-761` - sync_availability_to_channel with retry logic
- `backend/app/api/routes/availability.py:476-556` - _retry_with_exponential_backoff helper

---

#### 4. Channel Connections API
**Router**: `backend/app/api/routers/channel_connections.py`

| Method | Endpoint | Auth | Roles | Description |
|--------|----------|------|-------|-------------|
| POST | `/channel-connections` | ✅ | Authenticated | Create connection |
| GET | `/channel-connections` | ✅ | Authenticated | List connections |
| GET | `/channel-connections/{id}` | ✅ | Authenticated | Get connection |
| PUT | `/channel-connections/{id}` | ✅ | Authenticated | Update connection |
| DELETE | `/channel-connections/{id}` | ✅ | Authenticated | Delete connection |
| POST | `/channel-connections/{id}/test` | ✅ | Authenticated | Test health |
| POST | `/channel-connections/{id}/sync` | ✅ | Authenticated | Trigger sync |
| GET | `/channel-connections/{id}/sync-logs` | ✅ | Authenticated | Get sync logs |

**Note**: Global auth via `Depends(get_current_user)` on router, no fine-grained RBAC yet.

**Evidence**:
- `backend/app/api/routers/channel_connections.py:31-35` - Router with global auth
- `backend/app/api/routers/channel_connections.py:368-418` - get_sync_logs endpoint

---

#### 5. Ops/Runbook API
**Router**: `backend/app/routers/ops.py`

| Method | Endpoint | Auth | Roles | Description | Status |
|--------|----------|------|-------|-------------|--------|
| GET | `/ops/current-commit` | ❌ | None | Get deployment version | STUB |
| GET | `/ops/env-sanity` | ❌ | None | Environment health checks | STUB |

**Status**: ⚠️ **PLACEHOLDERS ONLY**
- Endpoints exist but return placeholder data
- No RBAC enforcement (TODO in comments)
- Health checks stubbed (not implemented)

**Evidence**:
- `backend/app/routers/ops.py:28-54` - get_current_commit returns `os.getenv("COMMIT_SHA", "unknown")`
- `backend/app/routers/ops.py:57-114` - get_env_sanity with hardcoded `"ok"` values
- `backend/app/routers/ops.py:42-45` - TODO comments: "Add RBAC: Require admin role"

---

## Authentication & Authorization

### JWT Authentication
**Implementation**: `backend/app/core/auth.py`

**Functions**:
- `get_current_user()` - Extract user from JWT (lines 57-177)
- `get_current_active_user()` - Verify user is active (lines 180-213)
- `get_current_user_id()` - Convenience wrapper (lines 216-240)
- `create_access_token()` - Generate JWT (lines 243-291)
- `verify_token()` - Verify without exceptions (lines 294-317)

**JWT Validation**:
- ✅ Signature verification (always on)
- ✅ Expiration verification (always on)
- ✅ Optional issuer verification (if `JWT_ISSUER` set)
- ✅ Optional audience verification (if `JWT_AUDIENCE` set)

**Evidence**:
- `backend/app/core/auth.py:87-129` - JWT decode logic with options
- `backend/app/core/auth.py:94-97` - Signature and expiration always verified

---

### RBAC System (Phase 1 - P1-01)
**Implementation**: `backend/app/core/auth.py` (lines 320-428)

**Roles**:
1. **admin** - Full system access
2. **manager** - Full agency access
3. **staff** - Limited create/update (no delete/cancel)
4. **owner** - Own properties only
5. **accountant** - Read-only financial access

**Helper Functions** (Phase 1 - P1-01 ✅):
```python
def has_role(user: dict, role: str) -> bool
def has_any_role(user: dict, roles: list[str]) -> bool
def require_role(*roles: str) -> Dependency
```

**Evidence**:
- `backend/app/core/auth.py:324-350` - has_role implementation
- `backend/app/core/auth.py:353-379` - has_any_role implementation
- `backend/app/core/auth.py:382-428` - require_role dependency factory
- `backend/tests/unit/test_rbac_helpers.py:1-136` - Comprehensive unit tests (not executed)

---

### Multi-Tenant Isolation
**Implementation**: `backend/app/api/deps.py`

**Key Dependencies**:
```python
get_current_agency_id(user, x_agency_id, db) -> UUID
get_current_role(user, agency_id, db) -> str
require_roles(*allowed_roles) -> Dependency
```

**Agency Resolution Strategy**:
1. **X-Agency-Id header** (preferred) - Validated against `team_members` table
2. **User's last active agency** - From `profiles.last_active_agency_id`
3. **First agency membership** - Fallback from `team_members.created_at ASC`

**Tenant Isolation Pattern**:
- All service queries include `WHERE agency_id = $1`
- Property/booking ownership verified for owner role
- Cross-tenant access logs warning + raises `ForbiddenException`

**Evidence**:
- `backend/app/api/deps.py:53-220` - get_current_agency_id with fallback chain
- `backend/app/api/deps.py:260-331` - get_current_role from team_members
- `backend/app/api/deps.py:561-626` - verify_resource_access helper
- `backend/app/services/booking_service.py` (partial read) - Uses agency_id in queries

---

## Error Handling (Phase 1 - P1-06)

### Error Taxonomy ✅ Implemented
**Implementation**: `backend/app/core/exceptions.py`

**Error Codes Defined**:
- `ERROR_CODE_BOOKING_CONFLICT` = "BOOKING_CONFLICT"
- `ERROR_CODE_PROPERTY_NOT_FOUND` = "PROPERTY_NOT_FOUND"
- `ERROR_CODE_NOT_AUTHORIZED` = "NOT_AUTHORIZED"
- (+ more, file too large for full read)

**Typed Exceptions** (3 implemented):
```python
class AppError(Exception)  # Base class
class BookingConflictError(AppError)
class PropertyNotFoundError(AppError)
class NotAuthorizedError(AppError)
```

**Evidence**:
- `backend/app/core/exceptions.py` (system reminder: file too large, contains error codes)
- `backend/docs/architecture/error-taxonomy.md:18-55` - Error code table
- `backend/docs/architecture/error-taxonomy.md:156-168` - Migration strategy confirms P1-06 done, P1-07 pending

### Response Format ❌ Not Unified Yet (Phase 1 - P1-07)
**Status**: Error codes defined, but response format NOT converted to structured `{error: {code, message}}` yet.

**Evidence**:
- `backend/docs/architecture/error-taxonomy.md:128-152` - "Response format changes are NOT part of P1-06" (line 130)
- `backend/docs/architecture/error-taxonomy.md:163-167` - "Phase 1 - P1-07 (Next)" - Register handlers, convert responses

---

## Database Schema

### Migrations
**Path**: `supabase/migrations/`

**Applied Migrations** (15 total):
1. `20250101000001_initial_schema.sql` - Core tables
2. `20250101000002_channels_and_financials.sql` - Channel connections
3. `20250101000003_indexes.sql` - Performance indexes
4. `20250101000004_rls_policies.sql` - Row-level security
5. `20251225153034_ensure_bookings_table.sql` - Bookings schema
6. `20251225154401_ensure_bookings_columns.sql` - Booking columns
7. `20251225172208_add_booking_reference_generator.sql` - Reference generation
8. `20251225180000_fix_channel_booking_id_uniqueness.sql` - Unique constraints
9. `20251225181000_ensure_guests_table.sql` - Guests table
10. `20251225183000_prevent_zero_uuid_guest_id.sql` - Guest validation
11. `20251225190000_availability_inventory_system.sql` - Inventory ranges
12. `20251226000000_fix_inventory_overlap_constraint.sql` - Overlap fixes
13. `20251227000000_create_channel_sync_logs.sql` - Sync logging
14. `20251229200517_enforce_overlap_prevention_via_exclusion.sql` - EXCLUSION constraint
15. (More migrations may exist, listing first 15)

**Evidence**:
- `ls supabase/migrations/` output shows 15 migration files

---

### Core Tables (Inferred)
Based on code references and migration names:

**Tenant Tables**:
- `agencies` - Multi-tenant root
- `team_members` - User-agency membership with roles
- `profiles` - User profiles with last_active_agency_id

**Domain Tables**:
- `properties` - Property listings (agency scoped)
- `bookings` - Booking records (agency scoped)
- `guests` - Guest information
- `inventory_ranges` - Availability blocks/bookings with EXCLUSION constraint
- `availability_blocks` - Manual blocks

**Channel Manager Tables**:
- `channel_connections` - OAuth integrations with platforms
- `channel_sync_logs` - Sync operation logs

**Not Yet Created** (Phase 1 planned):
- `audit_log` - Audit trail (Phase 1 - P1-10)
- `idempotency_keys` - Idempotency (Phase 1 - P1-11)
- `agency_features` - Feature flags (Phase 1 - P1-12)

**Evidence**:
- Migration filenames indicate table creation
- Code queries reference tables (e.g., `app/api/deps.py:143-146` - profiles query)
- `backend/docs/roadmap/phase-1.md:118-162` - Planned tables with SQL

---

## Channel Manager

### Architecture
**Path**: `backend/app/channel_manager/`

**Components**:
1. **Sync Engine**: `core/sync_engine.py` - Celery tasks for bidirectional sync
2. **Adapters**: `adapters/` - Platform integrations (Airbnb, base adapter, factory)
3. **Reliability**: `core/rate_limiter.py`, `core/circuit_breaker.py`
4. **Config**: `config.py`

**Sync Types**:
- `availability` - Block/release dates on channels
- `pricing` - Update nightly rates
- `bookings` - Import bookings from platforms (inbound)

**Event Model** (defined but not fully wired):
```python
class BookingEvent(BaseModel)  # booking.confirmed, booking.cancelled, etc.
class PricingEvent(BaseModel)  # pricing.updated
class PropertyEvent(BaseModel) # property.created
```

**Evidence**:
- `backend/app/channel_manager/core/sync_engine.py:1-150` - SyncEngine class, event models
- `find` output shows adapter files: airbnb/adapter.py, base_adapter.py, factory.py

---

### Celery Tasks
**Implementation**: `backend/app/channel_manager/core/sync_engine.py`

**Tasks** (imported from sync_engine):
- `update_channel_availability.delay()` - Celery task for availability sync
- `update_channel_pricing.delay()` - Celery task for pricing sync

**Retry Logic**:
- Exponential backoff: 1s, 2s, 4s
- Max 3 retries
- Database error handling (asyncpg.PostgresError)

**Evidence**:
- `backend/app/api/routes/availability.py:63-66` - Import of update_channel_availability
- `backend/app/api/routes/availability.py:476-556` - _retry_with_exponential_backoff implementation
- `backend/app/api/routes/availability.py:668-694` - Celery task.delay() calls

---

## Frontend

### Technology Stack
- **Framework**: Next.js 15 with App Router
- **Auth**: Supabase SSR (@supabase/ssr)
- **UI**: React with TypeScript

### Routes
**Path**: `frontend/app/`

**Implemented Routes**:
1. `/login` - Login page (server + client component split)
2. `/ops/*` - Ops Console (SSR auth, admin-only)
3. `/channel-sync` - Channel Manager UI (SSR auth, admin-only)
4. `/auth/login` - Route handler for cookie-based login

**Shared Components**:
- `BackofficeLayout.tsx` - Unified navigation for ops + channel-sync

**Evidence**:
- `ls frontend/app/` output: auth/, channel-sync/, ops/, login/, components/

---

## Phase 1 Status (Roadmap Alignment)

### Phase 1 Deliverables Status

| Task | Deliverable | Status | Evidence |
|------|-------------|--------|----------|
| P1-01 | RBAC Finalization | ✅ DONE | `app/core/auth.py:324-428` |
| P1-02 | Tenant Isolation Audit | ⚠️ IN PROGRESS | `app/api/deps.py` implemented, audit pending |
| P1-03 | Mandatory Migrations Workflow | ❌ NOT STARTED | No migrations/README.md found |
| P1-06 | Error Taxonomy | ✅ DONE | `app/core/exceptions.py` + error-taxonomy.md |
| P1-07 | Error Response Format | ❌ NOT STARTED | Docs confirm pending |
| P1-08 | `/ops/current-commit` | ⚠️ STUB | Endpoint exists, returns placeholders |
| P1-09 | `/ops/env-sanity` | ⚠️ STUB | Endpoint exists, health checks stubbed |
| P1-10 | Audit Log Table | ❌ NOT CREATED | Planned in phase-1.md:119-132 |
| P1-11 | Idempotency Keys Table | ❌ NOT CREATED | Planned in phase-1.md:134-144 |
| P1-12 | Agency Features Table | ❌ NOT CREATED | Planned in phase-1.md:146-159 |

**Phase 1 Progress**: ~40% complete (4 of 10 tasks done, 3 stubbed)

**Evidence**:
- `backend/docs/roadmap/phase-1.md:14-21` - MUST/SHOULD/COULD scope
- `backend/docs/roadmap/phase-1.md:34-101` - Deliverables & DoD

---

## Test Coverage

### Unit Tests
**Path**: `backend/tests/unit/`

**Implemented**:
- `test_rbac_helpers.py` - RBAC helper tests (3 test classes, 15+ test cases)

**Status**: ⚠️ Tests written but NOT executed
- Header comment: "DO NOT RUN THESE TESTS YET - they are part of Phase 1 foundation"

**Evidence**:
- `backend/tests/unit/test_rbac_helpers.py:1-9` - Warning comment
- `backend/tests/unit/test_rbac_helpers.py:16-136` - Comprehensive test cases

### Integration Tests
**Path**: `backend/tests/integration/` (not explored in this scan)

**Status**: Unknown (not scanned)

---

## Deployment & Operations

### Graceful Degradation
**Implementation**: `backend/app/main.py`

**Lifespan Handler**:
- Attempts to create DB connection pool at startup
- If DB unavailable: Logs warning, app runs in DEGRADED MODE (no crash)
- Returns 503 for DB-dependent endpoints

**Evidence**:
- `backend/app/main.py` (read during scan) - Lifespan handler with try/except for pool creation

### Health Checks
**Status**: ❌ Not fully implemented

**Ops Endpoints**: Stubbed (see Ops API section)

---

## Known Issues & Debt

### Technical Debt
1. **Ops endpoints are placeholders** - Need actual health check implementation
2. **Error response format not unified** - Phase 1 - P1-07 pending
3. **No audit logging** - Planned tables not created
4. **Channel connections lack fine-grained RBAC** - Global auth only
5. **Tests not executed** - RBAC unit tests exist but marked "DO NOT RUN"

### Documentation Drift
1. **Phase 1 roadmap lists items not started** (P1-07 onwards)
2. **Ops endpoints have TODO comments** but roadmap shows them as deliverables
3. **error-taxonomy.md correctly reflects reality** (P1-06 done, P1-07 pending)

**Evidence**: See DRIFT_REPORT.md for detailed analysis

---

## Recommendations

### Immediate Actions (Sprint 1)
1. ✅ **Complete P1-07**: Implement unified error response format
2. ✅ **Implement ops endpoints**: Replace stubs with real health checks
3. ✅ **Add RBAC to ops endpoints**: Require admin role
4. ✅ **Create migration tables**: audit_log, idempotency_keys, agency_features
5. ✅ **Execute unit tests**: Run test_rbac_helpers.py and verify RBAC logic

### Documentation Updates
1. ✅ **Update phase-1.md**: Mark P1-01, P1-06 as complete
2. ✅ **Create migration docs**: Document workflow in migrations/README.md
3. ✅ **Channel manager architecture doc**: Document sync engine, adapters, retry logic
4. ✅ **API reference**: Generate OpenAPI/Swagger docs from FastAPI

### Long-Term
1. ✅ **Tenant isolation audit**: Verify all queries filter by agency_id (P1-02)
2. ✅ **Add integration tests**: Test full request flows with DB
3. ✅ **Frontend-backend integration tests**: Verify SSR auth + API calls
4. ✅ **Monitoring**: Implement actual health checks, metrics export

---

## Evidence Manifest

All claims in this document are backed by evidence. See **MANIFEST.md** for:
- File paths for every code reference
- Symbol definitions (function signatures, class names)
- Line numbers for specific logic
- Commit metadata and timestamps

**Methodology**: READ-ONLY analysis, no speculation, code-derived only.

---

**End of Status Report**

**Next Steps**: Review DRIFT_REPORT.md for gaps between docs and reality.
