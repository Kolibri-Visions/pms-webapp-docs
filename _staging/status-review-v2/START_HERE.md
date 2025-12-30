# Status Review v2 - Start Here

**Review Type**: Code-derived comprehensive scan (read-only analysis)
**Scope**: Backend + Frontend + Worker + Scripts + Docs
**Method**: Evidence-based (no speculation, no code execution)

---

## Repository Snapshot

- **Reviewed Commit**: `1c42e9598044a0928462522f58e1a8019ad1737e`
- **Generated At**: `2025-12-30 20:48:06 UTC`
- **Scope Scanned**: backend + frontend + worker + scripts (read-only)

---

## What Changed from v1 to v2?

### v1 Issues (2025-12-30 17:34:20 UTC, commit `393ba8da`)
1. **API prefix errors**: v1 missed that all API routes are mounted under `/api/v1`
2. **Ops router not mounted**: v1 listed ops endpoints as "implemented" but they're NOT mounted in module system
3. **Frontend vs backend routes confused**: v1 didn't distinguish frontend /ops/* pages from backend /ops/* API
4. **Module system overlooked**: v1 didn't document MODULES_ENABLED flag and module registry
5. **Frontend feature flags missed**: v1 didn't document NEXT_PUBLIC_ENABLE_OPS_CONSOLE requirement

### v2 Improvements
- ✅ **Correct API paths**: All backend API routes documented with `/api/v1` prefix
- ✅ **Ops router status clarified**: Backend `/ops/*` router exists but NOT MOUNTED (dead code)
- ✅ **Frontend vs backend separated**: Clear distinction between frontend pages and backend API
- ✅ **Module system documented**: MODULES_ENABLED, module registry, graceful degradation
- ✅ **Frontend feature flags**: NEXT_PUBLIC_ENABLE_OPS_CONSOLE requirement documented
- ✅ **Runbook evidence included**: Deployment facts sourced from backend/docs/ops/runbook.md

---

## Files in This Review

1. **START_HERE.md** (this file) - Navigation and v1 vs v2 comparison
2. **DOCS_MAP.md** - Inventory of existing documentation with links
3. **PROJECT_STATUS.md** - Code-derived status with 3-axis matrix (Implemented/Wired/Verified)
4. **DRIFT_REPORT.md** - Docs vs code mismatches + v1 vs v2 drift analysis
5. **MANIFEST.md** - Scope, scan commands, verification checklist

---

## Critical Findings

### Backend API
- **All routes mount under `/api/v1`** (not root)
- Properties: `/api/v1/properties/*`
- Bookings: `/api/v1/bookings/*`
- Availability: `/api/v1/availability/*`
- Health: `/health` (NO `/api/v1` prefix)

**Evidence**: `backend/app/main.py:134-136`, `backend/app/modules/bootstrap.py`

### Ops Endpoints NOT MOUNTED
- Backend `app/routers/ops.py` exists with 2 endpoints
- BUT: NOT registered in module system
- NOT imported in `main.py` or any module
- **Status**: Dead code (not accessible via HTTP)

**Evidence**: `rg "from.*ops.*router" backend --type py` returns no results

### Frontend Ops Console
- Frontend `/ops/*` pages ARE implemented (Next.js SSR)
- Server-side admin role check in `app/ops/layout.tsx`
- Requires `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1` env var
- Middleware refreshes session cookies

**Evidence**: `frontend/app/ops/layout.tsx:94-140`, `frontend/middleware.ts:71-76`

### Module System
- Feature flag: `MODULES_ENABLED` (default: true)
- Graceful degradation if module import fails
- Channel Manager module gated by `CHANNEL_MANAGER_ENABLED` (default: false)

**Evidence**: `backend/app/main.py:117-136`, `backend/app/modules/bootstrap.py:86-94`

---

## How to Read This Review

### For Quick Status Check
1. Read **PROJECT_STATUS.md** summary table
2. Check **DRIFT_REPORT.md** for known gaps

### For Evidence Verification
1. Review **MANIFEST.md** for scan methodology
2. All claims in PROJECT_STATUS.md include "Evidence:" sections with file paths

### For Documentation Updates
1. Compare **DRIFT_REPORT.md** findings with existing docs
2. Use evidence to update roadmaps/tickets

---

## v1 vs v2 Drift Summary

| Area | v1 Status | v2 Status | Impact |
|------|-----------|-----------|--------|
| API paths | Incorrect (missing `/api/v1`) | Correct | HIGH - API docs need updates |
| Backend ops router | "Implemented" | "Exists but NOT MOUNTED" | HIGH - Dead code |
| Frontend ops console | Not mentioned | "Implemented with SSR auth + feature flag" | MEDIUM - Ops surface unclear |
| Module system | Not documented | "Active with feature flags" | MEDIUM - Deployment config missing |
| Health endpoint | Correct (`/health`) | Correct (no prefix) | NONE |

---

## Next Steps

1. **Update API documentation** to reflect `/api/v1` prefix
2. **Decision on ops router**: Mount it OR delete dead code
3. **Document feature flags**: MODULES_ENABLED, CHANNEL_MANAGER_ENABLED, NEXT_PUBLIC_ENABLE_OPS_CONSOLE
4. **Frontend/backend clarity**: Update docs to distinguish /ops/* pages vs /ops/* API

---

**Last Updated**: 2025-12-30 20:48:06 UTC
**Review Owner**: Backend Team
**Status**: Add-only (no code changes, no existing doc edits)
