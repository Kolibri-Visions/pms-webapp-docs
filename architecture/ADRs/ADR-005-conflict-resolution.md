# ADR-005: Conflict Resolution Strategy

**Status:** Accepted
**Date:** 2025-12-21
**Decision Makers:** System Architecture Team

---

## Context

With bookings coming from multiple sources (direct, 5 channel platforms), conflicts can arise:
- Two guests booking the same dates simultaneously
- Status updates from channel vs. status updates from owner
- Availability/pricing drift between PMS-Core and channels

We need a deterministic conflict resolution strategy that:
- Prevents double-bookings absolutely
- Maintains PMS-Core as the source of truth
- Handles cross-channel conflicts fairly
- Provides clear rules for all scenarios

## Decision Drivers

1. **Zero Double-Bookings**: This is the most critical invariant
2. **Source of Truth**: PMS-Core decisions are authoritative
3. **Fairness**: First-come-first-served principle
4. **Transparency**: Clear rules that can be explained to users
5. **Recoverability**: Conflicts should be detectable and resolvable

## Conflict Scenarios

### Scenario 1: Simultaneous Booking Conflict

**Description:** Guest A books Dec 20-25 via Direct while Guest B books Dec 22-27 via Airbnb at the same moment.

**Options Considered:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| First-Write-Wins | Whoever's DB transaction commits first wins | Simple, fair | Race condition possible |
| Pessimistic Locking | Lock calendar before availability check | Guaranteed prevention | Performance impact |
| Optimistic Locking | Check-and-set with version number | Good performance | Retries needed |
| Distributed Lock | Redis lock on property+dates | Reliable, scalable | Extra infrastructure |

**Decision: Distributed Lock (Redis) + Database Constraint**

Defense in depth:
1. **Redis distributed lock** acquired before availability check
2. **PostgreSQL exclusion constraint** as final safeguard

### Scenario 2: Status Update Conflict

**Description:** Owner marks booking as "cancelled" while Airbnb sends "confirmed" status.

**Decision: Source-Based Resolution**

| Booking Origin | Owner Updates | Channel Updates | Resolution |
|---------------|---------------|-----------------|------------|
| Direct | Owner wins | N/A | Core is authoritative |
| Channel (e.g., Airbnb) | Owner wins* | Channel wins | Origin channel is authoritative for its bookings |

*Owner can override channel bookings, but we sync the change back to channel.

### Scenario 3: Availability/Pricing Drift

**Description:** Availability on Booking.com differs from PMS-Core.

**Decision: Most Restrictive Availability, Core Pricing Wins**

- If Core says "available" and channel says "blocked" → Apply "blocked"
- If Core says "blocked" and channel says "available" → Apply "blocked"
- For pricing mismatches → Push Core pricing to channel

## Decision

We implement a **multi-layer conflict resolution strategy**:

### Layer 1: Prevention (Distributed Locking)

```python
async def create_booking_with_lock(booking_data: BookingCreate) -> Booking:
    """Create booking with distributed lock."""

    # Lock key includes property and approximate date range
    lock_key = f"booking:lock:{booking_data.property_id}:{booking_data.check_in.isoformat()}"

    # Acquire distributed lock with 10-minute TTL
    lock = await redis.lock(lock_key, timeout=600, blocking_timeout=5)

    if not await lock.acquire():
        raise ConflictError(
            code="CONCURRENT_BOOKING",
            message="Another booking is being processed for these dates. Please try again."
        )

    try:
        # While holding lock, verify availability
        if not await check_availability(booking_data):
            raise ConflictError(
                code="DATES_UNAVAILABLE",
                message="The selected dates are no longer available."
            )

        # Create booking
        return await db.bookings.create(booking_data)

    finally:
        await lock.release()
```

### Layer 2: Database Constraint (Final Safeguard)

```sql
-- Exclusion constraint prevents overlapping bookings
ALTER TABLE bookings
    ADD CONSTRAINT no_booking_overlap
    EXCLUDE USING gist (
        property_id WITH =,
        daterange(check_in, check_out, '[)') WITH &&
    )
    WHERE (status NOT IN ('cancelled', 'inquiry'));
```

### Layer 3: Status Conflict Resolution

```python
def resolve_status_conflict(
    booking: Booking,
    incoming_status: str,
    incoming_source: str
) -> StatusResolution:
    """
    Determine winning status in a conflict.

    Rules:
    1. Direct bookings: Core/Owner always wins
    2. Channel bookings: Origin channel wins for status changes
    3. Cross-channel: Most restrictive status wins
    """

    # Define status priority (lower = more restrictive)
    STATUS_PRIORITY = {
        'cancelled': 1,      # Most restrictive
        'checked_out': 2,
        'checked_in': 3,
        'confirmed': 4,
        'reserved': 5,
        'inquiry': 6,        # Least restrictive
    }

    # Rule 1: Direct bookings - Core is authoritative
    if booking.source == 'direct':
        return StatusResolution(
            winner='core',
            status=booking.status,
            reason="Direct bookings are managed by Core"
        )

    # Rule 2: Update from origin channel - channel wins
    if incoming_source == booking.source:
        return StatusResolution(
            winner='channel',
            status=incoming_status,
            reason=f"Booking originated from {booking.source}; channel is authoritative"
        )

    # Rule 3: Cross-channel or owner update - most restrictive wins
    current_priority = STATUS_PRIORITY.get(booking.status, 99)
    incoming_priority = STATUS_PRIORITY.get(incoming_status, 99)

    if incoming_priority < current_priority:
        return StatusResolution(
            winner='incoming',
            status=incoming_status,
            reason="More restrictive status applied"
        )
    else:
        return StatusResolution(
            winner='current',
            status=booking.status,
            reason="Current status is more restrictive or equal"
        )
```

### Layer 4: Availability Reconciliation

```python
async def reconcile_availability(property_id: str, channel: str) -> ReconciliationResult:
    """
    Reconcile availability between Core and channel.

    Rule: Apply most restrictive availability (blocked > available)
    """

    core_avail = await get_core_availability(property_id)
    channel_avail = await get_channel_availability(property_id, channel)

    changes = []

    for date in date_range(core_avail.start, core_avail.end):
        core_status = core_avail.get(date, 'available')
        channel_status = channel_avail.get(date, 'available')

        if core_status == channel_status:
            continue  # No conflict

        # Determine winner
        if core_status == 'blocked' or channel_status == 'blocked':
            winner_status = 'blocked'
            winner = 'most_restrictive'
        else:
            # Both available but different prices - Core wins
            winner_status = core_status
            winner = 'core'

        changes.append(AvailabilityChange(
            date=date,
            core_status=core_status,
            channel_status=channel_status,
            resolved_status=winner_status,
            resolution_reason=winner
        ))

        # Apply changes
        if winner_status != core_status:
            await update_core_availability(property_id, date, winner_status)
        if winner_status != channel_status:
            await update_channel_availability(property_id, channel, date, winner_status)

    # Alert if significant drift
    if len(changes) > 5:
        await alert_availability_drift(property_id, channel, changes)

    return ReconciliationResult(
        property_id=property_id,
        channel=channel,
        changes=changes
    )
```

## Consequences

### Positive

- Zero double-bookings guaranteed (lock + constraint)
- Clear, deterministic resolution rules
- Audit trail of all conflicts
- Owner maintains ultimate control

### Negative

- Lock contention during high traffic
- Slight latency for lock acquisition
- Complexity in handling edge cases

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Lock timeout during checkout | Extend lock with watchdog, 10-min generous timeout |
| Redis lock server failure | PostgreSQL constraint is fallback; alerts on Redis issues |
| Frequent availability drift | Daily reconciliation, root cause investigation |
| Guest confusion on rejection | Clear error messages, immediate notification |

## User-Facing Behavior

### For Guests

```
Scenario: Guest A and Guest B try to book overlapping dates

Timeline:
T+0s:  Guest A starts checkout for Dec 20-25
T+1s:  Guest B starts checkout for Dec 22-27
T+2s:  Guest A's lock acquired
T+3s:  Guest B's lock fails (wait)
T+4s:  Guest A completes payment
T+5s:  Guest A's booking confirmed, lock released
T+6s:  Guest B's lock acquired
T+7s:  Guest B's availability check fails

Guest B sees:
"Sorry, the dates December 22-27 are no longer available.
The property was just booked by another guest.
Would you like to search for alternative dates?"
```

### For Property Owners

```
Scenario: Booking status conflict

Dashboard notification:
"Booking #12345 Status Conflict Resolved

A status conflict occurred for booking #12345:
- Current status: Confirmed
- Airbnb sent: Cancelled

Resolution: Airbnb status applied (booking originated from Airbnb)
New status: Cancelled

Action: Refund of $500 has been initiated."
```

## Implementation Checklist

- [ ] Implement Redis distributed lock with proper TTL
- [ ] Add PostgreSQL exclusion constraint
- [ ] Create conflict resolution service
- [ ] Implement status resolution logic
- [ ] Add availability reconciliation job
- [ ] Create conflict audit logging
- [ ] Add user-facing error messages
- [ ] Write comprehensive tests for edge cases

## References

- [Redis Distributed Locks (Redlock)](https://redis.io/docs/manual/patterns/distributed-locks/)
- [PostgreSQL Exclusion Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-EXCLUSION)
- [ADR-004: Event-Driven Sync Architecture](./ADR-004-event-driven-sync.md)
