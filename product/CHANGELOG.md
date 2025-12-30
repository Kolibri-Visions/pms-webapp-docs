# Changelog

**Purpose**: Track all user-facing changes across releases

**Audience**: Product Owners, Customers, Stakeholders, Developers

**Format**: Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

**Versioning**: [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`)

---

## [Unreleased]

### Added
- Product backlog with 10 epics (A-J)
- Release plan (MVP → Beta → Prod-ready)
- Process documentation (DoD, Docs Lifecycle, Release Cadence)

### Changed
- (None)

### Fixed
- (None)

---

## [0.3.0] - 2025-12-30

### Added
- Comprehensive documentation structure under `backend/docs/`
- Project status documentation (live + historical snapshots)
- Ops runbook with 6 documented failure modes
- Feature flags reference (MODULES_ENABLED, CHANNEL_MANAGER_ENABLED, NEXT_PUBLIC_ENABLE_OPS_CONSOLE)
- Testing guide with server-side smoke test workflow
- Architecture documentation (Module System, Channel Manager, Error Taxonomy)
- Database documentation (Migrations Guide, EXCLUSION Constraints, Index Strategy)
- Frontend documentation (Authentication, Ops Console)

### Changed
- Aligned testing workflow to server-side smoke tests (local pytest optional)
- Softened feature flag boolean parsing claims (recommend `true`/`false`)

### Fixed
- Corrected commit references in status review v3 (3490c89 → 7f34c7d)
- Replaced UNKNOWN placeholders with real staging URLs
- Removed hardcoded migrations list (now uses dynamic command)

---

## [0.2.0] - 2025-12-25

### Added
- Availability inventory system (Phase 17B)
- EXCLUSION constraints for double-booking prevention
- Inventory ranges table (unified availability + bookings)
- Bulk availability upload API
- Channel Manager architecture (adapters, sync engine, circuit breaker)
- Celery workers for async tasks (availability sync, channel sync)
- Feature gating for Channel Manager (`CHANNEL_MANAGER_ENABLED` flag)

### Changed
- Migrated from separate `availability_blocks` + `bookings` to unified `inventory_ranges` table
- Booking creation now inserts into `inventory_ranges` (unified model)

### Fixed
- Double-booking prevention now enforced at database level (EXCLUSION constraint)

---

## [0.1.0] - 2025-12-15

### Added
- Core database schema (agencies, properties, bookings, guests, team_members)
- Multi-tenancy via `agency_id` (RLS policies)
- 5 RBAC roles (admin, manager, staff, owner, accountant)
- JWT authentication (Supabase Auth)
- FastAPI backend with module system
- Health checks (`/health`, `/health/ready`)
- Properties CRUD API (`/api/v1/properties`)
- Bookings CRUD API (`/api/v1/bookings`)
- Next.js frontend with SSR authentication
- Ops Console pages (admin-only, feature flag required)

### Changed
- (None - initial release)

### Fixed
- (None - initial release)

---

## Release Notes Format

Each release follows this structure:

### Added
New features, endpoints, or capabilities

### Changed
Changes to existing functionality (breaking or non-breaking)

### Deprecated
Features marked for removal in future releases

### Removed
Features removed in this release

### Fixed
Bug fixes, security patches

### Security
Security-related changes (CVEs, vulnerability fixes)

---

## Version History Summary

| Version | Release Date | Phase | Description |
|---------|--------------|-------|-------------|
| 0.3.0   | 2025-12-30   | Pre-MVP | Documentation overhaul |
| 0.2.0   | 2025-12-25   | Phase 17B | Availability inventory system |
| 0.1.0   | 2025-12-15   | Foundation | Core PMS functionality |

---

## Upcoming Releases

### [0.4.0] - Planned (Q1 2026)

**Focus**: MVP preparation

**Planned Features**:
- Error taxonomy completion (P1-07)
- Booking status workflow (inquiry → confirmed → checked-out)
- Basic email notifications (booking confirmed)
- Calendar view (frontend, read-only)
- Security audit completion

**Related**: See [RELEASE_PLAN.md](RELEASE_PLAN.md) for MVP details

---

### [1.0.0] - Planned (Q1 2026)

**Focus**: MVP launch

**Planned Features**:
- All MVP acceptance criteria met (see [RELEASE_PLAN.md](RELEASE_PLAN.md))
- Production-ready stability and security
- Complete documentation
- Customer onboarding process

---

### [1.1.0] - Planned (Q2 2026)

**Focus**: Beta launch (Channel Manager + Direct Booking)

**Planned Features**:
- Airbnb adapter (OAuth, sync, webhooks)
- Booking.com adapter
- VRBO/Expedia adapter
- Direct Booking Engine (public property listings, Stripe payment)
- Monitoring dashboards (Prometheus + Grafana)

---

## How to Update This Changelog

**When to Update**: After every user-facing change (per [DoD](../process/DEFINITION_OF_DONE.md))

**Where to Add Changes**:
1. Add change to `[Unreleased]` section during development
2. Move to versioned section when released (per [RELEASE_CADENCE.md](../process/RELEASE_CADENCE.md))

**Commit Message**:
```bash
git commit -m "docs: update CHANGELOG for v0.4.0 - add email notifications"
```

---

## Related Documentation

- [PRODUCT_BACKLOG.md](PRODUCT_BACKLOG.md) - Epic breakdown
- [RELEASE_PLAN.md](RELEASE_PLAN.md) - MVP → Beta → Prod-ready milestones
- [RELEASE_CADENCE.md](../process/RELEASE_CADENCE.md) - Bi-weekly release schedule
- [DEFINITION_OF_DONE.md](../process/DEFINITION_OF_DONE.md) - Includes changelog update requirement

---

**Last Updated**: 2025-12-31
**Maintained By**: Product Owner + Engineering Team
