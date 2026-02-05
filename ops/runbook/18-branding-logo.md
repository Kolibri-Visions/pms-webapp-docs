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

**Storage Path:** `property-media` bucket → `branding/{tenant_id}/logo_{hash}.{ext}`

### Sidebar Logo Display

The Admin UI sidebar displays the uploaded logo:
- **With logo:** `<img>` element with white background, rounded corners
- **Without logo:** Gold circle with first letter of agency name (fallback: "L")

**Cache-Busting:** Logo URL includes content hash, ensuring browsers fetch the new version.

## API Endpoints

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| Get branding | `/api/v1/branding` | GET | authenticated |
| Update branding | `/api/v1/branding` | PUT | admin, manager |
| Upload logo | `/api/v1/branding/logo` | POST | admin, manager |

### POST /api/v1/branding/logo

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` field with image data

**Response:**
```json
{
  "logo_url": "https://sb-pms.../storage/v1/object/public/property-media/branding/{tenant_id}/logo_{hash}.png",
  "updated_at": "2026-02-05T10:00:00Z"
}
```

**Error Responses:**
| Status | Cause |
|--------|-------|
| 400 | Invalid file type or size > 2MB |
| 403 | Not admin or manager role |
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
  --data-binary "$(jq -nc --arg e \"$SB_EMAIL\" --arg p \"$SB_PASSWORD\" '{email:$e,password:$p}')" \
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

### Upload Fails with 503

**Symptom:** "Storage service not configured" error.

**Resolution:**
1. Check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set
2. Verify Supabase storage is accessible
3. Check `property-media` bucket exists in Supabase Storage

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
4. **Verify change:** GET /api/v1/branding → logo_url contains "branding/" path

### Expected Result

```
RESULT: PASS
Summary: PASS=4, FAIL=0, SKIP=0
```

## Related Documentation

- [Branding API](../../api/branding.md) — Branding configuration
- [Storage Service](../../api/storage.md) — File upload infrastructure
