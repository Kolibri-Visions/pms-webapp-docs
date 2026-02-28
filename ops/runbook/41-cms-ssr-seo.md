# 41 - CMS Server-Side Rendering & SEO

**Erstellt:** 2026-02-28
**Phase:** CMS Upgrade Roadmap Phase -1 & 0

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
