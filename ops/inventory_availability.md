# Inventory & Availability System

**Phase 20**: Unified inventory management, conflict handling, and availability queries.

## Overview

The PMS inventory system prevents double-bookings through:
- **Unified inventory tracking** (`inventory_ranges` table)
- **PostgreSQL EXCLUSION constraints** (automatic conflict detection)
- **Explicit date semantics** (exclusive end dates for back-to-back support)
- **Cancelled booking exclusion** (cancelled reservations don't occupy inventory)

---

## Date Semantics

### Exclusive End Dates

All date ranges use **half-open intervals** `[start, end)`:
- `start_date`: **Inclusive** (first day of occupancy)
- `end_date`: **Exclusive** (checkout day, NOT occupied)

**Example:**
```
Booking: check_in = 2026-02-01, check_out = 2026-02-03
Occupies: Feb 1, Feb 2 (NOT Feb 3)
```

### Back-to-Back Bookings

Consecutive bookings with `booking_a.end = booking_b.start` **do NOT overlap**:

```
Booking A: 2026-02-01 to 2026-02-03 (occupies Feb 1-2)
Booking B: 2026-02-03 to 2026-02-05 (occupies Feb 3-4)
Result: ✅ ALLOWED (no conflict)
```

### Overlap Detection

Two ranges overlap if and only if:
```
start_a < end_b AND end_a > start_b
```

**Examples:**
```
[2026-02-01, 2026-02-05) overlaps [2026-02-03, 2026-02-07) ✓ (overlaps Feb 3-4)
[2026-02-01, 2026-02-03) overlaps [2026-02-03, 2026-02-05) ✗ (back-to-back)
[2026-02-01, 2026-02-05) overlaps [2026-01-28, 2026-02-02) ✓ (overlaps Feb 1)
```

---

## API Endpoints

### Query Availability

**Request:**
```bash
GET /api/v1/availability?property_id={uuid}&from_date=2026-02-01&to_date=2026-02-28
Authorization: Bearer <token>
```

**Response (Free Slot):**
```json
{
  "property_id": "123e4567-e89b-12d3-a456-426614174000",
  "from_date": "2026-02-01",
  "to_date": "2026-02-28",
  "ranges": []
}
```

**Response (Occupied Slots):**
```json
{
  "property_id": "123e4567-e89b-12d3-a456-426614174000",
  "from_date": "2026-02-01",
  "to_date": "2026-02-28",
  "ranges": [
    {
      "kind": "booking",
      "start_date": "2026-02-05",
      "end_date": "2026-02-10",
      "state": "booked",
      "booking_id": "abc-123",
      "booking_status": "confirmed"
    },
    {
      "kind": "block",
      "start_date": "2026-02-15",
      "end_date": "2026-02-20",
      "state": "blocked",
      "block_id": "def-456",
      "reason": "Maintenance"
    }
  ]
}
```

**Fields:**
- `kind`: `"booking"` or `"block"`
- `state`: `"booked"` (booking) or `"blocked"` (block)
- `booking_id`: UUID (only for bookings)
- `block_id`: UUID (only for blocks)
- `booking_status`: Booking status (e.g., `"confirmed"`, `"pending"`)
- `reason`: Optional reason for block

---

### Create Availability Block

Block a date range to prevent bookings (e.g., maintenance, owner use).

**Request:**
```bash
POST /api/v1/availability/blocks
Authorization: Bearer <token>
Content-Type: application/json

{
  "property_id": "123e4567-e89b-12d3-a456-426614174000",
  "start_date": "2026-03-01",
  "end_date": "2026-03-05",
  "reason": "Property maintenance"
}
```

**Response (Success):**
```json
{
  "id": "block-uuid-123",
  "property_id": "123e4567-e89b-12d3-a456-426614174000",
  "start_date": "2026-03-01",
  "end_date": "2026-03-05",
  "reason": "Property maintenance",
  "created_at": "2026-01-15T10:30:00Z"
}
```

**Response (Conflict - 409):**
```json
{
  "error": "conflict",
  "message": "Property is already occupied for dates 2026-03-01 - 2026-03-05. Cannot create overlapping block.",
  "path": "/api/v1/availability/blocks",
  "conflict_type": "overlapping_dates"
}
```

---

### Delete Availability Block

Remove a block to free up inventory.

**Request:**
```bash
DELETE /api/v1/availability/blocks/{block_id}
Authorization: Bearer <token>
```

**Response (Success):**
```
HTTP/1.1 204 No Content
```

**Response (Not Found - 404):**
```json
{
  "error": "not_found",
  "message": "Availability block not found",
  "path": "/api/v1/availability/blocks/abc-123"
}
```

---

## Conflict Types

When creating bookings or blocks, conflicts return **HTTP 409** with a flat JSON structure:

```json
{
  "error": "conflict",
  "message": "<human-readable-description>",
  "path": "/api/v1/...",
  "conflict_type": "<type>"
}
```

### Conflict Type Reference

| Type | Trigger | Returned By |
|------|---------|-------------|
| `double_booking` | Booking overlaps existing booking | POST /bookings |
| `inventory_overlap` | Booking overlaps existing block | POST /bookings |
| `overlapping_dates` | Block overlaps existing block | POST /availability/blocks |
| `active_bookings` | Deleting property with active bookings | DELETE /properties/{id} |

### Examples

**Booking overlaps booking:**
```json
{
  "error": "conflict",
  "message": "Property is already booked for these dates",
  "path": "/api/v1/bookings",
  "conflict_type": "double_booking"
}
```

**Booking overlaps block:**
```json
{
  "error": "conflict",
  "message": "Property is already occupied for dates 2026-03-01 - 2026-03-05. Cannot create overlapping booking.",
  "path": "/api/v1/bookings",
  "conflict_type": "inventory_overlap"
}
```

**Block overlaps block:**
```json
{
  "error": "conflict",
  "message": "Property is already occupied for dates 2026-03-01 - 2026-03-05. Cannot create overlapping block.",
  "path": "/api/v1/availability/blocks",
  "conflict_type": "overlapping_dates"
}
```

---

## Cancelled Bookings

**Important:** Cancelled bookings **do NOT occupy inventory**.

### Behavior

1. **Availability Query**: Cancelled bookings do NOT appear in ranges
2. **Conflict Detection**: Cancelled bookings do NOT cause 409 conflicts
3. **Rebooking**: Same dates can be booked immediately after cancellation

### Example Flow

```bash
# 1. Create booking
POST /api/v1/bookings
{
  "property_id": "abc-123",
  "check_in": "2026-04-01",
  "check_out": "2026-04-05",
  ...
}
→ 201 Created

# 2. Cancel booking
POST /api/v1/bookings/{booking_id}/cancel
{
  "cancelled_by": "host",
  "cancellation_reason": "Maintenance needed"
}
→ 200 OK

# 3. Query availability (FREE)
GET /api/v1/availability?property_id=abc-123&from_date=2026-04-01&to_date=2026-04-05
→ {"ranges": []} (no occupancy)

# 4. Rebook same dates (SUCCESS)
POST /api/v1/bookings
{
  "property_id": "abc-123",
  "check_in": "2026-04-01",
  "check_out": "2026-04-05",
  ...
}
→ 201 Created
```

---

## Troubleshooting

### "Property already booked" Error

**Symptom:** POST /bookings returns 409 `double_booking` or `inventory_overlap`.

**Causes:**
1. Existing confirmed/pending/checked_in booking overlaps
2. Availability block exists for those dates
3. Date range validation failed (check_out must be after check_in)

**Solutions:**
```bash
# Check availability
curl -X GET "https://api.example.com/api/v1/availability?property_id={id}&from_date=2026-04-01&to_date=2026-04-30" \
  -H "Authorization: Bearer <token>"

# If block exists, delete it
curl -X DELETE "https://api.example.com/api/v1/availability/blocks/{block_id}" \
  -H "Authorization: Bearer <token>"
```

### "Block already exists" Error

**Symptom:** POST /availability/blocks returns 409 `overlapping_dates`.

**Causes:**
1. Another block overlaps the requested dates
2. Confirmed booking overlaps the requested dates

**Solutions:**
```bash
# Query availability to find conflicting range
curl -X GET "https://api.example.com/api/v1/availability?property_id={id}&from_date=2026-03-01&to_date=2026-03-31" \
  -H "Authorization: Bearer <token>"

# If conflicting block, delete it first
curl -X DELETE "https://api.example.com/api/v1/availability/blocks/{block_id}" \
  -H "Authorization: Bearer <token>"
```

### Cancelled Booking Still Blocks

**Symptom:** Cancelled booking prevents new bookings.

**Diagnosis:**
```bash
# Check availability (should show NO ranges if truly cancelled)
curl -X GET "https://api.example.com/api/v1/availability?property_id={id}&from_date=2026-04-01&to_date=2026-04-05" \
  -H "Authorization: Bearer <token>"

# Check booking status
curl -X GET "https://api.example.com/api/v1/bookings/{booking_id}" \
  -H "Authorization: Bearer <token>"
```

**Expected:** Availability ranges should be empty if booking is cancelled.

**If still blocked:** Check for manual availability block:
```bash
# List all blocks for property in date range
curl -X GET "https://api.example.com/api/v1/availability?property_id={id}&from_date=2026-01-01&to_date=2026-12-31" \
  -H "Authorization: Bearer <token>" | jq '.ranges[] | select(.kind == "block")'
```

---

## RBAC Permissions

### Availability Query (GET /availability)
- **Allowed:** All roles (admin, manager, staff, owner, accountant)
- **Scope:** Agency-wide

### Create Block (POST /availability/blocks)
- **Allowed:** admin, manager, owner
- **Restrictions:** Owners can only block their own properties

### Delete Block (DELETE /availability/blocks/{id})
- **Allowed:** admin, manager, owner
- **Restrictions:** Owners can only delete blocks for their own properties

---

## Database Schema

### inventory_ranges

Unified tracking of all property occupancy:

```sql
CREATE TABLE inventory_ranges (
  id UUID PRIMARY KEY,
  property_id UUID NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('booking', 'block')),
  source_id UUID NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('active', 'cancelled')),
  reason TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- EXCLUSION constraint (prevents overlaps)
ALTER TABLE inventory_ranges
  ADD CONSTRAINT inventory_ranges_no_overlap
  EXCLUDE USING gist (
    property_id WITH =,
    daterange(start_date, end_date, '[)') WITH &&
  )
  WHERE (state = 'active');
```

**Key Points:**
- `state = 'active'`: Participates in overlap detection
- `state = 'cancelled'`: Ignored by overlap constraint (freed inventory)
- `kind = 'booking'`: Links to `bookings.id`
- `kind = 'block'`: Links to `availability_blocks.id`

---

## Curl Examples

### Check if Property is Free

```bash
curl -X GET "https://api.example.com/api/v1/availability?property_id=123e4567-e89b-12d3-a456-426614174000&from_date=2026-02-01&to_date=2026-02-28" \
  -H "Authorization: Bearer eyJhbGc..."

# Expected (free): {"ranges": []}
# Expected (occupied): {"ranges": [{"kind": "booking", ...}]}
```

### Block Property for Maintenance

```bash
curl -X POST "https://api.example.com/api/v1/availability/blocks" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "123e4567-e89b-12d3-a456-426614174000",
    "start_date": "2026-03-01",
    "end_date": "2026-03-08",
    "reason": "Annual maintenance"
  }'

# Expected: {"id": "block-uuid", ...}
```

### Unblock Property

```bash
curl -X DELETE "https://api.example.com/api/v1/availability/blocks/block-uuid-123" \
  -H "Authorization: Bearer eyJhbGc..."

# Expected: HTTP 204 No Content
```

### Handle 409 Conflict

```bash
# Attempt booking (may fail with 409)
curl -X POST "https://api.example.com/api/v1/bookings" \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "123e4567-e89b-12d3-a456-426614174000",
    "check_in": "2026-04-01",
    "check_out": "2026-04-05",
    ...
  }'

# If 409 returned:
{
  "error": "conflict",
  "message": "Property is already booked for these dates",
  "path": "/api/v1/bookings",
  "conflict_type": "double_booking"
}

# Troubleshoot: Check availability
curl -X GET "https://api.example.com/api/v1/availability?property_id=123e4567-e89b-12d3-a456-426614174000&from_date=2026-04-01&to_date=2026-04-05" \
  -H "Authorization: Bearer eyJhbGc..."
```

---

## See Also

- **Phase 19**: Core Booking Flow API
- **Phase 14**: Availability/Inventory System Implementation
- **OpenAPI Docs**: `/docs` endpoint for interactive API reference
