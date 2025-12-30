# Phase 9: Projekt- & Release-Vorbereitung

**Status:** Draft
**Version:** 1.0
**Erstellt:** 2025-12-21
**Projekt:** PMS-Webapp

---

## Executive Summary

### Ziel
**Production-Ready Release-Strategie** für PMS-Webapp mit fokussiertem Ansatz auf:
- GitHub Workflow & Collaboration
- Deployment-Automation (Supabase → Backend → Workers → Frontend)
- Post-Deployment Testing (Smoke → Integration → E2E)
- Design-System-Vorbereitung (für spätere UI/UX-Phase)

### Scope
⚠️ **Wichtig:** Dieses Dokument enthält **Strategie & Checklisten**, keine Implementierung.

**In Scope:**
- ✅ GitHub-Setup-Strategie (Branches, Tags, Commits, PRs)
- ✅ Deployment-Reihenfolge & Environment-Setup
- ✅ Test-Strategie (Post-Deployment)
- ✅ Design-System-Vorbereitung (Struktur, ohne Design)

**Out of Scope:**
- ❌ Konkrete GitHub Actions YAML Files (kommt bei Implementierung)
- ❌ Deployment Scripts (kommt bei Implementierung)
- ❌ Test Code (kommt bei Implementierung)
- ❌ UI/UX Design (kommt in separater Phase)

---

## 1. GitHub Setup Strategie

### 1.1 Branch-Strategie: Trunk-Based Development (Simplified GitFlow)

**Rationale:**
- Small Team (1-3 Entwickler)
- Schnelle Iteration gewünscht
- Minimaler Overhead
- Trunk-Based Development mit kurzlebigen Feature Branches

**Branch-Struktur:**

```
main (protected)
  ↓
  develop (integration branch)
    ↓
    feature/xyz (kurzlebig, < 3 Tage)
    fix/abc (kurzlebig, < 1 Tag)

release/vX.Y.Z (für Releases)
hotfix/critical-bug (für Production Hotfixes)
```

#### Branch-Details

| Branch | Zweck | Lebensdauer | Protected | Deploy To |
|--------|-------|-------------|-----------|-----------|
| `main` | Production-ready code | Permanent | ✅ Yes | Production |
| `develop` | Integration branch | Permanent | ✅ Yes | Staging |
| `feature/*` | Feature development | < 3 Tage | ❌ No | Dev (optional) |
| `fix/*` | Bug fixes | < 1 Tag | ❌ No | Dev (optional) |
| `release/*` | Release preparation | < 1 Woche | ✅ Yes | Staging → Production |
| `hotfix/*` | Critical production fixes | < 2 Stunden | ❌ No | Production (urgent) |

#### Branch Protection Rules

**`main` Branch:**
```yaml
Protection Rules:
  - Require pull request reviews: 1 approver (für Team > 1)
  - Require status checks to pass:
    - CI Tests (pytest, linting)
    - Security Scan (Dependabot)
  - Require branches to be up to date: true
  - Restrict who can push: Admins only
  - Require signed commits: false (optional)
```

**`develop` Branch:**
```yaml
Protection Rules:
  - Require pull request reviews: 0 (für Solo-Dev) / 1 (für Team)
  - Require status checks to pass:
    - CI Tests (pytest, linting)
  - Require branches to be up to date: true
  - Restrict who can push: false
```

### 1.2 Commit Convention: Conventional Commits

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring (no feature/fix)
- `perf`: Performance improvement
- `test`: Add/update tests
- `build`: Build system or dependencies
- `ci`: CI/CD configuration
- `chore`: Maintenance tasks

**Scopes (PMS-Webapp specific):**
- `backend`: Backend API (FastAPI)
- `frontend`: Frontend (Next.js)
- `channel-manager`: Channel Manager Adapters
- `sync-engine`: Sync Engine (Celery tasks)
- `database`: Database schema, migrations
- `auth`: Authentication/Authorization
- `payments`: Payment processing (Stripe)
- `webhooks`: Webhook handlers
- `monitoring`: Observability (Prometheus, Sentry)
- `docs`: Documentation

**Examples:**
```bash
# Feature
feat(channel-manager): add Booking.com adapter
feat(frontend): implement property search UI

# Fix
fix(sync-engine): prevent duplicate booking imports
fix(payments): handle Stripe webhook timeout

# Refactor
refactor(backend): extract availability logic to service
refactor(frontend): migrate to App Router

# Docs
docs(api): update OpenAPI spec for bookings endpoint

# Chore
chore(deps): upgrade FastAPI to 0.109.0
```

**Breaking Changes:**
```bash
feat(backend)!: migrate to Supabase RLS

BREAKING CHANGE: All API endpoints now require tenant_id header.
Migration guide: docs/migration-v2.md
```

### 1.3 Pull Request (PR) Workflow

#### PR Template (`.github/PULL_REQUEST_TEMPLATE.md`)

```markdown
## Description
<!-- What does this PR do? -->

## Type of Change
- [ ] 🚀 New Feature
- [ ] 🐛 Bug Fix
- [ ] 📝 Documentation
- [ ] ♻️ Refactoring
- [ ] ⚡ Performance
- [ ] ✅ Tests

## Related Issues
<!-- Link to GitHub Issues: Closes #123 -->

## Changes
<!-- List of changes -->
-
-

## Testing
<!-- How was this tested? -->
- [ ] Unit Tests (coverage > 80%)
- [ ] Integration Tests
- [ ] Manual Testing

## Deployment Notes
<!-- Any special deployment steps? -->

## Checklist
- [ ] Code follows project conventions
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] CI checks passing
```

#### PR Review Process

**For Solo Developer:**
1. Create PR from `feature/*` → `develop`
2. Self-review code
3. Ensure CI passes
4. Merge (Squash & Merge)

**For Team (2+ Developers):**
1. Create PR from `feature/*` → `develop`
2. Request review from team member
3. Address feedback
4. Ensure CI passes
5. Merge after approval (Squash & Merge)

**Merge Strategies:**
- `feature/*` → `develop`: **Squash & Merge** (clean history)
- `develop` → `main`: **Merge Commit** (preserve history)
- `hotfix/*` → `main`: **Merge Commit** (preserve urgency context)

### 1.4 Tagging-Strategie: Semantic Versioning

**Format:** `vMAJOR.MINOR.PATCH` (z.B. `v1.0.0`, `v1.2.3`)

**Semantic Versioning:**
- **MAJOR:** Breaking changes (API contract breaks, DB migration required)
- **MINOR:** New features (backward-compatible)
- **PATCH:** Bug fixes (backward-compatible)

**Pre-Release:**
- `v1.0.0-alpha.1` (early development)
- `v1.0.0-beta.1` (feature-complete, testing)
- `v1.0.0-rc.1` (release candidate)

**Tag-Beispiele:**
```bash
# MVP Release (erste Production-Version)
v1.0.0 (2025-01-XX)
  - Direct Booking Engine
  - Airbnb Channel Manager
  - Property Management

# Feature Release (neue Channels)
v1.1.0 (2025-02-XX)
  - Booking.com Adapter
  - Revenue Analytics Dashboard

# Patch Release (Bugfixes)
v1.1.1 (2025-02-XX)
  - Fix: Airbnb webhook timeout
  - Fix: Pricing calculation edge case

# Breaking Change (DB migration)
v2.0.0 (2025-03-XX)
  - BREAKING: Migrate to new RLS schema
  - Migration: docs/migrations/v2.0.0.md
```

**Tag-Creation:**
```bash
# Create annotated tag (bevorzugt)
git tag -a v1.0.0 -m "Release v1.0.0: MVP Launch

Features:
- Direct Booking Engine
- Airbnb Channel Manager
- Property Management
- Multi-Tenancy (RLS)

Deployment: docs/deployment/v1.0.0.md"

# Push tag
git push origin v1.0.0
```

### 1.5 Issue & Project Management

#### Issue Labels

**Type:**
- `type: bug` - Bug reports
- `type: feature` - Feature requests
- `type: enhancement` - Improvements
- `type: docs` - Documentation
- `type: question` - Questions

**Priority:**
- `priority: critical` - Urgent (< 24h)
- `priority: high` - Important (< 1 week)
- `priority: medium` - Normal (< 2 weeks)
- `priority: low` - Nice-to-have

**Status:**
- `status: triage` - Needs triage
- `status: backlog` - Backlog
- `status: in-progress` - In progress
- `status: blocked` - Blocked
- `status: review` - In review

**Area:**
- `area: backend`
- `area: frontend`
- `area: channel-manager`
- `area: sync-engine`
- `area: database`
- `area: devops`

#### GitHub Projects (Optional, für Teams)

**Kanban Board:**
```
Backlog → Todo → In Progress → In Review → Done
```

**Milestones:**
- `MVP v1.0` (Direct Booking + Airbnb)
- `v1.1 - Booking.com Integration`
- `v1.2 - Revenue Analytics`
- `v2.0 - UI/UX Redesign`

### 1.6 GitHub Setup Checklist

- [ ] **Repository Setup**
  - [ ] Create repository (public/private)
  - [ ] Add README.md with setup instructions
  - [ ] Add LICENSE (MIT, Apache 2.0, oder Proprietary)
  - [ ] Add .gitignore (Python, Node.js, IDE)
  - [ ] Add CODEOWNERS (optional)

- [ ] **Branch Protection**
  - [ ] Enable branch protection for `main`
  - [ ] Enable branch protection for `develop`
  - [ ] Configure required status checks
  - [ ] Configure required reviews (für Teams)

- [ ] **Templates**
  - [ ] Add PR template (`.github/PULL_REQUEST_TEMPLATE.md`)
  - [ ] Add Issue templates (Bug Report, Feature Request)
  - [ ] Add Contributing Guide (`CONTRIBUTING.md`)

- [ ] **Automation**
  - [ ] Setup Dependabot (dependency updates)
  - [ ] Setup CodeQL (security scanning)
  - [ ] Add GitHub Actions workflows (CI/CD)

- [ ] **Documentation**
  - [ ] Update README with badges (build status, coverage, license)
  - [ ] Add CHANGELOG.md (auto-generate via Conventional Commits)
  - [ ] Document branch strategy in CONTRIBUTING.md

---

## 2. Deployment-Strategie

### 2.1 Environments

| Environment | Branch | Purpose | Uptime SLA | Deployment |
|-------------|--------|---------|------------|------------|
| **Development** | `feature/*` | Dev testing | None | Manual / On-demand |
| **Staging** | `develop` | Integration testing | 95% | Auto-deploy on push |
| **Production** | `main` | Live users | 99.9% | Manual approval |

#### Environment-Details

**Development:**
- **Purpose:** Lokale Entwicklung + Feature-Testing
- **Infrastructure:** Local (Docker Compose) oder Dev Cloud
- **Database:** Supabase Project (Dev)
- **Redis:** Local / Cloud Dev Instance
- **Domain:** `dev.pms-webapp.com` (optional)
- **Secrets:** `.env.development` (nicht committed)

**Staging:**
- **Purpose:** Pre-Production Testing (QA, Integration Tests)
- **Infrastructure:** Railway/Render (Backend), Vercel (Frontend)
- **Database:** Supabase Project (Staging)
- **Redis:** Upstash/Redis Cloud (Staging)
- **Domain:** `staging.pms-webapp.com`
- **Secrets:** GitHub Secrets (Staging)
- **Deployment:** Auto-deploy on `develop` push

**Production:**
- **Purpose:** Live Users
- **Infrastructure:** Railway/Render (Backend), Vercel (Frontend)
- **Database:** Supabase Project (Production)
- **Redis:** Upstash/Redis Cloud (Production)
- **Domain:** `app.pms-webapp.com`
- **Secrets:** GitHub Secrets (Production)
- **Deployment:** Manual approval after `main` push

### 2.2 Deployment-Reihenfolge

**Kritisch:** Deployment muss in korrekter Reihenfolge erfolgen, um Breaking Changes zu vermeiden.

#### Reihenfolge: Supabase → Backend → Workers → Frontend

```
1. Supabase (Database)
   ↓ (wait for migrations to complete)
2. Backend API (FastAPI)
   ↓ (wait for health check)
3. Celery Workers (Sync Engine)
   ↓ (wait for worker registration)
4. Frontend (Next.js)
```

**Rationale:**
- **Database first:** Schema muss existieren bevor Backend startet
- **Backend before Workers:** Workers brauchen API-Endpoints für Health Checks
- **Frontend last:** Frontend braucht Backend APIs

#### Detailed Deployment Steps

**Step 1: Supabase (Database)**
```bash
# 1. Run migrations
supabase db push --db-url $SUPABASE_DB_URL

# 2. Verify migrations
supabase db diff --db-url $SUPABASE_DB_URL

# 3. Update RLS policies (if changed)
supabase db push --include rls

# 4. Smoke test
psql $SUPABASE_DB_URL -c "SELECT version();"
psql $SUPABASE_DB_URL -c "SELECT COUNT(*) FROM properties;"
```

**Wait Condition:** Migrations completed + RLS policies applied

---

**Step 2: Backend API (FastAPI)**
```bash
# 1. Build Docker image (or deploy to Railway/Render)
docker build -t pms-backend:$VERSION ./backend

# 2. Deploy to infrastructure
railway up  # or: render deploy
# or: docker push + kubernetes apply

# 3. Wait for health check
curl https://api.pms-webapp.com/health
# Expected: {"status": "healthy", "version": "1.0.0"}

# 4. Smoke test
curl https://api.pms-webapp.com/api/properties
# Expected: 200 OK (mit leerer Liste oder Test-Daten)
```

**Wait Condition:** Health check returns 200 OK

---

**Step 3: Celery Workers (Sync Engine)**
```bash
# 1. Deploy workers (separate service)
railway up --service celery-worker
# or: docker run pms-backend:$VERSION celery worker

# 2. Wait for worker registration
celery -A app.worker inspect active
# Expected: Workers registered, no errors

# 3. Smoke test (trigger manual task)
celery -A app.worker inspect ping
# Expected: Pong from all workers
```

**Wait Condition:** Workers registered + ping successful

---

**Step 4: Frontend (Next.js)**
```bash
# 1. Build & Deploy (Vercel)
vercel deploy --prod
# or: npm run build && npm run start

# 2. Wait for deployment
vercel --prod
# Expected: Deployment successful

# 3. Smoke test
curl https://app.pms-webapp.com/
# Expected: 200 OK (HTML page)

# 4. Test API connection
curl https://app.pms-webapp.com/api/health
# Expected: 200 OK (Next.js API route → Backend API proxy)
```

**Wait Condition:** Frontend reachable + Backend API reachable

### 2.3 Infrastructure Setup

#### Supabase (Database + Auth + Realtime)

**Projects:**
- `pms-webapp-dev` (Development)
- `pms-webapp-staging` (Staging)
- `pms-webapp-prod` (Production)

**Setup Checklist:**
- [ ] Create Supabase projects (3 environments)
- [ ] Configure Database (PostgreSQL 15+)
- [ ] Enable RLS on all tables
- [ ] Setup Auth (Magic Links, OAuth)
- [ ] Configure Realtime (for live updates)
- [ ] Setup Storage (for property photos)
- [ ] Add Database Webhooks (for CDC)

**Connection Strings:**
```env
# Development
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres

# Staging
SUPABASE_URL=https://yyy.supabase.co
...

# Production
SUPABASE_URL=https://zzz.supabase.co
...
```

#### Backend (FastAPI + Celery)

**Hosting Options:**
1. **Railway** (bevorzugt, einfach)
   - Auto-deploys from GitHub
   - Built-in Postgres/Redis (optional)
   - Simple scaling
   - $5-20/month (Hobby Plan)

2. **Render** (Alternative)
   - Free Tier verfügbar
   - Auto-deploys from GitHub
   - $7-25/month (Starter Plan)

3. **Fly.io** (Alternative)
   - Global edge deployment
   - $5-15/month

**Services:**
- `backend-api` (FastAPI, Uvicorn)
- `celery-worker` (Celery, async tasks)
- `celery-beat` (Celery, scheduled tasks)

**Scaling:**
- **Staging:** 1 API instance, 1 worker
- **Production:** 2-3 API instances (load-balanced), 2-3 workers

#### Redis (Cache + Queue + Locks)

**Hosting Options:**
1. **Upstash** (bevorzugt, serverless)
   - Serverless Redis
   - Pay-per-request
   - Global replication
   - Free Tier: 10k requests/day

2. **Redis Cloud** (Alternative)
   - Managed Redis
   - $5-30/month

**Usage:**
- Celery Broker (task queue)
- Rate Limiting (channel sync)
- Idempotency Cache (webhooks)
- Distributed Locks (double-booking prevention)

#### Frontend (Next.js)

**Hosting: Vercel** (bevorzugt)
- Native Next.js support
- Auto-deploys from GitHub
- Edge Functions (API routes)
- Free Tier für Hobby (1 project)
- Pro: $20/month (unlimited projects)

**Configuration:**
```json
// vercel.json
{
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/next"
    }
  ],
  "env": {
    "NEXT_PUBLIC_API_URL": "https://api.pms-webapp.com",
    "NEXT_PUBLIC_SUPABASE_URL": "https://xxx.supabase.co",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY": "@supabase-anon-key"
  },
  "regions": ["fra1"]
}
```

### 2.4 Environment Variables Management

#### Secrets per Environment

**Development (`.env.development`, NOT committed):**
```env
# Supabase
SUPABASE_URL=https://dev.supabase.co
SUPABASE_ANON_KEY=dev_anon_key
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://localhost:6379

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...

# Channel Manager
AIRBNB_CLIENT_ID=dev_client_id
AIRBNB_CLIENT_SECRET=dev_secret

# Encryption
ENCRYPTION_KEY=dev_44_char_fernet_key_here...
```

**Staging (GitHub Secrets):**
```yaml
# GitHub Secrets (Settings → Secrets → Actions)
STAGING_SUPABASE_URL: https://staging.supabase.co
STAGING_DATABASE_URL: postgresql://...
STAGING_REDIS_URL: redis://...
STAGING_STRIPE_SECRET_KEY: sk_test_...
STAGING_ENCRYPTION_KEY: staging_44_char_key...
STAGING_AIRBNB_CLIENT_SECRET: staging_secret
```

**Production (GitHub Secrets):**
```yaml
# GitHub Secrets (Settings → Secrets → Actions)
PROD_SUPABASE_URL: https://prod.supabase.co
PROD_DATABASE_URL: postgresql://...
PROD_REDIS_URL: redis://...
PROD_STRIPE_SECRET_KEY: sk_live_...  # LIVE KEY!
PROD_ENCRYPTION_KEY: prod_44_char_key...
PROD_AIRBNB_CLIENT_SECRET: prod_secret
```

**Security Best Practices:**
- ✅ Never commit secrets to Git
- ✅ Use GitHub Secrets for CI/CD
- ✅ Rotate secrets regularly (quarterly)
- ✅ Use different keys per environment
- ✅ Use Stripe Test Keys in Dev/Staging
- ✅ Encrypt sensitive data at rest (OAuth tokens)

### 2.5 Rollback-Strategie

#### Rollback-Trigger

**When to Rollback:**
- ❌ Critical bug in production (data loss, crashes)
- ❌ Performance degradation (> 50% slower)
- ❌ Security vulnerability introduced
- ❌ Breaking change not backward-compatible

**When NOT to Rollback:**
- ✅ Minor UI bug (fix forward)
- ✅ Non-critical feature broken (disable feature flag)
- ✅ Small performance regression (< 10%)

#### Rollback-Reihenfolge (Reverse of Deployment)

```
1. Frontend (Next.js)
   ↓ (revert to previous version)
2. Celery Workers
   ↓ (stop workers, revert, restart)
3. Backend API
   ↓ (revert to previous version)
4. Supabase (Database)
   ↓ (run DOWN migrations, if applicable)
```

**Rollback Steps:**

**Step 1: Frontend Rollback**
```bash
# Vercel: Promote previous deployment
vercel rollback
# or: vercel promote <previous-deployment-url>
```

**Step 2: Workers Rollback**
```bash
# Stop workers
celery -A app.worker control shutdown

# Deploy previous version
railway rollback --service celery-worker
# or: docker run pms-backend:v1.0.0 celery worker

# Restart workers
railway restart --service celery-worker
```

**Step 3: Backend Rollback**
```bash
# Deploy previous version
railway rollback --service backend-api
# or: docker run pms-backend:v1.0.0

# Verify health
curl https://api.pms-webapp.com/health
```

**Step 4: Database Rollback (if needed)**
```bash
# Run DOWN migration (only if schema changed)
alembic downgrade -1

# Verify schema
psql $DATABASE_URL -c "\dt"
```

**Rollback Validation:**
- [ ] Frontend reachable
- [ ] Backend API health check passes
- [ ] Workers active
- [ ] Database schema correct
- [ ] Smoke tests passing

### 2.6 Deployment Checklist

#### Pre-Deployment Checklist

- [ ] **Code Quality**
  - [ ] All tests passing (pytest, coverage > 80%)
  - [ ] Linting passing (ruff, black, mypy)
  - [ ] No security vulnerabilities (Dependabot, CodeQL)
  - [ ] PR approved (für Teams)

- [ ] **Environment Variables**
  - [ ] All required env vars documented in `.env.example`
  - [ ] Secrets configured in GitHub Secrets
  - [ ] Encryption keys rotated (if needed)

- [ ] **Database**
  - [ ] Migrations tested locally
  - [ ] Migrations tested in Staging
  - [ ] Backup created (before migration)
  - [ ] Rollback plan documented

- [ ] **Dependencies**
  - [ ] `requirements.txt` updated (backend)
  - [ ] `package.json` updated (frontend)
  - [ ] No major version bumps (unless tested)

- [ ] **Documentation**
  - [ ] CHANGELOG.md updated
  - [ ] API docs updated (OpenAPI)
  - [ ] Deployment notes documented (if special steps)

#### During Deployment

- [ ] **Deployment Execution**
  - [ ] Deploy to Staging first
  - [ ] Run smoke tests in Staging
  - [ ] Get approval for Production (für Teams)
  - [ ] Deploy to Production (in correct order)
  - [ ] Monitor deployment logs (Railway, Vercel, Sentry)

- [ ] **Health Checks**
  - [ ] Supabase: Database accessible
  - [ ] Backend: Health endpoint returns 200
  - [ ] Workers: Celery workers registered
  - [ ] Frontend: Homepage loads

#### Post-Deployment Checklist

- [ ] **Smoke Tests** (5-10 min after deployment)
  - [ ] Homepage loads
  - [ ] User can login
  - [ ] API endpoints respond
  - [ ] Database queries work
  - [ ] Redis cache works
  - [ ] Celery tasks execute

- [ ] **Integration Tests** (15-30 min after deployment)
  - [ ] Direct Booking Flow (end-to-end)
  - [ ] Channel Sync (Airbnb)
  - [ ] Payment Processing (Stripe)
  - [ ] Webhook Processing

- [ ] **Monitoring**
  - [ ] Check Prometheus metrics (no spike in errors)
  - [ ] Check Sentry (no new errors)
  - [ ] Check Logs (no critical errors)
  - [ ] Check Performance (response times < SLA)

- [ ] **Communication**
  - [ ] Notify team of successful deployment
  - [ ] Update CHANGELOG.md (if not auto-generated)
  - [ ] Tag release in GitHub (`git tag vX.Y.Z`)

---

## 3. Test-Strategie (Post-Deployment)

### 3.1 Test-Pyramide

```
        E2E Tests (5%)
       /           \
      /  Integration  \
     /    Tests (25%)  \
    /___________________\
    Unit Tests (70%)
```

**Rationale:**
- **70% Unit Tests:** Fast, isolated, hohe Coverage
- **25% Integration Tests:** API + Database + External Services
- **5% E2E Tests:** Critical User Journeys (expensive, slow)

### 3.2 Smoke Tests (Post-Deployment)

**Purpose:** Schnelle Validierung, dass Deployment nicht kritische Funktionen gebrochen hat

**Execution Time:** 2-5 Minuten
**When:** Sofort nach Deployment (jede Environment)

#### Smoke Test Checklist

**Infrastructure:**
- [ ] `GET /health` → 200 OK (Backend)
- [ ] `GET /` → 200 OK (Frontend)
- [ ] Database connection works (`SELECT 1`)
- [ ] Redis connection works (`PING`)
- [ ] Celery workers active (`celery inspect active`)

**Core Functionality:**
- [ ] User can access login page
- [ ] User can search properties (empty result OK)
- [ ] API returns valid JSON (no 500 errors)

**Example Smoke Test Script:**
```bash
#!/bin/bash
# smoke-test.sh

API_URL=${API_URL:-https://api.pms-webapp.com}
FRONTEND_URL=${FRONTEND_URL:-https://app.pms-webapp.com}

echo "=== Smoke Tests ==="

# Backend Health
echo "Testing Backend Health..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/health)
if [ $STATUS -eq 200 ]; then
  echo "✅ Backend Health: PASS"
else
  echo "❌ Backend Health: FAIL (HTTP $STATUS)"
  exit 1
fi

# Frontend Homepage
echo "Testing Frontend Homepage..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" $FRONTEND_URL)
if [ $STATUS -eq 200 ]; then
  echo "✅ Frontend Homepage: PASS"
else
  echo "❌ Frontend Homepage: FAIL (HTTP $STATUS)"
  exit 1
fi

# Database Connection
echo "Testing Database Connection..."
RESPONSE=$(curl -s $API_URL/health/db)
if [[ $RESPONSE == *"healthy"* ]]; then
  echo "✅ Database Connection: PASS"
else
  echo "❌ Database Connection: FAIL"
  exit 1
fi

echo "=== All Smoke Tests Passed ==="
```

### 3.3 Integration Tests (Post-Deployment)

**Purpose:** Validierung von API-Integrationen, Datenbank-Operationen, externe Services

**Execution Time:** 10-20 Minuten
**When:** Nach Smoke Tests (Staging Environment)

#### Integration Test Categories

**1. API Integration Tests**
- Property CRUD (Create, Read, Update, Delete)
- Booking Creation & Management
- User Authentication (Supabase)
- Channel Connection (OAuth flow)

**2. Database Integration Tests**
- RLS Policies (Multi-Tenancy)
- Exclusion Constraints (Double-Booking prevention)
- Triggers (Availability auto-update)
- Transactions (Atomic operations)

**3. External Service Integration Tests**
- Stripe Payment (using Test Mode)
- Airbnb API (using Sandbox)
- Supabase Auth (Magic Links)
- Redis Cache (Set/Get/Delete)

**4. Celery Task Integration Tests**
- Booking Expiration Task (30-min timeout)
- Channel Sync Task (Availability, Pricing)
- Email Task (Confirmation, Reminder)

#### Example Integration Test (Property CRUD)

```python
# tests/integration/test_property_crud.py

import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_property_crud_flow(async_client: AsyncClient, auth_headers):
    """Test complete Property CRUD flow"""

    # 1. Create Property
    property_data = {
        "name": "Test Villa",
        "address": "123 Test St",
        "property_type": "villa",
        "bedrooms": 3,
        "bathrooms": 2,
        "max_guests": 6
    }

    response = await async_client.post(
        "/api/properties",
        json=property_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    property_id = response.json()["id"]

    # 2. Read Property
    response = await async_client.get(
        f"/api/properties/{property_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test Villa"

    # 3. Update Property
    response = await async_client.patch(
        f"/api/properties/{property_id}",
        json={"name": "Updated Villa"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Villa"

    # 4. Delete Property
    response = await async_client.delete(
        f"/api/properties/{property_id}",
        headers=auth_headers
    )
    assert response.status_code == 204

    # 5. Verify Deleted
    response = await async_client.get(
        f"/api/properties/{property_id}",
        headers=auth_headers
    )
    assert response.status_code == 404
```

### 3.4 E2E Tests (Post-Deployment)

**Purpose:** Validierung von kritischen User Journeys (end-to-end)

**Execution Time:** 20-40 Minuten
**When:** Vor Production Deployment (Staging Environment)

**Tool:** Playwright (für Frontend E2E)

#### Critical User Journeys

**1. Direct Booking Flow (Guest)**
```
Search Property → Select Property → Enter Guest Info → Payment → Confirmation
```

**2. Property Management (Owner)**
```
Login → Create Property → Upload Photos → Set Pricing → Publish
```

**3. Channel Connection (Owner)**
```
Login → Connect Airbnb (OAuth) → Sync Availability → Verify Sync
```

**4. Booking Management (Staff)**
```
Login → View Bookings → Check-in Guest → Update Status
```

#### Example E2E Test (Direct Booking)

```typescript
// tests/e2e/direct-booking.spec.ts

import { test, expect } from '@playwright/test';

test('Guest can complete Direct Booking flow', async ({ page }) => {
  // 1. Search Property
  await page.goto('https://staging.pms-webapp.com');
  await page.fill('[data-testid="search-location"]', 'Berlin');
  await page.fill('[data-testid="search-checkin"]', '2025-07-01');
  await page.fill('[data-testid="search-checkout"]', '2025-07-05');
  await page.fill('[data-testid="search-guests"]', '2');
  await page.click('[data-testid="search-button"]');

  // 2. Select Property
  await expect(page.locator('[data-testid="property-card"]').first()).toBeVisible();
  await page.locator('[data-testid="property-card"]').first().click();

  // 3. Click "Book Now"
  await page.click('[data-testid="book-now-button"]');

  // 4. Enter Guest Info
  await page.fill('[data-testid="guest-name"]', 'John Doe');
  await page.fill('[data-testid="guest-email"]', 'john@example.com');
  await page.fill('[data-testid="guest-phone"]', '+49123456789');
  await page.click('[data-testid="continue-to-payment"]');

  // 5. Payment (Stripe Test Mode)
  const stripeFrame = page.frameLocator('iframe[name^="__privateStripeFrame"]');
  await stripeFrame.fill('[name="cardnumber"]', '4242424242424242');
  await stripeFrame.fill('[name="exp-date"]', '12/25');
  await stripeFrame.fill('[name="cvc"]', '123');
  await page.click('[data-testid="pay-button"]');

  // 6. Confirmation
  await expect(page.locator('[data-testid="booking-confirmation"]')).toBeVisible({ timeout: 10000 });
  await expect(page.locator('[data-testid="booking-id"]')).toContainText(/^[A-Z0-9]{8}$/);
});
```

### 3.5 Test-Strategie Checklist

#### Pre-Deployment Testing

- [ ] **Local Development**
  - [ ] Unit Tests passing (`pytest tests/unit`)
  - [ ] Integration Tests passing (`pytest tests/integration`)
  - [ ] Code coverage > 80% (`pytest --cov`)
  - [ ] Linting passing (`ruff check`, `black --check`)
  - [ ] Type checking passing (`mypy app`)

#### Post-Deployment Testing (Staging)

- [ ] **Smoke Tests** (5 min)
  - [ ] Infrastructure health checks
  - [ ] Core functionality accessible
  - [ ] No 500 errors

- [ ] **Integration Tests** (15 min)
  - [ ] API CRUD operations
  - [ ] Database operations (RLS, constraints)
  - [ ] External services (Stripe Test Mode, Airbnb Sandbox)
  - [ ] Celery tasks

- [ ] **E2E Tests** (30 min)
  - [ ] Direct Booking Flow
  - [ ] Property Management Flow
  - [ ] Channel Connection Flow
  - [ ] Booking Management Flow

#### Pre-Production Deployment

- [ ] **Staging Sign-Off**
  - [ ] All tests passing in Staging
  - [ ] Performance metrics acceptable (< SLA)
  - [ ] No critical errors in Sentry
  - [ ] Approval from stakeholders (für Teams)

#### Post-Production Deployment

- [ ] **Smoke Tests** (5 min)
  - [ ] Production infrastructure health
  - [ ] Homepage accessible
  - [ ] Login works

- [ ] **Monitoring** (24h)
  - [ ] Monitor Sentry for new errors
  - [ ] Monitor Prometheus for performance regressions
  - [ ] Monitor user feedback (support tickets)

---

## 4. Design-System-Vorbereitung (für UI/UX-Phase)

**⚠️ Wichtig:** Diese Sektion definiert **Struktur & Ansatz**, KEINE konkreten Design-Werte.

### 4.1 Design-Token-Struktur

**Purpose:** Konsistente Design-Werte (Colors, Typography, Spacing, etc.) über gesamte App

**Tool:** CSS Variables oder Styled-System (z.B. Tailwind Config)

#### Token-Kategorien

**1. Colors**
```json
{
  "colors": {
    "brand": {
      "primary": "TBD",
      "secondary": "TBD",
      "accent": "TBD"
    },
    "neutral": {
      "50": "TBD",
      "100": "TBD",
      "..": "TBD",
      "900": "TBD"
    },
    "semantic": {
      "success": "TBD",
      "warning": "TBD",
      "error": "TBD",
      "info": "TBD"
    }
  }
}
```

**2. Typography**
```json
{
  "typography": {
    "fontFamily": {
      "heading": "TBD",
      "body": "TBD",
      "mono": "TBD"
    },
    "fontSize": {
      "xs": "TBD",
      "sm": "TBD",
      "base": "TBD",
      "lg": "TBD",
      "xl": "TBD",
      "2xl": "TBD",
      "3xl": "TBD"
    },
    "fontWeight": {
      "normal": "TBD",
      "medium": "TBD",
      "semibold": "TBD",
      "bold": "TBD"
    },
    "lineHeight": {
      "tight": "TBD",
      "normal": "TBD",
      "relaxed": "TBD"
    }
  }
}
```

**3. Spacing**
```json
{
  "spacing": {
    "0": "0",
    "1": "TBD",
    "2": "TBD",
    "3": "TBD",
    "4": "TBD",
    "6": "TBD",
    "8": "TBD",
    "12": "TBD",
    "16": "TBD",
    "24": "TBD"
  }
}
```

**4. Breakpoints (Responsive)**
```json
{
  "breakpoints": {
    "sm": "640px",
    "md": "768px",
    "lg": "1024px",
    "xl": "1280px",
    "2xl": "1536px"
  }
}
```

**5. Shadows, Borders, Radii**
```json
{
  "shadows": {
    "sm": "TBD",
    "md": "TBD",
    "lg": "TBD"
  },
  "borders": {
    "width": {
      "1": "TBD",
      "2": "TBD"
    },
    "radius": {
      "sm": "TBD",
      "md": "TBD",
      "lg": "TBD",
      "full": "9999px"
    }
  }
}
```

### 4.2 Component-Architektur: Atomic Design

**Hierarchie:**
```
Atoms (kleinste Bausteine)
  ↓
Molecules (Kombinationen von Atoms)
  ↓
Organisms (Komplexe UI-Sections)
  ↓
Templates (Page-Layouts)
  ↓
Pages (Konkrete Seiten)
```

#### Atoms (Beispiele)
- Button (primary, secondary, ghost, danger)
- Input (text, email, tel, date)
- Label
- Badge (status, count)
- Icon
- Avatar
- Spinner (loading)

#### Molecules (Beispiele)
- FormField (Label + Input + ErrorMessage)
- SearchBar (Input + SearchIcon + Button)
- PropertyCard (Image + Title + Price + Badge)
- DateRangePicker (DateInput + DateInput)
- UserMenu (Avatar + Dropdown)

#### Organisms (Beispiele)
- Header (Logo + Navigation + UserMenu)
- PropertySearchForm (SearchBar + Filters + Button)
- PropertyGrid (PropertyCard[])
- BookingCalendar (Calendar + AvailabilityOverlay)
- CheckoutForm (FormField[] + PaymentElement + Button)

#### Templates (Beispiele)
- DashboardLayout (Header + Sidebar + MainContent)
- PropertyDetailLayout (Header + PropertyGallery + PropertyInfo + BookingWidget)
- CheckoutLayout (Header + ProgressBar + CheckoutForm)

#### Pages (Beispiele)
- HomePage (PropertySearchForm + FeaturedProperties)
- PropertyDetailPage (PropertyDetailLayout + BookingWidget)
- CheckoutPage (CheckoutLayout + CheckoutForm)
- DashboardPage (DashboardLayout + PropertyList + Stats)

### 4.3 Theming-Strategie

**Modes:**
- Light Mode (default)
- Dark Mode (optional, Post-MVP)

**Approach:** CSS Variables + `data-theme` attribute

```css
/* Light Mode (default) */
:root {
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f7f7f7;
  --color-text-primary: #1a1a1a;
  --color-text-secondary: #6b6b6b;
}

/* Dark Mode (optional) */
[data-theme="dark"] {
  --color-bg-primary: #1a1a1a;
  --color-bg-secondary: #2a2a2a;
  --color-text-primary: #ffffff;
  --color-text-secondary: #a0a0a0;
}
```

**Theme Toggle:**
```typescript
// useTheme hook (Post-MVP)
const [theme, setTheme] = useState<'light' | 'dark'>('light');

const toggleTheme = () => {
  const newTheme = theme === 'light' ? 'dark' : 'light';
  setTheme(newTheme);
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
};
```

### 4.4 Accessibility-Guidelines (WCAG 2.1 AA)

#### Checklisten

**Color Contrast:**
- [ ] Text vs Background: 4.5:1 (normal text), 3:1 (large text)
- [ ] Interactive Elements: 3:1 (buttons, links)
- [ ] Tool: WebAIM Contrast Checker

**Keyboard Navigation:**
- [ ] All interactive elements focusable (Tab)
- [ ] Focus indicators visible (outline, ring)
- [ ] No keyboard traps
- [ ] Skip links (für long pages)

**Screen Reader Support:**
- [ ] Semantic HTML (`<header>`, `<nav>`, `<main>`, `<footer>`)
- [ ] ARIA labels for icons (`aria-label="Search"`)
- [ ] ARIA landmarks (`role="navigation"`)
- [ ] Alt text for images (`alt="Property photo"`)

**Forms:**
- [ ] Labels for all inputs (`<label htmlFor="email">`)
- [ ] Error messages associated (`aria-describedby="email-error"`)
- [ ] Required fields indicated (`aria-required="true"`)
- [ ] Autocomplete attributes (`autocomplete="email"`)

**Responsive Design:**
- [ ] Mobile-first approach
- [ ] Touch targets > 44x44px
- [ ] Text scalable (no fixed font sizes)
- [ ] Viewport meta tag (`<meta name="viewport" content="width=device-width">`)

### 4.5 Component-Library-Ansatz

**Base:** Shadcn/UI (Tailwind CSS, Radix UI)

**Rationale:**
- ✅ Copy-paste components (no npm install)
- ✅ Full customization (own tokens)
- ✅ Accessible (Radix UI primitives)
- ✅ TypeScript support

**Alternative:** MUI (Material-UI), Chakra UI

**Component-Struktur:**
```
src/components/
  atoms/
    Button.tsx
    Input.tsx
    Label.tsx
    Badge.tsx
  molecules/
    FormField.tsx
    SearchBar.tsx
    PropertyCard.tsx
  organisms/
    Header.tsx
    PropertySearchForm.tsx
    BookingCalendar.tsx
  templates/
    DashboardLayout.tsx
    PropertyDetailLayout.tsx
  pages/
    HomePage.tsx
    PropertyDetailPage.tsx
```

### 4.6 Design-System Checklist

#### Phase 1: Foundation (Vor UI-Implementierung)

- [ ] **Design Tokens**
  - [ ] Define Color Palette (brand, neutral, semantic)
  - [ ] Define Typography Scale (fonts, sizes, weights)
  - [ ] Define Spacing Scale (4px, 8px, 12px, 16px, ...)
  - [ ] Define Breakpoints (sm, md, lg, xl)
  - [ ] Export tokens to JSON/CSS Variables

- [ ] **Component Inventory**
  - [ ] List all needed components (Atoms, Molecules, Organisms)
  - [ ] Prioritize components (MVP vs Post-MVP)
  - [ ] Document component API (props, variants)

- [ ] **Accessibility Audit**
  - [ ] Define color contrast requirements (WCAG 2.1 AA)
  - [ ] Plan keyboard navigation strategy
  - [ ] Plan screen reader support (ARIA)

#### Phase 2: Implementation (Während UI-Entwicklung)

- [ ] **Atoms**
  - [ ] Button (primary, secondary, ghost, danger)
  - [ ] Input (text, email, tel, date)
  - [ ] Label, Badge, Icon, Avatar, Spinner

- [ ] **Molecules**
  - [ ] FormField, SearchBar, PropertyCard, DateRangePicker

- [ ] **Organisms**
  - [ ] Header, PropertySearchForm, BookingCalendar, CheckoutForm

- [ ] **Templates & Pages**
  - [ ] DashboardLayout, PropertyDetailLayout, CheckoutLayout
  - [ ] HomePage, PropertyDetailPage, CheckoutPage

#### Phase 3: Documentation (Post-Implementation)

- [ ] **Storybook** (optional, für Teams)
  - [ ] Setup Storybook
  - [ ] Document all components (props, variants, examples)
  - [ ] Add accessibility checks (Storybook a11y addon)

- [ ] **Design-System Docs**
  - [ ] Document design tokens
  - [ ] Document component usage (Markdown)
  - [ ] Add examples & code snippets

---

## 5. Checklisten (Übersicht)

### 5.1 GitHub Setup Checklist (Einmalig)

- [ ] Repository Setup
  - [ ] Create repo (public/private)
  - [ ] Add README, LICENSE, .gitignore, CODEOWNERS
  - [ ] Setup branch protection (main, develop)
  - [ ] Add PR/Issue templates
  - [ ] Configure Dependabot, CodeQL

### 5.2 Pre-Deployment Checklist (Jeder Release)

- [ ] Code Quality
  - [ ] Tests passing (> 80% coverage)
  - [ ] Linting passing
  - [ ] Security scan passed
  - [ ] PR approved

- [ ] Environment
  - [ ] Env vars documented
  - [ ] Secrets configured (GitHub Secrets)
  - [ ] Migrations tested

- [ ] Documentation
  - [ ] CHANGELOG updated
  - [ ] API docs updated

### 5.3 Deployment Checklist (Production)

- [ ] Deploy to Staging first
- [ ] Run smoke tests (Staging)
- [ ] Run integration tests (Staging)
- [ ] Run E2E tests (Staging)
- [ ] Get approval (für Teams)
- [ ] Deploy to Production (Supabase → Backend → Workers → Frontend)
- [ ] Run smoke tests (Production)
- [ ] Monitor for 24h (Sentry, Prometheus)

### 5.4 Rollback Checklist (Wenn nötig)

- [ ] Identify issue (critical bug, performance, security)
- [ ] Decide: Rollback vs Fix-Forward
- [ ] Rollback (Frontend → Workers → Backend → Database)
- [ ] Verify rollback (smoke tests)
- [ ] Postmortem (root cause analysis)

### 5.5 Design-System Checklist (Vor UI-Phase)

- [ ] Define design tokens (colors, typography, spacing)
- [ ] Create component inventory (atoms, molecules, organisms)
- [ ] Plan accessibility (WCAG 2.1 AA)
- [ ] Setup component library (Shadcn/UI)
- [ ] Document component API

---

## 6. Timeline & Dependencies

### 6.1 Phase-Dependencies

```
Phase 9 (Release Prep) - NOW
  ↓
Phase 2 (Direct Booking) - 4-6 Wochen
  ↓ (dependency: Backend APIs)
Phase 3 (Channel Manager) - 4-6 Wochen
  ↓ (dependency: Sync Engine)
Phase 4 (Multi-Tenant) - 2-3 Wochen
  ↓ (dependency: RLS)
Phase 5 (MVP Polish) - 2-3 Wochen
  ↓ (dependency: E2E Tests)
MVP Launch - v1.0.0
  ↓
UI/UX Phase - Post-MVP
  ↓ (dependency: Design System)
Advanced Features - Post-MVP
```

### 6.2 GitHub Setup Timeline

**Week 1: Repository Setup**
- Day 1-2: Create repo, add templates, configure protection
- Day 3-5: Setup CI/CD (GitHub Actions)
- Day 6-7: Test workflows, documentation

**Week 2: Deployment Setup**
- Day 1-3: Setup Supabase (3 environments)
- Day 4-6: Setup Backend (Railway/Render)
- Day 7: Setup Frontend (Vercel)

**Week 3: Testing Setup**
- Day 1-3: Write smoke tests
- Day 4-6: Write integration tests
- Day 7: Write E2E tests (skeleton)

**Week 4: Design Prep**
- Day 1-3: Define design tokens (structure)
- Day 4-6: Create component inventory
- Day 7: Document design system approach

### 6.3 Critical Path

**Blocker:** Keine Frontend-Implementierung vorhanden
- **Impact:** E2E Tests können nicht geschrieben werden (nur Struktur)
- **Mitigation:** E2E Tests vorbereiten (Playwright Setup, Test-Struktur), Tests schreiben sobald Frontend existiert

**Blocker:** Keine Design-Tokens definiert
- **Impact:** UI-Implementierung verzögert
- **Mitigation:** Design-Token-Struktur vorbereiten, konkrete Werte später (UI/UX-Phase)

---

## 7. Appendix

### 7.1 Glossar

| Begriff | Definition |
|---------|------------|
| **Trunk-Based Development** | Branch-Strategie mit kurzlebigen Feature Branches + main/develop |
| **Conventional Commits** | Commit-Format mit type/scope/subject |
| **Semantic Versioning** | Versioning-Schema: MAJOR.MINOR.PATCH |
| **Smoke Tests** | Schnelle Tests für grundlegende Funktionalität |
| **Integration Tests** | Tests für API + Database + External Services |
| **E2E Tests** | End-to-End Tests für kritische User Journeys |
| **Design Tokens** | Design-Werte (Colors, Typography, Spacing, etc.) |
| **Atomic Design** | Component-Hierarchie: Atoms → Molecules → Organisms → Templates → Pages |
| **WCAG 2.1 AA** | Accessibility-Standard (Web Content Accessibility Guidelines) |

### 7.2 Referenzen

**GitHub Workflow:**
- [Trunk-Based Development](https://trunkbaseddevelopment.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

**Deployment:**
- [Railway Docs](https://docs.railway.app/)
- [Vercel Docs](https://vercel.com/docs)
- [Supabase Docs](https://supabase.com/docs)

**Testing:**
- [Playwright Docs](https://playwright.dev/)
- [Pytest Docs](https://docs.pytest.org/)
- [Testing Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)

**Design System:**
- [Atomic Design](https://bradfrost.com/blog/post/atomic-web-design/)
- [Design Tokens](https://www.w3.org/community/design-tokens/)
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/)
- [Shadcn/UI](https://ui.shadcn.com/)

---

**Ende des Release-Plans**

**Nächster Schritt:** Implementierung von Phase 2 (Direct Booking Engine) + GitHub Setup
