# ADR-003: Multi-Tenancy — Agency-basiert mit dreifacher Absicherung

**Status:** Accepted (implementiert)
**Datum:** 2025-12-21

---

## Entscheidung

**Agency-basierte Multi-Tenancy** mit dreifacher Absicherung:
1. RLS-Policies (Datenbank-Ebene)
2. Service-Layer agency_id Checks (Applikations-Ebene)
3. JWT-basierte Agency-Zuordnung (Auth-Ebene)

## Tenant-Modell

| Begriff | Bedeutung |
|---------|-----------|
| **Agency** | Mandant (Ferienwohnungsverwaltung) |
| **Team Member** | Benutzer mit Rolle in einer Agency |
| **Role** | Berechtigungsgruppe (admin, manager, staff, owner, accountant) |

Ein User kann **mehreren Agencies** angehoeren (ueber `team_members` Tabelle).

## Absicherungs-Ebenen

### Ebene 1: RLS (Datenbank)

```sql
-- Jede tenant-scoped Tabelle hat agency_id + RLS Policy
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "agency_isolation" ON bookings
  FOR ALL
  USING (agency_id IN (SELECT get_user_agency_ids()));
```

### Ebene 2: Service-Layer

```python
# Jeder Service-Aufruf filtert explizit nach agency_id
async def list_bookings(self, agency_id: UUID, **kwargs):
    rows = await self.db.fetch(
        "SELECT * FROM bookings WHERE agency_id = $1",
        agency_id
    )
```

### Ebene 3: Auth/JWT

```python
# Route-Dependencies pruefen Agency-Zugehoerigkeit
@router.get("/bookings")
async def list_bookings(
    user=Depends(get_current_user),
    agency_id: UUID = Depends(require_agency_access),
):
    ...
```

## Tabellen-Struktur

Alle tenant-scoped Tabellen haben:
- `agency_id UUID NOT NULL` — FK zu agencies
- RLS Policy mit `get_user_agency_ids()` Check
- Index auf `agency_id`

Ausnahmen (kein agency_id):
- `profiles` — User-Profildaten (via auth.uid())
- `agencies` — Die Agencies selbst
- `permission_definitions` — Globale Berechtigungsdefinitionen

## Rollen-System

```
agencies
  └── roles (pro Agency definierbar)
       └── role_permissions (N:M zu permission_definitions)

team_members (User ↔ Agency ↔ Role)
```

Standard-Rollen: `admin`, `manager`, `staff`, `owner`, `accountant`
