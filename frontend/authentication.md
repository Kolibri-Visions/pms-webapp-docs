# Frontend Authentication (Supabase SSR)

**Purpose**: Document frontend authentication approach (SSR, session refresh, role checks)

**Audience**: Frontend developers

**Source of Truth**: `frontend/middleware.ts`, `frontend/app/ops/layout.tsx`

---

## Overview

Frontend authentication uses **Supabase Auth** with **Server-Side Rendering (SSR)** pattern.

**Auth Provider**: Supabase Auth

**Package**: `@supabase/ssr`

**Pattern**: Server-side session refresh + role checks

---

## Middleware (Session Refresh)

**Location**: `frontend/middleware.ts`

**Purpose**: Refresh Supabase auth cookies on every request to protected routes

**Why Needed**: Ensures server components can read latest session (cookies stay fresh)

### Protected Routes

**Middleware applies to** (lines 77-82):
- `/ops/:path*` - Ops Console pages
- `/channel-sync/:path*` - Channel Sync pages
- `/login` - Login page

**Configuration**:
```typescript
export const config = {
  matcher: [
    '/ops/:path*',
    '/channel-sync/:path*',
    '/login',
  ],
};
```

### Session Refresh Logic

**What It Does**:
1. Create Supabase server client (with cookie handlers)
2. Call `supabase.auth.getUser()` - triggers session refresh
3. Update cookies in request/response

**Code** (`frontend/middleware.ts:10-73`):
```typescript
export async function middleware(request: NextRequest) {
  // Clone headers and add pathname
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-pathname', request.nextUrl.pathname);

  let response = NextResponse.next({
    request: { headers: requestHeaders },
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SB_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value;
        },
        set(name: string, value: string, options: CookieOptions) {
          // Set cookie in both request and response
          request.cookies.set({ name, value, ...options });
          response.cookies.set({ name, value, ...options });
        },
        remove(name: string, options: CookieOptions) {
          // Remove cookie from both request and response
          request.cookies.set({ name, value: '', ...options });
          response.cookies.set({ name, value: '', ...options });
        },
      },
    }
  );

  // Refresh session - this updates the cookies if needed
  await supabase.auth.getUser();

  return response;
}
```

---

## Server-Side Authentication (Ops Console Example)

**Location**: `frontend/app/ops/layout.tsx`

**Purpose**: Server-side session validation + admin role check for `/ops/*` pages

### Step 1: Session Check (Lines 27-40)

**What It Does**: Verify user has valid session (server-side)

**Code**:
```typescript
// Create server-side Supabase client
const supabase = await createSupabaseServerClient();

// Get current session (server-side)
const { data: { session }, error: sessionError } = await supabase.auth.getSession();

// If no session, redirect to login immediately (server-side)
if (!session || sessionError) {
  const loginUrl = `/login?next=${encodeURIComponent(pathname)}`;
  redirect(loginUrl);
}
```

**Behavior**:
- ✅ Valid session: Continue to next step (role check)
- ❌ No session: Redirect to `/login?next=/ops/...` (preserves original path)

---

### Step 2: Admin Role Check (Lines 46-92)

**What It Does**: Query `team_members` table to verify user has `admin` role

**Code**:
```typescript
const userId = session.user.id;

// Query team_members to check admin role (authoritative check)
const { data: teamMembers, error: teamError } = await supabase
  .from('team_members')
  .select('user_id, agency_id, role, is_active')
  .eq('user_id', userId)
  .eq('is_active', true);

// Determine admin status
let isAdmin = false;
if (!teamError && teamMembers && teamMembers.length > 0) {
  // Get last_active_agency_id from profiles if available
  const { data: profile } = await supabase
    .from('profiles')
    .select('last_active_agency_id')
    .eq('id', userId)
    .single();

  // Prefer team member matching last_active_agency_id
  let selectedMember = teamMembers[0];
  if (teamMembers.length > 1 && profile?.last_active_agency_id) {
    const preferredMember = teamMembers.find(
      (m) => m.agency_id === profile.last_active_agency_id
    );
    if (preferredMember) {
      selectedMember = preferredMember;
    }
  }

  const resolvedRole = selectedMember.role;
  isAdmin = resolvedRole?.toLowerCase() === 'admin';
}
```

**Behavior**:
- ✅ User has `role='admin'`: Continue to render ops pages
- ❌ User is NOT admin: Show "Access Denied" message (no redirect loop)

---

### Step 3: Feature Flag Check (Lines 95-140)

**What It Does**: Check if Ops Console is enabled via `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` env var

**Code**:
```typescript
const opsConsoleEnabled =
  process.env.NEXT_PUBLIC_ENABLE_OPS_CONSOLE &&
  ['1', 'true', 'yes', 'on'].includes(
    process.env.NEXT_PUBLIC_ENABLE_OPS_CONSOLE.toLowerCase().trim()
  );

if (!opsConsoleEnabled) {
  return (
    <div className="...">
      <h1>Ops Console is Disabled</h1>
      <p>Set NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1 in environment variables and redeploy.</p>
    </div>
  );
}
```

**Behavior**:
- ✅ `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1`: Continue to render ops pages
- ❌ Feature flag unset: Show "Ops Console is Disabled" message

**Related Docs**: [Feature Flags](../ops/feature-flags.md#next_public_enable_ops_console)

---

## Supabase Client (Server-Side)

**Location**: `frontend/app/lib/supabase-server.ts` (assumed)

**Purpose**: Create Supabase client for server components (SSR)

**Usage**:
```typescript
import { createSupabaseServerClient } from '../lib/supabase-server';

export default async function ServerComponent() {
  const supabase = await createSupabaseServerClient();

  // Get session
  const { data: { session } } = await supabase.auth.getSession();

  // Query database (with RLS)
  const { data } = await supabase
    .from('properties')
    .select('*')
    .eq('agency_id', session.user.app_metadata.agency_id);

  return <div>...</div>;
}
```

**Note**: Server-side client automatically uses cookies from request (no manual cookie handling)

---

## Authentication Flow

### 1. User Visits Protected Route (e.g., `/ops/dashboard`)

**Step 1**: Middleware refreshes session cookies (`frontend/middleware.ts`)
**Step 2**: Server component checks session (`frontend/app/ops/layout.tsx:27-40`)
  - ❌ No session → Redirect to `/login?next=/ops/dashboard`
  - ✅ Valid session → Continue to next step

### 2. User Is Authenticated

**Step 3**: Server component checks admin role (`frontend/app/ops/layout.tsx:46-92`)
  - ❌ Not admin → Show "Access Denied" (no redirect)
  - ✅ Admin → Continue to next step

**Step 4**: Server component checks feature flag (`frontend/app/ops/layout.tsx:95-140`)
  - ❌ Feature flag unset → Show "Ops Console is Disabled"
  - ✅ Feature flag set → Render ops page

### 3. User Accesses Ops Page

**Rendered**: Ops Console page content (e.g., `/ops/dashboard`)

---

## No Redirect Loop

**Important**: Access denied shows error message, does NOT redirect to `/channel-sync`

**Why**: Prevents infinite redirect loops if user is not admin

**Code** (`frontend/app/ops/layout.tsx:143-238`):
```typescript
// If authenticated but not admin, show AccessDenied (NO redirect to /channel-sync)
if (!isAdmin) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-2xl mx-auto text-center px-4">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
        <p className="text-gray-600 mb-6">
          You do not have permission to access this page. Only admins can access the Ops Console.
        </p>
        {/* Link to channel-sync, but no automatic redirect */}
        <a href="/channel-sync" className="...">Go to Channel Sync</a>
      </div>
    </div>
  );
}
```

---

## Permission-Based Authorization (PermissionContext)

**Location**: `frontend/app/lib/contexts/PermissionContext.tsx`

**Purpose**: Granular permission checks for UI elements (buttons, menus, pages)

**Added**: 2026-02-18

### Overview

The PermissionContext provides client-side permission checks:

- **Permissions loaded from backend** via `/api/internal/permissions/me`
- **Admin bypass**: Admins have all permissions (unless impersonating)
- **Role impersonation**: Admins can preview other roles
- **Navigation filtering**: AdminShell filters menu items based on permissions

### Usage

```typescript
import { usePermissions } from "../lib/contexts/PermissionContext";

function MyComponent() {
  const { hasPermission, isAdmin, isImpersonating } = usePermissions();

  // Check single permission
  if (!hasPermission("bookings.create")) {
    return null; // Hide button
  }

  return <button>Create Booking</button>;
}
```

### Permission Codes

Format: `resource.action`

| Permission | Description |
|------------|-------------|
| `bookings.read` | View bookings |
| `bookings.create` | Create new bookings |
| `bookings.update` | Confirm/modify bookings |
| `bookings.delete` | Cancel/delete bookings |
| `properties.read` | View properties |
| `properties.create` | Create new properties |
| `properties.update` | Modify properties |
| `guests.read` | View guests |
| `guests.create` | Create guests |
| `team.read` | View team members |
| `team.manage` | Invite/manage team |
| `team.roles` | Manage roles & permissions |

### Protected UI Elements

| Page | Button | Permission |
|------|--------|------------|
| `/bookings` | "Neue Buchung" | `bookings.create` |
| `/bookings/[id]` | "Stornieren" | `bookings.delete` |
| `/bookings/[id]` | "Bestätigen" | `bookings.update` |
| `/properties` | "Neues Objekt" | `properties.create` |
| `/guests` | "Neuer Gast" | `guests.create` |
| `/team` | "Mitglied einladen" | `team.manage` |

### Navigation Filtering

**Location**: `frontend/app/components/AdminShell.tsx`

The sidebar navigation is filtered based on `NAV_PERMISSION_MAP`:

```typescript
// In PermissionContext.tsx
export const NAV_PERMISSION_MAP: Record<string, string[]> = {
  dashboard: [],                              // Everyone
  availability: ["calendar.read"],
  bookings: ["bookings.read"],
  properties: ["properties.read"],
  guests: ["guests.read"],
  team: ["team.read"],
  roles: ["team.roles"],
  // ... more mappings
};
```

**Function**: `canAccessNavItem(navKey, permissions, isAdmin)`
- Returns `true` if user has ANY of the required permissions
- Admins always have access (unless impersonating)

---

## Role Impersonation ("Als Rolle ansehen")

**Purpose**: Admins can preview the app as a different role

**Location**: `frontend/app/lib/contexts/PermissionContext.tsx`

### How It Works

1. Admin clicks "Als Rolle ansehen" on `/settings/roles`
2. `impersonateRole(role)` is called with role data + permissions
3. State saved to `localStorage` (key: `pms_impersonated_role`)
4. Navigation and buttons reflect impersonated role's permissions
5. Banner shows at top of page (ImpersonationBanner component)
6. Admin clicks "Beenden" to stop impersonation

### State Management

```typescript
// When impersonating:
isImpersonating: true
impersonatedRole: { role_id, role_code, role_name, permissions }
isAdmin: false        // Disabled during impersonation
isActualAdmin: true   // True value preserved

// Permissions from impersonated role are used for all checks
```

### ImpersonationBanner Component

**Location**: `frontend/app/components/ImpersonationBanner.tsx`

Shows when impersonating:
- Role name and permission count
- "Beenden" button to stop impersonation

**Styling**: Pink/coral background (`bg-t-accent`)

### Security Notes

- **Frontend-only**: Does NOT affect backend API calls
- Backend still validates actual user permissions
- Impersonation is for UI preview only (UX testing)

---

## Related Documentation

- [Ops Console](ops-console.md) - Frontend `/ops/*` pages
- [Feature Flags](../ops/feature-flags.md#next_public_enable_ops_console) - `NEXT_PUBLIC_ENABLE_OPS_CONSOLE` flag
- [Runbook](../ops/runbook.md) - Troubleshooting auth issues

**Code References**:
- `frontend/middleware.ts` - Session refresh middleware
- `frontend/app/ops/layout.tsx` - Server-side session + role checks
- `frontend/app/lib/supabase-server.ts` - Supabase server client (assumed)
- `frontend/app/lib/contexts/PermissionContext.tsx` - Permission context + impersonation
- `frontend/app/components/ImpersonationBanner.tsx` - Impersonation UI banner
- `frontend/app/components/AdminShell.tsx` - Navigation filtering

---

**Last Updated**: 2026-02-18
**Maintained By**: Frontend Team
