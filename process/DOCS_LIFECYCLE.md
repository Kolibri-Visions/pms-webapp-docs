# Docs Lifecycle

**Purpose**: Establish single source of truth for planning and ensure docs stay in sync with real code and deployments.

**Audience**: All contributors

---

## Canonical Docs (Must Remain Canonical)

These docs are the single source of truth. Never create duplicates (e.g., roadmap/, tickets/ folders).

| Doc | Purpose | Update Frequency |
|-----|---------|------------------|
| **product/PRODUCT_BACKLOG.md** | Planning - 10 epics (A-J), features, tasks | Start/finish work |
| **product/RELEASE_PLAN.md** | Release milestones (MVP → Beta → Prod-ready) | Major releases |
| **process/DEFINITION_OF_DONE.md** | Task completion criteria | Rarely (process changes) |
| **PROJECT_STATUS_LIVE.md** | Current deployment status, flags, known issues | After deploys, config changes |
| **process/DEPRECATION_MAP.md** | Historical tracking of deleted docs | When deprecating/deleting docs |

---

## When You Start Work

**Before writing code**, update planning docs:

- [ ] **Pick a task** in `product/PRODUCT_BACKLOG.md`
  - Mark status: `Planned` → `In Progress`
  - Assign yourself if tracking assignments
- [ ] **Check feature flags** (if relevant)
  - Reference `ops/feature-flags.md` if feature is gated
  - Ensure flag is documented before implementation
- [ ] **Check dependencies**
  - Review epic dependencies in PRODUCT_BACKLOG
  - Ensure prerequisite tasks are complete

**Never create** new roadmap/ or tickets/ docs. All planning lives in PRODUCT_BACKLOG + RELEASE_PLAN.

---

## When You Finish Work (Done)

**After merging code**, update docs to reflect live state:

### 1. Update Planning Docs

- [ ] **Mark task Done** in `product/PRODUCT_BACKLOG.md`
  - Update status: `In Progress` → `Done`
  - Link to PR/commit (if available): `[#123](https://github.com/...)`
  - Move to "Completed" section if epic structure supports it

### 2. Update Live Status

- [ ] **Update `PROJECT_STATUS_LIVE.md`**
  - Reflect actual deployment state (what's live NOW)
  - Update feature flags if changed (e.g., `MODULES_ENABLED=true`)
  - Close resolved known issues
  - Add new known issues if discovered

### 3. Update Ops Docs (If Relevant)

- [ ] **If ops impact** (new endpoints, env vars, failure modes):
  - Update `ops/runbook.md` (troubleshooting, Top 5 Failure Modes)
  - Update `testing/README.md` (smoke checks, new test cases)
  - Update `ops/feature-flags.md` (new flags, flag changes)

### 4. Follow Definition of Done

- [ ] **Check `process/DEFINITION_OF_DONE.md`**
  - Ensure all criteria met (tests, docs, no regressions)
  - Docs updated is MANDATORY (not optional)

---

## Rules (Anti-Duplication)

### ✅ Do This

- **Planning**: Use PRODUCT_BACKLOG.md + RELEASE_PLAN.md only
- **Status**: Update PROJECT_STATUS_LIVE.md after every deploy/config change
- **Snapshots**: Use `_staging/` for code-derived snapshots only (commit-bound, read-only)
- **Deprecation**: Add to DEPRECATION_MAP.md first, then delete via cleanup wave

### ❌ Never Do This

- **No roadmap/ or tickets/ folders** (deleted in Wave 2, don't recreate)
- **No phase*.md planning docs** (deleted in Waves 2-3, don't recreate)
- **No duplicate planning docs** (if it's planning, it goes in PRODUCT_BACKLOG)
- **Never link from START_HERE.md to _staging/** (snapshots are historical, not active)

---

## Deprecating Docs

If a doc becomes obsolete:

1. **Add entry** to `process/DEPRECATION_MAP.md`:
   - OLD path → NEW canonical path
   - Coverage notes (what replaces it)
   - Deletion wave assignment (Wave 1/2/3/etc.)
2. **Update inbound links** to point to canonical replacement
3. **Delete via cleanup wave** (verify no broken links first)
4. **Never delete** without DEPRECATION_MAP entry

**Precedent**: Waves 1-3 deleted 37 files (ops duplicates, roadmap/, tickets/, phase21 plan) using this process.

---

## Quick Reference

**Starting work?**
→ Update PRODUCT_BACKLOG (mark In Progress)

**Finished work?**
→ Update PRODUCT_BACKLOG (mark Done) + PROJECT_STATUS_LIVE (live state) + ops docs (if needed)

**Need to delete a doc?**
→ Add to DEPRECATION_MAP first, then cleanup wave

**Need to plan work?**
→ Add to PRODUCT_BACKLOG (epics A-J), never create roadmap/tickets/phase* files

---

**Last Updated**: 2025-12-31
**Maintained By**: Team
