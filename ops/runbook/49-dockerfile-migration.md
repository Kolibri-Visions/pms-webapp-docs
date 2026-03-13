# 49 — Nixpacks → Dockerfile Migration

**Datum:** 2026-03-12 bis 2026-03-13
**Status:** ABGESCHLOSSEN
**Betrifft:** Alle 4 Coolify-Services (Backend, Worker, Admin-Frontend, Public-Website)

---

## Überblick

Migration aller Services von Nixpacks (Coolify Auto-Detection) auf eigene Multi-Stage Dockerfiles.

**Vorteile:**
- Docker-native HEALTHCHECK (plattformunabhängig)
- Kleinere Images (~200MB statt ~800MB+ mit Nixpacks)
- Volle Kontrolle, reproduzierbare Builds
- Kein Node-Version Workaround mehr nötig

---

## Dateien

| Datei | Beschreibung |
|-------|-------------|
| `frontend/Dockerfile` | Multi-Stage Build: deps → builder → runner (node:20-alpine) |
| `frontend/.dockerignore` | Optimierter Build-Context (node_modules, .next, Tests ausgeschlossen) |
| `frontend/next.config.js` | `output: "standalone"` — erzeugt `.next/standalone/server.js` |
| `backend/Dockerfile` | Python Backend mit `--start-period=60s` HEALTHCHECK |
| `backend/Dockerfile.worker` | Celery Worker |

---

## Coolify-Konfiguration (Endstand)

### pms-api-backend
- **Build Pack:** Dockerfile
- **Base Directory:** `/backend`
- **Dockerfile Location:** `/Dockerfile`
- **Port:** 8000
- **Custom Docker Options:** `--network bccg4gs4o4kgsowocw08wkw4`

### pms-admin-frontend
- **Build Pack:** Dockerfile
- **Base Directory:** `/frontend`
- **Dockerfile Location:** `/Dockerfile`
- **Port:** 3000

### public-website
- **Build Pack:** Dockerfile
- **Base Directory:** `/frontend`
- **Dockerfile Location:** `/Dockerfile`
- **Port:** 3000

### pms-worker-v2
- **Build Pack:** Dockerfile
- **Base Directory:** `/backend`
- **Dockerfile Location:** `/Dockerfile.worker`
- **Port:** 8000
- **Custom Docker Options:** `--network bccg4gs4o4kgsowocw08wkw4`

---

## Probleme & Lösungen (Chronologisch)

### Problem 1: Geister-Container nach Umbenennung

**Symptom:** Nach Umbenennung von `pms-backend` → `pms-api-backend` in Coolify blockierten alte Container die Ports.

**Root Cause:** Coolify erstellt bei Umbenennung neue Container, stoppt die alten aber NICHT.

**Fix:**
```bash
docker stop pms-backend pms-admin && docker rm pms-backend pms-admin
```

**Lesson Learned:** NIEMALS Services in Coolify umbenennen während sie laufen!

---

### Problem 2: Coolify UI-Healthcheck schlägt fehl

**Symptom:** Container als "unhealthy" markiert → Traefik zeigt "no available server".

**Root Cause:** Coolify UI-Healthcheck nutzt `curl` — nicht vorhanden in `node:20-alpine` Images.

**Fix:** Coolify UI-Healthcheck für alle Services **deaktivieren**. Stattdessen Docker HEALTHCHECK im Dockerfile verwenden (nutzt `wget` statt `curl`).

---

### Problem 3: Backend nicht im Supabase-Netzwerk

**Symptom:** `gaierror: [Errno -3] Temporary failure in name resolution` bei `host=supabase-db`.

**Root Cause:** `--network` Custom Docker Option in Coolify ist unzuverlässig bei Dockerfile-Builds. Nach Redeploy ist der Container manchmal nicht im Supabase-Netzwerk.

**Fix (nach jedem Backend-Redeploy prüfen!):**
```bash
# Prüfen ob Backend im Supabase-Netzwerk ist
docker inspect pms-api-backend --format '{{json .NetworkSettings.Networks}}' | python3 -m json.tool | grep bccg4gs4o4kgsowocw08wkw4

# Falls nicht: manuell andocken
docker network connect bccg4gs4o4kgsowocw08wkw4 pms-api-backend
```

**Supabase-Netzwerk-Daten:**
- Netzwerk-ID: `bccg4gs4o4kgsowocw08wkw4`
- DB-Host: `supabase-db`
- DB-IP: `10.0.2.3`

**⚠️ ACHTUNG:** Dieser Fix überlebt keinen Redeploy! Nach JEDEM Backend-Redeploy prüfen!

---

### Problem 4: HEALTHCHECK "Connection refused" (localhost → IPv6)

**Symptom:** Docker HEALTHCHECK meldet dauerhaft "Connection refused", obwohl `wget http://127.0.0.1:3000/` funktioniert.

**Root Cause:** Alpine Linux resolves `localhost` zu `::1` (IPv6 Loopback). Next.js Standalone hört aber nur auf IPv4 (`0.0.0.0:3000`). Ergebnis: `wget http://localhost:3000/` → versucht IPv6 → Connection refused.

**Beweis:**
```bash
# Funktioniert NICHT (IPv6):
docker exec pms-admin-frontend wget -qO- http://localhost:3000/ 2>&1
# → "Connection refused"

# Funktioniert (IPv4):
docker exec pms-admin-frontend wget -qO- http://127.0.0.1:3000/api/ops/version 2>&1
# → {"service":"pms-admin","source_commit":"..."}
```

**Fix:** Im Dockerfile IMMER `127.0.0.1` statt `localhost` verwenden:
```dockerfile
# FALSCH:
HEALTHCHECK CMD wget --spider http://localhost:3000/ || exit 1

# RICHTIG:
HEALTHCHECK CMD wget -qO /dev/null http://127.0.0.1:3000/api/ops/version || exit 1
```

---

### Problem 5: HEALTHCHECK --spider schlägt fehl (HEAD vs GET)

**Symptom:** `wget --spider` bekommt Fehler, obwohl der Endpoint mit normalem GET funktioniert.

**Root Cause:** `wget --spider` sendet HEAD-Request. Next.js Standalone-Server beantwortet HEAD-Requests für API-Routes nicht korrekt.

**Fix:** Statt `--spider` normalen GET verwenden und Output verwerfen:
```dockerfile
# FALSCH:
HEALTHCHECK CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3000/api/ops/version || exit 1

# RICHTIG:
HEALTHCHECK CMD wget --no-verbose --tries=1 -qO /dev/null http://127.0.0.1:3000/api/ops/version || exit 1
```

---

### Problem 6: Root-Path `/` gibt 404 zurück

**Symptom:** HEALTHCHECK auf `http://127.0.0.1:3000/` bekommt 404 → Container bleibt unhealthy.

**Root Cause:** Next.js Middleware redirected `/` auf `/login` oder `/dashboard`. Im Standalone-Modus gibt der Root-Path 404 zurück statt Redirect.

**Fix:** HEALTHCHECK auf `/api/ops/version` umstellen (gibt immer 200 zurück):
```dockerfile
HEALTHCHECK CMD wget -qO /dev/null http://127.0.0.1:3000/api/ops/version || exit 1
```

---

## Finaler HEALTHCHECK (Frontend)

```dockerfile
# Health check — curl not available in alpine, use wget
# - 127.0.0.1 statt localhost (Alpine IPv6-Problem)
# - -qO /dev/null statt --spider (HEAD vs GET)
# - /api/ops/version statt / (404 vs 200)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD wget --no-verbose --tries=1 -qO /dev/null http://127.0.0.1:3000/api/ops/version || exit 1
```

---

## Diagnose-Befehle

```bash
# Container-Status + Health prüfen
docker inspect pms-admin-frontend --format '{{.State.Status}} / {{.State.Health.Status}}'

# Health-Log mit Details (zeigt letzte 5 Checks)
docker inspect pms-admin-frontend --format '{{json .State.Health}}' | python3 -m json.tool

# Manuell Endpoint testen (im Container)
docker exec pms-admin-frontend wget -qO- http://127.0.0.1:3000/api/ops/version 2>&1

# Offene Ports im Container prüfen (ohne netstat)
docker exec pms-admin-frontend cat /proc/net/tcp
# Port 0BB8 = 3000 (hex → dezimal)

# Netzwerk-Zugehörigkeit prüfen
docker inspect pms-admin-frontend --format '{{json .NetworkSettings.Networks}}' | python3 -m json.tool

# Supabase-Netzwerk andocken (Backend/Worker)
docker network connect bccg4gs4o4kgsowocw08wkw4 pms-api-backend

# Alle Container im Coolify-Netzwerk auflisten
docker network inspect coolify --format '{{range .Containers}}{{.Name}} {{end}}'
```

---

## Checkliste: Nach Frontend-Redeploy

- [ ] Coolify zeigt "Running (healthy)"
- [ ] `docker inspect ... '{{.State.Health.Status}}'` → `healthy`
- [ ] Website im Browser erreichbar (kein "no available server")

## Checkliste: Nach Backend-Redeploy

- [ ] Coolify zeigt "Running (healthy)"
- [ ] `docker inspect pms-api-backend ...` → `healthy`
- [ ] **Supabase-Netzwerk prüfen:**
  ```bash
  docker inspect pms-api-backend --format '{{json .NetworkSettings.Networks}}' | grep bccg4gs4o4kgsowocw08wkw4
  ```
- [ ] Falls fehlt: `docker network connect bccg4gs4o4kgsowocw08wkw4 pms-api-backend`
- [ ] API erreichbar: `curl https://api.fewo.kolibri-visions.de/health`

---

## Relevante Commits

| Commit | Beschreibung |
|--------|-------------|
| `35d3d036` | Frontend Dockerfile + .dockerignore erstellt |
| `25a653bf` | Fix: scripts/ in Docker Build-Context einbinden |
| `ead1badd` | Fix: fehlende public/ Directory behandeln |
| `21cde64d` | Revert: standalone output entfernt (Rollback) |
| `324db127` | Re-enable: standalone output nach Fixes |
| `d9011f58` | Fix: /api/ops/version statt / für HEALTHCHECK |
| `9c1ff433` | Fix: GET (-qO) statt HEAD (--spider) |
| `4231ecc3` | Fix: 127.0.0.1 statt localhost (IPv6-Problem) |
