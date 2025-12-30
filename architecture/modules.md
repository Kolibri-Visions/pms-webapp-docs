# Modular Monolith Architecture

**Purpose:** Define the module system architecture for PMS-Webapp's modular monolith.

**Audience:** Backend developers, architects, integration teams.

**Last Updated:** 2025-12-27 (Phase 33B)

**Status:** Phase 33B Active (Core + Domain modules: properties, bookings, inventory)

---

## Motivation

### Why Modular Monolith?

The PMS-Webapp backend uses a **modular monolith** architecture to achieve:

1. **Clear Domain Boundaries**: Separate business domains (core, channel manager, direct booking, owner area) into distinct modules
2. **Incremental Scalability**: Start with a monolith, migrate to microservices only when needed
3. **Reduced Complexity**: Avoid distributed systems overhead (network calls, eventual consistency, distributed transactions)
4. **Stable Interfaces**: Modules communicate via well-defined boundaries, making future extraction easier

### Target Modules (Roadmap)

- **core_pms**: Core PMS functionality (health checks) — ✅ Active (Phase 22)
- **properties**: Properties domain (CRUD for properties) — ✅ Active (Phase 33B)
- **bookings**: Bookings domain (CRUD for bookings) — ✅ Active (Phase 33B)
- **inventory**: Inventory domain (availability, blocks) — ✅ Active (Phase 33B)
- **api_v1**: Legacy wrapper (superseded by domain modules) — ⚠️ Legacy (Phase 33B)
- **channel_manager**: Channel Manager integration (Airbnb, Booking.com sync) — 🔜 Future
- **direct_booking**: Direct booking engine (guest-facing booking flow) — 🔜 Future
- **owner_area**: Owner/property manager portal — 🔜 Future
- **distribution**: Rate/availability distribution logic — 🔜 Future

---

## Core Concepts

### ModuleSpec

A `ModuleSpec` defines a module's metadata and wiring information.

**Definition** (`app/modules/_types.py`):
```python
@dataclass
class ModuleSpec:
    name: str                         # Unique module identifier (snake_case)
    version: Optional[str]            # Module version (semver recommended)
    routers: list[APIRouter]          # Simple routers (no prefix/tags)
    router_configs: list[tuple]       # Routers with config (prefix, tags, etc.)
    depends_on: list[str]             # Module dependencies (topological sort)
    startup: Optional[Callable]       # Optional startup hook
    shutdown: Optional[Callable]      # Optional shutdown hook
    tags: Optional[list[str]]         # OpenAPI tags
    enabled: Optional[Callable]       # Feature flag function
```

**Key Fields:**
- `name`: Unique module identifier (e.g., `"core_pms"`, `"channel_manager"`)
- `routers`: FastAPI routers without prefix/tags (simple inclusion)
- `router_configs`: Routers with configuration tuples: `[(router, {"prefix": "/api/v1", "tags": ["Properties"]}), ...]`
- `depends_on`: List of module names this module depends on (validated at startup)

### ModuleRegistry

The `ModuleRegistry` manages module registration and validation.

**Location**: `app/modules/registry.py`

**Key Methods:**
- `register(spec: ModuleSpec)`: Register a module (validates dependencies, detects cycles)
- `get(name: str) -> ModuleSpec`: Get module by name
- `get_all() -> list[ModuleSpec]`: Get all modules in **dependency order** (topological sort)
- `validate()`: Validate entire registry (dependencies exist, no cycles)
- `mount_all(app: FastAPI)`: Mount all module routers to FastAPI app
  - **Dedupe Guard (Phase 35)**: Tracks mounted routers by `(type, id, prefix, tags)` to prevent accidental double-mounts
  - Skips duplicate router includes and logs a warning
  - Helps prevent issues when legacy modules are accidentally reintroduced

**Singleton Instance:**
```python
from app.modules.registry import registry

# Register a module
registry.register(MY_MODULE_SPEC)

# Get all modules (dependency order)
for module in registry.get_all():
    print(module.name)
```

### Router Aggregation Pattern

Modules self-register their routers on import. The application mounts all routers in dependency order.

**Current Flow (Phase 33B):**
```
app/main.py
  └─> mount_modules(app)
        └─> import app.modules.core        # Triggers core registration
        └─> import app.modules.inventory   # Triggers inventory registration
        └─> import app.modules.properties  # Triggers properties registration
        └─> import app.modules.bookings    # Triggers bookings registration
        └─> registry.validate()            # Validate dependencies
        └─> registry.mount_all(app)        # Mount routers in dependency order
```

---

## Module Definition Pattern

### Example: Core PMS Module

**File**: `app/modules/core.py`

```python
"""
Core PMS Module

Foundational module for PMS-Webapp.
"""

from ..core.health import router as health_router
from ._types import ModuleSpec
from .registry import registry

# Define module specification
CORE_MODULE = ModuleSpec(
    name="core_pms",
    version="0.1.0",
    routers=[
        health_router,  # Health check router (no prefix)
    ],
    depends_on=[],  # Core module has no dependencies
    tags=["Core PMS", "Health"],
)

# Auto-register on import
registry.register(CORE_MODULE)
```

### Example: Properties Domain Module

**File**: `app/modules/properties.py`

```python
"""
Properties Domain Module

Wraps the properties router into the module system.
"""

from ..api.routes import properties
from ._types import ModuleSpec
from .registry import registry

# Define module specification
PROPERTIES_MODULE = ModuleSpec(
    name="properties",
    version="1.0.0",
    router_configs=[
        (properties.router, {"prefix": "/api/v1", "tags": ["Properties"]}),
    ],
    depends_on=["core_pms"],
    tags=["Properties"],
)

# Auto-register on import
registry.register(PROPERTIES_MODULE)
```

### Example: Bookings Domain Module

**File**: `app/modules/bookings.py`

```python
"""
Bookings Domain Module

Wraps the bookings router with inventory dependency.
"""

from ..api.routes import bookings
from ._types import ModuleSpec
from .registry import registry

# Define module specification
BOOKINGS_MODULE = ModuleSpec(
    name="bookings",
    version="1.0.0",
    router_configs=[
        (bookings.router, {"prefix": "/api/v1", "tags": ["Bookings"]}),
    ],
    depends_on=["core_pms", "inventory"],  # Bookings depend on inventory for conflict checks
    tags=["Bookings"],
)

# Auto-register on import
registry.register(BOOKINGS_MODULE)
```

---

## Rules of Engagement

**For comprehensive module boundary rules, dependency constraints, and violation examples, see:**
- **[Module Boundaries & Dependency Rules](module-boundaries.md)** (normative reference)

The rules below provide a quick overview:

### 1. No Cross-Module Imports (Except Interfaces)

**Rule:** Modules must NOT import implementation details from other modules.

**Bad:**
```python
# In channel_manager module
from app.modules.core_pms.services.booking_service import BookingService  # ❌ Direct import
```

**Good:**
```python
# In channel_manager module
from app.api.routes.bookings import create_booking  # ✅ Via API route
# OR use dependency injection via FastAPI Depends()
```

**Why:** Direct imports create tight coupling. Use:
- Public API routes (HTTP endpoints)
- Shared schemas/models (via `app/schemas/`)
- Dependency injection (FastAPI `Depends()`)

### 2. Keep Routers Where They Are (For Now)

**Rule:** Do NOT move existing routers during module adoption.

**Phase 22 Approach:**
- Routers remain in `app/api/routes/`
- Modules **import and register** existing routers
- No file moves, no import path changes

**Future Phases:**
- May move routers into module directories (`app/modules/{name}/api/`)
- Requires careful migration and testing

### 3. Modules Must Declare Dependencies

**Rule:** If module B uses module A's functionality, declare `depends_on=["module_a"]`.

**Example:**
```python
CHANNEL_MANAGER_MODULE = ModuleSpec(
    name="channel_manager",
    depends_on=["core_pms"],  # Needs core booking functionality
    ...
)
```

**Benefits:**
- Registry validates dependencies at startup (fails fast if missing)
- Routers mounted in correct order (dependencies first)
- Topological sort detects circular dependencies

### 4. Feature Flags for Optional Modules

**Rule:** Use `enabled` callable for modules that should be conditionally loaded.

**Example:**
```python
def is_channel_manager_enabled(settings):
    return settings.enable_channel_manager  # env var: ENABLE_CHANNEL_MANAGER=true

CHANNEL_MANAGER_MODULE = ModuleSpec(
    name="channel_manager",
    enabled=is_channel_manager_enabled,
    ...
)
```

**Note:** Not yet implemented (Phase 31 roadmap). Currently all registered modules are mounted.

---

## Application Wiring

### Current Setup (Phase 22)

**File**: `app/main.py`

```python
from .modules.bootstrap import mount_modules

app = FastAPI(...)

# Mount all registered modules
mount_modules(app)
```

**What `mount_modules()` does:**
1. Import core and api_v1 modules (triggers self-registration)
2. Validate all registered modules (`registry.validate()`)
3. Mount routers in dependency order (`registry.mount_all(app)`)
4. Log module mounting summary

**Benefits:**
- Single call mounts all modules
- Dependency order guaranteed
- Graceful degradation (missing modules logged, don't crash app)

---

## Module Directory Structure (Future)

When modules are eventually migrated into separate directories:

```
app/modules/
├── _types.py              # ModuleSpec dataclass
├── registry.py            # ModuleRegistry
├── bootstrap.py           # mount_modules() function
├── core.py                # Core module registration (Phase 22)
├── api_v1.py              # API v1 module registration (Phase 22)
│
├── channel_manager/       # Future: Channel Manager module
│   ├── __init__.py
│   ├── api/
│   │   └── routes.py
│   ├── services/
│   │   └── airbnb_sync.py
│   └── schemas/
│       └── airbnb.py
│
├── direct_booking/        # Future: Direct Booking module
│   ├── __init__.py
│   ├── api/
│   │   └── routes.py
│   └── services/
│       └── booking_flow.py
│
└── owner_area/            # Future: Owner Portal module
    ├── __init__.py
    ├── api/
    │   └── routes.py
    └── services/
        └── analytics.py
```

**Migration Approach (Future):**
1. Create module directory (`app/modules/{name}/`)
2. Move routers from `app/api/routes/` to `app/modules/{name}/api/`
3. Update module spec to use new import paths
4. Test thoroughly (no API path changes)
5. Update documentation

---

## Testing Strategy

### Unit Tests

Test individual modules in isolation:

```python
# tests/modules/test_core.py
def test_core_module_registration():
    from app.modules.core import CORE_MODULE
    assert CORE_MODULE.name == "core_pms"
    assert len(CORE_MODULE.routers) > 0
```

### Integration Tests

Test module dependencies and mounting:

```python
# tests/integration/test_module_registry.py
def test_module_dependency_order():
    from app.modules.registry import registry
    modules = registry.get_all()
    # Ensure core_pms comes before api_v1
    names = [m.name for m in modules]
    assert names.index("core_pms") < names.index("api_v1")
```

### Smoke Tests

Validate module routers via HTTP:

```bash
# Ensure all module endpoints are accessible
curl http://localhost:8000/health          # core_pms module
curl http://localhost:8000/api/v1/properties  # api_v1 module
```

---

## Troubleshooting

### Circular Dependency Detected

**Error:**
```
CircularDependencyError: Circular dependency detected involving modules: {'module_a', 'module_b'}
```

**Solution:**
1. Check `depends_on` lists in both modules
2. Remove circular dependency (A → B → A)
3. Consider introducing a shared interface module if needed

### Module Import Fails

**Error:**
```
ImportError: cannot import name 'router' from 'app.api.routes.missing'
```

**Solution:**
1. Check router import path in `ModuleSpec.router_configs`
2. Ensure router file exists and exports `router` variable
3. Check for typos in import path

### Router Not Mounted

**Symptom:** Endpoint returns 404 despite router definition.

**Debug:**
```python
# Check registered modules
from app.modules.registry import registry
print(registry.describe_modules())

# Check if router is in module spec
module = registry.get("api_v1")
print(module.router_configs)
```

**Common Causes:**
- Module not imported in `bootstrap.py`
- Router not included in `ModuleSpec.routers` or `router_configs`
- Prefix mismatch (e.g., `/api/v1` vs `/api/v2`)

---

## Roadmap

### Phase 22 ✅ (Complete)
- Core PMS module (health router)
- API v1 module (monolithic wrapper)
- Module registry with dependency validation
- Auto-registration on import

### Phase 31 ✅ (Complete)
- Architecture documentation (this file)
- Runbook updates
- Module system awareness documentation

### Phase 33B ✅ (Current)
- Split api_v1 into domain modules (properties, bookings, inventory)
- Domain dependency modeling (bookings → inventory)
- api_v1 marked as legacy (kept for reference)

### Future Phases
- **Phase 32+**: Channel Manager module
  - Airbnb/Booking.com sync
  - Rate/availability distribution
- **Phase 33+**: Direct Booking module
  - Guest-facing booking flow
  - Payment integration
- **Phase 34+**: Owner Area module
  - Analytics dashboard
  - Property management tools
- **Phase 35+**: Feature flags
  - Environment-based module toggling
  - Gradual rollout support

---

## References

- **Module Registry**: `app/modules/registry.py`
- **Module Types**: `app/modules/_types.py`
- **Bootstrap**: `app/modules/bootstrap.py`
- **Core Module**: `app/modules/core.py`
- **Properties Module**: `app/modules/properties.py`
- **Bookings Module**: `app/modules/bookings.py`
- **Inventory Module**: `app/modules/inventory.py`
- **API v1 Module (Legacy)**: `app/modules/api_v1.py` (no longer imported)
- **Inventory Contract**: `backend/docs/domain/inventory.md` (domain logic, independent of module system)

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-27 | Initial modular monolith architecture documentation (Phase 31) | Claude Code |
| 2025-12-27 | Split api_v1 into domain modules: properties, bookings, inventory (Phase 33B) | Claude Code |
