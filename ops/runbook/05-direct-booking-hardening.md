# 05 - Direct Booking Hardening (CORS, Host Allowlist, Tenant Resolution)

This chapter covers security hardening for public direct booking endpoints, including CORS configuration, Host allowlist enforcement, and multi-tenant domain resolution.

## Overview

Public direct booking endpoints require additional security measures to:
- Prevent cross-origin request forgery from unauthorized domains
- Enforce host allowlist to block requests from unknown hosts
- Resolve tenant/agency context from custom domain mappings

## Architecture

```
                                    ┌─────────────────────┐
                                    │   Public Website    │
                                    │ fewo.kolibri-...de  │
                                    └──────────┬──────────┘
                                               │
                                               │ Origin: https://fewo.kolibri-visions.de
                                               │ Host: api.fewo.kolibri-visions.de
                                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            PMS Backend                                   │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────────────┐   │
│  │ CORS Middleware│ → │ Host Allowlist │ → │ Tenant Domain Resolver │   │
│  │ (FastAPI)      │   │ (P3b)          │   │ (agency_domains)       │   │
│  └────────────────┘   └────────────────┘   └────────────────────────┘   │
│         │                    │                       │                   │
│         ▼                    ▼                       ▼                   │
│   Check Origin         Check Host            Resolve agency_id          │
│   against list         against list          from domain mapping        │
└──────────────────────────────────────────────────────────────────────────┘
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALLOWED_ORIGINS` | Comma-separated CORS origins (legacy) | Production origins |
| `CORS_ALLOWED_ORIGINS` | Explicit CORS origins (preferred, overrides ALLOWED_ORIGINS) | None |
| `ALLOWED_HOSTS` | Comma-separated host allowlist for public endpoints | Empty (warning in prod) |
| `CORS_ALLOW_CREDENTIALS` | Allow credentials in CORS requests | `true` |
| `CORS_ALLOW_METHODS` | Allowed HTTP methods for CORS | `GET,POST,PUT,DELETE,PATCH` |
| `TRUST_PROXY_HEADERS` | Trust X-Forwarded-Host header | `true` |

### Example Configuration

```bash
# Production configuration
ALLOWED_ORIGINS="https://admin.fewo.kolibri-visions.de,https://fewo.kolibri-visions.de"
CORS_ALLOWED_ORIGINS="https://fewo.kolibri-visions.de,https://app.customer.com"
ALLOWED_HOSTS="api.fewo.kolibri-visions.de,api.customer.com"
TRUST_PROXY_HEADERS=true
```

## CORS Behavior

### Expected Behavior

| Origin | CORS Response |
|--------|---------------|
| In `CORS_ALLOWED_ORIGINS` | `Access-Control-Allow-Origin: <exact-origin>` |
| Not in list | No CORS header (browser blocks) |
| Wildcard (`*`) | Not recommended for credentials |

### Preflight Requests

CORS preflight (OPTIONS) requests are handled automatically by FastAPI middleware:

```bash
# Test CORS preflight
curl -X OPTIONS "https://api.fewo.kolibri-visions.de/api/v1/public/booking-requests" \
  -H "Origin: https://fewo.kolibri-visions.de" \
  -H "Access-Control-Request-Method: POST" \
  -i

# Expected: 200/204 with Access-Control-Allow-Origin header
```

## Host Allowlist Enforcement

### Implementation

File: `backend/app/core/public_host_allowlist.py`

The host allowlist dependency (`enforce_host_allowlist`) validates the Host header against `ALLOWED_HOSTS`:

- **Valid host**: Request proceeds
- **Invalid host**: 403 Forbidden with `host_not_allowed` error
- **Empty allowlist (prod)**: Warning logged, request allowed (backward compat)
- **Empty allowlist (dev)**: Request allowed silently

### Error Response

```json
{
  "detail": {
    "error": "host_not_allowed",
    "message": "Host 'evil.example' not allowed. Configure ALLOWED_HOSTS environment variable.",
    "host": "evil.example",
    "allowed_hosts": ["api.fewo.kolibri-visions.de"]
  }
}
```

## Tenant Domain Resolution

### How It Works

1. Extract Host from request (respects `X-Forwarded-Host` if `TRUST_PROXY_HEADERS=true`)
2. Look up domain in `agency_domains` table
3. Resolve to `agency_id` for request context

### Adding a Customer Domain

```sql
-- Add custom domain mapping
INSERT INTO agency_domains (agency_id, domain, is_primary, created_at)
VALUES (
  'ffd0123a-10b6-40cd-8ad5-66eee9757ab7',
  'booking.customer.com',
  false,
  NOW()
);

-- Also add to ALLOWED_HOSTS environment variable
-- ALLOWED_HOSTS="api.fewo.kolibri-visions.de,booking.customer.com"
```

## Smoke Test

### Script: `pms_direct_booking_cors_host_smoke.sh`

PROD-safe smoke test for CORS and Host allowlist verification.

```bash
# Basic usage
./backend/scripts/pms_direct_booking_cors_host_smoke.sh

# With custom configuration
API_BASE_URL="https://api.fewo.kolibri-visions.de" \
PUBLIC_ORIGIN="https://fewo.kolibri-visions.de" \
PUBLIC_HOST="fewo.kolibri-visions.de" \
./backend/scripts/pms_direct_booking_cors_host_smoke.sh
```

### What It Tests

| Test | Description | Expected |
|------|-------------|----------|
| 1. CORS Preflight | OPTIONS with valid Origin | 200/204, CORS header matches |
| 2. GET with Origin | GET public endpoint with Origin | 200, CORS header present |
| 3. Invalid Origin | OPTIONS with evil.example | CORS header absent or not echoed |
| 4. Invalid Host | GET with unknown.example Host | 403 or skip (proxy may strip) |

### Exit Codes

- `0` = PASS (all tests passed or skipped safely)
- `1` = FAIL (one or more tests failed)

## Troubleshooting

### CORS Header Not Returned

**Symptoms**: Browser blocks request with "No 'Access-Control-Allow-Origin' header"

**Causes**:
1. Origin not in `CORS_ALLOWED_ORIGINS` or `ALLOWED_ORIGINS`
2. CORS middleware not mounted (check main.py)

**Fix**:
```bash
# Check current CORS origins
grep CORS_ALLOWED_ORIGINS /path/to/.env

# Add missing origin
CORS_ALLOWED_ORIGINS="https://fewo.kolibri-visions.de,https://new-origin.com"
```

### Host Allowlist Blocking Legitimate Requests

**Symptoms**: 403 `host_not_allowed` for valid host

**Causes**:
1. Host not in `ALLOWED_HOSTS`
2. Proxy/LB changing Host header

**Fix**:
```bash
# Check allowed hosts
grep ALLOWED_HOSTS /path/to/.env

# Add missing host
ALLOWED_HOSTS="api.fewo.kolibri-visions.de,new-host.com"

# If proxy changes Host, check X-Forwarded-Host
TRUST_PROXY_HEADERS=true
```

### Domain Tenant Resolution Fails

**Symptoms**: Request doesn't resolve to correct agency

**Causes**:
1. Domain not in `agency_domains` table
2. Domain not in `ALLOWED_HOSTS`

**Diagnosis**:
```sql
-- Check domain mapping
SELECT * FROM agency_domains WHERE domain = 'customer.com';

-- Check if any mapping exists for agency
SELECT * FROM agency_domains WHERE agency_id = '<agency-uuid>';
```

## Related Files

| File | Purpose |
|------|---------|
| `app/main.py` | CORS middleware configuration |
| `app/core/config.py` | Settings (CORS_*, ALLOWED_*) |
| `app/core/public_host_allowlist.py` | Host allowlist enforcement |
| `app/core/tenant_domain.py` | Domain extraction and normalization |
| `scripts/pms_direct_booking_cors_host_smoke.sh` | PROD-safe smoke test |
| `scripts/pms_p3b_domain_host_cors_smoke.sh` | Extended P3b smoke test |

## See Also

- [03-auth.md](./03-auth.md) - Authentication and authorization
- [01-deployment.md](./01-deployment.md) - Environment variable configuration
