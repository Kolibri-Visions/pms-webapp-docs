# 37 - Premium Hybrid Navigation

> **Status:** Phase 6 abgeschlossen (Branding-UI Erweiterung)
> **Ziel:** Moderne, responsive Admin-Navigation mit Collapsible Groups, Icon-Only Toggle, Favoriten und Command Palette

---

## Übersicht

Das Premium Hybrid Navigation System erweitert die bestehende Admin-Sidebar mit folgenden Features:

1. **Collapsible Groups** - Akkordeon-Navigation mit ein-/ausklappbaren Gruppen
2. **Icon-Only Toggle** - Kompakt-Modus mit Flyout-Menüs
3. **Favoriten-System** - Pinbare Menüpunkte im Schnellzugriff
4. **Command Palette** - Globale Suche mit ⌘K
5. **Mobile Responsiveness** - Bottom Tab Bar, Drawer, Touch UX

Das Design ist vollständig über `/settings/branding` konfigurierbar (ab Phase 6).

---

## Phase 1: CSS-Variablen-System (IMPLEMENTED)

### Neue CSS-Variablen in `globals.css`

Die folgenden CSS-Variablen wurden additiv zu den bestehenden hinzugefügt:

#### Brand Gradient

```css
--brand-primary-from: #f59e0b;      /* Gradient Start */
--brand-primary-via: #f97316;       /* Gradient Mitte */
--brand-primary-to: #f43f5e;        /* Gradient Ende */
--brand-gradient: linear-gradient(...);
--brand-shadow: 0 10px 15px -3px rgba(249, 115, 22, 0.3);
```

#### Surface Tokens

```css
--surface-app: #f8f9fb;
--surface-sidebar: #ffffff;
--surface-sidebar-border: rgba(226, 232, 240, 0.8);
--surface-content: #ffffff;
--surface-header: #ffffff;
--surface-elevated-shadow: ...;
```

#### Interactive Colors

```css
--interactive-subtle-bg: #f8fafc;
--interactive-subtle-bg-hover: #f1f5f9;
--interactive-subtle-bg-active: rgba(241, 245, 249, 0.8);
--interactive-accent-bg: #fef3c7;        /* Favoriten-Highlight */
--interactive-accent-text: #d97706;
```

#### Navigation-Specific

```css
/* Group Header */
--nav-group-text, --nav-group-text-active, --nav-group-bg-active

/* Icon Container */
--nav-icon-bg, --nav-icon-bg-active, --nav-icon-text, --nav-icon-text-active

/* Item Badge (Count) */
--nav-badge-bg, --nav-badge-text, --nav-badge-text-active

/* Nav Item */
--nav-item-text, --nav-item-bg-hover, --nav-item-bg-active, --nav-item-shadow-active

/* Behavior */
--nav-width-expanded: 280px;
--nav-width-collapsed-new: 76px;
--nav-transition-duration: 300ms;

/* Spacing */
--nav-padding-x: 12px;
--nav-padding-y: 20px;
--nav-icon-container-size: 36px;

/* Typography */
--nav-group-font-size: 13px;
--nav-group-font-weight: 600;
--nav-item-font-size: 13px;
```

#### Component-Specific

```css
/* Search Input */
--search-bg, --search-border-focus, --search-ring-focus, --search-icon-focus

/* Command Palette */
--palette-backdrop, --palette-bg, --palette-shadow, --palette-item-bg-hover

/* Flyout Menu */
--flyout-bg, --flyout-border, --flyout-shadow

/* Mobile */
--mobile-header-height: 56px;
--mobile-bottom-bar-height: 64px;
--mobile-drawer-width: 320px;
--touch-target-min: 44px;
```

### Theme Provider Erweiterung

`frontend/app/lib/theme-provider.tsx` wurde erweitert:

1. **Neue Interfaces:**
   - `ApiBrandConfig` - Gradient-Konfiguration
   - `ApiNavBehavior` - Verhalten (Collapsible, Favorites, etc.)

2. **Neue Funktion:**
   - `applyPremiumNavCssVariables()` - Setzt Brand-Gradient und Nav-Behavior-Variablen

3. **Automatische Ableitung:**
   - Brand-Gradient wird aus `accent_color` abgeleitet (wenn nicht explizit gesetzt)
   - Accent-Light/Medium/Dark werden automatisch berechnet

### Dark Mode Support

Alle neuen Variablen haben Dark Mode Overrides:
- In `[data-theme="dark"]` Block
- In `[data-theme="system"]` Block (prefers-color-scheme: dark)

---

## Phase 2: Navigation-Komponenten (IMPLEMENTED)

### Neue Features in `AdminShell.tsx`

#### Flyout-Menüs im Collapsed Mode

Wenn die Sidebar collapsed ist, zeigt das Hovern über eine Gruppe ein Flyout-Menü:

```tsx
// Flyout State
const [hoveredGroup, setHoveredGroup] = useState<string | null>(null);
const flyoutTimeoutRef = useRef<NodeJS.Timeout | null>(null);

// Flyout erscheint bei Hover über Gruppe im collapsed Mode
{isHovered && (
  <div className="absolute left-full top-0 ml-2 z-50 animate-in fade-in slide-in-from-left-2">
    {/* Flyout Header + Items */}
  </div>
)}
```

#### Group Item Count Badges

Jede Gruppe zeigt die Anzahl der sichtbaren Items:

```tsx
<span style={{
  backgroundColor: isExpanded ? 'var(--nav-badge-bg-active)' : 'var(--nav-badge-bg)',
  color: isExpanded ? 'var(--nav-badge-text-active)' : 'var(--nav-badge-text)',
}}>
  {visibleItems.length}
</span>
```

#### Animierte Transitions

Alle Expand/Collapse-Animationen nutzen CSS-Variablen:

```tsx
style={{
  maxHeight: isExpanded ? '500px' : '0px',
  transition: `max-height var(--nav-transition-duration, 300ms) ease-out`,
}}
```

### Premium Hybrid Design

Die Sidebar verwendet jetzt das Premium Hybrid Design:

- **Weiße Sidebar** statt dunkel (`--surface-sidebar`)
- **Gradient Logo** mit Brand Shadow
- **Icon Container** mit aktiven Gradient-Hintergründen
- **Subtile Hover-States** mit Slate-Tönen
- **Item Count Badges** mit Amber-Akzent

### Animation Utilities

Neue CSS-Utilities in `globals.css`:

```css
.animate-in { animation-duration: 150ms; }
.fade-in { animation-name: fadeIn; }
.slide-in-from-left-2 { animation-name: slideInFromLeft; }
```

---

## Phase 3: Favoriten-System (IMPLEMENTED)

### Funktionsweise

Das Favoriten-System ermöglicht es Benutzern, häufig verwendete Menüpunkte als Favoriten zu markieren. Diese erscheinen dann in einer separaten Sektion über den Navigation-Gruppen.

### Implementierte Features

#### LocalStorage-Persistenz (Tenant-isoliert)

```tsx
const FAVORITES_STORAGE_KEY = "pms-nav-favorites";
const FAVORITES_MAX_COUNT = 5;

// Laden aus localStorage
const savedFavorites = localStorage.getItem(FAVORITES_STORAGE_KEY);

// Speichern in localStorage
localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(next));
```

#### Favoriten-Sektion UI

Die Favoriten-Sektion erscheint automatisch, wenn mindestens ein Favorit existiert:

- **Header:** Stern-Icon + "Favoriten" Label + Counter (z.B. "2/5")
- **Items:** Amber-farbene Akzente im aktiven Zustand
- **Remove-Button:** Erscheint bei Hover, entfernt Item aus Favoriten
- **Collapsed Mode:** Nur Stern-Icons, vollständige Links

#### Star-Toggle an Nav-Items

Jedes Nav-Item hat einen Stern-Button:

- **Sichtbarkeit:** Erscheint bei Hover (oder immer wenn bereits Favorit)
- **Gefüllt:** Wenn Item ein Favorit ist (Amber-Farbe)
- **Outline:** Wenn kein Favorit (dezenter grauer Stern)
- **Max-Limit:** Verhindert Hinzufügen wenn 5 Favoriten erreicht

#### Star-Toggle in Flyout-Menüs

Auch in den Flyout-Menüs (Collapsed Mode) können Items favorisiert werden:

- Gleiche Logik wie bei normalen Nav-Items
- Kompakteres Design für Flyout-Kontext

### CSS-Variablen für Favoriten

```css
--interactive-accent-bg: #fef3c7;        /* Favoriten-Hintergrund */
--interactive-accent-text: #d97706;      /* Favoriten-Text (Amber) */
```

### Übersetzungsschlüssel

| Key | Deutsch | English |
|-----|---------|---------|
| `nav.favorites` | Favoriten | Favorites |
| `nav.addToFavorites` | Zu Favoriten hinzufügen | Add to Favorites |
| `nav.removeFromFavorites` | Aus Favoriten entfernen | Remove from Favorites |

### Konfiguration (für Phase 6)

Branding-Option geplant: `enable_favorites: boolean`

---

## Phase 4: Command Palette (IMPLEMENTED)

### Funktionsweise

Die Command Palette ist eine globale Suchfunktion für schnelle Navigation zu allen Seiten.

### Öffnen der Command Palette

- **Keyboard Shortcut:** `⌘K` (Mac) oder `Ctrl+K` (Windows/Linux)
- **Search Button:** In der Sidebar unter dem Brand Header

### Implementierte Features

#### Komponente: `CommandPalette.tsx`

Neue Komponente unter `frontend/app/components/CommandPalette.tsx`:

```tsx
import { CommandPalette, useCommandPalette } from "./CommandPalette";

// In AdminShell:
const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useCommandPalette();

<CommandPalette
  isOpen={isCommandPaletteOpen}
  onClose={() => setIsCommandPaletteOpen(false)}
  favorites={favorites}
/>
```

#### Keyboard Navigation

| Taste | Funktion |
|-------|----------|
| `⌘K` / `Ctrl+K` | Öffnen/Schließen (Toggle) |
| `↑` / `↓` | Navigation durch Ergebnisse |
| `Enter` | Auswahl bestätigen |
| `ESC` | Schließen |

#### Recent Searches (LocalStorage)

```tsx
const RECENT_SEARCHES_KEY = "pms-command-palette-recent";
const MAX_RECENT_SEARCHES = 5;

// Speichern nach Navigation
addToRecent(item.key);
```

#### Sektionen

1. **Favoriten:** Zeigt favorisierte Seiten (Stern-Icon, Amber-Farbe)
2. **Zuletzt besucht:** Letzte 5 besuchte Seiten (Uhr-Icon)
3. **Suchergebnisse:** Gefilterte Ergebnisse bei Texteingabe

#### Integration mit Navigation Items

- Verwendet `NAV_REGISTRY` aus AdminShell
- Respektiert Berechtigungen via `canAccessNavItem`
- Zeigt übersetzte Labels via `useTranslation`

### CSS-Variablen

```css
--palette-backdrop: rgba(0, 0, 0, 0.6);
--palette-bg: #ffffff;
--palette-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
--palette-item-bg-hover: #f8fafc;
```

### Übersetzungsschlüssel

| Key | Deutsch | English |
|-----|---------|---------|
| `commandPalette.search` | Suchen... | Search... |
| `commandPalette.searchPlaceholder` | Seite suchen... | Search pages... |
| `commandPalette.results` | Ergebnisse | Results |
| `commandPalette.noResults` | Keine Ergebnisse gefunden | No results found |
| `commandPalette.recent` | Zuletzt besucht | Recently visited |
| `commandPalette.startTyping` | Tippen zum Suchen... | Start typing to search... |
| `commandPalette.navigate` | Navigieren | Navigate |
| `commandPalette.select` | Auswählen | Select |
| `commandPalette.close` | Schließen | Close |

### Konfiguration (für Phase 6)

Branding-Option geplant: `enable_command_palette: boolean`

---

## Phase 5: Mobile Responsiveness (IMPLEMENTED)

### Überblick

Phase 5 implementiert eine vollständig responsive Mobile-Erfahrung mit nativen Mobile-Patterns.

### Bottom Tab Bar

Die Bottom Tab Bar zeigt die 4 wichtigsten Navigation-Items plus "Mehr"-Button:

```tsx
const BOTTOM_TABS = [
  { key: "dashboard", labelKey: "nav.dashboard", href: "/dashboard", icon: LayoutDashboard },
  { key: "availability", labelKey: "nav.calendar", href: "/availability", icon: Calendar },
  { key: "properties", labelKey: "nav.properties", href: "/properties", icon: Home },
  { key: "guests", labelKey: "nav.contacts", href: "/guests", icon: Users },
];
```

**Features:**
- Fixierte Position am unteren Bildschirmrand
- iOS Safe Area Inset Support (`env(safe-area-inset-bottom)`)
- Aktiver State mit Amber-Hintergrund
- Touch-optimierte Ziele (min. 44px)
- "Mehr"-Button öffnet Mobile Drawer

### Mobile Drawer

Verbesserter Drawer mit Touch-optimiertem Design:

- **Header:** Logo + "Navigation" + Close-Button
- **Search Button:** Öffnet Command Palette
- **Favoriten-Sektion:** Quick Access zu favorisierten Seiten
- **Navigation Groups:** Collapsible mit Star-Toggle für Favoriten
- **User Footer:** Avatar, Name, Rolle, Settings-Link

**Safe Area Support:**
```css
paddingTop: 'env(safe-area-inset-top, 0px)';
paddingBottom: 'calc(12px + env(safe-area-inset-bottom, 0px))';
```

### Mobile Header

Verbesserter Header für mobile Geräte:

- **Links:** Hamburger-Menü + Branding (Logo + Name)
- **Rechts:** Search-Button + Language + Notifications + Profile
- **Safe Area:** Top-Padding für Notch/Dynamic Island

### CSS Utilities (globals.css)

Neue Utility-Klassen für Mobile:

```css
/* Animation für Command Palette */
.slide-in-from-top-4 { ... }

/* Touch-optimierte Active-States */
.touch-active:active {
  transform: scale(0.97);
}

/* iOS Safe Area */
.safe-area-top { padding-top: env(safe-area-inset-top); }
.safe-area-bottom { padding-bottom: env(safe-area-inset-bottom); }
.safe-area-x { ... }

/* Touch-Optimierung */
.no-select { user-select: none; }
.gpu-accelerated { transform: translateZ(0); }
```

### Responsive Breakpoints

| Breakpoint | Bereich | Layout |
|------------|---------|--------|
| Mobile | < 1024px (lg) | Bottom Tab Bar + Drawer |
| Desktop | ≥ 1024px | Sidebar (collapsed/expanded) |

### Übersetzungsschlüssel

| Key | Deutsch | English |
|-----|---------|---------|
| `nav.more` | Mehr | More |

---

## Phasen-Übersicht

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | CSS-Variablen-System | ✅ IMPLEMENTED |
| 2 | Navigation-Komponenten (Collapsible, Icon-Only) | ✅ IMPLEMENTED |
| 3 | Favoriten-System | ✅ IMPLEMENTED |
| 4 | Command Palette | ✅ IMPLEMENTED |
| 5 | Mobile Responsiveness | ✅ IMPLEMENTED |
| 6 | Branding-UI Erweiterung | ✅ IMPLEMENTED |

---

## Phase 6: Branding-UI Erweiterung (IMPLEMENTED)

### Überblick

Phase 6 erweitert die `/settings/branding` Seite um neue Einstellungen für die Premium Hybrid Navigation.

### Neue DB-Felder

Migration: `supabase/migrations/20260226163000_add_branding_nav_behavior.sql`

```sql
-- Navigation Behavior
enable_favorites BOOLEAN DEFAULT true
enable_command_palette BOOLEAN DEFAULT true
enable_collapsible_groups BOOLEAN DEFAULT true
default_sidebar_collapsed BOOLEAN DEFAULT false

-- Gradient Colors
gradient_from TEXT (hex validation)
gradient_via TEXT (hex validation)
gradient_to TEXT (hex validation)

-- Mobile Settings
mobile_bottom_tabs_enabled BOOLEAN DEFAULT true
```

### Backend Schema

Aktualisierte Pydantic-Schemas in `backend/app/schemas/branding.py`:

- `BrandingUpdate` - Akzeptiert alle neuen Felder
- `BrandingResponse` - Gibt alle neuen Felder zurück

### Frontend Branding-Form

Neue UI-Sektionen in `/settings/branding`:

1. **Navigationsverhalten**
   - Toggle: Favoriten-System aktivieren
   - Toggle: Befehlspalette (⌘K) aktivieren
   - Toggle: Einklappbare Gruppen aktivieren
   - Toggle: Sidebar standardmäßig eingeklappt

2. **Gradient-Farben**
   - 3 Color Picker (Start, Mitte, Ende)
   - Live-Vorschau des Gradients
   - Reset-Button für Auto-Ableitung

3. **Mobile-Einstellungen**
   - Toggle: Bottom Tab Bar aktivieren

### Theme Provider

`frontend/app/lib/theme-provider.tsx` wurde erweitert:

1. Interfaces erweitert (`ApiBrandingResponse`, `BrandingConfig`)
2. Neue Felder aus API geladen und in normalizedBranding gespeichert
3. `applyPremiumNavCssVariables()` erhält jetzt die echten Backend-Werte

### AdminShell Integration

`frontend/app/components/admin-shell/AdminShell.tsx` respektiert die Branding-Einstellungen:

| Einstellung | Auswirkung |
|-------------|------------|
| `enable_favorites` | Favoriten-Sektion + Star-Toggles ausgeblendet |
| `enable_command_palette` | Search-Button + ⌘K Shortcut deaktiviert |
| `enable_collapsible_groups` | Gruppen werden fest angezeigt (nicht einklappbar) |
| `default_sidebar_collapsed` | Sidebar startet collapsed wenn kein localStorage-Wert |
| `mobile_bottom_tabs_enabled` | Bottom Tab Bar auf Mobile ausgeblendet |

### Bugfixes (2026-02-26)

Folgende Issues wurden nach dem initialen Phase 6 Release behoben:

| Problem | Lösung |
|---------|--------|
| `enable_collapsible_groups` wirkungslos | AdminShell prüft jetzt die Einstellung |
| `default_sidebar_collapsed` wirkungslos | Neuer useEffect respektiert Branding-Default |
| `font_family` wirkungslos | theme-provider.tsx setzt `--font-family` CSS-Variable |
| Navigation CSS-Variablen nicht synchron | Variable-Namen zwischen theme-provider und AdminShell synchronisiert |
| `ALLOWED_NAV_KEYS` veraltet | Backend-Schema aktualisiert (26 Keys, neue Seiten) |
| Gradient-Reset löscht DB nicht | Leere Werte werden als `null` gesendet |

### Verwendung

```tsx
// Theme Provider liest automatisch aus Branding-API:
const { branding } = useTheme();

// In Komponenten:
{branding?.enable_favorites !== false && (
  <FavoritesSection />
)}
```

---

## Verwendung der CSS-Variablen

### In Tailwind (empfohlen)

```tsx
<div className="bg-[var(--surface-sidebar)] border-[var(--surface-sidebar-border)]">
  <button className="bg-[var(--interactive-subtle-bg)] hover:bg-[var(--interactive-subtle-bg-hover)]">
    Item
  </button>
</div>
```

### In Style-Objekten

```tsx
<aside style={{
  width: 'var(--nav-width-expanded)',
  transition: `width var(--nav-transition-duration) ease-out`
}}>
```

### Mit CSS-Klassen

```css
.nav-item-active {
  background: var(--nav-item-bg-active);
  color: var(--nav-item-text-active);
  box-shadow: var(--nav-item-shadow-active);
}
```

---

## Data-Attribute für Testing

Die Theme Provider setzt folgende Attribute auf `<html>`:

```html
<html
  data-nav-collapsible="true"
  data-nav-favorites="true"
  data-nav-command-palette="true"
  data-nav-icon-only="true"
>
```

Diese können für Feature Detection und Smoke Tests verwendet werden.

---

## Referenz-Dateien

| Datei | Beschreibung |
|-------|-------------|
| `frontend/app/globals.css` | CSS-Variablen-Definitionen |
| `frontend/app/lib/theme-provider.tsx` | Dynamisches Setzen der Variablen |
| `TODO.md` (lokal) | Phasen-Übersicht mit Checkboxen |

---

## Abwärtskompatibilität

Die neuen CSS-Variablen sind **additiv** und brechen keine bestehende Funktionalität:

- Bestehende `--t-*` Tokens bleiben unverändert
- Bestehende `--nav-*` Variablen bleiben unverändert
- Neue Variablen haben Fallback-Werte in globals.css
- `applyPremiumNavCssVariables()` wird mit `null` für noch nicht implementierte Config-Felder aufgerufen
