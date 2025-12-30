# Database Migrations Runbook

## Overview

This document describes how to manage database migrations for the PMS-Webapp project deployed on Coolify with Supabase (self-hosted PostgreSQL).

**Migration System:** Plain SQL migrations in `supabase/migrations/`

**Goal:** Never manually "add columns" in production. Use versioned migrations as Single Source of Truth.

---

## Table of Contents

- [Migration File Structure](#migration-file-structure)
- [How to Run Migrations](#how-to-run-migrations)
- [Migration Best Practices](#migration-best-practices)
- [Troubleshooting](#troubleshooting)
- [Common Operations](#common-operations)

---

## Migration File Structure

### Location

```
supabase/migrations/
├── 20250101000001_initial_schema.sql
├── 20250101000002_channels_and_financials.sql
├── 20250101000003_indexes.sql
├── 20250101000004_rls_policies.sql
└── 20250125000001_fix_properties_location_geometry.sql
```

### Naming Convention

```
YYYYMMDDHHMMSS_descriptive_name.sql
```

- **Timestamp:** Ensures chronological ordering
- **Descriptive name:** Brief description of changes (snake_case)

### Migration File Template

```sql
-- ============================================================================
-- Migration: [Brief Description]
-- ============================================================================
-- Created: YYYY-MM-DD
-- Description: [Detailed description of what this migration does]
--
-- Background: [Why this migration is needed]
--
-- Safety: [How this migration ensures data safety]
-- ============================================================================

-- Your SQL here

-- ============================================================================
-- End Migration
-- ============================================================================
```

---

## How to Run Migrations

### Option 1: Via Supabase SQL Editor (Recommended for Production)

**Where:** Supabase Dashboard → SQL Editor

**Steps:**

1. Navigate to your Supabase project dashboard
2. Go to **SQL Editor**
3. Create a new query
4. Copy the migration SQL file content
5. Execute the query
6. Verify the output (look for NOTICE/RAISE messages)

**Pros:**
- Direct access to production database
- No SSH/container access needed
- Visual feedback in UI

**Cons:**
- Manual process (must copy-paste each migration)
- No automatic tracking of which migrations have been run

---

### Option 2: Via Coolify Terminal (Backend Container)

**Where:** Coolify Dashboard → Your PMS-Webapp Service → Terminal

**Steps:**

1. Open Coolify dashboard
2. Navigate to your backend service
3. Click **Terminal** button
4. Run migrations using `psql`:

```bash
# Connect to Supabase database
psql "${DATABASE_URL}" -f /path/to/migration.sql

# Or using inline SQL
psql "${DATABASE_URL}" <<'EOF'
-- Your migration SQL here
EOF
```

**Example:**

```bash
# From backend container
cd /app/supabase/migrations
psql "${DATABASE_URL}" -f 20250125000001_fix_properties_location_geometry.sql
```

**Pros:**
- Scriptable
- Can run multiple migrations in sequence
- Environment variables automatically loaded

**Cons:**
- Requires container access
- Must ensure migration files are available in container

---

### Option 3: Via Supabase DB Container (Direct PostgreSQL)

**Where:** Coolify → Supabase-DB Service → Terminal

**Steps:**

1. Open Coolify dashboard
2. Navigate to your `supabase-db` service
3. Click **Terminal** button
4. Connect as postgres user:

```bash
# Inside supabase-db container
psql -U postgres -d postgres -f /path/to/migration.sql
```

**Pros:**
- Direct database access
- No network overhead

**Cons:**
- Migration files must be copied into container first
- More complex setup

---

### Option 4: Via Host Server SSH

**Where:** SSH into your Coolify host server

**Steps:**

```bash
# SSH into host
ssh user@your-coolify-server

# Option A: Execute via psql remotely
psql "postgresql://postgres:PASSWORD@supabase-db:5432/postgres" \
    -f supabase/migrations/20250125000001_fix_properties_location_geometry.sql

# Option B: Docker exec into supabase-db container
docker exec -i supabase-db psql -U postgres -d postgres < migration.sql
```

**Pros:**
- Full control
- Can script deployment pipelines

**Cons:**
- Requires SSH access to host
- Must manage PostgreSQL connection details

---

## Migration Best Practices

### 1. **Always Use Idempotent SQL**

✅ **Good:**
```sql
CREATE TABLE IF NOT EXISTS properties (...);
CREATE INDEX IF NOT EXISTS idx_properties_agency ON properties(agency_id);
```

❌ **Bad:**
```sql
CREATE TABLE properties (...);  -- Fails if table exists
```

### 2. **Use DO Blocks for Conditional Logic**

```sql
DO $$
BEGIN
    -- Check if column exists before adding
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'properties' AND column_name = 'owner_id'
    ) THEN
        ALTER TABLE properties ADD COLUMN owner_id UUID;
    END IF;
END $$;
```

### 3. **Add Constraints Safely**

```sql
-- Check if constraint already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_properties_agency'
    ) THEN
        ALTER TABLE properties
            ADD CONSTRAINT fk_properties_agency
            FOREIGN KEY (agency_id) REFERENCES agencies(id);
    END IF;
END $$;
```

### 4. **Verify Data Before Destructive Changes**

```sql
DO $$
DECLARE
    row_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO row_count FROM properties WHERE location IS NOT NULL;

    IF row_count > 0 THEN
        RAISE EXCEPTION 'Cannot drop column: % rows have non-NULL values', row_count;
    END IF;

    -- Safe to drop
    ALTER TABLE properties DROP COLUMN location;
END $$;
```

### 5. **Use RAISE NOTICE for Progress Logging**

```sql
DO $$
BEGIN
    RAISE NOTICE 'Starting migration...';

    -- Migration steps
    CREATE TABLE IF NOT EXISTS properties (...);
    RAISE NOTICE 'Created properties table';

    CREATE INDEX IF NOT EXISTS idx_properties_agency ON properties(agency_id);
    RAISE NOTICE 'Created index on agency_id';

    RAISE NOTICE '✅ Migration completed successfully';
END $$;
```

### 6. **Never Leak Credentials**

❌ **Bad:**
```sql
-- Don't include DSN/passwords in migrations
CREATE USER myuser WITH PASSWORD 'hardcoded_password';
```

✅ **Good:**
```sql
-- Use environment variables or separate secret management
-- Document required permissions in migration comments
```

---

## Troubleshooting

### Error: "permission denied to create extension"

**Cause:** User doesn't have SUPERUSER privileges

**Solution:**

```sql
-- Connect as superuser (postgres)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**In Supabase:** Use SQL Editor (runs as superuser by default)

---

### Error: "relation already exists"

**Cause:** Migration was run twice, or table already exists

**Solution:**

```sql
-- Use IF NOT EXISTS
CREATE TABLE IF NOT EXISTS properties (...);

-- Or check before creating
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'properties') THEN
        CREATE TABLE properties (...);
    END IF;
END $$;
```

---

### Error: "column does not exist" in SELECT queries

**Cause:** Migration hasn't been run yet, or schema drift

**Solution:**

1. Check which migrations have been run:
   ```sql
   SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
   SELECT column_name FROM information_schema.columns WHERE table_name = 'properties';
   ```

2. Run missing migrations in chronological order

---

### Error: "type geography does not exist"

**Cause:** PostGIS extension not enabled

**Solution:**

```sql
-- Run as superuser
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify
SELECT postgis_version();
```

---

### Error: "cannot drop column location because other objects depend on it"

**Cause:** Index, constraint, or view depends on the column

**Solution:**

```sql
-- Drop dependencies first
DROP INDEX IF EXISTS idx_properties_location;

-- Then drop column
ALTER TABLE properties DROP COLUMN location;

-- Recreate dependencies
CREATE INDEX idx_properties_location ON properties USING GIST(location);
```

---

## Common Operations

### Check Current Schema Version

```sql
-- List all tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- Check column types
SELECT
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_name = 'properties'
ORDER BY ordinal_position;

-- Check indexes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'properties';
```

---

### Verify PostGIS Setup

```sql
-- Check PostGIS version
SELECT postgis_version();

-- Check available extensions
SELECT * FROM pg_available_extensions WHERE name LIKE '%postgis%';

-- Check installed extensions
SELECT * FROM pg_extension;
```

---

### Test ST_X/ST_Y on Geometry

```sql
-- Create test point
SELECT ST_SetSRID(ST_MakePoint(13.4050, 52.5200), 4326)::geometry;

-- Extract coordinates
SELECT
    ST_X(ST_SetSRID(ST_MakePoint(13.4050, 52.5200), 4326)::geometry) as longitude,
    ST_Y(ST_SetSRID(ST_MakePoint(13.4050, 52.5200), 4326)::geometry) as latitude;
```

---

### Rollback a Migration (Manual)

**Note:** SQL migrations don't have automatic rollback. You must write manual rollback SQL.

```sql
-- Example: Rollback adding a column
ALTER TABLE properties DROP COLUMN IF EXISTS new_column;

-- Example: Rollback creating a table
DROP TABLE IF EXISTS new_table CASCADE;

-- Example: Rollback geometry conversion
ALTER TABLE properties DROP COLUMN location;
ALTER TABLE properties ADD COLUMN location geography(Point, 4326);
```

---

## Migration Checklist

Before running a migration in production:

- [ ] Migration is idempotent (uses IF NOT EXISTS, DO blocks)
- [ ] Migration includes safety checks (count rows before DROP)
- [ ] Migration has RAISE NOTICE statements for progress tracking
- [ ] Migration handles missing dependencies gracefully
- [ ] Migration doesn't leak credentials or DSN
- [ ] Migration has been tested on a local/staging database
- [ ] Migration file follows naming convention
- [ ] Migration includes descriptive header comments
- [ ] You have a rollback plan (manual SQL ready)

---

## Next Steps

### Setting Up Automated Migration Tracking

**Option A: Manual Tracking**

Create a `schema_migrations` table:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    description TEXT
);

-- After running each migration
INSERT INTO schema_migrations (version, description)
VALUES ('20250125000001', 'Fix properties.location geometry')
ON CONFLICT (version) DO NOTHING;
```

**Option B: Use Supabase CLI**

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Login
supabase login

# Link to project
supabase link --project-ref YOUR_PROJECT_REF

# Push migrations
supabase db push
```

**Option C: Use Alembic (Future)**

Consider migrating to Alembic for automatic version tracking:

```bash
# Install Alembic
pip install alembic

# Initialize
alembic init alembic

# Generate migration
alembic revision -m "description"

# Run migration
alembic upgrade head
```

---

## Support

**Questions?** Check:
- Supabase Docs: https://supabase.com/docs/guides/database
- PostGIS Docs: https://postgis.net/documentation/
- PostgreSQL Docs: https://www.postgresql.org/docs/

**Issues?** Contact DevOps team or create a GitHub issue.
