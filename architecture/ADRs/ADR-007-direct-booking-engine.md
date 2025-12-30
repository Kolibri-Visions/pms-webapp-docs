# ADR-007: Direct Booking Engine Design

**Status:** Accepted
**Date:** 2025-12-21
**Decision Makers:** System Architecture Team

---

## Context

The Direct Booking Engine enables guests to book properties directly through the PMS-Webapp, bypassing external channel platforms. This engine must:
- Provide a seamless booking experience comparable to Airbnb/Booking.com
- Integrate with PMS-Core as the source of truth
- Handle payments securely
- Prevent double-bookings during the checkout flow
- Support multiple currencies and payment methods
- Trigger channel sync after booking confirmation

## Decision Drivers

1. **User Experience**: Frictionless booking flow with minimal steps
2. **Security**: PCI-DSS compliant payment handling
3. **Reliability**: Prevent double-bookings and race conditions
4. **Integration**: Seamless sync with Channel Manager
5. **Flexibility**: Support various property types and pricing models

## Booking Flow Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DIRECT BOOKING FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────────┐ │
│  │  Search   │──▶│  View     │──▶│ Select    │──▶│   Checkout    │ │
│  │Properties │   │ Property  │   │  Dates    │   │   (3 steps)   │ │
│  └───────────┘   └───────────┘   └───────────┘   └───────┬───────┘ │
│                                                           │         │
│                       ┌───────────────────────────────────┘         │
│                       ▼                                             │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ CHECKOUT FLOW                                                  │ │
│  │                                                                │ │
│  │  Step 1: Guest Details                                        │ │
│  │  ┌─────────────────────────────────────────────────────────┐  │ │
│  │  │ Name, Email, Phone, Country                             │  │ │
│  │  │ [Optional: Create account]                              │  │ │
│  │  └─────────────────────────────────────────────────────────┘  │ │
│  │                           │                                    │ │
│  │                           ▼                                    │ │
│  │  Step 2: Special Requests (Optional)                          │ │
│  │  ┌─────────────────────────────────────────────────────────┐  │ │
│  │  │ Early check-in, Late checkout, Extra amenities          │  │ │
│  │  └─────────────────────────────────────────────────────────┘  │ │
│  │                           │                                    │ │
│  │                           ▼                                    │ │
│  │  Step 3: Payment                                              │ │
│  │  ┌─────────────────────────────────────────────────────────┐  │ │
│  │  │ [Stripe Payment Element]                                │  │ │
│  │  │ Credit Card / Apple Pay / Google Pay / SEPA             │  │ │
│  │  └─────────────────────────────────────────────────────────┘  │ │
│  │                           │                                    │ │
│  └───────────────────────────┼────────────────────────────────────┘ │
│                               ▼                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ CONFIRMATION                                                   │ │
│  │  ✓ Booking Confirmed                                          │ │
│  │  Booking #: PMS-2024-12345                                    │ │
│  │  [Email confirmation sent]                                    │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Decision

We implement a **stateful checkout with distributed locking and Stripe PaymentIntents**.

### Key Design Decisions

1. **Distributed Lock During Checkout**: Acquire Redis lock when guest enters checkout, hold until payment success or timeout.

2. **Stripe PaymentIntents**: Create PaymentIntent at checkout start, confirm on client, finalize booking on webhook.

3. **Booking States**: `inquiry` → `reserved` (lock held) → `confirmed` (payment success) → lifecycle states.

4. **Server-Side Pricing**: Never trust client-submitted prices; always recalculate on server.

5. **Idempotent Confirmation**: Stripe webhook may arrive before or after client confirmation; handle both.

## Implementation

### Step 1: Start Checkout (Lock Acquisition)

```python
# POST /api/bookings/checkout/start
@app.post("/api/bookings/checkout/start")
async def start_checkout(
    request: CheckoutStartRequest,
    background_tasks: BackgroundTasks
) -> CheckoutSession:
    """
    Start checkout flow. Acquires calendar lock and creates PaymentIntent.
    """

    # Validate property exists and is bookable
    property = await get_property(request.property_id)
    if not property or property.status != 'active':
        raise HTTPException(404, "Property not available")

    # Validate dates
    if request.check_in >= request.check_out:
        raise HTTPException(400, "Invalid date range")

    if request.check_in < date.today():
        raise HTTPException(400, "Cannot book in the past")

    # Acquire calendar lock (10 minute hold for checkout)
    lock_key = f"checkout:lock:{request.property_id}:{request.check_in.isoformat()}"
    lock = await redis.lock(lock_key, timeout=600)

    if not await lock.acquire(blocking_timeout=5):
        raise HTTPException(
            409,
            "This property is currently being booked by another guest. Please try again shortly."
        )

    try:
        # Verify availability while holding lock
        if not await check_availability(request.property_id, request.check_in, request.check_out):
            await lock.release()
            raise HTTPException(409, "Selected dates are no longer available")

        # Calculate pricing
        pricing = await calculate_booking_price(
            property=property,
            check_in=request.check_in,
            check_out=request.check_out,
            guests=request.guests
        )

        # Create booking in RESERVED state
        booking = await create_booking(
            property_id=request.property_id,
            check_in=request.check_in,
            check_out=request.check_out,
            guests=request.guests,
            status='reserved',
            source='direct',
            total_price=pricing.total,
            currency=property.currency
        )

        # Create Stripe PaymentIntent
        payment_intent = await stripe.PaymentIntent.create(
            amount=int(pricing.total * 100),  # Cents
            currency=property.currency.lower(),
            metadata={
                'booking_id': str(booking.id),
                'property_id': str(property.id),
                'check_in': request.check_in.isoformat(),
                'check_out': request.check_out.isoformat(),
            },
            automatic_payment_methods={'enabled': True},
        )

        # Store PaymentIntent ID with booking
        await update_booking_payment_intent(booking.id, payment_intent.id)

        # Store lock key for cleanup
        await redis.setex(
            f"booking:lock_key:{booking.id}",
            600,  # 10 minutes
            lock_key
        )

        # Schedule lock release if checkout times out
        background_tasks.add_task(
            schedule_lock_release,
            booking_id=booking.id,
            lock_key=lock_key,
            delay=600
        )

        return CheckoutSession(
            booking_id=booking.id,
            property=property.to_summary(),
            check_in=request.check_in,
            check_out=request.check_out,
            guests=request.guests,
            pricing=pricing,
            client_secret=payment_intent.client_secret,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )

    except Exception as e:
        await lock.release()
        raise
```

### Step 2: Collect Guest Details

```python
# POST /api/bookings/checkout/{booking_id}/guest
@app.post("/api/bookings/checkout/{booking_id}/guest")
async def update_guest_details(
    booking_id: UUID,
    request: GuestDetailsRequest
) -> BookingResponse:
    """
    Update guest details for the booking.
    Can be called multiple times during checkout.
    """

    booking = await get_booking(booking_id)
    if not booking or booking.status != 'reserved':
        raise HTTPException(400, "Invalid checkout session")

    # Validate checkout hasn't expired
    lock_key = await redis.get(f"booking:lock_key:{booking_id}")
    if not lock_key:
        raise HTTPException(410, "Checkout session expired. Please start again.")

    # Create or find guest
    guest = await find_or_create_guest(
        email=request.email,
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        country=request.country
    )

    # Update booking with guest
    booking = await update_booking(
        booking_id=booking_id,
        guest_id=guest.id,
        special_requests=request.special_requests
    )

    return BookingResponse.from_orm(booking)
```

### Step 3: Confirm Payment (Client-Side)

```tsx
// Frontend: Stripe Payment Element
'use client';

import { useStripe, useElements, PaymentElement } from '@stripe/react-stripe-js';

export function PaymentForm({ clientSecret, bookingId, onSuccess }: PaymentFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setIsProcessing(true);
    setError(null);

    const { error: paymentError, paymentIntent } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/booking/${bookingId}/confirm`,
      },
      redirect: 'if_required',
    });

    if (paymentError) {
      setError(paymentError.message || 'Payment failed');
      setIsProcessing(false);
      return;
    }

    if (paymentIntent?.status === 'succeeded') {
      // Payment succeeded, confirm booking
      await confirmBooking(bookingId);
      onSuccess();
    }

    setIsProcessing(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <PaymentElement />
      {error && <div className="text-red-500 mt-2">{error}</div>}
      <button
        type="submit"
        disabled={!stripe || isProcessing}
        className="w-full mt-4 btn btn-primary"
      >
        {isProcessing ? 'Processing...' : 'Confirm & Pay'}
      </button>
    </form>
  );
}
```

### Step 4: Finalize Booking (Webhook)

```python
# POST /webhooks/stripe
@app.post("/webhooks/stripe")
async def handle_stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    This is the source of truth for payment status.
    """

    # Verify webhook signature
    payload = await request.body()
    sig = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        booking_id = payment_intent['metadata']['booking_id']

        # Idempotency: Check if already confirmed
        booking = await get_booking(booking_id)
        if booking.status == 'confirmed':
            return {"status": "already_confirmed"}

        # Confirm booking
        booking = await update_booking(
            booking_id=booking_id,
            status='confirmed',
            payment_status='paid',
            payment_intent_id=payment_intent['id']
        )

        # Release calendar lock
        lock_key = await redis.get(f"booking:lock_key:{booking_id}")
        if lock_key:
            await redis.delete(lock_key)
            await redis.delete(f"booking:lock_key:{booking_id}")

        # Emit event for channel sync
        await emit_event(EventType.BOOKING_CREATED, booking, source='direct')

        # Send confirmation email
        await send_booking_confirmation_email(booking)

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        booking_id = payment_intent['metadata']['booking_id']

        # Log failure but don't cancel yet (guest may retry)
        logger.warning(f"Payment failed for booking {booking_id}")

    return {"status": "ok"}
```

### Pricing Calculation

```python
async def calculate_booking_price(
    property: Property,
    check_in: date,
    check_out: date,
    guests: int
) -> BookingPricing:
    """
    Calculate total booking price including all fees.
    """

    nights = (check_out - check_in).days

    # Get base price per night (may vary by date)
    daily_prices = []
    current_date = check_in
    while current_date < check_out:
        # Check for price overrides
        override = await get_price_override(property.id, current_date)
        if override:
            price = override.price
        else:
            price = property.base_price

        # Apply pricing rules
        rules = await get_pricing_rules(property.id, current_date, nights)
        for rule in rules:
            if rule.rule_type == 'weekend' and current_date.weekday() >= 5:
                price = apply_adjustment(price, rule)
            elif rule.rule_type == 'seasonal':
                if rule.conditions.get('season') == get_season(current_date):
                    price = apply_adjustment(price, rule)
            elif rule.rule_type == 'length_of_stay':
                if nights >= rule.conditions.get('min_nights', 0):
                    price = apply_adjustment(price, rule)

        daily_prices.append(DailyPrice(date=current_date, price=price))
        current_date += timedelta(days=1)

    subtotal = sum(dp.price for dp in daily_prices)

    # Cleaning fee (flat)
    cleaning_fee = property.cleaning_fee or Decimal('0')

    # Service fee (percentage)
    service_fee_rate = Decimal('0.10')  # 10%
    service_fee = subtotal * service_fee_rate

    # Taxes (varies by location)
    tax_rate = await get_tax_rate(property.address.country, property.address.state)
    taxes = (subtotal + cleaning_fee + service_fee) * tax_rate

    total = subtotal + cleaning_fee + service_fee + taxes

    return BookingPricing(
        nights=nights,
        daily_prices=daily_prices,
        price_per_night=subtotal / nights,
        subtotal=subtotal,
        cleaning_fee=cleaning_fee,
        service_fee=service_fee,
        taxes=taxes,
        total=total,
        currency=property.currency
    )
```

### Booking Lifecycle

```python
class BookingStatus(str, Enum):
    INQUIRY = 'inquiry'         # Optional: Guest inquires, no hold
    RESERVED = 'reserved'       # Checkout started, dates locked, payment pending
    CONFIRMED = 'confirmed'     # Payment received, booking active
    CHECKED_IN = 'checked_in'   # Guest has arrived
    CHECKED_OUT = 'checked_out' # Guest has departed, booking complete
    CANCELLED = 'cancelled'     # Booking cancelled (any stage before check-in)


class BookingStateMachine:
    """Valid state transitions for bookings."""

    TRANSITIONS = {
        BookingStatus.INQUIRY: [BookingStatus.RESERVED, BookingStatus.CANCELLED],
        BookingStatus.RESERVED: [BookingStatus.CONFIRMED, BookingStatus.CANCELLED],
        BookingStatus.CONFIRMED: [BookingStatus.CHECKED_IN, BookingStatus.CANCELLED],
        BookingStatus.CHECKED_IN: [BookingStatus.CHECKED_OUT],
        BookingStatus.CHECKED_OUT: [],  # Terminal state
        BookingStatus.CANCELLED: [],     # Terminal state
    }

    @classmethod
    def can_transition(cls, from_status: BookingStatus, to_status: BookingStatus) -> bool:
        return to_status in cls.TRANSITIONS.get(from_status, [])

    @classmethod
    def transition(cls, booking: Booking, new_status: BookingStatus) -> Booking:
        if not cls.can_transition(booking.status, new_status):
            raise InvalidStateTransition(
                f"Cannot transition from {booking.status} to {new_status}"
            )
        booking.status = new_status
        return booking
```

## Consequences

### Positive

- Secure payment handling via Stripe
- No double-bookings (lock + constraint)
- Fast, responsive checkout experience
- Full audit trail of booking states
- Seamless channel sync after confirmation

### Negative

- Checkout timeout may frustrate slow users
- Lock management adds complexity
- Multiple webhook scenarios to handle

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Lock expires during payment | Watchdog extends lock during active payment |
| Stripe webhook arrives late | Client-side confirmation + webhook idempotent |
| Guest abandons checkout | Background job cancels after 30 min, releases lock |
| Payment fails | Guest can retry, booking stays reserved until timeout |

## References

- [Stripe PaymentIntents](https://stripe.com/docs/payments/payment-intents)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [ADR-005: Conflict Resolution Strategy](./ADR-005-conflict-resolution.md)
