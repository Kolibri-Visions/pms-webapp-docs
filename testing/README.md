# Testing Guide

**Purpose**: Document test organization and workflow

**Audience**: Backend developers, QA engineers

**Source of Truth**: `backend/tests/` directory structure

---

## Overview

**Test Framework**: pytest

**Test Location**: `backend/tests/`

**Test Types**: unit, integration, security, smoke

**Official Workflow**: **Server-side smoke tests after deployment** (no local pytest in standard workflow)

---

## Test Organization

### Directory Structure

```
backend/tests/
├── unit/                   # Unit tests (isolated, no DB)
├── integration/            # Integration tests (DB required)
├── security/               # Security tests (token encryption, webhook signatures)
├── smoke/                  # Smoke tests (high-level sanity checks)
└── conftest.py             # Test fixtures, configuration
```

---

## Test Types

### 1. Unit Tests

**Location**: `backend/tests/unit/`

**Purpose**: Test individual functions/classes in isolation (no database, no external dependencies)

**Examples**:
- `test_jwt_verification.py` - JWT token validation logic
- `test_rbac_helpers.py` - RBAC helper functions
- `test_agency_deps.py` - Agency dependency extraction
- `test_database_generator.py` - Test data generation utilities
- `test_channel_sync_log_service.py` - Channel sync log service

**Note**: See "Optional (Contributor Only)" section below for local test commands.

---

### 2. Integration Tests

**Location**: `backend/tests/integration/`

**Purpose**: Test API endpoints with database (requires `DATABASE_URL` and `JWT_SECRET`)

**Examples**:
- `test_availability.py` - Availability API integration tests
- `test_bookings.py` - Bookings API integration tests
- `test_rbac.py` - RBAC enforcement integration tests
- `test_auth_db_priority.py` - Auth vs DB priority tests

**Note**: See "Optional (Contributor Only)" section below for local test commands.

---

### 3. Security Tests

**Location**: `backend/tests/security/`

**Purpose**: Test security mechanisms (encryption, signature validation, etc.)

**Examples**:
- `test_token_encryption.py` - Token encryption/decryption
- `test_redis_client.py` - Redis client security
- `test_webhook_signature.py` - Webhook signature validation

**Note**: See "Optional (Contributor Only)" section below for local test commands.

---

### 4. Smoke Tests

**Location**: `backend/tests/smoke/`

**Purpose**: High-level sanity checks (system works end-to-end)

**Examples**:
- `test_channel_manager_smoke.py` - Channel Manager smoke test

**Official Workflow**: Run on server after deployment

**Related Docs**: [Runbook - Smoke Script Pitfalls](../ops/runbook.md#smoke-script-pitfalls) for smoke script usage and troubleshooting.

---

## Test Fixtures

**Location**: `backend/tests/conftest.py`

**Purpose**: Shared test fixtures, configuration

**Common Fixtures**: Check `backend/tests/conftest.py` for available fixtures (database connection, test client, mock users, etc.)

---

## Official Workflow: Server-Side Smoke Tests

**Local Development**:
- Rely on type checking (mypy), linting (ruff)
- No pytest in standard local workflow

**Server Deployment**:
- ✅ Run smoke tests on server after deployment
- ✅ Smoke tests verify critical paths (health, auth, DB connectivity)

**Why**:
- Tests require DATABASE_URL + JWT_SECRET (sensitive credentials)
- Integration tests create/destroy data (risky on shared DB)
- Smoke tests provide faster feedback loop

---

### Server-Side Smoke Tests (Official Workflow)

**What It Tests**:
- `/health` endpoint returns 200
- `/health/ready` endpoint returns 200 (DB connectivity)
- JWT token validation works
- Basic CRUD operations (if applicable)

**How to Run**: See [Runbook - Smoke Script Pitfalls](../ops/runbook.md#smoke-script-pitfalls) for usage and troubleshooting.

---

### Server-side Smoke Checks (Official)

**Purpose**: Minimal smoke sequence to verify critical paths after deployment.

**Policy**: No local tests. Server-side only.

**When to Run**:
- After every deployment to staging/production
- After container restart
- After environment variable changes
- After database migrations

---

#### Prerequisites

**Environment Variables Required:**

WHERE: HOST-SERVER-TERMINAL
```bash
# Set variables before running smoke checks
export BACKEND_URL="https://api.fewo.kolibri-visions.de"
export SUPABASE_URL="https://sb-pms.kolibri-visions.de"
export ANON_KEY="your-anon-key-here"
export EMAIL="admin@example.com"
export PASSWORD="your-password"

# Optional: Set property ID for booking tests
export PROPERTY_ID="some-uuid-here"
```

**Verify variables are set:**

WHERE: HOST-SERVER-TERMINAL
```bash
echo "BACKEND_URL: $BACKEND_URL"
echo "ANON_KEY length: ${#ANON_KEY}"
echo "EMAIL: $EMAIL"
```

---

#### Minimal Smoke Sequence

**Step 1: Health Checks**

WHERE: HOST-SERVER-TERMINAL
```bash
# Basic health (always returns 200, even if DB down)
curl -L $BACKEND_URL/health
# Expected: {"status":"ok","service":"pms-backend"}

# Readiness check (returns 503 if DB/Redis/Celery down)
curl -L $BACKEND_URL/health/ready
# Expected: {"status":"healthy","db":"up","redis":"up","celery":"up"}

# If 503: Check container logs, network attachment, env vars
```

---

**Step 2: Fetch JWT Token**

WHERE: HOST-SERVER-TERMINAL
```bash
# Login and extract token
TOKEN=$(curl -s -X POST $SUPABASE_URL/auth/v1/token?grant_type=password \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | jq -r '.access_token')

# Validate token
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "ERROR: Failed to fetch token"
  exit 1
fi

# Verify token structure
echo "Token length: ${#TOKEN}"  # Should be ~500+ chars
echo "Token parts: $(echo $TOKEN | tr '.' '\n' | wc -l)"  # Should be 3

# Export for subsequent requests
export TOKEN
```

---

**Step 3: Test Authenticated Endpoint (GET /api/v1/properties)**

WHERE: HOST-SERVER-TERMINAL
```bash
# List properties
curl -s -L $BACKEND_URL/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.'

# Expected: 200 with JSON array (may be empty if no data)
# Failure modes:
# - 401: Invalid token (check JWT_SECRET)
# - 403: Missing role/agency_id (check auth logic)
# - 503: DB unavailable (check network attachment)
```

---

**Step 4: Create Booking (POST /api/v1/bookings)**

WHERE: HOST-SERVER-TERMINAL
```bash
# Create test booking
BOOKING_ID=$(curl -s -L -X POST $BACKEND_URL/api/v1/bookings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"property_id\": \"$PROPERTY_ID\",
    \"check_in\": \"2025-07-01\",
    \"check_out\": \"2025-07-05\",
    \"guest_first_name\": \"Test\",
    \"guest_last_name\": \"Smoke\",
    \"guest_email\": \"smoke@example.com\",
    \"status\": \"inquiry\"
  }" \
  | jq -r '.id')

# Verify booking created
if [ -z "$BOOKING_ID" ] || [ "$BOOKING_ID" = "null" ]; then
  echo "ERROR: Failed to create booking"
  exit 1
fi

echo "Created booking: $BOOKING_ID"

# Export for subsequent steps
export BOOKING_ID
```

---

**Step 5: Confirm Booking (PATCH /api/v1/bookings/{id})**

WHERE: HOST-SERVER-TERMINAL
```bash
# Confirm booking
curl -s -L -X PATCH $BACKEND_URL/api/v1/bookings/$BOOKING_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}' \
  | jq '.'

# Expected: 200 with updated booking (status="confirmed")
```

---

**Step 6: Cancel Booking (DELETE /api/v1/bookings/{id} or PATCH with status=cancelled)**

WHERE: HOST-SERVER-TERMINAL
```bash
# Cancel booking (cleanup)
curl -s -L -X PATCH $BACKEND_URL/api/v1/bookings/$BOOKING_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "cancelled"}' \
  | jq '.'

# Expected: 200 with updated booking (status="cancelled")

# Alternative: Delete booking
# curl -s -L -X DELETE $BACKEND_URL/api/v1/bookings/$BOOKING_ID \
#   -H "Authorization: Bearer $TOKEN"
```

---

**Step 7: Trigger Availability Sync (if Channel Manager enabled)**

WHERE: HOST-SERVER-TERMINAL
```bash
# Check if Channel Manager is enabled
if [ "$CHANNEL_MANAGER_ENABLED" = "true" ]; then
  # Trigger sync
  SYNC_LOG_ID=$(curl -s -L -X POST $BACKEND_URL/api/v1/channel-sync/trigger \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"property_id\": \"$PROPERTY_ID\",
      \"sync_type\": \"availability\"
    }" \
    | jq -r '.log_id')

  echo "Triggered sync: $SYNC_LOG_ID"

  # Wait 5 seconds for worker to process
  sleep 5

  # Check sync log status
  curl -s -L $BACKEND_URL/api/v1/channel-sync/logs/$SYNC_LOG_ID \
    -H "Authorization: Bearer $TOKEN" \
    | jq '.status'

  # Expected: "success" or "running"
  # If "triggered" (stuck): Check worker logs, Redis, Celery
else
  echo "Channel Manager disabled, skipping sync test"
fi
```

---

#### Full Smoke Script (Combined)

**Script Location (if exists):**
- `backend/scripts/smoke.sh` (check if exists in repo)
- `backend/tests/smoke/` (pytest smoke tests)

**Run script:**

WHERE: HOST-SERVER-TERMINAL
```bash
# Export all variables first
export BACKEND_URL="https://api.fewo.kolibri-visions.de"
export SUPABASE_URL="https://sb-pms.kolibri-visions.de"
export ANON_KEY="your-anon-key"
export EMAIL="admin@example.com"
export PASSWORD="your-password"
export PROPERTY_ID="some-uuid"

# Run smoke script (if exists)
./backend/scripts/smoke.sh

# Or run pytest smoke tests (contributor only)
# DATABASE_URL="postgresql://postgres:$PASSWORD@supabase-db:5432/postgres" \
# JWT_SECRET="your-jwt-secret" \
# python -m pytest backend/tests/smoke/ -v
```

**Common Pitfalls**: See [Runbook - Smoke Script Pitfalls](../ops/runbook.md#smoke-script-pitfalls)

---

#### Verification Checklist

After running smoke checks, verify:

- ✅ Health endpoint returns 200 (`/health`)
- ✅ Readiness endpoint returns 200 (`/health/ready`)
- ✅ JWT token fetched successfully (length ~500+ chars, 3 parts)
- ✅ Properties endpoint returns 200 (`/api/v1/properties`)
- ✅ Booking created successfully (returns booking ID)
- ✅ Booking confirmed (status transitions to "confirmed")
- ✅ Booking cancelled (status transitions to "cancelled")
- ✅ Sync triggered and completed (if Channel Manager enabled)

**If any check fails**: See [Runbook - Top 5 Failure Modes](../ops/runbook.md#top-5-failure-modes-and-fixes)

---

#### Smoke Check Schedule

**When to Run:**
- ✅ After every deployment to staging
- ✅ After every deployment to production
- ✅ After container restart
- ✅ After environment variable changes
- ✅ After database migrations
- ✅ Before declaring deployment "successful"

**Who Runs:**
- Ops team after deployment
- CI/CD pipeline (automated)
- On-call engineer during incident response

---

## Optional (Contributor Only): Local Test Execution

**Note**: The following commands are for contributors who need to run tests locally. This is NOT part of the standard workflow.

### Full Test Suite

```bash
# Requires DATABASE_URL, JWT_SECRET
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test"
export JWT_SECRET="test-secret-key-1234567890123456"

pytest backend/tests/
```

### By Test Type

```bash
# Unit tests (no DB required)
pytest backend/tests/unit/

# Integration tests (requires DATABASE_URL, JWT_SECRET)
pytest backend/tests/integration/

# Security tests
pytest backend/tests/security/

# Smoke tests
pytest backend/tests/smoke/
```

**Warning**: Integration tests create/destroy test data. Use a test database, NOT production.

---

## Test Execution Results

**Expected Output**:
```
================================ test session starts =================================
collected 42 items

backend/tests/unit/test_jwt_verification.py ....                             [  9%]
backend/tests/unit/test_rbac_helpers.py .......                              [ 26%]
backend/tests/integration/test_availability.py ....                          [ 38%]
backend/tests/integration/test_bookings.py .....                             [ 50%]
backend/tests/security/test_token_encryption.py ...                          [ 57%]
backend/tests/smoke/test_channel_manager_smoke.py .                          [ 59%]

================================ 42 passed in 12.34s =================================
```

---

## Adding New Tests

### Step 1: Choose Test Type

- **Unit test**: Isolated function/class logic (no DB)
- **Integration test**: API endpoint with DB
- **Security test**: Security mechanism (encryption, signatures)
- **Smoke test**: High-level sanity check

### Step 2: Create Test File

**Naming**: `test_{feature}.py`

**Location**: `backend/tests/{unit|integration|security|smoke}/`

**Example**:
```bash
# Create integration test for new feature
touch backend/tests/integration/test_reviews.py
```

### Step 3: Write Test Cases

**Example** (pytest):
```python
import pytest

async def test_create_review(db, client, test_user):
    """Test creating a review."""
    response = await client.post(
        "/api/v1/reviews",
        json={"property_id": "123", "rating": 5, "comment": "Great!"},
        headers={"Authorization": f"Bearer {test_user.token}"}
    )
    assert response.status_code == 201
    assert response.json()["rating"] == 5
```

### Step 4: Run Tests

```bash
# Run new test file
pytest backend/tests/integration/test_reviews.py
```

---

## Test Coverage (Estimated)

**Current Coverage** (as of 2025-12-30):
- **Unit tests**: 5 files (JWT, RBAC, agency deps, DB generator, channel sync log)
- **Integration tests**: 5 files (availability, bookings, RBAC, auth DB priority)
- **Security tests**: 3 files (token encryption, Redis client, webhook signature)
- **Smoke tests**: 1 file (channel manager smoke)

**Total**: 14+ test files

**Coverage Goal**: UNKNOWN (not measured, check with pytest-cov if needed)

---

## Troubleshooting

### Tests Fail with "Database unavailable"

**Symptom**: `asyncpg.exceptions.CannotConnectNowError` or `503 Service Unavailable`

**Cause**: `DATABASE_URL` not set or incorrect

**Fix**:
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test"
```

---

### Tests Fail with "JWT validation failed"

**Symptom**: `401 Unauthorized` in integration tests

**Cause**: `JWT_SECRET` not set or incorrect

**Fix**:
```bash
export JWT_SECRET="test-secret-key-1234567890123456"
```

---

### Smoke Script Fails

**Symptom**: Empty TOKEN/PID, bash errors

**Related Docs**: [Runbook - Smoke Script Pitfalls](ops/runbook.md#smoke-script-pitfalls)

---

## Related Documentation

- [Runbook - Smoke Script Pitfalls](ops/runbook.md#smoke-script-pitfalls) - Troubleshooting smoke tests
- [Error Taxonomy](architecture/error-taxonomy.md) - Exception types for testing

---

**Last Updated**: 2025-12-30
**Maintained By**: Backend Team
