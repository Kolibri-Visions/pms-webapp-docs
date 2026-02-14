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

## Additional Failure Mode: SSR Hydration Error (dynamic imports with ssr:false)

### Symptom

- Public homepage returns HTTP 500
- Container logs show: `TypeError: Cannot read properties of undefined (reading 'clientModules')`
- Other routes may work (404) while homepage crashes

### Root Cause

Using `dynamic()` with `ssr: false` directly in a Server Component (like `layout.tsx`) breaks the Server/Client component boundary:

```tsx
// WRONG - in layout.tsx (Server Component)
const AuthProvider = dynamic(
  () => import("./lib/auth-context").then((mod) => mod.AuthProvider),
  { ssr: false }  // ❌ Breaks SSR hydration
);
```

### Fix: Providers Client Component Pattern (Commit 0a13b0e)

1. **Create a Client Component wrapper:**

```tsx
// frontend/app/components/Providers.tsx
"use client";

import { AuthProvider } from "../lib/auth-context";
import { ThemeProvider } from "../lib/theme-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <ThemeProvider>{children}</ThemeProvider>
    </AuthProvider>
  );
}
```

2. **Use in layout.tsx (Server Component):**

```tsx
// frontend/app/layout.tsx
import { Providers } from "./components/Providers";

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>  {/* ✓ Clean boundary */}
      </body>
    </html>
  );
}
```

### Verification

```bash
# After fix, homepage should return 200 (not 500)
curl -sS -o /dev/null -w "%{http_code}" https://fewo.kolibri-visions.de/
# Expected: 200
```

---

## Additional Failure Mode: Root Route Conflict (duplicate page.tsx)

### Symptom

- Public homepage returns HTTP 404 (not 500)
- Build succeeds without errors
- Other routes in `(public)` folder also return 404

### Root Cause

Two pages compete for the root `/` route:
- `app/page.tsx` (Server Component)
- `app/(public)/page.tsx` (Client Component)

Route groups like `(public)` don't affect URL paths, so both claim `/`. Next.js may pick one arbitrarily or fail silently.

### Fix: Remove Duplicate (Commit e83301b)

Delete the conflicting `app/page.tsx`:

```bash
git rm frontend/app/page.tsx
```

The `app/(public)/page.tsx` now correctly serves `/` with the public layout (header/footer).

### Verification

```bash
# After fix + redeploy, homepage should return 200
curl -sS -o /dev/null -w "%{http_code}" https://fewo.kolibri-visions.de/
# Expected: 200

# Marker should exist
curl -sS "https://fewo.kolibri-visions.de/?cb=$(date +%s)" | grep -c 'data-testid="public-home"'
# Expected: 1
```

---

## Failure Mode: PROD Shows 404 After Fix (Stale Deployment)

### Symptom

- Local build succeeds, routes visible in build output
- GitHub has correct code (verified via `gh api`)
- PROD still returns 404 for homepage

### Root Cause

Coolify/Railway deployment not triggered or using cached build.

### Fix

1. **Verify GitHub has correct commit:**
```bash
gh api repos/Kolibri-Visions/PMS-Webapp/commits/main --jq '.sha[0:7]'
# Should match your fix commit
```

2. **Force redeploy in Coolify:**
   - Dashboard → Service → Redeploy
   - Or: Push empty commit to trigger

3. **Verify deployment:**
```bash
cd /data/repos/pms-webapp
EXPECT_COMMIT=e83301b ./backend/scripts/pms_verify_deploy.sh
# Expected: rc=0
```

4. **Test after redeploy:**
```bash
curl -sS -o /dev/null -w "%{http_code}" "https://fewo.kolibri-visions.de/?cb=$(date +%s)"
# Expected: 200

PUBLIC_BASE_URL="https://fewo.kolibri-visions.de" \
  ./backend/scripts/pms_public_homepage_ui_smoke.sh
# Expected: rc=0
```

---

## Prevention

1. **Always pin Node version** in production configs
2. **Do NOT delete `.next/cache`** in build scripts (Coolify mount)
3. **Test Node upgrades** in staging before production
4. **Monitor container logs** for runtime errors
5. **Use Providers pattern** for client-side context in layouts
6. **Avoid duplicate routes** - check for conflicting page.tsx files
7. **Verify deployments** - use pms_verify_deploy.sh after push

## Related Files

- `frontend/package.json` - Node engine constraint + build script
- `frontend/.node-version` - Node version for tooling
- `frontend/nixpacks.toml` - Nixpacks/Coolify build config
- `backend/scripts/pms_public_homepage_ui_smoke.sh` - UI verification

## Version History

- **2026-02-14**: Add failure modes: SSR Hydration (Providers pattern fix), Root Route Conflict (duplicate page.tsx)
- **2026-02-13**: Add prebuild guard for "index" folder prevention + website/pages 403 fix
- **2026-02-13**: Upgrade Next.js 14.1.0 → 14.2.35 to fix clientModules runtime bug
- **2026-02-14**: Enforce Node 20 via `nixPkgs = ["nodejs_20"]` + runtime version proof in start script
- **2026-02-13**: Added "Device or resource busy" failure mode (Coolify cache mount)
- **2026-02-13**: Initial runbook for Node 22 / Next 14.1 clientModules incompatibility
