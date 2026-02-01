# Team Management Admin UI

This runbook chapter covers the Team Management features in the Admin UI.

**When to use:** Troubleshooting team role changes, member removal, or permission issues.

## Overview

The Team Management Admin UI allows administrators to:

1. **View team members** — List all members with email/user-id and role
2. **Change member role** — Update a member's role (admin/agent/owner)
3. **Remove member** — Remove a member from the agency

**Access:** Admin role required for role changes and member removal.

## Features

### Role Change

**UI Location:** Team page → Member row → Actions menu (⋮) → "Rolle ändern..."

**Workflow:**
1. Click actions menu on member row
2. Select "Rolle ändern..."
3. Choose new role from dropdown
4. Click "Speichern"

**Available Roles:**
| Role | Label | Description |
|------|-------|-------------|
| `admin` | Administrator | Full access, can manage team |
| `agent` | Mitarbeiter | Standard team member |
| `owner` | Eigentümer | Property owner access |

**Backend Endpoint:** `PATCH /api/v1/team/members/{user_id}`

**Request Body:**
```json
{
  "role": "agent"
}
```

### Remove Member

**UI Location:** Team page → Member row → Actions menu (⋮) → "Mitglied entfernen..."

**Workflow:**
1. Click actions menu on member row
2. Select "Mitglied entfernen..."
3. Confirm in dialog: "Mitglied wirklich entfernen?"
4. Click "Entfernen"

**Backend Endpoint:** `DELETE /api/v1/team/members/{user_id}`

## API Endpoints

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| List members | `/api/v1/team/members` | GET | admin, manager |
| Update role | `/api/v1/team/members/{user_id}` | PATCH | admin |
| Remove member | `/api/v1/team/members/{user_id}` | DELETE | admin |

## Troubleshooting

### 403 Forbidden on Role Change

**Symptom:** "Rollenänderung fehlgeschlagen" error when changing role

**Cause:** User does not have admin role.

**Resolution:**
1. Verify user's role in `team_members` table
2. Only admins can change roles
3. Check JWT token has correct permissions

### "Es muss mindestens ein Administrator vorhanden sein"

**Symptom:** Cannot change admin's role to non-admin

**Cause:** Backend guards against removing the last admin.

**Resolution:**
- This is expected behavior (safety guard)
- Create another admin first before downgrading current admin
- At least one admin must always exist

### 404 Member Not Found

**Symptom:** Role change or remove fails with 404

**Cause:** Member not found in agency's team_members table.

**Resolution:**
1. Refresh the team list
2. Member may have been removed by another admin
3. Check `team_members` table for member existence

### Member Cannot Be Removed

**Symptom:** Delete fails with 400 error

**Cause:** Possible causes:
- Trying to remove the last admin
- Trying to remove self (if last admin)

**Resolution:**
1. Check error message for specific guard
2. Ensure another admin exists before removing an admin
3. Transfer admin role to another user first

## Internal API Proxy

The Admin UI uses internal API proxy routes to forward requests to the backend:

| UI Request | Internal Proxy | Backend Endpoint |
|------------|----------------|------------------|
| PATCH role | `/api/internal/team/members/{user_id}` | `PATCH /api/v1/team/members/{user_id}` |
| DELETE member | `/api/internal/team/members/{user_id}` | `DELETE /api/v1/team/members/{user_id}` |

**Proxy Location:** `frontend/app/api/internal/team/members/[user_id]/route.ts`

## Smoke Test

**Script:** `backend/scripts/pms_team_role_remove_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage (requires JWT_TOKEN)
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_team_role_remove_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_team_role_remove_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT with admin role |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |

### What It Tests

1. **Preflight:** GET /health → HTTP 200
2. **List members:** GET /api/v1/team/members → HTTP 200, has `members` array
3. **Role change:** PATCH role on non-admin member (toggle agent↔owner, then revert)
4. **Delete endpoint:** Verify 404 for non-existent member (actual delete SKIPPED)

### DELETE Step: Why SKIPPED

The smoke test **SKIPs** actual member deletion for safety:
- No disposable test user creation in headless mode
- Deleting real members in PROD would be destructive
- Invite+accept flow requires email confirmation (not headless)

The test verifies the DELETE endpoint responds correctly (404 for fake UUID) without performing destructive actions.

### Expected Result

```
RESULT: PASS
Summary: PASS=4, FAIL=0, SKIP=2
```

Note: SKIP count varies based on team composition (e.g., if only admins exist, role toggle skips).

## Database Schema

```sql
-- team_members table
SELECT id, user_id, agency_id, role, is_active, created_at, updated_at
FROM team_members
WHERE agency_id = '<agency_id>';
```

### Query: Check Admin Count

```sql
SELECT COUNT(*) as admin_count
FROM team_members
WHERE agency_id = '<agency_id>'
  AND role = 'admin'
  AND is_active = true;
```

### Query: List All Members with Email

```sql
SELECT tm.id, tm.user_id, tm.role, p.email
FROM team_members tm
LEFT JOIN profiles p ON tm.user_id = p.id
WHERE tm.agency_id = '<agency_id>'
  AND tm.is_active = true;
```

## Related Documentation

- [Epic A API Routes](../../api/epic_a.md) — Team management API details
- [Scripts README](../../../scripts/README.md#pms_team_role_remove_smokesh) — Smoke test documentation
