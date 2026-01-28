# PMS-Webapp Documentation Index

**Single Source of Truth**: All documentation lives under `backend/docs/`.

---

## Quick Start

| Goal | Document |
|------|----------|
| New developer onboarding | [START_HERE.md](./START_HERE.md) |
| Run the system locally | [meta/readme.md](./meta/readme.md) |
| Understand architecture | [architecture.md](./architecture.md) |
| Operations & troubleshooting | [ops/runbook.md](./ops/runbook.md) |

---

## Documentation Structure

```
backend/docs/
├── index.md              # This file - canonical entry point
├── START_HERE.md         # Developer onboarding
├── architecture.md       # System architecture overview
├── project_status.md     # Project status & phase tracking
│
├── meta/                 # Repository meta-documentation
│   ├── readme.md         # Project overview (was root README.md)
│   ├── changelog.md      # Version history
│   ├── contributing.md   # Contribution guidelines
│   ├── current_state.md  # Current system state
│   └── agent_system.md   # AI agent documentation
│
├── ops/                  # Operations documentation
│   ├── runbook.md        # Main runbook (legacy, large)
│   └── runbook/          # Modular runbook chapters (new content here)
│       ├── 00-golden-paths.md
│       ├── 01-deployment.md
│       ├── 02-database.md
│       ├── 03-auth.md
│       └── ...
│
├── design/               # UI/UX design documentation
├── database/             # Database documentation
├── frontend/             # Frontend documentation
├── channel-manager/      # Channel manager documentation
├── direct-booking-engine/ # Direct booking documentation
├── product/              # Product backlog & planning
├── testing/              # Testing documentation
└── ui/                   # UI component documentation
```

---

## Rules

1. **All new documentation** goes under `backend/docs/`.
2. **Runbook additions** go into `backend/docs/ops/runbook/*.md` (modular chapters).
3. **Root-level *.md files** are stubs pointing here.
4. **Design docs** live in `backend/docs/design/`.

---

## Key Documents

### Operations
- [Runbook](./ops/runbook.md) - Troubleshooting, deployment, monitoring
- [Feature Flags](./ops/feature-flags.md) - Feature flag configuration

### Architecture
- [System Architecture](./architecture.md) - High-level system design
- [Channel Manager](./channel-manager/channel-manager-architecture.md) - Channel integration
- [Direct Booking Flow](./direct-booking-engine/direct-booking-flow.md) - Booking engine

### Database
- [Migrations Guide](./database/migrations-guide.md) - Database migration procedures
- [Data Integrity](./database/data-integrity.md) - Integrity constraints
- [Index Strategy](./database/index-strategy.md) - Database indexing

### Product
- [Product Backlog](./product/PRODUCT_BACKLOG.md) - Feature backlog
- [Release Plan](./product/RELEASE_PLAN.md) - Release schedule

---

*Last updated: 2026-01-28*
