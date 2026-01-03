# Modular Monolith Phase 21: Registry-Driven Module System

**Date:** 2026-01-03
**Status:** Planning / Scaffold Only
**Phase:** 21 (Post-Phase 20 Inventory Validation)

## Context

Phase 20 successfully validated core inventory mechanics (exclusion constraints, concurrency, availability blocks). With the core business logic proven stable, Phase 21 begins architectural improvements to support long-term maintainability and modularity.

**Why Now?**
- Phase 20 validated that our domain logic is sound
- Current module bootstrap is manual and error-prone (easy to forget router mounts)
- Channel Manager module already demonstrates the need for optional/toggleable features
- Future modules (reporting, analytics, integrations) will benefit from declarative registration

**Constraints:**
- NO refactors of existing code during Phase 21 scaffolding
- NO changes to runtime behavior (scaffold only, not wired in)
- Docs-first approach: define the pattern before implementing
- Additive only: new files, no modifications to existing bootstrap

## Goals

1. **Define ModuleSpec Pattern**: Standardize how modules declare themselves (name, routers, dependencies, feature flags)
2. **Document Migration Strategy**: Plan how to transition from manual router mounting to registry-driven
3. **Create Minimal Scaffold**: Add code structures without wiring them into runtime yet
4. **Enable Future Modularity**: Set foundation for plugin-like module system

## ModuleSpec Definition

A `ModuleSpec` describes a feature module and its integration points:

```python
from dataclasses import dataclass
from typing import List, Optional, Callable
from fastapi import APIRouter

@dataclass
class ModuleSpec:
    """
    Specification for a feature module in the PMS application.

    Modules are self-contained feature sets that can be:
    - Toggled via environment variables
    - Dynamically mounted at runtime (future)
    - Tested independently
    - Deployed selectively (future)
    """

    # Module identity
    name: str
    """Unique module identifier (e.g., 'channel_manager', 'inventory', 'reporting')"""

    # Feature flag
    enabled_env_var: str
    """Environment variable name that controls module enablement (e.g., 'CHANNEL_MANAGER_ENABLED')"""

    # Routing
    routers: List[APIRouter]
    """FastAPI routers to mount when module is enabled"""

    router_prefix: str
    """URL prefix for all module routes (e.g., '/api/v1/channel-connections')"""

    # Dependencies (future)
    dependencies: Optional[List[str]] = None
    """Other modules this module depends on (module names)"""

    # Lifecycle hooks (future)
    on_startup: Optional[Callable] = None
    """Function to call during app startup if module is enabled"""

    on_shutdown: Optional[Callable] = None
    """Function to call during app shutdown if module is enabled"""

    # Metadata
    version: str = "1.0.0"
    """Module version (semantic versioning)"""

    description: Optional[str] = None
    """Human-readable description of module functionality"""
```

## Example: Inventory Module Spec

```python
# backend/app/modules/inventory/module.py (future location)
from app.modules.core.module_spec import ModuleSpec
from app.api.routers import availability, availability_blocks

inventory_module = ModuleSpec(
    name="inventory",
    enabled_env_var="INVENTORY_ENABLED",  # Default: true
    routers=[
        availability.router,
        availability_blocks.router,
    ],
    router_prefix="/api/v1",
    version="1.0.0",
    description="Core inventory and availability management",
)
```

## Example: Channel Manager Module Spec

```python
# backend/app/modules/channel_manager/module.py (future refactor)
from app.modules.core.module_spec import ModuleSpec
from app.api.routers.channel_connections import router as channel_router

channel_manager_module = ModuleSpec(
    name="channel_manager",
    enabled_env_var="CHANNEL_MANAGER_ENABLED",
    routers=[channel_router],
    router_prefix="/api/v1",
    dependencies=["inventory"],  # Requires inventory module
    version="1.0.0",
    description="External channel integrations (Airbnb, Booking.com, etc.)",
)
```

## Module Registry Pattern (Future)

Once ModuleSpecs are defined, a central registry can manage module lifecycle:

```python
# backend/app/modules/core/registry.py (future implementation)
from typing import Dict, List
from app.modules.core.module_spec import ModuleSpec
from app.core.config import get_settings
import os

class ModuleRegistry:
    """
    Central registry for all application modules.
    Handles module discovery, dependency resolution, and router mounting.
    """

    def __init__(self):
        self._modules: Dict[str, ModuleSpec] = {}

    def register(self, module: ModuleSpec) -> None:
        """Register a module spec"""
        self._modules[module.name] = module

    def is_enabled(self, module: ModuleSpec) -> bool:
        """Check if module is enabled via environment variable"""
        env_value = os.getenv(module.enabled_env_var, "true")
        return env_value.lower() in ("true", "1", "yes")

    def get_enabled_modules(self) -> List[ModuleSpec]:
        """Return list of modules that should be loaded"""
        enabled = []
        for module in self._modules.values():
            if self.is_enabled(module):
                enabled.append(module)
        return enabled

    def mount_routers(self, app) -> None:
        """Mount all routers from enabled modules"""
        for module in self.get_enabled_modules():
            for router in module.routers:
                app.include_router(router, prefix=module.router_prefix)
                print(f"✓ Mounted {module.name} router: {router.prefix}")

# Global registry instance
registry = ModuleRegistry()
```

## Migration Strategy

**Phase 21 (Current):**
1. ✅ Create `ModuleSpec` dataclass (scaffold only)
2. ✅ Document pattern and examples (this file)
3. ✅ No runtime changes (existing bootstrap unchanged)

**Phase 22 (Future):**
1. Create module specs for existing modules (inventory, channel_manager, properties, bookings, guests)
2. Implement `ModuleRegistry` class
3. Update `backend/app/main.py` to use registry for router mounting
4. Test that all routers still mount correctly (no behavior change)

**Phase 23 (Future):**
1. Add dependency resolution to registry
2. Add lifecycle hooks (on_startup, on_shutdown)
3. Add module health checks
4. Consider dynamic module loading (hot reload for dev)

**Phase 24+ (Future):**
1. Split large modules into smaller ones based on bounded contexts
2. Consider separate module deployments (microservices-lite)
3. Add module versioning and compatibility checks

## Benefits

**Immediate (Phase 21+):**
- Clear documentation of module structure
- Foundation for future improvements
- No risk (scaffold only, not wired in)

**Short-term (Phase 22-23):**
- Declarative module registration (less boilerplate)
- Centralized enable/disable logic (easier feature flags)
- Better module boundaries (explicit dependencies)
- Easier testing (can test modules in isolation)

**Long-term (Phase 24+):**
- Plugin-like architecture (add modules without touching main.py)
- Selective deployment (disable unused modules in production)
- Module marketplace potential (third-party modules)
- Gradual migration to microservices if needed

## Current Module Inventory

Based on existing codebase structure:

| Module | Current Status | Router(s) | Feature Flag |
|--------|---------------|-----------|--------------|
| **Properties** | Core | `app.api.routers.properties` | Always enabled |
| **Bookings** | Core | `app.api.routers.bookings` | Always enabled |
| **Guests** | Core | `app.api.routers.guests` | Always enabled |
| **Inventory** | Core | `app.api.routers.availability`, `app.api.routers.availability_blocks` | Always enabled |
| **Channel Manager** | Optional | `app.api.routers.channel_connections` | `CHANNEL_MANAGER_ENABLED` |
| **Sync (Future)** | Planned | Sync batch status, manual triggers | TBD |
| **Reporting (Future)** | Planned | Analytics, metrics, dashboards | TBD |

## Phase 21 Deliverables

**Documentation (This File):**
- ✅ ModuleSpec definition
- ✅ Example module specs
- ✅ Registry pattern design
- ✅ Migration strategy
- ✅ Benefits and timeline

**Code Scaffold:**
- ✅ `backend/app/modules/core/module_spec.py` - ModuleSpec dataclass
- Future: `backend/app/modules/core/registry.py` - ModuleRegistry class (Phase 22)
- Future: Individual `module.py` files per feature (Phase 22)

**Integration:**
- Phase 21: NONE (scaffold only, not wired in)
- Phase 22: Wire registry into `main.py` bootstrap
- Phase 23: Add lifecycle hooks and dependency resolution

## Open Questions (To Be Resolved)

1. **Module Directory Structure**: Keep flat `app/modules/` or nest by domain (`app/modules/inventory/`, `app/modules/channel_manager/`)?
2. **Registry Singleton**: Use global instance or FastAPI dependency injection?
3. **Module Discovery**: Auto-discover modules via file system scan or explicit registration?
4. **Testing Strategy**: How to test modules in isolation? Separate test fixtures per module?
5. **Database Migrations**: Should modules own their migrations? How to handle cross-module schema dependencies?

## References

- Existing modular architecture docs: `backend/docs/architecture/modular-monolith.md`
- Module boundaries: `backend/docs/architecture/module-boundaries.md`
- Current module system: `backend/docs/architecture/module-system.md`
- Channel Manager module: `backend/docs/architecture/channel-manager.md`

## Next Steps

1. Review this design with team
2. Create `module_spec.py` scaffold (Phase 21)
3. Plan Phase 22 implementation timeline
4. Consider: Should we add ADR (Architecture Decision Record) for module registry pattern?
