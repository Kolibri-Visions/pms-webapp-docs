# PMS-Webapp Project Status

**Last Updated:** 2026-03-11

**Current Phase:** Code-Qualitaet Audit 2 — Stufe 6-8 abgeschlossen, UI-Fixes + Refactorings

---

## P8.3: Pre-Commit Hook fuer Type-Sync Warnung (2026-03-11) — IMPLEMENTED

### Was wurde geaendert

- **Neuer Hook:** `.githooks/pre-commit` — warnt wenn Backend-Schemas geaendert werden ohne Frontend-Types zu aktualisieren
- Zweite Pruefung: warnt wenn Backend-Models geaendert werden ohne neue Migration
- Nicht blockierend (exit 0) — nur Warnung, kein Hard-Fail
- Installation: `git config core.hooksPath .githooks`

### Wo

- `.githooks/pre-commit`

### Verification Path

- `git config core.hooksPath .githooks` ausfuehren
- Backend-Schema aendern und committen → Warnung muss erscheinen

---

## P8.1: Scaffold-Script fuer Feature-Module (2026-03-11) — IMPLEMENTED

### Was wurde geaendert

- **Neues Script:** `backend/scripts/scaffold_feature.py` — Code-Generator fuer neue Feature-Module
- Generiert 7 Dateien: Migration (mit RLS), Schema (Pydantic), Service, Routes, Module, Frontend Types, Frontend Page
- Basiert auf Amenities-Modul als Referenz-Pattern
- `--dry-run` Modus zum Testen ohne Dateien zu erstellen
- Automatische Singular-Erkennung (payments→payment, categories→category)
- Templates folgen allen Projekt-Konventionen (Design-Tokens, Table-to-Card, require_roles, emit_audit_event)

### Wo

- `backend/scripts/scaffold_feature.py`

### Usage

```bash
python3 backend/scripts/scaffold_feature.py payments --dry-run  # Vorschau
python3 backend/scripts/scaffold_feature.py payments            # Dateien erstellen
```

### Verification Path

- `python3 backend/scripts/scaffold_feature.py payments --dry-run` muss 7 Dateien auflisten
- Generierte Dateien muessen Projekt-Konventionen einhalten

---

## UI-Refactoring: DismissibleHint + CI-Fix + RoleForm (2026-03-11) — IMPLEMENTED

### Was wurde geaendert

**DismissibleHint System:**
- Neue zentrale Komponente fuer wegklickbare Hinweise (localStorage-basiert)
- 8 Admin-Seiten auf DismissibleHint migriert (einheitliches Pattern)

**CI-Fix:**
- `API_BASE_URL` Umgebungsvariable in GitHub Actions korrekt gesetzt
- Node.js Version von 20 auf 22 aktualisiert in CI-Pipeline

**RoleForm Shared Component:**
- RoleForm als wiederverwendbare Form-Komponente extrahiert
- Modal- und useConfirm-Migration fuer Rollen-Verwaltung

### Verification Path

- Frontend Build: `cd frontend && npm run build`
- DismissibleHint: Manuell pruefen ob Hinweise wegklickbar sind und nach Reload verschwunden bleiben
- CI: GitHub Actions Pipeline muss gruen sein

---

## Pricing/Booking Fixes + Status-Bereinigung (2026-03-10) — IMPLEMENTED

### Was wurde geaendert

**MwSt Netto/Brutto Fix:**
- `is_inclusive` Flag durch gesamte Chain propagiert (Backend → Frontend)
- Korrekte Berechnung bei inklusiver vs exklusiver MwSt
- Labels angepasst: "enthaltene MwSt." vs "zzgl. MwSt."

**Booking Validierungsfehler-Persistenz:**
- Validierungsfehler verschwinden jetzt korrekt bei erneuter Feldeingabe

**Calendar Fallback-Basispreis entfernt:**
- Tage ohne Saison zeigen "Kein Preis" statt falschem 100€-Fallback

**Booking-Status Bereinigung:**
- Status `pending`, `declined`, `no_show` komplett entfernt
- DB-Migration, Backend-Constants und Frontend-Labels bereinigt

**Booking-Requests Verfuegbarkeitsfilter:**
- Zeigt nur zukuenftige Anfragen als "verfuegbar" an

### Verification Path

- Frontend Build: `cd frontend && npm run build`
- Pricing: Manuell pruefen ob MwSt-Labels korrekt (inklusiv/exklusiv)
- Calendar: Pruefen ob Tage ohne Saison "Kein Preis" zeigen
- Booking-Status: Pruefen ob pending/declined/no_show nicht mehr in Dropdowns erscheinen

---

## Infrastruktur-Hardening P6+P7: Observability + DB-Hardening (2026-03-08) — IMPLEMENTED

### Was wurde geaendert

**P6: Observability**
- `backend/app/core/logging_config.py` (NEU): Structured Logging mit structlog (JSON in Prod, farbig in Dev)
- `backend/app/core/request_id_middleware.py` (NEU): X-Request-ID Middleware mit structlog-Context-Binding
- `backend/app/core/metrics.py` (BEREITS VORHANDEN): Prometheus-Metrics (HTTP, Business, DB-Pool, Events)
- `backend/app/main.py`: Structured Logging integriert, /metrics Endpoint, Request-ID Middleware, erweiterte Startup-Diagnostics
- GET `/metrics` Endpoint fuer Prometheus-Scraping

**P7: DB-Hardening**
- `supabase/scripts/index_usage_audit.sql` (NEU): Ungenutzte Indexes, Sequential Scans, doppelte Indexes
- `supabase/scripts/rls_performance_check.sql` (NEU): RLS-Policy-Analyse, Index-Pruefung fuer team_members
- P7.1 Slow-Query Logging: Server-seitige PostgreSQL-Konfiguration (Anleitung im FIXPLAN)
- P7.2 Pool-Metrics: Integriert in GET /metrics (db_pool_size, db_pool_free, db_pool_used)

### Betroffene Dateien

- `backend/app/main.py` (geaendert)
- `backend/app/core/logging_config.py` (neu)
- `backend/app/core/request_id_middleware.py` (neu)
- `supabase/scripts/index_usage_audit.sql` (neu)
- `supabase/scripts/rls_performance_check.sql` (neu)

### Verification Path

```bash
# Syntax-Check:
cd backend && python3 -m compileall app/core/logging_config.py app/core/request_id_middleware.py app/core/metrics.py -q

# Metrics-Endpoint (nach Deploy):
curl -s https://YOUR_DOMAIN/metrics | head -20

# Request-ID Header:
curl -sI https://YOUR_DOMAIN/health | grep -i x-request-id

# Index-Audit (Supabase SQL Editor):
# Inhalt von supabase/scripts/index_usage_audit.sql ausfuehren

# RLS-Check (Supabase SQL Editor):
# Inhalt von supabase/scripts/rls_performance_check.sql ausfuehren
```

---

## Infrastruktur-Hardening P1+P2: CI Quality Gates + Backend-Refactoring (2026-03-08) — IMPLEMENTED

### Was wurde geaendert

**P1: CI/CD Quality Gates**
- `ci-backend.yml`: pytest von optional (`|| echo`) auf mandatory geaendert
- `ci-backend.yml`: Ruff Lint-Check als zusaetzlichen Step hinzugefuegt
- `ci-backend.yml`: Umgebungsvariablen fuer CI-Tests hinzugefuegt (Placeholder)
- `lint-full.yml`: Von manuell (`workflow_dispatch`) auf automatisch bei PRs umgestellt

**P2: Backend deps.py Refactoring**
- `backend/app/api/deps.py` (1.078 Zeilen God-File) aufgeteilt in Package:
  - `deps/__init__.py` — Re-Exports (volle Backward-Kompatibilitaet)
  - `deps/auth.py` — Agency-Context, Role-Resolution
  - `deps/rbac.py` — Role/Permission-Based Access Control (V1 + V2)
  - `deps/services.py` — Service Factory Functions (DI)
  - `deps/verification.py` — Cross-Tenant Resource Verification

### Betroffene Dateien

- `.github/workflows/ci-backend.yml` (geaendert)
- `.github/workflows/lint-full.yml` (geaendert)
- `backend/app/api/deps.py` → `backend/app/api/deps/` Package (5 neue Dateien)

### Verification Path

```bash
# Syntax-Check:
cd backend && python3 -m compileall app/ -q
# Erwartung: Exit-Code 0

# Import-Check (auf Python 3.12):
python3 -c "from app.api.deps import get_booking_service, require_roles, get_current_agency_id; print('OK')"

# CI-Datei Check:
grep -c "echo.*No unit tests" .github/workflows/ci-backend.yml
# Erwartung: 0 (kein echo-Fallback mehr)
```

---

## Code-Qualitaet Stufe 3: TypeScript any Eradication (2026-03-08) — IMPLEMENTED

### Was wurde geaendert

- **62 catch-Bloecke**: `catch (err: any)` → `catch (err: unknown)` mit korrektem Type-Narrowing
- **Channel/Sync Interfaces**: `types/channel.ts` mit ChannelConnection, SyncLog, BatchOperation, SyncTriggerResult u.a.
- **AuthContext**: `user: any` → `User` (aus @supabase/supabase-js)
- **ApiError.data**: `any` → `Record<string, unknown> | null`
- **apiClient Generics**: `<T = any>` → `<T = unknown>`, `body?: any` → `body?: unknown`
- **Inline Button**: Ersetzt durch shared `Button` aus `components/ui/Button.tsx`, `accent` Variant hinzugefuegt
- **[key: string]: any**: Spread Props entfernt (Card/Button in bookings/[id])
- **~20 API-Callsites**: Explizite Typ-Parameter hinzugefuegt

### Betroffene Dateien

- 46 Dateien geaendert, 581 Einfuegungen, 469 Loeschungen
- 1 neue Datei: `frontend/app/types/channel.ts`

### Verification Path

```bash
# TypeScript-Check
cd frontend && npx tsc --noEmit
# Erwartung: 0 Fehler

# Verbleibende catch any pruefen
grep -rn "catch (err: any)\|catch (e: any)\|catch (error: any)" app/ --include="*.tsx" --include="*.ts"
# Erwartung: 0 Treffer
```

---

## Bugfix: Booking-Requests CSP Trailing-Slash Redirect (2026-03-08) — IMPLEMENTED

### Problem

Die `/booking-requests`-Seite im Admin-Panel war komplett unbenutzbar. Alle API-Aufrufe wurden von der CSP `connect-src` Direktive blockiert, weil die URLs `http://` statt `https://` verwendeten.

### Root Cause (Kausalkette)

1. **God-File Refactoring** (commit `02a266b`): `booking_requests.py` wurde in Package `booking_requests/` aufgesplittet
2. **FastAPI Startup-Crash** (commit `3104d23`): Fehler "Prefix and path cannot be both empty" — Fix: Route-Path von `""` auf `"/"` geaendert
3. **Trailing-Slash Mismatch**: Backend-Route war nun `/api/v1/booking-requests/` (mit Slash), Frontend rief `/api/v1/booking-requests` (ohne Slash) auf
4. **307 Redirect**: FastAPI leitete automatisch auf die Trailing-Slash-Variante um
5. **HTTP-Schema im Redirect**: Hinter dem Reverse-Proxy (Traefik/Coolify) nutzte die Redirect-URL `http://` statt `https://`, weil `scope["scheme"]` intern "http" war
6. **CSP-Blockade**: Browser blockierte den Redirect zu `http://api.fewo...` (CSP erlaubt nur `https://`)

### Fix

- **Commit `7030269`**: Trailing-Slash zu allen 6 List-API-Aufrufen im Frontend hinzugefuegt (`/api/v1/booking-requests/?...`)
- Kein Redirect mehr noetig → kein http:// → kein CSP-Problem

### Zusaetzlich revertierte Aenderung (Stufe 2, Item 2.6)

- `getApiBase()` in `api-client.ts` wurde zurueck auf eigenstaendige Implementierung gesetzt (commit `e700a46`)
- **Begruendung:** `config.ts` `getApiBaseUrl()` hat Server-Pfad mit `API_BASE_URL` (potenziell internes `http://`). `getApiBase()` ist absichtlich Client-Only und nutzt nur `NEXT_PUBLIC_*` Vars
- **Entscheidung:** Revert bleibt — die Trennung ist architektonisch korrekt

### Betroffene Dateien

| Datei | Aenderung |
|-------|-----------|
| `frontend/app/(admin)/booking-requests/page.tsx` | 6x URL mit Trailing-Slash |
| `frontend/app/lib/api-client.ts` | Revert auf eigenstaendige getApiBase() |
| `backend/app/api/routes/booking_requests/list.py` | Route-Path `"/"` (unveraendert, war der Ausgangs-Fix) |

### Verification Path

```bash
# PROD: Seite laden und Konsole pruefen
# https://admin.fewo.kolibri-visions.de/booking-requests
# Erwartung: Keine CSP-Fehler, Daten laden korrekt
```

### Lessons Learned

- Bei Route-Path-Aenderungen (`""` → `"/"`) immer Frontend-URLs auf Trailing-Slash pruefen
- FastAPI `redirect_slashes=True` (Default) + Reverse-Proxy = potenzielle http:// Redirects
- `ForwardedProtoMiddleware` existiert, aber `TRUST_PROXY_HEADERS` muss in Coolify auf `true` stehen

---

## Code-Qualitaet Stufe 2: Shared Utilities (2026-03-08) — IMPLEMENTED

### Was wurde geaendert
- **formatDate/formatDateTime/formatDateISO/formatDateShort** als Shared Utilities in `frontend/app/lib/format-utils.ts` zentralisiert
- **getApiErrorMessage** als Shared Utility in `frontend/app/lib/api-utils.ts` zentralisiert
- **escape_like()** Utility in `backend/app/core/sql_utils.py` erstellt — schuetzt ILIKE-Queries vor Metacharacter-Injection
- **getApiBase()** in `api-client.ts`: Delegation an config.ts wurde revertiert (siehe Bugfix oben) — bleibt eigenstaendig (Client-Only Safety)

### Betroffene Dateien (Frontend — 22 Dateien)
- 18 Dateien: inline formatDate/formatDateTime entfernt, Import aus format-utils
- 4 Dateien: inline getApiErrorMessage entfernt, Import aus api-utils
- `api-client.ts`: getApiBase() Delegation revertiert — bleibt eigenstaendig (Client-Only)

### Betroffene Dateien (Backend — 9 Dateien)
- Neues Modul: `app/core/sql_utils.py` mit escape_like()
- 9 Dateien mit ILIKE-Queries: escape_like() eingefuegt

### Verification Path
- `python3 -m py_compile app/core/sql_utils.py` — OK
- `python3 -m py_compile` aller 9 Backend-Dateien — 9/9 OK
- `npx tsc --noEmit` — 0 Fehler

---

## Audit-Logging: CRUD-Routes Erweiterung (2026-03-08) — IMPLEMENTED

**Ziel:** emit_audit_event() zu allen CRUD-Routes hinzufuegen, die bisher kein Audit-Logging hatten.

### Geaenderte Dateien

| Datei | Hinzugefuegte Audit-Events |
|-------|---------------------------|
| `app/api/routes/properties.py` | property_created, property_updated, property_deleted |
| `app/api/routes/guests.py` | guest_created, guest_updated, guest_deleted, guest_gdpr_deleted, guest_dsgvo_data_exported |
| `app/api/routes/bookings.py` | booking_updated, booking_status_changed, booking_cancelled (booking_created war bereits vorhanden) |
| `app/api/routes/owners/crud.py` | owner_created, owner_updated, owner_deleted, owner_gdpr_deleted, property_owner_assigned |
| `app/api/routes/availability.py` | availability_block_created, availability_block_updated, availability_block_deleted |
| `app/api/routes/extra_services.py` | extra_service_created, extra_service_updated, extra_service_deleted |
| `app/api/routes/amenities.py` | amenity_created, amenity_updated, amenity_deleted |

### Details

- Alle Audit-Events werden NACH erfolgreicher DB-Operation ausgeloest
- actor_type = "user" fuer alle authentifizierten Endpoints
- GDPR-Loeschungen sind als `critical=True` markiert
- Metadata enthaelt kontextrelevante Informationen (geaenderte Felder, Entity-Namen)
- emit_audit_event ist best-effort (Fehler brechen die Anfrage nicht ab)

### Verification Path

```bash
rg "emit_audit_event" backend/app/api/routes/ --count
# Erwartetes Ergebnis: Alle 7 Route-Dateien mit Audit-Events
```

---

## Security-Audit: Migrations-Konsolidierung + RLS-Bereinigung (2026-03-06) — IMPLEMENTED

**Ziel:** RLS-Luecken schliessen + 117 Einzel-Migrationen in saubere Baseline konsolidieren.

### Uebersicht

| Task | Beschreibung | Commit | Status |
|------|-------------|--------|--------|
| 10.1 | PROD-Audit (58 Tabellen, 155 Policies, 4 Auth-Patterns) | — | ✅ FERTIG |
| 10.2 | RLS-Fix: media_audit_log, agency_domains, amenity_definitions | `a658c09` | ✅ FERTIG |
| 10.3 | Baseline-Migration aus pg_dump (5.001 Zeilen) | `8383d97` | ✅ FERTIG |
| 10.4 | 117 Migrationen archiviert, Scripts aktualisiert | `8383d97` | ✅ FERTIG |
| 10.5 | Verifikation + Dokumentation | — | ✅ FERTIG |

### RLS-Audit Findings

| ID | Beschreibung | Severity | Status |
|----|-------------|----------|--------|
| K-04 | media_audit_log ohne RLS | HIGH | GEFIXT |
| K-05 | agency_domains ohne RLS | HIGH | GEFIXT |
| M-04 | amenity_definitions ohne RLS | LOW | GEFIXT |
| K-02 | agency_members fehlt | — | FALSE POSITIVE (ist VIEW) |
| K-03 | USING(true) auf amenities | — | FALSE POSITIVE (spaetere Migration OK) |

### Dateien

- `supabase/migrations/00000000000000_baseline.sql` — Konsolidierte Baseline (58 Tabellen, 190 Policies)
- `supabase/migrations/20260306220000_enable_rls_media_audit_agency_domains.sql` — RLS-Fix (archiviert)
- `supabase/migrations/_archive/` — 117 historische Migrationen
- `supabase/scripts/mark_baseline_applied.sql` — PROD-DB: Baseline als applied markieren
- `supabase/verify-rls.sql` — Aktualisiertes Verifikations-Script
- `supabase/rls-policies.sql` — Referenz-Dokument aller RLS-Policies

### Verification Path

```bash
# Auf PROD im Supabase SQL-Editor:
# 1. verify-rls.sql ausfuehren — Erwartung: 57/58 RLS, 190 Policies
# 2. mark_baseline_applied.sql ausfuehren (einmalig nach Deploy)
```

---

## Multi-VAT System: IN PROGRESS (2026-03-05)

**Ziel:** Differenzierte Mehrwertsteuersätze für Unterkünfte (7%), Services (19%) und durchlaufende Posten (0%)

### Übersicht

| Phase | Beschreibung | Git Tag | Status |
|-------|--------------|---------|--------|
| 1-3 | DB Schema, Backend Models | - | ✅ (Vorarbeit) |
| 4 | Fee Templates UI: tax_id Dropdown | - | ✅ |
| 5 | Build Verification | - | ✅ |
| 6 | Extra Services UI: tax_id Dropdown | - | ✅ |
| 7 | Property Form: accommodation_tax_id | `multi-vat-phase7-ui` | ✅ |
| 8 | Pricing Engine: compute_totals_multi_vat() | `multi-vat-phase8-engine` | ✅ |
| 9 | Price Breakdown Display | `multi-vat-phase9-display` | ✅ |
| 10 | E-Mail Templates MwSt.-Anzeige | `multi-vat-phase10-email` | ✅ IMPLEMENTED |
| 10+ | Backend API Routes Fix (tax_id Persistierung) | `a1008ce` | ✅ IMPLEMENTED |
| 10++ | Tax Fields Fix (hint, is_inclusive, is_default_accommodation) | `009cc93` | ✅ IMPLEMENTED |
| 10+++ | Property Service Fix (accommodation_tax_id in Queries) | `f7f7c53` | ✅ IMPLEMENTED |
| 10++++ | List Taxes Fix (fehlende Felder in SELECT) | `b4438e9` | ✅ IMPLEMENTED |
| 10+++++ | Fee Edit UI + Info-Box Platzierung | - | ✅ IMPLEMENTED |
| 12 | Cleaning Tax UI (separater MwSt.-Satz für Endreinigung) | - | ✅ IMPLEMENTED |
| 13 | Price Preview Enhancement (MwSt. pro Zeile + Gruppierung) | `8e894a0` | ✅ IMPLEMENTED |
| 14 | Tax Fallback für Pre-Multi-VAT Fees | `93c4f87` | ✅ IMPLEMENTED |
| 15 | Type Konsolidierung (Frontend Types) | `7e5270a` | ✅ IMPLEMENTED |
| 16 | Test & Verifikation | - | ⏳ PENDING |

### Phase 10: E-Mail Templates (2026-03-05)

**Änderungen:**
- `backend/app/services/email_notification_service.py`:
  - `format_pricing_breakdown_for_email()` - Multi-VAT Preisaufschlüsselung
  - `format_legacy_pricing_for_email()` - Fallback für alte Buchungen
  - Templates `booking_confirmed`, `booking_request_approved` mit `{pricing_breakdown}` Placeholder

**Verification Path:** Manual Template Review + Runbook Documentation

### Phase 10+: Backend API Routes Fix (2026-03-05)

**Problem:** tax_id wurde in INSERT-Statements nicht persistiert und in Responses nicht zurückgegeben.

**Änderungen:**

**extra_services.py:**
- `list_extra_services()`: LEFT JOIN für tax_name/tax_percent hinzugefügt
- `create_extra_service()`: tax_id in INSERT + Follow-up Query für Response
- `get_extra_service()`: LEFT JOIN für tax_name/tax_percent hinzugefügt
- `update_extra_service()`: Follow-up Query für tax_info in Response

**pricing.py:**
- `list_fees()`: tax_id, tax_name, tax_percent via LEFT JOIN
- `create_fee()`: tax_id in INSERT + Follow-up Query für Response
- `update_fee()`: tax_id Handling in UPDATE + Follow-up Query
- `list_fee_templates()`: tax_info via LEFT JOIN
- `list_property_fees()`: tax_info via LEFT JOIN
- `assign_fee_from_template()`: tax_id aus Template kopieren + Follow-up Query

**Commit:** `a1008ce` - fix(multi-vat): persist and return tax_id in backend API routes

**Verification Path:** POST/GET Extra Service oder Fee mit tax_id, Response muss tax_id + tax_name + tax_percent enthalten

**Status:** ✅ IMPLEMENTED

### Phase 10++: Tax Fields Fix (2026-03-05)

**Problem:** Steuerfelder `hint`, `is_inclusive`, `is_default_accommodation` wurden nicht gespeichert.

**Änderungen:**

**pricing.py:**
- `create_tax()`: Alle Felder in INSERT (is_inclusive, hint, is_default_accommodation)
- `update_tax()`: Alle Felder in UPDATE-Handler + RETURNING *

**fees-taxes/page.tsx:**
- Info-Kasten aktualisiert: erklärt Multi-VAT-Zweck statt veralteter Text
- Geändert von Warnungs-Stil zu primärem Info-Stil

**Commit:** `009cc93` - fix(multi-vat): persist tax fields and update UI info box

**Verification Path:** Steuer erstellen/bearbeiten mit Hinweis-Feld → Hinweis muss in Tabelle erscheinen

**Status:** ✅ IMPLEMENTED

### Phase 10+++: Property Service Fix (2026-03-05)

**Problem:** `accommodation_tax_id` wurde beim Laden/Speichern von Properties nicht berücksichtigt.

**Ursache:**
- `get_property()` und `list_properties()` Queries enthielten `accommodation_tax_id` nicht
- `update_property()` hatte `accommodation_tax_id` nicht in `allowed_fields`

**Änderungen:**

**property_service.py:**
- `get_property()`: `accommodation_tax_id` + LEFT JOIN für `accommodation_tax_name`, `accommodation_tax_percent`
- `list_properties()`: Gleiche Änderung wie oben
- `update_property()`: `accommodation_tax_id` zu `allowed_fields` + UUID-Konvertierung

**Commit:** `f7f7c53` - fix(multi-vat): add accommodation_tax_id to property queries

**Verification Path:** Objekt bearbeiten → MwSt. ändern → Speichern → Erneut bearbeiten → Dropdown zeigt korrekte Auswahl

**Status:** ✅ IMPLEMENTED

### Phase 10++++: List Taxes Fix (2026-03-05)

**Problem:** Hinweis-Feld wird in der Steuern-Tabelle nicht angezeigt (immer "—").

**Ursache:** `list_taxes()` Query selektierte nur Basis-Felder, nicht die Multi-VAT Felder.

**Änderungen:**

**pricing.py:**
- `list_taxes()`: SELECT erweitert um `is_inclusive`, `hint`, `is_default_accommodation`

**Commit:** `b4438e9` - fix(multi-vat): add missing fields to list_taxes query

**Verification Path:** Steuer bearbeiten → Hinweis eingeben → Speichern → Tabelle zeigt Hinweis in HINWEIS-Spalte

**Status:** ✅ IMPLEMENTED

### Phase 10+++++: Fee Edit UI + Info-Box Platzierung (2026-03-05)

**Probleme:**
1. Gebühren-Vorlagen können nicht bearbeitet werden (nur erstellen war möglich)
2. Info-Box "Vorlagen-Verwaltung" erscheint auch im Steuern-Tab

**Änderungen:**

**fees-taxes/page.tsx:**
- `FeeTemplateForm` um `initialData?: FeeTemplate` prop erweitert
- Edit-Modus: Felder werden mit existierenden Werten vorausgefüllt
- Titel wechselt zwischen "Gebühr bearbeiten" und "Neue Gebühren-Vorlage"
- Button wechselt zwischen "Speichern" und "Erstellen"
- Info-Box "Vorlagen-Verwaltung" in den Gebühren-Tab verschoben (nicht mehr global)

**Verification Path:**
1. /fees-taxes → Gebühren → Bearbeiten-Icon klicken → Formular öffnet mit vorausgefüllten Werten
2. Ändern + Speichern → Daten werden aktualisiert
3. Tab zu Steuern wechseln → Info-Box erscheint NICHT

**Status:** ✅ IMPLEMENTED

### Phase 12: Cleaning Tax UI (2026-03-05)

**Problem:** Endreinigung hat 19% MwSt. (Dienstleistung), aber kein eigener Dropdown dafür existiert im Objekt-Formular. Layout-Problem: "Ab Gast Nr." war nicht aligned.

**Änderungen:**

**Migration:**
- `supabase/migrations/20260305224500_add_cleaning_tax_to_properties.sql`
- Neues Feld `cleaning_tax_id` UUID (FK zu pricing_taxes)

**property_service.py:**
- `list_properties()`: `cleaning_tax_id`, `cleaning_tax_name`, `cleaning_tax_percent` via LEFT JOIN
- `get_property()`: dto.
- `update_property()`: `cleaning_tax_id` zu `allowed_fields` + UUID-Konvertierung

**PropertyForm.tsx:**
- Neues Feld `cleaning_tax_id` in `PropertyFormData`
- Neuer Dropdown "MwSt. Endreinigung" neben "MwSt. Übernachtung"
- Layout-Fix: Preise-Grid in zwei separate Zeilen aufgeteilt
  - Zeile 1: Basispreis | Währung | Endreinigung | Kaution
  - Zeile 2: Extra-Gast-Gebühr | Ab Gast Nr.
- MwSt.-Dropdowns in eigener 2-Spalten-Zeile

**property.ts (Types):**
- `cleaning_tax_id`, `cleaning_tax_name`, `cleaning_tax_percent` zu Property, PropertyCreate, PropertyUpdate

**Verification Path:**
1. Objekt bearbeiten → Preise-Bereich zeigt MwSt.-Dropdowns nebeneinander
2. MwSt. Endreinigung auf 19% setzen → Speichern
3. Preisaufschlüsselung zeigt Endreinigung mit 19%

**Status:** ✅ IMPLEMENTED

### Phase 13: Price Preview Enhancement (2026-03-05)

**Ziel:** Preisvorschau im Buchungsformular verbessern - MwSt.-Sätze pro Zeile anzeigen und nach Satz gruppierte Zusammenfassung.

**Änderungen:**

**pricing.py (API Route):**
- Property-Query erweitert um `cleaning_tax_id`, `cleaning_tax_percent`, `cleaning_tax_is_inclusive`
- LEFT JOIN auf `pricing_taxes` für Cleaning Tax Daten
- Endreinigung-Berechnung nutzt jetzt `cleaning_tax_id` für MwSt.-Berechnung
- Brutto/Netto-Unterscheidung basierend auf `is_inclusive` Flag

**pricing.py (Schema):**
- `FeeLineItem.tax_percent` Feld hinzugefügt für MwSt.-Anzeige pro Zeile

**pricing_totals.py:**
- `FeeLineItem` Dataclass erweitert um `tax_percent: Optional[float]`

**bookings/page.tsx (Frontend):**
- Jede Zeile zeigt MwSt.-Satz: `Endreinigung ... (19%)`
- Gruppierte MwSt.-Zusammenfassung vor Gesamtpreis:
  ```
  Enthaltene MwSt.:
  7% (Netto: €X.XX)    €Y.YY
  19% (Netto: €A.AA)   €B.BB
  ```
- Gesamtpreis-Label: "Gesamtpreis (inkl. MwSt.)"

**Verification Path:**
1. Buchung erstellen mit Objekt das cleaning_tax_id gesetzt hat
2. Preisvorschau prüfen:
   - Jede Zeile zeigt MwSt.-Prozentsatz
   - MwSt.-Zusammenfassung gruppiert nach Satz
   - Gesamtpreis zeigt "(inkl. MwSt.)"

**Status:** ✅ IMPLEMENTED

### Phase 14: Tax Fallback für Pre-Multi-VAT Fees (2026-03-06)

**Problem:** Property-Gebühren, die VOR dem Multi-VAT Feature aus Templates importiert wurden, haben `tax_id=NULL`. Obwohl das Template jetzt `tax_id` hat, zeigt die Preisvorschau 0% statt 19%.

**Ursache:**
```sql
-- ALT: Nur die Property-Fee's tax_id wird geprüft
LEFT JOIN pricing_taxes pt ON pt.id = pf.tax_id
-- Property-Fee hat tax_id=NULL → JOIN findet nichts → tax_percent=NULL → 0%
```

**Lösung:**
```sql
-- NEU: Fallback auf Template's tax_id
LEFT JOIN pricing_fees tmpl ON pf.source_template_id = tmpl.id
LEFT JOIN pricing_taxes pt ON pt.id = COALESCE(pf.tax_id, tmpl.tax_id)
-- Property-Fee hat tax_id=NULL, aber Template hat tax_id → 19%
```

**Geänderte Datei:**
- `backend/app/api/routes/pricing.py` (fees_query in quote calculation)

**Verification Path:**
1. Property mit alter importierter Gebühr (pre-Multi-VAT)
2. Template hat tax_id gesetzt (z.B. 19%)
3. Preisvorschau zeigt jetzt korrekten MwSt.-Satz

**Status:** ✅ IMPLEMENTED

### Phase 15: Type Konsolidierung (2026-03-06)

**Ziel:** Frontend Types konsolidieren - manuelle Duplikate durch Aliase auf generierte Types ersetzen.

**Problem:** `extra-service.ts` hatte manuelle Type-Definitionen, die mit `api-generated.ts` dupliziert waren. Führte zu Inkonsistenzen und Type-Fehlern beim Deployment.

**Änderungen:**

**extra-service.ts (Frontend):**
```typescript
// VORHER: Manuelle Duplikate
export interface ExtraService { ... }
export interface PropertyExtraService { ... }

// NACHHER: Aliase auf generierte Types
export type ExtraService = components['schemas']['ExtraServiceResponse'];
export type PropertyExtraService = components['schemas']['PropertyExtraServiceResponse'];
```

**Backend Schema + Routes:**
- `PropertyExtraServiceResponse`: `service_tax_id`, `service_tax_percent` hinzugefügt
- Routes: JOIN mit `pricing_taxes` für Tax-Daten

**Deployment-Fixes (7 Commits):**
| Commit | Problem | Fix |
|--------|---------|-----|
| `72e853b` | tax_percent fehlt | Felder hinzugefügt |
| `1316c11` | Backend + Frontend Types | Konsolidierung |
| `6524f29` | extra_service_id deprecated | service_id verwenden |
| `fd64fa2` | readonly Arrays | Spread-Operator |
| `bca8985` | price_type deprecated | Entfernt |
| `fd91d55` | tax_id fehlt in ExtraService | Hinzugefügt |
| `7e5270a` | null vs undefined | ?? undefined |

**Status:** ✅ IMPLEMENTED

### Architektur

```
pricing_taxes (MwSt.-Katalog)
    ├── id, name, percent, is_inclusive
    │
fee_templates.tax_id ───┘ (FK für Gebühren-MwSt.)
extra_services.tax_id ──┘ (FK für Service-MwSt.)
properties.accommodation_tax_id ─┘ (FK für Unterkunfts-MwSt., z.B. 7%)
properties.cleaning_tax_id ─┘ (FK für Endreinigung-MwSt., z.B. 19%)

pricing_totals.py:
    compute_totals_multi_vat() → TaxLineItem mit source, source_name
```

---

## Code-Cleanup Sprint 2: COMPLETE (2026-03-05)

**Ziel:** Validators und Currency Formatting konsolidieren

### Übersicht

| Phase | Beschreibung | Commit | Status |
|-------|--------------|--------|--------|
| 2.1 | Backend Validators extrahieren | `eb2ec26` | ✅ |
| 2.2 | Frontend formatCurrency() konsolidieren | `eb2ec26` | ✅ |

### Neue Dateien

| Datei | Inhalt |
|-------|--------|
| `backend/app/schemas/validators.py` | Shared validators (phone, country, currency) |
| `frontend/app/lib/currency-utils.ts` | Currency formatting utilities |

### Aktualisierte Dateien

**Backend:**
- `app/schemas/guests.py` - nutzt shared validators
- `app/schemas/properties.py` - nutzt shared validators

**Frontend (7 Dateien):**
- `guests/[id]/page.tsx`
- `booking-requests/page.tsx`
- `bookings/page.tsx`
- `bookings/[id]/page.tsx`
- `properties/[id]/page.tsx`
- `dashboard/page.tsx`
- `components/booking/PricingBreakdown.tsx`

### Ergebnis

- **~100 Zeilen Code reduziert**
- **Einheitliche Formatierung** im gesamten Frontend
- **DRY-Prinzip** für Validators eingehalten

**Status:** ✅ IMPLEMENTED

---

## Code-Cleanup Sprint 1: COMPLETE (2026-03-05)

**Ziel:** Public Booking Code konsolidieren, kritischen Bug fixen, API-Versionen vereinheitlichen

### Übersicht

| Phase | Beschreibung | Commit | Status |
|-------|--------------|--------|--------|
| 1.1 | PublicBookingService erstellen | `d08ff1f` | ✅ |
| 1.2 | Availability Bug Fix (inventory_ranges) | `d08ff1f` | ✅ |
| 1.3 | Booking Creation konsolidiert | `d08ff1f` | ✅ |
| 1.4 | v1/v2 API konsolidiert | `d1488f4` | ✅ |

### Kritischer Bug Fix

**Problem (BEHOBEN):**
- Availability-Check fragte nur `bookings` Tabelle
- Sperrzeiten (`availability_blocks`) wurden ignoriert
- Gäste konnten für gesperrte Zeiträume buchen

**Lösung:**
- `PublicBookingService.check_availability()` nutzt jetzt `inventory_ranges`
- Erkennt sowohl Buchungen als auch Sperrzeiten
- Returns `reason: "blocked"` oder `reason: "double_booking"`

### API-Konsolidierung

**Problem (BEHOBEN):**
- v1 für site/properties, v2 für booking → Inkonsistent
- v2 war nur Feldnamen-Konvention, keine echte API-Version

**Lösung:**
- Alle Public APIs jetzt unter `/api/v1/public/*`
- Standardisierte Feldnamen: `check_in`, `check_out`, `num_adults`, `num_children`
- `public_booking_v2.py` gelöscht

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/public_booking_service.py` | NEU (320 Zeilen) |
| `backend/app/api/routes/public_booking.py` | Neu geschrieben |
| `backend/app/api/routes/public_booking_v2.py` | GELÖSCHT |
| `backend/app/modules/public_booking.py` | v2 entfernt |
| `frontend/app/(public)/buchung/BuchungClient.tsx` | v2 → v1 |

### PROD-Verifikation

```bash
# Ping
curl https://api.fewo.kolibri-visions.de/api/v1/public/ping
# → {"status": "ok", "message": "Public booking router operational"}

# Availability (freie Daten)
curl ".../availability?property_id=...&check_in=2026-06-15&check_out=2026-06-20"
# → {"available": true, ...}

# Availability (Sperrzeit)
curl ".../availability?property_id=...&check_in=2026-03-26&check_out=2026-03-29"
# → {"available": false, "reason": "blocked"}
```

### Git-Tags

- `pre-cleanup-baseline` (Commit: ef44c41)
- `pre-cleanup-phase-1.1` (Commit: ef44c41)
- `pre-v1-consolidation` (Commit: d08ff1f)

### Ergebnis

- **~714 Zeilen Code reduziert**
- **Kritischer Bug behoben** (Sperrzeiten werden erkannt)
- **Einheitliche API-Struktur** (alle unter /api/v1/public/*)

**Status:** ✅ VERIFIED (PROD-Tests erfolgreich)

---

## Type-Consistency Re-Audit Phase 4: COMPLETE (2026-03-04)

**Gesamtumfang:** 6 Phasen, 12 Commits, ~700 Zeilen neue/geänderte Types

### Phase-Übersicht

| Phase | Beschreibung | Commit | Status |
|-------|--------------|--------|--------|
| 4.1 | Branding Types (30+ Felder) | `e449de9` | ✅ |
| 4.2 | Guest Types (9 Felder, 7 Guards) | `23e930e` | ✅ |
| 4.3 | API-Pagination (limit/offset) | `cda0b02` | ✅ |
| 4.4 | Response-Wrapper (.items) | `4516c25` | ✅ |
| 4.5 | Accessibility Audit | `97a4ca9` | ✅ |
| 4.6 | Documentation | `30d81e4` | ✅ |

### Neue Dateien

| Datei | Zeilen | Inhalt |
|-------|--------|--------|
| `frontend/app/types/branding.ts` | 356 | Vollständige Branding-Types |

### Erweiterte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/guest.ts` | +228 Zeilen (9 Felder, 7 Guards) |
| `frontend/app/types/api.ts` | Pagination-Standard, Utilities |
| `frontend/app/types/media.ts` | limit/offset Support |
| `frontend/app/types/operations.ts` | Response-Wrapper Cleanup |
| `frontend/app/lib/api-utils.ts` | normalizeResponse erweitert |
| `frontend/app/(auth)/login/login-client.tsx` | a11y Improvements |

### Git-Tags

- `pre-type-consistency-4-phase-1` ... `pre-type-consistency-4-phase-6`
- `type-consistency-4-complete` ← **Finale Version**

### Revert (alle Phase 4 Änderungen)

```bash
git reset --hard b97c6a9  # Commit vor Phase 4.1
```

---

## Type-Consistency Re-Audit Phase 4.5: Accessibility (2026-03-04) — IMPLEMENTED

**Scope:** WCAG 2.1 AA Compliance-Audit und Verbesserungen

### Audit-Ergebnis: Größtenteils Compliant ✅

Die meisten kritischen WCAG-Anforderungen waren bereits implementiert.

### Bereits Implementiert (vor Phase 4.5)

| Feature | WCAG | Dateien |
|---------|------|---------|
| Skip-Links | 2.4.1 | AdminShell.tsx, public/layout.tsx |
| FocusTrap in Modals | 2.1.2 | 70+ Modal-Komponenten |
| role="dialog" + aria-modal | 4.1.2 | Alle Dialog-Komponenten |
| aria-label auf Icon-Buttons | 4.1.2 | 431 Vorkommen in 60 Dateien |
| htmlFor auf Labels | 1.3.1 | Alle kritischen Formulare |
| aria-live auf Toast | 4.1.3 | Toast.tsx |
| aria-labelledby auf Dialoge | 4.1.2 | Modal.tsx, ConfirmDialog.tsx |

### Verbesserungen (Phase 4.5)

| Komponente | Änderung | WCAG |
|------------|----------|------|
| login-client.tsx | role="alert" + aria-live auf Fehlermeldung | 4.1.3 |
| login-client.tsx | aria-invalid + aria-describedby auf Inputs | 3.3.1 |

### Komponenten mit voller WCAG-Compliance

- `Modal.tsx` - FocusTrap, aria-modal, aria-labelledby, aria-describedby, ESC-Support
- `ConfirmDialog.tsx` - FocusTrap, aria-modal, aria-labelledby, Cancel-Focus
- `Toast.tsx` - aria-live="polite", role="alert", aria-label
- `AdminShell.tsx` - Skip-Link, aria-current auf Navigation

### Commits

| Phase | Commit | Status |
|-------|--------|--------|
| Git-Tag erstellt | `pre-type-consistency-4-phase-5` | ✅ |
| Login-Form verbessert | `97a4ca9` | ✅ |

### Verification Path

```bash
cd frontend && npm run build  # TypeScript-Validierung ✅
# Manuelle Tests: Tab-Navigation, Screen-Reader, ESC-Taste
```

### Revert

```bash
git reset --hard pre-type-consistency-4-phase-5
```

### Status

✅ IMPLEMENTED

---

## Type-Consistency Re-Audit Phase 4.4: Response-Wrapper (2026-03-04) — IMPLEMENTED

**Scope:** Standardisierung aller List-Responses auf `.items` Pattern

### Änderungen

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/operations.ts` | AuditLogResponse, OutboxListResponse bereinigt |
| `frontend/app/lib/api-utils.ts` | normalizeResponse erweitert um `entries` Support |

### Response-Wrapper Standard

```typescript
// Standard Format (alle neuen APIs)
interface ListResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
```

### Backend-Ausnahmen

| API | Feld | Hinweis |
|-----|------|---------|
| AuditLogListResponse | `entries` | Historisch, normalizeResponse konvertiert |

### normalizeResponse Priorität

1. Custom `itemsKey` (wenn angegeben)
2. `items` (Standard)
3. `entries` (AuditLog)
4. `data` (Legacy)
5. `results` (Legacy)

### Commits

| Phase | Commit | Status |
|-------|--------|--------|
| Git-Tag erstellt | `pre-type-consistency-4-phase-4` | ✅ |
| Response-Wrapper standardisiert | `4516c25` | ✅ |

### Verification Path

```bash
cd frontend && npm run build  # TypeScript-Validierung ✅
```

### Revert

```bash
git reset --hard pre-type-consistency-4-phase-4
```

### Status

✅ IMPLEMENTED

---

## Type-Consistency Re-Audit Phase 4.3: API-Pagination (2026-03-04) — IMPLEMENTED

**Scope:** Standardisierung aller Pagination-Types auf limit/offset

### Neue Types

| Type | Beschreibung |
|------|--------------|
| `PaginationParams` | Standard: { limit?: number; offset?: number } |
| `StandardPaginatedResponse<T>` | Standard: { items, total, limit, offset } |
| `StandardListParams` | PaginationParams + sort_by, sort_order, search |

### Utilities

| Funktion | Beschreibung |
|----------|--------------|
| `pageToOffset(page, perPage)` | Konvertiert page/per_page → limit/offset |
| `offsetToPage(offset, limit)` | Konvertiert offset/limit → page (1-based) |
| `calculateTotalPages(total, limit)` | Berechnet Seitenzahl |
| `DEFAULT_PAGINATION` | Konstante: { limit: 20, offset: 0 } |

### Deprecated (Legacy)

| Type/Field | Ersatz |
|------------|--------|
| `PaginatedResponse.data` | `StandardPaginatedResponse.items` |
| `PaginatedResponse.page` | `offset = (page - 1) * limit` |
| `PaginatedResponse.per_page` | `limit` |
| `ListParams.page` | `StandardListParams.offset` |
| `ListParams.per_page` | `StandardListParams.limit` |
| `MediaFileFilter.page_size` | `limit` |

### Commits

| Phase | Commit | Status |
|-------|--------|--------|
| Git-Tag erstellt | `pre-type-consistency-4-phase-3` | ✅ |
| Pagination standardisiert | `cda0b02` | ✅ |

### Verification Path

```bash
cd frontend && npm run build  # TypeScript-Validierung ✅
```

### Revert

```bash
git reset --hard pre-type-consistency-4-phase-3
```

### Status

✅ IMPLEMENTED

---

## Type-Consistency Re-Audit Phase 4.2: Guest Types (2026-03-04) — IMPLEMENTED

**Scope:** Fehlende Guest-Felder und Type Guards hinzufügen

### Änderungen

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/guest.ts` | 228 neue Zeilen (+9 Felder, +7 Type Guards) |

### Neue Union Types

| Type | Beschreibung |
|------|--------------|
| `IdDocumentType` | 'passport' \| 'id_card' \| 'drivers_license' |
| `CommunicationChannel` | 'email' \| 'phone' \| 'whatsapp' \| 'sms' |
| `GuestSource` | 'direct' \| 'airbnb' \| ... \| 'referral' \| 'other' |

### Neue Guest-Felder

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `auth_user_id` | `string \| null` | Link zu auth.users |
| `id_document_type` | `IdDocumentType \| null` | Ausweistyp |
| `id_document_number` | `string \| null` | Ausweisnummer |
| `id_verified_at` | `string \| null` | Verifizierungs-Timestamp |
| `marketing_consent_at` | `string \| null` | Consent-Timestamp |
| `first_booking_at` | `string \| null` | Erste Buchung |
| `average_rating` | `string \| null` | Durchschnittsbewertung |
| `source` | `GuestSource \| null` | Akquise-Quelle |
| `deleted_at` | `string \| null` | Soft-Delete Timestamp |

### Type Guards & Utilities

- `isGuestDeleted()` - Soft-Delete Check
- `isGuestActive()` - Aktiv-Check
- `isGuestVip()` - VIP-Status Check
- `isGuestBlacklisted()` - Blacklist Check
- `isGuestVerified()` - ID-Verifizierungs Check
- `hasGuestAccount()` - Auth-Account Check
- `getGuestFullName()` - Name-Helper

### Commits

| Phase | Commit | Status |
|-------|--------|--------|
| Git-Tag erstellt | `pre-type-consistency-4-phase-2` | ✅ |
| guest.ts erweitert | `23e930e` | ✅ |

### Verification Path

```bash
cd frontend && npm run build  # TypeScript-Validierung ✅
```

### Revert

```bash
git reset --hard pre-type-consistency-4-phase-2
```

### Status

✅ IMPLEMENTED

---

## Type-Consistency Re-Audit Phase 4.1: Branding Types (2026-03-04) — IMPLEMENTED

**Scope:** Umfassende TypeScript-Typdefinitionen für alle tenant_branding DB-Spalten (30+ Felder)

### Neue Datei

| Datei | Beschreibung |
|-------|--------------|
| `frontend/app/types/branding.ts` | Vollständige Branding-Types (356 Zeilen) |

### Inhalt branding.ts

| Type | Beschreibung |
|------|--------------|
| `FontFamily` | Union: 'system' \| 'inter' \| 'roboto' \| 'open-sans' \| 'poppins' |
| `RadiusScale` | Union: 'none' \| 'sm' \| 'md' \| 'lg' |
| `ThemeMode` | Union: 'system' \| 'light' \| 'dark' |
| `ShadowIntensity` | Union: 'none' \| 'subtle' \| 'normal' \| 'strong' |
| `LogoPosition` | Union: 'left' \| 'center' |
| `NavigationBrandingConfig` | JSONB nav_config Struktur |
| `ThemeTokens` | Computed Theme-Tokens (8 Felder) |
| `TenantBranding` | Haupt-Interface (30+ Felder, alle Phasen 1-6) |
| `BrandingUpdate` | Partial für API-Updates |
| `BrandingResponse` | API-Response mit tokens |
| `BrandingLogoResponse` | Logo-Upload Response |

### Utility-Funktionen

- `isValidHexColor()` - Hex-Farbvalidierung
- `getDefaultThemeTokens()` - Fallback-Tokens
- `deriveBrandingTokens()` - Token-Berechnung aus Branding

### Synchronisation

- Synchronisiert mit: `backend/app/schemas/branding.py`
- Alle 6+ Migrationen berücksichtigt

### Commits

| Phase | Commit | Status |
|-------|--------|--------|
| Git-Tag erstellt | `pre-type-consistency-4-phase-1` | ✅ |
| branding.ts + Export | `e449de9` | ✅ |

### Verification Path

```bash
cd frontend && npm run build  # TypeScript-Validierung ✅
```

### Revert

```bash
git reset --hard pre-type-consistency-4-phase-1
```

### Status

✅ IMPLEMENTED

---

## Type-Consistency Konsolidierung Phase 3 (2026-03-04) — IMPLEMENTED

**Scope:** Umfassende Type-Synchronisation zwischen Frontend (TypeScript) und Backend (Pydantic) - 27 Issues in 12 Kategorien.

### Phasen

| Phase | Beschreibung | Commit | Status |
|-------|-------------|--------|--------|
| 3.1 | Availability Types (5 kritische Feldnamen) | `4716fb9` | ✅ |
| 3.2 | Media Library Types (tenant_id→agency_id, document type) | `378a835` | ✅ |
| 3.3 | Branding Types (FALSE POSITIVE korrigiert) | `482fb9d` | ✅ |
| 3.4 | Property Types (deactivated_at, required fields) | `760c8ba` | ✅ |
| 3.5 | Website/Public Types (SiteSettings, TopbarConfig) | `d530628` | ✅ |
| 3.6 | Block System Types (600+ Zeilen neue blocks.ts) | `50a2e8c` | ✅ |
| 3.7 | Operations/AuditLog Types (actor_user_id, entity_type) | `cdd30df` | ✅ |
| 3.8 | Cleanup & Medium Priority (Dokumentation) | `92aee55` | ✅ |
| 3.9 | Dokumentation & Abschluss | (dieser Commit) | ✅ |

### Neue/Geänderte Type-Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/availability.ts` | Vollständige Neufassung: from_date/to_date, state/kind |
| `frontend/app/types/media.ts` | agency_id, FileType mit 'document', Normalizer |
| `frontend/app/types/property.ts` | deactivated_at, PropertyCreateData, PropertyUpdateData |
| `frontend/app/types/website.ts` | SiteSettings, TopbarConfig, PublicDesignData erweitert |
| `frontend/app/types/blocks.ts` | **NEU** - 600+ Zeilen: 26 BlockTypes, 20+ Props, StyleOverrides |
| `frontend/app/types/operations.ts` | AuditLogEntry aktualisiert, ComponentHealth |
| `frontend/app/types/cancellation.ts` | refund_percent INTEGER Dokumentation |
| `frontend/app/types/dashboard.ts` | _cents vs float Dokumentation |
| `frontend/app/types/owner.ts` | Amount-Felder Dokumentation |

### Highlights

- **blocks.ts erstellt:** Vollständiges Block-Type-System mit 26 Block-Typen, 20+ Props-Interfaces, 30+ StyleOverrides
- **@deprecated Marker:** Legacy-Felder konsistent markiert für schrittweise Migration
- **Type Guards:** Utility-Funktionen für Runtime-Checks (isContainerBlock, isDeactivated, etc.)
- **Normalizer-Funktionen:** Für Backend-Kompatibilität (normalizeMediaFile, normalizeRange)

### Verification Path

```bash
cd frontend && npm run build  # TypeScript-Validierung
```

### Revert

```bash
# Einzelne Phase
git reset --hard pre-type-consistency-3-phase-{N}

# Alles Phase 3
git reset --hard pre-type-consistency-3-baseline
```

### Status

✅ IMPLEMENTED

---

## Type-Consistency Konsolidierung Phase 2 (2026-03-04) — IMPLEMENTED

**Scope:** Behebung von 17 zusätzlichen Type-Inkonsistenzen, die nach der ersten Konsolidierung entdeckt wurden.

### Phasen

| Phase | Beschreibung | Commit | Status |
|-------|-------------|--------|--------|
| 1 | Pricing-Feldnamen (7 Felder) | `a502bcd` | ✅ |
| 2 | Booking-Feldnamen (2 Felder) | `b07ef5a` | ✅ |
| 3 | Nicht-implementierte Backend-Felder (@deprecated) | `97650b4` | ✅ |
| 4 | Guest-Timeline Felder (Korrektur) | `0620cf2` | ✅ |
| 5 | Doppelte Varianten Cleanup | `f0764b2` | ✅ |
| 6 | Dokumentation | (dieser Commit) | ✅ |

### Geänderte Type-Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/pricing.ts` | RatePlan, Season, FeeTemplate, PropertyFee Felder |
| `frontend/app/types/extra-service.ts` | ExtraService, PropertyExtraService Felder |
| `frontend/app/types/visitor-tax.ts` | VisitorTaxPeriod Felder |
| `frontend/app/types/booking.ts` | tax→tax_amount, guest_notes→guest_message |
| `frontend/app/types/amenity.ts` | is_highlighted @deprecated |
| `frontend/app/types/guest.ts` | TimelineBooking Felder korrigiert |
| `frontend/app/types/user.ts` | TeamMember, Invite role-Felder |

### Erkenntnisse

- **Guest-Timeline:** Backend verwendet korrekterweise `check_in_date`/`check_out_date` (mit `_date` Suffix) - dies war KEIN Fehler
- **Backend-Spalten:** `is_highlighted`, `is_inclusive`, `child_rate_cents` werden nicht verwendet - keine Migration nötig

### Verification Path

```bash
cd frontend && npm run build  # TypeScript-Validierung
```

### Revert

```bash
# Einzelne Phase
git reset --hard pre-type-consistency-2-phase-{N}

# Alles
git reset --hard pre-type-consistency-2-baseline
```

### Status

✅ IMPLEMENTED

---

## Type-Consistency Konsolidierung (2026-03-04) — IMPLEMENTED

**Scope:** Behebung aller Type-Inkonsistenzen zwischen Frontend (TypeScript) und Backend (Pydantic).

### Phasen

| Phase | Beschreibung | Commit | Status |
|-------|-------------|--------|--------|
| 1 | OwnerBooking date_from→check_in | (frühere Session) | ✅ |
| 2 | BillingUnit per_person entfernt | (frühere Session) | ✅ |
| 3 | Owner name→computed property | (frühere Session) | ✅ |
| 4 | Guest address @deprecated | (bereits vorhanden) | ✅ |
| 5 | Response-Wrapper .data Fallback | `bc2864d` | ✅ |
| 6 | BookingRequest deadline @deprecated | `3ba6947` | ✅ |
| 7 | PropertyExtraService extra_service_id @deprecated | `c605537` | ✅ |
| 8 | Dokumentation | (dieser Commit) | ✅ |

### Geänderte Dateien (Phase 5-8)

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/extra-services/page.tsx` | .data Fallback entfernt |
| `frontend/app/(admin)/ops/audit-log/page.tsx` | .data Fallback entfernt |
| `frontend/app/(admin)/owners/[ownerId]/page.tsx` | .data Fallback entfernt |
| `frontend/app/(admin)/connections/page.tsx` | normalizeConnections/normalizeLogs bereinigt |
| `frontend/app/(admin)/channel-sync/page.tsx` | .data Fallback entfernt (2×) |
| `frontend/app/types/extra-service.ts` | ExtraServiceListResponse, extra_service_id @deprecated |
| `frontend/app/types/booking.ts` | deadline @deprecated, JSDoc |
| `backend/docs/conventions.md` | §12.6 aktualisiert |

### Verification Path

```bash
cd frontend && npm run build  # TypeScript-Validierung
```

### Revert

```bash
# Einzelne Phase
git reset --hard pre-type-consistency-phase-{N}

# Alles
git reset --hard pre-type-consistency-baseline
```

### Status

✅ IMPLEMENTED

---

## Pricing-Bug: Vollständige Preisaufschlüsselung bei Buchungserstellung (2026-03-04) — IMPLEMENTED

**Scope:** Fix für fehlende Gebühren/Steuern-Aufschlüsselung bei manuell erstellten Buchungen.

### Problem

Bei manueller Buchungserstellung wurden Gebühren (Buchungsgebühr, Endreinigung) und Steuern nicht in die Buchung übernommen, obwohl sie in der Preisvorschau korrekt angezeigt wurden.

**Root Cause:** Frontend suchte nach Fee-Types `"cleaning"`, `"service"` die im Backend nicht existieren. Backend sendet `"per_stay"`, `"per_night"`, `"percent"`, `"per_person"`.

### Lösung

1. **Fee-Summierung:** Alle Fees via `fees_total_cents` in `cleaning_fee` speichern
2. **Steuer-Summierung:** `taxes_total_cents + visitor_tax_cents` in `tax_amount` speichern
3. **Vollständige Breakdown:** `pricing_breakdown` Objekt in `channel_data` speichern
4. **Detail-Anzeige:** Dynamisches Rendering aus `pricing_breakdown` mit Legacy-Fallback
5. **Extras-Validierung:** `extrasTotal` in `service_fee` speichern (Backend validiert `total_price == sum(subtotal + cleaning_fee + service_fee + tax_amount)`)

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/bookings/page.tsx` | Fee/Tax-Extraktion via Summen, `pricing_breakdown` in channel_data |
| `frontend/app/(admin)/bookings/[id]/page.tsx` | Dynamische Breakdown-Anzeige, "Sonstige Gebühren" Fallback |
| `frontend/app/types/booking.ts` | `pricing_breakdown` Type in channel_data |

### Verification Path

```bash
cd frontend && npm run build

# Manueller Test:
# 1. Neue Buchung mit Objekt das Gebühren/Steuern hat erstellen
# 2. Buchungs-Detail öffnen
# 3. Prüfen: Alle Gebühren einzeln sichtbar, Summe = Gesamtpreis
```

### Revert

```bash
git revert <commit-hash>
```

### Status

✅ IMPLEMENTED

---

## API-Migration Teil 2: Properties, Roles, Bookings (2026-03-04) — IMPLEMENTED

**Scope:** Migration verbleibender Proxy-Routes von `/api/internal/` zu direkten `/api/v1/` apiClient-Calls

### Änderungen

**Phase 1: Properties-Seiten (9 Calls)**
- `properties/[id]/page.tsx`: Amenities GET/PUT
- `properties/[id]/extra-services/page.tsx`: Extra-Services CRUD

**Phase 2: Settings/Roles (6 Calls)**
- `settings/roles/page.tsx`: Roles + Permissions CRUD

**Phase 3: Bookings-Detail (1 Call)**
- `bookings/[id]/page.tsx`: Property Media GET

### Geänderte Dateien

| Datei | Calls | Änderung |
|-------|-------|----------|
| `frontend/app/(admin)/properties/[id]/page.tsx` | 3 | apiClient Migration |
| `frontend/app/(admin)/properties/[id]/extra-services/page.tsx` | 6 | apiClient Migration |
| `frontend/app/(admin)/settings/roles/page.tsx` | 6 | apiClient Migration |
| `frontend/app/(admin)/bookings/[id]/page.tsx` | 1 | apiClient Migration |

### Git Tags

- `pre-api-migrate-2-baseline` → vor allen Änderungen
- `pre-api-migrate-2-phase-2` → nach Properties
- `pre-api-migrate-2-phase-3` → nach Roles
- `pre-api-migrate-2-phase-4` → nach Bookings

### Verification Path

```bash
cd frontend && npm run build  # Keine Fehler
git tag -l | grep api-migrate-2
```

### Revert

```bash
git reset --hard pre-api-migrate-2-baseline
```

### Status

✅ IMPLEMENTED

---

## Backend-Frontend Synchronisation (2026-03-04) — IMPLEMENTED

**Scope:** API-Prefix Migration und Type-Dokumentation

### Änderungen

**Phase 3: API-Prefix Migration**
- Admin-Frontend von `/api/internal/` zu `/api/v1/` mit `apiClient` migriert
- Betroffene Seiten: amenities, extra-services, team, ops/modules, ops/audit-log, notifications/email-outbox
- Standardisiertes Pattern: `useAuth()` → `accessToken` → `apiClient.get/post/patch/delete()`

**Phase 4: Legacy-Feldnamen Dokumentation**
- `@deprecated` Marker in Frontend-Types hinzugefügt
- Semantische Datumsfeldnamen-Konvention dokumentiert:
  - `check_in`/`check_out` → Buchungen
  - `date_from`/`date_to` → Zeiträume (Seasons, Tax Periods)
  - `start_date`/`end_date` → Availability Segments

**Phase 5: Type-Validierung**
- Frontend Build erfolgreich (keine TypeScript-Fehler)

**Phase 6: Dokumentation**
- `conventions.md` aktualisiert (Semantische Feldnamen, API-Prefix Regeln)
- `field-mapping.md` erweitert (Semantik-Erklärung)
- `CHANGELOG.md` aktualisiert

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/amenities/page.tsx` | apiClient Migration |
| `frontend/app/(admin)/extra-services/page.tsx` | apiClient Migration |
| `frontend/app/(admin)/team/page.tsx` | apiClient Migration |
| `frontend/app/(admin)/ops/modules/page.tsx` | apiClient Migration |
| `frontend/app/(admin)/ops/audit-log/page.tsx` | apiClient Migration |
| `frontend/app/(admin)/notifications/email-outbox/page.tsx` | apiClient Migration |
| `frontend/app/types/availability.ts` | @deprecated Marker |
| `frontend/app/types/owner.ts` | @deprecated Marker |
| `frontend/app/types/pricing.ts` | Dokumentation |
| `frontend/app/types/visitor-tax.ts` | Dokumentation |

### Git Tags

- `pre-sync-phase-3` → vor API-Migration
- `pre-sync-phase-4` → vor Type-Dokumentation
- `pre-sync-phase-5` → vor Validierung
- `pre-sync-phase-6` → vor Dokumentation

### Verification Path

```bash
cd frontend && npm run build  # Keine Fehler
git tag -l | grep pre-sync
```

### Revert

```bash
git reset --hard pre-sync-phase-3  # Zurück vor alle Änderungen
```

### Status

✅ IMPLEMENTED

---

## Architektur-Konsolidierung Phase 2 (2026-03-04) — IMPLEMENTED

**Scope:** Pricing-Struktur Konsolidierung (Non-Breaking)

### Änderungen

1. **Konsolidierte Pricing-Types:** `PricingBreakdown`, `PricingFee`, `PricingTax`, `VisitorTaxDetails`, `BookedExtra`
2. **Type Guards:** `hasPricingBreakdown()`, `hasBookedExtras()` für Runtime-Checks
3. **Helper Functions:** `calculateExtrasTotal()`, `formatCentsAsEuro()`
4. **Wiederverwendbare Komponente:** `PricingBreakdown.tsx` mit Legacy-Fallback
5. **Booking-Detail refaktoriert:** 120+ Zeilen Code durch Komponente ersetzt

### Neue Dateien

| Datei | Inhalt |
|-------|--------|
| `frontend/app/types/pricing.ts` | PricingBreakdown-Types, Type Guards, Helpers |
| `frontend/app/components/booking/PricingBreakdown.tsx` | Wiederverwendbare Pricing-Anzeige |
| `frontend/app/components/booking/index.ts` | Component Exports |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/bookings/[id]/page.tsx` | Verwendet PricingBreakdown-Komponente |

### Verification Path

```bash
cd frontend && npm run build
git tag -l | grep pre-consolidation-phase-2
```

### Revert

```bash
git reset --hard pre-consolidation-phase-2
```

### Status

✅ IMPLEMENTED

---

## Architektur-Konsolidierung Phase 1 (2026-03-04) — IMPLEMENTED

**Scope:** Frontend Type-Bereinigung (Non-Breaking)

### Änderungen

1. **Redundantes Feld entfernt:** `guests_count` aus `Booking` Interface (nicht verwendet)
2. **Union Type bereinigt:** `total_price: string | number` → `total_price: string`
3. **Redundantes Feld entfernt:** `guests` aus `BookingRequest` Interface
4. **Deprecation-Kommentare:** Legacy-Felder markiert für spätere Migration
5. **Zentrale Exports:** `index.ts` mit Konventions-Referenz aktualisiert

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/booking.ts` | Type-Bereinigung, Deprecation-Kommentare |
| `frontend/app/types/index.ts` | Konventions-Referenz, fehlende Exports |

### Verification Path

```bash
cd frontend && npm run build
git tag -l | grep pre-consolidation-phase-1
```

### Revert

```bash
git reset --hard pre-consolidation-phase-1
```

### Status

✅ IMPLEMENTED

---

## Architektur-Konsolidierung Phase 0 (2026-03-04) — IMPLEMENTED

**Scope:** Vorbereitung und Dokumentation für systematische Behebung von Architektur-Inkonsistenzen.

### Problem

Verschiedene Teile der Anwendung wurden mit inkonsistenten Konventionen entwickelt:
- **Feldnamen:** `date_from/date_to` (Public) vs `check_in/check_out` (Admin)
- **Gästezahlen:** `adults/children` (Public) vs `num_adults/num_children` (Admin)
- **Types:** `total_price: string | number` (Frontend) - Union statt eindeutiger Typ
- **Redundanz:** `guests`, `guests_count`, `num_guests` als separate Felder

### Lösung Phase 0

1. **Baseline-Tag:** `pre-consolidation-baseline` erstellt
2. **Konventionen-Dokument:** Verbindliche Namensregeln definiert
3. **Field-Mapping:** Legacy → Standard Zuordnung dokumentiert
4. **Architecture-Skills:** 3 neue Claude-Skills für konsistente Entwicklung

### Neue Dokumentation

| Datei | Inhalt |
|-------|--------|
| `backend/docs/conventions.md` | Verbindliche Namens- und Type-Konventionen |
| `backend/docs/field-mapping.md` | Legacy → Standard Mapping, betroffene Dateien |
| `.claude/skills/architecture/conventions-check.md` | Skill: Konventions-Prüfung vor Code-Änderungen |
| `.claude/skills/architecture/type-sync.md` | Skill: Frontend/Backend Type-Synchronisation |
| `.claude/skills/architecture/api-refactor.md` | Skill: Sichere API-Refaktorisierung |

### Verification Path

```bash
# Baseline-Tag prüfen
git tag -l | grep pre-consolidation

# Dokumentation prüfen
ls -la backend/docs/conventions.md backend/docs/field-mapping.md
ls -la .claude/skills/architecture/
```

### Revert

```bash
git reset --hard pre-consolidation-baseline
```

### Status

✅ IMPLEMENTED

---

## Buchungslogik: no_show Status-Transition (2026-03-04) — IMPLEMENTED

**Scope:** Erweiterung der Buchungs-State-Machine um Transition `confirmed → no_show`.

### Problem

Der Status `no_show` war als Terminal-Status definiert, aber nicht von `confirmed` erreichbar. Wenn ein Gast mit bestätigter Buchung nicht erscheint, konnte der Status nicht korrekt gesetzt werden.

### Lösung

`VALID_TRANSITIONS` in `backend/app/services/booking/update.py` erweitert:

```python
# Vorher
"confirmed": ["checked_in", "cancelled"],

# Nachher
"confirmed": ["checked_in", "cancelled", "no_show"],
```

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/booking/update.py:31` | `no_show` zu confirmed-Transitions hinzugefügt |

### Verification Path

```bash
# Backend-Test (wenn vorhanden)
pytest backend/tests/services/booking/ -v -k "no_show"

# Manueller Test via API
curl -X PATCH /api/v1/bookings/{id}/status -d '{"status": "no_show"}'
# → Sollte bei confirmed Booking funktionieren
```

### Status

✅ IMPLEMENTED (Commit `70fac5d`)

---

## Security Fix: NPM minimatch ReDoS (2026-03-03) — IMPLEMENTED

**Scope**: Behebung einer High-Severity Vulnerability in der Frontend-Dependency `minimatch`.

### Problem

- **CVE:** GHSA-7r86-cg39-jmmj, GHSA-23c5-xmqv-rm74
- **Severity:** HIGH (CVSS 7.5)
- **Betroffene Versionen:** minimatch <=3.1.3 und 9.0.0-9.0.6
- **Risiko:** ReDoS (Regular Expression Denial of Service) durch speziell gestaltete Glob-Patterns

### Lösung

```bash
cd frontend && npm audit fix
```

### Geänderte Versionen

| Package | Vorher | Nachher |
|---------|--------|---------|
| minimatch | 3.1.3 | 3.1.5 |
| minimatch | 9.0.6 | 9.0.9 |
| brace-expansion | 5.0.3 | 2.0.2 |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/package-lock.json` | Dependency-Updates |

### Verification Path

```bash
cd frontend && npm audit
# → found 0 vulnerabilities
```

### Status

✅ IMPLEMENTED (Commit `6f707e6`)

---

## A-03: Dependency Injection statt Lazy Imports (2026-03-03) — IMPLEMENTED

**Scope:** Umstellung der BookingService Sub-Services von Lazy Imports auf Dependency Injection (DI) für bessere Testbarkeit und Code-Qualität.

### Problem

Die Booking-Sub-Services (`create.py`, `update.py`, `cancellation.py`) verwendeten eine "Lazy Import"-Hilfsfunktion in `utils.py`, um zirkuläre Imports zu vermeiden:

```python
# Alter Pattern in utils.py
_availability_service = None
def get_availability_service(db):
    global _availability_service
    if _availability_service is None:
        from app.services.availability_service import AvailabilityService
        _availability_service = AvailabilityService(db)
    return _availability_service
```

Dieser Pattern hat mehrere Nachteile:
- Globaler Zustand erschwert Unit-Tests
- Versteckte Abhängigkeiten (nicht im Konstruktor sichtbar)
- Potentielle Connection-Mismatch-Probleme

### Lösung: Dependency Injection

1. **Service-Konstruktoren**: `availability_service` wird jetzt explizit im Konstruktor übergeben
2. **FastAPI Depends()**: Neue Provider in `deps.py` für automatische DI in Routes
3. **TYPE_CHECKING Pattern**: Vermeidet zirkuläre Imports zur Laufzeit

```python
# Neuer Pattern in deps.py
def get_booking_service(db: asyncpg.Connection = Depends(get_db_authed)):
    availability_service = AvailabilityService(db)
    return BookingService(db, availability_service)

# Route-Usage
@router.post("/bookings")
async def create_booking(
    service: BookingService = Depends(get_booking_service)
):
    ...
```

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/booking/create.py` | Konstruktor: `availability_service` Parameter |
| `backend/app/services/booking/update.py` | Konstruktor: `availability_service` Parameter |
| `backend/app/services/booking/cancellation.py` | Konstruktor: `availability_service` Parameter |
| `backend/app/services/booking/service.py` | Facade akzeptiert & delegiert `availability_service` |
| `backend/app/services/booking/utils.py` | Lazy-Import-Helper entfernt |
| `backend/app/services/booking/__init__.py` | Export-Liste aktualisiert |
| `backend/app/services/booking_service.py` | Re-Export aktualisiert |
| `backend/app/api/routes/bookings.py` | Routes nutzen `Depends(get_booking_service)` |
| `backend/app/api/deps.py` | `get_booking_service` & `get_availability_service` Provider |

### Bugfix während Refactoring

Die Route `update_booking_status` hatte einen Signatur-Mismatch (aufruf mit `updated_by_user_id`, `notes` statt `role`). Dies wurde korrigiert.

### Hotfix: skip_availability_check Parameter (628f0ef)

Nach dem initialen Deploy trat ein TypeError auf:
```
BookingCreateService.create_booking() takes from 3 to 4 positional arguments but 5 were given
```

**Ursache:** Die Facade `BookingService.create_booking()` übergab `skip_availability_check` an den Sub-Service, aber `BookingCreateService.create_booking()` akzeptierte diesen Parameter nicht.

**Fix:** Parameter `skip_availability_check: bool = False` zu `BookingCreateService.create_booking()` hinzugefügt und in der Availability-Check-Logik verwendet.

### Verification Path

```bash
# Syntaxprüfung
python -m py_compile backend/app/services/booking/service.py
python -m py_compile backend/app/api/routes/bookings.py

# Smoke Test (nach Deploy)
./backend/scripts/pms_smoke_bookings.sh
```

### Status

✅ IMPLEMENTED (Commit b45f0aa, Hotfix 628f0ef, fd94776)

---

## Bugfix: Status-Update idempotent + Zahlungsdetails (2026-03-03) — IMPLEMENTED

**Scope:** Zwei Bugs bei der Buchungsverwaltung behoben.

### Bug 1: Status-Update warf Fehler bei idempotenten Aufrufen

**Problem:** Wenn eine Buchung bereits den gewünschten Status hatte (z.B. "confirmed -> confirmed"), warf die State Machine einen ValidationException statt den aktuellen Zustand zurückzugeben.

**Ursache:** Die `VALID_TRANSITIONS` Map erlaubte keine "same status" Transitionen.

**Fix:** Idempotenz-Check vor der Transition-Validierung:
```python
# Idempotent: If already at target status, return current booking
if current_status == new_status:
    return await self._get_booking_dict(booking_id, agency_id)
```

### Bug 2: Zahlungsdetails zeigten keine Aufschlüsselung

**Problem:** Bei neuen Buchungen wurden Endreinigung, Servicegebühr, Steuern und Zusatzleistungen als 0,00 € angezeigt, obwohl der Gesamtpreis korrekt war.

**Ursache:**
1. Frontend sendete nur `total_price`, nicht die einzelnen Preiskomponenten
2. Ausgewählte Zusatzleistungen (`selectedExtras`) wurden nicht an Backend gesendet

**Fix (Frontend):**
- Alle Quote-Preise (nightly_rate, subtotal, cleaning_fee, service_fee, tax_amount) werden im Payload gesendet
- Ausgewählte Extras werden in `channel_data.booked_extras` als JSON gespeichert
- Buchungsdetail-Seite zeigt `booked_extras` an

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/booking/update.py` | Idempotenz-Check hinzugefügt |
| `frontend/app/(admin)/bookings/page.tsx` | Quote-Preise + Extras im Payload |
| `frontend/app/(admin)/bookings/[id]/page.tsx` | Extras-Anzeige in Zahlungsdetails |

### Hinweis: Technische Schulden

Die Extras werden aktuell als JSON in `channel_data.booked_extras` gespeichert.
Für eine saubere Lösung sollte eine `booking_extra_services` Junction-Tabelle erstellt werden.
Dies ist als zukünftige Verbesserung markiert.

### Status

✅ IMPLEMENTED (Commit fd94776)

---

## Security Fix: defusedxml als Hard-Requirement (M-03) (2026-03-03) — IMPLEMENTED

**Scope**: Entfernung des unsicheren Fallbacks auf `xml.etree.ElementTree` bei fehlendem `defusedxml`.

### Problem

- `defusedxml` war als optional behandelt (try/except ImportError)
- Bei fehlendem `defusedxml` Fallback auf unsichere Standard-Library
- Standard `xml.etree.ElementTree` ist anfällig für XXE (XML External Entity) Attacken
- SVG-Uploads könnten lokale Dateien lesen oder SSRF auslösen

### Vorher (unsicher)

```python
# file_validator.py / branding.py
try:
    import defusedxml.ElementTree as ET
    DEFUSEDXML_AVAILABLE = True
except ImportError:
    import xml.etree.ElementTree as ET  # ← XXE-verwundbar!
    DEFUSEDXML_AVAILABLE = False
```

### Lösung

Fallback entfernt, defusedxml ist jetzt REQUIRED. App startet nicht ohne (Fail Fast).

```python
# SECURITY: defusedxml is REQUIRED for XXE attack prevention in SVG uploads.
# Do NOT make this optional - the app should fail to start if defusedxml is missing.
import defusedxml.ElementTree as ET
```

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/file_validator.py` | Optional-Import → Direct Import |
| `backend/app/api/routes/branding.py` | Optional-Import → Direct Import + Fallback entfernt |

### Verification Path

```bash
# App startet nur mit defusedxml
python -c "from app.services.file_validator import sanitize_svg; print('OK')"
python -c "from app.api.routes.branding import sanitize_svg; print('OK')"

# Bei fehlendem defusedxml → ImportError (gewünscht)
pip uninstall defusedxml -y && python -c "from app.services.file_validator import sanitize_svg"
# → ImportError: No module named 'defusedxml'
```

### Status

✅ IMPLEMENTED

---

## Architecture Fix: Module-System vervollständigen (A-01) (2026-03-03) — IMPLEMENTED

**Scope**: Entfernung des FAILSAFE-Codes durch Migration aller Router ins Module-System.

### Problem

- ~150 Zeilen FAILSAFE-Code in `main.py` mounteten Router manuell
- 8 Router hatten keine entsprechenden Module
- Doppelte Mount-Logik und unklare Verantwortlichkeiten
- Inkonsistente Architektur

### Lösung

8 neue Module erstellt und FAILSAFE-Code entfernt:

| Neues Modul | Router | Prefix |
|-------------|--------|--------|
| `public_site` | public_site.router + agency_domain_router | `/api/v1/public` |
| `public_domain_admin` | public_domain_admin.router | `/api/v1/public-site` |
| `roles` | roles.router | `/api/v1` |
| `visitor_tax` | visitor_tax.router | `/api/v1` |
| `cancellation_policies` | cancellation_policies.router | `/api/v1` |
| `analytics` | analytics.router | `/api/v1` |
| `block_templates` | block_templates.router | `/api/v1/website` |
| `public_root_meta` | public_root_meta.router | `/` (root) |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/modules/public_site.py` | NEU - Modul erstellt |
| `backend/app/modules/public_domain_admin.py` | NEU - Modul erstellt |
| `backend/app/modules/roles.py` | NEU - Modul erstellt |
| `backend/app/modules/visitor_tax.py` | NEU - Modul erstellt |
| `backend/app/modules/cancellation_policies.py` | NEU - Modul erstellt |
| `backend/app/modules/analytics.py` | NEU - Modul erstellt |
| `backend/app/modules/block_templates.py` | NEU - Modul erstellt |
| `backend/app/modules/public_root_meta.py` | NEU - Modul erstellt |
| `backend/app/modules/bootstrap.py` | +8 Import-Blöcke |
| `backend/app/main.py` | -147 Zeilen FAILSAFE-Code |

### Verification Path

```bash
# 1. App startet
curl https://api.pms.../api/v1/health

# 2. Alle Endpoints erreichbar
curl https://api.pms.../api/v1/public/site/settings
curl https://api.pms.../api/v1/permissions
curl https://api.pms.../api/v1/visitor-tax/locations
curl https://api.pms.../api/v1/cancellation-policies
curl https://api.pms.../api/v1/analytics/vitals
curl https://api.pms.../api/v1/website/block-templates
curl https://api.pms.../robots.txt
```

### Rollback

```bash
git revert HEAD
```

### Status

✅ IMPLEMENTED

---

## Security Fix: Smoke Auth Bypass Default (M-01) (2026-03-03) — IMPLEMENTED

**Scope**: Änderung des Defaults für den Smoke Test Auth Bypass von "aktiviert" auf "deaktiviert".

### Problem

- `SMOKE_AUTH_BYPASS_ENABLED` war standardmäßig aktiviert (opt-out)
- Erlaubte Admin-Bypass mit `x-pms-smoke: 1` Header + JWT
- Production war nur sicher wenn explizit `SMOKE_AUTH_BYPASS_ENABLED=false` gesetzt

### Lösung

Default von opt-out auf opt-in geändert:

```typescript
// Vorher (unsicher):
const smokeBypassEnabled = process.env.SMOKE_AUTH_BYPASS_ENABLED !== 'false';

// Nachher (sicher):
const smokeBypassEnabled = process.env.SMOKE_AUTH_BYPASS_ENABLED === 'true';
```

### Auswirkung

| Umgebung | Vorher | Nachher |
|----------|--------|---------|
| Production (kein Env-Var) | Aktiviert ❌ | Deaktiviert ✅ |
| Dev/Staging | `=true` setzen | `=true` setzen |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/middleware.ts` | Default auf `=== 'true'` geändert |
| `backend/docs/ops/runbook/40-rate-limiting-security.md` | Dokumentation aktualisiert |

### Status

✅ IMPLEMENTED (Commit `7259328`)

---

## Security Fix: SECURITY DEFINER search_path (M-02) (2026-03-03) — VERIFIED

**Scope**: Hinzufügen von `SET search_path = ''` zu SECURITY DEFINER Funktionen ohne expliziten Pfad.

### Problem

- 4 SECURITY DEFINER Funktionen hatten keinen expliziten `search_path`
- Potentielles Risiko für search_path injection attacks
- SECURITY DEFINER läuft mit Owner-Rechten (postgres) - wie sudo

### Betroffene Funktionen

| Funktion | Zweck |
|----------|-------|
| `encrypt_pii` | PII-Verschlüsselung |
| `decrypt_pii` | PII-Entschlüsselung |
| `user_has_permission` | Permission-Check |
| `get_user_permissions` | Permission-Liste |

### Lösung

Migration `20260303183211_fix_security_definer_search_path.sql`:
- `SET search_path = ''` zu allen 4 Funktionen hinzugefügt
- Tabellennamen voll qualifiziert (`public.table_name`)

### Verification (DB-Abfrage nach Migration)

```
function_name        | config_options
---------------------|---------------
decrypt_pii          | search_path=""
encrypt_pii          | search_path=""
get_user_permissions | search_path=""
user_has_permission  | search_path=""
```

### Nicht betroffene Funktionen

- `st_estimatedextent` (3x) - PostGIS System-Funktionen, nicht anfassen
- `end_user_session`, `end_all_user_sessions`, `get_user_agency_ids`, `get_user_role_in_agency`, `user_has_agency_access` - bereits mit `search_path=public`

### Status

✅ VERIFIED (Commit `12c7bce`, Migration ausgeführt 2026-03-03)

---

## Security: CSP unsafe-inline Dokumentation (H-02) (2026-03-03) — ACCEPTED RISK

**Scope**: Dokumentation der CSP-Konfiguration mit `unsafe-inline` als akzeptiertes Risiko.

### Aktuelle CSP-Konfiguration

```
default-src 'self'
script-src 'self' 'unsafe-inline' 'unsafe-eval'
style-src 'self' 'unsafe-inline'
img-src 'self' data: blob: https://*.supabase.co ...
connect-src 'self' https://*.supabase.co ...
frame-ancestors 'none'
form-action 'self'
base-uri 'self'
object-src 'none'
```

### Warum unsafe-inline erforderlich ist

| Direktive | Grund |
|-----------|-------|
| `script-src 'unsafe-inline'` | Next.js 15 injiziert Hydration-Scripts ohne Nonce-Support |
| `script-src 'unsafe-eval'` | Next.js Development-Modus, Hot Reload |
| `style-src 'unsafe-inline'` | Tailwind CSS, dynamische Styles |

### Next.js 15 Limitation

- Next.js 15 unterstützt **keine automatischen Nonces** für interne Scripts
- Ohne `unsafe-inline` blockiert CSP alle Next.js Hydration-Scripts
- Die App würde nicht funktionieren (keine Interaktivität)
- Siehe: [Next.js CSP Docs](https://nextjs.org/docs/app/building-your-application/configuring/content-security-policy)

### Kompensierende Maßnahmen

Trotz `unsafe-inline` sind folgende Schutzmaßnahmen aktiv:

| Header | Wert | Schutz gegen |
|--------|------|--------------|
| `frame-ancestors 'none'` | Entspricht X-Frame-Options: DENY | Clickjacking |
| `form-action 'self'` | Nur eigene Domain | Form Hijacking |
| `base-uri 'self'` | Nur eigene Domain | Base Tag Injection |
| `object-src 'none'` | Keine Plugins | Flash/Java Exploits |
| `X-Content-Type-Options` | nosniff | MIME Sniffing |
| `X-Frame-Options` | DENY | Clickjacking (Legacy) |
| `Strict-Transport-Security` | max-age=31536000 | Downgrade Attacks |

### Risikobewertung

| Aspekt | Bewertung |
|--------|-----------|
| **CVSS** | 6.1 (Medium) |
| **Wahrscheinlichkeit** | Niedrig - erfordert andere Schwachstelle (z.B. XSS via User Input) |
| **Impact** | Mittel - Script-Injection möglich wenn XSS-Lücke existiert |
| **Akzeptanz** | ✅ Akzeptiert - Next.js Framework-Limitation |

### Zukunft: Nonce-Support

Wenn Next.js vollständigen Nonce-Support implementiert:

1. `unsafe-inline` aus `script-src` entfernen
2. Nonce-basierte CSP aktivieren: `script-src 'self' 'nonce-{random}'`
3. Middleware generiert bereits Nonces (vorbereitet)

**Tracking**: Next.js GitHub Issues beobachten für Nonce-Support in App Router.

### Betroffene Dateien

| Datei | Beschreibung |
|-------|--------------|
| `frontend/middleware.ts` | CSP-Header-Generierung |
| `CLAUDE.md` § 11 | CSP-Dokumentation für Entwickler |

### Status

✅ ACCEPTED RISK (dokumentiert 2026-03-03)

---

## AdminShell Refactoring: Modulare Architektur (2026-03-03) — IMPLEMENTED

**Scope**: Refactoring der monolithischen AdminShell.tsx (1979 Zeilen) in modulare Sub-Komponenten.

### Problem (vorher)

- AdminShell.tsx war mit 1979 Zeilen zu groß für effektive Wartung
- Alle Verantwortlichkeiten (Navigation, State, Layout, Dropdowns) in einer Datei
- Schwierig zu testen und zu debuggen
- Code-Reviews kompliziert durch Dateigröße

### Lösung: Modulare Architektur

Extraktion in fokussierte Sub-Komponenten:

| Komponente | Zeilen | Verantwortlichkeit |
|------------|--------|-------------------|
| nav-config.ts | 272 | Navigation-Konfiguration, Typen, Helper |
| SidebarNavigation.tsx | 837 | Desktop-Sidebar mit Flyouts |
| MobileDrawer.tsx | 461 | Mobile Navigation-Drawer |
| TopBar.tsx | 202 | Header mit Language/Notifications |
| ProfileDropdown.tsx | 227 | Benutzer-Menü |
| AdminShell.tsx | 543 | Orchestrierung (↓73%) |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/components/AdminShell.tsx` | REDUZIERT: 1979 → 543 Zeilen |
| `frontend/app/components/admin-shell/nav-config.ts` | NEU |
| `frontend/app/components/admin-shell/SidebarNavigation.tsx` | NEU |
| `frontend/app/components/admin-shell/MobileDrawer.tsx` | NEU |
| `frontend/app/components/admin-shell/TopBar.tsx` | NEU |
| `frontend/app/components/admin-shell/ProfileDropdown.tsx` | NEU |
| `frontend/app/components/admin-shell/hooks/useAdminShellState.ts` | NEU (vorbereitet) |

### Beibehaltene Funktionalität

- ✅ Desktop-Navigation mit Collapsible Groups
- ✅ Mobile-Drawer mit Backdrop
- ✅ Favorites-System (localStorage)
- ✅ Language-Switcher
- ✅ ProfileDropdown mit Impersonation
- ✅ CommandPalette-Integration
- ✅ Branding CSS-Variablen
- ✅ ARIA Accessibility

### Verification Path

```bash
cd frontend && npm run build
# → Build erfolgreich, keine TypeScript-Fehler
```

### Status

✅ IMPLEMENTED

**Commits:**
- `b451f61` - nav-config.ts
- `d35de65` - useAdminShellState Hook
- `ab6e8f5` - ProfileDropdown (Type-Fix)
- `9e2bde9` - SidebarNavigation
- `704722a` - MobileDrawer
- `bf168f8` - TopBar

**Runbook:** [44-adminshell-architecture.md](./ops/runbook/44-adminshell-architecture.md)

---

## BookingService Refactoring: Modulare Sub-Services (2026-03-03) — IMPLEMENTED

**Scope**: Refactoring des monolithischen BookingService (2464 Zeilen) in modulare Sub-Services mit Composition Pattern.

### Problem (vorher)

- `booking_service.py` war mit 2464 Zeilen zu groß für effektive Wartung
- Alle Operationen (Query, Create, Update, Cancel) in einer Klasse
- Schwierig zu testen, keine Isolation
- Hohe kognitive Last beim Code-Review

### Lösung: Modulare Architektur mit Composition Pattern

Extraktion in fokussierte Sub-Services:

| Modul | Zeilen | Verantwortlichkeit |
|-------|--------|-------------------|
| utils.py | ~350 | Helper-Funktionen (normalize_*, to_uuid, retry_on_deadlock) |
| query.py | ~440 | BookingQueryService (list, get, check_availability) |
| create.py | ~710 | BookingCreateService (create_booking, guest upsert) |
| update.py | ~730 | BookingUpdateService (status transitions, update) |
| cancellation.py | ~390 | BookingCancellationService (cancel, calculate_refund) |
| service.py | ~300 | BookingService (Orchestrierung, Delegation) |
| booking_service.py | 58 | Backward-Compat Re-Export (↓98%) |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/booking/__init__.py` | NEU: Package-Exports |
| `backend/app/services/booking/utils.py` | NEU: Helper-Funktionen |
| `backend/app/services/booking/query.py` | NEU: Lese-Operationen |
| `backend/app/services/booking/create.py` | NEU: Buchungserstellung |
| `backend/app/services/booking/update.py` | NEU: Status-Updates |
| `backend/app/services/booking/cancellation.py` | NEU: Stornierung |
| `backend/app/services/booking/service.py` | NEU: Hauptklasse |
| `backend/app/services/booking_service.py` | REDUZIERT: 2464 → 58 Zeilen |

### Beibehaltene Funktionalität

- ✅ Alle öffentlichen Methoden identisch
- ✅ Backward-Kompatibilität für bestehende Imports
- ✅ State Machine für Buchungsstatus
- ✅ Double-Booking Prevention
- ✅ Advisory Locks für Concurrent Updates
- ✅ Optimistic Locking mit version-Feld
- ✅ Refund-Berechnung basierend auf Policy

### Import-Patterns

```python
# Empfohlen (neu):
from app.services.booking import BookingService

# Backward-kompatibel (deprecated):
from app.services.booking_service import BookingService
```

### Verification Path

```bash
cd backend
python -m compileall app/services/booking/ -q
python -c "from app.services.booking import BookingService; print('OK')"
python -c "from app.services.booking_service import BookingService; print('OK')"
```

### Status

✅ IMPLEMENTED

**Commits:**
- `83abd7a` - booking/ Ordner + utils.py
- `150514e` - query.py
- `0fc64ad` - create.py
- `c7b364d` - update.py
- `4628259` - cancellation.py
- `5ddcb64` - service.py
- `f13dc74` - booking_service.py Re-Export

**Runbook:** [45-booking-service-architecture.md](./ops/runbook/45-booking-service-architecture.md)

---

## Media Library - Phase 8: Public Bucket für CMS/Website (2026-03-03) — IMPLEMENTED

**Scope**: Umstellung von Signed URLs auf permanente Public URLs für CMS-/Website-Inhalte.

### Problem (vorher)

CMS-Bilder (z.B. Hero-Blocks) waren nach 1 Stunde nicht mehr sichtbar:
- `property-media` Bucket war PRIVAT
- Signed URLs hatten 1h Ablaufzeit
- CMS speicherte URLs in Datenbank → nach 1h ungültig
- Property Showcase funktionierte (API generiert frische URLs)

### Lösung: WordPress/Strapi-Style Public Bucket

Industry-Standard für CMS-Systeme:
- Website-/CMS-Bilder sind öffentlich zugänglich
- Tenant-Isolation über Pfad-Struktur (`agencies/{agency_id}/...`)
- URLs sind permanent, CDN-cacheable, SEO-freundlich

### Was wurde implementiert

1. **Migration** (`20260303080000_make_property_media_bucket_public.sql`)
   - `property-media` Bucket auf public=true gesetzt
   - RLS Policies für public read, auth write/delete
   - Bestehende URLs von signed auf public konvertiert
   - Thumbnails URLs ebenfalls konvertiert

2. **Backend Service** (`media.py`)
   - `_get_signed_url()` → `_get_public_url()` (permanent)
   - `_add_signed_url_to_item()` → `_ensure_public_url()`
   - `upload_to_storage()` gibt direkt public URL zurück

### URL-Format Vergleich

| Typ | URL-Format | Gültigkeit |
|-----|------------|------------|
| Signed (alt) | `/storage/v1/object/sign/...?token=xyz` | 1 Stunde |
| Public (neu) | `/storage/v1/object/public/...` | Permanent |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260303080000_make_property_media_bucket_public.sql` | NEU: Migration |
| `backend/app/services/media.py` | GEÄNDERT: Public URLs statt Signed URLs |
| `backend/app/services/property_service.py` | GEÄNDERT: Public URLs, media_file_id Support |
| `backend/app/schemas/properties.py` | GEÄNDERT: media_file_id Feld hinzugefügt |
| `frontend/app/components/media/MediaGrid.tsx` | GEÄNDERT: pickerMode für Checkbox-Toggle |
| `frontend/app/components/media/MediaModal.tsx` | GEÄNDERT: pickerMode aktiviert |

### Bugfixes (2026-03-03)

1. **500 Error beim Hinzufügen aus Media Library**
   - Problem: Backend erwartete `storage_path`, aber Media Library sendet `media_file_id`
   - Fix: `PropertyMediaCreate` Schema um `media_file_id` erweitert
   - Fix: `add_property_media` verwendet vorhandene `media_file_id` statt neuen Eintrag

2. **Checkbox-Mehrfachauswahl nur mit Cmd-Taste**
   - Problem: Normal-Klick ersetzte Auswahl statt zu togglen
   - Fix: `pickerMode` Prop in MediaGrid - Checkbox immer sichtbar, Klick togglet

3. **Signed URLs in property_service.py**
   - Alle `get_signed_url()` Aufrufe durch Public URLs ersetzt

### Security

- ✅ Tenant-Isolation bleibt (Pfad-basiert)
- ✅ Write/Delete nur für authentifizierte User (RLS)
- ✅ Öffentliche Lesbarkeit ist CMS-Standard

### Verification Path

```bash
# Nach Migration:
# 1. Bucket prüfen (SQL Editor)
SELECT id, name, public FROM storage.buckets WHERE id = 'property-media';
# → public = true

# 2. CMS Hero-Block mit Bild testen
# → Bild bleibt dauerhaft sichtbar (auch nach 1h+)

# 3. URL-Format prüfen
SELECT id, public_url FROM media_files LIMIT 5;
# → URLs enthalten /object/public/
```

---

## Media Library - Phase 1: Backend Foundation (2026-03-02) — IMPLEMENTED

**Scope**:
WordPress-style Media Library für zentrales File-Management mit höchster Sicherheit.

### Was wurde implementiert

1. **Datenbank-Struktur** (Migration: `20260302155624_create_media_tables.sql`)
   - `media_folders`: Ordner mit Tenant-Isolation, Hierarchie via `parent_id`
   - `media_files`: Dateien mit Metadaten, Thumbnails, Audit-Trail
   - `media_audit_log`: Audit-Logging für alle Media-Operationen
   - RLS-Policies für strikte Tenant-Isolation

2. **Backend Services**
   - `file_validator.py`: Magic-Bytes Validierung (KEIN Content-Type Trust!)
   - `image_processor.py`: Thumbnail-Generierung (sm/md/lg) + WebP-Konvertierung
   - `media.py`: Service mit strikter Tenant-Isolation

3. **API Endpoints** (`/api/v1/media`)
   - `POST /upload`: Datei-Upload mit Validierung + Thumbnails
   - `GET /`: Liste mit Pagination + Filter
   - `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`: CRUD
   - `POST /bulk-delete`, `POST /move`: Bulk-Operationen
   - `GET /folders`, `POST /folders`, etc.: Ordner-Management

4. **Sicherheitsfeatures**
   - Magic-Bytes Validierung (PNG, JPEG, WebP, GIF, SVG, PDF, MP4, WebM)
   - SVG Sanitization (Script-Tags, Event-Handler, externe URLs entfernt)
   - XSS-Schutz via Bleach in Pydantic-Schemas
   - Tenant-Isolation auf ALLEN DB-Queries
   - Permission-basierte Zugriffskontrolle
   - Audit-Logging für Upload/Delete

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260302155624_create_media_tables.sql` | NEU: Tabellen + RLS |
| `backend/app/schemas/media.py` | NEU: Pydantic-Schemas mit XSS-Schutz |
| `backend/app/services/file_validator.py` | NEU: Magic-Bytes + SVG-Sanitization |
| `backend/app/services/image_processor.py` | NEU: Thumbnails + WebP |
| `backend/app/services/media.py` | NEU: Media Service |
| `backend/app/api/routes/media.py` | NEU: REST API Endpoints |
| `backend/app/modules/media.py` | NEU: Module-System Integration |
| `backend/app/modules/bootstrap.py` | GEÄNDERT: Media Module Import |
| `backend/app/main.py` | GEÄNDERT: Failsafe Router Registration |

### Verification Path

```bash
# Nach Migration + Deploy:
# 1. Health Check
curl https://api.fewo.kolibri-visions.de/health

# 2. Upload Test (mit Auth Token)
curl -X POST https://api.fewo.kolibri-visions.de/api/v1/media/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.png"

# 3. Liste abrufen
curl https://api.fewo.kolibri-visions.de/api/v1/media \
  -H "Authorization: Bearer $TOKEN"
```

### Nächste Schritte

- Phase 3: ~~ImagePicker Component~~ ✅ (in Phase 2 integriert)
- Phase 4: ~~Image Editor (Crop, Rotate, Flip)~~ ✅
- Phase 5: ~~Admin Media Page~~ ✅
- Phase 6: ~~Unified Media Architecture~~ ✅
- Phase 7: ~~Integration in bestehende Formulare~~ ✅

**Media Library vollständig implementiert!**

---

## Media Library - Phase 6: Unified Media Architecture (2026-03-02) — IMPLEMENTED

**Scope**: WordPress-style zentrale Medien-Architektur - Media Library zeigt ALLE Medien unabhängig vom Upload-Weg.

### Problem (vorher)

1. `property_media` Tabelle war isoliert - Property-Bilder erschienen NICHT in Media Library
2. Media Library zeigte nur direkt hochgeladene Dateien aus `media_files`
3. Zwei getrennte Datenspeicher für gleiche Funktion (Medien)

### Architektur (nachher)

```
┌─────────────────────────────────────────────────────────────────┐
│                     media_files (ZENTRAL)                       │
│  - Alle Medien (Bilder, PDFs, Videos)                          │
│  - WordPress-Stil "Attachment Library"                          │
│  - agency_id für Tenant-Isolation                               │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ FK: media_file_id
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   property_media (Junction)                     │
│  - Verknüpft Properties mit media_files                        │
│  - Enthält property-spezifische Daten (is_cover, sort_order)   │
└─────────────────────────────────────────────────────────────────┘
```

### Was wurde implementiert

1. **Migration** (`20260302180000_unify_media_architecture.sql`)
   - `media_file_id` FK-Spalte zu `property_media` hinzugefügt
   - Bestehende property_media Records in media_files migriert
   - property_media mit neuen media_files Einträgen verknüpft
   - Helper-Funktion `get_property_media_with_files()` erstellt
   - Stats-View `media_migration_stats` für Monitoring

2. **Backend Service Anpassungen**
   - `MediaService.list_files()` fragt nur noch `media_files` ab
   - Signed URL Generierung für private Bucket Files
   - `PropertyService.add_property_media()` erstellt zuerst media_files Eintrag
   - `PropertyService.delete_property_media()` löscht auch aus media_files

3. **Signed URL Support** (für private Buckets)
   - `_get_signed_url()` Methode für Supabase Storage API
   - Automatische URL-Signierung für Property-Medien in list_files()
   - 1h Gültigkeitsdauer für signierte URLs

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260302180000_unify_media_architecture.sql` | NEU: Migration |
| `backend/app/services/media.py` | GEÄNDERT: Signed URLs, Single-Table Query |
| `backend/app/services/property_service.py` | GEÄNDERT: Dual-Insert für neue Uploads |
| `backend/app/api/routes/media.py` | GEÄNDERT: get_current_agency_id Dependency |
| `frontend/app/(admin)/media/page.tsx` | GEÄNDERT: accessToken useEffect Dependency |

### Verification Path

```bash
# Nach Migration:
# 1. Migration Status prüfen (SQL Editor)
SELECT * FROM media_migration_stats;

# 2. Media Library öffnen
# → Sollte Property-Bilder + direkt hochgeladene Dateien zeigen

# 3. Property-Bild hochladen (über Property-Formular)
# → Bild sollte in Media Library erscheinen

# 4. Bild in Media Library hochladen
# → Kann später einer Property zugewiesen werden
```

### Status: ✅ IMPLEMENTED

Migration erfolgreich ausgeführt, 4 Property-Bilder in Media Library sichtbar.
Signed URLs für private Bucket Files implementiert.

---

## Media Library - Phase 6.1: UI Fixes & Signed URL Improvements (2026-03-02) — IMPLEMENTED

**Scope**: Bugfixes für Media Library UI und vollständige Signed-URL-Unterstützung.

### Probleme (vorher)

1. **Thumbnails brechen nach Metadaten-Edit**: Nach Klick auf Alt-Text/Caption Felder wurden Bilder plötzlich gebrochen
2. **Upload-Button verschwindet**: Hydration-Issue - Button sichtbar für Millisekunden, dann weg
3. **Modal transparent**: CSS-Variablen griffen nicht korrekt nach Hydration
4. **Buttons ohne Branding**: Hardcoded Farben statt Admin-Panel CSS-Variablen
5. **Neu hochgeladene Bilder gebrochen**: 400 Bad Request weil private Bucket URLs ohne Signierung

### Fixes implementiert

1. **Signed URLs für ALLE Dateien**
   - `_add_signed_url_to_item()` generiert jetzt URLs für alle Files mit `storage_path`
   - Vorher nur für `"agencies/"` Pfade - Library-Uploads (`{agency_id}/library/...`) fehlten
   - Fix in `create_file()`: Signierte URL wird direkt nach DB-Insert generiert

2. **Floating Action Button (FAB)**
   - Zuverlässiger Upload-Button unten rechts als Fallback
   - Branding-konform: `bg-t-accent hover:bg-t-accent-hover`
   - Position: `bottom-20 lg:bottom-8 right-8`

3. **Modal mit korrektem Background**
   - Overlay: `bg-black/60` (statt problematischer CSS-Variable)
   - Content: `bg-surface-elevated` für Branding-Konformität

4. **Unnötige PATCH-Requests verhindert**
   - `originalFileValues` useRef speichert Initialwerte
   - `handleUpdateFile` prüft auf echte Änderungen vor API-Call

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/media.py` | GEÄNDERT: Signed URLs für alle Files |
| `frontend/app/(admin)/media/page.tsx` | GEÄNDERT: FAB, Modal-Styles, Branding |

### Commits

- `57b91e9`: fix: generate signed URLs for all files in private bucket
- `1c53519`: fix: use branding CSS variables for buttons and modals
- `6547da2`: fix: modal backgrounds with explicit colors instead of CSS variables
- `ee52065`: fix: add floating upload button as reliable alternative

### Verification Path

```bash
# 1. Datei in Media Library hochladen
# → Bild sollte sofort korrekt angezeigt werden (nicht 400 Error)

# 2. Alt-Text/Caption bearbeiten
# → Thumbnail bleibt intakt nach Save

# 3. FAB Button sollte immer sichtbar sein (unten rechts)
```

### Status: ✅ IMPLEMENTED

---

## Media Library - Phase 7: Form Integration (2026-03-02) — IMPLEMENTED

**Scope**: Integration der Media Library in bestehende Formulare via ImagePicker-Komponente.

### Was wurde implementiert

1. **Settings Branding** (`/settings/branding`)
   - Logo-Upload ersetzt durch ImagePicker
   - Favicon-Upload ersetzt durch ImagePicker
   - Vereinfachte Upload-Logik ohne lokale File-Handling

2. **Website Design** (`/website/design`)
   - Logo Light/Dark: ImagePicker statt alte LogoUploadCard
   - Favicon: ImagePicker statt alte FaviconUploadCard
   - LogoUploadCard/FaviconUploadCard Komponenten entfernt

3. **Website SEO** (`/website/seo`)
   - Open Graph Bild: ImagePicker für og_image_url
   - Volle Media Library Unterstützung

4. **Property Media** (`/properties/[id]/media`)
   - Neuer Tab "Bibliothek" für Media-Library-Auswahl
   - Mehrfachauswahl aus Media Library möglich
   - Ausgewählte Bilder werden automatisch mit Property verknüpft

5. **CMS Block Editor** (`/website/pages/[id]`)
   - **Array-Felder**: MediaModal für image-Felder in ArrayItemEditor
     - Beispiel: `offer_cards`, `location_grid` mit Bildern
   - **Single-Felder**: ImagePicker für `backgroundImage`, `image`, etc.
     - Beispiel: `hero_fullwidth.backgroundImage`, `image_text.image`
   - Token-Weitergabe durch Komponentenbaum

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/settings/branding/branding-form.tsx` | ImagePicker für Logo/Favicon |
| `frontend/app/(admin)/website/design/design-form.tsx` | ImagePicker, alte Upload-Komponenten entfernt |
| `frontend/app/(admin)/website/seo/page.tsx` | ImagePicker für OG-Bild |
| `frontend/app/(admin)/properties/[id]/media/page.tsx` | MediaModal für "Bibliothek"-Tab |
| `frontend/app/(admin)/website/components/ArrayItemEditor.tsx` | MediaModal für Array-Image-Felder, Type-Fixes |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | ImagePicker Import, Token-Prop, Image-Field Handling |
| `frontend/app/components/media/MediaModal.tsx` | Solider Hintergrund, Branding-Buttons |
| `frontend/app/components/media/ImagePicker.tsx` | Signed-URL Thumbnail-Fix, Branding-Buttons |
| `backend/app/schemas/block_validation.py` | Image-URL max_length 500→2000 |

### Bugfixes (Post-Integration)

1. **MediaModal durchsichtiger Hintergrund**
   - Problem: `bg-surface-default` war transparent, Inhalt schimmerte durch
   - Fix: `bg-white` für Modal, `bg-gray-50` für Footer

2. **Buttons nicht im Branding**
   - Problem: `bg-accent-primary` statt Tenant-Primärfarbe
   - Fix: `bg-t-primary text-t-primary-fg hover:bg-t-primary-hover`

3. **Block-Bilder: "string_too_long" Fehler**
   - Problem: Signed URLs sind ~700-800 Zeichen, Schema erlaubte nur 500
   - Fix: `max_length=2000` für alle Image-URL-Felder in `block_validation.py`
   - Betroffene Felder: `backgroundImage`, `background_image`, `image` (in OfferCardItem, LocationItem, ImageTextProps)

4. **ImagePicker zeigt keine Thumbnails**
   - Problem: Regex `/\.(jpg|jpeg|png|webp|gif|svg)$/i` erkennt keine URLs mit Query-Parametern
   - Fix: Regex geändert zu `/\.(jpg|jpeg|png|webp|gif|svg)(\?|$)/i`

### Commits

- `e92929e`: feat: Media Library Phase 7 - ImagePicker Integration
- `55e0e8c`: fix: MediaModal solid backgrounds + increase image URL length limits
- `1f0f786`: fix: ImagePicker shows thumbnails + buttons use branding colors

### Verification Path

```bash
# 1. Branding-Seite öffnen
# → Logo/Favicon: Button "Medienbibliothek" öffnet Modal

# 2. Website Design öffnen
# → Logo Light/Dark/Favicon: ImagePicker mit Media-Button

# 3. SEO-Seite öffnen
# → OG-Bild: ImagePicker mit Media-Button

# 4. Property-Media Seite öffnen
# → Tab "Bibliothek" zeigt MediaModal

# 5. CMS Page Editor öffnen
# → Block mit Bild-Feld (z.B. Hero)
# → Feld "Hintergrundbild" zeigt ImagePicker
# → Array-Items (z.B. Offer Cards) zeigen Ordner-Icon für Media-Auswahl
```

### Status: ✅ IMPLEMENTED

---

## Media Library - Phase 4: Image Editor (2026-03-02) — IMPLEMENTED

**Scope**: Bildbearbeitung direkt in der Media Library mit Crop, Rotate und Flip-Funktionen.

### Was wurde implementiert

1. **ImageEditor Component** (`frontend/app/components/media/ImageEditor.tsx`)
   - Vollwertiger Bild-Editor als Modal-Dialog
   - Verwendet `react-image-crop` für Zuschneiden
   - Canvas API für Transformationen

2. **Crop-Funktionen**
   - Freies Zuschneiden oder mit Seitenverhältnis
   - Voreinstellungen: Frei, 1:1, 16:9, 4:3, 3:2, 9:16
   - Visueller Crop-Rahmen mit Handles

3. **Rotation & Spiegelung**
   - 90°-Drehung links/rechts
   - Horizontale Spiegelung
   - Vertikale Spiegelung
   - Kombinierbar

4. **Responsive Design**
   - **Desktop**: Sidebar mit allen Werkzeugen
   - **Mobile**: Tab-Navigation (Zuschneiden / Drehen & Spiegeln)
   - Optimierte Touch-Bedienung

5. **Speicherung**
   - Bearbeitete Bilder werden als neue Kopie gespeichert
   - Suffix `_edited.jpg` wird angehängt
   - Original bleibt unverändert

### Integration

- **Media Library Page** (`/media`)
  - "Bearbeiten"-Button im FileDetailsPanel (nur für Bilder)
  - Verfügbar in Desktop-Sidebar und Mobile-Bottom-Sheet

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/components/media/ImageEditor.tsx` | NEU: Image Editor Component |
| `frontend/app/components/media/index.ts` | Export hinzugefügt |
| `frontend/app/(admin)/media/page.tsx` | ImageEditor Integration |
| `frontend/package.json` | react-image-crop Dependency |

### Commits

- `295e7ab`: feat: add ImageEditor component for media library (Phase 4)

### Verification Path

```bash
# 1. Media Library öffnen (/media)
# 2. Bild anklicken → Details-Panel öffnet
# 3. "Bearbeiten" Button klicken
# 4. Im Editor:
#    - Seitenverhältnis wählen → Crop-Rahmen erscheint
#    - Drehen/Spiegeln testen
#    - "Als Kopie speichern" klicken
# 5. Neues Bild mit "_edited" Suffix erscheint in Library
```

### Status: ✅ IMPLEMENTED

---

## Media Library - Phase 6.2: Responsive Design & UX Improvements (2026-03-02) — IMPLEMENTED

**Scope**: Responsive Design, Verschieben-Funktion, UI-Verbesserungen.

### Neue Features

1. **Responsive Design**
   - Mobile: Ordner-Sidebar als Slide-In Overlay
   - Mobile: Datei-Details als Bottom Sheet
   - Mobile: Vereinfachte Toolbar mit Wrap
   - Breakpoint: `md` (768px)

2. **Verschieben-Funktion**
   - Dateien können zwischen Ordnern verschoben werden
   - Bulk-Move für mehrere ausgewählte Dateien
   - Dialog mit Ordner-Hierarchie zur Auswahl

3. **Grid/Listen-Ansicht**
   - Toggle zwischen Grid und List View
   - Listen-Ansicht mit Spalten: Name, Typ, Größe, Datum

4. **Inline-Bestätigungsdialoge**
   - Browser `confirm()` durch Inline-Modals ersetzt
   - Einheitliches Design für alle Lösch-Aktionen

### UI-Korrekturen

1. **Folder-Icon statt Hamburger**
   - Ordner-Sidebar Button verwendet jetzt Folder-Icon
   - Unterscheidbar vom globalen Navigation-Hamburger

2. **Topbar Mobile Logo entfernt**
   - Logo war redundant (bereits in Navigation sichtbar)
   - Topbar ist jetzt aufgeräumter

3. **Logo Shadow Fallbacks entfernt**
   - Gecancelte Gradient-Funktion komplett entfernt
   - Kein oranger Schatten mehr als Fallback

4. **Solide Hintergründe**
   - Mobile Sidebar: Explizit weiß statt CSS-Variable
   - Mobile Bottom Sheet: Explizit weiß

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/media/page.tsx` | Responsive, Move, ViewMode, Inline-Modals |
| `frontend/app/components/media/MediaGrid.tsx` | Grid + List View Support |
| `frontend/app/components/AdminShell.tsx` | Logo/Shadow entfernt |

### Commits

- `f194dc0`: fix: replace browser confirm() with inline confirmation modal
- `e336de6`: feat: Medienbibliothek - responsive design, Verschieben-Funktion, deutsche Bezeichnung
- `308e1a5`: fix: Medienbibliothek - solid backgrounds, viewMode toggle working
- `c37dac9`: fix: remove topbar mobile logo, remove logo shadow fallbacks, use Folder icon

### Verification Path

```bash
# Mobile (< 768px):
# 1. Folder-Icon öffnet Ordner-Sidebar (Slide-In)
# 2. Bild anklicken zeigt Bottom Sheet
# 3. Topbar zeigt KEIN Logo mehr

# Desktop:
# 1. Grid/List Toggle funktioniert
# 2. Dateien auswählen → Verschieben-Button → Ordner wählen
# 3. Logo hat keinen orangenen Schatten
```

### Status: ✅ IMPLEMENTED

---

## Media Library - Phase 5: Admin Page (2026-03-02) — IMPLEMENTED

**Scope**: Vollständige Admin-Seite für Medienverwaltung unter `/media`.

### Was wurde implementiert

1. **Admin Media Page** (`frontend/app/(admin)/media/page.tsx`)
   - Vollbild-Layout mit Sidebar (Ordner) und Content (Grid)
   - Upload-Dialog mit Drag & Drop
   - File Details Sidebar mit Metadaten-Bearbeitung
   - Bulk-Operationen (Multi-Select, Löschen)
   - Search & Filter (Typ, Suche)
   - View Mode Toggle (Grid/List - List noch TODO)

2. **Navigation Integration**
   - Neuer Nav-Link "Medien" unter Website-Sektion
   - Übersetzungen (DE/EN) hinzugefügt
   - Icon: ImageIcon von Lucide

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/media/page.tsx` | NEU: Admin Page |
| `frontend/app/components/AdminShell.tsx` | GEÄNDERT: Media Nav-Link |
| `frontend/app/lib/i18n/translations/de.json` | GEÄNDERT: +nav.media |
| `frontend/app/lib/i18n/translations/en.json` | GEÄNDERT: +nav.media |

### Verification Path

```bash
# Frontend Build
cd frontend && npm run build

# Navigate to /media in Admin UI
# - Folder Tree should load
# - Upload button should work
# - File selection + details should work
```

---

## Media Library - Phase 2: Frontend Components (2026-03-02) — IMPLEMENTED

**Scope**: Core Frontend Components für Media Library UI.

### Was wurde implementiert

1. **TypeScript Types** (`frontend/app/types/media.ts`)
   - MediaFile, MediaFolder, MediaFolderTree Interfaces
   - Helper-Funktionen (formatFileSize, getFileTypeIcon)
   - Konstanten für Dateitypen und Größenlimits

2. **API Client** (`frontend/app/lib/api/media.ts`)
   - uploadFile mit Progress-Tracking
   - listFiles, getFile, updateFile, deleteFile
   - Folder-Operationen (list, tree, create, delete)
   - bulkDeleteFiles, moveFiles

3. **Core Components** (`frontend/app/components/media/`)
   - **MediaGrid**: Grid-Ansicht mit Multi-Selection (Shift/Ctrl-Click)
   - **MediaModal**: Dialog zum Durchsuchen/Auswählen mit Tabs
   - **FolderTree**: Hierarchische Navigation mit Context-Menu
   - **MediaUploader**: Drag & Drop mit Progress-Anzeige
   - **ImagePicker**: Ersatz für URL-Eingabefelder

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/media.ts` | NEU: TypeScript Types |
| `frontend/app/lib/api/media.ts` | NEU: API Client |
| `frontend/app/components/media/MediaGrid.tsx` | NEU: Grid Component |
| `frontend/app/components/media/MediaModal.tsx` | NEU: Modal Component |
| `frontend/app/components/media/FolderTree.tsx` | NEU: Folder Navigation |
| `frontend/app/components/media/MediaUploader.tsx` | NEU: Upload Component |
| `frontend/app/components/media/ImagePicker.tsx` | NEU: Image Picker |
| `frontend/app/components/media/index.ts` | NEU: Re-exports |

### Verification Path

```bash
# TypeScript-Compilation prüfen
cd frontend && npm run build

# Component-Import testen
# In beliebiger Admin-Seite:
# import { ImagePicker } from '@/app/components/media';
```

---

## Organisations-Kontaktdaten & Topbar-Erweiterung (2026-03-02) — IMPLEMENTED

**Scope**:
1. Organisation-Seite um Telefon, Adresse und Social Media Links erweitern
2. Topbar-Konfiguration mit individuellen Social Media Items und Layout-Optionen
3. **Fix**: Tenant-Resolution für Server-Side Fetches

### Problem (vorher)

1. Die Organisation-Seite (`/organization`) hatte nur Name und E-Mail - keine Telefon, Adresse oder Social Media Links
2. Die Topbar zeigte alle Social Media Links als Block - keine individuelle Steuerung
3. Kontaktdaten waren in `public_site_settings` und `agencies` dupliziert
4. **Bug**: Server-Side Fetches sendeten keinen Host-Header → Backend konnte Tenant nicht auflösen

### Lösung (nachher)

#### 1. Organisation als Single Source of Truth

| Feld | Tabelle | Beschreibung |
|------|---------|--------------|
| `phone` | `agencies` | Telefonnummer |
| `address` | `agencies` | Vollständige Adresse |
| `social_links` | `agencies` | JSONB mit Social Media URLs |

Die Public Website liest diese Daten jetzt aus der `agencies` Tabelle (JOIN).

#### 3. Fix: Tenant-Resolution für Server-Side Rendering

Das Problem: Wenn Next.js Server-Side fetches an das Backend macht, geht der Request an `api.fewo.kolibri-visions.de` statt an die Public-Domain `fewo.kolibri-visions.de`. Das Backend konnte daher den Tenant nicht aus dem Host-Header auflösen.

**Lösung**: Die API-Helpers in `api.ts` lesen jetzt den Original-Host aus dem eingehenden Request (`headers()`) und senden ihn als `x-public-host` Header an das Backend weiter.

#### 2. Erweiterte Topbar-Konfiguration

| Funktion | Beschreibung |
|----------|--------------|
| **Individual Social Items** | `social_facebook`, `social_instagram`, `social_twitter`, `social_youtube`, `social_linkedin` |
| **Layout: Gap** | Abstand zwischen Elementen: `sm` (16px), `md` (24px), `lg` (32px) |
| **Layout: Gruppen** | Jedes Element kann in `left`, `center` oder `right` Gruppe platziert werden |
| **Separator** | Optionale Trennlinie zwischen Gruppen |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260302000000_add_topbar_config.sql` | GEÄNDERT: gap, individuelle Social Items |
| `supabase/migrations/20260302120000_add_agency_contact_fields.sql` | NEU: address, social_links für agencies |
| `supabase/migrations/20260302140000_add_topbar_item_groups.sql` | NEU: group Feld für Topbar-Items (left/center/right) |
| `backend/app/schemas/epic_a.py` | GEÄNDERT: AgencyResponse/UpdateRequest mit neuen Feldern |
| `backend/app/api/routes/epic_a.py` | GEÄNDERT: GET/PATCH mit phone, address, social_links |
| `backend/app/api/routes/public_site.py` | GEÄNDERT: JOIN mit agencies für Kontaktdaten |
| `backend/app/schemas/public_site.py` | GEÄNDERT: TopbarConfig mit gap, alignment, neue Item-Typen |
| `frontend/app/types/organisation.ts` | NEU: SOCIAL_PLATFORMS, SocialLinks Interface |
| `frontend/app/(admin)/organization/page.tsx` | GEÄNDERT: Erweitertes Bearbeitungsformular |
| `frontend/app/(public)/context/DesignContext.tsx` | GEÄNDERT: TopbarItemType mit Social-Plattformen |
| `frontend/app/(public)/components/HeaderClient.tsx` | GEÄNDERT: Rendering für individuelle Social Items |
| `frontend/app/(admin)/website/design/design-form.tsx` | GEÄNDERT: Layout-Optionen im TopbarEditor |
| `frontend/app/(public)/lib/api.ts` | GEÄNDERT: Tenant-Resolution via x-public-host Header |

### Datenstruktur

```typescript
// agencies Tabelle
interface Agency {
  phone: string | null;
  address: string | null;
  social_links: {
    facebook?: string;
    instagram?: string;
    twitter?: string;
    youtube?: string;
    linkedin?: string;
    // ...
  };
}

// TopbarConfig
interface TopbarConfig {
  visible: boolean;
  bg_color: string | null;
  text_color: string | null;
  gap: "sm" | "md" | "lg";
  items: TopbarItem[];
}

// TopbarItem
interface TopbarItem {
  id: string;
  type: TopbarItemType;
  visible: boolean;
  position: number;
  group: "left" | "center" | "right";  // Platzierung
  // ...
}
```

### Verification Path

```bash
# 1. Migrationen anwenden
psql -c "SELECT phone, address, social_links FROM agencies LIMIT 1;"
# Erwartung: Neue Spalten vorhanden

# 2. Organisation-Seite testen
# /organization → Bearbeiten → Telefon, Adresse, Social Links editierbar

# 3. Topbar-Editor testen
# /website/design → Topbar → Layout-Optionen (Gap, Ausrichtung) sichtbar
# Individuelle Social-Plattform Items (Facebook, Instagram, etc.)

# 4. Public Website testen
# Nach Deploy: Topbar sollte Telefon + Social Icons anzeigen
# Test: curl -H "x-public-host: fewo.kolibri-visions.de" https://api.fewo.kolibri-visions.de/api/v1/public/site/settings
# Erwartung: phone, social_links sind befüllt
```

**Status:** ✅ IMPLEMENTED

### Sicherheitsentscheidung: CSP (2026-03-02)

Security Headers Scan ergab Grade A. Die `unsafe-inline` Warnung für `script-src` betrifft ausschließlich Next.js-interne Hydration-Scripts, nicht eigenen Code. Nach Evaluierung wurde entschieden, die aktuelle Konfiguration beizubehalten:

- **Entscheidung:** Keine Nonce-Implementierung
- **Begründung:**
  - Grade A bereits erreicht
  - XSS-Schutz durch React automatisch (keine raw HTML Injection)
  - Nonce-Implementierung würde bei Next.js Updates brechen können
  - Komplexität/Nutzen-Verhältnis ungünstig
- **Bestehende Schutzmechanismen:** HSTS, X-Frame-Options, frame-ancestors 'none', CSP

---

## Multiple Root Layouts — SSR Public Website (2026-03-01) — IMPLEMENTED

**Scope**: Root Layout (`app/layout.tsx`) aufgelöst in 4 eigenständige Root Layouts per Route Group für echtes HTML-SSR auf der Public Website.

### Problem (vorher)

Das globale Root Layout wrappte ALLE Routen in `<Providers>` (`"use client"`), was HTML-SSR für die gesamte App verhinderte. Der `<body>` enthielt nur RSC Flight Payload Scripts statt echtem HTML. Zusätzlich hatte die Public Website `<html lang="en">` (falsch) und den Admin-Titel "PMS Channel Sync Console".

### Lösung (nachher)

| Route Group | Root Layout | Providers | Rendering |
|-------------|-------------|-----------|-----------|
| `(public)` | `<html><body>` + DesignProvider | KEINE globalen Providers | SSR/ISR (echtes HTML) |
| `(admin)` | `<html><body>` + Providers + AdminShell | Auth, Permission, Language, Theme | Dynamic (Client) |
| `(auth)` | `<html><body>` minimal | KEINE | Dynamic |
| `(owner)` | `<html><body>` + Providers | Auth, Permission, Language, Theme | Dynamic (Client) |

### Geänderte Dateien

| Datei | Aktion |
|-------|--------|
| `app/fonts.ts` | NEU — Shared Font-Instanz für alle Layouts |
| `app/(public)/layout.tsx` | GEÄNDERT — `<html lang="de"><body>` hinzugefügt, OHNE Providers |
| `app/(admin)/layout.tsx` | GEÄNDERT — `<html lang="de"><body>` + Providers + Metadata hinzugefügt |
| `app/(auth)/layout.tsx` | NEU — Minimales Root Layout für Login |
| `app/(owner)/layout.tsx` | NEU — Root Layout mit Providers für Owner Portal |
| `app/layout.tsx` | GELÖSCHT — Ersetzt durch 4 eigenständige Root Layouts |
| `app/login/` → `app/(auth)/login/` | VERSCHOBEN |
| `app/owner/` → `app/(owner)/owner/` | VERSCHOBEN |
| `app/(public)/components/BlockRenderer.tsx` | FIX — DOMPurify server-safe gemacht |

### Bonus-Fixes (automatisch durch die Trennung)

- `<html lang="en">` → `<html lang="de">` (SEO-Korrektur)
- `title: "PMS Channel Sync Console"` nur noch auf Admin, nicht mehr auf Public
- Public JS-Bundle ~50% kleiner (keine Auth/Permission/Theme Provider)
- DOMPurify server-safe fix für Static Build

### Verification Path

```bash
# 1. Build muss durchlaufen
cd frontend && npm run build
# Erwartung: rc=0, keine "Missing root layout" Warnings

# 2. Public Website — muss echtes HTML enthalten
curl -s https://fewo.kolibri-visions.de/ | grep -o '<header\|<nav\|<footer\|<main'
# Erwartung: HTML-Elemente gefunden

# 3. lang-Attribut korrekt
curl -s https://fewo.kolibri-visions.de/ | grep -o 'lang="[^"]*"' | head -1
# Erwartung: lang="de"

# 4. Login funktioniert
curl -s https://admin.fewo.kolibri-visions.de/login | grep -o '<form\|<input'
```

---

## Public Layout SSR - Server-Side Rendering für Header/Footer (2026-03-01) - IMPLEMENTED

**Scope**: Public Website Layout von Client Component (`"use client"`) zu Server Component umgebaut, damit Header, Navigation und Footer als echtes HTML im SSR-Response enthalten sind.

### Problem (vorher)

Das gesamte Public Layout war ein Client Component mit `useEffect`-basiertem Datenfetching. Der Server lieferte nur leere `<body>`-Tags mit React-Hydration-Scripts. Crawler und Browser sahen keinen Inhalt bis JavaScript geladen und ausgeführt war.

### Lösung (nachher)

| Komponente | Vorher | Nachher |
|------------|--------|---------|
| `layout.tsx` | `"use client"` + `useEffect` fetch | Server Component + `async/await` fetch |
| Header | Im Layout (client) | Eigene `HeaderClient.tsx` (nur Interaktivität) |
| Footer | Im Layout (client) | Eigene `FooterServer.tsx` (rein Server) |
| `SiteSettings` | Lokales Interface im Layout | Exportiert aus `lib/api.ts` |
| `fetchSiteSettings()` | Nur `{ site_name }` | Vollständiges `SiteSettings`-Interface mit Fallback-Defaults |
| Design-Tokens | Client-Fetch per `useEffect` | Server-Fetch per `fetchDesign()` |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(public)/layout.tsx` | Server Component, kein `"use client"` mehr |
| `frontend/app/(public)/lib/api.ts` | `SiteSettings` Interface + `defaultSiteSettings` + erweiterte `fetchSiteSettings()` |
| `frontend/app/(public)/components/HeaderClient.tsx` | NEU: Client Component nur für Mobile-Menu + Scroll-Detection |
| `frontend/app/(public)/components/FooterServer.tsx` | NEU: Server Component für Footer-Rendering |

### Architektur

```
Server Component (layout.tsx)
  ├── fetchSiteSettings() ─── server-side, cached 5 min
  ├── fetchDesign() ───────── server-side, cached 1 min
  ├── HeaderClient ─────────── "use client" (useState, useEffect)
  │   ├── Mobile menu toggle
  │   └── Scroll detection (sticky shadow)
  ├── DesignProvider ────────── "use client" (Context für Kinder)
  │   └── children (Seiten-Content)
  └── FooterServer ─────────── Server Component (kein JS)
```

### Verification Path

```bash
# 1. SSR HTML prüfen - View Source sollte Header/Nav/Footer zeigen
curl -s https://fewo.example.com | grep -o '<header[^>]*>' | head -1
curl -s https://fewo.example.com | grep -o '<footer[^>]*>' | head -1

# 2. Navigation im SSR-HTML sichtbar
curl -s https://fewo.example.com | grep 'Unterkünfte'

# 3. Build prüft Kompilation (lokal verifiziert, rc=0)
cd frontend && npx next build
```

---

## German Translation Fixes - Website Admin UI (2026-03-01) - IMPLEMENTED

**Scope**: Englische Texte und Variablen-Namen durch deutsche Bezeichnungen ersetzt.

### Änderungen

| Datei | Fix |
|-------|-----|
| `design-form.tsx` | Logo (Hell/Dunkel), Fixierter Header statt Sticky Header |
| `templates/page.tsx` | Block-Vorlagen, Neue Vorlage, korrigierte Umlaute |
| `navigation/page.tsx` | placeholder "Bezeichnung" statt "Label" |
| `filters/page.tsx` | placeholder "Filtername" statt "Filter" |
| `pages/[id]/page.tsx` | FIELD_LABELS Mapping für dynamische Block-Felder |

### Commits

- `cc7c3ff` fix: German translations for website admin UI

### Verification Path

Admin → Website → beliebige Unterseite → Labels prüfen → alle in Deutsch

---

## Block Height Control (min_height_vh) (2026-03-01) - IMPLEMENTED

**Scope**: Einstellbare Mindesthöhe (vh) für alle Design-Blöcke der Public Website.

### Feature

| Komponente | Beschreibung |
|------------|--------------|
| Slider UI | Mindesthöhe-Slider im Styling-Tab (0-100vh) |
| Backend-Validierung | `min_height_vh` Feld in `BlockStyleOverrides` |
| Rendering | Flex-Container für korrekte Höhenausfüllung |

### Funktionsweise

- Wert 0 = automatische Höhe (Standard)
- Wert 1-100 = Mindesthöhe in Viewport-Height-Einheiten (vh)
- Wrapper verwendet Flex-Layout damit innerer Block die Höhe ausfüllt
- Gilt für ALLE Block-Typen (Hero, Section, CTA, etc.)

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/schemas/block_validation.py` | `min_height_vh: Optional[int]` (0-100) |
| `frontend/app/types/website.ts` | Interface erweitert |
| `frontend/app/(admin)/website/lib/block-schemas.ts` | Schema erweitert |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Slider UI im Styling-Tab |
| `frontend/app/(public)/components/BlockRenderer.tsx` | Flex-Wrapper + minHeight Style |

### Commits

- `49305db` feat: add min_height_vh setting for all design blocks
- `391a13d` fix: min_height_vh now properly fills block height

### Verification Path

Admin → Website → Seiten → Block auswählen → Styling-Tab → Mindesthöhe auf 100vh → Speichern → Public Website → Block hat 100vh Höhe

---

## Developer Settings Admin UI (2026-03-01) - IMPLEMENTED

**Scope**: Admin-UI für Website-Entwickler-Einstellungen.

### Features

| Einstellung | Feld | Beschreibung |
|-------------|------|--------------|
| HTML formatieren | `prettify_html` | Generiertes HTML wird formatiert (Debugging) |
| Debug-Modus | `debug_mode` | Zusätzliche Debug-Infos in Konsole |
| Cache deaktivieren | `disable_cache` | Browser-Caching für Entwicklung deaktivieren |

### API-Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/v1/website/developer-settings` | GET | Einstellungen abrufen |
| `/api/v1/website/developer-settings` | PUT | Einstellungen speichern |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/developer/page.tsx` | UI komplett neu implementiert |
| `backend/app/api/routes/website_admin.py` | PUT-Endpoint erweitert mit Pydantic Body |
| `supabase/migrations/20260301132546_add_developer_settings_fields.sql` | NEU: `debug_mode`, `disable_cache` Spalten |
| `frontend/app/components/AdminShell.tsx` | Nav-Eintrag + Code Icon |
| `frontend/app/lib/i18n/translations/de.json` | `nav.developer` |
| `frontend/app/lib/i18n/translations/en.json` | `nav.developer` |

**Verification Path:** Admin → Website → Entwickler → Toggle ändern → Speichern → Seite neu laden → Einstellung persistiert

---

## Domain Management Admin UI (2026-03-01) - IMPLEMENTED

**Scope**: Admin-UI fuer Public Website Domain-Einrichtung.

### Feature

| Komponente | Beschreibung |
|------------|--------------|
| Domain-Eingabe | Input-Feld zum Speichern der eigenen Domain |
| Status-Anzeige | Verifizierungsstatus (verifiziert/pending/nicht konfiguriert) |
| Verifizierung | Button zum Pruefen der Domain-Erreichbarkeit |
| DNS-Anleitung | CNAME/A-Record Setup-Instruktionen |

### API-Endpoints (bereits vorhanden)

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/v1/public-site/domain` | GET | Domain-Status abrufen |
| `/api/v1/public-site/domain` | PUT | Domain speichern |
| `/api/v1/public-site/domain/verify` | POST | Domain verifizieren |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/domain/page.tsx` | NEU: Admin-UI |
| `backend/app/api/routes/public_domain_admin.py` | Backend, bereits vorhanden |
| `frontend/app/components/AdminShell.tsx` | Nav-Eintrag + Globe2 Icon |
| `frontend/app/lib/i18n/translations/de.json` | `nav.domain` |
| `frontend/app/lib/i18n/translations/en.json` | `nav.domain` |

### Verification Path

Admin → Website → Domain → Domain eingeben → Speichern → DNS einrichten → Verifizieren

---

## CMS Bug Fixes (2026-02-28) - IMPLEMENTED

**Scope**: Kritische Fixes nach CMS Phase 8 Deployment.

### Fix 1: TrustIndicatorItem Alias

| Problem | Lösung |
|---------|--------|
| Frontend sendet `text`, Backend erwartet `label` | Pydantic `alias="text"` + `populate_by_name=True` |

**Dateien:**
- `backend/app/schemas/block_validation.py` (TrustIndicatorItem)

**Commit:** `5b48466`

### Fix 2: CTABannerBlock Feldnamen

| Problem | Lösung |
|---------|--------|
| Admin speichert camelCase (`buttonText`), Renderer erwartet snake_case (`cta_text`) | Renderer akzeptiert beide Konventionen |

**Mapping:**
| Admin (camelCase) | Renderer (snake_case) |
|-------------------|----------------------|
| `buttonText` | `cta_text` |
| `buttonLink` | `cta_href` |
| `backgroundColor` | `background_color` |
| `subtitle` | `text` |

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx` (CTABannerBlock)

**Commit:** `e6681f3`

### Fix 3: SEO Endpoint 500 Error (3 Bugs)

| Problem | Lösung |
|---------|--------|
| `get_seo()` ohne `agency_id` aufgerufen | `agency_id=agency_id` Parameter hinzugefügt |
| `.model_dump()` auf dict aufgerufen | `seo_defaults` ist bereits dict nach `model_dump()` |
| asyncpg liefert JSONB als String | `_parse_seo_row()` Helper parst JSON-String zu dict |

**Betroffene Stellen:**
- Zeile 1026: Fallback wenn keine set_clauses
- Zeile 1055: Fallback nach leerem Query-Result
- Zeile 1018: `seo_defaults` ist bereits dict, nicht Pydantic model
- Zeile 979, 1063: `SeoResponse(**dict(row))` → `SeoResponse(**_parse_seo_row(row))`

**Dateien:**
- `backend/app/api/routes/website_admin.py` (get_seo, update_seo, _parse_seo_row)

**Commits:** `964bbe0`, `2459c66`, `7508118`

### Fix 4: Block Templates API

| Problem | Lösung |
|---------|--------|
| `block_templates.py` nutzte nicht existierendes `get_supabase` | Komplett auf asyncpg umgestellt |
| Migration referenzierte `tenants` statt `agencies` | Migration korrigiert |
| Router nicht gemountet bei `MODULES_ENABLED=true` | Failsafe-Mounting in `main.py` |

**Dateien:**
- `backend/app/api/routes/block_templates.py` (Komplettes Rewrite)
- `backend/app/main.py` (Failsafe-Mounting)
- `supabase/migrations/20260228182604_add_block_templates.sql`

**Verification Path:** Admin → Website → Seiten → Block hinzufügen → CTA-Banner → Speichern → Public Site prüfen

### Fix 5: Block Style Overrides nicht angewendet

| Problem | Lösung |
|---------|--------|
| Admin speichert `style_overrides` (snake_case) | Renderer prüft jetzt beide: `styleOverrides` und `style_overrides` |
| Block-Styling (Hintergrund, Padding, etc.) wurde ignoriert | `const styleOverrides = block.styleOverrides || block.style_overrides` |

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx`

**Commit:** `1d64c02`

**Verification Path:** Admin → Website → Seiten → Block → Styling-Tab → Hintergrundfarbe setzen → Speichern → Public Site prüfen (Farbe sichtbar)

### Fix 6: Block-Komponenten überschreiben Wrapper-Styling

| Problem | Lösung |
|---------|--------|
| 10 Blöcke setzten eigene `backgroundColor` auf Main-Container | Hardcoded Background entfernt, Wrapper handled Styling via styleOverrides |
| Wrapper styleOverrides wurden durch inneren Block überdeckt | Blöcke sind jetzt "transparent", Background wird vom Wrapper gesetzt |

**Betroffene Blöcke (alle gefixt):**
- `TrustIndicatorsBlock` ✅
- `SearchFormBlock` ✅
- `OfferCardsBlock` ✅
- `LocationGridBlock` ✅
- `PropertyShowcaseBlock` ✅
- `PropertySearchBlock` ✅
- `TestimonialsBlock` ✅
- `ImageTextBlock` ✅
- `FAQAccordionBlock` ✅
- `ContactSectionBlock` ✅

**Nicht geänderte Blöcke (korrekt):**
- `CTABannerBlock` - behält bgColor aus props (gewolltes Banner-Design)
- Innere Elemente (Cards, Buttons, Icons) - behalten ihre Farben

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx`

**Commits:** `97fc39e`, `81b78ab`

**Verification Path:** Admin → Website → Seiten → beliebigen Block → Styling-Tab → Hintergrundfarbe setzen → Speichern → Public Site prüfen (Block-Hintergrund ist custom Farbe)

### Fix 7: TrustIndicatorsBlock Text nicht sichtbar

| Problem | Lösung |
|---------|--------|
| Admin speichert `item.label` | Renderer akzeptiert jetzt `label` ODER `text` |
| Renderer suchte nur nach `item.text` | `const indicatorText = item.label \|\| item.text` |

**Symptom:** Icons wurden angezeigt, aber Texte wie "4.9/5 Bewertung" fehlten.

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx` (TrustIndicatorsBlock)

**Commit:** `8fe59e1`

**Verification Path:** Admin → Website → Seiten → Vertrauens-Indikatoren Block → Text eingeben → Speichern → Public Site prüfen (Text unter Icons sichtbar)

### Fix 8: Block-Feldnamen Kompatibilität (5 Blöcke)

| Problem | Lösung |
|---------|--------|
| Admin speichert camelCase/andere Feldnamen | Renderer akzeptiert beide Konventionen |
| Blöcke zeigten keine Inhalte | Dual-Naming-Support für alle Array- und Einzelfelder |

**Betroffene Blöcke und Mappings:**

| Block | Admin-Feld | Renderer akzeptiert |
|-------|------------|---------------------|
| **OfferCardsBlock** | `offers` | `offers` ODER `items` |
| | `discount` | `discount` ODER `badge` |
| | `description` | `description` ODER `subtitle` |
| | `image` | `image` ODER `image_url` |
| **LocationGridBlock** | `locations` | `locations` ODER `items` |
| | `image` | `image` ODER `image_url` |
| | `count` | `count` ODER `property_count` |
| **TestimonialsBlock** | `testimonials` | `testimonials` ODER `items` |
| | `text` | `text` ODER `quote` |
| **ImageTextBlock** | `image` | `image` ODER `image_url` |
| | `imagePosition` | `imagePosition` ODER `image_position` |

**Bereits korrekt konfiguriert (keine Änderung nötig):**
- `HeroFullwidthBlock` - hatte schon Dual-Naming
- `FAQAccordionBlock` - `items`, `question`, `answer` stimmen überein
- `ContactSectionBlock` - `phone`, `email` stimmen überein
- `IconBoxWidget` - `icon`, `title`, `description` stimmen überein

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx`

**Commit:** `c67333a`

**Verification Path:** Admin → Website → Seiten → beliebigen Block (z.B. Angebots-Karten, Standort-Raster, Kundenstimmen) → Inhalte eingeben → Speichern → Public Site prüfen (alle Inhalte sichtbar)

### Fix 9: Filter-Konfiguration 500 Error

| Problem | Lösung |
|---------|--------|
| GET/PUT `/api/v1/website/filter-config` liefert 500 | JSON-Parsing für asyncpg JSONB-Felder hinzugefügt |
| asyncpg liefert JSONB als String, Pydantic erwartet dict/list | `_parse_filter_config_row()` Helper parst JSON-Strings |

**Betroffene Felder (JSONB):**
- `filter_order` (List[str])
- `visible_amenities` (Optional[List[str]])
- `available_sort_options` (List[str])
- `labels` (Dict[str, str])

**Dateien:**
- `backend/app/api/routes/website_admin.py` (get_filter_config, update_filter_config, _parse_filter_config_row)

**Commit:** `2eb3211`

**Verification Path:** Admin → Website → Filter → Einstellungen ändern → Speichern (kein 500 Error)

### Fix 10: Horizontaler Filter UX-Verbesserungen

| Problem | Lösung |
|---------|--------|
| Dunkle Eingabefelder (schwer lesbar) | Explizites Light-Styling mit `backgroundColor: #ffffff` |
| Ausstattung-Filter bricht Layout | Kompakter Popover/Dropdown statt inline Checkboxen |

**Änderungen:**
1. **Input-Styling**: Alle Dropdowns/Inputs haben jetzt weiße Hintergründe mit `getInputStyle(design)` Helper
2. **Amenities-Popover**: Im horizontalen Layout zeigt ein Button "X gewählt" an und öffnet ein Dropdown mit Checkboxen

**Vorher:**
```
[Ort ▾] [Gäste ▾] [Schlafzimmer ▾] [Min] [Max]
☐ Einzelbetten
☐ Kamin          ← Bricht das Layout
☐ Mikrowelle
...
```

**Nachher:**
```
[Ort ▾] [Gäste ▾] [Schlafzimmer ▾] [Min] [Max] [Ausstattung (2) ▾]
                                              ↓ Klick öffnet Popover
```

**Dateien:**
- `frontend/app/(public)/components/PropertyFilter.tsx`

**Commit:** `5c90150`

**Verification Path:** Public Site → /unterkuenfte → Horizontaler Filter → Inputs lesbar (weiß), Ausstattung als Dropdown

### Fix 11: Footer voll dynamisch aus Admin-Einstellungen

| Problem | Lösung |
|---------|--------|
| Footer-Spalten hardcodiert (nicht alle Admin-Einstellungen wurden angezeigt) | Dynamisches `FooterColumns` Component iteriert über alle `footer_links` Keys |

**Änderungen:**
1. **FooterColumns Component**: Neue Komponente rendert alle Spalten basierend auf Admin `footer_links`
2. **Keine hardcodierten Spalten**: Statt fester Spalten (Service, Legal, etc.) werden alle Keys aus `footer_links` dynamisch gerendert
3. **Kontakt-Spalte**: Wird nur angezeigt wenn `phone`, `email`, `address` oder `social_links` vorhanden sind
4. **Spalten-Titel Mapping**: `columnTitles` Map übersetzt Keys in deutsche Bezeichnungen (fallback: capitalize)

**Vorher:**
```
[Kontakt] [Reiseziele] [Service] [Rechtliches]
    ↑ Hardcodiert, ignoriert Admin "owner" Spalte
```

**Nachher:**
```
[Kontakt] [Service] [Rechtliches] [Eigentümer] [Reiseziele]
    ↑ Dynamisch aus Admin footer_links, alle Spalten sichtbar
```

**Dateien:**
- `frontend/app/(public)/layout.tsx` (FooterColumns Component)

**Commit:** `7104116`

**Verification Path:** Admin → Website → Einstellungen → Footer Links (z.B. owner Spalte) → Speichern → Public Site Footer prüfen (alle konfigurierten Spalten sichtbar)

---

## CMS Performance & Polish - Phase 8 (2026-02-28) - IMPLEMENTED

**Scope**: Performance-Optimierungen, Skeleton-Loader und Accessibility-Verbesserungen.

### Phase 8.1: Performance-Optimierungen

| Feature | Beschreibung |
|---------|--------------|
| React.memo | Memoized Components: SectionPropsEditor, BlockStyleEditor, SortableWidgetItem |
| useCallback | Clipboard-Funktionen (copyBlock, cutBlock, pasteBlock) |
| Reduced Re-renders | Komponenten werden nur bei Props-Änderungen neu gerendert |

### Phase 8.2: Skeleton Loader

| Feature | Beschreibung |
|---------|--------------|
| Skeleton UI | Layoutgetreuer Placeholder während des Ladens |
| Animate Pulse | Sanfte Animation für visuelles Feedback |
| ARIA Status | role="status" mit aria-label für Screenreader |

### Phase 8.3: Accessibility & Polish

| Feature | Beschreibung |
|---------|--------------|
| ARIA Labels | Alle Buttons mit aria-label für Screenreader |
| ARIA Roles | role="dialog", role="menu", role="menuitem", role="status" |
| aria-hidden | Icons für Screenreader ausgeblendet |
| aria-live | Status-Indikatoren für Auto-Save und Clipboard |
| aria-haspopup | Dropdown-Buttons korrekt annotiert |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | memo, Skeleton, ARIA |

**Verification Path**: Admin → Website → Seiten → Loading prüfen (Skeleton sichtbar) → Screenreader-Test

---

## CMS Copy/Paste & Quick Actions - Phase 7 (2026-02-28) - IMPLEMENTED

**Scope**: Clipboard-Funktionen und Schnellzugriff für effizientes Block-Management.

### Phase 7.1: Clipboard-System

| Feature | Beschreibung |
|---------|--------------|
| Copy Block | Block in Zwischenablage kopieren |
| Cut Block | Block ausschneiden (wird beim Einfügen entfernt) |
| Paste Block | Block aus Zwischenablage einfügen (unterhalb ausgewähltem Block) |
| Keyboard Shortcuts | Ctrl+C, Ctrl+X, Ctrl+V |

### Phase 7.2: Quick Actions Menü

| Feature | Beschreibung |
|---------|--------------|
| Dropdown-Menü | Schnellzugriff-Dropdown pro Block |
| Aktionen | Kopieren, Ausschneiden, Einfügen, Nach oben, Nach unten, Als Vorlage, Löschen |
| Touch-Optimiert | Größere Klickflächen für Mobile |

### Phase 7.3: Keyboard Shortcuts Overlay

| Feature | Beschreibung |
|---------|--------------|
| Help-Modal | Vollständige Shortcut-Übersicht |
| Kategorien | Allgemein, Block-Aktionen, Navigation |
| Toggle | `?` Taste oder Help-Button |

### Keyboard Shortcuts

| Shortcut | Aktion |
|----------|--------|
| Ctrl+C | Block kopieren |
| Ctrl+X | Block ausschneiden |
| Ctrl+V | Block einfügen |
| Ctrl+Z | Rückgängig |
| Ctrl+Y / Ctrl+Shift+Z | Wiederholen |
| Ctrl+S | Speichern |
| Escape | Auswahl aufheben |
| ? | Shortcuts-Hilfe anzeigen |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Clipboard-State, Quick Actions UI, Shortcuts Modal |

**Verification Path**: Admin → Website → Seiten → Block auswählen → Ctrl+C → Ctrl+V testen → Quick Actions Dropdown → `?` für Shortcuts-Hilfe

---

## CMS Block Templates - Phase 6 (2026-02-28) - IMPLEMENTED

**Scope**: Wiederverwendbare Block-Vorlagen speichern und anwenden.

### Phase 6.1: Datenstruktur & API

| Feature | Beschreibung |
|---------|--------------|
| Supabase Migration | `block_templates` Tabelle mit RLS |
| Pydantic Schemas | Create, Update, Response Models |
| REST API | CRUD Endpoints unter `/api/v1/website/block-templates` |

### Phase 6.2: Template-Library UI

| Feature | Beschreibung |
|---------|--------------|
| Tabs im Block-Picker | "Neue Blöcke" / "Vorlagen" |
| Kategorie-Filter | All, Custom, Hero, Content, Marketing, Contact, Layout, Widget |
| Template-Karten | Name, Block-Typ, Löschen-Button |

### Phase 6.4: Block Templates Admin UI (2026-03-01)

| Feature | Beschreibung |
|---------|--------------|
| Admin-Seite `/website/templates` | Vollstandige CRUD-UI fur Block-Templates |
| Kategorie-Filter | Dropdown mit allen 7 Kategorien |
| Suche | Durchsucht Name, Beschreibung und Block-Typ |
| Responsive Layout | Tabelle (Desktop) / Karten (Mobile) |
| Create/Edit Modal | JSON-Editoren fur block_props und style_overrides |
| Delete Confirmation | useConfirm Dialog |
| Navigation | Neuer Eintrag in Sidebar unter Website-Gruppe |

### Phase 6.3: Template Anwenden

| Feature | Beschreibung |
|---------|--------------|
| "Als Vorlage speichern" Button | BookmarkPlus Icon bei jedem Block |
| Save-Modal | Name, Kategorie, Block-Typ Anzeige |
| Template einfügen | Click auf Template → neuer Block mit Props/Styles |

### Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260228182604_add_block_templates.sql` | NEU: DB Schema |
| `backend/app/schemas/block_templates.py` | NEU: Pydantic Models |
| `backend/app/api/routes/block_templates.py` | NEU: CRUD Endpoints |
| `backend/app/main.py` | Router registriert |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Template UI |
| `frontend/app/(admin)/website/templates/page.tsx` | NEU: Admin UI fur Templates |
| `frontend/app/components/AdminShell.tsx` | Navigation + LayoutTemplate Icon |
| `frontend/app/lib/i18n/translations/de.json` | nav.templates |
| `frontend/app/lib/i18n/translations/en.json` | nav.templates |

**Verification Path**: Admin → Website → Templates → Liste sichtbar → Neues Template → Erstellen → Bearbeiten → Loschen

---

## CMS Undo/Redo & Auto-Save - Phase 5 (2026-02-28) - IMPLEMENTED

**Scope**: History-Management für Block-Änderungen mit Undo/Redo und automatischem Speichern.

### Phase 5.1: History-Stack

| Feature | Beschreibung |
|---------|--------------|
| useHistory Hook | Custom Hook für State-History |
| Max 50 Einträge | Begrenzte History-Größe |
| Deep-Clone | JSON.stringify/parse für State-Vergleich |

### Phase 5.2: Undo/Redo UI & Shortcuts

| Feature | Beschreibung |
|---------|--------------|
| Toolbar Buttons | Undo/Redo Buttons mit Tooltips |
| Ctrl+Z | Rückgängig machen |
| Ctrl+Y / Ctrl+Shift+Z | Wiederholen |
| Status-Anzeige | Anzahl verfügbarer Schritte |

### Phase 5.3: Auto-Save

| Feature | Beschreibung |
|---------|--------------|
| 30-Sekunden-Timer | Automatisches Speichern bei Änderungen |
| Status-Indikator | "Speichert..." / "Automatisch gespeichert" |
| Error-Handling | Fehlermeldung bei fehlgeschlagenem Save |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/pages/[id]/use-history.ts` | NEU: useHistory & useHistoryKeyboard Hooks |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | History-Integration, UI-Buttons, Auto-Save |

**Verification Path**: Admin → Website → Seiten → Blocks bearbeiten → Ctrl+Z testen → 30s warten → Auto-Save prüfen

---

## CMS Block-Styling-Panel - Phase 4 (2026-02-28) - IMPLEMENTED

**Scope**: Erweitertes Styling-Panel für jeden Block mit Background-, Typography-, Border- und Animation-Optionen.

### Phase 4.1: Erweiterte Background-Optionen

| Option | Beschreibung |
|--------|--------------|
| Gradient | CSS-Gradienten (linear/radial) |
| Position | center, top, bottom, left, right, Kombinationen |
| Size | cover, contain, auto, 100% auto, auto 100% |
| Repeat | no-repeat, repeat, repeat-x, repeat-y |
| Attachment | scroll, fixed (Parallax-Effekt) |

### Phase 4.2: Typography-Optionen

| Option | Werte |
|--------|-------|
| Text Color | Hex-Farbe |
| Font Size | xs, sm, base, lg, xl, 2xl, 3xl, 4xl |
| Font Weight | normal, medium, semibold, bold |
| Line Height | tight, normal, relaxed, loose |
| Text Align | left, center, right, justify |
| Letter Spacing | tighter, tight, normal, wide, wider |

### Phase 4.3: Border & Shadow

| Option | Werte |
|--------|-------|
| Border Radius | none, sm, md, lg, xl, 2xl, full |
| Border Width | 0, 1, 2, 4, 8 px |
| Border Color | Hex-Farbe |
| Border Style | solid, dashed, dotted, none |
| Box Shadow | none, sm, md, lg, xl, 2xl |

### Phase 4.4: Animation & Hover-Effekte

| Option | Werte |
|--------|-------|
| Animation | fade-in, slide-up, slide-down, scale-in, bounce |
| Hover Effect | lift, glow, scale, darken |
| Transition Duration | fast (150ms), normal (300ms), slow (500ms) |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/website.ts` | BlockStyleOverrides erweitert |
| `backend/app/schemas/block_validation.py` | Neue Style-Felder validiert |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | BlockStyleEditor UI erweitert |
| `frontend/app/(public)/components/BlockRenderer.tsx` | Style-Klassen und CSS-Verarbeitung |
| `frontend/app/globals.css` | Animation Keyframes |

**Verification Path**: Admin → Website → Seiten → Block bearbeiten → Styling-Tab → Optionen testen

---

## CMS Drag-Drop in Sections - Phase 3 (2026-02-28) - IMPLEMENTED

**Scope**: Drag-Drop-Funktionalität für Widgets in Section-Spalten.

### Features

| Feature | Beschreibung |
|---------|--------------|
| @dnd-kit Library | Moderne React Drag-Drop Library |
| Drop-Zones | Jede Spalte ist eine Drop-Zone für Widgets |
| Widget Picker | Click-to-Add UI für neue Widgets |
| Sortierung | Widgets per Drag-Drop neu anordnen |
| Spalten-Transfer | Widgets zwischen Spalten verschieben |
| Drag Overlay | Visuelles Feedback beim Ziehen |

### Neue Komponenten

| Komponente | Funktion |
|------------|----------|
| `SectionColumnsEditor` | DndContext Container für Spalten |
| `DroppableColumn` | Drop-Zone mit Widget-Picker |
| `SortableWidgetItem` | Draggable Widget Item |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/package.json` | @dnd-kit Dependencies |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | SectionColumnsEditor, DroppableColumn, SortableWidgetItem |

**Verification Path**: Admin → Website → Seiten → Section bearbeiten → Widgets in Spalten ziehen

---

## CMS Widget-Library - Phase 2 (2026-02-28) - IMPLEMENTED

**Scope**: Atomare Widget-Blöcke für flexible Seitengestaltung.

### Widget-Typen

| Widget | Beschreibung | Optionen |
|--------|--------------|----------|
| button | CTA-Button | primary/secondary/outline/ghost, sm/md/lg, icon |
| headline | Überschrift | h1-h6, alignment, color, fontSize |
| paragraph | Textabsatz | HTML-Unterstützung, alignment, fontSize |
| spacer | Vertikaler Abstand | Presets (sm-2xl) oder Custom px |
| divider | Trennlinie | solid/dashed/dotted, thickness, width |
| icon_box | Icon mit Text | Lucide Icons, vertical/horizontal layout |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/website.ts` | 6 Widget Props Interfaces |
| `backend/app/schemas/block_validation.py` | 6 Widget Validators mit Sanitierung |
| `frontend/app/(public)/components/BlockRenderer.tsx` | 6 Widget Renderer Komponenten |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Widget Block-Typen, Kategorie "Widget" |

### Widget JSON-Beispiel

```json
{
  "type": "button",
  "props": {
    "text": "Jetzt buchen",
    "href": "/kontakt",
    "variant": "primary",
    "size": "md",
    "icon": "arrow-right",
    "iconPosition": "right"
  }
}
```

**Verification Path**: Admin → Website → Seiten → Widget hinzufügen → Props bearbeiten

---

## CMS Container-System - Phase 1 (2026-02-28) - IMPLEMENTED

**Scope**: Elementor-inspiriertes Container-System mit Sections und flexiblen Spalten.

### Section-Block Features

| Feature | Beschreibung |
|---------|--------------|
| Spalten-Layouts | 1-col, 2-col, 2-col-wide, 3-col, 4-col |
| Layout-Varianten | full (volle Breite), boxed (container), narrow |
| Gap-Optionen | none, sm, md, lg, xl |
| Mobile-Reverse | Spaltenreihenfolge auf Mobil umkehren |
| Vertical Align | top, center, bottom, stretch |
| Rekursive Tiefe | Max. 3 Ebenen (Section in Section in Section) |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/website.ts` | ColumnConfig, SectionBlockProps, SectionPreset Types |
| `backend/app/schemas/block_validation.py` | ColumnConfig, SectionBlockProps Validatoren, rekursive Validierung |
| `frontend/app/(public)/components/BlockRenderer.tsx` | SectionBlock Renderer mit CSS Grid |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Section Block-Typ, SectionPropsEditor UI |

### Section-Block JSON-Struktur

```json
{
  "type": "section",
  "props": {
    "layout": "boxed",
    "gap": "md",
    "columns": [
      { "width": 66.67, "widgets": [] },
      { "width": 33.33, "widgets": [] }
    ],
    "mobileReverse": false,
    "verticalAlign": "top"
  }
}
```

### Einschränkungen Phase 1

- Widgets in Spalten werden per JSON editiert (kein Drag-Drop)
- Vorschau muss manuell aktualisiert werden

**Verification Path**: Admin → Website → Seiten → Section hinzufügen → Spalten-Preset wählen

---

## CMS SSR & SEO - Phase 0 (2026-02-28) - IMPLEMENTED

**Scope**: Server-Side Rendering und SEO-Optimierung für Public Website.

### Server-Side Rendering

| Änderung | Beschreibung | Datei(en) |
|----------|--------------|-----------|
| Homepage SSR | Server Component mit prefetched data | `(public)/page.tsx` |
| CMS-Seiten SSR | Server Component mit generateStaticParams | `(public)/[slug]/page.tsx` |
| Design API | `fetchDesign()` für Server-Side fetch | `(public)/lib/api.ts` |
| Client Components entfernt | `HomePageClient`, `CmsPageClient` gelöscht | - |

### Technical SEO

| Feature | Beschreibung | Datei |
|---------|--------------|-------|
| Sitemap | Dynamische XML Sitemap für CMS + Properties | `app/sitemap.ts` |
| Robots.txt | Dynamisches robots.txt mit Sitemap-Link | `app/robots.ts` |
| Canonical URLs | Automatische canonical links | `(public)/lib/metadata.ts` |
| ISR | 60 Sekunden Revalidierung | `page.tsx` files |

### Structured Data (Schema.org)

| Schema | Verwendung | Datei |
|--------|------------|-------|
| BreadcrumbList | Alle CMS-Seiten | `(public)/lib/structured-data.tsx` |
| FAQPage | Seiten mit FAQ-Blocks | `(public)/lib/structured-data.tsx` |

### SEO-Verbesserungen

- Full HTML content für Crawler sichtbar (kein Loading Skeleton)
- Open Graph & Twitter Cards in Metadaten
- Canonical URLs verhindern Duplikate
- ISR für schnelle Updates bei CMS-Änderungen

**Verification Path**: View-Source auf Public Website → HTML-Content sichtbar

---

## CMS Security Hardening - Phase -1 (2026-02-28) - IMPLEMENTED

**Scope**: Security-Hardening des bestehenden CMS vor dem Elementor-Upgrade.

### Änderungen

| Task | Beschreibung | Datei(en) |
|------|--------------|-----------|
| CSS-Validierung | `sanitize_css_strict()` für `custom_css` aktiviert | `website_admin.py` |
| Block-Validatoren | 8 fehlende Block-Typen hinzugefügt | `block_validation.py` |
| Unknown Blocks ablehnen | Strict-Mode für API-Endpunkte | `block_validation.py`, `website_admin.py` |

### Neue Block-Validatoren (19 total)

**Neu:** `search_form`, `property_search`

**Legacy:** `hero_search`, `usp_grid`, `rich_text`, `contact_cta`, `faq`, `featured_properties`

### Security-Verbesserungen

- Ungültiges CSS löst `400 Bad Request` aus
- Unbekannte Block-Typen werden mit Fehlermeldung abgelehnt
- `validate_blocks_strict()` für API-Endpunkte (kein silent pass-through)

**Verification Path**: Manuelle Tests über Admin-Panel → Website → Seiten bearbeiten

---

## Dokumentations-Bereinigung (2026-02-27) - IMPLEMENTED

**Scope**: Abgleich der Dokumentation mit aktuellem Codebase-Stand basierend auf Audit-Reports.

### Aktualisierte Dateien

| Datei | Änderung |
|-------|----------|
| `RELEASE_PLAN.md` | Status "Pre-MVP" → "Produktionsreif (85%)", Timeline aktualisiert |
| `CHANGELOG.md` | Fehlende Versionen 0.4.0-0.6.0 hinzugefügt |
| `PRODUCT_BACKLOG.md` | Epic-Status korrigiert (A, C, G, H, J) |

### Korrigierte Epic-Status

- **Epic A (Stability)**: 🚧 → ✅ Done (Session-Management, CSP implementiert)
- **Epic C (Booking)**: 🚧 → ✅ Done (E-Mail-System, Buchungsanfragen)
- **Epic G (Owner Portal)**: 💡 Proposed → 🚧 In Progress (RBAC-Rolle funktioniert)
- **Epic H (Finance)**: 💡 Proposed → 🚧 In Progress (Kurtaxe, DAC7 implementiert)
- **Epic J (Branding)**: Branding-System als vollständig dokumentiert

### Neue CHANGELOG-Einträge

- **v0.6.0** (2026-02-27): Branding-System Phase 3-5, Font-Optimierung
- **v0.5.0** (2026-02-15): Kurtaxe, DSGVO/DAC7, Extra-Services
- **v0.4.0** (2026-01-31): E-Mail-System, Session-Management

**Verification Path**: `git diff HEAD~1 backend/docs/product/`

---

## Security Fixes - Audit Findings (2026-02-27) - IMPLEMENTED

**Scope**: Behebung kritischer, hoher und mittlerer Security-Findings aus dem Security Audit.

### Behobene Issues

| # | Schweregrad | Problem | Lösung |
|---|-------------|---------|--------|
| 1 | **CRITICAL** | Rate Limiting Fail-Open bei Redis-Ausfall | In-Memory Fallback implementiert |
| 2 | **HIGH** | Smoke Auth Bypass ohne Production-Disable | `SMOKE_AUTH_BYPASS_ENABLED` Flag hinzugefügt |
| 3 | **HIGH** | JWT Secret Generation in Development | Verbesserte Warnung + .env.example Update |
| 4 | **HIGH** | Fehlende Rate Limiting für Auth Endpoints | Middleware-basiertes Rate Limiting |
| 5 | **HIGH** | Custom CSS Injection | CSS Sanitizer mit Dangerous Pattern Blocking |
| 6 | **HIGH** | Unvollständige RBAC Enforcement | RBAC an 22 Endpoints nachgerüstet |
| 7 | **MEDIUM** | Trust Proxy Headers Default True | Default auf False geändert |
| 8 | **MEDIUM** | CORS x-http-method-override erlaubt | Header entfernt (Method Tampering) |
| 9 | **MEDIUM** | Encryption Key ohne Validierung | Validation Property + Warnungen |
| 10 | **MEDIUM** | Redis TLS ohne Validierung | Warnung bei unsicherer Konfiguration |
| 11 | **MEDIUM** | Audit Log Best-Effort | Redis-basierte Retry Queue implementiert |

### Änderungen im Detail

#### 1. In-Memory Rate Limiting Fallback

**Problem:** Bei Redis-Ausfall wurden alle Requests durchgelassen (Fail-Open). Dies ermöglichte DDoS und Brute-Force Angriffe.

**Lösung:** Neues Modul `memory_rate_limit.py` mit In-Memory Token Bucket als Fallback:
- Sliding Window Counter Algorithmus
- Thread-safe für async Operations
- Automatisches Cleanup abgelaufener Einträge
- `X-RateLimit-Fallback: memory` Header zur Observability

**Betroffene Dateien:**
- `backend/app/core/memory_rate_limit.py` (NEU)
- `backend/app/core/public_anti_abuse.py` (Fallback integriert)
- `backend/app/core/auth_rate_limit.py` (Fallback integriert)

#### 2. Smoke Auth Bypass Production Flag

**Problem:** Der Smoke Test Auth Bypass in `middleware.ts` konnte nicht in Production deaktiviert werden.

**Lösung:** Neues Environment Flag `SMOKE_AUTH_BYPASS_ENABLED`:
- Default: `true` (Backwards-Kompatibilität)
- In Production: `SMOKE_AUTH_BYPASS_ENABLED=false` setzen
- Deaktiviert x-pms-smoke Header Auth-Bypass

**Betroffene Dateien:**
- `frontend/middleware.ts` (Flag-Check hinzugefügt)

#### 3. JWT Secret Warning Verbesserung

**Problem:** In Development wird JWT Secret generiert, aber die Warnung war nicht klar genug über die Konsequenzen (Session-Verlust nach Restart).

**Lösung:**
- Verbesserte Warnung mit konkreten Konsequenzen
- `.env.example` mit Generierungs-Kommando und Erklärung aktualisiert

**Betroffene Dateien:**
- `backend/app/core/config.py` (Verbesserte Warnung)
- `backend/.env.example` (Dokumentation)

#### 4. Auth Rate Limiting Middleware

**Problem:** Die meisten authentifizierten Endpoints (100+) hatten kein Rate Limiting. Nur `get_current_user_rate_limited()` war geschützt.

**Lösung:** Neue Middleware `AuthRateLimitMiddleware`:
- Automatisches Rate Limiting für ALLE authentifizierten Requests
- User-basierte Limits (aus JWT)
- IP-basierte Limits als zusätzlicher Schutz
- Exempt Paths für Health/Docs

**Betroffene Dateien:**
- `backend/app/core/auth_rate_limit_middleware.py` (NEU)
- `backend/app/main.py` (Middleware registriert)

#### 5. Custom CSS Sanitizer

**Problem:** `custom_css` Feld erlaubte potenziell gefährliche CSS Konstrukte (url(), @import, expression()).

**Lösung:** Neuer CSS Sanitizer mit Dangerous Pattern Blocking:
- Blockiert: `url()`, `@import`, `expression()`, `javascript:`, `behavior:`
- Blockiert: `position:fixed` (UI Overlay), Unicode Escapes
- Logging bei Validation Failures

**Betroffene Dateien:**
- `backend/app/core/css_sanitizer.py` (NEU)
- `backend/app/api/routes/branding.py` (Validator integriert)

#### 6. RBAC Enforcement für alle Admin-Endpoints

**Problem:** Mehrere Admin-Endpoints hatten nur Basic Auth (`get_current_user`) ohne Rollen-Prüfung. Jeder authentifizierte User konnte sensible Operationen durchführen.

**Betroffene Endpoints (vorher ohne RBAC):**
- `extra_services.py`: 8 Endpoints (Katalog CRUD + Property Assignments)
- `website_admin.py`: 12 Endpoints (Design, Pages, Branding, Navigation, SEO)
- `public_domain_admin.py`: 3 Endpoints (Domain Management)
- `roles.py`: 4 Endpoints (Permissions/Roles Read)

**Lösung:** `require_agency_roles()` Dependency zu allen Endpoints hinzugefügt:
- **DELETE**: Nur `admin`
- **POST/PATCH/PUT**: `admin`, `manager`
- **GET (sensibel)**: `staff`, `manager`, `admin`

**Betroffene Dateien:**
- `backend/app/api/routes/extra_services.py` (8 Endpoints)
- `backend/app/api/routes/website_admin.py` (12 Endpoints)
- `backend/app/api/routes/public_domain_admin.py` (3 Endpoints)
- `backend/app/api/routes/roles.py` (4 Endpoints)

#### 7. Reliable Audit Logging mit Redis Queue

**Problem:** Audit Events wurden "best-effort" geschrieben. Bei DB-Fehlern wurden Events verloren. Dies gefährdet Compliance-Anforderungen (GDPR, SOC2).

**Lösung:** Redis-basierte Retry-Queue für fehlgeschlagene Audit Events:
- Primary: Direkter DB-Write (Fast Path, ~1ms)
- On Failure: Event wird in Redis Queue eingereiht
- Background Worker: Verarbeitet Queue periodisch
- Dead Letter Queue: Nach 3 Retries für manuelle Review

**Architektur:**
```
┌─────────────────────────────────────────────────────────────────┐
│  RELIABLE AUDIT LOGGING                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Request → emit_audit_event()                                   │
│                │                                                │
│                ▼                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. DB Write (Primary)                                  │   │
│  │     ✓ Success → Event logged                            │   │
│  │     ✗ Failure → Continue to step 2                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                │ (on failure)                                   │
│                ▼                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  2. Redis Queue (Fallback)                              │   │
│  │     Event → pms:audit:failed_events                     │   │
│  │     retry_count, last_error, created_at                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                │ (background)                                   │
│                ▼                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  3. Queue Worker (Periodic)                             │   │
│  │     Pop event → Retry DB write                          │   │
│  │     ✓ Success → Done                                    │   │
│  │     ✗ Failure (retry < 3) → Re-queue                    │   │
│  │     ✗ Failure (retry >= 3) → Dead Letter Queue          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Konfiguration:**
```bash
# .env
AUDIT_QUEUE_ENABLED=true          # Enable/disable queue fallback
AUDIT_QUEUE_MAX_RETRIES=3         # Retries before DLQ
AUDIT_QUEUE_RETRY_DELAY=60        # Seconds between retries
```

**Health Check:**
```bash
# Enable audit queue health check
ENABLE_AUDIT_QUEUE_HEALTHCHECK=true

# Check status
curl -s localhost:8000/health/ready | jq '.components.audit_queue'
```

**Betroffene Dateien:**
- `backend/app/core/audit.py` (erweitert mit Queue-Integration)
- `backend/app/core/audit_queue.py` (NEU - Queue Manager)
- `backend/app/core/config.py` (Queue-Konfiguration)
- `backend/app/core/health.py` (Queue Health Check)

### Verification Path

```bash
# Backend Unit Tests für Memory Rate Limiter
cd backend && pytest tests/core/test_memory_rate_limit.py -v

# Manuelle Verifikation:
# 1. Redis stoppen, API-Request senden -> sollte 429 nach Limit zurückgeben
# 2. X-RateLimit-Fallback: memory Header prüfen
# 3. SMOKE_AUTH_BYPASS_ENABLED=false setzen -> x-pms-smoke Bypass sollte nicht funktionieren
```

### Migrationen

Keine Datenbank-Migrationen erforderlich.

### Post-Deploy Bug Fixes (2026-02-27)

Nach dem initialen Deploy der RBAC-Änderungen traten 500-Fehler auf. Die folgenden Fixes wurden angewendet:

#### Fix 1: RBAC Exception-Handling + x-agency-id Header (`9fecb70`)

**Problem:** Extra Services Seite zeigte "Datenbank-Fehler: Tabellen möglicherweise nicht vorhanden"

**Ursachen:**
1. Backend `require_agency_roles()` fing nur `HTTPException`, andere DB-Fehler (z.B. `asyncpg.UndefinedTableError`) wurden als unbehandelter 500 weitergegeben
2. Frontend API Proxy Routes sendeten keinen `x-agency-id` Header, wodurch Tenant-Resolution fehlschlug

**Lösung:**
- **Backend `auth.py`**: Erweiterte Exception-Behandlung in `require_agency_roles`:
  - `asyncpg.UndefinedTableError/UndefinedColumnError` → graceful fallback (RBAC wird übersprungen)
  - Andere Exceptions → 500 mit Details zur Diagnose
- **Frontend `extra-services/page.tsx`**: Zeigt echte Backend-Fehlermeldungen und 403 RBAC-Fehler an
- **Frontend alle 4 extra-services API Routes**: Senden `x-agency-id` Header via `getAgencyIdFromSession()` Helper

**Betroffene Dateien:**
- `backend/app/core/auth.py`
- `frontend/app/(admin)/extra-services/page.tsx`
- `frontend/app/api/internal/extra-services/route.ts`
- `frontend/app/api/internal/extra-services/[id]/route.ts`
- `frontend/app/api/internal/properties/[id]/extra-services/route.ts`
- `frontend/app/api/internal/properties/[id]/extra-services/[assignmentId]/route.ts`

#### Fix 2: UUID Type Mismatch (`0690a28`)

**Problem:** Nach Fix 1 trat ein neuer Fehler auf:
```
AttributeError: 'UUID' object has no attribute 'replace'
```

**Ursache:**
- `deps.py` → `get_current_agency_id()` gibt `UUID`-Objekt zurück (Zeile 80: `-> UUID:`)
- Routes annotierten `agency_id: str` und riefen dann `UUID(agency_id)` auf
- Python kann `UUID(uuid_object)` nicht verarbeiten - erwartet String

**Lösung:**
- `agency_id: str` → `agency_id: UUID` in allen betroffenen Endpoints
- Entfernte redundante `UUID(agency_id)` Konvertierungen

**Betroffene Dateien:**
- `backend/app/api/routes/extra_services.py` (9 Endpoints)
- `backend/app/api/routes/public_domain_admin.py` (3 Endpoints)

### Commits

| Commit | Beschreibung |
|--------|--------------|
| `c7a1da6` | RBAC enforcement für 27 Endpoints |
| `23531b6` | Reliable audit logging mit Redis Queue |
| `9fecb70` | RBAC 500-error fix (Exception-Handling + x-agency-id) |
| `0690a28` | UUID type mismatch fix |

---

## Branding-Einstellungen Integritätsfixes (2026-02-27) - IMPLEMENTED

**Scope**: Behebung von CSS-Variablen die gesetzt aber nicht verwendet wurden, fehlende Fonts, überlappende Optionen.

### Behobene Issues

| # | Problem | Lösung |
|---|---------|--------|
| 1 | Fonts (Roboto, Open Sans, Poppins) nicht geladen | `layout.tsx`: Google Fonts Import hinzugefügt |
| 2 | `topbar_height_px` CSS-Variable nicht verwendet | AdminShell.tsx: `minHeight: var(--topbar-height)` auf Header |
| 3 | `button_border_radius` ignoriert | globals.css: Button nutzt `--button-radius` mit Fallback |
| 4 | `logo_position` nicht implementiert | AdminShell.tsx: Center/Left Positionierung via Flexbox |
| 5 | `shadow_intensity` ohne Wirkung | globals.css: Data-Attribute-basierte Shadow-Overrides |
| 6 | `nav_border_radius` nicht angewendet | globals.css: Nav-Elemente nutzen `--nav-radius` |
| 7 | `radius_scale` vs individuelle Radius-Optionen unklar | branding-form.tsx: Beschreibungstexte hinzugefügt |
| 8 | `background_color` vs `content_bg_color` unklar | branding-form.tsx: Hinweistexte und Hints |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/layout.tsx` | Roboto, Open_Sans, Poppins Imports |
| `frontend/app/globals.css` | Shadow Intensity, Border Radius, Button Radius CSS |
| `frontend/app/lib/theme-provider.tsx` | Font-Variablen, Shadow Data-Attribute |
| `frontend/app/components/AdminShell.tsx` | Topbar Height, Logo Position, Shadow CSS |
| `frontend/app/(admin)/settings/branding/branding-form.tsx` | UI-Beschreibungen/Hints |

### Verification Path

```bash
# Frontend Build
cd frontend && npm run build

# PROD-Verifikation
# - /settings/branding > Marke: Fonts (Roboto, Poppins, Open Sans) testen
# - /settings/branding > Erweitert: Topbar-Höhe Slider testen
# - /settings/branding > Erweitert: Logo-Position (Links/Zentriert) testen
# - /settings/branding > Erweitert: Schatten-Intensität testen (none/subtle/normal/strong)
# - /settings/branding > Erweitert: Border-Radius pro Komponente testen
```

---

## Premium Hybrid Navigation - Phase 1+2 (2026-02-26) - IMPLEMENTED

**Scope**: CSS-Variablen-System und Navigation-Komponenten für moderne, responsive Admin-Navigation.

### Phase 1: CSS-Variablen-System

- **globals.css**: 80+ neue CSS-Variablen für Brand Gradient, Surface, Interactive, Navigation-specific, Component-specific (Search, Palette, Flyout), Mobile
- **theme-provider.tsx**: Neue Interfaces (`ApiBrandConfig`, `ApiNavBehavior`) und Funktion `applyPremiumNavCssVariables()` für dynamisches Setzen der Variablen
- **Dark Mode**: Vollständige Overrides für alle neuen Variablen in `[data-theme="dark"]` und `[data-theme="system"]`

### Phase 2: Navigation-Komponenten

- **Flyout-Menüs**: Im collapsed Mode zeigt Hover über Gruppen ein Flyout mit allen Items
- **Item Count Badges**: Jede Gruppe zeigt Anzahl der sichtbaren Items
- **Animierte Transitions**: Smooth Expand/Collapse mit CSS-Variablen-basierter Duration
- **Premium Hybrid Design**: Weiße Sidebar, Gradient Logo, Icon Container mit aktiven Gradients

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/globals.css` | +80 CSS-Variablen, Animation Utilities |
| `frontend/app/lib/theme-provider.tsx` | +2 Interfaces, +2 Funktionen |
| `frontend/app/components/AdminShell.tsx` | Flyouts, Badges, Premium Design |
| `backend/docs/ops/runbook/37-premium-hybrid-navigation.md` | Dokumentation |

### Abwärtskompatibilität

- Alle bestehenden `--t-*` und `--nav-*` Variablen bleiben unverändert
- Neue Variablen haben Fallback-Werte in globals.css
- Keine Breaking Changes

### Verification Path

```bash
# 1. Lokaler Syntax-Check (keine Fehler)
cd frontend && npm run lint

# 2. Build-Test
npm run build

# 3. PROD-Verifikation nach Deploy
# - Browser: Sidebar Collapse/Expand testen
# - Browser: Hover über Gruppe im collapsed Mode → Flyout erscheint
# - Browser: Expand-Gruppen zeigen Item Count Badges
```

### Nächste Phasen

- ~~Phase 3: Favoriten-System~~ ✅
- ~~Phase 4: Command Palette~~ ✅
- ~~Phase 5: Mobile Responsiveness~~ ✅
- ~~Phase 6: Branding-UI Erweiterung~~ ✅

---

## Premium Hybrid Navigation - Phase 3-6 (2026-02-26) - IMPLEMENTED

**Scope**: Favoriten-System, Command Palette, Mobile Responsiveness, Branding-UI Erweiterung.

### Phase 3: Favoriten-System

- **LocalStorage-Persistenz**: Tenant-isoliert via `pms-nav-favorites` Key
- **Favoriten-Sektion**: Erscheint automatisch bei ≥1 Favorit
- **Star-Toggle**: An allen Nav-Items (Hover-State, Amber-Farbe)
- **Max-Limit**: 5 Favoriten (konfigurierbar via FAVORITES_MAX_COUNT)

### Phase 4: Command Palette

- **Komponente**: `frontend/app/components/CommandPalette.tsx`
- **Keyboard Shortcut**: ⌘K (Mac) / Ctrl+K (Windows/Linux)
- **Recent Searches**: LocalStorage-Persistenz (`pms-command-palette-recent`)
- **Sektionen**: Favoriten, Zuletzt besucht, Suchergebnisse
- **Keyboard Navigation**: ↑/↓ + Enter + ESC

### Phase 5: Mobile Responsiveness

- **Bottom Tab Bar**: Fixiert am unteren Rand (< 1024px)
- **Mobile Drawer**: Vollständige Navigation mit Touch UX
- **iOS Safe Area**: `env(safe-area-inset-*)` Support
- **Touch Targets**: Min. 44px, `active:scale-95`

### Phase 6: Branding-UI Erweiterung

- **DB-Migration**: `supabase/migrations/20260226163000_add_branding_nav_behavior.sql`
- **Backend Schema**: `BrandingUpdate` + `BrandingResponse` mit neuen Feldern
- **Branding-Form UI**: Toggles für enable_favorites, enable_command_palette, enable_collapsible_groups, default_sidebar_collapsed
- **Gradient Colors**: 3 Color Picker mit Live-Vorschau
- **Mobile Settings**: Toggle für mobile_bottom_tabs_enabled
- **AdminShell Integration**: Respektiert alle neuen Branding-Einstellungen

### Dateien (Phase 3-6)

| Datei | Änderung |
|-------|----------|
| `frontend/app/components/AdminShell.tsx` | Favorites, Mobile Drawer, Bottom Tabs, Branding Checks |
| `frontend/app/components/CommandPalette.tsx` | Neue Komponente |
| `frontend/app/lib/theme-provider.tsx` | Phase 6 Felder, CSS-Variablen |
| `frontend/app/settings/branding/branding-form.tsx` | Neue UI-Sektionen |
| `backend/app/schemas/branding.py` | Phase 6 Felder |
| `supabase/migrations/20260226163000_add_branding_nav_behavior.sql` | Neue Spalten |

### Verification Path

```bash
# 1. DB-Migration
supabase db diff  # Zeigt neue Spalten

# 2. Frontend Build
cd frontend && npm run build

# 3. PROD-Verifikation
# - /settings/branding: Neue Sektionen vorhanden
# - Toggle "Favoriten-System" deaktivieren → Sterne verschwinden
# - Toggle "Befehlspalette" deaktivieren → ⌘K funktioniert nicht mehr
# - Mobile: Bottom Tab Bar ausblenden via Toggle
```

---

## Branding-Einstellungen Bugfixes (2026-02-26) - IMPLEMENTED

**Scope**: Behebung von 9 Issues in der Branding-UI (`/settings/branding`) - Einstellungen ohne Wirkung und Bugs.

### Behobene Issues

| # | Problem | Lösung |
|---|---------|--------|
| 1 | `enable_collapsible_groups` hatte keine Wirkung | AdminShell.tsx prüft jetzt `branding.enable_collapsible_groups` |
| 2 | `default_sidebar_collapsed` hatte keine Wirkung | Neuer useEffect respektiert Branding-Default wenn kein localStorage |
| 3 | `font_family` hatte keine Wirkung | theme-provider.tsx setzt jetzt `--font-family` CSS-Variable |
| 4 | Nav `hover_text` Farbe wirkungslos | CSS-Variable-Namen synchronisiert (`--nav-item-text-hover`) |
| 5 | Nav `width_pct` wirkungslos | Beide Variable-Namen gesetzt (legacy + premium) |
| 6 | Nav `icon_size_px`/`item_gap_px` wirkungslos | AdminShell nutzt jetzt CSS-Variablen statt hardcoded Werte |
| 7 | Nav-Farbeinstellungen teilweise wirkungslos | Alle CSS-Variablen-Namen zwischen theme-provider und AdminShell synchronisiert |
| 8 | `ALLOWED_NAV_KEYS` veraltet | Backend-Schema aktualisiert (26 Keys statt 24, korrekte Namen) |
| 9 | Gradient-Reset löscht DB-Werte nicht | `handleSubmit` sendet jetzt `null` für leere Gradient-Felder |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/components/AdminShell.tsx` | `isGroupCollapsible` Check, `default_sidebar_collapsed` useEffect, CSS-Variablen |
| `frontend/app/lib/theme-provider.tsx` | `applyFontFamily()`, erweiterte `applyNavCssVariables()` |
| `frontend/app/settings/branding/branding-form.tsx` | Gradient-Reset sendet null |
| `backend/app/schemas/branding.py` | `ALLOWED_NAV_KEYS` aktualisiert |

### Verification Path

```bash
# 1. Frontend Build
cd frontend && npm run build

# 2. Backend Schema Check
cd backend && python3 -c "from app.schemas.branding import ALLOWED_NAV_KEYS; print(len(ALLOWED_NAV_KEYS), 'keys')"
# Erwartet: 26 keys

# 3. PROD-Verifikation
# - /settings/branding: "Einklappbare Gruppen" deaktivieren → Gruppen nicht mehr einklappbar
# - /settings/branding: "Sidebar standardmäßig eingeklappt" aktivieren → localStorage löschen → Sidebar startet collapsed
# - /settings/branding: Font ändern → Text ändert Schriftart
# - /settings/branding: Gradient zurücksetzen + speichern → Gradient wird entfernt
```

---

## Backend Branding API Fix - Phase 6 Felder (2026-02-26) - IMPLEMENTED

**Scope**: Kritischer Bugfix - Backend `/api/v1/branding` Route ignorierte alle Phase 6 Felder.

### Root Cause

Die DB-Migration `20260226163000_add_branding_nav_behavior.sql` fügte 8 neue Spalten hinzu, aber die Backend-Route `branding.py` wurde **nie aktualisiert**:

1. **GET Route** selektierte Phase 6 Spalten nicht aus der DB
2. **PUT Route** hatte keine Handler für Phase 6 Felder
3. **BrandingResponse** Konstruktion populierte Phase 6 Felder nicht

### Auswirkung

- User speicherte Phase 6 Einstellungen → Daten wurden **nie in DB geschrieben**
- GET Route gab nur Schema-Defaults zurück (nicht die gespeicherten Werte)
- Folge: enable_favorites, enable_command_palette, enable_collapsible_groups, default_sidebar_collapsed, gradient_from/via/to, mobile_bottom_tabs_enabled hatten **keine Wirkung**

### Fix

| Stelle | Änderung |
|--------|----------|
| GET SELECT | +8 Phase 6 Spalten |
| GET BrandingResponse | +8 Felder aus row[] |
| PUT Handlers | +8 `if updates.xxx is not None:` Blöcke |
| PUT RETURNING | +8 Phase 6 Spalten |
| PUT BrandingResponse | +8 Felder aus row[] |

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/api/routes/branding.py` | GET/PUT Phase 6 Support |

### Verification Path

```bash
# 1. PROD-Verifikation nach Deploy
# - /settings/branding: "Favoriten-System" deaktivieren → Speichern → Page Reload → Bleibt deaktiviert
# - /settings/branding: "Sidebar eingeklappt" aktivieren → Speichern → Logout → Login → Sidebar startet collapsed
# - /settings/branding: Gradient setzen → Speichern → Sidebar Logo zeigt Gradient
# - API Check: GET /api/v1/branding liefert Phase 6 Felder (nicht mehr null/default)
```

---

## Branding UX Verbesserungen (2026-02-26) - IMPLEMENTED

**Scope**: Navigation und Branding-Einstellungen Bugfixes + UX-Verbesserungen.

### Behobene Issues

| # | Problem | Lösung |
|---|---------|--------|
| 1 | Sidebar-Breite (width_pct) wirkungslos | `--nav-width-expanded` wird jetzt in `applyNavCssVariables()` gesetzt, nicht mehr überschrieben |
| 2 | Sidebar-Hintergrund nicht anpassbar | Neues Feld `nav_bg_color` hinzugefügt (DB, Schema, API, Form, CSS) |
| 3 | Sidebar flackert beim Navigieren | `useState` Initializer liest localStorage synchron statt in useEffect |
| 4 | Suchfeld zu nah am Logo | `paddingTop: 16px` hinzugefügt |
| 5 | Branding-Seite zu schmal | Container von `max-w-2xl` auf `max-w-5xl` erweitert |

### Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260226175739_add_branding_nav_bg_color.sql` | Neue Spalte nav_bg_color |
| `backend/app/schemas/branding.py` | nav_bg_color Feld + Validator |
| `backend/app/api/routes/branding.py` | GET/PUT nav_bg_color Support |
| `frontend/app/lib/theme-provider.tsx` | nav_bg_color → --surface-sidebar, width sync |
| `frontend/app/components/AdminShell.tsx` | Flicker-Fix, Logo-Search-Spacing |
| `frontend/app/settings/branding/branding-form.tsx` | nav_bg_color UI, breiteres Layout |

### Verification Path

```bash
# 1. Sidebar-Breite: /settings/branding → Slider ändern → Sidebar ändert Breite
# 2. Sidebar-Hintergrund: /settings/branding → Sidebar-Hintergrund Farbe setzen → Speichern → Sidebar ändert Farbe
# 3. Flicker-Fix: Zwischen Seiten navigieren → Sidebar bleibt stabil (kein collapse/expand flicker)
# 4. Layout: /settings/branding aufrufen → Seite nutzt mehr Breite
```

---

## Branding Topbar & Body Styling (2026-02-26) - IMPLEMENTED

**Scope**: Einheitliche Gestaltungsoptionen für Topbar und Content-Bereich, Bugfixes, UX-Verbesserungen.

### Neue Features

| Feature | Beschreibung |
|---------|-------------|
| `topbar_bg_color` | Hintergrundfarbe des Topbars (Admin Header) |
| `topbar_border_color` | Rahmenfarbe des Topbars |
| `content_bg_color` | Hintergrundfarbe des Content-Bereichs (Body) |
| Gradient in "Marke"-Tab | Gradient-Farben von "Erweitert" nach "Marke" verschoben |
| `hover_text` UI | Fehlender Color-Picker für Hover-Textfarbe hinzugefügt |

### Behobene Issues

| # | Problem | Lösung |
|---|---------|--------|
| 1 | Topbar verwendete hardcoded Tailwind-Klassen | CSS-Variablen `--surface-header`, `--surface-header-border` |
| 2 | Content-Bereich nicht anpassbar | CSS-Variable `--surface-content` |
| 3 | `hover_text` in Schema aber nicht im UI | Color-Picker in branding-form.tsx hinzugefügt |
| 4 | Gradient in "Erweitert"-Tab versteckt | Nach "Marke"-Tab verschoben |
| 5 | Leerer "Erweitert"-Tab | Tab entfernt (nur noch "Marke" und "Navigation") |
| 6 | Font-Family nicht überall angewendet | `--font-family` CSS-Variable global + inherit-Regel |
| 7 | `width_pct` Label unklar | Label zeigt jetzt `{value}rem ({px}px)` |

### Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260226234133_add_branding_topbar_body_colors.sql` | Neue Spalten |
| `backend/app/schemas/branding.py` | 3 neue Felder + Validator |
| `backend/app/api/routes/branding.py` | GET/PUT für neue Felder |
| `frontend/app/lib/theme-provider.tsx` | CSS-Variablen für Topbar/Content |
| `frontend/app/components/AdminShell.tsx` | Topbar/Content mit CSS-Variablen statt hardcoded |
| `frontend/app/(admin)/settings/branding/branding-form.tsx` | Neue UI-Sektion, Tab-Struktur, Bugfixes |
| `frontend/app/globals.css` | `--font-family` Variable + inherit-Regel |

### Verification Path

```bash
# 1. Topbar-Farbe: /settings/branding → "Topbar & Content" Sektion → Topbar-Hintergrund setzen → Speichern → Topbar ändert Farbe
# 2. Body-Farbe: /settings/branding → Content-Hintergrund setzen → Speichern → Content-Bereich ändert Farbe
# 3. Gradient: /settings/branding → Tab "Marke" → Gradient-Sektion ist sichtbar (nicht mehr in "Erweitert")
# 4. Font: /settings/branding → Schriftart ändern → Speichern → Topbar, Content und Navigation nutzen gleiche Schriftart
# 5. hover_text: /settings/branding → Tab "Navigation" → Sidebar-Farben → "Hover Text" Feld vorhanden
```

---

## Admin Route Group Architektur (2026-02-26) - IMPLEMENTED

**Scope**: Refaktorierung der Frontend-Route-Struktur für stabiles AdminShell-Verhalten.

### Problem

AdminShell wurde bei jeder Navigation zwischen Admin-Seiten neu gemountet, da jede Route ihr eigenes Layout mit AdminShell hatte. Dies verursachte:
- Sidebar-Flicker durch Hydration-Mismatch
- Verlust des Sidebar-States (collapsed, expanded groups, favorites)
- Redundante Auth-Checks (25x pro Session statt 1x)
- Performance-Overhead durch ständiges Remounting

### Lösung

Zentrale `(admin)` Route Group mit einmaligem AdminShell:

```
app/
  (admin)/                    ← Route Group
    layout.tsx                ← AdminShell EINMAL hier
    properties/
      page.tsx
      [id]/
        layout.tsx            ← Nur Tabs (kein AdminShell)
    guests/
      page.tsx
    ...
```

### Änderungen

| Typ | Anzahl | Beschreibung |
|-----|--------|--------------|
| Gelöscht | 22 | Einfache AdminShell-Wrapper-Layouts |
| Aktualisiert | 3 | Authorization-Layouts (ohne AdminShell) |
| Neu | 1 | Zentrales `(admin)/layout.tsx` |
| Import-Fixes | ~50+ | Relative → Absolute Pfade (`@/app/...`) |

### Verification Path

```bash
# Build testen
cd frontend && npm run build
# Erwartung: Build erfolgreich
```

### Dokumentation

- Runbook: `backend/docs/ops/runbook/38-admin-route-group-architecture.md`

---

## Multi-Device Session Tracking (2026-02-26) - VERIFIED

**Scope**: Anzeige und Verwaltung aller aktiven Sitzungen eines Benutzers auf verschiedenen Geräten.

### Problem

Bisher zeigte die Security-Seite (`/profile/security`) nur die aktuelle Sitzung des Geräts an, von dem die Seite aufgerufen wird. Login von einem anderen Gerät (z.B. Handy) wurde nicht als separate Sitzung angezeigt.

**Ursache:** Supabase Auth bietet keine API zum Abrufen aller aktiven Sessions eines Benutzers.

### Lösung

Eigene `user_sessions` Tabelle mit Session-Tracking bei Login/Logout.

### Implementierung

| Phase | Beschreibung | Dateien |
|-------|-------------|---------|
| 1 | DB-Migration mit `user_sessions` Tabelle | `supabase/migrations/20260226100000_add_user_sessions.sql` |
| 2 | RLS Fix + SECURITY DEFINER Funktionen | `supabase/migrations/20260226120000_fix_user_sessions_rls.sql` |
| 3 | IDOR Security Fix | `supabase/migrations/20260226140000_fix_session_functions_idor.sql` |
| 4 | Shared User-Agent Parser | `frontend/app/lib/user-agent.ts` (NEU) |
| 5 | Login: Session erstellen + Cookie setzen | `frontend/app/auth/login/route.ts` |
| 6 | Logout: Session beenden (scope: local) | `frontend/app/auth/logout/route.ts` |
| 7 | Client Logout: Redirect zu Server-Route | `frontend/app/lib/logout.ts` |
| 8 | Sessions API: GET/DELETE mit UUID-Validation | `frontend/app/api/internal/auth/sessions/route.ts` |
| 9 | Middleware: Revoked Session Detection | `frontend/middleware.ts` |
| 10 | Frontend: Revoke-Button aktiviert | `frontend/app/profile/security/page.tsx` |

### Datenbank-Schema

```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY,
    agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    device_type TEXT DEFAULT 'Desktop',
    browser TEXT,
    os TEXT,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    ended_by TEXT,  -- 'user', 'revoked', 'new_login', 'expired'
    is_active BOOLEAN GENERATED ALWAYS AS (ended_at IS NULL) STORED
);
```

### SECURITY DEFINER Funktionen

```sql
-- Beendet einzelne Session mit auth.uid() Validierung
end_user_session(p_session_id UUID, p_user_id UUID, p_ended_by TEXT) → BOOLEAN

-- Beendet alle Sessions mit auth.uid() Validierung
end_all_user_sessions(p_user_id UUID, p_ended_by TEXT) → INTEGER
```

### Datenfluss

```
Login:
[User] → POST /auth/login → [Create user_sessions Record] → [Set pms_session_id Cookie]

Security Page:
[User] → GET /api/internal/auth/sessions → [Query user_sessions WHERE ended_at IS NULL]
       → [Show all sessions, mark current via cookie]

Revoke Session:
[User] → DELETE /api/internal/auth/sessions {session_id}
       → [end_user_session() mit auth.uid() Check]
       → [Anderes Gerät: Middleware erkennt revoked → Redirect zu Logout]

Logout (nur aktuelles Gerät):
[User] → performLogout() → GET /auth/logout
       → [end_user_session()] → [signOut({ scope: 'local' })] → [Clear Cookie]

"Alle Sitzungen beenden":
[User] → DELETE /api/internal/auth/sessions {all_others: true}
       → [end_all_user_sessions()] → [signOut({ scope: 'global' })]
```

### Security Features

| Feature | Implementierung |
|---------|-----------------|
| Cookie Security | `httpOnly`, `secure`, `sameSite='strict'` |
| UUID Validation | Regex-Check vor DB-Queries |
| IDOR Prevention | `auth.uid()` Check in SECURITY DEFINER |
| Revoked Detection | Middleware prüft `ended_at` bei jedem Admin-Request |
| Local Logout | `signOut({ scope: 'local' })` → Nur aktuelles Gerät |
| User-Agent Parser | iOS/iPad vor macOS prüfen (enthält "Mac OS") |

### RLS Policies

- SELECT: Nur eigene Sessions (`user_id = auth.uid()`)
- INSERT: Nur eigene Sessions (`WITH CHECK`)
- UPDATE: Nur eigene Sessions (`WITH CHECK`)

### Commits

```
d00ab68 security: fix IDOR vulnerability in session functions
8026ec5 feat: add session validity check in middleware
159a9ee fix: redirect client logout to server route
e6ba0c9 fix: use local scope in client-side logout utility
6826681 fix: detect iOS/iPad before macOS in user-agent parser
55130ed fix: remove aggressive session cleanup on login
871da89 feat: change logout to local scope
c5bdf9a fix: clean up orphaned sessions on login
8d48dfd fix: use SECURITY DEFINER functions for session management
```

### Verification Path

```bash
# 1. Migrations anwenden (3 SQL-Dateien)
# Supabase Dashboard → SQL Editor

# 2. Login von Desktop → Session in DB erstellt
# 3. Login von Handy → Zweite Session in DB
# 4. Security-Seite → Beide Sessions angezeigt
# 5. Handy abmelden → Desktop bleibt eingeloggt ✓
# 6. Security-Seite → Handy-Session verschwunden ✓
# 7. Session von Desktop revoken → Handy wird bei nächstem Request ausgeloggt ✓
```

**Security Audit:** ✅ Bestanden (2026-02-26)

**Status:** ✅ VERIFIED

**Runbook:** [36-multi-device-sessions.md](./ops/runbook/36-multi-device-sessions.md)

---

## Supabase Auth & Web Vitals Logging Fixes (2026-02-26) - IMPLEMENTED

**Scope**: Behebung von Supabase Security-Warnungen und Web Vitals Log-Spam.

### Übersicht der Fixes

| # | Problem | Ursache | Lösung |
|---|---------|---------|--------|
| S1 | Supabase `getSession()` Warning im Log | `getSession()` validiert JWT nicht serverseitig | `getUser()` vor `getSession()` aufrufen |
| S2 | Web Vitals 422 Fehler | Backend gab `{"agency_id": "None"}` zurück | 404 statt 200 mit null-Wert zurückgeben |
| S3 | Frontend Log-Spam `[WebVitals] Could not determine agency_id` | Warning für jede Metrik auf Admin-Domain | Warning entfernt (erwartetes Verhalten) |
| S4 | Backend Log-Spam `WARNING - Could not resolve agency_id` | WARNING Level für Admin-Domains | Log-Level zu DEBUG reduziert |

### S1: Supabase `getSession()` Security Warning

**Problem:** Supabase loggte Warnung: "Using supabase.auth.getSession() could be vulnerable to session spoofing"

**Ursache:** `getSession()` liest nur Cookies ohne JWT-Validierung. Für Server-Side Auth sollte `getUser()` verwendet werden.

**Lösung:**
1. Neue Helper-Funktion `getValidatedSession()` in `frontend/app/lib/server-auth.ts`
2. Pattern: Erst `getUser()` für JWT-Validierung, dann `getSession()` für `access_token`
3. 33 Dateien aktualisiert (6 Layouts, 26 API Routes, 1 Helper)

**Geänderte Dateien:**
- `frontend/app/lib/server-auth.ts` - Neue `getValidatedSession()` Funktion
- `frontend/app/*/layout.tsx` (6 Dateien) - `getSession()` → `getUser()`
- `frontend/app/api/internal/*/route.ts` (26 Dateien) - Two-step Auth Pattern

### S2: Web Vitals 422 Fehler

**Problem:** Backend gab HTTP 200 mit `{"agency_id": "None"}` zurück wenn Domain nicht gemappt

**Ursache:** `str(None)` in Python wird zu String `"None"`, nicht `null`

**Lösung:** Explizite Prüfung auf `None` und 404-Response in `backend/app/api/routes/public_site.py`

```python
if agency_id is None:
    raise HTTPException(status_code=404, detail="Agency not found for domain")
```

### S3 & S4: Log-Spam Bereinigung

**Problem:** Hunderte Warn-Logs für erwartetes Verhalten (Admin-Domain ohne Agency-Mapping)

**Lösung:**
- Frontend: Warning komplett entfernt (silent OK return)
- Backend: Log-Level von WARNING zu DEBUG in `tenant_domain.py`

### Commits

- `db24d18` - fix: use getUser() for JWT validation before getSession()
- `42ffac9` - fix: return 404 instead of "None" string for unknown agency domains
- `dac6e93` - chore: remove noisy WebVitals warning for admin domains
- `eb8ed38` - chore: reduce tenant_domain log level from warning to debug

### Verification Path

```bash
# 1. Prüfen dass keine getSession Warnings mehr im Frontend Log erscheinen
# Coolify → pms-admin → Logs → Keine "getSession" Warnungen

# 2. Prüfen dass keine 422 Fehler mehr für Web Vitals
# Coolify → pms-admin → Logs → Keine "[WebVitals] Backend returned error: 422"

# 3. Prüfen dass Backend keine WARNING-Spam mehr für tenant_domain
# Coolify → pms-backend → Logs → "Could not resolve agency_id" nur noch auf DEBUG Level
```

**Status:** ✅ IMPLEMENTED

---

## Web Vitals Performance Monitoring (2026-02-25) - IMPLEMENTED

**Scope**: Core Web Vitals Monitoring für Public Websites mit Admin-Dashboard.

### Features

| Feature | Beschreibung |
|---------|-------------|
| Datenerfassung | Automatische Erfassung von LCP, FCP, CLS, FID, INP, TTFB via `sendBeacon` |
| Admin-Dashboard | `/ops/web-vitals` - Aggregierte Metriken mit Rating-Anzeige |
| Langsamste Seiten | Top 5 Seiten nach LCP-Wert |
| Zeitfilter | 24h, 7d, 30d Perioden-Auswahl |
| Auto-Cleanup | Trigger löscht Einträge älter als 30 Tage, max 10.000 pro Agency |

### Architektur

```
[Public Website] → sendBeacon → [Frontend Proxy] → [Backend API] → [Supabase]
                                 /api/internal/      POST /vitals
                                 analytics/vitals    (public, no auth)

[Admin Panel] → apiClient → [Backend API] → [Supabase]
                            GET /vitals/summary
                            (admin only, JWT auth)
```

### Implementierte Komponenten

| Komponente | Datei | Beschreibung |
|------------|-------|--------------|
| DB Migration | `supabase/migrations/20260225110000_add_web_vitals_metrics.sql` | Tabelle + Trigger + RLS |
| RLS Fix | `supabase/migrations/20260225160000_fix_web_vitals_rls.sql` | Public INSERT Policy |
| Backend Routes | `backend/app/api/routes/analytics.py` | POST + GET Endpoints |
| Backend Schemas | `backend/app/schemas/analytics.py` | Pydantic Models |
| Frontend Proxy | `frontend/app/api/internal/analytics/vitals/route.ts` | sendBeacon Proxy |
| Admin UI | `frontend/app/ops/web-vitals/page.tsx` | Dashboard-Seite |
| WebVitals Hook | `frontend/app/components/WebVitals.tsx` | Metric Collection |
| Agency Resolver | `backend/app/api/routes/public_site.py` | `/agency-by-domain` Endpoint |

### Gelöste Probleme (Debugging-Prozess)

| # | Problem | Ursache | Lösung |
|---|---------|---------|--------|
| 1 | 404 auf `/api/v1/analytics/vitals/summary` | Router nicht gemountet bei `MODULES_ENABLED=true` | Failsafe-Mount in `main.py` hinzugefügt |
| 2 | 403 "Not authenticated" | Frontend sendete kein Auth-Token | `accessToken` aus `useAuth()` an apiClient übergeben |
| 3 | Build Error "Property 'token' does not exist" | AuthContextType verwendet `accessToken`, nicht `token` | Variable umbenannt |
| 4 | 500 "NoneType has no attribute 'acquire'" | `get_pool()` gibt None zurück bei Startup | `get_db` Dependency statt `get_pool()` verwenden |
| 5 | 500 "invalid input for query argument $2" | asyncpg benötigt `timedelta` für Interval, nicht String | `timedelta(hours=24)` statt `"24 hours"` |
| 6 | 403 Host Allowlist Check Failed | `/agency-by-domain` wurde von Admin-Domain aufgerufen | Separaten Router ohne Host-Allowlist erstellt |
| 7 | "Database pool not available" Warning | POST Endpoint nutzte `get_pool()` | `get_db` Dependency verwenden |
| 8 | Daten nicht angezeigt (0 Messungen) trotz 144 Einträgen | RLS Policy blockierte SELECT | Permissive SELECT Policy hinzugefügt |
| 9 | Daten immer noch 0 trotz korrekter RLS | `agency_id` Typ-Mismatch (String vs UUID) | `ensure_uuid()` Funktion für Konvertierung |
| 10 | 500 "badly formed hexadecimal UUID string" | JWT enthält kein `agency_id` Claim | `resolve_agency_id()` Funktion mit Auto-Pick aus `team_members` |

### Key Learnings

1. **Supabase JWT enthält kein `agency_id`**: Multi-Tenant Apps müssen Agency aus `team_members` Tabelle auflösen
2. **asyncpg Interval-Type**: PostgreSQL Intervals müssen als `timedelta` übergeben werden, nicht als String
3. **RLS für Backend-Zugriff**: Backend nutzt Service Role Key, aber RLS Policies müssen trotzdem korrekt sein
4. **sendBeacon + Auth**: `sendBeacon` kann keine Auth-Header senden → Public Endpoint erforderlich
5. **Host Allowlist**: Nicht alle Public Endpoints sollen auf bestimmte Domains beschränkt sein

### Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260225110000_*.sql` | NEU - DB Schema |
| `supabase/migrations/20260225160000_*.sql` | NEU - RLS Fix |
| `backend/app/api/routes/analytics.py` | NEU - API Routes |
| `backend/app/schemas/analytics.py` | NEU - Schemas |
| `backend/app/api/routes/public_site.py` | `agency_domain_router` hinzugefügt |
| `backend/app/main.py` | Failsafe Mounts für analytics + agency_domain_router |
| `frontend/app/api/internal/analytics/vitals/route.ts` | NEU - Proxy |
| `frontend/app/ops/web-vitals/page.tsx` | NEU - Admin UI |
| `frontend/app/ops/web-vitals/layout.tsx` | NEU - Auth Layout |
| `frontend/app/components/AdminShell.tsx` | Navigation Link hinzugefügt |

### Verification Path

```bash
# 1. Public Website besuchen (generiert Web Vitals Daten)
curl -I https://www.syltwerker.de/

# 2. Admin Panel → Einstellungen → Performance aufrufen
# Erwartet: Metriken-Karten mit LCP, FCP, CLS, FID, INP, TTFB

# 3. Zeitfilter wechseln (7 Tage, 30 Tage)
# Erwartet: Daten werden aktualisiert

# 4. Backend Logs prüfen
# Erwartet: "Auto-picked agency for user ... " bei GET Request
```

### Commits

- `1c134af` - fix: allow anonymous inserts for web vitals metrics
- `3effc86` - fix: use get_db dependency instead of get_pool()
- `65562da` - fix: use separate router for agency-by-domain
- `eb02d5e` - fix: ensure agency_id is UUID type for web vitals queries
- `b701770` - fix: add agency_id resolution for web vitals endpoint

**Status:** ✅ IMPLEMENTED

**Runbook:** [35-web-vitals-monitoring.md](ops/runbook/35-web-vitals-monitoring.md)

---

## UI Fixes & Cancellation Policy (2026-02-25) - IMPLEMENTED

**Scope**: UI-Verbesserungen und Backend-Fix für Stornierungsregeln.

### Übersicht der Fixes

| # | Problem | Datei | Fix |
|---|---------|-------|-----|
| U1 | Datumsformat ohne führende Nullen (3.1.2026) | `properties/[id]/page.tsx` | `toLocaleString()` mit `day: "2-digit"` |
| U2 | Dashboard-Icon passt nicht zum Branding | `dashboard/page.tsx` | AlertTriangle → Clock Icon |
| U3 | Stornierungsregel wird nicht gespeichert | `property_service.py` | Felder zu `allowed_fields` hinzugefügt |

### U1: Datumsformat mit führenden Nullen

**Vorher:** `3.1.2026 14:5:3`
**Nachher:** `03.01.2026 14:05:03`

**Lösung:** `toLocaleString("de-DE", { day: "2-digit", month: "2-digit", ... })`

### U2: Dashboard-Icon Konsistenz

**Vorher:** AlertTriangle-Icon für "Offene Buchungsanfragen" (wirkt wie Warnung)
**Nachher:** Clock-Icon (passt besser zum Konzept "wartend")

### U3: Stornierungsregel speichern

**Problem:** Bei Property-Edit wurde "Andere vordefinierte verwenden" nicht persistiert.

**Ursachen (3 Fehler):**
1. `cancellation_policy_id` und `use_agency_default_cancellation` fehlten in `allowed_fields` Dictionary
2. `cancellation_policy_id` wurde nicht von String zu UUID konvertiert
3. `cancellation_policy_id` und `use_agency_default_cancellation` fehlten in den SELECT-Queries

**Lösung:**
1. Beide Felder zu `allowed_fields` in `property_service.py` hinzugefügt
2. UUID-Konvertierung für `cancellation_policy_id` (wie bei `owner_id`) + NULL-Handling für leere Strings
3. Beide Felder zu `list_properties` und `get_property` SELECT-Queries hinzugefügt

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/properties/[id]/page.tsx` | `formatDateTime()` mit 2-digit Formatierung |
| `frontend/app/dashboard/page.tsx` | Clock statt AlertTriangle Import/Verwendung |
| `backend/app/services/property_service.py` | allowed_fields, UUID-Konvertierung, SELECT-Queries |

### Verification Path

```bash
# U1: Datumsformat prüfen
# Property-Detail Seite öffnen, Buchungshistorie prüfen

# U2: Dashboard-Icon prüfen
# Dashboard öffnen, "Offene Buchungsanfragen" Karte prüfen

# U3: Stornierungsregel speichern
# Property bearbeiten → Stornierungsregeln → "Andere vordefinierte verwenden" → Speichern → Reload
```

**Commits:**
- `0783ea3` - allowed_fields fix
- `2613266` - UUID conversion fix
- `cce652c` - SELECT queries fix

**Status:** ✅ IMPLEMENTED

---

## Bug Fixes - Kritische Validierungen (2026-02-24) - IMPLEMENTED

**Scope**: Behebung kritischer Bugs aus PMS-Audit (#1, #3-#6).

### Bug #1: Doppelbuchungen (Race Condition)

**Problem**: `update_booking_status()` hatte keinen Advisory Lock. Bei gleichzeitiger Bestätigung zweier Anfragen für dieselben Daten konnte eine Race Condition auftreten.

**Szenario**:
```
Thread 1: inquiry → confirmed (liest Status, validiert, bestätigt)
Thread 2: inquiry → confirmed (liest Status, validiert, bestätigt)
→ Beide sehen "inquiry", beide versuchen zu bestätigen
```

**Lösung**:
- Advisory Lock `pg_advisory_xact_lock` zu `update_booking_status()` hinzugefügt
- Lock wird auf Property-ID gesetzt (serialisiert alle Status-Änderungen pro Property)
- Status wird NACH Lock-Erwerb erneut geprüft (Double-Check Pattern)

**Datei**: `backend/app/services/booking_service.py`

**Vorher**: ⚠️ Teilweise geschützt (nur DB-Constraint)
**Nachher**: ✅ Vollständig geschützt (Lock + Constraint)

### Bug #3: Kurtaxe ignoriert Altersgrenze

**Problem**: `free_under_age` Feld in `visitor_tax_periods` wurde nicht in der Berechnung verwendet.

**Lösung**:
- Neues Feld `children_taxable` in `QuoteRequest` Schema
- Erlaubt explizite Angabe wie viele Kinder über der Altersgrenze sind
- Validator: `children_taxable <= children`

**Dateien**:
- `backend/app/schemas/pricing.py` - Neues Feld + Validator
- `backend/app/api/routes/pricing.py` - Berechnung aktualisiert

### Bug #4: Timezone-naive Datetimes

**Problem**: `datetime.utcnow()` erzeugt naive Timestamps ohne Timezone-Info.

**Lösung**: Alle 30 Vorkommen im gesamten Backend durch `datetime.now(timezone.utc)` ersetzt.

**Betroffene Dateien**:
| Datei | Anzahl |
|-------|--------|
| `backend/app/services/booking_service.py` | 8 |
| `backend/app/api/routes/booking_requests.py` | 14 |
| `backend/app/core/auth.py` | 3 |
| `backend/app/api/routers/channel_connections.py` | 2 |
| `backend/app/services/channel_connection_service.py` | 1 |
| `backend/app/services/guest_service.py` | 1 |
| `backend/app/api/routes/notifications.py` | 1 |

### Bug #5: Fehlende max_guests Validierung

**Problem**: Gästeanzahl wurde nicht gegen `properties.max_guests` validiert.

**Lösung**:
- `max_guests` zu Property-Queries hinzugefügt
- Validierung in `create_booking()` und `update_booking()` implementiert
- Fehlermeldung: "Gästeanzahl (X) überschreitet die maximale Kapazität (Y Gäste)"

**Datei**: `backend/app/services/booking_service.py`

### Bug #6: 0-Nacht-Buchung möglich

**Status**: ✅ Bereits abgesichert

**Analyse**: Pydantic-Validator in `BookingBase` (Zeile 92-98) erzwingt `check_out > check_in`.

### Verification Path

```bash
# Bug #3: Kurtaxe mit children_taxable
curl -X POST "${API}/api/v1/pricing/quote" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"property_id":"...", "check_in":"2026-03-01", "check_out":"2026-03-03", "adults":2, "children":2, "children_taxable":1}'

# Bug #5: Überbuchung sollte 422 Fehler liefern
curl -X POST "${API}/api/v1/bookings" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"property_id":"...", "num_adults":10, "num_children":10}'  # > max_guests
```

**Status**: ✅ IMPLEMENTED

---

## Logic Bug Fixes - Berechnungs- und Validierungsfehler (2026-02-24) - IMPLEMENTED

**Scope**: Behebung von Logikfehlern bei Preis- und Rückerstattungsberechnungen.

### Übersicht der Fixes

| # | Problem | Datei | Fix |
|---|---------|-------|-----|
| L1 | Refund-Berechnung trunciert statt rundet | `booking_service.py` | `ROUND_HALF_UP` verwenden |
| L2 | Preis-Konvertierung (€→Cents) trunciert | `booking_service.py` | `ROUND_HALF_UP` verwenden |
| L3 | Refund auf 0€-Buchung erlaubt | `booking_service.py` | ValidationException werfen |
| L4 | Fee-Berechnung bei fehlenden Werten silent | `pricing_totals.py` | Warnings loggen |

### L1: Refund-Rundungsfehler

**Vorher (falsch):**
```python
refund_amount_cents = int(total_price_cents * refund_percent / 100)
# 9999 × 12% = 1199.88 → int() = 1199 cents
```

**Nachher (korrekt):**
```python
refund_decimal = (Decimal(total_price_cents) * Decimal(refund_percent)) / Decimal("100")
refund_amount_cents = int(refund_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
# 9999 × 12% = 1199.88 → ROUND_HALF_UP = 1200 cents
```

### L2: Preis-Konvertierung

**Vorher:** `int(Decimal(price) * 100)` - trunciert bei 99.995 → 9999
**Nachher:** `quantize(Decimal("1"), rounding=ROUND_HALF_UP)` - rundet zu 10000

### L3: Validierung bei fehlender Buchungssumme

**Neu:** Wenn `total_price_cents = 0`, wird eine `ValidationException` geworfen statt Refund auf 0€ zu berechnen.

### L4: Fee-Berechnungen mit Warnings

**Neu:** Wenn `per_stay`, `per_night` oder `per_person` Fees keine `value_cents` haben, wird ein Warning geloggt statt silent 0 zu berechnen.

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/booking_service.py` | ROUND_HALF_UP Import, Refund/Preis-Rundung, Validierung |
| `backend/app/services/pricing_totals.py` | Fee-Validierung mit Warnings |

**Status**: ✅ IMPLEMENTED

---

## Logic Bug Fixes Phase 2 - Codebase Audit (2026-02-24) - IMPLEMENTED

**Scope**: Umfassende Code-Analyse und Behebung weiterer Logikfehler.

### Übersicht der Fixes

| # | Schweregrad | Problem | Datei | Fix |
|---|-------------|---------|-------|-----|
| K1 | KRITISCH | Commission-Berechnung trunciert | `owners.py:944` | `ROUND_HALF_UP` verwenden |
| K2 | KRITISCH | Altersberechnung falsch (`days // 365`) | `guests.py:185` | Korrekte Datum-basierte Berechnung |
| H1 | HOCH | List.remove() kann ValueError werfen | `registry.py:80` | Existenz-Prüfung vor remove |
| H2 | HOCH | SQL f-Strings statt Parametern | `booking_requests.py` | Parameterisierte Queries |
| H3 | HOCH | Race Condition in update_booking() | `booking_service.py` | Advisory Lock + Double-Check |
| M1 | MITTEL | Type Coercion bei Geldwerten | `owners.py:942-943` | Explizite None-Prüfung |
| N1 | NIEDRIG | Bare Exceptions ohne Logging | 3 Dateien | `as e` + `logger.debug()` |
| N2 | NIEDRIG | Money-Parsing Heuristik fehlerhaft | `money.py` | Robuste Format-Erkennung |

### K1: Commission-Rundungsfehler

**Vorher (falsch):**
```python
commission_cents = int(gross_total_cents * commission_rate_bps / 10000)
# 10001 × 500 / 10000 = 500.05 → int() = 500 cents (sollte 500 sein, aber 500.5 → 501)
```

**Nachher (korrekt):**
```python
commission_decimal = (Decimal(str(gross_total_cents)) * Decimal(str(commission_rate_bps))) / Decimal("10000")
commission_cents = int(commission_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
```

### K2: Altersberechnungsfehler

**Vorher (falsch):**
```python
age = (date.today() - v).days // 365
# 01.01.2000 bis 01.01.2025 = 9131 Tage / 365 = 24 Jahre (FALSCH! Sollte 25 sein)
```

**Nachher (korrekt):**
```python
age = today.year - v.year
if (today.month, today.day) < (v.month, v.day):
    age -= 1  # Geburtstag noch nicht erreicht
```

### H1: Registry Safe Remove

**Vorher:** `.remove()` konnte `ValueError` werfen wenn Element nicht in Liste
**Nachher:** Existenz-Prüfung vor `remove()` + `.pop(key, None)` statt `.pop(key)`

### H2: SQL Parameterisierung

**Vorher (Anti-Pattern):**
```python
where_clauses.append(f"b.status IN ('{DB_STATUS_REQUESTED}', '{DB_STATUS_INQUIRY}')")
```

**Nachher (Best Practice):**
```python
where_clauses.append(f"b.status IN (${param_idx}, ${param_idx + 1})")
params.extend([DB_STATUS_REQUESTED, DB_STATUS_INQUIRY])
param_idx += 2
```

### H3: Race Condition in update_booking()

**Problem:** `update_booking()` prüfte Verfügbarkeit VOR Transaktion. Zwei gleichzeitige Updates konnten beide die Verfügbarkeitsprüfung bestehen, aber überlappende Buchungen erstellen.

**Szenario:**
```
Thread A: Liest Buchung X (01.-05. März)    Thread B: Liest Buchung Y (10.-15. März)
Thread A: check_availability() → OK         Thread B: check_availability() → OK
Thread A: UPDATE X zu 01.-12. März          Thread B: UPDATE Y zu 08.-15. März
→ OVERLAP bei 08.-12. März!
```

**Lösung:**
1. Advisory Lock am Anfang der Transaktion (serialisiert alle Updates pro Property)
2. Double-Check Pattern: Verfügbarkeit wird NACH Lock-Erwerb erneut geprüft

```python
async with self.db.transaction():
    # Lock verhindert parallele Updates
    await self.db.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
        str(current["property_id"])
    )
    # Verfügbarkeit erneut prüfen (andere Transaktion könnte inzwischen geändert haben)
    if dates_changed or status_changed:
        is_available = await self.check_availability(...)
        if not is_available:
            raise ConflictException("Property is already booked")
    # UPDATE durchführen
```

### N1: Bare Exceptions ohne Logging

**Problem:** `except Exception:` ohne `as e` fängt Fehler ab, aber loggt nichts - Debugging wird unmöglich.

**Vorher:**
```python
except Exception:
    return "unknown"  # Was ist passiert? Keine Ahnung!
```

**Nachher:**
```python
except Exception as e:
    logger.debug(f"Frame introspection failed: {e}")
    return "unknown"
```

**Betroffene Dateien:**
- `backend/app/channel_manager/adapters/base_adapter.py` - Connection validation
- `backend/app/core/health.py` - Settings import fallback
- `backend/app/core/database.py` - Frame/URL/Module introspection (3×)

### N2: Money-Parsing Heuristik

**Problem:** `to_decimal()` konnte deutsche Zahlenformate nicht korrekt erkennen.

**Vorher (fehlerhaft):**
```python
# "1.234,56" (German) → wurde nicht unterstützt!
# "1,234" → wurde als 1.234 interpretiert (falsch für US-Tausender)
```

**Nachher (robust):**
```python
# Format-Erkennung basierend auf Position von Komma/Punkt:
# "1.234,56" (DE) → Punkt vor Komma → 1234.56
# "1,234.56" (US) → Komma vor Punkt → 1234.56
# "10,50" → nur Komma, nicht 3 Ziffern → Dezimal → 10.50
# "1,234" → nur Komma, genau 3 Ziffern → Tausender → 1234
```

**Test-Ergebnisse:**
| Eingabe | Erwartet | Ergebnis |
|---------|----------|----------|
| `1.234,56` | 1234.56 | ✅ 1234.56 |
| `1,234.56` | 1234.56 | ✅ 1234.56 |
| `10,50` | 10.50 | ✅ 10.50 |
| `1,234` | 1234 | ✅ 1234 |
| `€ 1.234,56` | 1234.56 | ✅ 1234.56 |

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/api/routes/owners.py` | ROUND_HALF_UP Import, Commission-Berechnung, None-Handling |
| `backend/app/schemas/guests.py` | Korrekte Altersberechnung |
| `backend/app/modules/registry.py` | Safe remove Pattern |
| `backend/app/api/routes/booking_requests.py` | 4× SQL-Parameter statt f-Strings |
| `backend/app/services/booking_service.py` | Advisory Lock + Double-Check in update_booking() |
| `backend/app/channel_manager/adapters/base_adapter.py` | Bare Exception + Logging |
| `backend/app/core/health.py` | Bare Exception + Logging |
| `backend/app/core/database.py` | 3× Bare Exception + Logging |
| `backend/app/core/money.py` | Robuste Format-Erkennung für DE/US Zahlenformate |

**Status**: ✅ IMPLEMENTED

---

## Cancellation Policies - Stornierungsfrist-Logik (2026-02-24) - IMPLEMENTED

**Feature**: Konfigurierbare Stornierungsregeln mit automatischer Rückerstattungsberechnung.

**Navigation**: Unter "Objekte" (nicht "Einstellungen") - Pfad `/cancellation-rules`

### Übersicht

- **Agency-Level**: Custom Regeln (Tage vor Check-in → Rückerstattung%)
- **Property-Level**: Optional eigene Regel oder Agency-Default verwenden
- **Booking-Level**: Automatische Rückerstattungsberechnung bei Stornierung

### Neue Tabelle: `cancellation_policies`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | UUID | Primary Key |
| `agency_id` | UUID | FK zu agencies |
| `name` | VARCHAR(100) | Name der Regel (z.B. "Standard", "Flexibel") |
| `is_default` | BOOLEAN | Ist Default für Agency |
| `rules` | JSONB | Array von `{days_before, refund_percent}` |

### Properties-Erweiterung

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `cancellation_policy_id` | UUID | FK zu cancellation_policies |
| `use_agency_default_cancellation` | BOOLEAN | true = Agency-Default verwenden |

### API Endpoints

| Method | Endpoint | Beschreibung | Rollen |
|--------|----------|--------------|--------|
| GET | `/api/v1/cancellation-policies` | Liste aller Policies | staff+ |
| POST | `/api/v1/cancellation-policies` | Neue Policy erstellen | manager+ |
| GET | `/api/v1/cancellation-policies/{id}` | Policy Details | staff+ |
| PATCH | `/api/v1/cancellation-policies/{id}` | Policy bearbeiten | manager+ |
| DELETE | `/api/v1/cancellation-policies/{id}` | Policy löschen | admin |
| GET | `/api/v1/bookings/{id}/calculate-refund` | Refund berechnen | staff+ |

### Frontend-Seiten

| Seite | Beschreibung |
|-------|--------------|
| `/cancellation-rules` | Stornierungsregeln verwalten (CRUD) - unter "Objekte" in Navigation |
| `/properties` (Create Modal) | Stornierungsregel-Auswahl bei neuen Objekten |
| `/properties/[id]` (Edit Modal) | Abschnitt "Stornierungsregeln" mit Radio-Auswahl |
| `/bookings/[id]` (Cancel Modal) | Automatische Refund-Berechnung mit Override-Option |

### Dateien

| Bereich | Datei | Aktion |
|---------|-------|--------|
| Migration | `supabase/migrations/20260224000000_add_cancellation_policies.sql` | NEU |
| Backend | `backend/app/schemas/cancellation_policies.py` | NEU |
| Backend | `backend/app/schemas/properties.py` | Erweitert |
| Backend | `backend/app/api/routes/cancellation_policies.py` | NEU |
| Backend | `backend/app/api/routes/bookings.py` | calculate-refund Endpoint |
| Backend | `backend/app/services/booking_service.py` | calculate_refund() Methode |
| Frontend | `frontend/app/types/cancellation.ts` | NEU |
| Frontend | `frontend/app/types/property.ts` | Erweitert |
| Frontend | `frontend/app/cancellation-rules/page.tsx` | NEU (CRUD UI) |
| Frontend | `frontend/app/cancellation-rules/layout.tsx` | NEU (Auth-Layout) |
| Frontend | `frontend/app/properties/page.tsx` | Create Modal erweitert |
| Frontend | `frontend/app/properties/[id]/page.tsx` | Edit Modal erweitert |
| Frontend | `frontend/app/bookings/[id]/page.tsx` | Cancel Modal erweitert |
| Frontend | `frontend/app/components/AdminShell.tsx` | Navigation aktualisiert |
| Frontend | `frontend/app/components/Breadcrumb.tsx` | Breadcrumb-Labels |

### Verification Path

```bash
# 1. DB Migration anwenden
supabase db push

# 2. Backend starten und API testen
curl -X POST /api/v1/cancellation-policies \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Standard","is_default":true,"rules":[{"days_before":14,"refund_percent":100},{"days_before":7,"refund_percent":50},{"days_before":0,"refund_percent":0}]}'

# 3. Frontend prüfen
# - /cancellation-rules → Regeln erstellen/bearbeiten (unter "Objekte" in Nav)
# - /properties → Create Modal → Stornierungsregel auswählen
# - /properties/[id] → Edit Modal → Stornierungsregeln-Abschnitt
# - /bookings/[id] → Stornieren → Refund-Berechnung prüfen
```

**Status**: ✅ IMPLEMENTED

---

## Table-to-Card Responsive Pattern - Alle Admin-Listen (2026-02-23) - IMPLEMENTED

**Feature**: Responsive Table-to-Card Pattern gemäß CLAUDE.md §10 auf alle verbleibenden Admin-Listen angewendet.

### Bearbeitete Seiten

| Phase | Seite | Beschreibung |
|-------|-------|--------------|
| 1 | `/extra-services` | Zusatzleistungen mit Checkbox-Selektion |
| 1 | `/guests` | Gästeliste mit VIP/Gesperrt-Badges |
| 1 | `/owners` | Eigentümerliste mit DAC7-Export-Button |
| 1 | `/team` | Teammitglieder + Einladungen (2 Tabellen) |
| 1 | `/seasons` | Saisonvorlagen mit erweiterbaren Perioden |
| 1 | `/bookings` | Buchungsliste mit Status-Badges |
| 2 | `/notifications/email-outbox` | E-Mail Outbox mit Status-Anzeige |
| 2 | `/connections` | Channel-Manager-Verbindungen |
| 2 | `/channel-sync` | Sync-Logs mit Batch-Links |
| 2 | `/website/pages` | Website-Seiten mit Template-Badges |
| 3 | `/ops/modules` | Backend-Module mit Tags/Prefixes |
| 3 | `/ops/audit-log` | Audit-Log mit Aktions-Badges |

### Implementierung

- **Desktop (md+)**: Tabellen-Layout mit `hidden md:block`
- **Mobile (<md)**: Karten-Layout mit `block md:hidden`
- **Breakpoint**: 768px (Tailwind `md`)
- **Actions**: Alle Aktionen in beiden Layouts verfügbar

### Verification Path

```bash
# Responsive-Test: Browser-DevTools → Responsive Mode
# Alle Seiten bei 375px und 1280px Breite prüfen

# Betroffene URLs:
# /extra-services, /guests, /owners, /team
# /seasons, /bookings, /notifications/email-outbox
# /connections, /channel-sync, /website/pages
# /ops/modules, /ops/audit-log
```

**Referenz:** CLAUDE.md §10 - Responsive UI Design Pattern

**Status**: ✅ IMPLEMENTED

---

## Owner DAC7 Compliance & Edit Modal (2026-02-23) - IMPLEMENTED

**Feature**: DAC7-Richtlinie Compliance für Eigentümer (EU-Steuertransparenz) mit vollständigem Edit Modal.

### Änderungen

#### 1. DAC7 Pflichtfelder (Migration)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `tax_id` | TEXT | Steuer-ID (11-stellig für DE) |
| `birth_date` | DATE | Geburtsdatum (DAC7-Pflicht) |
| `vat_id` | TEXT | USt-IdNr. (für Gewerbetreibende) |

#### 2. Banking-Felder (für Auszahlungen)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `iban` | TEXT | IBAN |
| `bic` | TEXT | BIC/SWIFT |
| `bank_name` | TEXT | Bankname |

#### 3. Strukturierte Adresse

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `street` | TEXT | Straße + Hausnummer |
| `postal_code` | TEXT | PLZ |
| `city` | TEXT | Ort |
| `country` | TEXT | Land (ISO 3166-1, Default: DE) |

### Dateien

| Bereich | Datei | Änderung |
|---------|-------|----------|
| Migration | `supabase/migrations/20260223000000_add_owner_dac7_fields.sql` | Neue Spalten |
| Backend | `backend/app/schemas/owners.py` | Schemas erweitert |
| Backend | `backend/app/api/routes/owners.py` | CRUD-Endpoints erweitert |
| Frontend | `frontend/app/types/owner.ts` | TypeScript-Interface erweitert |
| Frontend | `frontend/app/owners/[ownerId]/page.tsx` | Detail-Seite + Edit Modal |

### Owner Edit Modal (Drawer-Style)

- Gleitet von rechts ein (Desktop) / von unten (Mobile)
- Sektionen: Name & Kontakt, Steuer & DAC7, Adresse, Bankverbindung, Provision & Status, Notizen
- PATCH auf `/api/v1/owners/{ownerId}`
- Auto-Refresh nach Speichern

### Verification Path

```bash
# 1. Owner Detail-Seite öffnen
# → /owners/{ownerId} zeigt alle DAC7-Felder

# 2. Edit Modal öffnen
# → "Bearbeiten" Button → Drawer öffnet sich
# → Alle Felder ausfüllen → "Änderungen speichern"

# 3. API-Test
curl -X PATCH "${API}/api/v1/owners/${OWNER_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tax_id": "12345678901",
    "birth_date": "1980-01-15",
    "iban": "DE89370400440532013000"
  }'
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 5: DAC7 Compliance)

**Status**: ✅ IMPLEMENTED

---

## DSGVO Datenexport (Art. 15 Auskunftsrecht) (2026-02-23) - IMPLEMENTED

**Feature**: Eigentümer können alle ihre personenbezogenen Daten exportieren (DSGVO Art. 15).

### Endpoint

`GET /api/v1/owner/me/export`

### Exportierte Daten

| Kategorie | Beschreibung |
|-----------|--------------|
| Stammdaten | Name, E-Mail, Telefon |
| Steuerdaten (DAC7) | tax_id, birth_date, vat_id |
| Adressdaten | street, postal_code, city, country |
| Bankverbindung | iban, bic, bank_name |
| Objektzuweisungen | Alle zugewiesenen Properties |
| Buchungsdaten | Buchungen für eigene Objekte |
| Abrechnungen | Finanzielle Statements |

### Dateien

| Bereich | Datei | Änderung |
|---------|-------|----------|
| Backend Schema | `backend/app/schemas/owners.py` | `OwnerDataExportResponse` + Hilfs-Schemas |
| Backend Route | `backend/app/api/routes/owners.py` | `GET /owner/me/export` Endpoint |

### Query Parameter

- `format=json` (default): JSON-Response
- `format=download`: Datei-Download als `.json`

### Verification Path

```bash
# Als eingeloggter Owner:
curl -X GET "${API}/api/v1/owner/me/export" \
  -H "Authorization: Bearer $OWNER_TOKEN"

# Als Download:
curl -X GET "${API}/api/v1/owner/me/export?format=download" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -o dsgvo_export.json
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 6: DSGVO Datenexport)

**Status**: ✅ IMPLEMENTED

---

## Strukturierte Adress-Migration (2026-02-23) - IMPLEMENTED

**Feature**: Migration von Legacy-`address` Feld zu strukturierten Feldern (street, postal_code, city, country).

### Migrationsskript

**Datei:** `backend/scripts/migrate_owner_addresses.sql`

### Ablauf

1. **Preview** (Step 1): Zeigt betroffene Owners
2. **Parse Preview** (Step 2): Zeigt was geparst würde
3. **Execute** (Step 3): Führt Migration aus (manuell auskommentieren)
4. **Verify** (Step 4): Zeigt Migrationsergebnis

### Unterstützte Formate

- Format A: `"Straße 123, 12345 Stadt"`
- Format B: `"Straße 123\n12345 Stadt"`

### Verification Path

```bash
# In Supabase SQL Editor:
# 1. Öffne backend/scripts/migrate_owner_addresses.sql
# 2. Führe Step 1 + 2 aus (Preview)
# 3. Prüfe Ergebnisse
# 4. Führe Step 3 aus (Migration)
# 5. Führe Step 4 aus (Verify)
```

**Status**: ✅ IMPLEMENTED

---

## GDPR Hard Delete / Anonymisierung (2026-02-23) - IMPLEMENTED

**Feature**: DSGVO Art. 17 - Recht auf Löschung ("Recht auf Vergessenwerden").

### Endpoint

`DELETE /api/v1/owners/{id}/gdpr-delete?confirm=true`

### Was wird anonymisiert

| Kategorie | Felder | Neuer Wert |
|-----------|--------|------------|
| Identität | first_name, last_name | "GELÖSCHT" |
| Kontakt | email | `deleted_xxx@anonymized.local` |
| Kontakt | phone | NULL |
| Adresse | address, street, postal_code, city, country | NULL |
| Steuerdaten | tax_id, vat_id, birth_date | NULL |
| Banking | iban, bic, bank_name | NULL |

### Was bleibt erhalten (Buchhaltung)

- Owner-ID (für Statement-Referenzen)
- commission_rate_bps (historisch)
- Statement-Records (nur Beträge, keine PII)

### Voraussetzungen

1. Owner muss **deaktiviert** sein (erst `DELETE /owners/{id}`)
2. Owner darf **keine Properties** zugewiesen haben
3. Nur **Admin-Rolle** kann ausführen
4. `confirm=true` erforderlich (Sicherheitscheck)

### Verification Path

```bash
# 1. Erst soft-delete
curl -X DELETE "${API}/api/v1/owners/${OWNER_ID}" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. Dann GDPR-Delete
curl -X DELETE "${API}/api/v1/owners/${OWNER_ID}/gdpr-delete?confirm=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 8: GDPR Hard Delete)

**Status**: ✅ IMPLEMENTED

---

## DAC7 XML-Export für Finanzamt (2026-02-23) - IMPLEMENTED

**Feature**: XML-Export im OECD DPI-Format für die Meldung an Finanzbehörden gemäß EU DAC7-Richtlinie.

### Endpoint

`GET /api/v1/dac7/export?year=2025`

### XML-Struktur (OECD DPI Schema)

| Element | Beschreibung |
|---------|--------------|
| `MessageSpec` | Metadaten (SendingEntity, Timestamp, ReportingPeriod) |
| `PlatformOperator` | Agency-Daten (Name, Adresse, Land) |
| `ReportableSeller` | Pro Owner mit Properties und Umsätzen |
| `ImmovableProperty` | Objekt-Typ (DPI903) mit Adressen |
| `Consideration` | Quartalweise Umsätze + Jahressumme |

### Exportierte Owner-Daten

| Kategorie | Felder |
|-----------|--------|
| Identität | first_name, last_name |
| Steuer-ID | tax_id (TIN), vat_id |
| Geburtsdatum | birth_date |
| Adresse | street, postal_code, city, country |

### Finanzielle Daten

- Quartalweise Aufschlüsselung (Q1-Q4)
- Umsatz pro Quartal (in EUR)
- Anzahl Aktivitäten (Buchungen)
- Jahressumme

### Voraussetzungen

1. Nur **Admin-Rolle** kann exportieren
2. Owner muss **is_active = true** sein
3. Owner muss mindestens **ein Property** haben
4. Properties müssen **Buchungen im Berichtsjahr** haben

### Verification Path

```bash
# DAC7 XML-Export für 2025 erstellen
curl -X GET "${API}/api/v1/dac7/export?year=2025" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o DAC7_Report_2025.xml

# XML validieren (Schema-Check)
xmllint --noout DAC7_Report_2025.xml
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 9: DAC7 XML-Export)

**Status**: ✅ IMPLEMENTED

---

## DAC7 Export UI auf /owners (2026-02-23) - IMPLEMENTED

**Feature**: Admin-UI für DAC7 XML-Export direkt auf der Eigentümer-Seite.

### UI-Komponenten

| Element | Beschreibung |
|---------|--------------|
| Export-Button | "DAC7 Export" Button im Header (nur für Admin sichtbar) |
| Modal | Jahr-Auswahl + Info-Box + Download-Button |
| Feedback | Erfolgs-/Fehlermeldungen im Modal |

### Funktionen

- Nur für **Admin-Rolle** sichtbar (`getUserRole(user) === "admin"`)
- Jahr-Dropdown (2024 bis aktuelles Jahr)
- Zeigt Meldefrist an (31. Januar Folgejahr)
- Download als XML-Datei

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/owners/page.tsx` | DAC7 Export Button + Modal |

### Verification Path

```bash
# 1. Als Admin einloggen
# 2. /owners öffnen
# 3. "DAC7 Export" Button klicken
# 4. Jahr auswählen → "XML herunterladen"
```

**Status**: ✅ IMPLEMENTED

---

## Immutable Objekt-ID (internal_name) (2026-02-23) - IMPLEMENTED

**Feature**: `internal_name` (Objekt-ID) ist nach Erstellung unveränderlich.

### Änderungen

- `internal_name` aus `allowed_fields` in `property_service.py` entfernt
- Auto-Generierung bei Erstellung: `OBJ-XXX` Format
- Migration für bestehende Properties mit leerem internal_name

**Dateien:**
- `backend/app/services/property_service.py`
- `backend/scripts/migrate_internal_names.sql`

**Status**: ✅ IMPLEMENTED

---

## Login Redirect zu /dashboard (2026-02-23) - IMPLEMENTED

**Feature**: Nach Login wird zu `/dashboard` statt `/channel-sync` weitergeleitet.

**Datei:** `frontend/app/login/page.tsx`

**Status**: ✅ IMPLEMENTED

---

## Fees/Taxes Umstrukturierung (Template-basiert) (2026-02-21) - IMPLEMENTED

**Feature**: Umstellung der Gebühren-/Steuerverwaltung auf Template-basiertes System. `/gebuehren-steuern` wird zur Agency-Level Template-Verwaltung, Property-Zuweisung erfolgt unter `/properties/[id]/gebuehren`.

### Architektur

| Seite | Zweck |
|-------|-------|
| `/gebuehren-steuern` | Agency-weite Fee/Tax-Templates definieren |
| `/properties/[id]/gebuehren` | Property-spezifische Fees/Templates zuweisen |

### Datenmodell

```
Agency-Template (property_id = NULL)
        ↓ "Zuweisen" = Kopie erstellen
Property-Fee (property_id = {uuid}, source_template_id = {template})
```

- **Fees**: Template + Kopie-Modell (Property bekommt eigene Kopie)
- **Steuern**: Nur Agency-Level (keine Property-spezifischen Steuern)

### Backend-Änderungen

| Datei | Änderung |
|-------|----------|
| `backend/app/schemas/pricing.py` | Neue Schemas: `PricingFeeTemplateResponse`, `AssignFeeFromTemplateRequest` |
| `backend/app/api/routes/pricing.py` | Neue Endpoints (siehe unten) |
| `supabase/migrations/20260221000000_add_pricing_fees_source_template.sql` | Neue Spalte `source_template_id` |

### Neue API Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /api/v1/pricing/fees/templates` | Nur Agency-Templates mit usage_count |
| `DELETE /api/v1/pricing/fees/{fee_id}` | Template löschen (nur wenn nicht verwendet) |
| `GET /api/v1/pricing/properties/{id}/fees` | Property-Fees mit source_template_name |
| `POST /api/v1/pricing/properties/{id}/fees/from-template` | Fee aus Template zuweisen |
| `DELETE /api/v1/pricing/properties/{id}/fees/{fee_id}` | Property-Fee entfernen |

### Frontend-Änderungen

| Datei | Änderung |
|-------|----------|
| `frontend/app/gebuehren-steuern/page.tsx` | Neue Template-Verwaltungsseite (kein Property-Dropdown) |
| `frontend/app/properties/[id]/gebuehren/page.tsx` | Neue Property-Gebühren-Seite |
| `frontend/app/properties/[id]/layout.tsx` | Neuer Tab "Gebühren" |
| `frontend/app/pricing/page.tsx` | Redirect zu `/gebuehren-steuern` |
| `frontend/app/components/AdminShell.tsx` | Navigation: `/pricing` → `/gebuehren-steuern` |

### Features

- **Template-Verwaltung**: Gebühren-Vorlagen auf Agency-Level erstellen
- **"Verwendet in X Objekte"**: Zeigt Usage-Count pro Template
- **Property-Zuweisung**: Templates kopieren oder eigene Gebühren erstellen
- **Quelle-Badge**: "Vorlage" vs "Manuell" auf Property-Seite
- **Table-to-Card**: Responsive Pattern gemäß CLAUDE.md §10
- **Steuern read-only**: Agency-weite Steuern auf Property-Seite anzeigen

### Verification Path

```bash
# 1. Templates-Seite
# → /gebuehren-steuern zeigt nur Agency-Templates
# → Kein Property-Dropdown mehr
# → "Verwendet in X Objekte" Spalte

# 2. Property-Seite
# → /properties/{id}/gebuehren zeigt:
#    - Zugewiesene Templates (mit "Vorlage" Badge)
#    - Property-spezifische Fees (mit "Manuell" Badge)
# → Template zuweisen funktioniert
# → Custom Fee erstellen funktioniert

# 3. Navigation
# → Sidebar zeigt "Gebühren & Steuern" → /gebuehren-steuern
# → /pricing redirected zu /gebuehren-steuern
```

**Status**: ✅ IMPLEMENTED

---

## Properties Table-to-Card Responsive UI (2026-02-21) - IMPLEMENTED

**Feature**: Responsive Table-to-Card Pattern für `/properties` Seite gemäß CLAUDE.md §10.

### Änderungen

| Bereich | Desktop (md+) | Mobile (<md) |
|---------|---------------|--------------|
| Objekt-Liste | Tabelle mit allen Spalten | Kompakte Karten |
| Header | Horizontal mit Buttons | Vertikal, Buttons full-width |
| Pagination | Inline | Gestapelt |
| Aktionen | 3-Dot-Menü | Text-Links im Card-Footer |

**Dateien**: `frontend/app/properties/page.tsx`

**Status**: ✅ IMPLEMENTED

---

## Season-Only Min Stay (2026-02-21) - IMPLEMENTED

**Feature**: Eliminierung von `properties.min_stay` und Umstellung auf `rate_plan_seasons.min_stay_nights` als einzige Quelle für Mindestaufenthalt.

### Fallback-Hierarchie

```
1. rate_plan_seasons.min_stay_nights  (Saison für Check-in-Datum)
   ↓ falls NULL oder keine Saison
2. rate_plans.min_stay_nights         (Rate-Plan Default)
   ↓ falls NULL
3. Hard-Default: 1 Nacht              (kein Minimum)
```

**Status**: ✅ IMPLEMENTED

---

## Rate-Plans Table-to-Card Redesign (2026-02-20) - IMPLEMENTED

**Feature**: Komplettes Redesign der Preiseinstellungen-Seite mit Table-to-Card Pattern.

**Dateien**: `frontend/app/properties/[id]/rate-plans/page.tsx`

**Status**: ✅ IMPLEMENTED

---

## Kurtaxen (Visitor Tax) Management Feature (2026-02-20) - IMPLEMENTED

**Feature**: Verwaltung von Kurtaxen pro Gemeinde mit saisonalen Tarifen und automatischer Property-Zuordnung via PLZ.

### Datenbank-Schema

| Tabelle | Beschreibung |
|---------|--------------|
| `visitor_tax_locations` | Gemeinden mit PLZ-Array für Auto-Matching |
| `visitor_tax_periods` | Saisonale Tarife (Betrag in Cents, Kinder-Freibetrag) |
| `properties.visitor_tax_location_id` | FK für Property-Zuweisung |

**Migration**: `supabase/migrations/20260220000000_add_visitor_tax.sql`

**Route**: `/kurtaxen` (Navigation unter OBJEKTE)

**Runbook**: [31-kurtaxen-visitor-tax.md](./ops/runbook/31-kurtaxen-visitor-tax.md)

**Status**: ✅ IMPLEMENTED

---

## Bookings Filter HTTP 500 Fix (2026-02-20) - IMPLEMENTED

**Problem**: Filtering bookings by status returned HTTP 500 errors.

**Solution**: Field normalization + NULL default handling in `booking_service.py`.

**Status**: ✅ IMPLEMENTED

---

## Luxe Token Elimination (2026-02-20) - IMPLEMENTED

**Objective**: Remove all hardcoded `luxe-*` design tokens and replace with dynamic semantic tokens.

**Deleted**: `app/components/luxe/` folder

**Status**: ✅ IMPLEMENTED

---

## RLS Security Fix (2026-02-24) - IMPLEMENTED

**Issue**: Critical security gap - Multiple tables had no Row Level Security (RLS) enabled, allowing potential cross-tenant data access.

### Phase 1: Initial Fix (8 tables)
**Migration**: `supabase/migrations/20260224120000_add_missing_rls_policies.sql`

| Table | Risk Level |
|-------|------------|
| `owners` | 🔴 CRITICAL |
| `rate_plans` | 🔴 CRITICAL |
| `rate_plan_seasons` | 🔴 CRITICAL |
| `pricing_fees` | 🔴 CRITICAL |
| `pricing_taxes` | 🔴 CRITICAL |
| `availability_blocks` | 🟠 HIGH |
| `inventory_ranges` | 🟠 HIGH |
| `channel_sync_logs` | 🟡 MEDIUM |

### Phase 2: Core Tables Repair (4 tables)
**Migration**: `supabase/migrations/20260224130000_repair_core_rls_policies.sql`

| Table | Risk Level |
|-------|------------|
| `profiles` | 🔴 CRITICAL |
| `properties` | 🔴 CRITICAL |
| `invoices` | 🔴 CRITICAL |
| `payments` | 🔴 CRITICAL |

### Phase 3: Complete Repair (12 tables)
**Migration**: `supabase/migrations/20260224140000_repair_all_missing_rls.sql`

| Table | Risk Level |
|-------|------------|
| `agencies` | 🔴 CRITICAL |
| `bookings` | 🔴 CRITICAL |
| `guests` | 🔴 CRITICAL |
| `team_members` | 🔴 CRITICAL |
| `channel_connections` | 🟠 HIGH |
| `direct_bookings` | 🟠 HIGH |
| `external_bookings` | 🟠 HIGH |
| `pricing_rules` | 🟠 HIGH |
| `webhooks` | 🟠 HIGH |
| `property_media` | 🟡 MEDIUM |
| `sync_logs` | 🟡 MEDIUM |
| `public_site_design` | 🟢 LOW |

**Total Tables Fixed**: 24

### Phase 4: Infinite Recursion Fix
**Migration**: `supabase/migrations/20260224150000_fix_rls_infinite_recursion.sql`

**Problem**: Die RLS Policies referenzierten `team_members` in Subqueries, was zu einer Endlosschleife führte:

```
User → SELECT FROM team_members
  → RLS Policy prüft: SELECT FROM team_members (Subquery)
    → RLS Policy prüft: SELECT FROM team_members (Subquery)
      → ... Endlosschleife
        → ERROR: infinite recursion detected in policy for relation "team_members"
```

**Lösung**: SECURITY DEFINER Funktionen, die RLS umgehen:

```sql
-- Funktion läuft mit Rechten des Erstellers (postgres), nicht des Users
-- Dadurch wird RLS umgangen und keine Rekursion ausgelöst
CREATE FUNCTION get_user_agency_ids()
RETURNS SETOF UUID
SECURITY DEFINER  -- ← Umgeht RLS
AS $$
  SELECT agency_id FROM team_members WHERE user_id = auth.uid();
$$;

-- Policy nutzt jetzt die Funktion statt Subquery
CREATE POLICY "team_members_select" ON team_members
  USING (agency_id IN (SELECT get_user_agency_ids()));
```

**Erstellte Helper-Funktionen**:
| Funktion | Zweck |
|----------|-------|
| `get_user_agency_ids()` | Gibt alle Agency-IDs des Users zurück |
| `user_has_agency_access(UUID)` | Prüft ob User Zugriff auf Agency hat |
| `get_user_role_in_agency(UUID)` | Gibt Rolle des Users in Agency zurück |

**Aktualisierte Policies** (13 Tabellen):
- `team_members`, `agencies`, `bookings`, `guests`
- `properties`, `profiles`, `invoices`, `payments`
- `owners`, `rate_plans`, `pricing_fees`, `pricing_taxes`
- `channel_connections`, `cancellation_policies`

**Warum SECURITY DEFINER?**
- Normale Funktionen laufen mit den Rechten des aufrufenden Users → RLS wird angewandt
- SECURITY DEFINER Funktionen laufen mit den Rechten des Erstellers (postgres) → RLS wird umgangen
- Dies ist der Standard-Ansatz für "Basis-Tabellen" wie `team_members`, die selbst die Quelle für Berechtigungsprüfungen sind

**Policy Pattern**:
- SELECT: Staff can read within agency
- INSERT/UPDATE: Manager+ for config tables, Staff+ for operational tables
- DELETE: Admin only for critical tables

**Verification Path**:
```sql
-- Test Helper-Funktionen:
SELECT get_user_agency_ids();
SELECT get_user_role_in_agency('agency-uuid-here');

-- Alle Tabellen sollten RLS aktiviert haben:
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public'
AND tablename NOT IN ('pms_schema_migrations', 'spatial_ref_sys', 'agency_domains', 'amenity_definitions');
-- Expected: All rows show rowsecurity = true
```

**Status**: ✅ IMPLEMENTED

---

## Redis TLS & PostgreSQL SSL (2026-02-25) - IMPLEMENTED

**Issue**: Redis-Verbindungen waren unverschlüsselt, PostgreSQL SSL war nicht explizit konfiguriert.

**Lösung**: TLS/SSL-Support für Redis und PostgreSQL implementiert.

**Änderungen**:

1. **Redis TLS** (`backend/app/core/redis.py`):
   - `_create_ssl_context()`: SSL-Context-Erstellung für TLS-Verbindungen
   - ConnectionPool akzeptiert nun `ssl` Parameter
   - Logging für TLS-Status

2. **Config** (`backend/app/core/config.py`):
   - `REDIS_TLS_ENABLED`: TLS aktivieren (default: false)
   - `REDIS_TLS_CERT_REQS`: Zertifikat-Validierung (none/optional/required)
   - `REDIS_TLS_CA_CERTS`: Pfad zu CA-Zertifikat

3. **Dokumentation** (`.env.example`):
   - PostgreSQL: `?ssl=require` dokumentiert
   - Redis: `rediss://` Protokoll dokumentiert
   - Celery: TLS-Konfiguration dokumentiert

**Konfiguration (Production)**:
```bash
# PostgreSQL mit SSL
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require

# Redis mit TLS
REDIS_URL=rediss://:password@redis-host:6379/0
REDIS_TLS_ENABLED=true
```

**Verification Path**:
- Logs prüfen: `docker logs pms-backend | grep -i "redis.*tls"`
- Health Check: `curl /health/ready` sollte `redis: up` zeigen

**Runbook**: [34-encryption-tls.md](./ops/runbook/34-encryption-tls.md)

**Status**: ✅ IMPLEMENTED

---

## CSP (Content-Security-Policy) (2026-02-25) - IMPLEMENTED

**Issue**: CSP mit Nonces blockierte alle Next.js Scripts, da Next.js 15 keine automatische Nonce-Injection unterstützt.

**Ursprünglicher Ansatz (2026-02-24)**: Nonce-basiertes CSP implementiert.
- Problem: Next.js 15 injiziert Hydration-Scripts ohne Nonce
- Resultat: Public Website komplett blank (alle JS blockiert)

**Aktuelle Lösung (2026-02-25)**: CSP mit `'unsafe-inline'` für script-src.

**Änderungen**:
- `frontend/middleware.ts`: CSP ohne Nonces
  - `script-src 'self' 'unsafe-inline' 'unsafe-eval'` (für Next.js Hydration)
  - `style-src 'self' 'unsafe-inline'`
- `CLAUDE.md`: Sektion 11 aktualisiert

**CSP-Direktiven**:
```
default-src 'self'
script-src 'self' 'unsafe-inline' 'unsafe-eval'
style-src 'self' 'unsafe-inline'
img-src 'self' data: blob: https://*.supabase.co ...
connect-src 'self' https://*.supabase.co ...
frame-ancestors 'none'
form-action 'self'
base-uri 'self'
object-src 'none'
```

**Verbleibende Schutzmaßnahmen**:
- `frame-ancestors 'none'` → Clickjacking-Schutz
- `object-src 'none'` → Flash/Plugin-Schutz
- HSTS, X-Frame-Options, X-Content-Type-Options → Aktiv
- Supabase Auth mit bcrypt → Passwort-Sicherheit

**Warum kein Nonce-CSP mit Next.js 15?**
- Next.js generiert interne Scripts ohne Nonce-Attribut
- `'strict-dynamic'` erfordert, dass initiale Scripts Nonces haben
- Kein offizieller Next.js 15 Support für automatische Nonces

**Status**: ✅ IMPLEMENTED

---

## Security Audit Fixes (2026-02-19) - IMPLEMENTED

**Audit Reference**: Audit-2026-02-19.md

**Resolved**: 12/15 findings (CRITICAL + HIGH vulnerabilities fixed)

**Open**: 3 findings (deferred - Channel Manager not enabled, MVP scope)

**Status**: ✅ IMPLEMENTED

---

## Property Filter Feature (2026-02-14) - IMPLEMENTED

**Overview**: Comprehensive property search and filter system for the public website.

**Features**:
- Filter by city, guests, bedrooms, price range, property type, amenities
- Three layout modes: sidebar, top, modal
- Admin control via `/website/filters`

**Status**: ✅ IMPLEMENTED

---

## Brand-Gradient Entfernung (2026-02-27) - IMPLEMENTED

**Issue**: Separate Gradient-Felder (`gradient_from`, `gradient_via`, `gradient_to`) führten zu Verwirrung mit der Akzentfarbe. Beide hatten ähnliche Auswirkung auf Logo-Hintergrund und aktive Navigation.

**Lösung**: Brand-Gradient-Felder komplett entfernt, Gradient wird nun ausschließlich aus der Akzentfarbe (`accent_color`) abgeleitet.

**Änderungen**:

1. **branding-form.tsx**:
   - Interface-Felder `gradient_from`, `gradient_via`, `gradient_to` entfernt
   - FormData defaults entfernt
   - useEffect-Mapping entfernt
   - Payload-Zeilen entfernt
   - Komplette "Brand-Gradient" UI-Sektion entfernt

2. **theme-provider.tsx**:
   - `ApiBrandConfig` Interface entfernt
   - `applyPremiumNavCssVariables()` vereinfacht - nutzt nur noch `accentColor`:
     ```typescript
     const gradientFrom = accentColor || "#f59e0b";
     const gradientVia = darkenColor(gradientFrom, 5);
     const gradientTo = darkenColor(gradientFrom, 15);
     ```
   - `BrandingConfig` Interface bereinigt
   - Alle Funktionsaufrufe angepasst

**Dateien**:
- `frontend/app/(admin)/settings/branding/branding-form.tsx`
- `frontend/app/lib/theme-provider.tsx`

**Auswirkung**: Akzentfarbe steuert nun konsistent Logo-Hintergrund und aktive Navigation. Keine separate Gradient-Konfiguration mehr nötig.

**Verification Path**:
- Browser: Settings > Branding > Akzentfarbe ändern
- CSS-Variablen prüfen: `--brand-primary-from` sollte der Akzentfarbe entsprechen

**Runbook**: [20-navigation-branding.md](./ops/runbook/20-navigation-branding.md#gradient-vereinfachung-2026-02-27)

**Status**: ✅ IMPLEMENTED

---

## Accessibility: Keyboard Navigation K2-Extended (2026-03-03) - IMPLEMENTED

**Issue**: Inline-Modals in der Admin-UI hatten keine FocusTrap-Implementierung, was gegen WCAG 2.1.2 "No Keyboard Trap" verstößt. Tab-Navigation konnte aus dem Modal herausspringen.

**Lösung**: `focus-trap-react` FocusTrap für alle 48 Modals in 13 Admin-Seiten implementiert.

**Features**:
- Tab-Navigation bleibt im Modal
- ESC schließt Modal (`escapeDeactivates: true`)
- Klick außerhalb schließt Modal (`clickOutsideDeactivates: true`)
- ARIA-Attribute für Screen Reader (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`)

**Änderungen**:

| Datei | Modals |
|-------|--------|
| `app/(admin)/properties/[id]/rate-plans/page.tsx` | 7 |
| `app/(admin)/seasons/page.tsx` | 7 |
| `app/(admin)/visitor-tax/page.tsx` | 7 |
| `app/(admin)/connections/page.tsx` | 5 |
| `app/(admin)/channel-sync/page.tsx` | 4 |
| `app/(admin)/booking-requests/page.tsx` | 4 |
| `app/(admin)/website/pages/page.tsx` | 1 |
| `app/(admin)/website/templates/page.tsx` | 1 |
| `app/(admin)/website/components/RichTextEditor.tsx` | 1 |
| `app/(admin)/website/pages/[id]/page.tsx` | 4 |
| `app/(admin)/properties/[id]/media/page.tsx` | 2 |
| `app/(admin)/properties/[id]/gebuehren/page.tsx` | 2 |
| `app/(admin)/fees-taxes/page.tsx` | 3 |

**Total**: 48 Modals in 13 Dateien

**Verification Path**:
1. Modal öffnen (z.B. Rate Plans > Import)
2. Tab-Taste → Focus bleibt im Modal
3. ESC → Modal schließt
4. Außerhalb klicken → Modal schließt

**Runbook**: [43-accessibility-keyboard.md](./ops/runbook/43-accessibility-keyboard.md)

**Status**: ✅ IMPLEMENTED

---

## Accessibility: Icon Button Labels K4 (2026-03-03) - IMPLEMENTED

**Issue**: Icon-only Buttons (z.B. Schließen-X, Menü-Dots) hatten keine `aria-label` Attribute. Screen Reader können diese Buttons nicht sinnvoll beschreiben.

**Lösung**: Alle Icon-Buttons mit `aria-label` für Screen Reader Unterstützung versehen.

**Pattern**:
```tsx
<button aria-label="Schließen" className="...">
  <X className="w-5 h-5" />
</button>
```

**Änderungen** (13 Dateien, 24 Buttons):
- `properties/page.tsx` - MoreVertical, Drawer close
- `properties/[id]/page.tsx` - 2x Modal close
- `properties/[id]/calendar/page.tsx` - Toast, Modal close
- `properties/[id]/extra-services/page.tsx` - Toast, Modal close
- `bookings/page.tsx` - Drawer close, Clear guest
- `guests/page.tsx` - Toast, Search clear, Drawer close
- `guests/[id]/page.tsx` - Toast, Drawer close
- `team/page.tsx` - 2x MoreVertical
- `amenities/page.tsx` - MoreVertical
- `media/page.tsx` - 3x Close buttons
- `extra-services/page.tsx` - Toast, Drawer close
- `notifications/email-outbox/page.tsx` - 2x Modal close
- `settings/branding/branding-form.tsx` - 2x Eye/EyeOff visibility toggles

**Status**: ✅ IMPLEMENTED

---

## Accessibility: Form Validation Error Links K5 (2026-03-03) - IMPLEMENTED

**Issue**: Formular-Validierungsfehler waren nicht programmatisch mit den zugehörigen Eingabefeldern verknüpft. Screen Reader konnten Fehlermeldungen nicht mit den korrekten Feldern assoziieren.

**Lösung**: `aria-describedby` und `aria-invalid` Attribute für alle Formularfelder mit Validierung implementiert.

**Pattern**:
```tsx
<label htmlFor="field-id">Feldname *</label>
<input
  id="field-id"
  aria-invalid={!!errors.field}
  aria-describedby={errors.field ? "field-id-error" : undefined}
  ...
/>
{errors.field && (
  <p id="field-id-error" role="alert" className="text-state-error">
    {errors.field}
  </p>
)}
```

**Änderungen** (3 Dateien, 11 Felder):
- `bookings/page.tsx` - property_id, check_in, check_out, num_adults (4 Felder)
- `website/templates/page.tsx` - name, block_type, block_props, style_overrides (4 Felder)
- `channel-sync/page.tsx` - connection_id, start_date, end_date (3 Felder, date_range Fehler)

**Status**: ✅ IMPLEMENTED

---

## Accessibility: Label-Input-Verknüpfung K2 (2026-03-07) - IMPLEMENTED

**Issue**: Weitere Labels ohne `htmlFor`/`id`-Verknüpfung in Admin-UI gefunden (WCAG 1.3.1, 4.1.2). Betrifft vor allem Website-Builder-Seiten und weitere Admin-Formulare.

**Lösung**: `htmlFor` und `id` Attribute systematisch ergänzt. Dynamische IDs für Felder in Schleifen (z.B. `` `block-prop-${key}` ``, `` `array-${fieldName}-${index}-${fieldKey}` ``).

**Änderungen** (18 Dateien, ~80 Labels):

| Datei | Labels | ID-Prefix |
|-------|--------|-----------|
| `booking-requests/components/ManualBookingModal.tsx` | 9 | `manual-booking-` |
| `owners/[ownerId]/page.tsx` | 12 | `owner-` |
| `properties/[id]/gebuehren/page.tsx` | 3 | `custom-fee-` |
| `properties/[id]/calendar/page.tsx` | 1 | `calendar-` |
| `properties/[id]/extra-services/page.tsx` | 3 | dynamisch mit `assignment.id` |
| `properties/[id]/media/page.tsx` | 1 | `property-media-` |
| `notifications/email-outbox/page.tsx` | 1 | `test-email-` |
| `media/page.tsx` | 3 | dynamisch mit `file.id` |
| `website/pages/[id]/components/PageSettingsModal.tsx` | 5 | `page-settings-` |
| `website/pages/[id]/components/SaveTemplateModal.tsx` | 2 | `save-template-` |
| `website/pages/page.tsx` | 3 | `new-page-` |
| `website/templates/page.tsx` | 3 | `template-` |
| `website/pages/[id]/components/BlockPropsEditor.tsx` | 10 | `block-prop-${key}` |
| `website/components/ArrayItemEditor.tsx` | 8 | `array-${fieldName}-${index}-${fieldKey}` |
| `website/pages/[id]/components/BlockStyleEditor.tsx` | 26 | `style-` |
| `website/pages/[id]/components/SectionPropsEditor.tsx` | 2 | `section-` |

**Ausnahmen (kein htmlFor noetig)**:
- Wrapping Labels (`<label><input .../></label>`) — bereits accessible
- Display-only Labels (Label + `<p>` Text, ohne Input)
- Labels für Button-Groups (kein einzelnes Input-Element)
- Labels für ImagePicker/RichTextEditor (Komponenten verwalten eigene a11y)
- Color-Inputs (type="color") erhalten `aria-label` statt htmlFor

**Verification Path**:
```bash
rg -l "htmlFor=" frontend/app/\(admin\)/
rg "id=\"(manual-booking|owner|custom-fee|calendar|property-media|test-email|page-settings|save-template|new-page|template|style|section)-" frontend/app/\(admin\)/
```

**Status**: ✅ IMPLEMENTED

---

## Accessibility: Label-Input-Verknüpfung K1 (2026-03-03) - IMPLEMENTED

**Issue**: Formular-Labels waren nicht programmatisch mit ihren Eingabefeldern verknüpft. Screen Reader konnten Labels und Inputs nicht zuordnen (WCAG 1.3.1, 4.1.2).

**Lösung**: `htmlFor` und `id` Attribute für alle Labels und Eingabefelder in Admin-UI implementiert.

**Pattern**:
```tsx
<label htmlFor="page-fieldname">Feldname</label>
<input id="page-fieldname" ... />
```

**ID-Namenskonvention**: `{seite}-{feldname}` (z.B. `booking-guest-email`, `property-edit-name`)

**Änderungen** (23 Dateien, ~200 Labels):

| Datei | Labels |
|-------|--------|
| `bookings/page.tsx` | 12 |
| `bookings/[id]/page.tsx` | 5 |
| `guests/page.tsx` | 7 |
| `guests/[id]/page.tsx` | 10 |
| `properties/page.tsx` | 34 |
| `properties/[id]/page.tsx` | 37 |
| `properties/[id]/rate-plans/page.tsx` | 10 |
| `seasons/page.tsx` | 13 |
| `visitor-tax/page.tsx` | 18 |
| `team/page.tsx` | 3 |
| `extra-services/page.tsx` | 4 |
| `amenities/page.tsx` | 5 |
| `fees-taxes/page.tsx` | 6 |
| `cancellation-rules/page.tsx` | 5 |
| `connections/page.tsx` | 10 |
| `profile/edit/page.tsx` | 9 |
| `profile/security/page.tsx` | 3 |
| `organization/page.tsx` | 13 |
| `settings/branding/branding-form.tsx` | 10 |
| `settings/roles/page.tsx` | 7 |
| `website/domain/page.tsx` | 1 |
| `website/seo/page.tsx` | 4 |
| `website/design/design-form.tsx` | 22 |

**Ausnahmen**: Checkbox-Labels die ihr Input umschließen (`<label><input type="checkbox"/>...</label>`) brauchen kein htmlFor.

**Verification Path**:
```bash
# Prüfen dass Labels htmlFor haben
rg -l "htmlFor=" frontend/app/\(admin\)/

# Prüfen dass IDs vorhanden sind
rg "id=\"(booking|guest|property|season|visitor-tax|team|profile|org|branding|seo|design)-" frontend/app/\(admin\)/
```

**Status**: ✅ IMPLEMENTED

---

## Status Semantics

| Status | Bedeutung |
|--------|-----------|
| ✅ IMPLEMENTED | Feature deployed, manual testing completed, docs updated |
| ✅ VERIFIED | IMPLEMENTED + automated production verification passed |

---

## Archiv

Historische Einträge (Phase 1-20, vor 2026-02-14) wurden ausgelagert:

➡️ **[project_status_archive.md](./project_status_archive.md)** - Vollständige Projekthistorie (32.000+ Zeilen)

---

## Accessibility Audit Abschluss A-08, A-04, A-09, A-10 (2026-03-04) - IMPLEMENTED

**Scope**: WCAG 2.1 Compliance - aria-live Regionen, Form-Labels, Dekorative Icons, Skeleton Loading.

### A-08: aria-live Regionen für dynamische Inhalte (WCAG 4.1.3)

Screen Reader erhalten nun Ankündigungen bei Lade- und Ergebnis-Zuständen.

**Pattern**:
```tsx
const [ariaAnnouncement, setAriaAnnouncement] = useState("");
useEffect(() => {
  if (loading) setAriaAnnouncement("Lade Daten...");
  else setAriaAnnouncement(`${items.length} Einträge geladen`);
}, [loading, items.length]);

<div aria-live="polite" aria-atomic="true" className="sr-only">
  {ariaAnnouncement}
</div>
```

**Implementiert in**: `bookings/page.tsx`, `guests/page.tsx`, `properties/page.tsx`, `team/page.tsx`

**i18n**: `de.json` und `en.json` um `aria` Sektion erweitert.

### A-04: Form-Labels mit htmlFor/id Paaren (WCAG 1.3.1, 3.3.2)

Alle Formularfelder haben nun programmatisch verknüpfte Labels.

**Pattern**:
```tsx
<label htmlFor="field-id">Feldname</label>
<input id="field-id" ... />
```

**Implementiert in**: `BuchungClient.tsx` (10 Felder), `channel-sync/page.tsx` (4 Felder), `website/filters/page.tsx`, `BlockRenderer.tsx`

### A-09: Dekorative Icons mit aria-hidden (WCAG 1.1.1)

80+ Lucide-Icons mit `aria-hidden="true"` für Screen Reader ausgeblendet.

**Pattern**:
```tsx
<Icon className="w-4 h-4" aria-hidden="true" />
```

**Implementiert in**: Toast, ErrorBoundary, ProfileDropdown, TopBar, MobileDrawer, Breadcrumb, ImpersonationBanner, FooterServer, PropertyFilter, MonthQuickNav, ViewToggle, PropertySidebar, BookingPopover, Modal, Alert, ConfirmDialog, BuchungClient, BlockRenderer (18 Komponenten)

### A-10: Konsistente Skeleton Loading Screens

Neue wiederverwendbare `Skeleton.tsx` Komponente mit:
- `Skeleton` - Basis-Block mit animate-pulse
- `SkeletonText` - Textzeilen-Platzhalter
- `SkeletonAvatar` - Runde Avatar-Platzhalter
- `SkeletonTable` / `SkeletonTableRow` - Tabellen-Skeleton
- `SkeletonList` - Mobile Karten-Liste
- `SkeletonGrid` - Grid-Layout

**Ersetzt** Spinner-Loading durch konsistente Skeleton-Screens (responsive: Desktop=Table, Mobile=List).

**Implementiert in**: `bookings/page.tsx`, `guests/page.tsx`, `properties/page.tsx`, `team/page.tsx`

### Änderungen

| Datei | Änderung |
|-------|----------|
| `frontend/app/components/ui/Skeleton.tsx` | Neue Komponente (8 Varianten) |
| `frontend/app/(admin)/bookings/page.tsx` | aria-live, SkeletonTable/List |
| `frontend/app/(admin)/guests/page.tsx` | aria-live, SkeletonTable/List |
| `frontend/app/(admin)/properties/page.tsx` | aria-live, SkeletonTable/List |
| `frontend/app/(admin)/team/page.tsx` | aria-live, SkeletonTable/List |
| `frontend/app/(public)/buchung/BuchungClient.tsx` | htmlFor/id, aria-hidden |
| `frontend/app/(public)/components/BlockRenderer.tsx` | htmlFor/id, aria-hidden |
| `frontend/app/components/*.tsx` (18 Dateien) | aria-hidden für Icons |
| `frontend/app/lib/i18n/translations/de.json` | aria Sektion |
| `frontend/app/lib/i18n/translations/en.json` | aria Sektion |

### Commits

- `8b30ead`: fix(a11y): WCAG compliance - aria-live, htmlFor, aria-hidden
- `c54c39a`: feat(ui): add consistent skeleton loading screens (A-10)

### Verification Path

1. **aria-live Test**: Öffne Buchungen-Seite → Screen Reader sollte "Lade Buchungen..." und dann "X Buchungen geladen" ansagen
2. **Form-Labels Test**: Tab durch BuchungClient → Screen Reader liest Label für jedes Feld
3. **Icon Test**: axe DevTools → Keine "Images must have alternate text" Fehler für dekorative Icons
4. **Skeleton Test**: Öffne Gäste-Seite → Skeleton-Blöcke erscheinen statt Spinner

### Status

✅ **Accessibility Audit vollständig abgeschlossen**: 10/10 Items behoben

| Kategorie | Behoben |
|-----------|---------|
| P1 Kritisch | 5 |
| P2 Wichtig | 3 |
| P3 Moderat | 2 |
| **Gesamt** | **10** |

---

---

## God-Files aufteilen (Audit Fix 6.3) — ✅ IMPLEMENTED

### Beschreibung

Alle Route-Dateien >800 Zeilen in Python-Packages mit Sub-Modulen aufgeteilt. Reine Datei-Reorganisation, keine Logik-Änderungen. Alle Imports in `main.py` und `modules/` bleiben unverändert (Python behandelt Packages wie Module).

### Aufgeteilte Dateien

| Datei | Zeilen | Aufgeteilt in | Dateien |
|-------|--------|---------------|---------|
| `booking_requests.py` | 1.884 | Package `booking_requests/` | 6 |
| `season_templates.py` | 2.142 | Dateien in `pricing/` | 4 |
| `website_admin.py` | 1.348 | Package `website_admin/` | 6 |
| `availability.py` | 1.346 | Package `availability/` | 5 |
| `branding.py` | 1.197 | Package `branding/` | 3 |
| `public_site.py` | 1.143 | Package `public_site/` | 6 |
| **Gesamt** | **~9.000** | **6 Packages** | **30 Dateien** |

### Übersprungen

- `property_service.py` (1.468 Zeilen): Service-Klasse (keine Routes), Aufteilung einer einzelnen Klasse riskanter als Routes

### Dateien

| Pfad | Änderung |
|------|----------|
| `backend/app/api/routes/booking_requests/` | NEU: Package mit 6 Sub-Modulen |
| `backend/app/api/routes/pricing/season_template_*.py` | NEU: 4 Sub-Module |
| `backend/app/api/routes/pricing/__init__.py` | Angepasst: season_template Imports |
| `backend/app/api/routes/website_admin/` | NEU: Package mit 6 Sub-Modulen |
| `backend/app/api/routes/availability/` | NEU: Package mit 5 Sub-Modulen |
| `backend/app/api/routes/branding/` | NEU: Package mit 3 Sub-Modulen |
| `backend/app/api/routes/public_site/` | NEU: Package mit 6 Sub-Modulen |

### Verification Path

```bash
python3 -m compileall backend/app/api/routes/ -q  # EXIT 0 = OK
```

### Status

✅ IMPLEMENTED

---

## CQ-01: Code-Qualität FIXPLAN Stufen 5-8 (2026-03-08) — IMPLEMENTED

**Scope:** Umfassende Code-Qualität-Verbesserungen basierend auf 98 Findings aus 3 Audits.

### Änderungen

**Stufe 5 — Error Handling Konsistenz:**
- Redundante Exception Re-Catches entfernt (bookings.py)
- Domain Exception Pass-Through vor Catch-All in Dashboard/Bookings
- Error Detail Format standardisiert (immer String statt Dict)
- Public Layout Error Boundary (`error.tsx`) hinzugefügt

**Stufe 6 — Frontend Patterns & Cleanup:**
- Mock-Daten aus Connections-Formular entfernt (mock_access_token, mock_mode defaults)
- console.warn/debug Statements entfernt (api-client, properties)
- Error State standardisiert: `useState("")` → `useState<string | null>(null)` in 5 Dateien
- Standalone `useDebounce` Hook extrahiert, Inline-Kopie in availability ersetzt

**Stufe 7 — Performance:**
- React.memo für PropertyRow, PropertyCard, BookingRequestRow, BookingRequestCard
- Dashboard Revenue: Python-Loop (7 Queries) → single `generate_series()` Query

**Stufe 8 — Naming & Hygiene:**
- aria-label für 14 Icon-Only Buttons (RichTextEditor, ArrayItemEditor)
- get_db → get_db_authed in extra_services Routes (9 Endpoints)

### Betroffene Dateien
- Backend: dashboard.py, bookings.py, extra_services.py, deps.py, schemas/dashboard.py
- Frontend: 15+ Dateien (availability, connections, seasons, visitor-tax, properties, booking-requests, website)

### Verification Path
```bash
cd frontend && npm run build  # EXIT 0 = OK
python3 -m compileall backend/app/ -q  # EXIT 0 = OK
```

### Status

✅ IMPLEMENTED

---

## CQ-02: Service-Layer Extraktion Stufe 4.2-4.4 (2026-03-08) — IMPLEMENTED

**Scope:** SQL-Logik aus 3 Route-Dateien in eigenständige Service-Klassen extrahieren.

### Änderungen

- **ExtraServiceService** (`services/extra_service_service.py`): 9 Endpoints, 24 SQL-Queries
  - Shared Helpers: `_verify_property_access()`, `_fetch_with_tax()`
  - Route-Datei: 597 → 274 Zeilen
- **VisitorTaxService** (`services/visitor_tax_service.py`): 13 Endpoints, 39 SQL-Queries
  - Shared Helpers: `_verify_location_access()`, `_fetch_periods_for_location()`, `_build_dynamic_update()`
  - Route-Datei: 878 → 338 Zeilen
- **DashboardService** (`services/dashboard_service.py`): 3 Endpoints, 32 SQL-Queries
  - Owner/Staff-Varianten beibehalten (1:1 Verhaltens-Erhalt)
  - Route-Datei: 683 → 186 Zeilen

**Zentrale Constants** (`core/constants.py`):
- `ZERO_UUID` — konsolidiert aus 3 Dateien
- `BookingStatus` — Klasse mit Status-Konstanten + Sets (OCCUPYING, ACTIVE, COMPLETED)
- `BookingRequestStatus` — Booking-Request-Status-Konstanten

### Betroffene Dateien
- Neue Services: 3 (extra_service_service.py, visitor_tax_service.py, dashboard_service.py)
- Neue Constants: 1 (core/constants.py)
- Geänderte Routes: 3 (extra_services.py, visitor_tax.py, dashboard.py)
- Geänderte DI: 1 (deps.py)
- Geänderte Services: 2 (booking/create.py, booking/query.py)
- Geänderte Schemas: 1 (bookings.py)

### Verification Path
```bash
python3 -m compileall backend/app/ -q  # EXIT 0 = OK
```

### Status

✅ IMPLEMENTED

---

---

## P5.5 ManualBookingModal → CreateBookingDrawer

### Was
- Unvollständiges ManualBookingModal (282 Zeilen) durch vollwertigen CreateBookingDrawer ersetzt
- booking-requests Seite nutzt jetzt denselben Drawer wie /bookings

### Wo
- `frontend/app/(admin)/booking-requests/page.tsx` (Import + State angepasst)
- `frontend/app/(admin)/booking-requests/components/ManualBookingModal.tsx` (GELÖSCHT)

### Status
✅ IMPLEMENTED

---

## P5.7 AvailabilityCalendar + AvailabilityDatePicker

### Was
- Wiederverwendbarer Verfügbarkeitskalender mit Farbkodierung:
  - Grün: verfügbar (mit Nachtpreis-Anzeige)
  - Rot: belegt (nicht klickbar)
  - Amber (#fde68a): gesperrt/Sperrzeit (nicht klickbar, mit Grund-Tooltip)
  - Grau: kein Saisonpreis definiert (nicht klickbar)
  - Diagonal rot/grün: Wechseltag (Check-in möglich)
  - Vergangenheit: ausgegraut
- AvailabilityDatePicker: Popover-Wrapper (analog zu DatePicker)
- Integration in CreateBookingDrawer: DatePicker durch AvailabilityDatePicker ersetzt
- Check-in Reset bei neuer Auswahl setzt Check-out zurück
- Min-Stay Enforcement im Check-out Modus
- Barriere-Logik: verhindert Check-out über Buchungen/Sperrzeiten/Preislücken hinweg
- WCAG Keyboard Navigation (role="grid", Arrow Keys, Enter/Space)
- Automatisches API-Fetching (Availability + Rate-Plan Seasons)

### Wo
- `frontend/app/components/ui/AvailabilityCalendar.tsx` (NEU)
- `frontend/app/components/ui/AvailabilityDatePicker.tsx` (NEU)
- `frontend/app/(admin)/bookings/components/CreateBookingDrawer.tsx` (DatePicker → AvailabilityDatePicker)

### Verification Path
```bash
# Build-Verifikation
cd frontend && npm run build  # EXIT 0
# Live-Test: Neue Buchung erstellen → Kalender muss Farben/Preise zeigen
```

### Status
✅ IMPLEMENTED

---

---

## P5.8 Bookings/Booking-Requests UX-Überarbeitung (2026-03-09)

### Was wurde geändert
- Status-Filter `/bookings`: `requested`, `under_review`, `inquiry` entfernt (gehören nur in `/booking-requests`)
- "Neue Buchung" Button aus `/booking-requests` entfernt (nur in `/bookings`)
- Genehmigungs-Toast zeigt Link "Zur Buchung →" zu `/bookings?highlight={id}`
- Sidebar-Badge: Zähler offener Anfragen neben "Anfragen" Nav-Item (auto-refresh 60s)
- Cross-Navigation Banner auf `/bookings`: Warnung bei offenen Anfragen mit Link
- Drawer-Breite: Alle Admin-Drawer auf `md:w-[60%] lg:w-1/3` standardisiert
- Toast-Komponente: optionaler Action-Link Support

### Wo
- `frontend/app/(admin)/bookings/page.tsx`
- `frontend/app/(admin)/booking-requests/page.tsx`
- `frontend/app/components/AdminShell.tsx`
- `frontend/app/components/admin-shell/SidebarNavigation.tsx`
- `frontend/app/components/Toast.tsx`
- 9 Drawer-Dateien (width-Standardisierung)

### Verification Path
```bash
cd frontend && npm run build  # EXIT 0
# Live-Test: /bookings Banner + /booking-requests Genehmigung mit Link
# Sidebar-Badge: offene Anfragen sichtbar
```

### Status
✅ IMPLEMENTED

---

---

## P5.10 Availability-Check, Mixed-Content-Fix & Booking-Approve-Constraint (2026-03-10)

### Was wurde geändert

**Availability Internal Proxy (Mixed-Content-Prävention):**
- Neuer interner API-Proxy `frontend/app/api/internal/availability/route.ts` erstellt
- Availability-Calls in Booking-Requests-Seite und Drawer nutzen jetzt `/api/internal/availability` mit `fetch()` statt `apiClient.get()` direkt an `/api/v1/availability/`
- Verhindert Mixed-Content-Fehler (Browser blockiert HTTP-Requests von HTTPS-Seite)

**Mixed-Content-Hardening (api-client.ts):**
- `getApiBase()` in `frontend/app/lib/api-client.ts` — robustes HTTPS-Protokoll-Matching
- Belt-and-Suspenders Check in `apiRequest()` als zusätzliche Absicherung

**CSP Security Hardening:**
- `frontend/middleware.ts` — unsicheres `http://api.fewo.kolibri-visions.de` aus CSP `connect-src` entfernt

**Booking-Request Approve Constraint Fix:**
- `backend/app/api/routes/booking_requests/actions.py` — `cancelled_by=user_id` aus Approve-Query entfernt
- Fehler: Feld verletzte `bookings_cancelled_by_check` Constraint (cancelled_by darf nur bei Status cancelled gesetzt sein)

### Wo
- `frontend/app/api/internal/availability/route.ts` (NEU)
- `frontend/app/lib/api-client.ts`
- `frontend/middleware.ts`
- `frontend/app/(admin)/booking-requests/page.tsx`
- `frontend/app/(admin)/booking-requests/components/RequestDetailDrawer.tsx`
- `backend/app/api/routes/booking_requests/actions.py`

### Migrationen
Keine.

### Verification Path
```bash
cd frontend && npm run build  # EXIT 0
# Live-Test: Booking-Request genehmigen → kein DB-Constraint-Fehler
# Live-Test: Availability-Badge in /booking-requests lädt ohne Mixed-Content-Fehler
# CSP: Keine http:// Origins in connect-src
```

### Status
✅ IMPLEMENTED

---

---

## Stufe 9+10: Availability/Bookings Konsistenz + A11y (2026-03-10)

### Was wurde geändert
- **9.1 (KRITISCH):** DB-Migration `20260310000001` — `under_review` zu `bookings_status_check` Constraint hinzugefügt
- **9.2:** Backend `BookingRequestStatus` Enum definiert, alle `status: str` durch typisiertes Literal ersetzt
- **9.3 + 9.6:** Datum-Feldnamen-Konvention + Availability-State-Semantik in `conventions.md` dokumentiert
- **10.1:** Availability Refresh-Button: `aria-label="Aktualisieren"` ergänzt
- **10.2:** ViewToggle-Buttons: `aria-label` für Icon-only Buttons
- **10.3:** Availability Suchfeld: `<label>` mit `htmlFor` + `id` verknüpft (WCAG 1.3.1)
- **10.5:** Booking-Requests Row: `aria-label` für Approve/Decline/Detail Icon-Buttons
- **10.6:** Booking-Requests Mobile Cards: `role="button"` + `tabIndex` + `onKeyDown` für Tastaturzugänglichkeit
- **10.7:** Drawer Close-Button + Toast Close-Button: `aria-label` ergänzt

### Wo
- `supabase/migrations/20260310000001_add_under_review_status.sql`
- `backend/app/schemas/booking_requests.py`
- `backend/docs/conventions.md`
- `frontend/app/(admin)/availability/page.tsx`
- `frontend/app/components/calendar/ViewToggle.tsx`
- `frontend/app/(admin)/booking-requests/components/BookingRequestRow.tsx`
- `frontend/app/(admin)/booking-requests/components/BookingRequestCard.tsx`
- `frontend/app/(admin)/booking-requests/components/RequestDetailDrawer.tsx`
- `frontend/app/(admin)/booking-requests/page.tsx`

### Migrationen
- `20260310000001_add_under_review_status.sql` — Erweitert bookings_status_check Constraint

### Verification Path
```bash
cd frontend && npm run build  # EXIT 0
python3 -m py_compile backend/app/schemas/booking_requests.py  # EXIT 0
# DB-Migration auf Staging ausführen und prüfen
# Playwright e2e/availability-explore.spec.ts (8/13 pass, 3 rate-limited, 2 minor)
```

### Status
✅ IMPLEMENTED

---

## DSGVO Gast-Datenexport (Art. 15/20) (2026-03-11) - IMPLEMENTED

**Feature**: Administratoren können alle personenbezogenen Daten eines Gastes als JSON exportieren (DSGVO Art. 15 Auskunftsrecht / Art. 20 Datenportabilität).

### Endpoint

`GET /api/v1/guests/{guest_id}/dsgvo-export`

### Exportierte Daten

| Kategorie | Beschreibung |
|-----------|-------------|
| Stammdaten | Name, E-Mail, Telefon |
| Adressdaten | address_line1/2, city, postal_code, country |
| Identitätsdaten | date_of_birth, nationality, Ausweisdaten |
| Buchungsdaten | Alle Buchungen (Property, Zeitraum, Status, Preis) |
| Direktbuchungs-Metadaten | UTM-Parameter, Referrer, User-Agent (OHNE IP) |
| Einwilligungsdaten | marketing_consent, marketing_consent_at |
| Profilnotizen | profile_notes, VIP-Status, Blacklist-Status |

### Datenminimierung (Art. 5 Abs. 1 lit. c)

- `guest_ip` wird bewusst NICHT exportiert (nicht erforderlich für Auskunft)

### RBAC

- Nur **Admin-Rolle** kann Export ausführen
- Export wird als `critical=True` im Audit-Log protokolliert

### Dateien

- `backend/app/schemas/guests.py` — GuestDataExportResponse + Hilfs-Schemas
- `backend/app/services/guest_service.py` — export_guest_data() Methode
- `backend/app/api/routes/guests.py` — GET /guests/{id}/dsgvo-export Endpoint
- `frontend/app/(admin)/guests/[id]/page.tsx` — DSGVO-Export Button (Admin only)

### Verification Path

```bash
python3 -m py_compile backend/app/schemas/guests.py   # EXIT 0
python3 -m py_compile backend/app/services/guest_service.py  # EXIT 0
python3 -m py_compile backend/app/api/routes/guests.py  # EXIT 0
cd frontend && npx tsc --noEmit  # EXIT 0
```

### Status
✅ IMPLEMENTED

---

## Meldewesen / Meldescheine (BMG §29-30) (2026-03-11) - IMPLEMENTED

### Was wurde geändert
- Meldeschein-Modul für ausländische Gäste (seit 01.01.2025 Pflicht)
- DB-Migration: `registration_forms` Tabelle mit RLS-Policies
- Backend: 7 Endpoints (CRUD, Sign, Print, Delete)
- Frontend: Meldeschein-Sektion in Buchungsdetails, Meldescheine-Listenseite
- SignaturePad-Komponente (react-signature-canvas)
- HTML-basierter Druckbarer Meldeschein (BMG-konform)
- Alter-Spalte + manuelle Löschung ab 15 Monaten (BMG §30 Abs. 4)
- Navigation: Meldescheine als Sub-Item unter Buchungen

### Wo
- `supabase/migrations/20260311000001_create_registration_forms.sql`
- `backend/app/schemas/registration.py`
- `backend/app/services/registration_service.py`
- `backend/app/api/routes/registrations.py`
- `backend/app/modules/registrations.py`
- `frontend/app/(admin)/registrations/page.tsx`
- `frontend/app/(admin)/bookings/components/RegistrationSection.tsx`
- `frontend/app/components/ui/SignaturePad.tsx`

### Verification Path
```bash
# Meldescheine-Seite öffnen
curl -s https://admin.fewo.kolibri-visions.de/registrations
# API-Endpoint prüfen
curl -s -H "Authorization: Bearer $TOKEN" https://api.fewo.kolibri-visions.de/api/v1/registrations
```

### Status
✅ IMPLEMENTED

---

## Cleanup Sprint: Dead Code + UI-Vereinheitlichung (2026-03-11) - IMPLEMENTED

### Was wurde geändert
- **Dead Code entfernt:** `backend/app/core/entitlements.py` (ungenutzter Stub, 0 Imports), `backend/app/modules/api_v1.py` (Legacy-Wrapper, 0 Imports)
- **Phone-Validator Fix:** Leerer String `''` crashte Pydantic-Validator auf Gäste-Seite 2 → normalisiert zu `None`
- **Tab-Design vereinheitlicht:** `rounded-none` gegen globale Button-Rundung, `bg-t-primary/15` + `hover:border-stroke-default` auf allen 9 Tab-Implementierungen (Referenz: properties layout)
- **Media API Pagination:** `page/page_size` → `limit/offset` migriert (Backend Schema/Route/Service + Frontend Types/API-Client/Pages)
- **BlockRenderer Normalization:** Zentrale `normalize-props.ts` Utility ersetzt duplizierte `props.x || props.y` Fallbacks in 5 Block-Komponenten
- **Media-Tabs Farb-Token:** `text-t-accent` → `text-t-primary` korrigiert

### Wo
- `backend/app/schemas/validators.py` (Phone-Fix)
- `backend/app/schemas/media.py`, `backend/app/api/routes/media.py`, `backend/app/services/media.py` (Pagination)
- `frontend/app/(public)/components/blocks/normalize-props.ts` (NEU)
- `frontend/app/(public)/components/blocks/{Hero,CTA,Offer,Location,Testimonials}Block.tsx`
- 9 Admin-Seiten (Tab-Styling): registrations, fees-taxes, branding, navigation, guests, gebuehren, media, page-editor, block-picker

### Verification Path
```bash
# Gäste-Seite Seite 2 laden (Phone-Validator)
curl -s -H "Authorization: Bearer $TOKEN" "https://api.fewo.kolibri-visions.de/api/v1/guests?limit=25&offset=25"
# Media API mit neuem Format
curl -s -H "Authorization: Bearer $TOKEN" "https://api.fewo.kolibri-visions.de/api/v1/media?limit=24&offset=0"
# Frontend Build
cd frontend && npm run build  # EXIT 0
```

### Status
✅ IMPLEMENTED

---

---

## P9: Hardcoded Domains → Env-Vars (2026-03-11) - IMPLEMENTED

### Was wurde geändert

**Backend:**
- `public_domain_admin.py`: 3x hardcodiertes `fewo.kolibri-visions.de` → `os.environ.get("PUBLIC_DNS_TARGET", "fewo.kolibri-visions.de")`
- `schemas/public_site.py`: Schema-Default ebenfalls aus `PUBLIC_DNS_TARGET` Env-Var
- Guidance-Text bei Verifizierungsfehler dynamisch

**Frontend:**
- `middleware.ts`: CSP `img-src` + `connect-src` dynamisch aus `NEXT_PUBLIC_SB_URL` / `NEXT_PUBLIC_API_BASE`
- `next.config.js`: Image hostname aus `NEXT_PUBLIC_SB_URL`, API-Fallback aus `API_BASE_URL` / `NEXT_PUBLIC_API_BASE`
- `vitals/route.ts`: API-Fallback aus `API_BASE_URL` / `NEXT_PUBLIC_API_BASE`
- `domain/page.tsx`: Fallback-Default entfernt (Backend liefert echten Wert)
- `organization/page.tsx`: Fallback neutral ("Ihren Server" statt hardcodiert)
- `playwright.config.ts`: `PLAYWRIGHT_BASE_URL` Env-Var (Default: localhost)

### Neue Env-Vars

| Env-Var | Wo | Default | Beschreibung |
|---------|-----|---------|-------------|
| `PUBLIC_DNS_TARGET` | Backend (Coolify) | `fewo.kolibri-visions.de` | CNAME-Ziel für Custom Domains |
| `PLAYWRIGHT_BASE_URL` | Lokal/CI (optional) | `http://localhost:3000` | Test-URL für E2E |

### Bestehende Env-Vars (bereits konfiguriert)
- `NEXT_PUBLIC_SB_URL` — Supabase URL (ersetzt `sb-pms.kolibri-visions.de`)
- `NEXT_PUBLIC_API_BASE` / `API_BASE_URL` — Backend URL (ersetzt `api.fewo.kolibri-visions.de`)

### Revert
```bash
git reset --hard pre-p9-hardcoded-domains
```

### Verification Path
- Frontend Build: `cd frontend && npm run build` → OK
- Backend Syntax: `ast.parse()` → OK
- Grep-Check: Keine funktionalen hardcodierten Domains mehr in App-Code (nur Defaults/Kommentare)

### Status
✅ IMPLEMENTED

---

---

## P3: CI/CD Workflow-Fixes (2026-03-11) - IMPLEMENTED

### Was wurde geändert

**post-deploy-check.yml:**
- URLs korrigiert: `pms-api.kolibri-visions.de` → `api.fewo.kolibri-visions.de` (alte URL existierte nicht!)
- `pms-admin.kolibri-visions.de` → `admin.fewo.kolibri-visions.de`
- URLs jetzt via GitHub Repository Variables überschreibbar (`vars.BACKEND_URL`, `vars.ADMIN_URL`)

**ci-e2e.yml:**
- Automatischer Trigger nach Frontend-CI (vorher nur manuell)
- Hardcodierte URL → `vars.ADMIN_URL` mit Fallback
- `PLAYWRIGHT_BASE_URL` Env-Var statt `BASE_URL`

### GitHub Repository Variables (optional)
In GitHub → Settings → Variables → Actions eintragen:
- `BACKEND_URL` = `https://api.fewo.kolibri-visions.de`
- `ADMIN_URL` = `https://admin.fewo.kolibri-visions.de`

### Revert
```bash
git reset --hard pre-p3-cicd-fix
```

### Status
✅ IMPLEMENTED

---

*Last updated: 2026-03-11 (P3: CI/CD Workflow-Fixes)*
