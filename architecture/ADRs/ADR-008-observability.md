# ADR-008: Observability — Sentry + Prometheus + structlog

**Status:** Accepted (teilweise implementiert)
**Datum:** 2025-12-21

---

## Entscheidung

**Sentry** fuer Error Tracking, **Prometheus** fuer Metriken, **structlog** fuer Logging.
OpenTelemetry ist installiert aber noch nicht aktiviert.

## Ist-Stand

### Sentry (Error Tracking) — AKTIV

**Konfiguration:** via Env-Vars
- `SENTRY_DSN` — Project DSN
- `SENTRY_ENVIRONMENT` — Environment (default: "development")
- `SENTRY_TRACES_SAMPLE_RATE` — Sampling (default: 0.1 = 10%)

**Integration:** FastAPI + Celery
**Headers:** `baggage`, `sentry-trace`, `traceparent`, `tracestate` werden durchgereicht

### Prometheus (Metriken) — AKTIV

**Endpoint:** `GET /metrics`
**Datei:** `app/core/metrics.py`

| Metrik | Typ | Labels |
|--------|-----|--------|
| `pms_http_requests_total` | Counter | method, endpoint, status_code |
| `pms_http_request_duration_seconds` | Histogram | method, endpoint |
| `pms_bookings_created_total` | Counter | source, agency_id |
| `pms_active_agencies` | Gauge | — |
| `pms_active_users` | Gauge | — |
| `pms_db_pool_size` | Gauge | — |
| `pms_db_pool_free` | Gauge | — |

### structlog (Logging) — AKTIV

**Datei:** `app/core/logging_config.py`

- JSON-Format in Production
- Colored Console in Development
- Integriert mit stdlib logging via `ProcessorFormatter`
- Setup via `setup_logging()` in `main.py`

### OpenTelemetry — INSTALLIERT, NICHT AKTIV

Installierte Packages:
- `opentelemetry-api==1.22.0`
- `opentelemetry-sdk==1.22.0`
- `opentelemetry-instrumentation-fastapi==0.43b0`

**Status:** Libraries vorhanden, aber keine Initialisierung in `main.py`.
Kann bei Bedarf aktiviert werden (Grafana Tempo als Backend geplant).

## Was NICHT implementiert ist

- Kein Grafana Cloud (keine Konfiguration vorhanden)
- Kein OpenTelemetry Tracing (nur installiert)
- Keine Grafana Dashboards
- Keine Alerting Rules
- Kein Flower (Celery Monitoring)

## Health-Checks

**Endpoint:** `GET /health`

Prueft:
- Database-Verbindung (asyncpg)
- Redis-Verbindung
- Celery-Worker (optional, via `ENABLE_CELERY_HEALTHCHECK`)

**Endpoint:** `GET /api/v1/ops/version`

Liefert:
- App-Version
- Source Commit (via `SOURCE_COMMIT` Env-Var)
- Python-Version
- Uptime
