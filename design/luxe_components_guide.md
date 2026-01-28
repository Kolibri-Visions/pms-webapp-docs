# LuxeStay Component Library - Usage Guide

## Overview

Premium Navy/Gold design system components for LuxeStay Admin UI.

## Installation

Components are located in `frontend/app/components/luxe/`

```tsx
import { Button, Card, Input } from "@/app/components/luxe";
```

---

## Components

### Button

Navy-primary button with multiple variants.

**Props:**
- `variant`: "primary" | "secondary" | "gold" | "ghost" | "danger"
- `size`: "sm" | "md" | "lg"
- `isLoading`: boolean

**Examples:**

```tsx
// Primary (Navy) - Main CTAs
<Button variant="primary">Save Changes</Button>

// Secondary (Outline) - Cancel actions
<Button variant="secondary">Cancel</Button>

// Gold (Accent) - Special highlights
<Button variant="gold">Upgrade</Button>

// Ghost (Transparent) - Subtle actions
<Button variant="ghost">Learn More</Button>

// Danger (Red) - Destructive actions
<Button variant="danger">Delete</Button>

// With loading state
<Button isLoading>Saving...</Button>

// Small size
<Button size="sm">Small Button</Button>
```

---

### Card

White card with optional gold icon header.

**Props:**
- `icon`: LucideIcon component
- `title`: string
- `headerAction`: ReactNode (e.g., counter, button)
- `variant`: "default" | "elevated" | "flat"

**Examples:**

```tsx
import { Clock, Wifi } from "lucide-react";

// With gold icon + title
<Card icon={Clock} title="Times & Prices">
  {/* Content */}
</Card>

// With header action (counter)
<Card 
  icon={Wifi} 
  title="Amenities"
  headerAction={<span>Selected: 8</span>}
>
  {/* Amenities grid */}
</Card>

// Elevated variant (more shadow)
<Card variant="elevated" title="Important Info">
  {/* Content */}
</Card>

// Flat variant (border instead of shadow)
<Card variant="flat">
  {/* Content */}
</Card>
```

---

### Input

Clean input with gold focus ring.

**Props:**
- `label`: string
- `error`: string
- `hint`: string
- All standard input props

**Examples:**

```tsx
// Basic input with label
<Input 
  label="Property Name" 
  placeholder="Enter property name"
/>

// With hint text
<Input 
  label="Check-in Time"
  hint="Format: HH:MM AM/PM"
  type="time"
/>

// With error state
<Input 
  label="Email"
  error="Invalid email format"
  value={email}
/>

// Disabled
<Input 
  label="Property ID"
  value="550e8400-e29b-41d4-a716-446655440000"
  disabled
/>
```

---

## Color Tokens

Use these Tailwind classes for custom components:

### Navy (Primary)
- `bg-luxe-navy` - #0F1F3A
- `bg-luxe-navy-light` - #1a2f4d
- `bg-luxe-navy-dark` - #0a1628
- `text-luxe-navy`
- `border-luxe-navy`

### Gray (Secondary)
- `bg-luxe-gray` - #7A7D85
- `bg-luxe-gray-light` - #9fa1a8
- `bg-luxe-gray-dark` - #5c5e63
- `text-luxe-gray`

### Gold (Accent)
- `bg-luxe-gold` - #C9A24D
- `bg-luxe-gold-light` - #d4b470
- `bg-luxe-gold-dark` - #b38f3a
- `text-luxe-gold` - Most common for icons!

### Cream (Background)
- `bg-luxe-cream` - #F2EFEA
- `bg-luxe-cream-light` - #f7f5f2
- `bg-luxe-cream-dark` - #e8e3dc

---

## Shadows

- `shadow-luxe` - 0 1px 3px rgba(0,0,0,0.12)
- `shadow-luxe-md` - 0 4px 6px rgba(0,0,0,0.1)
- `shadow-luxe-lg` - 0 10px 15px rgba(0,0,0,0.1)

---

## Example: Property Times & Prices Card

```tsx
import { Card, Input } from "@/app/components/luxe";
import { Clock } from "lucide-react";

function TimesAndPricesCard() {
  return (
    <Card icon={Clock} title="Times & Prices">
      <div className="grid grid-cols-2 gap-4">
        <Input 
          label="Check-in Time"
          type="time"
          defaultValue="15:00"
        />
        <Input 
          label="Check-out Time"
          type="time"
          defaultValue="11:00"
        />
        <Input 
          label="Currency"
          type="select"
          defaultValue="USD"
        />
        <Input 
          label="Base Price / Night"
          type="number"
          placeholder="450"
        />
      </div>
    </Card>
  );
}
```

---

## Example: Amenities Card with Checkboxes

```tsx
import { Card } from "@/app/components/luxe";
import { Wifi } from "lucide-react";

function AmenitiesCard() {
  const amenities = [
    { id: "wifi", label: "Wifi", checked: true },
    { id: "pool", label: "Pool", checked: true },
    { id: "kitchen", label: "Kitchen", checked: true },
    { id: "gym", label: "Gym", checked: false },
    // ...
  ];
  
  const selectedCount = amenities.filter(a => a.checked).length;
  
  return (
    <Card 
      icon={Wifi} 
      title="Amenities"
      headerAction={<span>Selected: {selectedCount}</span>}
    >
      <div className="grid grid-cols-3 gap-4">
        {amenities.map((amenity) => (
          <label key={amenity.id} className="flex items-center gap-2 cursor-pointer">
            <input 
              type="checkbox" 
              checked={amenity.checked}
              className="w-5 h-5 text-luxe-gold rounded border-gray-300 
                         focus:ring-luxe-gold focus:ring-2"
            />
            <span className="text-sm text-luxe-navy">{amenity.label}</span>
          </label>
        ))}
      </div>
    </Card>
  );
}
```

---

## Next Steps

Phase 2: AdminShell Sidebar with Navy/Gold theme
Phase 3: Property Detail Page implementation

