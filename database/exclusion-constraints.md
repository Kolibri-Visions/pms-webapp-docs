# EXCLUSION Constraints for Concurrency Protection

**Purpose**: Document PostgreSQL EXCLUSION constraints for double-booking prevention

**Audience**: Backend developers, database engineers

**Source of Truth**: `supabase/migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql`

---

## Problem Statement

**Double-Booking**: Two bookings for the same property with overlapping dates

**Why Application-Level Checks Are Insufficient**:
- **Race conditions**: Two requests check availability simultaneously, both see "available", both create bookings
- **Time-of-check vs time-of-use**: Availability changes between check and booking creation
- **No atomic guarantee**: Application logic cannot guarantee atomicity across concurrent requests

**Solution**: Database-level enforcement via PostgreSQL EXCLUSION constraints

---

## EXCLUSION Constraint Overview

**What It Does**: Prevents overlapping ranges for the same property at the database level

**Technology**:
- **PostgreSQL EXCLUSION constraint**: Native database feature (PostgreSQL 9.0+)
- **GiST index**: Generalized Search Tree (supports range queries)
- **Range types**: `daterange(start_date, end_date, '[)')` (half-open interval)

**Table**: `inventory_ranges`

**Constraint Name**: `inventory_ranges_no_overlap`

---

## Constraint Definition

**Migration**: `supabase/migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql`

**SQL**:
```sql
ALTER TABLE inventory_ranges
ADD CONSTRAINT inventory_ranges_no_overlap
EXCLUDE USING gist (
  property_id WITH =,
  daterange(start_date, end_date, '[)') WITH &&
)
WHERE (state = 'active');
```

### Breakdown

1. **`EXCLUDE USING gist`**: Use GiST index for exclusion (supports range operators)

2. **`property_id WITH =`**: Same property (exact match)
   - Operator: `=` (equality)
   - Meaning: Check same property_id

3. **`daterange(start_date, end_date, '[)') WITH &&`**: Overlapping date ranges
   - Operator: `&&` (overlap)
   - `'[)'`: Half-open interval (includes start_date, excludes end_date)
   - Meaning: Check if date ranges overlap

4. **`WHERE (state = 'active')`**: Only active inventory ranges
   - Deleted/cancelled bookings (state != 'active') are excluded from overlap check

### Example

**Scenario**: Property ID `123`, date range `2025-01-10` to `2025-01-15`

**Constraint Prevents**:
- ❌ Booking `2025-01-12` to `2025-01-14` (fully contained)
- ❌ Booking `2025-01-09` to `2025-01-11` (start overlap)
- ❌ Booking `2025-01-14` to `2025-01-16` (end overlap)
- ❌ Booking `2025-01-09` to `2025-01-16` (fully contains)

**Constraint Allows**:
- ✅ Booking `2025-01-15` to `2025-01-20` (no overlap, `[)` excludes end_date)
- ✅ Booking `2025-01-05` to `2025-01-10` (no overlap, `[)` excludes end_date)
- ✅ Booking on different property (property_id != 123)

---

## How It Works

### Insertion Flow

1. **Application**: Attempts to insert new booking into `inventory_ranges`
   ```sql
   INSERT INTO inventory_ranges (property_id, start_date, end_date, state)
   VALUES ('123', '2025-01-12', '2025-01-14', 'active');
   ```

2. **Database**: Checks EXCLUSION constraint
   - Looks for existing active ranges for property `123`
   - Checks if `daterange('2025-01-12', '2025-01-14', '[)')` overlaps with any existing range

3. **Outcome**:
   - **No overlap**: Insert succeeds
   - **Overlap detected**: Insert fails with error:
     ```
     ERROR:  conflicting key value violates exclusion constraint "inventory_ranges_no_overlap"
     DETAIL:  Key (property_id, daterange(start_date, end_date, '[)'))=(123, [2025-01-12,2025-01-14))
     conflicts with existing key (property_id, daterange(start_date, end_date, '[)'))=(123, [2025-01-10,2025-01-15)).
     ```

---

## Application Integration

### Catch Constraint Violation

**Backend** (`backend/app/services/booking_service.py` or similar):
```python
from app.core.exceptions import BookingConflictError

async def create_booking(...):
    try:
        # Insert booking into inventory_ranges
        await db.execute(
            "INSERT INTO inventory_ranges (property_id, start_date, end_date, state) VALUES ($1, $2, $3, $4)",
            property_id, start_date, end_date, 'active'
        )
    except asyncpg.exceptions.ExclusionViolationError as e:
        # EXCLUSION constraint violated (overlap detected)
        raise BookingConflictError(
            f"Booking conflict: Property {property_id} is already booked for {start_date} to {end_date}"
        )
```

### Return 409 Conflict to Client

**API Response** (when `BookingConflictError` raised):
```json
{
  "error": {
    "code": "BOOKING_CONFLICT",
    "message": "Property is already booked for the selected dates"
  }
}
```

**HTTP Status**: `409 Conflict`

**Related Docs**: [Error Taxonomy](../architecture/error-taxonomy.md)

---

## Benefits

### 1. Database-Level Enforcement

**Atomicity**: Constraint check and insert are atomic (no race conditions)

**No Application Logic Bugs**: Even if application logic has bugs, database prevents double-booking

---

### 2. Performance

**GiST Index**: Efficient range queries (O(log n) lookup)

**No Application-Level Locks**: No need for pessimistic locking (SELECT FOR UPDATE)

---

### 3. Data Integrity

**Guaranteed Consistency**: Database enforces invariant (no overlapping active bookings)

**Audit Trail**: Constraint violations logged (can track attempted double-bookings)

---

## Limitations

### 1. Only PostgreSQL

**Not Portable**: EXCLUSION constraints are PostgreSQL-specific (not MySQL, SQLite, etc.)

**Mitigation**: Use PostgreSQL in production (Supabase uses PostgreSQL)

---

### 2. GiST Index Overhead

**Index Size**: GiST indexes larger than B-tree indexes

**Insert Performance**: Slightly slower inserts due to index maintenance

**Mitigation**: Acceptable trade-off for data integrity

---

### 3. Deleted/Cancelled Bookings

**Soft Deletes**: If using soft deletes (state = 'deleted'), constraint only checks `state = 'active'`

**Hard Deletes**: If using hard deletes (DELETE FROM), constraint no longer applies (row removed)

**Mitigation**: Use `state` column to distinguish active vs inactive bookings

---

## Testing

### Unit Tests (Recommended)

**Test Cases**:
1. ✅ Insert non-overlapping bookings (should succeed)
2. ❌ Insert overlapping booking (should fail with `ExclusionViolationError`)
3. ✅ Insert booking on different property (should succeed)
4. ✅ Insert booking with `state = 'cancelled'` that overlaps active booking (should succeed, excluded from constraint)

**Example** (pytest):
```python
import pytest
import asyncpg

async def test_exclusion_constraint_prevents_overlap():
    # Insert first booking
    await db.execute(
        "INSERT INTO inventory_ranges (property_id, start_date, end_date, state) VALUES ($1, $2, $3, $4)",
        '123', '2025-01-10', '2025-01-15', 'active'
    )

    # Attempt overlapping booking (should fail)
    with pytest.raises(asyncpg.exceptions.ExclusionViolationError):
        await db.execute(
            "INSERT INTO inventory_ranges (property_id, start_date, end_date, state) VALUES ($1, $2, $3, $4)",
            '123', '2025-01-12', '2025-01-14', 'active'
        )
```

---

## Related Documentation

- [Migrations Guide](migrations-guide.md) - How to create/apply migrations
- [Data Integrity](data-integrity.md) - Other constraints, validation rules
- [Error Taxonomy](../architecture/error-taxonomy.md) - `BookingConflictError` exception

**Migration File**: `supabase/migrations/20251229200517_enforce_overlap_prevention_via_exclusion.sql`

---

## Further Reading

**PostgreSQL Documentation**:
- [EXCLUSION Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-EXCLUSION)
- [GiST Indexes](https://www.postgresql.org/docs/current/gist.html)
- [Range Types](https://www.postgresql.org/docs/current/rangetypes.html)

---

**Last Updated**: 2025-12-30
**Maintained By**: Backend Team
