# Branding Logo Upload

This runbook chapter covers the Branding Logo Upload feature in the Admin UI.

**When to use:** Uploading and managing tenant logo for Admin UI sidebar branding.

## Overview

The Branding Logo feature provides:

1. **Logo Upload** — Upload custom logo via Admin UI (PNG, JPEG, WebP, SVG)
2. **Live Update** — Sidebar logo updates immediately after upload (no page reload)
3. **Cache-Busting** — Content-hash in storage path ensures new logos appear immediately
4. **Fallback** — Shows first letter of agency name if no logo uploaded

**Access:** Admin and Manager roles can upload; all authenticated users see the logo.

## Architecture

### Request Flow

```
Browser → /api/internal/branding/logo → Backend /api/v1/branding/logo → Supabase Storage
```

The Admin UI uses an internal Next.js API route (`/api/internal/branding/logo`) to proxy uploads to the backend. This avoids CORS/routing issues when the frontend is served from a different domain than the API.

### Storage

| Setting | Value | Description |
|---------|-------|-------------|
| Bucket | `branding-assets` | Dedicated bucket for branding assets |
| Path | `{tenant_id}/logo_{hash}.{ext}` | Per-tenant path with content hash |
| Access | Public | No signed URLs needed |
| ENV Override | `BRANDING_STORAGE_BUCKET` | Configurable bucket name |

## Navigation / Wo finde ich das?

| Menüpunkt | Pfad | Beschreibung |
|-----------|------|--------------|
| Einstellungen → Branding | `/settings/branding` | Logo upload and branding settings |

## Features

### Logo Upload

**UI Location:** Einstellungen → Branding → Logo

**Supported Formats:**
| Format | MIME Type | Max Size |
|--------|-----------|----------|
| PNG | image/png | 2 MB |
| JPEG | image/jpeg | 2 MB |
| WebP | image/webp | 2 MB |
| SVG | image/svg+xml | 2 MB |

**Upload Flow:**
1. Click "Logo hochladen" button or drag file
2. Preview appears
3. Click "Speichern" to upload
4. Sidebar logo updates automatically

### Manual URL (extern) vs Upload (Storage)

The branding form distinguishes between **uploaded logos** (stored in Supabase Storage) and **external URLs**:

| Source | Behavior | Manual URL Input |
|--------|----------|------------------|
| **Upload** | File stored in `branding-assets` bucket | Input stays **empty** (not auto-filled) |
| **External URL** | URL saved directly to `logo_url` | Input shows current external URL |

**Important:** After uploading a logo, the "URL manuell eingeben" field intentionally remains empty. The storage URL is NOT copied into this field. This prevents confusion between uploaded and external logos.

**To use an external logo instead of upload:**
1. Expand "Oder externe URL manuell eingeben"
2. Enter the full URL (e.g., `https://cdn.example.com/logo.png`)
3. Click "Save Changes"

### Branding Colors (Theme Customization)

**Available Colors:**
| Field | CSS Variable | Usage |
|-------|--------------|-------|
| Primärfarbe | `--t-primary` | Buttons, links, primary actions |
| Sekundärfarbe | `--t-secondary` | Secondary buttons, badges |
| Akzentfarbe | `--t-accent` | Focus rings, highlights, accents |
| Hintergrundfarbe | `--t-bg` | Main app background |

**How Colors Apply Globally:**
- Colors are applied as CSS variables on `document.documentElement`
- Components using Tailwind classes automatically pick up colors
- Foreground colors (text on buttons) are computed for contrast

**Default Behavior:**
- If a color field is empty, the default theme is used
- Defaults: Primary=#4F46E5, Secondary=#0F172A, Accent=#10B981, Background=#FFFFFF

### Sidebar Logo Display

The Admin UI sidebar displays the uploaded logo:
- **With logo:** `<img>` element with white background, rounded corners
- **Without logo:** Gold circle with first letter of agency name (fallback: "L")

**Cache-Busting:** Logo URL includes content hash, ensuring browsers fetch the new version.

## Bucket Provisioning

The branding logo feature requires the `branding-assets` bucket in Supabase Storage.

### Auto-Creation (Default Behavior)

The backend **automatically creates** the `branding-assets` bucket on first upload if it doesn't exist. This requires:
- `SUPABASE_SERVICE_ROLE_KEY` to be set and have admin permissions
- Supabase Storage API to be accessible

If auto-creation fails, the upload will return a 503 error with details. In this case, create the bucket manually (see below).

### Create Bucket (Supabase Dashboard)

1. Open Supabase Dashboard → Storage
2. Click "New bucket"
3. Name: `branding-assets`
4. Public bucket: **Yes** (logos must be publicly accessible)
5. File size limit: 2MB (optional, backend enforces this)
6. Click "Create bucket"

### Create Bucket (SQL)

```sql
-- Run in Supabase SQL Editor
INSERT INTO storage.buckets (id, name, public)
VALUES ('branding-assets', 'branding-assets', true)
ON CONFLICT (id) DO NOTHING;
```

### Verify Bucket Exists

```bash
# Using Supabase CLI
supabase storage ls

# Or check via API
curl -s "${SUPABASE_URL}/storage/v1/bucket/branding-assets" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" | jq
```

## API Endpoints

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| Get branding | `/api/v1/branding` | GET | authenticated |
| Update branding | `/api/v1/branding` | PUT | admin, manager |
| Upload logo | `/api/v1/branding/logo` | POST | admin, manager |
| Internal proxy | `/api/internal/branding/logo` | POST | session auth |

### POST /api/v1/branding/logo

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` field with image data

**Response:**
```json
{
  "logo_url": "https://sb-pms.../storage/v1/object/public/branding-assets/{tenant_id}/logo_{hash}.png",
  "updated_at": "2026-02-05T10:00:00Z"
}
```

**Error Responses:**
| Status | Cause |
|--------|-------|
| 400 | Invalid file type or size > 2MB |
| 403 | Not admin or manager role |
| 502 | Storage upload failed (bucket creation or upload error) |
| 503 | Storage service not configured |

## Verification (PROD)

### Deploy Verification

```bash
# HOST-SERVER-TERMINAL
source /root/.pms_env
export API_BASE_URL="https://api.fewo.kolibri-visions.de"

# 1. Verify deploy
EXPECT_COMMIT=<sha> ./backend/scripts/pms_verify_deploy.sh

# 2. Get JWT token
export JWT_TOKEN="$(curl -k -sS -X POST "${SB_URL}/auth/v1/token?grant_type=password" \
  -H "apikey: ${SB_ANON_KEY}" \
  -H "Content-Type: application/json" \
  --data-binary "$(jq -nc --arg e \"$SB_EMAIL\" --arg p \"$SB_PASSWORD\" '{email:\$e,password:\$p}')" \
  | jq -r '.access_token // empty')"

# 3. Run smoke test
JWT_TOKEN="${JWT_TOKEN}" ./backend/scripts/pms_branding_logo_smoke.sh

echo "branding_logo_rc=$?"
```

### Quick API Test

```bash
# Test upload with tiny PNG
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==" | base64 -d > /tmp/test_logo.png

curl -sS \
  -H "Authorization: Bearer ${JWT_TOKEN}" \
  -F "file=@/tmp/test_logo.png;type=image/png" \
  "${API_BASE_URL}/api/v1/branding/logo" | jq

rm /tmp/test_logo.png
```

## Troubleshooting

### Branding API Returns 503 (Schema Out of Date)

**Symptom:** PUT/GET `/api/v1/branding` returns 503 with message:
- "Branding schema out of date. Run database migrations"
- Or in logs: "column secondary_color does not exist"

**Cause:** The `tenant_branding` table is missing the `secondary_color` and/or `background_color` columns added in migration `20260206000000_add_branding_secondary_background_colors.sql`.

**Resolution:**
1. Apply the migration in Supabase SQL Editor:
   ```sql
   -- Add secondary_color if missing
   DO $$
   BEGIN
     IF NOT EXISTS (
       SELECT 1 FROM information_schema.columns
       WHERE table_schema = 'public'
         AND table_name = 'tenant_branding'
         AND column_name = 'secondary_color'
     ) THEN
       ALTER TABLE public.tenant_branding ADD COLUMN secondary_color text;
       ALTER TABLE public.tenant_branding
         ADD CONSTRAINT valid_secondary_color
         CHECK (secondary_color IS NULL OR secondary_color ~* '^#[0-9A-Fa-f]{6}$');
     END IF;
   END $$;

   -- Add background_color if missing
   DO $$
   BEGIN
     IF NOT EXISTS (
       SELECT 1 FROM information_schema.columns
       WHERE table_schema = 'public'
         AND table_name = 'tenant_branding'
         AND column_name = 'background_color'
     ) THEN
       ALTER TABLE public.tenant_branding ADD COLUMN background_color text;
       ALTER TABLE public.tenant_branding
         ADD CONSTRAINT valid_background_color
         CHECK (background_color IS NULL OR background_color ~* '^#[0-9A-Fa-f]{6}$');
     END IF;
   END $$;
   ```
2. Verify columns exist:
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'tenant_branding'
   ORDER BY ordinal_position;
   ```
3. Retry the branding API call.

### Upload Fails with 404 (Admin UI)

**Symptom:** Browser shows 404 when clicking "Speichern" for logo upload.

**Cause:** Frontend posting to wrong URL (direct `/api/v1/...` instead of internal proxy).

**Resolution:**
1. Verify frontend uses `/api/internal/branding/logo` (not direct API URL)
2. Check `frontend/app/api/internal/branding/logo/route.ts` exists
3. Redeploy frontend if route was recently added

### Upload Fails with 503 (Bucket Auto-Creation Failed)

**Symptom:** Error: "Could not create branding bucket 'branding-assets'. Check service role permissions."

**Cause:** Backend tried to auto-create the bucket but failed (likely permissions issue).

**Resolution:**
1. Check `SUPABASE_SERVICE_ROLE_KEY` has admin/service_role permissions
2. Verify the key is not expired or rate-limited
3. Check backend logs for detailed error message
4. If permissions cannot be fixed, create bucket manually (see Bucket Provisioning above)

### Upload Fails with 502 (Storage Error)

**Symptom:** Error: "Failed to upload logo to storage (HTTP 4xx)"

**Cause:** Upload to Supabase Storage failed after bucket check/creation.

**Resolution:**
1. Check backend logs for detailed storage error
2. Verify Supabase Storage is operational
3. Check bucket exists and is accessible
4. Verify file size is under 2MB

### Upload Fails with 400 (Embedded 404 - Bucket Not Found)

**Symptom:** Upload returns HTTP 500/502 with logs showing:
```
HTTP 400 - {"statusCode":"404","error":"Bucket not found","message":"Bucket not found"}
```

**Cause:** Supabase Storage behind Kong returns HTTP 400 with embedded 404 in JSON body instead of plain HTTP 404. The backend now detects both cases.

**Resolution:**
1. Backend should auto-detect and create bucket (check logs for "Ensuring branding bucket")
2. If auto-creation fails, check `SUPABASE_SERVICE_ROLE_KEY` permissions
3. Manual fallback — create bucket via SQL:
   ```sql
   INSERT INTO storage.buckets (id, name, public)
   VALUES ('branding-assets', 'branding-assets', true)
   ON CONFLICT (id) DO NOTHING;
   ```
4. Verify bucket exists after manual creation, then retry upload

### Logo Not Appearing in Sidebar

**Symptom:** Uploaded logo but sidebar still shows letter initial.

**Causes & Solutions:**
1. **Browser cache:** Hard refresh (Ctrl+Shift+R / Cmd+Shift+R)
2. **Upload failed:** Check browser console for errors
3. **Wrong URL:** Verify `logo_url` in `/api/v1/branding` response
4. **CORS issue:** Check Supabase storage bucket has correct CORS policy

### Upload Fails with 400

**Symptom:** "Invalid file type" or "File too large" error.

**Resolution:**
1. Check file type is PNG, JPEG, WebP, or SVG
2. Check file size is under 2 MB
3. Try re-saving image in supported format

### Upload Fails with 503 (Service Not Configured)

**Symptom:** "Storage service not configured" error.

**Resolution:**
1. Check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set
2. Verify Supabase storage is accessible
3. Check bucket exists (see Bucket Provisioning)

### Old Logo Still Showing

**Symptom:** After upload, old logo still appears.

**Resolution:**
1. Logo URL includes content hash, so different content = different URL
2. Check if upload actually succeeded (verify `logo_url` changed)
3. Hard refresh browser
4. Check for CDN caching (if using CDN)

## Smoke Test

**Script:** `backend/scripts/pms_branding_logo_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_branding_logo_smoke.sh

# Skip upload test (dry-run GET endpoints only)
JWT_TOKEN="eyJhbG..." SKIP_UPLOAD=1 ./backend/scripts/pms_branding_logo_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT (admin/manager role) |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |
| `SKIP_UPLOAD` | No | `0` | Set to `1` to skip upload test |

### What It Tests

1. **Health check:** GET /health → HTTP 200
2. **Get branding:** GET /api/v1/branding → HTTP 200
3. **Upload logo:** POST /api/v1/branding/logo with tiny PNG → HTTP 200/201
4. **Verify change:** GET /api/v1/branding → logo_url contains "branding-assets/" path

### Expected Result

```
RESULT: PASS
Summary: PASS=4, FAIL=0, SKIP=0
```

## Related Documentation

- [Branding API](../../api/branding.md) — Branding configuration
- [Storage Service](../../api/storage.md) — File upload infrastructure
