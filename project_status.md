# PMS-Webapp Project Status

**Last Updated:** 2026-02-21

**Current Phase:** Phase 21 - Fees/Taxes Template-Based Restructuring

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

## Archived Entries

Historische Einträge vor 2026-02-14 wurden archiviert. Diese Datei enthält nur aktuelle Features der letzten 2 Wochen.

Für ältere Phase-Dokumentation siehe Git-History oder die jeweiligen Runbook-Kapitel unter `ops/runbook/`.

---

*Last updated: 2026-02-21*
