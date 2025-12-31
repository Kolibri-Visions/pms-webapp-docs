# Modules & Entitlements Architecture

**Document Status**: Living architecture document
**Last Updated**: 2025-12-30
**Owner**: Backend Team

## Overview

This document describes the **modular monolith** architecture for the PMS backend, focusing on:
- Global feature flags (`MODULES_ENABLED`)
- Per-agency entitlements (`agency_features` table)
- Router registration gating
- Feature enforcement at runtime

## Goals

1. **Modular Activation**: Enable/disable entire modules (e.g., channel sync, direct booking) globally or per-agency
2. **Gradual Rollout**: Deploy features to production but activate only for pilot agencies
3. **Graceful Degradation**: If a module is disabled, return 404 or 503 instead of crashing
4. **Auditability**: Log all feature access attempts for security and compliance

## Architecture: Modular Monolith

The PMS backend is a **monolith** (single deployment unit) but **modular** (features can be toggled).

### Key Concepts

- **Module**: A logical grouping of features (e.g., "channel_sync", "direct_booking", "owner_portal")
- **Global Feature Flag**: Environment variable that enables/disables a module globally
- **Agency Entitlement**: Per-agency setting that enables/disables a module for specific agencies
- **Router Gating**: Conditionally register FastAPI routers based on feature flags
- **Runtime Enforcement**: Check entitlements on every request using dependencies

## Global Feature Flags

### Environment Variables

Global feature flags are set via environment variables:

```bash
# .env
MODULES_ENABLED=channel_sync,direct_booking,owner_portal
```

**Format**: Comma-separated list of enabled modules.

**Example**:
- `MODULES_ENABLED=channel_sync` → Only channel sync is enabled
- `MODULES_ENABLED=*` → All modules enabled (default for development)
- `MODULES_ENABLED=` (empty) → All modules disabled

### Usage in Code

```python
# app/core/config.py
class Settings(BaseSettings):
    MODULES_ENABLED: str = "*"  # Default: all modules enabled

    def is_module_enabled(self, module: str) -> bool:
        """Check if a module is enabled globally."""
        if self.MODULES_ENABLED == "*":
            return True
        enabled_modules = [m.strip() for m in self.MODULES_ENABLED.split(",")]
        return module in enabled_modules

settings = Settings()
```

**Example Check**:
```python
if settings.is_module_enabled("channel_sync"):
    # Register channel sync router
    app.include_router(channel_sync_router)
```

## Per-Agency Entitlements

### Database Schema

The `agency_features` table stores per-agency feature entitlements:

```sql
CREATE TABLE agency_features (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id),
  feature_name TEXT NOT NULL,  -- e.g., 'channel_sync', 'direct_booking'
  enabled BOOLEAN DEFAULT TRUE,
  config JSONB,  -- Feature-specific config (e.g., {"max_properties": 10})
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(agency_id, feature_name)
);
```

**RLS Policy**:
```sql
-- Agencies can only read their own features
CREATE POLICY agency_features_select ON agency_features
  FOR SELECT USING (agency_id = current_setting('app.current_agency_id')::uuid);
```

### Usage Pattern

1. **Global Check**: Is the module enabled globally? (`MODULES_ENABLED`)
2. **Agency Check**: Is the module enabled for this agency? (`agency_features`)

**Example**:
```python
async def require_feature(
    feature_name: str,
    agency_id: UUID,
    db: AsyncSession
) -> None:
    """
    Dependency to enforce feature entitlement.
    Raises 404 if feature is disabled globally or for this agency.
    """
    # 1. Global check
    if not settings.is_module_enabled(feature_name):
        raise HTTPException(
            status_code=404,
            detail=f"Feature '{feature_name}' is not available"
        )

    # 2. Agency check
    result = await db.execute(
        select(AgencyFeature).where(
            AgencyFeature.agency_id == agency_id,
            AgencyFeature.feature_name == feature_name,
            AgencyFeature.enabled == True
        )
    )
    feature = result.scalars().first()

    if not feature:
        raise HTTPException(
            status_code=403,
            detail=f"Your agency does not have access to '{feature_name}'"
        )
```

## Router Registration Gating

**Problem**: If a module is disabled, we don't want to register its routes at all (cleaner than 404s everywhere).

**Solution**: Conditionally register routers based on global feature flags.

### Example: Channel Sync Router

```python
# app/main.py
from app.core.config import settings
from app.routers import channel_sync

app = FastAPI()

# Register routers conditionally
if settings.is_module_enabled("channel_sync"):
    app.include_router(
        channel_sync.router,
        prefix="/api/v1/channel-sync",
        tags=["channel_sync"]
    )
```

**Result**:
- If `channel_sync` is **enabled**: Routes are registered, endpoints work
- If `channel_sync` is **disabled**: Routes are not registered, return 404

### Pattern for All Routers

```python
ROUTERS = [
    ("channel_sync", channel_sync.router, "/api/v1/channel-sync"),
    ("direct_booking", direct_booking.router, "/api/v1/direct-booking"),
    ("owner_portal", owner_portal.router, "/api/v1/owners"),
]

for module_name, router, prefix in ROUTERS:
    if settings.is_module_enabled(module_name):
        app.include_router(router, prefix=prefix, tags=[module_name])
```

## Runtime Enforcement

**Problem**: Even if a router is registered, we want to enforce agency-level entitlements.

**Solution**: Use FastAPI dependencies to check entitlements on every request.

### Dependency: `require_feature`

```python
# app/dependencies.py
from app.core.entitlements import get_enabled_modules_for_agency

async def require_feature(
    feature_name: str
) -> Callable:
    """
    Returns a dependency that checks if the feature is enabled for the agency.
    Usage: dependencies=[Depends(require_feature("channel_sync"))]
    """
    async def _check(
        agency_id: UUID = Depends(get_current_agency_id),
        db: AsyncSession = Depends(get_db)
    ):
        enabled_modules = await get_enabled_modules_for_agency(agency_id, db)
        if feature_name not in enabled_modules:
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature_name}' is not enabled for your agency"
            )
    return _check
```

### Usage in Routers

```python
# app/routers/channel_sync.py
router = APIRouter()

@router.post("/sync")
async def trigger_sync(
    # ... other dependencies
    _=Depends(require_feature("channel_sync"))  # Enforce entitlement
):
    # Only reached if feature is enabled for this agency
    ...
```

## Helper Functions

### `get_enabled_modules_for_agency`

```python
# app/core/entitlements.py
async def get_enabled_modules_for_agency(
    agency_id: UUID,
    db: AsyncSession
) -> set[str]:
    """
    Returns a set of enabled module names for this agency.
    Caches results in Redis for performance.
    """
    # Check cache first
    cache_key = f"agency:{agency_id}:modules"
    cached = await redis.get(cache_key)
    if cached:
        return set(cached.split(","))

    # Query DB
    result = await db.execute(
        select(AgencyFeature.feature_name).where(
            AgencyFeature.agency_id == agency_id,
            AgencyFeature.enabled == True
        )
    )
    modules = {row[0] for row in result}

    # Cache for 5 minutes
    await redis.setex(cache_key, 300, ",".join(modules))

    return modules
```

## Example: Complete Feature Gating Flow

### 1. Global Feature Flag (Environment)

```bash
# .env
MODULES_ENABLED=channel_sync,direct_booking
```

### 2. Router Registration (Startup)

```python
# app/main.py
if settings.is_module_enabled("channel_sync"):
    app.include_router(channel_sync_router, prefix="/api/v1/channel-sync")
```

### 3. Per-Agency Entitlement (Database)

```sql
-- Enable channel_sync for Agency A
INSERT INTO agency_features (agency_id, feature_name, enabled)
VALUES ('uuid-agency-a', 'channel_sync', TRUE);

-- Disable for Agency B (or no row = disabled)
-- No insert = feature not available
```

### 4. Runtime Check (Dependency)

```python
@router.post("/sync")
async def trigger_sync(
    agency_id: UUID = Depends(get_current_agency_id),
    _=Depends(require_feature("channel_sync"))  # ← Checks DB
):
    # Agency must have channel_sync enabled to reach here
    ...
```

### 5. Result

| Scenario | Global Flag | Agency Feature | Result |
|----------|-------------|----------------|--------|
| Module disabled globally | `MODULES_ENABLED=direct_booking` | Enabled | **404** (router not registered) |
| Module enabled globally, agency disabled | `MODULES_ENABLED=channel_sync` | Not enabled | **403** (dependency rejects) |
| Module enabled globally, agency enabled | `MODULES_ENABLED=channel_sync` | Enabled | **200** (success) |

## Rollout Strategy

### Phase 1: Global Kill Switch Only
- Deploy with `MODULES_ENABLED=*` (all enabled)
- No per-agency checks yet
- **Goal**: Test global gating mechanism

### Phase 2: Per-Agency Entitlements
- Deploy `agency_features` table
- Add `require_feature()` dependencies
- Enable for pilot agencies only
- **Goal**: Gradual rollout to select agencies

### Phase 3: Production Rollout
- Enable for all agencies via migration:
  ```sql
  INSERT INTO agency_features (agency_id, feature_name, enabled)
  SELECT id, 'channel_sync', TRUE FROM agencies;
  ```
- Monitor for issues
- **Goal**: 100% agency coverage

## Monitoring & Observability

### Metrics to Track
- **Feature access attempts**: Count per feature per agency
- **Feature denial rate**: 403s due to entitlement checks
- **Cache hit rate**: Redis cache effectiveness for entitlements

### Logs to Capture
- Feature check failures (403s)
- Global feature flag changes (env var updates)
- Agency feature updates (DB inserts/updates)

### Alerts
- Alert on high 403 rate (> 5% of requests)
- Alert on cache misses (> 50%)
- Alert on unauthorized feature access attempts

## FAQ

**Q: What happens if a module is disabled mid-request?**
A: The request continues with the cached entitlement. Cache expires after 5 minutes.

**Q: How do we test feature gating?**
A: Use integration tests with different `MODULES_ENABLED` values and DB states.

**Q: Can features depend on other features?**
A: Not yet. Future enhancement: feature dependency graph.

**Q: How do we disable a feature in emergency?**
A: Set `MODULES_ENABLED=` (empty) and redeploy, or update `agency_features.enabled = FALSE`.

## Related Documents
- [Product Backlog](../product/PRODUCT_BACKLOG.md) - Epic A: Foundation & Ops (RBAC, feature flags, agency_features)
- [Release Plan](../product/RELEASE_PLAN.md) - MVP → Beta → Prod-ready milestones
- [Project Status](../PROJECT_STATUS_LIVE.md) - Current deployment status
