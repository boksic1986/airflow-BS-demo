---
name: fastapi-backend-dev
description: Develop FastAPI backend for airflow-demo. Use for APIs, database models, Airflow client, sample parser, QC parser, logs and artifact endpoints.
---

## Required reading

- `AGENTS.md`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/10_QC_LOGGING_REPORTING.md`

## Workflow

1. Confirm API/DB contract before coding.
2. Implement minimal models/endpoints.
3. Add or update tests.
4. Prevent path traversal for log/artifact reads.
5. Keep secrets out of logs.
6. Update API/DB docs when behavior changes.

## Acceptance

- Backend health endpoint works.
- Tests for changed endpoints pass.
- Errors return structured JSON.
- `HANDOFF.md` lists commands run and skipped.
