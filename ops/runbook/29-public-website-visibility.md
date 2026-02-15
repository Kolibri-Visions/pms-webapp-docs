# Public Website — Property Visibility

**Added**: 2026-02-15

This runbook chapter covers property visibility rules for the public website.

## Overview

Properties on the public website (`/unterkuenfte`, property detail pages) are filtered by two flags:

| Flag | Description |
|------|-------------|
| `is_public` | Property is listed on public website |
| `is_active` | Property is active (not archived/disabled) |

**Both flags must be `true`** for a property to appear on the public website.

## Visibility Logic

### Before (Pre-2026-02-15)

Only `is_public = true` was checked. Inactive properties could still appear.

### After (2026-02-15)

All public queries now include: `p.is_public = true AND p.is_active = true`

## Affected Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/public/properties` | Property list |
| `GET /api/v1/public/properties/{id}` | Property detail |
| `GET /api/v1/public/properties/filter-options` | Filter options (cities, types, amenities) |

## File Location

**Backend**: `backend/app/api/routes/public_site.py`

**Key Lines**:
```python
# Line 392
where_clauses = ["p.agency_id = $1", "p.is_public = true", "p.is_active = true"]

# Lines 598, 613, 635, 845
WHERE ... AND p.is_public = true AND p.is_active = true
```

## Common Issues

### Property Not Appearing on Public Site

**Symptom**: Property exists in Admin but not on `/unterkuenfte`.

**Debug Steps**:

1. Check property flags in Admin UI:
   - "Aktiv" badge should be green
   - "Gelistet" badge should be green

2. Direct DB check:
   ```sql
   SELECT name, is_public, is_active
   FROM properties
   WHERE id = 'PROPERTY_UUID';
   ```

3. If `is_active = false`:
   - Edit property in Admin
   - Toggle "Aktiv" to enabled
   - Save

### Property Still Appearing After Deactivation

**Symptom**: Set property inactive, still shows on public site.

**Possible Causes**:

1. **CDN/Browser Cache**: Clear cache or wait for TTL
   - filter-options: 60s cache
   - property list: varies by CDN config

2. **Deployment not complete**: Verify backend redeployed

3. **Different agency**: Check correct agency context

## Verification

**API Test**:
```bash
# Should NOT include inactive properties
curl -s "https://api.fewo.kolibri-visions.de/api/v1/public/properties" \
  -H "Host: fewo.kolibri-visions.de" | jq '.items[].name'
```

**SQL Verification**:
```sql
-- Find properties that would appear on public site
SELECT id, name, is_public, is_active
FROM properties
WHERE agency_id = 'YOUR_AGENCY_ID'
  AND is_public = true
  AND is_active = true;

-- Find properties hidden due to is_active=false
SELECT id, name, is_public, is_active
FROM properties
WHERE agency_id = 'YOUR_AGENCY_ID'
  AND is_public = true
  AND is_active = false;
```

## Related Commits

- `731dfc1` — fix: hide inactive properties from public website
