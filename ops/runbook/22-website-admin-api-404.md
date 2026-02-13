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

## Version History

- **2026-02-13**: Added `get_authenticated_user` compat alias in deps.py to fix ImportError
- **2026-02-13**: Added website_admin router failsafe + OpenAPI alias
