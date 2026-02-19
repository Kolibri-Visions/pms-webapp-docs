# Module Boundaries & Dependency Rules

**Purpose:** Define strict module boundary rules and dependency constraints for PMS-Webapp's modular monolith.

**Audience:** Backend developers adding new modules or modifying existing ones.

**Last Updated:** 2025-12-27 (Phase 34)

**Status:** Normative (MUST follow these rules)

---

## Current Modules (Phase 33B)

| Module | Purpose | Dependencies |
|--------|---------|--------------|
| `core_pms` | Health checks, foundational utilities | None |
| `inventory` | Availability and blocks (inventory management) | `core_pms` |
| `bookings` | Booking CRUD and lifecycle | `core_pms`, `inventory` |
| `properties` | Property CRUD | `core_pms` |

---

## Dependency Direction Rules

### MUST Follow

1. **All modules MAY depend on `core_pms`**
   - Core provides foundational services (health, config, auth utilities)
   - Core has no dependencies (foundation layer)

2. **`inventory` MUST NOT depend on `bookings` or `properties`**
   - Inventory is a low-level domain (availability semantics)
   - Bookings and properties consume inventory, not the reverse
   - Prevents circular dependencies

3. **`bookings` MAY depend on `inventory`**
   - Bookings need conflict detection (HTTP 409 inventory_overlap)
   - See [Inventory Contract](../domain/inventory.md) for semantics

4. **`properties` SHOULD stay independent**
   - MAY depend on `core_pms` only
   - Properties are a standalone domain (no booking/inventory logic)

### MUST NOT Violate

1. **No circular dependencies**
   - Module registry validates dependencies at startup (fails fast)
   - Use topological sort to detect cycles

2. **No cross-module implementation imports**
   - DO NOT import another module's service/model implementations
   - Use public API routes, schemas, or dependency injection instead

3. **No "god modules"**
   - If a module depends on everything, refactor it
   - Consider extracting shared logic into a new foundation module

---

## Layering Rules

### Router Layer (HTTP Boundary)

**Purpose:** Handle HTTP requests/responses only.

**Rules:**
- Routers live in `app/api/routes/` (current structure)
- Routers delegate business logic to services
- Routers MUST NOT contain complex business rules
- Routers validate request schemas, return response schemas

**Example:**
```python
@router.post("/bookings", status_code=201)
async def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    # Router handles HTTP only
    result = await booking_service.create_booking(db, booking)
    return result
```

### Service Layer (Business Logic)

**Purpose:** Implement business rules and orchestration.

**Rules:**
- Services live in `app/services/`
- Services MUST NOT import routers
- Services MAY import other services (respecting module boundaries)
- Services use schemas for data transfer

**Example:**
```python
# ✅ GOOD: Service uses schemas
from app.schemas.bookings import BookingCreate

async def create_booking(db: Session, booking: BookingCreate):
    # Business logic here
    pass

# ❌ BAD: Service imports router
from app.api.routes.bookings import router  # FORBIDDEN
```

### Cross-Module Communication

**Rules:**
1. **Preferred:** Use service imports (respecting dependency direction)
   ```python
   # In bookings service
   from app.services.availability import check_conflicts
   ```

2. **Acceptable:** Use shared schemas from `app/schemas/`
   ```python
   from app.schemas.availability import AvailabilityBlock
   ```

3. **Forbidden:** Import routers or private module internals
   ```python
   # ❌ BAD
   from app.api.routes.availability import router
   from app.modules.inventory._private import internal_util
   ```

---

## How to Add a New Module

Follow this checklist when creating a new module:

### 1. Create Module Wrapper

**File:** `app/modules/{module_name}.py`

```python
"""
{Module Name} Domain Module

Description of what this module does.
"""

from ..api.routes import {router_name}
from ._types import ModuleSpec
from .registry import registry

{MODULE_NAME}_MODULE = ModuleSpec(
    name="{module_name}",
    version="1.0.0",
    router_configs=[
        ({router_name}.router, {"prefix": "/api/v1", "tags": ["{Module Name}"]}),
    ],
    depends_on=["core_pms"],  # Add dependencies as needed
    tags=["{Module Name}"],
)

registry.register({MODULE_NAME}_MODULE)
```

### 2. Register ModuleSpec with Correct Prefix/Tags

- Ensure `prefix` matches existing API paths (usually `/api/v1`)
- Use consistent tag naming (title case)
- Declare all dependencies in `depends_on` list

### 3. Add Bootstrap Import

**File:** `app/modules/bootstrap.py`

```python
try:
    from . import {module_name}  # noqa: F401
except ImportError as e:
    logger.warning(f"{Module Name} module not available: {e}")
    # Continue without module (graceful degradation)
```

### 4. Update Module Documentation

**File:** `docs/architecture/modular-monolith.md`

- Add module to "Target Modules (Roadmap)" table
- Update "Current Flow" diagram if needed
- Add example code snippet showing module structure
- Update References section with new module link

### 5. Ensure MODULES_ENABLED Fallback Works

**File:** `app/main.py`

If `MODULES_ENABLED=false`, ensure your new router is included in the fallback:

```python
if not settings.modules_enabled:
    # Add fallback mounting
    from .api.routes import {router_name}
    app.include_router({router_name}.router, prefix="/api/v1", tags=["{Module Name}"])
```

### 6. Validate Dependencies

- Run `python -m app.modules.registry` to validate (if CLI exists)
- Check for circular dependencies
- Ensure dependency order is correct

### 7. Update Runbook

**File:** `docs/ops/runbook.md`

- Add any new environment variables
- Document new endpoints for smoke tests
- Update Phase change log

### 8. Run Phase 23 Smoke After Deploy

- Execute `scripts/pms_phase23_smoke.sh` to validate endpoints
- Check logs for module mounting success
- Verify no 404s on new routes

---

## Domain-Specific Rules

### Inventory Module

**Semantics:** See [Inventory Contract](../domain/inventory.md)

**Rules:**
- Inventory defines end-exclusive date semantics (check-out day is free)
- Conflict detection returns HTTP 409 with `inventory_overlap` error code
- Bookings query inventory for conflicts, NOT the reverse

**Dependency Chain:**
```
inventory (foundation)
    ↓
bookings (consumes inventory)
```

### Bookings Module

**Dependencies:** Requires `inventory` for conflict checking.

**Rules:**
- Bookings MUST validate against inventory before creation
- Use inventory service for overlap detection
- DO NOT bypass inventory checks

### Properties Module

**Independence:** Properties should remain standalone.

**Rules:**
- No dependencies on bookings or inventory
- Properties provide metadata only (name, address, amenities)
- Future: Property availability may link to inventory (one-way dependency)

---

## Violation Examples

### ❌ BAD: Circular Dependency

```python
# inventory.py
INVENTORY_MODULE = ModuleSpec(
    name="inventory",
    depends_on=["bookings"],  # ❌ FORBIDDEN: Creates cycle
)

# bookings.py
BOOKINGS_MODULE = ModuleSpec(
    name="bookings",
    depends_on=["inventory"],  # ❌ Creates cycle with above
)
```

**Fix:** Invert dependency (bookings → inventory, not the reverse)

### ❌ BAD: Router Import in Service

```python
# services/booking_service.py
from app.api.routes.availability import check_availability_route  # ❌ FORBIDDEN

def create_booking(db, booking):
    result = check_availability_route(...)  # ❌ Service calling router
```

**Fix:** Import service function instead:
```python
from app.services.availability import check_conflicts  # ✅ GOOD

def create_booking(db, booking):
    conflicts = check_conflicts(...)  # ✅ Service calling service
```

### ❌ BAD: Missing Dependency Declaration

```python
# bookings.py
BOOKINGS_MODULE = ModuleSpec(
    name="bookings",
    depends_on=["core_pms"],  # ❌ Missing "inventory" dependency
)

# But in code:
from app.services.availability import check_conflicts  # ⚠️ Undeclared dependency
```

**Fix:** Declare all dependencies:
```python
BOOKINGS_MODULE = ModuleSpec(
    name="bookings",
    depends_on=["core_pms", "inventory"],  # ✅ GOOD: Explicit dependency
)
```

---

## Testing Module Boundaries

### Unit Tests

**Test:** Module dependency validation
```python
def test_inventory_has_no_circular_deps():
    from app.modules.registry import registry
    modules = registry.get_all()

    # Ensure inventory comes before bookings
    names = [m.name for m in modules]
    assert names.index("inventory") < names.index("bookings")
```

### Integration Tests

**Test:** Cross-module communication
```python
def test_bookings_can_check_inventory():
    # Ensure bookings can call inventory service
    from app.services.availability import check_conflicts

    conflicts = check_conflicts(...)
    assert isinstance(conflicts, list)
```

### Smoke Tests

**Test:** Module mounting order
```bash
# scripts/pms_phase23_smoke.sh
curl http://localhost:8000/health  # core_pms
curl http://localhost:8000/api/v1/availability  # inventory
curl http://localhost:8000/api/v1/bookings  # bookings (depends on inventory)
```

---

## References

- **Module Registry:** `app/modules/registry.py`
- **Module Types:** `app/modules/_types.py`
- **Bootstrap:** `app/modules/bootstrap.py`
- **Inventory Contract:** `docs/domain/inventory.md` (date semantics, conflict rules)
- **Modular Monolith Overview:** `docs/architecture/modular-monolith.md`

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2025-12-27 | Initial module boundaries documentation (Phase 34) | Claude Code |
