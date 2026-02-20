# PMS Operations Runbook

**Purpose**: Practical troubleshooting guide for common production issues.

**Audience**: Ops engineers, DevOps, on-call responders.

**Last Updated**: 2026-01-28

---

## RUNBOOK INDEX

> **RULE**: New content goes into `backend/docs/ops/runbook/*.md` chapter files only.
> This legacy file is kept for reference but should not grow further.

### Modular Chapters (New Content Here)

| Chapter | Description |
|---------|-------------|
| [00-golden-paths.md](./runbook/00-golden-paths.md) | Quick-reference happy-path procedures |
| [01-deployment.md](./runbook/01-deployment.md) | Deployment, rollback, environments |
| [02-database.md](./runbook/02-database.md) | Database connectivity, migrations |
| [03-auth.md](./runbook/03-auth.md) | Authentication, authorization, JWT |
| [04-channel-manager.md](./runbook/04-channel-manager.md) | Channel integrations, sync ops |
| [05-direct-booking-hardening.md](./runbook/05-direct-booking-hardening.md) | CORS, Host allowlist, tenant resolution |
| [10-amenities-admin-ui.md](./runbook/10-amenities-admin-ui.md) | Amenities CRUD, icons, public filter RLS |
| [16-extra-services.md](./runbook/16-extra-services.md) | Extra services billing units, per_unit_night |
| [28-property-edit-extended-fields.md](./runbook/28-property-edit-extended-fields.md) | Property edit modal extended fields |
| [29-public-website-visibility.md](./runbook/29-public-website-visibility.md) | Public website is_active filtering |
| [31-kurtaxen-visitor-tax.md](./runbook/31-kurtaxen-visitor-tax.md) | Kurtaxen (Visitor Tax) Management |

### Golden Paths (Most Common Operations)

1. **Deploy** → Merge to main → Coolify auto-deploys → Run `pms_verify_deploy.sh`
2. **Rollback** → Coolify → Select previous → Click Rollback
3. **Health Check** → `curl /health` + `curl /health/ready`
4. **Smoke Test** → Export env vars → Run `pms_verify_deploy.sh`

---

## Quick Reference

| Issue | Symptom | Section |
|-------|---------|---------|
| API returns 503 after deploy | "Service degraded" or "Database unavailable" | [DB DNS / Degraded Mode](#db-dns--degraded-mode) |
| JWT auth fails | 401 Unauthorized despite valid token | [Token Validation](#token-validation-apikey-header) |
| API returns 503 with schema error | "Schema not installed/out of date" | [Schema Drift](#schema-drift) |
| Booking detail returns 500 | ResponseValidationError on status field | [Booking Status Validation](#booking-status-validation-error-500) |
| Website pages returns 500 | "blocks Input should be a valid list" | [Website Pages Blocks 500](./runbook/25-website-pages-blocks-500.md) |
| Public site API returns 404 | /unterkuenfte shows 404, API not proxied | [Public API Proxy](./runbook/26-public-api-proxy.md) |
| Public page cached as 404 | /unterkuenfte shows "not found", x-nextjs-cache: HIT | [Cached 404 Fix](./runbook/27-public-unterkuenfte-next-cache-404.md) |
| Smoke script fails | Empty TOKEN/PID, bash errors | [Smoke Script Pitfalls](#smoke-script-pitfalls) |
| Amenities filter empty | /unterkuenfte filter shows no amenities | [Amenities RLS](./runbook/10-amenities-admin-ui.md#public-amenities-filter-rls) |
| Extra service billing error | per_unit_night not saving | [Extra Services Migration](./runbook/16-extra-services.md#migration-per_unit_night-2026-02-15) |
| Property not on public site | Active property missing from /unterkuenfte | [Public Visibility](./runbook/29-public-website-visibility.md) |

---

## Daily Ops Checklist (5–10 minutes)

**Purpose**: Quick daily health check for production PMS system. Catches common issues before they escalate.

**When to Run**: Start of shift, after deployments, or when investigating user reports.

---

### Step 1: Verify Containers + Deployed Commit

**WHERE:** HOST-SERVER-TERMINAL

```bash
# Check all PMS containers are running
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | grep -E 'pms-backend|pms-admin|pms-worker'

# Expected output:
# pms-backend       Up X hours   ghcr.io/.../pms-backend:main
# pms-admin         Up X hours   ghcr.io/.../pms-admin:main
# pms-worker-v2     Up X hours   ghcr.io/.../pms-worker-v2:main

# Verify deployed commit matches latest main
docker exec pms-backend env | grep SOURCE_COMMIT
# Cross-check with: git log -1 --oneline (on your local main branch)
```

**Red Flags:**
- Any container missing or in "Restarting" status
- pms-worker (old) still running alongside pms-worker-v2
- SOURCE_COMMIT doesn't match expected deploy

---

### Step 2: Health Checks

**WHERE:** HOST-SERVER-TERMINAL

```bash
# Quick HEAD checks (status-only, no body)
curl -I https://api.fewo.kolibri-visions.de/health
# Expected: HTTP/2 200

curl -I https://api.fewo.kolibri-visions.de/health/ready
# Expected: HTTP/2 200

# Full readiness check (JSON body for component details)
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq .
```

**Expected Response:**
```json
{
  "status": "up",
  "components": {
    "db": {"status": "up"},
    "redis": {"status": "up"},
    "celery": {
      "status": "up",
      "details": {"workers": ["celery@pms-worker-v2-..."]}
    }
  },
  "checked_at": "2026-01-01T12:00:00Z"
}
```

**Red Flags:**
- `/health/ready` returns 503
- `db: "down"` → Check [DB DNS / Degraded Mode](#db-dns--degraded-mode)
- `redis: "down"` → Verify Redis container running
- `celery: "down"` → Check worker status (see Step 3)

---

### Step 3: Worker Singleton Enforcement

**WHERE:** HOST-SERVER-TERMINAL

```bash
# Verify exactly ONE Celery worker is running
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep pms-worker

# Expected: Only pms-worker-v2 listed (NOT pms-worker)

# Cross-check with health endpoint
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq '.components.celery'
```

**Expected Health Response:**
```json
{
  "status": "up",
  "details": {
    "workers": ["celery@pms-worker-v2-abc123"]
  }
}
```

**Red Flags:**
- Multiple workers detected (e.g., pms-worker AND pms-worker-v2)
- Health check shows `celery: "down"` with error: "Expected exactly 1 worker, found 2"

**Fix (if multiple workers found):**
```bash
# Stop old worker (HOST-SERVER-TERMINAL)
docker stop pms-worker  # or whichever is the old container

# Verify only one remains
docker ps | grep pms-worker
# Should only show pms-worker-v2

# Verify health check passes
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq '.components.celery.status'
# Expected: "up"
```

**Why This Matters:**
- Multiple workers cause duplicate sync tasks (same operation executed 2-3x)
- Race conditions when updating sync log status
- Inconsistent batch status in Admin UI

See [Single-Worker Enforcement](#get-healthready) for automatic detection details.

---

### Step 4: Channel Manager Sanity Check

**WHERE:** Browser (Admin UI) + HOST-SERVER-TERMINAL (optional curl)

**Admin UI (Quick Visual Check):**

1. Navigate to: `https://admin.fewo.kolibri-visions.de/connections`
2. Click any connection to view details
3. Check **Sync History** section:
   - Recent batches should show within last 24h
   - Filter by "Failed" status → Expect 0 or minimal failed batches
   - If many failures: investigate sync logs for error patterns

**Optional: curl API Check (HOST-SERVER-TERMINAL):**

```bash
# Get admin token (if not cached)
TOKEN=$(curl -sX POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access_token')

# List recent sync batches for a connection
CID="your-connection-uuid-here"
curl -s "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync-batches?limit=10&status=any" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.items[] | {batch_id, batch_status, created_at_min}'

# Get batch detail for failed batch (if any)
BATCH_ID="batch-uuid-from-above"
curl -s "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync-batches/$BATCH_ID" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '{batch_status, status_counts, operations: .operations[] | {operation_type, status}}'
```

**Red Flags:**
- High failed batch rate (>10% in last 24h)
- All batches stuck in "running" status (worker may be down)
- Recent batches show `status_counts.other > 0` (unexpected status values)

---

### Step 5: Quick Issue Triage (If Red Flags Found)

**DB Degraded Mode:**

```bash
# WHERE: HOST-SERVER-TERMINAL
# Check DNS resolution
docker exec pms-backend getent hosts supabase-db
# Empty output = DNS failure → See [DB DNS / Degraded Mode](#db-dns--degraded-mode)

# Check network attachment
docker inspect pms-backend | jq '.[0].NetworkSettings.Networks | keys'
# Must include: "bccg4gs4o4kgsowocw08wkw4" (Supabase network)
```

**Redis/Celery Issues:**

```bash
# WHERE: HOST-SERVER-TERMINAL
# Check Redis container
docker ps | grep redis
# Expected: supabase-redis running

# Check worker logs for errors
docker logs pms-worker-v2 --tail 50
# Look for: connection errors, task failures, retry exhaustion
```

**Where to Look:**
- Backend logs: `docker logs pms-backend --tail 100`
- Worker logs: `docker logs pms-worker-v2 --tail 100`
- Admin logs: `docker logs pms-admin --tail 50`
- Health endpoint: `/health/ready` component details

---

### Step 6: Retention Reminder (Weekly/Monthly)

**WHERE:** Supabase SQL Editor (Dashboard → SQL Editor → New Query)

```sql
-- Quick check: row count and date range
SELECT COUNT(*) AS total_logs,
       MIN(created_at) AS oldest_log,
       MAX(created_at) AS newest_log,
       COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '90 days') AS logs_older_than_90d
FROM public.channel_sync_logs;

-- If logs_older_than_90d > 0, consider cleanup
-- See [Channel Manager — Sync Log Retention & Cleanup](#channel-manager--sync-log-retention--cleanup)
```

**Retention Guidelines:**
- Test/Staging: 90 days
- Production: 180-365 days (depending on compliance)

**Cleanup (when needed):**
```sql
-- Preview deletion count first (dry-run)
SELECT COUNT(*) AS logs_to_delete
FROM public.channel_sync_logs
WHERE created_at < NOW() - INTERVAL '90 days';

-- Execute cleanup (after verifying count above)
DELETE FROM public.channel_sync_logs
WHERE created_at < NOW() - INTERVAL '90 days';
```

See [Channel Manager — Sync Log Retention & Cleanup](#channel-manager--sync-log-retention--cleanup) for full cleanup procedures and safety notes.

**Monthly Code Quality Check:**

Run regression guard to verify no browser popups (alert/confirm/prompt) were reintroduced:

```bash
# WHERE: LOCAL-DEV-TERMINAL (in repo root)
bash frontend/scripts/check_no_browser_popups.sh
```

**Expected Output:**
```
✅ OK: No browser popups (alert/confirm/prompt) found in frontend/
```

If popups detected, see [Regression Guard](#regression-guard) section for remediation steps.

---

**Checklist Complete** ✅

- If all green: System healthy, no action needed
- If red flags found: Investigate using sections linked above
- Document any issues/fixes in ops log for trending analysis

**Related:**
- [Quick Smoke (5 minutes)](../scripts/README.md#quick-smoke-5-minutes) - Automated smoke test script
- [Health Monitoring (HEAD vs GET)](#head-vs-get-for-health-monitoring) - Detailed health check guide
- [Top 5 Failure Modes](#top-5-failure-modes-and-fixes) - Common production issues and fixes

---

## Top 5 Failure Modes (and Fixes)

**Quick Reference** — For detailed steps, see [99-legacy.md](./runbook/99-legacy.md#top-5-failure-modes-and-fixes).

| # | Issue | Quick Fix |
|---|-------|-----------|
| 1 | DB DNS / Network Disconnect | `docker network connect bccg4gs4o4kgsowocw08wkw4 pms-backend` |
| 2 | ImportError at Startup | Check logs: `docker logs pms-backend --tail 50` |
| 3 | JWT 401 Despite Valid Token | Add `apikey` header alongside Bearer token |
| 4 | Schema Drift (503) | Run migrations: `bash backend/scripts/ops/apply_supabase_migrations.sh` |
| 5 | Smoke Script Variable Errors | Use `-s` flag for curl, check env vars |

---

## Legacy Section Stubs

> The following headings maintain backward compatibility with existing anchor links.
> Each links to the appropriate chapter file or the legacy archive.

---

## DB DNS / Degraded Mode

**Moved to:** [02-database.md → DB DNS / Degraded Mode](./runbook/02-database.md#db-dns--degraded-mode)

---

## Schema Drift

**Moved to:** [02-database.md → Schema Drift](./runbook/02-database.md#schema-drift)

---

## DB Migrations (Production)

**Moved to:** [02-database.md → DB Migrations](./runbook/02-database.md#db-migrations-production)

---

## Data Hygiene

**Moved to:** [02-database.md → Data Hygiene](./runbook/02-database.md#data-hygiene)

---

## Token Validation (apikey Header)

**Moved to:** [03-auth.md → Token Validation](./runbook/03-auth.md#token-validation-apikey-header)

---

## Fresh JWT (Supabase)

**Moved to:** [03-auth.md → Fresh JWT](./runbook/03-auth.md#fresh-jwt-supabase)

---

## CORS Errors (Admin Console Blocked)

**Moved to:** [03-auth.md → CORS Errors](./runbook/03-auth.md#cors-errors)

---

## Deploy Gating (Docs-Only Change Detection)

**Moved to:** [01-deployment.md → Deploy Gating](./runbook/01-deployment.md#deploy-gating-docs-only-change-detection)

---

## Deployment Process

**Moved to:** [01-deployment.md → Deployment Process](./runbook/01-deployment.md#deployment-process)

---

## Redis + Celery Worker Setup (Channel Manager)

**Moved to:** [04-channel-manager.md → Redis + Celery Worker Setup](./runbook/04-channel-manager.md#redis--celery-worker-setup-channel-manager)

---

## Celery Worker (pms-worker-v2)

**Moved to:** [04-channel-manager.md → Celery Worker](./runbook/04-channel-manager.md#celery-worker-pms-worker-v2)

---

## Channel Manager Error Handling & Retry Logic

**Moved to:** [04-channel-manager.md → Error Handling](./runbook/04-channel-manager.md#channel-manager-error-handling--retry-logic)

---

## Smoke Script Pitfalls

**Moved to:** [99-legacy.md → Smoke Script Pitfalls](./runbook/99-legacy.md#smoke-script-pitfalls)

---

## Booking Status Validation Error (500)

**Moved to:** [99-legacy.md → Booking Status Validation](./runbook/99-legacy.md#booking-status-validation-error-500)

---

## Network Attachment at Create-Time (Docker)

**Moved to:** [99-legacy.md → Network Attachment](./runbook/99-legacy.md#network-attachment-at-create-time-docker)

---

## Additional Legacy Content

For all other historical sections, see [99-legacy.md](./runbook/99-legacy.md).

This includes: Phase-specific documentation, Channel Manager operations, Admin UI verification, and archived troubleshooting procedures.
