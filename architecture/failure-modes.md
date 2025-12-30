# PMS-Webapp Failure Mode Analysis

**Version:** 1.0.0
**Last Updated:** 2025-12-21
**Status:** Approved

---

## Executive Summary

This document provides a comprehensive analysis of failure modes for the PMS-Webapp system, covering all five integrated channel platforms (Airbnb, Booking.com, Expedia, FeWo-direkt, Google Vacation Rentals) and internal system components. Each failure mode includes detection mechanisms, mitigation strategies, and recovery procedures.

---

## 1. Channel Platform Failure Modes

### 1.1 Airbnb API

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Rate limit exceeded (429) | HTTP 429 response, `Retry-After` header | Token bucket rate limiter, request queue | Exponential backoff (1m, 2m, 4m, 8m, max 15m) |
| OAuth token expiration | HTTP 401 response | Token refresh 5 min before expiry | Auto-refresh using refresh token |
| OAuth token revocation | HTTP 401 after refresh attempt | Detect invalid_grant error | Alert owner, require re-authorization |
| API downtime (5xx) | HTTP 500/502/503 responses | Circuit breaker opens after 5 failures in 1 min | Queue requests, retry when circuit half-opens (30s) |
| Webhook delivery failure | No webhook received for known booking | Polling fallback every 5 minutes | Import missing bookings during reconciliation |
| Webhook signature invalid | Signature verification fails | Reject webhook, log attempt | Alert security team, no retry |
| Malformed API response | JSON parse error | Validate response schema | Log error, retry 3x, alert on persistent failure |
| Network timeout | Request exceeds 30s timeout | Set aggressive timeout (10s), circuit breaker | Retry with backoff, queue for later |
| Listing sync conflict | Listing data mismatch | Detect during reconciliation | Owner resolves manually, apply Core state |

**Airbnb-Specific Considerations:**
- API version deprecation: Monitor Airbnb developer announcements
- Sandbox vs Production differences: Test thoroughly in sandbox
- Calendar sync delay: Airbnb may take up to 15 minutes to reflect changes

**Metrics to Monitor:**
- `airbnb_api_latency_seconds` (p50, p95, p99)
- `airbnb_api_error_rate` (by error code)
- `airbnb_circuit_breaker_state`
- `airbnb_token_refresh_failures`

---

### 1.2 Booking.com API

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Rate limit exceeded | HTTP 429 or custom error code | Lower rate limit (5 req/sec), strict queue | Backoff per Booking.com guidelines |
| XML parsing error | XML schema validation failure | Strict XSD validation before processing | Log malformed XML, alert, skip message |
| Authentication failure | HTTP 401/403 | Validate credentials on startup | Alert ops team, require manual credential update |
| API downtime | HTTP 5xx | Circuit breaker | Queue and retry |
| Reservation status mismatch | Status differs from PMS | Compare during sync | Booking.com status wins for their bookings |
| Missing availability update | Channel shows stale availability | Periodic full availability push | Daily reconciliation corrects drift |
| Connectivity zones | Region-specific API endpoints down | Multi-region health checks | Failover to backup endpoint if available |

**Booking.com-Specific Considerations:**
- Uses XML format (unlike others using JSON)
- Stricter rate limits than most platforms
- Requires specific reservation states (e.g., `modified`, `cancelled`)
- Extranet may show different data than API (reconcile via API only)

**Metrics to Monitor:**
- `booking_com_xml_parse_errors`
- `booking_com_sync_latency_seconds`
- `booking_com_reservation_state_mismatches`

---

### 1.3 Expedia API

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Rate limit exceeded (50 req/sec) | HTTP 429 | Higher limit, but still enforce bucket | Standard backoff |
| Network timeout | > 30s response time | 10s timeout, retry | 3 retries with exponential backoff |
| Invalid property mapping | Property ID not found | Validate mapping on connection | Alert owner, require re-mapping |
| Authentication error | HTTP 401 | Token validation | Re-authenticate, alert if persistent |
| Partial sync failure | Some updates succeed, others fail | Atomic batch operations where possible | Retry failed items individually |
| Rate card sync failure | Pricing not reflected | Validate rate cards after sync | Force full rate sync |
| Webhook payload changes | Unexpected fields/format | Lenient parsing, log unknown fields | Adapt parser, alert dev team |

**Expedia-Specific Considerations:**
- Higher rate limits (50 req/sec) allow faster sync
- Complex rate/inventory model (room types, rate plans)
- Requires maintaining property content separately
- Longer booking lead times typical

**Metrics to Monitor:**
- `expedia_sync_batch_size`
- `expedia_partial_failure_rate`
- `expedia_rate_card_sync_success_rate`

---

### 1.4 FeWo-direkt (Vrbo) API

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Rate limit exceeded | HTTP 429 | Token bucket (10 req/sec) | Backoff and queue |
| OAuth token expiration | HTTP 401 | Proactive refresh | Auto-refresh with buffer |
| API version deprecation | Deprecation headers | Monitor headers, subscribe to announcements | Upgrade adapter before deadline |
| Calendar sync lag | Availability not updated | Detect stale data | Force full calendar push |
| Booking modification conflicts | Conflicting updates | Lock booking during modification | Last-write-wins with audit |
| Webhook delivery issues | Missing notifications | Polling fallback (5 min) | Reconciliation catches gaps |
| Property matching errors | Listing not found | Validate external ID | Re-link property |

**FeWo-direkt-Specific Considerations:**
- Part of Vrbo/Expedia Group, but separate API
- Popular in Germany, Austria, Switzerland
- Supports multiple languages/currencies
- Calendar representation may differ from other platforms

**Metrics to Monitor:**
- `fewo_direkt_calendar_sync_delay`
- `fewo_direkt_booking_import_errors`
- `fewo_direkt_webhook_delivery_rate`

---

### 1.5 Google Vacation Rentals API

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Rate limit exceeded (100 req/sec) | HTTP 429, `Retry-After` | High limit, but enforce bucket | Standard backoff |
| OAuth/Service account error | HTTP 401/403 | Validate service account credentials | Rotate credentials, re-authorize |
| Feed ingestion delay | Listings not appearing in search | Monitor feed status dashboard | Re-submit feed, contact Google support |
| Landing page policy violation | Listing suspended | Monitor listing status | Fix violations, appeal |
| Booking API not enabled | Booking attempts fail | Verify API enablement | Enable in Google Cloud Console |
| Price accuracy issues | Prices mismatch | Hash-based change detection | Force full price sync |
| Schema validation errors | Feed rejected | Validate against Google schema | Fix schema issues, re-submit |

**Google VR-Specific Considerations:**
- Uses feed-based ingestion (not purely real-time API)
- Strict landing page and pricing policies
- Booking may go through Google-hosted flow
- Integration with Google Hotel Ads

**Metrics to Monitor:**
- `google_vr_feed_submission_latency`
- `google_vr_listing_status` (active, suspended, pending)
- `google_vr_price_accuracy_score`
- `google_vr_booking_conversion_rate`

---

## 2. Internal System Failure Modes

### 2.1 Database (PostgreSQL/Supabase)

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Connection pool exhausted | Connection timeout errors | Pool size 20, overflow 10, recycle 1800s | Increase pool, investigate leaks |
| Connection loss | `ConnectionError` exceptions | Auto-reconnect with backoff | Retry operations, failover to replica |
| Slow queries | Query time > 1s | Query timeout (10s), EXPLAIN ANALYZE | Add indexes, optimize queries |
| Deadlocks | `DeadlockError` | Ordered lock acquisition | Retry transaction |
| Disk space exhaustion | Disk usage > 90% | Alert at 80%, auto-vacuum | Emergency cleanup, scale storage |
| Replication lag | Replica > 10s behind primary | Monitor replication_lag metric | Route reads to primary temporarily |
| RLS policy bypass | Unauthorized data access | Audit logs, security tests | Immediate investigation, patch |
| Backup failure | Backup job fails | Monitor backup status | Manual backup, investigate cause |

**Recovery Procedures:**

```python
# Connection pool configuration
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True,  # Verify connection health
    connect_args={
        "command_timeout": 10,
        "server_settings": {
            "statement_timeout": "10000"  # 10s query timeout
        }
    }
)

# Retry decorator for transient failures
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
async def execute_with_retry(query):
    async with engine.connect() as conn:
        return await conn.execute(query)
```

---

### 2.2 Redis (Cache & Queue)

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Connection failure | `ConnectionError` | Connection pool, retry | Failover to replica (Upstash auto) |
| Memory exhaustion | Memory usage > 90% | maxmemory policy (allkeys-lru) | Eviction, increase memory |
| Cache miss storm | High DB load after cache clear | Cache warming, staggered TTLs | Gradual repopulation |
| Lock expiration (during operation) | Lock lost mid-operation | Extend lock, watchdog thread | Abort and retry operation |
| Queue message loss | Messages disappear | Persistent queues (AOF) | Investigate, replay from DB |
| Pub/Sub disconnect | Subscribers miss messages | Auto-reconnect, replay | Re-subscribe, fetch missed |

**Graceful Degradation (Redis Unavailable):**

```python
class CacheManager:
    async def get(self, key: str) -> Optional[str]:
        try:
            return await self.redis.get(key)
        except RedisError as e:
            logger.warning(f"Redis unavailable, falling back to DB: {e}")
            # Graceful degradation: bypass cache
            return None

    async def availability_check(self, property_id: str, dates: DateRange) -> bool:
        # Try cache first
        cache_key = f"availability:{property_id}:{dates.start}:{dates.end}"

        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except RedisError:
            pass  # Fall through to DB

        # Direct DB query
        return await self.db.check_availability(property_id, dates)
```

---

### 2.3 Celery Workers (Task Queue)

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Worker crash | Worker heartbeat missing | Supervisor/systemd auto-restart | Task re-queued automatically |
| Task timeout | Task exceeds time_limit | Soft limit (warning), hard limit (kill) | Retry with backoff |
| Queue backlog | Queue depth > threshold | Auto-scale workers, alert | Add workers, prioritize critical tasks |
| Dead letter queue overflow | DLQ size > threshold | Monitor DLQ, alert | Manual investigation and replay |
| Duplicate task execution | Same task runs twice | Idempotency keys in Redis | Check idempotency before processing |
| Memory leak in worker | Memory grows over time | max_tasks_per_child limit | Worker recycles after N tasks |

**Celery Configuration:**

```python
app = Celery('pms_webapp')

app.conf.update(
    # Task execution limits
    task_soft_time_limit=120,  # Soft limit: 2 minutes (warning)
    task_time_limit=180,       # Hard limit: 3 minutes (kill)

    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,  # Recycle after 1000 tasks

    # Retry settings
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,  # Re-queue if worker dies

    # Dead letter queue
    task_routes={
        'sync.*': {'queue': 'sync', 'routing_key': 'sync'},
        'notify.*': {'queue': 'notifications', 'routing_key': 'notify'},
    },
)

# Retry configuration per task
@app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True
)
def sync_to_channel(self, booking_id: str, channel: str):
    try:
        # Sync logic
        pass
    except RateLimitError as e:
        raise self.retry(exc=e, countdown=e.retry_after)
    except ChannelApiError as e:
        raise self.retry(exc=e)
```

---

### 2.4 API Backend (FastAPI)

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| High latency | Response time > 500ms (p99) | Caching, query optimization | Scale up, identify slow endpoints |
| Memory exhaustion | Memory usage > 85% | Memory limits, profiling | Restart pods, investigate leaks |
| Unhandled exception | 500 Internal Server Error | Global exception handler | Log, alert, return safe error |
| Request timeout | Gateway timeout (30s) | Background tasks for long ops | Async processing, polling |
| Rate limit (own API) | Too many requests from client | Token bucket per user/IP | Enforce limits, return 429 |
| Validation error | Invalid request payload | Pydantic validation | Return 422 with details |
| Authentication failure | Invalid/expired JWT | Middleware validation | Return 401, client re-auth |

**Error Handling:**

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log with correlation ID
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    logger.error(
        "Unhandled exception",
        correlation_id=correlation_id,
        path=request.url.path,
        error=str(exc),
        exc_info=True
    )

    # Don't expose internal details to client
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
            "correlation_id": correlation_id
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.detail.get("code", "ERROR") if isinstance(exc.detail, dict) else "ERROR",
            "message": exc.detail.get("message", str(exc.detail)) if isinstance(exc.detail, dict) else str(exc.detail)
        }
    )
```

---

### 2.5 Frontend (Next.js)

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Build failure | CI/CD pipeline fails | Pre-commit linting, type checking | Fix errors, rebuild |
| SSR error | Server-side render crash | Error boundaries, fallback content | Show error page, log |
| API unreachable | Network error | Retry with exponential backoff | Show offline state, retry button |
| Slow hydration | High TTI (Time to Interactive) | Code splitting, lazy loading | Optimize bundle size |
| Stale data | Cache not invalidated | SWR revalidation, cache tags | Force revalidation |
| Auth token expiration | 401 from API | Token refresh interceptor | Silent refresh or redirect to login |

---

## 3. Cross-Cutting Failure Modes

### 3.1 Double-Booking Prevention

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Lock acquisition race | Two requests for same dates | Redis distributed lock with SETNX | First lock wins, second fails immediately |
| Lock expiration mid-booking | Long checkout flow | Lock renewal (watchdog), 10min TTL | Warn user, restart flow |
| Database constraint violation | Overlap exclusion constraint fails | Database-level EXCLUDE constraint | Catch exception, return conflict error |
| Channel sync delay | Booking on channel before sync | Near-real-time sync (< 30s) | Reject conflicting booking, notify |
| Reconciliation finds double | Two bookings for same dates | Daily reconciliation check | Alert ops, manual resolution |

**Implementation:**

```python
async def create_booking_with_lock(booking_data: BookingCreate) -> Booking:
    lock_key = f"calendar:lock:{booking_data.property_id}"

    async with redis_lock(lock_key, timeout=600) as lock:
        if not lock:
            raise ConflictError("Property calendar is locked by another booking")

        # Double-check availability (lock held)
        if not await check_availability(booking_data):
            raise ConflictError("Dates no longer available")

        # Create booking (DB constraint is final safeguard)
        try:
            booking = await db.bookings.create(booking_data)
        except IntegrityError as e:
            if "exclude" in str(e).lower():
                raise ConflictError("Dates conflict with existing booking")
            raise

        # Emit event (async sync to channels)
        await emit_event("booking.created", booking)

        return booking
```

---

### 3.2 Data Consistency

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| Event processing failure | Event stuck in queue | Dead letter queue, retry limits | Manual investigation, replay |
| Partial sync | Some channels updated, others not | Track sync status per channel | Retry failed channels |
| Database transaction rollback | Error mid-transaction | Atomic transactions | No partial state, retry whole op |
| Cache-DB inconsistency | Stale cache data | Write-through cache, TTL | Invalidate cache, refresh |
| Event ordering issues | Out-of-order processing | Event timestamps, sequence numbers | Process in order or detect conflicts |

---

### 3.3 Security Failures

| Failure Mode | Detection | Mitigation | Recovery |
|-------------|-----------|------------|----------|
| JWT token compromise | Unusual activity patterns | Short expiry (15min), refresh rotation | Revoke all tokens, force re-auth |
| OAuth token leak | Unexpected API usage | Monitor for unusual patterns | Revoke tokens, rotate secrets |
| SQL injection attempt | WAF detection, query patterns | Parameterized queries, ORM | Block IP, investigate |
| XSS attempt | CSP violation reports | Content Security Policy | Block, log, investigate |
| CSRF attempt | Token validation failure | SameSite cookies, CSRF tokens | Block, log |
| RLS bypass attempt | Unauthorized data access | Audit logging, penetration testing | Investigate, patch, notify |

---

## 4. Failure Response Playbooks

### 4.1 Channel API Outage (e.g., Airbnb Down)

```
TRIGGER: Circuit breaker opens for Airbnb

1. IMMEDIATE (Automated)
   - Circuit breaker blocks new requests
   - Requests queued for retry
   - Alert sent to ops channel (Slack/PagerDuty)

2. ASSESSMENT (5 min)
   - Check Airbnb status page
   - Check our error logs for pattern
   - Determine scope (all properties or subset)

3. COMMUNICATION (10 min)
   - Post status to internal dashboard
   - If extended (>30 min), notify affected owners

4. MONITORING
   - Watch circuit breaker half-open probes
   - Monitor Airbnb status page

5. RECOVERY
   - Circuit closes automatically on success
   - Verify queued requests processed
   - Run reconciliation if outage > 1 hour

6. POST-MORTEM
   - Document timeline
   - Verify no bookings were lost
   - Update runbook if needed
```

### 4.2 Double-Booking Detected

```
TRIGGER: Reconciliation finds overlapping bookings

1. IMMEDIATE (Automated)
   - Alert to ops team (PagerDuty)
   - Flag both bookings in system

2. ASSESSMENT (10 min)
   - Determine booking sources and timestamps
   - Identify which booking came first
   - Check sync logs for failures

3. RESOLUTION
   - Contact later booking guest
   - Offer alternative dates or refund
   - Cancel duplicate booking in all systems

4. ROOT CAUSE
   - Investigate sync failure
   - Check lock mechanism
   - Review constraint violations

5. PREVENTION
   - Fix underlying issue
   - Add monitoring for gap
   - Update runbook
```

### 4.3 Database Connection Crisis

```
TRIGGER: Connection pool exhausted, errors > 10/min

1. IMMEDIATE (Automated)
   - Alert to ops (PagerDuty)
   - Auto-scale if configured

2. TRIAGE (2 min)
   - Check active connections: SELECT * FROM pg_stat_activity
   - Identify connection hogs
   - Check for long-running transactions

3. MITIGATION
   - Kill idle connections if needed
   - Increase pool size temporarily
   - Enable read replica routing

4. INVESTIGATION
   - Review application logs
   - Check for connection leaks
   - Analyze query patterns

5. RESOLUTION
   - Fix connection leaks
   - Optimize pool settings
   - Add connection monitoring
```

---

## 5. Monitoring & Alerting Summary

### 5.1 Critical Alerts (PagerDuty - Immediate Response)

| Alert | Condition | Response Time |
|-------|-----------|---------------|
| Double-booking detected | Any overlap found | < 15 min |
| All channel circuits open | 0 channels healthy | < 5 min |
| Database connection failures | > 10/min for 5 min | < 5 min |
| Payment processing failure | Stripe webhooks failing | < 10 min |
| API error rate spike | 5xx > 5% for 5 min | < 10 min |

### 5.2 Warning Alerts (Slack - Business Hours Response)

| Alert | Condition | Response Time |
|-------|-----------|---------------|
| Single channel circuit open | 1 channel unhealthy | < 1 hour |
| Sync backlog growing | Queue depth > 1000 | < 1 hour |
| Slow API responses | p99 > 1s for 15 min | < 2 hours |
| High memory usage | > 85% for 30 min | < 2 hours |
| Reconciliation mismatches | > 5 per day | < 4 hours |

### 5.3 Informational (Dashboard Only)

- Sync success rates per channel
- API request volumes
- Cache hit rates
- Worker task throughput

---

## 6. Disaster Recovery

### 6.1 Recovery Point Objective (RPO)

| Data Type | RPO | Mechanism |
|-----------|-----|-----------|
| Bookings | 0 (no loss) | Synchronous DB writes |
| Availability | < 5 min | Event replay from sync_events |
| Guest data | < 1 hour | Point-in-time recovery |
| Sync logs | < 24 hours | Daily backups |

### 6.2 Recovery Time Objective (RTO)

| Scenario | RTO | Procedure |
|----------|-----|-----------|
| Single component failure | < 5 min | Auto-restart/failover |
| Database failover | < 1 min | Supabase automatic |
| Full region outage | < 1 hour | Restore from backup, DNS switch |
| Data corruption | < 4 hours | Point-in-time recovery |

---

## Appendix A: Error Code Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `CONFLICT_DOUBLE_BOOKING` | 409 | Dates conflict with existing booking |
| `CONFLICT_CONCURRENT_LOCK` | 409 | Another booking in progress |
| `CHANNEL_UNAVAILABLE` | 503 | Channel API is down |
| `RATE_LIMITED` | 429 | Too many requests |
| `SYNC_FAILED` | 500 | Sync to channel failed |
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `AUTH_REQUIRED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Access denied |
| `NOT_FOUND` | 404 | Resource not found |

---

## Appendix B: Related Documents

- [System Architecture](./system-architecture.md)
- [Sync Workflows](./sync-workflows.mmd)
- [ADR-004: Event-Driven Sync Architecture](./ADRs/ADR-004-event-driven-sync.md)
- [ADR-005: Conflict Resolution Strategy](./ADRs/ADR-005-conflict-resolution.md)
- [ADR-008: Observability Stack](./ADRs/ADR-008-observability.md)
