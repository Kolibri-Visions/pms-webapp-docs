# Phase 2 Tickets: Availability & Booking Lifecycle

**Sprint**: 2 of 5
**Total Tickets**: 12
**Estimated Points**: 24

## Ticket List

### P2-01: Implement blocked dates table and queries
**Priority**: High | **Points**: 2
**Touch Points**: `app/services/availability.py`, `supabase/migrations/`

**Acceptance Criteria**:
- [ ] Create `blocked_dates` table migration
- [ ] Add blocked date check to availability queries
- [ ] CRUD endpoints for blocked dates
- [ ] Tests: Blocked dates prevent availability

---

### P2-02: Add minimum stay validation
**Priority**: High | **Points**: 2
**Touch Points**: `app/services/availability.py`, `app/schemas/availability.py`

**Acceptance Criteria**:
- [ ] Check stay length against property.min_stay_nights
- [ ] Return unavailable if stay < min_stay
- [ ] Tests: Min stay validation works

---

### P2-03: Implement buffer days logic
**Priority**: Medium | **Points**: 3
**Touch Points**: `app/services/availability.py`

**Acceptance Criteria**:
- [ ] Block N days before/after bookings (configurable)
- [ ] Availability queries respect buffer days
- [ ] Tests: Buffer days block availability

---

### P2-04: Add changeover day rules
**Priority**: Medium | **Points**: 2
**Touch Points**: `app/services/availability.py`, `app/models/properties.py`

**Acceptance Criteria**:
- [ ] Property setting: allowed_checkin_days, allowed_checkout_days
- [ ] Validate checkin/checkout against allowed days
- [ ] Tests: Changeover rules enforced

---

### P2-05: Create booking status enum and migration
**Priority**: High | **Points**: 1
**Touch Points**: `app/schemas/bookings.py`, `supabase/migrations/`

**Acceptance Criteria**:
- [ ] Add `status` column to bookings table
- [ ] Enum: pending, confirmed, cancelled, refunded, completed
- [ ] Migration with default value

---

### P2-06: Implement booking state machine
**Priority**: High | **Points**: 3
**Touch Points**: `app/services/bookings.py`, `app/routers/bookings.py`

**Acceptance Criteria**:
- [ ] State transitions: pending → confirmed → cancelled/refunded
- [ ] Validate transitions (no confirmed → pending)
- [ ] Audit log integration
- [ ] Tests: State machine validates transitions

---

### P2-07: Create idempotency helper
**Priority**: High | **Points**: 2
**Touch Points**: `app/core/idempotency.py` (new file)

**Acceptance Criteria**:
- [ ] `check_idempotency_key(key)` returns cached response if exists
- [ ] `store_idempotency_key(key, response)` caches response
- [ ] Keys expire after 24 hours
- [ ] Tests: Idempotency key lookup

---

### P2-08: Add idempotency to booking creation
**Priority**: High | **Points**: 3
**Touch Points**: `app/routers/bookings.py`

**Acceptance Criteria**:
- [ ] `POST /api/v1/bookings` accepts `Idempotency-Key` header
- [ ] Return cached response if key exists
- [ ] Store response on successful creation
- [ ] Tests: Duplicate POST returns same booking

---

### P2-09: Create holds table and endpoints
**Priority**: Medium | **Points**: 3
**Touch Points**: `app/routers/holds.py`, `app/services/holds.py`

**Acceptance Criteria**:
- [ ] Create `holds` table migration
- [ ] `POST /api/v1/holds` creates temporary hold (15 min expiry)
- [ ] `DELETE /api/v1/holds/:id` releases hold
- [ ] Tests: Holds block availability

---

### P2-10: Implement hold expiry job
**Priority**: Medium | **Points**: 2
**Touch Points**: `app/workers/hold_expiry.py` (new file)

**Acceptance Criteria**:
- [ ] Celery beat task runs every 5 minutes
- [ ] Delete expired holds
- [ ] Log expiry events
- [ ] Tests: Expired holds are deleted

---

### P2-11: Add booking conflict detection
**Priority**: Low | **Points**: 2
**Touch Points**: `app/services/bookings.py`

**Acceptance Criteria**:
- [ ] Check for overlapping dates before creating booking
- [ ] Return 409 Conflict if overlap detected
- [ ] Tests: Overlapping bookings rejected

---

### P2-12: Phase 2 retrospective
**Priority**: Low | **Points**: 1

**Acceptance Criteria**:
- [ ] Team retrospective held
- [ ] Update roadmap with progress
- [ ] Document lessons learned

---

## Dependencies

```
P2-05 → P2-06 (State enum required for state machine)
P2-07 → P2-08 (Helper required for endpoint)
P2-09 → P2-10 (Table required for expiry job)
```
