# Extra Services (Zusatzleistungen) Admin UI

This runbook chapter covers the Extra Services feature in the Admin UI.

**When to use:** Managing optional add-on services for properties, understanding billing units, troubleshooting assignment issues.

## Overview

The Extra Services feature allows agencies to:

1. **Create a catalog** — Define agency-wide extra services (e.g., pets, breakfast, parking)
2. **Assign to properties** — Enable services per property with optional price/billing overrides
3. **Quote integration** — Services can be included in pricing quotes (API ready)

**Access:** Admin role required.

## Navigation / Wo finde ich das?

| Menüpunkt | Pfad | Beschreibung |
|-----------|------|--------------|
| Einstellungen → Zusatzleistungen | `/settings/extra-services` | Katalog verwalten |
| Objekte → [Objekt] → Zusatzleistungen | `/properties/[id]` (Tab) | Zuweisungen verwalten |

## Billing Units (Abrechnungsmodelle)

| Unit | German | Formula |
|------|--------|---------|
| `per_night` | Pro Nacht | price × nights × quantity |
| `per_stay` | Pro Aufenthalt | price × quantity |
| `per_person_per_night` | Pro Person/Nacht | price × nights × guests × quantity |
| `per_person_per_stay` | Pro Person/Aufenthalt | price × guests × quantity |
| `per_unit` | Pro Einheit | price × quantity |

**Examples:**

- **Pet fee** (`per_night`): 15€/night × 3 nights = 45€
- **Cleaning fee** (`per_stay`): 50€ × 1 = 50€
- **Breakfast** (`per_person_per_night`): 10€ × 2 guests × 3 nights = 60€
- **Airport transfer** (`per_unit`): 40€ × 2 = 80€

## Features

### Catalog Management (Settings)

**UI Location:** Einstellungen → Zusatzleistungen

**Capabilities:**
- Create/edit/delete extra services
- Set default price and billing unit
- Activate/deactivate services
- Sort order for display

**Fields:**
| Field | Required | Description |
|-------|----------|-------------|
| Name | Yes | Service name (e.g., "Haustier") |
| Beschreibung | No | Optional description |
| Abrechnungsmodell | Yes | How service is billed |
| Standardpreis | Yes | Default price in cents |
| Aktiv | Yes | Whether service is available |

### Property Assignments

**UI Location:** Objekte → [Objekt] → Zusatzleistungen (Tab)

**Assignment Options:**
| Field | Description |
|-------|-------------|
| is_enabled | Whether assignment is active |
| included_by_default | Auto-include in quotes |
| price_override_cents | Override default price |
| billing_unit_override | Override billing unit |
| max_quantity | Limit selectable quantity |

## API Endpoints

### Catalog (Agency-wide)

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| List services | `/api/v1/pricing/extra-services` | GET | auth |
| Create service | `/api/v1/pricing/extra-services` | POST | auth |
| Update service | `/api/v1/pricing/extra-services/{id}` | PATCH | auth |
| Delete service | `/api/v1/pricing/extra-services/{id}` | DELETE | auth |

### Property Assignments

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| List assignments | `/api/v1/properties/{id}/extra-services` | GET | auth |
| Assign service | `/api/v1/properties/{id}/extra-services` | POST | auth |
| Update assignment | `/api/v1/properties/{id}/extra-services/{aid}` | PATCH | auth |
| Remove assignment | `/api/v1/properties/{id}/extra-services/{aid}` | DELETE | auth |

## Verification (PROD)

### Deploy Verification

```bash
# HOST-SERVER-TERMINAL
source /root/.pms_env
export API_BASE_URL="https://api.fewo.kolibri-visions.de"

# 1. Verify deploy (replace <sha> with expected commit)
EXPECT_COMMIT=<sha> ./backend/scripts/pms_verify_deploy.sh

# 2. Get JWT token
export JWT_TOKEN="$(curl -k -sS -X POST "${SB_URL}/auth/v1/token?grant_type=password" \
  -H "apikey: ${SB_ANON_KEY}" \
  -H "Content-Type: application/json" \
  --data-binary "$(jq -nc --arg e "$SB_EMAIL" --arg p "$SB_PASSWORD" '{email:$e,password:$p}')" \
  | jq -r '.access_token // empty')"

# 3. Get property ID for testing
export PROPERTY_ID="$(curl -k -sS \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "x-agency-id: ${AGENCY_ID}" \
  "${API_BASE_URL}/api/v1/properties?limit=1" \
  | jq -r '.items[0].id // empty')"

# 4. Run smoke test
JWT_TOKEN="${JWT_TOKEN}" AGENCY_ID="${AGENCY_ID}" PROPERTY_ID="${PROPERTY_ID}" \
  ./backend/scripts/pms_extra_services_smoke.sh

echo "extra_services_rc=$?"
```

### DB Table Verification

```sql
-- Check tables exist
SELECT to_regclass('public.extra_services'), to_regclass('public.property_extra_services');
-- Expected: NOT NULL for both

-- Check trigger function exists
SELECT proname FROM pg_proc WHERE proname = 'set_updated_at';
-- Expected: set_updated_at
```

## Troubleshooting

### Migration Fails: set_updated_at Missing

**Symptom:** Migration fails with `function public.set_updated_at() does not exist`.

**Cause:** The `set_updated_at()` trigger function is not defined in the database.

**Resolution:**
1. Apply the prelude migration first:
   ```sql
   -- In Supabase SQL Editor, run:
   CREATE OR REPLACE FUNCTION public.set_updated_at()
   RETURNS trigger
   LANGUAGE plpgsql
   AS $$
   BEGIN
       NEW.updated_at = now();
       RETURN NEW;
   END;
   $$;

   GRANT EXECUTE ON FUNCTION public.set_updated_at() TO authenticated;
   GRANT EXECUTE ON FUNCTION public.set_updated_at() TO service_role;
   ```
2. Then apply the extra_services migration

### 404 Not Found (Route Prefix Mismatch)

**Symptom:** API returns 404 for `/api/v1/pricing/extra-services` endpoints.

**Cause:** The extra_services module is not registered in the module system.

**Resolution:**
1. Verify `backend/app/modules/extra_services.py` exists
2. Verify `bootstrap.py` imports the extra_services module
3. Check logs for "Extra Services module not available" warning
4. Redeploy backend

### 503 Schema Drift (Tables Missing)

**Symptom:** API returns 500/503 when accessing extra services endpoints.

**Cause:** Database migrations not applied.

**Resolution:**
1. Check if tables exist:
   ```sql
   SELECT to_regclass('public.extra_services');
   ```
2. If NULL, apply migrations in order:
   - `20260202115000_add_set_updated_at_function.sql`
   - `20260202120000_add_extra_services.sql`

### 401 Unauthorized

**Symptom:** API returns 401 when accessing endpoints.

**Cause:** Session expired or not logged in.

**Resolution:**
1. Refresh page (triggers re-auth)
2. Log out and log in again
3. Check Supabase session

### 404 Property/Service Not Found

**Symptom:** "Property not found" or "Extra service not found" error.

**Cause:** Property/service doesn't belong to current agency.

**Resolution:**
1. Verify you're in correct agency context
2. Check if property/service ID is correct
3. Check if service was deleted

### 409 Already Assigned

**Symptom:** "Service already assigned to this property" error.

**Cause:** Attempting to assign same service twice.

**Resolution:**
1. Check existing assignments
2. Update existing assignment instead of creating new

### Service Not Showing in Property

**Symptom:** Created service not appearing in property assignment picker.

**Cause:** Service is inactive.

**Resolution:**
1. Go to Settings → Zusatzleistungen
2. Activate the service (toggle)
3. Refresh property page

## Internal API Proxy

The Admin UI uses internal API proxy routes:

| UI Request | Internal Proxy | Backend Endpoint |
|------------|----------------|------------------|
| GET catalog | `/api/internal/extra-services` | `GET /api/v1/pricing/extra-services` |
| POST catalog | `/api/internal/extra-services` | `POST /api/v1/pricing/extra-services` |
| GET property | `/api/internal/properties/{id}/extra-services` | `GET /api/v1/properties/{id}/extra-services` |

## Smoke Test

**Script:** `backend/scripts/pms_extra_services_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage (requires JWT_TOKEN and PROPERTY_ID)
JWT_TOKEN="eyJhbG..." PROPERTY_ID="uuid..." ./backend/scripts/pms_extra_services_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="..." PROPERTY_ID="..." ./backend/scripts/pms_extra_services_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT (admin/manager) |
| `PROPERTY_ID` | Yes | - | Property UUID to test with |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |

### What It Tests

1. **Health check:** GET /health → HTTP 200
2. **Preflight routes:** Verify extra-services paths exist in OpenAPI
3. **Create service:** POST /api/v1/pricing/extra-services → HTTP 201
4. **List services:** GET /api/v1/pricing/extra-services → HTTP 200
5. **Assign to property:** POST /api/v1/properties/{id}/extra-services → HTTP 201
6. **List property services:** GET /api/v1/properties/{id}/extra-services → HTTP 200
7. **Cleanup:** Deletes created test data

### Expected Result

```
RESULT: PASS
Summary: PASS=6, FAIL=0, SKIP=0
```

## Database Tables

### extra_services (Catalog)

```sql
CREATE TABLE extra_services (
    id uuid PRIMARY KEY,
    agency_id uuid NOT NULL,
    name text NOT NULL,
    description text,
    billing_unit text NOT NULL,
    default_price_cents integer NOT NULL,
    currency_code text NOT NULL DEFAULT 'EUR',
    is_active boolean NOT NULL DEFAULT true,
    sort_order integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
```

### property_extra_services (Assignments)

```sql
CREATE TABLE property_extra_services (
    id uuid PRIMARY KEY,
    property_id uuid NOT NULL,
    service_id uuid NOT NULL,
    is_enabled boolean NOT NULL DEFAULT true,
    included_by_default boolean NOT NULL DEFAULT false,
    price_override_cents integer,
    billing_unit_override text,
    max_quantity integer,
    sort_order integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(property_id, service_id)
);
```

## Related Documentation

- [Pricing API](../../api/pricing.md) — Rate plans and quotes
- [Properties API](../../api/properties.md) — Property management
