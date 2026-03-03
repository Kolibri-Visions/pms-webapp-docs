# Rate Limiting Security

## Übersicht

Das PMS-Webapp verwendet ein zweistufiges Rate Limiting System:

1. **Primär: Redis-basiert** - Verteiltes Rate Limiting über alle Worker
2. **Fallback: In-Memory** - Per-Process Limiting bei Redis-Ausfall

## Architektur

```
Request → Redis verfügbar?
           ├─ Ja → Redis Rate Limiter
           └─ Nein → In-Memory Fallback
                      ↓
                   Rate Check
                      ↓
              Allowed/Blocked (429)
```

## Konfiguration

### Umgebungsvariablen

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `PUBLIC_ANTI_ABUSE_ENABLED` | `true` | Public Rate Limiting aktivieren |
| `PUBLIC_RATE_LIMIT_ENABLED` | `true` | Rate Limiting für /api/v1/public/* |
| `PUBLIC_RATE_LIMIT_REDIS_URL` | - | Redis URL (Fallback: REDIS_URL) |
| `PUBLIC_RATE_LIMIT_WINDOW_SECONDS` | `60` | Zeitfenster in Sekunden |
| `PUBLIC_RATE_LIMIT_PING_MAX` | `60` | Max Requests für /ping |
| `PUBLIC_RATE_LIMIT_AVAIL_MAX` | `30` | Max Requests für /availability |
| `PUBLIC_RATE_LIMIT_BOOKING_MAX` | `10` | Max Requests für /booking-requests |
| `AUTH_RATE_LIMIT_ENABLED` | `true` | Auth Rate Limiting aktivieren |
| `AUTH_RATE_LIMIT_MAX_REQUESTS` | `100` | Max Requests pro User |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Zeitfenster in Sekunden |

## In-Memory Fallback

### Wann aktiv?

Der In-Memory Fallback wird automatisch aktiviert wenn:
- Redis nicht erreichbar ist
- Redis-Operationen fehlschlagen
- Connection Pool erschöpft ist

### Einschränkungen

- **Per-Process:** Limits gelten pro Worker-Prozess
- **Nicht persistent:** Bei Restart werden Limits zurückgesetzt
- **Kein Cluster-Sharing:** Worker teilen keine Limits

### Erkennung

Der Fallback-Modus ist erkennbar am Response Header:
```
X-RateLimit-Fallback: memory
```

### Monitoring

Logs bei Fallback-Aktivierung:
```
WARNING: In-memory rate limiter fallback ACTIVATED (Redis unavailable)
```

Bei Recovery:
```
INFO: In-memory rate limiter fallback DEACTIVATED (Redis recovered)
```

## Response Headers

Alle Rate-Limited Endpoints setzen diese Headers:

| Header | Beschreibung |
|--------|--------------|
| `X-RateLimit-Limit` | Max erlaubte Requests |
| `X-RateLimit-Remaining` | Verbleibende Requests |
| `X-RateLimit-Window` | Zeitfenster in Sekunden |
| `X-RateLimit-Fallback` | `memory` wenn Fallback aktiv |
| `Retry-After` | Sekunden bis Reset (nur bei 429) |

## Troubleshooting

### Rate Limiter greift nicht

1. Prüfen ob Feature aktiviert:
   ```bash
   curl -I https://api.example.com/api/v1/public/ping | grep X-RateLimit
   ```

2. Prüfen ob Redis verbunden:
   ```bash
   # In Coolify Terminal (pms-backend)
   python -c "from app.core.config import settings; print(settings.redis_url)"
   ```

### Zu viele 429 Fehler

1. Limits erhöhen (temporär):
   ```bash
   PUBLIC_RATE_LIMIT_AVAIL_MAX=100
   ```

2. Oder spezifische IPs whitelisten (Backend-Konfiguration)

### Fallback dauerhaft aktiv

1. Redis-Verbindung prüfen:
   ```bash
   redis-cli -u $REDIS_URL ping
   ```

2. Redis-Logs prüfen:
   ```bash
   docker logs pms-redis 2>&1 | tail -50
   ```

## Smoke Auth Bypass

### Aktivierung/Deaktivierung

Der Smoke Test Auth Bypass für automatisierte Tests ist **standardmäßig deaktiviert** (sicher für Production).

```bash
# Default: Deaktiviert (sicher für Production)
# Keine Variable setzen = deaktiviert

# Für Dev/Staging aktivieren (opt-in)
SMOKE_AUTH_BYPASS_ENABLED=true

# Explizit deaktivieren
SMOKE_AUTH_BYPASS_ENABLED=false
```

### Funktionsweise

Wenn aktiviert (`SMOKE_AUTH_BYPASS_ENABLED=true`), erlaubt der Bypass:
- GET/HEAD Requests auf Admin-Routen
- Mit `x-pms-smoke: 1` Header
- Und gültigem `Authorization: Bearer <token>` Header
- Token wird gegen Supabase validiert

### Security

**Default (kein Env-Var):** Deaktiviert ✅

Der Bypass ist für CI/CD-Smoke-Tests gedacht. In Production bleibt er deaktiviert, da:
- Token-Cookies sind nicht httpOnly (für Client lesbar)
- Keine IP-Whitelist implementiert
- Erhöhte Angriffsfläche

**Änderung 2026-03-03:** Default von "aktiviert" auf "deaktiviert" geändert (M-01 Security Fix).

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `backend/app/core/public_anti_abuse.py` | Public API Rate Limiting |
| `backend/app/core/auth_rate_limit.py` | Authenticated API Rate Limiting |
| `backend/app/core/memory_rate_limit.py` | In-Memory Fallback Limiter |
| `frontend/middleware.ts` | Smoke Auth Bypass Logic |
