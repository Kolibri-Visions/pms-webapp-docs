# PMS-Webapp Documentation

**Who Are You? Quick Navigation**

---

## For Ops / DevOps / On-Call

- **[Runbook](ops/runbook.md)** - Troubleshooting guide for production issues
  - **[Top 5 Failure Modes](ops/runbook.md#top-5-failure-modes-and-fixes)** - Quick fixes for common failures
- **[Feature Flags](ops/feature-flags.md)** - Central reference for all feature toggles
- **[Schema Drift SOP](database/migrations-guide.md#schema-drift-sop)** - Step-by-step procedure to detect and fix schema drift
- **[Server-side Smoke Checks](testing/README.md#server-side-smoke-checks-official)** - Official smoke test sequence

## For Product / Planning

- **[Product Backlog](product/PRODUCT_BACKLOG.md)** - Epics with features and open tasks
- **[Release Plan](product/RELEASE_PLAN.md)** - MVP → Beta → Prod-ready milestones
- **[Changelog](product/CHANGELOG.md)** - Release history (user-facing changes)
- **[Definition of Done](process/DEFINITION_OF_DONE.md)** - Task completion criteria
- **[Docs Lifecycle](process/DOCS_LIFECYCLE.md)** - Keep backlog + live status in sync
- **[Deprecation Map](process/DEPRECATION_MAP.md)** - Safe deletion roadmap
- **[Release Cadence](process/RELEASE_CADENCE.md)** - Bi-weekly releases, hotfix process

## For Developers

### Architecture

- **[Architecture Overview](architecture/)** - System design documentation
  - [Error Taxonomy](architecture/error-taxonomy.md) - Error codes, typed exceptions
  - [Module System](architecture/module-system.md) - Module registry, graceful degradation
  - [Modules & Entitlements](architecture/modules-and-entitlements.md) - Module configuration
  - [Channel Manager](architecture/channel-manager.md) - Channel sync architecture

### Database

- **[Database Documentation](database/)** - Schema, migrations, integrity
  - [Data Integrity](database/data-integrity.md) - Constraints, validation rules
  - [Index Strategy](database/index-strategy.md) - Query optimization, indexing
  - [Migrations Guide](database/migrations-guide.md) - How to create/apply migrations
  - [EXCLUSION Constraints](database/exclusion-constraints.md) - Double-booking prevention

### Frontend

- **[Frontend Documentation](frontend/)** - Next.js SSR, authentication, pages
  - [Authentication](frontend/authentication.md) - Supabase SSR, session refresh, role checks
  - [Ops Console](frontend/ops-console.md) - Frontend /ops/* pages (admin-only)

### Testing

- **[Testing Guide](testing/README.md)** - Test organization, workflow (server-side smoke only)

---

## Project Status

➡️ **[project_status.md](project_status.md)** - Current feature status and recent changes

---

## Additional Resources

- **[Product Backlog](product/PRODUCT_BACKLOG.md)** - Epics with features and open tasks
- **[Release Plan](product/RELEASE_PLAN.md)** - MVP → Beta → Prod-ready milestones

---

**Last Updated**: 2026-02-21
**Maintained By**: Backend Team
