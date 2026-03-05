# Email Notifications (Admin)

This runbook chapter covers the Email Notifications system for the PMS-Webapp.

**When to use:** Troubleshooting email delivery, inspecting the outbox, or configuring email providers.

## Overview

The email notification system uses an **outbox pattern** for reliable email delivery:

1. Events (booking created, approved, etc.) trigger email generation
2. Emails are queued in the `email_outbox` table
3. A processor sends queued emails via the configured provider
4. Failed emails can be retried

**Safety Default:** `EMAIL_NOTIFICATIONS_ENABLED=false` by default.
When disabled, emails are queued but NOT sent (status='skipped').

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_NOTIFICATIONS_ENABLED` | No | `false` | Enable actual email sending |
| `SMTP_HOST` | If enabled | - | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | If enabled | - | SMTP username |
| `SMTP_PASSWORD` | If enabled | - | SMTP password |
| `SMTP_FROM_EMAIL` | If enabled | - | Sender email address |
| `SMTP_FROM_NAME` | No | `PMS-Webapp` | Sender display name |
| `SMTP_REPLY_TO` | No | - | Reply-to address |

## Email Status Flow

```
queued → sent     (email delivered successfully)
       → failed   (delivery error, can retry)
       → skipped  (EMAIL_NOTIFICATIONS_ENABLED=false)
```

## API Endpoints

| Action | Endpoint | Method | RBAC |
|--------|----------|--------|------|
| List outbox | `/api/v1/notifications/email/outbox` | GET | admin, manager |
| Send test email | `/api/v1/notifications/email/test` | POST | admin, manager |
| Process outbox | `/api/v1/notifications/email/process-outbox` | POST | admin, manager |

### List Outbox

```bash
curl -sS "${API}/api/v1/notifications/email/outbox?limit=25&offset=0" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Query Parameters:**
- `limit`: Max entries (1-100, default 25)
- `offset`: Pagination offset
- `status`: Filter by status (queued/sent/failed/skipped)
- `search`: Search in recipient_email or subject

### Send Test Email

```bash
curl -sS -X POST "${API}/api/v1/notifications/email/test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_email": "test@example.com", "template": "test"}' | jq .
```

**Response:**
```json
{
  "success": true,
  "outbox_id": "uuid-here",
  "status": "skipped",
  "message": "E-Mail wurde in Outbox gespeichert (EMAIL_NOTIFICATIONS_ENABLED=false)"
}
```

## Email Templates (DE)

| Template | Event | Recipient |
|----------|-------|-----------|
| `booking_request_created` | New booking request | Agency (notification_email) |
| `booking_request_approved` | Request approved | Guest |
| `booking_request_declined` | Request declined | Guest |
| `booking_confirmed` | Booking confirmed | Guest |
| `booking_cancelled` | Booking cancelled | Guest |
| `test` | Manual test | Specified recipient |

### Pricing Breakdown in Templates (Multi-VAT)

Die Templates `booking_confirmed` und `booking_request_approved` unterstützen detaillierte Preisaufschlüsselung mit Multi-VAT:

**Template-Placeholder:** `{pricing_breakdown}`

**Erforderlicher Kontext:**
```python
from app.services.email_notification_service import (
    format_pricing_breakdown_for_email,
    format_legacy_pricing_for_email,
)

# Multi-VAT Format (mit Gebühren und Steuern)
pricing_breakdown = format_pricing_breakdown_for_email(
    subtotal="450.00",
    nightly_rate="90.00",
    num_nights=5,
    fees=[
        {"name": "Endreinigung", "amount_cents": 8000},
        {"name": "Bettwäsche", "amount_cents": 2500},
    ],
    taxes=[
        {"name": "MwSt.", "percent": 7, "amount_cents": 3150, "source_name": "Übernachtungen"},
        {"name": "MwSt.", "percent": 19, "amount_cents": 1520, "source_name": "Endreinigung"},
    ],
    visitor_tax_cents=1200,
    visitor_tax_details={"persons": 2, "nights": 5},
    total_price="542.70",
    currency="EUR",
)

# Legacy Format (nur Gesamtpreis)
pricing_breakdown = format_legacy_pricing_for_email(
    total_price="542.70",
    currency="EUR",
)
```

**Beispiel-Ausgabe (Multi-VAT):**
```
Übernachtungen (5 Nächte × 90.00 €): 450.00 €
Endreinigung: 80.00 €
Bettwäsche: 25.00 €
MwSt. (7% auf Übernachtungen): 31.50 €
MwSt. (19% auf Endreinigung): 15.20 €
Kurtaxe (2 Pers. × 5 Nächte): 12.00 €
----------------------------------------
Gesamtbetrag: 542.70 €
```

## Troubleshooting

### Emails Not Being Sent

**Symptom:** Outbox entries show status='skipped'

**Cause:** `EMAIL_NOTIFICATIONS_ENABLED=false` (default)

**Resolution:**
1. Verify SMTP configuration is complete
2. Set `EMAIL_NOTIFICATIONS_ENABLED=true`
3. Restart backend

### SMTP Connection Failed

**Symptom:** Outbox entries show status='failed' with SMTP error

**Cause:** SMTP configuration incorrect or server unreachable

**Resolution:**
1. Verify SMTP credentials
2. Check firewall allows outbound port 587
3. Test SMTP connection manually:
   ```bash
   openssl s_client -starttls smtp -connect $SMTP_HOST:587
   ```

### Duplicate Emails

**Symptom:** Same email sent multiple times

**Cause:** Missing idempotency key or retries

**Resolution:**
1. Check idempotency_key is set for event-driven emails
2. Review outbox for duplicate entries:
   ```sql
   SELECT recipient_email, subject, COUNT(*)
   FROM email_outbox
   WHERE agency_id = '<id>'
   GROUP BY recipient_email, subject
   HAVING COUNT(*) > 1;
   ```

## Inspecting the Outbox

### View Recent Emails

```sql
SELECT id, recipient_email, subject, status, attempts, created_at
FROM email_outbox
WHERE agency_id = '<agency_id>'
ORDER BY created_at DESC
LIMIT 20;
```

### Check Failed Emails

```sql
SELECT id, recipient_email, subject, last_error, attempts
FROM email_outbox
WHERE agency_id = '<agency_id>'
  AND status = 'failed'
ORDER BY created_at DESC;
```

### Retry Failed Email

```sql
UPDATE email_outbox
SET status = 'queued', last_error = NULL
WHERE id = '<outbox_id>';
```

Then trigger processing via API or Celery.

## Smoke Test

**Location:** `backend/scripts/pms_email_notifications_smoke.sh`

**EXECUTION LOCATION:** HOST-SERVER-TERMINAL

### Usage

```bash
# Basic usage (requires JWT_TOKEN)
JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_email_notifications_smoke.sh

# Custom API URL
API_BASE_URL=https://api.test.example.com JWT_TOKEN="eyJhbG..." ./backend/scripts/pms_email_notifications_smoke.sh
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_TOKEN` | Yes | - | Valid JWT with admin/manager role |
| `API_BASE_URL` | No | `https://api.fewo.kolibri-visions.de` | API base URL |

### What It Tests

1. POST /api/v1/notifications/email/test → HTTP 200 + outbox entry created
2. GET /api/v1/notifications/email/outbox → List works
3. Search outbox by recipient → Entry found
4. Filter outbox by status → Filter works
5. Verify entry structure → All required fields present

### Expected Result

```
RESULT: PASS
Summary: PASS=6, FAIL=0, SKIP=0
```

### Cleanup

Test emails are created with unique addresses like `smoke.<timestamp>@example.com`.
These entries remain in the outbox for inspection but are never sent to real addresses.

## Migration ohne Supabase CLI (Studio SQL Editor)

Wenn `supabase db push` nicht verfügbar ist (`supabase: command not found` oder keine CLI installiert):

### Schritte

1. **Supabase Studio öffnen**
   - Dashboard: https://supabase.com/dashboard
   - Projekt auswählen → SQL Editor

2. **Migration-Datei einfügen**
   - Inhalt von `supabase/migrations/20260201100000_add_email_outbox.sql` kopieren
   - In SQL Editor einfügen und ausführen

3. **Verifizierung**
   ```sql
   SELECT to_regclass('public.email_outbox');
   -- Erwartetes Ergebnis: 'email_outbox' (nicht NULL)
   ```

### Troubleshooting: "must be owner of table"

**Fehler:** `ERROR: must be owner of table email_outbox`

**Ursache:** Sie haben die Migration als falsche Rolle ausgeführt (z.B. `postgres` via docker exec).

**Lösung:**
- Tabelle existiert bereits (Prüfung: `SELECT to_regclass('public.email_outbox');`)
- Migration erneut via **Studio SQL Editor** ausführen (korrekte Owner-Rechte)
- Alternativ: Smoke-Test ausführen — wenn rc=0, ist die Tabelle funktionsfähig

---

## Celery Integration (Future)

For production workloads, process outbox via Celery task:

```python
@celery.task
def process_email_outbox():
    """Periodic task to process queued emails."""
    # Call /api/v1/notifications/email/process-outbox
    # or directly invoke EmailNotificationService
    pass
```

Schedule via Celery Beat (e.g., every 5 minutes).

---

## Admin UI: E-Mail-Outbox

**Route:** `/notifications/email-outbox`

**Berechtigungen:** `admin`, `manager`

### Features

1. **Outbox-Tabelle**
   - Paginierte Liste aller E-Mails
   - Status-Badges: queued (gelb), sent (grün), failed (rot), skipped (grau)
   - Spalten: Status, Empfänger, Betreff, Event-Typ, Erstellt, Versuche

2. **Filter**
   - Status-Dropdown: Alle/Warteschlange/Gesendet/Fehlgeschlagen/Übersprungen
   - Freitextsuche: Empfänger, Betreff, Event-Typ

3. **Aktionen**
   - **Test-E-Mail senden:** Modal mit E-Mail-Eingabe, sendet Test-Email (oder speichert als "skipped" wenn disabled)
   - **Warteschlange verarbeiten:** Verarbeitet queued Emails mit Cooldown-Protection

4. **Detail-Modal**
   - Alle Felder inkl. Idempotency-Key, Fehler, Timestamps
   - Deep-Links zu Buchungen/Anfragen (entity_type → UI-Route)
   - Plaintext-Body-Vorschau (kein HTML-Rendering aus Sicherheitsgründen)

### Sicherheitshinweise

- **HTML-Preview:** Nur Plaintext wird angezeigt. HTML-Rendering ist deaktiviert um XSS zu vermeiden.
- **Process-Outbox:** Button hat Cooldown (3 Sekunden) um Spam-Klicks zu verhindern.
- **Feature-Flag:** Wenn `EMAIL_NOTIFICATIONS_ENABLED=false`, werden Test-E-Mails als "skipped" gespeichert.

### Troubleshooting UI

**Symptom:** 403 Forbidden beim Aufruf von `/notifications/email-outbox`

**Ursache:** Benutzer hat keine admin/manager Rolle.

**Lösung:** Rolle in `team_members` Tabelle prüfen.

---

**Symptom:** Leere Tabelle obwohl E-Mails versendet wurden

**Ursache:** Mögliche Ursachen:
1. Session abgelaufen (401)
2. Agency-ID nicht gefunden
3. Filter zu restriktiv

**Lösung:**
1. Seite neu laden / neu einloggen
2. Filter auf "Alle Status" zurücksetzen
3. Browser-Konsole auf Fehler prüfen

## Related Documentation

- [Backend Notifications Routes](../../api/notifications.md) — API endpoint details
- [Scripts README](../../../scripts/README.md#pms_email_notifications_smokesh) — Smoke test documentation
- [Config Settings](../../core/config.py) — EMAIL_* settings
