# Database Operations

This chapter covers database connectivity, migrations, backups, and troubleshooting.

## Overview

The PMS system uses Supabase (PostgreSQL) with Row-Level Security (RLS) for multi-tenancy. The database connection pool is managed by asyncpg.

## Key Concepts

- **Connection Pool**: Managed by asyncpg, auto-reconnects on failure
- **RLS Policies**: Enforce tenant isolation at the database level
- **Migrations**: Managed via Supabase migrations in `supabase/migrations/`

## Common Operations

### Check Database Connectivity

```bash
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq '.database'
```

### Run Migrations

```bash
cd supabase
supabase db push
```

## Troubleshooting

See main runbook sections:
- Pool connection errors
- RLS policy issues
- Migration failures

---

*For detailed procedures, see the legacy runbook.md.*
