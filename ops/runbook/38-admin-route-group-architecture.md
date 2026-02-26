# 38 - Admin Route Group Architektur

> **Status:** ✅ IMPLEMENTED (2026-02-26)
> **Scope:** Frontend-Architektur, Next.js App Router

---

## Übersicht

Die Admin-Routen wurden in eine zentrale Route Group `(admin)` verschoben. AdminShell wird jetzt **einmal** im zentralen Layout gemountet und bleibt bei Navigation zwischen Admin-Seiten stabil.

---

## Vorher (Problem)

```
app/
  properties/
    layout.tsx      ← AdminShell hier
  guests/
    layout.tsx      ← AdminShell hier (DUPLIZIERT)
  bookings/
    layout.tsx      ← AdminShell hier (DUPLIZIERT)
  ... (25 weitere)
```

**Probleme:**
- AdminShell wurde bei jeder Navigation neu gemountet
- Sidebar-Flicker durch Hydration-Mismatch
- 25x duplizierter Auth-Check
- Performance-Overhead durch Remounting

---

## Nachher (Lösung)

```
app/
  layout.tsx                    ← Root Layout (Fonts, Providers)
  (public)/
    layout.tsx                  ← Public Website Layout
  (admin)/
    layout.tsx                  ← ZENTRALES AdminShell
    properties/
      page.tsx
      [id]/
        layout.tsx              ← Property-Tabs (kein AdminShell)
    guests/
      page.tsx
    bookings/
      page.tsx
    settings/
      branding/
        layout.tsx              ← Nur Autorisierung (kein AdminShell)
    ...
```

**Vorteile:**
- AdminShell bleibt bei Navigation stabil (kein Flicker)
- Sidebar-State wird zwischen Seiten beibehalten
- Einmaliger Auth-Check pro Session
- Bessere Performance (kein Remounting)

---

## Struktur der Layouts

### 1. Zentrales Admin Layout
**Datei:** `app/(admin)/layout.tsx`

- Enthält AdminShell
- Macht Auth-Check via `getAuthenticatedUser()`
- Alle Admin-Routen erben dieses Layout

### 2. Einfache Routen (ohne eigenes Layout)
**Beispiel:** `app/(admin)/guests/page.tsx`

- Kein eigenes `layout.tsx`
- Erbt AdminShell vom Parent

### 3. Routen mit UI-spezifischem Layout
**Beispiel:** `app/(admin)/properties/[id]/layout.tsx`

- Hat Tab-Navigation
- Kein AdminShell (erbt vom Parent)
- Nur route-spezifische UI

### 4. Routen mit Autorisierung
**Beispiel:** `app/(admin)/settings/branding/layout.tsx`

- Prüft Rolle (admin/manager)
- Zeigt "Zugriff verweigert" wenn nicht autorisiert
- Kein AdminShell-Wrapper (erbt vom Parent)

---

## Betroffene Dateien

### Gelöschte Layouts (22 Dateien)
Alle einfachen AdminShell-Wrapper-Layouts wurden entfernt:
- `amenities/layout.tsx`
- `availability/layout.tsx`
- `booking-requests/layout.tsx`
- `bookings/layout.tsx`
- `channel-sync/layout.tsx`
- `connections/layout.tsx`
- `dashboard/layout.tsx`
- `fees-taxes/layout.tsx`
- `guests/layout.tsx`
- `notifications/email-outbox/layout.tsx`
- `ops/layout.tsx`
- `organization/layout.tsx`
- `owners/layout.tsx`
- `pricing/layout.tsx`
- `profile/layout.tsx`
- `properties/layout.tsx`
- `seasons/layout.tsx`
- `settings/billing/layout.tsx`
- `settings/roles/layout.tsx`
- `team/layout.tsx`
- `visitor-tax/layout.tsx`
- `website/layout.tsx`

### Aktualisierte Layouts (3 Dateien)
AdminShell-Wrapping entfernt, Autorisierung beibehalten:
- `settings/branding/layout.tsx`
- `extra-services/layout.tsx`
- `cancellation-rules/layout.tsx`

### Unveränderte Layouts (1 Datei)
- `properties/[id]/layout.tsx` - Hatte nie AdminShell, zeigt nur Tabs

### Neues Layout (1 Datei)
- `(admin)/layout.tsx` - Zentrales AdminShell Layout

---

## Import-Pfad-Änderungen

Nach der Verschiebung in `(admin)/` waren relative Imports kaputt. Alle wurden zu absoluten Pfaden geändert:

```typescript
// Vorher (kaputt nach Verschiebung)
import { useAuth } from "../../lib/auth-context";

// Nachher
import { useAuth } from "@/app/lib/auth-context";
```

**Betroffene Import-Kategorien:**
- `@/app/lib/*` (auth-context, api-client, config, i18n, theme-provider, ops-utils)
- `@/app/components/*` (AdminShell, BackofficeLayout, ui/*)
- `@/app/types/*` (alle Type-Definitionen)
- `@/app/lib/contexts/*` (PermissionContext)

---

## Verification Path

```bash
# Build testen
cd frontend && npm run build

# Erwartetes Ergebnis: Build erfolgreich ohne Fehler
```

---

## Bekannte Einschränkungen

1. **Doppelter Auth-Check in Autorisierungs-Layouts**
   - `settings/branding`, `extra-services`, `cancellation-rules` machen eigenen Auth-Check
   - Das zentrale Layout macht bereits Auth-Check
   - Könnte in Zukunft optimiert werden

2. **x-pathname Header**
   - Das zentrale Layout nutzt `x-pathname` Header für Login-Redirect
   - Middleware muss diesen Header setzen (bereits implementiert)

---

## Rollback

Falls Probleme auftreten:
1. Git revert zum Commit vor der Refaktorierung
2. Oder: Route Group `(admin)` löschen und Ordner zurück nach `app/` verschieben

---

*Erstellt: 2026-02-26*
