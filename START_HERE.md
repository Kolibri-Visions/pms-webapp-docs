# PMS-Webapp Documentation

**Who Are You? Quick Navigation**

---

## For Ops / DevOps / On-Call

- **[Runbook](ops/runbook.md)** - Troubleshooting guide for production issues (DB DNS, token validation, schema drift)
- **[Feature Flags](ops/feature-flags.md)** - Central reference for all feature toggles (MODULES_ENABLED, CHANNEL_MANAGER_ENABLED, etc.)
- **[Live Status](PROJECT_STATUS_LIVE.md)** - Current staging/deploy reality (what's running now, known issues)

## For Developers

### Architecture

- **[Architecture Overview](architecture/)** - System design documentation
  - [Error Taxonomy](architecture/error-taxonomy.md) - Error codes, typed exceptions (P1-06 done, P1-07 pending)
  - [Module System](architecture/module-system.md) - Module registry, graceful degradation, MODULES_ENABLED flag
  - [Modules & Entitlements](architecture/modules-and-entitlements.md) - Module configuration, entitlements
  - [Channel Manager](architecture/channel-manager.md) - Channel sync architecture (adapters, sync engine, feature gating)

### Database

- **[Database Documentation](database/)** - Schema, migrations, integrity
  - [Data Integrity](database/data-integrity.md) - Constraints, validation rules
  - [Index Strategy](database/index-strategy.md) - Query optimization, indexing
  - [Migrations Guide](database/migrations-guide.md) - How to create/apply migrations
  - [EXCLUSION Constraints](database/exclusion-constraints.md) - Double-booking prevention with PostgreSQL EXCLUSION

### Frontend

- **[Frontend Documentation](frontend/)** - Next.js SSR, authentication, pages
  - [Authentication](frontend/authentication.md) - Supabase SSR, session refresh, role checks
  - [Ops Console](frontend/ops-console.md) - Frontend /ops/* pages (admin-only, feature flag required)

### Testing

- **[Testing Guide](testing/README.md)** - Test organization, workflow (no local tests; server-side smoke only)

---

## Project Status

### Live Status (Current Staging/Deploy)

➡️ **[PROJECT_STATUS_LIVE.md](PROJECT_STATUS_LIVE.md)** - What is deployed NOW (manually maintained)

### Historical Snapshots (Code-Derived)

📸 **[_staging/status-review-v3/PROJECT_STATUS.md](_staging/status-review-v3/PROJECT_STATUS.md)** - Code-derived snapshot (commit `3490c89`, 2025-12-30 21:01 UTC)

**Important Note**:
- `_staging/status-review-v3/*` is a **historical, code-derived snapshot** (commit-bound, read-only).
- `PROJECT_STATUS_LIVE.md` reflects **current staging/deploy reality** (manually maintained).

---

## Additional Resources

- **[Roadmap](roadmap/)** - Phase planning (phase-1 through phase-5)
- **[Tickets](tickets/)** - Phase task breakdown
- **[Direct Booking Engine](direct-booking-engine/)** - Stripe integration, email templates (future feature)
- **[Channel Manager Docs](channel-manager/)** - Channel-specific documentation

---

**Last Updated**: 2025-12-30
**Maintained By**: Backend Team
