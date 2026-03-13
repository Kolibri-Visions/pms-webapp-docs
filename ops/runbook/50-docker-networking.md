# 50 — Docker Networking: Coolify + Self-hosted Supabase

**Datum:** 2026-03-13
**Status:** GELÖST (v2 Bridge-Ansatz)
**Betrifft:** Alle PMS-Services + Supabase-DB

---

## Das Problem

PMS-Webapp läuft auf einem Server mit **Coolify** als Deployment-Plattform und **Self-hosted Supabase** als Datenbank. Coolify erstellt für jede Ressource ein eigenes Docker-Netzwerk:

```
┌─────────────────────────────┐   ┌────────────────────────────────────┐
│      coolify (Netzwerk)     │   │   bccg4gs... (Supabase-Netzwerk)  │
│                             │   │                                    │
│  pms-api-backend      :8000 │   │  supabase-db             :5432    │
│  pms-worker-v2              │   │  supabase-auth                    │
│  pms-admin-frontend   :3000 │   │  supabase-storage                 │
│  public-website       :3000 │   │  supabase-rest                    │
│  coolify-redis        :6379 │   │  supabase-kong                    │
│  coolify-proxy (Traefik)    │   │  supabase-studio                  │
│                             │   │  supabase-analytics               │
│                             │   │  supabase-meta                    │
│                             │   │  supabase-minio                   │
│                             │   │  supabase-vector                  │
│                             │   │  supabase-edge-functions          │
│                             │   │  supabase-supavisor               │
└─────────────────────────────┘   └────────────────────────────────────┘
         ❌ Keine Verbindung zwischen den Netzwerken!
```

**Ergebnis:** Backend und Worker können `supabase-db` nicht per DNS auflösen → `gaierror: Temporary failure in name resolution`.

---

## Warum hat Supabase ein eigenes Netzwerk?

**Coolify-Designentscheidung**, keine technische Notwendigkeit:

- **Applications** (unsere 4 PMS-Container) → landen im `coolify`-Netzwerk
- **Services** (Supabase-Stack mit ~10 Containern) → bekommen ein eigenes isoliertes Netzwerk

Das ist gedacht für Multi-Tenant-Setups (viele Kunden auf einem Server), wo sich Projekte nicht sehen sollen. Bei uns läuft **alles für ein Projekt** — die Isolation ist hinderlich.

**Kann man Supabase als Application statt Service anlegen?**
Nein. In Coolify ist ein "Service" ein Multi-Container-Stack (Supabase hat ~10 Container). Eine "Application" ist immer ein einzelner Container.

---

## Lösungsansätze (Chronologie)

### v1: PMS-Container → Supabase-Netzwerk (2025-12 bis 2026-03-13)

```
Ansatz:  Backend + Worker manuell ins Supabase-Netzwerk hängen
Script:  pms_ensure_supabase_net.sh (Cron alle 5 Min)
Befehl:  docker network connect bccg4gs... pms-api-backend
```

**Problem:** Bei **jedem** Backend-Redeploy (mehrmals pro Woche) wurde der Container neu erstellt → Netzwerk-Verbindung weg → bis zu 5 Min Downtime bis Cron eingreift.

**Zusätzliche Probleme:**
- Coolify's `--network` Custom Docker Option wird komplett ignoriert
- Coolify's Post-deployment Command läuft **im Container** (kein `docker` verfügbar)
- Container-Name wurde umbenannt (`pms-backend` → `pms-api-backend`), Script lief ins Leere

### v2: Supabase-DB → coolify-Netzwerk (2026-03-13, AKTUELL)

```
Ansatz:  Supabase-DB ins coolify-Netzwerk holen (mit DNS-Alias)
Script:  pms_ensure_supabase_net.sh (Cron alle 5 Min)
Befehl:  docker network connect --alias supabase-db coolify supabase-db-bccg4gs...
```

```
┌──────────────────────────────────────────────┐   ┌─────────────────────┐
│              coolify (Netzwerk)               │   │  Supabase-Netzwerk  │
│                                              │   │                     │
│  pms-api-backend      :8000                  │   │  supabase-auth      │
│  pms-worker-v2                               │   │  supabase-storage   │
│  pms-admin-frontend   :3000                  │   │  supabase-rest      │
│  public-website       :3000                  │   │  supabase-kong      │
│  coolify-redis        :6379                  │   │  ...                │
│  coolify-proxy (Traefik)                     │   │                     │
│                                              │   │                     │
│  supabase-db ←── (Alias, Bridge) ──→ :5432   │   │  supabase-db :5432  │
│                                              │   │                     │
└──────────────────────────────────────────────┘   └─────────────────────┘
         ✅ DB erreichbar über "supabase-db" Alias!
```

**Warum das besser ist:**

| | v1 (Alt) | v2 (Neu) |
|--|----------|----------|
| Was wird verbunden? | PMS-Container → Supabase-Netz | Supabase-DB → coolify-Netz |
| Bricht bei... | Jedem Backend-Redeploy (häufig) | Supabase-Redeploy (selten) |
| Betroffene Container | 2 (Backend + Worker) | 1 (nur DB) |
| DNS-Änderung nötig? | Nein | Nein (Alias = "supabase-db") |
| Max. Downtime | ~5 Min nach jedem Deploy | ~5 Min nach seltenem Supabase-Update |

---

## Aktuelle Konfiguration

### Cron-Job auf dem Server

```bash
# Aktiver Cron-Eintrag (crontab -l)
*/5 * * * * /data/repos/pms-webapp/backend/scripts/ops/pms_ensure_supabase_net.sh >> /var/log/pms/ensure_supabase_net.log 2>&1
```

### Script-Konfiguration

```bash
# In pms_ensure_supabase_net.sh
COOLIFY_NETWORK="coolify"
SUPABASE_DB_CONTAINER="supabase-db-bccg4gs4o4kgsowocw08wkw4"
DB_ALIAS="supabase-db"
```

### Log-Datei

```bash
tail -20 /var/log/pms/ensure_supabase_net.log
```

---

## Netzwerk-Daten (Referenz)

| Netzwerk | Name/ID | Zweck |
|----------|---------|-------|
| coolify | `coolify` | Alle PMS-Apps + Traefik + Redis |
| Supabase | `bccg4gs4o4kgsowocw08wkw4` | Interner Supabase-Stack |

### Supabase-Container (Stand 2026-03-13)

```
supabase-db-bccg4gs4o4kgsowocw08wkw4          ← PostgreSQL (der wichtige!)
supabase-auth-bccg4gs4o4kgsowocw08wkw4         ← GoTrue Auth Server
supabase-storage-bccg4gs4o4kgsowocw08wkw4      ← Storage API
supabase-rest-bccg4gs4o4kgsowocw08wkw4         ← PostgREST
supabase-kong-bccg4gs4o4kgsowocw08wkw4         ← API Gateway
supabase-studio-bccg4gs4o4kgsowocw08wkw4       ← Dashboard UI
supabase-meta-bccg4gs4o4kgsowocw08wkw4         ← Metadata API
supabase-analytics-bccg4gs4o4kgsowocw08wkw4    ← Analytics
supabase-minio-bccg4gs4o4kgsowocw08wkw4        ← S3-kompatibler Storage
supabase-vector-bccg4gs4o4kgsowocw08wkw4       ← Vector/Embeddings
supabase-edge-functions-bccg4gs4o4kgsowocw08wkw4 ← Deno Edge Functions
supabase-supavisor-bccg4gs4o4kgsowocw08wkw4    ← Connection Pooler
```

### PMS-Container

```
pms-api-backend          ← FastAPI (Port 8000)
pms-worker-v2            ← Celery Worker
pms-admin-frontend       ← Next.js Admin (Port 3000)
public-website           ← Next.js Public (Port 3000)
```

---

## Diagnose-Befehle

```bash
# Welche Netzwerke hat die Supabase-DB?
docker inspect supabase-db-bccg4gs4o4kgsowocw08wkw4 --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
# Erwartung: bccg4gs4o4kgsowocw08wkw4 coolify

# Kann Backend die DB per DNS finden?
docker exec pms-api-backend python -c "import socket; print(socket.getaddrinfo('supabase-db', 5432))"
# Erwartung: IP-Adresse zurück (z.B. 10.0.1.12)

# Welche Netzwerke hat das Backend?
docker inspect pms-api-backend --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
# Erwartung: coolify (NUR coolify — kein Supabase-Netzwerk mehr nötig)

# Manuell DB ins coolify-Netzwerk bringen
docker network connect --alias supabase-db coolify supabase-db-bccg4gs4o4kgsowocw08wkw4

# Manuell DB aus coolify-Netzwerk entfernen (Rollback)
docker network disconnect coolify supabase-db-bccg4gs4o4kgsowocw08wkw4

# Cron-Job Log prüfen
tail -30 /var/log/pms/ensure_supabase_net.log

# Cron-Job Status prüfen
crontab -l | grep supabase

# Script manuell ausführen
/data/repos/pms-webapp/backend/scripts/ops/pms_ensure_supabase_net.sh
```

---

## Coolify-Erkenntnisse (Lessons Learned)

### Was Coolify NICHT kann

1. **`--network` Custom Docker Option** wird bei Dockerfile-Builds komplett ignoriert
   - Steht in der Coolify UI, wird aber NICHT in die generierte docker-compose übernommen
   - Beweis: `cat /data/coolify/applications/<id>/docker-compose.yaml` → kein Supabase-Netzwerk

2. **Post-deployment Commands** laufen **im Container**, nicht auf dem Host
   - `docker network connect ...` im Post-deployment → Fehler (docker CLI nicht verfügbar)
   - Nur Befehle die INNERHALB des Containers laufen (z.B. `php artisan migrate`) funktionieren

3. **Services und Applications** haben getrennte Netzwerke
   - Keine UI-Option um sie zusammenzuführen
   - Docker-intern mit `docker network connect` lösbar, aber nicht persistent

### Was Coolify gut kann

1. Auto-Deploy via GitHub Webhook
2. Rollback auf vorherige Deployments
3. Environment-Variable Management per UI
4. TLS-Zertifikate via Traefik + Let's Encrypt
5. Container-Logs in der UI

---

## Entscheidungsmatrix: Langfristige Optionen

| Option | Aufwand | Netzwerk-Problem | Kosten | Vendor Lock-in |
|--------|---------|------------------|--------|----------------|
| **Coolify + Cron-Job (aktuell)** | Keiner | Gelöst (v2 Bridge) | ~0€ (VPS) | Coolify |
| **docker-compose.prod.yml** | 1 Tag | Permanent gelöst | ~0€ (VPS) | Keiner |
| **Supabase Cloud** | 1-2 Tage | Nicht existent | ~25€/Monat | Supabase |
| **Managed PostgreSQL** | 3-5 Tage | Nicht existent | ~15€/Monat | Umbau nötig |

### Empfehlung

1. **Kurzfristig:** v2 Bridge-Ansatz (Cron-Job, funktioniert)
2. **Mittelfristig:** Coolify → docker-compose.prod.yml (volle Kontrolle)
3. **Langfristig:** Supabase Cloud evaluieren (wenn Datenschutz es erlaubt)

---

## Relevante Dateien

| Datei | Zweck |
|-------|-------|
| `backend/scripts/ops/pms_ensure_supabase_net.sh` | Cron-Script (v2 Bridge) |
| `docker-compose.prod.yml` | Production Compose (Alternative zu Coolify) |
| `DEPLOYMENT.md` | Deployment-Anleitung |
| `backend/docs/ops/runbook/49-dockerfile-migration.md` | Dockerfile-Migration |
| `backend/docs/ops/runbook/02-database.md` | DB-Connectivity Runbook |

---

## Änderungshistorie

| Datum | Änderung |
|-------|----------|
| 2025-12-29 | v1: Script erstellt (`pms-backend` → Supabase-Netzwerk) |
| 2026-03-13 | Container umbenannt: `pms-backend` → `pms-api-backend` |
| 2026-03-13 | v2: Strategy-Wechsel zu Bridge-Ansatz (DB → coolify-Netzwerk) |
| 2026-03-13 | Dokumentation erstellt (dieses Dokument) |
