# GATK selective port report — 2026-09-12

## Scope and provenance

- Production baseline: `8e982c9d534ff82c97ca87eba8a033f5b4135b86` in the independent normal clone `D:/pipeline/airflow-demo-production`.
- Pinned donor: `4013f93414ba21e24ec5f6a101d373e0297bd66c` (`origin/jiucheng/gatk/T262-transfer-progress-evidence`). The former donor worktree was already absent when this task began; no worktree was removed, moved, pruned, restored or recreated by this work.
- Port method: pinned-object `git show` review plus bounded file/hunk application. No branch merge, checkout, ref change, commit, production deploy or analysis submission was performed.

## Exact code/test allowlist

- `backend/app/config.py`: add fail-closed `GATK_SOURCE_POLICY=restricted|unrestricted`; default is `restricted`.
- `backend/app/gatk_submission_service.py`: preserve production SCMC/config/barcode/FASTQ validation; add explicit unrestricted input policy; freeze exact resolved source and resolved FASTQ parent authorities; derive `<source_project>_GATK` result project.
- `backend/app/gatk_runtime_service.py`: port tested generation fencing, terminal reconciliation and delivery/runtime evidence handling.
- `backend/app/main.py`: GATK-only DAG-terminal request model/import/internal route hunk.
- `backend/app/pipeline_registry_service.py`: GATK-only stage-backed progress projector and adapter registration hunk.
- `backend/tests/test_gatk_submission_service.py`
- `backend/tests/test_gatk_runtime_service.py`
- `backend/tests/test_gatk_terminal_reconciliation.py`
- `backend/tests/test_gatk_workspace_api.py`
- `dags/bio_gatk.py`
- `dags/tests/test_bio_gatk_contract.py`
- `scripts/gatk_runtime_gate.py`: include T256 result naming and T262 Step1 transfer-progress evidence.
- `scripts/tests/test_gatk_runtime_gate.py`
- `scripts/materialize_gatk_runtime_profile.py`
- `scripts/tests/test_materialize_gatk_runtime_profile.py`
- `config/gatk_snakemake.airflow-overlay.yaml`
- `config/gatk_runtime.node200.env.example`

No WGS runtime, WGS tests, frontend, generic registry definition, database migration or production environment file was copied from the donor.

## Unrestricted input policy

`unrestricted` removes business-root whitelisting for both the authenticated operator's explicit source project and that project's resolved FASTQ link targets. It does not configure `/`, `/sg2` or `/bi` as an application allowlist. The deployment's read-only `/sg2` and `/bi` mounts remain the outer visibility boundary.

The following checks remain mandatory: absolute and strictly resolved source path; real non-symlink project directory; fixed required manifest files; valid batch-form project name; SCMC hospital filtering; matching YAML SCMC set and barcode sidecar; complete R1/R2 set; every resolved FASTQ target is a regular file; hash/size/mtime/path fingerprint revalidation; authenticated owner-bound expiring single-use draft; duplicate-batch lock; safe submitted project component; and exact frozen source path in the request. Invalid policy values fail closed. Restricted behavior remains the default.

## RED evidence (BS10610 only)

Environment preflight returned hostname `server10610`, current release `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260910-t258-cce084-r1`, and cached image ID `sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed` for `airflow-demo/backend:t235-232154f`.

All tests ran in disposable `--rm --network none` containers against candidate `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/gatk-production-20260912`; no active service or runtime tree was changed.

- Initial policy RED: unrestricted project outside the configured source root failed in `_within` as expected before implementation.
- Expanded policy RED: an unrestricted project whose FASTQ links resolved outside configured FASTQ roots failed at `FASTQ SCMC001.R1 is outside every approved root` before the unrestricted FASTQ change.
- Shared integration RED: 13 targeted tests passed and 2 failed because GATK `project_progress` was not registered; this directly required the bounded shared registry hunk.

## GREEN evidence (BS10610 only)

- Backend GATK submission/runtime/terminal/workspace suite: **15 passed**, one upstream Starlette deprecation warning.
- GATK runtime gate, profile materializer and DAG contract suite: **21 passed**.
- Python compilation of all changed Python modules: passed with no output.
- Broader registry/WGS/DAG/gate selection: **84 passed, 3 failed**. The failures are the three already recorded production-baseline exclusions: WGS finalize sample state, WGS selected-sample projection and Heavy Slot display expectation. They are outside this GATK allowlist; no WGS production logic was changed to make them pass.

Two command-shape failures were corrected without code changes: the first combined script test lacked `PYTHONPATH=/workspace`, and a later mixed-root collection used `/workspace` instead of `/workspace/backend:/workspace`. The final commands use the correct isolated import paths.

## Frontend and deployment review

The production frontend already has the manual GATK pipeline switcher, release query, preview/confirm form, execution-disabled message, submitted-run link and GATK run-detail handling, with existing frontend tests. No frontend donor hunk is required.

Minimum deployment-side requirements remain outside this port: deploy `gatk` in the registry/capability set, provide the reviewed runtime/evidence/source mounts and private node200 configuration, explicitly set `GATK_SOURCE_POLICY=unrestricted`, keep execution disabled until the final gate, install the reviewed gate/profile, and unpause `bio_gatk` only under explicit production authorization. The new `docker-compose.gatk.yaml` was reviewed read-only and supplies the backend policy/gates and Airflow DAG environment; coordinator validation of complete inherited mounts, private SSH config, rendered Compose, and service restart scope remains required.

## Uncovered dependencies and issues

- No real source project was previewed and no real DAG/CCE job was submitted.
- No Airflow import/database integration check was run against an active service; validation was container-isolated.
- The configured production GATK runtime/private roots and source pin reported by the coordinator were not mutated or independently exercised by this task.
- The donor directory disappearance is an external workspace-state event; pinned object provenance remained available and matched the requested HEAD.
- Final `git diff --check` passed with no whitespace errors.

## P2 generation-fenced Step1 transfer repair

Independent review found that the initial T262 port stored every Step1 transfer
plan and raw progress row under one attempt/stage directory. A failed generation
1 followed by generation 2 therefore encountered the old execution ID and could
not start. The aggregator also checked only analysis, attempt, stage and file key,
then stamped the current identity onto a potentially stale raw row.

The repaired contract uses a private
`<spool>/<analysis>/attempt-N/step1_upload/generation-N/` directory for each
generation. Transfer environment and plan paths point to that directory. Plan
replay requires exact `execution_id`, `generation` and `request_hash`. Raw v1
rows are accepted only when those three fields also match the current request.
The validated v2 aggregate is written both inside the generation directory and
atomically to the stable legacy observer location
`<spool>/<analysis>/attempt-N/step1_upload/progress.json`. This preserves backend
discoverability without allowing an older generation to supply current values.

RED evidence on the original port, BS10610 isolated candidate:

- Generation-aware environment-path assertion failed because `generation-3`
  was absent.
- Creating the generation-2 plan after generation 1 raised
  `existing GATK transfer plan identity mismatch`.
- Foreign generation/execution/hash rows with a later heartbeat replaced the
  valid current row (`99` bytes observed instead of `7`).

GREEN evidence after the repair:

- Full `scripts/tests/test_gatk_runtime_gate.py` plus backend legacy-path
  ingestion tests in `backend/tests/test_gatk_evidence_projection.py`:
  **19 passed** in the cached `airflow-demo/backend:t235-232154f` image with
  `--rm --network none`.
- The tests prove generation-1 plan retention, generation-2 creation,
  same-generation replay, rejection of wrong generation/execution/hash raw
  records, correct current-row aggregation, and legacy public-path discovery.

### Follow-up observer compatibility and non-regression fence

A second review found two edge cases in the first repair. The shared transfer
root helper had also moved Step5 into `generation-N`, but the existing GATK
observer discovers download evidence at the attempt-level `*/progress.json`.
Step5 now retains its original attempt/stage progress directory; only Step1 is
generation-private.

Step1 publication now holds an exclusive `.progress.lock` across the complete
current-request read, identity comparison, existing-public comparison and
atomic replace. The latest request file must exactly match analysis, attempt,
stage, execution ID, generation and request hash. A generation-1 worker that
reads after the request replacement is suppressed, and generation 1 cannot
overwrite an already-published generation-2 aggregate. Because the backend
request writer does not share this lock, a worker that read the old request
immediately before replacement may briefly publish generation 1 before the
first generation-2 row; the backend's exact current-execution check rejects
that stale snapshot. An existing higher generation or conflicting
same-generation public aggregate also fails closed.

The actual repository raw producer, `scripts/wgs_obsutil_progress.py`, emits
`wgs-runtime.transfer-progress.v1` rows with analysis, attempt, stage and file
identity but does not emit `execution_id`, `generation` or `request_hash`.
Read-only inspection of BS10610's `cce-pipeline 0.8.4` installation found no
raw transfer-progress producer or `WGS_STAGE_REQUEST_HASH` consumer in that
package. Therefore the GATK aggregator accepts absent optional execution
fields only from its already generation-private Step1 directory. If any of
those fields are present, they must match; malformed or foreign values are
ignored. This matches the deployed producer without weakening cross-generation
isolation.

Follow-up RED evidence reproduced: nested Step5 path, valid identity-less raw
row filtered to zero bytes, late generation 1 creating the public aggregate,
and malformed generation raising instead of being ignored. Final BS10610
GREEN for the full GATK gate suite plus backend evidence discovery is
**21 passed** using the same cached, network-disabled disposable container.
