# 44 - AdminShell Architektur

**Status:** IMPLEMENTIERT (2026-03-03)

**Commits:**
- `b451f61` - nav-config.ts
- `d35de65` - useAdminShellState Hook
- `ab6e8f5` - ProfileDropdown
- `9e2bde9` - SidebarNavigation
- `704722a` - MobileDrawer
- `bf168f8` - TopBar

---

## Übersicht

Die AdminShell-Komponente wurde von einer monolithischen 1979-Zeilen-Datei in modulare Sub-Komponenten aufgeteilt. Ziel war verbesserte Wartbarkeit, Testbarkeit und Code-Organisation.

### Vorher (Monolith)

```
frontend/app/components/
└── AdminShell.tsx (1979 Zeilen)
    - Navigation-Konfiguration
    - State-Management
    - Desktop-Sidebar
    - Mobile-Drawer
    - TopBar
    - ProfileDropdown
    - Layout-Orchestrierung
```

### Nachher (Modular)

```
frontend/app/components/
├── admin-shell/
│   ├── nav-config.ts          (272 Zeilen)
│   ├── hooks/
│   │   └── useAdminShellState.ts (393 Zeilen, vorbereitet)
│   ├── SidebarNavigation.tsx  (837 Zeilen)
│   ├── MobileDrawer.tsx       (461 Zeilen)
│   ├── TopBar.tsx             (202 Zeilen)
│   └── ProfileDropdown.tsx    (227 Zeilen)
└── AdminShell.tsx             (543 Zeilen, orchestriert alles)
```

**Reduktion:** 1979 → 543 Zeilen in AdminShell.tsx (73%)

---

## Komponenten-Beschreibung

### nav-config.ts

Zentrale Navigation-Konfiguration:
- `NAV_GROUPS` - Alle Navigationsgruppen mit Items
- `LANGUAGES` - Sprachoptionen (DE/EN)
- `BOTTOM_TABS` - Mobile Bottom-Navigation
- `NavItem`, `NavGroup` TypeScript-Interfaces
- Helper: `getAllNavItems()`, `computeNavItems()`, `getOrderedNavItems()`

### useAdminShellState.ts (Hook)

Konsolidierte State-Logik (vorbereitet, noch nicht integriert):
- Alle `useState` Hooks
- localStorage-Sync (isCollapsed, favorites, expandedGroups)
- Hydration-State-Pattern für SSR
- Branding-Defaults-Anwendung

### SidebarNavigation.tsx

Desktop-Sidebar-Komponente:
- Collapsible Groups mit Animation
- Flyout-Menüs bei collapsed State
- Favorites-Sektion mit Star-Toggle
- Group-Item-Count-Badges
- Search-Button (CommandPalette-Trigger)
- ARIA-Labels für Accessibility

### MobileDrawer.tsx

Mobile Navigation-Drawer:
- Slide-in Animation
- Backdrop mit Klick-to-Close und Blur
- Navigation-Items und Favorites
- Collapsible Groups
- Profile-Info und Settings-Link
- iOS Safe Area Support (env(safe-area-inset-*))
- Full ARIA Accessibility (role="dialog", aria-modal)

### TopBar.tsx

Header-Leiste:
- Mobile Menu Button (Hamburger)
- Mobile Search Button
- Language-Switcher Dropdown mit Flaggen
- Notification Buttons (Messages, Alerts)
- ProfileDropdown Integration

### ProfileDropdown.tsx

Benutzer-Menü:
- Avatar mit Fallback-Initialen
- Links zu Profil, Sicherheit, Organisation
- Logout-Button mit Loading-State
- Impersonation-Info (wenn aktiv)
- ARIA-Attribute für Accessibility

---

## State-Management

### localStorage-Persistenz

| Key | Beschreibung | Scope |
|-----|--------------|-------|
| `pms-sidebar-collapsed` | Sidebar ein/ausgeklappt | Global |
| `pms-favorites-{tenantId}` | Favoriten-Liste | Tenant-spezifisch |
| `pms-nav-expanded-groups` | Ausgeklappte Gruppen | Global |

### Hydration-Pattern

Um SSR/Client-Mismatches zu vermeiden:

```tsx
const [isHydrated, setIsHydrated] = useState(false);
const [isCollapsed, setIsCollapsed] = useState(() => {
  // Synchroner Initialwert für SSR
  if (typeof window === 'undefined') return true;
  return localStorage.getItem('pms-sidebar-collapsed') === 'true';
});

useEffect(() => {
  // Client-seitige Korrektur nach Hydration
  setIsCollapsed(localStorage.getItem('pms-sidebar-collapsed') === 'true');
  setIsHydrated(true);
}, []);
```

---

## Branding-Integration

Alle Komponenten respektieren die Branding-CSS-Variablen:

| Variable | Komponente | Verwendung |
|----------|------------|------------|
| `--surface-sidebar` | SidebarNavigation, MobileDrawer | Hintergrundfarbe |
| `--surface-header` | TopBar | Header-Hintergrund |
| `--brand-gradient` | Alle | Active-State Hintergrund |
| `--brand-shadow` | Alle | Active-State Schatten |
| `--nav-transition-duration` | Alle | Animationsgeschwindigkeit |

---

## ARIA Accessibility

Implementierte Accessibility-Features:

| Feature | Komponenten |
|---------|-------------|
| `role="navigation"` | SidebarNavigation |
| `role="dialog"` + `aria-modal` | MobileDrawer |
| `aria-expanded` | Collapsible Groups |
| `aria-label` | Alle interaktiven Elemente |
| `aria-current="page"` | Active Nav-Items |
| `aria-haspopup` + `aria-controls` | Dropdowns |

---

## Troubleshooting

### Sidebar springt beim Seitenwechsel

**Symptom:** Sidebar ändert Breite kurz beim Navigieren

**Ursache:** Hydration-Mismatch (Server: collapsed, Client: expanded)

**Lösung:** `isHydrated` Pattern verwenden - Transition erst aktivieren wenn hydrated

### Favorites werden nicht gespeichert

**Symptom:** Favorites verschwinden nach Refresh

**Ursache:** localStorage-Key enthält keine Tenant-ID

**Prüfen:**
```javascript
// Browser DevTools Console
localStorage.getItem('pms-favorites-' + tenantId)
```

### Flyout-Menü schließt sofort

**Symptom:** Flyout bei collapsed Sidebar schließt beim Hover

**Ursache:** Mouse-Leave wird zu früh getriggert

**Lösung:** `onMouseEnter`/`onMouseLeave` auf Container UND Flyout setzen

---

## Dateipfade

| Komponente | Pfad |
|------------|------|
| AdminShell | `frontend/app/components/admin-shell/AdminShell.tsx` |
| nav-config | `frontend/app/components/admin-shell/nav-config.ts` |
| SidebarNavigation | `frontend/app/components/admin-shell/SidebarNavigation.tsx` |
| MobileDrawer | `frontend/app/components/admin-shell/MobileDrawer.tsx` |
| TopBar | `frontend/app/components/admin-shell/TopBar.tsx` |
| ProfileDropdown | `frontend/app/components/admin-shell/ProfileDropdown.tsx` |
| useAdminShellState | `frontend/app/components/admin-shell/hooks/useAdminShellState.ts` |
