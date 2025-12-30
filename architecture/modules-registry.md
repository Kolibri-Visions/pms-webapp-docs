# Module Registry - How It Works

**Status**: Phase 21 (Active - Minimal Adoption)

This document explains the module registry system introduced in Phase 21.

---

## Overview

The Module Registry provides a lightweight foundation for organizing PMS-Webapp code into cohesive, independently-testable modules with explicit dependencies.

**Key Principles:**
- **Incremental Adoption**: Existing code remains unchanged. Modules are adopted gradually.
- **No Big Refactors**: Routers stay in current locations. Module system wraps them without moving files.
- **Explicit Dependencies**: Modules declare dependencies on other modules (validated at startup).
- **Failure Detection**: Circular dependencies detected early (app startup fails fast).

---

## Architecture

### Components

1. **ModuleSpec** (`app/modules/_types.py`)
   - Dataclass defining module metadata
   - Fields: name, version, routers, dependencies, hooks, tags
   - Self-validates on creation (no circular deps, valid names)

2. **ModuleRegistry** (`app/modules/registry.py`)
   - Central registry for all modules
   - Validates dependencies via topological sort (Kahn's algorithm)
   - Provides ordered list of modules for mounting
   - Methods: `register()`, `validate()`, `mount_all()`, `describe_modules()`

3. **Bootstrap** (`app/modules/bootstrap.py`)
   - Application integration point
   - Imports modules (triggers registration)
   - Validates and mounts to FastAPI app
   - Single function: `mount_modules(app)`

4. **Example Modules** (`app/modules/core.py`)
   - Demonstrates pattern
   - Wraps existing routers without moving them
   - Self-registers on import

---

## ModuleSpec Definition

```python
@dataclass
class ModuleSpec:
    name: str                           # Unique identifier (snake_case)
    version: Optional[str] = None       # Semver recommended
    routers: list[APIRouter] = []       # FastAPI routers to mount
    depends_on: list[str] = []          # Module names this depends on
    startup: Optional[Callable] = None  # Async/sync startup hook
    shutdown: Optional[Callable] = None # Async/sync shutdown hook
    tags: Optional[list[str]] = None    # OpenAPI tags
    # Additional fields: init_app, settings_hook, migrations_path, enabled
```

**Validation Rules:**
- Module name must be snake_case (alphanumeric + underscores)
- No self-dependencies
- No duplicate dependencies
- Circular dependencies detected at registration time

---

## How It Works

### 1. Module Definition

Create a module file (e.g., `app/modules/core.py`):

```python
from ..core.health import router as health_router
from ._types import ModuleSpec
from .registry import registry

CORE_MODULE = ModuleSpec(
    name="core_pms",
    version="0.1.0",
    routers=[health_router],
    depends_on=[],  # No dependencies
    tags=["Core PMS", "Health"],
)

# Auto-register on import
registry.register(CORE_MODULE)
```

**Important:** Module files are NOT moved. They remain in `app/api/routes/` or their current locations. The module simply imports and wraps them.

### 2. Bootstrap Integration

In `app/main.py`, call `mount_modules(app)`:

```python
from .modules.bootstrap import mount_modules

app = FastAPI()
mount_modules(app)  # Imports modules, validates, mounts routers
```

### 3. Registration Flow

```
1. main.py imports bootstrap.mount_modules()
   ↓
2. mount_modules() imports app/modules/core.py
   ↓
3. core.py imports registry and calls registry.register(CORE_MODULE)
   ↓
4. Registry validates module (no circular deps, valid name)
   ↓
5. mount_modules() calls registry.validate() (topological sort)
   ↓
6. mount_modules() calls registry.mount_all(app)
   ↓
7. mount_all() includes routers in dependency order
```

### 4. Dependency Validation

**Topological Sort (Kahn's Algorithm):**
- Modules sorted so dependencies come before dependents
- Example: Module B depends on A → mounting order: [A, B]
- Circular dependencies cause `CircularDependencyError` at startup

**Detection:**
```python
# This FAILS at startup (circular dependency):
module_a = ModuleSpec(name="a", depends_on=["b"])
module_b = ModuleSpec(name="b", depends_on=["a"])
```

---

## Router Aggregation Strategy

### Phase 21 (Current)

**Minimal Adoption:**
- Only `health_router` migrated to module system
- All other routers remain in `main.py` with existing `include_router()` calls
- No API path changes, no prefix changes, no tag changes

**Why Minimal?**
- Demonstrates pattern without risk
- Validates module system works
- Allows testing before large-scale migration

### Phase 22+ (Future)

**Incremental Migration:**
1. Create domain modules (e.g., `properties_module`, `bookings_module`)
2. Import existing routers without moving files
3. Remove corresponding `include_router()` calls from `main.py`
4. Let module system handle mounting

**Example (Phase 22):**
```python
# app/modules/properties.py
from ..api.routes import properties
from ._types import ModuleSpec
from .registry import registry

PROPERTIES_MODULE = ModuleSpec(
    name="properties",
    version="1.0.0",
    routers=[properties.router],
    depends_on=["core_pms"],
    tags=["Properties"],
)

registry.register(PROPERTIES_MODULE)
```

**Benefit:** Explicit dependency graph shows `properties` depends on `core_pms`.

---

## Rules

### Hard Rules (Must Follow)

1. **No Big Refactors**: Routers stay in current files. No file moves in Phase 21.
2. **Incremental Adoption**: Migrate one module at a time. Test after each.
3. **Existing Routers Stay**: Keep `include_router()` calls in `main.py` for non-migrated routers.
4. **No API Changes**: Module system must not change API paths, prefixes, tags, or auth.
5. **Fail Fast**: Circular dependencies must fail at startup, not runtime.

### Soft Guidelines

- Use semantic versioning for module versions
- Module names should match domain boundaries (core_pms, distribution, finance)
- Keep modules small and cohesive (single responsibility)
- Document module dependencies in module docstrings

---

## Migration Plan

### Phase 21 (Complete)
- ✅ Create ModuleSpec, ModuleRegistry, bootstrap
- ✅ Create example `core` module (health router only)
- ✅ Wire `mount_modules()` into `main.py`
- ✅ Validate pattern works without breaking existing behavior

### Phase 22 (Complete)
- ✅ Add `router_configs` field to ModuleSpec for prefix/tags support
- ✅ Update `mount_all()` to handle configured routers
- ✅ Create `api_v1` module wrapping properties, bookings, availability routers
- ✅ Register routers with EXACT same configuration (prefix="/api/v1", tags)
- ✅ Remove direct `include_router()` calls from `main.py`
- ✅ **Wrap-only approach**: NO file moves, NO API path changes

**Phase 22 Rules:**
- ✅ Routers remain in `app/api/routes/` (no relocation)
- ✅ API paths unchanged: `/api/v1/properties`, `/api/v1/bookings`, `/api/v1/availability`
- ✅ Tags unchanged: `["Properties"]`, `["Bookings"]`, `["Availability"]`
- ✅ Auth/RBAC unchanged

### Phase 23 (Future)
- Create `distribution` module (channel manager integration)
- Create `finance` module (pricing, invoicing)
- Create `guest_experience` module (portal, communication)

### Phase 24+ (Future)
- Create `owner_portal` module
- Create `direct_booking` module
- Establish clear dependency graph across all modules

---

## Debugging

### Describe Modules

```python
from app.modules.registry import registry

# Get module summary
info = registry.describe_modules()
print(info)
# {
#   "total_modules": 1,
#   "modules": [
#     {
#       "name": "core_pms",
#       "version": "0.1.0",
#       "router_count": 1,
#       "dependencies": [],
#       "tags": ["Core PMS", "Health"]
#     }
#   ]
# }
```

### Validation Errors

**Circular Dependency:**
```
CircularDependencyError: Circular dependency detected involving modules: {'module_a', 'module_b'}
```

**Unknown Dependency:**
```
ValueError: Module 'properties' depends on unknown module: 'core_pms'
```

**Duplicate Name:**
```
ValueError: Module 'core_pms' is already registered
```

---

## Testing

### Unit Tests

Located in `tests/modules/test_module_registry.py`:
- Test circular dependency detection
- Test topological sort
- Test duplicate module rejection
- Test unknown dependency rejection

**Run tests:**
```bash
pytest tests/modules/
```

### Integration Tests

No integration tests yet (Phase 22+).

---

## Benefits

1. **Explicit Dependencies**: Know what depends on what (dependency graph visible)
2. **Validation at Startup**: Circular deps fail fast (not at runtime)
3. **Incremental Migration**: No big-bang refactor required
4. **Testability**: Modules can be tested independently
5. **Feature Flags**: Future support for enabling/disabling modules via settings
6. **Clear Boundaries**: Domain logic separated by module

---

## Limitations (Current)

- ✅ **Prefix Support**: Added in Phase 22 via `router_configs` field
- **No Startup/Shutdown Hooks**: Not implemented yet (fields exist but not wired)
- **No Settings Injection**: Not implemented yet
- **No Feature Flags**: Not implemented yet (field exists but not wired)

These will be addressed in future phases as needed.

---

## See Also

- **Modular Monolith Overview**: `modular-monolith.md`
- **Phase 21 Plan**: `phase21-modularization-plan.md`
- **Module Package**: `app/modules/README.md`
- **Product Model**: `docs/product/reference-product-model.md`
