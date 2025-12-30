# Phase 3: Pricing & Quoting

**Sprint**: 3 of 5
**Duration**: 2 weeks
**Status**: Not Started
**Owner**: Backend Team

## Goal

Implement dynamic pricing logic, seasonal rates, minimum stay rules, quote endpoint for price calculation, and hold/expiry mechanism for temporary price locks.

## Scope

### MUST (Sprint Goal)
- ✓ **Pricing Base Logic**: Nightly rates, cleaning fees, taxes, discounts
- ✓ **Season/Min Stay Rules**: Apply seasonal pricing, enforce min stay requirements
- ✓ **Quote Endpoint**: Calculate total price without creating booking
- ✓ **Hold/Expiry Skeleton**: Temporary price locks (quotes valid for N hours)

### SHOULD (Nice to Have)
- Multi-currency support (EUR, USD, CHF)
- Dynamic pricing (weekend surcharges, last-minute discounts)
- Quote versioning (track quote changes)

### COULD (Stretch)
- Price comparison (show savings vs. base rate)
- Promotional codes / coupons
- Channel-specific pricing (Airbnb vs. Booking.com rates)

## Deliverables & Definition of Done

### 1. Pricing Base Logic
**Files Touched**:
- `app/services/pricing.py` (new service)
- `app/schemas/pricing.py` (new schema)
- `app/models/pricing.py` (new models)

**DoD**:
- [ ] Calculate nightly rate × nights
- [ ] Add cleaning fee (one-time)
- [ ] Add taxes (configurable % per property)
- [ ] Apply discounts (weekly/monthly stay discounts)
- [ ] Return breakdown: `{base_rate, cleaning_fee, taxes, discounts, total}`
- [ ] Tests: Verify pricing calculations

### 2. Season/Min Stay Rules
**Files Touched**:
- `app/services/pricing.py` (seasonal rate logic)
- `app/routers/seasons.py` (new CRUD for seasons)
- `app/schemas/seasons.py` (new schema)

**DoD**:
- [ ] Define seasons: `{start_date, end_date, rate_multiplier}`
- [ ] Apply seasonal rates: `base_rate × multiplier`
- [ ] Enforce min stay: Reject quotes if stay < season.min_nights
- [ ] Handle overlapping seasons (priority by specificity)
- [ ] Tests: Seasonal rates apply correctly

### 3. Quote Endpoint
**Files Touched**:
- `app/routers/quotes.py` (new router)
- `app/services/quotes.py` (new service)
- `app/schemas/quotes.py` (new schema)

**DoD**:
- [ ] `POST /api/v1/quotes` returns price breakdown + quote_id
- [ ] Quote does NOT create booking (read-only operation)
- [ ] Quote includes: property, dates, guests, total, breakdown
- [ ] Quote is stored in DB (for hold/expiry)
- [ ] Tests: Quote API returns accurate pricing

### 4. Hold/Expiry Skeleton
**Files Touched**:
- `app/services/quotes.py` (hold logic)
- `app/routers/quotes.py` (hold endpoints)
- Celery beat task for expiry

**DoD**:
- [ ] `POST /api/v1/quotes/:id/hold` locks price for N hours
- [ ] Held quotes return `{quote_id, expires_at, total}`
- [ ] Expiry job: Mark expired quotes as `expired`
- [ ] Converting quote to booking uses held price (no recalculation)
- [ ] Tests: Expired quotes cannot be converted to bookings

## APIs Touched

**New Endpoints**:
- `POST /api/v1/quotes` (create quote)
- `GET /api/v1/quotes/:id` (retrieve quote)
- `POST /api/v1/quotes/:id/hold` (lock price)
- `DELETE /api/v1/quotes/:id` (cancel quote)
- `POST /api/v1/seasons` (CRUD for seasonal rates)
- `GET /api/v1/seasons?property_id=...` (list seasons)

**Modified Endpoints**:
- `POST /api/v1/bookings` (accept quote_id to use held price)

**No Breaking Changes**: Existing endpoints remain functional.

## Database Changes

**New Tables**:
1. `seasons`:
   ```sql
   CREATE TABLE seasons (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     property_id UUID NOT NULL REFERENCES properties(id),
     agency_id UUID NOT NULL REFERENCES agencies(id),
     name TEXT NOT NULL,  -- e.g., 'Summer', 'Winter', 'Holiday'
     start_date DATE NOT NULL,
     end_date DATE NOT NULL,
     rate_multiplier DECIMAL(5,2) DEFAULT 1.0,  -- e.g., 1.5 = 150% of base rate
     min_nights INT DEFAULT 1,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_seasons_property ON seasons(property_id, start_date, end_date);
   ```

2. `quotes`:
   ```sql
   CREATE TABLE quotes (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     agency_id UUID NOT NULL REFERENCES agencies(id),
     property_id UUID NOT NULL REFERENCES properties(id),
     start_date DATE NOT NULL,
     end_date DATE NOT NULL,
     guests INT NOT NULL,
     base_rate DECIMAL(10,2),
     cleaning_fee DECIMAL(10,2),
     taxes DECIMAL(10,2),
     discounts DECIMAL(10,2),
     total DECIMAL(10,2),
     status TEXT DEFAULT 'active',  -- active, held, expired, converted
     held_at TIMESTAMPTZ,
     expires_at TIMESTAMPTZ,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_quotes_agency ON quotes(agency_id);
   CREATE INDEX idx_quotes_expires ON quotes(expires_at);
   ```

**RLS Policies**:
- Add RLS for `seasons`, `quotes` (agency_id scoped)

## Ops Notes

### Deployment
1. Apply migrations (seasons, quotes)
2. Deploy backend with pricing logic
3. Start quote expiry job (Celery beat)
4. Monitor quote → booking conversion rate

### Monitoring
- Track quote API response times (should be < 500ms p99)
- Monitor quote expiry job performance
- Alert on pricing calculation errors (e.g., negative totals)

### Rollback Plan
- Quote API is read-only, safe to deploy/rollback
- Booking creation still works without quote_id (backward compatible)
- Seasonal rates are optional (defaults to base rate)

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Pricing calculation errors | High | Extensive unit tests, manual validation |
| Seasonal rate conflicts | Medium | Priority rules, validation on season create |
| Quote expiry job performance | Low | Batch updates, index on expires_at |
| Hold abuse (infinite holds) | Medium | Limit holds per user, expiry enforcement |

## Dependencies

**Blocks**:
- Phase 5 (checkout flow requires quote API)

**Depends On**:
- Phase 2 (availability rules, booking lifecycle)

## Success Metrics

- ✓ Quote API response time < 500ms p99
- ✓ Pricing calculations match manual verification (100% accuracy)
- ✓ Hold expiry job runs reliably (< 1% failure rate)
- ✓ Quote → booking conversion rate measured

## Next Steps

1. Review this spec with team
2. Create Phase 3 tickets (`/docs/tickets/phase-3.md`)
3. Assign tickets and kickoff sprint
4. Integration tests for pricing logic

---

**Related Documents**:
- [Roadmap Overview](./overview.md)
- [Phase 3 Tickets](../tickets/phase-3.md)
- [Phase 2 Spec](./phase-2.md)
