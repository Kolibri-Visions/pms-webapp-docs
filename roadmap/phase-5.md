# Phase 5: Public APIs & Polish

**Sprint**: 5 of 5
**Duration**: 2 weeks
**Status**: Not Started
**Owner**: Backend Team

## Goal

Expose public-facing APIs, implement checkout flow (quote → booking), create owner-facing read APIs + documents, and polish observability (structured logging, metrics, traces).

## Scope

### MUST (Sprint Goal)
- ✓ **Public Read APIs**: Properties, availability, rates (versioned, documented)
- ✓ **Checkout Flow**: Quote → booking with payment integration
- ✓ **Owner Read APIs + Documents**: Bookings, revenue, documents (invoices, contracts)
- ✓ **Observability Polish**: Structured logging, metrics, distributed traces

### SHOULD (Nice to Have)
- API rate limiting (per-user, per-agency)
- API versioning strategy (v1, v2)
- Owner notification system (email on booking, cancellation)

### COULD (Stretch)
- Public API SDK (Python, JavaScript)
- API analytics dashboard
- Owner mobile app support (push notifications)

## Deliverables & Definition of Done

### 1. Public Read APIs
**Files Touched**:
- `app/routers/public.py` (new router)
- `app/schemas/public.py` (new schemas)
- `app/services/public.py` (new service)

**DoD**:
- [ ] `GET /api/v1/public/properties` (list properties, no auth)
- [ ] `GET /api/v1/public/properties/:id` (property details)
- [ ] `GET /api/v1/public/availability?property_id=...&start=...&end=...` (check availability)
- [ ] `GET /api/v1/public/rates?property_id=...&start=...&end=...` (get pricing)
- [ ] API is versioned: `/api/v1/...` (prepare for v2)
- [ ] API docs: OpenAPI/Swagger auto-generated
- [ ] Tests: Public API returns correct data, no sensitive info leaked

### 2. Checkout Flow
**Files Touched**:
- `app/routers/checkout.py` (new router)
- `app/services/checkout.py` (new service)
- `app/schemas/checkout.py` (new schema)
- Payment integration (Stripe, PayPal)

**DoD**:
- [ ] `POST /api/v1/checkout` accepts `{quote_id, payment_method, guest_info}`
- [ ] Validate quote is not expired
- [ ] Create booking with status `pending`
- [ ] Process payment (Stripe integration)
- [ ] On payment success: Update booking status to `confirmed`
- [ ] On payment failure: Return error, do not create booking
- [ ] Send confirmation email to guest
- [ ] Tests: End-to-end checkout flow

### 3. Owner Read APIs + Documents
**Files Touched**:
- `app/routers/owners.py` (new router)
- `app/services/owners.py` (new service)
- `app/schemas/owners.py` (new schema)

**DoD**:
- [ ] `GET /api/v1/owners/bookings` (list owner's bookings, RLS enforced)
- [ ] `GET /api/v1/owners/revenue` (revenue summary, by month/year)
- [ ] `GET /api/v1/owners/documents` (invoices, contracts, reports)
- [ ] `GET /api/v1/owners/documents/:id/download` (download PDF)
- [ ] Enforce RLS: Owner can only see their own properties
- [ ] Tests: Owner A cannot access Owner B's data

### 4. Observability Polish
**Files Touched**:
- `app/core/logging.py` (structured logging)
- `app/core/metrics.py` (new metrics helper)
- `app/core/tracing.py` (distributed tracing)
- `app/main.py` (middleware for logging, metrics, tracing)

**DoD**:
- [ ] Structured logging: JSON format, include `request_id`, `user_id`, `agency_id`
- [ ] Metrics: Track request latency, error rate, active users (Prometheus)
- [ ] Distributed tracing: OpenTelemetry integration (Jaeger or Datadog)
- [ ] Health check endpoint: Include DB, Redis, Celery status
- [ ] Tests: Verify logs are structured, metrics are collected

## APIs Touched

**New Endpoints**:
- `GET /api/v1/public/properties` (public, no auth)
- `GET /api/v1/public/properties/:id` (public, no auth)
- `GET /api/v1/public/availability` (public, no auth)
- `GET /api/v1/public/rates` (public, no auth)
- `POST /api/v1/checkout` (authenticated)
- `GET /api/v1/owners/bookings` (owner-only)
- `GET /api/v1/owners/revenue` (owner-only)
- `GET /api/v1/owners/documents` (owner-only)
- `GET /api/v1/owners/documents/:id/download` (owner-only)

**Modified Endpoints**:
- All endpoints: Add structured logging, metrics, tracing

**No Breaking Changes**: Existing endpoints remain functional.

## Database Changes

**New Tables**:
1. `owner_documents`:
   ```sql
   CREATE TABLE owner_documents (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     owner_id UUID NOT NULL REFERENCES auth.users(id),
     agency_id UUID NOT NULL REFERENCES agencies(id),
     property_id UUID REFERENCES properties(id),
     document_type TEXT NOT NULL,  -- 'invoice', 'contract', 'report'
     title TEXT NOT NULL,
     file_path TEXT NOT NULL,  -- S3 or local path
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_owner_documents_owner ON owner_documents(owner_id, created_at DESC);
   ```

**RLS Policies**:
- Add RLS for `owner_documents` (owner_id scoped)

## Ops Notes

### Deployment
1. Apply migrations (owner_documents)
2. Deploy backend with public APIs
3. Enable observability (logging, metrics, tracing)
4. Monitor public API traffic, checkout conversion rate

### Monitoring
- Track public API response times (should be < 200ms p95)
- Monitor checkout success rate (alert if < 90%)
- Track owner API usage (adoption metrics)
- Alert on 5xx errors (should be < 0.1%)

### Rollback Plan
- Public APIs are read-only, safe to deploy/rollback
- Checkout flow can be disabled via feature flag
- Owner APIs enforce RLS, safe to deploy

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Public API abuse (scraping, DDoS) | High | Rate limiting, CAPTCHA, WAF |
| Checkout payment failures | High | Retry logic, payment gateway fallback |
| Owner API RLS bypass | High | Extensive testing, code review |
| Observability overhead | Low | Async logging, sampling for traces |

## Dependencies

**Blocks**:
- Production launch (all features complete)

**Depends On**:
- Phase 1 (RBAC, error taxonomy)
- Phase 2 (booking lifecycle)
- Phase 3 (quote API)
- Phase 4 (channel sync reliability)

## Success Metrics

- ✓ Public API documentation published
- ✓ Checkout flow conversion rate measured (target: > 80%)
- ✓ Owner API adoption > 50% of agencies
- ✓ Observability: < 0.1% 5xx error rate, < 500ms p99 latency

## Next Steps

1. Review this spec with team
2. Create Phase 5 tickets (`/docs/tickets/phase-5.md`)
3. Assign tickets and kickoff sprint
4. End-to-end testing for checkout flow
5. Production readiness review

---

**Related Documents**:
- [Roadmap Overview](./overview.md)
- [Phase 5 Tickets](../tickets/phase-5.md)
- [Phase 4 Spec](./phase-4.md)
