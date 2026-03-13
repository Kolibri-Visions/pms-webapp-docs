# Eigene Auth (Phase 1 — Supabase-Abloesung)

**Datum:** 2026-03-13
**Status:** PROD-deployed, funktional

---

## Uebersicht

Phase 1 der Supabase-Abloesung: Eigene JWT-basierte Authentifizierung ersetzt Supabase GoTrue.
PostgREST + Supabase Storage bleiben vorerst bestehen (Phase 2+3).

## Architektur

```
Browser → pms_access_token Cookie → Next.js Middleware (JWT verify via jose)
                                   → Backend API (JWT verify via PyJWT)
                                   → PostgREST (service_role key, kein User-JWT!)
```

### Warum Proxy-Pattern in supabase-server.ts?

Unser JWT enthaelt `role: "admin"` (App-Rolle). PostgREST interpretiert das als PostgreSQL-Rolle
(`SET ROLE admin`) die nicht existiert → 500. Loesung: JavaScript Proxy trennt `.auth` (eigene
JWT-Verifikation) von `.from()/.rpc()/.storage` (plain Supabase Client mit service_role key).

## Komponenten

| Komponente | Datei | Beschreibung |
|-----------|-------|-------------|
| Auth Routes | `backend/app/api/routes/auth.py` | Login, Refresh, Logout, Me, Change-Password |
| Auth Module | `backend/app/modules/auth.py` | ModuleSpec-Registrierung |
| JWT Core | `backend/app/core/auth/jwt.py` | Token-Erstellung, Verifikation, Dependencies |
| Config | `backend/app/core/config.py` | JWT_SECRET, Expiration, Audience, Issuer |
| Compat-Layer | `frontend/app/lib/supabase-server.ts` | Proxy: Auth + PostgREST getrennt |
| Auth Client | `frontend/app/lib/auth-client.ts` | Client-seitige Auth-Funktionen |
| Auth Context | `frontend/app/lib/auth-context.tsx` | React Context fuer Auth-State |
| Server Auth | `frontend/app/lib/server-auth.ts` | Server-seitige JWT-Verifikation |
| Login Route | `frontend/app/auth/login/route.ts` | Login → Cookie setzen |
| Logout Route | `frontend/app/auth/logout/route.ts` | Cookies loeschen |
| Middleware | `frontend/middleware.ts` | Token-Refresh, Session-Check |
| DB Migration | `supabase/migrations/20260313000001_own_auth_migration.sql` | public.users, RLS-Rewrite |

## Cookies

| Cookie | HttpOnly | SameSite | Zweck |
|--------|----------|----------|-------|
| `pms_access_token` | Nein | Lax | JWT fuer API-Calls (Client braucht Zugriff) |
| `pms_refresh_token` | Ja | Strict | Refresh-Token (nur Server) |

## Environment-Variablen

### Backend (pms-api-backend)
- `JWT_SECRET` — gleicher Wert wie `SUPABASE_JWT_SECRET`
- `JWT_EXPIRATION_MINUTES` — Default: 60
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` — Default: 30

### Frontend (pms-admin-frontend)
- `JWT_SECRET` — gleicher Wert
- `SUPABASE_SERVICE_ROLE_KEY` — **NEU erforderlich** fuer PostgREST DB-Queries

## Troubleshooting

### "role admin does not exist" (PostgREST)
**Ursache:** User-JWT mit `role: "admin"` wird an PostgREST gesendet.
**Fix:** `SUPABASE_SERVICE_ROLE_KEY` im Frontend-Container setzen. Die Proxy-Architektur
in `supabase-server.ts` verhindert, dass der User-JWT an PostgREST gelangt.

### "supabaseKey is required"
**Ursache:** `SUPABASE_SERVICE_ROLE_KEY` nicht gesetzt und Fallback-Key fehlt.
**Fix:** ENV-Variable in Coolify setzen.

### Login schlaegt fehl mit 500
**Ursache:** bcrypt-Inkompatibilitaet (passlib + bcrypt>=4.1).
**Fix:** Direktes `import bcrypt` statt passlib (bereits gefixt in Commit 96cd112f).

### Token wird abgelehnt (MissingRequiredClaimError "aud")
**Ursache:** `JWT_AUDIENCE` konfiguriert aber Token ohne `aud` Claim.
**Fix:** `create_access_token()` setzt `aud`/`iss` Claims (bereits gefixt in Commit 2dfa3f8b).

### RLS-Policies blockieren Zugriff
**Ursache:** Helper-Funktionen (`current_user_id()`) ohne Fallback zu `auth.uid()`.
**Fix:** SQL-Fix in den Helper-Funktionen: `COALESCE(current_setting(...), auth.uid())`.

## Rollback

Siehe `/Plaene/Supabase-Abloesung/ANLEITUNG-ZUR-DURCHFUEHRUNG.md` → Notfall-Rollback.
Kurzfassung:
1. `git revert` der Auth-Commits
2. Frontend + Backend redeployen
3. `DROP TABLE public.users CASCADE` + Helper-Funktionen loeschen
4. `JWT_SECRET` ENV entfernen

## Naechste Phasen

- **Phase 2:** Storage → MinIO (Supabase Storage ersetzen)
- **Phase 3:** Datenbank → Direkte PostgreSQL-Verbindung (PostgREST + supabase-js entfernen)
