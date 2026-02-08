# Admin Navigation Branding

This runbook chapter covers the Navigation Customization feature (P2.21.4.8ad + P2.21.4.8ae).

**When to use:** Understanding and troubleshooting navigation branding settings, sidebar customization, nav item ordering, visibility, and custom labels.

## Overview

Navigation Branding provides:

1. **Sidebar Width** — Configurable width percentage (12-28rem)
2. **Nav Styling** — Custom colors for text, hover, and active states
3. **Icon & Spacing** — Adjustable icon sizes (14-24px) and item gaps (4-16px)
4. **Item Ordering** — Tenant-specific navigation item order (P2.21.4.8ae)
5. **Show/Hide Items** — Toggle visibility of nav items per tenant (P2.21.4.8ae)
6. **Custom Labels** — Override default labels with custom text (P2.21.4.8ae)

**Access:** Admin/Manager roles can customize via Settings > Branding > Navigation section.

## Architecture

### Database Schema

| Column | Type | Description |
|--------|------|-------------|
| `nav_config` | `jsonb` | Navigation customization settings |

**nav_config Fields:**

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `width_pct` | int | 12-28 | 16 | Sidebar width in rem |
| `text_color` | hex | - | #ffffff | Navigation text color |
| `icon_size_px` | int | 14-24 | 16 | Icon size in pixels |
| `item_gap_px` | int | 4-16 | 12 | Gap between nav items |
| `hover_bg` | hex | - | rgba(255,255,255,0.1) | Hover background |
| `hover_text` | hex | - | #ffffff | Hover text color |
| `active_bg` | hex | - | (uses accent) | Active item background |
| `active_text` | hex | - | #ffffff | Active item text |
| `order` | string[] | - | [] | Custom nav item order |
| `hidden_keys` | string[] | - | [] | Nav items to hide |
| `label_overrides` | object | - | {} | Custom labels {key: label} |

### CSS Variables

```css
/* Navigation layout */
--nav-width: 16rem;
--nav-width-collapsed: 5rem;

/* Navigation colors */
--nav-text: #ffffff;
--nav-hover-bg: rgba(255,255,255,0.1);
--nav-hover-text: #ffffff;
--nav-active-bg: var(--t-accent);
--nav-active-text: #ffffff;

/* Navigation sizing */
--nav-icon-size: 16px;
--nav-item-gap: 12px;
```

### Allowed Nav Item Keys

These stable keys are used for ordering:

```
dashboard, properties, amenities, extra-services, bookings,
booking-requests, availability, email-outbox, team,
connections, channel-sync, pricing, pricing-seasons,
guests, owners, organisation, branding, roles,
billing, status, runbook, audit-log, modules
```

## Files & Components

### Backend

| File | Purpose |
|------|---------|
| `backend/app/schemas/branding.py` | NavigationBrandingConfig model |
| `backend/app/api/routes/branding.py` | nav_config CRUD with partial merge |
| `supabase/migrations/20260206120000_add_branding_nav_config.sql` | Database migration |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/app/lib/theme-provider.tsx` | applyNavCssVariables() function |
| `frontend/app/components/AdminShell.tsx` | Sidebar with CSS var styling |
| `frontend/app/settings/branding/branding-form.tsx` | Navigation settings UI |

## API

### GET /api/v1/branding

Returns branding with nav_config:

```json
{
  "tenant_id": "uuid",
  "nav_config": {
    "width_pct": 18,
    "text_color": "#FFFFFF",
    "icon_size_px": 18,
    "item_gap_px": 8,
    "hover_bg": "#1E293B",
    "active_bg": "#8B5CF6",
    "order": ["dashboard", "bookings", "properties"]
  },
  "tokens": { ... }
}
```

### PUT /api/v1/branding

Update nav_config (partial merge):

```json
{
  "nav_config": {
    "width_pct": 20,
    "icon_size_px": 20
  }
}
```

Only provided fields are merged; existing values are preserved.

## Validation

### Backend Validation

| Field | Validation |
|-------|------------|
| `width_pct` | 12 ≤ value ≤ 28 |
| `icon_size_px` | 14 ≤ value ≤ 24 |
| `item_gap_px` | 4 ≤ value ≤ 16 |
| Color fields | Valid hex (#RRGGBB) |
| `order` | Only ALLOWED_NAV_KEYS permitted |
| `hidden_keys` | Only ALLOWED_NAV_KEYS permitted |
| `label_overrides` | Keys must be ALLOWED_NAV_KEYS, values non-empty |

### Error Responses

| Status | Cause |
|--------|-------|
| 400 | Invalid nav key in order array |
| 400 | Value out of range |
| 400 | Invalid hex color format |
| 403 | Not admin/manager role |

## Troubleshooting

### Sidebar Width Not Changing

**Symptom:** Sidebar stays at default width after saving changes.

**Causes & Solutions:**

1. **Browser cache:** Hard refresh (Ctrl+Shift+R)
2. **Theme provider not loaded:** Check browser console for errors
3. **CSS var not applied:** Inspect `--nav-width` on documentElement

```javascript
// In browser DevTools
getComputedStyle(document.documentElement).getPropertyValue('--nav-width')
```

### Nav Item Order Not Persisting

**Symptom:** Navigation items revert to default order.

**Causes & Solutions:**

1. **Invalid keys:** Only ALLOWED_NAV_KEYS are accepted
2. **API error:** Check network tab for 400 response
3. **Partial order:** Missing items are appended at end

### Colors Not Applying

**Symptom:** Nav hover/active colors use default instead of custom.

**Causes & Solutions:**

1. **Empty string sent:** Only non-empty hex values are applied
2. **Invalid format:** Must be #RRGGBB format
3. **CSS specificity:** Custom classes may override CSS vars

### Hidden Items Still Visible

**Symptom:** Items in `hidden_keys` still appear in sidebar.

**Causes & Solutions:**

1. **Browser cache:** Hard refresh (Ctrl+Shift+R)
2. **Theme not refreshed:** Check that branding API response includes `hidden_keys`
3. **Verify API:** `curl /api/v1/branding | jq '.nav_config.hidden_keys'`

### Custom Labels Not Showing

**Symptom:** Label overrides not displayed in sidebar.

**Causes & Solutions:**

1. **Empty label:** Labels cannot be empty strings
2. **Invalid key:** Key must match ALLOWED_NAV_KEYS exactly
3. **Verify API:** `curl /api/v1/branding | jq '.nav_config.label_overrides'`

### Save Fails with 500 "column reference nav_config is ambiguous"

**Symptom:** Clicking "Save Changes" in Branding settings returns HTTP 500 with error message containing "column reference 'nav_config' is ambiguous".

**Root Cause:** Backend SQL UPSERT query used unqualified `nav_config` reference in `ON CONFLICT DO UPDATE SET`, causing PostgreSQL ambiguity between table column and EXCLUDED row.

**Fix:** Deploy backend with commit containing the fix. The SQL now uses qualified `tenant_branding.nav_config` reference.

**Verification:**

```bash
# 1. Verify deploy has the fix
EXPECT_COMMIT=<fixed_commit_sha> ./backend/scripts/pms_verify_deploy.sh

# 2. Run smoke test (includes branding save test)
./backend/scripts/pms_admin_theming_smoke.sh
echo "rc=$?"
```

Expected: Both scripts return rc=0, branding save works without errors.

### Save Fails with 500 "NavigationBrandingConfig mapping not list"

**Symptom:** Clicking "Save Changes" in Branding settings returns HTTP 500 with error containing "argument after ** must be a mapping, not list".

**Root Cause:** Database `nav_config` column contains a JSON array (e.g., `["dashboard","properties"]`) instead of a JSON object (e.g., `{"order":["dashboard","properties"]}`). This happens with legacy data or incorrect writes.

**Fix:** Deploy backend with `normalize_nav_config()` function that auto-converts arrays to objects.

**SQL Normalization (run if needed):**

```sql
-- Convert array to object with order field
UPDATE public.tenant_branding
SET nav_config = jsonb_build_object('order', nav_config)
WHERE jsonb_typeof(nav_config) = 'array';

-- Reset non-object/non-array to empty object
UPDATE public.tenant_branding
SET nav_config = '{}'::jsonb
WHERE jsonb_typeof(nav_config) NOT IN ('object', 'array');
```

**Verification:**

```bash
EXPECT_COMMIT=<commit_sha> ./backend/scripts/pms_verify_deploy.sh
./backend/scripts/pms_admin_theming_smoke.sh
```

### Legacy nav_config Array Auto-Normalization

The backend automatically normalizes legacy `nav_config` formats:

| Input Format | Normalized Output |
|--------------|-------------------|
| `null` | `{}` |
| `["a","b"]` (array) | `{"order":["a","b"]}` |
| `{"order":[...]}` (object) | passthrough with sanitized arrays |
| invalid JSON string | `{}` |

The smoke test verifies GET /api/v1/branding always returns `nav_config` as an object with string-only arrays.

### Save Fails with 500 "order.0 Input should be a valid string"

**Symptom:** Clicking "Save Changes" in Branding settings returns HTTP 500 with error containing "order.0 Input should be a valid string (input_value={}, input_type=dict)".

**Root Cause:** Database `nav_config.order` contains dict objects (e.g., `[{"key":"dashboard"}]`) instead of strings (e.g., `["dashboard"]`). This happens when corrupted data is saved.

**Fix:** Deploy backend with enhanced `normalize_nav_config()` and `_sanitize_key_list()` functions that extract string keys from dict objects. Also deploy frontend with normalized order loading.

**SQL Sanitization (run if needed):**

```sql
-- Function to extract string key from mixed types
CREATE OR REPLACE FUNCTION pg_temp.extract_nav_key(val jsonb) RETURNS text AS $$
BEGIN
    IF jsonb_typeof(val) = 'string' THEN RETURN val #>> '{}'; END IF;
    IF jsonb_typeof(val) = 'object' AND val ? 'key' THEN RETURN val->>'key'; END IF;
    IF jsonb_typeof(val) = 'object' AND val ? 'id' THEN RETURN val->>'id'; END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Sanitize order array
UPDATE public.tenant_branding
SET nav_config = nav_config || jsonb_build_object('order',
    (SELECT COALESCE(jsonb_agg(pg_temp.extract_nav_key(elem)), '[]'::jsonb)
     FROM jsonb_array_elements(nav_config->'order') AS elem
     WHERE pg_temp.extract_nav_key(elem) IS NOT NULL))
WHERE nav_config ? 'order'
  AND EXISTS (SELECT 1 FROM jsonb_array_elements(nav_config->'order') AS elem
              WHERE jsonb_typeof(elem) != 'string');
```

**Verification:**

```bash
EXPECT_COMMIT=<sha> ./backend/scripts/pms_verify_deploy.sh
./backend/scripts/pms_admin_theming_smoke.sh
```

Expected: Both scripts return rc=0, nav_config.order contains only strings.

### Save Fails with 500 "nav_config is list-of-dicts"

**Symptom:** Clicking "Save Changes" in Branding settings returns HTTP 500, browser shows CORS error. Server logs show nav_config normalization failure or validation errors like "Invalid nav keys: [{"width_pct":14}, ...]".

**Root Cause:** Database `nav_config` column contains a JSON array of config objects (e.g., `[{"width_pct":14}, {"order":["dashboard"]}]`) instead of a single object. This can happen due to:
- Legacy data migration issues
- Concurrent updates
- Frontend bug sending array instead of object

**Fix (Backend):** Deploy backend with enhanced `normalize_nav_config()` that handles list-of-dicts by merging them into a single object. The function now:
1. Detects if input is `list[dict]`
2. Merges all scalar config values (last-write-wins)
3. Collects and sanitizes all `order`/`hidden_keys` arrays
4. Merges all `label_overrides`
5. Never crashes - always returns valid dict or empty `{}`

**SQL Normalization (run if needed):**

```sql
-- Convert array of config dicts to single object
UPDATE public.tenant_branding
SET nav_config = (
    SELECT jsonb_strip_nulls(jsonb_build_object(
        'width_pct', (SELECT elem->>'width_pct' FROM jsonb_array_elements(nav_config) elem WHERE elem ? 'width_pct' LIMIT 1),
        'order', (SELECT jsonb_agg(o) FROM jsonb_array_elements(nav_config) elem, jsonb_array_elements_text(elem->'order') o WHERE elem ? 'order')
    ))
)
WHERE jsonb_typeof(nav_config) = 'array';
```

**Verification:**

```bash
EXPECT_COMMIT=<sha> ./backend/scripts/pms_verify_deploy.sh
./backend/scripts/pms_admin_theming_smoke.sh
```

Expected: Both scripts return rc=0, Branding Save works without 500/CORS errors.

### Settings Saved But Not Applied (P2.21.4.8af + P2.21.4.8ag)

**Symptom:** User changes nav width, icon size, gap, or reorder in Settings → Branding, clicks Save (success), but sidebar doesn't visually reflect the changes.

**Root Cause Analysis:**

1. **CSS vars not set:** Theme provider didn't call `applyNavCssVariables()` after save
2. **Component not using CSS vars:** Hardcoded Tailwind classes override CSS variables
3. **Context not refreshed:** `refreshBranding()` not called or failed silently
4. **Values are defaults:** Payload didn't include changed values (only sends non-default)

**P2.21.4.8ag Fix (Hardcoded Tailwind → CSS vars):**

The fix in `AdminShell.tsx` replaced hardcoded Tailwind classes with CSS variable usage:

| Element | Before (hardcoded) | After (CSS var) |
|---------|-------------------|-----------------|
| Nav container | `space-y-3` | `style={{ gap: 'var(--nav-item-gap)' }}` |
| Item groups | `space-y-0` | `style={{ gap: 'calc(var(--nav-item-gap) / 3)' }}` |
| Icon wrapper | `w-8 h-8` | `style={{ width: 'calc(var(--nav-icon-size) + 16px)' }}` |
| Icon SVG | fixed size | `style={{ width: 'var(--nav-icon-size)' }}` |
| Sidebar width | `w-64` | `style={{ width: 'var(--nav-width)' }}` |
| Hover states | `hover:bg-white/10` | `hover:bg-[var(--nav-hover-bg)]` |

**Verification Steps:**

1. Open browser DevTools → Console, check for errors
2. Check CSS variables in DevTools → Elements → :root styles:
   ```
   --nav-width: 22rem  (should match saved value)
   --nav-icon-size: 20px
   --nav-item-gap: 10px
   ```
3. Inspect sidebar `<aside>` element, verify `style` uses `var(--nav-width)`
4. Inspect `<nav>` element, verify `style` has `gap: var(--nav-item-gap)`
5. Inspect icon SVG, verify `style` has `width: var(--nav-icon-size)`
6. Check Network tab: PUT /api/v1/branding should return 200 with new values

**Fix Verification (Smoke):**

The smoke test `pms_admin_theming_smoke.sh` includes "Navigation settings APPLY end-to-end" test that:
- Records BEFORE CSS var values AND DOM computed sizes
- Changes width/icon/gap via sliders
- Saves and verifies PUT returns 200
- Records AFTER CSS var values AND DOM computed sizes
- Asserts values CHANGED (not just exist)
- Verifies DOM actually reflects the changes (sidebar width, icon size, nav gap)

```bash
./backend/scripts/pms_admin_theming_smoke.sh
# Look for "[PASS] Nav width CSS var changed" and "[PASS] Icon DOM size changed" lines
```

### Branding Not Visible on Key Pages (P2.21.4.8ah)

**Symptom:** Branding colors are saved successfully, but buttons/badges on /bookings, /booking-requests, /owners pages still show default blue colors instead of branding.

**Root Cause:**

Pages were using legacy `bg-bo-primary` CSS classes which reference hardcoded `--bo-primary: #2563eb` instead of the dynamic `bg-t-primary` which references `--t-primary` from branding API.

**P2.21.4.8ah Fix:**

Replaced legacy `bo-primary` tokens with design system `t-primary` tokens:

| Page | Before | After |
|------|--------|-------|
| /bookings | `bg-bo-primary text-white` | `bg-t-primary text-t-primary-fg` |
| /owners | `bg-bo-primary text-white` | `bg-t-primary text-t-primary-fg` |
| /owners/[id] | `bg-bo-primary text-white` | `bg-t-primary text-t-primary-fg` |
| All focus rings | `ring-bo-primary` | `ring-t-primary` |
| All text links | `text-bo-primary` | `text-t-primary` |

**Verification Steps:**

1. Open browser DevTools → Elements → check `:root` styles for `--t-primary`
2. Inspect primary button, verify `background-color` matches `--t-primary` computed value
3. Change branding color in Settings → Branding, save, reload target page
4. Buttons should reflect new branding color

**Smoke Test Verification:**

```bash
./backend/scripts/pms_admin_theming_smoke.sh
# Look for "[PASS] /bookings: Primary button uses branding color"
# Look for "[PASS] /owners: Primary button uses branding color"
```

### Navigation Settings Not Applying (P2.21.4.8ai + P2.21.4.8aj)

**Symptom:** Saving navigation branding settings (width, icon size, gap, order) succeeds with HTTP 200, but the sidebar doesn't visually change.

**Root Causes:**

1. **CSS vars not re-applied after save:** Theme provider must call `applyNavCssVariables()` after PUT response
2. **Default value mismatch:** theme-provider and AdminShell had different default gap values
3. **Missing data attributes:** Nav items lacked `data-nav-key` for reliable order verification
4. **Stale nav_config values (P2.21.4.8aj):** Frontend only sent non-default values, Backend merged instead of replaced

**P2.21.4.8ai Fix:**

| Issue | Resolution |
|-------|------------|
| Gap default mismatch | Changed theme-provider default `item_gap_px` from 4px to 12px |
| Missing data attributes | Added `data-nav-key={item.key}` to nav Link/div elements |
| Smoke test reliability | Updated tests to use `data-nav-key` for order verification |

**P2.21.4.8aj Fix:**

| Issue | Resolution |
|-------|------------|
| Frontend only sent changed values | Now sends ALL nav_config values (width, icon_size, gap, order, hidden_keys, label_overrides) |
| Backend merged nav_config | Changed from JSONB merge (`\|\|`) to full REPLACE |
| Order/hidden couldn't be cleared | Empty arrays are now sent and properly saved |

**Verification Steps:**

1. Open DevTools → Elements → check `:root` for `--nav-width`, `--nav-icon-size`, `--nav-item-gap`
2. Check `aside` element computed width matches `--nav-width` value
3. Check `nav svg` computed size matches `--nav-icon-size` value
4. Check `nav` computed gap matches `--nav-item-gap` value
5. Use `document.querySelectorAll('nav [data-nav-key]')` to verify nav order

**Smoke Test Verification:**

```bash
./backend/scripts/pms_admin_theming_smoke.sh
# Look for "[PASS] Nav width CSS var changed"
# Look for "[PASS] Sidebar DOM width changed"
# Look for nav key order in output
```

## Navigation Builder (P2.21.4.8ae)

The Navigation Builder UI in Settings > Branding provides:

### Reorder Items

Use up/down arrows to change item order:
- Items are displayed in custom order after save
- If no custom order, default group structure is preserved
- Missing items from order array are appended at end

### Show/Hide Items

Toggle visibility per item:
- Hidden items are stored in `hidden_keys` array
- Hidden items don't render in sidebar
- Role restrictions still apply (hidden item + no role = hidden)

### Custom Labels

Override default labels:
- Enter custom text in input field
- Empty field = use default label
- Stored in `label_overrides` object: `{key: "Custom Label"}`

### Reset

Click "Zurücksetzen" to clear all customizations:
- Resets order to default
- Shows all hidden items
- Removes all label overrides

## Maximale Branding Möglichkeiten

Future enhancements for maximum branding flexibility:

| Feature | Status | Description |
|---------|--------|-------------|
| Sidebar Width | ✅ Implemented | 12-28rem range |
| Nav Text Color | ✅ Implemented | Hex color |
| Icon Size | ✅ Implemented | 14-24px |
| Item Gap | ✅ Implemented | 4-16px |
| Hover Background | ✅ Implemented | Hex color |
| Hover Text | ✅ Implemented | Hex color |
| Active Background | ✅ Implemented | Hex color |
| Active Text | ✅ Implemented | Hex color |
| Item Ordering | ✅ Implemented | Custom order array |
| Show/Hide Items | ✅ Implemented | hidden_keys array |
| Custom Labels | ✅ Implemented | label_overrides object |
| Collapsed Width | 🔮 Planned | Custom collapsed sidebar width |
| Active Indicator Style | 🔮 Planned | Line, pill, background variants |
| Icon Color | 🔮 Planned | Separate icon color token |
| Divider Color | 🔮 Planned | Color for section dividers |
| Section Header Style | 🔮 Planned | Font size, weight, color |
| Density Mode | 🔮 Planned | Compact vs. comfortable spacing |
| Custom Icons | 🔮 Planned | Upload custom icons per item |

## Verification (PROD)

### Deploy Verification

```bash
# HOST-SERVER-TERMINAL
source /root/.pms_env
export API_BASE_URL="https://api.fewo.kolibri-visions.de"

# 1. Verify deploy
EXPECT_COMMIT=<sha> ./backend/scripts/pms_verify_deploy.sh

# 2. Run smoke test
./backend/scripts/pms_admin_theming_smoke.sh

echo "admin_theming_rc=$?"
```

### API Verification

```bash
# Get current nav_config
curl -s "${API_BASE_URL}/api/v1/branding" \
  -H "Authorization: Bearer ${JWT_TOKEN}" | jq '.nav_config'

# Update nav_config
curl -X PUT "${API_BASE_URL}/api/v1/branding" \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"nav_config": {"width_pct": 20}}'
```

### Browser Verification

```javascript
// Check nav CSS variables
getComputedStyle(document.documentElement).getPropertyValue('--nav-width')
getComputedStyle(document.documentElement).getPropertyValue('--nav-icon-size')
getComputedStyle(document.documentElement).getPropertyValue('--nav-text')

// Check data attributes (set by theme-provider)
document.documentElement.dataset.navWidth
document.documentElement.dataset.navIconSize
```

## Smoke Test

**Script:** `backend/scripts/pms_admin_theming_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

The smoke test includes a navigation CSS variables test that verifies:
- `--nav-width` is defined
- `--nav-width-collapsed` is defined
- `--nav-text` is defined
- `--nav-icon-size` is defined
- `--nav-item-gap` is defined

### Expected Result

```
[PASS] All navigation CSS variables are defined
```

## Related Documentation

- [Admin UI Design System](./19-admin-theming.md) — Design tokens and theming
- [Branding Logo Upload](./18-branding-logo.md) — Logo customization
