# ADR-002: Database Choice

**Status:** Accepted
**Date:** 2025-12-21
**Decision Makers:** System Architecture Team

---

## Context

We need to select a database solution for the PMS-Webapp that will:
- Serve as the single source of truth for all booking data
- Support multi-tenancy with data isolation between property owners
- Handle complex queries (availability, calendar, reporting)
- Scale to 1000+ properties with 10000+ bookings/month
- Provide high availability and disaster recovery
- Integrate with our FastAPI backend

## Decision Drivers

1. **Multi-Tenancy**: Robust data isolation between property owners
2. **Performance**: Fast availability checks and calendar queries
3. **Reliability**: High availability, automatic backups
4. **Developer Experience**: Easy setup, good tooling
5. **Cost**: Reasonable pricing at target scale
6. **Managed vs Self-Hosted**: Operational burden consideration

## Options Considered

### Option 1: Supabase (Managed PostgreSQL)

**Pros:**
- Built-in Row-Level Security (RLS) for multi-tenancy
- Integrated authentication (Supabase Auth)
- Real-time subscriptions via WebSocket
- Automatic backups and point-in-time recovery
- Edge Functions for serverless logic
- PostgREST for direct database API
- Generous free tier, reasonable scaling costs
- Quick setup with excellent documentation

**Cons:**
- Vendor lock-in for Supabase-specific features
- Less control than self-hosted
- Some advanced PostgreSQL features may be limited
- Real-time has scaling limits

### Option 2: Self-Hosted PostgreSQL (on AWS RDS or similar)

**Pros:**
- Full control over configuration
- No vendor lock-in for database layer
- Can use any PostgreSQL extension
- Potentially lower cost at very high scale

**Cons:**
- Requires manual RLS policy management
- No built-in auth (need separate solution)
- Operational burden (backups, updates, monitoring)
- No built-in real-time features
- Higher initial setup effort

### Option 3: PlanetScale (MySQL-compatible)

**Pros:**
- Excellent horizontal scaling
- Branching for schema changes
- Good developer experience

**Cons:**
- MySQL, not PostgreSQL (less rich SQL features)
- No native RLS support
- Would require application-level multi-tenancy
- Foreign keys disabled by default

### Option 4: CockroachDB

**Pros:**
- Distributed SQL with automatic scaling
- Strong consistency
- Multi-region support

**Cons:**
- Higher cost
- More complex operational model
- Overkill for initial scale
- Less ecosystem support

## Decision

**We choose Supabase (Managed PostgreSQL)** for the following reasons:

1. **Row-Level Security (RLS)**: Supabase makes RLS first-class, perfect for multi-tenant property isolation. Policies are defined in SQL and enforced at the database level.

2. **Integrated Authentication**: Supabase Auth provides ready-to-use authentication with JWT tokens that integrate directly with RLS policies.

3. **Real-Time Subscriptions**: Built-in WebSocket support enables real-time booking notifications without additional infrastructure.

4. **PostgreSQL Foundation**: Full PostgreSQL 15+ with all features (exclusion constraints for calendar, JSONB, full-text search).

5. **Managed Operations**: Automatic backups, point-in-time recovery, and monitoring reduce operational burden.

6. **Developer Experience**: Excellent dashboard, CLI, and documentation speed up development.

7. **Cost-Effective**: Free tier for development, Pro tier ($25/mo) handles our target scale.

## Consequences

### Positive

- Multi-tenancy enforced at database level (not application)
- Reduced development time with integrated auth
- Real-time features without additional infrastructure
- No database operations burden
- Easy local development with Supabase CLI

### Negative

- Vendor lock-in for auth and real-time features
- RLS adds complexity to query patterns
- Some advanced PostgreSQL configs not available
- Real-time has connection limits

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Supabase vendor lock-in | Core data model is standard PostgreSQL; only auth/realtime are Supabase-specific |
| RLS performance overhead | Careful policy design, indexing, query optimization |
| Real-time scaling limits | Use for notifications only, not high-frequency data |
| Supabase service outage | Supabase runs on AWS with multi-AZ; backup to self-hosted PostgreSQL as DR option |

## RLS Implementation

```sql
-- Enable RLS on all tables
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE channel_connections ENABLE ROW LEVEL SECURITY;

-- Policy: Owners can only access their own properties
CREATE POLICY "owner_isolation" ON properties
    FOR ALL
    USING (auth.uid() = owner_id);

-- Policy: Owners can access bookings for their properties
CREATE POLICY "owner_booking_access" ON bookings
    FOR ALL
    USING (
        property_id IN (
            SELECT id FROM properties WHERE owner_id = auth.uid()
        )
    );

-- Policy: Guests can view their own bookings
CREATE POLICY "guest_booking_view" ON bookings
    FOR SELECT
    USING (guest_id = auth.uid());

-- Service role bypasses RLS for internal operations
-- (used by backend for cross-tenant operations like reconciliation)
```

## Schema Design

```sql
-- Core tables (simplified)
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES auth.users(id) NOT NULL,
    name TEXT NOT NULL,
    -- ... other fields
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id) NOT NULL,
    -- Exclusion constraint prevents overlapping bookings
    CONSTRAINT no_overlap EXCLUDE USING gist (
        property_id WITH =,
        daterange(check_in, check_out) WITH &&
    ) WHERE (status NOT IN ('cancelled', 'inquiry'))
);

-- Indexes for common queries
CREATE INDEX idx_bookings_property_dates
    ON bookings(property_id, check_in, check_out);
CREATE INDEX idx_bookings_status
    ON bookings(status) WHERE status NOT IN ('cancelled', 'checked_out');
```

## References

- [Supabase RLS Documentation](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL Exclusion Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-EXCLUSION)
- [ADR-003: Multi-Tenancy Strategy](./ADR-003-multi-tenancy.md)
