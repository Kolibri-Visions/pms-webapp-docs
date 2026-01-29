# Channel Manager Operations

**When to use:** Redis/Celery setup, worker configuration, sync troubleshooting, Channel Manager error handling.

---

## Table of Contents

- [Redis + Celery Worker Setup](#redis--celery-worker-setup-channel-manager)
- [Quick Smoke Test](#quick-smoke-5-minutes)
- [Deep Diagnostics](#deep-diagnostics-1530-minutes)
- [Celery Worker (pms-worker-v2)](#celery-worker-pms-worker--pms-worker-v2)
- [Error Handling & Retry Logic](#channel-manager-error-handling--retry-logic)

---

## Golden Commands

```bash
# Check health (Redis + Celery)
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq '.components'

# Ping Celery workers
docker exec pms-backend celery -A app.channel_manager.core.sync_engine:celery_app \
  --broker "$CELERY_BROKER_URL" inspect ping -t 3

# Test Redis connection
docker exec pms-backend python3 -c "import redis; import os; r=redis.from_url(os.environ['REDIS_URL']); print(r.ping())"

# Check worker logs
docker logs pms-worker-v2 --tail 50 | grep "ready"

# Trigger manual sync
curl -X POST "https://api.fewo.kolibri-visions.de/api/v1/channel-connections/$CID/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sync_type":"full"}'
```

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

## Quick Smoke (5 minutes)

**Purpose:** Rapid health check after Redis/Celery deployment or configuration changes.

**Prerequisites:**

Check in **Coolify UI**:
- ✅ `pms-backend` deployed and running (green status)
- ✅ `pms-worker` deployed and running (green status)
- ✅ `coolify-redis` service running
- ✅ Required environment variables set (see [Required Environment Variables](#required-environment-variables))

**Execution Location:** HOST-SERVER-TERMINAL (SSH to host server)

### Step 1: Load Environment

```bash
# Load environment file
source /root/pms_env.sh

# Verify required variables are set
echo "SB_URL: ${SB_URL:0:30}..."
echo "EMAIL: $EMAIL"
```

### Step 2: Get JWT Token

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

### Step 3: Check Health Endpoint

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

### Step 4: Get Channel Connection ID

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

### Step 5: Trigger Manual Sync

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

### Step 6: Check Sync Logs

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

## Deep Diagnostics (15–30 minutes)

**Purpose:** Comprehensive troubleshooting for Redis, Celery, and Channel Manager issues.

**When to use:**
- Quick Smoke fails
- Persistent connection errors
- Task execution failures
- After configuration changes

---

### Common HTTP Responses Reference

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

### Redis Connection Diagnostics

**Execution Location:** HOST-SERVER-TERMINAL

#### 1. Get Redis Password (requirepass)

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

#### 2. Test Redis Connection

```bash
# Test with raw password
redis-cli -h coolify-redis -a "$REDIS_PASS" ping
# Expected output: PONG

# If you get "Authentication required":
# - Password is wrong
# - Redis requirepass not set
# - Network connectivity issue
```

#### 3. Verify Password Encoding

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

#### 4. Test Connection from Backend Container

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

### Celery Worker Diagnostics

**Execution Location:** HOST-SERVER-TERMINAL

#### 1. Verify Worker Container Exists

```bash
# Check if worker container is running
docker ps -a | egrep -i 'pms-worker|celery|worker'

# Expected: pms-worker container with "Up" status
# If "Exited": worker crashed - check logs
```

#### 2. Check Worker Logs for Tasks

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

#### 3. Test Celery Connection from Backend

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

#### 4. Check Active Workers and Registered Tasks

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

### Coolify / Nixpacks Quirks

#### Start Command Quoting Issues

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

#### COOLIFY_URL Null Issue

**Symptom:** Build fails with "COOLIFY_URL is null" or similar.

**Workaround:**
```bash
# Add to Environment Variables (build + runtime)
COOLIFY_URL=https://coolify.example.com
# Or any non-empty string - value may not matter for worker
```

---

### Database Connection Diagnostics

#### DNS Flapping After Deploy

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

#### Network Configuration

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

#### Database URL Verification

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

### Worker Configuration Checklist

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

### Special Characters in Passwords

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

### Execution Location Quick Reference

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

### Required Environment Variables (Worker)

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

### Verification Checklist (Worker)

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

### Common Worker Issues & Troubleshooting

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
