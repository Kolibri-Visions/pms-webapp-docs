# Release Cadence

**Purpose**: Define when and how we release software to production

**Audience**: Engineering Team, Product Owners, Stakeholders

**Source of Truth**: This file defines release schedule and process

---

## Overview

**Release Strategy**: Continuous deployment to staging, scheduled releases to production

**Staging**: Every merge to `main` triggers deployment to staging

**Production**: Bi-weekly releases (every 2 weeks) OR on-demand for critical fixes

---

## Release Schedule

### Staging Releases

**Trigger**: Every commit merged to `main` branch

**Deployment**: Automatic via CI/CD (Coolify)

**Environment**: https://api.fewo.kolibri-visions.de (staging backend)

**Purpose**:
- Validate changes in production-like environment
- Run smoke tests
- Allow stakeholders to preview features

**SLA**: Deployed within 5 minutes of merge

---

### Production Releases

**Schedule**: Bi-weekly on Thursdays at 10:00 UTC

**Next Release Dates** (example):
- 2026-01-09 (Thu)
- 2026-01-23 (Thu)
- 2026-02-06 (Thu)

**Deployment Window**: 10:00-12:00 UTC (2 hours)

**Freeze Period**: No merges to `main` during deployment window

---

## Release Types

### 1. Scheduled Release (Bi-weekly)

**What**: All features/fixes merged to `main` since last release

**Process**:
1. **Monday (3 days before)**: Code freeze announced, QA testing begins on staging
2. **Wednesday (1 day before)**: Final smoke tests, go/no-go decision
3. **Thursday (release day)**: Deploy to production, monitor for 2 hours
4. **Friday (1 day after)**: Retrospective if issues occurred

**Rollback Plan**: Revert to previous release tag if critical issues found

---

### 2. Hotfix Release (On-Demand)

**What**: Critical bug fix or security patch

**Criteria for Hotfix**:
- Production outage (P0)
- Security vulnerability (CVSS > 7.0)
- Data integrity issue
- Critical business blocker

**Process**:
1. Create hotfix branch from `main`: `hotfix/YYYY-MM-DD-description`
2. Implement fix, test locally
3. Deploy to staging, run smoke tests
4. Get approval from Tech Lead + Product Owner
5. Deploy to production immediately
6. Retrospective within 24 hours (per [DoD Emergency Hotfix Process](DEFINITION_OF_DONE.md#exceptions))

**SLA**: Deploy within 4 hours of approval

---

### 3. Feature Flag Release (Gradual Rollout)

**What**: Deploy feature to production but keep disabled via feature flag

**Use Cases**:
- Large features requiring phased rollout
- Beta testing with select users
- Features requiring external dependencies (e.g., Channel Manager)

**Process**:
1. Deploy code to production with feature flag `false`
2. Enable feature flag for internal testing
3. Enable for beta users (if applicable)
4. Monitor metrics, gather feedback
5. Enable for all users OR rollback if issues

**Feature Flags**: See [Feature Flags Reference](../ops/feature-flags.md)

**Examples**:
- `CHANNEL_MANAGER_ENABLED` (default: false)
- `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` (frontend)

---

## Release Artifacts

### Version Tagging

**Format**: `vMAJOR.MINOR.PATCH` (Semantic Versioning)

**Examples**:
- `v1.0.0` - Initial MVP release
- `v1.1.0` - New feature (minor version bump)
- `v1.1.1` - Bug fix (patch version bump)
- `v2.0.0` - Breaking change (major version bump)

**Tagging Command**:
```bash
git tag -a v1.2.0 -m "Release v1.2.0 - Add Channel Manager sync"
git push origin v1.2.0
```

---

### Release Notes

**Location**: `backend/docs/product/CHANGELOG.md`

**Format**:
```markdown
## [1.2.0] - 2026-01-23

### Added
- Channel Manager sync for Airbnb (Phase 17A)
- Bulk availability upload API

### Fixed
- Double-booking prevention via EXCLUSION constraint

### Changed
- Upgraded FastAPI to 0.115.0
```

**Must Include**:
- Version number + release date
- User-facing changes (Added/Fixed/Changed/Removed)
- Link to related docs or tickets

**Related**: See [CHANGELOG.md](../product/CHANGELOG.md) for full history

---

## Pre-Release Checklist

**Before every production release**, verify:

### Code Quality
- ✅ All CI/CD checks pass (linting, type checking)
- ✅ No critical security vulnerabilities (Dependabot alerts)
- ✅ Code review completed for all changes

### Testing
- ✅ Smoke tests pass on staging
- ✅ Integration tests pass (if run locally by contributors)
- ✅ Manual QA completed for new features

### Documentation
- ✅ CHANGELOG.md updated with all user-facing changes
- ✅ API documentation updated (if endpoints changed)
- ✅ Runbook updated (if new failure modes introduced)
- ✅ Feature flags documented (if new flags added)

### Database
- ✅ Migrations applied successfully in staging
- ✅ Schema drift check passed (`supabase db diff` shows no drift)
- ✅ RLS policies verified (multi-tenancy isolation working)

### Environment
- ✅ Environment variables configured in production (if new vars added)
- ✅ Feature flags set correctly (per [Feature Flags](../ops/feature-flags.md))
- ✅ Database connection verified (health checks pass)

### Stakeholder Communication
- ✅ Release notes shared with Product Owner
- ✅ Breaking changes communicated to affected teams
- ✅ Downtime window announced (if applicable)

---

## Post-Release Checklist

**After production deployment**:

### Verification
- ✅ Health check passes: `curl https://api.fewo.kolibri-visions.de/health`
- ✅ Readiness check passes: `curl https://api.fewo.kolibri-visions.de/health/ready`
- ✅ Smoke tests pass on production
- ✅ Key user flows tested (login, create booking, etc.)

### Monitoring
- ✅ No error spikes in logs (first 30 minutes)
- ✅ Response times normal (compare to baseline)
- ✅ Database connections stable

### Communication
- ✅ Release announcement posted (team chat, stakeholders)
- ✅ Monitoring dashboard shared (if metrics exist)

### Rollback Plan
- ✅ Previous version tag known: `git tag -l | tail -1`
- ✅ Rollback procedure documented (if not standard)

---

## Rollback Procedure

**If critical issue found post-release**:

### Step 1: Assess Severity

**P0 (Immediate rollback)**:
- Production outage
- Data corruption
- Security breach

**P1 (Rollback within 1 hour)**:
- Major feature broken
- Performance degradation > 50%

**P2 (Fix forward)**:
- Minor bugs
- Non-critical features broken

---

### Step 2: Execute Rollback

**Option A: Revert to Previous Tag** (preferred):
```bash
# Check current version
git describe --tags

# Rollback to previous tag
git checkout v1.1.0

# Deploy to production
# (Deployment command varies by platform - see Coolify/CI/CD config)
```

**Option B: Revert Specific Commit**:
```bash
# Revert problematic commit
git revert <commit-hash>

# Push to main
git push origin main

# Auto-deploys to staging, then promote to production
```

---

### Step 3: Verify Rollback

- ✅ Health checks pass
- ✅ Smoke tests pass
- ✅ Issue resolved

---

### Step 4: Post-Mortem

**Within 24 hours of rollback**:
1. Write incident report (what happened, why, how to prevent)
2. Update runbook with new failure mode
3. Create tickets to fix root cause
4. Share findings with team

**Template**: See [Runbook](../ops/runbook.md) for incident report format

---

## Release Metrics

**Track release health**:

- **Deployment Frequency**: Target 26 releases/year (bi-weekly)
- **Lead Time**: Time from commit to production (target < 2 weeks)
- **MTTR** (Mean Time To Recover): Time to rollback if issue found (target < 1 hour)
- **Change Failure Rate**: % of releases requiring rollback (target < 5%)

**Review Quarterly**: Adjust cadence if metrics degrade

---

## Exceptions

### Expedited Release

**Scenario**: Critical feature needed before next bi-weekly release

**Approval Required**: Tech Lead + Product Owner

**Process**: Same as Hotfix Release (but for features, not bugs)

---

### Release Postponement

**Scenario**: Critical bug found in staging, release not ready

**Decision Maker**: Tech Lead

**Process**:
1. Announce postponement (team + stakeholders)
2. Fix bug, retest in staging
3. Reschedule release (typically +1 week)

---

## Related Documentation

- [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) - What must be completed before release
- [RELEASE_PLAN.md](../product/RELEASE_PLAN.md) - MVP → Beta → Prod-ready milestones
- [CHANGELOG.md](../product/CHANGELOG.md) - Release history
- [Runbook](../ops/runbook.md) - Production troubleshooting
- [Feature Flags](../ops/feature-flags.md) - Feature flag reference

---

**Last Updated**: 2025-12-31
**Maintained By**: Engineering Team
