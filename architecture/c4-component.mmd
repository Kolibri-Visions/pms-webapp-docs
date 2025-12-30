%% C4 Component Diagram - Backend API Components
%% This diagram shows the components within the Backend API container

C4Component
    title Component Diagram for PMS-Webapp Backend

    Container_Boundary(api, "Backend API") {

        %% API Layer Components
        Component(apiRouter, "API Router", "FastAPI Router", "Routes HTTP requests to appropriate handlers. Handles authentication, validation, rate limiting.")

        Component(authMiddleware, "Auth Middleware", "FastAPI Middleware", "Validates JWT tokens from Supabase Auth. Extracts user context for RLS.")

        Component(webhookHandler, "Webhook Handler", "FastAPI Endpoints", "Receives and validates webhooks from channel platforms. Verifies signatures.")

        %% PMS-Core Components
        Component_Boundary(pmsCoreEngine, "PMS-Core Engine") {
            Component(bookingService, "Booking Service", "Python Class", "Manages booking lifecycle. Creates, updates, cancels bookings. Enforces business rules.")

            Component(availabilityService, "Availability Service", "Python Class", "Manages calendar availability. Calculates open dates. Handles blocks and overrides.")

            Component(pricingEngine, "Pricing Engine", "Python Class", "Calculates booking prices. Applies seasonal rates, discounts, fees. Supports multiple currencies.")

            Component(guestService, "Guest Service", "Python Class", "Manages guest profiles. Unified view across all booking sources. Handles PII with encryption.")

            Component(financialService, "Financial Service", "Python Class", "Revenue tracking. Owner statements. Payment reconciliation. Tax calculations.")
        }

        %% Direct Booking Engine Components
        Component_Boundary(directBookingEngine, "Direct Booking Engine") {
            Component(searchService, "Search Service", "Python Class", "Property search with filters. Location, dates, guests, amenities. Uses ElasticSearch-like queries.")

            Component(checkoutService, "Checkout Service", "Python Class", "Multi-step booking flow. Guest details, special requests, payment. Session management.")

            Component(paymentService, "Payment Service", "Python Class", "Stripe integration. PaymentIntent creation. Webhook handling for payment status.")

            Component(calendarWidget, "Calendar Widget API", "Python Class", "Availability calendar data. Price preview per date. Min/max stay rules.")
        }

        %% Channel Manager Components
        Component_Boundary(channelManagerEngine, "Channel Manager") {

            Component(syncEngine, "Sync Engine", "Python Class", "Orchestrates sync operations. Fan-out to channels. Handles retries and failures.")

            Component(eventPublisher, "Event Publisher", "Python Class", "Publishes PMS-Core events to Redis Stream. Ensures delivery guarantees.")

            Component(connectionManager, "Connection Manager", "Python Class", "Manages OAuth tokens per platform. Handles refresh, encryption, validation.")

            Component(reconciliationService, "Reconciliation Service", "Python Class", "Daily full sync. Detects drift. Applies conflict resolution rules.")

            %% Platform Adapters
            Component(airbnbAdapter, "Airbnb Adapter", "Python Class", "Airbnb API integration. REST API. Handles listings, reservations, calendar.")

            Component(bookingComAdapter, "Booking.com Adapter", "Python Class", "Booking.com API integration. XML format. Room availability, reservations.")

            Component(expediaAdapter, "Expedia Adapter", "Python Class", "Expedia API integration. REST API. Property content, rates, availability.")

            Component(fewoAdapter, "FeWo-direkt Adapter", "Python Class", "FeWo-direkt (Vrbo) API integration. REST API. Listings, bookings, calendar.")

            Component(googleVRAdapter, "Google VR Adapter", "Python Class", "Google Vacation Rentals API. REST API. Listings, availability, bookings.")

            Component(rateLimiter, "Rate Limiter", "Python Class", "Per-platform rate limiting. Token bucket algorithm. Uses Redis for distributed state.")

            Component(circuitBreaker, "Circuit Breaker", "Python Class", "Fault tolerance for channel APIs. OPEN/HALF-OPEN/CLOSED states. Auto-recovery.")
        }

        %% Data Access Layer
        Component(repository, "Repository Layer", "SQLAlchemy", "Database access abstraction. Query builders. Transaction management.")

        Component(cacheManager, "Cache Manager", "Redis Client", "Read-through caching. Cache invalidation. TTL management.")

        Component(lockManager, "Lock Manager", "Redis Locks", "Distributed locks for calendar operations. Prevents double-booking.")
    }

    %% External dependencies
    ContainerDb(database, "PostgreSQL", "Supabase", "Primary data store")
    ContainerDb(redis, "Redis", "Upstash", "Cache & Queue")
    Container_Ext(stripe, "Stripe API", "Payment processing")
    Container_Ext(channels, "Channel APIs", "Airbnb, Booking.com, etc.")

    %% Request flow relationships
    Rel(apiRouter, authMiddleware, "Authenticates requests")
    Rel(apiRouter, bookingService, "Booking operations")
    Rel(apiRouter, searchService, "Property search")
    Rel(apiRouter, checkoutService, "Direct booking flow")
    Rel(webhookHandler, syncEngine, "Inbound channel events")

    %% PMS-Core internal relationships
    Rel(bookingService, availabilityService, "Checks/updates availability")
    Rel(bookingService, pricingEngine, "Calculates prices")
    Rel(bookingService, guestService, "Manages guest data")
    Rel(bookingService, financialService, "Records transactions")
    Rel(bookingService, eventPublisher, "Emits booking events")

    %% Direct Booking internal relationships
    Rel(searchService, availabilityService, "Gets available properties")
    Rel(checkoutService, bookingService, "Creates booking via Core")
    Rel(checkoutService, paymentService, "Processes payment")
    Rel(calendarWidget, availabilityService, "Gets calendar data")
    Rel(calendarWidget, pricingEngine, "Gets prices per date")

    %% Channel Manager internal relationships
    Rel(syncEngine, airbnbAdapter, "Syncs to Airbnb")
    Rel(syncEngine, bookingComAdapter, "Syncs to Booking.com")
    Rel(syncEngine, expediaAdapter, "Syncs to Expedia")
    Rel(syncEngine, fewoAdapter, "Syncs to FeWo-direkt")
    Rel(syncEngine, googleVRAdapter, "Syncs to Google VR")
    Rel(syncEngine, rateLimiter, "Rate limits requests")
    Rel(syncEngine, circuitBreaker, "Handles failures")
    Rel(syncEngine, connectionManager, "Gets OAuth tokens")
    Rel(reconciliationService, syncEngine, "Triggers reconciliation sync")

    %% Channel adapters to external
    Rel(airbnbAdapter, channels, "Airbnb API calls")
    Rel(bookingComAdapter, channels, "Booking.com API calls")
    Rel(expediaAdapter, channels, "Expedia API calls")
    Rel(fewoAdapter, channels, "FeWo-direkt API calls")
    Rel(googleVRAdapter, channels, "Google VR API calls")

    %% Data access relationships
    Rel(repository, database, "SQL queries")
    Rel(cacheManager, redis, "Cache operations")
    Rel(lockManager, redis, "Lock operations")
    Rel(eventPublisher, redis, "Publishes to Redis Stream")
    Rel(rateLimiter, redis, "Rate limit counters")
    Rel(circuitBreaker, redis, "Circuit state")

    %% Service to data layer
    Rel(bookingService, repository, "Data access")
    Rel(bookingService, lockManager, "Calendar locks")
    Rel(availabilityService, repository, "Data access")
    Rel(availabilityService, cacheManager, "Caches availability")
    Rel(guestService, repository, "Data access")
    Rel(connectionManager, repository, "Token storage")
    Rel(paymentService, stripe, "Payment API")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="2")
