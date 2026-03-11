# ADR-005: Doppelbuchungsschutz — PostgreSQL Exclusion Constraint

**Status:** Accepted (implementiert)
**Datum:** 2025-12-21

---

## Entscheidung

**PostgreSQL Exclusion Constraint** als primaerer Doppelbuchungsschutz.
Kein Redis Distributed Locking.

## Implementierung

```sql
-- Exclusion Constraint auf bookings Tabelle
EXCLUDE USING gist (
    property_id WITH =,
    daterange(check_in, check_out, '[)') WITH &&
)
WHERE (
    status = ANY (ARRAY['confirmed', 'checked_in'])
    AND deleted_at IS NULL
);
```

### Welche Status werden geprueft?

| Status | Blockiert Ueberlappung? |
|--------|------------------------|
| `confirmed` | Ja |
| `checked_in` | Ja |
| `inquiry` | Nein |
| `pending` | Nein |
| `requested` | Nein |
| `under_review` | Nein |
| `cancelled` | Nein |
| `declined` | Nein |
| `no_show` | Nein |
| `checked_out` | Nein |

### Datum-Semantik

Half-open Interval `[check_in, check_out)`:
- Check-in Tag ist belegt
- Check-out Tag ist frei (naechster Gast kann am selben Tag einchecken)

## Was NICHT implementiert ist

- Kein Redis Distributed Lock (RedLock)
- Keine Optimistic Locking mit Version-Feld
- Keine StatusResolution-Klasse fuer Konflikte
- Kein Lock waehrend Checkout-Flow

## Konsequenzen

- Doppelbuchungen sind auf DB-Ebene unmoeglich (fuer confirmed/checked_in)
- Race Conditions bei gleichzeitigen Buchungen → DB wirft Constraint-Fehler
- Applikation muss den DB-Fehler abfangen und nutzerfreundlich melden
