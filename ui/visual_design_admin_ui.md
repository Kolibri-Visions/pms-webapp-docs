# Admin UI Visual Design System

**Last Updated:** 2026-01-05
**Status:** Implemented
**Scope:** Admin Console (Backend Office)

## Overview

The Admin UI implements a modern, elegant, and soft visual language with consistent navigation and layout patterns across all administrative features.

## Design Principles

### 1. Soft + Elegant + Modern
- **Calm surfaces**: White backgrounds with subtle gray borders
- **Clear hierarchy**: Typography scale with proper weight distribution
- **Gentle contrast**: Indigo primary color with soft gray neutrals
- **Consistent spacing**: 4/8/12/16/24 px rhythm
- **Subtle interactions**: Smooth transitions on hover/active/focus states

### 2. Clarity and Efficiency
- Information density balanced with whitespace
- Tables with clear column headers and row separation
- Form inputs with visible focus states
- Empty/error/loading states always present

### 3. Accessibility First
- High contrast text (WCAG AA minimum)
- Keyboard navigation support
- Focus indicators on interactive elements
- Semantic HTML structure

## Layout Architecture

### Admin Shell Structure

```
┌─────────────────────────────────────────────────────┐
│  Sidebar (Collapsible)  │  Main Content Area       │
│                         │  ┌────────────────────┐  │
│  [Logo/Agency]          │  │  Topbar            │  │
│                         │  │  - Page Title      │  │
│  Übersicht              │  │  - User Info       │  │
│  - Dashboard            │  │  - Logout          │  │
│                         │  └────────────────────┘  │
│  Betrieb                │                          │
│  - Objekte              │  ┌────────────────────┐  │
│  - Buchungen            │  │                    │  │
│  - Verfügbarkeit        │  │  Page Content      │  │
│                         │  │                    │  │
│  Channel Manager        │  │                    │  │
│  - Verbindungen         │  │                    │  │
│  - Sync-Protokoll       │  │                    │  │
│                         │  └────────────────────┘  │
│  CRM                    │                          │
│  - Gäste                │                          │
│                         │                          │
│  Einstellungen [+/-]    │                          │
│  - Branding             │                          │
│  - Rollen & Rechte 🔒   │                          │
│  - Plan & Abrechnung 🔒 │                          │
│                         │                          │
│  [← Einklappen]         │                          │
└─────────────────────────────────────────────────────┘
```

### Sidebar Navigation

**Desktop (> 1024px):**
- Default width: 256px (w-64)
- Collapsed width: 80px (w-20)
- Sticky positioning (top: 0)
- Collapsible via toggle button at bottom
- State persisted in localStorage

**Mobile (< 1024px):**
- Drawer overlay pattern
- Full-width drawer (256px)
- Dark backdrop (50% opacity black)
- Hamburger menu icon in topbar
- Swipe-to-close support

**Navigation Groups:**
1. **Übersicht** - Dashboard and high-level views
2. **Betrieb** - Core operations (Properties, Bookings, Availability)
3. **Channel Manager** - Integrations and sync
4. **CRM** - Customer relationship (Guests)
5. **Einstellungen** - Settings (collapsible group)

### Active State Behavior

- **Current route**: Indigo background (bg-indigo-50) + indigo text (text-indigo-700)
- **Auto-expand**: Settings group expands when any settings page is active
- **Page title**: Topbar shows current page label from active nav item
- **Breadcrumbs**: Not implemented (page title sufficient for current depth)

## Component Patterns

### Tables

**Structure:**
- White background with border
- Gray header row (bg-gray-50)
- Hover state on rows (hover:bg-gray-50)
- Dividers between rows (divide-y divide-gray-200)
- Clickable rows with cursor-pointer

**Columns:**
- Left-aligned text
- Consistent padding (px-6 py-4)
- Uppercase headers (text-xs uppercase tracking-wider)
- Truncate long content with ellipsis

**Pagination:**
- Separate card below table
- Show range: "Zeige X bis Y von Z"
- Prev/Next buttons + page counter
- Disabled state for unavailable actions

### Forms

**Input Fields:**
- Border: border-gray-300
- Focus: ring-2 ring-indigo-500
- Padding: px-4 py-2
- Rounded: rounded-lg
- Full width in containers

**Buttons:**
- **Primary**: bg-indigo-600 hover:bg-indigo-700 (white text)
- **Secondary**: border border-gray-300 hover:bg-gray-50 (gray text)
- **Danger**: bg-red-600 hover:bg-red-700 (white text)
- Consistent padding: px-4 py-2
- Rounded: rounded-lg
- Font weight: font-medium

### Cards

**Standard Card:**
```tsx
<div className="bg-white rounded-lg border border-gray-200 p-6">
  <h2 className="text-lg font-semibold text-gray-900 mb-4">Title</h2>
  {/* Content */}
</div>
```

**Usage:**
- Detail views
- Form sections
- Stat summaries
- Settings panels

### Modals/Drawers

**Pattern:**
- Overlay: bg-black bg-opacity-50
- Panel: bg-white with shadow
- Close button: top-right
- Action buttons: bottom-right
- Max width: max-w-2xl

### Empty States

**Structure:**
```tsx
<div className="p-12 text-center text-gray-500">
  <div className="text-4xl mb-4">{emoji}</div>
  <p className="text-gray-900 font-medium">{title}</p>
  <p className="text-sm text-gray-600 mt-1">{description}</p>
</div>
```

**Examples:**
- 👥 No guests found
- 📅 No bookings
- 🔗 No connections

### Loading States

**Spinner:**
```tsx
<div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
```

**Skeleton Loaders:**
- Use for table rows
- Animated pulse effect
- Gray background placeholders

### Error States

**Structure:**
```tsx
<div className="p-12 text-center">
  <div className="text-red-600 mb-2">⚠️</div>
  <p className="text-gray-900 font-medium">{title}</p>
  <p className="text-sm text-gray-600 mt-1">{message}</p>
  <button onClick={retry}>Retry</button>
</div>
```

## Color System

### Primary Palette
- **Indigo 600**: #4f46e5 (primary actions, active states)
- **Indigo 700**: #4338ca (hover states)
- **Indigo 50**: #eef2ff (active backgrounds)

### Neutral Palette
- **Gray 900**: #111827 (headings)
- **Gray 700**: #374151 (body text)
- **Gray 600**: #4b5563 (secondary text)
- **Gray 500**: #6b7280 (labels, placeholders)
- **Gray 200**: #e5e7eb (borders)
- **Gray 100**: #f3f4f6 (hover backgrounds)
- **Gray 50**: #f9fafb (table headers, page background)
- **White**: #ffffff (cards, main surfaces)

### Semantic Colors
- **Success**: Green 600 (#16a34a)
- **Warning**: Yellow 600 (#ca8a04)
- **Error**: Red 600 (#dc2626)
- **Info**: Blue 600 (#2563eb)

### Status Indicators
- **VIP**: Yellow 100 bg / Yellow 800 text
- **Blacklisted**: Red 100 bg / Red 800 text
- **Active**: Green 100 bg / Green 800 text
- **Locked**: Gray 400 with 🔒 icon

## Typography Scale

### Font Family
- **Primary**: Inter (Google Fonts)
- **Fallback**: system-ui, sans-serif

### Type Scale
- **Heading 1**: text-2xl font-bold (page titles)
- **Heading 2**: text-lg font-semibold (section titles)
- **Heading 3**: text-base font-semibold (subsections)
- **Body**: text-sm (tables, forms, general content)
- **Small**: text-xs (labels, captions)

### Font Weights
- **Bold**: 700 (headings)
- **Semibold**: 600 (subheadings)
- **Medium**: 500 (buttons, emphasized text)
- **Regular**: 400 (body text)

## Spacing System

**Base unit:** 4px (Tailwind default)

**Common values:**
- **xs**: 4px (gap-1, p-1)
- **sm**: 8px (gap-2, p-2)
- **md**: 12px (gap-3, p-3)
- **lg**: 16px (gap-4, p-4)
- **xl**: 24px (gap-6, p-6)
- **2xl**: 32px (gap-8, p-8)

**Section spacing:**
- Between major sections: space-y-6
- Within cards: space-y-3 or space-y-4
- Between form fields: space-y-4

## Border Radius

- **Default**: rounded-lg (8px) - cards, buttons, inputs
- **Small**: rounded (4px) - tags, badges
- **Large**: rounded-xl (12px) - modals
- **Circle**: rounded-full - avatars, icons

## Shadows

- **Card**: border border-gray-200 (no shadow, prefer borders)
- **Elevated**: shadow-sm (dropdowns, popovers)
- **Modal**: shadow-lg (overlays)

## Responsive Breakpoints

- **sm**: 640px (small tablets)
- **md**: 768px (tablets)
- **lg**: 1024px (sidebar toggle point)
- **xl**: 1280px (desktop)
- **2xl**: 1536px (large desktop)

## RBAC & Plan-Gating UX

### Access Control Indicators

**Hidden Items:**
- If user lacks role permission → nav item not rendered

**Plan-Locked Items:**
- Shown in nav with lock icon (🔒)
- Disabled appearance (opacity-60, cursor-not-allowed)
- Tooltip: "Feature locked - contact admin"

**Locked Pages:**
- Show within AdminShell (sidebar visible)
- Friendly message: feature locked, explain how to request access
- No sales language or pricing information
- Link to admin contact or support

**Access Denied Pages:**
- Show within AdminShell
- Clear message about permission requirements
- Display user's current role
- No harsh language, professional tone

## Guests UI Flows

### Guests List (`/guests`)

**Features:**
1. Search input with clear button
2. Table columns: Name, Email, Phone, City, Status, Bookings, Last Booking
3. Status badges: VIP (yellow), Gesperrt (red)
4. Row click → navigate to detail
5. Pagination controls
6. Empty state: "Keine Gäste gefunden"
7. Loading: spinner with "Lade Gäste..."
8. Error: retry button

**API Integration:**
- GET /api/v1/guests?limit={limit}&offset={offset}&q={searchQuery}
- Credentials: include (cookies)
- Error handling: HTTP 503 (schema drift), 401 (auth), 500 (server)

### Guest Detail (`/guests/{id}`)

**Features:**
1. Back link to list
2. Header: name + status badges (VIP, Gesperrt, Marketing OK)
3. Edit button (placeholder)
4. Tabs: Details | Buchungshistorie
5. **Details Tab:**
   - Contact info card (email, phone, city, country)
   - Booking stats card (total bookings, total spent, last booking)
   - Notes section (profile notes, blacklist reason)
6. **Timeline Tab:**
   - List of bookings with property, dates, status, price
   - Link to booking detail
   - Empty state: "Keine Buchungen"

**API Integration:**
- GET /api/v1/guests/{id}
- GET /api/v1/guests/{id}/timeline?limit=10&offset=0

### Guest Create/Edit

**Status:** Placeholder (button alerts "coming soon")

**Future Implementation:**
- Modal or drawer pattern
- Form fields: first_name, last_name, email, phone, city, etc.
- POST /api/v1/guests (create)
- PATCH /api/v1/guests/{id} (update)
- Validation: required fields, email format, phone format
- Success: toast message + redirect/refresh

## Manual Verification Checklist

### Navigation
- [ ] Sidebar visible on all admin pages
- [ ] Active route highlighted in sidebar
- [ ] Settings group expands when in settings pages
- [ ] Sidebar collapses to icons-only mode
- [ ] Collapse state persists on page refresh
- [ ] Mobile: hamburger menu opens drawer
- [ ] Mobile: backdrop closes drawer
- [ ] Logout button works from any page

### Guests CRUD
- [ ] List loads without errors
- [ ] Search filters results
- [ ] Clear button resets search
- [ ] Pagination prev/next works
- [ ] Row click navigates to detail
- [ ] Detail page shows guest info
- [ ] Timeline tab shows bookings
- [ ] Empty states display correctly
- [ ] Loading states show spinner
- [ ] Error states allow retry

### Branding
- [ ] Branding page has sidebar
- [ ] Settings group expanded on branding page
- [ ] Access denied shows within AdminShell
- [ ] Unauthorized users see friendly message

### RBAC
- [ ] Admin sees all nav items
- [ ] Non-admin nav hides restricted items
- [ ] Plan-locked items show lock icon
- [ ] Plan-locked pages show explanation

### Responsive
- [ ] Desktop: sidebar visible by default
- [ ] Mobile: drawer pattern works
- [ ] Tables scroll horizontally if needed
- [ ] Cards stack on mobile

## Future Enhancements

**Phase 1 (Current):**
- ✅ Sidebar navigation
- ✅ Guests list + detail + timeline
- ✅ Settings/Branding with sidebar
- ✅ RBAC indicators

**Phase 2 (Next):**
- [ ] Guest create/edit modals
- [ ] Dark mode support
- [ ] Branding customization (logo upload, color picker)
- [ ] Real dashboard page
- [ ] Properties/Bookings/Availability pages

**Phase 3 (Future):**
- [ ] Advanced search filters
- [ ] Bulk actions
- [ ] Export functionality
- [ ] Notification system
- [ ] User preferences panel
