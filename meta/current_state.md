# PMS-Webapp – Current State

**Projekt:** PMS-Webapp (B2B SaaS für Ferienwohnungs-Agenturen)
**Stand:** 2025-12-23
**Phase:** 18A FROZEN v1.0
**Status:** ✅ Production-Ready für lokales Testing

---

## Frozen Phasen

- **Phase 10A–16:** Konzeptionelle Phasen (RBAC, Multi-Tenancy, Direct Booking, Eigentümer-Isolation)
- **Phase 17A:** GitHub Setup (FROZEN v1.0)
- **Phase 17B:** Database Schema & RLS Policies (FROZEN v1.0) - **SSOT für Schema**
- **Phase 18A:** Schema Alignment & RLS Implementation (FROZEN v1.0)

---

## Letzte Commits (7 Commits seit Phase 17B)

```
dce1ee0 chore: remove legacy migrations (superseded by frozen 18A set)
04ee061 docs: add Phase 18A implementation documentation (FROZEN v1.0)
15d4ce2 fix: remove redundant health router (BLOCKER FIX)
83dc771 feat: add seed data for local development and testing
da384fa feat: add Phase 17B compliant database migrations (agencies schema)
853090f chore: add Supabase local development configuration
6b42ced docs: add Phase 17B database schema and RLS policies (FROZEN v1.0)
```

---

## Wichtige Entscheidungen

### 1. Schema & Multi-Tenancy
- **Root Entity:** `agencies` (NICHT `tenants`)
- **SSOT:** `docs/phase17b-database-schema-rls.md`
- **Migrations:** 4 FROZEN Files in `supabase/migrations/202501010000*`
- **RLS:** 5 Rollen (admin, manager, staff, owner, accountant)

### 2. Deferred Components (Redis/Celery)
- **Default:** Skipped in health checks
- **Aktivierung:** Via Environment Variables:
  - `ENABLE_REDIS_HEALTHCHECK=true`
  - `ENABLE_CELERY_HEALTHCHECK=true`

### 3. Health Endpoints
- **Backend Port:** 8000 (FastAPI)
- **Liveness:** `GET /health` (immer UP)
- **Readiness:** `GET /health/ready` (DB mandatory, Redis/Celery optional)

### 4. Local Development
- **Supabase API:** Port 54321
- **Supabase DB:** Port 54322
- **Backend API:** Port 8000
- **Seed Data:** `supabase/seed.sql` (2 Agencies, 8 Users, 3 Properties, 4 Bookings)

---

## How to Resume Work

1. **Read CURRENT_STATE.md** (this file)
2. **Read latest phase doc:** `docs/phase18a-schema-alignment-rls-implementation.md`
3. **Run preflight checks:** See `docs/phase18a-preflight.md`

---

## Next Phase Proposal (NICHT STARTEN)

**Phase 19: Core Booking Flow API**

Deliverables:
1. FastAPI CRUD Endpoints für Properties (GET, POST, PUT, DELETE)
2. FastAPI CRUD Endpoints für Bookings (GET, POST, PUT, PATCH für Status-Transitions)
3. RBAC Middleware Integration (Permission Checks basierend auf team_members.role)
4. Booking Status Workflow (pending → confirmed → checked_in → checked_out → cancelled)
5. Validation Layer (Pydantic Schemas für Request/Response)
6. Error Handling & HTTP Status Codes (400, 401, 403, 404, 422, 500)
7. Integration Tests (pytest + TestClient)
8. OpenAPI Documentation (Swagger UI auf /docs)
9. Database Connection Pool Setup (asyncpg)
10. Environment Configuration (.env.example, settings.py)

**Basis:** Phase 17B Schema + Phase 18A Migrations + Seed Data

---

**Ende CURRENT_STATE.md**
