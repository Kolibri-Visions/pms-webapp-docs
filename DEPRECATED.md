# DEPRECATED.md — Deprecation Timeline

> **Erstellt:** 2026-03-12
> **Letzte Aktualisierung:** 2026-03-12
> **Zweck:** Zentrale Übersicht aller deprecated Felder, Types und Funktionen mit Ablaufzeitplan.

---

## 1) Tax-Related Deprecations (Priorität: HOCH)

### 1.1 `properties.tax_rate` / `properties.tax_included`

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | DB-Spalte, Backend-Schema, Frontend-Type |
| **Ersatz** | `accommodation_tax_id` (FK auf `pricing_taxes`) / `pricing_taxes.is_inclusive` |
| **Status** | Deprecated, Legacy-Reads noch aktiv |
| **Entfernung geplant** | Nach Migration aller Properties auf `accommodation_tax_id` |

**Dateien:**
- DB: `supabase/migrations/00000000000000_baseline.sql` (Zeile 1487, 1490)
- Backend: `backend/app/schemas/properties.py` (Zeilen 228-236, 417-418, 606-608)
- Frontend: `frontend/app/types/property.ts` (Zeilen 122, 124, 220, 222, 273, 275)
- Frontend: `frontend/app/components/forms/PropertyForm.tsx` (Zeilen 66, 68)

### 1.2 `pricing_fees.taxable`

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | DB-Spalte, Backend-Schema, Frontend-Type |
| **Ersatz** | `tax_id` (UUID-Referenz auf `pricing_taxes`) |
| **Status** | Deprecated, Backward-Compatibility aktiv |
| **Entfernung geplant** | Wenn alle Fees `tax_id` statt `taxable` boolean nutzen |

**Dateien:**
- DB: `supabase/migrations/00000000000000_baseline.sql` (Zeile 1840)
- Backend: `backend/app/schemas/pricing.py` (Zeilen 289, 299, 313, 336)
- Backend: `backend/app/services/pricing_totals.py` (Zeile 65)
- Frontend: `frontend/app/types/pricing.ts` (Zeilen 290, 292, 313, 315, 355)

---

## 2) Date-Field Deprecations (Priorität: MITTEL)

### 2.1 `date_from` / `date_to` → `check_in` / `check_out`

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | Frontend-Types (Legacy-Interfaces) |
| **Ersatz** | `check_in` / `check_out` |
| **Status** | Deprecated, Legacy-Interfaces vorhanden |
| **Entfernung geplant** | Bei nächstem Breaking Change (API v2) |

**Dateien:**
- Frontend: `frontend/app/types/booking.ts` — `BookingRequestLegacy` (Zeilen 277-284), `BookingChangeMessageLegacy` (Zeilen 299-308)
- Frontend: `frontend/app/types/owner.ts` (Zeilen 78, 80)
- Frontend: `frontend/app/types/availability.ts` (Zeilen 76, 78, 110, 112)

### 2.2 `date_from` / `date_to` → `start_date` / `end_date` (Availability)

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | Frontend Availability-Types |
| **Ersatz** | `start_date` / `end_date` |
| **Status** | Deprecated |

**Dateien:**
- Frontend: `frontend/app/types/availability.ts` (Zeilen 76, 78, 204, 206)

---

## 3) Field-Renaming Deprecations (Priorität: NIEDRIG)

### 3.1 `tenant_id` → `agency_id`

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | Frontend Media-Types |
| **Ersatz** | `agency_id` |
| **Status** | Deprecated, Normalizer-Funktionen vorhanden |

**Dateien:**
- Frontend: `frontend/app/types/media.ts` — `MediaFile.tenant_id` (Zeile 42), `MediaFolder.tenant_id` (Zeile 74)

### 3.2 `address` → `address_line1`

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | Frontend Property-Types, Guest-Types |
| **Ersatz** | `address_line1` |
| **Status** | Deprecated |

**Dateien:**
- Frontend: `frontend/app/types/property.ts` (Zeile 75)
- Frontend: `frontend/app/types/guest.ts` (Zeile 68)

### 3.3 `notes` → `guest_message`

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | Frontend Booking-Types |
| **Ersatz** | `guest_message` |
| **Status** | Deprecated |

**Dateien:**
- Frontend: `frontend/app/types/booking.ts` (Zeile 89)

### 3.4 `role` → `role_id` / `role_code` / `role_name`

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | Frontend User-Types |
| **Ersatz** | `role_id`, `role_code`, `role_name` |
| **Status** | Deprecated |

**Dateien:**
- Frontend: `frontend/app/types/user.ts` (Zeilen 37, 56)

### 3.5 `inquiry_deadline` → `decision_deadline_at`

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | Frontend Booking-Types |
| **Ersatz** | `decision_deadline_at` |
| **Status** | Deprecated (Backend liefert Feld nicht) |

**Dateien:**
- Frontend: `frontend/app/types/booking.ts` (Zeile 194)

### 3.6 Audit-Log Felder

| Alt | Neu |
|-----|-----|
| `user_id` | `actor_user_id` |
| `message` | (entfernt) |
| `resource_type` | `entity_type` |
| `resource_id` | `entity_id` |
| `address` | `ip` |
| `recipient` | `recipient_email` |
| `message` (notification) | `error_message` |

**Dateien:**
- Frontend: `frontend/app/types/operations.ts` (Zeilen 143-153, 213, 225)

### 3.7 `reason` → `cancellation_reason` (Booking-Stornierung)

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | Backend API (Pydantic AliasChoices) |
| **Ersatz** | `cancellation_reason` |
| **Status** | Backward-Compatible via AliasChoices |

**Dateien:**
- Backend: `backend/tests/integration/test_bookings.py` (Zeilen 1868-1910)

---

## 4) Pricing-Deprecations (Priorität: MITTEL)

### 4.1 Legacy Booking-Pricing-Felder

| Alt | Neu |
|-----|-----|
| `cleaning_fee` | `channel_data.pricing_breakdown.fees` |
| `service_fee` | `channel_data.pricing_breakdown.fees` |
| `tax` | `channel_data.pricing_breakdown.taxes` |
| `discount_amount` | `tax_amount` |
| `total_price` (Owner) | `total_price_cents` |
| `nightly` | `base_nightly_cents` / `nightly_cents` |

**Dateien:**
- Frontend: `frontend/app/types/booking.ts` (Zeilen 33, 35, 37, 39, 43)
- Frontend: `frontend/app/types/owner.ts` (Zeile 83)
- Frontend: `frontend/app/types/pricing.ts` (Zeilen 91, 164, 181, 207, 225)

### 4.2 `PricingLegacy` Interface

| Eigenschaft | Wert |
|-------------|------|
| **Betroffen** | Frontend Pricing-Types |
| **Ersatz** | `PricingBreakdown` |
| **Status** | Deprecated |

**Dateien:**
- Frontend: `frontend/app/types/pricing.ts` (Zeile 91)

---

## 5) Bereits entfernt (2026-03-12)

| Item | Datei | Entfernt in |
|------|-------|-------------|
| `PaginatedResponse<T>` (Legacy page/per_page) | `frontend/app/types/api.ts` | Sprint 3+4 Cleanup |
| `ListParams` | `frontend/app/types/api.ts` | Sprint 3+4 Cleanup |
| `pageToOffset()` | `frontend/app/types/api.ts` | Sprint 3+4 Cleanup |
| `LegacyFileType` | `frontend/app/types/media.ts` | Sprint 3+4 Cleanup |
| `BillingUnit` (Alias) | `frontend/app/types/extra-service.ts` | Sprint 3+4 Cleanup |
| `legacySyncCheck()` | — | Vor Sprint 3 bereits entfernt |
| `api_v1.py` (Legacy-Router) | `backend/app/api/` | Commit 35385277 |
| Entitlements-System | `backend/app/` | Commit 35385277 |

---

## 6) Sonderfälle

### 6.1 `amenity.is_highlighted`

| Eigenschaft | Wert |
|-------------|------|
| **Status** | Deprecated — Backend unterstützt Feld NICHT |
| **Aktion** | Aus Frontend-Type entfernen wenn keine UI-Referenz mehr |

**Dateien:**
- Frontend: `frontend/app/types/amenity.ts` (Zeilen 19, 44)

### 6.2 `visitor_tax.child_rate_cents`

| Eigenschaft | Wert |
|-------------|------|
| **Status** | Deprecated — Backend unterstützt Feld NICHT |
| **Aktion** | Aus Frontend-Type und UI entfernen |

**Dateien:**
- Frontend: `frontend/app/types/visitor-tax.ts` (Zeilen 49, 51, 73, 75)

### 6.3 `AvailabilityLegacy` Interface

| Eigenschaft | Wert |
|-------------|------|
| **Ersatz** | `AvailabilityState` |
| **Grund** | Legacy hat Extra-Werte die Backend nicht liefert |

**Dateien:**
- Frontend: `frontend/app/types/availability.ts` (Zeile 47)

### 6.4 `getOrderedNavItems()` Funktion

| Eigenschaft | Wert |
|-------------|------|
| **Ersatz** | `computeNavItems()` |
| **Status** | Deprecated |

**Dateien:**
- Frontend: `frontend/app/components/admin-shell/nav-config.ts` (Zeilen 261-264)

### 6.5 `legacyNoCache` Parameter

| Eigenschaft | Wert |
|-------------|------|
| **Ersatz** | `options.noCache` |
| **Status** | Deprecated |

**Dateien:**
- Frontend: `frontend/app/lib/api-client.ts` (Zeile 233)

### 6.6 `PaginatedResponse<T>` in api-utils.ts

| Eigenschaft | Wert |
|-------------|------|
| **Ersatz** | `StandardPaginatedResponse` aus `@/app/types/api` |
| **Status** | Deprecated, aber noch von `normalizeResponse()` und `isPaginatedResponse()` verwendet |
| **Aktion** | Kann entfernt werden wenn Rückgabetyp auf `StandardPaginatedResponse` umgestellt |

**Dateien:**
- Frontend: `frontend/app/lib/api-utils.ts` (Zeile 33)

---

## 7) Entfernungs-Prioritäten

### Sofort entfernbar (keine Abhängigkeiten)
- `amenity.is_highlighted` (Backend liefert es nicht)
- `visitor_tax.child_rate_cents` (Backend liefert es nicht)
- `AvailabilityLegacy` (prüfen ob noch referenziert)
- `getOrderedNavItems()` (prüfen ob noch referenziert)

### Nach Migration entfernbar
- `properties.tax_rate` / `tax_included` (nach DB-Migration aller Properties)
- `pricing_fees.taxable` (nach Migration aller Fees auf `tax_id`)
- Legacy Booking-Pricing-Felder (nach Frontend-Umstellung auf `pricing_breakdown`)

### Bei API v2 entfernbar
- `date_from` / `date_to` Legacy-Interfaces
- `reason` → `cancellation_reason` AliasChoices
- `tenant_id` → `agency_id` Normalizer
