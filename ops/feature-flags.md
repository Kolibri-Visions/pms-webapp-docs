# Feature Flags Reference

**Purpose**: Central reference for all feature toggles controlling deployment behavior

**Audience**: Ops engineers, DevOps, deployment staff

**Source of Truth**: This file + environment configuration in deployment platform

---

## Overview

Feature flags control which features are enabled without code changes. All flags are configured via environment variables.

---

## Backend Feature Flags

### MODULES_ENABLED

**Purpose**: Enable module system vs fallback routing

**Default**: `true`

**Values**: `true` | `false` (case-sensitive)

**Behavior**:
- If `MODULES_ENABLED=true`: Use module system (`mount_modules(app)` in `backend/app/modules/bootstrap.py`)
- If `MODULES_ENABLED=false`: Use fallback (explicit router mounting in `backend/app/main.py:126-136`)

**Impact**: If false, bypasses module registry and uses explicit router mounting

**Where Used**: `backend/app/main.py:117-124`

**Recommendation**: Keep `true` in production (module system is the standard path)

---

### CHANNEL_MANAGER_ENABLED

**Purpose**: Enable Channel Manager module (Airbnb sync, webhooks, etc.)

**Default**: `false`

**Values**: `true` | `false` (case-sensitive)

**Behavior**:
- If `CHANNEL_MANAGER_ENABLED=true`: Import and mount Channel Manager module
- If `CHANNEL_MANAGER_ENABLED=false`: Channel Manager module NOT imported (disabled)

**Impact**: If false, Channel Manager endpoints NOT available, sync tasks NOT registered

**Where Used**: `backend/app/modules/bootstrap.py:86-94`

**Recommendation**: Keep `false` until Channel Manager is production-ready

**Related Docs**: [Channel Manager Architecture](../architecture/channel-manager.md)

---

## Frontend Feature Flags

### NEXT_PUBLIC_ENABLE_OPS_CONSOLE

**Purpose**: Enable Ops Console pages (`/ops/*`)

**Default**: Unset (disabled)

**Values**: `1` | `true` | `yes` | `on` (case-insensitive)

**Behavior**:
- If set to truthy value: Ops Console pages accessible (admin role required)
- If unset/false: Ops Console shows "Ops Console is Disabled" message

**Impact**: If unset, admin users cannot access `/ops/*` pages (shows disabled message, no redirect loop)

**Where Used**: `frontend/app/ops/layout.tsx:95-140`

**Recommendation**: Set `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1` in production if ops staff need access

**Related Docs**: [Frontend Ops Console](../frontend/ops-console.md)

---

## Deployment Checklist

### Production Deployment

**Backend**:
- ✅ `MODULES_ENABLED=true` (use module system)
- ✅ `CHANNEL_MANAGER_ENABLED=false` (unless channel sync is production-ready)

**Frontend**:
- ✅ `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1` (if ops staff need access to `/ops/*` pages)

### Development / Staging

**Backend**:
- ✅ `MODULES_ENABLED=true` (standard)
- ⚠️ `CHANNEL_MANAGER_ENABLED=true` (only if testing channel sync)

**Frontend**:
- ✅ `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1` (for testing ops console)

---

## Troubleshooting

### Module System Issues

**Symptom**: Routes not found, 404 errors

**Check**:
```bash
# Check logs for module mounting
grep "MODULES_ENABLED" /path/to/logs

# Expected: "MODULES_ENABLED=true → Mounting modules via module system"
```

**Fix**: Ensure `MODULES_ENABLED=true` (or unset, defaults to true)

---

### Channel Manager Not Available

**Symptom**: Channel sync endpoints return 404

**Check**:
```bash
# Check logs for channel manager
grep "Channel Manager" /path/to/logs

# Expected: "Channel Manager module enabled via CHANNEL_MANAGER_ENABLED=true"
```

**Fix**: Set `CHANNEL_MANAGER_ENABLED=true` if channel sync is needed

---

### Ops Console Shows "Disabled" Message

**Symptom**: Admin users see "Ops Console is Disabled" instead of ops pages

**Check**:
```bash
# Check frontend env vars
echo $NEXT_PUBLIC_ENABLE_OPS_CONSOLE

# Expected: "1" or "true" or "yes" or "on"
```

**Fix**: Set `NEXT_PUBLIC_ENABLE_OPS_CONSOLE=1` and redeploy frontend

---

## Related Documentation

- [Module System Architecture](../architecture/module-system.md) - How module registry works
- [Channel Manager Architecture](../architecture/channel-manager.md) - Channel sync design
- [Frontend Ops Console](../frontend/ops-console.md) - Ops Console pages implementation
- [Runbook](runbook.md) - Production troubleshooting guide

---

**Last Updated**: 2025-12-30
**Maintained By**: Backend Team
