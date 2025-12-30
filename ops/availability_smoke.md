# Availability & Inventory System - Smoke Test Guide

This guide provides copy/paste SQL and curl commands to test the Phase 14 Availability/Inventory system.

> **Note:** For **Phase 20** automated smoke testing (recommended for production), see:
> - **[Run Phase 20 Smoke via SSH](runbook.md#run-phase-20-smoke-via-ssh-recommended)** - SSH-based automated test (recommended)
> - **[Phase 20 Smoke Test – Coolify Terminal](runbook.md#phase-20-smoke-test--ausführen-in-coolify)** - Coolify terminal method
>
> This guide covers **manual testing** with curl/SQL for development and debugging.

---

## Prerequisites

- Supabase/Postgres database running
- Backend API running on `http://localhost:8000`
- Valid JWT token for testing (replace `$TOKEN` in curl examples)

## 1. Setup Test Data

### Create Test Property (if needed)

```sql
-- Insert test agency
INSERT INTO public.agencies (id, name, created_at, updated_at)
VALUES (
  '11111111-1111-1111-1111-111111111111',
  'Test Agency',
  now(),
  now()
)
ON CONFLICT (id) DO NOTHING;

-- Insert test property
INSERT INTO public.properties (
  id,
  agency_id,
  name,
  address_line1,
  city,
  country,
  created_at,
  updated_at
)
VALUES (
  '22222222-2222-2222-2222-222222222222',
  '11111111-1111-1111-1111-111111111111',
  'Test Villa',
  '123 Test Street',
  'Test City',
  'Germany',
  now(),
  now()
)
ON CONFLICT (id) DO NOTHING;
```

### Verify Tables Exist

```sql
-- Check availability_blocks table
SELECT COUNT(*) FROM public.availability_blocks;

-- Check inventory_ranges table
SELECT COUNT(*) FROM public.inventory_ranges;

-- Check exclusion constraint exists
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.inventory_ranges'::regclass
  AND contype = 'x';
```

## 2. Test Availability Blocks

### Create an Availability Block (Owner Maintenance)

```bash
curl -X POST http://localhost:8000/api/v1/availability/blocks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "22222222-2222-2222-2222-222222222222",
    "start_date": "2026-01-15",
    "end_date": "2026-01-20",
    "reason": "Property maintenance - roof repair"
  }'
```

Expected: `201 Created` with block details

### Try Creating Overlapping Block (Should Fail with 409)

```bash
curl -X POST http://localhost:8000/api/v1/availability/blocks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "22222222-2222-2222-2222-222222222222",
    "start_date": "2026-01-17",
    "end_date": "2026-01-22",
    "reason": "Personal use"
  }'
```

Expected: `409 Conflict` with message about overlapping dates

### Query Availability for Property

```bash
curl -X GET "http://localhost:8000/api/v1/availability?property_id=22222222-2222-2222-2222-222222222222&from_date=2026-01-01&to_date=2026-01-31" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: `200 OK` with list of ranges (including the block created above)

### Delete Availability Block

```bash
# Use the block_id from the create response
curl -X DELETE http://localhost:8000/api/v1/availability/blocks/{block_id} \
  -H "Authorization: Bearer $TOKEN"
```

Expected: `204 No Content`

## 3. Test Booking Integration

### Create Booking on Available Dates

```bash
curl -X POST http://localhost:8000/api/v1/bookings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "22222222-2222-2222-2222-222222222222",
    "check_in": "2026-02-01",
    "check_out": "2026-02-05",
    "num_adults": 2,
    "source": "direct",
    "currency": "EUR"
  }'
```

Expected: `201 Created` with booking details + inventory_range created automatically

### Try Creating Block on Booked Dates (Should Fail with 409)

```bash
curl -X POST http://localhost:8000/api/v1/availability/blocks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "22222222-2222-2222-2222-222222222222",
    "start_date": "2026-02-03",
    "end_date": "2026-02-07",
    "reason": "Maintenance"
  }'
```

Expected: `409 Conflict` (booking already exists on those dates)

### Try Creating Overlapping Booking (Should Fail with 409)

```bash
curl -X POST http://localhost:8000/api/v1/bookings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "22222222-2222-2222-2222-222222222222",
    "check_in": "2026-02-03",
    "check_out": "2026-02-08",
    "num_adults": 2,
    "source": "direct",
    "currency": "EUR"
  }'
```

Expected: `409 Conflict` (overlaps with existing booking)

### Cancel Booking and Verify Inventory Freed

```bash
# 1. Cancel the booking (PATCH status to cancelled)
curl -X PATCH http://localhost:8000/api/v1/bookings/{booking_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "cancelled",
    "cancellation_reason": "Guest cancelled",
    "cancelled_by": "guest"
  }'

# 2. Now create a block on same dates (should succeed)
curl -X POST http://localhost:8000/api/v1/availability/blocks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "22222222-2222-2222-2222-222222222222",
    "start_date": "2026-02-01",
    "end_date": "2026-02-05",
    "reason": "Now available for blocking"
  }'
```

Expected: First request `200 OK`, second request `201 Created`

## 4. SQL Queries for Debugging

### View All Availability Blocks

```sql
SELECT
  id,
  property_id,
  start_date,
  end_date,
  reason,
  created_at
FROM public.availability_blocks
ORDER BY start_date;
```

### View All Inventory Ranges

```sql
SELECT
  id,
  property_id,
  kind,
  source_id,
  start_date,
  end_date,
  state,
  reason,
  created_at
FROM public.inventory_ranges
ORDER BY property_id, start_date;
```

### View Active Inventory (What's Blocking)

```sql
SELECT
  property_id,
  kind,
  start_date,
  end_date,
  state,
  reason
FROM public.inventory_ranges
WHERE state = 'active'
ORDER BY property_id, start_date;
```

### Check for Overlaps (Manual Verification)

```sql
-- This should return 0 rows if exclusion constraint is working
SELECT
  a.id AS range1_id,
  b.id AS range2_id,
  a.property_id,
  a.start_date AS a_start,
  a.end_date AS a_end,
  b.start_date AS b_start,
  b.end_date AS b_end
FROM public.inventory_ranges a
JOIN public.inventory_ranges b
  ON a.property_id = b.property_id
  AND a.id < b.id
  AND a.state = 'active'
  AND b.state = 'active'
  AND daterange(a.start_date, a.end_date, '[)') && daterange(b.start_date, b.end_date, '[)');
```

### View Inventory with Booking/Block Details

```sql
SELECT
  ir.id,
  ir.property_id,
  p.name AS property_name,
  ir.kind,
  ir.start_date,
  ir.end_date,
  ir.state,
  ir.reason,
  CASE
    WHEN ir.kind = 'booking' THEN b.booking_reference
    ELSE NULL
  END AS booking_ref,
  CASE
    WHEN ir.kind = 'booking' THEN b.status
    ELSE NULL
  END AS booking_status
FROM public.inventory_ranges ir
LEFT JOIN public.properties p ON p.id = ir.property_id
LEFT JOIN public.bookings b ON ir.kind = 'booking' AND ir.source_id = b.id
WHERE ir.state = 'active'
ORDER BY ir.property_id, ir.start_date;
```

## 5. Edge Cases to Test

### Adjacent Dates (Should NOT Conflict)

Ranges use `[start, end)` (end-exclusive), so these should both succeed:

```sql
-- Block 1: 2026-03-01 to 2026-03-10
INSERT INTO public.availability_blocks (property_id, start_date, end_date, reason)
VALUES ('22222222-2222-2222-2222-222222222222', '2026-03-01', '2026-03-10', 'Test 1');

INSERT INTO public.inventory_ranges (property_id, kind, source_id, start_date, end_date, state)
SELECT property_id, 'block', id, start_date, end_date, 'active'
FROM public.availability_blocks
WHERE start_date = '2026-03-01';

-- Block 2: 2026-03-10 to 2026-03-15 (starts exactly when Block 1 ends)
INSERT INTO public.availability_blocks (property_id, start_date, end_date, reason)
VALUES ('22222222-2222-2222-2222-222222222222', '2026-03-10', '2026-03-15', 'Test 2');

INSERT INTO public.inventory_ranges (property_id, kind, source_id, start_date, end_date, state)
SELECT property_id, 'block', id, start_date, end_date, 'active'
FROM public.availability_blocks
WHERE start_date = '2026-03-10';
```

### Different Properties (Should NOT Conflict)

```sql
-- Same dates, different properties - both should succeed
-- Property 1
INSERT INTO public.availability_blocks (property_id, start_date, end_date, reason)
VALUES ('22222222-2222-2222-2222-222222222222', '2026-04-01', '2026-04-10', 'Property 1');

-- Property 2 (assuming it exists)
INSERT INTO public.availability_blocks (property_id, start_date, end_date, reason)
VALUES ('33333333-3333-3333-3333-333333333333', '2026-04-01', '2026-04-10', 'Property 2');
```

## 6. Cleanup Test Data

```sql
-- Delete test inventory ranges
DELETE FROM public.inventory_ranges
WHERE property_id = '22222222-2222-2222-2222-222222222222';

-- Delete test blocks
DELETE FROM public.availability_blocks
WHERE property_id = '22222222-2222-2222-2222-222222222222';

-- Delete test bookings (if any)
DELETE FROM public.bookings
WHERE property_id = '22222222-2222-2222-2222-222222222222';
```

## 7. Expected HTTP Response Formats

### Success: Create Block (201)

```json
{
  "id": "uuid",
  "property_id": "uuid",
  "start_date": "2026-01-15",
  "end_date": "2026-01-20",
  "reason": "Property maintenance - roof repair",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### Conflict: Overlapping Dates (409)

```json
{
  "detail": {
    "error": "conflict",
    "message": "Dates conflict with existing booking/block for this property.",
    "conflict": {
      "property_id": "uuid",
      "start_date": "2026-01-17",
      "end_date": "2026-01-22"
    }
  }
}
```

### Success: Query Availability (200)

```json
{
  "property_id": "uuid",
  "from_date": "2026-01-01",
  "to_date": "2026-01-31",
  "ranges": [
    {
      "kind": "block",
      "start_date": "2026-01-15",
      "end_date": "2026-01-20",
      "state": "active",
      "reason": "Property maintenance",
      "block_id": "uuid"
    },
    {
      "kind": "booking",
      "start_date": "2026-01-25",
      "end_date": "2026-01-28",
      "state": "active",
      "booking_id": "uuid"
    }
  ]
}
```

## 8. Troubleshooting

### Error: "extension btree_gist does not exist"

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

### Error: "relation inventory_ranges does not exist"

Run the migration:
```bash
cd supabase
supabase db reset  # or apply specific migration
```

### 409 Conflicts Not Working

Check exclusion constraint:
```sql
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'public.inventory_ranges'::regclass
  AND contype = 'x';
```

Should return constraint like:
```
EXCLUDE USING gist (property_id WITH =, daterange(start_date, end_date, '[)'::text) WITH &&) WHERE (state = 'active'::text)
```

### Cancelled Bookings Still Blocking

Check inventory_ranges state:
```sql
SELECT * FROM public.inventory_ranges
WHERE source_id = 'booking_id_here';
```

State should be 'cancelled', not 'active'.
