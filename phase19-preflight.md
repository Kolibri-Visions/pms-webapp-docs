# Phase 19 Preflight Gates

**Phase:** 19 - Core Booking Flow API
**Status:** IMPLEMENTATION COMPLETE (awaiting testing)
**Date:** 2025-12-23
**Implementation Completed:** 2025-12-23

---

## 1. Scope

**Deliverables:**
1. Properties CRUD API (GET, POST, PATCH, DELETE /properties)
2. Bookings CRUD API (GET, POST, PATCH /bookings)
3. RBAC Middleware (get_current_user, get_current_agency, Role Guards)
4. Pydantic Validation Schemas (20+ models)
5. Error Handling (4xx/5xx with details)
6. Integration Tests (30+ tests, >80% coverage)
7. OpenAPI Documentation (/docs, /openapi.json)
8. Database Connection Pool (asyncpg)
9. Environment Configuration (.env.example, settings.py)
10. Phase 19 Documentation & Preflight

**Dependencies:**
- Phase 17B (Schema FROZEN v1.0)
- Phase 18A (Migrations FROZEN v1.0)
- FastAPI
- asyncpg
- pydantic
- pytest
- Supabase local (PostgreSQL 17)

---

## 2. Local Checks

### 2.1 Linting & Code Quality

**Commands:**
```bash
cd backend

# Ruff linting
ruff check app/

# Ruff formatting check
ruff format --check app/

# Optional: mypy type checking
mypy app/ --ignore-missing-imports
```

**Expected Output:**
```
✅ No linting errors
✅ All files formatted correctly
✅ Type checks pass (if mypy installed)
```

**Gate:** ⬜ NOT RUN YET

### 2.2 Unit Tests

**Commands:**
```bash
cd backend
pytest tests/unit/ -v --cov=app --cov-report=term-missing
```

**Expected Output:**
```
✅ All unit tests pass
✅ Coverage > 80%
```

**Gate:** ⬜ NOT RUN YET

---

## 3. Database & Migrations

### 3.1 Supabase Local Start

**Commands:**
```bash
supabase start
```

**Expected Output:**
```
Started supabase local development setup.

         API URL: http://127.0.0.1:54321
          DB URL: postgresql://postgres:postgres@127.0.0.1:54322/postgres
      Studio URL: http://127.0.0.1:54323
```

**Gate:** ⬜ NOT RUN YET

### 3.2 Migrations Apply

**Commands:**
```bash
supabase db reset
```

**Expected Output:**
```
Resetting local database...
Applying migration 20250101000001_initial_schema.sql...
Applying migration 20250101000002_channels_and_financials.sql...
Applying migration 20250101000003_indexes.sql...
Applying migration 20250101000004_rls_policies.sql...
Seeding data supabase/seed.sql...
Finished supabase db reset on branch main.
```

**Gate:** ⬜ NOT RUN YET

### 3.3 Database Smoke Checks

**Commands:**
```bash
# Check Phase 18A migrations still intact (no changes)
ls -1 supabase/migrations/

# Check seed data loaded
supabase db psql -c "SELECT COUNT(*) FROM agencies;"
supabase db psql -c "SELECT COUNT(*) FROM properties;"
supabase db psql -c "SELECT COUNT(*) FROM bookings;"

# Verify RLS policies exist
supabase db psql -c "SELECT tablename, COUNT(*) FROM pg_policies WHERE tablename IN ('properties', 'bookings') GROUP BY tablename;"
```

**Expected Output:**
```
# Migrations (FROZEN 18A, unchanged):
20250101000001_initial_schema.sql
20250101000002_channels_and_financials.sql
20250101000003_indexes.sql
20250101000004_rls_policies.sql

# Seed data counts:
agencies:    2
properties:  3
bookings:    4

# RLS policies:
properties  | 10
bookings    | 15
```

**Gate:** ⬜ NOT RUN YET

---

## 4. Backend API Smoke Checks

**Important:** Backend runs on port **8000**, NOT 54321 (Supabase API)

### 4.1 Start Backend

**Commands:**
```bash
cd backend
export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
export JWT_SECRET="super-secret-jwt-token-with-at-least-32-characters-long"
uvicorn app.main:app --reload --port 8000
```

**Expected Output:**
```
INFO:     Will watch for changes in these directories: ['/path/to/backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using StatReload
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Gate:** ⬜ NOT RUN YET

### 4.2 Health Endpoints

**Commands:**
```bash
# Liveness (should still work)
curl -s http://localhost:8000/health | python3 -m json.tool

# Readiness (should still work)
curl -s http://localhost:8000/health/ready | python3 -m json.tool
```

**Expected Output:**

**Liveness:**
```json
{
  "status": "up",
  "checked_at": "2025-12-23T..."
}
```

**Readiness:**
```json
{
  "status": "up",
  "components": {
    "db": {"status": "up"},
    "redis": {"status": "up", "details": {"skipped": true}},
    "celery": {"status": "up", "details": {"skipped": true}}
  }
}
```

**Gate:** ⬜ NOT RUN YET

### 4.3 OpenAPI Schema

**Commands:**
```bash
# OpenAPI JSON
curl -s http://localhost:8000/openapi.json | head -n 50

# Check new endpoints exist
curl -s http://localhost:8000/openapi.json | grep -E "(properties|bookings)" | head -n 20
```

**Expected Output:**
```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "PMS Backend API",
    "version": "0.1.0"
  },
  "paths": {
    "/health": {...},
    "/health/ready": {...},
    "/api/v1/properties": {
      "get": {"summary": "List all properties", ...},
      "post": {"summary": "Create property", ...}
    },
    "/api/v1/properties/{property_id}": {
      "get": {...},
      "patch": {...},
      "delete": {...}
    },
    "/api/v1/bookings": {
      "get": {"summary": "List all bookings", ...},
      "post": {"summary": "Create booking", ...}
    },
    "/api/v1/bookings/{booking_id}": {...},
    "/api/v1/bookings/{booking_id}/status": {...},
    "/api/v1/bookings/{booking_id}/cancel": {...}
  }
}
```

**Gate:** ⬜ NOT RUN YET

### 4.4 Properties API Smoke

**Commands:**
```bash
# List properties (requires auth token)
export ADMIN_TOKEN="Bearer eyJhbGciOiJIUzI1NiIs..."  # From test fixture
curl -s http://localhost:8000/api/v1/properties \
  -H "Authorization: $ADMIN_TOKEN" | python3 -m json.tool

# Get property by ID
curl -s http://localhost:8000/api/v1/properties/<property_id> \
  -H "Authorization: $ADMIN_TOKEN" | python3 -m json.tool
```

**Expected Output:**
```json
{
  "items": [
    {
      "id": "p1111111-1111-1111-1111-111111111111",
      "name": "Alpenchalet Zugspitze",
      "agency_id": "11111111-1111-1111-1111-111111111111",
      "owner_id": "a0000000-0000-0000-0000-000000000004",
      "property_type": "chalet",
      "bedrooms": 3,
      "base_price": 150.00,
      "currency": "EUR",
      "is_active": true
    },
    {
      "id": "p1111111-1111-1111-1111-111111111112",
      "name": "Moderne Stadtwohnung München Zentrum",
      ...
    }
  ],
  "total": 2,
  "limit": 50,
  "offset": 0
}
```

**Gate:** ⬜ NOT RUN YET

### 4.5 Bookings API Smoke

**Commands:**
```bash
# List bookings
curl -s http://localhost:8000/api/v1/bookings \
  -H "Authorization: $ADMIN_TOKEN" | python3 -m json.tool

# Get booking by ID
curl -s http://localhost:8000/api/v1/bookings/<booking_id> \
  -H "Authorization: $ADMIN_TOKEN" | python3 -m json.tool
```

**Expected Output:**
```json
{
  "items": [
    {
      "id": "b0000001-0000-0000-0000-000000000001",
      "booking_reference": "PMS-2025-000001",
      "property_id": "p1111111-1111-1111-1111-111111111111",
      "check_in": "2025-02-14",
      "check_out": "2025-02-21",
      "status": "confirmed",
      "num_guests": 4,
      "total_price": 1130.00,
      "currency": "EUR"
    },
    ...
  ],
  "total": 4,
  "limit": 50,
  "offset": 0
}
```

**Gate:** ⬜ NOT RUN YET

---

## 5. Integration Tests

### 5.1 Run All Integration Tests

**Commands:**
```bash
cd backend
pytest tests/integration/ -v --cov=app --cov-report=term-missing
```

**Expected Output:**
```
tests/integration/test_properties.py::test_list_properties_as_admin PASSED
tests/integration/test_properties.py::test_list_properties_as_owner PASSED
tests/integration/test_properties.py::test_create_property_as_admin PASSED
tests/integration/test_properties.py::test_create_property_as_staff PASSED (403)
tests/integration/test_properties.py::test_update_property_as_manager PASSED
tests/integration/test_properties.py::test_delete_property_as_admin PASSED
tests/integration/test_properties.py::test_delete_property_as_manager PASSED (403)
tests/integration/test_properties.py::test_get_property_not_found PASSED (404)

tests/integration/test_bookings.py::test_list_bookings_as_admin PASSED
tests/integration/test_bookings.py::test_list_bookings_as_owner PASSED
tests/integration/test_bookings.py::test_create_booking_as_staff PASSED
tests/integration/test_bookings.py::test_create_booking_double_booking PASSED (409)
tests/integration/test_bookings.py::test_update_status_pending_to_confirmed PASSED
tests/integration/test_bookings.py::test_update_status_invalid_transition PASSED (400)
tests/integration/test_bookings.py::test_cancel_booking_as_admin PASSED
tests/integration/test_bookings.py::test_cancel_booking_as_staff PASSED (403)

tests/integration/test_rbac.py::test_admin_full_access PASSED
tests/integration/test_rbac.py::test_manager_cannot_delete_properties PASSED
tests/integration/test_rbac.py::test_staff_read_only_properties PASSED
tests/integration/test_rbac.py::test_owner_isolation PASSED
tests/integration/test_rbac.py::test_accountant_no_properties_access PASSED

tests/integration/test_multi_tenancy.py::test_agency_isolation PASSED
tests/integration/test_multi_tenancy.py::test_cross_agency_property_access_forbidden PASSED
tests/integration/test_multi_tenancy.py::test_cross_agency_booking_access_forbidden PASSED

======================== 30 passed in 5.43s ========================
Coverage: 85%
```

**Gate:** ⬜ NOT RUN YET

### 5.2 RBAC Integration Tests

**Commands:**
```bash
cd backend
pytest tests/integration/test_rbac.py -v
```

**Expected Output:**
```
test_admin_full_access PASSED
test_manager_cannot_delete_properties PASSED
test_staff_read_only_properties PASSED
test_owner_isolation PASSED (owner sees only own properties)
test_accountant_no_properties_access PASSED (403)

All RBAC tests passed ✅
```

**Gate:** ⬜ NOT RUN YET

### 5.3 Multi-Tenancy Isolation Tests

**Commands:**
```bash
cd backend
pytest tests/integration/test_multi_tenancy.py -v
```

**Expected Output:**
```
test_agency_isolation PASSED (Agency 1 cannot see Agency 2 data)
test_cross_agency_property_access_forbidden PASSED (403)
test_cross_agency_booking_access_forbidden PASSED (403)

All Multi-Tenancy tests passed ✅
```

**Gate:** ⬜ NOT RUN YET

---

## 6. CI/CD Checks (Future)

### 6.1 GitHub Actions

**Status:** ⬜ NOT IMPLEMENTED YET

**Future Check:**
- Open GitHub repository
- Navigate to Actions tab
- Verify latest workflow run is GREEN

### 6.2 Pre-commit Hooks (Optional)

**Commands:**
```bash
pre-commit run --all-files
```

**Expected Output:**
```
✅ All hooks pass
```

**Gate:** ⬜ OPTIONAL

---

## 7. Deploy Smoke (Future)

### 7.1 Container Build

**Commands:**
```bash
docker build -t pms-backend:phase19 -f backend/Dockerfile backend/
```

**Expected Output:**
```
✅ Build succeeds without errors
✅ Image size < 500MB
```

**Gate:** ⬜ NOT IMPLEMENTED YET

---

## 8. Gate Checklist

**Phase 19 Deliverables:**
- [x] Backend API structure created (`api/`, `schemas/`, `services/`)
- [x] Auth dependencies implemented (`get_current_user`, `get_current_agency_id`, `get_current_role`)
- [x] RBAC guards implemented (`require_roles`)
- [x] Properties API (5 endpoints: GET list, GET single, POST, PATCH, DELETE)
- [x] Bookings API (5 endpoints: GET list, GET single, POST, PATCH status, POST cancel)
- [x] Pydantic schemas (20+ models for request/response: common, properties, bookings, guests)
- [x] Error handling (custom exceptions + HTTP status codes)
- [x] Integration tests (106 tests across 4 modules, targeting >80% coverage)
  - [x] test_properties.py (23 tests)
  - [x] test_bookings.py (25 tests)
  - [x] test_rbac.py (36 tests)
  - [x] test_multi_tenancy.py (22 tests)
- [x] OpenAPI documentation (descriptions, examples, tags in all endpoints)
- [x] Environment configuration (.env.example, settings.py already in Phase 18A)
- [x] Database connection pool (asyncpg, implemented in core/database.py)
- [x] Phase 19 documentation (phase19-core-booking-flow-api.md)
- [x] Phase 19 preflight (this file)

**Quality Gates:**
- [ ] Local linting passes (ruff)
- [ ] Unit tests pass
- [ ] Migrations apply cleanly (FROZEN 18A, no changes)
- [ ] Database smoke checks pass (seed data intact)
- [ ] Backend starts without errors (port 8000)
- [ ] Health endpoints still work
- [ ] OpenAPI schema accessible with new endpoints
- [ ] Properties API smoke tests pass
- [ ] Bookings API smoke tests pass
- [ ] Integration tests pass (30+ tests)
  - [ ] RBAC tests pass
  - [ ] Multi-tenancy isolation tests pass
  - [ ] Booking status workflow tests pass
  - [ ] Validation tests pass
- [ ] Test coverage > 80%
- [ ] No schema changes to FROZEN tables
- [ ] Documentation complete

**Gate Status:** 🟡 **IMPLEMENTATION COMPLETE** (Quality Gates testing pending)

**Implementation Notes:**
- ✅ All 13 deliverables completed
- ✅ 106 integration tests written (exceeds 30+ requirement)
- ✅ Full RBAC implementation (5 roles)
- ✅ Multi-tenancy isolation enforced
- ✅ Status workflow state machine implemented
- ⏳ Quality Gates (linting, test execution, smoke tests) awaiting user execution

**Signed Off By:** Claude Code Agent | 2025-12-23

---

## 9. Notes

### 9.1 Deferred Components

**Still Deferred (from Phase 18A):**
- ✅ Redis: Skipped in health checks
- ✅ Celery: Skipped in health checks

**Deferred to Later Phases:**
- ❌ Channel Manager (Phase 20)
- ❌ Payment Processing (Phase 21)
- ❌ File Upload (Phase 22)
- ❌ Email Notifications (Phase 23)

### 9.2 FROZEN Schema Compliance

**CRITICAL:** Phase 19 must NOT change:
- ✅ Migrations in `supabase/migrations/202501010000*`
- ✅ RLS Policies in `20250101000004_rls_policies.sql`
- ✅ Seed Data structure in `supabase/seed.sql`

**Allowed:**
- ✅ Backend code (FastAPI routes, schemas, services)
- ✅ Integration tests
- ✅ Documentation

**Verification:**
```bash
# Check migrations unchanged
git diff --name-status supabase/migrations/

# Should return empty (no changes)
```

---

## 10. Rollback Plan

**If Phase 19 needs rollback:**

1. **Identify last good commit:**
   ```bash
   git log --oneline | grep "9f379f8"  # Last commit before Phase 19
   ```

2. **Revert Phase 19 commits:**
   ```bash
   git revert <first_phase19_commit>..HEAD --no-commit
   git commit -m "revert: rollback Phase 19"
   ```

3. **Verify backend still works:**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   curl http://localhost:8000/health/ready
   ```

4. **Verify database unchanged:**
   ```bash
   supabase db reset
   supabase db psql -c "SELECT COUNT(*) FROM agencies;"  # Should be 2
   ```

**Recovery Time:** < 5 minutes (nur Backend Code, kein Schema Change)

---

## 11. Next Steps

**After Phase 19 PASSED:**

1. Mark Phase 19 as FROZEN v1.0
2. Update CURRENT_STATE.md
3. Push all commits to origin/main
4. Plan Phase 20 (Channel Manager Integration)

**Phase 20 Proposal:** Channel Manager Integration
- Channel Connections API
- iCal Feed Import/Export
- External Bookings Sync
- Availability Calendar API
- Integration Tests

**Do NOT start Phase 20 without:**
- Phase 19 FROZEN v1.0
- User approval
- New phase planning document
- Preflight template filled out

---

**Ende Phase 19 Preflight**
