# Phase 3 Tickets: Pricing & Quoting

**Sprint**: 3 of 5
**Total Tickets**: 10
**Estimated Points**: 21

## Ticket List

### P3-01: Create pricing calculation service
**Priority**: High | **Points**: 3
**Touch Points**: `app/services/pricing.py` (new), `app/schemas/pricing.py`

**Acceptance Criteria**:
- [ ] Calculate base rate (nightly rate × nights)
- [ ] Add cleaning fee (one-time)
- [ ] Calculate taxes (configurable %)
- [ ] Apply discounts (weekly/monthly)
- [ ] Return breakdown
- [ ] Tests: Pricing calculations accurate

---

### P3-02: Create seasons table and CRUD
**Priority**: High | **Points**: 2
**Touch Points**: `app/routers/seasons.py`, `supabase/migrations/`

**Acceptance Criteria**:
- [ ] Create `seasons` table migration
- [ ] CRUD endpoints for seasons
- [ ] Validation: no overlapping seasons
- [ ] Tests: Season CRUD operations

---

### P3-03: Implement seasonal rate logic
**Priority**: High | **Points**: 3
**Touch Points**: `app/services/pricing.py`

**Acceptance Criteria**:
- [ ] Apply seasonal multiplier to base rate
- [ ] Handle overlapping seasons (priority logic)
- [ ] Tests: Seasonal rates apply correctly

---

### P3-04: Create quotes table and schema
**Priority**: High | **Points**: 1
**Touch Points**: `supabase/migrations/`, `app/schemas/quotes.py`

**Acceptance Criteria**:
- [ ] Create `quotes` table migration
- [ ] Schema includes breakdown fields
- [ ] RLS policies added
- [ ] Migration rollback script

---

### P3-05: Implement quote creation endpoint
**Priority**: High | **Points**: 3
**Touch Points**: `app/routers/quotes.py`, `app/services/quotes.py`

**Acceptance Criteria**:
- [ ] `POST /api/v1/quotes` creates quote (no booking)
- [ ] Quote includes price breakdown
- [ ] Store quote in DB
- [ ] Tests: Quote API returns accurate pricing

---

### P3-06: Implement quote retrieval endpoint
**Priority**: Medium | **Points**: 1
**Touch Points**: `app/routers/quotes.py`

**Acceptance Criteria**:
- [ ] `GET /api/v1/quotes/:id` returns quote details
- [ ] Include expiry status
- [ ] Tests: Quote retrieval works

---

### P3-07: Add quote hold functionality
**Priority**: Medium | **Points**: 2
**Touch Points**: `app/routers/quotes.py`, `app/services/quotes.py`

**Acceptance Criteria**:
- [ ] `POST /api/v1/quotes/:id/hold` locks price
- [ ] Set expires_at (configurable duration)
- [ ] Update status to `held`
- [ ] Tests: Quote hold works

---

### P3-08: Implement quote expiry job
**Priority**: Medium | **Points**: 2
**Touch Points**: `app/workers/quote_expiry.py` (new)

**Acceptance Criteria**:
- [ ] Celery beat task runs hourly
- [ ] Mark expired quotes as `expired`
- [ ] Log expiry events
- [ ] Tests: Expired quotes marked correctly

---

### P3-09: Add minimum stay enforcement in pricing
**Priority**: Low | **Points**: 2
**Touch Points**: `app/services/pricing.py`

**Acceptance Criteria**:
- [ ] Check seasonal min_nights
- [ ] Return error if stay < min_nights
- [ ] Tests: Min stay enforced in quotes

---

### P3-10: Phase 3 retrospective
**Priority**: Low | **Points**: 1

**Acceptance Criteria**:
- [ ] Team retrospective held
- [ ] Update roadmap
- [ ] Document lessons learned

---

## Dependencies

```
P3-01 → P3-05 (Pricing service required for quotes)
P3-02, P3-03 → P3-05 (Seasons required for quote pricing)
P3-04 → P3-05, P3-07, P3-08 (Table required for all quote operations)
```
