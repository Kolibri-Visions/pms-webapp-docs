# 26. Public API Proxy (Next.js Rewrites)

**Date Added**: 2026-02-15

## Overview

The public website (`fewo.*`) needs to access the backend API (`api.*`) for property listings, CMS pages, and site settings. Instead of configuring CORS for every white-label domain, we use Next.js rewrites to proxy public API requests through the frontend server.

## Architecture

```
Browser (fewo.kolibri-visions.de)
    │
    ├── /api/v1/public/* → Next.js Rewrite → api.kolibri-visions.de
    │                      (same-origin)      (server-to-server)
    │
    └── /api/v1/* (other) → Middleware blocks → 404
```

## Security Guardrails

| Layer | Protection |
|-------|------------|
| **next.config.js** | Only `/api/v1/public/:path*` is rewritten |
| **middleware.ts** | Blocks ALL `/api/v1/*` except `/api/v1/public/*` |
| **Method restriction** | Only GET/HEAD allowed for public endpoints (405 for POST/PUT/etc.) |
| **Server-only env** | `API_BASE_URL` (not NEXT_PUBLIC_*) keeps backend URL hidden |

## Configuration

### Environment Variable

Set in Coolify/deployment:
```bash
API_BASE_URL=https://api.fewo.kolibri-visions.de
```

This is a **server-only** env var (not prefixed with `NEXT_PUBLIC_`), so it's never exposed to the browser.

### Files

| File | Purpose |
|------|---------|
| `frontend/next.config.js` | Defines rewrite rule for `/api/v1/public/*` |
| `frontend/middleware.ts` | Blocks non-public API routes, restricts methods |

## Verification

Run smoke test:
```bash
PUBLIC_SITE_URL=https://fewo.kolibri-visions.de \
./backend/scripts/pms_public_api_proxy_smoke.sh
```

Expected results:
- ✅ `GET /api/v1/public/site/settings` → 200 JSON
- ✅ `GET /api/v1/public/properties?limit=1` → 200 JSON
- ✅ `GET /api/v1/website/pages` → 404 (blocked)
- ✅ `POST /api/v1/public/properties` → 405 (method blocked)

## Troubleshooting

### Public endpoints return 404

**Symptoms**: `/api/v1/public/site/settings` returns 404 or HTML error page.

**Causes**:
1. `API_BASE_URL` not set in deployment
2. Backend not reachable from frontend server
3. Next.js build didn't pick up rewrites config

**Fix**:
```bash
# Check env var in container
docker exec pms-admin env | grep API_BASE_URL

# Test backend directly from frontend container
docker exec pms-admin curl -s https://api.fewo.kolibri-visions.de/health

# Rebuild if config changed
# (rewrites are evaluated at build time)
```

### Admin endpoints accessible from public site

**Symptoms**: `/api/v1/website/pages` returns 200 instead of 404.

**Cause**: Middleware not running or misconfigured.

**Fix**: Verify middleware.ts has API route protection block and matcher includes API routes.

### POST returns 405 when needed

**Context**: By default, only GET/HEAD are allowed on public endpoints.

**If POST is needed** (rare for public API): Update middleware.ts to allow specific methods for specific paths.
