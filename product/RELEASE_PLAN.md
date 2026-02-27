# Release Plan

**Purpose**: Define MVP → Beta → Prod-ready milestones and timeline

**Audience**: Product Owners, Engineering Team, Stakeholders, Investors

**Source of Truth**: This file defines release phases and what's included in each

---

## Overview

**Release Strategy**: Phased rollout from MVP → Beta → Production-Ready

**Timeline**: Q1 2026 (MVP) → Q2 2026 (Beta) → Q3 2026 (Prod-Ready)

**Current Phase**: ✅ **Produktionsreif (85%)** - Core PMS funktionsfähig, Admin-UI vollständig

---

## Release Phases

### Phase 0: Foundation (Complete)

**Goal**: Core infrastructure, database schema, authentication

**Status**: ✅ **Done**

**What's Included**:
- ✅ FastAPI backend with module system
- ✅ PostgreSQL/Supabase database (16 migrations applied)
- ✅ Supabase Auth (SSR, JWT validation)
- ✅ Multi-tenancy via `agency_id` (RLS policies)
- ✅ 5 RBAC roles (admin, manager, staff, owner, accountant)
- ✅ Health checks (`/health`, `/health/ready`)
- ✅ Basic CRUD APIs (properties, bookings)
- ✅ Celery workers + Redis broker
- ✅ Docker containerization (Coolify deployment)

**Infrastructure**:
- Backend API: https://api.fewo.kolibri-visions.de
- Frontend Admin UI: https://admin.fewo.kolibri-visions.de
- Supabase Gateway: https://sb-pms.kolibri-visions.de

**Related Docs**: [PROJECT_STATUS_LIVE.md](../PROJECT_STATUS_LIVE.md)

---

## Phase 1: MVP (Minimum Viable Product)

**Target Date**: Q1 2026 (End of March 2026)

**Goal**: Core booking functionality for single agency (manual operations)

**Status**: ✅ **Erreicht** (Stand: Februar 2026)

---

### What's Included (MVP)

#### Epic A: Stability & Security (MVP Subset)
- ✅ Typed exceptions (error taxonomy vollständig)
- ✅ Structured logging (JSON logs mit trace IDs)
- ✅ Security audit (CSP, CORS, JWT-Validierung)
- ✅ Session-Management mit Revocation

#### Epic B: Inventory & Availability (MVP Subset)
- ✅ Availability API (`/api/v1/availability`)
- ✅ EXCLUSION constraints (double-booking prevention)
- ✅ Calendar view (frontend, interaktiv)
- ✅ Rate Plans & Seasons

#### Epic C: Booking Lifecycle (MVP Subset)
- ✅ Booking CRUD API
- ✅ Guest assignment
- ✅ Booking status workflow (inquiry → confirmed → checked-out)
- ✅ E-Mail Notifications (Resend-Integration)
- ✅ Buchungsanfragen (öffentliches Formular)

---

### Was noch aussteht (Beta/Prod-Ready)

- 🚧 Channel Manager (Epic D) - Architektur vorhanden, Adapter ausstehend
- 📋 Direct Booking Engine (Epic E) - Öffentliche Website geplant
- ✅ Owner Portal (Epic G) - Basis implementiert (owner RBAC-Rolle)
- 🚧 Finance/Accounting (Epic H) - Kurtaxe-System implementiert
- 🚧 Multi-Tenant Branding (Epic J) - White-Label-Branding implementiert

---

### MVP Acceptance Criteria

**Functional**:
- ✅ Admin user can create agency, properties, bookings
- ✅ Double-booking prevention works (database-level)
- ✅ Booking workflow: create → confirm → check-out
- ✅ Email sent on booking confirmation
- ✅ Calendar view shows availability (read-only)

**Technical**:
- ✅ All API endpoints return typed exceptions (per error taxonomy)
- ✅ Health checks pass (`/health`, `/health/ready`)
- ✅ Smoke tests pass on staging and production
- ✅ RLS policies enforce multi-tenancy (no data leaks)
- ✅ JWT validation on all authenticated endpoints

**Operational**:
- ✅ Runbook covers all known failure modes
- ✅ Deployment to staging is automated (CI/CD)
- ✅ Deployment to production is documented
- ✅ Rollback procedure tested

**Documentation**:
- ✅ All MVP features documented in [PRODUCT_BACKLOG.md](PRODUCT_BACKLOG.md)
- ✅ API documentation updated
- ✅ Runbook updated

---

### MVP Launch Checklist

**Before declaring MVP complete**:

- ✅ All MVP acceptance criteria met
- ✅ Security audit completed (no P0/P1 vulnerabilities)
- ✅ Load testing (simulate 100 concurrent users)
- ✅ Backup/restore tested
- ✅ Disaster recovery plan documented
- ✅ Customer onboarding process defined
- ✅ Support SLA defined (response time, escalation)

---

## Phase 2: Beta (Feature Expansion)

**Target Date**: Q2 2026 (End of June 2026)

**Goal**: Channel Manager integration + Direct Booking Engine (reduce manual work, increase bookings)

**Status**: 📋 **Planned**

---

### What's Included (Beta)

#### Epic D: Channel Manager (Beta Focus)
- 📋 Airbnb adapter (OAuth, sync, webhooks)
- 📋 Booking.com adapter
- 📋 VRBO/Expedia adapter
- 📋 Sync engine with conflict resolution
- 📋 Channel performance dashboard

#### Epic E: Direct Booking Engine (Beta Focus)
- 📋 Public property listing pages
- 📋 Search/filter (dates, location, price)
- 📋 Booking flow (select dates → guest info → payment → confirmation)
- 📋 Stripe payment integration
- 📋 Confirmation emails

#### Epic A: Stability & Security (Beta Improvements)
- 📋 Rate limiting (per-user, per-agency)
- 📋 Monitoring dashboards (Prometheus + Grafana)
- 📋 Alerting rules (PagerDuty or Slack)

#### Epic C: Booking Lifecycle (Beta Improvements)
- 📋 Payment tracking (Stripe integration)
- 📋 Cancellation policy enforcement
- 📋 SMS notifications (check-in reminders)

---

### Beta Acceptance Criteria

**Functional**:
- 📋 Channel Manager syncs availability to Airbnb/Booking.com/VRBO
- 📋 Bookings from external channels appear in PMS
- 📋 Direct booking website accepts bookings (payment via Stripe)
- 📋 No double-bookings across channels (conflict resolution works)

**Technical**:
- 📋 Sync success rate > 95% (channel manager)
- 📋 Payment success rate > 99% (Stripe integration)
- 📋 API response time < 500ms (p95)
- 📋 Monitoring dashboards show system health

**Operational**:
- 📋 Runbook updated with channel manager failure modes
- 📋 On-call rotation defined
- 📋 Incident response playbooks created

**Documentation**:
- 📋 Channel Manager docs complete
- 📋 Direct Booking Engine docs complete
- 📋 API docs updated

---

## Phase 3: Production-Ready (Full Feature Set)

**Target Date**: Q3 2026 (End of September 2026)

**Goal**: Enterprise-grade feature set (guest portal, owner portal, finance, scaling)

**Status**: 💡 **Proposed**

---

### What's Included (Prod-Ready)

#### Epic F: Guest Portal
- 💡 Guest login (passwordless or password-based)
- 💡 Booking history (upcoming, past bookings)
- 💡 Check-in instructions
- 💡 In-app messaging (guest ↔ host)
- 💡 Review submission (post-checkout)

#### Epic G: Owner Portal
- 💡 Owner login (RBAC role: `owner`)
- 💡 Booking calendar (read-only, filtered by owner's properties)
- 💡 Revenue dashboard (bookings, payouts, occupancy)
- 💡 Payout tracking
- 💡 Monthly/quarterly reports (PDF export)

#### Epic H: Finance & Accounting
- 💡 Revenue tracking (booking revenue, channel fees)
- 💡 Expense tracking (cleaning, maintenance)
- 💡 Invoice generation
- 💡 Tax calculation (VAT, tourism tax)
- 💡 Payout scheduling (automate owner payouts)
- 💡 Accounting export (CSV/Excel for accountant role)

#### Epic I: Ops/Runbook Completeness
- 💡 Monitoring dashboards (system health, API response times)
- 💡 Alerting rules (critical vs warning thresholds)
- 💡 Incident response playbooks
- 💡 On-call rotation schedule
- 💡 Post-mortem process and template

#### Epic J: Multi-Tenant Scaling & Domains
- 💡 Custom domain support (e.g., `bookings.property-name.com`)
- 💡 White-label branding (agency logo, colors)
- 💡 Email template customization (per agency)
- 💡 Subscription tiers (free, pro, enterprise)
- 💡 Billing integration (Stripe Billing)

---

### Prod-Ready Acceptance Criteria

**Functional**:
- 💡 Guests can self-service (view bookings, check-in info, message host)
- 💡 Owners can track revenue and payouts
- 💡 Accountant role can export financial data
- 💡 Agencies can use custom domains and branding
- 💡 Billing system charges agencies per subscription tier

**Technical**:
- 💡 System uptime > 99.9% (SLA)
- 💡 API response time < 200ms (p95)
- 💡 Database query performance optimized (no N+1 queries)
- 💡 Horizontal scaling tested (multiple backend instances)

**Operational**:
- 💡 24/7 on-call coverage
- 💡 Incident response time < 15 minutes (P0)
- 💡 Post-mortem process in place (all incidents reviewed)

**Documentation**:
- 💡 All features documented
- 💡 Runbook covers 100% of known failure modes
- 💡 Customer-facing help docs published

---

## Release Timeline (Visual)

```
2025-12-31
    |
    ├─── Foundation (Phase 0) ✅ Done
    |
2026-01-31
    |
    ├─── MVP Development (Phase 1) ✅ Done
    |    - Stability & Security ✅
    |    - Inventory & Availability ✅
    |    - Booking Lifecycle ✅
    |    - E-Mail System ✅
    |    - Kurtaxe-System ✅
    |    - Branding/Theming ✅
    |
2026-02-27 (Heute)
    |
    ├─── MVP Produktionsreif 🚀 (85%)
    |
2026-04-01
    |
    ├─── Beta Development (Phase 2) 📋 Planned
    |    - Channel Manager (Airbnb, Booking.com, VRBO)
    |    - Direct Booking Engine (Stripe integration)
    |
2026-06-30 (Q2 End)
    |
    ├─── Beta Launch 🚀
    |
2026-07-01
    |
    ├─── Prod-Ready Development (Phase 3) 💡 Proposed
    |    - Guest Portal, Owner Portal
    |    - Finance/Accounting
    |    - Multi-Tenant Scaling
    |
2026-09-30 (Q3 End)
    |
    └─── Production-Ready Launch 🚀
```

---

## Risk Mitigation

### MVP Risks

**Risk**: Security vulnerabilities found late in MVP development
**Mitigation**: Security audit scheduled for 2026-02-28 (1 month before launch)

**Risk**: Double-booking edge cases not covered by EXCLUSION constraint
**Mitigation**: Extensive integration testing, manual QA with concurrent booking scenarios

**Risk**: Performance degradation under load
**Mitigation**: Load testing scheduled for 2026-03-15 (2 weeks before launch)

---

### Beta Risks

**Risk**: Channel Manager sync failures (API rate limits, auth issues)
**Mitigation**: Circuit breaker, exponential backoff, comprehensive logging

**Risk**: Stripe payment failures (network issues, fraud detection)
**Mitigation**: Retry logic, webhook verification, fallback to manual payment

**Risk**: Conflict resolution complexity (multiple channels book same dates)
**Mitigation**: Conservative availability buffer, manual conflict resolution UI

---

### Prod-Ready Risks

**Risk**: Scaling bottlenecks (database, API, Redis)
**Mitigation**: Horizontal scaling tested in Beta, database connection pooling tuned

**Risk**: Custom domain setup complexity (DNS, SSL certs)
**Mitigation**: Automated DNS/SSL provisioning (Let's Encrypt), clear docs for agencies

**Risk**: Billing integration bugs (overcharging, undercharging)
**Mitigation**: Extensive billing tests, manual review before first charge

---

## Success Metrics

### MVP Success Criteria

- ✅ 5 agencies onboarded and actively using PMS
- ✅ 100+ bookings created via PMS
- ✅ 0 data leaks (multi-tenancy working)
- ✅ < 5% bug escape rate (bugs found in production vs staging)

---

### Beta Success Criteria

- 📋 50+ agencies using Channel Manager
- 📋 1000+ bookings synced from external channels
- 📋 10+ direct bookings via Direct Booking Engine
- 📋 > 95% sync success rate (Channel Manager)

---

### Prod-Ready Success Criteria

- 💡 200+ agencies on platform
- 💡 10,000+ bookings processed
- 💡 > 99.9% uptime (SLA met)
- 💡 < 1% churn rate (agencies leaving platform)

---

## Go/No-Go Decision Criteria

**Before each release**, verify:

### MVP Go/No-Go

- ✅ All MVP acceptance criteria met
- ✅ Security audit passed (no P0/P1 vulnerabilities)
- ✅ Load testing passed (100 concurrent users, < 500ms response time)
- ✅ Disaster recovery tested (backup/restore works)
- ✅ Customer support team trained
- ✅ Onboarding materials ready

**Decision Maker**: Product Owner + Tech Lead

---

### Beta Go/No-Go

- 📋 All Beta acceptance criteria met
- 📋 Channel Manager sync success rate > 95% (in staging)
- 📋 Stripe payment success rate > 99% (in staging)
- 📋 No P0/P1 bugs in backlog
- 📋 Monitoring dashboards operational

**Decision Maker**: Product Owner + Tech Lead

---

### Prod-Ready Go/No-Go

- 💡 All Prod-Ready acceptance criteria met
- 💡 Uptime SLA met in Beta (> 99.5%)
- 💡 Customer satisfaction score > 4.0/5.0
- 💡 No critical incidents in last 30 days
- 💡 On-call rotation staffed

**Decision Maker**: CEO + Product Owner + Tech Lead

---

## Related Documentation

- [PRODUCT_BACKLOG.md](PRODUCT_BACKLOG.md) - Epic breakdown and prioritization
- [CHANGELOG.md](CHANGELOG.md) - Release history
- [DEFINITION_OF_DONE.md](../process/DEFINITION_OF_DONE.md) - Task completion criteria
- [RELEASE_CADENCE.md](../process/RELEASE_CADENCE.md) - Bi-weekly release schedule
- [Runbook](../ops/runbook.md) - Operational guide

---

**Last Updated**: 2026-02-27
**Maintained By**: Product Owner + Engineering Team
