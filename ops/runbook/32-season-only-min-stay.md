# 32 - Season-Only Min Stay

**Datum:** 2026-02-20

## Übersicht

Mindestaufenthalt wird nicht mehr auf Property-Level definiert, sondern über Rate-Plan-Seasons gesteuert. Dies ermöglicht saisonabhängige Mindestaufenthalte (z.B. 7 Nächte Hauptsaison, 2 Nächte Nebensaison).

## Fallback-Hierarchie

```
1. rate_plan_seasons.min_stay_nights  (Saison für Check-in-Datum)
   ↓ falls NULL oder keine Saison
2. rate_plans.min_stay_nights         (Rate-Plan Default)
   ↓ falls NULL
3. Hard-Default: 1 Nacht              (kein Minimum)
```

**Check-in-Datum bestimmt die Regel** (Branchenstandard)

## Betroffene Komponenten

### Backend

| Datei | Funktion | Änderung |
|-------|----------|----------|
| `backend/app/services/rate_plan_resolver.py` | `get_effective_min_stay()` | Neue Funktion |
| `backend/app/services/booking_service.py` | `create_booking()` | Season-Validierung |
| `backend/app/services/booking_service.py` | `update_booking()` | Season-Validierung |

### Frontend

| Datei | Änderung |
|-------|----------|
| `frontend/app/properties/[id]/page.tsx` | Edit Modal: "Min. Nächte" entfernt |
| `frontend/app/properties/[id]/page.tsx` | Display: "Siehe Preiseinstellungen" |

## Fehlermeldungen

Wenn eine Buchung gegen den Mindestaufenthalt verstößt:

```
Mindestaufenthalt ist 7 Nächte (Saison: Hauptsaison)
```

Falls keine Saison definiert:

```
Mindestaufenthalt ist 3 Nächte
```

## Min-Stay konfigurieren

1. Navigiere zu `/properties/{id}/rate-plans`
2. Bearbeite eine Saisonzeit
3. Setze "Min. Nächte" auf den gewünschten Wert

## Datenbank

`properties.min_stay` existiert weiterhin, wird aber nicht mehr für Validierung verwendet. Dies ermöglicht:
- Rollback bei Problemen
- Historische Daten bleiben erhalten

## Troubleshooting

### Fehler: "Mindestaufenthalt ist X Nächte"

1. Prüfe Rate-Plan-Seasons für das Property:
   ```sql
   SELECT label, date_from, date_to, min_stay_nights
   FROM rate_plan_seasons
   WHERE rate_plan_id IN (
     SELECT id FROM rate_plans
     WHERE property_id = 'PROPERTY_UUID'
     AND active = true AND archived_at IS NULL
   )
   AND active = true AND archived_at IS NULL
   ORDER BY date_from;
   ```

2. Prüfe Rate-Plan Default:
   ```sql
   SELECT name, min_stay_nights
   FROM rate_plans
   WHERE property_id = 'PROPERTY_UUID'
   AND active = true AND archived_at IS NULL;
   ```

### Kein Rate-Plan vorhanden

Falls kein aktiver Rate-Plan für das Property existiert, gilt Default = 1 Nacht.
