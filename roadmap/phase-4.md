# Phase 4: Channel Sync Reliability

**Sprint**: 4 of 5
**Duration**: 2 weeks
**Status**: Not Started
**Owner**: Backend Team

## Goal

Harden channel sync with state transitions, retry/backoff/deadletter queue, channel mapping model, inbound webhook skeleton, and reconciliation job for drift detection.

## Scope

### MUST (Sprint Goal)
- ✓ **Sync Log State Transitions**: triggered → running → success/failed (atomic updates)
- ✓ **Retry/Backoff/Deadletter**: Exponential backoff, max retries, deadletter queue
- ✓ **Channel Mapping Model**: Property ↔ platform ID mapping (Airbnb, Booking.com)
- ✓ **Inbound Webhook Skeleton**: Receive updates from channels (secure + validated)
- ✓ **Reconciliation Job Skeleton**: Detect booking drift between PMS and channels

### SHOULD (Nice to Have)
- Webhook signature validation (HMAC, JWT)
- Sync log retention policy (auto-delete old logs)
- Channel-specific error handling (Airbnb vs. Booking.com errors)

### COULD (Stretch)
- Real-time sync status dashboard
- Sync performance metrics (latency, success rate)
- Channel-specific retry strategies

## Deliverables & Definition of Done

### 1. Sync Log State Transitions
**Files Touched**:
- `app/services/channel_sync.py` (state machine logic)
- `app/workers/availability_sync.py` (update state transitions)
- `app/schemas/sync_logs.py` (add state enum)

**DoD**:
- [ ] State enum: `triggered`, `running`, `success`, `failed`, `retrying`
- [ ] Atomic state updates: Use DB transactions
- [ ] Track timestamps: `triggered_at`, `started_at`, `finished_at`
- [ ] Track attempts: `retry_count`, `max_retries`
- [ ] Tests: State transitions are atomic, no race conditions

### 2. Retry/Backoff/Deadletter
**Files Touched**:
- `app/workers/availability_sync.py` (retry logic)
- `app/core/celery_config.py` (retry settings)
- `app/services/deadletter.py` (new service)

**DoD**:
- [ ] Retry with exponential backoff: 1s, 2s, 4s, 8s, 16s
- [ ] Max retries: 5 (configurable)
- [ ] After max retries: Move to deadletter queue
- [ ] Deadletter queue: Store failed tasks with full context
- [ ] Manual retry: Admin can requeue from deadletter
- [ ] Tests: Verify retry behavior, deadletter insertion

### 3. Channel Mapping Model
**Files Touched**:
- `app/models/channel_mappings.py` (new model)
- `app/routers/channel_mappings.py` (CRUD endpoints)
- `app/schemas/channel_mappings.py` (new schema)

**DoD**:
- [ ] Map property → platform listing: `{property_id, platform, listing_id}`
- [ ] Support multiple platforms per property
- [ ] Validate listing_id format per platform
- [ ] CRUD endpoints: Create, read, update, delete mappings
- [ ] Tests: Mapping CRUD operations

### 4. Inbound Webhook Skeleton
**Files Touched**:
- `app/routers/webhooks.py` (new router)
- `app/services/webhook_processor.py` (new service)
- `app/schemas/webhooks.py` (new schema)

**DoD**:
- [ ] `POST /api/v1/webhooks/airbnb` (receive Airbnb webhooks)
- [ ] `POST /api/v1/webhooks/booking_com` (receive Booking.com webhooks)
- [ ] Validate webhook signature (HMAC or JWT)
- [ ] Log all webhooks: `{platform, payload, processed_at, status}`
- [ ] Process asynchronously (queue webhook to Celery task)
- [ ] Tests: Webhook signature validation, payload parsing

### 5. Reconciliation Job Skeleton
**Files Touched**:
- `app/workers/reconciliation.py` (new worker)
- `app/services/reconciliation.py` (new service)
- Celery beat task (daily reconciliation)

**DoD**:
- [ ] Fetch bookings from PMS
- [ ] Fetch bookings from channel (via API)
- [ ] Compare: Detect missing bookings, status mismatches
- [ ] Report: Log discrepancies to `reconciliation_log` table
- [ ] Alert: Notify admin if drift detected
- [ ] Tests: Reconciliation detects drift

## APIs Touched

**New Endpoints**:
- `POST /api/v1/webhooks/airbnb` (receive Airbnb webhooks)
- `POST /api/v1/webhooks/booking_com` (receive Booking.com webhooks)
- `GET /api/v1/channel-mappings` (list mappings)
- `POST /api/v1/channel-mappings` (create mapping)
- `DELETE /api/v1/channel-mappings/:id` (delete mapping)
- `GET /api/v1/sync-logs/:id/retry` (manual retry from deadletter)

**Modified Endpoints**:
- `GET /api/v1/channel-connections/:id/sync-logs` (include retry_count)

**No Breaking Changes**: Existing endpoints remain functional.

## Database Changes

**New Tables**:
1. `channel_mappings`:
   ```sql
   CREATE TABLE channel_mappings (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     property_id UUID NOT NULL REFERENCES properties(id),
     agency_id UUID NOT NULL REFERENCES agencies(id),
     platform TEXT NOT NULL,  -- 'airbnb', 'booking_com', etc.
     listing_id TEXT NOT NULL,  -- Platform-specific listing ID
     created_at TIMESTAMPTZ DEFAULT NOW(),
     UNIQUE(property_id, platform)
   );
   CREATE INDEX idx_channel_mappings_property ON channel_mappings(property_id);
   ```

2. `webhook_log`:
   ```sql
   CREATE TABLE webhook_log (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     platform TEXT NOT NULL,
     payload JSONB NOT NULL,
     signature TEXT,
     status TEXT DEFAULT 'pending',  -- pending, processed, failed
     processed_at TIMESTAMPTZ,
     error TEXT,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_webhook_log_platform ON webhook_log(platform, created_at DESC);
   ```

3. `reconciliation_log`:
   ```sql
   CREATE TABLE reconciliation_log (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     agency_id UUID NOT NULL REFERENCES agencies(id),
     platform TEXT NOT NULL,
     discrepancy_type TEXT NOT NULL,  -- 'missing_booking', 'status_mismatch', etc.
     details JSONB,
     resolved BOOLEAN DEFAULT FALSE,
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_reconciliation_log_agency ON reconciliation_log(agency_id, created_at DESC);
   ```

**Modified Tables**:
- `sync_logs`: Add `retry_count`, `max_retries`, `deadletter_at`

**RLS Policies**:
- Add RLS for all new tables (agency_id scoped)

## Ops Notes

### Deployment
1. Apply migrations (channel_mappings, webhook_log, reconciliation_log)
2. Deploy backend with retry logic
3. Start reconciliation job (Celery beat, daily)
4. Monitor webhook processing latency

### Monitoring
- Alert on deadletter queue growth (sign of systemic issues)
- Track webhook processing latency (should be < 2s p99)
- Monitor reconciliation job for drift detection
- Alert on retry exhaustion (5 retries failed)

### Rollback Plan
- Webhook endpoints are new, safe to disable
- Retry logic is backward compatible (default to sync behavior)
- Reconciliation job is read-only, safe to disable

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Webhook signature validation bypass | High | Use HMAC, validate on every request |
| Deadletter queue unbounded growth | Medium | Auto-cleanup after 30 days |
| Reconciliation job false positives | Medium | Tune detection thresholds, manual review |
| Retry storms (all tasks retry simultaneously) | Low | Jitter in backoff, rate limiting |

## Dependencies

**Blocks**:
- Phase 5 (public API reconciliation)

**Depends On**:
- Phase 1 (audit_log, error taxonomy)
- Phase 2 (booking lifecycle)

## Success Metrics

- ✓ Channel sync success rate > 95%
- ✓ Webhook processing latency < 2s p99
- ✓ Reconciliation job detects drift within 1 hour
- ✓ Deadletter queue < 1% of total syncs

## Next Steps

1. Review this spec with team
2. Create Phase 4 tickets (`/docs/tickets/phase-4.md`)
3. Assign tickets and kickoff sprint
4. Integration tests for webhook processing

---

**Related Documents**:
- [Roadmap Overview](./overview.md)
- [Phase 4 Tickets](../tickets/phase-4.md)
- [Phase 3 Spec](./phase-3.md)
