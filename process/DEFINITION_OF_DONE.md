# Definition of Done

**Purpose**: Standard checklist for task completion

**Audience**: Developers, QA engineers, Product Owners

**Source of Truth**: This file defines what "done" means across all work items

---

## Universal Definition of Done

All tasks (features, bugs, refactors, spikes) must meet these criteria before being marked complete:

### 1. Code Quality

- ✅ Code follows project style guide (ruff for Python, ESLint for TypeScript)
- ✅ Type checking passes (mypy for Python, TypeScript strict mode)
- ✅ No linting errors or warnings
- ✅ Code reviewed by at least one team member (if applicable)
- ✅ No commented-out code or debug statements in committed code

---

### 2. Functionality

- ✅ Acceptance criteria met (as defined in task/ticket)
- ✅ Edge cases handled (null values, empty strings, boundary conditions)
- ✅ Error handling implemented (typed exceptions per [Error Taxonomy](../architecture/error-taxonomy.md))
- ✅ RBAC enforced (if endpoint requires authorization)
- ✅ Multi-tenancy isolation verified (agency_id checks, RLS policies)

---

### 3. Testing

**Server-Side Workflow** (official):
- ✅ Smoke tests pass on server after deployment

**Optional (Contributor Only)**:
- Unit tests written for business logic (if applicable)
- Integration tests written for API endpoints (if applicable)

**Related Docs**: [Testing Guide](../testing/README.md)

---

### 4. Documentation

**CRITICAL REQUIREMENT**: Documentation must be updated after every task.

- ✅ **Code comments** added for non-obvious logic
- ✅ **API documentation** updated (if endpoint added/modified)
- ✅ **Architecture docs** updated (if design changed)
- ✅ **Runbook** updated (if new failure mode introduced)
- ✅ **Migration guide** updated (if database schema changed)
- ✅ **Feature flags** updated (if new flag added or behavior changed)
- ✅ **CHANGELOG** updated (if user-facing change)

**Where to Update**:
- Architecture changes → `backend/docs/architecture/`
- Database changes → `backend/docs/database/`
- Ops changes → `backend/docs/ops/`
- Product changes → `backend/docs/product/CHANGELOG.md`

**Docs Sync (Required)**:
- ✅ **Mark task Done** in `product/PRODUCT_BACKLOG.md` (update status, link to PR/commit)
- ✅ **Update `PROJECT_STATUS_LIVE.md`** (reflect actual deployment state, flags, known issues)
- ✅ **Update ops docs** (if relevant): `ops/runbook.md`, `testing/README.md`, `ops/feature-flags.md`

See [DOCS_LIFECYCLE.md](DOCS_LIFECYCLE.md) for full workflow and deprecation process.

---

### 5. Database Migrations

(If database schema changed)

- ✅ Migration file created with UTC timestamp prefix
- ✅ Migration uses idempotent operations (`IF NOT EXISTS`, `IF EXISTS`)
- ✅ Migration tested locally (`supabase start`)
- ✅ Migration applied to staging before production
- ✅ Rollback plan documented (if destructive change)

**Related Docs**: [Migrations Guide](../database/migrations-guide.md)

---

### 6. Deployment

- ✅ Environment variables documented (if new env vars added)
- ✅ Feature flags configured correctly (if feature gated)
- ✅ Backward compatibility verified (if breaking change)
- ✅ Deployed to staging and verified working
- ✅ Smoke tests pass on staging

**Related Docs**: [Feature Flags](../ops/feature-flags.md), [Runbook](../ops/runbook.md)

---

### 7. Security

- ✅ No secrets committed to git
- ✅ No SQL injection vulnerabilities
- ✅ No XSS vulnerabilities (frontend)
- ✅ JWT validation enforced (if authenticated endpoint)
- ✅ Input validation implemented (Pydantic schemas for API)

---

## Task-Specific DoD

### Feature Development

In addition to Universal DoD:

- ✅ Product Owner acceptance
- ✅ UX/UI design implemented per spec (if UI change)
- ✅ User-facing documentation updated (if applicable)
- ✅ CHANGELOG.md updated with feature description

---

### Bug Fixes

In addition to Universal DoD:

- ✅ Root cause identified and documented
- ✅ Fix verified in production-like environment
- ✅ Regression test added (if applicable)
- ✅ Related bugs checked for similar issues

---

### Refactoring

In addition to Universal DoD:

- ✅ No behavioral changes (existing tests still pass)
- ✅ Performance impact measured (if performance-related)
- ✅ Code coverage maintained or improved
- ✅ Architecture docs updated to reflect new structure

---

### Database Schema Changes

In addition to Universal DoD:

- ✅ Migration applied successfully in staging
- ✅ Data integrity verified (constraints, foreign keys)
- ✅ Index strategy reviewed (per [Index Strategy](../database/index-strategy.md))
- ✅ RLS policies updated (if new table or column)
- ✅ Schema drift check passed (`supabase db diff`)

---

### Documentation Tasks

(Meta: updating docs)

- ✅ Technical accuracy verified against code
- ✅ Links to related docs added
- ✅ Examples provided (where applicable)
- ✅ Troubleshooting section added (where applicable)
- ✅ Last Updated date updated

---

## Checklist for Task Closure

Before marking task as "Done" in project management system:

1. ☑️ All applicable DoD criteria met
2. ☑️ Code merged to main branch (if code change)
3. ☑️ Documentation updated (ALWAYS)
4. ☑️ Deployed to staging and verified
5. ☑️ Smoke tests pass
6. ☑️ Stakeholders notified (if user-facing change)

---

## Exceptions

**When DoD can be relaxed** (requires explicit approval):

- Spike tasks (research/exploration only)
- Proof-of-concept work (not intended for production)
- Emergency hotfixes (retrospective compliance required)

**Emergency Hotfix Process**:
1. Fix deployed immediately (skip non-critical DoD items)
2. Retrospective compliance within 24 hours (tests, docs, review)
3. Post-mortem added to runbook

---

## Enforcement

**Code Review**: Reviewers must verify DoD compliance before approving PR

**CI/CD**: Automated checks enforce linting, type checking, smoke tests

**Team Responsibility**: Every team member is responsible for upholding DoD

---

## Related Documentation

- [DOCS_LIFECYCLE.md](DOCS_LIFECYCLE.md) - How to deprecate and migrate docs
- [RELEASE_CADENCE.md](RELEASE_CADENCE.md) - When/how we release
- [Testing Guide](../testing/README.md) - Testing workflow
- [Runbook](../ops/runbook.md) - Operational troubleshooting

---

**Last Updated**: 2025-12-31
**Maintained By**: Engineering Team
