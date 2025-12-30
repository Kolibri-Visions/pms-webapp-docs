# Direct Booking Engine - Stripe Integration

**Version:** 1.0.0
**Last Updated:** 2025-12-21
**Status:** Approved

---

## Overview

This document details the Stripe payment integration for the Direct Booking Engine using the **PaymentIntents API**. The integration follows Stripe's recommended payment flow for collecting payments while maintaining security and reliability.

### Why PaymentIntents API?

We use **PaymentIntents** (not Checkout Sessions) because:
1. Full control over the booking flow UI
2. Handle payment failures with retry logic
3. Support for 3D Secure authentication
4. Better webhook handling for async confirmations
5. Ability to hold bookings before payment completes

---

## 1. Payment Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PAYMENT FLOW ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FRONTEND (Next.js)                      BACKEND (FastAPI)                  │
│  ─────────────────                       ────────────────                    │
│                                                                              │
│  1. Guest Details Form                                                       │
│         │                                                                    │
│         ▼                                                                    │
│  [Continue to Payment] ─────────▶  POST /api/v1/bookings                    │
│                                         │                                    │
│                                         ▼                                    │
│                                    ┌───────────────────┐                    │
│                                    │ Validate Dates    │                    │
│                                    │ Check Availability │                   │
│                                    │ Calculate Price    │                    │
│                                    │ Create Guest       │                    │
│                                    └─────────┬─────────┘                    │
│                                              │                               │
│                                              ▼                               │
│                                    ┌───────────────────┐                    │
│                                    │ Create Stripe     │                    │
│                                    │ PaymentIntent     │                    │
│                                    └─────────┬─────────┘                    │
│                                              │                               │
│                                              ▼                               │
│                                    ┌───────────────────┐                    │
│                                    │ Create Booking    │                    │
│                                    │ status=reserved   │                    │
│                                    │ payment=pending   │                    │
│                                    └─────────┬─────────┘                    │
│                                              │                               │
│  ◀────────── client_secret ───────────────◀─┘                               │
│         │                                                                    │
│         ▼                                                                    │
│  2. Payment Page                                                             │
│  ┌───────────────────┐                                                       │
│  │ Stripe Elements   │                                                       │
│  │ PaymentElement    │                                                       │
│  └─────────┬─────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│  [Pay Now] ─────────────────────▶  Stripe API (directly)                    │
│                                    stripe.confirmPayment()                   │
│                                         │                                    │
│                                         ▼                                    │
│                              ┌─────────────────────┐                        │
│                              │ 3D Secure Required? │                        │
│                              └─────────┬───────────┘                        │
│                                        │                                     │
│                        ┌───────────────┴───────────────┐                    │
│                        ▼                               ▼                     │
│                   [No 3DS]                        [3DS Required]            │
│                        │                               │                     │
│                        ▼                               ▼                     │
│               Payment Succeeds               3DS Authentication              │
│                        │                          Modal Opens                │
│                        │                               │                     │
│                        └───────────────┬───────────────┘                    │
│                                        │                                     │
│                                        ▼                                     │
│                              Payment Result Returned                        │
│                                        │                                     │
│                        ┌───────────────┴───────────────┐                    │
│                        ▼                               ▼                     │
│                   [Succeeded]                     [Failed]                  │
│                        │                               │                     │
│                        ▼                               ▼                     │
│  POST /api/v1/bookings/{id}/confirm          Show Error + Retry             │
│         │                                                                    │
│         ▼                                                                    │
│  ┌───────────────────┐                                                       │
│  │ Verify Payment    │                                                       │
│  │ Update Booking    │                                                       │
│  │ status=confirmed  │                                                       │
│  │ payment=paid      │                                                       │
│  └─────────┬─────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│  3. Confirmation Page                                                        │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────── │
│                                                                              │
│  WEBHOOK (Backup)                                                            │
│  ─────────────────                                                           │
│                                                                              │
│  Stripe ───────────▶  POST /api/v1/webhooks/stripe                          │
│  payment_intent.         │                                                   │
│  succeeded               ▼                                                   │
│                    ┌───────────────────┐                                    │
│                    │ Idempotent Check  │                                    │
│                    │ Confirm Booking   │                                    │
│                    │ (if not already)  │                                    │
│                    └───────────────────┘                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Stripe Configuration

### 2.1 Environment Variables

```bash
# .env.local (Frontend)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

# .env (Backend)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 2.2 Stripe Dashboard Setup

1. **Enable Payment Methods:**
   - Cards (Visa, Mastercard, Amex)
   - SEPA Direct Debit (Europe)
   - iDEAL (Netherlands)
   - Bancontact (Belgium)
   - Giropay (Germany)

2. **Configure Webhooks:**
   - Endpoint URL: `https://api.pms-webapp.com/api/v1/webhooks/stripe`
   - Events to listen:
     - `payment_intent.succeeded`
     - `payment_intent.payment_failed`
     - `payment_intent.canceled`
     - `charge.refunded`
     - `charge.dispute.created`

3. **Set Up Radar Rules (Optional):**
   - Block high-risk payments
   - Request 3DS for amounts > 100 EUR
   - Allow only supported countries

---

## 3. Backend Implementation

### 3.1 PaymentIntent Creation

```python
import stripe
from decimal import Decimal
from datetime import datetime, timedelta

stripe.api_key = settings.STRIPE_SECRET_KEY

async def create_payment_intent(
    booking_id: UUID,
    amount: Decimal,
    currency: str,
    guest_email: str,
    property_id: UUID,
    check_in: date,
    check_out: date,
) -> stripe.PaymentIntent:
    """
    Create a Stripe PaymentIntent for a booking.

    Args:
        booking_id: UUID of the booking record
        amount: Total amount in major currency unit (e.g., 555.00 EUR)
        currency: ISO currency code (e.g., 'EUR')
        guest_email: Guest's email for receipt
        property_id: Property being booked
        check_in: Check-in date
        check_out: Check-out date

    Returns:
        Stripe PaymentIntent object with client_secret
    """
    # Convert to smallest currency unit (cents/pence)
    amount_cents = int(amount * 100)

    payment_intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency.lower(),

        # Automatic payment method selection
        automatic_payment_methods={
            "enabled": True,
        },

        # Receipt email (optional)
        receipt_email=guest_email,

        # Metadata for webhook processing
        metadata={
            "booking_id": str(booking_id),
            "property_id": str(property_id),
            "guest_email": guest_email,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "source": "direct_booking_engine",
        },

        # Description for statement
        description=f"Booking at PMS-Webapp ({check_in} to {check_out})",

        # Statement descriptor (max 22 chars)
        statement_descriptor="PMSWEBAPP BOOKING",

        # Capture method: automatic (charge immediately when confirmed)
        capture_method="automatic",

        # Optional: Set up for future use (for guest with account)
        # setup_future_usage="off_session",
    )

    return payment_intent
```

### 3.2 PaymentIntent Verification

```python
async def verify_payment_intent(
    payment_intent_id: str,
    expected_booking_id: UUID,
) -> dict:
    """
    Verify that a PaymentIntent has succeeded and matches the booking.

    Returns:
        {
            "valid": True/False,
            "status": "succeeded" | "requires_action" | "failed" | ...,
            "amount_received": Decimal,
            "error": None | str
        }
    """
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        # Verify metadata matches booking
        if payment_intent.metadata.get("booking_id") != str(expected_booking_id):
            return {
                "valid": False,
                "status": payment_intent.status,
                "error": "Payment intent does not match booking",
            }

        # Check status
        if payment_intent.status == "succeeded":
            return {
                "valid": True,
                "status": "succeeded",
                "amount_received": Decimal(payment_intent.amount_received) / 100,
                "charge_id": payment_intent.latest_charge,
                "error": None,
            }
        elif payment_intent.status == "requires_action":
            return {
                "valid": False,
                "status": "requires_action",
                "error": "3D Secure authentication required",
            }
        elif payment_intent.status == "requires_payment_method":
            return {
                "valid": False,
                "status": "requires_payment_method",
                "error": "Payment method failed",
            }
        else:
            return {
                "valid": False,
                "status": payment_intent.status,
                "error": f"Unexpected status: {payment_intent.status}",
            }

    except stripe.error.StripeError as e:
        return {
            "valid": False,
            "status": "error",
            "error": str(e),
        }
```

### 3.3 PaymentIntent Cancellation

```python
async def cancel_payment_intent(payment_intent_id: str) -> bool:
    """
    Cancel a PaymentIntent when booking expires.

    Returns:
        True if cancelled successfully, False otherwise
    """
    try:
        payment_intent = stripe.PaymentIntent.cancel(
            payment_intent_id,
            cancellation_reason="abandoned",
        )
        return payment_intent.status == "canceled"
    except stripe.error.InvalidRequestError as e:
        # PaymentIntent may already be cancelled or succeeded
        if "cannot be canceled" in str(e).lower():
            return False
        raise
```

### 3.4 Refund Processing

```python
from enum import Enum

class RefundType(Enum):
    FULL = "full"
    PARTIAL = "partial"

async def create_refund(
    payment_intent_id: str,
    amount: Optional[Decimal] = None,
    reason: str = "requested_by_customer",
) -> stripe.Refund:
    """
    Create a refund for a payment.

    Args:
        payment_intent_id: The PaymentIntent to refund
        amount: Amount to refund (None = full refund)
        reason: Refund reason (requested_by_customer, duplicate, fraudulent)

    Returns:
        Stripe Refund object
    """
    refund_params = {
        "payment_intent": payment_intent_id,
        "reason": reason,
    }

    if amount is not None:
        refund_params["amount"] = int(amount * 100)

    refund = stripe.Refund.create(**refund_params)

    return refund


async def get_refund_status(refund_id: str) -> dict:
    """Get the status of a refund."""
    refund = stripe.Refund.retrieve(refund_id)

    return {
        "id": refund.id,
        "status": refund.status,  # pending, succeeded, failed, canceled
        "amount": Decimal(refund.amount) / 100,
        "currency": refund.currency.upper(),
        "failure_reason": refund.failure_reason,
    }
```

---

## 4. Frontend Implementation

### 4.1 Stripe Provider Setup

```typescript
// app/providers/stripe-provider.tsx
'use client'

import { Elements } from '@stripe/react-stripe-js'
import { loadStripe, Stripe, StripeElementsOptions } from '@stripe/stripe-js'
import { ReactNode, useEffect, useState } from 'react'

// Initialize Stripe outside component to avoid recreating on re-render
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!)

interface StripeProviderProps {
  clientSecret: string
  children: ReactNode
}

export function StripeProvider({ clientSecret, children }: StripeProviderProps) {
  const options: StripeElementsOptions = {
    clientSecret,
    appearance: {
      theme: 'stripe',
      variables: {
        colorPrimary: '#0f172a',
        colorBackground: '#ffffff',
        colorText: '#1e293b',
        colorDanger: '#dc2626',
        fontFamily: 'Inter, system-ui, sans-serif',
        spacingUnit: '4px',
        borderRadius: '8px',
      },
      rules: {
        '.Input': {
          border: '1px solid #e2e8f0',
          boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        },
        '.Input:focus': {
          border: '1px solid #0f172a',
          boxShadow: '0 0 0 1px #0f172a',
        },
        '.Input--invalid': {
          border: '1px solid #dc2626',
        },
        '.Label': {
          fontWeight: '500',
        },
        '.Error': {
          color: '#dc2626',
          fontSize: '14px',
        },
      },
    },
    loader: 'auto',
  }

  return (
    <Elements stripe={stripePromise} options={options}>
      {children}
    </Elements>
  )
}
```

### 4.2 Payment Form Component

```typescript
// components/stripe-payment-form.tsx
'use client'

import { useState, FormEvent } from 'react'
import {
  PaymentElement,
  useStripe,
  useElements,
  AddressElement,
} from '@stripe/react-stripe-js'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { LockIcon, AlertCircleIcon, Loader2Icon } from 'lucide-react'

interface PaymentFormProps {
  bookingId: string
  amount: number
  currency: string
  onSuccess: () => void
  onError: (error: string) => void
}

export function StripePaymentForm({
  bookingId,
  amount,
  currency,
  onSuccess,
  onError,
}: PaymentFormProps) {
  const stripe = useStripe()
  const elements = useElements()

  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  const MAX_RETRIES = 3
  const currencySymbol = currency === 'EUR' ? '€' : currency

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()

    if (!stripe || !elements) {
      setError('Payment system not loaded. Please refresh the page.')
      return
    }

    if (!termsAccepted) {
      setError('Please accept the terms and conditions.')
      return
    }

    setIsProcessing(true)
    setError(null)

    try {
      // Confirm payment with Stripe
      const { error: stripeError, paymentIntent } = await stripe.confirmPayment({
        elements,
        redirect: 'if_required',
        confirmParams: {
          return_url: `${window.location.origin}/booking/${bookingId}/confirmation`,
          payment_method_data: {
            billing_details: {
              // Collected via AddressElement or manually
            },
          },
        },
      })

      if (stripeError) {
        // Handle specific error types
        if (stripeError.type === 'card_error') {
          // Card was declined
          handlePaymentError(stripeError.message || 'Your card was declined.')
        } else if (stripeError.type === 'validation_error') {
          // Form validation error
          setError(stripeError.message || 'Please check your payment details.')
        } else if (stripeError.type === 'invalid_request_error') {
          // Something went wrong on our end
          setError('An error occurred. Please try again.')
        } else {
          handlePaymentError(stripeError.message || 'Payment failed.')
        }
        return
      }

      if (paymentIntent) {
        switch (paymentIntent.status) {
          case 'succeeded':
            // Payment successful, confirm with backend
            await confirmBookingPayment(paymentIntent.id)
            onSuccess()
            break

          case 'processing':
            // Payment is being processed (e.g., bank transfer)
            setError('Your payment is being processed. You will receive a confirmation email once complete.')
            break

          case 'requires_action':
            // 3D Secure authentication was handled by Stripe Elements
            // If we reach here, something went wrong
            setError('Additional authentication required. Please try again.')
            break

          default:
            setError(`Unexpected payment status: ${paymentIntent.status}`)
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred'
      setError(message)
      onError(message)
    } finally {
      setIsProcessing(false)
    }
  }

  const handlePaymentError = (message: string) => {
    if (retryCount < MAX_RETRIES - 1) {
      setRetryCount((prev) => prev + 1)
      setError(`${message} (Attempt ${retryCount + 1}/${MAX_RETRIES})`)
    } else {
      setError(`Payment failed after ${MAX_RETRIES} attempts. ${message}`)
      onError(message)
    }
    setIsProcessing(false)
  }

  const confirmBookingPayment = async (paymentIntentId: string) => {
    const response = await fetch(`/api/v1/bookings/${bookingId}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payment_intent_id: paymentIntentId }),
    })

    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to confirm booking')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertCircleIcon className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Payment Element - renders card input + other payment methods */}
      <div className="space-y-4">
        <h3 className="font-semibold">Payment Method</h3>
        <PaymentElement
          options={{
            layout: {
              type: 'tabs',
              defaultCollapsed: false,
            },
            wallets: {
              applePay: 'auto',
              googlePay: 'auto',
            },
          }}
        />
      </div>

      {/* Billing Address (optional - can be collected in PaymentElement) */}
      <div className="space-y-4">
        <h3 className="font-semibold">Billing Address</h3>
        <AddressElement
          options={{
            mode: 'billing',
            autocomplete: {
              mode: 'google_maps_api',
              apiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
            },
          }}
        />
      </div>

      {/* Terms acceptance */}
      <div className="flex items-start space-x-3">
        <Checkbox
          id="terms"
          checked={termsAccepted}
          onCheckedChange={(checked) => setTermsAccepted(checked === true)}
        />
        <label htmlFor="terms" className="text-sm leading-relaxed">
          I agree to the{' '}
          <a href="/terms" target="_blank" className="underline">
            Terms of Service
          </a>{' '}
          and{' '}
          <a href="/privacy" target="_blank" className="underline">
            Privacy Policy
          </a>
          , and I understand the cancellation policy.
        </label>
      </div>

      {/* Submit button */}
      <Button
        type="submit"
        className="w-full"
        size="lg"
        disabled={!stripe || !elements || isProcessing || !termsAccepted}
      >
        {isProcessing ? (
          <>
            <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <LockIcon className="mr-2 h-4 w-4" />
            Pay {currencySymbol}{amount.toFixed(2)} & Confirm Booking
          </>
        )}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Your payment is secure and encrypted. Powered by Stripe.
      </p>
    </form>
  )
}
```

### 4.3 3D Secure Handling

3D Secure (3DS) is automatically handled by Stripe Elements:

```typescript
// The confirmPayment method handles 3DS automatically
const { error, paymentIntent } = await stripe.confirmPayment({
  elements,
  redirect: 'if_required',  // Key: only redirect if 3DS requires it
  confirmParams: {
    return_url: `${window.location.origin}/booking/${bookingId}/confirmation`,
  },
})

// If 3DS is required:
// 1. Stripe Elements opens a modal for authentication
// 2. User completes 3DS verification
// 3. Modal closes
// 4. paymentIntent.status === 'succeeded' if verified

// If redirect is required (some banks):
// 1. User is redirected to bank's 3DS page
// 2. After verification, redirected to return_url
// 3. We handle the result on the confirmation page
```

### 4.4 Handling Redirect Returns

```typescript
// app/booking/[bookingId]/confirmation/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { loadStripe } from '@stripe/stripe-js'

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!)

export default function ConfirmationPage({ params }: { params: { bookingId: string } }) {
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const handlePaymentResult = async () => {
      const paymentIntentClientSecret = searchParams.get('payment_intent_client_secret')
      const redirectStatus = searchParams.get('redirect_status')

      if (!paymentIntentClientSecret) {
        // Direct navigation without payment redirect
        // Check booking status from backend
        await checkBookingStatus()
        return
      }

      // Handle redirect return from 3DS
      const stripe = await stripePromise
      if (!stripe) {
        setError('Failed to load payment system')
        setStatus('error')
        return
      }

      const { paymentIntent, error } = await stripe.retrievePaymentIntent(
        paymentIntentClientSecret
      )

      if (error) {
        setError(error.message || 'Failed to verify payment')
        setStatus('error')
        return
      }

      switch (paymentIntent?.status) {
        case 'succeeded':
          // Confirm with backend (idempotent)
          await confirmBooking(paymentIntent.id)
          setStatus('success')
          break

        case 'processing':
          setStatus('loading')
          // Poll for status updates
          break

        case 'requires_payment_method':
          setError('Payment was not completed. Please try again.')
          setStatus('error')
          break

        default:
          setError(`Unexpected status: ${paymentIntent?.status}`)
          setStatus('error')
      }
    }

    handlePaymentResult()
  }, [searchParams, params.bookingId])

  // ... render confirmation UI based on status
}
```

---

## 5. Webhook Implementation

### 5.1 Webhook Handler

```python
# app/api/webhooks/stripe.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import stripe
import hashlib
import json
from datetime import datetime

router = APIRouter()

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    """
    Handle Stripe webhook events.

    Security:
    - Verify webhook signature using STRIPE_WEBHOOK_SECRET
    - Prevent replay attacks with event ID caching

    Idempotency:
    - Cache event IDs in Redis for 24 hours
    - Skip already-processed events

    Events Handled:
    - payment_intent.succeeded: Confirm booking
    - payment_intent.payment_failed: Mark payment failed
    - payment_intent.canceled: Cancel booking if still reserved
    - charge.refunded: Update booking refund status
    - charge.dispute.created: Alert for manual review
    """
    # Get raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Idempotency check
    event_id = event.id
    cache_key = f"stripe_event:{event_id}"

    if await redis.exists(cache_key):
        # Already processed, return success
        return JSONResponse({"status": "already_processed"})

    # Route to appropriate handler
    try:
        if event.type == "payment_intent.succeeded":
            await handle_payment_succeeded(event.data.object, db)

        elif event.type == "payment_intent.payment_failed":
            await handle_payment_failed(event.data.object, db)

        elif event.type == "payment_intent.canceled":
            await handle_payment_canceled(event.data.object, db)

        elif event.type == "charge.refunded":
            await handle_charge_refunded(event.data.object, db)

        elif event.type == "charge.dispute.created":
            await handle_dispute_created(event.data.object, db)

        else:
            # Log unhandled event types for monitoring
            logger.info(f"Unhandled Stripe event: {event.type}")

    except Exception as e:
        # Log error but return 200 to prevent Stripe retries for app errors
        logger.error(f"Error handling Stripe event {event_id}: {str(e)}")
        # For critical errors, we might want to return 500 for Stripe retry
        # raise HTTPException(status_code=500, detail=str(e))

    # Mark event as processed (24h TTL)
    await redis.setex(cache_key, 86400, "processed")

    return JSONResponse({"status": "success"})


async def handle_payment_succeeded(
    payment_intent: dict,
    db: AsyncSession,
) -> None:
    """
    Handle successful payment.

    This is a backup to frontend confirmation.
    Uses idempotent logic to avoid double-processing.
    """
    booking_id = payment_intent["metadata"].get("booking_id")
    if not booking_id:
        logger.warning(f"Payment succeeded without booking_id: {payment_intent['id']}")
        return

    # Get booking
    booking = await db.get(Booking, UUID(booking_id))
    if not booking:
        logger.error(f"Booking not found for payment: {booking_id}")
        return

    # Idempotent: skip if already confirmed
    if booking.status == BookingStatus.CONFIRMED.value:
        return

    # Only confirm if in reserved state
    if booking.status != BookingStatus.RESERVED.value:
        logger.warning(
            f"Cannot confirm booking {booking_id} in state {booking.status}"
        )
        return

    # Confirm the booking
    now = datetime.utcnow()
    booking.status = BookingStatus.CONFIRMED.value
    booking.payment_status = PaymentStatus.PAID.value
    booking.paid_amount = Decimal(payment_intent["amount_received"]) / 100
    booking.paid_at = now
    booking.confirmed_at = now
    booking.updated_at = now

    # Update calendar
    await update_calendar_to_booked(db, booking)

    # Create payment transaction record
    await create_payment_transaction(
        db,
        booking=booking,
        payment_intent_id=payment_intent["id"],
        charge_id=payment_intent.get("latest_charge"),
    )

    await db.commit()

    # Send confirmation email (fire and forget)
    asyncio.create_task(send_booking_confirmation_email(booking.id))

    # Publish event for channel sync
    await publish_event("booking.confirmed", {
        "booking_id": str(booking.id),
        "property_id": str(booking.property_id),
    })


async def handle_payment_failed(
    payment_intent: dict,
    db: AsyncSession,
) -> None:
    """Handle failed payment attempt."""
    booking_id = payment_intent["metadata"].get("booking_id")
    if not booking_id:
        return

    booking = await db.get(Booking, UUID(booking_id))
    if not booking:
        return

    # Update payment status
    booking.payment_status = PaymentStatus.FAILED.value
    booking.updated_at = datetime.utcnow()

    # Store failure reason
    last_error = payment_intent.get("last_payment_error", {})
    booking.payment_failure_reason = last_error.get("message")

    await db.commit()

    # Optionally send notification to guest
    # await send_payment_failed_email(booking.id)


async def handle_payment_canceled(
    payment_intent: dict,
    db: AsyncSession,
) -> None:
    """Handle canceled PaymentIntent (e.g., from timeout)."""
    booking_id = payment_intent["metadata"].get("booking_id")
    if not booking_id:
        return

    booking = await db.get(Booking, UUID(booking_id))
    if not booking or booking.status != BookingStatus.RESERVED.value:
        return

    # Cancel the booking
    booking.status = BookingStatus.CANCELLED.value
    booking.payment_status = PaymentStatus.EXPIRED.value
    booking.cancelled_at = datetime.utcnow()
    booking.cancellation_reason = "Payment canceled"
    booking.updated_at = datetime.utcnow()

    # Release calendar dates
    await release_calendar_dates(db, booking)

    await db.commit()


async def handle_charge_refunded(
    charge: dict,
    db: AsyncSession,
) -> None:
    """Handle charge refund."""
    # Find booking by charge ID
    query = select(Booking).where(Booking.stripe_charge_id == charge["id"])
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        return

    # Update refund amount
    refund_amount = Decimal(charge["amount_refunded"]) / 100
    booking.refund_amount = refund_amount
    booking.updated_at = datetime.utcnow()

    # If fully refunded, update status
    if charge["refunded"]:
        booking.payment_status = PaymentStatus.REFUNDED.value

    await db.commit()


async def handle_dispute_created(
    dispute: dict,
    db: AsyncSession,
) -> None:
    """
    Handle chargeback/dispute.

    This requires manual intervention.
    """
    charge_id = dispute["charge"]

    # Find booking
    query = select(Booking).where(Booking.stripe_charge_id == charge_id)
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        return

    # Log dispute for manual review
    logger.critical(
        f"DISPUTE CREATED: Booking {booking.id}, "
        f"Amount: {dispute['amount']}, "
        f"Reason: {dispute['reason']}"
    )

    # Send alert to operations team
    await send_dispute_alert(
        booking_id=booking.id,
        dispute_id=dispute["id"],
        amount=Decimal(dispute["amount"]) / 100,
        reason=dispute["reason"],
    )
```

### 5.2 Webhook Security

```python
# Signature verification is automatic with stripe.Webhook.construct_event()

# Additional security measures:

def is_valid_stripe_ip(request: Request) -> bool:
    """
    Validate request comes from Stripe's IP range.

    Note: This is optional as signature verification is sufficient.
    Stripe's webhook IPs: https://stripe.com/docs/ips
    """
    stripe_ips = [
        "3.18.12.63",
        "3.130.192.231",
        "13.235.14.237",
        "13.235.122.149",
        "18.211.135.69",
        "35.154.171.200",
        "52.15.183.38",
        "54.88.130.119",
        "54.88.130.237",
        "54.187.174.169",
        "54.187.205.235",
        "54.187.216.72",
    ]

    client_ip = request.client.host
    forwarded_for = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()

    return client_ip in stripe_ips or forwarded_for in stripe_ips


def validate_webhook_timestamp(sig_header: str, tolerance: int = 300) -> bool:
    """
    Validate webhook timestamp to prevent replay attacks.

    Stripe signs webhooks with a timestamp. We reject events
    older than tolerance seconds (default: 5 minutes).
    """
    # Extract timestamp from signature header
    # Format: t=1234567890,v1=xxx,v0=yyy
    parts = {
        k: v for k, v in
        (part.split("=") for part in sig_header.split(","))
    }

    timestamp = int(parts.get("t", 0))
    current_time = int(time.time())

    return abs(current_time - timestamp) <= tolerance
```

---

## 6. Error Handling

### 6.1 Payment Error Types

```typescript
// Frontend error handling

interface PaymentError {
  type: 'card_error' | 'validation_error' | 'api_error' | 'authentication_error'
  code?: string
  message: string
  decline_code?: string
}

const errorMessages: Record<string, string> = {
  // Card errors
  'card_declined': 'Your card was declined. Please try a different card.',
  'insufficient_funds': 'Insufficient funds. Please use a different card.',
  'expired_card': 'Your card has expired. Please use a different card.',
  'incorrect_cvc': 'The CVC code is incorrect. Please check and try again.',
  'incorrect_number': 'The card number is incorrect. Please check and try again.',
  'processing_error': 'An error occurred while processing your card. Please try again.',

  // Authentication errors
  'authentication_required': 'Your bank requires additional authentication.',

  // Generic errors
  'generic_decline': 'Your card was declined. Please contact your bank or try a different card.',
  'try_again_later': 'Unable to process payment. Please try again in a few minutes.',
}

function getErrorMessage(error: PaymentError): string {
  // Check for specific decline code
  if (error.decline_code && errorMessages[error.decline_code]) {
    return errorMessages[error.decline_code]
  }

  // Check for error code
  if (error.code && errorMessages[error.code]) {
    return errorMessages[error.code]
  }

  // Use Stripe's message or fallback
  return error.message || 'An error occurred. Please try again.'
}
```

### 6.2 Backend Error Handling

```python
# Custom exception for payment failures

class PaymentError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "payment_error",
        recoverable: bool = True,
    ):
        self.message = message
        self.code = code
        self.recoverable = recoverable
        super().__init__(self.message)


# Error handler in create_booking endpoint

try:
    payment_intent = stripe.PaymentIntent.create(...)
except stripe.error.CardError as e:
    # Card was declined
    err = e.error
    raise HTTPException(
        status_code=402,
        detail={
            "code": err.code,
            "message": err.message,
            "decline_code": err.decline_code,
            "recoverable": True,
        }
    )
except stripe.error.RateLimitError:
    # Too many requests
    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please try again in a moment."
    )
except stripe.error.InvalidRequestError as e:
    # Invalid parameters
    logger.error(f"Invalid Stripe request: {e}")
    raise HTTPException(
        status_code=400,
        detail="Invalid payment request. Please try again."
    )
except stripe.error.AuthenticationError:
    # API key issues
    logger.critical("Stripe authentication failed - check API keys")
    raise HTTPException(
        status_code=500,
        detail="Payment system configuration error."
    )
except stripe.error.APIConnectionError:
    # Network issues
    raise HTTPException(
        status_code=503,
        detail="Unable to connect to payment provider. Please try again."
    )
except stripe.error.StripeError as e:
    # Generic Stripe error
    logger.error(f"Stripe error: {e}")
    raise HTTPException(
        status_code=500,
        detail="Payment processing error. Please try again."
    )
```

---

## 7. Testing

### 7.1 Test Cards

| Scenario | Card Number | Result |
|----------|-------------|--------|
| Success | 4242424242424242 | Payment succeeds |
| Decline | 4000000000000002 | Generic decline |
| Insufficient funds | 4000000000009995 | Insufficient funds |
| 3DS Required | 4000002500003155 | Requires authentication |
| 3DS Always | 4000002760003184 | Always requires 3DS |

### 7.2 Webhook Testing

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe

# Trigger test events
stripe trigger payment_intent.succeeded
stripe trigger payment_intent.payment_failed
stripe trigger charge.refunded
```

### 7.3 Integration Tests

```python
# tests/test_payment_integration.py

import pytest
from httpx import AsyncClient
import stripe

@pytest.mark.asyncio
async def test_successful_payment_flow(
    client: AsyncClient,
    db: AsyncSession,
    mock_stripe,
):
    """Test complete successful payment flow."""
    # 1. Create booking (gets client_secret)
    response = await client.post("/api/v1/bookings", json={
        "property_id": "test-property-id",
        "check_in": "2025-03-01",
        "check_out": "2025-03-05",
        "num_guests": 2,
        "guest": {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
        },
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reserved"
    assert "stripe_client_secret" in data

    booking_id = data["booking_id"]

    # 2. Simulate Stripe payment confirmation
    mock_stripe.PaymentIntent.retrieve.return_value = MockPaymentIntent(
        id="pi_test",
        status="succeeded",
        amount_received=55500,
    )

    # 3. Confirm booking
    response = await client.post(
        f"/api/v1/bookings/{booking_id}/confirm",
        json={"payment_intent_id": "pi_test"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

    # 4. Verify booking in database
    booking = await db.get(Booking, booking_id)
    assert booking.status == "confirmed"
    assert booking.payment_status == "paid"


@pytest.mark.asyncio
async def test_webhook_idempotency(
    client: AsyncClient,
    redis: Redis,
):
    """Test that webhooks are processed only once."""
    event_payload = create_webhook_payload("payment_intent.succeeded")

    # First call
    response1 = await client.post(
        "/api/v1/webhooks/stripe",
        content=event_payload,
        headers={"stripe-signature": create_signature(event_payload)},
    )
    assert response1.json()["status"] == "success"

    # Second call (same event)
    response2 = await client.post(
        "/api/v1/webhooks/stripe",
        content=event_payload,
        headers={"stripe-signature": create_signature(event_payload)},
    )
    assert response2.json()["status"] == "already_processed"
```

---

## 8. Monitoring & Alerts

### 8.1 Metrics

```python
# Prometheus metrics for payment monitoring

from prometheus_client import Counter, Histogram

payment_attempts = Counter(
    "payment_attempts_total",
    "Total payment attempts",
    ["status", "currency"]
)

payment_latency = Histogram(
    "payment_processing_seconds",
    "Payment processing latency",
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)

webhook_events = Counter(
    "stripe_webhook_events_total",
    "Stripe webhook events received",
    ["event_type", "status"]
)
```

### 8.2 Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| High Payment Failure Rate | > 10% failures in 5 min | Warning |
| Webhook Processing Lag | > 100 unprocessed events | Warning |
| Stripe API Errors | > 5 errors in 1 min | Critical |
| Dispute Created | Any dispute | Critical |
| Payment Timeout Rate | > 5% timeouts in 1 hour | Warning |

---

## Appendix A: Currency Handling

```python
# Stripe uses smallest currency unit (cents, pence, etc.)

ZERO_DECIMAL_CURRENCIES = {
    'BIF', 'CLP', 'DJF', 'GNF', 'JPY', 'KMF', 'KRW',
    'MGA', 'PYG', 'RWF', 'UGX', 'VND', 'VUV', 'XAF',
    'XOF', 'XPF',
}

def to_stripe_amount(amount: Decimal, currency: str) -> int:
    """Convert amount to Stripe's smallest unit."""
    if currency.upper() in ZERO_DECIMAL_CURRENCIES:
        return int(amount)
    return int(amount * 100)

def from_stripe_amount(amount: int, currency: str) -> Decimal:
    """Convert Stripe amount back to major unit."""
    if currency.upper() in ZERO_DECIMAL_CURRENCIES:
        return Decimal(amount)
    return Decimal(amount) / 100
```

---

## Appendix B: Related Documents

- [Direct Booking Flow](./direct-booking-flow.md)
- [Backend API Routes](./backend-api-routes.py)
- [Edge Cases](./edge-cases.md)
- [Stripe Dashboard Setup Guide](./stripe-setup-guide.md) (TBD)
