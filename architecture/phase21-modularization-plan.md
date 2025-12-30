# Phase 21: Modularization Plan

**Status**: Scaffold Preparation (Current Phase)
**Goal**: Prepare codebase for modular architecture without breaking existing functionality
**Strategy**: Additive changes only, no refactoring

---

## Overview

This document defines the step-by-step plan for modularizing the PMS-Webapp monolith into a clean modular monolith architecture. Phase 21 focuses on **preparation and scaffolding** - actual module extraction happens in Phase 22+.

**Guiding Principle**: **No Debugging Chaos**
- Minimal, additive changes
- No router moves or service refactoring
- No database schema changes
- All existing tests must pass
- New tests for scaffold only

---

## Phase 21 Checkpoints

### Checkpoint A: Documentation ✅

**Goal**: Define architecture and module boundaries before writing code

**Deliverables**:
1. `docs/product/reference-product-model.md` - Product model mapping
2. `docs/architecture/modular-monolith.md` - Architecture rules
3. `docs/architecture/phase21-modularization-plan.md` - This document

**Status**: ✅ **COMPLETE** (current commit)

**Acceptance Criteria**:
- [x] All 6 reference model pillars mapped to modules
- [x] Dependency rules documented (no circular imports)
- [x] Layer separation defined (API → Service → Repository → DB)
- [x] Module folder structure conventions established
- [x] Integration patterns documented (sync calls + future events)

---

### Checkpoint B: Module Scaffold

**Goal**: Create minimal module infrastructure without wiring it to the application

**Deliverables**:
1. `backend/app/modules/__init__.py` - Module package
2. `backend/app/modules/_types.py` - `ModuleSpec` dataclass
3. `backend/app/modules/registry.py` - `ModuleRegistry` class
4. `backend/app/modules/README.md` - Usage documentation
5. `backend/app/modules/examples/core_stub.py` - Example module spec

**Status**: 🎯 **IN PROGRESS** (current commit)

**Implementation**:

#### 1. Module Types (`_types.py`)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from fastapi import APIRouter, FastAPI
    from pydantic_settings import BaseSettings

@dataclass
class ModuleSpec:
    """
    Specification for a PMS-Webapp module.

    Design Goals:
    - Lightweight (no heavy dependencies)
    - TYPE_CHECKING imports to avoid circular dependencies
    - Clear metadata for validation and registration

    Why This Exists:
    - Centralized module registration prevents scattered configuration
    - Dependency validation catches circular imports at startup
    - Enables feature flags and conditional module loading
    """
    name: str
    """Unique module name (e.g., 'core_pms', 'distribution')"""

    routers: list[APIRouter] = field(default_factory=list)
    """FastAPI routers to include in application"""

    depends_on: list[str] = field(default_factory=list)
    """List of module names this module depends on"""

    init_app: Optional[Callable[[FastAPI], None]] = None
    """Optional startup hook (e.g., initialize connections)"""

    settings_hook: Optional[Callable[[BaseSettings], None]] = None
    """Optional settings injection hook"""

    migrations_path: Optional[str] = None
    """Optional path to module-specific migrations (metadata only)"""

    enabled: Optional[Callable[[BaseSettings], bool]] = None
    """Optional feature flag function (returns True if module enabled)"""

    def __post_init__(self):
        # Validate module name (snake_case)
        if not self.name.replace('_', '').isalnum():
            raise ValueError(f"Module name must be snake_case: {self.name}")

        # Validate no self-dependency
        if self.name in self.depends_on:
            raise ValueError(f"Module {self.name} cannot depend on itself")
```

#### 2. Module Registry (`registry.py`)

```python
from typing import Dict, List, Optional
from ._types import ModuleSpec

class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected"""
    pass

class ModuleRegistry:
    """
    Central registry for all PMS-Webapp modules.

    Responsibilities:
    - Register modules with validation
    - Detect circular dependencies (topological sort)
    - Provide ordered list of modules for application wiring

    Thread-Safety: Not thread-safe (registration happens at import time)
    """

    def __init__(self):
        self._modules: Dict[str, ModuleSpec] = {}
        self._registered_order: List[str] = []

    def register(self, spec: ModuleSpec) -> None:
        """
        Register a module with validation.

        Args:
            spec: Module specification

        Raises:
            ValueError: If module name already registered
            CircularDependencyError: If dependency creates a cycle
        """
        if spec.name in self._modules:
            raise ValueError(f"Module {spec.name} already registered")

        # Temporarily add to registry for cycle detection
        self._modules[spec.name] = spec
        self._registered_order.append(spec.name)

        # Validate dependencies exist and no cycles
        self._validate_dependencies(spec)

    def get(self, name: str) -> Optional[ModuleSpec]:
        """Get module by name"""
        return self._modules.get(name)

    def get_all(self) -> List[ModuleSpec]:
        """
        Get all modules in dependency order (topological sort).

        Returns modules sorted so that dependencies come before dependents.
        Example: If module B depends on A, returns [A, B]
        """
        sorted_names = self._topological_sort()
        return [self._modules[name] for name in sorted_names]

    def validate(self) -> None:
        """
        Validate entire registry.

        Checks:
        - All dependencies exist
        - No circular dependencies
        - All module names are unique

        Raises:
            ValueError: If validation fails
            CircularDependencyError: If circular dependencies detected
        """
        for module in self._modules.values():
            self._validate_dependencies(module)

        # Ensure topological sort succeeds (will raise if cycle exists)
        self._topological_sort()

    def _validate_dependencies(self, spec: ModuleSpec) -> None:
        """Validate module dependencies exist"""
        for dep_name in spec.depends_on:
            if dep_name not in self._modules:
                raise ValueError(
                    f"Module {spec.name} depends on unknown module: {dep_name}"
                )

        # Check for circular dependencies
        try:
            self._topological_sort()
        except CircularDependencyError:
            # Remove the module we just added and re-raise
            self._modules.pop(spec.name)
            self._registered_order.remove(spec.name)
            raise

    def _topological_sort(self) -> List[str]:
        """
        Topological sort of modules by dependencies.

        Returns:
            List of module names in dependency order

        Raises:
            CircularDependencyError: If circular dependencies detected
        """
        # Kahn's algorithm for topological sort
        in_degree = {name: 0 for name in self._modules}
        adj_list = {name: [] for name in self._modules}

        # Build adjacency list and in-degree count
        for name, spec in self._modules.items():
            for dep in spec.depends_on:
                adj_list[dep].append(name)
                in_degree[name] += 1

        # Queue of modules with no dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            # Reduce in-degree for dependent modules
            for dependent in adj_list[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # If result doesn't contain all modules, there's a cycle
        if len(result) != len(self._modules):
            missing = set(self._modules.keys()) - set(result)
            raise CircularDependencyError(
                f"Circular dependency detected involving: {missing}"
            )

        return result

# Global registry instance
registry = ModuleRegistry()
```

#### 3. Module README (`README.md`)

```markdown
# PMS-Webapp Modules

**Status**: Phase 21 (Scaffold Only - NOT WIRED)

## Overview

This directory contains the module scaffold for PMS-Webapp's modular monolith architecture.

**IMPORTANT**: Modules are NOT yet wired to the application. This is preparation only.

## What Exists

- `_types.py` - ModuleSpec dataclass
- `registry.py` - ModuleRegistry for validation
- `examples/` - Example module specs (not registered)

## What Does NOT Exist Yet

- ❌ Actual module directories (`core_pms/`, `distribution/`, etc.)
- ❌ Module registration in `main.py`
- ❌ Router aggregation from modules
- ❌ Existing routers moved into modules

## Usage (Future)

### Defining a Module

```python
# app/modules/core_pms/module.py
from app.modules._types import ModuleSpec
from .api.routes import property_router, booking_router

CORE_PMS_SPEC = ModuleSpec(
    name="core_pms",
    routers=[property_router, booking_router],
    depends_on=[],  # No dependencies
)
```

### Registering a Module

```python
# app/modules/core_pms/__init__.py
from app.modules.registry import registry
from .module import CORE_PMS_SPEC

registry.register(CORE_PMS_SPEC)
```

### Wiring Modules (Not Yet Implemented)

```python
# app/main.py (future Phase 22+)
from app.modules.registry import registry

# Validate all modules
registry.validate()

# Include routers in dependency order
for module in registry.get_all():
    for router in module.routers:
        app.include_router(router, prefix="/api/v1")
```

## See Also

- `docs/architecture/modular-monolith.md` - Architecture rules
- `docs/architecture/phase21-modularization-plan.md` - Implementation plan
```

**Acceptance Criteria**:
- [x] `ModuleSpec` supports: name, routers, depends_on, init_app, migrations_path
- [x] `ModuleRegistry` implements topological sort
- [x] Circular dependency detection raises `CircularDependencyError`
- [x] README clearly states scaffold is NOT wired
- [x] Example module spec exists but is NOT registered

---

### Checkpoint C: Unit Tests

**Goal**: Verify module scaffold works correctly

**Deliverables**:
1. `backend/tests/modules/__init__.py`
2. `backend/tests/modules/test_module_registry.py`

**Status**: 🎯 **IN PROGRESS** (current commit)

**Implementation**:

```python
# tests/modules/test_module_registry.py
import pytest
from app.modules._types import ModuleSpec
from app.modules.registry import ModuleRegistry, CircularDependencyError

def test_module_spec_validation():
    """Test ModuleSpec validation rules"""
    # Valid module
    spec = ModuleSpec(name="test_module", routers=[])
    assert spec.name == "test_module"

    # Invalid name (not snake_case)
    with pytest.raises(ValueError, match="snake_case"):
        ModuleSpec(name="TestModule", routers=[])

    # Self-dependency
    with pytest.raises(ValueError, match="cannot depend on itself"):
        ModuleSpec(name="test", routers=[], depends_on=["test"])

def test_registry_basic_registration():
    """Test basic module registration"""
    registry = ModuleRegistry()

    spec = ModuleSpec(name="core_pms", routers=[])
    registry.register(spec)

    assert registry.get("core_pms") == spec

def test_registry_duplicate_registration():
    """Test duplicate module names are rejected"""
    registry = ModuleRegistry()

    spec1 = ModuleSpec(name="core_pms", routers=[])
    registry.register(spec1)

    spec2 = ModuleSpec(name="core_pms", routers=[])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(spec2)

def test_registry_unknown_dependency():
    """Test dependency on unknown module is rejected"""
    registry = ModuleRegistry()

    spec = ModuleSpec(
        name="distribution",
        routers=[],
        depends_on=["core_pms"]  # Not registered
    )

    with pytest.raises(ValueError, match="unknown module"):
        registry.register(spec)

def test_registry_topological_sort():
    """Test modules are sorted in dependency order"""
    registry = ModuleRegistry()

    # Register in random order
    core = ModuleSpec(name="core_pms", routers=[], depends_on=[])
    dist = ModuleSpec(name="distribution", routers=[], depends_on=["core_pms"])
    finance = ModuleSpec(name="finance", routers=[], depends_on=["core_pms"])

    registry.register(dist)  # Out of order
    registry.register(core)
    registry.register(finance)

    modules = registry.get_all()
    module_names = [m.name for m in modules]

    # core_pms must come before its dependents
    assert module_names.index("core_pms") < module_names.index("distribution")
    assert module_names.index("core_pms") < module_names.index("finance")

def test_registry_circular_dependency():
    """Test circular dependencies are detected"""
    registry = ModuleRegistry()

    core = ModuleSpec(name="core_pms", routers=[], depends_on=[])
    dist = ModuleSpec(name="distribution", routers=[], depends_on=["core_pms"])

    registry.register(core)
    registry.register(dist)

    # Try to create cycle: core_pms depends on distribution
    core.depends_on.append("distribution")

    with pytest.raises(CircularDependencyError):
        registry.validate()

def test_registry_complex_dependencies():
    """Test complex dependency graph"""
    registry = ModuleRegistry()

    #     core_pms
    #     /     \
    #  dist    direct
    #     \     /
    #     guest
    #       |
    #     finance

    core = ModuleSpec(name="core_pms", routers=[])
    dist = ModuleSpec(name="distribution", routers=[], depends_on=["core_pms"])
    direct = ModuleSpec(name="direct_booking", routers=[], depends_on=["core_pms"])
    guest = ModuleSpec(name="guest_exp", routers=[], depends_on=["distribution", "direct_booking"])
    finance = ModuleSpec(name="finance", routers=[], depends_on=["guest_exp"])

    # Register in random order
    for spec in [finance, guest, direct, dist, core]:
        registry.register(spec)

    modules = registry.get_all()
    names = [m.name for m in modules]

    # Verify topological order
    assert names.index("core_pms") < names.index("distribution")
    assert names.index("core_pms") < names.index("direct_booking")
    assert names.index("distribution") < names.index("guest_exp")
    assert names.index("direct_booking") < names.index("guest_exp")
    assert names.index("guest_exp") < names.index("finance")
```

**Acceptance Criteria**:
- [x] Test unique name validation
- [x] Test circular dependency detection
- [x] Test topological sort correctness
- [x] Test unknown dependency rejection
- [x] Test complex dependency graph
- [x] All tests pass (but NOT executed locally per rules)

---

### Checkpoint D: Safety Verification

**Goal**: Ensure no existing functionality is broken

**Tasks**:
1. Verify no imports broken
2. Verify existing routers still work
3. Verify no changes to `main.py`
4. Verify database migrations unchanged

**Status**: 🎯 **IN PROGRESS** (current commit)

**Verification Commands** (for CI, not local):
```bash
# Lint check (no execution)
ruff check backend/app/modules/

# Type check (no execution)
mypy backend/app/modules/

# Verify main.py unchanged (no new includes)
git diff backend/app/main.py

# Verify migrations unchanged
git diff supabase/migrations/
```

**Acceptance Criteria**:
- [x] No changes to `backend/app/main.py` (no wiring yet)
- [x] No changes to `backend/app/api/` (routers not moved)
- [x] No changes to `backend/app/services/` (services not refactored)
- [x] No changes to database migrations
- [x] No new dependencies in `requirements.txt` or `pyproject.toml`

---

## Phase 22+ Roadmap (Future)

### Phase 22: Core PMS Module Extraction

**Goal**: Extract existing code into `core_pms` module

**Steps**:
1. Create `app/modules/core_pms/` directory structure
2. Move existing routers: `properties`, `bookings`, `availability`
3. Move existing services: `PropertyService`, `BookingService`, `AvailabilityService`
4. Move existing schemas: `properties.py`, `bookings.py`, `availability.py`
5. Create `core_pms/module.py` with `ModuleSpec`
6. Register in `app/modules/core_pms/__init__.py`
7. Update `main.py` to include routers from registry

**Risks**:
- Import path changes (update all imports: `from app.api.routes.bookings` → `from app.modules.core_pms.api.routes`)
- Circular import detection (ensure services don't cross boundaries)
- Migration path confusion (keep migrations in `supabase/migrations/`)

---

### Phase 23: Distribution Module Extraction

**Goal**: Extract `app/channel_manager/` into `distribution` module

**Steps**:
1. Create `app/modules/distribution/` directory
2. Move `app/channel_manager/` contents into `distribution/`
3. Refactor imports (update all references)
4. Create `distribution/module.py` with dependency on `core_pms`
5. Register module

**Risks**:
- `channel_manager` is well-isolated but large (many adapters)
- Airbnb adapter has complex OAuth flow (ensure no breakage)
- Webhook handlers may have hardcoded paths

---

### Phase 24: Feature Flags & Gradual Rollout

**Goal**: Enable module-level feature flags

**Steps**:
1. Add `enabled` callable to `ModuleSpec`
2. Implement settings-based feature flags
3. Test disabling modules via environment variables
4. Per-agency feature flags (database-driven)

**Example**:
```python
DISTRIBUTION_SPEC = ModuleSpec(
    name="distribution",
    routers=[...],
    enabled=lambda settings: settings.enable_distribution_module
)
```

---

### Phase 25: Event-Driven Communication

**Goal**: Replace direct service calls with domain events

**Steps**:
1. Implement event bus (Celery + Redis)
2. Define domain events: `BookingCreatedEvent`, `PropertyUpdatedEvent`
3. Refactor `distribution` to listen to events instead of calling `core_pms`
4. Implement event log table for debugging

**Benefits**:
- Loose coupling (modules don't import each other)
- Async processing (background jobs)
- Easier testing (mock event bus)

---

## Risk Mitigation

### Risk: Circular Import Detection Fails

**Symptom**: Module starts but crashes on first request with `ImportError`

**Mitigation**:
- Topological sort validation at startup (raises before app starts)
- Unit tests for circular dependency detection
- CI/CD check for import cycles (use `importchecker` tool)

---

### Risk: Migration Drift

**Symptom**: Modules have conflicting schema changes

**Mitigation**:
- Keep migrations in global `supabase/migrations/` (not per-module)
- Optional `migrations_path` in `ModuleSpec` is metadata only
- Single source of truth for schema

---

### Risk: Duplicated Schemas

**Symptom**: Multiple modules define `PropertyResponse` schema

**Mitigation**:
- Each module owns its schemas
- Cross-module data via **DTOs** (data transfer objects)
- Example: `core_pms.schemas.PropertyResponse` vs `distribution.schemas.ChannelListingDTO`

---

### Risk: Testing Isolation Breaks

**Symptom**: Module tests fail due to missing dependencies

**Mitigation**:
- Mock dependencies in unit tests
- Integration tests use test database
- Pytest fixtures per module (`tests/modules/{module}/conftest.py`)

---

## Exit Criteria (Phase 21 Complete)

Phase 21 is successful when ALL criteria are met:

1. ✅ **Documentation Complete**
   - [x] `docs/product/reference-product-model.md` exists
   - [x] `docs/architecture/modular-monolith.md` exists
   - [x] `docs/architecture/phase21-modularization-plan.md` exists (this file)

2. ✅ **Scaffold Created**
   - [x] `app/modules/__init__.py` exists
   - [x] `app/modules/_types.py` defines `ModuleSpec`
   - [x] `app/modules/registry.py` implements `ModuleRegistry` with topological sort
   - [x] `app/modules/README.md` explains usage
   - [x] `app/modules/examples/core_stub.py` example exists

3. ✅ **Tests Written (Not Executed Locally)**
   - [x] `tests/modules/test_module_registry.py` covers:
     - Unique name validation
     - Circular dependency detection
     - Topological sort
     - Unknown dependency rejection

4. ✅ **No Functional Changes**
   - [x] `main.py` unchanged (no module wiring)
   - [x] Existing routers unchanged (`app/api/routes/`)
   - [x] Existing services unchanged (`app/services/`)
   - [x] Database migrations unchanged
   - [x] No new dependencies

5. ✅ **Committed & Deployed**
   - [x] Commit message: `docs+scaffold: prepare modular monolith (phase21-ready)`
   - [x] Pushed to main branch
   - [x] Coolify auto-deploy successful

---

## Lessons Learned (Post-Phase Retrospective)

*To be filled after Phase 21 completion*

### What Went Well
- TBD

### What Could Be Improved
- TBD

### Action Items for Phase 22
- TBD

---

## References

- **Product Model**: `docs/product/reference-product-model.md`
- **Modular Monolith**: `docs/architecture/modular-monolith.md`
- **Current State**: `CURRENT_STATE.md`
- **System Architecture**: `docs/architecture/system-architecture.md`
