# Ops Modules View Admin UI

This runbook chapter covers the Ops Modules View feature in the Admin UI.

**When to use:** Verifying module loading, debugging missing routes, or checking deployment status.

## Overview

The Ops Modules View Admin UI is a **Developer Tool** that allows administrators to:

1. **View module status** — Check if module system is enabled and how many modules are loaded
2. **Inspect modules** — See name, version, router count, prefixes, and tags for each module
3. **View mounted paths** — List all API prefixes actually mounted in the application
4. **Debug routes** — Compare registered modules vs actual mounted routes

**Access:** Admin role required.

## Navigation / Wo finde ich das?

Die Ops-Seiten befinden sich im Admin-Panel unter **Einstellungen**:

| Menüpunkt | Pfad | Beschreibung |
|-----------|------|--------------|
| Einstellungen → Systemstatus | `/ops/status` | System-Gesundheit und Status |
| Einstellungen → Runbook | `/ops/runbook` | Operations-Dokumentation |
| Einstellungen → Log-Protokoll | `/ops/audit-log` | Audit-Log Viewer |
| Einstellungen → Module | `/ops/modules` | **Ops Modules View** (Developer Tool) |

**Direkter Link:** `/ops/modules`

## Features

### Summary Cards

**UI Location:** Top of page

**Displays:**
| Card | Description |
|------|-------------|
| Modulsystem | Active/Inactive status |
| Module | Total registered modules count |
| API Prefixes | Count of mounted endpoint prefixes |
| Spezialpfade | Pricing + Channel connection path counts |

### Module Table

**UI Location:** Main section

**Columns:**
- Name — Module identifier
- Version — Module version string
- Router — Number of routers in module
- Prefixes — API path prefixes (badges, truncated)
- Tags — Module tags (badges, truncated)

**Features:**
- Client-side search (name, prefix, tag)
- Pagination (10/25/50 per page)
- Click row to open detail modal

### Detail Modal

**UI Location:** Click any table row

**Shows:**
- Full module name and version
- Router count
- All prefixes (as badges)
- All tags (as badges)
- JSON representation
- "Copy JSON" button

### Mounted Paths Sections

**UI Location:** Bottom of page (collapsible)

**Lists:**
- Alle API Prefixes — All mounted route prefixes
- Pricing Paths — Pricing-specific routes
- Channel Connections Paths — Channel manager routes

## API Endpoint

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| Get modules | `/api/v1/ops/modules` | GET | auth required |

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `modules_enabled` | boolean | Whether module system is active |
| `total_modules` | integer | Count of registered modules |
| `modules` | array | List of module objects |
| `modules[].name` | string | Module name |
| `modules[].version` | string | Module version |
| `modules[].router_count` | integer | Number of routers |
| `modules[].prefixes` | array | API path prefixes |
| `modules[].tags` | array | Module tags |
| `mounted_prefixes` | array | All mounted API prefixes |
| `mounted_has_pricing` | boolean | Pricing routes exist |
| `pricing_paths` | array | Pricing route paths |
| `mounted_has_channel_connections` | boolean | Channel routes exist |
| `channel_connections_paths` | array | Channel route paths |

## Troubleshooting

### 401 Unauthorized

**Symptom:** "Unauthorized" error when loading page

**Cause:** Session expired or not logged in.

**Resolution:**
1. Refresh page (triggers re-auth)
2. Log out and log in again
3. Check Supabase session

### Empty Modules List

**Symptom:** "Keine Module registriert" message

**Cause:** Module system disabled or no modules loaded.

**Resolution:**
1. Check `modules_enabled` card — should show "Aktiv"
2. If inactive, check `MODULES_ENABLED` environment variable
3. Check backend logs for module registration errors

### Missing Routes

**Symptom:** Expected route not in mounted_prefixes

**Cause:** Module not loaded or router not mounted.

**Resolution:**
1. Find the module that should provide the route
2. Check if module appears in modules list
3. Check module's prefixes — does it include expected prefix?
4. Check backend startup logs for mounting errors

## Internal API Proxy

The Admin UI uses an internal API proxy route:

| UI Request | Internal Proxy | Backend Endpoint |
|------------|----------------|------------------|
| GET modules | `/api/internal/ops/modules` | `GET /api/v1/ops/modules` |

**Proxy Location:** `frontend/app/api/internal/ops/modules/route.ts`

## Smoke Test

**Script:** `backend/scripts/pms_ops_modules_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage (requires JWT_TOKEN)
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_ops_modules_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_ops_modules_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT (admin/manager) |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |

### What It Tests

1. **Health check:** GET /health → HTTP 200
2. **Modules endpoint:** GET /api/v1/ops/modules → HTTP 200
3. **Response fields:** modules_enabled, total_modules, modules, mounted_prefixes present
4. **Modules structure:** First module has 'name' field

### Expected Result

```
RESULT: PASS
Summary: PASS=7, FAIL=0, SKIP=0
```

## Related Documentation

- [Ops Routes](../../api/ops.md) — Backend endpoint documentation
- [Scripts README](../../../scripts/README.md#pms_ops_modules_smokesh) — Smoke test documentation
