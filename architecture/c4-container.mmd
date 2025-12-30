%% C4 Container Diagram - PMS-Webapp
%% This diagram shows the containers (applications/services) within PMS-Webapp

C4Container
    title Container Diagram for PMS-Webapp

    Person(propertyOwner, "Property Owner", "Manages vacation rental properties")
    Person(guest, "Guest", "Books vacation rentals")

    System_Boundary(pmsWebapp, "PMS-Webapp") {

        Container(frontend, "Frontend Application", "Next.js 14, React", "Server-side rendered web application for property owners and guests. Includes property search, booking flow, and owner dashboard.")

        Container(api, "Backend API", "FastAPI, Python 3.11+", "REST API handling all business logic. Routes requests to appropriate engines.")

        Container(pmsCore, "PMS-Core Engine", "Python Module", "Central booking engine. Source of truth for all bookings, availability, and pricing. Manages booking lifecycle.")

        Container(directBooking, "Direct Booking Engine", "Python Module", "Handles guest-facing booking flow. Property search, availability checks, payment processing.")

        Container(channelManager, "Channel Manager", "Python Module + Celery Workers", "Bidirectional sync with external platforms. Event-driven outbound, webhook-driven inbound.")

        ContainerDb(database, "PostgreSQL Database", "Supabase PostgreSQL 15", "Stores all application data. RLS for multi-tenancy. Source of truth for bookings and properties.")

        ContainerDb(cache, "Cache & Queue", "Redis 7 (Upstash)", "Caching layer, distributed locks, message queue for async tasks, rate limiting.")

        Container(workers, "Background Workers", "Celery", "Async task processing for channel sync, email sending, reconciliation jobs.")

    }

    System_Ext(channels, "Channel Platforms", "Airbnb, Booking.com, Expedia, FeWo-direkt, Google VR")
    System_Ext(stripe, "Stripe", "Payment processing")
    System_Ext(email, "Email Service", "SendGrid/Postmark")

    %% User interactions
    Rel(propertyOwner, frontend, "Manages properties, views bookings", "HTTPS")
    Rel(guest, frontend, "Searches, books properties", "HTTPS")

    %% Frontend to Backend
    Rel(frontend, api, "API requests", "HTTPS/JSON")

    %% Backend internal routing
    Rel(api, pmsCore, "Booking operations", "Internal")
    Rel(api, directBooking, "Guest booking flow", "Internal")
    Rel(api, channelManager, "Sync operations", "Internal")

    %% Core engine dependencies
    Rel(pmsCore, database, "Reads/writes bookings, availability", "SQL/Supabase Client")
    Rel(pmsCore, cache, "Calendar locks, availability cache", "Redis Protocol")

    %% Direct booking dependencies
    Rel(directBooking, pmsCore, "Creates bookings via Core", "Internal")
    Rel(directBooking, stripe, "Payment processing", "HTTPS API")
    Rel(directBooking, cache, "Reservation locks", "Redis Protocol")

    %% Channel manager dependencies
    Rel(channelManager, pmsCore, "Validates channel bookings", "Internal")
    Rel(channelManager, cache, "Event queue, rate limiting", "Redis Protocol")
    Rel(channelManager, channels, "Outbound sync", "Platform APIs")
    Rel(channels, channelManager, "Inbound webhooks", "HTTPS Webhooks")

    %% Workers
    Rel(workers, cache, "Consumes task queue", "Redis Protocol")
    Rel(workers, channelManager, "Executes sync tasks", "Internal")
    Rel(workers, email, "Sends notifications", "HTTPS API")
    Rel(workers, database, "Updates sync status", "SQL")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="1")
