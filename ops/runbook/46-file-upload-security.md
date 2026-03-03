# File Upload Security

## Übersicht

Das PMS-Webapp implementiert mehrere Sicherheitsebenen für Datei-Uploads:

1. **Magic Bytes Validierung** - Dateityp-Erkennung anhand der Binärsignatur
2. **SVG Sanitization** - Entfernung gefährlicher Elemente/Attribute
3. **XXE-Schutz** - Verwendung von `defusedxml` für XML-Parsing

## Architektur

```
Upload → Magic Bytes Check → Type Detection
                ↓
          SVG detected?
           ├─ Ja → defusedxml Parse → Sanitize → Store
           └─ Nein → Direct Store
```

## XXE-Schutz (defusedxml)

### Warum defusedxml?

Die Python Standard-Library `xml.etree.ElementTree` ist anfällig für XXE (XML External Entity) Attacken:

```xml
<!-- Malicious SVG -->
<?xml version="1.0"?>
<!DOCTYPE svg [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<svg>&xxe;</svg>
```

Ohne `defusedxml` könnte ein Angreifer:
- Lokale Dateien lesen (`file:///etc/passwd`)
- SSRF-Attacken ausführen (interne Services angreifen)
- DoS via Billion Laughs Attack

### Konfiguration

`defusedxml` ist eine **Hard-Dependency** (nicht optional):

```python
# SECURITY: defusedxml is REQUIRED for XXE attack prevention in SVG uploads.
# Do NOT make this optional - the app should fail to start if defusedxml is missing.
import defusedxml.ElementTree as ET
```

**Wichtig:** Die App startet NICHT ohne `defusedxml`. Dies ist beabsichtigt (Fail Fast).

### Verification

```bash
# Prüfen ob defusedxml installiert ist
pip show defusedxml

# Import-Test
python -c "import defusedxml; print(f'defusedxml {defusedxml.__version__}')"
```

## SVG Sanitization

### Entfernte Elemente

Diese SVG-Elemente werden vollständig entfernt:

| Element | Risiko |
|---------|--------|
| `<script>` | JavaScript-Ausführung |
| `<foreignObject>` | HTML-Injection |
| `<iframe>` | Externe Inhalte |
| `<embed>` | Plugin-Ausführung |
| `<object>` | Externe Ressourcen |
| `<use>` | XSS via externe SVG-Referenzen |
| `<image>` | Tracking via externe Bilder |

### Entfernte Attribute

Event-Handler und gefährliche URLs werden entfernt:

- Alle `on*` Attribute (onclick, onerror, onload, ...)
- `javascript:` URLs
- `data:` URLs (außer Bilder)
- `xlink:href` zu externen Ressourcen

### Beispiel

**Vor Sanitization:**
```xml
<svg onclick="alert('xss')">
  <script>malicious()</script>
  <image href="https://tracker.com/pixel.gif"/>
</svg>
```

**Nach Sanitization:**
```xml
<svg>
  <g/>
</svg>
```

## Magic Bytes Validierung

### Unterstützte Formate

| Format | Magic Bytes | Max. Größe |
|--------|-------------|------------|
| PNG | `89 50 4E 47` | 10 MB |
| JPEG | `FF D8 FF` | 10 MB |
| GIF | `47 49 46 38` | 10 MB |
| WebP | `52 49 46 46...57 45 42 50` | 10 MB |
| SVG | `<svg` oder `<?xml` | 10 MB |
| PDF | `25 50 44 46` | 20 MB |
| MP4 | `ftyp` box | 100 MB |

### Warum Magic Bytes?

**Content-Type Headers sind NICHT vertrauenswürdig:**

```bash
# Angreifer kann Content-Type fälschen
curl -X POST -H "Content-Type: image/png" --data-binary @malware.exe /upload
```

Magic Bytes prüfen die tatsächlichen Datei-Bytes, nicht den Header.

## Troubleshooting

### SVG-Upload schlägt fehl

1. **"Invalid SVG" Fehler:**
   - SVG ist malformed (nicht wohlgeformtes XML)
   - Prüfen mit: `xmllint --noout file.svg`

2. **"Ungültige SVG-Kodierung" Fehler:**
   - Datei ist nicht UTF-8/Latin-1 kodiert
   - Konvertieren: `iconv -f ... -t UTF-8 file.svg > fixed.svg`

### defusedxml fehlt (ImportError)

```bash
# In Coolify Terminal (pms-backend)
pip install defusedxml==0.7.1

# Oder requirements.txt prüfen
grep defusedxml requirements.txt
# → defusedxml==0.7.1
```

**Hinweis:** Bei fehlendem `defusedxml` startet die App nicht. Dies ist beabsichtigt.

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `backend/app/services/file_validator.py` | Magic Bytes + SVG Sanitization |
| `backend/app/api/routes/branding.py` | Logo-Upload mit SVG-Support |
| `backend/app/api/routes/media.py` | Media-Upload für Properties |
| `backend/requirements.txt` | defusedxml Dependency |

## Security Fixes

| Datum | Fix | Beschreibung |
|-------|-----|--------------|
| 2026-03-03 | M-03 | defusedxml als Hard-Requirement (kein Fallback mehr) |
