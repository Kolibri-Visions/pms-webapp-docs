# Theming & Branding System

**Last Updated:** 2026-01-03
**Status:** Phase A - Admin UI Theme Tokens (Implemented)

## Overview

The PMS-Webapp theming system enables per-tenant white-label branding through a **Brand Kit** (stored config) and **Theme Tokens** (derived CSS variables).

**Architecture:**
- **Brand Kit**: Tenant-specific config (logo, colors, font, radius) stored in `tenant_branding` table
- **Theme Tokens**: Computed CSS variables derived from Brand Kit with sensible defaults
- **Admin UI**: Consumes theme tokens for consistent styling (light/dark aware)
- **Future (Phase B+)**: Client-facing site reuses same token contract

## Brand Kit Schema

**Table:** `public.tenant_branding`

**Columns:**
- `tenant_id` (uuid, PK) - FK to `agencies`
- `logo_url` (text, nullable) - Tenant logo URL
- `primary_color` (text, nullable) - Brand primary color (hex, e.g., `#4F46E5`)
- `accent_color` (text, nullable) - Brand accent color (hex, e.g., `#10B981`)
- `font_family` (text, nullable) - Font preference (allowlist: `system`, `inter`, `geist`)
- `radius_scale` (text, nullable) - Border radius scale (`none`, `sm`, `md`, `lg`)
- `mode` (text, nullable) - Theme mode (`system`, `light`, `dark`)
- `updated_at` (timestamptz) - Last updated timestamp

**Validation Constraints:**
- Hex colors: `/^#[0-9A-Fa-f]{6}$/`
- Font family: Allowlist only
- Radius scale: Allowlist only
- Mode: Allowlist only

**Defaults (if null):**
- `primary_color`: `#4F46E5` (indigo)
- `accent_color`: `#10B981` (emerald)
- `font_family`: `system`
- `radius_scale`: `md`
- `mode`: `system`

## Theme Tokens Contract

**Endpoint:** `GET /api/v1/branding`

**Response Shape:**
```json
{
  "tenant_id": "uuid",
  "logo_url": "https://...",
  "primary_color": "#4F46E5",
  "accent_color": "#10B981",
  "font_family": "system",
  "radius_scale": "md",
  "mode": "system",
  "tokens": {
    "primary": "#4F46E5",
    "accent": "#10B981",
    "background": "#FFFFFF",
    "surface": "#F9FAFB",
    "text": "#111827",
    "text_muted": "#6B7280",
    "border": "#E5E7EB",
    "radius": "0.5rem"
  }
}
```

**Token Keys:**
- `primary` - Primary brand color (buttons, links, highlights)
- `accent` - Accent/secondary color (success states, badges)
- `background` - Page background
- `surface` - Card/panel surfaces
- `text` - Primary text color
- `text_muted` - Secondary/muted text
- `border` - Border color
- `radius` - Border radius value

**Light/Dark Mode:**
- Tokens include light mode defaults
- CSS variables support dark mode via `dark:` classes
- Mode preference (`system`/`light`/`dark`) informs UI but doesn't override user OS preference

## API Endpoints

### GET /api/v1/branding

**Auth:** Authenticated users (any role)

**Returns:** Effective branding with defaults applied

**Use Case:** Frontend fetches on app load to apply theme

### PUT /api/v1/branding

**Auth:** Admin or Manager only

**Body:** `BrandingUpdate` schema (all fields optional)

**Returns:** Updated branding with tokens

**Use Case:** Admin sets logo/colors via Branding Settings UI

## Admin Workflow

**Location:** Admin UI → Settings/Branding (future dedicated page or existing settings panel)

**Steps:**
1. Admin navigates to Branding settings
2. Uploads logo or enters logo URL
3. Selects primary color (color picker)
4. Selects accent color (color picker)
5. Optionally selects font and radius scale
6. Clicks "Save"
7. Page refreshes/reloads theme automatically
8. Changes apply across all admin UI surfaces (sidebar, buttons, cards, etc.)

## Safety & Validation

**Server-Side Validation:**
- Hex color regex enforced via CHECK constraints
- Font/radius/mode allowlists enforced via CHECK constraints
- RLS policies prevent cross-tenant access

**Frontend Validation:**
- Color inputs use HTML5 color picker (always valid hex)
- Dropdowns restrict to allowlist values
- No freeform text for controlled fields

**Defaults Strategy:**
- Missing fields fall back to hardcoded defaults in `derive_theme_tokens()`
- No breaking changes if new token keys added (backwards compatible)

## Future Phases

**Phase B (Client-Facing Site):**
- Reuse same `GET /api/v1/branding` endpoint
- Apply tokens to booking widget, property listings, guest portal
- Consistent brand identity across admin + client experiences

**Phase C (Advanced Theming):**
- Custom CSS overrides (admin uploads custom.css)
- Multi-brand support (sub-brands per property group)
- Dark mode force override (admin locks mode to light or dark)

## Migration

**File:** `supabase/migrations/20260103150000_create_tenant_branding.sql`

**Apply:**
```bash
# Production (HOST-SERVER-TERMINAL)
cd /path/to/repo
bash backend/scripts/ops/apply_supabase_migrations.sh --status
bash backend/scripts/ops/apply_supabase_migrations.sh --apply
```

**Rollback:**
- DROP TABLE tenant_branding (data loss, use with caution)
