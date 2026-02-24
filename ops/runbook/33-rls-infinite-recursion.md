# 33 — RLS Infinite Recursion (Bootstrap-Tabellen)

**Erstellt:** 2026-02-24
**Kategorie:** Datenbank / Sicherheit
**Schweregrad:** KRITISCH (verhindert Login/Zugriff)

---

## Übersicht

Dieses Kapitel dokumentiert das **RLS Infinite Recursion Problem** bei Multi-Tenant-Systemen und die korrekte Lösung mit SECURITY DEFINER Funktionen.

---

## Das Problem

### Symptom

Nach Aktivierung von RLS auf `team_members`:

```
ERROR: infinite recursion detected in policy for relation "team_members"
```

**Auswirkung:** Kompletter Systemausfall — kein User kann sich einloggen oder Daten abrufen.

### Ursache

Die `team_members`-Tabelle ist gleichzeitig:
- **Schutzobjekt** (braucht RLS)
- **Zugangskontrolle** (wird von anderen RLS-Policies referenziert)

```
┌─────────────────────────────────────────────────────────────┐
│                    RLS Policy Check                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User will auf "bookings" zugreifen                        │
│           │                                                 │
│           ▼                                                 │
│  Policy prüft: "agency_id IN (SELECT ... FROM team_members)"│
│           │                                                 │
│           ▼                                                 │
│  PostgreSQL: "Moment, team_members hat auch RLS!"          │
│           │                                                 │
│           ▼                                                 │
│  team_members Policy prüft: "agency_id IN (SELECT ...      │
│                              FROM team_members)"           │
│           │                                                 │
│           ▼                                                 │
│  PostgreSQL: "Moment, team_members hat auch RLS!"          │
│           │                                                 │
│           ▼                                                 │
│         ∞ ENDLOSSCHLEIFE                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Warum passiert das?

| Aspekt | Ursache? | Erklärung |
|--------|----------|-----------|
| **Logik** | Nein | Die RLS-Logik war korrekt (User sieht nur eigene Agency) |
| **Struktur** | **JA** | Multi-Tenant-Design mit `team_members` als zentrale Tabelle |
| **PostgreSQL-Verhalten** | **JA** | RLS wird bei JEDEM Subquery rekursiv geprüft |

---

## Die Lösung: SECURITY DEFINER Funktionen

### Konzept

SECURITY DEFINER Funktionen laufen mit den Rechten des **Funktions-Eigentümers** (postgres), nicht des aufrufenden Users. Dadurch wird RLS innerhalb der Funktion **umgangen**.

### Implementierte Helper-Funktionen

```sql
-- 1. Gibt alle agency_ids des aktuellen Users zurück
CREATE FUNCTION get_user_agency_ids()
RETURNS SETOF UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT agency_id
  FROM team_members
  WHERE user_id = auth.uid()
  AND is_active = true;
$$;

-- 2. Prüft ob User Zugriff auf eine Agency hat
CREATE FUNCTION user_has_agency_access(check_agency_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM team_members
    WHERE user_id = auth.uid()
    AND agency_id = check_agency_id
    AND is_active = true
  );
$$;

-- 3. Gibt die Rolle des Users in einer Agency zurück
CREATE FUNCTION get_user_role_in_agency(check_agency_id UUID)
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT role
  FROM team_members
  WHERE user_id = auth.uid()
  AND agency_id = check_agency_id
  AND is_active = true
  LIMIT 1;
$$;
```

### Vorher vs. Nachher

**FALSCH (verursacht Rekursion):**

```sql
CREATE POLICY "bookings_select" ON bookings
  FOR SELECT TO authenticated
  USING (
    agency_id IN (
      SELECT agency_id FROM team_members  -- ← RLS-Check auf team_members!
      WHERE user_id = auth.uid()
    )
  );
```

**RICHTIG (keine Rekursion):**

```sql
CREATE POLICY "bookings_select" ON bookings
  FOR SELECT TO authenticated
  USING (
    agency_id IN (SELECT get_user_agency_ids())  -- ← Funktion umgeht RLS
  );
```

---

## Sicherheitsaspekte

### Ist SECURITY DEFINER sicher?

**JA**, wenn korrekt implementiert. Unsere Implementierung erfüllt alle Anforderungen:

| Risiko | Mitigierung |
|--------|-------------|
| **Privilege Escalation** | Funktion gibt nur User-eigene agency_ids zurück via `auth.uid()` |
| **Unauthenticated Access** | `auth.uid()` gibt `NULL` für Nicht-Authentifizierte → leeres Ergebnis |
| **Search Path Injection** | `SET search_path = public` verhindert Schema-Hijacking |
| **SQL Injection** | Keine User-Inputs in Queries (nur `auth.uid()` als trusted Input) |
| **Data Leakage** | Minimale Rückgabe (nur UUIDs, keine vollen Records) |

### Best Practices für SECURITY DEFINER

1. **IMMER** `SET search_path = public` verwenden
2. **NIEMALS** User-Input direkt in SQL einbauen
3. **MINIMALE** Rückgabewerte (nur was nötig ist)
4. **STABLE** oder **IMMUTABLE** für Query-Optimierung
5. **GRANT EXECUTE** nur an `authenticated` Role

---

## Prävention: Wie vermeiden?

### Bei neuen Multi-Tenant-Projekten

```
┌─────────────────────────────────────────────────────────────┐
│  ARCHITEKTUR-REGEL                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Identifiziere die "Bootstrap-Tabelle" (team_members)   │
│  2. Erstelle SECURITY DEFINER Helper-Funktionen ZUERST     │
│  3. ALLE Policies nutzen diese Funktionen                  │
│  4. NIEMALS direkte Subqueries auf Bootstrap-Tabellen      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Reihenfolge bei RLS-Implementierung

1. **Zuerst:** Helper-Funktionen erstellen
2. **Dann:** RLS auf Bootstrap-Tabelle (team_members) mit Funktionen
3. **Zuletzt:** RLS auf alle anderen Tabellen mit Funktionen

### Code-Review Checklist

Bei jedem RLS-Policy Review prüfen:

- [ ] Enthält die Policy einen Subquery auf `team_members`?
- [ ] Falls ja: Wird stattdessen eine Helper-Funktion verwendet?
- [ ] Hat die Helper-Funktion `SECURITY DEFINER`?
- [ ] Hat die Helper-Funktion `SET search_path = public`?

---

## Verifikation

### Prüfen ob Funktionen existieren

```sql
-- Supabase SQL Editor
SELECT routine_name, routine_type, security_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'get_user_agency_ids',
    'user_has_agency_access',
    'get_user_role_in_agency'
  );
```

**Erwartete Ausgabe:**

| routine_name | routine_type | security_type |
|--------------|--------------|---------------|
| get_user_agency_ids | FUNCTION | DEFINER |
| user_has_agency_access | FUNCTION | DEFINER |
| get_user_role_in_agency | FUNCTION | DEFINER |

### Funktionstest

```sql
-- Als authentifizierter User ausführen
SELECT get_user_agency_ids();
-- Sollte agency_ids des Users zurückgeben

SELECT user_has_agency_access('your-agency-uuid');
-- Sollte true/false zurückgeben

SELECT get_user_role_in_agency('your-agency-uuid');
-- Sollte 'admin', 'manager', 'staff', etc. zurückgeben
```

### RLS-Policies prüfen

```sql
-- Alle Policies anzeigen die team_members referenzieren (sollte 0 sein)
SELECT schemaname, tablename, policyname, qual
FROM pg_policies
WHERE qual LIKE '%team_members%'
  AND qual NOT LIKE '%get_user_agency_ids%'
  AND qual NOT LIKE '%get_user_role_in_agency%';
```

**Erwartete Ausgabe:** Keine Zeilen (alle Policies nutzen Helper-Funktionen)

---

## Troubleshooting

### Problem: "infinite recursion detected"

**Symptom:** Fehler bei jedem Datenbankzugriff

**Diagnose:**

```sql
-- Finde die problematische Policy
SELECT tablename, policyname, qual
FROM pg_policies
WHERE qual LIKE '%team_members%';
```

**Fix:**

1. Policy identifizieren die Subquery auf team_members enthält
2. Helper-Funktion stattdessen verwenden
3. Policy neu erstellen

### Problem: "permission denied for function"

**Symptom:** Authentifizierte User können Funktion nicht aufrufen

**Fix:**

```sql
GRANT EXECUTE ON FUNCTION get_user_agency_ids() TO authenticated;
GRANT EXECUTE ON FUNCTION user_has_agency_access(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_role_in_agency(UUID) TO authenticated;
```

### Problem: Funktion gibt leeres Ergebnis

**Mögliche Ursachen:**

1. User ist nicht authentifiziert (`auth.uid()` = NULL)
2. User hat keine aktiven team_members Einträge
3. `is_active = false` bei allen Einträgen

**Diagnose:**

```sql
-- Prüfe ob User team_members hat
SELECT * FROM team_members WHERE user_id = auth.uid();
```

---

## Referenzen

- **Migration:** `supabase/migrations/20260224150000_fix_rls_infinite_recursion.sql`
- **Supabase Docs:** [Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)
- **PostgreSQL Docs:** [SECURITY DEFINER](https://www.postgresql.org/docs/current/sql-createfunction.html)

---

## Zusammenfassung

| Aspekt | Details |
|--------|---------|
| **Problem** | RLS auf Bootstrap-Tabelle verursacht Rekursion |
| **Lösung** | SECURITY DEFINER Helper-Funktionen |
| **Sicherheit** | Sicher bei korrekter Implementierung |
| **Prävention** | Helper-Funktionen ZUERST erstellen |
| **Status** | ✅ Implementiert (2026-02-24) |
