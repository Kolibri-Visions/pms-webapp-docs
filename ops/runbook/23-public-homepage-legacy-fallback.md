# Runbook 23: Public Homepage Shows Legacy Welcome Card

## Symptom

- Public domain root "/" shows "Willkommen" card with "Diese Seite wird gerade geladen..."
- Buttons: "Zu den Unterkünften" and "Login"
- Expected: CMS homepage with hero_fullwidth, trust_indicators, and other blocks

## Root Causes

1. **Wrong Next.js route priority**: `app/page.tsx` (legacy fallback) takes precedence over `app/(public)/page.tsx` because root-level routes win over route groups
2. **Missing tenant context**: API calls don't include `public_host` query param, causing tenant resolution to fail
3. **Stale deploy/cache**: Old frontend version still cached at CDN or in Next.js build cache

## Quick Diagnosis

```bash
# Check if homepage HTML contains CMS markers
curl -sS "https://fewo.kolibri-visions.de/?cb=$(date +%s)" | grep -c 'data-testid="public-homepage"'
# Expected: 1
# Actual if broken: 0

# Check for legacy markers
curl -sS "https://fewo.kolibri-visions.de/?cb=$(date +%s)" | grep -c 'Diese Seite wird gerade geladen'
# Expected: 0
# Actual if broken: 1

# Run UI smoke test
PUBLIC_BASE_URL=https://fewo.kolibri-visions.de \
./backend/scripts/pms_public_homepage_ui_smoke.sh
# Expected: rc=0
```

## Fix

### 1. Route Priority Fix

Ensure `frontend/app/page.tsx` is a server component that:
- Reads host from headers (x-forwarded-host > host)
- If admin host: redirect to /login
- If public host: fetch CMS homepage with `public_host` query param and render blocks

```typescript
// frontend/app/page.tsx (server component)
import { headers } from "next/headers";
import BlockRenderer from "./(public)/components/BlockRenderer";

export default async function RootPage() {
  const headersList = await headers();
  const publicHost = getPublicHost(headersList);

  // Fetch with tenant context
  const url = `${API_BASE}/api/v1/public/site/pages/home?public_host=${publicHost}`;
  const page = await fetch(url, { next: { revalidate: 60 } }).then(r => r.json());

  return <BlockRenderer blocks={page.blocks} />;
}
```

### 2. Tenant Context Fix

All public API calls must include `?public_host=<domain>`:

```
GET /api/v1/public/site/pages/home?public_host=fewo.kolibri-visions.de
GET /api/v1/public/site/design?public_host=fewo.kolibri-visions.de
```

### 3. Clear Caches

```bash
# Force redeploy in Coolify (rebuilds Next.js)
# Or clear CDN cache if using Cloudflare
```

## Verification

After deploying the fix:

```bash
# 1. Verify frontend deploy
curl -sS "https://fewo.kolibri-visions.de/api/ops/version" 2>/dev/null || echo "no version endpoint"

# 2. Run UI smoke
PUBLIC_BASE_URL=https://fewo.kolibri-visions.de \
./backend/scripts/pms_public_homepage_ui_smoke.sh
# Expected: rc=0

# 3. Manual check
# Open https://fewo.kolibri-visions.de/ in browser (incognito)
# Should see hero image + headline, NOT "Willkommen" card
```

## Test Markers

The fixed implementation includes SSR-rendered test markers:

- `data-testid="public-homepage"` - On the `<main>` element
- `data-testid="block-hero_fullwidth"` - On the hero block container

These markers appear in the initial HTML (curl-grepable) for automated testing.

## Related Files

- `frontend/app/page.tsx` - Root page (must be server component with tenant context)
- `frontend/app/(public)/page.tsx` - Alternative (route group, lower priority)
- `frontend/app/(public)/components/BlockRenderer.tsx` - Block rendering
- `frontend/middleware.ts` - Host-based routing logic
- `backend/scripts/pms_public_homepage_ui_smoke.sh` - UI smoke test

## Version History

- **2026-02-13**: Initial runbook for legacy welcome card issue
