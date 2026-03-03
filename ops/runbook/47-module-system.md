# Module-System Architektur

## Übersicht

Das PMS-Webapp verwendet ein modulares Router-System für FastAPI. Alle Router werden über das Module-System in `bootstrap.py` registriert und gemountet.

## Architektur

```
bootstrap.py (mount_modules)
     ↓
registry.register(ModuleSpec)
     ↓
registry.mount_all(app)
     ↓
FastAPI app.include_router()
```

## Module-Struktur

Jedes Modul ist eine Python-Datei unter `backend/app/modules/`:

```python
# modules/example.py
from ..api.routes import example
from ._types import ModuleSpec
from .registry import registry

EXAMPLE_MODULE = ModuleSpec(
    name="example",
    version="1.0.0",
    router_configs=[
        (example.router, {"prefix": "/api/v1/example", "tags": ["Example"]}),
    ],
    depends_on=["core_pms"],
    tags=["Example"],
)

registry.register(EXAMPLE_MODULE)
```

## Registrierte Module (Stand: 2026-03-03)

| Modul | Router | Prefix |
|-------|--------|--------|
| `core` | health | `/` |
| `inventory` | availability | `/api/v1/availability` |
| `properties` | properties | `/api/v1/properties` |
| `bookings` | bookings | `/api/v1/bookings` |
| `booking_requests` | booking_requests | `/api/v1/booking-requests` |
| `branding` | branding | `/api/v1/branding` |
| `amenities` | amenities | `/api/v1` |
| `guests` | guests | `/api/v1` |
| `public_booking` | public_booking | `/api/v1/public` |
| `pricing` | pricing | `/api/v1/pricing` |
| `owners` | owners | `/api/v1` |
| `epic_a` | epic_a | `/api/v1` |
| `dashboard` | dashboard | `/api/v1` |
| `notifications` | notifications | `/api/v1` |
| `extra_services` | extra_services | `/api/v1` |
| `website_admin` | website_admin | `/api/v1/website` |
| `media` | media | `/api/v1` |
| `public_site` | public_site + agency_domain | `/api/v1/public` |
| `public_domain_admin` | public_domain_admin | `/api/v1/public-site` |
| `roles` | roles | `/api/v1` |
| `visitor_tax` | visitor_tax | `/api/v1` |
| `cancellation_policies` | cancellation_policies | `/api/v1` |
| `analytics` | analytics | `/api/v1` |
| `block_templates` | block_templates | `/api/v1/website` |
| `public_root_meta` | public_root_meta | `/` |
| `channel_manager` | (conditional) | `/api/v1` |

## Feature Flags

| Flag | Default | Beschreibung |
|------|---------|--------------|
| `MODULES_ENABLED` | `true` | Module-System aktiv |
| `CHANNEL_MANAGER_ENABLED` | `false` | Channel Manager Modul laden |

## Troubleshooting

### Router nicht erreichbar

1. **Modul nicht in bootstrap.py importiert:**
   ```bash
   grep "from . import example" backend/app/modules/bootstrap.py
   ```

2. **Modul-Datei fehlt:**
   ```bash
   ls backend/app/modules/example.py
   ```

3. **Registry-Registrierung prüfen:**
   ```bash
   grep "registry.register" backend/app/modules/example.py
   ```

### Circular Dependency Error

Module werden in Abhängigkeitsreihenfolge gemountet. Wenn A → B und B → A:

```
CircularDependencyError: Circular dependency detected
```

**Lösung:** `depends_on` Feld in einem der Module anpassen.

### ImportError beim Start

```
Module not available: No module named 'app.api.routes.example'
```

**Lösung:** Router-Datei unter `backend/app/api/routes/` erstellen.

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `backend/app/modules/bootstrap.py` | Modul-Bootstrap und Import |
| `backend/app/modules/registry.py` | ModuleRegistry Implementierung |
| `backend/app/modules/_types.py` | ModuleSpec TypedDict |
| `backend/app/modules/*.py` | Einzelne Module |

## History

| Datum | Änderung |
|-------|----------|
| 2026-03-03 | A-01: FAILSAFE-Code entfernt, 8 neue Module erstellt |
