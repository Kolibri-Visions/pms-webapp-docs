# Deployment & CI/CD

> Source of Truth: `backend/Dockerfile`, `backend/Dockerfile.worker`, `frontend/nixpacks.toml`, `.github/workflows/`

## Deployment-Architektur

Alle Apps laufen auf **Coolify** (Self-hosted Docker) auf einem VPS.

| App | Image/Build | Port | Watch Path |
|-----|-------------|------|------------|
| Backend API | `backend/Dockerfile` (python:3.12-slim) | 8000 | `/backend/**` |
| Worker | `backend/Dockerfile.worker` (python:3.12-slim) | — | `/backend/**` |
| Admin Frontend | `frontend/nixpacks.toml` (Node 20) | 3000 | `/frontend/**` |
| Public Website | `frontend/nixpacks.toml` (Node 20) | 3000 | `/frontend/**` |
| Supabase | Managed (Supabase Cloud) | — | — |

Watch Paths sorgen dafuer, dass nur relevante Apps bei Commits deployen.

## Backend Dockerfile

```dockerfile
FROM python:3.12-slim
RUN useradd -m -u 1000 app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/logs && chown app:app /app/logs
EXPOSE 8000
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Worker Dockerfile

```dockerfile
FROM python:3.12-slim
# System-Deps: libpq-dev, procps, netcat, bash
RUN useradd -m -u 10001 appuser
ENV CELERY_POOL=threads
ENV CELERY_CONCURRENCY=4
ENV CELERY_LOGLEVEL=INFO
# Wait-for-deps: supabase-db:5432, coolify-redis:6379
CMD ["bash", "/app/scripts/ops/start_worker.sh"]
```

## Frontend (Nixpacks)

```toml
[phases.setup]
nixPkgs = ["nodejs_20"]    # Node 22 bricht Next.js 14.1!

[phases.install]
cmds = ["npm ci --no-audit --no-fund"]

[phases.build]
cmds = ["npm run build"]

[start]
cmd = "npm run start"
```

**Wichtig:** `NPM_CONFIG_PRODUCTION=false` muss gesetzt sein (sonst werden devDependencies uebersprungen).

## Health Checks

### GET /health (Liveness)

Gibt immer 200 zurueck. Keine DB/Redis-Abhaengigkeit.

```json
{"status": "up", "checked_at": "2026-03-11T12:00:00Z"}
```

### GET /health/ready (Readiness)

| Check | Pflicht | Feature-Gate |
|-------|---------|--------------|
| Database (asyncpg) | Ja | — |
| Redis | Nein | `ENABLE_REDIS_HEALTHCHECK` |
| Celery Worker | Nein | `ENABLE_CELERY_HEALTHCHECK` |
| Audit Queue | Nein | `ENABLE_AUDIT_QUEUE_HEALTHCHECK` |

Gibt 200 wenn DB erreichbar, sonst 503.

### GET /api/v1/ops/version

```json
{
  "version": "1.0.0",
  "source_commit": "abc1234",
  "python_version": "3.12.x",
  "uptime_seconds": 3600
}
```

## CI/CD Workflows (GitHub Actions)

| Workflow | Datei | Trigger | Zweck |
|----------|-------|---------|-------|
| CI Backend | `ci-backend.yml` | Push/PR (backend/**) | pytest, ruff lint |
| CI Frontend | `ci-frontend.yml` | Push/PR (frontend/**) | `npm run build` |
| E2E Tests | `ci-e2e.yml` | Nach Frontend CI auf main | Playwright Tests |
| Post-Deploy | `post-deploy-check.yml` | Nach Backend CI auf main | Health + Version Check |
| Lint Full | `lint-full.yml` | PR (backend/app/**) | ruff + mypy |
| CodeQL | `codeql.yml` | Manuell + Weekly | Security Scanning |
| Publish Docs | `publish-docs.yml` | Push (docs/**) | Docs publizieren |

### Pflicht-Variablen (GitHub Repository Variables)

| Variable | Zweck | Beispiel |
|----------|-------|---------|
| `BACKEND_URL` | Post-Deploy Health Check | `https://api.example.com` |
| `ADMIN_URL` | E2E Tests + Post-Deploy | `https://admin.example.com` |

### Pflicht-Secrets

| Secret | Zweck |
|--------|-------|
| `E2E_USER_EMAIL` | E2E Test-User |
| `E2E_USER_PASSWORD` | E2E Test-Passwort |

## Env-Variablen (Backend, wichtigste)

| Variable | Pflicht | Default | Zweck |
|----------|---------|---------|-------|
| `DATABASE_URL` | Ja | — | PostgreSQL Connection String |
| `REDIS_URL` | Nein | `redis://localhost:6379/0` | Redis Broker |
| `SUPABASE_URL` | Ja | — | Supabase Project URL |
| `SUPABASE_ANON_KEY` | Ja | — | Supabase Anon Key |
| `SUPABASE_SERVICE_ROLE_KEY` | Ja | — | Supabase Service Role |
| `JWT_SECRET` | Ja | — | JWT Signing Key |
| `SENTRY_DSN` | Nein | — | Sentry Error Tracking |
| `PUBLIC_DNS_TARGET` | Nein | `fewo.kolibri-visions.de` | DNS-Ziel fuer Custom Domains |
| `MODULES_ENABLED` | Nein | `true` | Modul-System Kill-Switch |
| `CHANNEL_MANAGER_ENABLED` | Nein | `false` | Channel Manager Feature-Gate |
| `SOURCE_COMMIT` | Nein | — | Git SHA fuer Version-Endpoint |
