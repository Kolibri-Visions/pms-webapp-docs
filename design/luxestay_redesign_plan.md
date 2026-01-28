# LuxeStay Admin UI Redesign - Implementierungsplan

## Design-System (Neu)

### Farben
```
Primary:    #0F1F3A  (Navy - Sidebar, Buttons, Headers)
Secondary:  #7A7D85  (Grau - Text, Borders)
Accent:     #C9A24D  (Gold - Icons, Active States, Highlights)
Background: #F2EFEA  (Off-White - Content Area)
Success:    #10B981  (Grün - Status "Live")
Error:      #EF4444  (Rot - Fehler)
Warning:    #F59E0B  (Orange - Warnungen)
```

### Typografie
- **Font:** Inter
- **Weights:** 400 (Regular), 600 (Semibold), 700 (Bold)
- **Sizes:** h1: 24px, h2: 20px, h3: 18px, body: 14px, small: 12px

### Spacing
- 8px-Raster: 8, 16, 24, 32, 48, 64px

### Border-Radius
- Cards: 8px
- Buttons: 6px
- Inputs: 4px

### Shadows
- Cards: 0 1px 3px rgba(0,0,0,0.12)
- Hover: 0 4px 6px rgba(0,0,0,0.1)

---

## Screenshot-Analyse: Property Detail Page

### Sidebar (Links, Fixed)
**Hintergrund:** #0F1F3A (Navy)
**Breite:** ~240px

**Logo:**
- Gold-Icon (Raute/Diamant #C9A24D)
- "LuxeStay" (Weiß, Bold)
- "ADMIN PANEL" (Grau, Klein)

**Navigation:**
- Dashboard (Grid-Icon, Weiß)
- **Properties** (Building-Icon, AKTIV = Gold + Indicator)
- Bookings (Bookmark-Icon, Weiß)
- Calendar (Calendar-Icon, Weiß)
- Finance (Credit Card-Icon, Weiß)
- Reports (Chart-Icon, Weiß)
- Settings (Gear-Icon, Weiß)

**User-Profil (Unten):**
- Avatar (40px, rund)
- "Alexander G." (Weiß)
- "Super Admin" (Grau, 12px)

### Hero-Section
- **Hero-Image:** Full-width, ~400px Höhe
- **Property Name:** "Ocean View" (Weiß, 32px, über Bild)
- **Beschreibung:** "with direct ocean access..." (Weiß, 14px)
- **Status-Card (Floating rechts oben):**
  - "Property Status" Label
  - Toggle-Switch (Gold/Grün)
  - "Live" Text mit grünem Dot

### Tab-Navigation
- Overview | Rates | Calendar | Reviews
- Active Tab: Gold-Underline

### Content (2-Spalten-Grid)

**Rechte Spalte Cards:**

1. **Times & Prices Card**
   - Gold-Uhr-Icon + "Times & Prices" Titel
   - Check-in Time: 03:00 PM (Time-Picker)
   - Check-out Time: 11:00 AM (Time-Picker)
   - Currency: USD ($) (Dropdown)
   - Base Price/Night: $ 450 (Input)

2. **Amenities Card**
   - Gold-WiFi-Icon + "Amenities" Titel
   - "Selected: 8" Counter (rechts)
   - Grid (3 Spalten):
     - Wifi ✓, Pool ✓, Kitchen ✓
     - Gym ☐, AC ✓, TV ✓
     - Parking ✓, Pets ☐, Washer ✓
   - Gold-Checkboxen für aktiv
   - Graue Checkboxen für inaktiv

---

## Implementierungsplan

### Phase 1: Design-System Setup ✅
1. Tailwind Config aktualisieren
2. Farb-Tokens definieren
3. Component-Library vorbereiten

### Phase 2: Globale Komponenten 🔄
1. **AdminShell** komplett neu:
   - Navy Sidebar mit Gold-Akzenten
   - Logo-Komponente
   - Navigation mit Active-States
   - User-Profil-Bereich
2. **Top Bar:**
   - Breadcrumbs
   - Notification Bell
   - Save Changes Button (Navy)

### Phase 3: Property Detail Page 📍 START HIER
1. Hero-Image-Section mit Overlay
2. Floating Status-Card
3. Tab-Navigation (Gold Underline)
4. **Times & Prices Card**:
   - Gold-Icon-Header
   - Time-Picker Inputs
   - Currency Dropdown
   - Price Input
5. **Amenities Card**:
   - Gold-Icon-Header
   - Selected Counter
   - 3-Spalten-Grid
   - Gold-Checkboxen

### Phase 4: Weitere Komponenten
- [ ] Dashboard
- [ ] Properties List
- [ ] Bookings
- [ ] Calendar
- [ ] etc.

---

## Komponenten-Bibliothek (Neu)

### Buttons
```tsx
// Primary (Navy)
<button className="bg-luxe-navy text-white px-6 py-2 rounded-md">
  Save Changes
</button>

// Secondary (Outline)
<button className="border-2 border-luxe-gray text-luxe-gray px-6 py-2 rounded-md">
  Cancel
</button>

// Gold Accent
<button className="bg-luxe-gold text-white px-6 py-2 rounded-md">
  Highlight
</button>
```

### Cards
```tsx
<div className="bg-white rounded-lg shadow-md p-6">
  {/* Gold-Icon + Title */}
  <div className="flex items-center gap-2 mb-4">
    <ClockIcon className="w-5 h-5 text-luxe-gold" />
    <h3 className="text-lg font-semibold">Times & Prices</h3>
  </div>
  {/* Content */}
</div>
```

### Checkboxen (Gold)
```tsx
<label className="flex items-center gap-2 cursor-pointer">
  <input 
    type="checkbox" 
    className="w-5 h-5 text-luxe-gold rounded border-gray-300"
  />
  <span>Wifi</span>
</label>
```

### Toggle-Switch (Gold/Green)
```tsx
<div className="flex items-center gap-2">
  <Switch className="bg-luxe-gold" checked={true} />
  <span className="text-green-500 flex items-center gap-1">
    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
    Live
  </span>
</div>
```

---

## Tailwind Config

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        luxe: {
          navy: '#0F1F3A',
          gray: '#7A7D85',
          gold: '#C9A24D',
          cream: '#F2EFEA',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    }
  }
}
```

---

## Nächste Schritte

1. ✅ Analyse abgeschlossen
2. 🔄 Tailwind Config aktualisieren
3. 🔄 AdminShell neu bauen (Sidebar)
4. 🔄 Property Detail Hero-Section
5. 🔄 Times & Prices Card
6. 🔄 Amenities Card

