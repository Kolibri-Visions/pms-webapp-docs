# Phase 1: Foundation & Ops Tooling

**Sprint**: 1 of 5
**Duration**: 2 weeks
**Status**: Not Started
**Owner**: Backend Team

## Goal

Lock down security (RBAC, tenant isolation), establish error handling standards, mandatory migrations workflow, and ops observability endpoints. This phase creates the foundation for all subsequent work.

## Scope

### MUST (Sprint Goal)
- ✓ **RBAC Finalization**: Enforce admin/manager/staff/owner/accountant roles across all endpoints
- ✓ **Tenant Isolation Audit**: Verify all queries filter by agency_id (no RLS bypass)
- ✓ **Mandatory Migrations Workflow**: Document + enforce migration process
- ✓ **Error Taxonomy**: Standardize exceptions (4xx/5xx, error codes, structured responses)
- ✓ **503 Degraded Mode**: Return 503 when critical services unavailable (DB, Redis)
- ✓ **Ops Runbook Endpoints**: `/ops/current-commit`, `/ops/env-sanity`

### SHOULD (Nice to Have)
- Audit log table + helper (log critical actions: booking create/cancel, role changes)
- Idempotency keys table (prepare for Phase 2 booking idempotency)
- Feature flags helper (prepare for agency entitlements)

### COULD (Stretch)
- Automated RLS policy tests
- Error response schema validation tests
- Ops alerting integration (Sentry, PagerDuty)

## Deliverables & Definition of Done

### 1. RBAC Finalization
**Files Touched**:
- `app/core/auth.py` (role helpers)
- `app/routers/properties.py`, `bookings.py`, etc. (role checks)
- `app/dependencies.py` (role dependencies)

**DoD**:
- [ ] `require_role()` dependency works for all 5 roles
- [ ] Admin-only endpoints reject non-admin requests (401/403)
- [ ] Owner-only endpoints enforce `user_id = owner_id` check
- [ ] Tests: Role enforcement for properties, bookings, channel-sync

### 2. Tenant Isolation Audit
**Files Touched**:
- All service files (`app/services/*.py`)
- All repository queries

**DoD**:
- [ ] Audit report: List all queries, verify agency_id filter
- [ ] Fix any missing filters (add `WHERE agency_id = ?`)
- [ ] Document exceptions (e.g., `team_members` lookup by `user_id`)
- [ ] Tests: Verify user from Agency A cannot access Agency B data

### 3. Mandatory Migrations Workflow
**Files Touched**:
- `backend/migrations/README.md` (new file)
- `backend/docs/ops/migrations.md` (new file)

**DoD**:
- [ ] Document workflow: Create migration → Review → Apply → Rollback plan
- [ ] Placeholder migrations for `audit_log`, `agency_features`, `idempotency_keys`
- [ ] Migration naming convention documented
- [ ] Rollback procedure documented

### 4. Error Taxonomy
**Files Touched**:
- `app/core/exceptions.py` (standardize exceptions)
- All routers (use structured exceptions)

**DoD**:
- [ ] Define error codes (e.g., `BOOKING_CONFLICT`, `PROPERTY_NOT_FOUND`)
- [ ] All endpoints return `{"error": {"code": "...", "message": "..."}}`
- [ ] 4xx errors: Client errors (validation, not found, forbidden)
- [ ] 5xx errors: Server errors (DB down, external service timeout)
- [ ] Tests: Verify error response format

### 5. 503 Degraded Mode
**Files Touched**:
- `app/core/database.py` (DB health check)
- `app/core/redis.py` (Redis health check)
- `app/main.py` (startup health checks)

**DoD**:
- [ ] Health check endpoint `/health` returns DB + Redis status
- [ ] If DB unavailable, return 503 with `{"error": "database_unavailable"}`
- [ ] If Redis unavailable, log warning but continue (non-critical)
- [ ] Tests: Simulate DB down, verify 503 response

### 6. Ops Runbook Endpoints
**Files Touched**:
- `app/routers/ops.py` (new endpoints)
- `app/core/config.py` (add `COMMIT_SHA` env var)

**DoD**:
- [ ] `GET /ops/current-commit` returns `{"commit_sha": "...", "deployed_at": "..."}`
- [ ] `GET /ops/env-sanity` returns `{"db": "ok", "redis": "ok", "celery": "ok", "env_vars": [...]}`
- [ ] Endpoints are admin-only
- [ ] Tests: Verify response format

## APIs Touched

**New Endpoints**:
- `GET /ops/current-commit` (admin-only)
- `GET /ops/env-sanity` (admin-only)

**Modified Endpoints** (RBAC enforcement):
- `POST /api/v1/bookings` (require manager or admin)
- `GET /api/v1/properties` (require authenticated user)
- `GET /api/v1/channel-connections` (require admin)

**No Breaking Changes**: Existing endpoints remain functional.

## Database Changes

**New Tables** (placeholder migrations):
1. `audit_log`:
   ```sql
   CREATE TABLE audit_log (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     agency_id UUID REFERENCES agencies(id),
     user_id UUID REFERENCES auth.users(id),
     action TEXT NOT NULL,  -- e.g., 'booking.create', 'role.change'
     resource_type TEXT,    -- e.g., 'booking', 'property'
     resource_id UUID,
     details JSONB,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_audit_log_agency ON audit_log(agency_id, created_at DESC);
   ```

2. `idempotency_keys`:
   ```sql
   CREATE TABLE idempotency_keys (
     key TEXT PRIMARY KEY,
     agency_id UUID NOT NULL REFERENCES agencies(id),
     response JSONB,
     created_at TIMESTAMPTZ DEFAULT NOW(),
     expires_at TIMESTAMPTZ NOT NULL
   );
   CREATE INDEX idx_idempotency_keys_expires ON idempotency_keys(expires_at);
   ```

3. `agency_features`:
   ```sql
   CREATE TABLE agency_features (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     agency_id UUID NOT NULL REFERENCES agencies(id),
     feature_name TEXT NOT NULL,  -- e.g., 'channel_sync', 'direct_booking'
     enabled BOOLEAN DEFAULT TRUE,
     config JSONB,  -- Feature-specific config
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW(),
     UNIQUE(agency_id, feature_name)
   );
   CREATE INDEX idx_agency_features_agency ON agency_features(agency_id);
   ```

**RLS Policies**:
- Add RLS policies for all new tables (agency_id scoped)

## Ops Notes

### Deployment
1. Apply migrations (audit_log, idempotency_keys, agency_features)
2. Deploy backend with RBAC enforcement
3. Verify ops endpoints are accessible
4. Monitor error logs for unexpected 403s (role enforcement)

### Monitoring
- Alert on 503 errors (degraded mode triggered)
- Alert on `/ops/env-sanity` failures
- Monitor RBAC denials (403s) for unexpected patterns

### Rollback Plan
- If RBAC breaks existing workflows, add temporary feature flag `ENFORCE_RBAC=false`
- Migrations are idempotent and reversible
- Ops endpoints are read-only, safe to deploy/rollback

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| RBAC too restrictive, breaks workflows | High | Phased rollout, feature flag |
| Tenant isolation audit finds many issues | Medium | Prioritize critical endpoints, fix iteratively |
| Migration failures in production | High | Test migrations in staging, rollback plan |
| 503 degraded mode triggers false alarms | Low | Tune health check thresholds |

## Dependencies

**Blocks**:
- Phase 2 (booking idempotency requires `idempotency_keys` table)
- Phase 4 (channel sync audit requires RBAC + tenant isolation)

**Depends On**:
- None (foundation phase)

## Success Metrics

- ✓ 100% of queries verified for tenant isolation
- ✓ All endpoints return structured errors
- ✓ Ops endpoints deployed and monitored
- ✓ Zero security regressions (RLS bypasses)

## Next Steps

1. Review this spec with team
2. Create Phase 1 tickets (`/docs/tickets/phase-1.md`)
3. Assign tickets and kickoff sprint
4. Daily standups to track progress

---

**Related Documents**:
- [Roadmap Overview](./overview.md)
- [Phase 1 Tickets](../tickets/phase-1.md)
- [Modules & Entitlements](../architecture/modules-and-entitlements.md)
- [Error Taxonomy](../architecture/error-taxonomy.md)
