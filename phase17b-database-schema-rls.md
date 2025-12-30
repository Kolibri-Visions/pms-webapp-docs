# Phase 17B: Database Schema & RLS Policies

**Version:** 1.0
**Erstellt:** 2025-12-22
**Projekt:** PMS-Webapp (B2B SaaS für Ferienwohnungs-Agenturen)
**Basis:** Phase 6 (Supabase RLS), Phase 11-13 (RBAC), Phase 15-16 (Direct Booking & Eigentümer)

---

## Executive Summary

### Ziel

Vollständiges PostgreSQL/Supabase Schema-Dokument mit allen Tabellen, Indexes, RLS Policies und Migrations für die PMS-Webapp MVP. Dieses Dokument dient als zentrale Referenz für die Datenbank-Struktur und als Basis für alle weiteren Entwicklungsarbeiten.

### Scope

- **Core Tables:** Authentication, Users, Properties, Bookings, Channels, Financials
- **RBAC-Integration:** 5 Rollen (Admin, Manager, Staff, Eigentümer, Buchhalter)
- **Multi-Tenancy:** Agency-Level Isolation (RLS)
- **Eigentümer-Isolation:** Property-Owner-Level Isolation (RLS)
- **Direct Booking:** Integration von Direct Bookings über Agentur-Website
- **Channel-Sync:** iCal Import/Export für Airbnb, Booking.com

### Leitplanken

- **PostgreSQL 15+** mit Supabase Extensions
- **Row-Level Security (RLS)** für alle Tabellen
- **UUID** für Primary Keys
- **Timestamps** (created_at, updated_at) auf allen Tabellen
- **Soft Deletes** wo sinnvoll (deleted_at)
- **Audit-Trail** für sensible Operationen
- **Sprache:** DEUTSCH (Kommentare, Beschreibungen)

---

## 1. Technologie-Stack

### 1.1 PostgreSQL & Supabase

**PostgreSQL Version:** 15+
**Supabase Managed:** Ja
**Hosting:** Supabase EU (DSGVO-konform)

**Extensions:**
- `uuid-ossp` - UUID-Generierung
- `postgis` - Geospatial-Support für Property-Locations
- `btree_gist` - GiST-Indexes für Exclusion Constraints
- `pg_trgm` - Trigram-Suche für Fuzzy-Search

### 1.2 Datenbank-Konventionen

**Naming:**
- **Tabellen:** Plural, lowercase, snake_case (z.B. `properties`, `team_members`)
- **Spalten:** Singular, lowercase, snake_case (z.B. `agency_id`, `created_at`)
- **Indexes:** `idx_<table>_<columns>` (z.B. `idx_properties_agency`)
- **Foreign Keys:** `fk_<table>_<column>` (z.B. `fk_properties_agency`)
- **Constraints:** `chk_<table>_<condition>` (z.B. `chk_bookings_dates`)

**Datentypen:**
- **IDs:** UUID (gen_random_uuid())
- **Timestamps:** TIMESTAMPTZ (mit Timezone)
- **Strings:** VARCHAR(N) mit sinnvollem Limit, TEXT für unbegrenzte Texte
- **Booleans:** BOOLEAN (NOT NULL mit DEFAULT)
- **Decimals:** DECIMAL(10,2) für Preise
- **JSON:** JSONB für flexible Daten

**Standard-Spalten:**
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

## 2. Core Tables (MVP-Scope)

### 2.1 Authentication & Users

#### 2.1.1 `auth.users` (Supabase managed)

Von Supabase bereitgestellt. Enthält:
- `id` (UUID)
- `email`
- `encrypted_password`
- `email_confirmed_at`
- `created_at`, `updated_at`

Wird NICHT von uns modifiziert.

#### 2.1.2 `agencies`

Agenturen (Multi-Tenant Root-Entity).

```sql
CREATE TABLE agencies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Basic Info
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  phone VARCHAR(50),
  company_name VARCHAR(255),
  tax_id VARCHAR(50),

  -- Subscription
  subscription_tier VARCHAR(50) NOT NULL DEFAULT 'starter'
    CHECK (subscription_tier IN ('starter', 'professional', 'enterprise')),
  subscription_status VARCHAR(50) NOT NULL DEFAULT 'active'
    CHECK (subscription_status IN ('active', 'past_due', 'cancelled', 'suspended')),
  subscription_started_at TIMESTAMPTZ,
  subscription_ends_at TIMESTAMPTZ,

  -- Stripe Integration
  stripe_customer_id VARCHAR(255) UNIQUE,
  stripe_subscription_id VARCHAR(255),

  -- Settings
  settings JSONB NOT NULL DEFAULT '{
    "timezone": "Europe/Berlin",
    "currency": "EUR",
    "language": "de",
    "date_format": "DD.MM.YYYY"
  }'::jsonb,

  -- Branding
  logo_url TEXT,
  brand_colors JSONB DEFAULT '{"primary": "#2563EB", "secondary": "#16A34A"}'::jsonb,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE agencies IS 'Agenturen (Multi-Tenant Root-Entity)';
COMMENT ON COLUMN agencies.subscription_tier IS 'Starter (5-20 Obj), Professional (21-100 Obj), Enterprise (100+ Obj)';
COMMENT ON COLUMN agencies.settings IS 'Agentur-spezifische Einstellungen (Timezone, Sprache, etc.)';
```

**Indexes:**
```sql
CREATE INDEX idx_agencies_email ON agencies(email);
CREATE INDEX idx_agencies_stripe_customer ON agencies(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
```

#### 2.1.3 `profiles`

User-Profile (erweitert auth.users).

```sql
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Personal Info
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  display_name VARCHAR(200),
  avatar_url TEXT,
  phone VARCHAR(50),

  -- Preferences
  preferred_language VARCHAR(10) DEFAULT 'de',
  preferred_timezone VARCHAR(50) DEFAULT 'Europe/Berlin',
  notification_preferences JSONB DEFAULT '{
    "email": {"bookings": true, "payments": true, "reminders": true},
    "push": {"bookings": true, "payments": false, "reminders": true}
  }'::jsonb,

  -- Last Activity
  last_login_at TIMESTAMPTZ,
  last_active_agency_id UUID REFERENCES agencies(id),

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE profiles IS 'User-Profile (erweitert auth.users)';
```

**Indexes:**
```sql
CREATE INDEX idx_profiles_last_active_agency ON profiles(last_active_agency_id);
```

#### 2.1.4 `team_members`

Team-Mitglieder mit Rollen (User-Agency-Mapping).

```sql
CREATE TABLE team_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,

  -- Role (5 Rollen aus Phase 11-13)
  role VARCHAR(50) NOT NULL
    CHECK (role IN ('admin', 'manager', 'staff', 'owner', 'accountant')),

  -- Granular Permissions (optional, falls Rollen-Customization gewünscht)
  permissions JSONB NOT NULL DEFAULT '{
    "bookings": {"create": true, "read": true, "update": true, "delete": false},
    "properties": {"create": true, "read": true, "update": true, "delete": false},
    "guests": {"create": true, "read": true, "update": true, "delete": false},
    "financials": {"read": true, "export": false},
    "settings": {"read": true, "update": false},
    "channels": {"manage": false}
  }'::jsonb,

  -- Invitation Tracking
  invited_by UUID REFERENCES auth.users(id),
  invited_at TIMESTAMPTZ,
  accepted_at TIMESTAMPTZ,

  -- Status
  is_active BOOLEAN NOT NULL DEFAULT true,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(user_id, agency_id)
);

COMMENT ON TABLE team_members IS 'Team-Mitglieder mit Rollen (User-Agency-Mapping)';
COMMENT ON COLUMN team_members.role IS 'admin, manager, staff, owner, accountant';
COMMENT ON COLUMN team_members.permissions IS 'Granulare Permissions (optional für Custom-Rollen)';
```

**Indexes:**
```sql
CREATE INDEX idx_team_members_user_agency ON team_members(user_id, agency_id) WHERE is_active = true;
CREATE INDEX idx_team_members_agency ON team_members(agency_id) WHERE is_active = true;
CREATE INDEX idx_team_members_role ON team_members(role);
```

---

### 2.2 Properties & Amenities

#### 2.2.1 `properties`

Objekte (Ferienwohnungen).

```sql
CREATE TABLE properties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,
  owner_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,

  -- Basic Info
  name VARCHAR(255) NOT NULL,
  internal_name VARCHAR(255),
  description TEXT,
  property_type VARCHAR(50) NOT NULL
    CHECK (property_type IN ('apartment', 'house', 'villa', 'condo', 'room', 'studio', 'cabin', 'cottage', 'chalet')),

  -- Capacity
  bedrooms INTEGER NOT NULL DEFAULT 1 CHECK (bedrooms >= 0),
  beds INTEGER NOT NULL DEFAULT 1 CHECK (beds >= 1),
  bathrooms DECIMAL(3,1) NOT NULL DEFAULT 1.0 CHECK (bathrooms >= 0),
  max_guests INTEGER NOT NULL DEFAULT 2 CHECK (max_guests > 0),

  -- Size
  size_sqm DECIMAL(8,2),

  -- Location
  address_line1 VARCHAR(255) NOT NULL,
  address_line2 VARCHAR(255),
  city VARCHAR(100) NOT NULL,
  postal_code VARCHAR(20) NOT NULL,
  country VARCHAR(2) NOT NULL DEFAULT 'DE',
  location GEOGRAPHY(POINT, 4326),

  -- Check-in/out
  check_in_time TIME NOT NULL DEFAULT '15:00',
  check_out_time TIME NOT NULL DEFAULT '10:00',
  check_in_instructions TEXT,

  -- Pricing Defaults
  base_price DECIMAL(10,2) NOT NULL DEFAULT 0,
  currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
  cleaning_fee DECIMAL(10,2) DEFAULT 0,
  security_deposit DECIMAL(10,2) DEFAULT 0,
  extra_guest_fee DECIMAL(10,2) DEFAULT 0,
  extra_guest_threshold INTEGER DEFAULT 1,

  -- Minimum/Maximum Stay
  min_stay INTEGER NOT NULL DEFAULT 1 CHECK (min_stay >= 1),
  max_stay INTEGER DEFAULT 365 CHECK (max_stay >= 1),

  -- Booking Settings
  advance_notice_days INTEGER DEFAULT 1,
  booking_window_days INTEGER DEFAULT 365,
  instant_book_enabled BOOLEAN DEFAULT false,

  -- Tax Configuration
  tax_rate DECIMAL(5,2) DEFAULT 0,
  tax_included BOOLEAN DEFAULT true,

  -- Status
  is_active BOOLEAN NOT NULL DEFAULT true,
  listed_at TIMESTAMPTZ,

  -- External IDs (für Channel-Sync)
  external_ids JSONB DEFAULT '{}'::jsonb,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

COMMENT ON TABLE properties IS 'Objekte (Ferienwohnungen)';
COMMENT ON COLUMN properties.owner_id IS 'Eigentümer (für Rolle "Property Owner", optional)';
COMMENT ON COLUMN properties.external_ids IS 'Airbnb-ID, Booking.com-ID, etc. für Sync';
```

**Indexes:**
```sql
CREATE INDEX idx_properties_agency ON properties(agency_id);
CREATE INDEX idx_properties_owner ON properties(owner_id) WHERE owner_id IS NOT NULL;
CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_active ON properties(is_active) WHERE is_active = true;
CREATE INDEX idx_properties_location ON properties USING GIST(location);
```

#### 2.2.2 `property_photos`

Property-Fotos.

```sql
CREATE TABLE property_photos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

  -- Image URLs
  url TEXT NOT NULL,
  thumbnail_url TEXT,

  -- Metadata
  caption TEXT,
  alt_text TEXT,

  -- Display
  is_primary BOOLEAN DEFAULT false,
  display_order INTEGER DEFAULT 0,

  -- Image Info
  width INTEGER,
  height INTEGER,
  file_size INTEGER,
  mime_type VARCHAR(50),

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE property_photos IS 'Property-Fotos';
```

**Indexes:**
```sql
CREATE INDEX idx_property_photos_property ON property_photos(property_id, display_order);
CREATE INDEX idx_property_photos_primary ON property_photos(property_id) WHERE is_primary = true;
```

#### 2.2.3 `property_amenities`

Property-Ausstattung (viele-zu-viele Relation).

```sql
CREATE TABLE property_amenities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  amenity_code VARCHAR(50) NOT NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(property_id, amenity_code)
);

COMMENT ON TABLE property_amenities IS 'Property-Ausstattung (viele-zu-viele Relation)';
COMMENT ON COLUMN property_amenities.amenity_code IS 'wifi, kitchen, parking, pool, etc.';
```

**Indexes:**
```sql
CREATE INDEX idx_property_amenities_property ON property_amenities(property_id);
CREATE INDEX idx_property_amenities_code ON property_amenities(amenity_code);
```

#### 2.2.4 `amenity_definitions`

Referenz-Daten für Ausstattungen.

```sql
CREATE TABLE amenity_definitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(50) NOT NULL UNIQUE,
  name_en VARCHAR(100) NOT NULL,
  name_de VARCHAR(100) NOT NULL,
  category VARCHAR(50) NOT NULL
    CHECK (category IN ('essentials', 'features', 'location', 'safety', 'accessibility')),
  icon VARCHAR(50),
  display_order INTEGER DEFAULT 0,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE amenity_definitions IS 'Referenz-Daten für Ausstattungen (Seed-Data)';

-- Seed Data (Beispiel)
INSERT INTO amenity_definitions (code, name_en, name_de, category, display_order) VALUES
('wifi', 'WiFi', 'WLAN', 'essentials', 1),
('kitchen', 'Kitchen', 'Küche', 'essentials', 2),
('parking', 'Free parking', 'Kostenloser Parkplatz', 'features', 10),
('pool', 'Pool', 'Pool', 'features', 11),
('air_conditioning', 'Air conditioning', 'Klimaanlage', 'features', 3),
('heating', 'Heating', 'Heizung', 'essentials', 4);
```

**Indexes:**
```sql
CREATE INDEX idx_amenity_definitions_category ON amenity_definitions(category);
```

---

### 2.3 Bookings

#### 2.3.1 `bookings`

Haupt-Tabelle für alle Buchungen (Source of Truth).

```sql
CREATE TABLE bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE RESTRICT,
  guest_id UUID NOT NULL REFERENCES guests(id) ON DELETE RESTRICT,

  -- Booking Reference (Auto-generiert)
  booking_reference VARCHAR(50) NOT NULL UNIQUE,

  -- Stay Dates
  check_in DATE NOT NULL,
  check_out DATE NOT NULL,

  -- Guest Count
  num_adults INTEGER NOT NULL DEFAULT 1 CHECK (num_adults > 0),
  num_children INTEGER NOT NULL DEFAULT 0 CHECK (num_children >= 0),
  num_infants INTEGER NOT NULL DEFAULT 0 CHECK (num_infants >= 0),
  num_pets INTEGER NOT NULL DEFAULT 0 CHECK (num_pets >= 0),

  -- Computed
  num_guests INTEGER GENERATED ALWAYS AS (num_adults + num_children) STORED,
  num_nights INTEGER GENERATED ALWAYS AS (check_out - check_in) STORED,

  -- Source Tracking
  source VARCHAR(50) NOT NULL
    CHECK (source IN ('direct', 'airbnb', 'booking_com', 'expedia', 'fewo_direkt', 'google', 'other')),
  channel_booking_id VARCHAR(255),
  channel_guest_id VARCHAR(255),

  -- Status
  status VARCHAR(50) NOT NULL DEFAULT 'inquiry'
    CHECK (status IN ('inquiry', 'pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled', 'declined', 'no_show')),

  -- Optimistic Locking
  version INTEGER NOT NULL DEFAULT 1,

  -- Pricing Breakdown
  nightly_rate DECIMAL(10,2) NOT NULL,
  subtotal DECIMAL(10,2) NOT NULL,
  cleaning_fee DECIMAL(10,2) DEFAULT 0,
  service_fee DECIMAL(10,2) DEFAULT 0,
  extra_guest_fee DECIMAL(10,2) DEFAULT 0,
  discount_amount DECIMAL(10,2) DEFAULT 0,
  discount_code VARCHAR(50),
  tax_amount DECIMAL(10,2) DEFAULT 0,
  total_price DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) NOT NULL DEFAULT 'EUR',

  -- Payment Tracking
  payment_status VARCHAR(50) NOT NULL DEFAULT 'pending'
    CHECK (payment_status IN ('pending', 'partial', 'paid', 'refunded', 'partial_refund', 'failed', 'external')),
  deposit_amount DECIMAL(10,2) DEFAULT 0,
  deposit_paid_at TIMESTAMPTZ,
  paid_amount DECIMAL(10,2) DEFAULT 0,
  paid_at TIMESTAMPTZ,

  -- Stripe Integration
  stripe_payment_intent_id VARCHAR(255),
  stripe_charge_id VARCHAR(255),

  -- Cancellation
  cancellation_policy VARCHAR(50)
    CHECK (cancellation_policy IS NULL OR cancellation_policy IN ('flexible', 'moderate', 'strict', 'non_refundable')),
  cancelled_at TIMESTAMPTZ,
  cancelled_by VARCHAR(50)
    CHECK (cancelled_by IS NULL OR cancelled_by IN ('guest', 'host', 'platform', 'system')),
  cancellation_reason TEXT,
  refund_amount DECIMAL(10,2),

  -- Special Requests
  guest_message TEXT,
  special_requests TEXT,
  internal_notes TEXT,

  -- Channel-Specific Data
  channel_data JSONB DEFAULT '{}'::jsonb,

  -- Key Timestamps
  inquiry_at TIMESTAMPTZ,
  confirmed_at TIMESTAMPTZ,
  check_in_at TIMESTAMPTZ,
  check_out_at TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Constraints
  CONSTRAINT check_dates CHECK (check_out > check_in),
  CONSTRAINT check_channel_id UNIQUE NULLS NOT DISTINCT (source, channel_booking_id),

  -- Prevent Double-Bookings (Exclusion Constraint)
  CONSTRAINT no_double_bookings EXCLUDE USING gist (
    property_id WITH =,
    daterange(check_in, check_out, '[)') WITH &&
  ) WHERE (status NOT IN ('cancelled', 'declined', 'no_show'))
);

COMMENT ON TABLE bookings IS 'Haupt-Tabelle für alle Buchungen (Source of Truth)';
COMMENT ON COLUMN bookings.source IS 'direct (Direct Booking), airbnb, booking_com, etc.';
COMMENT ON COLUMN bookings.booking_reference IS 'Auto-generiert (z.B. PMS-2025-000001)';
COMMENT ON CONSTRAINT no_double_bookings ON bookings IS 'Verhindert Doppelbuchungen auf Datenbank-Ebene';
```

**Indexes:**
```sql
CREATE INDEX idx_bookings_agency ON bookings(agency_id);
CREATE INDEX idx_bookings_property ON bookings(property_id);
CREATE INDEX idx_bookings_guest ON bookings(guest_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_source ON bookings(source);
CREATE INDEX idx_bookings_dates ON bookings(check_in, check_out);
CREATE INDEX idx_bookings_property_dates ON bookings(property_id, check_in, check_out);
CREATE INDEX idx_bookings_channel_id ON bookings(source, channel_booking_id) WHERE channel_booking_id IS NOT NULL;
```

#### 2.3.2 `direct_bookings`

Direct Bookings (über Agentur-Website).

```sql
CREATE TABLE direct_bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE UNIQUE,

  -- Widget-Specific Data
  widget_source VARCHAR(100),
  referrer_url TEXT,
  utm_source VARCHAR(100),
  utm_medium VARCHAR(100),
  utm_campaign VARCHAR(100),

  -- Payment Method
  payment_method VARCHAR(50)
    CHECK (payment_method IN ('stripe', 'paypal', 'bank_transfer', 'other')),
  payment_link TEXT,

  -- Guest IP (für Fraud-Prevention)
  guest_ip INET,
  guest_user_agent TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE direct_bookings IS 'Direct Bookings (über Agentur-Website)';
COMMENT ON COLUMN direct_bookings.widget_source IS 'Welches Widget genutzt wurde (z.B. embedded, standalone)';
```

**Indexes:**
```sql
CREATE INDEX idx_direct_bookings_booking ON direct_bookings(booking_id);
CREATE INDEX idx_direct_bookings_payment_method ON direct_bookings(payment_method);
```

#### 2.3.3 `external_bookings`

External Bookings (iCal Import von Airbnb, Booking.com).

```sql
CREATE TABLE external_bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE UNIQUE,

  -- iCal-Specific
  ical_uid VARCHAR(255) NOT NULL UNIQUE,
  ical_summary TEXT,
  ical_description TEXT,

  -- Channel Connection
  connection_id UUID REFERENCES channel_connections(id) ON DELETE SET NULL,

  -- Last Sync
  last_synced_at TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE external_bookings IS 'External Bookings (iCal Import von Airbnb, Booking.com)';
COMMENT ON COLUMN external_bookings.ical_uid IS 'Unique UID aus iCal-Feed (für Deduplication)';
```

**Indexes:**
```sql
CREATE INDEX idx_external_bookings_booking ON external_bookings(booking_id);
CREATE INDEX idx_external_bookings_ical_uid ON external_bookings(ical_uid);
CREATE INDEX idx_external_bookings_connection ON external_bookings(connection_id);
```

#### 2.3.4 `guests`

Gäste (mit optionalem Auth-Account).

```sql
CREATE TABLE guests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,

  -- Personal Info
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(50),

  -- Optional Link zu Auth (NULL = kein Account)
  auth_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,

  -- Address
  address_line1 VARCHAR(255),
  address_line2 VARCHAR(255),
  city VARCHAR(100),
  postal_code VARCHAR(20),
  country VARCHAR(2),

  -- Identity Verification
  date_of_birth DATE,
  nationality VARCHAR(2),
  id_document_type VARCHAR(50)
    CHECK (id_document_type IS NULL OR id_document_type IN ('passport', 'id_card', 'drivers_license')),
  id_document_number VARCHAR(100),
  id_verified_at TIMESTAMPTZ,

  -- Communication Preferences
  language VARCHAR(10) DEFAULT 'de',
  communication_channel VARCHAR(50) DEFAULT 'email'
    CHECK (communication_channel IN ('email', 'phone', 'whatsapp', 'sms')),
  marketing_consent BOOLEAN DEFAULT false,
  marketing_consent_at TIMESTAMPTZ,

  -- Guest Profile
  profile_notes TEXT,
  vip_status BOOLEAN DEFAULT false,
  blacklisted BOOLEAN DEFAULT false,
  blacklist_reason TEXT,

  -- Statistics
  total_bookings INTEGER DEFAULT 0,
  total_spent DECIMAL(12,2) DEFAULT 0,
  first_booking_at TIMESTAMPTZ,
  last_booking_at TIMESTAMPTZ,
  average_rating DECIMAL(3,2),

  -- Source Tracking
  source VARCHAR(50)
    CHECK (source IS NULL OR source IN ('direct', 'airbnb', 'booking_com', 'expedia', 'fewo_direkt', 'google', 'referral', 'other')),

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,

  UNIQUE(agency_id, email)
);

COMMENT ON TABLE guests IS 'Gäste (mit optionalem Auth-Account für Direct Bookings)';
COMMENT ON COLUMN guests.auth_user_id IS 'Optionaler Link zu auth.users (für Gäste mit Account)';
```

**Indexes:**
```sql
CREATE INDEX idx_guests_agency ON guests(agency_id);
CREATE INDEX idx_guests_email ON guests(email);
CREATE INDEX idx_guests_auth_user ON guests(auth_user_id) WHERE auth_user_id IS NOT NULL;
```

---

### 2.4 Channels & Sync

#### 2.4.1 `channel_connections`

OAuth-Connections zu Airbnb, Booking.com, etc.

```sql
CREATE TABLE channel_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,

  -- Channel Info
  channel VARCHAR(50) NOT NULL
    CHECK (channel IN ('airbnb', 'booking_com', 'expedia', 'fewo_direkt', 'google', 'other')),
  channel_account_id VARCHAR(255),
  channel_account_name VARCHAR(255),

  -- OAuth Tokens (ENCRYPTED at application layer!)
  access_token_encrypted TEXT,
  refresh_token_encrypted TEXT,
  token_expires_at TIMESTAMPTZ,

  -- Sync Config
  sync_enabled BOOLEAN DEFAULT true,
  sync_interval_minutes INTEGER DEFAULT 15,
  last_sync_at TIMESTAMPTZ,
  last_sync_status VARCHAR(50)
    CHECK (last_sync_status IS NULL OR last_sync_status IN ('success', 'failed', 'partial')),
  last_sync_error TEXT,

  -- iCal Config (für passive Sync)
  ical_import_url TEXT,
  ical_export_url TEXT,

  -- Status
  is_active BOOLEAN NOT NULL DEFAULT true,
  connected_at TIMESTAMPTZ,
  disconnected_at TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(agency_id, channel)
);

COMMENT ON TABLE channel_connections IS 'OAuth-Connections zu Airbnb, Booking.com, etc.';
COMMENT ON COLUMN channel_connections.access_token_encrypted IS 'Verschlüsselt auf Applikations-Ebene (NICHT Klartext!)';
```

**Indexes:**
```sql
CREATE INDEX idx_channel_connections_agency ON channel_connections(agency_id);
CREATE INDEX idx_channel_connections_channel ON channel_connections(channel);
CREATE INDEX idx_channel_connections_active ON channel_connections(is_active) WHERE is_active = true;
```

#### 2.4.2 `sync_logs`

Sync-Historie.

```sql
CREATE TABLE sync_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  connection_id UUID NOT NULL REFERENCES channel_connections(id) ON DELETE CASCADE,

  -- Sync Info
  sync_type VARCHAR(50) NOT NULL
    CHECK (sync_type IN ('full', 'incremental', 'manual')),
  sync_direction VARCHAR(50) NOT NULL
    CHECK (sync_direction IN ('import', 'export', 'bidirectional')),

  -- Status
  status VARCHAR(50) NOT NULL
    CHECK (status IN ('started', 'in_progress', 'success', 'failed', 'partial')),

  -- Stats
  items_processed INTEGER DEFAULT 0,
  items_created INTEGER DEFAULT 0,
  items_updated INTEGER DEFAULT 0,
  items_failed INTEGER DEFAULT 0,

  -- Error Details
  error_message TEXT,
  error_details JSONB,

  -- Timestamps
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE sync_logs IS 'Sync-Historie (für Debugging & Monitoring)';
```

**Indexes:**
```sql
CREATE INDEX idx_sync_logs_connection ON sync_logs(connection_id, created_at DESC);
CREATE INDEX idx_sync_logs_status ON sync_logs(status);
```

#### 2.4.3 `webhooks`

Webhook-Events (für Channel-Notifications).

```sql
CREATE TABLE webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  connection_id UUID REFERENCES channel_connections(id) ON DELETE CASCADE,

  -- Event Info
  event_type VARCHAR(100) NOT NULL,
  event_source VARCHAR(50) NOT NULL,
  event_id VARCHAR(255),

  -- Payload
  payload JSONB NOT NULL,

  -- Processing
  processed BOOLEAN DEFAULT false,
  processed_at TIMESTAMPTZ,
  processing_error TEXT,

  -- Retry
  retry_count INTEGER DEFAULT 0,

  -- Timestamps
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE webhooks IS 'Webhook-Events (für Channel-Notifications)';
```

**Indexes:**
```sql
CREATE INDEX idx_webhooks_connection ON webhooks(connection_id);
CREATE INDEX idx_webhooks_processed ON webhooks(processed, received_at);
CREATE INDEX idx_webhooks_event_id ON webhooks(event_source, event_id);
```

---

### 2.5 Pricing & Financials

#### 2.5.1 `pricing_rules`

Dynamische Preisregeln.

```sql
CREATE TABLE pricing_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,

  -- Rule Name
  name VARCHAR(255) NOT NULL,
  description TEXT,

  -- Date Range (NULL = immer gültig)
  valid_from DATE,
  valid_to DATE,

  -- Weekday (Bit-Mask: 1=Mo, 2=Di, 4=Mi, 8=Do, 16=Fr, 32=Sa, 64=So)
  weekday_mask INTEGER,

  -- Price Adjustment
  price_type VARCHAR(50) NOT NULL
    CHECK (price_type IN ('fixed', 'percentage', 'override')),
  price_adjustment DECIMAL(10,2) NOT NULL,

  -- Conditions
  min_stay INTEGER,
  max_stay INTEGER,
  min_guests INTEGER,
  max_guests INTEGER,

  -- Priority (höher = wichtiger)
  priority INTEGER DEFAULT 0,

  -- Status
  is_active BOOLEAN NOT NULL DEFAULT true,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE pricing_rules IS 'Dynamische Preisregeln (Saison, Wochentag, etc.)';
COMMENT ON COLUMN pricing_rules.weekday_mask IS 'Bit-Mask für Wochentage (1=Mo, 2=Di, ..., 64=So)';
```

**Indexes:**
```sql
CREATE INDEX idx_pricing_rules_property ON pricing_rules(property_id);
CREATE INDEX idx_pricing_rules_dates ON pricing_rules(valid_from, valid_to);
CREATE INDEX idx_pricing_rules_active ON pricing_rules(is_active) WHERE is_active = true;
```

#### 2.5.2 `invoices`

Rechnungen (für Agenturen, nicht Gäste!).

```sql
CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,

  -- Invoice Number (Auto-generiert)
  invoice_number VARCHAR(50) NOT NULL UNIQUE,

  -- Invoice Details
  invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
  due_date DATE NOT NULL,

  -- Status
  status VARCHAR(50) NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'sent', 'paid', 'overdue', 'cancelled')),

  -- Line Items
  line_items JSONB NOT NULL DEFAULT '[]'::jsonb,

  -- Amounts
  subtotal DECIMAL(10,2) NOT NULL,
  tax_amount DECIMAL(10,2) DEFAULT 0,
  total_amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) NOT NULL DEFAULT 'EUR',

  -- Payment
  paid_amount DECIMAL(10,2) DEFAULT 0,
  paid_at TIMESTAMPTZ,
  payment_method VARCHAR(50),

  -- Stripe Integration
  stripe_invoice_id VARCHAR(255),

  -- Notes
  notes TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE invoices IS 'Rechnungen (für Agenturen, NICHT Gäste!)';
COMMENT ON COLUMN invoices.invoice_number IS 'Auto-generiert (z.B. INV-2025-000001)';
```

**Indexes:**
```sql
CREATE INDEX idx_invoices_agency ON invoices(agency_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_invoices_stripe ON invoices(stripe_invoice_id) WHERE stripe_invoice_id IS NOT NULL;
```

#### 2.5.3 `payments`

Zahlungen (Tracking).

```sql
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,
  invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,

  -- Payment Details
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
  payment_method VARCHAR(50) NOT NULL
    CHECK (payment_method IN ('stripe', 'paypal', 'bank_transfer', 'cash', 'other')),

  -- Status
  status VARCHAR(50) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'refunded')),

  -- External IDs
  stripe_payment_intent_id VARCHAR(255),
  stripe_charge_id VARCHAR(255),

  -- Timestamps
  processed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE payments IS 'Zahlungen (Tracking für Agentur-Subscriptions)';
```

**Indexes:**
```sql
CREATE INDEX idx_payments_agency ON payments(agency_id);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_stripe ON payments(stripe_payment_intent_id) WHERE stripe_payment_intent_id IS NOT NULL;
```

---

### 2.6 Reports & Analytics

#### 2.6.1 `occupancy_reports`

Auslastungs-Reports (Materialized View).

```sql
CREATE MATERIALIZED VIEW occupancy_reports AS
SELECT
  p.id AS property_id,
  p.agency_id,
  DATE_TRUNC('month', b.check_in) AS month,
  COUNT(*) AS total_bookings,
  SUM(b.num_nights) AS total_nights,
  SUM(b.total_price) AS total_revenue,
  ROUND(SUM(b.num_nights)::DECIMAL / 30 * 100, 2) AS occupancy_rate
FROM bookings b
JOIN properties p ON p.id = b.property_id
WHERE b.status NOT IN ('cancelled', 'declined', 'no_show')
GROUP BY p.id, p.agency_id, DATE_TRUNC('month', b.check_in);

COMMENT ON MATERIALIZED VIEW occupancy_reports IS 'Auslastungs-Reports (monatlich, pro Property)';

-- Refresh täglich (via Cron-Job)
CREATE UNIQUE INDEX idx_occupancy_reports_unique ON occupancy_reports(property_id, month);
```

#### 2.6.2 `revenue_reports`

Umsatz-Reports (Materialized View).

```sql
CREATE MATERIALIZED VIEW revenue_reports AS
SELECT
  b.agency_id,
  b.property_id,
  b.source,
  DATE_TRUNC('month', b.check_in) AS month,
  COUNT(*) AS total_bookings,
  SUM(b.total_price) AS total_revenue,
  AVG(b.total_price) AS avg_booking_value,
  SUM(b.num_nights) AS total_nights
FROM bookings b
WHERE b.status NOT IN ('cancelled', 'declined', 'no_show')
  AND b.payment_status IN ('paid', 'partial')
GROUP BY b.agency_id, b.property_id, b.source, DATE_TRUNC('month', b.check_in);

COMMENT ON MATERIALIZED VIEW revenue_reports IS 'Umsatz-Reports (monatlich, pro Property & Source)';

-- Refresh täglich (via Cron-Job)
CREATE UNIQUE INDEX idx_revenue_reports_unique ON revenue_reports(agency_id, property_id, source, month);
```

---

## 3. Relationships & Foreign Keys

### 3.1 Entity-Relationship Diagram (ASCII)

```
┌──────────────────────────────────────────────────────────────────────┐
│                          MULTI-TENANCY                               │
└──────────────────────────────────────────────────────────────────────┘

agencies (1) ─────< team_members (N)
agencies (1) ─────< properties (N)
agencies (1) ─────< bookings (N)
agencies (1) ─────< guests (N)
agencies (1) ─────< channel_connections (N)
agencies (1) ─────< invoices (N)
agencies (1) ─────< payments (N)

┌──────────────────────────────────────────────────────────────────────┐
│                          AUTHENTICATION                              │
└──────────────────────────────────────────────────────────────────────┘

auth.users (1) ───< profiles (1)
auth.users (1) ───< team_members (N)
auth.users (1) ───< properties (N) [als owner_id]
auth.users (1) ───< guests (N) [optional, auth_user_id]

┌──────────────────────────────────────────────────────────────────────┐
│                          PROPERTIES                                  │
└──────────────────────────────────────────────────────────────────────┘

properties (1) ───< property_photos (N)
properties (1) ───< property_amenities (N)
properties (1) ───< bookings (N)
properties (1) ───< pricing_rules (N)

┌──────────────────────────────────────────────────────────────────────┐
│                          BOOKINGS                                    │
└──────────────────────────────────────────────────────────────────────┘

bookings (1) ───< direct_bookings (1)
bookings (1) ───< external_bookings (1)
guests (1) ───< bookings (N)

┌──────────────────────────────────────────────────────────────────────┐
│                          CHANNELS                                    │
└──────────────────────────────────────────────────────────────────────┘

channel_connections (1) ───< sync_logs (N)
channel_connections (1) ───< webhooks (N)
channel_connections (1) ───< external_bookings (N)

┌──────────────────────────────────────────────────────────────────────┐
│                          FINANCIALS                                  │
└──────────────────────────────────────────────────────────────────────┘

invoices (1) ───< payments (N)
```

### 3.2 Critical Foreign Key Constraints

**ON DELETE CASCADE:**
- `agencies` → alle abhängigen Tabellen (Multi-Tenancy Isolation)
- `properties` → `property_photos`, `property_amenities`
- `bookings` → `direct_bookings`, `external_bookings`

**ON DELETE RESTRICT:**
- `properties` → `bookings` (verhindert Löschen von Properties mit Buchungen)
- `guests` → `bookings` (verhindert Löschen von Gästen mit Buchungen)

**ON DELETE SET NULL:**
- `auth.users` → `guests.auth_user_id` (Gast bleibt auch ohne Account)
- `auth.users` → `properties.owner_id` (Property bleibt auch ohne Eigentümer)

---

## 4. RLS Policies (vollständig)

### 4.1 Multi-Tenancy (agency_id)

**Grundprinzip:** Benutzer sehen nur Daten ihrer eigenen Agentur.

**Alle Tabellen mit `agency_id`:**
- properties
- bookings
- guests
- team_members
- channel_connections
- sync_logs
- invoices
- payments
- pricing_rules

**Standard-Policy (Beispiel: properties):**

```sql
-- RLS aktivieren
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

-- Policy: agency_isolation_select
CREATE POLICY agency_isolation_select
ON properties
FOR SELECT
USING (
  agency_id = (auth.jwt() ->> 'agency_id')::uuid
);

-- Policy: agency_isolation_insert
CREATE POLICY agency_isolation_insert
ON properties
FOR INSERT
WITH CHECK (
  agency_id = (auth.jwt() ->> 'agency_id')::uuid
  AND (auth.jwt() ->> 'role') IN ('admin', 'manager')
);

-- Policy: agency_isolation_update
CREATE POLICY agency_isolation_update
ON properties
FOR UPDATE
USING (
  agency_id = (auth.jwt() ->> 'agency_id')::uuid
  AND (auth.jwt() ->> 'role') IN ('admin', 'manager')
)
WITH CHECK (
  agency_id = (auth.jwt() ->> 'agency_id')::uuid
);

-- Policy: agency_isolation_delete
CREATE POLICY agency_isolation_delete
ON properties
FOR DELETE
USING (
  agency_id = (auth.jwt() ->> 'agency_id')::uuid
  AND (auth.jwt() ->> 'role') = 'admin'
);
```

**WICHTIG:** Analog für alle anderen Tabellen mit `agency_id`.

---

### 4.2 Eigentümer-Isolation (owner_id)

**Grundprinzip:** Eigentümer sehen nur ihre eigenen Objekte.

**Tabellen mit `owner_id`:**
- properties
- bookings (via property_id JOIN)

**Policy für properties:**

```sql
-- Policy: owner_read_own_properties
CREATE POLICY owner_read_own_properties
ON properties
FOR SELECT
USING (
  -- Eigentümer sieht nur eigene Objekte
  (auth.jwt() ->> 'role' = 'owner' AND owner_id = auth.uid())
  OR
  -- Admin/Manager/Staff sehen alle Objekte ihrer Agentur
  (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff', 'accountant')
   AND agency_id = (auth.jwt() ->> 'agency_id')::uuid)
);

-- Eigentümer kann NICHTS bearbeiten (READ-ONLY)
-- Keine INSERT/UPDATE/DELETE Policies für Rolle "owner"
```

**Policy für bookings:**

```sql
-- Policy: owner_read_own_bookings
CREATE POLICY owner_read_own_bookings
ON bookings
FOR SELECT
USING (
  -- Eigentümer sieht nur Buchungen seiner Objekte
  (auth.jwt() ->> 'role' = 'owner'
   AND property_id IN (
     SELECT id FROM properties WHERE owner_id = auth.uid()
   ))
  OR
  -- Admin/Manager/Staff/Accountant sehen alle Buchungen ihrer Agentur
  (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff', 'accountant')
   AND agency_id = (auth.jwt() ->> 'agency_id')::uuid)
);

-- Eigentümer kann NICHTS bearbeiten (READ-ONLY)
-- Keine INSERT/UPDATE/DELETE Policies für Rolle "owner"
```

---

### 4.3 Rollenbasierte Policies

**Permissions-Matrix (aus Phase 11-13):**

| Feature | Admin | Manager | Staff | Owner | Accountant |
|---------|-------|---------|-------|-------|------------|
| Properties SELECT | ✅ | ✅ | ✅ (Read) | ✅ (nur eigene) | ❌ / Read |
| Properties INSERT | ✅ | ✅ | ❌ | ❌ | ❌ |
| Properties UPDATE | ✅ | ✅ | ❌ | ❌ | ❌ |
| Properties DELETE | ✅ | ✅ | ❌ | ❌ | ❌ |
| Bookings SELECT | ✅ | ✅ | ✅ | ✅ (nur eigene) | ✅ (nur Finanzen) |
| Bookings INSERT | ✅ | ✅ | ❌ | ❌ | ❌ |
| Bookings UPDATE | ✅ | ✅ | ✅ (nur Status) | ❌ | ❌ |
| Bookings DELETE | ✅ | ✅ | ❌ | ❌ | ❌ |
| Team SELECT | ✅ | ✅ (Read) | ❌ | ❌ | ❌ |
| Team INSERT/UPDATE/DELETE | ✅ | ❌ | ❌ | ❌ | ❌ |
| Channels SELECT | ✅ | ✅ (Read) | ❌ | ❌ | ❌ |
| Channels INSERT/UPDATE/DELETE | ✅ | ❌ | ❌ | ❌ | ❌ |
| Invoices SELECT | ✅ | ❌ | ❌ | ❌ | ✅ |
| Invoices INSERT/UPDATE/DELETE | ✅ | ❌ | ❌ | ❌ | ✅ |

**Beispiel: Vollständige RLS für bookings:**

```sql
-- 1. SELECT: Alle Rollen (mit Isolation)
CREATE POLICY bookings_select
ON bookings
FOR SELECT
USING (
  -- Eigentümer: nur Buchungen seiner Objekte
  (auth.jwt() ->> 'role' = 'owner'
   AND property_id IN (
     SELECT id FROM properties WHERE owner_id = auth.uid()
   ))
  OR
  -- Admin, Manager, Staff, Buchhalter: alle Buchungen ihrer Agentur
  (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff', 'accountant')
   AND agency_id = (auth.jwt() ->> 'agency_id')::uuid)
);

-- 2. INSERT: Nur Admin, Manager
CREATE POLICY bookings_insert
ON bookings
FOR INSERT
WITH CHECK (
  auth.jwt() ->> 'role' IN ('admin', 'manager')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);

-- 3. UPDATE: Admin, Manager (voller Zugriff), Staff (nur Status)
CREATE POLICY bookings_update_full
ON bookings
FOR UPDATE
USING (
  auth.jwt() ->> 'role' IN ('admin', 'manager')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
)
WITH CHECK (
  auth.jwt() ->> 'role' IN ('admin', 'manager')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);

CREATE POLICY bookings_update_status_only
ON bookings
FOR UPDATE
USING (
  auth.jwt() ->> 'role' = 'staff'
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
)
WITH CHECK (
  auth.jwt() ->> 'role' = 'staff'
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
  -- Zusätzliche Check: Nur Status-Spalte geändert (muss auf App-Ebene validiert werden)
);

-- 4. DELETE: Nur Admin, Manager
CREATE POLICY bookings_delete
ON bookings
FOR DELETE
USING (
  auth.jwt() ->> 'role' IN ('admin', 'manager')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);
```

---

### 4.4 Public Access (für Direct Booking Widget)

**Tabellen mit Public-Read:**
- properties (nur aktive)
- amenity_definitions (alle)
- property_photos (nur von aktiven Properties)

**Policy für properties (Public Read):**

```sql
-- Policy: public_read_active_properties
CREATE POLICY public_read_active_properties
ON properties
FOR SELECT
USING (
  -- Anon User kann nur aktive Properties sehen
  auth.role() = 'anon' AND is_active = true
);
```

**Policy für amenity_definitions (Public Read):**

```sql
-- Policy: public_read_amenities
CREATE POLICY public_read_amenities
ON amenity_definitions
FOR SELECT
USING (true); -- Alle können lesen
```

---

## 5. Indexes (Performance-optimiert)

### 5.1 Index-Strategie

**Grundregeln:**
1. **Primary Keys:** UUID (automatischer Index)
2. **Foreign Keys:** Immer indexieren (agency_id, property_id, etc.)
3. **Häufige WHERE-Klauseln:** Indexieren (status, check_in/check_out)
4. **Partial Indexes:** Für gefilterte Queries (WHERE is_active = true)
5. **Composite Indexes:** Für Multi-Column Queries
6. **GiST Indexes:** Für Geospatial (location) und Exclusion Constraints

### 5.2 Standard-Indexes

**Alle Foreign Keys:**
```sql
-- Properties
CREATE INDEX idx_properties_agency ON properties(agency_id);
CREATE INDEX idx_properties_owner ON properties(owner_id) WHERE owner_id IS NOT NULL;

-- Bookings
CREATE INDEX idx_bookings_agency ON bookings(agency_id);
CREATE INDEX idx_bookings_property ON bookings(property_id);
CREATE INDEX idx_bookings_guest ON bookings(guest_id);

-- Guests
CREATE INDEX idx_guests_agency ON guests(agency_id);
CREATE INDEX idx_guests_auth_user ON guests(auth_user_id) WHERE auth_user_id IS NOT NULL;

-- Team Members
CREATE INDEX idx_team_members_user_agency ON team_members(user_id, agency_id) WHERE is_active = true;
CREATE INDEX idx_team_members_agency ON team_members(agency_id) WHERE is_active = true;

-- Channel Connections
CREATE INDEX idx_channel_connections_agency ON channel_connections(agency_id);

-- Invoices
CREATE INDEX idx_invoices_agency ON invoices(agency_id);

-- Payments
CREATE INDEX idx_payments_agency ON payments(agency_id);
```

### 5.3 Query-optimierte Indexes

**Booking-Suche (häufigste Query):**
```sql
-- Suche nach Datum-Bereich
CREATE INDEX idx_bookings_dates ON bookings(check_in, check_out);

-- Suche nach Property + Datum (für Verfügbarkeits-Check)
CREATE INDEX idx_bookings_property_dates ON bookings(property_id, check_in, check_out);

-- Suche nach Status
CREATE INDEX idx_bookings_status ON bookings(status);

-- Suche nach Source
CREATE INDEX idx_bookings_source ON bookings(source);
```

**Property-Suche:**
```sql
-- Suche nach Stadt
CREATE INDEX idx_properties_city ON properties(city);

-- Suche nach Aktiv-Status
CREATE INDEX idx_properties_active ON properties(is_active) WHERE is_active = true;

-- Geospatial-Suche
CREATE INDEX idx_properties_location ON properties USING GIST(location);
```

**Sync-Log-Queries:**
```sql
-- Letzte Sync-Logs pro Connection
CREATE INDEX idx_sync_logs_connection ON sync_logs(connection_id, created_at DESC);

-- Sync-Status
CREATE INDEX idx_sync_logs_status ON sync_logs(status);
```

### 5.4 Partial Indexes (für häufige Filters)

```sql
-- Nur aktive Properties
CREATE INDEX idx_properties_active ON properties(is_active) WHERE is_active = true;

-- Nur aktive Team-Members
CREATE INDEX idx_team_members_user_agency ON team_members(user_id, agency_id) WHERE is_active = true;

-- Nur aktive Channel-Connections
CREATE INDEX idx_channel_connections_active ON channel_connections(is_active) WHERE is_active = true;

-- Nur unverarbeitete Webhooks
CREATE INDEX idx_webhooks_unprocessed ON webhooks(received_at) WHERE processed = false;
```

---

## 6. Triggers & Functions

### 6.1 Auto-Update `updated_at`

**Function:**
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Trigger (auf allen Tabellen mit `updated_at`):**
```sql
CREATE TRIGGER update_properties_updated_at
  BEFORE UPDATE ON properties
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bookings_updated_at
  BEFORE UPDATE ON bookings
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Analog für alle anderen Tabellen mit updated_at
```

### 6.2 Auto-Generate `booking_reference`

**Function:**
```sql
CREATE OR REPLACE FUNCTION generate_booking_reference()
RETURNS TEXT AS $$
DECLARE
  year_suffix TEXT;
  sequence_num TEXT;
BEGIN
  year_suffix := TO_CHAR(CURRENT_DATE, 'YYYY');

  -- Hole nächste Sequence-Nummer für dieses Jahr
  SELECT LPAD((COUNT(*) + 1)::TEXT, 6, '0')
  INTO sequence_num
  FROM bookings
  WHERE EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM CURRENT_DATE);

  RETURN 'PMS-' || year_suffix || '-' || sequence_num;
END;
$$ LANGUAGE plpgsql;
```

**Trigger:**
```sql
CREATE OR REPLACE FUNCTION auto_generate_booking_reference()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.booking_reference IS NULL OR NEW.booking_reference = '' THEN
    NEW.booking_reference := generate_booking_reference();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_booking_reference
  BEFORE INSERT ON bookings
  FOR EACH ROW
  EXECUTE FUNCTION auto_generate_booking_reference();
```

### 6.3 Auto-Generate `invoice_number`

**Function:**
```sql
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS TEXT AS $$
DECLARE
  year_suffix TEXT;
  sequence_num TEXT;
BEGIN
  year_suffix := TO_CHAR(CURRENT_DATE, 'YYYY');

  SELECT LPAD((COUNT(*) + 1)::TEXT, 6, '0')
  INTO sequence_num
  FROM invoices
  WHERE EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM CURRENT_DATE);

  RETURN 'INV-' || year_suffix || '-' || sequence_num;
END;
$$ LANGUAGE plpgsql;
```

**Trigger:**
```sql
CREATE OR REPLACE FUNCTION auto_generate_invoice_number()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.invoice_number IS NULL OR NEW.invoice_number = '' THEN
    NEW.invoice_number := generate_invoice_number();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_invoice_number
  BEFORE INSERT ON invoices
  FOR EACH ROW
  EXECUTE FUNCTION auto_generate_invoice_number();
```

### 6.4 Update Guest Statistics

**Function:**
```sql
CREATE OR REPLACE FUNCTION update_guest_statistics()
RETURNS TRIGGER AS $$
BEGIN
  -- Update total_bookings, total_spent, first/last booking dates
  UPDATE guests
  SET
    total_bookings = (
      SELECT COUNT(*)
      FROM bookings
      WHERE guest_id = NEW.guest_id
        AND status NOT IN ('cancelled', 'declined', 'no_show')
    ),
    total_spent = (
      SELECT COALESCE(SUM(total_price), 0)
      FROM bookings
      WHERE guest_id = NEW.guest_id
        AND payment_status = 'paid'
    ),
    first_booking_at = (
      SELECT MIN(created_at)
      FROM bookings
      WHERE guest_id = NEW.guest_id
    ),
    last_booking_at = (
      SELECT MAX(created_at)
      FROM bookings
      WHERE guest_id = NEW.guest_id
    )
  WHERE id = NEW.guest_id;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Trigger:**
```sql
CREATE TRIGGER update_guest_stats_on_booking
  AFTER INSERT OR UPDATE ON bookings
  FOR EACH ROW
  EXECUTE FUNCTION update_guest_statistics();
```

---

## 7. Migrations-Strategie

### 7.1 Supabase Migrations

**Ordner-Struktur:**
```
supabase/migrations/
  20250101000001_initial_schema.sql
  20250101000002_rls_policies.sql
  20250101000003_indexes.sql
  20250101000004_functions_triggers.sql
  20250102000001_add_direct_bookings.sql
```

**Naming-Convention:**
- Format: `YYYYMMDDHHMMSS_description.sql`
- Sortierung: Chronologisch (älteste zuerst)
- Ein File = eine logische Änderung

### 7.2 Migration-Best-Practices

**1. Idempotenz:**
```sql
-- Gut: CREATE IF NOT EXISTS
CREATE TABLE IF NOT EXISTS properties (...);
CREATE INDEX IF NOT EXISTS idx_properties_agency ON properties(agency_id);

-- Gut: DROP IF EXISTS (für Rollback)
DROP TABLE IF EXISTS old_table;
```

**2. Rollback-Fähigkeit:**
```sql
-- Migration: 20250101000001_add_column.sql
ALTER TABLE properties ADD COLUMN IF NOT EXISTS new_column TEXT;

-- Rollback (manuell):
-- ALTER TABLE properties DROP COLUMN IF EXISTS new_column;
```

**3. Data-Migration (in Transaktionen):**
```sql
BEGIN;

-- Schema-Änderung
ALTER TABLE bookings ADD COLUMN new_status VARCHAR(50);

-- Daten migrieren
UPDATE bookings SET new_status = old_status WHERE old_status IS NOT NULL;

-- Alte Spalte löschen
ALTER TABLE bookings DROP COLUMN old_status;

-- Neue Spalte umbenennen
ALTER TABLE bookings RENAME COLUMN new_status TO status;

COMMIT;
```

**4. Extensions aktivieren:**
```sql
-- Immer zuerst Extensions aktivieren
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### 7.3 Deployment-Prozess

**Lokal testen:**
```bash
# Supabase CLI starten
supabase start

# Migration erstellen
supabase migration new add_feature_x

# Migration anwenden
supabase db push

# Migration verifizieren
supabase db remote status
```

**Auf Production deployen:**
```bash
# Mit Production-Projekt verbinden
supabase link --project-ref your-prod-ref

# Migrations anwenden
supabase db push

# Verifizieren
supabase migration list
```

---

## 8. Anhang

### A. Complete Schema Script

**Vollständiges SQL-Script zum Erstellen aller Tabellen:**

Siehe separate Datei: `supabase/migrations/20251221000001_initial_schema.sql`

(Bereits vorhanden in: `/Users/khaled/Documents/KI/Claude/Claude Code/Projekte/PMS-Webapp/supabase/migrations/`)

### B. Seed Data

**Beispiel-Daten für Development/Testing:**

```sql
-- Seed: Agencies
INSERT INTO agencies (id, name, email, company_name) VALUES
('11111111-1111-1111-1111-111111111111', 'Küstenvermietung Nord', 'info@kueste-nord.de', 'Küstenvermietung Nord GmbH'),
('22222222-2222-2222-2222-222222222222', 'Alpen-Lodges', 'info@alpen-lodges.de', 'Alpen-Lodges GmbH');

-- Seed: Properties (5 pro Agency)
INSERT INTO properties (agency_id, name, property_type, bedrooms, bathrooms, max_guests, city, address_line1, postal_code, base_price) VALUES
('11111111-1111-1111-1111-111111111111', 'Beach Villa', 'villa', 4, 2.0, 8, 'Sylt', 'Strandweg 12', '25980', 120.00),
('11111111-1111-1111-1111-111111111111', 'Ocean View Apartment', 'apartment', 2, 1.0, 4, 'Sylt', 'Meerstraße 5', '25980', 80.00),
('22222222-2222-2222-2222-222222222222', 'Mountain Cabin', 'cabin', 3, 1.5, 6, 'Garmisch', 'Bergweg 3', '82467', 100.00);

-- Seed: Team Members (3 pro Agency)
-- Hinweis: auth.users müssen bereits existieren
INSERT INTO team_members (user_id, agency_id, role) VALUES
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'admin'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '11111111-1111-1111-1111-111111111111', 'manager'),
('cccccccc-cccc-cccc-cccc-cccccccccccc', '22222222-2222-2222-2222-222222222222', 'admin');

-- Seed: Amenity Definitions
INSERT INTO amenity_definitions (code, name_en, name_de, category, display_order) VALUES
('wifi', 'WiFi', 'WLAN', 'essentials', 1),
('kitchen', 'Kitchen', 'Küche', 'essentials', 2),
('parking', 'Free parking', 'Kostenloser Parkplatz', 'features', 10),
('pool', 'Pool', 'Pool', 'features', 11),
('air_conditioning', 'Air conditioning', 'Klimaanlage', 'features', 3),
('heating', 'Heating', 'Heizung', 'essentials', 4);
```

### C. Testing RLS

**Test-Queries zum Verifizieren der RLS Policies:**

```sql
-- Test 1: Tenant-Isolation
-- User A (Agency 1) sollte nur Properties von Agency 1 sehen

-- Simuliere User A (Admin, Agency 1)
SET request.jwt.claims = '{"sub": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "agency_id": "11111111-1111-1111-1111-111111111111", "role": "admin"}';
SELECT * FROM properties; -- Sollte nur Properties von Agency 1 zurückgeben

-- Simuliere User B (Admin, Agency 2)
SET request.jwt.claims = '{"sub": "cccccccc-cccc-cccc-cccc-cccccccccccc", "agency_id": "22222222-2222-2222-2222-222222222222", "role": "admin"}';
SELECT * FROM properties; -- Sollte nur Properties von Agency 2 zurückgeben

-- Test 2: Rollen-basierte Berechtigungen
-- Manager kann Properties lesen/bearbeiten, aber nicht löschen

SET request.jwt.claims = '{"sub": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "agency_id": "11111111-1111-1111-1111-111111111111", "role": "manager"}';

-- Sollte funktionieren:
SELECT * FROM properties WHERE agency_id = '11111111-1111-1111-1111-111111111111';
UPDATE properties SET name = 'Updated Name' WHERE id = '...';

-- Sollte fehlschlagen:
DELETE FROM properties WHERE id = '...'; -- ERROR: permission denied

-- Test 3: Eigentümer-Isolation
-- Eigentümer sieht nur eigene Properties

-- Simuliere Eigentümer (owner_id = auth.uid())
SET request.jwt.claims = '{"sub": "dddddddd-dddd-dddd-dddd-dddddddddddd", "agency_id": "11111111-1111-1111-1111-111111111111", "role": "owner"}';

-- Setze owner_id für Test-Property
UPDATE properties SET owner_id = 'dddddddd-dddd-dddd-dddd-dddddddddddd' WHERE id = '...';

-- Sollte nur dieses Property zurückgeben:
SELECT * FROM properties; -- Nur Properties mit owner_id = 'dddddddd-...'

-- Sollte fehlschlagen (READ-ONLY):
UPDATE properties SET name = 'New Name' WHERE id = '...'; -- ERROR: permission denied
```

### D. Performance-Monitoring

**Langsame Queries identifizieren:**

```sql
-- Aktiviere Query-Logging (Supabase Dashboard → Database → Settings)
ALTER DATABASE postgres SET log_min_duration_statement = 1000; -- 1 Sekunde

-- Analyse: Langsame Queries
SELECT
  query,
  calls,
  total_time,
  mean_time,
  max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

**Index-Usage überwachen:**

```sql
-- Welche Indexes werden nicht genutzt?
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan AS index_scans
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE 'pg_toast%'
ORDER BY schemaname, tablename;
```

**Tabellen-Größen überwachen:**

```sql
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 9. Zusammenfassung

### 9.1 Wichtigste Tabellen

**Core:**
- `agencies` (Root-Entity, Multi-Tenancy)
- `team_members` (User-Agency-Mapping, Rollen)
- `properties` (Objekte)
- `bookings` (Source of Truth)
- `guests` (Gäste)

**Channels:**
- `channel_connections` (OAuth)
- `sync_logs` (Sync-Historie)
- `external_bookings` (iCal Import)

**Direct Booking:**
- `direct_bookings` (Website-Bookings)

**Financials:**
- `invoices` (Agentur-Rechnungen)
- `payments` (Zahlungen)
- `pricing_rules` (Dynamische Preise)

**Reports:**
- `occupancy_reports` (Materialized View)
- `revenue_reports` (Materialized View)

### 9.2 Wichtigste RLS-Konzepte

1. **Multi-Tenancy:** `agency_id` überall, User sieht nur eigene Agentur
2. **Eigentümer-Isolation:** `owner_id` auf Properties, READ-ONLY für Owner-Rolle
3. **Rollenbasiert:** 5 Rollen (Admin, Manager, Staff, Owner, Accountant)
4. **JWT-Claims:** `agency_id`, `role` im JWT für RLS-Policies

### 9.3 Wichtigste Performance-Features

1. **Indexes:** Alle Foreign Keys, häufige WHERE-Klauseln, Composite Indexes
2. **Partial Indexes:** Für gefilterte Queries (is_active = true)
3. **GiST Indexes:** Für Geospatial (location) und Exclusion Constraints
4. **Materialized Views:** Für Reports (täglich refreshen)
5. **Triggers:** Auto-update updated_at, Auto-generate References

### 9.4 Nächste Schritte

**Phase 18: Backend-Implementierung**
1. Supabase-Integration (Supabase Client)
2. API-Endpoints (Next.js API Routes)
3. RLS-Testing (mit echten Benutzern)

**Phase 19: Frontend-Implementierung**
1. Supabase Auth-Integration
2. RBAC-UI (Rollen-basierte Navigation)
3. Dashboard pro Rolle

**Phase 20: Channel-Integration**
1. Airbnb OAuth-Flow
2. iCal Import/Export
3. Sync-Engine (Background Jobs)

---

**Ende des Dokuments.**
