# Channel Manager Monitoring & Observability

## Overview

This document defines the monitoring strategy for the Channel Manager & Sync Engine. It covers metrics, dashboards, alerting rules, and operational procedures.

---

## 1. Metrics Architecture

### 1.1 Metrics Stack

```
+-------------------+
| Application Code  |
| (Python + Celery) |
+--------+----------+
         |
         v Prometheus client
+-------------------+
| Prometheus Server |
+--------+----------+
         |
         v PromQL
+-------------------+
|      Grafana      |
+-------------------+
         |
         v Alerts
+-------------------+
|    AlertManager   |
+--------+----------+
         |
    +----+----+
    |         |
    v         v
  Slack     PagerDuty
```

### 1.2 Metric Types

| Type | Use Case | Example |
|------|----------|---------|
| Counter | Cumulative events | `channel_sync_total` |
| Gauge | Current state | `circuit_breaker_state` |
| Histogram | Latency distribution | `channel_sync_duration_seconds` |
| Summary | Quantile calculation | `webhook_processing_seconds` |

---

## 2. Key Metrics

### 2.1 Sync Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Sync operations
SYNC_TOTAL = Counter(
    "channel_sync_total",
    "Total sync operations",
    ["channel_type", "sync_type", "direction", "status"]
)

SYNC_DURATION = Histogram(
    "channel_sync_duration_seconds",
    "Sync operation duration",
    ["channel_type", "sync_type"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

SYNC_RECORDS = Counter(
    "channel_sync_records_total",
    "Records processed in sync",
    ["channel_type", "sync_type", "result"]  # result: created, updated, failed, skipped
)

SYNC_IN_PROGRESS = Gauge(
    "channel_sync_in_progress",
    "Currently running sync operations",
    ["channel_type", "sync_type"]
)
```

### 2.2 API Metrics

```python
# External API calls
API_REQUESTS = Counter(
    "channel_api_requests_total",
    "Total API requests to channels",
    ["channel_type", "endpoint", "method", "status_code"]
)

API_LATENCY = Histogram(
    "channel_api_latency_seconds",
    "API call latency",
    ["channel_type", "endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

API_ERRORS = Counter(
    "channel_api_errors_total",
    "API errors by type",
    ["channel_type", "error_type"]  # error_type: timeout, rate_limit, auth, server_error
)
```

### 2.3 Rate Limiting Metrics

```python
RATE_LIMIT_REQUESTS = Counter(
    "channel_rate_limit_requests_total",
    "Rate limit check requests",
    ["channel_type", "result"]  # result: allowed, denied
)

RATE_LIMIT_CURRENT = Gauge(
    "channel_rate_limit_current_count",
    "Current request count in sliding window",
    ["channel_type", "connection_id"]
)

RATE_LIMIT_WAIT_TIME = Histogram(
    "channel_rate_limit_wait_seconds",
    "Time spent waiting for rate limit",
    ["channel_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)
```

### 2.4 Circuit Breaker Metrics

```python
CIRCUIT_STATE = Gauge(
    "channel_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["channel_type"]
)

CIRCUIT_TRANSITIONS = Counter(
    "channel_circuit_breaker_transitions_total",
    "State transitions",
    ["channel_type", "from_state", "to_state"]
)

CIRCUIT_REJECTIONS = Counter(
    "channel_circuit_breaker_rejections_total",
    "Requests rejected by open circuit",
    ["channel_type"]
)
```

### 2.5 Webhook Metrics

```python
WEBHOOK_RECEIVED = Counter(
    "channel_webhook_received_total",
    "Webhooks received",
    ["channel_type", "event_type"]
)

WEBHOOK_PROCESSED = Counter(
    "channel_webhook_processed_total",
    "Webhooks processed",
    ["channel_type", "status"]  # status: success, duplicate, invalid_signature, error
)

WEBHOOK_LATENCY = Histogram(
    "channel_webhook_processing_seconds",
    "Webhook processing time",
    ["channel_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)
```

### 2.6 Token Management Metrics

```python
TOKEN_EXPIRY = Gauge(
    "channel_token_expires_at_timestamp",
    "Token expiry timestamp",
    ["channel_type", "connection_id"]
)

TOKEN_REFRESH_TOTAL = Counter(
    "channel_token_refresh_total",
    "Token refresh attempts",
    ["channel_type", "status"]  # status: success, failure
)
```

### 2.7 Connection Health Metrics

```python
CONNECTIONS_TOTAL = Gauge(
    "channel_connections_total",
    "Total channel connections",
    ["channel_type", "status"]  # status: active, paused, error, disconnected
)

CONNECTIONS_LAST_SYNC = Gauge(
    "channel_connection_last_sync_timestamp",
    "Last successful sync timestamp",
    ["channel_type", "connection_id"]
)

CONNECTIONS_ERROR_COUNT = Gauge(
    "channel_connection_error_count",
    "Consecutive error count",
    ["channel_type", "connection_id"]
)
```

### 2.8 Conflict Metrics

```python
CONFLICTS_TOTAL = Counter(
    "channel_conflicts_total",
    "Conflicts detected",
    ["conflict_type", "channel_type"]
)

CONFLICTS_RESOLVED = Counter(
    "channel_conflicts_resolved_total",
    "Conflicts resolved",
    ["conflict_type", "resolution"]
)

CONFLICTS_REQUIRING_REVIEW = Gauge(
    "channel_conflicts_requiring_review",
    "Conflicts awaiting manual review",
    ["conflict_type"]
)
```

---

## 3. Grafana Dashboards

### 3.1 Channel Manager Overview Dashboard

**Rows:**

1. **Summary Stats (Stat Panels)**
   - Total Active Connections
   - Sync Success Rate (24h)
   - Average Sync Latency
   - Open Alerts

2. **Sync Activity (Time Series)**
   - Syncs per minute by channel
   - Success vs Failure rate
   - Records processed

3. **Channel Health (Table)**
   - Channel | Status | Last Sync | Error Count | Latency P95

4. **Circuit Breaker Status (State Timeline)**
   - Per-channel circuit breaker state over time

### 3.2 Dashboard JSON

```json
{
  "dashboard": {
    "title": "Channel Manager Overview",
    "uid": "channel-manager-overview",
    "tags": ["channel-manager", "pms"],
    "timezone": "browser",
    "refresh": "30s",
    "panels": [
      {
        "id": 1,
        "type": "stat",
        "title": "Active Connections",
        "targets": [
          {
            "expr": "sum(channel_connections_total{status='active'})",
            "legendFormat": "Active"
          }
        ],
        "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4}
      },
      {
        "id": 2,
        "type": "stat",
        "title": "Sync Success Rate (24h)",
        "targets": [
          {
            "expr": "sum(rate(channel_sync_total{status='success'}[24h])) / sum(rate(channel_sync_total[24h])) * 100",
            "legendFormat": "Success Rate"
          }
        ],
        "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4},
        "options": {
          "colorMode": "value",
          "graphMode": "none"
        },
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"value": null, "color": "red"},
                {"value": 90, "color": "yellow"},
                {"value": 99, "color": "green"}
              ]
            }
          }
        }
      },
      {
        "id": 3,
        "type": "timeseries",
        "title": "Sync Operations per Channel",
        "targets": [
          {
            "expr": "sum by (channel_type) (rate(channel_sync_total[5m]))",
            "legendFormat": "{{channel_type}}"
          }
        ],
        "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8}
      },
      {
        "id": 4,
        "type": "timeseries",
        "title": "Sync Latency by Channel (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum by (channel_type, le) (rate(channel_sync_duration_seconds_bucket[5m])))",
            "legendFormat": "{{channel_type}} P95"
          }
        ],
        "gridPos": {"x": 12, "y": 4, "w": 12, "h": 8}
      },
      {
        "id": 5,
        "type": "stat",
        "title": "Circuit Breakers Open",
        "targets": [
          {
            "expr": "sum(channel_circuit_breaker_state == 1)",
            "legendFormat": "Open"
          }
        ],
        "gridPos": {"x": 12, "y": 0, "w": 6, "h": 4},
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                {"value": null, "color": "green"},
                {"value": 1, "color": "red"}
              ]
            }
          }
        }
      }
    ]
  }
}
```

### 3.3 Per-Platform Dashboard

Each platform gets a dedicated dashboard with:

1. **Connection Status** - All connections for this platform
2. **Sync Timeline** - Sync operations over time
3. **Error Breakdown** - Errors by type
4. **Rate Limit Usage** - Current vs limit
5. **Token Status** - Expiry countdown

---

## 4. Alerting Rules

### 4.1 Critical Alerts

```yaml
groups:
  - name: channel_manager_critical
    interval: 30s
    rules:
      # High failure rate
      - alert: ChannelSyncHighFailureRate
        expr: |
          sum(rate(channel_sync_total{status="failure"}[5m])) by (channel_type)
          /
          sum(rate(channel_sync_total[5m])) by (channel_type)
          > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High sync failure rate for {{ $labels.channel_type }}"
          description: "Sync failure rate is {{ $value | humanizePercentage }} (threshold: 10%)"
          runbook_url: "https://wiki.example.com/runbooks/channel-sync-failures"

      # Circuit breaker open too long
      - alert: ChannelCircuitBreakerOpen
        expr: channel_circuit_breaker_state == 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker OPEN for {{ $labels.channel_type }}"
          description: "Circuit has been open for more than 5 minutes"
          runbook_url: "https://wiki.example.com/runbooks/circuit-breaker"

      # Token expiring soon
      - alert: ChannelTokenExpiringCritical
        expr: (channel_token_expires_at_timestamp - time()) < 86400
        labels:
          severity: critical
        annotations:
          summary: "OAuth token expires in < 24 hours"
          description: "Token for {{ $labels.channel_type }} connection {{ $labels.connection_id }} expires soon"

      # Webhook processing failing
      - alert: ChannelWebhookProcessingFailing
        expr: |
          sum(rate(channel_webhook_processed_total{status="error"}[5m])) by (channel_type)
          /
          sum(rate(channel_webhook_received_total[5m])) by (channel_type)
          > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Webhook processing errors for {{ $labels.channel_type }}"
```

### 4.2 Warning Alerts

```yaml
  - name: channel_manager_warning
    interval: 1m
    rules:
      # Rate limit approaching
      - alert: ChannelRateLimitApproaching
        expr: |
          channel_rate_limit_current_count
          /
          on(channel_type) group_left
          channel_rate_limit_max
          > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Rate limit usage > 80% for {{ $labels.channel_type }}"

      # Sync latency increasing
      - alert: ChannelSyncLatencyHigh
        expr: |
          histogram_quantile(0.95, sum by (channel_type, le) (rate(channel_sync_duration_seconds_bucket[15m])))
          > 10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Sync latency P95 > 10s for {{ $labels.channel_type }}"

      # Connection errors increasing
      - alert: ChannelConnectionErrorsIncreasing
        expr: |
          increase(channel_connection_error_count[1h]) > 5
        labels:
          severity: warning
        annotations:
          summary: "Connection errors increasing for {{ $labels.connection_id }}"

      # Token expiring in 7 days
      - alert: ChannelTokenExpiringSoon
        expr: (channel_token_expires_at_timestamp - time()) < 604800
        labels:
          severity: warning
        annotations:
          summary: "OAuth token expires in < 7 days"
```

### 4.3 Info Alerts

```yaml
  - name: channel_manager_info
    interval: 5m
    rules:
      # Daily reconciliation drift
      - alert: ChannelAvailabilityDriftDetected
        expr: channel_reconciliation_drift_days > 5
        labels:
          severity: info
        annotations:
          summary: "Availability drift detected for {{ $labels.channel_type }}"
          description: "{{ $value }} days of drift detected in last reconciliation"

      # New connection inactive
      - alert: ChannelNewConnectionInactive
        expr: |
          (time() - channel_connection_created_at) > 86400
          and
          channel_connections_last_sync == 0
        labels:
          severity: info
        annotations:
          summary: "New connection inactive for 24h"
```

---

## 5. Log Aggregation

### 5.1 Structured Logging

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Example log entries
logger.info(
    "sync_started",
    channel_type="airbnb",
    connection_id="abc-123",
    sync_type="availability_export",
    direction="outbound"
)

logger.info(
    "sync_completed",
    channel_type="airbnb",
    connection_id="abc-123",
    sync_type="availability_export",
    duration_ms=1234,
    records_processed=30,
    records_updated=28,
    records_failed=2
)

logger.warning(
    "rate_limit_exceeded",
    channel_type="airbnb",
    connection_id="abc-123",
    retry_after_seconds=5.2
)

logger.error(
    "sync_failed",
    channel_type="airbnb",
    connection_id="abc-123",
    error="AuthenticationError",
    error_message="Token expired"
)
```

### 5.2 Log Queries (Elasticsearch/Loki)

```
# Failed syncs in last hour
level:error AND message:sync_failed AND @timestamp:[now-1h TO now]

# Rate limit events by channel
level:warning AND message:rate_limit_exceeded | stats count by channel_type

# Webhook errors
level:error AND message:webhook_* | stats count by channel_type, error

# Slow syncs (>5s)
message:sync_completed AND duration_ms:>5000
```

---

## 6. SLOs and SLIs

### 6.1 Service Level Objectives

| SLO | Target | Measurement |
|-----|--------|-------------|
| Sync Availability | 99.9% | % of sync requests that complete without error |
| Sync Latency | P95 < 10s | 95th percentile of sync duration |
| Webhook Processing | 99.95% | % of webhooks processed successfully |
| Token Refresh | 100% | All tokens refreshed before expiry |
| Data Consistency | 99.9% | % of days with no reconciliation drift |

### 6.2 SLI Calculations

```promql
# Sync Availability SLI
sum(rate(channel_sync_total{status="success"}[30d]))
/
sum(rate(channel_sync_total[30d]))

# Sync Latency SLI (P95 under 10s)
histogram_quantile(0.95, sum(rate(channel_sync_duration_seconds_bucket[30d])))

# Webhook Processing SLI
(
  sum(rate(channel_webhook_processed_total{status="success"}[30d]))
  +
  sum(rate(channel_webhook_processed_total{status="duplicate"}[30d]))
)
/
sum(rate(channel_webhook_received_total[30d]))
```

---

## 7. Runbooks

### 7.1 Circuit Breaker Open

**Trigger:** `ChannelCircuitBreakerOpen` alert

**Steps:**
1. Check the channel's status page for outages
2. Review recent API error logs: `level:error AND channel_type:${channel}`
3. If platform is down: Wait for recovery, circuit will auto-reset
4. If our issue: Check for expired tokens, rate limiting, or code bugs
5. Manual reset (if needed): `redis-cli DEL circuit_breaker:${channel}:state`

### 7.2 High Sync Failure Rate

**Trigger:** `ChannelSyncHighFailureRate` alert

**Steps:**
1. Check error breakdown: Query `channel_api_errors_total`
2. If auth errors: Run token refresh manually
3. If rate limit: Reduce worker concurrency
4. If server errors: Check platform status, enable backoff

### 7.3 Token Expiring

**Trigger:** `ChannelTokenExpiringCritical` alert

**Steps:**
1. Attempt automatic refresh: `celery call channel_manager.refresh_single_token --args='["connection-id"]'`
2. If refresh fails: Check platform's OAuth app status
3. If persistent: User may need to re-authorize via OAuth flow

---

## 8. Operational Procedures

### 8.1 Daily Health Check

```bash
#!/bin/bash
# daily-health-check.sh

echo "=== Channel Manager Health Check ==="
echo

echo "1. Connection Status:"
curl -s http://localhost:8000/api/v1/channels/status | jq '.connections | group_by(.status) | map({status: .[0].status, count: length})'

echo
echo "2. Circuit Breaker States:"
curl -s http://localhost:8000/api/v1/channels/circuit-breakers | jq '.[] | {channel: .channel_type, state: .state}'

echo
echo "3. Sync Success Rate (24h):"
curl -s "http://prometheus:9090/api/v1/query?query=sum(rate(channel_sync_total{status='success'}[24h]))/sum(rate(channel_sync_total[24h]))*100" | jq '.data.result[0].value[1]'

echo
echo "4. Pending Reconciliation Issues:"
curl -s http://localhost:8000/api/v1/channels/reconciliation/pending | jq '.count'

echo
echo "5. Tokens Expiring Soon:"
curl -s http://localhost:8000/api/v1/channels/tokens/expiring | jq '.[] | {connection: .connection_id, expires_in_days: .expires_in_days}'
```

### 8.2 Emergency Procedures

**Disable All Sync for a Channel:**
```bash
# Via API
curl -X POST http://localhost:8000/api/v1/channels/${CHANNEL}/pause-all

# Via Redis
redis-cli SET channel_manager:${CHANNEL}:paused "true"
```

**Force Close Circuit Breaker:**
```bash
curl -X POST http://localhost:8000/api/v1/channels/${CHANNEL}/circuit-breaker/close
```

**Clear Rate Limit:**
```bash
redis-cli DEL "rate_limit:${CHANNEL}:*"
```

---

## 9. Capacity Planning

### 9.1 Resource Estimates

| Component | CPU | Memory | Scale Factor |
|-----------|-----|--------|--------------|
| FastAPI (webhooks) | 0.5 core | 512MB | 1 per 100 req/s |
| Celery Worker (outbound) | 1 core | 1GB | 1 per 50 connections |
| Celery Worker (inbound) | 0.5 core | 512MB | 1 per 200 webhooks/min |
| Redis | 1 core | 2GB | 1 per 1000 connections |

### 9.2 Scaling Triggers

- Scale outbound workers when sync queue depth > 1000
- Scale webhook handlers when latency P95 > 1s
- Scale Redis when memory usage > 80%

---

*Document Version: 1.0.0*
*Last Updated: 2024-12-21*
*Author: channel-manager-architect*
