# ADR-003: Multi-Tenancy Strategy

**Status:** Accepted
**Date:** 2025-12-21
**Decision Makers:** System Architecture Team

---

## Context

PMS-Webapp serves multiple property owners (tenants), each managing their own properties, bookings, guests, and channel connections. We need a multi-tenancy strategy that:
- Ensures complete data isolation between property owners
- Prevents accidental or malicious cross-tenant data access
- Scales efficiently as tenant count grows
- Minimizes complexity in application code
- Supports future enterprise features (teams, sub-accounts)

## Decision Drivers

1. **Security**: Absolute data isolation between tenants
2. **Simplicity**: Minimal application code changes
3. **Performance**: No significant overhead
4. **Scalability**: Handle 1000+ tenants efficiently
5. **Flexibility**: Support various tenant structures

## Options Considered

### Option 1: Row-Level Security (RLS) - Single Database

**Description:**
All tenants share one database. PostgreSQL RLS policies filter data based on the authenticated user.

**Pros:**
- Simplest infrastructure (one database)
- Database enforces isolation (defense in depth)
- Efficient connection pooling
- Easy schema migrations (one place)
- Supabase provides excellent RLS support

**Cons:**
- Requires careful policy design
- Some query overhead for policy checks
- "Noisy neighbor" potential at extreme scale

### Option 2: Schema-Per-Tenant

**Description:**
Each tenant gets a separate PostgreSQL schema within the same database.

**Pros:**
- Strong isolation
- Easy to backup/restore individual tenants
- Can customize schema per tenant

**Cons:**
- Complex connection management
- Schema migrations applied N times
- Connection pool per schema
- Harder to query across tenants

### Option 3: Database-Per-Tenant

**Description:**
Each tenant gets their own database instance.

**Pros:**
- Complete isolation
- Individual backup/restore
- No noisy neighbor issues
- Easy to migrate large tenants

**Cons:**
- Very high operational overhead
- Expensive at scale
- Difficult cross-tenant operations
- Overkill for this use case

### Option 4: Application-Level Filtering

**Description:**
Single database, application code filters by tenant_id.

**Pros:**
- Simple to implement initially
- No database-specific features needed

**Cons:**
- Error-prone (developer must remember filter)
- No database-level enforcement
- Security risk if filter is missed
- Harder to audit

## Decision

**We choose Row-Level Security (RLS) with a single shared database** for the following reasons:

1. **Database-Level Enforcement**: RLS policies are evaluated by PostgreSQL for every query, providing defense in depth even if application code has bugs.

2. **Supabase Integration**: Supabase Auth tokens carry user identity (`auth.uid()`) that RLS policies can reference directly.

3. **Operational Simplicity**: Single database means one connection pool, one backup strategy, one set of migrations.

4. **Performance**: RLS overhead is minimal with proper indexing. PostgreSQL optimizes policy checks efficiently.

5. **Scalability**: Can handle thousands of tenants in one database with proper partitioning if needed later.

6. **Developer Experience**: Developers write normal queries; RLS is transparent. Less code, fewer bugs.

## Consequences

### Positive

- Data isolation enforced at database level
- No tenant filtering code in application
- Single database simplifies operations
- Supabase Auth integrates seamlessly
- Easy to add new tables with consistent policies

### Negative

- Must design RLS policies carefully
- Some queries need restructuring for RLS
- Testing requires multi-user setup
- Service role access needs careful management

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| RLS policy bug exposes data | Comprehensive security testing, policy review process |
| Service role misuse | Strict code review for service role usage, audit logging |
| Performance degradation | Index on owner_id, query analysis, policy optimization |
| Complex cross-tenant queries | Use service role with explicit tenant context, audit |

## Implementation

### Table Structure

```sql
-- All tenant-scoped tables include owner_id
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES auth.users(id) NOT NULL,
    name TEXT NOT NULL,
    -- ... other fields
);

-- Tables that reference properties inherit isolation
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID REFERENCES properties(id) NOT NULL,
    -- No direct owner_id needed; isolation via property_id
);
```

### RLS Policies

```sql
-- Properties: Direct ownership check
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner_crud" ON properties
    FOR ALL
    USING (auth.uid() = owner_id)
    WITH CHECK (auth.uid() = owner_id);

-- Bookings: Check via property ownership
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "owner_via_property" ON bookings
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM properties
            WHERE properties.id = bookings.property_id
            AND properties.owner_id = auth.uid()
        )
    );

-- Guest access to their own bookings
CREATE POLICY "guest_own_bookings" ON bookings
    FOR SELECT
    USING (guest_id = auth.uid());

-- Public read access for property search (no auth required)
CREATE POLICY "public_property_view" ON properties
    FOR SELECT
    USING (status = 'active');
```

### Service Role Usage

```python
# Service role bypasses RLS - use sparingly and with explicit tenant context
from supabase import create_client

# Regular client (respects RLS)
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Service role client (bypasses RLS) - for admin operations
service_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Example: Daily reconciliation (cross-tenant)
async def daily_reconciliation():
    # Explicitly iterate tenants to maintain audit trail
    for owner in await service_client.table("auth.users").select("id").execute():
        logger.info(f"Reconciling for owner: {owner['id']}")
        # Process each owner's data explicitly
        properties = await service_client.table("properties") \
            .select("*") \
            .eq("owner_id", owner["id"]) \
            .execute()
        # ...
```

### Testing RLS

```python
import pytest
from supabase import create_client

@pytest.fixture
def owner_a_client():
    """Client authenticated as Owner A."""
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.auth.sign_in_with_password(email="owner_a@test.com", password="...")
    return client

@pytest.fixture
def owner_b_client():
    """Client authenticated as Owner B."""
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.auth.sign_in_with_password(email="owner_b@test.com", password="...")
    return client

def test_rls_isolation(owner_a_client, owner_b_client, owner_a_property_id):
    """Owner B cannot see Owner A's properties."""
    # Owner A can see their property
    result = owner_a_client.table("properties").select("*").eq("id", owner_a_property_id).execute()
    assert len(result.data) == 1

    # Owner B cannot see Owner A's property
    result = owner_b_client.table("properties").select("*").eq("id", owner_a_property_id).execute()
    assert len(result.data) == 0  # RLS filters it out
```

## Future Considerations

1. **Teams/Sub-Accounts**: Add `organization_id` and `role` to support property management companies with multiple users.

2. **Table Partitioning**: If a single owner has millions of bookings, partition by date range.

3. **Read Replicas**: Route read-heavy queries (analytics) to replicas while writes go to primary.

## References

- [ADR-002: Database Choice](./ADR-002-database-choice.md)
- [Supabase RLS Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
