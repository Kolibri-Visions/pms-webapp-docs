# 43 - Accessibility: Keyboard Navigation (K2)

## Übersicht

WCAG 2.1.2 "No Keyboard Trap" Compliance für alle Admin-Modals durch FocusTrap-Implementierung.

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
