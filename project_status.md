# PMS-Webapp Project Status

**Last Updated:** 2026-02-24

**Current Phase:** Phase 27 - Codebase Audit & Logic Bug Fixes Phase 2

---

## Bug Fixes - Kritische Validierungen (2026-02-24) - IMPLEMENTED

**Scope**: Behebung kritischer Bugs aus PMS-Audit (#1, #3-#6).

### Bug #1: Doppelbuchungen (Race Condition)

**Problem**: `update_booking_status()` hatte keinen Advisory Lock. Bei gleichzeitiger Bestätigung zweier Anfragen für dieselben Daten konnte eine Race Condition auftreten.

**Szenario**:
```
Thread 1: inquiry → confirmed (liest Status, validiert, bestätigt)
Thread 2: inquiry → confirmed (liest Status, validiert, bestätigt)
→ Beide sehen "inquiry", beide versuchen zu bestätigen
```

**Lösung**:
- Advisory Lock `pg_advisory_xact_lock` zu `update_booking_status()` hinzugefügt
- Lock wird auf Property-ID gesetzt (serialisiert alle Status-Änderungen pro Property)
- Status wird NACH Lock-Erwerb erneut geprüft (Double-Check Pattern)

**Datei**: `backend/app/services/booking_service.py`

**Vorher**: ⚠️ Teilweise geschützt (nur DB-Constraint)
**Nachher**: ✅ Vollständig geschützt (Lock + Constraint)

### Bug #3: Kurtaxe ignoriert Altersgrenze

**Problem**: `free_under_age` Feld in `visitor_tax_periods` wurde nicht in der Berechnung verwendet.

**Lösung**:
- Neues Feld `children_taxable` in `QuoteRequest` Schema
- Erlaubt explizite Angabe wie viele Kinder über der Altersgrenze sind
- Validator: `children_taxable <= children`

**Dateien**:
- `backend/app/schemas/pricing.py` - Neues Feld + Validator
- `backend/app/api/routes/pricing.py` - Berechnung aktualisiert

### Bug #4: Timezone-naive Datetimes

**Problem**: `datetime.utcnow()` erzeugt naive Timestamps ohne Timezone-Info.

**Lösung**: Alle 30 Vorkommen im gesamten Backend durch `datetime.now(timezone.utc)` ersetzt.

**Betroffene Dateien**:
| Datei | Anzahl |
|-------|--------|
| `backend/app/services/booking_service.py` | 8 |
| `backend/app/api/routes/booking_requests.py` | 14 |
| `backend/app/core/auth.py` | 3 |
| `backend/app/api/routers/channel_connections.py` | 2 |
| `backend/app/services/channel_connection_service.py` | 1 |
| `backend/app/services/guest_service.py` | 1 |
| `backend/app/api/routes/notifications.py` | 1 |

### Bug #5: Fehlende max_guests Validierung

**Problem**: Gästeanzahl wurde nicht gegen `properties.max_guests` validiert.

**Lösung**:
- `max_guests` zu Property-Queries hinzugefügt
- Validierung in `create_booking()` und `update_booking()` implementiert
- Fehlermeldung: "Gästeanzahl (X) überschreitet die maximale Kapazität (Y Gäste)"

**Datei**: `backend/app/services/booking_service.py`

### Bug #6: 0-Nacht-Buchung möglich

**Status**: ✅ Bereits abgesichert

**Analyse**: Pydantic-Validator in `BookingBase` (Zeile 92-98) erzwingt `check_out > check_in`.

### Verification Path

```bash
# Bug #3: Kurtaxe mit children_taxable
curl -X POST "${API}/api/v1/pricing/quote" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"property_id":"...", "check_in":"2026-03-01", "check_out":"2026-03-03", "adults":2, "children":2, "children_taxable":1}'

# Bug #5: Überbuchung sollte 422 Fehler liefern
curl -X POST "${API}/api/v1/bookings" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"property_id":"...", "num_adults":10, "num_children":10}'  # > max_guests
```

**Status**: ✅ IMPLEMENTED

---

## Logic Bug Fixes - Berechnungs- und Validierungsfehler (2026-02-24) - IMPLEMENTED

**Scope**: Behebung von Logikfehlern bei Preis- und Rückerstattungsberechnungen.

### Übersicht der Fixes

| # | Problem | Datei | Fix |
|---|---------|-------|-----|
| L1 | Refund-Berechnung trunciert statt rundet | `booking_service.py` | `ROUND_HALF_UP` verwenden |
| L2 | Preis-Konvertierung (€→Cents) trunciert | `booking_service.py` | `ROUND_HALF_UP` verwenden |
| L3 | Refund auf 0€-Buchung erlaubt | `booking_service.py` | ValidationException werfen |
| L4 | Fee-Berechnung bei fehlenden Werten silent | `pricing_totals.py` | Warnings loggen |

### L1: Refund-Rundungsfehler

**Vorher (falsch):**
```python
refund_amount_cents = int(total_price_cents * refund_percent / 100)
# 9999 × 12% = 1199.88 → int() = 1199 cents
```

**Nachher (korrekt):**
```python
refund_decimal = (Decimal(total_price_cents) * Decimal(refund_percent)) / Decimal("100")
refund_amount_cents = int(refund_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
# 9999 × 12% = 1199.88 → ROUND_HALF_UP = 1200 cents
```

### L2: Preis-Konvertierung

**Vorher:** `int(Decimal(price) * 100)` - trunciert bei 99.995 → 9999
**Nachher:** `quantize(Decimal("1"), rounding=ROUND_HALF_UP)` - rundet zu 10000

### L3: Validierung bei fehlender Buchungssumme

**Neu:** Wenn `total_price_cents = 0`, wird eine `ValidationException` geworfen statt Refund auf 0€ zu berechnen.

### L4: Fee-Berechnungen mit Warnings

**Neu:** Wenn `per_stay`, `per_night` oder `per_person` Fees keine `value_cents` haben, wird ein Warning geloggt statt silent 0 zu berechnen.

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/services/booking_service.py` | ROUND_HALF_UP Import, Refund/Preis-Rundung, Validierung |
| `backend/app/services/pricing_totals.py` | Fee-Validierung mit Warnings |

**Status**: ✅ IMPLEMENTED

---

## Logic Bug Fixes Phase 2 - Codebase Audit (2026-02-24) - IMPLEMENTED

**Scope**: Umfassende Code-Analyse und Behebung weiterer Logikfehler.

### Übersicht der Fixes

| # | Schweregrad | Problem | Datei | Fix |
|---|-------------|---------|-------|-----|
| K1 | KRITISCH | Commission-Berechnung trunciert | `owners.py:944` | `ROUND_HALF_UP` verwenden |
| K2 | KRITISCH | Altersberechnung falsch (`days // 365`) | `guests.py:185` | Korrekte Datum-basierte Berechnung |
| H1 | HOCH | List.remove() kann ValueError werfen | `registry.py:80` | Existenz-Prüfung vor remove |
| H2 | HOCH | SQL f-Strings statt Parametern | `booking_requests.py` | Parameterisierte Queries |
| M1 | MITTEL | Type Coercion bei Geldwerten | `owners.py:942-943` | Explizite None-Prüfung |

### K1: Commission-Rundungsfehler

**Vorher (falsch):**
```python
commission_cents = int(gross_total_cents * commission_rate_bps / 10000)
# 10001 × 500 / 10000 = 500.05 → int() = 500 cents (sollte 500 sein, aber 500.5 → 501)
```

**Nachher (korrekt):**
```python
commission_decimal = (Decimal(str(gross_total_cents)) * Decimal(str(commission_rate_bps))) / Decimal("10000")
commission_cents = int(commission_decimal.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
```

### K2: Altersberechnungsfehler

**Vorher (falsch):**
```python
age = (date.today() - v).days // 365
# 01.01.2000 bis 01.01.2025 = 9131 Tage / 365 = 24 Jahre (FALSCH! Sollte 25 sein)
```

**Nachher (korrekt):**
```python
age = today.year - v.year
if (today.month, today.day) < (v.month, v.day):
    age -= 1  # Geburtstag noch nicht erreicht
```

### H1: Registry Safe Remove

**Vorher:** `.remove()` konnte `ValueError` werfen wenn Element nicht in Liste
**Nachher:** Existenz-Prüfung vor `remove()` + `.pop(key, None)` statt `.pop(key)`

### H2: SQL Parameterisierung

**Vorher (Anti-Pattern):**
```python
where_clauses.append(f"b.status IN ('{DB_STATUS_REQUESTED}', '{DB_STATUS_INQUIRY}')")
```

**Nachher (Best Practice):**
```python
where_clauses.append(f"b.status IN (${param_idx}, ${param_idx + 1})")
params.extend([DB_STATUS_REQUESTED, DB_STATUS_INQUIRY])
param_idx += 2
```

### Dateien

| Datei | Änderung |
|-------|----------|
| `backend/app/api/routes/owners.py` | ROUND_HALF_UP Import, Commission-Berechnung, None-Handling |
| `backend/app/schemas/guests.py` | Korrekte Altersberechnung |
| `backend/app/modules/registry.py` | Safe remove Pattern |
| `backend/app/api/routes/booking_requests.py` | 4× SQL-Parameter statt f-Strings |

**Status**: ✅ IMPLEMENTED

---

## Cancellation Policies - Stornierungsfrist-Logik (2026-02-24) - IMPLEMENTED

**Feature**: Konfigurierbare Stornierungsregeln mit automatischer Rückerstattungsberechnung.

**Navigation**: Unter "Objekte" (nicht "Einstellungen") - Pfad `/cancellation-rules`

### Übersicht

- **Agency-Level**: Custom Regeln (Tage vor Check-in → Rückerstattung%)
- **Property-Level**: Optional eigene Regel oder Agency-Default verwenden
- **Booking-Level**: Automatische Rückerstattungsberechnung bei Stornierung

### Neue Tabelle: `cancellation_policies`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | UUID | Primary Key |
| `agency_id` | UUID | FK zu agencies |
| `name` | VARCHAR(100) | Name der Regel (z.B. "Standard", "Flexibel") |
| `is_default` | BOOLEAN | Ist Default für Agency |
| `rules` | JSONB | Array von `{days_before, refund_percent}` |

### Properties-Erweiterung

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `cancellation_policy_id` | UUID | FK zu cancellation_policies |
| `use_agency_default_cancellation` | BOOLEAN | true = Agency-Default verwenden |

### API Endpoints

| Method | Endpoint | Beschreibung | Rollen |
|--------|----------|--------------|--------|
| GET | `/api/v1/cancellation-policies` | Liste aller Policies | staff+ |
| POST | `/api/v1/cancellation-policies` | Neue Policy erstellen | manager+ |
| GET | `/api/v1/cancellation-policies/{id}` | Policy Details | staff+ |
| PATCH | `/api/v1/cancellation-policies/{id}` | Policy bearbeiten | manager+ |
| DELETE | `/api/v1/cancellation-policies/{id}` | Policy löschen | admin |
| GET | `/api/v1/bookings/{id}/calculate-refund` | Refund berechnen | staff+ |

### Frontend-Seiten

| Seite | Beschreibung |
|-------|--------------|
| `/cancellation-rules` | Stornierungsregeln verwalten (CRUD) - unter "Objekte" in Navigation |
| `/properties` (Create Modal) | Stornierungsregel-Auswahl bei neuen Objekten |
| `/properties/[id]` (Edit Modal) | Abschnitt "Stornierungsregeln" mit Radio-Auswahl |
| `/bookings/[id]` (Cancel Modal) | Automatische Refund-Berechnung mit Override-Option |

### Dateien

| Bereich | Datei | Aktion |
|---------|-------|--------|
| Migration | `supabase/migrations/20260224000000_add_cancellation_policies.sql` | NEU |
| Backend | `backend/app/schemas/cancellation_policies.py` | NEU |
| Backend | `backend/app/schemas/properties.py` | Erweitert |
| Backend | `backend/app/api/routes/cancellation_policies.py` | NEU |
| Backend | `backend/app/api/routes/bookings.py` | calculate-refund Endpoint |
| Backend | `backend/app/services/booking_service.py` | calculate_refund() Methode |
| Frontend | `frontend/app/types/cancellation.ts` | NEU |
| Frontend | `frontend/app/types/property.ts` | Erweitert |
| Frontend | `frontend/app/cancellation-rules/page.tsx` | NEU (CRUD UI) |
| Frontend | `frontend/app/cancellation-rules/layout.tsx` | NEU (Auth-Layout) |
| Frontend | `frontend/app/properties/page.tsx` | Create Modal erweitert |
| Frontend | `frontend/app/properties/[id]/page.tsx` | Edit Modal erweitert |
| Frontend | `frontend/app/bookings/[id]/page.tsx` | Cancel Modal erweitert |
| Frontend | `frontend/app/components/AdminShell.tsx` | Navigation aktualisiert |
| Frontend | `frontend/app/components/Breadcrumb.tsx` | Breadcrumb-Labels |

### Verification Path

```bash
# 1. DB Migration anwenden
supabase db push

# 2. Backend starten und API testen
curl -X POST /api/v1/cancellation-policies \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Standard","is_default":true,"rules":[{"days_before":14,"refund_percent":100},{"days_before":7,"refund_percent":50},{"days_before":0,"refund_percent":0}]}'

# 3. Frontend prüfen
# - /cancellation-rules → Regeln erstellen/bearbeiten (unter "Objekte" in Nav)
# - /properties → Create Modal → Stornierungsregel auswählen
# - /properties/[id] → Edit Modal → Stornierungsregeln-Abschnitt
# - /bookings/[id] → Stornieren → Refund-Berechnung prüfen
```

**Status**: ✅ IMPLEMENTED

---

## Table-to-Card Responsive Pattern - Alle Admin-Listen (2026-02-23) - IMPLEMENTED

**Feature**: Responsive Table-to-Card Pattern gemäß CLAUDE.md §10 auf alle verbleibenden Admin-Listen angewendet.

### Bearbeitete Seiten

| Phase | Seite | Beschreibung |
|-------|-------|--------------|
| 1 | `/extra-services` | Zusatzleistungen mit Checkbox-Selektion |
| 1 | `/guests` | Gästeliste mit VIP/Gesperrt-Badges |
| 1 | `/owners` | Eigentümerliste mit DAC7-Export-Button |
| 1 | `/team` | Teammitglieder + Einladungen (2 Tabellen) |
| 1 | `/seasons` | Saisonvorlagen mit erweiterbaren Perioden |
| 1 | `/bookings` | Buchungsliste mit Status-Badges |
| 2 | `/notifications/email-outbox` | E-Mail Outbox mit Status-Anzeige |
| 2 | `/connections` | Channel-Manager-Verbindungen |
| 2 | `/channel-sync` | Sync-Logs mit Batch-Links |
| 2 | `/website/pages` | Website-Seiten mit Template-Badges |
| 3 | `/ops/modules` | Backend-Module mit Tags/Prefixes |
| 3 | `/ops/audit-log` | Audit-Log mit Aktions-Badges |

### Implementierung

- **Desktop (md+)**: Tabellen-Layout mit `hidden md:block`
- **Mobile (<md)**: Karten-Layout mit `block md:hidden`
- **Breakpoint**: 768px (Tailwind `md`)
- **Actions**: Alle Aktionen in beiden Layouts verfügbar

### Verification Path

```bash
# Responsive-Test: Browser-DevTools → Responsive Mode
# Alle Seiten bei 375px und 1280px Breite prüfen

# Betroffene URLs:
# /extra-services, /guests, /owners, /team
# /seasons, /bookings, /notifications/email-outbox
# /connections, /channel-sync, /website/pages
# /ops/modules, /ops/audit-log
```

**Referenz:** CLAUDE.md §10 - Responsive UI Design Pattern

**Status**: ✅ IMPLEMENTED

---

## Owner DAC7 Compliance & Edit Modal (2026-02-23) - IMPLEMENTED

**Feature**: DAC7-Richtlinie Compliance für Eigentümer (EU-Steuertransparenz) mit vollständigem Edit Modal.

### Änderungen

#### 1. DAC7 Pflichtfelder (Migration)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `tax_id` | TEXT | Steuer-ID (11-stellig für DE) |
| `birth_date` | DATE | Geburtsdatum (DAC7-Pflicht) |
| `vat_id` | TEXT | USt-IdNr. (für Gewerbetreibende) |

#### 2. Banking-Felder (für Auszahlungen)

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `iban` | TEXT | IBAN |
| `bic` | TEXT | BIC/SWIFT |
| `bank_name` | TEXT | Bankname |

#### 3. Strukturierte Adresse

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `street` | TEXT | Straße + Hausnummer |
| `postal_code` | TEXT | PLZ |
| `city` | TEXT | Ort |
| `country` | TEXT | Land (ISO 3166-1, Default: DE) |

### Dateien

| Bereich | Datei | Änderung |
|---------|-------|----------|
| Migration | `supabase/migrations/20260223000000_add_owner_dac7_fields.sql` | Neue Spalten |
| Backend | `backend/app/schemas/owners.py` | Schemas erweitert |
| Backend | `backend/app/api/routes/owners.py` | CRUD-Endpoints erweitert |
| Frontend | `frontend/app/types/owner.ts` | TypeScript-Interface erweitert |
| Frontend | `frontend/app/owners/[ownerId]/page.tsx` | Detail-Seite + Edit Modal |

### Owner Edit Modal (Drawer-Style)

- Gleitet von rechts ein (Desktop) / von unten (Mobile)
- Sektionen: Name & Kontakt, Steuer & DAC7, Adresse, Bankverbindung, Provision & Status, Notizen
- PATCH auf `/api/v1/owners/{ownerId}`
- Auto-Refresh nach Speichern

### Verification Path

```bash
# 1. Owner Detail-Seite öffnen
# → /owners/{ownerId} zeigt alle DAC7-Felder

# 2. Edit Modal öffnen
# → "Bearbeiten" Button → Drawer öffnet sich
# → Alle Felder ausfüllen → "Änderungen speichern"

# 3. API-Test
curl -X PATCH "${API}/api/v1/owners/${OWNER_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tax_id": "12345678901",
    "birth_date": "1980-01-15",
    "iban": "DE89370400440532013000"
  }'
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 5: DAC7 Compliance)

**Status**: ✅ IMPLEMENTED

---

## DSGVO Datenexport (Art. 15 Auskunftsrecht) (2026-02-23) - IMPLEMENTED

**Feature**: Eigentümer können alle ihre personenbezogenen Daten exportieren (DSGVO Art. 15).

### Endpoint

`GET /api/v1/owner/me/export`

### Exportierte Daten

| Kategorie | Beschreibung |
|-----------|--------------|
| Stammdaten | Name, E-Mail, Telefon |
| Steuerdaten (DAC7) | tax_id, birth_date, vat_id |
| Adressdaten | street, postal_code, city, country |
| Bankverbindung | iban, bic, bank_name |
| Objektzuweisungen | Alle zugewiesenen Properties |
| Buchungsdaten | Buchungen für eigene Objekte |
| Abrechnungen | Finanzielle Statements |

### Dateien

| Bereich | Datei | Änderung |
|---------|-------|----------|
| Backend Schema | `backend/app/schemas/owners.py` | `OwnerDataExportResponse` + Hilfs-Schemas |
| Backend Route | `backend/app/api/routes/owners.py` | `GET /owner/me/export` Endpoint |

### Query Parameter

- `format=json` (default): JSON-Response
- `format=download`: Datei-Download als `.json`

### Verification Path

```bash
# Als eingeloggter Owner:
curl -X GET "${API}/api/v1/owner/me/export" \
  -H "Authorization: Bearer $OWNER_TOKEN"

# Als Download:
curl -X GET "${API}/api/v1/owner/me/export?format=download" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -o dsgvo_export.json
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 6: DSGVO Datenexport)

**Status**: ✅ IMPLEMENTED

---

## Strukturierte Adress-Migration (2026-02-23) - IMPLEMENTED

**Feature**: Migration von Legacy-`address` Feld zu strukturierten Feldern (street, postal_code, city, country).

### Migrationsskript

**Datei:** `backend/scripts/migrate_owner_addresses.sql`

### Ablauf

1. **Preview** (Step 1): Zeigt betroffene Owners
2. **Parse Preview** (Step 2): Zeigt was geparst würde
3. **Execute** (Step 3): Führt Migration aus (manuell auskommentieren)
4. **Verify** (Step 4): Zeigt Migrationsergebnis

### Unterstützte Formate

- Format A: `"Straße 123, 12345 Stadt"`
- Format B: `"Straße 123\n12345 Stadt"`

### Verification Path

```bash
# In Supabase SQL Editor:
# 1. Öffne backend/scripts/migrate_owner_addresses.sql
# 2. Führe Step 1 + 2 aus (Preview)
# 3. Prüfe Ergebnisse
# 4. Führe Step 3 aus (Migration)
# 5. Führe Step 4 aus (Verify)
```

**Status**: ✅ IMPLEMENTED

---

## GDPR Hard Delete / Anonymisierung (2026-02-23) - IMPLEMENTED

**Feature**: DSGVO Art. 17 - Recht auf Löschung ("Recht auf Vergessenwerden").

### Endpoint

`DELETE /api/v1/owners/{id}/gdpr-delete?confirm=true`

### Was wird anonymisiert

| Kategorie | Felder | Neuer Wert |
|-----------|--------|------------|
| Identität | first_name, last_name | "GELÖSCHT" |
| Kontakt | email | `deleted_xxx@anonymized.local` |
| Kontakt | phone | NULL |
| Adresse | address, street, postal_code, city, country | NULL |
| Steuerdaten | tax_id, vat_id, birth_date | NULL |
| Banking | iban, bic, bank_name | NULL |

### Was bleibt erhalten (Buchhaltung)

- Owner-ID (für Statement-Referenzen)
- commission_rate_bps (historisch)
- Statement-Records (nur Beträge, keine PII)

### Voraussetzungen

1. Owner muss **deaktiviert** sein (erst `DELETE /owners/{id}`)
2. Owner darf **keine Properties** zugewiesen haben
3. Nur **Admin-Rolle** kann ausführen
4. `confirm=true` erforderlich (Sicherheitscheck)

### Verification Path

```bash
# 1. Erst soft-delete
curl -X DELETE "${API}/api/v1/owners/${OWNER_ID}" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 2. Dann GDPR-Delete
curl -X DELETE "${API}/api/v1/owners/${OWNER_ID}/gdpr-delete?confirm=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 8: GDPR Hard Delete)

**Status**: ✅ IMPLEMENTED

---

## DAC7 XML-Export für Finanzamt (2026-02-23) - IMPLEMENTED

**Feature**: XML-Export im OECD DPI-Format für die Meldung an Finanzbehörden gemäß EU DAC7-Richtlinie.

### Endpoint

`GET /api/v1/dac7/export?year=2025`

### XML-Struktur (OECD DPI Schema)

| Element | Beschreibung |
|---------|--------------|
| `MessageSpec` | Metadaten (SendingEntity, Timestamp, ReportingPeriod) |
| `PlatformOperator` | Agency-Daten (Name, Adresse, Land) |
| `ReportableSeller` | Pro Owner mit Properties und Umsätzen |
| `ImmovableProperty` | Objekt-Typ (DPI903) mit Adressen |
| `Consideration` | Quartalweise Umsätze + Jahressumme |

### Exportierte Owner-Daten

| Kategorie | Felder |
|-----------|--------|
| Identität | first_name, last_name |
| Steuer-ID | tax_id (TIN), vat_id |
| Geburtsdatum | birth_date |
| Adresse | street, postal_code, city, country |

### Finanzielle Daten

- Quartalweise Aufschlüsselung (Q1-Q4)
- Umsatz pro Quartal (in EUR)
- Anzahl Aktivitäten (Buchungen)
- Jahressumme

### Voraussetzungen

1. Nur **Admin-Rolle** kann exportieren
2. Owner muss **is_active = true** sein
3. Owner muss mindestens **ein Property** haben
4. Properties müssen **Buchungen im Berichtsjahr** haben

### Verification Path

```bash
# DAC7 XML-Export für 2025 erstellen
curl -X GET "${API}/api/v1/dac7/export?year=2025" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -o DAC7_Report_2025.xml

# XML validieren (Schema-Check)
xmllint --noout DAC7_Report_2025.xml
```

**Runbook:** [12-owner-management-pro.md](./ops/runbook/12-owner-management-pro.md) (Sektion 9: DAC7 XML-Export)

**Status**: ✅ IMPLEMENTED

---

## DAC7 Export UI auf /owners (2026-02-23) - IMPLEMENTED

**Feature**: Admin-UI für DAC7 XML-Export direkt auf der Eigentümer-Seite.

### UI-Komponenten

| Element | Beschreibung |
|---------|--------------|
| Export-Button | "DAC7 Export" Button im Header (nur für Admin sichtbar) |
| Modal | Jahr-Auswahl + Info-Box + Download-Button |
| Feedback | Erfolgs-/Fehlermeldungen im Modal |

### Funktionen

- Nur für **Admin-Rolle** sichtbar (`getUserRole(user) === "admin"`)
- Jahr-Dropdown (2024 bis aktuelles Jahr)
- Zeigt Meldefrist an (31. Januar Folgejahr)
- Download als XML-Datei

### Dateien

| Datei | Änderung |
|-------|----------|
| `frontend/app/owners/page.tsx` | DAC7 Export Button + Modal |

### Verification Path

```bash
# 1. Als Admin einloggen
# 2. /owners öffnen
# 3. "DAC7 Export" Button klicken
# 4. Jahr auswählen → "XML herunterladen"
```

**Status**: ✅ IMPLEMENTED

---

## Immutable Objekt-ID (internal_name) (2026-02-23) - IMPLEMENTED

**Feature**: `internal_name` (Objekt-ID) ist nach Erstellung unveränderlich.

### Änderungen

- `internal_name` aus `allowed_fields` in `property_service.py` entfernt
- Auto-Generierung bei Erstellung: `OBJ-XXX` Format
- Migration für bestehende Properties mit leerem internal_name

**Dateien:**
- `backend/app/services/property_service.py`
- `backend/scripts/migrate_internal_names.sql`

**Status**: ✅ IMPLEMENTED

---

## Login Redirect zu /dashboard (2026-02-23) - IMPLEMENTED

**Feature**: Nach Login wird zu `/dashboard` statt `/channel-sync` weitergeleitet.

**Datei:** `frontend/app/login/page.tsx`

**Status**: ✅ IMPLEMENTED

---

## Fees/Taxes Umstrukturierung (Template-basiert) (2026-02-21) - IMPLEMENTED

**Feature**: Umstellung der Gebühren-/Steuerverwaltung auf Template-basiertes System. `/gebuehren-steuern` wird zur Agency-Level Template-Verwaltung, Property-Zuweisung erfolgt unter `/properties/[id]/gebuehren`.

### Architektur

| Seite | Zweck |
|-------|-------|
| `/gebuehren-steuern` | Agency-weite Fee/Tax-Templates definieren |
| `/properties/[id]/gebuehren` | Property-spezifische Fees/Templates zuweisen |

### Datenmodell

```
Agency-Template (property_id = NULL)
        ↓ "Zuweisen" = Kopie erstellen
Property-Fee (property_id = {uuid}, source_template_id = {template})
```

- **Fees**: Template + Kopie-Modell (Property bekommt eigene Kopie)
- **Steuern**: Nur Agency-Level (keine Property-spezifischen Steuern)

### Backend-Änderungen

| Datei | Änderung |
|-------|----------|
| `backend/app/schemas/pricing.py` | Neue Schemas: `PricingFeeTemplateResponse`, `AssignFeeFromTemplateRequest` |
| `backend/app/api/routes/pricing.py` | Neue Endpoints (siehe unten) |
| `supabase/migrations/20260221000000_add_pricing_fees_source_template.sql` | Neue Spalte `source_template_id` |

### Neue API Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /api/v1/pricing/fees/templates` | Nur Agency-Templates mit usage_count |
| `DELETE /api/v1/pricing/fees/{fee_id}` | Template löschen (nur wenn nicht verwendet) |
| `GET /api/v1/pricing/properties/{id}/fees` | Property-Fees mit source_template_name |
| `POST /api/v1/pricing/properties/{id}/fees/from-template` | Fee aus Template zuweisen |
| `DELETE /api/v1/pricing/properties/{id}/fees/{fee_id}` | Property-Fee entfernen |

### Frontend-Änderungen

| Datei | Änderung |
|-------|----------|
| `frontend/app/gebuehren-steuern/page.tsx` | Neue Template-Verwaltungsseite (kein Property-Dropdown) |
| `frontend/app/properties/[id]/gebuehren/page.tsx` | Neue Property-Gebühren-Seite |
| `frontend/app/properties/[id]/layout.tsx` | Neuer Tab "Gebühren" |
| `frontend/app/pricing/page.tsx` | Redirect zu `/gebuehren-steuern` |
| `frontend/app/components/AdminShell.tsx` | Navigation: `/pricing` → `/gebuehren-steuern` |

### Features

- **Template-Verwaltung**: Gebühren-Vorlagen auf Agency-Level erstellen
- **"Verwendet in X Objekte"**: Zeigt Usage-Count pro Template
- **Property-Zuweisung**: Templates kopieren oder eigene Gebühren erstellen
- **Quelle-Badge**: "Vorlage" vs "Manuell" auf Property-Seite
- **Table-to-Card**: Responsive Pattern gemäß CLAUDE.md §10
- **Steuern read-only**: Agency-weite Steuern auf Property-Seite anzeigen

### Verification Path

```bash
# 1. Templates-Seite
# → /gebuehren-steuern zeigt nur Agency-Templates
# → Kein Property-Dropdown mehr
# → "Verwendet in X Objekte" Spalte

# 2. Property-Seite
# → /properties/{id}/gebuehren zeigt:
#    - Zugewiesene Templates (mit "Vorlage" Badge)
#    - Property-spezifische Fees (mit "Manuell" Badge)
# → Template zuweisen funktioniert
# → Custom Fee erstellen funktioniert

# 3. Navigation
# → Sidebar zeigt "Gebühren & Steuern" → /gebuehren-steuern
# → /pricing redirected zu /gebuehren-steuern
```

**Status**: ✅ IMPLEMENTED

---

## Properties Table-to-Card Responsive UI (2026-02-21) - IMPLEMENTED

**Feature**: Responsive Table-to-Card Pattern für `/properties` Seite gemäß CLAUDE.md §10.

### Änderungen

| Bereich | Desktop (md+) | Mobile (<md) |
|---------|---------------|--------------|
| Objekt-Liste | Tabelle mit allen Spalten | Kompakte Karten |
| Header | Horizontal mit Buttons | Vertikal, Buttons full-width |
| Pagination | Inline | Gestapelt |
| Aktionen | 3-Dot-Menü | Text-Links im Card-Footer |

**Dateien**: `frontend/app/properties/page.tsx`

**Status**: ✅ IMPLEMENTED

---

## Season-Only Min Stay (2026-02-21) - IMPLEMENTED

**Feature**: Eliminierung von `properties.min_stay` und Umstellung auf `rate_plan_seasons.min_stay_nights` als einzige Quelle für Mindestaufenthalt.

### Fallback-Hierarchie

```
1. rate_plan_seasons.min_stay_nights  (Saison für Check-in-Datum)
   ↓ falls NULL oder keine Saison
2. rate_plans.min_stay_nights         (Rate-Plan Default)
   ↓ falls NULL
3. Hard-Default: 1 Nacht              (kein Minimum)
```

**Status**: ✅ IMPLEMENTED

---

## Rate-Plans Table-to-Card Redesign (2026-02-20) - IMPLEMENTED

**Feature**: Komplettes Redesign der Preiseinstellungen-Seite mit Table-to-Card Pattern.

**Dateien**: `frontend/app/properties/[id]/rate-plans/page.tsx`

**Status**: ✅ IMPLEMENTED

---

## Kurtaxen (Visitor Tax) Management Feature (2026-02-20) - IMPLEMENTED

**Feature**: Verwaltung von Kurtaxen pro Gemeinde mit saisonalen Tarifen und automatischer Property-Zuordnung via PLZ.

### Datenbank-Schema

| Tabelle | Beschreibung |
|---------|--------------|
| `visitor_tax_locations` | Gemeinden mit PLZ-Array für Auto-Matching |
| `visitor_tax_periods` | Saisonale Tarife (Betrag in Cents, Kinder-Freibetrag) |
| `properties.visitor_tax_location_id` | FK für Property-Zuweisung |

**Migration**: `supabase/migrations/20260220000000_add_visitor_tax.sql`

**Route**: `/kurtaxen` (Navigation unter OBJEKTE)

**Runbook**: [31-kurtaxen-visitor-tax.md](./ops/runbook/31-kurtaxen-visitor-tax.md)

**Status**: ✅ IMPLEMENTED

---

## Bookings Filter HTTP 500 Fix (2026-02-20) - IMPLEMENTED

**Problem**: Filtering bookings by status returned HTTP 500 errors.

**Solution**: Field normalization + NULL default handling in `booking_service.py`.

**Status**: ✅ IMPLEMENTED

---

## Luxe Token Elimination (2026-02-20) - IMPLEMENTED

**Objective**: Remove all hardcoded `luxe-*` design tokens and replace with dynamic semantic tokens.

**Deleted**: `app/components/luxe/` folder

**Status**: ✅ IMPLEMENTED

---

## Security Audit Fixes (2026-02-19) - IMPLEMENTED

**Audit Reference**: Audit-2026-02-19.md

**Resolved**: 12/15 findings (CRITICAL + HIGH vulnerabilities fixed)

**Open**: 3 findings (deferred - Channel Manager not enabled, MVP scope)

**Status**: ✅ IMPLEMENTED

---

## Property Filter Feature (2026-02-14) - IMPLEMENTED

**Overview**: Comprehensive property search and filter system for the public website.

**Features**:
- Filter by city, guests, bedrooms, price range, property type, amenities
- Three layout modes: sidebar, top, modal
- Admin control via `/website/filters`

**Status**: ✅ IMPLEMENTED

---

## Status Semantics

| Status | Bedeutung |
|--------|-----------|
| ✅ IMPLEMENTED | Feature deployed, manual testing completed, docs updated |
| ✅ VERIFIED | IMPLEMENTED + automated production verification passed |

---

## Archiv

Historische Einträge (Phase 1-20, vor 2026-02-14) wurden ausgelagert:

➡️ **[project_status_archive.md](./project_status_archive.md)** - Vollständige Projekthistorie (32.000+ Zeilen)

---

*Last updated: 2026-02-24*
