# Phase 10A: UI/UX & Design System (Konzeption)

**Status:** Draft
**Version:** 1.0
**Erstellt:** 2025-12-21
**Projekt:** PMS-Webapp

---

## Executive Summary

### Ziel
**Umsetzungsreife UI/UX-Konzeption** für PMS-Webapp MVP mit vollständiger Informationsarchitektur, Wireframes und Design-System-Grundlagen.

### Scope
- ✅ Informationsarchitektur & Navigation (rollenbasiert)
- ✅ Wireframes (Low-Mid Fidelity) für alle MVP-Screens
- ✅ Design-System-Grundlagen (konzeptionell)
- ✅ UI States (Empty, Loading, Error, Success)

### Leitplanken
- ⚠️ **Kein Code:** Nur konzeptionelle Dokumentation
- ⚠️ **Kein Design:** Keine Farben, Fonts, Icons (nur Platzhalter)
- ⚠️ **Direct Booking gleichwertig:** Zu Channel Bookings
- ⚠️ **Airbnb als Referenz:** Weitere Channels als Platzhalter

---

## 1. Informationsarchitektur & Navigation

### 1.1 Sitemap (Gesamtübersicht)

```
PMS-Webapp
├── Public (nicht authentifiziert)
│   ├── Homepage
│   ├── Property Search
│   ├── Property Detail
│   └── Direct Booking Flow (5 Steps)
│       ├── Step 1: Search & Select
│       ├── Step 2: Guest Info
│       ├── Step 3: Payment
│       ├── Step 4: Confirmation
│       └── Step 5: Booking Management (optional)
│
└── App (authentifiziert, rollenbasiert)
    ├── Dashboard (Home)
    ├── Properties
    │   ├── Property List
    │   ├── Property Detail
    │   ├── Property Create/Edit
    │   └── Property Settings
    ├── Bookings
    │   ├── Booking List
    │   ├── Booking Calendar
    │   ├── Booking Detail
    │   └── Booking Create (Manual)
    ├── Channels
    │   ├── Channel Connections
    │   ├── Channel Connect (OAuth)
    │   ├── Channel Detail
    │   └── Sync Logs
    ├── Availability & Pricing
    │   ├── Calendar View
    │   ├── Pricing Rules
    │   └── Blocked Dates
    ├── Team
    │   ├── Team Members
    │   ├── Invite Member
    │   └── Role Management
    └── Settings
        ├── Account Settings
        ├── Payment Settings (Stripe)
        ├── Notification Settings
        └── Billing
```

### 1.2 Hauptnavigation (Desktop)

**Layout: Sidebar + Top Bar**

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]  PMS-Webapp        [Notifications] [User Menu]      │  ← Top Bar
├──────────┬──────────────────────────────────────────────────┤
│          │                                                   │
│ Sidebar  │          Main Content Area                       │
│          │                                                   │
│  [Icon]  │                                                   │
│ Dashboard│                                                   │
│          │                                                   │
│  [Icon]  │                                                   │
│Properties│                                                   │
│          │                                                   │
│  [Icon]  │                                                   │
│ Bookings │                                                   │
│          │                                                   │
│  [Icon]  │                                                   │
│ Channels │                                                   │
│          │                                                   │
│  [Icon]  │                                                   │
│  Team    │                                                   │
│          │                                                   │
│  [Icon]  │                                                   │
│ Settings │                                                   │
│          │                                                   │
└──────────┴──────────────────────────────────────────────────┘
```

**Navigation-Items:**

| Item | Icon | Route | Roles |
|------|------|-------|-------|
| Dashboard | 📊 | `/app/dashboard` | All |
| Properties | 🏠 | `/app/properties` | All |
| Bookings | 📅 | `/app/bookings` | All |
| Channels | 🔗 | `/app/channels` | Owner, Manager |
| Team | 👥 | `/app/team` | Owner, Manager |
| Settings | ⚙️ | `/app/settings` | All |

**User Menu (Top Bar):**
- Profile
- Switch Role (wenn mehrere Tenants)
- Help & Support
- Logout

### 1.3 Mobile Navigation

**Layout: Bottom Tab Bar**

```
┌─────────────────────────────┐
│      [Logo] [Notifications] │  ← Top Bar (collapsed)
│                             │
│                             │
│     Main Content Area       │
│                             │
│                             │
│                             │
│                             │
├─────┬──────┬──────┬──────┬──┤
│ 📊  │ 🏠   │ 📅   │ 🔗   │ ⋮ │  ← Bottom Tab Bar
│Dash │Props │Books │Chan. │More
└─────┴──────┴──────┴──────┴──┘
```

**Mobile Tab Bar:**
- Dashboard (📊)
- Properties (🏠)
- Bookings (📅)
- Channels (🔗)
- More (⋮) → Team, Settings, Profile

### 1.4 Rollenbasierte Sichtbarkeit

**Owner (Full Access):**
- ✅ Dashboard, Properties, Bookings, Channels, Team, Settings (all)
- ✅ Create, Edit, Delete (all entities)
- ✅ Connect/Disconnect Channels
- ✅ Manage Team Members
- ✅ Financial Data (revenue, reports)

**Manager (Property Management):**
- ✅ Dashboard, Properties, Bookings, Channels (view), Team (view)
- ✅ Create, Edit Properties
- ✅ Manage Bookings (create, update, cancel)
- ✅ View Channel Connections (cannot connect/disconnect)
- ❌ Cannot manage Team Members
- ❌ Cannot access Financial Settings (Payment, Billing)

**Staff (Operational):**
- ✅ Dashboard (limited), Bookings (limited)
- ✅ View Properties (read-only)
- ✅ View Upcoming Bookings (next 7 days)
- ✅ Update Booking Status (Check-in, Check-out)
- ❌ Cannot access Channels, Team, Settings
- ❌ Cannot view Financial Data

**Viewer (Read-Only):**
- ✅ Dashboard (all), Properties (all), Bookings (all)
- ✅ View-Only (no create/edit/delete)
- ❌ Cannot access Channels (sensitive OAuth data)
- ❌ Cannot access Team, Settings

### 1.5 Öffentliche Bereiche (Direct Booking)

**Public Pages (nicht authentifiziert):**

```
Public Website
├── Homepage
│   ├── Hero Section (Search Bar)
│   ├── Featured Properties
│   └── Call-to-Action (Sign Up)
│
├── Property Search
│   ├── Filters (Location, Dates, Guests, Price)
│   ├── Property Grid (Cards)
│   └── Map View (optional)
│
├── Property Detail
│   ├── Photo Gallery
│   ├── Property Info (Bedrooms, Bathrooms, Amenities)
│   ├── Reviews (optional, Post-MVP)
│   ├── Calendar (Availability)
│   ├── Pricing Calculator
│   └── "Book Now" Button
│
└── Direct Booking Flow (5 Steps)
    ├── Step 1: Confirm Dates & Guests
    ├── Step 2: Guest Information
    ├── Step 3: Payment (Stripe)
    ├── Step 4: Confirmation
    └── Step 5: Manage Booking (with link)
```

**Navigation (Public):**
- Top Bar: Logo, "Sign In", "List Your Property" (CTA)
- Footer: About, Contact, Terms, Privacy

---

## 2. Wireframes (Low-Mid Fidelity)

### 2.1 Dashboard (Home)

**Purpose:** Überblick über aktuelle Aktivitäten, wichtige Metriken, schnelle Actions

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Dashboard                      [User Menu]    │
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  Welcome back, [Owner Name]                    │
│ Dashboard  │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 🏠         │  │ Quick Stats (Cards)                     │   │
│Properties  │  │                                         │   │
│            │  │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │   │
│ 📅         │  │ │ 24   │ │ 12   │ │ 95%  │ │€4.5k │   │   │
│ Bookings   │  │ │Props │ │Active│ │Occup.│ │Rev.  │   │   │
│            │  │ └──────┘ └──────┘ └──────┘ └──────┘   │   │
│ 🔗         │  └─────────────────────────────────────────┘   │
│ Channels   │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 👥         │  │ Upcoming Check-ins (Today)              │   │
│  Team      │  │                                         │   │
│            │  │ • 10:00 - Beach Villa - John Doe        │   │
│ ⚙️         │  │ • 14:00 - Mountain Cabin - Jane Smith   │   │
│ Settings   │  │ • 16:00 - City Apartment - Mike Brown   │   │
│            │  │                                         │   │
│            │  │ [View All Bookings →]                   │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Recent Activity                         │   │
│            │  │                                         │   │
│            │  │ 🟢 New booking - Beach Villa (Airbnb)   │   │
│            │  │ 🔵 Channel synced - Mountain Cabin      │   │
│            │  │ 🟠 Booking updated - City Apartment     │   │
│            │  │                                         │   │
│            │  │ [View All Activity →]                   │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Channel Status                          │   │
│            │  │                                         │   │
│            │  │ ✅ Airbnb - Connected - Last sync: 2m   │   │
│            │  │ ⚠️  Booking.com - Not Connected         │   │
│            │  │                                         │   │
│            │  │ [Manage Channels →]                     │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Components:**

1. **Quick Stats (4 Cards):**
   - Total Properties (count)
   - Active Bookings (count, current month)
   - Occupancy Rate (percentage, current month)
   - Revenue (currency, current month)

2. **Upcoming Check-ins (List):**
   - Time, Property Name, Guest Name
   - "View All Bookings" link

3. **Recent Activity (Timeline):**
   - Event type (New Booking, Channel Sync, Booking Update)
   - Property Name, Source (Airbnb, Direct, etc.)
   - "View All Activity" link

4. **Channel Status (List):**
   - Channel Name, Status (Connected, Not Connected, Error)
   - Last Sync Time
   - "Manage Channels" link

**Rollenbasierte Anpassungen:**
- **Owner:** Alle Widgets sichtbar
- **Manager:** Channel Status: Read-Only (kann nicht verbinden/trennen)
- **Staff:** Nur "Upcoming Check-ins" Widget
- **Viewer:** Alle Widgets, aber Read-Only

---

### 2.2 Properties

#### 2.2.1 Property List

**Purpose:** Übersicht über alle Properties, Quick Actions

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Properties                     [+ New Property]│
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  [Search: "Search properties..."]              │
│ Dashboard  │  [Filter: All | Active | Inactive]             │
│            │  [Sort: Name | Created | Occupancy]            │
│ 🏠         │                                                 │
│Properties  │  ┌─────────────────────────────────────────┐   │
│            │  │ Property Card 1                         │   │
│ 📅         │  │ ┌──────┐                                │   │
│ Bookings   │  │ │Photo │ Beach Villa                    │   │
│            │  │ │      │ Berlin, Germany                │   │
│ 🔗         │  │ └──────┘                                │   │
│ Channels   │  │ 3 Beds • 2 Baths • 6 Guests             │   │
│            │  │                                         │   │
│ 👥         │  │ Status: ✅ Active                        │   │
│  Team      │  │ Occupancy: 85%                          │   │
│            │  │ Channels: Airbnb                        │   │
│ ⚙️         │  │                                         │   │
│ Settings   │  │ [View] [Edit] [•••]                     │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Property Card 2                         │   │
│            │  │ ┌──────┐                                │   │
│            │  │ │Photo │ Mountain Cabin                 │   │
│            │  │ │      │ Munich, Germany                │   │
│            │  │ └──────┘                                │   │
│            │  │ 2 Beds • 1 Bath • 4 Guests              │   │
│            │  │                                         │   │
│            │  │ Status: ✅ Active                        │   │
│            │  │ Occupancy: 92%                          │   │
│            │  │ Channels: Airbnb, Direct                │   │
│            │  │                                         │   │
│            │  │ [View] [Edit] [•••]                     │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Property Card 3                         │   │
│            │  │ ┌──────┐                                │   │
│            │  │ │Photo │ City Apartment                 │   │
│            │  │ │      │ Hamburg, Germany               │   │
│            │  │ └──────┘                                │   │
│            │  │ 1 Bed • 1 Bath • 2 Guests               │   │
│            │  │                                         │   │
│            │  │ Status: ⚠️  Inactive                     │   │
│            │  │ Occupancy: 0%                           │   │
│            │  │ Channels: None                          │   │
│            │  │                                         │   │
│            │  │ [View] [Edit] [•••]                     │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Components:**

1. **Header:**
   - Title: "Properties"
   - Action: "+ New Property" Button (Owner, Manager only)

2. **Filters & Search:**
   - Search: "Search properties..." (name, location)
   - Filter: All | Active | Inactive
   - Sort: Name | Created Date | Occupancy

3. **Property Card:**
   - Photo (thumbnail)
   - Property Name
   - Location (City, Country)
   - Details: Bedrooms, Bathrooms, Max Guests
   - Status: Active (✅), Inactive (⚠️)
   - Occupancy Rate (percentage, current month)
   - Channels: List of connected channels (Airbnb, Direct, etc.)
   - Actions: [View] [Edit] [•••] (More: Delete, Duplicate)

**Empty State:**
```
┌─────────────────────────────────────────┐
│                                         │
│         [Icon: Empty Folder]            │
│                                         │
│      No properties yet                  │
│                                         │
│  Get started by adding your first       │
│  property to start managing bookings.   │
│                                         │
│         [+ Add Property]                │
│                                         │
└─────────────────────────────────────────┘
```

---

#### 2.2.2 Property Detail

**Purpose:** Detailansicht einer Property, Edit-Mode, Quick Stats

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Properties > Beach Villa       [Edit Property]│
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  ┌─────────────────────────────────────────┐   │
│ Dashboard  │  │ Photo Gallery (Primary + 5 more)        │   │
│            │  │ ┌──────────────────────────────────────┐│   │
│ 🏠         │  │ │                                      ││   │
│Properties  │  │ │       Main Photo (Large)             ││   │
│            │  │ │                                      ││   │
│ 📅         │  │ └──────────────────────────────────────┘│   │
│ Bookings   │  │ [Photo2] [Photo3] [Photo4] [Photo5] [+] │   │
│            │  └─────────────────────────────────────────┘   │
│ 🔗         │                                                 │
│ Channels   │  Beach Villa                                    │
│            │  ⭐ 4.8 (24 reviews) • Berlin, Germany          │
│ 👥         │                                                 │
│  Team      │  ┌─────────────────────────────────────────┐   │
│            │  │ Quick Stats                             │   │
│ ⚙️         │  │                                         │   │
│ Settings   │  │ Status: ✅ Active                        │   │
│            │  │ Occupancy: 85% (this month)             │   │
│            │  │ Revenue: €4,200 (this month)            │   │
│            │  │ Channels: Airbnb, Direct                │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Property Details                        │   │
│            │  │                                         │   │
│            │  │ Type: Villa                             │   │
│            │  │ Bedrooms: 3                             │   │
│            │  │ Bathrooms: 2                            │   │
│            │  │ Max Guests: 6                           │   │
│            │  │ Size: 120 sqm                           │   │
│            │  │                                         │   │
│            │  │ Address:                                │   │
│            │  │ Strandstraße 123, 10115 Berlin, Germany │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Amenities                               │   │
│            │  │                                         │   │
│            │  │ ✅ WiFi      ✅ Kitchen   ✅ Parking     │   │
│            │  │ ✅ Pool      ✅ AC        ✅ Washer      │   │
│            │  │ ✅ TV        ✅ Heating   ❌ Gym         │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Description                             │   │
│            │  │                                         │   │
│            │  │ Beautiful beachfront villa with...      │   │
│            │  │ [Read More]                             │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Tabs: [Bookings] [Calendar] [Channels]  │   │
│            │  │                                         │   │
│            │  │ Upcoming Bookings (5)                   │   │
│            │  │ • Jul 1-5: John Doe (Airbnb)            │   │
│            │  │ • Jul 10-15: Jane Smith (Direct)        │   │
│            │  │ • Jul 20-25: Mike Brown (Airbnb)        │   │
│            │  │                                         │   │
│            │  │ [View All Bookings →]                   │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Components:**

1. **Photo Gallery:**
   - Primary Photo (large, hero)
   - Thumbnails (5 more photos)
   - "+ Add Photos" Button

2. **Header:**
   - Property Name
   - Rating + Reviews (optional, Post-MVP)
   - Location (City, Country)
   - "Edit Property" Button (Owner, Manager only)

3. **Quick Stats:**
   - Status (Active, Inactive)
   - Occupancy Rate (percentage, current month)
   - Revenue (currency, current month)
   - Connected Channels (list)

4. **Property Details:**
   - Type, Bedrooms, Bathrooms, Max Guests, Size
   - Address (full)

5. **Amenities:**
   - Checkboxes (WiFi, Kitchen, Parking, Pool, etc.)

6. **Description:**
   - Full text (collapsible)

7. **Tabs:**
   - **Bookings Tab:** Upcoming Bookings (list)
   - **Calendar Tab:** Availability Calendar (inline)
   - **Channels Tab:** Connected Channels + Sync Status

---

#### 2.2.3 Property Create/Edit

**Purpose:** Formular zum Anlegen/Bearbeiten einer Property

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  New Property                   [Save] [Cancel]│
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  ┌─────────────────────────────────────────┐   │
│ Dashboard  │  │ Basic Information                       │   │
│            │  │                                         │   │
│ 🏠         │  │ Property Name *                         │   │
│Properties  │  │ [Beach Villa                        ]   │   │
│            │  │                                         │   │
│ 📅         │  │ Property Type *                         │   │
│ Bookings   │  │ [Dropdown: Villa ▼]                     │   │
│            │  │                                         │   │
│ 🔗         │  │ Address *                               │   │
│ Channels   │  │ Street: [Strandstraße 123           ]   │   │
│            │  │ City:   [Berlin                     ]   │   │
│ 👥         │  │ ZIP:    [10115                      ]   │   │
│  Team      │  │ Country:[Germany                    ]   │   │
│            │  └─────────────────────────────────────────┘   │
│ ⚙️         │                                                 │
│ Settings   │  ┌─────────────────────────────────────────┐   │
│            │  │ Property Details                        │   │
│            │  │                                         │   │
│            │  │ Bedrooms *   [3   ]                     │   │
│            │  │ Bathrooms *  [2   ]                     │   │
│            │  │ Max Guests * [6   ]                     │   │
│            │  │ Size (sqm)   [120 ]                     │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Amenities                               │   │
│            │  │                                         │   │
│            │  │ ☑ WiFi        ☑ Kitchen    ☑ Parking    │   │
│            │  │ ☑ Pool        ☑ AC         ☑ Washer     │   │
│            │  │ ☑ TV          ☑ Heating    ☐ Gym        │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Photos                                  │   │
│            │  │                                         │   │
│            │  │ [Upload Area - Drag & Drop]             │   │
│            │  │ or [Choose Files]                       │   │
│            │  │                                         │   │
│            │  │ Uploaded (2):                           │   │
│            │  │ [Photo1 Thumbnail] [×]                  │   │
│            │  │ [Photo2 Thumbnail] [×]                  │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Description                             │   │
│            │  │                                         │   │
│            │  │ [Textarea: Beautiful beachfront villa...│   │
│            │  │                                      ]  │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Pricing                                 │   │
│            │  │                                         │   │
│            │  │ Base Price (per night) * [150 €]       │   │
│            │  │ Currency                 [EUR ▼]       │   │
│            │  │                                         │   │
│            │  │ ℹ️  Advanced pricing rules can be set   │   │
│            │  │    after creating the property.         │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │                        [Save Property] [Cancel]│
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Form Sections:**

1. **Basic Information:**
   - Property Name (required)
   - Property Type (dropdown: Villa, Apartment, House, Cabin, etc.)
   - Address (Street, City, ZIP, Country)

2. **Property Details:**
   - Bedrooms (number)
   - Bathrooms (number)
   - Max Guests (number)
   - Size (sqm, optional)

3. **Amenities:**
   - Checkboxes (multi-select)
   - WiFi, Kitchen, Parking, Pool, AC, Washer, TV, Heating, Gym, etc.

4. **Photos:**
   - Upload Area (Drag & Drop)
   - "Choose Files" Button
   - Uploaded Photos (thumbnails with delete button)

5. **Description:**
   - Textarea (rich text, optional)

6. **Pricing:**
   - Base Price (per night, required)
   - Currency (dropdown: EUR, USD, GBP, etc.)
   - Info: "Advanced pricing rules can be set after creating the property."

**Validation:**
- Required fields: Property Name, Type, Address, Bedrooms, Bathrooms, Max Guests, Base Price
- Form cannot be submitted if required fields are empty
- Inline validation errors (red border + error message below field)

---

### 2.3 Bookings

#### 2.3.1 Booking List

**Purpose:** Übersicht über alle Bookings, Filter, Quick Actions

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Bookings                       [+ New Booking]│
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  [Search: "Search bookings..."]                │
│ Dashboard  │  [Filter: All | Upcoming | Past | Cancelled]   │
│            │  [Source: All | Direct | Airbnb | Booking.com] │
│ 🏠         │  [Sort: Check-in | Created | Guest]            │
│Properties  │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 📅         │  │ Booking Row 1                           │   │
│ Bookings   │  │                                         │   │
│            │  │ BK-12345 • Beach Villa                  │   │
│ 🔗         │  │ John Doe • john@example.com             │   │
│ Channels   │  │ Jul 1-5, 2025 (4 nights) • 4 Guests     │   │
│            │  │                                         │   │
│ 👥         │  │ Status: ✅ Confirmed                     │   │
│  Team      │  │ Source: 🔗 Airbnb                        │   │
│            │  │ Total: €600                             │   │
│ ⚙️         │  │                                         │   │
│ Settings   │  │ [View] [Check-in] [Cancel] [•••]       │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Booking Row 2                           │   │
│            │  │                                         │   │
│            │  │ BK-12346 • Mountain Cabin               │   │
│            │  │ Jane Smith • jane@example.com           │   │
│            │  │ Jul 10-15, 2025 (5 nights) • 2 Guests   │   │
│            │  │                                         │   │
│            │  │ Status: 🔵 Reserved (Payment Pending)    │   │
│            │  │ Source: 🌐 Direct                        │   │
│            │  │ Total: €750                             │   │
│            │  │                                         │   │
│            │  │ [View] [Remind Payment] [Cancel] [•••]  │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Booking Row 3                           │   │
│            │  │                                         │   │
│            │  │ BK-12347 • City Apartment               │   │
│            │  │ Mike Brown • mike@example.com           │   │
│            │  │ Jul 20-25, 2025 (5 nights) • 2 Guests   │   │
│            │  │                                         │   │
│            │  │ Status: 🟢 Checked-in                    │   │
│            │  │ Source: 🌐 Direct                        │   │
│            │  │ Total: €500                             │   │
│            │  │                                         │   │
│            │  │ [View] [Check-out] [•••]                │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  [Pagination: 1 2 3 ... 10]                    │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Components:**

1. **Header:**
   - Title: "Bookings"
   - Action: "+ New Booking" Button (Owner, Manager only)

2. **Filters & Search:**
   - Search: "Search bookings..." (booking ID, guest name, property)
   - Filter: All | Upcoming | Past | Cancelled
   - Source Filter: All | Direct | Airbnb | Booking.com | etc.
   - Sort: Check-in Date | Created Date | Guest Name

3. **Booking Row:**
   - Booking ID + Property Name
   - Guest Name + Email
   - Check-in - Check-out (nights) + Guests
   - Status (badge):
     - 🔵 Reserved (Payment Pending)
     - ✅ Confirmed
     - 🟢 Checked-in
     - 🟠 Checked-out
     - ❌ Cancelled
   - Source (icon + name): Direct, Airbnb, Booking.com, etc.
   - Total Price (currency)
   - Actions:
     - [View] (all roles)
     - [Check-in] [Check-out] (Owner, Manager, Staff)
     - [Remind Payment] (if status = Reserved)
     - [Cancel] (Owner, Manager)
     - [•••] More: Edit, Refund, Send Email

**Empty State:**
```
┌─────────────────────────────────────────┐
│                                         │
│         [Icon: Empty Calendar]          │
│                                         │
│      No bookings yet                    │
│                                         │
│  Start by creating a booking or wait    │
│  for guests to book through channels.   │
│                                         │
│         [+ Create Booking]              │
│                                         │
└─────────────────────────────────────────┘
```

---

#### 2.3.2 Booking Calendar

**Purpose:** Kalenderansicht aller Bookings, Drag & Drop (Post-MVP)

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Booking Calendar         [Month ▼] [Property ▼]│
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  ← June 2025 →                                  │
│ Dashboard  │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 🏠         │  │ Sun Mon Tue Wed Thu Fri Sat             │   │
│Properties  │  │                                         │   │
│            │  │  1   2   3   4   5   6   7              │   │
│ 📅         │  │ ┌──────────────┐                        │   │
│ Bookings   │  │ │ BK-12345     │  9  10  11  12  13  14 │   │
│            │  │ │ Beach Villa  │ ┌──────────────────┐  │   │
│ 🔗         │  │ │ John Doe     │ │ BK-12346         │  │   │
│ Channels   │  │ └──────────────┘ │ Mountain Cabin   │  │   │
│            │  │ 15  16  17  18  │ Jane Smith       │  │   │
│ 👥         │  │                 └──────────────────┘  │   │
│  Team      │  │                  19 ┌───────────────┐ │   │
│            │  │ 22  23  24  25  │   │ BK-12347      │ │   │
│ ⚙️         │  │                 │   │ City Apt      │ │   │
│ Settings   │  │ 29  30          │   │ Mike Brown    │ │   │
│            │  │                 └───────────────────┘ │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Legend                                  │   │
│            │  │                                         │   │
│            │  │ 🔵 Reserved  ✅ Confirmed  🟢 Checked-in │   │
│            │  │ ❌ Cancelled  ⚫ Blocked                 │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Click on a booking to view details      │   │
│            │  │ (Drag & Drop: Post-MVP)                 │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Components:**

1. **Header:**
   - Title: "Booking Calendar"
   - Filters:
     - Month Selector (dropdown or arrows)
     - Property Filter (dropdown: All Properties, Beach Villa, etc.)

2. **Calendar Grid:**
   - Days of week (Sun-Sat)
   - Dates (1-30/31)
   - Bookings (colored blocks):
     - Each booking spans multiple dates (check-in to check-out)
     - Color-coded by status (Reserved, Confirmed, Checked-in, Cancelled)
     - Shows: Booking ID, Property Name, Guest Name (truncated)

3. **Legend:**
   - Status colors (Reserved, Confirmed, Checked-in, Cancelled, Blocked)

4. **Interactions:**
   - Click on booking → Open Booking Detail modal/page
   - Drag & Drop (Post-MVP) → Change dates

---

#### 2.3.3 Booking Detail

**Purpose:** Detailansicht einer Booking, Actions, History

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Bookings > BK-12345            [Edit] [Cancel]│
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  Booking BK-12345                               │
│ Dashboard  │  Status: ✅ Confirmed                            │
│            │  Source: 🔗 Airbnb                               │
│ 🏠         │                                                 │
│Properties  │  ┌─────────────────────────────────────────┐   │
│            │  │ Property                                │   │
│ 📅         │  │                                         │   │
│ Bookings   │  │ Beach Villa                             │   │
│            │  │ Strandstraße 123, Berlin, Germany       │   │
│ 🔗         │  │ 3 Beds • 2 Baths • 6 Guests             │   │
│ Channels   │  │                                         │   │
│            │  │ [View Property →]                       │   │
│ 👥         │  └─────────────────────────────────────────┘   │
│  Team      │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ ⚙️         │  │ Guest                                   │   │
│ Settings   │  │                                         │   │
│            │  │ John Doe                                │   │
│            │  │ john@example.com                        │   │
│            │  │ +49 123 456789                          │   │
│            │  │                                         │   │
│            │  │ [View Guest Profile →]                  │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Booking Details                         │   │
│            │  │                                         │   │
│            │  │ Check-in:  Jul 1, 2025 (14:00)          │   │
│            │  │ Check-out: Jul 5, 2025 (11:00)          │   │
│            │  │ Nights: 4                               │   │
│            │  │ Guests: 4 Adults, 0 Children            │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Pricing                                 │   │
│            │  │                                         │   │
│            │  │ Base Price:     €150 × 4 nights = €600  │   │
│            │  │ Cleaning Fee:                     €50   │   │
│            │  │ Service Fee:                      €30   │   │
│            │  │ ───────────────────────────────────     │   │
│            │  │ Total:                           €680   │   │
│            │  │                                         │   │
│            │  │ Payment Status: ✅ Paid                  │   │
│            │  │ Payment Method: Stripe (via Airbnb)     │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Actions                                 │   │
│            │  │                                         │   │
│            │  │ [Check-in Guest]                        │   │
│            │  │ [Send Message]                          │   │
│            │  │ [Download Invoice]                      │   │
│            │  │ [Cancel Booking]                        │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ History                                 │   │
│            │  │                                         │   │
│            │  │ • Jun 15, 2025 - Booking created        │   │
│            │  │ • Jun 15, 2025 - Payment confirmed      │   │
│            │  │ • Jun 20, 2025 - Synced to Airbnb       │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Components:**

1. **Header:**
   - Booking ID (e.g., BK-12345)
   - Status (badge: Reserved, Confirmed, Checked-in, Checked-out, Cancelled)
   - Source (icon + name: Direct, Airbnb, etc.)
   - Actions: [Edit] [Cancel]

2. **Property Section:**
   - Property Name
   - Address
   - Details (Bedrooms, Bathrooms, Max Guests)
   - "View Property" link

3. **Guest Section:**
   - Guest Name
   - Email
   - Phone
   - "View Guest Profile" link

4. **Booking Details:**
   - Check-in Date & Time
   - Check-out Date & Time
   - Number of Nights
   - Number of Guests (Adults, Children)

5. **Pricing:**
   - Base Price (per night × nights)
   - Cleaning Fee
   - Service Fee
   - **Total**
   - Payment Status (Paid, Pending, Refunded)
   - Payment Method (Stripe, Airbnb, etc.)

6. **Actions:**
   - [Check-in Guest] (Owner, Manager, Staff)
   - [Send Message] (Owner, Manager)
   - [Download Invoice] (all roles)
   - [Cancel Booking] (Owner, Manager)

7. **History:**
   - Timeline of events (Booking created, Payment confirmed, Synced to channel, etc.)

---

### 2.4 Direct Booking Flow (Public)

**Purpose:** 5-Step Buchungsflow für Gäste (nicht authentifiziert)

#### 2.4.1 Step 1: Search & Select

**Layout: Homepage with Search**

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo] PMS-Webapp              [Sign In] [List Your Property]│
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                    Find Your Perfect Stay                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Search Bar                                           │   │
│  │                                                      │   │
│  │ Location: [Berlin, Germany            ]             │   │
│  │ Check-in: [Jul 1, 2025 ▼]                           │   │
│  │ Check-out:[Jul 5, 2025 ▼]                           │   │
│  │ Guests:   [2 Adults ▼]                              │   │
│  │                                                      │   │
│  │                     [Search Properties]              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  Featured Properties                                         │
│                                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                        │
│  │ Photo   │ │ Photo   │ │ Photo   │                        │
│  │         │ │         │ │         │                        │
│  │ Beach   │ │Mountain │ │ City    │                        │
│  │ Villa   │ │ Cabin   │ │ Apt     │                        │
│  │ €150/nt │ │ €120/nt │ │ €80/nt  │                        │
│  └─────────┘ └─────────┘ └─────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Layout: Search Results**

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]              [Location] [Dates] [Guests] [Search]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [Filters: Price | Bedrooms | Amenities]                    │
│  [Sort: Recommended | Price | Rating]                       │
│                                                              │
│  12 properties found                                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Property Card 1                                      │   │
│  │ ┌──────┐                                             │   │
│  │ │Photo │ Beach Villa                                 │   │
│  │ │      │ Berlin, Germany                             │   │
│  │ └──────┘                                             │   │
│  │ ⭐ 4.8 (24 reviews)                                   │   │
│  │ 3 Beds • 2 Baths • 6 Guests                          │   │
│  │ WiFi • Kitchen • Parking • Pool                      │   │
│  │                                                      │   │
│  │ €150/night • €600 total (4 nights)                   │   │
│  │                                    [View Property]   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Property Card 2                                      │   │
│  │ ┌──────┐                                             │   │
│  │ │Photo │ Mountain Cabin                              │   │
│  │ │      │ Munich, Germany                             │   │
│  │ └──────┘                                             │   │
│  │ ⭐ 4.9 (18 reviews)                                   │   │
│  │ 2 Beds • 1 Bath • 4 Guests                           │   │
│  │ WiFi • Kitchen • Fireplace                           │   │
│  │                                                      │   │
│  │ €120/night • €480 total (4 nights)                   │   │
│  │                                    [View Property]   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [Pagination: 1 2 3 ... 5]                                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

#### 2.4.2 Step 2: Property Detail & Book Now

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]              [Dates] [Guests]           [Sign In]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Photo Gallery (Large)                                │   │
│  │ ┌────────────────────────────────────────────────┐   │   │
│  │ │                                                │   │   │
│  │ │             Main Photo                         │   │   │
│  │ │                                                │   │   │
│  │ └────────────────────────────────────────────────┘   │   │
│  │ [Photo2] [Photo3] [Photo4] [Photo5]              │   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────┐ ┌───────────────────────┐│
│  │ Beach Villa                  │ │ Booking Widget        ││
│  │ ⭐ 4.8 (24 reviews)           │ │                       ││
│  │ Berlin, Germany              │ │ €150 / night          ││
│  │                              │ │                       ││
│  │ Hosted by John Owner         │ │ Check-in:             ││
│  │                              │ │ [Jul 1, 2025 ▼]       ││
│  │ 3 Beds • 2 Baths • 6 Guests  │ │ Check-out:            ││
│  │                              │ │ [Jul 5, 2025 ▼]       ││
│  │ ────────────────────────     │ │ Guests:               ││
│  │                              │ │ [2 Adults ▼]          ││
│  │ Description:                 │ │                       ││
│  │ Beautiful beachfront villa...│ │ €150 × 4 nights = €600││
│  │ [Read More]                  │ │ Cleaning Fee:     €50 ││
│  │                              │ │ Service Fee:      €30 ││
│  │ ────────────────────────     │ │ ───────────────────── ││
│  │                              │ │ Total:           €680 ││
│  │ Amenities:                   │ │                       ││
│  │ ✅ WiFi      ✅ Kitchen       │ │ [Book Now]            ││
│  │ ✅ Parking   ✅ Pool          │ │                       ││
│  │ ✅ AC        ✅ Washer        │ │ ℹ️ Free cancellation  ││
│  │                              │ │   before Jul 1        ││
│  │ ────────────────────────     │ └───────────────────────┘│
│  │                              │                          │
│  │ Location:                    │                          │
│  │ [Map with pin]               │                          │
│  │                              │                          │
│  │ ────────────────────────     │                          │
│  │                              │                          │
│  │ Reviews (24):                │                          │
│  │ ⭐ John Doe: "Great stay!"   │                          │
│  │ ⭐ Jane Smith: "Amazing!"    │                          │
│  │ [View All Reviews]           │                          │
│  └──────────────────────────────┘                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Booking Widget (Sticky on scroll):**
- Price (per night)
- Check-in / Check-out (editable)
- Guests (editable)
- Price Breakdown (Base + Cleaning + Service = Total)
- **[Book Now]** Button
- Info: "Free cancellation before [date]"

---

#### 2.4.3 Step 3: Guest Information

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]              Booking Checkout                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Progress: [●──────○──────○] Step 1 of 3: Guest Info        │
│                                                              │
│  ┌──────────────────────────────┐ ┌───────────────────────┐│
│  │ Guest Information            │ │ Booking Summary       ││
│  │                              │ │                       ││
│  │ First Name *                 │ │ Beach Villa           ││
│  │ [John                    ]   │ │ Berlin, Germany       ││
│  │                              │ │                       ││
│  │ Last Name *                  │ │ Check-in: Jul 1, 2025 ││
│  │ [Doe                     ]   │ │ Check-out: Jul 5, 2025││
│  │                              │ │ Guests: 2 Adults      ││
│  │ Email *                      │ │                       ││
│  │ [john@example.com        ]   │ │ ───────────────────── ││
│  │                              │ │                       ││
│  │ Phone *                      │ │ €150 × 4 nights = €600││
│  │ [+49 123 456789          ]   │ │ Cleaning Fee:     €50 ││
│  │                              │ │ Service Fee:      €30 ││
│  │ ────────────────────────     │ │ ───────────────────── ││
│  │                              │ │ Total:           €680 ││
│  │ Special Requests (optional)  │ │                       ││
│  │ [Late check-in...        ]   │ │                       ││
│  │                              │ └───────────────────────┘│
│  │ ────────────────────────     │                          │
│  │                              │                          │
│  │ ☐ Create an account          │                          │
│  │   (optional, save bookings)  │                          │
│  │                              │                          │
│  │ ☑ I accept Terms & Conditions│                          │
│  │                              │                          │
│  │           [← Back]            │                          │
│  │           [Continue to Payment →]                       │
│  └──────────────────────────────┘                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Form Fields:**
- First Name (required)
- Last Name (required)
- Email (required)
- Phone (required)
- Special Requests (optional, textarea)
- "Create an account" (checkbox, optional)
- "I accept Terms & Conditions" (checkbox, required)

**Validation:**
- Real-time validation (email format, phone format)
- Cannot proceed if required fields empty or invalid

---

#### 2.4.4 Step 4: Payment (Stripe)

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]              Booking Checkout                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Progress: [●──────●──────○] Step 2 of 3: Payment           │
│                                                              │
│  ┌──────────────────────────────┐ ┌───────────────────────┐│
│  │ Payment Information          │ │ Booking Summary       ││
│  │                              │ │                       ││
│  │ [Stripe Payment Element]     │ │ Beach Villa           ││
│  │                              │ │ Berlin, Germany       ││
│  │ Card Number                  │ │                       ││
│  │ [4242 4242 4242 4242     ]   │ │ Jul 1-5, 2025         ││
│  │                              │ │ 2 Adults, 4 nights    ││
│  │ Expiry          CVC          │ │                       ││
│  │ [12/25]         [123]        │ │ Guest: John Doe       ││
│  │                              │ │ john@example.com      ││
│  │ Name on Card *               │ │                       ││
│  │ [John Doe                ]   │ │ ───────────────────── ││
│  │                              │ │                       ││
│  │ ────────────────────────     │ │ €150 × 4 nights = €600││
│  │                              │ │ Cleaning Fee:     €50 ││
│  │ ℹ️ Secure payment via Stripe │ │ Service Fee:      €30 ││
│  │   Your data is encrypted.    │ │ ───────────────────── ││
│  │                              │ │ Total:           €680 ││
│  │ ℹ️ Booking expires in 29:45  │ │                       ││
│  │   (30 min timer)             │ │ 🔒 Secure Payment     ││
│  │                              │ │                       ││
│  │           [← Back]            │                          │
│  │           [Pay €680 →]        │                          │
│  └──────────────────────────────┘                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Stripe Payment Element:**
   - Card Number (Stripe iframe)
   - Expiry Date (MM/YY)
   - CVC (3-4 digits)
   - Name on Card

2. **Info Messages:**
   - "Secure payment via Stripe. Your data is encrypted."
   - "Booking expires in 29:45" (countdown timer)

3. **Booking Summary (sticky):**
   - Property Name, Location
   - Dates, Guests
   - Guest Info (Name, Email)
   - Price Breakdown
   - Total
   - "🔒 Secure Payment" badge

4. **Actions:**
   - [← Back] (return to guest info)
   - [Pay €680 →] (submit payment)

**Payment States:**
- **Processing:** Loading spinner + "Processing payment..."
- **3DS Challenge:** Redirect to bank (3D Secure)
- **Success:** Redirect to Confirmation page
- **Failure:** Error message + "Please try again or use a different card"

---

#### 2.4.5 Step 5: Confirmation

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]              Booking Confirmed                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Progress: [●──────●──────●] Step 3 of 3: Confirmed         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                                                      │   │
│  │             ✅ Booking Confirmed!                     │   │
│  │                                                      │   │
│  │     Your booking has been successfully confirmed.    │   │
│  │     A confirmation email has been sent to:           │   │
│  │     john@example.com                                 │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Booking Details                                      │   │
│  │                                                      │   │
│  │ Booking ID: BK-12345                                 │   │
│  │                                                      │   │
│  │ Property: Beach Villa                                │   │
│  │ Location: Berlin, Germany                            │   │
│  │                                                      │   │
│  │ Check-in:  Jul 1, 2025 (14:00)                       │   │
│  │ Check-out: Jul 5, 2025 (11:00)                       │   │
│  │ Nights: 4                                            │   │
│  │ Guests: 2 Adults                                     │   │
│  │                                                      │   │
│  │ Guest: John Doe                                      │   │
│  │ Email: john@example.com                              │   │
│  │ Phone: +49 123 456789                                │   │
│  │                                                      │   │
│  │ ───────────────────────────────────────────────      │   │
│  │                                                      │   │
│  │ Total Paid: €680                                     │   │
│  │ Payment Method: Visa ****4242                        │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ What's Next?                                         │   │
│  │                                                      │   │
│  │ • Check your email for confirmation & details        │   │
│  │ • We'll send you check-in instructions 24h before    │   │
│  │ • Manage your booking: [View Booking →]              │   │
│  │ • Need help? [Contact Support]                       │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [Download Invoice (PDF)] [View Booking] [Back to Homepage] │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Components:**

1. **Success Message:**
   - ✅ Icon
   - "Booking Confirmed!" headline
   - "A confirmation email has been sent to: [email]"

2. **Booking Details:**
   - Booking ID
   - Property (Name, Location)
   - Dates (Check-in, Check-out)
   - Nights, Guests
   - Guest Info (Name, Email, Phone)
   - Total Paid
   - Payment Method (masked card)

3. **What's Next:**
   - Bullet list with next steps
   - Links: "View Booking", "Contact Support"

4. **Actions:**
   - [Download Invoice (PDF)]
   - [View Booking] (manage booking link)
   - [Back to Homepage]

---

### 2.5 Channels

#### 2.5.1 Channel Connections

**Purpose:** Übersicht über alle Channel Connections, Connect/Disconnect

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Channels                      [+ Connect Channel]│
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  Connected Channels (1)                         │
│ Dashboard  │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 🏠         │  │ Airbnb Channel Card                     │   │
│Properties  │  │ ┌──────┐                                │   │
│            │  │ │ Logo │ Airbnb                         │   │
│ 📅         │  │ │      │ Connected                      │   │
│ Bookings   │  │ └──────┘                                │   │
│            │  │                                         │   │
│ 🔗         │  │ Status: ✅ Active                        │   │
│ Channels   │  │ Last Sync: 2 minutes ago                │   │
│            │  │ Synced Properties: 12                   │   │
│ 👥         │  │ Synced Bookings: 24                     │   │
│  Team      │  │                                         │   │
│            │  │ [View Details] [Sync Now] [Disconnect]  │   │
│ ⚙️         │  └─────────────────────────────────────────┘   │
│ Settings   │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Sync Logs (Recent)                      │   │
│            │  │                                         │   │
│            │  │ • 2 min ago - Availability synced       │   │
│            │  │ • 5 min ago - Booking imported          │   │
│            │  │ • 10 min ago - Pricing synced           │   │
│            │  │                                         │   │
│            │  │ [View All Logs →]                       │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ────────────────────────────────────────────   │
│            │                                                 │
│            │  Available Channels                             │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Booking.com Channel Card                │   │
│            │  │ ┌──────┐                                │   │
│            │  │ │ Logo │ Booking.com                    │   │
│            │  │ │      │ Not Connected                  │   │
│            │  │ └──────┘                                │   │
│            │  │                                         │   │
│            │  │ Reach millions of travelers worldwide.  │   │
│            │  │                                         │   │
│            │  │ [Connect Booking.com]                   │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Expedia Channel Card                    │   │
│            │  │ ┌──────┐                                │   │
│            │  │ │ Logo │ Expedia                        │   │
│            │  │ │      │ Not Connected                  │   │
│            │  │ └──────┘                                │   │
│            │  │                                         │   │
│            │  │ Connect to Expedia, Hotels.com & more.  │   │
│            │  │                                         │   │
│            │  │ [Connect Expedia]                       │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Components:**

1. **Header:**
   - Title: "Channels"
   - Action: "+ Connect Channel" Button (Owner only)

2. **Connected Channels Section:**
   - **Channel Card (Connected):**
     - Channel Logo + Name
     - Status: ✅ Active, ⚠️ Warning, ❌ Error
     - Last Sync Time (relative, e.g., "2 minutes ago")
     - Synced Properties (count)
     - Synced Bookings (count)
     - Actions:
       - [View Details] (see channel detail page)
       - [Sync Now] (manual sync trigger)
       - [Disconnect] (Owner only)

3. **Sync Logs (Recent):**
   - Timeline of recent sync events
   - "View All Logs" link

4. **Available Channels Section:**
   - **Channel Card (Not Connected):**
     - Channel Logo + Name
     - Status: "Not Connected"
     - Short Description (benefits)
     - Action: [Connect {Channel}] Button (Owner only)

**Empty State (No Channels Connected):**
```
┌─────────────────────────────────────────┐
│                                         │
│         [Icon: Link/Chain]              │
│                                         │
│      No channels connected              │
│                                         │
│  Connect to Airbnb, Booking.com and     │
│  more to sync your properties and       │
│  prevent double-bookings.               │
│                                         │
│         [+ Connect Channel]             │
│                                         │
└─────────────────────────────────────────┘
```

---

#### 2.5.2 Channel Connect (OAuth Flow)

**Purpose:** OAuth-Flow zum Verbinden eines Channels

**Layout: Step 1 - Select Channel**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Connect Channel                     [× Close]  │
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  Select a channel to connect:                   │
│ Dashboard  │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 🏠         │  │ [○] Airbnb                              │   │
│Properties  │  │     Connect to Airbnb to sync bookings  │   │
│            │  └─────────────────────────────────────────┘   │
│ 📅         │                                                 │
│ Bookings   │  ┌─────────────────────────────────────────┐   │
│            │  │ [○] Booking.com                         │   │
│ 🔗         │  │     Connect to Booking.com              │   │
│ Channels   │  └─────────────────────────────────────────┘   │
│            │                                                 │
│ 👥         │  ┌─────────────────────────────────────────┐   │
│  Team      │  │ [○] Expedia                             │   │
│            │  │     Connect to Expedia, Hotels.com      │   │
│ ⚙️         │  └─────────────────────────────────────────┘   │
│ Settings   │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ [○] FeWo-direkt                         │   │
│            │  │     Connect to FeWo-direkt              │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ [○] Google Vacation Rentals             │   │
│            │  │     Connect to Google                   │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │                    [Cancel] [Continue →]       │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Layout: Step 2 - OAuth Redirect (Airbnb Example)**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Connect to Airbnb                   [× Close]  │
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  ┌─────────────────────────────────────────┐   │
│ Dashboard  │  │ Connect your Airbnb account             │   │
│            │  │                                         │   │
│ 🏠         │  │ You will be redirected to Airbnb to     │   │
│Properties  │  │ authorize access to your account.       │   │
│            │  │                                         │   │
│ 📅         │  │ We will sync:                           │   │
│ Bookings   │  │ • Your properties                       │   │
│            │  │ • Bookings                              │   │
│ 🔗         │  │ • Availability & Pricing                │   │
│ Channels   │  │                                         │   │
│            │  │ ℹ️ Your Airbnb credentials are securely  │   │
│ 👥         │  │   stored and encrypted.                 │   │
│  Team      │  │                                         │   │
│            │  │          [Authorize with Airbnb]        │   │
│ ⚙️         │  └─────────────────────────────────────────┘   │
│ Settings   │                                                 │
│            │                    [Cancel]                     │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**OAuth Flow:**
1. User clicks [Authorize with Airbnb]
2. Redirect to Airbnb OAuth page (external)
3. User logs in to Airbnb and authorizes
4. Redirect back to PMS-Webapp (callback URL)
5. Display success message + sync status

**Layout: Step 3 - Success**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Airbnb Connected                    [× Close]  │
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  ┌─────────────────────────────────────────┐   │
│ Dashboard  │  │                                         │   │
│            │  │          ✅ Successfully Connected!       │   │
│ 🏠         │  │                                         │   │
│Properties  │  │ Your Airbnb account has been connected. │   │
│            │  │                                         │   │
│ 📅         │  │ Sync Status:                            │   │
│ Bookings   │  │ • Properties: 12 synced                 │   │
│            │  │ • Bookings: 24 synced                   │   │
│ 🔗         │  │ • Availability: Synced                  │   │
│ Channels   │  │ • Pricing: Synced                       │   │
│            │  │                                         │   │
│ 👥         │  │          [View Channel Details]         │   │
│  Team      │  └─────────────────────────────────────────┘   │
│            │                                                 │
│ ⚙️         │                    [Done]                       │
│ Settings   │                                                 │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

---

#### 2.5.3 Channel Detail

**Purpose:** Detailansicht eines verbundenen Channels, Sync-Status, Logs

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Channels > Airbnb            [Sync Now] [Disconnect]│
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  Airbnb Channel                                 │
│ Dashboard  │  Status: ✅ Active                               │
│            │  Last Sync: 2 minutes ago                       │
│ 🏠         │                                                 │
│Properties  │  ┌─────────────────────────────────────────┐   │
│            │  │ Sync Statistics                         │   │
│ 📅         │  │                                         │   │
│ Bookings   │  │ Synced Properties: 12                   │   │
│            │  │ Synced Bookings: 24                     │   │
│ 🔗         │  │ Last Availability Sync: 2 min ago       │   │
│ Channels   │  │ Last Pricing Sync: 5 min ago            │   │
│            │  │                                         │   │
│ 👥         │  │ Success Rate: 99.2%                     │   │
│  Team      │  └─────────────────────────────────────────┘   │
│            │                                                 │
│ ⚙️         │  ┌─────────────────────────────────────────┐   │
│ Settings   │  │ Sync Logs (Last 24h)                    │   │
│            │  │                                         │   │
│            │  │ [Filter: All | Success | Error]         │   │
│            │  │ [Type: All | Availability | Pricing | Booking]│
│            │  │                                         │   │
│            │  │ • 2 min ago - ✅ Availability synced     │   │
│            │  │   Beach Villa (12 days)                 │   │
│            │  │                                         │   │
│            │  │ • 5 min ago - ✅ Booking imported        │   │
│            │  │   BK-12345, Mountain Cabin              │   │
│            │  │                                         │   │
│            │  │ • 10 min ago - ✅ Pricing synced         │   │
│            │  │   City Apartment (€80/night)            │   │
│            │  │                                         │   │
│            │  │ • 15 min ago - ❌ Sync failed (rate limit)│   │
│            │  │   Beach Villa (retry in 5 min)          │   │
│            │  │                                         │   │
│            │  │ [Load More]                             │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Mapped Properties (12)                  │   │
│            │  │                                         │   │
│            │  │ • Beach Villa → airbnb_listing_789      │   │
│            │  │ • Mountain Cabin → airbnb_listing_456   │   │
│            │  │ • City Apartment → airbnb_listing_123   │   │
│            │  │                                         │   │
│            │  │ [View All Mappings →]                   │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Danger Zone                             │   │
│            │  │                                         │   │
│            │  │ [Disconnect Airbnb]                     │   │
│            │  │                                         │   │
│            │  │ ⚠️  This will stop syncing with Airbnb. │   │
│            │  │    Your bookings will not be deleted.   │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Components:**

1. **Header:**
   - Channel Name (Airbnb)
   - Status (Active, Warning, Error)
   - Last Sync Time
   - Actions: [Sync Now] [Disconnect]

2. **Sync Statistics:**
   - Synced Properties (count)
   - Synced Bookings (count)
   - Last Availability Sync (time)
   - Last Pricing Sync (time)
   - Success Rate (percentage)

3. **Sync Logs:**
   - Filters: All | Success | Error
   - Type Filter: All | Availability | Pricing | Booking
   - Log Entries:
     - Timestamp
     - Status (✅ Success, ❌ Error)
     - Operation (Availability synced, Booking imported, etc.)
     - Details (Property name, Booking ID, etc.)
   - [Load More] Button

4. **Mapped Properties:**
   - List of properties mapped to channel listings
   - "View All Mappings" link

5. **Danger Zone:**
   - [Disconnect Airbnb] Button
   - Warning message

---

### 2.6 Team & Roles

#### 2.6.1 Team Members

**Purpose:** Übersicht über Team Members, Invite/Remove

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Team                            [+ Invite Member]│
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  Team Members (4)                               │
│ Dashboard  │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 🏠         │  │ Member Row 1                            │   │
│Properties  │  │                                         │   │
│            │  │ [Avatar] John Owner                     │   │
│ 📅         │  │          john@pms-webapp.com            │   │
│ Bookings   │  │          Role: Owner                    │   │
│            │  │          Status: Active                 │   │
│ 🔗         │  │                                         │   │
│ Channels   │  │          [Edit Role] [Remove] (disabled)│   │
│            │  └─────────────────────────────────────────┘   │
│ 👥         │                                                 │
│  Team      │  ┌─────────────────────────────────────────┐   │
│            │  │ Member Row 2                            │   │
│ ⚙️         │  │                                         │   │
│ Settings   │  │ [Avatar] Jane Manager                   │   │
│            │  │          jane@example.com               │   │
│            │  │          Role: Manager                  │   │
│            │  │          Status: Active                 │   │
│            │  │                                         │   │
│            │  │          [Edit Role] [Remove]           │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Member Row 3                            │   │
│            │  │                                         │   │
│            │  │ [Avatar] Mike Staff                     │   │
│            │  │          mike@example.com               │   │
│            │  │          Role: Staff                    │   │
│            │  │          Status: Active                 │   │
│            │  │                                         │   │
│            │  │          [Edit Role] [Remove]           │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Member Row 4                            │   │
│            │  │                                         │   │
│            │  │ [Avatar] Sarah Viewer                   │   │
│            │  │          sarah@example.com              │   │
│            │  │          Role: Viewer                   │   │
│            │  │          Status: ⏳ Pending Invitation   │   │
│            │  │                                         │   │
│            │  │          [Resend Invite] [Cancel]       │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Components:**

1. **Header:**
   - Title: "Team"
   - Action: "+ Invite Member" Button (Owner, Manager only)

2. **Member Row:**
   - Avatar (profile picture or initials)
   - Name
   - Email
   - Role (Owner, Manager, Staff, Viewer)
   - Status: Active, Pending Invitation
   - Actions:
     - [Edit Role] (Owner only, cannot edit own role)
     - [Remove] (Owner only, cannot remove self)
     - [Resend Invite] [Cancel] (for pending invitations)

**Permissions:**
- **Owner:** Can invite, edit roles, remove members (cannot remove self)
- **Manager:** Can view team, cannot edit/remove
- **Staff/Viewer:** Cannot access Team page

**Empty State:**
```
┌─────────────────────────────────────────┐
│                                         │
│         [Icon: People]                  │
│                                         │
│      No team members yet                │
│                                         │
│  Invite team members to collaborate     │
│  on property management.                │
│                                         │
│         [+ Invite Member]               │
│                                         │
└─────────────────────────────────────────┘
```

---

#### 2.6.2 Invite Member

**Purpose:** Formular zum Einladen eines neuen Team Members

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Invite Team Member               [× Close]     │
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  ┌─────────────────────────────────────────┐   │
│ Dashboard  │  │ Invite a team member                    │   │
│            │  │                                         │   │
│ 🏠         │  │ Email *                                 │   │
│Properties  │  │ [jane@example.com               ]       │   │
│            │  │                                         │   │
│ 📅         │  │ Role *                                  │   │
│ Bookings   │  │ [Dropdown: Manager ▼]                   │   │
│            │  │                                         │   │
│ 🔗         │  │ ────────────────────────────────────    │   │
│ Channels   │  │                                         │   │
│            │  │ Role Permissions:                       │   │
│ 👥         │  │                                         │   │
│  Team      │  │ Owner:                                  │   │
│            │  │ ✅ Full access to all features          │   │
│ ⚙️         │  │ ✅ Manage team members                  │   │
│ Settings   │  │ ✅ Financial settings                   │   │
│            │  │                                         │   │
│            │  │ Manager:                                │   │
│            │  │ ✅ Create & edit properties             │   │
│            │  │ ✅ Manage bookings                      │   │
│            │  │ ✅ View channels (cannot connect)       │   │
│            │  │ ❌ Manage team                          │   │
│            │  │ ❌ Financial settings                   │   │
│            │  │                                         │   │
│            │  │ Staff:                                  │   │
│            │  │ ✅ View properties (read-only)          │   │
│            │  │ ✅ View upcoming bookings               │   │
│            │  │ ✅ Check-in/out guests                  │   │
│            │  │ ❌ Create/edit properties               │   │
│            │  │ ❌ Financial data                       │   │
│            │  │                                         │   │
│            │  │ Viewer:                                 │   │
│            │  │ ✅ View all properties & bookings       │   │
│            │  │ ❌ Create/edit/delete anything          │   │
│            │  │                                         │   │
│            │  │ ────────────────────────────────────    │   │
│            │  │                                         │   │
│            │  │ Personal Message (optional)             │   │
│            │  │ [Hi Jane, I'd like you to help...   ]  │   │
│            │  │                                         │   │
│            │  │          [Cancel] [Send Invitation]     │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Form Fields:**
- Email (required)
- Role (dropdown: Owner, Manager, Staff, Viewer)
- Personal Message (optional, textarea)

**Role Permissions (Info Box):**
- Displays permissions for each role
- Updates when role is selected

**Validation:**
- Email must be valid
- Email cannot already be in team
- Cannot invite multiple users with same email

---

### 2.7 Settings

#### 2.7.1 Account Settings

**Purpose:** User-spezifische Settings (Profile, Password, Notifications)

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Settings                                      │
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  Tabs: [Account] [Payment] [Notifications] [Billing]│
│ Dashboard  │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 🏠         │  │ Profile                                 │   │
│Properties  │  │                                         │   │
│            │  │ [Avatar Upload]                         │   │
│ 📅         │  │                                         │   │
│ Bookings   │  │ First Name *                            │   │
│            │  │ [John                           ]       │   │
│ 🔗         │  │                                         │   │
│ Channels   │  │ Last Name *                             │   │
│            │  │ [Owner                          ]       │   │
│ 👥         │  │                                         │   │
│  Team      │  │ Email *                                 │   │
│            │  │ [john@pms-webapp.com            ]       │   │
│ ⚙️         │  │                                         │   │
│ Settings   │  │ Phone                                   │   │
│            │  │ [+49 123 456789                 ]       │   │
│            │  │                                         │   │
│            │  │ [Save Changes]                          │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Change Password                         │   │
│            │  │                                         │   │
│            │  │ Current Password *                      │   │
│            │  │ [••••••••                       ]       │   │
│            │  │                                         │   │
│            │  │ New Password *                          │   │
│            │  │ [••••••••                       ]       │   │
│            │  │                                         │   │
│            │  │ Confirm New Password *                  │   │
│            │  │ [••••••••                       ]       │   │
│            │  │                                         │   │
│            │  │ [Update Password]                       │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Language & Timezone                     │   │
│            │  │                                         │   │
│            │  │ Language: [English ▼]                   │   │
│            │  │ Timezone: [Europe/Berlin ▼]             │   │
│            │  │                                         │   │
│            │  │ [Save Changes]                          │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

---

#### 2.7.2 Payment Settings

**Purpose:** Stripe-Integration konfigurieren

**Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar   │  Settings > Payment                            │
├────────────┼──────────────────────────────────────────────┤
│            │                                                 │
│ 📊         │  Tabs: [Account] [Payment] [Notifications] [Billing]│
│ Dashboard  │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 🏠         │  │ Stripe Integration                      │   │
│Properties  │  │                                         │   │
│            │  │ Status: ✅ Connected                     │   │
│ 📅         │  │ Account: john@pms-webapp.com            │   │
│ Bookings   │  │                                         │   │
│            │  │ [Disconnect Stripe]                     │   │
│ 🔗         │  └─────────────────────────────────────────┘   │
│ Channels   │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│ 👥         │  │ Payment Methods                         │   │
│  Team      │  │                                         │   │
│            │  │ ℹ️  Guests pay via Stripe on Direct      │   │
│ ⚙️         │  │    Booking checkout.                    │   │
│ Settings   │  │                                         │   │
│            │  │ Supported Methods:                      │   │
│            │  │ ✅ Credit/Debit Cards (Visa, MC, Amex)  │   │
│            │  │ ✅ SEPA Direct Debit (EU)               │   │
│            │  │ ✅ iDEAL (Netherlands)                  │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
│            │  ┌─────────────────────────────────────────┐   │
│            │  │ Payout Settings                         │   │
│            │  │                                         │   │
│            │  │ Payout Schedule: Weekly (Friday)        │   │
│            │  │ Payout Account: DE89 3704 0044 0532 0130 │   │
│            │  │                                         │   │
│            │  │ [Manage Payouts in Stripe Dashboard]    │   │
│            │  └─────────────────────────────────────────┘   │
│            │                                                 │
└────────────┴──────────────────────────────────────────────┘
```

**Permissions:**
- **Owner:** Full access
- **Manager/Staff/Viewer:** Cannot access Payment Settings

---

## 3. Design-System-Grundlagen

### 3.1 Spacing Scale

**Base Unit:** 4px (0.25rem)

| Token | Value | Use Case |
|-------|-------|----------|
| `space-0` | 0px | No spacing |
| `space-1` | 4px | Tight spacing (icon-text gap) |
| `space-2` | 8px | Compact spacing (button padding) |
| `space-3` | 12px | Small spacing (form field gap) |
| `space-4` | 16px | Default spacing (card padding) |
| `space-6` | 24px | Medium spacing (section gap) |
| `space-8` | 32px | Large spacing (page margin) |
| `space-12` | 48px | XL spacing (hero section) |
| `space-16` | 64px | XXL spacing (page header) |

**Layout Application:**
- **Padding (Cards, Containers):** `space-4` (16px)
- **Gap (Flex, Grid):** `space-3` (12px) or `space-4` (16px)
- **Margin (Sections):** `space-6` (24px) or `space-8` (32px)
- **Page Margins:** `space-8` (32px) Desktop, `space-4` (16px) Mobile

---

### 3.2 Typography Scale

**Font Family:**
- **Heading:** `[TBD - Sans-serif, e.g., Inter, Roboto]`
- **Body:** `[TBD - Sans-serif, same as heading]`
- **Mono:** `[TBD - Monospace, e.g., Fira Code, Consolas]`

**Font Size:**

| Token | Size | Line Height | Use Case |
|-------|------|-------------|----------|
| `text-xs` | 12px | 16px | Small labels, captions |
| `text-sm` | 14px | 20px | Secondary text, helper text |
| `text-base` | 16px | 24px | Body text (default) |
| `text-lg` | 18px | 28px | Large body text |
| `text-xl` | 20px | 28px | Section headings |
| `text-2xl` | 24px | 32px | Page headings |
| `text-3xl` | 30px | 36px | Hero headings |
| `text-4xl` | 36px | 40px | Display headings |

**Font Weight:**

| Token | Value | Use Case |
|-------|-------|----------|
| `font-normal` | 400 | Body text |
| `font-medium` | 500 | Labels, buttons |
| `font-semibold` | 600 | Headings, emphasis |
| `font-bold` | 700 | Strong emphasis |

**Typography Application:**
- **Page Headings:** `text-2xl` + `font-semibold`
- **Section Headings:** `text-xl` + `font-medium`
- **Body Text:** `text-base` + `font-normal`
- **Labels:** `text-sm` + `font-medium`
- **Helper Text:** `text-xs` + `font-normal`

---

### 3.3 Button Patterns

**Button Variants:**

```
Primary Button:   [Book Now]
  - Use: Primary actions (submit, confirm, save)
  - Style: Solid background, white text

Secondary Button: [Cancel]
  - Use: Secondary actions (cancel, back)
  - Style: Outline border, transparent background

Ghost Button:     [View Details →]
  - Use: Tertiary actions (links, navigation)
  - Style: No background, colored text

Danger Button:    [Delete Property]
  - Use: Destructive actions (delete, disconnect)
  - Style: Red background, white text
```

**Button Sizes:**

| Size | Height | Padding (X) | Font Size | Use Case |
|------|--------|-------------|-----------|----------|
| `sm` | 32px | 12px | `text-sm` | Compact buttons (tables, cards) |
| `md` | 40px | 16px | `text-base` | Default buttons (forms, actions) |
| `lg` | 48px | 24px | `text-lg` | Primary CTAs (hero, checkout) |

**Button States:**
- **Default:** Normal appearance
- **Hover:** Slightly darker background (10% darker)
- **Active:** Pressed appearance (darker background, slight scale)
- **Disabled:** Opacity 50%, cursor not-allowed
- **Loading:** Spinner icon + "Loading..." text

---

### 3.4 Form Patterns

**Input Fields:**

```
Text Input:
┌────────────────────────────────┐
│ Property Name                  │  ← Label (text-sm, font-medium)
│ [Beach Villa               ]   │  ← Input (text-base, height: 40px)
│ ↑ Helper text (optional)       │  ← Helper (text-xs)
└────────────────────────────────┘
```

**Input States:**
- **Default:** Gray border, white background
- **Focus:** Blue border (2px), subtle shadow
- **Error:** Red border, error message below
- **Disabled:** Gray background, opacity 60%

**Form Layout:**
- **Label:** Above input (mobile), left side (desktop, optional)
- **Helper Text:** Below input (text-xs, gray)
- **Error Message:** Below input (text-xs, red)
- **Required Indicator:** Asterisk (*) after label

---

### 3.5 Status Components

**Badges (Status Indicators):**

```
✅ Confirmed    (Green background, dark green text)
🔵 Reserved     (Blue background, dark blue text)
🟢 Checked-in   (Green background, white text)
🟠 Checked-out  (Orange background, white text)
❌ Cancelled    (Red background, white text)
⚠️ Warning      (Yellow background, dark yellow text)
⏳ Pending      (Gray background, dark gray text)
```

**Badge Pattern:**
- **Size:** `text-xs`, padding `space-1` × `space-2` (4px × 8px)
- **Border Radius:** Small (4px)
- **Icon:** Optional emoji/icon prefix

**Alerts (Messages):**

```
Success:  ✅ [Your booking has been confirmed!]
Error:    ❌ [Payment failed. Please try again.]
Warning:  ⚠️  [Booking expires in 5 minutes.]
Info:     ℹ️  [Free cancellation before Jul 1.]
```

**Alert Pattern:**
- **Background:** Light color (success, error, warning, info)
- **Border:** Solid 1px, matching color (darker)
- **Padding:** `space-3` (12px)
- **Icon:** Prefix icon/emoji
- **Dismiss:** Close button (×) top-right (optional)

---

### 3.6 Layout-Grundlagen

**Grid System:**
- **Columns:** 12-column grid (desktop), 4-column (mobile)
- **Gutter:** `space-4` (16px) Desktop, `space-3` (12px) Mobile
- **Max Width:** 1280px (Desktop), 100% (Mobile)

**Breakpoints:**

| Breakpoint | Width | Use Case |
|------------|-------|----------|
| `sm` | 640px | Mobile landscape |
| `md` | 768px | Tablet |
| `lg` | 1024px | Desktop |
| `xl` | 1280px | Large desktop |
| `2xl` | 1536px | XL desktop |

**Responsive Patterns:**
- **Mobile:** Single column, stack vertically
- **Tablet:** 2 columns for cards, single column for content
- **Desktop:** Multi-column layout (sidebar + main content)

**Container Sizes:**
- **Full Width:** 100% (mobile)
- **Constrained:** 1280px max (desktop), centered

---

## 4. UI States

### 4.1 Empty States

**Purpose:** Zeigen, wenn keine Daten vorhanden sind

**Pattern:**

```
┌─────────────────────────────────────────┐
│                                         │
│         [Icon: Relevant to context]     │
│                                         │
│      [Heading: "No {items} yet"]        │
│                                         │
│  [Description: Helpful next step]       │
│                                         │
│         [Primary Action Button]         │
│                                         │
└─────────────────────────────────────────┘
```

**Examples:**

**Properties (Empty):**
```
[Icon: Empty Folder]
No properties yet

Get started by adding your first property
to start managing bookings.

[+ Add Property]
```

**Bookings (Empty):**
```
[Icon: Empty Calendar]
No bookings yet

Start by creating a booking or wait for
guests to book through channels.

[+ Create Booking]
```

**Channels (Empty):**
```
[Icon: Link/Chain]
No channels connected

Connect to Airbnb, Booking.com and more
to sync your properties and prevent
double-bookings.

[+ Connect Channel]
```

**Team (Empty):**
```
[Icon: People]
No team members yet

Invite team members to collaborate on
property management.

[+ Invite Member]
```

---

### 4.2 Loading States

**Purpose:** Zeigen, während Daten geladen werden

**Pattern:**

**1. Skeleton Loaders (bevorzugt):**
```
┌─────────────────────────────────────────┐
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                   │  ← Gray boxes (animated pulse)
│ ▓▓▓▓▓▓▓▓▓▓▓                             │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                 │
└─────────────────────────────────────────┘
```

**2. Spinner (für Actions):**
```
┌─────────────────────┐
│    [Spinner Icon]   │
│    Loading...       │
└─────────────────────┘
```

**Examples:**

**Property List (Loading):**
```
Property Card (Skeleton):
┌──────┐
│ ▓▓▓▓ │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
│ ▓▓▓▓ │ ▓▓▓▓▓▓▓▓▓▓▓
└──────┘
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
▓▓▓▓▓▓▓▓▓▓▓
```

**Button (Loading):**
```
[Spinner] Saving...
```

---

### 4.3 Error States

**Purpose:** Zeigen, wenn ein Fehler aufgetreten ist

**Pattern:**

```
┌─────────────────────────────────────────┐
│                                         │
│         [Icon: Error/Alert]             │
│                                         │
│      [Heading: "Something went wrong"]  │
│                                         │
│  [Error Message: Detailed description]  │
│                                         │
│         [Retry Button]                  │
│         [Support Link]                  │
│                                         │
└─────────────────────────────────────────┘
```

**Examples:**

**API Error:**
```
❌ Something went wrong

We couldn't load your properties.
Please try again.

[Retry]  [Contact Support]
```

**Payment Error:**
```
❌ Payment Failed

Your payment could not be processed.
Please check your card details and try again.

[Try Again]  [Use Different Card]
```

**Network Error:**
```
❌ Connection Lost

We're having trouble connecting to the server.
Please check your internet connection.

[Retry]
```

**Form Validation Error:**
```
Email Address
[john@example                    ]  ← Red border
↑ Please enter a valid email address  ← Red text (text-xs)
```

---

### 4.4 Permission Denied

**Purpose:** Zeigen, wenn User keine Berechtigung hat

**Pattern:**

```
┌─────────────────────────────────────────┐
│                                         │
│         [Icon: Lock/Shield]             │
│                                         │
│      [Heading: "Permission Denied"]     │
│                                         │
│  [Message: What user cannot do]         │
│                                         │
│         [Back to Dashboard]             │
│                                         │
└─────────────────────────────────────────┘
```

**Examples:**

**Staff trying to access Channels:**
```
🔒 Permission Denied

You don't have permission to access
Channel Connections.

Contact your manager if you need access.

[Back to Dashboard]
```

**Viewer trying to edit Property:**
```
🔒 View-Only Access

You can view properties but cannot
make changes.

Contact the property owner to request
edit permissions.

[Back to Properties]
```

---

### 4.5 Success / Confirmation

**Purpose:** Bestätigen, dass eine Aktion erfolgreich war

**Pattern:**

```
┌─────────────────────────────────────────┐
│                                         │
│         [Icon: Checkmark]               │
│                                         │
│      [Heading: "Success!"]              │
│                                         │
│  [Message: What happened]               │
│                                         │
│         [Next Action Button]            │
│                                         │
└─────────────────────────────────────────┘
```

**Examples:**

**Booking Confirmed:**
```
✅ Booking Confirmed!

Your booking has been successfully confirmed.
A confirmation email has been sent to:
john@example.com

[View Booking]  [Download Invoice]
```

**Property Created:**
```
✅ Property Created!

Beach Villa has been added to your properties.

What's next?
• Add photos
• Set pricing rules
• Connect to channels

[View Property]  [Add Photos]
```

**Channel Connected:**
```
✅ Successfully Connected!

Your Airbnb account has been connected.

Sync Status:
• Properties: 12 synced
• Bookings: 24 synced

[View Channel Details]
```

**Toast Notification (temporary, auto-dismiss):**
```
┌──────────────────────────────────┐
│ ✅ Property updated successfully │
└──────────────────────────────────┘
```

---

## 5. Component Specifications

### 5.1 Card Component

**Purpose:** Container für Inhalt (Property Card, Booking Card, etc.)

**Anatomy:**
```
┌───────────────────────────────┐
│ Header (optional)             │  ← Card Header
├───────────────────────────────┤
│                               │
│ Content                       │  ← Card Body
│                               │
├───────────────────────────────┤
│ Footer (optional)             │  ← Card Footer
└───────────────────────────────┘
```

**Specifications:**
- **Padding:** `space-4` (16px)
- **Border:** 1px solid, light gray
- **Border Radius:** Medium (8px)
- **Shadow:** Subtle (0 1px 3px rgba(0,0,0,0.1))
- **Hover:** Shadow increases (elevation)

---

### 5.2 Table Component

**Purpose:** Tabellarische Darstellung von Daten

**Anatomy:**
```
┌─────┬─────────────┬──────────┬─────────┐
│ ID  │ Property    │ Guest    │ Actions │  ← Header
├─────┼─────────────┼──────────┼─────────┤
│ 123 │ Beach Villa │ John Doe │ [View]  │  ← Row
├─────┼─────────────┼──────────┼─────────┤
│ 124 │ Cabin       │ Jane S.  │ [View]  │  ← Row
└─────┴─────────────┴──────────┴─────────┘
```

**Specifications:**
- **Header:** `font-medium`, `text-sm`, gray background
- **Row:** `text-base`, white background (odd), light gray (even, zebra striping)
- **Padding:** `space-2` × `space-3` (8px × 12px)
- **Border:** 1px solid, light gray (between rows)
- **Hover:** Row background changes (light blue)

---

### 5.3 Modal/Dialog Component

**Purpose:** Overlay für Actions (Create, Edit, Confirm, etc.)

**Anatomy:**
```
┌─────────────────────────────────────────┐
│ [Backdrop - semi-transparent dark]      │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │ Modal Header          [× Close] │   │  ← Modal
│   ├─────────────────────────────────┤   │
│   │                                 │   │
│   │ Modal Content                   │   │
│   │                                 │   │
│   ├─────────────────────────────────┤   │
│   │ Modal Footer (Actions)          │   │
│   │              [Cancel] [Confirm] │   │
│   └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

**Specifications:**
- **Backdrop:** Semi-transparent black (opacity 50%)
- **Modal:** White background, centered, max-width 600px
- **Padding:** `space-6` (24px)
- **Border Radius:** Large (12px)
- **Shadow:** Large (0 20px 25px rgba(0,0,0,0.1))
- **Close Button:** Top-right (×), gray

---

## 6. Appendix

### 6.1 Glossar

| Begriff | Definition |
|---------|------------|
| **Wireframe** | Low-fidelity visual representation of UI |
| **Skeleton Loader** | Animated placeholder while content loads |
| **Toast Notification** | Temporary notification (auto-dismiss) |
| **Badge** | Small status indicator (colored label) |
| **Empty State** | UI when no data is available |
| **Modal** | Overlay dialog for actions/confirmation |

### 6.2 Naming Conventions

**Components:**
- PascalCase: `PropertyCard`, `BookingCalendar`, `ChannelConnectionCard`

**Routes:**
- kebab-case: `/app/properties`, `/app/booking-calendar`, `/app/channel-connections`

**CSS Classes (wenn Tailwind):**
- Utility-first: `p-4`, `text-base`, `bg-blue-500`

### 6.3 Accessibility Notes

**WCAG 2.1 AA Compliance:**
- ✅ Color Contrast: 4.5:1 (normal text), 3:1 (large text)
- ✅ Keyboard Navigation: All interactive elements focusable
- ✅ Screen Reader Support: Semantic HTML + ARIA labels
- ✅ Focus Indicators: Visible focus ring (2px blue outline)

**Focus Management:**
- Modals: Focus trapped within modal
- Forms: Auto-focus on first input (optional)
- Errors: Focus on first error field

---

**Ende der UI/UX-Konzeption (Phase 10A)**

**Next Step:** Implementation (Frontend Development mit Next.js, TanStack Query, Zustand)
