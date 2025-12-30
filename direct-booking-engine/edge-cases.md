# Direct Booking Engine - Edge Case Handling

**Version:** 1.0.0
**Last Updated:** 2025-12-21
**Status:** Approved

---

## Overview

This document details all edge cases in the Direct Booking Engine and their handling strategies. Each edge case includes the scenario description, detection method, resolution strategy, and code examples.

---

## 1. Payment Timeout (30 Minutes)

### Scenario
Guest starts booking, gets to payment page, but doesn't complete payment within 30 minutes.

### Why It Matters
- Calendar dates are held during reservation
- Blocks other potential guests from booking
- Stripe PaymentIntent remains open

### Detection

```python
# Celery task scheduled at booking creation
from celery import shared_task
from datetime import datetime, timedelta

@shared_task(bind=True, max_retries=3)
def check_booking_expiration(self, booking_id: str):
    """
    Check if a booking has expired and cancel if necessary.

    Scheduled to run BOOKING_RESERVATION_TIMEOUT_MINUTES after booking creation.
    """
    with get_db_session() as db:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()

        if not booking:
            return {"status": "not_found"}

        # Skip if already processed
        if booking.status != BookingStatus.RESERVED.value:
            return {"status": "already_processed", "current_status": booking.status}

        if booking.payment_status != PaymentStatus.PENDING.value:
            return {"status": "already_processed", "payment_status": booking.payment_status}

        # Check if expired
        now = datetime.utcnow()
        expires_at = booking.created_at + timedelta(minutes=BOOKING_RESERVATION_TIMEOUT_MINUTES)

        if now >= expires_at:
            # Cancel the booking
            cancel_expired_booking_sync(db, booking)
            return {"status": "cancelled"}
        else:
            # Not yet expired, reschedule check
            remaining_seconds = (expires_at - now).total_seconds()
            self.retry(countdown=remaining_seconds + 60)  # Check 1 min after expiry
            return {"status": "rescheduled"}
```

### Resolution

```python
async def cancel_expired_booking(db: AsyncSession, booking: Booking) -> None:
    """
    Cancel an expired booking and release resources.

    Steps:
    1. Update booking status to cancelled
    2. Release calendar dates
    3. Cancel Stripe PaymentIntent
    4. Send expiration notification email
    """
    now = datetime.utcnow()

    # 1. Update booking status
    booking.status = BookingStatus.CANCELLED.value
    booking.payment_status = PaymentStatus.EXPIRED.value
    booking.cancelled_at = now
    booking.cancellation_reason = "Payment timeout - booking expired"
    booking.updated_at = now

    # 2. Release calendar dates
    date_range = [
        booking.check_in + timedelta(days=i)
        for i in range((booking.check_out - booking.check_in).days)
    ]

    await db.execute(
        CalendarAvailability.__table__.update()
        .where(
            and_(
                CalendarAvailability.property_id == booking.property_id,
                CalendarAvailability.date.in_(date_range),
                CalendarAvailability.booking_id == booking.id,
            )
        )
        .values(
            available=True,
            availability_status="available",
            booking_id=None,
            updated_at=now,
        )
    )

    # 3. Cancel Stripe PaymentIntent
    if booking.stripe_payment_intent_id:
        try:
            stripe.PaymentIntent.cancel(
                booking.stripe_payment_intent_id,
                cancellation_reason="abandoned",
            )
        except stripe.error.InvalidRequestError:
            # Already cancelled or succeeded - that's fine
            pass

    await db.commit()

    # 4. Send expiration notification
    asyncio.create_task(send_booking_expired_email(booking.id))


async def send_booking_expired_email(booking_id: UUID) -> None:
    """Send email to guest about expired booking with link to rebook."""
    booking = await get_booking_with_details(booking_id)

    await send_email(
        to=booking.guest.email,
        subject="Your Booking Has Expired",
        template="booking_expired",
        data={
            "guest_name": booking.guest.first_name,
            "property_name": booking.property.name,
            "check_in": booking.check_in.strftime("%B %d, %Y"),
            "check_out": booking.check_out.strftime("%B %d, %Y"),
            "rebook_link": f"https://app.pms-webapp.com/properties/{booking.property_id}"
                          f"?check_in={booking.check_in}&check_out={booking.check_out}",
        },
    )
```

### Frontend Timer

```typescript
// components/payment-timer.tsx
'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { AlertTriangle } from 'lucide-react'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'

interface PaymentTimerProps {
  expiresAt: string
  bookingId: string
  propertyId: string
  onExpired: () => void
}

export function PaymentTimer({ expiresAt, bookingId, propertyId, onExpired }: PaymentTimerProps) {
  const router = useRouter()
  const [timeLeft, setTimeLeft] = useState<number>(0)
  const [isExpired, setIsExpired] = useState(false)

  // Warning thresholds
  const FIVE_MINUTES = 5 * 60 * 1000
  const ONE_MINUTE = 60 * 1000

  const calculateTimeLeft = useCallback(() => {
    const now = new Date().getTime()
    const expires = new Date(expiresAt).getTime()
    return Math.max(0, expires - now)
  }, [expiresAt])

  useEffect(() => {
    const timer = setInterval(() => {
      const remaining = calculateTimeLeft()
      setTimeLeft(remaining)

      if (remaining === 0) {
        setIsExpired(true)
        clearInterval(timer)
        onExpired()
      }
    }, 1000)

    return () => clearInterval(timer)
  }, [calculateTimeLeft, onExpired])

  if (isExpired) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Booking Expired</AlertTitle>
        <AlertDescription>
          Your booking session has expired. Please{' '}
          <button
            onClick={() => router.push(`/properties/${propertyId}`)}
            className="underline font-medium"
          >
            start a new booking
          </button>
          .
        </AlertDescription>
      </Alert>
    )
  }

  const minutes = Math.floor(timeLeft / 60000)
  const seconds = Math.floor((timeLeft % 60000) / 1000)

  const isUrgent = timeLeft < ONE_MINUTE
  const isWarning = timeLeft < FIVE_MINUTES && timeLeft >= ONE_MINUTE

  return (
    <div
      className={cn(
        'flex items-center gap-2 p-3 rounded-lg',
        isUrgent && 'bg-red-50 text-red-700 border border-red-200',
        isWarning && 'bg-amber-50 text-amber-700 border border-amber-200',
        !isUrgent && !isWarning && 'bg-blue-50 text-blue-700 border border-blue-200'
      )}
    >
      {isUrgent && <AlertTriangle className="h-5 w-5 animate-pulse" />}
      <span className="font-medium">
        Complete payment within{' '}
        <span className="font-mono text-lg">
          {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
        </span>
      </span>
    </div>
  )
}
```

---

## 2. Payment Failure (Retry Logic)

### Scenario
Guest's card is declined or payment fails for any reason.

### Why It Matters
- Guest should have opportunity to fix card issues
- Prevents unnecessary booking cancellations
- Maintains good conversion rates

### Detection

```typescript
// Frontend: Stripe confirmPayment error handling
const { error, paymentIntent } = await stripe.confirmPayment({
  elements,
  redirect: 'if_required',
})

if (error) {
  // Payment failed
  handlePaymentError(error)
}
```

### Resolution

```typescript
// components/payment-form.tsx

const MAX_RETRIES = 3

export function PaymentForm({ bookingId, clientSecret, onSuccess, onFailure }) {
  const [retryCount, setRetryCount] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const handlePaymentError = useCallback((stripeError: StripeError) => {
    const newRetryCount = retryCount + 1

    if (newRetryCount >= MAX_RETRIES) {
      // Max retries reached - cancel booking
      setError(`Payment failed after ${MAX_RETRIES} attempts. Your booking has been cancelled.`)
      cancelBookingAfterPaymentFailure(bookingId)
      onFailure(stripeError.message)
      return
    }

    setRetryCount(newRetryCount)

    // Show appropriate error message based on error type
    let message = ''
    switch (stripeError.code) {
      case 'card_declined':
        message = `Your card was declined. Please try a different card. (Attempt ${newRetryCount}/${MAX_RETRIES})`
        break
      case 'insufficient_funds':
        message = `Insufficient funds. Please use a different card. (Attempt ${newRetryCount}/${MAX_RETRIES})`
        break
      case 'expired_card':
        message = `Your card has expired. Please use a different card. (Attempt ${newRetryCount}/${MAX_RETRIES})`
        break
      case 'incorrect_cvc':
        message = `Incorrect CVC. Please check and try again. (Attempt ${newRetryCount}/${MAX_RETRIES})`
        break
      default:
        message = `${stripeError.message || 'Payment failed'}. Please try again. (Attempt ${newRetryCount}/${MAX_RETRIES})`
    }

    setError(message)
    setIsProcessing(false)

    // Track payment failure for analytics
    trackEvent('payment_failed', {
      booking_id: bookingId,
      error_code: stripeError.code,
      retry_count: newRetryCount,
    })
  }, [bookingId, retryCount, onFailure])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setIsProcessing(true)
    setError(null)

    try {
      const { error, paymentIntent } = await stripe.confirmPayment({
        elements,
        redirect: 'if_required',
      })

      if (error) {
        handlePaymentError(error)
        return
      }

      if (paymentIntent?.status === 'succeeded') {
        await confirmBooking(bookingId, paymentIntent.id)
        onSuccess()
      }
    } catch (err) {
      handlePaymentError({ message: 'An unexpected error occurred' })
    }
  }

  // ... render form with error display and retry button
}


async function cancelBookingAfterPaymentFailure(bookingId: string) {
  try {
    await fetch(`/api/v1/bookings/${bookingId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: 'Payment failed after maximum retries' }),
    })
  } catch (error) {
    console.error('Failed to cancel booking:', error)
  }
}
```

### Backend: Update Payment Retry Count

```python
@router.post("/bookings/{booking_id}/payment-attempt")
async def record_payment_attempt(
    booking_id: UUID,
    success: bool = False,
    error_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a payment attempt for a booking.

    Called by frontend to track retries.
    """
    booking = await db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Increment attempt counter
    booking.payment_attempts = (booking.payment_attempts or 0) + 1
    booking.last_payment_error = error_code if not success else None
    booking.updated_at = datetime.utcnow()

    if booking.payment_attempts >= MAX_PAYMENT_RETRIES and not success:
        # Auto-cancel after max retries
        await cancel_booking_internal(db, booking, reason="Max payment retries exceeded")

    await db.commit()

    return {
        "attempts": booking.payment_attempts,
        "max_retries": MAX_PAYMENT_RETRIES,
        "cancelled": booking.status == BookingStatus.CANCELLED.value,
    }
```

---

## 3. Race Condition (Simultaneous Booking)

### Scenario
Two guests try to book the same property for overlapping dates at exactly the same time.

### Why It Matters
- Must prevent double-bookings
- Only one guest should succeed
- Other guest needs friendly error message

### Detection

```sql
-- PostgreSQL exclusion constraint on bookings table
ALTER TABLE bookings
ADD CONSTRAINT no_double_bookings EXCLUDE USING gist (
    property_id WITH =,
    daterange(check_in, check_out, '[)') WITH &&
)
WHERE (status NOT IN ('cancelled', 'declined'));

-- This constraint automatically prevents overlapping date ranges
-- for the same property
```

### Resolution

```python
# Backend: Handle constraint violation gracefully

from sqlalchemy.exc import IntegrityError
from asyncpg.exceptions import ExclusionViolationError

@router.post("/bookings")
async def create_booking(
    request: BookingCreateRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Create a new booking with race condition protection."""

    # Layer 1: Redis distributed lock (prevents hitting DB in most cases)
    lock_key = f"booking:lock:{request.property_id}:{request.check_in}:{request.check_out}"
    lock = redis.lock(lock_key, timeout=30, blocking_timeout=5)

    try:
        if not await lock.acquire():
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "concurrent_booking",
                    "message": "Another guest is currently booking these dates. Please wait a moment and try again.",
                    "retry_after": 10,  # seconds
                }
            )

        # Layer 2: Availability check (with lock held)
        if not await is_available(db, request.property_id, request.check_in, request.check_out):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "dates_unavailable",
                    "message": "Sorry, these dates are no longer available. Please select different dates.",
                }
            )

        # Layer 3: Create booking (database constraint as final guard)
        try:
            booking = Booking(...)
            db.add(booking)
            await db.commit()
        except IntegrityError as e:
            await db.rollback()

            # Check if it's the exclusion constraint
            if "no_double_bookings" in str(e.orig):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "dates_just_booked",
                        "message": "These dates were just booked by another guest. Please select different dates.",
                    }
                )
            raise

        return booking

    finally:
        await lock.release()
```

### Frontend: Handle Race Condition Error

```typescript
// app/booking/[propertyId]/details/page.tsx

async function handleCreateBooking() {
  setIsLoading(true)
  setError(null)

  try {
    const response = await fetch('/api/v1/bookings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bookingData),
    })

    if (!response.ok) {
      const data = await response.json()

      switch (data.code) {
        case 'concurrent_booking':
          // Another booking in progress - show retry option
          setError({
            type: 'retry',
            message: data.message,
            retryAfter: data.retry_after,
          })
          break

        case 'dates_unavailable':
        case 'dates_just_booked':
          // Dates no longer available - refresh calendar
          setError({
            type: 'dates_taken',
            message: data.message,
          })
          // Refetch calendar to show updated availability
          await refetchCalendar()
          break

        default:
          setError({
            type: 'error',
            message: data.message || 'An error occurred',
          })
      }
      return
    }

    // Success - redirect to payment
    const booking = await response.json()
    router.push(`/booking/${booking.booking_id}/payment`)

  } catch (err) {
    setError({
      type: 'error',
      message: 'Network error. Please check your connection and try again.',
    })
  } finally {
    setIsLoading(false)
  }
}

// Error display component
function BookingErrorDisplay({ error, onRetry }) {
  if (error.type === 'retry') {
    return (
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Please Wait</AlertTitle>
        <AlertDescription>
          {error.message}
          <CountdownRetryButton seconds={error.retryAfter} onClick={onRetry} />
        </AlertDescription>
      </Alert>
    )
  }

  if (error.type === 'dates_taken') {
    return (
      <Alert variant="destructive">
        <XCircle className="h-4 w-4" />
        <AlertTitle>Dates No Longer Available</AlertTitle>
        <AlertDescription>
          {error.message}
          <Button onClick={() => scrollToCalendar()} variant="outline" className="mt-2">
            Select Different Dates
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <Alert variant="destructive">
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>Error</AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
    </Alert>
  )
}
```

---

## 4. Webhook Processing Delay

### Scenario
Stripe webhook arrives late (after guest has already seen confirmation) or arrives multiple times.

### Why It Matters
- Don't double-confirm bookings
- Don't overwrite frontend confirmation with webhook data
- Maintain data consistency

### Detection & Resolution: Idempotent Webhook Processing

```python
# Idempotency using Redis event cache + database state check

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Handle Stripe webhooks with idempotency guarantees.

    Idempotency Layers:
    1. Redis cache: Fast check for recent duplicates (24h TTL)
    2. Database state: Only process if booking in expected state
    """
    event = verify_webhook(request)
    event_id = event.id

    # Layer 1: Redis duplicate check
    cache_key = f"stripe_webhook:{event_id}"
    if await redis.exists(cache_key):
        logger.info(f"Duplicate webhook event {event_id} - skipping")
        return JSONResponse({"status": "duplicate"})

    # Layer 2: Process with state check
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        booking_id = payment_intent.metadata.get("booking_id")

        if not booking_id:
            return JSONResponse({"status": "ignored", "reason": "no_booking_id"})

        booking = await db.get(Booking, UUID(booking_id))

        if not booking:
            logger.warning(f"Booking {booking_id} not found for webhook")
            return JSONResponse({"status": "ignored", "reason": "booking_not_found"})

        # Idempotency: Only process if still in reserved state
        if booking.status == BookingStatus.CONFIRMED.value:
            logger.info(f"Booking {booking_id} already confirmed (likely by frontend)")
            # Still mark event as processed to prevent future duplicates
            await redis.setex(cache_key, 86400, "processed")
            return JSONResponse({"status": "already_confirmed"})

        if booking.status != BookingStatus.RESERVED.value:
            logger.warning(f"Booking {booking_id} in unexpected state: {booking.status}")
            await redis.setex(cache_key, 86400, "skipped")
            return JSONResponse({"status": "ignored", "reason": f"unexpected_state_{booking.status}"})

        # Proceed with confirmation
        await confirm_booking_from_webhook(db, booking, payment_intent)

    # Mark event as processed
    await redis.setex(cache_key, 86400, "processed")
    return JSONResponse({"status": "success"})


async def confirm_booking_from_webhook(
    db: AsyncSession,
    booking: Booking,
    payment_intent: dict,
) -> None:
    """
    Confirm booking from webhook.

    Uses optimistic locking to prevent race with frontend confirmation.
    """
    now = datetime.utcnow()

    # Optimistic locking with version check
    result = await db.execute(
        Booking.__table__.update()
        .where(
            and_(
                Booking.id == booking.id,
                Booking.status == BookingStatus.RESERVED.value,
                Booking.version == booking.version,  # Optimistic lock
            )
        )
        .values(
            status=BookingStatus.CONFIRMED.value,
            payment_status=PaymentStatus.PAID.value,
            paid_amount=Decimal(payment_intent["amount_received"]) / 100,
            paid_at=now,
            confirmed_at=now,
            updated_at=now,
            version=booking.version + 1,
        )
    )

    if result.rowcount == 0:
        # Another process already confirmed this booking
        logger.info(f"Booking {booking.id} was confirmed by another process")
        return

    # Update calendar dates
    await update_calendar_to_booked(db, booking)

    await db.commit()

    # Send confirmation email (idempotent - check if already sent)
    await send_confirmation_if_not_sent(booking.id)
```

---

## 5. Guest Closes Browser

### Scenario
Guest enters details, creates booking reservation, but closes browser before completing payment.

### Why It Matters
- Booking is in reserved state holding dates
- Guest may want to complete payment later
- Need to handle gracefully

### Resolution: Payment Reminder Email

```python
# Background task: Send payment reminder emails

@shared_task
def send_payment_reminders():
    """
    Send reminder emails for bookings with pending payments.

    Schedule: Run every 10 minutes
    """
    with get_db_session() as db:
        # Find reserved bookings older than 10 minutes but not yet expired
        cutoff_old = datetime.utcnow() - timedelta(minutes=10)
        cutoff_expire = datetime.utcnow() - timedelta(minutes=BOOKING_RESERVATION_TIMEOUT_MINUTES)

        pending_bookings = db.query(Booking).filter(
            and_(
                Booking.status == BookingStatus.RESERVED.value,
                Booking.payment_status == PaymentStatus.PENDING.value,
                Booking.created_at < cutoff_old,
                Booking.created_at > cutoff_expire,
                Booking.payment_reminder_sent_at.is_(None),  # Not already sent
            )
        ).all()

        for booking in pending_bookings:
            send_payment_reminder_email.delay(str(booking.id))
            booking.payment_reminder_sent_at = datetime.utcnow()

        db.commit()


@shared_task
def send_payment_reminder_email(booking_id: str):
    """Send payment reminder email with direct payment link."""
    with get_db_session() as db:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()

        if not booking or booking.status != BookingStatus.RESERVED.value:
            return

        # Calculate remaining time
        expires_at = booking.created_at + timedelta(minutes=BOOKING_RESERVATION_TIMEOUT_MINUTES)
        remaining_minutes = int((expires_at - datetime.utcnow()).total_seconds() / 60)

        if remaining_minutes <= 0:
            return  # Already expired

        # Generate payment link
        payment_link = f"https://app.pms-webapp.com/booking/{booking.id}/payment"

        send_email(
            to=booking.guest.email,
            subject=f"Complete Your Booking - {remaining_minutes} minutes remaining",
            template="payment_reminder",
            data={
                "guest_name": booking.guest.first_name,
                "property_name": booking.property.name,
                "check_in": booking.check_in.strftime("%B %d, %Y"),
                "check_out": booking.check_out.strftime("%B %d, %Y"),
                "total_price": f"{booking.currency} {booking.total_price}",
                "remaining_minutes": remaining_minutes,
                "payment_link": payment_link,
                "expires_at": expires_at.strftime("%H:%M"),
            },
        )
```

### Frontend: Resume Payment Flow

```typescript
// app/booking/[bookingId]/payment/page.tsx

export default function PaymentPage({ params }: { params: { bookingId: string } }) {
  const [booking, setBooking] = useState<BookingReserved | null>(null)
  const [isExpired, setIsExpired] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadBooking() {
      try {
        const response = await fetch(`/api/v1/bookings/${params.bookingId}`)
        const data = await response.json()

        if (!response.ok) {
          setError(data.detail || 'Booking not found')
          return
        }

        // Check if booking is still valid for payment
        if (data.status === 'cancelled') {
          setError('This booking has been cancelled.')
          return
        }

        if (data.status === 'confirmed') {
          // Already paid - redirect to confirmation
          router.push(`/booking/${params.bookingId}/confirmation`)
          return
        }

        if (data.status !== 'reserved') {
          setError(`Cannot process payment for booking in status: ${data.status}`)
          return
        }

        // Check if expired
        const expiresAt = new Date(data.expires_at)
        if (expiresAt < new Date()) {
          setIsExpired(true)
          return
        }

        setBooking(data)

      } catch (err) {
        setError('Failed to load booking')
      }
    }

    loadBooking()
  }, [params.bookingId])

  if (isExpired) {
    return (
      <div className="text-center py-12">
        <XCircle className="h-16 w-16 text-destructive mx-auto mb-4" />
        <h1 className="text-2xl font-bold mb-2">Booking Expired</h1>
        <p className="text-muted-foreground mb-6">
          This booking reservation has expired. Please start a new booking.
        </p>
        <Button onClick={() => router.push(`/properties/${booking?.property_id}`)}>
          Book Again
        </Button>
      </div>
    )
  }

  // ... render payment form
}
```

---

## 6. Network Errors During Payment

### Scenario
Network connection fails during payment submission.

### Why It Matters
- Payment might have succeeded on Stripe's end
- User doesn't know if they need to retry
- Must handle gracefully without double-charging

### Detection & Resolution

```typescript
// Frontend: Handle network errors with status check

async function handlePaymentSubmit() {
  setIsProcessing(true)

  try {
    const { error, paymentIntent } = await stripe.confirmPayment({
      elements,
      redirect: 'if_required',
    })

    if (error) {
      // Stripe returned an error - safe to retry
      handlePaymentError(error)
      return
    }

    // Success!
    await confirmBooking(paymentIntent.id)
    onSuccess()

  } catch (err) {
    // Network error - payment status unknown
    handleNetworkError()
  } finally {
    setIsProcessing(false)
  }
}

async function handleNetworkError() {
  setError(null)
  setIsCheckingStatus(true)

  // Wait a moment for potential webhook
  await new Promise(resolve => setTimeout(resolve, 2000))

  // Check payment status
  try {
    const response = await fetch(`/api/v1/bookings/${bookingId}/payment-status`)
    const data = await response.json()

    switch (data.status) {
      case 'confirmed':
        // Payment succeeded! Redirect to confirmation
        onSuccess()
        break

      case 'processing':
        // Still processing - show appropriate message
        setError({
          type: 'processing',
          message: 'Your payment is being processed. Please wait...',
        })
        // Poll for status
        startStatusPolling()
        break

      case 'pending':
        // Payment didn't go through - safe to retry
        setError({
          type: 'network',
          message: 'Connection lost. Your payment was not processed. Please try again.',
        })
        break

      case 'expired':
        // Booking expired
        setError({
          type: 'expired',
          message: 'Your booking has expired. Please start a new booking.',
        })
        break

      default:
        setError({
          type: 'unknown',
          message: 'Unable to verify payment status. Please contact support.',
        })
    }
  } catch (checkError) {
    // Still can't connect - show support contact
    setError({
      type: 'offline',
      message: 'Unable to connect to our servers. Please check your internet connection.',
    })
  } finally {
    setIsCheckingStatus(false)
  }
}

function startStatusPolling() {
  const pollInterval = setInterval(async () => {
    try {
      const response = await fetch(`/api/v1/bookings/${bookingId}/payment-status`)
      const data = await response.json()

      if (data.status === 'confirmed') {
        clearInterval(pollInterval)
        onSuccess()
      } else if (data.status === 'failed' || data.status === 'expired') {
        clearInterval(pollInterval)
        setError({
          type: data.status,
          message: data.message,
        })
      }
    } catch (err) {
      // Keep polling
    }
  }, 3000) // Poll every 3 seconds

  // Stop polling after 2 minutes
  setTimeout(() => {
    clearInterval(pollInterval)
    setError({
      type: 'timeout',
      message: 'Payment verification timed out. Please contact support.',
    })
  }, 120000)
}
```

### Backend: Payment Status Endpoint

```python
@router.get("/bookings/{booking_id}/payment-status")
async def get_payment_status(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get current payment status for a booking.

    Used by frontend to recover from network errors.
    """
    booking = await db.get(Booking, booking_id)

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Check Stripe for latest status
    if booking.stripe_payment_intent_id:
        try:
            payment_intent = stripe.PaymentIntent.retrieve(booking.stripe_payment_intent_id)

            # Update local status if different
            if payment_intent.status == "succeeded" and booking.status == BookingStatus.RESERVED.value:
                # Webhook hasn't processed yet - confirm now
                await confirm_booking_internal(db, booking, payment_intent)

            return {
                "status": booking.status,
                "payment_status": booking.payment_status,
                "stripe_status": payment_intent.status,
            }
        except stripe.error.StripeError:
            pass

    return {
        "status": booking.status,
        "payment_status": booking.payment_status,
        "stripe_status": None,
    }
```

---

## 7. Partial Refund Scenarios

### Scenario
Guest cancels but is only entitled to partial refund based on cancellation policy.

### Resolution

```python
def calculate_refund_amount(booking: Booking) -> RefundCalculation:
    """
    Calculate refund amount based on cancellation policy.

    Returns:
        RefundCalculation with breakdown of refund
    """
    days_until_checkin = (booking.check_in - date.today()).days
    total_paid = booking.paid_amount or booking.total_price

    # Get property cancellation policy
    policy = get_cancellation_policy(booking.property_id)

    if policy.type == "flexible":
        # Full refund if cancelled 24+ hours before check-in
        if days_until_checkin >= 1:
            refund_percentage = Decimal("1.00")
        else:
            refund_percentage = Decimal("0.00")

    elif policy.type == "moderate":
        # Full refund if cancelled 7+ days before
        # 50% refund if cancelled 3-6 days before
        # No refund if cancelled < 3 days before
        if days_until_checkin >= 7:
            refund_percentage = Decimal("1.00")
        elif days_until_checkin >= 3:
            refund_percentage = Decimal("0.50")
        else:
            refund_percentage = Decimal("0.00")

    elif policy.type == "strict":
        # Full refund if cancelled 14+ days before
        # 50% refund if cancelled 7-13 days before
        # No refund if cancelled < 7 days before
        if days_until_checkin >= 14:
            refund_percentage = Decimal("1.00")
        elif days_until_checkin >= 7:
            refund_percentage = Decimal("0.50")
        else:
            refund_percentage = Decimal("0.00")

    else:
        # Custom policy
        refund_percentage = calculate_custom_refund(policy, days_until_checkin)

    refund_amount = (total_paid * refund_percentage).quantize(Decimal("0.01"))

    # Calculate fee retention
    service_fee_retained = Decimal("0")
    if refund_percentage < Decimal("1.00"):
        # Keep service fee on partial refunds
        service_fee_retained = booking.service_fee

    # Cleaning fee is always refunded (service not provided)
    cleaning_fee_refunded = booking.cleaning_fee if refund_amount > 0 else Decimal("0")

    return RefundCalculation(
        original_amount=total_paid,
        refund_amount=refund_amount,
        refund_percentage=refund_percentage,
        nights_refunded=calculate_nights_refunded(booking, refund_percentage),
        service_fee_retained=service_fee_retained,
        cleaning_fee_refunded=cleaning_fee_refunded,
        cancellation_policy=policy.type,
        days_until_checkin=days_until_checkin,
    )


@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: UUID,
    request: CancelBookingRequest,
    db: AsyncSession = Depends(get_db),
):
    """Cancel booking with partial refund calculation."""
    booking = await db.get(Booking, booking_id)

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Calculate refund
    refund_calc = calculate_refund_amount(booking)

    # Show confirmation before processing
    if not request.confirmed:
        return {
            "status": "confirmation_required",
            "refund_details": refund_calc.dict(),
            "message": f"You will receive a refund of {booking.currency} {refund_calc.refund_amount}",
        }

    # Process refund
    if refund_calc.refund_amount > 0 and booking.stripe_payment_intent_id:
        refund = await create_refund(
            payment_intent_id=booking.stripe_payment_intent_id,
            amount=refund_calc.refund_amount,
            reason="requested_by_customer",
        )

    # Update booking
    booking.status = BookingStatus.CANCELLED.value
    booking.refund_amount = refund_calc.refund_amount
    booking.cancelled_at = datetime.utcnow()
    booking.cancellation_reason = request.reason

    # Release dates
    await release_calendar_dates(db, booking)

    await db.commit()

    return {
        "status": "cancelled",
        "refund_amount": refund_calc.refund_amount,
        "refund_status": "processing",
    }
```

---

## 8. Summary Table

| Edge Case | Detection | Resolution | User Experience |
|-----------|-----------|------------|-----------------|
| Payment Timeout | Celery scheduled task | Auto-cancel + release dates + email | Timer + expiration message |
| Payment Failure | Stripe error response | Allow 3 retries, then cancel | Error message with retry button |
| Race Condition | Redis lock + DB constraint | First wins, second gets friendly error | "Dates just booked" message |
| Webhook Delay | Redis event cache + DB state | Idempotent processing | No visible impact |
| Browser Close | Check booking on page load | Payment reminder email | Email with payment link |
| Network Error | Catch fetch errors | Check payment status, poll if needed | Status checking UI |
| Partial Refund | Cancellation policy rules | Calculate based on days to check-in | Refund breakdown display |

---

## Related Documents

- [Direct Booking Flow](./direct-booking-flow.md)
- [Stripe Integration](./stripe-integration.md)
- [Backend API Routes](./backend-api-routes.py)
- [State Machine](./state-machine.mmd)
