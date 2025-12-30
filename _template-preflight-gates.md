# Preflight Gates Template

**Zweck:** Standardisierte Checkliste vor Start einer neuen Phase oder vor Deploy.

---

## 1. Scope

**Phase:** [PHASE_NAME]
**Deliverables:** [LIST_DELIVERABLES]
**Dependencies:** [LIST_DEPENDENCIES]

---

## 2. Local Checks

### 2.1 Linting & Code Quality

**Commands:**
```bash
# Python Backend
cd backend
ruff check .
ruff format --check .

# Optional: mypy type checking
mypy app/
```

**Expected Output:**
- ✅ No linting errors
- ✅ Code formatting consistent
- ✅ Type checks pass (if applicable)

### 2.2 Unit Tests

**Commands:**
```bash
cd backend
pytest tests/unit/ -v
```

**Expected Output:**
- ✅ All unit tests pass
- ✅ Coverage > 80% (optional)

---

## 3. Database & Migrations

### 3.1 Supabase Local Start

**Commands:**
```bash
supabase start
```

**Expected Output:**
- ✅ PostgreSQL container started (port 54322)
- ✅ API started (port 54321)
- ✅ Studio available (port 54323)

### 3.2 Migrations Apply

**Commands:**
```bash
supabase db reset
```

**Expected Output:**
- ✅ All migrations applied successfully
- ✅ Seed data loaded
- ✅ No errors in logs

### 3.3 Database Smoke Checks

**Commands:**
```bash
# Check tables exist
supabase db psql -c "\dt"

# Check RLS policies
supabase db psql -c "SELECT tablename, policyname FROM pg_policies LIMIT 10;"

# Check seed data
supabase db psql -c "SELECT COUNT(*) FROM agencies;"
supabase db psql -c "SELECT COUNT(*) FROM properties;"
supabase db psql -c "SELECT COUNT(*) FROM bookings;"
```

**Expected Output:**
- ✅ All core tables present
- ✅ RLS policies created
- ✅ Seed data counts match expectations

---

## 4. Backend API Smoke Checks

**Note:** Backend runs on port 8000 (NOT 54321, which is Supabase API)

### 4.1 Start Backend

**Commands:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Expected Output:**
- ✅ Server starts without errors
- ✅ Listening on http://127.0.0.1:8000

### 4.2 Health Endpoints

**Commands:**
```bash
# Liveness (always UP)
curl http://localhost:8000/health

# Readiness (DB check)
curl http://localhost:8000/health/ready

# OpenAPI Schema
curl http://localhost:8000/openapi.json | head -n 20
```

**Expected Output:**
- ✅ `/health` returns `{"status": "up"}`
- ✅ `/health/ready` returns `{"status": "up", "components": {"db": {"status": "up"}}}`
- ✅ `/openapi.json` returns valid JSON schema

**Note:** Redis/Celery checks are SKIPPED by default. Enable via:
```bash
export ENABLE_REDIS_HEALTHCHECK=true
export ENABLE_CELERY_HEALTHCHECK=true
```

### 4.3 Integration Tests

**Commands:**
```bash
cd backend
pytest tests/integration/ -v
```

**Expected Output:**
- ✅ All integration tests pass
- ✅ Database rollback works correctly

---

## 5. CI/CD Checks

### 5.1 GitHub Actions

**Check:**
- Open GitHub repository
- Navigate to Actions tab
- Verify latest workflow run is GREEN

**Expected Output:**
- ✅ All jobs passed (lint, test, build)

### 5.2 Pre-commit Hooks (optional)

**Commands:**
```bash
pre-commit run --all-files
```

**Expected Output:**
- ✅ All hooks pass

---

## 6. Deploy Smoke (Staging/Production)

### 6.1 Container Build

**Commands:**
```bash
docker build -t pms-backend:test -f backend/Dockerfile backend/
```

**Expected Output:**
- ✅ Build succeeds without errors
- ✅ Image size reasonable (<500MB)

### 6.2 Container Run

**Commands:**
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  pms-backend:test
```

**Expected Output:**
- ✅ Container starts
- ✅ Health endpoints respond

### 6.3 Coolify Deploy (if applicable)

**Check:**
- Trigger deploy via Coolify
- Monitor logs
- Verify service status

**Expected Output:**
- ✅ Deploy successful
- ✅ Service running
- ✅ Health checks passing

---

## 7. Rollback & Recovery

### 7.1 Rollback Plan

**Steps:**
1. Identify last known good commit: `git log --oneline`
2. Revert if needed: `git revert <commit-hash>`
3. Redeploy previous version
4. Verify health endpoints

### 7.2 Database Rollback

**Steps:**
```bash
# Rollback last migration
supabase db push --dry-run

# Or restore from backup
supabase db dump -f backup.sql
psql $DATABASE_URL < backup.sql
```

---

## 8. Gate Checklist

- [ ] Local linting passes
- [ ] Unit tests pass
- [ ] Migrations apply cleanly
- [ ] Database smoke checks pass
- [ ] Backend starts without errors
- [ ] Health endpoints respond correctly
- [ ] Integration tests pass
- [ ] CI/CD pipeline GREEN
- [ ] Container builds successfully
- [ ] Rollback plan documented

**Gate Status:** ❌ NOT PASSED / ✅ PASSED

**Signed Off By:** [NAME] | [DATE]

---

## 9. Notes

**Deferred Components:**
- Redis: Enable via `ENABLE_REDIS_HEALTHCHECK=true`
- Celery: Enable via `ENABLE_CELERY_HEALTHCHECK=true`

**Production-Ready Criteria:**
- All gates passed
- Documentation updated
- Phase marked as FROZEN

---

**Ende Template**
