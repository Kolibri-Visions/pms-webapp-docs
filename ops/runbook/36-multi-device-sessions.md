# 36. Multi-Device Session Tracking

**Erstellt:** 2026-02-26
**Status:** VERIFIED
**Scope:** Session-Verwaltung für mehrere Geräte

---

## 1. Übersicht

Das Multi-Device Session Tracking ermöglicht Benutzern, alle aktiven Sitzungen auf verschiedenen Geräten einzusehen und zu verwalten.

### Features

| Feature | Beschreibung |
|---------|--------------|
| Session-Liste | Alle aktiven Sessions auf `/profile/security` |
| Einzelne Session revoken | "Sitzung beenden" Button pro Session |
| Alle Sessions beenden | "Alle anderen Sitzungen beenden" Button |
| Automatischer Logout | Revoked Sessions werden bei nächstem Request erkannt |
| Local Logout | Abmelden betrifft nur aktuelles Gerät |

---

## 2. Architektur

### Datenmodell

```
┌─────────────────────────────────────────────────────────┐
│                    user_sessions                         │
├─────────────────────────────────────────────────────────┤
│ id              UUID PRIMARY KEY                         │
│ agency_id       UUID NOT NULL → agencies(id)            │
│ user_id         UUID NOT NULL                            │
│ device_type     TEXT ('Desktop', 'Mobile', 'Tablet')    │
│ browser         TEXT ('Chrome', 'Safari', 'Firefox')    │
│ os              TEXT ('macOS', 'iOS', 'Windows', etc.)  │
│ user_agent      TEXT (vollständiger UA-String)          │
│ ip_address      INET                                     │
│ created_at      TIMESTAMPTZ                              │
│ last_activity_at TIMESTAMPTZ                             │
│ ended_at        TIMESTAMPTZ (NULL = aktiv)              │
│ ended_by        TEXT ('user', 'revoked', 'new_login')   │
│ is_active       BOOLEAN GENERATED (ended_at IS NULL)    │
└─────────────────────────────────────────────────────────┘
```

### Komponenten

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Login Route   │────▶│  user_sessions   │◀────│  Sessions API   │
│ /auth/login     │     │     Tabelle      │     │ /api/.../sessions│
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       ▲                        │
        ▼                       │                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  pms_session_id │     │   Middleware     │     │  Security Page  │
│     Cookie      │────▶│ Session Check    │     │ /profile/security│
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## 3. Konfiguration

### Cookies

| Cookie | Wert | Flags |
|--------|------|-------|
| `pms_session_id` | UUID der Session | `httpOnly`, `secure`, `sameSite=strict`, `maxAge=7d` |

### Environment

Keine zusätzlichen Environment-Variablen erforderlich.

---

## 4. API Endpoints

### GET /api/internal/auth/sessions

Gibt alle aktiven Sessions des Benutzers zurück.

**Response:**
```json
{
  "sessions": [
    {
      "id": "uuid",
      "is_current": true,
      "browser": "Safari",
      "os": "macOS",
      "device": "Desktop",
      "ip_address": "77.0.191.220",
      "last_active": "2026-02-26T13:30:00Z",
      "created_at": "2026-02-26T10:00:00Z"
    }
  ],
  "current_session_id": "uuid"
}
```

### DELETE /api/internal/auth/sessions

Beendet eine oder alle Sessions.

**Body (einzelne Session):**
```json
{
  "session_id": "uuid"
}
```

**Body (alle Sessions):**
```json
{
  "all_others": true
}
```

---

## 5. Troubleshooting

### Problem: Session wird nicht als beendet markiert

**Symptom:** Nach Logout erscheint Session noch als aktiv.

**Ursache:** Client-Logout ging nicht über `/auth/logout`.

**Lösung:**
```typescript
// Korrekt: performLogout() redirected zu Server-Route
import { performLogout } from "@/app/lib/logout";
await performLogout();

// NICHT: Direkter signOut-Aufruf
// await supabase.auth.signOut(); // ← Aktualisiert user_sessions NICHT
```

### Problem: Revoked Session bleibt eingeloggt

**Symptom:** Nach Revoken von Desktop bleibt Mobile eingeloggt.

**Ursache:** Middleware-Check läuft nur bei Admin-Requests.

**Lösung:** Mobile muss eine Admin-Seite aufrufen (Navigation, Dashboard, etc.) um erkannt zu werden. Statische Assets triggern den Check nicht.

### Problem: iOS wird als macOS erkannt

**Symptom:** iPhone-Sessions zeigen "Safari auf macOS".

**Ursache:** iOS User-Agent enthält "Mac OS".

**Lösung:** User-Agent Parser prüft Mobile-Keywords VOR Desktop:
```typescript
// Korrekt (user-agent.ts):
if (userAgent.includes("iPhone")) { os = "iOS"; }
else if (userAgent.includes("Mac OS")) { os = "macOS"; }
```

---

## 6. Datenbank-Abfragen

### Alle aktiven Sessions eines Users

```sql
SELECT id, device_type, browser, os, ip_address, created_at, last_activity_at
FROM user_sessions
WHERE user_id = 'user-uuid'
  AND ended_at IS NULL
ORDER BY last_activity_at DESC;
```

### Session-Statistik pro Agency

```sql
SELECT
  COUNT(*) FILTER (WHERE ended_at IS NULL) AS active_sessions,
  COUNT(*) FILTER (WHERE ended_at IS NOT NULL) AS ended_sessions,
  COUNT(DISTINCT user_id) AS unique_users
FROM user_sessions
WHERE agency_id = 'agency-uuid';
```

### Verwaiste Sessions bereinigen (älter als 30 Tage)

```sql
UPDATE user_sessions
SET ended_at = NOW(), ended_by = 'expired'
WHERE ended_at IS NULL
  AND last_activity_at < NOW() - INTERVAL '30 days';
```

---

## 7. Security Considerations

### SECURITY DEFINER Funktionen

Die Funktionen `end_user_session()` und `end_all_user_sessions()` sind SECURITY DEFINER, um RLS zu umgehen. Sie validieren `auth.uid()` explizit:

```sql
IF auth.uid() IS NULL OR auth.uid() != p_user_id THEN
  RAISE EXCEPTION 'Unauthorized: user_id mismatch';
END IF;
```

### Rate Limiting (TODO)

Sessions API sollte Rate Limited werden:
- DELETE: max 10 req/min/user
- Siehe `PMS-Webapp-TODO.md`

### Cookie Security

- `httpOnly`: Verhindert XSS-Cookie-Theft
- `secure`: Nur über HTTPS
- `sameSite=strict`: CSRF-Schutz
- `maxAge=7d`: Automatische Expiration

---

## 8. Migrationen

| Migration | Beschreibung |
|-----------|--------------|
| `20260226100000_add_user_sessions.sql` | Tabelle + RLS + Indices |
| `20260226120000_fix_user_sessions_rls.sql` | SECURITY DEFINER Funktionen |
| `20260226140000_fix_session_functions_idor.sql` | auth.uid() Check hinzugefügt |

---

## 9. Dateien

| Datei | Beschreibung |
|-------|--------------|
| `frontend/app/lib/user-agent.ts` | User-Agent Parser |
| `frontend/app/lib/logout.ts` | Client-Logout Utility |
| `frontend/app/auth/login/route.ts` | Session-Erstellung |
| `frontend/app/auth/logout/route.ts` | Session-Beendigung |
| `frontend/app/api/internal/auth/sessions/route.ts` | Sessions API |
| `frontend/middleware.ts` | Revoked Session Detection |
| `frontend/app/profile/security/page.tsx` | UI |

---

*Zuletzt aktualisiert: 2026-02-26*
