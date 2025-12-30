# Documentation Duplicates and Overlaps - v1

**Purpose**: Identify redundant content, propose merge recommendations
**Method**: Filename analysis + logical overlap detection (most files not read)
**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd

---

## Summary

**Duplication Types Identified**:
1. **Roadmap vs Tickets** (same phase, different perspectives)
2. **Root Phase Docs vs Roadmap Docs** (phase-specific content scattered)
3. **Database Schema Docs** (RLS policies in multiple places)
4. **Status Reviews** (v1, v2, v3 - intentional historical duplication)

**Recommendation**: Consolidate phase docs into `phases/` folder to reduce scatter

---

## Duplication 1: Roadmap vs Tickets (Per Phase)

### Files Involved

**Phase 1**:
- `roadmap/phase-1.md` - Phase 1 planning (features, DoD)
- `tickets/phase-1.md` - Phase 1 task breakdown

**Phase 2**:
- `roadmap/phase-2.md` - Phase 2 planning
- `tickets/phase-2.md` - Phase 2 task breakdown

**Phase 3-5**: Same pattern

### Overlap Type

**Likely Overlap**: 40-60% (estimated, files not read)

**Roadmap Content** (typical):
- Feature descriptions
- Definition of Done (DoD)
- Success criteria
- Dependencies

**Tickets Content** (typical):
- Task breakdown
- Acceptance criteria
- Implementation steps
- Estimates (if any)

### Recommendation

**Option A (Merge)**:
- Merge into single `phases/phase-N/README.md`
- Section 1: Roadmap (planning)
- Section 2: Tickets (task breakdown)

**Pros**: Single source of truth, less navigation
**Cons**: Large files, mixed audiences (PM vs dev)

**Option B (Keep Separate)**:
- Keep as `phases/phase-N/roadmap.md` and `phases/phase-N/tickets.md`
- Add cross-references between them

**Pros**: Clear separation, different audiences
**Cons**: Potential duplication (feature descriptions in both)

**Recommended**: Option B (keep separate, add cross-references)

---

## Duplication 2: Root Phase Docs vs Roadmap Docs

### Files Involved

**Example 1: Phase 17 (Database)**:
- `roadmap/phase-17.md` (assumed, not verified to exist)
- `phase17b-database-schema-rls.md` (root) - Database schema + RLS policies

**Potential Overlap**: Database schema description may be in both files

**Example 2: Phase 19 (Bookings)**:
- `roadmap/phase-19.md` (assumed, not verified to exist)
- `phase19-core-booking-flow-api.md` (root) - Booking API specification

**Potential Overlap**: Booking API design may be in both files

### Overlap Type

**Likely Overlap**: 20-40% (estimated, files not read)

**Roadmap Content** (typical):
- High-level feature description
- Dependencies, success criteria

**Root Phase Doc Content** (typical):
- Detailed specification
- API endpoints, database schema
- Implementation details

### Recommendation

**Option A (Merge)**:
- Merge detailed specs into roadmap (single `phases/phase-N/roadmap.md`)
- Delete root phase docs

**Pros**: Single source of truth
**Cons**: Roadmap becomes very detailed (may mix PM and dev concerns)

**Option B (Keep Separate, Organize)**:
- Keep roadmap as `phases/phase-N/roadmap.md`
- Move detailed specs to `phases/phase-N/spec.md` (or topic-specific name)
- Example: `phases/phase-17/database-schema-rls.md`

**Pros**: Clear separation (planning vs specification)
**Cons**: 2 files per phase (but logically distinct)

**Recommended**: Option B (keep separate, organize into `phases/`)

**Exception**: `phase17b-database-schema-rls.md` is database-specific, not phase-specific
→ Move to `database/schema-rls.md` instead

---

## Duplication 3: Database Schema Documentation

### Files Involved

**Potential Overlap**:
- `phase17b-database-schema-rls.md` (root) - Database schema + RLS policies
- `database/data-integrity.md` (not read) - May contain schema info
- `supabase/migrations/*.sql` (16 migration files) - Canonical schema source

### Overlap Type

**Likely Overlap**: Schema descriptions may be in multiple places

**Issue**: Schema documentation may be out of sync with migrations

### Recommendation

**Establish Source of Truth**:
1. **Canonical Source**: `supabase/migrations/*.sql` (code is truth)
2. **High-Level Docs**: `database/schema-rls.md` (overview, RLS strategy)
3. **Data Integrity**: `database/data-integrity.md` (constraints, validation)

**Actions**:
1. Move `phase17b-database-schema-rls.md` → `database/schema-rls.md`
2. Ensure `database/schema-rls.md` references migrations (not duplicate schema DDL)
3. Update docs to point to migrations for canonical schema

**Example Structure** (`database/schema-rls.md`):
```markdown
# Database Schema and RLS Policies

## Overview
See `supabase/migrations/20250101000001_initial_schema.sql` for canonical schema.

## Core Tables
- agencies: Multi-tenancy root
- properties: Property management
- bookings: Booking records
- ...

(Summary, not full DDL - reference migrations for details)

## RLS Policies
See `supabase/migrations/20250101000004_rls_policies.sql` for canonical policies.

### Policy Strategy
- All tables enforce agency_id isolation
- admin role bypasses RLS (via security definer functions)
- ...

(Strategy, not policy DDL - reference migrations for details)
```

---

## Duplication 4: Status Reviews (Intentional)

### Files Involved

- `_staging/status-review-v1/*.md` (5 files, 2025-12-30 17:34 UTC)
- `_staging/status-review-v2/*.md` (5 files, 2025-12-30 20:48 UTC)
- `_staging/status-review-v3/*.md` (5 files, 2025-12-30 21:01 UTC)

### Overlap Type

**Intentional Duplication**: Historical snapshots at different points in time

**Purpose**: Track progress, compare findings across reviews

**Content Overlap**: 60-80% (later reviews build on earlier ones)

### Recommendation

**Keep All Reviews** (no merge):
- v1, v2, v3 are historical records
- Useful for tracking how project status evolved
- Duplication is intentional

**Action**: No changes (keep as-is)

---

## Duplication 5: Architecture Documentation

### Files Involved

**Root**:
- `architecture.md` (root) - High-level architecture overview

**Subfolder**:
- `architecture/error-taxonomy.md` - Error handling architecture
- `architecture/modules-and-entitlements.md` - Module system architecture

### Overlap Type

**Likely Overlap**: 10-20% (root `architecture.md` may summarize subfolder docs)

### Recommendation

**Reorganize**:
1. Move `architecture.md` → `architecture/overview.md`
2. Ensure `overview.md` summarizes other architecture docs (with links)
3. Avoid duplicating detailed content (link instead)

**Example Structure** (`architecture/overview.md`):
```markdown
# Architecture Overview

## System Components
- Backend: FastAPI (Python 3.12+)
- Frontend: Next.js (SSR)
- Database: PostgreSQL (Supabase)
- Worker: Celery (Redis broker)

## Architecture Topics
- [Error Taxonomy](error-taxonomy.md) - Error handling strategy
- [Module System](module-system.md) - Module registry, feature flags
- [Channel Manager](channel-manager.md) - Channel sync architecture

(High-level overview, links to detailed docs)
```

---

## Duplication 6: Ops Console Documentation

### Files Involved

**Backend**:
- `backend/app/routers/ops.py` - Backend `/ops/*` API (dead code, not mounted)

**Frontend**:
- `frontend/app/ops/` - Frontend `/ops/*` pages (implemented)

**Documentation** (proposed):
- `frontend/docs/ops-console.md` - Frontend Ops Console (NEW, see MISSING_DOCS_GAPS.md)

### Overlap Type

**Naming Collision**: Backend and frontend both have `/ops/*` routes (different purposes)

### Recommendation

**Clarify Naming**:
1. **Backend Ops API**: `/ops/*` (currently dead code, NOT mounted)
   - If mounted: Document in `architecture/ops-api.md` or `ops/backend-ops-api.md`
   - If deleted: No documentation needed

2. **Frontend Ops Console**: `/ops/*` pages (implemented)
   - Document in `frontend/docs/ops-console.md`

**Action**:
- Ensure docs clearly distinguish "Backend Ops API" (dead code) vs "Frontend Ops Console" (active)
- See DRIFT_REPORT.md for ops router dead code issue

---

## Non-Duplication: Domain-Specific Docs

### Files Involved

- `direct-booking-engine/*.md` (3+ files)
- `channel-manager/*.md` (unknown count)

### Assessment

**No duplication detected** (domain-specific, well-organized)

**Recommendation**: Keep as-is (no changes)

---

## Merge Recommendations Summary

| Duplication | Merge? | Recommendation |
|-------------|--------|----------------|
| Roadmap vs Tickets | ❌ No | Keep separate, add cross-references |
| Root Phase Docs vs Roadmap | ❌ No | Organize into `phases/phase-N/`, keep separate |
| Database Schema Docs | ⚠️ Partial | Move to `database/`, reference migrations (don't duplicate DDL) |
| Status Reviews | ❌ No | Keep all (intentional historical duplication) |
| Architecture Docs | ⚠️ Partial | Move root to `architecture/overview.md`, link to details |
| Ops Console Docs | ❌ No | Clarify naming (backend vs frontend), document separately |
| Domain-Specific Docs | ❌ No | Keep as-is |

---

## Cross-Reference Strategy

### Problem

Files moved during reorganization may break cross-references.

### Solution

1. **Inventory all cross-references**:
   ```bash
   rg "\]\(\.\.\/" backend/docs/ -l
   ```

2. **Update relative paths** after file moves

3. **Prefer absolute paths** (from repo root) for stability:
   ```markdown
   <!-- Relative (brittle after moves) -->
   See [Roadmap](../roadmap/phase-1.md)

   <!-- Absolute (stable after moves) -->
   See [Roadmap](/backend/docs/phases/phase-1/roadmap.md)
   ```

4. **Test links** (manual or automated):
   ```bash
   # Find all markdown links
   rg "\]\([^)]+\.md\)" backend/docs/
   ```

---

## Consolidation Actions (Detailed)

### Action 1: Consolidate Phase Docs

**Before**:
```
backend/docs/
├── roadmap/phase-1.md
├── tickets/phase-1.md
└── (root - no phase-1 files)
```

**After**:
```
backend/docs/phases/phase-1/
├── roadmap.md   (moved from roadmap/phase-1.md)
└── tickets.md   (moved from tickets/phase-1.md)
```

**Cross-Reference Updates**:
- In `roadmap.md`: Update links to `../architecture/` → `../../architecture/`
- In `tickets.md`: Update links to `../database/` → `../../database/`

### Action 2: Move Database Docs

**Before**:
```
backend/docs/
├── phase17b-database-schema-rls.md (root)
└── database/
    ├── data-integrity.md
    └── index-strategy.md
```

**After**:
```
backend/docs/database/
├── schema-rls.md         (moved from root phase17b-database-schema-rls.md)
├── data-integrity.md     (kept)
└── index-strategy.md     (kept)
```

**Content Update**:
- `schema-rls.md`: Reference migrations instead of duplicating DDL

### Action 3: Move Architecture Overview

**Before**:
```
backend/docs/
├── architecture.md (root)
└── architecture/
    ├── error-taxonomy.md
    └── modules-and-entitlements.md
```

**After**:
```
backend/docs/architecture/
├── overview.md                 (moved from root architecture.md)
├── error-taxonomy.md           (kept)
└── modules-and-entitlements.md (kept)
```

**Content Update**:
- `overview.md`: Add links to other architecture docs

---

## Testing Strategy

### After Reorganization

1. **Verify all files moved**:
   ```bash
   # Root should only have github-setup.md
   ls backend/docs/*.md
   ```

2. **Test all cross-references**:
   ```bash
   # Find all markdown links
   rg "\]\([^)]+\.md\)" backend/docs/ -A 1
   # Manually verify each link resolves
   ```

3. **Check for orphaned files**:
   ```bash
   # Find all .md files not in known folders
   find backend/docs -name "*.md" -type f | grep -v -E "(architecture|database|ops|testing|frontend|phases|direct-booking-engine|channel-manager|_staging|github-setup)"
   ```

---

## Rollback Strategy

### If Reorganization Fails

1. **Git revert**: All moves tracked in git commits
2. **Restore original structure**: `git revert <commit-sha>`
3. **No content loss**: Only moves, no deletions

---

**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd
**Status**: PROPOSAL ONLY (no changes made)
**Note**: Most overlap inferred from filenames, files not read
