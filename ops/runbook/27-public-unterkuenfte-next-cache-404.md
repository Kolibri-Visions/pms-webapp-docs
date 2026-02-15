# 27. Public /unterkuenfte Cached 404 (Next.js ISR)

**Date Added**: 2026-02-15

## Symptom

- `curl https://fewo.kolibri-visions.de/unterkuenfte` returns "This page could not be found."
- Response headers show `x-nextjs-cache: HIT` and `cache-control: s-maxage=31536000`
- API endpoints work fine: `/api/v1/public/properties` returns 200

## Root Cause

Next.js ISR (Incremental Static Regeneration) cached a `notFound` response from an earlier transient backend failure.

**Timeline**:
1. Public website requested `/unterkuenfte`
2. Backend API was temporarily unavailable (proxy not configured, 500 error, etc.)
3. Next.js rendered a 404 page
4. ISR cached this 404 response for up to 1 year (`s-maxage=31536000`)
5. Backend was fixed, but Next.js keeps serving the cached 404

## Fix Applied

### 1. Force Dynamic Rendering

Added to all public pages (`unterkuenfte/page.tsx`, `[slug]/page.tsx`, `page.tsx`):

```typescript
"use client";

export const dynamic = "force-dynamic";
export const revalidate = 0;
```

This prevents ISR from caching the page output.

### 2. No-Store Fetch

All client-side fetch calls now use `cache: "no-store"`:

```typescript
fetch(`${apiBase}/api/v1/public/site/pages/${slug}`, {
  cache: "no-store",
});
```

### 3. No notFound() on Transient Errors

Changed `[slug]/page.tsx` to render an error state instead of calling `notFound()`:

```typescript
// BAD: Can be cached by ISR
if (error) {
  notFound(); // ❌ Don't do this
}

// GOOD: Renders error state, user can retry
if (error) {
  return (
    <div>
      <p>{error}</p>
      <button onClick={() => window.location.reload()}>Retry</button>
    </div>
  );
}
```

## Verification

### Smoke Test

```bash
PUBLIC_SITE_URL=https://fewo.kolibri-visions.de \
./backend/scripts/pms_public_unterkuenfte_page_smoke.sh
```

Expected output:
```
✅ PASS: No 'This page could not be found.' text
✅ PASS: No 'next-error-h1' class
✅ PASS: No '404' in page title
✅ SMOKE TEST PASSED: /unterkuenfte page renders correctly
```

### Manual Check

```bash
# Check for cached 404 indicators
curl -sI https://fewo.kolibri-visions.de/unterkuenfte | grep -i "x-nextjs-cache"

# x-nextjs-cache: MISS = good (fresh render)
# x-nextjs-cache: HIT  = check if page content is correct
```

## Cache Invalidation

If the 404 is still cached after deploying the fix:

1. **Redeploy the frontend** - This triggers a full rebuild and clears ISR cache
2. **Wait for cache expiry** - Not recommended (could be up to 1 year)
3. **On-Demand Revalidation** - If implemented, call the revalidation API

In Coolify:
1. Navigate to the pms-admin service
2. Click "Redeploy"
3. Wait for deployment to complete
4. Run smoke test to verify

## Files Changed

| File | Change |
|------|--------|
| `frontend/app/(public)/unterkuenfte/page.tsx` | Added `dynamic = "force-dynamic"`, `revalidate = 0` |
| `frontend/app/(public)/[slug]/page.tsx` | Added dynamic config, removed `notFound()`, added error state |
| `frontend/app/(public)/page.tsx` | Added dynamic config, `cache: "no-store"` on fetches |

## Prevention

For all new public tenant pages:

1. Always add `export const dynamic = "force-dynamic"` and `export const revalidate = 0`
2. Use `cache: "no-store"` on all fetch calls
3. Never call `notFound()` on API errors - render an error state instead
4. Test with backend unavailable to ensure graceful degradation
