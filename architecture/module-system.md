# Module System Architecture

**Purpose**: Document the module registry pattern, graceful degradation, and feature flag control

**Audience**: Backend developers, architects

**Source of Truth**: `backend/app/modules/bootstrap.py`, `backend/app/main.py:117-136`

---

## Overview

The module system provides **modular router registration** with graceful degradation instead of hardcoded imports in `main.py`.

**Key Benefits**:
- Modules self-register when imported (auto-registration pattern)
- Module import failures logged but don't crash the app (graceful degradation)
- Feature flag control (`MODULES_ENABLED`) for ops safety

**Feature Flag**: `MODULES_ENABLED` (default: `true`)
- If `true`: Use module system (`mount_modules(app)`)
- If `false`: Use fallback (explicit router mounting in `main.py`)

---

## Module Registry Pattern

### How It Works

1. **Module Definition** (e.g., `backend/app/modules/properties.py`):
   ```python
   from .registry import registry

   # Module self-registers when imported
   registry.register(
       name="properties",
       version="1.0.0",
       router=properties_router,
       config={"prefix": "/api/v1", "tags": ["Properties"]}
   )
   ```

2. **Bootstrap** (`backend/app/modules/bootstrap.py:30-140`):
   ```python
   def mount_modules(app: FastAPI):
       # Import modules to trigger self-registration
       from . import core        # Health router
       from . import inventory   # Availability router
       from . import properties  # Properties router
       from . import bookings    # Bookings router

       # Conditionally import Channel Manager
       if settings.channel_manager_enabled:
           from . import channel_manager

       # Mount all registered modules
       registry.mount_all(app)
   ```

3. **Main App** (`backend/app/main.py:117-124`):
   ```python
   if settings.modules_enabled:
       mount_modules(app)  # Use module system
   else:
       # Fallback: explicit router mounting
       app.include_router(properties.router, prefix="/api/v1", tags=["Properties"])
       # ...
   ```

---

## Registered Modules

### Current Modules (as of 2025-12-30)

1. **core** - Health router
   - Route: `/health`
   - Purpose: Health checks, readiness checks

2. **inventory** - Availability router
   - Route: `/api/v1/availability`
   - Purpose: Availability blocks, inventory ranges

3. **properties** - Properties router
   - Route: `/api/v1/properties`
   - Purpose: Property CRUD operations

4. **bookings** - Bookings router
   - Route: `/api/v1/bookings`
   - Purpose: Booking CRUD operations

5. **channel_manager** - Channel Manager router (CONDITIONAL)
   - Route: `/api/v1/channel-manager` (or similar, check code)
   - Purpose: Channel sync, webhooks
   - **Feature Flag**: `CHANNEL_MANAGER_ENABLED` (default: `false`)
   - Only imported if `CHANNEL_MANAGER_ENABLED=true`

---

## Graceful Degradation

### Module Import Failures

**Behavior**: If a module import fails, log warning and continue without that module

**Example** (`backend/app/modules/bootstrap.py:62-71`):
```python
try:
    from . import core  # noqa: F401
except ImportError as e:
    logger.warning(f"Core module not available: {e}")
    # Continue without core module (graceful degradation)
```

**Impact**: App starts even if some modules are broken, but missing module endpoints return 404

---

### Database Unavailability

**Behavior**: If database is unavailable at startup, app runs in **degraded mode**

**What Works**:
- Auth-only endpoints (JWT validation, no DB required)
- Health endpoint (`/health`) returns 200

**What Fails**:
- DB-dependent endpoints return `503 Service Unavailable`
- `/health/ready` returns 503

**Where Implemented**: `backend/app/main.py:39-87` (lifespan handler)

**Related Docs**: [Runbook - DB DNS / Degraded Mode](../ops/runbook.md#db-dns--degraded-mode)

---

## Fallback Routing

### When MODULES_ENABLED=false

If `MODULES_ENABLED=false` (or unset and defaults to false), the app uses **explicit router mounting** instead of the module system.

**Where**: `backend/app/main.py:126-136`

**Code**:
```python
else:
    logger.warning("MODULES_ENABLED=false → Mounting routers via fallback (module system bypassed)")
    # Fallback: Mount routers explicitly (same as modules do)
    from .core.health import router as health_router
    app.include_router(health_router)

    from .api.routes import availability, bookings, properties
    app.include_router(properties.router, prefix="/api/v1", tags=["Properties"])
    app.include_router(bookings.router, prefix="/api/v1", tags=["Bookings"])
    app.include_router(availability.router, prefix="/api/v1", tags=["Availability"])
```

**Use Case**: Ops safety kill-switch if module system has issues

---

## Module Configuration

### Module Specification

Each module can specify:
- **name**: Module identifier (e.g., `"properties"`)
- **version**: Module version (e.g., `"1.0.0"`)
- **router**: FastAPI router instance
- **config**: Router configuration (prefix, tags, dependencies)

### Example Configuration

```python
registry.register(
    name="properties",
    version="1.0.0",
    router=properties_router,
    config={
        "prefix": "/api/v1",
        "tags": ["Properties"],
        # Optional: dependencies=["core"]
    }
)
```

---

## Validation

### Circular Dependency Detection

**Where**: `backend/app/modules/registry.py` (assumed, check code)

**Purpose**: Prevent circular dependencies between modules

**Behavior**: If circular dependency detected, raise `CircularDependencyError` at startup

---

## Code References

**Module Bootstrap**:
- `backend/app/modules/bootstrap.py` (lines 30-140)
- Imports modules, validates registry, mounts routers

**Main App**:
- `backend/app/main.py` (lines 117-136)
- Feature flag check, module vs fallback routing

**Module Registry**:
- `backend/app/modules/registry.py` (implementation details)

**Module Definitions**:
- `backend/app/modules/core.py` - Health module
- `backend/app/modules/inventory.py` - Availability module
- `backend/app/modules/properties.py` - Properties module
- `backend/app/modules/bookings.py` - Bookings module
- `backend/app/modules/channel_manager.py` - Channel Manager module (conditional)

---

## Related Documentation

- [Feature Flags](../ops/feature-flags.md) - `MODULES_ENABLED` flag reference
- [Channel Manager Architecture](channel-manager.md) - Channel Manager module details
- [Runbook](../ops/runbook.md) - Troubleshooting degraded mode

---

**Last Updated**: 2025-12-30
**Maintained By**: Backend Team
