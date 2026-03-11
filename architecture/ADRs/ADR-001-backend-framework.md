# ADR-001: Backend Framework — FastAPI + Raw AsyncPG

**Status:** Accepted (implementiert)
**Datum:** 2025-12-21

---

## Entscheidung

**FastAPI** mit **raw asyncpg** (kein ORM) als Backend-Stack.

## Stack (Ist-Stand)

| Komponente | Version | Zweck |
|------------|---------|-------|
| FastAPI | 0.115.0 | Web-Framework (async) |
| Pydantic | 2.5.3 | Request/Response Validation |
| asyncpg | 0.29.0 | PostgreSQL async Driver |
| uvicorn | 0.27.0 | ASGI Server |
| Celery | 5.3.6 | Background Tasks (Redis Broker) |
| redis | 5.0.1 | Cache + Celery Broker |

## Warum kein ORM?

SQLAlchemy 2.0.25 ist als Dependency installiert, wird aber **nicht fuer Queries verwendet**.
Alle DB-Zugriffe erfolgen ueber raw asyncpg:

```python
# Tatsaechliches Pattern (app/core/database.py)
row = await db.fetchrow(
    "SELECT * FROM bookings WHERE id = $1 AND agency_id = $2",
    booking_id, agency_id
)
```

**Gruende:**
- Volle Kontrolle ueber SQL (keine ORM-Magie)
- Bessere Performance bei komplexen Queries
- Einfacheres Debugging
- RLS-Policies transparent (kein ORM das Queries veraendert)

## Projektstruktur (Ist-Stand)

```
backend/
  app/
    api/           # FastAPI Routes + Dependencies
    core/          # Config, Auth, Database, Events, Metrics
    modules/       # 27 Feature-Module (Registry Pattern)
    schemas/       # Pydantic Schemas (27 Dateien)
    services/      # Business Logic (Service Layer)
    channel_manager/  # Channel-Integration (feature-gated)
  scripts/         # Smoke Tests, Scaffold, Export
  docs/            # Dokumentation
```

## Konsequenzen

- Kein automatisches Schema-Mapping → Schemas muessen manuell gepflegt werden
- OpenAPI-Spec wird automatisch aus Pydantic-Schemas generiert
- Frontend-Types werden aus OpenAPI generiert (`npm run generate:types`)
