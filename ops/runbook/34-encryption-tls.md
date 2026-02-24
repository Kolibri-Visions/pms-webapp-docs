# Encryption in Transit & at Rest

**When to use:** TLS/SSL Konfiguration, Verschlüsselungsprobleme, Security Audits.

---

## Table of Contents

- [Übersicht](#übersicht)
- [Encryption in Transit](#encryption-in-transit)
  - [HTTPS/TLS (Frontend)](#httpstls-frontend)
  - [PostgreSQL SSL](#postgresql-ssl)
  - [Redis TLS](#redis-tls)
- [Encryption at Rest](#encryption-at-rest)
  - [PostgreSQL (Supabase)](#postgresql-supabase)
  - [OAuth Token Encryption](#oauth-token-encryption)
- [Konfiguration](#konfiguration)
- [Troubleshooting](#troubleshooting)

---

## Übersicht

| Bereich | Status | Protokoll |
|---------|--------|-----------|
| Frontend ↔ User | ✅ | HTTPS + HSTS |
| Frontend ↔ Backend | ✅ | HTTPS |
| Backend ↔ PostgreSQL | ✅ | SSL (konfigurierbar) |
| Backend ↔ Redis | ✅ | TLS (konfigurierbar) |
| OAuth Tokens (DB) | ✅ | Fernet (AES-128-CBC) |
| PostgreSQL Disk | ⚠️ | Host-Level (LUKS empfohlen) |

---

## Encryption in Transit

### HTTPS/TLS (Frontend)

**Status:** ✅ Aktiv

**HSTS Header** (`frontend/next.config.js`):
```javascript
{
  key: 'Strict-Transport-Security',
  value: 'max-age=31536000; includeSubDomains'
}
```

**Cookie Security** (`frontend/middleware.ts`):
```typescript
response.cookies.set('sb-access-token', token, {
  httpOnly: true,
  secure: !host.includes('localhost'),  // TLS in Production
  sameSite: 'lax',
});
```

**Verifikation:**
```bash
# HSTS Header prüfen
curl -sI https://admin.fewo.kolibri-visions.de | grep -i strict-transport
# Expected: strict-transport-security: max-age=31536000; includeSubDomains
```

---

### PostgreSQL SSL

**Status:** ✅ Konfigurierbar

**Konfiguration (.env):**
```bash
# Development (ohne SSL):
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

# Production (mit SSL - EMPFOHLEN):
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require

# Self-Hosted mit eigenem Zertifikat:
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=verify-full&sslrootcert=/path/to/ca.crt
```

**SSL-Modi:**

| Modus | Beschreibung | Empfehlung |
|-------|--------------|------------|
| `disable` | Kein SSL | ❌ Nie in Production |
| `allow` | SSL wenn Server es unterstützt | ⚠️ Unsicher |
| `prefer` | SSL bevorzugt, Fallback auf unverschlüsselt | ⚠️ Unsicher |
| `require` | SSL erzwungen, kein Zertifikat-Check | ✅ Minimum für Production |
| `verify-ca` | SSL + CA-Zertifikat validiert | ✅ Empfohlen |
| `verify-full` | SSL + CA + Hostname validiert | ✅ Maximum Sicherheit |

**Verifikation:**
```bash
# Prüfen ob SSL aktiv ist
docker exec pms-backend python -c "
from app.core.config import settings
print('SSL in URL:', 'ssl=' in settings.database_url or 'sslmode=' in settings.database_url)
"
```

---

### Redis TLS

**Status:** ✅ Konfigurierbar (seit 2026-02-25)

**Konfiguration (.env):**
```bash
# Development (ohne TLS):
REDIS_URL=redis://localhost:6379/0
REDIS_TLS_ENABLED=false

# Production (mit TLS - EMPFOHLEN):
REDIS_URL=rediss://:password@redis-host:6379/0
REDIS_TLS_ENABLED=true
REDIS_TLS_CERT_REQS=required  # none, optional, required
REDIS_TLS_CA_CERTS=           # Pfad zu CA-Zertifikat (optional)
```

**Wichtig:**
- `redis://` = unverschlüsselt
- `rediss://` = TLS (doppeltes 's')

**Code-Implementierung** (`backend/app/core/redis.py`):
```python
def _create_ssl_context() -> ssl.SSLContext | None:
    if not settings.redis_tls_enabled:
        return None

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    if settings.redis_tls_ca_certs:
        ssl_context.load_verify_locations(settings.redis_tls_ca_certs)

    return ssl_context
```

**Verifikation:**
```bash
# Prüfen ob TLS aktiv ist
docker logs pms-backend 2>&1 | grep -i "redis.*tls"
# Expected: "Redis connection pool created successfully (TLS enabled)"
```

**Celery Worker:**
Celery verwendet dieselbe Redis-URL. Für TLS:
```bash
CELERY_BROKER_URL=rediss://:password@redis-host:6379/0
CELERY_RESULT_BACKEND=rediss://:password@redis-host:6379/0
```

---

## Encryption at Rest

### PostgreSQL (Supabase)

**Self-Hosted Supabase:**
- Disk-Encryption ist **NICHT automatisch**
- Empfehlung: **LUKS/dm-crypt** auf Host-Ebene

**Prüfen ob LUKS aktiv:**
```bash
# Auf dem Host-Server
lsblk -o NAME,TYPE,FSTYPE,MOUNTPOINT,ENCRYPTED
# oder
dmsetup status | grep crypt
```

**LUKS aktivieren (falls nicht vorhanden):**
```bash
# ACHTUNG: Erfordert Neuformatierung der Partition!
# Backup VORHER erstellen!
cryptsetup luksFormat /dev/sdX
cryptsetup luksOpen /dev/sdX encrypted_data
mkfs.ext4 /dev/mapper/encrypted_data
```

### OAuth Token Encryption

**Status:** ✅ Aktiv (Fernet/AES-128-CBC)

**Datei:** `backend/app/core/encryption.py`

```python
from app.core.encryption import get_token_encryption

enc = get_token_encryption()
encrypted = enc.encrypt("oauth_access_token")  # AES-128-CBC + HMAC
decrypted = enc.decrypt(encrypted)
```

**Konfiguration:**
```bash
# 44 Zeichen Base64-encoded Fernet Key
ENCRYPTION_KEY=base64_encoded_32_byte_key_here_44chars
```

**Key generieren:**
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

---

## Konfiguration

### Minimale Production-Konfiguration

```bash
# .env (Production)

# PostgreSQL mit SSL
DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/pms?ssl=require

# Redis mit TLS
REDIS_URL=rediss://:password@redis-host:6379/0
REDIS_TLS_ENABLED=true
REDIS_TLS_CERT_REQS=required

# Celery mit TLS
CELERY_BROKER_URL=rediss://:password@redis-host:6379/0
CELERY_RESULT_BACKEND=rediss://:password@redis-host:6379/0

# OAuth Token Encryption
ENCRYPTION_KEY=your_44_char_fernet_key_here
```

### Empfohlene Production-Konfiguration (Maximum Security)

```bash
# PostgreSQL mit Zertifikat-Validierung
DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/pms?ssl=verify-full&sslrootcert=/etc/ssl/certs/db-ca.crt

# Redis mit CA-Zertifikat
REDIS_URL=rediss://:password@redis-host:6379/0
REDIS_TLS_ENABLED=true
REDIS_TLS_CERT_REQS=required
REDIS_TLS_CA_CERTS=/etc/ssl/certs/redis-ca.crt
```

---

## Troubleshooting

### PostgreSQL SSL-Fehler

**Symptom:** `SSL connection required but server does not support SSL`

**Ursache:** PostgreSQL-Server hat SSL nicht aktiviert.

**Lösung (Self-Hosted):**
```bash
# postgresql.conf
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
```

---

### Redis TLS-Fehler

**Symptom:** `Connection refused` oder `SSL: CERTIFICATE_VERIFY_FAILED`

**Prüfen:**
```bash
# TLS-Verbindung testen
openssl s_client -connect redis-host:6379 -tls1_2
```

**Lösung bei Zertifikatsfehler:**
```bash
# CA-Zertifikat angeben
REDIS_TLS_CA_CERTS=/path/to/ca.crt

# Oder Zertifikat-Prüfung deaktivieren (NUR für Debugging!)
REDIS_TLS_CERT_REQS=none
```

---

### Health Check mit TLS

```bash
# Backend Health (inkl. Redis + DB)
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq .
```

**Expected:**
```json
{
  "status": "up",
  "components": {
    "db": {"status": "up"},
    "redis": {"status": "up"},
    "celery": {"status": "up"}
  }
}
```

---

## Zusammenfassung

| Komponente | Verschlüsselung | Konfiguration |
|------------|-----------------|---------------|
| HTTPS | ✅ Automatisch | Traefik/Coolify |
| PostgreSQL SSL | ✅ Manuell | `?ssl=require` in DATABASE_URL |
| Redis TLS | ✅ Manuell | `REDIS_TLS_ENABLED=true` + `rediss://` |
| OAuth Tokens | ✅ Automatisch | `ENCRYPTION_KEY` setzen |
| Disk (Self-Hosted) | ⚠️ Host-Ebene | LUKS/dm-crypt |

---

*Last updated: 2026-02-25*
