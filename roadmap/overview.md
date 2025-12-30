# Sprint Roadmap: Phases 1-5 Overview

**Document Status**: Living roadmap (updated as sprints progress)
**Last Updated**: 2025-12-30
**Target Timeline**: 5 sprints × 2 weeks = 10 weeks

## Executive Summary

This roadmap defines 5 sequential sprints to harden the PMS backend for production readiness. The focus is on:
- **Reliability**: RBAC, tenant isolation, error handling, idempotency
- **Feature completeness**: Availability rules, booking lifecycle, pricing logic
- **Channel integration**: Sync reliability, retry mechanisms, webhooks
- **API maturity**: Public APIs, checkout flow, owner-facing endpoints
- **Observability**: Ops tooling, monitoring, degraded mode

## Sequencing Rationale

```
Phase 1: Foundation (RBAC, isolation, ops tooling)
  ↓
Phase 2: Core domain (availability, booking lifecycle)
  ↓
Phase 3: Pricing & quoting (seasons, min stay, quote API)
  ↓
Phase 4: Channel sync reliability (retry, webhooks, reconciliation)
  ↓
Phase 5: Public APIs & polish (checkout, owner APIs, observability)
```

**Why this order?**
1. **Phase 1 first**: Security and ops tooling must be solid before adding features
2. **Phase 2 before 3**: Availability/booking logic is prerequisite for pricing
3. **Phase 4 after core**: Channel sync improvements require stable booking core
4. **Phase 5 last**: Public APIs and checkout depend on all prior work

## Dependencies Between Phases

| Phase | Depends On | Enables |
|-------|------------|---------|
| Phase 1 | None (foundation) | All subsequent phases |
| Phase 2 | Phase 1 (RBAC, migrations) | Phase 3, Phase 5 |
| Phase 3 | Phase 2 (booking core) | Phase 5 (checkout) |
| Phase 4 | Phase 1, Phase 2 | Phase 5 (reconciliation) |
| Phase 5 | All prior phases | Production launch |

## Phase Summaries

### Phase 1: Foundation & Ops Tooling (Sprint 1)
**Goal**: Lock down security, tenant isolation, error handling, ops observability

**Key Deliverables**:
- RBAC finalization (admin/manager/staff/owner/accountant roles)
- Tenant isolation audit (all queries filtered by agency_id)
- Mandatory migrations workflow
- Error taxonomy + 503 degraded mode
- Ops runbook endpoints (/ops/current-commit, /ops/env-sanity)

**Success Criteria**:
- Zero RLS bypass vulnerabilities
- All errors use standardized exceptions
- Ops endpoints return actionable diagnostics

### Phase 2: Availability & Booking Lifecycle (Sprint 2)
**Goal**: Complete availability rules, booking state machine, idempotency

**Key Deliverables**:
- Availability rules completeness (blocked dates, min stay, buffer days)
- Booking lifecycle (pending → confirmed → cancelled → refunded)
- Idempotency for booking creation (prevent duplicate bookings)
- Holds/blocks primitives (temporary reservations)

**Success Criteria**:
- Availability queries respect all rules
- Booking state transitions are atomic and logged
- Duplicate booking creation is impossible

### Phase 3: Pricing & Quoting (Sprint 3)
**Goal**: Implement dynamic pricing, seasonal rates, quote endpoint

**Key Deliverables**:
- Pricing base logic (nightly rates, cleaning fees, taxes)
- Season/min stay rules
- Quote endpoint (calculate total without creating booking)
- Hold/expiry skeleton (temporary price locks)

**Success Criteria**:
- Quote API returns accurate pricing breakdown
- Seasonal rates apply correctly
- Quotes can be held for configurable duration

### Phase 4: Channel Sync Reliability (Sprint 4)
**Goal**: Harden channel sync with retry, backoff, webhooks, reconciliation

**Key Deliverables**:
- Sync log state transitions (triggered → running → success/failed)
- Retry/backoff/deadletter queue
- Channel mapping model (property ↔ platform IDs)
- Inbound webhook skeleton (receive updates from channels)
- Reconciliation job skeleton (detect drift)

**Success Criteria**:
- Failed syncs retry with exponential backoff
- Webhook endpoints are secure and validated
- Reconciliation job detects booking drift

### Phase 5: Public APIs & Polish (Sprint 5)
**Goal**: Expose public APIs, checkout flow, owner-facing endpoints, observability

**Key Deliverables**:
- Public read APIs (properties, availability, rates)
- Checkout flow (quote → booking with payment)
- Owner read APIs + documents (bookings, revenue, documents)
- Observability polish (structured logging, metrics, traces)

**Success Criteria**:
- Public APIs are versioned and documented
- Checkout flow is end-to-end tested
- Owner APIs enforce row-level security

## Risk Management

### High-Risk Items
| Risk | Mitigation | Owner Phase |
|------|------------|-------------|
| RLS bypass in tenant isolation | Full audit + tests in Phase 1 | Phase 1 |
| Booking race conditions | Idempotency + DB constraints | Phase 2 |
| Pricing calculation errors | Unit tests + quote validation | Phase 3 |
| Channel sync data loss | Retry + deadletter + reconciliation | Phase 4 |
| Public API security | Auth middleware + rate limiting | Phase 5 |

### Low-Risk Items
| Risk | Mitigation | Owner Phase |
|------|------------|-------------|
| Migration failures | Rollback plan + testing | Phase 1 |
| Performance degradation | Load testing + caching | Phase 5 |
| Documentation drift | Living docs + CI checks | All phases |

## Feature Flags & Rollout Strategy

**Global Feature Flags** (see `modules-and-entitlements.md`):
- `MODULES_ENABLED`: Global kill switch for new modules
- Per-agency entitlements in `agency_features` table

**Rollout Approach**:
1. **Phase 1-2**: Backend-only, no customer-facing changes
2. **Phase 3**: Soft launch quote API to internal users
3. **Phase 4**: Enable channel sync for pilot agencies
4. **Phase 5**: Public API beta, gradual rollout

## Success Metrics

### Phase 1
- ✓ 100% of queries use RLS or explicit agency_id filter
- ✓ All endpoints return structured errors (no raw exceptions)
- ✓ Ops endpoints deployed and monitored

### Phase 2
- ✓ Availability checks pass 100% of rule validations
- ✓ Zero duplicate bookings in production
- ✓ Booking state transitions logged in audit_log

### Phase 3
- ✓ Quote API response time < 500ms p99
- ✓ Pricing calculations match manual verification
- ✓ Hold expiry job runs reliably

### Phase 4
- ✓ Channel sync success rate > 95%
- ✓ Webhook processing latency < 2s p99
- ✓ Reconciliation job detects drift within 1 hour

### Phase 5
- ✓ Public API documentation published
- ✓ Checkout flow conversion rate measured
- ✓ Owner API adoption > 50% of agencies

## Communication Plan

**Weekly**:
- Sprint standup (progress, blockers, risks)
- Updated ticket status in `/docs/tickets/phase-N.md`

**Per Phase**:
- Phase kickoff (review spec, assign tickets)
- Mid-phase checkpoint (pivot if needed)
- Phase retrospective (lessons learned, update overview)

**Stakeholders**:
- Engineering: Implement tickets, review PRs
- Product: Validate deliverables, adjust scope
- Ops: Monitor runbook endpoints, alert on anomalies

## Next Steps

1. Review this overview with team
2. Deep-dive into Phase 1 spec (`phase-1.md`)
3. Assign Phase 1 tickets (`/docs/tickets/phase-1.md`)
4. Kickoff Sprint 1

---

**Related Documents**:
- [Phase 1 Spec](./phase-1.md)
- [Phase 1 Tickets](../tickets/phase-1.md)
- [Modules & Entitlements Architecture](../architecture/modules-and-entitlements.md)
