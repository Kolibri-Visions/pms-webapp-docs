# Direct Booking Engine - Email Templates

**Version:** 1.0.0
**Last Updated:** 2025-12-21

---

## Overview

This directory contains email templates for all booking-related notifications in the Direct Booking Engine. Templates are provided in both HTML and plain text formats.

## Template Variables

All templates use Jinja2-style variable interpolation:
- `{{ variable_name }}` - Variable substitution
- `{% if condition %}...{% endif %}` - Conditional blocks
- `{% for item in items %}...{% endfor %}` - Loops

---

## Templates

### 1. Booking Confirmation
- **File:** `booking-confirmation.html` / `booking-confirmation.txt`
- **Trigger:** After payment is confirmed
- **Recipient:** Guest
- **Variables:**
  - `guest_name` - Guest's first name
  - `booking_reference` - Confirmation number (e.g., PMS-2025-000123)
  - `property_name` - Property name
  - `property_address` - Full property address
  - `check_in_date` - Check-in date (formatted)
  - `check_in_time` - Check-in time
  - `check_out_date` - Check-out date (formatted)
  - `check_out_time` - Check-out time
  - `num_guests` - Number of guests
  - `num_nights` - Number of nights
  - `total_price` - Total amount paid
  - `currency` - Currency code
  - `special_requests` - Guest's special requests
  - `host_name` - Property owner's name
  - `host_phone` - Property owner's phone (optional)
  - `booking_url` - Link to view booking
  - `calendar_url` - Link to add to calendar

### 2. Payment Reminder
- **File:** `payment-reminder.html` / `payment-reminder.txt`
- **Trigger:** 10 minutes after booking creation if payment not completed
- **Recipient:** Guest
- **Variables:**
  - `guest_name` - Guest's first name
  - `property_name` - Property name
  - `check_in_date` - Check-in date
  - `check_out_date` - Check-out date
  - `total_price` - Amount to pay
  - `currency` - Currency code
  - `remaining_minutes` - Minutes until expiration
  - `payment_url` - Direct link to complete payment
  - `expires_at` - Expiration time

### 3. Booking Expired
- **File:** `booking-expired.html` / `booking-expired.txt`
- **Trigger:** After booking reservation expires (30 min timeout)
- **Recipient:** Guest
- **Variables:**
  - `guest_name` - Guest's first name
  - `property_name` - Property name
  - `check_in_date` - Original check-in date
  - `check_out_date` - Original check-out date
  - `rebook_url` - Link to start new booking

### 4. Booking Cancelled (Guest)
- **File:** `booking-cancelled-guest.html` / `booking-cancelled-guest.txt`
- **Trigger:** When booking is cancelled (by guest or system)
- **Recipient:** Guest
- **Variables:**
  - `guest_name` - Guest's first name
  - `booking_reference` - Confirmation number
  - `property_name` - Property name
  - `check_in_date` - Original check-in date
  - `check_out_date` - Original check-out date
  - `cancellation_reason` - Reason for cancellation
  - `refund_amount` - Refund amount (if applicable)
  - `refund_status` - Refund status (processing, completed)
  - `support_email` - Support email address

### 5. Booking Cancelled (Host)
- **File:** `booking-cancelled-host.html` / `booking-cancelled-host.txt`
- **Trigger:** When booking is cancelled
- **Recipient:** Property owner
- **Variables:**
  - `host_name` - Host's name
  - `guest_name` - Guest's full name
  - `booking_reference` - Confirmation number
  - `property_name` - Property name
  - `check_in_date` - Original check-in date
  - `check_out_date` - Original check-out date
  - `cancellation_reason` - Reason for cancellation
  - `dashboard_url` - Link to dashboard

### 6. New Booking (Host)
- **File:** `new-booking-host.html` / `new-booking-host.txt`
- **Trigger:** After payment is confirmed
- **Recipient:** Property owner
- **Variables:**
  - `host_name` - Host's name
  - `guest_name` - Guest's full name
  - `guest_email` - Guest's email
  - `guest_phone` - Guest's phone (if provided)
  - `booking_reference` - Confirmation number
  - `property_name` - Property name
  - `check_in_date` - Check-in date
  - `check_out_date` - Check-out date
  - `num_guests` - Number of guests
  - `total_price` - Total booking amount
  - `payout_amount` - Amount after fees
  - `currency` - Currency code
  - `special_requests` - Guest's special requests
  - `dashboard_url` - Link to booking in dashboard

### 7. Check-in Instructions
- **File:** `checkin-instructions.html` / `checkin-instructions.txt`
- **Trigger:** 24 hours before check-in
- **Recipient:** Guest
- **Variables:**
  - `guest_name` - Guest's first name
  - `booking_reference` - Confirmation number
  - `property_name` - Property name
  - `property_address` - Full property address
  - `check_in_date` - Check-in date
  - `check_in_time` - Check-in time
  - `checkin_instructions` - Detailed check-in instructions
  - `access_code` - Door/lockbox code (if applicable)
  - `wifi_name` - WiFi network name
  - `wifi_password` - WiFi password
  - `host_name` - Host's name
  - `host_phone` - Host's phone for emergencies
  - `property_rules` - House rules summary

### 8. Review Request
- **File:** `review-request.html` / `review-request.txt`
- **Trigger:** After check-out
- **Recipient:** Guest
- **Variables:**
  - `guest_name` - Guest's first name
  - `property_name` - Property name
  - `check_in_date` - Check-in date
  - `check_out_date` - Check-out date
  - `review_url` - Link to leave review
  - `host_name` - Host's name

### 9. Guest Invitation
- **File:** `guest-invitation.html` / `guest-invitation.txt`
- **Trigger:** When host invites guest to create account
- **Recipient:** Guest
- **Variables:**
  - `guest_name` - Guest's first name
  - `host_name` - Host's name
  - `custom_message` - Custom message from host
  - `invitation_url` - Magic link to create account
  - `expires_at` - Link expiration date

---

## Email Service Configuration

### SendGrid (Recommended)

```python
# app/services/email.py

import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from jinja2 import Environment, FileSystemLoader

sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
template_env = Environment(loader=FileSystemLoader('email-templates'))

async def send_email(
    to: str,
    subject: str,
    template: str,
    data: dict,
    from_email: str = "bookings@pms-webapp.com",
    from_name: str = "PMS-Webapp",
) -> bool:
    """Send an email using a template."""
    # Render templates
    html_template = template_env.get_template(f"{template}.html")
    text_template = template_env.get_template(f"{template}.txt")

    html_content = html_template.render(**data)
    text_content = text_template.render(**data)

    message = Mail(
        from_email=Email(from_email, from_name),
        to_emails=To(to),
        subject=subject,
        html_content=Content("text/html", html_content),
        plain_text_content=Content("text/plain", text_content),
    )

    try:
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
```

---

## Testing

Use Mailhog or similar for local testing:

```bash
# Docker command for Mailhog
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Access web UI at http://localhost:8025
```

Configure for local development:
```python
# settings.py
if settings.ENVIRONMENT == "development":
    EMAIL_HOST = "localhost"
    EMAIL_PORT = 1025
    EMAIL_USE_TLS = False
```

---

## Localization

Templates support localization via template variants:
- `booking-confirmation.html` (English - default)
- `booking-confirmation.de.html` (German)
- `booking-confirmation.fr.html` (French)

```python
def get_template_path(template: str, language: str = "en") -> str:
    """Get localized template path."""
    if language != "en":
        localized = f"{template}.{language}.html"
        if os.path.exists(f"email-templates/{localized}"):
            return localized
    return f"{template}.html"
```
