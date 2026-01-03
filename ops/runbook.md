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

### 2. JWT/Auth Failures (401 Invalid Token / 403 Not Authenticated)

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
triggered → queued → running → success
                              ↘ failed
                              ↘ cancelled
```

**Status Descriptions:**

| Status | Description | Updated By |
|--------|-------------|------------|
| `triggered` | Sync request received, log created | API endpoint |
| `queued` | Task queued in Celery | Celery broker |
| `running` | Task execution started | Celery worker |
| `success` | Task completed successfully | Celery worker |
| `failed` | Task failed after all retries | Celery worker |
| `cancelled` | Task manually cancelled | Manual intervention |

---

### Querying Sync Logs

**Via API:**
```bash
# Get last 50 logs for connection
curl https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?limit=50 \
  -H "Authorization: Bearer TOKEN"

# Get logs with pagination
curl https://api.your-domain.com/api/v1/channel-connections/{id}/sync-logs?limit=20&offset=40 \
  -H "Authorization: Bearer TOKEN"
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

**Full Documentation**: `/app/scripts/README.md` (in container)

### Other Resources

- **Inventory Contract** (Single Source of Truth): `/app/docs/domain/inventory.md` (date semantics, API contracts, edge cases, DB guarantees, test evidence)
- **Inventory & Availability Rules**: `/app/docs/database/exclusion-constraints.md` (conflict rules, EXCLUSION constraints, overlap prevention)
- **Modular Monolith Architecture**: `/app/docs/architecture/modules.md` (module system, registry, dependency management)
- **Architecture Docs**: `/app/docs/architecture/` (in container)
- **Supabase Dashboard**: Check database health, logs, network
- **Coolify Dashboard**: Application logs, environment variables, networks

---

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

---

## Change Log

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
