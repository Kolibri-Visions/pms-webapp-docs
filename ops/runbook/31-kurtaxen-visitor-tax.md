# 31 — Kurtaxen (Visitor Tax) Management

**Letzte Aktualisierung**: 2026-02-20

---

## Überblick

Verwaltung von Kurtaxen (Tourismusabgabe) pro Gemeinde mit saisonalen Tarifen.

**Anwendungsfall**: Ferienwohnungsagenturen auf Sylt/Nordsee müssen Kurtaxe pro Person/Nacht abrechnen, die je nach Gemeinde und Saison variiert.

**Route**: `/kurtaxen` (Admin UI, unter OBJEKTE)

---

## Datenmodell

### Tabellen

| Tabelle | Beschreibung |
|---------|--------------|
| `visitor_tax_locations` | Gemeinden mit Name, Beschreibung, PLZ-Array |
| `visitor_tax_periods` | Saisonale Tarife (Betrag in Cents, Kinder-Freibetrag) |
| `properties.visitor_tax_location_id` | FK für Property-Zuweisung |

### Wichtige Felder

```sql
-- visitor_tax_locations
id UUID PRIMARY KEY
agency_id UUID NOT NULL              -- Mandantentrennung
name TEXT NOT NULL                   -- "Kampen", "List"
postal_codes TEXT[] DEFAULT '{}'     -- ['25999'] für PLZ-Matching
archived_at TIMESTAMPTZ NULL         -- Soft-Delete

-- visitor_tax_periods
location_id UUID NOT NULL            -- FK zu locations
label TEXT NOT NULL                  -- "Hauptsaison", "Nebensaison"
date_from DATE NOT NULL
date_to DATE NOT NULL
amount_cents INTEGER NOT NULL        -- 350 = 3,50€
free_under_age INTEGER NULL          -- Kinder unter X frei
active BOOLEAN DEFAULT true
```

### RLS-Policies

- **SELECT**: Alle authentifizierten Agency-Mitglieder
- **INSERT/UPDATE/DELETE**: Nur admin/manager

---

## API-Endpoints

### Locations

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/v1/visitor-tax/locations` | Liste (inkl. Perioden) |
| POST | `/api/v1/visitor-tax/locations` | Erstellen (atomar mit Perioden) |
| GET | `/api/v1/visitor-tax/locations/{id}` | Detail |
| PATCH | `/api/v1/visitor-tax/locations/{id}` | Aktualisieren |
| DELETE | `/api/v1/visitor-tax/locations/{id}` | Archivieren (soft) |
| POST | `/api/v1/visitor-tax/locations/{id}/restore` | Wiederherstellen |
| DELETE | `/api/v1/visitor-tax/locations/{id}/permanent` | Endgültig löschen |

### Perioden

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/v1/visitor-tax/locations/{id}/periods` | Liste |
| POST | `/api/v1/visitor-tax/locations/{id}/periods` | Hinzufügen |
| PATCH | `/api/v1/visitor-tax/locations/{id}/periods/{pid}` | Bearbeiten |
| DELETE | `/api/v1/visitor-tax/locations/{id}/periods/{pid}` | Löschen |
| POST | `/api/v1/visitor-tax/locations/{id}/periods/bulk-delete` | Bulk-Delete |

### PLZ-Suggestion

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| GET | `/api/v1/visitor-tax/suggest?postal_code=XXX` | Auto-Match Location |

---

## Frontend UI

### Navigation

Unter OBJEKTE → "Kurtaxen" (Icon: Landmark)

### Funktionen

1. **Gemeinden-Liste**: Accordion mit expandierbaren Perioden
2. **Create/Edit Modal**: Name, Beschreibung, PLZ (kommagetrennt), Inline-Perioden-Builder
3. **Sylt-Beispiel**: Button lädt vorkonfigurierte Haupt-/Nebensaison
4. **Bulk-Delete**: Checkbox-Auswahl für Perioden
5. **Archive/Restore**: Soft-Delete Workflow
6. **PLZ-Badges**: Visuelle Identifikation der zugeordneten PLZ

### Property-Integration

Im Property-Edit-Modal (Adress-Bereich):
- Dropdown zur Kurtaxen-Gemeinde-Zuweisung
- PLZ-Auto-Suggestion bei Adressänderung

---

## Troubleshooting

### Problem: Location wird nicht gefunden

**Symptom**: `GET /visitor-tax/locations` gibt leere Liste zurück

**Ursache**: Falsche Agency-ID oder archivierte Locations

**Lösung**:
```bash
# Prüfe Agency-ID im JWT
curl -s "https://api.fewo.kolibri-visions.de/api/v1/visitor-tax/locations?include_archived=true" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Problem: PLZ-Suggestion funktioniert nicht

**Symptom**: `GET /visitor-tax/suggest?postal_code=25999` gibt `location: null`

**Ursache**: PLZ nicht im `postal_codes` Array der Location

**Lösung**:
```sql
-- Prüfe PLZ-Zuordnung
SELECT id, name, postal_codes
FROM visitor_tax_locations
WHERE agency_id = 'xxx' AND '25999' = ANY(postal_codes);
```

### Problem: Hard-Delete schlägt fehl (409)

**Symptom**: `DELETE /locations/{id}/permanent` gibt 409 Conflict

**Ursache**: Properties referenzieren noch die Location

**Lösung**:
```sql
-- Finde referenzierende Properties
SELECT id, name FROM properties WHERE visitor_tax_location_id = 'xxx';

-- Entferne Referenzen
UPDATE properties SET visitor_tax_location_id = NULL WHERE visitor_tax_location_id = 'xxx';
```

---

## Verification Commands

### PROD Smoke Test

```bash
# WHERE: HOST-SERVER-TERMINAL

# 1. Auth
export TOKEN=$(curl -sX POST "$SB_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.de","password":"xxx"}' | jq -r '.access_token')

# 2. List Locations
curl -s "https://api.fewo.kolibri-visions.de/api/v1/visitor-tax/locations" \
  -H "Authorization: Bearer $TOKEN" | jq 'length'
# Expected: >= 0 (no error)

# 3. PLZ Suggestion
curl -s "https://api.fewo.kolibri-visions.de/api/v1/visitor-tax/suggest?postal_code=25999" \
  -H "Authorization: Bearer $TOKEN" | jq '.postal_code'
# Expected: "25999"

# 4. Admin UI
open https://admin.fewo.kolibri-visions.de/kurtaxen
# Verify: Page loads, navigation works
```

---

## Migration

**Datei**: `supabase/migrations/20260220000000_add_visitor_tax.sql`

**Anwendung**:
```bash
# WHERE: Supabase SQL Editor oder
cd /path/to/repo && supabase db push
```

**Rollback** (falls nötig):
```sql
-- ACHTUNG: Datenverlust!
DROP TABLE IF EXISTS visitor_tax_periods CASCADE;
DROP TABLE IF EXISTS visitor_tax_locations CASCADE;
ALTER TABLE properties DROP COLUMN IF EXISTS visitor_tax_location_id;
```

---

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `backend/app/api/routes/visitor_tax.py` | API Routes (878 Zeilen) |
| `backend/app/schemas/visitor_tax.py` | Pydantic Schemas |
| `frontend/app/kurtaxen/page.tsx` | UI (1330 Zeilen) |
| `frontend/app/kurtaxen/layout.tsx` | AdminShell Wrapper |
| `supabase/migrations/20260220000000_add_visitor_tax.sql` | DB Migration |
