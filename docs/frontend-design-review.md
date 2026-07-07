# Frontend Design Review

Date: 2026-07-08

## Current UI Problems

The current frontend proves the backend/API workflow, but it reads as an engineering smoke page rather than a production task platform:

- Information architecture is flat: PGT-A create form, WES create form, run list, run detail, QC, rules, logs, and artifacts all compete on one screen.
- Layout is inconsistent for real work: the run list is a narrow aside, submission controls sit above detail content, and there is no durable page model for Dashboard, Runs, Samples, Workflows, or Failures.
- Status semantics are duplicated through CSS classes instead of a reusable component with icon, label, and accessible text.
- Run detail lacks a strong hierarchy: Airflow run, Snakemake/qsub rule state, QC, files, config, logs, and reanalysis actions are visible but not prioritized.
- Logs are displayed as static lines without search, copy, stream emphasis, or failed-run default-to-stderr behavior.
- QC is technically visible, but not framed as production interpretation; PGT-A workflow success and QC fail can be confused.
- Submission is pipeline-specific and demo-specific; it does not yet look like a WES/NIPT/WGS-capable sample submission workflow.
- Loading, empty, and error states exist in places but are not a consistent page/component contract.
- Mobile and narrow widths collapse, but the design remains dense in the wrong places because the core information model is not separated.

## Reference Patterns

- BaseSpace and Seven Bridges separate projects/runs/tasks/files and make run health, samples, QC, and logs inspectable without SSH.
- shadcn/ui encourages small, typed, composable primitives instead of one large page component.
- shadcn-admin uses a persistent sidebar/topbar shell, dense dashboard cards, data tables, and settings surfaces suitable for internal tools.
- Ant Design Pro informs the list/detail/form split: filterable tables, action toolbars, compact descriptions, and page-level state.
- Refine and react-admin frame backend entities as resources: runs, samples, workflows, artifacts, and failures each get their own route and list/detail behaviors.
- DESIGN.md-style documentation is useful here because status colors, log behavior, and QC interpretation must stay consistent as agents add pipelines.

## Keep

- Existing FastAPI-only data access through `frontend/src/api.ts`.
- Existing PGT-A server-path scan/create/submit behavior.
- Existing WES mock create/submit/resume/rerun behavior.
- Existing `/runs`, `/samples`, `/rules`, `/qc`, `/logs`, and `/artifacts` API contracts.
- Existing Vite React stack and `lucide-react` icons.
- Remote-on-fengxian acceptance rule.

## Refactor

- Replace the single workspace with routed pages and a persistent app shell.
- Split API-independent UI into reusable components.
- Centralize status labels, colors, icons, and terminal/active-state logic.
- Move demo data for unavailable NIPT/WGS/resource features into fixtures marked as mock.
- Turn run detail into a summary header plus workflow/QC/logs/files/config tabs.
- Turn logs and failures into diagnostic surfaces, not text dumps.

## Do Not Do

- Do not connect the frontend to Airflow DB or Postgres directly.
- Do not introduce Ant Design, Tailwind, or shadcn package dependencies in this pass.
- Do not make unsupported NIPT/WGS flows look production-ready; label them as demo/mock.
- Do not hide QC fail behind workflow success.
