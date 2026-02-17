# Runbook 22: Website Admin API 404 Troubleshooting

## Symptom

- `/api/v1/website/design` returns 404 Not Found
- `/api/v1/website/pages` returns 404 Not Found
- `/api/v1/website/navigation` returns 404 Not Found
- `/api/v1/website/seo` returns 404 Not Found
- BUT `/api/v1/me` returns 200 OK (auth works)

## Root Cause

The `website_admin` router is not mounted in the FastAPI application. This typically happens when:

1. `MODULES_ENABLED=true` (production default) and the module system doesn't mount it
2. The failsafe mounting code in `main.py` is missing or broken
3. Router import fails silently
4. **ImportError** - `website_admin.py` imports a missing dependency (e.g., `get_authenticated_user`)
   - Fixed via compat alias in `backend/app/api/deps.py`
5. **PydanticUndefinedAnnotation** - Forward-ref type hints (e.g., `"NavigationUpdateRequest"`) not resolvable
   - Cause: Schema classes used in route signatures but only imported inside function body
   - Fix: Import all request/response models at module scope in `website_admin.py`
   - Symptom: Coolify restart loop with `pydantic.errors.PydanticUndefinedAnnotation`

## Quick Diagnosis

```bash
# Check if OpenAPI contains website routes
curl -s "https://api.fewo.kolibri-visions.de/openapi.json" | grep -c "/api/v1/website/design"
# Expected: 2 (GET and PUT)
# Actual if broken: 0

# Check if endpoint is 404 vs other error
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/website/design"
# Expected: 200
# Actual if broken: 404
```

## Fix

Ensure `backend/app/main.py` includes the website_admin router failsafe:

```python
# After the other public router failsafes
website_admin_routes_exist = any(
    route.path == "/api/v1/website/design"
    for route in app.routes
)
if not website_admin_routes_exist:
    from .api.routes import website_admin
    logger.warning("Website admin router not found, applying failsafe mounting")
    app.include_router(website_admin.router, prefix="/api/v1/website", tags=["Website Admin"])
    logger.info("✅ Failsafe: Website admin router mounted at /api/v1/website")
```

## Verification

After deploying the fix:

```bash
# 1. Verify deploy
EXPECT_COMMIT=<sha> ./backend/scripts/pms_verify_deploy.sh

# 2. Check OpenAPI
curl -s "https://api.fewo.kolibri-visions.de/openapi.json" | grep "/api/v1/website/design"
# Should show the route

# 3. Run admin smoke
source /root/.pms_env
API_BASE_URL=https://api.fewo.kolibri-visions.de \
./backend/scripts/pms_admin_website_design_smoke.sh
# Expected: rc=0

# 4. Direct curl test
curl -s -H "Authorization: Bearer $JWT_TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/website/design" | head -c 200
# Should return JSON with design tokens
```

## OpenAPI URLs

- **Canonical**: `/openapi.json`
- **Alias**: `/api/v1/openapi.json` (same content)

Both return the full OpenAPI schema. The alias exists for consistency with `/api/v1/` prefix convention.

## Related Files

- `backend/app/main.py` - Router mounting and failsafe logic
- `backend/app/api/routes/website_admin.py` - Website admin router
- `backend/scripts/pms_admin_website_design_smoke.sh` - Smoke test

## Branding Upload 404 (Website Logo System)

### Symptom

- `/api/v1/website/branding/upload` returns 404 Not Found
- Logo upload in Website Design page fails with "Upload fehlgeschlagen"

### Root Causes (Fixed 2026-02-17)

1. **Invalid Form() parameter** - `Form(..., pattern=...)` is not valid in FastAPI
   - Fix: Remove `pattern` param, validate manually in function body

2. **Wrong storage bucket** - Code used `property-media` instead of `branding-assets`
   - Fix: Use dedicated `branding-assets` bucket in `storage.py`

3. **Missing website_admin module** - Module system didn't load router
   - Fix: Created `backend/app/modules/website_admin.py` + added to bootstrap

4. **Missing internal proxy route** - Frontend called backend directly (CORS/404)
   - Fix: Created Next.js proxy routes:
     - `frontend/app/api/internal/website/branding/upload/route.ts`
     - `frontend/app/api/internal/website/branding/[assetType]/route.ts`

### Request Flow

```
Browser (design-form.tsx)
  → /api/internal/website/branding/upload (Next.js proxy)
  → /api/v1/website/branding/upload (Backend)
  → Supabase Storage (branding-assets bucket)
```

### Endpoints

| Purpose | Internal Proxy | Backend Endpoint |
|---------|----------------|------------------|
| Upload logo/favicon | `POST /api/internal/website/branding/upload` | `POST /api/v1/website/branding/upload` |
| Delete logo/favicon | `DELETE /api/internal/website/branding/{type}` | `DELETE /api/v1/website/branding/{type}` |

Asset types: `logo_light`, `logo_dark`, `favicon`

### Storage Path

```
branding-assets/{agency_id}/{asset_type}.{ext}
```

Example: `branding-assets/ffd0123a-10b6-40cd-8ad5-.../logo_light.png`

### Related Files

- `backend/app/api/routes/website_admin.py` - Upload/delete endpoints
- `backend/app/core/storage.py` - `upload_branding_asset()` method
- `backend/app/modules/website_admin.py` - Module registration
- `frontend/app/website/design/design-form.tsx` - Logo upload UI
- `frontend/app/api/internal/website/branding/` - Proxy routes

## Version History

- **2026-02-17**: Added branding upload endpoints + internal proxy routes for website logo system
- **2026-02-13**: Fixed PydanticUndefinedAnnotation (NavigationUpdateRequest/SeoUpdateRequest imports)
- **2026-02-13**: Added `get_authenticated_user` compat alias in deps.py to fix ImportError
- **2026-02-13**: Added website_admin router failsafe + OpenAPI alias
