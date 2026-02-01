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

## Related Documentation

- [Backend Notifications Routes](../../api/notifications.md) — API endpoint details
- [Scripts README](../../../scripts/README.md#pms_email_notifications_smokesh) — Smoke test documentation
- [Config Settings](../../core/config.py) — EMAIL_* settings
