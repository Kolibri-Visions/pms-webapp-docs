# Changelog

Alle wichtigen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### In Entwicklung

- Phase 17A: GitHub Setup (Branching, CI/CD, Templates)
- Produktspezifikation vollständig (Phase 1-16)

---

## Produktspezifikation (Frozen Phases)

### [Phase 15-16] - 2025-12-22

#### Added (Konzept)
- Direct Booking Flow (ohne Zahlungsabwicklung)
  - Booking Widget für Agentur-Website
  - 4-Schritte Booking Flow (Datum → Gästedaten → Zusammenfassung → Bestätigung)
  - Payment-Integration-Konzept (Stripe, PayPal, Überweisung)
  - E-Mail-Templates (4 vollständige Templates, Deutsch)
  - Kalender-Synchronisation (iCal 2-Wege-Sync)
- Eigentümer-Portal (Read-Only)
  - Eigentümer-Dashboard (nur eigene Objekte)
  - Berichte für Eigentümer (Umsatz, Auslastung)
  - RLS-Konzept (Supabase PostgreSQL Policies)

#### Documentation
- `docs/phase15-16-direct-booking-eigentuemer.md` (2.148 Zeilen)

---

### [Phase 14] - 2025-12-22

#### Added (Konzept)
- Preismodell & Billing-Strategie
  - 3 Tiers: Starter (€49), Professional (€149), Enterprise (Custom)
  - 14 Tage Trial (OHNE Kreditkarte)
  - Stripe Billing (Subscriptions, Invoicing, Dunning)
  - Competitor Analysis (Guesty, Hostaway, Beds24)
  - Pricing Page (Wireframe, Copywriting Deutsch)

#### Documentation
- `docs/phase14-preismodell-logik.md` (1.395 Zeilen)

---

### [Phase 11-13] - 2025-12-22

#### Added (Konzept)
- Agentur-UX & RBAC
  - Agency-First Positioning (Markt, Value Proposition)
  - Landing Page & Pitch-Logik (10 Sections, Sales Funnel)
  - RBAC-System (5 Rollen: Agentur-Admin, Manager, Mitarbeiter, Eigentümer, Buchhalter)
  - Permissions-Matrix (5 Rollen × 40+ Features)
  - Menü-Struktur pro Rolle (ASCII Mockups)
  - RLS-Konzept (Row-Level Security)

#### Documentation
- `docs/phase11-13-agentur-ux-rollen.md` (~15.000 Wörter)

---

### [Phase 10B/10C] - 2025-12-22

#### Added (Konzept)
- Visual Design System
  - Color System (Brand: #2563EB, Neutrals, Semantic)
  - Typography (Inter, 12px-36px Scale)
  - Component Styling (Buttons, Forms, Cards, Tables, Modals)
  - White-Label Theming (CSS Variables)
  - Deutsche UI-Texte (Labels, Buttons, Error Messages)

#### Documentation
- `docs/phase10b-10c-visual-design.md` (~1.800 Zeilen)

---

### [Phase 10A] - 2025-12-22

#### Added (Konzept)
- UI/UX Konzeption
  - Informationsarchitektur & Navigation
  - Wireframes für alle MVP-Screens
  - Design-System-Grundlagen
  - UI States (Empty, Loading, Error, Success)

#### Documentation
- `docs/phase10a-ui-ux.md` (~2.400 Zeilen)

---

### [Phase 9] - 2025-12-22

#### Added (Konzept)
- Projekt- & Release-Vorbereitung
  - GitHub-Setup-Strategie (Branches, Tags, Commits)
  - Deployment-Reihenfolge (Supabase → Backend → Workers → Frontend)
  - Test-Strategie nach Deployment (Smoke → Integration → E2E)
  - Design-System-Ansatz

#### Documentation
- `docs/phase9-release-plan.md` (~1.000 Zeilen)

---

### [Phase 8] - 2025-12-22

#### Added (Konzept)
- PRD / Pflichtenheft (Product Requirements Document)
  - Produkt-Vision & Ziele
  - Funktionale Anforderungen
  - Nicht-funktionale Anforderungen
  - MVP-Scope Definition

#### Documentation
- `docs/phase8-prd-light.md`

---

### [Phase 1-7] - 2025-12-21

#### Added (Implementation)
- Backend Setup (FastAPI)
- Supabase Integration (PostgreSQL, Auth, Storage)
- Channel Manager (Airbnb Adapter)
- Sync Engine (Celery)
- Security Features:
  - OAuth Token Encryption (Fernet)
  - Webhook Signature Verification (HMAC-SHA256)
  - Redis Client (Upstash)
  - Rate Limiting & Circuit Breaker

#### Tests
- 26 Security Tests (✅ All Passing)
- Smoke Tests für Channel Manager

---

## Release-Schema

### Version Format: `vMAJOR.MINOR.PATCH`

- **MAJOR:** Breaking changes (z.B. v2.0.0)
- **MINOR:** Neue Features, backward-compatible (z.B. v1.1.0)
- **PATCH:** Bug fixes, backward-compatible (z.B. v1.0.1)

### Pre-Release Tags:
- `vX.Y.Z-alpha.N`: Alpha releases (unstable)
- `vX.Y.Z-beta.N`: Beta releases (feature-complete, testing)
- `vX.Y.Z-rc.N`: Release candidates (release-ready, final testing)

---

## Lizenz

Dieses Projekt ist proprietär. Alle Rechte vorbehalten.
