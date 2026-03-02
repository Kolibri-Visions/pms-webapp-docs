# 42 - Medienbibliothek (Media Library)

**Erstellt:** 2026-03-02
**Letzte Aktualisierung:** 2026-03-02

---

## Übersicht

WordPress-style zentrale Medienverwaltung für alle Dateien (Bilder, PDFs, Videos).

**Architektur:**
- `media_files` - Zentrale Tabelle für ALLE Medien
- `media_folders` - Ordner-Hierarchie mit Tenant-Isolation
- `property_media` - Junction-Table (verknüpft Properties mit media_files)
- Supabase Storage Bucket: `property-media` (privat, signierte URLs)

---

## API Endpoints

| Methode | Endpoint | Beschreibung |
|---------|----------|--------------|
| `POST` | `/api/v1/media/upload` | Datei hochladen |
| `GET` | `/api/v1/media` | Dateien auflisten (mit Filter/Pagination) |
| `GET` | `/api/v1/media/{id}` | Einzelne Datei abrufen |
| `PATCH` | `/api/v1/media/{id}` | Metadaten aktualisieren (alt_text, caption) |
| `DELETE` | `/api/v1/media/{id}` | Datei löschen |
| `POST` | `/api/v1/media/bulk-delete` | Mehrere Dateien löschen |
| `POST` | `/api/v1/media/move` | Dateien in Ordner verschieben |
| `GET` | `/api/v1/media/folders` | Ordner auflisten |
| `GET` | `/api/v1/media/folders/tree` | Ordner-Baum abrufen |
| `POST` | `/api/v1/media/folders` | Ordner erstellen |
| `PATCH` | `/api/v1/media/folders/{id}` | Ordner umbenennen |
| `DELETE` | `/api/v1/media/folders/{id}` | Ordner löschen |

---

## Häufige Probleme & Lösungen

### Problem: Bild zeigt 400 Bad Request nach Upload

**Symptom:** Neu hochgeladenes Bild zeigt gebrochenes Thumbnail, Network Tab zeigt 400.

**Ursache:** Private Bucket URLs ohne Signierung.

**Lösung:** Backend generiert signierte URLs in `MediaService.create_file()`.

**Verifikation:**
```bash
# Prüfe ob signed URL generiert wird
curl -s "https://api.fewo.kolibri-visions.de/api/v1/media" \
  -H "Authorization: Bearer $TOKEN" | jq '.[0].public_url'
# Sollte enthalten: /storage/v1/object/sign/property-media/...
```

---

### Problem: Thumbnails brechen nach Metadaten-Bearbeitung

**Symptom:** Nach Klick auf Alt-Text/Caption Felder wird Bild plötzlich gebrochen.

**Ursache:** `update_file()` gab unsigned URL aus DB zurück.

**Lösung:** `_add_signed_url_to_item()` wird auf alle Response-Methoden angewendet.

**Betroffene Methoden:**
- `create_file()`
- `get_file()`
- `list_files()`
- `update_file()`

---

### Problem: Property-Bilder erscheinen nicht in Medienbibliothek

**Symptom:** Über Property-Formular hochgeladene Bilder sind in `/media` nicht sichtbar.

**Ursache:** Vor Migration waren `property_media` und `media_files` getrennt.

**Lösung:** Migration `20260302180000_unify_media_architecture.sql`:
- Fügt `media_file_id` FK zu `property_media` hinzu
- Migriert existierende Records in `media_files`
- Verknüpft property_media mit media_files

**Verifikation:**
```sql
-- Prüfe Migration Status
SELECT * FROM media_migration_stats;

-- Erwartetes Ergebnis:
-- total_property_media = linked_property_media
```

---

### Problem: Upload schlägt fehl mit "Ungültiger Dateityp"

**Symptom:** Upload wird abgelehnt trotz korrekter Dateiendung.

**Ursache:** Magic-Bytes Validierung erkennt Dateityp nicht.

**Erlaubte Typen (Magic Bytes):**
| Typ | Magic Bytes |
|-----|-------------|
| PNG | `89 50 4E 47 0D 0A 1A 0A` |
| JPEG | `FF D8 FF` |
| WebP | `RIFF....WEBP` |
| GIF | `GIF87a` oder `GIF89a` |
| PDF | `%PDF-` |
| MP4 | `....ftyp` |
| WebM | `1A 45 DF A3` |

**Prüfung:**
```bash
# Magic Bytes einer Datei anzeigen
xxd -l 16 datei.jpg
```

---

### Problem: SVG wird abgelehnt

**Symptom:** SVG-Upload schlägt fehl mit "Ungültige SVG-Datei".

**Ursache:** SVG enthält gefährliche Elemente (XSS-Schutz).

**Entfernte Elemente:**
- `<script>`, `<foreignObject>`, `<iframe>`, `<embed>`, `<object>`
- Event-Handler: `onclick`, `onerror`, `onload`, etc.
- `javascript:` URLs

**Lösung:** SVG vor Upload bereinigen oder Backend akzeptiert bereinigte Version.

---

## Storage-Pfade

```
property-media/                          # Bucket (privat)
├── agencies/{agency_id}/properties/     # Property-Uploads (alt)
│   └── {property_id}/{filename}
└── {agency_id}/library/originals/       # Media Library Uploads (neu)
    └── {file_id}.{ext}
```

**Thumbnails werden generiert in:**
```
property-media/
└── {agency_id}/library/thumbnails/
    ├── sm/{file_id}.webp    # 150x150
    ├── md/{file_id}.webp    # 400x400
    └── lg/{file_id}.webp    # 800x800
```

---

## Signed URLs

**Gültigkeit:** 1 Stunde (3600 Sekunden)

**Generierung:**
```python
# backend/app/services/media.py
async def _get_signed_url(self, storage_path: str) -> str:
    response = await client.post(
        f"{self.supabase_url}/storage/v1/object/sign/{MEDIA_BUCKET}/{storage_path}",
        json={"expiresIn": 3600}
    )
    return f"{self.supabase_url}/storage/v1{data['signedURL']}"
```

**Wichtig:** Signed URLs werden bei JEDEM API-Response generiert, nicht gecached.

---

## Tenant-Isolation

**KRITISCH:** Alle Queries müssen `agency_id` Filter enthalten!

```python
# RICHTIG
.eq("agency_id", str(self.agency_id))

# FALSCH - Sicherheitslücke!
.eq("id", str(file_id))  # ohne agency_id
```

**RLS Policies aktiv auf:**
- `media_files`
- `media_folders`
- `media_audit_log`

---

## Audit Logging

Alle Media-Aktionen werden geloggt in `media_audit_log`:

| Aktion | Geloggte Daten |
|--------|----------------|
| `upload` | filename, size, mime_type |
| `delete` | file_id |
| `bulk_delete` | deleted_count, failed_count |
| `update` | geänderte Felder |

**Abfrage:**
```sql
SELECT * FROM media_audit_log
WHERE agency_id = 'xxx'
ORDER BY created_at DESC
LIMIT 50;
```

---

## Verifikation Commands

### Health Check
```bash
curl -s "https://api.fewo.kolibri-visions.de/api/v1/media" \
  -H "Authorization: Bearer $TOKEN" | jq 'length'
```

### Upload Test
```bash
curl -X POST "https://api.fewo.kolibri-visions.de/api/v1/media/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.jpg" \
  -F "alt_text=Test Image"
```

### Folder Tree
```bash
curl -s "https://api.fewo.kolibri-visions.de/api/v1/media/folders/tree" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### Migration Status
```sql
SELECT * FROM media_migration_stats;
```

---

## Zugehörige Dateien

### Backend
- `backend/app/services/media.py` - MediaService
- `backend/app/services/file_validator.py` - Magic Bytes + SVG Sanitization
- `backend/app/services/image_processor.py` - Thumbnails
- `backend/app/api/routes/media.py` - API Endpoints
- `backend/app/schemas/media.py` - Pydantic Schemas

### Frontend
- `frontend/app/(admin)/media/page.tsx` - Admin Page
- `frontend/app/components/media/MediaGrid.tsx` - Grid/List View
- `frontend/app/components/media/FolderTree.tsx` - Ordner-Navigation
- `frontend/app/components/media/MediaUploader.tsx` - Upload Component
- `frontend/app/lib/api/media.ts` - API Client

### Migrationen
- `supabase/migrations/20260302155624_create_media_tables.sql` - Initiale Tabellen
- `supabase/migrations/20260302180000_unify_media_architecture.sql` - Unified Architecture

---

## Siehe auch

- [project_status.md](../../project_status.md) - Media Library Phasen
- [PLAN-MediaLibrary.md](/PMS-Webapp-Dokumente/PLAN-MediaLibrary.md) - Vollständiger Plan
