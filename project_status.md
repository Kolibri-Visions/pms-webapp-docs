# PMS-Webapp Project Status

**Last Updated:** 2026-02-26

**Current Phase:** Phase 27 - Codebase Audit & Logic Bug Fixes Phase 2

---

## Premium Hybrid Navigation - Phase 1+2 (2026-02-26) - IMPLEMENTED

**Scope**: CSS-Variablen-System und Navigation-Komponenten für moderne, responsive Admin-Navigation.

### Phase 1: CSS-Variablen-System

- **globals.css**: 80+ neue CSS-Variablen für Brand Gradient, Surface, Interactive, Navigation-specific, Component-specific (Search, Palette, Flyout), Mobile
- **theme-provider.tsx**: Neue Interfaces (`ApiBrandConfig`, `ApiNavBehavior`) und Funktion `applyPremiumNavCssVariables()` für dynamisches Setzen der Variablen
- **Dark Mode**: Vollständige Overrides für alle neuen Variablen in `[data-theme="dark"]` und `[data-theme="system"]`

### Phase 2: Navigation-Komponenten

- **Flyout-Menüs**: Im collapsed Mode zeigt Hover über Gruppen ein Flyout mit allen Items
- **Item Count Badges**: Jede Gruppe zeigt Anzahl der sichtbaren Items
- **Animierte Transitions**: Smooth Expand/Collapse mit CSS-Variablen-basierter Duration
- **Premium Hybrid Design**: Weiße Sidebar, Gradient Logo, Icon Container mit aktiven Gradients

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/globals.css` | +80 CSS-Variablen, Animation Utilities |
| `frontend/app/lib/theme-provider.tsx` | +2 Interfaces, +2 Funktionen |
| `frontend/app/components/AdminShell.tsx` | Flyouts, Badges, Premium Design |
| `backend/docs/ops/runbook/37-premium-hybrid-navigation.md` | Dokumentation |

### Abwärtskompatibilität

- Alle bestehenden `--t-*` und `--nav-*` Variablen bleiben unverändert
- Neue Variablen haben Fallback-Werte in globals.css
- Keine Breaking Changes

### Verification Path

```bash
# 1. Lokaler Syntax-Check (keine Fehler)
cd frontend && npm run lint

# 2. Build-Test
npm run build

# 3. PROD-Verifikation nach Deploy
# - Browser: Sidebar Collapse/Expand testen
# - Browser: Hover über Gruppe im collapsed Mode → Flyout erscheint
# - Browser: Expand-Gruppen zeigen Item Count Badges
```

### Nächste Phasen

- ~~Phase 3: Favoriten-System~~ ✅
- ~~Phase 4: Command Palette~~ ✅
- ~~Phase 5: Mobile Responsiveness~~ ✅
- ~~Phase 6: Branding-UI Erweiterung~~ ✅

---

## Premium Hybrid Navigation - Phase 3-6 (2026-02-26) - IMPLEMENTED

**Scope**: Favoriten-System, Command Palette, Mobile Responsiveness, Branding-UI Erweiterung.

### Phase 3: Favoriten-System

- **LocalStorage-Persistenz**: Tenant-isoliert via `pms-nav-favorites` Key
- **Favoriten-Sektion**: Erscheint automatisch bei ≥1 Favorit
- **Star-Toggle**: An allen Nav-Items (Hover-State, Amber-Farbe)
- **Max-Limit**: 5 Favoriten (konfigurierbar via FAVORITES_MAX_COUNT)

### Phase 4: Command Palette

- **Komponente**: `frontend/app/components/CommandPalette.tsx`
- **Keyboard Shortcut**: ⌘K (Mac) / Ctrl+K (Windows/Linux)
- **Recent Searches**: LocalStorage-Persistenz (`pms-command-palette-recent`)
- **Sektionen**: Favoriten, Zuletzt besucht, Suchergebnisse
- **Keyboard Navigation**: ↑/↓ + Enter + ESC

### Phase 5: Mobile Responsiveness

- **Bottom Tab Bar**: Fixiert am unteren Rand (< 1024px)
- **Mobile Drawer**: Vollständige Navigation mit Touch UX
- **iOS Safe Area**: `env(safe-area-inset-*)` Support
- **Touch Targets**: Min. 44px, `active:scale-95`

### Phase 6: Branding-UI Erweiterung

- **DB-Migration**: `supabase/migrations/20260226163000_add_branding_nav_behavior.sql`
- **Backend Schema**: `BrandingUpdate` + `BrandingResponse` mit neuen Feldern
- **Branding-Form UI**: Toggles für enable_favorites, enable_command_palette, enable_collapsible_groups, default_sidebar_collapsed
- **Gradient Colors**: 3 Color Picker mit Live-Vorschau
- **Mobile Settings**: Toggle für mobile_bottom_tabs_enabled
- **AdminShell Integration**: Respektiert alle neuen Branding-Einstellungen

### Dateien (Phase 3-6)

| Datei | Änderung |
|-------|----------|
| `frontend/app/components/AdminShell.tsx` | Favorites, Mobile Drawer, Bottom Tabs, Branding Checks |
| `frontend/app/components/CommandPalette.tsx` | Neue Komponente |
| `frontend/app/lib/theme-provider.tsx` | Phase 6 Felder, CSS-Variablen |
| `frontend/app/settings/branding/branding-form.tsx` | Neue UI-Sektionen |
| `backend/app/schemas/branding.py` | Phase 6 Felder |
| `supabase/migrations/20260226163000_add_branding_nav_behavior.sql` | Neue Spalten |

### Verification Path

```bash
# 1. DB-Migration
supabase db diff  # Zeigt neue Spalten

# 2. Frontend Build
cd frontend && npm run build

# 3. PROD-Verifikation
# - /settings/branding: Neue Sektionen vorhanden
# - Toggle "Favoriten-System" deaktivieren → Sterne verschwinden
# - Toggle "Befehlspalette" deaktivieren → ⌘K funktioniert nicht mehr
# - Mobile: Bottom Tab Bar ausblenden via Toggle
```

---

## Branding-Einstellungen Bugfixes (2026-02-26) - IMPLEMENTED

**Scope**: Behebung von 9 Issues in der Branding-UI (`/settings/branding`) - Einstellungen ohne Wirkung und Bugs.

### Behobene Issues

| # | Problem | Lösung |
|---|---------|--------|
| 1 | `enable_collapsible_groups` hatte keine Wirkung | AdminShell.tsx prüft jetzt `branding.enable_collapsible_groups` |
| 2 | `default_sidebar_collapsed` hatte keine Wirkung | Neuer useEffect respektiert Branding-Default wenn kein localStorage |
| 3 | `font_family` hatte keine Wirkung | theme-provider.tsx setzt jetzt `--font-family` CSS-Variable |
| 4 | Nav `hover_text` Farbe wirkungslos | CSS-Variable-Namen synchronisiert (`--nav-item-text-hover`) |
| 5 | Nav `width_pct` wirkungslos | Beide Variable-Namen gesetzt (legacy + premium) |
| 6 | Nav `icon_size_px`/`item_gap_px` wirkungslos | AdminShell nutzt jetzt CSS-Variablen statt hardcoded Werte |
| 7 | Nav-Farbeinstellungen teilweise wirkungslos | Alle CSS-Variablen-Namen zwischen theme-provider und AdminShell synchronisiert |
| 8 | `ALLOWED_NAV_KEYS` veraltet | Backend-Schema aktualisiert (26 Keys statt 24, korrekte Namen) |
| 9 | Gradient-Reset löscht DB-Werte nicht | `handleSubmit` sendet jetzt `null` für leere Gradient-Felder |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/components/AdminShell.tsx` | `isGroupCollapsible` Check, `default_sidebar_collapsed` useEffect, CSS-Variablen |
| `frontend/app/lib/theme-provider.tsx` | `applyFontFamily()`, erweiterte `applyNavCssVariables()` |
| `frontend/app/settings/branding/branding-form.tsx` | Gradient-Reset sendet null |
| `backend/app/schemas/branding.py` | `ALLOWED_NAV_KEYS` aktualisiert |

### Verification Path

```bash
# 1. Frontend Build
cd frontend && npm run build

# 2. Backend Schema Check
cd backend && python3 -c "from app.schemas.branding import ALLOWED_NAV_KEYS; print(len(ALLOWED_NAV_KEYS), 'keys')"
# Erwartet: 26 keys

# 3. PROD-Verifikation
# - /settings/branding: "Einklappbare Gruppen" deaktivieren → Gruppen nicht mehr einklappbar
# - /settings/branding: "Sidebar standardmäßig eingeklappt" aktivieren → localStorage löschen → Sidebar startet collapsed
# - /settings/branding: Font ändern → Text ändert Schriftart
# - /settings/branding: Gradient zurücksetzen + speichern → Gradient wird entfernt
```

---

## Backend Branding API Fix - Phase 6 Felder (2026-02-26) - IMPLEMENTED

**Scope**: Kritischer Bugfix - Backend `/api/v1/branding` Route ignorierte alle Phase 6 Felder.

### Root Cause

Die DB-Migration `20260226163000_add_branding_nav_behavior.sql` fügte 8 neue Spalten hinzu, aber die Backend-Route `branding.py` wurde **nie aktualisiert**:

1. **GET Route** selektierte Phase 6 Spalten nicht aus der DB
2. **PUT Route** hatte keine Handler für Phase 6 Felder
3. **BrandingResponse** Konstruktion populierte Phase 6 Felder nicht

### Auswirkung

- User speicherte Phase 6 Einstellungen → Daten wurden **nie in DB geschrieben**
- GET Route gab nur Schema-Defaults zurück (nicht die gespeicherten Werte)
- Folge: enable_favorites, enable_command_palette, enable_collapsible_groups, default_sidebar_collapsed, gradient_from/via/to, mobile_bottom_tabs_enabled hatten **keine Wirkung**

### Fix

| Stelle | Änderung |
|--------|----------|
| GET SELECT | +8 Phase 6 Spalten |
| GET BrandingResponse | +8 Felder aus row[] |
| PUT Handlers | +8 `if updates.xxx is not None:` Blöcke |
| PUT RETURNING | +8 Phase 6 Spalten |
| PUT BrandingResponse | +8 Felder aus row[] |

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/api/routes/branding.py` | GET/PUT Phase 6 Support |

### Verification Path

```bash
# 1. PROD-Verifikation nach Deploy
# - /settings/branding: "Favoriten-System" deaktivieren → Speichern → Page Reload → Bleibt deaktiviert
# - /settings/branding: "Sidebar eingeklappt" aktivieren → Speichern → Logout → Login → Sidebar startet collapsed
# - /settings/branding: Gradient setzen → Speichern → Sidebar Logo zeigt Gradient
# - API Check: GET /api/v1/branding liefert Phase 6 Felder (nicht mehr null/default)
```

---

## Branding UX Verbesserungen (2026-02-26) - IMPLEMENTED

**Scope**: Navigation und Branding-Einstellungen Bugfixes + UX-Verbesserungen.

### Behobene Issues

| # | Problem | Lösung |
|---|---------|--------|
| 1 | Sidebar-Breite (width_pct) wirkungslos | `--nav-width-expanded` wird jetzt in `applyNavCssVariables()` gesetzt, nicht mehr überschrieben |
| 2 | Sidebar-Hintergrund nicht anpassbar | Neues Feld `nav_bg_color` hinzugefügt (DB, Schema, API, Form, CSS) |
| 3 | Sidebar flackert beim Navigieren | `useState` Initializer liest localStorage synchron statt in useEffect |
| 4 | Suchfeld zu nah am Logo | `paddingTop: 16px` hinzugefügt |
| 5 | Branding-Seite zu schmal | Container von `max-w-2xl` auf `max-w-5xl` erweitert |

### Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260226175739_add_branding_nav_bg_color.sql` | Neue Spalte nav_bg_color |
| `backend/app/schemas/branding.py` | nav_bg_color Feld + Validator |
| `backend/app/api/routes/branding.py` | GET/PUT nav_bg_color Support |
| `frontend/app/lib/theme-provider.tsx` | nav_bg_color → --surface-sidebar, width sync |
| `frontend/app/components/AdminShell.tsx` | Flicker-Fix, Logo-Search-Spacing |
| `frontend/app/settings/branding/branding-form.tsx` | nav_bg_color UI, breiteres Layout |

### Verification Path

```bash
# 1. Sidebar-Breite: /settings/branding → Slider ändern → Sidebar ändert Breite
# 2. Sidebar-Hintergrund: /settings/branding → Sidebar-Hintergrund Farbe setzen → Speichern → Sidebar ändert Farbe
# 3. Flicker-Fix: Zwischen Seiten navigieren → Sidebar bleibt stabil (kein collapse/expand flicker)
# 4. Layout: /settings/branding aufrufen → Seite nutzt mehr Breite
```

---

## Branding Topbar & Body Styling (2026-02-26) - IMPLEMENTED

**Scope**: Einheitliche Gestaltungsoptionen für Topbar und Content-Bereich, Bugfixes, UX-Verbesserungen.

### Neue Features

| Feature | Beschreibung |
|---------|-------------|
| `topbar_bg_color` | Hintergrundfarbe des Topbars (Admin Header) |
| `topbar_border_color` | Rahmenfarbe des Topbars |
| `content_bg_color` | Hintergrundfarbe des Content-Bereichs (Body) |
| Gradient in "Marke"-Tab | Gradient-Farben von "Erweitert" nach "Marke" verschoben |
| `hover_text` UI | Fehlender Color-Picker für Hover-Textfarbe hinzugefügt |

### Behobene Issues

| # | Problem | Lösung |
|---|---------|--------|
| 1 | Topbar verwendete hardcoded Tailwind-Klassen | CSS-Variablen `--surface-header`, `--surface-header-border` |
| 2 | Content-Bereich nicht anpassbar | CSS-Variable `--surface-content` |
| 3 | `hover_text` in Schema aber nicht im UI | Color-Picker in branding-form.tsx hinzugefügt |
| 4 | Gradient in "Erweitert"-Tab versteckt | Nach "Marke"-Tab verschoben |
| 5 | Leerer "Erweitert"-Tab | Tab entfernt (nur noch "Marke" und "Navigation") |
| 6 | Font-Family nicht überall angewendet | `--font-family` CSS-Variable global + inherit-Regel |
| 7 | `width_pct` Label unklar | Label zeigt jetzt `{value}rem ({px}px)` |

### Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260226234133_add_branding_topbar_body_colors.sql` | Neue Spalten |
| `backend/app/schemas/branding.py` | 3 neue Felder + Validator |
| `backend/app/api/routes/branding.py` | GET/PUT für neue Felder |
| `frontend/app/lib/theme-provider.tsx` | CSS-Variablen für Topbar/Content |
| `frontend/app/components/AdminShell.tsx` | Topbar/Content mit CSS-Variablen statt hardcoded |
| `frontend/app/(admin)/settings/branding/branding-form.tsx` | Neue UI-Sektion, Tab-Struktur, Bugfixes |
| `frontend/app/globals.css` | `--font-family` Variable + inherit-Regel |

### Verification Path

```bash
# 1. Topbar-Farbe: /settings/branding → "Topbar & Content" Sektion → Topbar-Hintergrund setzen → Speichern → Topbar ändert Farbe
# 2. Body-Farbe: /settings/branding → Content-Hintergrund setzen → Speichern → Content-Bereich ändert Farbe
# 3. Gradient: /settings/branding → Tab "Marke" → Gradient-Sektion ist sichtbar (nicht mehr in "Erweitert")
# 4. Font: /settings/branding → Schriftart ändern → Speichern → Topbar, Content und Navigation nutzen gleiche Schriftart
# 5. hover_text: /settings/branding → Tab "Navigation" → Sidebar-Farben → "Hover Text" Feld vorhanden
```

---

## Admin Route Group Architektur (2026-02-26) - IMPLEMENTED

**Scope**: Refaktorierung der Frontend-Route-Struktur für stabiles AdminShell-Verhalten.

### Problem

AdminShell wurde bei jeder Navigation zwischen Admin-Seiten neu gemountet, da jede Route ihr eigenes Layout mit AdminShell hatte. Dies verursachte:
- Sidebar-Flicker durch Hydration-Mismatch
- Verlust des Sidebar-States (collapsed, expanded groups, favorites)
- Redundante Auth-Checks (25x pro Session statt 1x)
- Performance-Overhead durch ständiges Remounting

### Lösung

Zentrale `(admin)` Route Group mit einmaligem AdminShell:

```
app/
  (admin)/                    ← Route Group
    layout.tsx                ← AdminShell EINMAL hier
    properties/
      page.tsx
      [id]/
        layout.tsx            ← Nur Tabs (kein AdminShell)
    guests/
      page.tsx
    ...
```

### Änderungen

| Typ | Anzahl | Beschreibung |
|-----|--------|--------------|
| Gelöscht | 22 | Einfache AdminShell-Wrapper-Layouts |
| Aktualisiert | 3 | Authorization-Layouts (ohne AdminShell) |
| Neu | 1 | Zentrales `(admin)/layout.tsx` |
| Import-Fixes | ~50+ | Relative → Absolute Pfade (`@/app/...`) |

### Verification Path

```bash
# Build testen
cd frontend && npm run build
# Erwartung: Build erfolgreich
```

### Dokumentation

- Runbook: `backend/docs/ops/runbook/38-admin-route-group-architecture.md`

---

## Multi-Device Session Tracking (2026-02-26) - VERIFIED

**Scope**: Anzeige und Verwaltung aller aktiven Sitzungen eines Benutzers auf verschiedenen Geräten.

### Problem

Bisher zeigte die Security-Seite (`/profile/security`) nur die aktuelle Sitzung des Geräts an, von dem die Seite aufgerufen wird. Login von einem anderen Gerät (z.B. Handy) wurde nicht als separate Sitzung angezeigt.

**Ursache:** Supabase Auth bietet keine API zum Abrufen aller aktiven Sessions eines Benutzers.

### Lösung

Eigene `user_sessions` Tabelle mit Session-Tracking bei Login/Logout.

### Implementierung

| Phase | Beschreibung | Dateien |
|-------|-------------|---------|
| 1 | DB-Migration mit `user_sessions` Tabelle | `supabase/migrations/20260226100000_add_user_sessions.sql` |
| 2 | RLS Fix + SECURITY DEFINER Funktionen | `supabase/migrations/20260226120000_fix_user_sessions_rls.sql` |
| 3 | IDOR Security Fix | `supabase/migrations/20260226140000_fix_session_functions_idor.sql` |
| 4 | Shared User-Agent Parser | `frontend/app/lib/user-agent.ts` (NEU) |
| 5 | Login: Session erstellen + Cookie setzen | `frontend/app/auth/login/route.ts` |
| 6 | Logout: Session beenden (scope: local) | `frontend/app/auth/logout/route.ts` |
| 7 | Client Logout: Redirect zu Server-Route | `frontend/app/lib/logout.ts` |
| 8 | Sessions API: GET/DELETE mit UUID-Validation | `frontend/app/api/internal/auth/sessions/route.ts` |
| 9 | Middleware: Revoked Session Detection | `frontend/middleware.ts` |
| 10 | Frontend: Revoke-Button aktiviert | `frontend/app/profile/security/page.tsx` |

### Datenbank-Schema

```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY,
    agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    device_type TEXT DEFAULT 'Desktop',
    browser TEXT,
    os TEXT,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    ended_by TEXT,  -- 'user', 'revoked', 'new_login', 'expired'
    is_active BOOLEAN GENERATED ALWAYS AS (ended_at IS NULL) STORED
);
```

### SECURITY DEFINER Funktionen

```sql
-- Beendet einzelne Session mit auth.uid() Validierung
end_user_session(p_session_id UUID, p_user_id UUID, p_ended_by TEXT) → BOOLEAN

-- Beendet alle Sessions mit auth.uid() Validierung
end_all_user_sessions(p_user_id UUID, p_ended_by TEXT) → INTEGER
```

### Datenfluss

```
Login:
[User] → POST /auth/login → [Create user_sessions Record] → [Set pms_session_id Cookie]

Security Page:
[User] → GET /api/internal/auth/sessions → [Query user_sessions WHERE ended_at IS NULL]
       → [Show all sessions, mark current via cookie]

Revoke Session:
[User] → DELETE /api/internal/auth/sessions {session_id}
       → [end_user_session() mit auth.uid() Check]
       → [Anderes Gerät: Middleware erkennt revoked → Redirect zu Logout]

Logout (nur aktuelles Gerät):
[User] → performLogout() → GET /auth/logout
       → [end_user_session()] → [signOut({ scope: 'local' })] → [Clear Cookie]

"Alle Sitzungen beenden":
[User] → DELETE /api/internal/auth/sessions {all_others: true}
       → [end_all_user_sessions()] → [signOut({ scope: 'global' })]
```

### Security Features

| Feature | Implementierung |
|---------|-----------------|
| Cookie Security | `httpOnly`, `secure`, `sameSite='strict'` |
| UUID Validation | Regex-Check vor DB-Queries |
| IDOR Prevention | `auth.uid()` Check in SECURITY DEFINER |
| Revoked Detection | Middleware prüft `ended_at` bei jedem Admin-Request |
| Local Logout | `signOut({ scope: 'local' })` → Nur aktuelles Gerät |
| User-Agent Parser | iOS/iPad vor macOS prüfen (enthält "Mac OS") |

### RLS Policies

- SELECT: Nur eigene Sessions (`user_id = auth.uid()`)
- INSERT: Nur eigene Sessions (`WITH CHECK`)
- UPDATE: Nur eigene Sessions (`WITH CHECK`)

### Commits

```
d00ab68 security: fix IDOR vulnerability in session functions
8026ec5 feat: add session validity check in middleware
159a9ee fix: redirect client logout to server route
e6ba0c9 fix: use local scope in client-side logout utility
6826681 fix: detect iOS/iPad before macOS in user-agent parser
55130ed fix: remove aggressive session cleanup on login
871da89 feat: change logout to local scope
c5bdf9a fix: clean up orphaned sessions on login
8d48dfd fix: use SECURITY DEFINER functions for session management
```

### Verification Path

```bash
# 1. Migrations anwenden (3 SQL-Dateien)
# Supabase Dashboard → SQL Editor

# 2. Login von Desktop → Session in DB erstellt
# 3. Login von Handy → Zweite Session in DB
# 4. Security-Seite → Beide Sessions angezeigt
# 5. Handy abmelden → Desktop bleibt eingeloggt ✓
# 6. Security-Seite → Handy-Session verschwunden ✓
# 7. Session von Desktop revoken → Handy wird bei nächstem Request ausgeloggt ✓
```

**Security Audit:** ✅ Bestanden (2026-02-26)

**Status:** ✅ VERIFIED

**Runbook:** [36-multi-device-sessions.md](./ops/runbook/36-multi-device-sessions.md)

---

## Supabase Auth & Web Vitals Logging Fixes (2026-02-26) - IMPLEMENTED

**Scope**: Behebung von Supabase Security-Warnungen und Web Vitals Log-Spam.

### Übersicht der Fixes

| # | Problem | Ursache | Lösung |
|---|---------|---------|--------|
| S1 | Supabase `getSession()` Warning im Log | `getSession()` validiert JWT nicht serverseitig | `getUser()` vor `getSession()` aufrufen |
| S2 | Web Vitals 422 Fehler | Backend gab `{"agency_id": "None"}` zurück | 404 statt 200 mit null-Wert zurückgeben |
| S3 | Frontend Log-Spam `[WebVitals] Could not determine agency_id` | Warning für jede Metrik auf Admin-Domain | Warning entfernt (erwartetes Verhalten) |
| S4 | Backend Log-Spam `WARNING - Could not resolve agency_id` | WARNING Level für Admin-Domains | Log-Level zu DEBUG reduziert |

### S1: Supabase `getSession()` Security Warning

**Problem:** Supabase loggte Warnung: "Using supabase.auth.getSession() could be vulnerable to session spoofing"

**Ursache:** `getSession()` liest nur Cookies ohne JWT-Validierung. Für Server-Side Auth sollte `getUser()` verwendet werden.

**Lösung:**
1. Neue Helper-Funktion `getValidatedSession()` in `frontend/app/lib/server-auth.ts`
2. Pattern: Erst `getUser()` für JWT-Validierung, dann `getSession()` für `access_token`
3. 33 Dateien aktualisiert (6 Layouts, 26 API Routes, 1 Helper)

**Geänderte Dateien:**
- `frontend/app/lib/server-auth.ts` - Neue `getValidatedSession()` Funktion
- `frontend/app/*/layout.tsx` (6 Dateien) - `getSession()` → `getUser()`
- `frontend/app/api/internal/*/route.ts` (26 Dateien) - Two-step Auth Pattern

### S2: Web Vitals 422 Fehler

**Problem:** Backend gab HTTP 200 mit `{"agency_id": "None"}` zurück wenn Domain nicht gemappt

**Ursache:** `str(None)` in Python wird zu String `"None"`, nicht `null`

**Lösung:** Explizite Prüfung auf `None` und 404-Response in `backend/app/api/routes/public_site.py`

```python
if agency_id is None:
    raise HTTPException(status_code=404, detail="Agency not found for domain")
```

### S3 & S4: Log-Spam Bereinigung

**Problem:** Hunderte Warn-Logs für erwartetes Verhalten (Admin-Domain ohne Agency-Mapping)

**Lösung:**
- Frontend: Warning komplett entfernt (silent OK return)
- Backend: Log-Level von WARNING zu DEBUG in `tenant_domain.py`

### Commits

- `db24d18` - fix: use getUser() for JWT validation before getSession()
- `42ffac9` - fix: return 404 instead of "None" string for unknown agency domains
- `dac6e93` - chore: remove noisy WebVitals warning for admin domains
- `eb8ed38` - chore: reduce tenant_domain log level from warning to debug

### Verification Path

```bash
# 1. Prüfen dass keine getSession Warnings mehr im Frontend Log erscheinen
# Coolify → pms-admin → Logs → Keine "getSession" Warnungen

# 2. Prüfen dass keine 422 Fehler mehr für Web Vitals
# Coolify → pms-admin → Logs → Keine "[WebVitals] Backend returned error: 422"

# 3. Prüfen dass Backend keine WARNING-Spam mehr für tenant_domain
# Coolify → pms-backend → Logs → "Could not resolve agency_id" nur noch auf DEBUG Level
```

**Status:** ✅ IMPLEMENTED

---

## Web Vitals Performance Monitoring (2026-02-25) - IMPLEMENTED

**Scope**: Core Web Vitals Monitoring für Public Websites mit Admin-Dashboard.

### Features

| Feature | Beschreibung |
|---------|-------------|
| Datenerfassung | Automatische Erfassung von LCP, FCP, CLS, FID, INP, TTFB via `sendBeacon` |
| Admin-Dashboard | `/ops/web-vitals` - Aggregierte Metriken mit Rating-Anzeige |
| Langsamste Seiten | Top 5 Seiten nach LCP-Wert |
| Zeitfilter | 24h, 7d, 30d Perioden-Auswahl |
| Auto-Cleanup | Trigger löscht Einträge älter als 30 Tage, max 10.000 pro Agency |

### Architektur

```
[Public Website] → sendBeacon → [Frontend Proxy] → [Backend API] → [Supabase]
                                 /api/internal/      POST /vitals
                                 analytics/vitals    (public, no auth)

[Admin Panel] → apiClient → [Backend API] → [Supabase]
                            GET /vitals/summary
                            (admin only, JWT auth)
```

### Implementierte Komponenten

| Komponente | Datei | Beschreibung |
|------------|-------|--------------|
| DB Migration | `supabase/migrations/20260225110000_add_web_vitals_metrics.sql` | Tabelle + Trigger + RLS |
| RLS Fix | `supabase/migrations/20260225160000_fix_web_vitals_rls.sql` | Public INSERT Policy |
| Backend Routes | `backend/app/api/routes/analytics.py` | POST + GET Endpoints |
| Backend Schemas | `backend/app/schemas/analytics.py` | Pydantic Models |
| Frontend Proxy | `frontend/app/api/internal/analytics/vitals/route.ts` | sendBeacon Proxy |
| Admin UI | `frontend/app/ops/web-vitals/page.tsx` | Dashboard-Seite |
| WebVitals Hook | `frontend/app/components/WebVitals.tsx` | Metric Collection |
| Agency Resolver | `backend/app/api/routes/public_site.py` | `/agency-by-domain` Endpoint |

### Gelöste Probleme (Debugging-Prozess)

| # | Problem | Ursache | Lösung |
|---|---------|---------|--------|
| 1 | 404 auf `/api/v1/analytics/vitals/summary` | Router nicht gemountet bei `MODULES_ENABLED=true` | Failsafe-Mount in `main.py` hinzugefügt |
| 2 | 403 "Not authenticated" | Frontend sendete kein Auth-Token | `accessToken` aus `useAuth()` an apiClient übergeben |
| 3 | Build Error "Property 'token' does not exist" | AuthContextType verwendet `accessToken`, nicht `token` | Variable umbenannt |
| 4 | 500 "NoneType has no attribute 'acquire'" | `get_pool()` gibt None zurück bei Startup | `get_db` Dependency statt `get_pool()` verwenden |
| 5 | 500 "invalid input for query argument $2" | asyncpg benötigt `timedelta` für Interval, nicht String | `timedelta(hours=24)` statt `"24 hours"` |
| 6 | 403 Host Allowlist Check Failed | `/agency-by-domain` wurde von Admin-Domain aufgerufen | Separaten Router ohne Host-Allowlist erstellt |
| 7 | "Database pool not available" Warning | POST Endpoint nutzte `get_pool()` | `get_db` Dependency verwenden |
| 8 | Daten nicht angezeigt (0 Messungen) trotz 144 Einträgen | RLS Policy blockierte SELECT | Permissive SELECT Policy hinzugefügt |
| 9 | Daten immer noch 0 trotz korrekter RLS | `agency_id` Typ-Mismatch (String vs UUID) | `ensure_uuid()` Funktion für Konvertierung |
| 10 | 500 "badly formed hexadecimal UUID string" | JWT enthält kein `agency_id` Claim | `resolve_agency_id()` Funktion mit Auto-Pick aus `team_members` |

### Key Learnings

1. **Supabase JWT enthält kein `agency_id`**: Multi-Tenant Apps müssen Agency aus `team_members` Tabelle auflösen
2. **asyncpg Interval-Type**: PostgreSQL Intervals müssen als `timedelta` übergeben werden, nicht als String
3. **RLS für Backend-Zugriff**: Backend nutzt Service Role Key, aber RLS Policies müssen trotzdem korrekt sein
4. **sendBeacon + Auth**: `sendBeacon` kann keine Auth-Header senden → Public Endpoint erforderlich
5. **Host Allowlist**: Nicht alle Public Endpoints sollen auf bestimmte Domains beschränkt sein

### Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260225110000_*.sql` | NEU - DB Schema |
| `supabase/migrations/20260225160000_*.sql` | NEU - RLS Fix |
| `backend/app/api/routes/analytics.py` | NEU - API Routes |
| `backend/app/schemas/analytics.py` | NEU - Schemas |
| `backend/app/api/routes/public_site.py` | `agency_domain_router` hinzugefügt |
| `backend/app/main.py` | Failsafe Mounts für analytics + agency_domain_router |
| `frontend/app/api/internal/analytics/vitals/route.ts` | NEU - Proxy |
| `frontend/app/ops/web-vitals/page.tsx` | NEU - Admin UI |
| `frontend/app/ops/web-vitals/layout.tsx` | NEU - Auth Layout |
| `frontend/app/components/AdminShell.tsx` | Navigation Link hinzugefügt |

### Verification Path

```bash
# 1. Public Website besuchen (generiert Web Vitals Daten)
curl -I https://www.syltwerker.de/

# 2. Admin Panel → Einstellungen → Performance aufrufen
# Erwartet: Metriken-Karten mit LCP, FCP, CLS, FID, INP, TTFB

# 3. Zeitfilter wechseln (7 Tage, 30 Tage)
# Erwartet: Daten werden aktualisiert

# 4. Backend Logs prüfen
# Erwartet: "Auto-picked agency for user ... " bei GET Request
```

### Commits

- `1c134af` - fix: allow anonymous inserts for web vitals metrics
- `3effc86` - fix: use get_db dependency instead of get_pool()
- `65562da` - fix: use separate router for agency-by-domain
- `eb02d5e` - fix: ensure agency_id is UUID type for web vitals queries
- `b701770` - fix: add agency_id resolution for web vitals endpoint

**Status:** ✅ IMPLEMENTED

**Runbook:** [35-web-vitals-monitoring.md](ops/runbook/35-web-vitals-monitoring.md)

---

## UI Fixes & Cancellation Policy (2026-02-25) - IMPLEMENTED

**Scope**: UI-Verbesserungen und Backend-Fix für Stornierungsregeln.

### Übersicht der Fixes

| # | Problem | Datei | Fix |
|---|---------|-------|-----|
| U1 | Datumsformat ohne führende Nullen (3.1.2026) | `properties/[id]/page.tsx` | `toLocaleString()` mit `day: "2-digit"` |
| U2 | Dashboard-Icon passt nicht zum Branding | `dashboard/page.tsx` | AlertTriangle → Clock Icon |
| U3 | Stornierungsregel wird nicht gespeichert | `property_service.py` | Felder zu `allowed_fields` hinzugefügt |

### U1: Datumsformat mit führenden Nullen

**Vorher:** `3.1.2026 14:5:3`
**Nachher:** `03.01.2026 14:05:03`

**Lösung:** `toLocaleString("de-DE", { day: "2-digit", month: "2-digit", ... })`

### U2: Dashboard-Icon Konsistenz

**Vorher:** AlertTriangle-Icon für "Offene Buchungsanfragen" (wirkt wie Warnung)
**Nachher:** Clock-Icon (passt besser zum Konzept "wartend")

### U3: Stornierungsregel speichern

**Problem:** Bei Property-Edit wurde "Andere vordefinierte verwenden" nicht persistiert.

**Ursachen (3 Fehler):**
1. `cancellation_policy_id` und `use_agency_default_cancellation` fehlten in `allowed_fields` Dictionary
2. `cancellation_policy_id` wurde nicht von String zu UUID konvertiert
3. `cancellation_policy_id` und `use_agency_default_cancellation` fehlten in den SELECT-Queries

**Lösung:**
1. Beide Felder zu `allowed_fields` in `property_service.py` hinzugefügt
2. UUID-Konvertierung für `cancellation_policy_id` (wie bei `owner_id`) + NULL-Handling für leere Strings
3. Beide Felder zu `list_properties` und `get_property` SELECT-Queries hinzugefügt

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/properties/[id]/page.tsx` | `formatDateTime()` mit 2-digit Formatierung |
| `frontend/app/dashboard/page.tsx` | Clock statt AlertTriangle Import/Verwendung |
| `backend/app/services/property_service.py` | allowed_fields, UUID-Konvertierung, SELECT-Queries |

### Verification Path

```bash
# U1: Datumsformat prüfen
# Property-Detail Seite öffnen, Buchungshistorie prüfen

# U2: Dashboard-Icon prüfen
# Dashboard öffnen, "Offene Buchungsanfragen" Karte prüfen

# U3: Stornierungsregel speichern
# Property bearbeiten → Stornierungsregeln → "Andere vordefinierte verwenden" → Speichern → Reload
```

**Commits:**
- `0783ea3` - allowed_fields fix
- `2613266` - UUID conversion fix
- `cce652c` - SELECT queries fix

**Status:** ✅ IMPLEMENTED

---

## Bug Fixes - Kritische Validierungen (2026-02-24) - IMPLEMENTED

**Scope**: Behebung kritischer Bugs aus PMS-Audit (#1, #3-#6).

### Bug #1: Doppelbuchungen (Race Condition)

**Problem**: `update_booking_status()` hatte keinen Advisory Lock. Bei gleichzeitiger Bestätigung zweier Anfragen für dieselben Daten konnte eine Race Condition auftreten.

**Szenario**:
```
Thread 1: inquiry → confirmed (liest Status, validiert, bestätigt)
Thread 2: inquiry → confirmed (liest Status, validiert, bestätigt)
→ Beide sehen "inquiry", beide versuchen zu bestätigen
```

**Lösung**:
- Advisory Lock `pg_advisory_xact_lock` zu `update_booking_status()` hinzugefügt
- Lock wird auf Property-ID gesetzt (serialisiert alle Status-Änderungen pro Property)
- Status wird NACH Lock-Erwerb erneut geprüft (Double-Check Pattern)

**Datei**: `backend/app/services/booking_service.py`

**Vorher**: ⚠️ Teilweise geschützt (nur DB-Constraint)
**Nachher**: ✅ Vollständig geschützt (Lock + Constraint)

### Bug #3: Kurtaxe ignoriert Altersgrenze

**Problem**: `free_under_age` Feld in `visitor_tax_periods` wurde nicht in der Berechnung verwendet.

**Lösung**:
- Neues Feld `children_taxable` in `QuoteRequest` Schema
- Erlaubt explizite Angabe wie viele Kinder über der Altersgrenze sind
- Validator: `children_taxable <= children`

**Dateien**:
- `backend/app/schemas/pricing.py` - Neues Feld + Validator
- `backend/app/api/routes/pricing.py` - Berechnung aktualisiert

### Bug #4: Timezone-naive Datetimes

**Problem**: `datetime.utcnow()` erzeugt naive Timestamps ohne Timezone-Info.

**Lösung**: Alle 30 Vorkommen im gesamten Backend durch `datetime.now(timezone.utc)` ersetzt.

**Betroffene Dateien**:
| Datei | Anzahl |
|-------|--------|
| `backend/app/services/booking_service.py` | 8 |
| `backend/app/api/routes/booking_requests.py` | 14 |
| `backend/app/core/auth.py` | 3 |
| `backend/app/api/routers/channel_connections.py` | 2 |
| `backend/app/services/channel_connection_service.py` | 1 |
| `backend/app/services/guest_service.py` | 1 |
| `backend/app/api/routes/notifications.py` | 1 |

### Bug #5: Fehlende max_guests Validierung

**Problem**: Gästeanzahl wurde nicht gegen `properties.max_guests` validiert.

**Lösung**:
- `max_guests` zu Property-Queries hinzugefügt
- Validierung in `create_booking()` und `update_booking()` implementiert
- Fehlermeldung: "Gästeanzahl (X) überschreitet die maximale Kapazität (Y Gäste)"

**Datei**: `backend/app/services/booking_service.py`

### Bug #6: 0-Nacht-Buchung möglich

**Status**: ✅ Bereits abgesichert

**Analyse**: Pydantic-Validator in `BookingBase` (Zeile 92-98) erzwingt `check_out > check_in`.

### Verification Path

```bash
# Bug #3: Kurtaxe mit children_taxable
curl -X POST "${API}/api/v1/pricing/quote" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"property_id":"...", "check_in":"2026-03-01", "check_out":"2026-03-03", "adults":2, "children":2, "children_taxable":1}'

# Bug #5: Überbuchung sollte 422 Fehler liefern
curl -X POST "${API}/api/v1/bookings" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"property_id":"...", "num_adults":10, "num_children":10}'  # > max_guests
```

**Status**: ✅ IMPLEMENTED

---

## Logic Bug Fixes - Berechnungs- und Validierungsfehler (2026-02-24) - IMPLEMENTED

**Scope**: Behebung von Logikfehlern bei Preis- und Rückerstattungsberechnungen.

### Übersicht der Fixes

| # | Problem | Datei | Fix |
|---|---------|-------|-----|
| L1 | Refund-Berechnung trunciert statt rundet | `booking_service.py` | `ROUND_HALF_UP` verwenden |
| L2 | Preis-Konvertierung (€→Cents) trunciert | `booking_service.py` | `ROUND_HALF_UP` verwenden |
| L3 | Refund auf 0€-Buchung erlaubt | `booking_service.py` | ValidationException werfen |
| L4 | Fee-Berechnung bei fehlenden Werten silent | `pricing_totals.py` | Warnings loggen |

### L1: Refund-Rundungsfehler

**Vorher (falsch):**
```python
refund_amount_cents = int(total_price_cents * refund_percent / 100)
# 9999 × 12% = 1199.88 → int() = 1199 cents
```

**Nachher (korrekt):**
```python
refund_decimal = (Decimal(total_price_cents) * Decimal(refund_percent)) / Decimal("100")
refund_amount_cents = int(refund_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
# 9999 × 12% = 1199.88 → ROUND_HALF_UP = 1200 cents
```

### L2: Preis-Konvertierung

**Vorher:** `int(Decimal(price) * 100)` - trunciert bei 99.995 → 9999
**Nachher:** `quantize(Decimal("1"), rounding=ROUND_HALF_UP)` - rundet zu 10000

### L3: Validierung bei fehlender Buchungssumme

**Neu:** Wenn `total_price_cents = 0`, wird eine `ValidationException` geworfen statt Refund auf 0€ zu berechnen.

### L4: Fee-Berechnungen mit Warnings

**Neu:** Wenn `per_stay`, `per_night` oder `per_person` Fees keine `value_cents` haben, wird ein Warning geloggt statt silent 0 zu berechnen.

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/booking_service.py` | ROUND_HALF_UP Import, Refund/Preis-Rundung, Validierung |
| `backend/app/services/pricing_totals.py` | Fee-Validierung mit Warnings |

**Status**: ✅ IMPLEMENTED

---

## Logic Bug Fixes Phase 2 - Codebase Audit (2026-02-24) - IMPLEMENTED

**Scope**: Umfassende Code-Analyse und Behebung weiterer Logikfehler.

### Übersicht der Fixes

| # | Schweregrad | Problem | Datei | Fix |
|---|-------------|---------|-------|-----|
| K1 | KRITISCH | Commission-Berechnung trunciert | `owners.py:944` | `ROUND_HALF_UP` verwenden |
| K2 | KRITISCH | Altersberechnung falsch (`days // 365`) | `guests.py:185` | Korrekte Datum-basierte Berechnung |
| H1 | HOCH | List.remove() kann ValueError werfen | `registry.py:80` | Existenz-Prüfung vor remove |
| H2 | HOCH | SQL f-Strings statt Parametern | `booking_requests.py` | Parameterisierte Queries |
| H3 | HOCH | Race Condition in update_booking() | `booking_service.py` | Advisory Lock + Double-Check |
| M1 | MITTEL | Type Coercion bei Geldwerten | `owners.py:942-943` | Explizite None-Prüfung |
| N1 | NIEDRIG | Bare Exceptions ohne Logging | 3 Dateien | `as e` + `logger.debug()` |
| N2 | NIEDRIG | Money-Parsing Heuristik fehlerhaft | `money.py` | Robuste Format-Erkennung |

### K1: Commission-Rundungsfehler

**Vorher (falsch):**
```python
commission_cents = int(gross_total_cents * commission_rate_bps / 10000)
# 10001 × 500 / 10000 = 500.05 → int() = 500 cents (sollte 500 sein, aber 500.5 → 501)
```

**Nachher (korrekt):**
```python
commission_decimal = (Decimal(str(gross_total_cents)) * Decimal(str(commission_rate_bps))) / Decimal("10000")
commission_cents = int(commission_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
```

### K2: Altersberechnungsfehler

**Vorher (falsch):**
```python
age = (date.today() - v).days // 365
# 01.01.2000 bis 01.01.2025 = 9131 Tage / 365 = 24 Jahre (FALSCH! Sollte 25 sein)
```

**Nachher (korrekt):**
```python
age = today.year - v.year
if (today.month, today.day) < (v.month, v.day):
    age -= 1  # Geburtstag noch nicht erreicht
```

### H1: Registry Safe Remove

**Vorher:** `.remove()` konnte `ValueError` werfen wenn Element nicht in Liste
**Nachher:** Existenz-Prüfung vor `remove()` + `.pop(key, None)` statt `.pop(key)`

### H2: SQL Parameterisierung

**Vorher (Anti-Pattern):**
```python
where_clauses.append(f"b.status IN ('{DB_STATUS_REQUESTED}', '{DB_STATUS_INQUIRY}')")
```

**Nachher (Best Practice):**
```python
where_clauses.append(f"b.status IN (${param_idx}, ${param_idx + 1})")
params.extend([DB_STATUS_REQUESTED, DB_STATUS_INQUIRY])
param_idx += 2
```

### H3: Race Condition in update_booking()

**Problem:** `update_booking()` prüfte Verfügbarkeit VOR Transaktion. Zwei gleichzeitige Updates konnten beide die Verfügbarkeitsprüfung bestehen, aber überlappende Buchungen erstellen.

**Szenario:**
```
Thread A: Liest Buchung X (01.-05. März)    Thread B: Liest Buchung Y (10.-15. März)
Thread A: check_availability() → OK         Thread B: check_availability() → OK
Thread A: UPDATE X zu 01.-12. März          Thread B: UPDATE Y zu 08.-15. März
→ OVERLAP bei 08.-12. März!
```

**Lösung:**
1. Advisory Lock am Anfang der Transaktion (serialisiert alle Updates pro Property)
2. Double-Check Pattern: Verfügbarkeit wird NACH Lock-Erwerb erneut geprüft

```python
async with self.db.transaction():
    # Lock verhindert parallele Updates
    await self.db.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
        str(current["property_id"])
    )
    # Verfügbarkeit erneut prüfen (andere Transaktion könnte inzwischen geändert haben)
    if dates_changed or status_changed:
        is_available = await self.check_availability(...)
        if not is_available:
            raise ConflictException("Property is already booked")
    # UPDATE durchführen
```

### N1: Bare Exceptions ohne Logging

**Problem:** `except Exception:` ohne `as e` fängt Fehler ab, aber loggt nichts - Debugging wird unmöglich.

**Vorher:**
```python
except Exception:
    return "unknown"  # Was ist passiert? Keine Ahnung!
```

**Nachher:**
```python
except Exception as e:
    logger.debug(f"Frame introspection failed: {e}")
    return "unknown"
```

**Betroffene Dateien:**
- `backend/app/channel_manager/adapters/base_adapter.py` - Connection validation
- `backend/app/core/health.py` - Settings import fallback
- `backend/app/core/database.py` - Frame/URL/Module introspection (3×)

### N2: Money-Parsing Heuristik

**Problem:** `to_decimal()` konnte deutsche Zahlenformate nicht korrekt erkennen.

**Vorher (fehlerhaft):**
```python
# "1.234,56" (German) → wurde nicht unterstützt!
# "1,234" → wurde als 1.234 interpretiert (falsch für US-Tausender)
```

**Nachher (robust):**
```python
# Format-Erkennung basierend auf Position von Komma/Punkt:
# "1.234,56" (DE) → Punkt vor Komma → 1234.56
# "1,234.56" (US) → Komma vor Punkt → 1234.56
# "10,50" → nur Komma, nicht 3 Ziffern → Dezimal → 10.50
# "1,234" → nur Komma, genau 3 Ziffern → Tausender → 1234
```

**Test-Ergebnisse:**
| Eingabe | Erwartet | Ergebnis |
|---------|----------|----------|
| `1.234,56` | 1234.56 | ✅ 1234.56 |
| `1,234.56` | 1234.56 | ✅ 1234.56 |
| `10,50` | 10.50 | ✅ 10.50 |
| `1,234` | 1234 | ✅ 1234 |
| `€ 1.234,56` | 1234.56 | ✅ 1234.56 |

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/api/routes/owners.py` | ROUND_HALF_UP Import, Commission-Berechnung, None-Handling |
| `backend/app/schemas/guests.py` | Korrekte Altersberechnung |
| `backend/app/modules/registry.py` | Safe remove Pattern |
| `backend/app/api/routes/booking_requests.py` | 4× SQL-Parameter statt f-Strings |
| `backend/app/services/booking_service.py` | Advisory Lock + Double-Check in update_booking() |
| `backend/app/channel_manager/adapters/base_adapter.py` | Bare Exception + Logging |
| `backend/app/core/health.py` | Bare Exception + Logging |
| `backend/app/core/database.py` | 3× Bare Exception + Logging |
| `backend/app/core/money.py` | Robuste Format-Erkennung für DE/US Zahlenformate |

**Status**: ✅ IMPLEMENTED

---

## Cancellation Policies - Stornierungsfrist-Logik (2026-02-24) - IMPLEMENTED

**Feature**: Konfigurierbare Stornierungsregeln mit automatischer Rückerstattungsberechnung.

**Navigation**: Unter "Objekte" (nicht "Einstellungen") - Pfad `/cancellation-rules`

### Übersicht

- **Agency-Level**: Custom Regeln (Tage vor Check-in → Rückerstattung%)
- **Property-Level**: Optional eigene Regel oder Agency-Default verwenden
- **Booking-Level**: Automatische Rückerstattungsberechnung bei Stornierung

### Neue Tabelle: `cancellation_policies`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | UUID | Primary Key |
| `agency_id` | UUID | FK zu agencies |
| `name` | VARCHAR(100) | Name der Regel (z.B. "Standard", "Flexibel") |
| `is_default` | BOOLEAN | Ist Default für Agency |
| `rules` | JSONB | Array von `{days_before, refund_percent}` |

### Properties-Erweiterung

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `cancellation_policy_id` | UUID | FK zu cancellation_policies |
| `use_agency_default_cancellation` | BOOLEAN | true = Agency-Default verwenden |

### API Endpoints

| Method | Endpoint | Beschreibung | Rollen |
|--------|----------|--------------|--------|
| GET | `/api/v1/cancellation-policies` | Liste aller Policies | staff+ |
| POST | `/api/v1/cancellation-policies` | Neue Policy erstellen | manager+ |
| GET | `/api/v1/cancellation-policies/{id}` | Policy Details | staff+ |
| PATCH | `/api/v1/cancellation-policies/{id}` | Policy bearbeiten | manager+ |
| DELETE | `/api/v1/cancellation-policies/{id}` | Policy löschen | admin |
| GET | `/api/v1/bookings/{id}/calculate-refund` | Refund berechnen | staff+ |

### Frontend-Seiten

| Seite | Beschreibung |
|-------|--------------|
| `/cancellation-rules` | Stornierungsregeln verwalten (CRUD) - unter "Objekte" in Navigation |
| `/properties` (Create Modal) | Stornierungsregel-Auswahl bei neuen Objekten |
| `/properties/[id]` (Edit Modal) | Abschnitt "Stornierungsregeln" mit Radio-Auswahl |
| `/bookings/[id]` (Cancel Modal) | Automatische Refund-Berechnung mit Override-Option |

### Dateien

| Bereich | Datei | Aktion |
|---------|-------|--------|
| Migration | `supabase/migrations/20260224000000_add_cancellation_policies.sql` | NEU |
| Backend | `backend/app/schemas/cancellation_policies.py` | NEU |
| Backend | `backend/app/schemas/properties.py` | Erweitert |
| Backend | `backend/app/api/routes/cancellation_policies.py` | NEU |
| Backend | `backend/app/api/routes/bookings.py` | calculate-refund Endpoint |
| Backend | `backend/app/services/booking_service.py` | calculate_refund() Methode |
| Frontend | `frontend/app/types/cancellation.ts` | NEU |
| Frontend | `frontend/app/types/property.ts` | Erweitert |
| Frontend | `frontend/app/cancellation-rules/page.tsx` | NEU (CRUD UI) |
| Frontend | `frontend/app/cancellation-rules/layout.tsx` | NEU (Auth-Layout) |
| Frontend | `frontend/app/properties/page.tsx` | Create Modal erweitert |
| Frontend | `frontend/app/properties/[id]/page.tsx` | Edit Modal erweitert |
| Frontend | `frontend/app/bookings/[id]/page.tsx` | Cancel Modal erweitert |
| Frontend | `frontend/app/components/AdminShell.tsx` | Navigation aktualisiert |
| Frontend | `frontend/app/components/Breadcrumb.tsx` | Breadcrumb-Labels |

### Verification Path

```bash
# 1. DB Migration anwenden
supabase db push

# 2. Backend starten und API testen
curl -X POST /api/v1/cancellation-policies \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Standard","is_default":true,"rules":[{"days_before":14,"refund_percent":100},{"days_before":7,"refund_percent":50},{"days_before":0,"refund_percent":0}]}'

# 3. Frontend prüfen
# - /cancellation-rules → Regeln erstellen/bearbeiten (unter "Objekte" in Nav)
# - /properties → Create Modal → Stornierungsregel auswählen
# - /properties/[id] → Edit Modal → Stornierungsregeln-Abschnitt
# - /bookings/[id] → Stornieren → Refund-Berechnung prüfen
```

**Status**: ✅ IMPLEMENTED

---

## Table-to-Card Responsive Pattern - Alle Admin-Listen (2026-02-23) - IMPLEMENTED

**Feature**: Responsive Table-to-Card Pattern gemäß CLAUDE.md §10 auf alle verbleibenden Admin-Listen angewendet.

### Bearbeitete Seiten

| Phase | Seite | Beschreibung |
|-------|-------|--------------|
| 1 | `/extra-services` | Zusatzleistungen mit Checkbox-Selektion |
| 1 | `/guests` | Gästeliste mit VIP/Gesperrt-Badges |
| 1 | `/owners` | Eigentümerliste mit DAC7-Export-Button |
| 1 | `/team` | Teammitglieder + Einladungen (2 Tabellen) |
| 1 | `/seasons` | Saisonvorlagen mit erweiterbaren Perioden |
| 1 | `/bookings` | Buchungsliste mit Status-Badges |
| 2 | `/notifications/email-outbox` | E-Mail Outbox mit Status-Anzeige |
| 2 | `/connections` | Channel-Manager-Verbindungen |
| 2 | `/channel-sync` | Sync-Logs mit Batch-Links |
| 2 | `/website/pages` | Website-Seiten mit Template-Badges |
| 3 | `/ops/modules` | Backend-Module mit Tags/Prefixes |
| 3 | `/ops/audit-log` | Audit-Log mit Aktions-Badges |

### Implementierung

- **Desktop (md+)**: Tabellen-Layout mit `hidden md:block`
- **Mobile (<md)**: Karten-Layout mit `block md:hidden`
- **Breakpoint**: 768px (Tailwind `md`)
- **Actions**: Alle Aktionen in beiden Layouts verfügbar

### Verification Path

```bash
# Responsive-Test: Browser-DevTools → Responsive Mode
# Alle Seiten bei 375px und 1280px Breite prüfen

# Betroffene URLs:
# /extra-services, /guests, /owners, /team
# /seasons, /bookings, /notifications/email-outbox
# /connections, /channel-sync, /website/pages
# /ops/modules, /ops/audit-log
```

**Referenz:** CLAUDE.md §10 - Responsive UI Design Pattern

**Status**: ✅ IMPLEMENTED

---

## Owner DAC7 Compliance & Edit Modal (2026-02-23) - IMPLEMENTED

**Feature**: DAC7-Richtlinie Compliance für Eigentümer (EU-Steuertransparenz) mit vollständigem Edit Modal.

### Änderungen

#### 1. DAC7 Pflichtfelder (Migration)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `tax_id` | TEXT | Steuer-ID (11-stellig für DE) |
| `birth_date` | DATE | Geburtsdatum (DAC7-Pflicht) |
| `vat_id` | TEXT | USt-IdNr. (für Gewerbetreibende) |

#### 2. Banking-Felder (für Auszahlungen)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `iban` | TEXT | IBAN |
| `bic` | TEXT | BIC/SWIFT |
| `bank_name` | TEXT | Bankname |

#### 3. Strukturierte Adresse

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `street` | TEXT | Straße + Hausnummer |
| `postal_code` | TEXT | PLZ |
| `city` | TEXT | Ort |
| `country` | TEXT | Land (ISO 3166-1, Default: DE) |

### Dateien

| Bereich | Datei | Änderung |
|---------|-------|----------|
| Migration | `supabase/migrations/20260223000000_add_owner_dac7_fields.sql` | Neue Spalten |
| Backend | `backend/app/schemas/owners.py` | Schemas erweitert |
| Backend | `backend/app/api/routes/owners.py` | CRUD-Endpoints erweitert |
| Frontend | `frontend/app/types/owner.ts` | TypeScript-Interface erweitert |
| Frontend | `frontend/app/owners/[ownerId]/page.tsx` | Detail-Seite + Edit Modal |

### Owner Edit Modal (Drawer-Style)

- Gleitet von rechts ein (Desktop) / von unten (Mobile)
- Sektionen: Name & Kontakt, Steuer & DAC7, Adresse, Bankverbindung, Provision & Status, Notizen
- PATCH auf `/api/v1/owners/{ownerId}`
- Auto-Refresh nach Speichern

### Verification Path

```bash
# 1. Owner Detail-Seite öffnen
# → /owners/{ownerId} zeigt alle DAC7-Felder

# 2. Edit Modal öffnen
# → "Bearbeiten" Button → Drawer öffnet sich
# → Alle Felder ausfüllen → "Änderungen speichern"

# 3. API-Test
curl -X PATCH "${API}/api/v1/owners/${OWNER_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tax_id": "12345678901",
    "birth_date": "1980-01-15",
    "iban": "DE89370400440532013000"
  }'
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 5: DAC7 Compliance)

**Status**: ✅ IMPLEMENTED

---

## DSGVO Datenexport (Art. 15 Auskunftsrecht) (2026-02-23) - IMPLEMENTED

**Feature**: Eigentümer können alle ihre personenbezogenen Daten exportieren (DSGVO Art. 15).

### Endpoint

`GET /api/v1/owner/me/export`

### Exportierte Daten

| Kategorie | Beschreibung |
|-----------|--------------|
| Stammdaten | Name, E-Mail, Telefon |
| Steuerdaten (DAC7) | tax_id, birth_date, vat_id |
| Adressdaten | street, postal_code, city, country |
| Bankverbindung | iban, bic, bank_name |
| Objektzuweisungen | Alle zugewiesenen Properties |
| Buchungsdaten | Buchungen für eigene Objekte |
| Abrechnungen | Finanzielle Statements |

### Dateien

| Bereich | Datei | Änderung |
|---------|-------|----------|
| Backend Schema | `backend/app/schemas/owners.py` | `OwnerDataExportResponse` + Hilfs-Schemas |
| Backend Route | `backend/app/api/routes/owners.py` | `GET /owner/me/export` Endpoint |

### Query Parameter

- `format=json` (default): JSON-Response
- `format=download`: Datei-Download als `.json`

### Verification Path

```bash
# Als eingeloggter Owner:
curl -X GET "${API}/api/v1/owner/me/export" \
  -H "Authorization: Bearer $OWNER_TOKEN"

# Als Download:
curl -X GET "${API}/api/v1/owner/me/export?format=download" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -o dsgvo_export.json
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 6: DSGVO Datenexport)

**Status**: ✅ IMPLEMENTED

---

## Strukturierte Adress-Migration (2026-02-23) - IMPLEMENTED

**Feature**: Migration von Legacy-`address` Feld zu strukturierten Feldern (street, postal_code, city, country).

### Migrationsskript

**Datei:** `backend/scripts/migrate_owner_addresses.sql`

### Ablauf

1. **Preview** (Step 1): Zeigt betroffene Owners
2. **Parse Preview** (Step 2): Zeigt was geparst würde
3. **Execute** (Step 3): Führt Migration aus (manuell auskommentieren)
4. **Verify** (Step 4): Zeigt Migrationsergebnis

### Unterstützte Formate

- Format A: `"Straße 123, 12345 Stadt"`
- Format B: `"Straße 123\n12345 Stadt"`

### Verification Path

```bash
# In Supabase SQL Editor:
# 1. Öffne backend/scripts/migrate_owner_addresses.sql
# 2. Führe Step 1 + 2 aus (Preview)
# 3. Prüfe Ergebnisse
# 4. Führe Step 3 aus (Migration)
# 5. Führe Step 4 aus (Verify)
```

**Status**: ✅ IMPLEMENTED

---

## GDPR Hard Delete / Anonymisierung (2026-02-23) - IMPLEMENTED

**Feature**: DSGVO Art. 17 - Recht auf Löschung ("Recht auf Vergessenwerden").

### Endpoint

`DELETE /api/v1/owners/{id}/gdpr-delete?confirm=true`

### Was wird anonymisiert

| Kategorie | Felder | Neuer Wert |
|-----------|--------|------------|
| Identität | first_name, last_name | "GELÖSCHT" |
| Kontakt | email | `deleted_xxx@anonymized.local` |
| Kontakt | phone | NULL |
| Adresse | address, street, postal_code, city, country | NULL |
| Steuerdaten | tax_id, vat_id, birth_date | NULL |
| Banking | iban, bic, bank_name | NULL |

### Was bleibt erhalten (Buchhaltung)

- Owner-ID (für Statement-Referenzen)
- commission_rate_bps (historisch)
- Statement-Records (nur Beträge, keine PII)

### Voraussetzungen

1. Owner muss **deaktiviert** sein (erst `DELETE /owners/{id}`)
2. Owner darf **keine Properties** zugewiesen haben
3. Nur **Admin-Rolle** kann ausführen
4. `confirm=true` erforderlich (Sicherheitscheck)

### Verification Path

```bash
# 1. Erst soft-delete
curl -X DELETE "${API}/api/v1/owners/${OWNER_ID}" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. Dann GDPR-Delete
curl -X DELETE "${API}/api/v1/owners/${OWNER_ID}/gdpr-delete?confirm=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 8: GDPR Hard Delete)

**Status**: ✅ IMPLEMENTED

---

## DAC7 XML-Export für Finanzamt (2026-02-23) - IMPLEMENTED

**Feature**: XML-Export im OECD DPI-Format für die Meldung an Finanzbehörden gemäß EU DAC7-Richtlinie.

### Endpoint

`GET /api/v1/dac7/export?year=2025`

### XML-Struktur (OECD DPI Schema)

| Element | Beschreibung |
|---------|--------------|
| `MessageSpec` | Metadaten (SendingEntity, Timestamp, ReportingPeriod) |
| `PlatformOperator` | Agency-Daten (Name, Adresse, Land) |
| `ReportableSeller` | Pro Owner mit Properties und Umsätzen |
| `ImmovableProperty` | Objekt-Typ (DPI903) mit Adressen |
| `Consideration` | Quartalweise Umsätze + Jahressumme |

### Exportierte Owner-Daten

| Kategorie | Felder |
|-----------|--------|
| Identität | first_name, last_name |
| Steuer-ID | tax_id (TIN), vat_id |
| Geburtsdatum | birth_date |
| Adresse | street, postal_code, city, country |

### Finanzielle Daten

- Quartalweise Aufschlüsselung (Q1-Q4)
- Umsatz pro Quartal (in EUR)
- Anzahl Aktivitäten (Buchungen)
- Jahressumme

### Voraussetzungen

1. Nur **Admin-Rolle** kann exportieren
2. Owner muss **is_active = true** sein
3. Owner muss mindestens **ein Property** haben
4. Properties müssen **Buchungen im Berichtsjahr** haben

### Verification Path

```bash
# DAC7 XML-Export für 2025 erstellen
curl -X GET "${API}/api/v1/dac7/export?year=2025" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o DAC7_Report_2025.xml

# XML validieren (Schema-Check)
xmllint --noout DAC7_Report_2025.xml
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 9: DAC7 XML-Export)

**Status**: ✅ IMPLEMENTED

---

## DAC7 Export UI auf /owners (2026-02-23) - IMPLEMENTED

**Feature**: Admin-UI für DAC7 XML-Export direkt auf der Eigentümer-Seite.

### UI-Komponenten

| Element | Beschreibung |
|---------|--------------|
| Export-Button | "DAC7 Export" Button im Header (nur für Admin sichtbar) |
| Modal | Jahr-Auswahl + Info-Box + Download-Button |
| Feedback | Erfolgs-/Fehlermeldungen im Modal |

### Funktionen

- Nur für **Admin-Rolle** sichtbar (`getUserRole(user) === "admin"`)
- Jahr-Dropdown (2024 bis aktuelles Jahr)
- Zeigt Meldefrist an (31. Januar Folgejahr)
- Download als XML-Datei

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/owners/page.tsx` | DAC7 Export Button + Modal |

### Verification Path

```bash
# 1. Als Admin einloggen
# 2. /owners öffnen
# 3. "DAC7 Export" Button klicken
# 4. Jahr auswählen → "XML herunterladen"
```

**Status**: ✅ IMPLEMENTED

---

## Immutable Objekt-ID (internal_name) (2026-02-23) - IMPLEMENTED

**Feature**: `internal_name` (Objekt-ID) ist nach Erstellung unveränderlich.

### Änderungen

- `internal_name` aus `allowed_fields` in `property_service.py` entfernt
- Auto-Generierung bei Erstellung: `OBJ-XXX` Format
- Migration für bestehende Properties mit leerem internal_name

**Dateien:**
- `backend/app/services/property_service.py`
- `backend/scripts/migrate_internal_names.sql`

**Status**: ✅ IMPLEMENTED

---

## Login Redirect zu /dashboard (2026-02-23) - IMPLEMENTED

**Feature**: Nach Login wird zu `/dashboard` statt `/channel-sync` weitergeleitet.

**Datei:** `frontend/app/login/page.tsx`

**Status**: ✅ IMPLEMENTED

---

## Fees/Taxes Umstrukturierung (Template-basiert) (2026-02-21) - IMPLEMENTED

**Feature**: Umstellung der Gebühren-/Steuerverwaltung auf Template-basiertes System. `/gebuehren-steuern` wird zur Agency-Level Template-Verwaltung, Property-Zuweisung erfolgt unter `/properties/[id]/gebuehren`.

### Architektur

| Seite | Zweck |
|-------|-------|
| `/gebuehren-steuern` | Agency-weite Fee/Tax-Templates definieren |
| `/properties/[id]/gebuehren` | Property-spezifische Fees/Templates zuweisen |

### Datenmodell

```
Agency-Template (property_id = NULL)
        ↓ "Zuweisen" = Kopie erstellen
Property-Fee (property_id = {uuid}, source_template_id = {template})
```

- **Fees**: Template + Kopie-Modell (Property bekommt eigene Kopie)
- **Steuern**: Nur Agency-Level (keine Property-spezifischen Steuern)

### Backend-Änderungen

| Datei | Änderung |
|-------|----------|
| `backend/app/schemas/pricing.py` | Neue Schemas: `PricingFeeTemplateResponse`, `AssignFeeFromTemplateRequest` |
| `backend/app/api/routes/pricing.py` | Neue Endpoints (siehe unten) |
| `supabase/migrations/20260221000000_add_pricing_fees_source_template.sql` | Neue Spalte `source_template_id` |

### Neue API Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /api/v1/pricing/fees/templates` | Nur Agency-Templates mit usage_count |
| `DELETE /api/v1/pricing/fees/{fee_id}` | Template löschen (nur wenn nicht verwendet) |
| `GET /api/v1/pricing/properties/{id}/fees` | Property-Fees mit source_template_name |
| `POST /api/v1/pricing/properties/{id}/fees/from-template` | Fee aus Template zuweisen |
| `DELETE /api/v1/pricing/properties/{id}/fees/{fee_id}` | Property-Fee entfernen |

### Frontend-Änderungen

| Datei | Änderung |
|-------|----------|
| `frontend/app/gebuehren-steuern/page.tsx` | Neue Template-Verwaltungsseite (kein Property-Dropdown) |
| `frontend/app/properties/[id]/gebuehren/page.tsx` | Neue Property-Gebühren-Seite |
| `frontend/app/properties/[id]/layout.tsx` | Neuer Tab "Gebühren" |
| `frontend/app/pricing/page.tsx` | Redirect zu `/gebuehren-steuern` |
| `frontend/app/components/AdminShell.tsx` | Navigation: `/pricing` → `/gebuehren-steuern` |

### Features

- **Template-Verwaltung**: Gebühren-Vorlagen auf Agency-Level erstellen
- **"Verwendet in X Objekte"**: Zeigt Usage-Count pro Template
- **Property-Zuweisung**: Templates kopieren oder eigene Gebühren erstellen
- **Quelle-Badge**: "Vorlage" vs "Manuell" auf Property-Seite
- **Table-to-Card**: Responsive Pattern gemäß CLAUDE.md §10
- **Steuern read-only**: Agency-weite Steuern auf Property-Seite anzeigen

### Verification Path

```bash
# 1. Templates-Seite
# → /gebuehren-steuern zeigt nur Agency-Templates
# → Kein Property-Dropdown mehr
# → "Verwendet in X Objekte" Spalte

# 2. Property-Seite
# → /properties/{id}/gebuehren zeigt:
#    - Zugewiesene Templates (mit "Vorlage" Badge)
#    - Property-spezifische Fees (mit "Manuell" Badge)
# → Template zuweisen funktioniert
# → Custom Fee erstellen funktioniert

# 3. Navigation
# → Sidebar zeigt "Gebühren & Steuern" → /gebuehren-steuern
# → /pricing redirected zu /gebuehren-steuern
```

**Status**: ✅ IMPLEMENTED

---

## Properties Table-to-Card Responsive UI (2026-02-21) - IMPLEMENTED

**Feature**: Responsive Table-to-Card Pattern für `/properties` Seite gemäß CLAUDE.md §10.

### Änderungen

| Bereich | Desktop (md+) | Mobile (<md) |
|---------|---------------|--------------|
| Objekt-Liste | Tabelle mit allen Spalten | Kompakte Karten |
| Header | Horizontal mit Buttons | Vertikal, Buttons full-width |
| Pagination | Inline | Gestapelt |
| Aktionen | 3-Dot-Menü | Text-Links im Card-Footer |

**Dateien**: `frontend/app/properties/page.tsx`

**Status**: ✅ IMPLEMENTED

---

## Season-Only Min Stay (2026-02-21) - IMPLEMENTED

**Feature**: Eliminierung von `properties.min_stay` und Umstellung auf `rate_plan_seasons.min_stay_nights` als einzige Quelle für Mindestaufenthalt.

### Fallback-Hierarchie

```
1. rate_plan_seasons.min_stay_nights  (Saison für Check-in-Datum)
   ↓ falls NULL oder keine Saison
2. rate_plans.min_stay_nights         (Rate-Plan Default)
   ↓ falls NULL
3. Hard-Default: 1 Nacht              (kein Minimum)
```

**Status**: ✅ IMPLEMENTED

---

## Rate-Plans Table-to-Card Redesign (2026-02-20) - IMPLEMENTED

**Feature**: Komplettes Redesign der Preiseinstellungen-Seite mit Table-to-Card Pattern.

**Dateien**: `frontend/app/properties/[id]/rate-plans/page.tsx`

**Status**: ✅ IMPLEMENTED

---

## Kurtaxen (Visitor Tax) Management Feature (2026-02-20) - IMPLEMENTED

**Feature**: Verwaltung von Kurtaxen pro Gemeinde mit saisonalen Tarifen und automatischer Property-Zuordnung via PLZ.

### Datenbank-Schema

| Tabelle | Beschreibung |
|---------|--------------|
| `visitor_tax_locations` | Gemeinden mit PLZ-Array für Auto-Matching |
| `visitor_tax_periods` | Saisonale Tarife (Betrag in Cents, Kinder-Freibetrag) |
| `properties.visitor_tax_location_id` | FK für Property-Zuweisung |

**Migration**: `supabase/migrations/20260220000000_add_visitor_tax.sql`

**Route**: `/kurtaxen` (Navigation unter OBJEKTE)

**Runbook**: [31-kurtaxen-visitor-tax.md](./ops/runbook/31-kurtaxen-visitor-tax.md)

**Status**: ✅ IMPLEMENTED

---

## Bookings Filter HTTP 500 Fix (2026-02-20) - IMPLEMENTED

**Problem**: Filtering bookings by status returned HTTP 500 errors.

**Solution**: Field normalization + NULL default handling in `booking_service.py`.

**Status**: ✅ IMPLEMENTED

---

## Luxe Token Elimination (2026-02-20) - IMPLEMENTED

**Objective**: Remove all hardcoded `luxe-*` design tokens and replace with dynamic semantic tokens.

**Deleted**: `app/components/luxe/` folder

**Status**: ✅ IMPLEMENTED

---

## RLS Security Fix (2026-02-24) - IMPLEMENTED

**Issue**: Critical security gap - Multiple tables had no Row Level Security (RLS) enabled, allowing potential cross-tenant data access.

### Phase 1: Initial Fix (8 tables)
**Migration**: `supabase/migrations/20260224120000_add_missing_rls_policies.sql`

| Table | Risk Level |
|-------|------------|
| `owners` | 🔴 CRITICAL |
| `rate_plans` | 🔴 CRITICAL |
| `rate_plan_seasons` | 🔴 CRITICAL |
| `pricing_fees` | 🔴 CRITICAL |
| `pricing_taxes` | 🔴 CRITICAL |
| `availability_blocks` | 🟠 HIGH |
| `inventory_ranges` | 🟠 HIGH |
| `channel_sync_logs` | 🟡 MEDIUM |

### Phase 2: Core Tables Repair (4 tables)
**Migration**: `supabase/migrations/20260224130000_repair_core_rls_policies.sql`

| Table | Risk Level |
|-------|------------|
| `profiles` | 🔴 CRITICAL |
| `properties` | 🔴 CRITICAL |
| `invoices` | 🔴 CRITICAL |
| `payments` | 🔴 CRITICAL |

### Phase 3: Complete Repair (12 tables)
**Migration**: `supabase/migrations/20260224140000_repair_all_missing_rls.sql`

| Table | Risk Level |
|-------|------------|
| `agencies` | 🔴 CRITICAL |
| `bookings` | 🔴 CRITICAL |
| `guests` | 🔴 CRITICAL |
| `team_members` | 🔴 CRITICAL |
| `channel_connections` | 🟠 HIGH |
| `direct_bookings` | 🟠 HIGH |
| `external_bookings` | 🟠 HIGH |
| `pricing_rules` | 🟠 HIGH |
| `webhooks` | 🟠 HIGH |
| `property_media` | 🟡 MEDIUM |
| `sync_logs` | 🟡 MEDIUM |
| `public_site_design` | 🟢 LOW |

**Total Tables Fixed**: 24

### Phase 4: Infinite Recursion Fix
**Migration**: `supabase/migrations/20260224150000_fix_rls_infinite_recursion.sql`

**Problem**: Die RLS Policies referenzierten `team_members` in Subqueries, was zu einer Endlosschleife führte:

```
User → SELECT FROM team_members
  → RLS Policy prüft: SELECT FROM team_members (Subquery)
    → RLS Policy prüft: SELECT FROM team_members (Subquery)
      → ... Endlosschleife
        → ERROR: infinite recursion detected in policy for relation "team_members"
```

**Lösung**: SECURITY DEFINER Funktionen, die RLS umgehen:

```sql
-- Funktion läuft mit Rechten des Erstellers (postgres), nicht des Users
-- Dadurch wird RLS umgangen und keine Rekursion ausgelöst
CREATE FUNCTION get_user_agency_ids()
RETURNS SETOF UUID
SECURITY DEFINER  -- ← Umgeht RLS
AS $$
  SELECT agency_id FROM team_members WHERE user_id = auth.uid();
$$;

-- Policy nutzt jetzt die Funktion statt Subquery
CREATE POLICY "team_members_select" ON team_members
  USING (agency_id IN (SELECT get_user_agency_ids()));
```

**Erstellte Helper-Funktionen**:
| Funktion | Zweck |
|----------|-------|
| `get_user_agency_ids()` | Gibt alle Agency-IDs des Users zurück |
| `user_has_agency_access(UUID)` | Prüft ob User Zugriff auf Agency hat |
| `get_user_role_in_agency(UUID)` | Gibt Rolle des Users in Agency zurück |

**Aktualisierte Policies** (13 Tabellen):
- `team_members`, `agencies`, `bookings`, `guests`
- `properties`, `profiles`, `invoices`, `payments`
- `owners`, `rate_plans`, `pricing_fees`, `pricing_taxes`
- `channel_connections`, `cancellation_policies`

**Warum SECURITY DEFINER?**
- Normale Funktionen laufen mit den Rechten des aufrufenden Users → RLS wird angewandt
- SECURITY DEFINER Funktionen laufen mit den Rechten des Erstellers (postgres) → RLS wird umgangen
- Dies ist der Standard-Ansatz für "Basis-Tabellen" wie `team_members`, die selbst die Quelle für Berechtigungsprüfungen sind

**Policy Pattern**:
- SELECT: Staff can read within agency
- INSERT/UPDATE: Manager+ for config tables, Staff+ for operational tables
- DELETE: Admin only for critical tables

**Verification Path**:
```sql
-- Test Helper-Funktionen:
SELECT get_user_agency_ids();
SELECT get_user_role_in_agency('agency-uuid-here');

-- Alle Tabellen sollten RLS aktiviert haben:
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public'
AND tablename NOT IN ('pms_schema_migrations', 'spatial_ref_sys', 'agency_domains', 'amenity_definitions');
-- Expected: All rows show rowsecurity = true
```

**Status**: ✅ IMPLEMENTED

---

## Redis TLS & PostgreSQL SSL (2026-02-25) - IMPLEMENTED

**Issue**: Redis-Verbindungen waren unverschlüsselt, PostgreSQL SSL war nicht explizit konfiguriert.

**Lösung**: TLS/SSL-Support für Redis und PostgreSQL implementiert.

**Änderungen**:

1. **Redis TLS** (`backend/app/core/redis.py`):
   - `_create_ssl_context()`: SSL-Context-Erstellung für TLS-Verbindungen
   - ConnectionPool akzeptiert nun `ssl` Parameter
   - Logging für TLS-Status

2. **Config** (`backend/app/core/config.py`):
   - `REDIS_TLS_ENABLED`: TLS aktivieren (default: false)
   - `REDIS_TLS_CERT_REQS`: Zertifikat-Validierung (none/optional/required)
   - `REDIS_TLS_CA_CERTS`: Pfad zu CA-Zertifikat

3. **Dokumentation** (`.env.example`):
   - PostgreSQL: `?ssl=require` dokumentiert
   - Redis: `rediss://` Protokoll dokumentiert
   - Celery: TLS-Konfiguration dokumentiert

**Konfiguration (Production)**:
```bash
# PostgreSQL mit SSL
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?ssl=require

# Redis mit TLS
REDIS_URL=rediss://:password@redis-host:6379/0
REDIS_TLS_ENABLED=true
```

**Verification Path**:
- Logs prüfen: `docker logs pms-backend | grep -i "redis.*tls"`
- Health Check: `curl /health/ready` sollte `redis: up` zeigen

**Runbook**: [34-encryption-tls.md](./ops/runbook/34-encryption-tls.md)

**Status**: ✅ IMPLEMENTED

---

## CSP (Content-Security-Policy) (2026-02-25) - IMPLEMENTED

**Issue**: CSP mit Nonces blockierte alle Next.js Scripts, da Next.js 15 keine automatische Nonce-Injection unterstützt.

**Ursprünglicher Ansatz (2026-02-24)**: Nonce-basiertes CSP implementiert.
- Problem: Next.js 15 injiziert Hydration-Scripts ohne Nonce
- Resultat: Public Website komplett blank (alle JS blockiert)

**Aktuelle Lösung (2026-02-25)**: CSP mit `'unsafe-inline'` für script-src.

**Änderungen**:
- `frontend/middleware.ts`: CSP ohne Nonces
  - `script-src 'self' 'unsafe-inline' 'unsafe-eval'` (für Next.js Hydration)
  - `style-src 'self' 'unsafe-inline'`
- `CLAUDE.md`: Sektion 11 aktualisiert

**CSP-Direktiven**:
```
default-src 'self'
script-src 'self' 'unsafe-inline' 'unsafe-eval'
style-src 'self' 'unsafe-inline'
img-src 'self' data: blob: https://*.supabase.co ...
connect-src 'self' https://*.supabase.co ...
frame-ancestors 'none'
form-action 'self'
base-uri 'self'
object-src 'none'
```

**Verbleibende Schutzmaßnahmen**:
- `frame-ancestors 'none'` → Clickjacking-Schutz
- `object-src 'none'` → Flash/Plugin-Schutz
- HSTS, X-Frame-Options, X-Content-Type-Options → Aktiv
- Supabase Auth mit bcrypt → Passwort-Sicherheit

**Warum kein Nonce-CSP mit Next.js 15?**
- Next.js generiert interne Scripts ohne Nonce-Attribut
- `'strict-dynamic'` erfordert, dass initiale Scripts Nonces haben
- Kein offizieller Next.js 15 Support für automatische Nonces

**Status**: ✅ IMPLEMENTED

---

## Security Audit Fixes (2026-02-19) - IMPLEMENTED

**Audit Reference**: Audit-2026-02-19.md

**Resolved**: 12/15 findings (CRITICAL + HIGH vulnerabilities fixed)

**Open**: 3 findings (deferred - Channel Manager not enabled, MVP scope)

**Status**: ✅ IMPLEMENTED

---

## Property Filter Feature (2026-02-14) - IMPLEMENTED

**Overview**: Comprehensive property search and filter system for the public website.

**Features**:
- Filter by city, guests, bedrooms, price range, property type, amenities
- Three layout modes: sidebar, top, modal
- Admin control via `/website/filters`

**Status**: ✅ IMPLEMENTED

---

## Status Semantics

| Status | Bedeutung |
|--------|-----------|
| ✅ IMPLEMENTED | Feature deployed, manual testing completed, docs updated |
| ✅ VERIFIED | IMPLEMENTED + automated production verification passed |

---

## Archiv

Historische Einträge (Phase 1-20, vor 2026-02-14) wurden ausgelagert:

➡️ **[project_status_archive.md](./project_status_archive.md)** - Vollständige Projekthistorie (32.000+ Zeilen)

---

*Last updated: 2026-02-26 (Multi-Device Session Tracking VERIFIED)*
