# Documentation Structure Proposal - v1

**Purpose**: Detailed folder-by-folder reorganization plan
**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd

---

## Proposed Documentation Structure

```
backend/docs/
├── _staging/
│   ├── status-review-v1/
│   ├── status-review-v2/
│   ├── status-review-v3/
│   └── docs-reorg-v1/           ⬅️ THIS PROPOSAL
├── architecture/
│   ├── overview.md              ⬅️ MOVE from root architecture.md
│   ├── error-taxonomy.md        ✅ KEEP (accurate)
│   ├── modules-and-entitlements.md ✅ KEEP
│   ├── module-system.md         ❌ NEW (Gap #1)
│   └── channel-manager.md       ❌ NEW (Gap #2)
├── database/
│   ├── data-integrity.md        ✅ KEEP
│   ├── index-strategy.md        ✅ KEEP
│   ├── schema-rls.md            ⬅️ MOVE from root phase17b-database-schema-rls.md
│   ├── migrations-guide.md      ❌ NEW (Gap #3)
│   └── exclusion-constraints.md ❌ NEW (Gap #4)
├── ops/
│   ├── runbook.md               ✅ KEEP (accurate)
│   ├── feature-flags.md         ❌ NEW (Gap #5)
│   └── deployment.md            ⬅️ NEW or merge from runbook.md
├── testing/
│   ├── README.md                ❌ NEW (Gap #6)
│   └── integration-tests.md     ⬅️ NEW (optional)
├── frontend/
│   ├── authentication.md        ❌ NEW (Gap #7)
│   └── ops-console.md           ❌ NEW (Gap #8)
├── phases/
│   ├── README.md                ❌ NEW (phase navigation)
│   ├── phase-1/
│   │   ├── roadmap.md           ⬅️ MOVE from roadmap/phase-1.md
│   │   ├── tickets.md           ⬅️ MOVE from tickets/phase-1.md
│   │   └── (other phase-1 docs) ⬅️ MOVE from root phase-1*.md
│   ├── phase-2/
│   │   ├── roadmap.md           ⬅️ MOVE from roadmap/phase-2.md
│   │   ├── tickets.md           ⬅️ MOVE from tickets/phase-2.md
│   │   └── (other phase-2 docs)
│   ├── ... (phase-3 through phase-6)
│   ├── phase-7/
│   │   └── qa-security.md       ⬅️ MOVE from root phase7-qa-security.md
│   ├── phase-8/
│   │   └── index.md             ⬅️ MOVE from root phase8.index.md
│   ├── phase-9/
│   │   ├── index.md             ⬅️ MOVE from root phase9.index.md
│   │   └── release-plan.md      ⬅️ MOVE from root phase9-release-plan.md
│   ├── phase-10/
│   │   ├── 10a-ui-ux.md         ⬅️ MOVE from root phase10a-ui-ux.md
│   │   ├── 10a.index.md         ⬅️ MOVE from root phase10a.index.md
│   │   └── 10b-10c-visual-design.md ⬅️ MOVE from root phase10b-10c-visual-design.md
│   ├── phase-15-16/
│   │   └── direct-booking-eigentuemer.md ⬅️ MOVE from root
│   ├── phase-17/
│   │   └── 17b-database-schema-rls.md ⬅️ DEPRECATED (merged into database/schema-rls.md)
│   ├── phase-18/
│   │   └── 18a-preflight.md     ⬅️ MOVE from root
│   └── phase-19/
│       └── core-booking-flow-api.md ⬅️ MOVE from root
├── direct-booking-engine/
│   ├── stripe-integration.md    ✅ KEEP
│   ├── edge-cases.md            ✅ KEEP
│   └── email-templates/README.md ✅ KEEP
├── channel-manager/
│   └── (existing docs)          ✅ KEEP
├── github-setup.md              ✅ KEEP in root
└── roadmap/ & tickets/          ⚠️ DEPRECATE (add redirect notices)
```

---

## Detailed Changes by Folder

### 1. architecture/ (Expand: 2 → 5 files)

#### Changes

| File | Action | Source | Notes |
|------|--------|--------|-------|
| `overview.md` | MOVE | `backend/docs/architecture.md` | Root architecture doc moved here |
| `error-taxonomy.md` | KEEP | (existing) | Accurate, no changes |
| `modules-and-entitlements.md` | KEEP | (existing) | Not verified, assume accurate |
| `module-system.md` | NEW | Gap #1 (MISSING_DOCS_GAPS.md) | Module registry, feature flags |
| `channel-manager.md` | NEW | Gap #2 (MISSING_DOCS_GAPS.md) | Channel Manager design |

#### Rationale

- Consolidate all architecture docs in one folder
- Root `architecture.md` renamed to `overview.md` for clarity
- New docs for module system and channel manager (code exists, docs missing)

---

### 2. database/ (Expand: 2 → 5 files)

#### Changes

| File | Action | Source | Notes |
|------|--------|--------|-------|
| `data-integrity.md` | KEEP | (existing) | Not verified |
| `index-strategy.md` | KEEP | (existing) | Not verified |
| `schema-rls.md` | MOVE | `backend/docs/phase17b-database-schema-rls.md` | Database-specific doc, belongs here |
| `migrations-guide.md` | NEW | Gap #3 (MISSING_DOCS_GAPS.md) | Migration workflow |
| `exclusion-constraints.md` | NEW | Gap #4 (MISSING_DOCS_GAPS.md) | EXCLUSION constraint pattern |

#### Rationale

- Consolidate all database docs in one folder
- `phase17b-database-schema-rls.md` is database-specific, not phase-specific
- New docs for migrations and EXCLUSION constraints (critical gaps)

---

### 3. ops/ (Expand: 1 → 3 files)

#### Changes

| File | Action | Source | Notes |
|------|--------|--------|-------|
| `runbook.md` | KEEP | (existing) | Accurate production guide |
| `feature-flags.md` | NEW | Gap #5 (MISSING_DOCS_GAPS.md) | Centralized feature flag docs |
| `deployment.md` | NEW or MERGE | Extract from `runbook.md` | Optional: separate deployment from troubleshooting |

#### Rationale

- Centralize operational docs
- Feature flags critical for deployment (currently scattered)
- Deployment guide may be separate from runbook (decision point)

---

### 4. testing/ (NEW FOLDER: 0 → 2 files)

#### Changes

| File | Action | Source | Notes |
|------|--------|--------|-------|
| `README.md` | NEW | Gap #6 (MISSING_DOCS_GAPS.md) | Test organization, how to run |
| `integration-tests.md` | NEW (optional) | - | Integration test patterns (optional) |

#### Rationale

- 15+ test files exist, no documentation on how to run/add tests
- Testing guide essential for contributors

---

### 5. frontend/ (NEW FOLDER: 0 → 2 files)

#### Changes

| File | Action | Source | Notes |
|------|--------|--------|-------|
| `authentication.md` | NEW | Gap #7 (MISSING_DOCS_GAPS.md) | Supabase SSR, middleware |
| `ops-console.md` | NEW | Gap #8 (MISSING_DOCS_GAPS.md) | Frontend Ops Console pages |

#### Rationale

- Frontend docs currently missing
- SSR authentication and ops console undocumented
- Proposed location: `frontend/docs/` (outside `backend/docs/`)

**Alternative**: Create `backend/docs/frontend/` to keep all docs in one repo location

---

### 6. phases/ (NEW FOLDER: Consolidate phase docs)

#### Strategy

**Consolidate 3 sources**:
1. `roadmap/phase-N.md` → `phases/phase-N/roadmap.md`
2. `tickets/phase-N.md` → `phases/phase-N/tickets.md`
3. Root `phaseN*.md` → `phases/phase-N/*.md`

#### Example: Phase 1

**Before**:
```
backend/docs/
├── roadmap/phase-1.md
├── tickets/phase-1.md
└── (no other phase-1 files in root)
```

**After**:
```
backend/docs/phases/phase-1/
├── roadmap.md   (moved from roadmap/phase-1.md)
└── tickets.md   (moved from tickets/phase-1.md)
```

#### Example: Phase 10

**Before**:
```
backend/docs/
├── roadmap/phase-10.md           (doesn't exist)
├── tickets/phase-10.md           (doesn't exist)
├── phase10a-ui-ux.md             (root)
├── phase10a.index.md             (root)
└── phase10b-10c-visual-design.md (root)
```

**After**:
```
backend/docs/phases/phase-10/
├── 10a-ui-ux.md              (moved from root)
├── 10a.index.md              (moved from root)
└── 10b-10c-visual-design.md  (moved from root)
```

#### All Phases

| Phase | Roadmap | Tickets | Root Files | Total Docs |
|-------|---------|---------|------------|------------|
| Phase 1 | ✅ | ✅ | 0 | 2 |
| Phase 2 | ✅ | ✅ | 0 | 2 |
| Phase 3 | ✅ | ✅ | 0 | 2 |
| Phase 4 | ✅ | ✅ | 0 | 2 |
| Phase 5 | ✅ | ✅ | 0 | 2 |
| Phase 6 | ❓ | ❓ | 0 | 0-2 |
| Phase 7 | ❓ | ❓ | 1 (`phase7-qa-security.md`) | 1-3 |
| Phase 8 | ❓ | ❓ | 1 (`phase8.index.md`) | 1-3 |
| Phase 9 | ❓ | ❓ | 2 (`phase9.index.md`, `phase9-release-plan.md`) | 2-4 |
| Phase 10 | ❓ | ❓ | 3 (`phase10a-ui-ux.md`, `phase10a.index.md`, `phase10b-10c-visual-design.md`) | 3-5 |
| Phase 15-16 | ❓ | ❓ | 1 (`phase15-16-direct-booking-eigentuemer.md`) | 1-3 |
| Phase 17 | ❓ | ❓ | 1 (`phase17b-database-schema-rls.md`) | 1-3 |
| Phase 18 | ❓ | ❓ | 1 (`phase18a-preflight.md`) | 1-3 |
| Phase 19 | ❓ | ❓ | 1 (`phase19-core-booking-flow-api.md`) | 1-3 |

**Total Phase Docs**: 50+ files (estimate)

---

### 7. roadmap/ & tickets/ (DEPRECATE)

#### Strategy

**Option A (Delete)**:
- Move all files to `phases/`
- Delete empty `roadmap/` and `tickets/` folders

**Option B (Redirect)**:
- Move all files to `phases/`
- Add `roadmap/README.md` and `tickets/README.md` with redirect notices:
  ```markdown
  # DEPRECATED: Roadmap Docs Moved

  All roadmap docs have been moved to `phases/phase-N/roadmap.md`.

  See `phases/README.md` for navigation.
  ```

**Recommendation**: Option B (redirect notices for backward compatibility)

---

### 8. Root Folder Cleanup

#### Files to Move

| File | Destination | Notes |
|------|-------------|-------|
| `architecture.md` | `architecture/overview.md` | Architecture overview |
| `phase7-qa-security.md` | `phases/phase-7/qa-security.md` | Phase-specific |
| `phase8.index.md` | `phases/phase-8/index.md` | Phase-specific |
| `phase9.index.md` | `phases/phase-9/index.md` | Phase-specific |
| `phase9-release-plan.md` | `phases/phase-9/release-plan.md` | Phase-specific |
| `phase10a-ui-ux.md` | `phases/phase-10/10a-ui-ux.md` | Phase-specific |
| `phase10a.index.md` | `phases/phase-10/10a.index.md` | Phase-specific |
| `phase10b-10c-visual-design.md` | `phases/phase-10/10b-10c-visual-design.md` | Phase-specific |
| `phase15-16-direct-booking-eigentuemer.md` | `phases/phase-15-16/direct-booking-eigentuemer.md` | Phase-specific |
| `phase17b-database-schema-rls.md` | `database/schema-rls.md` | Database-specific |
| `phase18a-preflight.md` | `phases/phase-18/18a-preflight.md` | Phase-specific |
| `phase19-core-booking-flow-api.md` | `phases/phase-19/core-booking-flow-api.md` | Phase-specific |

#### Files to Keep in Root

| File | Reason |
|------|--------|
| `github-setup.md` | Project setup doc (not phase/architecture/ops) |

---

### 9. direct-booking-engine/ & channel-manager/ (KEEP AS-IS)

**No changes** to these folders (domain-specific docs, already well-organized)

---

## File Count Summary

### Before Reorganization

- Root: ~40 files (phase docs, architecture.md, github-setup.md)
- architecture/: 2 files
- database/: 2 files
- ops/: 1 file
- roadmap/: 6 files
- tickets/: 5 files
- _staging/: 4 folders (v1, v2, v3, docs-reorg-v1)
- Other folders: Unchanged

**Total**: 80+ files

### After Reorganization

- Root: 1 file (github-setup.md)
- architecture/: 5 files (+3 new)
- database/: 5 files (+3 new, +1 moved)
- ops/: 3 files (+2 new)
- testing/: 2 files (+2 new)
- frontend/: 2 files (+2 new) **OR** `backend/docs/frontend/` (decision point)
- phases/: ~50 files (moved from roadmap/, tickets/, root)
- roadmap/ & tickets/: DEPRECATED (redirect notices)
- _staging/: 4 folders (unchanged)
- Other folders: Unchanged

**Total**: 88+ files (+8 new docs)

---

## Navigation Improvements

### Before

**Finding Phase 1 docs**:
1. Check `roadmap/phase-1.md` for planning
2. Check `tickets/phase-1.md` for tasks
3. Search root for `phase-1*.md` files (none found)
4. **3 locations to check**

### After

**Finding Phase 1 docs**:
1. Navigate to `phases/phase-1/`
2. See `roadmap.md`, `tickets.md` in one folder
3. **1 location to check**

---

## Cross-Reference Updates Required

### Pattern

All relative links need updating after file moves.

**Example**:
```markdown
<!-- Before (in roadmap/phase-1.md) -->
See [Architecture](../architecture.md) for details.

<!-- After (in phases/phase-1/roadmap.md) -->
See [Architecture](../../architecture/overview.md) for details.
```

### Update Strategy

1. **Find all cross-references**:
   ```bash
   rg "\]\(\.\.\/" backend/docs/
   ```

2. **Update relative paths** after file moves

3. **Test links** (manual or automated)

---

## Implementation Phases (Detailed)

### Phase 1: Create Missing Docs (No Moves)

**Files Created**: 8 new docs (MISSING_DOCS_GAPS.md)
1. `architecture/module-system.md`
2. `architecture/channel-manager.md`
3. `database/migrations-guide.md`
4. `database/exclusion-constraints.md`
5. `ops/feature-flags.md`
6. `testing/README.md`
7. `frontend/docs/authentication.md` (or `backend/docs/frontend/authentication.md`)
8. `frontend/docs/ops-console.md` (or `backend/docs/frontend/ops-console.md`)

**No file moves**: Safest change, additive only

### Phase 2: Consolidate Phase Docs

**Steps**:
1. Create `phases/` folder
2. Create `phases/README.md` with navigation
3. For each phase:
   - Create `phases/phase-N/` folder
   - Move `roadmap/phase-N.md` → `phases/phase-N/roadmap.md`
   - Move `tickets/phase-N.md` → `phases/phase-N/tickets.md`
   - Move root `phaseN*.md` → `phases/phase-N/*.md`
4. Update cross-references in moved files

### Phase 3: Consolidate Architecture Docs

**Steps**:
1. Move `architecture.md` → `architecture/overview.md`
2. Update cross-references

### Phase 4: Consolidate Database Docs

**Steps**:
1. Move `phase17b-database-schema-rls.md` → `database/schema-rls.md`
2. Update cross-references

### Phase 5: Deprecate roadmap/ & tickets/

**Steps**:
1. Add `roadmap/README.md` with redirect notice
2. Add `tickets/README.md` with redirect notice
3. (Optional) Delete folders in next major version

---

**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd
**Status**: PROPOSAL ONLY (no changes made)
