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

### 12.6 Bekannte Inkonsistenzen (Stand 2026-03-04)

| Entity | Problem | Status |
|--------|---------|--------|
| OwnerBooking | `date_from`/`date_to` statt `check_in`/`check_out` | TODO: Phase 1 |
| ExtraService | Frontend hat `per_person` (Backend nicht) | TODO: Phase 2 |
| Owner | Frontend erwartet `name` (Backend liefert nicht) | TODO: Phase 3 |
| Guest | Legacy `address` Feld | TODO: Phase 4 |
| ExtraServiceList | `.data` Fallback im Frontend | TODO: Phase 5 |

---

**Letzte Aktualisierung:** 2026-03-04 (Type-Konsistenz-Definitionen hinzugefügt)
