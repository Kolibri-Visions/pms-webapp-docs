# 48 — RLS & Migrations-Konsolidierung

> Erstellt: 2026-03-06 | Phase 10 Security-Audit

## Zusammenfassung

117 einzelne SQL-Migrationen wurden in eine saubere Baseline-Migration konsolidiert.
Zusaetzlich wurden 3 Tabellen ohne RLS gefixt.

## Architektur

### Baseline-Migration

```
supabase/migrations/
  00000000000000_baseline.sql   ← Komplettes Schema (5.001 Zeilen)
  _archive/                     ← 117 historische Migrationen (Referenz)
  _TEMPLATE.sql                 ← Template fuer neue Migrationen
```

**Neue Migrationen** werden wie gewohnt mit Timestamp-Praefix erstellt:
```
supabase/migrations/20260307XXXXXX_beschreibung.sql
```

### RLS Auth-Patterns (4 Patterns in PROD)

| Pattern | Beschreibung | Tabellen | Beispiel |
|---------|-------------|----------|---------|
| A | JWT Claims (`auth.jwt()`) | 10 | amenities, visitor_tax_* |
| B | team_members Subquery | 22 | audit_log, extra_services |
| C | SECURITY DEFINER Functions | 14 | bookings, properties, guests |
| D | current_setting | 4 | block_templates, media_files |

**Ziel-Pattern ist C** (SECURITY DEFINER). Neue Tabellen sollten Pattern C verwenden.

### SECURITY DEFINER Helper-Functions

```sql
-- Gibt alle agency_ids des aktuellen Users zurueck
get_user_agency_ids() RETURNS SETOF uuid

-- Gibt die Rolle des Users in einer Agency zurueck
get_user_role_in_agency(check_agency_id uuid) RETURNS text

-- Prueft ob User Zugang zu einer Agency hat
user_has_agency_access(check_agency_id uuid) RETURNS boolean
```

Alle mit `SECURITY DEFINER` + `SET search_path TO 'public'`.

## Wichtig: service_role umgeht RLS

Das Backend nutzt immer `service_key` (service_role) fuer Supabase-Zugriff.
RLS schuetzt **nur** gegen direkten Client-Zugriff mit anon/authenticated JWTs.

## Tabellen ohne RLS (beabsichtigt)

| Tabelle | Grund |
|---------|-------|
| pms_schema_migrations | Meta-Tabelle, kein User-Zugriff |

## Operationen

### Neue Migration erstellen

```bash
# Timestamp generieren
date +%Y%m%d%H%M%S
# Datei erstellen
touch supabase/migrations/YYYYMMDDHHMMSS_beschreibung.sql
```

### Verifikation ausfuehren

Im Supabase SQL-Editor `supabase/verify-rls.sql` ausfuehren.
Erwartete Werte: 57/58 RLS enabled, 190+ Policies.

### Baseline auf bestehender PROD-DB registrieren

```sql
-- Einmalig im SQL-Editor ausfuehren:
-- supabase/scripts/mark_baseline_applied.sql
```

### Fresh-Deploy (neue DB)

Nur `00000000000000_baseline.sql` wird ausgefuehrt.
Enthaelt das komplette Schema inkl. aller RLS-Policies.

## Referenzen

- Baseline: `supabase/migrations/00000000000000_baseline.sql`
- RLS-Referenz: `supabase/rls-policies.sql`
- Verifikation: `supabase/verify-rls.sql`
- PROD-Fix: `supabase/migrations/_archive/20260306220000_enable_rls_media_audit_agency_domains.sql`
- Audit-CSVs (lokal): `DB SQL/10_1_*.csv`
