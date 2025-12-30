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
