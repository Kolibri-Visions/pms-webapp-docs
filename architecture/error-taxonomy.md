# Error Taxonomy & Exception Handling

**Document Status**: Phase 1 Foundation (P1-06)
**Last Updated**: 2025-12-30
**Owner**: Backend Team

## Overview

This document defines the standardized error taxonomy for the PMS backend API. The goal is to provide consistent, machine-readable error codes and typed exceptions across all endpoints.

## Goals

1. **Consistency**: All endpoints return errors in a predictable format
2. **Machine-Readable**: Error codes allow clients to programmatically handle errors
3. **Type Safety**: Typed exceptions make error handling explicit in code
4. **Debuggability**: Structured errors with context aid debugging

## Error Code List

Error codes are defined as constants in `app/core/exceptions.py`.

### Client Errors (4xx)

| Error Code | HTTP Status | Description | When to Use |
|------------|-------------|-------------|-------------|
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist | GET/DELETE of non-existent resource |
| `NOT_AUTHORIZED` | 403 | User lacks permission | RBAC enforcement, owner-only actions |
| `FORBIDDEN` | 403 | Action is forbidden | Generic authorization failure |
| `VALIDATION_ERROR` | 422 | Request data is invalid | Business logic validation failures |
| `RESOURCE_CONFLICT` | 409 | Resource conflict detected | Generic conflicts |
| `BAD_REQUEST` | 400 | Malformed request | Invalid parameters, malformed data |

### Booking-Specific Errors

| Error Code | HTTP Status | Description | When to Use |
|------------|-------------|-------------|-------------|
| `BOOKING_CONFLICT` | 409 | Booking dates conflict | Double booking, overlapping dates |
| `BOOKING_NOT_FOUND` | 404 | Booking does not exist | GET/DELETE of non-existent booking |
| `BOOKING_CANCELLED` | 409 | Booking is already cancelled | Attempt to modify cancelled booking |

### Property-Specific Errors

| Error Code | HTTP Status | Description | When to Use |
|------------|-------------|-------------|-------------|
| `PROPERTY_NOT_FOUND` | 404 | Property does not exist | GET/DELETE of non-existent property |
| `PROPERTY_UNAVAILABLE` | 409 | Property is unavailable | Booking attempt on unavailable property |

### Server Errors (5xx)

| Error Code | HTTP Status | Description | When to Use |
|------------|-------------|-------------|-------------|
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error | Unhandled exceptions, bugs |
| `SERVICE_UNAVAILABLE` | 503 | Service is temporarily down | DB unavailable, external service down |
| `DATABASE_ERROR` | 500 | Database operation failed | DB errors (caught and converted) |

## Typed Exceptions

Typed exceptions provide a structured way to raise errors with error codes and messages.

### Base Exception: `AppError`

All typed exceptions inherit from `AppError`:

```python
from app.core.exceptions import AppError, ERROR_CODE_BOOKING_CONFLICT

raise AppError(
    code=ERROR_CODE_BOOKING_CONFLICT,
    message="Property is already booked for these dates"
)
```

**Attributes**:
- `code`: Machine-readable error code
- `message`: Human-readable error message
- `status_code`: HTTP status code (optional)

### Typed Exception Classes

**1. BookingConflictError**

Use when booking dates conflict:

```python
from app.core.exceptions import BookingConflictError

raise BookingConflictError(
    message="Property is already booked from 2025-01-01 to 2025-01-05"
)
```

**2. PropertyNotFoundError**

Use when a property is not found:

```python
from app.core.exceptions import PropertyNotFoundError

raise PropertyNotFoundError(property_id="abc-123")
# or
raise PropertyNotFoundError(message="Property with internal_name 'villa-1' not found")
```

**3. NotAuthorizedError**

Use for authorization failures (403):

```python
from app.core.exceptions import NotAuthorizedError

raise NotAuthorizedError(
    message="You do not have permission to delete this booking"
)
```

## When to Use Typed Exceptions

**Use typed exceptions when**:
- You have a specific error scenario (e.g., booking conflict)
- You want to attach additional context (e.g., property_id)
- You want clients to programmatically handle the error

**Use pre-existing exceptions when**:
- The error is generic (e.g., NotFoundException)
- No additional context is needed
- The pre-existing exception fits the use case

## Response Format (Phase 1 - P1-07)

**IMPORTANT**: Response format changes are NOT part of P1-06.

Currently, typed exceptions are raised but not converted to structured responses. This will be implemented in **Phase 1 - P1-07** (ticket P1-07).

**Current behavior** (P1-06):
```python
raise BookingConflictError(message="Property already booked")
# Raises exception, but no custom response handler yet
```

**Future behavior** (P1-07):
```python
raise BookingConflictError(message="Property already booked")
# Will return:
# {
#   "error": {
#     "code": "BOOKING_CONFLICT",
#     "message": "Property already booked"
#   }
# }
```

For now, the existing exception handlers in `app/core/exceptions.py` continue to work.

## Migration Strategy

### Phase 1 - P1-06 (Current)
- ✅ Define error codes
- ✅ Create base `AppError` class
- ✅ Create 3 typed exceptions (BookingConflictError, PropertyNotFoundError, NotAuthorizedError)
- ❌ Do NOT register exception handlers yet
- ❌ Do NOT change response formats yet

### Phase 1 - P1-07 (Next)
- Register FastAPI exception handlers for typed exceptions
- Convert responses to structured format: `{"error": {"code": "...", "message": "..."}}`
- Update all endpoints to return structured errors
- Test error response format

### Phase 1 - P1-15 (Retrospective)
- Review error taxonomy effectiveness
- Add more typed exceptions as needed
- Refine error codes based on usage

## Examples

### Example 1: Booking Conflict

**Before (generic exception)**:
```python
from fastapi import HTTPException

if booking_exists:
    raise HTTPException(status_code=409, detail="Property already booked")
```

**After (typed exception)**:
```python
from app.core.exceptions import BookingConflictError

if booking_exists:
    raise BookingConflictError(
        message="Property is already booked from 2025-01-01 to 2025-01-05"
    )
```

### Example 2: Property Not Found

**Before**:
```python
from app.core.exceptions import NotFoundException

if not property:
    raise NotFoundException(resource="Property", resource_id=property_id)
```

**After**:
```python
from app.core.exceptions import PropertyNotFoundError

if not property:
    raise PropertyNotFoundError(property_id=property_id)
```

### Example 3: Authorization Failure

**Before**:
```python
from app.core.auth import AuthorizationError

if not has_role(user, "admin"):
    raise AuthorizationError("Admin role required")
```

**After**:
```python
from app.core.exceptions import NotAuthorizedError

if not has_role(user, "admin"):
    raise NotAuthorizedError(message="Admin role required")
```

## Best Practices

1. **Use specific error codes**: Prefer `BOOKING_CONFLICT` over generic `RESOURCE_CONFLICT`
2. **Provide context in messages**: Include relevant IDs, dates, or values
3. **Keep messages user-friendly**: Avoid technical jargon or stack traces
4. **Log technical details separately**: Use logging for debug info, not error messages
5. **Be consistent**: Use the same error code for the same scenario across endpoints

## Adding New Error Codes

To add a new error code:

1. **Define constant** in `app/core/exceptions.py`:
   ```python
   ERROR_CODE_GUEST_NOT_FOUND = "GUEST_NOT_FOUND"
   ```

2. **Create typed exception** (optional but recommended):
   ```python
   class GuestNotFoundError(AppError):
       def __init__(self, guest_id: Optional[str] = None):
           message = f"Guest with ID '{guest_id}' not found" if guest_id else "Guest not found"
           super().__init__(
               code=ERROR_CODE_GUEST_NOT_FOUND,
               message=message,
               status_code=404
           )
   ```

3. **Document in this file**: Add to error code table above

4. **Use in code**:
   ```python
   from app.core.exceptions import GuestNotFoundError

   if not guest:
       raise GuestNotFoundError(guest_id=guest_id)
   ```

## Related Documents

- [Product Backlog](../product/PRODUCT_BACKLOG.md) - Epic A: Foundation & Ops (error taxonomy, RBAC, ops endpoints)
- `app/core/exceptions.py` - Exception classes and error codes
- `app/core/auth.py` - RBAC helpers and authentication

## FAQ

**Q: Should I use typed exceptions or HTTPException?**
A: Prefer typed exceptions for domain-specific errors (booking conflicts, property not found). Use HTTPException for generic errors (400, 401, 500).

**Q: When will response format change?**
A: Response format changes are in Phase 1 - P1-07, not P1-06. For now, keep using existing exception handlers.

**Q: Can I add more error codes?**
A: Yes! Follow the "Adding New Error Codes" section above. Start with a constant, then optionally create a typed exception.

**Q: What's the difference between AppError and HTTPException?**
A: `AppError` is our base class with error codes. `HTTPException` is FastAPI's generic exception. Use `AppError` for typed, structured errors.
