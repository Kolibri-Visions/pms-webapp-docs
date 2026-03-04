# PMS-Webapp Field-Mapping (Legacy → Standard)

**Erstellt:** 2026-03-04
**Zweck:** Übersicht aller inkonsistenten Felder und deren Migration

---

## 1. Datumsfelder

### Check-in Datum

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Admin API (bookings.py) | `check_in` | `check_in` | OK |
| Public API (public_booking.py) | `date_from` | `check_in` | Migration Phase 3 |
| Frontend Types (booking.ts) | `check_in` | `check_in` | OK |
| Frontend Public (BuchungClient.tsx) | `date_from` | `check_in` | Migration Phase 3 |
| DB Schema | `check_in` | `check_in` | OK |

**Betroffene Dateien:**
- `backend/app/api/routes/public_booking.py:76-77`
- `backend/app/schemas/public_booking.py` (falls existiert)
- `frontend/app/(public)/buchung/BuchungClient.tsx:61-62, 141, 180-182`

### Check-out Datum

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Admin API | `check_out` | `check_out` | OK |
| Public API | `date_to` | `check_out` | Migration Phase 3 |
| Frontend Types | `check_out` | `check_out` | OK |
| Frontend Public | `date_to` | `check_out` | Migration Phase 3 |
| DB Schema | `check_out` | `check_out` | OK |

**Betroffene Dateien:**
- `backend/app/api/routes/public_booking.py:76-77`
- `frontend/app/(public)/buchung/BuchungClient.tsx:61-62, 141, 180-182`

---

## 2. Gästezahlen

### Erwachsene

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Admin API | `num_adults` | `num_adults` | OK |
| Public API | `adults` | `num_adults` | Migration Phase 3 |
| Booking Requests API | `num_adults` | `num_adults` | OK |
| Frontend Admin Types | `num_adults` | `num_adults` | OK |
| Frontend Public | `adults` | `num_adults` | Migration Phase 3 |
| DB Schema | `num_adults` | `num_adults` | OK |

**Betroffene Dateien:**
- `backend/app/api/routes/public_booking.py:78-79`
- `frontend/app/(public)/buchung/BuchungClient.tsx`

### Kinder

| Kontext | Aktuell | Standard | Status |
|---------|---------|----------|--------|
| Admin API | `num_children` | `num_children` | OK |
| Public API | `children` | `num_children` | Migration Phase 3 |
| Booking Requests API | `num_children` | `num_children` | OK |
| Frontend Admin Types | `num_children` | `num_children` | OK |
| Frontend Public | `children` | `num_children` | Migration Phase 3 |
| DB Schema | `num_children` | `num_children` | OK |

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

### Phase 3: Public API v2 (Minor Breaking)

| Änderung | v1 → v2 |
|----------|---------|
| Endpoint | `/api/v1/public/booking-requests` → `/api/v2/public/booking-requests` |
| `date_from` | → `check_in` |
| `date_to` | → `check_out` |
| `adults` | → `num_adults` |
| `children` | → `num_children` |

**Frontend-Änderungen:**
- `frontend/app/(public)/buchung/BuchungClient.tsx`
- `frontend/app/(public)/buchung/api.ts` (falls vorhanden)

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

**Letzte Aktualisierung:** 2026-03-04
