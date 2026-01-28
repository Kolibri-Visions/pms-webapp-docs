# Golden Paths

Quick-reference procedures for common operations. These are the "happy paths" that should work 99% of the time.

## Deploy New Version

1. Merge PR to `main`
2. Coolify auto-deploys backend + frontend
3. Run `./backend/scripts/pms_verify_deploy.sh`
4. If verification passes, done

## Rollback

1. In Coolify, select previous deployment
2. Click "Rollback"
3. Run verification script

## Check System Health

```bash
curl -s https://api.fewo.kolibri-visions.de/health | jq
curl -s https://api.fewo.kolibri-visions.de/health/ready | jq
```

## Run Smoke Tests

```bash
export API_BASE_URL="https://api.fewo.kolibri-visions.de"
export ADMIN_BASE_URL="https://admin.fewo.kolibri-visions.de"
export JWT_TOKEN="<your_token>"
./backend/scripts/pms_verify_deploy.sh
```

---

*See main runbook for detailed troubleshooting.*
