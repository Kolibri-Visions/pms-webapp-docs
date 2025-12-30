# Frontend Ops Console

**Purpose**: Document frontend Ops Console pages (`/ops/*`)

**Audience**: Frontend developers, ops engineers

**Source of Truth**: `frontend/app/ops/layout.tsx`, `frontend/middleware.ts`

---

## Overview

The Ops Console provides **admin-only operational tools** via frontend pages at `/ops/*`.

**Status**: Implemented (frontend SSR pages)

**Access**: Admin role required + feature flag enabled

**Feature Flag**: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` (default: unset, disabled)

**Important**: This is the **FRONTEND** Ops Console. The **BACKEND** `/ops/*` API router exists but is **NOT MOUNTED** (dead code).

---

## Frontend vs Backend Ops Routes

### Frontend Ops Console (ACTIVE)

**Routes**: `/ops/*` (Next.js SSR pages)

**Status**: ✅ Implemented and active

**Location**: `frontend/app/ops/`

**Access Control**: Server-side session check + admin role check + feature flag

**Examples** (assumed, check code):
- `/ops/dashboard` - Ops dashboard
- `/ops/logs` - System logs
- `/ops/sync` - Sync status

---

### Backend Ops API (DEAD CODE, NOT MOUNTED)

**Routes**: `/ops/*` (FastAPI endpoints)

**Status**: ❌ EXISTS but NOT MOUNTED (dead code)

**Location**: `backend/app/routers/ops.py`

**Why Not Mounted**: Router exists but never imported in `backend/app/main.py` or module system

**Endpoints Defined** (but NOT accessible):
- `GET /ops/current-commit` - Git commit SHA (stub)
- `GET /ops/env-sanity` - Environment sanity check (stub)

**Related Docs**: [status-review-v3/DRIFT_REPORT.md](../_staging/status-review-v3/DRIFT_REPORT.md#critical-drift-ops-router-status)

**Future**: Backend `/ops/*` API may be mounted in future phases (TBD)

---

## Access Control

### 1. Server-Side Session Check

**Where**: `frontend/app/ops/layout.tsx:27-40`

**What**: Verify user has valid Supabase session (server-side)

**Behavior**:
- ✅ Valid session: Continue to role check
- ❌ No session: Redirect to `/login?next=/ops/...` (preserves original path)

**Code**:
```typescript
const { data: { session }, error: sessionError } = await supabase.auth.getSession();

if (!session || sessionError) {
  const loginUrl = `/login?next=${encodeURIComponent(pathname)}`;
  redirect(loginUrl);
}
```

---

### 2. Admin Role Check

**Where**: `frontend/app/ops/layout.tsx:46-92`

**What**: Query `team_members` table to verify `role='admin'`

**Behavior**:
- ✅ Admin role: Continue to feature flag check
- ❌ Not admin: Show "Access Denied" message (no redirect loop)

**Code**:
```typescript
const { data: teamMembers } = await supabase
  .from('team_members')
  .select('user_id, agency_id, role, is_active')
  .eq('user_id', userId)
  .eq('is_active', true);

// Determine admin status
const resolvedRole = selectedMember.role;
const isAdmin = resolvedRole?.toLowerCase() === 'admin';
```

**Related Docs**: [Frontend Authentication](authentication.md#step-2-admin-role-check-lines-46-92)

---

### 3. Feature Flag Check

**Where**: `frontend/app/ops/layout.tsx:95-140`

**What**: Check `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` environment variable

**Behavior**:
- ✅ Feature flag set: Render ops pages
- ❌ Feature flag unset: Show "Ops Console is Disabled" message

**Code**:
```typescript
const opsConsoleEnabled =
  process.env.NEXT_PUBLIC_ENABLE_OPS_CONSOLE &&
  ['1', 'true', 'yes', 'on'].includes(
    process.env.NEXT_PUBLIC_ENABLE_OPS_CONSOLE.toLowerCase().trim()
  );

if (!opsConsoleEnabled) {
  return (
    <div>
      <h1>Ops Console is Disabled</h1>
      <p>Set NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1 in environment variables and redeploy.</p>
    </div>
  );
}
```

**Related Docs**: [Feature Flags](../ops/feature-flags.md#next_public_enable_ops_console)

---

## No Redirect Loop

**Important**: Non-admin users see "Access Denied" message, NOT redirect to `/channel-sync`

**Why**: Prevents infinite redirect loops

**Code** (`frontend/app/ops/layout.tsx:143-238`):
```typescript
if (!isAdmin) {
  return (
    <div className="...">
      <h1>Access Denied</h1>
      <p>You do not have permission to access this page. Only admins can access the Ops Console.</p>
      {/* Link to channel-sync, but no automatic redirect */}
      <a href="/channel-sync">Go to Channel Sync</a>
    </div>
  );
}
```

---

## Middleware Protection

**Where**: `frontend/middleware.ts:77-82`

**What**: Middleware applies to `/ops/:path*` (session refresh)

**Config**:
```typescript
export const config = {
  matcher: [
    '/ops/:path*',     // ← Ops Console protected
    '/channel-sync/:path*',
    '/login',
  ],
};
```

**Purpose**: Refresh Supabase session cookies before server components run

**Related Docs**: [Frontend Authentication - Middleware](authentication.md#middleware-session-refresh)

---

## Feature Flag Configuration

### Enable Ops Console

**Environment Variable**: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE`

**Values**: `1` | `true` | `yes` | `on` (case-insensitive)

**Where to Set** (deployment platform):
- Coolify: Project settings → Environment variables
- Vercel: Project settings → Environment variables
- Other: Check platform-specific docs

**Example**:
```bash
# .env.local (local development)
NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1
```

**After Setting**: Redeploy frontend (rebuild required for Next.js env vars)

**Related Docs**: [Feature Flags](../ops/feature-flags.md#next_public_enable_ops_console)

---

## Deployment Checklist

### Production Deployment

**Frontend**:
- ✅ Set `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1` if ops staff need access
- ✅ Ensure admin users exist in `team_members` table with `role='admin'`
- ✅ Test login flow: `/login` → `/ops/dashboard` (preserves `?next=/ops/dashboard`)

**Backend** (related):
- ⚠️ Backend `/ops/*` API is NOT mounted (dead code, unless changed in future)

---

## Ops Console Pages (Assumed, Check Code)

**Assumed Routes** (check `frontend/app/ops/` for actual pages):
- `/ops/dashboard` - Ops dashboard (overview)
- `/ops/logs` - System logs viewer
- `/ops/sync` - Sync status (channel manager, availability, etc.)
- `/ops/health` - Health checks (backend, database, redis)
- `/ops/users` - User management (RBAC, roles)

**Note**: Actual pages may differ - check `frontend/app/ops/` directory for complete list

---

## Troubleshooting

### Ops Console Shows "Ops Console is Disabled"

**Symptom**: Admin users see "Ops Console is Disabled" instead of ops pages

**Cause**: `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` not set or set to false

**Fix**:
1. Set `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1` in environment variables
2. Redeploy frontend (rebuild required)
3. Test: Navigate to `/ops/dashboard`

**Related Docs**: [Feature Flags - Troubleshooting](../ops/feature-flags.md#ops-console-shows-disabled-message)

---

### Non-Admin Users See "Access Denied"

**Symptom**: Authenticated users see "Access Denied" message

**Cause**: User's `role` in `team_members` table is not `'admin'`

**Fix**:
1. Verify user exists in `team_members` table:
   ```sql
   SELECT user_id, role, is_active FROM team_members WHERE user_id = '<user_id>';
   ```
2. Update user role to admin:
   ```sql
   UPDATE team_members SET role = 'admin' WHERE user_id = '<user_id>';
   ```
3. Test: User logs out and logs back in, navigates to `/ops/dashboard`

---

### Redirect Loop on `/ops/*`

**Symptom**: Infinite redirects between `/ops/dashboard` and `/login` or `/channel-sync`

**Cause**: Access denied logic redirects instead of showing message

**Fix**: Check `frontend/app/ops/layout.tsx` - should show "Access Denied" message, NOT redirect

**Expected Behavior**: Non-admin users see static "Access Denied" message with link to `/channel-sync` (no automatic redirect)

---

## Code References

**Frontend Ops Layout**:
- `frontend/app/ops/layout.tsx` - Server-side auth + role check + feature flag

**Middleware**:
- `frontend/middleware.ts` - Session refresh for `/ops/*` routes

**Backend Ops Router** (DEAD CODE):
- `backend/app/routers/ops.py` - Backend ops router (NOT MOUNTED)

---

## Related Documentation

- [Frontend Authentication](authentication.md) - SSR auth, session refresh, role checks
- [Feature Flags](../ops/feature-flags.md#next_public_enable_ops_console) - `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` flag
- [status-review-v3/DRIFT_REPORT.md](../_staging/status-review-v3/DRIFT_REPORT.md#critical-drift-ops-router-status) - Backend ops router dead code

---

**Last Updated**: 2025-12-30
**Maintained By**: Frontend Team
