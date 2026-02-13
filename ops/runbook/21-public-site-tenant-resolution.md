# Runbook 21: Public Site Tenant Resolution

## Overview

This runbook covers tenant resolution for public-facing endpoints. Public endpoints like `/api/v1/public/site/settings`, `/api/v1/public/properties`, and the public website need to determine which agency (tenant) is being accessed.

## Resolution Priority

The `extract_request_host()` function resolves the effective host in this order:

1. **Query param `public_host`** (preferred for smoke tests)
   - Example: `GET /api/v1/public/site/settings?public_host=fewo.example.com`
   - Works reliably through proxies, load balancers, and CDNs
   - Recommended for automated testing and debugging

2. **Header `x-public-host`** (alternative for programmatic access)
   - Example: `curl -H "x-public-host: fewo.example.com" /api/v1/public/site/settings`
   - Useful for programmatic overrides without modifying URLs

3. **Header `X-Forwarded-Host`** (proxy scenario)
   - Set by reverse proxies (nginx, Traefik, Cloudflare)
   - Standard HTTP header for proxy pass-through

4. **Header `Host`** (fallback)
   - Standard HTTP Host header
   - Used when no overrides are present

## When to Use Each Method

### Query Param `public_host` (Recommended for Testing)

```bash
# Smoke tests
curl "https://api.fewo.kolibri-visions.de/api/v1/public/site/settings?public_host=fewo.kolibri-visions.de"

# With other query params
curl "https://api.example.com/api/v1/public/properties?public_host=tenant.example.com&limit=10"
```

**Why?** Host header overrides (`-H "Host: ..."`) are unreliable through proxies and load balancers. They may be stripped, rewritten, or cause SSL certificate mismatches.

### Header `x-public-host` (Programmatic)

```bash
# When you can't modify the URL
curl -H "x-public-host: fewo.example.com" \
     "https://api.fewo.kolibri-visions.de/api/v1/public/site/settings"
```

### Production (Automatic)

In production, the `X-Forwarded-Host` or `Host` header is set automatically by the proxy:

```
Client → Cloudflare (fewo.example.com) → Traefik → API
                    ↓
         X-Forwarded-Host: fewo.example.com
```

## Smoke Test Examples

### Test Public Site Design

```bash
API_BASE_URL=https://api.fewo.kolibri-visions.de \
PUBLIC_HOST=fewo.kolibri-visions.de \
./pms_public_site_design_smoke.sh
```

### Test Homepage Blocks

```bash
API_BASE_URL=https://api.fewo.kolibri-visions.de \
PUBLIC_HOST=fewo.kolibri-visions.de \
./pms_public_homepage_blocks_smoke.sh
```

### Test Admin Website Design

```bash
API_BASE_URL=https://api.fewo.kolibri-visions.de \
JWT_TOKEN=eyJ... \
./pms_admin_website_design_smoke.sh
```

## Troubleshooting

### Tenant Not Resolved (404 or Wrong Data)

1. **Check domain mapping exists:**
   ```sql
   SELECT * FROM agency_domains WHERE domain = 'fewo.example.com';
   ```

2. **Verify resolution via query param:**
   ```bash
   curl "https://api.example.com/api/v1/public/site/settings?public_host=fewo.example.com"
   # Should return agency_id
   ```

3. **Check logs for resolution:**
   ```bash
   docker logs backend 2>&1 | grep -i "resolve"
   ```

### Host Header Stripped by Proxy

**Symptom:** Tests work locally but fail through Cloudflare/Traefik.

**Solution:** Use `?public_host=` query param instead of `-H "Host: ..."`:

```bash
# BAD (unreliable through proxy)
curl -H "Host: fewo.example.com" https://api.example.com/...

# GOOD (works reliably)
curl "https://api.example.com/...?public_host=fewo.example.com"
```

### Multiple Tenants on Same API

The multi-tenant setup works like this:

```
fewo-client-a.com → api.example.com → agency_id = UUID_A
fewo-client-b.com → api.example.com → agency_id = UUID_B
```

Each public request includes tenant context via host resolution, ensuring data isolation.

## Domain Registration

Domains must be registered in `agency_domains` table:

```sql
INSERT INTO agency_domains (agency_id, domain, is_primary, is_verified)
VALUES ('uuid-here', 'fewo.example.com', true, true);
```

## Related Files

- `backend/app/core/tenant_domain.py` - Resolution logic
- `backend/app/api/routes/public_site.py` - Public site endpoints
- `backend/scripts/pms_public_site_design_smoke.sh` - Design smoke test
- `backend/scripts/pms_public_homepage_blocks_smoke.sh` - Homepage smoke test
- `backend/scripts/pms_epic_c_public_website_smoke.sh` - Full website smoke test

## Version History

- **2026-02-13**: Added `public_host` query param and `x-public-host` header support
- **2025-xx-xx**: Initial domain-based tenant resolution (P3b)
