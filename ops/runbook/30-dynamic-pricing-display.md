# Runbook 30: Dynamic Pricing Display ("ab X€")

## Overview

The public website shows "ab X€" (from X€) prices for properties. This price is dynamically calculated from the **minimum seasonal price** across all active rate plan seasons.

## How It Works

### Price Calculation Flow

```
Public API Request
    ↓
Query calculates MIN(rate_plan_seasons.nightly_cents)
    ↓
Falls back to properties.base_price if no seasons found
    ↓
Returns as display_price (shown as base_price to frontend)
```

### SQL Logic (simplified)

```sql
COALESCE(
    (SELECT MIN(rps.nightly_cents) / 100
     FROM rate_plans rp
     JOIN rate_plan_seasons rps ON rps.rate_plan_id = rp.id
     WHERE rp.property_id = p.id
       AND rp.archived_at IS NULL
       AND rp.deleted_at IS NULL
       AND rps.active = true
       AND rps.archived_at IS NULL
       AND rps.nightly_cents IS NOT NULL
    ),
    p.base_price
) as display_price
```

## Common Issues

### Wrong Price Displayed

**Symptom:** Public website shows incorrect "ab X€" price (e.g., 100€ instead of expected 120€)

**Diagnosis:**

```sql
-- Check what MIN price the query finds
SELECT
    p.name,
    p.base_price as "DB base_price",
    (SELECT MIN(rps.nightly_cents)::numeric / 100
     FROM rate_plans rp
     JOIN rate_plan_seasons rps ON rps.rate_plan_id = rp.id
     WHERE rp.property_id = p.id
       AND rp.archived_at IS NULL
       AND rp.deleted_at IS NULL
       AND rps.active = true
       AND rps.archived_at IS NULL
       AND rps.nightly_cents IS NOT NULL
    ) as "Calculated MIN price"
FROM properties p
WHERE p.id = '<PROPERTY_UUID>';
```

**Root Causes:**

1. **Test/Smoke Rate Plans with low prices**
   - Many SMOKE_*, TEST_* rate plans exist with 100€ placeholder prices
   - Fix: Archive test rate plans
   ```sql
   UPDATE rate_plans
   SET archived_at = now()
   WHERE property_id = '<PROPERTY_UUID>'
     AND (name LIKE 'SMOKE%' OR name LIKE 'TEST%' OR name LIKE 'Test Rate Plan%')
     AND archived_at IS NULL;
   ```

2. **Future year seasons with placeholder prices**
   - Template-imported seasons (e.g., 2027) have default 100€ prices
   - Fix: Update prices via Admin UI or archive future seasons
   ```sql
   -- Archive future year seasons
   UPDATE rate_plan_seasons
   SET archived_at = now()
   WHERE rate_plan_id IN (
       SELECT id FROM rate_plans WHERE property_id = '<PROPERTY_UUID>'
   )
   AND date_from >= '2027-01-01';
   ```

3. **All rate plans have `active = false`**
   - Note: The query does NOT filter on `rp.active` anymore
   - Only `archived_at IS NULL` and `deleted_at IS NULL` matter

### Debugging Checklist

```sql
-- 1. List all rate plans and their season counts
SELECT rp.name, rp.active, rp.archived_at, COUNT(rps.id) as seasons
FROM rate_plans rp
LEFT JOIN rate_plan_seasons rps ON rps.rate_plan_id = rp.id
  AND rps.archived_at IS NULL AND rps.active = true
WHERE rp.property_id = '<PROPERTY_UUID>'
  AND rp.archived_at IS NULL
GROUP BY rp.id
ORDER BY rp.name;

-- 2. List all seasons with prices (sorted by price ASC)
SELECT
    rp.name as rate_plan,
    rps.label,
    rps.nightly_cents / 100 as price_eur,
    rps.date_from,
    rps.active,
    rps.archived_at
FROM rate_plans rp
JOIN rate_plan_seasons rps ON rps.rate_plan_id = rp.id
WHERE rp.property_id = '<PROPERTY_UUID>'
  AND rp.archived_at IS NULL
ORDER BY rps.nightly_cents ASC
LIMIT 20;
```

## Auto-Sync (Option B)

When seasons are created/updated/deleted, the property's `base_price` is automatically synced to the MIN seasonal price. This is handled by `sync_property_base_price()` in `pricing.py`.

**Triggered by:**
- Create/update/delete/restore/purge season
- Bulk archive/delete seasons
- Apply season template
- Sync from template

## Related Files

| File | Purpose |
|------|---------|
| `backend/app/api/routes/public_site.py` | Public API with display_price calculation |
| `backend/app/api/routes/pricing.py` | Season CRUD + sync_property_base_price() |
| `frontend/app/(public)/[...slug]/page.tsx` | Property detail page showing price |

## Version History

- **2026-02-17**: Initial implementation of dynamic pricing (Option A + B)
- **2026-02-17**: Removed `rp.active = true` requirement (flag often not set in UI)
- **2026-02-17**: Removed `rp.is_default = true` requirement (no UI to set it)
