---
name: deployment-debug
description: Debug deployment and server issues for airflow-demo. Use for Docker Compose, Airflow service health, backend/frontend startup, qsub availability, and runbook updates.
---

## Required reading

- `AGENTS.md`
- `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`
- `SERVER_INFO.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/13_SECURITY_AND_OPERATIONS.md`

## Workflow

1. Declare `test` or `production`; verify SSH alias, hostname, control root, current release and actual service mounts with read-only commands.
2. Run `docker compose config` before starting services.
3. Use `docker compose logs --tail=...` for diagnostics.
4. Do not delete volumes by default.
5. Stop on environment or permission drift; do not substitute a path from the other environment.
6. Record findings in `SERVER_INFO.md` and `CURRENT_STATE.md`.
7. Append failures and next steps to `HANDOFF.md`.

## Forbidden without explicit approval

- `docker compose down -v`
- `docker system prune -a`
- `docker volume prune`
- destructive file deletion
- unfiltered image/container cleanup or any cleanup outside the Airflow Compose project
