# Phase 8: PRD / Pflichtenheft (MVP-Light)

**Status:** Draft
**Version:** 1.0
**Erstellt:** 2025-12-21
**Projekt:** PMS-Webapp

---

## Executive Summary

### Vision
**All-in-One Property Management System (PMS)** für Ferienwohnungen mit integriertem Channel Manager zur Vermeidung von Doppelbuchungen durch bidirektionale Echtzeit-Synchronisation.

### Target Users
- **Vermieter** (Vacation Rental Owners): 1-10 Objekte, Self-Service
- **Property Manager**: 10-100 Objekte, Team-Management
- **Staff**: Housekeeping, Maintenance, Check-in

### MVP Definition (One-Liner)
> **Funktionierendes PMS mit Direct Booking Engine + Airbnb Channel Manager, das Doppelbuchungen verhindert und grundlegende Property/Booking Management Features bietet.**

---

## 1. Scope & Non-Goals

### 1.1 In Scope (MVP)

#### Core Features
- ✅ **Direct Booking Engine** (gleichwertig zu Channel Bookings)
  - Property Search & Availability
  - Guest Checkout (optional Guest Account)
  - Stripe Payment Integration
  - Email Confirmations
- ✅ **Channel Manager** (Airbnb als Referenz-Implementierung)
  - OAuth-basierte Channel Connection
  - Bidirektionale Synchronisation (Availability, Pricing, Bookings)
  - Webhook-basierte Echtzeit-Updates
  - Idempotente Sync-Logik
- ✅ **Property Management**
  - Property CRUD (Name, Address, Photos, Amenities)
  - Room/Unit Management
  - Property-Status (active, inactive)
- ✅ **Booking Management**
  - Booking Lifecycle (Reserved → Confirmed → Checked-in → Checked-out)
  - Booking Source Tracking (direct, airbnb, booking_com, etc.)
  - Guest Information Management
  - Cancellation & Refund Handling
- ✅ **Availability & Pricing**
  - Calendar Management (blocked dates, available dates)
  - Base Pricing + Seasonal Rules
  - Dynamic Pricing (optional)
  - Minimum Stay Rules
- ✅ **Multi-Tenancy & Roles**
  - Row-Level Security (RLS) via Supabase
  - 4 Rollen: Owner, Manager, Staff, Viewer
  - Tenant Isolation (tenant_id)

#### Technical Infrastructure
- ✅ **Backend:** FastAPI (Python), Supabase (PostgreSQL + RLS + Auth)
- ✅ **Frontend:** Next.js 14+ (App Router), TanStack Query, Zustand
- ✅ **Sync Engine:** Celery (async tasks), Redis (cache, rate limiting, idempotency)
- ✅ **Observability:** Prometheus Metrics, Logging, Tracing Hooks
- ✅ **Security:** OAuth Token Encryption, Webhook Signature Verification, RLS

### 1.2 Out of Scope (Post-MVP Roadmap)

#### Weitere Channels
- Booking.com, Expedia, FeWo-direkt, Google Vacation Rentals
- (Struktur vorhanden, Adapter-Implementierung fehlt)

#### Advanced Features
- Revenue Management & Analytics Dashboard
- Smart Pricing Algorithms (Competitor-based)
- Housekeeping & Maintenance Workflows
- Guest Communication (Messaging, SMS, WhatsApp)
- Owner Reporting (Financial Statements, Occupancy Reports)
- Mobile Apps (iOS, Android)

#### Guest Portal (Optional)
- Self-Service Guest Portal (Booking History, Invoices, Support Tickets)
- Guest Reviews & Ratings

### 1.3 Explicit Non-Goals (für MVP)

❌ **UI/UX Polish** (kommt in separatem Phase)
- Professionelles Design System
- Custom Illustrations & Icons
- Animationen & Transitions
- Responsive Design Optimization

❌ **Advanced Integrations**
- Smart Lock Integrations (Nuki, August, etc.)
- POS Systems
- Accounting Software (QuickBooks, Xero)

❌ **Enterprise Features**
- SSO (SAML, LDAP)
- White-Label Branding
- API für Drittanbieter

---

## 2. User Roles & Permissions

### 2.1 Rollen-Hierarchie

| Rolle | Beschreibung | Permissions |
|-------|--------------|-------------|
| **Owner** | Property Owner (Vollzugriff) | Create/Read/Update/Delete: Properties, Bookings, Channels, Users, Settings |
| **Manager** | Property Manager (Verwaltung) | Create/Read/Update: Properties, Bookings, Channels, Users (read-only Settings) |
| **Staff** | Housekeeping/Maintenance | Read: Properties, Bookings (upcoming), Update: Booking Status (Checked-in/out) |
| **Viewer** | Read-Only (Reports, Analytics) | Read-Only: Properties, Bookings, Reports |

### 2.2 Rollen-Details

#### Owner (Full Access)
**Use Case:** Vermieter mit 1-10 Objekten, vollständige Kontrolle über alle Aspekte

**Permissions:**
- ✅ Create, Edit, Delete Properties
- ✅ Manage Bookings (all statuses, all sources)
- ✅ Connect/Disconnect Channels (OAuth)
- ✅ Manage Pricing & Availability
- ✅ Invite/Remove Team Members (Manager, Staff, Viewer)
- ✅ Access Financial Reports
- ✅ Configure Settings (Payment, Notifications, Integrations)

**Typical User Journey:**
1. Onboarding: Create Properties, Upload Photos, Set Pricing
2. Channel Setup: Connect Airbnb via OAuth
3. Team Management: Invite Manager/Staff
4. Daily Operations: Monitor Bookings, Respond to Inquiries

#### Manager (Property Management)
**Use Case:** Angestellter Property Manager, verwaltet Objekte im Auftrag

**Permissions:**
- ✅ Create, Edit Properties (cannot delete)
- ✅ Manage Bookings (create, update, cancel)
- ✅ View Channel Connections (cannot connect/disconnect)
- ✅ Update Pricing & Availability
- ✅ View Team Members (cannot invite/remove)
- ❌ Cannot access Financial Settings
- ❌ Cannot configure Payment Settings

**Typical User Journey:**
1. Daily: Check new bookings from channels
2. Operations: Update availability, adjust pricing
3. Guest Communication: Respond to inquiries
4. Reporting: View occupancy, bookings by source

#### Staff (Operational)
**Use Case:** Housekeeping, Maintenance, Check-in Staff

**Permissions:**
- ✅ View Properties (read-only)
- ✅ View Upcoming Bookings (next 7 days)
- ✅ Update Booking Status (Checked-in, Checked-out)
- ✅ View Guest Contact Information (for check-in)
- ❌ Cannot create/edit bookings
- ❌ Cannot access pricing/financial data
- ❌ Cannot manage channels

**Typical User Journey:**
1. Morning: View today's check-ins/check-outs
2. Cleaning: Mark units as ready after cleaning
3. Check-in: Update booking status when guest arrives

#### Viewer (Read-Only)
**Use Case:** Accountant, Analyst, externe Berater

**Permissions:**
- ✅ View Properties (read-only)
- ✅ View Bookings (all statuses, all dates)
- ✅ View Financial Reports
- ✅ Export Data (CSV, PDF)
- ❌ Cannot create/edit anything
- ❌ Cannot access settings

**Typical User Journey:**
1. Monthly: Export booking data for accounting
2. Analysis: View occupancy trends
3. Reporting: Generate revenue reports

### 2.3 Guest Portal (Optional, Post-MVP)

**Status:** ⚠️ Optional Feature (nicht Teil des MVP)

**Use Case:** Self-Service für Gäste

**Permissions (wenn implementiert):**
- ✅ View Own Bookings (past & upcoming)
- ✅ Download Invoices
- ✅ Submit Support Requests
- ✅ Leave Reviews
- ❌ Cannot view other guests' data

---

## 3. MVP Features (Detailliert)

### 3.1 Direct Booking Engine

**Status:** ✅ Vollständig designt (Phase 3), Backend implementiert

**Gleichwertigkeit zu Channel Bookings:**
- Beide Buchungsquellen nutzen dieselbe `bookings`-Tabelle
- Gleiches Booking Lifecycle (Reserved → Confirmed → ...)
- Gleiche Availability-Update-Logik
- Gleiche Event-Triggers für Sync Engine

**User Flow (5 Steps):**

1. **Search & Filter**
   - Input: Location, Check-in, Check-out, Guests
   - Output: Available Properties (Real-Time Availability Check)

2. **Property Detail & Booking**
   - Property Photos, Description, Amenities
   - Price Calculation (Base + Seasonal Rules + Length-of-Stay)
   - "Book Now" → Creates Booking (status='reserved', expires in 30 min)

3. **Guest Information**
   - Name, Email, Phone
   - Optional: Create Guest Account (Supabase Magic Link)
   - Terms & Conditions Acceptance

4. **Payment (Stripe)**
   - PaymentIntent API (not Checkout Session)
   - 3D Secure (SCA Compliance)
   - Status: payment_status='pending'

5. **Confirmation**
   - Webhook: payment_intent.succeeded → status='confirmed', payment_status='paid'
   - Email: Booking Confirmation + Calendar Invite
   - Event: booking.confirmed → Triggers Channel Sync

**Edge Cases Covered:**
- Payment Timeout (30 min) → Auto-Cancel + Email
- Payment Failure (3 Retries) → Cancel + Redirect
- Race Condition → Database Exclusion Constraint
- Webhook Idempotency → Redis Cache (24h)
- Guest Closes Browser → Email mit Payment-Link

**Acceptance Criteria:**
- [ ] Guest kann Property suchen und verfügbare Objekte sehen
- [ ] Guest kann buchen (mit/ohne Account)
- [ ] Payment erfolgt via Stripe PaymentIntents
- [ ] Booking wird nach Payment confirmed
- [ ] Confirmation Email wird gesendet
- [ ] Booking erscheint in Owner Dashboard
- [ ] Availability wird automatisch aktualisiert
- [ ] Channel Sync wird getriggert (booking.confirmed event)

### 3.2 Channel Manager (Airbnb als Referenz)

**Status:** ✅ Vollständig implementiert (Phase 4)

**Scope:**
- ✅ **Airbnb:** Vollständiger Adapter (OAuth, Sync, Webhooks)
- ⚠️ **Weitere Channels:** Struktur vorhanden, Implementierung Post-MVP
  - booking_com, expedia, fewo_direkt, google (Ordner existieren, Adapter fehlt)

**Airbnb Features:**

1. **OAuth Connection**
   - Flow: Redirect → Airbnb Auth → Callback → Store Encrypted Tokens
   - UI: "Connect Airbnb" Button → OAuth Flow
   - Backend: `POST /api/channel-connections` (speichert access_token_encrypted)

2. **Bidirektionale Synchronisation**

   **Outbound (PMS → Airbnb):**
   - Availability Update: `update_availability()` API Call
   - Pricing Update: `update_pricing()` API Call
   - Booking Block: Create/Cancel Bookings on Airbnb
   - Trigger: Event-Driven (booking.confirmed event → Celery Task)

   **Inbound (Airbnb → PMS):**
   - Webhook: `POST /webhooks/airbnb` (reservation.created, reservation.updated, etc.)
   - Signature Verification: HMAC-SHA256 (constant-time comparison)
   - Import: Create Booking in PMS (source='airbnb')
   - Idempotency: Redis Cache (24h TTL)

3. **Resilienz**
   - Rate Limiting: Redis-based (100 req/min pro Kanal)
   - Circuit Breaker: Auto-Disable nach 5 Failures (5-min cooldown)
   - Retry Logic: Exponential Backoff (3 attempts)
   - Distributed Locks: Redis Lock (5-min TTL) verhindert Race Conditions

4. **Observability**
   - Prometheus Metrics: 30+ Metriken (sync_success, sync_failure, rate_limit_hits, etc.)
   - Logging: Structured Logs (JSON) für alle Sync-Operationen
   - Tracing: Hooks für OpenTelemetry

**Acceptance Criteria:**
- [ ] Owner kann Airbnb-Account verbinden (OAuth)
- [ ] Verfügbarkeit wird von PMS zu Airbnb synchronisiert
- [ ] Preise werden von PMS zu Airbnb synchronisiert
- [ ] Airbnb-Buchungen werden in PMS importiert (Webhook)
- [ ] Doppelbuchungen werden verhindert (Redis Lock + DB Constraint)
- [ ] Sync-Fehler werden geloggt und gecountert
- [ ] Rate Limits werden eingehalten
- [ ] Circuit Breaker aktiviert bei wiederholten Fehlern

### 3.3 Property Management

**Features:**
- CRUD Operations: Create, Read, Update, Delete Properties
- Property Fields:
  - Basic: Name, Address, Property Type (Apartment, House, Villa)
  - Details: Bedrooms, Bathrooms, Max Guests, Size (sqm)
  - Amenities: WiFi, Kitchen, Parking, Pool, etc. (Multi-Select)
  - Photos: Upload (max 20), Reorder, Delete
  - Status: Active, Inactive (soft delete)

**Acceptance Criteria:**
- [ ] Owner kann neue Property anlegen
- [ ] Owner kann Property-Details bearbeiten
- [ ] Owner kann Fotos hochladen und ordnen
- [ ] Owner kann Property deaktivieren (soft delete)
- [ ] Multi-Tenancy: Owner sieht nur eigene Properties (RLS)

### 3.4 Booking Management

**Booking Lifecycle:**
```
Reserved → Confirmed → Checked-in → Checked-out
    ↓           ↓            ↓            ↓
Cancelled  Cancelled    No-Show      Complete
```

**Features:**
- Booking List: Filterable by Status, Source, Date Range
- Booking Detail: Guest Info, Property, Pricing Breakdown, Payment Status
- Actions:
  - Cancel Booking (mit Refund-Logik, wenn innerhalb Cancellation Policy)
  - Update Status (Check-in, Check-out)
  - Send Email (Confirmation, Reminder, Custom Message)
- Guest Management:
  - Guest CRUD (Name, Email, Phone, Notes)
  - Guest History (alle Buchungen eines Gasts)

**Acceptance Criteria:**
- [ ] Owner sieht alle Bookings (filterable)
- [ ] Owner kann Booking canceln (mit Refund)
- [ ] Staff kann Check-in/Check-out Status updaten
- [ ] Guest Info ist vollständig (Name, Email, Phone)
- [ ] Multi-Tenancy: Owner sieht nur eigene Bookings (RLS)

### 3.5 Availability & Pricing

**Availability Management:**
- Calendar View: 12-Monats-Ansicht
- Actions:
  - Block Dates (Owner Block, Maintenance)
  - Unblock Dates
  - Import iCal (für externe Kalender)
- Auto-Update: Nach Booking (Check-in → Check-out werden blocked)

**Pricing Management:**
- Base Price: Nightly Rate (default)
- Seasonal Pricing: Date Ranges mit Custom Rates (z.B. Summer: +20%)
- Length-of-Stay Discounts: Weekly Discount (-10%), Monthly Discount (-20%)
- Minimum Stay Rules: Min 2 Nights (Weekend), Min 7 Nights (Peak Season)

**Acceptance Criteria:**
- [ ] Owner kann Dates im Kalender blocken/unblocken
- [ ] Owner kann Base Price setzen
- [ ] Owner kann Seasonal Pricing Rules erstellen
- [ ] Owner kann Minimum Stay Rules setzen
- [ ] Pricing wird korrekt berechnet (Base + Seasonal + Discounts)
- [ ] Availability wird nach Booking automatisch aktualisiert

### 3.6 Sync Engine

**Architektur:**
```
PMS-Core (Source of Truth)
    ↓ Events (booking.created, availability.updated)
Event Queue (Celery)
    ↓ Async Tasks
Channel Manager Sync
    ↓ API Calls (Rate-Limited, Circuit-Breaker)
External Platforms (Airbnb, Booking.com, etc.)

External Platforms
    ↓ Webhooks (signed)
Webhook Handler (signature verification, idempotency)
    ↓ Import
PMS-Core (validate, store, emit events)
```

**Core Principles:**
1. **Source of Truth:** PMS-Core ist master, Channels sind replicas
2. **Event-Driven:** Alle Sync-Operationen getriggert durch Events
3. **Idempotent:** Alle Operationen können mehrfach ausgeführt werden (Redis Cache)
4. **Resilient:** Rate Limiting, Circuit Breaker, Retry Logic

**Acceptance Criteria:**
- [ ] PMS-Core Events triggern Channel Sync (Celery Tasks)
- [ ] Channel Webhooks werden verarbeitet (signature verified)
- [ ] Idempotenz garantiert (keine Duplicate Bookings)
- [ ] Rate Limits werden eingehalten (100 req/min)
- [ ] Circuit Breaker aktiviert bei Failures (5 Failures → 5 min cooldown)
- [ ] Sync-Logs werden geschrieben (Prometheus Metrics)

---

## 4. Phasenplan (Implementation Roadmap)

### Phase 1: Foundation ✅ (COMPLETED)
**Timeline:** Abgeschlossen (Phases 1-7)

**Deliverables:**
- ✅ System Architecture (C4 Diagrams, ADRs)
- ✅ Tech Stack (FastAPI, Supabase, Next.js)
- ✅ Database Schema (Migrations, RLS Policies)
- ✅ Backend APIs (50+ Endpoints, OpenAPI Spec)
- ✅ Supabase RLS (Multi-Tenancy, Row-Level Security)
- ✅ Security Fixes (Redis, Webhook Signature, Token Encryption)

**Status:** ✅ Vollständig abgeschlossen

---

### Phase 2: Direct Booking Engine (MVP Core)
**Timeline:** 4-6 Wochen

**Deliverables:**

**Frontend (Next.js):**
- [ ] Property Search & Filter Component
- [ ] Property Detail Page
- [ ] Booking Flow (5 Steps)
- [ ] Stripe Payment Integration (Stripe Elements)
- [ ] Confirmation Page

**Backend (FastAPI):**
- [ ] Availability Check API (real-time)
- [ ] Booking Creation API (with validation)
- [ ] Stripe Webhook Handler (payment_intent.succeeded)
- [ ] Email Service (Confirmation, Reminder)
- [ ] Celery Task: Auto-Cancel Expired Bookings (30 min timeout)

**Acceptance Criteria:**
- [ ] End-to-End Booking Flow funktioniert
- [ ] Payment via Stripe funktioniert (3DS)
- [ ] Booking wird nach Payment confirmed
- [ ] Email wird gesendet
- [ ] Availability wird aktualisiert
- [ ] Edge Cases gehandelt (Timeout, Payment Failure, Race Condition)

---

### Phase 3: Channel Manager (Airbnb MVP)
**Timeline:** 4-6 Wochen

**Deliverables:**

**Frontend:**
- [ ] Channel Connection UI ("Connect Airbnb" Button)
- [ ] OAuth Callback Handler
- [ ] Channel Connection Status Dashboard
- [ ] Manual Sync Trigger Button

**Backend:**
- [ ] Airbnb Adapter vollständig (DONE ✅, aber Test-Coverage fehlt)
- [ ] Channel Connection API (OAuth, CRUD)
- [ ] Webhook Handler (Airbnb) (DONE ✅, aber Integration Test fehlt)
- [ ] Sync Engine (Celery Tasks) (DONE ✅)
- [ ] Rate Limiter, Circuit Breaker (DONE ✅)

**Testing:**
- [ ] Unit Tests: Airbnb Adapter (100% Coverage)
- [ ] Integration Tests: OAuth Flow, Webhook Processing
- [ ] E2E Tests: End-to-End Sync (PMS → Airbnb → PMS)

**Acceptance Criteria:**
- [ ] Owner kann Airbnb verbinden (OAuth)
- [ ] Sync funktioniert bidirektional
- [ ] Doppelbuchungen werden verhindert
- [ ] Rate Limits funktionieren
- [ ] Circuit Breaker aktiviert bei Failures
- [ ] Metrics werden geloggt

---

### Phase 4: Multi-Tenant & Roles
**Timeline:** 2-3 Wochen

**Deliverables:**

**Backend:**
- [ ] RLS Policies für alle Tabellen (DONE ✅, aber Verification fehlt)
- [ ] User Management API (Invite, Remove, Update Roles)
- [ ] Permission Checks (Middleware)

**Frontend:**
- [ ] Team Management UI (Invite, Remove, Change Roles)
- [ ] Permission-basierte UI (z.B. Staff sieht keine Pricing)
- [ ] User Settings Page

**Acceptance Criteria:**
- [ ] Owner kann Team Members einladen (Manager, Staff, Viewer)
- [ ] Rollen-Permissions werden enforced (RLS)
- [ ] Tenant Isolation funktioniert (Owner A sieht nicht Owner B's Daten)
- [ ] Permission-basierte UI funktioniert (Staff sieht keine Pricing)

---

### Phase 5: MVP Polish & Launch Prep
**Timeline:** 2-3 Wochen

**Deliverables:**

**Testing:**
- [ ] Comprehensive E2E Tests (kritische User Journeys)
- [ ] Load Testing (100 concurrent bookings)
- [ ] Security Audit (OWASP Top 10)

**DevOps:**
- [ ] CI/CD Pipeline (GitHub Actions)
- [ ] Monitoring Setup (Prometheus, Grafana)
- [ ] Alerting Setup (PagerDuty, Slack)
- [ ] Runbooks (Incident Response)

**Documentation:**
- [ ] User Guide (Owner, Manager, Staff)
- [ ] API Documentation (OpenAPI)
- [ ] Admin Guide (Deployment, Monitoring)

**Acceptance Criteria:**
- [ ] E2E Tests passing (100%)
- [ ] Load Tests passing (100 concurrent bookings)
- [ ] Security Audit passed (keine CRITICAL/HIGH findings)
- [ ] Monitoring funktioniert (Metrics, Logs, Traces)
- [ ] Runbooks vorhanden (für alle kritischen Szenarien)

---

## 5. Acceptance Criteria (Zusammenfassung)

### 5.1 Funktionale Kriterien

#### Direct Booking
- [ ] **F-DB-01:** Guest kann Property suchen (Location, Dates, Guests)
- [ ] **F-DB-02:** Guest sieht nur verfügbare Properties (Real-Time Check)
- [ ] **F-DB-03:** Guest kann buchen (mit/ohne Account)
- [ ] **F-DB-04:** Payment via Stripe PaymentIntents funktioniert (inkl. 3DS)
- [ ] **F-DB-05:** Booking wird nach Payment confirmed
- [ ] **F-DB-06:** Confirmation Email wird gesendet
- [ ] **F-DB-07:** Availability wird automatisch aktualisiert
- [ ] **F-DB-08:** Edge Cases gehandelt (Timeout, Payment Failure, Race Condition)

#### Channel Manager (Airbnb)
- [ ] **F-CM-01:** Owner kann Airbnb-Account verbinden (OAuth)
- [ ] **F-CM-02:** Availability wird von PMS zu Airbnb synchronisiert
- [ ] **F-CM-03:** Pricing wird von PMS zu Airbnb synchronisiert
- [ ] **F-CM-04:** Airbnb-Buchungen werden in PMS importiert (Webhook)
- [ ] **F-CM-05:** Doppelbuchungen werden verhindert (Redis Lock + DB Constraint)
- [ ] **F-CM-06:** Sync-Fehler werden geloggt und gecountert
- [ ] **F-CM-07:** Rate Limits werden eingehalten (100 req/min)
- [ ] **F-CM-08:** Circuit Breaker aktiviert bei Failures (5 Failures → 5 min cooldown)

#### Property Management
- [ ] **F-PM-01:** Owner kann neue Property anlegen
- [ ] **F-PM-02:** Owner kann Property-Details bearbeiten
- [ ] **F-PM-03:** Owner kann Fotos hochladen und ordnen
- [ ] **F-PM-04:** Owner kann Property deaktivieren (soft delete)
- [ ] **F-PM-05:** Multi-Tenancy: Owner sieht nur eigene Properties (RLS)

#### Booking Management
- [ ] **F-BM-01:** Owner sieht alle Bookings (filterable by Status, Source, Date Range)
- [ ] **F-BM-02:** Owner kann Booking canceln (mit Refund-Logik)
- [ ] **F-BM-03:** Staff kann Check-in/Check-out Status updaten
- [ ] **F-BM-04:** Guest Info ist vollständig (Name, Email, Phone)
- [ ] **F-BM-05:** Multi-Tenancy: Owner sieht nur eigene Bookings (RLS)

#### Availability & Pricing
- [ ] **F-AP-01:** Owner kann Dates im Kalender blocken/unblocken
- [ ] **F-AP-02:** Owner kann Base Price setzen
- [ ] **F-AP-03:** Owner kann Seasonal Pricing Rules erstellen
- [ ] **F-AP-04:** Owner kann Minimum Stay Rules setzen
- [ ] **F-AP-05:** Pricing wird korrekt berechnet (Base + Seasonal + Discounts)
- [ ] **F-AP-06:** Availability wird nach Booking automatisch aktualisiert

### 5.2 Nicht-Funktionale Kriterien

#### Performance
- [ ] **NF-P-01:** Availability Check < 500ms (P95)
- [ ] **NF-P-02:** Booking Creation < 2s (P95)
- [ ] **NF-P-03:** Property Search < 1s (P95)
- [ ] **NF-P-04:** Channel Sync Latency < 30s (P95, inbound webhooks)

#### Reliability
- [ ] **NF-R-01:** Zero Doppelbuchungen (100% guarantee via locks + constraints)
- [ ] **NF-R-02:** Sync Success Rate > 99% (mit Retry-Logik)
- [ ] **NF-R-03:** Uptime > 99.5% (SLA)

#### Security
- [ ] **NF-S-01:** OAuth Tokens encrypted at rest (Fernet AES-128)
- [ ] **NF-S-02:** Webhook Signatures verified (HMAC-SHA256)
- [ ] **NF-S-03:** Multi-Tenancy enforced (RLS Policies)
- [ ] **NF-S-04:** OWASP Top 10 compliant (keine CRITICAL/HIGH findings)

#### Scalability
- [ ] **NF-SC-01:** System handhabt 100 concurrent bookings
- [ ] **NF-SC-02:** Database handhabt 10,000 properties
- [ ] **NF-SC-03:** Redis Cache hit rate > 80%

#### Observability
- [ ] **NF-O-01:** Alle Sync-Operationen werden geloggt (Structured Logs)
- [ ] **NF-O-02:** Prometheus Metrics für alle kritischen Operations
- [ ] **NF-O-03:** Tracing aktiviert für Debugging (OpenTelemetry Hooks)

---

## 6. Technical Constraints (Given)

### 6.1 Tech Stack (Locked)
- **Backend:** FastAPI (Python 3.11+), Supabase (PostgreSQL 15+)
- **Frontend:** Next.js 14+ (App Router), React 18+, TypeScript
- **State Management:** Zustand, TanStack Query
- **UI Library:** Shadcn/UI (Tailwind CSS)
- **Auth:** Supabase Auth (Magic Links, OAuth)
- **Payment:** Stripe (PaymentIntents API)
- **Queue:** Celery (Redis as broker)
- **Cache:** Redis (Idempotency, Rate Limiting, Locks)
- **Monitoring:** Prometheus, Grafana, OpenTelemetry

### 6.2 Security Requirements
- OAuth Token Encryption (Fernet, 44-char keys)
- Webhook Signature Verification (HMAC-SHA256)
- Row-Level Security (RLS) für Multi-Tenancy
- HTTPS Only (TLS 1.3)

### 6.3 Database Schema (Locked)
- Tables: properties, bookings, guests, channel_connections, pricing_rules, availability, users
- RLS Policies: Alle Tabellen mit tenant_id
- Constraints: Exclusion Constraint für bookings (property_id, daterange)

---

## 7. Success Metrics

### 7.1 Launch Metrics (MVP Success)

**Critical Metrics:**
- ✅ **Zero Doppelbuchungen:** 100% guarantee (via locks + constraints)
- ✅ **Sync Reliability:** > 99% success rate (mit Retry-Logik)
- ✅ **Direct Booking Conversion:** > 10% (Guest visits → Confirmed Booking)
- ✅ **Channel Sync Latency:** < 30s (P95, inbound webhooks)

**Quality Metrics:**
- ✅ **Test Coverage:** > 80% (Unit + Integration)
- ✅ **Security Audit:** No CRITICAL/HIGH findings
- ✅ **Uptime:** > 99.5% (SLA)

**User Adoption Metrics (Post-Launch):**
- Target: 10 Owners onboarded (first month)
- Target: 100 Properties listed (first month)
- Target: 50 Direct Bookings (first month)
- Target: 5 Airbnb Channel Connections (first month)

### 7.2 Post-MVP Metrics (Growth)

**Channel Expansion:**
- Target: 4 zusätzliche Channels (Booking.com, Expedia, FeWo-direkt, Google)
- Timeline: 6-12 Monate nach MVP

**Feature Expansion:**
- Guest Portal (optional)
- Revenue Analytics Dashboard
- Smart Pricing (Competitor-based)

---

## 8. Roadmap (Post-MVP)

### 8.1 Channel Expansion (6-12 Monate)

**Booking.com Integration**
- Priority: HIGH (wichtigster Channel nach Airbnb)
- Timeline: 2-3 Monate nach MVP
- Complexity: MEDIUM (ähnlich zu Airbnb)

**Expedia Integration**
- Priority: MEDIUM
- Timeline: 4-6 Monate nach MVP
- Complexity: HIGH (komplexere API)

**FeWo-direkt Integration**
- Priority: LOW
- Timeline: 6-9 Monate nach MVP
- Complexity: MEDIUM

**Google Vacation Rentals Integration**
- Priority: LOW
- Timeline: 9-12 Monate nach MVP
- Complexity: HIGH

### 8.2 Advanced Features

**Revenue Management**
- Analytics Dashboard (Occupancy, Revenue, Trends)
- Smart Pricing (Competitor-based, ML-driven)
- Financial Reports (P&L, Tax Reports)

**Workflow Automation**
- Housekeeping Workflows (Task Assignment, Status Tracking)
- Maintenance Workflows (Issue Reporting, Tracking)
- Automated Guest Communication (Pre-Arrival, During Stay, Post-Stay)

**Guest Portal**
- Self-Service Portal (Booking History, Invoices)
- Support Tickets
- Reviews & Ratings

### 8.3 UI/UX Polish (Separates Phase)

**Design System**
- Custom Illustrations & Icons
- Branded Color Palette
- Typography System
- Animation Library

**Responsive Design**
- Mobile Optimization
- Tablet Optimization
- Accessibility Enhancements (WCAG 2.1 AA)

**Performance Optimization**
- Image Optimization (Next.js Image)
- Code Splitting (Dynamic Imports)
- Lighthouse Score > 90 (Performance, Accessibility)

---

## 9. Risiken & Mitigations

### 9.1 Technical Risks

**Risk 1: Channel API Changes**
- **Impact:** HIGH (Sync könnte brechen)
- **Likelihood:** MEDIUM (APIs ändern sich gelegentlich)
- **Mitigation:** Adapter-Pattern (isoliert Changes), API Versioning, Monitoring

**Risk 2: Rate Limiting (Channels)**
- **Impact:** MEDIUM (Sync-Verzögerungen)
- **Likelihood:** MEDIUM (bei vielen Properties)
- **Mitigation:** Redis Rate Limiter, Circuit Breaker, Exponential Backoff

**Risk 3: Race Conditions (Doppelbuchungen)**
- **Impact:** CRITICAL (Zero-Tolerance)
- **Likelihood:** LOW (mit Locks + Constraints)
- **Mitigation:** Redis Distributed Lock (5-min TTL), DB Exclusion Constraint

### 9.2 Business Risks

**Risk 4: Channel Connection Failures**
- **Impact:** HIGH (Owner kann nicht verbinden)
- **Likelihood:** LOW (aber OAuth kann tricky sein)
- **Mitigation:** Klare Error Messages, Retry-Mechanismen, Support-Docs

**Risk 5: Payment Failures (Stripe)**
- **Impact:** MEDIUM (verlorene Buchungen)
- **Likelihood:** LOW (Stripe ist robust)
- **Mitigation:** Payment Timeout (30 min), Email mit Payment-Link, Retry-Logic

---

## 10. Appendix

### 10.1 Glossar

| Begriff | Definition |
|---------|------------|
| **PMS** | Property Management System |
| **Channel Manager** | Integration zu Buchungsplattformen (Airbnb, Booking.com, etc.) |
| **Direct Booking** | Buchung direkt über die PMS-Webapp (ohne Channel) |
| **Source of Truth** | PMS-Core ist master, Channels sind replicas |
| **RLS** | Row-Level Security (PostgreSQL Feature für Multi-Tenancy) |
| **Idempotency** | Operation kann mehrfach ausgeführt werden ohne Side-Effects |
| **Circuit Breaker** | Automatisches Deaktivieren bei wiederholten Fehlern |
| **Rate Limiting** | Begrenzung der API-Calls pro Zeiteinheit |

### 10.2 Referenzen

**Interne Docs:**
- `docs/architecture.md` - System Architecture (C4 Diagrams, ADRs)
- `docs/direct-booking.md` - Direct Booking Engine Design
- `docs/channel-manager.md` - Channel Manager Implementation
- `docs/phase7-qa-security-remediation.md` - Security Fixes

**Externe APIs:**
- [Airbnb API Docs](https://www.airbnb.com/partner/api-docs) (Partner API)
- [Stripe API Docs](https://stripe.com/docs/api) (PaymentIntents)
- [Supabase Docs](https://supabase.com/docs) (RLS, Auth)

---

**Ende des PRD / Pflichtenheft (MVP-Light)**
