# PMS Operations Runbook

**Purpose**: Practical troubleshooting guide for common production issues.

**Audience**: Ops engineers, DevOps, on-call responders.

**Last Updated**: 2025-12-26

---

## Quick Reference

| Issue | Symptom | Section |
|-------|---------|---------|
| API returns 503 after deploy | "Service degraded" or "Database unavailable" | [DB DNS / Degraded Mode](#db-dns--degraded-mode) |
| JWT auth fails | 401 Unauthorized despite valid token | [Token Validation](#token-validation-apikey-header) |
| API returns 503 with schema error | "Schema not installed/out of date" | [Schema Drift](#schema-drift) |
| Booking detail returns 500 | ResponseValidationError on status field | [Booking Status Validation](#booking-status-validation-error-500) |
| Smoke script fails | Empty TOKEN/PID, bash errors | [Smoke Script Pitfalls](#smoke-script-pitfalls) |

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

This section provides quick, actionable fixes for the most common production failures. Each includes symptoms, root cause, fix steps, and verification commands with explicit WHERE labels.

---

### 1. DB DNS / Network Disconnect → Degraded Mode

**Symptoms:**
```
socket.gaierror: [Errno -2] Name or service not known: 'supabase-db'
GET /health/ready → 503 {"status":"unhealthy","db":"down"}
Logs: "Database connection pool creation FAILED"
```

**Root Cause:**
pms-backend or pms-worker-v2 container not attached to Supabase network (`bccg4gs4o4kgsowocw08wkw4`).

**Fix Steps:**

1. Verify DNS resolution fails

WHERE: HOST-SERVER-TERMINAL
```bash
docker exec pms-backend getent hosts supabase-db
# Empty output = DNS failure
```

2. Attach container to Supabase network

WHERE: HOST-SERVER-TERMINAL
```bash
docker network connect bccg4gs4o4kgsowocw08wkw4 pms-backend
docker network connect bccg4gs4o4kgsowocw08wkw4 pms-worker-v2
```

3. Restart containers

WHERE: HOST-SERVER-TERMINAL
```bash
docker restart pms-backend
docker restart pms-worker-v2
```

**Verification:**

WHERE: HOST-SERVER-TERMINAL
```bash
# 1. DNS resolves
docker exec pms-backend getent hosts supabase-db
# Expected: 172.20.0.X supabase-db

# 2. DB connection works
docker exec pms-backend python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://postgres:$PASSWORD@supabase-db:5432/postgres').execute('SELECT 1'))"

# 3. Health endpoint passes
curl https://api.fewo.kolibri-visions.de/health/ready
# Expected: {"status":"healthy","db":"up","redis":"up","celery":"up"}
```

**See Also:** [DB DNS / Degraded Mode](#db-dns--degraded-mode) (detailed section below)

---

### 2. ImportError at Startup → 503 No Available Server

**Symptoms:**
```
Traefik returns: 503 Service Unavailable - "no available server"
Container status: Restarting
Logs: ImportError: cannot import name 'X' from 'app.Y'
Backend never reaches healthy state
```

**Root Cause:**
Python import-time error in application startup, often due to:
- Importing non-existent function/symbol from a module
- Circular import dependency
- Missing dependency (typo in import statement)

**Common Example (Public Booking Router):**
```python
# WRONG - get_db_pool doesn't exist in app.api.deps
from app.api.deps import get_db_pool

# CORRECT - use canonical DB dependency
from app.api.deps import get_db
```

**Fix Steps:**

1. Check container logs for ImportError

WHERE: HOST-SERVER-TERMINAL
```bash
docker logs pms-backend --tail 50 | grep -A 5 "ImportError"
# Look for: "ImportError: cannot import name 'X' from 'Y'"
```

2. Identify the failing import

WHERE: HOST-SERVER-TERMINAL
```bash
# Check which module/file triggered the error
docker logs pms-backend | grep -B 10 "ImportError"
# Note the file path (e.g., /app/app/api/routes/public_booking.py)
```

3. Fix the import (use correct symbol name)

WHERE: YOUR-WORKSTATION
```bash
# Example: Replace invalid get_db_pool with canonical get_db
# Edit backend/app/api/routes/public_booking.py:
# - from app.api.deps import get_db_pool  # REMOVE
# + from app.api.deps import get_db       # ADD
```

4. Commit and redeploy

WHERE: YOUR-WORKSTATION
```bash
git add backend/app/api/routes/public_booking.py
git commit -m "fix: use canonical get_db dependency"
git push origin main
```

**Verification:**

WHERE: HOST-SERVER-TERMINAL
```bash
# 1. Container stays running (not restarting)
docker ps | grep pms-backend
# Expected: "Up X seconds" (not "Restarting")

# 2. Health endpoint responds
curl https://api.fewo.kolibri-visions.de/health
# Expected: 200 OK

# 3. No ImportError in logs
docker logs pms-backend --tail 50 | grep ImportError
# Expected: No output
```

**Prevention:**
- Use canonical dependencies defined in `app/api/deps.py` (__all__ exports)
- Verify imports exist before deploying
- Run `python3 -m py_compile <file>` to catch import errors early

---

### 3. JWT/Auth Failures (401 Invalid Token / 403 Not Authenticated)

**Symptoms:**
```
POST /api/v1/bookings → 401 {"detail":"Invalid authentication token"}
Logs: "JWT token validation failed"
Missing TOKEN env var or TOKEN=""
Wrong JWT_SECRET (token signature verification fails)
Kong /auth/v1/user returns 401 without apikey header
```

**Root Cause:**
- Missing/empty TOKEN environment variable
- JWT_SECRET mismatch between backend and GoTrue
- Missing `apikey` header when calling Kong-protected /auth/v1/user

**Fix Steps:**

1. Fetch valid JWT token

WHERE: HOST-SERVER-TERMINAL
```bash
# Login and extract token
curl -X POST https://sb-pms.kolibri-visions.de/auth/v1/token?grant_type=password \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"$EMAIL","password":"$PASSWORD"}' | jq -r '.access_token'

# Save to variable
export TOKEN="eyJhb..."
```

2. Verify token structure

WHERE: HOST-SERVER-TERMINAL
```bash
# Check token length (should be ~500+ chars)
echo ${#TOKEN}

# Check JWT parts (should have 3 parts: header.payload.signature)
echo $TOKEN | tr '.' '\n' | wc -l
# Expected: 3
```

3. Verify JWT_SECRET matches GoTrue

WHERE: Coolify Dashboard > pms-backend > Environment Variables
```
JWT_SECRET=your-jwt-secret-here
SUPABASE_JWT_SECRET=your-jwt-secret-here
```

WHERE: Supabase SQL Editor
```sql
-- Get GoTrue JWT secret
SELECT decrypted_secret
FROM vault.decrypted_secrets
WHERE name = 'jwt_secret';
```

4. Test auth endpoint with apikey header

WHERE: HOST-SERVER-TERMINAL
```bash
# Kong requires apikey header
curl https://sb-pms.kolibri-visions.de/auth/v1/user \
  -H "apikey: $ANON_KEY" \
  -H "Authorization: Bearer $TOKEN"

# Expected: {"id":"...","email":"...","role":"authenticated"}
```

**Verification:**

WHERE: HOST-SERVER-TERMINAL
```bash
# Test authenticated endpoint
curl https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 with property list (not 401)
```

**See Also:** [Token Validation](#token-validation-apikey-header) (detailed section below)

---

### 3. Worker/Celery/Redis Misconfig (Connection Refused / Tasks Not Updating Logs)

**Symptoms:**
```
Celery: ConnectionRefusedError [Errno 111] Connection refused
GET /health/ready → 503 {"celery":"down"}
Sync logs stuck in "triggered" or "running" (never "success"/"failed")
Worker logs: "Cannot connect to redis://localhost:6379"
```

**Root Cause:**
- Missing/wrong REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- Redis container not reachable from worker
- Health check not enabled in celery.py

**Fix Steps:**

1. Verify Redis is reachable

WHERE: Coolify Terminal (pms-worker-v2 container)
```bash
# Check Redis connection
redis-cli -u $CELERY_BROKER_URL ping
# Expected: PONG
```

2. Set correct environment variables

WHERE: Coolify Dashboard > pms-worker-v2 > Environment Variables
```
REDIS_URL=redis://coolify-redis:6379/0
CELERY_BROKER_URL=redis://coolify-redis:6379/0
CELERY_RESULT_BACKEND=redis://coolify-redis:6379/1
```

3. Verify Celery worker is running

WHERE: Coolify Terminal (pms-worker-v2 container)
```bash
# Check Celery status
celery -A app.worker.celery_app inspect ping
# Expected: {"celery@...": {"ok": "pong"}}

# Check active tasks
celery -A app.worker.celery_app inspect active
```

4. Check worker logs

WHERE: Coolify Dashboard > pms-worker-v2 > Logs
```
# Should see:
[INFO/MainProcess] Connected to redis://coolify-redis:6379/0
[INFO/MainProcess] celery@worker ready
```

**Verification:**

WHERE: HOST-SERVER-TERMINAL
```bash
# 1. Health check passes
curl https://api.fewo.kolibri-visions.de/health/ready
# Expected: {"celery":"up","redis":"up"}

# 2. Trigger availability sync
curl -X POST https://api.fewo.kolibri-visions.de/api/v1/channel-sync/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"property_id":"$PROPERTY_ID","sync_type":"availability"}'

# 3. Check sync log status updates
curl https://api.fewo.kolibri-visions.de/api/v1/channel-sync/logs/$LOG_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: status transitions from "triggered" → "running" → "success"
```

**See Also:** Worker troubleshooting sections below

---

### 4. Schema Drift / Missing Migrations (UndefinedTable/UndefinedColumn → 503)

**Symptoms:**
```
GET /api/v1/properties → 503 {"detail":"Database schema not installed or out of date..."}
Logs: asyncpg.exceptions.UndefinedTableError: relation "properties" does not exist
Logs: asyncpg.exceptions.UndefinedColumnError: column "agency_id" does not exist
```

**Root Cause:**
Deployed database schema doesn't match migration files in repo. Migrations not applied after schema changes.

**Fix Steps:**

1. Check what tables exist

WHERE: Supabase SQL Editor
```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Expected: agencies, properties, bookings, inventory_ranges, etc.
```

2. Check for missing columns

WHERE: Supabase SQL Editor
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'properties'
ORDER BY ordinal_position;

-- Verify key columns exist: id, agency_id, name, created_at, etc.
```

3. List migration files in repo

WHERE: HOST-SERVER-TERMINAL
```bash
ls -1 supabase/migrations/*.sql | tail -5
# See latest migration files
```

4. Apply migrations

WHERE: Supabase SQL Editor
```sql
-- Copy/paste migration SQL from supabase/migrations/*.sql
-- Execute each migration in order (oldest to newest)
-- Use DO $$ blocks for idempotent DDL if needed:

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'properties'
  ) THEN
    CREATE TABLE properties (...);
  END IF;
END $$;
```

**Verification:**

WHERE: HOST-SERVER-TERMINAL
```bash
# 1. Check endpoint returns 200
curl https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 with data (not 503)

# 2. Verify health check passes
curl https://api.fewo.kolibri-visions.de/health/ready
# Expected: {"status":"healthy","db":"up"}
```

WHERE: Supabase SQL Editor
```sql
-- Sample query to verify schema
SELECT p.id, p.name, p.agency_id
FROM properties p
LIMIT 1;

-- Should return data without errors
```

**See Also:**
- [Schema Drift](#schema-drift) (detailed section below)
- [Migrations Guide - Schema Drift SOP](../database/migrations-guide.md#schema-drift-sop) (step-by-step SOP)

---

### 5. Bash Smoke Script Pitfalls (TOKEN/PID Empty, set -u Unbound Variable, 307 Redirect)

**Symptoms:**
```bash
smoke.sh: line 42: PID: unbound variable
smoke.sh: line 55: TOKEN: unbound variable
curl: Expecting value: line 1 column 1 (char 0)  # Empty response
curl: 307 Temporary Redirect (without -L flag)
```

**Root Cause:**
- `set -u` causes script to exit if PID or TOKEN unset/empty
- Missing `-L` flag on curl (doesn't follow redirects)
- Invalid JSON response (HTML redirect page instead of JSON)

**Fix Steps:**

1. Export required variables before running script

WHERE: HOST-SERVER-TERMINAL
```bash
# Set variables
export BACKEND_URL="https://api.fewo.kolibri-visions.de"
export ANON_KEY="your-anon-key"
export EMAIL="admin@example.com"
export PASSWORD="your-password"
export PID="some-property-id"

# Verify variables are set
echo "BACKEND_URL: $BACKEND_URL"
echo "PID length: ${#PID}"
```

2. Fetch and validate TOKEN

WHERE: HOST-SERVER-TERMINAL
```bash
# Login and extract token
TOKEN=$(curl -X POST https://sb-pms.kolibri-visions.de/auth/v1/token?grant_type=password \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | jq -r '.access_token')

# Validate token
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "ERROR: Failed to fetch token"
  exit 1
fi

# Check token structure
echo "Token length: ${#TOKEN}"
echo "Token parts: $(echo $TOKEN | tr '.' '\n' | wc -l)"  # Should be 3
```

3. Use -L flag for curl redirects

WHERE: HOST-SERVER-TERMINAL
```bash
# Without -L: may return 307 redirect
curl https://api.fewo.kolibri-visions.de/health

# With -L: follows redirect to final destination
curl -L https://api.fewo.kolibri-visions.de/health
# Expected: {"status":"ok","service":"pms-backend"}
```

4. Quick smoke checks

WHERE: HOST-SERVER-TERMINAL
```bash
# Health check
curl -L $BACKEND_URL/health
# Expected: {"status":"ok"}

# Readiness check
curl -L $BACKEND_URL/health/ready
# Expected: {"status":"healthy","db":"up","redis":"up"}

# Authenticated endpoint
curl -L $BACKEND_URL/api/v1/properties \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 with JSON array
```

**Verification:**

WHERE: HOST-SERVER-TERMINAL
```bash
# Run smoke script with all variables set
./smoke.sh
# Expected: All checks pass, no "unbound variable" errors
```

**See Also:** [Smoke Script Pitfalls](#smoke-script-pitfalls) (detailed section below)

---

## DB DNS / Degraded Mode

### Symptom

After deployment or container restart:
- API returns `503 Service Unavailable`
- Logs show: `"Database connection pool creation FAILED"` or `"Service degraded"`
- Health endpoint (`/health`) returns 200, but `/health/ready` returns 503

### Root Cause

PMS backend container cannot resolve Supabase database DNS (`supabase-db`) due to missing Docker network attachment.

**Why this happens:**
- Coolify creates a dedicated network for Supabase stack: `bccg4gs4o4kgsowocw08wkw4`
- Coolify creates a default network for PMS app: `coolify`
- Container needs to be attached to **both** networks to resolve `supabase-db` hostname

**Common scenario:**
- Database/network may be temporarily unavailable during container startup (race condition)
- DNS resolution may fail transiently before network is fully ready
- Backend now retries connection for up to 60s before entering degraded mode

### New Behavior: Startup Retry + Background Self-Heal (2026-01-04)

**Startup Retry:**
- Backend now retries DB connection for up to `DB_STARTUP_MAX_WAIT_SECONDS` (default: 60s)
- Sleeps `DB_STARTUP_RETRY_INTERVAL_SECONDS` (default: 2s) between attempts
- Logs progress: elapsed time, error type, next retry
- If connection succeeds within timeout: starts normally (no degraded mode warning)
- If still failing after timeout: enters degraded mode and starts background reconnection

**Background Self-Heal:**
- If startup fails, backend starts a background task to periodically retry DB connection
- Retries every `DB_BACKGROUND_RECONNECT_INTERVAL_SECONDS` (default: 30s)
- When DB becomes available: pool is created automatically (no restart needed)
- Logs success: "Background reconnection: SUCCESS. App is now in NORMAL MODE"
- Disable with `DB_BACKGROUND_RECONNECT_ENABLED=false` if needed

**Expected Logs:**
```
# Startup (first attempt fails, retrying)
Database connection attempt 1 failed (gaierror: Temporary failure in name resolution).
Retrying in 2.0s (elapsed: 0.2s, max: 60s)...

# Startup (success after retries)
Database connection pool created successfully (PID=1, host=supabase-db, attempt=3, elapsed=4.5s)

# Startup (all retries exhausted, entering degraded mode)
Database connection failed after 30 attempts (60.1s).
Last error: gaierror: Temporary failure in name resolution.
App will start in DEGRADED MODE (DB unavailable).
Background reconnection will retry every 30s.

# Background reconnection (attempting)
Background reconnection: attempting to create DB pool...

# Background reconnection (success)
Background reconnection: SUCCESS. App is now in NORMAL MODE (DB available).
```

**Impact:**
- **Before:** Immediate degraded mode on any startup DNS failure (required restart)
- **After:** Retries for 60s, then self-heals via background task (no restart needed)
- **Readiness:** `/health/ready` will return 503 for up to 60s after deploy if DB is slow to start
- **Operators:** If you see 503 immediately after deploy, wait up to 60s before investigating

### Single-Instance Pool Initialization (2026-01-04 Updated)

**Symptom:**
- Backend logs show repeated "Database connection pool created successfully" messages with different attempt numbers
- Multiple pool creation log lines appear (e.g., "attempt=12", then "attempt=1", then "attempt=1")
- Indicates multiple init call sites creating new pools instead of reusing shared instance
- Logs may show: pool created ... generation=1, then generation=2, generation=3 (generation increments)

**Root Cause (Updated Analysis):**
- Previous fix added lock but didn't prevent sequential retry loops
- Multiple call sites (startup, request-time ensure, health checks) each started own retry loop
- Lock only prevented concurrent execution, not duplicate initialization attempts
- First caller starts retry loop (attempt=1...12), completes; second caller starts new retry (attempt=1)
- Risk: leaked pools/connections, wasted DB retry attempts, noisy logs

**Fix Applied (Init Task Tracking):**
- Added `_init_task` to track ongoing pool initialization (prevents duplicate init)
- Added `_pool_generation` counter (increments on each pool creation for verification)
- `ensure_pool()` now uses init task pattern:
  - If pool exists: returns immediately (fast path, no lock)
  - If init task exists: awaits it (reuses ongoing initialization)
  - If neither exists: creates init task, awaits it (single retry loop)
- All call sites use `ensure_pool()` (startup, requests, health, background task)
- Retry loop runs exactly once per pool creation (not once per caller)

**Expected Behavior After Fix:**
```
# Startup (single pool creation, single retry loop)
Creating database connection pool (PID=1, host=supabase-db, max_wait=60s, retry_interval=2s)...
Database connection pool created successfully (PID=1, host=supabase-db, generation=1, attempt=3, elapsed=4.5s, pool_id=140...)
Database connected: PostgreSQL 15.1...

# Subsequent calls (pool already exists, reuse, NO logs)
[Silent - pool is reused via fast path]

# If pool creation fails and background reconnect succeeds
Background reconnection: attempting to create DB pool...
Creating database connection pool (PID=1, host=supabase-db, max_wait=60s, retry_interval=2s)...
Database connection pool created successfully (PID=1, host=supabase-db, generation=2, attempt=1, elapsed=0.5s, pool_id=140...)
Background reconnection: SUCCESS. App is now in NORMAL MODE (DB available).
```

**Verification Steps:**
```bash
# 1. Restart backend container
docker restart $(docker ps -q -f name=pms-backend)

# 2. Count pool creation events (should be exactly 1)
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | wc -l
# Expected: 1

# 3. Check generation counter (should be 1 for first pool)
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully"
# Expected: Single line with "generation=1"

# 4. Check pool_id stays constant (proves same pool reused)
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | grep -o "pool_id=[0-9]*"
# Expected: Single pool_id value

# 5. Make multiple concurrent /health/ready requests (should NOT create new pools)
for i in {1..20}; do curl -s https://api.fewo.kolibri-visions.de/health/ready & done
wait

# 6. Verify still only one pool creation
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | wc -l
# Expected: Still 1 (not 2, 3, 10, etc.)

# 7. Check for multiple attempt sequences (regression symptom)
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "Database connection attempt" | grep -o "attempt=[0-9]*"
# Expected: Single sequence (e.g., attempt=1, attempt=2, attempt=3)
# NOT multiple sequences starting from attempt=1
```

**Operator Notes:**
- **Healthy:** Exactly one "pool created" log with generation=1, single attempt sequence
- **Regression:** Multiple "pool created" logs, or generation>1 without background reconnect
- **Forked processes:** Celery workers create own pool (generation increments per worker - expected)
- **Pool ID:** Should remain constant across all requests (proves reuse)

### Multiple Pools Created in Same PID (pool_id changes) - 2026-01-04

**Symptom:**
- Same PID creates multiple pools with DIFFERENT pool_id values
- Example logs from PID=1:
  - pool_id=128315581080752, generation=1
  - pool_id=136539789892368, generation=1
  - pool_id=140137983023888, generation=1
- Generation stays at 1 (should increment to 2, 3, 4)
- Indicates true pool recreation, not just duplicate logging

**Root Causes (Investigated):**

**A) Multiple module instances (singleton not shared):**
- Multiple imports of database module create separate _pool variables
- Check: `module_id` should be identical across all "pool created" logs
- If module_id changes: multiple module instances exist (reimport issue)

**B) Code path closes/resets pool incorrectly:**
- Some code calls `_pool = None` or `pool.close()` outside shutdown
- Check: grep logs for "Resetting pool state" or "Closing database connection pool"
- If appears during normal operation: incorrect reset/close call

**C) Celery worker reset without clearing init task:**
- `reset_pool_state()` must reset `_pool`, `_pool_pid`, AND `_init_task`
- If `_init_task` not reset: child process may await parent's task (wrong event loop)
- Fix: reset_pool_state() now clears _init_task (2026-01-04)

**Fix Applied (2026-01-04):**
- Updated `reset_pool_state()` to also reset `_init_task` (critical for fork safety)
- Added comprehensive diagnostics to pool creation log:
  - `module_file`: Path to database.py file (proves same module)
  - `module_id`: ID of module object (proves singleton)
  - `pool_id`: ID of pool instance (changes on recreation)
  - `generation`: Counter (must increment on each creation)

**Verification Commands:**
```bash
# 1. Check if pool_id changes (regression symptom)
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | grep -o "pool_id=[0-9]*"
# Expected: Single pool_id value
# Bad: Multiple different pool_id values

# 2. Check if generation increments correctly
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | grep -o "generation=[0-9]*"
# Expected: generation=1 (or generation=1, generation=2 if background reconnect)
# Bad: Multiple generation=1 entries

# 3. Check module_id stays constant (proves singleton)
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | grep -o "module_id=[0-9]*"
# Expected: Single module_id value
# Bad: Multiple different module_id values (indicates multiple module instances)

# 4. Check module_file stays constant
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | grep -o "module_file=[^ ]*"
# Expected: Same file path for all entries
# Bad: Different file paths (indicates import from different locations)

# 5. Full diagnostic line
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully"
# Analyze: PID, generation, pool_id, module_id, module_file should be consistent
```

**Diagnosis Decision Tree:**
1. **pool_id changes, generation stays 1, module_id changes:**
   - Cause: Multiple module instances (reimport or circular import)
   - Action: Check import paths, remove circular imports

2. **pool_id changes, generation stays 1, module_id constant:**
   - Cause: Pool is being closed/reset incorrectly during operation
   - Action: Check for unauthorized pool.close() or _pool=None assignments

3. **pool_id changes, generation increments, module_id constant:**
   - Cause: Background reconnect working correctly (not a bug)
   - Action: Verify degraded mode preceded this (expected behavior)

### Pool Churn Diagnostics - Python Helpers (2026-01-04)

**Purpose:** Programmatic diagnostic functions for detecting pool churn at runtime.

**Function: `pool_debug_state()`**

Returns comprehensive pool state for debugging:

```python
from app.core.database import pool_debug_state
import json

# In endpoint (for debugging)
@router.get("/debug/pool-state")
async def get_pool_state():
    return pool_debug_state()

# In logs
logger.info(f"Pool state: {json.dumps(pool_debug_state(), indent=2)}")
```

**Returns:**
```json
{
  "pool_exists": true,
  "pool_id": 140137983023888,
  "pool_pid": 1,
  "current_pid": 1,
  "pool_generation": 1,
  "init_task_running": false,
  "background_reconnect_running": false,
  "module_info": {
    "duplicates_found": false,
    "module_keys": ["app.core.database"],
    "module_id": 140137982456320,
    "module_file": "/app/app/core/database.py"
  }
}
```

**Function: `detect_duplicate_module_import()`**

Detects if database module is imported multiple times (root cause of pool churn):

```python
from app.core.database import detect_duplicate_module_import

result = detect_duplicate_module_import()
if result["duplicates_found"]:
    logger.error(f"Duplicate module imports detected: {result['module_keys']}")
    # Example: ["app.core.database", "core.database", "database"]
```

**Common Causes of Duplicate Imports:**
- Import path variation: `app.core.database` vs `core.database` vs `database`
- Symlinks: `/app/core/database.py` vs `/app-symlink/core/database.py`
- sys.path manipulation: module loaded from different paths
- Circular imports: Python imports module twice to break cycle

**Action on Detection:**
1. Review all import statements: grep for `from.*database import` or `import.*database`
2. Standardize to single import path: `from app.core.database import ...`
3. Remove circular imports (use TYPE_CHECKING for type hints)
4. Verify sys.path doesn't contain duplicate entries

### Singleflight Pool Creation - Race Condition Fix (2026-01-04)

**Symptom:**
- Multiple "Database connection pool created successfully" logs within single container lifetime
- Different pool_id values despite same PID=1, RestartCount=0
- Occurs during startup + concurrent requests (health checks, tenant resolution)
- Race window: startup creates pool while concurrent requests also call ensure_pool()

**Root Cause:**
- **Before Fix:** ensure_pool() had bug where existing init task was awaited INSIDE lock
- Lock held while waiting → concurrent callers blocked from joining same task
- Result: Sequential callers each created own init task → multiple asyncpg.create_pool() calls
- Manifests as: pool_id=123, then pool_id=456, then pool_id=789 (all PID=1, generation=1)

**Fix Applied (2026-01-04 Singleflight):**

Changed ensure_pool() to implement true singleflight pattern:
1. **Fast path (line 262):** If pool exists, return immediately (zero lock contention, 99.9% case)
2. **Slow path (lines 269-311):**
   - Acquire lock to atomically check/create init task
   - If init task in progress: store reference, **release lock**, await outside lock
   - If no init task: create one, store reference, **release lock**, await outside lock
   - All concurrent callers await the SAME task → asyncpg.create_pool() called exactly once

**Key Change:**
```python
# BEFORE (BUG): Await inside lock - blocks other callers
async with lock:
    if _init_task is not None and not _init_task.done():
        await _init_task  # ❌ Lock held while waiting!
        return _pool

# AFTER (FIXED): Store reference, await outside lock - allows concurrent joins
async with lock:
    if _init_task is not None and not _init_task.done():
        task_to_await = _init_task  # ✅ Store reference
# Lock released here
await task_to_await  # ✅ Await outside lock
```

**Verification After Deployment:**

```bash
# 1. Check pool created only once per container lifetime
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | wc -l
# Expected: 1 (unless background reconnect triggered after degraded mode)

# 2. Verify pool_id stays constant
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | grep -o "pool_id=[0-9]*" | sort -u
# Expected: Single pool_id value

# 3. Check for singleflight log messages
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "joining existing task (singleflight)"
# If present: Confirms concurrent callers joined existing init task (correct behavior)

# 4. Check generation counter
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | grep -o "generation=[0-9]*"
# Expected: generation=1 (first pool creation after startup)
```

**Expected Behavior:**
- Startup calls ensure_pool() → creates init task, starts pool creation
- Concurrent health check calls ensure_pool() → sees init task, awaits same task
- Concurrent tenant resolution calls ensure_pool() → sees init task, awaits same task
- Result: Single "pool created successfully" log, single pool_id, all callers get same pool

**Regression Test:**
- Unit tests added: `tests/unit/test_database_singleflight.py`
- Test spawns 20 concurrent ensure_pool() calls, asserts asyncpg.create_pool() called exactly once
- Test simulates realistic scenario: startup + health check + tenant resolution concurrently

### Multiple pool_id Within One Runtime - Detection & Debug (2026-01-04)

**Symptom:**
- Same container (RestartCount=0, PID=1) shows multiple "pool created successfully" logs
- Different pool_id values within single runtime (no container restart)
- Server startup sequence appears twice in logs:
  - "Started server process [1]"
  - "Waiting for application startup"
  - "Application startup complete"
  - (repeats above sequence again)

**Root Cause Analysis:**

Multiple pool creations within same runtime can be caused by:
1. **Application startup running twice** (reload, worker restart, double-init)
2. **Concurrent requests racing** during startup (health checks, tenant resolution)
3. **Background reconnect** after degraded mode (expected, generation increments)

**Detection Commands:**

```bash
# 1. Check container hasn't restarted
docker inspect $(docker ps -q -f name=pms-backend) --format '{{.Name}}: Started={{.State.StartedAt}} RestartCount={{.RestartCount}}'
# Expected: RestartCount=0 (no restarts)
# If symptom persists with RestartCount=0: multiple pools in same runtime confirmed

# 2. Count pool creations in current runtime
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | wc -l
# Expected: 1 (unless background reconnect triggered)
# Bad: 2+ within same runtime

# 3. List unique pool_id values
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | grep -o "pool_id=[0-9]*" | sort -u
# Expected: Single pool_id
# Bad: Multiple different pool_id values

# 4. Check generation counter progression
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | grep -o "generation=[0-9]*"
# Expected: generation=1 (or 1,2 if background reconnect)
# Bad: Multiple generation=1 entries (indicates duplicate init, not progression)

# 5. Look for startup sequence duplication
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep -c "Started server process"
# Expected: 1
# Bad: 2+ (indicates application lifecycle running twice)
```

**Debug Mode (DB_POOL_DEBUG=true):**

Enable detailed pool initialization logging to diagnose which code path triggers duplicate creation:

```bash
# Set via environment variable
docker exec pms-backend env | grep DB_POOL_DEBUG
# Or restart with DB_POOL_DEBUG=true

# Check debug logs after enabling
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "\[DB_POOL_DEBUG\]"
# Shows: entry point, PID, generation, reason, callsite (file:line/function)
```

**Debug Log Example:**
```
[DB_POOL_DEBUG] ensure_pool entry: PID=1, gen=0, pool_exists=False, callsite=main.py:77/lifespan
[DB_POOL_DEBUG] Creating pool init task (PID=1, reason=no_pool, callsite=main.py:77/lifespan)
Database connection pool created successfully (PID=1, host=db.supabase.co, generation=1, ...)
[DB_POOL_DEBUG] ensure_pool entry: PID=1, gen=1, pool_exists=True, callsite=health.py:15/health_check
# Fast path returns immediately (no duplicate creation)
```

**Mitigation Applied (2026-01-04):**
- Singleflight pattern ensures only ONE pool creation per runtime
- DB_POOL_DEBUG flag for detailed diagnostics (silent by default)
- Defensive check: warns + closes old pool if duplicate detected (shouldn't happen)

**Expected Behavior:**
- Within single runtime (RestartCount=0): exactly 1 pool creation
- pool_id stays constant throughout runtime
- generation=1 for first pool (or increments on reconnect after degraded mode)
- DB_POOL_DEBUG shows fast path returns after first init

### External Stop-Start Causing Duplicate Startup (2026-01-04)

**Symptom:**
- Container logs show duplicate startup signatures:
  - "Started server process [1]" appears twice
  - "Application startup complete" appears twice
  - CancelledError between the two startup sequences
- Multiple "pool created successfully" logs with different pool_id values
- RestartCount remains 0 (no increment)
- Container appears to have been stopped and started without a "restart"

**How to Prove It's External Stop-Start (Not In-Process Issue):**

```bash
# 1. Check container state for FinishedAt timestamp
docker inspect $(docker ps -q -f name=pms-backend) --format '{{.State.FinishedAt}}'
# If non-zero: container was stopped at some point
# Compare with StartedAt to see if stop happened during current runtime

# 2. Compare container StartedAt vs log timestamps
docker inspect $(docker ps -q -f name=pms-backend) --format 'StartedAt={{.State.StartedAt}}'
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "Started server process" | head -2
# If first "Started server process" timestamp is BEFORE StartedAt: old log from previous run
# If both timestamps are AFTER StartedAt: duplicate startup in current run (different issue)

# 3. Check container state for ExitCode
docker inspect $(docker ps -q -f name=pms-backend) --format 'ExitCode={{.State.ExitCode}} RestartCount={{.RestartCount}}'
# ExitCode=0 + RestartCount=0 suggests clean stop (not crash/restart)

# 4. Check daemon journal for manual stop events
journalctl -u docker.service --since "1 hour ago" | grep "container.*stop"
journalctl -u docker.service --since "1 hour ago" | grep "hasBeenManuallyStopped=true"
# Look for stop events matching container ID at the same time as FinishedAt

# 5. Search host for network connectivity automation
find /usr/local/bin /etc/systemd/system -name "*network*" -o -name "*ensure*" 2>/dev/null
systemctl list-timers --all | grep -i network
systemctl list-timers --all | grep -i ensure
# Look for timers or services that might restart containers

# 6. Inspect the automation script for restart behavior
cat /usr/local/bin/pms-ensure-*-network.sh  # or similar
# Check if script contains "docker restart" command
```

**Root Cause:**
Host-level automation designed to "ensure network connectivity" was:
- Running on a timer (e.g., every 30 seconds)
- Executing `docker network connect <network> <container>`
- **Also executing `docker restart <container>`** (unnecessary and harmful)

This caused the container to stop cleanly (ExitCode=0), then start again, without incrementing RestartCount (because it's a manual stop-start, not an automatic restart).

**Fix Applied (on Host):**
Updated the host network connectivity script to:
1. **NEVER restart the container**
2. Only attach the network if it's missing (idempotent `docker network connect`)
3. Only operate on running containers (check container state first)
4. Optionally adjust timer frequency if 30s is too aggressive

**Example Fixed Script Pattern:**
```bash
#!/bin/bash
# Good: Idempotent network attach WITHOUT restart

CONTAINER_NAME="pms-backend"
NETWORK_NAME="your-network"

# Only proceed if container is running
if [ "$(docker inspect -f '{{.State.Running}}' $CONTAINER_NAME 2>/dev/null)" != "true" ]; then
    exit 0
fi

# Idempotent network connect (fails silently if already connected)
docker network connect $NETWORK_NAME $CONTAINER_NAME 2>/dev/null || true

# NO docker restart command!
```

**Verification Steps After Fix:**

```bash
# 1. Verify StartedAt doesn't change over time
docker inspect $(docker ps -q -f name=pms-backend) --format 'StartedAt={{.State.StartedAt}}'
# Wait 5 minutes, check again - should be unchanged

# 2. Monitor daemon journal for stop/start events
journalctl -u docker.service -f | grep "container.*pms-backend"
# Should see network connect events, but NO stop/start events

# 3. Check for new startup signatures in logs
docker logs --since 5m $(docker ps -q -f name=pms-backend) 2>&1 | grep "Started server process"
# Should be empty (no new startup sequences)

# 4. Verify timer still runs but doesn't restart
systemctl list-timers --all | grep ensure
journalctl -u your-ensure-timer.service --since "5m ago"
# Timer should run, but logs should show only network operations, no restarts

# 5. Verify single pool_id persists
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully" | tail -1
# Wait 5 minutes, check again - should show same pool_id
```

**Expected Behavior After Fix:**
- Container StartedAt timestamp remains constant
- No stop/start events in daemon journal
- No new "Started server process" signatures in logs
- Single pool_id throughout entire runtime
- Network connectivity maintained without container disruption

### Duplicate Startup Signatures + Multiple pool_id: Distinguish External Causes (2026-01-04)

**Overview:**
When you observe duplicate "Started server process [1]" + "Application startup complete" logs with CancelledError between them, and multiple different pool_id values while RestartCount=0, this is NOT an in-process application bug (e.g., uvicorn reload or multiple workers). It is caused by external container lifecycle events.

**Proven Evidence (Not In-Process):**
```bash
# CONTAINER: Check process tree shows single process
docker exec pms-backend ps aux
# Expected: Single /opt/venv/bin/python ... uvicorn app.main:app --host 0.0.0.0 --port 8000

# CONTAINER: Verify no reload or workers flags
docker exec pms-backend cat /proc/1/cmdline | tr '\0' ' '
# Expected: NO --reload or --workers flags
```

**Two Distinct External Causes:**

---

#### **CASE A: Container Replace (Deploy/Recreate)**

**What Happens:**
- Deployment manager (orchestrator) creates NEW container with updated image tag
- Old container stops/removed, new container starts
- Container ID changes (new container created)
- RestartCount may stay 0 (new container, not a daemon restart loop)
- Each container has its own startup sequence + pool_id

**How to Prove (HOST):**

```bash
# 1. Check for container ID change
docker ps -a --no-trunc --filter name=pms-backend | head -5
# If multiple containers with different IDs: replacement occurred

# 2. Check container creation/start times
docker inspect pms-backend --format 'Id={{.Id}}
Created={{.Created}}
StartedAt={{.State.StartedAt}}
FinishedAt={{.State.FinishedAt}}
RestartCount={{.RestartCount}}
ExitCode={{.State.ExitCode}}'
# Created timestamp shows when container was created (replacement creates new)

# 3. Check rendered deployment files modification time
# (Use your deployment manager's rendered directory path)
stat $DEPLOY_APP_DIR/docker-compose.yaml
stat $DEPLOY_APP_DIR/.env
# If mtimes align with container Created time: deployment recreated container

# 4. Check image tag change in rendered compose
diff <previous-compose-backup> $DEPLOY_APP_DIR/docker-compose.yaml
# Look for image: tag changes (e.g., old-hash -> new-hash)

# 5. Check logs show TWO separate container lifecycles
docker logs --timestamps pms-backend 2>&1 | grep -E 'Started server process|Application startup complete|pool created' | head -20
# First startup from old container (before Created time)
# Second startup from new container (after Created time)
```

**Expected Behavior (Case A):**
- Two container IDs exist (old removed, new running)
- Two startup sequences in logs (one per container)
- Each container has different pool_id (expected, separate processes)
- RestartCount=0 in new container (not a restart, it's a new container)

**Safe Pattern (Case A):**
- This is normal deployment behavior (recreate strategy)
- Use SOURCE_COMMIT or image tag + compose/env mtime to correlate deployments
- Monitor for exactly ONE startup sequence in new container
- Verify old container is stopped/removed (not running simultaneously)

---

#### **CASE B: Host Automation Restart (Network Connectivity)**

**What Happens:**
- Host-level script/timer monitors network connectivity
- Script executes `docker network connect <network> <container>` (correct, idempotent)
- Script ALSO executes `docker restart <container>` (incorrect, harmful)
- Same container ID, but stop/start cycle produces duplicate startups
- RestartCount stays 0 (manual stop/start, not daemon restart)

**How to Prove (HOST):**

```bash
# 1. Check container ID stays SAME across time
docker ps -a --no-trunc --filter name=pms-backend
# Same container ID but FinishedAt set: stop/start within same container

# 2. Check container state shows stop event
docker inspect pms-backend --format 'FinishedAt={{.State.FinishedAt}}
ExitCode={{.State.ExitCode}}
RestartCount={{.RestartCount}}'
# FinishedAt non-zero + ExitCode=0 + RestartCount=0: manual stop (not crash)

# 3. Check daemon journal for manual stop events
journalctl -u docker.service --since "1 hour ago" | grep -E "container.*stop|hasBeenManuallyStopped=true"
# Look for stop events matching container ID

# 4. Search host for network connectivity automation
systemctl list-timers --all | grep -iE 'network|ensure|connectivity'
find /usr/local/bin /etc/systemd/system -type f -name "*network*" -o -name "*ensure*" 2>/dev/null

# 5. Audit automation script for restart behavior
systemctl cat <timer-service-name>
cat /usr/local/bin/<ensure-network-script>
# Look for "docker restart" command (HARMFUL)

# 6. Monitor for stop/start events during timer execution
journalctl -u docker.service -f | grep "container.*pms-backend"
# While timer runs, watch for stop/start events
```

**Expected Behavior Before Fix (Case B):**
- Same container ID persists
- FinishedAt timestamp appears (container was stopped)
- Duplicate startup signatures every timer interval (e.g., 30s)
- Multiple pool_id values within same container name

**Safe Fix Pattern (Case B):**
```bash
#!/bin/bash
# CORRECT: Idempotent network attach WITHOUT restart

CONTAINER_NAME="pms-backend"
NETWORK_NAME="database-network"  # Generic placeholder

# Only proceed if container is running
if [ "$(docker inspect -f '{{.State.Running}}' $CONTAINER_NAME 2>/dev/null)" != "true" ]; then
    exit 0
fi

# Idempotent network connect (fails silently if already connected)
docker network connect $NETWORK_NAME $CONTAINER_NAME 2>/dev/null || true

# NO docker restart command!
# NO docker stop/start commands!
```

**Verification After Fix (Case B):**
```bash
# 1. Verify StartedAt doesn't change
docker inspect pms-backend --format 'StartedAt={{.State.StartedAt}}'
# Wait through several timer cycles, check again - should be unchanged

# 2. Monitor daemon journal shows NO stop/start
journalctl -u docker.service -f | grep "container.*pms-backend"
# Should see network connect events, but NO stop/start

# 3. Check logs show NO new startup signatures
docker logs --since 10m pms-backend 2>&1 | grep "Started server process"
# Should be empty (no new startups)

# 4. Verify single pool_id persists
docker logs pms-backend 2>&1 | grep "pool created successfully" | tail -5
# Same pool_id across all recent logs
```

---

**Decision Tree: Which Case?**

| Observation | Indicates |
|-------------|-----------|
| Container ID changed between startups | **CASE A** (Deploy Replace) |
| Container ID same, FinishedAt set | **CASE B** (Host Automation) |
| Rendered compose/env mtime matches startup | **CASE A** (Deploy Replace) |
| Image tag changed in compose | **CASE A** (Deploy Replace) |
| Daemon journal shows "manually stopped" | **CASE B** (Host Automation) |
| Host timer service found with restart | **CASE B** (Host Automation) |
| Two container IDs in `docker ps -a` | **CASE A** (Deploy Replace) |
| StartedAt changes regularly (e.g., every 30s) | **CASE B** (Host Automation) |

**Verification Checklist:**

After Host Automation Fix (Case B):
- [ ] Container StartedAt stable across timer triggers
- [ ] No stop/start events in daemon journal
- [ ] No new startup signatures in logs
- [ ] Single pool_id throughout runtime
- [ ] Network connectivity maintained without disruption

After Deploy Replace (Case A):
- [ ] Exactly one startup sequence in new container
- [ ] Old container stopped/removed (not running)
- [ ] Process tree shows single uvicorn process
- [ ] No --reload or --workers flags in /proc/1/cmdline
- [ ] New container ID correlates with compose/env mtime

### Verify

```bash
# SSH to host server
ssh root@your-host

# Check container networks
docker inspect $(docker ps -q -f name=pms) | grep -A 10 Networks

# Expected: both "coolify" and "bccg4gs4o4kgsowocw08wkw4" networks

# Test DNS resolution inside container
docker exec $(docker ps -q -f name=pms) getent hosts supabase-db

# Expected: IP address (e.g., 172.20.0.2)
# If empty/error: DNS resolution failed
```

### Fix

**Option 1: Via Coolify Dashboard (Recommended)**

1. Open Coolify dashboard
2. Navigate to: **Applications > PMS-Webapp > Networks**
3. Ensure both networks are selected:
   - `coolify` (default)
   - `bccg4gs4o4kgsowocw08wkw4` (Supabase network)
4. Click **Save** and **Restart** application

**Option 2: Manual Docker Network Attachment**

```bash
# Attach container to Supabase network
docker network connect bccg4gs4o4kgsowocw08wkw4 $(docker ps -q -f name=pms)

# Verify
docker exec $(docker ps -q -f name=pms) getent hosts supabase-db
# Should now return IP address

# Restart container to recreate pool
docker restart $(docker ps -q -f name=pms)
```

**Option 3: Update DATABASE_URL to use public DNS**

If network attachment fails, use Supabase public URL:

```bash
# In Coolify: Applications > PMS-Webapp > Environment Variables
DATABASE_URL=postgresql://postgres:your-password@your-project.supabase.co:5432/postgres

# Note: This bypasses pgBouncer connection pooling (less efficient)
```

### Prevention

- Ensure Coolify deployment config includes both networks
- Add network check to CI/CD health checks
- Monitor `/health/ready` endpoint (should return 200 within 10s of deploy)

### Auto-Heal Supabase Network Attachment (Host Cron)

**Problem:** Coolify redeploys may drop the extra network attachment, causing DB DNS resolution failures and "Database temporarily unavailable" errors even when the network is configured in Coolify UI.

**Solution:** Use a host-side cron job to automatically reconnect containers to the Supabase network if they become detached.

---

#### The Auto-Heal Script

**Location (Production):** `/usr/local/bin/pms_ensure_supabase_net.sh`

**Source:** `backend/scripts/ops/pms_ensure_supabase_net.sh` (in repo)

**What It Does:**

The script performs automatic network attachment healing for PMS containers:

1. **Checks target containers** (`pms-backend`, `pms-worker-v2`) every 2 minutes
2. **Inspects Docker networks** for each container
3. **Detects missing attachment** to Supabase network (`bccg4gs4o4kgsowocw08wkw4`)
4. **Auto-attaches + restarts** if detached (logs action to `/var/log/pms_ensure_supabase_net.log`)
5. **Silent no-op** if already attached (logs daily "OK" heartbeat to `/var/log/pms_ensure_supabase_net.ok`)

**Behavior Summary:**
- **Intentionally quiet:** No output when everything is OK (except daily heartbeat)
- **Logs only when fixing:** Writes to `.log` when it reconnects a container
- **Daily heartbeat:** Writes single "OK" message to `.ok` file once per day (confirms cron is alive)
- **Restart required:** Container must restart after network attachment for DNS to work

**Key Features:**
- Idempotent (safe to run every 2 minutes)
- No-op if containers don't exist or are stopped
- Automatic restart after network reattachment
- Timestamped logs (UTC)

---

#### Cron Schedule

**Location:** `/etc/cron.d/pms_ensure_supabase_net` (production)

**Schedule:** Every 2 minutes

**Content:**
```bash
# PMS Supabase Network Auto-Heal
# Runs every 2 minutes to ensure pms-backend and pms-worker-v2
# are always attached to the Supabase network (bccg4gs4o4kgsowocw08wkw4)
*/2 * * * * root /usr/local/bin/pms_ensure_supabase_net.sh >> /var/log/pms_ensure_supabase_net.log 2>&1
```

**Alternative (Root crontab):**
```bash
# Edit root crontab
crontab -e

# Add this line:
*/2 * * * * /usr/local/bin/pms_ensure_supabase_net.sh >> /var/log/pms_ensure_supabase_net.log 2>&1
```

---

#### Log Files

**Primary Log:** `/var/log/pms_ensure_supabase_net.log`

Contains timestamped entries when script takes action (attaches network, restarts container):

```
[2025-12-29 14:32:01 UTC] ====== PMS Supabase Network Auto-Attach Check ======
[2025-12-29 14:32:01 UTC] FIXING: pms-backend not attached to bccg4gs4o4kgsowocw08wkw4
[2025-12-29 14:32:01 UTC] ACTION: Connecting pms-backend to bccg4gs4o4kgsowocw08wkw4...
[2025-12-29 14:32:02 UTC] SUCCESS: Connected pms-backend to bccg4gs4o4kgsowocw08wkw4
[2025-12-29 14:32:02 UTC] ACTION: Restarting pms-backend...
[2025-12-29 14:32:05 UTC] SUCCESS: Restarted pms-backend
[2025-12-29 14:32:05 UTC] OK: pms-worker-v2 already attached to bccg4gs4o4kgsowocw08wkw4
[2025-12-29 14:32:05 UTC] ====== Check Complete ======
```

**Heartbeat Log:** `/var/log/pms_ensure_supabase_net.ok`

Contains daily heartbeat (single "OK" message per day, confirms cron is running):

```
[2025-12-29 00:00:01 UTC] OK: Daily heartbeat - pms-backend and pms-worker-v2 healthy
[2025-12-30 00:00:01 UTC] OK: Daily heartbeat - pms-backend and pms-worker-v2 healthy
```

**Why separate .ok file?**
- Keeps primary log clean (only shows actual fixes)
- Easy grep for "all is well" vs "something was fixed"
- Prevents log bloat (1 heartbeat/day vs 720 checks/day)

---

#### Verification Commands

**Check cron is configured:**
```bash
# Option 1: Check /etc/cron.d/
ls -la /etc/cron.d/pms_ensure_supabase_net

# Option 2: Check root crontab
crontab -l | grep pms_ensure_supabase_net
```

**Check cron daemon is running:**
```bash
# SystemD (most modern distros)
systemctl status cron

# OR
systemctl status crond

# Expected: "active (running)"
```

**Check script exists and is executable:**
```bash
ls -la /usr/local/bin/pms_ensure_supabase_net.sh

# Expected: -rwxr-xr-x (executable)
```

**Check recent logs:**
```bash
# Last 20 lines of action log (shows fixes)
tail -20 /var/log/pms_ensure_supabase_net.log

# Last heartbeat (daily OK)
tail -5 /var/log/pms_ensure_supabase_net.ok

# Live tail (watch for fixes in real-time)
tail -f /var/log/pms_ensure_supabase_net.log
```

**Verify network attachment:**
```bash
# Check pms-backend networks
docker inspect pms-backend --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'

# Expected: coolify bccg4gs4o4kgsowocw08wkw4

# Check pms-worker-v2 networks
docker inspect pms-worker-v2 --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'

# Expected: coolify bccg4gs4o4kgsowocw08wkw4
```

**Manual test (trigger script immediately):**
```bash
# Run script manually (see output)
/usr/local/bin/pms_ensure_supabase_net.sh

# Expected output (if already attached):
# [2025-12-29 14:45:01 UTC] ====== PMS Supabase Network Auto-Attach Check ======
# [2025-12-29 14:45:01 UTC] OK: pms-backend already attached to bccg4gs4o4kgsowocw08wkw4
# [2025-12-29 14:45:01 UTC] OK: pms-worker-v2 already attached to bccg4gs4o4kgsowocw08wkw4
# [2025-12-29 14:45:01 UTC] ====== Check Complete ======
```

---

#### Setup Instructions (HOST-SERVER-TERMINAL)

**Step 1: Install script to production path**

```bash
# SSH to host server
ssh root@your-server.com

# Option A: Copy from cloned repo
cd /root
git clone https://github.com/Kolibri-Visions/PMS-Webapp.git
cp PMS-Webapp/backend/scripts/ops/pms_ensure_supabase_net.sh /usr/local/bin/
chmod +x /usr/local/bin/pms_ensure_supabase_net.sh

# Option B: Download directly (if repo is public)
curl -o /usr/local/bin/pms_ensure_supabase_net.sh \
  https://raw.githubusercontent.com/Kolibri-Visions/PMS-Webapp/main/backend/scripts/ops/pms_ensure_supabase_net.sh
chmod +x /usr/local/bin/pms_ensure_supabase_net.sh
```

**Step 2: Create cron.d entry (Recommended)**

```bash
# Create /etc/cron.d/pms_ensure_supabase_net
cat > /etc/cron.d/pms_ensure_supabase_net <<'EOF'
# PMS Supabase Network Auto-Heal
# Runs every 2 minutes to ensure containers stay attached to Supabase network
*/2 * * * * root /usr/local/bin/pms_ensure_supabase_net.sh >> /var/log/pms_ensure_supabase_net.log 2>&1
EOF

# Set correct permissions
chmod 644 /etc/cron.d/pms_ensure_supabase_net

# Reload cron
systemctl reload cron || systemctl reload crond
```

**Step 3: Verify cron is active**

```bash
# Check cron daemon
systemctl status cron

# Wait 2 minutes, then check logs
tail -f /var/log/pms_ensure_supabase_net.log

# Expected (if all OK):
# [2025-12-29 14:50:01 UTC] ====== PMS Supabase Network Auto-Attach Check ======
# [2025-12-29 14:50:01 UTC] OK: pms-backend already attached to bccg4gs4o4kgsowocw08wkw4
# [2025-12-29 14:50:01 UTC] OK: pms-worker-v2 already attached to bccg4gs4o4kgsowocw08wkw4
# [2025-12-29 14:50:01 UTC] ====== Check Complete ======
```

**Step 4: Verify network attachment persists**

```bash
# Check backend networks
docker inspect pms-backend | grep -A 10 '"Networks"'

# Check worker networks
docker inspect pms-worker-v2 | grep -A 10 '"Networks"'

# Expected: Both "coolify" and "bccg4gs4o4kgsowocw08wkw4" networks
```

---

#### Customization

**Find your Supabase network ID:**

```bash
# Method 1: List all networks
docker network ls | grep supabase

# Method 2: Inspect Supabase DB container
docker inspect supabase-db | grep -A 5 '"Networks"'

# Update script with your network ID:
# Edit SUPABASE_NETWORK="your-network-id" in script
```

**Add more containers to monitor:**

```bash
# Edit /usr/local/bin/pms_ensure_supabase_net.sh
# Change CONTAINERS array:
CONTAINERS=("pms-backend" "pms-worker-v2" "your-other-service")
```

---

#### Troubleshooting

**Script not running:**
```bash
# Check cron daemon
systemctl status cron || systemctl status crond

# Check cron.d file permissions (must be 644)
ls -la /etc/cron.d/pms_ensure_supabase_net

# Check script permissions (must be executable)
ls -la /usr/local/bin/pms_ensure_supabase_net.sh

# Check cron logs (SystemD journal)
journalctl -u cron -f
```

**No log output:**
```bash
# Ensure log directory is writable
touch /var/log/pms_ensure_supabase_net.log
chmod 644 /var/log/pms_ensure_supabase_net.log

# Run script manually to see output
/usr/local/bin/pms_ensure_supabase_net.sh
```

**Container keeps getting detached:**
```bash
# Verify Coolify network config
# Coolify Dashboard → pms-backend → Settings → Networks
# Ensure "bccg4gs4o4kgsowocw08wkw4" is selected

# Check if Coolify is fighting with cron (check timestamps)
tail -f /var/log/pms_ensure_supabase_net.log
# If you see "FIXING" messages every 2 minutes → Coolify may be removing network
```

---

#### Security Note

**Caution:** This script requires root access on the host server and uses the Docker socket. This is acceptable for single-server ops environments but should be carefully reviewed for multi-tenant or high-security deployments.

**Alternative approaches for more secure environments:**
- Use Coolify API to trigger redeploy with network config
- Use Docker Swarm or Kubernetes for network management
- Implement network checks in application health probes
- Use Docker events API to trigger network reattachment (reactive instead of polling)

---

### Optional: Cleanup Stale Sync Logs

**Problem:** Sync logs may remain in `running` status after previous outages or worker crashes.

**Solution:** Run this SQL snippet to mark stale logs as `failed`:

```sql
-- Mark sync logs stuck in "running" status for > 1 hour as failed
UPDATE channel_sync_logs
SET
    status = 'failed',
    error = 'Task timed out or worker crashed (auto-cleaned)',
    updated_at = NOW()
WHERE
    status = 'running'
    AND created_at < NOW() - INTERVAL '1 hour';

-- Check affected rows
SELECT COUNT(*)
FROM channel_sync_logs
WHERE status = 'failed' AND error LIKE '%auto-cleaned%';
```

**When to run:**
- After resolving worker outages
- Before investigating sync issues (to clear old noise)
- As part of regular maintenance (monthly)

**Caution:** Review logs before cleaning to ensure you're not cancelling legitimate long-running tasks.

---

## Deploy Gating (Docs-Only Change Detection)

### Overview

**Problem:** Docs-only commits (e.g., `*.md`, `docs/**`) currently trigger full container rebuild + redeploy, causing unnecessary downtime and duplicate startup signatures.

**Solution:** Use `backend/scripts/ops/deploy_should_run.sh` to classify changes as docs-only vs code/config, enabling CI/CD to skip deploys for non-functional changes.

**Ticket:** See `backend/docs/ops/tickets/2026-01-04_deploy_gating_docs_only.md`

---

### How It Works

```bash
# Script classifies git changes
./scripts/ops/deploy_should_run.sh HEAD~1..HEAD

# Exit codes:
#   0 = Needs deploy (code/config changes detected)
#   1 = Skip deploy (docs-only changes detected)
#   2 = Error (invalid git range, not a git repo)
```

**Classification Rules:**

**Docs-only paths** (skip deploy):
- `*.md` (Markdown files)
- `docs/**` (Documentation directories)
- `*.txt` (Text files, EXCEPT `requirements.txt`)
- `.gitignore`, `LICENSE`
- `scripts/ops/deploy_should_run.sh` (Deploy classifier itself - tooling)
- `scripts/ops/deploy_gate.sh` (Deploy wrapper - tooling)

**Always deploy paths** (proceed with deploy):
- `app/**` (Python application code)
- `requirements.txt` (Python dependencies)
- `Dockerfile`, `docker-compose*.yml` (Container config)
- `alembic/**` (Database migrations)
- `tests/**` (Test code)
- `.env*` (Environment config)
- `scripts/**` (Operational scripts, EXCEPT `deploy_should_run.sh` and `deploy_gate.sh`)
- Any other files not in docs-only category

**Note:** Changes to `ops/deploy_should_run.sh` and `ops/deploy_gate.sh` are treated as tooling and do not require app deploy.

---

### CI/CD Integration Examples

#### CI Pipeline Example 1

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need full history for git diff

      - name: Check if deploy needed
        id: deploy_gate
        run: |
          if ./backend/scripts/ops/deploy_should_run.sh ${{ github.event.before }}..${{ github.sha }}; then
            echo "should_deploy=true" >> $GITHUB_OUTPUT
          else
            echo "should_deploy=false" >> $GITHUB_OUTPUT
          fi

      - name: Build and deploy
        if: steps.deploy_gate.outputs.should_deploy == 'true'
        run: |
          docker build -t myapp backend/
          docker push myapp
```

#### CI Pipeline Example 2

```yaml
deploy:
  stage: deploy
  script:
    - ./backend/scripts/ops/deploy_should_run.sh $CI_COMMIT_BEFORE_SHA..$CI_COMMIT_SHA
    - docker build -t myapp backend/
    - docker push myapp
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
  only:
    - main
```

---

### Manual Testing

```bash
# Test with last commit
cd backend
./scripts/ops/deploy_should_run.sh HEAD~1..HEAD

# Test with specific commit range
./scripts/ops/deploy_should_run.sh abc123..def456

# Example output (docs-only):
# Changed files in range HEAD~1..HEAD:
#   - docs/ops/runbook.md
#
#   [DOCS] docs/ops/runbook.md
#
# ✅ Classification: DOCS-ONLY
# Action: Skip deploy (no container rebuild needed)
# Exit code: 1

# Example output (needs deploy):
# Changed files in range HEAD~1..HEAD:
#   - app/core/database.py
#   - docs/ops/runbook.md
#
#   [DEPLOY] app/core/database.py (Application code)
#   [DOCS] docs/ops/runbook.md
#
# 🚀 Classification: NEEDS DEPLOY
# Action: Proceed with deploy (code/config changes detected)
# Exit code: 0
```

---

### Benefits

1. **Reduced downtime**: Documentation changes no longer trigger container replacement
2. **Fewer duplicate startup signatures**: Avoid Case A (container replace) for docs commits
3. **Faster feedback**: Docs contributors see changes merged without waiting for deploy
4. **Cost savings**: Skip unnecessary image builds/pushes/pulls

---

### Deployment Runner Wrapper (Enforcement)

**Execution Location:** HOST-SERVER-TERMINAL (deployment automation context)

**Script:** `backend/scripts/ops/deploy_gate.sh`

**Purpose:** Vendor-neutral wrapper for deployment runners to gate container rebuild/recreate operations based on change classification.

**Usage:**
```bash
# Explicit commit range
./scripts/ops/deploy_gate.sh OLD_COMMIT NEW_COMMIT

# Auto-infer from SOURCE_COMMIT env var
SOURCE_COMMIT=abc123 ./scripts/ops/deploy_gate.sh

# Auto-infer from HEAD~1..HEAD (last commit)
./scripts/ops/deploy_gate.sh
```

**Output Format (Machine-Readable):**
```
DEPLOY=1 reason="code/config changes detected" old=abc123 new=def456
DEPLOY=0 reason="docs-only changes" old=abc123 new=def456
DEPLOY=1 reason="error: ... (fail-open mode)" old=unknown new=unknown
```

**Exit Codes:**
- `0` = Proceed with deploy (code/config changes OR fail-open error)
- `1` = Skip deploy (docs-only changes OR fail-closed error)
- `2` = Critical error (git unavailable, not a repo)

**Fail-Safe Behavior:**

Use `DEPLOY_GATE_FAIL_MODE` environment variable to control error handling:

- **`open`** (default, recommended): On error, proceed with deploy (exit 0)
  - Rationale: Transient issues shouldn't block legitimate deployments
  - Use case: Production environments where availability > optimization

- **`closed`** (strict): On error, skip deploy (exit 1)
  - Rationale: Maximum protection against unnecessary deployments
  - Use case: Staging environments, cost-sensitive workloads

**Integration Pattern:**

```bash
# Deployment runner pseudocode
if ./backend/scripts/ops/deploy_gate.sh "$OLD" "$NEW"; then
  echo "Proceeding with container rebuild"
  # Build image
  # Push to registry
  # Replace/recreate container
else
  echo "Skipping deployment (docs-only changes)"
  # No container operations
fi
```

**Auto-Inference Logic:**

1. If `OLD_COMMIT` and `NEW_COMMIT` arguments provided: Use them directly
2. If `SOURCE_COMMIT` env var is set: Use `SOURCE_COMMIT..HEAD`
3. Otherwise: Use `HEAD~1..HEAD` (last commit only)

**Example Scenarios:**

```bash
# Scenario 1: Explicit range (deployment platform provides commit range)
./scripts/ops/deploy_gate.sh f936bda 12cbe9f
# Output: DEPLOY=1 reason="code/config changes detected" old=f936bda new=12cbe9f
# Exit: 0 (proceed)

# Scenario 2: SOURCE_COMMIT env var (platform sets this)
SOURCE_COMMIT=f936bda ./scripts/ops/deploy_gate.sh
# Output: DEPLOY=0 reason="docs-only changes" old=f936bda new=HEAD
# Exit: 1 (skip)

# Scenario 3: Fail-closed mode (strict)
DEPLOY_GATE_FAIL_MODE=closed ./scripts/ops/deploy_gate.sh invalid_ref HEAD
# Output: DEPLOY=0 reason="error: old commit not found: invalid_ref (fail-closed mode)" old=unknown new=unknown
# Exit: 1 (skip on error)

# Scenario 4: Fail-open mode (default)
./scripts/ops/deploy_gate.sh invalid_ref HEAD
# Output: DEPLOY=1 reason="error: old commit not found: invalid_ref (fail-open mode)" old=unknown new=unknown
# Exit: 0 (proceed on error)
```

**Safety Notes:**

- This script is **read-only** (only classifies changes)
- **NEVER** triggers container operations directly
- Safe to run multiple times (idempotent)
- No side effects on repository or containers

**Recommended Default:** Fail-open mode (`DEPLOY_GATE_FAIL_MODE=open`) to avoid blocking deployments due to transient errors.

---

### Phase-1 vs Phase-2

**Phase-1** (Current):
- Helper script exists (`deploy_should_run.sh`)
- Enforcement wrapper exists (`deploy_gate.sh`)
- Documentation provided
- CI/CD integration examples available
- No enforcement in actual pipelines yet (manual opt-in)

**Phase-2** (Future):
- Integrate script into actual CI/CD pipeline
- Add force-deploy override flag
- Monitor deployment frequency reduction
- Add metrics (deploy count, docs-only commit %)

---

## Network Attachment at Create-Time (Docker)

### Overview

**Problem:** PMS backend container currently lacks network connectivity at create-time, requiring a post-create restart by host automation to establish connectivity. This causes duplicate startup signatures (Case B).

**Solution:** Attach network at `docker run` time using `--network` flag (or equivalent in Docker Compose, Kubernetes, etc.), eliminating the need for post-create restarts.

**Ticket:** See `backend/docs/ops/tickets/2026-01-04_network_attach_create_time.md`

---

### Current vs Desired Behavior

**Current** (Network attached AFTER create):
```bash
docker run --name pms-backend ghcr.io/org/pms-backend:latest
  → Container starts (PID=1, generation=1)
  → No network connectivity
  → DB connection fails (DNS timeout)
  → App enters degraded mode
  → Host timer detects missing network
  → docker restart pms-backend  # ← Creates duplicate startup
  → Network now available
  → DB connection succeeds (new PID=1, generation=1 again)
```

**Desired** (Network attached AT create):
```bash
docker run --name pms-backend --network pms-network ghcr.io/org/pms-backend:latest
  → Container starts (PID=1, generation=1)
  → Network connectivity ALREADY available
  → DB connection succeeds immediately
  → App enters ready mode (no degraded mode)
  → Host timer becomes optional safety net (no restart)
```

---

### Implementation Examples

#### Docker CLI

**Before:**
```bash
docker run -d \
  --name pms-backend \
  --env-file .env \
  ghcr.io/org/pms-backend:latest
```

**After:**
```bash
docker run -d \
  --name pms-backend \
  --network pms-network \
  --env-file .env \
  ghcr.io/org/pms-backend:latest
```

#### Docker Compose

**Before:**
```yaml
services:
  backend:
    image: ghcr.io/org/pms-backend:latest
    env_file: .env
    # No networks section
```

**After:**
```yaml
services:
  backend:
    image: ghcr.io/org/pms-backend:latest
    env_file: .env
    networks:
      - pms-network

networks:
  pms-network:
    external: true  # Assumes network already exists
    # OR
    # driver: bridge  # Creates network if not exists
```

#### Kubernetes

Kubernetes automatically attaches Pod network at create-time (no action needed):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pms-backend
spec:
  containers:
  - name: backend
    image: ghcr.io/org/pms-backend:latest
  # Network attachment is automatic
```

---

### Update Host Timer Script (Safety Net)

**Before** (restart-based):
```bash
# Host timer script (HARMFUL - causes duplicate startups)
if ! docker exec pms-backend ping -c1 database 2>/dev/null; then
  echo "No connectivity, restarting container"
  docker restart pms-backend  # ← Creates duplicate startup
fi
```

**After** (attach-only):
```bash
# Host timer script (SAFE - attach without restart)
NETWORK_ATTACHED=$(docker inspect pms-backend \
  --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' \
  | grep -q pms-network && echo yes || echo no)

if [ "$NETWORK_ATTACHED" != "yes" ]; then
  echo "Network not attached, attaching now (no restart)"
  docker network connect pms-network pms-backend
else
  echo "Network already attached, no action needed"
fi
```

**Why no restart?** Docker supports live network attachment (`docker network connect`) without container restart. DNS resolution will work immediately after attachment.

---

### Benefits

1. **Single startup signature**: Eliminates Case B duplicate startups (host automation restart)
2. **Faster application readiness**: DB connection succeeds on first attempt (no degraded mode)
3. **Simpler operations**: Host timer becomes attach-only safety net, not primary mechanism
4. **Cleaner logs**: No false-positive "duplicate pool creation" alerts

---

### Verification

**Before fix** (duplicate startup):
```bash
# Check logs for multiple startups
docker logs pms-backend 2>&1 | grep -E "Started server process|pool created successfully"

# Expected (BEFORE):
# [Startup #1] Started server process [1]
# [Startup #1] Database connection pool created successfully ... pool_id=12345
# [Startup #1] Database connection pool initialization FAILED ... Degraded mode
# [Startup #2] Started server process [1]  ← Duplicate!
# [Startup #2] Database connection pool created successfully ... pool_id=67890
# [Startup #2] ✅ Database connection pool initialized
```

**After fix** (single startup):
```bash
# Check logs for single startup
docker logs pms-backend 2>&1 | grep -E "Started server process|pool created successfully"

# Expected (AFTER):
# [Startup #1] Started server process [1]
# [Startup #1] Database connection pool created successfully ... pool_id=12345
# [Startup #1] ✅ Database connection pool initialized
# [Startup #1] 🚀 PMS Backend API started successfully
```

---

### Phase-1 vs Phase-2

**Phase-1** (Current - Ticket Created):
- Ticket documents problem + solution
- Examples provided for Docker CLI, Compose, Kubernetes
- Host timer script update pattern documented
- No infrastructure changes yet

**Phase-2** (Future):
- Update actual deployment configs to include `--network` flag
- Patch host timer script to attach-only (no restart)
- Validate single startup signature in production logs
- Monitor reduction in duplicate startup events

---

## Token Validation (apikey Header)

### Symptom

- JWT token fetched successfully (200 from Supabase auth)
- API requests with `Authorization: Bearer <token>` return `401 Unauthorized`
- Logs show: `"Invalid JWT"` or `"Unauthorized"`

### Root Cause

**IMPORTANT: apikey header scope depends on which service you're calling:**

1. **Supabase Kong endpoints** (e.g., `https://sb-pms.../auth/v1/...`) require **two headers**:
   - `Authorization: Bearer <jwt>`
   - `apikey: <anon_key>`

2. **PMS Backend API** (e.g., `https://api.fewo.../api/v1/...`) requires **only**:
   - `Authorization: Bearer <jwt>`
   - **NO apikey header needed**

**Why does Supabase Kong require both?**
- `Authorization` header contains user's JWT (specific user identity)
- `apikey` header contains project's anon key (project identification for rate limiting/routing)

**Why doesn't PMS Backend need apikey?**
- PMS Backend validates JWT directly using the JWT_SECRET
- No Kong gateway in front of PMS Backend
- apikey is only needed for Supabase services

### Verify

```bash
# Test Supabase Kong endpoint (requires both headers)
# Example: Fetch current user profile
curl -X GET "https://sb-pms.kolibri-visions.de/auth/v1/user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "apikey: $ANON_KEY"
# Returns: 200 OK (user profile)

# Test without apikey (FAILS on Kong)
curl -X GET "https://sb-pms.kolibri-visions.de/auth/v1/user" \
  -H "Authorization: Bearer $TOKEN"
# Returns: 401 Unauthorized

# Test PMS Backend API (only Authorization needed)
curl -X GET "https://api.fewo.kolibri-visions.de/api/v1/properties?limit=1" \
  -H "Authorization: Bearer $TOKEN"
# Returns: 200 OK (no apikey needed)
```

### Fix

**For Supabase Kong API Clients:**

When calling Supabase services (auth, storage, etc.), include both headers:

```python
# Python example - Supabase Kong endpoint
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "apikey": anon_key,  # Required for Kong
    "Content-Type": "application/json"
}
response = requests.get(f"{supabase_url}/auth/v1/user", headers=headers)
```

**For PMS Backend API Clients:**

When calling PMS Backend, only Authorization header is needed:

```python
# Python example - PMS Backend API
headers = {
    "Authorization": f"Bearer {jwt_token}",
    # NO apikey needed
    "Content-Type": "application/json"
}
response = requests.get(f"{api_url}/api/v1/properties", headers=headers)
```

**For Smoke Scripts:**

Our smoke scripts call both:
- Supabase Kong for auth (`fetch_token()` includes apikey)
- PMS Backend API for tests (only Authorization header)

### Prevention

- Document apikey requirement in API docs
- Add example requests showing both headers
- Test authentication flow in CI/CD

---

## Fresh JWT (Supabase)

### Quick Token Generation

Use the `get_fresh_token.sh` helper script to obtain Supabase JWT tokens for testing, debugging, or manual API calls:

```bash
# Get token to variable
TOKEN="$(./backend/scripts/get_fresh_token.sh)"

# Export to environment
source <(./backend/scripts/get_fresh_token.sh --export)

# Verify token metadata
./backend/scripts/get_fresh_token.sh --check

# Test token against /auth/v1/user
./backend/scripts/get_fresh_token.sh --user
```

**Required environment variables:**
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SB_EMAIL` - User email for authentication
- `SB_PASSWORD` - User password for authentication
- `SB_URL` (optional) - Supabase URL (defaults to https://sb-pms.kolibri-visions.de)

**Exit codes:**
- `0` - Success
- `1` - Missing required environment variables
- `2` - Authentication failed (invalid credentials)
- `3` - Empty or invalid JSON response
- `4` - Token verification failed (--user flag)

For detailed usage, integration examples, and troubleshooting, see **[backend/scripts/README.md - Get Fresh JWT Token](../scripts/README.md#get-fresh-jwt-token-get_fresh_tokensh)**.

---

## CORS Errors (Admin Console Blocked)

### Symptom

- Admin UI at `https://admin.fewo.kolibri-visions.de` shows CORS error in browser console
- Browser error: `Access to fetch at 'https://api.fewo.kolibri-visions.de/...' has been blocked by CORS policy`
- Preflight request (OPTIONS) fails with missing `Access-Control-Allow-Origin` header
- API returns 403 or connection refused for cross-origin requests

### Root Cause

CORS (Cross-Origin Resource Sharing) middleware not configured to allow admin console origin:
- Default CORS origins only include localhost (development)
- Production domains not added to `ALLOWED_ORIGINS` environment variable
- Missing `Authorization` header in allowed headers (rare, default allows all)

### Verify

Check current CORS configuration:

```bash
# Check environment variable on backend container
docker exec pms-backend env | grep ALLOWED_ORIGINS
# Should show: ALLOWED_ORIGINS=https://admin.fewo.kolibri-visions.de,https://fewo.kolibri-visions.de,...

# Or check backend logs on startup for CORS origins
docker logs pms-backend | grep -i cors
```

Test CORS preflight manually:

```bash
# Send OPTIONS preflight request
curl -X OPTIONS https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Origin: https://admin.fewo.kolibri-visions.de" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  -v

# Should return:
# Access-Control-Allow-Origin: https://admin.fewo.kolibri-visions.de
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH
# Access-Control-Allow-Headers: *
```

### Fix

**Option 1: Set Environment Variable** (Recommended)

Add `ALLOWED_ORIGINS` to backend environment:

```bash
# In Coolify or deployment config
ALLOWED_ORIGINS=https://admin.fewo.kolibri-visions.de,https://fewo.kolibri-visions.de,http://localhost:3000
```

Restart backend:

```bash
docker restart pms-backend
```

**Option 2: Update Default in Code** (Already Done)

The default in `backend/app/core/config.py` now includes:
- `https://admin.fewo.kolibri-visions.de` (admin console)
- `https://fewo.kolibri-visions.de` (public site)
- `http://localhost:3000` (local dev)

If env var is not set, these defaults will be used.

### Prevention

- Always include admin and frontend origins in `ALLOWED_ORIGINS`
- Test CORS with `curl -X OPTIONS` before deploying frontend changes
- Document required origins in deployment checklist

---

## Booking Status Validation Error (500)

### Symptom

- Admin UI shows "Failed to fetch" when viewing booking details
- Browser console shows: `GET /api/v1/bookings/{id}` returns HTTP 500
- Backend logs show: `ResponseValidationError` with `literal_error` on `response.status`
- Error message: `Input should be 'inquiry', 'pending', 'confirmed', ... (value='requested')`
- CORS headers missing on 500 response (FastAPI behavior)

### Root Cause

Database contains booking status values (e.g., `'requested'`, `'under_review'`) that are not in the `BookingStatus` Literal type definition in `backend/app/schemas/bookings.py`.

**Why this happens:**
- Booking request workflow creates bookings with status `'requested'`
- Schema Literal was not updated when new statuses were added to database
- Pydantic validation fails when serializing response, causing 500 before CORS middleware runs

### Verify

Check backend logs for validation error:

```bash
docker logs pms-backend | grep -A 5 "ResponseValidationError"
# Look for: "literal_error" on "response.status"
# Input value causing error: 'requested' or 'under_review'
```

Test booking detail endpoint:

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export TOKEN="..."  # valid JWT token
export BOOKING_ID="..."  # booking ID with 'requested' status

curl -k -sS -i -H "Authorization: Bearer $TOKEN" "$API_BASE_URL/api/v1/bookings/$BOOKING_ID" | head -20
# Expected before fix: HTTP 500, no CORS headers
# Expected after fix: HTTP 200, booking details with status='requested'
```

Check database for affected bookings:

```bash
# Connect to database
docker exec -it <supabase-db-container> psql -U postgres

# Find bookings with non-standard statuses
SELECT id, status, created_at FROM bookings WHERE status NOT IN ('inquiry', 'pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled', 'declined', 'no_show');
```

### Fix

**Solution:** Extend `BookingStatus` Literal in `backend/app/schemas/bookings.py` to include all valid database statuses.

**Code Change:**

```python
# backend/app/schemas/bookings.py (line ~35)

# Before:
BookingStatus = Literal[
    "inquiry", "pending", "confirmed", "checked_in",
    "checked_out", "cancelled", "declined", "no_show"
]

# After:
BookingStatus = Literal[
    "requested", "under_review",  # Booking request lifecycle
    "inquiry", "pending", "confirmed", "checked_in",
    "checked_out", "cancelled", "declined", "no_show"
]
```

**Deploy:**

```bash
# Commit fix
git add backend/app/schemas/bookings.py backend/tests/unit/test_booking_schemas.py
git commit -m "fix: allow booking status 'requested' in API responses"
git push origin main

# Verify deploy
curl -s "https://api.fewo.kolibri-visions.de/api/v1/ops/version" | jq -r .source_commit
```

### Test

After deploy, verify booking detail endpoint returns 200:

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export TOKEN="..."
export BOOKING_ID="..."

curl -k -sS -i -H "Authorization: Bearer $TOKEN" "$API_BASE_URL/api/v1/bookings/$BOOKING_ID" | head -30
# Expected: HTTP 200, body includes "status": "requested"
```

### Prevention

- When adding new booking statuses to database, update `BookingStatus` Literal in schemas
- Add unit tests for new status values in `backend/tests/unit/test_booking_schemas.py`
- Use database migrations to document valid status values with CHECK constraints

### PROD Verified (2026-01-07)

**Deployed Commit:** cb8da7f18b4fb19f9d68908afcaf52c8f8ca4645

**Verification Evidence:**
```bash
# HOST-SERVER-TERMINAL
export API_BASE_URL="https://api.fewo.kolibri-visions.de"

# Verify deployed commit
curl -s "$API_BASE_URL/api/v1/ops/version" | jq -r .source_commit
# Output: cb8da7f18b4fb19f9d68908afcaf52c8f8ca4645

# Verify booking with status='requested' returns 200
curl -k -sS -i -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/bookings/de5aac06-486e-4c22-a6cf-0c7708d603d1" | head -20
# Output: HTTP/2 200
# Body includes: "status":"requested"

# Verify CORS headers present
curl -sS -i -H "Origin: https://admin.fewo.kolibri-visions.de" \
  "$API_BASE_URL/api/v1/branding" | grep -i access-control-allow-origin
# Output: access-control-allow-origin: https://admin.fewo.kolibri-visions.de
```

**Backend Started At:** 2026-01-07T17:49:04.742363+00:00

**Result:** ✅ Fix verified in production - booking detail endpoint returns 200 for status='requested'

---

## Schema Drift

### Symptom

- API returns `503 Service Unavailable`
- Logs show: `"Schema not installed"` or `"Schema out of date"` or `"Relation does not exist"`
- Database is reachable (DNS resolves, pool created), but queries fail

### Root Cause

Database schema is out of sync with application code:
- Migrations not applied after deploy
- Database restored from old backup
- Manual schema changes not tracked in migrations

### Verify

```bash
# SSH to host server
ssh root@your-host

# Check migration status (if using Alembic)
docker exec $(docker ps -q -f name=pms) alembic current
# Expected: Latest migration hash

# Check if tables exist
docker exec $(docker ps -q -f name=pms) psql "$DATABASE_URL" -c "\dt"
# Expected: List of tables (properties, bookings, availability_blocks, etc.)

# Check Supabase migrations (if using Supabase CLI)
docker exec $(docker ps -q -f name=supabase) supabase migration list
# Expected: All migrations marked as applied
```

### Fix

**Option 1: Apply Missing Migrations (Recommended)**

```bash
# If using Alembic
docker exec $(docker ps -q -f name=pms) alembic upgrade head

# If using Supabase CLI
docker exec $(docker ps -q -f name=supabase) supabase migration up

# Restart application
docker restart $(docker ps -q -f name=pms)
```

**Option 2: Manual Schema Inspection**

```bash
# Connect to database
docker exec -it $(docker ps -q -f name=supabase) psql -U postgres -d postgres

# Check if critical tables exist
\dt properties
\dt bookings
\dt availability_blocks

# If missing, check migration files in /app/migrations/ or supabase/migrations/
```

**Option 3: Full Database Reset (DESTRUCTIVE - Dev/Staging Only)**

```bash
# DANGER: This deletes all data
docker exec $(docker ps -q -f name=supabase) supabase db reset

# Re-apply migrations
docker exec $(docker ps -q -f name=pms) alembic upgrade head
```

### Prevention

- Include migration check in deployment pipeline
- Version migrations with semantic versioning
- Test migrations on staging before production
- Document schema changes in migration files

### Channel Manager Sync Logs Migration

**Migration File**: `supabase/migrations/20251227000000_create_channel_sync_logs.sql`

**When to Apply**: Required for Channel Manager sync log persistence (replaces stub/dummy data)

**Symptom if Missing**:
- GET `/api/v1/channel-connections/{id}/sync-logs` returns `503 Service Unavailable`
- Error message: `"Channel sync logs schema not installed (missing table: channel_sync_logs)"`
- Logs show: `UndefinedTableError: relation "channel_sync_logs" does not exist`

**Apply Migration**:

```bash
# Option 1: Using Supabase CLI
cd supabase/migrations
docker exec $(docker ps -q -f name=supabase) supabase migration up

# Option 2: Manual SQL execution
docker exec -it $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  < supabase/migrations/20251227000000_create_channel_sync_logs.sql

# Option 3: Via Supabase Dashboard
# Navigate to: SQL Editor > Paste migration content > Run
```

**Verify Installation**:

```bash
# Check table exists
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  -c "\dt channel_sync_logs"

# Expected output:
#  Schema |        Name          | Type  | Owner
# --------+----------------------+-------+-------
#  public | channel_sync_logs    | table | postgres

# Check indexes
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  -c "\d channel_sync_logs"

# Expected: 4 indexes (connection_id, task_id, tenant_id, status)
```

**What This Migration Does**:
- Creates `channel_sync_logs` table with JSONB details column
- Adds indexes for fast queries (connection_id, task_id, tenant_id, status)
- Sets up CHECK constraints for operation_type, direction, status
- Conditionally adds FK to `channel_connections` (if table exists)
- Enables persistent tracking of Channel Manager sync operations

**Rollback** (if needed):

```bash
docker exec -it $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  -c "DROP TABLE IF EXISTS public.channel_sync_logs CASCADE;"
```

### Guests Metrics Columns Migration

**Migration File**: `supabase/migrations/20260103120000_ensure_guests_metrics_columns.sql`

**When to Apply**: Required when existing guests table is missing metrics columns

**Symptom if Missing**:
- API returns `503 Service Unavailable` on guest operations
- Error message: `"column total_bookings of relation guests does not exist"`
- Logs show: `UndefinedColumn: column "total_bookings" does not exist`

**Apply Migration**:

```bash
# Using Supabase CLI
docker exec $(docker ps -q -f name=supabase) supabase migration up

# Or manual SQL execution
docker exec -it $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  < supabase/migrations/20260103120000_ensure_guests_metrics_columns.sql
```

**Verify Installation**:

```bash
# Check columns exist
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  -c "\d guests"

# Expected columns: total_bookings, total_spent, last_booking_at
```

**What This Migration Does**:
- Adds `total_bookings` column (INTEGER, default 0) if missing
- Adds `total_spent` column (NUMERIC(12,2), default 0) if missing
- Adds `last_booking_at` column (TIMESTAMPTZ NULL) if missing
- Creates index on `last_booking_at` for recent guest activity queries
- Idempotent: safe to run multiple times (uses information_schema checks)

### Guests Booking Timeline Columns Migration

**Migration File**: `supabase/migrations/20260103123000_ensure_guests_booking_timeline_columns.sql`

**When to Apply**: Required when existing guests table is missing booking timeline columns

**Symptom if Missing**:
- API returns `503 Service Unavailable` on guest operations or Phase 20 smoke tests
- Error message: `"column first_booking_at of relation guests does not exist"`
- Logs show: `UndefinedColumn: column "first_booking_at" does not exist`

**Apply Migration**:

```bash
# Using Supabase CLI
docker exec $(docker ps -q -f name=supabase) supabase migration up

# Or manual SQL execution (Supabase SQL Editor or psql)
docker exec -it $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  < supabase/migrations/20260103123000_ensure_guests_booking_timeline_columns.sql
```

**Verify Installation**:

```bash
# Check columns exist
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  -c "\d guests"

# Expected columns: first_booking_at, average_rating, updated_at, deleted_at
```

**What This Migration Does**:
- Adds `first_booking_at` column (TIMESTAMPTZ NULL) if missing
- Adds `average_rating` column (NUMERIC(3,2) NULL) if missing
- Adds `updated_at` column (TIMESTAMPTZ NOT NULL DEFAULT now()) if missing
- Adds `deleted_at` column (TIMESTAMPTZ NULL) for soft delete support
- Creates indexes on `first_booking_at` and `deleted_at` for performance
- Idempotent: safe to run multiple times (uses information_schema checks)

---

## DB Migrations (Production)

**Date Added:** 2026-01-03 (Phase 21A)

**Purpose:** Apply Supabase SQL migrations to production database in a safe, idempotent manner.

### Migration Runner Script

**Location:** `backend/scripts/ops/apply_supabase_migrations.sh`

**Features:**
- Tracks applied migrations in `public.pms_schema_migrations` table
- Only applies pending migrations (idempotent)
- Dry-run mode (preview without applying)
- Status mode (show applied/pending summary)
- Transaction-based (each migration runs in a transaction)
- Production safety guard (requires explicit confirmation)

### Common Use Cases

#### 1. Check Migration Status

```bash
# SSH to host server
ssh root@your-host

# Navigate to repo
cd /data/repos/pms-webapp

# Check status
bash backend/scripts/ops/apply_supabase_migrations.sh --status
```

**Expected Output:**
```
INFO: Latest applied: 20260103123000_ensure_guests_booking_timeline_columns.sql
INFO: Applied migrations: 15
INFO: Pending migrations: 0
✓ All migrations applied - database schema is up to date
```

#### 2. Preview Pending Migrations (Dry-Run)

```bash
# Show what would be applied without executing
bash backend/scripts/ops/apply_supabase_migrations.sh --dry-run
```

**Expected Output:**
```
INFO: 2 pending migration(s):
  - 20260103140000_add_new_feature.sql
  - 20260103150000_update_constraints.sql

INFO: Dry-run mode - no migrations will be applied
```

#### 3. Apply Pending Migrations

```bash
# Set production confirmation flag
export CONFIRM_PROD=1

# Apply migrations
bash backend/scripts/ops/apply_supabase_migrations.sh
```

**Expected Output:**
```
WARNING: Production mode confirmed (CONFIRM_PROD=1)
✓ Database connection OK
✓ Tracking table ready: public.pms_schema_migrations

---
INFO: Applying: 20260103140000_add_new_feature.sql
✓ Applied: 20260103140000_add_new_feature.sql
---
INFO: Applying: 20260103150000_update_constraints.sql
✓ Applied: 20260103150000_update_constraints.sql

✓ All pending migrations applied successfully
```

### Environment Variables

**Option 1: DATABASE_URL (Recommended)**
```bash
export DATABASE_URL="postgresql://postgres:password@host:port/database"
bash backend/scripts/ops/apply_supabase_migrations.sh --status
```

**Option 2: Individual PG* Variables**
```bash
export PGHOST="your-host.supabase.co"
export PGPORT="5432"
export PGUSER="postgres"
export PGPASSWORD="your-password"
export PGDATABASE="postgres"
bash backend/scripts/ops/apply_supabase_migrations.sh --status
```

### Production Safety Guards

**Required Confirmation:**
```bash
# Without confirmation → Error
bash backend/scripts/ops/apply_supabase_migrations.sh
# ERROR: Production safety guard: set CONFIRM_PROD=1 to proceed

# With confirmation → Proceeds
export CONFIRM_PROD=1
bash backend/scripts/ops/apply_supabase_migrations.sh
```

**Dev/Staging Override:**
```bash
# Skip confirmation for non-production environments
export ALLOW_NON_PROD=1
bash backend/scripts/ops/apply_supabase_migrations.sh
```

### Failure Modes & Troubleshooting

#### Migration Fails Mid-Execution

**Symptom:** Script stops with error:
```
ERROR: Failed to apply: 20260103140000_add_feature.sql
ERROR: psql returned non-zero exit code
```

**Cause:** SQL syntax error, constraint violation, or missing dependencies

**Fix:**
1. Check the migration file for errors:
   ```bash
   cat supabase/migrations/20260103140000_add_feature.sql
   ```
2. Review psql error output (run migration manually for details):
   ```bash
   psql "$DATABASE_URL" -f supabase/migrations/20260103140000_add_feature.sql
   ```
3. Fix the SQL file or revert changes
4. Re-run migration script (only pending migrations will be applied)

**Important:** Failed migrations are NOT recorded in tracking table. Fix the issue and re-run.

#### "Database connection failed"

**Symptom:**
```
ERROR: Failed to connect to database
Connection: host:5432/database as user
```

**Fix:**
- Verify DATABASE_URL or PG* environment variables are set correctly
- Check network connectivity to database host
- Verify credentials are correct
- Check firewall rules allow connection from host server

#### "Migrations directory not found"

**Symptom:**
```
ERROR: Migrations directory not found: /data/repos/pms-webapp/supabase/migrations
```

**Fix:**
- Ensure you're running from repo root: `cd /data/repos/pms-webapp`
- Verify migrations directory exists: `ls -la supabase/migrations/`
- Pull latest code if directory is missing: `git pull`

### Manual Migration Verification

To verify migrations were applied correctly:

```bash
# Connect to database
psql "$DATABASE_URL"

# List applied migrations
SELECT filename, applied_at FROM public.pms_schema_migrations ORDER BY applied_at DESC LIMIT 10;

# Check specific table exists
\dt guests

# Check column exists
\d guests
```

### When to Run Migrations

**Always run after:**
- Deploying new code with schema changes
- Pulling latest code from git (check `supabase/migrations/` for new files)
- Seeing 503 errors with "schema not installed" or "schema out of date"

**Recommended workflow:**
1. Pull latest code: `git pull`
2. Check status: `bash backend/scripts/ops/apply_supabase_migrations.sh --status`
3. If pending migrations exist:
   - Preview with `--dry-run`
   - Apply with `CONFIRM_PROD=1`
4. Verify with `--status` again
5. Run smoke tests to confirm

### Migration Tracking Table Schema

```sql
CREATE TABLE public.pms_schema_migrations (
    filename TEXT PRIMARY KEY,                    -- Migration filename
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(), -- When applied
    sha256 TEXT,                                   -- File hash (integrity check)
    notes TEXT                                     -- Optional notes
);
```

**Example Data:**
```
filename                                          | applied_at                  | sha256
--------------------------------------------------+-----------------------------+--------
20260103120000_ensure_guests_metrics_columns.sql  | 2026-01-03 10:30:00+00     | abc123...
20260103123000_ensure_guests_booking_timeline... | 2026-01-03 10:35:00+00     | def456...
```

---

## Smoke Script Pitfalls

### Symptom

Smoke script (`pms_phase23_smoke.sh`) fails with:
- `"Required environment variable not set"`
- `"Token is empty"`
- `"PID not set and could not auto-derive"`
- Bash errors: `"unbound variable"`

### Root Causes & Fixes

#### 1. Empty TOKEN (Authentication Failure)

**Cause:** Invalid credentials or Supabase unreachable.

**Fix:**
```bash
# Verify credentials (do NOT print PASSWORD or full ANON_KEY)
echo "SB_URL: $SB_URL"
echo "ANON_KEY length: ${#ANON_KEY}"
echo "EMAIL: $EMAIL"

# Test auth manually
curl -X POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"'$EMAIL'","password":"'$PASSWORD'"}'

# Expected: JSON with "access_token" field
# If error: check credentials, network, Supabase status
```

#### 2. Empty PID (Auto-Derive Failed)

**Cause:** No properties exist, or properties endpoint returned empty items.

**Fix:**
```bash
# Check if properties exist
curl -X GET "$API/api/v1/properties?limit=1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "apikey: $ANON_KEY"

# Expected: {"items": [{"uuid": "...", ...}], ...}
# If empty: create a test property first

# Override PID explicitly
export PID="your-property-uuid"
bash scripts/pms_phase23_smoke.sh
```

#### 3. Bash `set -u` (Unbound Variable Errors)

**Cause:** Script uses `set -u` (strict mode) - accessing undefined variables causes immediate exit.

**Fix:**
```bash
# Always use ${VAR:-default} syntax
export PID="${PID:-}"  # Empty string if not set
export API="${API:-https://api.fewo.kolibri-visions.de}"

# Or export all required vars before running
export SB_URL="..."
export ANON_KEY="..."
export EMAIL="..."
export PASSWORD="..."
bash scripts/pms_phase23_smoke.sh
```

#### 4. Running on Host vs Container

**Problem:** Script expects `/app/scripts/` paths (container), but you're on host.

**Fix:**

**Run in Container (Recommended):**
```bash
# SSH to host
ssh root@your-host

# Run in container terminal (via Coolify dashboard)
# OR via docker exec:
docker exec -it $(docker ps -q -f name=pms) bash

# Inside container:
export ENV_FILE=/root/pms_env.sh
bash /app/scripts/pms_phase23_smoke.sh
```

**Run on Host (Alternative):**
```bash
# SSH to host
ssh root@your-host

# Use docker exec one-liner
docker exec $(docker ps -q -f name=pms) bash -c '
export ENV_FILE=/root/pms_env.sh
bash /app/scripts/pms_phase23_smoke.sh
'
```

#### 5. Environment File Not Found

**Cause:** ENV_FILE path is wrong (host vs container filesystem).

**Fix:**
```bash
# Check if file exists in container
docker exec $(docker ps -q -f name=pms) ls -la /root/pms_env.sh

# If missing, create it:
cat > /tmp/pms_env.sh <<'ENVEOF'
export SB_URL="https://your-project.supabase.co"
export ANON_KEY="eyJhbGc..."
export EMAIL="admin@example.com"
export PASSWORD="your-password"
export API="https://api.fewo.kolibri-visions.de"
ENVEOF

# Copy to container
docker cp /tmp/pms_env.sh $(docker ps -q -f name=pms):/root/pms_env.sh

# Run script
docker exec $(docker ps -q -f name=pms) bash -c '
export ENV_FILE=/root/pms_env.sh
bash /app/scripts/pms_phase23_smoke.sh
'
```

### Prevention

- Document required environment variables clearly
- Provide example env file template
- Add validation at script start (require_env)
- Test scripts in CI/CD pipeline

---

## Optional: Availability Block Conflict Test

### Overview

The Phase 23 smoke script includes an **opt-in** test for availability block/booking conflict validation. This test:
- Creates an availability block for a future window (today + 30 days, 3 days duration)
- Verifies the block appears in `/api/v1/availability` response
- Attempts to create an overlapping booking (expects 409 conflict)
- Always cleans up the block (via trap, even on failure)

**Use Case:** Validate inventory conflict detection after schema changes or deployment.

**Safety:** Future window (30 days out) avoids interfering with real operations.

### Enable the Test

Set `AVAIL_BLOCK_TEST=true` to enable:

```bash
# SSH to host server
ssh root@your-host

# Run in container with block test enabled
docker exec $(docker ps -q -f name=pms) bash -c '
export ENV_FILE=/root/pms_env.sh
export AVAIL_BLOCK_TEST=true
bash /app/scripts/pms_phase23_smoke.sh
'
```

**Expected Output (when enabled):**
```
ℹ️  Test 8: Availability block conflict test (opt-in via AVAIL_BLOCK_TEST=true)
ℹ️  Creating availability block: 2026-01-25 to 2026-01-28 (PID: abc-123...)
ℹ️  Block created: def-456...
ℹ️  Verifying block appears in /api/v1/availability...
ℹ️  ✓ Block found in availability response
ℹ️  Attempting to create overlapping booking (expect 409 conflict)...
ℹ️  ✓ Booking correctly rejected with 409 (conflict_type: inventory_overlap)
ℹ️  Deleting block def-456...
ℹ️  ✓ Block deleted successfully
ℹ️  ✅ PASS - Availability block conflict test complete

Summary:
  ...
  ✓ Availability block conflict test passed
```

**Expected Output (when disabled, default):**
```
ℹ️  Test 8: Availability block conflict test (opt-in via AVAIL_BLOCK_TEST=true)
⚠️  AVAIL_BLOCK_TEST not set to 'true' - skipping block conflict test
⚠️  To enable: export AVAIL_BLOCK_TEST=true

Summary:
  ...
  ⊘ Availability block conflict test skipped (AVAIL_BLOCK_TEST not enabled)
```

### Requirements

- Requires PID (uses auto-derived or explicit `export PID=...`)
- Requires JWT token (automatic via SB_URL/ANON_KEY/EMAIL/PASSWORD)
- Requires write access to `/api/v1/availability/blocks` (admin/manager role)

### What It Tests

1. **Block Creation** (`POST /api/v1/availability/blocks`)
   - Verifies block can be created for future window
   - Captures block ID for cleanup

2. **Block Visibility** (`GET /api/v1/availability`)
   - Verifies block appears in availability response
   - Checks: `kind=block`, `state=blocked`, `block_id` present
   - **Property Validation:** Returns 404 if property_id does not exist (prevents false positives from demo UUIDs)

3. **Conflict Detection** (`POST /api/v1/bookings`)
   - Verifies overlapping booking is rejected with 409
   - Checks: `conflict_type=inventory_overlap`

4. **Block Deletion** (`DELETE /api/v1/availability/blocks/{id}`)
   - Verifies block can be deleted (cleanup)
   - Trap ensures cleanup even on test failure

### Cleanup Guarantee

The test uses a bash trap to ensure cleanup:
```bash
trap cleanup_block EXIT
```

**If test fails mid-execution:**
- Block will still be deleted automatically
- No orphaned test data left in database

**Manual cleanup (if needed):**
```bash
# List blocks with reason="smoke-test"
curl -X GET "$API/api/v1/availability/blocks?reason=smoke-test" \
  -H "Authorization: Bearer $TOKEN"

# Delete specific block
curl -X DELETE "$API/api/v1/availability/blocks/<block-id>" \
  -H "Authorization: Bearer $TOKEN"
```

### When to Use

**Recommended:**
- After schema migrations affecting `availability_blocks` or `inventory_ranges`
- After deployment of conflict detection logic changes
- When validating EXCLUSION constraint behavior
- Pre-production smoke test before go-live

**Not Recommended:**
- In CI/CD pipelines (adds ~5-10s, requires write access)
- Production health checks (read-only tests preferred)
- Frequent monitoring (creates/deletes data)

### Important Notes

**Demo UUIDs vs Real Properties:**
- Some documentation examples use demo UUIDs like `550e8400-e29b-41d4-a716-446655440000`
- These may exist in `channel_connections` mocks but are NOT real properties in the database
- `GET /api/v1/availability` now returns **404 Property not found** for non-existent property_id
- This prevents false positives from smoke tests using invalid property IDs

**Smoke Script PID Validation:**
- The smoke script (`pms_phase23_smoke.sh`) now validates PID before running availability tests
- If PID is invalid (property not found), script auto-selects a valid PID from `/api/v1/properties`
- Warning displayed: `⚠️ PID invalid (Property not found). Using fallback PID=<id> from /properties`
- This ensures tests run against real properties, not demo UUIDs

**To override PID:**
```bash
export PID="<valid-property-uuid>"
bash scripts/pms_phase23_smoke.sh
```

---

## Phase 21: Inventory/Availability Production Hardening

**Date:** 2026-01-03

**Summary:** Production readiness validation for inventory/availability APIs with common gotchas documentation and operational guidance.

### What Phase 20 Proved

Phase 20 smoke tests validated core inventory mechanics:
- ✅ **Manual blocks prevent bookings**: Availability blocks correctly reject overlapping bookings with HTTP 409 `inventory_overlap`
- ✅ **Deleting blocks unblocks inventory**: Block deletion immediately frees inventory for booking
- ✅ **Cancel frees inventory**: Booking cancellation releases inventory instantly
- ✅ **Idempotent cancellation**: Canceling already-cancelled bookings returns 200 (safe retry)
- ✅ **Cancelled bookings don't prevent rebooking**: Same dates can be rebooked after cancellation
- ✅ **Race-safe concurrency**: Under concurrent requests, exactly 1 booking succeeds (201), rest rejected (409)

### Common Gotchas Checklist

#### 1. Missing Query Parameters (422 Validation Error)

**Symptom:** `GET /api/v1/availability` returns HTTP 422 with validation errors

**Cause:** `from_date` and `to_date` query parameters are required but missing

**Example Error (FastAPI/Pydantic format):**
```json
{
  "detail": [
    {"type": "missing", "loc": ["query", "from_date"], "msg": "Field required"},
    {"type": "missing", "loc": ["query", "to_date"], "msg": "Field required"}
  ]
}
```

**Example Error (PMS custom envelope):**
```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "errors": [
    {"field": "query.from_date", "message": "Field required", "type": "missing"},
    {"field": "query.to_date", "message": "Field required", "type": "missing"}
  ],
  "path": "/api/v1/availability"
}
```

**Note:** The API may return either error format. Both indicate missing required query parameters. When using curl or smoke scripts, you may see extra artifacts (HTTP headers, status lines, trailing text) mixed with the JSON response. The Phase 21 smoke script handles this by extracting JSON boundaries and falling back to raw string checks.

**Fix:** Always include both query parameters:
```bash
# Correct usage
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/availability?property_id=$PID&from_date=2026-01-10&to_date=2026-01-20"

# Incorrect (422 error)
curl -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/availability?property_id=$PID"
```

#### 2. Availability Block Overlap Returns 500 Instead of 409

**Date Added:** 2026-01-08 (Phase 21C Bugfix)

**Symptom:** `POST /api/v1/availability/blocks` with overlapping dates returns HTTP 500 Internal Server Error with `{"detail":"Failed to create availability block"}` instead of 409 Conflict (observed in Phase 21 smoke test TEST 3)

**Root Cause:** PostgreSQL EXCLUSION constraint violation (SQLSTATE 23P01 on `inventory_ranges_no_overlap`) was being raised as generic `asyncpg.PostgresError` instead of specific `asyncpg.exceptions.ExclusionViolationError`. Original exception handler only caught the specific type, causing overlap errors to fall through to generic 500 handler.

**Fix Applied:** Two-layer robust overlap detection to prevent 500 fallthrough:
- **Service layer** (`backend/app/services/availability_service.py:357-387`): Catches `asyncpg.PostgresError` and detects overlap by: `sqlstate == '23P01'` OR `constraint_name == 'inventory_ranges_no_overlap'` OR message contains `'inventory_ranges_no_overlap'` OR message contains `'exclusion constraint'`. Raises `ConflictException` (409) when detected.
- **Route layer** (`backend/app/api/routes/availability.py:321-354`): Safety net with same detection logic. Added explicit `except HTTPException: raise` to prevent generic `except Exception` from swallowing `ConflictException`. Logs sqlstate/constraint on overlap detection and exception type on unexpected errors.

**Logs for debugging (if regression occurs):**
```bash
# Capture sqlstate/constraint from backend logs (HOST-SERVER-TERMINAL)
docker logs pms-backend 2>&1 | grep -A2 "Overlap detected\|Inventory range conflict" | tail -20
# Look for: "sqlstate=23P01" or "constraint=inventory_ranges_no_overlap"
```

**Verification (HOST-SERVER-TERMINAL):**
```bash
# 1. Verify deployed commit includes fix (check /api/v1/ops/version)
curl -k -sS https://api.fewo.kolibri-visions.de/api/v1/ops/version | jq -r '.commit'
# → Should show commit hash containing this fix (post-cc42fe7)

# 2. Run Phase 21 smoke test (all 6 tests should pass, especially TEST 3 overlap → 409)
JWT_TOKEN="<admin-or-manager-token>" PID="<property-id>" ./backend/scripts/pms_availability_phase21_smoke.sh ; echo "Exit code: $?"
# → Exit code: 0 (all tests passed)
# → TEST 3: Create overlapping block → ✓ PASS: HTTP 409 - overlap correctly rejected

# 3. Manual verification (optional)
curl -k -X POST "https://api.fewo.kolibri-visions.de/api/v1/availability/blocks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"property_id":"'$PID'","start_date":"2026-02-01","end_date":"2026-02-08","reason":"Test"}' ; echo ""
# → HTTP 201 Created

curl -k -X POST "https://api.fewo.kolibri-visions.de/api/v1/availability/blocks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"property_id":"'$PID'","start_date":"2026-02-05","end_date":"2026-02-10","reason":"Overlap"}' ; echo ""
# → HTTP 409 Conflict (NOT 500) with {"error":"conflict","message":"Availability block overlaps..."}
```

**Related Endpoints:**
- `GET /api/v1/availability/blocks/{block_id}` - Retrieve single block (added in Phase 21C)
- `DELETE /api/v1/availability/blocks/{block_id}` - Delete block (existing)

**Smoke Test:** `backend/scripts/pms_availability_phase21_smoke.sh` validates all block operations including overlap detection

#### 3. Schema Drift Symptoms

**Symptom:** API returns `503 Service Unavailable` with error message `"Schema not installed"` or `"Schema out of date"`

**Common Missing Columns:**
- `guests.total_bookings`, `guests.total_spent`, `guests.last_booking_at` → Apply migration `20260103120000_ensure_guests_metrics_columns.sql`
- `guests.first_booking_at`, `guests.average_rating`, `guests.updated_at`, `guests.deleted_at` → Apply migration `20260103123000_ensure_guests_booking_timeline_columns.sql`

**What to Do:**
1. Check which column is missing from error logs
2. Apply corresponding migration via Supabase CLI or SQL Editor
3. Verify with `\d guests` in psql
4. See [Schema Drift](#schema-drift) section for full troubleshooting steps

### Minimum Production Checklist for Inventory

Before deploying inventory/availability features to production:

- [ ] **Migrations Applied**
  - Run `supabase migration list` or check migration table
  - Ensure all inventory-related migrations present (guests metrics, timeline columns, exclusion constraints)

- [ ] **Exclusion Constraint Present**
  - Verify `bookings.no_double_bookings` constraint exists
  - Check with: `\d bookings` in psql and look for `EXCLUDE USING gist` constraint
  - Migration: `20251229200517_enforce_overlap_prevention_via_exclusion.sql`

- [ ] **Smoke Scripts Pass**
  - Run `pms_phase20_final_smoke.sh` → Should complete without 503/422 errors
  - Run `pms_booking_concurrency_test.sh` → Should show exactly 1 success, rest 409
  - Run `pms_phase21_inventory_hardening_smoke.sh` → Should validate availability API contract

- [ ] **Environment Variables Configured**
  - `DATABASE_URL` set and reachable
  - `JWT_SECRET` configured for token validation
  - `ALLOWED_ORIGINS` includes admin console domain (CORS)

### What We Do Next

Phase 21 focuses on edge cases and operational robustness:

- **Back-to-Back Bookings**: Validate check-out day can be another booking's check-in (end-exclusive semantics)
- **Timezone Boundaries**: Test bookings crossing DST transitions and UTC midnight boundaries
- **Min Stay Constraints**: Enforce minimum night requirements per property/season
- **Booking Window Rules**: Validate advance booking limits (e.g., max 365 days future)
- **Availability Read Contract**: Negative tests for missing query params, malformed dates
- **Concurrency Edge Cases**: Multi-property parallel bookings, rapid cancel-rebook cycles

---

## Phase 30 — Inventory Final Validation

**Date:** 2025-12-27

**Summary:** Comprehensive validation of inventory/availability conflict detection and date semantics.

### What Was Validated

#### Test 8: Availability Block Conflict (AVAIL_BLOCK_TEST=true)
- ✅ Availability block creation (future window: 2026-01-25 to 2026-01-28)
- ✅ Block visibility in `/api/v1/availability` response
- ✅ Overlapping booking rejection with HTTP 409 `conflict_type=inventory_overlap`
- ✅ Block deletion cleanup

**Result:** PASS — Availability blocks correctly prevent overlapping bookings.

#### Test 9: Back-to-Back Booking Boundary (B2B_TEST=true)
- ✅ Free gap detection (found 2026-02-26 to 2026-03-02)
- ✅ Booking A creation (2026-02-26 to 2026-02-28, 2 nights)
- ✅ Booking B creation (2026-02-28 to 2026-03-02, check-in = A's check-out)
- ✅ Both bookings returned HTTP 201 (no boundary conflict)
- ✅ Booking cancellation cleanup via PATCH

**Result:** PASS — Confirms end-exclusive date semantics (check-out date is NOT occupied).

### How to Run Validation

**Location:** HOST-SERVER-TERMINAL

```bash
# SSH to host server
ssh root@your-host

# Load environment (contains SB_URL, ANON_KEY, EMAIL, PASSWORD, API)
source /root/pms_env.sh

# Enable opt-in tests (optional - choose one or both)
export AVAIL_BLOCK_TEST=true  # Availability block conflict test
export B2B_TEST=true          # Back-to-back booking boundary test

# Run smoke script
bash backend/scripts/pms_phase23_smoke.sh
```

**Notes:**
- Tests are **opt-in** (disabled by default)
- Tests use **future dates** (30-60+ days out) to avoid production conflicts
- Tests **clean up after themselves**:
  - Availability blocks: deleted via DELETE `/api/v1/availability/blocks/{id}`
  - Bookings: cancelled via PATCH `/api/v1/bookings/{id}` with `status=cancelled`
- Cleanup runs via trap (executes even on test failure)
- No data left behind on success or failure

### Production Impact

**Zero** — Tests create and delete temporary data in far-future date ranges.

---

## Module System Kill-Switch

**Purpose:** Emergency fallback to bypass the module mounting system if issues are detected.

### Overview

The PMS backend uses a modular monolith architecture (Phase 33B) where routers are registered and mounted via a module system. If module system issues are detected in production, the `MODULES_ENABLED` environment variable provides a kill-switch to bypass it.

**Default:** `MODULES_ENABLED=true` (module system active)

**Fallback behavior when disabled:**
- Mounts health router (core_pms)
- Mounts `/api/v1` routers: properties, bookings, availability
- Same API paths and behavior as module system
- No module validation or dependency checks

### When to Use the Kill-Switch

**Symptoms that may require kill-switch:**
- Routes appear missing (404 errors on expected endpoints)
- Module import errors in startup logs
- Circular dependency errors on startup
- Module registration failures
- Routers not mounting correctly

**DO NOT use unless:**
- Module system is confirmed broken
- Rollback to previous deployment is not possible
- Business impact requires immediate resolution

### How to Disable Module System

**Location:** Coolify Dashboard (Environment Variables)

**Steps:**
1. Open Coolify dashboard
2. Navigate to: **Applications > PMS-Webapp > Environment Variables**
3. Add or update variable:
   - Name: `MODULES_ENABLED`
   - Value: `false`
4. Click **Save**
5. **Restart** the application

**Expected Behavior:**
- Application startup logs: `"MODULES_ENABLED=false → Mounting routers via fallback"`
- Fallback mounts health + `/api/v1/properties`, `/api/v1/bookings`, `/api/v1/availability`
- Same API paths and behavior as module system
- No module validation or dependency checks

### How to Re-enable Module System

**Steps:**
1. Open Coolify dashboard
2. Navigate to: **Applications > PMS-Webapp > Environment Variables**
3. Update variable:
   - Name: `MODULES_ENABLED`
   - Value: `true` (or remove the variable - defaults to `true`)
4. Click **Save**
5. **Restart** the application

**Expected Behavior:**
- Application startup logs: `"MODULES_ENABLED=true → Mounting modules via module system"`
- Module validation runs (detects circular dependencies)
- Routers mounted via registry in dependency order

### Verification

**After changing MODULES_ENABLED:**

```bash
# SSH to host server
ssh root@your-host

# Check application logs
docker logs pms-backend --tail 50 | grep "MODULES_ENABLED"

# Expected: "MODULES_ENABLED=true →" or "MODULES_ENABLED=false →"

# Verify health endpoint
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Verify API endpoints
curl http://localhost:8000/api/v1/properties
# Expected: 200 OK or 401 Unauthorized (depends on auth)
```

### Important Notes

- **No API changes**: Both modes mount the same routers with the same prefixes and tags
- **No data loss**: Kill-switch only affects router mounting, not database or data
- **Backwards compatible**: `/docs` and `/openapi.json` show identical routes in both modes
- **Temporary measure**: After using kill-switch, investigate root cause and restore module system
- **Module system preferred**: Default mode includes dependency validation and better error detection

### Rollback Plan

If disabling the module system causes issues:
1. Set `MODULES_ENABLED=true` in Coolify
2. Restart application
3. If still broken, rollback to previous deployment

---

## Module Feature Flags

**Purpose:** Control which optional modules are loaded and exposed via API.

### Channel Manager Module

**Environment Variable:** `CHANNEL_MANAGER_ENABLED`

**Default:** `false` (disabled)

**Purpose:**
- Controls whether Channel Manager API endpoints are exposed
- Channel Manager handles OAuth credentials and platform integrations
- Disabled by default for security

**Endpoints (when enabled):**
- `/api/v1/channel-connections/*` - Channel connection management (CRUD, sync, health checks)

**⚠️ SECURITY WARNING:**

**NEVER enable CHANNEL_MANAGER_ENABLED in production unless authentication is verified.**

All Channel Manager endpoints require Bearer JWT authentication. Before enabling in production:

1. Verify authentication is enforced (without token → 401):
   ```bash
   curl -k -i https://api.fewo.kolibri-visions.de/api/v1/channel-connections/ | head
   # Expected: HTTP/1.1 401 Unauthorized (or 403 Forbidden)
   ```

2. Verify authenticated access works (with token → 200):
   ```bash
   TOKEN="<valid-jwt-token>"
   curl -k -i https://api.fewo.kolibri-visions.de/api/v1/channel-connections/ \
     -H "Authorization: Bearer $TOKEN" | head
   # Expected: HTTP/1.1 200 OK
   ```

If authentication check fails (returns 200 without token), **DO NOT enable** and escalate immediately.

**How to Enable:**

1. Open Coolify dashboard
2. Navigate to: **Applications > PMS-Webapp > Environment Variables**
3. Add variable:
   - Name: `CHANNEL_MANAGER_ENABLED`
   - Value: `true`
4. Click **Save**
5. **Restart** the application

**Verification:**

```bash
# Check application logs
docker logs pms-backend --tail 50 | grep "Channel Manager"

# Expected when enabled:
# "Channel Manager module enabled via CHANNEL_MANAGER_ENABLED=true"

# Expected when disabled:
# "Channel Manager module disabled (CHANNEL_MANAGER_ENABLED=false, default)"

# Verify endpoints are exposed (when enabled)
curl http://localhost:8000/docs
# Check for /api/v1/channel-connections endpoints in Swagger UI
```

**Important Notes:**
- Requires `MODULES_ENABLED=true` (module system must be active)
- If `MODULES_ENABLED=false`, the Channel Manager module is bypassed regardless of this flag
- OpenAPI documentation (`/docs`) only shows Channel Manager endpoints when enabled
- Ensure proper authentication and RBAC policies are configured before enabling

---

### Verify Sync Batch Details (PROD)

**Purpose:** Verify channel manager sync batch API endpoints are working correctly in production.

**Prerequisites:**
- Channel Manager enabled (`CHANNEL_MANAGER_ENABLED=true`)
- Valid Bearer TOKEN (JWT)
- At least one channel connection exists (CID = connection UUID)
- At least one sync batch has been created (trigger sync via Admin UI or API)

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

**Manual Verification Commands:**

```bash
# 1. List sync batches for a connection (paginated)
export API="https://api.fewo.kolibri-visions.de"
export TOKEN="your-jwt-token"
export CID="your-connection-uuid"

curl -L -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/channel-connections/$CID/sync-batches?limit=10&offset=0" | python3 -m json.tool

# Expected: HTTP 200 with JSON response containing "items" array
# Each item: batch_id, batch_status, status_counts, created_at_min, operations array

# 2. Get details for a specific batch
export BATCH_ID="batch-uuid-from-above"

curl -L -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/channel-connections/$CID/sync-batches/$BATCH_ID" | python3 -m json.tool

# Expected: HTTP 200 with JSON response containing:
# - batch_id
# - connection_id
# - batch_status (failed/running/success/unknown)
# - status_counts (triggered, running, success, failed)
# - created_at_min, updated_at_max
# - operations: array of BatchOperation (operation_type, status, direction, task_id, error, duration_ms, log_id)
```

**Automated Smoke Test:**

Use the smoke test script for quick verification:

```bash
# Run smoke test (auto-picks first batch if BATCH_ID not set)
export API="https://api.fewo.kolibri-visions.de"
export TOKEN="your-jwt-token"
export CID="your-connection-uuid"

bash backend/scripts/pms_sync_batch_details_smoke.sh

# Expected output:
# ✓ List batches returned HTTP 200
# ✓ Get batch details returned HTTP 200
# Summary: All endpoints verified successfully
```

**Common Issues:**

- **No batches found:** Trigger a sync operation first via Admin UI (`/channel-sync` page) or API (`POST /api/v1/channel-connections/{id}/sync`)
- **HTTP 404 on batch details:** Batch may have been deleted or batch_id is incorrect
- **HTTP 401:** TOKEN expired or invalid (re-fetch from Supabase auth)
- **HTTP 503:** Database schema not installed or out of date (run migration: `20251227000000_create_channel_sync_logs.sql`)
- **HTTP 307 redirects:** Use `-L` flag with curl to follow redirects
- **HTTP 405 on HEAD requests:** Batch endpoints reject HEAD method; use GET for sanity checks (never use `curl -I`)
- **List endpoint JSON shape:** `/api/v1/channel-connections` may return top-level array OR `{items: [...]}` object; scripts handle both shapes robustly

**Batch Status Logic:**

- **failed**: Any operation has status='failed'
- **running**: Any operation has status='triggered' or 'running' (and none failed)
- **success**: All operations have status='success'
- **unknown**: No operations found or other states

**Admin UI Integration:**

The "Batch Details Modal" in Admin UI (`/channel-sync` page) uses these endpoints to display:
- Batch ID and overall status
- Operation breakdown with statuses, durations, errors
- Task IDs (Celery task UUIDs)
- Direction indicators (→ outbound, ← inbound)

Verify modal displays data correctly by clicking "View Details" on any sync batch row.

**UI E2E Verification:** Click the "Batch" badge in Sync Logs table to open Batch Details Modal. Confirm operations list renders with correct batch_id, connection_id, operation types, statuses, and durations. Modal should display direction indicators (→/←) and handle loading/error states gracefully.

**Manual Sync Trigger Form:**
- Auto-detect connection now auto-derives Platform and Property fields from the selected connection
- Platform and Property fields are locked (disabled) when derived from connection with "from connection" badge indicator
- Use Clear button to reset derived state and unlock fields for manual selection
- Manually changing Platform or Property while connection is derived will auto-clear the connection and unlock fields

---

### Channel Sync Console UX Verification Checklist

**Purpose:** Verify Channel Sync Console (`/channel-sync` page) handles errors, empty states, and destructive actions correctly.

**EXECUTION LOCATION:** WEB-BROWSER (Admin UI)

**Prerequisites:**
- Admin user logged in
- At least one channel connection configured

**Error State Verification:**

1. **401 Unauthorized (Session Expired)**
   - Test: Clear session token or wait for expiration, refresh page
   - Expected: "Session expired. Redirecting to login..." message, automatic redirect to /auth/logout
   - Applies to: Sync Logs list, Batch Details modal

2. **403 Forbidden (Access Denied)**
   - Test: Try accessing as non-admin user (if RBAC enforced at API level)
   - Expected: "Access denied. You don't have permission to view sync logs." (or batch details)
   - Applies to: Sync Logs list, Batch Details modal

3. **404 Not Found**
   - Test: Delete connection or batch, then try to fetch
   - Expected: "Connection not found. It may have been deleted." (logs) or "Batch not found. It may have been deleted or purged." (batch details)
   - Applies to: Sync Logs list, Batch Details modal

4. **503 Service Unavailable**
   - Test: Stop backend service temporarily
   - Expected: "Service temporarily unavailable. Please try again shortly."
   - Applies to: Sync Logs list, Batch Details modal

**Empty State Verification:**

1. **No Sync Logs Yet**
   - Test: Select connection with no sync history
   - Expected: "No sync logs yet" with hint "Trigger a manual sync or wait for automatic sync to create logs"
   - Location: Main Sync Logs table

2. **No Matching Search Results**
   - Test: Enter search query that matches no logs
   - Expected: "No logs match your search."
   - Location: Main Sync Logs table

3. **No Failed Logs**
   - Test: Filter by status=failed when no failures exist
   - Expected: "No failed logs yet. (Note: invalid requests (422) do not create logs.)"
   - Location: Main Sync Logs table

**Destructive Actions Verification:**

1. **Purge Logs Confirmation**
   - Test: Click "Purge Logs" button (admin only)
   - Expected:
     - Modal opens with purge preview (shows count to be deleted)
     - Requires typing "PURGE" exactly (case-sensitive)
     - "Purge" button disabled until phrase entered correctly
     - Button disabled while purge in-flight (shows loading state)
     - Error displayed if confirm phrase incorrect
   - Location: Purge modal (triggered from admin controls)

**Copy Helpers Verification:**

1. **curl Commands Use Safe Placeholders**
   - Test: Click "📋 Copy 'List Logs' curl" or "📋 Copy 'Trigger Sync' curl"
   - Expected:
     - Copied command includes placeholders: `$CID`, `$TOKEN`, `$PROPERTY_UUID`
     - NO actual tokens embedded (prevents accidental secret exposure)
     - Command is syntactically valid bash with placeholders
   - Location: API Helpers section

**Loading States Verification:**

1. **Spinners and Disabled Buttons**
   - Test: Trigger sync, open batch details modal, purge logs
   - Expected:
     - Loading spinners visible during fetch
     - Buttons disabled during in-flight requests (no double-click triggers)
     - Errors clear properly on retry
   - Location: All fetch operations

2. **Search Field Text Visibility**
   - Test: Click into Sync Logs search field and type text
   - Expected:
     - Typed text is clearly visible (not white on white or invisible)
     - Typed text has high contrast in light mode (dark text on white background, not low-contrast gray)
     - Works in both light mode and dark mode
     - Placeholder text remains readable
   - Location: Sync Logs search input

**RBAC Alignment:**

- Purge logs action requires **admin** role (aligned with sync trigger permissions)
- Non-admin users should NOT see "Purge Logs" button or link
- Admin UI gracefully degrades for non-admin users (403 errors handled)

---

## Branding & Theming Verification (PROD)

**Purpose:** Verify tenant branding system is working correctly in production (logo, colors, theme tokens).

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL (migration) + WEB-BROWSER (UI verification)

### Apply Migration (HOST-SERVER-TERMINAL)

```bash
# Check migration status
cd /path/to/repo
bash backend/scripts/ops/apply_supabase_migrations.sh --status

# Apply branding migration
bash backend/scripts/ops/apply_supabase_migrations.sh --apply

# Verify table exists
psql $DATABASE_URL -c "\d tenant_branding"
# Expected: Table with tenant_id, logo_url, primary_color, accent_color, etc.
```

### Verify API Endpoints (HOST-SERVER-TERMINAL or WEB-BROWSER)

**Get Branding (defaults if no custom config):**
```bash
export API="https://api.fewo.kolibri-visions.de"
export TOKEN="your-jwt-token"

curl -L -H "Authorization: Bearer $TOKEN" \
  "$API/api/v1/branding" | python3 -m json.tool

# Expected: HTTP 200 with tokens object (primary, accent, background, surface, text, etc.)
```

**Update Branding (admin/manager only):**
```bash
curl -L -X PUT "$API/api/v1/branding" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_color": "#4F46E5",
    "accent_color": "#10B981",
    "logo_url": "https://example.com/logo.png"
  }' | python3 -m json.tool

# Expected: HTTP 200 with updated tokens
```

### Verify UI (WEB-BROWSER)

**1. Default Branding:**
- Open Admin UI (fresh tenant with no branding set)
- Expected: Default indigo primary, emerald accent, no logo

**2. Set Custom Branding:**
- Log in as admin
- Navigate to Branding Settings (if UI implemented) OR use API via curl
- Set logo_url, primary_color, accent_color
- Save changes

**3. Verify Theme Application:**
- Refresh admin UI page
- Expected:
  - Logo appears in sidebar/header (if UI implemented)
  - Primary color applied to buttons, links
  - Accent color applied to success badges, highlights
  - Theme persists across page navigations

**4. Light/Dark Mode Toggle:**
- Toggle OS/browser dark mode
- Expected:
  - Background/surface colors invert
  - Text colors invert (dark text in light mode, light text in dark mode)
  - Primary/accent colors remain consistent
  - Search inputs NOT inverted (proper contrast in both modes)

### Troubleshooting

**Issue:** GET /api/v1/branding returns 503

**Solution:**
- Migration not applied: Run migration script
- RLS policy blocking: Check user's agency_id matches tenant_id

**Issue:** PUT /api/v1/branding returns 403

**Solution:**
- User is not admin or manager
- Check role via: `SELECT role FROM users WHERE id = auth.uid()`

**Issue:** Theme not applying in UI

**Solution:**
- Frontend not fetching branding on load (check browser DevTools network tab)
- CSS variables not injected (check :root styles in DevTools elements tab)
- Cache issue: Hard refresh (Cmd+Shift+R / Ctrl+Shift+R)

**Issue:** Migration pending but table already exists (ERROR: idx_tenant_branding_tenant already exists)

**Symptom:**
- Table `tenant_branding` exists
- Index `idx_tenant_branding_tenant` exists
- Policies missing (Policies: (none))
- Migration `20260103150000_create_tenant_branding.sql` not tracked in `pms_schema_migrations`

**Solution:**
- Partial apply state detected (table + index created but policies failed)
- Migration has been patched for full idempotency (v2026-01-03)
- Re-run migration via: `bash backend/scripts/ops/apply_supabase_migrations.sh --apply`
- DO NOT manually INSERT into `pms_schema_migrations` (runner tracks automatically on success)
- Verify completion: `bash backend/scripts/ops/apply_supabase_migrations.sh --status` (should show 0 pending)
- Verify policies: `\d+ tenant_branding` in psql (should show 3 policies: select, insert, update)

**Issue:** Migration fails with "relation public.users does not exist"

**Symptom:**
- Migration apply fails with ERROR: relation "public.users" does not exist
- Context: CREATE POLICY tenant_branding_select ... SELECT agency_id FROM public.users WHERE id = auth.uid()
- Policies not created, migration not tracked

**Solution:**
- Policy SQL referenced non-existent table (early version used public.users instead of JWT claims)
- Migration patched (2026-01-03) to use JWT-based pattern: `auth.jwt() ->> 'agency_id'` and `auth.jwt() ->> 'role'`
- Pull latest migration: `git pull origin main`
- Re-run migration: `bash backend/scripts/ops/apply_supabase_migrations.sh --apply`
- Verify policies installed:
  ```bash
  psql $DATABASE_URL -c "\d+ tenant_branding"
  # Should show: Policies: tenant_branding_select, tenant_branding_insert, tenant_branding_update
  ```
- Verify migration tracked:
  ```bash
  psql $DATABASE_URL -c "SELECT filename, applied_at FROM public.pms_schema_migrations WHERE filename LIKE '%tenant_branding%' ORDER BY applied_at DESC LIMIT 1;"
  # Should show: 20260103150000_create_tenant_branding.sql with recent timestamp
  ```

**Issue:** GET /api/v1/branding returns 404 while MODULES_ENABLED=true

**Symptom:**
- Migration applied successfully, policies exist, but API endpoint unreachable
- openapi.json does not contain branding paths
- Logs show: "Mounting N module(s): ['core_pms', 'inventory', 'properties', 'bookings', 'channel_manager']" (branding missing)

**Cause:**
- Branding router not part of module system, only mounted in fallback (MODULES_ENABLED=false)
- Module system skips non-registered modules

**Solution:**
- Branding module now registered in module system (backend/app/modules/branding.py)
- Auto-imported in bootstrap.py for self-registration

**Issue:** GET /api/v1/guests returns 404 while MODULES_ENABLED=true

**Symptom:**
- Guests table exists, migrations applied, but API endpoints unreachable
- openapi.json does not contain /api/v1/guests* paths
- Logs show mounted modules list without 'guests' entry

**Cause:**
- Guests router not part of module system (module registration missing)
- Module system skips non-registered modules when MODULES_ENABLED=true

**Solution:**
- Guests module now registered in module system (backend/app/modules/guests.py)
- Auto-imported in bootstrap.py for self-registration
- Enabled by default (no env var required)

**Verification:**
```bash
# Check startup logs for guests module
docker logs pms-backend --tail 100 | grep -i "guests"
# Expected: "Module 'guests' (v1.0.0, 1 router(s))"

# Verify openapi.json contains guests paths
curl http://localhost:8000/openapi.json | jq '.paths | keys | map(select(startswith("/api/v1/guests")))'
# Expected: ["/api/v1/guests", "/api/v1/guests/{guest_id}", "/api/v1/guests/{guest_id}/timeline"]
```

**Detailed Verification (CONTAINER - prove routes exist):**
```bash
# Execute inside container to verify routes are registered
docker exec pms-backend python3 - <<'PY'
from app.main import app
routes=[]
for r in app.routes:
    p=getattr(r,"path",None)
    m=getattr(r,"methods",None)
    if p: routes.append((p,sorted(list(m)) if m else []))
guest=[(p,m) for (p,m) in routes if "guest" in p.lower()]
print("guest_routes_found=",len(guest))
for p,m in guest: print("ROUTE",p,"methods=",m)
spec=app.openapi()
paths=spec.get("paths",{}) or {}
guest_paths=[p for p in paths.keys() if "guest" in p.lower()]
print("guest_paths_found=",len(guest_paths))
for p in sorted(guest_paths): print("OPENAPI",p,"methods=",sorted((paths.get(p) or {}).keys()))
PY

# Expected output:
# guest_routes_found= 6
# ROUTE /api/v1/guests methods= ['GET']
# ROUTE /api/v1/guests/{guest_id} methods= ['GET']
# ROUTE /api/v1/guests/{guest_id} methods= ['PATCH']
# ROUTE /api/v1/guests/{guest_id} methods= ['PUT']
# ROUTE /api/v1/guests methods= ['POST']
# ROUTE /api/v1/guests/{guest_id}/timeline methods= ['GET']
# guest_paths_found= 5
# OPENAPI /api/v1/guests methods= ['get', 'post']
# OPENAPI /api/v1/guests/{guest_id} methods= ['get', 'patch', 'put']
# OPENAPI /api/v1/guests/{guest_id}/timeline methods= ['get']
```

**Detailed Verification (HOST-SERVER-TERMINAL - prove external OpenAPI):**
```bash
# Verify external OpenAPI exposes guests endpoints
API="https://api.fewo.kolibri-visions.de"
curl -k -sS "$API/openapi.json" | grep -oE '"/api/v1/guests[^"]*"' | head

# Expected output:
# "/api/v1/guests"
# "/api/v1/guests/{guest_id}"
# "/api/v1/guests/{guest_id}/timeline"
```



**Issue:** GET /api/v1/guests returns 500 with validation errors or missing fields

**Symptom:**
- Endpoint returns HTTP 500 Internal Server Error
- Logs show: "validation errors for GuestResponse" with missing fields like agency_id, updated_at
- OR logs show: "UndefinedColumn" or "column does not exist"
- OR language/vip_status/blacklisted fields contain NULL causing validation failures

**Cause:**
- Database schema drift: required columns missing or nullable when code expects non-null
- Migration 20260105120000_fix_guests_list_required_fields.sql not applied
- Columns language, vip_status, blacklisted lack defaults and contain NULLs

**Fix:**
1. Apply migration via SQL Editor:
   ```sql
   -- Run migration: supabase/migrations/20260105120000_fix_guests_list_required_fields.sql
   -- Or apply manually:

   -- Ensure updated_at exists
   ALTER TABLE public.guests
   ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now() NOT NULL;

   -- Set defaults and backfill NULLs
   ALTER TABLE public.guests ALTER COLUMN language SET DEFAULT 'unknown';
   UPDATE public.guests SET language = 'unknown' WHERE language IS NULL;

   ALTER TABLE public.guests ALTER COLUMN vip_status SET DEFAULT false;
   UPDATE public.guests SET vip_status = false WHERE vip_status IS NULL;
   ALTER TABLE public.guests ALTER COLUMN vip_status SET NOT NULL;

   ALTER TABLE public.guests ALTER COLUMN blacklisted SET DEFAULT false;
   UPDATE public.guests SET blacklisted = false WHERE blacklisted IS NULL;
   ALTER TABLE public.guests ALTER COLUMN blacklisted SET NOT NULL;

   -- Backfill updated_at
   UPDATE public.guests SET updated_at = COALESCE(updated_at, created_at, now()) WHERE updated_at IS NULL;
   ```

2. Restart backend to reload schema metadata:
   ```bash
   docker restart pms-backend
   ```

**Verification (DB SQL Editor):**
```sql
-- Verify required columns exist with correct defaults
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema='public' AND table_name='guests'
  AND column_name IN ('agency_id','updated_at','city','country','language','vip_status','blacklisted','source')
ORDER BY column_name;

-- Expected output:
-- agency_id    | uuid         | NO  | (not null)
-- blacklisted  | boolean      | NO  | false
-- city         | text         | YES | NULL
-- country      | text         | YES | NULL
-- language     | text         | YES | 'unknown'::text
-- source       | text         | YES | NULL
-- updated_at   | timestamptz  | NO  | now()
-- vip_status   | boolean      | NO  | false
```

**Verification (HOST-SERVER-TERMINAL):**
```bash
# Test endpoint with valid JWT
API="https://api.fewo.kolibri-visions.de"
curl -k -sS -i -L "$API/api/v1/guests?limit=1&offset=0" -H "Authorization: Bearer $JWT_TOKEN" | sed -n '1,120p'

# Expected: HTTP/1.1 200 OK (not 500)
# Expected response body: {"items":[...],"total":N,"limit":1,"offset":0}
```

**Verification (CONTAINER):**
```bash
# Verify routes and OpenAPI paths
docker exec pms-backend python3 - <<'PY'
from app.main import app
print("guest_routes=", [getattr(r,"path",None) for r in app.routes if getattr(r,"path",None) and "guest" in getattr(r,"path","").lower()])
spec=app.openapi()
paths=spec.get("paths",{}) or {}
print("guest_paths=", sorted([p for p in paths.keys() if "guest" in p.lower()]))
PY

# Expected guest_routes= ['/api/v1/guests', '/api/v1/guests/{guest_id}', '/api/v1/guests/{guest_id}/timeline', ...]
# Expected guest_paths= ['/api/v1/guests', '/api/v1/guests/{guest_id}', '/api/v1/guests/{guest_id}/timeline']
```

**Issue:** GET /api/v1/guests/{guest_id}/timeline returns 500 with UndefinedColumnError

**Symptom:**
- Endpoint returns HTTP 500 Internal Server Error
- Logs show: "asyncpg.exceptions.UndefinedColumnError: column b.check_in_date does not exist"
- Hint suggests: "Perhaps you meant b.check_in_at"

**Cause:**
- Timeline query expected old column names (check_in_date, check_out_date)
- Database schema uses check_in_at and check_out_at columns
- Code updated to use correct column names in commit that fixes this issue

**Fix:**
- Deploy latest code (includes corrected timeline query using check_in_at/check_out_at)
- Restart backend:
  ```bash
  docker restart pms-backend
  ```

**Verification (HOST-SERVER-TERMINAL):**
```bash
# Test timeline endpoint with valid guest ID and JWT
API="https://api.fewo.kolibri-visions.de"
GID="1e9dd87c-ba39-4ec5-844e-e4c66e1f4dc1"
curl -k -sS -i -L "$API/api/v1/guests/$GID/timeline?limit=5&offset=0" \
  -H "Authorization: Bearer $JWT_TOKEN" | sed -n '1,160p'

# Expected: HTTP/1.1 200 OK (empty bookings list is fine)
# Expected response: {"guest_id":"...","guest_name":"...","bookings":[...],"total":N,"limit":5,"offset":0}
```

**Verification (DB SQL Editor):**
```sql
-- Verify bookings table has correct column names
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema='public' AND table_name='bookings'
  AND column_name IN ('check_in_at','check_out_at','check_in_date','check_out_date')
ORDER BY column_name;

-- Expected: check_in_at and check_out_at exist (not check_in_date/check_out_date)
```

**Issue:** GET /api/v1/guests/{guest_id}/timeline returns 500 with response validation error

**Symptom:**
- Endpoint returns HTTP 500 Internal Server Error
- Logs show: "ValidationError" for GuestTimelineResponse
- Missing required fields: check_in_date and check_out_date in bookings array
- Timeline dict contains check_in_at and check_out_at instead

**Cause:**
- Response schema expects check_in_date and check_out_date (DATE fields)
- Timeline query was returning check_in_at and check_out_at (timestamp fields)
- Field name mismatch between service layer and response schema

**Fix:**
- Deploy latest code (timeline query now casts timestamps to date with correct aliases)
- Query uses: `b.check_in_at::date as check_in_date, b.check_out_at::date as check_out_date`
- Restart backend:
  ```bash
  docker restart pms-backend
  ```

**Verification (HOST-SERVER-TERMINAL):**
```bash
# Test timeline endpoint with valid guest ID and JWT
API="https://api.fewo.kolibri-visions.de"
GID="<guest_uuid>"
curl -k -sS -i -L "$API/api/v1/guests/$GID/timeline?limit=5&offset=0" \
  -H "Authorization: Bearer $JWT_TOKEN" | sed -n '1,200p'

# Expected: HTTP/1.1 200 OK
# Expected response: {"guest_id":"...","guest_name":"...","bookings":[{"check_in_date":"2024-01-15","check_out_date":"2024-01-20",...}],...}
```

**Issue:** GET /api/v1/guests/{guest_id}/timeline returns 500 with null date fields

**Symptom:**
- Endpoint returns HTTP 500 Internal Server Error
- Logs show: "ValidationError" or "Timeline response validation failed"
- Error mentions check_in_date or check_out_date fields are null
- Booking records exist but have NULL check_in_at or check_out_at timestamps

**Cause:**
- Response schema previously required non-null date fields
- Legacy or incomplete booking records may have NULL check_in_at or check_out_at
- Query casts NULL timestamps to NULL dates, causing validation error

**Fix:**
- Deploy latest code (response schema now allows nullable date fields)
- check_in_date and check_out_date fields are now Optional (may be null)
- Restart backend:
  ```bash
  docker restart pms-backend
  ```

**Verification (HOST-SERVER-TERMINAL):**
```bash
# Test timeline endpoint with valid guest ID and JWT
API="https://api.fewo.kolibri-visions.de"
GID="<guest_uuid>"
curl -k -sS -i -L "$API/api/v1/guests/$GID/timeline?limit=5&offset=0" \
  -H "Authorization: Bearer $JWT_TOKEN" | sed -n '1,200p'

# Expected: HTTP/1.1 200 OK (even if some bookings have null dates)
# Expected response: {"guest_id":"...","guest_name":"...","bookings":[{"check_in_date":null,"check_out_date":null,...}],...}
```

**Verification (DB SQL Editor - Find bookings with null dates):**
```sql
-- Find bookings with NULL check_in_at or check_out_at for a guest
SELECT id, status, created_at, check_in_at, check_out_at
FROM bookings
WHERE guest_id = '<guest_uuid>' AND agency_id = '<agency_uuid>'
ORDER BY created_at DESC;

-- Expected: Some rows may show NULL in check_in_at or check_out_at columns
```

**Optional Data Cleanup:**
If you need to backfill missing dates, update rows with appropriate values based on business logic. Do not use arbitrary fake dates without verifying business requirements first.

**Issue:** POST /api/v1/guests returns 500 with UndefinedColumnError for auth_user_id

**Symptom:**
- Endpoint returns HTTP 500 Internal Server Error
- Logs show: "asyncpg.exceptions.UndefinedColumnError: column 'auth_user_id' does not exist"

**Cause:**
- guests.auth_user_id column missing from database schema
- Migration 20260105130000_add_guests_auth_user_id.sql not applied

**Fix:**
1. Apply migration via SQL Editor:
   ```sql
   -- Run migration: supabase/migrations/20260105130000_add_guests_auth_user_id.sql
   -- Or apply manually:

   ALTER TABLE public.guests
   ADD COLUMN IF NOT EXISTS auth_user_id uuid;

   COMMENT ON COLUMN public.guests.auth_user_id IS 'Optional link to authenticated user account (for guest portal access)';

   CREATE INDEX IF NOT EXISTS idx_guests_auth_user_id
   ON public.guests(auth_user_id)
   WHERE auth_user_id IS NOT NULL;
   ```

2. Restart backend to reload schema metadata:
   ```bash
   docker restart pms-backend
   ```

**Verification (DB SQL Editor):**
```sql
-- Verify auth_user_id column exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND table_name='guests'
  AND column_name='auth_user_id';

-- Expected output:
-- auth_user_id | uuid | YES
```

**Verification (HOST-SERVER-TERMINAL):**
```bash
# Run full CRUD smoke test including POST
cd /data/repos/pms-webapp
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export GUESTS_CRUD_TEST=true
./backend/scripts/pms_guests_smoke.sh

# Expected: All tests pass including "POST /api/v1/guests"
```

**Issue:** Guests endpoints return 503 with missing column errors

**Symptom:**
- Endpoints return HTTP 503 Service Unavailable
- Logs show: "asyncpg.exceptions.UndefinedColumnError: column does not exist"
- Missing columns: address_line1, address_line2, marketing_consent, marketing_consent_at, profile_notes, blacklist_reason

**Cause:**
- Database schema drift: optional guest profile columns not created
- Migration 20260105140000_guests_missing_columns.sql not applied
- Fresh database installations or schema restores missing these columns

**Fix:**
1. Apply migration via SQL Editor:
   ```sql
   -- Run migration: supabase/migrations/20260105140000_guests_missing_columns.sql
   -- Or apply manually:

   ALTER TABLE public.guests
   ADD COLUMN IF NOT EXISTS address_line1 text;

   ALTER TABLE public.guests
   ADD COLUMN IF NOT EXISTS address_line2 text;

   ALTER TABLE public.guests
   ADD COLUMN IF NOT EXISTS marketing_consent boolean NOT NULL DEFAULT false;

   ALTER TABLE public.guests
   ADD COLUMN IF NOT EXISTS marketing_consent_at timestamptz;

   ALTER TABLE public.guests
   ADD COLUMN IF NOT EXISTS profile_notes text;

   ALTER TABLE public.guests
   ADD COLUMN IF NOT EXISTS blacklist_reason text;
   ```

2. Restart backend to reload schema metadata:
   ```bash
   docker restart pms-backend
   ```

**Verification (DB SQL Editor):**
```sql
-- Verify all optional profile columns exist
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema='public' AND table_name='guests'
  AND column_name IN ('address_line1', 'address_line2', 'marketing_consent', 'marketing_consent_at', 'profile_notes', 'blacklist_reason')
ORDER BY column_name;

-- Expected: 6 rows returned with all columns present
```

**Verification (HOST-SERVER-TERMINAL):**
```bash
# Run full Guests CRUD smoke test
cd /data/repos/pms-webapp
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export GUESTS_CRUD_TEST=true
./backend/scripts/pms_guests_smoke.sh

# Expected: All tests pass (list, search, create, details, update, timeline)
```

- Redeploy to apply changes

**Verification:**
```bash
# Verify branding paths in OpenAPI schema
curl -s https://your-domain.com/openapi.json | grep -i branding
# Expected: "/api/v1/branding" appears

# Verify module mounting in logs (after redeploy)
# Expected: "Mounting 6 module(s): ['core_pms', 'inventory', 'properties', 'bookings', 'branding', ...]"

# Test endpoint (should return 401 without token, or 200 with valid token)
curl -i https://your-domain.com/api/v1/branding
# Expected: HTTP 401 Unauthorized (no token) or HTTP 200 OK (with Authorization header)
```

**Issue:** /api/v1/branding returns 404 and openapi.json lacks branding paths

**Symptom:**
- Migration applied successfully, table and policies exist
- openapi.json does not contain /api/v1/branding paths
- Endpoint returns 404
- Container logs show: "Branding module not available: cannot import name 'User' from 'app.core.auth'"

**Cause:**
- ImportError in branding router prevents module from loading
- Invalid import: `from app.core.auth import User` (User does not exist in app.core.auth)
- get_current_user returns dict, not User object

**Solution:**
- Fixed branding.py to remove invalid User import
- Changed type annotations to use dict instead of non-existent User class
- Changed current_user.agency_id to current_user["agency_id"] (dict access)
- Redeploy to apply changes

**Verification:**
```bash
# Check container logs for successful module mounting (after redeploy)
docker logs pms-backend 2>&1 | grep -i "mounting.*branding"
# Expected: "Mounting 6 module(s): ['core_pms', 'inventory', 'properties', 'bookings', 'branding', ...]"

# Verify openapi.json contains branding paths
curl -s https://your-domain.com/openapi.json | grep -o '"/api/v1/branding"'
# Expected: "/api/v1/branding"

# Test endpoint (should return 401 without token)
curl -i https://your-domain.com/api/v1/branding
# Expected: HTTP 401 Unauthorized (NOT 404)
```

**Issue:** Branding endpoints return 404 because module import failed (require_roles import path)

**Symptom:**
- Container logs show: "Branding module not available: cannot import name 'require_roles' from 'app.core.auth'"
- openapi.json does not contain /api/v1/branding paths
- GET /api/v1/branding returns 404

**Cause:**
- branding.py imports require_roles from wrong module (app.core.auth)
- require_roles is actually in app.api.deps (same as other routes)

**Solution:**
- Fixed import in branding.py: from app.api.deps import require_roles
- Redeploy to apply changes

**Verification:**
```bash
# Check mounted modules in container logs
docker logs pms-backend 2>&1 | grep -i "mounting.*module"
# Expected: "Mounting 6 module(s): ['core_pms', 'inventory', 'properties', 'bookings', 'branding', ...]"

# Check INTERNAL openapi has branding paths (from inside container)
docker exec pms-backend curl -s http://localhost:8000/openapi.json | grep -o '"/api/v1/branding"'
# Expected: "/api/v1/branding"

# Test external endpoint (should return 401 without token, 200 with token)
curl -i https://your-domain.com/api/v1/branding
# Expected: HTTP 401 Unauthorized (NOT 404)
```

**Verify Branding Endpoint (PROD)**

**Expected GET Response (200 OK):**
```json
{
  "tenant_id": "uuid-here",
  "logo_url": null,
  "primary_color": "#4F46E5",
  "accent_color": "#10B981",
  "font_family": "system",
  "radius_scale": "md",
  "mode": "system",
  "tokens": {
    "primary": "#4F46E5",
    "accent": "#10B981",
    "background": "#FFFFFF",
    "surface": "#F9FAFB",
    "text": "#111827",
    "text_muted": "#6B7280",
    "border": "#E5E7EB",
    "radius": "0.5rem"
  }
}
```

**Common Failure Modes:**

| Status | Cause | Solution |
|--------|-------|----------|
| 400 Bad Request | JWT missing agency_id claim | Regenerate token with proper claims |
| 401 Unauthorized | Token expired or invalid | Get fresh token |
| 403 Forbidden | Token valid but no auth header | Add Authorization: Bearer header |
| 503 Service Unavailable | DB unavailable or migration not applied | Check DB connectivity, apply migrations |

**Smoke Test (HOST-SERVER-TERMINAL):**
```bash
# Set environment variables
export API_BASE_URL="https://your-domain.com"
export JWT_TOKEN="eyJhbGc..."  # Valid token with agency_id claim

# Run smoke test
bash backend/scripts/pms_branding_smoke.sh

# Expected output:
# ✅ GET /api/v1/branding: SUCCESS
# HTTP Status: 200
```

**Manual Verification:**
```bash
# Test GET endpoint with curl
curl -H "Authorization: Bearer $JWT_TOKEN" https://your-domain.com/api/v1/branding | jq

# Expected: HTTP 200 with defaults (if no custom branding)
# Expected: tenant_id matches user's agency_id from JWT
```

**Branding Tenant Context Resolution**

**Symptom:** GET /api/v1/branding returns 400 "Tenant context not available"

**Cause:**
- JWT token missing agency_id claim
- User belongs to multiple tenants and no tenant specified

**Solution (tenant resolution order):**
1. JWT claim agency_id (if present)
2. x-agency-id header (validated via membership check)
3. Auto-pick (if user belongs to exactly one tenant)

**Fix with x-agency-id header (HOST-SERVER-TERMINAL):**
```bash
# Using curl directly
export JWT_TOKEN="your-jwt-token"
export TENANT_ID="ffd0123a-10b6-40cd-8ad5-66eee9757ab7"

curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "x-agency-id: $TENANT_ID" \
     https://your-domain.com/api/v1/branding

# Expected: HTTP 200 with branding data
```

**Fix with smoke script:**
```bash
# EXECUTION LOCATION: HOST-SERVER-TERMINAL
export API_BASE_URL="https://your-domain.com"
export JWT_TOKEN="your-jwt-token"
export AGENCY_ID="ffd0123a-10b6-40cd-8ad5-66eee9757ab7"

bash backend/scripts/pms_branding_smoke.sh

# Expected: GET /api/v1/branding: SUCCESS (HTTP 200)
```

**Error Messages:**
- "User belongs to N tenants. Provide x-agency-id header" → Set AGENCY_ID env var
- "Not authorized for this tenant" (403) → User not member of specified tenant
- "No tenant context available" → User not assigned to any tenant (contact admin)

---

### Guest CRM API Smoke Test

**Problem:** After deployment, guests API endpoints (list, create, update, timeline) may fail due to database issues, schema mismatches, or RBAC configuration errors.

**Symptoms:**
- GET /api/v1/guests returns 500 or 503
- Search functionality returns no results
- Guest creation fails with validation errors
- Timeline endpoint returns 404 for valid guest IDs

**Diagnostic Steps:**

1. **Verify API Availability:**
   ```bash
   # EXECUTION LOCATION: HOST-SERVER-TERMINAL
   curl -I https://your-domain.com/api/v1/guests
   # Expected: HTTP 401 (auth required)
   ```

2. **Check Database Connection:**
   ```bash
   # Verify guests table exists
   docker exec pms-backend psql -U postgres -c "\d guests"
   # Expected: Table structure with columns id, agency_id, email, etc.
   ```

3. **Verify RBAC Configuration:**
   ```bash
   # Check if JWT token has correct role
   echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq '.role'
   # Expected: "admin", "manager", or "staff" for CRUD operations
   ```

**Common Errors:**

| Error Code | Symptom | Cause | Solution |
|------------|---------|-------|----------|
| 200 Empty List | GET /api/v1/guests returns `{"items":[],"total":0}` | No guests in database | Expected for new deployment |
| 403 Forbidden | POST /api/v1/guests fails | User has owner/accountant role | Use admin/manager/staff token |
| 404 Not Found | GET /api/v1/guests/{id} fails | Guest belongs to different agency | Verify multi-tenant isolation |
| 422 Validation | POST /api/v1/guests fails | Invalid email or phone format | Check payload validation |
| 503 Service Unavailable | All endpoints fail | Database connection lost | Check DB connectivity, restart container |

**Smoke Test (HOST-SERVER-TERMINAL):**
```bash
# Set environment variables
export API_BASE_URL="https://your-domain.com"
export JWT_TOKEN="eyJhbGc..."  # Valid token with admin/manager/staff role
export AGENCY_ID="your-tenant-uuid"  # Optional: if JWT lacks agency_id claim

# Run smoke test (read-only)
bash backend/scripts/pms_guests_smoke.sh

# Expected output:
# ✅ GET /api/v1/guests: SUCCESS
# ✅ GET /api/v1/guests?q=search: SUCCESS

# Run smoke test (full CRUD)
export GUESTS_CRUD_TEST=true
bash backend/scripts/pms_guests_smoke.sh

# Expected output:
# ✅ POST /api/v1/guests: SUCCESS
# ✅ PATCH /api/v1/guests/{id}: SUCCESS
# ✅ GET /api/v1/guests/{id}/timeline: SUCCESS
```

**Manual Verification:**
```bash
# Test list endpoint
curl -H "Authorization: Bearer $JWT_TOKEN" https://your-domain.com/api/v1/guests | jq

# Test search endpoint
curl -H "Authorization: Bearer $JWT_TOKEN" "https://your-domain.com/api/v1/guests?q=test" | jq

# Test create endpoint (requires admin/manager/staff role)
curl -X POST \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Test","last_name":"Guest","email":"test@example.com"}' \
  https://your-domain.com/api/v1/guests | jq

# Test timeline endpoint (replace {guest_id} with actual ID)
curl -H "Authorization: Bearer $JWT_TOKEN" https://your-domain.com/api/v1/guests/{guest_id}/timeline | jq
```

**Fix Steps:**

1. **Database Connection Issues:**
   ```bash
   # Check if database is accepting connections
   docker exec pms-backend pg_isready -U postgres
   
   # Restart backend if needed
   docker restart pms-backend
   ```

2. **RBAC Issues:**
   ```bash
   # Verify token role
   echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq '.role'
   
   # If role is "owner" or "accountant", use a different token
   # Admin, manager, or staff role required for CRUD operations
   ```

3. **Multi-Tenant Isolation Issues:**
   ```bash
   # If JWT lacks agency_id claim, provide it explicitly
   export AGENCY_ID="your-tenant-uuid"
   bash backend/scripts/pms_guests_smoke.sh
   ```

**Validation Checklist:**
- [ ] GET /api/v1/guests returns HTTP 200 with guest list
- [ ] GET /api/v1/guests?q=search returns HTTP 200 with search results
- [ ] POST /api/v1/guests creates new guest (HTTP 201)
- [ ] PATCH /api/v1/guests/{id} updates guest (HTTP 200)
- [ ] GET /api/v1/guests/{id}/timeline returns booking history (HTTP 200)
- [ ] Cross-tenant access returns 404 (not 403 to avoid leaking existence)
- [ ] Search works across first_name, last_name, email, phone
- [ ] Pagination works correctly (limit, offset parameters)

---


**Admin Branding UI Verification**

**Purpose:** Verify branding tokens are applied in Admin UI and settings page works correctly.

**EXECUTION LOCATION:** WEB-BROWSER

**Prerequisites:**
- Admin or manager role
- Valid JWT token
- Frontend deployed and accessible
- Backend branding API working (verified via smoke script)

**Verification Steps (WEB-BROWSER):**

1. **Login and Navigate:**
   - Login to Admin UI at `https://your-domain.com/login`
   - Click "Branding" tab in navigation (admin/manager only)
   - Expected: `/settings/branding` page loads

2. **Verify CSS Variables Applied:**
   - Open browser developer tools (F12)
   - Select Elements/Inspector tab
   - Inspect `<html>` or `<body>` element
   - Check Computed Styles for CSS variables:
     ```
     --t-primary: #3b82f6 (or custom value)
     --t-accent: #8b5cf6 (or custom value)
     --t-bg: #ffffff (light) or #111827 (dark)
     --t-surface: #f9fafb (light) or #1f2937 (dark)
     --t-text: #111827 (light) or #f9fafb (dark)
     --t-radius: 0.375rem (or custom)
     ```
   - Expected: All theme variables present with correct values

3. **Verify Theme Mode:**
   - Check `<html data-theme="...">` attribute
   - Expected values: `light`, `dark`, or `system`
   - If system mode: verify auto-switches based on OS preference

4. **Test Branding Settings Form:**
   - Change Primary Color to `#4169E1` (royal blue)
   - Change Accent Color to `#32CD32` (lime green)
   - Change Mode to "Dark"
   - Click "Save Changes"
   - Expected: "Branding updated successfully!" message
   - Verify CSS variables update immediately (inspect developer tools)
   - Verify background switches to dark mode

5. **Test Form Validation:**
   - Enter invalid hex color (e.g., `#ZZZ`)
   - Try to save
   - Expected: Browser validation error or API 400 error message

6. **Test Access Control:**
   - Logout and login as non-admin/non-manager user
   - Try accessing `/settings/branding` directly
   - Expected: "Access Denied" page with diagnostics
   - Expected: "Branding settings are restricted to administrators and managers only."

**Error Scenarios and Expected UI Behavior:**

| Scenario | Expected UI Behavior |
|----------|---------------------|
| JWT lacks `agency_id` claim | Theme loads with defaults + console warning (graceful degradation) |
| User belongs to multiple tenants | Theme loads with defaults if no `x-agency-id` header |
| API returns 400 tenant error | Error toast: "Tenant context not available. Using default theme." |
| API returns 401/403 | Error toast: "Not authorized to view branding. Using default theme." |
| API returns 503 | Error toast: "Branding service temporarily unavailable. Using default theme." |
| PUT fails with 400 | Form error message: "Validation error: ..." |
| PUT fails with 403 | Form error message: "Access denied. Only admins and managers..." |
| Network error | Form error message: "Failed to update branding. Please try again." |

**Alternative Verification (HOST-SERVER-TERMINAL):**

Check branding API returns correct tokens:
```bash
# EXECUTION LOCATION: HOST-SERVER-TERMINAL
export JWT_TOKEN="your-jwt-token"
export TENANT_ID="ffd0123a-10b6-40cd-8ad5-66eee9757ab7"

curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "x-agency-id: $TENANT_ID" \
     https://your-domain.com/api/v1/branding | jq '.tokens'

# Expected output:
# {
#   "primary": "#3b82f6",
#   "primaryHover": "#2563eb",
#   "accent": "#8b5cf6",
#   ...
# }
```

**Troubleshooting:**

| Issue | Cause | Solution |
|-------|-------|----------|
| CSS variables not applied | ThemeProvider not rendering | Check browser console for errors, verify ThemeProvider in root layout |
| Form doesn't load | Auth check failed | Verify user has admin or manager role in `team_members` table |
| Save button disabled | Form validation error | Check form inputs match validation patterns |
| Theme doesn't change after save | refreshBranding() failed | Check network tab for API errors, verify PUT request succeeded |
| Dark mode not working | CSS not loaded or `data-theme` attr missing | Verify globals.css loaded, check `<html data-theme>` attribute |

**CSS Variable "undefined" String Bug (Fixed):**

**Symptom:** Browser console shows CSS variables set to string "undefined" instead of valid color values.

Example:
```
--t-primary: "#3B82F6"   ✓ correct
--t-bg: "undefined"      ✗ bug (fixed in latest release)
```

**Root Cause:**
- API response token field mismatch (API returns `background`, frontend expected `bg`)
- Missing token sanitization allowed undefined values to be stringified
- No validation before setting CSS properties

**Fix Applied:**
1. Added `normalizeTokenValue()` sanitizer: rejects undefined/null/"undefined"/"null" strings
2. Created API token mapper: `background` → `bg`, `text_muted` → `textMuted`
3. Derived missing tokens: `primaryHover`, `accentHover`, `surfaceHover`, `borderSubtle`
4. Safe CSS property setter: `applyCssVariable()` uses `removeProperty()` for null values instead of setting "undefined"

**Verification (POST-FIX):**

```bash
# EXECUTION LOCATION: WEB-BROWSER (developer tools console)

# Check CSS variables are valid hex colors (not "undefined" strings)
getComputedStyle(document.documentElement).getPropertyValue('--t-bg')
# Expected: "#ffffff" or "#111827" (valid hex)
# NOT: "undefined"

getComputedStyle(document.documentElement).getPropertyValue('--t-primary')
# Expected: "#3b82f6" or custom hex
# NOT: "undefined"
```

**Expected Result:**
- All theme variables (`--t-*`) resolve to valid CSS values
- No "undefined" or "null" strings in computed styles
- Theme applies correctly on page load and after save

**If Bug Persists:**
1. Clear browser cache and hard reload
2. Check browser console for API errors
3. Verify API response format matches expected schema
4. Check network tab: `/api/v1/branding` response should include `tokens.background` field

**Theme Mode Palette Mismatch (Fixed):**

**Symptom:** `data-theme="dark"` but CSS variables still show light palette values (white background, dark text).

Example:
```
<html data-theme="dark" ...>
--t-bg: "#ffffff"    ✗ bug (should be "#111827" for dark mode)
--t-text: "#111827"  ✗ bug (should be "#f9fafb" for dark mode)
```

**Root Cause:**
- Backend returns flat light-mode tokens only (no per-mode token sets)
- Frontend applied those light tokens to :root regardless of mode setting
- data-theme attribute changed but CSS variable values did not

**Fix Applied:**
1. Separate light and dark default palettes defined in frontend
2. `deriveDarkTokens()` function creates dark palette from light tokens (keeps primary/accent, changes bg/surface/text)
3. `getEffectiveMode()` determines active mode (light/dark/system with OS detection)
4. `applyThemeTokens()` applies correct palette based on effective mode
5. Added `data-effective-theme` attribute for debugging (shows resolved mode)

**Verification (POST-FIX):**

```bash
# EXECUTION LOCATION: WEB-BROWSER (developer tools console)

# Check data-theme and effective theme
document.documentElement.getAttribute('data-theme')
# Expected: "dark", "light", or "system"

document.documentElement.getAttribute('data-effective-theme')
# Expected: "dark" or "light" (resolved from system if mode=system)

# Check CSS variables match the effective theme
const mode = document.documentElement.getAttribute('data-effective-theme');
const bg = getComputedStyle(document.documentElement).getPropertyValue('--t-bg').trim();
const text = getComputedStyle(document.documentElement).getPropertyValue('--t-text').trim();

console.log(`Mode: ${mode}, BG: ${bg}, Text: ${text}`);
# Expected for dark mode: Mode: dark, BG: #111827 (dark gray), Text: #f9fafb (light)
# Expected for light mode: Mode: light, BG: #ffffff (white), Text: #111827 (dark)
```

**Expected Result:**
- Dark mode: bg="#111827", surface="#1f2937", text="#f9fafb"
- Light mode: bg="#ffffff", surface="#f9fafb", text="#111827"
- System mode: follows OS preference automatically

**If Bug Persists:**
1. Clear browser cache and hard reload
2. Check mode setting in branding form matches data-theme
3. Verify no CSS overrides in globals.css
4. Check browser console for theme provider errors

**Auth Client Multiple Instances Warning (Fixed):**

**Symptom:** Browser console shows "multiple auth-client instances detected in same browser context"

**Root Cause:**
- Auth client created on each function call instead of singleton
- Module-level caching didn't survive HMR (hot module reload)

**Fix Applied:**
1. Created dedicated singleton module: `auth-client-singleton.ts`
2. Uses `globalThis` to cache instance (survives HMR and page reloads)
3. `getAuthClient()` function returns same instance on all calls
4. All auth client creation refactored to use singleton

**Verification (POST-FIX):**

```bash
# EXECUTION LOCATION: WEB-BROWSER (developer tools console)

# Check for warning message (should NOT appear after fix)
# Open console and reload page
# Expected: No "multiple instances" warning
```

**Expected Result:**
- No console warnings about multiple auth-client instances
- Single client instance used throughout application
- Instance persists across HMR and page reloads

---

## Redis + Celery Worker Setup (Channel Manager)

**Purpose:** Configure Redis and Celery worker for Channel Manager background sync operations.

### Background / Symptoms

If Redis or Celery worker are not properly configured, you may encounter these issues:

**Redis Connection Failures:**
- `/health/ready` endpoint shows `redis: down` with error:
  ```
  "Authentication required."
  "invalid username-password pair or user is disabled."
  ```

**Celery Worker Issues:**
- `/health/ready` shows `celery: down` with error:
  ```
  "Celery inspect timeout (broker may be unreachable)"
  "No active Celery workers detected"
  ```

**Channel Manager Sync Failures:**
- Channel sync endpoints return connection refused
- Celery tasks fail with "Broker connection error"
- Background jobs (Airbnb/Booking.com sync) do not execute

---

### Required Coolify Resources

To enable Channel Manager background processing, you need:

#### 1. Redis Service

**Service Name:** `coolify-redis` (or your chosen name)

**Configuration:**
- Type: Redis
- Enable authentication: **YES**
- Set `requirepass` in Redis config or via environment variable
- Network: Must be on same Docker network as backend/worker

**How to Deploy in Coolify:**
1. Go to: **Services > Add New Service > Redis**
2. Set service name: `coolify-redis`
3. Set Redis password in configuration
4. Deploy and note the password for next steps

#### 2. PMS Backend App

**App Name:** `pms-backend` (already exists)

**Purpose:** Main FastAPI application serving HTTP API

**Configuration:**
- Already deployed
- Will connect to Redis for health checks
- Will trigger Celery tasks via broker

#### 3. PMS Worker App (NEW)

**App Name:** `pms-worker`

**Purpose:** Celery worker process for background jobs (sync operations)

**Configuration:**
- Type: Git-based Application
- Repository: Same as pms-backend
- Branch: Same as pms-backend (usually `main`)
- Base Directory: `/backend`
- Build Pack: Nixpacks
- Start Command: See [Worker Start Command](#worker-start-command) section below

**Important:**
- Worker does NOT need public domain/Traefik proxy
- Worker does NOT serve HTTP traffic (background processing only)
- Coolify requires "Ports Exposes" field: set to `8000` (harmless value, not actually used)

---

### Required Environment Variables

The worker app must have **identical configuration** to the backend for task execution consistency.

**Copy ALL of these environment variables from `pms-backend` to `pms-worker`:**

#### Core Application
```
DATABASE_URL
ENCRYPTION_KEY
JWT_SECRET
SUPABASE_JWT_SECRET
JWT_AUDIENCE
```

#### Module Feature Flags
```
CHANNEL_MANAGER_ENABLED=true
MODULES_ENABLED=true
```

#### Redis & Celery
```
REDIS_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
```

#### Health Checks
```
ENABLE_REDIS_HEALTHCHECK=true
ENABLE_CELERY_HEALTHCHECK=true
```

#### Optional (if used in backend)
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SENTRY_DSN
LOG_LEVEL
ENVIRONMENT
```

**Why copy all variables?**
- Worker executes the same application code as backend
- Tasks may need database access, encryption, JWT validation, etc.
- Missing variables cause cryptic task failures

**Important Notes:**
- Worker should NOT have public domains configured
- Worker does NOT need port exposure (but Coolify may require "Ports Exposes" field - use `8000`)
- Worker and backend must share the same Redis/Celery configuration

---

### Redis URL Format + Password Encoding

#### Redis URL Structure

Redis with authentication uses this format:
```
redis://:<PASSWORD>@<HOST>:<PORT>/<DB>
```

**Example:**
```bash
redis://:my_secure_password_123@coolify-redis:6379/0
```

**Components:**
- `<PASSWORD>`: Redis requirepass value
- `<HOST>`: Redis service name (e.g., `coolify-redis`)
- `<PORT>`: Redis port (usually `6379`)
- `<DB>`: Redis database number (usually `0`)

#### Special Characters MUST Be URL-Encoded

**⚠️ CRITICAL: Password Encoding Required**

If your Redis password contains special characters (`+`, `=`, `@`, `:`, `/`, `?`, `#`, `&`, `%`), you **MUST** URL-encode the password in environment variables.

**Why?**
- Special characters have meaning in URLs
- `+` is interpreted as space if not encoded
- `@` and `:` are URL delimiters
- Unencoded passwords cause "Authentication required" or "invalid username-password pair" errors

#### How to URL-Encode Password

**Location:** HOST-SERVER-TERMINAL (your local machine or SSH to host server)

**Method 1: Using Python (recommended)**
```bash
python3 - <<'PY'
import urllib.parse
# Replace PASTE_PASSWORD_HERE with your actual Redis password
password = "PASTE_PASSWORD_HERE"
encoded = urllib.parse.quote(password, safe="")
print(f"Encoded password: {encoded}")
PY
```

**Example:**
```bash
# Original password: my+pass=word@123
# Encoded password: my%2Bpass%3Dword%40123
```

**Method 2: Using Node.js**
```bash
node -e "console.log(encodeURIComponent('PASTE_PASSWORD_HERE'))"
```

**Method 3: Online tool** (not recommended for production secrets)
- Use https://www.urlencoder.org/ (avoid for sensitive passwords)

#### Setting Encoded Password in Environment Variables

**Example with encoded password:**
```bash
# Original password: complex+pass=word
# Encoded password: complex%2Bpass%3Dword

REDIS_URL=redis://:complex%2Bpass%3Dword@coolify-redis:6379/0
CELERY_BROKER_URL=redis://:complex%2Bpass%3Dword@coolify-redis:6379/0
CELERY_RESULT_BACKEND=redis://:complex%2Bpass%3Dword@coolify-redis:6379/0
```

**Where to set:**
1. Coolify Dashboard → `pms-backend` → Environment Variables
2. Coolify Dashboard → `pms-worker` → Environment Variables
3. **Both apps must have identical Redis URLs**

---

### Worker Start Command

**NOTE:** This section applies to **Nixpacks build pack** deployments. If using **Dockerfile.worker** (recommended), the Start Command is **automatic** and cannot be set in Coolify UI. See [Alternative: Build with Dockerfile.worker](#alternative-build-with-dockerfileworker-recommended-for-non-root) for Dockerfile deployments.

**Location:** Coolify Dashboard → `pms-worker` → Settings → Start Command

**Command (Nixpacks only):**
```bash
celery -A app.channel_manager.core.sync_engine:celery_app --broker "$CELERY_BROKER_URL" --result-backend "$CELERY_RESULT_BACKEND" worker -l INFO
```

**Breakdown:**
- `-A app.channel_manager.core.sync_engine:celery_app`: Celery app module path
- `--broker "$CELERY_BROKER_URL"`: Redis broker URL (from environment)
- `--result-backend "$CELERY_RESULT_BACKEND"`: Redis result backend (from environment)
- `worker`: Run as worker process
- `-l INFO`: Log level (INFO for production, DEBUG for troubleshooting)

**Alternative log levels:**
- `-l DEBUG`: Verbose logging (troubleshooting)
- `-l WARNING`: Minimal logging (production)
- `-l ERROR`: Only errors

**Why use Dockerfile.worker instead?**
- Runs as non-root user (no SecurityWarning)
- Includes wait-for-deps preflight (prevents DNS failures)
- Configurable via environment variables
- Start Command handled automatically by Dockerfile CMD

---

### Deployment Steps

#### Step 1: Verify Redis Password

**Location:** HOST-SERVER-TERMINAL

Get Redis password from Coolify Redis service configuration or container:

```bash
# Option A: Check Redis container command/env
docker inspect coolify-redis | grep -i requirepass

# Option B: Check Redis config inside container
docker exec -it coolify-redis cat /etc/redis/redis.conf | grep requirepass

# Note the password - you'll need it for URL encoding
```

#### Step 2: URL-Encode Password

**Location:** HOST-SERVER-TERMINAL

```bash
python3 - <<'PY'
import urllib.parse
# Replace with your actual Redis password
password = "YOUR_REDIS_PASSWORD_HERE"
encoded = urllib.parse.quote(password, safe="")
print(f"Original: {password}")
print(f"Encoded:  {encoded}")
print(f"\nRedis URL: redis://:{encoded}@coolify-redis:6379/0")
PY
```

Copy the encoded password for next steps.

#### Step 3: Test Redis Connection

**Location:** HOST-SERVER-TERMINAL

```bash
# Test with raw password (before encoding)
redis-cli -h coolify-redis -a 'YOUR_RAW_PASSWORD' ping
# Expected output: PONG

# If you get "Authentication required" or "invalid username-password pair":
# - Password is wrong
# - Redis requirepass is not set
# - Network connectivity issue
```

#### Step 4: Configure pms-backend Environment

**Location:** Coolify Dashboard → pms-backend → Environment Variables

Add or update these variables with your encoded password:

```bash
REDIS_URL=redis://:YOUR_ENCODED_PASSWORD@coolify-redis:6379/0
CELERY_BROKER_URL=redis://:YOUR_ENCODED_PASSWORD@coolify-redis:6379/0
CELERY_RESULT_BACKEND=redis://:YOUR_ENCODED_PASSWORD@coolify-redis:6379/0
ENABLE_REDIS_HEALTHCHECK=true
ENABLE_CELERY_HEALTHCHECK=true
CHANNEL_MANAGER_ENABLED=true
```

Click **Save** and **Restart** pms-backend.

#### Step 5: Create pms-worker App

**Location:** Coolify Dashboard

1. Click **Add New Resource > Application**
2. Select **Git Repository**
3. Configure:
   - Repository: Same as pms-backend
   - Branch: Same as pms-backend
   - Base Directory: `/backend`
   - Build Pack: Nixpacks
   - Start Command: (see [Worker Start Command](#worker-start-command))
   - Ports Exposes: `8000` (required by Coolify, not actually used)
4. **Do NOT configure public domain** (worker doesn't serve HTTP)

#### Step 6: Configure pms-worker Environment

**Location:** Coolify Dashboard → pms-worker → Environment Variables

**Copy ALL environment variables from pms-backend**, especially:

```bash
DATABASE_URL=<same as backend>
ENCRYPTION_KEY=<same as backend>
JWT_SECRET=<same as backend>
SUPABASE_JWT_SECRET=<same as backend>
JWT_AUDIENCE=<same as backend>

REDIS_URL=redis://:YOUR_ENCODED_PASSWORD@coolify-redis:6379/0
CELERY_BROKER_URL=redis://:YOUR_ENCODED_PASSWORD@coolify-redis:6379/0
CELERY_RESULT_BACKEND=redis://:YOUR_ENCODED_PASSWORD@coolify-redis:6379/0

ENABLE_REDIS_HEALTHCHECK=true
ENABLE_CELERY_HEALTHCHECK=true
CHANNEL_MANAGER_ENABLED=true
MODULES_ENABLED=true

# Optional (if used)
SUPABASE_URL=<same as backend>
SUPABASE_SERVICE_ROLE_KEY=<same as backend>
SENTRY_DSN=<same as backend>
LOG_LEVEL=INFO
ENVIRONMENT=production
```

Click **Save** and **Deploy**.

#### Step 7: Verify Deployment

Wait for both apps to deploy, then proceed to [Verification Steps](#verification-steps).

---

### Verification Steps

#### 1. Check /health/ready Endpoint

**Location:** Browser or curl from HOST-SERVER-TERMINAL

```bash
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq .
```

**Expected output:**
```json
{
  "status": "ready",
  "checks": {
    "database": "up",
    "redis": "up",
    "celery": "up"
  },
  "celery_workers": [
    "celery@<worker-hostname>"
  ]
}
```

**If redis shows "down":**
- Check Redis URL encoding
- Verify Redis password matches
- Check network connectivity

**If celery shows "down":**
- Worker not running
- Worker cannot connect to Redis
- Wrong start command

#### 2. Check Worker Logs

**Location:** Coolify Dashboard → pms-worker → Logs

**Look for:**
```
[INFO] Connected to redis://coolify-redis:6379/0
[INFO] celery@<hostname> ready.
[INFO] Tasks: [...list of registered tasks...]
```

**Red flags:**
```
Authentication required
Connection refused
invalid username-password pair
Cannot connect to redis
```

#### 3. Test Celery Connection from Backend

**Location:** Coolify Terminal (pms-backend container)

```bash
# Ping Celery workers
celery -A app.channel_manager.core.sync_engine:celery_app \
  --broker "$CELERY_BROKER_URL" \
  inspect ping -t 3

# Expected output:
# -> celery@<worker-hostname>: {'ok': 'pong'}
```

**If timeout:**
- Worker not running
- Worker on different network
- Redis broker unreachable

#### 4. Verify Redis Connection from Backend

**Location:** Coolify Terminal (pms-backend container)

```bash
# Test Redis connection (masked password)
python3 - <<'PY'
import os
import redis
from urllib.parse import urlparse

redis_url = os.environ.get("REDIS_URL", "")
parsed = urlparse(redis_url)

# Mask password for logging
masked_url = redis_url.replace(parsed.password or "", "***") if parsed.password else redis_url
print(f"Testing Redis connection to: {masked_url}")

try:
    r = redis.from_url(redis_url)
    result = r.ping()
    print(f"✓ Redis PING successful: {result}")
    print(f"✓ Password length: {len(parsed.password or '')}")
except Exception as e:
    print(f"✗ Redis connection failed: {e}")
PY
```

**Expected output:**
```
Testing Redis connection to: redis://:***@coolify-redis:6379/0
✓ Redis PING successful: True
✓ Password length: 16
```

#### 5. Test Channel Sync Endpoint

**Location:** Browser or curl

```bash
# Trigger a manual sync (requires valid channel connection ID)
curl -X POST https://api.fewo.kolibri-visions.de/api/v1/channel-connections/{id}/sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "full"}'
```

**Expected:**
- HTTP 200 OK
- Returns task IDs
- Check worker logs for task execution

---

### Troubleshooting

#### Redis Authentication Errors

**Symptom:**
```
Authentication required.
invalid username-password pair or user is disabled.
```

**Causes & Solutions:**

1. **Password not URL-encoded**
   - Solution: URL-encode password (see [Password Encoding](#how-to-url-encode-password))
   - Example: `pass+word` → `pass%2Bword`

2. **Password mismatch**
   - Solution: Verify Redis requirepass:
     ```bash
     docker exec -it coolify-redis redis-cli CONFIG GET requirepass
     ```
   - Ensure encoded password matches requirepass

3. **Wrong Redis URL format**
   - Correct: `redis://:password@host:6379/0`
   - Wrong: `redis://password@host:6379/0` (missing colon)
   - Wrong: `redis://user:password@host:6379/0` (Redis usually no username)

#### Celery Worker Not Detected

**Symptom:**
```
No active Celery workers detected
Celery inspect timeout
```

**Causes & Solutions:**

1. **Worker not running**
   - Check Coolify: pms-worker app status
   - View logs: Look for "ready" message
   - Restart worker app

2. **Wrong start command**
   - Verify Start Command in Coolify matches [Worker Start Command](#worker-start-command)
   - Check for typos in module path

3. **Worker cannot reach Redis**
   - Verify CELERY_BROKER_URL is correct
   - Check network: worker and Redis on same Docker network
   - Test Redis connection from worker container

4. **Environment variables missing**
   - Ensure worker has all required env vars
   - Compare with backend environment variables

#### Database Connection Issues

**Symptom:**
```
Connection refused to database
Database name resolution failed
```

**Causes & Solutions:**

1. **DNS flapping after deploy**
   - Wait 30-60 seconds after deployment
   - DNS resolution can be temporarily unstable
   - Check again after services stabilize

2. **Network misconfiguration**
   - Worker must be on Coolify network AND Supabase network
   - Verify network configuration in Coolify
   - Check docker network ls on host

3. **Wrong DATABASE_URL**
   - Verify worker has correct DATABASE_URL
   - Must match backend exactly
   - Test connection from worker container:
     ```bash
     python3 -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect(os.environ['DATABASE_URL']).close())"
     ```

4. **Worker database operations fail**
   - **Symptom:** Worker logs show `"Database is temporarily unavailable"` or `"Failed to update sync log ... 503"`
   - **Cause:** Celery workers must NOT rely on FastAPI lifespan pool (pool doesn't exist in worker context)
   - **Solution (Current Architecture):** Workers use direct `asyncpg.connect()` connections
     - `_check_database_availability()`: Creates short-lived connection with 5s timeout for health checks
     - `_update_log_status()`: Creates connection per sync log update with JSON/JSONB codec registration
     - All connections are properly closed in finally blocks (fork/event-loop safe)
   - **Verification checklist:**
     a) Worker is connected to supabase network (check Coolify network config)
     b) DATABASE_URL environment variable is set correctly in worker
     c) Worker has latest code with direct connection architecture
   - **Test from worker container:**
     ```bash
     docker exec pms-worker python3 -c "import asyncpg; import asyncio; import os; asyncio.run(asyncpg.connect(os.environ['DATABASE_URL']).close()); print('DB OK')"
     ```

#### Worker Logs Show Task Failures

**Symptom:**
```
Task failed: KeyError, AttributeError, etc.
```

**Causes & Solutions:**

1. **Missing environment variables**
   - Worker needs same env as backend
   - Check for missing: ENCRYPTION_KEY, JWT_SECRET, etc.

2. **Code version mismatch**
   - Worker and backend must be on same git commit
   - Redeploy both to sync versions

3. **Database schema mismatch**
   - Run migrations if needed
   - Ensure worker has latest schema

#### Password Special Characters Reference

**Characters requiring URL encoding:**

| Character | URL Encoded | Example |
|-----------|-------------|---------|
| `+` | `%2B` | `pass+word` → `pass%2Bword` |
| `=` | `%3D` | `pass=word` → `pass%3Dword` |
| `@` | `%40` | `pass@word` → `pass%40word` |
| `:` | `%3A` | `pass:word` → `pass%3Aword` |
| `/` | `%2F` | `pass/word` → `pass%2Fword` |
| `?` | `%3F` | `pass?word` → `pass%3Fword` |
| `#` | `%23` | `pass#word` → `pass%23word` |
| `&` | `%26` | `pass&word` → `pass%26word` |
| `%` | `%25` | `pass%word` → `pass%25word` |
| Space | `%20` | `pass word` → `pass%20word` |

**Tool to check encoding:**
```bash
python3 -c "import urllib.parse; print(urllib.parse.quote('YOUR_PASSWORD', safe=''))"
```

---

### Quick Smoke (5 minutes)

**Purpose:** Rapid health check after Redis/Celery deployment or configuration changes.

**Prerequisites:**

Check in **Coolify UI**:
- ✅ `pms-backend` deployed and running (green status)
- ✅ `pms-worker` deployed and running (green status)
- ✅ `coolify-redis` service running
- ✅ Required environment variables set (see [Required Environment Variables](#required-environment-variables))

**Execution Location:** HOST-SERVER-TERMINAL (SSH to host server)

#### Step 1: Load Environment

```bash
# Load environment file
source /root/pms_env.sh

# Verify required variables are set
echo "SB_URL: ${SB_URL:0:30}..."
echo "EMAIL: $EMAIL"
```

#### Step 2: Get JWT Token

```bash
# Fetch JWT token from Supabase auth
TOKEN="$(curl -sS "$SB_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')"

# Verify token (without printing secret)
echo "TOKEN len=${#TOKEN} parts=$(awk -F. '{print NF}' <<<"$TOKEN")"
# Expected: len > 100, parts = 3 (JWT format: header.payload.signature)
```

**Expected output:**
```
TOKEN len=857 parts=3
```

**If token fetch fails:**
- Check Supabase URL: `curl -s "$SB_URL/health" | head -c 50`
- Verify credentials in `/root/pms_env.sh`
- Check network connectivity to Supabase

#### Step 3: Check Health Endpoint

```bash
# Check /health/ready endpoint
curl -k -sS https://api.fewo.kolibri-visions.de/health/ready
```

**Expected output:**
```json
{
  "status": "ready",
  "checks": {
    "database": "up",
    "redis": "up",
    "celery": "up"
  },
  "celery_workers": [
    "celery@pms-worker-abc123"
  ]
}
```

**If redis shows "down":**
- Check Redis URL encoding (see [Password Encoding](#redis-url-format--password-encoding))
- Verify Redis service is running: `docker ps | grep redis`

**If celery shows "down":**
- Check worker is running: `docker ps | grep worker`
- View worker logs: Coolify UI → pms-worker → Logs

**If database shows "down":**
- Check DATABASE_URL in backend environment
- Verify Supabase database is running

#### Step 4: Get Channel Connection ID

```bash
# Fetch first channel connection ID
# NOTE: Use -L to follow redirects (trailing slash redirect)
CID="$(curl -k -sS -L "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[0]["id"] if d else "")')"

echo "CID=$CID"
```

**Expected output:**
```
CID=550e8400-e29b-41d4-a716-446655440000
```

**If CID is empty:**
- No channel connections exist
- Create one first via POST `/api/v1/channel-connections`
- Or use Swagger UI (`/docs`) to create a test connection

**If you get 307 redirect:**
- Add trailing slash: `/api/v1/channel-connections/`
- Or use `-L` flag (already included above)

**If you get 401 Unauthorized:**
- Token expired or invalid
- Re-fetch token (Step 2)
- Verify CHANNEL_MANAGER_ENABLED=true in backend

#### Step 5: Trigger Manual Sync

```bash
# Trigger full sync on channel connection
curl -k -sS -i -X POST "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type":"full"}'
```

**Expected output:**
```
HTTP/2 200
content-type: application/json

{
  "status": "queued",
  "message": "Sync queued successfully",
  "task_ids": ["abc123-def456-..."]
}
```

**If you get 405 Method Not Allowed:**
- Check OpenAPI spec: endpoint requires POST
- Verify URL is correct (no trailing slash after `$CID/sync`)

**If you get 422 Validation Error:**
- CID must be valid UUID
- Request body must include `{"sync_type":"full"}` (or "availability", "pricing", "bookings")

**If you get 404 Not Found:**
- Channel connection doesn't exist
- Verify CID is correct: `echo $CID`

#### Step 6: Check Sync Logs

```bash
# Fetch sync logs (save to file to avoid pipe JSON errors)
OUT="/tmp/sync_logs.json"
HDR="/tmp/sync_logs.headers.txt"
CODE="$(curl -k -sS -L -D "$HDR" -o "$OUT" -w '%{http_code}' \
  "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync-logs?limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN")"

echo "HTTP=$CODE"
head -c 200 "$OUT"; echo
```

**Parse logs:**
```bash
python3 - <<'PY'
import json
d = json.load(open("/tmp/sync_logs.json"))
logs = d.get("logs", [])
print(f"Total logs: {len(logs)}")
if logs:
    last = logs[0]
    print(f"Last operation: {last.get('operation_type')}")
    print(f"Last status: {last.get('status')}")
    print(f"Last created_at: {last.get('created_at')}")
PY
```

**Expected output:**
```
HTTP=200
Total logs: 5
Last operation: full_sync
Last status: success
Last created_at: 2025-12-27T10:30:45.123Z
```

**If last.status is "failed":**
- Check worker logs for task errors
- Review sync_logs error_message field
- Verify channel connection credentials are valid

**If HTTP=404:**
- No sync logs exist for this connection
- Sync may not have completed yet (check worker logs)

---

### Deep Diagnostics (15–30 minutes)

**Purpose:** Comprehensive troubleshooting for Redis, Celery, and Channel Manager issues.

**When to use:**
- Quick Smoke fails
- Persistent connection errors
- Task execution failures
- After configuration changes

---

#### Common HTTP Responses Reference

Understanding API response codes:

| Code | Meaning | Common Causes | Solution |
|------|---------|---------------|----------|
| 200 | Success | - | Expected for GET/POST/PATCH |
| 201 | Created | - | Expected for POST (create) |
| 307 | Temporary Redirect | Missing trailing slash | Add `/` or use `-L` flag |
| 401 | Unauthorized | Missing/invalid token | Re-fetch JWT token |
| 403 | Forbidden | Insufficient permissions | Check user role/permissions |
| 404 | Not Found | Wrong URL or missing resource | Verify endpoint and resource ID |
| 405 | Method Not Allowed | Wrong HTTP method | Check OpenAPI: `/sync` needs POST |
| 422 | Validation Error | Invalid request body | CID must be UUID; sync needs `sync_type` |
| 500 | Internal Server Error | Backend exception | Check backend logs |
| 503 | Service Unavailable | Database/Redis down | Check /health/ready |

**Examples:**

**307 Redirect (trailing slash):**
```bash
# Without -L flag, you'll see:
curl -k -i "https://api.fewo.kolibri-visions.de/api/v1/channel-connections"
# HTTP/2 307
# location: /api/v1/channel-connections/

# Solution: Add -L or trailing slash
curl -k -L "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/"
```

**Common symptom with 307 redirects:**
```bash
# Without -L, curl returns empty body + redirect header
curl -k "https://api.fewo.kolibri-visions.de/api/v1/channel-connections" > /tmp/output.json
# HTTP_CODE=307, output file is empty

# Parsing fails with JSONDecodeError:
cat /tmp/output.json | jq .
# jq: parse error: Invalid numeric literal at line 1, column 2

# Fix: Always use -L to follow redirects
curl -k -L "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/" > /tmp/output.json
# HTTP_CODE=200, output contains valid JSON array
```

**Note:** When using `curl` in runbook examples for endpoints like:
- `GET /api/v1/channel-connections?...`
- `GET /api/v1/availability/blocks?...`
- Any GET endpoint that may have trailing slash redirects

Always include `-L` flag to automatically follow 307 redirects and avoid empty response bodies.

**422 Validation (sync endpoint):**
```bash
# Missing sync_type causes 422
curl -X POST ".../channel-connections/$CID/sync" -H "..." -d '{}'

# Solution: Include required field
curl -X POST ".../channel-connections/$CID/sync" -H "..." \
  -d '{"sync_type":"full"}'
```

---

#### Redis Connection Diagnostics

**Execution Location:** HOST-SERVER-TERMINAL

##### 1. Get Redis Password (requirepass)

**⚠️ Security:** Do NOT paste raw password in production logs/docs.

```bash
# Extract requirepass from Redis container config
# This shows the password - use with caution
docker inspect coolify-redis --format '{{range .Config.Cmd}}{{println .}}{{end}}' \
  | awk 'p{print; exit} $0=="--requirepass"{p=1}'

# Store in variable (don't echo to logs)
REDIS_PASS="$(docker inspect coolify-redis --format '{{range .Config.Cmd}}{{println .}}{{end}}' \
  | awk 'p{print; exit} $0=="--requirepass"{p=1}')"

# Verify password length (safe to log)
echo "Redis password length: ${#REDIS_PASS}"
```

##### 2. Test Redis Connection

```bash
# Test with raw password
redis-cli -h coolify-redis -a "$REDIS_PASS" ping
# Expected output: PONG

# If you get "Authentication required":
# - Password is wrong
# - Redis requirepass not set
# - Network connectivity issue
```

##### 3. Verify Password Encoding

**Compare Redis password with REDIS_URL:**

```bash
# Get decoded password from REDIS_URL (from pms-backend env)
python3 - <<'PY'
import os
import urllib.parse

# Get REDIS_URL from environment (set this to your actual REDIS_URL)
# In production: docker exec pms-backend env | grep REDIS_URL
redis_url = os.environ.get("REDIS_URL", "redis://:password@host:6379/0")

parsed = urllib.parse.urlparse(redis_url)
decoded_pass = urllib.parse.unquote(parsed.password or "")

print(f"REDIS_URL password length: {len(decoded_pass)}")
print(f"REDIS_URL password SHA256: ", end="")

import hashlib
print(hashlib.sha256(decoded_pass.encode()).hexdigest()[:16] + "...")
PY
```

**Compare with Redis requirepass:**
```bash
# Get SHA256 of Redis requirepass (don't print password)
echo -n "$REDIS_PASS" | sha256sum | cut -c1-16
```

**If hashes don't match:**
- Password mismatch between Redis and REDIS_URL
- Check if password needs URL encoding
- Re-encode password: see [Password Encoding](#how-to-url-encode-password)

##### 4. Test Connection from Backend Container

**Execution Location:** Coolify Terminal (pms-backend container)

```bash
# Test Redis connection from backend
python3 - <<'PY'
import os
import redis
from urllib.parse import urlparse

redis_url = os.environ.get("REDIS_URL", "")
parsed = urlparse(redis_url)

# Mask password for logging
masked_url = redis_url.replace(parsed.password or "", "***") if parsed.password else redis_url
print(f"Testing: {masked_url}")

try:
    r = redis.from_url(redis_url)
    result = r.ping()
    print(f"✓ Redis PING: {result}")
    print(f"✓ Password length: {len(parsed.password or '')}")

    # Test basic operations
    r.set("test_key", "test_value", ex=10)
    val = r.get("test_key")
    print(f"✓ SET/GET test: {val.decode() if val else 'None'}")
except Exception as e:
    print(f"✗ Redis connection failed: {e}")
PY
```

---

#### Celery Worker Diagnostics

**Execution Location:** HOST-SERVER-TERMINAL

##### 1. Verify Worker Container Exists

```bash
# Check if worker container is running
docker ps -a | egrep -i 'pms-worker|celery|worker'

# Expected: pms-worker container with "Up" status
# If "Exited": worker crashed - check logs
```

##### 2. Check Worker Logs for Tasks

```bash
# View recent worker logs (last 60 minutes)
# Replace <worker_container> with actual container name/ID
docker logs <worker_container> --since 60m | egrep -n 'received|succeeded|ERROR|Traceback'

# Look for:
# - "Task ... received" (task queued)
# - "Task ... succeeded" (task completed)
# - "ERROR" or "Traceback" (task failed)
```

**Search for specific task ID:**
```bash
# If you have a task ID from sync trigger response
TASK_ID="abc123-def456-..."
docker logs <worker_container> | egrep -n "$TASK_ID"
```

##### 3. Test Celery Connection from Backend

**Execution Location:** Coolify Terminal (pms-backend container)

```bash
# Ping Celery workers from backend
celery -A app.channel_manager.core.sync_engine:celery_app \
  --broker "$CELERY_BROKER_URL" \
  inspect ping -t 3

# Expected output:
# -> celery@pms-worker-abc123: {'ok': 'pong'}
```

**If timeout:**
```bash
# Check broker URL is correct
echo "CELERY_BROKER_URL (masked):"
python3 -c "import os; url=os.environ.get('CELERY_BROKER_URL',''); print(url[:20] + '***' + url[-10:] if len(url) > 30 else url)"

# Verify worker can reach Redis
docker exec <worker_container> redis-cli -h coolify-redis -a "$REDIS_PASS" ping
```

##### 4. Check Active Workers and Registered Tasks

**Execution Location:** Coolify Terminal (pms-backend container)

```bash
# List active workers
celery -A app.channel_manager.core.sync_engine:celery_app \
  --broker "$CELERY_BROKER_URL" \
  inspect active

# List registered tasks
celery -A app.channel_manager.core.sync_engine:celery_app \
  --broker "$CELERY_BROKER_URL" \
  inspect registered
```

**Expected output includes:**
- `app.channel_manager.sync_tasks.full_sync`
- `app.channel_manager.sync_tasks.availability_sync`
- etc.

---

#### Coolify / Nixpacks Quirks

##### Start Command Quoting Issues

**Problem:** Quoting `$ENV_VAR` in Coolify Start Command can break Nixpacks build.

**Bad (may break):**
```bash
celery -A app.celery_app --broker "$CELERY_BROKER_URL" worker
```

**Good (recommended):**
```bash
# Rely on environment variables (unquoted)
celery -A app.channel_manager.core.sync_engine:celery_app worker -l INFO
```

**Why?** Nixpacks may interpret quotes literally during build phase.

**Workaround:** Use simple start command, ensure `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are in environment variables.

##### COOLIFY_URL Null Issue

**Symptom:** Build fails with "COOLIFY_URL is null" or similar.

**Workaround:**
```bash
# Add to Environment Variables (build + runtime)
COOLIFY_URL=https://coolify.example.com
# Or any non-empty string - value may not matter for worker
```

---

#### Database Connection Diagnostics

##### DNS Flapping After Deploy

**Symptom:** `/health/ready` shows database errors like:
```
"name resolution failed"
"connection refused"
```

**Cause:** Docker DNS can be temporarily unstable after deployment.

**Solution:**
1. Wait 30-60 seconds after deployment
2. Recheck `/health/ready`
3. If persists, check network configuration

##### Network Configuration

**Execution Location:** HOST-SERVER-TERMINAL

```bash
# Check if pms-backend is on both networks
docker inspect pms-backend | grep -A 10 '"Networks"'

# Expected: coolify network AND supabase network
```

**If backend can't resolve `supabase-db`:**
```bash
# Test DNS from backend container
docker exec pms-backend nslookup supabase-db

# If fails, backend may not be on supabase network
# Fix: Add supabase network in Coolify UI
```

##### Database URL Verification

**Execution Location:** Coolify Terminal (pms-backend container)

```bash
# Test database connection (masked URL)
python3 - <<'PY'
import os
import asyncio
import asyncpg
from urllib.parse import urlparse

db_url = os.environ.get("DATABASE_URL", "")
parsed = urlparse(db_url)

# Mask password
masked = db_url.replace(parsed.password or "", "***") if parsed.password else db_url
print(f"Testing: {masked}")

async def test_connection():
    try:
        conn = await asyncpg.connect(db_url)
        version = await conn.fetchval("SELECT version()")
        print(f"✓ Connected: {version[:50]}...")
        await conn.close()
    except Exception as e:
        print(f"✗ Connection failed: {e}")

asyncio.run(test_connection())
PY
```

---

#### Worker Configuration Checklist

**Verify in Coolify UI → pms-worker:**

- ✅ **No public domain configured** (worker doesn't serve HTTP)
- ✅ **No Traefik labels** (no proxy/routing needed)
- ✅ **Ports Exposes:** `8000` (Coolify UI requirement, not actually used)
- ✅ **Start Command:** `celery -A app.channel_manager.core.sync_engine:celery_app worker -l INFO`
- ✅ **Environment variables:** All copied from pms-backend
- ✅ **Network:** On same Docker network as Redis and backend

**Common mistakes:**
- Adding public domain → Worker gets Traefik labels → Port conflicts
- Missing environment variables → Worker can't connect to database/Redis
- Wrong start command → Worker starts but doesn't register tasks

---

#### Special Characters in Passwords

**Characters requiring URL encoding:**

| Character | URL Encoded | Example |
|-----------|-------------|---------|
| `+` | `%2B` | `pass+word` → `pass%2Bword` |
| `=` | `%3D` | `pass=word` → `pass%3Dword` |
| `@` | `%40` | `pass@word` → `pass%40word` |
| `:` | `%3A` | `pass:word` → `pass%3Aword` |
| `/` | `%2F` | `pass/word` → `pass%2Fword` |
| `?` | `%3F` | `pass?word` → `pass%3Fword` |
| `#` | `%23` | `pass#word` → `pass%23word` |
| `&` | `%26` | `pass&word` → `pass%26word` |
| `%` | `%25` | `pass%word` → `pass%25word` |

**URL encoding script:**
```bash
python3 - <<'PY'
import urllib.parse
password = "YOUR_PASSWORD_HERE"
encoded = urllib.parse.quote(password, safe="")
print(f"Original: {password}")
print(f"Encoded:  {encoded}")
PY
```

**Why `+` is problematic:**
- In URLs, `+` is interpreted as space (URL encoding legacy)
- `redis://:pass+word@host` → server sees `redis://:pass word@host`
- Must encode as `redis://:pass%2Bword@host`

---

#### Execution Location Quick Reference

| Task | Location | Access Method |
|------|----------|---------------|
| Check Coolify app status | Coolify UI | Browser → Dashboard |
| Get Redis password | HOST-SERVER-TERMINAL | SSH to host, `docker inspect` |
| Test Redis connection | HOST-SERVER-TERMINAL | `redis-cli -h coolify-redis` |
| Check worker logs | Coolify UI or HOST | Dashboard → Logs or `docker logs` |
| Test Celery ping | Coolify Terminal (backend) | Dashboard → pms-backend → Terminal |
| Verify environment vars | Coolify UI | Dashboard → Environment Variables |
| Run smoke tests | HOST-SERVER-TERMINAL | SSH + `/root/pms_env.sh` |

---

## Channel Manager Error Handling & Retry Logic

**Purpose:** Understand how the Channel Manager handles failures and retries sync operations.

### Overview

The Channel Manager implements comprehensive error handling at two layers:
1. **API Layer** (immediate retry for user-facing endpoints)
2. **Celery Task Layer** (background retry for async operations)

Both layers use exponential backoff to prevent overwhelming failed services.

---

### Exponential Backoff Strategy

**Formula:** `delay = base_delay * (2 ^ retry_count)`

**Default Configuration:**
- Base delay: 1 second
- Max retries: 3
- Total duration: 7 seconds (1s + 2s + 4s)

**Retry Progression:**
```
Attempt 1: Execute immediately
├─ Fails → Wait 1 second (2^0)
Attempt 2: Execute after 1s delay
├─ Fails → Wait 2 seconds (2^1)
Attempt 3: Execute after 2s delay
├─ Fails → Wait 4 seconds (2^2)
Attempt 4: Execute after 4s delay
└─ Fails → Mark as permanently failed
```

**Benefits:**
- ✅ Fast recovery from transient failures (starts with 1s)
- ✅ Reduces load on failing services (exponentially increasing delays)
- ✅ Predictable total duration (7 seconds max vs. previous 180 seconds)

---

### Error Types and Handling

#### 1. Database Unavailable (503)

**Errors Caught:**
```python
asyncpg.PostgresError
asyncpg.exceptions.PostgresConnectionError
asyncpg.exceptions.ConnectionDoesNotExistError
asyncpg.exceptions.TooManyConnectionsError
```

**Response:**
```json
{
  "error": "service_unavailable",
  "message": "Database is temporarily unavailable.",
  "retry_count": 3
}
```

**What Happens:**
1. **Pre-flight Check**: Database availability validated BEFORE sync
2. **Retry**: Up to 3 retries with exponential backoff (1s, 2s, 4s)
3. **Logging**: Each retry logged with countdown duration
4. **Sync Log**: Status updated to "running" with retry details
5. **Final Failure**: After 3 retries, marked as "failed" with error details

**Example Log Output:**
```
WARNING: Database error on attempt 2/4: connection timeout. Retrying in 2 seconds...
ERROR: Database still unavailable after 3 retries. Final error: connection timeout
```

#### 2. General Exceptions (500)

**Response:**
```json
{
  "error": "internal_server_error",
  "message": "Failed to trigger availability sync: [error details]"
}
```

**What Happens:**
1. **Retry**: Up to 3 retries with exponential backoff
2. **Logging**: Full exception stacktrace logged
3. **Sync Log**: Error type and message stored in JSONB details
4. **Best-Effort Cleanup**: Attempts to update sync log even on failure

**Example Log Output:**
```
ERROR: Error updating availability on airbnb (task_id=abc123, retry=1): API timeout
WARNING: Retrying task abc123 after error (countdown=2s, retry=2/3)
```

#### 3. Validation Errors (400)

**No Retry** — These are permanent failures requiring user correction.

**Common Causes:**
- Invalid `sync_type` (must be "availability" or "pricing")
- Invalid `platform` (must be one of: airbnb, booking_com, expedia, etc.)
- Invalid UUID format

**Response:**
```json
{
  "detail": "Invalid sync_type. Must be one of: ['availability', 'pricing']"
}
```

#### 4. Not Found (404)

**No Retry** — Resource doesn't exist.

**Response:**
```json
{
  "detail": "Property not found or does not belong to your agency"
}
```

---

### Database Pre-flight Check

**When:** Before every sync operation
**Why:** Fail-fast to avoid wasted work
**How:** Simple `SELECT 1` query to verify connection pool health

**Implementation:**
```python
async def _check_database_availability():
    """Verify database is reachable before sync"""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
```

**Benefits:**
- ✅ Detects DB issues immediately (before triggering tasks)
- ✅ Clear error message: "Database is temporarily unavailable."
- ✅ Prevents queuing tasks that will fail

---

### Celery Task Retry Logic

**Configured on Task Decorator:**
```python
@celery_app.task(bind=True, max_retries=3, autoretry_for=(Retry,))
def update_channel_availability(self, ...):
```

**Retry Behavior:**
1. **Immediate Execution**: First attempt runs immediately
2. **Exponential Backoff**: Retries at 1s, 2s, 4s intervals
3. **Status Updates**: Sync log updated on each attempt
4. **Max Retries**: After 3 retries, task marked as permanently failed

**Retry Details Stored in Sync Log:**
```json
{
  "retry_count": 2,
  "error_type": "database_unavailable",
  "next_retry_seconds": 4
}
```

---

### Monitoring Retry Attempts

**Check /health/ready:**
```bash
curl https://api.your-domain.com/health/ready | jq .
```

**Check Sync Logs:**
```bash
curl https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs \
  -H "Authorization: Bearer TOKEN" | jq '.logs[0]'
```

**Sample Retry Log Entry:**
```json
{
  "id": "log-uuid",
  "operation_type": "availability_update",
  "status": "running",
  "details": {
    "retry_count": 2,
    "error_type": "database_unavailable",
    "next_retry_seconds": 4,
    "platform": "airbnb"
  },
  "error": null,
  "task_id": "celery-task-uuid",
  "created_at": "2025-12-28T10:00:00Z",
  "updated_at": "2025-12-28T10:00:03Z"
}
```

**Sample Failed Log Entry:**
```json
{
  "id": "log-uuid",
  "operation_type": "availability_update",
  "status": "failed",
  "details": {
    "retry_count": 3,
    "error_type": "database_unavailable"
  },
  "error": "Database unavailable after 3 retries: connection timeout",
  "task_id": "celery-task-uuid",
  "created_at": "2025-12-28T10:00:00Z",
  "updated_at": "2025-12-28T10:00:07Z"
}
```

---

## Mock Mode for Channel Providers

**Purpose:** Test Channel Manager endpoints without making real API calls to external platforms (Airbnb, Booking.com, etc.).

### Overview

Mock mode allows you to test connection health and sync operations without requiring actual platform credentials or API connectivity. This is useful for:

- **Development:** Testing Channel Manager logic without external dependencies
- **CI/CD:** Running integration tests without platform API keys
- **Staging:** Validating deployment before configuring real connections
- **Debugging:** Isolating issues from external API failures

### Configuration

**Environment Variable:** `CHANNEL_MOCK_MODE`

**Default:** `false` (real API calls)

**Enable Mock Mode:**
```bash
# In .env or Coolify environment variables
CHANNEL_MOCK_MODE=true
```

**Disable Mock Mode (Production):**
```bash
CHANNEL_MOCK_MODE=false
```

### Behavior

#### Test Connection Endpoint

**Endpoint:** `POST /api/v1/channel-connections/{connection_id}/test`

**Mock Mode Enabled (`CHANNEL_MOCK_MODE=true`):**
- Returns simulated health response without calling external platform APIs
- Health status based on connection's current `status` field:
  - `active` → `healthy=true`
  - `paused` / `inactive` → `healthy=false`
- Response includes `mock_mode=true` flag in details

**Mock Mode Disabled (Default):**
- Calls actual platform API for real health check
- Returns genuine connection status from external service

**Example Mock Response (200):**
```json
{
  "connection_id": "abc-123-456-...",
  "platform_type": "airbnb",
  "healthy": true,
  "message": "Mock: Connection is healthy",
  "details": {
    "mock_mode": true,
    "simulated": true,
    "connection_status": "active",
    "note": "This is a simulated response. Set CHANNEL_MOCK_MODE=false for real API calls."
  }
}
```

**Example Mock Response (Inactive Connection):**
```json
{
  "connection_id": "def-456-789-...",
  "platform_type": "booking_com",
  "healthy": false,
  "message": "Mock: Connection status is paused",
  "details": {
    "mock_mode": true,
    "simulated": true,
    "connection_status": "paused",
    "note": "This is a simulated response. Set CHANNEL_MOCK_MODE=false for real API calls."
  }
}
```

### Verification

**Check if Mock Mode is Active:**

WHERE: Coolify Terminal (pms-backend)
```bash
# Check environment variable
echo $CHANNEL_MOCK_MODE

# Test a connection and look for mock_mode flag
curl -X POST "$API/api/v1/channel-connections/$CID/test" \
  -H "Authorization: Bearer $TOKEN" | jq '.details.mock_mode'
# Expected: true (if mock mode enabled)
```

**Enable Mock Mode in Coolify:**
1. Navigate to: Coolify → Applications → pms-backend → Environment Variables
2. Add/Update: `CHANNEL_MOCK_MODE=true`
3. Restart backend: `docker restart pms-backend`

### Safety Considerations

**Production Deployment:**
- **ALWAYS** set `CHANNEL_MOCK_MODE=false` (or omit entirely) in production
- Mock mode is intended for testing/staging environments only
- Real sync operations will fail if mock mode is enabled (no actual API calls made)

**Audit Trail:**
- All mock responses include `mock_mode=true` flag for transparency
- Sync logs will reflect simulated operations (check `details.mock_mode`)

### Error Codes and Messages

When a connection test fails (mock or real mode), the response includes an `error_code` field for programmatic handling:

#### `CREDENTIALS_MISSING`

**Meaning:** Integration is enabled but platform-specific credentials are not configured.

**Example Response:**
```json
{
  "connection_id": "abc-123-456-...",
  "platform_type": "booking_com",
  "healthy": false,
  "message": "Booking.com credentials not configured. Add BOOKING_COM_API_KEY and BOOKING_COM_SECRET to environment.",
  "details": {
    "error_code": "CREDENTIALS_MISSING",
    "required_env_vars": ["BOOKING_COM_API_KEY", "BOOKING_COM_SECRET"],
    "mock_mode": false
  }
}
```

**Action Required:**
1. Add missing environment variables to Coolify (pms-backend)
2. Restart backend container
3. Re-test connection

#### `INTEGRATION_DISABLED`

**Meaning:** Platform integration is not implemented or is disabled in the current deployment.

**Example Response:**
```json
{
  "connection_id": "def-456-789-...",
  "platform_type": "expedia",
  "healthy": false,
  "message": "Expedia integration is disabled. Contact support to enable.",
  "details": {
    "error_code": "INTEGRATION_DISABLED",
    "mock_mode": false
  }
}
```

**Action Required:**
- Contact platform vendor or system administrator
- Enable integration via feature flag or code deployment

#### `CONNECTION_INACTIVE`

**Meaning:** Connection exists but is paused or inactive (not an error, but expected behavior).

**Example Response:**
```json
{
  "connection_id": "ghi-789-012-...",
  "platform_type": "airbnb",
  "healthy": false,
  "message": "Connection is paused",
  "details": {
    "error_code": "CONNECTION_INACTIVE",
    "connection_status": "paused",
    "mock_mode": true
  }
}
```

**Action Required:**
- Update connection status to `active` via Admin UI or API
- Re-test connection

### Mock Mode Platform Responses

When `CHANNEL_MOCK_MODE=true`, test connection returns platform-specific mock data:

#### Airbnb (Mock)
```json
{
  "connection_id": "...",
  "platform_type": "airbnb",
  "healthy": true,
  "message": "Mock: Connection is healthy",
  "details": {
    "mock_mode": true,
    "simulated": true,
    "connection_status": "active",
    "remote_account_id": "mock_airbnb_host_123456",
    "remote_listing_id": "mock_listing_987654",
    "capabilities": ["availability_sync", "pricing_sync", "booking_retrieval"],
    "note": "This is a simulated response. Set CHANNEL_MOCK_MODE=false for real API calls."
  }
}
```

#### Booking.com (Mock)
```json
{
  "connection_id": "...",
  "platform_type": "booking_com",
  "healthy": true,
  "message": "Mock: Connection is healthy",
  "details": {
    "mock_mode": true,
    "simulated": true,
    "connection_status": "active",
    "remote_account_id": "mock_booking_hotel_789012",
    "remote_listing_id": "mock_property_345678",
    "capabilities": ["availability_sync", "pricing_sync", "booking_retrieval", "channel_manager"],
    "note": "This is a simulated response. Set CHANNEL_MOCK_MODE=false for real API calls."
  }
}
```

#### Expedia (Mock)
```json
{
  "connection_id": "...",
  "platform_type": "expedia",
  "healthy": true,
  "message": "Mock: Connection is healthy",
  "details": {
    "mock_mode": true,
    "simulated": true,
    "connection_status": "active",
    "remote_account_id": "mock_expedia_partner_456789",
    "remote_listing_id": "mock_vrbo_listing_234567",
    "capabilities": ["availability_sync", "pricing_sync", "booking_retrieval"],
    "note": "This is a simulated response. Set CHANNEL_MOCK_MODE=false for real API calls."
  }
}
```

#### FeWo-direkt (Mock)
```json
{
  "connection_id": "...",
  "platform_type": "fewo_direkt",
  "healthy": true,
  "message": "Mock: Connection is healthy",
  "details": {
    "mock_mode": true,
    "simulated": true,
    "connection_status": "active",
    "remote_account_id": "mock_fewo_owner_654321",
    "remote_listing_id": "mock_fewo_property_876543",
    "capabilities": ["availability_sync", "pricing_sync"],
    "note": "This is a simulated response. Set CHANNEL_MOCK_MODE=false for real API calls."
  }
}
```

#### Google (Mock)
```json
{
  "connection_id": "...",
  "platform_type": "google",
  "healthy": true,
  "message": "Mock: Connection is healthy",
  "details": {
    "mock_mode": true,
    "simulated": true,
    "connection_status": "active",
    "remote_account_id": "mock_google_hotel_112233",
    "remote_listing_id": "mock_google_listing_998877",
    "capabilities": ["availability_sync", "pricing_sync"],
    "note": "This is a simulated response. Set CHANNEL_MOCK_MODE=false for real API calls."
  }
}
```

### Production Readiness

To go production-ready (disable mock mode and enable real platform integrations), configure the following environment variables:

#### Required for All Platforms
```bash
# Disable mock mode
CHANNEL_MOCK_MODE=false
```

#### Platform-Specific Credentials

**Airbnb:**
```bash
AIRBNB_API_KEY=your_airbnb_api_key
AIRBNB_API_SECRET=your_airbnb_secret
```

**Booking.com:**
```bash
BOOKING_COM_API_KEY=your_booking_api_key
BOOKING_COM_SECRET=your_booking_secret
BOOKING_COM_HOTEL_ID=your_hotel_id
```

**Expedia:**
```bash
EXPEDIA_API_KEY=your_expedia_key
EXPEDIA_API_SECRET=your_expedia_secret
EXPEDIA_PARTNER_ID=your_partner_id
```

**FeWo-direkt:**
```bash
FEWO_DIREKT_API_KEY=your_fewo_key
FEWO_DIREKT_SECRET=your_fewo_secret
```

**Google Vacation Rentals:**
```bash
GOOGLE_HOTELS_API_KEY=your_google_key
GOOGLE_HOTELS_PARTNER_ID=your_partner_id
```

**After Adding Credentials:**
1. Restart backend: `docker restart pms-backend`
2. Test connection via Admin UI or API: `POST /api/v1/channel-connections/{id}/test`
3. Verify `healthy=true` and `mock_mode=false` in response
4. If `healthy=false`, check error_code and message for next steps

### Admin UI Indicator

The Admin UI (Connections page) automatically detects and displays Mock Mode status when testing connections.

**Visual Indicators:**

**Mock Mode Enabled:**
- Blue "Mock Mode (Simulated)" badge displayed above test result
- Explanatory text: "This response is simulated. For production set CHANNEL_MOCK_MODE=false."
- Link to this runbook section for configuration details

**Credentials Missing (Production Mode):**
- Yellow "Not Configured" badge displayed
- Lists required environment variables for the platform
- Link to Production Readiness section above

**How It Works:**
- UI checks `details.mock_mode` or `details.simulated` flags in test response
- UI checks `error_code` field for CREDENTIALS_MISSING status
- No manual configuration needed - indicators appear automatically based on backend response

**Example:**
1. Navigate to Admin UI → Connections
2. Click "Open" on any connection
3. Click "Run Test"
4. If mock mode is enabled, you'll see the blue badge immediately
5. If credentials are missing, you'll see the yellow badge with required env vars

### Limitations

**Current Implementation (Phase C1):**
- Mock mode ONLY affects `/test` endpoint
- Sync operations (`/api/availability/sync`) are NOT yet mocked
- CRUD endpoints (`POST`, `GET`, `PUT`, `DELETE` connections) operate normally regardless of mock mode

**Planned Future Enhancements:**
- Mock sync operations (availability/pricing updates)
- Configurable mock data (success/failure scenarios)
- Per-platform mock behavior customization

---

## Channel Manager - channel_connections Schema Drift

**Purpose:** Diagnose and fix missing table/columns that cause 500/503 errors when calling Channel Manager endpoints.

### Symptoms

**HTTP 500 Internal Server Error:**
```json
{
  "detail": "Failed to simulate connection test: column \"platform_type\" does not exist"
}
```

**HTTP 503 Service Unavailable (after hardening):**
```json
{
  "detail": "Database schema not installed/out of date. Missing column in channel_connections: column \"status\" does not exist. Run Supabase migrations: supabase/migrations/20260101030000_channel_connections_schema_upgrade.sql"
}
```

**HTTP 404 Not Found:**
```
Connection not found
```
This occurs when schema exists but no test row seeded (expected in fresh deployments).

**HTTP 405 Method Not Allowed:**
```
Method Not Allowed
```
The `/test` endpoint is **POST**, not GET. Use `curl -X POST`.

### Root Cause

The `channel_connections` table was created in migration `20250101000002_channels_and_financials.sql` but is missing columns expected by backend code:

**Missing columns:**
- `platform_type` (backend queries this instead of `channel`)
- `status` (used for health check simulation in mock mode)
- `platform_metadata` (JSONB for connection details)
- `deleted_at` (soft delete filtering with `WHERE deleted_at IS NULL`)

**Original schema** only had: `id`, `agency_id`, `channel`, `is_active`, etc.

### Verification

**Check if table exists:**

WHERE: Supabase SQL Editor or HOST-SERVER-TERMINAL (psql)
```sql
SELECT to_regclass('public.channel_connections');
-- Expected: 'channel_connections' (if exists) or NULL (if missing)
```

**Check for missing columns:**

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'channel_connections'
ORDER BY ordinal_position;

-- Expected columns:
-- id, agency_id, channel, platform_type, status, platform_metadata, deleted_at
```

**Check if columns are missing (quick):**
```sql
SELECT
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='channel_connections' AND column_name='platform_type') AS has_platform_type,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='channel_connections' AND column_name='status') AS has_status,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='channel_connections' AND column_name='platform_metadata') AS has_platform_metadata,
  EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='channel_connections' AND column_name='deleted_at') AS has_deleted_at;

-- Expected: all true (t, t, t, t)
-- If any false, schema drift detected
```

### Fix: Apply Migration

**Migration File:**
```
supabase/migrations/20260101030000_channel_connections_schema_upgrade.sql
```

**What it does:**
- Adds `platform_type`, `status`, `platform_metadata`, `deleted_at` columns (idempotent)
- Backfills `platform_type` from existing `channel` column
- Backfills `status` from existing `is_active` (true → 'active', false → 'inactive')
- Adds check constraints for valid enum values
- Adds indexes for performance

**Apply via Supabase CLI:**

WHERE: Local development machine (with Supabase CLI installed)
```bash
cd /path/to/PMS-Webapp
supabase db push

# Or apply single migration:
supabase migration up --file supabase/migrations/20260101030000_channel_connections_schema_upgrade.sql
```

**Apply via Supabase Dashboard:**

1. Navigate to: Supabase Dashboard → SQL Editor
2. Copy contents of `20260101030000_channel_connections_schema_upgrade.sql`
3. Paste and execute (safe: idempotent, will skip if columns exist)

**Apply via psql (HOST-SERVER-TERMINAL):**

```bash
# SSH to host server
cd /app/supabase/migrations
psql "$DATABASE_URL" < 20260101030000_channel_connections_schema_upgrade.sql
```

### Seed Test Row (Optional)

**For testing /test endpoint, seed a row:**

WHERE: Supabase SQL Editor or psql
```sql
INSERT INTO channel_connections (
  agency_id,
  channel,
  platform_type,
  status,
  platform_metadata
) VALUES (
  (SELECT id FROM agencies LIMIT 1),  -- Use existing agency
  'airbnb',
  'airbnb',
  'active',
  '{"listing_id": "12345678", "host_id": "host_abc"}'::jsonb
)
ON CONFLICT (agency_id, channel) DO NOTHING;

-- Get the connection ID for testing:
SELECT id, agency_id, platform_type, status
FROM channel_connections
WHERE deleted_at IS NULL;
```

**Verify seed:**
```bash
# In backend logs or via API
curl -X POST "$API/api/v1/channel-connections/$CID/test" \
  -H "Authorization: Bearer $TOKEN"

# Expected (mock mode): {"healthy": true, "details": {"mock_mode": true, ...}}
```

### Mock Mode Behavior

**When `CHANNEL_MOCK_MODE=true`:**

**Schema exists + row exists:**
- Returns simulated health check based on `status` column
- `healthy=true` if `status='active'`, `healthy=false` otherwise
- Response includes `"mock_mode": true` flag

**Schema missing (before hardening):**
- HTTP 500 with cryptic error message
- No actionable guidance

**Schema missing (after hardening - Phase C1):**
- HTTP 503 with clear migration guidance
- Error message points to specific migration file
- Prevents confusing 500 errors

**Row missing (404):**
- Expected in fresh deployments (no seed data)
- Fix: Insert a test row (see seed snippet above)
- OR: Create connection via POST `/api/v1/channel-connections/` endpoint

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 500 "column platform_type does not exist" | Schema drift (old migration) | Apply 20260101030000 migration |
| 503 "Missing column in channel_connections" | Schema drift (after hardening) | Apply 20260101030000 migration |
| 404 "Connection not found" | No rows in table | Seed test row or create via API |
| 405 "Method Not Allowed" | Using GET instead of POST | Use `curl -X POST` |
| 401 "Unauthorized" | Missing/invalid JWT token | Fetch token via auth endpoint |

### Expected Response (Mock Mode)

**Success (200):**
```json
{
  "connection_id": "abc-123-456-...",
  "platform_type": "airbnb",
  "healthy": true,
  "message": "Mock: Connection is healthy",
  "details": {
    "mock_mode": true,
    "simulated": true,
    "connection_status": "active",
    "note": "This is a simulated response. Set CHANNEL_MOCK_MODE=false for real API calls."
  }
}
```

**Note:** `/test` endpoint is **POST**, not GET. Using GET returns HTTP 405.

### Related Sections

- [Mock Mode for Channel Providers](#mock-mode-for-channel-providers) - Mock mode configuration
- [Channel Manager API Endpoints](#channel-manager-api-endpoints) - Complete API reference
- [Seeding Test Connections](#seeding-test-connections) - Automated seeding via script

---

## Seeding Test Connections

**Purpose:** Quickly seed or reset channel connections for testing without manual SQL Editor operations.

**Script:** `backend/scripts/pms_channel_seed_connection.sh`

**Key Feature: NO psql required on host** - uses `docker exec` in Supabase DB container automatically.

**Why Use This Script:**
- **No psql required:** Runs via `docker exec` in supabase-db-* container (auto-detects)
- **Idempotent:** Safe to run multiple times (uses `ON CONFLICT DO UPDATE`)
- **Auto-pick agency:** No manual UUID lookup required
- **Validation:** UUID and JSON validation before INSERT
- **Clean state:** Optional purge of sync logs with confirmation
- **Automation-ready:** `--print-cid` flag for scripting/CI/CD
- **No secrets in output:** Passwords redacted in logs

**Requirements:**
- `docker` command on host (for docker exec into DB container)
- `python3` (for JSON validation)
- **NO psql required** on host (runs inside container)

### Quick Start

**Basic usage (auto-pick agency, default airbnb):**

WHERE: HOST-SERVER-TERMINAL
```bash
# NO DATABASE_URL needed - script auto-detects DB container and reads credentials

# Seed connection (auto-detects supabase-db-* container)
bash backend/scripts/pms_channel_seed_connection.sh

# Expected output:
# ℹ️  Auto-detecting Supabase DB container...
# ℹ️  ✓ Auto-detected DB container: supabase-db-bccg4gs4o4kgsowocw08wkw4
# ℹ️  Reading DB credentials from container...
# ℹ️  ✓ DB credentials loaded (user: postgres, db: postgres)
# ℹ️  No --agency-id provided, auto-picking first agency from database...
# ℹ️  ✓ Auto-picked agency: abc-123-def-456...
# ✅ CHANNEL CONNECTION SEEDED
# Connection ID:   xyz-789-ghi-012...
# Agency ID:       abc-123-def-456...
# Channel:         airbnb
# Platform Type:   airbnb
# Status:          active
```

**Scripting mode (automation):**
```bash
# Export connection ID for use in other scripts (no output except CID)
export CID=$(bash backend/scripts/pms_channel_seed_connection.sh --print-cid)

# Use with sync poll script
bash backend/scripts/pms_channel_sync_poll.sh --cid $CID --sync-type availability
```

**Explicit DB container (if multiple containers exist):**
```bash
# Via flag
bash backend/scripts/pms_channel_seed_connection.sh --db-container supabase-db-xyz123

# Via ENV
export SUPABASE_DB_CONTAINER=supabase-db-xyz123
bash backend/scripts/pms_channel_seed_connection.sh
```

### Common Use Cases

**1. Seed booking.com connection:**
```bash
bash backend/scripts/pms_channel_seed_connection.sh \
  --channel booking_com \
  --platform-type booking_com \
  --platform-listing-id booking_12345678
```

**2. Seed with explicit agency and property:**
```bash
# Option A: Let script auto-pick agency (recommended)
bash backend/scripts/pms_channel_seed_connection.sh \
  --channel airbnb \
  --platform-type airbnb

# Option B: Get agency ID manually first (if you need a specific agency)
# Note: Script uses docker exec internally, no local psql needed
export AGENCY_ID=$(bash backend/scripts/pms_channel_seed_connection.sh --print-cid --channel temp 2>&1 | grep "Auto-picked agency" | awk '{print $NF}')

# Then seed with explicit IDs
bash backend/scripts/pms_channel_seed_connection.sh \
  --agency-id $AGENCY_ID \
  --property-id <your-property-uuid> \
  --channel airbnb \
  --platform-type airbnb
```

**3. Reset connection and clear sync logs:**
```bash
# Reset (clear logs) with confirmation prompt
bash backend/scripts/pms_channel_seed_connection.sh --reset

# Reset without confirmation (automation)
bash backend/scripts/pms_channel_seed_connection.sh --reset --yes

# Legacy: --purge-logs still works (alias for --reset)
bash backend/scripts/pms_channel_seed_connection.sh --purge-logs --yes
```

**What does --reset do?**
- Deletes all `channel_sync_logs` entries for the seeded connection
- Useful for testing full sync operations in UI without old log clutter
- Connection itself remains (only logs are cleared)
- Requires confirmation unless `--yes` flag is used

**4. Seed inactive/error connection for testing:**
```bash
bash backend/scripts/pms_channel_seed_connection.sh \
  --status error \
  --metadata '{"listing_id": "test_123", "error_reason": "auth_failed"}'
```

### Script Options

| Option | Description | Default |
|--------|-------------|---------|
| `--agency-id <uuid>` | Agency ID (auto-picks first if not provided) | Auto-pick |
| `--channel <string>` | Channel name | `airbnb` |
| `--platform-type <string>` | Platform type | `airbnb` |
| `--status <status>` | Status: active/inactive/paused/disabled/error | `active` |
| `--tenant-id <uuid>` | Tenant ID (optional, if column exists) | - |
| `--property-id <uuid>` | Property ID (optional, if column exists) | - |
| `--platform-listing-id <str>` | Platform listing ID | `airbnb_listing_789` |
| `--metadata <json>` | Platform metadata JSON | `{}` |
| `--db-container <name>` | **NEW:** Explicit DB container name (overrides auto-detect) | Auto-detect |
| `--print-cid` | Print seeded connection ID only (for scripting) | - |
| `--reset` | Clear channel_sync_logs for this connection (alias: `--purge-logs`) | - |
| `--seed` | No-op flag (script always seeds, for CLI consistency) | - |
| `--yes` | Skip confirmation prompts (use with `--reset`) | - |

### Idempotent Behavior

**Conflict Key:** `(agency_id, channel)` — One connection per agency per channel

**First Run (INSERT):**
```sql
-- Creates new connection
INSERT INTO channel_connections (...) VALUES (...);
```

**Subsequent Runs (UPDATE):**
```sql
-- Updates existing connection
ON CONFLICT (agency_id, channel)
DO UPDATE SET
  platform_type = EXCLUDED.platform_type,
  status = EXCLUDED.status,
  platform_metadata = EXCLUDED.platform_metadata,
  deleted_at = NULL,  -- Revives soft-deleted connections
  updated_at = NOW();
```

**Safe to run repeatedly:**
- No duplicate connections created
- Existing connections updated to match new parameters
- Soft-deleted connections (`deleted_at IS NOT NULL`) are revived

### Environment Variables

**Required:**
- `DATABASE_URL` or `SUPABASE_DB_URL` — PostgreSQL connection string

**Optional:**
- `ENV_FILE` — Path to environment file (default: `/root/pms_env.sh`)

**Example env file (`/root/pms_env.sh`):**
```bash
export DATABASE_URL="postgresql://postgres:your-password@supabase-db:5432/postgres"
export SUPABASE_DB_URL="$DATABASE_URL"  # Alias
```

### Validation

The script validates inputs before execution:

**UUID validation:**
```bash
# Regex pattern: [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}
# Validates: --agency-id, --tenant-id, --property-id
```

**JSON validation:**
```bash
# Uses python3 to validate --metadata JSON
# Example valid: '{"listing_id":"123","host_id":"abc"}'
# Example invalid: '{listing_id:123}'  # Missing quotes
```

**Status validation:**
```bash
# Allowed values: active, inactive, paused, disabled, error
# Example valid: --status active
# Example invalid: --status ACTIVE  # Case-sensitive
```

### Log Purge Safety

**Preview before deletion:**
```bash
# Script shows count of logs before confirmation
⚠️  Found 42 sync logs for connection abc-123-456...
⚠️  Delete all sync logs for this connection? [y/N]
```

**Auto-confirm for automation:**
```bash
# Use --yes flag to skip confirmation
bash backend/scripts/pms_channel_seed_connection.sh --reset --yes
# ✓ Purged 42 sync logs (--yes flag)
```

**Scope:** Only purges logs for the seeded connection (not global)

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Required command not found: psql` | Old version of script (pre docker exec) | Update script to latest version |
| `docker command not found` | Docker not installed on host | Install docker: `apt-get install docker.io` |
| `No supabase-db-* container found` | Supabase DB not running | Start Supabase: `docker ps \| grep supabase` |
| `Multiple supabase-db-* containers found` | Multiple DB containers running | Use `--db-container <name>` or `export SUPABASE_DB_CONTAINER=<name>` |
| `Container 'xyz' not found or not running` | Wrong container name | Check: `docker ps \| grep supabase-db` |
| `Failed to read POSTGRES_* env vars` | Container missing DB env vars | Verify container has POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD |
| `Incomplete DB credentials from container` | Partial env vars in container | Check: `docker exec <container> env \| grep POSTGRES` |
| `Invalid UUID format` | Malformed UUID | Check UUID format (lowercase, hyphens) |
| `Invalid JSON for --metadata` | Malformed JSON | Use double quotes: `'{"key":"value"}'` |
| `Invalid status` | Wrong status value | Use: active/inactive/paused/disabled/error |
| `No agencies found` | Empty agencies table | Create agency first or use explicit `--agency-id` |
| `Failed to seed connection` | SQL error | Check database logs, verify schema exists |

### Integration with Other Scripts

**Use with sync poll script:**
```bash
# 1. Seed connection and capture ID
export CID=$(bash backend/scripts/pms_channel_seed_connection.sh --print-cid)

# 2. Trigger availability sync and poll for completion
bash backend/scripts/pms_channel_sync_poll.sh --cid $CID --sync-type availability

# Expected flow:
# ✅ CHANNEL CONNECTION SEEDED (Connection ID: abc-123...)
# ℹ️  Fetching JWT token...
# ✅ SYNC COMPLETED SUCCESSFULLY (Status: success)
```

**CI/CD pipeline example:**
```bash
#!/bin/bash
set -euo pipefail

# Setup
export DATABASE_URL="postgresql://..."
export SB_URL="https://..."
export ANON_KEY="..."
export EMAIL="test@example.com"
export PASSWORD="..."

# Seed test connection
CID=$(bash backend/scripts/pms_channel_seed_connection.sh \
  --channel airbnb \
  --status active \
  --print-cid \
  --yes)

echo "Seeded connection: $CID"

# Run smoke test
bash backend/scripts/pms_channel_sync_poll.sh \
  --cid $CID \
  --sync-type availability \
  --poll-limit 30

# Cleanup (optional)
bash backend/scripts/pms_channel_seed_connection.sh \
  --channel airbnb \
  --status inactive \
  --reset \
  --yes
```

### Next Steps After Seeding

**Test connection health:**
```bash
# Via UI
https://admin.fewo.kolibri-visions.de/connections

# Via API
curl -X POST "$API/api/v1/channel-connections/$CID/test" \
  -H "Authorization: Bearer $TOKEN"
```

**Trigger sync:**
```bash
# Via script (recommended)
bash backend/scripts/pms_channel_sync_poll.sh --cid $CID --sync-type availability

# Via API
curl -X POST "$API/api/v1/channel-connections/$CID/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type":"availability"}'
```

**Monitor logs:**
```bash
# Via script
bash backend/scripts/pms_channel_sync_poll.sh --cid $CID

# Via API
curl "$API/api/v1/channel-connections/$CID/sync-logs?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

### When to Use

✅ **Use this script when:**
- Setting up test connections for development
- Resetting connection state after schema changes
- Automating connection setup in CI/CD pipelines
- Testing Channel Manager sync operations
- Creating connections without UI access

❌ **Don't use this script when:**
- Setting up production connections (use Admin UI instead)
- Updating OAuth credentials (use Admin UI or encrypted SQL)
- Bulk operations (use migration scripts instead)
- Managing multiple connections at once (use batch SQL instead)

### Related Sections

- [Channel Manager - Schema Drift](#channel-manager---channel_connections-schema-drift) - Fix missing columns
- [pms_channel_sync_poll.sh](../scripts/README.md#pms_channel_sync_pollsh) - Trigger and poll syncs
- [Channel Connections Management](../scripts/README.md#channel-connections-management-curl-examples) - curl API examples
- [Admin UI – Channel Manager Operations](#admin-ui--channel-manager-operations) - Web UI guide

---

## Admin UI – Channel Manager Operations

**Purpose:** Guide for using the admin web UI to manage channel connections, test health, trigger syncs, and monitor logs.

**Access:** Admin-only (requires admin role). Navigate to: `https://admin.fewo.kolibri-visions.de/connections`

### UI Notifications

**Important:** The Admin UI uses in-app notifications exclusively. No browser alerts (alert/confirm/prompt) are used.

**Notification System:**
- All feedback is shown via non-blocking in-app banners/toasts
- Success messages: Green banner with auto-dismiss (5 seconds)
- Error messages: Red banner with auto-dismiss (5 seconds)
- Manual dismiss: Click X button to close immediately
- Notifications appear at top of page (Connections page) or below page header (System Status page)

**Examples:**
- "Connection test passed: Mock: Connection is healthy (Mock Mode - see runbook for production setup)"
- "Connection status updated to paused"
- "Diagnostics copied to clipboard"
- "Failed to update status: Network error"

**Affected Pages:**
- `/connections` - Connection management and testing
- `/ops/status` - System health diagnostics

**Test Connection Feedback:**
When clicking "Test" button (inline in connections table):
1. Button shows "Testing..." while API call is in progress
2. On success/failure, notification banner appears at top of connections page
3. Banner auto-dismisses after 10 seconds or click X to close manually
4. Success example: "Connection test passed: Mock: Connection is healthy (Mock Mode - see runbook for production setup)"
5. Failure example: "Test failed: Connection timeout" or "Connection test failed: Invalid credentials"
6. If `error_code` is present (e.g., CREDENTIALS_MISSING), it's shown in the detailed test result modal, not the inline toast

**Where to Look for Feedback:**
- **Inline test (table row "Test" button):** Notification banner appears at top of main page above search box
- **Modal test ("Run Test" button in connection details):** Test result displays below button in modal with full details including badges
- Both locations use same notification system (green for success, red for error)

**Common Error Messages:**

The Admin UI displays user-friendly error messages instead of technical errors. Here's what they mean and how to resolve them:

**Network Errors:**
- **"Network error (API not reachable). Check your connection, VPN, or firewall."**
  - **Meaning:** Browser cannot reach the API endpoint (typically "Failed to fetch" from browser)
  - **Common Causes:**
    - Internet connection lost
    - VPN blocking API domain
    - Corporate firewall/proxy blocking requests
    - CORS policy blocking cross-origin requests
    - Ad blocker or browser extension interfering
    - API server is down (check `/ops/status` page)
  - **Action:**
    - Check internet connection
    - Disable VPN temporarily and retry
    - Try different network (e.g., mobile hotspot)
    - Check browser console for CORS/network errors
    - Verify API is reachable: `curl https://api.fewo.kolibri-visions.de/health`
    - Contact IT if corporate firewall is blocking

- **"You appear to be offline. Check your internet connection."**
  - **Meaning:** Browser detects no network connectivity (navigator.onLine = false)
  - **Action:** Reconnect to Wi-Fi/Ethernet and retry

**Authentication & Authorization Errors:**
- **"Session expired. Please reload and log in again."** (HTTP 401)
  - **Meaning:** JWT token expired or invalid
  - **Action:** Refresh page (F5) and log in again with valid credentials

- **"Not authorized to perform this action."** (HTTP 403)
  - **Meaning:** User lacks permission for the operation
  - **Action:** Contact admin to grant required role/permissions

**Service Availability Errors:**
- **"Service temporarily unavailable. Try again shortly."** (HTTP 503)
  - **Meaning:** Backend API is temporarily down (database error, maintenance, etc.)
  - **Action:**
    - Wait 30-60 seconds and retry
    - Check `/ops/status` page for component health
    - Check Coolify logs if persistent: `docker logs pms-backend`
    - See [Quick Smoke Test](#quick-smoke-5-minutes) for diagnostics

**Other Errors:**
- **"Unexpected error occurred"**
  - **Meaning:** Unknown error type (not network, not HTTP)
  - **Action:** Check browser console for details, report to developers

**Why No Browser Alerts:**
Browser popups (window.alert/confirm/prompt) are blocking and interrupt workflow. In-app notifications provide better UX:
- Non-blocking: User can continue working
- Consistent styling: Matches app design
- Context-aware: Stays within the application UI
- Auto-dismiss: Reduces manual clicks (10 seconds)

**Regression Guard:**

To prevent accidental reintroduction of browser popups, the codebase includes automated checks:

**ESLint Rule:**
The frontend has ESLint configured with `"no-alert": "error"` (`.eslintrc.json`). This prevents:
- `alert()` / `window.alert()`
- `confirm()` / `window.confirm()`
- `prompt()` / `window.prompt()`

If ESLint detects a browser popup during development:
1. Remove the popup call
2. Replace with in-app notification banner (see examples above)
3. Use the existing notification system (`setNotification()` pattern)

**Manual Check Script:**
Run the regression guard script to verify no browser popups exist:

```bash
bash frontend/scripts/check_no_browser_popups.sh
```

**Expected Output (Clean):**
```
Checking frontend/ for browser popups (alert/confirm/prompt)...
Repo root: /Users/.../PMS-Webapp

✅ OK: No browser popups (alert/confirm/prompt) found in frontend/
```

**If Popups Found:**
```
❌ FAILED: Browser popups detected!

frontend/app/connections/page.tsx:142:        alert("Test failed!");

Action required:
  - Replace alert() with in-app notification banners/toasts
  - Replace confirm() with in-app confirmation dialogs
  - Replace prompt() with in-app input forms
  - See backend/docs/ops/runbook.md for guidance
```

**Monthly Maintenance:**
Run `check_no_browser_popups.sh` as part of monthly code quality checks (see [Daily Ops Checklist](#daily-ops-checklist) for automation).

### Overview

The Connections page provides a centralized interface for Channel Manager operations:
- **List Connections:** View all channel connections with search/filter
- **Test Health:** Quick inline tests or detailed test results
- **Connection Details:** Modal view with full management capabilities
- **Trigger Syncs:** Manual sync operations (full/availability/pricing/bookings)
- **Monitor Logs:** Real-time sync log tracking with auto-refresh and filters

### Connections List

**Features:**
- **Search box:** Filter by connection ID, platform type, or status (client-side)
- **Table columns:** ID (copyable), Platform, Status, Last Sync, Updated
- **Inline actions:** Test (quick toast result), Open (detailed modal)

**Common Actions:**

1. **Create new connection:**
   - Click "New Connection" button (indigo, next to Refresh)
   - Opens modal form with fields:
     - **Property:** Select from dropdown (loads via API)
     - **Platform:** airbnb, booking_com, expedia, fewo_direkt, google
     - **Platform Listing ID:** Text input (default: `mock_<platform>_<timestamp>`)
     - **Access Token:** Text input (default: `mock_access_token`)
     - **Refresh Token:** Optional (default: `mock_refresh_token`)
     - **Platform Metadata:** JSON textarea (default: `{"mock_mode": true}`)
   - **Mock Mode Support:** In mock mode, mock tokens are accepted (no real OAuth required)
   - Click "Create Connection" to submit POST `/api/v1/channel-connections/`
   - On success: modal closes, success toast appears, list refreshes
   - On error: shows friendly error message (e.g., "Not allowed: need admin or manager role")
   - **Requirements:** Admin or Manager role

2. **Search connections:**
   - Type in search box to filter by ID/platform/status
   - Results update instantly (client-side filter)

3. **Copy connection ID:**
   - Click on truncated ID (e.g., "abc123...") to copy full UUID
   - Useful for API calls or debugging

4. **Quick test:**
   - Click "Test" button for inline health check
   - Shows in-app notification: "Connection test passed: Mock: Connection is healthy (Mock Mode - see runbook for production setup)"
   - Non-blocking, auto-dismisses after 10 seconds

5. **Open details:**
   - Click "Open" to view full connection details modal
   - See sync operations, logs, and advanced controls

### Connection Details Modal

**Sections:**

#### 1. Summary
Shows key connection fields:
- Platform type (airbnb, booking_com, etc.)
- Status (active, paused, inactive, error)
- Last sync timestamp
- Last updated timestamp

#### 2. Test Connection
- **Button:** "Run Test" - performs POST `/api/v1/channel-connections/{id}/test`
- **Result display:**
  - Green banner: Connection healthy (status=active in mock mode)
  - Red banner: Connection unhealthy (status!=active or test failed)
  - Details section: Shows `mock_mode`, `simulated`, connection status
- **Mock mode:** If `CHANNEL_MOCK_MODE=true` (current production), response includes `mock_mode: true` flag

#### 3. Trigger Sync
- **Dropdown:** Select sync type (Full, Availability, Pricing, Bookings)
- **Button:** "Trigger Sync" - performs POST `/api/v1/channel-connections/{id}/sync` with `{"sync_type": "..."}`
- **Result:** In-app notification (non-blocking inline banner, auto-clears after 5s):
  - **Success:** Green banner showing "Sync gestartet: {sync_type}" with clickable batch_id (if Full Sync)
  - **Error:** Red banner showing "Fehler beim Starten (HTTP {status}): {detail}" (or generic error message)
  - **Dismiss:** Click X button to close notification manually
- **Auto-refresh:** Logs table refreshes 1s after sync trigger to show new log entry

#### 4. Sync Logs
- **Auto-refresh toggle:** Default ON, refreshes every 10 seconds while modal open
- **Filters:**
  - Status: All / Triggered / Running / Success / Failed
  - Sync Type: All / Full / Availability / Pricing / Bookings
- **Table columns:**
  - Time (created_at timestamp)
  - Type (operation_type or sync_type)
  - Status (color-coded badges: green=success, red=failed, blue=running, gray=triggered)
  - Error (first 50 chars, truncated)
  - Actions: "Details" button opens full log JSON modal
- **Details modal:** Shows complete log object in formatted JSON (error details, retry count, task ID, metadata)

### UX Features

#### New Connection Modal

**Platform Selection:**
- Platform dropdown starts **unselected** (shows placeholder: "Select a platform...")
- User **must explicitly choose** a platform before submitting
- Property dropdown also starts unselected (default behavior)
- Submit button is disabled until both property and platform are selected

**Validation:**
- Backend requires both `property_id` and `platform_type`
- Frontend validates before submission to prevent errors

**Design Rationale:**
- Prevents accidental default selections
- Ensures deliberate platform choice
- Reduces user errors from auto-selected platforms

#### Batch Details Navigation

**Back Arrow Behavior:**
- Batch Details modal always shows icon-only back arrow (left arrow, no text)
- **If opened from Log Details:** Back arrow returns to Log Details modal (same log entry)
- **If opened directly from Batch History table:** Back arrow closes Batch Details and returns to Connection Details
- Tooltip dynamically shows "Back to log details" or "Back to connection" based on context

**Implementation:**
- Modal stack approach: Log Details (z-index 60) and Batch Details (z-index 70) can coexist
- When navigating Log Details → Batch Details, Log Details stays open in background
- Back arrow simply closes Batch Details, revealing whatever was underneath
- Source context is tracked via `sourceLogId` state for tooltip accuracy

**User Flow:**
```
Connection Details
  → Open Log Details
    → Click "Open Batch Details →" button
      → Batch Details opens on top (Log Details still in state)
      → Click back arrow ←
        → Returns to Log Details (same log entry)
        → Click X to close Log Details
          → Returns to Connection Details
```

### API Endpoints Used

**List connections:**
```
GET /api/v1/channel-connections/
Response: JSON array of connection objects (not wrapped in {items:...})
```

**Test connection:**
```
POST /api/v1/channel-connections/{id}/test
Request: {}
Response: {healthy: bool, message: str, details: {...}}
```

**Trigger sync:**
```
POST /api/v1/channel-connections/{id}/sync
Request: {sync_type: "full"|"availability"|"pricing"|"bookings"}
Response: {
  status: "triggered",
  message: "...",
  task_ids: ["celery-task-id-1", ...],
  batch_id: "uuid" (only for full sync, groups 3 operations)
}
```

**IMPORTANT:** Response ALWAYS includes `task_ids` array (not `task_id`). Full sync also returns `batch_id` to group the 3 operations (availability_update, pricing_update, bookings_sync). Backend triggers Celery tasks and creates sync log entries.

### Sync Type → Operation Type Mapping

When you trigger a sync via UI or API, the backend creates sync log entries with specific `operation_type` values:

| sync_type (Request) | operation_type (Logs) | Direction | Description |
|---------------------|----------------------|-----------|-------------|
| `availability` | `availability_update` | outbound | Push availability to platform |
| `pricing` | `pricing_update` | outbound | Push pricing to platform |
| `bookings` | `bookings_sync` | inbound | Import bookings from platform |
| `full` | `availability_update` + `pricing_update` + `bookings_sync` | both | Triggers all three syncs (3 log entries) |

**Key Points:**
- `full` creates **3 separate log entries** (one per operation type)
- Each log entry has a unique `task_id` from Celery
- Filter by "Type" in UI to see specific operation types
- Poll script validates `operation_type` matches requested `sync_type` (prevents false positives)

**Troubleshooting:**

| Issue | Cause | Fix |
|-------|-------|-----|
| Bookings sync shows "success" but wrong operation_type | Backend not emitting bookings logs (old version) | Update to commit `d4434cf` or later |
| Full sync shows only `availability_update` | Backend not triggering all tasks | Update to commit `d4434cf` or later |
| Poll script reports "success" for wrong type | Old poll script (no type validation) | Update to latest `pms_channel_sync_poll.sh` |
| No `task_ids` in sync response | Backend error or old version | Check backend logs, verify migration applied |

**Fetch sync logs:**
```
GET /api/v1/channel-connections/{id}/sync-logs?limit=50&offset=0
Response: Array or {logs: [...]} depending on backend version
UI handles both formats defensively
```

### Common Errors

| Error | Symptom | UI Behavior | Fix |
|-------|---------|-------------|-----|
| 401 Unauthorized | Token expired | Error banner: "Unauthorized - please log in again" | Re-login via `/login` |
| 403 Forbidden | Non-admin user | Error banner: "Forbidden - admin access required" | Use admin account or check RLS policies |
| 404 Connection not found | Connection ID invalid or deleted | Test/sync fails with "Connection not found" | Verify connection exists with `deleted_at IS NULL` |
| 405 Method Not Allowed | Using GET on /test | Backend returns 405 | UI uses POST (correct), only applies to curl errors |
| 503 Service Unavailable | DB schema missing columns | Error banner: "Service unavailable - database may need migrations" | Apply migration 20260101030000 (see [Schema Drift](#channel-manager---channel_connections-schema-drift)) |
| Empty logs array | No sync operations run yet | Logs table shows "No logs found" | Trigger a sync or wait for scheduled sync |

### Troubleshooting

**Connections list empty:**
1. Check if backend returns 200: Open browser DevTools → Network tab → Refresh page
2. If 200 but empty array: No connections seeded in database (expected in fresh deployments)
3. Solution: Create connection via API (see [Channel Connections Management](../scripts/README.md#channel-connections-management-curl-examples))

**Test always shows "unhealthy":**
1. Check if mock mode enabled: Backend env `CHANNEL_MOCK_MODE=true`
2. Check connection status: Only `status='active'` returns healthy in mock mode
3. If status='paused', test returns: `healthy: false, message: "Mock: Connection status is paused"`

**Sync trigger does nothing:**
1. Check browser console for errors (F12 → Console tab)
2. Verify in-app notification appears (green success banner or red error banner below the Trigger Sync button)
3. If no notification: POST /sync may have failed silently (check Network tab for API response)
4. Check sync logs table for new entry (should appear within 1-2s)
5. If no log entry: Backend may not support /sync endpoint or Celery worker offline

**Auto-refresh not working:**
1. Verify toggle is ON (checkbox should be checked)
2. Open browser console to see if fetch errors occur every 10s
3. If errors: Backend /sync-logs endpoint may be failing (check HTTP status)

**Logs show cryptic field names:**
1. UI expects fields: `id`, `created_at`, `status`, `operation_type`/`sync_type`, `error`
2. If backend uses different field names, logs may display "N/A"
3. Click "Details" to see raw log JSON and identify actual field names

**Input text not visible (white-on-white):**
1. Symptom: Search input, dropdown selections, or modal summary text appears invisible
2. Cause: Browser cache serving old CSS or stale build
3. Fix: Hard refresh (Ctrl+F5 or Cmd+Shift+R), clear browser cache, verify latest deploy
4. Verify: Check SOURCE_COMMIT in backend logs matches latest git commit
5. Note: UI now enforces explicit text colors (text-gray-900) to prevent this issue

**Log Details JSON text invisible/too light:**
1. Symptom: Clicking "Details" in Sync Logs shows JSON modal, but text appears white/faint (only readable when highlighted)
2. Cause: Browser cache serving old CSS without explicit code block styles
3. Fix: Hard refresh (Ctrl+F5 or Cmd+Shift+R), clear browser cache, ensure latest deploy
4. Verify: JSON should appear in dark text (slate-900) on light background (slate-50) with border
5. Note: UI now enforces readable code block styles (bg-slate-50, text-slate-900, border)

**Text/JSON white-on-white across admin UI (Inputs/Modals/JSON blocks):**
1. Symptom: Multiple UI elements show invisible white text (search inputs, modal content, JSON viewers in /connections and /ops/status)
2. Root Cause: System Dark Mode preference triggers `globals.css` media query that sets body text to white (--foreground-rgb: 255,255,255)
3. Components affected: Search inputs, Connection Details modal summary, Log Details JSON, /ops/status raw JSON blocks
4. Fix: Deploy frontend with JsonViewer component (components/ui/json-viewer.tsx) for all JSON displays, then hard refresh
5. Verify: All mentioned components should display dark text clearly in both Light and Dark system modes
6. Technical Note: JsonViewer component uses explicit bg-slate-50/text-slate-900 (not inherited color) to override globals.css dark mode defaults
7. Pages using JsonViewer: /ops/status (health + ready raw JSON), /connections (Log Details modal + test result details)

---

## Full Sync Operations (Channel Manager)

**Purpose:** Understand and validate full sync behavior, which triggers ALL Channel Manager operations concurrently.

### What is Full Sync?

Full sync (`sync_type=full`) triggers **three concurrent Celery tasks**:
1. **Availability Sync** (`availability_update`) - Syncs property availability/calendar
2. **Pricing Sync** (`pricing_update`) - Syncs rates and pricing rules
3. **Bookings Sync** (`bookings_sync` or `bookings_import`) - Imports platform bookings

In **mock mode** (development/testing), all three operations return instant mock success. In **production mode**, tasks make real API calls to external platforms (Airbnb, Booking.com, etc.).

### Validation (Full Sync Success Criteria)

Full sync is **only successful** when:
- ✅ ALL three operation types are present in `channel_sync_logs`
- ✅ ALL three have `status='success'`
- ✅ All logs created AFTER trigger timestamp (no old logs)

**Partial success is treated as failure:**
- ❌ If only `availability_update` + `pricing_update` appear → **NOT complete**
- ❌ If any operation has `status='failed'` → **Entire sync failed**
- ❌ If bookings task is `triggered` but stuck → **Incomplete** (wait or timeout)

### How to Validate Full Sync

**1. Via Script (Recommended):**
```bash
# Trigger full sync and wait for all operations
bash backend/scripts/pms_channel_sync_poll.sh \
  --sync-type full \
  --poll-limit 30 \
  --poll-interval 2

# Expected output:
# ℹ️  Found operations: [availability_update, bookings_sync, pricing_update] (need: [availability_update, pricing_update, bookings_sync])
# ✅ SYNC COMPLETED SUCCESSFULLY
# Operation Summary:
#   Operation Type            Status          Task ID
#   ------------------------- --------------- ----------------------------------------
#   availability_update       success         abc-123...
#   bookings_sync             success         def-456...
#   pricing_update            success         ghi-789...
```

**2. Via UI:**
```
1. Navigate to: https://admin.fewo.kolibri-visions.de/connections
2. Click "Sync" button → Select "Full Sync"
3. Wait for sync to complete (alert shows "Sync triggered successfully")
4. Check "Sync Logs" table → Should show 3 recent entries:
   - availability_update (success)
   - pricing_update (success)
   - bookings_sync (success)
```

**3. Via Database:**
```sql
-- Check last 5 sync logs for connection
SELECT
  operation_type,
  status,
  created_at,
  task_id,
  error
FROM channel_sync_logs
WHERE connection_id = '<your-connection-uuid>'
ORDER BY created_at DESC
LIMIT 5;

-- Expected (after full sync):
-- availability_update | success | 2026-01-01 12:00:01 | abc-123 | NULL
-- pricing_update      | success | 2026-01-01 12:00:01 | def-456 | NULL
-- bookings_sync       | success | 2026-01-01 12:00:02 | ghi-789 | NULL
```

### Troubleshooting Full Sync

**Issue: Poll script exits early (no "Found operations:" output)**

**Symptoms:**
- Script prints "Poll attempt 1/20..." and "GET /sync-logs => HTTP 200, XXXX bytes"
- Then terminates immediately (exit=0) WITHOUT printing operation summary

**Root Cause (Fixed in Commit TBD):**
- Fragile string injection in Python parser caused silent failures
- Empty POLL_RESULT led to false "all_success" condition

**Fix:**
```bash
# Ensure you have the latest poll script
git pull origin main
bash backend/scripts/pms_channel_sync_poll.sh --sync-type full --poll-limit 30
```

**Verification:**
- Script should now print: `ℹ️  Found operations: [...]` on EVERY poll
- If missing: Check `/tmp/pms_poll_*.{json,txt}` for write errors

---

**Issue: Only 1 or 2 operations appear (missing bookings_sync)**

**Symptoms:**
- Script finds `availability_update` + `pricing_update` only
- Missing `bookings_sync` or `bookings_import`

**Diagnosis:**
```sql
-- Check if bookings task was created
SELECT operation_type, status, created_at, error
FROM channel_sync_logs
WHERE connection_id = '<cid>'
  AND operation_type IN ('bookings_sync', 'bookings_import')
ORDER BY created_at DESC
LIMIT 1;
```

**Possible Causes:**
1. **Backend not triggering bookings task:** Update to commit `d4434cf` or later
2. **Celery worker offline:** Check `docker ps | grep celery` and verify worker is running
3. **Bookings task failed:** Check worker logs: `docker logs <celery-container> | grep bookings`
4. **DB constraint blocks bookings_sync:** Check for error: `channel_sync_logs_operation_type_check` violation
   - Fix: Apply migration `20260101140000_fix_channel_sync_logs_operation_type_check.sql`

---

**Issue: Full sync succeeds in UI but script says "not complete"**

**Symptom:**
- UI shows all 3 logs with status=success
- Poll script continues waiting or times out

**Diagnosis:**
```bash
# Check trigger timestamp vs log timestamps
TRIGGER_TS=$(date +%s)
echo "Trigger timestamp: $TRIGGER_TS"

# In DB, check created_at (must be AFTER trigger)
SELECT operation_type,
       EXTRACT(EPOCH FROM created_at) as log_ts
FROM channel_sync_logs
WHERE connection_id = '<cid>'
ORDER BY created_at DESC
LIMIT 3;
```

**Possible Cause:**
- Script is filtering out OLD logs (created before trigger timestamp)
- Full sync might have triggered tasks, but logs existed from previous sync

**Fix:**
- Clear old logs before triggering full sync:
```bash
bash backend/scripts/pms_channel_seed_connection.sh --reset --yes
bash backend/scripts/pms_channel_sync_poll.sh --sync-type full
```

---

### See Also

- [pms_channel_sync_poll.sh Documentation](../scripts/README.md#pms_channel_sync_pollsh) - Full script reference
- [Channel Manager Sync Logs Migration](#channel-manager-sync-logs-migration) - DB schema for logs
- [Celery Worker Troubleshooting](#celery-worker-pms-worker-v2-start-verify-troubleshoot) - Worker issues

---

### Navigation Path

**From login:**
1. Log in as admin user at `/login`
2. Admin layout auto-loads with navigation tabs: Status | Runbook | Connections | Sync
3. Click "Connections" tab
4. See connections list and search box

**Direct URL:**
- `https://admin.fewo.kolibri-visions.de/connections`
- Requires admin authentication (layout enforces server-side check)
- Non-admins redirected to `/channel-sync`

### Robust Sync Trigger + Polling (HOST-SERVER-TERMINAL)

**Purpose:** Production-grade script for triggering channel syncs and waiting for completion with robust error handling.

**Script:** `backend/scripts/pms_channel_sync_poll.sh`

**Why Use This Instead of curl:**
- **Auto-recovery:** Never crashes on empty responses (SSH disconnects, network drops)
- **Invalid JSON handling:** Shows first 200 bytes for debugging, continues polling
- **Redirect support:** Follows 307/302 redirects automatically with `curl -L`
- **Exit codes:** Clean 0/1/2 exit codes for automation
- **Polling:** Waits for completion (success/failed) instead of fire-and-forget

**Common Failure Modes This Handles:**
1. **Empty response due to disconnect:**
   - Symptom: `JSONDecodeError` when parsing empty body from `curl`
   - Old behavior: Script crashes with Python traceback
   - New behavior: Prints `⚠️ Empty response (bytes=0), retrying...` and continues

2. **JSONDecodeError when parsing empty body:**
   - Symptom: `jq` or `python -m json.tool` fails on partial/corrupt JSON
   - Old behavior: Script exits with error
   - New behavior: Shows first 200 bytes preview, continues polling

3. **Redirect chain without -L:**
   - Symptom: `/api/v1/channel-connections/` returns HTTP 307, no data
   - Old behavior: Script tries to parse redirect HTML as JSON
   - New behavior: Uses `curl -L` to follow redirects automatically

4. **Transient 502 during deploy/proxy restart:**
   - Symptom: Auto-pick list call returns HTTP 502 (11 bytes) during deploy or proxy hiccup
   - Old behavior: Script exits immediately with "Failed to list connections (HTTP 502)"
   - New behavior: Retries up to 5 times with exponential backoff (1s, 2s, 3s, 5s, 8s), prints `⚠️ Transient 502 error (deploy/proxy hiccup), retrying...`
   - Alternative: Pass `--cid` explicitly to bypass auto-pick entirely

**Quick Start:**
```bash
# On HOST-SERVER-TERMINAL
source /root/pms_env.sh
bash /app/scripts/pms_channel_sync_poll.sh
```

**Example Usage:**
```bash
# Auto-pick first connection, trigger availability sync
bash scripts/pms_channel_sync_poll.sh

# Explicit connection ID, pricing sync
bash scripts/pms_channel_sync_poll.sh --cid abc-123-456 --sync-type pricing

# Longer polling for slow syncs (30 attempts, 3s interval)
bash scripts/pms_channel_sync_poll.sh --poll-limit 30 --poll-interval 3
```

**Exit Codes:**
- `0` - Sync completed successfully
- `1` - Sync failed (check error message in output)
- `2` - Sync task not found after polling limit (worker offline or queue stuck)

**Troubleshooting:**

**Exit code 2 (task not found):**
1. Check Celery worker is running: `docker ps | grep pms-worker`
2. Check Redis is accessible: `docker logs pms-worker | grep -i redis`
3. Increase `--poll-limit` if sync takes longer than 40s (20 attempts × 2s default)

**See Also:**
- [Script Documentation](../scripts/README.md#pms_channel_sync_pollsh) - Full script reference with all options
- [Channel Manager Sync (curl examples)](../scripts/README.md#channel-manager-sync-curl-examples) - Manual curl commands for debugging

### Related Sections

- [Channel Manager - Schema Drift](#channel-manager---channel_connections-schema-drift) - Fix 503 schema errors
- [Mock Mode for Channel Providers](#mock-mode-for-channel-providers) - Mock mode configuration
- [Channel Manager API Endpoints](#channel-manager-api-endpoints) - Complete API reference
- [Channel Connections Management (curl examples)](../scripts/README.md#channel-connections-management-curl-examples) - Server-side testing

---

## Channel Manager API Endpoints

**Purpose:** Complete reference for Channel Manager API endpoints with request/response examples.

### Authentication

**All endpoints require Bearer JWT authentication:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" ...
```

**Without token → 401 Unauthorized**

---

### POST /api/availability/sync

**Purpose:** Trigger availability or pricing sync to external booking platform

**RBAC:** admin, manager only (NOT owner, staff, accountant)

**Request Body:**
```json
{
  "sync_type": "availability",           // Required: "availability" or "pricing"
  "platform": "airbnb",                   // Required: "airbnb", "booking_com", "expedia", "fewo_direkt", "google"
  "property_id": "uuid-here",             // Required: Property UUID
  "connection_id": "uuid-optional",       // Optional: Specific connection UUID
  "manual_trigger": true,                 // Optional: Default true
  "start_date": "2025-12-28",            // Optional: Default today
  "end_date": "2026-03-28"               // Optional: Default today + 90 days
}
```

**Success Response (200):**
```json
{
  "status": "triggered",
  "message": "Availability sync task triggered successfully",
  "task_id": "abc123-def456-ghi789",
  "sync_log_id": "xyz789-uvw012-rst345",
  "platform": "airbnb",
  "retry_count": 0
}
```

**Error Responses:**

**400 Bad Request** (Invalid sync_type):
```json
{
  "detail": "Invalid sync_type. Must be one of: ['availability', 'pricing']"
}
```

**400 Bad Request** (Invalid platform):
```json
{
  "detail": "Invalid platform. Must be one of: ['airbnb', 'booking_com', 'expedia', 'fewo_direkt', 'google']"
}
```

**404 Not Found** (Property not found):
```json
{
  "detail": "Property not found or does not belong to your agency"
}
```

**503 Service Unavailable** (Database down after retries):
```json
{
  "error": "service_unavailable",
  "message": "Database is temporarily unavailable.",
  "retry_count": 3
}
```

**500 Internal Server Error** (Other failures):
```json
{
  "detail": "Failed to trigger availability sync: [error details]"
}
```

**Example Usage:**
```bash
# Trigger availability sync to Airbnb
curl -X POST https://api.your-domain.com/api/availability/sync \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "sync_type": "availability",
    "platform": "airbnb",
    "property_id": "550e8400-e29b-41d4-a716-446655440000",
    "manual_trigger": true,
    "start_date": "2025-12-28",
    "end_date": "2026-03-28"
  }'
```

---

### POST /api/v1/channel-connections/{id}/sync

**Purpose:** Trigger manual sync for a channel connection

**RBAC:** Requires valid JWT (all authenticated users)

**Request Body:**
```json
{
  "sync_type": "full"  // Required: "full", "availability", "pricing", "bookings"
}
```

**Success Response (200):**
```json
{
  "status": "triggered",
  "message": "Manual full sync triggered successfully",
  "task_ids": ["task-uuid-1", "task-uuid-2"]
}
```

**Error Responses:**

**400 Bad Request** (Invalid sync_type):
```json
{
  "detail": "Invalid sync_type. Must be one of: ['full', 'availability', 'pricing', 'bookings']"
}
```

**404 Not Found** (Connection not found):
```json
{
  "status": "error",
  "message": "Connection not found",
  "task_ids": []
}
```

---

### GET /api/v1/channel-connections/{id}/sync-logs

**Purpose:** Retrieve sync operation logs for a connection

**RBAC:** Requires valid JWT

**Query Parameters:**
- `limit` (optional): Number of logs to return (max 100, default 50)
- `offset` (optional): Pagination offset (default 0)

**Success Response (200):**
```json
{
  "connection_id": "connection-uuid",
  "logs": [
    {
      "id": "log-uuid",
      "connection_id": "connection-uuid",
      "operation_type": "availability_update",
      "direction": "outbound",
      "status": "success",
      "details": {
        "platform": "airbnb",
        "property_id": "property-uuid",
        "manual_trigger": true,
        "start_date": "2025-12-28",
        "end_date": "2026-03-28",
        "check_in": "2025-12-28",
        "check_out": "2025-12-30",
        "available": true
      },
      "error": null,
      "task_id": "celery-task-uuid",
      "created_at": "2025-12-28T10:00:00Z",
      "updated_at": "2025-12-28T10:00:05Z"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

**Error Response (503):**
```json
{
  "error": "service_unavailable",
  "message": "Channel sync logs schema not installed (missing table: channel_sync_logs). Run DB migration: supabase/migrations/20251227000000_create_channel_sync_logs.sql"
}
```

---

### GET /api/v1/channel-connections

**Purpose:** List all channel connections for current agency

**RBAC:** Requires valid JWT

**Success Response (200):**
```json
[
  {
    "id": "connection-uuid",
    "tenant_id": "agency-uuid",
    "property_id": "property-uuid",
    "platform_type": "airbnb",
    "platform_listing_id": "airbnb-listing-123",
    "status": "active",
    "platform_metadata": {"listing_id": "123"},
    "last_sync_at": "2025-12-28T10:00:00Z",
    "created_at": "2025-12-01T00:00:00Z",
    "updated_at": "2025-12-28T10:00:00Z"
  }
]
```

---

### POST /api/v1/channel-connections

**Purpose:** Create new channel connection (OAuth integration)

**RBAC:** admin, manager only

**Request Body:**
```json
{
  "property_id": "property-uuid",
  "platform_type": "airbnb",
  "platform_listing_id": "airbnb-listing-123",
  "access_token": "oauth-access-token",
  "refresh_token": "oauth-refresh-token",
  "platform_metadata": {
    "listing_id": "123",
    "host_id": "456"
  }
}
```

**Success Response (201):**
```json
{
  "id": "new-connection-uuid",
  "tenant_id": "agency-uuid",
  "property_id": "property-uuid",
  "platform_type": "airbnb",
  "platform_listing_id": "airbnb-listing-123",
  "status": "active",
  "platform_metadata": {"listing_id": "123", "host_id": "456"},
  "last_sync_at": null,
  "created_at": "2025-12-28T10:00:00Z",
  "updated_at": "2025-12-28T10:00:00Z"
}
```

**Query Parameters:**

- `skip_connection_test` (boolean, default: `false`) - Skip external platform connection test (dev/mock mode only)

**Mock Mode / Development:**

When `skip_connection_test=true`:
- ✅ Skips OAuth validation and platform API health checks
- ✅ Allows creating connections for unsupported platforms (e.g., `booking_com`)
- ✅ Skips initial sync trigger
- ⚠️ Platform tokens are still encrypted and stored (but not validated)
- ⚠️ Backend logs warning: "Creating connection in MOCK MODE"

**Example - Create Connection in Mock Mode:**
```bash
curl -X POST "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/?skip_connection_test=true" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "property-uuid",
    "platform_type": "booking_com",
    "platform_listing_id": "mock_booking_123",
    "access_token": "mock_access_token",
    "refresh_token": "mock_refresh_token",
    "platform_metadata": {"mock_mode": true}
  }'
```

**Example - Production (with validation):**
```bash
# Default behavior - validates tokens and tests connection
curl -X POST "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "property-uuid",
    "platform_type": "airbnb",
    "platform_listing_id": "airbnb-listing-123",
    "access_token": "real-oauth-access-token",
    "refresh_token": "real-oauth-refresh-token",
    "platform_metadata": {"listing_id": "123"}
  }'
```

**Common Errors (when skip_connection_test=false):**

| Error | Cause | Solution |
|-------|-------|----------|
| `400 Platform booking_com not yet supported` | Platform adapter not implemented | Use `skip_connection_test=true` for development |
| `400 Connection test failed: verify your OAuth tokens` | Invalid tokens or OAuth flow incomplete | Complete OAuth flow first, or use skip flag for testing |
| `400 Connection test failed: [platform error]` | Platform API rejected request | Check token validity, permissions, and platform status |

**Admin UI:**

The Admin UI's "New Connection" modal includes a checkbox:
- ✅ **"Mock mode (skip connection test)"** - Default: ON
- When checked: Passes `skip_connection_test=true` to the API
- Allows creating connections without valid OAuth tokens for development/testing

**Database Persistence:**

Channel connections are persisted in PostgreSQL:
- **Table:** `channel_connections`
- **Migration:** `supabase/migrations/20260102000000_add_property_fields_to_channel_connections.sql`
- **Key columns:** `id`, `agency_id`, `property_id`, `platform_type`, `platform_listing_id`, `status`, `platform_metadata`, `access_token_encrypted`, `refresh_token_encrypted`
- **Soft delete:** Rows marked with `deleted_at` timestamp instead of hard deletion

**List Endpoint:**

GET `/api/v1/channel-connections/` returns JSON array of all connections:
```json
[
  {
    "id": "connection-uuid",
    "tenant_id": "agency-uuid",
    "property_id": "property-uuid",
    "platform_type": "booking_com",
    "platform_listing_id": "mock_booking_123",
    "status": "active",
    "platform_metadata": {"mock_mode": true},
    "last_sync_at": null,
    "created_at": "2026-01-02T10:00:00Z",
    "updated_at": "2026-01-02T10:00:00Z"
  }
]
```

**Troubleshooting - List Returns Only Stub:**

If GET `/api/v1/channel-connections/` returns only hardcoded stub data (single airbnb entry with fixed UUIDs):
1. **WHERE:** HOST-SERVER-TERMINAL - Check deployed commit
   ```bash
   docker exec pms-backend env | grep SOURCE_COMMIT
   ```
2. **WHERE:** HOST-SERVER-TERMINAL - Verify API schema has skip_connection_test param
   ```bash
   curl -s https://api.fewo.kolibri-visions.de/openapi.json | jq '.paths."/api/v1/channel-connections/".post.parameters'
   # Should show skip_connection_test query parameter
   ```
3. **If old build:** Redeploy from main branch (commit c097acd or later)
4. **WHERE:** SUPABASE-SQL-EDITOR - Verify schema migration applied
   ```sql
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'channel_connections'
   AND column_name IN ('property_id', 'platform_listing_id');
   -- Should return both columns
   ```
5. **If schema missing:** Apply migration (see below)

**Applying Schema Migration:**

**WHERE:** SUPABASE-SQL-EDITOR (Supabase Dashboard → SQL Editor)
```sql
-- Run migration: 20260102000000_add_property_fields_to_channel_connections.sql
-- This adds property_id and platform_listing_id columns
-- Copy-paste migration file contents here or use Supabase CLI
```

**WHERE:** HOST-SERVER-TERMINAL (Alternative: Supabase CLI)
```bash
supabase migration up --file supabase/migrations/20260102000000_add_property_fields_to_channel_connections.sql
```

**Expected Result After Fix:**
- Created connections appear in list immediately
- No hardcoded stub data
- Empty array `[]` when no connections exist

**Troubleshooting - List Returns HTTP 500:**

If GET `/api/v1/channel-connections/` returns HTTP 500 and breaks Admin UI:
1. **WHERE:** HOST-SERVER-TERMINAL - Check backend logs for ResponseValidationError
   ```bash
   docker logs pms-backend --tail 100 | grep -i "ResponseValidationError\|property_id"
   # Look for: loc=('response', 0, 'property_id') msg='UUID input should be a string/bytes/UUID' input=None
   ```
2. **Root Cause:** Legacy connection rows have `property_id = null` but response model expected non-null UUID
3. **Fix:** Deploy includes:
   - Response model accepts `Optional[UUID]` for property_id
   - Per-row validation skips invalid rows instead of crashing entire endpoint
4. **WHERE:** HOST-SERVER-TERMINAL - Verify fix deployed
   ```bash
   docker exec pms-backend env | grep SOURCE_COMMIT
   # Should be commit 4c28afd or later
   ```
5. **If old build:** Redeploy from main branch (commit 4c28afd or later)
6. **Expected Result:**
   - GET returns HTTP 200 with array (may exclude legacy rows with validation errors)
   - Backend logs warnings for skipped rows but endpoint stays up
   - Admin UI Connections page loads successfully

**Admin UI - Properties Fetch 422:**

If Admin UI shows 422 error when fetching properties:
- **Cause:** Frontend requested `limit=200` but backend validation rejects high limits
- **Fix:** Deployed frontend uses safe limit=100
- **Verify:** Check browser DevTools → Network → `/api/v1/properties` request shows `?limit=100`

**Admin UI - Property Dropdown Empty:**

If New Connection modal shows empty Property dropdown despite 200 response:
1. **WHERE:** BROWSER - Check DevTools → Network → `/api/v1/properties` response format
   - **Expected:** `{items: [...], total: 16, limit: 100, offset: 0, has_more: false}`
   - **Issue:** Properties endpoint returns paginated object, not array
2. **Root Cause:** Frontend expected array but API returns `{items: [...]}`
3. **Fix:** Deployed frontend parses response correctly:
   ```typescript
   const items = Array.isArray(data) ? data : (data.items || data.properties || []);
   ```
4. **Expected Result:**
   - Dropdown shows all properties with readable labels
   - Loading state: "Loading properties..." (disabled)
   - Error state: "No properties available" (red background)
   - Success state: "Property Name (internal_name) - 12345678"

**Multi-Tenant Filtering (Channel Connections):**

Channel connections list is filtered by agency_id for tenant isolation:
- **Backend:** GET `/api/v1/channel-connections/` uses `get_current_agency_id` dependency
- **Filter:** `WHERE agency_id = $1 AND deleted_at IS NULL`
- **Result:** Each tenant only sees their own connections
- **Security:** Prevents cross-tenant data leaks

If booking_com connection created via API doesn't appear in UI:
1. **WHERE:** HOST-SERVER-TERMINAL - Verify connection was created for correct agency
   ```bash
   # Check connection's agency_id matches user's agency
   curl -s "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/" \
     -H "Authorization: Bearer $TOKEN" | jq '.[] | {id, agency_id, platform_type}'
   ```
2. **Verify:** Created connection's `agency_id` matches property's `agency_id`
3. **Expected:** Backend derives `agency_id` from property, not from hardcoded values

**Mock Mode Behavior:**

When creating connections with `skip_connection_test=true`:
- ✅ Skips OAuth validation and platform API health checks
- ✅ Allows unsupported platforms (e.g., booking_com)
- ✅ Persists to database immediately
- ✅ Skips initial sync trigger
- ⚠️ Tokens still encrypted before storage (but not validated)

**Backoffice Console → New Connection:**

When opening the New Connection modal in Admin UI:
- **Property:** Empty by default - user must select from dropdown
- **Platform:** Empty by default - user must explicitly select (no preselection)
- **Intentional Design:** Forces user to make conscious choice rather than defaulting to Airbnb
- **Mock Mode:** After platform selection, mock values are auto-suggested:
  - `platform_listing_id`: `mock_{platform}_{timestamp}`
  - `access_token`: `mock_access_token`
  - `refresh_token`: `mock_refresh_token`
- **Validation:** "Create Connection" button disabled until both Property and Platform selected

**Expected Behavior:**
1. Open modal → both Property and Platform show placeholder text
2. Select Property → dropdown populated from `/api/v1/properties?limit=100`
3. Select Platform → `platform_listing_id` auto-populated with `mock_{platform}_{timestamp}`
4. Fill remaining fields → click "Create Connection"

---

### GET /api/v1/channel-connections/{connection_id}

**Purpose:** Get details for a specific channel connection

**RBAC:** Requires valid JWT

**Success Response (200):**
```json
{
  "id": "connection-uuid",
  "tenant_id": "agency-uuid",
  "property_id": "property-uuid",
  "platform_type": "airbnb",
  "platform_listing_id": "airbnb-listing-123",
  "status": "active",
  "platform_metadata": {"listing_id": "123"},
  "last_sync_at": "2025-12-28T10:00:00Z",
  "created_at": "2025-12-01T00:00:00Z",
  "updated_at": "2025-12-28T10:00:00Z"
}
```

**Error Response (404):**
```json
{
  "detail": "Connection not found"
}
```

**Example:**
```bash
curl -X GET "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID" \
  -H "Authorization: Bearer $TOKEN"
```

---

### POST /api/v1/channel-connections/{connection_id}/test

**Purpose:** Test if a channel connection is healthy (validates OAuth tokens and platform API connectivity)

**RBAC:** Requires valid JWT

**Request Body:**
```json
{}
```

**Success Response (200):**
```json
{
  "connection_id": "connection-uuid",
  "platform_type": "airbnb",
  "healthy": true,
  "message": "Connection is healthy",
  "details": {
    "platform_listing_id": "airbnb-listing-123",
    "last_sync_at": "2025-12-28T10:00:00Z"
  }
}
```

**Failed Health Check (200 with healthy=false):**
```json
{
  "connection_id": "connection-uuid",
  "platform_type": "airbnb",
  "healthy": false,
  "message": "Connection test failed",
  "details": {}
}
```

**Error Response (404):**
```json
{
  "connection_id": "connection-uuid",
  "platform_type": "unknown",
  "healthy": false,
  "message": "Connection not found",
  "details": {}
}
```

**Example:**
```bash
curl -X POST "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### GET /api/v1/channel-connections/{connection_id}/sync-batches

**Purpose:** List recent sync batches for a connection (aggregated status for batch operations)

**RBAC:** Requires valid JWT

**Query Parameters:**
- `limit` (optional): Number of batches to return (max 200, default 50)
- `offset` (optional): Pagination offset (default 0)
- `status` (optional): Filter by batch status: `any`, `running`, `success`, `failed` (default `any`)

**Success Response (200):**
```json
[
  {
    "batch_id": "batch-uuid",
    "connection_id": "connection-uuid",
    "batch_status": "success",
    "status_counts": {
      "triggered": 0,
      "running": 0,
      "success": 3,
      "failed": 0,
      "other": 0
    },
    "created_at_min": "2025-12-28T10:00:00Z",
    "updated_at_max": "2025-12-28T10:00:15Z",
    "operations": [
      {
        "operation_type": "availability_update",
        "status": "success",
        "updated_at": "2025-12-28T10:00:05Z"
      },
      {
        "operation_type": "pricing_update",
        "status": "success",
        "updated_at": "2025-12-28T10:00:10Z"
      },
      {
        "operation_type": "bookings_sync",
        "status": "success",
        "updated_at": "2025-12-28T10:00:15Z"
      }
    ]
  }
]
```

**Example:**
```bash
# List recent batches
curl -s "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync-batches?limit=10&status=any" \
  -H "Authorization: Bearer $TOKEN"
```

**Batch Status Values:**
- `running`: At least one operation still in progress (triggered/queued/running)
- `success`: All operations completed successfully
- `failed`: At least one operation failed
- `unknown`: No operations or unexpected state

---

### GET /api/v1/channel-connections/{connection_id}/sync-batches/{batch_id}

**Purpose:** Get detailed status for a specific sync batch (for polling until completion)

**RBAC:** Requires valid JWT

**Success Response (200):**
```json
{
  "batch_id": "batch-uuid",
  "connection_id": "connection-uuid",
  "batch_status": "success",
  "status_counts": {
    "triggered": 0,
    "running": 0,
    "success": 3,
    "failed": 0,
    "other": 0
  },
  "created_at_min": "2025-12-28T10:00:00Z",
  "updated_at_max": "2025-12-28T10:00:15Z",
  "operations": [
    {
      "operation_type": "availability_update",
      "status": "success",
      "updated_at": "2025-12-28T10:00:05Z"
    }
  ]
}
```

**Error Response (404):**
```json
{
  "error": "batch_not_found",
  "message": "Batch not found or does not belong to this connection"
}
```

**Example - Polling Pattern:**
```bash
# 1. Trigger sync and capture batch_id
RESPONSE=$(curl -s -X POST "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type":"full"}')

BATCH_ID=$(echo "$RESPONSE" | jq -r '.batch_id')
echo "Triggered batch: $BATCH_ID"

# 2. Poll batch status until completion
while true; do
  BATCH_STATUS=$(curl -s "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync-batches/$BATCH_ID" \
    -H "Authorization: Bearer $TOKEN" | jq -r '.batch_status')

  echo "Batch status: $BATCH_STATUS"

  if [[ "$BATCH_STATUS" != "running" ]]; then
    echo "Batch finished: $BATCH_STATUS"
    break
  fi

  sleep 1
done
```

**Note on Trailing Slash:**

⚠️ **IMPORTANT:** The list endpoint (`GET /api/v1/channel-connections/`) requires a trailing slash when using query parameters to avoid HTTP 307 redirects:

```bash
# ✅ CORRECT - Trailing slash before query params
curl "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/?limit=5&offset=0"

# ❌ WRONG - No trailing slash causes 307 redirect
curl "https://api.fewo.kolibri-visions.de/api/v1/channel-connections?limit=5&offset=0"
```

**Why:** FastAPI treats `/channel-connections` and `/channel-connections/` as different routes. The list endpoint is registered with trailing slash.

**Fix:** Frontend uses `buildApiUrl()` helper to ensure consistent URL construction.

**Detail/Sync/Test Endpoints:** Do NOT use trailing slash (no query params needed):
```bash
# ✅ CORRECT - No trailing slash for detail/action endpoints
curl "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID"
curl -X POST "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/test"
curl -X POST "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync"
```

**Troubleshooting curl Verification:**

If you encounter issues when verifying channel-connections endpoints via curl:

**Issue: 307 Redirect with Empty Body**
```bash
# Symptom: curl returns 307 and empty response
curl "https://api.fewo.kolibri-visions.de/api/v1/channel-connections?limit=5"

# Fix 1: Add trailing slash before query params
curl "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/?limit=5"

# Fix 2: Use -L flag to follow redirects automatically
curl -L "https://api.fewo.kolibri-visions.de/api/v1/channel-connections?limit=5"
```

**Issue: 401 "Token has expired" or 403 "Not authenticated"**
```bash
# Symptom: curl returns 401 Unauthorized or 403 Forbidden

# Fix 1: Ensure environment variables are loaded
source /root/pms_env.sh

# Fix 2: Verify SB_URL is set (required for token refresh)
echo $SB_URL
# Expected: https://supabase-kong-url (not empty)

# Fix 3: Refresh JWT token
curl -X POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -H "apikey: $SB_ANON_KEY" \
  -d "{\"email\":\"admin@example.com\",\"password\":\"your-password\"}" \
  | jq -r '.access_token'

# Fix 4: Use refreshed token
TOKEN=$(curl -X POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -H "apikey: $SB_ANON_KEY" \
  -d "{\"email\":\"admin@example.com\",\"password\":\"your-password\"}" \
  | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/?limit=5"
```

**Common Pitfall:** In new SSH sessions, environment variables (SB_URL, SB_ANON_KEY) are not loaded automatically. Always run `source /root/pms_env.sh` first.

---

## Backoffice Console — Connections (E2E Check)

**Purpose:** End-to-end verification of Channel Connections management in the Admin UI (Backoffice Console).

**URL:** `https://admin.fewo.kolibri-visions.de/connections`

**RBAC:** Admin and Manager roles only

### A) Connections Quick Actions

Each connection row in the Connections table provides inline quick actions for rapid E2E testing and operational workflows:

**Quick Action Buttons:**

1. **Test** - Test connection health
   - Endpoint: `POST /api/v1/channel-connections/{id}/test`
   - Response: Health status, platform API connectivity check
   - Display: Shows pass/fail notification banner
   - Mock Mode: Displays "Mock Mode (Simulated)" badge when `CHANNEL_MOCK_MODE=true`

2. **View Logs** - Navigate to Channel Sync page with logs preloaded
   - Action: Sets `localStorage.setItem("channelSync:lastConnectionId", connection_id)`
   - Navigation: Redirects to `/channel-sync` page
   - Result: Logs load immediately for the selected connection (no manual Auto-detect needed)
   - UX: Does NOT auto-open sync log details modal (modal opens only on explicit user row click)

3. **Avail** (previously **A**) = Availability sync (quick trigger)
   - Endpoint: `POST /api/v1/channel-connections/{id}/sync` with `{"sync_type": "availability"}`
   - Response: Returns `task_ids` array (single task for availability-only sync)
   - Display: Shows success toast "Availability sync triggered (Batch: ...)" with auto-dismiss after 10 seconds

4. **Price** (previously **P**) = Pricing sync (quick trigger)
   - Endpoint: `POST /api/v1/channel-connections/{id}/sync` with `{"sync_type": "pricing"}`
   - Response: Returns `task_ids` array (single task for pricing-only sync)
   - Display: Shows success toast "Pricing sync triggered (Batch: ...)" with auto-dismiss after 10 seconds

5. **Book** (previously **B**) = Bookings sync (quick trigger)
   - Endpoint: `POST /api/v1/channel-connections/{id}/sync` with `{"sync_type": "bookings"}`
   - Response: Returns `task_ids` array (single task for bookings-only sync)
   - Display: Shows success toast "Bookings sync triggered (Batch: ...)" with auto-dismiss after 10 seconds

6. **Full** (previously **F**) = Full sync (quick trigger)
   - Endpoint: `POST /api/v1/channel-connections/{id}/sync` with `{"sync_type": "full"}`
   - Response: Returns `batch_id` + `task_ids` array (3 tasks: availability, pricing, bookings)
   - Display: Shows success toast "Full sync triggered (Batch: ...)" with batch ID and task count, auto-dismiss after 10 seconds

**Expected UX Behavior:**

- **No Dangerous Defaults:** No sync type or platform is preselected in form fields
- **Trigger Disabled Until Ready:** Sync trigger buttons disabled until all required selections are made
- **Auto-Refresh After Trigger:** After triggering sync, connections list refetches to update `last_sync_at` column
- **Logs Auto-Load After Trigger:** After successful sync trigger, logs automatically refresh to show new sync operation
- **Clear Resets All State:** Clicking "Clear" on Connection ID field:
  - Clears logs list
  - Closes sync log details modal if open
  - Hides stale success banners
  - Resets all filters and search state
- **Inline Status Feedback:** Each quick action button shows loading state during operation (e.g., "Testing..." or "...")
- **Last Sync Age Display:** `last_sync_at` column shows relative time ("3m ago", "2h ago", "never") instead of full ISO timestamp

**Fastest UI-Based E2E Check:**

The quick actions provide the fastest path for operators to verify end-to-end Channel Manager functionality:

1. Click **Test** → Verify connection health (< 1 second)
2. Click **A** (Availability) → Trigger sync (< 1 second to queue)
3. Click **View Logs** → Navigate to logs page and verify sync completed (logs preloaded)
4. Verify status badge shows "success" (green) or "failed" (red)

This workflow validates: API authentication, connection health, sync task queueing, Celery workers, database writes, and UI state management.

---

### UI Flow (Step-by-Step)

**1. Create New Connection**

1. Navigate to Connections page
2. Click "New Connection" button
3. **Verify:** Platform dropdown is **NOT preselected** (shows "Select a platform..." placeholder)
   - This is intentional UX - user must explicitly choose platform
   - Submit button disabled until platform selected
4. Select Property from dropdown
5. Select Platform (e.g., `booking_com`)
6. **For dev/staging:** Check "Skip connection test (Mock mode)" checkbox
   - This bypasses real API calls during connection creation
   - Backend accepts `?skip_connection_test=true` query parameter
7. Fill Platform Listing ID (e.g., `test_booking_123`)
8. Click "Create Connection"
9. **Expected:** New connection row appears in table

**2. Test Connection Health**

1. Find the newly created connection in the table
2. Click "Test" button (inline action)
3. **Expected (Mock Mode):**
   - Green notification: "Connection test passed: Mock: Connection is healthy (Mock Mode - see runbook for production setup)"
   - Badge shows "Mock Mode (Simulated)"
4. **Expected (Real Mode):**
   - Green notification if healthy, red if failed
   - No mock mode badge

**3. Trigger Sync & Monitor Logs**

1. Click "Open" on the connection row
2. In Connection Details modal, select "Availability" from sync type dropdown
3. Click "Trigger Sync"
4. **Expected:**
   - Green notification: "Sync gestartet: availability"
   - Sync Logs section shows new log entry with status "triggered" or "running"
5. Wait ~5-10 seconds (auto-refresh enabled by default)
6. **Expected:** Log status changes to "success" (green badge)

**4. View Batch History**

1. Scroll to "Batch History" section in Connection Details modal
2. **Expected:** Recent batch appears with:
   - Batch ID (truncated, click to copy full UUID)
   - Status badge (green for success)
   - Operation counts (e.g., "1/1 success")
   - Timestamp

**5. Navigate Batch Details**

1. Click on a batch row in Batch History table
2. **Expected:** Batch Details modal opens (z-index 70, on top of Connection Details)
3. **Verify:** Back arrow (←) visible in header (icon-only, no text)
4. Click back arrow
5. **Expected:** Returns to Connection Details modal (Batch Details closes)

**6. Log Details → Batch Details Navigation**

1. In Sync Logs section, click "Details" on any batched log entry
2. **Expected:** Log Details modal opens
3. If log has a `batch_id`, "Open Batch Details →" button appears
4. Click "Open Batch Details →"
5. **Expected:** Batch Details modal opens on top (Log Details stays in background)
6. Click back arrow ←
7. **Expected:** Returns to Log Details modal (same log entry, Batch Details closes)
8. Close Log Details modal (X button)
9. **Expected:** Returns to Connection Details

### API Flow (HOST-SERVER-TERMINAL)

**Prerequisites:**
```bash
# Export credentials
export API="https://api.fewo.kolibri-visions.de"
export SB_URL="https://sb-pms.kolibri-visions.de"
export ANON_KEY="your-anon-key"
export EMAIL="admin@example.com"
export PASSWORD="your-password"

# Fetch JWT token
export TOKEN=$(curl -sX POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | \
  python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
```

**1. Create Connection (Skip Connection Test)**

```bash
# Get first property ID
export PID=$(curl -sX GET "$API/api/v1/properties?limit=1" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c 'import sys,json; data=json.load(sys.stdin); print(data["items"][0]["id"] if "items" in data and len(data["items"]) > 0 else "")')

# Create connection with skip_connection_test=true (for dev/mock mode)
curl -X POST "$API/api/v1/channel-connections?skip_connection_test=true" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"property_id\": \"$PID\",
    \"platform_type\": \"booking_com\",
    \"platform_listing_id\": \"test_booking_e2e_$(date +%s)\",
    \"status\": \"active\"
  }"

# Expected response (201):
# {
#   "id": "new-connection-uuid",
#   "property_id": "...",
#   "platform_type": "booking_com",
#   "status": "active",
#   "created_at": "2026-01-02T..."
# }
```

**2. List Connections**

```bash
# List all connections
curl -sX GET "$API/api/v1/channel-connections" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# IMPORTANT: Response is a JSON ARRAY (not wrapped in {items:...})
# Example:
# [
#   {
#     "id": "abc-123",
#     "property_id": "prop-456",  // May be null for legacy rows
#     "platform_type": "booking_com",
#     "status": "active",
#     ...
#   },
#   {
#     "id": "legacy-airbnb",
#     "property_id": null,  // Legacy row without property_id
#     "platform_type": "airbnb",
#     ...
#   }
# ]
```

**3. Test Connection**

```bash
# Save connection ID
export CID="new-connection-uuid"

# Test connection health
curl -X POST "$API/api/v1/channel-connections/$CID/test" \
  -H "Authorization: Bearer $TOKEN"

# Expected (Mock Mode):
# {
#   "healthy": true,
#   "message": "Mock: Connection is healthy",
#   "details": {"mock_mode": true, "simulated": true, ...}
# }
```

**4. Trigger Sync**

```bash
# Trigger availability sync
curl -X POST "$API/api/v1/channel-connections/$CID/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "availability"}'

# Expected response (200):
# {
#   "status": "triggered",
#   "message": "Availability sync triggered",
#   "task_ids": ["celery-task-uuid"],
#   "batch_id": "batch-uuid"  // For full sync only
# }
```

**5. Fetch Sync Logs**

```bash
# Get sync logs for connection
curl -sX GET "$API/api/v1/channel-connections/$CID/sync-logs?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Response may be array or {logs: [...]} (admin UI handles both)
```

### Troubleshooting

**Platform dropdown empty / "Select a platform..." not showing**
- **Cause:** Platform select has `disabled` attribute on placeholder option (browser compatibility issue)
- **Fix:** Latest deploy removes `disabled` attribute (commit `f446745` or later)
- **Workaround:** Select any platform, save, then edit to change platform

**Failed to fetch connections (HTTP 404) in Admin UI**
- **Symptom:** Connections page shows error, browser console shows `GET .../channel-connections/ -> 404 Not Found`
- **Cause:** Frontend using wrong URL with trailing slash (e.g., `/api/v1/channel-connections/` instead of `/api/v1/channel-connections`)
- **Fix:** Latest deploy removes trailing slashes from collection endpoints (commit after `33e1357`)
- **Verify endpoint works:** `curl -i "$API/api/v1/channel-connections" -H "Authorization: Bearer $TOKEN"`
  - Expected: HTTP 200 with JSON array of connections
  - Wrong: `curl "$API/api/v1/channel-connections/"` → HTTP 404
- **Root cause:** FastAPI routes `/channel-connections` and `/channel-connections/` as different endpoints
- **Prevention:** Use `buildApiUrl()` helper in frontend for consistent URL construction

**Properties dropdown empty in New Connection modal**
- **Cause:** API returns `{items: [...]}` but frontend expects plain array, OR filtering by agency_id returns empty
- **Fix:** Frontend parses `data.items || data.properties || data` (handles all response formats)
- **Verify API:** `curl "$API/api/v1/properties?limit=10" -H "Authorization: Bearer $TOKEN"`
  - Should return `{items: [...], total: N}`
- **Check role:** Ensure user has access to properties (admin/manager role, correct agency_id)

**curl: command not found / sed: command not found (smoke/monitoring scripts)**
- **Symptom:** Scripts fail before making requests: `curl: command not found` or `sed: command not found`
- **Cause:** PATH missing `/usr/bin` and `/bin` in minimal shells (cron, Coolify exec, non-interactive)
- **Commands exist at:** `/usr/bin/curl`, `/usr/bin/sed` but aren't found due to broken PATH
- **Fix (immediate):**
  ```bash
  # Export PATH before running script
  export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  bash backend/scripts/pms_phase23_smoke.sh
  ```
- **Fix (permanent):** Latest deploy includes automatic PATH bootstrap in:
  - `backend/scripts/pms_smoke_common.sh` (sourced by all smoke scripts)
  - `backend/scripts/pms_channel_seed_connection.sh` (standalone script)
  - Docker exec calls include `-e PATH="..."` for container execution
- **Verification (endpoints work once PATH is fixed):**
  ```bash
  # External endpoints
  curl -I https://api.fewo.kolibri-visions.de/health  # Expect: 200

  # Internal endpoints (from container)
  curl -I /health/ready    # Expect: 200
  curl -I /openapi.json    # Expect: 200
  curl -I /docs            # Expect: 200
  ```
- **Debug:**
  ```bash
  # Check if commands exist
  command -v curl  # Should show: /usr/bin/curl
  command -v sed   # Should show: /usr/bin/sed

  # Check current PATH
  echo $PATH       # Should include: /usr/bin:/bin
  ```
- **Related:** See [backend/scripts/README.md](../../scripts/README.md#troubleshooting) for PATH bootstrap details

**Channel Manager module not mounted - /api/v1/channel-connections returns 404**
- **Symptom:** Requests to `/api/v1/channel-connections` return 404 even though `CHANNEL_MANAGER_ENABLED=true`
- **Cause:** Channel Manager module failed to import due to `ImportError: cannot import name 'Json' from 'asyncpg'`
- **Logs show:**
  ```
  Channel Manager module enabled via CHANNEL_MANAGER_ENABLED=true
  Channel Manager module not available: cannot import name 'Json' from 'asyncpg' (/opt/venv/lib/python3.12/site-packages/asyncpg/__init__.py)
  ```
- **Root cause:** asyncpg version incompatibility - some versions don't export `Json` at top level
- **Fix:** Latest deploy includes compatibility shim (`backend/app/core/pg_json.py`) that:
  - Tries `from asyncpg.types import Json` (most common)
  - Falls back to `from asyncpg import Json` (older versions)
  - Falls back to native dict (asyncpg auto-converts dicts to jsonb)
- **Verification (endpoints work once module mounts):**
  ```bash
  # Check OpenAPI includes channel-connections routes
  curl -s https://api.fewo.kolibri-visions.de/openapi.json | grep -o '/api/v1/channel-connections' | head -1
  # Expected: /api/v1/channel-connections

  # Check endpoint works
  curl -i https://api.fewo.kolibri-visions.de/api/v1/channel-connections -H "Authorization: Bearer $TOKEN"
  # Expected: HTTP 200 with JSON array (not 404)
  ```
- **Check module is mounted:**
  ```bash
  # Inside pms-backend container
  docker exec pms-backend bash -c 'curl -s localhost:8000/openapi.json | python3 -c "import sys, json; routes = [p for p in json.load(sys.stdin)[\"paths\"].keys()]; print(f\"TOTAL_ROUTES={len(routes)}\"); print(f\"CHANNEL_ROUTES={len([r for r in routes if \"channel\" in r])}\");"'
  # Expected: CHANNEL_ROUTES > 0 (should show routes like /api/v1/channel-connections, /api/v1/channel-connections/{connection_id}, etc.)
  ```
- **Related:** See `backend/app/core/pg_json.py` for compatibility implementation

**GET /channel-connections returns HTTP 500 (ResponseValidationError)**
- **Cause:** Backend response validation fails when `property_id` is `null` (legacy rows)
- **Symptom:** `"detail": "Response validation error", "errors": [{"loc": ["property_id"], "msg": "none is not an allowed value"}]`
- **Fix:** Latest deploy includes tolerant response validation (per-row validation, skips invalid rows)
- **Verify migration:** Ensure DB has `property_id uuid NULL` (nullable column)
  ```sql
  -- In Supabase SQL Editor
  SELECT column_name, is_nullable, data_type
  FROM information_schema.columns
  WHERE table_name = 'channel_connections'
    AND column_name IN ('property_id', 'platform_listing_id');

  -- Expected: Both columns nullable (is_nullable = 'YES')
  ```
- **DB Hotfix (if needed):**
  ```sql
  -- Add columns if missing (idempotent)
  ALTER TABLE public.channel_connections
  ADD COLUMN IF NOT EXISTS property_id uuid NULL REFERENCES properties(id) ON DELETE CASCADE;

  ALTER TABLE public.channel_connections
  ADD COLUMN IF NOT EXISTS platform_listing_id text NULL;
  ```

**Token expired (401 Unauthorized)**
- **Cause:** JWT tokens expire after ~1 hour (Supabase default)
- **Fix:** Re-fetch token using Prerequisites command above
- **Automation:** Use `pms_phase23_smoke.sh` or `pms_channel_sync_poll.sh` (auto-fetches token)

**Back arrow missing in Batch Details**
- **Cause:** Old deploy (before commit `f446745`)
- **Fix:** Back arrow now always visible (context-aware tooltip)
- **Verify:** Check `frontend/app/connections/page.tsx:1667-1677` for unconditional back button

**Sync logs empty / "No logs found"**
- **Cause:** Auto-refresh disabled, OR sync not triggered yet, OR agency_id filtering issue
- **Fix:**
  1. Enable "Auto-refresh (10s)" toggle in Connection Details modal
  2. Wait ~10 seconds after triggering sync
  3. Click "Trigger Sync" again to create a new log entry
- **Verify API:** `curl "$API/api/v1/channel-connections/$CID/sync-logs?limit=10" -H "Authorization: Bearer $TOKEN"`

**Batch Details modal doesn't close when clicking back arrow**
- **Cause:** JavaScript error in console (check browser DevTools)
- **Fix:** Hard refresh page (Cmd+Shift+R / Ctrl+Shift+F5)
- **Check:** Modal stack z-index conflict (Log Details z-[60], Batch Details z-[70])

**Connection test shows "Connection test failed: Invalid credentials"**
- **Cause:** Real mode enabled (`CHANNEL_MOCK_MODE=false`) but no credentials configured
- **Fix (Dev):** Enable mock mode: `export CHANNEL_MOCK_MODE=true` in backend container
- **Fix (Prod):** Add platform-specific credentials (see [Production Readiness](runbook.md#production-readiness))

### Related Documentation

- [Admin UI – Channel Manager Operations](#admin-ui--channel-manager-operations) - API endpoints and UI features
- [UX Features](#ux-features) - New Connection modal and Batch Details navigation details
- [Channel Manager Connection Testing](../scripts/README.md#channel-manager-connection-testing) - curl examples
- [Mock Mode for Channel Providers](#mock-mode-for-channel-providers) - Dev/staging mock mode setup

---

## Connections → Property Mapping

**Purpose:** Map channel connections to PMS properties and fix legacy unmapped connections.

**Context:**
- Each channel connection should be mapped to a specific PMS property via `property_id`
- Legacy connections may have `property_id = null` (created before multi-property support)
- Unmapped connections have limited functionality - property mapping is required for full features

### UI Features

#### Connections List

**Property Column:**
- Shows mapped property name (from `/api/v1/properties`)
- Falls back to truncated `property_id` if name not resolvable
- Displays **"Unmapped"** badge (yellow) if `property_id` is null

#### Connection Details Modal

**Property Mapping Section:**

**When Mapped (`property_id` exists):**
- Displays property name
- Shows full property ID with copy-to-clipboard icon
- Shows platform listing ID with copy-to-clipboard icon (if available)
- "Change Property" link to reassign

**When Unmapped (`property_id` is null):**
- Prominent yellow warning banner:
  - "No Property Assigned"
  - "This is a legacy connection without a mapped property. Assign a property to enable full functionality."
- **"Assign Property"** button (yellow, primary action)

#### Assign Property Modal

**Workflow:**
1. Click "Assign Property" button (for unmapped) or "Change Property" link (for mapped)
2. Modal opens with property dropdown
3. Select property from list (fetched from `/api/v1/properties`)
4. Click "Assign Property" to save
5. Modal closes, connection details refresh
6. Connections list updates to show property name

**Validation:**
- "Assign Property" button disabled until property selected
- Shows "Assigning..." during save operation
- Success toast: "Property assigned successfully"
- Error toast: "Failed to assign property: [error message]"

### API Endpoint

**Update Connection (Partial Update):**

```bash
# PATCH or PUT /api/v1/channel-connections/{connection_id}
# Endpoint supports partial updates - only provide fields to update

# Example: Assign property to legacy connection
export CID="connection-uuid"
export PID="property-uuid"

curl -X PUT "$API/api/v1/channel-connections/$CID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"property_id\": \"$PID\"}"

# Expected response (200):
# {
#   "id": "connection-uuid",
#   "tenant_id": "agency-uuid",
#   "property_id": "property-uuid",  // Now mapped
#   "platform_type": "booking_com",
#   "platform_listing_id": "test_booking_123",
#   "status": "active",
#   "platform_metadata": {...},
#   "last_sync_at": null,
#   "created_at": "2026-01-02T...",
#   "updated_at": "2026-01-02T..."  // Updated timestamp
# }
```

**Supported Update Fields:**
- `property_id` (UUID or null) - Map/unmap connection to property
- `platform_listing_id` (string or null) - Platform-specific listing identifier
- `platform_metadata` (object or null) - Platform-specific configuration
- `status` (string) - Connection status (active, paused, error)

**RBAC:** Admin and Manager roles only

**Tenant Scoping:**
- Backend enforces agency_id filtering via `get_current_agency_id` dependency
- Users can only update connections belonging to their agency

### Troubleshooting

**Property dropdown empty in Assign Property modal**
- **Cause:** No properties exist for the agency, or properties fetch failed
- **Fix:**
  1. Verify `/api/v1/properties?limit=100` returns data
  2. Check user's agency has properties created
  3. Check browser console for fetch errors
- **Workaround:** Create property first via Properties page

**"Failed to assign property: 404"**
- **Cause:** Property ID does not exist or user doesn't have access to it
- **Fix:** Ensure property UUID is correct and belongs to same agency
- **Verify:** `curl "$API/api/v1/properties" -H "Authorization: Bearer $TOKEN"`

**"Failed to assign property: 403"**
- **Cause:** User lacks admin/manager role
- **Fix:** Verify role in token: `jwt_decode($TOKEN) | jq .role`
- **Expected:** Role should be "admin" or "manager", not "staff"

**Connection still shows "Unmapped" after assignment**
- **Cause:** Frontend cache not refreshed
- **Fix:**
  1. Close and reopen Connection Details modal
  2. Hard refresh page (Cmd+Shift+R / Ctrl+Shift+F5)
  3. Check backend actually updated: `curl "$API/api/v1/channel-connections/$CID" -H "Authorization: Bearer $TOKEN"`

**PUT request returns 500 (database error)**
- **Cause:** Database connection pool not available in service layer, or UPDATE query failed
- **Fix:** Check backend logs for asyncpg errors
- **Verify service:** Ensure `ChannelConnectionService.update_connection()` has DB connection
- **Check migration:** Ensure `property_id` column exists and is nullable

**Legacy connections with property_id=null cause validation errors**
- **Symptom:** GET `/channel-connections` returns 500 for some connections
- **Fix:** Already handled via per-row validation (skips invalid rows)
- **Long-term:** Assign properties to all legacy connections via UI or bulk script

### Related Documentation

- [Backoffice Console — Connections (E2E Check)](#backoffice-console--connections-e2e-check) - Full E2E workflow
- [Admin UI – Channel Manager Operations](#admin-ui--channel-manager-operations) - API endpoints
- Database Migration: `supabase/migrations/20260102000000_add_property_fields_to_channel_connections.sql`

---

## Admin UI - Channel Sync

**Purpose:** Web-based admin interface for triggering and monitoring channel sync operations.

**URL:** `https://admin.fewo.kolibri-visions.de/channel-sync`

**RBAC:** Admin and Manager roles only (same as API `/api/availability/sync`)

---

### Sync Types

The Channel Sync Admin UI supports three sync types, each using different API endpoints:

**1. Availability Sync**
- **Endpoint:** `POST /api/v1/availability/sync`
- **Purpose:** Sync availability calendar only
- **Required Fields:** platform, property_id
- **Optional Fields:** connection_id (auto-detected), start_date, end_date

**2. Pricing Sync**
- **Endpoint:** `POST /api/v1/availability/sync`
- **Purpose:** Sync pricing information only
- **Required Fields:** platform, property_id
- **Optional Fields:** connection_id (auto-detected), start_date, end_date

**3. Full Sync**
- **Endpoint:** `POST /api/v1/channel-connections/{connection_id}/sync`
- **Purpose:** Complete sync (availability + pricing + bookings)
- **Required Fields:** connection_id (must be valid UUID)
- **Optional Fields:** start_date, end_date
- **Response:** Returns `batch_id` and `task_ids` array for tracking multiple concurrent operations

**Key Differences:**
- **Availability/Pricing:** Use property-scoped endpoint, connection_id is optional
- **Full:** Uses connection-scoped endpoint, connection_id is REQUIRED
- **Full sync** triggers orchestrated backend flow handling all sync types simultaneously
- **Connection ID vs Property ID:**
  - `connection_id` → channel_connections table (platform linkage UUID)
  - `property_id` → properties table (actual property UUID)
  - Full sync operates at connection level, not property level

---

### Features

The Channel Sync Admin UI provides:

1. **Trigger Sync Operations:**
   - Select sync type (availability, pricing, or full)
   - Select platform (airbnb, booking_com, expedia, fewo_direkt, google)
   - Select property from dropdown
   - Optional: Choose specific channel connection (REQUIRED for full sync)
   - Optional: Set custom date range (default: today → +90 days)
   - Full sync automatically resolves connection_id if platform + property selected

2. **View Sync Logs:**
   - Real-time table of recent sync operations
   - Columns: Status, Platform, Sync Type, Property, Error (if failed), Duration, Started At, Finished At
   - Status badges: triggered (blue), running (yellow), success (green), failed (red)
   - Click any row to view full log details in slide-in drawer
   - **Auto-load on Login:** Logs load automatically after login **if** a last-used connection ID exists in localStorage
     - Fast prefill: uses `localStorage.getItem("channelSync:lastConnectionId")` if present and valid
     - Badge indicator shows **"auto-detected"** (blue) when connection ID is prefilled from localStorage
     - If no last-used connection ID exists, logs panel shows: **"Enter Connection ID or use Auto-detect button above"**
   - **Explicit Auto-detect Button:** Appears when Connection ID field is empty
     - On click, fetches all connections from `/api/v1/channel-connections/?limit=100&offset=0`
     - **Smart Matching:** Filters connections by `platform_type` + `property_id` (if both Platform and Property are selected)
     - **If exactly 1 match:** Sets connection.id automatically and persists to localStorage
     - **If 0 matches:** Shows error message with platform and property info
     - **If multiple matches:** Shows modal selector with platform_type, property_id, platform_listing_id, status for user to choose
     - Shows loading state ("Detecting...") and error messages with HTTP status on failure
     - **Important:** Auto-detection sets the actual `connection.id` from the matched connection object, NOT the property_id
   - **Manual Entry:** Connection ID input field allows manual entry
     - Badge indicator shows **"manual"** (gray) when user manually edits the connection ID
     - Valid UUIDs are automatically persisted to localStorage for future sessions
   - **"Clear" button:** Removes connection ID, clears localStorage, and shows Auto-detect button again
     - Displays toast: "Connection ID cleared. Use Auto-detect or enter manually."
   - **Note:** Logs are fetched via `GET /api/v1/channel-connections/{connection_id}/sync-logs`
     - Connection ID must be a valid UUID format
     - Invalid connection ID shows helpful message instead of attempting fetch
     - After successful trigger, UI automatically retries fetch (0s, 1s, 2s, 3s) until new log appears

3. **Detail Drawer:**
   - Full log JSON with syntax highlighting
   - Copy individual fields to clipboard (task_id, sync_log_id, etc.)
   - View error messages and retry counts
   - View complete details JSONB payload
   - **Connection & Property IDs:** Shows both Connection ID (from log) and Property ID (from connection details)
   - **Null Timestamp Handling:** Started At / Finished At show "—" when null (instead of "01.01.1970")
   - **JSON Pretty-Printing:** Details drawer automatically detects and parses JSON-encoded strings (including double-escaped JSON) and renders them as pretty-printed JSON for readability
   - **Copy JSON** button copies the parsed, pretty-printed payload (not the raw escaped string)
   - **Duration Calculation:** Shows sync duration using `started_at`/`finished_at` timestamps (preferred) or falls back to `created_at`/`updated_at` if start/finish times are missing

4. **Filters & Search:**
   - **Status Filter:** All / Triggered / Running / Success / Failed / Active (triggered+running)
   - **Operation Type Filter:** All / availability_update / pricing_update / bookings_sync
   - **Direction Filter:** All / outbound / inbound
   - **Search Input:** Case-insensitive free-text search across all log fields:
     - IDs: batch_id, task_id, log_id, connection_id, property_id
     - Fields: operation_type, status, direction, error
     - Timestamps: created_at, updated_at
     - Placeholder: "Search logs…"
     - Clear button (✕) appears when search is active
     - Empty state: "No logs match your search." when no results
   - **Copy Buttons:** Click 📋 icons in table and drawer to copy IDs (Log ID, Connection ID, Property ID, Task ID, Batch ID) to clipboard
   - **Sorting:** Logs always sorted by created_at (newest first)
   - Filter buttons and search work together (both applied simultaneously)
   - Smart auto-refresh (only polls when active triggered/running logs exist)

5. **In-App Notifications:**
   - **Sync Trigger:** Inline green/red banner (auto-clears after 5s)
     - Success: "Sync gestartet: {sync_type}" with clickable batch_id
     - Error: "Fehler beim Starten (HTTP {status}): {detail}"
   - **Clipboard:** Browser-native alert for copy confirmations (unchanged)
   - **Success Message Fields:**
     - **Full Sync:** Displays "Batch ID: {uuid} (N tasks)" with copy buttons for batch_id and individual task_ids (first 3 shown, rest collapsed)
     - **Single Sync (Availability/Pricing):** Displays "Task ID: {uuid}" or "N tasks queued" depending on response format
     - No empty/undefined fields shown (dynamic display based on response shape)

6. **Troubleshooting Link:**
   - "Troubleshooting (Runbook)" link below Sync Logs title navigates directly to Ops Runbook tab (`/ops/runbook`)
   - Provides quick access to full operational documentation and runbook

7. **Duration Column:**
   - Shows elapsed time for each sync operation
   - Calculated from `started_at` → `finished_at` (preferred) or `created_at` → `updated_at` (fallback)
   - Format: `Xs` (seconds), `Ym Zs` (minutes/seconds), or `-` if timestamps unavailable
   - Active syncs (triggered/running) may show `-` until completion

8. **Safety Defaults (Form Validation):**
   - **Intentionally NO preselected values:** Sync Type, Platform, and Property fields start empty
   - **Trigger button disabled** until all required fields are selected
   - **Helper text displayed:** "ℹ️ Please select Sync Type, Platform, and Property to avoid triggering the wrong sync"
   - **Why:** Prevents accidental syncs against wrong platform/property due to overlooked defaults
   - **User must explicitly choose:**
     - Sync Type (Availability / Pricing / Full)
     - Platform (Airbnb / Booking.com / Expedia / FeWo-direkt / Google)
     - Property (from dropdown loaded from database)
   - **Connection ID:** Optional, can be auto-detected or manually entered after selecting platform + property
   - **Form remains disabled** until user makes conscious selection of each required field

9. **UX Behavior:**
   - **Trigger Sync Auto-loads Logs:** After clicking "Trigger Sync", logs automatically appear immediately
     - If Connection ID was not set, it gets set from the triggered sync's connection
     - Logs refresh automatically to show the new sync operation
     - Success panel shows batch_id/task_ids with copy buttons
   - **Auto-detect Only Sets Connection:** Clicking "Auto-detect" button:
     - Populates Connection ID field
     - Fetches and displays logs for that connection
     - Does NOT open the Sync Log Details modal
     - User must explicitly click a log row to view details
   - **Clearing Connection Resets UI:** Clicking "Clear" button:
     - Clears Connection ID field
     - Clears logs list (table becomes empty)
     - Closes Sync Log Details modal if open
     - Hides success panel (green banner)
     - Clears any error messages
     - Resets all filters and search state
   - **Success Panel Auto-dismiss:** Green success banner after triggering sync:
     - Includes dismiss button (×) in top-right corner
     - Auto-dismisses after 15 seconds
     - User can manually dismiss anytime by clicking ×
   - **Note:** Jobs can complete very quickly (< 1 second), so status may jump directly from "triggered" to "success" without showing "running" state

---

### Channel Sync safety defaults

**Intentionally NO preselected values:** The Channel Sync form starts with all fields empty (Sync Type, Platform, Property) to prevent accidental syncs.

**Trigger button disabled** until all required fields are selected, with helper text: "ℹ️ Please select Sync Type, Platform, and Property to avoid triggering the wrong sync"

**Why:** Prevents accidental syncs against wrong platform/property due to overlooked defaults. User must explicitly choose each field.

See: **Features → Safety Defaults (Form Validation)** for full details.

---

### Channel Sync Logs: lifecycle

**Status Progression:**
1. `triggered` (blue) - Sync queued in Celery
2. `running` (yellow) - Worker executing sync
3. `success` (green) - Sync completed successfully
4. `failed` (red) - Sync failed with error

**Important Notes:**
- Jobs can complete very quickly (< 1 second), so status may jump directly from "triggered" to "success" without showing "running" state
- Logs automatically refresh when active (triggered/running) logs exist
- Each log entry includes: status, platform, sync type, property, error (if failed), duration, timestamps
- Connection's `last_sync_at` field updates on trigger (immediate) and on success (completion)

See: **Features → View Sync Logs** and **Channel Connections: Last Sync Semantics** for full details.

---

### UX behavior

**Trigger Sync Auto-loads Logs:**
- After clicking "Trigger Sync", logs automatically appear immediately
- If Connection ID was not set, it gets set from the triggered sync's connection
- Success panel shows batch_id/task_ids with copy buttons

**Auto-detect Only Sets Connection:**
- Clicking "Auto-detect" button populates Connection ID and fetches logs
- Does NOT open the Sync Log Details modal
- User must explicitly click a log row to view details

**Clearing Connection Resets UI:**
- Clears Connection ID field and logs list
- Closes Sync Log Details modal if open
- Hides success panel and error messages
- **Clears all active toasts immediately** (no lingering success/error messages)
- Resets all filters and search state

**Toast Auto-dismiss Behavior:**
- **Channel Sync page:** Toasts auto-dismiss after 6 seconds
- **Connections page:** Notifications auto-dismiss after 10 seconds
- Green success banner (syncResult panel) auto-dismisses after 15 seconds
- All toasts include manual dismiss button (×)
- **Navigation cleanup:** Toasts and banners are cleared automatically when navigating away from page

See: **Features → UX Behavior** for full details.

---

### Sync Trigger Payload Architecture

**Important:** The sync page sends two distinct IDs to the API:

1. **property_id (REQUIRED):**
   - The actual property UUID from the "Property" dropdown
   - Always sent in POST `/api/v1/availability/sync` request body
   - Example: `"property_id": "6da0f8d2-677f-4182-a06c-db155f43704a"`

2. **connection_id (OPTIONAL):**
   - The channel connection UUID (auto-detected or user-entered)
   - Only sent if a connection is selected
   - Example: `"connection_id": "abc-123-def-456"`
   - Omitted from payload if empty

**Example Request Body:**
```json
{
  "sync_type": "availability",
  "platform": "booking_com",
  "property_id": "6da0f8d2-677f-4182-a06c-db155f43704a",
  "connection_id": "abc-123-def-456",
  "manual_trigger": true
}
```

**State Management:**
- UI maintains separate state variables: `propertyId` and `connectionId`
- After sync trigger, `connectionId` is NOT overwritten from API response
- This prevents confusion where API might return `property_id` in the response

**Property ID Display (No 404 Calls):**
- Sync page does NOT call `GET /api/v1/channel-connections/{id}` to fetch connection details
- Instead, uses cached connections list from auto-detect (`GET /api/v1/channel-connections/?limit=100&offset=0`)
- Property ID extracted from:
  1. Log details/metadata (`log.details.property_id`)
  2. Cached connections list (lookup by `connection_id`)
- This avoids 404 errors when connection_id is invalid or missing

**Trailing Slash Requirement:**
- List endpoint MUST use trailing slash before query params: `/api/v1/channel-connections/?limit=100`
- Without trailing slash: `/api/v1/channel-connections?limit=100` → 307 redirect → fails

**API Response Shape:**
- `GET /api/v1/channel-connections/` can return two formats:
  1. Direct array: `[{id, property_id, platform_type, ...}, ...]`
  2. Paginated object: `{items: [...], total: N, ...}`
- Frontend normalizes both: `const connections = Array.isArray(res) ? res : res.items ?? []`
- Prioritize `items` key if present, fallback to array check

**DevTools Verification:**
To verify sync trigger includes `connection_id`:
1. Open DevTools → Network tab
2. Select Platform + Property in Admin UI
3. Click "Trigger Sync"
4. Find POST request to `/api/v1/availability/sync`
5. Check Payload tab - should include:
   ```json
   {
     "sync_type": "availability",
     "platform": "booking_com",
     "property_id": "6da0f8d2-677f-4182-a06c-db155f43704a",
     "connection_id": "c1df8491-197a-4881-aec6-18e4297f5f79",
     "manual_trigger": true
   }
   ```
6. If `connection_id` is missing: cache not populated or no matching connection

**Auto-Resolution Logic:**
- On page load, Admin UI fetches `/api/v1/channel-connections/?limit=100` and caches results
- At sync trigger, if `connection_id` field is empty:
  - Searches cache for match: `platform_type === platform && property_id === propertyId`
  - If exactly 1 match: includes `connection.id` in payload automatically
  - If 0 or multiple matches: omits `connection_id` from payload

---

### API Response Shapes (Normalized)

**POST `/api/v1/channel-connections/{connection_id}/sync` Response:**

The sync trigger endpoint returns a consistent response shape with all required fields:

```json
{
  "status": "triggered",
  "message": "Manual full sync triggered successfully",
  "connection_id": "c1df8491-197a-4881-aec6-18e4297f5f79",
  "sync_type": "full",
  "task_ids": [
    "abc-123-task-1",
    "abc-123-task-2",
    "abc-123-task-3"
  ],
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_log_ids": [
    "log-uuid-1",
    "log-uuid-2",
    "log-uuid-3"
  ]
}
```

**Field Guarantees:**
- `status`: Always present (string: "triggered" or "error")
- `message`: Always present (human-readable description)
- `connection_id`: **Always present** (UUID, echoed from request)
- `sync_type`: **Always present** (string: "availability"|"pricing"|"bookings"|"full")
- `task_ids`: **Always array** (never single string, may be empty on error)
- `batch_id`: Nullable UUID (present for full sync, null for single-type syncs)
- `created_log_ids`: Nullable array of UUIDs (sync log entry IDs, null if creation failed)

**GET `/api/v1/channel-connections/{connection_id}/sync-logs` Response:**

The sync logs endpoint returns logs with normalized `details` field:

```json
{
  "connection_id": "c1df8491-197a-4881-aec6-18e4297f5f79",
  "logs": [
    {
      "id": "log-uuid-1",
      "connection_id": "c1df8491-197a-4881-aec6-18e4297f5f79",
      "operation_type": "availability_update",
      "direction": "outbound",
      "status": "success",
      "details": [
        "{\"sync_type\": \"full\", \"manual_trigger\": true}",
        "{\"property_id\": \"6da0f8d2-677f-4182-a06c-db155f43704a\"}"
      ],
      "error": null,
      "task_id": "abc-123-task-1",
      "batch_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2026-01-02T12:45:30.123456Z",
      "updated_at": "2026-01-02T12:45:35.654321Z"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

**Details Field Normalization:**

The `details` field is **always** an array of JSON-encoded strings:
- Database stores JSONB (dict/list/str/null)
- API normalizes on read to array[str] for consistent UI rendering
- Normalization rules:
  - `null` → `[]` (empty array)
  - `string` → `[string]` (wrap in array)
  - `dict` → `[json.dumps(dict)]` (serialize and wrap)
  - `list` → normalize each element to string (already in array format)

**Error Response Format:**

Endpoints return structured error responses with `error_code` and `hint`:

```json
{
  "detail": {
    "error": "not_found",
    "message": "Connection not found",
    "error_code": "NOT_FOUND",
    "hint": "Verify connection_id via GET /api/v1/channel-connections/?limit=100"
  }
}
```

**Common Error Codes:**
- `NOT_FOUND`: Resource not found (404)
- `SERVICE_UNAVAILABLE`: Database or external service unavailable (503)
- `INVALID_STATUS`: Invalid status parameter (400)
- `CONNECTION_INACTIVE`: Connection not active (health check failed)

---

### Channel Connections: Last Sync Semantics

**last_sync_at Persistence:**

The `last_sync_at` field in channel_connections is updated in TWO places:

1. **On Sync Trigger** (Immediate):
   - When manual sync is triggered via API (`POST /api/v1/availability/sync` or `POST /api/v1/channel-connections/{id}/sync`)
   - Sets `last_sync_at = NOW()` immediately when sync is queued
   - Updates `updated_at = NOW()` as well
   - Best-effort operation (logs warning if fails, doesn't block sync)

2. **On Sync Success** (Completion):
   - When Celery worker marks sync log as "success"
   - Sets `last_sync_at = NOW()` (finish time)
   - Updates `updated_at = NOW()` as well
   - Best-effort operation (logs warning if fails, doesn't affect task result)

**Why Two Updates?**
- First update: Shows sync was attempted (user sees "Last Sync: moments ago" in UI)
- Second update: Confirms sync completed successfully (reflects actual sync finish time)
- If worker crashes, first timestamp remains (shows attempted, not succeeded)

**Debugging Last Sync:**

Check connection's `last_sync_at` via API:
```bash
# List all connections with last_sync_at
curl -X GET "$API/api/v1/channel-connections/?limit=100" \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | {id, platform_type, property_id, last_sync_at, updated_at}'

# Expected output:
# {
#   "id": "c1df8491-197a-4881-aec6-18e4297f5f79",
#   "platform_type": "booking_com",
#   "property_id": "6da0f8d2-677f-4182-a06c-db155f43704a",
#   "last_sync_at": "2026-01-02T12:45:30.123456Z",  # <-- Should be non-null after sync
#   "updated_at": "2026-01-02T12:45:30.123456Z"
# }
```

Check directly in database (optional):
```sql
-- Connect to Supabase/Postgres
SELECT id, platform_type, property_id, last_sync_at, updated_at
FROM channel_connections
WHERE deleted_at IS NULL
ORDER BY updated_at DESC LIMIT 10;
```

**Troubleshooting:**

If `last_sync_at` remains `null` after running sync:
1. Check worker logs for warnings: `grep "Failed to touch connection" worker.log`
2. Verify database permissions (UPDATE on channel_connections table)
3. Verify connection_id is valid UUID (not property_id mistakenly)
4. Check if connection was soft-deleted (`deleted_at IS NOT NULL`)

If last_sync_at shows trigger time but not finish time:
- Worker may have crashed before updating (check Celery worker status)
- Check sync logs for task status: `GET /api/v1/channel-connections/{id}/sync-logs`

---

### Log Retention & Purge Policy

**Default Retention Policy:** 30 days (recommended)

**Admin-Only Purge Feature:**
- **Admin UI**: "Purge logs" button in `/channel-sync` page
- **API Endpoint**: `POST /api/v1/channel-connections/{connection_id}/sync-logs/purge`
- **Access**: Admin role only (403 for non-admins)
- **Safety**: Requires typing "PURGE" to confirm (irreversible deletion)

**Retention Options:**
- 7 days: Short-term cleanup for testing/debugging
- 30 days: Recommended default for production
- 90 days: Extended retention for audit/compliance

**How to Purge Logs (Admin UI):**

1. **Navigate to Channel Sync:**
   - Go to: `https://admin.fewo.kolibri-visions.de/channel-sync`
   - Select connection ID (auto-detect or manual entry)

2. **Click "Purge logs" button** (upper right, next to Refresh)
   - Only visible when valid connection ID is set
   - Disabled for non-admin users

3. **Configure Purge:**
   - Select retention period: 7 / 30 / 90 days
   - Type `PURGE` in confirmation field (case-sensitive)
   - Click "Purge Logs" button

4. **Verify Result:**
   - Success toast shows number of deleted logs
   - Logs table refreshes automatically
   - Purge is immediate and irreversible

**How to Purge Logs (curl):**

See [scripts/README.md - Purge Sync Logs](#) for curl examples.

```bash
# Example: Purge logs older than 30 days
curl -X POST "$API/api/v1/channel-connections/$CID/sync-logs/purge" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "retention_days": 30,
    "confirm_phrase": "PURGE"
  }'

# Expected response (200):
# {
#   "connection_id": "abc-123...",
#   "retention_days": 30,
#   "cutoff": "2025-01-01T12:00:00Z",
#   "deleted_count": 42
# }
```

**Error Responses:**
- **400**: Invalid confirm_phrase (must be exactly "PURGE")
- **401**: Not authenticated (missing/invalid token)
- **403**: Forbidden (not an admin)
- **422**: Invalid retention_days (must be 1-3650)

**Purge Preview (Safety Feature):**
- **Before Deletion**: Modal shows preview count ("Will delete: X logs")
- **Scope Display**: Clearly shows "This connection only" with connection ID
- **Real-time Update**: Preview refreshes when retention period changes (7/30/90 days)
- **Safe Decision**: User sees exactly how many logs will be deleted before confirming
- **Loading State**: Shows "Loading..." while fetching preview count
- **Error Handling**: Displays error if preview fails (doesn't block purge if needed)

**Safety Notes:**
- **Irreversible**: Deleted logs cannot be recovered
- **Scoped**: Only deletes logs for specified connection_id (not global)
- **Preview First**: Always shows count before deletion (requires connection ID)
- **Audit Trail**: Lost after purge — export logs before purging if needed for compliance
- **No Automatic Purge**: Manual trigger only (no cron/scheduled purge)

---

### How to Access

1. **Login to Admin UI:**
   - Navigate to: `https://admin.fewo.kolibri-visions.de`
   - Login with admin or manager credentials

2. **Navigate to Channel Sync:**
   - Click "Channel Sync" in sidebar navigation
   - Or directly: `https://admin.fewo.kolibri-visions.de/channel-sync`

---

### How to Trigger a Sync

1. **Fill out the Trigger Form:**
   - **Sync Type:** Select "availability" or "pricing"
   - **Platform:** Select target booking platform
   - **Property:** Select property from dropdown (auto-fetched from `/api/v1/properties`)
   - **Connection (Optional):** Select specific connection if needed
   - **Date Range (Optional):** Defaults to today → +90 days

2. **Click "Trigger Sync"**
   - Request sent to `POST /api/availability/sync`
   - Success toast shows task_id and sync_log_id
   - UI automatically fetches logs with retry (up to 4 attempts: 0s, 1s, 2s, 3s)
   - New log appears at top of sync logs table and detail drawer opens automatically
   - Status starts as "triggered", transitions to "running" → "success" or "failed"
   - If log doesn't appear after retries, click Refresh button manually

3. **Monitor Progress:**
   - Watch status badge change in real-time
   - Duration updates when log completes
   - Click row to view full details

---

### Interpreting Sync Statuses

| Status | Badge Color | Meaning | Next Action |
|--------|-------------|---------|-------------|
| **triggered** | Blue | Sync task queued in Celery | Wait for worker to pick up task |
| **running** | Yellow | Worker actively processing sync | Wait for completion (usually < 30s) |
| **success** | Green | Sync completed successfully | No action needed |
| **failed** | Red | Sync failed with error | Click row → view error → troubleshoot |

**Duration Calculation:**
- Shows time from `started_at` to `finished_at`
- Only visible after log completes (status = success/failed)
- Format: `XXXms` (if < 1s) or `X.Xs` (if ≥ 1s)

---

### Troubleshooting Common Issues

#### 1. Validation Errors (422) — No Sync Log Created

**Symptom:**
- Trigger button disabled or form shows red field errors
- Yellow banner: "Validation failed — fix highlighted fields"
- No sync log appears in table

**Cause:**
- **Client-side validation failed:**
  - Connection ID is not a valid UUID format
  - End date is before start date
- **Server-side validation failed (422):**
  - Invalid field values sent to API
  - Missing required fields

**Why No Log Appears:**
- **422 validation errors mean the request was rejected before queuing**
- The sync task was never created, so no log entry exists in `channel_sync_logs` table
- Only successfully triggered syncs (status 200) create log entries

**Fix:**
1. **Check field-level error messages** under each input (red text)
2. **Fix highlighted fields:**
   - Connection ID must be valid UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
   - End date must be on or after start date
3. **Trigger button will re-enable** once validation passes
4. **After fixing:** Click "Trigger Sync" again

**Note:** Client-side validation now prevents most 422 errors before API call. If you still see 422 from the server, check the field error messages for details.

---

#### 2. Trigger Button Disabled or "No properties available"

**Symptom:**
- Trigger form shows "No properties available"
- Property dropdown is empty

**Cause:**
- GET `/api/v1/properties` returned empty array or failed
- User's agency has no properties created yet
- RLS policies preventing property access

**Fix:**
```bash
# Check if properties exist for this user
curl -X GET https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Authorization: Bearer YOUR_JWT" | jq '.properties'

# Expected: Array with at least one property
# If empty: Create a property first or check RLS policies
```

---

#### 3. Sync Triggered but Logs Stay "triggered" Forever

**Symptom:**
- POST `/api/availability/sync` returns 200 with task_id
- Sync log appears in table with status "triggered"
- Status never transitions to "running" or "success/failed"

**Cause:**
- Celery worker not running or not connected to Redis broker
- Worker crashed or stuck in infinite loop
- Worker old version (code drift)

**Fix:**
```bash
# SSH to host server
ssh root@your-host

# Check if pms-worker-v2 is running
docker ps | grep pms-worker

# Check worker logs for errors
docker logs --tail 100 pms-worker-v2

# Ping Celery workers from backend
docker exec pms-backend \
  celery -A app.channel_manager.core.sync_engine:celery_app \
  --broker "$CELERY_BROKER_URL" inspect ping -t 3

# Expected: -> celery@pms-worker-v2-...: {'ok': 'pong'}
# If timeout: Worker not connected to Redis

# Restart worker
docker restart pms-worker-v2
```

**See Also:** [Celery Worker Troubleshooting](#celery-worker-pms-worker-v2-start-verify-troubleshoot)

---

#### 4. 401 Unauthorized (Token Expired)

**Symptom:**
- UI shows error toast: "Unauthorized" or "Token expired"
- Trigger sync fails with 401
- Sync logs fail to load

**Cause:**
- JWT token expired (tokens expire after 1 hour by default)
- User session invalidated

**Fix:**
1. **Logout and Login Again:**
   - Click logout in Admin UI
   - Login with credentials again
   - Token will be refreshed

2. **Manual Token Refresh (for testing):**
   ```bash
   # Fetch new token via Supabase auth
   curl -X POST "https://your-project.supabase.co/auth/v1/token?grant_type=password" \
     -H "apikey: YOUR_ANON_KEY" \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"your-password"}' \
     | jq -r '.access_token'
   ```

---

#### 5. 503 Service Unavailable (Database Temporarily Unavailable)

**Symptom:**
- UI shows error toast: "Service temporarily unavailable"
- API returns 503 with message "Database is temporarily unavailable"

**Cause:**
- Backend container lost connection to Supabase database
- Supabase network attachment dropped during redeploy
- Database DNS resolution failed

**Fix:**

See: [DB DNS / Degraded Mode](#db-dns--degraded-mode)

**Quick check:**
```bash
# SSH to host
ssh root@your-host

# Check if backend can resolve supabase-db
docker exec pms-backend getent hosts supabase-db

# Expected: IP address (e.g., 172.20.0.2)
# If empty: DNS resolution failed → reattach network

# Reattach Supabase network
docker network connect bccg4gs4o4kgsowocw08wkw4 pms-backend
docker restart pms-backend
```

---

#### 6. Sync Logs Table Empty or Stale

**Symptom:**
- Sync logs table shows "No sync logs found"
- OR logs are stale (not updating after triggering sync)

**Cause A:** No syncs triggered yet
- **Fix:** Trigger a sync first

**Cause B:** GET `/api/v1/channel-connections/{id}/sync-logs` failed silently
- **Fix:** Open browser console (F12) → check for API errors

**Cause C:** Database migration not applied (`channel_sync_logs` table missing)
- **Symptom:** API returns 503 with message "Channel sync logs schema not installed"
- **Fix:** Apply migration: `supabase/migrations/20251227000000_create_channel_sync_logs.sql`

```bash
# Check if table exists
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  -c "\dt channel_sync_logs"

# Expected: Table listing
# If not found: Apply migration (see "Channel Manager Sync Logs Migration" section)
```

---

#### 7. Admin UI Shows "Failed to fetch connections" (Mixed Content)

**Symptom:**
- Browser console shows: `Mixed Content: The page at 'https://admin...' was loaded over HTTPS, but requested an insecure resource 'http://api...'.`
- Connections page shows "Failed to fetch connections" error
- Auto-detect fails to load connections
- Error message: "Failed to auto-detect connection ID (TypeError: Failed to fetch)"

**Cause:**
- Frontend environment variable `NEXT_PUBLIC_API_BASE` set to HTTP instead of HTTPS
- API endpoint without trailing slash triggers FastAPI 307 redirect
- Redirect downgrades from HTTPS to HTTP (proxy/load balancer issue)
- Browser blocks the HTTP request as Mixed Content

**Fix 1: Set Frontend API Base to HTTPS**

Ensure `NEXT_PUBLIC_API_BASE` uses HTTPS in deployment environment:

```bash
# In Coolify/deployment environment variables
NEXT_PUBLIC_API_BASE=https://api.fewo.kolibri-visions.de
```

**Fix 2: Automatic HTTPS Upgrade (Built-in Protection)**

The frontend now automatically upgrades HTTP to HTTPS when:
- Frontend loaded via HTTPS (`window.location.protocol === 'https:'`)
- API base URL starts with `http://`
- Console warning appears: `[api-client] Upgrading HTTP API base to HTTPS to avoid mixed content`

This prevents mixed content errors even if `NEXT_PUBLIC_API_BASE` is misconfigured.

**Fix 3: Redeploy Frontend**

If the issue persists after setting env var:

1. **Redeploy frontend** to rebuild with new environment variable
2. **Clear browser cache** and hard reload (Ctrl+Shift+R / Cmd+Shift+R)
3. **Verify API base URL** in browser console: should be `https://api...` (not `http://`)
4. **Check proxy/load balancer config** if the issue persists (ensure HTTPS forwarding is correct)

**Technical Note:**
- ✅ Correct: `GET /api/v1/channel-connections/?limit=50` (with trailing slash, HTTPS)
- ❌ Causes redirect: `GET /api/v1/channel-connections?limit=50` (no trailing slash)
- ❌ Blocked by browser: `GET http://api...` (HTTP from HTTPS page)

---

#### 8. Redirect Location is http:// (Mixed Content from Backend)

**Symptom:**
- Browser console shows: `Mixed Content: ... requested an insecure resource 'http://api...'.`
- API redirect (307) uses `http://` instead of `https://` in Location header
- Request to `https://api.../channel-connections?limit=1` redirects to `http://api.../channel-connections/?limit=1`

**Cause:**
- FastAPI/Starlette generates redirect without trusting X-Forwarded-Proto header
- Reverse proxy (Traefik/Coolify) sets `X-Forwarded-Proto: https` but backend ignores it
- Backend sees scheme=http from internal connection, builds http:// redirect Location
- Browser blocks the HTTP redirect as mixed content

**Verification:**
```bash
# Test redirect Location header
curl -k -sS -D - -o /dev/null "https://api.fewo.kolibri-visions.de/api/v1/channel-connections?limit=1&offset=0" | sed -n '1,30p'

# Expected BEFORE fix: location: http://api.fewo.kolibri-visions.de/...
# Expected AFTER fix:  location: https://api.fewo.kolibri-visions.de/...
```

**Fix: Enable Proxy Header Trust**

The backend now trusts X-Forwarded-Proto by default via `ForwardedProtoMiddleware`.

**Environment Variable (Backend):**
```bash
# Default: true (recommended for production behind reverse proxy)
TRUST_PROXY_HEADERS=true
```

**How It Works:**
1. Middleware reads `X-Forwarded-Proto` header from Traefik/Nginx
2. Sets `scope["scheme"]` to "https" (instead of "http")
3. FastAPI redirect Location header uses https://
4. Browser accepts redirect (no mixed content error)

**Startup Log Verification:**
```bash
# Check backend logs for middleware initialization
docker logs pms-backend --tail 50 | grep TRUST_PROXY_HEADERS

# Expected output:
# TRUST_PROXY_HEADERS=true → trusting X-Forwarded-Proto for scheme
```

**Disable (Not Recommended):**
```bash
# Only disable if NOT behind reverse proxy (direct HTTPS termination)
TRUST_PROXY_HEADERS=false
```

**Related:**
- Frontend already upgrades HTTP to HTTPS (automatic protection)
- Backend middleware ensures redirects stay HTTPS
- Both protections work together for complete mixed-content prevention

---

#### 9. Connections Last Sync shows "Never" (NULL last_sync_at)

**Symptom:**
- Admin UI Connections page shows "Last Sync: Never" despite successful sync logs existing
- `channel_connections.last_sync_at` column remains NULL in database
- Sync logs exist with `status='success'` but connection timestamp not updated

**Causes:**

**A. Sync log updates not triggering connection touch**
- Worker successfully completes sync task but `update_log_by_task_id` not called
- Log status updated manually/directly without using service layer
- Worker crashed before calling update method

**B. Auto-update logic not running (code version mismatch)**
- Deployed code doesn't include auto-update logic in `update_log_by_task_id`
- Service layer bypassed (direct SQL UPDATE on channel_sync_logs)

**C. Database permissions issue**
- Worker has SELECT on `channel_sync_logs` but not UPDATE on `channel_connections`
- RLS policy blocks UPDATE on `channel_connections` for service role

**D. Connection deleted or soft-deleted**
- `channel_connections.deleted_at IS NOT NULL` blocks update
- Connection ID from log doesn't match any active connection

**Verification:**

```bash
# 1. Check if sync logs exist with status=success
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres -c "
  SELECT id, connection_id, operation_type, status, created_at, updated_at
  FROM channel_sync_logs
  WHERE status = 'success'
  ORDER BY updated_at DESC
  LIMIT 5;
"

# 2. Check if corresponding connections have NULL last_sync_at
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres -c "
  SELECT c.id, c.platform_type, c.last_sync_at, c.updated_at, c.deleted_at
  FROM channel_connections c
  WHERE c.id IN (
    SELECT DISTINCT connection_id
    FROM channel_sync_logs
    WHERE status = 'success'
  )
  ORDER BY c.updated_at DESC
  LIMIT 5;
"

# Expected: last_sync_at should NOT be NULL if success logs exist

# 3. Check tenant_id in sync logs (should not be NULL)
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres -c "
  SELECT connection_id, tenant_id, COUNT(*) as log_count
  FROM channel_sync_logs
  GROUP BY connection_id, tenant_id
  ORDER BY log_count DESC
  LIMIT 10;
"

# Expected: tenant_id should match connection's agency_id (not NULL)
```

**Fix 1: Manual Backfill (Immediate Fix)**

If production connections have NULL `last_sync_at` but success logs exist, backfill from logs:

```sql
-- Backfill last_sync_at from most recent successful sync log
UPDATE channel_connections c
SET
  last_sync_at = (
    SELECT MAX(updated_at)
    FROM channel_sync_logs
    WHERE connection_id = c.id
      AND status = 'success'
  ),
  updated_at = NOW()
WHERE c.deleted_at IS NULL
  AND c.last_sync_at IS NULL
  AND EXISTS (
    SELECT 1
    FROM channel_sync_logs
    WHERE connection_id = c.id
      AND status = 'success'
  );

-- Verify backfill
SELECT id, platform_type, last_sync_at, updated_at
FROM channel_connections
WHERE deleted_at IS NULL
  AND last_sync_at IS NOT NULL
ORDER BY last_sync_at DESC
LIMIT 10;
```

**Fix 2: Verify Code Deployment**

Ensure latest code with auto-update logic is deployed:

```bash
# Check deployed commit hash
docker exec pms-backend env | grep SOURCE_COMMIT

# Expected: Latest commit with auto-update logic
# Commit should include:
# - channel_sync_log_service.py: update_log_by_task_id updates connection.last_sync_at on success
# - channel_connection_service.py: list_connections has COALESCE fallback for last_sync_at

# Check backend logs for auto-update messages
docker logs pms-backend --tail 100 | grep "Updated connection.*last_sync_at"

# Expected on successful sync:
# "Updated connection <uuid> last_sync_at due to log <log_id> transitioning to success"
```

**Fix 3: Redeploy Backend + Worker**

If code is out of date:

```bash
# 1. Pull latest main
git checkout main
git pull origin main

# 2. Verify changes
git log --oneline --grep="last_sync_at" -5

# 3. Redeploy via Coolify
# Navigate to Coolify Dashboard → pms-backend → Redeploy
# Navigate to Coolify Dashboard → pms-worker-v2 → Redeploy

# 4. Wait for containers to restart (30-60s)

# 5. Verify deployment
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | grep -E 'pms-backend|pms-worker'

# 6. Trigger test sync and verify last_sync_at updates
```

**Fix 4: Check Database Permissions**

Verify service role can UPDATE channel_connections:

```sql
-- Test UPDATE as service role (anon JWT)
BEGIN;

UPDATE channel_connections
SET last_sync_at = NOW(), updated_at = NOW()
WHERE id = '<test-connection-uuid>'
  AND deleted_at IS NULL;

-- If ERROR: Check RLS policies
SELECT tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename = 'channel_connections'
  AND cmd = 'UPDATE';

ROLLBACK;
```

**Expected Behavior (After Fix):**

1. When sync log transitions to `status='success'`:
   - Service calls `update_log_by_task_id(task_id, status='success')`
   - Service updates log row in `channel_sync_logs`
   - Service automatically updates `channel_connections.last_sync_at = NOW()`
   - Backend logs: "Updated connection <uuid> last_sync_at due to log <log_id> transitioning to success"

2. When `list_connections` is called:
   - If `channel_connections.last_sync_at IS NULL`:
     - Query uses COALESCE to fallback to `MAX(updated_at) FROM channel_sync_logs WHERE status='success'`
     - API returns computed timestamp (not NULL)
   - If `channel_connections.last_sync_at IS NOT NULL`:
     - Query returns actual column value

3. Admin UI Connections page shows accurate "Last Sync" timestamp

**Related Sections:**
- [Admin UI - Channel Sync](#admin-ui---channel-sync)
- [Sync Logs Persistence](#sync-logs-persistence)
- [Channel Manager Error Handling & Retry Logic](#channel-manager-error-handling--retry-logic)

---

## Verify Connection last_sync_at (E2E)

**Purpose:** End-to-end verification that `last_sync_at` updates correctly after sync operations complete successfully. This guide helps new team members verify the feature without stumbling over redirects, token expiration, or SQL column name errors.

**When to Use:**
- After deploying last_sync_at auto-update logic
- When troubleshooting "Last Sync: Never" issues
- During onboarding to verify sync persistence works correctly

**Quick Smoke Test:**
For automated API-level verification, use the smoke test script:
```bash
source /root/pms_env.sh
export TOKEN=$(curl -X POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -H "apikey: $SB_ANON_KEY" \
  -d '{"email":"admin@example.com","password":"your-password"}' \
  | jq -r '.access_token')
bash backend/scripts/pms_channel_last_sync_smoke.sh
```
See [pms_channel_last_sync_smoke.sh](../../scripts/README.md#pms_channel_last_sync_smokesh) for details.

---

### 1. Admin UI Verification (Browser)

**Navigate to Connections page:**
```
https://admin.fewo.kolibri-visions.de/connections
```

**Verification Steps:**

1. **Check Connections Table:**
   - Locate your test connections (booking_com, airbnb, etc.)
   - Verify "Last Sync" column shows actual timestamps (not "Never")
   - If "Never" is shown, trigger a sync and verify it updates after completion

2. **Trigger Sync via Sync Page:**
   - Navigate to Channel Sync page: `https://admin.fewo.kolibri-visions.de/channel-sync`
   - Select platform and property
   - Use "Auto-detect" button if Connection ID is empty (matches platform + property)
   - Trigger any sync type (Availability, Pricing, or Full)
   - Wait for success message with batch_id or task_id

3. **Verify Connection Summary:**
   - On Sync page, scroll to "Connection Summary" section
   - Verify "Last Sync" shows updated timestamp (within last few minutes)
   - Compare with Connections table to ensure consistency

**Expected Result:**
- Last Sync timestamp updates after successful sync completion
- Timestamp reflects when the sync log transitioned to `status='success'`
- Both Connections page and Sync page show consistent timestamps

---

### 2. API Verification (curl)

**Prerequisites:**
```bash
# Load environment variables
source /root/pms_env.sh

# Verify variables are set
echo $SB_URL  # Should not be empty
echo $API     # Should be https://api.fewo.kolibri-visions.de

# Get fresh JWT token
TOKEN=$(curl -X POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -H "apikey: $SB_ANON_KEY" \
  -d '{"email":"admin@example.com","password":"your-password"}' \
  | jq -r '.access_token')

# Verify token is set
echo $TOKEN
```

**Verification Query:**

⚠️ **IMPORTANT:** The list endpoint requires trailing slash to avoid 307/308 redirects.

```bash
# Method 1: Use trailing slash (RECOMMENDED)
curl -s "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/?limit=100&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nHTTP Status: %{http_code}\n" \
  -o /tmp/cc_body.json

# Method 2: Use -L to follow redirects (alternative)
curl -sL "https://api.fewo.kolibri-visions.de/api/v1/channel-connections?limit=100&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -w "\nHTTP Status: %{http_code}\n" \
  -o /tmp/cc_body.json

# Check HTTP status (should be 200)
cat /tmp/cc_body.json | head -c 100  # Verify body is not empty

# Parse last_sync_at for booking_com connections
jq '.[] | select(.platform_type == "booking_com") | {id, platform_type, property_id, last_sync_at, updated_at}' /tmp/cc_body.json

# Parse last_sync_at for airbnb connections
jq '.[] | select(.platform_type == "airbnb") | {id, platform_type, property_id, last_sync_at, updated_at}' /tmp/cc_body.json

# Filter connections with NULL last_sync_at (should be empty after syncs)
jq '.[] | select(.last_sync_at == null) | {id, platform_type, property_id, status}' /tmp/cc_body.json
```

**Expected Output:**
```json
{
  "id": "abc-123-def-456",
  "platform_type": "booking_com",
  "property_id": "property-uuid",
  "last_sync_at": "2026-01-03T14:30:00.123456Z",
  "updated_at": "2026-01-03T14:30:00.123456Z"
}
```

**Troubleshooting:**
- **Empty body with 307/308 status:** Missing trailing slash → use `/api/v1/channel-connections/` (with slash) or add `-L` flag
- **401 "Token has expired":** Fetch new token using `$SB_URL/auth/v1/token` endpoint (see Prerequisites)
- **Empty `$SB_URL` variable:** Run `source /root/pms_env.sh` first (env vars not loaded in fresh shells)
- **JSONDecodeError:** Usually means empty body (redirect or auth failure) → check HTTP status code first

---

### 3. Database Verification (Supabase SQL Editor)

**Navigate to Supabase SQL Editor:**
```
https://supabase.com/dashboard/project/<project-id>/sql/new
```

**Query 1: Check channel_connections.last_sync_at**

```sql
-- List all connections with last_sync_at timestamps
SELECT
  id,
  platform_type,
  property_id,
  status,
  last_sync_at,
  updated_at,
  created_at
FROM public.channel_connections
WHERE deleted_at IS NULL
ORDER BY updated_at DESC
LIMIT 20;
```

**Expected Result:**
- `last_sync_at` should NOT be NULL for connections that have completed successful syncs
- Timestamp should match recent sync completions (within reasonable time window)

**Query 2: Check channel_sync_logs for specific connection**

⚠️ **IMPORTANT:** Column is `operation_type` (NOT `operation`)

```sql
-- List recent sync logs for a connection
SELECT
  id,
  connection_id,
  operation_type,    -- CORRECT column name (not "operation")
  direction,
  status,
  error,
  task_id,
  batch_id,
  tenant_id,
  created_at,
  updated_at
FROM public.channel_sync_logs
WHERE connection_id = '<CONNECTION-UUID-HERE>'
ORDER BY created_at DESC
LIMIT 20;
```

**Expected Result:**
- Successful syncs show `status = 'success'`
- `operation_type` values: `availability_update`, `pricing_update`, `bookings_sync`
- `tenant_id` should NOT be NULL (matches connection's `agency_id`)

**Query 3: Cross-check last_sync_at vs most recent success log**

```sql
-- Verify last_sync_at matches most recent successful sync
SELECT
  c.id AS connection_id,
  c.platform_type,
  c.last_sync_at AS connection_last_sync,
  MAX(l.updated_at) AS latest_success_log,
  CASE
    WHEN c.last_sync_at IS NULL AND MAX(l.updated_at) IS NOT NULL
      THEN 'MISMATCH: connection NULL but logs exist'
    WHEN c.last_sync_at < MAX(l.updated_at)
      THEN 'STALE: connection older than latest log'
    WHEN c.last_sync_at >= MAX(l.updated_at)
      THEN 'OK'
    ELSE 'UNKNOWN'
  END AS sync_status
FROM public.channel_connections c
LEFT JOIN public.channel_sync_logs l
  ON l.connection_id = c.id AND l.status = 'success'
WHERE c.deleted_at IS NULL
GROUP BY c.id, c.platform_type, c.last_sync_at
ORDER BY c.updated_at DESC
LIMIT 20;
```

**Expected Result:**
- `sync_status` should be `'OK'` for all connections with recent syncs
- No `'MISMATCH'` entries (indicates auto-update logic not running)
- No `'STALE'` entries (indicates connection not updated on log success)

---

### 4. Troubleshooting Quick Reference

**Issue: "Token has expired" (401)**
```bash
# Fix: Refresh JWT token
source /root/pms_env.sh  # Load env vars first
TOKEN=$(curl -X POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -H "apikey: $SB_ANON_KEY" \
  -d '{"email":"admin@example.com","password":"your-password"}' \
  | jq -r '.access_token')
```

**Issue: JSONDecodeError or empty response**
```bash
# Root cause: Usually redirect (307/308) or auth failure
# Fix 1: Check HTTP status code
curl -I "https://api.fewo.kolibri-visions.de/api/v1/channel-connections?limit=5"
# If 307/308: Add trailing slash OR use -L flag

# Fix 2: Check response body size
curl -s "..." -w "\nBody size: %{size_download} bytes\n" | head -c 200
# If 0 bytes: Auth failure or redirect issue
```

**Issue: Wrong SQL column name**
```sql
-- ❌ WRONG (column doesn't exist)
SELECT operation FROM channel_sync_logs;

-- ✅ CORRECT
SELECT operation_type FROM channel_sync_logs;
```

**Issue: Empty `$SB_URL` or `$SB_ANON_KEY`**
```bash
# Root cause: Environment variables not loaded in fresh SSH session
# Fix: Always source env file first
source /root/pms_env.sh

# Verify
echo $SB_URL       # Should show Supabase URL
echo $SB_ANON_KEY  # Should show anon key
```

**Issue: Admin UI shows "Never" despite successful logs**
- See [Connections Last Sync shows "Never"](#9-connections-last-sync-shows-never-null-last_sync_at) for full troubleshooting steps
- Quick fix: Run manual backfill SQL (see section above)
- Permanent fix: Verify auto-update logic deployed (check commit hash)

---

### Environment Variables

**Frontend (`pms-admin`):**
- `NEXT_PUBLIC_API_BASE`: API base URL (default: `https://api.fewo.kolibri-visions.de`)
  - Used for all API calls: `/api/v1/properties`, `/api/availability/sync`, `/api/v1/channel-connections/*/sync-logs`

**Backend (`pms-backend`):**
- `DATABASE_URL`: PostgreSQL connection string (must include `channel_sync_logs` table)
- `JWT_SECRET`: JWT signing key (must match frontend auth)

---

### Monitoring & Logging

**Frontend Logs:**
- Browser console (F12) shows API request/response
- Inline banner notifications show sync trigger success/error (auto-clears after 5s)

**Backend Logs:**
- Coolify Dashboard → pms-backend → Logs
- Shows incoming POST `/api/availability/sync` requests
- Shows Celery task dispatch

**Worker Logs:**
- Coolify Dashboard → pms-worker-v2 → Logs
- Shows task execution (received → started → success/failed)
- Shows retry attempts and exponential backoff

**Database Logs:**
- Query `channel_sync_logs` table directly:
  ```sql
  SELECT id, operation_type, status, error, created_at, updated_at
  FROM channel_sync_logs
  ORDER BY created_at DESC
  LIMIT 50;
  ```

---

### Smart Auto-Refresh Behavior

The Admin UI uses **conditional polling** to reduce unnecessary API calls:

- **Polls every 5 seconds** ONLY when there are active logs (status = "triggered" or "running")
- **Stops polling** when all logs are in terminal state (success/failed)
- **Resumes polling** when user triggers a new sync

This ensures:
- Real-time updates for active syncs
- Minimal backend load when idle
- No browser tab wake-up spam

---

### Known Limitations

1. **No Bulk Sync:**
   - UI only supports triggering one sync at a time
   - For bulk operations, use API directly or create custom script

2. **No Cancel Operation:**
   - Once triggered, sync cannot be cancelled from UI
   - Must wait for completion or manually kill Celery task

3. **Log Pagination:**
   - Currently loads all sync logs (no pagination in UI)
   - For large log history, use API with `limit`/`offset` parameters

4. **No Real-Time WebSocket:**
   - Uses HTTP polling (not WebSocket)
   - 5-second refresh interval may show delayed status updates

---

### Related Sections

- [Channel Manager API Endpoints](#channel-manager-api-endpoints) - API documentation
- [Sync Logs Persistence](#sync-logs-persistence) - Database schema
- [Celery Worker Troubleshooting](#celery-worker-pms-worker-v2-start-verify-troubleshoot) - Worker issues
- [DB DNS / Degraded Mode](#db-dns--degraded-mode) - Database connectivity

---

## Sync Logs Persistence

**Purpose:** Understand how sync operations are tracked in the database.

### Database Table: `channel_sync_logs`

**Schema:**
```sql
CREATE TABLE public.channel_sync_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NULL,
  connection_id uuid NOT NULL,
  operation_type text NOT NULL CHECK (operation_type IN (
    'full_sync', 'availability_update', 'pricing_update',
    'bookings_import', 'calendar_sync', 'listing_update'
  )),
  direction text NOT NULL DEFAULT 'outbound' CHECK (direction IN ('outbound', 'inbound')),
  status text NOT NULL CHECK (status IN (
    'triggered', 'queued', 'running', 'success', 'failed', 'cancelled'
  )),
  details jsonb NULL,
  error text NULL,
  task_id text NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NULL
);
```

**Indexes:**
- `(connection_id, created_at DESC)` - Fast queries by connection
- `(task_id)` - Fast updates by Celery task ID
- `(tenant_id, created_at DESC)` - Multi-tenant queries
- `(status, created_at DESC)` - Filter by status

---

### Logged Information

**Mandatory Fields:**
- `id`: Unique log entry UUID
- `connection_id`: Channel connection or property UUID
- `operation_type`: Type of sync operation
- `direction`: "outbound" (PMS → Channel) or "inbound" (Channel → PMS)
- `status`: Current status (triggered/queued/running/success/failed/cancelled)
- `created_at`: When log entry was created

**Optional Fields:**
- `tenant_id`: Agency UUID (for multi-tenant filtering)
- `task_id`: Celery task UUID (for async tracking)
- `error`: Error message (if status=failed)
- `updated_at`: Last status update timestamp

**JSONB Details Field:**

Flexible metadata storage, varies by operation:

**Availability Sync:**
```json
{
  "platform": "airbnb",
  "property_id": "uuid",
  "manual_trigger": true,
  "start_date": "2025-12-28",
  "end_date": "2026-03-28",
  "check_in": "2025-12-28",
  "check_out": "2025-12-30",
  "available": true,
  "retry_count": 0,
  "next_retry_seconds": null
}
```

**Pricing Sync:**
```json
{
  "platform": "booking_com",
  "property_id": "uuid",
  "manual_trigger": false,
  "check_in": "2025-12-28",
  "check_out": "2025-12-30",
  "nightly_rate": 150.00,
  "currency": "EUR"
}
```

**During Retry:**
```json
{
  "retry_count": 2,
  "error_type": "database_unavailable",
  "next_retry_seconds": 4
}
```

---

### Status Lifecycle

```
triggered → running → success
                   ↘ failed
                   ↘ cancelled
```

**Status Descriptions:**

| Status | Description | Updated By | Transition |
|--------|-------------|------------|------------|
| `triggered` | Sync request received, log created | API endpoint | Immediately on POST /sync |
| `running` | Task execution started | Celery worker | When worker picks up task |
| `success` | Task completed successfully | Celery worker | On successful completion |
| `failed` | Task failed after all retries | Celery worker | On permanent failure |
| `cancelled` | Task manually cancelled | Manual intervention | Rare, manual only |

**Lifecycle Flow:**
1. **API trigger** (POST `/api/v1/channel-connections/{id}/sync`):
   - Creates log entry with `status="triggered"`
   - Includes `task_id` (Celery task UUID) and `batch_id` (groups multiple operations)
   - Returns immediately with task_ids array

2. **Worker picks up task**:
   - Updates log to `status="running"`
   - Executes sync operation (platform API calls)

3. **Task completes**:
   - On success: Updates log to `status="success"`, updates `connection.last_sync_at`
   - On failure: Updates log to `status="failed"`, sets `error` field

**Note on "queued" status:** Prior to 2026-01-03, logs used `status="queued"` when triggered. This was semantically equivalent to "triggered" and both are treated identically in batch status aggregation. Production systems may still show "queued" in historical logs.

---

### Querying Sync Logs

**Via API (Basic):**
```bash
# Get last 50 logs for connection
curl https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?limit=50 \
  -H "Authorization: Bearer TOKEN"

# Get logs with pagination
curl https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?limit=20&offset=40 \
  -H "Authorization: Bearer TOKEN"
```

**Via API (Filtering & Polling):**
```bash
# Poll logs for a specific task_id (check if task completed)
curl "https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?task_id=abc123" \
  -H "Authorization: Bearer TOKEN"

# Poll logs for entire batch (check batch progress)
curl "https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?batch_id={batch_uuid}" \
  -H "Authorization: Bearer TOKEN"

# Filter by status (get only failed syncs)
curl "https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?status=failed" \
  -H "Authorization: Bearer TOKEN"

# Filter by operation type (get only availability updates)
curl "https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?operation_type=availability_update" \
  -H "Authorization: Bearer TOKEN"

# Filter by direction (get only inbound syncs)
curl "https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?direction=inbound" \
  -H "Authorization: Bearer TOKEN"

# Combine filters (get failed availability updates)
curl "https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?status=failed&operation_type=availability_update" \
  -H "Authorization: Bearer TOKEN"
```

**Polling Pattern (Check Task Completion):**
```bash
# 1. Trigger sync and capture task_id
RESPONSE=$(curl -X POST "https://api.your-domain.com/api/v1/channel-connections/{id}/sync" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "availability", "properties": []}')

TASK_ID=$(echo "$RESPONSE" | jq -r '.task_ids[0]')
echo "Task ID: $TASK_ID"

# 2. Poll until task completes (simple loop)
while true; do
  STATUS=$(curl -s "https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?task_id=$TASK_ID" \
    -H "Authorization: Bearer TOKEN" | jq -r '.logs[0].status')

  echo "Status: $STATUS"

  if [[ "$STATUS" == "success" ]] || [[ "$STATUS" == "failed" ]]; then
    echo "Task completed with status: $STATUS"
    break
  fi

  sleep 2  # Wait 2 seconds before next poll
done
```

**Via Database:**
```sql
-- Get recent logs for connection
SELECT id, operation_type, status, created_at, updated_at
FROM channel_sync_logs
WHERE connection_id = 'uuid-here'
ORDER BY created_at DESC
LIMIT 50;

-- Get failed logs
SELECT id, operation_type, error, created_at
FROM channel_sync_logs
WHERE status = 'failed'
ORDER BY created_at DESC;

-- Get logs with retry details
SELECT id, operation_type, status,
       details->>'retry_count' as retries,
       created_at
FROM channel_sync_logs
WHERE details->>'retry_count' IS NOT NULL
ORDER BY created_at DESC;
```

---

### Channel Manager — Sync Log Retention & Cleanup

**Purpose:** Prevent indefinite database growth by implementing periodic cleanup of old sync logs. This section provides professional retention guidelines and manual cleanup procedures.

---

#### Why Retention Matters

**Database Growth:**
- Each sync operation creates 1-3 log entries (full sync creates 3: availability, pricing, bookings)
- High-volume properties with hourly syncs generate ~72 logs/day = ~2,160 logs/month
- Without cleanup, logs accumulate indefinitely, consuming disk space and slowing queries
- Example: 10 properties × 2,160 logs/month × 12 months = 259,200 log entries/year

**UI Performance:**
- Admin UI `/channel-sync` page loads all logs for selected connection (no server-side pagination)
- Large log tables (>10,000 entries per connection) cause slow page loads and browser memory issues
- Sync History section fetches paginated batches, but still slows with excessive data

**Query Performance:**
- Indexed queries remain fast up to ~100,000 total rows
- Beyond 1M rows, even indexed queries may slow down
- Regular cleanup maintains optimal performance

---

#### Recommended Retention Periods

**Test/Staging Environments:**
- **90 days** (3 months)
- Sufficient for debugging recent issues
- Keeps DB size manageable for development workflows

**Production Environments:**
- **180 days** (6 months): Standard retention for operational visibility
- **365 days** (1 year): Extended retention for audit/compliance requirements
- **Custom**: Adjust based on legal/regulatory requirements (e.g., GDPR, financial audits)

**Factors to Consider:**
- **Compliance Requirements:** Some industries require longer retention (e.g., 7 years for financial data)
- **Disk Space:** Monitor Supabase storage usage and adjust retention accordingly
- **Query Performance:** If Admin UI becomes slow, reduce retention period
- **Debugging Needs:** Keep at least 90 days to troubleshoot recurring sync issues

---

#### Manual Cleanup (Supabase SQL Editor)

**Access:** Supabase Dashboard → SQL Editor → New Query

**IMPORTANT:** These queries delete data permanently. Always verify cutoff date before execution.

**1. Delete Logs Older Than N Days**

```sql
-- Test/Staging: Delete logs older than 90 days
DELETE FROM public.channel_sync_logs
WHERE created_at < NOW() - INTERVAL '90 days';

-- Production: Delete logs older than 180 days
DELETE FROM public.channel_sync_logs
WHERE created_at < NOW() - INTERVAL '180 days';

-- Production (Extended): Delete logs older than 365 days
DELETE FROM public.channel_sync_logs
WHERE created_at < NOW() - INTERVAL '365 days';
```

**2. Preview Deletion Count (Safe Dry-Run)**

Before executing DELETE, preview how many rows will be deleted:

```sql
-- Preview: Count logs older than 90 days
SELECT COUNT(*) AS logs_to_delete,
       MIN(created_at) AS oldest_log,
       MAX(created_at) AS newest_affected_log
FROM public.channel_sync_logs
WHERE created_at < NOW() - INTERVAL '90 days';
```

**3. Delete by Specific Cutoff Date**

```sql
-- Delete logs before specific date (e.g., before 2025-01-01)
DELETE FROM public.channel_sync_logs
WHERE created_at < '2025-01-01 00:00:00'::timestamptz;
```

**4. Connection-Specific Cleanup**

```sql
-- Delete old logs for specific connection only
DELETE FROM public.channel_sync_logs
WHERE connection_id = 'your-connection-uuid-here'
  AND created_at < NOW() - INTERVAL '90 days';
```

**5. Advanced: Keep Last N Batches Per Connection**

For connections with batch_id (full syncs), keep only the most recent N batches:

```sql
-- Keep only last 50 batches per connection, delete older batches
WITH batches_to_keep AS (
  SELECT DISTINCT batch_id
  FROM public.channel_sync_logs
  WHERE batch_id IS NOT NULL
    AND connection_id = 'your-connection-uuid-here'
  ORDER BY created_at DESC
  LIMIT 50
)
DELETE FROM public.channel_sync_logs
WHERE connection_id = 'your-connection-uuid-here'
  AND batch_id IS NOT NULL
  AND batch_id NOT IN (SELECT batch_id FROM batches_to_keep);
```

---

#### Safety Notes

**Critical Warnings:**

1. **History Only — No Impact on Bookings/Inventory:**
   - Deleting sync logs removes audit history only
   - Does NOT affect current bookings, availability, or pricing data
   - Safe to delete old logs without business impact

2. **Irreversible Deletion:**
   - Deleted logs cannot be recovered (no soft delete)
   - Always preview with COUNT(*) before executing DELETE
   - Consider exporting logs to CSV if long-term archival is needed

3. **Run During Low-Traffic Windows:**
   - Large deletes (>100,000 rows) can cause brief table locks
   - Recommended: Run during off-peak hours (e.g., 2-4 AM local time)
   - Monitor Supabase dashboard for connection pool usage during execution

4. **Database Locks:**
   - DELETE operations acquire row-level locks
   - Concurrent sync operations may briefly slow down during cleanup
   - Use smaller batches if full table scan is too slow (e.g., delete 1 month at a time)

**Best Practices:**

- **Schedule Regular Cleanup:** Run monthly or quarterly (set calendar reminder)
- **Document Execution:** Keep log of cleanup dates and row counts in operations log
- **Monitor Disk Usage:** Check Supabase storage metrics before/after cleanup
- **Test First:** Run on staging environment before executing on production

---

#### Verification Queries

**1. Check Table Size**

```sql
-- Get total row count and date range
SELECT COUNT(*) AS total_logs,
       MIN(created_at) AS oldest_log,
       MAX(created_at) AS newest_log,
       COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '90 days') AS logs_older_than_90d,
       COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '180 days') AS logs_older_than_180d
FROM public.channel_sync_logs;
```

**2. Logs Per Connection**

```sql
-- Count logs per connection (identify high-volume connections)
SELECT connection_id,
       COUNT(*) AS log_count,
       MIN(created_at) AS oldest,
       MAX(created_at) AS newest
FROM public.channel_sync_logs
GROUP BY connection_id
ORDER BY log_count DESC
LIMIT 20;
```

**3. Storage Size Estimate**

```sql
-- Estimate table size in MB (PostgreSQL)
SELECT pg_size_pretty(pg_total_relation_size('public.channel_sync_logs')) AS total_size,
       pg_size_pretty(pg_relation_size('public.channel_sync_logs')) AS table_size,
       pg_size_pretty(pg_indexes_size('public.channel_sync_logs')) AS indexes_size;
```

**4. Verify Cleanup Success**

Run immediately after DELETE to confirm expected row count:

```sql
-- Should show 0 logs older than retention period
SELECT COUNT(*) AS remaining_old_logs
FROM public.channel_sync_logs
WHERE created_at < NOW() - INTERVAL '90 days';
-- Expected: 0
```

---

#### Automated Cleanup (Future Enhancement)

**Current State:** Manual cleanup required (no automated retention policy implemented)

**Future Options:**

1. **Supabase Cron Job:**
   - Use `pg_cron` extension to schedule monthly cleanup
   - Example: Auto-delete logs older than 180 days on 1st of each month

2. **Application-Level Cleanup:**
   - Add FastAPI scheduled task to run cleanup during off-peak hours
   - Implement configurable retention period via environment variable

3. **Partitioned Tables:**
   - Partition `channel_sync_logs` by month (e.g., `channel_sync_logs_2025_01`)
   - Drop entire partitions for faster cleanup (avoids DELETE scan)

**Tracking Issue:** Consider creating GitHub issue to track automated cleanup implementation.

---

**Related:**

- See [Log Retention & Purge Policy](#log-retention--purge-policy) for Admin UI purge feature (connection-scoped)
- See [Stale Sync Logs (Automatic Cleanup)](#stale-sync-logs-automatic-cleanup) for automatic status-based cleanup
- See [Sync Logs Persistence](#sync-logs-persistence) for table schema and indexes

---

## Celery Worker (pms-worker / pms-worker-v2)

**Purpose:** Comprehensive guide for setting up and troubleshooting the Celery worker application in Coolify.

---

### What is the Celery Worker?

The Celery worker (`pms-worker` or `pms-worker-v2`) is a **headless background task processor** that executes Channel Manager operations:
- Availability sync to external platforms (Airbnb, Booking.com, etc.)
- Pricing sync to external platforms
- Booking imports from external platforms
- Retry logic with exponential backoff for failed operations

**Key Characteristics:**
- No public HTTP endpoints (no domains required)
- Connects to Redis broker for task queue
- Connects to PostgreSQL database for sync log persistence
- Runs independently of pms-backend (different container)
- Must be on same git commit as pms-backend for task compatibility

---

### Coolify Setup (Step-by-Step)

#### Step 1: Create New Application

**Location:** Coolify Dashboard → Add New Resource → Application

1. **Application Name:** `pms-worker-v2` (or `pms-worker`)
2. **Source:** Select your Git repository
3. **Branch:** `main`
4. **Base Directory:** `/backend`
5. **Build Pack:** Nixpacks (auto-detected)

#### Step 2: Configure Start Command

**Location:** Application Settings → Build & Deploy → Start Command

```bash
celery -A app.channel_manager.core.sync_engine:celery_app worker -l INFO
```

**Breakdown:**
- `-A app.channel_manager.core.sync_engine:celery_app`: Celery app module path
- `worker`: Run as worker process (not beat/flower)
- `-l INFO`: Log level (use `DEBUG` for troubleshooting)

#### Step 3: Configure Ports (Coolify UI Requirement)

**Location:** Application Settings → Network → Ports Exposes

**Set:** `8000`

**Important:** This is a dummy value required by Coolify UI. The worker does NOT actually serve HTTP traffic on this port.

#### Step 4: Configure Domains (Leave Empty)

**Location:** Application Settings → Domains

**Action:** Do NOT add any domains. Worker is headless and should not be exposed via Traefik proxy.

#### Step 5: Coolify Beta Workarounds

**Problem:** Deployment may fail with `"Deployment failed: Undefined variable $labels"`

**Solution:**

1. **Enable Read-only Labels:**
   - Application Settings → Advanced → Enable "Read-only labels"

2. **Add Label to Disable Traefik:**
   - Application Settings → Labels
   - Add: `traefik.enable=false`

3. **Disable Proxy Features:**
   - Force HTTPS: **OFF**
   - Gzip Compression: **OFF**
   - Strip Prefixes: **OFF**

4. **Clean Rebuild (if code seems stale):**
   - Deployment Settings → Check "Disable build cache"
   - Pin to specific commit SHA instead of branch reference

---

### Alternative: Build with Dockerfile.worker (Recommended for Non-Root)

**Why use Dockerfile.worker instead of Nixpacks:**

Nixpacks auto-detection installs Python packages under `/root/.nix-profile`, which prevents running as non-root user. Using a dedicated Dockerfile provides:
- **Reliable non-root execution** (appuser UID 10001)
- **No Celery SecurityWarning** (avoids "running as root" warning)
- **Explicit dependency management** (no Nixpacks magic)
- **Better security posture** (principle of least privilege)
- **Configurable worker pool** (threads, prefork, gevent via env vars)

#### Step-by-Step: Switch to Dockerfile.worker

**Step 1: Update Build Pack**

**Location:** Application Settings → Build & Deploy → Build Pack

Change from `Nixpacks` to `Dockerfile`

**Step 2: Set Dockerfile Path**

**Location:** Application Settings → Build & Deploy → Dockerfile

Set: `Dockerfile.worker`

**Base Directory** should still be: `/backend`

**Step 3: Start Command (Automatic via Dockerfile)**

**IMPORTANT:** When using Dockerfile build pack, Coolify does **NOT** allow setting a Start Command in the UI. The worker image automatically boots via the CMD defined in `backend/Dockerfile.worker`:

```bash
CMD ["bash", "/app/scripts/ops/start_worker.sh"]
```

**Note:** With Coolify Build Pack set to "Dockerfile", the Start Command UI field may not be available. The Dockerfile CMD/ENTRYPOINT defines the start command. All customization happens via environment variables (see Step 4 below), not by overriding the start command.

**What this means:**
- Leave "Start Command" field **empty** in Coolify UI (field is disabled/ignored for Dockerfile build pack)
- Worker boots via `scripts/ops/start_worker.sh` by default
- **Wait-for-deps preflight is active automatically** (waits for DB/Redis DNS+TCP before starting Celery)
- Worker pool and concurrency are controlled via environment variables (see Step 4 below)

**Why use the start script:**
- Prevents transient DNS/network failures after Coolify deploys
- Ensures DB and Redis are reachable before Celery starts
- If dependencies unavailable after timeout (default 60s), container exits to trigger restart

**Step 4: Set Worker Pool Environment Variables (Optional)**

**Location:** Application Settings → Environment Variables

Add these optional variables to customize worker behavior:

```bash
# Worker pool type (default: threads)
# Options: threads, prefork, gevent, eventlet, solo
CELERY_POOL=threads

# Number of worker threads/processes (default: 4)
CELERY_CONCURRENCY=4

# Log level (default: INFO)
CELERY_LOGLEVEL=INFO

# Optional: Max tasks before worker restart (prevents memory leaks)
CELERY_MAX_TASKS_PER_CHILD=1000

# Optional: Hard time limit for tasks in seconds
CELERY_TIME_LIMIT=300
```

**Wait-for-deps configuration (prevents transient DNS failures):**

The worker includes a preflight check that waits for database and Redis to be reachable before starting Celery. This prevents transient failures caused by Docker DNS/network timing issues after deployments.

```bash
# Enable dependency wait (default: true)
# Set to false to skip wait (not recommended)
WORKER_WAIT_FOR_DEPS=true

# Max wait time in seconds (default: 60)
# Worker exits if dependencies not ready within this time
WORKER_WAIT_TIMEOUT=60

# Check interval in seconds (default: 2)
# How often to retry DNS/TCP checks
WORKER_WAIT_INTERVAL=2

# Database hostname to wait for (default: supabase-db)
WORKER_WAIT_DB_HOST=supabase-db

# Database port (default: 5432)
WORKER_WAIT_DB_PORT=5432

# Redis hostname to wait for (default: coolify-redis)
WORKER_WAIT_REDIS_HOST=coolify-redis

# Redis port (default: 6379)
WORKER_WAIT_REDIS_PORT=6379
```

**Why wait-for-deps:**
- **Problem:** Docker DNS resolution and network attachment can take 5-30 seconds after container start
- **Symptom:** Worker logs show `socket.gaierror: [Errno -3] Temporary failure in name resolution`
- **Solution:** Wait for DNS + TCP connectivity before starting Celery
- **Behavior:** If timeout exceeded, worker exits (container restarts automatically)
- **Reliability:** Prefer delayed start over starting "half-ready" and failing tasks

**Recommended settings:**
- **Development:** `CELERY_POOL=threads`, `CELERY_CONCURRENCY=4`, `CELERY_LOGLEVEL=DEBUG`
- **Production:** `CELERY_POOL=threads`, `CELERY_CONCURRENCY=8`, `CELERY_LOGLEVEL=INFO`
- **Heavy I/O:** Use `threads` pool (better for async DB/HTTP operations)
- **CPU-bound:** Use `prefork` pool (isolates tasks in separate processes)

**Step 5: Deploy**

Click **Deploy** and monitor logs for:
```
[INFO/MainProcess] celery@pms-worker-v2 ready.
[INFO/MainProcess] Tasks:
  - app.channel_manager.core.sync_engine.update_channel_availability
  - app.channel_manager.core.sync_engine.update_channel_pricing
```

**Verification:**

```bash
# Check process user (should be appuser, not root)
docker exec pms-worker-v2 ps aux | head -3

# Expected output:
# USER       PID  %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
# appuser      1   0.0  0.1 123456 12345 ?        Ss   12:00   0:00 celery -A app.channel_manager...

# Check for SecurityWarning (should be empty)
docker logs pms-worker-v2 2>&1 | grep -i "securitywarning\|running as root"

# Expected: No output (warning is gone)
```

**What changed:**
- Build uses `backend/Dockerfile.worker` instead of Nixpacks auto-detection
- Worker runs as `appuser` (UID 10001) instead of root
- All files owned by `appuser:appuser`
- Celery SecurityWarning no longer appears
- Worker pool and concurrency configurable via env vars

**Rollback to Nixpacks (if needed):**
1. Set Build Pack back to `Nixpacks`
2. Clear "Dockerfile" field
3. Set Start Command to: `celery -A app.channel_manager.core.sync_engine:celery_app worker -l INFO`
4. Redeploy

---

### Required Environment Variables

**Location:** Application Settings → Environment Variables

**Copy ALL environment variables from `pms-backend`, especially:**

#### Core Application
```
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

#### Redis & Celery (CRITICAL)
```
REDIS_URL=redis://:<password>@coolify-redis:6379/0
CELERY_BROKER_URL=redis://:<password>@coolify-redis:6379/0
CELERY_RESULT_BACKEND=redis://:<password>@coolify-redis:6379/0
```

**Important:** Encode special characters in Redis password (e.g., `+` → `%2B`, `=` → `%3D`)

#### Database (CRITICAL)
```
DATABASE_URL=postgresql+asyncpg://postgres:<password>@supabase-db:5432/postgres
```

**Note:** Use `supabase-db` hostname (requires Supabase network attachment, see below)

#### Health Checks
```
ENABLE_REDIS_HEALTHCHECK=true
ENABLE_CELERY_HEALTHCHECK=true
```

#### Authentication (CRITICAL)
```
JWT_SECRET=<same-as-backend>
SUPABASE_JWT_SECRET=<same-as-goTrue>
JWT_AUDIENCE=authenticated
ENCRYPTION_KEY=<same-as-backend>
```

**Important:** JWT secrets must EXACTLY match pms-backend and Supabase GoTrue for token validation.

#### Optional
```
SENTRY_DSN=<if-using-sentry>
FEATURE_CHANNEL_MANAGER_ENABLED=true
```

---

### Networks (CRITICAL)

**Problem:** Worker needs access to BOTH Coolify infrastructure AND Supabase database.

**Required Networks:**
1. `coolify` (default, for Redis access)
2. `bccg4gs4o4kgsowocw08wkw4` (Supabase network, for database access)

#### Attach to Supabase Network

**Symptom if missing:** Database DNS resolution fails, "Database temporarily unavailable" errors

**Solution (Host Server Terminal):**

```bash
# SSH to host server
ssh root@your-server.com

# Connect worker to Supabase network
docker network connect bccg4gs4o4kgsowocw08wkw4 pms-worker-v2

# Restart worker to pick up network changes
docker restart pms-worker-v2

# Verify networks
docker inspect pms-worker-v2 | grep -A 10 '"Networks"'

# Expected: both "coolify" and "bccg4gs4o4kgsowocw08wkw4" networks
```

**Test DNS Resolution:**

```bash
# Test database DNS from inside worker container
docker exec pms-worker-v2 nslookup supabase-db

# Expected: IP address (e.g., 172.20.0.2)
# If empty/error: Network attachment failed
```

---

### Verification Checklist

#### 1. Container is Running

```bash
# Host server terminal
docker ps | grep pms-worker

# Expected: pms-worker-v2 container with "Up" status
# If "Exited": Check logs for crash reason
```

#### 2. Celery Worker is Ready

```bash
# Host server terminal
docker logs pms-worker-v2 --tail 50 | grep "ready"

# Expected output:
# [INFO/MainProcess] celery@pms-worker-v2 ready.
# [INFO/MainProcess] Tasks:
#   - app.channel_manager.core.sync_engine.update_channel_availability
#   - app.channel_manager.core.sync_engine.update_channel_pricing
```

#### 3. Tasks are Being Received

**Trigger a test sync:**

```bash
# From backend API
curl -X POST https://api.fewo.kolibri-visions.de/api/v1/availability/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sync_type": "availability",
    "platform": "airbnb",
    "property_id": "<property-uuid>",
    "manual_trigger": true
  }'

# Check worker logs for task receipt
docker logs pms-worker-v2 --tail 20 | grep "received"

# Expected:
# [INFO/MainProcess] Task update_channel_availability[abc123] received
# [INFO/ForkPoolWorker-1] Task update_channel_availability[abc123] succeeded
```

#### 4. Sync Logs are Updated

```bash
# From backend API
curl https://api.fewo.kolibri-visions.de/api/v1/channel-connections/<connection-id>/sync-logs?limit=5 \
  -H "Authorization: Bearer $TOKEN"

# Expected: Logs show status progression
# triggered → running → success (or failed)
# updated_at timestamps should be set
```

#### 5. Verify Code Version (Optional)

**Use Case:** Ensure worker is running latest code after deployment

```bash
# Get SHA256 hash of sync_engine.py in container
docker exec pms-worker-v2 sha256sum /app/app/channel_manager/core/sync_engine.py

# Compare with local repo hash
sha256sum backend/app/channel_manager/core/sync_engine.py

# Hashes should match
```

**Alternative: Check Git Commit**

```bash
# Backend commit
docker exec pms-backend git rev-parse HEAD

# Worker commit
docker exec pms-worker-v2 git rev-parse HEAD

# Must match exactly
```

---

### Common Issues & Troubleshooting

#### Worker Crashes on Startup

**Symptom:** Container exits immediately after deployment

**Diagnosis:**

```bash
docker logs pms-worker-v2 --tail 100
```

**Common Causes:**
1. **Redis connection failed:** Check `REDIS_URL` and password encoding
2. **Module import error:** Check if code compiles (`python3 -m py_compile app/channel_manager/core/sync_engine.py`)
3. **Missing environment variable:** Check logs for "KeyError" or "FieldValidationError"

#### Tasks Not Being Received

**Symptom:** Worker is "ready" but no tasks appear in logs

**Diagnosis:**

```bash
# From backend container, ping Celery workers
docker exec pms-backend celery -A app.channel_manager.core.sync_engine:celery_app \
  --broker "$CELERY_BROKER_URL" inspect ping -t 3

# Expected: -> celery@pms-worker-v2: {'ok': 'pong'}
# If timeout: Worker cannot connect to Redis broker
```

**Solutions:**
1. Verify `CELERY_BROKER_URL` matches between backend and worker
2. Check Redis is running: `docker ps | grep redis`
3. Check worker is on `coolify` network

#### Database Temporarily Unavailable

**Symptom:** Worker logs show `"Database is temporarily unavailable"` or `"Failed to update sync log ... 503"`

**Cause:** Worker not attached to Supabase network

**Solution:** See [Networks (CRITICAL)](#networks-critical) section above

**Test:**

```bash
# Test direct DB connection from worker
docker exec pms-worker-v2 python3 -c "import asyncpg; import asyncio; import os; asyncio.run(asyncpg.connect(os.environ['DATABASE_URL']).close()); print('DB OK')"

# Expected: "DB OK"
# If error: DATABASE_URL wrong or network missing
```

#### Worker Starts with Wrong CMD (start_worker.sh Not Used)

**Symptom:**
- `docker inspect` shows wrong command even though Dockerfile.worker has correct CMD:
  ```bash
  docker inspect pms-worker-v2 --format 'Cmd={{json .Config.Cmd}}'
  # Shows: ["/bin/sh","-c","celery -A app.channel_manager.core.sync_engine:celery_app worker ..."]
  # Expected: ["bash","/app/scripts/ops/start_worker.sh"]
  ```
- Worker logs do NOT show:
  ```
  [worker] start_worker.sh active
  ====== Wait-for-Deps Preflight Check ======
  ```

**Root Causes:**

A) **Coolify Start Command Override:** Legacy "Start Command" field in Coolify UI overrides Dockerfile CMD
B) **Coolify Git Commit Pinned:** Build log shows checkout of old commit SHA before Dockerfile.worker was updated
C) **Dockerfile Path Mismatch:** Coolify prepends "/" automatically; incorrect Base Directory or Dockerfile Location

**Diagnosis (HOST-SERVER-TERMINAL):**

```bash
# 1. Compare container CMD vs image CMD
docker inspect pms-worker-v2 --format 'Image={{.Config.Image}} Cmd={{json .Config.Cmd}}'
# Container shows: Cmd=["/bin/sh","-c","celery ..."]

# Get image ID from above output
IMAGE_ID="<image-id-or-tag-from-above>"
docker inspect $IMAGE_ID --format 'Cmd={{json .Config.Cmd}}'
# Image shows: ["bash","/app/scripts/ops/start_worker.sh"]
# If these differ: Coolify Start Command override is active

# 2. Confirm repo has correct CMD
cd /path/to/PMS-Webapp
git log -n 3 --oneline
# Should show recent commits including Dockerfile.worker updates

grep -nE '^(CMD|ENTRYPOINT)\b' backend/Dockerfile.worker
# Should show: CMD ["bash", "/app/scripts/ops/start_worker.sh"]
```

**Fix Steps (Coolify UI):**

1. **Clear Start Command Override:**
   - Location: Coolify Dashboard → pms-worker-v2 → General → Start Command
   - Action: **Delete any text in the field** (leave it empty)
   - Why: Dockerfile CMD should be used, not UI override

2. **Unpin Git Commit (Build from HEAD):**
   - Location: Coolify Dashboard → pms-worker-v2 → General → Git
   - Field: "Commit SHA" or "Git Commit to deploy"
   - Action: **Clear the field** (empty = build latest commit from main)
   - Why: Ensures latest Dockerfile.worker is used

3. **Verify Build Settings:**
   - Location: Coolify Dashboard → pms-worker-v2 → Build & Deploy
   - Base Directory: `/backend` (with leading slash)
   - Dockerfile Location: `/Dockerfile.worker` (with leading slash)
   - Note: Coolify may prepend "/" automatically; do not use `backend/Dockerfile.worker`

4. **Redeploy (NOT just restart):**
   - Location: Coolify Dashboard → pms-worker-v2 → Deployments
   - Action: Click "Redeploy" (triggers new build)
   - Why: Restart uses existing image; redeploy builds fresh image

**Verification:**

```bash
# After redeploy completes, verify container CMD
docker inspect pms-worker-v2 --format 'Cmd={{json .Config.Cmd}}'
# Expected: ["bash","/app/scripts/ops/start_worker.sh"]

# Check worker logs for startup sequence
docker logs pms-worker-v2 --tail 50 | head -20
# Expected output:
#   [worker] start_worker.sh active
#   [2025-12-29 ...] ====== Wait-for-Deps Preflight Check ======
#   [2025-12-29 ...] Waiting for Database (supabase-db:5432)...
#   [2025-12-29 ...]   ✓ Database is ready (supabase-db:5432)
#   [2025-12-29 ...] Waiting for Redis (coolify-redis:6379)...
#   [2025-12-29 ...]   ✓ Redis is ready (coolify-redis:6379)
#   [2025-12-29 ...] ✓ All dependencies ready
#   [2025-12-29 ...] ====== Celery Worker Starting ======
#   [2025-12-29 ...] Configuration:
#   [2025-12-29 ...]   Pool: threads
#   [2025-12-29 ...]   Concurrency: 4
```

**Related Issues:**
- If worker crashes after fixing CMD: Check [Worker Crashes on Startup](#worker-crashes-on-startup)
- If wait-for-deps times out: Check [Networks (CRITICAL)](#networks-critical) and DNS resolution

#### Stale Code After Deployment

**Symptom:** New code changes don't appear in worker behavior

**Diagnosis:**

```bash
# Check if code hash matches local repo
docker exec pms-worker-v2 sha256sum /app/app/channel_manager/core/sync_engine.py

# Compare with local
sha256sum backend/app/channel_manager/core/sync_engine.py
```

**Solutions:**
1. **Pin to commit SHA** in Coolify deployment settings (instead of branch reference)
2. **Enable "Disable build cache"** in deployment settings
3. **Force rebuild:** Settings → Deployments → Redeploy with cache disabled

#### Sync Logs Stuck at "running"

**Symptom:** Sync logs never transition to `success` or `failed`

**Diagnosis:**

```bash
# Check worker logs for exceptions during task execution
docker logs pms-worker-v2 --tail 100 | grep -i error

# Check if MaxRetriesExceededError is being caught
docker logs pms-worker-v2 | grep "Max retries exceeded"
```

**Common Causes:**
1. Task is hanging indefinitely (no timeout configured)
2. Exception handler not marking log as failed
3. Worker crashed mid-task

**Solution:** Check sync_engine.py retry logic and ensure MaxRetriesExceededError sets status to "failed"

---

### Architecture Notes

**Direct Database Connections (Celery-Safe):**

Celery workers do NOT use the FastAPI connection pool (pool only exists in backend lifespan). Instead, workers use direct connections:

- `_check_database_availability()`: Creates short-lived connection with 5s timeout for health checks
- `_update_log_status()`: Creates connection per sync log update with JSON/JSONB codec registration
- All connections are properly closed in `finally` blocks (fork/event-loop safe)

**Fork-Safety:**

Celery uses prefork pool model. Workers register a `worker_process_init` signal to reset pool state in forked children, ensuring each worker process creates its own connections.

**Celery 6 Broker Connection Retry:**

The worker explicitly sets `broker_connection_retry_on_startup = True` to silence Celery 6 deprecation warnings. This makes the broker connection retry behavior explicit on worker startup.

**Why this setting:**
- **Celery 6 deprecation:** Celery 6 warns if this setting is not explicitly configured
- **Default behavior:** When `True`, the worker retries connecting to Redis broker on startup if the initial connection fails
- **Recommended for production:** Prevents worker crash if Redis is temporarily unavailable during startup
- **Location:** Configured in `app/channel_manager/core/sync_engine.py` (celery_app.conf)

**Expected behavior:**
- Worker startup logs no longer show deprecation warning about `broker_connection_retry_on_startup`
- If Redis is down during worker startup, worker retries connection instead of crashing
- Consistent with existing retry behavior for broker connection during runtime

**Worker Runs as Non-Root User:**

Both pms-backend and pms-worker-v2 containers run as a non-root user (`app` with UID 1000) for improved security and to silence Celery's SecurityWarning.

**Why non-root:**
- **Security best practice:** Reduces attack surface if container is compromised
- **Celery warning:** Celery emits a SecurityWarning when running as root
- **Production hygiene:** Follows principle of least privilege
- **Container standards:** Aligns with Docker/Kubernetes security best practices

**Implementation:**
- Dockerfile creates user `app` (UID 1000) during build
- All application files owned by `app:app`
- Container switches to `USER app` before running commands
- Both backend (uvicorn) and worker (celery) run as this user

**Verification:**

Check which user is running the worker process:

```bash
# Inside worker container
docker exec pms-worker-v2 ps aux

# Expected output:
# USER       PID  %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
# app          1   0.0  0.1 123456 12345 ?        Ss   12:00   0:00 celery -A app.channel_manager...
# app         XX   0.0  0.1 123456 12345 ?        S    12:00   0:00 [celery worker process]
```

Check worker startup logs for absence of SecurityWarning:

```bash
# Check logs for security warning (should be empty)
docker logs pms-worker-v2 2>&1 | grep -i "securitywarning\|running as root"

# Expected: No output (warning is gone)
```

**Files:**
- `backend/Dockerfile`: Defines non-root user and sets USER directive
- Image build: Coolify auto-detects Dockerfile and uses it instead of Nixpacks

**Note:** If you see permission errors after deployment, check that `/app` and `/app/logs` are owned by `app:app` (UID 1000).

---

## Celery Worker (pms-worker-v2): Start, Verify, Troubleshoot

**Purpose:** Reference guide for verifying worker startup, CMD/entrypoint configuration, and diagnosing build/cache drift issues (SOURCE_COMMIT mismatch).

---

### 1. Current Stable Setup (pms-worker-v2)

**Production Container Topology:**

```
Containers:
- pms-backend        (FastAPI application)
- pms-worker-v2      (Celery worker - headless background processor)
- coolify-redis      (Redis broker for Celery task queue)
- supabase-db-<id>   (PostgreSQL database)
```

**Network Configuration:**

```
pms-backend:
  - coolify                          (default Coolify network)
  - bccg4gs4o4kgsowocw08wkw4          (Supabase network - for supabase-db DNS)

pms-worker-v2:
  - coolify                          (default Coolify network)
  - bccg4gs4o4kgsowocw08wkw4          (Supabase network - for supabase-db DNS)

coolify-redis:
  - coolify                          (default Coolify network)
```

**Why both containers need Supabase network:**
- Resolves `supabase-db` hostname for DATABASE_URL
- Without it: `socket.gaierror: [Errno -3] Temporary failure in name resolution`

**Health Evidence:**

Endpoint: `GET /health/ready`

Expected response when worker is operational:
```json
{
  "status": "ready",
  "checks": {
    "database": "up",
    "redis": "up",
    "celery": "up"
  },
  "celery_workers": [
    "celery@pms-worker-v2-<hostname>"
  ]
}
```

**Key indicators:**
- `celery: "up"` → Redis connection OK
- `celery_workers` array not empty → At least one worker is registered and responding to ping

---

### 2. Worker Startup CMD / Entrypoint (from CMD Issue Diagnose)

**Container Boot Path:**

The `pms-worker-v2` container is started via the repository script (not direct Celery command):

**Path in container:** `/app/scripts/ops/start_worker.sh`

**Purpose:**
- Stable Celery startup with configurable pool/concurrency/loglevel
- Preflight dependency checks (wait-for-deps: database + Redis DNS/TCP reachable)
- Environment-driven configuration (no hardcoded values)

**Effective Celery Command:**

The script executes:
```bash
celery -A app.channel_manager.core.sync_engine:celery_app worker \
  --pool=${CELERY_POOL:-threads} \
  --concurrency=${CELERY_CONCURRENCY:-4} \
  --loglevel=${CELERY_LOGLEVEL:-INFO}
```

**Environment Variable Defaults:**
```bash
CELERY_POOL=threads           # Worker pool type (threads, prefork, gevent)
CELERY_CONCURRENCY=4          # Number of worker threads/processes
CELERY_LOGLEVEL=INFO          # Log verbosity (DEBUG, INFO, WARNING, ERROR)
```

**Optional environment overrides:**
```bash
CELERY_MAX_TASKS_PER_CHILD=1000   # Max tasks before worker restart (memory leak prevention)
CELERY_TIME_LIMIT=300             # Hard time limit for tasks (seconds)
```

**Coolify Build Pack Quirk:**

When using **Dockerfile** build pack (recommended for pms-worker-v2):
- Coolify UI does **NOT** allow setting "Start Command" (field disabled/ignored)
- Worker boots via `CMD` defined in `backend/Dockerfile.worker`:
  ```dockerfile
  CMD ["bash", "/app/scripts/ops/start_worker.sh"]
  ```
- **Workaround:** All customization happens via environment variables (not Start Command override)

**Coolify "Ports Exposes" Requirement:**

Even though pms-worker-v2 does NOT serve HTTP traffic, Coolify UI may require a port value:
- **Location:** Application Settings → Network → Ports Exposes
- **Set:** `8000` (placeholder - not actually used)
- **Why:** Coolify beta UI validation bug (worker is headless, no real port needed)

---

### 3. Verification Checklist (Copy/Paste Commands)

**HOST-SERVER-TERMINAL:**

```bash
# Check all PMS containers and their networks
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Networks}}' | egrep -i 'pms|redis|supabase' || true

# Expected output:
# NAMES              STATUS          NETWORKS
# pms-backend        Up X hours      coolify, bccg4gs4o4kgsowocw08wkw4
# pms-worker-v2      Up X hours      coolify, bccg4gs4o4kgsowocw08wkw4
# coolify-redis      Up X hours      coolify
# supabase-db-<id>   Up X hours      bccg4gs4o4kgsowocw08wkw4
```

**Coolify TERMINAL (Container: pms-backend):**

```bash
# Check API health and worker registration
curl -k -sS https://api.fewo.kolibri-visions.de/health/ready | sed -n '1,200p'

# Expected JSON:
# {
#   "status": "ready",
#   "checks": { "database": "up", "redis": "up", "celery": "up" },
#   "celery_workers": ["celery@pms-worker-v2-..."]
# }
```

**Coolify TERMINAL (Container: pms-worker-v2) - Optional Verification:**

```bash
# Verify start script exists
ls -la /app/scripts/ops/start_worker.sh

# Expected:
# -rwxr-xr-x 1 app app <size> <date> /app/scripts/ops/start_worker.sh
# (executable bit set, owned by app:app)

# Inspect start script content
head -n 40 /app/scripts/ops/start_worker.sh

# Expected to see:
# - #!/usr/bin/env bash
# - wait-for-deps preflight checks (DNS + TCP for database/Redis)
# - celery -A app.channel_manager.core.sync_engine:celery_app worker ...
```

**Quick Smoke Test:**

```bash
# Test Celery worker responds to ping
docker exec pms-worker-v2 celery -A app.channel_manager.core.sync_engine:celery_app inspect ping

# Expected:
# -> celery@pms-worker-v2-<hostname>: {'ok': 'pong'}
```

---

### 4. Critical Failure Mode: SOURCE_COMMIT Correct but Worker Runs Old Code (Build/Cache Drift)

**Symptoms:**

1. **Worker cannot update channel_sync_logs:**
   - Sync logs stuck in "triggered" status (never transition to "running" → "success/failed")
   - Worker logs show errors about missing columns/tables that SHOULD exist in new schema

2. **Worker errors look "wrong" vs expected commit:**
   - Code references functions/modules that were refactored/removed in latest commit
   - Import errors for recently added modules

3. **SOURCE_COMMIT env says new SHA but code files differ:**
   - Environment variable shows latest commit hash
   - Actual Python files in `/app/` directory contain old code

**Root Cause:**

Coolify built the worker image from an **outdated checkout or stale build cache**:
- Git source directory under `/data/coolify/source` not updated to origin/main
- Build cache from previous deployment used despite new SOURCE_COMMIT
- Image layering cached old dependencies/code even though new commit was deployed

**Diagnosis (Copy/Paste Commands):**

**Coolify TERMINAL (Container: pms-worker-v2):**

```bash
# Check SOURCE_COMMIT environment variable
echo "SOURCE_COMMIT=$SOURCE_COMMIT"

# Expected: Latest commit SHA from origin/main (e.g., 733038a...)
```

```bash
# Verify actual code file hash (example: sync_engine.py)
python -c 'import pathlib,hashlib; p=pathlib.Path("/app/app/channel_manager/core/sync_engine.py"); print(p, p.exists(), hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "missing")'

# Expected: File exists + SHA256 hash
# Compare this hash with the file at SOURCE_COMMIT in GitHub repo
# If hashes differ → build/cache drift confirmed
```

```bash
# Inspect start script content
head -n 40 /app/scripts/ops/start_worker.sh

# Expected: Script content matches repo at SOURCE_COMMIT
# If script is missing/outdated → build/cache drift confirmed
```

**Additional Verification:**

```bash
# Check git status inside container (if .git exists)
docker exec pms-worker-v2 git rev-parse HEAD 2>/dev/null || echo ".git not in image"

# If .git exists: compare with SOURCE_COMMIT env
# If they differ OR .git missing → verify via file hash instead
```

**Fix Guidance (High-Level):**

1. **Force Clean Rebuild in Coolify:**
   - Coolify Dashboard → pms-worker-v2 → Deployment Settings
   - Enable: **"Disable build cache"** (forces fresh build)
   - Trigger new deployment

2. **Pin to Specific Commit SHA (instead of branch reference):**
   - Coolify Dashboard → pms-worker-v2 → General → Git
   - Change branch from `main` to specific commit SHA (e.g., `733038a`)
   - This prevents Coolify from using stale branch pointer

3. **Ensure Source Directory is Updated:**
   - **If using host checkout:** Coolify may clone repo to `/data/coolify/source/<app-id>`
   - SSH to host server and verify:
     ```bash
     cd /data/coolify/source/<app-id>
     git fetch origin
     git log --oneline -5  # Should show latest commits
     ```
   - If outdated: `git pull origin main` and redeploy

4. **Verify Base Directory is Correct:**
   - Coolify Dashboard → pms-worker-v2 → General → Base Directory
   - Must be: `/backend` (NOT `/` or `/backend/app`)
   - Dockerfile.worker path: `Dockerfile.worker` (relative to base directory)

**Prevention:**

- Always deploy pms-backend FIRST, then pms-worker-v2 (sequential, not parallel)
- Use commit SHA instead of branch name for critical deployments
- Enable "Disable build cache" after major refactors
- Verify `/health/ready` shows worker registration after each deploy

---

### 5. Decommission Old Worker (if it ever exists again)

**"Done" Criteria:**

Only `pms-worker-v2` exists in production:
```bash
docker ps | egrep -i 'pms-worker'

# Expected output:
# pms-worker-v2   Up X hours   ...

# NOT expected:
# pms-worker      Up X hours   ...  (old worker should NOT exist)
# pms-worker-v2   Up X hours   ...
```

**Why multiple workers are dangerous:**

- **Task distribution is non-deterministic:** Redis/Celery load-balance tasks across ALL registered workers
- **Version skew:** If old worker runs outdated code, some tasks execute with wrong logic
- **Silent failures:** HTTP 201 from POST /availability/sync but task runs on wrong worker → logs stuck "triggered"
- **Diagnosis confusion:** Half of tasks succeed (new worker), half fail (old worker) → intermittent issues

**Decommission Steps:**

1. **Identify old worker container:**
   ```bash
   docker ps -a | grep pms-worker | grep -v v2
   ```

2. **Stop and remove old worker:**
   ```bash
   docker stop pms-worker
   docker rm pms-worker
   ```

3. **Disable old worker service in Coolify:**
   - Coolify Dashboard → Applications
   - Find `pms-worker` (without v2 suffix)
   - Settings → Danger Zone → Delete Application

4. **Verify only pms-worker-v2 remains:**
   ```bash
   curl -k -sS https://api.fewo.kolibri-visions.de/health/ready | jq '.celery_workers'

   # Expected:
   # ["celery@pms-worker-v2-<hostname>"]
   # (only ONE worker, name includes "v2")
   ```

**Migration from pms-worker → pms-worker-v2:**

If you need to migrate (upgrade old worker to new version):
1. Create new `pms-worker-v2` app in Coolify (following setup steps in this runbook)
2. Deploy pms-worker-v2 and verify `/health/ready` shows it registered
3. Stop old `pms-worker` container (verify tasks still processing via v2)
4. Monitor for 24-48 hours (ensure no issues)
5. Delete old `pms-worker` app from Coolify permanently

---

## Deployment Process

**Purpose:** Safe sequential deployment of pms-backend and pms-worker to avoid race conditions.

### Critical Requirement: Sequential Deployment

**⚠️ NEVER deploy pms-backend and pms-worker in parallel!**

**Why Sequential?**
1. Backend and worker must be on the **same git commit**
2. Code changes may affect both HTTP endpoints and Celery tasks
3. Deploying in parallel → version mismatch → task failures

**Correct Order:**
```
1. Deploy pms-backend (wait for completion)
2. Deploy pms-worker (after backend is stable)
```

---

### Deployment Workflow

#### Step 1: Pre-Deployment Checks

**Location:** Coolify Dashboard

**Verify:**
- ✅ All tests pass in CI/CD (if configured)
- ✅ Database migrations ready (if schema changes)
- ✅ No active incidents or alerts
- ✅ Current deployments are stable (check `/health/ready`)

**Health Check:**
```bash
curl https://api.your-domain.com/health/ready | jq .

# Expected:
# {
#   "status": "ready",
#   "checks": {
#     "database": "up",
#     "redis": "up",
#     "celery": "up"
#   }
# }
```

#### Step 2: Deploy pms-backend

**Location:** Coolify Dashboard → pms-backend

1. Click **Deploy** button
2. Monitor deployment logs for errors
3. Wait for "Deployment successful" message
4. **DO NOT proceed to worker deployment yet**

**Verify Backend Deployment:**
```bash
# Check health endpoint
curl https://api.your-domain.com/health | jq .

# Check API version (if versioned)
curl https://api.your-domain.com/docs | grep version

# Verify git commit
docker exec pms-backend git rev-parse HEAD
```

#### Step 3: Verify Backend Stability

**Wait Time:** 2-3 minutes minimum

**Health Checks:**
```bash
# Check /health/ready multiple times
for i in {1..5}; do
  echo "Check $i:"
  curl -s https://api.your-domain.com/health/ready | jq '.status'
  sleep 10
done

# Expected: All checks return "ready"
```

**Check Logs:**
```bash
# Look for errors in backend logs
docker logs pms-backend --tail 100 | grep -i error

# No critical errors should appear
```

#### Step 4: Run Database Migrations (If Needed)

**If schema changes in this deployment:**

```bash
# SSH to host
ssh root@your-host

# Run migrations (adjust path as needed)
docker exec -it pms-backend python -m alembic upgrade head

# OR for Supabase migrations:
cd supabase/migrations
docker exec $(docker ps -q -f name=supabase) supabase migration up
```

**Verify Migration:**
```bash
# Check if channel_sync_logs table exists
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  -c "\dt channel_sync_logs"
```

#### Step 5: Deploy pms-worker

**⚠️ Only proceed if backend is stable!**

**Location:** Coolify Dashboard → pms-worker

1. Click **Deploy** button
2. Monitor deployment logs
3. Wait for "Deployment successful"

**Verify Worker Deployment:**
```bash
# Check worker logs for startup
docker logs pms-worker --tail 50 | grep "ready"

# Expected:
# [INFO] celery@pms-worker ready.
# [INFO] Tasks: [list of registered tasks]
```

#### Step 6: Post-Deployment Verification

**Check Health Endpoint:**
```bash
curl https://api.your-domain.com/health/ready | jq .
```

**Expected Output:**
```json
{
  "status": "ready",
  "checks": {
    "database": "up",
    "redis": "up",
    "celery": "up"
  },
  "celery_workers": [
    "celery@pms-worker-abc123"
  ]
}
```

**Test Celery Connection:**
```bash
# From backend container
docker exec pms-backend \
  celery -A app.channel_manager.core.sync_engine:celery_app \
  --broker "$CELERY_BROKER_URL" inspect ping -t 3

# Expected: -> celery@pms-worker-abc123: {'ok': 'pong'}
```

**Verify Git Commits Match:**
```bash
# Get backend commit
BACKEND_COMMIT=$(docker exec pms-backend git rev-parse HEAD)
echo "Backend: $BACKEND_COMMIT"

# Get worker commit
WORKER_COMMIT=$(docker exec pms-worker git rev-parse HEAD)
echo "Worker:  $WORKER_COMMIT"

# They should match!
if [ "$BACKEND_COMMIT" = "$WORKER_COMMIT" ]; then
  echo "✓ Commits match - deployment consistent"
else
  echo "✗ COMMIT MISMATCH - redeploy worker!"
fi
```

#### Step 7: Smoke Test

**Run Quick Smoke Test:**
```bash
# Load environment
source /root/pms_env.sh

# Get JWT token
TOKEN="$(curl -sS "$SB_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')"

# Trigger test sync
CID="$(curl -k -sS -L "https://api.your-domain.com/api/v1/channel-connections/" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[0]["id"] if d else "")')"

curl -X POST "https://api.your-domain.com/api/v1/channel-connections/$CID/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type":"availability"}'

# Check sync logs
sleep 5
curl "https://api.your-domain.com/api/v1/channel-connections/$CID/sync-logs?limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq '.logs[0]'
```

---

### Coolify Auto-Deploy Configuration

**⚠️ DO NOT enable auto-deploy for both apps simultaneously!**

**Safe Configuration:**

**Option 1: Manual Deployment (Recommended)**
- pms-backend: Auto-deploy **OFF**
- pms-worker: Auto-deploy **OFF**
- Deploy manually via dashboard in correct sequence

**Option 2: Backend Auto-Deploy Only**
- pms-backend: Auto-deploy **ON** (trigger: push to `main`)
- pms-worker: Auto-deploy **OFF** (manual only)
- After backend auto-deploys, manually deploy worker

**Option 3: Deployment Script (Advanced)**

Create deployment script that enforces sequence:

```bash
#!/bin/bash
# deploy-pms.sh

set -e  # Exit on error

echo "Step 1: Deploying pms-backend..."
# Trigger backend deployment via Coolify API
curl -X POST https://coolify.example.com/api/deploy/pms-backend \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"

echo "Waiting for backend to stabilize (2 minutes)..."
sleep 120

echo "Step 2: Verifying backend health..."
STATUS=$(curl -s https://api.your-domain.com/health/ready | jq -r '.status')
if [ "$STATUS" != "ready" ]; then
  echo "✗ Backend health check failed - aborting worker deployment"
  exit 1
fi

echo "Step 3: Deploying pms-worker..."
curl -X POST https://coolify.example.com/api/deploy/pms-worker \
  -H "Authorization: Bearer $COOLIFY_API_TOKEN"

echo "Waiting for worker to start..."
sleep 60

echo "Step 4: Verifying worker health..."
CELERY_STATUS=$(curl -s https://api.your-domain.com/health/ready | jq -r '.checks.celery')
if [ "$CELERY_STATUS" = "up" ]; then
  echo "✓ Deployment complete and healthy"
else
  echo "✗ Worker health check failed"
  exit 1
fi
```

**Trigger via GitHub Actions:**
```yaml
name: Deploy PMS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Run sequential deployment
        run: |
          ssh root@your-host 'bash /root/deploy-pms.sh'
```

---

### Rollback Procedure

**If deployment fails:**

**Step 1: Identify Failed Component**
```bash
# Check which service is unhealthy
curl https://api.your-domain.com/health/ready | jq '.checks'
```

**Step 2: Rollback via Coolify**

**Location:** Coolify Dashboard → pms-backend (or pms-worker) → Deployments

1. Find previous successful deployment
2. Click **Redeploy** on that version
3. Wait for completion
4. Verify health

**Step 3: Verify Rollback Success**
```bash
# Check health
curl https://api.your-domain.com/health/ready

# Verify git commit matches expected version
docker exec pms-backend git rev-parse HEAD
```

---

### Common Deployment Issues

**Issue:** Worker shows old code after backend deployment

**Cause:** Worker not redeployed
**Solution:** Deploy worker manually

**Issue:** Celery tasks fail with "Task not registered"

**Cause:** Backend/worker version mismatch
**Solution:** Redeploy worker to match backend commit

**Issue:** Database migration fails

**Cause:** Schema conflict or missing dependency
**Solution:** Rollback deployment, fix migration, redeploy

**Issue:** pms-admin (frontend) build fails in Coolify/Nixpacks

**Symptom:**
- Coolify deployment shows `npm run build` failing with webpack/TypeScript compile error
- Build log shows: "the name `X` is defined multiple times" (e.g., `copyToClipboard`)
- Error import trace points to Next.js page file (e.g., `./app/channel-sync/page.tsx`)
- Build exits with code 1

**Common Causes:**
1. **Duplicate function declarations** in a single file (TypeScript/webpack cannot resolve)
   - Example: `const copyToClipboard = ...` defined twice in same component
   - Often happens when merging features or copy-pasting helper functions
2. **Import conflicts** or circular dependencies
3. **Type errors** that fail strict TypeScript compilation

**Solution:**
1. **Check build logs** in Coolify → pms-admin → Deployments → Build Logs
2. **Identify duplicate declaration:**
   ```bash
   # Search for duplicate in the file mentioned in error trace
   grep -n "const copyToClipboard" frontend/app/channel-sync/page.tsx
   # Expected: Should show only ONE definition
   ```
3. **Fix locally:**
   - Open the problematic file
   - Find all instances of the duplicate function/const
   - Keep ONE definition (preferably the most robust one with fallbacks)
   - Update all call sites to use consistent signature
   - Remove the duplicate(s)
4. **Commit and push:**
   ```bash
   git add frontend/app/channel-sync/page.tsx
   git commit -m "admin-ui: fix duplicate function declaration"
   git push origin main
   ```
5. **Redeploy** via Coolify → pms-admin → Redeploy
6. **Verify build succeeds** (watch build logs until "Build successful")

**Note:** `$NIXPACKS_PATH` UndefinedVar warnings in build logs are usually **non-fatal**. Build failures are typically due to TypeScript/webpack compile errors (duplicate declarations, type mismatches, import errors).

**Prevention:**
- Before adding helper functions, search the file to check if they already exist
- Use consistent naming conventions to avoid collisions
- Run `npm run build` locally before pushing (if possible)

**Issue:** Frontend build fails with JSX syntax error (unclosed tag)

**Symptom:**
- Coolify deployment shows `npm run build` failing with error: "Unexpected token `div`. Expected jsx identifier"
- Error trace points to a line with valid-looking JSX (e.g., `<div className="...">`)
- TypeScript compiler (`npx tsc --noEmit`) shows "JSX element 'div' has no corresponding closing tag"
- Actual root cause is often LATER in the file (cascading error from missing closing tag)

**Common Causes:**
1. **Missing closing tag** in JSX block (e.g., `<div>...</div>` → missing `</div>`)
2. **Unclosed ternary expression** inside JSX (e.g., `{condition ? <div>...</div> : <div>...</div>}` missing closing tag)
3. **Brace mismatch** in nested JSX blocks

**Solution:**
1. **Run TypeScript compiler locally** to get full error list:
   ```bash
   cd frontend
   npx tsc --noEmit --jsx preserve app/connections/page.tsx
   ```
2. **Identify root cause:** Look for FIRST error (e.g., "JSX element 'div' has no corresponding closing tag")
3. **Check surrounding JSX structure:** Trace opening tags to their closing tags
4. **Common fix:** Add missing `</div>` after ternary expressions or conditional blocks
5. **Re-run build** to verify: `npm run build`
6. **Commit and push:**
   ```bash
   git add frontend/app/connections/page.tsx
   git commit -m "fix: missing closing div tag in batch operations error display"
   git push origin main
   ```

**Example Fix (Real Case):**
```tsx
{/* BEFORE (BROKEN) */}
<div className="text-xs mt-1">
  {op.error ? <div>...</div> : <div>...</div>}
</div>  {/* This closes PARENT div, not "text-xs mt-1" div! */}

{/* AFTER (FIXED) */}
<div className="text-xs mt-1">
  {op.error ? <div>...</div> : <div>...</div>}
</div>  {/* Closes "text-xs mt-1" div */}
</div>  {/* Closes parent div */}
```

**Prevention:**
- Use editor with JSX tag matching/highlighting (VS Code, WebStorm)
- Run `npm run build` locally before pushing
- Watch for cascading errors in TypeScript output (first error is usually root cause)

---

### TLS: Admin Subdomain Shows TRAEFIK DEFAULT CERT (Let's Encrypt Missing)

**Purpose:** Diagnose and fix admin.fewo.kolibri-visions.de (or other subdomains) serving Traefik's default certificate instead of a valid Let's Encrypt certificate.

#### Symptoms

**Browser:**
- Certificate warning: "Your connection is not private" or "Invalid certificate"
- Certificate issuer shown as "TRAEFIK DEFAULT CERT" instead of "Let's Encrypt"

**CLI Verification (HOST-SERVER-TERMINAL):**
```bash
# Check certificate for admin subdomain
echo | openssl s_client -connect admin.fewo.kolibri-visions.de:443 \
  -servername admin.fewo.kolibri-visions.de 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates

# Output with TRAEFIK DEFAULT CERT:
# subject=CN = TRAEFIK DEFAULT CERT
# issuer=CN = TRAEFIK DEFAULT CERT
# notBefore=...
# notAfter=...
```

**Compare to Working Host (api.fewo.kolibri-visions.de):**
```bash
echo | openssl s_client -connect api.fewo.kolibri-visions.de:443 \
  -servername api.fewo.kolibri-visions.de 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates

# Expected output with Let's Encrypt:
# subject=CN = api.fewo.kolibri-visions.de
# issuer=C = US, O = Let's Encrypt, CN = R13
# notBefore=...
# notAfter=...
```

#### Root Causes

**A) Router Rule Parse Error → Router Not Loaded → Default Cert**

Traefik fails to parse the router rule, so the router is never registered, and Traefik falls back to the default certificate.

Common Traefik log errors:
```
level=error msg="Router rule parse error: expected operand, found '/'"
level=error msg="PathPrefix: path does not start with a '/'"
level=error msg="invalid rule syntax"
```

**Typical Mistakes:**
- Using hostname in PathPrefix: `PathPrefix(admin.fewo.kolibri-visions.de)` ❌
- Missing backticks: `PathPrefix(/)` ❌
- Correct syntax: `PathPrefix(\`/\`)` ✅ (with backticks)
- Best practice: Use `Host(\`admin.fewo...\`)` alone, no PathPrefix needed for single-domain apps

**B) Missing Certificate Resolver for Router**

Router has `tls=true` but no `tls.certresolver` label, so Traefik does not request/attach a Let's Encrypt certificate for this hostname and falls back to the default certificate.

#### Diagnosis Steps

**1. Check Current Certificate (HOST-SERVER-TERMINAL):**
```bash
echo | openssl s_client -connect admin.fewo.kolibri-visions.de:443 \
  -servername admin.fewo.kolibri-visions.de 2>/dev/null \
  | openssl x509 -noout -subject -issuer

# If subject/issuer = "TRAEFIK DEFAULT CERT": Problem confirmed
```

**2. Confirm Traefik Proxy Container and Cert Resolver Name (HOST-SERVER-TERMINAL):**
```bash
# List Traefik/proxy containers
docker ps --format 'table {{.Names}}\t{{.Image}}' | egrep -i 'proxy|traefik'
# Expected: coolify-proxy (or similar)

# Inspect Traefik args to find cert resolver name
docker inspect coolify-proxy --format '{{range .Args}}{{println .}}{{end}}' \
  | egrep -i 'certificatesresolvers|acme' | head -n 20

# Look for lines like:
# --certificatesresolvers.letsencrypt.acme.email=...
# --certificatesresolvers.letsencrypt.acme.storage=...
# Resolver name is "letsencrypt" in this example
```

**3. Inspect pms-admin Container Labels and Router Rules (HOST-SERVER-TERMINAL):**
```bash
# View Traefik labels on pms-admin
docker inspect pms-admin --format 'Labels={{json .Config.Labels}}' \
  | python3 -m json.tool | grep -A 2 -B 2 traefik | head -n 100

# Check for:
# - traefik.http.routers.pmsadmin-https.rule: Should be Host(`admin.fewo...`)
# - traefik.http.routers.pmsadmin-https.tls: Should be "true"
# - traefik.http.routers.pmsadmin-https.tls.certresolver: Should be "letsencrypt" (or resolver name from step 2)

# Common issues:
# - Rule syntax error: PathPrefix(/) instead of PathPrefix(`/`)
# - Missing tls.certresolver label
```

**4. Check Traefik Logs for Errors (HOST-SERVER-TERMINAL):**
```bash
# Grep Traefik logs for admin subdomain and errors
docker logs --since 48h coolify-proxy 2>&1 \
  | egrep -i 'admin\.fewo\.kolibri-visions\.de|acme|letsencrypt|certificate|tls|router|rule|error' \
  | tail -n 100

# Look for:
# - Rule parsing errors: "expected operand", "PathPrefix: path does not start with a '/'"
# - ACME errors: "unable to obtain certificate", "DNS challenge failed"
# - Router registration: "Creating router pmsadmin-https" (should appear if rule is valid)
```

#### Fix Steps (Coolify UI)

**1. Fix Invalid Router Rules:**

Location: Coolify Dashboard → pms-admin → Domains

- **If using Host-only rule (recommended for single-domain apps):**
  - Rule: `Host(\`admin.fewo.kolibri-visions.de\`)`
  - No PathPrefix needed

- **If PathPrefix is needed (e.g., for path-based routing):**
  - Correct: `Host(\`admin.fewo...\`) && PathPrefix(\`/\`)`
  - Incorrect: `PathPrefix(/)` (missing backticks)
  - Incorrect: `PathPrefix(admin.fewo...)` (hostname in PathPrefix)

**2. Explicitly Set Certificate Resolver on HTTPS Router:**

Location: Coolify Dashboard → pms-admin → Environment Variables or Labels

Add container label (or verify it exists):
```
traefik.http.routers.pmsadmin-https.tls.certresolver=letsencrypt
```

**Important:** Resolver name (`letsencrypt`) must match the name from step 2 diagnosis. Common names: `letsencrypt`, `le`, `default`.

**3. Redeploy pms-admin (NOT Just Restart):**

Location: Coolify Dashboard → pms-admin → Deployments

- Action: Click "Redeploy"
- Why: Container labels are set during build/deploy; restart does not update labels
- Note: Domain changes also require redeploy, not just restart

**4. Wait for Certificate Issuance (30-60 seconds):**

- Traefik will automatically request Let's Encrypt certificate for the hostname
- Check Traefik logs for ACME progress:
  ```bash
  docker logs --since 5m coolify-proxy 2>&1 | grep -i acme
  ```
- Look for: "Certificate obtained for domain admin.fewo..."

#### Verification

**1. Check Certificate via OpenSSL (HOST-SERVER-TERMINAL):**
```bash
echo | openssl s_client -connect admin.fewo.kolibri-visions.de:443 \
  -servername admin.fewo.kolibri-visions.de 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates

# Expected output with Let's Encrypt:
# subject=CN = admin.fewo.kolibri-visions.de
# issuer=C = US, O = Let's Encrypt, CN = R13
# notBefore=Dec 29 12:00:00 2025 GMT
# notAfter=Mar 29 12:00:00 2026 GMT  (90 days validity)
```

**2. Check Browser:**
- Open https://admin.fewo.kolibri-visions.de
- Click lock icon → Certificate → Verify issuer is "Let's Encrypt"
- No certificate warnings

**3. Optional: Verify Traefik Logs Show No Rule Errors (HOST-SERVER-TERMINAL):**
```bash
docker logs --since 10m coolify-proxy 2>&1 \
  | grep -i admin.fewo | grep -i error

# Expected: No output (no errors for admin.fewo router)
```

#### Related Issues

- If certificate still shows TRAEFIK DEFAULT CERT after fix:
  - Check DNS: `nslookup admin.fewo.kolibri-visions.de` (must resolve to server IP)
  - Check firewall: Port 443 must be open
  - Check Traefik ACME logs for challenge failures
- If router rule still invalid:
  - Review Traefik documentation: https://doc.traefik.io/traefik/routing/routers/
  - Test rule syntax in isolation before deploying

---

## Monitoring & Troubleshooting

**Purpose:** Monitor system health and troubleshoot Channel Manager issues.

### Health Endpoints

#### GET /health

**Purpose:** Basic application health check
**Auth:** None required
**Response:**
```json
{
  "status": "healthy"
}
```

#### GET /health/ready

**Purpose:** Comprehensive readiness check (database, Redis, Celery)
**Auth:** None required
**Response:**
```json
{
  "status": "ready",
  "checks": {
    "database": "up",
    "redis": "up",
    "celery": "up"
  },
  "celery_workers": [
    "celery@pms-worker-abc123"
  ]
}
```

**Possible Status Values:**
- `ready`: All checks passed
- `degraded`: Some checks failed

**Individual Check Status:**
- `up`: Component healthy
- `down`: Component unavailable

**Single-Worker Enforcement (Celery):**

When `ENABLE_CELERY_HEALTHCHECK=true`, the readiness check enforces the single-worker rule for Channel Manager:

- **Expected:** Exactly 1 active Celery worker (pms-worker-v2)
- **If Multiple Workers Detected:** `celery` component returns `status: "down"` with error message
- **Error Message Includes:**
  - Worker count (expected: 1, found: N)
  - Worker names (e.g., "celery@pms-worker-v2-abc123, celery@pms-worker-old-xyz789")
  - Fix instructions (stop extra workers)

**Why Single-Worker Rule:**
- Multiple workers cause duplicate sync tasks (same operation executed 2-3x)
- Race conditions when updating sync log status
- Duplicate log entries in `channel_sync_logs` table
- Inconsistent batch status (some ops "success", others "running" for same batch)

**Fix Multiple Workers:**

```bash
# Check running workers (HOST-SERVER-TERMINAL)
docker ps | grep pms-worker

# Expected output: Only pms-worker-v2 should be listed
# 1a2b3c4d5e6f   ghcr.io/your-org/pms-worker-v2:main   ...   pms-worker-v2

# If multiple workers found:
docker stop <old_worker_container_id>

# Verify only one worker remains
docker ps | grep pms-worker

# Verify health check passes
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq '.components.celery'
# Expected: {"status": "up", "details": {"workers": ["celery@pms-worker-v2-..."]}}
```

**Related:**
- See [Single Worker Rule](#single-worker-rule-critical) for deployment guidelines
- See [Duplicate Sync Tasks](#duplicate-sync-tasks) for troubleshooting duplicate tasks

#### HEAD Support for Health Endpoints

Both `/health` and `/health/ready` support **HEAD** requests for lightweight monitoring.

**Purpose:** External monitors (uptime checkers, load balancers) can use HEAD to check status without fetching response body.

**Behavior:**
- Returns same HTTP status code as GET (200 when healthy, 503 when unhealthy)
- Empty response body (no JSON payload)
- Same logic as GET endpoints (checks DB/Redis/Celery based on feature flags)

**Examples:**

```bash
# HEAD request to /health (always returns 200)
curl -k -I https://api.fewo.kolibri-visions.de/health

# HEAD request to /health/ready (returns 200 when up, 503 when down)
curl -k -I https://api.fewo.kolibri-visions.de/health/ready

# Compare with GET (includes response body)
curl -k https://api.fewo.kolibri-visions.de/health/ready
```

**Expected Responses:**

```bash
# HEAD /health (liveness - always 200)
HTTP/2 200
content-length: 0

# HEAD /health/ready (readiness - 200 when healthy)
HTTP/2 200
content-length: 0

# HEAD /health/ready (readiness - 503 when DB down)
HTTP/2 503
content-length: 0
```

**Troubleshooting:**

If HEAD returns **405 Method Not Allowed** with `Allow: GET` header:
- You are running an older backend version without HEAD support
- Update to commit `62d7c80` or later for HEAD support
- Workaround: Use GET instead (less efficient for monitors)

---

### Monitoring Strategy

**Automated Monitoring (Recommended):**

```bash
# Set up cron job to check health every minute
* * * * * curl -f https://api.your-domain.com/health/ready || echo "Health check failed" | mail -s "PMS Alert" ops@example.com
```

**Manual Monitoring:**

```bash
# Quick health check
watch -n 10 'curl -s https://api.your-domain.com/health/ready | jq .'

# Monitor sync log failures
watch -n 30 'curl -s https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?limit=5 -H "Authorization: Bearer TOKEN" | jq ".logs[] | select(.status==\"failed\")"'
```

---

### HEAD vs GET for Health Monitoring

**Purpose:** Understand when to use HEAD (status-only) vs GET (JSON body) for health checks.

**Use Cases:**

- **HEAD (Status-Only):**
  - Uptime monitors, load balancers, Kubernetes probes
  - Lightweight checks (no response body parsing)
  - Returns HTTP status code + headers only
  - Same logic as GET, but no JSON payload

- **GET (JSON Body):**
  - Debugging, troubleshooting, manual checks
  - Full component status details (DB, Redis, Celery)
  - Useful for identifying which component failed

**Production Examples:**

```bash
# HEAD /health (liveness - always 200, no body)
curl -k -sS -I https://api.fewo.kolibri-visions.de/health

# Expected output:
HTTP/2 200
content-type: application/json
content-length: 0

# HEAD /health/ready (readiness - 200 when up, 503 when down, no body)
curl -k -sS -I https://api.fewo.kolibri-visions.de/health/ready

# Expected output when healthy:
HTTP/2 200
content-type: application/json
content-length: 0

# Expected output when degraded (DB down):
HTTP/2 503
content-type: application/json
content-length: 0

# GET /health/ready (readiness - returns JSON body for debugging)
curl -k -sS https://api.fewo.kolibri-visions.de/health/ready

# Expected output when healthy:
{
  "status": "up",
  "components": {
    "db": {"status": "up", "checked_at": "2026-01-01T12:00:00Z"},
    "redis": {"status": "up", "details": {"skipped": true}},
    "celery": {"status": "up", "details": {"skipped": true}}
  },
  "checked_at": "2026-01-01T12:00:00Z"
}

# Expected output when degraded (DB down):
{
  "status": "down",
  "components": {
    "db": {"status": "down", "error": "connection refused", "checked_at": "..."},
    "redis": {"status": "up", "details": {"skipped": true}},
    "celery": {"status": "up", "details": {"skipped": true}}
  },
  "checked_at": "2026-01-01T12:00:00Z"
}
```

**Key Points:**

- HEAD and GET return the **same HTTP status code** (200 or 503)
- HEAD has **no response body** (content-length: 0)
- GET includes **full JSON payload** with component details
- `/health` (liveness) always returns 200 (application is running)
- `/health/ready` (readiness) returns 503 if DB is down (mandatory dependency)
- Redis and Celery are optional (controlled by `ENABLE_REDIS_HEALTHCHECK` and `ENABLE_CELERY_HEALTHCHECK`)

**When to Use:**

| Scenario | Method | Endpoint | Why |
|----------|--------|----------|-----|
| Uptime monitoring | HEAD | `/health/ready` | Lightweight, status-only |
| Load balancer probe | HEAD | `/health/ready` | Fast, no body parsing |
| K8s liveness probe | HEAD | `/health` | Minimal overhead |
| K8s readiness probe | HEAD | `/health/ready` | Status-only check |
| Debugging failed health | GET | `/health/ready` | See which component failed |
| Manual verification | GET | `/health/ready` | Human-readable JSON |

---

### Celery Worker Singleton (Important)

**Rule:** Only **ONE** Celery worker service must be active at any time.

**Current Worker:** `pms-worker-v2` (Coolify app)

**Why This Matters:**

Running multiple Celery workers simultaneously causes:
- **Duplicate sync tasks:** Same sync operation executed multiple times
- **Duplicate log entries:** Multiple workers writing to `channel_sync_logs`
- **Inconsistent batch status:** Race conditions when updating sync log status
- **Resource waste:** Unnecessary DB/Redis connections

**Symptoms of Violation:**

- Sync logs show duplicate entries with different `task_id` for the same operation
- Batch status shows inconsistent results (some ops "success", others "running" for same batch)
- Channel sync operations trigger 2-3x expected tasks
- Worker logs show multiple workers picking up same task

**Verification (HOST-SERVER-TERMINAL):**

```bash
# Check running workers
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' | egrep -i 'pms-worker' || true

# Expected output (ONLY ONE worker running):
pms-worker-v2    Up 2 hours    ghcr.io/...

# Check all workers (including stopped)
docker ps -a --format 'table {{.Names}}\t{{.Status}}' | egrep -i 'pms-worker' || true

# Expected output:
pms-worker-v2    Up 2 hours
pms-worker       Exited (0) 3 days ago     <- OLD, should stay stopped

# If multiple workers are running (BAD):
pms-worker-v2    Up 2 hours
pms-worker       Up 5 minutes              <- PROBLEM! Stop this immediately
```

**Remediation:**

If multiple workers are running:

```bash
# 1. Stop the old worker immediately
docker stop pms-worker

# 2. Verify only pms-worker-v2 is running
docker ps | grep pms-worker

# 3. In Coolify:
#    - Navigate to old worker app (pms-worker)
#    - Click "Stop" or "Disable"
#    - Ensure "Auto Deploy" is OFF
#    - This prevents it from restarting on deploy
```

**Coolify Configuration:**

1. **Active Worker:** `pms-worker-v2`
   - Status: Running
   - Auto Deploy: ON
   - Health Check: Enabled

2. **Old Workers:** `pms-worker` (if exists)
   - Status: Stopped/Disabled
   - Auto Deploy: **OFF** (critical - prevents accidental restart)
   - Action: Archive or delete if no longer needed

**Deployment Best Practice:**

When deploying a new worker version:
1. Stop old worker first
2. Deploy new worker
3. Verify new worker is running (docker ps)
4. Disable auto-deploy on old worker in Coolify
5. Test sync operations (check for duplicates)

---

### Stale Sync Logs (Automatic Cleanup)

**Purpose:** Understand automatic cleanup of stale sync logs to maintain UI cleanliness.

**What Are Stale Logs?**

Sync logs stuck in `triggered` or `running` status for longer than the threshold (default: 60 minutes).

**Common Causes:**

- **Worker restart:** Celery worker restarted mid-task (deployment, crash, OOM kill)
- **DB disconnect:** Worker lost database connection during task execution
- **Redis disconnect:** Worker lost Redis connection (broker/result backend)
- **Task timeout:** Task exceeded Celery soft/hard time limits
- **Manual intervention:** Task manually revoked/terminated in Celery

**Automatic Cleanup Behavior:**

On every sync trigger (POST `/api/v1/channel-connections/{id}/sync`), the system:
1. Identifies logs for that connection older than `SYNC_LOG_STALE_MINUTES`
2. Marks them as `status='failed'`
3. Sets `error` field to: "Marked stale (no update for X minutes). Likely worker restart or lost DB connection."
4. Updates `updated_at` timestamp

**Configuration:**

```bash
# Environment variable (optional, defaults to 60)
SYNC_LOG_STALE_MINUTES=60

# Default: 60 minutes
# Increase if tasks legitimately take longer (e.g., large full syncs)
# Decrease for faster UI cleanup (not recommended < 30 minutes)
```

**Verification (Supabase SQL Editor):**

```sql
-- Check for currently stale logs (before cleanup)
SELECT
  id,
  connection_id,
  operation_type,
  status,
  created_at,
  updated_at,
  NOW() - COALESCE(updated_at, created_at) AS age,
  error
FROM channel_sync_logs
WHERE
  status IN ('triggered', 'running')
  AND COALESCE(updated_at, created_at) < NOW() - INTERVAL '60 minutes'
ORDER BY created_at DESC
LIMIT 20;

-- Check recently auto-cleaned logs
SELECT
  id,
  connection_id,
  operation_type,
  status,
  error,
  updated_at
FROM channel_sync_logs
WHERE
  status = 'failed'
  AND error LIKE 'Marked stale%'
ORDER BY updated_at DESC
LIMIT 20;
```

**Troubleshooting:**

If stale logs occur frequently:

1. **Check worker logs** for crashes or OOM kills:
   ```bash
   # Coolify: pms-worker-v2 → Logs
   # Look for: "Worker shutdown", "MemoryError", "Killed"
   docker logs pms-worker-v2 | grep -i "error\|killed\|shutdown" | tail -50
   ```

2. **Check worker health** (should be running):
   ```bash
   docker ps | grep pms-worker-v2
   ```

3. **Verify Redis connection** (worker needs Redis for task queue):
   ```bash
   # From worker container
   docker exec pms-worker-v2 redis-cli -h redis-host PING
   # Expected: PONG
   ```

4. **Check Celery worker concurrency** (may be overloaded):
   ```bash
   # Coolify env: CELERY_WORKER_CONCURRENCY
   # Default: 4 (increase if tasks timeout frequently)
   ```

5. **Review task timeouts** (may be too aggressive):
   ```python
   # In celery.py or task definition
   soft_time_limit = 300  # 5 minutes
   time_limit = 600       # 10 minutes hard limit
   ```

**When to Investigate:**

- **Occasional stale logs (< 5% of syncs):** Normal after deployments/restarts
- **Frequent stale logs (> 10% of syncs):** Worker stability issue - investigate logs
- **All syncs stale:** Worker offline or not processing tasks - check deployment

**Related:**

- See [Celery Worker Singleton](#celery-worker-singleton-important) for worker management
- See [Worker Logs](#worker-logs) for debugging task failures

---

### Troubleshooting Sync Log Issues

#### Issue: Sync Logs Not Persisting

**Symptom:**
- POST `/availability/sync` returns 200
- GET `/sync-logs` shows no entries or 503 error

**Diagnosis:**
```bash
# Check if channel_sync_logs table exists
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  -c "\dt channel_sync_logs"

# Expected: Table listing
# If not found: Migration not applied
```

**Solution:**
```bash
# Apply migration
cd supabase/migrations
docker exec $(docker ps -q -f name=supabase) supabase migration up

# Verify
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres \
  -c "SELECT COUNT(*) FROM channel_sync_logs;"
```

---

#### Issue: Sync Logs Show "failed" Status

**Symptom:**
- All syncs marked as "failed" in logs
- Worker logs show errors

**Diagnosis:**
```bash
# Get failed log details
curl -s https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?limit=10 \
  -H "Authorization: Bearer TOKEN" | jq '.logs[] | select(.status=="failed")'

# Check worker logs for exceptions
docker logs pms-worker --tail 100 | grep -i error
```

**Common Causes & Solutions:**

**1. Database Connection Error:**
```
Solution: Check DATABASE_URL in worker environment
```

**2. Missing Environment Variables:**
```bash
# Compare worker env with backend
docker exec pms-backend env | grep -E "DATABASE_URL|JWT_SECRET|ENCRYPTION_KEY" | sort > /tmp/backend-env.txt
docker exec pms-worker env | grep -E "DATABASE_URL|JWT_SECRET|ENCRYPTION_KEY" | sort > /tmp/worker-env.txt
diff /tmp/backend-env.txt /tmp/worker-env.txt

# Any differences? Add missing vars to worker
```

**3. Code Version Mismatch:**
```bash
# Check git commits match
docker exec pms-backend git rev-parse HEAD
docker exec pms-worker git rev-parse HEAD

# If different: Redeploy worker
```

---

#### Issue: Retry Count Not Updating

**Symptom:**
- Sync fails but retry_count stays at 0
- No retry attempts logged

**Diagnosis:**
```bash
# Check if Celery task has retry configured
docker exec pms-worker celery -A app.channel_manager.core.sync_engine:celery_app inspect registered | grep update_channel

# Should show: max_retries=3
```

**Solution:**
- Verify task decorator has `@celery_app.task(bind=True, max_retries=3)`
- Redeploy worker if code changes needed

---

#### Issue: Bookings Sync Logs Missing (HTTP 503 on Constraint Violation)

**Symptom:**
- POST `/channel-connections/{id}/sync` with `sync_type=bookings` returns HTTP 503
- API returns: "Database schema out of date: channel_sync_logs.operation_type constraint blocks 'bookings'"
- OR: Task executes successfully but no logs appear (silent failure)
- Worker logs: "DB constraint violation creating sync log" or "No sync log found for task_id=..."

**Root Cause:**
The `channel_sync_logs.operation_type` CHECK constraint doesn't allow `bookings_sync` (only allows `bookings_import`), but backend code uses `operation_type='bookings_sync'` when triggering bookings imports.

**Diagnosis:**
```bash
# Check current constraint definition
docker exec $(docker ps -q -f name=supabase-db) psql -U postgres -d postgres -c \
  "SELECT pg_get_constraintdef(oid) FROM pg_constraint
   WHERE conrelid = 'public.channel_sync_logs'::regclass
   AND conname = 'channel_sync_logs_operation_type_check';"

# Expected (before fix): Shows only 'bookings_import' (missing 'bookings_sync')
# Expected (after fix):  Shows both 'bookings_import' and 'bookings_sync' + pattern matching
```

**Solution:**
```bash
# Apply migration to fix constraint
cd /path/to/pms-webapp
supabase migration up --file supabase/migrations/20260101140000_fix_channel_sync_logs_operation_type_check.sql

# Verify constraint updated
docker exec $(docker ps -q -f name=supabase-db) psql -U postgres -d postgres -c \
  "SELECT pg_get_constraintdef(oid) FROM pg_constraint
   WHERE conrelid = 'public.channel_sync_logs'::regclass
   AND conname = 'channel_sync_logs_operation_type_check';"

# Test bookings sync
bash backend/scripts/pms_channel_sync_poll.sh --sync-type bookings --poll-limit 30

# Expected: Sync succeeds, logs show operation_type=bookings_sync
```

**Migration Details:**
- **File:** `supabase/migrations/20260101140000_fix_channel_sync_logs_operation_type_check.sql`
- **Action:** Drops old constraint and recreates with:
  - Explicit support for `bookings_sync` and `bookings_import`
  - Pattern matching for future-proofing: `booking%` and `bookings%`
- **Idempotent:** Safe to run multiple times (uses `IF EXISTS` checks)

**Backend Behavior After Fix:**
- **Before migration:** API returns HTTP 503 with actionable error message (fail-fast)
- **After migration:** API returns HTTP 200, Celery task executes, logs are created

**Related Files:**
- `backend/app/services/channel_sync_log_service.py` (catches CheckViolationError and re-raises)
- `backend/app/api/routers/channel_connections.py` (returns 503 on constraint violations)

---

### Alert Thresholds

**Recommended Alert Rules:**

| Metric | Threshold | Action |
|--------|-----------|--------|
| `/health/ready` status | degraded | Investigate immediately |
| Failed sync logs | >10% in 1 hour | Check worker logs |
| Celery workers | 0 workers | Restart pms-worker |
| Database response time | >500ms | Check Supabase load |
| Redis response time | >100ms | Check Redis container |

---

### Troubleshooting Inventory Conflicts

#### Database-Level Exclusion Constraints (Source of Truth)

**Overview:**

The PMS uses PostgreSQL exclusion constraints to prevent inventory conflicts (double-bookings, overlapping blocks) at the database level. This is the **source of truth** for inventory management and provides race-safe protection under high concurrency.

**Constraints Enforced:**

1. **`bookings.no_double_bookings`**
   - Prevents overlapping bookings for same property within agency
   - Scope: `(agency_id, property_id, daterange)`
   - Excludes: `cancelled`, `declined`, `no_show` statuses
   - Uses: `[)` end-exclusive daterange semantics

2. **`availability_blocks.availability_blocks_no_overlap`**
   - Prevents overlapping blocks for same property
   - Scope: `(property_id, daterange)`
   - Uses: `[)` end-exclusive daterange semantics

3. **`inventory_ranges.inventory_ranges_no_overlap`**
   - Prevents overlapping inventory holds
   - Scope: `(property_id, daterange)` for active ranges only
   - Uses: `[)` end-exclusive daterange semantics

**Date Semantics:**

All constraints use `[)` end-exclusive semantics:
- `check_in` / `start_date`: **Included** (occupied)
- `check_out` / `end_date`: **Excluded** (available)
- **Back-to-back bookings allowed**: Booking A `check_out` = Booking B `check_in`

**Example:**
```
Booking A: 2026-01-10 to 2026-01-12  (occupies: Jan 10, Jan 11)
Booking B: 2026-01-12 to 2026-01-14  (occupies: Jan 12, Jan 13)
Result: ✓ Both allowed (Jan 12 is available for Booking B)
```

**Inquiry Bookings Policy (Non-Blocking):**

As of 2026-01-03, inquiry bookings (`status='inquiry'`) are **non-blocking** for both availability checks and booking creation:

- **Availability API** (`GET /api/v1/availability`): Does NOT show inquiry bookings as blocked ranges
- **Booking Creation** (`POST /api/v1/bookings`): Does NOT treat inquiry bookings as conflicts (409)
- **Rationale**: Inquiry bookings are preliminary/tentative and should not prevent confirmed reservations

**Non-Blocking Statuses:**
- `cancelled` - Cancelled bookings
- `declined` - Declined bookings
- `no_show` - No-show bookings
- `inquiry` - Inquiry/tentative bookings (as of 2026-01-03)

**Blocking Statuses:**
- `confirmed` - Confirmed reservations
- `pending` - Pending confirmation
- `checked_in` - Active stays
- `checked_out` - Completed stays (historical data)

**Database Implementation:**
- `inventory_ranges` table uses `source_id` (UUID) and `kind` (enum) to reference bookings/blocks
- No `booking_id` or `block_id` columns exist in `inventory_ranges`
- API responses may present `booking_id`/`block_id` derived from `source_id` + `kind` for client convenience

**Source of Truth for Availability (2026-01-03 Update):**

Both availability API and booking creation now use `inventory_ranges` as the **single source of truth** for overlap detection:

- **Availability API**: Queries `inventory_ranges` with `state='active'` to return blocked ranges
- **Booking Creation**: `check_availability()` queries `inventory_ranges` (not bookings table) to detect conflicts
- **Consistency**: This ensures both APIs treat inquiry bookings identically (non-blocking)
- **How It Works**:
  - Inquiry bookings: Created in `bookings` table but do NOT create `inventory_ranges` entries
  - Confirmed bookings: Create both `bookings` entry AND `inventory_ranges` entry with `state='active'`
  - Blocks: Create `availability_blocks` entry AND `inventory_ranges` entry with `state='active'`
  - Exclusion constraint on `inventory_ranges` provides race-safe overlap protection

**Troubleshooting: "Free Window" but All 409s:**

If availability API shows a window as free (`ranges=[]`) but booking creation returns 409 for all requests:

1. Check for inquiry bookings overlapping the window:
   ```sql
   SELECT id, status, check_in, check_out
   FROM bookings
   WHERE property_id = 'your-property-uuid'
     AND status = 'inquiry'
     AND daterange(check_in, check_out, '[)') && daterange('2026-01-10', '2026-01-12', '[)');
   ```

2. Verify inquiry bookings do NOT have `inventory_ranges` entries:
   ```sql
   SELECT ir.*
   FROM inventory_ranges ir
   JOIN bookings b ON ir.source_id = b.id
   WHERE b.status = 'inquiry'
     AND ir.state = 'active';
   -- Should return 0 rows (inquiry should not create active ranges)
   ```

3. If inquiry bookings ARE blocking (incorrect behavior):
   - Verify backend code uses `inventory_ranges` query in `check_availability()`
   - Check for stale code that queries `bookings` table directly
   - Ensure migration created `inventory_ranges` properly

#### Issue: HTTP 409 with `conflict_type=inventory_overlap`

**Symptom:**
- POST `/api/v1/bookings` returns 409 Conflict
- Response body: `{"detail": "Property is already booked for these dates", "conflict_type": "inventory_overlap"}`
- Or: `{"detail": "Property is already occupied for dates...", "conflict_type": "inventory_overlap"}`

**Root Cause:**

Database exclusion constraint detected overlapping dates:
- Another booking/block exists for same property and overlapping dates
- Application-level checks passed, but DB constraint fired (race condition)
- Constraint provides **definitive** conflict detection (no false negatives)

**Diagnosis:**

```bash
# Check for overlapping bookings in same property
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres -c "
  SELECT
    id,
    property_id,
    check_in,
    check_out,
    status,
    created_at
  FROM bookings
  WHERE property_id = '<property-uuid>'
    AND status NOT IN ('cancelled', 'declined', 'no_show')
    AND daterange(check_in, check_out, '[)') && daterange('2026-01-10', '2026-01-12', '[)')
  ORDER BY check_in;
"

# Check for overlapping availability blocks
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres -c "
  SELECT
    id,
    property_id,
    start_date,
    end_date,
    created_at
  FROM availability_blocks
  WHERE property_id = '<property-uuid>'
    AND daterange(start_date, end_date, '[)') && daterange('2026-01-10', '2026-01-12', '[)')
  ORDER BY start_date;
"

# Check for overlapping inventory ranges
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres -c "
  SELECT
    id,
    property_id,
    start_date,
    end_date,
    kind,
    state,
    created_at
  FROM inventory_ranges
  WHERE property_id = '<property-uuid>'
    AND state = 'active'
    AND daterange(start_date, end_date, '[)') && daterange('2026-01-10', '2026-01-12', '[)')
  ORDER BY start_date;
"
```

**Expected Behavior:**

- HTTP 409 is **correct** when overlap exists
- Clients should retry with different dates or cancel conflicting booking/block
- This is **not an error** — it's race-safe conflict prevention working as designed

**Conflict Type Semantics:**

The `conflict_type` field distinguishes between different overlap causes:

| conflict_type | Meaning | Example Scenario |
|---------------|---------|------------------|
| `inventory_overlap` | Overlap with **availability block** | Admin blocks Jan 10-12 for maintenance. Guest tries to book Jan 10-12 → HTTP 409 with `conflict_type=inventory_overlap` |
| `double_booking` | Overlap with **existing booking** | Guest A books Jan 10-12. Guest B tries to book Jan 10-12 → HTTP 409 with `conflict_type=double_booking` |

**Detection Logic:**
- When availability check fails, API queries `availability_blocks` table to determine conflict source
- If overlapping block found → `conflict_type=inventory_overlap`
- If no block found → `conflict_type=double_booking` (must be booking overlap)
- This allows clients to provide context-aware error messages (e.g., "Property is blocked for maintenance" vs "Property is already booked")

**Example Response (Availability Block Conflict):**
```json
{
  "detail": "Property is already booked for these dates",
  "conflict_type": "inventory_overlap"
}
```

**Example Response (Booking Overlap):**
```json
{
  "detail": "Property is already booked for these dates",
  "conflict_type": "double_booking"
}
```

**Common Issues:**

*HTTP 500 on booking creation after conflict-type detection changes:*
- **Symptom:** POST `/api/v1/bookings` returns HTTP 500 instead of expected 409 when overlapping availability block
- **Error in logs:** `NameError: name 'conn' is not defined` in BookingService.create_booking()
- **Root cause:** Conflict detection pre-check uses undefined database connection variable (`conn` instead of `self.db`)
- **Location:** `booking_service.py` availability block query in pre-check or update paths
- **Fix:** Replace `await conn.fetchrow(...)` with `await self.db.fetchrow(...)` in all block overlap queries
- **Expected behavior:** Should return HTTP 409 with `conflict_type=inventory_overlap` for block overlaps

**Verify Constraints Exist:**

```bash
# List all exclusion constraints
docker exec $(docker ps -q -f name=supabase) psql -U postgres -d postgres -c "
  SELECT
    conrelid::regclass AS table_name,
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS definition
  FROM pg_constraint
  WHERE contype = 'x'  -- exclusion constraint
    AND connamespace = 'public'::regnamespace
  ORDER BY conrelid::regclass::text;
"
```

**Expected Output:**
```
table_name          | constraint_name                     | definition
--------------------+-------------------------------------+---------------------------
bookings            | no_double_bookings                  | EXCLUDE USING gist (agency_id WITH =, property_id WITH =, daterange(check_in, check_out, '[)'::text) WITH &&) WHERE ((status <> ALL (ARRAY['cancelled'::text, 'declined'::text, 'no_show'::text])))
availability_blocks | availability_blocks_no_overlap      | EXCLUDE USING gist (property_id WITH =, daterange(start_date, end_date, '[)'::text) WITH &&)
inventory_ranges    | inventory_ranges_no_overlap         | EXCLUDE USING gist (property_id WITH =, daterange(start_date, end_date, '[)'::text) WITH &&) WHERE ((state = 'active'::text))
```

**Migration:**

Constraints added via migration: `supabase/migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql`

**Error Handling:**

Application code catches `asyncpg.exceptions.ExclusionViolationError` (SQLSTATE 23P01) and maps to:
- HTTP 409 Conflict
- `conflict_type=inventory_overlap`
- Human-readable error message

**Locations:**
- `backend/app/services/booking_service.py:678` (booking creation)
- `backend/app/services/availability_service.py:325` (inventory_range creation)
- `backend/app/services/availability_service.py:404` (inventory_range update)

#### Testing Race-Safe Behavior (Concurrency Test)

**Script:** `backend/scripts/pms_booking_concurrency_test.sh`

**Purpose:** Validate that exclusion constraints prevent double-bookings under concurrent requests.

**What it does:**
- Fires N parallel POST /bookings requests (default: 10) to same property/dates
- Expects exactly **1 success** (HTTP 201) and **N-1 conflicts** (HTTP 409)
- Validates DB-level race-safe inventory management

**Usage:**
```bash
# Basic usage (auto-picks property)
export ENV_FILE=/root/pms_env.sh
bash scripts/pms_booking_concurrency_test.sh

# With explicit property and dates
export PID="your-property-uuid"
export FROM="2026-06-01"
export TO="2026-06-03"
bash scripts/pms_booking_concurrency_test.sh
```

**Important:** If you see **HTTP 401 "Token has expired"**, re-fetch your TOKEN:
```bash
source /root/pms_env.sh
bash scripts/pms_phase23_smoke.sh  # Auto-fetches token
# OR manually fetch token (see script output for instructions)
```

**Expected PASS:**
- Exactly 1 booking succeeds (201)
- All other requests rejected with 409 `inventory_overlap`
- No double-booking occurred

**See:** `backend/scripts/README.md` for full documentation.

---

### Booking Concurrency Deadlocks

**Symptom:**
- POST `/api/v1/bookings` returns HTTP 503 (not 500!) with message "Database deadlock detected. Please retry your request."
- Multiple concurrent booking requests for the same property may trigger PostgreSQL deadlock errors

**Root Cause:**

Under high concurrency, multiple booking requests for the same property can trigger PostgreSQL deadlocks due to:
1. Exclusion constraint checks (`bookings.no_double_bookings`)
2. Foreign key constraint checks (property_id, guest_id)
3. Multiple transactions acquiring locks in different orders

**Prevention (Implemented):**

The application prevents deadlocks using a two-layer approach:

1. **Advisory Lock Serialization** (`booking_service.py:470-475`)
   - Each booking transaction acquires a PostgreSQL advisory lock scoped to the property ID
   - Lock is transaction-scoped (automatically released on commit/rollback)
   - Serializes concurrent bookings for the same property (no deadlocks)

2. **Automatic Retry with Exponential Backoff** (`booking_service.py:84-121`)
   - If deadlock still occurs (rare edge case), automatically retries up to 3 times
   - Exponential backoff: 100ms, 200ms between attempts
   - Only deadlocks are retried; other errors propagate immediately

3. **Error Mapping** (`bookings.py:288-298`)
   - If all retries exhausted, maps deadlock to HTTP 503 (not 500!)
   - Client-friendly message: "Database deadlock detected. Please retry your request."
   - Prevents 500 errors from reaching clients

**Expected Behavior:**

- Under normal load: Advisory lock prevents deadlocks entirely
- Under extreme load: Deadlocks auto-retry and succeed on retry
- Worst case (all retries exhausted): HTTP 503 with retry-friendly message

**Verification:**

Test concurrent booking behavior using the concurrency smoke script:
```bash
# Fire 10 parallel booking requests for the same property/dates
export ENV_FILE=/root/pms_env.sh
bash scripts/pms_booking_concurrency_test.sh

# Expected result:
# - Exactly 1 success (HTTP 201)
# - All others: HTTP 409 inventory_overlap (NOT 503 deadlock)
```

**Troubleshooting:**

If you see HTTP 503 deadlock errors in production:
1. Check if concurrency script passes (validates advisory lock works)
2. Check backend logs for "Deadlock detected after 3 attempts" errors
3. If deadlocks persist despite retries, increase retry attempts or backoff in `booking_service.py`
4. Consider property-level rate limiting if single property receives extreme concurrency

**Code Locations:**
- Advisory lock: `backend/app/services/booking_service.py:510-520`
- Retry wrapper: `backend/app/services/booking_service.py:84-121`
- Route error handler: `backend/app/api/routes/bookings.py:288-298`
- Unit tests: `backend/tests/unit/test_booking_deadlock.py`

**Hotfix Note (2026-01-03):**

After initial deployment of advisory lock serialization, a production bug was discovered:

**Symptom:**
- POST `/api/v1/bookings` returned HTTP 500 for all valid requests
- Backend logs showed: `NameError: name 'property_id' is not defined` at line ~516

**Root Cause:**
- Advisory lock code referenced `property_id` variable before it was defined
- The variable needed to be extracted from `booking_data["property_id"]` before use

**Fix Applied:**
- Added `property_id = to_uuid(booking_data["property_id"])` before transaction start (line 511)
- Advisory lock now correctly uses the extracted property_id for lock key
- Lock still executes inside transaction (xact lock, auto-released on commit/rollback)

**Expected Behavior Restored:**
- Single booking for free window → HTTP 201
- Concurrent requests (10 parallel, same property/dates) → 1x201, 9x409 inventory_overlap
- Deadlock (if retries exhausted) → HTTP 503 with retry message (not 500)

**Verification:**
- Concurrency smoke script: `bash scripts/pms_booking_concurrency_test.sh`
- Unit test added: `test_advisory_lock_uses_property_id_from_request()`

---

### Inventory Blocking Behavior (Inquiry vs Confirmed)

**Updated:** 2026-01-03 (Production Fix)

**Contract:**

Not all booking statuses occupy inventory. Only confirmed/hard reservations create `inventory_ranges` entries that block availability:

**BLOCKING Statuses** (create active `inventory_ranges`):
- `pending` - Awaiting payment/confirmation
- `confirmed` - Paid reservation (hard hold)
- `checked_in` - Guest currently on property

**NON-BLOCKING Statuses** (do NOT create `inventory_ranges`):
- `inquiry` - Information request, tentative interest (NOT a reservation)
- `cancelled` - Reservation cancelled (inventory freed)
- `declined` - Inquiry declined by host
- `no_show` - Guest didn't arrive (inventory freed)
- `checked_out` - Guest departed (inventory freed)

**Why This Matters:**

The availability API (`GET /api/v1/availability`) and booking creation (`POST /api/v1/bookings`) both use `inventory_ranges` with `state='active'` as the source of truth. This ensures:

1. **Inquiry bookings never block availability** - They don't create `inventory_ranges`, so overlapping confirmed bookings can be created
2. **API consistency** - If availability shows a window as free, booking creation will succeed (no false 409s)
3. **Concurrency safety** - The exclusion constraint on `inventory_ranges` prevents race conditions

**Common Scenario:**

```
# Scenario: Inquiry exists for 2026-01-10 to 2026-01-12

# Step 1: Check availability
GET /api/v1/availability?property_id=X&from_date=2026-01-10&to_date=2026-01-12
→ Response: { "ranges": [] }  # Free! (inquiry doesn't block)

# Step 2: Create confirmed booking
POST /api/v1/bookings
{ "property_id": "X", "check_in": "2026-01-10", "check_out": "2026-01-12", "status": "confirmed" }
→ Response: HTTP 201 (success! inquiry doesn't block)

# Step 3: Try to create another confirmed booking
POST /api/v1/bookings (same dates)
→ Response: HTTP 409 inventory_overlap (first confirmed booking blocks)
```

**Production Bug Fixed (2026-01-03):**

**Symptom:**
- Concurrency test auto-found "free window" via availability API (ranges=[])
- But ALL 10 concurrent booking requests returned 409 (0 successes)
- DB showed an `inquiry` booking overlapping the window

**Root Cause:**
- `inquiry` was incorrectly included in `OCCUPYING_STATUSES`
- This caused inquiry bookings to create `inventory_ranges` entries
- Violated the contract that inquiry should be non-blocking

**Fix Applied:**
- Removed `inquiry` from `OCCUPYING_STATUSES` (line 147)
- Added `inquiry` to `NON_OCCUPYING_STATUSES` (line 150)
- Now inquiry bookings do NOT create `inventory_ranges` entries
- Confirmed bookings can overlap with inquiry bookings (as intended)

**Code Locations:**
- Status definitions: `backend/app/services/booking_service.py:145-150`
- Inventory range creation: `backend/app/services/booking_service.py:771-788`
- Status transition logic: `backend/app/services/booking_service.py:926-962`
- Unit test: `backend/tests/unit/test_booking_deadlock.py::test_inquiry_non_blocking_full_lifecycle`

**Verification:**
```bash
# Concurrency script should now succeed even if inquiry bookings exist
bash scripts/pms_booking_concurrency_test.sh

# Expected: 1 success (201), 9 conflicts (409)
# Inquiry bookings in the window will NOT cause all-409s
```

**Database Constraint Fix (2026-01-03 Follow-up):**

**Second Production Bug Discovered:**

After the initial OCCUPYING_STATUSES fix, another issue was found:

**Symptom:**
- Availability API shows window as free (0 inventory_ranges)
- Inquiry booking exists overlapping the window
- ALL concurrent booking requests return 409 (0 successes)
- Backend logs show: `ExclusionViolationError: "no_double_bookings"`

**Root Cause:**
- The `bookings` table has its own exclusion constraint `no_double_bookings`
- Original constraint: `WHERE (status NOT IN ('cancelled', 'declined', 'no_show'))`
- This incorrectly included 'inquiry' in the blocking set
- When trying to INSERT a confirmed booking, the constraint blocked it due to overlapping inquiry

**Fix Applied (Migration 20260103140000):**
- Dropped old `no_double_bookings` constraint
- Recreated with positive filter: `WHERE (status IN ('pending', 'confirmed', 'checked_in'))`
- Now inquiry bookings do NOT trigger this database-level constraint
- Aligns with OCCUPYING_STATUSES and inventory_ranges policy

**Diagnostic Logging Added:**
- Enhanced `booking_service.py` ExclusionViolationError handler (line 731-760)
- Now logs which constraint triggered the 409:
  - `bookings.no_double_bookings` → overlapping pending/confirmed/checked_in booking
  - `inventory_ranges.inventory_ranges_no_overlap` → overlapping active inventory_range
  - Includes property_id, dates, status, and error details for admin debugging

**Troubleshooting: Availability Free but All 409s**

If concurrency test shows "free window" (ranges=[]) but ALL requests get 409:

1. **Check for inquiry bookings in window:**
   ```sql
   SELECT id, status, check_in, check_out
   FROM bookings
   WHERE property_id = 'YOUR-PROPERTY-ID'
     AND status = 'inquiry'
     AND daterange(check_in, check_out, '[)') && daterange('2026-01-10', '2026-01-12', '[)');
   ```

2. **Verify no active inventory_ranges exist:**
   ```sql
   SELECT *
   FROM inventory_ranges
   WHERE property_id = 'YOUR-PROPERTY-ID'
     AND state = 'active'
     AND daterange(start_date, end_date, '[)') && daterange('2026-01-10', '2026-01-12', '[)');
   ```
   Expected: 0 rows (inquiry doesn't create ranges)

3. **Check database constraint:**
   ```sql
   SELECT conname, pg_get_constraintdef(oid)
   FROM pg_constraint
   WHERE conname = 'no_double_bookings' AND conrelid = 'bookings'::regclass;
   ```
   Expected: `WHERE (status IN ('pending', 'confirmed', 'checked_in'))`
   If shows `WHERE (status NOT IN (...))` with inquiry not excluded → apply migration 20260103140000

4. **Check backend logs for constraint name:**
   - Look for `ExclusionViolationError` in logs
   - If "no_double_bookings" appears → database constraint issue (apply migration)
   - If "inventory_ranges" appears → inventory_ranges conflict (unexpected if API says free)

**Migration Path:**
```sql
-- Apply fix (run via Supabase migration runner or psql)
\i supabase/migrations/20260103140000_fix_bookings_exclusion_inquiry_non_blocking.sql
```

**Known Issue (Fixed):**
If migration 20260103140000 fails with syntax error near `||` (ERROR 42601), ensure you have the fixed version that uses a single dollar-quoted string literal for `COMMENT ON CONSTRAINT` instead of concatenated strings. This was fixed in commit 82ffc27 (initial) and refined in a follow-up commit to remove string concatenation operators.

**Applying Supabase Migrations in Production (Host Terminal):**

Production migrations must be applied from the host server terminal with proper credentials:

```bash
# Prerequisites:
# - DATABASE_URL must be set to Supabase Postgres connection string
# - User must be supabase_admin (table owner) for ALTER TABLE operations
# - Run from repo root directory

# Golden Check (recommended): verify you are table owner before ALTER TABLE migrations
psql "$DATABASE_URL" -c "select current_user, (select tableowner from pg_tables where schemaname='public' and tablename='bookings') as bookings_owner;"
# Expected: current_user = supabase_admin AND bookings_owner = supabase_admin

# 1. Check migration status (shows applied vs pending)
bash backend/scripts/ops/apply_supabase_migrations.sh --status

# 2. Apply pending migrations (requires confirmation)
export CONFIRM_PROD=1
bash backend/scripts/ops/apply_supabase_migrations.sh

# 3. Verify constraint was updated correctly
psql "$DATABASE_URL" -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='no_double_bookings' AND conrelid='bookings'::regclass;"
```

**Expected verification output:**
```
WHERE (status = ANY (ARRAY['pending'::text, 'confirmed'::text, 'checked_in'::text]))
```

**Common Pitfalls:**

1. **psql connects to local socket instead of Supabase:**
   - Symptom: Connection succeeds but queries show wrong database
   - Fix: Ensure `DATABASE_URL` is exported in current shell session
   - Verify: `echo $DATABASE_URL` should show full connection string

2. **User is not table owner:**
   - Symptom: `ERROR: must be owner of table bookings`
   - Fix: Use `supabase_admin` role, not `postgres` or `anon`
   - Reliable methods:
     - Include username in URL: `postgresql://supabase_admin:password@host:5432/postgres`
     - OR export `PGUSER=supabase_admin` and `PGPASSWORD=...` before psql
   - Note: Query parameter `?user=supabase_admin` is NOT required (and may not work in all contexts)

3. **Running SQL in Supabase SQL Editor:**
   - Limitation: Supabase SQL Editor does NOT support psql meta-commands (`\i`, `\set`)
   - Limitation: Parameter placeholders like `:pid` only work in psql CLI
   - Fix: Always run migrations from host terminal via psql or migration runner script

---

## Ops Console (Admin UI)

**Purpose:** Optional web-based operations console for system diagnostics and monitoring.

**URL:** `https://admin.fewo.kolibri-visions.de/ops`

**Access Control:**
- **Admin-only:** Only users with `admin` role can access
- **Feature-flagged:** Must be explicitly enabled via environment variable

---

### How to Enable

**Environment Variable (Frontend):**
```bash
NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1
```

**Accepted Values (case-insensitive):**
- `1` (recommended)
- `true`
- `yes`
- `on`

**Default:** Disabled (when not set, or set to `0`, `false`, etc.)

**Where to Set:**
- Coolify Dashboard → pms-admin → Build Pack Variables (Environment Variables)
- Add new variable: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` = `1`
- Redeploy frontend for changes to take effect

---

### Who Can Access

**Requirements (ALL must be met):**
1. User must be logged in with valid JWT token
2. User role must be `admin` (not manager/staff/owner/accountant)
3. Feature flag `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` must be set to a truthy value

**Access Control Behavior (No Silent Redirects):**
- **If auth loading:** Shows loading skeleton
- **If feature disabled:** Shows "Ops Console is Disabled" error page with:
  - Clear explanation that feature flag must be set
  - List of accepted values (`1`, `true`, `yes`, `on`)
  - Link to return to Channel Sync
- **If non-admin (but feature enabled):** Shows "Access Denied" error page with:
  - Message: "Ops Console is restricted to administrators only"
  - Link to return to Channel Sync
  - Logout button
- **If admin AND feature enabled:** Full access to Ops Console

**Important:** Ops Console **never redirects silently** to `/login` or `/channel-sync`. This makes debugging easier — you always see the exact reason you can't access the console.

---

### Pages

The Ops Console includes three main pages:

#### 1. `/ops/status` - System Health

**What it shows:**
- **Overall system status banner** (Healthy / Checking / Down):
  - **Checking system...** (blue, spinning icon) on initial page load while health checks run
    - This is normal and prevents false "System Down" alarms during loading
    - Appears briefly (usually < 1 second) while fetching `/health` and `/health/ready`
  - **System Healthy** (green) when ALL of the following are true:
    - `/health` endpoint returns `status: "up"`
    - `/health/ready` endpoint returns `status: "up"`
    - All components (db, redis, celery) have `status: "up"`
  - **System Down** (red) when ANY check fails:
    - Lists specific failed checks (e.g., "db component (status: down)")
    - Example: "/health (not 'up')", "redis component (status: down)"
    - **Only shows red after checks complete** (not during initial load)
- GET `/health` response with version/commit if available
- GET `/health/ready` response with component statuses
  - Database (db)
  - Redis (if exposed)
  - Celery workers (if exposed)
  - **Component badges** display `component.status` (e.g., "ok", "healthy", "up", "down")
  - **Error messages** appear below component name if `component.error` is present (truncated to 60 chars)

**Endpoint Metadata:**
Each health endpoint displays operational metrics:
- **Last checked:** Local timestamp of last check (e.g., "3:45:23 PM")
- **Duration:** Request round-trip time in milliseconds (e.g., "152ms")
- **HTTP:** Response status code (e.g., "200" for success, "503" for unavailable)

**Actions:**
- **Refresh:** Manually refresh health checks
- **Copy Diagnostics:** Copies system diagnostics to clipboard:
  - Timestamp
  - Current URL (for context)
  - API base URL
  - User role (admin)
  - **Overall status** ("healthy", "down", or "checking")
  - **Failed checks** (list of specific failures if any)
  - **Endpoint metadata** (duration_ms, http_status, last_checked_at for each endpoint)
  - **Component statuses** (summary of db/redis/celery status)
  - `/health` response
  - `/health/ready` response
  - **NO secrets / NO environment values exposed**

**Use Cases:**
- Quick system health check after deployment
- Verify database/Redis/worker connectivity
- Gather diagnostics for issue reports

**Troubleshooting:**
- **"Checking system..." state:** Normal on page load/refresh (brief, < 1 second). Only red "System Down" indicates confirmed failure.
- If banner shows "System Down", check the listed failed checks
- Expand "Show raw JSON" on `/health` and `/health/ready` sections to see full response
- Verify each component has `status: "up"` (not "ok", "healthy", or other values)
- Check endpoint metadata:
  - High duration (> 5000ms) may indicate network/database slowness
  - HTTP status ≠ 200 indicates endpoint failure
  - Recent "Last checked" confirms data freshness
- Common causes:
  - Database connection lost → db component status ≠ "up"
  - Redis unavailable → redis component status ≠ "up"
  - Celery worker down → celery component status ≠ "up"

#### 2. `/ops/sync` - Channel Sync Operations

**What it shows:**
- Link button to existing `/channel-sync` page
- Info cards explaining sync features:
  - Trigger Sync (manual availability/pricing sync)
  - View Logs (real-time sync logs table)
  - Monitor (auto-refresh, error tracking)
- Related resources links (Runbook, System Status)

**Use Cases:**
- Quick navigation to channel sync console
- Overview of sync capabilities

#### 3. `/ops/runbook` - Troubleshooting Guide

**What it shows:**
- Link to full runbook documentation (GitHub)
- Common issues cards:
  - 503: Database Temporarily Unavailable
  - Celery Worker / Redis Down
  - 401: JWT Token Expired
  - 422: Validation Errors (No Sync Log Created)
- Each card includes:
  - Symptoms
  - Causes
  - Quick fix steps

**Actions:**
- **Copy Troubleshooting Template:** Copies issue report template to clipboard:
  - What I was doing
  - Expected vs actual behavior
  - Paste `/health` + `/health/ready` diagnostics
  - Paste last sync log IDs (if applicable)
  - Browser/timestamp/user role
  - **NO secrets exposed**

**Use Cases:**
- Quick reference for common issues
- Generate structured issue reports
- Link to full runbook documentation

---

### Navigation

**Ops Console Navigation Bar:**
- Status → `/ops/status`
- Sync → `/ops/sync`
- Runbook → `/ops/runbook`
- Channel Sync (external link) → `/channel-sync`

**Default Route:**
- Accessing `/ops` redirects to `/ops/status`

---

### Safety & Security

**Read-Only Operations:**
- All Ops Console pages are **read-only diagnostics**
- No dangerous actions (restart services, delete data, etc.)
- No configuration changes allowed

**No Secrets Exposed:**
- Copy Diagnostics does NOT include:
  - Environment variables
  - Database credentials
  - API keys
  - JWT tokens
  - User passwords
- Only exposes:
  - Public health check responses
  - User's own role (admin)
  - API base URL (already public)
  - Timestamps

**RBAC Enforcement:**
- Backend API endpoints still enforce RBAC
- Ops Console UI only provides convenient access
- Admin-only endpoints (like `/health/ready`) still require admin token

---

### How to Use "Copy Diagnostics"

**When to use:**
- Investigating system issues
- Reporting bugs to ops team
- Post-deployment health checks
- Troubleshooting sync failures

**Steps:**
1. Navigate to `/ops/status`
2. Click "Copy Diagnostics" button
3. Paste into issue tracker, Slack, or email
4. Diagnostics include full JSON from `/health` and `/health/ready`
5. Safe to share (no secrets included)

**Example Output:**
```json
{
  "timestamp": "2025-12-30T12:34:56.789Z",
  "api_base": "https://api.fewo.kolibri-visions.de",
  "user_role": "admin",
  "health": {
    "status": "healthy",
    "version": "1.0.0",
    "commit": "abc123def"
  },
  "health_ready": {
    "status": "degraded",
    "components": {
      "db": "ok",
      "redis": "error"
    }
  }
}
```

---

### Troubleshooting Ops Console Access

#### Issue: "Access Denied" Message Although User is Admin

**Symptom:**
- Admin UI shows "Access Denied" error page when opening `/ops`
- Message: "Ops Console is restricted to administrators only"
- Page shows "Access Check Diagnostics" panel with user details
- User verified as admin in database via PostgREST/psql

**Root Cause:**
The frontend now queries the `team_members` table directly (using `user_id` column) instead of relying on JWT metadata. Common reasons for denial:
1. RLS policy blocks the query (user can't read their own team_members row)
2. `is_active=false` in team_members table
3. User ID mismatch (auth.users.id vs team_members.user_id)
4. Static page cache (old access check cached from before role was granted)

**Diagnostics Panel (New in v2):**
The Access Denied page now shows detailed diagnostics:
- User ID and Email
- Team Members Found count (should be ≥1 for valid users)
- Resolved Role (what role was found in team_members)
- Last Active Agency ID (from profiles table)
- Error message (Supabase error or "No active team_members record found")

**Verify Database State with PostgREST:**
```bash
# Replace with your actual JWT token and Supabase URL
export JWT="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export SUPABASE_URL="https://your-project.supabase.co"

# Check team_members (should return at least one row with role='admin')
curl -s "${SUPABASE_URL}/rest/v1/team_members?user_id=eq.USER_ID_HERE&select=user_id,agency_id,role,is_active" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer ${JWT}" | jq

# Expected result:
# [{"user_id":"8036f477-...","agency_id":"ffd0123a-...","role":"admin","is_active":true}]

# Check profiles for last_active_agency_id
curl -s "${SUPABASE_URL}/rest/v1/profiles?id=eq.USER_ID_HERE&select=id,last_active_agency_id" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer ${JWT}" | jq

# Expected result:
# [{"id":"8036f477-...","last_active_agency_id":"ffd0123a-..."}]
```

**Fix Steps:**

1. **Check Diagnostics Panel First:**
   - Look at "Team Members Found" count
   - If 0: User has no active team_members row (see step 2)
   - If ≥1: Check "Resolved Role" (see step 3)
   - If error message shown: See step 4

2. **If Team Members Found = 0:**
   ```sql
   -- Check if row exists but is_active=false
   SELECT user_id, agency_id, role, is_active
   FROM public.team_members
   WHERE user_id = 'USER_ID_HERE';

   -- If exists but is_active=false, activate it
   UPDATE public.team_members
   SET is_active = true
   WHERE user_id = 'USER_ID_HERE';

   -- If no row exists at all, insert one
   INSERT INTO public.team_members (user_id, agency_id, role, is_active)
   VALUES ('USER_ID_HERE', 'AGENCY_ID_HERE', 'admin', true);
   ```

3. **If Resolved Role ≠ 'admin':**
   ```sql
   -- Update role to admin
   UPDATE public.team_members
   SET role = 'admin'
   WHERE user_id = 'USER_ID_HERE'
     AND is_active = true;
   ```

4. **If Error Message Mentions Supabase Error/RLS:**
   - Check RLS policies on `team_members` table
   - User must be able to SELECT their own rows:
     ```sql
     -- Example RLS policy (adjust for your schema)
     CREATE POLICY "Users can view their own team_members"
     ON public.team_members
     FOR SELECT
     USING (auth.uid() = user_id);
     ```
   - Verify Supabase anon key has read access to team_members

5. **If Still Denied After Database Fix:**
   - Hard refresh browser (Ctrl+Shift+R / Cmd+Shift+R)
   - Clear browser cache
   - Logout and login again
   - Check browser console for JavaScript errors
   - Try incognito/private mode to rule out cache

6. **Verify Fix Worked:**
   - Refresh `/ops` page
   - Diagnostics should now show:
     - Team Members Found: ≥1
     - Resolved Role: admin
     - No error message
   - Should redirect to Ops Console status page

#### Issue: "Ops Console is Disabled" Message

**Symptom:**
- Admin UI shows "Ops Console is Disabled" error page
- Message explains that `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` must be set
- Shows accepted values: `1`, `true`, `yes`, `on` (case-insensitive)

**Cause:**
- Feature flag `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` is not set, OR
- Set to a falsy value like `0`, `false`, empty string, etc.

**Fix:**
1. Go to Coolify Dashboard → pms-admin → Build Pack Variables (Environment Variables)
2. Add or update: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` = `1`
3. Redeploy pms-admin application
4. Wait for deployment to complete (~2-3 minutes)
5. Refresh browser (hard refresh: Ctrl+Shift+R / Cmd+Shift+R)

**Note:** The feature flag now accepts multiple truthy values for flexibility:
- `1` (recommended, works in all contexts)
- `true`
- `yes`
- `on`

All values are case-insensitive, so `TRUE`, `True`, `YES`, etc. all work.

#### Issue: Still Shows Auth Loading Skeleton

**Symptom:**
- Opening `/ops` shows "Loading..." indefinitely
- Never transitions to error page or Ops Console

**Cause:**
- Auth context not initializing properly
- JWT token validation hanging

**Fix:**
1. Check browser console for JavaScript errors
2. Verify JWT_SECRET is set correctly in backend
3. Logout and login again
4. Clear browser cache and cookies
5. Try in incognito/private mode to rule out cache issues

---

### Known Limitations

1. **No Real-Time Monitoring:**
   - Status page requires manual "Refresh" button clicks
   - No WebSocket/SSE auto-updates
   - No alerts or notifications

2. **No Historical Data:**
   - Health checks show current state only
   - No time-series graphs or trends
   - No component uptime statistics

3. **No Celery Worker Control:**
   - Cannot restart workers from UI
   - Cannot view active task queue
   - Cannot cancel running tasks

4. **No Log Streaming:**
   - Ops Console does not stream backend/worker logs
   - Must use Coolify Dashboard for log viewing

5. **Feature Flag is Frontend-Only:**
   - Backend API endpoints are always available (if deployed)
   - Ops Console just gates UI access
   - RBAC on backend still enforces admin-only access

---

### Related Sections

- [Channel Manager API Endpoints](#channel-manager-api-endpoints) - API documentation
- [Celery Worker Troubleshooting](#celery-worker-pms-worker-v2-start-verify-troubleshoot) - Worker issues
- [DB DNS / Degraded Mode](#db-dns--degraded-mode) - Database connectivity

---

## Admin UI Authentication Verification

### Overview

The Admin UI (frontend) uses cookie-based SSR authentication for the Ops Console at `/ops/*`. After login, the session must be stored in HTTP cookies (not just localStorage) so that server-side components can validate access.

### Verify Cookie-Based Auth (curl)

These checks verify that the server login endpoint (`/auth/login`) properly sets session cookies, and that the Ops Console respects those cookies.

**Prerequisites:**
- Admin user credentials (e.g., `test1@example.com` with password `12345678`)
- User must have `role='admin'` and `is_active=true` in `public.team_members` table

#### 1. Unauthenticated Access (Expect 307 Redirect)

```bash
# Check that /ops/status redirects to login when not authenticated
curl -sS -I https://admin.fewo.kolibri-visions.de/ops/status | sed -n '1,30p'

# Expected output:
# HTTP/2 307
# location: /login?next=%2Fops%2Fstatus
# ...
```

**What this verifies:**
- Server-side layout properly checks for session cookies
- Unauthenticated requests are redirected to `/login?next=...` (preserves original path)

#### 2. Login to Get Session Cookies

```bash
# Login via server endpoint to get session cookies
curl -sS -i -c /tmp/admin.cookies \
  -H 'Content-Type: application/json' \
  -d '{"email":"test1@example.com","password":"12345678","next":"/ops/status"}' \
  https://admin.fewo.kolibri-visions.de/auth/login | sed -n '1,60p'

# Expected output:
# HTTP/2 200
# set-cookie: sb-<project>-auth-token=...; Path=/; ...
# set-cookie: sb-<project>-auth-token-code-verifier=...; Path=/; ...
# ...
# {"success":true,"user":{"id":"...","email":"test1@example.com"},"next":"/ops/status"}
```

**What this verifies:**
- Server login endpoint (`/auth/login`) accepts POST JSON
- Sets Supabase session cookies (`sb-*-auth-token`)
- Returns success response with user info and next path
- Cookies are saved to `/tmp/admin.cookies` for subsequent requests

**Troubleshooting:**
- `401 Unauthorized`: Invalid credentials or user not found
- `500 Internal Server Error`: Check backend logs for Supabase connection issues
- No `set-cookie` headers: Check that `@supabase/ssr` is properly configured in route handler

#### 3. Authenticated Access (Expect 200 or 307 if Not Admin)

```bash
# Access /ops/status with session cookies
curl -sS -I -b /tmp/admin.cookies \
  https://admin.fewo.kolibri-visions.de/ops/status | sed -n '1,30p'

# Expected output (if user IS admin):
# HTTP/2 200
# ...
#
# Expected output (if user is NOT admin):
# HTTP/2 307
# location: /ops/status (may show Access Denied page, not redirect)
```

**What this verifies:**
- Server-side layout reads session from cookies
- Admin users get 200 OK (ops page renders)
- Non-admin users see Access Denied page (no redirect loop)

**Troubleshooting:**
- `307 to /login`: Session cookies expired or invalid, middleware didn't refresh
- `200 but user not admin`: Check `team_members` table for `role='admin'` and `is_active=true`

#### 4. Logout and Re-Verify (Expect 307 Redirect)

```bash
# Logout (clears session cookies)
curl -sS -I -b /tmp/admin.cookies \
  https://admin.fewo.kolibri-visions.de/auth/logout | sed -n '1,40p'

# Expected output:
# HTTP/2 307
# location: /login
# set-cookie: sb-<project>-auth-token=; Path=/; Expires=Thu, 01 Jan 1970...
# ...

# Verify cookies are invalid - should redirect to login
curl -sS -I -b /tmp/admin.cookies \
  https://admin.fewo.kolibri-visions.de/ops/status | sed -n '1,30p'

# Expected output:
# HTTP/2 307
# location: /login?next=%2Fops%2Fstatus
```

**What this verifies:**
- Logout route (`/auth/logout`) calls `supabase.auth.signOut()` server-side
- Session cookies are cleared (set to expired)
- Subsequent requests to `/ops/*` redirect to login (session invalidated)

**Troubleshooting:**
- Still get 200 after logout: Session not properly cleared, check `createSupabaseRouteHandlerClient()` implementation
- Cookies not expired: Check that route handler sets cookie expiry to past date

### Common Issues

**Issue**: After login, `/ops/status` still redirects to `/login`

**Cause**: Session stored in localStorage only, not cookies. Server components can't read localStorage.

**Fix**:
1. Verify login page calls `/auth/login` endpoint (not direct `supabase.auth.signInWithPassword`)
2. Check that `/auth/login` route handler uses `createSupabaseRouteHandlerClient()`
3. Verify middleware is active for `/ops/*` routes (refreshes session cookies)

---

**Issue**: Login works in Channel Sync but not Ops Console

**Cause**: Split auth storage - Channel Sync uses client localStorage, Ops uses SSR cookies.

**Fix**: Both should use the same cookie-based auth (`/auth/login` endpoint).

---

**Issue**: curl shows 200 but browser shows "Loading..." forever

**Cause**: Client-side hydration waiting for localStorage session, which doesn't exist.

**Fix**: Remove any client-side auth checks in Ops pages. All auth should be server-side in layout.

---

## Additional Resources
---

## Admin UI: Bookings & Properties Lists

### Overview

The Admin UI provides real list pages for `/bookings` and `/properties` with search, filtering, pagination, and error handling. These pages replace the previous "coming soon" placeholders.

### Bookings List Page

**URL**: `https://admin.fewo.kolibri-visions.de/bookings`

**Requires**: JWT authentication (session cookie or Authorization header)

**Features**:
- **Table view** with columns: Referenz, Check-in, Check-out, Status, Preis, Erstellt
- **Search** (client-side): Filters by booking_reference, property_id, or guest_id
- **Status filter** dropdown: All, Angefragt (requested), In Prüfung (under_review), Anfrage (inquiry), Ausstehend (pending), Bestätigt (confirmed), Eingecheckt (checked_in), Ausgecheckt (checked_out), Storniert (cancelled), Abgelehnt (declined)
- **Pagination**: 50 items per page with "Zurück" / "Weiter" buttons
- **Row click**: Navigate to `/bookings/{id}` detail page
- **Loading state**: Spinner with "Lade Buchungen..."
- **Error states**:
  - 401: "Session abgelaufen. Bitte melden Sie sich erneut an."
  - 403: "Zugriff verweigert. Sie haben keine Berechtigung, Buchungen anzuzeigen."
  - 503: "Service vorübergehend nicht verfügbar. Bitte versuchen Sie es später erneut."
- **Empty state**: "Keine Buchungen gefunden" with hint about Public Booking Requests / Channel Manager Sync

**API Endpoint**: `GET /api/v1/bookings?limit=50&offset=0`

**Response Format**: Supports both array and `{ items: [], total: number, limit: number, offset: number }`

### Properties List Page

**URL**: `https://admin.fewo.kolibri-visions.de/properties`

**Requires**: JWT authentication

**Features**:
- **Table view** with columns: Name, Interner Name, Status, ID, Erstellt
- **Search** (client-side): Filters by internal_name, name, title, or id
- **Pagination**: 50 items per page
- **Loading/Error/Empty states**: Same pattern as bookings list
- **No detail page link**: Properties detail page not yet implemented

**API Endpoint**: `GET /api/v1/properties?limit=50&offset=0`

**Response Format**: Same as bookings (supports array or object with items)

### Booking Detail Page

**URL**: `https://admin.fewo.kolibri-visions.de/bookings/{id}`

**Features**:
- **Status badges** with color coding:
  - "requested" → Blue (bg-blue-100 text-blue-800)
  - "under_review" → Purple (bg-purple-100 text-purple-800)
  - "confirmed" → Green
  - "pending" → Yellow
  - "cancelled" → Red
  - "checked_in" → Indigo
  - "checked_out" → Gray
- **Grid layout** with sections: Aufenthaltsinformationen, Preisinformationen, IDs und Referenzen, Zeitstempel, Notizen
- **Guest link**: "Zum Gast →" button if guest_id exists and guest record found
- **Error handling**: 401/403/404/503 with clear German messages

**API Endpoint**: `GET /api/v1/bookings/{id}`

### Browser Verification Steps

**Step 1: Login to Admin UI**

```bash
# Open browser
open https://admin.fewo.kolibri-visions.de/login

# Login with admin credentials
# Email: test1@example.com
# Password: 12345678
```

**Step 2: Navigate to Properties**

```bash
# Click "Objekte" in sidebar navigation
# Or directly: https://admin.fewo.kolibri-visions.de/properties

# Expected:
# - Table loads with property list (not "Objekte kommt bald" placeholder)
# - Columns show: Name, Interner Name, Status, ID, Erstellt
# - Search field works (type partial name, table filters client-side)
# - Pagination buttons enabled if > 50 properties
```

**Step 3: Navigate to Bookings**

```bash
# Click "Buchungen" in sidebar navigation
# Or directly: https://admin.fewo.kolibri-visions.de/bookings

# Expected:
# - Table loads with booking list (not "Buchungen kommt bald" placeholder)
# - Columns show: Referenz, Check-in, Check-out, Status, Preis, Erstellt
# - Status filter dropdown works (select "Angefragt" → shows only requested bookings)
# - Search field works (type booking_reference → filters results)
# - Pagination buttons enabled if > 50 bookings
```

**Step 4: Click on a Booking Row**

```bash
# Click any booking row in the table

# Expected:
# - Navigate to /bookings/{id} detail page
# - Page loads booking details (no "Failed to fetch" error)
# - Status badge displays correctly (e.g., "requested" shows blue badge)
# - All sections render: Aufenthaltsinformationen, Preisinformationen, etc.
# - "Zurück zur Buchungsliste" link works
```

### Troubleshooting

**Problem**: Bookings or Properties page shows "Keine ... gefunden" (empty state) despite data in database

**Root Causes**:
1. **API returns empty array**: Backend query filters results (e.g., agency_id mismatch, RLS policy)
2. **Client-side filters too restrictive**: Search query or status filter excludes all results
3. **Pagination offset too high**: Requesting offset=500 when only 50 records exist

**Solution**:
```bash
# 1. Check browser DevTools Network tab
# Look for: GET /api/v1/bookings?limit=50&offset=0
# Response should be: { items: [...], total: N } or [...]
# If items is empty, issue is backend

# 2. Verify JWT agency_id claim matches data in database
# Open browser console: localStorage.getItem('supabase.auth.token')
# Decode JWT (jwt.io): Check agency_id claim
# Query database: SELECT COUNT(*) FROM bookings WHERE agency_id = '<claim-value>'

# 3. Check RLS policies
# Database console:
SELECT * FROM pg_policies WHERE tablename = 'bookings';
# Ensure policy allows current user's role and agency_id

# 4. Reset filters in UI
# Clear search field (click X button)
# Set status filter to "Alle Status"
# Reset pagination to page 1
```

**Problem**: Booking detail page returns HTTP 500 with ResponseValidationError

**Root Cause**: Booking status value in database not in allowed Literal types (e.g., "requested" not in schema)

**Solution**: Fixed in backend commit cb8da7f - Extended BookingStatus Literal to include "requested" and "under_review"

**Verification**:
```bash
# Check deployed commit
curl -s https://api.fewo.kolibri-visions.de/api/v1/ops/version | jq -r .source_commit

# Should be cb8da7f or later (2026-01-07+)
# If earlier commit, trigger deployment or wait for auto-deploy
```

**Problem**: Properties or Bookings page shows "Session abgelaufen" (401 error)

**Root Cause**: JWT token expired or not present in request

**Solution**:
```bash
# 1. Check if cookies are set
# Browser DevTools → Application → Cookies → admin.fewo.kolibri-visions.de
# Should see: sb-*-auth-token cookies

# 2. If no cookies, re-login via /login page
# Login sets new session cookies

# 3. If cookies exist but still 401, check token validity
# Network tab → Request Headers → Authorization: Bearer <token>
# If no Authorization header, check that apiClient uses accessToken from useAuth()

# TOKEN SANITY CHECK:
# - TOKEN must be access_token (not refresh_token)
# - Expected length: ~616 characters
# - JWT parts: 3 (header.payload.signature)
# - When calling Kong auth endpoints (e.g., Supabase token endpoint at sb-pms.kolibri-visions.de):
#   Include "apikey" header with anon/service_role key
# - Verify JWT: echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq .
#   Should include: sub (user_id), email, role, agency_id (for multi-tenant)

# 4. Check CORS configuration
# Network tab → Failed request → Response Headers
# If missing Access-Control-Allow-Origin, backend CORS misconfigured
# See: [CORS Errors](#cors-errors-admin-console-blocked)
```

**Problem**: Properties or Bookings page shows "Service vorübergehend nicht verfügbar" (503 error)

**Root Cause**: Backend database unavailable or schema drift

**Solution**:
```bash
# 1. Check backend health
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq .

# Expected: {"status": "up", "components": {"db": {"status": "up"}, ...}}
# If db: "down", check [DB DNS / Degraded Mode](#db-dns--degraded-mode)

# 2. Check backend logs
docker logs pms-backend --tail 100 | grep -i "error\|503"

# Look for: "Database unavailable", "Schema not installed", "Relation does not exist"
# If schema errors, see [Schema Drift](#schema-drift)

# 3. Verify backend container is running
docker ps | grep pms-backend

# If not running, restart via Coolify UI or docker start
```

### PROD Verified (2026-01-07)

**Deployed Commit:** 17448496c88810a32be44bc76b2ca36dac87f072

**Verification Evidence:**
```bash
# HOST-SERVER-TERMINAL
export API_BASE_URL="https://api.fewo.kolibri-visions.de"

# Verify deployed commit
curl -s "$API_BASE_URL/api/v1/ops/version" | jq -r .source_commit
# Output: 17448496c88810a32be44bc76b2ca36dac87f072

# Verify bookings list endpoint
curl -k -sS -i -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/bookings?limit=1&offset=0" | head -20
# Output: HTTP/2 200
# Body includes: items array with booking objects

# Verify properties list endpoint
curl -k -sS -i -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/properties?limit=1&offset=0" | head -20
# Output: HTTP/2 200
# Body includes: items array with property objects

# Verify CORS headers present
curl -sS -i -H "Origin: https://admin.fewo.kolibri-visions.de" \
  -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/bookings?limit=1&offset=0" | grep -i access-control-allow-origin
# Output: access-control-allow-origin: https://admin.fewo.kolibri-visions.de
```

**Backend Started At:** 2026-01-07T19:13:03.928023+00:00

**Browser Verification:**
- ✅ https://admin.fewo.kolibri-visions.de/bookings shows real table (not "Buchungen kommt bald" placeholder)
- ✅ https://admin.fewo.kolibri-visions.de/properties shows real table (not "Objekte kommt bald" placeholder)
- ✅ Search, filtering, and pagination work as expected
- ✅ Booking detail page displays status='requested' with blue badge

**Result:** ✅ Admin UI list pages verified in production - real tables with full functionality

### Related Sections

- [Admin UI Authentication Verification](#admin-ui-authentication-verification) - For cookie-based SSR auth checks
- [CORS Errors (Admin Console Blocked)](#cors-errors-admin-console-blocked) - For CORS configuration
- [Booking Status Validation Error (500)](#booking-status-validation-error-500) - For status field validation errors
- [Schema Drift](#schema-drift) - For database schema issues


### Smoke Scripts

**Location**: `/app/scripts/` (in container)

The Phase 23 smoke script (`pms_phase23_smoke.sh`) provides quick confidence checks for post-deployment validation. It includes two **opt-in tests** for advanced inventory/availability validation:

#### AVAIL_BLOCK_TEST (Availability Block Conflict Test)

**What it does:**
- Creates a future availability block (today+30 days, 3-day duration)
- Verifies block appears in `/api/v1/availability` response
- Attempts to create overlapping booking (expects 409 `inventory_overlap`)
- Deletes the block for cleanup

**Usage:**
```bash
# In Coolify container terminal or via docker exec
export ENV_FILE=/root/pms_env.sh
export AVAIL_BLOCK_TEST=true
bash /app/scripts/pms_phase23_smoke.sh
```

**Safety:**
- Uses future dates (30+ days out) to avoid production conflicts
- Always cleans up (block deletion via trap, runs even on failure)

#### B2B_TEST (Back-to-Back Booking Boundary Test)

**What it does:**
- Scans for a 4-day free gap in the future (today+60 to today+150)
- Creates booking A: D → D+2 (2 nights)
- Creates booking B: D+2 → D+4 (2 nights, check-in = A's check-out)
- Expects both HTTP 201 (confirms end-exclusive date semantics)
- Cancels both bookings via PATCH `status=cancelled`

**Usage:**
```bash
# In Coolify container terminal or via docker exec
export ENV_FILE=/root/pms_env.sh
export B2B_TEST=true
bash /app/scripts/pms_phase23_smoke.sh
```

**Safety:**
- Uses far-future dates (60+ days out) to avoid production conflicts
- Always cleans up (booking cancellation via trap, runs even on failure)
- Uses PATCH cancel instead of DELETE (DELETE /bookings returns 405)

**When to Use:**
- After schema migrations affecting availability/inventory tables
- After deployment of conflict detection logic changes
- Pre-production validation before go-live
- NOT recommended for CI/CD or frequent monitoring (creates/deletes data)

#### Phase 23 Status Summary (2026-01-04)

**Test Status:** PASS (all required + optional tests)

**Core Tests (Always Run):**
- Health endpoints (`/health`, `/health/ready`) - HEAD and GET methods
- OpenAPI schema availability (`/openapi.json`)
- JWT authentication (token fetch from auth service)
- Authenticated API access (properties, bookings, availability)

**Optional Test 8 (AVAIL_BLOCK_TEST=true):**
- **Status:** PASS
- **Expectation:** Availability block overlap MUST return HTTP 409 with `conflict_type=inventory_overlap`
- **Enforcement:** Script FAILS (exit 1) if wrong conflict_type, even when HTTP 409 is correct
- **Semantic rule:** Block overlap → `inventory_overlap`, booking overlap → `double_booking`

**Optional Test 9 (B2B_TEST=true):**
- **Status:** PASS
- **Validation:** Back-to-back bookings allowed (check-in = previous check-out)
- **Confirms:** End-exclusive date semantics `[check_in, check_out)` working correctly

**Known Issues Resolved:**
- ✓ Conflict type detection: Fixed NameError (undefined `conn` variable) that caused HTTP 500
  - **Symptom:** Booking creation returned 500 instead of 409 when overlapping block
  - **Root cause:** Wrong database handle in pre-check (`conn` instead of `self.db`)
  - **Fix:** Use `self.db.fetchrow()` for availability block queries
- ✓ Frontend auto-detect: Connection selection now auto-derives Platform and Property fields
- ✓ Batch details: Duration display shows `duration_ms` with fallback logic

**API Response Shape Notes:**
- Some list endpoints return raw JSON array: `[{...}, {...}]`
- Others return object with items: `{"items": [...], "total": N, "has_more": bool}`
- **Best practice:** Always verify JSON shape before parsing in shell scripts
- **Example:** Use `python3 -c 'data = json.load(sys.stdin); items = data if isinstance(data, list) else data.get("items", [])'`

**Redirect/Trailing Slash:**
- Some endpoints may redirect (307/302) on trailing slash mismatch
- **Best practice:** Use `curl -L` in scripts to follow redirects automatically
- **Avoid:** Parsing empty/non-JSON bodies from redirect responses

**Full Documentation**: `/app/scripts/README.md` (in container)

### Other Resources

- **Inventory Contract** (Single Source of Truth): `/app/docs/domain/inventory.md` (date semantics, API contracts, edge cases, DB guarantees, test evidence)
- **Inventory & Availability Rules**: `/app/docs/database/exclusion-constraints.md` (conflict rules, EXCLUSION constraints, overlap prevention)
- **Modular Monolith Architecture**: `/app/docs/architecture/modules.md` (module system, registry, dependency management)
- **Architecture Docs**: `/app/docs/architecture/` (in container)
- **Supabase Dashboard**: Check database health, logs, network
- **Coolify Dashboard**: Application logs, environment variables, networks

---


---


## Admin UI Visual Style (Backoffice Theme v1)

### Overview

The Admin UI uses a modern "Backoffice Theme v1" inspired by Paperpillar dashboard design. The theme features a soft neutral background (#E8EFEA), white cards with generous radius, icon-only sidebar with dark active states, and a cohesive green-purple-beige color system.

### Theme v1 Palette

**Base Colors**:
- #121212 #201F23 #45515C #596269 #FFFFFF

**Green Palette** (Primary actions, success states):
- #395917 (dark green) #4C6C5A (primary) #617C6C #A4C8AE #E8EFEA (background)

**Purple Palette** (Accents, borders):
- #595D75 (accent) #BBBED5 (light) #E3E4EA (borders)

**Additional Accents**:
- Beige: #A39170 #E5D6B8
- Tosca: #C1DBDA
- Red: #9B140B (danger)

### Theme Tokens

**CSS Variables** (defined in `frontend/app/globals.css`):
- `--bo-bg`: #E8EFEA (soft neutral background - lightest green)
- `--bo-card`: #FFFFFF (white cards)
- `--bo-border`: #E3E4EA (subtle borders - light purple)
- `--bo-text`: #121212 (primary text - darkest base)
- `--bo-text-muted`: #596269 (muted text)
- `--bo-primary`: #4C6C5A (primary green for actions)
- `--bo-success`: #A4C8AE (success states)
- `--bo-danger`: #9B140B (danger/error states)
- `--bo-accent`: #595D75 (purple accents)
- `--bo-shadow-soft`: Soft shadows for pills/buttons
- `--bo-shadow`: Standard card shadows
- `--bo-shadow-md`: Medium elevation shadows
- `--bo-radius-lg`: 1.5rem (24px) for main cards
- `--bo-radius-full`: 9999px for pills/circles

**Typography**:
- Headings: Plus Jakarta Sans (via `font-heading` class) - fallback for General Sans
- Body: Inter (via `font-sans` class)
- Hierarchy: H1 = 2xl-3xl, H2 = xl, Body = base/sm

### Design Patterns

**Shell Layout**:
- Background: Soft neutral (`bg-bo-bg` - #E8EFEA, lightest green)
- Sidebar: Icon-only by default, pill container with `rounded-bo-lg`, white background, soft shadow
- Topbar: Transparent background with greeting header ("Hello, User!"), pill search input, circular icon buttons
- Content area: Generous padding (p-6 to p-8), cards with large radius

**Navigation**:
- Icon backgrounds: Circular (`w-10 h-10 rounded-full`) with light purple background
- Active state: Dark circle (#121212 - darkest base) with white icon and shadow
- Inactive state: Light purple background, hover transitions to lighter purple
- Expandable sidebar: Shows labels when expanded, icon-only when collapsed

**Cards & Tables**:
- Cards: White (`bg-bo-card`), `rounded-bo-lg` (24px), subtle border (#E3E4EA), soft shadow
- Table rows: Hover effect with `hover:bg-bo-surface-2`
- Status badges: `rounded-full` pills with semantic colors
- Card spacing: Generous internal padding (p-6 to p-12)

**Form Elements**:
- Inputs: Pill style (`rounded-full`), white background, light purple border, soft shadow
- Buttons: Primary uses green (`bg-bo-primary`), rounded-xl to rounded-2xl, soft shadows
- Focus rings: Use primary green color
- Search bar: Pill-shaped with icon, integrated in topbar

### Browser Verification

**Visual Checklist**:
```bash
# Navigate to Admin UI
open https://admin.fewo.kolibri-visions.de/login

# After login, verify Theme v1 styling:
1. Background is soft neutral (#E8EFEA - lightest green)
2. Sidebar is icon-only vertical layout (left side)
3. Navigation icons have circular backgrounds (w-10 h-10 rounded-full)
4. Active nav icon has dark circle (#121212) with white icon
5. Inactive nav icons have light background (bg-bo-surface-2)
6. Topbar has white background with pill-shaped search input
7. Topbar shows round icon buttons (notifications, profile)
8. Cards are white (#FFFFFF) with soft shadows (shadow-bo-soft)
9. Cards have large rounded corners (rounded-bo-lg or rounded-bo-xl)
10. Status badges are pill-shaped with semantic colors
11. Buttons are rounded-full with primary green (#4C6C5A)
12. Text colors: primary #121212, muted #596269
13. All text uses Inter font (next/font/google optimization)
14. Good contrast on all interactive elements

# Test pages for Theme v1:
- /dashboard         → White cards on soft green background
- /bookings          → Table with new color palette
- /bookings/{id}     → Detail page with info cards
- /properties        → Table with search filter
- /properties/{id}   → Detail page with multiple sections
- /channel-sync      → Sync dashboard with connection cards
- /guests            → Guest list
- /connections       → Connection management
```

### Troubleshooting

**Problem**: Fonts not loading or fallback to system fonts

**Solution**:
```bash
# 1. Check browser network tab for font download
# Inter font should load from fonts.gstatic.com

# 2. Hard refresh to clear cache
# Browser: Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows)

# 3. Verify font variables in DevTools
# Elements → <body> → Should see --font-inter variable
# Theme v1 uses Inter for all text (body and headings)

# 4. Check Next.js font optimization
# Inter is loaded via next/font/google with automatic preloading
```

**Problem**: CSS variables not applied (colors look wrong)

**Solution**:
```bash
# 1. Check if globals.css is loaded
# DevTools → Network → Filter CSS → Should see globals.css

# 2. Verify Theme v1 CSS variable values in DevTools
# DevTools → Elements → :root → Styles panel
# Should see Backoffice Theme v1 variables:
# --bo-bg: #E8EFEA
# --bo-card: #FFFFFF
# --bo-text: #121212
# --bo-primary: #4C6C5A
# ... (all Theme v1 palette variables)

# 3. Hard refresh browser cache
# Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows)

# 4. Check Tailwind config extension
# Ensure tailwind.config.ts extends theme.colors.bo with new utilities
```

**Problem**: Components still show old styling

**Solution**:
```bash
# 1. Check if page was updated to Theme v1
# View source → Search for "bg-bo-card", "text-bo-text", "rounded-bo-lg"
# Should NOT see old classes like "bg-white", "text-gray-*"

# 2. Clear Next.js cache and rebuild
cd frontend && rm -rf .next && npm run dev

# 3. Verify deployment includes Theme v1 commit
# Check git log for "ui: backoffice theme v1 (dashboard style)"
```

**Problem**: Rounded corners too aggressive / not matching design

**Solution**:
```bash
# Adjust CSS variables in frontend/app/globals.css
# --bo-radius-xl: 2rem → Reduce to 1.5rem for less rounding
# --bo-radius: 1rem → Adjust for standard cards

# Then rebuild frontend
cd frontend && npm run build
```

### Related Sections

- [Admin UI Authentication Verification](#admin-ui-authentication-verification)
- [Admin UI: Bookings & Properties Lists](#admin-ui-bookings--properties-lists)
- [Admin UI: Booking & Property Detail Pages](#admin-ui-booking--property-detail-pages)


## Admin UI Layout Polish v2.1 (Profile + Language + Sidebar Polish)

### Overview

Layout v2.1 adds comprehensive polish to the Admin UI with language switcher (RTL support), profile dropdown, and improved sidebar collapsed state. This builds on Theme v2 (blue/indigo palette, Lucide icons).

### Key Features

**Language Switcher**:
- Flag icons for DE/EN/AR in topbar (right side)
- Dropdown shows on HOVER (not just click)
- Persists selection in localStorage (`bo_lang` key)
- Sets `document.documentElement.lang` to 'de'|'en'|'ar'
- Sets `document.documentElement.dir` to 'rtl' for Arabic, 'ltr' for others
- Supports internationalization scaffolding for future i18n

**Profile Dropdown**:
- User icon button in topbar (right side)
- Shows user name (extracted from email if needed) and role
- Menu links:
  - Profil (`/profile`)
  - Profil bearbeiten (`/profile/edit`)
  - Sicherheit (`/profile/security`)
  - Abmelden (`performLogout()` - client-side signOut with redirect to /login)
- Stub pages created with AdminShell layout

**Sidebar Collapsed Polish**:
- Logo properly centered when collapsed (no clipping)
- Toggle button more visible: border, background, shadow
- All icons consistently centered in collapsed mode
- Tooltips show labels on hover when collapsed
- Scrollbar hidden but scroll functional (`scrollbar-hide` utility)
- No animation jank on route changes (no transitions on desktop)

### Implementation Details

**Files Modified**:
- `frontend/app/components/AdminShell.tsx` - Main shell component
  - Added `useEffect` to set document.lang and dir based on language state
  - Changed language dropdown from onClick to onMouseEnter/onMouseLeave
  - Centered logo in collapsed mode with conditional justify-center
  - Enhanced toggle button styling with border/bg/shadow

**Files Created**:
- `frontend/app/profile/page.tsx` - Profile stub page
- `frontend/app/profile/edit/page.tsx` - Edit profile stub page
- `frontend/app/profile/security/page.tsx` - Security settings stub page
- `frontend/app/profile/layout.tsx` - Profile section layout with auth

### Browser Verification

**Language Switcher**:
```bash
# 1. Open Admin UI in browser
open https://admin.fewo.kolibri-visions.de/dashboard

# 2. Verify language dropdown
# - Topbar right side shows current flag (🇩🇪 DE by default)
# - HOVER over flag button → dropdown appears with DE/EN/AR options
# - Click different language → page updates, selection persists on reload

# 3. Check RTL support for Arabic
# DevTools → Elements → <html>
# Should see: lang="ar" dir="rtl" when Arabic selected
# Should see: lang="de" dir="ltr" when German selected
# Should see: lang="en" dir="ltr" when English selected

# 4. Check localStorage persistence
# DevTools → Application → Local Storage
# Should see: bo_lang = "de"|"en"|"ar"
```

**Profile Dropdown**:
```bash
# 1. Click user icon in topbar (right side, after notifications)
# Dropdown appears with user info header (name + role)

# 2. Verify menu items
# - "Profil" link → navigates to /profile
# - "Profil bearbeiten" link → navigates to /profile/edit
# - "Sicherheit" link → navigates to /profile/security

# 3. Check profile pages
# All pages should:
# - Use AdminShell layout with sidebar
# - Show "Demnächst verfügbar" placeholder
# - Require authentication (redirect to /login if not logged in)
```

**Sidebar Collapsed State**:
```bash
# 1. Collapse sidebar using toggle button at bottom
# DevTools → Application → Local Storage
# Should see: sidebar-collapsed = "true"

# 2. Verify collapsed appearance
# - Logo centered in header (not clipped on sides)
# - All navigation icons centered (40px × 40px containers)
# - Toggle button has visible border and background
# - Sidebar width reduced to w-24 (96px)

# 3. Test tooltips
# Hover over any nav icon when collapsed
# Should see tooltip with item label (e.g., "Dashboard", "Buchungen")

# 4. Verify no scrollbar visible
# Sidebar should scroll if content exceeds height
# But scrollbar should be hidden (scrollbar-hide utility)

# 5. Test route changes
# Navigate between pages (Dashboard → Bookings → Properties)
# Sidebar should NOT animate/transition (no jank)
# Only content area updates
```

### Troubleshooting

**Problem**: Language dropdown doesn't show on hover

**Solution**:
```bash
# 1. Check JavaScript enabled in browser
# 2. Verify React hydration completed (no console errors)
# 3. Test with onClick as fallback:
# - Click flag button → dropdown should appear
# 4. Check browser event listeners in DevTools
# Elements → Language dropdown div → Event Listeners
# Should see: mouseenter, mouseleave
```

**Problem**: RTL not working for Arabic

**Solution**:
```bash
# 1. Verify document.documentElement.dir is set
# DevTools → Elements → <html> → Should see dir="rtl"

# 2. Check if CSS supports RTL
# Most Tailwind utilities are LTR-only by default
# May need to add RTL-specific CSS or use logical properties

# 3. Verify language state is "ar"
# DevTools → React DevTools → AdminShell component
# Should see: language = "ar"
```

**Problem**: Logo clipped in collapsed sidebar

**Solution**:
```bash
# 1. Check if conditional centering is applied
# DevTools → Elements → Brand header div
# When collapsed: should have "justify-center" class
# When expanded: should have "gap-3" class

# 2. Verify sidebar width
# Collapsed: w-24 (96px) - Logo is 48px, fits with padding
# Expanded: w-72 (288px)

# 3. Check logo flexbox
# Logo container should have: flex-shrink-0
```

**Problem**: Profile pages return 404

**Solution**:
```bash
# 1. Verify pages exist
ls -la frontend/app/profile/
# Should see: page.tsx, edit/, security/, layout.tsx

# 2. Rebuild Next.js
cd frontend && rm -rf .next && npm run dev

# 3. Check authentication
# Profile pages require auth via layout.tsx
# If not logged in → redirects to /login with returnTo parameter
```

### Related Sections

- [Admin UI Visual Style (Backoffice Theme v1)](#admin-ui-visual-style-backoffice-theme-v1)
- [Admin UI Authentication Verification](#admin-ui-authentication-verification)


## Admin UI Static Verification (Smoke Test)

### Overview

Automated smoke test that verifies Admin UI deployment and expected UI content without requiring authentication. Checks that critical UI components (language switcher, logout menu) are present in the deployed JavaScript bundles.

### Script

**Location**: `backend/scripts/pms_admin_ui_static_smoke.sh`

**Execution**: HOST-SERVER-TERMINAL (where Coolify/Docker is running)

**Purpose**: Verify that:
1. Admin UI container is running with expected SOURCE_COMMIT
2. `/login` endpoint returns HTTP 200
3. Next.js static chunks contain expected UI strings (Abmelden, Deutsch, English, العربية)

### Usage

```bash
# Basic usage (default: https://admin.fewo.kolibri-visions.de)
./backend/scripts/pms_admin_ui_static_smoke.sh

# With custom base URL
ADMIN_BASE_URL=https://admin.example.com ./backend/scripts/pms_admin_ui_static_smoke.sh

# With expected commit verification
EXPECTED_COMMIT=abc1234567 ./backend/scripts/pms_admin_ui_static_smoke.sh

# Increase chunk crawl limit if expected strings not found
MAX_CHUNKS=150 ./backend/scripts/pms_admin_ui_static_smoke.sh

# Debug mode: preserve temp directory with downloaded chunks
KEEP_TEMP=true ./backend/scripts/pms_admin_ui_static_smoke.sh

# Full configuration
ADMIN_BASE_URL=https://admin.example.com CONTAINER_NAME=pms-admin EXPECTED_COMMIT=abc1234567 MAX_CHUNKS=80 KEEP_TEMP=false ./backend/scripts/pms_admin_ui_static_smoke.sh
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_BASE_URL` | `https://admin.fewo.kolibri-visions.de` | Base URL of Admin UI |
| `CONTAINER_NAME` | `pms-admin` | Docker container name to inspect |
| `EXPECTED_COMMIT` | (empty) | Expected SOURCE_COMMIT; accepts short prefix (e.g., 7 chars) or full 40-char SHA |
| `MAX_CHUNKS` | `80` | Maximum number of JS chunks to download during crawling |
| `KEEP_TEMP` | `false` | Set to `true` to preserve temp directory for debugging |

**Notes**:
- `EXPECTED_COMMIT` supports short SHA prefixes (e.g., `18d76f2`) for convenience; full 40-char SHA also accepted
- Script checks numeric HTTP status code (`%{http_code}`), so HTTP/2 200 responses work correctly
- **Scan modes**: Script uses container-scan mode when docker is available (scans built Next.js assets inside container at `.next/static`); this covers UI strings in authenticated routes not referenced by /login. Falls back to http-crawl mode (downloads chunks from public site) when docker unavailable.
- Script crawls chunk graph: downloads initial chunks from /login HTML, parses them for additional chunk URLs, downloads up to `MAX_CHUNKS` limit
- If expected strings not found, try increasing `MAX_CHUNKS` or use `KEEP_TEMP=true` to inspect downloaded chunks

### Expected Output (PASS)

```
======================================================================
Admin UI Static Smoke Test
======================================================================

[INFO] Configuration:
[INFO]   ADMIN_BASE_URL: https://admin.fewo.kolibri-visions.de
[INFO]   CONTAINER_NAME: pms-admin
[INFO]   EXPECTED_COMMIT: 0572b72f059a71dc280c564a194dd279d9a7ab6d
[INFO]   MAX_CHUNKS: 80
[INFO]   KEEP_TEMP: false

[INFO] Step 1: Checking Docker container...
[INFO]   Container SOURCE_COMMIT: 0572b72f059a71dc280c564a194dd279d9a7ab6d
[INFO]   ✓ Commit matches expected: 0572b72f059a71dc280c564a194dd279d9a7ab6d

[INFO] Step 2: Checking https://admin.fewo.kolibri-visions.de/login ...
[INFO]   ✓ HTTP 200 OK

[INFO] Step 3: Searching for UI strings (mode: container-scan)...
[INFO]   Found Next.js assets at: /app/.next/static
[INFO]   ✓ Found 'Abmelden' in container:/app/.next/static/chunks/app-layout-1a2b3c4d5e.js
[INFO]   ✓ Found 'Deutsch' in container:/app/.next/static/chunks/app-layout-1a2b3c4d5e.js
[INFO]   ✓ Found 'English' in container:/app/.next/static/chunks/app-layout-1a2b3c4d5e.js
[INFO]   ✓ Found 'العربية' in container:/app/.next/static/chunks/app-layout-1a2b3c4d5e.js

[INFO] Summary: Found 4/4 expected strings

======================================================================
[INFO] ✓ PASS: All checks passed
======================================================================
```

Exit code: `0`

### Production Verification Procedure

To mark Admin UI features as **VERIFIED** in project_status.md:

1. **Collect commit hash** from Coolify deployment or Docker:
   ```bash
   docker inspect pms-admin --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^SOURCE_COMMIT='
   ```

2. **Run smoke script** with expected commit:
   ```bash
   EXPECTED_COMMIT=abc1234567 ./backend/scripts/pms_admin_ui_static_smoke.sh
   ```

3. **Verify exit code** is `0` and output shows all checks passing

4. **Update project_status.md**: Change status from "IMPLEMENTED (NOT VERIFIED)" to "VERIFIED" and add verification evidence:
   ```markdown
   **Status**: ✅ VERIFIED

   **Verification Evidence** (HOST-SERVER-TERMINAL):
   - Date: 2026-01-08
   - Container: pms-admin
   - SOURCE_COMMIT: 0572b72f059a71dc280c564a194dd279d9a7ab6d
   - Smoke script: pms_admin_ui_static_smoke.sh rc=0
   - All expected UI strings found in static bundles
   ```

### Troubleshooting

**Problem**: Script fails with "No chunk URLs found in HTML"

**Solution**:
```bash
# 1. Check if Next.js is using different build output structure (find chunk URLs manually)
curl -k -sS https://admin.fewo.kolibri-visions.de/login | grep -oE '/_next/static/[^"]+\.js' | head -5

# 2. Download first chunk and verify content structure
CHUNK="$(curl -k -sS https://admin.fewo.kolibri-visions.de/login | grep -oE '/_next/static/[^"]+\.js' | head -1)" && echo "Chunk: $CHUNK" && curl -k -sS "https://admin.fewo.kolibri-visions.de${CHUNK}" | head -20

# 3. Check if Next.js version changed (different chunk structure)
docker exec pms-admin sh -c "cat package.json | grep '\"next\"'"
```

**Problem**: Script fails with "Missing expected strings"

**Solution**:
```bash
# 1. Download first chunk manually and search for expected strings
CHUNK="$(curl -k -sS https://admin.fewo.kolibri-visions.de/login | grep -oE '/_next/static/[^"]+\.js' | head -1)" && curl -k -sS "https://admin.fewo.kolibri-visions.de${CHUNK}" -o /tmp/chunk.js && grep -E 'Abmelden|Deutsch|English|العربية' /tmp/chunk.js

# 2. If strings not found, check if deployment is correct commit
docker inspect pms-admin --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^SOURCE_COMMIT='

# 3. Check if UI code was actually deployed (cache issue) - force browser hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

# 4. If still missing, check if feature was actually merged
git log --oneline | grep -Ei 'logout|language|abmelden' | head -20
```

**Problem**: Commit mismatch error

**Solution**:
```bash
# 1. Check what commit is actually deployed
docker inspect pms-admin --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^SOURCE_COMMIT='

# 2. Check Coolify deployment logs (via Coolify UI or docker logs pms-admin)

# 3. If Coolify hasn't picked up latest commit yet: trigger manual redeploy in Coolify or wait for automatic deployment

# 4. Verify local repo is up to date
git fetch origin main && git log origin/main --oneline -5
```

### Related Sections

- [Admin UI Layout Polish v2.1 (Profile + Language + Sidebar Polish)](#admin-ui-layout-polish-v21-profile--language--sidebar-polish)
- [Admin UI Authentication Verification](#admin-ui-authentication-verification)

---

## Phase 21 — Availability Hardening Verification

### Overview

Phase 21 production hardening for Availability API endpoints. Validates availability query, block creation/deletion, overlap conflict detection (409), and proper error handling.

### Script

**Location**: `backend/scripts/pms_availability_phase21_smoke.sh`

**Execution**: HOST-SERVER-TERMINAL

**Purpose**: Verify that:
1. Availability query works (GET /api/v1/availability)
2. Block creation succeeds with 201 (POST /api/v1/availability/blocks)
3. Overlapping block returns 409 conflict (DB EXCLUSION constraint working)
4. Block read works (GET /api/v1/availability/blocks/{block_id})
5. Block deletion succeeds with 204 (DELETE /api/v1/availability/blocks/{block_id})
6. Deleted block returns 404 (verification)

### Usage

```bash
# Basic usage (requires JWT_TOKEN and PID)
JWT_TOKEN="eyJhbG..." PID="550e8400-e29b-..." ./backend/scripts/pms_availability_phase21_smoke.sh

# With custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJhbG..." PID="550e8400-..." ./backend/scripts/pms_availability_phase21_smoke.sh

# With custom date range
JWT_TOKEN="eyJhbG..." PID="550e8400-..." AVAIL_FROM=2026-02-01 AVAIL_TO=2026-02-08 ./backend/scripts/pms_availability_phase21_smoke.sh
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_TOKEN` | (required) | Valid JWT token with admin or manager role |
| `PID` | (required) | Property ID (UUID) to test with |
| `API_BASE_URL` | `https://api.fewo.kolibri-visions.de` | API base URL |
| `AVAIL_FROM` | tomorrow (YYYY-MM-DD) | Block start date |
| `AVAIL_TO` | tomorrow + 7 days (YYYY-MM-DD) | Block end date |

**Notes**:
- Script uses future dates by default to avoid past-date validation errors
- Property must exist and belong to authenticated user's agency
- Script creates test block, verifies overlap protection (409), then cleans up via DELETE
- Safe to run multiple times (idempotent: creates + deletes block each run)
- All HTTP status codes validated: 200 (query/read), 201 (create), 204 (delete), 404 (not found), 409 (conflict)

### Expected Output (PASS)

```
======================================================================
Availability API Phase 21 - Smoke Test
======================================================================

Configuration:
  API_BASE_URL: https://api.fewo.kolibri-visions.de
  PID: 550e8400-e29b-41d4-a716-446655440000
  AVAIL_FROM: 2026-01-09
  AVAIL_TO: 2026-01-16
  JWT_TOKEN: <set (hidden)>

[TEST 1] Query availability for property
  ✓ PASS: HTTP 200 - availability query successful
  ✓ PASS: Response has valid structure (property_id, from_date, to_date, ranges)

[TEST 2] Create availability block
  ✓ PASS: HTTP 201 - block created successfully
  ✓ PASS: Block ID extracted: 123e4567-e89b-12d3-a456-426614174000

[TEST 3] Create overlapping block (expect 409 conflict)
  ✓ PASS: HTTP 409 - overlap correctly rejected

[TEST 4] Read single availability block
  ✓ PASS: HTTP 200 - block retrieved successfully
  ✓ PASS: Block ID matches created block

[TEST 5] Delete availability block (cleanup)
  ✓ PASS: HTTP 204 - block deleted successfully

[TEST 6] Verify block deletion (expect 404)
  ✓ PASS: HTTP 404 - block no longer exists (verified)

======================================================================
Test Summary
======================================================================

Tests run:    6
Tests passed: 6
Tests failed: 0

  ✓ PASS: ✓ ALL TESTS PASSED
```

Exit code: `0`

### Troubleshooting

**Problem**: Test 1 fails with 401 Unauthorized

**Solution**:
```bash
# 1. Verify JWT_TOKEN is valid and not expired
echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .exp

# 2. Check JWT has admin or manager role
echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq .role

# 3. Get fresh token from /api/v1/auth/login
curl -X POST https://api.fewo.kolibri-visions.de/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"..."}'
```

**Problem**: Test 1 fails with 404 Property not found

**Solution**:
```bash
# 1. Verify property exists and belongs to your agency
curl -H "Authorization: Bearer $JWT_TOKEN" https://api.fewo.kolibri-visions.de/api/v1/properties

# 2. Use a valid PID from the response
PID=<valid-property-uuid> JWT_TOKEN="..." ./backend/scripts/pms_availability_phase21_smoke.sh
```

**Problem**: Test 3 fails - overlap not rejected (expected 409, got 201)

**Cause**: Database EXCLUSION constraint not working or migration not applied

**Solution**:
```bash
# 1. Verify btree_gist extension enabled
psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname='btree_gist';"

# 2. Verify EXCLUSION constraint exists
psql $DATABASE_URL -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='inventory_ranges_no_overlap';"

# 3. Re-apply migration if missing
psql $DATABASE_URL -f supabase/migrations/20251225190000_availability_inventory_system.sql
```

**Problem**: Test 2 fails with 422 Validation Error (invalid date range)

**Cause**: AVAIL_FROM is in the past or AVAIL_TO <= AVAIL_FROM

**Solution**:
```bash
# Use explicit future dates
AVAIL_FROM=2026-06-01 AVAIL_TO=2026-06-08 JWT_TOKEN="..." PID="..." ./backend/scripts/pms_availability_phase21_smoke.sh
```

**Problem**: Test 5 fails with 503 Service Unavailable

**Cause**: Database temporarily unavailable or connection pool exhausted

**Solution**:
```bash
# 1. Check database connectivity
psql $DATABASE_URL -c "SELECT 1;"

# 2. Check API health
curl https://api.fewo.kolibri-visions.de/health

# 3. Wait 30 seconds and retry (automatic retry with exponential backoff already in API)
```

### Production Verification Procedure

To mark Phase 21 as **VERIFIED** in project_status.md:

1. **Get JWT token** from authenticated session or login endpoint
2. **Get valid PID** from properties list:
   ```bash
   curl -H "Authorization: Bearer $JWT_TOKEN" https://api.fewo.kolibri-visions.de/api/v1/properties | jq -r '.items[0].id'
   ```
3. **Run smoke script**:
   ```bash
   JWT_TOKEN="eyJhbG..." PID="550e8400-..." ./backend/scripts/pms_availability_phase21_smoke.sh
   ```
4. **Verify exit code** is `0` and all 6 tests pass
5. **Update project_status.md**: Change status from "IMPLEMENTED" to "VERIFIED" and add verification evidence

### Related Sections

- [Availability API Documentation](#availability-api) (if exists)
- [Database Schema - Availability Tables](#database-schema) (if exists)

---

## Admin UI: Booking & Property Detail Pages

✅ **Verified in PROD on 2026-01-07** (source_commit a22da6660b7ad24a309429249c1255e575be37bc, smoke script exit code 0)

**Autodiscovery Note**:
- Autodiscovery requires list endpoints (`GET /api/v1/bookings?limit=1&offset=0`, `GET /api/v1/properties?limit=1&offset=0`) to return valid JSON with at least one item.
- If autodiscovery fails (empty database, auth error, session termination), bypass with explicit IDs:
  ```bash
  BID=your-booking-id PID=your-property-id TOKEN=... ./backend/scripts/pms_admin_detail_endpoints_smoke.sh
  ```
- For troubleshooting details, see [Scripts README: Troubleshooting Autodiscovery](../../scripts/README.md#troubleshooting-autodiscovery).

### Overview

The Admin UI provides detail pages for individual bookings and properties. These pages fetch full entity data via single-item GET endpoints and display comprehensive information.

### Booking Detail Page

**URL**: `https://admin.fewo.kolibri-visions.de/bookings/{id}`

**API Endpoint**: `GET /api/v1/bookings/{id}`

**Requires**: JWT authentication (session cookie or Authorization header)

**Features**:
- **Header**: booking_reference, status badge (includes "requested" and "under_review")
- **Dates & Stay**: check_in, check_out, num_nights
- **Guest Info**: guest_id with link to `/guests/{guest_id}` (handles null guest gracefully)
- **Price Breakdown**: nightly_rate, subtotal, cleaning_fee, service_fee, tax, total_price, currency
- **IDs**: booking id, property_id, guest_id, channel_booking_id (if present)
- **Metadata**: created_at, updated_at
- **Special Requests / Internal Notes**: displayed if present
- **Navigation**: "← Zurück zur Buchungsliste" link
- **Error States**: German messages for 401, 403, 404, 503 with retry button

### Property Detail Page

**URL**: `https://admin.fewo.kolibri-visions.de/properties/{id}`

**API Endpoint**: `GET /api/v1/properties/{id}`

**Requires**: JWT authentication

**Features**:
- **Header**: internal_name/name/title, status badge (aktiv/inaktiv/gelöscht)
- **Address**: address_line1/2, postal_code, city, country
- **Capacity**: max_guests, bedrooms, beds, bathrooms
- **Times**: check_in_time, check_out_time
- **Pricing**: base_price, cleaning_fee, currency, min_stay, booking_window_days
- **IDs**: property id, agency_id
- **Metadata**: created_at, updated_at, deleted_at (if soft-deleted)
- **Navigation**: "← Zurück zur Objektliste" link
- **Error States**: German messages for 401, 403, 404, 503 with retry button

### Browser Verification Steps

**Step 1: Verify Booking Detail**

```bash
# Login to Admin UI
open https://admin.fewo.kolibri-visions.de/login
# Login with admin credentials

# Navigate to bookings list
open https://admin.fewo.kolibri-visions.de/bookings

# Click on any booking row

# Expected:
# - Navigates to /bookings/{id} detail page
# - Page loads without "Failed to fetch" error
# - Status badge shows correct color:
#   - "requested" → blue
#   - "under_review" → purple
#   - "confirmed" → green
#   - "pending" → yellow
#   - "cancelled" → red
# - Guest section handles null guest gracefully (shows guest_id + link, no crash)
# - Price breakdown shows all fields with correct formatting
# - Retry button appears if error occurs
```

**Step 2: Verify Property Detail**

```bash
# Navigate to properties list
open https://admin.fewo.kolibri-visions.de/properties

# Click on any property row

# Expected:
# - Navigates to /properties/{id} detail page
# - Page loads without error
# - Status badge shows: Aktiv (green) / Inaktiv (gray) / Gelöscht (red)
# - Address section shows all available address fields
# - Capacity and pricing sections display available data
# - "—" shown for missing optional fields
# - Retry button appears if error occurs
```

### Troubleshooting

**Problem**: Detail page returns "Session abgelaufen. Bitte melden Sie sich erneut an." (401)

**Root Cause**: JWT token expired or missing

**Solution**:
```bash
# 1. Check if session cookie exists
# Browser DevTools → Application → Cookies → admin.fewo.kolibri-visions.de
# Should see: sb-*-auth-token cookies

# 2. Re-login via /login page if cookies missing or expired
open https://admin.fewo.kolibri-visions.de/login

# 3. If cookies exist but still 401, check token in Authorization header
# Network tab → Request Headers → Authorization: Bearer <token>
# TOKEN must be access_token (not refresh_token)
# Expected length: ~616 characters
# JWT parts: 3 (header.payload.signature)

# 4. Verify JWT claims:
# Open browser console:
const token = localStorage.getItem('supabase.auth.token');
# Decode at jwt.io - should include: sub, email, role, agency_id
```

**Problem**: Detail page returns "Keine Berechtigung, dieses Objekt/diese Buchung anzuzeigen." (403)

**Root Cause**: User role lacks permission or agency_id mismatch

**Solution**:
```bash
# 1. Check user role in JWT claims
# Network tab → Response Headers from any API call
# Or decode TOKEN and check "role" claim

# 2. Verify RLS policies allow access
# Database console:
SELECT * FROM pg_policies WHERE tablename IN ('bookings', 'properties');
# Ensure policy allows current user's role and agency_id

# 3. Check agency_id in JWT matches entity's agency_id
# Decode JWT → check agency_id claim
# Compare with entity: SELECT agency_id FROM bookings WHERE id = '...';
```

**Problem**: Detail page returns "Objekt/Buchung nicht gefunden." (404)

**Root Cause**: Entity doesn't exist or was soft-deleted

**Solution**:
```bash
# 1. Verify entity exists in database
# Database console:
SELECT id, deleted_at FROM bookings WHERE id = '...';
SELECT id, deleted_at FROM properties WHERE id = '...';

# 2. If soft-deleted (deleted_at NOT NULL), entity is hidden from detail view
# Admin UI doesn't show deleted entities by design

# 3. Check if ID was copied correctly from list page
# Compare URL: /bookings/{id} with database ID
```

**Problem**: Detail page returns "Service vorübergehend nicht verfügbar." (503)

**Root Cause**: Backend database unavailable or schema drift

**Solution**:
```bash
# 1. Check backend health
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq .

# Expected: {"status": "up", "components": {"db": {"status": "up"}, ...}}
# If db: "down", see [DB DNS / Degraded Mode](#db-dns--degraded-mode)

# 2. Check backend logs for schema errors
docker logs pms-backend --tail 100 | grep -i "error\|503"

# Look for: "Relation does not exist", "column ... does not exist"
# If schema errors, see [Schema Drift](#schema-drift)

# 3. Verify detail endpoint works via curl
export TOKEN="..."
export API_BASE_URL="https://api.fewo.kolibri-visions.de"

curl -sS -i -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/bookings/{id}" | head -20
# Expected: HTTP/2 200

curl -sS -i -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/properties/{id}" | head -20
# Expected: HTTP/2 200
```

**Problem**: Booking detail returns "500 Internal Server Error" with "ResponseValidationError: cancelled_by"

✅ **Fixed and Verified in PROD on 2026-01-07** (source_commit a22da6660b7ad24a309429249c1255e575be37bc, smoke script exit code 0)

**Root Cause**: Legacy data in database has UUID values in `cancelled_by` field instead of expected actor enum ('guest', 'host', 'platform', 'system').

**Solution**:
```bash
# This is now fixed via backward-compatible normalization.
# The service layer automatically maps:
# - UUID values → actor='host', cancelled_by_user_id=<uuid>
# - Valid actors → preserved as-is
# - Invalid values → actor='system' (safe fallback)

# Verify fix is deployed:
curl -sS -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/bookings/{id}" | jq -r '.cancelled_by, .cancelled_by_user_id'

# Expected output for legacy UUID data:
# "host"
# "8036f477-1234-5678-9abc-def012345678"

# Expected output for standard actor data:
# "guest"
# null

# If still seeing 500 errors, check backend logs for ResponseValidationError
docker logs pms-backend --tail 50 | grep -i "validationerror"
```

**Prevention**: All new cancellations should use actor enum values. The `cancelled_by_user_id` field preserves user identity when needed.

### Verification (SERVER-SIDE)

**Automated Smoke Test**:

```bash
# HOST-SERVER-TERMINAL

# Set TOKEN (obtain from Admin UI login or Supabase dashboard)
export TOKEN="eyJhbGc..."

# Run smoke test (auto-discovers booking and property IDs)
./backend/scripts/pms_admin_detail_endpoints_smoke.sh

# Expected output:
# [INFO] All tests passed! ✓
# [INFO] Booking detail endpoint: OK
# [INFO] Property detail endpoint: OK
# [INFO] CORS headers: OK

# Exit code 0 = success
# Exit code 1 = failure (404, 401, 403, or missing data)
# Exit code 2 = server error (500 - regression!)
```

**Manual API Verification**:

```bash
# HOST-SERVER-TERMINAL
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export TOKEN="..."

# Get booking ID from list
BID=$(curl -sS -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/bookings?limit=1&offset=0" | jq -r '.items[0].id // .[0].id')

echo "Testing booking ID: $BID"

# Test booking detail endpoint
curl -sS -i -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/bookings/$BID" | head -30

# Expected: HTTP/2 200
# Body includes: booking_reference, status, total_price, etc.

# Get property ID from list
PID=$(curl -sS -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/properties?limit=1&offset=0" | jq -r '.items[0].id // .[0].id')

echo "Testing property ID: $PID"

# Test property detail endpoint
curl -sS -i -H "Authorization: Bearer $TOKEN" \
  "$API_BASE_URL/api/v1/properties/$PID" | head -30

# Expected: HTTP/2 200
# Body includes: internal_name, address fields, capacity, pricing, etc.
```

**Deploy Verification**:

```bash
# HOST-SERVER-TERMINAL

# Verify deployed commit
curl -s "$API_BASE_URL/api/v1/ops/version" | jq -r '.source_commit, .started_at'

# Run deploy verification script (checks commit match + modules)
EXPECT_COMMIT=<commit-sha> ./backend/scripts/pms_verify_deploy.sh

# Exit code 0 = commit matches and backend healthy
```

### Related Sections

- [Admin UI: Bookings & Properties Lists](#admin-ui-bookings--properties-lists) - List pages that link to these detail pages
- [Booking Status Validation Error (500)](#booking-status-validation-error-500) - For status field validation issues
- [Admin UI Authentication Verification](#admin-ui-authentication-verification) - For cookie-based SSR auth checks
- [CORS Errors (Admin Console Blocked)](#cors-errors-admin-console-blocked) - For CORS configuration

## Full Sync Batching (batch_id)

**Purpose:** Full Sync operations trigger 3 concurrent tasks (availability_update, pricing_update, bookings_sync) grouped by a shared `batch_id` for easier tracking and verification.

**Migration:** `supabase/migrations/20260101150000_add_batch_id_to_channel_sync_logs.sql`

### How It Works

When triggering a Full Sync via:
```bash
curl -X POST https://api.fewo.kolibri-visions.de/api/v1/channel-connections/{connection_id}/sync \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "full"}'
```

**Response includes batch_id:**
```json
{
  "status": "triggered",
  "message": "Manual full sync triggered successfully",
  "task_ids": ["task_1", "task_2", "task_3"],
  "batch_id": "70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11"
}
```

All 3 operations (availability_update, pricing_update, bookings_sync) share the same `batch_id`.

### Verification via API

**List all sync logs (includes batch_id):**
```bash
curl https://api.fewo.kolibri-visions.de/api/v1/channel-connections/{connection_id}/sync-logs \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected response:**
```json
{
  "connection_id": "...",
  "logs": [
    {
      "id": "...",
      "operation_type": "availability_update",
      "status": "success",
      "batch_id": "70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11",
      "created_at": "2026-01-01T12:00:00Z",
      "task_id": "..."
    },
    {
      "id": "...",
      "operation_type": "pricing_update",
      "status": "success",
      "batch_id": "70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11",
      "created_at": "2026-01-01T12:00:00Z",
      "task_id": "..."
    },
    {
      "id": "...",
      "operation_type": "bookings_sync",
      "status": "success",
      "batch_id": "70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11",
      "created_at": "2026-01-01T12:00:00Z",
      "task_id": "..."
    }
  ]
}
```

**Filter logs by batch_id:**
```bash
curl "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/{connection_id}/sync-logs?batch_id=70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Verification via Database

**Count operations per batch:**
```sql
SELECT
  batch_id,
  COUNT(*) as operation_count,
  ARRAY_AGG(DISTINCT operation_type ORDER BY operation_type) as operations,
  ARRAY_AGG(DISTINCT status ORDER BY status) as statuses,
  MIN(created_at) as first_created,
  MAX(created_at) as last_created
FROM channel_sync_logs
WHERE batch_id IS NOT NULL
GROUP BY batch_id
ORDER BY first_created DESC
LIMIT 10;
```

**Expected output for Full Sync:**
```
              batch_id              | operation_count |                   operations                   | statuses | first_created | last_created
------------------------------------+-----------------+------------------------------------------------+----------+---------------+--------------
 70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11 |               3 | {availability_update,bookings_sync,pricing_update} | {success}| 2026-01-01... | 2026-01-01...
```

**Find incomplete batches (not all 3 operations succeeded):**
```sql
SELECT
  batch_id,
  COUNT(*) as total_ops,
  COUNT(*) FILTER (WHERE status = 'success') as success_count,
  COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
  ARRAY_AGG(operation_type || ':' || status) as op_statuses
FROM channel_sync_logs
WHERE batch_id IS NOT NULL
GROUP BY batch_id
HAVING COUNT(*) FILTER (WHERE status = 'success') < 3
ORDER BY MAX(created_at) DESC
LIMIT 10;
```

### UI Display

The Admin UI (`/connections` page) automatically groups Full Sync operations by `batch_id`:

**Batch Header Features:**
- **Collapsible indigo card** with expand/collapse arrow icon
- **Overall batch status badge** (Success/Failed/Running/Pending):
  - Green "Success" = all 3 operations succeeded
  - Red "Failed" = any operation failed
  - Blue "Running" = operations in progress
  - Gray "Pending" = operations queued/triggered
- **Batch ID display** with copy button (click to copy full UUID)
  - Shows shortened ID: `70bce471...`
  - Copies full UUID on click
- **Timestamp** from newest operation
- **Operation count** with filter indicator (e.g., "2 operations (filtered)" if filters active)
- **Operation badges** showing each operation with status-coded color:
  - Full labels without truncation (e.g., "availability update", "pricing update", "bookings sync")
  - Color matches status (green/red/blue/gray)

**Expanded Batch View:**
- Click batch header to expand/collapse
- Shows table with: Operation, Status, Error, Actions
- "Details" button opens log details modal
- Expansion state preserved across auto-refresh

**Filtering Behavior:**
- Filters (status/type) work with batched logs
- Batch visible if ANY operation matches filter
- Shows only matching operations inside batch
- Displays "(filtered)" indicator if fewer than 3 operations shown

**Unbatched Logs:**
- Logs without `batch_id` (old logs, manual single operations) appear in standard flat table
- Backward compatible with pre-migration logs

### Troubleshooting

**Problem:** API `/sync-logs` does not include `batch_id` field

**Diagnosis:**
```bash
# Check if migration applied
docker exec -it pms-db psql -U postgres -d postgres \
  -c "\d channel_sync_logs" | grep batch_id
```

**Expected:** `batch_id | uuid |`

**If missing:**
```bash
# Apply migration
docker exec -i pms-db psql -U postgres -d postgres \
  < supabase/migrations/20260101150000_add_batch_id_to_channel_sync_logs.sql
```

**Restart API after migration:**
```bash
docker restart pms-api
```

**Problem:** Old logs show `batch_id: null` in API response

**Cause:** Logs created before migration have `NULL` batch_id (expected, backward compatible)

**Verification:** Only logs created after migration + restart will have batch_id populated

---

## Batch Status Aggregation

**Purpose:** Query aggregated batch status for monitoring and UI display without fetching individual log entries.

**Endpoint:**
```
GET /api/v1/channel-connections/{connection_id}/sync-batches/{batch_id}
```

**Use Cases:**

- **Admin UI:** Display batch progress card with overall status badge (green/red/blue)
- **Monitoring:** Quick health check for batch completion without parsing logs
- **Debugging:** Identify which operation(s) in a batch failed
- **Dashboards:** Show batch completion rate (success vs. failed)

**Request Example:**

```bash
# Production
curl -k -sS https://api.fewo.kolibri-visions.de/api/v1/channel-connections/abc-123-def-456/sync-batches/70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11 \
  -H "Authorization: Bearer $TOKEN" \
  | jq .

# Local (via Supabase auth)
TOKEN=$(curl -sX POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access_token')

curl -sS "$API/api/v1/channel-connections/$CID/sync-batches/$BATCH_ID" \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

**Response Example (Success):**

```json
{
  "batch_id": "70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11",
  "connection_id": "abc-123-def-456",
  "batch_status": "success",
  "status_counts": {
    "triggered": 0,
    "running": 0,
    "success": 3,
    "failed": 0,
    "other": 0
  },
  "created_at_min": "2026-01-01T12:00:00Z",
  "updated_at_max": "2026-01-01T12:05:30Z",
  "operations": [
    {
      "operation_type": "availability_update",
      "status": "success",
      "updated_at": "2026-01-01T12:03:15Z"
    },
    {
      "operation_type": "pricing_update",
      "status": "success",
      "updated_at": "2026-01-01T12:04:20Z"
    },
    {
      "operation_type": "bookings_sync",
      "status": "success",
      "updated_at": "2026-01-01T12:05:30Z"
    }
  ]
}
```

**Response Example (Failed):**

```json
{
  "batch_id": "70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11",
  "connection_id": "abc-123-def-456",
  "batch_status": "failed",
  "status_counts": {
    "triggered": 0,
    "running": 0,
    "success": 2,
    "failed": 1,
    "other": 0
  },
  "created_at_min": "2026-01-01T12:00:00Z",
  "updated_at_max": "2026-01-01T12:05:30Z",
  "operations": [
    {
      "operation_type": "availability_update",
      "status": "success",
      "updated_at": "2026-01-01T12:03:15Z"
    },
    {
      "operation_type": "pricing_update",
      "status": "failed",
      "updated_at": "2026-01-01T12:04:20Z"
    },
    {
      "operation_type": "bookings_sync",
      "status": "success",
      "updated_at": "2026-01-01T12:05:30Z"
    }
  ]
}
```

**Batch Status Logic:**

The `batch_status` field is derived from status counts:

| Condition | batch_status | Meaning |
|-----------|--------------|---------|
| `failed > 0` | `failed` | At least one operation failed (batch incomplete) |
| `running > 0` OR `triggered > 0` | `running` | Operations still in progress (no failures yet) |
| `success == total` AND `total > 0` | `success` | All operations completed successfully |
| None of above | `unknown` | No operations found or unexpected state |

**Priority:** Failed > Running > Success > Unknown

**Status Semantics: Queued vs. Triggered**

**Queued Status:**

Operations with `status = 'queued'` are **counted under the "Triggered" bucket** in `status_counts.triggered`. This ensures correct batch status when the Celery worker is offline or overloaded.

| Individual Status | Bucket in status_counts | Meaning |
|-------------------|------------------------|---------|
| `triggered` | `triggered` | Sync task created, waiting for worker pickup |
| `queued` | `triggered` | Task enqueued in Celery, worker not processing yet |
| `running` | `running` | Worker actively processing task |
| `success` | `success` | Task completed successfully |
| `failed` | `failed` | Task failed (exhausted retries or unrecoverable error) |
| Other | `other` | Unknown/unexpected status (should not occur) |

**Why Queued = Triggered:**

- **Semantically:** Both `queued` and `triggered` represent "in-progress but not yet running"
- **User Expectation:** Users expect batch_status="running" when sync is triggered, even if worker is offline
- **Prior Bug:** When worker was stopped, `queued` counted as `other`, causing batch_status="unknown" (misleading)

**Reproduction Steps (Worker Offline Scenario):**

1. **Stop worker:** `docker stop pms-worker-v2` (or systemctl stop)
2. **Trigger full sync:** POST `/api/v1/channel-connections/{id}/sync?sync_type=full`
   - API returns 200 with batch_id
   - 3 operations created with status="queued" (Celery task enqueued but not picked up)
3. **Check batch status:** GET `/api/v1/channel-connections/{id}/sync-batches/{batch_id}`
   - **Expected:** `batch_status="running"`, `status_counts.triggered=3` (queued counted as triggered)
   - **Before fix:** `batch_status="unknown"`, `status_counts.other=3` (misleading)
4. **Start worker:** `docker start pms-worker-v2`
   - Worker picks up queued tasks
   - Operations transition: `queued` → `running` → `success`/`failed`
5. **Final check:** Batch status becomes `success` (if all ops succeed) or `failed` (if any fail)

**SQL Implementation:**

```sql
-- Triggered count includes both triggered and queued
COUNT(*) FILTER (WHERE status IN ('triggered', 'queued')) AS triggered_count

-- Other count excludes queued
COUNT(*) FILTER (WHERE status NOT IN ('triggered', 'queued', 'running', 'success', 'failed')) AS other_count

-- Batch status derivation treats triggered>0 as running
CASE
  WHEN COUNT(*) FILTER (WHERE status = 'failed') > 0 THEN 'failed'
  WHEN COUNT(*) FILTER (WHERE status = 'running') > 0
    OR COUNT(*) FILTER (WHERE status IN ('triggered', 'queued')) > 0 THEN 'running'
  WHEN COUNT(*) FILTER (WHERE status = 'success') = COUNT(*) AND COUNT(*) > 0 THEN 'success'
  ELSE 'unknown'
END AS batch_status
```

**Use in Admin UI:**

```javascript
// Fetch batch status
const response = await fetch(
  `/api/v1/channel-connections/${connectionId}/sync-batches/${batchId}`,
  { headers: { Authorization: `Bearer ${token}` } }
);
const batch = await response.json();

// Display badge based on batch_status
const badgeColor = {
  success: 'green',
  failed: 'red',
  running: 'blue',
  unknown: 'gray'
}[batch.batch_status];

// Show progress: "2/3 operations completed"
const completed = batch.status_counts.success + batch.status_counts.failed;
const total = Object.values(batch.status_counts).reduce((a, b) => a + b, 0);
```

**Performance:**

- **Single SQL query** with CTEs (batch_aggregation + operations_list)
- **Efficient aggregation** using `COUNT(*) FILTER (WHERE ...)` (PostgreSQL 9.4+)
- **Scoped by connection_id** (prevents cross-tenant leaks)
- **Indexed columns:** `batch_id`, `connection_id`, `status`, `created_at`

**Error Responses:**

```bash
# 404 - Batch not found
{
  "error": "batch_not_found",
  "message": "No sync operations found for batch_id=... and connection_id=..."
}

# 503 - Schema not installed
{
  "error": "service_unavailable",
  "message": "Channel sync logs schema not installed..."
}

# 401 - Not authenticated
{
  "detail": "Not authenticated"
}
```

**Monitoring Examples:**

```bash
# Check if batch completed successfully
BATCH_STATUS=$(curl -sS "$API/api/v1/channel-connections/$CID/sync-batches/$BATCH_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.batch_status')

if [[ "$BATCH_STATUS" == "success" ]]; then
  echo "✅ Batch completed successfully"
  exit 0
elif [[ "$BATCH_STATUS" == "failed" ]]; then
  echo "❌ Batch failed - check logs"
  exit 1
elif [[ "$BATCH_STATUS" == "running" ]]; then
  echo "⏳ Batch still in progress"
  exit 2
else
  echo "❓ Unknown batch status"
  exit 3
fi

# Get failed operations count
FAILED_COUNT=$(curl -sS "$API/api/v1/channel-connections/$CID/sync-batches/$BATCH_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.status_counts.failed')

if [[ "$FAILED_COUNT" -gt 0 ]]; then
  echo "⚠️  $FAILED_COUNT operation(s) failed in batch"
fi
```

**Related:**

- See [Full Sync Batching (batch_id)](#full-sync-batching-batch_id) for batch grouping concept
- See [GET /sync-logs](#get-sync-logs) for individual log entries
- See [Admin UI - Channel Manager Operations](#admin-ui--channel-manager-operations) for UI usage

---

## List Sync Batches

**Purpose:** List recent sync batches for a connection with pagination and optional status filtering. Used by Admin UI "Sync history" page.

**Endpoint:**
```
GET /api/v1/channel-connections/{connection_id}/sync-batches
```

**Query Parameters:**
- `limit` (int, default: 50, max: 200): Number of batches to return
- `offset` (int, default: 0): Offset for pagination
- `status` (optional string): Filter by batch status
  - Omit or `any`: Return all batches regardless of status
  - `running`: Return batches where any operation is triggered or running (and none failed)
  - `failed`: Return batches where any operation failed
  - `success`: Return batches where all operations are success (and none failed/running/triggered)

**Sorting:**
- Newest first by `updated_at_max` (most recently updated batch)
- Falls back to `created_at_min` for batches with no updates

**Use Cases:**

- **Admin UI:** Display sync history with pagination
- **Monitoring:** Find recent failed batches for alerting
- **Debugging:** Track sync operations over time
- **Dashboards:** Show sync success rate and trends

**Request Examples:**

```bash
# Production - List first 20 batches
curl -k -sS https://api.fewo.kolibri-visions.de/api/v1/channel-connections/abc-123-def-456/sync-batches?limit=20&offset=0 \
  -H "Authorization: Bearer $TOKEN" \
  | jq .

# Production - List only failed batches
curl -k -sS https://api.fewo.kolibri-visions.de/api/v1/channel-connections/abc-123-def-456/sync-batches?status=failed \
  -H "Authorization: Bearer $TOKEN" \
  | jq .

# Production - Pagination (second page, 50 items per page)
curl -k -sS https://api.fewo.kolibri-visions.de/api/v1/channel-connections/abc-123-def-456/sync-batches?limit=50&offset=50 \
  -H "Authorization: Bearer $TOKEN" \
  | jq .

# Local (via Supabase auth)
TOKEN=$(curl -sX POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access_token')

curl -sS "$API/api/v1/channel-connections/$CID/sync-batches?status=running" \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

**Response Example:**

```json
{
  "items": [
    {
      "batch_id": "70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11",
      "connection_id": "abc-123-def-456",
      "batch_status": "success",
      "status_counts": {
        "triggered": 0,
        "running": 0,
        "success": 3,
        "failed": 0,
        "other": 0
      },
      "created_at_min": "2026-01-01T12:00:00Z",
      "updated_at_max": "2026-01-01T12:05:30Z",
      "operations": [
        {
          "operation_type": "availability_update",
          "status": "success",
          "updated_at": "2026-01-01T12:03:15Z"
        },
        {
          "operation_type": "pricing_update",
          "status": "success",
          "updated_at": "2026-01-01T12:04:20Z"
        },
        {
          "operation_type": "bookings_sync",
          "status": "success",
          "updated_at": "2026-01-01T12:05:30Z"
        }
      ]
    },
    {
      "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "connection_id": "abc-123-def-456",
      "batch_status": "failed",
      "status_counts": {
        "triggered": 0,
        "running": 0,
        "success": 2,
        "failed": 1,
        "other": 0
      },
      "created_at_min": "2026-01-01T10:00:00Z",
      "updated_at_max": "2026-01-01T10:08:45Z",
      "operations": [
        {
          "operation_type": "availability_update",
          "status": "success",
          "updated_at": "2026-01-01T10:03:20Z"
        },
        {
          "operation_type": "pricing_update",
          "status": "failed",
          "updated_at": "2026-01-01T10:05:15Z"
        },
        {
          "operation_type": "bookings_sync",
          "status": "success",
          "updated_at": "2026-01-01T10:08:45Z"
        }
      ]
    }
  ],
  "limit": 50,
  "offset": 0
}
```

**Status Filter Mapping:**

| Filter Value | SQL Logic | Description |
|--------------|-----------|-------------|
| Omit or `any` | No filter applied | Return all batches |
| `running` | `failed_count = 0 AND (running_count > 0 OR triggered_count > 0)` | At least one operation in progress, none failed |
| `failed` | `failed_count > 0` | At least one operation failed |
| `success` | `failed_count = 0 AND running_count = 0 AND triggered_count = 0 AND success_count = total_count AND total_count > 0` | All operations succeeded |

**Performance:**

- **Single SQL query** with CTEs (batch_aggregation + operations_per_batch)
- **Efficient aggregation** using `COUNT(*) FILTER (WHERE ...)` and `json_agg()`
- **Status filter in SQL** (WHERE clause on derived batch_status)
- **Scoped by connection_id** (prevents cross-tenant leaks)
- **Indexed columns:** `batch_id`, `connection_id`, `status`, `created_at`, `updated_at`

**Error Responses:**

```bash
# 400 - Invalid status parameter
{
  "error": "invalid_status",
  "message": "Status must be one of: any, running, failed, success (got 'invalid')"
}

# 503 - Schema not installed
{
  "error": "service_unavailable",
  "message": "Channel sync logs schema not installed..."
}

# 401 - Not authenticated
{
  "detail": "Not authenticated"
}
```

**Monitoring Examples:**

```bash
# Count total batches (all statuses)
curl -sS "$API/api/v1/channel-connections/$CID/sync-batches?limit=200" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.items | length'

# Find recent failed batches (last 10)
curl -sS "$API/api/v1/channel-connections/$CID/sync-batches?status=failed&limit=10" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.items[] | {batch_id, created_at_min, failed_count: .status_counts.failed}'

# Check if any batches are currently running
RUNNING_COUNT=$(curl -sS "$API/api/v1/channel-connections/$CID/sync-batches?status=running&limit=1" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.items | length')

if [[ "$RUNNING_COUNT" -gt 0 ]]; then
  echo "⏳ Sync operations in progress"
else
  echo "✅ No active syncs"
fi

# Pagination example - fetch all batches (handling large result sets)
OFFSET=0
LIMIT=50
while true; do
  RESPONSE=$(curl -sS "$API/api/v1/channel-connections/$CID/sync-batches?limit=$LIMIT&offset=$OFFSET" \
    -H "Authorization: Bearer $TOKEN")

  COUNT=$(echo "$RESPONSE" | jq '.items | length')

  if [[ "$COUNT" -eq 0 ]]; then
    break
  fi

  echo "$RESPONSE" | jq -c '.items[]'

  OFFSET=$((OFFSET + LIMIT))
done
```

**Use in Admin UI:**

```javascript
// Fetch recent batches with status filter
const fetchBatches = async (connectionId, status = 'any', limit = 50, offset = 0) => {
  const params = new URLSearchParams({ limit, offset });
  if (status !== 'any') {
    params.append('status', status);
  }

  const response = await fetch(
    `/api/v1/channel-connections/${connectionId}/sync-batches?${params}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );

  return await response.json();
};

// Display batches with pagination
const { items: batches, limit, offset } = await fetchBatches(connectionId, 'failed');

batches.forEach(batch => {
  console.log(`Batch ${batch.batch_id}: ${batch.batch_status}`);
  console.log(`  Operations: ${batch.operations.length}`);
  console.log(`  Success: ${batch.status_counts.success}, Failed: ${batch.status_counts.failed}`);
});

// Infinite scroll / pagination
const nextPage = await fetchBatches(connectionId, 'any', limit, offset + limit);
```

**Related:**

- See [Batch Status Aggregation](#batch-status-aggregation) for single batch status details
- See [Full Sync Batching (batch_id)](#full-sync-batching-batch_id) for batch grouping concept
- See [GET /sync-logs](#get-sync-logs) for individual log entries

---

## Admin UI - Sync History Integration

**Purpose:** The Admin UI provides a user-friendly interface for viewing and managing channel sync history using the batch list and batch detail endpoints.

**Location:** `/connections` page → Connection Details modal → **Sync History** section

**Features:**

1. **Batch List View:**
   - Displays recent sync batches in a paginated table
   - Status filter dropdown (Any, Running, Failed, Success)
   - Table columns:
     - **Updated**: Most recent update timestamp (updated_at_max)
     - **Status**: Visual badge (green/red/blue/gray) indicating batch_status
     - **Counts**: Icon-based summary (✓ success, ✗ failed, ⟳ running, ⋯ triggered)
     - **Operations**: Emoji indicators for operation types (📅 availability, 💰 pricing, 🔄 bookings)
     - **Batch ID**: Truncated UUID with copy button
   - Pagination: Previous/Next buttons (20 batches per page)

2. **Batch Detail Modal:**
   - Click any batch row to open detailed view
   - Nested modal (z-60) overlays connection details modal
   - Sections:
     - **Batch Summary**: Status, created/updated timestamps, total operations
     - **Status Breakdown**: Visual grid showing counts for each status
     - **Operations List**: Individual operations with status badges and timestamps
     - **Troubleshooting Hint**: Yellow warning box for failed batches with runbook reference

**API Integration:**

```javascript
// Fetch batch list
GET /api/v1/channel-connections/{connectionId}/sync-batches?limit=20&offset=0&status=any

// Fetch batch detail
GET /api/v1/channel-connections/{connectionId}/sync-batches/{batchId}
```

**Auto-Refresh Behavior:**

- Batch list refreshes when:
  - Connection details modal is opened
  - Status filter is changed
  - Pagination buttons are clicked
- No auto-polling for batch list (user must manually refresh)
- Batch detail loaded on-demand when row is clicked

**Error Handling:**

| Error | UI Behavior |
|-------|-------------|
| 401/403 | Modal remains open, error logged to console (no user-facing alert) |
| 503 (DB schema drift) | Empty batch list, error logged to console |
| Network error | Empty batch list, error logged to console |

**User Flow Example:**

1. Admin opens connection details for connection `abc-123-def-456`
2. Scrolls to **Sync History** section (below Sync Logs)
3. Selects "Failed" from status filter dropdown → Only failed batches shown
4. Clicks a batch row → Batch detail modal opens
5. Reviews status breakdown → Sees 2/3 operations succeeded, 1 failed
6. Reads troubleshooting hint → "Check worker logs / runbook.md"
7. Closes batch detail modal → Returns to batch list
8. Clicks "Next" → Loads next 20 batches (offset=20)

**Production Access:**

- **URL**: `https://fewo.kolibri-visions.de/connections`
- **Auth**: Requires valid JWT token (admin role recommended for full access)
- **Browser Console**: Check network tab for API requests/responses if batches don't load

**Troubleshooting:**

**Problem:** Batch list is empty despite recent syncs

**Possible Causes:**
- No batches match current status filter (try "Any")
- All batches are on later pages (click "Next")
- Database schema drift (check API response in network tab for 503 errors)
- Connection has no sync history (batches only created after batch_id feature deployed)

**Solution:**
```bash
# Check if batches exist via API
curl -sS "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync-batches?status=any&limit=100" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.items | length'

# Expected: > 0 if batches exist
```

**Problem:** Batch detail modal shows "Loading batch details..." indefinitely

**Possible Causes:**
- 404 error (batch_id not found or doesn't belong to connection_id)
- 503 error (DB schema drift)
- Network timeout

**Solution:**
- Check browser console for errors
- Verify batch_id exists: `curl ... /sync-batches/{batch_id}` via API
- Check backend logs for database connection issues

**Related:**

- See [List Sync Batches](#list-sync-batches) for API endpoint documentation
- See [Batch Status Aggregation](#batch-status-aggregation) for single batch detail endpoint
- Frontend code: `/frontend/app/connections/page.tsx`

---

## Admin UI - Batch Details & Live Status

**Purpose:** Enhanced batch detail view with real-time updates for running batches and quick access from log details.

**Features:**

### 1. Live Status Updates

When viewing a batch that is currently running:

- **Auto-Polling**: Batch details refresh every 3 seconds automatically
- **Live Indicator**: Blue "Live" badge with pulsing dot appears in header
- **Last Updated**: Timestamp shows when data was last refreshed
- **Auto-Stop**: Polling stops automatically when:
  - Batch status becomes `success`, `failed`, or `unknown`
  - All operations complete (no triggered/running operations)
  - Maximum polling time reached (60 seconds / 20 polls)

**Visual Cues:**

```
┌─────────────────────────────────────────────────┐
│ Batch Details  [🔵 Live]                        │
│ Batch ID: 70bce471-... │ Last updated: 14:23:45 │
└─────────────────────────────────────────────────┘
```

**When Polling Is Active:**

- Running batches (batch_status = "running")
- Batches with triggered or running operations (counts.triggered + counts.running > 0)

**Implementation Details:**

```typescript
// Polling logic (frontend)
useEffect(() => {
  if (!selectedBatchDetail) return;

  const isRunning = selectedBatchDetail.batch_status === "running" ||
                   (selectedBatchDetail.status_counts.triggered +
                    selectedBatchDetail.status_counts.running) > 0;

  if (!isRunning) return;

  // Poll every 3s for up to 60s (20 polls max)
  const interval = setInterval(() => {
    refreshBatchDetail();
  }, 3000);

  return () => clearInterval(interval);
}, [selectedBatchDetail]);
```

### 2. Open Batch from Log Details

Users can navigate from individual log entries to the full batch view:

**Location:** Log Details modal → Summary section

**When Visible:** Only when log entry has a `batch_id` field

**Behavior:**
1. Log Details modal shows "Batch ID" field in summary
2. "Open Batch Details →" button appears below summary
3. Click button → Log Details modal closes, Batch Details modal opens
4. Full batch status, operations list, and counts displayed

**Use Case Example:**

```
User Flow:
1. Admin clicks "Details" on a log entry in Sync Logs
2. Sees batch_id: "70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11"
3. Clicks "Open Batch Details →" button
4. Batch Details modal opens showing:
   - All 3 operations in the batch
   - Overall batch status (e.g., 2/3 success, 1 failed)
   - Status breakdown chart
   - If running: Live indicator + auto-refresh
```

**Button Appearance:**

```html
┌────────────────────────────────┐
│ Operation Type: availability   │
│ Status: success                │
│ Batch ID: 70bce471-...         │
│                                │
│      [Open Batch Details →]   │
└────────────────────────────────┘
```

### 3. Back Navigation from Batch to Log

**Purpose:** Seamless back navigation from Batch Details to Log Details modal.

**Location:** Batch Details modal → Header (left side, icon-only button)

**When Visible:** Only when batch was opened from a log entry (not standalone)

**Behavior:**
1. Batch Details header shows left arrow icon (←) button on left side (no text label)
2. Click arrow → Batch Details closes, Log Details remains visible underneath
3. Log Details shows the exact same log that opened the batch
4. If batch was opened standalone (e.g., from sync history), no back arrow appears

**Modal Stack:**
- Log Details remains open in background (z-index 60) when Batch Details opens
- Batch Details renders on top (z-index 70) with darker overlay
- Back arrow simply closes Batch Details layer, revealing Log Details underneath
- No re-fetching or state restoration needed - log modal stays in memory

**User Flow Example:**

```
Navigation Path:
1. Connections → Open → Sync Logs → Click "Details" on a log entry
2. Log Details modal opens (z-60)
3. Click "Open Batch Details →" → Batch Details overlays on top (z-70)
4. Log Details remains open underneath (not closed)
5. Click [←] arrow icon → Batch Details closes
6. Log Details is immediately visible with same content
7. Close Log Details → returns to Connection Details
```

**Visual Appearance:**

```html
┌──────────────────────────────────────────────────┐
│ [←]  Batch Details  [🔵 Live]  [×]               │
│      (icon only - no text)                       │
│ Batch ID: 70bce471-... │ Last updated: 14:23:45  │
└──────────────────────────────────────────────────┘
```

**Testing Navigation:**

1. Open Admin UI → Connections → Select connection → "Open"
2. Navigate to Sync Logs table
3. Click "Details" on any log entry with a batch_id
4. In Log Details, click "Open Batch Details →"
5. Verify: Batch Details shows [←] arrow icon (top left, no text)
6. Click the arrow icon
7. Verify: Batch Details closes, Log Details is visible immediately
8. Verify: Same log content as before (no re-fetch)
9. Alternative: Click "X" in Batch Details → closes batch, reveals log

**Implementation Notes:**

- Modal stack approach: both modals coexist in state
- Log Details NOT closed when opening Batch Details
- Source log ID tracked for conditional rendering of back arrow
- aria-label="Back to log" for accessibility (screen readers)
- Escape key and X button work as normal close actions
- Navigation is purely UI state-based (no URL routing)

### 4. Failed Batch Guidance

When viewing a batch with failed operations:

**Yellow Warning Box:**
```
⚠️ Troubleshooting
This batch has failed operations. Check worker logs for detailed error messages.
See backend/docs/ops/runbook.md for common issues and solutions.
```

**Where to Check Logs:**

```bash
# Production worker logs (Docker)
docker logs pms-worker-v2 --tail 100 --follow

# Filter for specific batch
docker logs pms-worker-v2 2>&1 | grep "70bce471-d82a-4cd9-8ad3-8c9f2e5f4a11"

# Check Celery task failures
docker logs pms-worker-v2 2>&1 | grep "Task.*failed"
```

**Common Failure Patterns:**

| Error Pattern | Likely Cause | Runbook Section |
|---------------|-------------|-----------------|
| `Database unavailable` | DB connection pool exhausted or DNS failure | [DB DNS / Degraded Mode](#db-dns--degraded-mode) |
| `Schema drift` | channel_sync_logs table missing or constraint out of date | [Schema Drift](#schema-drift) |
| `Channel adapter error` | External API timeout or rate limit | Check platform-specific sections |
| `Task timeout` | Operation exceeded soft/hard time limits | [Celery Configuration](#celery-configuration) |

### 4. Performance Characteristics

**Polling Overhead:**

- **Network**: 1 API request every 3 seconds (max 20 requests)
- **Backend**: No additional load (read-only query, indexed columns)
- **Browser**: Minimal CPU/memory (React state updates only)

**Automatic Cleanup:**

- Polling stops when batch completes → no infinite loops
- Modal close clears polling interval → no background requests
- Last updated timestamp prevents stale data confusion

**Best Practices:**

- ✅ **Do**: Let polling run for active batches (provides real-time feedback)
- ✅ **Do**: Close batch detail modal when done (stops polling immediately)
- ❌ **Don't**: Open batch details for old/completed batches expecting updates (polling won't start)
- ❌ **Don't**: Keep multiple batch detail modals open simultaneously (only one can be open at a time)

### 5. Troubleshooting Auto-Refresh & Live Updates

**Problem:** "Live" badge doesn't appear for running batch

**Possible Causes:**
- Batch status is not "running" (check batch_status field)
- All operations already completed (counts.triggered + counts.running = 0)
- Batch detail loaded before operations started (rare race condition)

**Solution:**
- Use manual Refresh button to fetch latest data
- Verify batch is actually running via API: `curl .../sync-batches/{batch_id}`

**Problem:** Auto-refresh not updating "Last refreshed" timestamp

**Possible Causes:**
- Auto-refresh toggle is OFF (unchecked)
- Network error preventing API calls (check browser console)
- Interval cleared unexpectedly (browser throttling, component error)

**Solution:**
1. Verify "Auto refresh" checkbox is checked in modal header
2. Check browser console for API errors (401/403/503)
3. Try manual Refresh button to verify API connectivity
4. If manual refresh works but auto-refresh doesn't: close and reopen modal
5. If issue persists: hard refresh page (Ctrl+F5 / Cmd+Shift+R)

**Problem:** Auto-refresh updates too slowly for running batch

**Expected Behavior:**
- Running batches: 3-second interval
- Completed batches: 10-second interval

**Debugging Steps:**
1. Check batch status in Batch Summary (should show "running" for 3s interval)
2. Verify operations list has triggered/running items
3. If batch shows "success" but has running operations: data inconsistency, use manual Refresh

**Problem:** Auto-refresh doesn't stop when toggled OFF

**Solution:**
- Expected: Interval clears immediately when unchecking toggle
- If "Last refreshed" keeps updating: component state issue, close and reopen modal
- Check browser console for React errors

**Problem:** Modal flickers/resizes during auto-refresh

**Root Cause:**
- UI was clearing data arrays (setLogs([]) / setHistory([])) before re-fetching
- Caused layout collapse → modal shrinks → data loads → modal expands
- Loading states (logsLoading / syncHistoryLoading) replaced content with "Loading..." text

**Solution (Implemented):**
- **Stale-while-revalidate pattern:** Keep existing data visible during refresh
- Separate loading states: `logsRefreshing` / `syncHistoryRefreshing` for auto-refresh vs `logsLoading` / `syncHistoryLoading` for initial load
- Stable layout heights: Added `min-h-[200px]` to content containers
- Errors during refresh don't clear existing data (graceful degradation)
- Only show "Loading..." on initial load, not on refresh

**Implementation:**
- `fetchSyncLogs(connectionId, isRefresh)` - auto-refresh calls with isRefresh=true
- `fetchSyncHistory(connectionId, isRefresh)` - auto-refresh calls with isRefresh=true
- Frontend code: `/frontend/app/connections/page.tsx:399-437` (fetchSyncLogs), `page.tsx:516-554` (fetchSyncHistory)

**Related:**

- See [Admin UI - Sync History Integration](#admin-ui---sync-history-integration) for batch list view
- See [Batch Status Aggregation](#batch-status-aggregation) for batch detail API endpoint
- See [Admin UI - Batch Details Refresh Semantics](#admin-ui---batch-details-refresh-semantics) for timestamp meanings
- Frontend code: `/frontend/app/connections/page.tsx` (refreshBatchDetail, auto-refresh useEffect, toggle state)

---

## Admin UI - Batch Details Refresh Semantics

**Purpose:** Clarify timestamp meanings and refresh behavior in Batch Details modal to avoid confusion between data timestamps and UI refresh times.

**Problem (Fixed):**

Previously, the Batch Details modal showed "Last updated" in the header, which was ambiguous:
- Did it mean when the data was last updated on the server (updated_at_max)?
- Or when the UI last fetched the data (local refresh time)?

The header timestamp didn't update while the modal stayed open, requiring users to close and reopen to see refresh updates.

**Solution:**

Two distinct timestamps with clear labels:

### 1. Data Updated At (Server Timestamp)

**Location:** Batch Summary section

**Label:** "Data Updated At"

**Value:** `updated_at_max` from API response (most recent operation update in the batch)

**Format:** Full date/time (e.g., "1/1/2026, 2:23:45 PM")

**Meaning:** When the batch data was last modified on the server

**Updates:** Only changes when backend operations complete/update

### 2. Last Refreshed (UI Timestamp)

**Location:** Modal header (below Batch ID)

**Label:** "Last refreshed"

**Value:** Local browser time of last successful API fetch

**Format:** Time only (e.g., "14:23:45")

**Meaning:** When the UI last successfully fetched fresh data from the server

**Updates:** Changes on every refresh (auto-poll or manual button click)

**Visual Example:**

```
┌────────────────────────────────────────────────────┐
│ Batch Details  [🔵 Live]          [Refresh]  [×]  │
│ Batch ID: 70bce471-... │ Last refreshed: 14:23:45 │ ← UI refresh time
├────────────────────────────────────────────────────┤
│ Batch Summary                                      │
│ Created At: 1/1/2026, 2:20:00 PM                   │
│ Data Updated At: 1/1/2026, 2:23:45 PM              │ ← Server data timestamp
│ Total Operations: 3                                │
└────────────────────────────────────────────────────┘
```

### 3. Manual Refresh Button

**Location:** Modal header (between title and close button)

**Appearance:** Indigo button with refresh icon

**States:**
- Normal: "Refresh" with circular arrow icon
- Loading: "Refreshing..." with spinning icon (disabled)

**Behavior:**
- Click → Immediately calls `GET /sync-batches/{batch_id}`
- Updates both batch data and "Last refreshed" timestamp
- Works for both running and completed batches

### 4. Auto-Refresh Behavior

**Auto-Refresh Toggle:**
- **Location:** Modal header (between Refresh button and Close button)
- **Default:** ON (checked)
- **Appearance:** Checkbox with "Auto refresh" label
- **Behavior:** User can toggle auto-refresh ON/OFF at any time

**Refresh Intervals (when toggle ON):**
- **Running Batches:** Auto-refreshes every 3 seconds
  - Batch status is "running" OR any operations are in "triggered"/"running" status
- **Completed Batches:** Auto-refreshes every 10 seconds
  - All operations completed (success/failed)

**Stable Interval Architecture:**
- Interval set exactly once when modal opens with toggle ON
- Runs continuously until modal closes or toggle turned OFF
- Updates "Last refreshed" timestamp on each automatic refresh
- Interval ID stored in ref for reliable cleanup

**Cleanup:**
- Interval cleared when modal closes
- Interval cleared when toggle turned OFF
- Auto-refresh resets to ON (default) when opening a new batch

### 5. Timestamp Semantics Table

| Timestamp | Location | Label | Source | Format | Updates When |
|-----------|----------|-------|--------|--------|--------------|
| Server | Summary | "Data Updated At" | `updated_at_max` | Full datetime | Backend operation updates |
| Client | Header | "Last refreshed" | `new Date()` | Time only | Every API fetch |

**Related:**

- See [Admin UI - Batch Details & Live Status](#admin-ui---batch-details--live-status) for auto-polling behavior
- Frontend code: `/frontend/app/connections/page.tsx` (refreshBatchDetail, polling useEffect, manual refresh button)

---

## Emergency Contacts

- **Primary On-Call**: [Add contact info]
- **Database Admin**: [Add contact info]
- **Supabase Support**: https://supabase.com/support

---

## Admin UI — Channel Manager (Connections + Sync Logs)

**Purpose:** Backoffice Console UI for managing channel connections, viewing sync logs, and triggering sync operations.

**URL:** `https://admin.fewo.kolibri-visions.de/connections`

**RBAC:** Admin and Manager roles only

---

### Overview

The Connections page provides a comprehensive interface for:
1. **Viewing channel connections** - Table of all configured platform connections
2. **Viewing sync logs** - Per-connection sync operation history with search and filters
3. **Triggering syncs** - Manual sync triggers (availability, pricing, bookings, full)
4. **Monitoring status** - Real-time status badges, error messages, and auto-refresh
5. **Batch tracking** - Grouped view of Full Sync operations with batch_id

---

### Connections Quick Actions

Each connection row in the table provides inline quick actions:

**Test Connection:**
- **Button:** "Test" (inline per row)
- **Action:** POST `/api/v1/channel-connections/{id}/test`
- **Response:** Health status, platform API connectivity check
- **Display:** Shows notification banner with pass/fail result
- **Disable state:** Button disabled during test (shows "Testing...")

**Sync Quick Actions:**
- **Buttons:** A (Availability), P (Pricing), B (Bookings), F (Full)
- **Action:** POST `/api/v1/channel-connections/{id}/sync` with `{"sync_type": "availability"|"pricing"|"bookings"|"full"}`
- **Response:** Returns `batch_id`, `task_ids` array, `status`, `message`
- **Display:** Shows success notification with task count/batch ID
- **Disable state:** Individual button disabled while that sync type is in progress (shows "...")
- **Optimistic update:** Connections list refetched after trigger to update `last_sync_at`

**View Logs:**
- **Button:** "View Logs" (link-style button)
- **Action:** Sets `localStorage.setItem("channelSync:lastConnectionId", connection_id)` and navigates to `/channel-sync`
- **Result:** Channel Sync page loads with connection preselected and logs displayed immediately (no Auto-detect click needed)
- **Note:** Does NOT auto-open sync log details modal (modal opens only on explicit row click)

**Last Sync Age Display:**
- **Column:** "Last Sync"
- **Format:** Relative time (e.g., "3m ago", "2h ago", "1d ago", "never")
- **Helper:** `formatRelativeTime()` converts ISO timestamp to human-friendly age
- **Precision:**
  - < 60s: "Xs ago"
  - < 60m: "Xm ago"
  - < 24h: "Xh ago"
  - < 7d: "Xd ago"
  - < 30d: "Xw ago"
  - < 365d: "Xmo ago"
  - ≥ 365d: "Xy ago"

---

### Sync History (Batches)

The Connections page includes a "Sync History" section that displays recent sync batches for the selected connection.

**Data Source:**
- Endpoint: `GET /api/v1/channel-connections/{connection_id}/sync-batches?limit={N}&offset={M}&status={filter}`
- Returns: List of batches with operations, status counts, and timestamps

**UI Features:**

1. **Batch Table Columns:**
   - **Updated:** Most recent timestamp (updated_at_max or created_at_min)
   - **Status:** Batch status badge (success/failed/running/unknown)
   - **Counts:** Visual summary of operation statuses (✓ success, ✗ failed, ⟳ running, ⋯ triggered)
   - **Operations:** Pills showing operation types with direction indicators (📅 → for availability_update outbound, 💰 → for pricing_update outbound, 🔄 ← for bookings_sync inbound)
   - **Batch ID:** Truncated ID with click-to-copy functionality

2. **Status Filter Dropdown:**
   - **Options:** All Status | Running | Failed | Success
   - **Behavior:** Updates `?status=` query parameter
   - **"All Status"**: Omits status param (shows all batches)
   - **Other values**: Filters batches by batch_status field

3. **Pagination Controls:**
   - **Buttons:** Previous / Next
   - **Default limit:** 50 batches per page
   - **Offset tracking:** Advances by limit value on each page change
   - **Display:** Shows "Showing X - Y" range indicator

4. **Batch Detail Modal:**
   - **Trigger:** Click any batch row in the table
   - **Action:** Fetches `GET /sync-batches/{batch_id}` for detailed operations
   - **Displays:** Batch summary, status breakdown, operations list with direction/task_id/error fields
   - **Auto-refresh:** Optional polling checkbox for running batches
   - **Back navigation:** Returns to connection details or log details (if opened from log)

**Direction Display:**
- **Outbound (→):** availability_update, pricing_update (PMS → Channel Manager)
- **Inbound (←):** bookings_sync (Channel Manager → PMS)
- Derived from operation_type if DB field is NULL (defensive fallback)

**Empty State:**
- Message: "No batches found" when items array is empty
- Occurs when: No sync operations triggered yet, or filter excludes all batches

**Error Handling:**
- Inline error banner for API failures
- Graceful degradation: Does not crash the page
- Retry button available via manual refresh

---

### Batch Details (Full Sync)

When a Full Sync is triggered (sync_type=full), the backend creates a batch containing 3 operations:
1. **availability_update** (outbound)
2. **pricing_update** (outbound)
3. **bookings_sync** (inbound)

All operations in the batch share the same `batch_id`.

**Accessing Batch Details:**
- **From logs table:** Click the blue "Batch" button in any log row that has a `batch_id` (visible for full sync operations)
- **From success panel:** After triggering a full sync, click the green "View Batch" button in the success notification

**Batch Details Modal:**
- **Header:**
  - Title: "Full Sync Batch Details"
  - Copy buttons for Batch ID and Connection ID (📋 with truncated IDs)
  - Refresh button (⟳) to reload batch details
  - Close button (×)

- **Table Columns:**
  - **Operation:** operation_type (e.g., availability_update, pricing_update, bookings_sync)
  - **Status:** Status badge (triggered/running/success/failed) with color coding
  - **Direction:** outbound or inbound
  - **Task ID:** Clickable truncated task_id (click to copy full ID)
  - **Duration:** Calculated from started_at/finished_at or created_at/updated_at
  - **Updated At:** Localized timestamp
  - **Error:** "View Error" button (if error exists) → opens detail drawer and closes batch modal

- **States:**
  - **Loading:** Spinner with "Loading batch details..." message
  - **Error:** Red error banner with API error message
  - **Empty:** "No operations found for this batch." (shouldn't happen for valid full sync batches)
  - **Success:** Table showing all 3 operations

**UX Rules:**
- Clicking "View Error" button transitions from batch modal to detail drawer (closes modal, opens drawer)
- Closing batch modal clears any active toasts (`setToast(null)`)
- Toast lifecycle follows standard rules (6s auto-dismiss, cleared on navigation)

**Backend Endpoints:**

**1. List Recent Batches (Discovery):**
```bash
GET /api/v1/channel-connections/{connection_id}/sync-batches?limit=5&offset=0
```

**Example curl:**
```bash
curl -L -X GET "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/{CID}/sync-batches?limit=5&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

**Response:** Array of batch summaries with `batch_id`, `batch_status`, `status_counts`, `operations` (detailed)

**2. Get Batch Details (Detailed Operations):**
```bash
GET /api/v1/channel-connections/{connection_id}/sync-batches/{batch_id}
```

**Example curl:**
```bash
curl -L -X GET "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/{CID}/sync-batches/{BATCH_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

**Response Fields (per operation):**
- `operation_type`: availability_update | pricing_update | bookings_sync
- `status`: triggered | running | success | failed
- `direction`: outbound | inbound (derived from operation_type if NULL: availability_update/pricing_update → outbound, bookings_sync → inbound)
- `task_id`: Celery task UUID (nullable)
- `error`: Error message string (nullable, present only if status=failed)
- `duration_ms`: Duration in milliseconds (nullable, null if started_at/finished_at not available)
- `updated_at`: Timestamp of last update
- `log_id`: Sync log UUID (for UI "View Error" drawer)

**Note:** Both list (`GET /sync-batches`) and details (`GET /sync-batches/{batch_id}`) endpoints return operations with all fields above. The list endpoint aggregates all logs per batch, while the details endpoint shows a single batch.

**Duration Computation Fallback:**

The `duration_ms` field is computed using the following fallback logic (implemented in SQL):
1. **Preferred:** If `started_at` and `finished_at` columns exist and are populated, use those timestamps
2. **Fallback:** If `started_at`/`finished_at` are not available but `created_at` and `updated_at` exist and `updated_at >= created_at`, compute duration as: `EXTRACT(EPOCH FROM (updated_at - created_at)) * 1000` milliseconds
3. **Null:** If neither timestamps are available or `updated_at < created_at`, `duration_ms` is `null`

**UI Display:**
- When `duration_ms` is present: Display as human-friendly format (e.g., "2.35s" for 2350ms)
- When `duration_ms` is `null`: Display as "—" (em dash) to indicate no duration available
- **Hover Tooltip:** When duration is available, hovering over the duration shows raw milliseconds (e.g., "453 ms")
- **Format:** Seconds with 2 decimal places (e.g., "0.45s"), tooltip shows integer milliseconds

**Response Example:**
```json
{
  "batch_id": "64c93985-f61b-4b95-856c-dae0baf35efc",
  "connection_id": "abc-123-def-456",
  "batch_status": "success",
  "status_counts": {
    "triggered": 0,
    "running": 0,
    "success": 3,
    "failed": 0,
    "other": 0
  },
  "created_at_min": "2026-01-03T10:00:00Z",
  "updated_at_max": "2026-01-03T10:05:00Z",
  "operations": [
    {
      "operation_type": "availability_update",
      "status": "success",
      "direction": "outbound",
      "task_id": "550e8400-e29b-41d4-a716-446655440001",
      "error": null,
      "duration_ms": null,
      "updated_at": "2026-01-03T10:03:00Z",
      "log_id": "log-uuid-001"
    },
    {
      "operation_type": "pricing_update",
      "status": "success",
      "direction": "outbound",
      "task_id": "550e8400-e29b-41d4-a716-446655440002",
      "error": null,
      "duration_ms": null,
      "updated_at": "2026-01-03T10:04:00Z",
      "log_id": "log-uuid-002"
    },
    {
      "operation_type": "bookings_sync",
      "status": "success",
      "direction": "inbound",
      "task_id": "550e8400-e29b-41d4-a716-446655440003",
      "error": null,
      "duration_ms": null,
      "updated_at": "2026-01-03T10:05:00Z",
      "log_id": "log-uuid-003"
    }
  ]
}
```

**Alternative Endpoint (Logs-based):**
```bash
GET /api/v1/channel-connections/{connection_id}/sync-logs?batch_id={batch_id}&limit=100
```

**Response:** Standard sync-logs response with `logs` array filtered to the specified batch_id

**Use Case:**
Operators can track the progress of all 3 operations in a Full Sync batch from a single view, quickly identifying which operation succeeded/failed and drilling into errors via the detail drawer. The `/sync-batches/{batch_id}` endpoint provides detailed per-operation fields (direction, task_id, error, duration_ms) in a single API call.

---

### API Endpoints Used

The Admin UI consumes the following Channel Manager API endpoints:

#### 1. List Connections
```
GET /api/v1/channel-connections/?limit=50&offset=0
```

**Response Shape:** Array
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "property_id": "uuid",
    "platform_type": "airbnb|booking_com|expedia|fewo_direkt|google",
    "platform_listing_id": "string",
    "status": "active|inactive|error",
    "platform_metadata": {},
    "last_sync_at": "2025-01-03T12:00:00Z" | null,
    "created_at": "2025-01-03T10:00:00Z",
    "updated_at": "2025-01-03T12:00:00Z"
  }
]
```

**curl Example:**
```bash
curl -L -X GET "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/?limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

**Notes:**
- Returns **array directly** (not wrapped in object)
- UI uses `normalizeConnections()` helper to handle both array and object responses
- Trailing slash + query params required to avoid 307 redirects

#### 2. Get Sync Logs
```
GET /api/v1/channel-connections/{connection_id}/sync-logs?limit=50&offset=0
```

**Response Shape:** Object with `logs` array
```json
{
  "connection_id": "uuid",
  "logs": [
    {
      "id": "uuid",
      "connection_id": "uuid",
      "operation_type": "availability_update|pricing_update|bookings_sync",
      "direction": "outbound|inbound",
      "status": "triggered|running|success|failed",
      "details": ["<json-string>", "<json-string>"] | {},
      "error": null | "error message",
      "task_id": "celery-task-uuid",
      "batch_id": "batch-uuid" | null,
      "created_at": "2025-01-03T12:00:00Z",
      "updated_at": "2025-01-03T12:05:00Z"
    }
  ],
  "limit": 50,
  "offset": 0,
  "batch_id": null
}
```

**curl Example:**
```bash
CID="your-connection-uuid"
curl -L -X GET "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync-logs?limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

**Notes:**
- Returns **object** with `logs` array (not array directly)
- UI uses `normalizeLogs()` helper to extract array from `data.logs || data.items || data.data`
- `details` field can be:
  - Array of JSON strings: `["{\\"key\\": \\"value\\"}"]`
  - Already parsed object: `{"key": "value"}`
  - UI uses `parseLogDetails()` to safely parse JSON strings

#### 3. Trigger Sync
```
POST /api/v1/channel-connections/{connection_id}/sync
```

**Request Body:**
```json
{
  "sync_type": "availability|pricing|bookings|full"
}
```

**Response Shape:**
```json
{
  "status": "triggered",
  "message": "Sync triggered successfully",
  "task_ids": ["task-uuid-1", "task-uuid-2", "task-uuid-3"],
  "batch_id": "batch-uuid"
}
```

**curl Example:**
```bash
CID="your-connection-uuid"
curl -L -X POST "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "availability"}'
```

**Notes:**
- Full sync returns `batch_id` + `task_ids` array (3 operations)
- Single sync (availability/pricing) may return single `task_id` or array
- UI displays batch_id with copy button for easy tracking

---

### UI Features

#### Connections Table
- **Columns:** Platform, Property ID, Status, Last Sync, Updated At
- **Search:** Client-side search by ID, platform, or status
- **Actions:**
  - **View Logs** - Opens detail modal with sync logs for that connection
  - **Trigger Sync** - Dropdown selector (availability, pricing, bookings, full)

#### Sync Logs Panel (in Connection Detail Modal)
- **Search:** Free-text search across all log fields:
  - IDs: id, task_id, batch_id, connection_id
  - Fields: operation_type, status, direction, error
  - Details: JSON-stringified details
  - Timestamps: created_at, updated_at
- **Filters:**
  - Status: All / Triggered / Running / Success / Failed
  - Sync Type: All / Full / Availability / Pricing / Bookings
- **Sorting:** Newest first (created_at DESC)
- **Batch Grouping:** Full Sync operations grouped by `batch_id` in collapsible indigo cards
- **Auto-Refresh:**
  - Logs: 10 seconds (when checkbox enabled)
  - Batch logs: 3 seconds (when batch is active)
- **Detail Drawer:** Click any log row to view:
  - Parsed details JSON (pretty-printed)
  - Error messages (if failed)
  - Full log record (expandable)

#### Polling After Trigger
When user triggers a sync:
1. API returns `batch_id` and `task_ids`
2. UI displays notification banner with batch_id (copy button)
3. UI starts polling sync logs endpoint every 3 seconds for up to 60 seconds
4. Matches logs by:
   - `batch_id` (for Full Sync)
   - Any `task_id` in returned array
5. Highlights matching rows in logs table
6. Stops polling when all matching logs reach terminal status (`success` or `failed`) OR timeout

---

### Manual Verification with curl

#### Step 1: List all connections
```bash
export TOKEN="your-jwt-token"
export API="https://api.fewo.kolibri-visions.de"

curl -L -X GET "$API/api/v1/channel-connections/?limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" | jq
```

**Expected:** Array of connection objects

#### Step 2: Get sync logs for a connection
```bash
CID="connection-uuid-from-step-1"

curl -L -X GET "$API/api/v1/channel-connections/$CID/sync-logs?limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" | jq
```

**Expected:** Object with `logs` array

#### Step 3: Trigger a sync
```bash
curl -L -X POST "$API/api/v1/channel-connections/$CID/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type": "availability"}' | jq
```

**Expected:** Object with `status`, `task_ids`, `batch_id`

#### Step 4: Poll logs to verify sync created log entries
```bash
# Wait 2-3 seconds, then fetch logs again
sleep 3
curl -L -X GET "$API/api/v1/channel-connections/$CID/sync-logs?limit=50&offset=0" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" | jq '.logs[] | select(.batch_id == "batch-uuid-from-step-3")'
```

**Expected:** Log entries with matching `batch_id` or `task_id`

---

### Response Shape Handling (Resilience)

The UI uses normalization helpers to handle API response variations:

```typescript
// Handle connections endpoint (array response)
function normalizeConnections(data: any): any[] {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    return data.connections || data.data || data.items || [];
  }
  return [];
}

// Handle sync logs endpoint (object with logs array)
function normalizeLogs(data: any): any[] {
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    return data.logs || data.items || data.data || [];
  }
  return [];
}

// Parse details field (can be JSON string, array of strings, or object)
function parseLogDetails(details: any): any {
  if (!details) return null;
  if (typeof details === 'object' && !Array.isArray(details)) return details;

  // Array of JSON strings
  if (Array.isArray(details)) {
    return details.map(item =>
      typeof item === 'string' ? JSON.parse(item) : item
    );
  }

  // Single JSON string
  if (typeof details === 'string') {
    try { return JSON.parse(details); }
    catch (e) { return details; }
  }

  return details;
}
```

**Why this matters:**
- Connections endpoint returns **array directly**
- Sync logs endpoint returns **object with `logs` array**
- Details field can be **JSON string, array of strings, or already parsed**
- Normalization prevents crashes when API shape changes

---

### Troubleshooting

#### No connections shown
**Check:**
1. User has admin/manager role (403 if insufficient permissions)
2. Database migrations applied (`channel_connections` table exists)
3. Browser console for API errors
4. curl command works (test token validity)

#### Sync logs empty after trigger
**Check:**
1. Celery worker is running (`docker ps | grep celery`)
2. Redis is accessible (`redis-cli ping`)
3. Check sync log status in DB: `SELECT * FROM channel_sync_logs WHERE batch_id = 'your-batch-id'`
4. Worker logs for errors: `docker logs pms-celery-worker`

#### Polling doesn't find new logs
**Check:**
1. `batch_id` or `task_id` matches between trigger response and log entries
2. Auto-refresh checkbox is enabled
3. Logs endpoint returns matching entries (test with curl)
4. Browser network tab shows polling requests every 3s

#### Error: "Failed to fetch connections (HTTP 503)"
**Fix:** Database schema out of date, run migrations:
```bash
cd supabase/migrations
supabase db push
```

#### Frontend deploy - Admin UI doesn't update / /guests 404 after commit
**Symptoms:**
- New admin UI features don't appear after git push
- Routes like `/guests` return 404
- Coolify shows "Build failed" or old image still running

**Common Causes:**
1. Frontend build failed due to ESLint not installed (requires `eslint` package or `ignoreDuringBuilds: true`)
2. TypeScript compilation errors (type mismatches, missing properties)
3. Build process exited before completion (OOM, timeout)

**Fix Checklist:**
1. Check Coolify build logs for errors (ESLint, TypeScript, out-of-memory)
2. Add `eslint: { ignoreDuringBuilds: true }` to `next.config.js` if ESLint not installed
3. Fix TypeScript errors (especially Supabase query response types - array vs object handling)
4. Verify routes exist in correct locations (`app/guests/page.tsx`, `app/guests/layout.tsx`)
5. Trigger manual redeploy in Coolify after fixes are pushed
6. Verify new routes are accessible after successful build

**Example Fix (TypeScript array/object handling):**
```typescript
// Bad: assumes object
const agencyName = teamMember?.agency?.name || 'PMS';

// Good: handles both array and object
const agency = (teamMember as any)?.agency;
const agencyName = (Array.isArray(agency) ? agency?.[0]?.name : agency?.name) ?? 'PMS';
```

**Specific Issue: Nullable Props to AdminShell (2026-01-05)**

**Symptom:**
```
Type error: Type 'string | null' is not assignable to type 'string'.
  ./app/settings/branding/layout.tsx:121:17
```

**Root Cause:**
- AdminShell expects `userRole: string` (non-nullable required)
- Layout files pass nullable values: `resolvedRole: string | null`, `session.user.email: string | null`

**Fix:**
Normalize to safe strings before passing to AdminShell:
```typescript
// Normalize nullable auth/session values
const safeUserName = (userEmail ?? "").trim() || "—";
const safeUserRole = (resolvedRole ?? "").trim() || "staff";

<AdminShell userRole={safeUserRole} userName={safeUserName} agencyName={agencyName}>
```

**Diagnostic Commands:**
```bash
# Check Coolify build logs for TypeScript errors
# Look for "Type 'string | null' is not assignable to type 'string'"

# Verify docker image tag after deploy
docker ps | grep pms-admin

# If old image still running, check build succeeded
docker logs <container-id> 2>&1 | grep -i error
```

#### Guests Page Shows HTTP 404 / List Not Loading (2026-01-05)

**Symptoms:**
- Navigate to `/guests` → page renders but shows "Fehler beim Laden — HTTP 404"
- No guest list displayed
- Browser console shows: `GET /api/v1/guests?limit=20&offset=0 404 (Not Found)`
- Search and pagination don't work (list never loads)

**Root Causes:**
1. **Wrong API base URL** - Frontend using relative URL `/api/v1/guests` instead of absolute backend API URL
   - Resolves to `https://admin.<domain>/api/v1/guests` instead of `https://api.<domain>/api/v1/guests`
   - Cause: fetch() call without proper base URL configuration
2. **Missing API route** - Guests router not properly mounted (less common after Phase 19)
3. **CORS/credentials** - API rejects requests without proper credentials or origin headers

**Quick Diagnostic Checks:**

1. **Verify API endpoint exists:**
```bash
# Check OpenAPI schema lists guests routes
curl -s https://api.<domain>/openapi.json | grep -i guests

# Test API directly
curl -H "Cookie: sb-access-token=..." \
     https://api.<domain>/api/v1/guests?limit=5
# Should return 200 with {items: [...], total: N}
```

2. **Check frontend API base URL:**
```bash
# In browser console on /guests page:
console.log(process.env.NEXT_PUBLIC_API_BASE)
# Should show: https://api.<domain>

# Check if getApiBase() is being used:
grep -n "getApiBase\|apiClient" frontend/app/guests/page.tsx
```

3. **Check browser network tab:**
   - Failed request URL should be `https://api.<domain>/api/v1/guests` (correct)
   - If showing `https://admin.<domain>/api/v1/guests` → frontend base URL issue

**Fix Summary (2026-01-05):**
- Exported `getApiBase()` from `frontend/app/lib/api-client.ts`
- Updated `frontend/app/guests/page.tsx` to use `getApiBase()` for constructing full API URL
- Before: `fetch('/api/v1/guests?...')`
- After: `fetch('${getApiBase()}/api/v1/guests?...')`

**Verification After Fix:**
```bash
# 1. Build should pass
cd frontend && npm run build

# 2. Deploy and check /guests loads
curl -H "Cookie: ..." https://admin.<domain>/guests
# Should render page without 404 errors

# 3. Run smoke test
export API_BASE_URL="https://api.<domain>"
export JWT_TOKEN="..."
bash backend/scripts/pms_guests_smoke.sh
# Should pass: list, search, pagination tests
```

---

#### Admin UI API Base URL Resolution (2026-01-05)

**Overview:**
The frontend admin UI needs to communicate with the backend API, which is hosted on a different subdomain. The API client uses a smart resolution strategy to determine the correct API base URL.

**Resolution Strategy (in order):**

1. **NEXT_PUBLIC_API_BASE environment variable (preferred)**
   - Explicitly set in `.env` or deployment config
   - Example: `NEXT_PUBLIC_API_BASE=https://api.fewo.kolibri-visions.de`
   - This is the recommended approach for production deployments

2. **Automatic hostname derivation (fallback)**
   - If `NEXT_PUBLIC_API_BASE` is not set, derives from current hostname
   - Pattern: `admin.*` → `api.*`
   - Examples:
     - `admin.fewo.kolibri-visions.de` → `https://api.fewo.kolibri-visions.de`
     - `admin.localhost:3000` → `http://api.localhost:3000`
   - Preserves protocol and port
   - Logs to console: `[api-client] Derived API base from hostname: <url>`

3. **Mixed content protection**
   - If frontend is HTTPS but env var specifies HTTP, automatically upgrades to HTTPS
   - Prevents browser mixed-content blocking
   - Logs warning: `[api-client] Upgrading HTTP API base to HTTPS...`

**Common Symptom: UI Shows 404 While API is Healthy**

**Diagnosis Steps:**

1. **Check browser network tab:**
   ```
   Expected: Request to https://api.<domain>/api/v1/...
   Wrong:    Request to https://admin.<domain>/api/v1/...
   ```
   - If seeing `admin.*` in API request URLs → API base URL resolution failed

2. **Check browser console:**
   ```javascript
   // Should show API base URL being used
   // Look for: [api-client] Derived API base from hostname: ...
   ```

3. **Verify environment variable:**
   ```bash
   # In Coolify or deployment config
   echo $NEXT_PUBLIC_API_BASE
   # Should show: https://api.<domain>

   # If empty, auto-derivation should work if hostname pattern is admin.*
   ```

4. **Test API endpoint directly:**
   ```bash
   # Verify API is actually reachable
   curl -H "Cookie: sb-access-token=..." \
        https://api.<domain>/api/v1/guests?limit=5
   # Should return 200 with data
   ```

**Fix Actions:**

1. **Set NEXT_PUBLIC_API_BASE explicitly (recommended):**
   ```bash
   # In Coolify environment variables or .env
   NEXT_PUBLIC_API_BASE=https://api.fewo.kolibri-visions.de
   ```
   - Rebuild and redeploy frontend
   - Verify in browser console that env var is set

2. **Verify hostname pattern (if using auto-derivation):**
   - Frontend must be hosted on `admin.*` subdomain
   - If using different pattern (e.g., `app.*`), auto-derivation won't work
   - Solution: Set `NEXT_PUBLIC_API_BASE` explicitly

3. **Check for typos in code:**
   ```bash
   # Verify all pages use getApiBase() or apiClient
   grep -r "fetch.*api/v1" frontend/app/
   # Should NOT find hardcoded relative URLs like fetch("/api/v1/...")

   # All should import and use:
   import { getApiBase } from "../lib/api-client";
   // OR
   import { apiClient } from "../lib/api-client";
   ```

**Code Reference:**
- Implementation: `frontend/app/lib/api-client.ts` → `getApiBase()` function
- Used by: All admin pages (guests, connections, settings, etc.)

---

#### Unified Admin UI Baseline (2026-01-05)

**Overview:**
All admin pages now use the unified AdminShell component for consistent layout, navigation, and branding.

**Pages using Admin UI baseline:**
- /guests - Guest CRM (list, detail, timeline)
- /settings/branding - Branding settings
- /connections - Channel connections management
- /channel-sync - Sync monitoring console
- /ops/status - System health checks
- /ops/runbook - Operations documentation

**Layout Components:**
- `AdminShell` (frontend/app/components/AdminShell.tsx) - Unified shell with sidebar navigation
- Individual `layout.tsx` files per route handle auth, role checks, and wrap children in AdminShell

**Navigation Structure:**
- Übersicht: Dashboard
- Betrieb: Objekte, Buchungen, Verfügbarkeit, **Systemstatus** (admin-only), **Runbook** (admin-only)
- Channel Manager: Verbindungen, Sync-Protokoll
- CRM: Gäste
- Einstellungen: Branding, Rollen & Rechte, Plan & Abrechnung

**Finding Ops Pages:**
- **Systemstatus** (/ops/status): Real-time system health monitoring - admin role required
- **Runbook** (/ops/runbook): Operations troubleshooting guide - admin role required
- Both pages accessible via sidebar navigation under "Betrieb" section
- Requires NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1 environment variable

**Design Consistency:**
- All pages use German language for UI text
- Platform names replaced with neutral labels (Plattform A/B/C)
- Consistent typography, spacing (4/8/12/16/24 px rhythm)
- Indigo primary palette with gray neutrals
- No third-party brand names in user-facing UI

**Finding Admin Pages:**
All admin routes now show sidebar navigation. Access via:
- Direct URL: `/guests`, `/connections`, `/channel-sync`, `/ops/status`, `/ops/runbook`
- Sidebar navigation from any admin page
- Login redirect preserves destination path

**UI Troubleshooting Quick Checks:**

If UI shows 404 errors or empty data when API is healthy:

1. **Check API Base URL Resolution:**
   ```javascript
   // In browser console:
   console.log(process.env.NEXT_PUBLIC_API_BASE)
   // Should show: https://api.<domain>
   ```
   - If undefined, check environment variables or hostname derivation (admin.* → api.*)
   - See "Admin UI API Base URL Resolution" section above for details

2. **Check Browser Network Tab:**
   ```
   Expected: Request to https://api.<domain>/api/v1/...
   Wrong:    Request to https://admin.<domain>/api/v1/... (404)
   ```
   - If seeing admin.* in API URLs → API base URL misconfigured

3. **Check JWT Session:**
   ```javascript
   // In browser console:
   document.cookie.split(';').find(c => c.trim().startsWith('sb-access-token'))
   // Should exist and not be expired
   ```
   - If missing → session expired, logout and login again
   - Check browser dev tools → Application → Cookies → sb-access-token

4. **Check Admin Role (for /ops pages):**
   - /ops/status and /ops/runbook require admin role
   - Non-admin users see "Access Denied" message (not a bug)
   - Verify user has role='admin' in team_members table

5. **Common UI Issues:**
   - **Sidebar doesn't show Ops pages** → User role is not admin
   - **Page shows blank/empty** → JWT expired, refresh or re-login
   - **404 on all API calls** → NEXT_PUBLIC_API_BASE not set or wrong
   - **Mixed content errors** → Frontend HTTPS but API configured as HTTP

---

## Admin UI Sidebar Architecture (Single Source of Truth)

**Purpose:** Ensure consistent navigation across ALL authenticated routes in the frontend admin UI.

**Problem Solved:** Previously, some pages used cookie-based authentication while others used Supabase server-side auth, leading to inconsistent user data (role, agency name) and navigation visibility across routes.

**Architecture Overview:**

1. **Navigation Configuration (Single Source):**
   - File: `frontend/app/components/AdminShell.tsx`
   - Constant: `NAV_GROUPS` (lines 34-73)
   - All navigation groups and items are defined here
   - Supports role-based visibility via `roles: ["admin"]` property
   - Supports plan-gating via `planLocked: true` property

2. **Server-Side Authentication (Shared Utility):**
   - File: `frontend/app/lib/server-auth.ts`
   - Function: `getAuthenticatedUser(currentPath)`
   - ALL authenticated routes use this utility for consistent:
     - Supabase session validation with redirect
     - Database role lookup from `team_members` table
     - Agency name resolution from `agencies` table
     - Normalized user data for AdminShell props

3. **Layout Pattern (Standardized):**
   - Every authenticated route has a `layout.tsx` that:
     - Calls `getAuthenticatedUser('/route-path')`
     - Wraps children in `<AdminShell>` with user data
     - Uses `dynamic = 'force-dynamic'` export config
   - Examples:
     - `frontend/app/guests/layout.tsx`
     - `frontend/app/properties/layout.tsx`
     - `frontend/app/connections/layout.tsx`
     - `frontend/app/settings/*/layout.tsx`

**Navigation Groups:**

Current sidebar groups (as of implementation):
1. **Übersicht** (Overview): Dashboard
2. **Betrieb** (Operations): Properties, Bookings, Availability, Systemstatus*, Runbook*
3. **Channel Manager**: Connections, Sync-Protokoll
4. **CRM**: Guests
5. **Einstellungen** (Settings): Branding, Roles*, Billing (plan-locked)

*Items marked with asterisk are admin-only (visible when `userRole === "admin"`)

**How to Add a New Sidebar Item:**

1. **Add Route Files:**
   ```bash
   mkdir -p frontend/app/my-feature
   touch frontend/app/my-feature/layout.tsx
   touch frontend/app/my-feature/page.tsx
   ```

2. **Create Layout (Use Shared Auth):**
   ```typescript
   // frontend/app/my-feature/layout.tsx
   import AdminShell from "../components/AdminShell";
   import { getAuthenticatedUser } from "../lib/server-auth";

   export const dynamic = 'force-dynamic';
   export const revalidate = 0;
   export const fetchCache = 'force-no-store';

   export default async function MyFeatureLayout({ children }) {
     const userData = await getAuthenticatedUser('/my-feature');
     return (
       <AdminShell
         userRole={userData.role}
         userName={userData.name}
         agencyName={userData.agencyName}
       >
         {children}
       </AdminShell>
     );
   }
   ```

3. **Add Nav Item to AdminShell:**
   ```typescript
   // frontend/app/components/AdminShell.tsx
   // Find the appropriate NAV_GROUP and add:
   {
     label: "Betrieb",
     items: [
       // ... existing items ...
       { label: "My Feature", href: "/my-feature", icon: "🎯" },
       // Optional: restrict to admins
       { label: "Admin Feature", href: "/admin-feature", icon: "🔒", roles: ["admin"] },
     ],
   }
   ```

4. **Verify Build:**
   ```bash
   cd frontend && npm run build
   # Should compile successfully
   ```

**Troubleshooting:**

1. **Sidebar item not showing:**
   - Check `NAV_GROUPS` in AdminShell.tsx includes the item
   - Check `roles` property - if set to `["admin"]`, only admins see it
   - Verify `userRole` is correctly passed from layout to AdminShell
   - Check browser console for any errors

2. **Different sidebar on different pages:**
   - This should NOT happen with unified architecture
   - Verify all layouts use `getAuthenticatedUser()` utility
   - Check that no layouts are reading cookies directly
   - Ensure all layouts import AdminShell from same file

3. **User role not resolving:**
   - Check Supabase session is valid (not expired)
   - Verify `team_members` table has active row for user
   - Check `profiles.last_active_agency_id` points to correct agency
   - Review `server-auth.ts` role resolution logic

**Architecture Benefits:**

- ✅ **Consistent UX:** Same navigation visible on all pages
- ✅ **Single Source of Truth:** Nav config in one place (AdminShell.tsx)
- ✅ **Secure:** Server-side Supabase auth with database role lookup
- ✅ **Maintainable:** Add new pages by following standard pattern
- ✅ **Role-Based:** Supports admin-only items via `roles` property
- ✅ **Plan-Gating:** Supports locked features via `planLocked` property

**Related Files:**
- `frontend/app/components/AdminShell.tsx` - Navigation config + UI component
- `frontend/app/lib/server-auth.ts` - Shared authentication utility
- `frontend/app/*/layout.tsx` - Individual route layouts (all use shared auth)

### Admin UI API Calls - Prevent Relative URL Bugs

**Symptom:** Admin UI page shows HTTP 404 in browser console when calling API:
```
GET https://admin.fewo.kolibri-visions.de/api/v1/guests/<id> → 404
```

**Root Cause:**
- Page uses relative API URL: `fetch("/api/v1/guests/...")`
- Browser resolves this against current domain (admin.*) instead of API backend (api.*)
- Backend API lives at `https://api.fewo.kolibri-visions.de`

**Fix Pattern (Mandatory):**

ALL client-side API calls MUST use the centralized API helper:

```typescript
// CORRECT - Use getApiBase() for fetch calls
import { getApiBase } from "../../lib/api-client";

const apiBase = getApiBase();
const response = await fetch(`${apiBase}/api/v1/guests/${id}`, {
  credentials: "include",
});

// OR use apiClient wrapper (preferred when token-based auth):
import { apiClient } from "../../lib/api-client";

const data = await apiClient.get(`/api/v1/guests/${id}`, accessToken);
```

```typescript
// WRONG - Never use relative URLs
const response = await fetch("/api/v1/guests/${id}"); // ❌ BUG!
```

**How getApiBase() Works:**

Resolution order (see `frontend/app/lib/api-client.ts`):
1. **NEXT_PUBLIC_API_BASE** env var (preferred, explicit)
2. **Hostname derivation:** `admin.fewo.* → api.fewo.*`
3. **HTTPS upgrade:** If frontend is HTTPS, upgrades HTTP API base to HTTPS (prevent mixed content)

**Quick Debugging Checklist:**

When investigating API 404 errors in Admin UI:

1. **Check browser DevTools Network tab:**
   - Look at the request URL hostname
   - Should be `api.fewo.kolibri-visions.de`, NOT `admin.fewo.kolibri-visions.de`

2. **Check source code:**
   ```bash
   cd frontend
   # Find all relative API fetch calls (should return EMPTY)
   rg -n --fixed-strings 'fetch("/api/' app/
   rg -n --fixed-strings "fetch('/api/" app/
   ```

3. **Verify env var (if set):**
   ```bash
   # In Coolify deployment settings:
   NEXT_PUBLIC_API_BASE=https://api.fewo.kolibri-visions.de
   ```

4. **Check runtime API base:**
   - Open browser console on admin page
   - Run: `fetch('/_next/static/...')` (check if HTTPS)
   - Derivation should work: admin.* → api.*

**Prevention:**

- Code review: Reject any `fetch("/api/v1/...")` patterns
- Use ESLint rule (future): Warn on relative `/api/` URLs in fetch calls
- Always import and use `getApiBase()` or `apiClient` from `lib/api-client.ts`

**Related Files:**
- `frontend/app/lib/api-client.ts` - API base URL resolution + apiClient wrapper
- `frontend/app/guests/[id]/page.tsx` - Example: Guest detail using `apiClient.get()` with auth
- `frontend/app/guests/page.tsx` - Example: Guest list using `apiClient.get()` with auth

#### 403 Forbidden - Missing Authorization Header

**Symptom:** Admin UI page loads but API calls return HTTP 403:
```
GET https://api.fewo.kolibri-visions.de/api/v1/guests/<id> → 403
Response: {"detail": "Not authenticated"}
```

**Root Causes:**

1. **Missing Authorization header** in client-side fetch call
2. **Missing access token** from Supabase session
3. **Using raw fetch()** instead of authenticated API client

**Fix Pattern (Mandatory):**

ALL authenticated API calls MUST:
1. Use `useAuth()` hook to get the access token
2. Pass token to `apiClient` methods OR add Authorization header manually
3. Handle 401/403 errors with actionable user message

```typescript
// CORRECT - Use apiClient with auth token
import { useAuth } from "../../lib/auth-context";
import { apiClient, ApiError } from "../../lib/api-client";

export default function MyPage() {
  const { accessToken } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      if (!accessToken) {
        setError("Session expired. Please log in again.");
        return;
      }

      try {
        const data = await apiClient.get(`/api/v1/guests/${id}`, accessToken);
        // Use data...
      } catch (err) {
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          setError("Session expired or not authenticated. Please log in again.");
        }
      }
    };
    fetchData();
  }, [accessToken]);
}
```

```typescript
// WRONG - Raw fetch without auth
const response = await fetch(`${apiBase}/api/v1/guests/${id}`); // ❌ NO AUTH!
```

**How apiClient Handles Auth:**

See `frontend/app/lib/api-client.ts`:
```typescript
export async function apiRequest(endpoint, options = {}) {
  const { token, ...fetchOptions } = options;
  const headers = new Headers();

  // Automatically adds Authorization header if token provided
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
  return fetch(url, { ...fetchOptions, headers });
}
```

**Debug Checklist for 403 Errors:**

1. **Check browser DevTools Network tab:**
   - Request Headers should include: `Authorization: Bearer eyJ...`
   - If missing → auth token not passed to apiClient

2. **Check React DevTools / Console:**
   ```javascript
   // In browser console on admin page:
   console.log("Access token:", localStorage.getItem('supabase.auth.token'))
   ```
   - If null/empty → Supabase session expired, user needs to login

3. **Check source code:**
   ```bash
   cd frontend/app
   # Find pages using raw fetch without auth (should return EMPTY)
   rg -n 'fetch.*api/v1' --type tsx | grep -v apiClient
   ```

4. **Verify useAuth() is called:**
   - Page must import: `import { useAuth } from "../../lib/auth-context";`
   - Component must call: `const { accessToken } = useAuth();`
   - Effect must check: `if (!accessToken) return;`

**Common Mistakes:**

- ❌ Using `credentials: "include"` without Authorization header (backend expects JWT, not cookies)
- ❌ Forgetting to pass `accessToken` to `apiClient.get()`
- ❌ Not handling 401/403 errors with user-friendly message
- ❌ Using raw `fetch()` instead of `apiClient` wrapper

**Prevention:**

- Code review: ALL API calls must use `apiClient` with `accessToken`
- Error boundaries: Show "Session expired" message on 401/403
- Consistent pattern: Follow guests list page example (frontend/app/guests/page.tsx)

#### Next.js 404 (Missing Route) vs API 404

**Symptom:** Clicking a link in Admin UI opens a page that shows Next.js 404 error:
```
404 | This page could not be found
```

**Browser network tab shows:**
```
GET /bookings/<uuid>?_rsc=... → 404
```

**Root Cause:**

This is a **Next.js route 404**, NOT an API 404. The difference:
- **Next route missing** → Browser requests `/bookings/<id>` from Next.js app, but no `app/bookings/[id]/page.tsx` exists
- **API 404** → Route exists, but backend API returns 404 for resource

**How to Distinguish:**

1. **Check URL in browser address bar:**
   - If URL is `https://admin.fewo.../bookings/<id>` → Next route issue
   - Network tab shows `?_rsc=...` parameter → Next.js RSC (React Server Component) request

2. **Check browser DevTools Network tab:**
   - Request URL ends with `?_rsc=...` → Next.js routing, NOT backend API
   - No `Authorization` header in request → Not an API call
   - Response is HTML/text, not JSON → Next.js 404 page

3. **Backend API 404 would show:**
   - Request URL: `https://api.fewo.../api/v1/bookings/<id>` (API domain)
   - Authorization header present
   - JSON response: `{"detail": "Not found"}`

**Fix Pattern:**

Create the missing Next.js route:

1. **Create route directory:**
   ```bash
   mkdir -p frontend/app/bookings/[id]
   ```

2. **Create page component:**
   ```typescript
   // frontend/app/bookings/[id]/page.tsx
   "use client";

   import { useState, useEffect } from "react";
   import { useParams } from "next/navigation";
   import { useAuth } from "../../lib/auth-context";
   import { apiClient, ApiError } from "../../lib/api-client";

   export default function BookingDetailPage() {
     const params = useParams();
     const bookingId = params?.id as string;
     const { accessToken } = useAuth();

     useEffect(() => {
       const fetchData = async () => {
         if (!accessToken) return;
         const data = await apiClient.get(
           `/api/v1/bookings/${bookingId}`,
           accessToken
         );
         // Render data...
       };
       fetchData();
     }, [bookingId, accessToken]);

     return <div>Booking Details...</div>;
   }
   ```

3. **IMPORTANT - Use correct import paths:**
   - From `app/bookings/[id]/page.tsx`: `import { ... } from "../../lib/..."`
   - NOT `../../../lib/...` (will cause webpack module not found error)

4. **Use apiClient with auth** (avoid relative URLs):
   - ✅ `apiClient.get(\`/api/v1/bookings/${id}\`, accessToken)`
   - ❌ `fetch(\`/api/v1/bookings/${id}\`)` (no auth)

**Verification:**

```bash
# Build must succeed
cd frontend && npm run build
# ✓ Compiled successfully

# Check route exists
ls frontend/app/bookings/[id]/page.tsx
```

**Common Mistakes:**

- ❌ Thinking it's an API issue when it's a Next route issue
- ❌ Wrong import paths (too many `../`)
- ❌ Forgetting to add auth to API calls in new route
- ❌ Not creating a layout if auth is needed

**Related Files:**
- `frontend/app/bookings/[id]/page.tsx` - Booking detail route
- `frontend/app/guests/[id]/page.tsx` - Similar pattern (guest detail)

#### Guest Booking History Count Badge Shows 0

**Symptom:** Admin UI → Guests → Guest Detail → Tab shows "Buchungshistorie (0)" but the booking history list renders multiple booking cards (e.g., 4 entries).

**Root Cause:**

The tab count badge used `guest.total_bookings` from the guest record, but the actual booking history is fetched separately via the timeline API. If `guest.total_bookings` is 0 or stale, the badge shows 0 even though timeline items are rendered.

**Fix Pattern:**

Derive the count from the actual timeline data fetched, not from the guest record:

```typescript
// Store timeline total from API response
const [timelineTotal, setTimelineTotal] = useState<number>(0);

// When fetching timeline
const timelineData: TimelineResponse = await apiClient.get(
  `/api/v1/guests/${guestId}/timeline?limit=10&offset=0`,
  accessToken
);
setTimeline(timelineData.bookings);
setTimelineTotal(timelineData.total ?? 0);

// In tab label - use max to handle cases where API total is 0 but items exist
<button>
  Buchungshistorie ({Math.max(timelineTotal, timeline.length)})
</button>
```

**Why `Math.max(timelineTotal, timeline.length)`:**
- `timelineTotal` is the API's total count (may be paginated total)
- `timeline.length` is the actual items fetched (limited to 10)
- If API returns `total: 0` but items exist → show items count (prevents 0 badge with visible items)
- If API returns correct total → show total (e.g., 15 when showing 10 items)

**Prevention:**
- Always derive UI counts from the actual data being rendered, not from separate/stale fields
- For paginated data, display either `items.length` or `max(apiTotal, items.length)`

**Related Files:**
- `frontend/app/guests/[id]/page.tsx:218` - Booking history tab count

#### Booking → Zum Gast Navigation (Guard Against 404)

**Symptom:** Admin UI → Booking Details → Clicking "Zum Gast →" button navigates to `/guests/<guest_id>` but returns 404 with `{"detail":"Guest with ID '...' not found"}`.

**Root Cause:**

Booking records may have a `guest_id` that references a non-existent guest record (orphaned reference, deleted guest, or data inconsistency). The UI previously rendered the "Zum Gast" link without verifying the guest exists, causing 404 navigation.

**Fix Pattern:**

Before rendering the guest link, verify the guest exists:

```typescript
const [guestExists, setGuestExists] = useState<boolean | null>(null);

// After fetching booking
if (bookingData.guest_id) {
  try {
    await apiClient.get(`/api/v1/guests/${bookingData.guest_id}`, accessToken);
    setGuestExists(true);
  } catch (guestErr) {
    if (guestErr instanceof ApiError && guestErr.status === 404) {
      setGuestExists(false);
    }
  }
}

// Conditional rendering
{booking.guest_id && guestExists === true && (
  <Link href={`/guests/${booking.guest_id}`}>Zum Gast →</Link>
)}
{booking.guest_id && guestExists === false && (
  <div>Gast nicht verknüpft</div>
)}
```

**UI Behavior:**
- If guest exists (200) → Show "Zum Gast →" link
- If guest missing (404) → Show "Gast nicht verknüpft" text (no link)
- In IDs section → Show "Gast-ID (nicht verknüpft)" label when guest doesn't exist

**Prevention:**
- Always verify foreign key references before navigation
- Use guard checks for optional relationships to prevent 404 user experience
- For orphaned references, show inline status ("nicht verknüpft") instead of broken links

**Related Files:**
- `frontend/app/bookings/[id]/page.tsx:72-89,194-206,313` - Guest existence check and conditional rendering

#### Booking Details Shows "NaN €"

**Symptom:** Admin UI → Booking Details → Preisinformationen section shows "Steuer: NaN €" (or other fields like "Subtotal: NaN €", "Cleaning Fee: NaN €").

**Root Cause:**

Monetary fields from the API (`tax`, `subtotal`, `cleaning_fee`, etc.) are strings (e.g., `"0.00"`) but may be `null`, `undefined`, or empty strings in some cases. The `formatCurrency()` function called `parseFloat(amount)` directly without validation, causing:
- `parseFloat(null)` → `NaN`
- `parseFloat(undefined)` → `NaN`
- `parseFloat("")` → `NaN`
- `Intl.NumberFormat().format(NaN)` → `"NaN €"`

**Fix Pattern:**

Add a `safeNumber` helper to coerce invalid values to 0 before formatting:

```typescript
const safeNumber = (value: string | null | undefined): number => {
  if (value === null || value === undefined || value === "") return 0;
  const num = parseFloat(value);
  return isNaN(num) ? 0 : num;
};

const formatCurrency = (amount: string | null | undefined) => {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  }).format(safeNumber(amount));
};
```

**Result:**
- Null/undefined/empty monetary fields → display as `"0,00 €"`
- Invalid strings → display as `"0,00 €"`
- Valid strings like `"42.50"` → display as `"42,50 €"`
- Never renders `"NaN €"`

**Prevention:**
- Always validate/coerce monetary values before formatting
- Use safe parsers for all numeric fields that may be null/undefined
- Add regression guards: `isNaN(num) ? 0 : num`

**Related Files:**
- `frontend/app/bookings/[id]/page.tsx:117-128` - safeNumber helper and formatCurrency

#### DSGVO / Guest vs Booking Linkage (Best Practice)

**Data Model Philosophy:**

The PMS follows DSGVO-minimal best practices for guest-booking relationships:
- **Guest is optional**: Bookings can exist without a linked guest (guest_id=NULL is valid)
- **Booking is standalone**: Preserves business records even after guest deletion (DSGVO right to erasure)
- **When guest_id is set, it MUST reference a valid guest**: Foreign key constraint prevents orphaned references
- **Never use Auth User UUID as guest_id**: Guests are CRM entities, not authentication entities

**Database Constraints:**

```sql
-- Foreign key with ON DELETE SET NULL
ALTER TABLE bookings
ADD CONSTRAINT fk_bookings_guest_id
FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE SET NULL;
```

**ON DELETE SET NULL behavior:**
- When guest deleted (DSGVO erasure request) → booking.guest_id becomes NULL
- Booking history preserved for business/accounting purposes
- Guest data (PII) removed from system
- Booking shows "Gast nicht verknüpft" in UI

**API Validation (Create/Update):**

When creating/updating bookings:
1. **If `guest_id` provided:** Validate guest exists in same agency, else 422 error
2. **If guest data provided** (email/phone/name): Upsert guest, then set guest_id
3. **If neither:** guest_id remains NULL (booking without CRM linkage)

```python
# In booking service create_booking():
if guest_id_input is not None:
    guest_exists = await db.fetchval(
        "SELECT EXISTS(SELECT 1 FROM guests WHERE id = $1 AND agency_id = $2)",
        guest_id_input, agency_id
    )
    if not guest_exists:
        raise ValidationException(
            f"Guest with ID '{guest_id_input}' not found or does not belong to this agency"
        )
```

**Migration Safety:**

Migration `20260105150000_enforce_booking_guest_fk.sql` handles existing bad data:
1. **Cleanup orphaned references:** `UPDATE bookings SET guest_id=NULL WHERE guest_id NOT IN (SELECT id FROM guests)`
2. **Add FK constraint:** Safe after cleanup, no data loss
3. **Add index:** Speeds up FK checks and guest-based queries

**Troubleshooting:**

| Symptom | Root Cause | Resolution |
|---------|-----------|------------|
| 422 "Guest with ID '...' not found" on booking creation | Provided guest_id doesn't exist in guests table | Verify guest exists, or provide guest data for upsert instead |
| Booking shows "Gast nicht verknüpft" | Guest was deleted (DSGVO erasure) or guest_id was NULL | Expected behavior - booking preserved, guest link cleared |
| Cannot create booking with guest_id | Guest belongs to different agency | Use guest from same agency, or create new guest |

**Related Files:**
- `backend/app/services/booking_service.py:540-553` - Guest existence validation
- `supabase/migrations/20260105150000_enforce_booking_guest_fk.sql` - FK constraint migration

**Production Issue: 500 ResponseValidationError After FK ON DELETE SET NULL**

**Symptom:** After applying FK constraint migration, `GET /api/v1/bookings/{id}` returns 500 error:
```json
{
  "detail": [
    {
      "loc": ["response", "guest_id"],
      "msg": "UUID input should be a string/bytes/UUID object",
      "input": null
    }
  ]
}
```

**Root Cause:**

After FK constraint with `ON DELETE SET NULL`, bookings can have `guest_id=NULL` (guest deleted or booking created without guest). However, `BookingResponse` schema defined `guest_id: UUID` (non-nullable), causing FastAPI response validation to fail when serializing bookings with NULL guest_id.

**Fix:**

Change `guest_id` in `BookingResponse` schema to nullable:
```python
# Before (breaks with NULL guest_id)
guest_id: UUID = Field(description="Guest making the booking")

# After (allows NULL per DSGVO design)
guest_id: Optional[UUID] = Field(
    default=None,
    description="Guest making the booking (nullable - guest optional per DSGVO design)"
)
```

**Prevention:**
- When adding FK constraints with `ON DELETE SET NULL`, ensure response schemas allow NULL
- Test API responses with NULL foreign keys before deploying constraints
- Align schema nullability with database column constraints

**Related Files:**
- `backend/app/schemas/bookings.py:662` - BookingResponse.guest_id now Optional[UUID]

#### Guest Booking History Consistency

**Symptom:** Guests list shows `total_bookings=0` but guest detail timeline displays multiple bookings (e.g., 4 entries shown).

**Root Cause:**

Inconsistency between two booking count queries:
- **Timeline API** (`GET /api/v1/guests/{id}/timeline`): Counts ALL bookings WHERE `bookings.guest_id = guest.id`
- **Old trigger** (`update_guest_statistics`): Filtered by status, excluded cancelled/declined/no_show bookings
- Result: UX confusion - "0 bookings listed but 4 shown in history"

**DSGVO/Business Rule:**

Guest booking history follows FK-based linkage ONLY:
- **Source of truth**: `bookings.guest_id` (FK to guests.id)
- **Counts ALL bookings** linked to guest (including cancelled)
- **Does NOT count**: Bookings with `guest_id=NULL` (guest optional by design)
- **Does NOT infer**: By auth_user_id, email, or other heuristics

**Fix:**

Align `total_bookings` computation with timeline query:
```sql
-- Updated trigger (migration 20260105160000)
total_bookings = (
  SELECT COUNT(*)
  FROM bookings
  WHERE guest_id = NEW.guest_id
    -- No status filter - count ALL bookings
    -- Aligns with timeline API behavior
)
```

**Timeline Query (unchanged, correct):**
```sql
-- backend/app/services/guest_service.py:675-680
SELECT COUNT(*)
FROM bookings b
WHERE b.guest_id = $1 AND b.agency_id = $2 AND b.deleted_at IS NULL
```

**Why Count Cancelled Bookings:**
- Part of guest's complete history (business record)
- Aligns with timeline display (shows all bookings regardless of status)
- Consistent UX: count matches what user sees

**Troubleshooting:**

| Symptom | Root Cause | Resolution |
|---------|-----------|------------|
| total_bookings=0 but timeline shows bookings | Old trigger had status filter | Apply migration 20260105160000 to align trigger |
| Expected bookings not shown in timeline | Bookings have guest_id=NULL | Link bookings to guest via booking create/update with valid guest_id |
| Timeline shows 0 for guest with bookings in agency | Bookings linked to different guest_id | Verify correct guest linkage in bookings table |

**Prevention:**
- Use same WHERE clause for counts and list queries
- Document filtering rules in API comments
- Test count endpoints against list endpoints in integration tests

**Related Files:**
- `supabase/migrations/20260105160000_align_guest_total_bookings_with_timeline.sql` - Fixed trigger
- `backend/app/services/guest_service.py:675-680` - Timeline count query (source of truth)

---

## Admin UI — Visual QA Checklist (Layout v2)

**Purpose:** Browser-based verification checklist for Admin UI layout and visual quality after Theme v2 updates.

**What Changed in v2:**
- Primary palette: Blue/indigo (#2563eb) instead of green (trustworthy, modern)
- Icons: Lucide React icons (professional, consistent) instead of emojis
- Sidebar scrollbar: Hidden (scrollbar-hide utility) but scroll still works
- Header overlap: Fixed with sticky + blur background (no content overlap)
- Sidebar animation: Removed width transitions to eliminate jank on navigation
- Brand header: Improved with gradient avatar + divider
- Collapsed state: Better tooltips, rounded-2xl icon containers, professional spacing

**Browser Verification Checklist:**

```bash
# Navigate to Admin UI
open https://admin.fewo.kolibri-visions.de/login

# After login, verify Layout v2:
□ Background is very light slate (#f8fafc)
□ Sidebar uses Lucide icons (not emojis)
□ Sidebar scrollbar is hidden (but scroll works if needed)
□ Sidebar has NO width animation jank when navigating between pages
□ Brand header shows gradient avatar + agency name with divider below
□ Active nav item has blue background (#2563eb) with white icon
□ Inactive nav items have rounded-2xl light backgrounds
□ Topbar is sticky with blur background (bg-bo-bg/80 backdrop-blur-md)
□ Topbar does NOT overlap content when scrolling
□ Primary buttons use blue (#2563eb)
□ Status badges use semantic colors (green=success, red=danger, blue=info)
□ Collapsed sidebar shows tooltips on hover
□ Collapsed sidebar icons are in rounded-2xl containers (not circles)
□ Search bar in topbar uses Lucide Search icon
□ Notification buttons use Lucide icons (MessageSquare, Bell)

# Test navigation between pages (NO sidebar jank):
- Click Dashboard → no sidebar width animation
- Click Buchungen → no sidebar width animation
- Click Objekte → no sidebar width animation
- Click Verbindungen → no sidebar width animation
- Sidebar should feel stable, only color changes on active item

# Test scrolling (header doesn't overlap):
- Go to /bookings (list page with table)
- Scroll down → header stays at top with blur, table rows visible below header
- Header NEVER covers table content

# Test collapsed mode:
- Click collapse button (ChevronLeft icon)
- Sidebar width changes to narrow (w-24)
- Only icons visible, text hidden
- Hover over nav icons → tooltips appear with labels
- No visible scrollbar in collapsed mode
- Icons in rounded-2xl containers with proper spacing

# Test palette consistency:
- Check buttons: should use blue primary (#2563eb)
- Check active states: blue not green
- Check status chips: green for confirmed, red for cancelled, blue for requested
```

**Common Issues:**

**Problem:** Sidebar still shows scrollbar

**Solution:**
```bash
# Check if scrollbar-hide class is applied
# DevTools → Inspect nav element → Should have class "scrollbar-hide"
# CSS should have:
#   -ms-overflow-style: none;
#   scrollbar-width: none;
#   ::-webkit-scrollbar { display: none; }

# If missing, rebuild frontend:
cd frontend && rm -rf .next && npm run dev
```

**Problem:** Sidebar still animates/janks on navigation

**Solution:**
```bash
# Check sidebar aside element in DevTools
# Should NOT have "transition-all" or "transition-width" classes
# Only collapse state changes width: isCollapsed ? "w-24" : "w-72"
# No duration/animation on width change

# Verify AdminShell.tsx line ~287-291:
# Should be: className={`hidden lg:block flex-shrink-0 ${isCollapsed ? "w-24" : "w-72"}`}
# NOT: className="... transition-all duration-300 ..."
```

**Problem:** Header overlaps content when scrolling

**Solution:**
```bash
# Check header element in DevTools
# Should have: "sticky top-0 z-30 bg-bo-bg/80 backdrop-blur-md"
# Ensure main content is NOT using negative margin or absolute positioning
# Content should flow naturally below header

# Verify layout structure:
# <div flex flex-col>
#   <header sticky> ... header content
#   <main flex-1> ... page content (starts AFTER header, not under it)
```

**Problem:** Icons still showing as emojis

**Solution:**
```bash
# Check if lucide-react is installed:
cd frontend && npm list lucide-react
# Should show: lucide-react@x.x.x

# If not installed:
npm install lucide-react

# Check AdminShell.tsx imports (lines 6-25):
# Should import from "lucide-react" (LayoutDashboard, Home, Calendar, etc.)

# Check NAV_GROUPS icon properties (lines 54-93):
# Should be: icon: LayoutDashboard (not icon: "📊")

# Rebuild:
rm -rf .next && npm run dev
```

**Problem:** Primary color still green instead of blue

**Solution:**
```bash
# Check globals.css Theme v2 palette (lines 24-60)
# Should have:
#   --bo-primary: #2563eb;  /* Primary blue (trustworthy) */
#   --bo-primary-hover: #1e3a8a;

# NOT:
#   --bo-primary: #4C6C5A;  /* Primary green */

# Check DevTools → Elements → :root → Styles
# Verify --bo-primary is #2563eb

# If wrong, ensure latest commit is deployed
# Hard refresh browser: Cmd+Shift+R
```

**Related Sections:**
- [Admin UI Sidebar Architecture (Single Source of Truth)](#admin-ui-sidebar-architecture-single-source-of-truth)
- [Admin UI Visual Style (Backoffice Theme v1)](#admin-ui-visual-style-backoffice-theme-v1)

---

## Admin UI — Header: Language Switch + Profile Dropdown

**Purpose:** Document the header changes that replaced search with language dropdown and added profile menu.

**What Changed:**
- **Search field removed** - Previously occupied center of topbar
- **Language dropdown added** - Shows current language flag (🇩🇪/🇬🇧/🇸🇦) with dropdown to switch
- **Profile dropdown added** - User icon in top-right opens menu with profile links
- **Page title simplified** - Left side shows only page name (e.g. "Verbindungen"), removed "Hello, email!" greeting

**Language Switcher:**
- **Location:** Top-right area, before notification icons
- **Display:** Current language flag + code (e.g. 🇩🇪 DE)
- **Dropdown:** Click to show all languages (Deutsch, English, العربية)
- **Persistence:** Selection saved in localStorage with key `bo_lang`
- **Supported languages:**
  - `de` - Deutsch (🇩🇪)
  - `en` - English (🇬🇧)
  - `ar` - العربية (🇸🇦)

**Profile Dropdown:**
- **Location:** Far right of topbar, after notifications
- **Icon:** User icon (Lucide `User` component)
- **Dropdown content:**
  - User display name (extracted from email if needed)
  - Role badge (e.g. "Admin", "User")
  - Links:
    - Profil → `/profile`
    - Profil bearbeiten → `/profile/edit`
    - Sicherheit → `/profile/security`

**Profile Routes:**
All profile routes use AdminShell layout with authentication:
- `/profile` - Profile overview (stub page)
- `/profile/edit` - Edit profile settings (stub page)
- `/profile/security` - Security settings (stub page)

Note: Profile pages are currently minimal stubs showing "Demnächst verfügbar" (Coming soon). Full implementation planned for future phase.

**localStorage Keys:**
- `bo_lang` - Stores selected language code (de/en/ar)
- `sidebar-collapsed` - Stores sidebar collapse state (unchanged)

**Verification Checklist:**
```bash
# Open Admin UI
open https://admin.fewo.kolibri-visions.de/dashboard

# Visual checks:
□ Header left shows only page title (e.g. "Dashboard")
□ No "Hello, email!" greeting visible
□ Language dropdown visible (flag + code)
□ Click language dropdown → shows all 3 languages
□ Select language → persists after page reload
□ Profile icon visible (User icon)
□ Click profile → dropdown opens with name, role, and 3 links
□ Profile links navigate to correct routes
□ Profile pages load (even if showing "Coming soon")

# localStorage verification:
# DevTools → Application → localStorage → Check for "bo_lang" key after switching language
```

**Related Sections:**
- [Admin UI — Visual QA Checklist (Layout v2)](#admin-ui--visual-qa-checklist-layout-v2)
- [Admin UI Sidebar Architecture (Single Source of Truth)](#admin-ui-sidebar-architecture-single-source-of-truth)

---

## Frontend Build Failures (TSX/JSX Syntax Errors)

**Problem:** Coolify deployment fails with TypeScript/JSX syntax errors like:
```
Expected ',', got '{'
```

**Common Causes:**
1. **Extra closing tags** - Premature closure of JSX container
2. **Mismatched braces** - Stray `}` or `]` breaking JSX context
3. **JSX comments outside JSX** - Comments in array/object literal context

**Diagnosis:**
```bash
# Run build locally to reproduce
cd frontend && npm run build

# Check TypeScript compilation
npx tsc --noEmit --jsx preserve app/path/to/file.tsx
```

**Root Cause (connections/page.tsx Example):**
The connections page had an extra `</div>` at line 1221 that prematurely closed the main container `<div className="space-y-6">`, leaving modals outside the JSX tree.

Structure was:
```tsx
return (
  <div className="space-y-6">  {/* Line 1037 - Main container */}
    {/* Search + Table cards */}
    <div className="bg-white...">  {/* Line 1102 - Table card */}
      {/* Table content */}
    </div>  {/* Line 1220 - Closes table card */}
    </div>  {/* Line 1221 - EXTRA! Closes main container */}

    {/* Connection Details Modal */}  {/* Line 1223 - NOW OUTSIDE JSX! */}
```

**Fix:**
Remove the extra closing tag so modals remain inside the JSX tree:
```tsx
return (
  <div className="space-y-6">
    {/* Search + Table */}
    <div className="bg-white...">
      {/* Table content */}
    </div>  {/* Closes table card only */}

    {/* Modals still inside main container */}
    {selectedConnection && (<div>...</div>)}

  </div>  {/* Main container closes at end */}
);
```

**Verification:**
```bash
# Build must succeed
npm run build
# ✓ Compiled successfully
```

**Related:**
- Prerender errors about missing Supabase env vars are expected in local builds
- Coolify deployment has env vars configured via settings

---

## Frontend Build Failures (AdminShell Icon Typing)

**Problem:** Coolify deployment fails during `npm run build` with TypeScript error in AdminShell.tsx:
```
./app/components/AdminShell.tsx:169:37
Type error: Property 'strokeWidth' does not exist on type '{ className?: string }'
<Icon className="w-5 h-5" strokeWidth={1.75} />
```

**Root Cause:**
The `icon` property in `NavItem` interface was typed too narrowly:
```ts
// WRONG - only accepts className prop
icon: React.ComponentType<{ className?: string }>;
```

This prevented passing `strokeWidth` and other Lucide icon props like `size`, `color`, etc.

**Fix:**
Import and use the proper `LucideIcon` type from lucide-react:
```ts
// Correct typing
import { type LucideIcon } from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;  // ✓ Accepts all Lucide props including strokeWidth
  roles?: string[];
  planLocked?: boolean;
}
```

**Verification:**
```bash
# Local build test
cd frontend && npm run build

# Should compile successfully with no strokeWidth errors
# All icon usages with strokeWidth={1.75} will now type-check correctly
```

**Files Changed:**
- `frontend/app/components/AdminShell.tsx` - Updated NavItem interface to use LucideIcon type

**Related:**
- All icons in AdminShell are Lucide React icons (LayoutDashboard, Home, Calendar, etc.)
- strokeWidth is a valid prop for all Lucide icons (controls line thickness)

---

## Deploy Verification + Implemented vs Verified

### Overview
This section documents the "Implemented vs Verified" best-practice workflow for production deployments.

**Status Semantics**:
- **Implemented**: Feature code merged to main branch, deployed to staging/production
- **Verified**: Automatic production verification succeeded (deploy script + health checks)

**Key Principle**: Only mark features as "Verified" after automated deploy verification succeeds in production environment.

### Deploy Verification Script

**Script**: `backend/scripts/pms_verify_deploy.sh`

**Purpose**: Automatically verify successful deployment and commit hash in production/staging.

**Usage**:
```bash
# On HOST-SERVER-TERMINAL (production/staging server)
# Basic verification
API_BASE_URL=https://api.example.com ./backend/scripts/pms_verify_deploy.sh

# With commit verification (recommended for CI/CD)
API_BASE_URL=https://api.example.com \
EXPECT_COMMIT=$(git rev-parse HEAD) \
./backend/scripts/pms_verify_deploy.sh
```

**Endpoints Checked**:

**EXPECT_COMMIT - Short SHA Support**:

The `EXPECT_COMMIT` parameter accepts both full (40-char) and short (7+ char) commit SHAs. The script uses intelligent prefix matching:

- **Short SHA** (recommended): `EXPECT_COMMIT=5767b15` - more readable, typical git convention
- **Full SHA**: `EXPECT_COMMIT=5767b154906f9edf037fc9bbc10312126698cc29` - exact match

Verification passes if the deployed `source_commit` starts with the expected prefix (case-insensitive). Output indicates "prefix match" or "exact match" for clarity.

1. `GET /health` - Basic health check
2. `GET /health/ready` - Readiness check (database connectivity)
3. `GET /api/v1/ops/version` - Deployment version metadata

**Exit Codes**:
- `0`: Success (all checks passed)
- `1`: Missing configuration (API_BASE_URL not set)
- `2`: Endpoint failure (non-200 status or parse error)
- `3`: Commit mismatch (EXPECT_COMMIT set but source_commit doesn't match)

**Example Output**:
```
╔════════════════════════════════════════════════════════════╗
║ PMS Deploy Verification                                    ║
╚════════════════════════════════════════════════════════════╝
API Base URL: https://api.example.com

[1/3] GET /health
✅ Status: 200 OK

[2/3] GET /health/ready
✅ Status: 200 OK

[3/3] GET /api/v1/ops/version
✅ Status: 200 OK
📦 Service: pms-backend
🌍 Environment: production
🔖 API Version: 0.1.0
📝 Source Commit: abc123def456
⏰ Started At: 2024-01-05T10:30:00Z

╔════════════════════════════════════════════════════════════╗
║ ✅ All checks passed!                                      ║
╚════════════════════════════════════════════════════════════╝
```

### Version Endpoint

**Marking Features as VERIFIED**:

After running `pms_verify_deploy.sh` with `EXPECT_COMMIT` and receiving exit code 0 (all checks passed):

1. Capture the script output as evidence
2. Update the corresponding entry in `backend/docs/project_status.md`:
   - Change header from `✅` to `✅ VERIFIED`
   - Add a "Verification (PROD)" subsection with:
     - Date and environment
     - Commit hash verified
     - Command executed
     - Verification results (endpoints, commit match, exit code)
     - Evidence summary

**Example Entry Update**:
```markdown
### Feature Name ✅ VERIFIED

**Date Completed:** 2026-01-05
[... implementation details ...]

**Verification (PROD)** ✅ VERIFIED

**Date**: 2026-01-05 (post-deployment)
**Environment**: Production
**Commit**: abc123def456

**Command Executed** (HOST-SERVER-TERMINAL):
```bash
API_BASE_URL=https://api.production.example.com \
EXPECT_COMMIT=abc123def456 \
./backend/scripts/pms_verify_deploy.sh
```

**Verification Results**:
- ✅ GET /health → 200 OK
- ✅ GET /health/ready → 200 OK
- ✅ GET /api/v1/ops/version → 200 OK
  - source_commit: abc123def456
- ✅ Commit verification: PASSED
- ✅ Script exit code: 0

**Evidence**: All checks passed - feature operational in production.
```


**Endpoint**: `GET /api/v1/ops/version`

**Purpose**: Returns deployment metadata for automated verification and monitoring.

**Authentication**: None required (public endpoint, safe metadata only)

**Response Schema**:
```json
{
  "service": "pms-backend",
  "source_commit": "abc123def456",
  "environment": "production",
  "api_version": "0.1.0",
  "started_at": "2024-01-05T10:30:00Z"
}
```

**Response Fields**:
- `service`: Service name (always "pms-backend")
- `source_commit`: Git commit SHA (from SOURCE_COMMIT env var, null if not set)
- `environment`: Environment name (development/staging/production)
- `api_version`: FastAPI application version
- `started_at`: ISO 8601 timestamp of process start time

**Environment Variables**:
- `SOURCE_COMMIT`: Git commit SHA (set by CI/CD pipeline)
- `ENVIRONMENT`: Environment name (development/staging/production)

**Characteristics**:
- **No database calls**: Always fast, suitable for health checks
- **No authentication**: Safe metadata only, no secrets exposed
- **Cheap**: Suitable for frequent monitoring/alerting polls

### Workflow: Implemented → Verified

**Step 1: Implementation**
1. Merge feature code to main branch
2. CI/CD pipeline builds and deploys to staging/production
3. Mark feature status as "Implemented" in project_status.md

**Step 2: Verification**
1. Run deploy verification script on production server:
   ```bash
   API_BASE_URL=https://api.production.example.com \
   EXPECT_COMMIT=$(git rev-parse HEAD) \
   ./backend/scripts/pms_verify_deploy.sh
   ```
2. If script exits with code 0 (success):
   - All endpoints returned 200 OK
   - Commit hash matches expected value
   - Mark feature status as "Verified" in project_status.md

**Step 3: Evidence**
- Save script output as deployment evidence
- Include in deployment log/changelog
- Reference commit SHA in verification notes

**Example project_status.md Entry**:
```markdown
### API - Deploy Verification Endpoint ✅ VERIFIED

**Date**: 2024-01-05  
**Status**: Implemented + Verified in production  
**Commit**: abc123def456

**Issue**: Need automated way to verify production deployments

**Implementation**:
- Added GET /api/v1/ops/version endpoint (no DB, no auth)
- Created backend/scripts/pms_verify_deploy.sh
- Updated runbook with verification workflow

**Verification**:
- ✅ Deployed to production (2024-01-05 15:30 UTC)
- ✅ Script passed: all endpoints 200 OK, commit verified
- ✅ Monitoring polling /ops/version successfully

**Expected Result**:
- Deploy verification script exits 0 on successful deployment
- Commit hash verification prevents wrong-version deploys
- Monitoring can track deployments via source_commit field
```

### Troubleshooting

**Problem**: Script exits with code 2 (endpoint failure)

**Diagnosis**:
- Check script output for which endpoint failed (health, ready, or version)
- Verify API_BASE_URL is correct and server is reachable
- Check server logs for errors

**Solution**:
```bash
# Test endpoints manually
curl -v https://api.example.com/health
curl -v https://api.example.com/health/ready
curl -v https://api.example.com/api/v1/ops/version
```

---

**Problem**: Script exits with code 3 (commit mismatch)

**Diagnosis**:
- SOURCE_COMMIT env var not set in deployment
- Wrong commit deployed (e.g., stale Docker image)

**Solution**:
```bash
# Check what's deployed
curl https://api.example.com/api/v1/ops/version

# Verify CI/CD sets SOURCE_COMMIT in deployment
# Example Dockerfile:
ARG SOURCE_COMMIT
ENV SOURCE_COMMIT=${SOURCE_COMMIT}

# Example docker-compose.yml:
environment:
  SOURCE_COMMIT: ${GITHUB_SHA}
```

---

**Problem**: source_commit field returns null

**Diagnosis**:
- SOURCE_COMMIT environment variable not set in deployment
- Deployment process doesn't pass git commit SHA

**Solution**:
1. Update CI/CD pipeline to set SOURCE_COMMIT:
   ```bash
   # In CI/CD script
   export SOURCE_COMMIT=$(git rev-parse HEAD)
   # or
   docker build --build-arg SOURCE_COMMIT=$(git rev-parse HEAD) .
   ```
2. Update Dockerfile to accept and use SOURCE_COMMIT:
   ```dockerfile
   ARG SOURCE_COMMIT
   ENV SOURCE_COMMIT=${SOURCE_COMMIT}
   ```
3. Verify deployment:
   ```bash
   curl https://api.example.com/api/v1/ops/version | grep source_commit
   ```

---


## Change Log
## Race-Safe Bookings (DB Exclusion Constraint)

### Overview

This section documents the database-level exclusion constraint that prevents overlapping bookings for the same property, ensuring inventory safety even under concurrent API requests.

**Problem**: Application-level availability checks are not race-safe (TOCTOU: time-of-check-time-of-use). Multiple concurrent POST /api/v1/bookings can create overlapping dates, resulting in double-bookings.

**Solution**: PostgreSQL EXCLUSION constraint with btree_gist extension provides atomic, database-level guarantees that no overlaps can occur.

### What It Prevents

The `bookings_no_overlap_exclusion` constraint prevents overlapping bookings for the same property when the booking status is **inventory-occupying**:

**Blocking Statuses** (inventory-occupying):
- `confirmed`: Booking is confirmed and occupies property
- `checked_in`: Guest is currently in the property

**Non-blocking Statuses** (do NOT occupy inventory):
- `cancelled`, `declined`, `no_show`: Booking is terminated
- `checked_out`: Guest has left
- `inquiry`, `pending`: Not yet confirmed

### Constraint Details

**Constraint Name**: `bookings_no_overlap_exclusion`

**Definition**:
```sql
ALTER TABLE bookings
ADD CONSTRAINT bookings_no_overlap_exclusion
EXCLUDE USING gist (
    property_id WITH =,
    daterange(check_in, check_out, '[)') WITH &&
)
WHERE (
    check_in IS NOT NULL
    AND check_out IS NOT NULL
    AND status IN ('confirmed', 'checked_in')
    AND deleted_at IS NULL
);
```

**Date Range Semantics**:
- `[)` means [check_in, check_out) - inclusive start, exclusive end
- Check-in day: included
- Check-out day: excluded (guest leaves, property available)
- Example: [2024-01-01, 2024-01-05) = nights of Jan 1-4, free on Jan 5

### How to Apply in Production

**Step 1: Verify btree_gist Extension**

```sql
-- In Supabase SQL Editor (or psql)
SELECT * FROM pg_extension WHERE extname = 'btree_gist';
```

If not installed, the migration will create it automatically.

**Step 2: Check for Existing Overlaps**

Before applying the migration, check if existing data has overlaps:

```sql
-- Find overlapping bookings
SELECT b1.id, b1.property_id, b1.check_in, b1.check_out, b1.status,
       b2.id AS id2, b2.check_in AS check_in2, b2.check_out AS check_out2, b2.status AS status2
FROM bookings b1
INNER JOIN bookings b2 ON (
  b1.property_id = b2.property_id
  AND b1.id < b2.id
  AND daterange(b1.check_in, b1.check_out, '[)') && daterange(b2.check_in, b2.check_out, '[)')
  AND b1.status IN ('confirmed', 'checked_in')
  AND b2.status IN ('confirmed', 'checked_in')
  AND b1.deleted_at IS NULL
  AND b2.deleted_at IS NULL
);
```

**Step 3: Resolve Conflicts (if any)**

If overlaps found, resolve before migration:

```sql
-- Option 1: Cancel one booking
UPDATE bookings
SET status = 'cancelled',
    cancellation_reason = 'Overlap resolution before constraint',
    cancelled_by = 'system',
    cancelled_at = NOW()
WHERE id = '<conflicting-booking-id>';

-- Option 2: Adjust dates
UPDATE bookings
SET check_out = '2024-01-05'  -- Adjust to not overlap
WHERE id = '<conflicting-booking-id>';
```

**Step 4: Apply Migration**

```bash
# Via Supabase Dashboard -> SQL Editor
# Paste contents of: supabase/migrations/20260105170000_race_safe_bookings_exclusion.sql
# Run migration
```

Or via CLI:
```bash
supabase db push
```

**Step 5: Verify Constraint**

```sql
-- Check constraint exists
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'bookings_no_overlap_exclusion';

-- Should return:
-- conname: bookings_no_overlap_exclusion
-- contype: x (exclusion)
-- pg_get_constraintdef: EXCLUDE USING gist (property_id WITH =, ...
```

### Testing

**Run Concurrency Smoke Test** (HOST-SERVER-TERMINAL):

```bash
# On production server or with production API access
export API_BASE_URL="https://api.production.example.com"
export TOKEN="$(./backend/scripts/get_fresh_token.sh)"

./backend/scripts/pms_booking_concurrency_smoke.sh
```

**Expected Output**:
```
╔════════════════════════════════════════════════════════════╗
║ PMS Booking Concurrency Smoke Test                        ║
╚════════════════════════════════════════════════════════════╝
API: https://api.production.example.com
Property: <uuid>
Dates: 2024-01-15 → 2024-01-17
Concurrency: 10 parallel requests

Results:
────────────────────────────────────────────────────────────
Total requests:     10
201 Created:        1 ✅
409 Conflict:       9 🚫
500 Server Error:   0 ⚠️
Other:              0
════════════════════════════════════════════════════════════

╔════════════════════════════════════════════════════════════╗
║ ✅ TEST PASSED                                             ║
╚════════════════════════════════════════════════════════════╝

Race-safe booking validation successful:
  - Exactly 1 booking created (201)
  - Exactly 9 requests rejected with 409 Conflict
  - Database exclusion constraint working correctly
  - No 500 errors (API properly maps constraint to 409)
```

**Important Note on Test Reuse**:
When rerunning the concurrency smoke test (e.g., after redeployment or for periodic verification), **always use a fresh date window** that doesn't overlap with previous test runs. If you reuse the same dates from a previous test, the property will already have a confirmed booking for those dates, causing all 10 concurrent requests to return 409 Conflict (10x409 instead of 1x201 + 9x409). This is a false negative—the constraint is working, but you won't see the expected "exactly 1 success" pattern.

**Best Practice**: Either:
- Set `CHECK_IN_DATE` and `CHECK_OUT_DATE` to future dates that haven't been tested yet
- Let the script use default dates (+14 days), which automatically advances with calendar time
- Cancel any bookings created by previous test runs before reusing the same date range

### Troubleshooting

---

**Problem**: Migration fails with "existing overlapping bookings found"

**Diagnosis**: Existing data has overlapping confirmed/checked_in bookings

**Solution**:
1. Query to find conflicts (see Step 2 above)
2. Review conflicting bookings with business team
3. Resolve: cancel one booking or adjust dates
4. Re-run migration

**Sample Error**:
```
ERROR:  Cannot create exclusion constraint: 2 existing overlapping bookings found.

Sample conflicts:
  property=abc-123: booking_id=xyz-1 [2024-01-01 to 2024-01-05] OVERLAPS booking_id=xyz-2 [2024-01-03 to 2024-01-07]
```

---

**Problem**: Concurrent booking requests return 500 Server Error

**Diagnosis**: API not properly catching ExclusionViolationError

**Solution**:
1. Check backend logs for `asyncpg.exceptions.ExclusionViolationError`
2. Verify booking_service.py catches exception and raises ConflictException
3. Verify exception handler maps ConflictException to 409
4. Check code at:
   - `backend/app/services/booking_service.py:766-829` (create_booking)
   - `backend/app/services/booking_service.py:1565-1576` (update_booking)

---

**Problem**: Concurrency smoke test shows multiple 201 (successes)

**Diagnosis**: Exclusion constraint not active or dates not overlapping

**Solution**:
1. Verify constraint exists: `SELECT * FROM pg_constraint WHERE conname = 'bookings_no_overlap_exclusion'`
2. Check if dates overlap: `SELECT daterange('2024-01-01', '2024-01-05', '[)') && daterange('2024-01-03', '2024-01-07', '[)')` (should be `t`)
3. Check booking status: constraint only blocks `confirmed` and `checked_in`
4. Check deleted_at: constraint excludes soft-deleted bookings

---

**Problem**: Need to temporarily disable constraint for data migration

**Diagnosis**: Bulk data import or migration needs to bypass constraint

**Solution** (use with caution):
```sql
-- Disable constraint (destructive - use only for migrations)
ALTER TABLE bookings DROP CONSTRAINT bookings_no_overlap_exclusion;

-- Perform data migration
-- ...

-- Re-enable constraint (check for overlaps first!)
-- Run pre-migration overlap check query from Step 2
-- Then re-apply constraint creation from migration file
```

---

**Problem**: Concurrency smoke test returns 0×201 and all 10×409 (all conflicts, no successes)

**Diagnosis**: Date window already booked (property has existing confirmed/checked_in booking for those dates)

**Symptoms**:
- `pms_booking_concurrency_smoke.sh` shows: 0 Created (201), 10 Conflict (409), 0 Server Errors
- Script prints "All requests returned 409 Conflict (0 successes)"
- Test is failing but API behavior is correct (constraint is working)

**Root Cause**:
- The date window being tested already has a booking
- All 10 concurrent requests correctly receive 409 Conflict
- This is NOT a test failure—it's expected behavior for already-booked dates

**Solution**:
1. **Use DATE_FROM/DATE_TO overrides** with known-free dates:
   ```bash
   export DATE_FROM="2026-12-01"
   export DATE_TO="2026-12-03"
   ./backend/scripts/pms_booking_concurrency_smoke.sh
   ```

2. **Rely on auto-shift** (default behavior as of 2026-01-05):
   - Script automatically detects "all 409s" and shifts window by `SHIFT_DAYS` (default 7)
   - Retries up to `MAX_WINDOW_TRIES` (default 10) times
   - First free window will yield expected 1×201 + 9×409

3. **Cancel existing booking** for the window:
   ```bash
   # Find booking for the window
   curl "$API_BASE_URL/api/v1/bookings?property_id=<uuid>&check_in=2026-09-14" \
     -H "Authorization: Bearer $TOKEN"

   # Cancel it
   curl -X POST "$API_BASE_URL/api/v1/bookings/<booking-id>/cancel" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"cancelled_by":"host","cancellation_reason":"Smoke test cleanup"}'
   ```

**Expected Behavior After Fix**:
- ✅ Script auto-shifts to free window and passes (1×201 + 9×409)
- ✅ OR manual override with DATE_FROM/DATE_TO succeeds
- ✅ Exit code 0 on success, exit code 2 if all retries exhausted

---

**Problem**: Concurrent booking requests return 500 Server Error with "foreign key constraint" violation

**Diagnosis**: API attempting to create bookings with invalid guest_id (not in guests table)

**Symptoms**:
- Backend logs show: `asyncpg.exceptions.ForeignKeyViolationError: insert or update on table "bookings" violates foreign key constraint "fk_bookings_guest_id"`
- Error message: `Key (guest_id)=<uuid> is not present in table "guests"`
- Concurrency smoke test: all 10 requests return 500

**Root Cause**:
- guest_id provided in request doesn't match any existing guest record
- Auth user ID (JWT sub) used as guest_id instead of actual guests table ID
- Concurrent guest upserts failing under load

**Solution**:
1. **Use existing guest_id**: Ensure guest exists before creating booking
   ```bash
   # Verify guest exists
   curl -H "Authorization: Bearer $TOKEN" \
        "$API_BASE_URL/api/v1/guests/$GUEST_ID"

   # If not found (404), create guest first:
   curl -X POST "$API_BASE_URL/api/v1/guests" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"email":"guest@example.com","first_name":"John","last_name":"Doe"}'
   ```

2. **For smoke test**: Use `GUEST_ID` env var or let script auto-pick/create
   ```bash
   export API_BASE_URL="https://api.example.com"
   export TOKEN="$(./backend/scripts/get_fresh_token.sh)"
   export GUEST_ID="<existing-guest-uuid>"  # Optional, auto-picked if not set
   ./backend/scripts/pms_booking_concurrency_smoke.sh
   ```

3. **Verify FK violation returns 422 (not 500)**: After fix, API should return:
   ```json
   {
     "error": "validation_error",
     "message": "guest_id does not reference an existing guest. Create the guest first or omit guest_id to create booking without guest."
   }
   ```

**Expected Behavior**:
- ✅ FK violations return 422 Unprocessable Entity (not 500)
- ✅ Exclusion violations return 409 Conflict
- ✅ Concurrency smoke test: 1 success (201), 9 conflicts (409), 0 errors (500)

**Code Reference**:
- FK violation handling: `backend/app/services/booking_service.py:833-855`
- Smoke test: `backend/scripts/pms_booking_concurrency_smoke.sh`

---

**Problem**: Smoke test script shows "syntax error in expression (error token is '0')" or "unbound variable" errors

**Diagnosis**: Bash parsing issues with counter variables under `set -euo pipefail`

**Symptoms**:
- Script output shows: `bash: 0: syntax error in expression (error token is "0")`
- Or: `bash: ERROR_COUNT: unbound variable`
- Test results show correct HTTP codes (1x201, 9x409) but script exits rc=1 or rc=2 instead of rc=0
- Counter values appear as "0\n0" (two lines) instead of single integer

**Root Cause**:
- Pattern `COUNT=$(grep -c ... || echo "0")` can produce "0\n0" when grep fails (outputs to stdout, then `|| echo "0"` also executes)
- Arithmetic evaluation `$((...))` on "0\n0" triggers "syntax error in expression"
- `set -u` requires all variables initialized before use, but counters were parsed directly without initialization

**Solution**:
1. **Initialize all counters to 0** before parsing:
   ```bash
   SUCCESS_COUNT=0
   CONFLICT_COUNT=0
   ERROR_COUNT=0
   ```

2. **Use robust parsing pattern**:
   ```bash
   # Safe pattern: grep || true, strip non-digits, default to 0
   SUCCESS_COUNT=$(grep -c "^201$" "$RESPONSES_FILE" 2>/dev/null || true)
   SUCCESS_COUNT=${SUCCESS_COUNT//[^0-9]/}  # strip non-digits
   [[ -n "$SUCCESS_COUNT" ]] || SUCCESS_COUNT=0
   ```

3. **Verify script version**: Ensure using latest version with counter parsing fix (commit 405d3f0 or later)

**Expected Behavior After Fix**:
- ✅ Script returns rc=0 when test passes (1 success, 9 conflicts, 0 errors)
- ✅ No "syntax error in expression" or "unbound variable" errors
- ✅ All counters are valid integers (0-10 range for 10 concurrent requests)

**Code Reference**:
- Counter parsing: `backend/scripts/pms_booking_concurrency_smoke.sh:262-291`

---

**Problem**: How to verify guest_id FK hardening in production

**Purpose**: Confirm that booking creation API correctly handles guest_id foreign key violations without returning 500 errors.

**When to Run**:
- After deploying guest_id FK hardening fix (commit with booking_service.py FK error handling)
- During routine production health checks
- Before marking feature as VERIFIED in project_status.md

**Steps**:
1. **Verify deployment commit**:
   ```bash
   export API_BASE_URL="https://api.example.com"
   export EXPECT_COMMIT="<commit-sha>"  # Expected production commit
   ./backend/scripts/pms_verify_deploy.sh
   ```

2. **Run guest_id FK smoke test**:
   ```bash
   export API_BASE_URL="https://api.example.com"
   export TOKEN="$(./backend/scripts/get_fresh_token.sh)"
   export PROPERTY_ID="<uuid>"  # Optional, auto-picks if not set
   ./backend/scripts/pms_booking_guest_id_fk_smoke.sh
   ```

3. **Expected results**:
   - Test 1 (guest_id omitted): 201 Created, guest_id=null
   - Test 2 (guest_id invalid): 422 Unprocessable Entity with actionable message
   - Exit code: rc=0
   - Auto-shift: Script automatically retries with shifted date window if 409 conflict encountered


**Success Criteria**:
- ✅ pms_verify_deploy.sh: Commit match + rc=0
- ✅ pms_booking_guest_id_fk_smoke.sh: Both tests pass + rc=0
- ✅ No 500 errors in either test case

**Failure Scenarios**:
- Test 1 returns 500: Booking service may be using auth user ID as guest_id fallback (check booking_service.py:555-558)
- Test 2 returns 500: FK violation not caught (check booking_service.py:833-855)
- Exit code rc=2: FK hardening broken, 500 errors present

**Code Reference**:
- Smoke test: `backend/scripts/pms_booking_guest_id_fk_smoke.sh`
- FK error handling: `backend/app/services/booking_service.py:833-855`
- Script docs: `backend/scripts/README.md` (search "guest_id FK Hardening")

---


### API Error Response

When exclusion constraint is triggered, API returns:

**HTTP 409 Conflict**:
```json
{
  "error": "conflict",
  "message": "Property is already booked for these dates",
  "conflict_type": "double_booking",
  "path": "/api/v1/bookings"
}
```

**Client Handling**:
- Do NOT retry automatically (conflict is permanent for same dates)
- Show user-friendly message: "Property unavailable for selected dates"
- Suggest alternative dates or properties

### Performance Considerations

**Index**: The EXCLUSION constraint creates a GIST index automatically.

**Advisory Lock**: Booking service acquires advisory lock per property to serialize concurrent requests and prevent deadlocks:

```sql
SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))
```

This ensures concurrent bookings for the same property are processed sequentially, preventing potential deadlock scenarios from overlapping constraint checks.

**Query Impact**: Minimal - GIST index lookups are O(log N).

---


## Smoke User Lifecycle

**Purpose**: Document the lifecycle of smoke test users and how to clean them up safely.

### User Creation

Smoke test users are created during API testing via the admin users endpoint:

**Typical creation pattern**:
```bash
# Create smoke test user
curl -X POST "$API_BASE_URL/api/v1/admin/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "pms-smoke-20260106-abc123@example.com",
    "password": "<generated-password>",
    "email_confirm": true
  }'
```

**Email naming convention**:
- Prefix: `pms-smoke-`
- Timestamp: YYYYMMDD or YYYYMMDD-HHMMSS
- Random suffix: 6-character hex
- Domain: `example.com` (test domain)
- Example: `pms-smoke-20260106-a3f7b2@example.com`

### Agency Membership

Smoke users may be linked to an agency via `team_members` table:

**Membership creation**:
```sql
INSERT INTO public.team_members (
  user_id,
  agency_id,
  role,
  is_active
) VALUES (
  '<smoke-user-id>',
  '<agency-id>',
  'staff',
  true
);
```

**Active membership** enables:
- Access to agency properties
- Booking creation/management
- Guest operations
- Channel Manager operations (if enabled)

### Cleanup Procedure

Use `pms_smoke_user_cleanup.sh` for safe cleanup:

**Step 1: Dry-run (default, safe)**:
```bash
# Show what would be cleaned up (no changes)
./backend/scripts/pms_smoke_user_cleanup.sh
```

**Step 2: Apply cleanup (deactivate membership)**:
```bash
# Deactivate membership in team_members (preserves auth user)
DRY_RUN=0 CONFIRM=1 ./backend/scripts/pms_smoke_user_cleanup.sh
```

**Step 3: Optional - Delete auth user**:
```bash
# Full cleanup: deactivate membership AND delete auth user
DRY_RUN=0 CONFIRM=1 CONFIRM_DELETE_USER=1 ./backend/scripts/pms_smoke_user_cleanup.sh
```

**What the script does**:
1. Finds the latest `pms-smoke-*@example.com` user (or uses `USER_ID` override)
2. Deactivates membership: `UPDATE team_members SET is_active=false WHERE user_id=...`
3. Optionally deletes auth user: `DELETE /auth/v1/admin/users/{id}` (requires explicit flag)

**Safety features**:
- Default `DRY_RUN=1` (no changes)
- Requires `CONFIRM=1` to apply changes
- Requires `CONFIRM_DELETE_USER=1` to delete auth user
- Never prints service keys or secrets to stdout
- Shows clear plan before executing destructive actions

### Security Notes

**CRITICAL - Never paste service keys in chat/logs**:
- The cleanup script requires `SB_SERVICE_KEY` (Supabase service role key)
- Script auto-detects from docker if not set: `docker exec supabase-kong printenv SUPABASE_SERVICE_KEY`
- Never echo or log the service key
- Only print key length for confirmation (e.g., "length: 274")

**Service key usage**:
- Used only for GoTrue Admin API calls (list/delete users)
- Passed via Authorization header (not in URL)
- Never logged or stored by the script

**Best practices**:
1. Always run dry-run first to verify target user
2. Use `USER_ID` override if you know the specific user to clean
3. Prefer membership deactivation over auth user deletion (less destructive)
4. Keep service keys in docker environment or 1Password (never in shell history)

### Related Documentation

- [Smoke User Cleanup Script](../scripts/README.md#smoke-user-cleanup-pms_smoke_user_cleanupsh) - Full script documentation
- [GoTrue Admin API](https://supabase.com/docs/reference/cli/global-flags#admin-api) - User management endpoints
- [Project Status](../docs/project_status.md) - Implementation status

---

## Direct Booking (Public) v0

**Purpose**: Public direct booking flow without authentication or payment integration.

**Production Status**: Verified in production on 2026-01-06 (commit d9db091, verify_rc=0, smoke_rc=0).

### What is included (v0)

**Endpoints** (no auth required):
1. GET /api/v1/public/availability - Check property availability for date range
2. POST /api/v1/public/booking-requests - Create public booking request

**Features**:
- No JWT/auth required (truly public endpoints)
- Guest creation/lookup by email (case-insensitive)
- Booking created with status="requested" (pending approval)
- Auto-detects agency via property_id
- Currency support: defaults to EUR if not specified; accepts 3-letter ISO codes (EUR, USD, GBP, etc.)
- Stub pricing (v0): nightly_rate, subtotal, and total_price all set to 0.00 to satisfy NOT NULL constraints; pricing engine integration comes in future version
- Proper error mapping:
  - 409 conflict_type=double_booking for overlapping bookings
  - 422 for FK violations/validation errors
  - Never returns 500 on constraint/validation errors

**What is NOT included (v0)**:
- ❌ Payment processing
- ❌ Email notifications
- ❌ Booking confirmation workflow (manual approval required)
- ❌ Availability calendar UI
- ❌ Price calculation

### How to run smoke test on HOST

**Prerequisites**:
- No token/auth required
- Need property ID (PID)

**Basic usage**:
```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export PID="<property-uuid>"
./backend/scripts/pms_direct_booking_public_smoke.sh
```

**With date override**:
```bash
export DATE_FROM="2037-01-01"
export DATE_TO="2037-01-03"
./backend/scripts/pms_direct_booking_public_smoke.sh
```

**Script behavior**:
1. Calls GET /api/v1/public/availability
2. Calls POST /api/v1/public/booking-requests
3. Auto-shifts date window on 409 conflicts (similar to other smoke scripts)
4. Exit 0 on success, 1 on unexpected codes, 2 on 500 errors

**Auto-retry**: If booking creation returns 409 (double_booking), automatically shifts window by SHIFT_DAYS (default 7) and retries up to MAX_WINDOW_TRIES (default 10) times.

### Troubleshooting

**Problem**: "PID (property ID) environment variable required"

**Solution**: Set PID explicitly (do NOT auto-pick in prod):
```bash
export PID="abc-123-uuid"
./backend/scripts/pms_direct_booking_public_smoke.sh
```

---

**Problem**: Booking creation returns 500 error

**Diagnosis**: Validation/FK/constraint errors not properly handled OR unhandled exception

**Solution**: Check backend logs for specific error type. Expected error mappings:
- Exclusion violation (double booking) → 409 conflict_type=double_booking
- FK violation (property/guest not found) → 422 with actionable message
- Validation error (invalid dates, etc.) → 422 with details
- Schema drift (UndefinedColumn/UndefinedTable) → 503 with migration guidance (see below)

If 500 persists, check logs for unexpected exceptions and file incident report.

---

**Problem**: Booking creation returns 503 "Database schema not installed or out of date"

**Diagnosis**: Schema drift - code references DB column/table/function that doesn't exist or has ambiguous signature

**Common Examples**:
```
# Case 1: Missing column
Backend logs: "column 'notes' of relation 'bookings' does not exist"
Response: 503 {"error":"service_unavailable","message":"Database schema not installed or out of date: column notes..."}

# Case 2: Ambiguous function
Backend logs: "function generate_booking_reference() is not unique"
Response: 503 {"error":"service_unavailable","message":"Database schema/function definitions out of date or duplicated: generate_booking_reference is ambiguous..."}
```

**Root Causes**:
- **Missing column**: Public booking endpoint tries to INSERT into column that doesn't exist (e.g., bookings.notes)
- **Ambiguous function**: Multiple `generate_booking_reference()` function signatures exist without proper type disambiguation
- **Schema drift**: DB migrations not run or schema out of sync with code

**Solution**:
1. Check if migration exists for the missing column/table/function
2. If migration exists, run it:
   ```bash
   cd /path/to/supabase
   supabase db push
   # OR manually apply migration SQL
   ```
3. For ambiguous function error:
   - Check for duplicate function definitions in database:
     ```sql
     SELECT proname, proargtypes, prosrc FROM pg_proc WHERE proname = 'generate_booking_reference';
     ```
   - Drop duplicate/old function signatures
   - Keep only one signature with explicit types (e.g., `generate_booking_reference(text)`)
   - Code uses explicit type cast: `public.generate_booking_reference($1::text)`
4. If migration does NOT exist:
   - Code should not reference the missing column/function (bug in code)
   - Public booking endpoint intentionally does NOT persist optional fields (like notes)
   - Verify `backend/app/api/routes/public_booking.py` generates booking_reference before INSERT
   - If code was reverted accidentally, redeploy correct version

**Prevention**: Public booking endpoint explicitly generates booking_reference with type cast (`$1::text`) before INSERT to avoid ambiguity. It does not rely on database DEFAULT values that may have ambiguous function calls.

---

**Problem**: Booking creation returns 422 "Property is missing agency assignment (agency_id)"

**Diagnosis**: Property tenant assignment missing - property exists but agency_id column is NULL

**Root Cause**:
- Property row exists in database but agency_id field is not populated
- This violates the NOT NULL constraint on bookings.agency_id
- Public booking endpoint resolves agency_id from property before creating booking

**SQL Diagnostic**:
```sql
-- Check if property exists and has agency_id populated
SELECT id, agency_id FROM public.properties WHERE id='<property-uuid>';

-- If agency_id is NULL, property needs tenant assignment
```

**Solution**:
1. If agency_id is NULL for the property:
   - Backfill agency_id for the property (assign it to correct agency/tenant)
   - Run migrations if agency_id column doesn't exist in properties table
   ```sql
   UPDATE public.properties SET agency_id = '<agency-uuid>' WHERE id = '<property-uuid>';
   ```
2. If agency_id column doesn't exist:
   - Run pending migrations to add agency_id to properties table
   ```bash
   cd /path/to/supabase
   supabase db push
   ```
3. Verify property now has agency_id:
   ```sql
   SELECT id, agency_id FROM public.properties WHERE id='<property-uuid>';
   ```

**Prevention**: Ensure all properties have agency_id populated before creating public bookings. Use database constraints or backfill scripts to enforce agency_id NOT NULL on properties table.

---

**Problem**: Booking creation returns 422 "Booking creation failed: currency is required"

**Diagnosis**: Currency field missing or NULL in booking request (should not happen with current API schema)

**Root Cause**:
- Public booking endpoint requires currency field (defaults to EUR)
- If currency is not provided or is NULL, booking INSERT fails NOT NULL constraint
- This error indicates request validation bypassed or schema mismatch

**Solution**:
1. Ensure currency is included in booking request payload:
   ```json
   {
     "property_id": "<uuid>",
     "date_from": "2026-06-01",
     "date_to": "2026-06-03",
     "adults": 2,
     "children": 0,
     "currency": "EUR",
     "guest": { ... }
   }
   ```
2. If omitted, API defaults to "EUR" (no need to explicitly set)
3. Currency must be 3-letter uppercase ISO code (EUR, USD, GBP, etc.)
4. Smoke script supports `PUBLIC_CURRENCY` env var (default: EUR):
   ```bash
   export PUBLIC_CURRENCY="USD"
   ./backend/scripts/pms_direct_booking_public_smoke.sh
   ```

**Validation Rules**:
- Must be exactly 3 alphabetic characters
- Automatically uppercased and trimmed
- Validated against pattern `^[A-Z]{3}$`

**Prevention**: Public booking endpoint now always sets currency (default EUR). This error should not occur in normal operation unless request schema validation is bypassed.

---

**Problem**: Booking creation returns 422 "null value in column 'nightly_rate' (or subtotal/total_price) violates not-null constraint"

**Diagnosis**: Pricing fields not set in booking INSERT (should not happen with current v0 implementation)

**Root Cause**:
- Bookings table has NOT NULL constraints on pricing fields: nightly_rate, subtotal, total_price
- Public booking v0 must provide stub pricing values (0.00) to satisfy these constraints
- Error indicates pricing stub values were not included in INSERT

**Solution**:
1. Verify public booking endpoint sets stub pricing:
   - `nightly_rate = Decimal("0.00")`
   - `subtotal = Decimal("0.00")`
   - `total_price = Decimal("0.00")`
2. Check INSERT statement includes these columns and bindings
3. Verify no schema drift (columns exist in bookings table):
   ```sql
   SELECT column_name, is_nullable, data_type
   FROM information_schema.columns
   WHERE table_name = 'bookings'
   AND column_name IN ('nightly_rate', 'subtotal', 'total_price');
   ```

**Expected Behavior (v0)**:
- All public bookings created with pricing = 0.00 (stub values)
- Status = "requested" (pending manual pricing/approval)
- Pricing engine integration comes in future version

**Prevention**: Public booking endpoint v0 always sets stub pricing defaults. This error should not occur unless code was reverted or INSERT statement modified incorrectly.

---

**Problem**: All window attempts exhausted

**Diagnosis**: Every tested date window already has bookings

**Solution**: Use DATE_FROM/DATE_TO with known-free dates:
```bash
export DATE_FROM="2037-01-01"
export DATE_TO="2037-01-03"
./backend/scripts/pms_direct_booking_public_smoke.sh
```

---

**Problem**: GET /api/v1/public/availability returns 404 Not Found, OpenAPI docs show zero /api/v1/public paths

**Diagnosis**: Public booking router not mounted (module system failed and failsafe not triggered)

**Root Cause**: Router not mounted via module registry AND failsafe explicit mounting in app factory did not execute

**Solution**:
1. Check backend logs for failsafe mounting messages:
   - ✅ Expected: "Public booking router already mounted via module system"
   - ⚠️  Fallback: "Public booking router not found in mounted routes, applying failsafe mounting"
   - ❌ Neither message → app factory not reached or error during startup
2. Verify module registration:
   - `backend/app/modules/public_booking.py` exists with ModuleSpec
   - `backend/app/modules/bootstrap.py:98` includes `from . import public_booking`
3. Verify failsafe mounting in app factory:
   - `backend/app/main.py:142-154` has failsafe include_router after mount_modules()
4. Check OpenAPI docs at `/docs` - should show "Public Direct Booking" tag
5. Use preflight check: `curl https://api.example.com/api/v1/public/ping` (should return 200 {"status": "ok"})

**Architecture**: Two-layer mounting guarantees router availability:
- **Layer 1 (Correct)**: Module system via `mount_modules()` registers public_booking module
- **Layer 2 (Failsafe)**: Explicit `include_router()` in main.py after module mounting if Layer 1 failed

**Prevention**: Smoke script includes /ping preflight check with OpenAPI diagnostics to detect unmounted router early

### Public API Anti-Abuse (Rate Limiting + Honeypot)

**Verification (PROD)**: ✅ Verified 2026-01-06 (commit f85efb9, smoke rc=0, observed 429 responses)

**Coverage**: All /api/v1/public/* endpoints

**Protection Mechanisms**:

1. **IP-Based Rate Limiting**:
   - Ping endpoint: 60 requests per 10-second window (per IP)
   - Availability endpoint: 30 requests per 10-second window (per IP + property_id when available)
   - Booking requests: 10 requests per 10-second window (per IP + property_id when available)
   - Redis-backed with atomic INCR+EXPIRE operations
   - Fail-open design: allows requests if Redis unavailable (logs warning)

2. **Honeypot Field** (Booking Requests Only):
   - Field name: `website` (configurable via PUBLIC_HONEYPOT_FIELD)
   - Behavior: If field is present and non-empty, request blocked with 429
   - Does not reveal honeypot reason in response
   - OpenAPI documents field as "Anti-bot honeypot field (must be empty)"

**Response Headers** (on success):
- `X-RateLimit-Limit`: Max requests allowed in window
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Window`: Window duration in seconds

**Response on Limit Exceeded**:
- Status: 429 Too Many Requests
- Detail: "Too many requests. Please try again later."
- Header: `Retry-After` (seconds until window resets)

**Environment Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `PUBLIC_ANTI_ABUSE_ENABLED` | `true` | Master toggle for anti-abuse protection |
| `PUBLIC_RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `PUBLIC_RATE_LIMIT_WINDOW_SECONDS` | `10` | Rate limit window duration |
| `PUBLIC_RATE_LIMIT_PING_MAX` | `60` | Max ping requests per window |
| `PUBLIC_RATE_LIMIT_AVAIL_MAX` | `30` | Max availability requests per window |
| `PUBLIC_RATE_LIMIT_BOOKING_MAX` | `10` | Max booking requests per window |
| `PUBLIC_RATE_LIMIT_REDIS_URL` | (auto) | Redis URL (defaults to REDIS_URL or CELERY_BROKER_URL) |
| `PUBLIC_RATE_LIMIT_PREFIX` | `public_rl` | Redis key prefix |
| `PUBLIC_HONEYPOT_FIELD` | `website` | Honeypot field name |

**Testing**:

The public booking smoke script (`pms_direct_booking_public_smoke.sh`) includes a rate limit test:
- Sends burst of ping requests (limit + 5 or 80 if header not present)
- Verifies at least one 429 response observed
- Honors Retry-After header if already rate-limited at start
- PASS condition: Test runs without fatal errors (informational test)

**Logging**:

Rate limit decisions logged with structured context:
- `decision`: allowed / limited / honeypot
- `ip`: Client IP address
- `path`: Request path
- `method`: HTTP method
- `bucket`: Rate limit bucket (ping/availability/booking_requests)
- `property_id`: Property ID if available
- `user_agent`: User-Agent header
- `retry_after`: Seconds until limit resets (on 429 only)

**Troubleshooting**:

**Problem**: All public requests return 429

**Solution**:
1. Check if rate limits configured too low for your traffic
2. Verify Redis is operational: `redis-cli -u $REDIS_URL PING`
3. Increase limits via environment variables (e.g., `PUBLIC_RATE_LIMIT_PING_MAX=120`)
4. Check if multiple IPs sharing same public IP (NAT/proxy) - consider property-scoped limits

**Problem**: Rate limiting not working (no 429s observed)

**Solution**:
1. Check `PUBLIC_RATE_LIMIT_ENABLED=true` in environment
2. Verify Redis connection: check app logs for "Rate limit Redis pool created"
3. If Redis unavailable, limiter fails open (allows all requests with warning)
4. Test manually: `for i in {1..70}; do curl -s -o /dev/null -w "%{http_code}\n" https://api.example.com/api/v1/public/ping; done | grep 429`

**Problem**: Legitimate requests blocked by honeypot

**Solution**:
1. Ensure frontend does NOT populate `website` field (or configured honeypot field)
2. Check POST payload: field should be absent or empty string
3. Verify field name matches `PUBLIC_HONEYPOT_FIELD` setting

### Related Documentation

- [Public Booking Smoke Script](../scripts/README.md#public-direct-booking-smoke-test-pms_direct_booking_public_smokesh) - Full script documentation
- [Public Booking Router](../app/api/routes/public_booking.py) - API implementation
- [Project Status](../docs/project_status.md) - Implementation status

### P1 Booking Request Review Workflow

**Scope**: Internal review workflow for public booking requests (submitted → under_review → approved/declined)

**Architecture Note**: Booking requests are stored directly in the `bookings` table (booking_request_id == bookings.id). The P1 workflow operates on existing bookings table columns:
- `status`: requested → under_review → confirmed OR cancelled
- `confirmed_at`: Set when approved (maps to API field `approved_at`)
- `cancelled_at`, `cancelled_by`, `cancellation_reason`: Set when declined (map to API fields `reviewed_at`, `reviewed_by`, `decline_reason`)
- `internal_notes`: Append-only log of review actions with timestamps
- No separate workflow-specific columns required (uses existing bookings schema)

**Status Mapping (API ↔ DB)**: The API exposes `under_review` status for P1 workflow semantics, but the database stores this as `inquiry` for backward compatibility with existing PROD schema constraints. The mapping layer transparently converts:
- API `under_review` ↔ DB `inquiry`
- All other statuses (requested, confirmed, cancelled) pass through unchanged
- Clients always see API status `under_review` in responses, never `inquiry`

**Endpoints** (authenticated, requires manager/admin role):

1. **List Booking Requests**:
   - `GET /api/v1/booking-requests?status=requested&limit=50&offset=0`
   - Filter by status: requested, under_review, confirmed, cancelled
   - Returns paginated list with confirmation/cancellation timestamps

2. **Get Booking Request Detail**:
   - `GET /api/v1/booking-requests/{id}`
   - Returns full booking request details including internal notes, decline reason (cancellation_reason)

3. **Review Booking Request**:
   - `POST /api/v1/booking-requests/{id}/review`
   - Transitions: requested → under_review, under_review → under_review (update note)
   - Body: `{"internal_note": "optional note"}`
   - Sets: status=under_review, internal_notes (appends timestamped note)

4. **Approve Booking Request**:
   - `POST /api/v1/booking-requests/{id}/approve`
   - Transitions: requested/under_review → confirmed
   - Body: `{"internal_note": "optional note"}`
   - Sets: status=confirmed, confirmed_at, cancelled_by (as actor field), internal_notes
   - Idempotent: re-approving returns 200 with existing booking_id

5. **Decline Booking Request**:
   - `POST /api/v1/booking-requests/{id}/decline`
   - Transitions: requested/under_review → cancelled
   - Body: `{"decline_reason": "required reason", "internal_note": "optional note"}`
   - Sets: status=cancelled, cancelled_at, cancelled_by (as actor field), cancellation_reason, internal_notes
   - Idempotent: re-declining returns 200 with existing state

**Status Lifecycle**:
```
requested → under_review → confirmed (approved)
         ↘               ↘ cancelled (declined)
```

**Error Codes**:
- **401 Unauthorized**: Missing or invalid JWT token
- **403 Forbidden**: User lacks manager/admin role or agency access
- **404 Not Found**: Booking request not found or deleted
- **409 Conflict**: Invalid status transition (e.g., cannot approve cancelled request)
- **422 Validation**: Missing required fields (e.g., decline_reason)
- **500 Internal Server Error**: Database error (check logs for column availability issues)

**Troubleshooting**:

**Problem**: Cannot approve booking request (409 Conflict - Invalid Transition)

**Solution**:
1. Check current status: `GET /api/v1/booking-requests/{id}` → verify status is requested/under_review
2. If status=cancelled: cannot approve cancelled requests (invalid transition)
3. If status=confirmed: already approved (idempotent, returns 200 with booking_id)

---

**Problem**: Approve returns 409 Conflict - Booking Overlap (no_double_bookings)

**Cause**: The requested date range overlaps with an existing confirmed booking for the same property. The database exclusion constraint `no_double_bookings` prevents double bookings.

**Solution**:
1. Check for existing bookings in the date range:
   ```sql
   SELECT id, check_in, check_out, status
   FROM bookings
   WHERE property_id = '<property_id>'
   AND daterange(check_in, check_out, '[)') && daterange('<check_in>', '<check_out>', '[)')
   AND status = 'confirmed'
   AND deleted_at IS NULL;
   ```
2. Options:
   - Choose a different date range (modify the booking request before approving)
   - Cancel the conflicting booking first (if appropriate)
   - Decline this booking request with appropriate reason

**Related**: The smoke test (`pms_public_booking_requests_workflow_smoke.sh`) automatically finds available windows using `/api/v1/public/availability` with configurable `MAX_WINDOW_TRIES` and `SHIFT_DAYS` to avoid this issue.

---

**Problem**: Decline fails with 422 Validation

**Solution**:
1. Ensure `decline_reason` is provided and non-empty in request body
2. Example: `{"decline_reason": "Property unavailable", "internal_note": "..."}`

**Problem**: Endpoints return 500 Internal Server Error

**Solution**:
1. Check backend logs for asyncpg errors (column not found, relation not found)
2. Verify bookings table has required columns: confirmed_at, cancelled_at, cancelled_by, cancellation_reason, internal_notes
3. P1 workflow uses EXISTING bookings columns (no separate workflow table/columns required)
4. If columns missing: check that Phase 17B migration was applied (initial bookings schema)

**Problem**: All endpoints return 404 Not Found (router not mounted)

**Solution**:
1. Verify router is mounted: Check `/openapi.json` for `/api/v1/booking-requests` paths
2. If missing from OpenAPI: router not registered in module system
3. Verify: `backend/app/modules/booking_requests.py` exists and is imported
4. Verify: `backend/app/modules/bootstrap.py` imports booking_requests module
5. Check logs at startup for "Booking Requests module not available" warnings
6. If MODULES_ENABLED=false in production, verify fallback router mounting in main.py

**Smoke Test**:
```bash
# Run workflow smoke test (requires JWT_TOKEN with manager/admin role)
HOST=https://api.example.com \
JWT_TOKEN=<token> \
./backend/scripts/pms_public_booking_requests_workflow_smoke.sh
```

**Related Documentation**:
- [Booking Request Workflow Smoke Script](../scripts/README.md#p1-booking-request-workflow-smoke-test) - Full script documentation
- [Booking Requests API](../app/api/routes/booking_requests.py) - API implementation
- [Migration 20260106120000](../../supabase/migrations/20260106120000_add_booking_request_workflow.sql) - Database schema

---

### P2 Pricing v1 Foundation

**Scope**: Rate plans, seasonal pricing overrides, and quote calculation for booking requests

**Architecture Note**: Pricing is stored in two tables:
- `rate_plans`: Base pricing configuration for properties (agency-wide or property-specific)
- `rate_plan_seasons`: Date-range specific pricing overrides (seasonal rates, min stay)

All pricing fields are nullable/optional for gradual adoption. If property_id is NULL, the rate plan applies agency-wide.

**Currency Fallback Hierarchy**: rate_plan.currency → property.currency → agency.currency → EUR

**Database Schema**:

1. **rate_plans**:
   - `id`: UUID primary key
   - `agency_id`: UUID (required, FK to agencies)
   - `property_id`: UUID (nullable, FK to properties, NULL = agency-wide)
   - `name`: TEXT (required, rate plan display name)
   - `currency`: TEXT (nullable, ISO 4217, fallback to property/agency)
   - `base_nightly_cents`: INT (nullable, base nightly rate in cents)
   - `min_stay_nights`: INT (nullable, minimum stay requirement)
   - `max_stay_nights`: INT (nullable, maximum stay allowed)
   - `active`: BOOLEAN (default true)
   - Constraints: FK to agencies (CASCADE), FK to properties (CASCADE)

2. **rate_plan_seasons**:
   - `id`: UUID primary key
   - `rate_plan_id`: UUID (required, FK to rate_plans)
   - `date_from`: DATE (required, season start inclusive)
   - `date_to`: DATE (required, season end exclusive)
   - `nightly_cents`: INT (nullable, override nightly rate)
   - `min_stay_nights`: INT (nullable, override min stay)
   - `active`: BOOLEAN (default true)
   - Constraints: FK to rate_plans (CASCADE), CHECK (date_from < date_to)

**Endpoints**:

1. **List Rate Plans** (manager/admin):
   - `GET /api/v1/pricing/rate-plans?property_id={uuid}`
   - Returns all rate plans for agency with seasonal overrides
   - Optional filter by property_id

2. **Create Rate Plan** (manager/admin):
   - `POST /api/v1/pricing/rate-plans`
   - Body: `{"property_id": "uuid|null", "name": "...", "currency": "USD", "base_nightly_cents": 15000, "min_stay_nights": 1, "active": true, "seasons": [...]}`
   - Creates rate plan with optional seasonal overrides
   - Returns 201 with created rate plan including all seasons

3. **Calculate Quote** (authenticated):
   - `POST /api/v1/pricing/quote`
   - Body: `{"property_id": "uuid", "check_in": "2026-01-10", "check_out": "2026-01-13"}`
   - Calculates pricing for date range using active rate plan
   - Seasonal override takes precedence over base rate if date range overlaps
   - Returns quote with nightly_cents, total_cents, nights, currency, rate_plan details
   - If no pricing configured: returns quote with message and null amounts

**Quote Calculation Logic**:
1. Find active rate plan for property (property-specific first, then agency-wide)
2. Check for seasonal override that applies to check_in date
3. Use seasonal override nightly_cents if found, otherwise base_nightly_cents
4. Calculate: total_cents = nightly_cents × nights
5. Return quote with all pricing details

**Error Codes**:
- **400 Bad Request**: Invalid dates (check_out must be after check_in)
- **401 Unauthorized**: Missing or invalid JWT token
- **403 Forbidden**: User lacks required role or agency access
- **404 Not Found**: Property not found in agency
- **422 Validation**: Invalid input (e.g., negative nightly_cents, invalid currency)
- **500 Internal Server Error**: Database error

**Troubleshooting**:

**Problem**: Quote returns null pricing (nightly_cents=null, total_cents=null)

**Solution**:
1. Check if rate plan exists: `GET /api/v1/pricing/rate-plans?property_id={uuid}`
2. If no rate plans: Create one with `POST /api/v1/pricing/rate-plans`
3. If rate plan exists but has null base_nightly_cents: No seasonal override found for dates
4. Add seasonal override or set base_nightly_cents in rate plan

---

**Problem**: Quote uses wrong rate (expected seasonal rate, got base rate)

**Solution**:
1. Check seasonal override date ranges: `GET /api/v1/pricing/rate-plans`
2. Verify check_in date falls within season date_from (inclusive) to date_to (exclusive)
3. Verify seasonal override has active=true and nightly_cents is not null
4. Season selection uses check_in date only (not check_out)

---

**Problem**: Quote uses wrong rate plan (expected newest plan, got older plan)

**Symptoms**:
- Multiple active rate plans exist for property
- Quote returns rate_plan_id that doesn't match most recently created/updated plan
- Smoke test fails with "Rate plan ID mismatch"
- Nondeterministic behavior: sometimes gets new plan, sometimes old plan

**Root Cause**:
- Before fix (commit <43c122a): Quote selection had no ORDER BY for updated_at/created_at
- PostgreSQL returned arbitrary row when multiple plans matched filter
- Race condition: which plan gets selected depended on database internal ordering

**Solution (Fixed)**:
Quote endpoint now uses deterministic ordering:
```sql
ORDER BY property_id NULLS LAST,        -- Prefer property-specific over agency-wide
         updated_at DESC NULLS LAST,    -- Then newest updated
         created_at DESC NULLS LAST,    -- Then newest created
         id DESC                        -- Final tiebreaker
LIMIT 1
```

List endpoint also uses same ordering (without property_id preference since already filtered):
```sql
ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id DESC
```

**Expected Behavior**:
- Quote always selects the most recently updated/created active rate plan
- Property-specific plans always preferred over agency-wide
- First rate plan in list matches the one used for quotes (consistent ordering)

**Verification**:
```bash
# Create new rate plan
curl -X POST "$HOST/api/v1/pricing/rate-plans" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "x-agency-id: $AGENCY_ID" \
  -H "Content-Type: application/json" \
  -d '{"property_id": "...", "name": "New Plan", ...}' | jq '.id'
# → new_plan_id

# Get quote - should use new_plan_id
curl -X POST "$HOST/api/v1/pricing/quote" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "x-agency-id: $AGENCY_ID" \
  -H "Content-Type: application/json" \
  -d '{"property_id": "...", "check_in": "...", "check_out": "..."}' | jq '.rate_plan_id'
# → should match new_plan_id
```

---

**Problem**: Create rate plan fails with 404 Property Not Found

**Solution**:
1. Verify property_id exists in agency: `GET /api/v1/properties`
2. Verify property belongs to current agency (agency scoping enforced)
3. For agency-wide rate plan: set property_id to null in request body

---

**Problem**: Create rate plan returns 500 Internal Server Error - Pydantic ValidationError on created_at/updated_at

**Symptoms**:
- POST /api/v1/pricing/rate-plans creates database row successfully
- Logs show: "Created rate plan: id=9c15fd7e-..."
- Then 500 error with ValidationError: "Input should be a valid string, got datetime.datetime(...)"
- Stack trace points to RatePlanResponse serialization (pricing.py line ~209)
- Same issue affects GET /api/v1/pricing/rate-plans if returned

**Root Cause**:
- Database returns created_at/updated_at as datetime.datetime objects
- Pydantic schema (RatePlanResponse, RatePlanSeasonResponse) typed these as `str`
- Validation fails when trying to serialize response with datetime objects

**Solution**:
Schema was fixed to use `datetime` type instead of `str`:
```python
# backend/app/schemas/pricing.py
from datetime import date, datetime  # Added datetime import

class RatePlanResponse(BaseModel):
    created_at: datetime  # Changed from str
    updated_at: datetime  # Changed from str
```

Pydantic v2 automatically serializes datetime to ISO 8601 strings in JSON responses.

**Verification**:
```bash
# Create rate plan should return 201 (not 500)
curl -X POST "$HOST/api/v1/pricing/rate-plans" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "x-agency-id: $AGENCY_ID" \
  -H "Content-Type: application/json" \
  -d '{"property_id": "...", "name": "Test", "currency": "USD", "base_nightly_cents": 15000, "active": true}' \
  | jq '.created_at'  # Should show ISO string like "2026-01-06T12:34:56.789Z"

# Smoke script should pass
HOST=$HOST JWT_TOKEN=$JWT_TOKEN AGENCY_ID=$AGENCY_ID ./backend/scripts/pms_pricing_quote_smoke.sh
```

**Prevention**:
- Always match Pydantic schema types to actual database column types
- Use `datetime` for TIMESTAMP columns, not `str`
- Let Pydantic handle serialization (no manual .isoformat() needed)

---

**Problem**: Smoke script fails with "Cannot index object with number" or JSONDecodeError during property auto-pick

**Solution**:
1. Properties list endpoint returns paginated response: `{items: [...], total: N, ...}`
2. Script auto-pick uses: `GET /api/v1/properties/?limit=1&offset=0` → parses `.items[0].id`
3. If you see 307 redirects: Script already uses `curl -L` to follow redirects automatically
4. If no properties exist: Create one first or export `PROPERTY_ID=<uuid>` and rerun (script exits with rc=2)
5. Verify API is reachable: `curl -L "$HOST/api/v1/properties/?limit=1" -H "Authorization: Bearer <token>"`

---

**Problem**: Endpoints return 404 Not Found (router not mounted)

**Solution**:
1. Check ACTUAL mounted routes (authoritative): `GET /api/v1/ops/modules` → verify:
   - `mounted_has_pricing: true`
   - `pricing_paths: ["/api/v1/pricing/rate-plans", "/api/v1/pricing/quote"]`
   - `pricing` appears in `modules` list with prefixes `["/api/v1/pricing"]`
2. If `mounted_has_pricing: false`:
   - Check if pricing module is in registry modules list
   - If missing from registry: pricing module failed to load/register
     - Root cause: `backend/app/api/routes/__init__.py` must import pricing
     - Verify: `from . import ... pricing` exists in routes/__init__.py
     - Check logs for "Pricing module not available" ImportError warnings
   - If in registry but not mounted: check MODULES_ENABLED setting
3. Check OpenAPI schema: `GET /openapi.json` → verify `/api/v1/pricing/*` paths exist
4. Check deploy commit: `GET /api/v1/ops/version` → verify `source_commit` matches expected SHA
5. If still failing: restart app (stale process or module import cached failure)

**Smoke Test**:
```bash
# Run pricing smoke test (requires JWT_TOKEN with manager/admin role)
HOST=https://api.example.com \
JWT_TOKEN=<token> \
./backend/scripts/pms_pricing_quote_smoke.sh
```

**Related Documentation**:
- [Pricing Quote Smoke Script](../scripts/README.md#p2-pricing-quote-smoke-test) - Full script documentation
- [Pricing API](../app/api/routes/pricing.py) - API implementation
- [Pricing Schemas](../app/schemas/pricing.py) - Pydantic models
- [Migration 20260106150000](../../supabase/migrations/20260106150000_add_pricing_v1.sql) - Database schema

---

---

**Problem**: GET /api/v1/ops/modules doesn't show channel-connections routes (hyphenated prefixes missing)

**Symptoms**:
- `/api/v1/ops/modules` returns `mounted_prefixes` list that's missing `/api/v1/channel-connections`
- `mounted_has_channel_connections: false` even though routes exist in OpenAPI schema
- Hyphenated path segments (e.g., `channel-connections`, `rate-plans`) not detected in prefix extraction
- Module registry shows routes but actual mounted paths are incomplete

**Root Cause**:
- Old prefix extraction used word-boundary regex `\w+` which doesn't match hyphens
- Pattern `^(/api/v1/\w+)` only matched alphanumeric + underscore (not hyphens)
- Routes like `/api/v1/channel-connections/*` were skipped during inspection
- Result: ops/modules output was incomplete and not authoritative

**Solution**:
Fixed prefix extraction to use robust regex: `^(/api/v1/[^/]+)`
- Matches any character except forward slash (includes hyphens, underscores, alphanumeric)
- Extracts first three path segments: `/api/v1/<prefix>`
- Handles hyphenated prefixes: `channel-connections`, `booking-requests`, etc.
- Deduplicates paths automatically (uses set internally)

**New Fields (added 2026-01-07)**:
- `mounted_has_channel_connections: bool` - True if `/api/v1/channel-connections/*` routes exist
- `channel_connections_paths: list[str]` - All channel-connections paths (sorted, deduplicated)
- `pricing_paths: list[str]` - Now deduplicated (previously could contain duplicates)

**Verification**:
```bash
# Check channel-connections detection
curl https://api.example.com/api/v1/ops/modules | jq '{
  mounted_has_channel_connections,
  channel_connections_paths,
  mounted_prefixes: .mounted_prefixes | map(select(contains("channel")))
}'

# Expected output (if channel-connections routes exist):
# {
#   "mounted_has_channel_connections": true,
#   "channel_connections_paths": [
#     "/api/v1/channel-connections/sync",
#     "/api/v1/channel-connections/availability",
#     "/api/v1/channel-connections/pricing"
#   ],
#   "mounted_prefixes": ["/api/v1/channel-connections"]
# }
```

**Use Cases**:
1. **Deploy Verification**: Confirm channel-connections module is mounted after deploy
2. **Troubleshooting 404s**: Check if routes are actually mounted vs just registered
3. **Module Registry vs Reality**: Compare registry metadata with actual app.routes
4. **Smoke Tests**: Verify specific route families exist before running tests

**Related Helpers** (internal, tested):
- `extract_mounted_prefixes(routes)` - Extract unique API prefixes with regex `^(/api/v1/[^/]+)`
- `extract_paths_by_prefix(routes, prefix)` - Get all paths matching prefix (deduplicated, sorted)
- Unit tests: `tests/unit/test_ops_helpers.py`

**Important Notes**:
- `/ops/modules` is **authoritative** - reads from `request.app.routes` (not registry)
- No database calls, no authentication required (safe metadata only)
- Response reflects actual FastAPI routing table at request time
- If `modules_enabled=false` but routes exist: routes were mounted directly (bypass module system)
- Use this endpoint for ops verification, not `/openapi.json` (OpenAPI may lag behind reality)

---

### P2 Pricing v1 Extension (Fees and Taxes)

**Scope**: Comprehensive pricing breakdown with fees and taxes for booking quotes

**Architecture Note**: Extends P2 Foundation with two additional tables:
- `pricing_fees`: Fixed or percentage-based fees added to booking cost (cleaning, service, etc.)
- `pricing_taxes`: Percentage taxes applied to taxable amounts (subtotal + taxable fees)

All fields nullable/optional for gradual adoption. If property_id is NULL, the fee/tax applies agency-wide.

**Database Schema**:

1. **pricing_fees**:
   - `id`: UUID primary key
   - `agency_id`: UUID (required, FK to agencies)
   - `property_id`: UUID (nullable, FK to properties, NULL = agency-wide)
   - `name`: TEXT (required, fee display name)
   - `type`: TEXT (required, one of: per_stay, per_night, per_person, percent)
   - `value_cents`: INT (nullable, value in cents for fixed fees)
   - `value_percent`: NUMERIC(5,2) (nullable, percentage for percent type)
   - `taxable`: BOOLEAN (default false, whether fee is included in tax calculation)
   - `active`: BOOLEAN (default true)
   - Constraints: FK to agencies (CASCADE), FK to properties (CASCADE)
   - Validation: percent type requires value_percent, others require value_cents

2. **pricing_taxes**:
   - `id`: UUID primary key
   - `agency_id`: UUID (required, FK to agencies)
   - `property_id`: UUID (nullable, FK to properties, NULL = agency-wide)
   - `name`: TEXT (required, tax display name)
   - `percent`: NUMERIC(5,2) (required, tax rate percentage 0-100)
   - `active`: BOOLEAN (default true)
   - Constraints: FK to agencies (CASCADE), FK to properties (CASCADE)

**Endpoints**:

1. **List Fees** (manager/admin):
   - `GET /api/v1/pricing/fees?property_id={uuid}&active={bool}&limit={int}&offset={int}`
   - Returns all fees for agency with optional filters
   - Pagination support with limit (default 100) and offset (default 0)

2. **Create Fee** (manager/admin):
   - `POST /api/v1/pricing/fees`
   - Body: `{"property_id": "uuid|null", "name": "Cleaning Fee", "type": "per_stay", "value_cents": 5000, "taxable": true, "active": true}`
   - Type validation: percent → value_percent required; others → value_cents required
   - Returns 201 with created fee

3. **List Taxes** (manager/admin):
   - `GET /api/v1/pricing/taxes?property_id={uuid}&active={bool}&limit={int}&offset={int}`
   - Returns all taxes for agency with optional filters
   - Pagination support with limit (default 100) and offset (default 0)

4. **Create Tax** (manager/admin):
   - `POST /api/v1/pricing/taxes`
   - Body: `{"property_id": "uuid|null", "name": "Sales Tax", "percent": 7.5, "active": true}`
   - Returns 201 with created tax

5. **Calculate Quote** (authenticated) - EXTENDED:
   - `POST /api/v1/pricing/quote`
   - Body: `{"property_id": "uuid", "check_in": "2026-01-10", "check_out": "2026-01-13", "adults": 2, "children": 1}`
   - Calculates comprehensive pricing breakdown including fees and taxes
   - Returns QuoteResponse with:
     - `nightly_cents`: Nightly rate (unchanged from Foundation)
     - `subtotal_cents`: Accommodation subtotal (nightly_cents × nights)
     - `fees`: Array of FeeLineItem (name, type, amount_cents, taxable)
     - `fees_total_cents`: Sum of all fees
     - `taxable_amount_cents`: Subtotal + taxable fees
     - `taxes`: Array of TaxLineItem (name, percent, amount_cents)
     - `taxes_total_cents`: Sum of all taxes
     - `total_cents`: Grand total (subtotal + fees + taxes)
   - Backward compatible: if no fees/taxes configured, returns empty arrays and totals=0

**Quote Calculation Logic (Extended)**:
1. Find active rate plan for property (unchanged from Foundation)
2. Calculate accommodation subtotal: `subtotal_cents = nightly_cents × nights`
3. Fetch active fees for property (property-specific first, then agency-wide)
4. Calculate each fee:
   - `per_stay`: fee.value_cents (once per booking)
   - `per_night`: fee.value_cents × nights
   - `per_person`: fee.value_cents × (adults + children) × nights
   - `percent`: (subtotal_cents × fee.value_percent) / 100
5. Calculate taxable amount: `taxable_amount_cents = subtotal_cents + sum(taxable_fees)`
6. Fetch active taxes for property (property-specific first, then agency-wide)
7. Calculate each tax: `tax_amount_cents = (taxable_amount_cents × tax.percent) / 100`
8. Calculate grand total: `total_cents = subtotal_cents + fees_total_cents + taxes_total_cents`

**Fee Type Examples**:
- **per_stay**: Cleaning fee charged once per booking (e.g., $50.00 = 5000 cents)
- **per_night**: Resort fee charged per night (e.g., $20.00/night = 2000 cents)
- **per_person**: Linen fee charged per person per night (e.g., $5.00/person/night = 500 cents)
- **percent**: Service fee as percentage of subtotal (e.g., 10% = 10.0)

**Error Codes**:
- **400 Bad Request**: Invalid fee/tax creation (e.g., percent type without value_percent)
- **401 Unauthorized**: Missing or invalid JWT token
- **403 Forbidden**: User lacks manager/admin role
- **404 Not Found**: Property not found in agency
- **422 Validation**: Invalid input (e.g., negative value_cents, percent > 100)
- **500 Internal Server Error**: Database error

**Troubleshooting**:

**Problem**: Quote returns empty fees/taxes arrays (fees=[], taxes=[])

**Solution**:
1. Check if fees exist: `GET /api/v1/pricing/fees?property_id={uuid}`
2. Check if taxes exist: `GET /api/v1/pricing/taxes?property_id={uuid}`
3. If no fees/taxes found: This is expected behavior, quote returns empty arrays
4. If fees/taxes exist but not in quote: Check active=true and property_id matches
5. For agency-wide fees/taxes: Create with property_id=null in request body

---

**Problem**: Fee calculation incorrect (expected $50, got different amount)

**Solution**:
1. Verify fee type matches expected calculation:
   - per_stay: Should be constant regardless of nights/guests
   - per_night: Should multiply by nights
   - per_person: Should multiply by (adults + children) × nights
   - percent: Should calculate as percentage of subtotal_cents
2. Check fee value_cents or value_percent in database
3. Verify fee is active=true and property_id matches quote property

---

**Problem**: Tax calculation incorrect (expected 7.5% of subtotal, got different amount)

**Solution**:
1. Taxes are calculated on taxable_amount_cents = subtotal + taxable fees (NOT just subtotal)
2. Check which fees have taxable=true in database
3. Formula: tax_amount = (subtotal + sum(taxable_fees)) × tax_percent / 100
4. Verify tax percent value in database (stored as NUMERIC, e.g., 7.5 for 7.5%)
5. Integer rounding: Tax calculation uses int() truncation, not round()

---

**Problem**: Create fee fails with 400 "value_percent is required for percent type fees"

**Solution**:
1. For type=percent: Must provide value_percent, value_cents must be null
2. For type=per_stay/per_night/per_person: Must provide value_cents, value_percent must be null
3. Check request body matches type requirements
4. Example percent fee: `{"type": "percent", "value_percent": 10.0, "value_cents": null}`
5. Example fixed fee: `{"type": "per_stay", "value_cents": 5000, "value_percent": null}`

---

**Problem**: Quote total doesn't match expected calculation

**Symptoms**:
- Frontend shows different total than backend quote
- Manual calculation: subtotal + fees + taxes ≠ total_cents
- Smoke test fails with "Grand total mismatch"

**Root Cause**:
- Floating point precision issues in fee/tax percentage calculations
- Client-side calculation differs from server-side int() truncation
- Missing taxable fees in tax base calculation

**Solution**:
1. Backend uses integer arithmetic with int() truncation (not round())
2. Always use backend total_cents as source of truth
3. Verify calculation manually:
   ```bash
   subtotal_cents = nightly_cents × nights
   fees_total_cents = sum(all fee amounts)
   taxable_amount_cents = subtotal_cents + sum(taxable fee amounts)
   taxes_total_cents = sum((taxable_amount_cents × tax.percent / 100) for each tax)
   total_cents = subtotal_cents + fees_total_cents + taxes_total_cents
   ```
4. Example: $150/night × 3 nights = $450 subtotal, $50 cleaning (taxable), $37.50 tax (7.5%) = $537.50 total
   - subtotal_cents = 15000 × 3 = 45000
   - fees_total_cents = 5000
   - taxable_amount_cents = 45000 + 5000 = 50000
   - taxes_total_cents = int(50000 × 7.5 / 100) = 3750
   - total_cents = 45000 + 5000 + 3750 = 53750

---

### Smoke Testing P2 Extension

**Script**: `backend/scripts/pms_pricing_quote_smoke.sh`

**Tests**:
1. Create rate plan with base pricing
2. Create cleaning fee (per_stay, taxable)
3. Create sales tax (7.5%)
4. Calculate quote and verify comprehensive breakdown
5. Verify: subtotal = nightly × nights
6. Verify: fees_total = cleaning_fee
7. Verify: taxable_amount = subtotal + cleaning_fee
8. Verify: taxes_total = taxable_amount × 7.5%
9. Verify: total = subtotal + fees + taxes

**Usage**:
```bash
# HOST-SERVER-TERMINAL
HOST="https://api.fewo.kolibri-visions.de" \
JWT_TOKEN="<manager-or-admin-token>" \
AGENCY_ID="<uuid>" \
./backend/scripts/pms_pricing_quote_smoke.sh
```

**Expected Output**:
```
✅ Created rate plan: <uuid>
✅ Created fee: <uuid> (Cleaning Fee: 5000 cents)
✅ Created tax: <uuid> (Sales Tax: 7.5%)
✅ Quote calculated:
  Subtotal: 45000 cents
  Fees Total: 5000 cents
  Taxable Amount: 50000 cents
  Taxes Total: 3750 cents
  Grand Total: 53750 cents
✅ Quote calculation verified (subtotal + fees + taxes = total)
✅ All P2 Pricing + Extension smoke tests passed! 🎉
```

---

## P2 Pricing Management UI

**Overview:** Admin UI for managing fees and taxes with create/list/toggle capabilities.

**Purpose:** Provide property managers and admins a web interface to configure pricing fees (cleaning, service, etc.) and taxes without backend access.

**UI Routes:**
- `/pricing` - Main pricing management page with fees/taxes tabs

**API Endpoints Used:**
- `GET /api/v1/properties` - List properties (for selector)
- `GET /api/v1/pricing/fees?property_id=&active=&limit=&offset=` - List fees
- `POST /api/v1/pricing/fees` - Create fee
- `PATCH /api/v1/pricing/fees/{id}` - Update fee (toggle active, edit values)
- `GET /api/v1/pricing/taxes?property_id=&active=&limit=&offset=` - List taxes
- `POST /api/v1/pricing/taxes` - Create tax
- `PATCH /api/v1/pricing/taxes/{id}` - Update tax (toggle active, edit values)
- `POST /api/v1/pricing/quote` - Calculate quote with fees/taxes (optional test)

**Database Tables:**
- `pricing_fees` - Property-specific or agency-wide fees (per_stay, per_night, per_person, percent types)
- `pricing_taxes` - Property-specific or agency-wide taxes (percent type)
- Migration: `20260104200000_add_pricing_fees_and_taxes.sql`

**Features:**
1. **Property Selector**: Auto-picks first property, allows manual selection
2. **Tabs**: Separate views for Fees and Taxes
3. **List View**: Paginated list with name, type, value, taxable, scope, active status
4. **Create Forms**:
   - Fee: name, type (per_stay/per_night/per_person/percent), value (cents or percent), taxable checkbox, scope (property/agency)
   - Tax: name, percent, scope (property/agency)
5. **Toggle Active**: Click status badge to toggle active=true/false using PATCH
6. **Validation**: Client-side validation for required fields, type-specific value fields
7. **Toast Notifications**: Success/error messages for CRUD operations

**Verification Commands:**

```bash
# [HOST-SERVER-TERMINAL] Pull latest code
cd /data/repos/pms-webapp
git fetch origin main && git reset --hard origin/main

# [HOST-SERVER-TERMINAL] Optional: Verify deploy after Coolify redeploy
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
./backend/scripts/pms_verify_deploy.sh

# [HOST-SERVER-TERMINAL] Run pricing management UI smoke test
export HOST="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<<<manager/admin JWT>>>"
# Optional:
# export PROPERTY_ID="23dd8fda-59ae-4b2f-8489-7a90f5d46c66"
# export AGENCY_ID="ffd0123a-10b6-40cd-8ad5-66eee9757ab7"
./backend/scripts/pms_pricing_management_ui_smoke.sh
echo "rc=$?"

# Expected output: All 8 tests pass, rc=0
```

**Common Issues:**

### PATCH Endpoints Return 404

**Symptom:** UI shows error when toggling active status: "Failed to update fee/tax".

**Cause:** PATCH endpoints not deployed yet (added in this release).

**How to Debug:**
```bash
# Check if PATCH endpoints exist in OpenAPI schema
curl -sS "$HOST/openapi.json" | jq '.paths["/api/v1/pricing/fees/{fee_id}"]'
curl -sS "$HOST/openapi.json" | jq '.paths["/api/v1/pricing/taxes/{tax_id}"]'

# Should return method "patch" with parameters
```

**Solution:** Ensure latest backend deployed with commit containing PATCH endpoints.

### PATCH Toggle Returns 500 Database Error

**Symptom:** Smoke test Test 5/6 fails with 500 Database error when calling PATCH `/api/v1/pricing/fees/{id}` or `/api/v1/pricing/taxes/{id}` to toggle active status. Response: `{"detail":{"error":"internal_server_error","message":"Database error occurred","path":null}}`

**Root Cause:** Bug in dynamic UPDATE query builder in `backend/app/api/routes/pricing.py`. The code incorrectly incremented `param_count` before adding `updated_at = NOW()`, causing parameter count mismatch. PostgreSQL expects N parameters but only N-1 were provided.

**Example Flow (Buggy Code):**
```python
# When only updating active field:
param_count = 1  # for active
update_fields = ["active = $1"]
params = [False]

# Bug: Increment param_count for NOW() (which needs no param!)
param_count = 2  # WRONG
update_fields.append("updated_at = NOW()")

# Add fee_id as final param
param_count = 3  # WRONG - should be 2
params.append(fee_id)

# Query: WHERE id = $3
# Params: [False, fee_id]  # Only 2 params!
# PostgreSQL error: $3 doesn't exist
```

**How to Debug:**
```bash
# Check backend logs for asyncpg parameter errors
docker logs pms-backend --tail 100 | grep -E "pricing|Parameter|asyncpg"

# Verify pricing.py has fix (param_count should NOT increment before NOW())
grep -A 2 "updated_at = NOW()" backend/app/api/routes/pricing.py
# Expected: No param_count += 1 on line before NOW()
```

**Solution:** Fixed in commit that removed incorrect `param_count += 1` on lines 464 and 673 (for fees and taxes respectively). The `NOW()` function doesn't use a parameter, so param_count should not be incremented. Ensure backend code is updated and redeployed.

**Verification:**
```bash
# Run smoke test to verify fix
HOST="$PROD_API" JWT_TOKEN="$TOKEN" ./backend/scripts/pms_pricing_management_ui_smoke.sh
# Expected: Test 5 PASSED, Test 6 PASSED
```

### UI Shows "Failed to load fees/taxes"

**Symptom:** UI displays error toast, browser console shows 401/403/500.

**Possible Causes:**
1. JWT token expired (401)
2. User lacks manager/admin role (403)
3. Migrations not applied - pricing_fees/pricing_taxes tables missing (500)

**How to Debug:**
```bash
# Check JWT expiration
echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq '.exp'
date -r $(echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq -r '.exp')

# Check JWT role
echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq '.role'
# Should be "manager" or "admin"

# Check tables exist
psql $DATABASE_URL -c "\dt pricing_*"
# Should show: pricing_fees, pricing_taxes

# Check backend logs
docker logs pms-backend --tail 50 | grep -E "pricing|fees|taxes"
```

**Solution:**
- Refresh JWT token if expired
- Verify user has manager/admin role
- Apply migration 20260104200000 if tables missing

### Create Fee/Tax Returns Validation Error

**Symptom:** UI shows "Failed to create fee: value_percent is required for percent type fees" or similar.

**Cause:** Client-side validation mismatch with backend requirements.

**Validation Rules:**
- **Fee (percent type)**: Must have `value_percent` (0-100), `value_cents` must be null
- **Fee (other types)**: Must have `value_cents` (≥0), `value_percent` must be null
- **Tax**: Must have `percent` (0-100)
- **All**: `name` required (1-255 chars), `active` defaults to true

**Solution:** Check form inputs match type-specific requirements, ensure UI sends correct payload shape.

### Active Toggle Doesn't Filter List

**Symptom:** After toggling fee/tax to inactive, it still appears in active=true filtered list.

**Cause:** Frontend may not be re-fetching list after PATCH, or active filter query param not working.

**How to Debug:**
```bash
# Verify PATCH worked
curl -X GET "$HOST/api/v1/pricing/fees?property_id=<uuid>" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq '.[] | {id, name, active}'

# Verify active filter works
curl -X GET "$HOST/api/v1/pricing/fees?property_id=<uuid>&active=true" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq 'length'

curl -X GET "$HOST/api/v1/pricing/fees?property_id=<uuid>&active=false" \
  -H "Authorization: Bearer $JWT_TOKEN" | jq 'length'
```

**Solution:** Ensure UI re-fetches list after PATCH, verify backend active filter logic.

### No Properties Found

**Symptom:** UI shows "No properties found. Create one to get started."

**Cause:** Agency has no properties, or JWT agency_id doesn't match any properties.

**Solution:**
- Create a property first via `/properties` UI or API
- Verify JWT agency_id matches property agency_id
- Check backend logs for tenant scoping issues

**Related Documentation:**
- [Scripts README: P2 Pricing Management UI](../../scripts/README.md#p2-pricing-management-ui-smoke-test-pms_pricing_management_ui_smokesh) - Smoke script usage
- [Project Status: P2 Pricing Management UI](../project_status.md) - Implementation status

---
## OPS endpoints: Auth & Zugriff

### Current Behavior (as deployed)

**Stand:** Nach Commit `ae589e4`:

- `/api/v1/ops/version` — **PUBLIC**
- `/api/v1/ops/modules` — **PUBLIC** (aktueller Stand)
- `/api/v1/ops/audit-log` — **AUTH REQUIRED** (JWT + ggf. Role/DB)

**PROD evidence (2026-01-07):**
source_commit=ae589e4266dd62085968eab0f76419865a7c423e
started_at=2026-01-07T14:55:04.858297+00:00

### Verification Commands (Current Behavior)

```bash
# HOST-SERVER-TERMINAL
export API_BASE_URL="https://api.fewo.kolibri-visions.de"

curl -k -sS -i "$API_BASE_URL/api/v1/ops/version" | sed -n '1,25p'
# Expected: HTTP 200

curl -k -sS -i "$API_BASE_URL/api/v1/ops/modules" | sed -n '1,25p'
# Expected: HTTP 200

curl -k -sS -i -H "Authorization: Bearer " "$API_BASE_URL/api/v1/ops/modules" | sed -n '1,25p'
# Expected: HTTP 200
```

---

### Hardening (Optional / Future)

Falls `/api/v1/ops/modules` künftig geschützt werden soll (JWT-Signaturprüfung, DB-frei):

- Ohne Authorization Header → HTTP 401/403
- Mit leerem Bearer (`Authorization: Bearer `) → HTTP 401/403
- Mit gültigem JWT → HTTP 200

```bash
# HOST-SERVER-TERMINAL
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export TOKEN="eyJhbGc..."  # valid JWT token

curl -k -sS -i "$API_BASE_URL/api/v1/ops/modules" | sed -n '1,25p'
# Expected after hardening: HTTP 401 or 403

curl -k -sS -i -H "Authorization: Bearer $TOKEN" "$API_BASE_URL/api/v1/ops/modules" | sed -n '1,25p'
# Expected after hardening: HTTP 200
```

**Rationale (warum /ops/modules ggf. schützen):**
- Sensible Ops-Metadaten (Routes, Module Registry)
- Reduziert API-Exposure für Unbefugte
- JWT-Check bleibt DB-frei (funktioniert auch wenn DB down)

**Rationale (warum /ops/version PUBLIC bleibt):**
- Deploy-Verify & Monitoring ohne Auth möglich
- Keine sensiblen Inhalte, nur Meta-Infos

---

**Problem**: Create rate plan fails with "Missing agency_id in token claims"

**Symptoms**:
- POST /api/v1/pricing/rate-plans returns 403 with `{"detail":"Missing agency_id in token claims"}`
- JWT is valid (authenticated successfully, len=616, parts=3)
- Endpoints are mounted correctly (pricing routes exist in OpenAPI)
- Issue occurs when JWT doesn't have agency_id claim

**Root Cause**:
- Pricing endpoints require agency context for multi-tenancy
- JWT token doesn't include agency_id claim (depends on auth provider/Supabase setup)
- Backend needs agency_id to scope rate plans to correct tenant

**Solution**:

Strategy 1: Provide agency_id via x-agency-id header (recommended for multi-agency users)
```bash
# Create rate plan with x-agency-id header
curl -X POST "$HOST/api/v1/pricing/rate-plans" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "x-agency-id: $AGENCY_ID" \
  -H "Content-Type: application/json" \
  -d '{"property_id": "...", "name": "...", ...}'

# Smoke script with AGENCY_ID
HOST=$HOST JWT_TOKEN=$JWT_TOKEN AGENCY_ID=$AGENCY_ID ./backend/scripts/pms_pricing_quote_smoke.sh
```

Strategy 2: Use single-agency fallback (if user belongs to exactly 1 agency)
- Backend automatically resolves to user's first/only agency membership
- Queries `team_members` table for user's active memberships
- Updates `profiles.last_active_agency_id` for future requests
- No header needed if user has only 1 agency

Strategy 3: Verify JWT includes agency_id claim (auth provider configuration)
```bash
# Decode JWT to check for agency_id claim
echo "$JWT_TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq '.'
# Should include: {"sub": "...", "agency_id": "...", "role": "..."}
```

**How Tenant Resolution Works** (backend/app/api/deps.py:get_current_agency_id):
1. Check x-agency-id header (if present, validate user membership)
2. Check JWT claim agency_id (if present)
3. Query user's last_active_agency_id from profiles table
4. Fallback to first agency membership from team_members table
5. If no memberships: return 404 with actionable error

**Prevention**:
- For multi-agency environments: Always send x-agency-id header in requests
- Update smoke scripts to support AGENCY_ID env var
- Document x-agency-id requirement for multi-tenant API clients

**Verification**:
```bash
# Verify user has agency membership
psql $DATABASE_URL -c "SELECT agency_id, role FROM team_members WHERE user_id = '$USER_ID' AND is_active = true;"

# Test with x-agency-id header
curl "$HOST/api/v1/pricing/rate-plans" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "x-agency-id: $AGENCY_ID"
```

---

**Problem**: PROD restart loop - ImportError: cannot import name 'get_current_agency_id' from 'app.core.auth'

**Symptoms**:
- Backend crashes at startup with ImportError
- 502 Bad Gateway (no healthy backend pods)
- Logs show: `ImportError: cannot import name 'get_current_agency_id' from 'app.core.auth'`
- Affects imports in pricing.py: `get_current_agency_id`, `get_current_role`, `require_roles`
- MODULES_ENABLED=false doesn't help (imports happen in main.py fallback)

**Root Cause**:
- `backend/app/api/routes/pricing.py` imports auth dependencies that don't exist in auth.py
- Missing symbols: `get_current_agency_id`, `get_current_role`, `require_roles`
- auth.py has `require_role` (singular) but pricing.py imports `require_roles` (plural)
- Import happens at startup (module load time), causing immediate crash

**Solution**:
1. Add missing auth dependencies to `backend/app/core/auth.py`:
   - `get_current_agency_id`: Extract agency_id from JWT claims
   - `get_current_role`: Extract role from JWT claims
   - `require_roles`: Alias to existing `require_role` function
2. Verify `get_current_user` extracts `agency_id` and `role` from JWT payload (lines 147-148)
3. Pattern: Follow same structure as `get_current_user_id` (lines 216-240)
4. Deploy and verify: Backend boots successfully, pricing routes respond

**Prevention**:
- Always verify imported symbols exist before deploying
- Test imports in isolation: `python -c "from app.core.auth import get_current_agency_id"`
- Add import smoke tests to CI/CD pipeline

**Verification**:
```bash
# Check if backend boots (should return version info, not 502)
curl https://api.example.com/api/v1/ops/version

# Verify pricing routes mounted
curl https://api.example.com/api/v1/ops/modules | jq '.mounted_has_pricing'  # should be true
```

**Related**:
- auth.py:243-273 - get_current_agency_id implementation
- auth.py:276-306 - get_current_role implementation
- auth.py:498 - require_roles alias
- pricing.py:22 - Import statement

---


| Date | Change | Author |
|------|--------|--------|
| 2025-12-26 | Initial runbook creation (Phase 24) | System |
| 2025-12-27 | Document smoke script opt-in tests (AVAIL_BLOCK_TEST, B2B_TEST) | System |
| 2025-12-27 | Phase 30 — Inventory Final validation results (block conflict, B2B boundary, end-exclusive semantics) | System |
| 2025-12-27 | Phase 30.5 — Inventory Contract documented (single source of truth for inventory semantics, edge cases, DB guarantees) | System |
| 2025-12-27 | Phase 31 — Modular Monolith architecture documented (module system, registry, router aggregation) | System |
| 2025-12-27 | Phase 31 — MODULES_ENABLED kill-switch added (ops safety, emergency fallback to explicit router mounting) | System |
| 2025-12-27 | Phase 33B — Split api_v1 into domain modules (properties, bookings, inventory) | System |
| 2025-12-27 | Phase 34 — Updated kill-switch docs with Phase 33B context (explicit fallback router list) | System |
| 2025-12-27 | Phase 35 — Module mounting hardening (router dedupe guard, improved logging) | System |
| 2025-12-27 | Phase 36 — Channel Manager module integration with feature flag (CHANNEL_MANAGER_ENABLED, default OFF) | System |
| 2025-12-27 | Phase 36 — Redis + Celery worker setup runbook (password encoding, deployment steps, verification, troubleshooting) | System |
| 2025-12-30 | Admin UI authentication verification - Cookie-based SSR login, curl checks for /ops/* access | System |
| 2026-01-01 | Full Sync batching (batch_id) - Group 3 operations, API exposure, UI grouping, verification queries | System |
| 2026-01-06 | P1 Booking Request Workflow - Fixed to operate on bookings table using existing columns (confirmed_at, cancelled_at, cancelled_by, cancellation_reason, internal_notes). Status: cancelled instead of declined. | System |
| 2026-01-06 | P1 Status Mapping - Added API-to-DB status mapping layer: API under_review maps to DB inquiry for PROD compatibility. Prevents 500 errors from unsupported status values. | System |
| 2026-01-06 | P2 Pricing v1 Foundation - rate_plans and rate_plan_seasons tables for pricing engine. All fields nullable/optional for gradual adoption. Endpoints: GET/POST /api/v1/pricing/rate-plans, POST /api/v1/pricing/quote. | System |
| 2026-01-06 | P3a: Idempotency + Audit Log - Idempotency-Key for public booking requests (dedupe) + best-effort audit log + smoke script | System |

## P3a: Idempotency + Audit Log (Public Booking Requests)

### Overview

P3a adds idempotency support and audit logging to the public direct booking endpoint (`POST /api/v1/public/booking-requests`). These features prevent duplicate booking creation from repeated requests and provide an audit trail for public booking requests.

### Idempotency-Key Support

**How It Works**:
1. Client sends `Idempotency-Key` header with request
2. First request with key creates booking and caches response (24h TTL)
3. Replay (same key + same payload) returns cached response without DB insert
4. Conflict (same key + different payload) returns 409 with actionable error

**Behavior**:
- Same key + same request → returns cached 201 response with same booking_id
- Same key + different request → returns 409 idempotency_conflict
- No key provided → standard behavior (no idempotency check)

**Tables**:
- `idempotency_keys`: Stores key, request hash, cached response, expires after 24h
- Indexed on `(agency_id, endpoint, method, idempotency_key)` for fast lookup

---

### Audit Log

**How It Works**:
- Best-effort logging for critical actions (must not break main request)
- Captures: actor type, action, entity, IP, user-agent, metadata
- Failed audit writes are logged but do NOT fail the request

**Tables**:
- `audit_log`: Stores event records (agency_id, actor_type, action, entity_type, entity_id, request_id, idempotency_key, ip, user_agent, metadata JSONB)
- Indexed on agency_id, entity, action, and actor for query performance

**Sample Events**:
- `public_booking_request_created`: Public booking request created via direct booking endpoint

---

### Troubleshooting

**Problem**: Idempotency replay creates duplicate booking instead of returning cached response

**Symptoms**:
- Same Idempotency-Key + same payload creates two bookings with different IDs
- Expected 201 with cached booking_id, got 201 with new booking_id

**Root Cause**:
- Idempotency check not running (missing dependency or import error)
- Race condition: two concurrent requests with same key before first commits
- Idempotency record expired (TTL > 24h since first request)

**Solution**:
1. Verify idempotency_keys table exists and has unique constraint:
   ```sql
   \d idempotency_keys
   -- Should show UNIQUE constraint: idempotency_keys_unique (agency_id, endpoint, method, idempotency_key)
   ```
2. Check if idempotency record exists:
   ```sql
   SELECT * FROM idempotency_keys 
   WHERE endpoint = '/api/v1/public/booking-requests' 
   AND idempotency_key = '<key>' 
   AND expires_at > NOW();
   ```
3. If missing: First request may have failed before storing idempotency record
4. If expired: Record was created >24h ago (normal behavior, retry will create new booking)
5. If race condition: Verify transaction isolation and uniqueness constraint enforcement

**Verification**:
```bash
# Run P3a smoke test
export API_BASE_URL="https://api.example.com"
export PID="<property-uuid>"
./backend/scripts/pms_p3a_idempotency_smoke.sh
# Should pass all 3 tests: first request (201), replay (cached 201), conflict (409)
```

---

**Problem**: Idempotency conflict (409) when replaying same request

**Symptoms**:
- Same Idempotency-Key + same payload returns 409 idempotency_conflict
- Expected cached 201 response

**Root Cause**:
- Request payload differs slightly (whitespace, field order, floating point precision)
- Request hash computation differs between first request and replay

**Solution**:
1. Verify payload is byte-for-byte identical (JSON canonical form):
   ```python
   import json, hashlib
   payload = {...}  # Your request dict
   canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
   print(hashlib.sha256(canonical.encode('utf-8')).hexdigest())
   ```
2. Check stored request_hash in idempotency_keys table
3. Common causes:
   - Floating point precision: `2.5` vs `2.50` (use integers for cents/currency)
   - Date format: `2037-06-01` vs `2037-6-1` (use ISO 8601 with zero-padding)
   - Field order: JSON objects have stable field order in canonical form
4. If hashes differ: Client must send exact same payload or use new Idempotency-Key

---

**Problem**: Audit events not appearing in audit_log table

**Symptoms**:
- Booking created successfully but no audit_log record
- Expected `public_booking_request_created` event missing

**Root Cause**:
- Audit logging is best-effort (failures logged but don't break request)
- audit_log table doesn't exist or schema out of date
- Audit event emission failed (exception caught and logged)

**Solution**:
1. Verify audit_log table exists:
   ```sql
   \d audit_log
   -- Should show columns: id, created_at, agency_id, actor_user_id, actor_type, action, entity_type, entity_id, request_id, idempotency_key, ip, user_agent, metadata
   ```
2. Check application logs for audit emission errors:
   ```bash
   docker logs pms-backend 2>&1 | grep "Failed to emit audit event"
   # Should show non-fatal error if audit write failed
   ```
3. If table missing: Run migrations to create audit_log table
4. If schema mismatch: Run latest migrations to update schema
5. Verify audit event was called (check application logs):
   ```bash
   docker logs pms-backend 2>&1 | grep "Audit event emitted"
   # Should show: action=public_booking_request_created, entity=booking/<uuid>
   ```

**Verification**:
```bash
# Check audit log for recent public booking events
psql $DATABASE_URL -c "
SELECT created_at, action, entity_type, entity_id, actor_type, ip, metadata->>'property_id' as property_id
FROM audit_log
WHERE action = 'public_booking_request_created'
ORDER BY created_at DESC
LIMIT 5;
"
```

---

**Problem**: Migration 20260106160000 fails with ERROR 42P17 (functions in index predicate must be marked IMMUTABLE)

**Symptoms**:
- Running migration `20260106160000_add_idempotency_keys.sql` in Supabase SQL Editor fails
- Error: `42P17 - functions in index predicate must be marked IMMUTABLE`
- Error points to indexes `idx_idempotency_keys_lookup` or `idx_idempotency_keys_expires_at`

**Root Cause**:
- Original migration created partial indexes with `WHERE expires_at > NOW()` predicates
- PostgreSQL rejects this because `NOW()` is VOLATILE (not IMMUTABLE)
- Index predicates require IMMUTABLE functions only

**Solution**:
1. Apply hotfix migration `20260106180000_fix_idempotency_keys_indexes.sql`:
   - Drops problematic partial indexes
   - Recreates them without the `WHERE` predicate
   - Indexes still work correctly, just without the partial filter optimization
2. Run in Supabase SQL Editor:
   ```sql
   -- Verify indexes exist after migration
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'idempotency_keys';
   ```
3. Expected output: Two indexes without `WHERE expires_at > NOW()` predicates

**Prevention**:
- Never use VOLATILE functions (`NOW()`, `CURRENT_TIMESTAMP`, etc.) in index predicates
- Use IMMUTABLE functions only, or omit the `WHERE` clause entirely

---

**Problem**: Smoke script Test 3 fails to detect idempotency_conflict despite 409 response

**Symptoms**:
- `pms_p3a_idempotency_smoke.sh` Test 3 returns 409 Conflict (correct)
- Script reports: "Got 409 but error type is not idempotency_conflict"
- Test 3 fails even though API behavior is correct

**Root Cause**:
- API returns 409 with nested error structure: `{"detail": {"error": "idempotency_conflict", ...}}`
- Script was checking top-level `.error` field, not `.detail.error`

**Solution**:
- Updated smoke script to check multiple paths: `.detail.error`, `.error`, or grep fallback
- Script now handles nested FastAPI HTTPException detail dicts
- No API changes needed (response format is correct)

**Verification**:
```bash
# Run smoke test (should pass all 3 tests now)
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export PID="<property-uuid>"
./backend/scripts/pms_p3a_idempotency_smoke.sh
# Expected: rc=0, all tests PASS
```

---

**Related Documentation**:
- [P3a Idempotency Smoke Script](../../scripts/pms_p3a_idempotency_smoke.sh) - Smoke test for idempotency behavior
- [Idempotency Implementation](../../app/core/idempotency.py) - Idempotency check/store functions
- [Audit Implementation](../../app/core/audit.py) - Audit event emission (best-effort)
- [Public Booking Routes](../../app/api/routes/public_booking.py) - Integration point
- [Migration 20260106160000](../../../supabase/migrations/20260106160000_add_idempotency_keys.sql) - Idempotency keys table
- [Migration 20260106170000](../../../supabase/migrations/20260106170000_add_audit_log.sql) - Audit log table
- [Migration 20260106180000](../../../supabase/migrations/20260106180000_fix_idempotency_keys_indexes.sql) - Fix 42P17 index issue (hotfix)

---
## P3b: Domain Tenant Resolution + Host Allowlist + CORS (Public Endpoints)

### Overview

P3b adds multi-tenant domain mapping, host allowlist enforcement, and explicit CORS configuration for public direct booking endpoints. These features enable:
1. **Domain-based tenant resolution**: Each agency can have their own domain (e.g., customer.com → agency_id)
2. **Host allowlist**: Prevents unauthorized domains from accessing public endpoints
3. **Explicit CORS origins**: Fine-grained control over which browser origins can call the API

### Environment Configuration

**Required Settings:**
```bash
# Host allowlist (comma-separated domains)
ALLOWED_HOSTS="api.fewo.kolibri-visions.de,customer1.com,customer2.de"

# CORS allowed origins (explicit origins, no wildcards)
# Optional: Uses ALLOWED_ORIGINS if not set (backward compat)
CORS_ALLOWED_ORIGINS="https://app.customer1.com,https://www.customer2.de"

# Proxy headers (default: true)
# Set to true if behind reverse proxy/load balancer (respect X-Forwarded-Host)
TRUST_PROXY_HEADERS=true
```

**Safe Defaults:**
- `ALLOWED_HOSTS=""` (empty): In non-prod → allow all with warning; In prod → allow all but log error (fail-open for backward compat)
- `CORS_ALLOWED_ORIGINS` not set: Falls back to existing `ALLOWED_ORIGINS`
- `TRUST_PROXY_HEADERS=true`: Respects X-Forwarded-Host header (standard for proxied deployments)

---

### How to Add Customer Domain

**Prerequisites:**
- Customer domain DNS points to API server (via A/CNAME record or reverse proxy)
- Domain is routed to your API (Plesk, Nginx, etc.)

**Steps:**

1. **Add domain mapping in Supabase SQL Editor:**
   ```sql
   -- Insert domain → agency mapping
   INSERT INTO public.agency_domains (agency_id, domain, is_primary)
   VALUES (
       '<agency-uuid>',        -- Agency UUID
       'customer.com',          -- Domain (lowercase, no port, no protocol)
       true                     -- Primary domain (one per agency recommended)
   );
   ```

2. **Add domain to ALLOWED_HOSTS:**
   ```bash
   # Update environment variable (append to existing list)
   ALLOWED_HOSTS="api.fewo.kolibri-visions.de,customer.com"
   ```

3. **Add site origins to CORS_ALLOWED_ORIGINS (if browser calls API directly):**
   ```bash
   # Update environment variable
   CORS_ALLOWED_ORIGINS="https://app.customer.com,https://www.customer.com"
   ```

4. **Restart backend service:**
   ```bash
   docker restart pms-backend
   ```

5. **Verify domain works:**
   ```bash
   # Test with custom Host header
   curl -H "Host: customer.com" https://api.fewo.kolibri-visions.de/api/v1/public/ping
   # Expected: 200 OK
   ```

---

### Domain Tenant Resolution Flow

**For Public Endpoints** (`/api/v1/public/*`):

1. **Extract Host from request:**
   - If `TRUST_PROXY_HEADERS=true`: Prefer `X-Forwarded-Host` (first value if multiple)
   - Else: Use `Host` header
   - Normalize: lowercase, remove port, strip trailing dot

2. **Resolve agency_id:**
   - **Primary**: Query `agency_domains` table by domain → get `agency_id`
   - **Fallback**: Query `properties` table by `property_id` → get `agency_id`
   - **Cross-check**: Verify property belongs to resolved agency (prevent cross-tenant access)

3. **If no resolution:**
   - Return 422 with actionable message: "Could not resolve agency for booking request. Property may not exist, or domain mapping not configured."

---

### Troubleshooting

**Problem**: Request returns 403 host_not_allowed

**Symptoms**:
- `POST /api/v1/public/booking-requests` returns 403
- Error: `{"error": "host_not_allowed", "message": "Host '...' not allowed. Configure ALLOWED_HOSTS."}`

**Root Cause**:
- Request Host/X-Forwarded-Host is not in `ALLOWED_HOSTS` environment variable
- Domain not added to allowlist after configuring in `agency_domains`

**Solution**:
1. Check request Host header:
   ```bash
   curl -v https://api.example.com/api/v1/public/ping 2>&1 | grep "Host:"
   # Or check X-Forwarded-Host if behind proxy
   ```
2. Verify ALLOWED_HOSTS includes the domain:
   ```bash
   # Check environment variable
   docker exec pms-backend env | grep ALLOWED_HOSTS
   ```
3. Add domain to ALLOWED_HOSTS and restart:
   ```bash
   ALLOWED_HOSTS="api.fewo.kolibri-visions.de,customer.com"
   docker restart pms-backend
   ```

---

**Problem**: Domain mapping not working (wrong agency resolved)

**Symptoms**:
- Request to `customer.com` resolves to wrong agency or fails
- "Property not available for this domain" error

**Root Cause**:
- Domain not in `agency_domains` table
- Domain normalized incorrectly (case mismatch, port included, etc.)
- Property belongs to different agency than domain mapping

**Solution**:
1. Check if domain mapping exists:
   ```sql
   SELECT * FROM agency_domains WHERE domain = 'customer.com';
   -- Should return row with correct agency_id
   ```
2. If missing, add mapping:
   ```sql
   INSERT INTO agency_domains (agency_id, domain, is_primary)
   VALUES ('<agency-uuid>', 'customer.com', true);
   ```
3. Verify domain normalization matches:
   - Stored domain must be lowercase, no port, no protocol
   - Example: ✅ `customer.com` ❌ `Customer.com:443` ❌ `https://customer.com`
4. Cross-check property agency:
   ```sql
   SELECT id, agency_id FROM properties WHERE id = '<property-uuid>';
   -- agency_id must match agency_domains.agency_id for domain
   ```

---

**Problem**: Proxy strips X-Forwarded-Host header

**Symptoms**:
- Domain resolution uses wrong host (API domain instead of customer domain)
- Host allowlist check fails unexpectedly

**Root Cause**:
- Reverse proxy (Nginx, Caddy, etc.) not forwarding `X-Forwarded-Host` header
- Proxy configuration missing `proxy_set_header X-Forwarded-Host $host;`

**Solution**:
1. **Nginx**: Add to proxy block:
   ```nginx
   location / {
       proxy_pass http://backend:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Forwarded-Host $host;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   }
   ```
2. **Caddy**: Usually automatic, but verify:
   ```caddyfile
   reverse_proxy backend:8000 {
       header_up Host {host}
       header_up X-Forwarded-Host {host}
   }
   ```
3. Restart proxy and verify headers are forwarded

---

**Problem**: CORS preflight fails (browser error)

**Symptoms**:
- Browser console shows CORS error: "Access-Control-Allow-Origin header missing"
- OPTIONS request to `/api/v1/public/booking-requests` fails

**Root Cause**:
- Origin not in `CORS_ALLOWED_ORIGINS` (or `ALLOWED_ORIGINS` if not set)
- CORS middleware not configured or disabled

**Solution**:
1. Add origin to CORS_ALLOWED_ORIGINS:
   ```bash
   CORS_ALLOWED_ORIGINS="https://app.customer.com,https://www.customer.com"
   ```
2. Restart backend:
   ```bash
   docker restart pms-backend
   ```
3. Test CORS preflight:
   ```bash
   curl -X OPTIONS https://api.example.com/api/v1/public/booking-requests \
     -H "Origin: https://app.customer.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type,idempotency-key" \
     -v
   # Expected: Access-Control-Allow-Origin: https://app.customer.com
   ```

---

**Related Documentation**:
- [P3b Domain/Host/CORS Smoke Script](../../scripts/pms_p3b_domain_host_cors_smoke.sh) - Smoke test for P3b features
- [Domain Resolution Implementation](../../app/core/tenant_domain.py) - Domain-based tenant resolution logic
- [Host Allowlist Implementation](../../app/core/public_host_allowlist.py) - Host enforcement for public endpoints
- [Public Booking Routes](../../app/api/routes/public_booking.py) - Integration point (updated for P3b)
- [Migration 20260106190000](../../../supabase/migrations/20260106190000_add_agency_domains.sql) - Agency domains table
- [Config](../../app/core/config.py) - ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, TRUST_PROXY_HEADERS settings

---


## P3c: Audit Review Actions + Request/Correlation ID + Idempotency (Review Endpoints)

### Overview

P3c completes the P3 hardening initiative by adding comprehensive audit logging, request tracing, and optional idempotency support for review workflow endpoints (approve/decline).

**What P3c Provides:**
1. **Audit Events for Review Actions**: Audit log entries are automatically created when booking requests are approved or declined via internal review endpoints
2. **Request/Correlation ID Capture**: Standardized request ID extraction from headers (`X-Request-ID`, `X-Correlation-ID`, `CF-Ray`, `X-Amzn-Trace-Id`) for end-to-end tracing
3. **Optional Idempotency for Review Transitions**: Prevents duplicate approve/decline transitions when the same `Idempotency-Key` is used (protects against retry/double-click)
4. **Ops Endpoint for Audit Log Reads**: Admin-only API endpoint for querying audit log entries (enables automated verification)

**Key Benefits:**
- **Accountability**: Track who approved/declined which booking requests and when
- **Traceability**: Correlate requests across systems using request IDs
- **Retry Safety**: Idempotency prevents accidental duplicate state transitions
- **Automated Verification**: Smoke tests can verify audit events are written correctly

### Request/Correlation ID Headers

P3c automatically extracts request IDs from incoming HTTP headers for correlation and tracing.

**Supported Headers (checked in order):**
1. `X-Request-ID` - Common custom request tracking header
2. `X-Correlation-ID` - Alternative correlation header
3. `CF-Ray` - Cloudflare trace ID (if using Cloudflare)
4. `X-Amzn-Trace-Id` - AWS ALB/API Gateway trace ID (if using AWS)

**Behavior:**
- First non-empty header value is used as the request ID
- If no headers present, a new UUID is generated automatically
- Request ID is stored in audit log entries for each action

**Example:**
```bash
curl -X POST https://api.example.com/api/v1/booking-requests/{id}/approve \
  -H "Authorization: Bearer $JWT" \
  -H "X-Request-ID: abc123-unique-id" \
  -d '{"internal_note": "Approved after guest verification"}'
```

### Audit Log Events

P3c emits audit events for the following review workflow actions:

**Actions Audited:**
- `booking_request_approved` - When a booking request is approved (status: requested/under_review → confirmed)
- `booking_request_declined` - When a booking request is declined (status: requested/under_review → cancelled)

**Audit Event Structure:**
```json
{
  "id": "uuid",
  "created_at": "2026-01-06T22:00:00Z",
  "agency_id": "uuid",
  "actor_type": "user",
  "actor_user_id": "uuid",
  "action": "booking_request_approved",
  "entity_type": "booking_request",
  "entity_id": "uuid",
  "request_id": "abc123-unique-id",
  "idempotency_key": "optional-idempotency-key",
  "ip": "192.168.1.1",
  "user_agent": "curl/7.68.0",
  "metadata": {
    "previous_status": "requested",
    "new_status": "confirmed",
    "internal_note": "Approved after verification",
    "booking_id": "uuid"
  }
}
```

**Audit Behavior:**
- **Best-effort**: Audit logging failures are logged but do NOT break the main request
- **Tenant-scoped**: All audit events include `agency_id` for multi-tenant isolation
- **Automatic**: No manual instrumentation needed - events are emitted automatically

### Idempotency for Review Endpoints

P3c extends the idempotency support from P3a to review endpoints (approve/decline).

**How to Use Idempotency:**
1. Include `Idempotency-Key` header in approve/decline requests
2. Use a unique key per logical operation (e.g., `approve-{uuid}`)
3. Reuse the same key for retries of the same operation

**Example - Approve with Idempotency:**
```bash
# First attempt
curl -X POST https://api.example.com/api/v1/booking-requests/{id}/approve \
  -H "Authorization: Bearer $JWT" \
  -H "Idempotency-Key: approve-20260106-abc123" \
  -d '{"internal_note": "Approved"}'
# Returns: 200 OK (approval executed)

# Retry with same key (e.g., after timeout/network error)
curl -X POST https://api.example.com/api/v1/booking-requests/{id}/approve \
  -H "Authorization: Bearer $JWT" \
  -H "Idempotency-Key: approve-20260106-abc123" \
  -d '{"internal_note": "Approved"}'
# Returns: 200 OK (cached response, no duplicate transition)
```

**Idempotency Behavior:**
- **Same key + same payload** → Returns cached response (status 200, no DB write)
- **Same key + different payload** → Returns 409 Conflict with `idempotency_conflict` error
- **No key provided** → Standard behavior (no idempotency check)

**Idempotency Key TTL:**
- 24 hours (same as P3a public booking requests)
- Stored in `public.idempotency_keys` table (shared with P3a)
- Agency-scoped with unique constraint: `(agency_id, endpoint, method, idempotency_key)`

### Ops Endpoint: Audit Log Reads

P3c adds a new admin-only API endpoint for querying audit log entries.

**Endpoint:** `GET /api/v1/ops/audit-log`

**Authentication:** JWT with admin role required

**Query Parameters:**
- `action` (optional): Filter by action (e.g., `booking_request_approved`)
- `entity_id` (optional): Filter by entity UUID
- `limit` (optional): Max records to return (1-500, default: 50)

**Example - Query Audit Log:**
```bash
# Get recent booking_request_approved events
curl -X GET "https://api.example.com/api/v1/ops/audit-log?action=booking_request_approved&limit=10" \
  -H "Authorization: Bearer $JWT"

# Get audit events for specific booking request
curl -X GET "https://api.example.com/api/v1/ops/audit-log?entity_id={booking_request_id}" \
  -H "Authorization: Bearer $JWT"
```

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "created_at": "2026-01-06T22:00:00Z",
      "action": "booking_request_approved",
      "actor_type": "user",
      "actor_user_id": "uuid",
      "entity_type": "booking_request",
      "entity_id": "uuid",
      "request_id": "abc123",
      "idempotency_key": "approve-20260106-xyz",
      "metadata": {...}
    }
  ],
  "total": 1,
  "limit": 50
}
```

**Usage:**
- Automated smoke tests: Verify audit events are written
- Manual auditing: Investigate who performed which actions
- Troubleshooting: Trace request flow via `request_id`

### Smoke Testing

**Script:** `backend/scripts/pms_p3c_audit_review_smoke.sh`

**Purpose:** Verify P3c audit logging, request ID capture, and idempotency for review endpoints.

**What It Tests:**
1. Create public booking requests
2. Approve booking request with `Idempotency-Key`
3. Test idempotent replay (same key → cached response)
4. Decline booking request with `Idempotency-Key`
5. Verify audit log entries via `/api/v1/ops/audit-log` endpoint

**Prerequisites:**
- `jq` (JSON parser)
- Admin JWT token
- Property UUID (`PID`)

**Usage:**
```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export PID="<property-uuid>"
export JWT="<admin-jwt-token>"
./backend/scripts/pms_p3c_audit_review_smoke.sh
```

**Expected Output:**
```
✅ TEST PASSED: All tests passed
Smoke test: PASS
rc=0
```

**Exit Codes:**
- `0` - Success (all tests passed)
- `1` - Test failure (unexpected status code or missing audit events)
- `2` - Server error (500 response detected)

### Troubleshooting

#### Missing Audit Log Entries

**Symptom:** Audit log query returns 0 results after approve/decline action.

**Possible Causes:**
1. **Best-effort audit failed**: Audit emission is non-blocking; database errors don't break requests
2. **Wrong tenant scope**: Audit log is tenant-scoped; verify JWT agency_id matches entity agency
3. **Timing issue**: Allow 1-2 seconds after action before querying audit log (eventual consistency)
4. **Wrong filter**: Check `action` and `entity_id` query parameters match expected values

**How to Debug:**
```bash
# Check backend logs for audit emission errors
tail -f logs/backend.log | grep "Failed to emit audit event"

# Query all recent audit events (no filters)
curl -X GET "https://api.example.com/api/v1/ops/audit-log?limit=50" \
  -H "Authorization: Bearer $JWT"

# Verify entity belongs to correct agency
curl -X GET "https://api.example.com/api/v1/booking-requests/{id}" \
  -H "Authorization: Bearer $JWT"
```

**Solution:**
- If audit emission consistently fails, check database connectivity and `audit_log` table schema
- If timing issue, add 2-second delay before verification in smoke tests
- If wrong tenant, ensure JWT token agency_id matches booking request agency_id

#### Idempotency Conflict (409) Unexpectedly

**Symptom:** Getting 409 `idempotency_conflict` when retrying approve/decline with same key.

**Possible Causes:**
1. **Payload mismatch**: Request body differs between attempts (even whitespace/ordering matters)
2. **Cached from different request**: Same key used for different operation/entity
3. **Expired but re-added**: Key expired (24h TTL) and recreated with different payload

**How to Debug:**
```bash
# Check idempotency_keys table
SELECT idempotency_key, request_hash, response_status, created_at, expires_at
FROM idempotency_keys
WHERE idempotency_key = 'your-key-here'
AND agency_id = '{agency-uuid}'
AND expires_at > NOW()
LIMIT 1;

# Compare request hashes (should match for idempotent replay)
```

**Solution:**
- Ensure request payload is byte-for-byte identical (JSON key ordering, whitespace)
- Use unique idempotency keys per operation (don't reuse across different entities)
- Wait for TTL expiration (24h) or use new key if payload needs to change

#### Auth Scope Issue (403 Forbidden)

**Symptom:** `GET /api/v1/ops/audit-log` returns 403 Forbidden.

**Possible Causes:**
1. **Non-admin role**: Endpoint requires admin role
2. **Invalid JWT**: Token expired or malformed
3. **Cross-tenant access**: JWT agency_id doesn't match audit records

**How to Debug:**
```bash
# Verify JWT role claim
echo $JWT | cut -d'.' -f2 | base64 -d | jq '.role'
# Should return: "admin"

# Check JWT expiration
echo $JWT | cut -d'.' -f2 | base64 -d | jq '.exp'
# Convert to date: date -r $(echo $JWT | cut -d'.' -f2 | base64 -d | jq -r '.exp')
```

**Solution:**
- Use JWT with admin role (manager role is NOT sufficient for `/ops/audit-log`)
- Refresh expired JWT using authentication endpoint
- Ensure JWT agency_id matches the agency you're querying

#### Request ID Not Captured

**Symptom:** Audit log entries have `request_id` but it's a random UUID (not the header value).

**Possible Causes:**
1. **Header not sent**: Request didn't include `X-Request-ID` or similar headers
2. **Proxy stripped headers**: Load balancer/proxy removed custom headers
3. **Header name mismatch**: Used non-standard header name not in P3c header list

**How to Debug:**
```bash
# Test header pass-through
curl -X POST https://api.example.com/api/v1/booking-requests/{id}/approve \
  -H "Authorization: Bearer $JWT" \
  -H "X-Request-ID: test-header-123" \
  -d '{"internal_note": "Test"}' \
  -v 2>&1 | grep -i request-id

# Check audit log entry
curl -X GET "https://api.example.com/api/v1/ops/audit-log?action=booking_request_approved&limit=1" \
  -H "Authorization: Bearer $JWT" | jq '.items[0].request_id'
# Should return: "test-header-123" (if header was captured)
```

**Solution:**
- Verify header is sent by client (use `-v` flag in curl to see request headers)
- If behind proxy, configure proxy to preserve `X-Request-ID` header
- Use one of the supported headers: `X-Request-ID`, `X-Correlation-ID`, `CF-Ray`, `X-Amzn-Trace-Id`
- If no header provided, P3c generates a UUID automatically (this is expected behavior)


#### Smoke Script 422 Validation Error

**Symptom:** `pms_p3c_audit_review_smoke.sh` fails with HTTP 422 validation_error when creating public booking requests.

**Possible Causes:**
1. **Payload mismatch**: Script sending incorrect field names or missing required fields
2. **Schema drift**: API schema changed but smoke script not updated
3. **Env var issues**: Required environment variables (PID, DATE_FROM, DATE_TO) not set or invalid

**How to Debug:**
The script automatically prints the sent payload on 422 errors:
```bash
❌ FAIL: Returned 422 validation_error (payload mismatch)
Response: {"detail":[{"type":"missing","loc":["body","date_from"],...}]}

Payload sent:
{
  "property_id": "...",
  "check_in": "2037-06-01",  # ← WRONG: should be "date_from"
  ...
}
```

**Common Issues:**
- Using `check_in`/`check_out` instead of `date_from`/`date_to`
- Using `num_adults`/`num_children` instead of `adults`/`children`
- Using `guest_info` instead of `guest`
- Missing required fields: `property_id`, `date_from`, `date_to`, `adults`, `guest`

**Solution:**
Ensure the script uses the correct BookingRequestInput schema:
```json
{
  "property_id": "uuid",
  "date_from": "YYYY-MM-DD",
  "date_to": "YYYY-MM-DD",
  "adults": 2,
  "children": 0,
  "guest": {
    "first_name": "...",
    "last_name": "...",
    "email": "...",
    "phone": "..."
  },
  "currency": "EUR"
}
```

If schema changed, update the smoke script payload builder to match current API requirements.



---

## P3 Public Direct Booking Hardening (Consolidated)

**Overview:** This section covers the consolidated P3 Direct Booking Hardening smoke test that verifies all P3 components (P3a, P3b, P3c) in a single test workflow.

**Purpose:** Validate that public direct booking endpoints are properly hardened with idempotency, CORS/origin controls, and comprehensive audit logging.

**Components Included:**
- **P3a**: Idempotency-Key support for `/api/v1/public/booking-requests`
- **P3b**: CORS/Origin/Host allowlist for public endpoints
- **P3c**: Audit log for booking request lifecycle events

**Smoke Test Script:** `backend/scripts/pms_public_direct_booking_hardening_smoke.sh`

**What The Consolidated Test Verifies:**
1. CORS preflight with allowed origin returns proper headers
2. First booking request with Idempotency-Key succeeds
3. Retry with same Idempotency-Key + same payload returns same booking ID
4. Retry with same Idempotency-Key + different payload returns HTTP 409
5. Audit log contains `public.booking_request.created` event

**Required Environment:**
- `HOST`: PMS backend base URL
- `JWT_TOKEN`: JWT with manager/admin role
- Optional: `AGENCY_ID`, `PROPERTY_ID`, `ALLOWED_ORIGIN`

**Public Booking Requests Payload Format:**
- The `/api/v1/public/booking-requests` endpoint requires `date_from` and `date_to` fields (YYYY-MM-DD format)
- Do NOT use `check_in`/`check_out` - these will cause validation errors
- Example: `{"property_id": "...", "date_from": "2026-02-01", "date_to": "2026-02-05", "adults": 2, "children": 0, "guest": {...}}`

**Usage:**
```bash
HOST=https://pms-backend.production.example.com \
JWT_TOKEN="eyJ..." \
./backend/scripts/pms_public_direct_booking_hardening_smoke.sh
```

**Expected Success Output:**
```
✅ Test 1 PASSED: CORS preflight returned allow-origin header
✅ Test 2 PASSED: Created booking request with idempotency key: 770e8400-...
✅ Test 3 PASSED: Idempotency works - same booking ID returned: 770e8400-...
✅ Test 4 PASSED: Idempotency conflict returned 409 as expected
✅ Test 5 PASSED: Found audit log event for booking request created
✅ All P3 Public Direct Booking Hardening smoke tests passed! 🎉
```

### Common Issues

#### Test 1 Skipped (CORS)

**Symptom:** Test 1 reports "SKIPPED: CORS may not be configured".

**Cause:** CORS middleware not configured in test environment or allowed origin mismatch.

**Impact:** Non-critical for functionality testing. Production should have CORS configured.

**Solution:** Verify `ALLOWED_ORIGINS` environment variable in production matches `ALLOWED_ORIGIN` test value.

#### Test 2 Fails (Create Booking Request)

**Symptom:** Test 2 fails with 400/404/500 error.

**Possible Causes:**
1. Property doesn't exist or user lacks access
2. JWT token invalid/expired
3. Required booking fields missing/invalid
4. Database connectivity issue

**How to Debug:**
```bash
# Verify property exists and is accessible
curl -X GET "$HOST/api/v1/properties/?limit=1" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Check JWT expiration
echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq '.exp'

# Test minimal booking request
curl -X POST "$HOST/api/v1/public/booking-requests" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-$(date +%s)" \
  -d '{"property_id":"<uuid>","check_in":"2026-02-01","check_out":"2026-02-05","adults":2,"children":0,"guest":{"email":"test@example.com","first_name":"Test","last_name":"User"}}'
```

**Solution:** Fix property access, refresh JWT, or correct booking payload.

#### Test 3 Fails (Idempotency Retry)

**Symptom:** Retry returns different booking ID instead of same ID.

**Cause:** Idempotency middleware not enabled or migration not applied.

**How to Debug:**
```bash
# Check if idempotency middleware is active (should see Idempotency-Key in response headers)
curl -v -X POST "$HOST/api/v1/public/booking-requests" \
  -H "Idempotency-Key: test-123" \
  -d '...' 2>&1 | grep -i idempotency

# Verify migration applied
psql $DATABASE_URL -c "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'idempotency_keys');"
```

**Solution:** Enable idempotency middleware in app startup, apply migration 20260106160000.

#### Test 4 Fails (Expected 409 Conflict)

**Symptom:** Retry with different payload returns 200/201 instead of 409.

**Cause:** Payload hash comparison not working or idempotency key TTL expired.

**How to Debug:**
```bash
# Check idempotency_keys table for stored payload hash
psql $DATABASE_URL -c "SELECT idempotency_key, payload_hash, created_at FROM idempotency_keys ORDER BY created_at DESC LIMIT 5;"

# Verify tests run within 24h TTL window
# If payload_hash is NULL, hash calculation is broken
```

**Solution:** Check `app/core/idempotency.py` hash calculation logic, ensure tests complete within TTL.

#### Test 5 Failed (Audit Log)

**Symptom:** Test 5 reports "FAILED: Could not find audit event for booking request" after polling retries.

**Possible Causes:**
1. JWT lacks admin role (audit-log endpoint requires admin)
2. Audit emission failed (database issue)
3. Multi-tenant setup requires `AGENCY_ID` to be set for x-agency-id header
4. Timing issue (audit not yet committed, though script polls up to ~10s)

**How to Debug:**
```bash
# Verify JWT role
echo $JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq '.role'
# Should return: "admin" (manager is NOT sufficient)

# Check if AGENCY_ID is needed (multi-tenant setups)
# Export AGENCY_ID before running script:
export AGENCY_ID="ffd0123a-10b6-40cd-8ad5-66eee9757ab7"

# Check audit_log table directly
psql $DATABASE_URL -c "SELECT action, actor_type, entity_id, metadata FROM audit_log WHERE action LIKE '%booking%request%' ORDER BY created_at DESC LIMIT 5;"

# Check backend logs for audit emission errors
docker logs pms-backend --tail 100 | grep -i audit
```

**Solution:**
- Use admin JWT token
- Set `AGENCY_ID` environment variable if you have multiple agencies
- Verify audit_log migration applied (20260106170000)
- Check database connectivity
- Script automatically polls up to 10 times (1s intervals) for eventual consistency

### Testing Against Production

**Pre-flight Checklist:**
- [ ] JWT token has valid admin role
- [ ] `HOST` points to production backend URL
- [ ] `PROPERTY_ID` exists and belongs to agency (or omit for auto-pick)
- [ ] `ALLOWED_ORIGIN` matches production CORS config (default: `https://fewo.kolibri-visions.de`)
- [ ] Production database has migrations 20260106160000 (idempotency) and 20260106170000 (audit) applied

**Recommended Workflow:**
1. Run consolidated smoke script first for quick validation
2. If any test fails, run individual P3a/b/c scripts for detailed debugging
3. Check specific runbook sections (P3a, P3b, P3c) for component-specific issues

**Related Documentation:**
- [P3a Runbook Section](#p3a-idempotency--audit-log-public-booking-requests) - Idempotency details
- [P3b Runbook Section](#p3b-domain-tenant-resolution--host-allowlist--cors-public-endpoints) - CORS/domain details
- [P3c Runbook Section](#p3c-audit-review-actions--requestcorrelation-id--idempotency-review-endpoints) - Audit details
- [Scripts README](../../scripts/README.md#p3-public-direct-booking-hardening-smoke-test-consolidated) - Script usage guide

---

## Customer Domain Onboarding SOP

**Purpose**: Step-by-step procedure for onboarding new customer domains to the PMS multi-tenant system.

**Target Audience**: Junior admins, ops engineers, support staff

**Estimated Time**: 15-30 minutes (including DNS propagation wait if not using pre-DNS verification)

### Pre-requisites

**Required Access:**
- ✅ Domain registrar access (or customer cooperation for DNS changes)
- ✅ Plesk admin access (for DNS zone management)
- ✅ Supabase owner/admin access (for SQL Editor and agency_domains table)
- ✅ Coolify admin access (for environment variable updates)
- ✅ Backend server SSH/shell access (for verification script execution)

**Required Information:**
- Customer domain (e.g., `customer.example.com`)
- Agency UUID (from agencies table in Supabase)
- Server IP address (for pre-DNS testing, from Coolify or server config)
- Frontend origin (e.g., `https://app.customer.example.com`, if applicable for CORS)

### Step-by-Step Procedure

#### Step 1: DNS Configuration (Plesk or Registrar)

**Goal**: Point customer domain to PMS backend server IP.

**Option A: CNAME Record (Recommended)**
```dns
customer.example.com.  3600  IN  CNAME  pms.your-server.com.
```

**Option B: A/AAAA Record (Direct IP)**
```dns
customer.example.com.  3600  IN  A      1.2.3.4
customer.example.com.  3600  IN  AAAA   2001:db8::1
```

**Important Notes:**
- Use **lowercase** domain names (backend normalizes to lowercase)
- **NO trailing dot** in Supabase/ENV vars (Plesk DNS may require it, but app does not)
- TTL 3600 (1 hour) is safe default
- If using Plesk DNS: Add record in domain zone file editor
- If using external DNS: Provide DNS change instructions to customer

**Validation:**
```bash
# Wait for DNS propagation (or skip if using pre-DNS verification)
nslookup customer.example.com
# Should resolve to server IP

# Test with dig (more detailed)
dig customer.example.com A
dig customer.example.com AAAA
```

#### Step 2: Supabase Database Mapping

**Goal**: Map customer domain to agency_id in agency_domains table.

**SQL Editor Query:**
```sql
-- Replace with actual values (NO trailing dots, lowercase)
INSERT INTO agency_domains (agency_id, domain)
VALUES (
  '12345678-1234-1234-1234-123456789abc',  -- Agency UUID from agencies table
  'customer.example.com'                     -- Customer domain (lowercase, no trailing dot)
)
ON CONFLICT (domain) DO NOTHING;
```

**Important Notes:**
- Domain must be **lowercase** and **no trailing dot**
- Agency UUID must exist in agencies table (verify first)
- ON CONFLICT prevents duplicate errors if domain already mapped
- RLS policies enforce tenant isolation (domain cannot be shared across agencies)

**Validation:**
```sql
-- Verify mapping exists
SELECT * FROM agency_domains WHERE domain = 'customer.example.com';
-- Should return one row with correct agency_id
```

#### Step 3: Coolify Environment Variables

**Goal**: Update backend ENV vars to allow customer domain in host allowlist and CORS.

**ENV Var Updates in Coolify:**

1. **ALLOWED_HOSTS** (Host Allowlist):
```bash
# Add customer domain to comma-separated list (NO trailing dots, lowercase)
ALLOWED_HOSTS=localhost,pms.your-server.com,customer.example.com
```

2. **CORS_ALLOWED_ORIGINS** (CORS Allow List):
```bash
# Add frontend origin if applicable (e.g., for SPA/React)
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://app.customer.example.com
```

3. **TRUST_PROXY_HEADERS** (Required for X-Forwarded-Host):
```bash
# Must be "true" for domain routing to work behind proxy
TRUST_PROXY_HEADERS=true
```

**Important Notes:**
- ENV var changes require **backend restart** (Coolify auto-restarts on ENV change)
- Domain in ALLOWED_HOSTS must **exactly match** request Host header (lowercase, no port)
- CORS origin must include **protocol** (https://) and **no trailing slash**
- Coolify may take 30-60 seconds to restart backend after ENV change

**Validation:**
```bash
# Check ENV vars are applied (SSH to backend container)
echo $ALLOWED_HOSTS
echo $CORS_ALLOWED_ORIGINS
echo $TRUST_PROXY_HEADERS
```

#### Step 4: TLS/Certificate Provisioning (Let's Encrypt)

**Goal**: Ensure HTTPS works for customer domain.

**Coolify Automatic Provisioning:**
1. Navigate to Coolify project → Domains tab
2. Add customer domain to domain list
3. Enable "Let's Encrypt" toggle
4. Coolify will automatically provision certificate via ACME challenge
5. Wait 1-2 minutes for certificate issuance

**Manual Validation (if needed):**
```bash
# Test TLS handshake
curl -v https://customer.example.com/api/v1/ops/version 2>&1 | grep -i "SSL certificate"
# Should show valid certificate (not self-signed)

# Check certificate expiry
echo | openssl s_client -connect customer.example.com:443 -servername customer.example.com 2>/dev/null | openssl x509 -noout -dates
```

**Common Issues:**
- **DNS not propagated**: Let's Encrypt ACME challenge fails → Wait for DNS TTL or use pre-DNS testing
- **Coolify domain not added**: Certificate not provisioned → Add domain in Coolify UI
- **Port 80 blocked**: ACME HTTP-01 challenge fails → Verify firewall allows port 80

#### Step 5: Verification (Pre-DNS or Post-DNS)

**Goal**: Verify domain routing, tenant isolation, and CORS before go-live.

**Option A: Pre-DNS Verification (Recommended)**
```bash
# Test before DNS propagation using curl --resolve
DOMAIN=customer.example.com \
SERVER_IP=1.2.3.4 \
./backend/scripts/pms_domain_onboarding_verify.sh
```

**Option B: Post-DNS Verification**
```bash
# Test after DNS propagation (omit SERVER_IP)
DOMAIN=customer.example.com \
./backend/scripts/pms_domain_onboarding_verify.sh
```

**Option C: With CORS Testing**
```bash
# Test CORS preflight for SPA/frontend
DOMAIN=customer.example.com \
TEST_ORIGIN=https://app.customer.example.com \
./backend/scripts/pms_domain_onboarding_verify.sh
```

**Expected Output:**
```
🔍 Verifying domain onboarding: customer.example.com
Using direct IP bypass (pre-DNS): 1.2.3.4
✅ Health check passed (HTTP 200)
✅ TLS certificate valid
✅ Agency ID confirmed: 12345678-1234-1234-1234-123456789abc
✅ CORS preflight passed (origin: https://app.customer.example.com)
✅ All checks passed - domain is ready for production traffic
```

**Troubleshooting:**
- See verification script output for actionable hints
- Common failures documented in script header comments
- Refer to "Customer Domain Onboarding Troubleshooting" section below

### Post-Onboarding Checklist

**Before Go-Live:**
- ✅ DNS resolves to correct IP (nslookup/dig)
- ✅ HTTPS works (valid certificate, not self-signed)
- ✅ Health endpoint returns 200 (not 403 host_not_allowed)
- ✅ Agency ID matches expected value
- ✅ CORS preflight passes (if applicable)
- ✅ Customer notified of go-live (if external domain)

**Documentation:**
- ✅ Record domain onboarding in ops log (domain, agency_id, date, operator)
- ✅ Update customer documentation with API base URL
- ✅ Provide customer with health endpoint for their monitoring: `https://customer.example.com/api/v1/ops/version`

**Monitoring:**
- ✅ Add domain to uptime monitoring (e.g., Pingdom, UptimeRobot)
- ✅ Set up alerts for certificate expiry (Let's Encrypt renews at 60 days)
- ✅ Monitor backend logs for 403 host_not_allowed errors

### Rollback Procedure

**If onboarding fails or needs to be reverted:**

1. **Remove Coolify ENV Vars:**
   - Remove customer domain from ALLOWED_HOSTS
   - Remove frontend origin from CORS_ALLOWED_ORIGINS
   - Coolify will auto-restart backend

2. **Delete Supabase Mapping:**
```sql
DELETE FROM agency_domains WHERE domain = 'customer.example.com';
```

3. **Revert DNS (if needed):**
   - Remove CNAME/A/AAAA record in Plesk or registrar
   - Wait for DNS TTL expiry (or flush caches)

4. **Remove Coolify Domain (if added):**
   - Remove domain from Coolify domains list
   - Let's Encrypt certificate will auto-expire (90 days)

**Rollback is safe and idempotent** - no data loss, only routing changes.

### Customer Domain Onboarding Troubleshooting

#### Problem: Verification Script Returns 403 host_not_allowed

**Symptom:**
```
❌ Health check failed: HTTP 403
Response: {"detail":"Host not allowed: customer.example.com"}
```

**Root Cause:**
- Customer domain not in ALLOWED_HOSTS environment variable
- ENV var change not applied (backend not restarted)
- Domain case mismatch (customer.example.com vs CUSTOMER.EXAMPLE.COM)

**Solution:**
1. Verify ALLOWED_HOSTS includes customer domain (lowercase, no port, no trailing dot)
2. Restart backend in Coolify (or wait for auto-restart)
3. Retry verification script

**Verification:**
```bash
# SSH to backend container
echo $ALLOWED_HOSTS | grep -i customer.example.com
# Should return the domain
```

#### Problem: Verification Script Returns 503 No Available Server

**Symptom:**
```
❌ Health check failed: HTTP 503
Response: <html>503 Service Temporarily Unavailable</html>
```

**Root Cause:**
- Backend is down (crashed, restart loop, deployment in progress)
- Proxy/load balancer cannot reach backend (network issue)
- TLS/certificate provisioning in progress (Coolify blocking traffic)

**Solution:**
1. Check backend health: `curl http://localhost:8000/api/v1/ops/version` (from server)
2. Check Coolify deployment logs for errors
3. Verify backend is running: `docker ps | grep backend`
4. Wait for deployment to complete (Coolify shows "Running" status)
5. Retry verification script

#### Problem: CORS Preflight Fails (403 or Missing Headers)

**Symptom:**
```
❌ CORS preflight failed: HTTP 403 (or missing Access-Control-Allow-Origin header)
```

**Root Cause:**
- Frontend origin not in CORS_ALLOWED_ORIGINS
- ENV var change not applied
- Origin format mismatch (http vs https, trailing slash, case)

**Solution:**
1. Verify CORS_ALLOWED_ORIGINS includes frontend origin (exact match, with protocol)
2. Restart backend in Coolify
3. Test with exact origin: `TEST_ORIGIN=https://app.customer.example.com ./script.sh`

**Verification:**
```bash
# Manual CORS preflight test
curl -X OPTIONS https://customer.example.com/api/v1/health \
  -H "Origin: https://app.customer.example.com" \
  -H "Access-Control-Request-Method: GET" \
  -v 2>&1 | grep -i "access-control"
# Should return Access-Control-Allow-Origin: https://app.customer.example.com
```

#### Problem: TLS Certificate Invalid or Self-Signed

**Symptom:**
```
❌ TLS error: self signed certificate
curl: (60) SSL certificate problem: self signed certificate
```

**Root Cause:**
- Let's Encrypt certificate not provisioned yet (Coolify in progress)
- DNS not propagated (ACME challenge fails)
- Domain not added to Coolify domains list

**Solution:**
1. Wait 2-5 minutes for Let's Encrypt provisioning
2. Verify DNS propagation: `nslookup customer.example.com`
3. Check Coolify logs for ACME errors
4. Ensure domain added to Coolify domains list with Let's Encrypt enabled
5. Retry verification script (or skip TLS check for pre-DNS testing)

**Workaround for Pre-DNS Testing:**
```bash
# Skip TLS verification (for testing only, not production)
curl -k https://customer.example.com/api/v1/ops/version
```

#### Problem: Agency ID Mismatch

**Symptom:**
```
⚠️  WARNING: Agency ID mismatch
Expected: 12345678-1234-1234-1234-123456789abc
Actual:   87654321-4321-4321-4321-cba987654321
```

**Root Cause:**
- Wrong agency_id in Supabase agency_domains mapping
- Database mapping not created (using default/fallback agency)
- Domain typo in Supabase (customer.example.com vs customer.exmaple.com)

**Solution:**
1. Verify agency_domains mapping: `SELECT * FROM agency_domains WHERE domain = 'customer.example.com';`
2. Update mapping if wrong: `UPDATE agency_domains SET agency_id = '...' WHERE domain = '...';`
3. Verify domain spelling (lowercase, no trailing dot)
4. Retry verification script

**Note**: Agency ID warning does not fail verification (exit code still 0), but should be investigated.

### Related Scripts

- **pms_domain_onboarding_verify.sh**: Automated verification script (this SOP)
- **pms_verify_deploy.sh**: Deployment verification (checks version/modules, not domain-specific)

### Related Documentation

- [Backend Configuration](../app/core/config.py) - ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, TRUST_PROXY_HEADERS
- [Domain Middleware](../app/middleware/domain.py) - Domain-to-tenant resolution logic
- [Database Schema](../../supabase/migrations/20250106000005_agency_domains.sql) - agency_domains table structure

### Maintenance

**Regular Tasks:**
- Monitor certificate expiry (Let's Encrypt auto-renews, but verify)
- Review agency_domains table for orphaned mappings (agency deleted but domain remains)
- Update ALLOWED_HOSTS when domains change or are removed

**Deprecation:**
- If domain is no longer needed, follow rollback procedure
- Archive ops log entry for domain removal (date, reason, operator)



---

## 1 VPS per Customer (Single-Tenant Installations Playbook)

**Purpose**: Complete step-by-step procedure for provisioning a dedicated VPS for a single customer (single-tenant deployment). This playbook enables junior admins to reliably set up isolated customer instances with their own domains, database, and infrastructure.

**Target Audience**: Junior admins, ops engineers, DevOps staff

**Estimated Time**: 2-4 hours (including DNS propagation and Let's Encrypt provisioning)

**Deployment Model**:
- **Single-Tenant**: One VPS per customer, one agency per VPS
- **Isolation**: Dedicated infrastructure (compute, database, domains)
- **White-Label**: Customer domains (www.kunde1.de, admin.kunde1.de, api.kunde1.de)
- **Architecture**: Full stack per VPS (Supabase/Postgres, Backend, Worker, Admin UI)

### Pre-requisites

**Required Access**:
- ✅ Hetzner Cloud account (or equivalent VPS provider)
- ✅ Coolify admin access (for app deployment and proxy configuration)
- ✅ Customer domain registrar access (or customer cooperation for DNS changes)
- ✅ Plesk admin access (for DNS zone management, if applicable)
- ✅ SSH access to customer VPS (root or sudo privileges)
- ✅ Git repository access (for source code deployment)

**Required Information**:
- Customer name/identifier (e.g., "kunde1")
- Customer domains (e.g., www.kunde1.de, admin.kunde1.de, api.kunde1.de)
- VPS size requirements (CPU, RAM, disk based on expected load)
- Database credentials strategy (auto-generated or customer-provided)
- SSL/TLS certificate requirements (Let's Encrypt recommended)

**Recommended Customer Domain Layout**:
```
www.kunde1.de        → Public-facing website/booking interface
admin.kunde1.de      → Backoffice/admin UI (staff access)
api.kunde1.de        → Backend API (used by admin UI and public site)
```

**Note**: API under customer domain is supported and recommended for white-label deployments. This differs from the internal/owner instance which uses `api.fewo.kolibri-visions.de`.

### Step-by-Step Procedure

#### Step 1: Provision VPS (HETZNER CLOUD UI)

**Goal**: Create a new dedicated VPS for the customer.

**Hetzner Cloud Console**:
1. Navigate to: https://console.hetzner.cloud/
2. Select project (or create new project for customer)
3. Click "Add Server"
4. Configuration:
   - **Location**: Select region closest to customer (e.g., Falkenstein, Nuremberg, Helsinki)
   - **Image**: Ubuntu 22.04 LTS (recommended) or Ubuntu 24.04 LTS
   - **Type**: 
     - **Starter**: CPX11 (2 vCPU, 2GB RAM) - for testing/small deployments
     - **Production**: CPX21 (3 vCPU, 4GB RAM) - recommended minimum
     - **High Load**: CPX31 (4 vCPU, 8GB RAM) - for high-traffic sites
   - **Networking**: 
     - Enable IPv4 and IPv6 (both recommended)
     - No additional networks required (unless customer has special requirements)
   - **Firewall**: 
     - Create firewall rule: Allow TCP 22 (SSH), 80 (HTTP), 443 (HTTPS)
     - Block all other inbound traffic
   - **SSH Keys**: Add your SSH public key for root access
   - **Name**: customer-vps-kunde1 (or similar descriptive name)
5. Click "Create & Buy Now"
6. Wait 1-2 minutes for provisioning
7. **Record VPS IP addresses** (IPv4 and IPv6) for DNS configuration

**Validation**:
```bash
# Test SSH access (from your local machine)
ssh root@<VPS_IPv4>
# Should connect successfully

# Check system info
uname -a
# Should show Ubuntu 22.04 or 24.04

# Check available resources
free -h
df -h
```

**Important**: Keep VPS IP addresses handy for Step 2 (DNS configuration).

#### Step 2: DNS Configuration (PLESK UI or DNS PROVIDER)

**Goal**: Point customer domains to the new VPS IP addresses.

**Recommended DNS Records** (using Plesk or customer DNS provider):

```dns
# Apex domain (A record for IPv4, AAAA for IPv6)
www.kunde1.de.       3600  IN  A      <VPS_IPv4>
www.kunde1.de.       3600  IN  AAAA   <VPS_IPv6>

# Admin subdomain
admin.kunde1.de.     3600  IN  A      <VPS_IPv4>
admin.kunde1.de.     3600  IN  AAAA   <VPS_IPv6>

# API subdomain
api.kunde1.de.       3600  IN  A      <VPS_IPv4>
api.kunde1.de.       3600  IN  AAAA   <VPS_IPv6>
```

**Alternative (CNAME for subdomains)**:
```dns
# If you prefer CNAME for subdomains (points to apex)
admin.kunde1.de.     3600  IN  CNAME  www.kunde1.de.
api.kunde1.de.       3600  IN  CNAME  www.kunde1.de.

# Note: Apex (www) must still use A/AAAA records
www.kunde1.de.       3600  IN  A      <VPS_IPv4>
www.kunde1.de.       3600  IN  AAAA   <VPS_IPv6>
```

**Plesk Configuration**:
1. Log in to Plesk: https://plesk.your-dns-server.com/
2. Navigate to: Domains → kunde1.de → DNS Settings
3. Add DNS records as shown above
4. Click "Apply" or "Update"
5. Wait for DNS propagation (typically 5-30 minutes, up to 24 hours for global propagation)

**Important Notes**:
- Use **lowercase** domain names (DNS is case-insensitive, but consistency helps)
- **NO trailing dot** in application configs (Plesk DNS editor may require it, but app does not)
- TTL 3600 (1 hour) is a safe default for production
- For testing, use TTL 300 (5 minutes) to allow faster changes

**Validation**:
```bash
# Check DNS propagation (wait 5-30 minutes after DNS changes)
dig www.kunde1.de A
dig www.kunde1.de AAAA
dig admin.kunde1.de A
dig api.kunde1.de A

# All should resolve to VPS IP addresses

# Quick test from multiple locations
nslookup www.kunde1.de 8.8.8.8  # Google DNS
nslookup www.kunde1.de 1.1.1.1  # Cloudflare DNS
```

**Pre-DNS Testing Option**: You can proceed with Steps 3-5 and use `pms_customer_vps_verify.sh` with `SERVER_IP` parameter to bypass DNS propagation (see Step 6).

#### Step 3: Install Coolify on Customer VPS (HOST-SERVER-TERMINAL)

**Goal**: Install Coolify as the deployment platform on the customer VPS.

**SSH to Customer VPS**:
```bash
ssh root@<VPS_IPv4>
```

**Install Coolify** (one-line installer):
```bash
# Run Coolify installer (official script)
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash

# Installation takes 5-10 minutes
# Follow prompts (typically defaults are OK)
```

**Post-Installation**:
```bash
# Verify Coolify is running
docker ps | grep coolify
# Should show multiple Coolify containers (coolify, postgres, redis, proxy)

# Get Coolify web UI URL
echo "Coolify UI: http://<VPS_IPv4>:8000"

# Get initial admin password (shown during installation, or reset if needed)
# First-time setup: Navigate to http://<VPS_IPv4>:8000 and create admin account
```

**Coolify Initial Setup** (COOLIFY UI):
1. Open browser: http://<VPS_IPv4>:8000
2. Create admin account (email + password)
3. Configure server settings:
   - **Server Name**: customer-vps-kunde1
   - **Server IP**: <VPS_IPv4>
   - **Wildcard Domain**: (leave empty for now)
4. Configure proxy (Traefik):
   - Coolify automatically installs Traefik as reverse proxy
   - No additional configuration needed at this stage

**Validation**:
```bash
# Check Coolify proxy (Traefik) is running
docker ps | grep coolify-proxy
# Should show coolify-proxy container

# Check Traefik logs (should show no errors)
docker logs coolify-proxy --tail 50

# Verify Docker network exists
docker network ls | grep coolify
# Should show 'coolify' network
```

**Important**: Record Coolify admin credentials securely (password manager recommended).

#### Step 4: Deploy Database Stack (COOLIFY UI + HOST-SERVER-TERMINAL)

**Goal**: Deploy Supabase (or standalone Postgres) for customer data.

**Option A: Supabase Self-Hosted (Recommended for Full Stack)**

**Coolify UI**:
1. Navigate to: Projects → Create New Project
2. Project Name: `kunde1-supabase`
3. Add Service → Docker Compose
4. Paste Supabase docker-compose.yml (from Supabase self-hosting docs)
5. Configure environment variables:
   - `POSTGRES_PASSWORD`: Generate strong password (save securely)
   - `JWT_SECRET`: Generate 32+ character secret (save securely)
   - `ANON_KEY`: Generate JWT with anon role (use Supabase JWT generator)
   - `SERVICE_ROLE_KEY`: Generate JWT with service_role (save securely)
6. Deploy → Start

**Option B: Standalone Postgres (Simpler, Database Only)**

**Coolify UI**:
1. Navigate to: Projects → Create New Project
2. Project Name: `kunde1-database`
3. Add Service → Postgres (from Coolify templates)
4. Configure:
   - `POSTGRES_DB`: `pms_kunde1`
   - `POSTGRES_USER`: `pms_user`
   - `POSTGRES_PASSWORD`: Generate strong password (save securely)
   - **Persistent Volume**: `/var/lib/postgresql/data` (ensure data persistence)
5. Deploy → Start

**Validation**:
```bash
# SSH to customer VPS
ssh root@<VPS_IPv4>

# For Supabase: Check all services are running
docker ps | grep supabase
# Should show: postgres, kong, auth, rest, realtime, storage, etc.

# For standalone Postgres: Check container is running
docker ps | grep postgres

# Test database connection
docker exec -it <postgres_container_id> psql -U <user> -d <database>
# Should connect successfully

# Run \dt to list tables (empty initially)
\dt

# Exit psql
\q
```

**Important**: 
- **Save DATABASE_URL** for backend configuration: `postgresql://<user>:<password>@<host>:<port>/<database>`
- **Save JWT_SECRET** (must match between Supabase/GoTrue and backend)
- For Supabase: Expose Kong API Gateway port (default 8000) internally only (no public access)

#### Step 5: Deploy Backend Stack (COOLIFY UI)

**Goal**: Deploy PMS backend API, worker, and admin UI on customer VPS.

**5a. Create Backend API Service (COOLIFY UI)**

1. Navigate to: Projects → Create New Project
2. Project Name: `kunde1-pms-backend`
3. Add Service → Docker Image or Git Repository
   - **Source**: Git repository (your PMS backend repo)
   - **Branch**: main (or specific release tag)
   - **Dockerfile Path**: `backend/Dockerfile`
4. Configure Domains:
   - Click "Add Domain"
   - Enter: `api.kunde1.de`
   - Enable HTTPS: ✅ (Let's Encrypt automatic)
5. Configure Traefik Labels (IMPORTANT):
   - Click "Labels" tab
   - Add custom label:
     - **Key**: `traefik.docker.network`
     - **Value**: `coolify`
   - Verify Host rule (auto-generated by Coolify):
     - `traefik.http.routers.<service>.rule=Host(\`api.kunde1.de\`)`
   - **Note**: Backticks in Host() rule are critical (not single quotes)
6. Configure Environment Variables:
   ```bash
   # Database
   DATABASE_URL=postgresql://pms_user:<password>@<postgres_host>:5432/pms_kunde1
   
   # JWT/Auth (must match Supabase/GoTrue)
   SUPABASE_JWT_SECRET=<jwt_secret_from_supabase>
   JWT_SECRET=<jwt_secret_from_supabase>
   JWT_AUDIENCE=authenticated
   
   # Redis/Celery
   REDIS_URL=redis://<redis_host>:6379/0
   CELERY_BROKER_URL=redis://<redis_host>:6379/0
   CELERY_RESULT_BACKEND=redis://<redis_host>:6379/1
   
   # Proxy Configuration
   TRUST_PROXY_HEADERS=true
   
   # Host Allowlist (IMPORTANT)
   ALLOWED_HOSTS=api.kunde1.de,admin.kunde1.de,www.kunde1.de
   
   # CORS Configuration
   CORS_ALLOWED_ORIGINS=https://www.kunde1.de,https://admin.kunde1.de
   
   # Environment
   ENVIRONMENT=production
   SOURCE_COMMIT=<git_commit_sha>  # Optional but recommended for tracking
   
   # Feature Flags (if applicable)
   MODULES_ENABLED=true
   ```
7. Deploy → Start
8. Monitor deployment logs (Coolify UI → Logs tab)

**5b. Create Worker Service (COOLIFY UI)**

1. Projects → kunde1-pms-backend → Add Service
2. **Source**: Same Git repository as backend
   - **Branch**: main
   - **Dockerfile Path**: `backend/Dockerfile` (or `backend/worker.Dockerfile` if separate)
   - **Command Override**: `celery -A app.celery_app worker -l info`
3. Configure Environment Variables:
   - Use **same environment variables** as backend API
   - No domain configuration needed (worker is internal only)
4. **No Traefik labels** needed (worker doesn't serve HTTP traffic)
5. Deploy → Start

**5c. Create Admin UI Service (COOLIFY UI)**

1. Projects → kunde1-pms-backend → Add Service (or separate project)
2. **Source**: Git repository (frontend/admin)
   - **Branch**: main
   - **Dockerfile Path**: `frontend/Dockerfile` (or appropriate path)
3. Configure Domains:
   - Add Domain: `admin.kunde1.de`
   - Enable HTTPS: ✅
4. Configure Traefik Labels:
   - Add: `traefik.docker.network=coolify`
5. Configure Environment Variables:
   ```bash
   # API endpoint (points to backend)
   NEXT_PUBLIC_API_URL=https://api.kunde1.de
   NEXT_PUBLIC_SUPABASE_URL=https://api.kunde1.de  # or Supabase Kong URL
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>
   
   # Environment
   NODE_ENV=production
   ```
6. Deploy → Start

**Validation**:
```bash
# Check all services are running
docker ps | grep kunde1
# Should show: backend, worker, admin

# Test backend health
curl https://api.kunde1.de/health
# Should return: {"status": "healthy"} or similar

# Test backend version
curl https://api.kunde1.de/api/v1/ops/version
# Should return JSON with service, source_commit, environment, etc.

# Test admin UI (browser)
# Open: https://admin.kunde1.de
# Should load admin interface (may show login screen)
```

**Common Failure: 503 Service Unavailable**

**Symptoms**: Curl returns 503 error or "no available server" message

**Possible Causes**:
1. **Invalid Traefik Host rule**: Backticks missing or escaped incorrectly
   - ✅ Correct: `Host(\`api.kunde1.de\`)`
   - ❌ Wrong: `Host('api.kunde1.de')` or `Host(api.kunde1.de)`
2. **Wrong Docker network**: Service not on `coolify` network
   - Fix: Add label `traefik.docker.network=coolify`
3. **Service not running**: Container crashed or failed to start
   - Check: `docker ps -a | grep kunde1`
   - Check logs: `docker logs <container_id>`
4. **Wrong port exposed**: Traefik trying to reach wrong service port
   - Fix: Add label `traefik.http.services.<service>.loadbalancer.server.port=8000`
5. **Firewall blocking**: VPS firewall blocking traffic
   - Check: `ufw status` (if UFW enabled)
   - Allow: `ufw allow 80/tcp && ufw allow 443/tcp`

**Troubleshooting Checklist**:
```bash
# 1. Verify Traefik can see the service
docker logs coolify-proxy 2>&1 | grep -i "kunde1"
# Should show backend service registration

# 2. Check service is on coolify network
docker inspect <container_id> | grep -i network
# Should include "coolify" network

# 3. Test service directly (bypass Traefik)
docker exec -it <backend_container> curl localhost:8000/health
# Should return healthy response

# 4. Check Traefik configuration
docker exec coolify-proxy cat /etc/traefik/traefik.toml
# Verify providers.docker.network = "coolify"

# 5. Restart Traefik if needed
docker restart coolify-proxy
```

#### Step 6: Run Database Migrations (HOST-SERVER-TERMINAL)

**Goal**: Apply database schema migrations to create tables and seed data.

**SSH to Customer VPS**:
```bash
ssh root@<VPS_IPv4>

# Get backend container ID
docker ps | grep kunde1.*backend
BACKEND_CONTAINER=<container_id>
```

**Apply Migrations** (using Alembic or custom migration tool):

**Option A: Alembic Migrations**:
```bash
# Run migrations inside backend container
docker exec -it $BACKEND_CONTAINER alembic upgrade head

# Verify migrations applied
docker exec -it $BACKEND_CONTAINER alembic current
# Should show current revision
```

**Option B: SQL Migrations (Supabase SQL Editor)**:

1. Navigate to Supabase UI (if using Supabase):
   - URL: http://<VPS_IPv4>:8000 (Supabase Kong Gateway, internal only)
   - Or use Supabase Studio if deployed
2. SQL Editor → New Query
3. Copy/paste migration files from `supabase/migrations/` (in order)
4. Execute each migration file
5. Verify tables created:
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public' 
   ORDER BY table_name;
   ```

**Option C: Manual Psql Migration**:
```bash
# Copy migration files to VPS
scp -r supabase/migrations/ root@<VPS_IPv4>:/tmp/

# SSH to VPS and run migrations
ssh root@<VPS_IPv4>

# Find postgres container
POSTGRES_CONTAINER=$(docker ps | grep postgres | awk '{print $1}')

# Apply migrations in order
for file in /tmp/migrations/*.sql; do
    echo "Applying $file..."
    docker exec -i $POSTGRES_CONTAINER psql -U <user> -d <database> < "$file"
done

# Verify schema
docker exec -it $POSTGRES_CONTAINER psql -U <user> -d <database> -c '\dt'
```

**Validation**:
```bash
# Check critical tables exist
docker exec -it $POSTGRES_CONTAINER psql -U <user> -d <database> -c "
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name IN (
    'agencies', 'users', 'properties', 'bookings', 
    'guests', 'audit_log', 'agency_domains'
);"
# Should return all critical tables
```

#### Step 7: Bootstrap Single-Tenant Data (SUPABASE SQL EDITOR or HOST-TERMINAL)

**Goal**: Create initial agency, admin user, and optional seed data for customer.

**Important**: Single-tenant deployment means **one agency per VPS**. The multi-tenant code remains enabled, but operationally there's only one agency.

**Bootstrap SQL** (run in Supabase SQL Editor or psql):

```sql
-- 1. Create customer agency
INSERT INTO agencies (id, name, created_at, updated_at)
VALUES (
    gen_random_uuid(),  -- Or use specific UUID for tracking
    'Kunde1 GmbH',      -- Customer company name
    NOW(),
    NOW()
)
RETURNING id;  -- Save this agency_id for next steps

-- Record agency_id from above (e.g., 'a1b2c3d4-...')

-- 2. Create admin user for customer
INSERT INTO users (id, agency_id, email, role, first_name, last_name, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    '<agency_id_from_step1>',
    'admin@kunde1.de',
    'admin',
    'Admin',
    'Kunde1',
    NOW(),
    NOW()
);

-- 3. (Optional) Map customer domain to agency
INSERT INTO agency_domains (agency_id, domain)
VALUES 
    ('<agency_id>', 'api.kunde1.de'),
    ('<agency_id>', 'admin.kunde1.de'),
    ('<agency_id>', 'www.kunde1.de')
ON CONFLICT (domain) DO NOTHING;

-- 4. (Optional) Seed a test property
INSERT INTO properties (id, agency_id, name, address, max_guests, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    '<agency_id>',
    'Test Property - Kunde1',
    'Teststraße 1, 12345 Berlin',
    4,
    NOW(),
    NOW()
);

-- Verify bootstrap
SELECT id, name FROM agencies;
SELECT id, email, role FROM users WHERE agency_id = '<agency_id>';
SELECT id, name FROM properties WHERE agency_id = '<agency_id>';
```

**Alternative: Bootstrap Script** (if available):
```bash
# SSH to VPS
ssh root@<VPS_IPv4>

# Run bootstrap script (if exists in your repo)
docker exec -it $BACKEND_CONTAINER python scripts/bootstrap_tenant.py \
    --agency-name "Kunde1 GmbH" \
    --admin-email "admin@kunde1.de" \
    --admin-password "<secure_password>"

# Script should output agency_id and admin credentials
```

**Validation**:
```sql
-- Verify agency exists
SELECT * FROM agencies WHERE name = 'Kunde1 GmbH';

-- Verify admin user exists
SELECT * FROM users WHERE email = 'admin@kunde1.de';

-- Verify domain mapping (if used)
SELECT * FROM agency_domains WHERE domain LIKE '%kunde1.de%';
```

**Important**: 
- **Save agency_id** for verification step
- **Save admin credentials** securely (share with customer via secure channel)
- If using Supabase Auth, create user in GoTrue as well (via Supabase UI or API)

#### Step 8: Configure SSL/TLS Certificates (COOLIFY UI - Automatic)

**Goal**: Ensure all customer domains have valid HTTPS certificates.

**Coolify Automatic Certificate Provisioning**:

Coolify automatically provisions Let's Encrypt certificates for all domains configured in Step 5. No manual intervention required if:
1. DNS is properly configured (domains resolve to VPS IP)
2. Ports 80 and 443 are open on VPS firewall
3. Domains are added to Coolify service configuration with HTTPS enabled

**Validation**:
```bash
# Test HTTPS for all customer domains
curl -I https://api.kunde1.de
curl -I https://admin.kunde1.de
curl -I https://www.kunde1.de

# All should return HTTP 200 or 30x (not certificate errors)

# Check certificate details
echo | openssl s_client -connect api.kunde1.de:443 -servername api.kunde1.de 2>/dev/null | openssl x509 -noout -dates -issuer
# Should show Let's Encrypt issuer and valid dates
```

**Manual Certificate Check (Coolify UI)**:
1. Navigate to: Project → Service → Domains tab
2. Each domain should show: ✅ HTTPS Enabled, Certificate Valid
3. Expiry date should be ~90 days from now (Let's Encrypt default)

**Troubleshooting Certificate Issues**:

**Symptom**: Certificate provisioning fails or self-signed certificate error

**Possible Causes**:
1. **DNS not propagated**: Let's Encrypt ACME challenge fails
   - Fix: Wait for DNS TTL expiry (1-24 hours) or use lower TTL
   - Verify: `dig api.kunde1.de` should resolve to VPS IP
2. **Port 80 blocked**: ACME HTTP-01 challenge requires port 80
   - Fix: Ensure VPS firewall allows port 80 (ufw allow 80/tcp)
3. **Domain not added in Coolify**: Certificate not requested
   - Fix: Add domain in Coolify service config, enable HTTPS
4. **Rate limit hit**: Let's Encrypt has rate limits (50 certs per domain per week)
   - Fix: Wait 1 week or use staging environment for testing

**Certificate Renewal**:
- Let's Encrypt certificates expire after 90 days
- Coolify automatically renews certificates at 60 days (no manual intervention)
- Monitor certificate expiry via monitoring tools (UptimeRobot, Pingdom)

#### Step 9: Verification (HOST-SERVER-TERMINAL or LOCAL)

**Goal**: Verify customer VPS is ready for production traffic using automated verification script.

**Run Verification Script**:

**Option A: Post-DNS Verification** (after DNS propagation):
```bash
# From your local machine or CI/CD
API_BASE_URL=https://api.kunde1.de \
./backend/scripts/pms_customer_vps_verify.sh
```

**Option B: Pre-DNS Verification** (before DNS propagation, recommended during setup):
```bash
# Use direct IP to bypass DNS
API_BASE_URL=https://api.kunde1.de \
SERVER_IP=<VPS_IPv4> \
./backend/scripts/pms_customer_vps_verify.sh
```

**Option C: Full Verification** (with commit check and CORS):
```bash
API_BASE_URL=https://api.kunde1.de \
ADMIN_BASE_URL=https://admin.kunde1.de \
PUBLIC_BASE_URL=https://www.kunde1.de \
EXPECT_COMMIT=caabb0b \
TEST_ORIGIN=https://www.kunde1.de \
./backend/scripts/pms_customer_vps_verify.sh
```

**Expected Output** (Success):
```
ℹ Verifying customer VPS deployment: https://api.kunde1.de

ℹ Check 1/5: GET /health (liveness)
✅ Health check passed (HTTP 200)

ℹ Check 2/5: GET /health/ready (readiness)
✅ Readiness check passed (HTTP 200)

ℹ Check 3/5: GET /api/v1/ops/version (deployment metadata)
✅ Version endpoint accessible
ℹ   Environment: production
ℹ   API Version: 0.1.0
ℹ   Source Commit: caabb0b...
✅ Source commit matches expected prefix: caabb0b

ℹ Check 4/5: Public router preflight
✅ Public router mounted (endpoint returned HTTP 422, not 404)

ℹ Check 5/5: CORS preflight (Origin: https://www.kunde1.de)
✅ CORS preflight passed (Allow-Origin: https://www.kunde1.de)

✅ All checks passed - customer VPS is ready for production traffic
ℹ Admin UI: https://admin.kunde1.de
ℹ Public Site: https://www.kunde1.de
```

**If Verification Fails**:
- Review error messages in script output (actionable hints provided)
- Check troubleshooting sections above for specific error codes
- Common issues: DNS not propagated, CORS misconfiguration, missing env vars

**Optional: Run Smoke Tests** (additional validation):
```bash
# Set up environment for smoke tests
export HOST=https://api.kunde1.de
export JWT_TOKEN=<admin_jwt_token>  # Generate via auth endpoint
export AGENCY_ID=<agency_id_from_bootstrap>

# Run public booking smoke test
./backend/scripts/pms_direct_booking_public_smoke.sh

# Run pricing quote smoke test (if pricing module enabled)
./backend/scripts/pms_pricing_quote_smoke.sh
```

#### Step 10: Customer Handoff (DOCUMENTATION)

**Goal**: Provide customer with access credentials and documentation.

**Handoff Package** (secure delivery via encrypted email or password manager):

1. **Access URLs**:
   - Admin UI: https://admin.kunde1.de
   - API Docs: https://api.kunde1.de/docs (FastAPI auto-generated docs)
   - Health Check: https://api.kunde1.de/health (for customer monitoring)

2. **Admin Credentials**:
   - Email: admin@kunde1.de
   - Password: <secure_password_from_bootstrap>
   - Role: admin (full access)

3. **Database Access** (optional, only if customer needs direct access):
   - Host: <VPS_IP> (not publicly exposed, VPN or SSH tunnel required)
   - Database: pms_kunde1
   - User: pms_user
   - Password: <postgres_password>
   - **Security Note**: Database should NOT be publicly accessible

4. **VPS Access** (optional, only for technical customers):
   - SSH: root@<VPS_IP> (add customer SSH key if requested)
   - Coolify UI: http://<VPS_IP>:8000 (create separate Coolify admin if needed)

5. **Support Contacts**:
   - Technical Support: support@your-company.com
   - Emergency Hotline: +49 xxx xxx xxxx (if applicable)

6. **Documentation Links**:
   - API Documentation: https://api.kunde1.de/docs
   - Admin User Guide: [Link to customer-facing docs]
   - FAQ: [Link to FAQ]

**Post-Handoff Checklist**:
- ✅ Customer can log in to admin UI
- ✅ Customer can create test booking (if applicable)
- ✅ Customer understands how to add properties/users
- ✅ Customer has emergency contact info
- ✅ Monitoring set up for customer VPS (see Step 11)

#### Step 11: Monitoring and Maintenance (OPTIONAL)

**Goal**: Set up monitoring and establish maintenance schedule for customer VPS.

**Uptime Monitoring** (recommended):
- Use UptimeRobot, Pingdom, or similar service
- Monitor endpoints:
  - https://api.kunde1.de/health (should return 200)
  - https://admin.kunde1.de (should return 200)
  - https://www.kunde1.de (should return 200)
- Alert on: HTTP 500/503 errors, downtime >5 minutes, certificate expiry

**Resource Monitoring** (Coolify built-in):
- Coolify UI → Server → Metrics
- Monitor: CPU usage, RAM usage, disk space
- Set up alerts: >80% CPU for 10+ minutes, >90% RAM, <10% disk free

**Certificate Expiry Monitoring**:
- Let's Encrypt certificates auto-renew at 60 days
- Set up alert at 30 days (if auto-renewal fails)
- Check manually: `openssl s_client -connect api.kunde1.de:443 -servername api.kunde1.de | openssl x509 -noout -dates`

**Backup Strategy**:
- Database backups (automated):
  - Coolify can enable automatic Postgres backups
  - Configure: Project → Service → Backups tab
  - Retention: 7 daily, 4 weekly, 12 monthly (adjust based on customer SLA)
- VPS snapshots (Hetzner):
  - Hetzner Cloud → Server → Snapshots
  - Create weekly snapshot (manual or via Hetzner API)
  - Keep 4 snapshots (1 month history)

**Update Schedule**:
- **Security Patches**: Apply within 7 days of release (OS + Docker images)
- **Application Updates**: Monthly or quarterly (coordinate with customer)
- **Database Migrations**: Test in staging before applying to production

**Maintenance Window**:
- Recommended: Weekly maintenance window (e.g., Sunday 2-4 AM local time)
- Notify customer 48 hours in advance for major updates
- Use Coolify zero-downtime deployments where possible

### Rollback Procedure

**If deployment fails or needs to be reverted**:

**1. Revert Backend Deployment (COOLIFY UI)**:
- Navigate to: Project → Service → Deployments tab
- Click "Rollback" next to previous successful deployment
- Wait for rollback to complete (2-5 minutes)
- Verify: `curl https://api.kunde1.de/api/v1/ops/version` (should show old commit)

**2. Revert Database Migrations (HOST-SERVER-TERMINAL)**:
```bash
# SSH to VPS
ssh root@<VPS_IPv4>

# Downgrade migrations (Alembic)
docker exec -it $BACKEND_CONTAINER alembic downgrade -1

# Or restore from database backup
docker exec -i $POSTGRES_CONTAINER psql -U <user> -d <database> < /backups/backup_YYYYMMDD.sql
```

**3. Revert Environment Variables (COOLIFY UI)**:
- Project → Service → Environment tab
- Restore previous values (Coolify keeps history)
- Redeploy service

**4. Revert DNS (if needed)**:
- Plesk → Domains → DNS Settings
- Remove or update DNS records
- Wait for TTL expiry (or flush local DNS cache)

**5. Remove VPS (if catastrophic failure)**:
- Hetzner Cloud → Server → Delete
- Update DNS to remove customer domains
- Notify customer and reschedule deployment

**Rollback is safe and tested** - practice rollback procedure during staging deployments.

### Troubleshooting Guide

#### Problem: Backend Returns 403 "Host not allowed"

**Symptom**: API requests return HTTP 403 with `{"detail": "Host not allowed: api.kunde1.de"}`

**Root Cause**: Customer domain not in ALLOWED_HOSTS environment variable

**Solution**:
1. Coolify UI → Project → Backend Service → Environment tab
2. Update ALLOWED_HOSTS: `api.kunde1.de,admin.kunde1.de,www.kunde1.de`
3. Redeploy service (Coolify auto-restarts on ENV change)
4. Verify: `curl https://api.kunde1.de/health` (should return 200)

#### Problem: CORS Errors in Browser Console

**Symptom**: Browser shows "CORS policy blocked" errors when accessing API from admin UI

**Root Cause**: Admin UI origin not in CORS_ALLOWED_ORIGINS

**Solution**:
1. Coolify UI → Backend Service → Environment tab
2. Update CORS_ALLOWED_ORIGINS: `https://admin.kunde1.de,https://www.kunde1.de`
3. Ensure TRUST_PROXY_HEADERS=true (for correct Origin detection)
4. Redeploy service
5. Test CORS: `curl -X OPTIONS https://api.kunde1.de/api/v1/public/booking-requests -H "Origin: https://admin.kunde1.de" -i`

#### Problem: Database Connection Refused

**Symptom**: Backend logs show "Connection refused" or "Database unavailable"

**Root Cause**: DATABASE_URL incorrect or database container not running

**Solution**:
1. Verify database container is running: `docker ps | grep postgres`
2. If stopped, start via Coolify UI or `docker start <container_id>`
3. Check DATABASE_URL format: `postgresql://user:password@host:5432/database`
4. For internal Docker networking, use container name as host (e.g., `postgres-kunde1`)
5. Test connection: `docker exec -it $BACKEND_CONTAINER curl postgres-kunde1:5432` (should connect)

#### Problem: Worker Not Processing Jobs

**Symptom**: Celery tasks stuck in pending state, never processed

**Root Cause**: Worker container not running or Redis connection failed

**Solution**:
1. Check worker container: `docker ps | grep worker`
2. Check worker logs: `docker logs <worker_container_id>`
3. Verify REDIS_URL in worker environment matches backend
4. Verify Redis container running: `docker ps | grep redis`
5. Restart worker: Coolify UI → Worker Service → Restart

#### Problem: Let's Encrypt Certificate Provisioning Fails

**Symptom**: HTTPS returns self-signed certificate error or ERR_CERT_AUTHORITY_INVALID

**Root Cause**: ACME challenge failed (DNS not propagated, port 80 blocked, rate limit)

**Solution**:
1. Verify DNS propagation: `dig api.kunde1.de` (should resolve to VPS IP)
2. Verify port 80 open: `curl http://api.kunde1.de/.well-known/acme-challenge/test` (should not timeout)
3. Check Coolify proxy logs: `docker logs coolify-proxy | grep -i acme`
4. If rate limited, wait 1 week or use Let's Encrypt staging for testing
5. Manual retry: Coolify UI → Service → Domains → Re-provision Certificate

### Related Scripts

- **pms_customer_vps_verify.sh**: Automated verification script for customer VPS deployments
- **pms_verify_deploy.sh**: General deployment verification (commit matching, module checks)
- **pms_direct_booking_public_smoke.sh**: Public booking flow smoke test
- **pms_pricing_quote_smoke.sh**: Pricing quote smoke test

### Related Documentation

- [Customer Domain Onboarding SOP](runbook.md#customer-domain-onboarding-sop) - For multi-tenant domain mapping
- [Database Schema](../../supabase/migrations/) - Database structure and migrations
- [API Documentation](../../backend/app/api/) - API endpoints and business logic
- [Project Status](../project_status.md) - Implementation status and verification criteria

### Maintenance

**Regular Tasks**:
- Weekly: Check uptime monitoring alerts
- Monthly: Review resource usage (CPU, RAM, disk)
- Quarterly: Review and rotate database backups
- Annually: Review and update SSL/TLS certificates (auto-renew, but verify)

**Security Hardening** (recommended post-deployment):
- Enable UFW firewall: `ufw enable && ufw allow 22,80,443/tcp`
- Disable root SSH login (use key-based auth only)
- Set up fail2ban for SSH brute-force protection
- Regular security updates: `apt update && apt upgrade -y`
- Database access: Only via SSH tunnel (no public exposure)

**Cost Optimization**:
- Monitor VPS usage: Right-size VPS based on actual load
- Consider reserved instances for long-term customers (Hetzner discounts)
- Archive old backups to object storage (Hetzner S3-compatible storage)


---

## Owner Portal O1

**Overview:** Read-only owner portal MVP with staff tools for owner profile management and property assignment.

**Purpose:** Allow property owners to view their properties and bookings through authenticated web UI, while staff (manager/admin) can create owner profiles and assign properties to owners.

**Architecture:**
- **Database**: `owners` table maps Supabase auth.users to owner profiles with agency scoping
- **RBAC**: 
  - Staff endpoints require manager/admin role (via `require_roles("manager", "admin")`)
  - Owner endpoints require `get_current_owner()` dependency (verifies auth_user_id + agency_id + is_active)
- **Property Ownership**: `properties.owner_id` FK references `owners.id`
- **Tenant Isolation**: All queries scoped by agency_id from JWT claims

**UI Routes:**
- `/owner` - Owner portal page (owner-only, lists properties + bookings)

**API Endpoints:**

Staff (manager/admin):
- `GET /api/v1/owners?active=&limit=&offset=` - List owner profiles
- `POST /api/v1/owners` - Create owner profile (requires auth_user_id)
- `PATCH /api/v1/owners/{id}` - Update owner profile (email, names, is_active)
- `PATCH /api/v1/properties/{id}/owner` - Assign/unassign property owner

Owner-only:
- `GET /api/v1/owner/properties?limit=&offset=` - List owned properties
- `GET /api/v1/owner/bookings?property_id=&limit=&offset=` - List bookings for owned properties

**Database Tables:**
- `owners` - Owner profiles mapped to auth users with agency scoping
- `properties.owner_id` - FK to owners.id (NULL = agency-owned, non-NULL = owner-assigned)

**Migration:** `20260109000000_add_owners_table.sql`

**Verification Commands:**

```bash
# [HOST-SERVER-TERMINAL] Pull latest code
cd /data/repos/pms-webapp
git fetch origin main && git reset --hard origin/main

# [HOST-SERVER-TERMINAL] Optional: Verify deploy after Coolify redeploy
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
./backend/scripts/pms_verify_deploy.sh

# [HOST-SERVER-TERMINAL] Run owner portal smoke test
export HOST="https://api.fewo.kolibri-visions.de"
export MANAGER_JWT_TOKEN="<<<manager/admin JWT>>>"
export OWNER_JWT_TOKEN="<<<owner user JWT>>>"
export OWNER_AUTH_USER_ID="<<<Supabase auth.users.id for owner>>>"
# Optional:
# export PROPERTY_ID="23dd8fda-59ae-4b2f-8489-7a90f5d46c66"
# export AGENCY_ID="ffd0123a-10b6-40cd-8ad5-66eee9757ab7"
./backend/scripts/pms_owner_portal_smoke.sh
echo "rc=$?"

# Expected output: All 5 tests pass, rc=0
```

**Common Issues:**

### Owner Endpoints Return 403 (Not Registered)

**Symptom:** Owner user gets 403 Forbidden when accessing `/api/v1/owner/properties` or `/api/v1/owner/bookings`. Error message: "Access denied: user is not registered as an owner".

**Root Cause:** User's auth_user_id (JWT sub) is not mapped to an owner profile in the `owners` table.

**How to Debug:**
```bash
# Check JWT sub claim (auth_user_id)
echo $OWNER_JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq '.sub'
# Example output: "550e8400-e29b-41d4-a716-446655440000"

# Check if owner profile exists
psql $DATABASE_URL -c "SELECT id, auth_user_id, is_active FROM owners WHERE auth_user_id = '550e8400-e29b-41d4-a716-446655440000';"

# Check agency_id matches JWT claim
echo $OWNER_JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq '.agency_id'
```

**Solution:**
- Have a manager/admin create owner profile: `POST /api/v1/owners` with `auth_user_id` matching JWT sub
- Ensure `is_active=true` in owners table: `UPDATE owners SET is_active = true WHERE auth_user_id = '...'`
- Verify JWT contains correct `agency_id` claim matching owner's agency

### Owner Sees No Properties (Empty List)

**Symptom:** Owner successfully accesses `/api/v1/owner/properties` but receives empty array `[]`.

**Root Cause:** No properties have `owner_id` set to this owner's ID.

**How to Debug:**
```bash
# Get owner ID from auth_user_id
psql $DATABASE_URL -c "SELECT id FROM owners WHERE auth_user_id = '550e8400-e29b-41d4-a716-446655440000';"
# Example output: "660e8400-e29b-41d4-a716-446655440001"

# Check if any properties assigned
psql $DATABASE_URL -c "SELECT id, name, owner_id FROM properties WHERE owner_id = '660e8400-e29b-41d4-a716-446655440001';"
```

**Solution:**
- Have manager/admin assign property: `PATCH /api/v1/properties/{property_id}/owner` with `{"owner_id": "660e8400-..."}`
- Verify property belongs to same agency as owner

### Staff Endpoint Accessible by Owners (RBAC Bypass)

**Symptom:** Owner can access `GET /api/v1/owners` (should return 403).

**Root Cause:** Missing `require_roles("manager", "admin")` dependency on staff endpoints.

**How to Debug:**
```bash
# Test staff endpoint with owner token
curl -X GET "$HOST/api/v1/owners?limit=10" \
  -H "Authorization: Bearer $OWNER_JWT_TOKEN"

# Should return 403, not 200
```

**Solution:**
- Ensure all staff endpoints use `_role_check=Depends(require_roles("manager", "admin"))`
- Verify JWT role claim: `echo $OWNER_JWT_TOKEN | cut -d'.' -f2 | base64 -d | jq '.role'` (should be "owner", not "manager"/"admin")

### Owner Can See Other Owners' Properties

**Symptom:** Owner sees properties not assigned to them.

**Root Cause:** Missing `WHERE properties.owner_id = $owner_id` filter in owner endpoints.

**How to Debug:**
```bash
# Check query in backend/app/api/routes/owners.py
# Line ~335: list_owner_properties query must filter by owner_id

# Verify properties returned match owner_id
curl -X GET "$HOST/api/v1/owner/properties" \
  -H "Authorization: Bearer $OWNER_JWT_TOKEN" | jq '.[].id'

psql $DATABASE_URL -c "SELECT owner_id FROM properties WHERE id IN (...);"
```

**Solution:**
- Verify query filters: `WHERE owner_id = $1 AND agency_id = $2`
- Ensure get_current_owner() correctly returns owner profile with ID

### Migration Fails (FK Constraint Violation)

**Symptom:** Migration `20260109000000_add_owners_table.sql` fails with FK constraint error on `properties.owner_id`.

**Root Cause:** Existing `properties.owner_id` values reference `auth.users.id` but migration tries to FK to `owners.id`.

**How to Debug:**
```bash
# Check existing owner_id values
psql $DATABASE_URL -c "SELECT id, owner_id FROM properties WHERE owner_id IS NOT NULL LIMIT 10;"

# Check if those owner_id values exist in auth.users
psql $DATABASE_URL -c "SELECT id FROM auth.users WHERE id IN (...);"
```

**Solution:**
- Before adding FK, clear invalid owner_id values: `UPDATE properties SET owner_id = NULL WHERE owner_id NOT IN (SELECT id FROM owners);`
- Or manually migrate existing auth.users to owners table first
- Then re-run migration to add FK constraint

---
