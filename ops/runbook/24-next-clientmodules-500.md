# Runbook 24: Next.js 500 - clientModules Undefined

## Symptom

- All pages return HTTP 500 error
- Docker logs show:
  ```
  TypeError: Cannot read properties of undefined (reading 'clientModules')
  at /app/node_modules/next/dist/compiled/next-server/app-page.runtime.prod.js:...
  ```
- Both public and admin containers affected
- Node version in container: v22.x

## Root Cause

Next.js 14.1.0 has a runtime bug affecting Server Component rendering. The `clientModules` error occurs when the runtime internals fail to initialize properly.

Root causes (in order of likelihood):
1. **Next.js 14.1.0 runtime bug**: Fixed in 14.2.x (upgrade required)
2. **Folder named "index" in app directory**: Next.js App Router bug (see below)
3. **Node.js v22 incompatibility**: Next.js 14.1 doesn't support Node 22
4. **Stale `.next` cache**: Corrupted build artifacts from previous builds
5. **No Node version pinning**: Nixpacks/Coolify may auto-select incompatible Node version

## Quick Diagnosis

```bash
# Check HTTP status
curl -k -sS -o /dev/null -w "%{http_code}" https://fewo.kolibri-visions.de/
# Expected: 200
# Actual if broken: 500

# Check Node version in container
docker exec public-website node --version
# If v22.x: likely cause of clientModules error

# Check container logs
docker logs public-website 2>&1 | grep -i "clientModules\|TypeError"
# Look for: Cannot read properties of undefined (reading 'clientModules')
```

## Fix

### 1. Upgrade Next.js to 14.2.x (Primary Fix)

**frontend/package.json:**
```json
{
  "dependencies": {
    "next": "14.2.35"
  },
  "devDependencies": {
    "eslint-config-next": "^14.2.35"
  }
}
```

Then run `npm install` to update package-lock.json.

**Why 14.2.35 and not 14.1.1?**
- 14.1.x has the clientModules runtime bug
- 14.2.x contains the fix and is stable
- Staying in 14.x avoids breaking changes from Next.js 15/16

### 2. Check for "index" Folder in App Directory

**Known Next.js Bug (Issue #69061):** If any folder in `frontend/app/` is named exactly "index", it causes the clientModules error at runtime.

**Check:**
```bash
find frontend/app -type d -name "index" -print
# Expected: no output
```

**If found:** Rename the folder. For example:
- `app/index/page.tsx` → `app/(home)/page.tsx` (route group)
- Or use a redirect in next.config.js

**Prevention:** A prebuild guard script blocks builds if "index" folders exist:
```json
// frontend/package.json
{
  "scripts": {
    "prebuild": "node scripts/assert_no_app_index_dir.mjs"
  }
}
```

The guard scans `frontend/app/` and fails with a clear error if any folder is named "index".

### 3. Pin Node to 20.x LTS

**frontend/package.json:**
```json
{
  "engines": {
    "node": "20.x"
  }
}
```

**frontend/.node-version:**
```
20
```

**frontend/nixpacks.toml (CRITICAL - use nixPkgs, not just env var):**
```toml
# NIXPACKS_NODE_VERSION env var alone does NOT control which Node is installed!
# We must explicitly request the nodejs_20 Nix package:
nixPkgs = ["nodejs_20"]

[variables]
# Keep for compatibility, but actual version is controlled by nixPkgs
NIXPACKS_NODE_VERSION = "20"
```

**Why `engines` and `NIXPACKS_NODE_VERSION` env var are NOT enough:**
- `engines.node` in package.json is only advisory - npm/node don't enforce it
- `NIXPACKS_NODE_VERSION` as env var may not be respected by Nixpacks
- Only `nixPkgs = ["nodejs_20"]` guarantees the Nix package used

### 4. Runtime Version Proof

Add version logging to start script so you can verify in container logs:

**frontend/package.json:**
```json
{
  "scripts": {
    "start": "node -e \"console.log('[pms-frontend] node='+process.version+' next='+require('next/package.json').version)\" && next start"
  }
}
```

Container logs will now show: `[pms-frontend] node=v20.x.x next=14.2.35`

### 5. Build Script (Coolify-safe)

**Do NOT delete `.next`** - Coolify mounts cache at `/app/.next/cache`:
```json
{
  "scripts": {
    "build": "next build",
    "build:clean": "find .next ... (local only)"
  }
}
```

### 6. Redeploy

Force a fresh build in Coolify:
1. Push commit with nixPkgs fix
2. Trigger new deployment
3. Check logs for `[pms-frontend] node=v20.x.x`

## Verification

After deploying the fix:

```bash
# 1. Check HTTP status (should be 200, not 500)
curl -k -sS -o /dev/null -w "%{http_code}" https://fewo.kolibri-visions.de/
# Expected: 200

# 2. Check marker exists
curl -k -sS "https://fewo.kolibri-visions.de/?cb=$(date +%s)" | grep -c 'data-testid="public-home"'
# Expected: 1

# 3. Run homepage smoke
PUBLIC_BASE_URL=https://fewo.kolibri-visions.de \
./backend/scripts/pms_public_homepage_ui_smoke.sh
# Expected: rc=0

# 4. Check Node/Next versions via start log (MUST be v20.x.x and 14.2.x)
docker logs public-website 2>&1 | grep '\[pms-frontend\]'
# Expected: [pms-frontend] node=v20.x.x next=14.2.35

# 5. Alternative: direct Node version check
docker exec public-website node --version
# Expected: v20.x.x

# 6. No clientModules errors in logs
docker logs public-website 2>&1 | tail -200 | grep -i "clientModules\|TypeError" || echo "OK: no errors"
# Expected: no matches (just "OK: no errors")
```

## Additional Failure Mode: Build Fails with "Device or resource busy"

### Symptom

Coolify build fails with:
```
rm: cannot remove '.next/cache': Device or resource busy
```
Build exit code 1, deploy never completes.

### Root Cause

Coolify/Nixpacks uses BuildKit cache mounts:
```
--mount=type=cache,target=/app/.next/cache
```

If the build script tries `rm -rf .next`, it cannot delete the mounted `.next/cache` directory.

### Fix

**Do NOT delete `.next` in the default build script:**

```json
// frontend/package.json
{
  "scripts": {
    "build": "next build",
    "build:clean": "find .next -mindepth 1 -maxdepth 1 ! -name cache -exec rm -rf {} + 2>/dev/null || true; next build"
  }
}
```

- `build`: Safe for Coolify (doesn't touch cache mount)
- `build:clean`: For local use only (preserves cache directory)

## Prevention

1. **Always pin Node version** in production configs
2. **Do NOT delete `.next/cache`** in build scripts (Coolify mount)
3. **Test Node upgrades** in staging before production
4. **Monitor container logs** for runtime errors

## Related Files

- `frontend/package.json` - Node engine constraint + build script
- `frontend/.node-version` - Node version for tooling
- `frontend/nixpacks.toml` - Nixpacks/Coolify build config
- `backend/scripts/pms_public_homepage_ui_smoke.sh` - UI verification

## Version History

- **2026-02-13**: Add prebuild guard for "index" folder prevention + website/pages 403 fix
- **2026-02-13**: Upgrade Next.js 14.1.0 → 14.2.35 to fix clientModules runtime bug
- **2026-02-14**: Enforce Node 20 via `nixPkgs = ["nodejs_20"]` + runtime version proof in start script
- **2026-02-13**: Added "Device or resource busy" failure mode (Coolify cache mount)
- **2026-02-13**: Initial runbook for Node 22 / Next 14.1 clientModules incompatibility
