# Authentication & Authorization Operations

**When to use:** JWT token issues, apikey header problems, CORS errors, fresh token generation.

---

## Table of Contents

- [Token Validation (apikey Header)](#token-validation-apikey-header)
- [Fresh JWT (Supabase)](#fresh-jwt-supabase)
- [CORS Errors (Admin Console Blocked)](#cors-errors-admin-console-blocked)
- [Booking Requests Approve/Decline](#booking-requests-approvedecline)

---

## Golden Commands

```bash
# Get fresh JWT token
TOKEN="$(./backend/scripts/get_fresh_token.sh)"

# Test token with API
curl -H "Authorization: Bearer $TOKEN" \
  https://api.fewo.kolibri-visions.de/api/v1/me

# Test CORS preflight
curl -X OPTIONS https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Origin: https://admin.fewo.kolibri-visions.de" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" -v

# Test Supabase auth (requires both headers)
curl -X GET "https://sb-pms.kolibri-visions.de/auth/v1/user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "apikey: $ANON_KEY"
```

---

## Token Validation (apikey Header)

### Symptom

- JWT token fetched successfully (200 from Supabase auth)
- API requests with `Authorization: Bearer <token>` return `401 Unauthorized`
- Logs show: `"Invalid JWT"` or `"Unauthorized"`

### Root Cause

**IMPORTANT: apikey header scope depends on which service you're calling:**

1. **Supabase Kong endpoints** (e.g., `https://sb-pms.../auth/v1/...`) require **two headers**:
   - `Authorization: Bearer <jwt>`
   - `apikey: <anon_key>`

2. **PMS Backend API** (e.g., `https://api.fewo.../api/v1/...`) requires **only**:
   - `Authorization: Bearer <jwt>`
   - **NO apikey header needed**

**Why does Supabase Kong require both?**
- `Authorization` header contains user's JWT (specific user identity)
- `apikey` header contains project's anon key (project identification for rate limiting/routing)

**Why doesn't PMS Backend need apikey?**
- PMS Backend validates JWT directly using the JWT_SECRET
- No Kong gateway in front of PMS Backend
- apikey is only needed for Supabase services

### Verify

```bash
# Test Supabase Kong endpoint (requires both headers)
# Example: Fetch current user profile
curl -X GET "https://sb-pms.kolibri-visions.de/auth/v1/user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "apikey: $ANON_KEY"
# Returns: 200 OK (user profile)

# Test without apikey (FAILS on Kong)
curl -X GET "https://sb-pms.kolibri-visions.de/auth/v1/user" \
  -H "Authorization: Bearer $TOKEN"
# Returns: 401 Unauthorized

# Test PMS Backend API (only Authorization needed)
curl -X GET "https://api.fewo.kolibri-visions.de/api/v1/properties?limit=1" \
  -H "Authorization: Bearer $TOKEN"
# Returns: 200 OK (no apikey needed)
```

### Fix

**For Supabase Kong API Clients:**

When calling Supabase services (auth, storage, etc.), include both headers:

```python
# Python example - Supabase Kong endpoint
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "apikey": anon_key,  # Required for Kong
    "Content-Type": "application/json"
}
response = requests.get(f"{supabase_url}/auth/v1/user", headers=headers)
```

**For PMS Backend API Clients:**

When calling PMS Backend, only Authorization header is needed:

```python
# Python example - PMS Backend API
headers = {
    "Authorization": f"Bearer {jwt_token}",
    # NO apikey needed
    "Content-Type": "application/json"
}
response = requests.get(f"{api_url}/api/v1/properties", headers=headers)
```

**For Smoke Scripts:**

Our smoke scripts call both:
- Supabase Kong for auth (`fetch_token()` includes apikey)
- PMS Backend API for tests (only Authorization header)

### Prevention

- Document apikey requirement in API docs
- Add example requests showing both headers
- Test authentication flow in CI/CD

---

## Fresh JWT (Supabase)

### Quick Token Generation

Use the `get_fresh_token.sh` helper script to obtain Supabase JWT tokens for testing, debugging, or manual API calls:

```bash
# Get token to variable
TOKEN="$(./backend/scripts/get_fresh_token.sh)"

# Export to environment
source <(./backend/scripts/get_fresh_token.sh --export)

# Verify token metadata
./backend/scripts/get_fresh_token.sh --check

# Test token against /auth/v1/user
./backend/scripts/get_fresh_token.sh --user
```

**Required environment variables:**
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SB_EMAIL` - User email for authentication
- `SB_PASSWORD` - User password for authentication
- `SB_URL` (optional) - Supabase URL (defaults to https://sb-pms.kolibri-visions.de)

**Exit codes:**
- `0` - Success
- `1` - Missing required environment variables
- `2` - Authentication failed (invalid credentials)
- `3` - Empty or invalid JSON response
- `4` - Token verification failed (--user flag)

For detailed usage, integration examples, and troubleshooting, see **[backend/scripts/README.md - Get Fresh JWT Token](../scripts/README.md#get-fresh-jwt-token-get_fresh_tokensh)**.

---

## CORS Errors (Admin Console Blocked)

### Symptom

- Admin UI at `https://admin.fewo.kolibri-visions.de` shows CORS error in browser console
- Browser error: `Access to fetch at 'https://api.fewo.kolibri-visions.de/...' has been blocked by CORS policy`
- Preflight request (OPTIONS) fails with missing `Access-Control-Allow-Origin` header
- API returns 403 or connection refused for cross-origin requests

### Root Cause

CORS (Cross-Origin Resource Sharing) middleware not configured to allow admin console origin:
- Default CORS origins only include localhost (development)
- Production domains not added to `ALLOWED_ORIGINS` environment variable
- Missing `Authorization` header in allowed headers (rare, default allows all)

### Verify

Check current CORS configuration:

```bash
# Check environment variable on backend container
docker exec pms-backend env | grep ALLOWED_ORIGINS
# Should show: ALLOWED_ORIGINS=https://admin.fewo.kolibri-visions.de,https://fewo.kolibri-visions.de,...

# Or check backend logs on startup for CORS origins
docker logs pms-backend | grep -i cors
```

Test CORS preflight manually:

```bash
# Send OPTIONS preflight request
curl -X OPTIONS https://api.fewo.kolibri-visions.de/api/v1/properties \
  -H "Origin: https://admin.fewo.kolibri-visions.de" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  -v

# Should return:
# Access-Control-Allow-Origin: https://admin.fewo.kolibri-visions.de
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH
# Access-Control-Allow-Headers: *
```

### Fix

**Option 1: Set Environment Variable** (Recommended)

Add `ALLOWED_ORIGINS` to backend environment:

```bash
# In Coolify or deployment config
ALLOWED_ORIGINS=https://admin.fewo.kolibri-visions.de,https://fewo.kolibri-visions.de,http://localhost:3000
```

Restart backend:

```bash
docker restart pms-backend
```

**Option 2: Update Default in Code** (Already Done)

The default in `backend/app/core/config.py` now includes:
- `https://admin.fewo.kolibri-visions.de` (admin console)
- `https://fewo.kolibri-visions.de` (public site)
- `http://localhost:3000` (local dev)

If env var is not set, these defaults will be used.

### Prevention

- Always include admin and frontend origins in `ALLOWED_ORIGINS`
- Test CORS with `curl -X OPTIONS` before deploying frontend changes
- Document required origins in deployment checklist

---

## Booking Requests Approve/Decline

### Symptom

- Admin UI "Genehmigen" (Approve) or "Ablehnen" (Decline) buttons return error
- HTTP 409 Conflict when trying to approve/decline
- HTTP 422 Validation Error on decline action

### Root Cause

**409 Conflict** - Invalid state transition:
- Request already approved/declined (idempotent - same response returned)
- Trying to approve a cancelled request
- Trying to decline an already confirmed request

**422 Validation Error** - Missing required fields:
- Decline requires `decline_reason` field (non-empty string)

### Verify

```bash
# Check current status of booking request
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>"

# Test approve (only for requested/under_review status)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"internal_note": "Approved via ops"}' \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>/approve"

# Test decline (requires decline_reason)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decline_reason": "Property unavailable", "internal_note": "Declined via ops"}' \
  "https://api.fewo.kolibri-visions.de/api/v1/booking-requests/<uuid>/decline"
```

### Valid State Transitions

| From Status | Approve → | Decline → |
|-------------|-----------|-----------|
| `requested` | `confirmed` | `declined` |
| `under_review` | `confirmed` | `declined` |
| `confirmed` | ❌ (already approved) | ❌ (cannot decline) |
| `declined` | ❌ (cannot approve) | ❌ (already declined) |
| `cancelled` | ❌ (cannot approve) | ❌ (cannot decline) |

### Smoke Test

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export JWT_TOKEN="<manager_jwt>"
./backend/scripts/pms_booking_requests_approve_decline_smoke.sh
# Expected: Test Results: 6/6 passed
```

---
