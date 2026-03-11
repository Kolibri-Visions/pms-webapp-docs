# Datenbank-Architektur

> Source of Truth: `supabase/migrations/00000000000000_baseline.sql`, `backend/app/core/database.py`

## Ueberblick

| Eigenschaft | Wert |
|-------------|------|
| Datenbank | PostgreSQL via Supabase |
| Tabellen | 58 |
| Driver | asyncpg 0.29.0 (raw SQL, kein ORM) |
| Migrationen | `supabase/migrations/` (raw SQL) |
| Multi-Tenancy | `agency_id` + RLS Policies |

## Query-Pattern

Kein ORM. Alle Queries sind parametrisierte raw SQL via asyncpg:

```python
# Service-Layer Pattern
row = await self.db.fetchrow(
    "SELECT * FROM bookings WHERE id = $1 AND agency_id = $2",
    booking_id, agency_id
)

rows = await self.db.fetch(
    "SELECT * FROM properties WHERE agency_id = $1 ORDER BY name",
    agency_id
)

count = await self.db.fetchval(
    "SELECT count(*) FROM guests WHERE agency_id = $1",
    agency_id
)
```

## Connection Pool (app/core/database.py)

- Fork-safe: PID-Tracking (`_pool_pid`)
- Generation Counter fuer Pool-Verifikation
- Lazy Lock-Initialisierung
- JSON/JSONB Codec-Registration bei Connection-Init
- Retry-Logik fuer DNS/Connection-Fehler
- Background-Reconnect (konfigurierbar)

Settings:
- `db_startup_max_wait_seconds=60`
- `db_startup_retry_interval_seconds=2`
- `db_background_reconnect_enabled=True`
- `db_background_reconnect_interval_seconds=30`
- `db_pool_debug=False`

## RLS (Row-Level Security)

### Pattern

```sql
-- Helper-Funktion
CREATE FUNCTION get_user_agency_ids() RETURNS SETOF UUID AS $$
  SELECT agency_id FROM team_members WHERE user_id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER;

-- RLS-Policy (auf jeder tenant-scoped Tabelle)
CREATE POLICY "agency_isolation" ON bookings
  FOR ALL
  USING (agency_id IN (SELECT get_user_agency_ids()));
```

### Weitere Helper-Funktionen

| Funktion | Zweck |
|----------|-------|
| `get_user_agency_ids()` | Alle Agency-IDs des Users |
| `user_has_agency_access(uuid)` | Prueft Zugriff auf Agency |
| `get_user_role_in_agency(uuid)` | Rolle in einer Agency |
| `get_user_permissions(uuid, uuid)` | Berechtigungen |
| `generate_booking_reference()` | Auto-Buchungsnummer |
| `generate_invoice_number()` | Auto-Rechnungsnummer |
| `encrypt_pii(text, text)` | PGP-Verschluesselung |
| `decrypt_pii(bytea, text)` | PGP-Entschluesselung |
| `set_updated_at()` | Trigger fuer updated_at |
| `calculate_refund_percent(jsonb, int)` | Storno-Berechnung |

## Exclusion Constraint (Doppelbuchungsschutz)

```sql
EXCLUDE USING gist (
    property_id WITH =,
    daterange(check_in, check_out, '[)') WITH &&
)
WHERE (
    status = ANY (ARRAY['confirmed', 'checked_in'])
    AND deleted_at IS NULL
);
```

Half-open Interval `[check_in, check_out)`: Check-out Tag ist frei.
Nur `confirmed` und `checked_in` blockieren Ueberlappungen.

## Tabellen (58 gesamt)

### Core

| Tabelle | Zweck |
|---------|-------|
| `agencies` | Mandanten |
| `team_members` | User ↔ Agency ↔ Role |
| `profiles` | User-Profile (Supabase Auth) |
| `roles` | Rollen pro Agency |
| `role_permissions` | Rollen ↔ Berechtigungen |
| `role_templates` | Rollen-Vorlagen |
| `permission_definitions` | Globale Berechtigungen |
| `permission_audit_log` | Berechtigungs-Audit |

### Buchungen & Gaeste

| Tabelle | Zweck |
|---------|-------|
| `bookings` | Buchungen |
| `booking_requests` | Buchungsanfragen (nicht in bookings Tabelle) |
| `direct_bookings` | Direktbuchungen |
| `external_bookings` | Externe Buchungen |
| `guests` | Gaeste-Stammdaten |
| `availability_blocks` | Verfuegbarkeitssperren |
| `inventory_ranges` | Inventar-Bereiche |
| `block_templates` | Sperr-Vorlagen |

### Properties

| Tabelle | Zweck |
|---------|-------|
| `properties` | Objekte |
| `property_amenities` | Property ↔ Amenity |
| `property_extra_services` | Property ↔ Zusatzleistung |
| `property_media` | Property ↔ Medien |
| `amenities` | Agency-spezifische Amenities |
| `amenity_definitions` | Globale Amenity-Definitionen |
| `extra_services` | Zusatzleistungen |

### Pricing

| Tabelle | Zweck |
|---------|-------|
| `rate_plans` | Preisplaene |
| `rate_plan_seasons` | Saisonale Preise |
| `pricing_rules` | Preisregeln |
| `pricing_fees` | Gebuehren-Templates |
| `pricing_taxes` | Steuern |
| `pricing_season_templates` | Saison-Vorlagen |
| `pricing_season_template_periods` | Saison-Perioden |
| `cancellation_policies` | Stornobedingungen |

### Finance

| Tabelle | Zweck |
|---------|-------|
| `invoices` | Rechnungen |
| `payments` | Zahlungen |
| `owners` | Eigentuemer |
| `owner_statements` | Eigentuemer-Abrechnungen |
| `owner_statement_items` | Abrechnungsposten |
| `owner_invites` | Eigentuemer-Einladungen |

### Public Website

| Tabelle | Zweck |
|---------|-------|
| `public_site_settings` | Website-Einstellungen |
| `public_site_design` | Design-Konfiguration |
| `public_site_pages` | CMS-Seiten |
| `public_site_filter_config` | Such-Filter |
| `agency_domains` | Custom Domains |
| `tenant_branding` | Branding/Theming |

### Media & Kommunikation

| Tabelle | Zweck |
|---------|-------|
| `media_files` | Dateien |
| `media_folders` | Ordner |
| `media_audit_log` | Media-Audit |
| `email_outbox` | E-Mail Queue |
| `notifications` | — (via notifications Modul) |

### Kurtaxe

| Tabelle | Zweck |
|---------|-------|
| `visitor_tax_locations` | Kurtaxe-Standorte |
| `visitor_tax_periods` | Kurtaxe-Perioden |

### Infrastruktur

| Tabelle | Zweck |
|---------|-------|
| `audit_log` | Audit-Trail |
| `sync_logs` | Sync-Protokoll |
| `channel_connections` | Channel-Verbindungen |
| `channel_sync_logs` | Channel-Sync-Protokoll |
| `idempotency_keys` | Idempotenz-Schutz |
| `pms_schema_migrations` | Schema-Versions-Tracking |
| `user_sessions` | Session-Tracking |
| `web_vitals_metrics` | Frontend Performance |
| `webhooks` | Webhook-Konfiguration |
| `team_invites` | Team-Einladungen |
| `registration_forms` | Meldescheine |

## Migrationen

```
supabase/
  migrations/
    00000000000000_baseline.sql    # Konsolidierte Baseline (117 → 1)
    20260306..._*.sql              # Inkrementelle Migrationen
  scripts/
    *.sql                          # Utility/Cleanup Scripts
```

Ausfuehrung: Supabase SQL Editor oder `supabase db push`.
