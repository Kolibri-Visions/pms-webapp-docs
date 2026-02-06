# Admin UI Design System & Theming

This runbook chapter covers the Admin UI Design System refactor (P2.21.4.8ac).

**When to use:** Understanding and troubleshooting the design token system, tenant branding integration, and UI consistency across admin pages.

## Overview

The Admin UI Design System provides:

1. **Unified Design Tokens** — Consistent color, spacing, and typography tokens
2. **Tenant Theming** — Dynamic branding colors applied via CSS variables
3. **Semantic State Colors** — Universal colors for success, warning, error, info states
4. **UI Primitives** — Reusable components (Button, Badge, Alert) with built-in theming

**Access:** All admin pages use the design system. Branding customization is available to admin/manager roles.

## Architecture

### Token Categories

| Category | Prefix | Purpose | Customizable? |
|----------|--------|---------|---------------|
| **Tenant (Theme)** | `t-*` | Brand colors from branding API | Yes |
| **Semantic State** | `state-*` | Status indicators (success, warning, error, info) | No |
| **Surface** | `surface-*` | Background hierarchies | No |
| **Content** | `content-*` | Text color hierarchies | No |
| **Stroke** | `stroke-*` | Border colors | No |

### CSS Variable Naming

```css
/* Tenant/Theme colors (dynamic from branding API) */
--t-primary: #3b82f6;
--t-primary-hover: #2563eb;
--t-primary-foreground: #ffffff;
--t-secondary: #0f172a;
--t-accent: #8b5cf6;
--t-bg: #ffffff;
--t-surface: #f9fafb;

/* Semantic states (fixed, universal meaning) */
--state-success: #10b981;
--state-success-bg: #d1fae5;
--state-success-fg: #065f46;
--state-warning: #f59e0b;
--state-warning-bg: #fef3c7;
--state-error: #ef4444;
--state-error-bg: #fee2e2;
--state-info: #3b82f6;
--state-info-bg: #dbeafe;

/* Surfaces (backgrounds) */
--surface-default: #ffffff;
--surface-elevated: #ffffff;
--surface-sunken: #f9fafb;

/* Content (text) */
--content-default: #111827;
--content-secondary: #374151;
--content-muted: #6b7280;
--content-inverse: #ffffff;

/* Stroke (borders) */
--stroke-default: #e5e7eb;
--stroke-subtle: #f3f4f6;
--stroke-strong: #d1d5db;
```

### Tailwind Class Mapping

| Token Type | Tailwind Classes | Example |
|------------|------------------|---------|
| Theme Primary | `bg-t-primary`, `text-t-primary`, `border-t-primary` | Primary buttons |
| Theme Accent | `bg-t-accent`, `ring-t-accent` | Focus rings, highlights |
| State Success | `bg-state-success`, `text-state-success-fg`, `bg-state-success-bg` | Success badges/alerts |
| State Error | `bg-state-error`, `text-state-error-fg` | Error badges/alerts |
| Surface | `bg-surface-elevated`, `bg-surface-sunken` | Cards, backgrounds |
| Content | `text-content-default`, `text-content-muted` | Text hierarchies |
| Stroke | `border-stroke-default`, `border-stroke-subtle` | Borders |

## Files & Components

### Design System Definition

| File | Purpose |
|------|---------|
| `frontend/tailwind.config.ts` | Tailwind color palettes mapping to CSS variables |
| `frontend/app/globals.css` | CSS variable definitions with defaults |
| `frontend/app/lib/theme-provider.tsx` | Dynamic theme application from branding API |

### UI Primitives

| Component | Location | Purpose |
|-----------|----------|---------|
| `Button` | `components/ui/Button.tsx` | Theme-aware buttons (primary, secondary, ghost, danger, outline) |
| `Badge` | `components/ui/Badge.tsx` | Status indicators with semantic colors |
| `Alert` | `components/ui/Alert.tsx` | Dismissible alerts with semantic variants |

### Layout Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `AdminShell` | `components/AdminShell.tsx` | Main admin layout with themed sidebar |
| `BackofficeLayout` | `components/BackofficeLayout.tsx` | Ops console layout |

## Features

### Tenant Branding Integration

The theme provider fetches branding from `/api/v1/branding` and applies colors as CSS variables:

```tsx
// theme-provider.tsx
useEffect(() => {
  if (branding?.primary_color) {
    document.documentElement.style.setProperty('--t-primary', branding.primary_color);
  }
  // ... other colors
}, [branding]);
```

**Branding Fields Mapped:**
| Branding API Field | CSS Variable | Tailwind |
|--------------------|--------------|----------|
| `primary_color` | `--t-primary` | `bg-t-primary` |
| `secondary_color` | `--t-secondary` | `bg-t-secondary` |
| `accent_color` | `--t-accent` | `bg-t-accent` |
| `background_color` | `--t-bg` | `bg-t-bg` |

### Semantic State Colors

State colors have **fixed meaning** and are NOT tenant-customizable:

| State | Usage | Example Classes |
|-------|-------|-----------------|
| Success | Completed, active, confirmed | `bg-state-success-bg text-state-success-fg` |
| Warning | Pending, expiring soon, caution | `bg-state-warning-bg text-state-warning-fg` |
| Error | Failed, rejected, expired | `bg-state-error-bg text-state-error-fg` |
| Info | Neutral information | `bg-state-info-bg text-state-info-fg` |

### Button Component Usage

```tsx
import { Button } from "@/app/components/ui/Button";

// Primary (tenant primary color)
<Button variant="primary">Save Changes</Button>

// Secondary (tenant secondary color)
<Button variant="secondary">Cancel</Button>

// Danger (error state color)
<Button variant="danger">Delete</Button>

// Ghost (transparent)
<Button variant="ghost">More Options</Button>

// With loading state
<Button variant="primary" isLoading>Processing...</Button>
```

### Badge Component Usage

```tsx
import { Badge } from "@/app/components/ui/Badge";

<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="error" dot>Offline</Badge>
<Badge variant="info">New</Badge>
```

### Alert Component Usage

```tsx
import { Alert } from "@/app/components/ui/Alert";

<Alert variant="error" title="Error">
  Something went wrong.
</Alert>

<Alert variant="success" dismissible onDismiss={() => {}}>
  Changes saved successfully!
</Alert>
```

## Token Reference

### Complete Token List

```
Tenant Theme (t-*):
  t-primary, t-primary-hover, t-primary-fg
  t-secondary, t-secondary-hover, t-secondary-fg
  t-accent, t-accent-hover, t-accent-fg
  t-bg, t-surface, t-surface-hover
  t-text, t-text-muted
  t-border, t-border-subtle
  t-ring

Semantic States (state-*):
  state-success, state-success-bg, state-success-border, state-success-fg
  state-warning, state-warning-bg, state-warning-border, state-warning-fg
  state-error, state-error-bg, state-error-border, state-error-fg
  state-info, state-info-bg, state-info-border, state-info-fg

Surfaces (surface-*):
  surface (default), surface-elevated, surface-sunken, surface-overlay

Content (content-*):
  content (default), content-secondary, content-muted, content-inverse

Strokes (stroke-*):
  stroke (default), stroke-subtle, stroke-strong
```

## Verification (PROD)

### Deploy Verification

```bash
# HOST-SERVER-TERMINAL
source /root/.pms_env
export API_BASE_URL="https://api.fewo.kolibri-visions.de"

# 1. Verify deploy
EXPECT_COMMIT=<sha> ./backend/scripts/pms_verify_deploy.sh

# 2. Run smoke test
E2E_ADMIN_EMAIL="$SB_EMAIL" \
E2E_ADMIN_PASSWORD="$SB_PASSWORD" \
./backend/scripts/pms_admin_theming_smoke.sh

echo "admin_theming_rc=$?"
```

### Quick API Verification

```bash
# Check theme tokens are returned by branding API
curl -s "${API_BASE_URL}/api/v1/branding" \
  -H "Authorization: Bearer ${JWT_TOKEN}" | jq '.tokens'
```

### Browser Verification

```javascript
// In browser DevTools console
// Check CSS variables
getComputedStyle(document.documentElement).getPropertyValue('--t-primary')
getComputedStyle(document.documentElement).getPropertyValue('--state-success')
getComputedStyle(document.documentElement).getPropertyValue('--surface-elevated')

// Check data attributes (set by theme-provider for debugging)
document.documentElement.dataset.tPrimary
```

## Troubleshooting

### Theme Colors Not Applying

**Symptom:** Admin UI shows default blue instead of custom branding colors.

**Causes & Solutions:**

1. **Browser cache:** Hard refresh (Ctrl+Shift+R / Cmd+Shift+R)
2. **Branding not saved:** Verify `/api/v1/branding` returns the expected colors
3. **Theme provider not loaded:** Check browser console for errors in theme-provider
4. **Invalid color format:** Ensure colors are valid hex (#RRGGBB)

### Semantic Colors Wrong

**Symptom:** Success badge shows wrong color (not green).

**Resolution:** Semantic state colors (success, warning, error, info) are NOT customizable via branding. They use fixed values. Check if the component is using `state-success` vs `t-primary`.

### Missing Token in Component

**Symptom:** Tailwind class not working (e.g., `bg-t-secondary-light`).

**Resolution:** Check if the token exists in:
1. `frontend/app/globals.css` (CSS variable definition)
2. `frontend/tailwind.config.ts` (Tailwind mapping)

Use existing tokens:
- Light variant: Use opacity (e.g., `bg-t-secondary/60`)
- Hover variant: Use defined hover token (e.g., `bg-t-primary-hover`)

### Component Using Hardcoded Colors

**Symptom:** Some buttons/badges don't change with branding.

**Resolution:** Check if the component is using design tokens:

**Correct (uses tokens):**
```tsx
<button className="bg-t-primary hover:bg-t-primary-hover">
```

**Wrong (hardcoded):**
```tsx
<button className="bg-blue-600 hover:bg-blue-700">
```

Search for hardcoded colors:
```bash
grep -r "bg-blue-" frontend/app/
grep -r "bg-gray-" frontend/app/
grep -r "#[0-9a-fA-F]\{6\}" frontend/app/
```

## Smoke Test

**Script:** `backend/scripts/pms_admin_theming_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage
E2E_ADMIN_EMAIL="admin@example.com" \
E2E_ADMIN_PASSWORD="password" \
./backend/scripts/pms_admin_theming_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `E2E_ADMIN_EMAIL` | Yes | - | Admin email for UI login |
| `E2E_ADMIN_PASSWORD` | Yes | - | Admin password |
| `ADMIN_BASE_URL` | No | `https://admin.fewo.kolibri-visions.de` | Admin UI URL |
| `PW_PROJECT` | No | `chromium` | Browser (chromium/firefox/webkit) |

### What It Tests

1. **Login:** Authenticate via UI form
2. **CSS Variables:** Verify design tokens are set on `documentElement`:
   - `--t-primary`, `--t-accent`, `--t-bg`, `--t-surface`
   - `--state-success`, `--state-warning`, `--state-error`
   - `--surface-elevated`, `--content-default`
3. **Screenshot:** Captures page state for visual verification

### Expected Result

```
PASS=3, FAIL=0
Screenshots saved to: /tmp/screenshots/
```

## Migration Guide

### Converting Hardcoded Colors

When migrating a component to use design tokens:

| Old Class | New Token |
|-----------|-----------|
| `bg-white` | `bg-surface-elevated` |
| `bg-gray-50` | `bg-surface-sunken` |
| `text-gray-900` | `text-content-default` |
| `text-gray-600` | `text-content-secondary` |
| `text-gray-500` | `text-content-muted` |
| `border-gray-200` | `border-stroke-default` |
| `bg-blue-600` | `bg-t-primary` |
| `hover:bg-blue-700` | `hover:bg-t-primary-hover` |
| `bg-green-100` | `bg-state-success-bg` |
| `text-green-800` | `text-state-success-fg` |
| `bg-red-100` | `bg-state-error-bg` |
| `text-red-800` | `text-state-error-fg` |

## Related Documentation

- [Branding Logo Upload](./18-branding-logo.md) — Logo and color customization
- [Theme Provider](../../api/theme-provider.md) — Dynamic theming implementation
