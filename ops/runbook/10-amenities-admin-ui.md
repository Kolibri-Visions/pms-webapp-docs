# Amenities Admin UI

This runbook chapter covers the Amenities management in the Admin UI.

**When to use:** Troubleshooting amenities toggle, CRUD operations, or category filtering.

## Overview

The Amenities page (`/amenities`) provides management for property features:

1. **List View**: Shows all amenities grouped by category
2. **Create/Edit**: Modal form for amenity CRUD
3. **Toggle Active**: Inline switch to enable/disable amenities
4. **Category Filter**: Filter amenities by category
5. **Search**: Search by name or description

## Common Issues

### PATCH /api/internal/amenities/:id Returns 400

**Symptom:** Toggling "aktiv/inaktiv" switch shows 400 error in DevTools.

**Cause (Fixed 2026-02-01):** The backend `AmenityUpdate` schema was missing `is_active` field.

**Resolution:**
1. Migration `20260201110000_add_amenities_is_active.sql` adds `is_active` column
2. Backend schema updated to accept `is_active` in PATCH requests
3. Service updated to handle `is_active` in dynamic UPDATE

**Verification:**
```bash
# Run smoke test
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_amenities_toggle_smoke.sh

# Expected: PASS=5, FAIL=0
```

### 503 Service Unavailable (Backend)

**Symptom:** All amenities operations return 503.

**Cause:** Amenities table not found (migration not applied).

**Resolution:**
1. Apply migration via Supabase Studio SQL Editor:
   - Copy contents of `supabase/migrations/20260122000000_add_amenities.sql`
   - Execute in SQL Editor
2. Verify table exists:
   ```sql
   SELECT to_regclass('public.amenities');
   -- Expected: 'amenities' (not NULL)
   ```

### 503/502 on /api/internal/amenities (Admin UI)

**Symptom:** Admin UI `/amenities` page shows 503 or 502 error in Network tab for `/api/internal/amenities`.

**Possible Causes:**

1. **Session expired**: Supabase session token expired
   - **Fix:** Clear cookies, re-login to Admin UI

2. **Backend unreachable**: `NEXT_PUBLIC_API_BASE_URL` misconfigured on server
   - **Check:** Verify env var in frontend deployment
   - **Fix:** Set `NEXT_PUBLIC_API_BASE_URL=https://api.fewo.kolibri-visions.de`

3. **Agency ID missing**: User not in any agency's team_members
   - **Check:** Query `team_members` for user_id
   - **Fix:** Add user to agency via team_members table

4. **Backend 503**: Upstream amenities service unavailable
   - **Check:** Direct API call: `curl -H "Authorization: Bearer $JWT" $API/api/v1/amenities`
   - **Fix:** See "503 Service Unavailable (Backend)" above

**Debug:** Check browser console and Next.js server logs for detailed error messages.

### Aktionen-Menü (Dropdown) wird abgeschnitten

**Symptom:** Das 3-Punkte-Menü ("Aktionen") bei einem Eintrag wird abgeschnitten oder ist nicht vollständig sichtbar.

**Ursache:** Das übergeordnete Container-Element hat `overflow: hidden`, was das Dropdown-Menü abschneidet.

**Lösung (Fixed 2026-02-01):**
1. Das Dropdown-Menü wird jetzt via React Portal direkt in `<body>` gerendert
2. z-index auf `9999` gesetzt, um über allen anderen Elementen zu erscheinen
3. Position wird dynamisch aus den Button-Koordinaten berechnet

**Verifizierung:** Öffne `/amenities`, klicke auf die 3-Punkte bei einem Eintrag → Menü erscheint vollständig.

### 403 Forbidden

**Symptom:** Create/Edit/Delete operations return 403.

**Cause:** User lacks admin/manager role.

**Resolution:**
1. Check user's role in `team_members` table
2. Ensure user has `admin` or `manager` role

## API Endpoints

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| List amenities | `/api/v1/amenities` | GET | all authenticated |
| Create amenity | `/api/v1/amenities` | POST | admin, manager |
| Get amenity | `/api/v1/amenities/{id}` | GET | all authenticated |
| Update amenity | `/api/v1/amenities/{id}` | PATCH | admin, manager |
| Delete amenity | `/api/v1/amenities/{id}` | DELETE | admin, manager |

**API Response Shape Note:**
- `GET /api/v1/amenities` returns a **JSON array** directly (not `{items: [...]}`)
- The internal proxy route (`/api/internal/amenities`) forwards this array to the UI
- Example: `[{"id": "...", "name": "WiFi", "is_active": true}, ...]`

### Toggle Active Example

```bash
# Toggle amenity inactive
curl -sS -X PATCH "$API/api/v1/amenities/$ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}' | jq .

# Response: { "id": "...", "is_active": false, ... }
```

## Smoke Test

**Location:** `backend/scripts/pms_amenities_toggle_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage (requires JWT_TOKEN)
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_amenities_toggle_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_amenities_toggle_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT with admin/manager role |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |

### What It Tests

1. GET /api/v1/amenities → List amenities
2. POST /api/v1/amenities → Create test amenity (if none exist)
3. PATCH /api/v1/amenities/{id} with `{is_active: false}` → Toggle off
4. GET /api/v1/amenities/{id} → Verify persisted state
5. PATCH /api/v1/amenities/{id} with `{is_active: true}` → Toggle back on

### Expected Result

```
RESULT: PASS
Summary: PASS=5, FAIL=0, SKIP=0
```

## Database Schema

```sql
-- amenities table
CREATE TABLE public.amenities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id uuid NOT NULL REFERENCES agencies(id),
  name varchar(255) NOT NULL,
  description text,
  category varchar(50),
  icon varchar(100),
  sort_order integer DEFAULT 0,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT amenities_unique_per_agency UNIQUE (agency_id, name)
);
```

## Icon Picker

Das Ausstattungs-Icon wird als String-Key in der Datenbank gespeichert (`icon` Spalte).

### Unterstützte Icon-Keys

Die folgenden Keys werden von der UI mit Lucide-React Icons gerendert:

| Key | Label | Icon |
|-----|-------|------|
| `wifi` | WLAN | Wifi |
| `tv` | Fernseher | Tv |
| `car` | Auto | Car |
| `parking` | Parkplatz | ParkingSquare |
| `key` | Schlüssel | Key |
| `lock` | Schloss/Safe | Lock |
| `shield` | Sicherheit | Shield |
| `snowflake` | Klimaanlage | Snowflake |
| `flame` | Heizung/Kamin | Flame |
| `coffee` | Kaffeemaschine | Coffee |
| `bath` | Badewanne | Bath |
| `bed` | Bett | Bed |
| `refrigerator` | Kühlschrank | Refrigerator |
| `utensils` | Besteck/Küche | Utensils |
| `paw` | Haustierfreundlich | PawPrint |
| `baby` | Kinderfreundlich | Baby |
| `accessibility` | Barrierefrei | Accessibility |
| `trees` | Garten | Trees |
| `waves` | Pool/Wasser | Waves |
| `wind` | Ventilator | Wind |
| `sun` | Sonnenterrasse | Sun |
| `dumbbell` | Fitness | Dumbbell |
| `bike` | Fahrrad | Bike |
| `sofa` | Wohnzimmer | Sofa |
| `airvent` | Lüftung | AirVent |
| `microwave` | Mikrowelle | Microwave |
| `cooking` | Kochen | CookingPot |
| `washer` | Waschmaschine | Shirt |
| `armchair` | Sessel | Armchair |
| `lamp` | Beleuchtung | Lamp |
| `monitor` | Arbeitsplatz | Monitor |
| `speaker` | Soundsystem | Speaker |
| `gaming` | Spielkonsole | Gamepad2 |
| `books` | Bücher | BookOpen |
| `scissors` | Werkzeug | Scissors |
| `sparkles` | Sauberkeit | Sparkles |

### Fallback-Verhalten

- **Bekannter Key:** Zeigt das entsprechende Lucide-Icon
- **Unbekannter Key:** Zeigt den Text als kleines Label (Legacy-Kompatibilität für z.B. "ofen")
- **Kein Icon:** Zeigt "—"

### Icon Picker Komponente

Datei: `frontend/app/amenities/components/amenity-icon-picker.tsx`

Features:
- Visuelles Grid aller verfügbaren Icons
- Suchfunktion nach Name/Label
- "Benutzerdefinierter Text" Option für Legacy-Werte
- Vorschau des aktuell gewählten Icons

## Objekt-Detail: Ausstattung

### Deaktivierte Ausstattungen werden ausgeblendet

**Verhalten (seit 2026-02-01):**
- Auf der Objekt-Detail-Seite (`/properties/{id}`) werden nur aktive Ausstattungen (`is_active=true`) angezeigt
- Deaktivierte Ausstattungen werden automatisch ausgeblendet

**Im "Ausstattung zuweisen" Modal:**
- Inaktive Ausstattungen werden nur angezeigt, wenn sie bereits dem Objekt zugewiesen sind
- Bereits zugewiesene inaktive Ausstattungen zeigen ein "deaktiviert" Badge
- Inaktive, nicht zugewiesene Ausstattungen sind nicht auswählbar

### Icons im Objekt-Detail

**Verhalten (seit 2026-02-01):**
- Ausstattungs-Icons werden mit der `AmenityIcon` Komponente gerendert
- Shared Komponente: `frontend/app/components/amenity-icon.tsx`
- Unterstützt alle Icon-Keys aus dem Icon Picker (s.o.)

**API-Payload:**
- `GET /api/v1/amenities/property/{id}` liefert `is_active` und `icon` für jede Ausstattung
- Frontend filtert basierend auf `is_active`

### Property Amenities Smoke Test

**Location:** `backend/scripts/pms_property_amenities_is_active_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

**Usage:**
```bash
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_property_amenities_is_active_smoke.sh
```

**What It Tests:**
1. Find a property with amenities
2. Verify `is_active` field is present in response
3. Verify `icon` field is present in response

**Expected Result:**
```
RESULT: PASS
Summary: PASS=N, FAIL=0, SKIP=0
```

## Related Documentation

- [Backend Amenities Routes](../../api/amenities.md) — API endpoint details
- [Scripts README](../../../scripts/README.md#pms_amenities_toggle_smokesh) — Smoke test documentation
