# Documentation Map

**Generated**: 2025-12-30
**Commit**: `393ba8da51b67fdd832b92232c43c524c3edec88`

This document inventories all existing documentation in the PMS-Webapp repository.

---

## Documentation Structure

```
backend/docs/
├── architecture/
│   ├── error-taxonomy.md          ✅ Accurate (Phase 1 - P1-06)
│   └── modules-and-entitlements.md (referenced but not read)
├── ops/
│   └── migrations.md              (referenced but not verified)
├── roadmap/
│   ├── overview.md                (referenced but not read)
│   ├── phase-1.md                 ✅ Read (comprehensive spec)
│   ├── phase-2.md                 (likely exists, not verified)
│   ├── phase-3.md                 (likely exists, not verified)
│   ├── phase-4.md                 (likely exists, not verified)
│   └── phase-5.md                 (likely exists, not verified)
├── tickets/
│   └── phase-1.md                 (referenced but not read)
└── _staging/
    └── status-review-v1/          ⬅️ THIS FOLDER
        ├── START_HERE.md
        ├── DOCS_MAP.md            ⬅️ YOU ARE HERE
        ├── PROJECT_STATUS.md      (being generated)
        ├── DRIFT_REPORT.md        (being generated)
        └── MANIFEST.md            (being generated)
```

---

## Key Documentation Files

### Phase 1 Roadmap
**Path**: `backend/docs/roadmap/phase-1.md`
**Status**: ✅ Accurate and comprehensive
**Last Updated**: 2025-12-30 (based on file evidence)

**Content Summary**:
- Sprint 1 of 5, 2-week duration
- **MUST**: RBAC, tenant isolation, migrations, error taxonomy, 503 degraded mode, ops endpoints
- **SHOULD**: Audit log, idempotency keys, feature flags
- **COULD**: Automated RLS tests, error response validation, alerting

**Deliverables**:
1. P1-01: RBAC Finalization (has_role, has_any_role, require_role)
2. P1-02: Tenant Isolation Audit
3. P1-03: Mandatory Migrations Workflow
4. P1-06: Error Taxonomy (error codes, typed exceptions)
5. P1-07: 503 Degraded Mode
6. P1-08: `/ops/current-commit` endpoint
7. P1-09: `/ops/env-sanity` endpoint

**Verification**: File read confirms structure and P1-01/P1-06 match implementation.

---

### Error Taxonomy Documentation
**Path**: `backend/docs/architecture/error-taxonomy.md`
**Status**: ✅ Accurate and up-to-date
**Last Updated**: 2025-12-30

**Content Summary**:
- Error code constants (BOOKING_CONFLICT, PROPERTY_NOT_FOUND, etc.)
- Base `AppError` class
- 3 typed exceptions: `BookingConflictError`, `PropertyNotFoundError`, `NotAuthorizedError`
- **IMPORTANT**: Clearly states P1-06 implemented, P1-07 (response format) pending

**Verification**: Matches implementation in `app/core/exceptions.py`.

---

### Unit Tests
**Path**: `backend/tests/unit/test_rbac_helpers.py`
**Status**: ✅ Comprehensive but NOT EXECUTED
**Last Updated**: 2025-12-30

**Content Summary**:
- Tests for `has_role()` (10 test cases)
- Tests for `has_any_role()` (9 test cases)
- Edge cases: case sensitivity, whitespace, payload fallback
- **WARNING**: Tests marked "DO NOT RUN THESE TESTS YET" - Phase 1 foundation

**Verification**: File contains tests but they have not been executed yet.

---

## Documentation Quality Assessment

### ✅ Accurate Documentation
1. **error-taxonomy.md**: Matches implementation perfectly
2. **phase-1.md**: Roadmap aligns with current progress
3. **test_rbac_helpers.py**: Tests match function signatures

### ⚠️ Incomplete Documentation
1. **modules-and-entitlements.md**: Referenced but not verified (may not exist)
2. **ops/migrations.md**: Referenced but not verified
3. **tickets/phase-1.md**: Referenced but not read

### ❌ Missing Documentation
1. **Channel Manager Architecture**: No docs found for channel_manager/
2. **Availability System**: No dedicated doc for inventory_ranges/EXCLUSION constraints
3. **Frontend Architecture**: No docs for Next.js App Router structure
4. **API Reference**: No OpenAPI/Swagger docs inventory

---

## Documentation Conventions

### File Naming
- Roadmap: `phase-{N}.md` (numbered phases)
- Architecture: `{topic}.md` (descriptive names)
- Tickets: `phase-{N}.md` (backlog per phase)

### Cross-references
- Most docs use relative paths: `../roadmap/phase-1.md`
- Format: `[Link Text](../relative/path.md)`

### Status Markers
- ✓ Checkmarks for completed items
- [ ] Unchecked boxes for pending
- TODO/STUB comments in code for placeholders

---

## Related Documents

- **PROJECT_STATUS.md**: Code-derived status (what's actually implemented)
- **DRIFT_REPORT.md**: Where docs diverge from reality
- **MANIFEST.md**: Evidence log for all claims

---

## How to Update This Map

When adding new documentation:
1. Add file path to structure tree above
2. Add summary entry with status emoji (✅/⚠️/❌)
3. Update relevant sections in PROJECT_STATUS.md
4. Commit with message: `docs: add {file} to documentation map`

---

**Last Scan**: 2025-12-30 17:34:20 UTC
**Next Review**: After Phase 1 completion
