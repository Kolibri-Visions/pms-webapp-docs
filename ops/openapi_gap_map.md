# OpenAPI Gap Map

**Generated:** 2026-01-22T13:41:56.193341
**Source:** https://api.fewo.kolibri-visions.de/openapi.json
**API Version:** 0.1.0

## Summary

- **Total API Paths:** 81
- **Total Tags:** 18
- **Complete Modules:** 5 (8+ endpoints)
- **Partial Modules:** 9 (3-7 endpoints)
- **Minimal Modules:** 4 (1-2 endpoints)

## Tags Overview

| Tag | Endpoints | GET | POST | PATCH | DELETE | PUT | Status | Priority |
|-----|-----------|-----|------|-------|--------|-----|--------|----------|
| Admin | 3 | 1 | 1 | 0 | 0 | 1 | 🟡 Partial | Medium |
| Agencies | 2 | 1 | 0 | 1 | 0 | 0 | 🔴 Minimal | High |
| Availability | 5 | 2 | 2 | 0 | 1 | 0 | 🟡 Partial | Medium |
| Booking Requests | 5 | 2 | 3 | 0 | 0 | 0 | 🟡 Partial | Medium |
| Bookings | 6 | 2 | 2 | 2 | 0 | 0 | 🟡 Partial | Medium |
| Branding | 2 | 1 | 0 | 0 | 0 | 1 | 🔴 Minimal | High |
| Channel Connections | 12 | 6 | 4 | 0 | 1 | 1 | ✅ Complete | Low |
| Epic A - Onboarding & RBAC | 10 | 4 | 3 | 2 | 1 | 0 | ✅ Complete | Low |
| Guests | 6 | 3 | 1 | 1 | 0 | 1 | 🟡 Partial | Medium |
| Operations | 3 | 3 | 0 | 0 | 0 | 0 | 🟡 Partial | Medium |
| Owners | 11 | 7 | 2 | 2 | 0 | 0 | ✅ Complete | Low |
| Pricing | 33 | 8 | 12 | 8 | 5 | 0 | ✅ Complete | Low |
| Properties | 5 | 2 | 1 | 1 | 1 | 0 | 🟡 Partial | Medium |
| Public Direct Booking | 3 | 2 | 1 | 0 | 0 | 0 | 🟡 Partial | Medium |
| Public Website | 8 | 6 | 1 | 0 | 0 | 1 | ✅ Complete | Low |
| RBAC | 1 | 1 | 0 | 0 | 0 | 0 | 🔴 Minimal | High |
| Team | 7 | 2 | 3 | 1 | 1 | 0 | 🟡 Partial | Medium |
| health | 2 | 2 | 0 | 0 | 0 | 0 | 🔴 Minimal | High |

## Detailed Module Analysis

### 🔴 Minimal Modules (High Priority)

#### Agencies

**Endpoints:** 2

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/agencies/current` | Get current agency |
| PATCH | `/api/v1/agencies/current` | Update current agency |

#### Branding

**Endpoints:** 2

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/branding` | Get tenant branding |
| PUT | `/api/v1/branding` | Update tenant branding (admin/manager) |

#### RBAC

**Endpoints:** 1

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/me` | Get current user identity |

#### health

**Endpoints:** 2

| Method | Path | Summary |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/health/ready` | Readiness |

### 🟡 Partial Modules (Medium Priority)

#### Admin

**Endpoints:** 3

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/public-site/domain` | Get public domain status |
| PUT | `/api/v1/public-site/domain` | Save/update public domain |
| POST | `/api/v1/public-site/domain/verify` | Verify public domain |

#### Availability

**Endpoints:** 5

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/availability` | Query property availability |
| POST | `/api/v1/availability/blocks` | Create availability block |
| DELETE | `/api/v1/availability/blocks/{block_id}` | Delete availability block |
| GET | `/api/v1/availability/blocks/{block_id}` | Get availability block by ID |
| POST | `/api/v1/availability/sync` | Sync availability to external channel |

#### Booking Requests

**Endpoints:** 5

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/booking-requests` | List booking requests |
| GET | `/api/v1/booking-requests/{booking_request_id}` | Get booking request detail |
| POST | `/api/v1/booking-requests/{booking_request_id}/approve` | Approve booking request |
| POST | `/api/v1/booking-requests/{booking_request_id}/decline` | Decline booking request |
| POST | `/api/v1/booking-requests/{booking_request_id}/review` | Review booking request |

#### Bookings

**Endpoints:** 6

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/bookings` | List all bookings |
| POST | `/api/v1/bookings` | Create new booking |
| GET | `/api/v1/bookings/{booking_id}` | Get booking by ID |
| PATCH | `/api/v1/bookings/{booking_id}` | Update booking |
| POST | `/api/v1/bookings/{booking_id}/cancel` | Cancel booking |
| PATCH | `/api/v1/bookings/{booking_id}/status` | Update booking status |

#### Guests

**Endpoints:** 6

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/guests` | List all guests |
| POST | `/api/v1/guests` | Create new guest |
| GET | `/api/v1/guests/{guest_id}` | Get guest details |
| PATCH | `/api/v1/guests/{guest_id}` | Update guest (partial) |
| PUT | `/api/v1/guests/{guest_id}` | Update guest (full) |
| GET | `/api/v1/guests/{guest_id}/timeline` | Get guest booking timeline |

#### Operations

**Endpoints:** 3

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/ops/audit-log` | Get Audit Log |
| GET | `/api/v1/ops/modules` | Get Modules |
| GET | `/api/v1/ops/version` | Get Version |

#### Properties

**Endpoints:** 5

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/properties` | List all properties |
| POST | `/api/v1/properties` | Create new property |
| DELETE | `/api/v1/properties/{property_id}` | Delete property |
| GET | `/api/v1/properties/{property_id}` | Get property by ID |
| PATCH | `/api/v1/properties/{property_id}` | Update property |

#### Public Direct Booking

**Endpoints:** 3

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/public/availability` | Check availability (public) |
| POST | `/api/v1/public/booking-requests` | Create booking request (public) |
| GET | `/api/v1/public/ping` | Public booking router health check |

#### Team

**Endpoints:** 7

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/team/invites` | List team invitations |
| POST | `/api/v1/team/invites` | Create team invitation |
| POST | `/api/v1/team/invites/{invite_id}/accept` | Accept team invitation |
| POST | `/api/v1/team/invites/{invite_id}/revoke` | Revoke team invitation |
| GET | `/api/v1/team/members` | List team members |
| DELETE | `/api/v1/team/members/{user_id}` | Remove team member |
| PATCH | `/api/v1/team/members/{user_id}` | Update team member role |

### ✅ Complete Modules (Low Priority)

#### Channel Connections

**Endpoints:** 12

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/channel-connections/` | List all connections |
| POST | `/api/v1/channel-connections/` | Create channel connection |
| DELETE | `/api/v1/channel-connections/{connection_id}` | Delete connection |
| GET | `/api/v1/channel-connections/{connection_id}` | Get connection details |
| PUT | `/api/v1/channel-connections/{connection_id}` | Update connection |
| POST | `/api/v1/channel-connections/{connection_id}/sync` | Trigger manual sync |
| GET | `/api/v1/channel-connections/{connection_id}/sync-batches` | List recent sync batches |
| GET | `/api/v1/channel-connections/{connection_id}/sync-batches/{batch_id}` | Get batch status aggregation |
| GET | `/api/v1/channel-connections/{connection_id}/sync-logs` | Get sync logs |
| POST | `/api/v1/channel-connections/{connection_id}/sync-logs/purge` | Purge old sync logs (admin only) |
| GET | `/api/v1/channel-connections/{connection_id}/sync-logs/purge/preview` | Preview purge count (admin only) |
| POST | `/api/v1/channel-connections/{connection_id}/test` | Test connection health |

#### Epic A - Onboarding & RBAC

**Endpoints:** 10

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/agencies/current` | Get current agency |
| PATCH | `/api/v1/agencies/current` | Update current agency |
| GET | `/api/v1/me` | Get current user identity |
| GET | `/api/v1/team/invites` | List team invitations |
| POST | `/api/v1/team/invites` | Create team invitation |
| POST | `/api/v1/team/invites/{invite_id}/accept` | Accept team invitation |
| POST | `/api/v1/team/invites/{invite_id}/revoke` | Revoke team invitation |
| GET | `/api/v1/team/members` | List team members |
| DELETE | `/api/v1/team/members/{user_id}` | Remove team member |
| PATCH | `/api/v1/team/members/{user_id}` | Update team member role |

#### Owners

**Endpoints:** 11

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/owner/bookings` | List Owner Bookings |
| GET | `/api/v1/owner/properties` | List Owner Properties |
| GET | `/api/v1/owner/statements` | List Owner Statements Owner |
| GET | `/api/v1/owner/statements/{statement_id}` | Get Owner Statement Detail |
| GET | `/api/v1/owner/statements/{statement_id}/download` | Download Owner Statement Csv |
| GET | `/api/v1/owners` | List Owners |
| POST | `/api/v1/owners` | Create Owner |
| PATCH | `/api/v1/owners/{owner_id}` | Update Owner |
| GET | `/api/v1/owners/{owner_id}/statements` | List Owner Statements Staff |
| POST | `/api/v1/owners/{owner_id}/statements/generate` | Generate Owner Statement |
| PATCH | `/api/v1/properties/{property_id}/owner` | Assign Property Owner |

#### Pricing

**Endpoints:** 33

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/pricing/fees` | List Fees |
| POST | `/api/v1/pricing/fees` | Create Fee |
| PATCH | `/api/v1/pricing/fees/{fee_id}` | Update Fee |
| POST | `/api/v1/pricing/quote` | Calculate Quote |
| GET | `/api/v1/pricing/rate-plans` | List Rate Plans |
| POST | `/api/v1/pricing/rate-plans` | Create Rate Plan |
| DELETE | `/api/v1/pricing/rate-plans/{rate_plan_id}` | Delete Rate Plan |
| GET | `/api/v1/pricing/rate-plans/{rate_plan_id}` | Get Rate Plan Detail |
| PATCH | `/api/v1/pricing/rate-plans/{rate_plan_id}` | Update Rate Plan |
| POST | `/api/v1/pricing/rate-plans/{rate_plan_id}/apply-season-template` | Apply Season Template To Rate Plan |
| PATCH | `/api/v1/pricing/rate-plans/{rate_plan_id}/archive` | Archive Rate Plan |
| PATCH | `/api/v1/pricing/rate-plans/{rate_plan_id}/restore` | Restore Rate Plan |
| GET | `/api/v1/pricing/rate-plans/{rate_plan_id}/seasons` | List Rate Plan Seasons |
| POST | `/api/v1/pricing/rate-plans/{rate_plan_id}/seasons` | Create Rate Plan Season |
| POST | `/api/v1/pricing/rate-plans/{rate_plan_id}/seasons/sync-from-template` | Sync Seasons From Template |
| DELETE | `/api/v1/pricing/rate-plans/{rate_plan_id}/seasons/{season_id}` | Delete Rate Plan Season |
| PATCH | `/api/v1/pricing/rate-plans/{rate_plan_id}/seasons/{season_id}` | Update Rate Plan Season |
| DELETE | `/api/v1/pricing/rate-plans/{rate_plan_id}/seasons/{season_id}/purge` | Purge Rate Plan Season |
| POST | `/api/v1/pricing/rate-plans/{rate_plan_id}/seasons/{season_id}/restore` | Restore Rate Plan Season |
| GET | `/api/v1/pricing/season-templates` | List Season Templates |
| POST | `/api/v1/pricing/season-templates` | Create Season Template |
| DELETE | `/api/v1/pricing/season-templates/{template_id}` | Archive Season Template |
| GET | `/api/v1/pricing/season-templates/{template_id}` | Get Season Template Detail |
| PATCH | `/api/v1/pricing/season-templates/{template_id}` | Update Season Template |
| GET | `/api/v1/pricing/season-templates/{template_id}/periods` | List Template Periods |
| POST | `/api/v1/pricing/season-templates/{template_id}/periods` | Create Template Period |
| DELETE | `/api/v1/pricing/season-templates/{template_id}/periods/{period_id}` | Delete Template Period |
| PATCH | `/api/v1/pricing/season-templates/{template_id}/periods/{period_id}` | Update Template Period |
| POST | `/api/v1/pricing/seasons/bulk-archive` | Bulk Archive Seasons |
| POST | `/api/v1/pricing/seasons/bulk-delete` | Bulk Delete Seasons |
| GET | `/api/v1/pricing/taxes` | List Taxes |
| POST | `/api/v1/pricing/taxes` | Create Tax |
| PATCH | `/api/v1/pricing/taxes/{tax_id}` | Update Tax |

#### Public Website

**Endpoints:** 8

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/public-site/domain` | Get public domain status |
| PUT | `/api/v1/public-site/domain` | Save/update public domain |
| POST | `/api/v1/public-site/domain/verify` | Verify public domain |
| GET | `/api/v1/public/properties` | List public properties |
| GET | `/api/v1/public/properties/{property_id}` | Get public property details |
| GET | `/api/v1/public/site/pages` | List published pages |
| GET | `/api/v1/public/site/pages/{slug}` | Get page by slug |
| GET | `/api/v1/public/site/settings` | Get public site settings |

## Implementation Candidates

Based on the gap analysis, the following modules are recommended for next implementation:

### High Priority (Minimal Coverage)

- **Agencies** (2 endpoints)
  - Current: GET:1, PATCH:1
  - Recommendation: Expand to full CRUD if applicable

- **Branding** (2 endpoints)
  - Current: GET:1, PUT:1
  - Recommendation: Expand to full CRUD if applicable

- **RBAC** (1 endpoints)
  - Current: GET:1
  - Recommendation: Expand to full CRUD if applicable

- **health** (2 endpoints)
  - Current: GET:2
  - Recommendation: Expand to full CRUD if applicable

### Medium Priority (Partial Coverage)

- **Admin** (3 endpoints)
  - Current: GET:1, POST:1, PUT:1
  - Recommendation: Review for missing operations

- **Availability** (5 endpoints)
  - Current: DELETE:1, GET:2, POST:2
  - Recommendation: Review for missing operations

- **Booking Requests** (5 endpoints)
  - Current: GET:2, POST:3
  - Recommendation: Review for missing operations

- **Bookings** (6 endpoints)
  - Current: GET:2, PATCH:2, POST:2
  - Recommendation: Review for missing operations

- **Guests** (6 endpoints)
  - Current: GET:3, PATCH:1, POST:1, PUT:1
  - Recommendation: Review for missing operations

- **Operations** (3 endpoints)
  - Current: GET:3
  - Recommendation: Review for missing operations

- **Properties** (5 endpoints)
  - Current: DELETE:1, GET:2, PATCH:1, POST:1
  - Recommendation: Review for missing operations

- **Public Direct Booking** (3 endpoints)
  - Current: GET:2, POST:1
  - Recommendation: Review for missing operations

- **Team** (7 endpoints)
  - Current: DELETE:1, GET:2, PATCH:1, POST:3
  - Recommendation: Review for missing operations

## Missing Common PMS Modules

The following common PMS modules are NOT present in the current API:

- **Amenities:** Property amenities and features management
- **Reviews:** Guest reviews and ratings
- **Payments:** Payment tracking and processing
- **Invoices:** Invoice generation and management
- **Reports:** Analytics and reporting
- **Housekeeping:** Cleaning schedules and tasks
- **Maintenance:** Property maintenance tracking
- **Messages:** Guest messaging and communication
- **Contracts:** Rental contracts and agreements
- **Documents:** Document storage and management

---

*Generated by `backend/scripts/openapi_gap_map.py`*
