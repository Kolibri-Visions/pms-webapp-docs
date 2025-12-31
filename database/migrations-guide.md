# Database Migrations Guide

**Purpose**: Document migration workflow, naming conventions, and best practices

**Audience**: Backend developers

**Source of Truth**: `supabase/migrations/` directory, Supabase CLI documentation

---

## Overview

Database migrations are managed using **Supabase migrations** (SQL files, versioned by timestamp).

**Migration Location**: `supabase/migrations/`

**Naming Convention**: `YYYYMMDDHHMMSS_description.sql`

**Example**: `20251225190000_availability_inventory_system.sql`

---

## How to List Migrations

**Check current migrations**:
```bash
# List all migration files
ls -1 supabase/migrations/

# Count total migrations
ls -1 supabase/migrations/*.sql | wc -l
```

**Historical context**: As of [status-review-v3 snapshot](_staging/status-review-v3/PROJECT_STATUS.md), 16 migrations were applied. Check the directory for the current count.

**Key migrations** (examples):
- `20250101000001_initial_schema.sql` - Core tables (agencies, properties, bookings, guests)
- `20250101000004_rls_policies.sql` - Row-Level Security policies
- `20251229200517_enforce_overlap_prevention_via_exclusion.sql` - EXCLUSION constraint for double-booking prevention

---

## Creating a New Migration

### Step 1: Generate Timestamp

```bash
# Generate UTC timestamp for migration filename
date -u +"%Y%m%d%H%M%S"

# Example output: 20251230210000
```

### Step 2: Create Migration File

```bash
# Create file with timestamp + description
cd supabase/migrations/
touch 20251230210000_add_reviews_table.sql
```

### Step 3: Write SQL

**Best Practices**:
- Use idempotent operations (`IF NOT EXISTS`, `IF EXISTS`)
- One logical change per migration (e.g., one table, one constraint)
- Include comments explaining why (not just what)
- Test migration locally before deploying

**Example**:
```sql
-- Add reviews table for property reviews
-- Purpose: Support guest reviews feature (Phase XX)

CREATE TABLE IF NOT EXISTS public.reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    booking_id UUID REFERENCES bookings(id) ON DELETE SET NULL,
    guest_id UUID NOT NULL REFERENCES guests(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add index for efficient property review lookups
CREATE INDEX IF NOT EXISTS idx_reviews_property_id ON reviews(property_id);
```

---

## Migration Types

### 1. Schema Migrations (DDL)

**Examples**:
- `CREATE TABLE`, `ALTER TABLE`
- `ADD COLUMN`, `DROP COLUMN`
- `CREATE TYPE`, `ALTER TYPE`

**Use Case**: Change database structure

---

### 2. Index Migrations

**Examples**:
- `CREATE INDEX`, `DROP INDEX`
- `CREATE UNIQUE INDEX`

**Use Case**: Improve query performance

**File**: `20250101000003_indexes.sql` (example)

---

### 3. RLS Policy Migrations

**Examples**:
- `CREATE POLICY`, `ALTER POLICY`, `DROP POLICY`
- `ENABLE ROW LEVEL SECURITY`

**Use Case**: Multi-tenancy isolation, access control

**File**: `20250101000004_rls_policies.sql` (example)

---

### 4. Constraint Migrations

**Examples**:
- `ADD CONSTRAINT` (FOREIGN KEY, UNIQUE, CHECK, EXCLUSION)
- `DROP CONSTRAINT`

**Use Case**: Data integrity enforcement

**File**: `20251229200517_enforce_overlap_prevention_via_exclusion.sql` (EXCLUSION constraint example)

**Related Docs**: [EXCLUSION Constraints](exclusion-constraints.md)

---

### 5. Data Migrations (DML)

**Examples**:
- `INSERT`, `UPDATE`, `DELETE`
- Data backfills, cleanup scripts

**Use Case**: One-time data changes (rare, use with caution)

**Warning**: Data migrations can be destructive. Always backup before deploying.

---

## Deploying Migrations

### Local Development

**Option A: Supabase CLI** (recommended):
```bash
# Start local Supabase (applies migrations automatically)
supabase start

# Or manually apply migrations
supabase db push
```

**Option B: Manual SQL**:
```bash
# Apply migration manually (not recommended)
psql $DATABASE_URL -f supabase/migrations/20251230210000_add_reviews_table.sql
```

---

### Production / Staging

**Method**: Supabase Dashboard OR Supabase CLI

**Supabase CLI** (recommended):
```bash
# Link to remote project
supabase link --project-ref YOUR_PROJECT_REF

# Push migrations to remote
supabase db push
```

**Supabase Dashboard**:
1. Navigate to Supabase project dashboard
2. Go to "SQL Editor"
3. Paste migration SQL
4. Execute

**Caution**: Always test migrations in staging before production

---

## Checking for Schema Drift

**Schema drift**: Deployed database schema doesn't match migration files

### Detect Drift

```bash
# Check current database schema against migrations
supabase db diff

# If drift detected, review differences before creating migration
```

**Production drift detection**: See [Runbook - Schema Drift](../ops/runbook.md#schema-drift) for troubleshooting steps when API returns "Schema not installed/out of date" errors.

### Resolve Drift

**Option A: Create migration from drift**:
```bash
# Generate migration from current schema
supabase db diff | tee supabase/migrations/$(date -u +"%Y%m%d%H%M%S")_fix_drift.sql
```

**Option B: Reset database** (LOCAL ONLY, destroys data):
```bash
# Reset local database to match migrations (destructive)
supabase db reset
```

**Related Docs**: [Runbook - Schema Drift](../ops/runbook.md#schema-drift)

---

## Schema Drift SOP

**Purpose**: Step-by-step procedure to detect, diagnose, and fix schema drift in production.

**When to Use**: API returns 503 with "Database schema not installed or out of date" or `UndefinedTable`/`UndefinedColumn` errors.

**Source of Truth**: Migration files in `supabase/migrations/` directory (in repo).

---

### Step 1: Detect Drift (Symptoms)

**Symptoms:**
```
GET /api/v1/properties → 503 {"detail":"Database schema not installed or out of date..."}
asyncpg.exceptions.UndefinedTableError: relation "properties" does not exist
asyncpg.exceptions.UndefinedColumnError: column "agency_id" does not exist
```

**Quick Check:**

WHERE: HOST-SERVER-TERMINAL
```bash
# Test endpoint
curl https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Authorization: Bearer $TOKEN"

# If 503: schema drift likely
```

WHERE: Supabase SQL Editor
```sql
-- Check if key tables exist
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('agencies', 'properties', 'bookings', 'inventory_ranges')
ORDER BY tablename;

-- Expected: All 4 tables present
-- If missing: schema drift confirmed
```

---

### Step 2: Identify Missing Tables/Columns

**Check what exists in database:**

WHERE: Supabase SQL Editor
```sql
-- List all public tables
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

**Check specific table columns:**

WHERE: Supabase SQL Editor
```sql
-- Replace 'properties' with table name from error
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'properties'
ORDER BY ordinal_position;

-- Verify key columns: id, agency_id, name, created_at, updated_at
```

---

### Step 3: List Migration Files (Source of Truth)

**Find migration files in repo:**

WHERE: HOST-SERVER-TERMINAL
```bash
# List all migrations
ls -1 supabase/migrations/*.sql

# See latest 5 migrations
ls -1 supabase/migrations/*.sql | tail -5

# Count total
ls -1 supabase/migrations/*.sql | wc -l
```

**Identify which migrations are missing:**
- Compare database tables vs migration file names
- Look for migration files with table names that don't exist in database

---

### Step 4: Apply Missing Migrations

**Locate migration file:**

WHERE: HOST-SERVER-TERMINAL
```bash
# Example: Find migration that creates 'properties' table
grep -l "CREATE TABLE.*properties" supabase/migrations/*.sql

# View migration content
cat supabase/migrations/20250101000001_initial_schema.sql
```

**Apply migration:**

WHERE: Supabase SQL Editor
```sql
-- Copy/paste SQL from migration file
-- Execute in SQL Editor

-- Example (from 20250101000001_initial_schema.sql):
CREATE TABLE IF NOT EXISTS public.agencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ... (continue with rest of migration)
```

**For safe idempotent DDL:**

WHERE: Supabase SQL Editor
```sql
-- Use DO $$ blocks for complex DDL
DO $$
BEGIN
  -- Check if table exists
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'properties'
  ) THEN
    CREATE TABLE public.properties (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      agency_id UUID NOT NULL,
      name TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  END IF;

  -- Check if column exists
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'properties'
      AND column_name = 'updated_at'
  ) THEN
    ALTER TABLE public.properties
    ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
  END IF;
END $$;
```

**Apply migrations in order:**
- Start with earliest timestamp (oldest first)
- Apply one migration at a time
- Check for errors before continuing

---

### Step 5: Verify Schema Fix

**Checklist:**

WHERE: Supabase SQL Editor
```sql
-- 1. Verify tables exist
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
-- Expected: agencies, properties, bookings, inventory_ranges, guests, team_members

-- 2. Verify key columns in properties table
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'properties'
ORDER BY ordinal_position;
-- Expected: id, agency_id, name, address, created_at, updated_at

-- 3. Run sample query
SELECT p.id, p.name, p.agency_id
FROM properties p
LIMIT 1;
-- Should return data (or empty if no data), NOT an error
```

WHERE: HOST-SERVER-TERMINAL
```bash
# 1. Test health endpoint
curl https://api.fewo.kolibri-visions.de/health/ready
# Expected: {"status":"healthy","db":"up"}

# 2. Test properties endpoint
curl https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 with JSON array (not 503)

# 3. Test booking creation (if applicable)
curl -X POST https://api.fewo.kolibri-visions.de/api/v1/bookings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"property_id":"...","check_in":"2025-07-01","check_out":"2025-07-05"}'
# Expected: 201 Created (not 503)
```

---

### Step 6: Document in Repo (Prevent Recurrence)

**If migrations were applied manually:**

WHERE: HOST-SERVER-TERMINAL
```bash
# Create a note in repo
cat > docs/ops/MANUAL_MIGRATION_LOG.md << EOF
# Manual Migration Log

## $(date -u +"%Y-%m-%d %H:%M UTC")

**Applied Migrations:**
- 20250101000001_initial_schema.sql
- 20250101000002_add_bookings.sql

**Reason:** Schema drift detected, migrations not applied during deployment

**Applied By:** [Your Name]

**Verification:** All endpoints return 200, health checks pass
EOF
```

**Update deployment process:**
- Ensure migrations are applied before deploying code changes
- Add migration check to CI/CD (if applicable)
- Document migration workflow in deployment runbook

---

### Common Patterns for Safe DDL

**Pattern 1: Idempotent CREATE TABLE**

```sql
CREATE TABLE IF NOT EXISTS public.table_name (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- ...
);
```

**Pattern 2: Idempotent ADD COLUMN**

```sql
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'properties'
      AND column_name = 'new_column'
  ) THEN
    ALTER TABLE public.properties
    ADD COLUMN new_column TEXT;
  END IF;
END $$;
```

**Pattern 3: Idempotent CREATE INDEX**

```sql
CREATE INDEX IF NOT EXISTS idx_name ON table_name(column_name);
```

**Pattern 4: Idempotent CREATE CONSTRAINT**

```sql
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema = 'public'
      AND table_name = 'properties'
      AND constraint_name = 'fk_agency'
  ) THEN
    ALTER TABLE public.properties
    ADD CONSTRAINT fk_agency
    FOREIGN KEY (agency_id) REFERENCES agencies(id) ON DELETE CASCADE;
  END IF;
END $$;
```

---

### Troubleshooting

**Migration fails with "relation already exists":**
- Migration not idempotent (missing `IF NOT EXISTS`)
- Wrap in DO $$ block or add IF NOT EXISTS

**Migration fails with "permission denied":**
- Execute as `postgres` user in Supabase SQL Editor
- Check RLS policies aren't blocking DDL

**Migration partially applied:**
- Check for syntax errors in migration file
- Apply remaining DDL statements individually
- Verify each step before continuing

**Foreign key constraint fails:**
- Ensure referenced table exists first
- Apply migrations in dependency order (parent tables before child tables)

---

### Related Documentation

- [Runbook - Schema Drift](../ops/runbook.md#schema-drift) - Quick troubleshooting guide
- [Runbook - Top 5 Failure Modes](../ops/runbook.md#top-5-failure-modes-and-fixes) - Schema drift failure mode
- [Data Integrity](data-integrity.md) - Constraints, validation rules
- [EXCLUSION Constraints](exclusion-constraints.md) - Advanced constraint patterns

---

## Best Practices

### DO:
- ✅ Use idempotent operations (`IF NOT EXISTS`, `IF EXISTS`)
- ✅ One logical change per migration
- ✅ Test migrations locally before deploying
- ✅ Add comments explaining why (not just what)
- ✅ Backup production database before destructive migrations

### DON'T:
- ❌ Edit existing migration files after deployment (create new migration instead)
- ❌ Delete migration files (breaks migration history)
- ❌ Mix schema and data changes in one migration (prefer separate migrations)
- ❌ Skip testing migrations (always test locally first)

---

## Rollback Strategy

**Supabase migrations are forward-only** (no automatic rollback).

**If migration fails**:
1. **Fix forward**: Create new migration to fix the issue
2. **Manual rollback**: Write reverse SQL (e.g., `DROP TABLE`, `DROP COLUMN`) in new migration

**Example Rollback Migration**:
```sql
-- Rollback: Remove reviews table
-- Reason: Migration 20251230210000_add_reviews_table.sql failed validation

DROP TABLE IF EXISTS public.reviews CASCADE;
```

**Warning**: Rollbacks can be destructive. Always backup before rolling back.

---

## Troubleshooting

### Migration Fails to Apply

**Symptom**: `supabase db push` fails with SQL error

**Common Causes**:
- Syntax error in SQL
- Constraint violation (e.g., foreign key references non-existent table)
- RLS policy conflict

**Fix**:
1. Review error message
2. Fix SQL in migration file
3. Reapply migration

---

### Schema Drift Detected

**Symptom**: `supabase db diff` shows differences between deployed schema and migrations

**Cause**: Manual schema changes made outside of migrations

**Fix**: See [Checking for Schema Drift](#checking-for-schema-drift)

**Related Docs**: [Runbook - Schema Drift](../ops/runbook.md#schema-drift)

---

## Related Documentation

- [EXCLUSION Constraints](exclusion-constraints.md) - EXCLUSION constraint pattern (double-booking prevention)
- [Data Integrity](data-integrity.md) - Constraints, validation rules
- [Index Strategy](index-strategy.md) - Query optimization, indexing
- [Runbook - Schema Drift](../ops/runbook.md#schema-drift) - Troubleshooting schema drift

---

**Last Updated**: 2025-12-30
**Maintained By**: Backend Team
