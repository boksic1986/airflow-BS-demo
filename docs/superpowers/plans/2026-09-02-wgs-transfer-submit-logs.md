# WGS transfer progress, direct submission, and Rule log implementation plan

> Scope: T153 follow-up corrections approved on 2026-09-02. This plan changes
> the disabled candidate worktree only. It does not rebind the WGS release,
> deploy production, pause the online T152 run, or start OBS/CCE work.

## Outcome

1. Airflow owns exact Step1/Step5 progress through a transparent node200
   `obsutil` wrapper and exposes bytes, speed, ETA and current file without
   requiring a cce-pipeline change.
2. The Submit page creates a normal WGS run directly. DAG prepare executes the
   WGS repository's `sampleinfo` then `analysis` behavior; only final selected
   samples appear in the frontend.
3. The configured release stays at `wgs-4.1.1-2499749` until WGS publishes the
   next approved revision. Updating HEAD alone never changes a run binding.
4. Failed Rule diagnostics use the already mirrored `analysis.log` and its
   existing opaque key; no arbitrary SFS path registry is introduced.

## Task 1: transfer progress contract and tests

Files:

- Add `scripts/wgs_obsutil_progress.py`
- Add `scripts/tests/test_wgs_obsutil_progress.py`
- Modify `scripts/wgs_runtime_gate.py`
- Modify `scripts/tests/test_wgs_runtime_gate.py`
- Modify `backend/app/wgs_observer.py`
- Modify `backend/tests/test_wgs_observer.py`

Steps:

1. Add failing wrapper tests for CR and LF progress, command passthrough,
   atomic JSON, redaction, successful completion and parser degradation.
2. Add failing runner tests proving Step1/Step5 publish the neutral schema and
   preserve status monotonicity.
3. Implement `wgs-runtime.transfer-progress.v1`. The wrapper invokes the real
   binary from `WGS_REAL_OBSUTIL_BIN`, forwards all arguments, streams stdout
   and stderr unchanged, and stores no URI, credential or absolute data path.
4. Use one request-local file per child process. Derive current-file display
   from a basename or ordinal only. Aggregate bytes and files every five
   seconds; calculate EWMA speed and ETA only when totals are trustworthy.
5. If parsing or atomic progress writing fails, continue the real `obsutil`
   process and mark monitoring degraded. The transfer exit code remains the
   source of truth.
6. Accept the neutral schema in the backend projection. Keep the old
   cce-pipeline schema only as a read-compatibility input, never as a deployment
   requirement.

## Task 2: direct WGS submission and native prepare

Files:

- Modify `backend/app/main.py`
- Modify `backend/app/wgs_platform_service.py`
- Modify `backend/app/wgs_runtime_adapter.py`
- Modify `backend/app/wgs_project_catalog.py`
- Modify `backend/tests/test_wgs_only_platform.py`
- Modify `backend/tests/test_wgs_runtime_adapter.py`
- Modify `frontend/src/api.ts`
- Modify `frontend/src/pages/SubmitPage.tsx`
- Modify `frontend/src/WgsProductionUi.test.tsx`

Steps:

1. Add failing API tests for `POST /api/wgs/runs`: catalog-only project/root,
   exact sequencing-directory resolution, no client path or version, automatic
   release binding, and repeat-submit idempotency.
2. Add failing runner tests that require explicit `platform`,
   `sequencing_batch`, `analysis_batch` and WGS `use_reference` values in the
   frozen request and prepare command.
3. Implement the server-controlled endpoint by resolving the catalog root,
   creating/reusing the AnalysisRun and submitting deterministic `bio_wgs`.
4. Remove the draft gate and preview wizard from the frontend. Present one
   confirmation form and explain that WGS prepares sampleinfo and selects final
   samples after submission.
5. Keep historical draft tables/endpoints inaccessible from the frontend for
   this candidate; remove them in a later schema cleanup only after confirming
   they were never deployed.
6. After prepare success, sync only WGS final `selection.kept` samples into the
   safe public projection. Never expose clinical fields or intermediate pending
   records as analyzed samples.

## Task 3: failed Rule diagnostics without a path registry

Files:

- Modify `backend/app/diagnostics_service.py`
- Modify `backend/app/wgs_timing_service.py`
- Modify `backend/tests/test_run_diagnostics.py`
- Modify `backend/tests/test_wgs_timing_service.py`
- Modify `frontend/src/features/run-detail/RunWorkflowTab.tsx`
- Modify `frontend/src/features/run-detail/RunWorkflowTab.test.tsx`

Steps:

1. Add failing tests for a failed Rule matched by exact job ID, then Rule name,
   unmatched fallback, maximum read size, maximum excerpt length and path
   isolation.
2. Read only the registered mirrored `analysis.log`, at most its final 2 MiB.
   Extract a bounded window around the latest matching failure marker and strip
   control characters. Never resolve a logger-supplied path.
3. Return `stderr_excerpt` and the existing analysis-log opaque key with failed
   Rule API rows. The log endpoint continues to resolve only indexed keys.
4. Show the excerpt in the failed Rule row and provide an “Open WGS analysis
   log” action. If no anchor exists, show the Rule message and the analysis-log
   tail link.

## Task 4: documentation and verification

Files:

- Modify `docs/04_DATABASE_SCHEMA.md`
- Modify `docs/05_API_CONTRACT.md`
- Modify `docs/06_FRONTEND_SPEC.md`
- Modify `docs/07_AIRFLOW_DAG_SPEC.md`
- Modify `docs/10_QC_LOGGING_REPORTING.md`
- Modify `docs/11_DEPLOYMENT_RUNBOOK.md`
- Modify `docs/13_SECURITY_AND_OPERATIONS.md`
- Modify `TASKS.md`, `CURRENT_STATE.md`, and `HANDOFF.md`

Verification runs on BS10610 using a task-specific path below
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/`; no evidence is written
under `/tmp`.

Run backend, runner, DAG import, frontend, migration and Compose/network tests.
Confirm the candidate keeps both execution switches false and `bio_wgs` paused.
Do not switch `current` and do not operate on the online T152 deployment in this
task.
