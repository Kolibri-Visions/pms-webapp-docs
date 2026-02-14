# 25. Website Pages Blocks 500 Error

**Date Added**: 2026-02-14

**Symptoms**:
- `GET /api/v1/website/pages` returns HTTP 500
- Backend log: `1 validation error for PageAdminResponse: blocks Input should be a valid list ... input_type=str`
- Website admin panel shows error loading pages

**Root Cause**:
The `blocks` JSONB column in `public_site_pages` table was stored as a JSON string instead of a JSON array. This happened when `json.dumps()` was called before inserting into the JSONB column, causing double-encoding.

Example of corrupted data:
```sql
-- Bad: blocks is a JSON string containing an array
SELECT blocks, jsonb_typeof(blocks) FROM public_site_pages;
-- Result: '"[{\"type\":\"hero\",...}]"', 'string'

-- Good: blocks is a JSON array
-- Result: '[{"type":"hero",...}]', 'array'
```

**Diagnosis**:
```sql
-- Check for corrupted blocks data
SELECT id, slug, jsonb_typeof(blocks) as blocks_type
FROM public_site_pages
WHERE jsonb_typeof(blocks) = 'string';
```

**Fix Applied**:

1. **Backend normalization** (`website_admin.py`):
   - Added `normalize_blocks()` function that parses JSON strings to arrays
   - Applied to all `PageAdminResponse` returns (list, get, create, update, publish, unpublish)

2. **Database migration** (`20260214100000_fix_filter_config_grants_and_blocks.sql`):
   ```sql
   -- Normalize blocks stored as JSON string to JSON array
   UPDATE public_site_pages
   SET blocks = (blocks #>> '{}')::jsonb
   WHERE jsonb_typeof(blocks) = 'string';
   ```

**Verification**:
```bash
# Run smoke test
API_BASE_URL=https://api.fewo.kolibri-visions.de \
JWT_TOKEN=... \
AGENCY_ID=... \
./backend/scripts/pms_website_pages_smoke.sh
```

**Prevention**:
- Always pass Python lists/dicts directly to asyncpg for JSONB columns
- Never use `json.dumps()` before inserting into JSONB
- asyncpg handles Python dict/list → JSONB serialization automatically

---

## Related Issues Fixed in Same Migration

### Filter Config Permission Denied

**Symptom**: `GET /api/v1/public/site/filter-config` returns 500 with "permission denied for table public_site_filter_config"

**Fix**: Added grants in migration:
```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON public_site_filter_config TO authenticated;
GRANT SELECT ON public_site_filter_config TO anon;
```

### Amenities Filter Column Error

**Symptom**: `GET /api/v1/public/properties?amenities=...` returns 500 with "column pa.amenity_code does not exist"

**Fix**: Changed amenities queries to use correct schema:
```sql
-- Old (wrong): pa.amenity_code
-- New (correct): JOIN amenities a ON a.id = pa.amenity_id, use a.name
```

---

## Smoke Test

Script: `backend/scripts/pms_website_pages_smoke.sh`

Tests:
1. GET /api/v1/website/pages returns 200
2. Response is valid JSON array
3. blocks field is array (not JSON string) for all pages
4. Public filter-config endpoint returns 200 or 503 (not 500)
5. Public filter-options endpoint returns 200 or 503 (not 500)
