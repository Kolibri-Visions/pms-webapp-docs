# Modular Monolith Architecture

**Status**: Phase 23 (Active - Smoke Scripts & Tooling)
**Last Updated**: 2025-12-26

---

## Definition

**Modular Monolith**: A single deployment unit (one codebase, one database, one process) organized into loosely-coupled modules with clear boundaries and explicit dependencies.

**Goals**:
- **Organized Complexity**: Large codebase remains navigable and comprehensible
- **Team Scalability**: Multiple developers/teams can work on different modules
- **Minimal Debugging**: Clear boundaries prevent circular dependencies and "spaghetti code"
- **Migration Path**: Can extract modules into microservices later if needed
- **Performance**: No network overhead, shared database transactions

**Non-Goals**:
- ❌ Microservices (single deployment, not distributed)
- ❌ Separate databases per module (shared PostgreSQL with schema isolation)
- ❌ Independent deployment (modules deployed together)

---

## Module Boundaries & Responsibilities

### Module Structure

Each module MUST have:
1. **Clear Responsibility**: Single domain/business capability
2. **Public Interface**: Explicit API/service exports
3. **Private Implementation**: Internal details hidden
4. **Dependency Declaration**: Explicit `depends_on` list
5. **Independent Tests**: Module can be tested in isolation

### Defined Modules

#### 1. Core PMS (`core_pms`)

**Responsibility**: Foundational property and booking management

**Boundaries**:
- Properties CRUD and lifecycle
- Booking creation, updates, status workflow
- Availability/inventory management with conflict detection
- Guest management
- Manual pricing (no dynamic rules)

**Public Interface** (Services):
- `PropertyService` - Property management
- `BookingService` - Booking lifecycle
- `AvailabilityService` - Availability queries, block management
- `GuestService` - Guest CRUD

**Routes**:
- `/api/v1/properties`
- `/api/v1/bookings`
- `/api/v1/availability`

**Database Tables**:
- `properties`, `bookings`, `guests`
- `availability_blocks`, `inventory_ranges`

**Dependencies**: NONE (foundational module)

---

#### 2. Distribution (`distribution`)

**Responsibility**: Multi-channel booking platform integrations

**Boundaries**:
- Channel connection management (OAuth, credentials)
- Bidirectional sync (rate, availability, reservations)
- Webhook receivers for platform events
- iCal export/import for unsupported platforms
- Sync error handling and retry logic

**Public Interface** (Services):
- `ChannelConnectionService` - Platform connections
- `SyncEngineService` - Synchronization orchestration
- `WebhookHandlerService` - Event processing

**Routes**:
- `/api/v1/channel-connections`
- `/api/v1/channels/sync`
- `/api/v1/webhooks/{platform}`

**Database Tables**:
- `channel_connections`, `channel_sync_logs`
- `channel_listings`, `events`

**Dependencies**: `core_pms` (reads bookings, updates availability)

---

#### 3. Direct Booking (`direct_booking`)

**Responsibility**: Public-facing booking engine and listings

**Boundaries**:
- Public property listings (guest view)
- Search/filter interface
- Booking form/widget
- Custom domain support (white-label)
- SEO optimization

**Public Interface** (Services):
- `ListingService` - Public property listings
- `BookingEngineService` - Direct booking flow
- `SearchService` - Property search/filter

**Routes** (Future):
- `/listings` - Public endpoints
- `/book` - Direct booking submission

**Database Tables** (Future):
- `public_listings`, `booking_requests`
- `custom_domains`, `website_settings`

**Dependencies**: `core_pms` (reads properties, creates bookings)

---

#### 4. Guest Experience (`guest_experience`)

**Responsibility**: Guest portal and communication

**Boundaries**:
- Guest portal (login, view bookings)
- Digital Gästemappe (house rules, WiFi, instructions)
- Automated email templates
- Document uploads

**Public Interface** (Services):
- `GuestPortalService` - Guest dashboard
- `CommunicationService` - Email automation
- `DocumentService` - File uploads/downloads

**Routes** (Future):
- `/guest/portal`
- `/guest/bookings`
- `/guest/documents`

**Database Tables** (Future):
- `guest_portal_access`, `digital_guides`
- `email_templates`, `documents`

**Dependencies**: `core_pms`, `distribution` (for channel bookings)

---

#### 5. Owner Portal (`owner_portal`)

**Responsibility**: Property owner dashboard and reporting

**Boundaries**:
- Owner-specific dashboard
- Financial statements
- Performance reporting (occupancy, ADR, RevPAR)
- Document management

**Public Interface** (Services):
- `OwnerDashboardService` - KPI aggregation
- `StatementService` - Financial statements
- `ReportingService` - Custom reports

**Routes** (Future):
- `/owner/dashboard`
- `/owner/statements`
- `/owner/reports`

**Database Tables** (Future):
- `owner_statements`, `owner_payouts`
- `owner_reports`

**Dependencies**: `core_pms`, `finance`

---

#### 6. Finance (`finance`)

**Responsibility**: Invoicing, payments, commissions, payouts

**Boundaries**:
- Invoice generation
- Payment processing (Stripe)
- Commission calculation
- Tax reporting
- Payout management

**Public Interface** (Services):
- `InvoiceService` - Invoice CRUD
- `PaymentService` - Payment processing
- `CommissionService` - Fee calculation
- `PayoutService` - Owner payouts

**Routes** (Future):
- `/api/v1/invoices`
- `/api/v1/payments`
- `/api/v1/payouts`

**Database Tables** (Future):
- `invoices`, `payments`, `commissions`
- `payouts`, `tax_records`

**Dependencies**: `core_pms` (for booking amounts)

---

## Implementation Phases

### Phase 21: Module Registry Scaffold (Complete)

**Goal**: Establish modular monolith foundation without disrupting existing code.

**Implemented**:
- `ModuleSpec` dataclass (`app/modules/_types.py`)
- `ModuleRegistry` with dependency validation (`app/modules/registry.py`)
- Bootstrap integration (`app/modules/bootstrap.py`)
- Example `core_pms` module wrapping health router only

**Outcome**: Module system validated, ready for incremental adoption.

---

### Phase 22: Core API Router Registration (Complete)

**Goal**: Register existing v1 API routers (properties, bookings, availability) into module system using wrap-only approach.

**Implemented**:
- `router_configs` field added to `ModuleSpec` for prefix/tags support
- `api_v1` module created wrapping 3 core routers
- Updated `mount_all()` to handle configured routers
- Removed direct `include_router()` calls from `main.py`

**Constraints Honored**:
- ✅ No file moves (routers remain in `app/api/routes/`)
- ✅ No API path changes (`/api/v1/properties`, etc.)
- ✅ No prefix/tag changes (exact preservation)
- ✅ No auth/RBAC changes

**Outcome**: Core API fully managed by module system, dependency graph established (`api_v1` → `core_pms`).

---

### Phase 23: Smoke Scripts & Tooling (Current)

**Goal**: Provide production-grade smoke testing tools for quick confidence checks and post-deployment validation.

**Implemented**:
- **`pms_smoke_common.sh`**: Shared helpers library
  - `require_env()` - Environment variable validation
  - `fetch_token()` - Supabase JWT authentication
  - `http_get()` / `http_get_json()` - HTTP helpers
  - `assert_http_code()` - Status code assertions
  - Security: Never prints secrets, uses `set -euo pipefail`

- **`pms_phase23_smoke.sh`**: Quick confidence check
  - Tests: `/health`, `/health/ready`, `/openapi.json`
  - Authenticated tests: Properties, Bookings, Availability APIs
  - Exit codes: 0 (pass), 1 (fail)
  - Suitable for CI/CD pipelines and post-deployment checks

**Design Principles**:
- Minimal dependencies (bash, curl, python3 only)
- Clear error messages with exit codes
- Optional PID for availability testing
- Environment file support (`/root/pms_env.sh`)
- Portable (works in Coolify container terminal and SSH)

**Outcome**: Fast smoke tests available for production validation without requiring pytest/test framework.

---

### Phase 24+ (Future)

**Planned Modules**:
- `distribution` - Channel Manager integration (Airbnb, Booking.com, etc.)
- `direct_booking` - Public booking engine
- `guest_experience` - Guest portal & communication
- `owner_portal` - Owner dashboard & reporting
- `finance` - Invoicing, payments, commissions

**Key Features**:
- Event-driven cross-module communication (Celery/Redis)
- Per-module settings/migrations isolation
- Feature flags for gradual rollout

---

## Dependency Rules (Anti-Debugging)

### Hard Rules

1. **NO Circular Dependencies**
   - Module A depends on B → B MUST NOT depend on A
   - Detected via topological sort in `ModuleRegistry.validate()`
   - **Violation = Build Failure**

2. **API → Service → Repository → Database**
   - API routers ONLY call services/use cases
   - Services ONLY call repositories or other services
   - NO direct SQL queries in routers
   - **Violation = Code Review Rejection**

3. **Shared Code via `/app/shared` ONLY**
   - Common utilities (logging, metrics, encryption) in shared
   - NO business logic in shared
   - Shared module has NO dependencies (leaf node)
   - **Keep shared minimal** - prefer duplication over premature abstraction

4. **Domain Models/DTOs per Module**
   - Each module owns its Pydantic schemas
   - Cross-module data via **explicit interfaces** (ports)
   - NO direct schema imports across modules
   - Use **data transfer objects (DTOs)** for cross-module communication

5. **Events for Cross-Module Communication**
   - Prefer **domain events** over direct service calls (future: Celery/Redis)
   - Example: `BookingCreatedEvent` emitted by `core_pms`, consumed by `distribution`
   - Decouples modules, allows async processing

---

### Layer Separation

```
┌──────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                │
│  - HTTP routing                                      │
│  - Request validation (Pydantic)                     │
│  - Response serialization                            │
│  - Authentication/Authorization (JWT, RBAC)          │
│  - Dependency injection                              │
└──────────────────┬───────────────────────────────────┘
                   │ (Depends↓)
┌──────────────────▼───────────────────────────────────┐
│                 Service Layer                        │
│  - Business logic                                    │
│  - Use case orchestration                            │
│  - Transaction management                            │
│  - Domain events emission                            │
│  - Cross-service calls (same or other modules)       │
└──────────────────┬───────────────────────────────────┘
                   │ (Depends↓)
┌──────────────────▼───────────────────────────────────┐
│              Repository Layer (Optional)             │
│  - Database queries (asyncpg)                        │
│  - Query building and execution                      │
│  - Result mapping to domain models                   │
└──────────────────┬───────────────────────────────────┘
                   │ (Depends↓)
┌──────────────────▼───────────────────────────────────┐
│                Database (PostgreSQL)                 │
│  - Schema, tables, indexes                           │
│  - RLS policies (multi-tenancy)                      │
│  - EXCLUSION constraints (conflict prevention)       │
└──────────────────────────────────────────────────────┘
```

**Key Principles**:
- **Top-down dependency** - Higher layers depend on lower layers, never reverse
- **No layer skipping** - API cannot call Repository directly (must go through Service)
- **Thin API layer** - Minimal logic, just routing and validation

---

## Integration Points

### Current: Synchronous Service Calls

**Pattern** (Phase 21):
```python
# distribution module calls core_pms
from app.modules.core_pms.services import PropertyService

class ChannelSyncService:
    def __init__(self, property_service: PropertyService):
        self.property_service = property_service

    async def sync_listing(self, property_id: UUID):
        # Cross-module call
        property = await self.property_service.get_property(property_id)
        # ... sync logic
```

**Limitations**:
- Tight coupling (distribution must import core_pms)
- No async processing
- Difficult to trace cross-module calls

---

### Future: Event-Driven Communication

**Pattern** (Phase 22+):
```python
# core_pms emits event
from app.events import emit_event

class BookingService:
    async def create_booking(self, data):
        booking = await self._create_booking_record(data)

        # Emit event (decoupled)
        await emit_event(
            "booking.created",
            {"booking_id": booking.id, "property_id": booking.property_id}
        )

        return booking

# distribution listens to event
from app.events import on_event

@on_event("booking.created")
async def sync_booking_to_channels(payload):
    # Async handler (Celery task)
    await channel_sync_service.sync_booking(payload["booking_id"])
```

**Benefits**:
- Loose coupling (modules don't import each other)
- Async processing (Celery/Redis queue)
- Easier testing (mock event bus)
- Traceable (event log in database)

---

### Shared Database with Schema Isolation

**Current Approach**:
- **Single PostgreSQL database**
- **Table prefixes** for module isolation (optional): `core_`, `dist_`, `finance_`
- **RLS policies** for multi-tenancy (agency-based)
- **Shared tables** for cross-cutting concerns: `agencies`, `team_members`, `profiles`

**Migration Strategy**:
- **Supabase migrations** (`supabase/migrations/`)
- **Per-module migration paths** (optional metadata in `ModuleSpec`)
- **Alembic** for local dev (optional)

**Advantages**:
- ACID transactions across modules
- No distributed transaction complexity
- Foreign key constraints work

**Disadvantages**:
- Tighter coupling at data layer
- Cannot independently scale database per module

---

## Naming & Folder Layout Conventions

### Module Folder Structure

**Standard Layout** (`app/modules/{module_name}/`):
```
app/modules/{module_name}/
├── __init__.py                # Module exports
├── module.py                  # ModuleSpec definition
├── api/                       # HTTP routes
│   ├── __init__.py
│   ├── routes.py             # FastAPI routers
│   └── deps.py               # Module-specific dependencies
├── services/                  # Business logic
│   ├── __init__.py
│   └── {domain}_service.py
├── schemas/                   # Pydantic models
│   ├── __init__.py
│   ├── requests.py           # API request models
│   └── responses.py          # API response models
├── repositories/              # Data access (optional)
│   ├── __init__.py
│   └── {domain}_repository.py
├── events/                    # Event handlers (optional)
│   ├── __init__.py
│   ├── emitters.py           # Event emission
│   └── handlers.py           # Event consumers
├── tests/                     # Module-specific tests
│   ├── test_services.py
│   ├── test_routes.py
│   └── test_repositories.py
└── README.md                  # Module documentation
```

**Example** (`app/modules/core_pms/`):
```
app/modules/core_pms/
├── __init__.py
├── module.py                  # CORE_PMS_SPEC
├── api/
│   ├── routes.py             # properties, bookings, availability
│   └── deps.py               # get_property_service, get_booking_service
├── services/
│   ├── property_service.py
│   ├── booking_service.py
│   └── availability_service.py
├── schemas/
│   ├── properties.py
│   ├── bookings.py
│   └── availability.py
└── README.md
```

---

### Naming Conventions

**Modules**:
- Snake_case: `core_pms`, `direct_booking`, `guest_experience`
- Descriptive, not abbreviated: `distribution` not `dist`

**Services**:
- Suffix with `Service`: `PropertyService`, `BookingService`
- Verb-noun methods: `create_booking`, `update_property`, `query_availability`

**Schemas** (Pydantic):
- Suffix with intent: `PropertyCreate`, `PropertyResponse`, `PropertyUpdate`
- Avoid generic names: `PropertyData` → `PropertyCreate`

**Routes** (FastAPI):
- Plural nouns: `/properties`, `/bookings`, `/listings`
- Action verbs for non-CRUD: `/bookings/{id}/cancel`, `/channels/sync`

**Database Tables**:
- Plural nouns: `properties`, `bookings`, `guests`
- Snake_case: `availability_blocks`, `channel_connections`

---

## Configuration & Settings

### Module-Specific Settings

**Pattern** (per module):
```python
# app/modules/distribution/config.py
from pydantic_settings import BaseSettings

class DistributionSettings(BaseSettings):
    channel_sync_interval_minutes: int = 15
    max_retry_attempts: int = 3
    webhook_secret: str

    class Config:
        env_prefix = "DIST_"
```

**Global Settings** (`app/core/config.py`):
- Database URL
- Redis URL
- JWT secrets
- CORS origins

**Module Registration**:
```python
# app/modules/distribution/module.py
from .config import DistributionSettings

DISTRIBUTION_SPEC = ModuleSpec(
    name="distribution",
    routers=[...],
    settings_class=DistributionSettings  # Optional hook
)
```

---

### Migrations Per Module

**Optional Metadata** (for future migration isolation):
```python
CORE_PMS_SPEC = ModuleSpec(
    name="core_pms",
    routers=[...],
    migrations_path="supabase/migrations/core_pms/"  # Optional
)
```

**Current Approach** (Phase 21):
- All migrations in `supabase/migrations/` (global)
- No per-module isolation yet

---

## Feature Flags (Optional)

**Pattern** (future):
```python
# app/core/config.py
class Settings(BaseSettings):
    enable_distribution_module: bool = True
    enable_direct_booking_module: bool = False
    enable_finance_module: bool = False
```

**ModuleSpec**:
```python
DISTRIBUTION_SPEC = ModuleSpec(
    name="distribution",
    routers=[...],
    enabled=lambda settings: settings.enable_distribution_module
)
```

**Use Case**:
- Gradual rollout (enable module per agency)
- A/B testing
- Feature parity with competitors

---

## Guardrails Against Debugging Nightmares

### 1. Import Validation

**Rule**: Modules CANNOT import from sibling modules (only from `core`, `shared`, or declared dependencies)

**Enforcement** (future):
```python
# tests/test_module_imports.py
def test_no_circular_imports():
    """Ensure no module imports its dependents"""
    for module in registry.get_all():
        for dep in module.depends_on:
            assert dep not in get_dependents(module.name)
```

---

### 2. Topological Sort

**Rule**: Module dependencies MUST form a DAG (Directed Acyclic Graph)

**Enforcement** (`app/modules/registry.py`):
```python
def validate(self) -> None:
    """Validate no circular dependencies via topological sort"""
    try:
        sorted_modules = topological_sort(self._modules)
    except ValueError as e:
        raise CircularDependencyError(f"Circular dependency detected: {e}")
```

---

### 3. API → Service Boundary

**Rule**: API routers CANNOT contain business logic or direct SQL queries

**Enforcement**:
- Code review checklist
- Linter rule (custom ruff plugin)
- Example:
  ```python
  # BAD (business logic in router)
  @router.post("/bookings")
  async def create_booking(data: BookingCreate, pool = Depends(get_pool)):
      # Direct SQL query - FORBIDDEN
      async with pool.acquire() as conn:
          result = await conn.fetchrow("INSERT INTO bookings ...")
      return result

  # GOOD (delegate to service)
  @router.post("/bookings")
  async def create_booking(
      data: BookingCreate,
      service: BookingService = Depends(get_booking_service)
  ):
      return await service.create_booking(data)
  ```

---

### 4. Shared Code Minimization

**Rule**: `/app/shared` MUST remain minimal and logic-free

**Allowed** in shared:
- Logging utilities (`logger.py`)
- Metrics wrappers (`metrics.py`)
- Encryption helpers (`crypto.py`)
- Generic validators (`validators.py`)

**Forbidden** in shared:
- Business logic
- Domain models
- Database queries
- API routes

---

## Testing Strategy

### Module-Level Tests

Each module MUST have:
1. **Unit tests** - Services, repositories (mocked dependencies)
2. **Integration tests** - API routes (real database, test fixtures)
3. **Contract tests** - Cross-module interfaces (if using events)

**Test Isolation**:
```python
# tests/modules/core_pms/test_booking_service.py
@pytest.fixture
def booking_service(mock_pool):
    return BookingService(pool=mock_pool)

def test_create_booking(booking_service):
    # Isolated unit test (no database)
    booking = await booking_service.create_booking(data)
    assert booking.status == "confirmed"
```

---

### Cross-Module Tests

**Integration tests** for cross-module workflows:
```python
# tests/integration/test_channel_booking_sync.py
async def test_airbnb_booking_syncs_to_core():
    # 1. Create channel booking (distribution module)
    channel_booking = await channel_service.import_booking(airbnb_data)

    # 2. Verify booking exists in core PMS (cross-module check)
    booking = await booking_service.get_booking(channel_booking.booking_id)
    assert booking.source == "airbnb"
```

---

## References

- **Product Model**: `docs/product/reference-product-model.md`
- **Phase 21 Plan**: `docs/architecture/phase21-modularization-plan.md`
- **System Architecture**: `docs/architecture/system-architecture.md`
- **Channel Manager**: `backend/app/channel_manager/README.md`
