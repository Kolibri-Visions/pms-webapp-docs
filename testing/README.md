# Testing Guide

**Purpose**: Document test organization and workflow

**Audience**: Backend developers, QA engineers

**Source of Truth**: `backend/tests/` directory structure

---

## Overview

**Test Framework**: pytest

**Test Location**: `backend/tests/`

**Test Types**: unit, integration, security, smoke

**Workflow**: **No local tests; server-side smoke only** (tests run on server, not locally)

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

**Run Locally** (if needed):
```bash
# Unit tests typically don't require DATABASE_URL
pytest backend/tests/unit/
```

---

### 2. Integration Tests

**Location**: `backend/tests/integration/`

**Purpose**: Test API endpoints with database (requires `DATABASE_URL` and `JWT_SECRET`)

**Examples**:
- `test_availability.py` - Availability API integration tests
- `test_bookings.py` - Bookings API integration tests
- `test_rbac.py` - RBAC enforcement integration tests
- `test_auth_db_priority.py` - Auth vs DB priority tests

**Run Locally** (if needed):
```bash
# Requires DATABASE_URL and JWT_SECRET
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test"
export JWT_SECRET="test-secret-key-1234567890123456"

pytest backend/tests/integration/
```

**Note**: Integration tests create/destroy test data (use test database, not production)

---

### 3. Security Tests

**Location**: `backend/tests/security/`

**Purpose**: Test security mechanisms (encryption, signature validation, etc.)

**Examples**:
- `test_token_encryption.py` - Token encryption/decryption
- `test_redis_client.py` - Redis client security
- `test_webhook_signature.py` - Webhook signature validation

**Run Locally** (if needed):
```bash
pytest backend/tests/security/
```

---

### 4. Smoke Tests

**Location**: `backend/tests/smoke/`

**Purpose**: High-level sanity checks (system works end-to-end)

**Examples**:
- `test_channel_manager_smoke.py` - Channel Manager smoke test

**Run on Server** (recommended workflow):
```bash
# Smoke tests run on server after deployment
# See ops/runbook.md for smoke script usage
```

**Related Docs**: [Runbook - Smoke Script Pitfalls](ops/runbook.md#smoke-script-pitfalls)

---

## Test Fixtures

**Location**: `backend/tests/conftest.py`

**Purpose**: Shared test fixtures, configuration

**Common Fixtures** (assumed, check code):
- `db` - Database connection (for integration tests)
- `client` - FastAPI test client (for API tests)
- `test_user` - Mock user for auth tests
- `test_agency` - Mock agency for multi-tenancy tests

**Example Usage**:
```python
import pytest

@pytest.fixture
async def db():
    # Setup: Create test database connection
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    yield conn
    # Teardown: Close connection
    await conn.close()
```

---

## Workflow: No Local Tests; Server-Side Smoke Only

### Current Workflow

**Local Development**:
- ❌ Do NOT run tests locally (no pytest in local dev workflow)
- ✅ Rely on type checking (mypy), linting (ruff) instead

**Server Deployment**:
- ✅ Run smoke tests on server after deployment
- ✅ Smoke tests verify critical paths (health, auth, DB connectivity)

**Why**:
- Tests require DATABASE_URL + JWT_SECRET (not available locally)
- Integration tests create/destroy data (risky on shared DB)
- Smoke tests are faster feedback loop (seconds vs minutes)

---

## Running Tests (Server-Side)

### Smoke Tests (Recommended)

**Location**: `backend/scripts/ops/smoke.py` (assumed, check `ops/runbook.md`)

**Usage**:
```bash
# Run smoke script on server
python backend/scripts/ops/smoke.py
```

**What It Tests**:
- `/health` endpoint returns 200
- `/health/ready` endpoint returns 200 (DB connectivity)
- JWT token validation works
- Basic CRUD operations (if applicable)

**Related Docs**: [Runbook - Smoke Script Pitfalls](ops/runbook.md#smoke-script-pitfalls)

---

### Full Test Suite (If Needed)

**All Tests**:
```bash
# Requires DATABASE_URL, JWT_SECRET
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test"
export JWT_SECRET="test-secret-key-1234567890123456"

pytest backend/tests/
```

**Unit Tests Only**:
```bash
pytest backend/tests/unit/
```

**Integration Tests Only**:
```bash
# Requires DATABASE_URL, JWT_SECRET
pytest backend/tests/integration/
```

**Security Tests Only**:
```bash
pytest backend/tests/security/
```

**Smoke Tests Only**:
```bash
pytest backend/tests/smoke/
```

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
