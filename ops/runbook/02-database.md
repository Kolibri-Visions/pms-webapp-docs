# Database Operations

**When to use:** Database connectivity issues, schema migrations, pool problems, degraded mode troubleshooting.

---

## Table of Contents

- [DB DNS / Degraded Mode](#db-dns--degraded-mode)
- [Schema Drift](#schema-drift)
- [DB Migrations (Production)](#db-migrations-production)

---

## Golden Commands

```bash
# Check database health
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq '.components.db'

# Check pool status
docker logs $(docker ps -q -f name=pms-backend) 2>&1 | grep "pool created successfully"

# Check migration status
bash backend/scripts/ops/apply_supabase_migrations.sh --status

# Apply pending migrations
export CONFIRM_PROD=1
bash backend/scripts/ops/apply_supabase_migrations.sh
```

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

## Data Hygiene

### Legacy bookings.cancelled_by Strings (host/guest)

**Symptom**: The `public.bookings.cancelled_by` column contains non-UUID string values like `'host'` or `'guest'` instead of proper user UUIDs.

**Root Cause**: Early legacy data stored the cancellation actor as a string descriptor (`'host'` or `'guest'`) before the schema standardized to UUIDs referencing `auth.users.id`.

**Impact**: 
- Data inconsistency warnings in logs
- Potential validation errors when querying cancelled bookings
- Foreign key or JOIN operations may fail if code expects UUIDs

**Verification (before cleanup)**:
```sql
-- Count non-UUID values in cancelled_by column
SELECT count(*) FILTER (
  WHERE cancelled_by IS NOT NULL
    AND substring(cancelled_by from '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}') IS NULL
) AS cancelled_by_non_uuid
FROM public.bookings;

-- List actual non-UUID values
SELECT DISTINCT cancelled_by
FROM public.bookings
WHERE cancelled_by IS NOT NULL
  AND substring(cancelled_by from '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}') IS NULL;
```

**Fix (transaction-safe)**:
```sql
BEGIN;

-- Normalize legacy string values to NULL
-- We do NOT attempt to invent user identities for legacy data
UPDATE public.bookings
  SET cancelled_by = NULL
  WHERE cancelled_by IN ('host', 'guest');

COMMIT;
```

**Verification (after cleanup)**:
```sql
-- Should return 0
SELECT count(*) FILTER (
  WHERE cancelled_by IS NOT NULL
    AND substring(cancelled_by from '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}') IS NULL
) AS cancelled_by_non_uuid
FROM public.bookings;
```

**PROD Remediation (2026-01-12)**:
- **Before**: 27 rows with legacy values (`host`=26, `guest`=1)
- **After**: 0 rows with non-UUID values
- **Action**: Applied UPDATE transaction, set legacy values to NULL
- **Impact**: No functional impact; cancelled_by is nullable and optional metadata

**Note**: This cleanup does not affect booking status or other fields. The `cancelled_at` timestamp and `cancellation_reason` fields (if populated) remain intact and provide cancellation context.

---


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

