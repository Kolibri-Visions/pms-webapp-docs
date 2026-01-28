# Phase 3: Property Detail Page - LuxeStay Redesign

## Übersicht

Diese Anleitung zeigt, wie die Property Detail Page mit den LuxeStay-Komponenten umgestaltet wird.

**Demo-Datei**: `docs/design/luxe_property_detail_demo.tsx`

---

## ✅ Umgesetzte Features

### 1. **Hero Section** (Phase 3.1)

```tsx
<Card variant="elevated">
  <div className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-6">
    {/* Cover Image mit Gold-Badge */}
    <div className="relative bg-luxe-cream rounded-lg">
      <img src={coverImageUrl} alt={property.name} />
      <div className="absolute top-3 right-3 bg-luxe-gold text-white px-3 py-1 rounded-full">
        Premium
      </div>
    </div>

    {/* Property Summary */}
    <div>
      <h1 className="text-3xl font-bold text-luxe-navy">{property.name}</h1>

      {/* Key Facts - 3 columns mit Gold-Icons */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <Users className="w-4 h-4 text-luxe-gold" />
          <div className="text-2xl font-bold text-luxe-navy">{max_guests}</div>
        </div>
        {/* ... */}
      </div>
    </div>
  </div>
</Card>
```

**Design-Merkmale**:
- ✨ Gold-Badge "Premium" overlay auf Cover Image
- ✨ 3-Spalten Key Facts mit Gold-Icons (Users, Bed, MapPin)
- ✨ Cream-Background für Adress-Section
- ✨ Action Buttons: Gold (primary), Secondary, Ghost

---

### 2. **Times & Prices Card** (Phase 3.2)

```tsx
<Card icon={Clock} title="Zeiten & Preise">
  <div className="grid grid-cols-2 gap-4">
    <Input
      label="Check-in Zeit"
      type="time"
      defaultValue={property.check_in_time}
    />
    <Input
      label="Check-out Zeit"
      type="time"
      defaultValue={property.check_out_time}
    />
    <Input
      label="Basispreis / Nacht"
      type="number"
      defaultValue={property.base_price}
      hint={`in ${property.currency}`}
    />
    {/* ... */}
  </div>

  <div className="mt-6 flex justify-end">
    <Button variant="primary">Änderungen speichern</Button>
  </div>
</Card>
```

**Design-Merkmale**:
- ✨ Gold Clock-Icon im Card-Header
- ✨ 2-Spalten Grid für Input-Felder
- ✨ LuxeStay Input mit Gold-Focus-Ring
- ✨ Navy Primary Button zum Speichern

---

### 3. **Amenities Card mit Gold-Checkboxen** (Phase 3.3)

```tsx
<Card
  icon={Sparkles}
  title="Ausstattung"
  headerAction={
    <span className="text-sm font-medium text-luxe-gray">
      Ausgewählt: <span className="text-luxe-gold">{count}</span>
    </span>
  }
  variant="elevated"
>
  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
    {amenities.map((amenity) => (
      <label
        className={`flex items-center gap-3 p-3 rounded-lg border-2 ${
          isSelected
            ? "border-luxe-gold bg-luxe-gold/5"
            : "border-luxe-cream-dark hover:border-luxe-gray-light"
        }`}
      >
        <input
          type="checkbox"
          className="w-5 h-5 text-luxe-gold rounded focus:ring-luxe-gold"
        />
        <div className="flex items-center gap-2">
          <span className="text-lg">{amenity.icon}</span>
          <span className="text-sm font-medium">{amenity.label}</span>
        </div>
      </label>
    ))}
  </div>

  <div className="mt-6 flex justify-end gap-2">
    <Button variant="secondary">Abbrechen</Button>
    <Button variant="gold">{count} Ausstattungen speichern</Button>
  </div>
</Card>
```

**Design-Merkmale**:
- ✨ Gold Sparkles-Icon im Header
- ✨ Counter im Header: "Ausgewählt: **8**" (Gold-Zahl)
- ✨ 4-Spalten responsives Grid
- ✨ **Gold-Border** bei ausgewählten Items
- ✨ **Gold-Checkboxen** mit focus:ring-luxe-gold
- ✨ Emoji-Icons für jede Ausstattung
- ✨ Gold "Speichern"-Button mit Counter

---

## 🎨 Verwendete Farben

### Navy (Primary)
- Titel: `text-luxe-navy`
- Text: `text-luxe-navy`

### Gold (Accent)
- Icons: `text-luxe-gold`
- Borders (selected): `border-luxe-gold`
- Buttons: `variant="gold"`
- Checkboxes: `text-luxe-gold`

### Cream (Background)
- Cards: `bg-luxe-cream` (innerhalb von Karten)
- Borders: `border-luxe-cream-dark`

### Gray (Secondary)
- Muted text: `text-luxe-gray`
- Borders: `border-luxe-gray-light`

---

## 📦 Komponenten-Imports

```tsx
import { Card, Input, Button } from "@/app/components/luxe";
import { Clock, Sparkles, MapPin, Bed, Users, Home } from "lucide-react";
```

---

## 🔄 Integration in bestehende Seite

Um die LuxeStay-Komponenten in die bestehende `frontend/app/properties/[id]/page.tsx` zu integrieren:

1. **Imports hinzufügen**:
   ```tsx
   import { Card, Input, Button } from "@/app/components/luxe";
   import { Clock, Sparkles, /* ... */ } from "lucide-react";
   ```

2. **Alte div-Karten ersetzen**:
   ```tsx
   // Alt (beige theme):
   <div className="bg-bo-surface rounded-bo-xl border border-bo-border p-6">
     <h2 className="text-xl font-heading">💰 Zeiten & Preise</h2>
     {/* ... */}
   </div>

   // Neu (LuxeStay):
   <Card icon={Clock} title="Zeiten & Preise">
     {/* ... */}
   </Card>
   ```

3. **Input-Felder konvertieren**:
   ```tsx
   // Alt:
   <input
     type="time"
     className="w-full h-10 px-3 border border-gray-300 rounded"
   />

   // Neu:
   <Input
     label="Check-in Zeit"
     type="time"
     defaultValue={property.check_in_time}
   />
   ```

4. **Buttons konvertieren**:
   ```tsx
   // Alt:
   <button className="px-4 py-2 bg-indigo-600 text-white rounded-lg">
     Speichern
   </button>

   // Neu:
   <Button variant="primary">Speichern</Button>
   <Button variant="gold">Upgrade</Button>
   <Button variant="secondary">Abbrechen</Button>
   ```

---

## 📱 Responsive Layout

Die Demo verwendet ein **2-Spalten-Grid** für Desktop, 1-Spalte für Mobile:

```tsx
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <Card>...</Card>
  <Card>...</Card>
</div>
```

Die **Amenities Card** ist immer **Full-Width** (`lg:grid-cols-4` intern):

```tsx
<Card variant="elevated">
  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
    {/* ... */}
  </div>
</Card>
```

---

## ✅ Checkliste für vollständige Integration

- [ ] `frontend/app/properties/[id]/page.tsx` öffnen
- [ ] LuxeStay-Komponenten importieren
- [ ] Hero Section mit Cover Image & Gold-Badge
- [ ] Objektinformationen-Card mit Icon
- [ ] Adresse-Card mit MapPin-Icon
- [ ] Kapazität-Card mit Bed-Icon
- [ ] **Zeiten & Preise Card** mit Clock-Icon + Input-Feldern ✅
- [ ] **Ausstattung Card** mit Sparkles-Icon + Gold-Checkboxen ✅
- [ ] Alle Action-Buttons (Bearbeiten, Löschen) mit LuxeStay Button
- [ ] Bestehende `bg-bo-*` und `text-bo-*` durch `luxe-*` ersetzen

---

## 🎯 Nächste Schritte

1. **Demo testen**: Demo-Komponente in Storybook/isolierter Page testen
2. **Schrittweise Integration**: Einen Card-Typ nach dem anderen migrieren
3. **Feedback einholen**: Design mit Stakeholder reviewen
4. **Vollständige Migration**: Alle Property-Seiten auf LuxeStay umstellen

---

## 📸 Screenshots

(Hier Screenshots der Demo einfügen, wenn deployed)

- Hero Section mit Gold-Badge
- Times & Prices Card mit Input-Grid
- Amenities Card mit Gold-Checkboxen

---

**Status**: ✅ Phase 3 Demo abgeschlossen
**Nächste Phase**: Integration in Production-Code
