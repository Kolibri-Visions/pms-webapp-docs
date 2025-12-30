# Documentation Lifecycle

**Purpose**: Define how documentation evolves, ages, and gets deprecated

**Audience**: Developers, Technical Writers, Maintainers

**Source of Truth**: This file defines the workflow for migrating and retiring old documentation

---

## Overview

Documentation has a lifecycle: **Create → Maintain → Deprecate → Verify → Delete**

This document defines the **Deprecate → Verify → Delete** workflow to prevent stale docs from accumulating.

---

## Documentation States

### 1. Active

**Definition**: Current, accurate documentation referenced in production workflow

**Indicators**:
- Referenced in START_HERE.md or other active docs
- Last Updated date within last 6 months
- Reflects current codebase state

**Maintenance**: Update after every related code change (per [DoD](DEFINITION_OF_DONE.md))

---

### 2. Deprecated

**Definition**: Documentation marked for removal but still available for reference

**When to Deprecate**:
- Feature removed from codebase
- Replaced by newer documentation
- Architecture changed significantly
- Migration completed (e.g., old API version sunsetted)

**How to Mark as Deprecated**:

```markdown
> **DEPRECATED**: This document is outdated. See [New Doc](link) instead.
>
> **Deprecation Date**: 2025-12-31
> **Removal Date**: 2026-01-31 (30 days)
> **Reason**: Feature removed in Phase XX
```

**Add to header** of deprecated doc.

---

### 3. Archived

**Definition**: Historical documentation moved to `_archive/` for reference

**When to Archive**:
- 30 days after deprecation (if no objections)
- Historical value (useful for understanding past decisions)
- Not actively maintained

**Archive Location**: `backend/docs/_archive/YYYY-MM/`

**Example**:
```bash
# Archive old module system doc
mv backend/docs/architecture/old-module-system.md \
   backend/docs/_archive/2025-12/old-module-system.md
```

---

### 4. Deleted

**Definition**: Documentation permanently removed from repository

**When to Delete**:
- No historical value (e.g., temporary spike docs)
- Superseded by active docs
- 90 days after archival (if never referenced)

**Before Deleting**:
1. ✅ Verify no active docs link to it
2. ✅ Check git history for context (can be recovered if needed)
3. ✅ Remove from any navigation (START_HERE.md, etc.)

---

## Deprecation Workflow

### Step 1: Identify Candidate for Deprecation

**Triggers**:
- Feature removed from codebase
- Code refactor makes doc obsolete
- Newer doc replaces old doc
- Scheduled review finds stale content

**Who Can Trigger**: Any team member

---

### Step 2: Mark as Deprecated

**Action**: Add deprecation notice to top of document

**Template**:
```markdown
> **DEPRECATED**: [Brief reason]
>
> **Deprecation Date**: [YYYY-MM-DD]
> **Removal Date**: [YYYY-MM-DD] (30 days from deprecation)
> **Reason**: [Detailed explanation]
> **Replacement**: [Link to new doc, or "N/A - feature removed"]
```

**Update Last Updated date** to deprecation date

**Commit Message**:
```
docs: deprecate [doc name] - [reason]
```

---

### Step 3: Notify Team

**Action**: Post in team chat / create ticket

**Message Template**:
```
📢 Documentation Deprecated:
- File: backend/docs/[path]
- Reason: [reason]
- Removal Date: [date]
- Replacement: [link or "N/A"]

Please review and raise concerns if this doc should remain active.
```

**Waiting Period**: 30 days (allows team to object)

---

### Step 4: Verify No Active References

**Before archiving/deleting**, verify no active docs link to deprecated doc:

```bash
# Search for references in active docs (exclude _archive and _staging)
cd backend/docs
grep -r "deprecated-doc-name" --exclude-dir=_archive --exclude-dir=_staging .

# Expected: No results (or only from deprecated docs)
```

**If references found**: Update referring docs to remove/replace links

---

### Step 5: Archive or Delete

**30 days after deprecation**:

**Option A: Archive** (if historical value):
```bash
# Create archive folder for current month
mkdir -p backend/docs/_archive/2026-01

# Move deprecated doc
mv backend/docs/architecture/old-feature.md \
   backend/docs/_archive/2026-01/old-feature.md

# Commit
git add backend/docs/_archive/2026-01/old-feature.md
git rm backend/docs/architecture/old-feature.md
git commit -m "docs: archive old-feature.md - feature removed in Phase XX"
```

**Option B: Delete** (if no historical value):
```bash
# Delete doc
git rm backend/docs/architecture/temp-spike.md

# Commit
git commit -m "docs: delete temp-spike.md - spike completed, no longer relevant"
```

---

## Special Cases

### Migrating Docs (Restructure)

**Scenario**: Moving docs to new location (e.g., `ops/runbook.md` → `ops/troubleshooting/runbook.md`)

**Workflow**:
1. Create new doc in new location
2. Add redirect notice to old doc:
   ```markdown
   > **MOVED**: This document has moved to [new location](link).
   >
   > **Redirect Date**: 2025-12-31
   > **Old Location Removal**: 2026-01-15 (15 days)
   ```
3. Update all references in active docs
4. Wait 15 days (shorter than deprecation since it's a move, not removal)
5. Delete old doc

---

### Versioned Docs (API Versions)

**Scenario**: API v1 docs deprecated, API v2 docs active

**Workflow**:
1. Keep v1 docs in `backend/docs/api/v1/` (archived)
2. Mark folder with deprecation notice in README:
   ```markdown
   # API v1 Documentation (DEPRECATED)

   **Deprecated**: 2025-12-31
   **Sunset Date**: 2026-06-30

   See [API v2 Documentation](../v2/) for current API.
   ```
3. After sunset date, archive entire `v1/` folder

---

### Snapshot Docs (Historical Reviews)

**Scenario**: Code-derived snapshots like `_staging/status-review-v3/`

**Workflow**:
- **Never deprecate**: Snapshots are historical records (commit-bound)
- **Never delete**: Useful for understanding past project state
- Mark as read-only in README:
  ```markdown
  > **READ-ONLY SNAPSHOT**: This folder is a historical snapshot from commit `7f34c7d`.
  > Do NOT update files in this folder. See [PROJECT_STATUS_LIVE.md](../../PROJECT_STATUS_LIVE.md) for current status.
  ```

---

## Scheduled Reviews

**Quarterly Documentation Health Check** (every 3 months):

1. ✅ Identify docs with "Last Updated" > 6 months ago
2. ✅ Review for accuracy against current codebase
3. ✅ Update or mark as deprecated
4. ✅ Check for broken links (`grep -r "](http" backend/docs/`)
5. ✅ Archive/delete deprecated docs past removal date

**Who**: Assigned rotating team member

**Output**: Document health report in team meeting

---

## Metrics

**Track documentation health**:

- **Active Docs**: Count of docs in `backend/docs/` (exclude `_archive`, `_staging`)
- **Deprecated Docs**: Count of docs with DEPRECATED notice
- **Stale Docs**: Count of docs with "Last Updated" > 6 months
- **Archived Docs**: Count of docs in `_archive/`

**Goal**: Keep stale docs < 10%, deprecated docs archived within 30 days

---

## Enforcement

**DoD Requirement**: See [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) - "Documentation must be updated after every task"

**Pull Request Reviews**: Reviewers verify related docs are updated

**CI/CD**: (Future) Automated link checker to catch broken references

---

## Related Documentation

- [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) - Includes "docs updated after every task" rule
- [RELEASE_CADENCE.md](RELEASE_CADENCE.md) - When/how we release
- [START_HERE.md](../START_HERE.md) - Documentation entrypoint

---

**Last Updated**: 2025-12-31
**Maintained By**: Engineering Team
