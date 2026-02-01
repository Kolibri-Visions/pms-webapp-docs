# Amenities Admin UI

This runbook chapter covers the Amenities management in the Admin UI.

**When to use:** Troubleshooting amenities toggle, CRUD operations, or category filtering.

## Overview

The Amenities page (`/amenities`) provides management for property features:

1. **List View**: Shows all amenities grouped by category
2. **Create/Edit**: Modal form for amenity CRUD
3. **Toggle Active**: Inline switch to enable/disable amenities
4. **Category Filter**: Filter amenities by category
5. **Search**: Search by name or description

## Common Issues

### PATCH /api/internal/amenities/:id Returns 400

**Symptom:** Toggling "aktiv/inaktiv" switch shows 400 error in DevTools.

**Cause (Fixed 2026-02-01):** The backend `AmenityUpdate` schema was missing `is_active` field.

**Resolution:**
1. Migration `20260201110000_add_amenities_is_active.sql` adds `is_active` column
2. Backend schema updated to accept `is_active` in PATCH requests
3. Service updated to handle `is_active` in dynamic UPDATE

**Verification:**
```bash
# Run smoke test
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_amenities_toggle_smoke.sh

# Expected: PASS=5, FAIL=0
```

### 503 Service Unavailable

**Symptom:** All amenities operations return 503.

**Cause:** Amenities table not found (migration not applied).

**Resolution:**
1. Apply migration via Supabase Studio SQL Editor:
   - Copy contents of `supabase/migrations/20260122000000_add_amenities.sql`
   - Execute in SQL Editor
2. Verify table exists:
   ```sql
   SELECT to_regclass('public.amenities');
   -- Expected: 'amenities' (not NULL)
   ```

### 403 Forbidden

**Symptom:** Create/Edit/Delete operations return 403.

**Cause:** User lacks admin/manager role.

**Resolution:**
1. Check user's role in `team_members` table
2. Ensure user has `admin` or `manager` role

## API Endpoints

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| List amenities | `/api/v1/amenities` | GET | all authenticated |
| Create amenity | `/api/v1/amenities` | POST | admin, manager |
| Get amenity | `/api/v1/amenities/{id}` | GET | all authenticated |
| Update amenity | `/api/v1/amenities/{id}` | PATCH | admin, manager |
| Delete amenity | `/api/v1/amenities/{id}` | DELETE | admin, manager |

### Toggle Active Example

```bash
# Toggle amenity inactive
curl -sS -X PATCH "$API/api/v1/amenities/$ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}' | jq .

# Response: { "id": "...", "is_active": false, ... }
```

## Smoke Test

**Location:** `backend/scripts/pms_amenities_toggle_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage (requires JWT_TOKEN)
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_amenities_toggle_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_amenities_toggle_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT with admin/manager role |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |

### What It Tests

1. GET /api/v1/amenities → List amenities
2. POST /api/v1/amenities → Create test amenity (if none exist)
3. PATCH /api/v1/amenities/{id} with `{is_active: false}` → Toggle off
4. GET /api/v1/amenities/{id} → Verify persisted state
5. PATCH /api/v1/amenities/{id} with `{is_active: true}` → Toggle back on

### Expected Result

```
RESULT: PASS
Summary: PASS=5, FAIL=0, SKIP=0
```

## Database Schema

```sql
-- amenities table
CREATE TABLE public.amenities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id uuid NOT NULL REFERENCES agencies(id),
  name varchar(255) NOT NULL,
  description text,
  category varchar(50),
  icon varchar(100),
  sort_order integer DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT amenities_unique_per_agency UNIQUE (agency_id, name)
);
```

## Related Documentation

- [Backend Amenities Routes](../../api/amenities.md) — API endpoint details
- [Scripts README](../../../scripts/README.md#pms_amenities_toggle_smokesh) — Smoke test documentation
