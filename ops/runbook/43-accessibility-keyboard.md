# 43 - Accessibility: Keyboard & ARIA (K1, K2, K4, K5)

## Übersicht

Accessibility-Patterns für Admin-UI:
- **K1**: WCAG 1.3.1 "Info and Relationships" - htmlFor Label-Input-Verknüpfung
- **K2**: WCAG 2.1.2 "No Keyboard Trap" - FocusTrap für Modals
- **K4**: WCAG 4.1.2 "Name, Role, Value" - aria-label für Icon Buttons
- **K5**: WCAG 3.3.1 "Error Identification" - aria-describedby für Formularfehler

---

## K1: Label-Input-Verknüpfung (htmlFor)

### Übersicht

Alle Formular-Labels müssen programmatisch mit ihren Eingabefeldern verknüpft sein (WCAG 1.3.1, 4.1.2).

### Pattern

```tsx
<label htmlFor="field-id" className="...">Feldname</label>
<input id="field-id" className="..." />
```

### Namenskonvention für IDs

Format: `{seite}-{feldname}`

| Seite | Beispiel-IDs |
|-------|--------------|
| bookings | `booking-property`, `booking-guest-first-name`, `booking-num-children` |
| guests | `guest-first-name`, `guest-email`, `guest-city` |
| properties | `property-name`, `property-type`, `property-max-guests` |
| properties/[id] | `property-edit-name`, `property-edit-description` |
| seasons | `season-name`, `season-start-date`, `season-priority` |
| visitor-tax | `visitor-tax-location-name`, `visitor-tax-period-start` |
| team | `team-email`, `team-role` |
| profile | `profile-first-name`, `profile-email` |
| organization | `org-name`, `org-legal-name`, `org-vat-id` |
| branding | `branding-logo`, `branding-primary-color` |
| website/seo | `seo-site-name`, `seo-title-suffix` |
| website/design | `design-primary-color`, `design-font-family` |

### Ausnahmen

**Checkbox-Labels die ihr Input umschließen brauchen KEIN htmlFor:**

```tsx
{/* OK - Label wraps input */}
<label className="flex items-center gap-2">
  <input type="checkbox" />
  Option aktivieren
</label>
```

### Betroffene Dateien (23 Dateien, ~200 Labels)

| Datei | Labels |
|-------|--------|
| `app/(admin)/bookings/page.tsx` | 12 |
| `app/(admin)/bookings/[id]/page.tsx` | 5 |
| `app/(admin)/guests/page.tsx` | 7 |
| `app/(admin)/guests/[id]/page.tsx` | 10 |
| `app/(admin)/properties/page.tsx` | 34 |
| `app/(admin)/properties/[id]/page.tsx` | 37 |
| `app/(admin)/properties/[id]/rate-plans/page.tsx` | 10 |
| `app/(admin)/seasons/page.tsx` | 13 |
| `app/(admin)/visitor-tax/page.tsx` | 18 |
| `app/(admin)/team/page.tsx` | 3 |
| `app/(admin)/extra-services/page.tsx` | 4 |
| `app/(admin)/amenities/page.tsx` | 5 |
| `app/(admin)/fees-taxes/page.tsx` | 6 |
| `app/(admin)/cancellation-rules/page.tsx` | 5 |
| `app/(admin)/connections/page.tsx` | 10 |
| `app/(admin)/profile/edit/page.tsx` | 9 |
| `app/(admin)/profile/security/page.tsx` | 3 |
| `app/(admin)/organization/page.tsx` | 13 |
| `app/(admin)/settings/branding/branding-form.tsx` | 10 |
| `app/(admin)/settings/roles/page.tsx` | 7 |
| `app/(admin)/website/domain/page.tsx` | 1 |
| `app/(admin)/website/seo/page.tsx` | 4 |
| `app/(admin)/website/design/design-form.tsx` | 22 |

### Verification

1. Browser DevTools → Elements → Label anklicken → prüfen ob Input fokussiert wird
2. Oder: `htmlFor` Attribut im Label suchen und prüfen ob `id` im Input vorhanden

### WCAG-Kriterien

- ✅ 1.3.1 Info and Relationships - Labels sind programmatisch verknüpft
- ✅ 4.1.2 Name, Role, Value - Inputs haben accessible names

## Was wurde implementiert?

### K2-Extended: FocusTrap für Inline-Modals

Alle Modals/Dialoge in der Admin-UI wurden mit `focus-trap-react` erweitert:

- **Tab-Navigation bleibt im Modal** (keine Escape nach außen)
- **ESC schließt Modal** (`escapeDeactivates: true`)
- **Klick außerhalb schließt Modal** (`clickOutsideDeactivates: true`)
- **ARIA-Attribute** für Screen Reader (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`)

### Pattern

```tsx
import FocusTrap from "focus-trap-react";

{showModal && (
  <FocusTrap focusTrapOptions={{ escapeDeactivates: true, clickOutsideDeactivates: true }}>
    <div className="fixed inset-0 ..." role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <h2 id="modal-title">...</h2>
      {/* Modal content */}
    </div>
  </FocusTrap>
)}
```

### Drawer-Pattern (Slide-in Panels)

Für Drawers mit separatem Backdrop:

```tsx
<FocusTrap focusTrapOptions={{ escapeDeactivates: true, clickOutsideDeactivates: true }}>
  <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
    {/* Backdrop - aria-hidden weil nicht interaktiv für Screen Reader */}
    <div className="absolute inset-0 bg-black/30" aria-hidden="true" onClick={onClose} />
    {/* Drawer Panel */}
    <div className="fixed z-50 ...">
      <h2 id="drawer-title">...</h2>
    </div>
  </div>
</FocusTrap>
```

## Betroffene Dateien

| Datei | Modals |
|-------|--------|
| `app/(admin)/properties/[id]/rate-plans/page.tsx` | 7 (Import, Season, Archive, Restore, Delete, Bulk Delete, Confirm) |
| `app/(admin)/seasons/page.tsx` | 7 (Template, Period, Archive, Restore, Delete, Delete Period, Bulk Delete) |
| `app/(admin)/visitor-tax/page.tsx` | 7 (Location, Period, Archive, Restore, Delete, Delete Period, Bulk Delete) |
| `app/(admin)/connections/page.tsx` | 5 (Connection Details, Log Details, Batch Detail, New Connection, Assign Property) |
| `app/(admin)/channel-sync/page.tsx` | 4 (Detail Drawer, Purge Modal, Connection Selector, Batch Details) |
| `app/(admin)/booking-requests/page.tsx` | 4 (Detail Drawer, Accept, Reject, Notes Edit) |
| `app/(admin)/website/pages/page.tsx` | 1 (New Page Modal) |
| `app/(admin)/website/templates/page.tsx` | 1 (Create/Edit Template Modal) |
| `app/(admin)/website/components/RichTextEditor.tsx` | 1 (Link Dialog) |
| `app/(admin)/website/pages/[id]/page.tsx` | 4 (Block Picker, Settings, Save Template, Shortcuts) |
| `app/(admin)/properties/[id]/media/page.tsx` | 2 (Upload Modal, Lightbox) |
| `app/(admin)/properties/[id]/gebuehren/page.tsx` | 2 (Add Fee, Delete Confirmation) |
| `app/(admin)/fees-taxes/page.tsx` | 3 (Delete, FeeTemplateForm, TaxForm) |

**Total: 48 Modals in 13 Dateien**

## Abhängigkeit

```bash
npm install focus-trap-react
```

Bereits im Projekt vorhanden (package.json).

## Verification

### Manuelle Prüfung

1. Modal öffnen (z.B. "Neuen Tarifplan importieren" in Rate Plans)
2. Tab-Taste drücken → Focus bleibt im Modal
3. ESC drücken → Modal schließt
4. Außerhalb klicken → Modal schließt

### WCAG 2.1.2 Kriterien

- ✅ Keyboard-Fokus kann jederzeit aus dem Modal navigiert werden (ESC)
- ✅ Keine Tastatur-Falle
- ✅ Screen Reader erkennt Modal-Kontext

## Commits

```
a11y(K2-Extended): add FocusTrap to rate-plans modals
a11y(K2-Extended): add FocusTrap to seasons page modals
a11y(K2-Extended): add FocusTrap to visitor-tax page modals
a11y(K2-Extended): add FocusTrap to connections page modals
a11y(K2-Extended): add FocusTrap to channel-sync page modals
a11y(K2-Extended): add FocusTrap to booking-requests modals
a11y(K2-Extended): add FocusTrap to website pages modals
a11y(K2-Extended): add FocusTrap to fees-taxes modals
```

## Troubleshooting

### Modal schließt nicht mit ESC

- Prüfen ob `escapeDeactivates: true` gesetzt ist
- Prüfen ob onClose-Handler korrekt implementiert

### Focus springt raus

- FocusTrap muss direkt um das Modal-Element wrappen
- Bei Fragment `<>` → durch Container `<div>` ersetzen

### Screen Reader liest Modal nicht korrekt

- `role="dialog"` und `aria-modal="true"` prüfen
- `aria-labelledby` mit korrekter ID zum Titel verknüpfen

---

## K4: Icon Button Labels

### Übersicht

Alle Icon-only Buttons benötigen `aria-label` damit Screen Reader die Funktion beschreiben können.

### Pattern

```tsx
<button aria-label="Schließen" className="...">
  <X className="w-5 h-5" />
</button>

<button aria-label="Menü öffnen" className="...">
  <MoreVertical className="w-5 h-5" />
</button>
```

### Betroffene Button-Typen

| Button | aria-label |
|--------|------------|
| Close (X) | "Schließen" |
| MoreVertical | "Menü öffnen" |
| Toast dismiss | "Benachrichtigung schließen" |
| Clear input | "Eingabe löschen" / "Gast entfernen" |
| Eye/EyeOff | "Passwort anzeigen/verbergen" |

### Verification

1. Browser DevTools → Elements → nach `aria-label` suchen
2. Screen Reader aktivieren und durch Buttons navigieren

---

## K5: Form Validation Error Links

### Übersicht

Formular-Validierungsfehler müssen programmatisch mit den zugehörigen Eingabefeldern verknüpft sein (WCAG 3.3.1).

### Pattern

```tsx
<label htmlFor="field-id">Feldname *</label>
<input
  id="field-id"
  aria-invalid={!!errors.field}
  aria-describedby={errors.field ? "field-id-error" : undefined}
  className={errors.field ? "border-state-error" : "border-stroke-default"}
/>
{errors.field && (
  <p id="field-id-error" role="alert" className="text-state-error">
    {errors.field}
  </p>
)}
```

### Attribute

| Attribut | Zweck |
|----------|-------|
| `id` | Eindeutige ID für Label-Verknüpfung |
| `aria-invalid` | Zeigt ungültigen Zustand an |
| `aria-describedby` | Verknüpft Fehlermeldung mit Input |
| `role="alert"` | Screen Reader liest Fehler sofort vor |

### Betroffene Dateien

| Datei | Felder mit Validierung |
|-------|------------------------|
| `bookings/page.tsx` | property_id, check_in, check_out, num_adults |
| `website/templates/page.tsx` | name, block_type, block_props, style_overrides |
| `channel-sync/page.tsx` | connection_id, start_date, end_date |

### Verification

1. Formular mit leeren Pflichtfeldern absenden
2. Fehler erscheint unter dem Feld
3. Mit Screen Reader: Fokus auf Input → Fehler wird vorgelesen
