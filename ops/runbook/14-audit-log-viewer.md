# Audit-Log Viewer Admin UI

This runbook chapter covers the Audit-Log Viewer feature in the Admin UI.

**When to use:** Investigating actions performed in the system, auditing user behavior, or troubleshooting issues.

## Overview

The Audit-Log Viewer Admin UI allows administrators to:

1. **View audit entries** — List all logged actions with filtering and pagination
2. **Filter by date** — Use presets (today, 7 days, 30 days) or custom date range
3. **Filter by action/entity** — Filter by action type or entity type
4. **View details** — Open detail modal with full entry metadata
5. **Export CSV** — Download filtered entries as CSV (Excel-compatible)

**Access:** Admin role required.

## Features

### Date Presets

**UI Location:** Audit-Log page → "Zeitraum" dropdown

**Available Presets:**
| Preset | Label | Description |
|--------|-------|-------------|
| `today` | Heute | From midnight today to now |
| `7days` | Letzte 7 Tage | Last 7 days |
| `30days` | Letzte 30 Tage | Last 30 days |
| `custom` | Benutzerdefiniert | Custom date range (date pickers) |

### Filtering

**UI Location:** Audit-Log page → Filter inputs

**Available Filters:**
| Filter | Description |
|--------|-------------|
| Aktion | Action type (e.g., booking_request_approved) |
| Entitäts-Typ | Entity type (e.g., booking_request, booking) |

### Pagination

- Default 25 entries per page
- Navigation: Zurück / Weiter buttons
- Disabled appropriately at start/end

### Detail Modal

**UI Location:** Click any row → Opens detail panel

**Shows:**
- All fields from audit entry
- Copy button for IDs (Request-ID, Entity-ID, etc.)
- Metadata JSON formatted

### CSV Export

**UI Location:** "CSV Export" button (top right)

**Features:**
- Applies current filters
- UTF-8 BOM for Excel compatibility
- German column headers
- Timestamped filename

## API Endpoints

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| List entries | `/api/v1/ops/audit-log` | GET | admin |
| Export CSV | `/api/v1/ops/audit-log/export` | GET | admin |

### Query Parameters (List)

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `action` | string | - | Filter by action |
| `entity_type` | string | - | Filter by entity type |
| `entity_id` | UUID | - | Filter by entity ID |
| `actor_user_id` | UUID | - | Filter by actor user |
| `from_date` | datetime | - | Filter from date (ISO 8601) |
| `to_date` | datetime | - | Filter to date (ISO 8601) |
| `limit` | int | 50 | Max records (1-500) |
| `offset` | int | 0 | Pagination offset |

### Query Parameters (Export)

Same as list, but:
- `limit` default: 1000 (max: 5000)
- No `offset` (full export)

## Troubleshooting

### 401 Unauthorized

**Symptom:** "Unauthorized" error when loading page

**Cause:** Session expired or not logged in.

**Resolution:**
1. Refresh page (triggers re-auth)
2. Log out and log in again
3. Check Supabase session

### 403 Forbidden

**Symptom:** "Forbidden" error when loading audit log

**Cause:** User does not have admin role.

**Resolution:**
1. Verify user's role in `team_members` table
2. Only admins can access audit log
3. Check JWT token has correct permissions

### No Entries Displayed

**Symptom:** Empty table despite expected data

**Cause:** Filters too restrictive or no data in date range.

**Resolution:**
1. Reset filters (remove action/entity type)
2. Expand date range (use "30 days" or "custom" with wider range)
3. Check audit_log table directly:
   ```sql
   SELECT COUNT(*) FROM audit_log WHERE agency_id = '<agency_id>';
   ```

### CSV Export Fails

**Symptom:** Export button does nothing or shows error

**Cause:** Large result set timeout or auth issue.

**Resolution:**
1. Apply more restrictive filters
2. Check browser network tab for error response
3. Verify JWT token is still valid

## Internal API Proxy

The Admin UI uses internal API proxy routes to forward requests to the backend:

| UI Request | Internal Proxy | Backend Endpoint |
|------------|----------------|------------------|
| GET list | `/api/internal/ops/audit-log` | `GET /api/v1/ops/audit-log` |
| GET export | `/api/internal/ops/audit-log/export` | `GET /api/v1/ops/audit-log/export` |

**Proxy Locations:**
- `frontend/app/api/internal/ops/audit-log/route.ts`
- `frontend/app/api/internal/ops/audit-log/export/route.ts`

## Smoke Test

**Script:** `backend/scripts/pms_audit_log_api_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage (requires JWT_TOKEN)
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_audit_log_api_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_audit_log_api_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT with admin role |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |

### What It Tests

1. **Health check:** GET /health → HTTP 200
2. **List entries:** GET /api/v1/ops/audit-log → HTTP 200, has `items` + `total` fields
3. **Filter by action:** GET with action filter → HTTP 200
4. **Date range filter:** GET with from_date/to_date → HTTP 200
5. **CSV export:** GET /api/v1/ops/audit-log/export → HTTP 200, CSV header present

### Expected Result

```
RESULT: PASS
Summary: PASS=7, FAIL=0, SKIP=0
```

Note: SKIP count varies if no audit entries exist (filter tests skip).

## Database Schema

```sql
-- audit_log table
SELECT id, created_at, action, actor_type, actor_user_id,
       entity_type, entity_id, request_id, metadata
FROM audit_log
WHERE agency_id = '<agency_id>'
ORDER BY created_at DESC
LIMIT 10;
```

### Query: Count by Action

```sql
SELECT action, COUNT(*) as count
FROM audit_log
WHERE agency_id = '<agency_id>'
GROUP BY action
ORDER BY count DESC;
```

### Query: Recent Actions by User

```sql
SELECT al.created_at, al.action, al.entity_type, p.email
FROM audit_log al
LEFT JOIN profiles p ON al.actor_user_id = p.id
WHERE al.agency_id = '<agency_id>'
  AND al.actor_user_id IS NOT NULL
ORDER BY al.created_at DESC
LIMIT 20;
```

## Related Documentation

- [P3c: Audit Logging + Idempotency](../../project_status.md) — Original audit log implementation
- [Scripts README](../../../scripts/README.md#pms_audit_log_api_smokesh) — Smoke test documentation
