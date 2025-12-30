# Project Status Report - v2

**Status**: Code-Derived Evidence-Based Review
**Method**: Read-Only Analysis (No Code Execution)

---

## Repository Snapshot

- **Reviewed Commit**: `1c42e9598044a0928462522f58e1a8019ad1737e`
- **Generated At**: `2025-12-30 20:48:06 UTC`
- **Scope Scanned**: backend + frontend + worker + scripts (read-only)
- **Previous Review (v1)**: `393ba8da` at `2025-12-30 17:34:20 UTC` (3.25 hours earlier)

---

## Deployment Facts (from docs/runbook only)

**Source**: `backend/docs/ops/runbook.md`

### Production Environment
- **Container Names**: `pms-backend`, `pms-worker-v2`
- **Networks**:
  - Default: `coolify`
  - Supabase: `bccg4gs4o4kgsowocw08wkw4`
- **Database Host**: `supabase-db` (internal DNS)
- **Auto-Heal**: Cron job every 2 minutes (`/usr/local/bin/pms_ensure_supabase_net.sh`)
- **Log Path**: `/var/log/pms_ensure_supabase_net.log`

### Deployment Platform
- **Orchestrator**: Coolify (inferred from runbook)
- **Database**: Supabase PostgreSQL (pooled via pgBouncer)

###URLs/Endpoints
- **Not Documented**: No production URLs found in runbook
- **Health Endpoints**: `/health`, `/health/ready` (mentioned in troubleshooting)

---

## Status Matrix Legend

**3-Axis Assessment** for each component:

| Axis | Values | Meaning |
|------|--------|---------|
| **A) Implemented** | Yes / Partial / No / Unknown | Code exists and functional |
| **B) Wired/Config** | Yes / Partial / No / Unknown | Router mounted, feature flags set |
| **C) Deployed/Verified** | Yes / Partial / No / Unknown | Evidence in runbook/scripts |

---

## Backend API Status

### API Routing

**All routes mount under `/api/v1` prefix** (Module system active)

| Component | Implemented | Wired | Deployed | Evidence |
|-----------|-------------|-------|----------|----------|
| **Properties API** | ✅ Yes | ✅ Yes | ⚠️ Partial | main.py:134, modules/properties.py |
| **Bookings API** | ✅ Yes | ✅ Yes | ⚠️ Partial | main.py:135, modules/bookings.py |
| **Availability API** | ✅ Yes | ✅ Yes | ⚠️ Partial | main.py:136, modules/inventory.py |
| **Health Check** | ✅ Yes | ✅ Yes | ✅ Yes | core/health.py, runbook mentions /health |
| **Ops API** | ⚠️ Partial | ❌ No | ❌ No | routers/ops.py EXISTS but NOT mounted |

**Key Findings**:
1. Properties: `/api/v1/properties/*` (5 endpoints)
2. Bookings: `/api/v1/bookings/*` (6 endpoints)
3. Availability: `/api/v1/availability/*` (4 endpoints + sync)
4. Health: `/health` (NO `/api/v1` prefix)
5. **Ops Router NOT MOUNTED**: Code exists but not registered in module system

**Evidence**:
- API prefix: `backend/app/main.py:134-136` (include_router with prefix="/api/v1")
- Module system: `backend/app/modules/bootstrap.py:119-131` (mount_all)
- Ops NOT mounted: `rg "from.*ops.*router" backend --type py` returns ZERO results

---

### Properties API (`/api/v1/properties`)

| Endpoint | Method | Implemented | Wired | RBAC | Evidence |
|----------|--------|-------------|-------|------|----------|
| List properties | GET | ✅ Yes | ✅ Yes | All roles | routes/properties.py:46-110 |
| Get property | GET | ✅ Yes | ✅ Yes | All roles | routes/properties.py:112-148 |
| Create property | POST | ✅ Yes | ✅ Yes | admin, manager | routes/properties.py:150-190, require_roles:161 |
| Update property | PATCH | ✅ Yes | ✅ Yes | admin, manager, owner | routes/properties.py:192-248 |
| Delete property | DELETE | ✅ Yes | ✅ Yes | admin, manager | routes/properties.py:251-289, require_roles:261 |

**Tenant Isolation**: ✅ All queries filter by `agency_id` from JWT

**Evidence**: `backend/app/api/routes/properties.py` (full file read)

---

### Bookings API (`/api/v1/bookings`)

| Endpoint | Method | Implemented | Wired | RBAC | Evidence |
|----------|--------|-------------|-------|------|----------|
| List bookings | GET | ✅ Yes | ✅ Yes | All roles | routes/bookings.py:68-156 |
| Get booking | GET | ✅ Yes | ✅ Yes | All roles | routes/bookings.py:159-198 |
| Create booking | POST | ✅ Yes | ✅ Yes | admin, manager, staff | routes/bookings.py:201-311, require_roles:213 |
| Update booking | PATCH | ✅ Yes | ✅ Yes | admin, manager, staff | routes/bookings.py:314-383 |
| Update status | PATCH | ✅ Yes | ✅ Yes | admin, manager, staff | routes/bookings.py:386-436 |
| Cancel booking | POST | ✅ Yes | ✅ Yes | admin, manager | routes/bookings.py:439-500, require_roles:451 |

**State Machine**: ✅ Implemented
- inquiry → [pending, confirmed, declined]
- pending → [confirmed, cancelled]
- confirmed → [checked_in, cancelled]
- checked_in → [checked_out, cancelled]

**Idempotency**: ❌ Not implemented (no idempotency_keys table)

**Evidence**:
- Endpoints: `backend/app/api/routes/bookings.py` (full file)
- State machine: `backend/app/services/booking_service.py:91-100` (VALID_TRANSITIONS)
- Idempotency: `rg "idempotency" backend --type py` found references but no table

---

### Availability API (`/api/v1/availability`)

| Endpoint | Method | Implemented | Wired | RBAC | Evidence |
|----------|--------|-------------|-------|------|----------|
| Query availability | GET | ✅ Yes | ✅ Yes | All roles | routes/availability.py:98-236 |
| Create block | POST | ✅ Yes | ✅ Yes | admin, manager, owner | routes/availability.py:238-328, require_roles:251 |
| Delete block | DELETE | ✅ Yes | ✅ Yes | admin, manager, owner | routes/availability.py:331-413 |
| Sync to channel | POST | ✅ Yes | ✅ Yes | admin, manager | routes/availability.py:558-761, require_roles:570 |

**Inventory System**: ✅ PostgreSQL EXCLUSION constraint enforced

**Retry Logic**: ✅ Exponential backoff (3 attempts, 1s/2s/4s delays)

**Evidence**:
- Endpoints: `backend/app/api/routes/availability.py` (full file)
- EXCLUSION: `supabase/migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql`
- Retry: `backend/app/api/routes/availability.py:476-556` (_retry_with_exponential_backoff)

---

### Ops/Runbook API (`/ops/*`) ⚠️ CRITICAL FINDING

**Status**: ROUTER EXISTS BUT NOT MOUNTED (Dead Code)

| Component | Implemented | Wired | RBAC | Evidence |
|-----------|-------------|-------|------|----------|
| Ops Router | ⚠️ Partial | ❌ No | ❌ No | routers/ops.py:22-25 |
| `/ops/current-commit` | ⚠️ Stub | ❌ No | ❌ No | routers/ops.py:28-54 (TODO comments) |
| `/ops/env-sanity` | ⚠️ Stub | ❌ No | ❌ No | routers/ops.py:57-114 (hardcoded "ok") |

**Why This Is Dead Code**:
1. Router defined in `backend/app/routers/ops.py`
2. NOT imported in `backend/app/main.py`
3. NOT registered in `backend/app/modules/core.py` or any module
4. `rg "from.*ops.*router" backend --type py` returns ZERO results
5. Endpoints return placeholder data (stub implementation)

**TODO Comments in Code**:
- Line 42-45: "Add RBAC: Require admin role"
- Line 81-85: "Implement actual health checks (currently stubs)"

**Evidence**:
- Router file: `backend/app/routers/ops.py` (read lines 1-122)
- NOT mounted: `rg "import.*ops" backend/app/main.py` → No results
- NOT in modules: `cat backend/app/modules/core.py` → Only health router registered

**Recommendation**: Either mount the router OR delete as dead code

---

### Health Check API (`/health`)

| Endpoint | Implemented | Wired | Deployed | Evidence |
|-----------|-------------|-------|----------|----------|
| `/health` | ✅ Yes | ✅ Yes | ✅ Yes | core/health.py, runbook mentions it |
| `/health/ready` | ✅ Yes | ✅ Yes | ✅ Yes | core/health.py, runbook troubleshooting |

**Evidence**:
- Implementation: `backend/app/core/health.py`
- Wired: `backend/app/modules/core.py:16-28` (health_router registered)
- Deployed: `backend/docs/ops/runbook.md:29` ("Health endpoint (`/health`) returns 200")

---

## Authentication & Authorization

### JWT Authentication

| Component | Implemented | Wired | Evidence |
|-----------|-------------|-------|----------|
| JWT decode/verify | ✅ Yes | ✅ Yes | core/auth.py:87-173 |
| Signature verification | ✅ Yes | ✅ Always on | core/auth.py:95 (verify_signature: True) |
| Expiration verification | ✅ Yes | ✅ Always on | core/auth.py:96 (verify_exp: True) |
| Issuer verification | ⚠️ Partial | ⚠️ Optional | core/auth.py:106-112 (if JWT_ISSUER set) |
| Audience verification | ⚠️ Partial | ⚠️ Optional | core/auth.py:115-122 (if JWT_AUDIENCE set) |

**Evidence**: `backend/app/core/auth.py:57-177` (get_current_user function)

---

### RBAC System

**Roles**: admin, manager, staff, owner, accountant (5 roles)

| Component | Implemented | Wired | Evidence |
|-----------|-------------|-------|----------|
| `has_role()` | ✅ Yes | ✅ Yes | core/auth.py:324-350 |
| `has_any_role()` | ✅ Yes | ✅ Yes | core/auth.py:353-379 |
| `require_role()` | ✅ Yes | ✅ Yes | core/auth.py:382-428 |
| Unit tests | ✅ Yes | ❌ Not executed | tests/unit/test_rbac_helpers.py (136 lines, "DO NOT RUN") |

**Enforcement Status**:
- ✅ Properties API: require_roles enforced
- ✅ Bookings API: require_roles enforced
- ✅ Availability API: require_roles enforced
- ❌ Ops API: NO enforcement (router not mounted anyway)

**Evidence**:
- Helpers: `backend/app/core/auth.py:320-428` (RBAC helpers section)
- Tests: `backend/tests/unit/test_rbac_helpers.py:7-8` (warning header)

---

### Multi-Tenant Isolation

| Component | Implemented | Wired | Evidence |
|-----------|-------------|-------|----------|
| `get_current_agency_id()` | ✅ Yes | ✅ Yes | api/deps.py:53-220 |
| X-Agency-Id header | ✅ Yes | ✅ Yes | api/deps.py:94-137 |
| Profile fallback | ✅ Yes | ✅ Yes | api/deps.py:140-200 |
| Team membership validation | ✅ Yes | ✅ Yes | api/deps.py:111-128 |

**Agency Resolution Order**:
1. X-Agency-Id header (preferred)
2. User's last_active_agency_id from profiles
3. First active team membership (created_at ASC)

**Evidence**: `backend/app/api/deps.py:53-220` (get_current_agency_id function)

---

## Frontend Status

### Routes & Pages

| Route | Implemented | SSR Auth | Admin Only | Feature Flag | Evidence |
|-------|-------------|----------|------------|--------------|----------|
| `/login` | ✅ Yes | No | No | None | app/login/page.tsx |
| `/ops/*` | ✅ Yes | ✅ Yes | ✅ Yes | NEXT_PUBLIC_ENABLE_OPS_CONSOLE | app/ops/layout.tsx:94-140 |
| `/channel-sync/*` | ✅ Yes | ✅ Yes | No | None | app/channel-sync/layout.tsx |
| `/` | ✅ Yes | No | No | None | app/page.tsx |

**Frontend Ops Console**:
- Server-side admin check: `app/ops/layout.tsx:46-92`
- Feature flag required: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1`
- Access denied for non-admins (NO redirect loop)
- Diagnostics panel shown on access denial

**Evidence**: `frontend/app/ops/layout.tsx` (full file read, 254 lines)

---

### Middleware

| Component | Implemented | Applies To | Evidence |
|-----------|-------------|------------|----------|
| Session refresh | ✅ Yes | `/ops/*`, `/channel-sync/*`, `/login` | middleware.ts:71-76 |
| Cookie updates | ✅ Yes | All protected routes | middleware.ts:25-60 |

**Middleware Pattern**: Supabase SSR with cookie-based session

**Evidence**: `frontend/middleware.ts` (full file read)

---

## Channel Manager

**Status**: ⚠️ Partial Implementation

| Component | Implemented | Wired | Evidence |
|-----------|-------------|-------|----------|
| Sync engine | ✅ Yes | ⚠️ Conditional | channel_manager/core/sync_engine.py |
| Celery tasks | ✅ Yes | ⚠️ Unknown | routes/availability.py:668-694 (task.delay calls) |
| Adapters (base) | ✅ Yes | ✅ Yes | channel_manager/adapters/base_adapter.py |
| Airbnb adapter | ✅ Yes | ❓ Unknown | channel_manager/adapters/airbnb/adapter.py |
| Module registration | ✅ Yes | ⚠️ Flag-gated | modules/channel_manager.py, CHANNEL_MANAGER_ENABLED |

**Feature Flag**: `CHANNEL_MANAGER_ENABLED` (default: false)

**Evidence**:
- Module: `backend/app/modules/bootstrap.py:86-94` (conditional import)
- Tasks: `backend/app/api/routes/availability.py:63-66` (import update_channel_availability)

---

## Module System

**Status**: ✅ Active (Production Feature)

| Component | Implemented | Wired | Evidence |
|-----------|-------------|-------|----------|
| Module registry | ✅ Yes | ✅ Yes | modules/registry.py |
| Bootstrap/mounting | ✅ Yes | ✅ Yes | modules/bootstrap.py:30-140 |
| Graceful degradation | ✅ Yes | ✅ Yes | modules/bootstrap.py:61-83 (try/except imports) |
| Feature flag | ✅ Yes | ✅ Yes | main.py:117 (MODULES_ENABLED) |
| Fallback mode | ✅ Yes | ✅ Yes | main.py:126-136 (explicit router mounting) |

**Registered Modules**:
1. core_pms (health router)
2. properties (properties router, /api/v1)
3. bookings (bookings router, /api/v1)
4. inventory (availability router, /api/v1)
5. channel_manager (conditional, default OFF)

**Evidence**:
- Registry: `backend/app/modules/registry.py` (full file)
- Bootstrap: `backend/app/modules/bootstrap.py` (full file)
- Main: `backend/app/main.py:117-136`

---

## Database

### Migrations

**Total Migrations**: 15 (in `supabase/migrations/`)

**Key Migrations**:
- `20251225190000_availability_inventory_system.sql` - Inventory ranges
- `20251229200517_enforce_overlap_prevention_via_exclusion.sql` - EXCLUSION constraint

**Evidence**: `ls supabase/migrations/` (15 files)

### Availability System

| Component | Implemented | Evidence |
|-----------|-------------|----------|
| inventory_ranges table | ✅ Yes | Migration 20251225190000 |
| EXCLUSION constraint | ✅ Yes | Migration 20251229200517 |
| Overlap prevention | ✅ Yes | PostgreSQL enforced |

**Evidence**: Migration filenames (grep for "inventory\|availability\|exclusion")

---

## Error Handling

| Component | Implemented | Wired | Evidence |
|-----------|-------------|-------|----------|
| Error code constants | ✅ Yes | ✅ Yes | core/exceptions.py (file too large) |
| AppError base class | ✅ Yes | ✅ Yes | core/exceptions.py |
| Typed exceptions (3) | ✅ Yes | ✅ Yes | core/exceptions.py, error-taxonomy.md:80-114 |
| Response format | ❌ No | ❌ No | error-taxonomy.md:130 ("NOT part of P1-06") |
| Exception handlers | ❌ No | ❌ No | error-taxonomy.md:163-167 (P1-07 pending) |

**Phase Status**:
- P1-06 (Error taxonomy): ✅ Complete
- P1-07 (Response format): ❌ Not started

**Evidence**: `backend/docs/architecture/error-taxonomy.md:128-168`

---

## Feature Flags

### Backend

| Flag | Default | Purpose | Evidence |
|------|---------|---------|----------|
| MODULES_ENABLED | true | Enable module system | main.py:117 |
| CHANNEL_MANAGER_ENABLED | false | Enable channel manager module | modules/bootstrap.py:86 |

### Frontend

| Flag | Default | Purpose | Evidence |
|------|---------|---------|----------|
| NEXT_PUBLIC_ENABLE_OPS_CONSOLE | undefined | Enable /ops/* pages | ops/layout.tsx:95-140 |

**Evidence**: File reads of main.py, bootstrap.py, layout.tsx

---

## Known Gaps

### Critical
1. **Ops Router NOT MOUNTED** - Dead code in backend
2. **Error response format not unified** - Phase 1 P1-07 pending
3. **Idempotency NOT implemented** - No idempotency_keys table

### High
4. **Ops endpoints lack RBAC** - No admin enforcement (but not mounted anyway)
5. **Channel manager deployment unknown** - CHANNEL_MANAGER_ENABLED default is false

### Medium
6. **RBAC tests not executed** - "DO NOT RUN" header in test file
7. **Tenant isolation audit incomplete** - No audit report document

---

## Recommendations

### Immediate Actions
1. **Decision on ops router**: Mount it OR delete dead code
2. **Document feature flags**: Create ops/feature-flags.md
3. **Execute RBAC tests**: Remove "DO NOT RUN" warning, run pytest

### Short-Term
4. **Implement P1-07**: Unified error response format
5. **Document API prefix**: Update all docs to show `/api/v1`
6. **Create module system doc**: Explain registry, graceful degradation

### Long-Term
7. **Tenant isolation audit**: Generate query audit report
8. **Idempotency implementation**: Create idempotency_keys table (P1-11)
9. **Channel manager docs**: Architecture and deployment guide

---

**End of Report**

**Next Steps**: Review DRIFT_REPORT.md for detailed doc vs code comparisons
