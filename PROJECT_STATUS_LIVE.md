# Project Status (Live)

**Purpose**: Current staging/deploy reality (manually maintained)

**Audience**: Ops engineers, developers, on-call

**Last Updated**: 2025-12-30

**Important**: This file is MANUALLY MAINTAINED. For historical code-derived snapshots, see [_staging/status-review-v3/](_staging/status-review-v3/PROJECT_STATUS.md).

---

## What's Deployed (Staging)

### Backend (FastAPI)

**Container**: `pms-backend` (Coolify deployment)

**API Endpoints**:
- ✅ `/health` - Health check (always returns 200, even if DB unavailable)
- ✅ `/health/ready` - Readiness check (returns 503 if DB unavailable)
- ✅ `/api/v1/properties` - Properties CRUD
- ✅ `/api/v1/bookings` - Bookings CRUD
- ✅ `/api/v1/availability` - Availability blocks, inventory ranges
- ❌ `/ops/*` - Backend ops router (EXISTS but NOT MOUNTED - dead code)

**Feature Flags**:
- `MODULES_ENABLED=true` (default, module system active)
- `CHANNEL_MANAGER_ENABLED=false` (default, channel manager disabled)

**Related Docs**: [Feature Flags](ops/feature-flags.md)

---

### Worker (Celery)

**Container**: `pms-worker-v2` (Coolify deployment)

**Broker**: Redis (shared with backend)

**Tasks**:
- Availability sync tasks
- Channel manager tasks (if `CHANNEL_MANAGER_ENABLED=true`)

**How to Verify in Coolify**:
1. Check container `pms-worker-v2` is running
2. Verify env vars: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
3. Check logs: `docker logs pms-worker-v2 --tail 50`

**Related Docs**: [Channel Manager Architecture](architecture/channel-manager.md)

---

### Redis

**Purpose**: Celery broker, caching (if used)

**Network**: Shared with backend and worker

**How to Verify in Coolify**:
1. Check Redis container is running (name varies by Coolify deployment)
2. Verify backend can connect: check `REDIS_URL` or `CELERY_BROKER_URL` env vars
3. Test connection: `redis-cli -u $REDIS_URL ping` (should return PONG)

---

### Database (Supabase)

**Provider**: Supabase (PostgreSQL)

**Hostname**: `supabase-db` (DNS name, requires network attachment)

**Network**: `bccg4gs4o4kgsowocw08wkw4` (Supabase network, Coolify-specific)

**Migrations Applied**: 16 migrations (as of 2025-12-30)

**Key Tables**:
- `agencies` - Multi-tenancy root
- `properties` - Property management
- `bookings` - Booking records
- `inventory_ranges` - Availability + bookings (unified, with EXCLUSION constraint)
- `team_members` - RBAC (5 roles: admin, manager, staff, owner, accountant)

**Concurrency Protection**: PostgreSQL EXCLUSION constraint prevents overlapping bookings

**Related Docs**:
- [Migrations Guide](database/migrations-guide.md)
- [EXCLUSION Constraints](database/exclusion-constraints.md)

---

### Frontend (Next.js)

**Platform**: UNKNOWN (check deployment platform)

**Routes**:
- ✅ `/login` - Login page (Supabase Auth)
- ✅ `/channel-sync/*` - Channel sync pages (authenticated users)
- ✅ `/ops/*` - Ops Console (admin-only, requires `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1`)

**Feature Flags**:
- `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` - Ops Console feature flag (status: UNKNOWN, check deployment)

**Related Docs**:
- [Frontend Authentication](frontend/authentication.md)
- [Frontend Ops Console](frontend/ops-console.md)

---

## Known Failure Modes

### 1. DB DNS / Degraded Mode

**Symptom**: API returns 503 after deploy/restart

**Cause**: Backend container cannot resolve `supabase-db` DNS (missing network attachment)

**Fix**: Attach backend container to Supabase network (`bccg4gs4o4kgsowocw08wkw4`)

**Mitigation**: Auto-heal cron script (`pms_ensure_supabase_net.sh`, runs every 2 minutes)

**Related Docs**: [Runbook - DB DNS / Degraded Mode](ops/runbook.md#db-dns--degraded-mode)

---

### 2. Schema Drift

**Symptom**: API returns 503 with "Schema not installed/out of date"

**Cause**: Deployed database schema doesn't match migration files

**Fix**: Apply missing migrations via `supabase db push`

**Related Docs**: [Runbook - Schema Drift](ops/runbook.md#schema-drift)

---

### 3. JWT Auth Fails

**Symptom**: 401 Unauthorized despite valid token

**Cause**: `JWT_SECRET` or `SUPABASE_JWT_SECRET` misconfigured

**Fix**: Verify env var matches Supabase project JWT secret

**Related Docs**: [Runbook - Token Validation](ops/runbook.md#token-validation-apikey-header)

---

### 4. Ops Console Disabled

**Symptom**: Admin users see "Ops Console is Disabled" message

**Cause**: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` not set in frontend deployment

**Fix**: Set `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1` and redeploy frontend

**Related Docs**: [Feature Flags - NEXT_PUBLIC_ENABLE_OPS_CONSOLE](ops/feature-flags.md#next_public_enable_ops_console)

---

## Key URLs (Staging)

**Backend API**: https://api.fewo.kolibri-visions.de

**Frontend Admin UI**: https://admin.fewo.kolibri-visions.de

**Supabase Gateway**: https://sb-pms.kolibri-visions.de

**Coolify Dashboard**: (check deployment platform credentials)

---

## RBAC (Role-Based Access Control)

**5 Roles** (from `team_members` table):
1. `admin` - Full system access (ops console, all endpoints)
2. `manager` - Agency management (properties, bookings CRUD)
3. `staff` - Day-to-day operations (limited CRUD)
4. `owner` - Property owner (limited read access)
5. `accountant` - Financial data access (read-only)

**Multi-Tenancy**: Agency-based isolation via `agency_id` (RLS policies enforce)

**Related Docs**: [status-review-v3/PROJECT_STATUS.md - RBAC](_staging/status-review-v3/PROJECT_STATUS.md#rbac-role-based-access-control)

---

## Next Steps (Ops)

### Immediate Actions

1. ✅ Verify DB network attachment (backend container attached to `bccg4gs4o4kgsowocw08wkw4`)
2. ✅ Verify `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1` if ops console is needed
3. ✅ Run smoke tests after deployment (check `/health`, `/health/ready`)

**Related Docs**: [Runbook](ops/runbook.md)

---

### Monitoring

**Smoke Tests**: UNKNOWN (check if smoke script is deployed)

**Logs**: UNKNOWN (check Coolify logs or deployment platform)

**Metrics**: UNKNOWN (check if metrics collection is deployed)

**Related Docs**: [Testing Guide - Smoke Tests](testing/README.md#smoke-tests-recommended)

---

## Related Documentation

### Operational

- **[Runbook](ops/runbook.md)** - Troubleshooting production issues (DB DNS, token validation, schema drift)
- **[Feature Flags](ops/feature-flags.md)** - Central reference for all feature toggles

### Architecture

- **[Module System](architecture/module-system.md)** - Module registry, graceful degradation
- **[Channel Manager](architecture/channel-manager.md)** - Channel sync architecture (disabled by default)

### Database

- **[Migrations Guide](database/migrations-guide.md)** - How to create/apply migrations
- **[EXCLUSION Constraints](database/exclusion-constraints.md)** - Double-booking prevention

### Frontend

- **[Authentication](frontend/authentication.md)** - SSR auth, session refresh
- **[Ops Console](frontend/ops-console.md)** - Admin-only ops pages

### Testing

- **[Testing Guide](testing/README.md)** - Test organization, smoke tests

---

## Historical Snapshots (Code-Derived)

**For code-derived status snapshots** (commit-bound, read-only):
- [status-review-v3/PROJECT_STATUS.md](_staging/status-review-v3/PROJECT_STATUS.md) - Snapshot at commit `7f34c7d` (2025-12-30 21:01 UTC)
- [status-review-v2/PROJECT_STATUS.md](_staging/status-review-v2/PROJECT_STATUS.md) - Snapshot at commit `1c42e95` (2025-12-30 20:48 UTC)
- [status-review-v1/PROJECT_STATUS.md](_staging/status-review-v1/PROJECT_STATUS.md) - Snapshot at commit `393ba8da` (2025-12-30 17:34 UTC)

---

**Last Updated**: 2025-12-30
**Maintained By**: Backend Team
**Update Frequency**: Manual (update after significant deployments or config changes)
