# 35 - Web Vitals Performance Monitoring

**Erstellt:** 2026-02-25
**Status:** Produktiv

---

## Übersicht

Web Vitals Monitoring erfasst automatisch Core Web Vitals (LCP, FCP, CLS, FID, INP, TTFB) von Public Websites und zeigt diese im Admin Panel an.

---

## Architektur

```
┌─────────────────┐     sendBeacon      ┌─────────────────┐
│  Public Website │ ──────────────────► │  Frontend Proxy │
│  (WebVitals.tsx)│                     │  /api/internal/ │
└─────────────────┘                     │  analytics/vitals│
                                        └────────┬────────┘
                                                 │
                                                 ▼
┌─────────────────┐     GET /summary    ┌─────────────────┐
│   Admin Panel   │ ◄────────────────── │   Backend API   │
│  /ops/web-vitals│                     │  /api/v1/       │
└─────────────────┘                     │  analytics/vitals│
                                        └────────┬────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │    Supabase     │
                                        │  web_vitals_    │
                                        │    metrics      │
                                        └─────────────────┘
```

### Datenfluss (Erfassung)

1. `WebVitals.tsx` erfasst Metriken via `next/web-vitals`
2. Metriken werden via `sendBeacon` an `/api/internal/analytics/vitals` gesendet
3. Frontend Proxy löst `agency_id` via `/agency-by-domain` auf
4. Daten werden an Backend POST `/api/v1/analytics/vitals?agency_id=...` gesendet
5. Backend speichert in `web_vitals_metrics` Tabelle

### Datenfluss (Anzeige)

1. Admin Panel ruft GET `/api/v1/analytics/vitals/summary?period=24h` auf
2. Backend löst `agency_id` aus JWT oder `team_members` Tabelle auf
3. Aggregierte Daten werden zurückgegeben

---

## Endpoints

### POST `/api/v1/analytics/vitals` (Public)

Speichert einzelne Web Vital Metrik.

**Query Parameter:**
- `agency_id` (UUID, required): Agency für die Metrik

**Body:**
```json
{
  "name": "LCP",
  "value": 1234.56,
  "rating": "good",
  "delta": 100.0,
  "id": "v1-123456",
  "navigationType": "navigate",
  "path": "/unterkuenfte"
}
```

**Antwort:** `{"status": "ok"}` (immer 200/201, niemals Fehler)

### GET `/api/v1/analytics/vitals/summary` (Admin Only)

Aggregierte Web Vitals Übersicht.

**Query Parameter:**
- `period`: `24h` | `7d` | `30d` (default: `24h`)

**Header:**
- `Authorization: Bearer <JWT>`
- `x-agency-id` (optional): Explizite Agency-Auswahl

**Antwort:**
```json
{
  "period": "24h",
  "metrics": [
    {
      "metric_name": "LCP",
      "avg_value": 1234.56,
      "p75_value": 1500.0,
      "good_count": 80,
      "needs_improvement_count": 15,
      "poor_count": 5,
      "total_count": 100,
      "good_percent": 80.0
    }
  ],
  "top_slow_pages": [
    {"path": "/buchung", "metric": "LCP", "avg_value": 2000.0, "count": 10}
  ],
  "total_measurements": 500
}
```

---

## Datenbank

### Tabelle: `web_vitals_metrics`

```sql
CREATE TABLE web_vitals_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,
    metric_name VARCHAR(10) NOT NULL,  -- LCP, FCP, CLS, FID, INP, TTFB
    value DOUBLE PRECISION NOT NULL,
    rating VARCHAR(20),  -- good, needs-improvement, poor
    path TEXT,
    navigation_type VARCHAR(20),
    delta DOUBLE PRECISION,
    metric_id VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Auto-Cleanup Trigger

```sql
-- Löscht alte Einträge (>30 Tage) und limitiert auf 10.000 pro Agency
CREATE OR REPLACE FUNCTION cleanup_old_web_vitals()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM web_vitals_metrics
    WHERE agency_id = NEW.agency_id
    AND (
        created_at < NOW() - INTERVAL '30 days'
        OR id IN (
            SELECT id FROM web_vitals_metrics
            WHERE agency_id = NEW.agency_id
            ORDER BY created_at DESC
            OFFSET 10000
        )
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### RLS Policies

```sql
-- Public INSERT (für sendBeacon)
CREATE POLICY "web_vitals_metrics_insert_public"
ON web_vitals_metrics FOR INSERT
WITH CHECK (true);

-- SELECT nur für eigene Agency (über RLS)
CREATE POLICY "web_vitals_metrics_select"
ON web_vitals_metrics FOR SELECT
USING (true);  -- Backend verwendet Service Role
```

---

## Troubleshooting

### Problem: 500 "badly formed hexadecimal UUID string"

**Ursache:** JWT Token enthält kein `agency_id` Claim.

**Lösung:** Backend löst Agency aus `team_members` Tabelle auf (Auto-Pick).

**Code:**
```python
async def resolve_agency_id(request, current_user, db):
    # 1. x-agency-id Header prüfen
    # 2. JWT agency_id prüfen
    # 3. Auto-Pick aus team_members
    tenants = await db.fetch(
        "SELECT DISTINCT agency_id FROM team_members WHERE user_id = $1",
        UUID(user_id)
    )
    if len(tenants) == 1:
        return tenants[0]['agency_id']
```

### Problem: 0 Messungen trotz Daten in DB

**Ursache:** String vs UUID Vergleich in SQL Query.

**Prüfung:**
```sql
-- Welche Agencies haben Daten?
SELECT DISTINCT agency_id, COUNT(*) FROM web_vitals_metrics GROUP BY agency_id;
```

**Lösung:** `agency_id` vor Query zu UUID konvertieren.

### Problem: POST gibt 422 mit agency_id=None

**Ursache:** Hostname-zu-Agency Mapping fehlgeschlagen.

**Prüfung:**
```sql
-- Domain-Mapping prüfen
SELECT * FROM agency_domains WHERE domain = 'www.example.de';
```

**Lösung:** Domain in `agency_domains` Tabelle eintragen.

### Problem: asyncpg "invalid input for query argument"

**Ursache:** PostgreSQL INTERVAL benötigt `timedelta`, nicht String.

**Falsch:**
```python
await db.fetch("... WHERE created_at > NOW() - $1::interval", "24 hours")
```

**Richtig:**
```python
from datetime import timedelta
await db.fetch("... WHERE created_at > NOW() - $1::interval", timedelta(hours=24))
```

---

## Monitoring

### Logs prüfen

```bash
# Backend Logs (Coolify)
# Suche nach "Auto-picked agency" für erfolgreiche Requests
grep "Auto-picked agency" /var/log/pms-backend.log

# Suche nach Fehlern
grep "web_vital" /var/log/pms-backend.log | grep -i error
```

### Datenbank-Check

```sql
-- Anzahl Messungen pro Agency (letzte 24h)
SELECT
    a.name as agency_name,
    COUNT(*) as measurements
FROM web_vitals_metrics w
JOIN agencies a ON w.agency_id = a.id
WHERE w.created_at > NOW() - INTERVAL '24 hours'
GROUP BY a.name
ORDER BY measurements DESC;

-- Durchschnittliche Werte pro Metrik
SELECT
    metric_name,
    ROUND(AVG(value)::numeric, 2) as avg_value,
    COUNT(*) as count
FROM web_vitals_metrics
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY metric_name
ORDER BY metric_name;
```

---

## Konfiguration

### Umgebungsvariablen

Keine speziellen Umgebungsvariablen erforderlich. Nutzt Standard-DB-Verbindung.

### Frontend

WebVitals-Komponente ist in `Providers.tsx` eingebunden und läuft auf allen Seiten.

Um Web Vitals zu deaktivieren, `WebVitals` aus `Providers.tsx` entfernen:

```tsx
// frontend/app/components/Providers.tsx
// Zeile auskommentieren:
// <WebVitals />
```

---

## Metriken-Referenz

| Metrik | Name | Gut | Verbesserungsbedarf | Schlecht | Einheit |
|--------|------|-----|---------------------|----------|---------|
| LCP | Largest Contentful Paint | ≤2.5s | ≤4.0s | >4.0s | ms |
| FCP | First Contentful Paint | ≤1.8s | ≤3.0s | >3.0s | ms |
| CLS | Cumulative Layout Shift | ≤0.1 | ≤0.25 | >0.25 | - |
| FID | First Input Delay | ≤100ms | ≤300ms | >300ms | ms |
| INP | Interaction to Next Paint | ≤200ms | ≤500ms | >500ms | ms |
| TTFB | Time to First Byte | ≤800ms | ≤1800ms | >1800ms | ms |

---

## Verwandte Dokumentation

- [Google Web Vitals](https://web.dev/vitals/)
- [next/web-vitals](https://nextjs.org/docs/advanced-features/measuring-performance)
