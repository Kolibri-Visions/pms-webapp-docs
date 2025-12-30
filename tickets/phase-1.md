# Phase 1 Tickets: Foundation & Ops Tooling

**Sprint**: 1 of 5
**Total Tickets**: 15
**Estimated Points**: 21

## Ticket List

### P1-01: Create RBAC helper functions
**Priority**: High
**Points**: 2
**Owner**: Backend

**Description**:
Create helper functions for role-based access control (RBAC) enforcement.

**Touch Points**:
- `app/core/auth.py` (add `require_role()`, `has_role()`)
- `app/dependencies.py` (add role dependencies)

**Acceptance Criteria**:
- [ ] `require_role(role: str)` dependency works for all 5 roles
- [ ] `has_role(user, role)` helper returns boolean
- [ ] Unit tests for role checking logic

**Rollout Notes**:
- No breaking changes, new helpers only

---

### P1-02: Enforce RBAC on properties endpoints
**Priority**: High
**Points**: 2
**Owner**: Backend

**Description**:
Add role enforcement to properties CRUD endpoints.

**Touch Points**:
- `app/routers/properties.py` (add `require_role()` dependencies)

**Acceptance Criteria**:
- [ ] `POST /api/v1/properties` requires admin or manager role
- [ ] `DELETE /api/v1/properties/:id` requires admin role
- [ ] Non-admin users get 403 Forbidden
- [ ] Tests: Role enforcement for all operations

**Rollout Notes**:
- May break existing workflows if non-admins were creating properties

---

### P1-03: Enforce RBAC on bookings endpoints
**Priority**: High
**Points**: 2
**Owner**: Backend

**Description**:
Add role enforcement to bookings CRUD endpoints.

**Touch Points**:
- `app/routers/bookings.py` (add role checks)

**Acceptance Criteria**:
- [ ] `POST /api/v1/bookings` requires manager, admin, or staff role
- [ ] `DELETE /api/v1/bookings/:id` requires admin or manager role
- [ ] Owners can only view their own bookings
- [ ] Tests: Role enforcement, owner isolation

**Rollout Notes**:
- Owner-only endpoints must enforce `user_id = owner_id`

---

### P1-04: Tenant isolation audit - properties service
**Priority**: High
**Points**: 3
**Owner**: Backend

**Description**:
Audit all queries in properties service for agency_id filtering.

**Touch Points**:
- `app/services/properties.py` (verify all queries filter by agency_id)

**Acceptance Criteria**:
- [ ] List all queries, verify agency_id filter exists
- [ ] Add missing filters where needed
- [ ] Document exceptions (e.g., admin cross-agency access)
- [ ] Tests: Verify Agency A cannot access Agency B properties

**Rollout Notes**:
- Critical for multi-tenant security

---

### P1-05: Tenant isolation audit - bookings service
**Priority**: High
**Points**: 3
**Owner**: Backend

**Description**:
Audit all queries in bookings service for agency_id filtering.

**Touch Points**:
- `app/services/bookings.py` (verify agency_id filtering)

**Acceptance Criteria**:
- [ ] Verify all booking queries filter by agency_id
- [ ] Fix any missing filters
- [ ] Tests: Cross-agency access denied

**Rollout Notes**:
- Critical security fix

---

### P1-06: Create error taxonomy and exceptions
**Priority**: High
**Points**: 2
**Owner**: Backend

**Description**:
Define standardized error codes and exception classes.

**Touch Points**:
- `app/core/exceptions.py` (add error codes, custom exceptions)

**Acceptance Criteria**:
- [ ] Define error codes: `BOOKING_CONFLICT`, `PROPERTY_NOT_FOUND`, etc.
- [ ] Create exception classes: `BookingConflictError`, `PropertyNotFoundError`
- [ ] All exceptions include code + message
- [ ] Documentation: Error code reference

**Rollout Notes**:
- Foundation for consistent error handling

---

### P1-07: Convert endpoints to use structured errors
**Priority**: Medium
**Points**: 3
**Owner**: Backend

**Description**:
Update all endpoints to return structured error responses.

**Touch Points**:
- All routers (`app/routers/*.py`)
- `app/main.py` (exception handlers)

**Acceptance Criteria**:
- [ ] All errors return `{"error": {"code": "...", "message": "..."}}`
- [ ] 4xx errors: Client errors
- [ ] 5xx errors: Server errors
- [ ] Tests: Verify error response format

**Rollout Notes**:
- Breaking change if clients depend on old error format

---

### P1-08: Implement 503 degraded mode
**Priority**: Medium
**Points**: 2
**Owner**: Backend

**Description**:
Return 503 when critical services (DB, Redis) are unavailable.

**Touch Points**:
- `app/core/database.py` (health check)
- `app/core/redis.py` (health check)
- `app/main.py` (startup checks)

**Acceptance Criteria**:
- [ ] Health check endpoint `/health` returns service status
- [ ] If DB unavailable, return 503
- [ ] If Redis unavailable, log warning (non-critical)
- [ ] Tests: Simulate DB down, verify 503

**Rollout Notes**:
- Improves error visibility during outages

---

### P1-09: Create ops/current-commit endpoint
**Priority**: Medium
**Points**: 1
**Owner**: Backend

**Description**:
Create endpoint to return current commit SHA and deployment timestamp.

**Touch Points**:
- `app/routers/ops.py` (new endpoint)
- `app/core/config.py` (add `COMMIT_SHA` env var)

**Acceptance Criteria**:
- [ ] `GET /ops/current-commit` returns `{"commit_sha": "...", "deployed_at": "..."}`
- [ ] Admin-only endpoint
- [ ] Tests: Verify response format

**Rollout Notes**:
- Useful for debugging production issues

---

### P1-10: Create ops/env-sanity endpoint
**Priority**: Medium
**Points**: 2
**Owner**: Backend

**Description**:
Create endpoint to check environment health (DB, Redis, Celery).

**Touch Points**:
- `app/routers/ops.py` (new endpoint)
- `app/core/health.py` (health check helpers)

**Acceptance Criteria**:
- [ ] `GET /ops/env-sanity` returns `{"db": "ok", "redis": "ok", "celery": "ok"}`
- [ ] Include env var check (missing required vars)
- [ ] Admin-only endpoint
- [ ] Tests: Verify response format

**Rollout Notes**:
- Helps diagnose configuration issues

---

### P1-11: Create audit_log migration
**Priority**: Low
**Points**: 1
**Owner**: Backend

**Description**:
Create database migration for audit_log table.

**Touch Points**:
- `backend/migrations/` (new migration file)
- `supabase/migrations/` (SQL migration)

**Acceptance Criteria**:
- [ ] Migration creates `audit_log` table
- [ ] RLS policies added (agency_id scoped)
- [ ] Indexes on agency_id, created_at
- [ ] Rollback script included

**Rollout Notes**:
- Run migration in staging first

---

### P1-12: Create idempotency_keys migration
**Priority**: Low
**Points**: 1
**Owner**: Backend

**Description**:
Create database migration for idempotency_keys table.

**Touch Points**:
- `backend/migrations/` (new migration file)
- `supabase/migrations/` (SQL migration)

**Acceptance Criteria**:
- [ ] Migration creates `idempotency_keys` table
- [ ] RLS policies added
- [ ] Index on expires_at
- [ ] Rollback script included

**Rollout Notes**:
- Prepare for Phase 2 booking idempotency

---

### P1-13: Create agency_features migration
**Priority**: Low
**Points**: 1
**Owner**: Backend

**Description**:
Create database migration for agency_features table (feature flags).

**Touch Points**:
- `backend/migrations/` (new migration file)
- `supabase/migrations/` (SQL migration)

**Acceptance Criteria**:
- [ ] Migration creates `agency_features` table
- [ ] RLS policies added
- [ ] Unique constraint on (agency_id, feature_name)
- [ ] Rollback script included

**Rollout Notes**:
- Foundation for modular entitlements

---

### P1-14: Document migration workflow
**Priority**: Medium
**Points**: 1
**Owner**: Backend

**Description**:
Document the migration creation, review, and deployment process.

**Touch Points**:
- `backend/docs/ops/migrations.md` (new file)
- `backend/migrations/README.md` (new file)

**Acceptance Criteria**:
- [ ] Document: How to create migration
- [ ] Document: Review checklist (RLS, indexes, rollback)
- [ ] Document: Deployment process (staging → production)
- [ ] Document: Rollback procedure

**Rollout Notes**:
- Living document, update as process evolves

---

### P1-15: Phase 1 retrospective
**Priority**: Low
**Points**: 1
**Owner**: Team

**Description**:
Conduct Phase 1 retrospective and update roadmap.

**Touch Points**:
- `backend/docs/roadmap/overview.md` (update progress)
- Retrospective notes

**Acceptance Criteria**:
- [ ] Team retrospective held
- [ ] Lessons learned documented
- [ ] Roadmap updated with actual progress
- [ ] Blockers escalated

**Rollout Notes**:
- Continuous improvement

---

## Ticket Summary by Priority

| Priority | Count | Points |
|----------|-------|--------|
| High     | 6     | 14     |
| Medium   | 7     | 10     |
| Low      | 2     | 2      |
| **Total**| **15**| **26** |

## Dependencies

```
P1-06 (Error taxonomy) → P1-07 (Convert endpoints)
P1-11, P1-12, P1-13 (Migrations) → P1-14 (Document workflow)
```

## Next Steps

1. Assign tickets to team members
2. Daily standups to track progress
3. Update ticket status in this file
4. Phase 1 retrospective (P1-15)
