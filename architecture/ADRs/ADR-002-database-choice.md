# ADR-002: Datenbank — Supabase PostgreSQL mit RLS

**Status:** Accepted (implementiert)
**Datum:** 2025-12-21

---

## Entscheidung

**Supabase** (Managed PostgreSQL) mit **Row-Level Security** fuer Multi-Tenancy.

## Ist-Stand

| Eigenschaft | Wert |
|-------------|------|
| DB | PostgreSQL via Supabase |
| Tabellen | 58 |
| RLS | Aktiviert auf allen tenant-scoped Tabellen |
| Tenant-Spalte | `agency_id` (UUID) |
| Auth | Supabase Auth (JWT) |
| Migrationen | `supabase/migrations/` (raw SQL, Baseline-Konsolidierung) |

## RLS-Pattern (tatsaechlich implementiert)

```sql
-- Helper-Funktion: Gibt alle agency_ids des aktuellen Users zurueck
CREATE FUNCTION get_user_agency_ids() RETURNS SETOF UUID AS $$
  SELECT agency_id FROM team_members WHERE user_id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER;

-- RLS-Policy Pattern (alle tenant-scoped Tabellen)
CREATE POLICY "agency_isolation" ON bookings
  FOR ALL
  USING (agency_id IN (SELECT get_user_agency_ids()));
```

**Wichtig:** Tenant-Isolation laeuft ueber `agency_id`, NICHT `owner_id`.
Agencies sind die Mandanten (Ferienwohnungsverwaltungen), nicht einzelne Eigentuemer.

## Exclusion Constraint (Doppelbuchungsschutz)

```sql
-- Verhindert ueberlappende Buchungen pro Property
-- Nur aktive Status werden geprueft (confirmed, checked_in)
EXCLUDE USING gist (
    property_id WITH =,
    daterange(check_in, check_out, '[)') WITH &&
) WHERE (status IN ('confirmed', 'checked_in') AND deleted_at IS NULL);
```

## Migrations-Struktur

```
supabase/
  migrations/
    00000000000000_baseline.sql   # Konsolidierte Baseline (117 Migrationen → 1)
    20260306...                    # Inkrementelle Migrationen
  scripts/
    *.sql                         # Utility/Cleanup Scripts
```

## DB-Funktionen (Auswahl)

| Funktion | Zweck |
|----------|-------|
| `get_user_agency_ids()` | RLS: Agency-IDs des Users |
| `get_user_role_in_agency(uuid)` | Rolle in einer Agency |
| `get_user_permissions(uuid, uuid)` | Berechtigungen |
| `generate_booking_reference()` | Auto-Buchungsnummer |
| `encrypt_pii(text, text)` | PGP-Verschluesselung |
| `set_updated_at()` | Trigger fuer updated_at |
