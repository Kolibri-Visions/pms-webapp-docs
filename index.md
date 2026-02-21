# PMS-Webapp Documentation Index

**Single Source of Truth**: All documentation lives under `backend/docs/`.

---

## Quick Start

| Goal | Document |
|------|----------|
| New developer onboarding | [START_HERE.md](./START_HERE.md) |
| Understand architecture | [architecture/system-architecture.md](./architecture/system-architecture.md) |
| Operations & troubleshooting | [ops/runbook.md](./ops/runbook.md) |
| Current project status | [project_status.md](./project_status.md) |

---

## Documentation Structure

```
backend/docs/
├── index.md              # This file - canonical entry point
├── START_HERE.md         # Developer onboarding
├── project_status.md     # Project status & recent changes
│
├── architecture/         # Architecture documentation
│   ├── system-architecture.md
│   ├── channel-manager.md
│   ├── module-system.md
│   └── ADRs/             # Architecture Decision Records
│
├── database/             # Database documentation
│   ├── migrations-guide.md
│   ├── data-integrity.md
│   └── index-strategy.md
│
├── frontend/             # Frontend documentation
│   ├── authentication.md
│   └── ops-console.md
│
├── meta/                 # Repository meta-documentation
│   ├── changelog.md
│   ├── contributing.md
│   └── agent_system.md
│
├── ops/                  # Operations documentation
│   ├── runbook.md        # Main runbook index
│   ├── feature-flags.md
│   └── runbook/          # Modular runbook chapters
│       ├── 00-golden-paths.md
│       ├── 01-deployment.md
│       ├── 02-database.md
│       └── ...
│
├── product/              # Product backlog & planning
├── process/              # Development process docs
├── testing/              # Testing documentation
└── ui/                   # UI component documentation
```

---

## Rules

1. **All new documentation** goes under `backend/docs/`.
2. **Runbook additions** go into `backend/docs/ops/runbook/*.md` (modular chapters).
3. **Root-level *.md files** are stubs pointing here.

---

## Key Documents

### Operations
- [Runbook](./ops/runbook.md) - Troubleshooting, deployment, monitoring
- [Feature Flags](./ops/feature-flags.md) - Feature flag configuration

### Architecture
- [System Architecture](./architecture/system-architecture.md) - High-level system design
- [Channel Manager](./architecture/channel-manager.md) - Channel sync architecture
- [Module System](./architecture/module-system.md) - Module registry

### Database
- [Migrations Guide](./database/migrations-guide.md) - Database migration procedures
- [Data Integrity](./database/data-integrity.md) - Integrity constraints
- [Index Strategy](./database/index-strategy.md) - Database indexing

### Product
- [Product Backlog](./product/PRODUCT_BACKLOG.md) - Feature backlog
- [Release Plan](./product/RELEASE_PLAN.md) - Release schedule

---

*Last updated: 2026-02-21*
