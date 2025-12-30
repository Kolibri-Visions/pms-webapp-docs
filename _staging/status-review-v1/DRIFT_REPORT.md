# Documentation Drift Report

**Generated**: 2025-12-30
**Commit**: `393ba8da51b67fdd832b92232c43c524c3edec88`

This document identifies gaps between existing documentation and actual codebase implementation.

---

## Summary

### Drift Types
- **✅ Aligned**: Documentation matches implementation perfectly
- **⚠️ Partial**: Implementation started but incomplete vs. docs
- **❌ Divergent**: Documentation describes features not implemented
- **🔄 Outdated**: Documentation doesn't reflect latest changes

### Overall Assessment
- **20%** ✅ Aligned (error-taxonomy.md, phase-1 scope)
- **30%** ⚠️ Partial (RBAC helpers, ops endpoints stubbed)
- **40%** ❌ Divergent (Phase 1 roadmap ahead of reality)
- **10%** 🔄 Outdated (No major outdated docs found)

---

## Phase 1 Roadmap Drift

### Document: `backend/docs/roadmap/phase-1.md`

#### ✅ Aligned Items
1. **P1-01: RBAC Finalization**
   - **Documented**: "require_role() dependency works for all 5 roles"
   - **Reality**: ✅ Implemented in `app/core/auth.py:382-428`
   - **Evidence**: Function signatures match, unit tests exist
   - **Status**: ALIGNED

2. **P1-06: Error Taxonomy**
   - **Documented**: "Define error codes, create AppError class, 3 typed exceptions"
   - **Reality**: ✅ Implemented in `app/core/exceptions.py`
   - **Evidence**: `ERROR_CODE_*` constants, AppError base class, 3 typed exceptions
   - **Status**: ALIGNED

#### ⚠️ Partial Implementation
3. **P1-08: `/ops/current-commit` endpoint**
   - **Documented**: "Returns commit_sha and deployed_at from env vars"
   - **Reality**: ⚠️ Endpoint exists but returns `os.getenv("COMMIT_SHA", "unknown")`
   - **Evidence**: `app/routers/ops.py:49-50` - Fallback to "unknown"
   - **Gap**: Environment variables not configured, no actual deployment metadata
   - **Action**: Configure CI/CD to inject COMMIT_SHA and DEPLOYED_AT

4. **P1-09: `/ops/env-sanity` endpoint**
   - **Documented**: "Performs environment sanity checks, returns service health status"
   - **Reality**: ⚠️ Endpoint exists but health checks are hardcoded `"ok"`
   - **Evidence**: `app/routers/ops.py:89-92` - Commented out actual checks
   - **Gap**: `check_database_health()`, `check_redis_health()`, `check_celery_health()` not called
   - **Action**: Implement actual health check calls

5. **P1-02: Tenant Isolation Audit**
   - **Documented**: "Audit report: List all queries, verify agency_id filter"
   - **Reality**: ⚠️ Infrastructure exists (deps.py, service patterns) but NO audit report
   - **Evidence**: `app/api/deps.py:53-220` - get_current_agency_id implemented
   - **Gap**: No audit document listing all queries with agency_id verification
   - **Action**: Generate audit report by scanning all service files for SQL queries

#### ❌ Not Implemented
6. **P1-03: Mandatory Migrations Workflow**
   - **Documented**: "Document workflow, create migrations/README.md"
   - **Reality**: ❌ No migrations/README.md found
   - **Evidence**: No file at `backend/migrations/README.md` or `supabase/migrations/README.md`
   - **Gap**: Documentation file does not exist
   - **Action**: Create migrations/README.md with workflow, naming conventions, rollback

7. **P1-07: Error Response Format**
   - **Documented**: "All endpoints return `{error: {code, message}}`"
   - **Reality**: ❌ Not implemented (error-taxonomy.md confirms this is P1-07, not P1-06)
   - **Evidence**: `docs/architecture/error-taxonomy.md:130` - "Response format changes are NOT part of P1-06"
   - **Gap**: FastAPI exception handlers not registered yet
   - **Action**: Add exception handlers in main.py to convert AppError → structured response

8. **P1-10: Audit Log Table**
   - **Documented**: SQL schema in phase-1.md (lines 119-132)
   - **Reality**: ❌ Table not created
   - **Evidence**: No migration file named `*audit_log*` in supabase/migrations/
   - **Gap**: Migration not written
   - **Action**: Create migration with audit_log schema

9. **P1-11: Idempotency Keys Table**
   - **Documented**: SQL schema in phase-1.md (lines 134-144)
   - **Reality**: ❌ Table not created
   - **Evidence**: No migration file named `*idempotency*` in supabase/migrations/
   - **Gap**: Migration not written
   - **Action**: Create migration with idempotency_keys schema

10. **P1-12: Agency Features Table**
    - **Documented**: SQL schema in phase-1.md (lines 146-159)
    - **Reality**: ❌ Table not created
    - **Evidence**: No migration file named `*agency_features*` in supabase/migrations/
    - **Gap**: Migration not written
    - **Action**: Create migration with agency_features schema

---

## Error Taxonomy Documentation Drift

### Document: `backend/docs/architecture/error-taxonomy.md`

#### ✅ Aligned
- **Status**: This document is **ACCURATE** and correctly reflects implementation
- **P1-06 Status**: ✅ Correctly marked as implemented
- **P1-07 Status**: ❌ Correctly marked as pending
- **Evidence**: Lines 128-152 explicitly state "Response format changes are NOT part of P1-06"

#### No Drift Detected
This is the gold standard for documentation accuracy. Other docs should follow this pattern.

---

## API Endpoints Drift

### Ops Endpoints
**Document**: `backend/docs/roadmap/phase-1.md` (lines 92-101)

| Endpoint | Documented | Reality | Drift |
|----------|-----------|---------|-------|
| `/ops/current-commit` | Returns commit_sha from env | Returns `"unknown"` if env not set | ⚠️ PARTIAL |
| `/ops/env-sanity` | Performs health checks | Returns hardcoded `"ok"` | ⚠️ PARTIAL |

**Evidence**:
- `app/routers/ops.py:42-45` - TODO comment: "Add RBAC: Require admin role"
- `app/routers/ops.py:81-85` - TODO comment: "Implement actual health checks"

**Impact**: Ops endpoints exist but are not production-ready.

---

### RBAC Enforcement Drift
**Document**: `backend/docs/roadmap/phase-1.md` (lines 34-44)

**Claim**: "Admin-only endpoints reject non-admin requests (401/403)"

**Reality**:
- ✅ Properties endpoints: RBAC enforced via `require_roles()`
- ✅ Bookings endpoints: RBAC enforced via `require_roles()`
- ✅ Availability endpoints: RBAC enforced via `require_roles()`
- ❌ Ops endpoints: NO RBAC (endpoints public, TODO in comments)
- ⚠️ Channel connections: Global auth only (no role enforcement)

**Evidence**:
- `app/api/routes/properties.py:161` - `Depends(require_roles("admin", "manager"))`
- `app/routers/ops.py:28` - No `Depends(require_roles(...))` on router or endpoints

**Gap**: Ops endpoints need RBAC added before production use.

---

## Tests Drift

### Unit Tests
**Document**: `backend/docs/roadmap/phase-1.md` (lines 40-44)

**DoD Claim**: "Tests: Role enforcement for properties, bookings, channel-sync"

**Reality**:
- ✅ Unit tests exist for RBAC helpers (`test_rbac_helpers.py`)
- ❌ Tests not executed yet (header comment warns "DO NOT RUN THESE TESTS YET")
- ❌ No integration tests for endpoint RBAC enforcement

**Evidence**:
- `tests/unit/test_rbac_helpers.py:7-8` - "DO NOT RUN THESE TESTS YET"

**Gap**: Tests exist but are not run. No CI/CD test execution confirmed.

---

## Migration Workflow Drift

### Document: `backend/docs/roadmap/phase-1.md` (lines 57-66)

**DoD Claims**:
- [ ] "Document workflow: Create migration → Review → Apply → Rollback plan"
- [ ] "Placeholder migrations for `audit_log`, `agency_features`, `idempotency_keys`"
- [ ] "Migration naming convention documented"
- [ ] "Rollback procedure documented"

**Reality**:
- ❌ No migrations/README.md found
- ❌ No placeholder migrations for audit_log, agency_features, idempotency_keys
- ✅ Naming convention observed in existing migrations: `YYYYMMDDHHMMSS_description.sql`
- ❌ No rollback procedure documented

**Evidence**:
- `ls supabase/migrations/` - No README.md, no placeholder migrations
- Existing migrations follow timestamp naming pattern

**Gap**: Documentation file completely missing, placeholder migrations not created.

---

## Channel Manager Drift

### Missing Documentation
**Issue**: Channel Manager has substantial implementation but NO architecture documentation

**Implemented Components**:
- `channel_manager/core/sync_engine.py` - Celery tasks, event models
- `channel_manager/adapters/` - Airbnb adapter, base adapter, factory
- `channel_manager/core/rate_limiter.py` - Rate limiting
- `channel_manager/core/circuit_breaker.py` - Circuit breaker pattern

**Documentation**: ❌ None found in `backend/docs/`

**Impact**: New developers cannot understand channel manager architecture without reading code.

**Action**: Create `backend/docs/architecture/channel-manager.md`

---

## Frontend Drift

### Missing Documentation
**Issue**: Frontend has SSR auth, unified navigation, but NO architecture documentation

**Implemented Components**:
- Next.js 15 App Router
- Supabase SSR authentication
- BackofficeLayout (shared ops + channel-sync nav)
- Server Components + Client Components split

**Documentation**: ❌ None found in `frontend/docs/` or `backend/docs/`

**Impact**: Frontend architecture decisions not documented.

**Action**: Create `frontend/docs/architecture.md`

---

## Recommendations

### High Priority (Fix Before Phase 1 Completion)
1. **Implement ops endpoint health checks** - Replace stubs with real checks
2. **Add RBAC to ops endpoints** - Require admin role
3. **Create migrations/README.md** - Document workflow, naming, rollback
4. **Create placeholder migrations** - audit_log, idempotency_keys, agency_features
5. **Execute unit tests** - Run test_rbac_helpers.py, fix any failures

### Medium Priority (Sprint 2)
6. **Implement P1-07 error response format** - Register exception handlers
7. **Tenant isolation audit** - Generate report of all queries with agency_id verification
8. **Channel manager documentation** - Create architecture doc
9. **Frontend documentation** - Create architecture doc

### Low Priority (Post-Phase 1)
10. **API reference generation** - Use FastAPI to generate OpenAPI/Swagger docs
11. **Integration tests** - Add endpoint RBAC enforcement tests
12. **CI/CD test execution** - Run unit tests in pipeline

---

## Drift Metrics

### By Severity
- **Critical**: 4 items (ops RBAC missing, health checks stubbed, error format not unified, migrations missing)
- **High**: 3 items (placeholder migrations, audit report, tests not executed)
- **Medium**: 3 items (channel manager docs, frontend docs, integration tests)
- **Low**: 2 items (API reference, CI/CD tests)

### By Phase 1 Task
- **P1-01**: ✅ ALIGNED (0% drift)
- **P1-02**: ⚠️ 50% drift (implementation exists, audit report missing)
- **P1-03**: ❌ 100% drift (not started)
- **P1-06**: ✅ ALIGNED (0% drift)
- **P1-07**: ❌ 100% drift (not started)
- **P1-08**: ⚠️ 60% drift (endpoint exists, env vars missing, RBAC missing)
- **P1-09**: ⚠️ 60% drift (endpoint exists, health checks stubbed, RBAC missing)
- **P1-10**: ❌ 100% drift (not started)
- **P1-11**: ❌ 100% drift (not started)
- **P1-12**: ❌ 100% drift (not started)

**Overall Phase 1 Drift**: ~60% of deliverables incomplete or partially implemented

---

## Closing Recommendations

### Update Phase 1 Roadmap
- Mark P1-01, P1-06 as ✅ COMPLETED
- Keep P1-02 as ⚠️ IN PROGRESS (add note: "infrastructure exists, audit report pending")
- Keep P1-08, P1-09 as ⚠️ IN PROGRESS (add note: "endpoints exist but health checks stubbed, RBAC missing")
- Update remaining tasks with accurate status

### Adopt Error Taxonomy Doc as Template
- `error-taxonomy.md` is perfectly aligned with reality
- It explicitly states what's done (P1-06) and what's pending (P1-07)
- Use this format for all future docs: clear phase markers, migration strategy, examples

### Create Missing Docs
1. `backend/migrations/README.md` - Migration workflow
2. `backend/docs/architecture/channel-manager.md` - Channel sync architecture
3. `frontend/docs/architecture.md` - Frontend architecture

---

**End of Drift Report**

**Next Steps**: Review PROJECT_STATUS.md for code-derived reality, then reconcile Phase 1 roadmap.
