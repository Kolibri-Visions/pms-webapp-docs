%% PMS-Webapp Sync Workflow Diagrams
%% Event-driven synchronization between PMS-Core and Channel Platforms

%% ============================================================================
%% DIAGRAM 1: OUTBOUND SYNC FLOW (PMS-Core to Channels)
%% ============================================================================

---
title: Outbound Sync Flow - PMS-Core to Channel Platforms
---
sequenceDiagram
    autonumber

    participant Owner as Property Owner
    participant FE as Frontend
    participant API as Backend API
    participant Core as PMS-Core
    participant DB as PostgreSQL
    participant Redis as Redis
    participant Queue as Celery Queue
    participant Worker as Sync Worker
    participant RL as Rate Limiter
    participant CB as Circuit Breaker
    participant Airbnb as Airbnb API
    participant BookingCom as Booking.com API
    participant Expedia as Expedia API

    Note over Owner,Expedia: Scenario: Owner creates new booking manually

    Owner->>FE: Create booking
    FE->>API: POST /bookings
    API->>Core: createBooking(data)

    Core->>Redis: Acquire calendar lock
    Redis-->>Core: Lock acquired

    Core->>DB: Check availability
    DB-->>Core: Dates available

    Core->>DB: INSERT booking
    DB-->>Core: Booking created

    Core->>Redis: Release lock
    Core->>Redis: Publish booking.created event

    Redis-->>Queue: Event queued

    Core-->>API: Booking response
    API-->>FE: 201 Created
    FE-->>Owner: Booking confirmed

    Note over Queue,Expedia: Async fan-out to all connected channels

    Queue->>Worker: Consume booking.created
    Worker->>DB: Get channel connections

    par Sync to Airbnb
        Worker->>RL: Check rate limit (Airbnb)
        RL-->>Worker: OK (under limit)
        Worker->>CB: Check circuit (Airbnb)
        CB-->>Worker: CLOSED (healthy)
        Worker->>Airbnb: POST /reservations
        Airbnb-->>Worker: 200 OK
        Worker->>DB: Log sync success
    and Sync to Booking.com
        Worker->>RL: Check rate limit (Booking.com)
        RL-->>Worker: OK
        Worker->>CB: Check circuit
        CB-->>Worker: CLOSED
        Worker->>BookingCom: POST /reservations (XML)
        BookingCom-->>Worker: 200 OK
        Worker->>DB: Log sync success
    and Sync to Expedia
        Worker->>RL: Check rate limit (Expedia)
        RL-->>Worker: OK
        Worker->>CB: Check circuit
        CB-->>Worker: CLOSED
        Worker->>Expedia: POST /bookings
        Expedia-->>Worker: 200 OK
        Worker->>DB: Log sync success
    end

    Worker->>Redis: Publish sync.completed

%% ============================================================================
%% DIAGRAM 2: INBOUND SYNC FLOW (Channels to PMS-Core)
%% ============================================================================

---
title: Inbound Sync Flow - Channel Webhook to PMS-Core
---
sequenceDiagram
    autonumber

    participant Airbnb as Airbnb Platform
    participant WH as Webhook Handler
    participant Verify as Signature Verifier
    participant Adapter as Airbnb Adapter
    participant Redis as Redis
    participant Core as PMS-Core
    participant DB as PostgreSQL
    participant Queue as Celery Queue
    participant Worker as Sync Worker
    participant BookingCom as Booking.com API
    participant Notify as Notification Service

    Note over Airbnb,Notify: Scenario: Guest books via Airbnb

    Airbnb->>WH: POST /webhooks/airbnb
    WH->>Verify: Verify signature
    Verify-->>WH: Signature valid

    WH->>Adapter: Parse webhook payload
    Adapter-->>WH: Normalized booking data

    WH->>Redis: Acquire calendar lock (property, dates)

    alt Lock acquired
        Redis-->>WH: Lock OK

        WH->>Core: checkConflicts(booking)
        Core->>DB: Query overlapping bookings

        alt No conflicts
            DB-->>Core: No conflicts
            Core-->>WH: Clear to proceed

            WH->>Core: createBooking(data, source=airbnb)
            Core->>DB: INSERT booking
            DB-->>Core: Created
            Core->>Redis: Publish booking.created (source=airbnb)

            Core-->>WH: Booking created
            WH->>Redis: Release lock
            WH-->>Airbnb: 200 OK (accepted)

            Note over Queue,Notify: Sync to OTHER channels (not Airbnb)

            Queue->>Worker: Consume booking.created

            par Sync to Booking.com
                Worker->>BookingCom: Block dates
                BookingCom-->>Worker: 200 OK
            and Send notification
                Worker->>Notify: Send owner notification
                Notify-->>Worker: Email sent
            end

        else Conflict detected
            DB-->>Core: Overlapping booking exists
            Core-->>WH: Conflict!
            WH->>Redis: Release lock
            WH->>Adapter: Reject booking on Airbnb
            Adapter->>Airbnb: Cancel reservation
            WH-->>Airbnb: 200 OK (rejected)
            Worker->>Notify: Alert owner of rejected booking
        end

    else Lock failed (concurrent booking)
        Redis-->>WH: Lock FAILED
        WH-->>Airbnb: 409 Conflict (retry later)
    end

%% ============================================================================
%% DIAGRAM 3: AVAILABILITY UPDATE FLOW
%% ============================================================================

---
title: Availability Update Sync Flow
---
sequenceDiagram
    autonumber

    participant Owner as Property Owner
    participant FE as Frontend
    participant API as Backend API
    participant Core as PMS-Core
    participant DB as PostgreSQL
    participant Redis as Redis
    participant Queue as Celery Queue
    participant Worker as Sync Worker
    participant Channels as All Channels

    Note over Owner,Channels: Scenario: Owner blocks dates for maintenance

    Owner->>FE: Block dates (Dec 20-25)
    FE->>API: POST /properties/{id}/availability-blocks

    API->>Core: createBlock(property, dates, type=maintenance)
    Core->>DB: INSERT availability_block
    DB-->>Core: Block created

    Core->>Redis: Invalidate availability cache
    Core->>Redis: Publish availability.updated

    Core-->>API: Block response
    API-->>FE: 201 Created
    FE-->>Owner: Dates blocked

    Note over Queue,Channels: Sync availability to all channels

    Queue->>Worker: Consume availability.updated

    Worker->>DB: Get all channel connections

    loop For each connected channel
        Worker->>Worker: Prepare availability payload
        Worker->>Channels: PUT /availability
        Channels-->>Worker: 200 OK
        Worker->>DB: Log sync
    end

    Worker->>Redis: Publish sync.completed

%% ============================================================================
%% DIAGRAM 4: DAILY RECONCILIATION FLOW
%% ============================================================================

---
title: Daily Reconciliation Sync Flow
---
sequenceDiagram
    autonumber

    participant Scheduler as Cron Scheduler
    participant Worker as Reconciliation Worker
    participant DB as PostgreSQL
    participant Adapter as Channel Adapter
    participant Channel as Channel API
    participant Core as PMS-Core
    participant Alert as Alert Service

    Note over Scheduler,Alert: Runs daily at 3:00 AM UTC

    Scheduler->>Worker: Trigger daily reconciliation

    Worker->>DB: Get all properties with connections

    loop For each property
        loop For each channel connection
            Worker->>Adapter: Fetch all channel bookings
            Adapter->>Channel: GET /reservations?status=active
            Channel-->>Adapter: Booking list
            Adapter-->>Worker: Normalized bookings

            Worker->>DB: Get our bookings (source=channel)
            DB-->>Worker: Our booking list

            Worker->>Worker: Compare bookings

            alt Missing in Core
                Note over Worker: Channel has booking we don't
                Worker->>Core: Import missing booking
                Core->>DB: INSERT booking
                Worker->>Alert: Log drift detected
            end

            alt Missing in Channel
                Note over Worker: We have booking channel doesn't
                Worker->>Adapter: Re-sync booking to channel
                Adapter->>Channel: POST /reservations
                Worker->>Alert: Log drift detected
            end

            alt Status Mismatch
                Note over Worker: Same booking, different status
                Worker->>Core: Apply conflict resolution
                alt Channel originated booking
                    Core->>DB: Update to channel status
                else Direct booking
                    Worker->>Adapter: Update channel to our status
                end
            end

            alt Availability Mismatch
                Worker->>Adapter: Get channel availability
                Adapter->>Channel: GET /calendar
                Channel-->>Adapter: Availability data
                Adapter-->>Worker: Availability

                Worker->>DB: Get our availability

                Worker->>Worker: Compare & apply most restrictive

                alt Core needs update
                    Worker->>Core: Update availability
                end

                alt Channel needs update
                    Worker->>Adapter: Sync availability
                    Adapter->>Channel: PUT /calendar
                end
            end
        end
    end

    Worker->>DB: Log reconciliation complete
    Worker->>Alert: Send reconciliation report

%% ============================================================================
%% DIAGRAM 5: BOOKING CANCELLATION FLOW
%% ============================================================================

---
title: Booking Cancellation Sync Flow
---
sequenceDiagram
    autonumber

    participant Source as Cancellation Source
    participant API as Backend API
    participant Core as PMS-Core
    participant DB as PostgreSQL
    participant Redis as Redis
    participant Payment as Stripe
    participant Queue as Celery Queue
    participant Worker as Sync Worker
    participant Channels as All Channels
    participant Notify as Notification Service

    Note over Source,Notify: Cancellation can come from Owner, Guest, or Channel

    alt Owner/Guest cancels (via UI)
        Source->>API: POST /bookings/{id}/cancel
        API->>Core: cancelBooking(id, reason)
    else Channel cancels (via webhook)
        Source->>API: POST /webhooks/{platform}
        API->>Core: cancelBooking(id, source=channel)
    end

    Core->>DB: Get booking details
    DB-->>Core: Booking data

    Core->>DB: UPDATE booking SET status=cancelled
    DB-->>Core: Updated

    Core->>DB: Release calendar dates
    Core->>Redis: Invalidate availability cache

    alt Payment exists
        Core->>Payment: Create refund (based on policy)
        Payment-->>Core: Refund processed
        Core->>DB: Record refund transaction
    end

    Core->>Redis: Publish booking.cancelled

    Core-->>API: Cancellation complete
    API-->>Source: 200 OK

    Note over Queue,Notify: Notify channels and stakeholders

    Queue->>Worker: Consume booking.cancelled

    par Sync to channels (except source)
        loop Each connected channel
            Worker->>Channels: DELETE /reservation or unblock dates
            Channels-->>Worker: 200 OK
        end
    and Send notifications
        Worker->>Notify: Email guest (cancellation confirmation)
        Worker->>Notify: Email owner (booking cancelled)
    end

    Worker->>Redis: Publish sync.completed

%% ============================================================================
%% DIAGRAM 6: CIRCUIT BREAKER FLOW
%% ============================================================================

---
title: Circuit Breaker Pattern for Channel API Failures
---
stateDiagram-v2
    [*] --> Closed

    Closed --> Closed: Success (reset failure count)
    Closed --> Open: Failure threshold reached (5 failures in 1 min)

    Open --> HalfOpen: Timeout elapsed (30 seconds)
    Open --> Open: Requests rejected (fast fail)

    HalfOpen --> Closed: Probe request succeeds
    HalfOpen --> Open: Probe request fails

    note right of Closed
        Normal operation
        All requests pass through
        Track failure rate
    end note

    note right of Open
        Channel API down
        All requests fail fast
        Queue for retry
        Alert ops team
    end note

    note right of HalfOpen
        Testing recovery
        Allow 1 probe request
        Decide next state
    end note

%% ============================================================================
%% DIAGRAM 7: EVENT FLOW STATE MACHINE
%% ============================================================================

---
title: PMS-Core Event Types and Flow
---
flowchart TD
    subgraph CoreEvents["PMS-Core Events (Source of Truth)"]
        BC[booking.created]
        BU[booking.updated]
        BX[booking.cancelled]
        AU[availability.updated]
        PU[pricing.updated]
    end

    subgraph ChannelEvents["Channel Manager Events"]
        CBR[channel.booking_received]
        SC[sync.completed]
        SF[sync.failed]
    end

    subgraph Sources["Event Sources"]
        Direct[Direct Booking]
        Manual[Manual Entry]
        CH[Channel Webhook]
        Owner[Owner Action]
    end

    subgraph Consumers["Event Consumers"]
        CM[Channel Manager]
        NS[Notification Service]
        AN[Analytics]
        LOGS[Audit Log]
    end

    subgraph Channels["External Platforms"]
        AIR[Airbnb]
        BOO[Booking.com]
        EXP[Expedia]
        FEW[FeWo-direkt]
        GOO[Google VR]
    end

    %% Event sources
    Direct --> BC
    Manual --> BC
    CH --> CBR
    CBR --> |Validated| BC
    Owner --> BU
    Owner --> BX
    Owner --> AU
    Owner --> PU

    %% Core events to consumers
    BC --> CM
    BC --> NS
    BC --> AN
    BC --> LOGS

    BU --> CM
    BU --> NS
    BU --> LOGS

    BX --> CM
    BX --> NS
    BX --> LOGS

    AU --> CM
    AU --> LOGS

    PU --> CM
    PU --> LOGS

    %% Channel Manager to platforms
    CM --> |Outbound Sync| AIR
    CM --> |Outbound Sync| BOO
    CM --> |Outbound Sync| EXP
    CM --> |Outbound Sync| FEW
    CM --> |Outbound Sync| GOO

    %% Sync events
    CM --> SC
    CM --> SF

    SC --> LOGS
    SC --> AN
    SF --> LOGS
    SF --> |Alert| NS

%% ============================================================================
%% DIAGRAM 8: RATE LIMITING STRATEGY
%% ============================================================================

---
title: Per-Platform Rate Limiting Strategy
---
flowchart LR
    subgraph RateLimits["Rate Limits by Platform"]
        AIR["Airbnb<br/>10 req/sec"]
        BOO["Booking.com<br/>5 req/sec"]
        EXP["Expedia<br/>50 req/sec"]
        FEW["FeWo-direkt<br/>10 req/sec"]
        GOO["Google VR<br/>100 req/sec"]
    end

    subgraph Strategy["Token Bucket Implementation"]
        TB["Token Bucket<br/>(Redis)"]
        Q["Priority Queue"]
        W["Worker Pool"]
    end

    subgraph Handling["Limit Exceeded Handling"]
        WAIT["Wait for tokens"]
        BACKOFF["Exponential backoff"]
        QUEUE["Re-queue with delay"]
    end

    AIR --> TB
    BOO --> TB
    EXP --> TB
    FEW --> TB
    GOO --> TB

    TB --> |"Tokens available"| W
    TB --> |"No tokens"| WAIT

    WAIT --> |"Timeout"| BACKOFF
    BACKOFF --> QUEUE
    QUEUE --> Q
    Q --> TB

    W --> |"Success"| DONE["Complete"]
    W --> |"Rate limit error"| BACKOFF

%% ============================================================================
%% DIAGRAM 9: IDEMPOTENCY MECHANISM
%% ============================================================================

---
title: Idempotent Event Processing
---
sequenceDiagram
    autonumber

    participant Queue as Event Queue
    participant Worker as Sync Worker
    participant Redis as Redis (Dedup)
    participant DB as PostgreSQL
    participant Channel as Channel API

    Note over Queue,Channel: Ensuring exactly-once processing

    Queue->>Worker: Consume event (id: evt-123)

    Worker->>Redis: EXISTS event:processed:evt-123
    Redis-->>Worker: 0 (not found)

    Worker->>DB: BEGIN transaction

    Worker->>Channel: Sync data
    Channel-->>Worker: 200 OK

    Worker->>DB: Update sync status
    Worker->>DB: INSERT sync_log
    Worker->>DB: COMMIT

    Worker->>Redis: SETEX event:processed:evt-123 86400 "1"

    Note over Worker,Redis: Same event delivered again (retry/duplicate)

    Queue->>Worker: Consume event (id: evt-123)
    Worker->>Redis: EXISTS event:processed:evt-123
    Redis-->>Worker: 1 (found)

    Worker->>Worker: Skip processing (idempotent)
    Worker-->>Queue: ACK (already processed)
