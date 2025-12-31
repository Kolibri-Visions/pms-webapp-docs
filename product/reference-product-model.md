# PMS Reference Product Model

**Purpose**: Map reference product model pillars to PMS-Webapp modules to ensure feature completeness while maintaining clean modular architecture.

---

## Overview

We are building PMS-Webapp as a **modular monolith** following a proven PMS product model. This document maps the reference model's 6 pillars to our module structure, defines MVP scope, and identifies implementation priorities.

**Current Phase**: 20 (Inventory/Availability system complete)
**Next Phase**: 21 (Modularization scaffold + preparation)

---

## Reference Model Pillars → PMS-Webapp Modules

### 1. Core PMS

**Reference Pillar**: Property Management System Core
**Our Module**: `core_pms`

**Scope (MVP - Phase 19-20 ✅)**:
- Properties management (CRUD, multi-tenancy)
- Bookings lifecycle (inquiry → confirmed → checked_in → checked_out)
- Availability/Inventory system with conflict detection
- Guest management
- Basic pricing (manual pricing, no dynamic rules yet)

**Main Routes**:
- `GET/POST /api/v1/properties` - Property management
- `GET/POST/PATCH /api/v1/bookings` - Booking lifecycle
- `GET /api/v1/availability` - Availability queries
- `POST/DELETE /api/v1/availability/blocks` - Manual blocks

**Core Entities/Tables**:
- `properties` - Property listings with location, amenities
- `bookings` - Booking records with status workflow
- `guests` - Guest information
- `availability_blocks` - Manual blocking (maintenance, owner use)
- `inventory_ranges` - Unified inventory tracking (bookings + blocks)
- `agencies` - Multi-tenant organizations
- `team_members` - User-agency assignments

**Status**: ✅ **IMPLEMENTED** (Phase 19-20)

---

### 2. Distribution (Channel Manager)

**Reference Pillar**: Multi-Channel Distribution
**Our Module**: `distribution`

**Scope (Phase 21+ - Modularize)**:
- Bidirectional sync with booking platforms (Airbnb, Booking.com, Expedia, etc.)
- Rate/availability synchronization
- Reservation import/export
- Webhook handling for platform events
- iCal fallback for unsupported platforms

**Main Routes**:
- `GET/POST /api/v1/channel-connections` - Platform connections
- `POST /api/v1/channels/sync` - Manual sync trigger
- `POST /api/v1/webhooks/{platform}` - Webhook receivers

**Core Entities/Tables**:
- `channel_connections` - Connected platforms (OAuth tokens, credentials)
- `channel_sync_logs` - Sync history and errors
- `channel_listings` - Platform-specific listing IDs
- `events` - Event log for auditing

**Status**: 🟡 **PARTIALLY IMPLEMENTED**
- Airbnb adapter exists (`app/channel_manager/adapters/airbnb/`)
- Sync engine framework ready (`app/channel_manager/core/`)
- Other platforms stubbed (Booking.com, Expedia, FewoDirekt, Google)
- **Not yet modularized** - lives in `app/channel_manager/`

**Phase 21 Goal**: Isolate as independent module with clear boundaries

---

### 3. Direct Booking Engine

**Reference Pillar**: Direct Bookings (Website + Booking Flow)
**Our Module**: `direct_booking`

**Scope (Later)**:
- Public-facing property listings (guest view)
- Search/filter properties
- Booking form/widget (check-in/out, guests, payment)
- Custom domain support (multi-tenant white-label)
- SEO optimization (meta tags, sitemaps)

**Main Routes** (Future):
- `GET /listings` - Public property listings
- `GET /listings/{property_slug}` - Property detail page
- `POST /book` - Direct booking submission
- `GET /availability-calendar` - Public calendar widget

**Core Entities/Tables** (Future):
- `public_listings` - SEO-optimized property pages
- `booking_requests` - Inquiry-stage bookings (before confirmation)
- `custom_domains` - Agency custom domain mappings
- `website_settings` - Theme, branding, legal pages

**Status**: ❌ **NOT STARTED**

---

### 4. Guest Experience (Guest Portal)

**Reference Pillar**: Guest Communication & Digital Gästemappe
**Our Module**: `guest_experience`

**Scope (Later)**:
- Guest portal (login, view bookings, documents)
- Digital Gästemappe (house rules, WiFi, check-in instructions)
- Automated email templates (confirmation, reminder, check-in)
- Document uploads (invoices, contracts)

**Main Routes** (Future):
- `GET /guest/portal` - Guest dashboard
- `GET /guest/bookings/{id}` - Booking details
- `GET /guest/documents` - Invoices, contracts
- `POST /guest/messages` - Guest-host messaging

**Core Entities/Tables** (Future):
- `guest_portal_access` - Guest login tokens
- `digital_guides` - Per-property guest guides
- `email_templates` - Automated communication
- `documents` - Uploaded files (invoices, contracts)

**Status**: ❌ **NOT STARTED**

---

### 5. Owner Portal

**Reference Pillar**: Owner Dashboard & Reporting
**Our Module**: `owner_portal`

**Scope (Later)**:
- Owner-specific dashboard (revenue, occupancy)
- Booking calendar (owner view)
- Financial statements (monthly/quarterly)
- Document management (tax docs, contracts)
- Performance reporting (booking trends, ADR, RevPAR)

**Main Routes** (Future):
- `GET /owner/dashboard` - Owner KPIs
- `GET /owner/statements` - Financial statements
- `GET /owner/calendar` - Owner booking calendar
- `GET /owner/reports` - Custom reports

**Core Entities/Tables** (Future):
- `owner_statements` - Monthly/quarterly financials
- `owner_payouts` - Payment records
- `owner_reports` - Saved report configurations

**Status**: ❌ **NOT STARTED**
**Note**: Current RBAC supports `owner` role, but no dedicated portal

---

### 6. Finance & Accounting

**Reference Pillar**: Invoicing, Payments, Commissions
**Our Module**: `finance`

**Scope (Later)**:
- Invoice generation (guest invoices, owner statements)
- Payment tracking (Stripe integration)
- Commission calculation (platform fees, owner splits)
- Tax reporting (VAT, tourist tax)
- Payout management (owner payouts)

**Main Routes** (Future):
- `GET/POST /api/v1/invoices` - Invoice CRUD
- `POST /api/v1/payments` - Payment processing
- `GET /api/v1/statements/{owner_id}` - Owner statements
- `POST /api/v1/payouts` - Trigger payouts

**Core Entities/Tables** (Future):
- `invoices` - Guest invoices
- `payments` - Payment records (Stripe, bank transfer)
- `commissions` - Platform fees, owner splits
- `payouts` - Owner payout history
- `tax_records` - VAT, tourist tax tracking

**Status**: ❌ **NOT STARTED**
**Note**: Basic `payment_status` enum exists in bookings schema

---

## MVP Scope Summary

### Phase 20 (✅ Complete)
- **Core PMS**: Properties, Bookings, Availability/Inventory
- **Multi-Tenancy**: Agency-based isolation with RLS
- **RBAC**: 5 roles (admin, manager, staff, owner, accountant)
- **Database**: PostgreSQL with PostGIS, asyncpg connection pool
- **Conflict Prevention**: EXCLUSION constraints, inventory overlap detection

### Phase 21 (🎯 Current Focus)
**Goal**: Modular Monolith Scaffold (Preparation Only)

**Deliverables**:
1. **Documentation** (this doc + modular-monolith.md + module-system.md)
2. **Module Scaffold**: `app/modules/` structure (NOT wired)
3. **No Functional Changes**: Additive only, no router moves

**NOT in Scope for Phase 21**:
- Moving existing routers
- Refactoring services
- Changing database schema
- Implementing new features
- Channel Manager modularization (deferred to Phase 22+)

---

## Module Dependency Map

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │  Core   │         │ Distrib │         │ Direct  │
   │   PMS   │◄────────│  ution  │         │ Booking │
   └────┬────┘         └────┬────┘         └────┬────┘
        │                   │                    │
        │              ┌────▼────┐         ┌────▼────┐
        │              │  Guest  │         │  Owner  │
        └──────────────►  Exp.   │         │ Portal  │
                       └────┬────┘         └────┬────┘
                            │                   │
                       ┌────▼───────────────────▼────┐
                       │        Finance              │
                       └─────────────────────────────┘

Dependency Rules:
- Core PMS is foundational (no dependencies on other modules)
- Distribution depends on Core PMS (for properties, bookings)
- Direct Booking depends on Core PMS (for availability queries)
- Guest Experience depends on Core PMS + Distribution
- Owner Portal depends on Core PMS + Finance
- Finance is lowest-level (depends on all)
```

---

## Non-Goals for This Commit

**Explicitly NOT Doing**:
1. ❌ Moving existing routers (`app/api/routes/`)
2. ❌ Refactoring services or schemas
3. ❌ Database migrations or schema changes
4. ❌ Implementing new features
5. ❌ Channel Manager modularization (too complex for this phase)
6. ❌ Changing API contracts or endpoints
7. ❌ Activating module registry in `main.py`

**Why Not?**
- Minimize debugging: Additive changes only
- Reduce risk: No functional changes
- Clear separation: Scaffold first, migration later

---

## Success Criteria

Phase 21 is successful when:
1. ✅ Documentation exists for all 6 pillars
2. ✅ `docs/architecture/modular-monolith.md` defines clear module boundaries
3. ✅ `docs/architecture/module-system.md` documents the module registry pattern
4. ✅ `app/modules/` scaffold created (ModuleSpec, Registry)
5. ✅ No existing functionality broken
6. ✅ Tests pass (including new unit tests for registry)
7. ✅ Code committed and deployed via Coolify

---

## References

- **Reference Product Model**: Industry-standard PMS architecture
- **System Architecture**: `docs/architecture/system-architecture.md`
- **Current State**: `CURRENT_STATE.md`
- **Inventory & Availability**: `docs/database/migrations-guide.md` (migration workflow, schema drift SOP)
