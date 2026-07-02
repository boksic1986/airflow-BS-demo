---
name: react-dashboard-dev
description: Develop React frontend for airflow-demo. Use for dashboard, submit form, run detail, rule table, QC panel, log viewer, and reanalysis UI.
---

## Required reading

- `AGENTS.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/05_API_CONTRACT.md`

## Workflow

1. Consume backend API only.
2. Keep API client isolated from components.
3. Show loading, empty, error states.
4. Tail logs instead of loading huge files.
5. Failed rule should default to stderr view.
6. Update UI spec if behavior changes.

## Do not

- Do not connect directly to Postgres.
- Do not query Airflow metadata DB.
- Do not hardcode server-specific URLs; use config/env.
