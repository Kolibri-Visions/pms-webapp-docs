# Deployment Operations

**When to use:** Deploying code changes, rollback procedures, Coolify configuration, TLS certificate issues.

---

## Table of Contents

- [Deploy Gating (Docs-Only Change Detection)](#deploy-gating-docs-only-change-detection)
- [Deployment Process](#deployment-process)
- [Coolify Auto-Deploy Configuration](#coolify-auto-deploy-configuration)
- [Rollback Procedure](#rollback-procedure)
- [Common Deployment Issues](#common-deployment-issues)
- [TLS Certificate Issues](#tls-admin-subdomain-shows-traefik-default-cert-lets-encrypt-missing)

---

## Golden Commands

```bash
# Check deployment health
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq .

# Check if deploy needed (docs-only detection)
./backend/scripts/ops/deploy_should_run.sh HEAD~1..HEAD

# Verify git commits match after deploy
BACKEND=$(docker exec pms-backend git rev-parse HEAD)
WORKER=$(docker exec pms-worker git rev-parse HEAD)
[ "$BACKEND" = "$WORKER" ] && echo "✓ Commits match" || echo "✗ MISMATCH"

# Check TLS certificate
echo | openssl s_client -connect api.fewo.kolibri-visions.de:443 \
  -servername api.fewo.kolibri-visions.de 2>/dev/null \
  | openssl x509 -noout -subject -issuer
```

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

## Coolify Auto-Deploy Configuration

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

## Rollback Procedure

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

## Common Deployment Issues

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

## TLS: Admin Subdomain Shows TRAEFIK DEFAULT CERT (Let's Encrypt Missing)

**Purpose:** Diagnose and fix admin.fewo.kolibri-visions.de (or other subdomains) serving Traefik's default certificate instead of a valid Let's Encrypt certificate.

### Symptoms

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

### Root Causes

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

### Diagnosis Steps

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

### Fix Steps (Coolify UI)

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

### Verification

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

### Related Issues

- If certificate still shows TRAEFIK DEFAULT CERT after fix:
  - Check DNS: `nslookup admin.fewo.kolibri-visions.de` (must resolve to server IP)
  - Check firewall: Port 443 must be open
  - Check Traefik ACME logs for challenge failures
- If router rule still invalid:
  - Review Traefik documentation: https://doc.traefik.io/traefik/routing/routers/
  - Test rule syntax in isolation before deploying

---

## Public Website SSL Shows TRAEFIK DEFAULT CERT (certresolver Label Typo)

**Purpose:** Diagnose and fix fewo.kolibri-visions.de (public website) serving Traefik's default self-signed certificate instead of a valid Let's Encrypt certificate, specifically when caused by malformed Docker label keys (e.g., trailing whitespace).

### Symptoms

**Browser:**
- Certificate warning: "Your connection is not private" / "NET::ERR_CERT_AUTHORITY_INVALID"
- Certificate shown as self-signed with subject/issuer: `CN=TRAEFIK DEFAULT CERT`
- Site content loads (200 OK) but SSL verification fails

**CLI Verification (HOST-SERVER-TERMINAL):**
```bash
# Check certificate for public website
openssl s_client -servername fewo.kolibri-visions.de \
  -connect fewo.kolibri-visions.de:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates

# Output with TRAEFIK DEFAULT CERT (PROBLEM):
# subject=CN = TRAEFIK DEFAULT CERT
# issuer=CN = TRAEFIK DEFAULT CERT
# notBefore=Jan  1 00:00:00 2024 GMT
# notAfter=Jan  1 00:00:00 2025 GMT

# After fix (Let's Encrypt):
# subject=CN = fewo.kolibri-visions.de
# issuer=C = US, O = Let's Encrypt, CN = R13
# notBefore=Jan 12 21:00:00 2026 GMT
# notAfter=Apr 12 21:00:00 2026 GMT

# Quick test: curl without -k should work after fix
curl -I https://fewo.kolibri-visions.de
# Expected: HTTP/2 200 (no certificate errors)
```

### Root Cause: Malformed certresolver Label Key

**Most Common:** Docker label key has trailing whitespace or typo, preventing Traefik from parsing the `certresolver` directive.

**Example of BAD label (trailing space before `=`):**
```
traefik.http.routers.public-website-https.tls.certresolver =letsencrypt
                                                            ↑
                                                     (space here)
```

**Correct label (no whitespace):**
```
traefik.http.routers.public-website-https.tls.certresolver=letsencrypt
```

**Traefik Behavior:**
- Traefik v3 logs: `"field not found, node: certresolver"` when it cannot parse the label
- Router is created with `tls=true` but no cert resolver attached
- Traefik serves its built-in default self-signed certificate

### Diagnosis Steps

**1. Check Current Certificate (HOST-SERVER-TERMINAL):**
```bash
openssl s_client -servername fewo.kolibri-visions.de \
  -connect fewo.kolibri-visions.de:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer

# If output shows "TRAEFIK DEFAULT CERT": Problem confirmed
```

**2. Check Traefik Logs for certresolver Parsing Errors (HOST-SERVER-TERMINAL):**
```bash
# Check recent Traefik logs for certresolver/ACME errors
docker logs --since 15m coolify-proxy 2>&1 \
  | grep -E "certresolver|acme|letsencrypt|error|field not found"

# Look for:
# - "field not found, node: certresolver" → Label key typo/whitespace
# - "unable to obtain ACME certificate" → DNS or challenge failure
# - "Creating router public-website-https" → Router loaded successfully
```

**3. Inspect Docker Labels for Trailing Whitespace (HOST-SERVER-TERMINAL):**
```bash
# List container for public website (adjust name if needed)
docker ps --format 'table {{.Names}}\t{{.Image}}' | grep -i public

# Inspect labels and show non-printable characters
docker inspect pms-public-website --format '{{json .Config.Labels}}' \
  | python3 -m json.tool | grep -E 'certresolver|tls' | cat -A

# Look for:
# - Trailing whitespace shown as spaces before $ (line end marker)
# - Correct: "...certresolver": "letsencrypt"$
# - Wrong:   "...certresolver ": "letsencrypt"$ (space before closing quote)
# - Wrong:   "... certresolver": "letsencrypt"$ (space before colon)

# Alternative: directly inspect labels array
docker inspect pms-public-website \
  | jq -r '.[0].Config.Labels | to_entries[] | select(.key | contains("certresolver")) | "\(.key) = \(.value)"'

# Check for whitespace in key name
```

**4. Verify Traefik Certificate Resolver Name (HOST-SERVER-TERMINAL):**
```bash
# Confirm cert resolver name configured in Traefik
docker inspect coolify-proxy --format '{{range .Args}}{{println .}}{{end}}' \
  | grep certificatesresolvers | head -5

# Look for:
# --certificatesresolvers.letsencrypt.acme.email=...
# --certificatesresolvers.letsencrypt.acme.storage=...
# Resolver name is "letsencrypt" in this example
```

### Fix Steps (Coolify UI or Docker Compose)

**Option A: Fix via Coolify UI (Recommended)**

1. Navigate to: Coolify Dashboard → pms-public-website → Configuration → Labels
2. Locate the certresolver label:
   - Key: `traefik.http.routers.public-website-https.tls.certresolver`
   - Value: `letsencrypt`
3. **Check for trailing spaces in key:**
   - Delete the label entry
   - Re-add with exact key (copy-paste from here to avoid typos):
     ```
     traefik.http.routers.public-website-https.tls.certresolver
     ```
   - Set value: `letsencrypt` (or your resolver name from step 4 diagnosis)
4. **Important:** Click "Save" then "Redeploy" (NOT just restart)
   - Container labels only update on redeploy, not restart

**Option B: Fix via Docker Compose (if not using Coolify UI)**

Edit `docker-compose.yml` or service labels section:
```yaml
labels:
  # Ensure NO trailing whitespace in key names
  traefik.enable: "true"
  traefik.http.routers.public-website-https.rule: "Host(`fewo.kolibri-visions.de`)"
  traefik.http.routers.public-website-https.tls: "true"
  traefik.http.routers.public-website-https.tls.certresolver: "letsencrypt"  # ← NO space before colon or =
  traefik.http.routers.public-website-https.entrypoints: "websecure"
```

Redeploy:
```bash
docker compose up -d --force-recreate pms-public-website
```

**5. Wait for Let's Encrypt Certificate Issuance (30-90 seconds):**
```bash
# Monitor ACME logs
docker logs -f --since 2m coolify-proxy 2>&1 | grep -E "fewo\.kolibri-visions\.de|acme|certificate"

# Look for:
# - "Serving default certificate for request..."  → Still using default (wait)
# - "Certificate obtained for domain [fewo.kolibri-visions.de]" → Success!
```

### Verification After Fix

**1. Check Certificate via OpenSSL (HOST-SERVER-TERMINAL):**
```bash
openssl s_client -servername fewo.kolibri-visions.de \
  -connect fewo.kolibri-visions.de:443 </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates

# Expected output with Let's Encrypt:
# subject=CN = fewo.kolibri-visions.de
# issuer=C = US, O = Let's Encrypt, CN = R13  (or R10, R11, etc.)
# notBefore=Jan 12 21:00:00 2026 GMT
# notAfter=Apr 12 21:00:00 2026 GMT  (90 days validity)
```

**2. Test with curl (HOST-SERVER-TERMINAL):**
```bash
# curl WITHOUT -k flag should work
curl -I https://fewo.kolibri-visions.de

# Expected: HTTP/2 200 (no SSL errors)
# If you still need -k, certificate is not yet valid
```

**3. Browser Test:**
- Open https://fewo.kolibri-visions.de
- Click lock icon → View Certificate
- Verify:
  - Issued to: fewo.kolibri-visions.de
  - Issued by: Let's Encrypt (R13 or similar)
  - Valid dates: Current date within range
  - No security warnings

**4. Optional: Check Traefik Logs (HOST-SERVER-TERMINAL):**
```bash
# Verify no "field not found" errors for certresolver
docker logs --since 10m coolify-proxy 2>&1 \
  | grep -i "fewo.kolibri-visions.de" | grep -i error

# Expected: No output (no errors)
```

### Common Issues

**Issue: www subdomain also shows default cert**

**Cause:** DNS record for www.fewo.kolibri-visions.de missing or no Traefik router for www.

**Solutions:**
1. **Add www DNS record** (if you want to serve www):
   - Create DNS A or CNAME record: `www.fewo.kolibri-visions.de` → same IP as apex domain
   - Update Traefik router rule to include www:
     ```
     traefik.http.routers.public-website-https.rule: "Host(`fewo.kolibri-visions.de`) || Host(`www.fewo.kolibri-visions.de`)"
     ```
   - Redeploy service
2. **Remove www from router rule** (if you don't want to serve www):
   - Keep rule as: `Host(\`fewo.kolibri-visions.de\`)`
   - www will return DNS error (expected)

**Issue: Certificate still shows TRAEFIK DEFAULT CERT after 5+ minutes**

**Checks:**
- DNS resolves correctly: `nslookup fewo.kolibri-visions.de` (must return server IP)
- Port 80 open for HTTP-01 challenge: `curl http://fewo.kolibri-visions.de/.well-known/acme-challenge/test`
- Traefik ACME storage writable: Check Traefik args for acme.storage path and permissions
- Check ACME logs for specific failure: `docker logs coolify-proxy 2>&1 | grep -A 5 "unable to obtain"`

**Issue: Typo reappears after redeploy from Coolify**

**Cause:** Coolify may store labels with whitespace if originally entered that way.

**Fix:**
- Delete label entirely in Coolify UI
- Re-add from scratch with clean copy-paste
- Or edit Coolify database/config directly (advanced)

### Related Documentation

- Traefik v3 routers: https://doc.traefik.io/traefik/routing/routers/
- Let's Encrypt with Traefik: https://doc.traefik.io/traefik/https/acme/
- Docker label format: https://docs.docker.com/compose/compose-file/compose-file-v3/#labels

---
