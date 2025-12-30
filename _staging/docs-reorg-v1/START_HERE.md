# Documentation Reorganization Proposal - v1

**Purpose**: Propose reorganization of 80+ existing documentation files
**Method**: Content analysis, duplication detection, gap identification
**Status**: PROPOSAL ONLY (no files moved/deleted)
**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd

---

## Overview

This proposal analyzes the existing 80+ documentation files in `backend/docs/` and proposes a reorganization to:
1. **Reduce duplication**: Consolidate overlapping content
2. **Fill gaps**: Identify missing documentation (from code analysis)
3. **Improve navigation**: Clearer folder structure, better discoverability
4. **Preserve all content**: No content loss, only restructuring

**Important**: This is a PROPOSAL. No files will be moved or deleted without approval.

---

## Current State

**Total Files**: 80+ markdown files in `backend/docs/`
**Total Size**: Unknown (not measured)
**Structure**: Mixed organization (phases, architecture, ops, domain-specific)

### Current Folder Structure

```
backend/docs/
├── _staging/              (3 review folders: v1, v2, v3 + this proposal)
├── architecture/          (2 files)
├── database/              (2 files)
├── direct-booking-engine/ (3+ files)
├── ops/                   (1 file: runbook.md)
├── roadmap/               (6 files: overview + phase-1 to phase-5)
├── tickets/               (5 files: phase-1 to phase-5)
├── channel-manager/       (unknown count)
└── (root)                 (40+ files: phase*.md, architecture.md, github-setup.md, etc.)
```

**Issues**:
1. **Root folder bloat**: 40+ phase-specific files mixed with architecture docs
2. **Inconsistent naming**: `phaseN.index.md`, `phaseN-topic.md`, `phaseN-topic-subtopic.md`
3. **Duplication**: Phase roadmaps vs tickets vs phase-specific docs
4. **Missing docs**: 8 gaps identified (see MISSING_DOCS_GAPS.md)
5. **Unclear ownership**: No clear "source of truth" for each topic

---

## Proposed Changes

### High-Level Goals

1. **Consolidate phase docs**: Move phase-specific docs into `phases/` folder
2. **Centralize architecture**: Move architecture docs into `architecture/` folder
3. **Create missing docs**: Fill 8 identified gaps
4. **Establish conventions**: Clear naming, folder structure, cross-references

### Proposed Folder Structure

```
backend/docs/
├── _staging/              (Preserve as-is: review folders, proposals)
├── architecture/          (EXPAND: 2 → 8 files)
│   ├── error-taxonomy.md            (✅ Exists, accurate)
│   ├── modules-and-entitlements.md  (✅ Exists, not verified)
│   ├── module-system.md             (❌ NEW: Module registry, feature flags)
│   ├── channel-manager.md           (❌ NEW: Channel Manager design)
│   └── overview.md                  (❌ NEW: Moved from root architecture.md)
├── database/              (EXPAND: 2 → 5 files)
│   ├── data-integrity.md            (✅ Exists)
│   ├── index-strategy.md            (✅ Exists)
│   ├── migrations-guide.md          (❌ NEW: Migration workflow)
│   ├── exclusion-constraints.md     (❌ NEW: EXCLUSION constraint pattern)
│   └── schema-rls.md                (⚠️ Moved from root phase17b-database-schema-rls.md)
├── ops/                   (EXPAND: 1 → 3 files)
│   ├── runbook.md                   (✅ Exists, accurate)
│   ├── feature-flags.md             (❌ NEW: Centralized feature flag docs)
│   └── deployment.md                (❌ NEW: Deployment guide)
├── testing/               (NEW FOLDER: 0 → 2 files)
│   ├── README.md                    (❌ NEW: Test organization, how to run)
│   └── integration-tests.md         (❌ NEW: Integration test patterns)
├── frontend/              (NEW FOLDER: 0 → 2 files)
│   ├── authentication.md            (❌ NEW: Supabase SSR, middleware)
│   └── ops-console.md               (❌ NEW: Frontend Ops Console pages)
├── phases/                (NEW FOLDER: Consolidate phase docs)
│   ├── README.md                    (❌ NEW: Phase overview)
│   ├── phase-1/                     (Move from root + roadmap + tickets)
│   ├── phase-2/
│   ├── ...
│   ├── phase-10/
│   └── phase-19/
├── roadmap/               (DEPRECATE: Merge into phases/)
├── tickets/               (DEPRECATE: Merge into phases/)
├── direct-booking-engine/ (Keep as-is)
├── channel-manager/       (Keep as-is, add architecture/channel-manager.md)
└── (root)                 (CLEAN UP: Move phase*.md to phases/)
```

**New Files**: 8 (see MISSING_DOCS_GAPS.md)
**Moved Files**: 50+ (phase-specific docs from root to `phases/`)
**Deprecated Folders**: 2 (`roadmap/`, `tickets/` → merged into `phases/`)

---

## Files in This Proposal

1. **START_HERE.md** (this file) - Proposal overview, before/after structure
2. **DOC_STRUCTURE_PROPOSAL.md** - Detailed folder-by-folder reorganization plan
3. **CONTENT_SUMMARY.md** - What each existing doc contains (inventory)
4. **DUPLICATES_AND_OVERLAPS.md** - Redundant content identification, merge recommendations
5. **MISSING_DOCS_GAPS.md** - 8 missing docs identified from code analysis

---

## Benefits

### 1. Reduced Navigation Overhead

**Before**: 40+ files in root, unclear which phase doc to read
**After**: `phases/phase-N/` contains all phase-N related docs

### 2. Clear Architecture Documentation

**Before**: 2 architecture docs, missing module system, channel manager
**After**: 5 architecture docs (error taxonomy, modules, channel manager, overview)

### 3. Centralized Feature Flags

**Before**: Feature flags scattered across code, not documented
**After**: `ops/feature-flags.md` central reference

### 4. Frontend Documentation

**Before**: No frontend docs (SSR auth, ops console undocumented)
**After**: `frontend/` folder with authentication, ops console docs

### 5. Testing Guide

**Before**: 15+ test files, no guide on how to run/add tests
**After**: `testing/README.md` with test organization, how-to

---

## Risks & Mitigation

### Risk 1: Breaking Links

**Risk**: Existing cross-references break when files move
**Mitigation**:
- Step 1: Inventory all cross-references (grep for `](../` or `](/`)
- Step 2: Update all relative links in moved files
- Step 3: Add redirects in old locations (e.g., `See phases/phase-1/`)

### Risk 2: Content Loss

**Risk**: Files accidentally deleted during reorganization
**Mitigation**:
- Git-based reorganization (all moves tracked)
- No deletions, only moves and merges
- Review PR carefully before merge

### Risk 3: Duplication Persists

**Risk**: Merge recommendations ignored, duplication remains
**Mitigation**:
- DUPLICATES_AND_OVERLAPS.md explicitly flags overlaps
- Prioritize merges before moving files

---

## Implementation Plan (Phased)

### Phase 1: Create Missing Docs (No Moves)

**Duration**: 1-2 days
**Scope**: Create 8 new docs identified in MISSING_DOCS_GAPS.md
**No file moves**: Safest change, additive only

**Files to Create**:
1. `architecture/module-system.md`
2. `architecture/channel-manager.md`
3. `database/migrations-guide.md`
4. `database/exclusion-constraints.md`
5. `ops/feature-flags.md`
6. `testing/README.md`
7. `frontend/authentication.md`
8. `frontend/ops-console.md`

### Phase 2: Consolidate Phase Docs

**Duration**: 2-3 days
**Scope**: Create `phases/` folder, move phase-specific docs

**Steps**:
1. Create `phases/phase-{1-19}/` folders
2. Move `roadmap/phase-N.md` → `phases/phase-N/roadmap.md`
3. Move `tickets/phase-N.md` → `phases/phase-N/tickets.md`
4. Move root `phaseN*.md` → `phases/phase-N/*.md`
5. Create `phases/README.md` with navigation

### Phase 3: Consolidate Architecture Docs

**Duration**: 1 day
**Scope**: Move architecture docs to `architecture/` folder

**Steps**:
1. Move root `architecture.md` → `architecture/overview.md`
2. Move `phase17b-database-schema-rls.md` → `database/schema-rls.md`
3. Update cross-references

### Phase 4: Merge Duplicates

**Duration**: 2-3 days
**Scope**: Merge overlapping content (see DUPLICATES_AND_OVERLAPS.md)

**Steps**:
1. Review DUPLICATES_AND_OVERLAPS.md
2. Merge content from duplicates into canonical doc
3. Add redirect notices in old locations
4. Remove duplicate files

### Phase 5: Update Cross-References

**Duration**: 1 day
**Scope**: Fix all broken links from file moves

**Steps**:
1. Grep for all cross-references: `rg "\]\(\.\./" backend/docs/`
2. Update relative paths
3. Test all links (manual or automated)

**Total Duration**: 7-10 days (can be spread over multiple PRs)

---

## Decision Points

### Decision 1: Merge or Keep Separate?

**Question**: Merge `roadmap/phase-N.md` and `tickets/phase-N.md` into single `phases/phase-N/README.md`?

**Option A (Merge)**:
- Pros: Single source of truth, less navigation
- Cons: Large files, roadmap vs tickets may have different audiences

**Option B (Keep Separate)**:
- Pros: Clear separation (planning vs execution)
- Cons: 2 files per phase (12 files for 6 phases)

**Recommendation**: Keep separate (`phases/phase-N/roadmap.md` and `phases/phase-N/tickets.md`)

### Decision 2: Deprecate `roadmap/` and `tickets/` Folders?

**Question**: Delete `roadmap/` and `tickets/` folders after moving content to `phases/`?

**Option A (Delete)**:
- Pros: Clean structure, no duplication
- Cons: Breaking change for any external links

**Option B (Redirect)**:
- Pros: Backward compatibility
- Cons: Empty folders with redirect notices

**Recommendation**: Add redirect notices, delete in next major version

### Decision 3: Root Folder Cleanup

**Question**: Move ALL phase-specific docs from root to `phases/`?

**Recommendation**: Yes, move all `phase*.md` files to `phases/phase-N/`

---

## Review Checklist

Before implementing this proposal:

1. ✅ Read CONTENT_SUMMARY.md - Understand what each doc contains
2. ✅ Read DUPLICATES_AND_OVERLAPS.md - Identify merge opportunities
3. ✅ Read MISSING_DOCS_GAPS.md - Understand what needs to be created
4. ✅ Read DOC_STRUCTURE_PROPOSAL.md - Detailed reorganization plan
5. ⬜ Approve or reject proposal
6. ⬜ If approved, follow Implementation Plan (Phase 1 → Phase 5)

---

## Next Steps

1. **Review this proposal** with team
2. **Approve/reject** each phase of implementation plan
3. **Start with Phase 1** (create missing docs, safest change)
4. **Create PRs** for each phase (incremental, reviewable)
5. **Update this proposal** based on feedback

---

**Status**: PROPOSAL ONLY (no changes made)
**Generated**: 2025-12-30 21:01:55 UTC
**Commit**: 3490c89b829704d10b87a2b42b739f1efd7ae5fd
**Companion**: See `status-review-v3/` for code-derived project status
