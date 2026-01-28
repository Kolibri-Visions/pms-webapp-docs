# LuxeStay Design System - Quick Start

## 🚀 In 5 Minuten starten

### 1. Komponenten importieren

```tsx
import { Button, Card, Input } from "@/app/components/luxe";
import { Clock, Sparkles, Users } from "lucide-react";
```

### 2. Card mit Gold-Icon

```tsx
<Card icon={Clock} title="Zeiten & Preise">
  <p>Ihr Content hier...</p>
</Card>
```

### 3. Input-Feld mit Gold-Focus

```tsx
<Input
  label="Check-in Zeit"
  type="time"
  defaultValue="15:00"
  hint="Format: HH:MM"
/>
```

### 4. Buttons

```tsx
<Button variant="primary">Speichern</Button>    {/* Navy */}
<Button variant="gold">Upgrade</Button>         {/* Gold */}
<Button variant="secondary">Abbrechen</Button>  {/* Outline */}
```

---

## 🎨 Farben - Copy & Paste

### Text
```tsx
text-luxe-navy        // #0F1F3A - Haupttext
text-luxe-gold        // #C9A24D - Akzente/Icons
text-luxe-gray        // #7A7D85 - Muted Text
text-white            // Weiß auf Navy
```

### Background
```tsx
bg-luxe-navy          // #0F1F3A - Sidebar
bg-luxe-cream         // #F2EFEA - Haupthintergrund
bg-luxe-gold          // #C9A24D - Buttons/Badges
bg-white              // Cards
```

### Borders
```tsx
border-luxe-gold              // Gold
border-luxe-cream-dark        // #e8e3dc - Subtle
border-luxe-navy-light        // #1a2f4d - Sidebar Divider
```

### Shadows
```tsx
shadow-luxe       // 0 1px 3px - Subtle
shadow-luxe-md    // 0 4px 6px - Cards
shadow-luxe-lg    // 0 10px 15px - Elevated
```

---

## 📦 Häufige Patterns

### 2-Spalten Input-Grid
```tsx
<div className="grid grid-cols-2 gap-4">
  <Input label="Vorname" />
  <Input label="Nachname" />
</div>
```

### Card mit Actions
```tsx
<Card icon={Users} title="Team">
  {/* Content */}
  <div className="mt-6 flex justify-end gap-2">
    <Button variant="secondary">Abbrechen</Button>
    <Button variant="primary">Speichern</Button>
  </div>
</Card>
```

### Gold-Checkbox
```tsx
<input
  type="checkbox"
  className="w-5 h-5 text-luxe-gold rounded border-luxe-gray
             focus:ring-luxe-gold focus:ring-2"
/>
```

### Badge (Gold)
```tsx
<div className="absolute top-3 right-3 bg-luxe-gold text-white
                px-3 py-1 rounded-full text-xs font-semibold shadow-luxe-md">
  Premium
</div>
```

### Hero Key Facts (3 Spalten)
```tsx
<div className="grid grid-cols-3 gap-4">
  <div>
    <div className="flex items-center gap-2 text-luxe-gold mb-1">
      <Users className="w-4 h-4" />
      <span className="text-xs font-semibold uppercase tracking-wide">
        Gäste
      </span>
    </div>
    <div className="text-2xl font-bold text-luxe-navy">8</div>
  </div>
  {/* 2 weitere Spalten */}
</div>
```

---

## 📱 Responsive Grid

### 1 → 2 Spalten
```tsx
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <Card>...</Card>
  <Card>...</Card>
</div>
```

### 2 → 3 → 4 Spalten (Amenities)
```tsx
<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
  {items.map(item => <div key={item.id}>...</div>)}
</div>
```

### Image | Content (Hero)
```tsx
<div className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-6">
  <div>{/* Image 400px */}</div>
  <div>{/* Content fills rest */}</div>
</div>
```

---

## 🎯 Icon-Guide

**Gold Icons** (wichtige Features):
```tsx
<Clock className="w-5 h-5 text-luxe-gold" />
<Sparkles className="w-5 h-5 text-luxe-gold" />
<Users className="w-4 h-4 text-luxe-gold" />
```

**Navy Icons** (neutral):
```tsx
<Home className="w-5 h-5 text-luxe-navy" />
```

**Gray Icons** (muted):
```tsx
<Settings className="w-4 h-4 text-luxe-gray" />
```

---

## 🔧 Troubleshooting

### Farben werden nicht angezeigt?
1. Tailwind Config prüfen: `luxe-*` Farben definiert?
2. CSS neu kompilieren: `npm run dev` neustarten
3. Cache leeren: `rm -rf .next`

### Komponenten nicht gefunden?
```bash
# Prüfen ob Datei existiert:
ls frontend/app/components/luxe/

# Sollte enthalten:
# Button.tsx  Card.tsx  Input.tsx  index.ts
```

### TypeScript Fehler?
```tsx
// Props explizit typen:
import { ButtonProps, CardProps, InputProps } from "@/app/components/luxe";
```

---

## 📚 Weitere Ressourcen

- **Komponenten-Guide**: `docs/design/luxe_components_guide.md`
- **Phase 3 Demo**: `docs/design/luxe_property_detail_demo.tsx`
- **Integration-Anleitung**: `docs/design/phase3_implementation_guide.md`
- **Vollständige Zusammenfassung**: `docs/design/luxestay_redesign_summary.md`

---

## ⚡ Pro-Tipps

### 1. Konsistente Abstände
```tsx
<div className="space-y-6">        {/* 24px vertical */}
<div className="gap-4">            {/* 16px grid */}
<div className="p-6">              {/* 24px padding */}
```

### 2. Text-Hierarchie
```tsx
<h1 className="text-3xl font-bold text-luxe-navy">   {/* Page Title */}
<h2 className="text-xl font-semibold text-luxe-navy"> {/* Card Title */}
<p className="text-sm text-luxe-gray">                {/* Muted Text */}
```

### 3. Transitions
```tsx
className="transition-all duration-150"  // Schnell
className="transition-colors"            // Nur Farben
```

### 4. Hover States
```tsx
hover:bg-luxe-cream           // Subtle
hover:bg-luxe-gold-light      // Gold Button
hover:border-luxe-gold        // Gold Border
```

### 5. Focus Rings (Accessibility)
```tsx
focus:ring-2 focus:ring-luxe-gold focus:outline-none
```

---

**Happy Coding! ✨**

*LuxeStay Design System - Premium Navy/Gold für PMS Admin UI*
