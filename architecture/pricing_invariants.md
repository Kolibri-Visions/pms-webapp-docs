# Pricing System Invariants (P2.13)

**Version:** 1.0
**Date:** 2026-01-17
**Status:** Active

## Purpose

This document defines the immutable business rules and data integrity constraints for the PMS pricing system (rate plans and seasonal pricing). These invariants prevent human error and ensure pricing data remains consistent and valid.

---

## Core Invariants

### 1. Date Semantics

**Rule:** All date ranges in the pricing system use half-open intervals `[date_from, date_to)`.

- **Inclusive Start:** `date_from` is the first night included in the season
- **Exclusive End:** `date_to` is the first night NOT included in the season
- **Example:** Season from 2026-06-01 to 2026-09-01 covers nights: June 1 through August 31 (inclusive), but NOT September 1

**Rationale:** This semantic aligns with PostgreSQL's `daterange` type and prevents off-by-one errors in season boundaries.

**Enforcement:**
- Database: `CHECK (date_from < date_to)` constraint on `rate_plan_seasons`
- Database: Exclusion constraint using `daterange` to prevent overlaps
- API: Validation in create/update endpoints

---

### 2. Price Resolution Logic

**Rule:** When calculating a nightly price for a booking, the system follows this exact resolution order:

1. **Season Match:** If a season exists where `night_date >= date_from AND night_date < date_to`:
   - Use `rate_plan_seasons.nightly_cents` (if NOT NULL)
   - Use `rate_plans.base_nightly_cents` (if season.nightly_cents IS NULL and base exists)

2. **Fallback Price:** If NO season matches:
   - Use `rate_plans.fallback_price_cents` (if configured and NOT NULL)
   - **OR** Return 422 error: "Keine Saison greift für Nacht {date}, kein Fallbackpreis definiert"

3. **No Pricing Available:**
   - If season matches but both `season.nightly_cents` AND `base_nightly_cents` are NULL: return 422 "Keine Preiskonfiguration für diese Nacht"

**Rationale:** Clear resolution order prevents ambiguity and allows for flexible pricing strategies (full coverage with seasons OR gaps with fallback).

**Enforcement:**
- Service layer: `calculate_quote` endpoint implements exact logic
- Validation: `apply-season-template` checks coverage vs. fallback configuration

---

### 3. One Active Rate Plan Per Property

**Rule:** At most ONE active rate plan per property at any time.

- **Active Defined As:** `archived_at IS NULL AND deleted_at IS NULL`
- **Scope:** Per `property_id` (NOT agency-wide)
- **Exception:** Agency-level rate plans (`property_id IS NULL`) are templates and NOT counted

**Rationale:** Prevents ambiguity in quote calculation and ensures predictable pricing behavior.

**Current Behavior:**
- No database constraint enforcing this rule
- Application enforces "one default per agency" via `is_default` field
- Multiple non-default active plans can exist per property (ALLOWED but discouraged)

**Desired Hardening:**
- Add partial unique index: `UNIQUE(property_id) WHERE archived_at IS NULL AND deleted_at IS NULL AND property_id IS NOT NULL`
- Enforce in API: Return 409 Conflict if attempting to create second active plan for same property

**Migration Path:**
- Existing data may violate this rule (multiple active plans per property)
- Migration must be tolerant: add constraint but allow existing violations
- Future enforcement: API prevents new violations

---

### 4. No Season Overlaps Per Rate Plan

**Rule:** Within a single rate plan, all active seasons MUST NOT overlap.

- **Overlap Definition:** Two date ranges overlap if `range1.date_from < range2.date_to AND range2.date_from < range1.date_to`
- **Scope:** Per `rate_plan_id`, only active seasons (`archived_at IS NULL`)
- **Allowed:** Archived seasons can overlap (historical data)

**Rationale:** Overlapping seasons create ambiguous pricing (which season wins?). Strict non-overlap ensures deterministic price resolution.

**Current Behavior:**
- Application checks overlaps in create/update endpoints (lines 558-577, 638-659 in `pricing.py`)
- No database constraint enforcing this rule
- `apply-season-template` validates overlaps in "merge" mode (lines 2403-2424)

**Desired Hardening:**
- Add exclusion constraint using `btree_gist` extension:
  ```sql
  CREATE EXTENSION IF NOT EXISTS btree_gist;

  ALTER TABLE rate_plan_seasons
  ADD CONSTRAINT rate_plan_seasons_no_overlap_excl
  EXCLUDE USING GIST (
    rate_plan_id WITH =,
    daterange(date_from, date_to, '[)') WITH &&
  )
  WHERE (archived_at IS NULL);
  ```
- API layer continues to provide clear German error messages BEFORE database rejection

---

### 5. Coverage and Gaps

**Rule:** Rate plans MAY have gaps in season coverage IF and ONLY IF `fallback_price_cents` is configured.

**Coverage Definition:**
- **Full Coverage:** Every possible future night (next 365+ days) is covered by at least one active season
- **Gaps Allowed:** Nights without season coverage are permitted IF `fallback_price_cents IS NOT NULL`
- **Gaps Forbidden:** If `fallback_price_cents IS NULL`, gaps result in quote failures (422 errors)

**Rationale:** Provides flexibility for different pricing strategies:
- Strategy A: Complete seasonal coverage (e.g., year-round detailed pricing)
- Strategy B: Sparse seasons + fallback (e.g., high/low season only, default for rest)

**Current Behavior:**
- No `fallback_price_cents` field exists in schema
- Gaps in coverage cause soft failures: quote returns `message` field but still calculates total with available nights
- `apply-season-template` does NOT validate coverage

**Desired Hardening:**
- Add `fallback_price_cents` field to `rate_plans` table
- Update `calculate_quote` to use fallback OR return 422 for gaps
- Update `apply-season-template` to validate coverage if fallback is NULL:
  - In dry_run: return gap ranges in response
  - If gaps exist and no fallback: return 422 "Lücken in Saisonabdeckung gefunden, bitte Fallbackpreis definieren"

---

## Error Response Standards

All pricing validation errors MUST follow these conventions:

### HTTP Status Codes

- **409 Conflict:** Attempting to create duplicate active rate plan for same property
- **422 Unprocessable Entity:** Validation failures (overlaps, gaps, invalid dates)
- **404 Not Found:** Resource doesn't exist or doesn't belong to agency
- **400 Bad Request:** Invalid input format (schema validation)

### Error Message Format

**German User-Facing Messages:**
- Clear, actionable, non-technical language
- Include specific details (dates, conflicts)
- Examples:
  - "Es existiert bereits ein aktiver Preisplan für dieses Objekt. Bitte archivieren Sie den bestehenden Plan zuerst."
  - "Überschneidung mit bestehender Saison: Hauptsaison 2026 (2026-06-01 bis 2026-09-01)"
  - "Keine Saison greift für Nacht 2026-12-25, kein Fallbackpreis definiert"

**Machine-Readable Details:**
- Include error codes for UI handling: `"code": "RATE_PLAN_DUPLICATE"`
- Include conflicting entities: season IDs, date ranges
- Structure for programmatic parsing

---

## Migration Strategy

### Phase 1: Add Fallback Price Support
- Add `fallback_price_cents INT NULL` to `rate_plans` table
- Update schemas to include fallback field
- Backward compatible: NULL means "no fallback" (current behavior)

### Phase 2: Add Database Constraints
- Add partial unique index for "one active plan per property"
- Add exclusion constraint for "no season overlaps"
- Constraints apply only to NEW data (use `NOT VALID` if needed for existing violations)

### Phase 3: API Hardening
- Update create/update endpoints with 409/422 error codes
- Enhance error messages with German text and details
- Update `apply-season-template` with gap validation

### Phase 4: Existing Data Cleanup (Optional)
- Identify properties with multiple active plans
- Admin tooling to archive/merge duplicate plans
- Validate constraint if cleanup successful

---

## Current vs. Desired State

### Current State (Pre-P2.13)

**Rate Plans:**
- ✅ Soft delete with `archived_at` (no `deleted_at` yet)
- ✅ `is_default` per agency (not per property)
- ❌ Multiple active plans per property allowed
- ❌ No `fallback_price_cents` field

**Seasons:**
- ✅ Application-level overlap checks
- ✅ Soft delete with `archived_at`
- ❌ No database constraint preventing overlaps
- ❌ Gaps in coverage cause soft failures (message but quote still returns)

**Quote Endpoint:**
- ✅ Per-night breakdown with seasonal pricing
- ✅ Falls back to `base_nightly_cents` if season has no price
- ❌ Continues calculating even if some nights have no pricing
- ❌ Does not return 422 for missing pricing

**Apply Template:**
- ✅ Validates overlaps in merge mode
- ✅ Atomic transaction for replace mode
- ❌ Does not validate coverage gaps
- ❌ Does not check fallback price requirement

### Desired State (Post-P2.13)

**Rate Plans:**
- ✅ Soft delete with `archived_at` (future: add `deleted_at`)
- ✅ Database constraint: one active plan per property
- ✅ `fallback_price_cents` field for gap handling
- ✅ 409 Conflict on duplicate create

**Seasons:**
- ✅ Database exclusion constraint preventing overlaps
- ✅ Enhanced error messages with conflict details
- ✅ German error messages for all validations

**Quote Endpoint:**
- ✅ Returns 422 if night has no season and no fallback
- ✅ Clear German error: "Keine Saison greift für Nacht {date}"
- ✅ Uses fallback price when configured

**Apply Template:**
- ✅ Validates coverage gaps before commit
- ✅ Returns 422 if gaps exist and no fallback
- ✅ Includes gap ranges in dry_run response
- ✅ All overlap conflicts have German messages

---

## Glossary

- **Active:** Not archived and not deleted (`archived_at IS NULL AND deleted_at IS NULL`)
- **Archived:** Soft-deleted but reversible (`archived_at IS NOT NULL`)
- **Coverage:** Whether every future night has a matching season
- **Fallback Price:** Default price used when no season matches
- **Gap:** A date range with no matching season
- **Overlap:** Two seasons with intersecting date ranges
- **Season:** A date range with optional pricing override
- **Template:** Agency-level rate plan used as blueprint (not quoted)

---

## References

- P2: Pricing v1 Foundation (base rate plans)
- P2.1: Season Templates (reusable date windows)
- P2.2: Season Editor (manual season management)
- P2.4: Apply Season Template (atomic application)
- P2.5: Per-Night Breakdown (seasonal pricing in quotes)
- P2.13: **This document** (hardening against human errors)

**Database Schema:**
- `/supabase/migrations/20260106150000_add_pricing_v1.sql`
- `/supabase/migrations/20260115000000_add_rate_plans_defaults.sql`
- `/supabase/migrations/20260117000000_add_rate_plan_seasons_label_archived.sql`

**API Implementation:**
- `/backend/app/api/routes/pricing.py`
- `/backend/app/services/rate_plan_resolver.py`
- `/backend/app/schemas/pricing.py`
