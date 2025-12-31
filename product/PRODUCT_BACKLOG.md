# Product Backlog

**Purpose**: Single source of truth for product features and roadmap

**Audience**: Product Owners, Engineering Team, Stakeholders

**Source of Truth**: This file defines all epics, features, and open tasks

---

## Overview

This backlog tracks the PMS-Webapp (Property Management System) product evolution from MVP to production-ready.

**Planning Policy**: This is the single source of truth for planning. Never create roadmap/, tickets/, or phase*.md files (see [DOCS_LIFECYCLE.md](../process/DOCS_LIFECYCLE.md)).

**Backlog Structure**: 10 Epics (A-J) → Features → Tasks

**Status Legend**:
- ✅ **Done**: Implemented and deployed to production
- 🚧 **In Progress**: Actively being developed
- 📋 **Planned**: Scoped and prioritized
- 💡 **Proposed**: Idea stage, not yet scoped

---

## Epic A: Stability & Security

**Outcome**: Production-grade reliability, security hardening, operational visibility

**Scope**: Error handling, monitoring, security audit, infrastructure stability

**Acceptance Criteria / DoD**:
- ✅ All endpoints use typed exceptions (per [Error Taxonomy](../architecture/error-taxonomy.md))
- ✅ Health checks (`/health`, `/health/ready`) return accurate status
- ✅ Runbook covers all known failure modes
- ✅ No secrets in git history
- ✅ JWT validation enforced on all authenticated endpoints
- ✅ RLS policies prevent cross-tenant data leaks

**Status**: 🚧 **In Progress**

**Open Tasks**:
1. 📋 Complete error taxonomy implementation (P1-06 done, P1-07 pending)
2. 📋 Add structured logging (JSON logs with trace IDs)
3. 📋 Implement rate limiting (per-user, per-agency)
4. 📋 Security audit (pen test, vulnerability scan)
5. 📋 Add monitoring/alerting (Prometheus, Grafana, or equivalent)
6. 📋 Database backup/restore procedure documented
7. 📋 Disaster recovery plan documented

**Related Docs**:
- [Error Taxonomy](../architecture/error-taxonomy.md)
- [Runbook](../ops/runbook.md)
- [Feature Flags](../ops/feature-flags.md)

---

## Epic B: Inventory & Availability

**Outcome**: Unified availability system supporting both direct bookings and channel manager

**Scope**: Inventory ranges, availability blocks, EXCLUSION constraints, bulk upload

**Acceptance Criteria / DoD**:
- ✅ Double-booking prevention via EXCLUSION constraint
- ✅ Availability API (`/api/v1/availability`) supports CRUD
- ✅ Inventory ranges track both availability and bookings
- ✅ Bulk availability upload API exists
- ✅ Calendar view in frontend (read-only or editable)

**Status**: ✅ **Done** (Phase 17B)

**Completed Features**:
- ✅ Inventory ranges table with EXCLUSION constraint
- ✅ Availability API endpoints
- ✅ Calendar overlap prevention (database-level)

**Open Tasks**:
1. 📋 Bulk availability upload UI (frontend)
2. 📋 Availability sync with external calendars (iCal import)
3. 📋 Availability forecasting (predict high/low demand periods)

**Related Docs**:
- [EXCLUSION Constraints](../database/exclusion-constraints.md)
- [Migrations Guide](../database/migrations-guide.md)

---

## Epic C: Booking Lifecycle

**Outcome**: Complete booking flow from inquiry to checkout

**Scope**: Booking creation, modification, cancellation, payment tracking, guest communication

**Acceptance Criteria / DoD**:
- ✅ Booking CRUD API (`/api/v1/bookings`)
- ✅ Booking status workflow (inquiry → confirmed → checked-in → checked-out → cancelled)
- ✅ Guest assignment (link booking to guest record)
- ✅ Payment tracking (amount, status, method)
- ✅ Cancellation policy enforcement
- ✅ Email notifications (booking confirmed, check-in reminder, etc.)

**Status**: 🚧 **In Progress**

**Completed Features**:
- ✅ Booking CRUD API
- ✅ Guest table and guest assignment

**Open Tasks**:
1. 📋 Booking status state machine (validate transitions)
2. 📋 Payment integration (Stripe or equivalent)
3. 📋 Cancellation policy rules engine
4. 📋 Email notification system (booking lifecycle events)
5. 📋 SMS notifications (optional, for check-in reminders)
6. 📋 Automated check-in/check-out (smart locks integration)

**Related Docs**:
- [Booking API](../api/) (to be created)
- [Direct Booking Engine](../../direct-booking-engine/) (future)

---

## Epic D: Channel Manager

**Outcome**: Multi-platform sync (Airbnb, Booking.com, VRBO) with unified inventory

**Scope**: Channel adapters, sync engine, webhooks, conflict resolution, feature gating

**Acceptance Criteria / DoD**:
- ✅ Channel Manager architecture documented
- ✅ Airbnb adapter implemented (OAuth, sync, webhooks)
- ✅ Sync engine with circuit breaker, retry logic
- ✅ Webhook signature validation
- ✅ Feature gating via `CHANNEL_MANAGER_ENABLED` flag
- ✅ Sync logs track success/failure per channel
- ✅ Conflict resolution (handle double-bookings from external platforms)

**Status**: 🚧 **In Progress** (Phase 17A-17B)

**Completed Features**:
- ✅ Channel Manager architecture designed
- ✅ Airbnb adapter scaffolded
- ✅ Sync engine with Celery workers
- ✅ Feature flag `CHANNEL_MANAGER_ENABLED`

**Open Tasks**:
1. 📋 Complete Airbnb sync (availability push, booking pull)
2. 📋 Add Booking.com adapter
3. 📋 Add VRBO/Expedia adapter
4. 📋 Conflict resolution UI (show conflicts, allow manual resolution)
5. 📋 Channel performance dashboard (sync success rate, latency)
6. 📋 Channel-specific pricing rules (markup/markdown per channel)

**Related Docs**:
- [Channel Manager Architecture](../architecture/channel-manager.md)
- [Feature Flags - CHANNEL_MANAGER_ENABLED](../ops/feature-flags.md#channel_manager_enabled)

---

## Epic E: Direct Booking Engine

**Outcome**: Public booking website for guests (bypassing OTAs)

**Scope**: Property listings, search/filter, booking flow, payment, confirmation emails

**Acceptance Criteria / DoD**:
- 📋 Public property listing pages (SEO-friendly)
- 📋 Search/filter (dates, location, amenities, price)
- 📋 Booking flow (select dates → guest info → payment → confirmation)
- 📋 Payment gateway integration (Stripe)
- 📋 Confirmation email with booking details
- 📋 Guest portal (view/modify/cancel bookings)

**Status**: 💡 **Proposed**

**Open Tasks**:
1. 💡 Design public booking UI/UX
2. 💡 Implement property listing API
3. 💡 Implement search/filter API
4. 💡 Integrate Stripe payment gateway
5. 💡 Build guest-facing booking form
6. 💡 Email template system (booking confirmation, etc.)
7. 💡 Guest portal (authenticate via email link or password)

**Related Docs**:
- [Direct Booking Engine](../../direct-booking-engine/) (future)

---

## Epic F: Guest Portal

**Outcome**: Self-service portal for guests (view bookings, access check-in info, contact host)

**Scope**: Guest authentication, booking history, check-in instructions, communication

**Acceptance Criteria / DoD**:
- 📋 Guest login (passwordless or password-based)
- 📋 Booking history (upcoming, past bookings)
- 📋 Check-in instructions (address, access codes, house rules)
- 📋 In-app messaging (guest ↔ host)
- 📋 Review submission (post-checkout)

**Status**: 💡 **Proposed**

**Open Tasks**:
1. 💡 Design guest portal UI/UX
2. 💡 Implement guest authentication (magic link or OAuth)
3. 💡 Build booking history view
4. 💡 Add check-in instructions management (admin side)
5. 💡 In-app messaging system
6. 💡 Review/rating submission form

**Related Docs**: (To be created)

---

## Epic G: Owner Portal

**Outcome**: Limited-access portal for property owners (view bookings, revenue, reports)

**Scope**: Owner authentication, booking/revenue views, payout tracking, read-only access

**Acceptance Criteria / DoD**:
- 📋 Owner login (RBAC role: `owner`)
- 📋 Booking calendar (read-only, filtered by owner's properties)
- 📋 Revenue dashboard (bookings, payouts, occupancy rate)
- 📋 Payout tracking (amount owed to owner, payment history)
- 📋 Monthly/quarterly reports (PDF export)

**Status**: 💡 **Proposed**

**Open Tasks**:
1. 💡 Design owner portal UI/UX
2. 💡 Implement RBAC enforcement for `owner` role
3. 💡 Build read-only booking calendar
4. 💡 Build revenue dashboard
5. 💡 Payout tracking system
6. 💡 Report generation (PDF export)

**Related Docs**:
- [RBAC](../_staging/status-review-v3/PROJECT_STATUS.md#rbac-role-based-access-control)

---

## Epic H: Finance & Accounting

**Outcome**: Financial tracking, invoicing, tax reporting, payout management

**Scope**: Revenue tracking, expense tracking, invoicing, tax calculation, payout scheduling

**Acceptance Criteria / DoD**:
- 📋 Revenue tracking (booking revenue, channel fees, platform fees)
- 📋 Expense tracking (cleaning, maintenance, utilities)
- 📋 Invoice generation (for owners, for guests)
- 📋 Tax calculation (VAT, tourism tax, etc.)
- 📋 Payout scheduling (automate owner payouts)
- 📋 Accounting export (CSV/Excel for accountant role)

**Status**: 💡 **Proposed**

**Open Tasks**:
1. 💡 Design finance data model (revenue, expenses, invoices)
2. 💡 Implement revenue tracking API
3. 💡 Implement expense tracking API
4. 💡 Invoice generation system
5. 💡 Tax calculation rules engine
6. 💡 Payout scheduling (automated or manual approval)
7. 💡 Accounting export (CSV/Excel, filtered by date range)

**Related Docs**: (To be created)

---

## Epic I: Ops/Runbook Completeness

**Outcome**: Operational excellence, comprehensive runbook, monitoring, incident response

**Scope**: Runbook coverage, monitoring setup, alerting, incident playbooks, on-call procedures

**Acceptance Criteria / DoD**:
- ✅ Runbook covers all known failure modes
- 📋 Monitoring dashboards (system health, API response times, DB connections)
- 📋 Alerting rules (PagerDuty, Slack, email)
- 📋 Incident response playbooks (DB outage, API degradation, etc.)
- 📋 On-call rotation defined
- 📋 Post-mortem template and process

**Status**: 🚧 **In Progress**

**Completed Features**:
- ✅ Runbook with 6 documented failure modes

**Open Tasks**:
1. 📋 Add monitoring dashboards (Prometheus + Grafana or equivalent)
2. 📋 Define alerting rules (critical vs warning thresholds)
3. 📋 Create incident response playbooks
4. 📋 Define on-call rotation schedule
5. 📋 Post-mortem process and template

**Related Docs**:
- [Runbook](../ops/runbook.md)
- [RELEASE_CADENCE.md](../process/RELEASE_CADENCE.md)

---

## Epic J: Multi-Tenant Scaling & Domains

**Outcome**: Scale to multiple agencies, custom domains, white-label branding

**Scope**: Agency isolation, custom domains, white-label UI, subscription/billing

**Acceptance Criteria / DoD**:
- ✅ Multi-tenancy via `agency_id` (RLS policies enforce isolation)
- 📋 Custom domain support (e.g., `bookings.property-name.com`)
- 📋 White-label branding (agency logo, colors, email templates)
- 📋 Subscription tiers (free, pro, enterprise)
- 📋 Billing system (charge agencies per property or booking)

**Status**: 🚧 **In Progress**

**Completed Features**:
- ✅ Multi-tenancy via `agency_id`
- ✅ RLS policies enforce agency isolation

**Open Tasks**:
1. 📋 Custom domain DNS configuration (CNAME setup, SSL certs)
2. 📋 White-label UI (agency branding settings)
3. 📋 Email template customization (per agency)
4. 📋 Subscription tier system
5. 📋 Billing integration (Stripe Billing or equivalent)
6. 📋 Usage-based pricing (per property, per booking, per sync)

**Related Docs**:
- [Multi-Tenancy](../_staging/status-review-v3/PROJECT_STATUS.md#multi-tenancy)

---

## Prioritization Framework

**How we prioritize epics/features**:

1. **MVP Blockers** (P0): Must-have for initial launch
   - Epic A (Stability & Security)
   - Epic B (Inventory & Availability)
   - Epic C (Booking Lifecycle - core features)

2. **Revenue Drivers** (P1): Features that unlock revenue
   - Epic D (Channel Manager - reduces manual work)
   - Epic E (Direct Booking Engine - reduces OTA fees)

3. **User Experience** (P2): Features that improve usability
   - Epic F (Guest Portal)
   - Epic G (Owner Portal)

4. **Business Operations** (P3): Features that streamline ops
   - Epic H (Finance & Accounting)
   - Epic I (Ops/Runbook Completeness)

5. **Scale & Growth** (P4): Features for long-term growth
   - Epic J (Multi-Tenant Scaling & Domains)

**Current Focus**: MVP (P0) + Channel Manager (P1)

---

## Release Mapping

**See [RELEASE_PLAN.md](RELEASE_PLAN.md) for detailed milestone breakdown**

**Quick Summary**:
- **MVP** (Q1 2026): Epics A, B, C (core features)
- **Beta** (Q2 2026): Epic D (Channel Manager), Epic E (Direct Booking)
- **Prod-Ready** (Q3 2026): Epics F, G, H, I (full feature set)

---

## Backlog Grooming

**Quarterly Review** (every 3 months):
1. Re-prioritize epics based on business needs
2. Break down high-priority epics into features/tasks
3. Archive completed epics
4. Update status (Done, In Progress, Planned, Proposed)

**Owned By**: Product Owner + Tech Lead

---

## Related Documentation

- [RELEASE_PLAN.md](RELEASE_PLAN.md) - MVP → Beta → Prod-ready milestones
- [CHANGELOG.md](CHANGELOG.md) - Release history
- [DEFINITION_OF_DONE.md](../process/DEFINITION_OF_DONE.md) - Task completion criteria
- [Runbook](../ops/runbook.md) - Operational guide

---

**Last Updated**: 2025-12-31
**Maintained By**: Product Owner + Engineering Team
