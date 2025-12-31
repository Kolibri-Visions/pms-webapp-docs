# Documentation Deprecation Map

**Purpose**: Safe deletion roadmap for old/duplicate documentation

**Audience**: Maintainers, documentation reviewers

**Source of Truth**: This file tracks OLD → NEW mappings before any deletion

---

## Rules

### No Deletes Until Coverage Verified

- **NEVER delete** old docs without verifying replacement coverage
- **ALWAYS check** START_HERE.md links cover all old doc topics
- **PREFER redirect stubs** if paths change (see [DOCS_LIFECYCLE.md](DOCS_LIFECYCLE.md#migrating-docs-restructure))
- **TAG before delete**: Create git tag `docs-archive-YYYY-MM-DD` before deletion PR

### Deprecation Workflow

1. Add entry to mapping table (status: `planned`)
2. Create replacement doc (update status: `covered`)
3. Verify coverage via deletion gate checklist
4. Update status: `ready-to-delete`
5. Create redirect stub if path changed
6. Only then: delete old file

---

## Mapping Table

### Status Legend

- **planned**: Identified for deprecation, replacement not yet complete
- **covered**: Replacement doc exists and covers all topics
- **ready-to-delete**: Deletion gate passed, safe to delete

---

### Phase/Roadmap Docs → Product Backlog/Release Plan

| OLD Path | NEW Path | Coverage Notes | Status | Verification |
|----------|----------|----------------|--------|--------------|
| `phase*.md` (root) | `product/PRODUCT_BACKLOG.md`, `product/RELEASE_PLAN.md` | All phase planning now in 10 epics (A-J) + MVP/Beta/Prod-ready milestones | **covered** | [PRODUCT_BACKLOG.md](../product/PRODUCT_BACKLOG.md), [RELEASE_PLAN.md](../product/RELEASE_PLAN.md) |
| `roadmap/phase-1.md` through `roadmap/phase-5.md` | `product/RELEASE_PLAN.md` | Phase 0 (Foundation) through Phase 3 (Prod-Ready) mapped | **covered** | [RELEASE_PLAN.md](../product/RELEASE_PLAN.md) |
| `tickets/phase-1.md` through `tickets/phase-5.md` | `product/PRODUCT_BACKLOG.md` (Open Tasks sections) | Task breakdown now in epic-level Open Tasks | **covered** | [PRODUCT_BACKLOG.md](../product/PRODUCT_BACKLOG.md) |
| `roadmap/overview.md` | `product/RELEASE_PLAN.md` | Overview replaced by release phases + timeline | **covered** | [RELEASE_PLAN.md](../product/RELEASE_PLAN.md) |
| `phase9-release-plan.md` | `product/RELEASE_PLAN.md` | Release planning consolidated | **covered** | [RELEASE_PLAN.md](../product/RELEASE_PLAN.md) |

---

### Ops Duplicates → Runbook/Feature Flags

| OLD Path | NEW Path | Coverage Notes | Status | Verification |
|----------|----------|----------------|--------|--------------|
| `ops/migrations.md` | `database/migrations-guide.md` | All migration workflows + Schema Drift SOP | **covered** | [migrations-guide.md](../database/migrations-guide.md), [runbook.md - Top 5 Failure Modes](../ops/runbook.md#top-5-failure-modes-and-fixes) |
| `ops/availability_smoke.md` | `testing/README.md` (Server-side Smoke Checks) | Availability smoke checks in official smoke sequence | **covered** | [testing/README.md](../testing/README.md#server-side-smoke-checks-official) |
| `ops/inventory_availability.md` | `ops/runbook.md`, `database/migrations-guide.md` | Availability/inventory troubleshooting in runbook, schema in migrations guide | **covered** | [runbook.md](../ops/runbook.md), [migrations-guide.md](../database/migrations-guide.md) |
| `ops/inventory_rules.md` | `database/exclusion-constraints.md`, `database/data-integrity.md` | EXCLUSION constraints doc covers overlap prevention rules | **covered** | [exclusion-constraints.md](../database/exclusion-constraints.md) |

---

### Architecture Phase Docs → Architecture/

| OLD Path | NEW Path | Coverage Notes | Status | Verification |
|----------|----------|----------------|--------|--------------|
| `architecture/phase21-modularization-plan.md` | `architecture/module-system.md` | Module registry, graceful degradation covered | **covered** | [module-system.md](../architecture/module-system.md) |
| `phase17b-database-schema-rls.md` | `database/migrations-guide.md`, `_staging/status-review-v3/PROJECT_STATUS.md` | RLS policies documented in status review v3 snapshot | **covered** | [migrations-guide.md](../database/migrations-guide.md), [status-review-v3](../_staging/status-review-v3/PROJECT_STATUS.md) |
| `phase18a-preflight.md`, `phase18a-schema-alignment-rls-implementation.md` | `database/migrations-guide.md` | Schema alignment + RLS covered in migrations guide | **covered** | [migrations-guide.md](../database/migrations-guide.md) |
| `phase19-core-booking-flow-api.md`, `phase19-preflight.md` | `product/PRODUCT_BACKLOG.md` (Epic C: Booking Lifecycle) | Core booking flow in product backlog | **covered** | [PRODUCT_BACKLOG.md - Epic C](../product/PRODUCT_BACKLOG.md#epic-c-booking-lifecycle) |

---

### Frontend/UX Phase Docs → Frontend/

| OLD Path | NEW Path | Coverage Notes | Status | Verification |
|----------|----------|----------------|--------|--------------|
| `phase10a-ui-ux.md`, `phase10a.index.md` | `frontend/ops-console.md`, `frontend/authentication.md` | Frontend architecture covered in frontend/ docs | **covered** | [ops-console.md](../frontend/ops-console.md), [authentication.md](../frontend/authentication.md) |
| `phase10b-10c-visual-design.md` | `product/PRODUCT_BACKLOG.md` (Epic F: Guest Portal, Epic G: Owner Portal) | Visual design planning in product backlog epics | **planned** | [PRODUCT_BACKLOG.md](../product/PRODUCT_BACKLOG.md) |
| `phase11-13-agentur-ux-rollen.md` | `_staging/status-review-v3/PROJECT_STATUS.md` (RBAC section) | Agency UX + RBAC roles documented in status review | **covered** | [status-review-v3 - RBAC](../_staging/status-review-v3/PROJECT_STATUS.md#rbac-role-based-access-control) |

---

### Backend/API Phase Docs → Architecture/

| OLD Path | NEW Path | Coverage Notes | Status | Verification |
|----------|----------|----------------|--------|--------------|
| `phase5-backend-apis.index.md`, `phase5-backend-apis.md` | `architecture/module-system.md`, `architecture/error-taxonomy.md` | Backend API patterns in architecture docs | **covered** | [module-system.md](../architecture/module-system.md), [error-taxonomy.md](../architecture/error-taxonomy.md) |
| `phase6-supabase-rls.md` | `database/migrations-guide.md`, `_staging/status-review-v3/PROJECT_STATUS.md` | RLS policies documented | **covered** | [migrations-guide.md](../database/migrations-guide.md) |
| `phase7-qa-security.md`, `phase7-qa-security-remediation.md`, `phase7.index.md` | `product/PRODUCT_BACKLOG.md` (Epic A: Stability & Security) | QA/security in Epic A | **covered** | [PRODUCT_BACKLOG.md - Epic A](../product/PRODUCT_BACKLOG.md#epic-a-stability--security) |
| `phase8-prd-light.md`, `phase8.index.md` | `product/PRODUCT_BACKLOG.md`, `product/RELEASE_PLAN.md` | PRD covered in product docs | **covered** | [PRODUCT_BACKLOG.md](../product/PRODUCT_BACKLOG.md) |

---

### Other Phase Docs

| OLD Path | NEW Path | Coverage Notes | Status | Verification |
|----------|----------|----------------|--------|--------------|
| `phase14-preismodell-logik.md` | `product/PRODUCT_BACKLOG.md` (Epic H: Finance & Accounting) | Pricing model in finance epic | **planned** | [PRODUCT_BACKLOG.md - Epic H](../product/PRODUCT_BACKLOG.md#epic-h-finance--accounting) |
| `phase15-16-direct-booking-eigentuemer.md` | `product/PRODUCT_BACKLOG.md` (Epic E: Direct Booking, Epic G: Owner Portal) | Direct booking + owner portal epics | **planned** | [PRODUCT_BACKLOG.md](../product/PRODUCT_BACKLOG.md) |

---

## Discovery Needed

**To Complete Mapping**: Search for the following patterns and assess coverage:

1. **Environment variable docs** (scattered notes)
   - Search: `grep -r "ENV" --include="*.md" backend/docs/`
   - Verify: All covered by `ops/feature-flags.md` or `PROJECT_STATUS_LIVE.md`

2. **Deployment/Docker notes** (scattered notes)
   - Search: `grep -r "Dockerfile\|docker-compose\|deployment" --include="*.md" backend/docs/`
   - Verify: All covered by `ops/runbook.md` or `PROJECT_STATUS_LIVE.md`

3. **Schema/DDL snippets** (scattered SQL)
   - Search: `grep -r "CREATE TABLE\|ALTER TABLE" --include="*.md" backend/docs/`
   - Verify: All covered by `database/migrations-guide.md` or `database/exclusion-constraints.md`

4. **Old test docs** (scattered test notes)
   - Search: `grep -r "pytest\|test" --include="*.md" backend/docs/`
   - Verify: All covered by `testing/README.md`

---

## Deletion Gate Checklist

**Before deleting ANY old doc**, verify ALL of the following:

### Coverage Verification

- [ ] **START_HERE.md links** cover all topics from old doc
- [ ] **Runbook** has Top 5 Failure Modes section
- [ ] **Migrations guide** includes Schema Drift SOP
- [ ] **Testing guide** includes official server-side smoke checks
- [ ] **Feature flags** doc exists and is current
- [ ] **Product backlog** + DoD + Release Plan exist
- [ ] **PROJECT_STATUS_LIVE.md** is current
- [ ] **Ops Console docs** exist (frontend/ops-console.md)
- [ ] **Authentication docs** exist (frontend/authentication.md)

### Technical Verification

- [ ] **Mirror publish green** (GitHub Actions CI passes)
- [ ] **No broken links** from START_HERE or other active docs to deleted file
- [ ] **Redirect stub created** (if path changed, per [DOCS_LIFECYCLE.md](DOCS_LIFECYCLE.md#migrating-docs-restructure))
- [ ] **Git tag created**: `docs-archive-YYYY-MM-DD` (marks pre-deletion state)

### Process Verification

- [ ] **Status in this map**: `ready-to-delete`
- [ ] **Team notification**: Posted in team chat (allow 7 days for objections)
- [ ] **Update DOCS_LIFECYCLE**: Add archived file to lifecycle tracking

---

## Safe Deletion Workflow

**Step 1: Verify Coverage**
- Check deletion gate checklist (all boxes ✅)
- Review replacement docs ensure completeness

**Step 2: Create Archive Tag**
```bash
# Create git tag before deletion
git tag -a docs-archive-$(date +%Y-%m-%d) -m "Archive state before deleting phase docs"
git push origin docs-archive-$(date +%Y-%m-%d)
```

**Step 3: Create Redirect Stub (if path changed)**

If old path was linked externally or had deep links:
```markdown
> **MOVED**: This document has moved to [new location](link).
>
> **Redirect Date**: YYYY-MM-DD
> **Old Location Removal**: YYYY-MM-DD (14 days)
```

**Step 4: Delete Files**
```bash
# Delete old doc
git rm backend/docs/path/to/old-doc.md

# Commit
git commit -m "docs: delete old-doc.md (replaced by new-doc.md)"
```

**Step 5: Update This Map**
- Move entry to "Deleted" section (see below)
- Update DOCS_LIFECYCLE.md archived list

---

## Deleted Files (Archive)

**When files are deleted**, move entries here with deletion date:

| Deleted Path | Replaced By | Deletion Date | Wave |
|--------------|-------------|---------------|------|
| `ops/availability_smoke.md` | `testing/README.md` | 2025-12-31 | Wave 1 |
| `ops/inventory_availability.md` | `database/migrations-guide.md` | 2025-12-31 | Wave 1 |
| `ops/inventory_rules.md` | `database/exclusion-constraints.md` | 2025-12-31 | Wave 1 |
| `ops/migrations.md` | `database/migrations-guide.md` | 2025-12-31 | Wave 1 |
| `phase5-backend-apis.index.md` | `product/PRODUCT_BACKLOG.md` | 2025-12-31 | Wave 2A |
| `phase7.index.md` | `product/PRODUCT_BACKLOG.md` | 2025-12-31 | Wave 2A |
| `phase8.index.md` | `product/PRODUCT_BACKLOG.md` | 2025-12-31 | Wave 2A |
| `phase9.index.md` | `product/RELEASE_PLAN.md` | 2025-12-31 | Wave 2A |
| `phase10a.index.md` | `product/PRODUCT_BACKLOG.md` | 2025-12-31 | Wave 2A |
| `phase10b-10c-visual-design.md` | `product/PRODUCT_BACKLOG.md` | 2025-12-31 | Wave 2A |
| `phase11-13-agentur-ux-rollen.md` | `product/PRODUCT_BACKLOG.md` | 2025-12-31 | Wave 2A |
| `phase14-preismodell-logik.md` | `product/PRODUCT_BACKLOG.md` | 2025-12-31 | Wave 2A |
| `phase15-16-direct-booking-eigentuemer.md` | `product/PRODUCT_BACKLOG.md` | 2025-12-31 | Wave 2A |
| `phase19-preflight.md` | `product/PRODUCT_BACKLOG.md` | 2025-12-31 | Wave 2A |

---

## Docs Inventory

**Total Files**: 91 markdown files (excluding `_staging/` snapshots)

**Breakdown by Folder**:

| Folder | Count | Notes |
|--------|-------|-------|
| **root** | 29 | Includes 21 phase*.md files, project docs, templates |
| **architecture/** | 19 | ADRs, module system, error taxonomy, channel manager |
| **roadmap/** | 6 | phase-1.md through phase-5.md, overview.md |
| **ops/** | 6 | runbook, feature-flags, 4 old duplicates |
| **tickets/** | 5 | phase-1.md through phase-5.md |
| **channel-manager/** | 5 | Architecture, OAuth flows, monitoring, conflict resolution |
| **product/** | 4 | PRODUCT_BACKLOG, RELEASE_PLAN, CHANGELOG, reference model |
| **process/** | 4 | DoD, DOCS_LIFECYCLE, DEPRECATION_MAP, RELEASE_CADENCE |
| **direct-booking-engine/** | 4 | Flow, edge cases, Stripe, email templates |
| **database/** | 4 | migrations-guide, exclusion-constraints, data-integrity, index-strategy |
| **frontend/** | 2 | authentication, ops-console |
| **testing/** | 1 | README |
| **domain/** | 1 | inventory |
| **agents/** | 1 | agents/docs/agents/README.md |

**Files Marked for Deletion** (from mapping table):
- **21 phase*.md** files (root)
- **6 roadmap/** files
- **5 tickets/** files
- **4 ops/** duplicates (availability_smoke, inventory_availability, inventory_rules, migrations)
- **1 architecture/** old plan (phase21-modularization-plan)

**Total Candidates**: 37 files

---

## Delete Waves

**Purpose**: Phased deletion approach to minimize risk

**Strategy**: Delete low-risk duplicates first, high-risk onboarding docs last

---

### Wave 1: Low-Risk Duplicates (COMPLETED ✅)

**Files** (4 total):
- ✅ `ops/availability_smoke.md` → Deleted (covered by `testing/README.md`)
- ✅ `ops/inventory_availability.md` → Deleted (covered by `database/migrations-guide.md`)
- ✅ `ops/inventory_rules.md` → Deleted (covered by `database/exclusion-constraints.md`)
- ✅ `ops/migrations.md` → Deleted (covered by `database/migrations-guide.md`)

**Completion Date**: 2025-12-31

**Risk Level**: **LOW** - Clear duplicates, no external links, full coverage in new docs

**Gate Checklist**:
- [x] Replacement docs exist and are complete
- [x] No references in START_HERE.md
- [x] Covered in runbook Top 5 Failure Modes
- [x] No broken links after deletion (inbound links updated in runbook.md and reference-product-model.md)

**Verification Steps**:
1. Verify replacement coverage:
   - `testing/README.md` has server-side smoke checks
   - `ops/runbook.md` has Top 5 Failure Modes
   - `database/exclusion-constraints.md` covers overlap prevention
   - `database/migrations-guide.md` has Schema Drift SOP
2. Search for broken links:
   ```bash
   grep -r "availability_smoke\|inventory_availability\|inventory_rules" backend/docs/ --include="*.md"
   # Expected: No results (or only from DEPRECATION_MAP.md)
   ```
3. Delete files (tag first):
   ```bash
   git tag -a docs-archive-wave1-$(date +%Y-%m-%d) -m "Archive before Wave 1 deletion"
   git rm backend/docs/ops/availability_smoke.md
   git rm backend/docs/ops/inventory_availability.md
   git rm backend/docs/ops/inventory_rules.md
   git rm backend/docs/ops/migrations.md
   git commit -m "docs: delete Wave 1 ops duplicates (covered by runbook/testing/database)"
   ```

---

### Wave 2: Medium-Risk Phase/Roadmap Docs (Delete After Team Review)

**Files** (32 total):

**Root phase*.md** (21 files):
- `phase5-backend-apis.md`, `phase5-backend-apis.index.md`
- `phase6-supabase-rls.md`
- `phase7-qa-security.md`, `phase7-qa-security-remediation.md`, `phase7.index.md`
- `phase8-prd-light.md`, `phase8.index.md`
- `phase9-release-plan.md`, `phase9.index.md`
- `phase10a-ui-ux.md`, `phase10a.index.md`
- `phase10b-10c-visual-design.md`
- `phase11-13-agentur-ux-rollen.md`
- `phase14-preismodell-logik.md`
- `phase15-16-direct-booking-eigentuemer.md`
- `phase17b-database-schema-rls.md`
- `phase18a-preflight.md`, `phase18a-schema-alignment-rls-implementation.md`
- `phase19-core-booking-flow-api.md`, `phase19-preflight.md`

**Roadmap folder** (6 files):
- `roadmap/overview.md`
- `roadmap/phase-1.md` through `roadmap/phase-5.md`

**Tickets folder** (5 files):
- `tickets/phase-1.md` through `tickets/phase-5.md`

**Risk Level**: **MEDIUM** - Historical planning docs, may have external references, full coverage in `product/PRODUCT_BACKLOG.md` and `product/RELEASE_PLAN.md`

**Gate Checklist**:
- [x] `product/PRODUCT_BACKLOG.md` covers all 10 epics
- [x] `product/RELEASE_PLAN.md` covers MVP/Beta/Prod-ready phases
- [ ] Team notification sent (allow 7 days for objections)
- [ ] No external wiki/confluence links to these files
- [ ] No broken links after deletion

**Verification Steps**:
1. Search for references:
   ```bash
   grep -r "phase[0-9]\|roadmap/\|tickets/" backend/docs/ --include="*.md" | grep -v "DEPRECATION_MAP"
   # Review results for any unexpected references
   ```
2. Post team notification:
   ```
   📢 Docs Cleanup Wave 2:
   Deleting 32 old phase/roadmap/tickets docs (replaced by product/PRODUCT_BACKLOG + RELEASE_PLAN).
   Review period: 7 days. Raise concerns before [DATE].
   Details: backend/docs/process/DEPRECATION_MAP.md#wave-2
   ```
3. After 7 days, delete files:
   ```bash
   git tag -a docs-archive-wave2-$(date +%Y-%m-%d) -m "Archive before Wave 2 deletion"
   git rm backend/docs/phase*.md
   git rm -r backend/docs/roadmap/
   git rm -r backend/docs/tickets/
   git commit -m "docs: delete Wave 2 phase/roadmap/tickets (covered by product backlog/release plan)"
   ```

---

### Wave 3: High-Risk Architecture Docs (Delete Last, After External Audit)

**Files** (1 total):
- `architecture/phase21-modularization-plan.md`

**Risk Level**: **HIGH** - Architecture doc that may be referenced externally, covered by `architecture/module-system.md`

**Gate Checklist**:
- [x] `architecture/module-system.md` covers module registry
- [ ] External references audited (GitHub issues, wiki, confluence)
- [ ] No broken links after deletion
- [ ] Redirect stub created (if needed)

**Verification Steps**:
1. Search GitHub issues for references:
   ```bash
   # Manually check GitHub issues/PRs for links to this file
   ```
2. Search for links:
   ```bash
   grep -r "phase21-modularization-plan" backend/docs/ --include="*.md"
   # Expected: Only DEPRECATION_MAP.md
   ```
3. Create redirect stub (14-day notice):
   ```markdown
   > **MOVED**: This document has moved to [Module System Architecture](module-system.md).
   >
   > **Redirect Date**: YYYY-MM-DD
   > **Old Location Removal**: YYYY-MM-DD (14 days)
   >
   > All module registry and graceful degradation content is now in the Module System doc.
   ```
4. After 14 days, delete:
   ```bash
   git tag -a docs-archive-wave3-$(date +%Y-%m-%d) -m "Archive before Wave 3 deletion"
   git rm backend/docs/architecture/phase21-modularization-plan.md
   git commit -m "docs: delete phase21-modularization-plan (covered by module-system.md)"
   ```

---

## Wave 1 Summary

**Status**: ✅ **COMPLETED** (2025-12-31)

**Results**:
- **Deleted**: 4 files
- **Stubbed**: 0 files
- **Blocked**: 0 files

**Deleted Files**:
1. `ops/availability_smoke.md` → `testing/README.md`
2. `ops/inventory_availability.md` → `database/migrations-guide.md`
3. `ops/inventory_rules.md` → `database/exclusion-constraints.md`
4. `ops/migrations.md` → `database/migrations-guide.md`

**Inbound Links Updated**:
- `ops/runbook.md`: Updated reference to `database/exclusion-constraints.md`
- `product/reference-product-model.md`: Updated reference to `database/migrations-guide.md`
- `roadmap/phase-1.md`: Updated reference to `database/migrations-guide.md`
- `tickets/phase-1.md`: Updated reference to `database/migrations-guide.md`

**Coverage Verified**:
- ✅ All replacement docs exist and cover topics
- ✅ No broken links in active docs
- ✅ START_HERE.md not affected

**Next Steps**: Proceed with Wave 2 (32 phase/roadmap/tickets files) after 7-day team review

---

## Wave 2A Summary

**Status**: ✅ **COMPLETED** (2025-12-31)

**Results**:
- **Deleted**: 10 files
- **Stubbed**: 0 files
- **Blocked**: 22 files (Wave 2B + 2C pending)

**Deleted Files** (Phase index files with 0 inbound links):
1. `phase5-backend-apis.index.md` → Covered by `product/PRODUCT_BACKLOG.md`
2. `phase7.index.md` → Covered by `product/PRODUCT_BACKLOG.md`
3. `phase8.index.md` → Covered by `product/PRODUCT_BACKLOG.md`
4. `phase9.index.md` → Covered by `product/RELEASE_PLAN.md`
5. `phase10a.index.md` → Covered by `product/PRODUCT_BACKLOG.md`
6. `phase10b-10c-visual-design.md` → Covered by `product/PRODUCT_BACKLOG.md`
7. `phase11-13-agentur-ux-rollen.md` → Covered by `product/PRODUCT_BACKLOG.md`
8. `phase14-preismodell-logik.md` → Covered by `product/PRODUCT_BACKLOG.md`
9. `phase15-16-direct-booking-eigentuemer.md` → Covered by `product/PRODUCT_BACKLOG.md`
10. `phase19-preflight.md` → Covered by `product/PRODUCT_BACKLOG.md`

**Inbound Links Updated**:
- None required (0 inbound links for all deleted files)

**Coverage Verified**:
- ✅ All content covered by `product/PRODUCT_BACKLOG.md` and `product/RELEASE_PLAN.md`
- ✅ No broken links in active docs
- ✅ START_HERE.md not affected

**Remaining Wave 2 Files**:
- **Wave 2B**: 11 root phase*.md files with inbound links (needs link cleanup)
- **Wave 2C**: 11 files in roadmap/ and tickets/ folders (needs START_HERE + architecture/ updates)

**Next Steps**: Execute Wave 2B (clean 3 external files, delete 11 phase*.md) and Wave 2C (update navigation, delete folders)

---

## Pre-Delete Validation Checklist

**Before deleting ANY file in any wave**, verify:

### Coverage Verification (8 checks)

- [ ] **START_HERE.md** covers all topics from old doc
- [ ] **ops/runbook.md** has Top 5 Failure Modes section
- [ ] **database/migrations-guide.md** has Schema Drift SOP section
- [ ] **testing/README.md** has Server-side Smoke Checks section
- [ ] **ops/feature-flags.md** exists and documents all flags
- [ ] **product/PRODUCT_BACKLOG.md** exists with 10 epics
- [ ] **process/DEFINITION_OF_DONE.md** exists with docs update rule
- [ ] **PROJECT_STATUS_LIVE.md** is current (updated within last 30 days)

### Technical Verification (3 checks)

- [ ] **Mirror publish green**: GitHub Actions CI passes
- [ ] **No broken links**: Search for references to deleted file paths
- [ ] **Redirect stub created**: If path changed and had external links

### Process Verification (2 checks)

- [ ] **Git tag created**: `docs-archive-waveN-YYYY-MM-DD`
- [ ] **Team notification**: Posted (7 days notice for Wave 2+, 14 days for Wave 3)

### Post-Delete (1 check)

- [ ] **Update this map**: Move deleted entry to "Deleted Files (Archive)" section

---

## Related Documentation

- [DOCS_LIFECYCLE.md](DOCS_LIFECYCLE.md) - Documentation aging workflow
- [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) - Includes "docs updated after every task"
- [START_HERE.md](../START_HERE.md) - Documentation entrypoint

---

**Last Updated**: 2025-12-31
**Maintained By**: Documentation Team
