# ADR-006: Frontend — Next.js 15 + Custom Components + Tailwind

**Status:** Accepted (implementiert)
**Datum:** 2025-12-21

---

## Entscheidung

**Next.js 15** (App Router) mit **Custom UI-Komponenten** und **Tailwind CSS**.
Kein shadcn/ui, kein TanStack Query, kein React Hook Form.

## Stack (Ist-Stand)

| Komponente | Version | Zweck |
|------------|---------|-------|
| Next.js | 15.5.12 | Framework (App Router) |
| React | 18 | UI Library |
| TypeScript | 5 | Typsicherheit |
| Tailwind CSS | 3.4.1 | Styling (Design Tokens via CSS-Variablen) |
| lucide-react | 0.562.0 | Icons |
| date-fns | 4.1.0 | Datumsformatierung |
| react-day-picker | 9.14.0 | Kalender/Datepicker |
| focus-trap-react | 12.0.0 | Modal Keyboard-Trap (WCAG) |
| @supabase/ssr | 0.5.2 | Auth (Server-side Sessions) |
| @dnd-kit/* | diverse | Drag & Drop |
| dompurify | 3.3.1 | HTML-Sanitization |

## Route-Gruppen (Ist-Stand)

```
frontend/app/
  (admin)/        # Admin-Dashboard (geschuetzt, JWT)
  (auth)/         # Login, Register, Password-Reset
  (owner)/        # Eigentuemer-Portal
  (public)/       # Public Website (kein Auth)
  api/            # Next.js API Routes (Proxy + Internal)
  components/     # Wiederverwendbare Komponenten
  lib/            # Utilities, API Client, i18n
  types/          # TypeScript Types (generiert + manuell)
```

## UI-Pattern

### State Management
- **Vanilla React**: `useState`, `useEffect`, `useContext`
- Kein TanStack Query, kein SWR, kein Redux
- API-Calls via `fetch()` mit `getApiBase()` Prefix

### Forms
- Vanilla `useState` + manuelle Validation
- Shared Form Components (z.B. `GuestForm`, `PropertyForm`)
- Kein React Hook Form, kein Zod

### Design Tokens (statt shadcn/ui)
```css
/* globals.css — CSS-Variablen */
--color-t-primary: ...;      /* Tenant-Branding */
--color-surface-default: ...;
--color-content-default: ...;
```

### Responsive (Table-to-Card)
```tsx
{/* Desktop: Tabelle */}
<div className="hidden md:block">...</div>
{/* Mobile: Karten */}
<div className="block md:hidden">...</div>
```

## Deployment

| Eigenschaft | Wert |
|-------------|------|
| Hosting | **Coolify** (Docker/Nixpacks) |
| Build | `nixpacks.toml` |
| CI | GitHub Actions (`ci-frontend.yml`) |
| E2E Tests | Playwright (`ci-e2e.yml`) |

**Nicht Vercel** — Self-hosted via Coolify auf eigenem Server.
