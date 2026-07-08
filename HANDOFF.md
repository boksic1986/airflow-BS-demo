# HANDOFF.md

> Agent 交接记录。最新记录放在最上面。

## Handoff Template

```markdown
## <YYYY-MM-DD HH:MM> - <agent name> - <task id/title>

### Goal

### Completed

### Changed files

### Commands run

| Command | Result | Notes |
|---|---|---|
|  |  |  |

### Tests

### Not run / why

### Current git status

### Risks

### Open questions

### Next recommended task

### Rollback notes
```

## Records

## 2026-07-08 17:10 - Codex - T104 Dashboard performance, observability, and intake config

### Goal

Replace Dashboard frontend fan-out with backend aggregate APIs, make Run Tracker
pipeline-driven and paginated, display node/resource/intake state clearly, and
move intake scanner roots into `config/intake.yaml`.

### Completed

- Added `/api/dashboard/overview`, `/api/dashboard/runs`,
  `/api/system/resources`, and `/api/intake/config`.
- Added `config/intake.yaml` and `INTAKE_CONFIG_PATH=/app/config/intake.yaml`;
  backend falls back to legacy env roots only if the YAML is missing.
- Added backend resource telemetry from host `/proc` plus Docker stats fallback.
- Changed Dashboard to left-side pipeline selection (`All pipelines`, `PGT-A`,
  `NIPT Docker`), visual status distribution/trend/QC panels, paginated
  10-row Run Tracker, intake scanner cards, and bottom health/resource/activity
  panels.
- Changed Run Tracker to consume `/api/dashboard/runs` rows instead of calling
  run detail/progress/rules for every visible run.
- Fixed intake display semantics so observed/bootstrap rows are not shown as
  queued execution.
- Updated API/frontend/Airflow/NIPT/runbook docs, task/state docs, and manifest.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `config/intake.yaml`
- `backend/app/config.py`
- `backend/app/dashboard_service.py`
- `backend/app/intake_config.py`
- `backend/app/intake_service.py`
- `backend/app/main.py`
- `backend/app/system_resources.py`
- `backend/requirements.txt`
- backend tests for dashboard, intake config, and system resources
- `frontend/src/api.ts`
- `frontend/src/components/RunTracker.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/styles.css`
- `frontend/src/App.test.tsx`
- docs/state/manifest files

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git diff --check` | success | Warning only: `docs/02_ENGINEERING_SPEC.md` CRLF will be normalized next time Git touches it |
| manifest consistency check | success | `file_count=186`, listed files `186`, missing `0` |
| local `py -3 -m py_compile ...` | success | Syntax-only check for changed backend modules |
| `docker compose -f docker-compose.yaml config --quiet` on fengxian | success | Compose rendered with `./config:/app/config:ro` |
| `docker build --target test -f frontend/Dockerfile frontend` on fengxian | success | 10 Vitest tests passed |
| backend Docker targeted pytest | success | 7 tests passed: dashboard, intake config, resources |
| `airflow dags list-import-errors` on fengxian | success | `No data found` |
| `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend` | success | Frontend production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-worker airflow-scheduler frontend` | success | Did not touch Postgres, Redis, volumes, or unpause intake |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `GET /api/health` and `/api/health/airflow` | success | Backend ok; Airflow scheduler/metadatabase healthy |
| `GET /api/dashboard/overview?pipeline=all` | success | `runs=26`, `running=0`, `failed=8`, intake `bootstrap=21` |
| `GET /api/dashboard/runs?pipeline=all&limit=10&offset=0` | success | `total=26`, `items=10`, `limit=10` |
| `GET /api/system/resources` | success | `source=host_proc`, `cores=128`, disks `/` and `/data` |
| `GET /api/intake/config` | success | `source=/app/config/intake.yaml`, pipelines `pgta`, `nipt_docker` |
| endpoint timing on fengxian | success | overview about `0.019s`; runs first page about `1.641s` |
| `airflow dags list | grep bio_intake_scan` | success | Final column `True`; DAG remains paused |

### Tests

Remote acceptance passed on `ssh fengxian`. T104 did not submit new PGT-A/NIPT
runs and did not run NIPT `full_run`.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no lint script.
- NIPT `full_run` was not run because it is a heavy workflow and still requires
  explicit approval plus `NIPT_ALLOW_HEAVY_RUN=true`.
- `bio_intake_scan` was not unpaused; T104 acceptance keeps it paused.

### Current git status

Local worktree is `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`
on `codex/dashboard/T104-dashboard-intake-config` with T104 changes ready to
commit.

### Risks

- `/api/dashboard/runs` still calls live progress for active/failed rows on the
  current page. This is intentionally limited to page size 10, but Airflow REST
  latency can still affect that endpoint.
- `GET /api/system/resources` returns `source=host_proc` on fengxian because
  Docker stats were not available from the backend container; this is an
  expected degraded mode.
- The scanner config is now repo-owned. Operators should review
  `config/intake.yaml` before unpausing `bio_intake_scan`.

### Open questions

- Whether to add a small Settings/Intake admin panel for explicit bootstrap and
  unpause guidance.
- Whether to expose per-container Docker stats by granting backend controlled
  access, or keep host-only resource telemetry.

### Next recommended task

Add an Intake settings page that shows `/api/intake/config`, last scan time,
bootstrap guidance, and an explicit operator checklist before unpausing
`bio_intake_scan`.

### Rollback notes

Revert T104 files and recreate backend/frontend. Do not delete Postgres, Docker
volumes, `shared/runs`, PGT-A rawdata, or NIPT source folders. If rollback is
needed, keep `bio_intake_scan` paused and continue using T103 submit/scan flows.

## 2026-07-08 15:27 - Codex - T103 PGT-A/NIPT batch scan and auto intake

### Goal

Replace new NIPT Docker `run1/run2` template submission with server-path scanned chip batches, add safe PGT-A/NIPT auto-intake discovery, and keep PGT-A/T102 progress behavior intact.

### Completed

- Added NIPT support to `POST /api/input/scan` plus `GET /api/input/roots`.
- Added NIPT clean FASTQ scanner for chip folders with top-level `*.clean.fastq.gz` R1/R2 pairs; nested adapter FASTQs remain out of v1.
- Changed new NIPT Docker run creation to accept `rawdata_root` and scanned `selected_samples`; `template_id` remains compatibility-only.
- Added `intake_discovery` model/migration, `/api/intake/status`, and `/api/intake/scan-and-submit`.
- Added paused-by-default `bio_intake_scan` DAG that calls backend intake endpoint.
- Updated `bio_nipt_docker` runner for scanned batches: run-local chip CSV/config/compose, read-only `/input_batch`, no large FASTQ copy.
- Updated Dashboard with read-only Intake auto scanner panel.
- Updated Submit Task to use one server-path scan UX for PGT-A/NIPT and create one NIPT run per selected chip folder.
- Updated docs/spec/runbook/state/manifest.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `backend/app/config.py`
- `backend/app/input_scanner.py`
- `backend/app/intake_service.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/run_service.py`
- `backend/alembic/versions/20260708_0002_intake_discovery.py`
- backend tests for scanner, scan API, intake, NIPT lifecycle, models
- `dags/bio_intake_scan.py`
- `dags/bio_nipt_docker.py`
- `dags/nipt_docker_runner.py`
- DAG/runner tests for intake and scanned NIPT
- frontend API, Dashboard, Submit, mocks, tests
- docs `02/04/05/06/07/09/11`, `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`, `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git diff --check` | success | Local and remote whitespace checks passed |
| manifest consistency check | success | `file_count=179`, listed files `179`, missing `0` |
| local `py -3.14 -m py_compile ...` | success | Local syntax-only check for changed backend/DAG files |
| `docker compose -f docker-compose.yaml config --quiet` on fengxian | success | Compose rendered after NIPT scan/intake env changes |
| `docker build --target test -f frontend/Dockerfile frontend` on fengxian | success | 10 Vitest tests passed |
| backend Docker targeted pytest | success | 25 tests passed |
| Airflow DAG unittest via `/usr/local/bin/python` | success | 4 tests passed for `bio_intake_scan` and `bio_nipt_docker` |
| NIPT runner/progress unittest via worker venv python | success | 12 tests passed |
| `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend` | success | Frontend build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-scheduler airflow-worker frontend` | success | Recreated services without deleting volumes |
| `docker compose -f docker-compose.yaml exec -T backend alembic upgrade head` | success | Applied `20260708_0002` intake discovery migration |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `/api/health`, `/api/health/airflow` | success | Backend ok; Airflow scheduler/metadatabase healthy |
| `airflow dags list-import-errors` | success | `No data found` |
| `GET /api/input/roots?pipeline=nipt_docker` | success | Returned `/opt/pipelines/NIPT/fastq` |
| `POST /api/input/scan` for NIPT | success | Returned clean FASTQ candidates under chip folder `FQ2025/250103_NDX550692_RUO_0044_AH3H37BGYW` |
| scanned NIPT mount smoke `NIPT_20260708_072349_4F942A` | success | Airflow/backend success, progress 100, `nipt_mount_smoke=success`, QC pass 1 |
| intake bootstrap `POST /api/intake/scan-and-submit` | success | Existing PGT-A/NIPT batches recorded as `observed/bootstrap`; no historical auto-submit |

### Tests

Remote acceptance passed on `ssh fengxian`. The important runtime proof is `NIPT_20260708_072349_4F942A`, created without `template_id` from a scanned NIPT chip folder, submitted to `manual__NIPT_20260708_072349_4F942A`, and completed `success`.

### Not run / why

- NIPT `full_run` was not run because it is a heavy 40-core batch and remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- PGT-A `baseline_qc` was not run in T103; acceptance used scanning/bootstrap and the light NIPT `mount_smoke`.
- `bio_intake_scan` was not unpaused; it is intentionally paused until operators review bootstrap rows and choose to enable automatic intake.

### Current git status

Local worktree: `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign` on `codex/intake/T103-pgta-nipt-auto-scan` with T101/T102/T103 changes pending. Remote `/home/jiucheng/project/airflow-demo` has the same overlay deployed and validated.

### Risks

- `bio_intake_scan` should not be unpaused before reviewing `/api/intake/status`; otherwise future stable changed fingerprints will auto-create/submits runs.
- Backend scans real server paths and records real file paths/metadata in biodemo; do not commit patient-identifying sample metadata beyond minimal path fixtures.
- Airflow worker still has Docker socket access for NIPT Docker; scheduler/API server do not.
- Legacy `template_id` code remains for historical compatibility and tests, but should not be presented as a current Submit entrypoint.

### Open questions

- Whether to unpause `bio_intake_scan` for continuous demo automation after operator review.
- Whether to approve any supervised NIPT `full_run`, with `NIPT_ALLOW_HEAVY_RUN=true` and a defined time/resource window.
- Whether PGT-A auto-intake should use a marker-file ready rule instead of stable two-scan fingerprint.

### Next recommended task

Add a small Settings/Intake admin action for explicit bootstrap and unpause guidance, or add marker-file/DONE-file ready rules before enabling production-like continuous auto intake.

### Rollback notes

Revert T103 files and recreate backend, airflow-scheduler, airflow-worker, and frontend. Do not delete Postgres, Docker volumes, `shared/runs`, or NIPT/PGT-A source data. If needed, keep `bio_intake_scan` paused and stop using `/api/intake/scan-and-submit`; existing `intake_discovery` rows are passive state and do not trigger work unless the endpoint/DAG is called.

## 2026-07-08 13:15 - Codex - T102 Airflow + Snakemake progress observability

### Goal

Expose real "where is the analysis now" progress for Dashboard and Run Detail by combining Airflow task instances with PGT-A/NIPT Docker runner events.

### Completed

- Added backend `GET /api/runs/{analysis_id}/progress`.
- Added `AirflowClient.list_task_instances()` for Airflow REST `/taskInstances`; no Airflow metadata DB reads.
- Added progress calculation for created/submitted/running/success/failed using PGT-A and NIPT Docker task weights.
- Added JSONL + backend POST runner event helper in `dags/common/progress_events.py`.
- Added PGT-A target-level progress events and Snakemake stdout/stderr parsing while preserving resume/preflight/no-`--forceall` behavior.
- Added NIPT Docker `nipt_mount_smoke` events and full-run stdout/stderr rule parsing path.
- Added terminal `sync-airflow` JSONL fallback import.
- Updated Dashboard and Run Detail to use `/progress`; Run Detail Workflow tab now shows `Airflow tasks` and `Pipeline steps`.
- Deployed backend, Airflow API/scheduler/worker, and frontend on `fengxian`.
- Verified light PGT-A metadata and NIPT Docker mount-smoke progress smokes.

### Changed files

- `backend/app/airflow_client.py`
- `backend/app/diagnostics_service.py`
- `backend/app/main.py`
- `backend/app/progress_service.py`
- `backend/app/rule_event_service.py`
- `backend/app/run_service.py`
- `backend/tests/test_airflow_client.py`
- `backend/tests/test_run_progress.py`
- `dags/common/progress_events.py`
- `dags/nipt_docker_runner.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_nipt_docker_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `dags/tests/test_progress_events.py`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/components/RunTracker.tsx`
- `frontend/src/lib/runProgress.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/styles.css`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/09_NIPT_DOCKER_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/progress/T102-airflow-snakemake-progress` | success | Created local T102 branch in `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign` |
| `git diff --check` | success | Local and remote checks passed |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose rendered cleanly |
| `docker build -t airflow-demo/backend:t102-test -f backend/Dockerfile backend && docker run --rm airflow-demo/backend:t102-test pytest -q tests/test_airflow_client.py tests/test_run_progress.py tests/test_snakemake_events_api.py tests/test_nipt_docker_lifecycle.py tests/test_run_diagnostics.py` | success | 29 backend tests passed |
| `docker compose -f docker-compose.yaml build airflow-worker` plus Airflow unittest container | success | 35 DAG/runner tests OK |
| `docker build --target test -f frontend/Dockerfile frontend` | success | 10 Vitest tests passed |
| `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend` | success | Frontend production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-api-server airflow-scheduler airflow-worker frontend` | success | Did not touch Postgres/Redis/volumes |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `curl -fsS http://127.0.0.1:8000/api/health` and `/api/health/airflow` | success | Backend ok; Airflow scheduler/metadatabase healthy |
| `airflow dags list-import-errors` | success | `No data found` |
| `GET /api/runs/PGTA_20260706_162150_00C4FD/progress` | success | Historical PGT-A returned Airflow task timeline, `percent=100`, empty historical rule events |
| `GET /api/runs/NIPT_20260708_033450_8362A0/progress` | success | Historical NIPT returned Airflow task timeline, `percent=100`, empty historical rule events |
| PGT-A metadata smoke `PGTA_20260708_050811_A24E36` | success | `/progress` showed Airflow tasks plus `metadata=success` pipeline event |
| NIPT Docker mount smoke `NIPT_20260708_050843_B3B05E` | success | `/progress` showed Airflow tasks plus `nipt_mount_smoke=success` pipeline event |

### Tests

- Backend targeted tests: 29 passed.
- Airflow DAG/runner tests: 35 passed.
- Frontend Docker test target: 10 tests passed.
- Production build/deploy and runtime health checks passed on `fengxian`.
- Light PGT-A metadata and NIPT Docker mount-smoke progress smokes passed.

### Not run / why

- NIPT `full_run` was not run because it is a heavy batch and remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- PGT-A `baseline_qc` was not run because the T102 acceptance only needed a light metadata progress smoke.
- `npm run lint` was not run because `frontend/package.json` has no lint script.
- Local Node/npm/Docker/Python runtime checks were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`; local Windows lacks Node/npm and uses the Windows Store Python placeholder.

### Current git status

Local worktree has T101/T102 changes pending on `codex/progress/T102-airflow-snakemake-progress`. Remote `/home/jiucheng/project/airflow-demo` has the same source overlay deployed for runtime validation.

### Risks

- Historical runs before T102 cannot reconstruct missing Snakemake/runner events; they still show Airflow task-instance progress.
- Airflow worker retains Docker socket access for NIPT Docker from T101.
- NIPT `full_run` has code-level parsing support but no heavy runtime acceptance in T102.

### Open questions

- Whether to approve and schedule a supervised NIPT Docker `full_run`.
- Whether to add a future Airflow task log endpoint for per-task stdout/stderr inside the same progress panel.

### Next recommended task

Add a small UI affordance on Dashboard/Run Detail to distinguish Airflow task progress from pipeline rule progress, then consider a supervised NIPT `full_run` only if demo needs it.

### Rollback notes

Revert T102 files and recreate backend, Airflow API/scheduler/worker, and frontend. Do not delete `shared/runs`, Postgres volumes, or Docker volumes. Existing T102 smoke runs can remain in history as small metadata/mount-smoke runs.

## 2026-07-08 11:35 - Codex - T101 NIPT Docker template-run deployment

### Goal

Deploy the Dockerized NIPT workflow as the second runnable demo pipeline beside PGT-A, while keeping WES qsub, NIPT qsub, WGS, and mail notification out of the current frontend surface.

### Completed

- Added backend `pipeline=nipt_docker` create support with `template_id=run1|run2`, `run_mode=mount_smoke|full_run`, `cores`, `project_name`, and `note`.
- Added submit support for `nipt_docker` to trigger Airflow DAG `bio_nipt_docker`.
- Added `bio_nipt_docker` DAG and repo-owned `nipt_docker_runner.py`.
- Runner validates request, writes run-local config/compose/request artifacts, executes host Docker with a unique container name, writes stdout/stderr/command logs, and writes NIPT QC summary.
- Kept `full_run` guarded by `NIPT_ALLOW_HEAVY_RUN=false`; acceptance used `mount_smoke`.
- Added NIPT QC parser/import and pipeline-filtered artifacts.
- Added Airflow worker NIPT bundle mount, Docker socket mount, and `group_add=${DOCKER_SOCKET_GID:-114}` for socket access on `fengxian`.
- Updated frontend Dashboard/Submit/Runs/Samples/Workflows/Failures to expose PGT-A and NIPT Docker only.
- Deployed backend, Airflow API/scheduler/worker, and frontend on `fengxian`.
- Verified final smoke `NIPT_20260708_033450_8362A0` reached Airflow/backend success.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/app/qc_service.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_nipt_docker_lifecycle.py`
- `dags/bio_nipt_docker.py`
- `dags/nipt_docker_runner.py`
- `dags/tests/test_bio_nipt_docker_dag.py`
- `dags/tests/test_nipt_docker_runner.py`
- `frontend/src/api.ts`
- `frontend/src/App.test.tsx`
- `frontend/src/layout/AppShell.tsx`
- `frontend/src/mocks/platform.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/SubmitPage.tsx`
- `frontend/src/pages/RunsPage.tsx`
- `frontend/src/pages/SamplesPage.tsx`
- `frontend/src/pages/FailuresPage.tsx`
- `frontend/src/pages/WorkflowsPage.tsx`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/09_NIPT_DOCKER_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/nipt/T101-nipt-docker-demo` | success | Created local T101 branch in `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Re-run after NIPT env/socket changes |
| `git diff --check` local and remote | success | No whitespace errors |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 9 Vitest tests passed |
| `docker build -t airflow-demo/backend:t101-test -f backend/Dockerfile backend && docker run --rm airflow-demo/backend:t101-test pytest -q tests/test_nipt_docker_lifecycle.py tests/test_run_creation.py tests/test_run_submit.py tests/test_run_diagnostics.py` | success | 31 backend tests passed |
| `docker run --rm --entrypoint /usr/local/bin/python -v /home/jiucheng/project/airflow-demo/dags:/opt/airflow/dags:ro -w /opt/airflow airflow-demo/airflow:t101-test -m unittest /opt/airflow/dags/tests/test_bio_nipt_docker_dag.py /opt/airflow/dags/tests/test_nipt_docker_runner.py -v` | success | 9 NIPT DAG/runner tests passed |
| `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend` | success | Frontend production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-api-server airflow-scheduler airflow-worker frontend` | success | Did not touch Postgres/Redis/volumes |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `curl -fsS http://127.0.0.1:8000/api/health` and `/api/health/airflow` | success | Backend ok; Airflow scheduler/metadatabase healthy after API readiness |
| `airflow dags list-import-errors` | success | `No data found` |
| `airflow dags list | grep bio_nipt_docker` | success | DAG visible |
| First NIPT smoke `NIPT_20260708_032949_C7F56B` | failed as expected after diagnosis | Docker socket permission denied before worker `group_add` fix |
| `stat -c '%a %u %g %U %G %n' /var/run/docker.sock` | success | Host socket group id is `114` |
| `docker compose up -d --no-deps --force-recreate airflow-worker` after `group_add` | success | Worker `id` shows groups `0(root),114` |
| Final NIPT smoke `NIPT_20260708_033450_8362A0` | success | Airflow/backend success, QC pass 96, artifacts correct |

### Tests

- Frontend Docker test target: 9 tests passed.
- Backend targeted tests: 31 passed; after artifact/QC refinement, 17 targeted tests passed.
- NIPT DAG/runner tests: 9 passed.
- Compose config and production builds passed.
- Runtime smoke passed on `fengxian` with `NIPT_20260708_033450_8362A0`.

### Not run / why

- NIPT `full_run` was not run because it is a heavy 40-core batch and remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- `npm run lint` was not run because `frontend/package.json` has no lint script.
- Local Node/npm/Docker/Python runtime checks were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`.
- Mail notification, WES qsub frontend restore, NIPT qsub, and WGS were not in scope.

### Current git status

Local worktree has T101 changes pending on `codex/nipt/T101-nipt-docker-demo`. Remote `/home/jiucheng/project/airflow-demo` has the same file overlay deployed for runtime validation, but remains on its existing branch name.

### Risks

- Airflow worker now has Docker socket access for NIPT Docker; this is limited to worker only, but it is still privileged host Docker access.
- The failed permission smoke `NIPT_20260708_032949_C7F56B` remains visible in history.
- `full_run` path is code-level integrated but not runtime-accepted in this task.
- Frontend progress remains an estimate, not authoritative Airflow task-instance progress.

### Open questions

- Whether to run a supervised `full_run` with `NIPT_ALLOW_HEAVY_RUN=true` and what resource/time window to reserve.

### Next recommended task

Add a backend Airflow task-instance/progress endpoint for Dashboard/Run Detail, then optionally schedule a separately approved NIPT Docker full-run acceptance.

### Rollback notes

To rollback the NIPT deployment surface, revert T101 files and recreate backend/airflow-worker/airflow-scheduler/airflow-api-server/frontend. Do not delete `shared/runs/NIPT_*`, Postgres volumes, or Docker volumes. Remove the worker Docker socket mount/group only by reverting `docker-compose.yaml` and recreating `airflow-worker`.

## 2026-07-08 09:38 - Codex - T100 PGT-A submit/Airflow status auto-sync

### Goal

Fix the user-reported PGT-A behavior where a project was created and submitted, but the frontend/backend stayed at `submitted`, making it look like Airflow had not entered the workflow.

### Completed

- Investigated the latest stuck run `PGTA_20260708_012630_352915`.
- Confirmed the run had a backend `dag_run_id=manual__PGTA_20260708_012630_352915` and backend `status=submitted`.
- Confirmed Airflow had actually completed that DAG run with `state=success`; the problem was missing frontend/backend reconciliation, not a missing Airflow handoff.
- Safely reconciled the stuck run by calling backend `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow`; no workflow rerun was submitted.
- Updated Dashboard so active/submitted PGT-A tracker rows call `sync-airflow` immediately and every 15 seconds, then reload tracker data.
- Updated Submit Task so primary `Create and submit to Airflow` calls `sync-airflow` after a successful submit handoff with `dag_run_id`, retrying briefly so fast runs can surface terminal backend status in the handoff summary.
- Added/updated frontend tests for Dashboard active auto-sync and Submit create+submit+sync handoff.
- Rebuilt and redeployed only the frontend container on `fengxian`.
- Updated frontend spec, task state, current state, handoff, and manifest timestamp.

### Changed files

- `frontend/src/App.test.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/SubmitPage.tsx`
- `docs/06_FRONTEND_SPEC.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `GET /api/runs?pipeline=pgta&status=submitted&limit=20&offset=0` on `fengxian` | success | Found user-visible stuck run `PGTA_20260708_012630_352915` before manual sync |
| `GET /api/runs/PGTA_20260708_012630_352915` on `fengxian` | success | Backend showed `status=submitted`, non-null `dag_run_id`, null start/end |
| Airflow CLI DAG-run query on `fengxian` | success | Same DAG run was `success`, with start and end timestamps |
| `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow` on `fengxian` | success | Reconciled backend status to `success`; no new run created |
| remote red frontend test target before implementation | failed as expected | Dashboard and Submit did not call `sync-airflow` |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 7 Vitest tests passed after implementation |
| `docker run --rm <frontend-test-image> npm test -- --run` on `fengxian` | success | Fresh verification after state-doc update: `1 test file`, `7 tests passed` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose rendered cleanly |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | Production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` on `fengxian` | success | Recreated only the frontend container |
| `curl -fsSI http://127.0.0.1:12959/` on `fengxian` | success | HTTP 200 from nginx |
| `GET /api/health` and `GET /api/health/airflow` on `fengxian` | success | Backend ok; Airflow metadatabase and scheduler healthy |
| `GET /api/runs/PGTA_20260708_012630_352915` after sync | success | Returned `status=success`, `dag_run_id`, and Airflow start/end timestamps |
| `GET /api/runs?pipeline=pgta&status=submitted&limit=20&offset=0` after sync | success | Returned no stuck submitted PGT-A runs |

### Tests

- Remote frontend Docker test target passed: `1 test file`, `7 tests`.
- Frontend production build passed through Compose: `tsc -b && vite build`.
- Runtime spot checks passed for frontend HTTP, backend health, Airflow health, reconciled PGT-A detail, and empty submitted PGT-A list.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no `lint` script.
- Local `npm`, `node`, and `docker` were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`.
- No new heavy `baseline_qc` workflow was submitted; the stuck run was reconciled by `sync-airflow` only.
- Backend, DAG, Snakemake, WES qsub, NIPT/WGS, and mail notification code were not changed.

### Current git status

Local worktree has T099/T100 changes pending commit on `codex/frontend/T099-pgta-run-tracker`. The remote service has been updated by syncing frontend source files to `/home/jiucheng/project/airflow-demo` and rebuilding/recreating the frontend container.

### Risks

- Dashboard progress remains an estimate from run status and rule events; authoritative task-level progress still needs a backend Airflow task-instance endpoint.
- Submit's post-handoff sync has a short retry window. Long-running baseline runs will still show active status until Dashboard polling observes terminal state.
- The frontend now masks this specific stale-submitted symptom, but the backend could still benefit from server-side reconciliation after `/actions/submit`.

### Open questions

- Whether to add backend-side sync immediately after submit as a stronger guarantee, or keep this frontend-only reconciliation for the current demo.

### Next recommended task

Add Airflow task-attempt history and authoritative task progress to Run Detail/Dashboard, or implement backend-side post-submit reconciliation. Keep mail notification paused unless the user reopens T034/T063.

### Rollback notes

Revert the T100 frontend changes and redeploy the previous T099 frontend image. No backend migration, Airflow DAG change, shared run directory change, or Docker volume rollback is required.

## 2026-07-08 07:46 - Codex - T099 PGT-A Dashboard run tracker and submit handoff

### Goal

Make the PGT-A-only Dashboard understandable as a project/run tracker and make Submit Task expose whether a run was only created in biodemo or actually handed off to Airflow.

### Completed

- Replaced the Dashboard split `Recent failed runs` / `Recent completed runs` layout with one large `PGT-A Run Tracker`.
- Added tracker ordering for active, failed/QC failed, created-only, and recent success PGT-A runs.
- Added tracker filters: All, Running, Submitted / queued, Created only, Failed, QC failed, Success.
- Added row-level progress estimate, progress bar, current step, project-name display, and View/Submit/Sync actions.
- Moved Service health, PGT-A resource overview, and PGT-A workflow into three equal bottom panels.
- Changed Submit Task primary action to `Create and submit to Airflow`; it now creates the backend run, submits to Airflow, fetches detail, and displays `dag_run_id`.
- Kept `Create only` as a secondary action and made the "not visible in Airflow until submitted" state explicit.
- Reworked scan results into a folder-first view with expandable FASTQ file names and hidden absolute paths.
- Updated frontend spec, task state, current state, handoff, and manifest.

### Changed files

- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/lib/runProgress.ts`
- `frontend/src/components/RunProgressBar.tsx`
- `frontend/src/components/RunTracker.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/SubmitPage.tsx`
- `frontend/src/styles.css`
- `docs/06_FRONTEND_SPEC.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git rev-parse --git-dir`, `git rev-parse --git-common-dir`, `git branch --show-current` | success | Confirmed worktree branch `codex/frontend/T099-pgta-run-tracker` under `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign` |
| remote red frontend test target before implementation | failed as expected | Existing UI lacked `PGT-A Run Tracker`, folder scan, and create+submit handoff behavior |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 7 Vitest tests passed after implementation |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose rendered cleanly |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | Production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` on `fengxian` | success | Recreated only the frontend container |
| `curl -fsSI http://127.0.0.1:12959/` on `fengxian` | success | HTTP 200 from nginx |
| `GET /api/health` and `GET /api/health/airflow` on `fengxian` | success | Backend ok; Airflow metadatabase and scheduler healthy |
| `GET /api/runs?pipeline=pgta&limit=20&offset=0` on `fengxian` | success | Returned 19 total PGT-A runs and included the two July 7 submitted runs |
| `GET /api/runs/PGTA_20260707_182024_8CA2A0` and `GET /api/runs/PGTA_20260707_182056_39A374` | success | Both returned non-null `dag_run_id` and `status=success` |
| deployed bundle grep for `PGT-A Run Tracker` | success | Confirms deployed frontend contains the new Dashboard tracker UI |

### Tests

- Remote frontend Docker test target passed: `1 test file`, `7 tests`.
- Frontend production build passed through Compose: `tsc -b && vite build`.
- Runtime spot checks passed for frontend HTTP, backend health, Airflow health, PGT-A run list, PGT-A detail handoff, and existing baseline QC evidence.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no `lint` script.
- Local `npm`, `node`, and `docker` were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`.
- No new PGT-A workflow was submitted during acceptance; this task used existing runs and UI tests to avoid a heavy `baseline_qc` run.
- Backend, DAG, Snakemake, WES qsub, NIPT/WGS, and mail notification code were not changed.

### Current git status

Local worktree has T099 changes pending commit on `codex/frontend/T099-pgta-run-tracker`. The remote service has been updated by syncing frontend source files to `/home/jiucheng/project/airflow-demo` and rebuilding/recreating the frontend container.

### Risks

- Dashboard progress is an estimate from run status and rule events; true Airflow task progress still needs a backend task-instance endpoint.
- `/api/runs` is analysis-run centric, not raw Airflow DAG-run centric. Resume history still appears as one analysis with the latest `dag_run_id`.
- The two July 7 PGT-A metadata runs are `success` with `qc_status=unknown`; they prove handoff/status flow, not baseline QC.

### Open questions

- Whether to add a backend endpoint for Airflow task instances so Dashboard progress can become authoritative rather than estimated.

### Next recommended task

Add Airflow task-attempt history and real task progress to Run Detail/Dashboard, or continue with T082 rollback/cleanup runbook. Keep mail notification paused unless the user reopens T034/T063.

### Rollback notes

Revert the T099 frontend files and redeploy the previous frontend image. No backend migration, Airflow DAG change, shared run directory change, or Docker volume rollback is required.

## 2026-07-08 02:18 - Codex - T098 PGT-A frontend/Airflow data reconciliation

### Goal

Resolve the apparent frontend/Airflow data mismatch in the PGT-A-only demo without exposing WES/NIPT/WGS or adding mail notification work.

### Completed

- Confirmed the frontend data path is `React -> FastAPI -> Airflow REST API + biodemo DB`; the frontend does not connect directly to Airflow metadata DB.
- Found one real mismatch: `/api/runs` hard-coded `qc_status=unknown`, while `PGTA_20260706_162150_00C4FD/qc` already reported 14 failed PGT-A baseline QC metrics.
- Fixed `/api/runs` to aggregate run-level QC from sample `qc_status` with priority `fail > warn > unknown > pass`.
- Restored active PGT-A Run Detail auto-sync: if the selected PGT-A run has a `dag_run_id` and active status, the page calls backend `sync-airflow` immediately and every 15 seconds until terminal state.
- Rebuilt and redeployed only backend/frontend on `fengxian`.
- Verified `PGTA_20260706_162150_00C4FD` is reconciled: frontend/backend list and detail show workflow `success`, run/sample QC `fail`; latest matching Airflow DAG run is `success`.

### Changed files

- `backend/app/run_service.py`
- `backend/tests/test_run_creation.py`
- `frontend/src/App.test.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| red backend targeted test in temporary clone | failed as expected | `qc_status` was `unknown` instead of expected `fail` |
| red frontend Docker test target in temporary clone | failed as expected | active PGT-A detail did not call `/actions/sync-airflow` |
| green targeted backend test in temporary clone | success | new QC aggregation test passed |
| green frontend Docker test target in temporary clone | success | 6 Vitest tests passed |
| temporary-clone full backend pytest | success | 53 passed |
| temporary-clone frontend production build | success | `tsc -b && vite build` passed |
| `git push -u origin codex/frontend/T098-airflow-data-reconcile` | success | pushed commit `f64e0d2` |
| remote mirror checkout/pull | success | `/home/jiucheng/project/airflow-demo` at `f64e0d2` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | compose config valid |
| `docker run --rm airflow-demo/backend:t098-test pytest -q` on `fengxian` | success | 53 passed |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | cache-hit test target for 6 Vitest tests |
| `docker compose -f docker-compose.yaml build backend frontend` on `fengxian` | success | backend built; frontend build passed `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend` on `fengxian` | success | recreated only backend/frontend; no volumes deleted |
| HTTP/API/Airflow spot check on `fengxian` | success | frontend HTTP 200; backend health ok; Airflow healthy; target PGT-A list/detail/QC/Airflow state reconciled |

### Tests

- Backend full pytest passed remotely: 53 tests.
- Frontend Docker test target passed remotely: 6 Vitest tests.
- Frontend production build passed remotely through Compose.
- Runtime spot check passed: `/api/runs?pipeline=pgta&limit=50&offset=0` returned 17 PGT-A analysis runs, and `PGTA_20260706_162150_00C4FD` now has `qc_status=fail`; Airflow `bio_pgta` has 20 DAG runs total and 5 matching that analysis because of resume history, latest matching run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` is `success`.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` still has no `lint` script.
- No new PGT-A analysis was submitted; this task only reconciled and displayed existing state.
- MailHog/SMTP notification remains out of scope by user request.
- WES qsub UI remains hidden; historical backend/DAG/Snakemake code was not deleted.

### Current git status

At handoff time, code commit `f64e0d2` is pushed and deployed. State-doc updates are pending local commit/push on the same branch.

### Risks

- Frontend analysis-run counts will still differ from raw Airflow DAG-run counts after resumes; this is expected and should be narrated clearly in demos.
- PGT-A `PGTA_20260706_162150_00C4FD` remains workflow success with QC fail, not a QC-pass biological sample.

### Open questions

- Whether the next frontend iteration should show a small "Airflow attempts/resume history" panel for PGT-A run detail to make the 1 analysis / many DAG runs relationship explicit.

### Next recommended task

Add an Airflow attempt history panel in Run Detail, or continue with `T082` rollback/cleanup runbook. Keep mail notifications paused unless the user reopens `T034/T063`.

### Rollback notes

Revert T098 commits and redeploy backend/frontend. No Airflow DAG code, database migration, shared run directory, or Docker volume rollback is required.

## 2026-07-08 01:54 - Codex - T097 PGT-A-only frontend deployment scope

### Goal

Converge the redesigned T096 frontend into a PGT-A-only deployable demo, hide WES/NIPT/WGS frontend entry points, leave historical backend/DAG/Snakemake code untouched, and verify the updated frontend service on port `12959`.

### Completed

- Sidebar now shows Dashboard, Submit Task, Runs, Samples, Failures, and Settings; Workflows is hidden from the main navigation.
- Dashboard, Runs, Samples, and Failures now display PGT-A data only.
- Submit Task now exposes only the PGT-A server-path scan/create/submit flow.
- Run Detail keeps PGT-A Overview/Samples/Workflow/QC/Logs/Files/Config tabs, sync, and baseline_qc `Resume with 64 cores`.
- Direct `/workflows` remains development-accessible but displays only the PGT-A workflow template.
- WES qsub, NIPT qsub, NIPT docker, and WGS are hidden from the current frontend demo. Existing backend/DAG/Snakemake code was not removed.
- Mail notification work was not started; `T034` and `T063` remain todo.
- Frontend container was rebuilt and recreated on `fengxian`; `http://127.0.0.1:12959/` returns HTTP 200.

### Changed files

- `docs/06_FRONTEND_SPEC.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`
- `frontend/src/App.test.tsx`
- `frontend/src/layout/AppShell.tsx`
- `frontend/src/mocks/platform.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/FailuresPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/RunsPage.tsx`
- `frontend/src/pages/SamplesPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/SubmitPage.tsx`
- `frontend/src/pages/WorkflowsPage.tsx`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git checkout -b codex/frontend/T097-pgta-only` | success | T097 branch created from T096 worktree |
| temporary-clone `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | red/green fix validation; 5 Vitest tests passed |
| temporary-clone `docker build -f frontend/Dockerfile frontend` on `fengxian` | success | production build passed `tsc -b && vite build` |
| `git push -u origin codex/frontend/T097-pgta-only` | success | branch pushed |
| remote mirror `git checkout -b codex/frontend/T097-pgta-only --track origin/codex/frontend/T097-pgta-only` | success | remote mirror at frontend code commit `3119be5` |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | cache-hit preflight before rebuild |
| `docker build --no-cache --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 1 test file, 5 tests passed |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | compose config valid |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | production build passed `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` on `fengxian` | success | recreated only frontend |
| `curl -fsSI http://127.0.0.1:12959/` on `fengxian` | success | HTTP 200 from nginx |
| PGT-A API spot checks on backend port `8000` | success | `/api/health`, `/api/health/airflow`, run detail, QC, and stderr log tail returned data |
| `git diff --check` | success | local non-runtime whitespace check passed before first commit |

### Tests

- Remote frontend Docker test target passed with `--no-cache`: `1 test file`, `5 tests`.
- Remote frontend production build passed through Compose: `tsc -b && vite build`.
- Remote frontend HTTP smoke passed on port `12959`.
- PGT-A backend/API compatibility spot checks passed for `PGTA_20260706_162150_00C4FD`, including detail, QC summary `pass=0,warn=0,fail=14,unknown=0`, and stderr log tail.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` does not define a `lint` script.
- Local `npm`, `node`, and `docker` were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`.
- No new PGT-A run was submitted; spot checks used the existing successful workflow/QC-fail demo run.
- MailHog/SMTP notification was not implemented or tested by user request.

### Current git status

Frontend code commit `3119be5` is pushed to `origin/codex/frontend/T097-pgta-only` and deployed on `fengxian`. This handoff/state/manifest sync is expected to be committed and pushed as a follow-up docs-state commit on the same branch.

### Risks

- PGT-A demo remains workflow success with QC fail for G10/G11; the UI should narrate this as workflow observability plus QC failure diagnosis, not as a QC-pass sample.
- WES qsub code remains in the repository and backend storage may still contain WES historical runs, but current frontend demo intentionally hides those surfaces.
- Direct `/workflows` still resolves for development, but only PGT-A is shown.

### Open questions

- Whether to remove or guard the direct `/workflows` route later, or keep it as a development-only page.

### Next recommended task

Keep the current demo focused on PGT-A. If future scope expands, add one deployable pipeline at a time, starting with a real acceptance plan rather than re-exposing old mock surfaces. Mail notifications remain `T034/T063`.

### Rollback notes

Revert the T097 frontend commit and redeploy the previous T096 frontend image. No backend, DAG, database, shared run directory, or Docker volume rollback is required.

## 2026-07-08 01:30 - Codex - T096 frontend platform UI redesign

### Goal

Redesign the demo frontend into a credible bioinformatics task platform prototype while preserving existing PGT-A and WES API behavior.

### Completed

- Added design/audit/spec documentation before implementation: `DESIGN.md`, `docs/frontend-design-review.md`, and `docs/frontend-spec.md`.
- Replaced the single-page workspace with `react-router-dom` routes and a persistent sidebar/topbar shell.
- Added Dashboard, Submit Task, Runs, Run Detail, Samples, Workflows, Failures, and Settings pages.
- Kept real PGT-A server-path scan/create/submit behavior and real WES mock create/submit/reanalysis behavior.
- Added clearly labeled mock/demo surfaces for NIPT qsub, NIPT docker, WGS, workflow templates, and resource usage.
- Added shared frontend components for status badges, metrics, pipeline cards, run tables, workflow timeline, log viewer, sample sheet validation, pipeline selection, error diagnosis, and QC metric display.
- Centralized status semantics in `frontend/src/lib/status.ts`, formatting helpers in `frontend/src/lib/format.ts`, and demo fixtures in `frontend/src/mocks/platform.ts`.
- Updated `docs/06_FRONTEND_SPEC.md`, `TASKS.md`, `CURRENT_STATE.md`, and `MANIFEST.json`.

### Changed files

- `DESIGN.md`
- `docs/frontend-design-review.md`
- `docs/frontend-spec.md`
- `docs/06_FRONTEND_SPEC.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/styles.css`
- `frontend/src/components/*`
- `frontend/src/layout/AppShell.tsx`
- `frontend/src/lib/*`
- `frontend/src/mocks/platform.ts`
- `frontend/src/pages/*`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git worktree add -b codex/frontend/T096-platform-ui-redesign ../airflow-demo-worktrees/T096-platform-ui-redesign` | success | isolated from dirty root worktree |
| `git status --short --branch` | success | checked local and remote mirror state |
| `ssh fengxian 'cd /home/jiucheng/project/airflow-demo && git pull --ff-only origin codex/frontend/T096-platform-ui-redesign'` | success | remote mirror fast-forwarded to frontend branch |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 7 Vitest tests passed |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | no rendered compose errors |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | ran `npm run build`, including `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` on `fengxian` | success | recreated only frontend |
| `curl -fsSI http://127.0.0.1:12959/` on `fengxian` | success | first immediate probe reset during nginx readiness; retry returned HTTP 200 |
| backend API spot checks on `http://127.0.0.1:8000/api` | success | health/db/airflow ok; PGT-A detail/samples/stderr and WES detail/rules/QC returned data |

### Tests

- Remote frontend Docker test target passed: `1 test file`, `7 tests`.
- Remote production frontend image build passed: `tsc -b && vite build`.
- Remote frontend HTTP smoke passed on port `12959`.
- Remote PGT-A/WES API compatibility spot checks passed against backend port `8000`.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` does not define a `lint` script.
- Local `npm`, `node`, and `docker` checks were not run because the Windows edit environment does not provide those binaries; runtime acceptance was performed on `ssh fengxian` per AGENTS.md.
- No new PGT-A or WES analysis run was submitted during final acceptance; existing API data was read for compatibility spot checks.

### Current git status

T096 code commits were pushed to `origin/codex/frontend/T096-platform-ui-redesign`; docs/state/manifest updates are pending final commit at this checkpoint.

### Risks

- NIPT/WGS pages are UI/mock surfaces only until backend/DAG tasks exist.
- The frontend nginx still serves only static assets; browser API calls intentionally target backend port `8000` by the existing API base logic.
- Current PGT-A demo evidence remains workflow success with QC fail for G10/G11; UI separates workflow status from QC decision.

### Open questions

- Whether to add a real reverse proxy for `/api` through frontend nginx, or keep the current explicit backend port model.
- Whether NIPT qsub/docker and WGS should be promoted from mock UI fixtures into backend/DAG tasks next.

### Next recommended task

Wire real Airflow/backend contracts for NIPT qsub, NIPT docker, and WGS, or add MailHog success/failure notification links into the redesigned Run Detail.

### Rollback notes

- Revert the T096 frontend branch commits and redeploy the previous frontend image. No database, shared run directory, or Docker volume changes are required.

## 2026-07-07 23:29 - Codex - T080/T081 demo smoke report and script

### Goal

Turn the already verified PGT-A/WES capabilities into a reproducible 10-15 minute demo script and smoke report without submitting new heavy PGT-A work.

### Completed

- Rechecked `fengxian` with read-only commands: frontend HTTP 200, backend `/api/health` ok, Airflow metadatabase and scheduler healthy.
- Verified PGT-A `PGTA_20260706_162150_00C4FD` remains workflow `success`, with G10/G11 sample workflow `success` and QC status `fail`.
- Verified PGT-A `/qc` summary is `pass=0,warn=0,fail=14,unknown=0`, and artifacts include `pgta_python_preflight`, `pgta_baseline_qc_summary`, `pgta_baseline_qc_pass_samples`, `pgta_baseline_qc_report`, and `snakemake_command`.
- Verified WES mock QC run `WES_20260705_164813_C5561C` is `success` with `/qc` summary `pass=6,warn=0,fail=0,unknown=0`.
- Verified WES rerun_rule run `WES_20260705_162041_2507AF` is `success`, has 7 rule rows, and command log contains `--forcerun fastp` without `--forceall`.
- Rewrote `docs/17_DEMO_SCRIPT.md` around the current demo truth and added `docs/21_DEMO_SMOKE_REPORT.md`.
- Updated `TASKS.md`, `CURRENT_STATE.md`, and `MANIFEST.json`.

### Changed files

- `docs/17_DEMO_SCRIPT.md`
- `docs/21_DEMO_SMOKE_REPORT.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | success | local branch clean before edits |
| read-only `fengxian` smoke script | success | no new run submitted; frontend/backend/Airflow and PGT-A/WES evidence checked |
| `curl http://127.0.0.1:12959/` on `fengxian` | HTTP 200 | frontend reachable |
| `GET /api/health` | success | backend returned `{"status":"ok"}` |
| `GET /health` on Airflow | success | metadatabase `healthy`, scheduler `healthy` |
| `GET /api/runs/PGTA_20260706_162150_00C4FD/qc` | success | `pass=0,warn=0,fail=14,unknown=0` |
| `GET /api/runs/WES_20260705_164813_C5561C/qc` | success | `pass=6,warn=0,fail=0,unknown=0` |
| command log grep for `WES_20260705_162041_2507AF` | success | contains `--forcerun fastp`; no `--forceall` |

### Tests

- Runtime validation was read-only and performed on `ssh fengxian`.
- Local static checks passed before commit: `git diff --check` had no whitespace errors, `rg` found the acceptance keywords, and `MANIFEST.json` reports `file_count=135`, `listed=135`, `missing=0`.

### Not run / why

- No backend/frontend/DAG unit tests were run because this is a docs/QA report-only update.
- No new PGT-A baseline_qc run was submitted; current evidence is from the existing successful workflow run.
- MailHog notification was not demonstrated because `T034/T063` is still todo.

### Current git status

Docs/state changes are pending commit at this checkpoint.

### Risks

- PGT-A demo should be narrated as workflow success with QC fail, not as a QC-pass biological sample.
- If a QC-pass PGT-A demo is required, do a read-only candidate data/threshold audit before another heavy baseline_qc run.

### Open questions

- None for T080/T081; QC-pass sample selection remains a future product/demo decision.

### Next recommended task

T082 rollback/cleanup runbook, or T034/T063 MailHog success/failure notification.

### Rollback notes

- Revert the docs-only T080/T081 commit to remove the new smoke report and restore the old demo script. No runtime service rollback is needed.

## 2026-07-07 23:05 - Codex - T095 PGT-A baseline QC preflight final resume

### Goal

Finish T095 by fixing the PGT-A baseline QC Python dynamic-library failure and resuming `PGTA_20260706_162150_00C4FD` in the same workdir without deleting BAM/QC/config data.

### Completed

- Confirmed the previous resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` had reached baseline QC and failed on `matplotlib` import due the system `libstdc++.so.6` lacking `CXXABI_1.3.15`.
- Added PGT-A subprocess env isolation: run-local `XDG_CACHE_HOME`, run-local `MPLCONFIGDIR`, `LD_LIBRARY_PATH=PGTA_CONDA_LIB`, and `LD_PRELOAD=PGTA_LIBSTDCXX`.
- Added `PGTA_LIBSTDCXX` to `.env.example` and Compose Airflow env.
- Added a preflight log header showing command, `LD_LIBRARY_PATH`, `LD_PRELOAD`, `MPLCONFIGDIR`, and `XDG_CACHE_HOME`.
- Deployed commit `3bd1270` to `fengxian` via `git pull --ff-only` and recreated only `airflow-scheduler` / `airflow-worker`.
- Final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` ended Airflow/backend `success`.
- Verified artifacts: `baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, `baseline_qc_report.md`, and `pgta.python_preflight.log`.
- Verified `/api/runs/PGTA_20260706_162150_00C4FD/qc`: 14 metrics imported, all `fail`; samples G10/G11 are workflow `success` with `qc_status=fail`.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | no rendered compose errors |
| `docker compose -f docker-compose.yaml exec -T airflow-worker bash -lc 'python -m unittest discover -s dags/tests -v'` | success | 47 tests OK, 5 expected logger-interface skips |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| direct worker `_run_pgta_python_preflight` in temp workdir | success | logged `matplotlib 3.10.8`, `numpy 1.26.4`, `pandas 2.2.1`, `pysam 0.23.3`, `scipy 1.16.0` |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/reanalyze` | success | created `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/sync-airflow` | success | backend status `success` |
| `GET /api/runs/PGTA_20260706_162150_00C4FD/qc` | success | `pass=0,warn=0,fail=14,unknown=0` |
| `git diff --check` | success | local non-runtime check |

### Tests

- Remote Airflow/DAG tests passed after the `LD_PRELOAD` fix.
- Runtime baseline QC final resume passed and generated terminal baseline QC artifacts.

### Not run / why

- Frontend browser click-through was not repeated; backend APIs and generated artifacts were verified, and frontend consumes the same `/qc`/artifacts endpoints.
- Backend full pytest was not rerun after the second `LD_PRELOAD` commit because no backend code changed after `966e0d8`; previous T095 backend pytest passed 52 tests.

### Current git status

Local branch `codex/airflow/T088-pgta-snakemake-cache` has state-doc updates pending after runtime success evidence.

### Risks

- Workflow success does not mean QC pass: G10/G11 baseline QC decision is `FAIL` (`median_abs_z>1.5;outlier_frac_abs_z_gt_3>0.3`).
- Do not rerun baseline_qc blindly to chase a QC pass; first audit data suitability or thresholds.

### Open questions

- Whether demo narrative should present this as "workflow success with QC fail" or whether another PGT-A input set should be selected for a QC-pass demonstration.

### Next recommended task

T080/T081: build the end-to-end smoke/demo report, explicitly separating workflow status from QC decision. If a QC-pass PGT-A demo is required, do a read-only candidate data/threshold audit first.

### Rollback notes

- To roll back T095 runtime behavior, revert commits `966e0d8`, `fd1f3cd`, and `3bd1270`, pull on `fengxian`, and recreate only Airflow scheduler/worker. Do not delete shared run directories or Docker volumes.

## 2026-07-07 21:35 - Codex - T095 PGT-A baseline QC Python library preflight

### Goal

Fix the second `PGTA_20260706_162150_00C4FD` 64-core resume failure. The T094 cleanup resume reached `baseline_bam_uniformity_qc`, but both G10/G11 rule logs failed while importing `matplotlib` because the task loaded the container system `libstdc++.so.6` without `CXXABI_1.3.15`.

### Completed

- Read-only failure check confirmed latest DAG run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` is `failed`; `run_pgta_target` failed, mapping outputs `G10/G11.sorted.bam(.bai)` exist, `/qc` is empty, and samples are `failed`.
- Added TDD red tests for PGT-A subprocess env and baseline QC preflight; red tests failed on missing `MPLCONFIGDIR`, missing conda-lib `LD_LIBRARY_PATH`, and missing preflight call.
- Updated `bio_pgta` runner env to set `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`, `MPLCONFIGDIR=<workdir>/tmp/matplotlib`, set `LD_LIBRARY_PATH` to `PGTA_CONDA_LIB`, and preload conda `libstdc++.so.6` with `LD_PRELOAD`.
- Added baseline-QC-only Python import preflight for `matplotlib/numpy/pandas/pysam/scipy`, writing `logs/pgta.python_preflight.log`.
- Added dynamic artifact discovery for `pgta_python_preflight`.
- Updated `.env.example`, Compose Airflow env, API/DAG/QC/runbook docs, `SERVER_INFO.md`, `CURRENT_STATE.md`, and `TASKS.md`.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml exec -T airflow-worker python -m unittest dags.tests.test_pgta_metadata_runner.PgtaMetadataRunnerTests -v` on `fengxian` before fix | failed as expected | 4 failures: missing matplotlib dir/env and missing preflight |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q tests/test_run_diagnostics.py::test_list_pgta_artifacts_discovers_python_preflight_log` before fix | failed as expected | `pgta_python_preflight` artifact not discovered |
| targeted Airflow runner test after fix | success | 19 tests OK |
| targeted backend artifact test after fix | success | 1 passed |
| `git diff --check` | success | local non-runtime check |

### Tests

- Red/green targeted Airflow runner tests passed after implementation.
- Red/green backend artifact test passed after implementation.

### Not run / why

- Full backend pytest, full Airflow unittest discovery, Compose config, Airflow import check, and runtime resume are pending after commit/push and clean remote mirror sync.
- Frontend tests not run; no frontend code changed.

### Current git status

Local branch `codex/airflow/T088-pgta-snakemake-cache` has uncommitted T095 changes at this checkpoint.

### Risks

- The next same-workdir resume is a real PGT-A baseline QC run; it may still be long-running or fail later inside QC logic after the Python library path issue is fixed.
- Do not delete existing `mapping/*.sorted.bam(.bai)` outputs or the shared run directory.

### Open questions

- None for the library path fix.

### Next recommended task

Commit/push T095, cleanly fast-forward `fengxian`, rebuild/recreate Airflow scheduler/worker, verify preflight import in worker, then resume `PGTA_20260706_162150_00C4FD` once.

### Rollback notes

- Revert the T095 commit to remove the env/preflight behavior and rebuild/recreate Airflow scheduler/worker if needed.
- Do not use `docker compose down -v`, Docker prune commands, destructive Git commands, or broad file deletion.

## 2026-07-07 20:14 - Codex - T094 PGT-A resume temp BAM cleanup and retry

### Goal

Fix the failed PGT-A `baseline_qc` resume for `PGTA_20260706_162150_00C4FD` where interrupted `samtools sort` temp BAMs caused `File exists`, then safely trigger another same-workdir 64-core resume.

### Completed

- Added red tests first for PGT-A resume cleanup and backend artifact discovery; both failed at the expected missing behavior.
- Added `bio_pgta` resume cleanup after successful Snakemake `--unlock` and before the main resume command.
- Cleanup scope is limited to current `workdir/mapping/*.sorted.bam.tmp.*.bam`; it refuses non run-local workdirs and does not touch final BAM/BAI, FASTQ, QC, logs, config, PGT-A source, or rawdata.
- Wrote cleanup audit artifact `logs/pgta.resume.cleanup.tsv`.
- Added `pgta_resume_cleanup` to dynamic artifact discovery.
- Updated API contract, DAG spec, QC/logging docs, and deployment runbook.
- Rebuilt backend, recreated backend plus Airflow scheduler/worker only; did not touch Postgres/Redis/frontend and did not delete volumes.
- Confirmed before retry: no matching `PGTA_20260706_162150_00C4FD` process was running and 16 stale `G11.sorted.bam.tmp.*.bam` files existed.
- Triggered new resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z`.
- Verified cleanup log records all 16 deleted tmp BAMs, remaining tmp count is 0, command contains `--cores 64 --rerun-incomplete`, and no `--forceall`.
- Explicit `sync-airflow` now shows backend status `running`; active worker process shows G11 running with `fastp -w 16`.

### Changed files

- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git diff --check` | success | local non-runtime static check |
| red Airflow test on `fengxian` | failed as expected | tmp files remained before implementation |
| red backend artifact test on `fengxian` | failed as expected | `pgta_resume_cleanup` not discovered before implementation |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | compose config valid |
| targeted Airflow runner test on `fengxian` | success | new cleanup test passed |
| `docker compose -f docker-compose.yaml build backend && docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 51 passed |
| Airflow unittest discover on `fengxian` | success | 44 tests OK, 5 skipped logger interface unavailable in that Python env |
| `airflow dags list-import-errors` | success | `No data found` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-scheduler airflow-worker` | success | no volumes deleted; Postgres/Redis/frontend left running |
| pre-resume tmp/process checks | success | 16 stale temp BAMs, no matching running processes |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/reanalyze` | success | returned new run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` |
| cleanup/command/artifact checks | success | cleanup log has 16 rows; temp count 0; command has `--cores 64 --rerun-incomplete`; artifact API includes `pgta_resume_cleanup` |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/sync-airflow` | success | backend status `running`, `error_summary=null` for latest DAG run |

### Tests

- Remote backend full pytest passed: 51 passed.
- Remote Airflow DAG unittest discover passed: 44 OK, 5 skipped for logger-interface availability in that Python env.
- Airflow import check passed: `No data found`.
- Runtime cleanup evidence passed: 16 stale temp BAMs were recorded and deleted; remaining tmp count is 0.

### Not run / why

- Did not wait for terminal baseline QC success/failure; the real PGT-A resume is still running.
- Did not run frontend tests; no frontend files changed.
- Did not stop frontend/Postgres/Redis or delete any volume.
- Did not submit a new heavy PGT-A run; only resumed the existing failed workdir.

### Current git status

Code commits `1ce3fa6` and `0a8e756` are pushed to `origin/codex/airflow/T088-pgta-snakemake-cache`. This handoff/status update records runtime evidence after `0a8e756`.

### Risks

- The latest resume is a real baseline QC workload and may still take time. Do not interrupt it unless the user explicitly asks.
- If the latest resume fails, sync Airflow first and inspect `error_summary`, `snakemake.stderr.log`, and rule logs before deciding on another resume.
- The cleanup intentionally deletes only matching samtools sort temp BAMs; do not broaden the pattern without another explicit review.

### Open questions

- None for T094 code. Runtime terminal success/failure remains pending.

### Next recommended task

Continue observing `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z`. If it succeeds, call `sync-airflow` and verify `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, `baseline_qc_report.md`, `/api/runs/{analysis_id}/qc`, artifacts, and frontend QC panel. If it fails, call `sync-airflow`, record `error_summary` and stderr/rule logs, then decide whether another fix is warranted.

### Rollback notes

- Revert commit `0a8e756` to remove cleanup behavior and rebuild/redeploy backend plus recreate Airflow scheduler/worker if needed.
- Do not delete `shared/runs/PGTA_20260706_162150_00C4FD`; it contains the active resumed workdir and logs.
- Do not use `docker compose down -v`, Docker prune commands, destructive Git commands, or broad file deletion.

## 2026-07-07 18:08 - Codex - T093 PGT-A controlled interrupt and 64-core resume

### Goal

Implement and validate a safe resume path for the long-running PGT-A `baseline_qc` run `PGTA_20260706_162150_00C4FD`: add backend/API, Airflow, and frontend support for same-workdir PGT-A resume, then perform one controlled interruption of the old `--cores 1` run and resume it with `--cores 64 --rerun-incomplete`.

### Completed

- Added PGT-A `POST /api/runs/{analysis_id}/actions/reanalyze` support for `pipeline=pgta,target=baseline_qc,mode=resume`.
- Guardrails: PGT-A resume is allowed only for terminal failed/terminated runs; active running/submitted/queued runs, non-`baseline_qc` targets, `rerun_rule`, `clone_new`, rule/sample selectors, and `forceall` are rejected.
- Extended `bio_pgta` resume mode: first runs Snakemake `--unlock`, then runs the main command with `--cores ${PGTA_SNAKEMAKE_CORES:-64} --rerun-incomplete`; no `--forceall`.
- Added command artifacts: `logs/snakemake.unlock.command.txt`, unlock stdout/stderr logs, and updated `logs/snakemake.command.txt`.
- Added frontend `Resume with 64 cores` button for failed/terminated PGT-A `baseline_qc` runs only.
- Deployed backend/frontend and recreated Airflow scheduler/worker after the old run had failed, so the resume run used fresh code.
- Controlled-interrupted only exact matching processes for `PGTA_20260706_162150_00C4FD`; did not touch unrelated host processes.
- Synced the old DAG run to backend `failed`; `error_summary` captured Snakemake interruption and failed `fastp_bwa` context.
- Submitted resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z`.
- Verified resume command artifacts:
  - `snakemake.unlock.command.txt` contains `--cores 64 ... --unlock`.
  - `snakemake.command.txt` contains `--cores 64 ... --rerun-incomplete`.
  - `snakemake.command.txt` does not contain `--forceall`.
- Fresh status at 2026-07-07 18:09 CST: resume DAG run is still `running`, `run_pgta_target=running`; active rule processes show `bwa mem -t 16` and `samtools sort -@ 16`; no `qc/baseline` terminal artifacts yet.

### Changed files

- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/tests/test_pgta_reanalysis.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | success | branch `codex/airflow/T088-pgta-snakemake-cache` |
| red backend/DAG/frontend tests on `fengxian` | failed as expected | backend endpoint only supported WES; DAG had no PGT-A resume/unlock; frontend lacked PGT-A resume button |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | compose config valid |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q tests/test_pgta_reanalysis.py tests/test_wes_run_lifecycle.py` | success | 7 passed |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 50 passed |
| Airflow image unittest discover on `fengxian` | success | 43 tests OK, 5 skipped logger interface unavailable in that Python env |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 17 Vitest tests passed |
| `airflow dags list-import-errors` on `fengxian` | success | `No data found` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend` | success | backend/frontend redeployed, no volumes deleted |
| `kill -TERM <snakemake pid>` then targeted child TERM if needed | success | only exact `PGTA_20260706_162150_00C4FD` processes were targeted |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/sync-airflow` | success | old run became backend `failed`, samples failed, `error_summary` non-null |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/reanalyze` | success | returned `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z`, status `submitted` |
| final read-only monitor at 18:09 CST | success | resume run still `running`; command has 64 cores/rerun-incomplete; G11 BWA/Samtools active; no baseline QC files yet |

### Tests

- Remote backend full pytest passed: 50 passed.
- Remote Airflow DAG unittest discover passed: 43 OK, 5 skipped for logger-interface availability in that Python env.
- Remote frontend Docker test target passed: 17 Vitest tests.
- Airflow import check passed: `No data found`.
- Runtime command evidence passed: `--unlock`, `--cores 64`, `--rerun-incomplete`, and no `--forceall`.

### Not run / why

- Did not call final `sync-airflow` for the resume DAG run because it is still running.
- Did not verify `baseline_qc_summary.tsv`, `/qc`, or frontend QC panel because `qc/baseline` outputs do not exist yet.
- Did not submit any additional heavy PGT-A run.
- Did not use `docker compose down -v`, `docker system prune`, or `docker volume prune`.

### Current git status

Code commits `6f9d617` and `2821a5e` are pushed to `origin/codex/airflow/T088-pgta-snakemake-cache`. This handoff/status update records runtime evidence after `2821a5e`.

### Risks

- The resumed baseline QC is still a real mapping/QC workload and may run for a while. Do not interrupt it again unless the user explicitly asks.
- Backend status may remain `submitted/running` until the frontend auto-sync or manual `sync-airflow` runs; the terminal truth is Airflow.
- If the resume run fails, sync first and inspect `error_summary`, `snakemake.stderr.log`, and rule logs before deciding on another action.

### Open questions

- None for code capability. Runtime success/failure of the resumed baseline QC is still pending.

### Next recommended task

Continue monitoring `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z`. If it reaches `success`, call `sync-airflow` and verify `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, `baseline_qc_report.md`, `/api/runs/{analysis_id}/qc`, artifacts, and frontend QC panel. If it reaches `failed`, call `sync-airflow`, record `error_summary` and stderr/rule logs, then decide whether another resume is warranted.

### Rollback notes

- Revert commit `2821a5e` to remove PGT-A resume support and rebuild/redeploy backend/frontend/Airflow images if needed.
- Do not delete `shared/runs/PGTA_20260706_162150_00C4FD`; it contains the current resumed workdir and logs.
- Use only safe service stops/recreates; never use `down -v`, Docker prune commands, or destructive Git commands.

## 2026-07-07 14:13 - Codex - T092 PGT-A baseline_qc current run monitor

### Goal

Safely monitor and record the current real PGT-A `baseline_qc` run `PGTA_20260706_162150_00C4FD` without stopping, restarting, retrying, or submitting another heavy run. If the run had reached terminal state, sync Airflow and verify QC/artifacts; otherwise leave clear evidence and next steps.

### Completed

- Confirmed `fengxian` services are running and `docker compose -f docker-compose.yaml config --quiet` still passes.
- Confirmed Airflow `bio_pgta` run `manual__PGTA_20260706_162150_00C4FD` is still `running` as of 2026-07-07 14:11 CST.
- Confirmed Airflow task states: `validate_request=success`, `prepare_pgta_config=success`, `run_pgta_target=running`, `collect_pgta_artifact=None`.
- Confirmed backend run detail still reports `status=running`, `target=baseline_qc`, `selected_count=2`, and samples `G10/G11` both `running`.
- Confirmed this historical run still uses `--cores 1` in `logs/snakemake.command.txt`; it started before T091 and cannot prove the new 64-core default.
- Confirmed G10 mapping completed; `logs/bwa/G10.log` reports BWA real time `33885.400 sec`.
- Confirmed G11 BWA is still progressing; `logs/bwa/G11.log` and `mapping/G11.sorted.bam.tmp.*` files are updating.
- Confirmed no terminal baseline QC outputs exist yet: no `qc/baseline` files, `/qc` returns zero metrics, and artifacts currently only include command/config files.
- Did not call `sync-airflow`, because Airflow has not reached `success` or `failed`.
- Did not stop, restart, clear, retry, resume, or submit any PGT-A run.

### Changed files

- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | success | local branch `codex/airflow/T088-pgta-snakemake-cache` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | no compose errors |
| `docker compose -f docker-compose.yaml ps` on `fengxian` | success | backend/frontend/Airflow/Postgres/Redis running |
| `airflow dags list-runs -d bio_pgta --output table` on `fengxian` | success | `PGTA_20260706_162150_00C4FD` still `running` |
| `curl http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD` | success | backend status `running`, target `baseline_qc` |
| `curl http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD/samples` | success | `G10/G11` sample status `running` |
| `curl http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD/qc` | success | `pass=0,warn=0,fail=0,unknown=0` because QC output has not been generated |
| `curl http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD/artifacts` | success | currently command/config artifacts only |
| `airflow tasks states-for-dag-run bio_pgta manual__PGTA_20260706_162150_00C4FD` | success | `run_pgta_target` running, collect task not started |
| `cat shared/runs/PGTA_20260706_162150_00C4FD/logs/snakemake.command.txt` | success | command contains `--cores 1` |
| `tail shared/runs/PGTA_20260706_162150_00C4FD/logs/bwa/G11.log` | success | BWA progress lines still updating |

### Tests

- This task is a live-run monitor/status update, not a code change.
- Remote-only runtime checks above were run on `ssh fengxian`.
- No local Docker/Python/Snakemake/Airflow tests were run or used as acceptance evidence.

### Not run / why

- `sync-airflow` was not run because the Airflow DAG run is still `running`; syncing now would not validate success/failure artifacts.
- The 64-core metadata smoke was not run because the plan requires waiting until the current `baseline_qc` run reaches terminal state first.
- Airflow worker/scheduler were not restarted to avoid perturbing the active `run_pgta_target` task.
- No new heavy `baseline_qc` run was submitted.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. This T092 update only changes state documents; runtime code and services were not modified.

### Risks

- `snakemake.stdout.log` and `snakemake.stderr.log` do not exist while the current Snakemake subprocess is still running; the current runner appears to write captured stdout/stderr only after process exit. Rule logs under `logs/bwa` are the live progress source for this run.
- The current run is using `--cores 1`; allowing it to finish is safe but slow. Switching it to 64 cores would require a separate stop/resume/rerun decision and is not part of T092.
- If the run eventually fails, do not blindly retry; sync Airflow first, inspect `error_summary`, stderr, and rule logs, then decide whether to resume.

### Open questions

- After `PGTA_20260706_162150_00C4FD` reaches terminal state, should Airflow worker/scheduler be safely recreated before the lightweight metadata smoke, or is confirming module reload enough?

### Next recommended task

Wait for `PGTA_20260706_162150_00C4FD` to finish. If it succeeds, call `sync-airflow`, verify `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, `baseline_qc_report.md`, `/qc`, artifacts, and frontend QC panel. If it fails, call `sync-airflow`, record `error_summary` and stderr tail. Only after terminal state, run one lightweight metadata smoke to verify `logs/snakemake.command.txt` contains `--cores 64`.

### Rollback notes

- This turn only updated docs/status files. Revert the T092 docs commit if needed.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, or `git reset --hard`.

## 2026-07-07 11:45 - Codex - T091 PGT-A 64-core runner and frontend auto-sync

### Goal

Make future PGT-A Airflow runs use Snakemake `--cores 64` by default and make the frontend automatically sync selected active runs, without interrupting the already-running `PGTA_20260706_162150_00C4FD` baseline_qc run.

### Completed

- Added `PGTA_SNAKEMAKE_CORES=64` to `.env.example` and Airflow Compose environment.
- Updated `bio_pgta` and `bio_pgta_airflow` runners to read `PGTA_SNAKEMAKE_CORES`, validate it as a positive integer, and write the resulting value to `logs/snakemake.command.txt`.
- Added Airflow runner tests for default `--cores 64` and env override behavior.
- Added frontend selected-run auto sync: active `submitted/running/queued` runs with `dag_run_id` call `sync-airflow` every 15 seconds, refresh run detail/list/samples/rules/artifacts/QC/current log, and stop when terminal.
- Added frontend UI text `Auto sync active` / `Last synced ...`; manual `Sync Airflow` remains.
- Rebuilt and redeployed only the frontend container on `fengxian`; Airflow worker/scheduler/API containers were not recreated.
- Confirmed current run `PGTA_20260706_162150_00C4FD` still reports backend status `running` after the redeploy.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `dags/pgta_metadata_runner.py`
- `dags/pgta_airflow_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `dags/tests/test_pgta_airflow_runner.py`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/styles.css`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `docs/20_PGTA_LEVEL4_AUDIT.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `py -3 -m unittest ...test_pgta_metadata_runner... ...test_pgta_airflow_runner... -v` | success | local development check only, 4 tests OK; not used as acceptance |
| `git diff --check` | success | no whitespace errors |
| `git push origin codex/airflow/T088-pgta-snakemake-cache` | success | pushed code commits `b30be7e`, `fb107a4` |
| `ssh fengxian 'cd /home/jiucheng/project/airflow-demo && git pull --ff-only && docker compose -f docker-compose.yaml config --quiet'` | success | mirror fast-forwarded; Compose config valid |
| `docker run --rm --entrypoint /usr/local/bin/python ... airflow-demo/airflow:0.1.0 -m unittest ... -v` | success | remote Airflow image, 4 tests OK |
| `docker build --target test -f frontend/Dockerfile frontend` | failed then success | first failed because the new test captured Testing Library internal intervals; fixed test and reran, 16 Vitest tests passed |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| `docker compose -f docker-compose.yaml build frontend` | success | production frontend image rebuilt |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` | success | recreated frontend only; no volumes deleted |
| `curl -fsS http://127.0.0.1:12959/` | success after nginx startup | returned React HTML |
| `docker compose -f docker-compose.yaml config \| grep -n PGTA_SNAKEMAKE_CORES` | success | rendered `PGTA_SNAKEMAKE_CORES: "64"` |
| `curl -fsS http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD` | success | run still `status="running"` |

### Tests

- Remote Airflow-image runner tests: 4 passed.
- Remote frontend Docker test target: 16 Vitest tests passed.
- Airflow DAG import check: `No data found`.
- Frontend production build passed and HTTP 12959 returned HTML.

### Not run / why

- Did not submit a new PGT-A `baseline_qc` run because `PGTA_20260706_162150_00C4FD` is still running.
- Did not stop or resume the current baseline_qc run; T091 intentionally only affects future PGT-A task starts.
- Did not recreate Airflow worker/scheduler/API containers to avoid interrupting or perturbing the active baseline_qc run. Code defaults still make future imported runner commands default to 64 cores.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. Runtime validation ran on `fengxian` at commit `fb107a4`; this handoff/status update follows that validation.

### Risks

- An already-running Snakemake process keeps its original `--cores 1` command; to make `PGTA_20260706_162150_00C4FD` use 64 cores, it would need a separate stop/resume or rerun decision.
- Running Airflow worker processes were not recreated. The code default is now 64, but if Airflow keeps a stale imported module in a long-lived worker process, a worker restart after the active run finishes may be prudent before a new heavy baseline_qc run.
- `--cores 64` is Snakemake's available core pool; actual parallelism still depends on the PGT-A Snakefile `threads` declarations and resource rules.

### Open questions

- After the current baseline_qc run finishes, should we run one lightweight metadata smoke to confirm `logs/snakemake.command.txt` contains `--cores 64`, or restart Airflow worker first and then run the next baseline_qc smoke?

### Next recommended task

Wait for `PGTA_20260706_162150_00C4FD` to finish, then sync it from the frontend. If it succeeds, verify baseline QC artifacts/QC panel; if it fails, inspect stderr/error_summary and decide whether to resume with the new 64-core default.

### Rollback notes

- Revert the T091 commits and redeploy frontend if needed.
- To revert only frontend polling, revert `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, and `frontend/src/styles.css`, rebuild frontend, then `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`.
- Do not use `docker compose down -v`, `docker system prune`, or `docker volume prune`.

## 2026-07-06 22:58 - Codex - T090 sample lifecycle status sync

### Goal

Fix the frontend Samples table showing `pending` forever even after a run was submitted or had reached Airflow `success/failed`.

### Completed

- Traced the issue through frontend -> API -> DB and confirmed the frontend was displaying backend data correctly.
- Root cause: `sample.status` was initialized as `pending`, but backend submit/reanalysis/sync paths only updated `analysis_run.status`, never sample lifecycle status.
- Added red backend tests showing:
  - submit left samples as `pending` instead of `running`;
  - sync success left samples as `pending` instead of `success`;
  - sync failed left samples as `pending` instead of `failed`.
- Updated backend submit/reanalyze paths to mark samples `running`.
- Updated explicit `sync-airflow` to map Airflow state back to sample status: `success -> success`, `failed -> failed`, active states to `running`.
- Rebuilt and redeployed backend on `fengxian`.
- Explicitly synced recent visible runs so the live UI no longer shows stale pending values for those runs.

### Changed files

- `backend/app/run_service.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_submit.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| targeted backend tests after test-only commit on `fengxian` | failed as expected | 3 failures showed actual sample status was still `pending` |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q tests/test_run_submit.py::... tests/test_run_diagnostics.py::...` | success | 3 targeted tests passed after implementation |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 48 passed |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend` | success | recreated backend only; no volumes deleted |
| `curl http://127.0.0.1:8000/api/health` | success | `{"status":"ok"}` |
| explicit sync for recent visible runs | success | refreshed sample statuses without submitting new DAG runs |

### Tests

- Red targeted tests failed with `pending != running/success/failed`.
- Green targeted tests passed: 3 passed.
- Full backend pytest passed: 48 passed.
- Runtime API sample checks passed:
  - `PGTA_20260706_141915_5BE5E2`: `E2/E3=success`.
  - `PGTA_20260706_140854_8F2CA4`: `E2=success`.
  - `WES_20260705_164813_C5561C`: `S001/S002=success`.

### Not run / why

- Frontend Docker tests were not rerun because the frontend code was not modified; Samples table already reads `sample.status` from the API.
- No new PGT-A/WES DAG run was submitted. Existing runs were only synced through the existing `sync-airflow` endpoint.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. Runtime validation ran on `fengxian` at commit `065907c`; this handoff/status update follows that validation.

### Risks

- Historical runs not included in the recent visible sync batch may still show old `pending` sample statuses until the user clicks `Sync Airflow` on that run.
- For failed runs, sample status is currently run-level `failed`; fine-grained per-sample failure attribution remains a future rule/qsub enhancement.

### Open questions

- None for this fix.

### Next recommended task

Return to the prior demo roadmap: user-confirmed PGT-A `baseline_qc` Level 4 smoke with at least 2 samples, or T080 demo smoke report/script.

### Rollback notes

- Revert the T090 commits, rebuild/redeploy backend, and re-sync affected runs if needed. Do not delete volumes.

## 2026-07-06 22:40 - Codex - T089 demo log/timezone alignment

### Goal

Fix the user-visible mismatch where demo logs and timestamps did not line up with the `fengxian` host clock.

### Completed

- Confirmed `fengxian` host time is `Asia/Shanghai`, while backend/Airflow containers previously had `TZ=<unset>` and Airflow was configured as `core.default_timezone=utc`, `webserver.default_ui_timezone=UTC`.
- Added Compose timezone defaults: `AIRFLOW_DEMO_TZ=Asia/Shanghai`, `AIRFLOW_DEFAULT_TIMEZONE=Asia/Shanghai`, and `AIRFLOW_DEFAULT_UI_TIMEZONE=Asia/Shanghai`.
- Recreated backend, frontend, and Airflow service containers so their process logs use `+0800 CST`.
- Updated frontend timestamp rendering to convert timezone-aware backend ISO timestamps into fixed `YYYY-MM-DD HH:mm:ss Asia/Shanghai` text.
- Added a frontend test covering UTC API timestamp rendering as Shanghai display time.
- Documented the timezone contract and verification evidence.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `frontend/Dockerfile`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `SERVER_INFO.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Rendered `AIRFLOW__CORE__DEFAULT_TIMEZONE=Asia/Shanghai`, `AIRFLOW__WEBSERVER__DEFAULT_UI_TIMEZONE=Asia/Shanghai`, `TZ=Asia/Shanghai`, and frontend build arg `VITE_DISPLAY_TIME_ZONE=Asia/Shanghai` |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 15 Vitest tests passed |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | Production frontend bundle rebuilt with `Asia/Shanghai` display timezone |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend airflow-api-server airflow-scheduler airflow-worker` on `fengxian` | success | Recreated only affected services; no volumes deleted |
| Health probes on `fengxian` | success | backend `/api/health`, Airflow `/health`, and frontend HTTP 200 |
| container date/timezone probe on `fengxian` | success | backend/frontend/Airflow containers report `TZ=Asia/Shanghai` and `date` as `+0800 CST` |
| Airflow timezone/log probe on `fengxian` | success | Airflow config reports core/UI `Asia/Shanghai`; scheduler/webserver logs show `+0800` and `Configured default timezone Asia/Shanghai` |

### Tests

- Remote frontend Docker test target passed: 15 tests.
- Remote Compose config passed.
- Runtime health and timezone probes passed on `fengxian`.

### Not run / why

- No backend pytest or DAG unittest was rerun because this change did not modify backend Python, DAG code, database schema, or Snakemake behavior.
- No new PGT-A or WES run was submitted; this was a display/log timezone fix only.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. Runtime validation ran on `fengxian` at commit `f2fdff2`; this handoff/status update follows that validation.

### Risks

- Airflow `/health` heartbeat and HTTP `Date` headers can still show UTC/GMT by protocol/API convention. Airflow service logs and UI timezone config now use `Asia/Shanghai`.
- Historical DB timestamps remain timezone-aware values and were not rewritten.

### Open questions

- None for this fix.

### Next recommended task

Return to the prior demo roadmap: user-confirmed PGT-A `baseline_qc` Level 4 smoke with at least 2 samples, or T080 demo smoke report/script.

### Rollback notes

- Revert the T089 commits, rebuild/redeploy frontend if needed, and recreate backend/frontend/Airflow services. Do not delete volumes.

## 2026-07-06 22:06 - Codex - T088 PGT-A run-local Snakemake cache fix

### Goal

Fix the PGT-A submit-after-click failure where backend successfully triggered `bio_pgta`, but the DAG failed almost immediately before the user could see a meaningful running state in Airflow.

### Completed

- Investigated latest failed run `PGTA_20260706_135413_598BA1`.
- Confirmed backend submit succeeded and Airflow created `manual__PGTA_20260706_135413_598BA1`.
- Identified root cause in `logs/snakemake.stderr.log`: Snakemake tried to create `/home/airflow/.cache/snakemake` and failed with `PermissionError`.
- Added TDD tests for `run_pgta_target` and `run_snakemake9_with_logger` requiring run-local cache directories and `XDG_CACHE_HOME`.
- Updated `bio_pgta` runner to create `<workdir>/tmp/xdg-cache`, set `XDG_CACHE_HOME`, and write `logs/snakemake.command.txt`.
- Updated `bio_pgta_airflow` Snakemake 9 logger runner with the same run-local cache behavior and command log.
- Verified a new metadata smoke run `PGTA_20260706_140854_8F2CA4` reaches Airflow/backend `success`.

### Changed files

- `dags/pgta_metadata_runner.py`
- `dags/pgta_airflow_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `dags/tests/test_pgta_airflow_runner.py`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker run --rm --entrypoint /usr/local/bin/python ... test_run_pgta_target_metadata... test_run_snakemake9...` on `fengxian` after tests-only commit | failed as expected | both tests failed because `<workdir>/tmp/xdg-cache` did not exist |
| same targeted test command after implementation | success | 2 tests OK |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | no compose errors |
| `docker run --rm --entrypoint /usr/local/bin/python ... -m unittest dags.tests.test_bio_pgta_dag dags.tests.test_pgta_metadata_runner dags.tests.test_pgta_airflow_runner -v` | success | 20 tests OK |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| remote API metadata smoke for `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` | success | created/submitted `PGTA_20260706_140854_8F2CA4`; sync statuses running, running, success |
| `airflow dags list-runs -d bio_pgta | grep PGTA_20260706_140854_8F2CA4` | success | Airflow state `success` |
| service health probes | success | backend `{"status":"ok"}`, frontend HTTP 200, Airflow scheduler/metadatabase healthy |

### Tests

- Red test confirmed the missing cache behavior before implementation.
- Targeted tests passed after implementation.
- Full PGT-A DAG/runner unit suite passed: 20 tests.
- Airflow import check passed.
- Real PGT-A metadata smoke passed and generated:
  - `logs/run_metadata.tsv` with 11 lines.
  - `logs/snakemake.command.txt`.
  - `logs/snakemake.stderr.log` without `/home/airflow/.cache/snakemake` PermissionError.
  - artifacts including `snakemake_command` and `run_metadata`.

### Not run / why

- No real `baseline_qc` Level 4 run was executed; this fix only targets metadata submit failure and Snakemake cache handling.
- No Docker volumes were deleted and no prune commands were run.
- No host `/home/airflow` chmod or PGT-A source directory modification was done.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. Code verification passed at commit `dd5c6e7`; this handoff/status update is the final docs batch for the same branch.

### Risks

- Metadata target is fast, so Airflow UI may still show `running` only briefly; the durable evidence is the DAG run final state and frontend/API sync result.
- `baseline_qc` remains heavier than metadata and still needs user-confirmed samples/window before running.

### Open questions

- Which two samples should be used for the first `baseline_qc` Level 4 smoke?

### Next recommended task

Ask the user to open `http://fengxian:12959/`, create a small `metadata smoke` run, submit, and verify the UI can sync to success. Then proceed to user-confirmed `baseline_qc` Level 4 smoke or T080 demo script.

### Rollback notes

- Stop services safely with `docker compose -f docker-compose.yaml down` only.
- Revert T088 commits on `codex/airflow/T088-pgta-snakemake-cache` if needed.
- Do not chmod `/home/airflow`, do not use `down -v`, and do not run Docker prune commands.

## 2026-07-06 21:45 - Codex - T085/T086/T087 PGT-A baseline_qc staged integration

### Goal

Re-center the next development phase on the PGT-A demo path: audit the real PGT-A workflow for a safe Level 4 target, add controlled `baseline_qc` support across backend/Airflow/frontend, expose baseline artifacts/QC, and keep real execution gated until the user confirms samples and runtime window.

### Completed

- Performed a read-only audit of `/home/jiucheng/pipelines/PGT_A` on `fengxian`.
- Confirmed `baseline_qc` exists in the real Snakefile, belongs to `pipeline.mode=build_ref`, requires at least 2 baseline/reference samples, and emits `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, and `baseline_qc_report.md`.
- Added `baseline_qc` to the controlled PGT-A target allowlist.
- Enforced the 2-selected-sample minimum in both run creation and submit validation.
- Extended `bio_pgta` config generation for `baseline_qc` with `pipeline.targets=["mapping","metadata","baseline_qc"]`, `build_reference.groups.demo`, `--cores 1`, and no dry-run flag.
- Added dynamic artifact discovery for PGT-A baseline QC summary/pass-samples/report.
- Added PGT-A baseline QC TSV parsing into existing `qc_metric` and `/api/runs/{analysis_id}/qc`.
- Updated the frontend target selector with `baseline QC smoke`, disabled Create Run until 2 samples are selected, and hid Submit for invalid baseline created runs.
- Rebuilt/redeployed backend, frontend, and Airflow services on `fengxian`.

### Changed files

- `backend/app/run_service.py`
- `backend/app/diagnostics_service.py`
- `backend/app/qc_service.py`
- `backend/tests/test_run_creation.py`
- `backend/tests/test_run_submit.py`
- `backend/tests/test_run_diagnostics.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/17_DEMO_SCRIPT.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `docs/20_PGTA_LEVEL4_AUDIT.md`
- `SERVER_INFO.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git checkout -b codex/fullstack/T085-pgta-main-demo` | success | local feature branch |
| read-only PGT-A audit via `ssh fengxian` heredoc | success | no remote writes; confirmed `baseline_qc` targets and constraints |
| `git diff --check` | success | only CRLF warning for `MANIFEST.json` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose v2.24.7 |
| `docker compose -f docker-compose.yaml build backend frontend airflow-worker airflow-scheduler airflow-api-server` on `fengxian` | success | frontend production build passed |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` on `fengxian` | success | 48 passed |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | failed first, then success | first failure was an async QC test race; after fixing test wait, 14 passed |
| `docker run --rm --entrypoint /usr/local/bin/python -v /home/jiucheng/project/airflow-demo:/repo:ro -w /repo airflow-demo/airflow:0.1.0 -m unittest dags.tests.test_bio_pgta_dag dags.tests.test_pgta_metadata_runner -v` | success | 14 DAG/runner tests OK |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| `docker compose -f docker-compose.yaml up -d --no-deps backend frontend airflow-api-server airflow-scheduler airflow-worker` | success | recreated only affected services; no volume deletion |
| `curl http://127.0.0.1:8000/api/health` | success | `{"status":"ok"}` |
| `curl http://127.0.0.1:12959/` | success | HTTP 200, title `airflow-demo` |
| `curl http://127.0.0.1:12958/health` | success after startup retry | Airflow scheduler/metadatabase healthy |

### Tests

- Backend Dockerized pytest: 48 passed.
- Frontend Dockerized Vitest target: 14 passed.
- Airflow/DAG unittest: 14 passed.
- Airflow import check: no import errors.
- Service smoke after redeploy: backend health ok, frontend HTTP 200, Airflow health healthy.

### Not run / why

- No real `baseline_qc` run was submitted. Audit showed it triggers mapping + metadata + baseline QC and requires at least 2 samples, so Level 4 execution must wait for user-confirmed sample selection and runtime window.
- No CNV production run, qsub, MailHog email, NIPT, BS10610 migration, or true PGT-A report/MultiQC registration was attempted.

### Current git status

Implementation commit `4cf6f6e` is pushed on branch `codex/fullstack/T085-pgta-main-demo`. This handoff/status update is the final docs batch for the same branch.

### Risks

- `baseline_qc` is not a lightweight single-sample smoke; it may consume meaningful runtime and mapping resources even with `--cores 1`.
- The generated run-local config has not yet been validated by a real `baseline_qc` execution.
- If the real PGT-A workflow writes unexpected relative paths, the Level 4 smoke should stop and preserve logs rather than retrying.

### Open questions

- Which two PGT-A samples should be used for the first Level 4 staged run?
- What runtime window and monitoring expectations are acceptable for that run?
- If `baseline_qc` is too heavy, should we choose a smaller real target after another audit pass?

### Next recommended task

Run a user-confirmed PGT-A Level 4 smoke for `target=baseline_qc` with exactly 2 selected samples, low concurrency, and output isolated under `shared/runs/<analysis_id>`. If that passes, move to T080/T081 demo script/report, then T034/T063 MailHog notifications.

### Rollback notes

- To stop services safely: `docker compose -f docker-compose.yaml down` only.
- Do not use `down -v`, `docker system prune`, or `docker volume prune`.
- To revert this branch before merge, revert the commit(s) on `codex/fullstack/T085-pgta-main-demo`; no production PGT-A directory files were modified.

## 2026-07-06 01:35 - Codex - T051 PGT-A submit workspace usability fix

### Goal

Fix the live frontend usability issue where the PGT-A submit form was cramped inside the left run-list sidebar and looked difficult to submit. Keep the backend/API contract unchanged and do not run PGT-A jobs as part of this UI fix.

### Completed

- Confirmed the backend scan API works for `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28`.
- Added a failing frontend test that requires a main `Submit new analysis` region, keeps `New PGT-A Run` out of the run-list aside, and shows clear Create Run enablement guidance.
- Moved `New PGT-A Run` and `New WES Mock Run` into a main submit workspace above run detail.
- Left sidebar now only contains the run list.
- Added `Select at least one scanned sample to enable Create Run.` guidance and selected-sample count text.
- Updated layout CSS so the PGT-A form uses the main content width and the candidate sample table is no longer squeezed into the side rail.
- Rebuilt and redeployed only the `frontend` service on `fengxian`.

### Modified files

- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/06_FRONTEND_SPEC.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands and results

| Command | Result |
|---|---|
| `git checkout -b codex/frontend/T051-pgta-submit-workspace` | success |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` after test-only commit | failed as expected: 1 failed, 11 passed; missing `Submit new analysis` region and form still inside run-list aside |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` after implementation | success: 12 tests passed |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success; Vite production build generated `index-BJnogiqz.css` and `index-BYax1L4P.js` |
| `docker compose -f docker-compose.yaml up -d frontend` on `fengxian` | success; recreated only frontend while backend stayed healthy |
| `curl http://100.112.254.72:12959/` | success, HTTP 200 |
| `curl http://100.112.254.72:8000/api/health` | success, HTTP 200 |
| deployed CSS grep for `submit-workspace` | success |

### Not run / why

- No real PGT-A job was submitted; this task only fixed the submit UI layout and guidance.
- Browser automation was attempted but the in-app browser control timed out; verification used Dockerized frontend tests plus live HTTP/CSS checks.
- No backend, DAG, Snakemake, DB migration, or Docker volume operation was needed.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was used.

### Current git status

Work is on branch `codex/frontend/T051-pgta-submit-workspace`. Runtime validation and live frontend deployment ran on the `fengxian` mirror at commit `872d59b`, followed by this docs/status update.

### Risks

- The page is still a single-page workspace, not a fully routed dashboard; this fix makes the existing workflow usable but does not add route-level navigation.
- PGT-A full production flow is still not deployed; this only improves the existing metadata/dry-run/failure-smoke submission UI.

### Next recommended task

Either continue with PGT-A real target staged integration, or add T080 smoke/demo scripting so the current PGT-A/WES demo can be replayed reliably from the UI and API.

### Rollback notes

- Revert the frontend/layout commits with normal `git revert` and rebuild/redeploy `frontend`.
- Stop services, if needed, with `docker compose -f docker-compose.yaml down` only; do not use `down -v`.

## 2026-07-06 00:54 - Codex - T060/T054 WES mock QC parser and panel

### Goal

Add WES mock QC output, parse successful `bio_wes_qsub` run QC into biodemo `qc_metric` through explicit `sync-airflow`, expose `GET /api/runs/{analysis_id}/qc`, and show the QC panel in the React run detail. Keep scope mock-only: no MailHog, NIPT, real qsub, real WES QC, MultiQC, or DB migration.

### Completed

- Added `reports/qc_summary.tsv` generation to the WES mock `final_summary` rule.
- Added backend QC parser/import service, idempotent refresh into `qc_metric`, sample `qc_status` aggregation, and `GET /api/runs/{analysis_id}/qc`.
- Extended `sync-airflow` so successful `wes_qsub` DAG runs import QC after Airflow reaches `success`.
- Extended dynamic artifacts to include `wes_qc_summary`.
- Added frontend API types/client and a run detail QC panel with pass/warn/fail/unknown summary, metric table, and empty state.
- Updated API/frontend/DAG/Snakemake/QC/runbook/testing docs, task status, current state, manifest, and this handoff.

### Modified files

- `backend/app/qc_service.py`
- `backend/app/diagnostics_service.py`
- `backend/app/main.py`
- `backend/tests/test_run_diagnostics.py`
- `dags/wes_qsub_runner.py`
- `dags/tests/test_wes_qsub_runner.py`
- `pipelines/wes/workflow/Snakefile`
- `pipelines/tests/test_wes_mock_contract.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/styles.css`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands and results

| Command | Result |
|---|---|
| `git checkout -b codex/fullstack/T060-T054-wes-qc-panel` | success |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success |
| `docker compose -f docker-compose.yaml build backend frontend airflow-worker airflow-scheduler airflow-api-server` on `fengxian` | success |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` on `fengxian` | success, `43 passed` |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q tests/test_run_diagnostics.py` on `fengxian` | success, `9 passed` |
| Dockerized `python -m unittest pipelines.tests.test_wes_mock_contract -v` on `fengxian` | success, `Ran 7 tests OK` |
| Dockerized `python -m unittest dags.tests.test_bio_wes_qsub_dag dags.tests.test_wes_qsub_runner -v` on `fengxian` | success, `Ran 11 tests OK` |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success, `11 passed` |
| `airflow dags list-import-errors` in Airflow scheduler container | success, `No data found` |
| API/frontend WES QC smoke | success: `WES_20260705_164813_C5561C` reached `success`, `/qc` returned `pass=6,warn=0,fail=0,unknown=0`, artifacts include `wes_qc_summary` |
| `test -s shared/runs/WES_20260705_164813_C5561C/reports/qc_summary.tsv` on `fengxian` | success; TSV contains deterministic rows for `S001/S002` |

### Not run / why

- No MailHog success/failure email was implemented or tested; T034/T063 remain next.
- No NIPT, real qsub, real WES data, real production QC, MultiQC HTML, or artifact table registration was implemented.
- No DB migration was added; existing `qc_metric` and `sample.qc_status` schema was sufficient.
- One smoke shell bundle exited nonzero only because a final `head` check inherited a CRLF path from a PowerShell here-string; the direct follow-up `test -s .../qc_summary.tsv && head ...` passed.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was used.

### Current git status

Work is on branch `codex/fullstack/T060-T054-wes-qc-panel`. Runtime validation ran on the `fengxian` mirror at commit `e22ea41`, followed by this docs/status update.

### Risks

- WES QC values are deterministic mock values for demo display only; they are not valid production WES QC.
- QC import is tied to explicit `sync-airflow`; the frontend must sync after DAG success before QC appears.
- Artifacts are still dynamically discovered; T061 artifact table registration and MultiQC report handling remain open.

### Next recommended task

Proceed to T034/T063: MailHog success/failure notification with QC and error-summary links. T080 smoke script/reporting is also a good next slice now that PGT-A and WES mock visible paths both exist.

### Rollback notes

- Revert repository changes with normal `git revert`.
- Stop services with `docker compose -f docker-compose.yaml down` only; do not use `down -v`.
- The WES smoke workdir `shared/runs/WES_20260705_164813_C5561C` is disposable demo output, but do not delete shared data without explicit user approval.

## 2026-07-06 00:24 - Codex - T044/T056 WES mock resume/rerun lifecycle

### Goal

Expose the WES mock `bio_wes_qsub` path through FastAPI/React and add same-workdir `resume` plus selected-rule `rerun_rule` without real qsub, real WES data, QC, email, NIPT, `clone_new`, or `--forceall`.

### Completed

- Added WES mock `POST /api/runs` creation for fixed samples `S001/S002`.
- Extended submit action to dispatch both `pgta` and `wes_qsub`; WES submit passes `backend_event_url=http://backend:8000/api/events/snakemake`.
- Added `POST /api/runs/{analysis_id}/actions/reanalyze` for WES `resume` and `rerun_rule`.
- Extended `bio_wes_qsub` runner validation and command construction for `new/resume/rerun_rule`.
- Added `logs/snakemake.command.txt` artifact to prove `--forcerun` use and absence of `--forceall`.
- Added frontend WES mock create-and-submit panel and WES detail `Resume` / `Rerun rule` controls.
- Verified full remote WES smoke: `WES_20260705_162041_2507AF` initial submit, resume, and `rerun_rule fastp/S001` all reached success.
- Updated API, frontend, DAG, Snakemake/qsub, logging, runbook, testing, task, current-state, and manifest docs.

### Changed files

- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_wes_run_lifecycle.py`
- `dags/wes_qsub_runner.py`
- `dags/tests/test_wes_qsub_runner.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/styles.css`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| red backend WES lifecycle tests on `fengxian` | failed as expected | WES create returned 422; reanalyze route returned 404 |
| red DAG runner tests on `fengxian` | failed as expected | `resume` rejected; `build_snakemake_command(mode=...)` unsupported |
| red frontend Docker test target on `fengxian` | failed as expected | missing WES panel and reanalysis controls |
| `docker compose -f docker-compose.yaml build backend` | success | Built `airflow-demo/backend:0.1.0` |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 40 tests passed |
| Airflow/DAG unittest in `airflow-demo/airflow:0.1.0` | success | 11 tests OK; used `/tmp/airflow` for logs |
| `docker build --target test -f frontend/Dockerfile frontend` | success | 10 Vitest tests passed |
| `docker compose -f docker-compose.yaml build frontend` | success | TypeScript and Vite production build passed |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend` | success | Applied rebuilt backend/frontend images; no volumes deleted |
| `docker compose -f docker-compose.yaml config --quiet` | success | Latest compose config rendered |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| WES API/Airflow smoke for `WES_20260705_162041_2507AF` | success | new, resume, and rerun_rule all reached success |
| `curl http://127.0.0.1:12959/` and `/api/runs?limit=5` | success | Frontend served; latest run list includes WES smoke run |

### Tests

Remote-only evidence from `fengxian`:

- `WES_20260705_162041_2507AF` initial DAG run `manual__WES_20260705_162041_2507AF` ended `success`.
- Resume DAG run `manual__WES_20260705_162041_2507AF__resume__20260705T162142Z` ended `success`.
- Rerun DAG run `manual__WES_20260705_162041_2507AF__rerun_rule__20260705T162151Z` ended `success`.
- `/api/runs/WES_20260705_162041_2507AF/rules` returned 7 rule rows.
- `shared/runs/WES_20260705_162041_2507AF/logs/events/snakemake_events.jsonl` has 28 lines.
- `shared/runs/WES_20260705_162041_2507AF/logs/snakemake.command.txt` contains `--forcerun fastp` and no `--forceall`.

### Not run / why

- No real qsub/qstat was run; `fengxian` still lacks real qsub and this task is mock-only.
- No QC parser/panel, MailHog notification, NIPT DAG, `rerun_failed`, or `clone_new` was implemented.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was used.

### Current git status

Work is on branch `codex/fullstack/T044-T056-wes-rerun`. Runtime validation ran on the `fengxian` mirror at commit `25c0633`, followed by this docs/status update.

### Risks

- WES remains mock-only and fixed to `S001/S002`; real WES inputs and real qsub require separate planning.
- The latest reanalysis action overwrites `analysis_run.dag_run_id` with the newest DAG run id; prior actions remain in `run_action`.
- Frontend reanalysis is intentionally hidden while a WES run is `submitted/running/queued`.

### Open questions

- Whether `rerun_failed` should be implemented as a real failed-rule selector after a controlled WES failure smoke exists.

### Next recommended task

Proceed to T060/T054: parse WES mock QC/final-summary data into `qc_metric` and add the frontend QC panel. T034/T063 MailHog notification is the other good next slice.

### Rollback notes

- Revert repository changes with normal `git revert`.
- If runtime cleanup is needed, remove only generated WES mock run directories under `shared/runs/WES_*` after path verification.
- Stop services only with `docker compose -f docker-compose.yaml down`; do not use `down -v` or prune commands.

## 2026-07-05 00:52 - Codex - T030/T031 bio_wes_qsub Airflow DAG skeleton

### Goal

Add the WES mock project-level Airflow DAG `bio_wes_qsub`, without FastAPI WES submission, frontend WES pages, QC/reanalysis, or real qsub. The DAG should run the already validated WES mock Snakemake workflow through `profiles/qsub` and the mock qsub wrapper inside the Airflow worker.

### Completed

- Added `dags/common` helpers for shared-root validation, directory creation, subprocess stdout/stderr capture, and small summaries.
- Added `dags/bio_wes_qsub.py` and `dags/wes_qsub_runner.py`.
- Added project Airflow image `airflow-demo/airflow:0.1.0`, based on `apache/airflow:2.9.3-python3.11`, with Snakemake 9.23.1 and `snakemake-executor-plugin-cluster-generic==1.0.9` isolated in `/opt/airflow/snakemake-venv`.
- Updated Compose Airflow services to use the project image and mount `./pipelines`, `./profiles`, and `./shared`.
- Fixed two remote runtime blockers found during smoke:
  - Airflow worker initially ran as uid `50000` and could not create new `shared/runs/WES_*` workdirs; `AIRFLOW_UID` now defaults to `1005` for `fengxian`, and runbook says to set it to `id -u` on new servers.
  - Snakemake tried to write `/home/airflow/.cache/snakemake`; `run_wes_qsub` now sets `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`.
- Verified `bio_wes_qsub` smoke success on `fengxian`: `manual__WES_AIRFLOW_20260705_004506`.
- Updated DAG, qsub, runbook, acceptance, server, task, current-state, handoff, and manifest docs.

### Changed files

- `.env.example`
- `airflow_image/Dockerfile`
- `airflow_image/pip.conf`
- `airflow_image/requirements.txt`
- `dags/common/__init__.py`
- `dags/common/paths.py`
- `dags/common/subprocess_utils.py`
- `dags/bio_wes_qsub.py`
- `dags/wes_qsub_runner.py`
- `dags/tests/test_bio_wes_qsub_dag.py`
- `dags/tests/test_wes_qsub_runner.py`
- `docker-compose.yaml`
- `pipelines/tests/test_wes_mock_contract.py`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote targeted UID contract test after tests-only commit | failed as expected | Compose still rendered `AIRFLOW_UID:-50000` |
| remote targeted cache test after tests-only commit | failed as expected | `XDG_CACHE_HOME` missing from Snakemake subprocess env |
| `docker compose -f docker-compose.yaml config --quiet` | success | Rendered Airflow `user: "1005:0"` after `.env` update |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate airflow-api-server airflow-scheduler airflow-worker` | success | Applied new Airflow uid; no volumes deleted |
| `docker compose -f docker-compose.yaml exec -T airflow-worker id` | success | `uid=1005(default) gid=0(root)` |
| `docker compose -f docker-compose.yaml build airflow-worker airflow-scheduler airflow-api-server` | success | Cached build, image `airflow-demo/airflow:0.1.0` |
| `docker run --rm airflow-demo/airflow:0.1.0 airflow version` | success | `2.9.3` |
| `docker run --rm --entrypoint snakemake airflow-demo/airflow:0.1.0 --version` | success | `9.23.1` |
| `docker run --rm --entrypoint snakemake airflow-demo/airflow:0.1.0 --help \| grep -F cluster-generic` | success | `cluster-generic` executor visible |
| `python -m unittest pipelines.tests.test_wes_mock_contract -v` in backend image | success | 6 tests OK |
| `/usr/local/bin/python -m unittest dags.tests.test_bio_wes_qsub_dag dags.tests.test_wes_qsub_runner -v` in Airflow image | success | 8 tests OK |
| `airflow dags list-import-errors` | success | `No data found` |
| trigger `bio_wes_qsub` with `WES_AIRFLOW_20260705_004506` | success | DAG run ended `success` |

### Tests

Remote-only evidence from `fengxian`:

- `manual__WES_AIRFLOW_20260705_004506` ended Airflow `success`.
- `shared/runs/WES_AIRFLOW_20260705_004506/reports/final_summary.tsv` contains `S001` and `S002` `mock_success`.
- `shared/runs/WES_AIRFLOW_20260705_004506/logs/events/snakemake_events.jsonl` has 14 lines with `qsub_submitted` and `qsub_success`.
- `shared/runs/WES_AIRFLOW_20260705_004506/logs/qsub/*.o/e` exists.
- `collect_wes_artifacts` task log returned XCom summary `event_count=14`, `qsub_log_count=14`.

### Not run / why

- No FastAPI WES create/submit endpoint was added; out of scope for T031.
- No frontend WES page, QC parser, reanalysis UI, MailHog notification, NIPT DAG, or real qsub was run.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was used.

### Current git status

Work is on branch `codex/airflow/T031-wes-qsub-dag`. Runtime validation ran on the `fengxian` mirror at commit `ec5c9e2`, followed by this docs/status update.

### Risks

- `.env` on any new Linux server must set `AIRFLOW_UID=$(id -u)` for the deploy user; otherwise Airflow-only DAGs may fail to create bind-mounted run directories.
- The Airflow image puts `/opt/airflow/snakemake-venv/bin` first on `PATH`; use `/usr/local/bin/python` when running tests that require the base Airflow Python packages.
- WES remains mock-only and does not represent production WES parameters or real cluster scheduling.

### Open questions

- Whether WES should next be exposed through FastAPI/frontend, or whether QC/reanalysis is higher demo priority.

### Next recommended task

Proceed to T044/T056 for resume/rerun behavior on top of `bio_wes_qsub`, or T060/T054 for mock QC parsing and the frontend QC panel.

### Rollback notes

- Revert repository changes with normal `git revert`.
- If runtime cleanup is needed, remove only generated WES mock run directories under `shared/runs/WES_AIRFLOW_*` after path verification.
- Stop services only with `docker compose -f docker-compose.yaml down`; do not use `down -v` or prune commands.

## 2026-07-04 23:11 - Codex - T042 Snakemake cluster-generic profile runtime

### Goal

Unblock T042 by adding an isolated Dockerized Snakemake runtime that can execute the WES mock workflow through `profiles/qsub` and the `cluster-generic` executor, without modifying `/biosoftware/miniconda/envs/*` or calling real qsub.

### Completed

- Added `snakemake_runner/` with `python:3.12-slim`, `snakemake==9.23.1`, `snakemake-executor-plugin-cluster-generic==1.0.9`, and the repo pip mirror config.
- Added run-only Compose service `snakemake-runner` with image `airflow-demo/snakemake-runner:0.1.0`, no exposed ports, read-only repo mount, shared run output mount, and writable tmpfs for `/app/.snakemake`.
- Updated `profiles/qsub/config.yaml` to use `${{AIRFLOW_DEMO_QSUB_PYTHON:-python}} pipelines/common/qsub_submit.py` so Snakemake formatting preserves shell env expansion.
- Added contract tests for the runner Dockerfile, pinned dependencies, Compose service, and mock-safe profile submit command.
- Verified on `fengxian` that `--profile profiles/qsub` drives the mock qsub wrapper through `cluster-generic` and produces final summary, qsub stdout/stderr, and JSONL events.
- Updated qsub, runbook, acceptance, server, task, current-state, handoff, and manifest docs.

### Changed files

- `snakemake_runner/Dockerfile`
- `snakemake_runner/requirements.txt`
- `snakemake_runner/pip.conf`
- `docker-compose.yaml`
- `.env.example`
- `profiles/qsub/config.yaml`
- `pipelines/tests/test_wes_mock_contract.py`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote temp contract tests after tests-only patch | failed as expected | Missing runner Dockerfile/service and old profile Python command |
| remote temp `python -m unittest pipelines.tests.test_wes_mock_contract -v` after implementation | success | 4 tests OK |
| remote profile runtime before env escape fix | failed as expected | Snakemake formatted `${AIRFLOW_DEMO_QSUB_PYTHON:-python}` as an unknown variable |
| remote temp regression test for escaped env expansion | failed as expected | Confirmed profile needed `${{AIRFLOW_DEMO_QSUB_PYTHON:-python}}` |
| remote temp regression test after fix | success | Escaped env expansion contract passed |
| official mirror `git pull --ff-only` | success | `/home/jiucheng/project/airflow-demo` fast-forwarded to `cd22c90` |
| official mirror `docker compose -f docker-compose.yaml config --quiet` | success | Compose rendered with `snakemake-runner` |
| official mirror `docker compose -f docker-compose.yaml build snakemake-runner` | success | Built `airflow-demo/snakemake-runner:0.1.0` |
| official mirror `docker compose -f docker-compose.yaml run --rm snakemake-runner snakemake --version` | success | Returned `9.23.1` |
| official mirror `snakemake --help` inside runner | success | `cluster-generic` executor and `--cluster-generic-submit-cmd` visible |
| official mirror plugin import check | success | Imported `snakemake_executor_plugin_cluster_generic` |
| official mirror Dockerized contract tests | success | `python -m unittest pipelines.tests.test_wes_mock_contract -v`, 4 tests OK |
| official mirror WES profile runtime smoke | success | `WES_PROFILE_20260704_230713` completed 8 WES mock jobs through `--profile profiles/qsub` |

### Tests

Remote-only evidence from `fengxian`:

- Runner build succeeded and produced image `airflow-demo/snakemake-runner:0.1.0`.
- Snakemake version inside runner: `9.23.1`.
- `cluster-generic` executor and settings are visible inside the runner.
- WES profile runtime smoke:
  - `analysis_id=WES_PROFILE_20260704_230713`
  - job stats: `all=1`, `fastp=2`, `bwa_mem=2`, `markdup=2`, `final_summary=1`, `total=8`
  - `shared/runs/WES_PROFILE_20260704_230713/reports/final_summary.tsv` exists with `S001` and `S002` `mock_success`
  - `shared/runs/WES_PROFILE_20260704_230713/logs/qsub/*.o/e` exists
  - `shared/runs/WES_PROFILE_20260704_230713/logs/events/snakemake_events.jsonl` has 14 lines and contains `qsub_submitted`/`qsub_success`

### Not run / why

- Optional DB smoke for `backend_event_url=http://backend:8000/api/events/snakemake` was not repeated in this task; T041 already verified backend POST and `/api/runs/{analysis_id}/rules`, while T042 scope was `cluster-generic` profile runtime.
- Real qsub was not run because `qsub/qstat` remain unavailable on `fengxian` and the demo is intentionally in mock mode.
- No `bio_wes_qsub` DAG, QC parser, frontend QC, or reanalysis UI work was done.

### Current git status

Work is on branch `codex/airflow/T086-pgta-airflow-logger`. Implementation commits `83fa789` and `cd22c90` were pushed and verified on the `fengxian` mirror; this handoff entry records the follow-up docs/status evidence update.

### Risks

- `snakemake-runner` is the supported runtime for this profile on `fengxian`; host Snakemake environments still do not contain `snakemake-executor-plugin-cluster-generic`.
- Generated WES smoke directories remain under `shared/runs/WES_PROFILE_*` on the server as ignored runtime evidence.
- The WES workflow remains mock-only and does not represent production WES parameters or real qsub scheduling.

### Open questions

- None for T042. Real qsub enablement should be separately planned after a server with `qsub/qstat` is available and authorized.

### Next recommended task

Proceed to T031: add a `bio_wes_qsub` Airflow DAG skeleton that invokes the verified `snakemake-runner` + `profiles/qsub` path for WES mock runs.

### Rollback notes

- Revert repository changes with normal `git revert`.
- If cleanup is needed, remove only generated WES mock run directories under `shared/runs/WES_PROFILE_*` after path verification.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-04 18:05 - Codex - T040/T041/T042 WES mock qsub observability

### Goal

Build the first WES mock Snakemake/qsub observability slice: a tiny WES Snakefile, a mock qsub submit wrapper that records qsub job id/stdout/stderr/events, and a qsub profile contract. Do not call real qsub, do not use real WES data, and keep runtime validation on `ssh fengxian`.

### Completed

- Added `pipelines/wes/workflow/Snakefile` with a two-sample mock chain: `fastp -> bwa_mem -> markdup -> final_summary`.
- Added tiny mock inputs and config under `pipelines/wes/`.
- Added `pipelines/common/qsub_submit.py` with `AIRFLOW_DEMO_QSUB_MODE=mock`.
- Mock wrapper reads Snakemake jobscript properties, creates stable `MOCK-*` qsub job ids, writes qsub stdout/stderr, writes JSONL events, optionally POSTs backend events, and records final success/failed status.
- Added `profiles/qsub/config.yaml` with `jobs=2`, `rerun-incomplete=true`, and explicit Snakemake env Python.
- Documented that `fengxian` currently lacks both `qsub/qstat` and `snakemake-executor-plugin-cluster-generic`; therefore direct wrapper smoke passes, while full `--profile profiles/qsub` runtime is blocked.

### Changed files

- `pipelines/common/qsub_submit.py`
- `pipelines/wes/workflow/Snakefile`
- `pipelines/wes/config/mock_config.yaml`
- `pipelines/wes/mock_data/S001.input.txt`
- `pipelines/wes/mock_data/S002.input.txt`
- `profiles/qsub/config.yaml`
- `pipelines/tests/test_qsub_submit.py`
- `pipelines/tests/test_wes_mock_contract.py`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote temp tests after tests-only patch | failed as expected | Missing `pipelines.common`, WES Snakefile, and qsub profile |
| remote temp `python -m unittest pipelines.tests.test_qsub_submit pipelines.tests.test_wes_mock_contract` | success | 5 tests OK |
| remote temp WES Snakemake dry-run | success | Snakemake 8.5.4 showed 8 jobs across all/fastp/bwa_mem/markdup/final_summary |
| remote temp direct mock wrapper smoke | success | Generated `MOCK-WES_20260704_DIRECT-12-bwa_mem-S001`, qsub stdout/stderr, result file, and submitted/success JSONL events |
| `snakemake --profile profiles/qsub` in remote temp | blocked | Snakemake executor choices are local/dryrun/touch; `cluster-generic` plugin missing |
| qsub/qstat probe on `fengxian` | not found | `command -v qsub` and `command -v qstat` returned empty |
| official mirror `git pull --ff-only` | success | `/home/jiucheng/project/airflow-demo` synced to implementation commit `a7f03f3` before runtime smoke |
| official mirror `docker compose -f docker-compose.yaml config --quiet` | success | Compose contract still renders |
| official mirror `docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 35 backend tests passed |
| official mirror Dockerized unittest for `pipelines.tests.*` | success | 5 WES/qsub contract tests OK |
| official mirror WES Snakemake dry-run | success | Job stats: all=1, fastp=2, bwa_mem=2, markdup=2, final_summary=1, total=8 |
| official mirror direct wrapper + backend POST | success | `WES_20260704_180650_MOCK` generated `MOCK-WES_20260704_180650_MOCK-12-bwa_mem-S001` |
| `GET /api/runs/WES_20260704_180650_MOCK/rules` | success | Returned `bwa_mem/S001=success`, qsub job id, stdout/stderr paths, and `return_code=0` |

### Tests

Remote-only evidence from `fengxian`:

- Unit/contract tests: `Ran 5 tests OK`.
- Backend image tests: `35 passed`.
- WES mock dry-run on official mirror: passed with 8 jobs.
- Direct mock qsub wrapper on official mirror with backend event POST: passed and wrote:
  - `shared/runs/WES_20260704_180650_MOCK/logs/qsub/bwa_mem.S001.o`
  - `shared/runs/WES_20260704_180650_MOCK/logs/qsub/bwa_mem.S001.e`
  - `shared/runs/WES_20260704_180650_MOCK/logs/events/snakemake_events.jsonl`
  - `shared/runs/WES_20260704_180650_MOCK/mock/result.txt`
- Backend rule query: `/api/runs/WES_20260704_180650_MOCK/rules` returned `bwa_mem/S001=success` with `qsub_jobid`, stdout/stderr paths, and `return_code=0`.

### Not run / why

- Full `--profile profiles/qsub` execution did not pass because neither Snakemake env has `snakemake-executor-plugin-cluster-generic`.
- Real qsub was not run because `qsub/qstat` are absent on `fengxian`.

### Current git status

Work is on branch `codex/airflow/T086-pgta-airflow-logger`. Implementation commit `a7f03f3` was pushed and validated on the `fengxian` mirror; this handoff entry includes the follow-up docs/status evidence update.

### Risks

- T042 should remain blocked until the cluster-generic executor plugin is installed in an isolated environment or added to a runtime image.
- The mock wrapper uses the Snakemake env Python explicitly; running it with system Python 3.6 fails because the script uses modern Python syntax.
- The WES workflow is mock-only and does not represent production WES parameters.

### Open questions

- Whether to unblock T042 by installing the executor plugin in a dedicated container image or by creating a separate Snakemake qsub runner environment on `fengxian`.

### Next recommended task

Unblock T042 by adding `snakemake-executor-plugin-cluster-generic` in an isolated runtime, then run `--profile profiles/qsub` end-to-end. After that, proceed to T031 `bio_wes_qsub` DAG skeleton.

### Rollback notes

- Revert repository changes with normal `git revert`.
- Remove only generated WES mock run directories under `shared/runs/WES_*` if cleanup is needed.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-04 01:18 - Codex - T045/T084 PGT-A dryrun and failure smoke

### Goal

Extend the existing PGT-A create -> submit -> Airflow -> sync chain with two controlled targets: `dryrun_cnv` for Snakemake CNV DAG parsing and `invalid_target` for failure/error-summary smoke. Keep PGT-A source/data mounts read-only, do not run real CNV/baseline_qc/qsub, and keep runtime validation on `ssh fengxian`.

### Completed

- Added controlled backend target support for `metadata`, `dryrun_cnv`, and `invalid_target`.
- Extended `bio_pgta` from metadata-only to target-aware tasks: `validate_request -> prepare_pgta_config -> run_pgta_target -> collect_pgta_artifact`.
- Added frontend target selector and submit support for created `dryrun_cnv` / `invalid_target` runs.
- Fixed `dryrun_cnv` config to use existing read-only WisecondorX XX/XY/gender references under `/data/project/CNV/PGT-A/refactor_validation_20260419/results_build_ref_v2_mask_only/reference`.
- Added dry-run Snakemake flags `--ignore-incomplete --rerun-triggers mtime` to avoid historical incomplete metadata interfering with DAG parsing.
- Updated API/DAG/frontend/runbook/testing/PGT-A plan docs and task/current-state/handoff docs.

### Changed files

- `backend/app/run_service.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_creation.py`
- `backend/tests/test_run_submit.py`
- `dags/bio_pgta.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_bio_pgta_dag.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote temp backend targeted tests after tests-only patch | failed as expected | metadata-only validation rejected `dryrun_cnv` and `invalid_target` |
| remote temp DAG tests after tests-only patch | failed as expected | target-aware runner/tasks not implemented yet |
| remote temp frontend test after tests-only patch | failed as expected | target selector/submit behavior missing |
| remote temp backend targeted tests after implementation | success | 10 tests passed |
| remote temp DAG tests after implementation | success | 11 tests OK |
| remote temp frontend Docker test after implementation | success | Vitest 7 passed |
| `git pull --ff-only` on `fengxian` | success | Mirror fast-forwarded to `f90b09c` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose still valid |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` on `fengxian` | success | 35 tests passed |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | Dockerized frontend test target passed |
| DAG unittest in Airflow image on `fengxian` | success | 11 tests OK |
| Airflow import check | success | `airflow dags list-import-errors` returned `No data found` |
| `docker compose restart airflow-api-server airflow-scheduler airflow-worker` | success | Safe restart only, no volume deletion |
| `dryrun_cnv` API smoke | success | `PGTA_20260703_170917_20E8F2`, Airflow/backend `success`, stdout recorded 7 dry-run jobs |
| `invalid_target` API smoke | success | `PGTA_20260703_170957_3DDEC3`, Airflow/backend `failed` as expected, non-null `error_summary` |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Backend suite: `35 passed`.
- Frontend Dockerized test target: passed.
- DAG tests: `Ran 11 tests OK`.
- `dryrun_cnv` smoke:
  - `analysis_id=PGTA_20260703_170917_20E8F2`
  - `dag_run_id=manual__PGTA_20260703_170917_20E8F2`
  - final status `success`
  - stdout log size 12677 bytes, stderr log size 89 bytes
  - artifact API returned `snakemake_stdout`, `snakemake_stderr`, `pgta_config_yaml`, `pgta_run_config`, `pgta_metadata_config`
- `invalid_target` smoke:
  - `analysis_id=PGTA_20260703_170957_3DDEC3`
  - `dag_run_id=manual__PGTA_20260703_170957_3DDEC3`
  - final status `failed`
  - `error_summary` is non-null and includes stderr path plus last error lines

### Not run / why

- No real CNV, baseline_qc, qsub, or QC parsing was run; out of scope for T045/T084.
- No custom Airflow Web plugin was added; existing FastAPI/frontend logs/artifacts/status APIs cover this smoke.
- No Docker volumes were deleted and no prune commands were run.

### Current git status

Implementation and smoke fix are on branch `codex/airflow/T086-pgta-airflow-logger`; verified code commit is `f90b09c`, followed by this docs/state update.

### Risks

- `invalid_target` currently proves the controlled failure/error-summary path. Snakemake reports the sentinel target in stderr, but the exact traceback shape is a CLI parsing detail and should not be treated as a production failure taxonomy.
- `dryrun_cnv` depends on the existing read-only reference path on `fengxian`; BS10610 migration must parameterize/check this path in Level 0 preflight.
- Services are left running for user review.

### Open questions

- Whether to parameterize the PGT-A demo reference root into `.env` before BS10610 migration, or keep it as a fengxian-only smoke assumption until the migration batch.

### Next recommended task

Run T041/T042 next for qsub submit wrapper/profile and qsub job-id observability, or T054/T056 if the next demo priority is QC/reanalysis UI.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`; do not use `down -v`.
- Revert repository changes with normal `git revert`.
- Do not use `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 23:48 - Codex - T051 PGT-A frontend submission flow

### Goal

Add the first frontend submission path for PGT-A: scan an allowlisted server FASTQ root, select samples, create a `created` run through FastAPI, then submit that run to Airflow from the detail toolbar. Keep the existing two-step create/submit model; do not add login, QC, dry-run/CNV, qsub, or new backend contracts.

### Completed

- Added `New PGT-A Run` panel to the existing single-page React workspace.
- Added form fields for project name, rawdata root, max samples, fixed `target=metadata`, optional email, and note.
- Added scan/create frontend API client functions for `POST /api/input/scan` and JSON `POST /api/runs`.
- Added selectable FASTQ candidate table and truncated-scan warning.
- Added `Submit to Airflow` action for `status=created` + `target=metadata`, using `POST /api/runs/{analysis_id}/actions/submit`.
- Preserved run list/detail, samples, rules, logs, artifacts, and sync UI.
- Updated frontend spec, task table, current state, handoff, and manifest docs.

### Changed files

- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/styles.css`
- `docs/06_FRONTEND_SPEC.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote temp `docker build --target test -f frontend/Dockerfile frontend` after adding tests only | failed as expected | 3 new tests failed because rawdata/project form and submit button did not exist |
| remote temp `docker build --target test -f frontend/Dockerfile frontend` after implementation | success | Vitest `5 passed` |
| `git diff --check` | success | Local non-runtime check only |
| `git pull --ff-only` on `fengxian` | success | Mirror fast-forwarded to T051 commits |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose still valid |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | failed once, then success | First failure was TypeScript test mock inference; fixed in `f5dae66`; production build then passed |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | Vitest `5 passed` |
| `docker compose -f docker-compose.yaml up -d postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker` | success | Frontend recreated with new image; services left running for user review |
| frontend/backend health probes | success | `http://127.0.0.1:12959/` returned React HTML; backend `/api/health` returned ok |
| API T051 smoke | success | Created/submitted `PGTA_20260703_154341_408A29`; sync ended `success`; metadata artifact/log readable |
| run list probe | success | `/api/runs?pipeline=pgta` contains `PGTA_20260703_154341_408A29`; total was 6 |
| final direct frontend test-stage run | success | `docker run --rm b1ffb26d16f7 npm test -- --run`; Vitest `5 passed` |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Frontend production Docker build passed.
- Frontend Dockerized Vitest target passed: `5 passed`; final direct test-stage run also passed `5 passed`.
- Real PGT-A metadata create/submit smoke passed:
  - `analysis_id=PGTA_20260703_154341_408A29`
  - `dag_run_id=manual__PGTA_20260703_154341_408A29`
  - `sync-airflow` status `success`
  - artifact API returned 5 items
  - metadata log tail returned 3 lines
- Frontend page is available at `http://fengxian:12959/`.

### Not run / why

- No browser automation screenshot was run; React behavior is covered by Dockerized Vitest and remote HTTP/API smoke.
- No login was implemented; out of scope.
- No dry-run/CNV/baseline_qc or invalid target failure smoke was run; T045/T084 remain next.
- No qsub wrapper/profile or qsub job-id events were implemented; T041/T042 remain pending.
- No QC panel or reanalysis UI was implemented; T054/T056 remain pending.

### Current git status

T051 code was verified on branch `codex/airflow/T086-pgta-airflow-logger` at `f5dae66`; the final docs/state commit records the smoke evidence.

### Risks

- Services are intentionally left running for user review; stop with `docker compose -f docker-compose.yaml down` only when done.
- The new submit UI triggers real `bio_pgta` metadata runs; it is still limited to `target=metadata`.
- The UI still uses demo-wide CORS and no auth; production-like access control remains future work.

### Open questions

- Whether the next frontend increment should add route-level navigation, or keep the single-page workspace until QC/reanalysis pages are ready.

### Next recommended task

Run T045/T084 next for PGT-A dry-run and invalid-target failure smoke, or T041/T042 if qsub job-id observability is the priority.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`; do not use `down -v`.
- Revert repository changes with normal `git revert`.
- Do not use `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 16:19 - Codex - T050/T057 frontend run detail v1

### Goal

Safely stop the running demo services on `fengxian`, then replace the nginx placeholder with a minimal React frontend for PGT-A run list/detail. The v1 UI must read existing runs, samples, logs, artifacts, Snakemake rule status, and provide a manual Airflow sync button. Do not implement login, sample creation, new DAG triggers, QC panels, or reanalysis.

### Completed

- Stopped current `fengxian` demo services with `docker compose -f docker-compose.yaml down`; `docker compose ps` was empty.
- Added Vite React + TypeScript frontend under `frontend/`.
- Replaced compose `frontend` placeholder with project image `airflow-demo/frontend:0.1.0`, still published on host port `12959`.
- Added frontend run list/detail workspace consuming existing backend APIs: runs, detail, samples, rules, logs, artifacts, and sync-airflow.
- Added backend CORS support via `BACKEND_CORS_ORIGINS`, defaulting to `*` for the demo.
- Added remote Dockerized frontend tests and a backend CORS test.
- Updated frontend, engineering, runbook, task, current state, handoff, and manifest docs.

### Changed files

- `.env.example`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/tests/test_cors.py`
- `docker-compose.yaml`
- `frontend/*`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml down` on `fengxian` | success | Safe stop only; no `down -v` or prune |
| `docker compose -f docker-compose.yaml build backend` before CORS implementation | success | Rebuilt red-test backend image |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_cors.py` before implementation | failed as expected | CORS preflight returned 405 |
| `docker build --target test -f frontend/Dockerfile frontend` before implementation | failed as expected | Missing `src/App.tsx` |
| `docker compose -f docker-compose.yaml config --quiet` | success | Compose rendered frontend build image and ports |
| `docker compose -f docker-compose.yaml build backend frontend` | success | Built `airflow-demo/backend:0.1.0` and `airflow-demo/frontend:0.1.0` |
| `docker build --target test -f frontend/Dockerfile frontend` | success | Vitest `2 passed` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_cors.py` | success | `1 passed` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` | success | `31 passed` |
| service startup on `fengxian` | success | Started postgres, redis, backend, frontend, airflow-api-server, airflow-scheduler, airflow-worker |
| `curl http://127.0.0.1:12959/` | success | Returned React HTML |
| `GET /api/runs?pipeline=pgta` | success | Returned existing PGT-A runs |
| `GET /api/runs/PGTA_20260703_054712_501D8B/rules` | success | Returned `all=success`, `collect_run_metadata=success` |
| metadata log/artifact/sample curls | success | Returned data for `PGTA_20260703_054712_501D8B` |
| Airflow `/health` | success | Metadatabase and scheduler healthy |
| CORS OPTIONS probe | success | HTTP 200, `access-control-allow-origin: *` |
| final `docker compose -f docker-compose.yaml down` | success | Safe stop only; `docker compose ps` empty |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Backend test suite passed: `31 passed`.
- Frontend Dockerized Vitest target passed: `2 passed`.
- Frontend production Docker build passed.
- React page served at `http://127.0.0.1:12959/`.
- Existing run `PGTA_20260703_054712_501D8B` exposed samples, metadata logs, artifacts, and rule statuses through backend APIs.

### Not run / why

- No frontend login was implemented; out of scope for v1.
- No PGT-A scan/create form was implemented; T051 remains next.
- No new PGT-A DAG run, dry-run target, CNV, baseline_qc, or invalid target smoke was run; T045/T084 remain pending.
- No QC panel or reanalysis UI was implemented; T054/T056 remain pending.
- No browser screenshot automation was run; component tests plus served HTML/API smoke were used.

### Current git status

Implementation is on branch `codex/airflow/T086-pgta-airflow-logger`; runtime smoke passed on `fengxian` at commit `403fa68`, followed by this docs/state update batch.

### Risks

- Frontend API base currently points browsers to `http://<host>:8000/api`; if a reverse proxy is later added, set `window.__AIRFLOW_DEMO_CONFIG__.apiBaseUrl` or `VITE_API_BASE_URL`.
- CORS default is `*` for demo ergonomics; tighten it before production-like deployment.
- `PGTA_20260703_054712_501D8B` has rule success rows from the Airflow-only event smoke, while the business run status remains `created` because that smoke did not call `sync-airflow`.

### Open questions

- Whether T051 should live in the same single-page workspace or become a separate `/submit` route once routing is introduced.

### Next recommended task

Run T051 next: add PGT-A server-path scan/create form using `POST /api/input/scan` and JSON `POST /api/runs`, then keep T045/T084 dry-run/failure smoke separate.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 13:49 - Codex - T026/T043 Snakemake event receiver and PGT-A logger POST

### Goal

Implement rule/job event ingestion for Snakemake logger events: FastAPI receives `/api/events/snakemake`, upserts biodemo `snakemake_rule_event`, exposes `/api/runs/{analysis_id}/rules`, and PGT-A Snakemake 9 logger optionally POSTs to backend while retaining JSONL fallback.

### Completed

- Added backend event receiver `POST /api/events/snakemake` with structured `RUN_NOT_FOUND` and validation errors.
- Added `GET /api/runs/{analysis_id}/rules` for frontend-ready rule/job status.
- Added idempotent upsert by `analysis_id/rule/sample_id/snakemake_jobid`; later success/failed events update the existing row.
- Added PGT-A Snakemake 9 logger backend POST via `backend_event_url`, with JSONL fallback on POST failure.
- Fixed logger job context backfill so Snakemake `job_finished/job_error` events without rule fields inherit rule/sample from earlier `job_info`.
- Added Airflow-only DAG conf passthrough for `backend_event_url`.
- Updated API, DB, DAG, Snakemake, logging, runbook, PGT-A plan, task, current state, and manifest docs.

### Changed files

- `backend/app/main.py`
- `backend/app/rule_event_service.py`
- `backend/tests/test_snakemake_events_api.py`
- `dags/pgta_airflow_runner.py`
- `dags/snakemake_logger_plugin_airflow_demo/__init__.py`
- `dags/tests/test_pgta_airflow_runner.py`
- `dags/tests/test_snakemake_logger_plugin.py`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml build backend` on `fengxian` | success | Rebuilt backend image with event tests/code |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_snakemake_events_api.py` before implementation | failed as expected | Missing endpoints returned 404 |
| Airflow runner unittest before implementation | failed as expected | `backend_event_url` not preserved/passed |
| Snakemake 9 plugin unittest before implementation | failed as expected | backend POST not called and fallback marker absent |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_snakemake_events_api.py` | success | `4 passed` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` | success | `30 passed` |
| Snakemake 9 plugin unittest after POST implementation | success | `4 tests OK` before context regression was added |
| T026/T043 first real smoke | partial | `PGTA_20260703_052742_C3A2F5` DAG success, but DB only got `info` rows; exposed missing job context backfill |
| Snakemake 9 plugin context regression before fix | failed as expected | `job_finished` without rule did not POST |
| Snakemake 9 plugin unittest after context fix | success | `5 tests OK` |
| Airflow unittest discover after context fix | success | `18 tests OK`, `5 skipped` in Airflow Python because Snakemake 9 interface is absent there |
| T026/T043 second real smoke | success | `PGTA_20260703_054712_501D8B` / `manual__PGTA_20260703_054712_501D8B_events` ended Airflow `success` |
| `GET /api/runs/PGTA_20260703_054712_501D8B/rules` | success | Returned `all=success`, `collect_run_metadata=success` |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; no `down -v` or prune |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Backend event API tests passed: `4 passed`.
- Full backend test suite passed: `30 passed`.
- Snakemake 9 logger plugin tests passed under `/biosoftware/miniconda/envs/snakemake9_env/bin/python`: `5 tests OK`.
- Airflow DAG/runner tests passed in Airflow Python: `18 tests OK`, `5 skipped`.
- Real PGT-A Airflow-only metadata event smoke passed:
  - `analysis_id=PGTA_20260703_054712_501D8B`
  - `dag_run_id=manual__PGTA_20260703_054712_501D8B_events`
  - Airflow state `success`
  - `run_metadata.tsv`: 11 lines
  - `snakemake_events.jsonl`: 22 lines
  - `snakemake_rule_summary.tsv`: 29 lines
  - rules API returned two success rows.

### Not run / why

- No frontend was implemented or tested; T057 remains next for visible run detail/rule table.
- No PGT-A dry-run/CNV/baseline_qc target was run; T045 remains pending.
- No qsub wrapper/profile was implemented; qsub job id and qsub stdout/stderr fields remain pending T041/T042.
- No DB migration was added; existing `snakemake_rule_event` schema was sufficient.

### Current git status

Implementation is on branch `codex/airflow/T086-pgta-airflow-logger`; code smoke passed on `fengxian` at commit `b917961`, followed by docs/state updates in this handoff batch.

### Risks

- Snakemake 9 emits some useful generic workflow/progress events without rule; backend intentionally ignores those and keeps them only in JSONL/Airflow XCom.
- `start_time` may remain null for some PGT-A rows because Snakemake `job_started` events do not always carry jobid/rule. Terminal success is still captured through `job_info -> job_finished` context backfill.
- `bio_pgta_airflow` is still manifest-only and does not replace the backend-triggered `bio_pgta` submit path.

### Open questions

- Whether `/api/runs/{analysis_id}/actions/submit` should eventually support `bio_pgta_airflow` for backend-created runs, or keep it as a diagnostic Airflow-only DAG.

### Next recommended task

Run T057 next: build PGT-A run detail UI that consumes run detail, samples, logs, artifacts, sync-airflow, and the new rules API. T045 dry-run and T041/T042 qsub wrapper remain separate follow-ups.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 07:56 - Codex - T036 PGT-A Airflow-only Snakemake 9 logger DAG

### Goal

Create an independent PGT-A Airflow-only metadata DAG using Snakemake 9.23.1 and a repo-local logger plugin, without changing the existing backend-triggered `bio_pgta` path or modifying PGT-A production code/environments.

### Completed

- Added DAG `bio_pgta_airflow` with `validate_request -> prepare_pgta_config -> run_snakemake9_with_logger -> collect_snakemake_events -> collect_metadata_artifact`.
- Added `pgta_airflow_runner.py` for manifest-only Airflow conf validation, PGT-A config generation, Snakemake 9 invocation, event JSONL parsing, summary TSV generation, and Airflow log/XCom summary.
- Added repo-local Snakemake logger plugin package `snakemake_logger_plugin_airflow_demo`.
- Added `.airflowignore` so Airflow does not parse DAG test files and create duplicate DAG IDs.
- Added tests for the new DAG, runner, and Snakemake 9 logger plugin.
- Added env knobs `PGTA_SNAKEMAKE9_BIN` and `AIRFLOW_DAGS_ROOT`.
- Updated engineering, DAG, Snakemake, logging, runbook, PGT-A plan, task, state, and manifest docs.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `dags/.airflowignore`
- `dags/bio_pgta_airflow.py`
- `dags/pgta_airflow_runner.py`
- `dags/snakemake_logger_plugin_airflow_demo/__init__.py`
- `dags/tests/test_bio_pgta_airflow_dag.py`
- `dags/tests/test_pgta_airflow_runner.py`
- `dags/tests/test_snakemake_logger_plugin.py`
- `SERVER_INFO.md`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| Airflow unittest before implementation on `fengxian` | failed as expected | Missing `bio_pgta_airflow` and `pgta_airflow_runner` |
| Snakemake 9 plugin test before implementation on `fengxian` | failed as expected | Missing `snakemake_logger_plugin_airflow_demo` |
| Airflow unittest after implementation | success | `13 tests OK`, `2 skipped` in Airflow Python because Snakemake 9 logger interface is not installed there |
| Snakemake 9 plugin unittest | success | `2 tests OK` with `/biosoftware/miniconda/envs/snakemake9_env/bin/python` |
| Snakemake 9 CLI logger help check | success | `--logger-airflow-demo-*` args discovered with `PYTHONPATH` |
| `docker compose -f docker-compose.yaml config --quiet` | success | Compose renders with new env vars |
| `airflow dags list-import-errors` | success | `No data found` after adding `dags/.airflowignore` |
| `airflow dags list | grep bio_pgta_airflow` | success | DAG listed |
| Airflow-only smoke run | success | `manual__PGTA_AIRFLOW_20260703_074844` ended success |
| artifact checks | success | `run_metadata.tsv`, `snakemake_events.jsonl`, and `snakemake_rule_summary.tsv` exist and are non-empty |
| XCom query | success | `snakemake_event_summary` contained `event_count=22`, status counts, and no failed jobs |

### Tests

Remote-only acceptance evidence on `fengxian`:

- DAG/runner unit tests passed in Airflow container.
- Logger plugin tests passed under Snakemake 9 Python.
- Snakemake 9 CLI discovered the repo-local plugin settings via `PYTHONPATH`.
- `bio_pgta_airflow` appeared in Airflow with no import errors.
- Real Airflow-only metadata smoke succeeded:
  - `analysis_id=PGTA_AIRFLOW_20260703_074844`
  - `dag_run_id=manual__PGTA_AIRFLOW_20260703_074844`
  - `run_metadata.tsv`: 11 lines
  - `snakemake_events.jsonl`: 22 lines
  - Airflow task log printed event count and status counts
  - XCom contained `snakemake_event_summary`

### Not run / why

- No frontend was implemented or tested.
- No FastAPI event receiver was implemented; T026 remains todo.
- No biodemo `snakemake_rule_event` writes were implemented; T043 remains todo.
- No PGT-A dry-run/CNV/baseline_qc target was run.
- No custom Airflow Web plugin was implemented; first UI surface is Airflow task log + XCom.

### Current git status

Work is on branch `codex/airflow/T086-pgta-airflow-logger`. Runtime code smoke passed on `fengxian` at commit `a5e6737`; final docs/state commit follows this handoff.

### Risks

- `bio_pgta_airflow` is intentionally manifest-only and does not create biodemo DB records.
- Logger events are currently JSONL + Airflow log/XCom only; backend POST is reserved for T026/T043.
- Snakemake event records expose useful workflow/job messages, but some log events do not include rule/sample fields.
- Airflow CLI `--conf` JSON is painful through Windows SSH quoting; use a temp JSON file plus `scp` for future manual triggers.

### Open questions

- Whether to make `/api/runs/{analysis_id}/actions/submit` optionally trigger `bio_pgta_airflow` after T026/T043, or keep it as a manual Airflow-only diagnostic DAG.

### Next recommended task

Run T026/T043 next: implement FastAPI `/api/events/snakemake` upsert and optionally let the logger plugin POST events while retaining JSONL fallback.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 02:13 - Codex - T025/T062 PGT-A diagnostics API

### Goal

Add backend diagnostics for PGT-A metadata runs: explicit Airflow state sync, fixed PGT-A log tail endpoints, dynamic metadata artifact listing, and run-level error summary extraction. Do not build frontend, dry-run target, Snakemake event receiver, qsub integration, or DB migration.

### Completed

- Added `POST /api/runs/{analysis_id}/actions/sync-airflow`.
- Added `GET /api/runs/{analysis_id}/logs?stream=stdout|stderr|metadata&tail=...`.
- Added `GET /api/runs/{analysis_id}/artifacts`.
- Added path safety checks so logs/artifacts must stay inside `CONTAINER_SHARED_ROOT` and the run `workdir`.
- Added missing log handling with structured `LOG_NOT_FOUND`.
- Added run-level failed DAG summary extraction from `logs/snakemake.stderr.log` into `analysis_run.error_summary`.
- Kept artifact discovery dynamic; no artifact table writes and no Alembic migration.
- Updated API, logging, runbook, task, current state, and manifest docs.

### Changed files

- `backend/app/diagnostics_service.py`
- `backend/app/main.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/05_API_CONTRACT.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml build backend` on `fengxian` before red test | success | Rebuilt image with red tests |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_run_diagnostics.py` before implementation | failed as expected | 6 failures: missing sync/log/artifact endpoints and structured errors |
| `docker compose -f docker-compose.yaml build backend` after implementation | success | Rebuilt diagnostics implementation |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_run_diagnostics.py` | success | `6 passed in 0.91s` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` | success | `26 passed in 1.56s` |
| `docker compose -f docker-compose.yaml config --quiet` | success | Compose still valid |
| service startup for postgres/redis/backend/Airflow | success | Used existing volumes; no `down -v` |
| `curl /api/health` and Airflow `/health` | success | Backend ok; Airflow metadatabase and scheduler healthy |
| `POST /api/runs/PGTA_20260702_171533_9A85B1/actions/sync-airflow` | success | Returned `status=success`, `error_summary=null` |
| `GET /api/runs/PGTA_20260702_171533_9A85B1/logs?stream=metadata&tail=3` | success | Returned last metadata lines from `run_metadata.tsv` |
| `GET /api/runs/PGTA_20260702_171533_9A85B1/logs?stream=stderr&tail=5` | success | Returned Snakemake stderr tail |
| `GET /api/runs/PGTA_20260702_171533_9A85B1/artifacts` | success | Returned metadata, stdout/stderr, config YAML, metadata config |
| `POST /api/runs/PGTA_20260702_171200_A68C19/actions/sync-airflow` | success | Returned `status=failed`, non-null `error_summary` |
| missing log probe for `PGTA_20260702_162531_74CE91` | success | HTTP 404 with `LOG_NOT_FOUND` |
| DB latest run query | success | success/failed/created states matched expected runs |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; compose ps empty |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Diagnostics unit tests passed: `6 passed`.
- Full backend test suite passed: `26 passed`.
- Real success run synced to `success`; real historical failed run synced to `failed` and wrote `error_summary`.
- Log and artifact APIs returned real files from `shared/runs`.
- Missing log returned structured `LOG_NOT_FOUND`.
- Path traversal/workdir safety is covered by unit test.

### Not run / why

- Frontend was not implemented or tested; this remains T057.
- PGT-A dry-run and invalid target failure smoke were not implemented; this remains T045/T084.
- Snakemake event receiver and rule/qsub-level errors were not implemented; this remains T026/T043.
- Airflow task-log API scraping was not implemented; current summary uses Snakemake stderr only.
- No DB migration was run or needed beyond existing Alembic head.

### Current git status

Implementation is on branch `codex/backend/T025-T062-logs-artifacts-sync` at code commit `25380e3`; final docs/state commit is expected before merging to `main`.

### Risks

- Historical failed run `PGTA_20260702_171200_A68C19` failed because of an Airflow PythonOperator bug, but current run-level summary intentionally reads Snakemake stderr first; it proves summary storage, not full Airflow task root-cause extraction.
- Artifact URLs for config files are reserved future view URLs; current implemented readable log URLs are stdout/stderr/metadata.
- `run_metadata.tsv` still contains tool-version probe errors for samtools/WisecondorX; that comes from the PGT-A metadata rule and was already present in the successful metadata smoke.

### Open questions

- Whether T045 should fix PGT-A metadata provenance/tool-version probes before adding dry-run, or leave that as a separate cleanup.

### Next recommended task

Run T045 next for PGT-A dry-run target, or T057 if the priority is visible demo UI using the newly available log/artifact/status APIs.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 01:19 - Codex - T027/T035 PGT-A submit to bio_pgta metadata

### Goal

Move an existing `pgta` run from `analysis_run.status=created` to the first Airflow executable path: submit it through FastAPI, trigger Airflow DAG `bio_pgta`, generate run-local PGT-A metadata config, and execute only the lightweight metadata target. Do not implement frontend, CNV, dry-run expansion, log API, or failure summary extraction.

### Completed

- Added `POST /api/runs/{analysis_id}/actions/submit`.
- Restricted submit to `pipeline=pgta`, `status=created`, and `target=metadata`.
- Triggered Airflow through the existing `AirflowClient`, with deterministic `dag_run_id=manual__<analysis_id>`.
- Updated biodemo `analysis_run.status` to `submitted`, wrote `dag_run_id`, and recorded a `run_action`.
- Added Airflow DAG `bio_pgta` with `validate_request -> prepare_pgta_config -> run_metadata -> collect_metadata_artifact`.
- Added PGT-A metadata runner that reads `samples.selected.tsv`, writes run-local `config.yaml` and `config/pgta_metadata_config.json`, runs Snakemake from `/opt/pipelines/PGT_A`, and stores stdout/stderr plus `logs/run_metadata.tsv`.
- Made created run workdirs/config dirs group-writable so Airflow UID `50000:0` can write metadata outputs.
- Fixed an Airflow task variable shadowing bug that caused the first DAG smoke to fail after metadata generation.
- Updated API, DAG, runbook, testing, PGT-A plan, task, current state, and handoff docs.

### Changed files

- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/tests/test_run_creation.py`
- `backend/tests/test_run_submit.py`
- `dags/bio_pgta.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_bio_pgta_dag.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_run_submit.py` before implementation | failed as expected | Submit endpoint did not exist yet, returned 404 |
| `docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint python airflow-scheduler -m unittest discover -s /opt/airflow/dags/tests -v` before implementation | failed as expected | `bio_pgta` and `pgta_metadata_runner` were not importable |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose rendered with backend, Airflow, PGT-A read-only mounts |
| `docker compose -f docker-compose.yaml build backend` on `fengxian` | success | Rebuilt backend image |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` on `fengxian` | success | `20 passed in 1.08s` |
| Airflow DAG unittest via `--entrypoint python` on `fengxian` | success | `6 tests OK` after the task shadowing fix |
| Airflow `py_compile` with `PYTHONPYCACHEPREFIX=/tmp/pycache` | success | Needed because mounted DAG directory is read-only for pycache writes |
| Service startup on `fengxian` | success | Started postgres, redis, backend, airflow-api-server, airflow-scheduler, airflow-worker |
| `curl /api/health`, `/api/health/db`, and Airflow `/health` | success | Backend DB and Airflow scheduler/metadatabase healthy |
| `airflow dags list | grep bio_pgta` | success | `bio_pgta` listed and not paused |
| Submit smoke for `PGTA_20260702_171200_A68C19` | Airflow failed | Metadata generated, then `collect_metadata_artifact` failed due PythonOperator variable shadowing |
| Submit smoke for `PGTA_20260702_171533_9A85B1` | success | Airflow run `manual__PGTA_20260702_171533_9A85B1` ended `success` |
| `find shared/runs/PGTA_20260702_171533_9A85B1 -maxdepth 4 -type f` | success | Found `config.yaml`, `config/pgta_metadata_config.json`, selected manifest, Snakemake logs, and `logs/run_metadata.tsv` |
| `head -5 logs/run_metadata.tsv` | success | Metadata file exists; git fields show permission errors but task succeeded |
| biodemo DB latest run query | success | `PGTA_20260702_171533_9A85B1|submitted|t|pgta` |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Backend test suite passed: `20 passed`.
- Airflow DAG tests passed: `6 tests OK`.
- Compose config and DAG py_compile passed.
- `bio_pgta` appeared in Airflow and was unpaused.
- Submit endpoint triggered `manual__PGTA_20260702_171533_9A85B1`.
- Airflow DAG state was `success`.
- `shared/runs/PGTA_20260702_171533_9A85B1/logs/run_metadata.tsv` exists.
- biodemo DB updated the run to `submitted` and `dag_run_id` non-null.

### Not run / why

- Frontend was not implemented or tested; still later T057.
- Backend log/artifact API and error summary extraction were not implemented; still T025/T062.
- PGT-A dry-run target and invalid target failure smoke were not implemented; still T045/T084.
- Airflow success/failed status is not yet written back to biodemo DB; current DB terminal state after submit is `submitted`.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was run.

### Current git status

Implementation commits were pushed on `codex/airflow/T027-T035-pgta-submit-metadata`; tested code commit is `9758c7a`. Final state-doc commit is expected before merging to `main`.

### Risks

- `run_metadata.tsv` currently records permission errors for `git_branch` and `git_commit` because the Airflow container environment cannot run the PGT-A metadata rule's git probe cleanly. The metadata target still succeeded; fix provenance separately if needed.
- The first failed smoke run `PGTA_20260702_171200_A68C19` remains in Airflow as failure evidence.
- Submit is intentionally not idempotent for already submitted runs; repeated submit returns validation error because status is no longer `created`.

### Open questions

- Whether to add an Airflow completion callback or polling worker so biodemo DB can move from `submitted` to `success`/`failed`.

### Next recommended task

Run T025/T062 next: implement log/artifact API and error summary extraction, then use that for dry-run/failure smoke and frontend run detail.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 00:28 - Codex - T022/T024 PGT-A server-path project creation

### Goal

Replace the old upload/sample-sheet plan with PGT-A server-path sample discovery: scan existing FASTQ paths under an allowlisted rawdata root, select samples, create a biodemo `analysis_run` and `sample` rows, and write a selected manifest. Do not trigger Airflow, write a DAG, run Snakemake, or build frontend pages.

### Completed

- Added backend `POST /api/input/scan` for `pipeline=pgta`, with `INPUT_SCAN_ROOTS` allowlist enforcement and R1/R2 FASTQ pairing.
- Added JSON `POST /api/runs` for PGT-A `target=metadata`, creating `analysis_run.status=created`, `sample` rows, `samples.selected.tsv`, and `request.json`.
- Added `GET /api/runs`, `GET /api/runs/{analysis_id}`, and `GET /api/runs/{analysis_id}/samples`.
- Kept `dag_run_id=null`; no Airflow DAG run is triggered in this phase.
- Added backend read-only PGT-A data mount and `INPUT_SCAN_ROOTS` env wiring.
- Updated API, architecture, engineering, frontend, DAG, testing, runbook, task, and state docs to use server-path scan instead of sample upload.
- Tightened `.gitignore` so generated `shared/runs/*`, `shared/uploads/*`, `shared/reports/*`, and `shared/logs/*` contents stay untracked while `.gitkeep` remains tracked.

### Changed files

- `.env.example`
- `.gitignore`
- `backend/app/config.py`
- `backend/app/input_scanner.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/run_service.py`
- `backend/tests/test_input_scanner.py`
- `backend/tests/test_input_scan_api.py`
- `backend/tests/test_run_creation.py`
- `docker-compose.yaml`
- `docs/01_SYSTEM_ARCHITECTURE.md`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/03_TASK_DESIGN.md`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/15_MULTI_AGENT_BOUNDARIES.md`
- `docs/17_DEMO_SCRIPT.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose run --rm --no-deps backend pytest -q` on `fengxian` before implementation build | failed as expected | `ModuleNotFoundError: No module named 'app.input_scanner'` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Rendered backend scan env and PGT-A read-only data mount |
| `docker compose -f docker-compose.yaml build backend` on `fengxian` | success | Rebuilt `airflow-demo/backend:0.1.0` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` on `fengxian` | success | `17 passed in 0.97s` |
| `docker compose -f docker-compose.yaml up -d postgres` on `fengxian` | success | Postgres healthy |
| `docker compose -f docker-compose.yaml run --rm biodemo-db-init` on `fengxian` | success | Repeat run altered/granted existing role/database |
| `docker compose -f docker-compose.yaml run --rm backend alembic upgrade head` on `fengxian` | success | No pending migration output, schema already at head |
| `docker compose -f docker-compose.yaml up -d backend` on `fengxian` | success | Backend healthy |
| `curl http://127.0.0.1:8000/api/health` and `/api/health/db` | success | Both returned `{"status":"ok"}` |
| API smoke script for `/api/input/scan` and `/api/runs` | API success, shell exit nonzero | API returned scan 5 candidates, `truncated=true`, create 201 for `PGTA_20260702_162531_74CE91`; PowerShell heredoc CRLF caused trailing `NameError: name 'PY' is not defined` after success |
| `curl /api/runs/PGTA_20260702_162531_74CE91` | success | status `created`, `dag_run_id=null`, sample_count 2, input_mode `server_path_scan` |
| `curl /api/runs/PGTA_20260702_162531_74CE91/samples` | success | 2 samples, status `pending`, qc_status `unknown`, fq1/fq2 paths present |
| `psql` latest run query | success | `PGTA_20260702_162531_74CE91|created|t|pgta` |
| `wc -l samples.selected.tsv` and `head -n 1` | success | 3 lines total; header `sample_id R1 R2 source_dir` |
| `test -f request.json` | success | request file exists |
| `docker compose -f docker-compose.yaml ps` before down | success | Only postgres and backend were running; no Airflow services |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; no `-v` or prune |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Dockerized backend tests passed: `17 passed`.
- Compose config passed.
- Backend health and DB health passed.
- `/api/input/scan` found candidates under `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28`.
- `/api/runs` created `PGTA_20260702_162531_74CE91` with 2 selected samples, status `created`, and `dag_run_id=null`.
- DB and generated files were verified; no Airflow containers were started for the smoke.

### Not run / why

- Airflow trigger and `bio_pgta` DAG were not run; this remains T027/T035.
- Snakemake and PGT-A metadata/dry-run/failure smoke were not run; this remains T045/T084.
- Frontend UI was not implemented or tested; this remains T051/T052/T057.
- Local pytest/Docker/Snakemake tests were not run by project rule; local checks were limited to Git, diff, and docs keyword checks.

### Current git status

Implementation commit `9928b9c` passed remote runtime verification on branch `codex/backend/T022-T024-server-path-runs`; final state-doc and `.gitignore` tightening were merged forward to `main`.

### Risks

- The scan algorithm is intentionally conservative and pairs direct-child FASTQ files by R1/R2 naming; unusual PGT-A layouts may need another parser rule after real examples are reviewed.
- Smoke created a persistent biodemo `created` run and shared output under `shared/runs/PGTA_20260702_162531_74CE91`; it is ignored by Git and can be left as smoke evidence.
- `target=metadata` is the only supported create-run target before DAG integration.

### Open questions

- Whether T027 should trigger Airflow from an existing `created` run only, or also allow create-and-trigger in one API call after the safer two-step path is stable.

### Next recommended task

Run T027/T035: trigger Airflow `bio_pgta` from an existing `created` run, generate PGT-A config from `samples.selected.tsv`, and keep execution limited to metadata target.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repo changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-02 23:49 - Codex - T021/T023 biodemo DB and Airflow client foundation

### Goal

Implement the P2 backend foundation only: biodemo SQLAlchemy/Alembic schema, repeatable DB init service, minimal Airflow REST client, and dependency health endpoints. Do not implement PGT-A, DAGs, React pages, or run submission APIs.

### Completed

- Added SQLAlchemy 2.0 models for `pipeline`, `analysis_run`, `sample`, `snakemake_rule_event`, `qc_metric`, `artifact`, and `run_action`.
- Added Alembic environment and initial migration `20260702_0001_initial_biodemo_schema.py`.
- Added repeatable Compose one-shot service `biodemo-db-init` to create/update `BIODEMO_USER` and `BIODEMO_DB`.
- Added backend `AirflowClient` with `health`, `list_dag_runs`, `get_dag_run`, and `trigger_dag_run`.
- Added `GET /api/health/db` and `GET /api/health/airflow`.
- Added `AIRFLOW_API_USERNAME` / `AIRFLOW_API_PASSWORD` env wiring.
- Added `backend/pip.conf` using the TUNA PyPI mirror and changed the backend image to install dependencies into `/opt/venv`.
- Verified on `fengxian`; then stopped services with `docker compose -f docker-compose.yaml down` only.

### Changed files

- `.env.example`
- `backend/Dockerfile`
- `backend/pip.conf`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/20260702_0001_initial_biodemo_schema.py`
- `backend/app/airflow_client.py`
- `backend/app/config.py`
- `backend/app/db.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/requirements.txt`
- `backend/requirements-dev.txt`
- `backend/tests/test_airflow_client.py`
- `backend/tests/test_health_dependencies.py`
- `backend/tests/test_models_metadata.py`
- `docker-compose.yaml`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| red probe importing `app.models` on `fengxian` | failed as expected | `ModuleNotFoundError: No module named 'app.models'` before implementation |
| `docker compose -f docker-compose.yaml config --quiet` | success | Included `biodemo-db-init` service |
| `docker compose -f docker-compose.yaml build backend` | success | After `backend/pip.conf`, pip used `https://pypi.tuna.tsinghua.edu.cn/simple`; install step took about 11s |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` | success | `9 passed` |
| `docker compose -f docker-compose.yaml up -d postgres` | success | Postgres healthy |
| `docker compose -f docker-compose.yaml run --rm biodemo-db-init` | success | First run created role/database; repeat run only altered role/granted schema privileges |
| `docker compose -f docker-compose.yaml run --rm backend alembic upgrade head` | success | Applied revision `20260702_0001`; repeat run succeeded |
| `psql` table list in `biodemo` | success | Found `alembic_version` plus 7 core business tables |
| `docker compose -f docker-compose.yaml up -d redis airflow-api-server airflow-scheduler airflow-worker backend` | success | Started backend and Airflow basics for smoke only |
| `curl http://127.0.0.1:8000/api/health` | success | Returned `{"status":"ok"}` |
| `curl http://127.0.0.1:8000/api/health/db` | success | Returned `{"status":"ok"}` |
| `curl http://127.0.0.1:12958/health` | success | Airflow metadatabase and scheduler healthy |
| `curl http://127.0.0.1:8000/api/health/airflow` | success | Backend returned Airflow health payload |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; no volume deletion |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Dockerized backend tests passed: `9 passed`.
- `biodemo-db-init` and Alembic migration are repeatable.
- `biodemo` contains `pipeline`, `analysis_run`, `sample`, `snakemake_rule_event`, `qc_metric`, `artifact`, and `run_action`.
- Backend health, DB health, direct Airflow health, and backend Airflow health all passed.

### Not run / why

- PGT-A metadata/dry-run/failure smoke was not run; that remains T027/T035/T045/T057/T084.
- No `bio_pgta` DAG was written or imported.
- No React/frontend functional page was implemented.
- No `/api/runs` submission/list/detail logic was implemented.
- No host-level Python dependency install was run; server-side installs remain Dockerized, and any future host Python work must use a venv.

### Current git status

Implementation was verified on task branch `codex/backend/T021-T023-db-airflow-client` at code commit `5e9065d`. This handoff/state-doc update is expected as the final docs commit before merging/pushing `main`.

### Risks

- The backend image currently includes `pytest` and tests because this early demo needs Dockerized remote tests; later production image slimming can split runtime and test targets.
- `AIRFLOW_API_PASSWORD` reuses the demo Airflow admin password in the remote untracked `.env`; do not commit or print it.
- Airflow triggerer remains absent; `/health` reports triggerer null, which is acceptable for current CeleryExecutor smoke.
- The initial schema is now applied in the persistent Postgres volume; use normal Alembic forward migrations for future changes, not destructive resets.

### Open questions

- Whether T024 should expose DB-backed `/api/runs` read endpoints first, or whether T022 upload/parser should land before any run listing UI contract.

### Next recommended task

Run T022 for mock sample upload/parser, then T024 for run list/detail/status APIs. Keep PGT-A DAG work behind T027/T035/T045/T057 after backend run contracts exist.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repo changes with a normal Git revert.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-02 23:03 - Codex - T011 Airflow 12958 smoke

### Goal

Move Airflow host access to port `12958`, move Docker nginx/frontend placeholder to `12959`, initialize Airflow metadata/admin, and verify the base Docker Compose services on `fengxian`.

### Completed

- Updated Compose defaults: `AIRFLOW_PORT=12958`, `FRONTEND_PORT=12959`.
- Added `airflow-init` one-shot service for Airflow DB migration and admin user creation.
- Kept Postgres and Redis internal-only; no `5432:5432` or `6379:6379` host port mapping was added.
- Updated remote `.env` with new non-secret port/admin keys and generated an Airflow admin password without printing it.
- Verified `12958`, `12959`, `8000`, `8025`, `1025`, `5432`, and `6379` were free before smoke; `3000` remains occupied by a non-project next-server.
- Ran `airflow-init`; Airflow metadata migration completed and admin user `admin` was created.
- Started postgres, redis, mailhog, backend, frontend, airflow-api-server, airflow-scheduler, and airflow-worker.
- Verified backend `/api/health`, frontend placeholder, MailHog UI, and Airflow `/health`.
- Stopped services with `docker compose -f docker-compose.yaml down`; no `-v`, prune, or volume deletion was used.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `docs/01_SYSTEM_ARCHITECTURE.md`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/infra/T011-airflow-12958` | success | Task branch for local edits |
| `docker compose config --quiet` on `fengxian` | success | Rendered Airflow `12958->8080`, frontend `12959->80`, backend `8000->8000`, MailHog `1025/8025` |
| remote port probe with `ss -lnt` | success | `12958/12959/8000/8025/1025/5432/6379` free; `3000` busy by non-project next-server |
| `docker compose -f docker-compose.yaml up airflow-init` | success | Airflow DB migration completed; admin user `admin` created |
| `docker compose -f docker-compose.yaml up -d postgres redis mailhog backend frontend airflow-api-server airflow-scheduler airflow-worker` | success | All base services started |
| `curl http://127.0.0.1:8000/api/health` | success | Returned `{"status":"ok"}` |
| `curl http://127.0.0.1:12959/` | success | Returned `airflow-demo frontend placeholder` |
| `curl http://127.0.0.1:8025/` | success | Returned MailHog HTML page |
| `curl http://127.0.0.1:12958/health` | success | Airflow metadatabase and scheduler healthy |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; no volume deletion |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Compose config passed for commit `9c640dc`.
- Airflow `/health` passed at `127.0.0.1:12958`.
- Docker nginx/frontend placeholder passed at `127.0.0.1:12959`.
- Backend health and MailHog HTTP GET passed.
- `docker compose ps` after down showed no running airflow-demo services.

### Not run / why

- PGT-A DAG, Snakemake metadata/dry-run, and failure smoke were not run; they remain later T027/T035/T045/T057/T084 work.
- React functional page was not implemented or tested; frontend is still Docker nginx placeholder only.
- biodemo DB migration was not implemented or run; T021 remains next.
- Airflow API client was not implemented; T023 remains next.

### Current git status

Implementation commit `9c640dc` was pushed to `origin/main` and pulled into `fengxian:/home/jiucheng/project/airflow-demo`. A follow-up state-doc commit is expected after this handoff update.

### Risks

- Airflow admin password exists only in the remote untracked `.env`; do not commit or print it.
- The Airflow triggerer is not running, so `/health` reports triggerer status as null; this is acceptable for the current CeleryExecutor smoke.
- Host port `3000` belongs to a non-project next-server and must not be stopped by airflow-demo tasks.
- PowerShell-to-SSH here-strings can introduce CRLF issues; prefer single-line SSH commands or CR-stripped bash scripts for future remote runs.

### Open questions

- Whether to keep Airflow reachable directly on `12958` for the demo, or later hide it behind a Docker nginx reverse proxy after frontend/API auth stabilizes.

### Next recommended task

Run T021 for biodemo DB models/migrations, then T023 for the FastAPI Airflow API client. Do not jump directly to PGT-A metadata smoke until backend DB/API basics are in place.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repo changes with a normal Git revert if needed.
- Do not run `docker compose down -v`, `docker system prune`, or `docker volume prune`.

## 2026-07-02 22:38 - Codex - fengxian host nginx inventory

### Goal

Record the existing host-level nginx on `fengxian` as deployment environment information without changing nginx configuration or service state.

### Completed

- Verified `/usr/sbin/nginx` exists and is executable on `fengxian`.
- Recorded host nginx path and version in `SERVER_INFO.md`.
- Added a deployment runbook note that host nginx is only a future reverse-proxy candidate for airflow-demo, not currently configured by this project.

### Changed files

- `SERVER_INFO.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `ssh fengxian '/usr/sbin/nginx -v 2>&1; test -x /usr/sbin/nginx && ls -l /usr/sbin/nginx'` | success | Returned `nginx version: nginx/1.14.0 (Ubuntu)` and executable path metadata |

### Tests

Remote-only read probe passed on `fengxian`; no local runtime test was run.

### Not run / why

- No nginx config test was run because airflow-demo does not yet manage host nginx.
- No nginx reload/restart was run.
- No Docker, Airflow, backend, frontend, DB, or Snakemake runtime test was needed for this documentation-only update.

### Current git status

Documentation changes are pending local commit/push at the time of this handoff entry.

### Risks

- Host nginx exists, but no airflow-demo server block or reverse proxy routing has been designed or applied.
- Future reverse-proxy work must avoid interrupting existing host services.

### Open questions

- Whether T011 or a later infra task should add a dedicated nginx reverse-proxy plan for backend, frontend, Airflow, and MailHog access.

### Next recommended task

Continue with T011 Airflow initialization first; handle host nginx reverse proxy as a separate infra task after service ports and auth behavior are stable.

### Rollback notes

This update is documentation only. Roll back with a normal Git revert if needed; do not edit or reload host nginx as part of rollback.

## 2026-07-02 22:47 - Codex - Docker image cleanup and tag pinning

### Goal

Clean duplicate/dangling `<none>` Docker images on `fengxian`, avoid implicit `latest` for airflow-demo images, and verify required compose images can be pulled or built without starting services.

### Completed

- Inspected running containers, all images, dangling images, compose images, latest-tag images, and Docker disk usage on `fengxian`.
- Removed 37 dangling `<none>:<none>` image IDs using exact `docker image rm` IDs.
- Did not run `docker system prune`, `docker volume prune`, or `docker compose down -v`.
- Did not touch running containers: `cosmetic-db-web` and `yunse-bio`.
- Did not delete non-project `latest` images such as `yunse-bio:latest` or `fischbachlab/*:latest`.
- Added explicit backend image tag `airflow-demo/backend:0.1.0` to compose and `.env.example`.
- Rebuilt backend on `fengxian` with the fixed tag and removed old project tag `airflow-demo-backend:latest`.
- Verified `docker compose config --images` now uses explicit tags and no airflow-demo `latest`.
- Pulled external compose images successfully: Airflow, Postgres, Redis, MailHog, nginx.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker ps -a` / `docker images` / `docker images --filter dangling=true` | success | Found 37 dangling images; found project backend image using implicit `latest` |
| `docker image rm <37 dangling ids>` | success | Dangling images reduced to zero; no force used |
| `docker system df` | success | Images count dropped from 54 to 17; no volume cleanup performed |
| `docker compose config --images` | success | Shows `airflow-demo/backend:0.1.0`; no project `latest` image |
| `docker compose build backend` | success | Built/tagged backend as `airflow-demo/backend:0.1.0` using cached layers |
| `docker image rm airflow-demo-backend:latest` | success | Removed old project latest tag only |
| `docker compose pull postgres redis mailhog frontend airflow-api-server airflow-scheduler airflow-worker` | success | Pulled external compose images; scheduler/worker reused Airflow image |
| image inspect loop | success | Verified Airflow, postgres, redis, mailhog, nginx, and backend images exist |
| `docker compose ps` | success | No airflow-demo containers running after checks |

### Tests

Remote-only evidence on `fengxian`:

- Dangling image list is empty after cleanup.
- `docker compose config --quiet` passed.
- Required compose images are present locally.
- `docker images` has no `airflow-demo*:latest`.

### Not run / why

- Airflow containers were not started; this task only checked image availability and cleanup.
- No frontend app container was built; frontend is still nginx placeholder only.
- No database migration was run.
- No volume cleanup was run, by project safety rule.

### Current git status

Code/docs changes for explicit backend image tag are committed and pushed as `07a63fa`; state docs from this cleanup are expected to be committed and pushed next.

### Risks

- Docker still reports reclaimable space from unused non-project images and unused volumes, but those were intentionally left untouched.
- Several non-project `latest` images remain on `fengxian`; deleting or retagging them needs separate owner confirmation.

### Open questions

- Whether airflow-demo should later use an internal registry or image digest pinning for stricter reproducibility.
- Whether to configure Docker registry mirrors for future Airflow/base-image pulls.

### Next recommended task

Proceed to T011: start and initialize Airflow services using the already pulled `apache/airflow:2.9.3-python3.11` image, then verify Airflow `/health`.

### Rollback notes

- The removed dangling images had no tags; rollback would require rebuilding or repulling the workloads that produced them.
- Revert the backend tag change with a normal Git revert if needed; do not force push.

## 2026-07-02 22:24 - Codex - T010/T012/T013/T014/T020 fengxian base skeleton

### Goal

Build the fengxian base runtime surface before PGT-A DAG/frontend work: user-level Docker Compose v2 readiness, GitHub mirror sync, Docker Compose service skeleton, shared directory contract, and minimal FastAPI `/api/health`.

### Completed

- Added minimal FastAPI backend at `backend/app/main.py` with `GET /api/health -> {"status":"ok"}`.
- Added backend Dockerfile and pinned minimal backend requirements.
- Added `docker-compose.yaml` with fixed `172.30.10.0/24` network and services: postgres, redis, mailhog, backend, frontend placeholder, airflow-api-server, airflow-scheduler, airflow-worker.
- Added tracked shared directory placeholders while keeping runtime contents ignored.
- Updated `.env.example`, engineering spec, API contract, deployment runbook, testing rules, agent workflow, and PGT-A plan.
- Added project constraint: local Windows repo is for editing/Git/docs only; runtime tests are remote-only.
- Re-ran fengxian Level 0 preflight: Docker 20.10.21, PGT-A/Snakemake paths readable, `172.30.10.0/24` non-conflicting.
- Installed Docker Compose v2.24.7 as a user-level CLI plugin at `/home/jiucheng/.docker/cli-plugins/docker-compose`.
- After user correction, replaced the plugin using local Windows GitHub Release download plus `scp` to fengxian; final plugin SHA256 is `19c9deb6f4d3915f5c93441b8d2da751a09af82df62d55eab097c2cbfebd519f`.
- Cloned `git@github.com:boksic1986/airflow-BS-demo.git` into empty `fengxian:/home/jiucheng/project/airflow-demo` as a code mirror.
- Created remote ignored `.env` for smoke only; no `.env` committed.

### Changed files

- `.env.example`
- `.gitignore`
- `AGENTS.md`
- `backend/Dockerfile`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/requirements-dev.txt`
- `backend/requirements.txt`
- `backend/tests/test_health.py`
- `dags/.gitkeep`
- `docker-compose.yaml`
- `shared/.gitkeep`
- `shared/uploads/.gitkeep`
- `shared/runs/.gitkeep`
- `shared/reports/.gitkeep`
- `shared/logs/.gitkeep`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/05_API_CONTRACT.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/14_AGENT_WORKFLOW.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `ssh fengxian` Level 0 preflight | success | Docker 20.10.21/API 1.41, PGT-A path and Snakefile readable, Snakemake 8.5.4, Python 3.12.2, no `172.30.10.0/24` conflict |
| direct `curl` GitHub release on fengxian | timed out | Left a partial plugin file, later replaced |
| TUNA Docker CE focal deb unpack to user plugin | success | Produced `Docker Compose version v2.24.7`; used as fallback path |
| local `curl.exe --proxy socks5h://127.0.0.1:1080` GitHub Release download + `scp` | success | Official `docker-compose-linux-x86_64` downloaded locally and synced to fengxian |
| `docker compose version` on fengxian | success | `Docker Compose version v2.24.7` |
| `git clone git@github.com:boksic1986/airflow-BS-demo.git /home/jiucheng/project/airflow-demo` | success | Directory was empty; mirror is on `main`, clean, commit `dd1d8a7` for tested code |
| `docker compose config --services` | success | Listed postgres, redis, airflow-worker, backend, frontend, mailhog, airflow-api-server, airflow-scheduler |
| `docker compose config --quiet` | success | Re-run after local GitHub plugin replacement also passed |
| `docker compose up -d postgres redis mailhog backend` | success | Built backend image, pulled base images, started minimal services |
| `curl -fsS http://127.0.0.1:8000/api/health` | success | Returned `{"status":"ok"}` |
| `docker compose down` | success | Used safe stop only, no `-v` |
| `curl -fsSI http://127.0.0.1:8025` | failed | MailHog returned 404 for HEAD; not a service failure |
| `curl -fsS http://127.0.0.1:8025/` | success | MailHog GET probe found page content |
| `docker compose ps` after cleanup | success | No running demo containers |

### Tests

Remote-only acceptance evidence:

- `docker compose config --quiet` passed on fengxian with user-level Compose v2.24.7.
- Minimal service smoke passed on fengxian: postgres, redis, mailhog, backend started; backend health returned `{"status":"ok"}`; services were stopped with `docker compose down`.
- MailHog HTTP GET probe passed on fengxian.

Local note: a local pytest/YAML parse check was run before the user clarified the remote-only testing rule. Those local results are not counted as acceptance evidence, and the temporary `.venv` was removed.

### Not run / why

- Airflow web/scheduler/worker startup: out of scope for this batch; T011 remains next.
- Airflow `/health`: not run because Airflow services were not started.
- frontend functional test: out of scope; frontend is only an nginx placeholder.
- biodemo DB migration: not implemented yet.
- PGT-A metadata/dry-run/failure smoke: intentionally deferred to T027/T035/T045/T057/T084.
- Snakemake dry-run: not run in this batch.

### Current git status

Local repo has the implementation commit `dd1d8a7` pushed to `origin/main`; this handoff/state-doc update is expected to be committed and pushed as a follow-up docs/state commit. Fengxian mirror is clean at the tested code commit.

### Risks

- Remote image and pip downloads can be slow; consider adding Docker registry/pip mirror configuration in a later infra task if builds remain slow.
- The current Postgres smoke starts only the default Airflow database; biodemo DB/schema creation is still pending.
- Airflow services are defined but not validated; the Airflow image may still require initialization/user setup in T011.
- The remote `.env` contains local-only demo credentials and is ignored; it must not be committed.

### Open questions

- Whether to keep direct commits to `main` during early bootstrap or switch to task branches/PRs for T011 onward.
- Which migration tool to use first for biodemo DB: Alembic with SQLAlchemy/SQLModel or plain SQL bootstrap.

### Next recommended task

Run T011: initialize and start Airflow web/scheduler/worker, then verify Airflow `/health` and document the minimal Airflow user/auth setup without adding PGT-A DAG yet.

### Rollback notes

- Stop services with `docker compose down` only.
- Remove the user-level Compose plugin with `rm "$HOME/.docker/cli-plugins/docker-compose"` if needed.
- Revert repository changes with a normal `git revert`; do not use `git reset --hard` or force push.

## 2026-07-02 21:16 - Codex - T005/local Git and plugin workflow

### Goal

Initialize `D:\pipeline\airflow-demo` as the local development Git repository, point it at `git@github.com:boksic1986/airflow-BS-demo.git`, and document server mirror, superpowers, and GitHub plugin usage rules.

### Completed

- Added `.gitignore` from the existing template so `.env`, local notes, shared data, FASTQ/BAM/VCF/NPZ, logs, caches, and build outputs stay untracked.
- Added `.gitattributes` to keep text files normalized to LF in the repository.
- Added `docs/19_REPO_AND_PLUGIN_WORKFLOW.md` with GitHub remote, local-vs-server mirror responsibilities, server pull-only rules, superpowers usage, GitHub plugin routing, and repository description.
- Updated `docs/14_AGENT_WORKFLOW.md` to require git status, remote, branch, commit/dirty-state checks and to document superpowers/GitHub plugin routing.
- Updated `docs/16_CODEX_PROMPTS.md` with Git/GitHub, superpowers, and GitHub plugin prompt templates.
- Updated `CURRENT_STATE.md`, `TASKS.md`, and `MANIFEST.json` for the new Git/GitHub workflow.
- Initialized local Git repository on branch `main` and added `origin` remote.

### Changed files

- `.gitignore`
- `.gitattributes`
- `docs/19_REPO_AND_PLUGIN_WORKFLOW.md`
- `docs/14_AGENT_WORKFLOW.md`
- `docs/16_CODEX_PROMPTS.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | initially failed before `git init` | Confirmed the directory was not yet a Git repo |
| `gh --version` | success | GitHub CLI available: `2.92.0` |
| `gh auth status` | success | Authenticated as `boksic1986`, SSH git protocol |
| `git init -b main` | success | Created local repository |
| `git remote add origin git@github.com:boksic1986/airflow-BS-demo.git` | success | Added GitHub remote |
| `git status --short --branch` | success | Showed no commits yet on `main` with untracked project files |
| `git remote -v` | success | `origin` fetch/push both point to `git@github.com:boksic1986/airflow-BS-demo.git` |
| `git ls-remote origin HEAD` | success with no output | Remote is reachable; no HEAD advertised, consistent with an empty remote repo |
| `git commit -m "docs: initialize airflow demo planning repo"` | failed | Git author identity was not configured locally; no commit was created |
| `git push -u origin main` | failed | No commit existed yet, so `main` refspec did not exist |
| `git config user.name "boksic1986"` and `git config user.email "boksic1986@users.noreply.github.com"` | success | Set repo-local identity only; did not modify global Git config |
| final manifest/keyword/safety checks | success | Manifest `48/48`, keywords found, no unsafe file candidates |
| `git commit -m "docs: initialize airflow demo planning repo"` | success | Created initial commit `73ca47f` |
| `git push -u origin main` | success | Pushed `main` to `git@github.com:boksic1986/airflow-BS-demo.git` and set upstream |

### Tests

Pending final verification before commit/push:

- Manifest `file_count` and listed files must match.
- Required GitHub/plugin/server mirror keywords must be searchable.
- Git safety check must confirm ignored secrets/data patterns are not staged.
- `git ls-remote origin HEAD` must remain accessible.

### Not run / why

- Docker/Airflow/PGT-A tests were not run; this task only initializes Git and updates documentation.
- GitHub PR creation was not run; the requested flow is initial commit and push to `main`, not a draft PR.

### Current git status

Local repository initialized on `main` with `origin=git@github.com:boksic1986/airflow-BS-demo.git`. Initial commit `73ca47f` was pushed to `origin/main`; a follow-up documentation-state commit records the final status.

### Risks

- If GitHub remote has branch protection or non-empty hidden state, `git push -u origin main` may fail. Do not force push without explicit user approval.
- Server mirror on fengxian has not been cloned or pulled in this task.

### Open questions

- Whether to configure GitHub repository description through the GitHub UI/API after the initial push.
- Whether future implementation should use direct commits on `main` for early bootstrap or task branches with draft PRs.

### Next recommended task

Run the final verification, commit the bootstrap documentation, push `main`, then use T014 for Docker Compose v2 readiness on fengxian.

### Rollback notes

If no push has happened, remove `.git/` and revert the documentation changes. If push succeeds and rollback is needed, use a normal revert commit; do not use `git reset --hard` or force push without explicit approval.

## 2026-07-02 20:51 - Codex - T004/fengxian PGT-A demo 测试计划

### Goal

将用户确认的 fengxian PGT-A demo 测试方案落地为仓库文档，并同步当前状态、任务表和交接记录；不执行服务器安装、部署、容器启动或 PGT-A 流程运行。

### Completed

- 新增 `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`，记录 `pgta` / `bio_pgta` 命名、Snakemake 8.5.4 暂不升级、用户级 Docker Compose v2 plugin 准入、固定 Docker 网段 `172.30.10.0/24`、Level 0-4 测试层级和 BS10610 迁移预检。
- 更新 `SERVER_INFO.md`，记录 fengxian 与 BS10610 的非敏感只读探测快照。
- 更新 `CURRENT_STATE.md`，标记当前仍处 P0，计划已落地但服务未实现/未启动。
- 更新 `TASKS.md`，新增 T004 计划任务并拆出后续 T014/T027/T035/T045/T057/T084。

### Changed files

- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | failed: not a git repository | 当前 `D:\pipeline\airflow-demo` 不是 Git 仓库 |
| `rg -n "PGT|pgta|bio_pgta|fengxian|BS10610|Snakemake 9|docker compose|172\.30\.10"` | success | 修改前仅发现通用 compose 文档，无 PGT-A 计划 |
| `Get-Date -Format 'yyyy-MM-dd HH:mm'` | success | 用于 handoff 时间 |
| PowerShell `ConvertFrom-Json` manifest check | success | `file_count=45`、manifest 列表数 `45`、缺失文件数 `0` |
| old draft identifier and placeholder grep | success: no matches | 无旧草案标识、BS10610 用户名笔误或占位文本 |
| `rg -n "bio_pgta|pipeline=pgta|172\.30\.10\.0/24|v2\.24\.7|Snakemake 8\.5\.4|BS10610|T004|T014|T027|T035|T045|T057|T084" ...` | success | 关键命名、网段、Compose 版本、任务 ID 均可定位 |
| `Select-String ... -Pattern 'docker compose down -v|docker system prune|docker volume prune|baseline_qc|Level 0|metadata|bio_pgta'` | success | 安全禁止项和 Level 0-4 关键测试词均可定位 |

### Tests

文档一致性检查已运行：manifest JSON 可解析且计数匹配；新增计划、任务、状态和交接中可定位 `pgta` / `bio_pgta`、固定网段、Compose 版本、Snakemake 8.5.4、BS10610 和后续任务 ID；旧草案标识和笔误检查无匹配。

### Not run / why

- `docker compose version` / `docker compose config`: 未运行；用户要求本轮不执行服务器变更，且当前本地目录无 compose 文件。
- backend/frontend/DAG/Snakemake tests: 未运行；对应代码尚未实现。
- PGT-A metadata/dry-run smoke: 未运行；本轮只落地计划文档。

### Current git status

不可用。`git status --short --branch` 返回 `fatal: not a git repository (or any of the parent directories): .git`。

### Risks

- `CURRENT_STATE.md` 和 `SERVER_INFO.md` 的服务器信息来自本轮前的只读探测快照，真实执行前仍需重复 Level 0 preflight。
- fengxian 当前没有 Docker Compose v2；后续 T014 必须先解决 Compose 准入。
- BS10610 路径与用户不同，迁移前必须参数化路径，不能复用 fengxian 硬编码路径。

### Open questions

- 是否要把 airflow-demo 初始化为 Git 仓库或从远端仓库重新同步。
- PGT-A Level 4 `baseline_qc` 是否在 Level 1-3 通过后允许运行，以及允许运行的并发上限。

### Next recommended task

执行 T014：在 fengxian 以用户级 Docker CLI plugin 方式安装/启用 Docker Compose v2，并只运行 `docker compose version` 作为准入验收。

### Rollback notes

本轮仅改文档。回滚方式是移除 `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`，并恢复 `SERVER_INFO.md`、`CURRENT_STATE.md`、`TASKS.md`、`HANDOFF.md` 到本轮修改前内容。

### <TO_BE_FILLED>

暂无。
