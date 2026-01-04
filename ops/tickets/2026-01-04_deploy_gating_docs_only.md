# Ops Ticket: Deploy Gating for Docs-Only Changes

**Date**: 2026-01-04
**Priority**: Medium
**Type**: Deployment Optimization
**Status**: Phase-1 (Ticket Created)

## Problem Statement

Currently, **all commits to main** trigger a container replace in production, even when changes are limited to documentation files (e.g., `*.md`, `docs/**`). This causes:

1. **Unnecessary downtime**: Documentation-only changes don't require application restart
2. **Duplicate startup signatures**: Container replace creates new PID=1 process with generation=1 logs
3. **Wasted compute**: Building/pushing/pulling unchanged container images
4. **Developer friction**: Docs contributors trigger production deployments unintentionally

**Example scenario**:
- Developer commits typo fix to `backend/docs/ops/runbook.md`
- CI/CD pipeline builds new Docker image (no code changes)
- Production container replaced (triggers startup logs, health checks, connection pool creation)
- No functional change delivered

## Current Behavior

```bash
# Current CI/CD logic (pseudocode)
git push origin main
  → Always build Docker image
  → Always push to registry
  → Always replace production container
  → Container restart creates duplicate startup signature
```

## Desired Behavior

```bash
# Desired CI/CD logic with deploy gating
git push origin main
  → Classify changes (docs-only vs code/config)
  → IF docs-only: Skip image build, skip container replace
  → IF code/config: Build image, replace container
  → Avoid unnecessary restarts for non-functional changes
```

## Acceptance Criteria

1. **Deploy classifier script** exists at `backend/scripts/ops/deploy_should_run.sh`
   - Takes git ref range (e.g., `HEAD~1..HEAD` or `$CI_COMMIT_BEFORE_SHA..$CI_COMMIT_SHA`)
   - Classifies changes as "docs-only" vs "needs-deploy"
   - Exit code 0 = needs deploy, Exit code 1 = skip deploy (docs-only)

2. **Documentation** exists in `backend/scripts/README.md` and `backend/docs/ops/runbook.md`
   - Explains deploy gating rationale
   - Shows example CI/CD integration patterns (GitHub Actions, GitLab CI, generic)
   - Documents edge cases (force deploy flag, initial deployment)

3. **Path classification rules** are clear and documented:
   - **Docs-only paths**: `*.md`, `docs/**`, `*.txt` (exclude requirements.txt)
   - **Always deploy paths**: `app/**`, `requirements.txt`, `Dockerfile`, `.env*`, `alembic/**`, `tests/**`, etc.

4. **CI/CD integration ready** (example snippets provided, not enforced)
   - GitHub Actions: `if: ${{ steps.deploy_gate.outputs.should_deploy == 'true' }}`
   - GitLab CI: `rules: - if: $DEPLOY_GATE_RESULT == "true"`

## Proposed Approach

### 1. Create Deploy Classifier Script

**File**: `backend/scripts/ops/deploy_should_run.sh`

```bash
#!/usr/bin/env bash
# Classifies git changes as docs-only or needs-deploy
# Exit 0 = needs deploy, Exit 1 = skip deploy

set -euo pipefail

# Usage: ./deploy_should_run.sh <git-ref-range>
# Example: ./deploy_should_run.sh HEAD~1..HEAD

REF_RANGE="${1:-HEAD~1..HEAD}"

# Get changed files
CHANGED_FILES=$(git diff --name-only "$REF_RANGE" || echo "")

if [ -z "$CHANGED_FILES" ]; then
  echo "No changes detected, skipping deploy"
  exit 1
fi

# Check if all changes are docs-only
DOCS_ONLY=true
while IFS= read -r file; do
  case "$file" in
    *.md|docs/*|*.txt)
      # Exclude requirements.txt
      if [[ "$file" == *requirements.txt ]]; then
        DOCS_ONLY=false
        break
      fi
      ;;
    *)
      # Non-docs file detected
      DOCS_ONLY=false
      break
      ;;
  esac
done <<< "$CHANGED_FILES"

if [ "$DOCS_ONLY" = true ]; then
  echo "Docs-only changes detected, skipping deploy"
  exit 1
else
  echo "Code/config changes detected, proceeding with deploy"
  exit 0
fi
```

### 2. Update Documentation

**Files to update**:
- `backend/docs/ops/runbook.md`: Add "Deploy Gating" section under Operations
- `backend/scripts/README.md`: Add `deploy_should_run.sh` documentation

### 3. CI/CD Integration Examples

Provide snippets for common platforms (GitHub Actions, GitLab CI) but don't enforce adoption in Phase-1.

## Phase-1 Scope (This Ticket)

- Create ticket markdown file (this file)
- Create `backend/scripts/ops/deploy_should_run.sh` helper script
- Update documentation (runbook.md, scripts/README.md, project_status.md)
- **DO NOT** modify CI/CD pipelines yet (Phase-2)

## Phase-2 Scope (Future)

- Integrate `deploy_should_run.sh` into actual CI/CD pipeline
- Add force-deploy environment variable override
- Monitor deployment frequency reduction
- Add metrics (deploy count, docs-only commit percentage)

## References

- Runbook: `backend/docs/ops/runbook.md` → "Deploy Gating" section
- Scripts: `backend/scripts/README.md` → "Deploy Gating Script"
- Project Status: `backend/docs/project_status.md` → Operations bullets

## Notes

- This is a **pure optimization** (no functional changes)
- Backwards compatible: Existing CI/CD continues to work if script not integrated
- Path classification rules may need tuning based on repository structure
- Consider `.github/**` and `.gitlab-ci.yml` changes (deploy or skip?)
