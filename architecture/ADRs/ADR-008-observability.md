# ADR-008: Observability Stack

**Status:** Accepted
**Date:** 2025-12-21
**Decision Makers:** System Architecture Team

---

## Context

PMS-Webapp is a distributed system with multiple components (Frontend, Backend, Workers, External APIs). We need comprehensive observability to:
- Monitor system health and performance
- Debug issues across service boundaries
- Track business metrics (bookings, conversions)
- Alert on failures and anomalies
- Audit security-relevant events

## Decision Drivers

1. **Visibility**: End-to-end visibility from frontend to external APIs
2. **Cost**: Reasonable pricing at target scale
3. **Ease of Use**: Minimal setup, good default dashboards
4. **Integration**: Works with FastAPI, Next.js, Celery, Supabase
5. **Alerting**: Reliable, actionable alerts

## Observability Pillars

### 1. Metrics (Quantitative Data)

Numbers about system behavior over time.

### 2. Logs (Events)

Structured records of what happened.

### 3. Traces (Request Flow)

End-to-end visibility of request paths.

## Options Considered

### Option 1: Grafana Cloud (Loki + Prometheus + Tempo)

**Pros:**
- Unified platform for all three pillars
- Generous free tier
- Self-service, no enterprise sales
- Open standards (OpenTelemetry, Prometheus)
- Excellent dashboards

**Cons:**
- Multiple components to configure
- Learning curve for Grafana

### Option 2: Datadog

**Pros:**
- All-in-one solution
- Excellent UI/UX
- Advanced APM features
- Strong alerting

**Cons:**
- Expensive at scale
- Vendor lock-in
- Complex pricing model

### Option 3: Self-Hosted (Prometheus + Grafana + Jaeger + ELK)

**Pros:**
- Full control
- No usage-based costs
- Open source

**Cons:**
- Significant operational burden
- High maintenance
- Storage management

### Option 4: Sentry + CloudWatch/Datadog

**Pros:**
- Sentry excellent for errors
- CloudWatch included with AWS

**Cons:**
- Fragmented tooling
- Multiple UIs
- Integration complexity

## Decision

**We choose a hybrid approach:**

1. **Sentry** for error tracking and performance monitoring (frontend + backend)
2. **Grafana Cloud** for metrics, logs, and distributed tracing
3. **Supabase Dashboard** for database-specific metrics

### Rationale

- **Sentry** excels at error tracking with excellent source maps, session replay, and developer-friendly alerts
- **Grafana Cloud** provides a unified view of metrics/logs/traces with OpenTelemetry support
- This combination provides comprehensive coverage without excessive cost

## Implementation

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     OBSERVABILITY STACK                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   Next.js   │  │   FastAPI   │  │   Celery    │                 │
│  │  Frontend   │  │   Backend   │  │   Workers   │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
│         │                │                │                         │
│         ▼                ▼                ▼                         │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │               OpenTelemetry Collector                       │    │
│  │     (Traces + Metrics + Logs aggregation)                  │    │
│  └──────────────────────────┬─────────────────────────────────┘    │
│                              │                                      │
│         ┌────────────────────┼────────────────────┐                │
│         ▼                    ▼                    ▼                │
│  ┌────────────┐      ┌────────────┐      ┌────────────┐           │
│  │   Sentry   │      │  Grafana   │      │  Grafana   │           │
│  │  (Errors)  │      │   Loki     │      │   Tempo    │           │
│  │            │      │  (Logs)    │      │  (Traces)  │           │
│  └────────────┘      └────────────┘      └────────────┘           │
│                              │                                      │
│                              ▼                                      │
│                      ┌────────────┐                                │
│                      │  Grafana   │                                │
│                      │ Dashboards │                                │
│                      └────────────┘                                │
│                              │                                      │
│                              ▼                                      │
│                      ┌────────────┐                                │
│                      │  Alerting  │                                │
│                      │ (PagerDuty/│                                │
│                      │   Slack)   │                                │
│                      └────────────┘                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Metrics

#### Custom Business Metrics

```python
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Booking metrics
bookings_created = Counter(
    'pms_bookings_created_total',
    'Total bookings created',
    ['source', 'property_id']
)

booking_value = Histogram(
    'pms_booking_value_euros',
    'Booking value in euros',
    ['source'],
    buckets=[100, 250, 500, 1000, 2500, 5000, 10000]
)

checkout_duration = Histogram(
    'pms_checkout_duration_seconds',
    'Time from checkout start to confirmation',
    buckets=[30, 60, 120, 300, 600]
)

checkout_abandonment_rate = Gauge(
    'pms_checkout_abandonment_rate',
    'Percentage of started checkouts not completed'
)

# Sync metrics
sync_latency = Histogram(
    'pms_sync_latency_seconds',
    'Time from booking creation to channel sync',
    ['platform'],
    buckets=[1, 5, 10, 30, 60, 120]
)

sync_errors = Counter(
    'pms_sync_errors_total',
    'Total sync errors',
    ['platform', 'error_type']
)

channel_api_requests = Counter(
    'pms_channel_api_requests_total',
    'Channel API requests',
    ['platform', 'endpoint', 'status_code']
)

# Queue metrics
celery_queue_depth = Gauge(
    'pms_celery_queue_depth',
    'Number of tasks in queue',
    ['queue_name']
)
```

#### System Metrics (Auto-Collected)

- CPU, memory, disk usage (via node exporter)
- HTTP request latency (via FastAPI middleware)
- Database connection pool stats
- Redis connection stats

### Logging

#### Structured Logging Setup

```python
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# Middleware for request logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Generate or extract correlation ID
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))

    # Bind context for all logs in this request
    bind_contextvars(
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        user_agent=request.headers.get("user-agent"),
    )

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration = time.perf_counter() - start_time

        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )

        response.headers["X-Correlation-ID"] = correlation_id
        return response

    except Exception as e:
        logger.error(
            "Request failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        raise
    finally:
        clear_contextvars()
```

#### Log Levels Usage

| Level | Use Case | Example |
|-------|----------|---------|
| ERROR | Failures requiring attention | Sync failed, payment error |
| WARNING | Potential issues | Rate limit approached, retry occurred |
| INFO | Significant events | Booking created, sync completed |
| DEBUG | Detailed diagnostics | API request/response, query timing |

### Distributed Tracing

#### OpenTelemetry Setup

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def setup_tracing():
    # Set up tracer provider
    provider = TracerProvider(
        resource=Resource.create({
            "service.name": "pms-webapp-api",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        })
    )

    # Export to Grafana Tempo
    exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        headers={"Authorization": f"Bearer {os.getenv('GRAFANA_OTEL_TOKEN')}"}
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # Auto-instrument libraries
    FastAPIInstrumentor.instrument_app(app)
    CeleryInstrumentor().instrument()
    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=engine)
    HTTPXClientInstrumentor().instrument()

tracer = trace.get_tracer(__name__)


# Custom span for business operations
async def sync_booking_to_channel(booking_id: str, channel: str):
    with tracer.start_as_current_span(
        "sync_booking_to_channel",
        attributes={
            "booking.id": booking_id,
            "channel.name": channel,
        }
    ) as span:
        try:
            result = await do_sync(booking_id, channel)
            span.set_attribute("sync.success", True)
            span.set_attribute("sync.external_id", result.external_id)
            return result
        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise
```

### Error Tracking (Sentry)

#### Sentry Configuration

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "development"),
    release=os.getenv("GIT_SHA", "unknown"),

    # Performance monitoring
    traces_sample_rate=0.1,  # 10% of transactions
    profiles_sample_rate=0.1,  # 10% profiling

    # Integrations
    integrations=[
        FastApiIntegration(transaction_style="url"),
        CeleryIntegration(),
        SqlalchemyIntegration(),
        RedisIntegration(),
    ],

    # Filter sensitive data
    before_send=filter_sensitive_data,

    # Ignore certain errors
    ignore_errors=[
        KeyboardInterrupt,
        SystemExit,
    ],
)

def filter_sensitive_data(event, hint):
    """Remove sensitive data before sending to Sentry."""
    if "request" in event:
        if "headers" in event["request"]:
            # Remove auth headers
            event["request"]["headers"] = {
                k: v for k, v in event["request"]["headers"].items()
                if k.lower() not in ("authorization", "cookie", "x-api-key")
            }
    return event
```

#### Frontend Sentry (Next.js)

```typescript
// sentry.client.config.ts
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT,

  // Performance
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  // Integrations
  integrations: [
    new Sentry.Replay({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],
});
```

### Dashboards

#### Channel Manager Dashboard

```yaml
# Grafana dashboard panels
panels:
  - title: "Sync Status by Channel"
    type: stat
    query: |
      sum by (platform) (
        rate(pms_sync_errors_total[5m])
      ) / sum by (platform) (
        rate(pms_channel_api_requests_total[5m])
      ) * 100

  - title: "Sync Latency (p99)"
    type: timeseries
    query: |
      histogram_quantile(0.99,
        rate(pms_sync_latency_seconds_bucket[5m])
      )

  - title: "Queue Depth"
    type: timeseries
    query: pms_celery_queue_depth

  - title: "API Errors by Channel"
    type: timeseries
    query: |
      sum by (platform, status_code) (
        rate(pms_channel_api_requests_total{status_code=~"5.."}[5m])
      )
```

#### Booking Funnel Dashboard

```yaml
panels:
  - title: "Conversion Funnel"
    type: funnel
    stages:
      - "Property Views"
      - "Availability Checks"
      - "Checkout Started"
      - "Payment Completed"
      - "Booking Confirmed"

  - title: "Booking Revenue (Today)"
    type: stat
    query: |
      sum(increase(pms_booking_value_euros_sum[24h]))

  - title: "Bookings by Source"
    type: piechart
    query: |
      sum by (source) (increase(pms_bookings_created_total[24h]))
```

### Alerting Rules

```yaml
# alerting-rules.yaml
groups:
  - name: pms-critical
    interval: 1m
    rules:
      - alert: DoubleBookingDetected
        expr: increase(pms_double_booking_detected_total[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Double booking detected"
          description: "A double booking was detected. Immediate action required."

      - alert: AllChannelsSyncFailing
        expr: count(pms_circuit_breaker_state == 1) == 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "All channel syncs failing"

      - alert: HighApiErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API error rate above 5%"

  - name: pms-warning
    interval: 5m
    rules:
      - alert: ChannelSyncDegraded
        expr: pms_circuit_breaker_state{platform=~".+"} == 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Channel {{ $labels.platform }} sync failing"

      - alert: HighSyncLatency
        expr: |
          histogram_quantile(0.99, rate(pms_sync_latency_seconds_bucket[5m])) > 60
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Sync latency p99 above 60s"

      - alert: QueueBacklog
        expr: pms_celery_queue_depth > 1000
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Task queue backlog growing"
```

## Consequences

### Positive

- Comprehensive visibility across all system components
- Fast issue detection and debugging
- Business metrics for decision making
- Reasonable cost with managed services
- OpenTelemetry ensures vendor flexibility

### Negative

- Multiple tools to learn (Sentry + Grafana)
- Some setup complexity
- Need to manage alert fatigue

### Costs

| Service | Free Tier | Expected Monthly Cost |
|---------|-----------|----------------------|
| Sentry | 5K errors/mo | $0-26 (Team) |
| Grafana Cloud | 50GB logs, 10K metrics | $0-49 |
| **Total** | | **$0-75/month** |

## References

- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Sentry FastAPI Integration](https://docs.sentry.io/platforms/python/integrations/fastapi/)
- [Grafana Cloud](https://grafana.com/products/cloud/)
- [structlog](https://www.structlog.org/)
