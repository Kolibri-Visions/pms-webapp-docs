# Phase 4 Tickets: Channel Sync Reliability

**Sprint**: 4 of 5
**Total Tickets**: 11
**Estimated Points**: 23

## Ticket List

### P4-01: Add retry_count fields to sync_logs
**Priority**: High | **Points**: 1
**Touch Points**: `supabase/migrations/`, `app/schemas/sync_logs.py`

**Acceptance Criteria**:
- [ ] Add columns: retry_count, max_retries, deadletter_at
- [ ] Migration with default values
- [ ] Update schema

---

### P4-02: Implement sync log state transitions
**Priority**: High | **Points**: 3
**Touch Points**: `app/services/channel_sync.py`, `app/workers/availability_sync.py`

**Acceptance Criteria**:
- [ ] Atomic state updates (use transactions)
- [ ] Track timestamps: triggered_at, started_at, finished_at
- [ ] Add `retrying` status
- [ ] Tests: State transitions are atomic

---

### P4-03: Implement retry with exponential backoff
**Priority**: High | **Points**: 3
**Touch Points**: `app/workers/availability_sync.py`, `app/core/celery_config.py`

**Acceptance Criteria**:
- [ ] Retry delays: 1s, 2s, 4s, 8s, 16s
- [ ] Max retries: 5 (configurable)
- [ ] Increment retry_count on each attempt
- [ ] Tests: Verify retry behavior

---

### P4-04: Create deadletter queue service
**Priority**: High | **Points**: 2
**Touch Points**: `app/services/deadletter.py` (new)

**Acceptance Criteria**:
- [ ] Move failed tasks to deadletter after max retries
- [ ] Store full context (payload, error, attempts)
- [ ] Manual requeue endpoint
- [ ] Tests: Deadletter insertion

---

### P4-05: Create channel_mappings table and CRUD
**Priority**: Medium | **Points**: 2
**Touch Points**: `app/routers/channel_mappings.py`, `supabase/migrations/`

**Acceptance Criteria**:
- [ ] Create `channel_mappings` table
- [ ] CRUD endpoints
- [ ] Validate listing_id format per platform
- [ ] Tests: Mapping CRUD

---

### P4-06: Create webhook log table
**Priority**: Medium | **Points**: 1
**Touch Points**: `supabase/migrations/`, `app/schemas/webhooks.py`

**Acceptance Criteria**:
- [ ] Create `webhook_log` table
- [ ] Schema for webhook events
- [ ] Indexes on platform, created_at

---

### P4-07: Implement webhook endpoints (Airbnb)
**Priority**: High | **Points**: 3
**Touch Points**: `app/routers/webhooks.py` (new)

**Acceptance Criteria**:
- [ ] `POST /api/v1/webhooks/airbnb` endpoint
- [ ] Validate webhook signature (HMAC)
- [ ] Log webhook to webhook_log table
- [ ] Queue processing to Celery
- [ ] Tests: Signature validation

---

### P4-08: Implement webhook endpoints (Booking.com)
**Priority**: Medium | **Points**: 2
**Touch Points**: `app/routers/webhooks.py`

**Acceptance Criteria**:
- [ ] `POST /api/v1/webhooks/booking_com` endpoint
- [ ] Validate signature
- [ ] Log and queue processing
- [ ] Tests: Webhook processing

---

### P4-09: Create reconciliation service
**Priority**: Medium | **Points**: 3
**Touch Points**: `app/services/reconciliation.py` (new)

**Acceptance Criteria**:
- [ ] Fetch bookings from PMS and channel
- [ ] Compare and detect drift
- [ ] Log discrepancies to reconciliation_log
- [ ] Tests: Drift detection

---

### P4-10: Implement reconciliation job
**Priority**: Low | **Points**: 2
**Touch Points**: `app/workers/reconciliation.py` (new)

**Acceptance Criteria**:
- [ ] Celery beat task (daily)
- [ ] Run reconciliation for all agencies
- [ ] Alert on drift detection
- [ ] Tests: Job runs successfully

---

### P4-11: Phase 4 retrospective
**Priority**: Low | **Points**: 1

**Acceptance Criteria**:
- [ ] Team retrospective held
- [ ] Update roadmap
- [ ] Document lessons learned

---

## Dependencies

```
P4-01 → P4-02, P4-03 (Schema changes required)
P4-02 → P4-04 (State machine required for deadletter)
P4-06 → P4-07, P4-08 (Table required for webhooks)
P4-09 → P4-10 (Service required for job)
```
