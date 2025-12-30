# Status Review v2 - Manifest

**Purpose**: Document scope, methodology, and verification for status-review-v2

---

## Repository State

- **Commit**: `1c42e9598044a0928462522f58e1a8019ad1737e`
- **Timestamp**: `2025-12-30 20:48:06 UTC`
- **Branch**: `main` (synced with `origin/main`)

**Sync Commands**:
```bash
git fetch origin
git checkout main
git reset --hard origin/main
git rev-parse HEAD  # 1c42e9598044a0928462522f58e1a8019ad1737e
date -u +"%Y-%m-%d %H:%M:%S UTC"  # 2025-12-30 20:48:06 UTC
```

---

## Scope

### Scanned Areas
1. **Backend**:
   - API routers (`app/api/routes/*`, `app/routers/*`)
   - Module system (`app/modules/*`)
   - Auth/RBAC (`app/core/auth.py`, `app/api/deps.py`)
   - Services (`app/services/*`)
   - Database migrations (`supabase/migrations/*`)
   - Configuration (`app/core/config.py`)
   - Health checks (`app/core/health.py`)

2. **Frontend**:
   - App routes (`frontend/app/**/page.tsx`, `frontend/app/**/layout.tsx`)
   - Middleware (`frontend/middleware.ts`)
   - Auth integration (`frontend/app/lib/supabase-server.ts`)

3. **Worker**:
   - Channel manager (`app/channel_manager/*`)
   - Celery tasks (referenced in code)

4. **Docs**:
   - Runbook (`backend/docs/ops/runbook.md`)
   - Roadmap (`backend/docs/roadmap/*`)
   - Architecture (`backend/docs/architecture/*`)

5. **Scripts**:
   - Deployment (`supabase/deploy.sh`)
   - Ops scripts (`backend/scripts/ops/*` - referenced in runbook)

### NOT Scanned
- Third-party agent plugins (`_agents/*`) - excluded per instructions
- Node modules, Python venv
- Git history (only HEAD commit)
- Test execution results (tests NOT run, only inspected)

---

## Methodology

### Read-Only Analysis
- ✅ File reads (`cat`, `Read` tool)
- ✅ Pattern searches (`rg`, `grep`, `find`)
- ✅ Symbol extraction (function/class names from source)
- ❌ No code execution (pytest, ruff, mypy - all skipped)
- ❌ No linters or formatters
- ❌ No test runs

### Evidence Collection Commands

**Router Discovery**:
```bash
rg "router\s*=\s*APIRouter" --type py -A 2
rg "app\.include_router|mount_modules" --type py -A 3
```

**Module System**:
```bash
find backend/app/modules -name "*.py" -type f
cat backend/app/modules/bootstrap.py
cat backend/app/main.py
```

**Frontend Routes**:
```bash
find frontend/app -name "layout.tsx" -o -name "middleware.ts" -o -name "page.tsx"
cat frontend/middleware.ts
cat frontend/app/ops/layout.tsx
```

**RBAC/Auth**:
```bash
rg "require_roles|get_current_role|get_current_agency_id" --type py -l
cat backend/app/api/deps.py
cat backend/app/core/auth.py
```

**Availability/Inventory**:
```bash
ls supabase/migrations | grep -E "(inventory|availability|exclusion)"
```

**Deployment Evidence**:
```bash
find . -name "runbook*" -o -name "deployment*" | grep -E "\.(md|txt|sh)$"
cat backend/docs/ops/runbook.md
```

**Ops Router Status**:
```bash
rg "from.*routers.*ops|import.*ops.*router" --type py -A 2
# Result: No matches (NOT imported/mounted)
```

---

## Files Generated

All files in `backend/docs/_staging/status-review-v2/`:

1. `START_HERE.md` - Navigation, v1 vs v2 comparison
2. `DOCS_MAP.md` - Existing documentation inventory
3. `PROJECT_STATUS.md` - Code-derived status report
4. `DRIFT_REPORT.md` - Docs vs code gaps
5. `MANIFEST.md` - This file (scope + methodology)

**Total**: 5 new markdown files (add-only, no existing files modified)

---

## Evidence Discipline

### Claim Requirements
Every claim in PROJECT_STATUS.md and DRIFT_REPORT.md MUST include:
- **Evidence** section with file paths
- Symbol names (functions, classes, endpoints)
- Line numbers where applicable
- "UNKNOWN" label if not verifiable from code

### Prohibited Practices
- ❌ No speculation about implementation
- ❌ No assumptions about deployment without runbook/script evidence
- ❌ No guessing at API behavior
- ❌ No inventing feature names
- ❌ No "fewoone" or other made-up terms

### Verified vs Unverified
- **Verified**: Found in code, docs, or runbook
- **Unverified**: Mentioned in roadmap but no code evidence
- **Unknown**: Cannot determine from read-only analysis

---

## Verification Checklist

### Human Verification Steps

**1. API Prefix Accuracy**
```bash
# All API routes should show /api/v1 prefix
grep -r "prefix=\"/api/v1\"" backend/app/
grep "app.include_router.*prefix=\"/api/v1\"" backend/app/main.py
```
Expected: Properties, Bookings, Availability mounted under `/api/v1`

**2. Ops Router Mounting**
```bash
# Ops router should NOT be imported anywhere
rg "from.*ops.*router" backend/app --type py
rg "import.*routers\.ops" backend/app --type py
```
Expected: No results (ops router not mounted)

**3. Frontend Middleware**
```bash
# Middleware should apply to /ops/*, /channel-sync/*, /login
grep "matcher:" frontend/middleware.ts -A 5
```
Expected: `matcher: ['/ops/:path*', '/channel-sync/:path*', '/login']`

**4. Frontend Ops Feature Flag**
```bash
# Ops layout should check NEXT_PUBLIC_ENABLE_OPS_CONSOLE
grep "NEXT_PUBLIC_ENABLE_OPS_CONSOLE" frontend/app/ops/layout.tsx
```
Expected: Lines 95-140 (feature flag check)

**5. Module System Feature Flag**
```bash
# Main should check MODULES_ENABLED
grep "MODULES_ENABLED" backend/app/main.py -A 5
```
Expected: Lines 117-136 (module system vs fallback)

**6. Availability EXCLUSION Constraint**
```bash
# Migration should create EXCLUSION constraint
ls supabase/migrations | grep exclusion
```
Expected: `20251229200517_enforce_overlap_prevention_via_exclusion.sql`

**7. Runbook Deployment Evidence**
```bash
# Runbook should have deployment section
grep -i "deployment\|deploy\|production" backend/docs/ops/runbook.md | head -5
```
Expected: DB DNS, network attachment, Coolify deployment

---

## Changes Made

### Code Changes
**NONE** - Read-only analysis only

### Documentation Changes
**Add-Only**:
- Created `backend/docs/_staging/status-review-v2/` folder
- Added 5 new markdown files (listed above)

**NOT Modified**:
- No existing .md files edited
- No existing code files touched
- No existing configs changed
- Existing `backend/docs/_staging/status-review-v1/` preserved

---

## Comparison with v1

### v1 Artifacts (2025-12-30 17:34:20 UTC)
- Commit: `393ba8da51b67fdd832b92232c43c524c3edec88`
- Folder: `backend/docs/_staging/status-review-v1/`
- Files: 5 markdown files

### v2 Artifacts (2025-12-30 20:48:06 UTC)
- Commit: `1c42e9598044a0928462522f58e1a8019ad1737e`
- Folder: `backend/docs/_staging/status-review-v2/`
- Files: 5 markdown files

### Time Difference
- **3 hours 14 minutes** between v1 and v2 generation
- **Same commit** (1c42e95) - v1 was committed, then v2 scanned

### Key Differences
See START_HERE.md "v1 vs v2 Drift Summary" section

---

## Commit Details

**Message**: `docs: add staging status-review v2 (code-derived, add-only)`

**NO Co-Authored-By Trailers** (per instructions)

**Files Added**:
- `backend/docs/_staging/status-review-v2/START_HERE.md`
- `backend/docs/_staging/status-review-v2/DOCS_MAP.md`
- `backend/docs/_staging/status-review-v2/PROJECT_STATUS.md`
- `backend/docs/_staging/status-review-v2/DRIFT_REPORT.md`
- `backend/docs/_staging/status-review-v2/MANIFEST.md`

---

## Next Review

**Trigger**: After Phase 1 completion or major architectural changes
**Scope**: Full rescan (backend + frontend + worker)
**Method**: Same read-only, evidence-based approach

---

**Generated**: 2025-12-30 20:48:06 UTC
**Verified**: Human verification checklist above
**Status**: Add-only (reversible, no code impact)
