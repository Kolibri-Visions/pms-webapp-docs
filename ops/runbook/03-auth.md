# Authentication & Authorization Operations

This chapter covers JWT authentication, role-based access control, and auth troubleshooting.

## Overview

The PMS system uses Supabase Auth with JWT tokens. Multi-tenancy is enforced via:
- JWT claims (agency_id, role)
- RLS policies in PostgreSQL
- API-level permission checks

## Key Concepts

- **JWT Tokens**: Issued by Supabase Auth, validated by backend
- **Roles**: admin, manager, staff, owner, accountant
- **Agency Isolation**: All data scoped by agency_id

## Common Operations

### Verify Token

```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api.fewo.kolibri-visions.de/api/v1/me
```

### Check Token Claims

Use jwt.io or the backend's token introspection endpoint.

## Troubleshooting

See main runbook sections:
- Token validation failures
- Permission denied errors
- Agency resolution issues

---

*For detailed procedures, see the legacy runbook.md.*
