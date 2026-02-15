# Property Edit Modal — Extended Fields

**Added**: 2026-02-15

This runbook chapter covers the extended property edit modal in the Admin UI.

## Overview

The property edit modal (`/properties/[id]`) was extended with additional editable fields organized into logical sections.

## New Fields (2026-02-15)

### Kapazität (Capacity)

| Field | Type | Description |
|-------|------|-------------|
| `size_sqm` | number (nullable) | Property size in square meters |
| `beds` | integer (nullable) | Number of beds |

### Buchungsregeln (Booking Rules)

| Field | Type | Description |
|-------|------|-------------|
| `min_nights` | integer (nullable) | Minimum nights for booking |
| `max_nights` | integer (nullable) | Maximum nights for booking |

### Preise (Pricing)

| Field | Type | Description |
|-------|------|-------------|
| `base_price` | decimal (nullable) | Base price per night |
| `cleaning_fee` | decimal (nullable) | One-time cleaning fee |

### Check-in/Check-out

| Field | Type | Description |
|-------|------|-------------|
| `check_in_time` | time string (nullable) | Check-in time (e.g., "15:00") |
| `check_out_time` | time string (nullable) | Check-out time (e.g., "10:00") |
| `check_in_instructions` | text (nullable) | Instructions for guests |

### Eigentümer (Owner)

| Field | Type | Description |
|-------|------|-------------|
| `owner_id` | UUID (nullable) | FK to owners table |

The owner field displays a dropdown populated from the agency's owners list.

### Adresse (Address)

| Field | Type | Description |
|-------|------|-------------|
| `street` | string (nullable) | Street address |
| `postal_code` | string (nullable) | Postal/ZIP code |
| `city` | string (nullable) | City name |
| `country` | string (nullable) | Country code (e.g., "DE") |
| `latitude` | decimal (nullable) | GPS latitude |
| `longitude` | decimal (nullable) | GPS longitude |

## File Location

**Frontend**: `frontend/app/properties/[id]/page.tsx`

## Common Issues

### NULL Values Not Saving

**Symptom**: Clearing a field doesn't save as NULL.

**Cause**: Frontend may send empty string instead of null.

**Resolution**: Check `setEditData` handlers use explicit `null` for empty values:
```typescript
onChange={(e) => setEditData({
  ...editData,
  size_sqm: e.target.value === "" ? null : parseFloat(e.target.value)
})}
```

### Owner Dropdown Empty

**Symptom**: Owner dropdown shows no options.

**Cause**: Agency has no owners, or API fetch failed.

**Debug**:
```bash
curl -s "$API_URL/api/internal/owners" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-agency-id: $AGENCY_ID" | jq '.items'
```

### Decimal Precision Issues

**Symptom**: Price shows unexpected decimal places.

**Cause**: JavaScript floating point representation.

**Resolution**: Use `toFixed(2)` for display, store as integer cents in DB if precision critical.

## Verification

**Manual Test**:
1. Navigate to `/properties/[id]`
2. Click "Bearbeiten" (Edit) button
3. Verify all sections visible: Grunddaten, Kapazität, Adresse, Preise, Buchungsregeln, Check-in/out, Status
4. Edit a field, save, refresh — verify value persisted

**Related Commits**: `c372d62`, `df97474`
