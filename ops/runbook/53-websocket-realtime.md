# 53 — WebSocket Realtime Events

## Übersicht

WebSocket-basierte Echtzeit-Events für die Admin-UI. Ersetzt Polling für:
- Buchungen (CRUD + Statusänderungen)
- Buchungsanfragen (Review/Approve/Decline)
- Verfügbarkeit (Sperren erstellen/ändern/löschen)
- Branding-Änderungen
- Berechtigungsänderungen

## Architektur

```
Client ←WebSocket→ Backend ←Redis Pub/Sub→ Backend (Mutation)
```

- **Channel-Pattern:** `pms:agency:{agency_id}:events`
- **Auth:** JWT als Query-Parameter (`/ws?token=...`)
- **Heartbeat:** Client ping alle 30s, Server-Timeout 90s
- **Reconnect:** Exponential Backoff (1s → 30s, max 50 Versuche)

## Connection-Limits

| Limit | Wert | Verhalten |
|-------|------|-----------|
| Pro User | 5 | Älteste Connection wird geschlossen (Code 4008) |
| Pro Agency | 50 | Neue Connection wird abgelehnt (Code 4009) |
| Global | 500 | Neue Connection wird abgelehnt (Code 4010) |

## Event-Throttling

Max 10 Events/Sekunde pro Agency. Überschüssige Events werden verworfen (geloggt als `realtime_event_throttled`).

## Graceful Degradation

Bei Redis-Ausfall:
1. Client erhält `{"type": "degraded", "reason": "event_service_unavailable"}`
2. Listener wartet 5s, dann Retry
3. API-Mutations funktionieren weiter (fire-and-forget)

## Prometheus Metriken

| Metrik | Typ | Beschreibung |
|--------|-----|--------------|
| `pms_ws_connections_total` | Gauge | Aktive WS-Connections |
| `pms_ws_connections_by_agency` | Gauge | Connections pro Agency |
| `pms_ws_messages_sent_total` | Counter | Gesendete Events (nach Typ) |
| `pms_ws_connections_rejected_total` | Counter | Abgelehnte Connections |
| `pms_ws_events_throttled_total` | Counter | Gedrosselte Events |

## Debugging

```bash
# WebSocket-Verbindung testen
wscat -c "wss://api.example.com/ws?token=JWT_TOKEN"

# Redis Pub/Sub manuell testen
redis-cli SUBSCRIBE "pms:agency:AGENCY_ID:events"

# Aktive Connections prüfen (Prometheus)
curl -s http://localhost:8000/metrics | grep pms_ws_

# Logs filtern
grep "ws_" /var/log/pms-backend/*.log
```

## Dateien

**Backend:**
- `app/core/realtime.py` — Event-Publishing + Throttling
- `app/core/ws_manager.py` — Connection Manager
- `app/api/routes/websocket.py` — WS-Endpoint
- `app/modules/websocket.py` — Modul-Registrierung

**Frontend:**
- `app/lib/ws-client.ts` — WebSocket-Client
- `app/lib/contexts/RealtimeContext.tsx` — Provider + Hooks
- `app/hooks/useBookingRealtime.ts` — Booking-Events
- `app/hooks/useAvailabilityRealtime.ts` — Availability-Events
