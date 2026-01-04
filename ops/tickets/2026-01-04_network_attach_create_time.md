# Ops Ticket: Network Attachment at Container Create-Time

**Date**: 2026-01-04
**Priority**: Medium
**Type**: Infrastructure Reliability
**Status**: Phase-1 (Ticket Created)

## Problem Statement

Currently, the PMS backend container **lacks network connectivity at create-time**, requiring a post-create restart by host automation scripts to establish connectivity. This causes:

1. **Duplicate startup signatures**: Container starts → no network → host detects → restarts container → new PID=1 with generation=1 logs
2. **Delayed application readiness**: Initial startup fails health checks, wastes time in degraded mode
3. **Dependency on host automation**: Requires external timer script to fix connectivity (fragile)
4. **Confusing diagnostics**: Duplicate pool creation logs appear to be in-process race conditions, but are actually external restart artifacts

**Example scenario**:
- Docker container created without network attached
- Application starts, attempts DB connection → DNS fails (no network)
- Enters degraded mode, logs "Database connection pool initialization FAILED"
- Host timer script detects no network → restarts container
- Second startup succeeds, but logs show duplicate startup signature (generation=1 appears twice in same container lifetime)

## Current Behavior

```bash
# Current container lifecycle
docker run --name pms-backend ...
  → Container starts (PID=1, generation=1)
  → No network connectivity at create-time
  → DB connection fails (DNS resolution timeout)
  → App enters degraded mode
  → Host timer detects missing network
  → docker restart pms-backend
  → Container restarts (new PID=1, generation=1 again)
  → Network now available → DB connection succeeds
```

**Log signature**:
```
[Container startup #1 - no network]
Database connection pool created successfully ... pool_id=140509283504848
Database connection pool initialization FAILED ... Degraded mode

[Container restart #1 - network available]
Database connection pool created successfully ... pool_id=140509283504848
Database connection pool initialized ... generation=1
```

Both startups show `generation=1` because each is a fresh process start.

## Desired Behavior

```bash
# Desired container lifecycle with create-time network attachment
docker run --name pms-backend --network <network-name> ...
  → Container starts (PID=1, generation=1)
  → Network connectivity ALREADY available at create-time
  → DB connection succeeds immediately
  → App enters ready mode (no degraded mode)
  → Host timer becomes optional safety net (no restart needed)
```

**Log signature**:
```
[Container startup #1 - network attached at create-time]
Database connection pool created successfully ... pool_id=140509283504848
Database connection pool initialized ... generation=1
✅ Database connection pool initialized
🚀 PMS Backend API started successfully
```

Single startup, no restarts, no duplicate signatures.

## Acceptance Criteria

1. **Container orchestration** attaches network at `docker run` time
   - Use `docker run --network <network-name>` or equivalent
   - For Docker Compose: `networks:` section in service definition
   - For Kubernetes: Pod network attachment happens automatically
   - For Nomad/ECS/other: Equivalent network configuration

2. **Host timer script** becomes attach-only (no restart)
   - Script detects missing network attachment
   - Runs `docker network connect <network> <container>` if needed
   - **DOES NOT** restart container (network attachment is live)
   - Updated to be a safety net, not a primary mechanism

3. **Documentation** exists in `backend/docs/ops/runbook.md`
   - Explains create-time network attachment benefits
   - Shows examples for Docker CLI, Docker Compose, Kubernetes
   - Documents troubleshooting steps if network not attached

4. **Validation**:
   - Container logs show single startup signature (no duplicate generation=1)
   - DB connection succeeds on first attempt (no degraded mode)
   - Host timer script does NOT trigger restart (only attach if needed)

## Proposed Approach

### 1. Docker CLI (Manual/Script Deployment)

**Before** (no network at create-time):
```bash
docker run -d \
  --name pms-backend \
  --env-file .env \
  ghcr.io/org/pms-backend:latest
```

**After** (network attached at create-time):
```bash
docker run -d \
  --name pms-backend \
  --network pms-network \
  --env-file .env \
  ghcr.io/org/pms-backend:latest
```

### 2. Docker Compose

**Before**:
```yaml
services:
  backend:
    image: ghcr.io/org/pms-backend:latest
    env_file: .env
    # No networks section
```

**After**:
```yaml
services:
  backend:
    image: ghcr.io/org/pms-backend:latest
    env_file: .env
    networks:
      - pms-network

networks:
  pms-network:
    external: true  # Assumes network already exists
    # OR
    # driver: bridge  # Creates network if not exists
```

### 3. Kubernetes (Reference)

Kubernetes automatically attaches Pod network at create-time (no action needed).

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pms-backend
spec:
  containers:
  - name: backend
    image: ghcr.io/org/pms-backend:latest
  # Network attachment is automatic
```

### 4. Update Host Timer Script (Safety Net)

**Before** (restart-based):
```bash
# Host timer script (current)
if ! docker exec pms-backend ping -c1 database 2>/dev/null; then
  echo "No connectivity, restarting container"
  docker restart pms-backend
fi
```

**After** (attach-only):
```bash
# Host timer script (updated)
NETWORK_ATTACHED=$(docker inspect pms-backend --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' | grep -q pms-network && echo yes || echo no)

if [ "$NETWORK_ATTACHED" != "yes" ]; then
  echo "Network not attached, attaching now (no restart)"
  docker network connect pms-network pms-backend
else
  echo "Network already attached, no action needed"
fi
```

## Phase-1 Scope (This Ticket)

- Create ticket markdown file (this file)
- Update documentation (runbook.md, project_status.md)
- Provide examples for Docker CLI, Docker Compose, Kubernetes
- **DO NOT** modify actual deployment scripts/configs yet (Phase-2)

## Phase-2 Scope (Future)

- Update Docker run commands or Compose files to include `--network` flag
- Patch host timer script to attach-only (no restart)
- Validate single startup signature in production logs
- Monitor reduction in duplicate startup events

## Root Cause Analysis

The duplicate startup signatures observed in production logs (multiple `generation=1` in same container) were NOT due to:
- In-process race conditions (singleflight pattern already prevents this)
- Module re-import bugs (detection code confirmed single import)
- Concurrent ensure_pool() calls (lock prevents duplicate pool creation)

The true root cause was **external container lifecycle events**:
- **Case A**: Container replace via deployment (expected, documented)
- **Case B**: Host automation restart due to missing network at create-time (preventable with this ticket)

This ticket addresses **Case B** by ensuring network connectivity exists at create-time, eliminating the need for post-create restarts.

## References

- Runbook: `backend/docs/ops/runbook.md` → "Network Attachment at Create-Time" section
- Project Status: `backend/docs/project_status.md` → Operations bullets
- Related: "Duplicate Startup Signatures + Multiple pool_id: Distinguish External Causes" (runbook)

## Notes

- This is a **pure infrastructure change** (no application code changes)
- Backwards compatible: App already handles degraded mode gracefully if network unavailable
- Benefits all deployment methods (Docker CLI, Compose, Kubernetes, ECS, Nomad, etc.)
- Reduces noise in logs and eliminates false-positive "duplicate pool creation" alerts
