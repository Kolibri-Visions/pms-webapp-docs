# PMS-Webapp Status Review v1

**Generated**: 2025-12-30
**Commit**: `393ba8da51b67fdd832b92232c43c524c3edec88`
**Timestamp**: 2025-12-30 17:34:20 UTC
**Purpose**: Code-derived evidence snapshot for PROJECT_STATUS.md alignment

---

## What is this folder?

This staging folder contains a comprehensive, evidence-based analysis of the PMS-Webapp codebase as it exists at commit `393ba8da`. The goal is to create a **PROJECT_STATUS.md** that accurately reflects the actual codebase, not idealized plans or outdated documentation.

## Files in this folder

1. **START_HERE.md** (this file) - Overview and navigation
2. **DOCS_MAP.md** - Inventory of existing documentation
3. **PROJECT_STATUS.md** - Code-derived status report (FROZEN snapshot)
4. **DRIFT_REPORT.md** - Gaps between docs and actual code
5. **MANIFEST.md** - Evidence log (file paths, symbols, timestamps)

## How to use this review

### For developers
- Read **PROJECT_STATUS.md** for a high-level overview of what's actually implemented
- Check **DRIFT_REPORT.md** to see where docs diverge from reality
- Use **MANIFEST.md** to trace any claim back to actual source code

### For project managers
- **PROJECT_STATUS.md** is the single source of truth for "what's done"
- **DRIFT_REPORT.md** highlights where roadmap docs are ahead of/behind reality
- Use this to update roadmap tickets and sprint planning

### For new contributors
- Start with **PROJECT_STATUS.md** to understand the current state
- Read **DOCS_MAP.md** to find relevant documentation
- Cross-reference with **MANIFEST.md** to see actual file locations

## Key findings (summary)

### What's implemented ✅
- **FastAPI backend** with modular router architecture (5 routers)
- **RBAC system** with 5 roles (admin, manager, staff, owner, accountant)
- **Multi-tenancy** via `agency_id` from JWT/headers
- **Typed exceptions** for error taxonomy (Phase 1 - P1-06)
- **Channel Manager** with Celery workers, rate limiting, circuit breaker
- **Availability system** with PostgreSQL EXCLUSION constraints
- **Next.js 15 frontend** with App Router, SSR auth, backoffice UI

### What's planned but not implemented ❌
- Ops endpoints are STUBS (Phase 1 - P1-08, P1-09)
- Error response format not unified yet (Phase 1 - P1-07)
- Audit log, idempotency_keys, agency_features tables (Phase 1 - P1-10, P1-11)
- Full RBAC enforcement on all endpoints (Phase 1 - P1-02, P1-03)

### Documentation drift 📊
- **Phase 1 roadmap** includes items not yet started (P1-07 onwards)
- **Error taxonomy doc** correctly states P1-06 done, P1-07 pending
- **Ops endpoints** have TODO comments referencing Phase 1 tasks

## Next steps

1. **Review**: Team reviews PROJECT_STATUS.md for accuracy
2. **Reconcile**: Update roadmap docs based on DRIFT_REPORT.md findings
3. **Commit**: Move PROJECT_STATUS.md to `backend/docs/` as frozen snapshot
4. **Plan**: Use drift findings to prioritize Phase 1 tickets

## Evidence methodology

All claims in this review are backed by:
- **File reads** (full content extraction, not search)
- **Symbol definitions** (function signatures, class names, API endpoints)
- **Commit metadata** (git log, file timestamps)
- **NO speculation** - if not in code, not in status report

See **MANIFEST.md** for full evidence log.

---

**Questions?** Contact the backend team or file an issue referencing commit `393ba8da`.
