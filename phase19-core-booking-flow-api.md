# Phase 19: Core Booking Flow API

**Version:** 1.0
**Status:** FROZEN v1.0 (Implementation Complete)
**Erstellt:** 2025-12-23
**Implementation Completed:** 2025-12-23
**Projekt:** PMS-Webapp (B2B SaaS für Ferienwohnungs-Agenturen)
**Basis:** Phase 17B (Schema FROZEN) + Phase 18A (Migrations FROZEN)

---

## Executive Summary

### Ziel

Implementierung der ersten Business-APIs für Properties und Bookings als stabile MVP-Basis. Fokus auf RBAC-Integration, Validierung, Fehlerhandling und automatisierte Tests. Diese Phase legt das Fundament für spätere Features (Channel Manager, Direct Booking Widget, Frontend).

### Scope

**IN SCOPE (Phase 19):**
- ✅ Properties CRUD API (GET, POST, PATCH, DELETE)
- ✅ Bookings CRUD API (GET, POST, PATCH für Status-Transitions)
- ✅ RBAC Middleware (get_current_user, get_current_agency, Role Guards)
- ✅ Validation Layer (Pydantic Schemas)
- ✅ Error Handling (4xx/5xx mit Details)
- ✅ Integration Tests (pytest + TestClient)
- ✅ OpenAPI Documentation (/docs, /openapi.json)
- ✅ Database Connection Pool (asyncpg)
- ✅ Environment Configuration (.env.example, settings.py)

**OUT OF SCOPE (spätere Phasen):**
- ❌ Channel Manager Integration (iCal Import/Export)
- ❌ Payment Processing (Stripe/PayPal)
- ❌ Direct Booking Widget (Frontend)
- ❌ Email Notifications
- ❌ PDF Generation (Invoices, Statements)
- ❌ File Upload (Property Photos)
- ❌ Advanced Filters (Fuzzy Search, Geospatial)

### Key Deliverables

1. Backend API Endpoints (10-15 Endpoints)
2. RBAC Dependencies & Permission Guards
3. Pydantic Schemas (20+ models)
4. Integration Tests (30+ tests)
5. OpenAPI Documentation
6. Environment Configuration
7. Phase 19 FROZEN Documentation

---

## 1. Database Tables Mapping

### 1.1 Tables Used in Phase 19

Phase 19 nutzt diese Tabellen aus **Phase 17B (FROZEN)**:

| Tabelle | Zweck | API Endpoints |
|---------|-------|---------------|
| `agencies` | Multi-Tenant Root | Implizit via Agency Context |
| `profiles` | User Profile | Implizit via JWT claims |
| `team_members` | User-Agency-Role Mapping | RBAC Permission Checks |
| `properties` | Objekte (Ferienwohnungen) | GET, POST, PATCH, DELETE /properties |
| `bookings` | Buchungen (Source of Truth) | GET, POST, PATCH /bookings |
| `guests` | Gäste | Implizit via bookings.guest_id |
| `direct_bookings` | Direct Booking Details | POST /bookings (wenn source=direct) |

### 1.2 Tables NOT Used (deferred)

| Tabelle | Grund | Phase |
|---------|-------|-------|
| `channel_connections` | Channel Manager | Phase 20+ |
| `external_bookings` | iCal Import | Phase 20+ |
| `invoices`, `payments` | Payment Processing | Phase 21+ |
| `property_photos` | File Upload | Phase 22+ |
| `amenities`, `property_amenities` | Advanced Filtering | Phase 19.1+ |

**Wichtig:** Phase 19 darf KEINE Schema-Änderungen an diesen Tabellen vornehmen (FROZEN).

---

## 2. API Endpoints

### 2.1 Properties API

**Base Path:** `/api/v1/properties`

#### 2.1.1 List Properties

```
GET /api/v1/properties
```

**Query Parameters:**
- `limit` (int, default: 50, max: 100)
- `offset` (int, default: 0)
- `is_active` (bool, optional) - Filter nur aktive Properties
- `owner_id` (UUID, optional) - Filter by owner (nur für admin/manager)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "agency_id": "uuid",
      "owner_id": "uuid | null",
      "name": "Alpenchalet Zugspitze",
      "internal_name": "ALX-001",
      "description": "...",
      "property_type": "chalet",
      "bedrooms": 3,
      "beds": 5,
      "bathrooms": 2.0,
      "max_guests": 6,
      "address_line1": "Bergstraße 42",
      "city": "Garmisch-Partenkirchen",
      "postal_code": "82467",
      "country": "DE",
      "base_price": 150.00,
      "currency": "EUR",
      "is_active": true,
      "created_at": "2025-01-01T10:00:00Z",
      "updated_at": "2025-01-01T10:00:00Z"
    }
  ],
  "total": 3,
  "limit": 50,
  "offset": 0
}
```

**RBAC:**
- **admin, manager:** Full access (alle Properties der Agency)
- **staff:** READ-ONLY (alle Properties der Agency)
- **owner:** READ-ONLY (nur eigene Properties via owner_id)
- **accountant:** 403 Forbidden

**RLS:** PostgreSQL RLS filtert automatisch nach `agency_id` und `owner_id`.

#### 2.1.2 Get Property

```
GET /api/v1/properties/{property_id}
```

**Response:** Single Property Object (siehe 2.1.1)

**RBAC:** Wie 2.1.1

#### 2.1.3 Create Property

```
POST /api/v1/properties
```

**Request Body:**
```json
{
  "name": "Neue Property",
  "internal_name": "MUC-002",
  "description": "...",
  "property_type": "apartment",
  "bedrooms": 2,
  "beds": 3,
  "bathrooms": 1.0,
  "max_guests": 4,
  "address_line1": "Hauptstraße 1",
  "city": "München",
  "postal_code": "80331",
  "country": "DE",
  "base_price": 120.00,
  "currency": "EUR",
  "owner_id": "uuid (optional)"
}
```

**Response:** 201 Created + Property Object

**RBAC:**
- **admin, manager:** Allowed
- **staff, owner, accountant:** 403 Forbidden

**Validation:**
- `name` required, max 255 chars
- `property_type` must be in enum
- `bedrooms, beds, bathrooms, max_guests` must be > 0
- `base_price` must be >= 0
- `owner_id` must exist in auth.users (if provided)

#### 2.1.4 Update Property

```
PATCH /api/v1/properties/{property_id}
```

**Request Body:** Partial Property Object (wie 2.1.3, alle Felder optional)

**Response:** 200 OK + Updated Property Object

**RBAC:**
- **admin, manager:** Allowed
- **staff, owner, accountant:** 403 Forbidden

**Validation:** Wie 2.1.3 (für provided fields)

#### 2.1.5 Delete Property (Soft Delete)

```
DELETE /api/v1/properties/{property_id}
```

**Response:** 204 No Content

**RBAC:**
- **admin:** Allowed
- **manager, staff, owner, accountant:** 403 Forbidden

**Implementation:** Set `deleted_at = now()` (Soft Delete)

---

### 2.2 Bookings API

**Base Path:** `/api/v1/bookings`

#### 2.2.1 List Bookings

```
GET /api/v1/bookings
```

**Query Parameters:**
- `limit` (int, default: 50, max: 100)
- `offset` (int, default: 0)
- `status` (string, optional) - Filter by status
- `property_id` (UUID, optional) - Filter by property
- `check_in_from` (date, optional) - Filter check_in >= date
- `check_in_to` (date, optional) - Filter check_in <= date

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "agency_id": "uuid",
      "property_id": "uuid",
      "guest_id": "uuid",
      "booking_reference": "PMS-2025-000001",
      "check_in": "2025-02-14",
      "check_out": "2025-02-21",
      "num_adults": 2,
      "num_children": 2,
      "num_guests": 4,
      "num_nights": 7,
      "source": "direct",
      "status": "confirmed",
      "nightly_rate": 150.00,
      "subtotal": 1050.00,
      "cleaning_fee": 80.00,
      "total_price": 1130.00,
      "currency": "EUR",
      "payment_status": "paid",
      "confirmed_at": "2025-01-15T10:00:00Z",
      "created_at": "2025-01-15T09:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 4,
  "limit": 50,
  "offset": 0
}
```

**RBAC:**
- **admin, manager:** Full access (alle Bookings der Agency)
- **staff:** READ-ONLY (alle Bookings der Agency)
- **owner:** READ-ONLY (nur Bookings für eigene Properties)
- **accountant:** READ-ONLY (alle Bookings der Agency)

**RLS:** PostgreSQL RLS filtert automatisch nach `agency_id` und `owner_id` (via property join).

#### 2.2.2 Get Booking

```
GET /api/v1/bookings/{booking_id}
```

**Response:** Single Booking Object (siehe 2.2.1) + expanded guest info

**RBAC:** Wie 2.2.1

#### 2.2.3 Create Booking

```
POST /api/v1/bookings
```

**Request Body:**
```json
{
  "property_id": "uuid",
  "guest": {
    "first_name": "Julia",
    "last_name": "Becker",
    "email": "julia.becker@example.com",
    "phone": "+49 172 1234567"
  },
  "check_in": "2025-03-01",
  "check_out": "2025-03-05",
  "num_adults": 2,
  "num_children": 0,
  "source": "direct",
  "status": "pending",
  "nightly_rate": 120.00,
  "subtotal": 480.00,
  "cleaning_fee": 60.00,
  "total_price": 540.00,
  "currency": "EUR"
}
```

**Response:** 201 Created + Booking Object

**RBAC:**
- **admin, manager, staff:** Allowed
- **owner, accountant:** 403 Forbidden

**Validation:**
- `property_id` must exist and belong to agency
- `check_in < check_out`
- `num_adults > 0`
- `num_guests <= property.max_guests`
- No double-booking (DB Exclusion Constraint will enforce)
- Guest: email valid, phone valid

**Implementation:**
1. Create or find guest (upsert by email)
2. Insert booking with generated `booking_reference` (e.g., "PMS-2025-{seq}")
3. If `source == 'direct'`: insert into `direct_bookings`

#### 2.2.4 Update Booking Status

```
PATCH /api/v1/bookings/{booking_id}/status
```

**Request Body:**
```json
{
  "status": "confirmed",
  "notes": "Optional internal notes"
}
```

**Response:** 200 OK + Updated Booking Object

**RBAC:**
- **admin, manager:** Allowed (all status transitions)
- **staff:** Allowed (limited: pending → confirmed, confirmed → checked_in)
- **owner, accountant:** 403 Forbidden

**Status Workflow:**
```
inquiry → pending → confirmed → checked_in → checked_out
                                     ↓
                                 cancelled
                                     ↓
                                 declined / no_show
```

**Validation:**
- Only allowed transitions (implement state machine)
- Set timestamp fields (`confirmed_at`, `check_in_at`, etc.)

#### 2.2.5 Cancel Booking

```
POST /api/v1/bookings/{booking_id}/cancel
```

**Request Body:**
```json
{
  "cancelled_by": "guest",
  "cancellation_reason": "Reisepläne geändert",
  "refund_amount": 415.00
}
```

**Response:** 200 OK + Updated Booking Object

**RBAC:**
- **admin, manager:** Allowed
- **staff, owner, accountant:** 403 Forbidden

**Implementation:**
- Set `status = 'cancelled'`
- Set `cancelled_at = now()`
- Set `cancelled_by`, `cancellation_reason`, `refund_amount`

---

## 3. RBAC & RLS Zusammenspiel

### 3.1 RLS (Database Layer)

**Was macht RLS?**
- Multi-Tenancy Isolation: User sieht nur Daten ihrer Agency (`agency_id`)
- Owner Isolation: Owner sieht nur eigene Properties (`owner_id`)
- Role-Based Row Filtering (definiert in Phase 17B/18A)

**Beispiel RLS Policy (Properties für Owner):**
```sql
CREATE POLICY "owner_select_own_properties" ON properties
  FOR SELECT TO authenticated
  USING (
    owner_id = auth.uid()
    AND EXISTS (
      SELECT 1 FROM team_members tm
      WHERE tm.user_id = auth.uid()
        AND tm.agency_id = properties.agency_id
        AND tm.role = 'owner'
        AND tm.is_active = true
    )
  );
```

### 3.2 API-Level RBAC (FastAPI Layer)

**Was macht API RBAC zusätzlich?**
- **Early Rejection:** 403 Forbidden BEVOR Datenbank-Query
- **Operation-Level Control:** z.B. "Staff darf READ-ONLY"
- **Klare Fehlermeldungen:** "You need 'admin' or 'manager' role to create properties"

**Implementation:**
```python
# Dependencies: app/api/deps.py
async def get_current_user(token: str) -> User:
    # JWT validation, extract user_id
    # Return User object from auth.users + profiles

async def get_current_agency_id(user: User) -> UUID:
    # Extract agency_id from JWT claims OR last_active_agency_id
    # Return agency_id

async def get_current_role(user: User, agency_id: UUID) -> str:
    # Query team_members: role where user_id + agency_id + is_active
    # Return role (admin, manager, staff, owner, accountant)

def require_roles(*allowed_roles: str):
    # Dependency that checks if current_role in allowed_roles
    # Raises 403 if not allowed
```

**Usage in Endpoint:**
```python
@router.post("/properties", dependencies=[Depends(require_roles("admin", "manager"))])
async def create_property(
    property_data: PropertyCreate,
    user: User = Depends(get_current_user),
    agency_id: UUID = Depends(get_current_agency_id),
    db: Connection = Depends(get_db)
):
    # Create property with agency_id
    # RLS ensures user can only create in their agency
    ...
```

### 3.3 Zusammenspiel

| Layer | Zweck | Beispiel |
|-------|-------|----------|
| **RLS (DB)** | Data Isolation | Owner sieht nur eigene Properties (Row Filtering) |
| **API RBAC** | Operation Control | Staff darf keine Properties erstellen (403) |

**Wichtig:** Beide Layer sind komplementär, nicht redundant!

---

## 4. Status Workflow (Bookings)

### 4.1 Status Enum

Definiert in Phase 17B Schema:
```sql
status IN ('inquiry', 'pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled', 'declined', 'no_show')
```

### 4.2 State Machine

```
inquiry
  ↓
pending ←──────────┐
  ↓                │
confirmed          │
  ↓                │
checked_in         │
  ↓                │
checked_out        │
                   │
  ↓──── cancelled ─┘
  ↓──── declined
  ↓──── no_show
```

**Transitions Allowed:**
- `inquiry → pending`
- `pending → confirmed`
- `pending → declined`
- `confirmed → checked_in`
- `confirmed → cancelled`
- `checked_in → checked_out`
- `checked_in → no_show`
- `any → cancelled` (admin only)

### 4.3 Timestamps

| Status | Timestamp Field |
|--------|----------------|
| `inquiry` | `inquiry_at` |
| `confirmed` | `confirmed_at` |
| `checked_in` | `check_in_at` |
| `checked_out` | `check_out_at` |
| `cancelled` | `cancelled_at` |

### 4.4 Implementation

```python
# app/services/bookings.py

ALLOWED_TRANSITIONS = {
    "inquiry": ["pending", "declined"],
    "pending": ["confirmed", "declined", "cancelled"],
    "confirmed": ["checked_in", "cancelled"],
    "checked_in": ["checked_out", "no_show"],
}

def validate_status_transition(current_status: str, new_status: str, role: str) -> bool:
    # Check if transition allowed
    if new_status not in ALLOWED_TRANSITIONS.get(current_status, []):
        return False

    # Role-specific restrictions
    if role == "staff" and new_status == "cancelled":
        return False  # Only admin/manager can cancel

    return True
```

---

## 5. Validation & Error Handling

### 5.1 Pydantic Schemas

**Example: PropertyCreate**
```python
# app/schemas/properties.py

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from decimal import Decimal
from uuid import UUID

class PropertyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    internal_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    property_type: Literal["apartment", "house", "villa", "condo", "room", "studio", "cabin", "cottage", "chalet"]
    bedrooms: int = Field(..., ge=0)
    beds: int = Field(..., ge=1)
    bathrooms: Decimal = Field(..., ge=0)
    max_guests: int = Field(..., ge=1)
    address_line1: str = Field(..., max_length=255)
    city: str = Field(..., max_length=100)
    postal_code: str = Field(..., max_length=20)
    country: str = Field(default="DE", max_length=2)
    base_price: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="EUR", max_length=3)
    owner_id: Optional[UUID] = None

    @field_validator("bedrooms", "beds", "max_guests")
    @classmethod
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError("Must be positive")
        return v
```

### 5.2 HTTP Status Codes

| Code | Verwendung | Beispiel |
|------|------------|----------|
| **200 OK** | Successful GET, PATCH | Property updated |
| **201 Created** | Successful POST | Booking created |
| **204 No Content** | Successful DELETE | Property deleted |
| **400 Bad Request** | Invalid request body | Missing required field |
| **401 Unauthorized** | Missing/invalid JWT | Authorization header missing |
| **403 Forbidden** | Insufficient permissions | Staff cannot delete properties |
| **404 Not Found** | Resource not found | Property ID does not exist |
| **422 Unprocessable Entity** | Pydantic validation error | Invalid email format |
| **409 Conflict** | Business rule violation | Double-booking detected |
| **500 Internal Server Error** | Unexpected error | Database connection failed |

### 5.3 Error Response Format

```json
{
  "detail": "Human-readable error message",
  "error_code": "INVALID_STATUS_TRANSITION",
  "field": "status",
  "value": "cancelled",
  "allowed_values": ["confirmed", "checked_in"]
}
```

**Example Errors:**
```json
// 403 Forbidden
{
  "detail": "You need 'admin' or 'manager' role to create properties",
  "error_code": "INSUFFICIENT_PERMISSIONS",
  "required_roles": ["admin", "manager"],
  "current_role": "staff"
}

// 409 Conflict (Double Booking)
{
  "detail": "Property is already booked for these dates",
  "error_code": "DOUBLE_BOOKING",
  "property_id": "uuid",
  "conflicting_booking_id": "uuid",
  "check_in": "2025-03-01",
  "check_out": "2025-03-05"
}

// 422 Validation Error
{
  "detail": [
    {
      "loc": ["body", "check_out"],
      "msg": "check_out must be after check_in",
      "type": "value_error"
    }
  ]
}
```

---

## 6. Testing Strategy

### 6.1 Integration Tests (pytest)

**Test Structure:**
```
backend/tests/
├── __init__.py
├── conftest.py           # Fixtures (TestClient, test_db, mock_auth)
├── integration/
│   ├── test_properties.py
│   ├── test_bookings.py
│   ├── test_rbac.py
│   └── test_multi_tenancy.py
```

### 6.2 Test Fixtures

```python
# tests/conftest.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_token():
    # Generate JWT for admin user (from seed data)
    return "Bearer eyJhbGciOiJIUzI1NiIs..."

@pytest.fixture
def owner_token():
    # Generate JWT for owner user
    return "Bearer eyJhbGciOiJIUzI1NiIs..."

@pytest.fixture
def db_session():
    # Return test database session
    # Use Supabase test instance OR mock
    ...
```

### 6.3 Test Cases

**Properties Tests (test_properties.py):**
1. `test_list_properties_as_admin()` - Admin sieht alle Properties der Agency
2. `test_list_properties_as_owner()` - Owner sieht nur eigene Properties
3. `test_create_property_as_admin()` - 201 Created
4. `test_create_property_as_staff()` - 403 Forbidden
5. `test_update_property_as_manager()` - 200 OK
6. `test_delete_property_as_admin()` - 204 No Content
7. `test_delete_property_as_manager()` - 403 Forbidden
8. `test_get_property_not_found()` - 404

**Bookings Tests (test_bookings.py):**
1. `test_list_bookings_as_admin()` - Alle Bookings der Agency
2. `test_list_bookings_as_owner()` - Nur Bookings für eigene Properties
3. `test_create_booking_as_staff()` - 201 Created
4. `test_create_booking_double_booking()` - 409 Conflict
5. `test_update_status_pending_to_confirmed()` - 200 OK
6. `test_update_status_invalid_transition()` - 400 Bad Request
7. `test_cancel_booking_as_admin()` - 200 OK
8. `test_cancel_booking_as_staff()` - 403 Forbidden

**RBAC Tests (test_rbac.py):**
1. `test_admin_full_access()`
2. `test_manager_cannot_delete_properties()`
3. `test_staff_read_only_properties()`
4. `test_owner_isolation()`
5. `test_accountant_no_properties_access()`

**Multi-Tenancy Tests (test_multi_tenancy.py):**
1. `test_agency_isolation()` - Agency 1 Admin sieht keine Agency 2 Daten
2. `test_cross_agency_property_access_forbidden()`
3. `test_cross_agency_booking_access_forbidden()`

### 6.4 Test Coverage Goal

- **Target:** >80% code coverage
- **Focus:** API endpoints, RBAC logic, validation
- **Deferred:** Database RLS (tested manually via SQL, siehe phase18a-preflight.md)

---

## 7. Environment Configuration

### 7.1 .env.example

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Supabase
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# JWT
JWT_SECRET=super-secret-jwt-token-with-at-least-32-characters-long
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# Health Checks (optional)
ENABLE_REDIS_HEALTHCHECK=false
ENABLE_CELERY_HEALTHCHECK=false

# Logging
LOG_LEVEL=INFO
```

### 7.2 settings.py

```python
# app/core/config.py

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False

    # Health Checks
    enable_redis_healthcheck: bool = False
    enable_celery_healthcheck: bool = False

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## 8. OpenAPI Documentation

### 8.1 FastAPI Automatic Docs

**Endpoints:**
- `/docs` - Swagger UI (interaktiv)
- `/redoc` - ReDoc (schön formatiert)
- `/openapi.json` - OpenAPI 3.1 Schema

### 8.2 Endpoint Descriptions

**Example:**
```python
@router.get(
    "/properties",
    response_model=PropertyListResponse,
    summary="List all properties",
    description="""
    Returns a paginated list of properties accessible to the current user.

    **RBAC:**
    - Admin/Manager: All properties in agency
    - Staff: All properties in agency (read-only)
    - Owner: Only own properties (where owner_id = user_id)
    - Accountant: Forbidden (403)

    **Filters:**
    - `is_active`: Filter by active status
    - `owner_id`: Filter by owner (admin/manager only)
    """,
    responses={
        200: {"description": "List of properties"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden (Accountant role)"},
    },
    tags=["properties"]
)
async def list_properties(...):
    ...
```

---

## 9. Known Limitations & Future Work

### 9.1 Limitations (Phase 19)

1. **No File Upload:** Property photos NOT implemented (Phase 22+)
2. **No Advanced Filters:** Fuzzy search, geospatial NOT implemented
3. **No Payment Processing:** Stripe/PayPal integration deferred (Phase 21+)
4. **No Email Notifications:** Booking confirmations deferred
5. **Simple Auth:** Basic JWT, no refresh tokens, no MFA
6. **No Rate Limiting:** API throttling deferred
7. **No Caching:** Redis integration deferred

### 9.2 Future Improvements

**Phase 19.1 (Quick Wins):**
- Add `amenities` filter to properties
- Add `pagination_cursor` for better performance
- Add `booking_reference` search

**Phase 20 (Channel Manager):**
- iCal Import/Export
- `channel_connections` API
- `external_bookings` sync

**Phase 21 (Payments):**
- Stripe Payment Intents
- `invoices` API
- `payments` API
- Refund handling

**Phase 22 (File Upload):**
- Property photos upload (Supabase Storage)
- `property_photos` API
- Image optimization

---

## 10. Rollback Plan

**If Phase 19 needs rollback:**

1. **Identify last good commit:**
   ```bash
   git log --oneline | grep "9f379f8"  # Last commit before Phase 19
   ```

2. **Revert Phase 19 commits:**
   ```bash
   git revert <first_phase19_commit>..HEAD --no-commit
   git commit -m "revert: rollback Phase 19"
   ```

3. **Reset database:** (Schema unverändert, kein Rollback nötig)
   ```bash
   supabase db reset  # Loads FROZEN 18A migrations
   ```

4. **Verify health:**
   ```bash
   curl http://localhost:8000/health/ready
   ```

**Recovery Time:** < 5 minutes (nur Backend Code, kein Schema Change)

---

## 11. Deliverables Checklist

- [ ] Backend API Struktur (`api/`, `schemas/`, `services/`)
- [ ] Auth Dependencies (`get_current_user`, `get_current_agency_id`, `get_current_role`)
- [ ] RBAC Guards (`require_roles`)
- [ ] Properties API (5 endpoints)
- [ ] Bookings API (5 endpoints)
- [ ] Pydantic Schemas (20+ models)
- [ ] Error Handling (custom exceptions + HTTP status codes)
- [ ] Integration Tests (30+ tests, >80% coverage)
- [ ] OpenAPI Documentation (descriptions, examples)
- [ ] Environment Configuration (.env.example, settings.py)
- [ ] Database Connection Pool (asyncpg)
- [ ] Phase 19 Documentation (this file)
- [ ] Phase 19 Preflight (filled out)
- [ ] Git Commits (logical, atomic)

---

## 12. Next Phase Proposal

**Phase 20: Channel Manager Integration**

Deliverables:
1. Channel Connections API (GET, POST, PUT, DELETE)
2. iCal Feed Import (Airbnb, Booking.com)
3. iCal Feed Export (für Channels)
4. External Bookings Sync
5. Booking Sync Log (Audit Trail)
6. Availability Calendar API
7. Conflict Detection & Resolution
8. Integration Tests (Channel Sync)
9. Documentation (Channel Manager Guide)
10. Error Handling (Sync failures)

**Basis:** Phase 19 (Core Booking Flow API FROZEN)

---

**Ende Phase 19 Planungsdoku**
