# Phase 5 Tickets: Public APIs & Polish

**Sprint**: 5 of 5
**Total Tickets**: 12
**Estimated Points**: 25

## Ticket List

### P5-01: Create public properties API
**Priority**: High | **Points**: 2
**Touch Points**: `app/routers/public.py` (new), `app/services/public.py`

**Acceptance Criteria**:
- [ ] `GET /api/v1/public/properties` (no auth)
- [ ] `GET /api/v1/public/properties/:id` (no auth)
- [ ] Return sanitized data (no sensitive info)
- [ ] Tests: Public API returns correct data

---

### P5-02: Create public availability API
**Priority**: High | **Points**: 2
**Touch Points**: `app/routers/public.py`

**Acceptance Criteria**:
- [ ] `GET /api/v1/public/availability` endpoint
- [ ] Query params: property_id, start_date, end_date
- [ ] Return available dates
- [ ] Tests: Availability check works

---

### P5-03: Create public rates API
**Priority**: High | **Points**: 2
**Touch Points**: `app/routers/public.py`

**Acceptance Criteria**:
- [ ] `GET /api/v1/public/rates` endpoint
- [ ] Return nightly rates for date range
- [ ] No pricing breakdown (just totals)
- [ ] Tests: Rates API works

---

### P5-04: Create checkout endpoint
**Priority**: High | **Points**: 5
**Touch Points**: `app/routers/checkout.py` (new), `app/services/checkout.py`

**Acceptance Criteria**:
- [ ] `POST /api/v1/checkout` endpoint
- [ ] Accept quote_id, payment_method, guest_info
- [ ] Validate quote not expired
- [ ] Create booking (status=pending)
- [ ] Process payment (Stripe integration)
- [ ] Update booking status on success/failure
- [ ] Send confirmation email
- [ ] Tests: End-to-end checkout flow

---

### P5-05: Create owner documents table
**Priority**: Medium | **Points**: 1
**Touch Points**: `supabase/migrations/`, `app/schemas/owners.py`

**Acceptance Criteria**:
- [ ] Create `owner_documents` table
- [ ] RLS policies (owner_id scoped)
- [ ] Migration with rollback

---

### P5-06: Implement owner bookings API
**Priority**: High | **Points**: 2
**Touch Points**: `app/routers/owners.py` (new)

**Acceptance Criteria**:
- [ ] `GET /api/v1/owners/bookings` endpoint
- [ ] Enforce RLS (owner sees only their properties)
- [ ] Tests: Owner A cannot access Owner B data

---

### P5-07: Implement owner revenue API
**Priority**: Medium | **Points**: 3
**Touch Points**: `app/routers/owners.py`, `app/services/owners.py`

**Acceptance Criteria**:
- [ ] `GET /api/v1/owners/revenue` endpoint
- [ ] Revenue summary by month/year
- [ ] Enforce RLS
- [ ] Tests: Revenue calculations accurate

---

### P5-08: Implement owner documents API
**Priority**: Medium | **Points**: 2
**Touch Points**: `app/routers/owners.py`

**Acceptance Criteria**:
- [ ] `GET /api/v1/owners/documents` endpoint
- [ ] `GET /api/v1/owners/documents/:id/download` endpoint
- [ ] Enforce RLS
- [ ] Tests: Document download works

---

### P5-09: Add structured logging
**Priority**: High | **Points**: 2
**Touch Points**: `app/core/logging.py`, `app/main.py`

**Acceptance Criteria**:
- [ ] JSON log format
- [ ] Include request_id, user_id, agency_id
- [ ] Log all requests/responses
- [ ] Tests: Verify log structure

---

### P5-10: Add metrics collection
**Priority**: Medium | **Points**: 2
**Touch Points**: `app/core/metrics.py` (new), `app/main.py`

**Acceptance Criteria**:
- [ ] Prometheus metrics integration
- [ ] Track: request latency, error rate, active users
- [ ] Expose `/metrics` endpoint
- [ ] Tests: Metrics collected

---

### P5-11: Add distributed tracing
**Priority**: Low | **Points**: 2
**Touch Points**: `app/core/tracing.py` (new), `app/main.py`

**Acceptance Criteria**:
- [ ] OpenTelemetry integration
- [ ] Trace all requests
- [ ] Export to Jaeger or Datadog
- [ ] Tests: Traces generated

---

### P5-12: Production readiness review & Phase 5 retrospective
**Priority**: High | **Points**: 2

**Acceptance Criteria**:
- [ ] Security audit complete
- [ ] Performance testing complete
- [ ] Documentation published
- [ ] Team retrospective held
- [ ] Final roadmap update

---

## Dependencies

```
P5-01, P5-02, P5-03 → P5-04 (Public APIs required for checkout)
P5-05 → P5-08 (Table required for documents API)
P5-09, P5-10, P5-11 → P5-12 (Observability required for production)
```
