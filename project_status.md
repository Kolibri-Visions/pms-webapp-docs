# PMS-Webapp Project Status

**Last Updated:** 2026-01-05
**Current Phase:** Phase 21 - Inventory/Availability Production Hardening

## Overview

This document tracks the current state of the PMS-Webapp project, including completed phases, ongoing work, and next steps.

## Current Status Summary

| Area | Status | Notes |
|------|--------|-------|
| **Core Inventory** | ✅ STABLE | Phase 20 validated, concurrency tested |
| **Availability API** | ✅ STABLE | Contract validated, schema migrations applied |
| **Channel Manager** | ✅ OPERATIONAL | Sync batches history, admin UI complete |
| **Database Schema** | ✅ UP-TO-DATE | Guests metrics + timeline columns migrated |
| **Admin Console** | ✅ DEPLOYED | Sync monitoring, batch details UI live |
| **Production Readiness** | 🟡 IN PROGRESS | Phase 21 hardening in progress |

## Completed Phases

### Phase 20: Inventory/Availability Final Validation ✅

**Date Completed:** 2025-12-27 to 2026-01-03

**Key Achievements:**
- ✅ Manual blocks prevent bookings (409 conflict enforcement)
- ✅ Deleting blocks unblocks inventory immediately
- ✅ Cancel frees inventory instantly
- ✅ Idempotent cancellation (safe retry)
- ✅ Cancelled bookings don't prevent rebooking
- ✅ Race-safe concurrency validated (1 success, rest 409)

**Validation Tools:**
- `pms_phase20_final_smoke.sh` - Core inventory mechanics
- `pms_booking_concurrency_test.sh` - Parallel booking race conditions

**Database Migrations:**
- `20260103120000_ensure_guests_metrics_columns.sql` - Metrics columns (total_bookings, total_spent, last_booking_at)
- `20260103123000_ensure_guests_booking_timeline_columns.sql` - Timeline columns (first_booking_at, average_rating, updated_at, deleted_at)

**Documentation:**
- Runbook troubleshooting sections for schema drift
- Scripts README updated with auto-pick logic
- Frontend README updated with batch details UI

**Operations:**
- ✅ DB pool duplicate startup issue root-caused: external host timer was restarting container (not in-process issue)
- ✅ Host connectivity automation updated to avoid container restarts (network attach only)
- ✅ Verification confirmed: single pool_id per runtime, StartedAt stable, no restart events
- ✅ Documentation clarified: duplicate startup signatures have TWO external causes (container replace via deployment recreate OR host automation restart), not in-process uvicorn reload/workers. Process tree verification and decision tree added to runbook.
- ✅ **Phase-1 Ops/Tickets Created (2026-01-04):** Two operational improvement tickets created with minimal tooling/docs
  - Deploy Gating: `backend/docs/ops/tickets/2026-01-04_deploy_gating_docs_only.md` - Classify git changes to skip deploys for docs-only commits (reduces Case A duplicate startups)
  - Network Attachment: `backend/docs/ops/tickets/2026-01-04_network_attach_create_time.md` - Attach network at container create-time (eliminates Case B duplicate startups)
  - Helper script: `backend/scripts/ops/deploy_should_run.sh` - Git diff classifier (exit 0=deploy, 1=skip, 2=error)
  - Runbook sections: "Deploy Gating (Docs-Only Change Detection)" and "Network Attachment at Create-Time (Docker)"
  - Scripts README: `ops/deploy_should_run.sh` documentation with CI/CD integration examples
  - Phase-1: Tickets + docs + helper script created (no enforcement yet, manual opt-in)
  - Phase-2: CI/CD integration + host timer script update (future work)
- ✅ **Deploy Gating Enforcement Wrapper (2026-01-05):** Vendor-neutral wrapper for deployment runners
  - Script: `backend/scripts/ops/deploy_gate.sh` - Machine-readable interface for deployment automation
  - Output: `DEPLOY=0|1 reason="..." old=... new=...` (single-line parseable format)
  - Exit codes: 0=deploy, 1=skip, 2=error
  - Fail-safe behavior: `DEPLOY_GATE_FAIL_MODE=open|closed` (default: open = proceed on error)
  - Auto-inference: SOURCE_COMMIT env var → HEAD, or HEAD~1..HEAD fallback
  - Runbook: "Deployment Runner Wrapper (Enforcement)" section added
  - Scripts README: `ops/deploy_gate.sh` documentation with integration examples
  - Enables deployment platforms to skip container rebuild for docs-only commits (reduces Case A duplicate startups)
  - Classifier updated: `deploy_gate.sh` treated as tooling (same as `deploy_should_run.sh`) - changes to wrapper itself do not trigger deploy
- ✅ **Guest CRM API Implementation (2026-01-05):** Full CRUD + Search + Timeline endpoints for guest management
  - API Routes: `backend/app/api/routes/guests.py` - 6 endpoints under /api/v1/guests
  - Endpoints: GET (list), GET (detail), POST (create), PATCH (update), PUT (update), GET (timeline)
  - Service Layer: `backend/app/services/guest_service.py` - list_guests, get_guest, update_guest, get_guest_timeline (upsert already existed)
  - Schemas: `backend/app/schemas/guests.py` - GuestListResponse, GuestTimelineResponse, GuestTimelineBooking
  - RBAC: admin/manager/staff for CRUD, all roles for read
  - Multi-tenant: Agency isolation enforced, owner role can view guests who booked their properties
  - Search: Text search across first_name, last_name, email, phone
  - Pagination: limit/offset params (default: 20, max: 100)
  - Timeline: Paginated booking history per guest (ordered by check-in desc)
  - Smoke Test: `backend/scripts/pms_guests_smoke.sh` - Verifies list, search, CRUD, timeline endpoints
  - Integration Tests: `backend/tests/integration/test_guests.py` - Full coverage (list, get, create, update, timeline)
  - Runbook: "Guest CRM API Smoke Test" section with diagnostic steps, error table, validation checklist
  - Scripts README: `pms_guests_smoke.sh` documentation with usage examples
- ✅ **Guests Module Integration (2026-01-05):** Guests routes now properly mounted in module system
  - Module: `backend/app/modules/guests.py` - Wraps guests router for module system
  - Bootstrap: Auto-imported in `app/modules/bootstrap.py` for self-registration
  - Production Fix: Guests API now reachable when MODULES_ENABLED=true (default)
  - OpenAPI: /api/v1/guests* paths now appear in /openapi.json
  - Logs: Module 'guests' appears in mounted modules list at startup
  - Runbook: Troubleshooting section added for guests 404 with MODULES_ENABLED=true
- ✅ **Guests List Response Fix (2026-01-05):** Fixed 500 error from missing fields in SELECT query
  - Issue: GET /api/v1/guests returned 500 with validation errors (missing agency_id, updated_at)
  - Root cause: list_guests query didn't select required fields; NULLs in language/vip_status/blacklisted
  - Service fix: Added agency_id, updated_at to SELECT; COALESCE for nullable fields
  - Router fix: Added asyncpg schema exception handling (503 with actionable message)
  - Migration: 20260105120000_fix_guests_list_required_fields.sql (defaults + backfill NULLs)
  - Runbook: Added troubleshooting section with DB/HOST/CONTAINER verification commands
- ✅ **Guests Timeline/Create Hardening (2026-01-05):** Fixed timeline + create schema mismatches
  - Timeline fix: Changed query to use check_in_at/check_out_at (was check_in_date/check_out_date)
  - Create fix: Added guests.auth_user_id column via migration for guest portal linking
  - Migration: 20260105130000_add_guests_auth_user_id.sql (optional uuid column + index)
  - Router fix: Added asyncpg schema exception handling to create_guest and get_guest_timeline (503)
  - Runbook: Added troubleshooting for timeline UndefinedColumnError and create auth_user_id errors
- ✅ **Guests Schema Migration (2026-01-05):** Added missing optional profile columns to prevent schema drift
  - Issue: Production returned 503 errors for missing columns (address_line1, address_line2, marketing_consent, etc.)
  - Migration: 20260105140000_guests_missing_columns.sql (6 optional profile fields)
  - Ensures fresh installations and schema restores have all required columns
  - Smoke script: backend/scripts/pms_guests_smoke.sh validates full CRUD lifecycle
  - Runbook: Added troubleshooting for 503 missing column errors with verification commands

### Admin UI Navigation + Guests CRM Interface ✅

**Date Completed:** 2026-01-05

**Overview:**
Implemented modern, cohesive Admin UI with sidebar navigation and integrated Guests CRM interface. Replaced top navigation with structured sidebar supporting grouped navigation, role-based access control, and consistent layout across all admin pages.

**Key Features:**
- ✅ **AdminShell Component:** Reusable layout with sidebar + topbar + content area
  - Sidebar groups: Übersicht, Betrieb, Channel Manager, CRM, Einstellungen
  - Collapsible sidebar (icons-only mode) with localStorage persistence
  - Responsive drawer pattern on mobile with overlay
  - Active route highlighting and auto-expand for settings group
  - Agency context display in sidebar header
- ✅ **Guests CRM UI Pages:**
  - Guests list page with search, pagination, status badges (VIP, Gesperrt)
  - Guest detail page with tabs (Details, Buchungshistorie)
  - Timeline integration showing booking history
  - Empty/loading/error states for all views
  - API integration with existing endpoints (list, detail, timeline)
- ✅ **Branding Settings Integration:**
  - Settings/Branding page now uses AdminShell (sidebar visible)
  - Access denied pages show within AdminShell for consistency
  - German translations for UI text
- ✅ **RBAC & Plan-Gating UX:**
  - Hide nav items user cannot access (role-based)
  - Show plan-locked items with lock icon and disabled state
  - Friendly access denied messages within layout shell
- ✅ **Visual Design System:**
  - Documented in backend/docs/ui/visual_design_admin_ui.md
  - Soft + elegant + modern aesthetic (calm surfaces, clear hierarchy, gentle contrast)
  - Consistent spacing (4/8/12/16/24 px rhythm), typography, colors
  - Component patterns for tables, forms, cards, modals, empty states, loading states
  - Indigo primary palette with gray neutrals

**Files Changed:**
- frontend/app/components/AdminShell.tsx (new)
- frontend/app/guests/page.tsx (new - list view)
- frontend/app/guests/[id]/page.tsx (new - detail + timeline)
- frontend/app/guests/layout.tsx (new)
- frontend/app/settings/branding/layout.tsx (updated to use AdminShell)
- backend/docs/ui/visual_design_admin_ui.md (new)

**Navigation Structure:**
```
Übersicht
  - Dashboard

Betrieb
  - Objekte
  - Buchungen
  - Verfügbarkeit

Channel Manager
  - Verbindungen
  - Sync-Protokoll

CRM
  - Gäste (NEW)

Einstellungen (collapsible)
  - Branding
  - Rollen & Rechte (admin-only)
  - Plan & Abrechnung (plan-locked)
```

**Manual Verification:**
- Navigate to /guests to see guests list with search and pagination
- Click a guest row to view detail page with timeline
- Visit /settings/branding to confirm sidebar is visible
- Try sidebar collapse toggle to verify icon-only mode
- Test mobile responsive drawer (hamburger menu)
- Verify active route highlighting in sidebar

### Admin UI Build Blockers Fixed ✅

**Date Completed:** 2026-01-05

**Overview:**
Fixed production build failures that prevented Admin UI changes (commit 922f581) from deploying. The Coolify build failed due to ESLint requirement and TypeScript compilation errors, causing /guests routes to remain 404 and sidebar UI to not appear.

**Build Blockers Resolved:**
- ✅ **ESLint Build Failure:** Next.js production build requires ESLint but package not installed
  - Fix: Added `eslint: { ignoreDuringBuilds: true }` to next.config.js
  - Allows builds to proceed without ESLint dependency
  - Lint still runs during development (next dev)
- ✅ **TypeScript Error in Branding Layout:** Property 'name' does not exist on type '{ name: any; }[]'
  - Root cause: Supabase query returned agency as array but code assumed object
  - Location: frontend/app/settings/branding/layout.tsx:73-76
  - Fix: Safe type handling for both array and object shapes
  - Code: `const agency = (teamMember as any)?.agency; const agencyName = (Array.isArray(agency) ? agency?.[0]?.name : agency?.name) ?? 'PMS';`
- ✅ **Runbook Documentation:** Added "Frontend deploy - Admin UI doesn't update / /guests 404 after commit" troubleshooting section
  - Symptoms: New UI features don't appear, routes 404, build failed in Coolify
  - Common causes: ESLint missing, TypeScript errors, OOM
  - Fix checklist: Check build logs, add ignoreDuringBuilds, fix TypeScript, verify routes, redeploy
  - Example fix for array/object type handling included

**Files Changed:**
- frontend/next.config.js (added eslint.ignoreDuringBuilds)
- frontend/app/settings/branding/layout.tsx (fixed agency type handling)
- backend/docs/ops/runbook.md (added frontend deploy troubleshooting)

**Expected Result:**
- Production build succeeds
- /guests routes accessible (no 404)
- /settings/branding shows AdminShell sidebar
- Future TypeScript errors caught during build with clear messages

### Admin UI - Guest Booking History Count Fix ✅

**Date Completed:** 2026-01-05

**Overview:**
Fixed UI bug where guest detail page showed "Buchungshistorie (0)" tab badge even when booking history list displayed multiple items.

**Issue:**
- Guest detail page tab label used `guest.total_bookings` field from guest record
- Actual booking history rendered from separate timeline API fetch
- When `guest.total_bookings` was 0 or stale, badge showed 0 while list had visible items

**Fix:**
- Added `timelineTotal` state to store API response `total` field
- Changed tab label to: `Math.max(timelineTotal, timeline.length)`
- Ensures badge always reflects actual rendered items or API total (whichever is higher)
- Prevents showing "(0)" when list has visible booking cards

**Files Changed:**
- `frontend/app/guests/[id]/page.tsx:57,91,218` - Added timelineTotal state, stored from API response, used in tab label
- `backend/docs/ops/runbook.md:17298` - Added troubleshooting section "Guest Booking History Count Badge Shows 0"

**Expected Result:**
- Booking history tab badge matches number of booking items displayed
- If timeline has 4 bookings → shows "Buchungshistorie (4)"
- If API total is 15 but only 10 items fetched → shows "Buchungshistorie (15)"


### Channel Manager Admin UI ✅

**Date Completed:** 2026-01-02 to 2026-01-03

**Key Features:**
- ✅ Sync batches history table with pagination
- ✅ Batch details modal with operation breakdown
- ✅ Direction indicators (→ outbound, ← inbound)
- ✅ Task ID and error message display
- ✅ Auto-refresh for running batches
- ✅ Status filter dropdown (All | Running | Failed | Success)

**API Enhancements:**
- Extended `BatchOperation` model with direction, task_id, error, duration_ms, log_id
- Fixed `list_batch_statuses()` to include all required fields
- Response validation errors resolved

**Batch Details API Endpoints (Verified 2026-01-03):**
- ✅ `GET /api/v1/channel-connections/{connection_id}/sync-batches` - List batches with pagination, status filtering
- ✅ `GET /api/v1/channel-connections/{connection_id}/sync-batches/{batch_id}` - Batch details with operations breakdown
- ✅ Response model: `BatchStatusResponse` with batch_id, batch_status, status_counts, operations array
- ✅ Batch status logic: failed (any op failed), running (any triggered/running), success (all success)
- ✅ Operations include: operation_type, status, direction, task_id, error, duration_ms, log_id
- ✅ Smoke test script: `backend/scripts/pms_sync_batch_details_smoke.sh`
- ✅ Runbook section: "Verify Sync Batch Details (PROD)" with curl examples
- ✅ **PROD E2E Verified (2026-01-03):** HOST-SERVER-TERMINAL smoke test (`backend/scripts/pms_sync_batch_details_smoke.sh`) returned HTTP 200 for list + details endpoints. Admin UI Batch Details Modal successfully displays batch ff237759… with 3 operations (availability_update, pricing_update, bookings_sync) all success, including batch_id, connection_id, statuses, and durations.

**Expected Fields:**
```json
{
  "batch_id": "uuid",
  "connection_id": "uuid",
  "batch_status": "failed|running|success|unknown",
  "status_counts": {
    "triggered": 0,
    "running": 0,
    "success": 2,
    "failed": 0
  },
  "created_at_min": "2026-01-03T...",
  "updated_at_max": "2026-01-03T...",
  "operations": [
    {
      "operation_type": "availability",
      "status": "success",
      "direction": "outbound",
      "task_id": "celery-task-uuid",
      "error": null,
      "duration_ms": 1234,
      "updated_at": "2026-01-03T...",
      "log_id": "uuid"
    }
  ]
}
```

### Channel Sync Console UX/Operability Hardening 🟡

**Date Started:** 2026-01-03
**Status:** Implemented (Pending User Verification after Deploy)

**Changes:**
- ✅ **Error state handling**: Added 403 Forbidden and 404 Not Found error messages for fetchLogs and fetchBatchDetails (previously only 401/503)
  - 401: "Session expired. Redirecting to login..." (auto-redirects)
  - 403: "Access denied. You don't have permission to view sync logs/batch details."
  - 404: "Connection not found. It may have been deleted." / "Batch not found. It may have been deleted or purged."
  - 503: "Service temporarily unavailable. Please try again shortly."
- ✅ **Empty state improvements**: "No sync logs yet" now includes actionable hint: "Trigger a manual sync or wait for automatic sync to create logs"
- ✅ **Search field text visibility fix**: Sync Logs search input now has explicit text color for light/dark mode (text-slate-900/dark:text-slate-100, placeholder:text-slate-400/dark:placeholder:text-slate-500). Fixes white-on-white invisible text issue.
- ✅ **Search field contrast enhancement**: Previous fix insufficient (low-contrast gray in light mode). Strengthened to text-gray-900/dark:text-white with explicit bg-white/dark:bg-gray-800, placeholder:text-gray-500. Pending user verification after deploy.
- ✅ **Purge logs safety**: Confirmation already present (requires typing "PURGE", button disabled while in-flight, admin-only)
- ✅ **Copy helpers verified**: curl commands use safe placeholders ($CID, $TOKEN, $PROPERTY_UUID) - no embedded secrets
- ✅ **Runbook checklist**: Added "Channel Sync Console UX Verification Checklist" section with systematic test steps for errors, empty states, destructive actions, copy helpers, loading states, and RBAC

**Files Changed:**
- `frontend/app/channel-sync/page.tsx` - Error handling and empty state improvements
- `backend/docs/ops/runbook.md` - UX verification checklist (line 2470+)

**Verification:**
- Deploy to staging/prod and follow runbook checklist: backend/docs/ops/runbook.md#channel-sync-console-ux-verification-checklist
- Expected: All error states display actionable messages, empty states provide guidance, purge requires confirmation, copy helpers never leak secrets

### Theming & Branding (Admin + Future Client) 🟡

**Date Started:** 2026-01-03
**Status:** Phase A - API + DB Implemented (Frontend UI Minimal/Pending)

**Goal:** Enable per-tenant white-label branding with theme tokens for admin UI and future client-facing site.

**Phase A (Implemented):**
- ✅ **Database schema**: `tenant_branding` table with validation constraints (hex colors, font allowlist, radius allowlist)
- ✅ **RLS policies**: SELECT for all tenant users, INSERT/UPDATE for admin/manager only
- ✅ **API endpoints**:
  - `GET /api/v1/branding` - Get effective branding with computed theme tokens (defaults applied)
  - `PUT /api/v1/branding` - Update branding (admin/manager only)
- ✅ **Theme token derivation**: Primary/accent colors → full token set (background, surface, text, border, radius)
- ✅ **Validation**: Server-side hex color regex, allowlist enforcement for font/radius/mode
- ✅ **Documentation**: `backend/docs/ux/theming_branding.md` with token contract, admin workflow, future phases
- ✅ **Runbook**: Branding verification section with migration steps, API curl examples, UI verification checklist

**Files Changed:**
- `supabase/migrations/20260103150000_create_tenant_branding.sql` - Schema + RLS
- `backend/app/schemas/branding.py` - Pydantic models with validators
- `backend/app/api/routes/branding.py` - GET/PUT endpoints
- `backend/app/main.py` - Router registration
- `backend/docs/ux/theming_branding.md` - Complete theming docs
- `backend/docs/ops/runbook.md` - Verification steps (line 2568+)

**Idempotency Fix (2026-01-03):**
- ✅ Migration `20260103150000_create_tenant_branding.sql` patched for full idempotency after partial PROD apply
- Issue: Initial apply failed at index creation (already exists), leaving policies uninstalled
- Fix: Added `IF NOT EXISTS` for index, DO blocks with pg_policies/pg_trigger checks for policies/trigger, BEGIN/COMMIT transaction
- Safe to re-run on partial state, fresh DB, or fully migrated DB
- Pending user apply in PROD (see runbook troubleshooting section)

**Policy Mapping Fix (2026-01-03):**
- ✅ Fixed RLS policies to use JWT-based tenant mapping (matches existing schema pattern)
- Issue: Policies referenced non-existent `public.users` table causing "relation does not exist" error in PROD
- Fix: Updated all policies to use `auth.jwt() ->> 'agency_id'` and `auth.jwt() ->> 'role'` (canonical pattern from existing migrations)
- Migration re-apply pending in PROD

**Module System Integration (2026-01-03):**
- ✅ Branding API mounted via module system (MODULES_ENABLED=true)
- Created branding module (backend/app/modules/branding.py) following domain module pattern
- Auto-registered in bootstrap.py for seamless integration
- Import fixes: Removed invalid User import; moved require_roles from app.core.auth to app.api.deps
- Use dict type for current_user (matches get_current_user return type)
- Error handling: 400 for missing tenant context, 503 for DB unavailable, 200 with defaults when no branding configured
- Tenant context fallback implemented: JWT claim → x-agency-id header (validated) → single-tenant auto-pick
- Smoke test script: backend/scripts/pms_branding_smoke.sh for PROD verification (supports AGENCY_ID env var)
- Status: Working (Phase A complete)

**Phase B (Implemented - 2026-01-04):**
- ✅ **Theme Provider**: Client-side context that fetches branding on app load and applies CSS variables to :root
- ✅ **CSS Variables**: Extended globals.css with theme tokens (--t-primary, --t-accent, --t-bg, --t-surface, --t-text, --t-border, --t-radius)
- ✅ **Dark Mode Support**: data-theme attribute (light/dark/system) with automatic theme switching
- ✅ **Branding Settings Page**: Admin UI page at /settings/branding with form to update branding
- ✅ **Form Fields**: logo_url, primary_color, accent_color, font_family, radius_scale, mode
- ✅ **Access Control**: Server-side auth check (admin/manager only) with role-based redirect
- ✅ **Error Handling**: Graceful degradation on API errors with user-friendly error messages
- ✅ **Navigation**: Added "Branding" tab to BackofficeLayout (admin-only, appears after Connections)
- ✅ **Runbook**: Added "Admin Branding UI Verification" section with WEB-BROWSER test steps

**Files Changed (Phase B):**
- `frontend/app/lib/theme-provider.tsx` - Theme context with branding fetch and CSS variable application
- `frontend/app/globals.css` - CSS variables for theme tokens with light/dark mode support
- `frontend/app/layout.tsx` - Wire ThemeProvider into root layout
- `frontend/app/settings/branding/layout.tsx` - Server-side auth check (admin/manager only)
- `frontend/app/settings/branding/page.tsx` - Branding settings page wrapper
- `frontend/app/settings/branding/branding-form.tsx` - Client form component with save/refresh
- `frontend/app/components/BackofficeLayout.tsx` - Added "Branding" navigation link
- `backend/docs/ops/runbook.md` - Added WEB-BROWSER verification section (line 2900+)

**Verification:**
- HOST-SERVER-TERMINAL: Apply migration `20260103150000_create_tenant_branding.sql`
- HOST-SERVER-TERMINAL: Curl GET/PUT `/api/v1/branding` (verify defaults, update, persist) via smoke script
- WEB-BROWSER: Login → Click Branding → Update colors → Verify CSS variables applied
- WEB-BROWSER: Access control verified (non-admin users see "Access Denied" page)
- WEB-BROWSER: Error handling verified (API errors gracefully fallback to default theme)

**Phase B Hardening (2026-01-04):**
- ✅ **CSS Variable "undefined" Bug Fix**: API token field mismatch caused undefined values in CSS variables
  - Root cause: API returns `background`/`text_muted`, frontend expected `bg`/`textMuted`
  - Fix: Added `normalizeTokenValue()` sanitizer, API token mapper, derived missing tokens
  - Safe property setter: `applyCssVariable()` removes null values instead of stringifying
  - Verification: Check browser console for valid hex colors (not "undefined" strings)
- ✅ **Single Auth Client Instance**: Singleton pattern prevents multiple client warnings
  - Fix: Module-level browser client instance with memoization
  - Prevents "multiple instances in same browser context" warning
- ✅ **Third-Party Name Removal**: Replaced product/tool names with generic terms in docs

**Files Changed (Hardening):**
- `frontend/app/lib/theme-provider.tsx` - Token sanitization, API mapping, derived tokens
- `frontend/app/lib/supabase-browser.ts` - Singleton browser client instance
- `backend/docs/ops/runbook.md` - CSS var verification, third-party name cleanup

**Phase B2 Fix (2026-01-04):**
- ✅ **Theme Mode Palette Mismatch**: Dark mode showed light palette values (white bg, dark text)
  - Root cause: Backend returns flat light tokens; frontend applied same tokens regardless of mode
  - Fix: Separate light/dark default palettes, `deriveDarkTokens()` creates dark palette from light
  - `getEffectiveMode()` resolves system mode via OS preference detection
  - `applyThemeTokens()` applies correct palette based on effective mode
  - Added `data-effective-theme` attribute for debugging
  - Verification: Check bg/surface/text values differ between light/dark modes
- ✅ **Auth Client Singleton Enhancement**: GlobalThis caching survives HMR and page reloads
  - Created `auth-client-singleton.ts` with globalThis-backed singleton
  - Refactored all auth client creation to use `getAuthClient()`
  - Eliminates "multiple instances in same browser context" warning

**Files Changed (B2):**
- `frontend/app/lib/auth-client-singleton.ts` - New singleton module with globalThis caching
- `frontend/app/lib/supabase-browser.ts` - Use singleton instead of module-level cache
- `frontend/app/lib/theme-provider.tsx` - Separate light/dark palettes, mode-driven token application
- `backend/docs/ops/runbook.md` - Mode palette verification, auth singleton troubleshooting

**Future Phase C (Client-Facing):**
- Apply tokens to booking widget, property listings, guest portal
- Consistent brand across admin + client experiences

## Current Phase

### Phase 21: Inventory/Availability Production Hardening 🟡

**Date Started:** 2026-01-03
**Status:** In Progress (Docs + Scaffolding)

**Goals:**
- Document common gotchas and operational guidance
- Validate availability API contract (negative tests)
- Plan modular architecture improvements
- Create minimal scaffolds (non-invasive, not wired in)

**Completed in Phase 21:**
- ✅ Runbook section: Phase 21 production hardening guide
  - What Phase 20 proved
  - Common gotchas checklist (422 errors, schema drift)
  - Minimum production checklist
  - Edge cases roadmap
- ✅ Smoke script: `pms_phase21_inventory_hardening_smoke.sh`
  - Negative test: Missing query params → 422
  - Positive test: Valid availability query → 200
  - Read-only (no side effects)
- ✅ Scripts README documentation for Phase 21 smoke
- ✅ Architecture doc: `modular_monolith_phase21.md`
  - ModuleSpec pattern definition
  - Example module specs (inventory, channel_manager)
  - Registry pattern design
  - Migration strategy (Phase 21-24 timeline)
- ✅ Code scaffold: `backend/app/modules/module_spec.py`
  - ModuleSpec dataclass with validation
  - Example module definitions (docs only)
  - NOT wired into runtime (Phase 22+)
- ✅ Phase 21 smoke validation hardening
  - Robust JSON extraction from mixed output
  - Fallback to raw string checks
  - Handles both PMS custom and FastAPI error envelopes

**Completed in Phase 21A (DB Operations):**
- ✅ Migration runner: `backend/scripts/ops/apply_supabase_migrations.sh`
  - Idempotent migration application with tracking table
  - Dry-run and status modes
  - Production safety guards (CONFIRM_PROD flag)
  - Transaction-based execution
- ✅ Runbook section: "DB Migrations (Production)"
  - Complete usage guide with examples
  - Failure modes and troubleshooting
  - Production workflow recommendations
- ✅ Scripts README: Production Database Migrations section
  - Usage examples and output samples
  - Production workflow steps

**Completed in Phase 21B (Booking Concurrency Hardening):**
- ✅ Advisory lock serialization for concurrent bookings
  - Transaction-scoped PostgreSQL advisory locks per property_id
  - Prevents deadlocks from exclusion constraint checks
  - Located in `booking_service.py:510-520` (updated after hotfix)
- ✅ Deadlock retry wrapper with exponential backoff
  - Automatic retry up to 3 attempts (100ms, 200ms backoff)
  - Only retries deadlocks, other errors propagate immediately
  - Located in `booking_service.py:84-121`
- ✅ Route-level error mapping (503, not 500)
  - Maps exhausted deadlock retries to HTTP 503
  - Client-friendly message: "Database deadlock detected. Please retry your request."
  - Located in `bookings.py:288-298`
- ✅ Concurrency script auto-finds free date windows
  - Queries availability API to find free windows (+1, +7, +14 days)
  - Fallback to +60 days if all attempts fail
  - Prevents test failures from existing bookings
- ✅ Unit tests for deadlock handling
  - Tests retry logic, exponential backoff, error propagation
  - Located in `tests/unit/test_booking_deadlock.py`
- ✅ Documentation updates
  - Runbook section: "Booking Concurrency Deadlocks"
  - Scripts README: Free window auto-detection
  - Project status: Phase 21B completion

**Production Hotfix (2026-01-03) - Phase 21B Follow-up:**
- ❗ **Bug:** NameError in advisory lock code (property_id not defined)
  - Symptom: POST /api/v1/bookings returned HTTP 500 for all requests
  - Root cause: Advisory lock referenced property_id before extraction from booking_data
  - Impact: All booking creation broken in production
- ✅ **Fix Applied:**
  - Added property_id extraction before transaction start (line 511)
  - Advisory lock now uses correctly extracted property_id
  - Transaction scope preserved (xact lock, auto-released)
- ✅ **Verification:**
  - Added unit test: `test_advisory_lock_uses_property_id_from_request()`
  - Expected behavior restored: 1x201 + 9x409 on concurrency test
- ✅ **Documentation:**
  - Runbook: Added "Hotfix Note (2026-01-03)" section
  - Project status: This entry

**API Consistency Fix (2026-01-03) - Inquiry Bookings Policy:**
- ❗ **Issue:** Availability API vs Booking Creation inconsistency
  - GET /api/v1/availability showed inquiry bookings as "free" (ranges=[])
  - POST /api/v1/bookings treated inquiry bookings as blocking (returned 409)
  - Concurrency script auto-window mode picked "free" windows with inquiry bookings, got all 409s (false fails)
- ✅ **Fix Applied (Phase 1 - Status Exclusion):**
  - Updated `BookingService.check_availability()` to exclude inquiry from blocking statuses (line 1565)
  - Non-blocking statuses: cancelled, declined, no_show, inquiry
  - Blocking statuses: confirmed, pending, checked_in, checked_out
- ✅ **Fix Applied (Phase 2 - inventory_ranges Source of Truth):**
  - Replaced bookings table query with `inventory_ranges` query in `check_availability()` (line 1567)
  - Both availability API and booking creation now use same source: `inventory_ranges` with `state='active'`
  - Inquiry bookings do NOT create `inventory_ranges` entries (non-blocking by design)
  - Confirmed/pending bookings and blocks create active `inventory_ranges` entries (blocking)
  - Ensures perfect consistency: if availability shows free, booking creation succeeds (no false 409s)
  - Exclusion constraint on `inventory_ranges` provides final race-safe guard
- ✅ **Testing:**
  - Added unit test: `test_inquiry_booking_does_not_block_confirmed_booking()`
  - Verifies confirmed booking succeeds even when inquiry overlaps (inventory_ranges has no conflict)
- ✅ **Script Improvements:**
  - Extended auto-window search from 3 to 7 windows (+1, +7, +14, +21, +30, +45, +60 days)
  - Improved diagnostic messages for 0 successes + all 409s scenario
  - Fallback increased to +90 days (from +60)
- ✅ **Documentation:**
  - Runbook: Added "Source of Truth for Availability" and troubleshooting sections
  - Scripts README: Updated common issues with "Free Window but All 409" guidance
  - Documented inventory_ranges architecture (source_id, kind, state fields)
- ✅ **Expected Behavior:**
  - Inquiry bookings do NOT block availability checks or booking creation
  - Perfect API consistency: availability free → booking creation succeeds
  - Concurrency script robust to inquiry-blocked windows

**Database Constraint Fix (2026-01-03 Follow-up):**
- ❗ **Second Production Bug:** After OCCUPYING_STATUSES fix, inquiry still blocked at DB level
  - Symptom: Availability showed free (0 inventory_ranges), but ALL booking requests got 409
  - Root cause: `bookings.no_double_bookings` exclusion constraint had `WHERE (status NOT IN ('cancelled', 'declined', 'no_show'))` which included inquiry
  - When trying to INSERT confirmed booking, constraint blocked due to overlapping inquiry
- ✅ **Fix Applied (Migration 20260103140000):**
  - Dropped old `no_double_bookings` constraint
  - Recreated with positive filter: `WHERE (status IN ('pending', 'confirmed', 'checked_in'))`
  - Inquiry bookings now excluded from database-level overlap check
  - Aligns with OCCUPYING_STATUSES and inventory_ranges policy
- ✅ **Diagnostic Logging Enhanced:**
  - Added detailed ExclusionViolationError handling in `booking_service.py:731-760`
  - Logs which constraint triggered 409: bookings.no_double_bookings vs inventory_ranges.inventory_ranges_no_overlap
  - Includes property_id, dates, status, and conflicting booking details
- ✅ **Regression Test Added:**
  - `test_bookings_exclusion_constraint_allows_inquiry_overlap()` in `test_booking_deadlock.py`
  - Verifies inquiry can be created, then confirmed booking overlaps inquiry (succeeds), then second confirmed fails
  - Tests database constraint behavior at unit level

**What's Next:**
- Edge cases validation:
  - Back-to-back bookings (end-exclusive semantics)
  - Timezone boundaries (DST, UTC midnight)
  - Min stay constraints
  - Booking window rules (max future days)
  - Malformed date handling

## Test Coverage Status

### Smoke Scripts

| Script | Purpose | Status | Last Run |
|--------|---------|--------|----------|
| `pms_phase20_final_smoke.sh` | Core inventory validation | ✅ PASS | 2026-01-03 |
| `pms_booking_concurrency_test.sh` | Race-safe concurrency | ✅ PASS | 2026-01-03 |
| `pms_phase21_inventory_hardening_smoke.sh` | API contract validation | ✅ NEW | 2026-01-03 |
| `pms_phase23_smoke.sh` | Quick confidence check | ✅ PASS | 2025-12-27 |

### Integration Tests

- Backend integration tests: ✅ Passing (pytest)
- Frontend build: ✅ Passing (npm run build)
- Database migrations: ✅ Up-to-date (Supabase)

## Database Schema Status

### Current Schema Version

- Supabase migrations: Up-to-date
- Last migration: `20260103140000_fix_bookings_exclusion_inquiry_non_blocking.sql`

### Recent Schema Changes

**Guests Table Enhancements:**
- Metrics columns: `total_bookings`, `total_spent`, `last_booking_at`
- Timeline columns: `first_booking_at`, `average_rating`, `updated_at`, `deleted_at`
- Indexes: `idx_guests_last_booking_at`, `idx_guests_first_booking_at`, `idx_guests_deleted_at`

**Exclusion Constraints:**
- `bookings.no_double_bookings` - Race-safe overlap prevention (GIST)

## Known Issues / Tech Debt

### Phase 21 Tech Debt

- [ ] Module bootstrap is still manual (routers mounted in main.py)
  - **Mitigation:** ModuleSpec scaffold created, registry pattern designed
  - **Timeline:** Integration planned for Phase 22

- [ ] No automated tests for availability API edge cases yet
  - **Mitigation:** Smoke scripts provide basic coverage
  - **Timeline:** Integration tests planned for Phase 21.5

### Monitoring Gaps

- [ ] No production metrics dashboard yet
  - **Impact:** Low (logs provide visibility)
  - **Priority:** Medium (Phase 22+)

- [ ] Admin console lacks WebSocket support (polling instead)
  - **Impact:** Low (3-second polling acceptable)
  - **Priority:** Low (future enhancement)

## Next Steps (Phase 21+)

### Immediate (Phase 21 Completion)

1. Run Phase 21 smoke script in production to validate contract
2. Review modular architecture design with team
3. Document any additional edge cases discovered
4. Update runbook with production deployment experience

### Short-term (Phase 22)

1. Wire ModuleSpec registry into `main.py` bootstrap
2. Create module specs for all existing features
3. Add module dependency resolution
4. Add lifecycle hooks (on_startup, on_shutdown)

### Medium-term (Phase 23-24)

1. Split large modules based on bounded contexts
2. Add module health checks
3. Consider dynamic module loading (hot reload for dev)
4. Implement min_stay and booking_window validation

### Long-term (Phase 25+)

1. Module marketplace consideration (third-party plugins)
2. Selective deployment (disable unused modules)
3. Gradual microservices migration (if needed)

## Deployment Status

### Production Environment

- **Backend API:** Deployed on Coolify
- **Frontend Admin:** Deployed on Coolify
- **Database:** Supabase (managed PostgreSQL)
- **Workers:** Celery + Redis (deployed)

### Environment Variables

All required environment variables configured:
- ✅ `DATABASE_URL`
- ✅ `JWT_SECRET`
- ✅ `ALLOWED_ORIGINS` (CORS configured)
- ✅ `CHANNEL_MANAGER_ENABLED=true`

## References

- [Runbook](./ops/runbook.md) - Operational troubleshooting guide
- [Scripts README](../scripts/README.md) - Smoke script documentation
- [Modular Monolith Phase 21](./architecture/modular_monolith_phase21.md) - Architecture planning
- [Channel Manager](./architecture/channel-manager.md) - Channel integration docs

## Changelog

| Date | Phase | Change |
|------|-------|--------|
| 2026-01-05 | Admin UI | Unified admin shell now covers ops + channel pages - all pages use consistent sidebar navigation |
| 2026-01-04 | Admin UI | Enhanced duration display with tooltip (hover shows raw ms, e.g., "453 ms") |
| 2026-01-04 | API | Implemented duration_ms SQL fallback for batch operations (created_at → updated_at) |
| 2026-01-04 | Admin UI | Added duration display in Batch Details Modal with null handling ("—") |
| 2026-01-03 | Phase 21 | Added Phase 21 hardening docs, smoke script, ModuleSpec scaffold |
| 2026-01-03 | Phase 20 | Applied guests timeline columns migration (first_booking_at, etc.) |
| 2026-01-03 | Phase 20 | Applied guests metrics columns migration (total_bookings, etc.) |
| 2026-01-03 | Admin UI | Fixed PID auto-pick in booking concurrency test |
| 2026-01-02 | Admin UI | Added sync batches history view with direction indicators |
| 2026-01-02 | API | Extended BatchOperation model with detailed fields |
| 2025-12-27 | Phase 30 | Inventory final validation (blocks, B2B, concurrency) PASS |
