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

## Public Booking Request Idempotency-Key

### Overview

The `POST /api/v1/public/booking-requests` endpoint supports an optional `Idempotency-Key` header for safe request retries. This prevents duplicate booking requests when network issues cause clients to retry submissions.

### How It Works

1. Client includes `Idempotency-Key: <unique-string>` header in POST request
2. Backend checks if key exists in idempotency store
3. **Key exists + same payload**: Return cached response (HTTP 200/201)
4. **Key exists + different payload**: Return HTTP 409 `idempotency_conflict`
5. **Key not found**: Process request, store result with key

### Implementation

File: `backend/app/api/routes/public_booking.py`

- Line 167: `idempotency_key: str | None = Header(None, alias="Idempotency-Key")`
- Lines 236-256: Check idempotency before processing
- Lines 413-428: Store idempotency after successful creation

### Error Responses

**409 Conflict (idempotency_conflict)**:
```json
{
  "error": "idempotency_conflict",
  "message": "Idempotency key already used with different payload"
}
```

**409 Conflict (double_booking)**:
```json
{
  "error": "date_conflict",
  "conflict_type": "double_booking",
  "message": "Requested dates overlap with existing booking"
}
```

### Smoke Test

Script: `backend/scripts/pms_public_booking_request_idempotency_smoke.sh`

```bash
# Basic usage (requires PROPERTY_ID)
PROPERTY_ID=<uuid> ./backend/scripts/pms_public_booking_request_idempotency_smoke.sh

# With custom configuration
API_BASE_URL="https://api.fewo.kolibri-visions.de" \
PUBLIC_ORIGIN="https://fewo.kolibri-visions.de" \
PROPERTY_ID=<uuid> \
./backend/scripts/pms_public_booking_request_idempotency_smoke.sh
```

**What It Tests**:

| Test | Description | Expected |
|------|-------------|----------|
| 1. Create | POST with Idempotency-Key | HTTP 201, booking_request_id |
| 2. Replay | Same key + same payload | HTTP 200/201, same ID |
| 3. Conflict | Same key + different payload | HTTP 409 idempotency_conflict |

### Troubleshooting

**Smoke script returns "PROXY MISROUTE DETECTED" or Next.js HTML**:
- The Host header override caused the proxy to route to Next.js instead of FastAPI
- Fix: Ensure `SEND_HOST_HEADER=false` (default) in smoke script
- The script uses `X-Forwarded-Host` instead for tenant resolution
- Direct API calls should target `api.fewo.kolibri-visions.de`, not the public domain

**Idempotency key not working**:
- Verify header name: `Idempotency-Key` (case-insensitive)
- Check key format: any non-empty string
- Idempotency window: typically 24-48 hours

**409 idempotency_conflict unexpectedly**:
- Client retried with modified payload
- Use unique idempotency key for each distinct request

---

## P3.4 Public Booking Request Smoke Hardening (Deterministic)

### Overview

The `pms_public_booking_request_hardening_smoke.sh` script provides deterministic, PROD-safe smoke testing for public booking request endpoints. It automatically selects a testable property and retries with different date windows to avoid false failures.

### Features

- **Auto-select property**: Uses `/api/v1/public/properties` to find a public property
- **Date window retry**: Tries up to 5 different date windows if conflicts occur
- **PROD-safe**: No `set -euo pipefail`, graceful SKIP on unavoidable conflicts
- **Misroute detection**: Detects and reports Next.js HTML responses

### Routing Pitfall Reminder

**Host header can route to Next.js 404:**
- The API domain (`api.fewo.kolibri-visions.de`) serves `/api/v1/public/*`
- The PUBLIC domain (`fewo.kolibri-visions.de`) may return 404 for API paths
- When testing via curl, **don't force `Host=fewo.*`** to the API endpoint

**Recommended defaults:**
- `SEND_HOST_HEADER=false` (default) — no Host override
- `SEND_X_FORWARDED_HOST=true` (default) — tenant resolution via X-Forwarded-Host

### Usage

```bash
# Basic usage (auto-selects property)
./backend/scripts/pms_public_booking_request_hardening_smoke.sh

# With explicit property
PROPERTY_ID=<uuid> ./backend/scripts/pms_public_booking_request_hardening_smoke.sh

# With custom API URL
API_BASE_URL="https://api.fewo.kolibri-visions.de" \
./backend/scripts/pms_public_booking_request_hardening_smoke.sh
```

### Tests Performed

| Test | Description | Expected |
|------|-------------|----------|
| A. Create | POST booking request (with retry) | 201/200, booking_request_id |
| B. Validation | Invalid payload | 422 validation_error |
| C. Double Booking | Duplicate request same dates | 409 double_booking or SKIP |

---

## P4.x Security Hardening

### Overview

P4.x security hardening addresses critical security issues identified in code analysis:

1. **Orphan Code Removal**: Removed `/ops/env-sanity` (unauthenticated endpoint leaking config status)
2. **CORS Headers Restriction**: Changed `allow_headers=["*"]` to specific headers
3. **Authenticated Rate Limiting**: Added per-user rate limiting for authenticated endpoints

### CORS Headers Configuration

**Before (insecure)**:
```python
allow_headers=["*"]
```

**After (hardened)**:
```python
allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Agency-Id", "X-Request-Id",
               "X-Forwarded-Host", "X-Forwarded-Proto", "Accept", "Accept-Language", "Content-Language",
               "baggage", "sentry-trace", "traceparent", "tracestate", "x-requested-with"]
```

**Environment Variable**: `CORS_ALLOW_HEADERS` (comma-separated list)

**Note**: Tracing headers (baggage, sentry-trace, traceparent, tracestate) and `x-requested-with` are included by default for browser compatibility.

### Troubleshooting: CORS Preflight Blocked in Admin UI

**Symptom**: Admin UI shows "Failed to fetch" or browser console shows "Disallowed CORS headers" / preflight blocked / HTTP 400.

**Root Cause**: Browser adds headers that were not in the CORS allowlist.

**Headers that browsers/clients may add**:

*Tracing headers:*
- `baggage` - W3C Trace Context baggage
- `sentry-trace` - Sentry distributed tracing
- `traceparent` - W3C Trace Context
- `tracestate` - W3C Trace Context state
- `x-requested-with` - AJAX request marker

*Supabase client headers:*
- `apikey` - Supabase anonymous key
- `x-client-info` - Supabase client info
- `x-supabase-api-version` - Supabase API version
- `x-supabase-client` - Supabase client identifier
- `x-supabase-auth` - Supabase auth header

*CSRF headers:*
- `x-csrf-token` - CSRF protection token
- `x-xsrf-token` - XSRF protection token
- `x-csrftoken` - Alternative CSRF token

**Fix**:
1. Default config now includes all common tracing, Supabase, and CSRF headers
2. To add custom headers, extend via `CORS_ALLOW_HEADERS` env var:
   ```bash
   CORS_ALLOW_HEADERS="Authorization,Content-Type,...,my-custom-header"
   ```
3. Do NOT revert to wildcard `*` (security risk with credentials)

**Coolify Note**: If `CORS_ALLOW_HEADERS` env var is set in Coolify, it **overrides** the defaults. Ensure it includes all required headers.

**Debug Commands** (HOST-SERVER-TERMINAL):

```bash
# 1. Test browser-realistic preflight
API="https://api.fewo.kolibri-visions.de"
ORIGIN="https://admin.fewo.kolibri-visions.de"
REQ_HEADERS="authorization,content-type,x-agency-id,apikey,x-client-info,x-supabase-api-version,x-supabase-client,x-supabase-auth,x-csrf-token,cache-control,if-none-match"
curl -k -sS -i -X OPTIONS \
  "${API}/api/v1/properties?limit=50" \
  -H "Origin: ${ORIGIN}" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: ${REQ_HEADERS}" | head -30

# 2. Run CORS smoke test (includes header probe on failure)
./backend/scripts/pms_cors_headers_smoke.sh

# 3. Check if Coolify overrides CORS config
docker exec pms-backend env | grep -i cors
```

**Expected**: HTTP 200/204 for preflight, `access-control-allow-headers` includes requested headers.

### Authenticated Rate Limiting

Per-user rate limiting for authenticated endpoints:

| Setting | Default | Description |
|---------|---------|-------------|
| `AUTH_RATE_LIMIT_ENABLED` | `true` | Enable/disable auth rate limiting |
| `AUTH_RATE_LIMIT_MAX_REQUESTS` | `100` | Max requests per window |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Window duration in seconds |

**Exempt Paths** (no rate limiting):
- `/health`
- `/api/v1/ops/version`
- `/docs`, `/redoc`, `/openapi.json`

**Fail-Open Design**: If Redis is unavailable, requests are allowed (PROD-safe).

### Smoke Tests

#### 1. Ops Security Test
```bash
./backend/scripts/pms_ops_security_smoke.sh
```

Tests:
- `/ops/env-sanity` returns 404 (removed)
- `/ops/version` is public
- `/ops/modules` requires auth
- `/ops/audit-log` requires admin role

#### 2. CORS Headers Test
```bash
./backend/scripts/pms_cors_headers_smoke.sh
```

Tests:
- `Access-Control-Allow-Headers` is NOT wildcard
- Required headers (Authorization, Content-Type, etc.) are allowed
- Tracing headers (baggage, sentry-trace, traceparent, tracestate, x-requested-with) are allowed
- Admin UI preflight with browser-realistic headers returns 200

#### 3. Auth Rate Limit Test
```bash
TOKEN=<jwt> ./backend/scripts/pms_auth_rate_limit_smoke.sh
```

Tests:
- X-RateLimit-* headers present on authenticated endpoints
- Exempt paths don't have rate limit headers

---

## See Also

- [03-auth.md](./03-auth.md) - Authentication and authorization
- [01-deployment.md](./01-deployment.md) - Environment variable configuration
