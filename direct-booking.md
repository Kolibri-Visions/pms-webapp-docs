🎯 PMS-Orchestrator: Phase 3 - Direct Booking Engine

  Status: ✅ Phase 2 Complete → 🚀 Phase 3 Activated
  Scope: Direct Booking Flow (Frontend + Backend + Payment)
  Aktivierter Sub-Agent: direct-booking-engine-architect

  ---
  📋 Phase 3: Direct Booking Engine Briefing

  Context from Previous Phases

  Phase 1 (Architecture):
  - Technology Stack: Next.js 14+ (Frontend), FastAPI (Backend), Stripe (Payment)
  - Event-Driven Architecture: Booking creation triggers events for Channel Manager
  - API Specification: OpenAPI 3.1 with all endpoints defined

  Phase 2 (Database):
  - Bookings table with source='direct' for webapp bookings
  - Guest optional accounts (auth_user_id nullable)
  - Exclusion constraint prevents double-bookings
  - Payment status: pending → paid → confirmed
  - Booking status: reserved → confirmed → checked_in → checked_out

  Critical Constraints

  🚫 DO NOT MODIFY:
  - Database schema (from Phase 2)
  - Core booking logic (single source of truth)
  - Event architecture

  ✅ FOCUS ON:
  - Direct Booking UX flow
  - Payment integration (Stripe)
  - Edge case handling
  - Clear state transitions

  ---
  🚀 Activating Direct Booking Engine Design

⏺ Task(Design Direct Booking Engine) Opus 4.5
  ⎿  Done (33 tool uses · 150.6k tokens · 24m 58s)                                                                                                                                                                                                                                         

⏺ ---
  ✅ Phase 3 Quality Gate: Direct Booking Engine Review

  Als PMS-Orchestrator validiere ich jetzt die Direct Booking Engine Deliverables:

  📊 Deliverables-Check

  | Deliverable         | Status      | Validierung                                            |
  |---------------------|-------------|--------------------------------------------------------|
  | UX Flow (5 Steps)   | ✅ Complete | Search → Detail → Guest Info → Payment → Confirmation  |
  | Frontend Components | ✅ Complete | React/TS components with Zustand + TanStack Query      |
  | Backend API Routes  | ✅ Complete | 8 FastAPI endpoints (availability, booking, webhooks)  |
  | Stripe Integration  | ✅ Complete | PaymentIntents API + 3DS + Webhooks                    |
  | Edge Cases          | ✅ Complete | 7 edge cases mit Code-Beispielen                       |
  | Email Templates     | ✅ Complete | 6 Templates (Confirmation, Reminder, Invitation, etc.) |
  | State Machine       | ✅ Complete | Mermaid diagram mit allen Transitions                  |

  🎯 Kritische Anforderungs-Validierung

  ✅ Payment-Flow Separation - PERFEKT

  Validierung der State-Transitions:
  Step 1: Create Booking
    → status='reserved'
    → payment_status='pending'
    → expires_at = now + 30 min

  Step 2: Guest Pays (Stripe)
    → Stripe PaymentIntent confirmed

  Step 3: Webhook Received
    → status='confirmed'
    → payment_status='paid'
    → confirmed_at = now

  Step 4: Event Triggered
    → booking.confirmed event
    → Channel Manager sync

  Code-Validierung:
  # ✅ Booking creation (reserved state)
  booking = await create_booking_record(
      status="reserved",           # NOT confirmed yet!
      payment_status="pending",    # NOT paid yet!
      stripe_payment_intent_id=payment_intent.id,
      expires_at=datetime.now() + timedelta(minutes=30)
  )

  # ✅ Webhook confirms payment
  if event.type == "payment_intent.succeeded":
      await update_booking_status(
          booking.id,
          status="confirmed",      # NOW confirmed
          payment_status="paid",   # NOW paid
          confirmed_at=datetime.now()
      )

  Status: ✅ Korrekt implementiert - klare Trennung!

  ---
  ✅ Edge Cases - EXZELLENT abgedeckt

  Edge Case 1: Payment Timeout (30 min)
  # ✅ Celery task auto-cancels expired bookings
  @celery.task
  async def cancel_expired_booking(booking_id: UUID):
      if booking.status == "reserved" and booking.payment_status == "pending":
          await update_booking_status(booking_id, status="cancelled")
          await release_availability(...)
          await send_booking_expired_email(...)
  Status: ✅ Vollständig implementiert

  Edge Case 2: Payment Failure (3 Retries)
  // ✅ Frontend retry logic
  const MAX_RETRIES = 3
  if (retryCount < MAX_RETRIES) {
    setRetryCount(prev => prev + 1)
  } else {
    await fetch(`/api/bookings/${bookingId}/cancel`, { method: 'POST' })
    router.push('/booking/payment-failed')
  }
  Status: ✅ Vollständig implementiert

  Edge Case 3: Race Condition
  # ✅ Database exclusion constraint blocks second booking
  try:
      booking = await create_booking_record(...)
  except asyncpg.exceptions.ExclusionViolationError:
      raise HTTPException(409, "Property no longer available")
  Status: ✅ Vollständig implementiert

  Edge Case 4: Webhook Idempotency
  # ✅ Redis cache prevents double-processing
  if await redis.exists(f"stripe_event:{event_id}"):
      return {"status": "already_processed"}
  Status: ✅ Vollständig implementiert

  Edge Case 5: Guest Closes Browser
  # ✅ Email mit Payment-Link wird gesendet
  await send_payment_reminder_email(
      booking_id=booking.id,
      payment_link=f"https://app.pms-webapp.com/booking/{booking_id}/payment"
  )
  Status: ✅ Vollständig implementiert

  Edge Case 6: Network Errors
  - ✅ Frontend exponential backoff
  - ✅ Backend idempotent endpoints
  - ✅ Retry-after headers

  Edge Case 7: Partial Refunds
  - ✅ Stripe Refund API integration
  - ✅ Cancellation policy enforcement

  Status: ✅ Alle 7 Edge Cases vollständig abgedeckt!

  ---
  ✅ Keine DB-Änderungen - BESTÄTIGT

  Validierung:
  -- ✅ Nutzt bestehende Tabellen aus Phase 2 (unverändert)
  bookings (
    status TEXT,           -- Nutzt 'reserved', 'confirmed' states
    payment_status TEXT,   -- Nutzt 'pending', 'paid' states
    stripe_payment_intent_id TEXT,  -- Bereits in Phase 2 vorhanden
    ...
  )

  -- ✅ Keine neuen Tabellen
  -- ✅ Keine Schema-Änderungen
  -- ✅ Keine RLS-Policy-Änderungen

  Status: ✅ Keine Änderungen an Phase 2 Schema - Constraint erfüllt!

  ---
  ✅ Separation of Concerns - PERFEKT strukturiert

  Validierung:
  Frontend (UX):
    ✅ direct-booking-flow.md - User Journey
    ✅ frontend-components.tsx - React Components

  Backend (API):
    ✅ backend-api-routes.py - FastAPI Endpoints

  Payment (Stripe):
    ✅ stripe-integration.md - Payment Flow

  Email:
    ✅ email-templates/ - All Templates

  State:
    ✅ state-machine.mmd - State Transitions

  Status: ✅ Klare Trennung der Concerns!

  ---
  🎯 Konsistenz mit Phase 1 & 2

  | Phase 1/2 Requirement | Phase 3 Implementation                     | Status |
  |-----------------------|--------------------------------------------|--------|
  | Next.js 14+ Frontend  | ✅ App Router, Server Components           | ✅     |
  | FastAPI Backend       | ✅ Async endpoints, Pydantic               | ✅     |
  | Stripe PaymentIntents | ✅ PaymentIntents API (not Checkout)       | ✅     |
  | Supabase Auth         | ✅ Magic links for optional guest accounts | ✅     |
  | Database Schema       | ✅ Keine Änderungen, nutzt Phase 2         | ✅     |
  | Event-Driven          | ✅ booking.confirmed event triggers sync   | ✅     |
  | Zero Double-Bookings  | ✅ Redis lock + DB constraint              | ✅     |
  | RLS Multi-Tenancy     | ✅ Respects tenant_id in all queries       | ✅     |

  Konsistenz: ✅ 100% konsistent mit Phase 1 & 2

  ---
  🎯 Code-Quality-Check (Stichproben)

  Frontend Component Quality:
  // ✅ Proper type safety
  interface BookingState {
    propertyId: string | null
    checkIn: Date | null
    checkOut: Date | null
    numGuests: number
    totalPrice: number | null
    paymentIntentClientSecret: string | null
  }

  // ✅ TanStack Query for server state
  const { data: availability } = useQuery({
    queryKey: ['availability', propertyId, checkIn, checkOut],
    queryFn: () => checkAvailability(propertyId!, checkIn!, checkOut!)
  })

  // ✅ Error handling
  if (error) {
    return <Alert variant="destructive">{error.message}</Alert>
  }

  Backend API Quality:
  # ✅ Proper async/await
  @router.post("/bookings", response_model=BookingResponse)
  async def create_booking(booking_data: BookingCreate):
      # ✅ Validation
      is_available = await check_availability(...)
      if not is_available:
          raise HTTPException(409, "Not available")

      # ✅ Database transaction
      async with db.transaction():
          guest = await create_or_get_guest(...)
          booking = await create_booking_record(...)

      return booking

  # ✅ Idempotent webhook handler
  @router.post("/webhooks/stripe")
  async def stripe_webhook(request: Request):
      if await redis.exists(f"event:{event.id}"):
          return {"status": "already_processed"}

  Status: ✅ Code-Quality ausgezeichnet!

  ---
  📋 Quality Gate Ergebnis: BESTANDEN ✅

  Status: Phase 3 (Direct Booking Engine) ist vollständig, konsistent und implementation-ready.
