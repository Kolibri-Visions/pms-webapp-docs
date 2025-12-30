# PMS-Core Database Index Strategy

## Overview

This document outlines the indexing strategy for the PMS-Core database, designed to optimize query performance while minimizing storage overhead and write latency.

## Index Design Principles

### 1. Query Pattern Analysis
Indexes are created based on actual query patterns, not speculative needs:
- High-frequency queries (e.g., availability checks) get priority
- Dashboard and reporting queries are optimized
- Channel sync operations are indexed for speed

### 2. Composite Index Strategy
- Most selective column first (except for range queries)
- Include columns needed for covering indexes where beneficial
- Avoid over-indexing (each index adds write overhead)

### 3. Partial Indexes
Used extensively to reduce index size and improve performance:
- Active records only (e.g., `WHERE deleted_at IS NULL`)
- Status-based (e.g., `WHERE status = 'active'`)
- Filtered by common query conditions

---

## Index Categories

### A. Primary Access Patterns

#### Tenant Isolation
Every query in the system filters by `tenant_id`. These indexes are critical:

```sql
-- All tenant-scoped tables have this pattern
CREATE INDEX idx_{table}_tenant ON {table}(tenant_id);
```

**Affected Tables:** properties, guests, bookings, invoices, messages, etc.

#### User Authentication
```sql
-- Fast user role lookup
CREATE INDEX idx_user_tenant_roles_user ON user_tenant_roles(user_id);
CREATE INDEX idx_user_tenant_roles_active ON user_tenant_roles(user_id, tenant_id)
    WHERE is_active = true;
```

### B. Booking System Indexes

The booking system is the most query-intensive part of the application.

#### Availability Checking (Most Critical)
```sql
-- Primary availability check: Is property available for dates?
CREATE INDEX idx_bookings_active ON bookings(property_id, check_in, check_out)
    WHERE status NOT IN ('cancelled', 'declined', 'no_show');

-- Calendar day-by-day availability
CREATE INDEX idx_calendar_available ON calendar_availability(property_id, date)
    WHERE available = true;

-- Full calendar lookup with pricing
CREATE INDEX idx_calendar_full ON calendar_availability(property_id, date, available, price, min_stay);
```

**Query Example:**
```sql
-- Check availability for date range
SELECT * FROM bookings
WHERE property_id = $1
  AND check_in < $2  -- desired check_out
  AND check_out > $3 -- desired check_in
  AND status NOT IN ('cancelled', 'declined', 'no_show');
```

#### Booking Lifecycle
```sql
-- Upcoming check-ins (dashboard)
CREATE INDEX idx_bookings_upcoming ON bookings(tenant_id, check_in)
    WHERE status IN ('confirmed', 'pending') AND check_in >= CURRENT_DATE;

-- Today's operations
CREATE INDEX idx_bookings_checkin_today ON bookings(property_id, check_in)
    WHERE status = 'confirmed';

CREATE INDEX idx_bookings_checkout_today ON bookings(property_id, check_out)
    WHERE status IN ('confirmed', 'checked_in');
```

#### Channel Booking Lookup
```sql
-- Prevent duplicate imports from channels
CREATE INDEX idx_bookings_channel ON bookings(source, channel_booking_id)
    WHERE channel_booking_id IS NOT NULL;
```

### C. Search & Discovery Indexes

#### Property Search
```sql
-- Full-text search on name/description
CREATE INDEX idx_properties_search ON properties USING GIN(
    to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, ''))
);

-- Geospatial search (PostGIS)
CREATE INDEX idx_properties_location ON properties USING GIST(location);

-- Capacity and price filtering
CREATE INDEX idx_properties_capacity ON properties(tenant_id, max_guests, bedrooms);
CREATE INDEX idx_properties_price ON properties(tenant_id, base_price);
```

**Query Example:**
```sql
-- Search properties near location
SELECT * FROM properties
WHERE ST_DWithin(location, ST_MakePoint($1, $2)::geography, $3)
  AND status = 'active'
  AND max_guests >= $4;
```

#### Guest Search
```sql
-- Full-text search on guest name/email
CREATE INDEX idx_guests_search ON guests USING GIN(
    to_tsvector('english', first_name || ' ' || last_name || ' ' || COALESCE(email, ''))
);

-- Email lookup (for deduplication)
CREATE INDEX idx_guests_email ON guests(tenant_id, email);
```

### D. Financial & Reporting Indexes

```sql
-- Payment transaction lookups
CREATE INDEX idx_payment_transactions_booking ON payment_transactions(booking_id)
    WHERE booking_id IS NOT NULL;

CREATE INDEX idx_payment_transactions_date ON payment_transactions(tenant_id, created_at DESC);

-- Invoice status and due dates
CREATE INDEX idx_invoices_overdue ON invoices(tenant_id, due_date)
    WHERE status NOT IN ('paid', 'cancelled', 'void');
```

### E. Channel Manager Indexes

```sql
-- Active connections needing sync
CREATE INDEX idx_channel_connections_active ON channel_connections(property_id, channel_type)
    WHERE status = 'active' AND sync_enabled = true;

-- Connections due for sync (scheduler)
CREATE INDEX idx_channel_connections_sync_due ON channel_connections(last_sync_at, sync_frequency_minutes)
    WHERE status = 'active' AND sync_enabled = true;

-- Recent sync logs
CREATE INDEX idx_channel_sync_logs_recent ON channel_sync_logs(channel_connection_id, started_at DESC);
```

### F. Background Processing Indexes

```sql
-- Job queue (worker picks next job)
CREATE INDEX idx_background_jobs_pending ON background_jobs(queue, priority DESC, scheduled_at)
    WHERE status = 'pending';

-- Unprocessed events (event handler)
CREATE INDEX idx_system_events_unprocessed ON system_events(created_at)
    WHERE processed = false;
```

---

## Index Type Selection

### B-tree (Default)
Used for: Equality, range queries, sorting
```sql
CREATE INDEX idx_example ON table(column);
```

### GiST
Used for: Geospatial, range types, exclusion constraints
```sql
CREATE INDEX idx_properties_location ON properties USING GIST(location);
```

### GIN
Used for: Full-text search, JSONB, arrays
```sql
CREATE INDEX idx_properties_search ON properties USING GIN(to_tsvector('english', name));
CREATE INDEX idx_properties_amenities ON properties USING GIN(amenities);
```

### Partial Indexes
Used for: Filtering common subsets
```sql
CREATE INDEX idx_bookings_active ON bookings(property_id, check_in)
    WHERE status NOT IN ('cancelled', 'declined', 'no_show');
```

---

## Query Patterns & Index Usage

### Dashboard Queries

| Query | Index Used | Expected Performance |
|-------|------------|---------------------|
| Upcoming check-ins | `idx_bookings_upcoming` | < 10ms |
| Today's check-outs | `idx_bookings_checkout_today` | < 10ms |
| Unread messages | `idx_messages_unread` | < 20ms |
| Pending payments | `idx_payment_transactions_status` | < 20ms |

### Availability Checks

| Query | Index Used | Expected Performance |
|-------|------------|---------------------|
| Date range availability | `idx_bookings_active` + exclusion | < 5ms |
| Calendar month view | `idx_calendar_full` | < 20ms |
| Property search by location | `idx_properties_location` | < 50ms |

### Channel Sync

| Query | Index Used | Expected Performance |
|-------|------------|---------------------|
| Get connections for sync | `idx_channel_connections_sync_due` | < 10ms |
| Check for duplicate booking | `idx_bookings_channel` | < 5ms |
| Log sync result | Sequential insert | < 5ms |

---

## Maintenance Recommendations

### Regular Maintenance

1. **ANALYZE** - Run after significant data changes
   ```sql
   ANALYZE bookings;
   ANALYZE calendar_availability;
   ```

2. **REINDEX** - Periodically rebuild bloated indexes
   ```sql
   REINDEX TABLE bookings;
   ```

3. **Monitor Index Usage**
   ```sql
   SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
   FROM pg_stat_user_indexes
   ORDER BY idx_scan DESC;
   ```

### Identifying Unused Indexes
```sql
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexname NOT LIKE '%_pkey'
  AND indexname NOT LIKE '%_key';
```

### Index Bloat Detection
```sql
SELECT
    current_database(),
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
```

---

## Partitioning Strategy (Future)

When tables grow large (1M+ rows), consider partitioning:

### Candidates for Partitioning

1. **channel_sync_logs** - Partition by month
   ```sql
   CREATE TABLE channel_sync_logs (
       ...
   ) PARTITION BY RANGE (started_at);
   ```

2. **booking_audit_log** - Partition by month
   ```sql
   CREATE TABLE booking_audit_log (
       ...
   ) PARTITION BY RANGE (created_at);
   ```

3. **system_events** - Partition by month
   ```sql
   CREATE TABLE system_events (
       ...
   ) PARTITION BY RANGE (created_at);
   ```

### Retention Policy
- Keep detailed logs for 90 days in hot storage
- Archive to cold storage (S3) after 90 days
- Aggregate statistics for long-term retention

---

## Performance Monitoring

### Key Metrics to Watch

1. **Index Hit Ratio** (target: > 99%)
   ```sql
   SELECT
       sum(idx_blks_hit) / nullif(sum(idx_blks_hit + idx_blks_read), 0) as ratio
   FROM pg_statio_user_indexes;
   ```

2. **Sequential Scan Ratio** (target: < 5% for large tables)
   ```sql
   SELECT
       relname,
       seq_scan,
       idx_scan,
       seq_scan::float / nullif(seq_scan + idx_scan, 0) * 100 as seq_pct
   FROM pg_stat_user_tables
   WHERE seq_scan + idx_scan > 100
   ORDER BY seq_pct DESC;
   ```

3. **Slow Queries** (via pg_stat_statements)
   ```sql
   SELECT
       query,
       calls,
       mean_exec_time,
       total_exec_time
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 20;
   ```

---

## Index Size Estimates

| Table | Estimated Rows (1 year) | Index Size Estimate |
|-------|------------------------|---------------------|
| bookings | 100,000 | ~50 MB |
| calendar_availability | 3,650,000 (10K properties) | ~500 MB |
| channel_sync_logs | 5,000,000 | ~1 GB |
| booking_audit_log | 500,000 | ~200 MB |
| guests | 50,000 | ~20 MB |
| messages | 200,000 | ~80 MB |

**Total estimated index storage:** ~2 GB

---

## Best Practices Summary

1. **Always include tenant_id** in indexes for tenant-scoped tables
2. **Use partial indexes** for status-filtered queries
3. **Prefer covering indexes** for frequently accessed column combinations
4. **Monitor and remove** unused indexes
5. **Run ANALYZE** after bulk data operations
6. **Plan for partitioning** on high-volume tables
7. **Test index performance** with EXPLAIN ANALYZE before deployment
