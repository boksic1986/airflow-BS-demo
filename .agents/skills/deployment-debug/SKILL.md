---
name: deployment-debug
description: Debug deployment and server issues for airflow-demo. Use for Docker Compose, Airflow service health, backend/frontend startup, qsub availability, and runbook updates.
---

## Required reading

- `AGENTS.md`
- `SERVER_INFO.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/13_SECURITY_AND_OPERATIONS.md`

## Workflow

1. Inspect environment with read-only commands first.
2. Run `docker compose config` before starting services.
3. Use `docker compose logs --tail=...` for diagnostics.
4. Do not delete volumes by default.
5. Record findings in `SERVER_INFO.md` and `CURRENT_STATE.md`.
6. Append failures and next steps to `HANDOFF.md`.

## Forbidden without explicit approval

- `docker compose down -v`
- `docker system prune -a`
- `docker volume prune`
- destructive file deletion
