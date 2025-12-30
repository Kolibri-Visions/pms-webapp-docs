# Phase 2: Availability & Booking Lifecycle

**Sprint**: 2 of 5
**Duration**: 2 weeks
**Status**: Not Started
**Owner**: Backend Team

## Goal

Complete availability rules, implement booking state machine, add idempotency for booking creation, and introduce holds/blocks primitives for temporary reservations.

## Scope

### MUST (Sprint Goal)
- ✓ **Availability Rules Completeness**: Blocked dates, min stay, buffer days, changeover rules
- ✓ **Booking Lifecycle**: State machine (pending → confirmed → cancelled → refunded)
- ✓ **Idempotency for Booking Creation**: Prevent duplicate bookings using idempotency keys
- ✓ **Holds/Blocks Primitives**: Temporary reservations (holds expire after N minutes)

### SHOULD (Nice to Have)
- Availability caching layer (Redis)
- Booking conflict detection (overlapping dates)
- Audit log integration (log booking state transitions)

### COULD (Stretch)
- Automated availability sync to channels
- Booking expiry job (auto-cancel pending bookings after timeout)
- Multi-property booking support

## Deliverables & Definition of Done

### 1. Availability Rules Completeness
**Files Touched**:
- `app/services/availability.py` (add rule checks)
- `app/schemas/availability.py` (add rule params)
- `app/routers/availability.py` (expose rules in API)

**DoD**:
- [ ] Check blocked dates: Return unavailable if date in `blocked_dates` table
- [ ] Check min stay: Return unavailable if stay < property.min_stay_nights
- [ ] Check buffer days: Block N days before/after existing bookings
- [ ] Check changeover rules: Only allow checkin/checkout on specific weekdays
- [ ] Tests: Availability respects all rules

### 2. Booking Lifecycle
**Files Touched**:
- `app/services/bookings.py` (state machine logic)
- `app/schemas/bookings.py` (add status enum)
- `app/routers/bookings.py` (add state transition endpoints)

**DoD**:
- [ ] Status enum: `pending`, `confirmed`, `cancelled`, `refunded`, `completed`
- [ ] State transitions: `pending → confirmed` (payment received)
- [ ] State transitions: `confirmed → cancelled` (guest cancels)
- [ ] State transitions: `cancelled → refunded` (refund processed)
- [ ] Audit log: Log all state transitions with user_id + timestamp
- [ ] Tests: State machine validates transitions (no `confirmed → pending`)

### 3. Idempotency for Booking Creation
**Files Touched**:
- `app/routers/bookings.py` (idempotency middleware)
- `app/core/idempotency.py` (new helper)
- `app/services/bookings.py` (check idempotency key)

**DoD**:
- [ ] `POST /api/v1/bookings` accepts `Idempotency-Key` header
- [ ] If key exists, return cached response (201 + booking ID)
- [ ] If key doesn't exist, create booking + store response
- [ ] Keys expire after 24 hours (cleanup job)
- [ ] Tests: Duplicate POST with same key returns same booking

### 4. Holds/Blocks Primitives
**Files Touched**:
- `app/routers/holds.py` (new router)
- `app/services/holds.py` (new service)
- `app/schemas/holds.py` (new schema)

**DoD**:
- [ ] `POST /api/v1/holds` creates temporary hold (expires in 15 min)
- [ ] Holds block availability (treated like bookings)
- [ ] `DELETE /api/v1/holds/:id` releases hold
- [ ] Expiry job: Auto-delete expired holds every 5 minutes
- [ ] Tests: Expired holds do not block availability

## APIs Touched

**New Endpoints**:
- `GET /api/v1/availability?property_id=...&start=...&end=...` (enhanced with rules)
- `POST /api/v1/holds` (create temporary hold)
- `DELETE /api/v1/holds/:id` (release hold)
- `PATCH /api/v1/bookings/:id/status` (transition booking state)

**Modified Endpoints**:
- `POST /api/v1/bookings` (add idempotency support)
- `GET /api/v1/bookings/:id` (include status field)

**No Breaking Changes**: Existing endpoints remain functional.

## Database Changes

**New Tables**:
1. `blocked_dates`:
   ```sql
   CREATE TABLE blocked_dates (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     property_id UUID NOT NULL REFERENCES properties(id),
     agency_id UUID NOT NULL REFERENCES agencies(id),
     start_date DATE NOT NULL,
     end_date DATE NOT NULL,
     reason TEXT,  -- e.g., 'maintenance', 'owner_use'
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_blocked_dates_property ON blocked_dates(property_id, start_date, end_date);
   ```

2. `holds`:
   ```sql
   CREATE TABLE holds (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     property_id UUID NOT NULL REFERENCES properties(id),
     agency_id UUID NOT NULL REFERENCES agencies(id),
     start_date DATE NOT NULL,
     end_date DATE NOT NULL,
     holder_email TEXT,
     expires_at TIMESTAMPTZ NOT NULL,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_holds_property ON holds(property_id, start_date, end_date);
   CREATE INDEX idx_holds_expires ON holds(expires_at);
   ```

**Modified Tables**:
- `bookings`: Add `status` column (enum: pending, confirmed, cancelled, refunded, completed)

**RLS Policies**:
- Add RLS for `blocked_dates`, `holds` (agency_id scoped)

## Ops Notes

### Deployment
1. Apply migrations (blocked_dates, holds, bookings.status)
2. Deploy backend with idempotency support
3. Start expiry job (Celery beat task for holds cleanup)
4. Monitor booking creation for duplicate keys

### Monitoring
- Alert on idempotency key collisions (different requests, same key)
- Monitor hold expiry job performance
- Track booking state transition metrics

### Rollback Plan
- Idempotency is backward compatible (header is optional)
- Holds table can be dropped without affecting bookings
- Booking status defaults to `confirmed` if migration fails

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Idempotency key collisions | Medium | Use UUID + timestamp for key generation |
| Hold expiry job performance | Low | Batch delete, index on expires_at |
| Booking state transition bugs | High | Extensive unit tests, audit log |
| Availability rules too strict | Medium | Make rules configurable per property |

## Dependencies

**Blocks**:
- Phase 3 (quote API requires availability rules)
- Phase 5 (checkout flow requires booking lifecycle)

**Depends On**:
- Phase 1 (idempotency_keys table, audit_log)

## Success Metrics

- ✓ Zero duplicate bookings in production
- ✓ Availability checks pass 100% of rule validations
- ✓ Booking state transitions logged in audit_log
- ✓ Hold expiry job runs reliably (< 1% failure rate)

## Next Steps

1. Review this spec with team
2. Create Phase 2 tickets (`/docs/tickets/phase-2.md`)
3. Assign tickets and kickoff sprint
4. Integration tests for booking lifecycle

---

**Related Documents**:
- [Roadmap Overview](./overview.md)
- [Phase 2 Tickets](../tickets/phase-2.md)
- [Phase 1 Spec](./phase-1.md)
