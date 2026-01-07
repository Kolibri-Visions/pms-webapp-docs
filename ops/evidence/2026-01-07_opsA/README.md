# Ops A — Production Verification Evidence (2026-01-07)

**Verification Date**: 2026-01-07

**Deployed Commit**: `db0f83de1335be1b165cdac01f28382bca2255c4`

**Process Started**: 2026-01-07T12:49:04.335364+00:00

## Verification Results

### Deploy Verification (pms_verify_deploy.sh)
- **Result**: `rc=0` (all checks passed)
- **Health Endpoint**: HTTP 200
- **Readiness Endpoint**: HTTP 200
- **/api/v1/ops/version**: HTTP 200
- **Commit Prefix Match**: `db0f83d` ✅ PASSED

### Domain Onboarding Verification (pms_domain_onboarding_verify.sh)
- **Result**: `rc=0` (all checks passed)
- **Domain**: api.fewo.kolibri-visions.de
- **Test Origin**: https://fewo.kolibri-visions.de
- **Agency ID**: ffd0123a-10b6-40cd-8ad5-66eee9757ab7
- **Health Check**: HTTP 200
- **CORS Preflight**: PASS (Access-Control-Allow-Origin: https://fewo.kolibri-visions.de)

## Evidence Files (Local Paths)

The following log files were generated during this verification run:

1. **Deploy Verification Log**:
   - Path: `backend/docs/ops/evidence/2026-01-07_opsA/pms_verify_deploy_db0f83d_2026-01-07_125532.log`
   - Script: `backend/scripts/pms_verify_deploy.sh`
   - Exit Code: 0

2. **Domain Onboarding Verification Log**:
   - Path: `backend/docs/ops/evidence/2026-01-07_opsA/opsA_domain_onboarding_api.fewo.kolibri-visions.de_db0f83d_2026-01-07_125545.log`
   - Script: `backend/scripts/pms_domain_onboarding_verify.sh`
   - Exit Code: 0

## Important Note

**`*.log` files are gitignored by design** (`.gitignore:33: *.log`).

Log files contain full command output including timestamps, HTTP headers, and detailed diagnostics. They are excluded from version control to:
- Avoid repository bloat
- Prevent accidental exposure of sensitive data (IPs, headers, timing info)
- Keep evidence collection ephemeral and reproducible

### Reproducing Evidence

To reproduce this verification evidence, re-run the verification scripts against the same deployment:

```bash
# Set environment
export HOST=https://api.fewo.kolibri-visions.de
export EXPECT_COMMIT=db0f83d

# Run deploy verification
./backend/scripts/pms_verify_deploy.sh

# Run domain onboarding verification
DOMAIN=api.fewo.kolibri-visions.de \
TEST_ORIGIN=https://fewo.kolibri-visions.de \
AGENCY_ID=ffd0123a-10b6-40cd-8ad5-66eee9757ab7 \
./backend/scripts/pms_domain_onboarding_verify.sh
```

Both scripts should exit with `rc=0` if the deployment is healthy and correctly configured.

## Summary

Ops A (Customer Domain Onboarding SOP + Verify Script) has been verified on production:
- ✅ Deploy verification passed (commit match, all health checks)
- ✅ Domain onboarding verified (api.fewo.kolibri-visions.de)
- ✅ CORS preflight verified (https://fewo.kolibri-visions.de)
- ✅ Agency mapping confirmed (ffd0123a-10b6-40cd-8ad5-66eee9757ab7)
- ✅ All scripts exited with rc=0

See `backend/docs/project_status.md` for full Ops A implementation details and verification criteria.
