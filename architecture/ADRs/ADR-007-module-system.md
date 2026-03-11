# ADR-007: Modul-System — Registry Pattern mit Graceful Degradation

**Status:** Accepted (implementiert)
**Datum:** 2025-12-21

---

## Entscheidung

**Module Registry Pattern** fuer Feature-Organisation. Jedes Feature ist ein eigenstaendiges Modul mit eigenem Router, Service und Schema.

## Architektur

```
app/modules/
  _types.py          # ModuleSpec Dataclass
  registry.py        # ModuleRegistry (Singleton)
  bootstrap.py       # mount_modules() — Modul-Import + Registrierung
  core.py            # Core PMS (Health, Ops)
  bookings.py        # Buchungsverwaltung
  properties.py      # Property CRUD
  ...                # 27 Module insgesamt
```

## ModuleSpec

```python
@dataclass
class ModuleSpec:
    name: str                    # snake_case Modulname
    routers: list[APIRouter]     # FastAPI Router
    router_configs: list[tuple]  # (Router, Config-Dict)
    depends_on: list[str]        # Abhaengigkeiten
    version: str
    description: str
    enabled_env_var: str | None  # Optional: Feature-Gate Env-Var
```

## Registrierung

```python
# In jedem Modul (z.B. modules/amenities.py)
from app.modules.registry import registry

registry.register(ModuleSpec(
    name="amenities",
    routers=[amenities_router],
    router_configs=[(amenities_router, {"prefix": "/api/v1", "tags": ["Amenities"]})],
    depends_on=["core_pms"],
))
```

## Bootstrap (mount_modules)

```python
# modules/bootstrap.py — Graceful Degradation
try:
    from . import amenities  # noqa: F401
except ImportError as e:
    logger.warning(f"Amenities module not available: {e}")
```

- Module werden importiert → Self-Registration via `registry.register()`
- Registry validiert Abhaengigkeiten (Kahn's Algorithmus, Zyklen-Erkennung)
- Router werden in topologischer Reihenfolge gemountet

## 27 registrierte Module (Ist-Stand)

| Modul | Feature-Gate | Kern-Funktion |
|-------|-------------|---------------|
| core | — | Health, Ops, Version |
| inventory | — | Verfuegbarkeit |
| properties | — | Property CRUD |
| bookings | — | Buchungen |
| booking_requests | — | Buchungsanfragen |
| branding | — | Tenant-Theming |
| amenities | — | Ausstattung |
| guests | — | Gaeste |
| public_booking | — | Oeffentliche Buchung |
| pricing | — | Preise, Rate Plans |
| owners | — | Eigentuemer |
| dashboard | — | Dashboard |
| notifications | — | Benachrichtigungen |
| extra_services | — | Zusatzleistungen |
| website_admin | — | Website-Verwaltung |
| media | — | Dateien/Bilder |
| public_site | — | Oeffentliche Website |
| public_domain_admin | — | Custom Domains |
| roles | — | Rollen/Berechtigungen |
| visitor_tax | — | Kurtaxen |
| cancellation_policies | — | Stornobedingungen |
| analytics | — | Berichte |
| block_templates | — | Sperr-Vorlagen |
| registrations | — | Meldescheine |
| epic_a | — | Epic A Features |
| public_root_meta | — | Public Metadata |
| channel_manager | `CHANNEL_MANAGER_ENABLED` | Channel-Integration |

## Scaffold-Script

Neue Module koennen generiert werden:

```bash
python3 backend/scripts/scaffold_feature.py payments --dry-run
```

Generiert 7 Dateien (Migration, Schema, Service, Routes, Module, Frontend Types, Frontend Page).
