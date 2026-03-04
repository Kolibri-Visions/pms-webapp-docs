# PMS-Webapp Entwicklungskonventionen

**Erstellt:** 2026-03-04
**Status:** Verbindlich
**Scope:** Alle neuen Entwicklungen, Refaktorisierungen

> Diese Konventionen sind **verbindlich** für alle Code-Änderungen.
> Bei Abweichungen: Dokumentieren und im PR begründen.

---

## 1. Feldnamen-Konventionen

### 1.1 Datum/Zeit

**Semantische Feldnamen (kontextabhängig):**

| Kontext | Feldnamen | Verwendung |
|---------|-----------|------------|
| **Buchungen** | `check_in`, `check_out` | Gäste checken ein/aus |
| **Zeiträume** | `date_from`, `date_to` | Seasons, Tax Periods, etc. |
| **Verfügbarkeit** | `start_date`, `end_date` | Availability Segments |

> **Wichtig:** `date_from`/`date_to` ist **KORREKT** für Zeiträume wie Seasons und Kurtaxe-Perioden.
> Diese sind **keine** Legacy-Felder, sondern semantisch passend für den Kontext.

**Timestamp-Felder:**

| Korrekt | FALSCH | Bemerkung |
|---------|--------|-----------|
| `created_at` | ~~createdAt~~, ~~create_date~~ | Erstellungszeitpunkt |
| `updated_at` | ~~updatedAt~~, ~~modify_date~~ | Aktualisierungszeitpunkt |
| `confirmed_at` | ~~confirmedAt~~ | Bestätigungszeitpunkt |
| `cancelled_at` | ~~cancelledAt~~ | Stornierungszeitpunkt |

**Format:**
- Datum: ISO 8601 String `"YYYY-MM-DD"`
- Zeitstempel: ISO 8601 mit Timezone `"YYYY-MM-DDTHH:mm:ssZ"`

### 1.2 Gästezahlen

| Korrekt | FALSCH | Bemerkung |
|---------|--------|-----------|
| `num_adults` | ~~adults~~, ~~adult_count~~, ~~guests~~ | Anzahl Erwachsene |
| `num_children` | ~~children~~, ~~child_count~~ | Anzahl Kinder |
| `num_infants` | ~~infants~~, ~~baby_count~~ | Anzahl Kleinkinder |
| `num_pets` | ~~pets~~, ~~pet_count~~ | Anzahl Haustiere |
| `num_guests` | ~~guests~~, ~~guests_count~~, ~~total_guests~~ | Aggregiert (adults + children) |

**Regel:** Immer `num_` Präfix für alle Zählfelder.

### 1.3 Preise

| Korrekt | FALSCH | Verwendung |
|---------|--------|------------|
| `total_price_cents` | ~~totalPrice~~, ~~total~~ | Gesamtpreis in Cents |
| `subtotal_cents` | ~~subtotal~~ (ohne Suffix) | Zwischensumme in Cents |
| `nightly_rate_cents` | ~~nightlyRate~~, ~~rate~~ | Nachtpreis in Cents |
| `cleaning_fee_cents` | ~~cleaningFee~~ | Reinigungsgebühr in Cents |
| `tax_amount_cents` | ~~tax~~, ~~taxes~~ | Steuerbetrag in Cents |

**Regeln:**
- **Neue Felder:** Immer in Cents als Integer mit `_cents` Suffix
- **Legacy-Felder:** `total_price`, `cleaning_fee` etc. (Decimal) nur für DB-Kompatibilität
- **Display:** Frontend formatiert Cents zu Euro (`cents / 100`)

### 1.4 IDs

| Korrekt | FALSCH | Bemerkung |
|---------|--------|-----------|
| `property_id` | ~~propertyId~~, ~~property~~ | Objekt-ID |
| `guest_id` | ~~guestId~~, ~~guest~~ | Gast-ID |
| `booking_id` | ~~bookingId~~ | Buchungs-ID |
| `agency_id` | ~~agencyId~~, ~~tenant_id~~ | Agentur/Tenant-ID |

**Format:** UUID v4 als String `"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`

### 1.5 Status

| Korrekt | FALSCH | Bemerkung |
|---------|--------|-----------|
| `confirmed` | ~~CONFIRMED~~, ~~Confirmed~~ | Bestätigt |
| `checked_in` | ~~checkedIn~~, ~~CHECKED_IN~~ | Eingecheckt |
| `checked_out` | ~~checkedOut~~ | Ausgecheckt |
| `cancelled` | ~~CANCELLED~~, ~~canceled~~ | Storniert |
| `no_show` | ~~noShow~~, ~~NO_SHOW~~ | Nicht erschienen |

**Regel:** Immer snake_case, lowercase.

### 1.6 Boolean

| Korrekt | FALSCH | Bemerkung |
|---------|--------|-----------|
| `is_active` | ~~active~~, ~~isActive~~ | Aktivstatus |
| `is_taxable` | ~~taxable~~ | Steuerpflichtig |
| `has_breakfast` | ~~breakfast~~, ~~hasBreakfast~~ | Hat Frühstück |
| `is_blocked` | ~~blocked~~ | Blockiert |

**Regel:** `is_` Präfix für Zustand, `has_` Präfix für Besitz.

---

## 2. Type-Konventionen

### 2.1 Frontend (TypeScript)

```typescript
// KORREKT: Strikte, eindeutige Typen
interface Booking {
  id: string;                    // UUID als String
  check_in: string;              // ISO Date "YYYY-MM-DD"
  check_out: string;             // ISO Date "YYYY-MM-DD"
  num_adults: number;            // Integer
  num_children: number;          // Integer
  total_price: string;           // Decimal vom Backend als String
  total_price_cents?: number;    // Neues Format (Integer)
  status: BookingStatus;         // Enum/Union Type
  created_at: string;            // ISO Timestamp
}

// FALSCH: Union Types für einzelne API-Felder
interface Booking {
  total_price: string | number;  // NIEMALS!
  num_adults: number | null;     // Wenn required, dann kein null
}
```

### 2.2 Backend (Pydantic)

```python
# KORREKT: Explizite Typen mit Validierung
class BookingCreate(BaseModel):
    property_id: UUID
    check_in: date
    check_out: date
    num_adults: int = Field(ge=1, le=20)
    num_children: int = Field(default=0, ge=0, le=20)
    total_price_cents: Optional[int] = Field(default=None, ge=0)

# FALSCH: Unklare optionale Felder
class BookingCreate(BaseModel):
    guests: Optional[int]  # Was passiert bei None? Welche Gäste?
```

### 2.3 Type-Mapping Backend → Frontend

| Python (Pydantic) | TypeScript | Serialisierung |
|-------------------|------------|----------------|
| `str` | `string` | Direkt |
| `int` | `number` | Direkt |
| `float` | `number` | Direkt |
| `bool` | `boolean` | Direkt |
| `UUID` | `string` | Als String |
| `datetime` | `string` | ISO 8601 |
| `date` | `string` | "YYYY-MM-DD" |
| `Decimal` | `string` | Als String (Präzision!) |
| `Optional[T]` | `T \| null` | null wenn nicht gesetzt |
| `List[T]` | `T[]` | Array |
| `Dict[str, Any]` | `Record<string, unknown>` | Object |

---

## 3. API-Konventionen

### 3.1 URL-Struktur

```
# KORREKT (RESTful)
GET    /api/v1/bookings              # Liste
GET    /api/v1/bookings/{id}         # Detail
POST   /api/v1/bookings              # Erstellen
PATCH  /api/v1/bookings/{id}         # Aktualisieren
DELETE /api/v1/bookings/{id}         # Löschen

# Aktionen als Sub-Resource
POST   /api/v1/bookings/{id}/cancel
POST   /api/v1/bookings/{id}/confirm
POST   /api/v1/booking-requests/{id}/approve
POST   /api/v1/booking-requests/{id}/decline

# FALSCH (RPC-Style)
GET    /api/v1/getBookings
POST   /api/v1/createBooking
POST   /api/v1/cancelBooking/{id}
```

### 3.2 Query-Parameter

```
# KORREKT (snake_case)
?sort_by=created_at&sort_order=desc&page_size=20&property_id=xxx

# FALSCH (camelCase)
?sortBy=createdAt&sortOrder=desc&pageSize=20&propertyId=xxx
```

### 3.3 Pagination Response

```json
{
  "items": [...],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

### 3.4 Error Response

```json
{
  "detail": "Booking nicht gefunden",
  "error_code": "BOOKING_NOT_FOUND",
  "status_code": 404
}
```

---

## 4. Versionierung

### 4.1 API-Versionen

- **v1:** Aktuelle stabile Version
- **v2:** Breaking Changes (z.B. Public API Feldnamen-Vereinheitlichung)

### 4.2 Breaking vs. Non-Breaking

**Non-Breaking (direkt deployen):**
- Neue optionale Felder
- Neue optionale Query-Parameter
- Neue Endpoints
- Erweiterte Enum-Werte

**Breaking (neue Version):**
- Feld umbenennen
- Feld entfernen
- Typ ändern
- Feld required machen
- Response-Struktur ändern

---

## 5. Verbotene Patterns

### 5.1 Keine defensiven Parsing-Funktionen

```typescript
// FALSCH: Zeigt inkonsistente Datenquellen
const safeNumber = (value: string | number | null | undefined): number => {
  if (value === null || value === undefined) return 0;
  if (typeof value === "number") return value;
  return parseFloat(value) || 0;
};

// RICHTIG: Typ ist bereits korrekt definiert
const price: number = booking.total_price_cents;
```

### 5.2 Keine redundanten Felder

```typescript
// FALSCH: Mehrere Felder für dasselbe
interface Booking {
  guests: number;
  guests_count: number;
  num_guests: number;
}

// RICHTIG: Ein eindeutiges Feld
interface Booking {
  num_guests: number;
}
```

### 5.3 Keine impliziten Konvertierungen

```typescript
// FALSCH
const total = Number(booking.total_price) || 0;

// RICHTIG
const total = booking.total_price_cents;  // Bereits number
```

---

## 6. Dokumentation

### 6.1 Neue Felder dokumentieren

```python
class BookingResponse(BaseModel):
    pricing_breakdown: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detaillierte Preisaufschlüsselung. Neu ab v1.5.0"
    )
```

### 6.2 Deprecation markieren

```typescript
interface Booking {
  /**
   * @deprecated Verwende `total_price_cents` stattdessen.
   * Wird in v2.0.0 entfernt.
   */
  total_price?: string;

  total_price_cents: number;
}
```

---

## 7. Checkliste für Code-Reviews

### Neue Felder

- [ ] Name folgt Konventionen (§1)?
- [ ] Typ ist eindeutig (keine Union für API-Felder)?
- [ ] Frontend und Backend synchron?
- [ ] In diesem Dokument referenziert?

### API-Änderungen

- [ ] Rückwärtskompatibel?
- [ ] Query-Parameter in snake_case?
- [ ] Response-Format konsistent?

### Types

- [ ] Keine `any` oder `unknown` ohne Begründung?
- [ ] Keine defensive Parsing-Logik?
- [ ] Optional/Nullable korrekt markiert?

---

## 8. Legacy-Abweichungen (GELÖST)

Die folgenden Legacy-Abweichungen wurden in der Architektur-Konsolidierung behoben:

| Legacy | Korrekt | Betroffene APIs | Status |
|--------|---------|-----------------|--------|
| `date_from` | `check_in` | Public API | ✅ v2 API erstellt |
| `date_to` | `check_out` | Public API | ✅ v2 API erstellt |
| `adults` | `num_adults` | Public API | ✅ v2 API erstellt |
| `children` | `num_children` | Public API | ✅ v2 API erstellt |
| `guests_count` | `num_guests` | Frontend Types | ✅ Entfernt |
| `total_price: string \| number` | `total_price: string` | Frontend Types | ✅ Korrigiert |
| `safeNumber()` Workaround | `parsePrice()` | Frontend | ✅ Ersetzt |

---

## 9. API-Versionen

### 9.1 Aktuelle Versionen

| Version | Pfad | Status | Feldnamen |
|---------|------|--------|-----------|
| **v1** | `/api/v1/public/*` | ⚠️ DEPRECATED | Legacy: `date_from`, `adults` |
| **v2** | `/api/v2/public/*` | ✅ AKTUELL | Standard: `check_in`, `num_adults` |

### 9.2 v1 → v2 Migration (Public API)

```typescript
// v1 (deprecated) → v2 (aktuell)
{
  "date_from": "2026-01-01",    → "check_in": "2026-01-01",
  "date_to": "2026-01-07",      → "check_out": "2026-01-07",
  "adults": 2,                  → "num_adults": 2,
  "children": 1                 → "num_children": 1
}
```

### 9.3 Deprecation-Timeline

- **2026-03-04:** v2 API erstellt, v1 als deprecated markiert
- **2026-06-01:** (geplant) v1 Deprecation-Warning in Response-Header
- **2026-09-01:** (geplant) v1 API entfernen

---

## 10. Type-Generierung

### 10.1 Single Source of Truth

Das OpenAPI-Schema des Backends ist die einzige verbindliche Quelle für API-Types:

```bash
# Schema exportieren (von PROD)
cd backend && python3 scripts/export_openapi.py --prod

# Frontend-Types generieren
cd frontend && npm run generate:types
```

### 10.2 Generierte Types verwenden

```typescript
// Option 1: API-Aliase (empfohlen)
import type { APIBooking, APIGuest } from '@/app/types';

// Option 2: Direkt aus generierten Types
import type { components } from '@/app/types';
type Booking = components['schemas']['BookingResponse'];
```

### 10.3 Wann Types neu generieren?

- Nach Backend-Schema-Änderungen
- Nach API-Änderungen (neue Felder, geänderte Typen)
- Vor größeren Frontend-Releases

---

---

## 11. API-Prefix Konventionen

### 11.1 Admin-Frontend API-Aufrufe

Das Admin-Frontend nutzt zwei Arten von API-Routen:

| Pfad | Verwendung | Authentifizierung |
|------|------------|-------------------|
| `/api/v1/*` | Direkte Backend-Calls | JWT via `apiClient` + `accessToken` |
| `/api/internal/*` | Next.js Proxy-Routes | Session-Cookie → JWT Konvertierung |

**Standard-Pattern (empfohlen):**

```typescript
import { useAuth } from "@/app/lib/auth-context";
import { apiClient, ApiError } from "@/app/lib/api-client";

const { accessToken } = useAuth();
const data = await apiClient.get<ResponseType>("/api/v1/endpoint", accessToken);
```

### 11.2 Wann `/api/internal/` verwenden?

Nur für spezielle Fälle:
- **Auth/Session:** Routes die mit Supabase Auth arbeiten
- **File Upload:** Avatar-Uploads zu Supabase Storage
- **SSR:** Server-Side Rendering ohne Client-Token

### 11.3 Blob-Downloads

Für Datei-Downloads (CSV, PDF) direkt `fetch` verwenden:

```typescript
import { getApiBase } from "@/app/lib/api-client";

const response = await fetch(`${getApiBase()}/api/v1/export`, {
  headers: { Authorization: `Bearer ${accessToken}` },
});
const blob = await response.blob();
```

---

## 12. Type-Konsistenz (Frontend ↔ Backend)

### 12.1 BillingUnit (Extra Services)

**Backend (authoritative):**
```python
# backend/app/schemas/extra_services.py
BillingUnit = Literal[
    "per_night",
    "per_stay",
    "per_person_per_night",
    "per_person_per_stay",
    "per_unit",
    "per_unit_night",
]
```

**Frontend MUSS identisch sein:**
```typescript
// frontend/app/types/extra-service.ts
export type BillingUnit =
  | 'per_night'
  | 'per_stay'
  | 'per_person_per_night'
  | 'per_person_per_stay'
  | 'per_unit'
  | 'per_unit_night';
```

**NICHT ERLAUBT:** `per_person` (ohne Präzision) - Backend unterstützt es nicht!

### 12.2 Response-Wrapper (List-Responses)

**Backend-Standard:**
```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]    # IMMER 'items', NIE 'data'
    total: int
    limit: int
    offset: int
```

**Frontend MUSS `.items` verwenden:**
```typescript
// RICHTIG
const data = await apiClient.get<{ items: T[] }>('/api/v1/...', accessToken);
setItems(data.items);

// FALSCH (Legacy - entfernen!)
setItems(data.items ?? data.data ?? []);
```

### 12.3 FK-Referenzen

| RICHTIG | FALSCH | Entity |
|---------|--------|--------|
| `service_id` | `extra_service_id` | PropertyExtraService |
| `property_id` | `propertyId` | Alle |
| `guest_id` | `guestId` | Booking |

### 12.4 Owner-Booking Felder (KRITISCH)

**Backend (Ziel-Schema):**
```python
class OwnerBookingResponse(BaseModel):
    check_in: date              # NICHT: date_from
    check_out: date             # NICHT: date_to
    total_price_cents: int      # Standardformat
```

**Frontend (mit Deprecation-Marker):**
```typescript
interface OwnerBooking {
  check_in: string;
  check_out: string;
  total_price_cents: number;

  /** @deprecated Use check_in instead */
  date_from?: string;
  /** @deprecated Use check_out instead */
  date_to?: string;
  /** @deprecated Use total_price_cents instead */
  total_price?: string;
}
```

### 12.5 Computed-Properties (Frontend)

Felder die das Backend NICHT liefert, aber das Frontend braucht:

```typescript
// Owner: name wird aus first_name + last_name berechnet
const getOwnerName = (owner: Owner) =>
  `${owner.first_name ?? ''} ${owner.last_name ?? ''}`.trim() || 'Unbekannt';

// Guest: address wird aus address_line1 + address_line2 berechnet
const getGuestAddress = (guest: Guest) =>
  [guest.address_line1, guest.address_line2].filter(Boolean).join(', ');
```

### 12.6 Behobene Inkonsistenzen (Type-Consistency Konsolidierung 2026-03-04)

| Entity | Problem | Status | Commit |
|--------|---------|--------|--------|
| OwnerBooking | `date_from`/`date_to` statt `check_in`/`check_out` | ✅ BEHOBEN | Phase 1 |
| ExtraService | Frontend hatte `per_person` (Backend nicht) | ✅ BEHOBEN | Phase 2 |
| Owner | Frontend erwartete `name` (Backend liefert nicht) | ✅ BEHOBEN | Phase 3 |
| Guest | Legacy `address` Feld | ✅ BEHOBEN (bereits) | Phase 4 |
| ExtraServiceList | `.data` Fallback im Frontend | ✅ BEHOBEN | Phase 5 (`bc2864d`) |
| BookingRequest | Ungenutzes `deadline` Feld | ✅ BEHOBEN | Phase 6 (`3ba6947`) |
| PropertyExtraService | `extra_service_id` statt `service_id` | ✅ BEHOBEN | Phase 7 (`c605537`) |

### 12.7 Revert-Strategie

```bash
# Einzelne Phase revertieren
git reset --hard pre-type-consistency-phase-{N}

# Alles revertieren
git reset --hard pre-type-consistency-baseline
```

---

### 12.8 Behobene Inkonsistenzen Phase 2 (2026-03-04) — ✅ COMPLETE

#### 12.8.1 Pricing-Feldnamen ✅ BEHOBEN (Phase 1, Commit `a502bcd`)

| Entity | Legacy (FALSCH) | Korrekt (Backend) | Status |
|--------|-----------------|-------------------|--------|
| RatePlan | `base_price_cents` | `base_nightly_cents` | ✅ @deprecated |
| Season | `nightly_rate_cents` | `nightly_cents` | ✅ @deprecated |
| ExtraService | `price_cents` | `default_price_cents` | ✅ @deprecated |
| ExtraService | `price_type` | `billing_unit` | ✅ @deprecated |
| PropertyExtraService | `custom_price_cents` | `price_override_cents` | ✅ @deprecated |
| VisitorTax | `rate_cents` | `amount_cents` | ✅ @deprecated |
| VisitorTax | `child_age_limit` | `free_under_age` | ✅ @deprecated |

**Standard-Konvention für Pricing-Felder:**
```
nightly_cents        - Preis pro Nacht (in Cent)
base_nightly_cents   - Basispreis pro Nacht (in Cent)
amount_cents         - Betrag (in Cent)
price_override_cents - Preisüberschreibung (in Cent)
default_price_cents  - Standardpreis (in Cent)
```

#### 12.8.2 Booking-Feldnamen ✅ BEHOBEN (Phase 2, Commit `b07ef5a`)

| Legacy (FALSCH) | Korrekt (Backend) | Status |
|-----------------|-------------------|--------|
| `tax` | `tax_amount` | ✅ @deprecated |
| `guest_notes` | `guest_message` | ✅ @deprecated |

#### 12.8.3 Nicht-implementierte Backend-Felder ✅ DOKUMENTIERT (Phase 3, Commit `97650b4`)

| Entity | Feld | Frontend-Status | Entscheidung |
|--------|------|-----------------|--------------|
| Amenity | `is_highlighted` | ✅ @deprecated | Keine Migration nötig (0 Verwendungen) |
| Tax | `is_inclusive` | ✅ @deprecated | Keine Migration nötig (0 Verwendungen) |
| VisitorTaxPeriod | `child_rate_cents` | ✅ @deprecated | Keine Migration nötig (0 Verwendungen) |

#### 12.8.4 Zeit-Felder (OK - keine Änderung nötig)

| Entity | Feld | Backend-Typ | Frontend-Typ | Status |
|--------|------|-------------|--------------|--------|
| Property | `check_in_time` | `time` | `string` | ✅ OK (JSON serialisiert als String) |
| Property | `check_out_time` | `time` | `string` | ✅ OK (JSON serialisiert als String) |

#### 12.8.5 Guest-Timeline Felder ✅ KORRIGIERT (Phase 4, Commit `0620cf2`)

**Erkenntnis:** Backend `GuestTimelineBooking` verwendet korrekterweise `_date` Suffix.

| Korrekt (Backend) | Alias (Legacy) | Status |
|-------------------|----------------|--------|
| `check_in_date` | `check_in` | ✅ Alias @deprecated |
| `check_out_date` | `check_out` | ✅ Alias @deprecated |

#### 12.8.6 Doppelte Varianten ✅ BEHOBEN (Phase 5, Commit `f0764b2`)

| Entity | Legacy | Korrekt (Backend) | Status |
|--------|--------|-------------------|--------|
| VisitorTax | `is_active` | `active` | ✅ @deprecated |
| FeeTemplate | `is_taxable` | `taxable` | ✅ @deprecated |
| PropertyFee | `is_taxable` | `taxable` | ✅ @deprecated |
| TeamMember | `role` | `role_id` + `role_code` + `role_name` | ✅ @deprecated |
| Invite | `role` | `role_id` + `role_code` + `role_name` | ✅ @deprecated |

---

### 12.9 Offene Inkonsistenzen Phase 3 (Stand 2026-03-04)

> **Baseline-Tag:** `pre-type-consistency-3-baseline`
> **TODO-Liste:** `/PMS-Webapp-Dokumente/PMS-Webapp-TODO.md`

#### 12.9.1 Availability-Feldnamen (KRITISCH)

| Frontend (FALSCH) | Backend (RICHTIG) | Aktion |
|-------------------|-------------------|--------|
| `date_from` / `date_to` | `from_date` / `to_date` | Frontend anpassen |
| `status` | `state` | Frontend anpassen |
| `start` / `end` | `start_date` / `end_date` | Frontend anpassen |
| `pending_markers` | `pending_requests` | Frontend anpassen |
| — | `kind: 'available' \| 'booking' \| 'block'` | Frontend hinzufügen |

**Standard-Konvention für Availability-Felder:**
```
from_date / to_date     - Query-Parameter für Zeitraum
start_date / end_date   - Segment-Grenzen (Beginn/Ende)
state                   - Status: 'available' | 'booked' | 'blocked'
kind                    - Art: 'available' | 'booking' | 'block'
```

#### 12.9.2 Media-Feldnamen (KRITISCH)

| Frontend (FALSCH) | Backend (RICHTIG) | Aktion |
|-------------------|-------------------|--------|
| `tenant_id` | `agency_id` | Frontend umbenennen |
| `FileType` (3 Werte) | `ALLOWED_FILE_TYPES` (4 Werte) | `"document"` hinzufügen |

**Standard-Konvention für Media-Felder:**
```
agency_id    - Tenant/Agentur-Referenz (NICHT tenant_id!)
file_type    - 'image' | 'pdf' | 'video' | 'document'
```

#### 12.9.3 Branding-Felder ✅ OK (False Positive korrigiert)

Die gradient-Felder existieren bereits in der Datenbank:

| Schema-Feld | DB-Spalte | Status |
|-------------|-----------|--------|
| `gradient_from` | `tenant_branding.gradient_from` | ✅ Existiert (Migration 20260226163000) |
| `gradient_via` | `tenant_branding.gradient_via` | ✅ Existiert (Migration 20260226163000) |
| `gradient_to` | `tenant_branding.gradient_to` | ✅ Existiert (Migration 20260226163000) |

**Nachweis:** `supabase/migrations/20260226163000_add_branding_nav_behavior.sql` Zeilen 18-20

#### 12.9.4 Property Required-Felder (HOCH)

Backend erwartet diese Felder als **REQUIRED** bei `PropertyCreate`:

**Pflicht:**
- `name`, `property_type`
- `bedrooms`, `beds`, `bathrooms`, `max_guests`
- `address_line1`, `city`, `postal_code`, `country`
- `base_price`, `currency`

**Optional:**
- `internal_name`, `description`, `size_sqm`
- `owner_id`, `latitude`, `longitude`
- `cleaning_fee`, `security_deposit`, `extra_guest_fee`

**Frontend muss prüfen:** Sind diese Felder als `optional` markiert obwohl Backend sie erwartet?

#### 12.9.5 Website/Public-Felder ✅ BEHOBEN (Phase 3.5)

| Frontend | Backend | Status |
|----------|---------|--------|
| `SiteSettings.phone` | `phone: Optional[str]` | ✅ Hinzugefügt |
| `SiteSettings.email` | `email: Optional[str]` | ✅ Hinzugefügt |
| `SiteSettings.address` | `address: Optional[str]` | ✅ Hinzugefügt |
| `SiteSettings.social_links` | `social_links: Dict[str, str]` | ✅ Hinzugefügt |
| `TopbarConfig` (vollständig) | `TopbarConfig` | ✅ Hinzugefügt |
| `TopbarItem` | `TopbarItem` | ✅ Hinzugefügt |
| `PublicDesignData` erweitert | `PublicSiteDesignResponse` | ✅ Vollständig synchronisiert |

**Neue Felder in `PublicDesignData`:**
- `logo_light_url`, `logo_dark_url`, `favicon_url`, `logo_display_mode`, `logo_height_px`
- `header_padding_top_px`, `header_padding_bottom_px`
- `topbar_config: TopbarConfig`
- `updated_at`

**Synchronisiert:** `frontend/app/types/website.ts` ↔ `backend/app/schemas/public_site.py`

#### 12.9.6 Block-System ✅ BEHOBEN (Phase 3.6)

**Neue Datei:** `frontend/app/types/blocks.ts`

**Implementiert:**

| Typ-Kategorie | Anzahl | Status |
|---------------|--------|--------|
| BlockType (Union) | 26 Block-Typen | ✅ |
| Block-Item-Types | 6 (Testimonial, FAQ, Trust, Offer, Location, USP) | ✅ |
| Block-Props | 20+ typisierte Props-Interfaces | ✅ |
| Widget-Props | 6 (Button, Headline, Paragraph, Spacer, Divider, IconBox) | ✅ |
| BlockStyleOverrides | 30+ Style-Properties | ✅ |
| BlockTemplate CRUD | 4 Interfaces | ✅ |
| Type Guards | `isContainerBlock()`, `isWidgetBlock()` | ✅ |

**Architektur:**
- `blocks.ts`: Vollständige Block-Typ-Definitionen (Backend-Sync)
- `website.ts`: Re-exportiert Block-Types + Website-spezifische Types
- `Block.props: Record<string, unknown>` für Flexibilität
- Spezifische `*Props` Interfaces für typsicheren Zugriff

**Synchronisiert:** `blocks.ts` ↔ `block_validation.py`, `block_templates.py`

#### 12.9.7 Operations/AuditLog ✅ BEHOBEN (Phase 3.7)

| Frontend (alt) | Backend (aktuell) | Status |
|----------------|-------------------|--------|
| `actor_id`, `user_id` | `actor_user_id` | ✅ @deprecated |
| `target_type`, `resource_type` | `entity_type` | ✅ @deprecated |
| `target_id`, `resource_id` | `entity_id` | ✅ @deprecated |
| `ip_address` | `ip` | ✅ @deprecated |
| `details` | `metadata` | ✅ @deprecated |

**AuditLogEntry Backend-Schema:**
```
agency_id, actor_user_id, actor_type,
action, entity_type, entity_id,
request_id, idempotency_key,
ip, user_agent, metadata, created_at
```

**Synchronisiert:** `operations.ts` ↔ `core/audit.py`

---

## 12.10 Type-Consistency Phase 3 Abschluss (2026-03-04)

**Status:** ✅ ABGESCHLOSSEN

| Phase | Beschreibung | Status |
|-------|-------------|--------|
| 3.1 | Availability Types | ✅ |
| 3.2 | Media Library Types | ✅ |
| 3.3 | Branding Types (FALSE POSITIVE) | ✅ |
| 3.4 | Property Types | ✅ |
| 3.5 | Website/Public Types | ✅ |
| 3.6 | Block System Types | ✅ |
| 3.7 | Operations/AuditLog Types | ✅ |
| 3.8 | Cleanup & Medium Priority | ✅ |
| 3.9 | Documentation & Completion | ✅ |

**Neue Dateien:**
- `frontend/app/types/blocks.ts` (600+ Zeilen)

**Synchronisierte Dateien:**
- availability.ts, media.ts, property.ts, website.ts
- operations.ts, cancellation.ts, dashboard.ts, owner.ts

**Revert-Tags:**
- `pre-type-consistency-3-baseline`
- `pre-type-consistency-3-phase-{1-8}`

---

## 13. Type-Consistency Konventionen (Phase 4)

> **Status:** ✅ IMPLEMENTIERT (2026-03-04)
> **Commits:** Siehe `backend/docs/project_status.md`

### 13.1 Branding-Type Konventionen

**Datei:** `frontend/app/types/branding.ts` (356 Zeilen)

**Union Types:**

| Type | Werte |
|------|-------|
| `FontFamily` | `'system' \| 'inter' \| 'roboto' \| 'open-sans' \| 'poppins'` |
| `RadiusScale` | `'none' \| 'sm' \| 'md' \| 'lg'` |
| `ThemeMode` | `'system' \| 'light' \| 'dark'` |
| `ShadowIntensity` | `'none' \| 'subtle' \| 'normal' \| 'strong'` |
| `LogoPosition` | `'left' \| 'center'` |

**Haupt-Interfaces:**

| Interface | Beschreibung |
|-----------|--------------|
| `TenantBranding` | Alle 30+ Branding-Felder |
| `NavigationBrandingConfig` | JSONB nav_config Struktur |
| `ThemeTokens` | Berechnete Theme-Tokens |
| `BrandingUpdate` | Partial für API-Updates |
| `BrandingResponse` | API-Response mit tokens |

**Feld-Kategorien:**

| Kategorie | Beispiele | TypeScript-Typ |
|-----------|-----------|----------------|
| Farben | `primary_color`, `nav_bg_color` | `string \| null` (Hex #RRGGBB) |
| Größen | `topbar_height_px`, `nav_item_font_size_px` | `number \| null` |
| Skalen | `radius_scale`, `shadow_intensity` | Union Type |
| Boolean | `enable_favorites`, `default_sidebar_collapsed` | `boolean \| null` |
| JSONB | `nav_config` | `NavigationBrandingConfig \| null` |

**Utilities:**
- `isValidHexColor()` - Hex-Farbvalidierung
- `getDefaultThemeTokens()` - Fallback-Tokens
- `deriveBrandingTokens()` - Token-Berechnung aus Branding
- `ALLOWED_NAV_KEYS` - Konstante für Navigation-Validierung

### 13.2 Guest-Erweiterungen

**Datei:** `frontend/app/types/guest.ts`

**Neue Union Types:**

| Type | Werte |
|------|-------|
| `IdDocumentType` | `'passport' \| 'id_card' \| 'drivers_license'` |
| `CommunicationChannel` | `'email' \| 'phone' \| 'whatsapp' \| 'sms'` |
| `GuestSource` | `'direct' \| 'airbnb' \| 'booking_com' \| ...` |

**Hinzugefügte Felder:**

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `auth_user_id` | `string \| null` | Link zu auth.users |
| `id_document_type` | `IdDocumentType \| null` | Ausweistyp |
| `id_document_number` | `string \| null` | Ausweisnummer |
| `id_verified_at` | `string \| null` | Verifizierungs-Timestamp |
| `marketing_consent_at` | `string \| null` | Consent-Timestamp |
| `first_booking_at` | `string \| null` | Erste Buchung |
| `average_rating` | `string \| null` | Durchschnittsbewertung (Decimal) |
| `source` | `GuestSource \| null` | Akquise-Quelle |
| `deleted_at` | `string \| null` | Soft-Delete Timestamp |

**Type Guards:**
- `isGuestDeleted()`, `isGuestActive()`
- `isGuestVip()`, `isGuestBlacklisted()`
- `isGuestVerified()`, `hasGuestAccount()`
- `getGuestFullName()`

### 13.3 API-Pagination Standard

**Einheitliches Format:**

```typescript
// Query-Parameter
interface PaginationParams {
  limit: number;   // Default: 20, Max: 100
  offset: number;  // Default: 0
}

// Response-Wrapper
interface PaginatedResponse<T> {
  items: T[];      // IMMER 'items', NIEMALS 'data'
  total: number;   // Gesamtanzahl (ohne Pagination)
  limit: number;   // Angewendetes Limit
  offset: number;  // Angewendeter Offset
}
```

**Deprecated (nicht mehr verwenden):**
- `page` / `page_size` → Ersetzen durch `limit` / `offset`
- `per_page` → Ersetzen durch `limit`
- `.data` in Response → Ersetzen durch `.items`

### 13.4 Accessibility-Konventionen

**Pflicht für alle UI-Komponenten:**

| Element | Pflicht-Attribute |
|---------|-------------------|
| `<button>` (Icon-only) | `aria-label="..."` |
| `<input>` | `id="..."` + `<label htmlFor="...">` |
| Modal/Dialog | `role="dialog"` + `aria-modal="true"` + FocusTrap |
| Fehlermeldung | `id="...-error"` + `aria-describedby` auf Input |
| Navigation | `aria-label="Hauptnavigation"` |
| Aktiver Nav-Link | `aria-current="page"` |

**Skip-Link Pattern:**
```tsx
<a href="#main-content" className="sr-only focus:not-sr-only ...">
  Zum Hauptinhalt springen
</a>
```

### 13.5 Audit-Workflow

**Regelmäßige Audits:**

| Audit-Typ | Häufigkeit | Skill |
|-----------|------------|-------|
| Type-Consistency | Nach Schema-Änderungen | `/type-audit` |
| Accessibility | Nach UI-Änderungen | `/accessibility-audit` |
| Security | Vor Releases | Runbook |

**Audit-Berichte speichern:**
```
/PMS-Webapp-Dokumente/Audit/
├── Code-Struktur/
├── Funktional/
├── UX-UI/
└── Type-Konsistenz/
```

---

**Letzte Aktualisierung:** 2026-03-04 (Type-Consistency Phase 4 geplant)
