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

Next.js 14.1.0 has compatibility issues with Node.js v22. The `clientModules` error occurs during Server Component rendering when the runtime internals fail to initialize properly.

Additional contributing factors:
1. **Stale `.next` cache**: Corrupted build artifacts from previous builds
2. **No Node version pinning**: Nixpacks/Coolify may auto-select incompatible Node version

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

### 1. Pin Node to 20.x LTS

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

**frontend/nixpacks.toml:**
```toml
[variables]
NIXPACKS_NODE_VERSION = "20"
```

### 2. Clean Build

**frontend/package.json:**
```json
{
  "scripts": {
    "build": "rm -rf .next && next build"
  }
}
```

### 3. Redeploy

Force a fresh build in Coolify:
1. Clear build cache (if option exists)
2. Trigger new deployment
3. Verify Node version in new container is 20.x

## Verification

After deploying the fix:

```bash
# 1. Check HTTP status (should be 200, not 500)
curl -k -sS -o /dev/null -w "%{http_code}" https://fewo.kolibri-visions.de/
# Expected: 200

# 2. Check Node version in container
docker exec public-website node --version
# Expected: v20.x.x

# 3. Run homepage smoke
PUBLIC_BASE_URL=https://fewo.kolibri-visions.de \
./backend/scripts/pms_public_homepage_ui_smoke.sh
# Expected: rc=0

# 4. Check for clientModules errors in logs
docker logs public-website 2>&1 | tail -50 | grep -i "clientModules\|TypeError"
# Expected: no matches
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

- **2026-02-13**: Added "Device or resource busy" failure mode (Coolify cache mount)
- **2026-02-13**: Initial runbook for Node 22 / Next 14.1 clientModules incompatibility
