# 41 - CMS Server-Side Rendering & SEO

**Erstellt:** 2026-02-28
**Phase:** CMS Upgrade Roadmap Phase -1, 0, 1, 2 & 3

---

## Übersicht

Dieses Kapitel dokumentiert die SSR-Migration und SEO-Optimierungen für die Public Website.

### Betroffene Komponenten

| Komponente | Vorher | Nachher |
|------------|--------|---------|
| Homepage | Client-Side Fetch | Server Component |
| CMS-Seiten | Client-Side Fetch | Server Component + ISR |
| Design-Tokens | Client-Side Fetch | Server-Side Fetch |
| Sitemap | Nicht vorhanden | Dynamisch generiert |

---

## Phase -1: Security Hardening

### Block-Validierung

**Dateien:**
- `backend/app/schemas/block_validation.py`
- `backend/app/api/routes/website_admin.py`

**Änderungen:**
1. CSS-Sanitierung für `custom_css` Feld aktiviert
2. 8 fehlende Block-Validatoren hinzugefügt
3. Strict-Mode für unbekannte Block-Typen

### Validierte Block-Typen (19 total)

```
Neu:          search_form, property_search
Legacy:       hero_search, usp_grid, rich_text, contact_cta, faq, featured_properties
Standard:     hero_fullwidth, trust_indicators, text_section, offer_cards,
              property_showcase, location_grid, testimonials, cta_banner,
              image_text, faq_accordion, contact_section
```

### Verifikation Phase -1

```bash
# Prüfen ob validate_blocks_strict verwendet wird
rg "validate_blocks_strict" backend/app/api/routes/website_admin.py

# Prüfen ob CSS-Sanitierung aktiv
rg "sanitize_css_strict" backend/app/api/routes/website_admin.py
```

---

## Phase 0: SSR & SEO

### Server-Side Rendering

**Dateien:**
- `frontend/app/(public)/page.tsx` - Homepage
- `frontend/app/(public)/[slug]/page.tsx` - CMS-Seiten
- `frontend/app/(public)/lib/api.ts` - Server-Side Fetch Functions

**Gelöschte Dateien:**
- `frontend/app/(public)/components/HomePageClient.tsx`
- `frontend/app/(public)/components/CmsPageClient.tsx`

### ISR-Konfiguration

```typescript
// In page.tsx Dateien:
export const revalidate = 60; // 60 Sekunden Cache

// Für statische Generierung:
export async function generateStaticParams() {
  const slugs = await fetchAllPageSlugs();
  return slugs.map((slug) => ({ slug }));
}
```

### Technical SEO

**Sitemap:** `frontend/app/sitemap.ts`
- Generiert `/sitemap.xml`
- Enthält: Homepage, CMS-Seiten, Properties
- Cache: 5 Minuten

**Robots:** `frontend/app/robots.ts`
- Generiert `/robots.txt`
- Erlaubt Crawling, blockiert `/api/`, `/admin/`
- Verlinkt zur Sitemap

**Canonical URLs:** `frontend/app/(public)/lib/metadata.ts`
- Automatisch aus Slug generiert
- In `alternates.canonical` gesetzt

### Structured Data

**Datei:** `frontend/app/(public)/lib/structured-data.tsx`

| Schema | Trigger | Daten-Quelle |
|--------|---------|--------------|
| BreadcrumbList | Alle Seiten | Slug + Titel |
| FAQPage | Seiten mit `faq_accordion` Block | Block-Props |

### Verifikation Phase 0

```bash
# 1. SSR prüfen - View Source sollte HTML-Content zeigen
curl -s https://example.com | grep -o '<h1[^>]*>.*</h1>'

# 2. Sitemap prüfen
curl -s https://example.com/sitemap.xml | head -20

# 3. robots.txt prüfen
curl -s https://example.com/robots.txt

# 4. Structured Data prüfen
curl -s https://example.com | grep -o 'application/ld+json'
```

---

## Phase 1: Container-System (Sections & Columns)

### Übersicht

Phase 1 führt ein Elementor-inspiriertes Container-System ein: **Sections** mit flexiblen **Spalten**.

| Feature | Beschreibung |
|---------|--------------|
| Sections | Container-Blöcke mit 1-6 Spalten |
| Spalten-Presets | 1-col, 2-col, 2-col-wide, 3-col, 4-col |
| Layout-Varianten | full, boxed, narrow |
| Gap-Optionen | none, sm, md, lg, xl |
| Mobile-Reverse | Spaltenreihenfolge auf Mobile umkehren |
| Rekursive Tiefe | Max. 3 Ebenen (Section in Section) |

### Dateien

**TypeScript Types:**
- `frontend/app/types/website.ts` - ColumnConfig, SectionBlockProps, SectionPreset

**Backend Validierung:**
- `backend/app/schemas/block_validation.py` - ColumnConfig, SectionBlockProps, rekursive Validierung

**Frontend Renderer:**
- `frontend/app/(public)/components/BlockRenderer.tsx` - SectionBlock Komponente

**Admin Editor:**
- `frontend/app/(admin)/website/pages/[id]/page.tsx` - SectionPropsEditor, Block-Typ "section"

### Section-Block Struktur

```json
{
  "type": "section",
  "props": {
    "layout": "boxed",
    "gap": "md",
    "columns": [
      { "width": 66.67, "widgets": [/* Blöcke */] },
      { "width": 33.33, "widgets": [/* Blöcke */] }
    ],
    "mobileReverse": false,
    "verticalAlign": "top"
  }
}
```

### Spalten-Presets

| Preset | Spaltenbreiten |
|--------|----------------|
| 1-col | 100% |
| 2-col | 50% / 50% |
| 2-col-wide | 66.67% / 33.33% |
| 2-col-narrow | 33.33% / 66.67% |
| 3-col | 33.33% / 33.33% / 33.33% |
| 3-col-wide | 50% / 25% / 25% |
| 4-col | 25% / 25% / 25% / 25% |

### Verifikation Phase 1

```bash
# 1. Backend-Validierung prüfen
rg "class SectionBlockProps" backend/app/schemas/block_validation.py

# 2. Frontend-Renderer prüfen
rg "function SectionBlock" frontend/app/(public)/components/BlockRenderer.tsx

# 3. Admin-Editor prüfen
rg "type.*section" frontend/app/(admin)/website/pages/\\[id\\]/page.tsx
```

### Einschränkungen Phase 1

- **Kein Drag-Drop für Widgets in Spalten** - Widgets werden per JSON editiert
- **Keine Live-Vorschau-Updates** - Vorschau muss manuell aktualisiert werden
- **Max. 3 Verschachtelungsebenen** - Tiefere Sections werden abgelehnt

---

## Phase 2: Widget-Library (Atomare Blöcke)

### Übersicht

Phase 2 fügt 6 atomare Widget-Typen hinzu, die in Sections oder standalone verwendet werden können.

| Widget | Beschreibung | Use Case |
|--------|--------------|----------|
| button | CTA-Button mit Varianten | Links, Aktionen |
| headline | Überschrift (h1-h6) | Titel, Abschnitte |
| paragraph | Text mit HTML-Unterstützung | Fließtext, Beschreibungen |
| spacer | Vertikaler Abstand | Layout-Spacing |
| divider | Horizontale Trennlinie | Visuelle Trennung |
| icon_box | Icon mit Titel/Beschreibung | Features, USPs |

### Widget-Optionen

**Button:**
- Varianten: primary, secondary, outline, ghost
- Größen: sm, md, lg
- Icon-Position: left, right
- Full-width Option

**Headline:**
- Tags: h1-h6
- Alignment: left, center, right
- Custom Color, Font Size

**Paragraph:**
- Alignment: left, center, right, justify
- Font Sizes: sm, base, lg, xl
- Line Heights: tight, normal, relaxed, loose

**Spacer:**
- Presets: sm (2rem), md (4rem), lg (6rem), xl (8rem)
- Custom Height in px
- Mobile/Desktop Visibility

**Divider:**
- Styles: solid, dashed, dotted
- Thickness: thin, normal, thick
- Width: 0-100%
- Alignment: left, center, right

**Icon Box:**
- Icon: Lucide Icon Name
- Layout: vertical, horizontal
- Icon Size: sm, md, lg, xl
- Custom Icon/Background Color

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/types/website.ts` | Widget Props Interfaces |
| `backend/app/schemas/block_validation.py` | Widget Validators |
| `frontend/app/(public)/components/BlockRenderer.tsx` | Widget Renderer |
| `frontend/app/(admin)/website/pages/[id]/page.tsx` | Widget Block-Typen, Editor |

### Verifikation Phase 2

```bash
# 1. Backend-Validierung prüfen
rg "class ButtonWidgetProps" backend/app/schemas/block_validation.py

# 2. Frontend-Renderer prüfen
rg "function ButtonWidget" frontend/app/(public)/components/BlockRenderer.tsx

# 3. Admin-Editor prüfen
rg "type.*button.*Widget" frontend/app/(admin)/website/pages/\\[id\\]/page.tsx
```

---

## Phase 3: Drag-Drop in Sections

### Übersicht

Phase 3 fügt Drag-Drop-Funktionalität für Widgets in Section-Spalten hinzu.

| Feature | Beschreibung |
|---------|--------------|
| @dnd-kit | Moderne Drag-Drop-Library für React |
| Drop-Zones | Jede Spalte ist eine Drop-Zone |
| Widget Picker | Click-to-Add für neue Widgets |
| Sortierung | Widgets per Drag-Drop neu anordnen |
| Spalten-Transfer | Widgets zwischen Spalten verschieben |

### Komponenten

| Komponente | Funktion |
|------------|----------|
| `SectionColumnsEditor` | Hauptcontainer mit DndContext |
| `DroppableColumn` | Drop-Zone für eine Spalte |
| `SortableWidgetItem` | Draggable Widget in einer Spalte |
| `DragOverlay` | Visuelles Feedback beim Ziehen |

### Verwendung

1. Section-Block im Editor öffnen
2. Im "Spalten-Inhalt" Bereich:
   - "+ Widget" klicken → Widget-Typ wählen
   - Widgets per Drag-Handle verschieben
   - Widgets zwischen Spalten ziehen

### Dependencies

```json
{
  "@dnd-kit/core": "^6.x",
  "@dnd-kit/sortable": "^8.x",
  "@dnd-kit/utilities": "^3.x"
}
```

### Verifikation Phase 3

```bash
# 1. Library installiert prüfen
grep "@dnd-kit" frontend/package.json

# 2. SectionColumnsEditor vorhanden
rg "function SectionColumnsEditor" frontend/app/(admin)/website/pages/\\[id\\]/page.tsx

# 3. DndContext verwendet
rg "DndContext" frontend/app/(admin)/website/pages/\\[id\\]/page.tsx
```

---

## Phase 4: Block-Styling-Panel (erweitert)

### Übersicht

Phase 4 erweitert den BlockStyleEditor um professionelle Styling-Optionen.

| Feature | Beschreibung |
|---------|--------------|
| Extended Backgrounds | Gradient, Position, Size, Repeat, Attachment |
| Typography | Color, Size, Weight, Line-Height, Align, Spacing |
| Border & Shadow | Radius, Width, Color, Style, Box-Shadow |
| Animation | Einblendanimationen, Hover-Effekte, Transitions |

### Dateien

**TypeScript Types:**
- `frontend/app/types/website.ts` - BlockStyleOverrides erweitert

**Backend Validierung:**
- `backend/app/schemas/block_validation.py` - Neue Felder validiert

**Frontend Editor:**
- `frontend/app/(admin)/website/pages/[id]/page.tsx` - BlockStyleEditor UI

**Public Renderer:**
- `frontend/app/(public)/components/BlockRenderer.tsx` - Style-Mapping

**CSS Animations:**
- `frontend/app/globals.css` - Keyframes für Animationen

### Style-Optionen im Detail

**Background (erweitert):**
```typescript
{
  background_gradient: "linear-gradient(180deg, #fff, #f0f0f0)",
  background_position: "center",
  background_size: "cover",
  background_repeat: "no-repeat",
  background_attachment: "fixed"  // Parallax
}
```

**Typography:**
```typescript
{
  text_color: "#333333",
  font_size: "lg",        // xs, sm, base, lg, xl, 2xl, 3xl, 4xl
  font_weight: "semibold", // normal, medium, semibold, bold
  line_height: "relaxed", // tight, normal, relaxed, loose
  text_align: "center",   // left, center, right, justify
  letter_spacing: "wide"  // tighter, tight, normal, wide, wider
}
```

**Border & Shadow:**
```typescript
{
  border_radius: "lg",    // none, sm, md, lg, xl, 2xl, full
  border_width: "2",      // 0, 1, 2, 4, 8
  border_color: "#e5e7eb",
  border_style: "solid",  // solid, dashed, dotted, none
  box_shadow: "lg"        // none, sm, md, lg, xl, 2xl
}
```

**Animation:**
```typescript
{
  animation: "slide-up",      // fade-in, slide-up, slide-down, scale-in, bounce
  hover_effect: "lift",       // lift, glow, scale, darken
  transition_duration: "normal" // fast, normal, slow
}
```

### Verifikation Phase 4

```bash
# 1. Backend-Validierung prüfen
rg "background_gradient|text_color|border_radius|animation" backend/app/schemas/block_validation.py

# 2. Frontend Types prüfen
rg "Phase 4" frontend/app/types/website.ts

# 3. Animation Keyframes prüfen
rg "animate-fade-in|animate-slide-up" frontend/app/globals.css

# 4. BlockStyleEditor UI prüfen
rg "Typografie|Rahmen & Schatten|Animation" frontend/app/(admin)/website/pages/\\[id\\]/page.tsx
```

---

## Troubleshooting

### Problem: CMS-Seite zeigt 404

**Ursache:** Seite nicht veröffentlicht oder Slug falsch

**Lösung:**
1. Admin → Website → Seiten prüfen
2. `is_published = true` sicherstellen
3. Slug korrekt (keine Sonderzeichen)

### Problem: Sitemap leer

**Ursache:** API-Fehler oder keine veröffentlichten Seiten

**Lösung:**
```bash
# API direkt prüfen
curl -s "https://api.example.com/api/v1/public/site/pages"
```

### Problem: Design-Tokens fehlen

**Ursache:** Public Design-Endpoint nicht erreichbar

**Lösung:**
```bash
# Endpoint prüfen
curl -s "https://api.example.com/api/v1/public/site/design"
```

---

## Verwandte Kapitel

- [21-public-site-tenant-resolution.md](./21-public-site-tenant-resolution.md)
- [26-public-api-proxy.md](./26-public-api-proxy.md)
- [29-public-website-visibility.md](./29-public-website-visibility.md)
