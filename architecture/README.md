# Architektur-Dokumentation

> **Source of Truth ist der Code.** Diese Docs werden aus dem Code abgeleitet.
> Letzte Aktualisierung: 2026-03-11

## Uebersicht

PMS-Webapp ist ein **Modular Monolith** fuer Ferienwohnungsverwaltung (Multi-Tenant SaaS).

| Komponente | Technologie | Deployment |
|------------|-------------|------------|
| Backend API | FastAPI 0.115.0 + asyncpg (raw SQL) | Docker (`python:3.12-slim`) |
| Worker | Celery 5.3.6 + Redis | Docker (`Dockerfile.worker`) |
| Frontend Admin | Next.js 15.5.12 + Tailwind 3.4.1 | Nixpacks (Node 20) |
| Public Website | Next.js (gleiche App, Route Group `(public)`) | Nixpacks |
| Datenbank | PostgreSQL via Supabase | Managed (Supabase) |
| Auth | Supabase Auth (JWT) | Managed |
| Hosting | Coolify (Self-hosted Docker) | VPS |

## Dokumente

| Datei | Inhalt |
|-------|--------|
| [module-system.md](module-system.md) | 27 Module, Registry Pattern, Bootstrap, ModuleSpec |
| [database.md](database.md) | 58 Tabellen, RLS, Exclusion Constraints, Connection Pool |
| [deployment.md](deployment.md) | Docker, Coolify, CI/CD Workflows, Health Checks |
| [observability.md](observability.md) | Sentry, Prometheus Metriken, structlog, Event Bus |
| [ADRs/](ADRs/) | 8 Architecture Decision Records |

## Kern-Architektur

```
                    ┌─────────────────────┐
                    │    Coolify (VPS)     │
                    └──────────┬──────────┘
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │  Frontend   │    │   Backend   │    │   Worker    │
    │  (Next.js)  │    │  (FastAPI)  │    │  (Celery)   │
    │  Port 3000  │    │  Port 8000  │    │  Threads    │
    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
           │                  │                   │
           │           ┌──────▼──────┐            │
           └──────────▶│  PostgreSQL │◀───────────┘
                       │  (Supabase) │
                       │  + Redis    │
                       └─────────────┘
```

## Multi-Tenancy

- Tenant = **Agency** (Ferienwohnungsverwaltung)
- Isolation via `agency_id` Spalte + RLS Policies
- Helper-Funktion: `get_user_agency_ids()` → prueft `team_members` Tabelle
- Dreifache Absicherung: RLS (DB) + Service-Layer + JWT (Auth)
- Details: [ADR-003](ADRs/ADR-003-multi-tenancy.md)
