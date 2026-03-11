# Modul-System

> Source of Truth: `backend/app/modules/bootstrap.py`, `backend/app/modules/_types.py`, `backend/app/modules/registry.py`

## Ueberblick

27 Module (+ 1 conditional), organisiert als **flache Dateien** unter `app/modules/`.
Jedes Modul ist eine einzelne Python-Datei die sich beim Import selbst registriert.

**Kein verschachteltes Verzeichnis-Layout.** Module importieren Router aus `app/api/routes/`,
Services aus `app/services/`, Schemas aus `app/schemas/`.

## Dateistruktur (Ist-Stand)

```
app/
  modules/
    _types.py           # ModuleSpec Dataclass
    registry.py         # ModuleRegistry Singleton
    bootstrap.py        # mount_modules() — Import + Registrierung
    core.py             # Health, Ops
    bookings.py         # Buchungen
    properties.py       # Properties
    amenities.py        # Ausstattung
    ...                 # 27 Module insgesamt
  api/routes/           # FastAPI Router (getrennt von Modulen)
  services/             # Business Logic
  schemas/              # Pydantic Schemas
```

## ModuleSpec (app/modules/_types.py)

```python
@dataclass
class ModuleSpec:
    name: str                                          # snake_case
    version: Optional[str] = None
    routers: list[APIRouter] = []                      # Einfache Router
    router_configs: list[tuple[APIRouter, dict]] = []  # Router mit Prefix/Tags
    depends_on: list[str] = []                         # Abhaengigkeiten
    startup: Optional[Callable] = None                 # Startup-Hook
    shutdown: Optional[Callable] = None                # Shutdown-Hook
    tags: Optional[list[str]] = None
    init_app: Optional[Callable[[FastAPI], None]] = None
    settings_hook: Optional[Callable] = None
    migrations_path: Optional[str] = None
    enabled: Optional[Callable] = None                 # Feature-Gate
```

Validierung in `__post_init__`: snake_case Name, keine Self-Dependencies, keine Duplikate.

## Registrierung (Beispiel: amenities.py)

```python
from ..api.routes import amenities
from ._types import ModuleSpec
from .registry import registry

AMENITIES_MODULE = ModuleSpec(
    name="amenities",
    version="1.0.0",
    router_configs=[
        (amenities.router, {"prefix": "/api/v1/amenities", "tags": ["Amenities"]}),
    ],
    depends_on=["core_pms", "properties"],
)

registry.register(AMENITIES_MODULE)
```

## Registry (app/modules/registry.py)

| Methode | Zweck |
|---------|-------|
| `register(spec, fail_soft=True)` | Modul registrieren (Graceful Degradation) |
| `get(name)` | Einzelnes Modul abfragen |
| `get_all()` | Alle Module in Dependency-Reihenfolge (Topological Sort) |
| `validate()` | Dependencies pruefen + Zyklen-Erkennung |
| `mount_all(app)` | Router an FastAPI mounten (mit Dedup-Guard) |
| `describe_modules()` | Metadata-Dict fuer Logging |

Singleton: `registry = ModuleRegistry()` (Zeile 287)

## Bootstrap (app/modules/bootstrap.py)

```python
def mount_modules(app: FastAPI):
    # 26 Module mit try/except (Graceful Degradation)
    try:
        from . import bookings  # noqa: F401
    except ImportError as e:
        logger.warning(f"bookings module not available: {e}")

    # Conditional: Channel Manager
    if settings.channel_manager_enabled:
        from . import channel_manager

    registry.validate()
    registry.mount_all(app)
```

Kill-Switch in `main.py`: `MODULES_ENABLED` (default: `true`).
Bei `false` werden Router explizit gemountet (Fallback).

## Alle 27 Module (Ist-Stand)

| # | Modul | Dependencies | Feature-Gate |
|---|-------|-------------|--------------|
| 1 | core | — | — |
| 2 | inventory | core_pms | — |
| 3 | properties | core_pms | — |
| 4 | bookings | core_pms | — |
| 5 | booking_requests | core_pms | — |
| 6 | branding | core_pms | — |
| 7 | amenities | core_pms, properties | — |
| 8 | guests | core_pms | — |
| 9 | public_booking | core_pms | — |
| 10 | pricing | core_pms | — |
| 11 | owners | core_pms | — |
| 12 | epic_a | — | — |
| 13 | dashboard | core_pms | — |
| 14 | notifications | core_pms | — |
| 15 | extra_services | core_pms | — |
| 16 | website_admin | core_pms | — |
| 17 | media | core_pms | — |
| 18 | public_site | core_pms | — |
| 19 | public_domain_admin | core_pms | — |
| 20 | roles | core_pms | — |
| 21 | visitor_tax | core_pms | — |
| 22 | cancellation_policies | core_pms | — |
| 23 | analytics | core_pms | — |
| 24 | block_templates | core_pms | — |
| 25 | public_root_meta | — | — |
| 26 | registrations | core_pms | — |
| 27 | channel_manager | core_pms | `CHANNEL_MANAGER_ENABLED` |

## Neues Modul erstellen

```bash
python3 backend/scripts/scaffold_feature.py payments --dry-run
```

Generiert 7 Dateien + zeigt manuelle Schritte (DI, Protocol, Bootstrap).

## Dependency Injection

Services werden ueber Factory-Funktionen injiziert (`app/api/deps/services.py`):

```python
def get_booking_service(db = Depends(get_db_authed)) -> BookingServiceProtocol:
    from app.services.booking_service import BookingService
    return BookingService(db)
```

Alle Services nutzen **Protocol-Types** (nicht konkrete Klassen) fuer Typsicherheit.

Registrierte Services: availability, property, guest, amenity, booking, dashboard, extra_service, visitor_tax.
