# Deployment Operations

This chapter covers deployment procedures, rollback strategies, and environment management.

## Overview

The PMS system deploys via Coolify with automatic deployments from the `main` branch. Backend (FastAPI) and frontend (Next.js) are deployed as separate containers.

## Deployment Flow

1. **PR merged to main** → Coolify webhook triggered
2. **Build** → Docker images built from Dockerfiles
3. **Deploy** → Rolling deployment with health checks
4. **Verify** → Run `pms_verify_deploy.sh`

## Environment Variables

Critical environment variables are managed in Coolify secrets. Never commit secrets to the repository.

## Troubleshooting

See main runbook sections:
- Database connectivity issues
- Container startup failures
- Health check failures

---

*For detailed procedures, see the legacy runbook.md.*
