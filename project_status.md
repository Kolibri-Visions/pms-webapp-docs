# PMS-Webapp Project Status

**Last Updated:** 2026-03-02

**Current Phase:** CMS Upgrade Roadmap - Phase 8 (Performance & Polish) ✅ COMPLETE

---

## Organisations-Kontaktdaten & Topbar-Erweiterung (2026-03-02) — IMPLEMENTED

**Scope**:
1. Organisation-Seite um Telefon, Adresse und Social Media Links erweitern
2. Topbar-Konfiguration mit individuellen Social Media Items und Layout-Optionen
3. **Fix**: Tenant-Resolution für Server-Side Fetches

### Problem (vorher)

1. Die Organisation-Seite (`/organization`) hatte nur Name und E-Mail - keine Telefon, Adresse oder Social Media Links
2. Die Topbar zeigte alle Social Media Links als Block - keine individuelle Steuerung
3. Kontaktdaten waren in `public_site_settings` und `agencies` dupliziert
4. **Bug**: Server-Side Fetches sendeten keinen Host-Header → Backend konnte Tenant nicht auflösen

### Lösung (nachher)

#### 1. Organisation als Single Source of Truth

| Feld | Tabelle | Beschreibung |
|------|---------|--------------|
| `phone` | `agencies` | Telefonnummer |
| `address` | `agencies` | Vollständige Adresse |
| `social_links` | `agencies` | JSONB mit Social Media URLs |

Die Public Website liest diese Daten jetzt aus der `agencies` Tabelle (JOIN).

#### 3. Fix: Tenant-Resolution für Server-Side Rendering

Das Problem: Wenn Next.js Server-Side fetches an das Backend macht, geht der Request an `api.fewo.kolibri-visions.de` statt an die Public-Domain `fewo.kolibri-visions.de`. Das Backend konnte daher den Tenant nicht aus dem Host-Header auflösen.

**Lösung**: Die API-Helpers in `api.ts` lesen jetzt den Original-Host aus dem eingehenden Request (`headers()`) und senden ihn als `x-public-host` Header an das Backend weiter.

#### 2. Erweiterte Topbar-Konfiguration

| Funktion | Beschreibung |
|----------|--------------|
| **Individual Social Items** | `social_facebook`, `social_instagram`, `social_twitter`, `social_youtube`, `social_linkedin` |
| **Layout: Gap** | Abstand zwischen Elementen: `sm` (16px), `md` (24px), `lg` (32px) |
| **Layout: Gruppen** | Jedes Element kann in `left`, `center` oder `right` Gruppe platziert werden |
| **Separator** | Optionale Trennlinie zwischen Gruppen |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260302000000_add_topbar_config.sql` | GEÄNDERT: gap, individuelle Social Items |
| `supabase/migrations/20260302120000_add_agency_contact_fields.sql` | NEU: address, social_links für agencies |
| `supabase/migrations/20260302140000_add_topbar_item_groups.sql` | NEU: group Feld für Topbar-Items (left/center/right) |
| `backend/app/schemas/epic_a.py` | GEÄNDERT: AgencyResponse/UpdateRequest mit neuen Feldern |
| `backend/app/api/routes/epic_a.py` | GEÄNDERT: GET/PATCH mit phone, address, social_links |
| `backend/app/api/routes/public_site.py` | GEÄNDERT: JOIN mit agencies für Kontaktdaten |
| `backend/app/schemas/public_site.py` | GEÄNDERT: TopbarConfig mit gap, alignment, neue Item-Typen |
| `frontend/app/types/organisation.ts` | NEU: SOCIAL_PLATFORMS, SocialLinks Interface |
| `frontend/app/(admin)/organization/page.tsx` | GEÄNDERT: Erweitertes Bearbeitungsformular |
| `frontend/app/(public)/context/DesignContext.tsx` | GEÄNDERT: TopbarItemType mit Social-Plattformen |
| `frontend/app/(public)/components/HeaderClient.tsx` | GEÄNDERT: Rendering für individuelle Social Items |
| `frontend/app/(admin)/website/design/design-form.tsx` | GEÄNDERT: Layout-Optionen im TopbarEditor |
| `frontend/app/(public)/lib/api.ts` | GEÄNDERT: Tenant-Resolution via x-public-host Header |

### Datenstruktur

```typescript
// agencies Tabelle
interface Agency {
  phone: string | null;
  address: string | null;
  social_links: {
    facebook?: string;
    instagram?: string;
    twitter?: string;
    youtube?: string;
    linkedin?: string;
    // ...
  };
}

// TopbarConfig
interface TopbarConfig {
  visible: boolean;
  bg_color: string | null;
  text_color: string | null;
  gap: "sm" | "md" | "lg";
  items: TopbarItem[];
}

// TopbarItem
interface TopbarItem {
  id: string;
  type: TopbarItemType;
  visible: boolean;
  position: number;
  group: "left" | "center" | "right";  // Platzierung
  // ...
}
```

### Verification Path

```bash
# 1. Migrationen anwenden
psql -c "SELECT phone, address, social_links FROM agencies LIMIT 1;"
# Erwartung: Neue Spalten vorhanden

# 2. Organisation-Seite testen
# /organization → Bearbeiten → Telefon, Adresse, Social Links editierbar

# 3. Topbar-Editor testen
# /website/design → Topbar → Layout-Optionen (Gap, Ausrichtung) sichtbar
# Individuelle Social-Plattform Items (Facebook, Instagram, etc.)

# 4. Public Website testen
# Nach Deploy: Topbar sollte Telefon + Social Icons anzeigen
# Test: curl -H "x-public-host: fewo.kolibri-visions.de" https://api.fewo.kolibri-visions.de/api/v1/public/site/settings
# Erwartung: phone, social_links sind befüllt
```

**Status:** ✅ IMPLEMENTED

---

## Multiple Root Layouts — SSR Public Website (2026-03-01) — IMPLEMENTED

**Scope**: Root Layout (`app/layout.tsx`) aufgelöst in 4 eigenständige Root Layouts per Route Group für echtes HTML-SSR auf der Public Website.

### Problem (vorher)

Das globale Root Layout wrappte ALLE Routen in `<Providers>` (`"use client"`), was HTML-SSR für die gesamte App verhinderte. Der `<body>` enthielt nur RSC Flight Payload Scripts statt echtem HTML. Zusätzlich hatte die Public Website `<html lang="en">` (falsch) und den Admin-Titel "PMS Channel Sync Console".

### Lösung (nachher)

| Route Group | Root Layout | Providers | Rendering |
|-------------|-------------|-----------|-----------|
| `(public)` | `<html><body>` + DesignProvider | KEINE globalen Providers | SSR/ISR (echtes HTML) |
| `(admin)` | `<html><body>` + Providers + AdminShell | Auth, Permission, Language, Theme | Dynamic (Client) |
| `(auth)` | `<html><body>` minimal | KEINE | Dynamic |
| `(owner)` | `<html><body>` + Providers | Auth, Permission, Language, Theme | Dynamic (Client) |

### Geänderte Dateien

| Datei | Aktion |
|-------|--------|
| `app/fonts.ts` | NEU — Shared Font-Instanz für alle Layouts |
| `app/(public)/layout.tsx` | GEÄNDERT — `<html lang="de"><body>` hinzugefügt, OHNE Providers |
| `app/(admin)/layout.tsx` | GEÄNDERT — `<html lang="de"><body>` + Providers + Metadata hinzugefügt |
| `app/(auth)/layout.tsx` | NEU — Minimales Root Layout für Login |
| `app/(owner)/layout.tsx` | NEU — Root Layout mit Providers für Owner Portal |
| `app/layout.tsx` | GELÖSCHT — Ersetzt durch 4 eigenständige Root Layouts |
| `app/login/` → `app/(auth)/login/` | VERSCHOBEN |
| `app/owner/` → `app/(owner)/owner/` | VERSCHOBEN |
| `app/(public)/components/BlockRenderer.tsx` | FIX — DOMPurify server-safe gemacht |

### Bonus-Fixes (automatisch durch die Trennung)

- `<html lang="en">` → `<html lang="de">` (SEO-Korrektur)
- `title: "PMS Channel Sync Console"` nur noch auf Admin, nicht mehr auf Public
- Public JS-Bundle ~50% kleiner (keine Auth/Permission/Theme Provider)
- DOMPurify server-safe fix für Static Build

### Verification Path

```bash
# 1. Build muss durchlaufen
cd frontend && npm run build
# Erwartung: rc=0, keine "Missing root layout" Warnings

# 2. Public Website — muss echtes HTML enthalten
curl -s https://fewo.kolibri-visions.de/ | grep -o '<header\|<nav\|<footer\|<main'
# Erwartung: HTML-Elemente gefunden

# 3. lang-Attribut korrekt
curl -s https://fewo.kolibri-visions.de/ | grep -o 'lang="[^"]*"' | head -1
# Erwartung: lang="de"

# 4. Login funktioniert
curl -s https://admin.fewo.kolibri-visions.de/login | grep -o '<form\|<input'
```

---

## Public Layout SSR - Server-Side Rendering für Header/Footer (2026-03-01) - IMPLEMENTED

**Scope**: Public Website Layout von Client Component (`"use client"`) zu Server Component umgebaut, damit Header, Navigation und Footer als echtes HTML im SSR-Response enthalten sind.

### Problem (vorher)

Das gesamte Public Layout war ein Client Component mit `useEffect`-basiertem Datenfetching. Der Server lieferte nur leere `<body>`-Tags mit React-Hydration-Scripts. Crawler und Browser sahen keinen Inhalt bis JavaScript geladen und ausgeführt war.

### Lösung (nachher)

| Komponente | Vorher | Nachher |
|------------|--------|---------|
| `layout.tsx` | `"use client"` + `useEffect` fetch | Server Component + `async/await` fetch |
| Header | Im Layout (client) | Eigene `HeaderClient.tsx` (nur Interaktivität) |
| Footer | Im Layout (client) | Eigene `FooterServer.tsx` (rein Server) |
| `SiteSettings` | Lokales Interface im Layout | Exportiert aus `lib/api.ts` |
| `fetchSiteSettings()` | Nur `{ site_name }` | Vollständiges `SiteSettings`-Interface mit Fallback-Defaults |
| Design-Tokens | Client-Fetch per `useEffect` | Server-Fetch per `fetchDesign()` |

### Geänderte Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(public)/layout.tsx` | Server Component, kein `"use client"` mehr |
| `frontend/app/(public)/lib/api.ts` | `SiteSettings` Interface + `defaultSiteSettings` + erweiterte `fetchSiteSettings()` |
| `frontend/app/(public)/components/HeaderClient.tsx` | NEU: Client Component nur für Mobile-Menu + Scroll-Detection |
| `frontend/app/(public)/components/FooterServer.tsx` | NEU: Server Component für Footer-Rendering |

### Architektur

```
Server Component (layout.tsx)
  ├── fetchSiteSettings() ─── server-side, cached 5 min
  ├── fetchDesign() ───────── server-side, cached 1 min
  ├── HeaderClient ─────────── "use client" (useState, useEffect)
  │   ├── Mobile menu toggle
  │   └── Scroll detection (sticky shadow)
  ├── DesignProvider ────────── "use client" (Context für Kinder)
  │   └── children (Seiten-Content)
  └── FooterServer ─────────── Server Component (kein JS)
```

### Verification Path

```bash
# 1. SSR HTML prüfen - View Source sollte Header/Nav/Footer zeigen
curl -s https://fewo.example.com | grep -o '<header[^>]*>' | head -1
curl -s https://fewo.example.com | grep -o '<footer[^>]*>' | head -1

# 2. Navigation im SSR-HTML sichtbar
curl -s https://fewo.example.com | grep 'Unterkünfte'

# 3. Build prüft Kompilation (lokal verifiziert, rc=0)
cd frontend && npx next build
```

---

## German Translation Fixes - Website Admin UI (2026-03-01) - IMPLEMENTED

**Scope**: Englische Texte und Variablen-Namen durch deutsche Bezeichnungen ersetzt.

### Änderungen

| Datei | Fix |
|-------|-----|
| `design-form.tsx` | Logo (Hell/Dunkel), Fixierter Header statt Sticky Header |
| `templates/page.tsx` | Block-Vorlagen, Neue Vorlage, korrigierte Umlaute |
| `navigation/page.tsx` | placeholder "Bezeichnung" statt "Label" |
| `filters/page.tsx` | placeholder "Filtername" statt "Filter" |
| `pages/[id]/page.tsx` | FIELD_LABELS Mapping für dynamische Block-Felder |

### Commits

- `cc7c3ff` fix: German translations for website admin UI

### Verification Path

Admin → Website → beliebige Unterseite → Labels prüfen → alle in Deutsch

---

## Block Height Control (min_height_vh) (2026-03-01) - IMPLEMENTED

**Scope**: Einstellbare Mindesthöhe (vh) für alle Design-Blöcke der Public Website.

### Feature

| Komponente | Beschreibung |
|------------|--------------|
| Slider UI | Mindesthöhe-Slider im Styling-Tab (0-100vh) |
| Backend-Validierung | `min_height_vh` Feld in `BlockStyleOverrides` |
| Rendering | Flex-Container für korrekte Höhenausfüllung |

### Funktionsweise

- Wert 0 = automatische Höhe (Standard)
- Wert 1-100 = Mindesthöhe in Viewport-Height-Einheiten (vh)
- Wrapper verwendet Flex-Layout damit innerer Block die Höhe ausfüllt
- Gilt für ALLE Block-Typen (Hero, Section, CTA, etc.)

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/schemas/block_validation.py` | `min_height_vh: Optional[int]` (0-100) |
| `frontend/app/types/website.ts` | Interface erweitert |
| `frontend/app/(admin)/website/lib/block-schemas.ts` | Schema erweitert |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Slider UI im Styling-Tab |
| `frontend/app/(public)/components/BlockRenderer.tsx` | Flex-Wrapper + minHeight Style |

### Commits

- `49305db` feat: add min_height_vh setting for all design blocks
- `391a13d` fix: min_height_vh now properly fills block height

### Verification Path

Admin → Website → Seiten → Block auswählen → Styling-Tab → Mindesthöhe auf 100vh → Speichern → Public Website → Block hat 100vh Höhe

---

## Developer Settings Admin UI (2026-03-01) - IMPLEMENTED

**Scope**: Admin-UI für Website-Entwickler-Einstellungen.

### Features

| Einstellung | Feld | Beschreibung |
|-------------|------|--------------|
| HTML formatieren | `prettify_html` | Generiertes HTML wird formatiert (Debugging) |
| Debug-Modus | `debug_mode` | Zusätzliche Debug-Infos in Konsole |
| Cache deaktivieren | `disable_cache` | Browser-Caching für Entwicklung deaktivieren |

### API-Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/v1/website/developer-settings` | GET | Einstellungen abrufen |
| `/api/v1/website/developer-settings` | PUT | Einstellungen speichern |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/developer/page.tsx` | UI komplett neu implementiert |
| `backend/app/api/routes/website_admin.py` | PUT-Endpoint erweitert mit Pydantic Body |
| `supabase/migrations/20260301132546_add_developer_settings_fields.sql` | NEU: `debug_mode`, `disable_cache` Spalten |
| `frontend/app/components/AdminShell.tsx` | Nav-Eintrag + Code Icon |
| `frontend/app/lib/i18n/translations/de.json` | `nav.developer` |
| `frontend/app/lib/i18n/translations/en.json` | `nav.developer` |

**Verification Path:** Admin → Website → Entwickler → Toggle ändern → Speichern → Seite neu laden → Einstellung persistiert

---

## Domain Management Admin UI (2026-03-01) - IMPLEMENTED

**Scope**: Admin-UI fuer Public Website Domain-Einrichtung.

### Feature

| Komponente | Beschreibung |
|------------|--------------|
| Domain-Eingabe | Input-Feld zum Speichern der eigenen Domain |
| Status-Anzeige | Verifizierungsstatus (verifiziert/pending/nicht konfiguriert) |
| Verifizierung | Button zum Pruefen der Domain-Erreichbarkeit |
| DNS-Anleitung | CNAME/A-Record Setup-Instruktionen |

### API-Endpoints (bereits vorhanden)

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/v1/public-site/domain` | GET | Domain-Status abrufen |
| `/api/v1/public-site/domain` | PUT | Domain speichern |
| `/api/v1/public-site/domain/verify` | POST | Domain verifizieren |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/domain/page.tsx` | NEU: Admin-UI |
| `backend/app/api/routes/public_domain_admin.py` | Backend, bereits vorhanden |
| `frontend/app/components/AdminShell.tsx` | Nav-Eintrag + Globe2 Icon |
| `frontend/app/lib/i18n/translations/de.json` | `nav.domain` |
| `frontend/app/lib/i18n/translations/en.json` | `nav.domain` |

### Verification Path

Admin → Website → Domain → Domain eingeben → Speichern → DNS einrichten → Verifizieren

---

## CMS Bug Fixes (2026-02-28) - IMPLEMENTED

**Scope**: Kritische Fixes nach CMS Phase 8 Deployment.

### Fix 1: TrustIndicatorItem Alias

| Problem | Lösung |
|---------|--------|
| Frontend sendet `text`, Backend erwartet `label` | Pydantic `alias="text"` + `populate_by_name=True` |

**Dateien:**
- `backend/app/schemas/block_validation.py` (TrustIndicatorItem)

**Commit:** `5b48466`

### Fix 2: CTABannerBlock Feldnamen

| Problem | Lösung |
|---------|--------|
| Admin speichert camelCase (`buttonText`), Renderer erwartet snake_case (`cta_text`) | Renderer akzeptiert beide Konventionen |

**Mapping:**
| Admin (camelCase) | Renderer (snake_case) |
|-------------------|----------------------|
| `buttonText` | `cta_text` |
| `buttonLink` | `cta_href` |
| `backgroundColor` | `background_color` |
| `subtitle` | `text` |

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx` (CTABannerBlock)

**Commit:** `e6681f3`

### Fix 3: SEO Endpoint 500 Error (3 Bugs)

| Problem | Lösung |
|---------|--------|
| `get_seo()` ohne `agency_id` aufgerufen | `agency_id=agency_id` Parameter hinzugefügt |
| `.model_dump()` auf dict aufgerufen | `seo_defaults` ist bereits dict nach `model_dump()` |
| asyncpg liefert JSONB als String | `_parse_seo_row()` Helper parst JSON-String zu dict |

**Betroffene Stellen:**
- Zeile 1026: Fallback wenn keine set_clauses
- Zeile 1055: Fallback nach leerem Query-Result
- Zeile 1018: `seo_defaults` ist bereits dict, nicht Pydantic model
- Zeile 979, 1063: `SeoResponse(**dict(row))` → `SeoResponse(**_parse_seo_row(row))`

**Dateien:**
- `backend/app/api/routes/website_admin.py` (get_seo, update_seo, _parse_seo_row)

**Commits:** `964bbe0`, `2459c66`, `7508118`

### Fix 4: Block Templates API

| Problem | Lösung |
|---------|--------|
| `block_templates.py` nutzte nicht existierendes `get_supabase` | Komplett auf asyncpg umgestellt |
| Migration referenzierte `tenants` statt `agencies` | Migration korrigiert |
| Router nicht gemountet bei `MODULES_ENABLED=true` | Failsafe-Mounting in `main.py` |

**Dateien:**
- `backend/app/api/routes/block_templates.py` (Komplettes Rewrite)
- `backend/app/main.py` (Failsafe-Mounting)
- `supabase/migrations/20260228182604_add_block_templates.sql`

**Verification Path:** Admin → Website → Seiten → Block hinzufügen → CTA-Banner → Speichern → Public Site prüfen

### Fix 5: Block Style Overrides nicht angewendet

| Problem | Lösung |
|---------|--------|
| Admin speichert `style_overrides` (snake_case) | Renderer prüft jetzt beide: `styleOverrides` und `style_overrides` |
| Block-Styling (Hintergrund, Padding, etc.) wurde ignoriert | `const styleOverrides = block.styleOverrides || block.style_overrides` |

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx`

**Commit:** `1d64c02`

**Verification Path:** Admin → Website → Seiten → Block → Styling-Tab → Hintergrundfarbe setzen → Speichern → Public Site prüfen (Farbe sichtbar)

### Fix 6: Block-Komponenten überschreiben Wrapper-Styling

| Problem | Lösung |
|---------|--------|
| 10 Blöcke setzten eigene `backgroundColor` auf Main-Container | Hardcoded Background entfernt, Wrapper handled Styling via styleOverrides |
| Wrapper styleOverrides wurden durch inneren Block überdeckt | Blöcke sind jetzt "transparent", Background wird vom Wrapper gesetzt |

**Betroffene Blöcke (alle gefixt):**
- `TrustIndicatorsBlock` ✅
- `SearchFormBlock` ✅
- `OfferCardsBlock` ✅
- `LocationGridBlock` ✅
- `PropertyShowcaseBlock` ✅
- `PropertySearchBlock` ✅
- `TestimonialsBlock` ✅
- `ImageTextBlock` ✅
- `FAQAccordionBlock` ✅
- `ContactSectionBlock` ✅

**Nicht geänderte Blöcke (korrekt):**
- `CTABannerBlock` - behält bgColor aus props (gewolltes Banner-Design)
- Innere Elemente (Cards, Buttons, Icons) - behalten ihre Farben

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx`

**Commits:** `97fc39e`, `81b78ab`

**Verification Path:** Admin → Website → Seiten → beliebigen Block → Styling-Tab → Hintergrundfarbe setzen → Speichern → Public Site prüfen (Block-Hintergrund ist custom Farbe)

### Fix 7: TrustIndicatorsBlock Text nicht sichtbar

| Problem | Lösung |
|---------|--------|
| Admin speichert `item.label` | Renderer akzeptiert jetzt `label` ODER `text` |
| Renderer suchte nur nach `item.text` | `const indicatorText = item.label \|\| item.text` |

**Symptom:** Icons wurden angezeigt, aber Texte wie "4.9/5 Bewertung" fehlten.

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx` (TrustIndicatorsBlock)

**Commit:** `8fe59e1`

**Verification Path:** Admin → Website → Seiten → Vertrauens-Indikatoren Block → Text eingeben → Speichern → Public Site prüfen (Text unter Icons sichtbar)

### Fix 8: Block-Feldnamen Kompatibilität (5 Blöcke)

| Problem | Lösung |
|---------|--------|
| Admin speichert camelCase/andere Feldnamen | Renderer akzeptiert beide Konventionen |
| Blöcke zeigten keine Inhalte | Dual-Naming-Support für alle Array- und Einzelfelder |

**Betroffene Blöcke und Mappings:**

| Block | Admin-Feld | Renderer akzeptiert |
|-------|------------|---------------------|
| **OfferCardsBlock** | `offers` | `offers` ODER `items` |
| | `discount` | `discount` ODER `badge` |
| | `description` | `description` ODER `subtitle` |
| | `image` | `image` ODER `image_url` |
| **LocationGridBlock** | `locations` | `locations` ODER `items` |
| | `image` | `image` ODER `image_url` |
| | `count` | `count` ODER `property_count` |
| **TestimonialsBlock** | `testimonials` | `testimonials` ODER `items` |
| | `text` | `text` ODER `quote` |
| **ImageTextBlock** | `image` | `image` ODER `image_url` |
| | `imagePosition` | `imagePosition` ODER `image_position` |

**Bereits korrekt konfiguriert (keine Änderung nötig):**
- `HeroFullwidthBlock` - hatte schon Dual-Naming
- `FAQAccordionBlock` - `items`, `question`, `answer` stimmen überein
- `ContactSectionBlock` - `phone`, `email` stimmen überein
- `IconBoxWidget` - `icon`, `title`, `description` stimmen überein

**Dateien:**
- `frontend/app/(public)/components/BlockRenderer.tsx`

**Commit:** `c67333a`

**Verification Path:** Admin → Website → Seiten → beliebigen Block (z.B. Angebots-Karten, Standort-Raster, Kundenstimmen) → Inhalte eingeben → Speichern → Public Site prüfen (alle Inhalte sichtbar)

### Fix 9: Filter-Konfiguration 500 Error

| Problem | Lösung |
|---------|--------|
| GET/PUT `/api/v1/website/filter-config` liefert 500 | JSON-Parsing für asyncpg JSONB-Felder hinzugefügt |
| asyncpg liefert JSONB als String, Pydantic erwartet dict/list | `_parse_filter_config_row()` Helper parst JSON-Strings |

**Betroffene Felder (JSONB):**
- `filter_order` (List[str])
- `visible_amenities` (Optional[List[str]])
- `available_sort_options` (List[str])
- `labels` (Dict[str, str])

**Dateien:**
- `backend/app/api/routes/website_admin.py` (get_filter_config, update_filter_config, _parse_filter_config_row)

**Commit:** `2eb3211`

**Verification Path:** Admin → Website → Filter → Einstellungen ändern → Speichern (kein 500 Error)

### Fix 10: Horizontaler Filter UX-Verbesserungen

| Problem | Lösung |
|---------|--------|
| Dunkle Eingabefelder (schwer lesbar) | Explizites Light-Styling mit `backgroundColor: #ffffff` |
| Ausstattung-Filter bricht Layout | Kompakter Popover/Dropdown statt inline Checkboxen |

**Änderungen:**
1. **Input-Styling**: Alle Dropdowns/Inputs haben jetzt weiße Hintergründe mit `getInputStyle(design)` Helper
2. **Amenities-Popover**: Im horizontalen Layout zeigt ein Button "X gewählt" an und öffnet ein Dropdown mit Checkboxen

**Vorher:**
```
[Ort ▾] [Gäste ▾] [Schlafzimmer ▾] [Min] [Max]
☐ Einzelbetten
☐ Kamin          ← Bricht das Layout
☐ Mikrowelle
...
```

**Nachher:**
```
[Ort ▾] [Gäste ▾] [Schlafzimmer ▾] [Min] [Max] [Ausstattung (2) ▾]
                                              ↓ Klick öffnet Popover
```

**Dateien:**
- `frontend/app/(public)/components/PropertyFilter.tsx`

**Commit:** `5c90150`

**Verification Path:** Public Site → /unterkuenfte → Horizontaler Filter → Inputs lesbar (weiß), Ausstattung als Dropdown

### Fix 11: Footer voll dynamisch aus Admin-Einstellungen

| Problem | Lösung |
|---------|--------|
| Footer-Spalten hardcodiert (nicht alle Admin-Einstellungen wurden angezeigt) | Dynamisches `FooterColumns` Component iteriert über alle `footer_links` Keys |

**Änderungen:**
1. **FooterColumns Component**: Neue Komponente rendert alle Spalten basierend auf Admin `footer_links`
2. **Keine hardcodierten Spalten**: Statt fester Spalten (Service, Legal, etc.) werden alle Keys aus `footer_links` dynamisch gerendert
3. **Kontakt-Spalte**: Wird nur angezeigt wenn `phone`, `email`, `address` oder `social_links` vorhanden sind
4. **Spalten-Titel Mapping**: `columnTitles` Map übersetzt Keys in deutsche Bezeichnungen (fallback: capitalize)

**Vorher:**
```
[Kontakt] [Reiseziele] [Service] [Rechtliches]
    ↑ Hardcodiert, ignoriert Admin "owner" Spalte
```

**Nachher:**
```
[Kontakt] [Service] [Rechtliches] [Eigentümer] [Reiseziele]
    ↑ Dynamisch aus Admin footer_links, alle Spalten sichtbar
```

**Dateien:**
- `frontend/app/(public)/layout.tsx` (FooterColumns Component)

**Commit:** `7104116`

**Verification Path:** Admin → Website → Einstellungen → Footer Links (z.B. owner Spalte) → Speichern → Public Site Footer prüfen (alle konfigurierten Spalten sichtbar)

---

## CMS Performance & Polish - Phase 8 (2026-02-28) - IMPLEMENTED

**Scope**: Performance-Optimierungen, Skeleton-Loader und Accessibility-Verbesserungen.

### Phase 8.1: Performance-Optimierungen

| Feature | Beschreibung |
|---------|--------------|
| React.memo | Memoized Components: SectionPropsEditor, BlockStyleEditor, SortableWidgetItem |
| useCallback | Clipboard-Funktionen (copyBlock, cutBlock, pasteBlock) |
| Reduced Re-renders | Komponenten werden nur bei Props-Änderungen neu gerendert |

### Phase 8.2: Skeleton Loader

| Feature | Beschreibung |
|---------|--------------|
| Skeleton UI | Layoutgetreuer Placeholder während des Ladens |
| Animate Pulse | Sanfte Animation für visuelles Feedback |
| ARIA Status | role="status" mit aria-label für Screenreader |

### Phase 8.3: Accessibility & Polish

| Feature | Beschreibung |
|---------|--------------|
| ARIA Labels | Alle Buttons mit aria-label für Screenreader |
| ARIA Roles | role="dialog", role="menu", role="menuitem", role="status" |
| aria-hidden | Icons für Screenreader ausgeblendet |
| aria-live | Status-Indikatoren für Auto-Save und Clipboard |
| aria-haspopup | Dropdown-Buttons korrekt annotiert |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | memo, Skeleton, ARIA |

**Verification Path**: Admin → Website → Seiten → Loading prüfen (Skeleton sichtbar) → Screenreader-Test

---

## CMS Copy/Paste & Quick Actions - Phase 7 (2026-02-28) - IMPLEMENTED

**Scope**: Clipboard-Funktionen und Schnellzugriff für effizientes Block-Management.

### Phase 7.1: Clipboard-System

| Feature | Beschreibung |
|---------|--------------|
| Copy Block | Block in Zwischenablage kopieren |
| Cut Block | Block ausschneiden (wird beim Einfügen entfernt) |
| Paste Block | Block aus Zwischenablage einfügen (unterhalb ausgewähltem Block) |
| Keyboard Shortcuts | Ctrl+C, Ctrl+X, Ctrl+V |

### Phase 7.2: Quick Actions Menü

| Feature | Beschreibung |
|---------|--------------|
| Dropdown-Menü | Schnellzugriff-Dropdown pro Block |
| Aktionen | Kopieren, Ausschneiden, Einfügen, Nach oben, Nach unten, Als Vorlage, Löschen |
| Touch-Optimiert | Größere Klickflächen für Mobile |

### Phase 7.3: Keyboard Shortcuts Overlay

| Feature | Beschreibung |
|---------|--------------|
| Help-Modal | Vollständige Shortcut-Übersicht |
| Kategorien | Allgemein, Block-Aktionen, Navigation |
| Toggle | `?` Taste oder Help-Button |

### Keyboard Shortcuts

| Shortcut | Aktion |
|----------|--------|
| Ctrl+C | Block kopieren |
| Ctrl+X | Block ausschneiden |
| Ctrl+V | Block einfügen |
| Ctrl+Z | Rückgängig |
| Ctrl+Y / Ctrl+Shift+Z | Wiederholen |
| Ctrl+S | Speichern |
| Escape | Auswahl aufheben |
| ? | Shortcuts-Hilfe anzeigen |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Clipboard-State, Quick Actions UI, Shortcuts Modal |

**Verification Path**: Admin → Website → Seiten → Block auswählen → Ctrl+C → Ctrl+V testen → Quick Actions Dropdown → `?` für Shortcuts-Hilfe

---

## CMS Block Templates - Phase 6 (2026-02-28) - IMPLEMENTED

**Scope**: Wiederverwendbare Block-Vorlagen speichern und anwenden.

### Phase 6.1: Datenstruktur & API

| Feature | Beschreibung |
|---------|--------------|
| Supabase Migration | `block_templates` Tabelle mit RLS |
| Pydantic Schemas | Create, Update, Response Models |
| REST API | CRUD Endpoints unter `/api/v1/website/block-templates` |

### Phase 6.2: Template-Library UI

| Feature | Beschreibung |
|---------|--------------|
| Tabs im Block-Picker | "Neue Blöcke" / "Vorlagen" |
| Kategorie-Filter | All, Custom, Hero, Content, Marketing, Contact, Layout, Widget |
| Template-Karten | Name, Block-Typ, Löschen-Button |

### Phase 6.4: Block Templates Admin UI (2026-03-01)

| Feature | Beschreibung |
|---------|--------------|
| Admin-Seite `/website/templates` | Vollstandige CRUD-UI fur Block-Templates |
| Kategorie-Filter | Dropdown mit allen 7 Kategorien |
| Suche | Durchsucht Name, Beschreibung und Block-Typ |
| Responsive Layout | Tabelle (Desktop) / Karten (Mobile) |
| Create/Edit Modal | JSON-Editoren fur block_props und style_overrides |
| Delete Confirmation | useConfirm Dialog |
| Navigation | Neuer Eintrag in Sidebar unter Website-Gruppe |

### Phase 6.3: Template Anwenden

| Feature | Beschreibung |
|---------|--------------|
| "Als Vorlage speichern" Button | BookmarkPlus Icon bei jedem Block |
| Save-Modal | Name, Kategorie, Block-Typ Anzeige |
| Template einfügen | Click auf Template → neuer Block mit Props/Styles |

### Dateien

| Datei | Änderung |
|-------|----------|
| `supabase/migrations/20260228182604_add_block_templates.sql` | NEU: DB Schema |
| `backend/app/schemas/block_templates.py` | NEU: Pydantic Models |
| `backend/app/api/routes/block_templates.py` | NEU: CRUD Endpoints |
| `backend/app/main.py` | Router registriert |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Template UI |
| `frontend/app/(admin)/website/templates/page.tsx` | NEU: Admin UI fur Templates |
| `frontend/app/components/AdminShell.tsx` | Navigation + LayoutTemplate Icon |
| `frontend/app/lib/i18n/translations/de.json` | nav.templates |
| `frontend/app/lib/i18n/translations/en.json` | nav.templates |

**Verification Path**: Admin → Website → Templates → Liste sichtbar → Neues Template → Erstellen → Bearbeiten → Loschen

---

## CMS Undo/Redo & Auto-Save - Phase 5 (2026-02-28) - IMPLEMENTED

**Scope**: History-Management für Block-Änderungen mit Undo/Redo und automatischem Speichern.

### Phase 5.1: History-Stack

| Feature | Beschreibung |
|---------|--------------|
| useHistory Hook | Custom Hook für State-History |
| Max 50 Einträge | Begrenzte History-Größe |
| Deep-Clone | JSON.stringify/parse für State-Vergleich |

### Phase 5.2: Undo/Redo UI & Shortcuts

| Feature | Beschreibung |
|---------|--------------|
| Toolbar Buttons | Undo/Redo Buttons mit Tooltips |
| Ctrl+Z | Rückgängig machen |
| Ctrl+Y / Ctrl+Shift+Z | Wiederholen |
| Status-Anzeige | Anzahl verfügbarer Schritte |

### Phase 5.3: Auto-Save

| Feature | Beschreibung |
|---------|--------------|
| 30-Sekunden-Timer | Automatisches Speichern bei Änderungen |
| Status-Indikator | "Speichert..." / "Automatisch gespeichert" |
| Error-Handling | Fehlermeldung bei fehlgeschlagenem Save |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/(admin)/website/pages/[id]/use-history.ts` | NEU: useHistory & useHistoryKeyboard Hooks |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | History-Integration, UI-Buttons, Auto-Save |

**Verification Path**: Admin → Website → Seiten → Blocks bearbeiten → Ctrl+Z testen → 30s warten → Auto-Save prüfen

---

## CMS Block-Styling-Panel - Phase 4 (2026-02-28) - IMPLEMENTED

**Scope**: Erweitertes Styling-Panel für jeden Block mit Background-, Typography-, Border- und Animation-Optionen.

### Phase 4.1: Erweiterte Background-Optionen

| Option | Beschreibung |
|--------|--------------|
| Gradient | CSS-Gradienten (linear/radial) |
| Position | center, top, bottom, left, right, Kombinationen |
| Size | cover, contain, auto, 100% auto, auto 100% |
| Repeat | no-repeat, repeat, repeat-x, repeat-y |
| Attachment | scroll, fixed (Parallax-Effekt) |

### Phase 4.2: Typography-Optionen

| Option | Werte |
|--------|-------|
| Text Color | Hex-Farbe |
| Font Size | xs, sm, base, lg, xl, 2xl, 3xl, 4xl |
| Font Weight | normal, medium, semibold, bold |
| Line Height | tight, normal, relaxed, loose |
| Text Align | left, center, right, justify |
| Letter Spacing | tighter, tight, normal, wide, wider |

### Phase 4.3: Border & Shadow

| Option | Werte |
|--------|-------|
| Border Radius | none, sm, md, lg, xl, 2xl, full |
| Border Width | 0, 1, 2, 4, 8 px |
| Border Color | Hex-Farbe |
| Border Style | solid, dashed, dotted, none |
| Box Shadow | none, sm, md, lg, xl, 2xl |

### Phase 4.4: Animation & Hover-Effekte

| Option | Werte |
|--------|-------|
| Animation | fade-in, slide-up, slide-down, scale-in, bounce |
| Hover Effect | lift, glow, scale, darken |
| Transition Duration | fast (150ms), normal (300ms), slow (500ms) |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/website.ts` | BlockStyleOverrides erweitert |
| `backend/app/schemas/block_validation.py` | Neue Style-Felder validiert |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | BlockStyleEditor UI erweitert |
| `frontend/app/(public)/components/BlockRenderer.tsx` | Style-Klassen und CSS-Verarbeitung |
| `frontend/app/globals.css` | Animation Keyframes |

**Verification Path**: Admin → Website → Seiten → Block bearbeiten → Styling-Tab → Optionen testen

---

## CMS Drag-Drop in Sections - Phase 3 (2026-02-28) - IMPLEMENTED

**Scope**: Drag-Drop-Funktionalität für Widgets in Section-Spalten.

### Features

| Feature | Beschreibung |
|---------|--------------|
| @dnd-kit Library | Moderne React Drag-Drop Library |
| Drop-Zones | Jede Spalte ist eine Drop-Zone für Widgets |
| Widget Picker | Click-to-Add UI für neue Widgets |
| Sortierung | Widgets per Drag-Drop neu anordnen |
| Spalten-Transfer | Widgets zwischen Spalten verschieben |
| Drag Overlay | Visuelles Feedback beim Ziehen |

### Neue Komponenten

| Komponente | Funktion |
|------------|----------|
| `SectionColumnsEditor` | DndContext Container für Spalten |
| `DroppableColumn` | Drop-Zone mit Widget-Picker |
| `SortableWidgetItem` | Draggable Widget Item |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/package.json` | @dnd-kit Dependencies |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | SectionColumnsEditor, DroppableColumn, SortableWidgetItem |

**Verification Path**: Admin → Website → Seiten → Section bearbeiten → Widgets in Spalten ziehen

---

## CMS Widget-Library - Phase 2 (2026-02-28) - IMPLEMENTED

**Scope**: Atomare Widget-Blöcke für flexible Seitengestaltung.

### Widget-Typen

| Widget | Beschreibung | Optionen |
|--------|--------------|----------|
| button | CTA-Button | primary/secondary/outline/ghost, sm/md/lg, icon |
| headline | Überschrift | h1-h6, alignment, color, fontSize |
| paragraph | Textabsatz | HTML-Unterstützung, alignment, fontSize |
| spacer | Vertikaler Abstand | Presets (sm-2xl) oder Custom px |
| divider | Trennlinie | solid/dashed/dotted, thickness, width |
| icon_box | Icon mit Text | Lucide Icons, vertical/horizontal layout |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/website.ts` | 6 Widget Props Interfaces |
| `backend/app/schemas/block_validation.py` | 6 Widget Validators mit Sanitierung |
| `frontend/app/(public)/components/BlockRenderer.tsx` | 6 Widget Renderer Komponenten |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Widget Block-Typen, Kategorie "Widget" |

### Widget JSON-Beispiel

```json
{
  "type": "button",
  "props": {
    "text": "Jetzt buchen",
    "href": "/kontakt",
    "variant": "primary",
    "size": "md",
    "icon": "arrow-right",
    "iconPosition": "right"
  }
}
```

**Verification Path**: Admin → Website → Seiten → Widget hinzufügen → Props bearbeiten

---

## CMS Container-System - Phase 1 (2026-02-28) - IMPLEMENTED

**Scope**: Elementor-inspiriertes Container-System mit Sections und flexiblen Spalten.

### Section-Block Features

| Feature | Beschreibung |
|---------|--------------|
| Spalten-Layouts | 1-col, 2-col, 2-col-wide, 3-col, 4-col |
| Layout-Varianten | full (volle Breite), boxed (container), narrow |
| Gap-Optionen | none, sm, md, lg, xl |
| Mobile-Reverse | Spaltenreihenfolge auf Mobil umkehren |
| Vertical Align | top, center, bottom, stretch |
| Rekursive Tiefe | Max. 3 Ebenen (Section in Section in Section) |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/website.ts` | ColumnConfig, SectionBlockProps, SectionPreset Types |
| `backend/app/schemas/block_validation.py` | ColumnConfig, SectionBlockProps Validatoren, rekursive Validierung |
| `frontend/app/(public)/components/BlockRenderer.tsx` | SectionBlock Renderer mit CSS Grid |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Section Block-Typ, SectionPropsEditor UI |

### Section-Block JSON-Struktur

```json
{
  "type": "section",
  "props": {
    "layout": "boxed",
    "gap": "md",
    "columns": [
      { "width": 66.67, "widgets": [] },
      { "width": 33.33, "widgets": [] }
    ],
    "mobileReverse": false,
    "verticalAlign": "top"
  }
}
```

### Einschränkungen Phase 1

- Widgets in Spalten werden per JSON editiert (kein Drag-Drop)
- Vorschau muss manuell aktualisiert werden

**Verification Path**: Admin → Website → Seiten → Section hinzufügen → Spalten-Preset wählen

---

## CMS SSR & SEO - Phase 0 (2026-02-28) - IMPLEMENTED

**Scope**: Server-Side Rendering und SEO-Optimierung für Public Website.

### Server-Side Rendering

| Änderung | Beschreibung | Datei(en) |
|----------|--------------|-----------|
| Homepage SSR | Server Component mit prefetched data | `(public)/page.tsx` |
| CMS-Seiten SSR | Server Component mit generateStaticParams | `(public)/[slug]/page.tsx` |
| Design API | `fetchDesign()` für Server-Side fetch | `(public)/lib/api.ts` |
| Client Components entfernt | `HomePageClient`, `CmsPageClient` gelöscht | - |

### Technical SEO

| Feature | Beschreibung | Datei |
|---------|--------------|-------|
| Sitemap | Dynamische XML Sitemap für CMS + Properties | `app/sitemap.ts` |
| Robots.txt | Dynamisches robots.txt mit Sitemap-Link | `app/robots.ts` |
| Canonical URLs | Automatische canonical links | `(public)/lib/metadata.ts` |
| ISR | 60 Sekunden Revalidierung | `page.tsx` files |

### Structured Data (Schema.org)

| Schema | Verwendung | Datei |
|--------|------------|-------|
| BreadcrumbList | Alle CMS-Seiten | `(public)/lib/structured-data.tsx` |
| FAQPage | Seiten mit FAQ-Blocks | `(public)/lib/structured-data.tsx` |

### SEO-Verbesserungen

- Full HTML content für Crawler sichtbar (kein Loading Skeleton)
- Open Graph & Twitter Cards in Metadaten
- Canonical URLs verhindern Duplikate
- ISR für schnelle Updates bei CMS-Änderungen

**Verification Path**: View-Source auf Public Website → HTML-Content sichtbar

---

## CMS Security Hardening - Phase -1 (2026-02-28) - IMPLEMENTED

**Scope**: Security-Hardening des bestehenden CMS vor dem Elementor-Upgrade.

### Änderungen

| Task | Beschreibung | Datei(en) |
|------|--------------|-----------|
| CSS-Validierung | `sanitize_css_strict()` für `custom_css` aktiviert | `website_admin.py` |
| Block-Validatoren | 8 fehlende Block-Typen hinzugefügt | `block_validation.py` |
| Unknown Blocks ablehnen | Strict-Mode für API-Endpunkte | `block_validation.py`, `website_admin.py` |

### Neue Block-Validatoren (19 total)

**Neu:** `search_form`, `property_search`

**Legacy:** `hero_search`, `usp_grid`, `rich_text`, `contact_cta`, `faq`, `featured_properties`

### Security-Verbesserungen

- Ungültiges CSS löst `400 Bad Request` aus
- Unbekannte Block-Typen werden mit Fehlermeldung abgelehnt
- `validate_blocks_strict()` für API-Endpunkte (kein silent pass-through)

**Verification Path**: Manuelle Tests über Admin-Panel → Website → Seiten bearbeiten

---

## Dokumentations-Bereinigung (2026-02-27) - IMPLEMENTED

**Scope**: Abgleich der Dokumentation mit aktuellem Codebase-Stand basierend auf Audit-Reports.

### Aktualisierte Dateien

| Datei | Änderung |
|-------|----------|
| `RELEASE_PLAN.md` | Status "Pre-MVP" → "Produktionsreif (85%)", Timeline aktualisiert |
| `CHANGELOG.md` | Fehlende Versionen 0.4.0-0.6.0 hinzugefügt |
| `PRODUCT_BACKLOG.md` | Epic-Status korrigiert (A, C, G, H, J) |

### Korrigierte Epic-Status

- **Epic A (Stability)**: 🚧 → ✅ Done (Session-Management, CSP implementiert)
- **Epic C (Booking)**: 🚧 → ✅ Done (E-Mail-System, Buchungsanfragen)
- **Epic G (Owner Portal)**: 💡 Proposed → 🚧 In Progress (RBAC-Rolle funktioniert)
- **Epic H (Finance)**: 💡 Proposed → 🚧 In Progress (Kurtaxe, DAC7 implementiert)
- **Epic J (Branding)**: Branding-System als vollständig dokumentiert

### Neue CHANGELOG-Einträge

- **v0.6.0** (2026-02-27): Branding-System Phase 3-5, Font-Optimierung
- **v0.5.0** (2026-02-15): Kurtaxe, DSGVO/DAC7, Extra-Services
- **v0.4.0** (2026-01-31): E-Mail-System, Session-Management

**Verification Path**: `git diff HEAD~1 backend/docs/product/`

---

## Security Fixes - Audit Findings (2026-02-27) - IMPLEMENTED

**Scope**: Behebung kritischer, hoher und mittlerer Security-Findings aus dem Security Audit.

### Behobene Issues

| # | Schweregrad | Problem | Lösung |
|---|-------------|---------|--------|
| 1 | **CRITICAL** | Rate Limiting Fail-Open bei Redis-Ausfall | In-Memory Fallback implementiert |
| 2 | **HIGH** | Smoke Auth Bypass ohne Production-Disable | `SMOKE_AUTH_BYPASS_ENABLED` Flag hinzugefügt |
| 3 | **HIGH** | JWT Secret Generation in Development | Verbesserte Warnung + .env.example Update |
| 4 | **HIGH** | Fehlende Rate Limiting für Auth Endpoints | Middleware-basiertes Rate Limiting |
| 5 | **HIGH** | Custom CSS Injection | CSS Sanitizer mit Dangerous Pattern Blocking |
| 6 | **HIGH** | Unvollständige RBAC Enforcement | RBAC an 22 Endpoints nachgerüstet |
| 7 | **MEDIUM** | Trust Proxy Headers Default True | Default auf False geändert |
| 8 | **MEDIUM** | CORS x-http-method-override erlaubt | Header entfernt (Method Tampering) |
| 9 | **MEDIUM** | Encryption Key ohne Validierung | Validation Property + Warnungen |
| 10 | **MEDIUM** | Redis TLS ohne Validierung | Warnung bei unsicherer Konfiguration |
| 11 | **MEDIUM** | Audit Log Best-Effort | Redis-basierte Retry Queue implementiert |

### Änderungen im Detail

#### 1. In-Memory Rate Limiting Fallback

**Problem:** Bei Redis-Ausfall wurden alle Requests durchgelassen (Fail-Open). Dies ermöglichte DDoS und Brute-Force Angriffe.

**Lösung:** Neues Modul `memory_rate_limit.py` mit In-Memory Token Bucket als Fallback:
- Sliding Window Counter Algorithmus
- Thread-safe für async Operations
- Automatisches Cleanup abgelaufener Einträge
- `X-RateLimit-Fallback: memory` Header zur Observability

**Betroffene Dateien:**
- `backend/app/core/memory_rate_limit.py` (NEU)
- `backend/app/core/public_anti_abuse.py` (Fallback integriert)
- `backend/app/core/auth_rate_limit.py` (Fallback integriert)

#### 2. Smoke Auth Bypass Production Flag

**Problem:** Der Smoke Test Auth Bypass in `middleware.ts` konnte nicht in Production deaktiviert werden.

**Lösung:** Neues Environment Flag `SMOKE_AUTH_BYPASS_ENABLED`:
- Default: `true` (Backwards-Kompatibilität)
- In Production: `SMOKE_AUTH_BYPASS_ENABLED=false` setzen
- Deaktiviert x-pms-smoke Header Auth-Bypass

**Betroffene Dateien:**
- `frontend/middleware.ts` (Flag-Check hinzugefügt)

#### 3. JWT Secret Warning Verbesserung

**Problem:** In Development wird JWT Secret generiert, aber die Warnung war nicht klar genug über die Konsequenzen (Session-Verlust nach Restart).

**Lösung:**
- Verbesserte Warnung mit konkreten Konsequenzen
- `.env.example` mit Generierungs-Kommando und Erklärung aktualisiert

**Betroffene Dateien:**
- `backend/app/core/config.py` (Verbesserte Warnung)
- `backend/.env.example` (Dokumentation)

#### 4. Auth Rate Limiting Middleware

**Problem:** Die meisten authentifizierten Endpoints (100+) hatten kein Rate Limiting. Nur `get_current_user_rate_limited()` war geschützt.

**Lösung:** Neue Middleware `AuthRateLimitMiddleware`:
- Automatisches Rate Limiting für ALLE authentifizierten Requests
- User-basierte Limits (aus JWT)
- IP-basierte Limits als zusätzlicher Schutz
- Exempt Paths für Health/Docs

**Betroffene Dateien:**
- `backend/app/core/auth_rate_limit_middleware.py` (NEU)
- `backend/app/main.py` (Middleware registriert)

#### 5. Custom CSS Sanitizer

**Problem:** `custom_css` Feld erlaubte potenziell gefährliche CSS Konstrukte (url(), @import, expression()).

**Lösung:** Neuer CSS Sanitizer mit Dangerous Pattern Blocking:
- Blockiert: `url()`, `@import`, `expression()`, `javascript:`, `behavior:`
- Blockiert: `position:fixed` (UI Overlay), Unicode Escapes
- Logging bei Validation Failures

**Betroffene Dateien:**
- `backend/app/core/css_sanitizer.py` (NEU)
- `backend/app/api/routes/branding.py` (Validator integriert)

#### 6. RBAC Enforcement für alle Admin-Endpoints

**Problem:** Mehrere Admin-Endpoints hatten nur Basic Auth (`get_current_user`) ohne Rollen-Prüfung. Jeder authentifizierte User konnte sensible Operationen durchführen.

**Betroffene Endpoints (vorher ohne RBAC):**
- `extra_services.py`: 8 Endpoints (Katalog CRUD + Property Assignments)
- `website_admin.py`: 12 Endpoints (Design, Pages, Branding, Navigation, SEO)
- `public_domain_admin.py`: 3 Endpoints (Domain Management)
- `roles.py`: 4 Endpoints (Permissions/Roles Read)

**Lösung:** `require_agency_roles()` Dependency zu allen Endpoints hinzugefügt:
- **DELETE**: Nur `admin`
- **POST/PATCH/PUT**: `admin`, `manager`
- **GET (sensibel)**: `staff`, `manager`, `admin`

**Betroffene Dateien:**
- `backend/app/api/routes/extra_services.py` (8 Endpoints)
- `backend/app/api/routes/website_admin.py` (12 Endpoints)
- `backend/app/api/routes/public_domain_admin.py` (3 Endpoints)
- `backend/app/api/routes/roles.py` (4 Endpoints)

#### 7. Reliable Audit Logging mit Redis Queue

**Problem:** Audit Events wurden "best-effort" geschrieben. Bei DB-Fehlern wurden Events verloren. Dies gefährdet Compliance-Anforderungen (GDPR, SOC2).

**Lösung:** Redis-basierte Retry-Queue für fehlgeschlagene Audit Events:
- Primary: Direkter DB-Write (Fast Path, ~1ms)
- On Failure: Event wird in Redis Queue eingereiht
- Background Worker: Verarbeitet Queue periodisch
- Dead Letter Queue: Nach 3 Retries für manuelle Review

**Architektur:**
```
┌─────────────────────────────────────────────────────────────────┐
│  RELIABLE AUDIT LOGGING                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Request → emit_audit_event()                                   │
│                │                                                │
│                ▼                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  1. DB Write (Primary)                                  │   │
│  │     ✓ Success → Event logged                            │   │
│  │     ✗ Failure → Continue to step 2                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                │ (on failure)                                   │
│                ▼                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  2. Redis Queue (Fallback)                              │   │
│  │     Event → pms:audit:failed_events                     │   │
│  │     retry_count, last_error, created_at                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                │ (background)                                   │
│                ▼                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  3. Queue Worker (Periodic)                             │   │
│  │     Pop event → Retry DB write                          │   │
│  │     ✓ Success → Done                                    │   │
│  │     ✗ Failure (retry < 3) → Re-queue                    │   │
│  │     ✗ Failure (retry >= 3) → Dead Letter Queue          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Konfiguration:**
```bash
# .env
AUDIT_QUEUE_ENABLED=true          # Enable/disable queue fallback
AUDIT_QUEUE_MAX_RETRIES=3         # Retries before DLQ
AUDIT_QUEUE_RETRY_DELAY=60        # Seconds between retries
```

**Health Check:**
```bash
# Enable audit queue health check
ENABLE_AUDIT_QUEUE_HEALTHCHECK=true

# Check status
curl -s localhost:8000/health/ready | jq '.components.audit_queue'
```

**Betroffene Dateien:**
- `backend/app/core/audit.py` (erweitert mit Queue-Integration)
- `backend/app/core/audit_queue.py` (NEU - Queue Manager)
- `backend/app/core/config.py` (Queue-Konfiguration)
- `backend/app/core/health.py` (Queue Health Check)

### Verification Path

```bash
# Backend Unit Tests für Memory Rate Limiter
cd backend && pytest tests/core/test_memory_rate_limit.py -v

# Manuelle Verifikation:
# 1. Redis stoppen, API-Request senden -> sollte 429 nach Limit zurückgeben
# 2. X-RateLimit-Fallback: memory Header prüfen
# 3. SMOKE_AUTH_BYPASS_ENABLED=false setzen -> x-pms-smoke Bypass sollte nicht funktionieren
```

### Migrationen

Keine Datenbank-Migrationen erforderlich.

### Post-Deploy Bug Fixes (2026-02-27)

Nach dem initialen Deploy der RBAC-Änderungen traten 500-Fehler auf. Die folgenden Fixes wurden angewendet:

#### Fix 1: RBAC Exception-Handling + x-agency-id Header (`9fecb70`)

**Problem:** Extra Services Seite zeigte "Datenbank-Fehler: Tabellen möglicherweise nicht vorhanden"

**Ursachen:**
1. Backend `require_agency_roles()` fing nur `HTTPException`, andere DB-Fehler (z.B. `asyncpg.UndefinedTableError`) wurden als unbehandelter 500 weitergegeben
2. Frontend API Proxy Routes sendeten keinen `x-agency-id` Header, wodurch Tenant-Resolution fehlschlug

**Lösung:**
- **Backend `auth.py`**: Erweiterte Exception-Behandlung in `require_agency_roles`:
  - `asyncpg.UndefinedTableError/UndefinedColumnError` → graceful fallback (RBAC wird übersprungen)
  - Andere Exceptions → 500 mit Details zur Diagnose
- **Frontend `extra-services/page.tsx`**: Zeigt echte Backend-Fehlermeldungen und 403 RBAC-Fehler an
- **Frontend alle 4 extra-services API Routes**: Senden `x-agency-id` Header via `getAgencyIdFromSession()` Helper

**Betroffene Dateien:**
- `backend/app/core/auth.py`
- `frontend/app/(admin)/extra-services/page.tsx`
- `frontend/app/api/internal/extra-services/route.ts`
- `frontend/app/api/internal/extra-services/[id]/route.ts`
- `frontend/app/api/internal/properties/[id]/extra-services/route.ts`
- `frontend/app/api/internal/properties/[id]/extra-services/[assignmentId]/route.ts`

#### Fix 2: UUID Type Mismatch (`0690a28`)

**Problem:** Nach Fix 1 trat ein neuer Fehler auf:
```
AttributeError: 'UUID' object has no attribute 'replace'
```

**Ursache:**
- `deps.py` → `get_current_agency_id()` gibt `UUID`-Objekt zurück (Zeile 80: `-> UUID:`)
- Routes annotierten `agency_id: str` und riefen dann `UUID(agency_id)` auf
- Python kann `UUID(uuid_object)` nicht verarbeiten - erwartet String

**Lösung:**
- `agency_id: str` → `agency_id: UUID` in allen betroffenen Endpoints
- Entfernte redundante `UUID(agency_id)` Konvertierungen

**Betroffene Dateien:**
- `backend/app/api/routes/extra_services.py` (9 Endpoints)
- `backend/app/api/routes/public_domain_admin.py` (3 Endpoints)

### Commits

| Commit | Beschreibung |
|--------|--------------|
| `c7a1da6` | RBAC enforcement für 27 Endpoints |
| `23531b6` | Reliable audit logging mit Redis Queue |
| `9fecb70` | RBAC 500-error fix (Exception-Handling + x-agency-id) |
| `0690a28` | UUID type mismatch fix |

---

## Branding-Einstellungen Integritätsfixes (2026-02-27) - IMPLEMENTED

**Scope**: Behebung von CSS-Variablen die gesetzt aber nicht verwendet wurden, fehlende Fonts, überlappende Optionen.

### Behobene Issues

| # | Problem | Lösung |
|---|---------|--------|
| 1 | Fonts (Roboto, Open Sans, Poppins) nicht geladen | `layout.tsx`: Google Fonts Import hinzugefügt |
| 2 | `topbar_height_px` CSS-Variable nicht verwendet | AdminShell.tsx: `minHeight: var(--topbar-height)` auf Header |
| 3 | `button_border_radius` ignoriert | globals.css: Button nutzt `--button-radius` mit Fallback |
| 4 | `logo_position` nicht implementiert | AdminShell.tsx: Center/Left Positionierung via Flexbox |
| 5 | `shadow_intensity` ohne Wirkung | globals.css: Data-Attribute-basierte Shadow-Overrides |
| 6 | `nav_border_radius` nicht angewendet | globals.css: Nav-Elemente nutzen `--nav-radius` |
| 7 | `radius_scale` vs individuelle Radius-Optionen unklar | branding-form.tsx: Beschreibungstexte hinzugefügt |
| 8 | `background_color` vs `content_bg_color` unklar | branding-form.tsx: Hinweistexte und Hints |

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/layout.tsx` | Roboto, Open_Sans, Poppins Imports |
| `frontend/app/globals.css` | Shadow Intensity, Border Radius, Button Radius CSS |
| `frontend/app/lib/theme-provider.tsx` | Font-Variablen, Shadow Data-Attribute |
| `frontend/app/components/AdminShell.tsx` | Topbar Height, Logo Position, Shadow CSS |
| `frontend/app/(admin)/settings/branding/branding-form.tsx` | UI-Beschreibungen/Hints |

### Verification Path

```bash
# Frontend Build
cd frontend && npm run build

# PROD-Verifikation
# - /settings/branding > Marke: Fonts (Roboto, Poppins, Open Sans) testen
# - /settings/branding > Erweitert: Topbar-Höhe Slider testen
# - /settings/branding > Erweitert: Logo-Position (Links/Zentriert) testen
# - /settings/branding > Erweitert: Schatten-Intensität testen (none/subtle/normal/strong)
# - /settings/branding > Erweitert: Border-Radius pro Komponente testen
```

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

## Brand-Gradient Entfernung (2026-02-27) - IMPLEMENTED

**Issue**: Separate Gradient-Felder (`gradient_from`, `gradient_via`, `gradient_to`) führten zu Verwirrung mit der Akzentfarbe. Beide hatten ähnliche Auswirkung auf Logo-Hintergrund und aktive Navigation.

**Lösung**: Brand-Gradient-Felder komplett entfernt, Gradient wird nun ausschließlich aus der Akzentfarbe (`accent_color`) abgeleitet.

**Änderungen**:

1. **branding-form.tsx**:
   - Interface-Felder `gradient_from`, `gradient_via`, `gradient_to` entfernt
   - FormData defaults entfernt
   - useEffect-Mapping entfernt
   - Payload-Zeilen entfernt
   - Komplette "Brand-Gradient" UI-Sektion entfernt

2. **theme-provider.tsx**:
   - `ApiBrandConfig` Interface entfernt
   - `applyPremiumNavCssVariables()` vereinfacht - nutzt nur noch `accentColor`:
     ```typescript
     const gradientFrom = accentColor || "#f59e0b";
     const gradientVia = darkenColor(gradientFrom, 5);
     const gradientTo = darkenColor(gradientFrom, 15);
     ```
   - `BrandingConfig` Interface bereinigt
   - Alle Funktionsaufrufe angepasst

**Dateien**:
- `frontend/app/(admin)/settings/branding/branding-form.tsx`
- `frontend/app/lib/theme-provider.tsx`

**Auswirkung**: Akzentfarbe steuert nun konsistent Logo-Hintergrund und aktive Navigation. Keine separate Gradient-Konfiguration mehr nötig.

**Verification Path**:
- Browser: Settings > Branding > Akzentfarbe ändern
- CSS-Variablen prüfen: `--brand-primary-from` sollte der Akzentfarbe entsprechen

**Runbook**: [20-navigation-branding.md](./ops/runbook/20-navigation-branding.md#gradient-vereinfachung-2026-02-27)

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

*Last updated: 2026-02-27 (Brand-Gradient Entfernung IMPLEMENTED)*
