# PMS-Webapp Project Status

**Last Updated:** 2026-02-23

**Current Phase:** Phase 22 - Owner DAC7 Compliance & Edit Modal

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

*Last updated: 2026-02-21*
