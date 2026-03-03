# 45 - Booking Service Architektur

> **Datum:** 2026-03-03
> **Status:** IMPLEMENTED
> **Betroffene Dateien:** `backend/app/services/booking/`, `backend/app/services/booking_service.py`

---

## Übersicht

Der `BookingService` wurde von einer monolithischen 2464-Zeilen-Datei in ein modulares Package mit spezialisierten Sub-Services refaktoriert. Das Composition Pattern ermöglicht saubere Trennung der Verantwortlichkeiten bei voller Backward-Kompatibilität.

## Architektur

```
backend/app/services/
├── booking/                          # Neues Package
│   ├── __init__.py                   # Re-Exports aller Services und Helpers
│   ├── service.py                    # BookingService (Haupt-Orchestrierung)
│   ├── query.py                      # BookingQueryService (Lese-Operationen)
│   ├── create.py                     # BookingCreateService (Buchungserstellung)
│   ├── update.py                     # BookingUpdateService (Updates/Status)
│   ├── cancellation.py               # BookingCancellationService (Stornierung)
│   └── utils.py                      # Helper-Funktionen
└── booking_service.py                # Backward-Compat Re-Export (DEPRECATED)
```

## Sub-Services

### BookingQueryService (`query.py`)

Lese-Operationen für Buchungen:

- `list_bookings(agency_id, filters, pagination)` - Buchungsliste mit Filter/Pagination
- `get_booking(booking_id, agency_id)` - Einzelne Buchung abrufen
- `check_availability(property_id, check_in, check_out)` - Verfügbarkeit prüfen

### BookingCreateService (`create.py`)

Buchungserstellung mit Validierung:

- `create_booking(booking_data, agency_id)` - Neue Buchung erstellen
- `generate_booking_reference()` - Eindeutige Referenznummer generieren
- `_upsert_guest()` - Gast anlegen oder aktualisieren (intern)

Features:
- Double-Booking Prevention mit inventory_ranges
- Automatische Preisberechnung
- Gast-Upsert basierend auf E-Mail

### BookingUpdateService (`update.py`)

Status-Übergänge und Buchungsaktualisierungen:

- `update_booking_status(booking_id, new_status, agency_id, role)` - Status ändern
- `update_booking(booking_id, agency_id, update_data)` - Buchung aktualisieren

Zustandsmaschine:
```
inquiry → pending → confirmed → checked_in → checked_out
       |                      |
       → declined            → cancelled
```

Features:
- Optimistic Locking mit `version`-Feld
- Advisory Locks für Concurrent Updates
- Inventory Range Updates bei Datumsänderungen

### BookingCancellationService (`cancellation.py`)

Stornierung und Rückerstattung:

- `cancel_booking(booking_id, cancel_data, agency_id)` - Buchung stornieren
- `calculate_refund(booking_id, agency_id)` - Rückerstattung berechnen

Features:
- Idempotente Stornierung (mehrfacher Aufruf sicher)
- Rückerstattungsberechnung basierend auf Policy
- Optional: Post-Cancel Hold Block

### BookingService (`service.py`)

Zentrale Fassade mit Composition Pattern:

```python
class BookingService:
    def __init__(self, db):
        self.query = BookingQueryService(db)
        self.create = BookingCreateService(db)
        self.update = BookingUpdateService(db)
        self.cancellation = BookingCancellationService(db)
```

Alle öffentlichen Methoden delegieren an Sub-Services.

## Helper-Funktionen (`utils.py`)

- `to_uuid(value)` - String zu UUID konvertieren
- `normalize_cancelled_by(value)` - Stornierungsgrund normalisieren
- `normalize_source(value)` - Buchungsquelle normalisieren
- `normalize_status(value)` - Status normalisieren
- `normalize_payment_status(value)` - Zahlungsstatus normalisieren
- `retry_on_deadlock(fn)` - Decorator für Deadlock-Retry
- `get_availability_service(db)` - Lazy Import für AvailabilityService

## Import-Patterns

### Empfohlen (neu)

```python
from app.services.booking import BookingService

# Oder für direkten Sub-Service-Zugriff:
from app.services.booking import BookingQueryService, BookingCreateService
```

### Backward-Kompatibel (deprecated)

```python
from app.services.booking_service import BookingService
from app.services.booking_service import retry_on_deadlock
```

## Vorteile der neuen Architektur

| Aspekt | Vorher | Nachher |
|--------|--------|---------|
| Dateigröße | 2464 Zeilen | ~150 Zeilen (service.py) |
| Testbarkeit | Schwer (alles gekoppelt) | Einfach (isolierte Services) |
| Lesbarkeit | Niedrig | Hoch (fokussierte Dateien) |
| Erweiterbarkeit | Schwierig | Einfach (neue Services hinzufügen) |
| Wartbarkeit | Aufwändig | Modular |

## Migration bestehender Code

Keine Migration erforderlich. Alle bestehenden Imports funktionieren weiterhin:

```python
# Diese Imports funktionieren weiterhin:
from app.services.booking_service import BookingService  # ✓
from app.services.booking_service import retry_on_deadlock  # ✓
from app.services.booking_service import normalize_cancelled_by  # ✓
```

## Verifizierung

```bash
# Alle Module kompilieren
cd backend
python -m compileall app/services/booking/ -q

# Import-Test
python -c "from app.services.booking import BookingService; print('OK')"
python -c "from app.services.booking_service import BookingService; print('OK')"
```

## Commits

| Commit | Beschreibung |
|--------|--------------|
| `83abd7a` | booking/ Ordner + utils.py |
| `150514e` | query.py extrahiert |
| `0fc64ad` | create.py extrahiert |
| `c7b364d` | update.py extrahiert |
| `4628259` | cancellation.py extrahiert |
| `5ddcb64` | service.py Orchestrierung |
| `f13dc74` | booking_service.py Re-Export |

---

*Erstellt: 2026-03-03 | Refactoring: booking_service.py Aufteilung*
