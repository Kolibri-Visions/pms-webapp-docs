# 52 — Storage → MinIO Migration (Phase 2)

## Zusammenfassung

Supabase Storage wurde durch einen eigenen MinIO-Container (S3-kompatibel) ersetzt.
Alle Datei-Uploads (Property-Media, Branding-Assets, Avatare) laufen jetzt ueber MinIO.

## Architektur

```
Frontend → Backend API → MinIO (S3 API, Port 9000)
Browser  → Backend /storage/{bucket}/{path} → MinIO (Proxy fuer oeffentliche Dateien)
```

### Buckets

| Bucket | Inhalt | Zugriff |
|--------|--------|---------|
| `property-media` | Property-Fotos, Thumbnails, PDF-Previews | Public (via Storage Proxy) |
| `branding-assets` | Tenant-Logos, Favicons | Public (via Storage Proxy) |
| `avatars` | User-Profilbilder | Public (via Storage Proxy) |

### Komponenten

| Datei | Funktion |
|-------|----------|
| `app/core/s3_storage.py` | S3Storage-Klasse (Upload, Delete, Sign) |
| `app/core/storage.py` | Re-Export-Wrapper (Rueckwaertskompatibilitaet) |
| `app/api/routes/storage_proxy.py` | GET /storage/{bucket}/{path} — Public File Proxy |
| `app/api/routes/avatar.py` | POST/DELETE /api/v1/avatar |
| `app/modules/storage_proxy.py` | Module-Registrierung (Root-Prefix, kein /api/v1) |
| `app/modules/avatar.py` | Module-Registrierung (unter /api/v1) |

## Environment Variables

| Variable | Beispiel | Beschreibung |
|----------|----------|-------------|
| `S3_ENDPOINT` | `http://pms-minio:9000` | MinIO API Endpoint (intern) |
| `S3_ACCESS_KEY` | `pms-minio-admin` | MinIO Root User |
| `S3_SECRET_KEY` | `<secret>` | MinIO Root Password |
| `S3_PUBLIC_URL` | `https://api.pms.kolibri-visions.de/storage` | Oeffentliche Basis-URL |
| `S3_SECURE` | `false` | HTTPS fuer S3 API (false bei internem Docker-Netz) |

## Troubleshooting

### Bilder laden nicht (404)

1. Pruefen ob MinIO laeuft: `curl http://pms-minio:9000/minio/health/live`
2. Pruefen ob Bucket existiert: `mc ls pms-minio/property-media`
3. Pruefen ob Storage Proxy erreichbar: `curl -I https://api.pms.kolibri-visions.de/storage/property-media/test`
4. Backend-Logs pruefen: `Storage proxy error` Meldungen

### Upload schlaegt fehl (500)

1. S3-Credentials pruefen: `S3_ACCESS_KEY` / `S3_SECRET_KEY` korrekt?
2. MinIO erreichbar vom Backend-Container? `curl http://pms-minio:9000/minio/health/live`
3. Backend-Logs: `S3Storage` oder `StorageError` Meldungen

### URLs zeigen noch auf Supabase

SQL-Migration wurde nicht ausgefuehrt. Script: `supabase/scripts/migrate_storage_urls_to_s3.sql`

### storage_provider Werte

- `"supabase"` — Legacy (vor Migration hochgeladene Dateien)
- `"s3"` — Neue Uploads (nach Migration)
- `"url-only"` — Externe URLs (kein Storage)

Code akzeptiert alle drei Werte: `storage_provider in ("supabase", "s3")`
