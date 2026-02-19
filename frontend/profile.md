# User Profile Management

**Purpose**: Document user profile pages, API routes, and i18n integration

**Audience**: Frontend developers

**Source of Truth**: `frontend/app/profile/`, `frontend/app/api/internal/profile/`

---

## Overview

User profile management allows authenticated users to:

- View and edit profile data (name, display name, phone, avatar)
- Change language and timezone preferences
- Manage notification settings
- Change password
- View active sessions (security)

**Profile Data Source**: `profiles` table in Supabase

**Authentication**: Session-based using `@supabase/ssr`

---

## Pages

### Profile View (`/profile`)

**Location**: `frontend/app/profile/page.tsx`

**Purpose**: Display user profile summary with read-only data

**Features**:
- Avatar display (or initials fallback)
- Name, email, phone display
- Language and timezone display
- Notification preferences summary
- Links to edit profile and security settings

### Profile Edit (`/profile/edit`)

**Location**: `frontend/app/profile/edit/page.tsx`

**Purpose**: Edit profile data and upload avatar

**Editable Fields**:
| Field | Type | Validation |
|-------|------|------------|
| `first_name` | Text | Max 100 chars |
| `last_name` | Text | Max 100 chars |
| `display_name` | Text | Max 200 chars (optional override) |
| `phone` | Text | Max 50 chars |
| `avatar_url` | Image | Max 2MB, JPEG/PNG/WebP/GIF |
| `preferred_language` | Select | "de" or "en" |
| `preferred_timezone` | Select | IANA timezone |
| `notification_preferences` | JSON | Email/push toggles |

**Avatar Upload**:
- Uses `/api/internal/profile/avatar` endpoint
- File stored in `avatars` Supabase Storage bucket
- Auto-deletes old avatar on new upload
- File naming: `{user_id}.{extension}`

### Security Settings (`/profile/security`)

**Location**: `frontend/app/profile/security/page.tsx`

**Purpose**: Password change and session management

**Features**:
- Password change form with validation
- Active sessions list
- End all other sessions button
- 2FA placeholder (coming soon)

**Password Requirements**:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 number

---

## API Routes

### Profile GET/PATCH (`/api/internal/profile`)

**Location**: `frontend/app/api/internal/profile/route.ts`

**Authentication**: Session-based (cookies)

#### GET `/api/internal/profile`

**Purpose**: Fetch current user's profile data

**Response Fields**:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "Johnny",
  "avatar_url": "https://supabase.../avatars/uuid.jpg",
  "phone": "+49 123 456 789",
  "preferred_language": "de",
  "preferred_timezone": "Europe/Berlin",
  "notification_preferences": {
    "email": { "bookings": true, "payments": true, "reminders": true },
    "push": { "bookings": true, "payments": false, "reminders": true }
  },
  "last_login_at": "2026-02-19T10:00:00Z",
  "created_at": "2026-01-15T08:30:00Z",
  "role": "admin",
  "role_name": "Administrator",
  "agency_id": "uuid",
  "agency_name": "LuxeStay Agency"
}
```

#### PATCH `/api/internal/profile`

**Purpose**: Update profile data

**Allowed Fields** (whitelist):
- `first_name`
- `last_name`
- `display_name`
- `phone`
- `preferred_language`
- `preferred_timezone`
- `notification_preferences`
- `avatar_url`

**Behavior**:
- Creates profile record if not exists (INSERT)
- Updates existing profile (UPDATE)
- Auto-sets `updated_at` timestamp

**Code** (`frontend/app/api/internal/profile/route.ts:161-193`):
```typescript
// Check if profile exists
const { data: existingProfile } = await supabase
  .from("profiles")
  .select("id")
  .eq("id", userId)
  .single();

if (existingProfile) {
  // Update existing profile
  const result = await supabase.from("profiles").update(updateData)...
} else {
  // Insert new profile
  const result = await supabase.from("profiles").insert({...})...
}
```

### Avatar Upload (`/api/internal/profile/avatar`)

**Location**: `frontend/app/api/internal/profile/avatar/route.ts`

**Authentication**: Session-based (cookies)

#### POST `/api/internal/profile/avatar`

**Purpose**: Upload new avatar image

**Request**: `multipart/form-data` with `file` field

**Validation**:
- Max size: 2MB
- Allowed types: `image/jpeg`, `image/png`, `image/webp`, `image/gif`

**Process**:
1. Validate file type and size
2. Delete existing avatar(s) for user
3. Upload new avatar to `avatars` bucket
4. Update `avatar_url` in profiles table
5. Return public URL

**Code** (`frontend/app/api/internal/profile/avatar/route.ts:66-67`):
```typescript
const fileExt = file.name.split(".").pop()?.toLowerCase() || "jpg";
const filePath = `${userId}.${fileExt}`;
```

#### DELETE `/api/internal/profile/avatar`

**Purpose**: Remove avatar image

**Process**:
1. Find and delete avatar files matching user ID
2. Set `avatar_url` to `null` in profiles table

### Password Change (`/api/internal/auth/password`)

**Location**: `frontend/app/api/internal/auth/password/route.ts`

**Authentication**: Session-based (cookies)

#### POST `/api/internal/auth/password`

**Purpose**: Change user password

**Request Body**:
```json
{
  "current_password": "...",
  "new_password": "..."
}
```

**Process**:
1. Get user email from session
2. Verify current password via `signInWithPassword`
3. Update password via `updateUser`

### Sessions (`/api/internal/auth/sessions`)

**Location**: `frontend/app/api/internal/auth/sessions/route.ts`

**Authentication**: Session-based (cookies)

#### GET `/api/internal/auth/sessions`

**Purpose**: Get active sessions (mock data for now)

**Note**: Returns mock session data since Supabase doesn't expose session list

#### DELETE `/api/internal/auth/sessions`

**Purpose**: Sign out from all other sessions

**Body**: `{ "all_others": true }`

**Process**: Calls `supabase.auth.signOut()` (signs out current session too)

---

## Storage Bucket (Avatars)

**Bucket Name**: `avatars`

**Location**: Supabase Storage

**Migration**: `supabase/migrations/20260219100000_add_avatars_storage.sql`

### Configuration

| Setting | Value |
|---------|-------|
| Public | Yes (URLs accessible without auth) |
| File Size Limit | 2MB |
| Allowed MIME Types | `image/jpeg`, `image/png`, `image/webp`, `image/gif` |

### RLS Policies

| Policy | Action | Who | Condition |
|--------|--------|-----|-----------|
| `avatars_public_read` | SELECT | Anyone | `bucket_id = 'avatars'` |
| `avatars_auth_insert` | INSERT | Authenticated | File named `{user_id}.{ext}` |
| `avatars_auth_update` | UPDATE | Authenticated | File named `{user_id}.{ext}` |
| `avatars_auth_delete` | DELETE | Authenticated | File named `{user_id}.{ext}` |

---

## Database Schema

### profiles Table

**Migration**: `supabase/migrations/20260219110000_add_missing_profiles_columns.sql`

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | UUID | PK | User ID (FK to auth.users) |
| `first_name` | VARCHAR(100) | NULL | User first name |
| `last_name` | VARCHAR(100) | NULL | User last name |
| `display_name` | VARCHAR(200) | NULL | Display name override |
| `avatar_url` | TEXT | NULL | URL to avatar in storage |
| `phone` | VARCHAR(50) | NULL | Phone number |
| `preferred_language` | VARCHAR(10) | 'de' | UI language (de, en) |
| `preferred_timezone` | VARCHAR(50) | 'Europe/Berlin' | Timezone |
| `notification_preferences` | JSONB | {...} | Email/push settings |
| `last_login_at` | TIMESTAMPTZ | NULL | Last login timestamp |
| `last_active_agency_id` | UUID | NULL | Last used agency |
| `created_at` | TIMESTAMPTZ | NOW() | Profile created |
| `updated_at` | TIMESTAMPTZ | NULL | Last modified |

---

## i18n Integration

**Translation Files**:
- `frontend/app/i18n/de.json` (German)
- `frontend/app/i18n/en.json` (English)

### Translation Keys

**Profile Section**:
```json
{
  "profile": {
    "title": "Profil",
    "edit": "Profil bearbeiten",
    "personalInfo": "Persönliche Informationen",
    "preferences": "Einstellungen",
    "notifications": "Benachrichtigungen",
    "security": "Sicherheit"
  }
}
```

**Security Section**:
```json
{
  "security": {
    "title": "Sicherheit",
    "changePassword": "Passwort ändern",
    "currentPassword": "Aktuelles Passwort",
    "newPassword": "Neues Passwort",
    "confirmPassword": "Passwort bestätigen",
    "passwordRequirements": "Min. 8 Zeichen, 1 Großbuchstabe, 1 Zahl",
    "activeSessions": "Aktive Sitzungen",
    "currentSession": "Aktuelle Sitzung",
    "endSession": "Beenden",
    "endAllSessions": "Alle anderen beenden",
    "lastActive": "Zuletzt aktiv",
    "twoFactor": "Zwei-Faktor-Authentifizierung",
    "twoFactorDescription": "Erhöhte Sicherheit für Ihr Konto",
    "comingSoon": "Demnächst verfügbar"
  }
}
```

### Usage

```typescript
import { useTranslation } from "../../lib/i18n";

export default function ProfilePage() {
  const { t, language, setLanguage } = useTranslation();

  return (
    <h1>{t("profile.title")}</h1>
  );
}
```

---

## AdminShell Integration

**Location**: `frontend/app/components/AdminShell.tsx`

### Profile Data in Topbar

The topbar profile dropdown fetches profile data via `/api/internal/profile`:

**Code** (`frontend/app/components/AdminShell.tsx:278-294`):
```typescript
// Fetch profile data for topbar display
useEffect(() => {
  const fetchProfile = async () => {
    const response = await fetch("/api/internal/profile");
    if (response.ok) {
      const data = await response.json();
      setProfileData({
        display_name: data.display_name,
        first_name: data.first_name,
        last_name: data.last_name,
        avatar_url: data.avatar_url,
      });
    }
  };
  fetchProfile();
}, []);
```

### Display Name Logic

**Priority Order**:
1. `display_name` (if set)
2. `first_name` + `last_name` (concatenated)
3. Username from `userName` prop (email prefix if email)
4. "User" (fallback)

**Code** (`frontend/app/components/AdminShell.tsx:405-420`):
```typescript
const getUserDisplayName = () => {
  if (profileData?.display_name) {
    return profileData.display_name;
  }
  if (profileData?.first_name || profileData?.last_name) {
    return [profileData.first_name, profileData.last_name].filter(Boolean).join(" ");
  }
  if (userName) {
    if (userName.includes("@")) {
      return userName.split("@")[0];
    }
    return userName;
  }
  return "User";
};
```

### Avatar Display

**Topbar Button**:
- Shows avatar image if `avatar_url` exists
- Falls back to User icon

**Dropdown Header**:
- Shows avatar image or initials circle
- Display name and role

---

## Code References

**Frontend Pages**:
- `frontend/app/profile/page.tsx` - Profile view
- `frontend/app/profile/edit/page.tsx` - Profile edit
- `frontend/app/profile/security/page.tsx` - Security settings

**API Routes**:
- `frontend/app/api/internal/profile/route.ts` - Profile GET/PATCH
- `frontend/app/api/internal/profile/avatar/route.ts` - Avatar POST/DELETE
- `frontend/app/api/internal/auth/password/route.ts` - Password change
- `frontend/app/api/internal/auth/sessions/route.ts` - Sessions

**Migrations**:
- `supabase/migrations/20260219100000_add_avatars_storage.sql` - Storage bucket
- `supabase/migrations/20260219110000_add_missing_profiles_columns.sql` - Profile columns

**i18n**:
- `frontend/app/i18n/de.json` - German translations
- `frontend/app/i18n/en.json` - English translations

**Components**:
- `frontend/app/components/AdminShell.tsx` - Topbar profile dropdown

---

**Last Updated**: 2026-02-19
**Maintained By**: Frontend Team
