# Missing Documentation Gaps - v1

**Purpose**: Identify documentation gaps based on code analysis
**Source**: status-review-v3 (code scan findings)
**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd

---

## Summary

**8 missing documentation files identified** from code analysis (status-review-v3).

Each gap represents a feature/system that:
- ✅ EXISTS in code (verified in MANIFEST.md)
- ❌ NOT documented (or documentation scattered/incomplete)

---

## Gap 1: Module System Documentation

### What's Missing

**File**: `architecture/module-system.md` (does not exist)

### What Exists in Code

**Evidence** (from status-review-v3/MANIFEST.md):
- Module registry system: `backend/app/modules/bootstrap.py:30-140`
- Feature flag: `MODULES_ENABLED` (default: true) in `backend/app/main.py:117-136`
- Graceful degradation: Module import failures logged, app continues
- Auto-registration pattern: Modules self-register when imported

### Why It Matters

**Impact**: HIGH
- Deployment staff unaware of module system toggle
- New developers don't understand module registry pattern
- Graceful degradation behavior undocumented

### What Should Be Documented

**Proposed Content** (`architecture/module-system.md`):

```markdown
# Module System Architecture

## Overview
- Purpose: Modular router registration vs fallback
- Feature flag: MODULES_ENABLED (default: true)
- Graceful degradation strategy

## Module Registry
- Auto-registration pattern
- Module configuration (prefix, tags, dependencies)
- Validation (circular dependency detection)

## Registered Modules
1. core - Health router
2. inventory - Availability router
3. properties - Properties router
4. bookings - Bookings router
5. channel_manager - **Conditional** (CHANNEL_MANAGER_ENABLED)

## Fallback Routing
- When MODULES_ENABLED=false
- Explicit router mounting in main.py

## Graceful Degradation
- Module import failures (log warning, continue)
- Database unavailability (degraded mode, 503 for DB endpoints)

## Code References
- Module bootstrap: backend/app/modules/bootstrap.py
- Main app: backend/app/main.py:117-136
```

---

## Gap 2: Channel Manager Architecture

### What's Missing

**File**: `architecture/channel-manager.md` (does not exist)

### What Exists in Code

**Evidence** (from status-review-v3/MANIFEST.md):
- 9+ Python files in `backend/app/channel_manager/`
- Adapters: Airbnb adapter, base adapter, factory pattern
- Sync engine: `core/sync_engine.py`
- Rate limiter: `core/rate_limiter.py`
- Circuit breaker: `core/circuit_breaker.py`
- Webhooks: `webhooks/handlers.py`
- Monitoring: `monitoring/metrics.py`

### Why It Matters

**Impact**: HIGH
- Channel Manager implementation exists (9 files) but design undocumented
- Adapter pattern unclear to new developers
- Sync strategy, rate limiting, circuit breaker patterns undocumented

### What Should Be Documented

**Proposed Content** (`architecture/channel-manager.md`):

```markdown
# Channel Manager Architecture

## Overview
- Purpose: Multi-channel sync (Airbnb, Booking.com, etc.)
- Feature flag: CHANNEL_MANAGER_ENABLED (default: false)

## Architecture
- Adapter pattern for channel-specific logic
- Sync engine for orchestration
- Rate limiting, circuit breaker for resilience
- Webhook handlers for channel events
- Monitoring/metrics for observability

## Adapters
- Base adapter interface
- Airbnb adapter implementation
- Factory pattern for adapter selection

## Sync Strategy
- Pull vs push sync
- Conflict resolution
- Retry logic, backoff strategy

## Resilience
- Rate limiting (avoid API throttling)
- Circuit breaker (protect against downstream failures)
- Graceful degradation

## Celery Integration
- Async tasks for sync operations
- Redis broker
- Worker processes

## Code References
- Channel Manager: backend/app/channel_manager/
- Module gating: backend/app/modules/bootstrap.py:86-94
```

---

## Gap 3: Database Migrations Guide

### What's Missing

**File**: `database/migrations-guide.md` (does not exist)

### What Exists in Code

**Evidence** (from status-review-v3/MANIFEST.md):
- 16 database migrations in `supabase/migrations/`
- Naming convention: `YYYYMMDDHHMMSS_description.sql`
- Migration types: Schema, indexes, RLS policies, constraints

### Why It Matters

**Impact**: MEDIUM
- Contributors uncertain about migration workflow
- No guide on how to create migrations, naming conventions
- Rollback strategy undocumented

### What Should Be Documented

**Proposed Content** (`database/migrations-guide.md`):

```markdown
# Database Migrations Guide

## Overview
- Migration system: Supabase migrations
- Location: supabase/migrations/
- Naming: YYYYMMDDHHMMSS_description.sql

## Creating Migrations
1. Generate timestamp: `date -u +"%Y%m%d%H%M%S"`
2. Create file: `supabase/migrations/TIMESTAMP_description.sql`
3. Write SQL (DDL, DML)
4. Test locally before deploying

## Migration Types
1. Schema migrations (CREATE TABLE, ALTER TABLE)
2. Index migrations (CREATE INDEX)
3. RLS policy migrations (CREATE POLICY)
4. Data migrations (INSERT, UPDATE, DELETE)
5. Constraint migrations (EXCLUSION, UNIQUE, CHECK)

## Best Practices
- One migration per logical change
- Idempotent migrations (IF NOT EXISTS, IF EXISTS)
- No destructive operations without backup
- Test rollback strategy

## Deployment
- Supabase CLI: `supabase db push`
- Manual: Apply migrations in order
- Rollback: Write down migrations if needed

## Existing Migrations
- 16 migrations applied (see status-review-v3/MANIFEST.md)
```

---

## Gap 4: EXCLUSION Constraints Documentation

### What's Missing

**File**: `database/exclusion-constraints.md` (does not exist)

### What Exists in Code

**Evidence** (from status-review-v3/MANIFEST.md):
- Migration: `20251229200517_enforce_overlap_prevention_via_exclusion.sql`
- Table: `inventory_ranges`
- Constraint: `inventory_ranges_no_overlap`
- Type: PostgreSQL EXCLUSION constraint using GiST index
- Purpose: Database-level double-booking prevention

### Why It Matters

**Impact**: HIGH
- Critical concurrency mechanism undocumented
- Developers unaware of database-level double-booking protection
- EXCLUSION constraint pattern unfamiliar to many developers

### What Should Be Documented

**Proposed Content** (`database/exclusion-constraints.md`):

```markdown
# EXCLUSION Constraints for Concurrency Protection

## Overview
- Purpose: Database-level prevention of overlapping bookings
- Technology: PostgreSQL EXCLUSION constraints with GiST index
- Table: inventory_ranges

## Problem Statement
- Double-booking: Two bookings for same property, overlapping dates
- Application-level checks insufficient (race conditions)
- Database-level enforcement required

## Solution: EXCLUSION Constraint

### Constraint Definition
```sql
ALTER TABLE inventory_ranges
ADD CONSTRAINT inventory_ranges_no_overlap
EXCLUDE USING gist (
  property_id WITH =,
  daterange(start_date, end_date, '[)') WITH &&
)
WHERE (state = 'active');
```

### How It Works
- GiST index: Generalized Search Tree (supports range queries)
- `property_id WITH =`: Same property
- `daterange(...) WITH &&`: Overlapping date ranges
- `WHERE (state = 'active')`: Only active inventory ranges

### Behavior
- INSERT/UPDATE violates constraint → Error raised
- Application must catch error, handle conflict
- No race conditions (database-level enforcement)

## Application Integration
- Try/catch on INSERT/UPDATE
- Conflict error → Return 409 Conflict to client
- Typed exception: `BookingConflictError`

## Code References
- Migration: supabase/migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql
- Exception: backend/app/core/exceptions.py (BookingConflictError)
```

---

## Gap 5: Feature Flags Documentation

### What's Missing

**File**: `ops/feature-flags.md` (does not exist)

### What Exists in Code

**Evidence** (from status-review-v3/MANIFEST.md):

**3 Feature Flags**:
1. `MODULES_ENABLED` (backend) - Module system vs fallback
   - Default: true
   - Location: `backend/app/main.py:117`
2. `CHANNEL_MANAGER_ENABLED` (backend) - Channel Manager module
   - Default: false
   - Location: `backend/app/modules/bootstrap.py:86`
3. `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` (frontend) - Ops Console pages
   - Default: Unset (required to enable)
   - Location: `frontend/app/ops/layout.tsx:95`

### Why It Matters

**Impact**: HIGH
- Deployment staff unaware of feature toggles
- Ops console won't work without frontend feature flag
- Channel Manager disabled by default, undocumented

### What Should Be Documented

**Proposed Content** (`ops/feature-flags.md`):

```markdown
# Feature Flags Reference

## Overview
- Purpose: Control feature availability without code changes
- Configuration: Environment variables

## Backend Feature Flags

### MODULES_ENABLED
- **Purpose**: Enable module system vs fallback routing
- **Default**: `true`
- **Values**: `true` | `false`
- **Impact**: If false, uses explicit router mounting (bypasses module registry)
- **Location**: backend/app/main.py:117

### CHANNEL_MANAGER_ENABLED
- **Purpose**: Enable Channel Manager module
- **Default**: `false`
- **Values**: `true` | `false`
- **Impact**: If false, Channel Manager module not imported (disabled)
- **Location**: backend/app/modules/bootstrap.py:86

## Frontend Feature Flags

### NEXT_PUBLIC_ENABLE_OPS_CONSOLE
- **Purpose**: Enable Ops Console pages (/ops/*)
- **Default**: Unset (disabled)
- **Values**: `1` | `true` | `yes` | `on` (case-insensitive)
- **Impact**: If unset/false, Ops Console shows "disabled" message
- **Location**: frontend/app/ops/layout.tsx:95

## Deployment Checklist

### Production Deployment
- [ ] MODULES_ENABLED=true (use module system)
- [ ] CHANNEL_MANAGER_ENABLED=false (unless needed)
- [ ] NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1 (if ops staff need access)

### Development
- [ ] MODULES_ENABLED=true
- [ ] CHANNEL_MANAGER_ENABLED=true (if testing channel sync)
- [ ] NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1 (for testing)
```

---

## Gap 6: Testing Guide

### What's Missing

**File**: `testing/README.md` (does not exist)

### What Exists in Code

**Evidence** (from status-review-v3/MANIFEST.md):
- 15+ test files in `backend/tests/`
- Test types: unit, integration, security, smoke
- Test fixtures: `conftest.py`

### Why It Matters

**Impact**: MEDIUM
- Contributors uncertain about test structure
- No guide on how to run tests, add new tests
- Test fixtures undocumented

### What Should Be Documented

**Proposed Content** (`testing/README.md`):

```markdown
# Testing Guide

## Overview
- Test framework: pytest
- Location: backend/tests/
- Test types: unit, integration, security, smoke

## Running Tests

### All Tests
```bash
pytest backend/tests/
```

### Unit Tests Only
```bash
pytest backend/tests/unit/
```

### Integration Tests
```bash
# Requires DATABASE_URL and JWT_SECRET
export DATABASE_URL="postgresql://..."
export JWT_SECRET="..."
pytest backend/tests/integration/
```

## Test Organization

### Unit Tests (backend/tests/unit/)
- JWT verification
- RBAC helpers
- Agency dependency extraction
- Database generator

### Integration Tests (backend/tests/integration/)
- Availability API
- Bookings API
- RBAC enforcement
- Auth vs DB priority

### Security Tests (backend/tests/security/)
- Token encryption/decryption
- Redis client security
- Webhook signature validation

### Smoke Tests (backend/tests/smoke/)
- Channel Manager smoke test

## Test Fixtures (conftest.py)
- Database setup/teardown
- Test data generation
- Mock fixtures

## Adding New Tests
1. Choose test type (unit, integration, security, smoke)
2. Create test file: `test_{feature}.py`
3. Import fixtures from conftest.py
4. Write test cases with descriptive names
```

---

## Gap 7: Frontend Authentication Documentation

### What's Missing

**File**: `frontend/authentication.md` (does not exist, proposed location: `frontend/docs/authentication.md`)

### What Exists in Code

**Evidence** (from status-review-v3/MANIFEST.md):
- Middleware: `frontend/middleware.ts:77-82` (session refresh)
- Ops layout: `frontend/app/ops/layout.tsx:27-92` (SSR session + admin check)
- Supabase SSR: `@supabase/ssr` package

### Why It Matters

**Impact**: MEDIUM
- Frontend SSR authentication undocumented
- Middleware purpose unclear
- Admin role check pattern undocumented

### What Should Be Documented

**Proposed Content** (`frontend/docs/authentication.md`):

```markdown
# Frontend Authentication (Supabase SSR)

## Overview
- Auth provider: Supabase Auth
- Package: @supabase/ssr
- Pattern: Server-Side Rendering (SSR) with session refresh

## Middleware (Session Refresh)

### Purpose
- Refresh Supabase auth cookies on every request
- Ensure server components can read latest session

### Protected Routes
- /ops/:path* (Ops Console)
- /channel-sync/:path* (Channel Sync)
- /login (Login page)

### Implementation
- Location: frontend/middleware.ts
- Session refresh: `supabase.auth.getUser()`

## Server-Side Authentication

### Ops Console (/ops/*)

#### Session Check
- Server-side session validation
- Redirects to /login if no session

#### Admin Role Check
- Query team_members table for role
- Check role='admin'
- Shows "Access Denied" for non-admins

### Implementation
- Location: frontend/app/ops/layout.tsx:27-92
- Feature flag: NEXT_PUBLIC_ENABLE_OPS_CONSOLE

## Supabase Client (Server-Side)

### Creation
```typescript
import { createSupabaseServerClient } from '../lib/supabase-server';
const supabase = await createSupabaseServerClient();
```

### Session Access
```typescript
const { data: { session } } = await supabase.auth.getSession();
```

### Database Queries
```typescript
const { data } = await supabase
  .from('team_members')
  .select('role')
  .eq('user_id', userId);
```

## Code References
- Middleware: frontend/middleware.ts
- Ops layout: frontend/app/ops/layout.tsx
```

---

## Gap 8: Frontend Ops Console Documentation

### What's Missing

**File**: `frontend/ops-console.md` (does not exist, proposed location: `frontend/docs/ops-console.md`)

### What Exists in Code

**Evidence** (from status-review-v3/MANIFEST.md):
- Ops layout: `frontend/app/ops/layout.tsx:95-140` (feature flag check)
- Routes: `/ops/*` (protected by middleware)

### Why It Matters

**Impact**: LOW
- Frontend Ops Console pages exist but purpose/features undocumented
- Feature flag requirement undocumented

### What Should Be Documented

**Proposed Content** (`frontend/docs/ops-console.md`):

```markdown
# Frontend Ops Console

## Overview
- Purpose: Admin-only operational tools
- Routes: /ops/*
- Feature flag: NEXT_PUBLIC_ENABLE_OPS_CONSOLE

## Access Control

### Server-Side Checks
1. Session check (redirects to /login if no session)
2. Admin role check (shows "Access Denied" for non-admins)
3. Feature flag check (shows "Ops Console is Disabled" if flag unset)

### No Redirect Loop
- Non-admins see "Access Denied" message (no redirect to /channel-sync)
- Prevents infinite redirect loops

## Feature Flag

### Configuration
- Environment variable: NEXT_PUBLIC_ENABLE_OPS_CONSOLE
- Values: 1 | true | yes | on (case-insensitive)
- Default: Unset (disabled)

### Deployment
- Production: Set NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1 to enable
- Development: Set NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1 for testing

## Code References
- Ops layout: frontend/app/ops/layout.tsx
- Middleware: frontend/middleware.ts
```

---

## Implementation Priority

### High Priority (Deploy Blockers)

1. **ops/feature-flags.md** - Feature flags undocumented, blocks ops staff
2. **database/exclusion-constraints.md** - Critical concurrency mechanism undocumented
3. **architecture/module-system.md** - Deployment config unclear

### Medium Priority (Phase 1 Completion)

4. **architecture/channel-manager.md** - Channel Manager design undocumented
5. **database/migrations-guide.md** - Migration workflow unclear
6. **testing/README.md** - Test organization unclear

### Low Priority (Nice to Have)

7. **frontend/docs/authentication.md** - Frontend auth pattern undocumented
8. **frontend/docs/ops-console.md** - Ops Console features undocumented

---

## Summary

**8 missing documentation files identified**:
- 3 High priority (deploy blockers)
- 3 Medium priority (Phase 1 completion)
- 2 Low priority (nice to have)

**Next Steps**:
1. Create high-priority docs first (ops/feature-flags.md, database/exclusion-constraints.md, architecture/module-system.md)
2. Create medium-priority docs (architecture/channel-manager.md, database/migrations-guide.md, testing/README.md)
3. Create low-priority docs (frontend docs)

---

**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd
**Source**: status-review-v3 code analysis
