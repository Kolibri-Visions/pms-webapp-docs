# PMS-Webapp Field-Mapping (Legacy → Standard)

**Erstellt:** 2026-03-04
**Zweck:** Übersicht aller inkonsistenten Felder und deren Migration

---

## 1. Datumsfelder

### Semantische Unterscheidung

> **WICHTIG:** Nicht alle Datumsfelder sind gleich! Die Feldnamen sind **kontextabhängig**:

| Kontext | Korrekte Felder | Erklärung |
|---------|-----------------|-----------|
| **Buchungen** | `check_in`, `check_out` | Gäste checken ein/aus |
| **Zeiträume** | `date_from`, `date_to` | Seasons, Kurtaxe-Perioden |
| **Verfügbarkeit** | `start_date`, `end_date` | Availability Segments |

**Beispiele:**
- `booking.check_in` ✅ (Gast kommt an)
- `season_period.date_from` ✅ (Saison beginnt)
- `availability_segment.start_date` ✅ (Verfügbarkeit beginnt)

Diese sind **keine Inkonsistenzen**, sondern **semantisch korrekte** Feldnamen für den jeweiligen Kontext.

### Check-in Datum (Buchungen)

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Admin API (bookings.py) | `check_in` | `check_in` | ✅ OK |
| Public API v1 (public_booking.py) | `date_from` | `check_in` | ⚠️ Deprecated |
| Public API v2 (public_booking_v2.py) | `check_in` | `check_in` | ✅ OK |
| Frontend Types (booking.ts) | `check_in` | `check_in` | ✅ OK |
| Frontend Public (BuchungClient.tsx) | `check_in` | `check_in` | ✅ Migriert zu v2 |
| DB Schema | `check_in` | `check_in` | ✅ OK |

**Betroffene Dateien:**
- `backend/app/api/routes/public_booking.py:76-77`
- `backend/app/schemas/public_booking.py` (falls existiert)
- `frontend/app/(public)/buchung/BuchungClient.tsx:61-62, 141, 180-182`

### Check-out Datum

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Admin API | `check_out` | `check_out` | ✅ OK |
| Public API v1 | `date_to` | `check_out` | ⚠️ Deprecated |
| Public API v2 | `check_out` | `check_out` | ✅ OK |
| Frontend Types | `check_out` | `check_out` | ✅ OK |
| Frontend Public | `check_out` | `check_out` | ✅ Migriert zu v2 |
| DB Schema | `check_out` | `check_out` | ✅ OK |

**Betroffene Dateien:**
- `backend/app/api/routes/public_booking.py:76-77`
- `frontend/app/(public)/buchung/BuchungClient.tsx:61-62, 141, 180-182`

---

## 2. Gästezahlen

### Erwachsene

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Admin API | `num_adults` | `num_adults` | ✅ OK |
| Public API v1 | `adults` | `num_adults` | ⚠️ Deprecated |
| Public API v2 | `num_adults` | `num_adults` | ✅ OK |
| Booking Requests API | `num_adults` | `num_adults` | ✅ OK |
| Frontend Admin Types | `num_adults` | `num_adults` | ✅ OK |
| Frontend Public | `num_adults` | `num_adults` | ✅ Migriert zu v2 |
| DB Schema | `num_adults` | `num_adults` | ✅ OK |

**Betroffene Dateien:**
- `backend/app/api/routes/public_booking.py:78-79`
- `frontend/app/(public)/buchung/BuchungClient.tsx`

### Kinder

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Admin API | `num_children` | `num_children` | ✅ OK |
| Public API v1 | `children` | `num_children` | ⚠️ Deprecated |
| Public API v2 | `num_children` | `num_children` | ✅ OK |
| Booking Requests API | `num_children` | `num_children` | ✅ OK |
| Frontend Admin Types | `num_children` | `num_children` | ✅ OK |
| Frontend Public | `num_children` | `num_children` | ✅ Migriert zu v2 |
| DB Schema | `num_children` | `num_children` | ✅ OK |

**Betroffene Dateien:**
- `backend/app/api/routes/public_booking.py:78-79`
- `frontend/app/(public)/buchung/BuchungClient.tsx`

### Aggregierte Gästezahl

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Frontend Types | `guests`, `guests_count`, `num_guests` | `num_guests` | Migration Phase 1 |
| Backend Response | `num_guests` (computed) | `num_guests` | OK |

**Betroffene Dateien:**
- `frontend/app/types/booking.ts:22-23` (redundante Felder)

---

## 3. Preisfelder

### Gesamtpreis

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Frontend Type | `string \| number` | `string` | Migration Phase 1 |
| Backend Response | `Decimal` (serialisiert als String) | `string` | OK |
| Neues Format | - | `total_price_cents: number` | Phase 2 |

**Betroffene Dateien:**
- `frontend/app/types/booking.ts:30`

### Pricing Breakdown

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Legacy DB-Felder | `cleaning_fee`, `service_fee`, `tax_amount` | Legacy (beibehalten) | - |
| Neue Struktur | `channel_data.pricing_breakdown` | Standard | Phase 2 |

**Struktur `pricing_breakdown`:**
```typescript
{
  fees: Array<{ name: string; type: string; amount_cents: number; taxable?: boolean }>;
  taxes: Array<{ name: string; percent: number; amount_cents: number }>;
  visitor_tax: { location_name: string; amount_cents: number; ... } | null;
  fees_total_cents: number;
  taxes_total_cents: number;
  visitor_tax_cents: number;
}
```

---

## 4. Status-Mapping

### Booking Status

| DB-Wert | Admin API | Booking Requests API | Standard |
|---------|-----------|---------------------|----------|
| `inquiry` | `inquiry` | `under_review` | `inquiry` |
| `requested` | `requested` | `requested` | `requested` |
| `pending` | `pending` | - | `pending` |
| `confirmed` | `confirmed` | `confirmed` | `confirmed` |
| `checked_in` | `checked_in` | - | `checked_in` |
| `checked_out` | `checked_out` | - | `checked_out` |
| `cancelled` | `cancelled` | `cancelled` | `cancelled` |
| `declined` | `declined` | `declined` | `declined` |
| `no_show` | `no_show` | - | `no_show` |

**Betroffene Dateien:**
- `backend/app/api/routes/booking_requests.py` (Status-Mapping)

---

## 5. Migration-Plan

### Phase 1: Frontend Type-Bereinigung (Non-Breaking)

| Änderung | Datei | Zeile |
|----------|-------|-------|
| `guests_count` entfernen | `frontend/app/types/booking.ts` | 23 |
| `total_price: string \| number` → `string` | `frontend/app/types/booking.ts` | 30 |
| Zentrale Type-Exports | `frontend/app/types/index.ts` | Neu |

### Phase 2: Pricing-Struktur (Non-Breaking)

| Änderung | Datei |
|----------|-------|
| `PricingBreakdown` Type definieren | `frontend/app/types/pricing.ts` |
| Display-Komponente erstellen | `frontend/app/components/booking/PricingBreakdown.tsx` |
| Backend: `pricing_breakdown` immer setzen | `backend/app/services/booking/create.py` |

### Phase 3: Public API v2 (Minor Breaking) ✅ ABGESCHLOSSEN

| Änderung | v1 → v2 |
|----------|---------|
| Availability | `/api/v1/public/availability` → `/api/v2/public/availability` |
| Booking Requests | `/api/v1/public/booking-requests` → `/api/v2/public/booking-requests` |
| `date_from` | → `check_in` |
| `date_to` | → `check_out` |
| `adults` | → `num_adults` |
| `children` | → `num_children` |

**Durchgeführte Änderungen (2026-03-04):**
- `backend/app/api/routes/public_booking_v2.py` (NEU)
- `backend/app/api/routes/public_booking.py` (Deprecation-Warnung hinzugefügt)
- `backend/app/modules/public_booking.py` (v2 Router registriert)
- `backend/app/main.py` (v2 Fallback-Router)
- `frontend/app/(public)/buchung/BuchungClient.tsx` (auf v2 API umgestellt)
- `frontend/app/types/booking.ts` (`PublicBookingRequestV2`, `AvailabilityResponseV2` hinzugefügt)

---

## 6. Validierungs-Queries

### Redundante Gästefelder finden

```bash
rg "guests_count|guests\s*:" frontend/app/types/
rg "guests\s*=" frontend/app/
```

### Union-Types für Preise finden

```bash
rg "string\s*\|\s*number" frontend/app/types/
```

### Legacy-Feldnamen in Public API

```bash
rg "date_from|date_to|\"adults\"|\"children\"" backend/app/api/routes/public
rg "date_from|date_to|adults|children" frontend/app/\(public\)/
```

---

## 7. Revert-Anleitung

Bei Problemen nach Migration:

```bash
# Zum Baseline-Tag zurückkehren
git reset --hard pre-consolidation-baseline

# Oder einzelne Phase revertieren
git reset --hard pre-consolidation-phase-X
```

---

---

## 8. Migration: Pricing Breakdown Backfill

Für bestehende Buchungen mit Legacy-Feldern (cleaning_fee, service_fee, tax) existiert ein
Backfill-Script unter:

```
supabase/scripts/backfill_pricing_breakdown.sql
```

**Status:** NICHT AUSGEFÜHRT (optional, Frontend unterstützt beide Formate)

Das Script:
- Analysiert betroffene Buchungen
- Erstellt pricing_breakdown aus Legacy-Feldern
- Ist auskommentiert zur Sicherheit (manuell ausführen nach Backup)

**Hinweis:** Die PricingBreakdown-Komponente unterstützt automatisch beide Formate:
- Neues Format: `channel_data.pricing_breakdown`
- Legacy-Fallback: `cleaning_fee`, `service_fee`, `tax`

---

**Letzte Aktualisierung:** 2026-03-04 (Architektur-Konsolidierung abgeschlossen)
