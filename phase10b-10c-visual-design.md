# Phase 10B/10C: Visuelles Design-System & White-Label-UX

**Status:** Draft
**Version:** 1.0
**Erstellt:** 2025-12-22
**Projekt:** PMS-Webapp
**Basis:** Phase 10A (UI/UX & Design System - Konzeption)

---

## Executive Summary

### Ziel
**Vollständiges visuelles Design-System** mit konkreten Werten (Farben, Typografie, Komponenten-Styles) und **White-Label-Theming-Strategie** für PMS-Webapp MVP.

### Scope
- ✅ **Phase 10B:** Farb-System, Typografie, Komponenten-Styling, Layout
- ✅ **Phase 10C:** White-Label-Theming, Deutsche UI-Texte, Rollen-spezifische UX

### Leitplanken
- ⚠️ **Basis:** Alle Spacing/Typography Scales aus Phase 10A (READ-ONLY)
- ⚠️ **Token-basiert:** CSS Variables für White-Label-Flexibilität
- ⚠️ **Deutsche UI:** Alle Labels, Buttons, Meldungen auf Deutsch
- ⚠️ **B2B-Fokus:** Professionell, ruhig, KEIN Marketing-Design

### Design-Philosophie
**Modern. Leicht. Professionell. Effizient.**

- **Modern:** Zeitgemäße UI-Patterns, aktuelle Best Practices
- **Leicht:** Viel Weißraum, klare Hierarchie, keine visuellen Ablenkungen
- **Professionell:** B2B-Software für täglichen Einsatz, keine spielerischen Elemente
- **Effizient:** Schnelles Erfassen von Informationen, intuitive Bedienung

---

## 1. Farb-System (Phase 10B)

### 1.1 Brand Colors

**Primärfarbe (Primary):**
- Verwendung: Hauptaktionen, Links, aktive Navigation
- Farbe: **Blau** (vertrauenswürdig, professionell, neutral)

| Token | Value | Use Case |
|-------|-------|----------|
| `--color-primary-50` | `#EFF6FF` | Sehr helle Hintergründe |
| `--color-primary-100` | `#DBEAFE` | Helle Hintergründe, Hover-States |
| `--color-primary-200` | `#BFDBFE` | Subtile Akzente |
| `--color-primary-300` | `#93C5FD` | Sekundäre UI-Elemente |
| `--color-primary-400` | `#60A5FA` | Interaktive Elemente (Hover) |
| `--color-primary-500` | `#3B82F6` | **Haupt-Primary (Standard)** |
| `--color-primary-600` | `#2563EB` | Primary Buttons (Default) |
| `--color-primary-700` | `#1D4ED8` | Primary Buttons (Hover) |
| `--color-primary-800` | `#1E40AF` | Primary Buttons (Active) |
| `--color-primary-900` | `#1E3A8A` | Dunkle Akzente |

**Sekundärfarbe (Secondary):**
- Verwendung: Akzente, wichtige sekundäre Actions
- Farbe: **Indigo** (ergänzt Primary, modern)

| Token | Value | Use Case |
|-------|-------|----------|
| `--color-secondary-50` | `#EEF2FF` | Sehr helle Hintergründe |
| `--color-secondary-100` | `#E0E7FF` | Helle Hintergründe |
| `--color-secondary-200` | `#C7D2FE` | Subtile Akzente |
| `--color-secondary-300` | `#A5B4FC` | Sekundäre UI-Elemente |
| `--color-secondary-400` | `#818CF8` | Interaktive Elemente |
| `--color-secondary-500` | `#6366F1` | **Haupt-Secondary** |
| `--color-secondary-600` | `#4F46E5` | Secondary Buttons |
| `--color-secondary-700` | `#4338CA` | Secondary Buttons (Hover) |
| `--color-secondary-800` | `#3730A3` | Secondary Buttons (Active) |
| `--color-secondary-900` | `#312E81` | Dunkle Akzente |

**Akzentfarbe (Accent):**
- Verwendung: Highlights, Tooltips, neue Features
- Farbe: **Cyan** (frisch, modern, nicht aufdringlich)

| Token | Value | Use Case |
|-------|-------|----------|
| `--color-accent-50` | `#ECFEFF` | Sehr helle Hintergründe |
| `--color-accent-100` | `#CFFAFE` | Helle Hintergründe |
| `--color-accent-200` | `#A5F3FC` | Subtile Akzente |
| `--color-accent-300` | `#67E8F9` | Highlights |
| `--color-accent-400` | `#22D3EE` | Interaktive Elemente |
| `--color-accent-500` | `#06B6D4` | **Haupt-Accent** |
| `--color-accent-600` | `#0891B2` | Accent Buttons |
| `--color-accent-700` | `#0E7490` | Accent Buttons (Hover) |
| `--color-accent-800` | `#155E75` | Accent Buttons (Active) |
| `--color-accent-900` | `#164E63` | Dunkle Akzente |

---

### 1.2 Neutral Colors (Graustufen)

**Grau-Palette:**
- Verwendung: Text, Borders, Hintergründe, Schatten

| Token | Value | Use Case |
|-------|-------|----------|
| `--color-neutral-50` | `#F9FAFB` | Page Background (sehr hell) |
| `--color-neutral-100` | `#F3F4F6` | Card Background (hell) |
| `--color-neutral-200` | `#E5E7EB` | Borders (hell), Dividers |
| `--color-neutral-300` | `#D1D5DB` | Borders (normal), Disabled Text |
| `--color-neutral-400` | `#9CA3AF` | Placeholder Text |
| `--color-neutral-500` | `#6B7280` | Secondary Text |
| `--color-neutral-600` | `#4B5563` | Primary Text (leicht abgeschwächt) |
| `--color-neutral-700` | `#374151` | **Primary Text (Standard)** |
| `--color-neutral-800` | `#1F2937` | Headings (dunkel) |
| `--color-neutral-900` | `#111827` | Headings (sehr dunkel), Icons |

**Weiß & Schwarz:**
- `--color-white` | `#FFFFFF` | Hintergründe, Text auf dunklen Flächen
- `--color-black` | `#000000` | Overlays (mit Transparenz)

---

### 1.3 Semantic Colors

**Success (Erfolg):**
- Verwendung: Bestätigungen, erfolgreiche Actions, positive Status

| Token | Value | Use Case |
|-------|-------|----------|
| `--color-success-50` | `#F0FDF4` | Helle Hintergründe |
| `--color-success-100` | `#DCFCE7` | Success Messages (Background) |
| `--color-success-200` | `#BBF7D0` | Subtile Akzente |
| `--color-success-300` | `#86EFAC` | Highlights |
| `--color-success-400` | `#4ADE80` | Interaktive Elemente |
| `--color-success-500` | `#22C55E` | **Haupt-Success** |
| `--color-success-600` | `#16A34A` | Success Buttons, Status Badges |
| `--color-success-700` | `#15803D` | Success Buttons (Hover) |
| `--color-success-800` | `#166534` | Success Buttons (Active) |
| `--color-success-900` | `#14532D` | Dunkle Akzente |

**Warning (Warnung):**
- Verwendung: Warnungen, zeitkritische Actions, wichtige Hinweise

| Token | Value | Use Case |
|-------|-------|----------|
| `--color-warning-50` | `#FFFBEB` | Helle Hintergründe |
| `--color-warning-100` | `#FEF3C7` | Warning Messages (Background) |
| `--color-warning-200` | `#FDE68A` | Subtile Akzente |
| `--color-warning-300` | `#FCD34D` | Highlights |
| `--color-warning-400` | `#FBBF24` | Interaktive Elemente |
| `--color-warning-500` | `#F59E0B` | **Haupt-Warning** |
| `--color-warning-600` | `#D97706` | Warning Buttons, Status Badges |
| `--color-warning-700` | `#B45309` | Warning Buttons (Hover) |
| `--color-warning-800` | `#92400E` | Warning Buttons (Active) |
| `--color-warning-900` | `#78350F` | Dunkle Akzente |

**Error (Fehler):**
- Verwendung: Fehlermeldungen, destruktive Actions, Validierungsfehler

| Token | Value | Use Case |
|-------|-------|----------|
| `--color-error-50` | `#FEF2F2` | Helle Hintergründe |
| `--color-error-100` | `#FEE2E2` | Error Messages (Background) |
| `--color-error-200` | `#FECACA` | Subtile Akzente |
| `--color-error-300` | `#FCA5A5` | Highlights |
| `--color-error-400` | `#F87171` | Interaktive Elemente |
| `--color-error-500` | `#EF4444` | **Haupt-Error** |
| `--color-error-600` | `#DC2626` | Error Buttons, Status Badges |
| `--color-error-700` | `#B91C1C` | Error Buttons (Hover) |
| `--color-error-800` | `#991B1B` | Error Buttons (Active) |
| `--color-error-900` | `#7F1D1D` | Dunkle Akzente |

**Info (Information):**
- Verwendung: Informative Hinweise, Tooltips, Hilfetext

| Token | Value | Use Case |
|-------|-------|----------|
| `--color-info-50` | `#EFF6FF` | Helle Hintergründe |
| `--color-info-100` | `#DBEAFE` | Info Messages (Background) |
| `--color-info-200` | `#BFDBFE` | Subtile Akzente |
| `--color-info-300` | `#93C5FD` | Highlights |
| `--color-info-400` | `#60A5FA` | Interaktive Elemente |
| `--color-info-500` | `#3B82F6` | **Haupt-Info (= Primary)** |
| `--color-info-600` | `#2563EB` | Info Buttons, Status Badges |
| `--color-info-700` | `#1D4ED8` | Info Buttons (Hover) |
| `--color-info-800` | `#1E40AF` | Info Buttons (Active) |
| `--color-info-900` | `#1E3A8A` | Dunkle Akzente |

---

### 1.4 Shadow & Border Colors

**Shadows:**
| Token | Value | Use Case |
|-------|-------|----------|
| `--shadow-sm` | `0 1px 2px 0 rgba(0, 0, 0, 0.05)` | Subtile Schatten (Inputs) |
| `--shadow-md` | `0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)` | Cards, Dropdowns |
| `--shadow-lg` | `0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)` | Modals, Popovers |
| `--shadow-xl` | `0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)` | Large Modals |
| `--shadow-2xl` | `0 25px 50px -12px rgba(0, 0, 0, 0.25)` | Hero Elements |
| `--shadow-focus` | `0 0 0 3px rgba(59, 130, 246, 0.3)` | Focus Ring (Primary) |

**Border Radius:**
| Token | Value | Use Case |
|-------|-------|----------|
| `--radius-sm` | `4px` | Badges, Small Buttons |
| `--radius-md` | `6px` | Inputs, Default Buttons, Cards |
| `--radius-lg` | `8px` | Large Cards, Modals |
| `--radius-xl` | `12px` | Hero Elements |
| `--radius-full` | `9999px` | Pills, Avatar, Circular Buttons |

---

### 1.5 Dark Mode (Post-MVP)

**Hinweis:** Dark Mode ist NICHT Teil des MVP, aber das Token-System ist vorbereitet.

**Strategie:**
- Light Mode: Standard (MVP)
- Dark Mode: Post-MVP (über CSS Variables togglebar)

**Dark Mode Tokens (Beispiel):**
```css
/* Light Mode (default) */
:root {
  --color-bg-primary: var(--color-white);
  --color-bg-secondary: var(--color-neutral-50);
  --color-text-primary: var(--color-neutral-700);
  --color-text-secondary: var(--color-neutral-500);
}

/* Dark Mode (Post-MVP) */
[data-theme="dark"] {
  --color-bg-primary: var(--color-neutral-900);
  --color-bg-secondary: var(--color-neutral-800);
  --color-text-primary: var(--color-neutral-100);
  --color-text-secondary: var(--color-neutral-400);
}
```

---

## 2. Typografie-System (Phase 10B)

### 2.1 Font Family

**Primär-Font: Inter (Google Fonts)**
- **Grund:** Modern, gut lesbar, professionell, open-source
- **Fallback:** System Font Stack (für Performance)

```css
--font-family-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
  'Roboto', 'Helvetica Neue', Arial, sans-serif;

--font-family-mono: 'Fira Code', 'Consolas', 'Monaco', 'Courier New', monospace;
```

**Google Fonts Import:**
```html
<!-- In <head> -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

**Alternative (System Font Stack - kein Import):**
Falls Google Fonts NICHT gewünscht:
```css
--font-family-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI',
  'Roboto', 'Helvetica Neue', Arial, sans-serif;
```

---

### 2.2 Font Sizes & Line Heights

**Basis:** Phase 10A Typography Scale (READ-ONLY)

| Token | Size (px/rem) | Line Height | Use Case |
|-------|---------------|-------------|----------|
| `--text-xs` | `12px` / `0.75rem` | `16px` / `1.33` | Small Labels, Captions, Helper Text |
| `--text-sm` | `14px` / `0.875rem` | `20px` / `1.43` | Secondary Text, Helper Text, Table Data |
| `--text-base` | `16px` / `1rem` | `24px` / `1.5` | **Body Text (Standard)** |
| `--text-lg` | `18px` / `1.125rem` | `28px` / `1.56` | Large Body Text, Subheadings |
| `--text-xl` | `20px` / `1.25rem` | `28px` / `1.4` | Section Headings |
| `--text-2xl` | `24px` / `1.5rem` | `32px` / `1.33` | Page Headings |
| `--text-3xl` | `30px` / `1.875rem` | `36px` / `1.2` | Hero Headings |
| `--text-4xl` | `36px` / `2.25rem` | `40px` / `1.11` | Display Headings |

**CSS Variables:**
```css
:root {
  /* Font Sizes */
  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.125rem;   /* 18px */
  --text-xl: 1.25rem;    /* 20px */
  --text-2xl: 1.5rem;    /* 24px */
  --text-3xl: 1.875rem;  /* 30px */
  --text-4xl: 2.25rem;   /* 36px */

  /* Line Heights */
  --leading-xs: 1.33;
  --leading-sm: 1.43;
  --leading-base: 1.5;
  --leading-lg: 1.56;
  --leading-xl: 1.4;
  --leading-2xl: 1.33;
  --leading-3xl: 1.2;
  --leading-4xl: 1.11;
}
```

---

### 2.3 Font Weights

**Basis:** Phase 10A Typography Scale (READ-ONLY)

| Token | Value | Use Case |
|-------|-------|----------|
| `--font-normal` | `400` | Body Text, Standard Text |
| `--font-medium` | `500` | Labels, Buttons, Emphasized Text |
| `--font-semibold` | `600` | Headings, Important Text |
| `--font-bold` | `700` | Strong Emphasis, Hero Headings |

**CSS Variables:**
```css
:root {
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
}
```

---

### 2.4 Typography Application (Konkrete Beispiele)

**Page Headings (h1):**
```css
.heading-page {
  font-size: var(--text-2xl);        /* 24px */
  line-height: var(--leading-2xl);   /* 1.33 */
  font-weight: var(--font-semibold); /* 600 */
  color: var(--color-neutral-800);
}

/* Beispiel: "Eigenschaften" */
```

**Section Headings (h2):**
```css
.heading-section {
  font-size: var(--text-xl);         /* 20px */
  line-height: var(--leading-xl);    /* 1.4 */
  font-weight: var(--font-medium);   /* 500 */
  color: var(--color-neutral-700);
}

/* Beispiel: "Aktuelle Buchungen" */
```

**Subsection Headings (h3):**
```css
.heading-subsection {
  font-size: var(--text-lg);         /* 18px */
  line-height: var(--leading-lg);    /* 1.56 */
  font-weight: var(--font-medium);   /* 500 */
  color: var(--color-neutral-700);
}

/* Beispiel: "Details zur Eigenschaft" */
```

**Body Text:**
```css
.body-text {
  font-size: var(--text-base);       /* 16px */
  line-height: var(--leading-base);  /* 1.5 */
  font-weight: var(--font-normal);   /* 400 */
  color: var(--color-neutral-600);
}

/* Beispiel: Beschreibung, Paragraphen */
```

**Labels (Form, Table Headers):**
```css
.label {
  font-size: var(--text-sm);         /* 14px */
  line-height: var(--leading-sm);    /* 1.43 */
  font-weight: var(--font-medium);   /* 500 */
  color: var(--color-neutral-700);
}

/* Beispiel: "Eigenschaftsname", "Check-in-Datum" */
```

**Helper Text (Kleingedrucktes):**
```css
.helper-text {
  font-size: var(--text-xs);         /* 12px */
  line-height: var(--leading-xs);    /* 1.33 */
  font-weight: var(--font-normal);   /* 400 */
  color: var(--color-neutral-500);
}

/* Beispiel: "Pflichtfeld", "Max. 100 Zeichen" */
```

**Captions (Bildunterschriften, Timestamps):**
```css
.caption {
  font-size: var(--text-xs);         /* 12px */
  line-height: var(--leading-xs);    /* 1.33 */
  font-weight: var(--font-normal);   /* 400 */
  color: var(--color-neutral-400);
}

/* Beispiel: "Vor 2 Minuten synchronisiert" */
```

---

## 3. Komponenten-Styling (Phase 10B)

### 3.1 Buttons

**Button Variants:**

#### 3.1.1 Primary Button (Hauptaktion)

**Verwendung:** Hauptaktionen (Speichern, Bestätigen, Buchen)

**Style:**
```css
.button-primary {
  /* Größe: Medium (default) */
  height: 40px;
  padding: 0 var(--space-4); /* 0 16px */

  /* Typography */
  font-size: var(--text-base); /* 16px */
  font-weight: var(--font-medium); /* 500 */
  line-height: 1;

  /* Colors */
  background-color: var(--color-primary-600); /* #2563EB */
  color: var(--color-white);
  border: 1px solid var(--color-primary-600);

  /* Shape */
  border-radius: var(--radius-md); /* 6px */

  /* Interactivity */
  cursor: pointer;
  transition: all 150ms ease-in-out;
}

.button-primary:hover {
  background-color: var(--color-primary-700); /* #1D4ED8 */
  border-color: var(--color-primary-700);
  box-shadow: var(--shadow-sm);
}

.button-primary:active {
  background-color: var(--color-primary-800); /* #1E40AF */
  border-color: var(--color-primary-800);
  transform: scale(0.98);
}

.button-primary:disabled {
  background-color: var(--color-neutral-300);
  border-color: var(--color-neutral-300);
  color: var(--color-neutral-500);
  cursor: not-allowed;
  opacity: 0.6;
}

.button-primary:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus); /* 0 0 0 3px rgba(59, 130, 246, 0.3) */
}
```

**Beispiel:** "Speichern", "Bestätigen", "Eigenschaft anlegen"

---

#### 3.1.2 Secondary Button (Sekundäraktion)

**Verwendung:** Sekundäre Aktionen (Abbrechen, Zurück)

**Style:**
```css
.button-secondary {
  /* Größe: Medium (default) */
  height: 40px;
  padding: 0 var(--space-4); /* 0 16px */

  /* Typography */
  font-size: var(--text-base); /* 16px */
  font-weight: var(--font-medium); /* 500 */
  line-height: 1;

  /* Colors */
  background-color: transparent;
  color: var(--color-neutral-700);
  border: 1px solid var(--color-neutral-300);

  /* Shape */
  border-radius: var(--radius-md); /* 6px */

  /* Interactivity */
  cursor: pointer;
  transition: all 150ms ease-in-out;
}

.button-secondary:hover {
  background-color: var(--color-neutral-50);
  border-color: var(--color-neutral-400);
}

.button-secondary:active {
  background-color: var(--color-neutral-100);
  border-color: var(--color-neutral-400);
  transform: scale(0.98);
}

.button-secondary:disabled {
  background-color: transparent;
  border-color: var(--color-neutral-200);
  color: var(--color-neutral-400);
  cursor: not-allowed;
  opacity: 0.6;
}

.button-secondary:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.3);
}
```

**Beispiel:** "Abbrechen", "Zurück", "Schließen"

---

#### 3.1.3 Ghost Button (Tertiäraktion)

**Verwendung:** Links, Navigation, weniger wichtige Aktionen

**Style:**
```css
.button-ghost {
  /* Größe: Medium (default) */
  height: 40px;
  padding: 0 var(--space-3); /* 0 12px */

  /* Typography */
  font-size: var(--text-base); /* 16px */
  font-weight: var(--font-medium); /* 500 */
  line-height: 1;

  /* Colors */
  background-color: transparent;
  color: var(--color-primary-600);
  border: none;

  /* Shape */
  border-radius: var(--radius-md); /* 6px */

  /* Interactivity */
  cursor: pointer;
  transition: all 150ms ease-in-out;
}

.button-ghost:hover {
  background-color: var(--color-primary-50);
  color: var(--color-primary-700);
}

.button-ghost:active {
  background-color: var(--color-primary-100);
  transform: scale(0.98);
}

.button-ghost:disabled {
  background-color: transparent;
  color: var(--color-neutral-400);
  cursor: not-allowed;
  opacity: 0.6;
}

.button-ghost:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}
```

**Beispiel:** "Details anzeigen →", "Mehr erfahren", "Abbrechen"

---

#### 3.1.4 Danger Button (Destruktive Aktion)

**Verwendung:** Löschen, Trennen, irreversible Aktionen

**Style:**
```css
.button-danger {
  /* Größe: Medium (default) */
  height: 40px;
  padding: 0 var(--space-4); /* 0 16px */

  /* Typography */
  font-size: var(--text-base); /* 16px */
  font-weight: var(--font-medium); /* 500 */
  line-height: 1;

  /* Colors */
  background-color: var(--color-error-600); /* #DC2626 */
  color: var(--color-white);
  border: 1px solid var(--color-error-600);

  /* Shape */
  border-radius: var(--radius-md); /* 6px */

  /* Interactivity */
  cursor: pointer;
  transition: all 150ms ease-in-out;
}

.button-danger:hover {
  background-color: var(--color-error-700); /* #B91C1C */
  border-color: var(--color-error-700);
  box-shadow: var(--shadow-sm);
}

.button-danger:active {
  background-color: var(--color-error-800); /* #991B1B */
  border-color: var(--color-error-800);
  transform: scale(0.98);
}

.button-danger:disabled {
  background-color: var(--color-neutral-300);
  border-color: var(--color-neutral-300);
  color: var(--color-neutral-500);
  cursor: not-allowed;
  opacity: 0.6;
}

.button-danger:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.3);
}
```

**Beispiel:** "Eigenschaft löschen", "Buchung stornieren", "Verbindung trennen"

---

#### 3.1.5 Button Sizes

**Small Button:**
```css
.button-sm {
  height: 32px;
  padding: 0 var(--space-3); /* 0 12px */
  font-size: var(--text-sm); /* 14px */
}
```
**Verwendung:** Kompakte Buttons in Tabellen, Cards

**Medium Button (Default):**
```css
.button-md {
  height: 40px;
  padding: 0 var(--space-4); /* 0 16px */
  font-size: var(--text-base); /* 16px */
}
```
**Verwendung:** Standard-Buttons in Formularen, Aktionen

**Large Button:**
```css
.button-lg {
  height: 48px;
  padding: 0 var(--space-6); /* 0 24px */
  font-size: var(--text-lg); /* 18px */
}
```
**Verwendung:** Primary CTAs (Hero, Checkout)

---

#### 3.1.6 Button States (Loading)

**Loading State:**
```css
.button-loading {
  position: relative;
  color: transparent; /* Text verstecken */
  pointer-events: none;
}

.button-loading::after {
  content: "";
  position: absolute;
  width: 16px;
  height: 16px;
  top: 50%;
  left: 50%;
  margin-left: -8px;
  margin-top: -8px;
  border: 2px solid var(--color-white);
  border-radius: 50%;
  border-top-color: transparent;
  animation: spinner 0.6s linear infinite;
}

@keyframes spinner {
  to { transform: rotate(360deg); }
}
```

**Beispiel:** "Speichern..." (mit Spinner)

---

### 3.2 Form Elements

#### 3.2.1 Text Input

**Style:**
```css
.input-text {
  /* Größe */
  height: 40px;
  width: 100%;
  padding: 0 var(--space-3); /* 0 12px */

  /* Typography */
  font-size: var(--text-base); /* 16px */
  font-weight: var(--font-normal); /* 400 */
  color: var(--color-neutral-700);

  /* Appearance */
  background-color: var(--color-white);
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); /* 6px */

  /* Interactivity */
  transition: all 150ms ease-in-out;
}

.input-text::placeholder {
  color: var(--color-neutral-400);
}

.input-text:hover {
  border-color: var(--color-neutral-400);
}

.input-text:focus {
  outline: none;
  border-color: var(--color-primary-500);
  box-shadow: var(--shadow-focus); /* 0 0 0 3px rgba(59, 130, 246, 0.3) */
}

.input-text:disabled {
  background-color: var(--color-neutral-100);
  border-color: var(--color-neutral-200);
  color: var(--color-neutral-500);
  cursor: not-allowed;
}

.input-text.error {
  border-color: var(--color-error-500);
}

.input-text.error:focus {
  border-color: var(--color-error-500);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.3);
}
```

**Label + Input + Helper:**
```html
<div class="form-field">
  <label class="label" for="property-name">
    Eigenschaftsname <span class="required">*</span>
  </label>
  <input
    type="text"
    id="property-name"
    class="input-text"
    placeholder="z.B. Strandvilla Ostsee"
  />
  <p class="helper-text">Wird in Buchungsbestätigung angezeigt</p>
</div>
```

**CSS:**
```css
.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2); /* 8px */
}

.label {
  font-size: var(--text-sm); /* 14px */
  font-weight: var(--font-medium); /* 500 */
  color: var(--color-neutral-700);
}

.label .required {
  color: var(--color-error-500);
}

.helper-text {
  font-size: var(--text-xs); /* 12px */
  color: var(--color-neutral-500);
}

.error-message {
  font-size: var(--text-xs); /* 12px */
  color: var(--color-error-600);
  font-weight: var(--font-medium); /* 500 */
}
```

---

#### 3.2.2 Textarea

**Style:**
```css
.input-textarea {
  /* Größe */
  min-height: 100px;
  width: 100%;
  padding: var(--space-3); /* 12px */

  /* Typography */
  font-size: var(--text-base); /* 16px */
  font-weight: var(--font-normal); /* 400 */
  color: var(--color-neutral-700);
  font-family: var(--font-family-sans);

  /* Appearance */
  background-color: var(--color-white);
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); /* 6px */

  /* Interactivity */
  transition: all 150ms ease-in-out;
  resize: vertical;
}

/* Gleiche States wie input-text (hover, focus, disabled, error) */
```

**Beispiel:** Beschreibung, Notizen

---

#### 3.2.3 Select (Dropdown)

**Style:**
```css
.input-select {
  /* Größe */
  height: 40px;
  width: 100%;
  padding: 0 var(--space-3); /* 0 12px */
  padding-right: var(--space-8); /* Platz für Arrow Icon */

  /* Typography */
  font-size: var(--text-base); /* 16px */
  font-weight: var(--font-normal); /* 400 */
  color: var(--color-neutral-700);

  /* Appearance */
  background-color: var(--color-white);
  background-image: url("data:image/svg+xml,..."); /* Chevron Down Icon */
  background-position: right 12px center;
  background-repeat: no-repeat;
  background-size: 16px;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md); /* 6px */

  /* Interactivity */
  appearance: none;
  cursor: pointer;
  transition: all 150ms ease-in-out;
}

/* Gleiche States wie input-text (hover, focus, disabled, error) */
```

**Beispiel:** Status-Filter, Eigenschaftstyp

---

#### 3.2.4 Checkbox

**Style:**
```css
.input-checkbox {
  /* Größe */
  width: 18px;
  height: 18px;

  /* Appearance */
  background-color: var(--color-white);
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-sm); /* 4px */

  /* Interactivity */
  cursor: pointer;
  transition: all 150ms ease-in-out;
  appearance: none;
}

.input-checkbox:hover {
  border-color: var(--color-neutral-400);
}

.input-checkbox:checked {
  background-color: var(--color-primary-600);
  border-color: var(--color-primary-600);
  background-image: url("data:image/svg+xml,..."); /* Checkmark Icon */
  background-position: center;
  background-repeat: no-repeat;
  background-size: 12px;
}

.input-checkbox:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

.input-checkbox:disabled {
  background-color: var(--color-neutral-100);
  border-color: var(--color-neutral-200);
  cursor: not-allowed;
}
```

**Label + Checkbox:**
```html
<div class="checkbox-field">
  <input type="checkbox" id="wifi" class="input-checkbox" />
  <label for="wifi" class="checkbox-label">WLAN verfügbar</label>
</div>
```

**CSS:**
```css
.checkbox-field {
  display: flex;
  align-items: center;
  gap: var(--space-2); /* 8px */
}

.checkbox-label {
  font-size: var(--text-base); /* 16px */
  font-weight: var(--font-normal); /* 400 */
  color: var(--color-neutral-700);
  cursor: pointer;
  user-select: none;
}
```

---

#### 3.2.5 Radio Button

**Style:**
```css
.input-radio {
  /* Größe */
  width: 18px;
  height: 18px;

  /* Appearance */
  background-color: var(--color-white);
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-full); /* Kreis */

  /* Interactivity */
  cursor: pointer;
  transition: all 150ms ease-in-out;
  appearance: none;
}

.input-radio:hover {
  border-color: var(--color-neutral-400);
}

.input-radio:checked {
  background-color: var(--color-white);
  border-color: var(--color-primary-600);
  border-width: 5px; /* Dicke Border = gefüllter Kreis */
}

.input-radio:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

.input-radio:disabled {
  background-color: var(--color-neutral-100);
  border-color: var(--color-neutral-200);
  cursor: not-allowed;
}
```

**Beispiel:** Eigenschaftstyp (Villa, Apartment, Haus)

---

### 3.3 Status Badges

**Basis:** Phase 10A Status Components (READ-ONLY)

**Badge-Struktur:**
```css
.badge {
  /* Größe */
  display: inline-flex;
  align-items: center;
  gap: var(--space-1); /* 4px - für Icon */
  padding: var(--space-1) var(--space-2); /* 4px 8px */

  /* Typography */
  font-size: var(--text-xs); /* 12px */
  font-weight: var(--font-medium); /* 500 */
  line-height: 1;

  /* Shape */
  border-radius: var(--radius-sm); /* 4px */

  /* No Interactivity (static) */
}
```

---

#### 3.3.1 Buchungs-Status

**Bestätigt (Confirmed):**
```css
.badge-confirmed {
  background-color: var(--color-success-100); /* #DCFCE7 */
  color: var(--color-success-700); /* #15803D */
}
```
**Text:** "Bestätigt"

**Reserviert (Reserved):**
```css
.badge-reserved {
  background-color: var(--color-info-100); /* #DBEAFE */
  color: var(--color-info-700); /* #1D4ED8 */
}
```
**Text:** "Reserviert"

**Eingecheckt (Checked-in):**
```css
.badge-checkedin {
  background-color: var(--color-success-600); /* #16A34A */
  color: var(--color-white);
}
```
**Text:** "Eingecheckt"

**Ausgecheckt (Checked-out):**
```css
.badge-checkedout {
  background-color: var(--color-warning-500); /* #F59E0B */
  color: var(--color-white);
}
```
**Text:** "Ausgecheckt"

**Storniert (Cancelled):**
```css
.badge-cancelled {
  background-color: var(--color-error-100); /* #FEE2E2 */
  color: var(--color-error-700); /* #B91C1C */
}
```
**Text:** "Storniert"

**Ausstehend (Pending):**
```css
.badge-pending {
  background-color: var(--color-neutral-200); /* #E5E7EB */
  color: var(--color-neutral-700); /* #374151 */
}
```
**Text:** "Ausstehend"

---

#### 3.3.2 Channel-Status

**Verbunden (Connected):**
```css
.badge-connected {
  background-color: var(--color-success-100);
  color: var(--color-success-700);
}
```
**Text:** "Verbunden"

**Fehler (Error):**
```css
.badge-error {
  background-color: var(--color-error-100);
  color: var(--color-error-700);
}
```
**Text:** "Fehler"

**Warnung (Warning):**
```css
.badge-warning {
  background-color: var(--color-warning-100);
  color: var(--color-warning-700);
}
```
**Text:** "Warnung"

**Nicht verbunden (Not Connected):**
```css
.badge-disconnected {
  background-color: var(--color-neutral-200);
  color: var(--color-neutral-700);
}
```
**Text:** "Nicht verbunden"

---

#### 3.3.3 Eigenschafts-Status

**Aktiv (Active):**
```css
.badge-active {
  background-color: var(--color-success-100);
  color: var(--color-success-700);
}
```
**Text:** "Aktiv"

**Inaktiv (Inactive):**
```css
.badge-inactive {
  background-color: var(--color-neutral-200);
  color: var(--color-neutral-700);
}
```
**Text:** "Inaktiv"

---

### 3.4 Cards

**Card-Struktur:**
```css
.card {
  /* Appearance */
  background-color: var(--color-white);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md); /* 6px */
  box-shadow: var(--shadow-sm); /* 0 1px 2px 0 rgba(0, 0, 0, 0.05) */

  /* Spacing */
  padding: var(--space-4); /* 16px */

  /* Interactivity (optional, wenn klickbar) */
  transition: all 150ms ease-in-out;
}

.card:hover {
  box-shadow: var(--shadow-md); /* 0 4px 6px -1px rgba(0, 0, 0, 0.1) */
  border-color: var(--color-neutral-300);
}

.card-clickable {
  cursor: pointer;
}

.card-clickable:active {
  transform: scale(0.99);
}
```

**Card Header + Body + Footer:**
```css
.card-header {
  padding-bottom: var(--space-3); /* 12px */
  border-bottom: 1px solid var(--color-neutral-200);
  margin-bottom: var(--space-4); /* 16px */
}

.card-body {
  /* Haupt-Content */
}

.card-footer {
  padding-top: var(--space-3); /* 12px */
  border-top: 1px solid var(--color-neutral-200);
  margin-top: var(--space-4); /* 16px */
}
```

**Beispiel:** Property Card, Booking Card, Channel Card

---

### 3.5 Tables

**Table-Struktur:**
```css
.table {
  width: 100%;
  border-collapse: collapse;
  background-color: var(--color-white);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md); /* 6px */
  overflow: hidden; /* für Border Radius */
}

.table thead {
  background-color: var(--color-neutral-50);
  border-bottom: 1px solid var(--color-neutral-200);
}

.table th {
  padding: var(--space-3) var(--space-4); /* 12px 16px */
  text-align: left;
  font-size: var(--text-sm); /* 14px */
  font-weight: var(--font-medium); /* 500 */
  color: var(--color-neutral-700);
}

.table tbody tr {
  border-bottom: 1px solid var(--color-neutral-200);
  transition: background-color 150ms ease-in-out;
}

.table tbody tr:last-child {
  border-bottom: none;
}

.table tbody tr:hover {
  background-color: var(--color-neutral-50);
}

.table td {
  padding: var(--space-3) var(--space-4); /* 12px 16px */
  font-size: var(--text-base); /* 16px */
  color: var(--color-neutral-600);
}
```

**Beispiel:** Booking List, Team Members, Sync Logs

---

### 3.6 Modals

**Modal-Struktur:**
```css
.modal-backdrop {
  /* Overlay */
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5); /* 50% Transparenz */
  z-index: 1000;

  /* Center Content */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4); /* 16px - für Mobile Margin */
}

.modal {
  /* Appearance */
  background-color: var(--color-white);
  border-radius: var(--radius-lg); /* 8px */
  box-shadow: var(--shadow-xl); /* 0 20px 25px -5px rgba(0, 0, 0, 0.1) */

  /* Größe */
  max-width: 500px; /* Small Modal */
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;

  /* Spacing */
  padding: var(--space-6); /* 24px */

  /* Animation */
  animation: modalFadeIn 200ms ease-out;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
```

**Modal Header + Body + Footer:**
```css
.modal-header {
  padding-bottom: var(--space-4); /* 16px */
  border-bottom: 1px solid var(--color-neutral-200);
  margin-bottom: var(--space-4); /* 16px */

  /* Header Content */
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title {
  font-size: var(--text-xl); /* 20px */
  font-weight: var(--font-semibold); /* 600 */
  color: var(--color-neutral-800);
}

.modal-close {
  /* X Button */
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--color-neutral-500);
  transition: color 150ms ease-in-out;
}

.modal-close:hover {
  color: var(--color-neutral-700);
}

.modal-body {
  /* Haupt-Content */
}

.modal-footer {
  padding-top: var(--space-4); /* 16px */
  border-top: 1px solid var(--color-neutral-200);
  margin-top: var(--space-4); /* 16px */

  /* Footer Buttons */
  display: flex;
  gap: var(--space-3); /* 12px */
  justify-content: flex-end;
}
```

**Modal Sizes:**
- **Small:** 400px (Confirm Dialogs)
- **Medium:** 500px (Forms)
- **Large:** 800px (Detailed Views)

---

### 3.7 Alerts (Meldungen)

**Alert-Struktur:**
```css
.alert {
  /* Appearance */
  border-radius: var(--radius-md); /* 6px */
  border: 1px solid;
  padding: var(--space-3); /* 12px */

  /* Layout */
  display: flex;
  align-items: flex-start;
  gap: var(--space-2); /* 8px */

  /* Typography */
  font-size: var(--text-sm); /* 14px */
  line-height: var(--leading-sm);
}

.alert-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
}

.alert-content {
  flex: 1;
}

.alert-close {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 150ms ease-in-out;
}

.alert-close:hover {
  opacity: 1;
}
```

**Alert Variants:**

**Success:**
```css
.alert-success {
  background-color: var(--color-success-50);
  border-color: var(--color-success-200);
  color: var(--color-success-700);
}
```
**Text:** "Buchung erfolgreich gespeichert!"

**Error:**
```css
.alert-error {
  background-color: var(--color-error-50);
  border-color: var(--color-error-200);
  color: var(--color-error-700);
}
```
**Text:** "Fehler beim Speichern. Bitte versuchen Sie es erneut."

**Warning:**
```css
.alert-warning {
  background-color: var(--color-warning-50);
  border-color: var(--color-warning-200);
  color: var(--color-warning-700);
}
```
**Text:** "Buchung läuft in 5 Minuten ab."

**Info:**
```css
.alert-info {
  background-color: var(--color-info-50);
  border-color: var(--color-info-200);
  color: var(--color-info-700);
}
```
**Text:** "Kostenlose Stornierung bis 1. Juli."

---

## 4. Layout & Grid (Phase 10B)

### 4.1 Breakpoints

**Basis:** Phase 10A Layout-Grundlagen (READ-ONLY)

| Breakpoint | Width | Use Case |
|------------|-------|----------|
| `sm` | `640px` | Mobile Landscape |
| `md` | `768px` | Tablet |
| `lg` | `1024px` | Desktop |
| `xl` | `1280px` | Large Desktop |
| `2xl` | `1536px` | XL Desktop |

**CSS Variables:**
```css
:root {
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;
  --breakpoint-2xl: 1536px;
}
```

---

### 4.2 Container Max-Width

**Desktop:**
```css
.container {
  max-width: 1280px; /* xl */
  margin-left: auto;
  margin-right: auto;
  padding-left: var(--space-4); /* 16px */
  padding-right: var(--space-4); /* 16px */
}

@media (min-width: 1536px) { /* 2xl */
  .container {
    max-width: 1536px;
  }
}
```

**Mobile:**
```css
.container-mobile {
  width: 100%;
  padding-left: var(--space-4); /* 16px */
  padding-right: var(--space-4); /* 16px */
}
```

---

### 4.3 Spacing System

**Basis:** Phase 10A Spacing Scale (READ-ONLY)

| Token | Value (px/rem) | Use Case |
|-------|----------------|----------|
| `space-0` | `0px` / `0` | No spacing |
| `space-1` | `4px` / `0.25rem` | Tight spacing (icon-text gap) |
| `space-2` | `8px` / `0.5rem` | Compact spacing (button padding) |
| `space-3` | `12px` / `0.75rem` | Small spacing (form field gap) |
| `space-4` | `16px` / `1rem` | Default spacing (card padding) |
| `space-6` | `24px` / `1.5rem` | Medium spacing (section gap) |
| `space-8` | `32px` / `2rem` | Large spacing (page margin) |
| `space-12` | `48px` / `3rem` | XL spacing (hero section) |
| `space-16` | `64px` / `4rem` | XXL spacing (page header) |

**CSS Variables:**
```css
:root {
  --space-0: 0;
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2rem;     /* 32px */
  --space-12: 3rem;    /* 48px */
  --space-16: 4rem;    /* 64px */
}
```

---

### 4.4 Grid System

**12-Column Grid (Desktop):**
```css
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--space-4); /* 16px */
}

/* Grid Spans */
.col-span-1 { grid-column: span 1 / span 1; }
.col-span-2 { grid-column: span 2 / span 2; }
.col-span-3 { grid-column: span 3 / span 3; }
.col-span-4 { grid-column: span 4 / span 4; }
.col-span-6 { grid-column: span 6 / span 6; }
.col-span-8 { grid-column: span 8 / span 8; }
.col-span-12 { grid-column: span 12 / span 12; }
```

**4-Column Grid (Mobile):**
```css
@media (max-width: 768px) {
  .grid {
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-3); /* 12px */
  }
}
```

---

### 4.5 Flexbox Utilities

**Flex Container:**
```css
.flex {
  display: flex;
}

.flex-col {
  display: flex;
  flex-direction: column;
}

/* Justify */
.justify-start { justify-content: flex-start; }
.justify-center { justify-content: center; }
.justify-end { justify-content: flex-end; }
.justify-between { justify-content: space-between; }

/* Align */
.items-start { align-items: flex-start; }
.items-center { align-items: center; }
.items-end { align-items: flex-end; }

/* Gap */
.gap-1 { gap: var(--space-1); }
.gap-2 { gap: var(--space-2); }
.gap-3 { gap: var(--space-3); }
.gap-4 { gap: var(--space-4); }
.gap-6 { gap: var(--space-6); }
.gap-8 { gap: var(--space-8); }
```

---

## 5. White-Label-Theming (Phase 10C)

### 5.1 Theming-Strategie

**Ziel:** Agenturen können eigene Markenfarben, Logo und Typografie einbinden.

**Methode:** CSS Variables (Custom Properties)

**Vorteil:**
- Einfaches Überschreiben durch Agentur-CSS
- Keine Code-Änderungen nötig
- Runtime-Anpassung möglich (Theme-Switcher)

---

### 5.2 CSS Variables Struktur

**Root Variables (Standard-Theme):**
```css
:root {
  /* Brand Colors (White-Label) */
  --color-brand-primary: var(--color-primary-600);     /* #2563EB */
  --color-brand-secondary: var(--color-secondary-600); /* #4F46E5 */
  --color-brand-accent: var(--color-accent-600);       /* #0891B2 */

  /* Typography (White-Label) */
  --font-family-heading: var(--font-family-sans);
  --font-family-body: var(--font-family-sans);

  /* Logo */
  --logo-url: url('/assets/logo.svg'); /* Default Logo */
  --logo-width: 150px;
  --logo-height: 40px;
}
```

**Verwendung in Components:**
```css
.button-primary {
  background-color: var(--color-brand-primary); /* Statt var(--color-primary-600) */
  border-color: var(--color-brand-primary);
}

.navbar-logo {
  background-image: var(--logo-url);
  width: var(--logo-width);
  height: var(--logo-height);
}

h1, h2, h3 {
  font-family: var(--font-family-heading);
}
```

---

### 5.3 Agentur-Theme (Custom-Theme)

**Beispiel: Agentur "Küstenvermietung Nord"**

**Agentur-CSS (überschreibt Root Variables):**
```css
:root {
  /* Agentur-Farben */
  --color-brand-primary: #0077B6;     /* Ozeanblau */
  --color-brand-secondary: #00B4D8;   /* Hellblau */
  --color-brand-accent: #90E0EF;      /* Akzentblau */

  /* Agentur-Typografie */
  --font-family-heading: 'Montserrat', sans-serif;
  --font-family-body: 'Open Sans', sans-serif;

  /* Agentur-Logo */
  --logo-url: url('https://cdn.kuesten-vermietung.de/logo.svg');
  --logo-width: 180px;
  --logo-height: 50px;
}
```

**Integration:**
```html
<!-- Standard-Theme -->
<link rel="stylesheet" href="/css/app.css">

<!-- Agentur-Theme (überschreibt) -->
<link rel="stylesheet" href="https://cdn.kuesten-vermietung.de/theme.css">
```

**Effekt:**
- Alle Primary Buttons: Ozeanblau (#0077B6)
- Alle Headings: Montserrat Font
- Logo: Agentur-Logo

---

### 5.4 Theme-Switching (Runtime)

**JavaScript-Implementierung (Post-MVP):**
```javascript
// Theme wechseln (z.B. bei Multi-Tenant-Login)
function applyAgencyTheme(agencyId) {
  fetch(`/api/agencies/${agencyId}/theme`)
    .then(res => res.json())
    .then(theme => {
      document.documentElement.style.setProperty('--color-brand-primary', theme.primaryColor);
      document.documentElement.style.setProperty('--color-brand-secondary', theme.secondaryColor);
      document.documentElement.style.setProperty('--logo-url', `url(${theme.logoUrl})`);
      // ...
    });
}
```

**Beispiel:** Benutzer wechselt zwischen Agenturen → Theme ändert sich live.

---

### 5.5 Wo erscheint Agentur-Branding?

**Logo:**
- **Header (Top Bar):** Links, immer sichtbar
- **Login-Seite:** Zentriert, groß
- **Öffentliche Buchungsseiten:** Header (für Direct Bookings)

**Farben:**
- **Primary Color:** Buttons, Links, Navigation (aktiv)
- **Secondary Color:** Akzente, Highlights
- **Accent Color:** Tooltips, neue Features

**Typografie:**
- **Headings:** Agentur-Font (wenn definiert)
- **Body:** Agentur-Font ODER Standard (aus Lesbarkeit)

**Favicon:**
- `--favicon-url` (überschreibbar)

---

### 5.6 Standard-Theme vs Custom-Theme

**Standard-Theme (MVP):**
- **Farben:** Blau (#2563EB), Indigo (#4F46E5), Cyan (#0891B2)
- **Typografie:** Inter (Google Fonts)
- **Logo:** Generisches PMS-Logo (KEIN Produktname)
- **Verwendung:** Default, Demo, Onboarding

**Custom-Theme (Agentur):**
- **Farben:** Agentur-Markenfarben
- **Typografie:** Agentur-Fonts (optional)
- **Logo:** Agentur-Logo
- **Verwendung:** Produktivbetrieb (nach Agentur-Setup)

---

## 6. Deutsche UI-Texte (Phase 10C)

### 6.1 Buttons (Aktionen)

**Primäre Aktionen:**
- "Speichern"
- "Bestätigen"
- "Anlegen"
- "Erstellen"
- "Hinzufügen"
- "Verbinden"
- "Synchronisieren"
- "Exportieren"
- "Herunterladen"

**Sekundäre Aktionen:**
- "Abbrechen"
- "Zurück"
- "Schließen"
- "Überspringen"

**Destruktive Aktionen:**
- "Löschen"
- "Stornieren"
- "Trennen"
- "Entfernen"

**Navigation:**
- "Alle anzeigen →"
- "Details anzeigen →"
- "Mehr erfahren →"
- "Bearbeiten"
- "Ansehen"

---

### 6.2 Labels (Formulare & Daten)

**Eigenschaften (Properties):**
- "Eigenschaftsname"
- "Eigenschaftstyp" (Villa, Apartment, Haus, Ferienhaus)
- "Adresse"
- "Stadt"
- "Postleitzahl"
- "Land"
- "Beschreibung"
- "Ausstattung"
- "Schlafzimmer"
- "Badezimmer"
- "Maximale Gäste"
- "Wohnfläche (qm)"
- "Status" (Aktiv, Inaktiv)

**Buchungen (Bookings):**
- "Buchungsnummer"
- "Gast"
- "Gastname"
- "E-Mail"
- "Telefon"
- "Check-in"
- "Check-out"
- "Nächte"
- "Anzahl Gäste"
- "Status" (Bestätigt, Reserviert, Eingecheckt, Ausgecheckt, Storniert, Ausstehend)
- "Quelle" (Direkt, Airbnb, Booking.com, Expedia)
- "Gesamtbetrag"
- "Gezahlter Betrag"
- "Offener Betrag"
- "Währung"

**Channels:**
- "Channel-Name"
- "Status" (Verbunden, Nicht verbunden, Fehler, Warnung)
- "Letzte Synchronisation"
- "Synchronisierte Eigenschaften"
- "Synchronisierte Buchungen"

**Team:**
- "Name"
- "E-Mail"
- "Rolle" (Inhaber, Manager, Mitarbeiter, Betrachter, Buchhalter)
- "Status" (Aktiv, Ausstehend, Deaktiviert)

**Zeiträume:**
- "Von"
- "Bis"
- "Zeitraum"
- "Datum"
- "Uhrzeit"

---

### 6.3 Fehlermeldungen

**Validierungsfehler (Formulare):**
- "Bitte füllen Sie alle Pflichtfelder aus."
- "Bitte geben Sie eine gültige E-Mail-Adresse ein."
- "Bitte geben Sie eine gültige Telefonnummer ein."
- "Das Passwort muss mindestens 8 Zeichen lang sein."
- "Die Passwörter stimmen nicht überein."
- "Bitte wählen Sie ein Datum aus."
- "Das Check-in-Datum muss vor dem Check-out-Datum liegen."
- "Bitte wählen Sie mindestens eine Ausstattung aus."
- "Der Eigenschaftsname ist bereits vergeben."

**API-Fehler (Netzwerk, Server):**
- "Fehler beim Laden der Daten. Bitte versuchen Sie es erneut."
- "Fehler beim Speichern. Bitte versuchen Sie es erneut."
- "Verbindung zum Server fehlgeschlagen. Bitte prüfen Sie Ihre Internetverbindung."
- "Sitzung abgelaufen. Bitte melden Sie sich erneut an."
- "Sie haben keine Berechtigung für diese Aktion."
- "Die angeforderte Ressource wurde nicht gefunden."

**Channel-Fehler:**
- "Synchronisation fehlgeschlagen. Bitte überprüfen Sie Ihre Verbindung."
- "Channel-Verbindung wurde getrennt. Bitte verbinden Sie sich erneut."
- "OAuth-Authentifizierung fehlgeschlagen. Bitte versuchen Sie es erneut."

**Buchungs-Fehler:**
- "Diese Eigenschaft ist für den gewählten Zeitraum bereits gebucht."
- "Buchung konnte nicht gespeichert werden. Bitte überprüfen Sie Ihre Eingaben."
- "Zahlung fehlgeschlagen. Bitte versuchen Sie es erneut."
- "Buchung konnte nicht storniert werden."

---

### 6.4 Erfolgsmeldungen

**Speicher-Erfolge:**
- "Eigenschaft erfolgreich gespeichert!"
- "Buchung erfolgreich gespeichert!"
- "Einstellungen erfolgreich gespeichert!"
- "Änderungen erfolgreich gespeichert!"

**Erstellungs-Erfolge:**
- "Eigenschaft erfolgreich angelegt!"
- "Buchung erfolgreich erstellt!"
- "Team-Mitglied erfolgreich eingeladen!"
- "Channel erfolgreich verbunden!"

**Lösch-Erfolge:**
- "Eigenschaft erfolgreich gelöscht."
- "Buchung erfolgreich storniert."
- "Team-Mitglied erfolgreich entfernt."
- "Channel-Verbindung erfolgreich getrennt."

**Synchronisations-Erfolge:**
- "Synchronisation erfolgreich abgeschlossen."
- "Alle Daten wurden aktualisiert."

---

### 6.5 Warnungen

**Zeitkritische Warnungen:**
- "Buchung läuft in 5 Minuten ab."
- "Zahlung noch ausstehend."
- "Check-in heute um 14:00 Uhr."

**Konfirmations-Warnungen (vor destruktiven Aktionen):**
- "Möchten Sie diese Eigenschaft wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden."
- "Möchten Sie diese Buchung wirklich stornieren?"
- "Möchten Sie die Verbindung zu diesem Channel wirklich trennen? Buchungen werden nicht mehr synchronisiert."

**Datenverlust-Warnungen:**
- "Sie haben ungespeicherte Änderungen. Möchten Sie die Seite wirklich verlassen?"

---

### 6.6 Info-Meldungen

**Hilfetext (Helper Text):**
- "Wird in Buchungsbestätigung angezeigt."
- "Max. 500 Zeichen."
- "Pflichtfeld."
- "Optional."
- "Wird nur für interne Zwecke verwendet."

**Status-Infos:**
- "Synchronisation läuft..."
- "Daten werden geladen..."
- "Buchung wird gespeichert..."

**Empty States:**
- "Noch keine Eigenschaften vorhanden."
- "Noch keine Buchungen vorhanden."
- "Noch keine Channels verbunden."
- "Noch keine Team-Mitglieder eingeladen."

---

### 6.7 Status-Texte (Badges)

**Buchungs-Status:**
- "Bestätigt"
- "Reserviert"
- "Eingecheckt"
- "Ausgecheckt"
- "Storniert"
- "Ausstehend"

**Channel-Status:**
- "Verbunden"
- "Nicht verbunden"
- "Fehler"
- "Warnung"

**Eigenschafts-Status:**
- "Aktiv"
- "Inaktiv"

**Team-Status:**
- "Aktiv"
- "Ausstehend"
- "Deaktiviert"

---

### 6.8 Navigation & Menü

**Haupt-Navigation:**
- "Dashboard"
- "Eigenschaften"
- "Buchungen"
- "Channels"
- "Team"
- "Einstellungen"

**Untermenü:**
- "Übersicht"
- "Kalender"
- "Berichte"
- "Benachrichtigungen"
- "Profil"
- "Abrechnung"
- "Abmelden"

**Breadcrumbs:**
- "Startseite"
- "Eigenschaften"
- "Strandvilla Ostsee"
- "Bearbeiten"

---

### 6.9 Tonalität & Stil

**Richtlinien:**
- **Professionell:** B2B-Software, kein Marketing-Sprech
- **Klar:** Eindeutige, präzise Formulierungen
- **Freundlich:** Höflich, aber nicht übertrieben
- **Konsistent:** Gleiche Begriffe für gleiche Konzepte
- **Aktiv:** Aktive Verben ("Speichern", nicht "Wird gespeichert...")

**DO's:**
- ✅ "Eigenschaft anlegen"
- ✅ "Buchung speichern"
- ✅ "Änderungen verwerfen"

**DON'Ts:**
- ❌ "Jetzt loslegen!" (zu Marketing-lastig)
- ❌ "Wow, super gemacht!" (zu informell)
- ❌ "Oops, da ist was schiefgelaufen!" (zu casual)

---

## 7. Rollen-spezifische UX (Phase 10C)

### 7.1 Rollenübersicht

**Rollen:**
1. **Agentur-Admin (Owner):** Voller Zugriff
2. **Manager:** Operativ (ohne Finanzen)
3. **Mitarbeiter (Staff):** Eingeschränkt (nur Buchungen)
4. **Eigentümer (Property Owner):** Stark reduziert (nur eigene Objekte, read-only)
5. **Buchhalter (Accountant):** Finanz-Fokus (Berichte, Abrechnungen)

---

### 7.2 Agentur-Admin (Owner)

**Zugriff:**
- ✅ Alle Menüpunkte sichtbar
- ✅ Alle Aktionen erlaubt (Create, Edit, Delete)
- ✅ Finanzdaten (Umsatz, Abrechnungen)
- ✅ Channel-Management (Verbinden, Trennen)
- ✅ Team-Management (Einladen, Rollen ändern, Entfernen)
- ✅ Einstellungen (Zahlungen, Benachrichtigungen, Billing)

**Navigation:**
```
Dashboard
Eigenschaften
Buchungen
Channels
Team
Einstellungen
  ├─ Account
  ├─ Zahlungen (Stripe)
  ├─ Benachrichtigungen
  └─ Abrechnung
```

---

### 7.3 Manager

**Zugriff:**
- ✅ Dashboard (alle Widgets)
- ✅ Eigenschaften (Erstellen, Bearbeiten, Löschen)
- ✅ Buchungen (Erstellen, Bearbeiten, Stornieren)
- ✅ Channels (Ansehen, NICHT verbinden/trennen)
- ✅ Team (Ansehen, NICHT einladen/entfernen)
- ❌ Einstellungen: KEINE Zahlungen, KEINE Abrechnung

**Navigation:**
```
Dashboard
Eigenschaften
Buchungen
Channels (Read-Only)
Team (Read-Only)
Einstellungen
  ├─ Account
  └─ Benachrichtigungen
```

**UX-Anpassungen:**
- **Channels:** "Verbinden" Button VERSCHWUNDEN (nicht nur disabled)
- **Team:** "+ Einladen" Button VERSCHWUNDEN
- **Einstellungen:** Menüpunkte "Zahlungen" und "Abrechnung" VERSCHWUNDEN

---

### 7.4 Mitarbeiter (Staff)

**Zugriff:**
- ✅ Dashboard (nur "Anstehende Check-ins")
- ✅ Buchungen (Ansehen, Status ändern: Check-in/Check-out)
- ✅ Eigenschaften (Ansehen, NICHT bearbeiten)
- ❌ Channels (KOMPLETT ausgeblendet)
- ❌ Team (KOMPLETT ausgeblendet)
- ❌ Einstellungen (NUR Account & Benachrichtigungen)

**Navigation:**
```
Dashboard (reduziert)
Eigenschaften (Read-Only)
Buchungen (eingeschränkt)
Einstellungen
  ├─ Account
  └─ Benachrichtigungen
```

**UX-Anpassungen:**
- **Dashboard:** Nur "Anstehende Check-ins" Widget (KEINE Umsatz-Stats)
- **Buchungen:** Nur "Status ändern" (Check-in/Check-out), KEIN "Bearbeiten" oder "Stornieren"
- **Eigenschaften:** Nur Ansehen, KEIN "Bearbeiten" Button
- **Navigation:** Channels, Team KOMPLETT ausgeblendet

---

### 7.5 Eigentümer (Property Owner)

**Zugriff:**
- ✅ Dashboard (nur eigene Eigenschaften)
- ✅ Eigenschaften (nur eigene, Read-Only)
- ✅ Buchungen (nur eigene Eigenschaften, Read-Only)
- ❌ Channels (KOMPLETT ausgeblendet)
- ❌ Team (KOMPLETT ausgeblendet)
- ❌ Einstellungen (NUR Account)

**Navigation:**
```
Dashboard (nur eigene Daten)
Eigenschaften (nur eigene, Read-Only)
Buchungen (nur eigene, Read-Only)
Einstellungen
  └─ Account
```

**UX-Anpassungen:**
- **Dashboard:** Nur eigene Eigenschaften und Buchungen
- **Eigenschaften:** Filter automatisch auf "Meine Eigenschaften"
- **Buchungen:** Filter automatisch auf "Buchungen meiner Eigenschaften"
- **Alle Actions:** VERSCHWUNDEN (kein "Bearbeiten", "Löschen", etc.)
- **Zweck:** Transparenz für Eigentümer (können ihre Objekte einsehen)

---

### 7.6 Buchhalter (Accountant)

**Zugriff:**
- ✅ Dashboard (Finanz-Fokus: Umsatz, Abrechnungen)
- ✅ Buchungen (Ansehen, KEINE Änderungen)
- ✅ Berichte (Umsatz, Auslastung, Prognosen)
- ✅ Abrechnungen (Erstellen, Exportieren)
- ❌ Eigenschaften (KOMPLETT ausgeblendet ODER Read-Only)
- ❌ Channels (KOMPLETT ausgeblendet)
- ❌ Team (KOMPLETT ausgeblendet)

**Navigation:**
```
Dashboard (Finanz-Widgets)
Buchungen (Read-Only)
Berichte
Abrechnungen
Einstellungen
  ├─ Account
  └─ Benachrichtigungen
```

**UX-Anpassungen:**
- **Dashboard:** Finanz-Widgets (Umsatz, Ausstehende Zahlungen, Abrechnungen)
- **Buchungen:** Read-Only (nur Finanz-Daten sichtbar)
- **Berichte:** Umsatz-Reports, Auslastungs-Reports
- **Abrechnungen:** Erstellen, Exportieren (PDF, CSV)

---

### 7.7 Menü-Reduktion (UI-Prinzip)

**Regel:** Menüpunkte VERSCHWINDEN, nicht nur disabled.

**Warum?**
- Bessere UX (weniger Clutter)
- Keine Frustration ("Warum kann ich das nicht anklicken?")
- Klarere Rollen-Trennung

**Beispiel (Manager):**
```jsx
// FALSCH (Disabled)
<MenuItem disabled={!isOwner}>Zahlungen</MenuItem>

// RICHTIG (Conditional Rendering)
{isOwner && <MenuItem>Zahlungen</MenuItem>}
```

---

### 7.8 Permissions-Matrix (Übersicht)

| Feature | Owner | Manager | Staff | Property Owner | Accountant |
|---------|-------|---------|-------|----------------|------------|
| **Dashboard** | Alles | Alles | Reduziert | Nur eigene | Finanz-Fokus |
| **Eigenschaften** | CRUD | CRUD | Read | Read (eigene) | Read/Hidden |
| **Buchungen** | CRUD | CRUD | Read + Status | Read (eigene) | Read |
| **Channels** | CRUD | Read | Hidden | Hidden | Hidden |
| **Team** | CRUD | Read | Hidden | Hidden | Hidden |
| **Berichte** | Alle | Alle | Hidden | Hidden | Alle |
| **Abrechnungen** | Alle | Hidden | Hidden | Hidden | CRUD |
| **Einstellungen: Account** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Einstellungen: Zahlungen** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Einstellungen: Billing** | ✅ | ❌ | ❌ | ❌ | ❌ |

**Legende:**
- **CRUD:** Create, Read, Update, Delete
- **Read:** Nur Lesen
- **Hidden:** Komplett ausgeblendet
- **✅:** Sichtbar/Erlaubt
- **❌:** Ausgeblendet/Verboten

---

## 8. Umsetzungshinweise

### 8.1 CSS Variables Implementation

**Datei-Struktur:**
```
/frontend/src/styles/
├── tokens/
│   ├── colors.css         (Alle Farb-Tokens)
│   ├── typography.css     (Alle Typografie-Tokens)
│   ├── spacing.css        (Alle Spacing-Tokens)
│   ├── shadows.css        (Alle Shadow-Tokens)
│   └── index.css          (Import aller Tokens)
├── components/
│   ├── buttons.css        (Button-Styles)
│   ├── forms.css          (Form-Styles)
│   ├── badges.css         (Badge-Styles)
│   ├── cards.css          (Card-Styles)
│   ├── tables.css         (Table-Styles)
│   ├── modals.css         (Modal-Styles)
│   └── alerts.css         (Alert-Styles)
├── layout/
│   ├── grid.css           (Grid-System)
│   ├── container.css      (Container)
│   └── utilities.css      (Flexbox, Spacing Utilities)
└── app.css                (Main Entry Point)
```

**app.css:**
```css
/* Import Tokens */
@import './tokens/index.css';

/* Import Components */
@import './components/buttons.css';
@import './components/forms.css';
@import './components/badges.css';
@import './components/cards.css';
@import './components/tables.css';
@import './components/modals.css';
@import './components/alerts.css';

/* Import Layout */
@import './layout/grid.css';
@import './layout/container.css';
@import './layout/utilities.css';
```

---

### 8.2 Component Library (React)

**Empfehlung:** Eigene Component Library (NICHT Tailwind, shadcn/ui)

**Grund:**
- Volle Kontrolle über Design-System
- Token-basierte Styles (White-Label)
- Konsistenz über alle Komponenten

**Beispiel-Komponenten:**
```
/frontend/src/components/
├── Button/
│   ├── Button.tsx
│   ├── Button.css
│   └── Button.stories.tsx (Storybook)
├── Input/
│   ├── Input.tsx
│   ├── Input.css
│   └── Input.stories.tsx
├── Badge/
│   ├── Badge.tsx
│   ├── Badge.css
│   └── Badge.stories.tsx
├── Card/
│   ├── Card.tsx
│   ├── Card.css
│   └── Card.stories.tsx
└── ...
```

---

### 8.3 Internationalisierung (i18n)

**Empfehlung:** react-i18next (für spätere Mehrsprachigkeit)

**Setup (MVP: Nur Deutsch):**
```javascript
// /frontend/src/i18n/de.json
{
  "buttons": {
    "save": "Speichern",
    "cancel": "Abbrechen",
    "delete": "Löschen",
    "edit": "Bearbeiten",
    "create": "Anlegen"
  },
  "labels": {
    "propertyName": "Eigenschaftsname",
    "checkIn": "Check-in",
    "checkOut": "Check-out",
    "status": "Status"
  },
  "status": {
    "confirmed": "Bestätigt",
    "reserved": "Reserviert",
    "cancelled": "Storniert"
  },
  "errors": {
    "required": "Bitte füllen Sie alle Pflichtfelder aus.",
    "invalidEmail": "Bitte geben Sie eine gültige E-Mail-Adresse ein."
  }
}
```

**Verwendung:**
```tsx
import { useTranslation } from 'react-i18next';

function PropertyForm() {
  const { t } = useTranslation();

  return (
    <form>
      <label>{t('labels.propertyName')}</label>
      <input type="text" />
      <button>{t('buttons.save')}</button>
    </form>
  );
}
```

---

### 8.4 Accessibility (a11y)

**Richtlinien:**
- **Kontrast:** Mindestens WCAG AA (4.5:1 für Text)
- **Keyboard Navigation:** Alle Actions per Tab/Enter erreichbar
- **Focus States:** Immer sichtbar (`:focus-visible`)
- **ARIA Labels:** Für Icons, Screen Reader
- **Semantisches HTML:** `<button>`, `<nav>`, `<main>`, etc.

**Beispiel:**
```tsx
<button
  className="button-primary"
  aria-label="Eigenschaft speichern"
>
  Speichern
</button>
```

---

### 8.5 Performance

**Optimierungen:**
- **Font Loading:** `font-display: swap` (FOUT statt FOIT)
- **CSS Variables:** Performanter als SASS (runtime-änderbar)
- **Critical CSS:** Above-the-fold CSS inline
- **Lazy Loading:** Components on demand

---

## 9. Zusammenfassung

### 9.1 Wichtigste Entscheidungen

**Farben:**
- Primary: Blau (#2563EB)
- Success: Grün (#16A34A)
- Error: Rot (#DC2626)
- Warning: Gelb (#D97706)

**Typografie:**
- Font: Inter (Google Fonts) ODER System Font Stack
- Base Size: 16px
- Headings: 600 (Semibold), 500 (Medium)

**Komponenten:**
- Buttons: 4 Variants (Primary, Secondary, Ghost, Danger)
- Forms: Standard Input (40px height, 6px border-radius)
- Badges: 12px font, 4px padding, 4px border-radius

**White-Label:**
- CSS Variables für alle Brand-Farben
- Logo über CSS Variable (--logo-url)
- Theme-Switching über JavaScript

**UI-Texte:**
- 100% Deutsch
- Professionell, klar, konsistent

**Rollen:**
- Menüpunkte VERSCHWINDEN (nicht disabled)
- Owner: Alles, Manager: Kein Finance, Staff: Nur Buchungen

---

### 9.2 Nächste Schritte (Implementierung)

**Phase 10D: Frontend-Implementierung (Next.js)**
1. CSS Variables Setup (tokens/)
2. Component Library (Button, Input, Badge, Card, Table, Modal, Alert)
3. Layout Components (Container, Grid, Flexbox)
4. i18n Setup (react-i18next)
5. Theming-Strategie (White-Label CSS Variables)
6. Permissions-System (rollenbasierte Navigation)

**Phase 10E: Storybook & Testing**
1. Storybook für alle Komponenten
2. Visual Regression Testing
3. Accessibility Testing

---

## Anhang: Vollständige CSS Variables

**Datei: `/frontend/src/styles/tokens/colors.css`**
```css
:root {
  /* Brand Colors */
  --color-primary-50: #EFF6FF;
  --color-primary-100: #DBEAFE;
  --color-primary-200: #BFDBFE;
  --color-primary-300: #93C5FD;
  --color-primary-400: #60A5FA;
  --color-primary-500: #3B82F6;
  --color-primary-600: #2563EB;
  --color-primary-700: #1D4ED8;
  --color-primary-800: #1E40AF;
  --color-primary-900: #1E3A8A;

  --color-secondary-50: #EEF2FF;
  --color-secondary-100: #E0E7FF;
  --color-secondary-200: #C7D2FE;
  --color-secondary-300: #A5B4FC;
  --color-secondary-400: #818CF8;
  --color-secondary-500: #6366F1;
  --color-secondary-600: #4F46E5;
  --color-secondary-700: #4338CA;
  --color-secondary-800: #3730A3;
  --color-secondary-900: #312E81;

  --color-accent-50: #ECFEFF;
  --color-accent-100: #CFFAFE;
  --color-accent-200: #A5F3FC;
  --color-accent-300: #67E8F9;
  --color-accent-400: #22D3EE;
  --color-accent-500: #06B6D4;
  --color-accent-600: #0891B2;
  --color-accent-700: #0E7490;
  --color-accent-800: #155E75;
  --color-accent-900: #164E63;

  /* Neutral Colors */
  --color-neutral-50: #F9FAFB;
  --color-neutral-100: #F3F4F6;
  --color-neutral-200: #E5E7EB;
  --color-neutral-300: #D1D5DB;
  --color-neutral-400: #9CA3AF;
  --color-neutral-500: #6B7280;
  --color-neutral-600: #4B5563;
  --color-neutral-700: #374151;
  --color-neutral-800: #1F2937;
  --color-neutral-900: #111827;

  --color-white: #FFFFFF;
  --color-black: #000000;

  /* Semantic Colors */
  --color-success-50: #F0FDF4;
  --color-success-100: #DCFCE7;
  --color-success-200: #BBF7D0;
  --color-success-300: #86EFAC;
  --color-success-400: #4ADE80;
  --color-success-500: #22C55E;
  --color-success-600: #16A34A;
  --color-success-700: #15803D;
  --color-success-800: #166534;
  --color-success-900: #14532D;

  --color-warning-50: #FFFBEB;
  --color-warning-100: #FEF3C7;
  --color-warning-200: #FDE68A;
  --color-warning-300: #FCD34D;
  --color-warning-400: #FBBF24;
  --color-warning-500: #F59E0B;
  --color-warning-600: #D97706;
  --color-warning-700: #B45309;
  --color-warning-800: #92400E;
  --color-warning-900: #78350F;

  --color-error-50: #FEF2F2;
  --color-error-100: #FEE2E2;
  --color-error-200: #FECACA;
  --color-error-300: #FCA5A5;
  --color-error-400: #F87171;
  --color-error-500: #EF4444;
  --color-error-600: #DC2626;
  --color-error-700: #B91C1C;
  --color-error-800: #991B1B;
  --color-error-900: #7F1D1D;

  --color-info-50: #EFF6FF;
  --color-info-100: #DBEAFE;
  --color-info-200: #BFDBFE;
  --color-info-300: #93C5FD;
  --color-info-400: #60A5FA;
  --color-info-500: #3B82F6;
  --color-info-600: #2563EB;
  --color-info-700: #1D4ED8;
  --color-info-800: #1E40AF;
  --color-info-900: #1E3A8A;

  /* White-Label Brand Colors */
  --color-brand-primary: var(--color-primary-600);
  --color-brand-secondary: var(--color-secondary-600);
  --color-brand-accent: var(--color-accent-600);
}
```

---

**Ende des Dokuments.**
