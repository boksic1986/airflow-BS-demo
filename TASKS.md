# TASKS.md

## T204 - ctapa production runtime migration and 20260904B recovery

Owner: airflow/runtime/infra/QA/docs

Status: deployed on `.96`; `20260904B` attempt 3 in progress

Acceptance:
- [x] Reproduce the `20260904B` prepare failure and prove the shared-NFS
  request visibility race from the exact Airflow log and runtime request.
- [x] Add a failing DAG regression for the generic registered-request-missing
  message, then pass the focused DAG suite in the `.96` Airflow image.
- [x] Install and validate the user-provided `ctapa` SSH identity outside the
  release without printing or committing private material.
- [x] Move active node200 runtime, CCE, OBS and SFS collector configuration to
  `/home/ctapa` and stop the old production `hanjj` collector.
- [x] Move production analysis/runtime roots to
  `/sg2/50.ctapa/project/HWcloud`, retaining fixed network and port boundaries.
- [x] Run the WGS backend as the required `ctapa` UID `6801` with shared gid
  `520`, and correct the three pre-contract `root:bioinfo` result directories
  to `ctapa:bioinfo` without moving or deleting analysis data.
- [x] Keep `/bi/software/obsutil_5.8.3/obsutil` as the real OBS client and
  preserve executable wrapper modes.
- [x] Regenerate `20260904B` sampleinfo and analysis configuration in the new
  root, import three samples, and start Step1 with an immutable transfer plan.
- [ ] Observe terminal Step1-Step6 success for `20260904B`; do not infer final
  workflow success from the currently running upload.

Restrictions:
- Do not sync the pending T194/cce-pipeline application update into this
  migration release.
- Do not modify or remove PostgreSQL, Redis, volumes, unrelated Docker
  workloads, source FASTQ, OBS data or another batch directory.
- Do not restore the retired `hanjj` key or collector to the active stack.

## T192 - Production Docker test-artifact cleanup

Owner: infra/operations/docs

Status: completed on `.96`

Acceptance:
- [x] Inventory every container, Compose project, image tag, network attachment
  and volume before deletion.
- [x] Preserve the complete running `airflow-wgs` production stack and keep one
  current image for each WGS application component: Airflow, backend and
  frontend.
- [x] Remove obsolete WGS backend/frontend image tags, the stopped obsolete
  migration container and exact unused test/build images without using prune.
- [x] Preserve PostgreSQL/Redis containers and volumes, all unrelated workloads,
  and the external `nipt_analysis_test_net` network.
- [x] Verify no dangling image remains, all 11 WGS production services remain
  running, network IPAM is unchanged and the published UI returns HTTP 200.

## T191 - Frontend login reverse-proxy DNS recovery

Owner: infra/operations/docs

Status: completed on `.96`

Acceptance:
- [x] Reproduce the login failure through the published nginx endpoint.
- [x] Confirm backend health independently and identify the exact stale nginx
  upstream address after the backend container recreate.
- [x] Run production Compose preflight and restart only frontend-nginx so it
  resolves the current backend container address.
- [x] Verify a real server-local admin login and authenticated `/api/auth/me`
  request both return HTTP 200 without exposing credentials.
- [x] Preserve the backend, databases, Airflow, scanner, volumes, external
  network and published-port boundary.

## T190 - T7 source-name correction and false backfill rollback

Owner: backend/operations/QA/docs

Status: completed and deployed on `.96`

Acceptance:
- [x] Prove that `.96` and the scanner container both see
  `2233th_20260901B_E250197502` under `/bi/fastq/T7_Fastq`.
- [x] Record the operator-confirmed source truth: 2224/20260902A and
  2225/20260902B are latest despite being misnumbered; 2233/20260901B is
  historical.
- [x] Remove numeric-chip ordering from scanner freshness decisions and retain
  the existing marker/bootstrap contract.
- [x] Delete only the false 2233 intake index row; preserve its successful WGS
  AnalysisRun, source directory and analysis results.
- [x] Reuse one backend WGS batch matcher for scanner reconciliation and
  automatic-dispatch duplicate detection.
- [x] Verify a new scanner cycle leaves only 2224/2225 and submits no run.
- [x] Pass the complete `.96` backend suite and preserve the production Docker
  network and single published endpoint.

Restrictions:
- Do not rename source FASTQ directories or synthesize 2234/2235 in the UI.
- Do not submit, resume, delete or recreate WGS analysis for `20260901B`.
- Do not recreate PostgreSQL, Redis, Airflow, frontend, volumes or the external
  Docker network.
- Do not commit Git.

## T189 - Step5 manifest handoff and 20260902B recovery

Owner: runtime/operations/docs

Status: completed and deployed on `.96`

Acceptance:
- [x] Reproduce the circular Step5 manifest prerequisite with a failing test.
- [x] Start the frozen Step5 script before requiring its OBS-delivered local
  manifest; atomically freeze an exact transfer plan once visible.
- [x] Fail closed if a successful Step5 process never yields a valid manifest
  after the bounded NFS grace period.
- [x] Prevent incrementally observed successful obsutil children from
  temporarily projecting the whole frozen plan as 100%; derive completed file
  count from planned targets and speed from active children only.
- [x] Install the tested gate atomically on node200.
- [x] Resume only Step5 and downstream tasks in the original `20260902B`
  DagRun and verify terminal success without rerunning Step1-Step4.
- [x] Reconcile the recovered same-attempt terminal state in biodemo without
  allowing ordinary terminal-state regressions.
- [x] Select only the exact batch-level QCstat when per-sample QCstat files are
  present; project non-empty QC exception text as warning rather than unknown.
- [x] Record `.96` Docker and live recovery evidence in state and handoff docs.

## T188 - Step6 terminal barrier, WGS run projection and guarded T7 dispatch

Owner: Airflow/backend/frontend/runtime/operations/docs

Status: completed and deployed on `.96`

Acceptance:
- [x] Insert `wait_step6_materialize` between the asynchronous Step6 start and
  `finalize_run`; finalization also validates the exact analysis, attempt,
  stage, schema and successful terminal marker.
- [x] Project the frozen `sampleinfo.tsv`, per-sample analysis state, safe QC,
  controlled artifacts and registered logs in the backend. Do not expose
  patient names, hospitals, raw sampleinfo content or server absolute paths.
- [x] Freeze Step1 and Step5 transfer denominators before transfer and mark old
  observations without a plan as `legacy_estimate`.
- [x] Make the dashboard resource panels compact: one selected node, no
  duplicate node name, no client-connections row, SFS name as a tag, and SFS
  I/O history selectable as 24h/1d/7d.
- [x] Add an internal ready-batch dispatcher which uses biodemo AnalysisRun and
  the deterministic Airflow DagRun ID as the idempotency authority. Existing
  manual, running, successful, failed or cancelled batches are linked and
  skipped, never restarted by the scanner.
- [x] Require an explicit `WGS_AUTO_DISPATCH_NOT_BEFORE` activation watermark;
  ready intake discovered before it is baseline-only and cannot be
  retrospectively submitted.
- [x] Pass candidate Docker validation on `.96`: backend full, runtime focused,
  DAG/deployment, frontend tests/build and Compose/network checks.
- [x] Publish the immutable release, update the node200 runtime gate, recreate
  only affected application services, enable automatic dispatch with a fresh
  watermark and verify no historical run or DagRun is created.
- [x] Reconcile existing false Step6 failures by clearing only the new wait,
  finalize and lease-release tail after proving their Step6 markers are exact
  successes.

Restrictions:
- Do not restart or mutate an in-flight CCE Master.
- Do not recreate PostgreSQL, Redis, Docker volumes or the external network.
- Keep WGS pinned to V4.1.1 commit `6c982817...` and do not commit Git.

## T187 - Reset and freshly resubmit failed 20260902B batch

Owner: operations/backend/Airflow/QA/docs

Status: completed; exact reset finished and the fresh 8-sample run is active in Step3

Authorization and scope:
- The operator explicitly authorized an exact-batch reset of `20260902B` after
  confirming whether the UI or runtime was wrong.
- The only business run in scope is `WGS_20260903_111829_1D58E1`, including
  its failed Airflow DagRuns and exact frozen batch directory
  `WGS_20260902B_T7Hg38V4.1.1`.
- The operator explicitly waived backups because this is a test reset. Do not
  touch another batch, the external Docker network, PostgreSQL/Redis volumes,
  OBS FASTQ, or the production WGS source.

Acceptance:
- [x] Prove the failure is real and occurs in `prepare_wgs_analysis`, not only
  in the frontend projection.
- [x] Confirm all seven DagRuns are terminal, no runner lock/process is active,
  the OBS lease is empty, and the exact Master/Pod/batch ConfigMap lock is gone.
- [x] Record the operator's explicit no-backup override before mutation.
- [x] Attempt the frozen Step0 orphan reset; after it failed before mutation on
  unavailable worker metadata/reset tooling, remove only the exact SFS
  run/linkage state manually while preserving OBS FASTQ.
- [x] Delete only the failed business run and its seven failed Airflow DagRuns,
  then remove the old runner identity so a new run ID can be created.
- [x] Diagnose the regenerated 2-sample selection: expanded family members
  `71/72/75` belong to sequencing batch `20260902A`; without recovered batch
  identity, WGS correctly holds their two complete families in pending.
- [x] Use the WGS pending recovery contract for the three exact rows and prove
  with the frozen selector that it yields 8 selected samples, 3 pending samples
  and 16 readable FASTQ files.
- [x] Freshly submit `20260902B`, regenerate sampleinfo, verify the 8-sample
  final selection and start Step1-Step6. The retained run is
  `WGS_20260903_200310_37E27D-a1`; it acquired the OBS slot after the previous
  lease expired, reused the existing FASTQ objects without duplicate upload,
  completed Step1 and Step2, and is now monitoring active Master Job
  `cce-master-44815ec87b04c2020d77` in Step3.

## T186 - Reschedule WGS approval gates on transient backend transport failures

Owner: Airflow/infra/QA/docs

Status: deployed on `.96`; operator recovery remains intentionally pending

Acceptance:
- [x] Prove `20260902B` attempt 6 failed in `wait_wgs_execution_approval`
  before Step1 because Docker DNS temporarily could not resolve `backend`.
- [x] Reproduce both config and execution approval-gate failures with a RED DAG
  regression test.
- [x] Use the same transport-only reschedule helper for stage and approval
  sensors; preserve hard failure for HTTP/application contract errors.
- [x] Pass the focused and complete `bio_wgs` DAG unit suite in the `.96`
  Airflow image.
- [x] Deploy only the Airflow DAG services while no synchronous WGS task is
  active; preserve the running `20260825A` Master and fixed network.
- [x] Leave `20260902B` at execution review until the operator explicitly
  confirms execution; do not start Step1 automatically.

## T185 - Repair retried WGS Rule evidence identity and stale observer display

Owner: backend/infra/QA/docs

Status: deployed on `.96`

Acceptance:
- [x] Reproduce the production schema-1 logger event `attempt-1` rejection for
  an Airflow attempt greater than one.
- [x] Keep exact `run_label`, release and binding checks while treating the
  schema-1 attempt label as Master-local and projecting events into the frozen
  Airflow binding attempt.
- [x] Return observer state only for the run's current attempt; never expose an
  older attempt's monitoring warning on a new prepare/review attempt.
- [x] Consume the existing `20260825A` attempt-7 and `20260902B` attempt-4
  JSONL files without rerunning or changing either CCE Master.
- [x] Pass the complete backend suite in an isolated `.96` Docker container.
- [x] Deploy only backend and observer, then restart Nginx to refresh its
  backend address; preserve databases, Airflow, scanner and fixed networking.

## T184 - Recover 20260902B prepare after shared-NFS visibility race

Owner: backend/Airflow/infra/QA/docs

Status: deployed on `.96`; attempt 6 is waiting for operator execution approval

Acceptance:
- [x] Preserve the refreshed 11-row source sampleinfo while recoverably archiving
  attempt 5's generated batch directory and final `sampleinfo.tsv`.
- [x] Reproduce the exact prepare-success/NFS-artifact race as a failing backend
  test in the `.96` Docker environment.
- [x] Return HTTP 200 with `ready=false` and `artifact_pending=true` only while a
  successful prepare artifact is not yet visible; retain hard failures for
  malformed, empty or identity-mismatched artifacts.
- [x] Pass the focused regression and complete `.96` backend suite.
- [x] Back up both databases and deploy backend-only without changing Airflow,
  PostgreSQL, Redis, volumes or the fixed Docker network.
- [x] Create attempt 6, regenerate the batch directory and final sample table,
  and verify two currently eligible samples were imported from 11 source rows.
- [x] Leave Step1, Step2 and CCE unstarted pending the operator's final approval.

## T183 - Recover 20260902A Rule monitoring and registered log access

Owner: backend/Airflow/frontend/infra/QA/docs

Status: deployed on `.96`; original CCE Master remains active

Acceptance:
- [x] Prove the Master/logger/evidence bridge are running and identify the
  failure as a control-plane recovery race rather than a WGS analysis failure.
- [x] Reschedule Step3 sensors on transient backend transport failures without
  weakening HTTP/application error handling.
- [x] Retry only the exact registered-request NFS visibility error, at most five
  times, before preserving the original hard failure.
- [x] Associate logger `data_id` values with a unique registered business sample
  and family; ambiguous aliases remain unassigned.
- [x] Return the registered opaque Master analysis-log key for every WGS Rule
  and expose an `Open log` action without returning server paths.
- [x] Recover only Step3 and downstream tasks in the same attempt; preserve
  Step1/Step2 and the existing Master Job.
- [x] Pass `.96` Docker DAG, backend and frontend suites/build and production
  API/network smoke checks.
- [ ] Operator refreshes the active run and confirms the Rule/Logs presentation.

## T179 - Transfer units, node load and SFS chart repair

Owner: frontend/runtime/infra/QA/docs

Status: deployed on `.96`; current in-flight upload preserved

Acceptance:
- [x] Use one shared formatter for byte-valued progress in Current Progress,
  Run Tracker and WGS Step1/Step5 workflow cards.
- [x] Display CPU, memory and normalized load utilization bars; keep the
  1/5/15 load values visible and colour the load bar by saturation.
- [x] Add `logical_cpu_count` to the bounded node metrics snapshot without a
  migration or a new API.
- [x] Right-align Client connections on an inline row with additional spacing.
- [x] Add a labelled, auto-scaled Y axis to the SFS read/write history chart.
- [x] Keep aggregate transfer state `running` while any child transfer is
  running, even when an earlier child record failed.
- [x] Observe failing tests before implementation, then pass full `.96` Docker
  frontend/Python suites and the frontend production build.
- [x] Deploy only the frontend and resource collectors, atomically update the
  node200 runner, and preserve active OBS workers and fixed Docker networking.
- [ ] Operator visually refreshes the dashboard after deployment.

## T178 - Reset failed 20260825A analysis directory

Owner: operations/QA/docs

Status: completed; operator run is active

Acceptance:
- [x] Confirm attempt 4 failed at analysis preparation because the exact batch
  directory already existed; sampleinfo preparation itself succeeded.
- [x] Resolve the exact target, confirm it is not a mountpoint, and verify no
  batch lock, Master Job or matching Master Pod exists.
- [x] Create a restricted backup and verify its SHA256 before removing only the
  exact batch analysis directory.
- [x] Preserve sampleinfo, Airflow/biodemo evidence, OBS, SFS and fixed Docker
  network state.
- [x] Record that the operator concurrently submitted a new run; do not submit,
  approve, cancel or otherwise mutate that run.

## T177 - Prepare-stage status routing repair

Owner: backend/QA/infra/docs

Status: deployed on `.96`; awaiting operator attempt 3

Acceptance:
- [x] Preserve attempt 2 and prove node200 `prepare_sampleinfo` returned success
  with the expected three-row sample table.
- [x] Reproduce the exact HTTP 500 caused by `unsupported runtime stage sync`.
- [x] Accept `prepare`, `prepare_sampleinfo` and `prepare_analysis` as valid
  status-sync stages without treating them as transfer or observer artifacts.
- [x] A successful sampleinfo status imports the safe sample/family preview and
  advances staged submission to `config_review`.
- [x] Focused tests fail before the implementation and pass afterward; complete
  `.96` backend suite passes with the repository config mounted.
- [x] Deploy backend-only on `.96`, preserving failed attempt 2, databases,
  Airflow task state, frontend, volumes and fixed Docker network.
- [ ] Operator starts attempt 3 after deployment; Codex does not submit it.

## T176 - Failed WGS resubmission and Submit refresh repair

Owner: backend/frontend/infra/QA/docs

Status: deployed on `.96`; awaiting operator resubmission

Acceptance:
- [x] Reproduced the defect: a terminal failed batch reused attempt 1 and its
  failed deterministic DagRun while resetting the page to sampleinfo preparation.
- [x] Active duplicate submission remains idempotent and successful duplicate
  submission is rejected.
- [x] Failed, cancelled and unknown-interrupted duplicates create a new attempt
  and `<analysis_id>-a<attempt>` DagRun while preserving AnalysisRun identity.
- [x] New attempts clear stale terminal timestamps, error and progress fields.
- [x] Submit polling exits the preparation view on terminal failure and links to
  the existing Run Detail failure evidence.
- [x] Focused tests failed before implementation and passed afterward; complete
  `.96` backend/frontend suites, frontend build, Compose and network guard pass.
- [x] Deploy only backend/frontend source and static assets on `.96`, preserving
  databases, Airflow metadata, existing attempts, volumes and fixed network.
- [ ] Operator may resubmit `20260825A`; Codex must not submit it on the user's behalf.

## T175 - Dashboard resource utilization and SFS I/O visualization

Owner: frontend/infra/QA/docs

Status: deployed on `.96`; awaiting operator visual refresh

Acceptance:
- [x] Analysis Node Health displays CPU and memory utilization bars while
  retaining load 1/5/15 and the existing node selector.
- [x] Cloud Resources displays reliable SFS used/total capacity when both
  Cloud Eye used bytes and percent are available, with a percentage-only
  fallback when total capacity cannot be derived.
- [x] Node and SFS source timestamps are right-aligned in their panel headings.
- [x] The duplicate Workflow Activity card is replaced by a read/write
  bandwidth chart using the existing bounded 60-point SFS history and current
  IOPS; no API, database or collector change is introduced.
- [x] Focused test was observed failing before implementation and passing after
  implementation; full `.96` Node Docker frontend suite and build pass.
- [x] Deploy only the `.96` frontend release while preserving databases,
  Airflow services, volumes, scanner, observer and fixed Docker network.

## T174 - Forward-only WGS submission evidence fixes

Owner: backend/airflow/frontend/infra/QA/docs

Status: deployed on `.96`; awaiting a new operator-submitted batch

Acceptance:
- [x] Public WGS Batch is projected once by the backend from `analysis_batch`,
  then `sequencing_batch`, and never re-parsed in React.
- [x] Run and sample searches explicitly include the public analysis/sequencing
  batch fields; Samples displays the public Batch column.
- [x] Final sampleinfo import and full Snakemake log indexing share one bounded
  node200-to-container batch-root resolver.
- [x] Missing terminal Rule JSONL marks monitoring degraded instead of healthy;
  no historical Rule/sample projection or database backfill is performed.
- [x] Airflow failures retain both remote stdout and SSH stderr, so a remote
  Python exception is not hidden by the TTY close message.
- [x] The first three-stage attempt exposed stale node200 gate deployment;
  node200 gate was backed up and atomically updated after 42 runner tests.
- [x] Deploy the backend/DAG/frontend candidate on `.96`, preserving databases,
  volumes, fixed network and the failed diagnostic attempt.
- [ ] Operator submits a new batch and verifies sample/family, Rule JSONL and
  Snakemake log evidence without relying on historical projection.

## T173 - Three-stage WGS submission and SFS-only Cloud Eye

Owner: backend/airflow/frontend/infra/QA/docs

Status: deployed on `.96`; awaiting the first operator-controlled three-stage production submission

Acceptance:
- [x] Submit Run exposes a pipeline selector and separates sampleinfo, config
  review, analysis prepare and final execution approval.
- [x] Reference selection/resource set are stage-2 server-whitelisted values;
  browser requests cannot contain paths, YAML or runtime commands.
- [x] Future Airflow DagRun and WGS run IDs use `<analysis_id>-a<attempt>`.
- [x] `bio_wgs` imports with 23 tasks and eight reschedule sensors; legacy
  requests bypass new approvals.
- [x] SFS Turbo Cloud Eye signed query returns 200 using regional
  `CES ReadOnlyAccess`; node200 writes an atomic SFS-only spool every minute.
- [x] Cloud Resources renders SFS only and hides the obsolete placeholder.
- [x] `.96` Docker backend, runner, frontend tests/build and isolated DagBag
  checks pass for the candidate.
- [x] Recheck that the legacy production DagRun is terminal, then deploy
  backend/DAG/frontend together without rebuilding databases, volumes or network.
- [x] Authenticated production smoke confirms the deployed three-stage assets,
  approval APIs, 23-task DAG and SFS-only resource response before a new batch.
- [ ] Operator submits the first three-stage batch and confirms the canonical
  `<analysis_id>-a<attempt>` identity across Airflow, WGS and runtime evidence.

## T172 - `.96` frontend request recovery and independent build

Owner: frontend/infra/QA/docs

Status: deployed; awaiting operator visual refresh

Acceptance:
- [x] Dashboard waits for resolved deployment capabilities and does not issue the
  duplicate initial `deployed` and `wgs` request waves.
- [x] Idempotent GET requests retry exactly once after a native network or body
  read failure; writes, HTTP errors and explicit aborts are never retried.
- [x] Scanner metadata and discovery-list results settle independently.
- [x] The SPA shell is not cached; only fingerprinted assets are immutable.
- [x] Frontend dependencies were freshly installed, tested and built on `.96`
  with an independently downloaded and checksummed Node 24.15.0 runtime.
- [x] The release changed only `frontend-nginx`; databases, Airflow, scanner,
  observer, volumes and the fixed Docker network were preserved.
- [ ] Operator refresh confirms the red `Failed to fetch` notices are absent in
  the existing workstation session.

## T171 - `.96` manual WGS submission activation

Owner: backend/airflow/infra/frontend/QA/docs

Status: manual-ready deployed; first real batch remains user-operated

Acceptance:
- [x] Public submission uses one `batch` field and maps it to identical WGS
  sequencing/analysis batch values.
- [x] request v4 separates control and analysis roots; WGS output is restricted
  to `Cloud_WGS_Clinical/WGS_Clinical/<batch>`.
- [x] `hanjj` node200 restricted runner, evidence bridge, OBS progress wrapper,
  CCE config, kubeconfig/kubectl and fixed WGS commit pass preflight.
- [x] `bio_wgs` is the only Airflow DAG and is unpaused; scanner remains a
  separate 600-second service and auto-dispatch remains false.
- [x] Remote backend/scripts, DAG import, frontend Docker tests/build, Compose,
  authenticated HTTP and fixed network checks pass.
- [x] Activation creates no AnalysisRun, RunAttempt, DagRun, OBS transfer or CCE
  workload.
- [ ] The operator submits `20260901B` and accepts the first real Step1-Step6
  run and transfer-progress evidence.

## T169/T170 - SSH node metrics and compact node selector

Owner: backend/frontend/infra/QA/docs

Status: done in disabled production mode

Acceptance:
- [x] `.96` and `.97` use distinct pinned host keys with the same approved client identity.
- [x] Fixed SSH probes populate healthy CPU/load/memory node snapshots without exposing SSH or database credentials across service boundaries.
- [x] Re-reading the same spool timestamp preserves derived metrics and does not add duplicate history points.
- [x] Analysis Node Health displays one node at a time with `.96`/`.97` tabs and hides disk, IOPS and network values.
- [x] Frontend and backend server-Docker tests, production build, HTTP/static-asset smoke, fixed network and disabled gates pass.

## T168 - `.96` WGS production control-plane disabled deployment

Owner: infra/backend/airflow/frontend/QA/docs

Status: done in disabled mode; real runtime remains blocked

Scope:
- Deploy the merged WGS-only backend/frontend/Airflow architecture to
  `172.17.61.96` without migrating BS10610 demo state.
- Keep PostgreSQL on a local Docker volume backed by `/data`, while WGS results
  and control spools use the approved `14.hanjingjing` `/sg2` roots.
- Install the `hanjj` SSH identity for node200 with a pinned host key, without
  placing private material in the release, image, database or logs.
- Preserve the fixed external Docker network and expose only the frontend.

Acceptance:
- [x] Fresh biodemo/Airflow databases initialized; one admin and zero run state.
- [x] Only paused `bio_wgs` is loaded with 18 tasks and no import errors.
- [x] Login, capabilities, release, scanner and disabled-submit HTTP smoke pass.
- [x] Scanner bootstrap counts historical directories without persisting detail
  rows or creating AnalysisRun/Airflow DagRun records.
- [x] PostgreSQL is a local Docker volume on `/data`; all persistent service logs
  are capped at `20m * 3` and all services have zero restarts at acceptance.
- [x] Network is `192.168.199.0/24`, gateway `192.168.199.1`, with only
  `172.17.61.96:12959` published.
- [x] Validate the approved `hanjj` node200 kubeconfig, kubectl and CCE operator
  contract, and restrict the kubeconfig and `cce.yaml` to mode `0600`.
- [ ] Run a separately approved minimal real WGS batch before unpausing the DAG.

## T129/T130 WGS-only production platform

| ID | Task | Owner | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|
| T129 | WGS-only control platform Phase 1 | backend/airflow/frontend/infra/docs | RBAC, biodemo schema, observer, WGS-only UI, paused safe DAGs, Compose and design docs | BS10610 fresh migration, health/login/RBAC, WGS-only UI/API, paused DAGs, submit denied | done |
| T130 | Current WGS server-copy observability foundation | airflow/snakemake/backend/frontend/infra/QA | immutable snapshot catalog, logger/evidence adapters in server development copy, durable observer cursors, Rule/Pod APIs/UI, isolated deployment | synthetic incremental/restart/Pod/API/RBAC/network acceptance; execution remains disabled | done |
| T131 | WGS execution and transfer integration | airflow/snakemake/infra/QA | refresh accepted server WGS snapshot, wire CCE/SGE/local runners, OBS `-vmd5`, result reconciliation and recovery | full failure/concurrency/transfer/three-mode acceptance | superseded by T132 |
| T132 | WGS 4.0.1 native Master Job/evidence integration | airflow/snakemake/backend/infra/QA | historical 4.0.1 design/audit baseline | superseded by the WGS 4.1.0 T133 implementation | superseded |
| T133 | WGS 4.1.0 single-DAG and Rule logger integration | airflow/backend/observer/QA | immutable Airflow WGS snapshot; offline biosan-jsonl plugin; one CCE-only `bio_wgs`; node 200 `172.17.61.200` restricted runner; immutable logger-overlay Master; Master-only evidence | disabled-mode contracts pass; cce follow-up docs committed; logger image pushed and smoke-tested; real execution still awaits cce FASTQ/progress implementation and approved runtime acceptance | blocked |
| T135 | WGS 4.1.1 contract freeze and security | coordinator/infra/security/docs | safe immutable snapshot, source/profile/image/wheel provenance, protected prepare-config contract | manifest and provenance checks pass; secret scan clean; no runtime execution | done |
| T136 | WGS 4.1.1 node200 runner and single DAG | airflow/infra/QA | SSH-config `wgs-runtime`, Step1-Step6 adapter, leases/reschedule sensors, only paused `bio_wgs` | synthetic idempotency/recovery and DAG import pass; both gates false | done |
| T137 | WGS 4.1.1 backend and observer | backend/observer/QA | DB/API contracts, Rule JSONL offsets, Master-only evidence, result reconciliation | restart/dedupe/interruption/result-manifest tests pass | done |
| T138 | WGS 4.1.1 frontend production alignment | frontend/backend/QA | manual submit, stage transfer state, Rule/Master/results/review/RBAC UI | focused frontend/API/RBAC tests and production build pass | done |
| T139 | WGS 4.1.1 disabled-mode production release | infra/QA/docs | migration, demo-state cleanup preserving admin, BS10610 release and smoke | only paused `bio_wgs`; gates false; network/volume/data boundaries pass | done |
| T140 | WGS 4.1.1 minimal real acceptance | airflow/infra/QA | approved real batch, transfer/Master/Rule/result recovery and four-run concurrency evidence | all real-runtime gates pass before unpause | blocked |
| T141 | WGS 4.1.1 Master Rule evidence bridge | airflow/backend/observer/QA | accept logger `attempt-N`; Step3 incremental JSONL copy; read-only terminal reader Job; disabled release | focused observer/bridge/runtime tests pass; gates remain false; real reader acceptance deferred to T140 | done in disabled mode |
| T142 | Single published WGS release Airflow integration | airflow/backend/observer/frontend/infra/docs | one server-owned release contract at `1778fca`; request v3; fixed-repository runner; release-bound DB/API/UI; disabled BS release | BS10610 tests and smoke pass with gates false and paused DAG; no real OBS/CCE execution | done in disabled mode |
| T143 | T7 scan-only intake | backend/observer/frontend/infra/QA/docs | 30-minute read-only T7 scanner, bootstrap, chip-level DB/API/UI, auto-dispatch hard-off | unit/integration/migration/network pass; two production cycles remain idempotent with zero AnalysisRun and DagRun | done |
| T144 | WGS Step4 CRAM repair contract | backend/airflow/observer/frontend/QA/docs | fixed-cram service action, same-attempt maintenance mode, 0.7.1 frozen-bundle command, RBAC and audit | disabled-mode tests pass; gates-off returns 409 before Airflow/SSH; real repair deferred | done in disabled mode |
| T145 | WGS scanner sparse persistence and CCE observer lifecycle | backend/airflow/observer/frontend/infra/QA/docs | split scanner/run observer, LISTEN/NOTIFY lifecycle, exact transfer sync, migration 0012, protected 1830-row cleanup and disabled release | baseline stores zero details; idle observer does no polling/logging; tests/API/network/gates pass | done in disabled mode |
| T146 | WGS 2499749 / cce-pipeline 0.8.1 manual production run | airflow/backend/frontend/infra/QA/docs | bind current WGS release, pass sequencing batch to prepare, deploy enabled manual flow, rebuild one approved batch from controlled intake | disabled tests and network pass; exact old batch state cleared; one manual run is visible through API/UI and reaches a verified terminal state | done; original run reached success through Step6/finalize |
| T147 | Airflow worktree reconciliation and PR workflow | coordinator/docs | audit every local worktree against origin/main, fast-forward safe ancestors, preserve dirty or obsolete branches, merge reconciliation through GitHub PR | no user changes overwritten; current WGS mainline unchanged except state docs; PR checks and merge verified | done |
| T148 | Prune completed worktrees and branches | coordinator/docs | retain root main and active T146 worktree, delete historical worktrees/local branches/remote branches, merge cleanup record through PR | exactly two worktrees, two local branches and only origin/main remain; T146 artifacts/runtime untouched | done |
| T149 | WGS Step3 monitor protocol repair and in-flight takeover | airflow/backend/infra/QA/docs | atomic monotonic node200 stage status, binding-authoritative Master validation, transitional status handling, same-attempt business-state recovery, exact Step3/downstream restart | existing attempt and Master retained; Step1/Step2 unchanged; UI resumes Master/Rule state; original DagRun continues to verified terminal state | done for Step3; terminal delivery now tracked by T152 |
| T150 | T7 FASTQ name-level scanner repair | backend/frontend/infra/QA/docs | accept regular/hard/symlink entries without resolving targets, v2 name fingerprint, historical reclassification, dynamic interval UI, rolling scanner/frontend release | 2227 is ready with 10 pairs; no AnalysisRun/RunAttempt/DagRun added; 600-second schedule, read-only mount and fixed network verified | done |
| T151 | Exclude non-clinical YF samples from T7 intake | backend/infra/QA/docs | ignore `YF*` sample IDs before pairing, v3 fingerprint with v2 compatibility, scanner-only rolling release | YF-only is no-new-WGS, YF missing mate is not review, existing ready rows upgrade without drift, no run side effects | done |
| T152 | Step4 Master completion race and same-attempt recovery | airflow/backend/infra/QA/docs | bounded binding-authoritative Master wait, failed Step4 retry generations, business-state recovery, original DagRun continuation | Step1-Step3 unchanged; same Master/attempt resumes normal Step4 then completes Step5-Step6 | done; same attempt/Master completed Step4-Step6 and DagRun success |
| T153 | WGS production UI and contract freeze | coordinator/backend/frontend/airflow/docs | document 28; stage/progress/draft/log/resource/Step7 contracts | contracts are internally consistent and preserve runtime/privacy/network boundaries | done |
| T154 | WGS stage, Rule and log projection | backend/observer/airflow/QA | migration 0013; authoritative stage state; transfer/Step3 progress; safe Rule and log evidence | focused and full backend/runner/DAG tests pass without fabricated progress | done; T159 replaced the path registry with bounded analysis.log excerpts |
| T155 | WGS dashboard and Run Detail production UI | frontend/backend/QA | Batch/stage progress; Samples; Rule phase graph/table; logs/failure/catalog cleanup; remove WGS QC UI | focused UI tests and production build pass | done; BS10610 offline image/package and HTTP smoke passed |
| T156 | WGS sampleinfo draft and submit wizard | backend/airflow/frontend/QA | historical candidate draft design | replaced by T159 native sampleinfo/analysis submission semantics | superseded |
| T157 | Platform resources and admin Step7 | backend/infra/frontend/security/QA | bounded resource snapshots; `.96/.97` and SFS/OBS projection; admin cleanup action | stale metrics do not affect runs; Step7 RBAC/double-confirm/idempotency pass | implemented disabled; live exporters/Cloud Eye and real Step7 not exercised |
| T158 | Disabled production regression and release | infra/QA/docs | BS10610 migration/tests/smoke/backup and non-destructive release | fixed network/port and data boundaries pass; real batch remains separately gated | blocked on release drift and T156/T157 external contracts |
| T159 | WGS native submission, Airflow-owned transfer progress and safe Rule errors | backend/airflow/frontend/infra/QA/docs | direct catalog submission; final-sample sync; transparent obsutil wrapper; bounded analysis.log Rule excerpt | BS backend/runner tests and frontend build pass; no arbitrary paths or fabricated progress; no online change | implemented in candidate; node200 install and disabled release pending |
| T160 | Bounded WGS log tail reader | backend/frontend/QA/docs | server-generated opaque key; reverse chunked log tail; file size/truncation metadata | large analysis.log is never loaded completely; BS10610 backend and Docker frontend suites pass | done in candidate; deployment pending |
| T161 | Production WGS 4.1.1 rebind and repository integration | backend/airflow/frontend/QA/docs | bind dev_CJC_4.1.1_cloud@6c98281; map T7/sequencing/analysis batch without test-only algo; full BS Docker validation; PR/merge/main-worktree sync | exact production release contract and UI pass; 4.2.0 remains test-only; network unchanged; no runtime deployment | done (PR #8, merge 6046a28) |
| T163 | Authenticated capabilities, T7 intake cleanup and recovered-run projection | backend/airflow/frontend/infra/QA/docs | load capabilities only after login; product-language scanner card; persistent exact-chip ignore; explicit Step4/Step5 retry generations; narrow Step5 business-state recovery | BS Docker suites/build pass; 2226 remains absent after rescan; original run resumes Step5 from checkpoint; fixed network/port retained | done; original run completed Step6/finalize successfully |
| T165 | Run Batch/Sample search, Finished timestamps and production UI synchronization | backend/frontend/infra/QA/docs | Batch and Finished in both run lists; server-side batch/sample search; immutable finalize time; deploy merged WGS UI contracts | BS Docker suites/build, migration, fixed-network preflight and authenticated HTTP smoke pass; historical successful run gets authoritative finish time; no WGS/OBS/CCE rerun | done; production disabled release deployed and verified |
| T166 | WGS workflow and Rule projection correction | backend/observer/frontend/infra/QA/docs | one backend Step1-Step6 contract; current WGS 4.1.1 Rule phase mapping; stable Rule order and exact analysis.log sample enrichment; API-driven UI stages | historical run shows six successful stages, production Rule phases/order/sample context, no ETA text in message, Docker tests and fixed-network smoke pass | done; disabled production release deployed and verified |
| T167 | `hanjj` runtime identity and directory migration | backend/airflow/infra/security/QA/docs | request v4 dual-root contract; protected `hanjj` SSH identity; node200 OBS/kubectl/kubeconfig/cce config; new control and direct batch roots; `.96/.97` SSH metrics | disabled release proves no old-root writes, no secret leakage, strict host keys, fixed network/port; real batch remains separately approved | implemented by T171; real batch pending |
| T168 | `.96` production control-plane disabled deployment | infra/backend/airflow/frontend/QA/docs | fresh local databases, WGS-only services, protected node200 SSH identity, fixed network and bounded logs | login/API/DAG/database/storage/network smoke pass; execution remains disabled | done in disabled mode; node200 CCE config and real batch remain blocked |

任务状态：`todo` / `in_progress` / `blocked` / `review` / `done`。

## T167 - `hanjj` runtime identity and directory migration

Owner: backend/airflow/infra/security/QA/docs

Status: implemented by T171; first real batch pending

Scope:
- Replace the active node200 SSH identity with `hanjj` while retaining the old
  `chenjc` material only as an unmounted rollback input until acceptance.
- Separate the new Airflow control root from the direct
  `WGS_Clinical/<batch>` analysis root under `14.hanjingjing`.
- Install `hanjj`-owned OBS/CCE configuration without exposing credential
  contents to Compose, Git, logs or biodemo.
- Monitor `.96/.97` through a key-only node probe; keep `.200` out of the
  Analysis Node UI and keep the DB collector key-free.

Acceptance:
- [x] Target identity, directories and trust boundaries approved in docs/29.
- [x] request v4 and dual-root path tests fail before implementation and pass after.
- [x] `.96`/node200 shared-root permissions and fixed runner path pass.
- [x] CCE read-only preflight passes as `hanjj` without printing secrets; OBS
  execution itself remains intentionally uncalled before the user batch.
- [x] Manual-ready release passes backend/DAG/frontend/Compose/network verification.
- [ ] A separately approved minimal real batch completes without writing the old root.

## T166 - WGS workflow and Rule projection correction

Owner: backend/observer/frontend/infra/QA/docs

Status: done

Scope:
- Replace the Batch Runs biological phase rail with the six project
  orchestration stages from one backend contract.
- Project current WGS 4.1.1 rule prefixes into Pre-calling, Variant analysis,
  QC and Cloud delivery; assign stable raw-event order.
- Enrich missing historical sample/family context only from exact registered
  sample identifiers in the bound `analysis.log`; never infer by row count.
- Reject logger-provided sample/family identifiers that are not registered for
  the run, and incrementally index appended `analysis.log` bytes before joining
  cached contexts against the current sample registry.
- Remove the frontend WGS rule-name map and six-stage template, fix stage-card
  CSS tokens, and keep ETA history out of the message column.

Out of scope:
- WGS rerun, OBS upload/download, a new CCE Master, Worker Pod monitoring,
  schema changes, external metrics, Step7, or execution-gate changes.

Acceptance:
- [x] Expected failures reproduced in BS10610 Docker before implementation.
- [x] Focused backend and frontend tests pass after implementation.
- [x] Full backend suite, TypeScript and production build pass in BS10610 Docker.
- [x] Post-review security, lifecycle-status and duplicate-mapping regressions pass.
- [x] Protected database backup, disabled release, projection replay and
  authenticated API/container HTTP verification complete.
- [x] External Docker network remains `192.168.199.0/24` and only
  `172.17.106.10:12959` is published.

Note: authenticated API and container HTTP smoke completed. The Codex in-app
browser refused the private HTTP URL under its URL safety policy, so no browser
screenshot was captured and no workaround was attempted.

## T152 - Step4 Master completion race and same-attempt recovery

Owner: airflow/backend/infra/QA/docs

Status: done; the original DagRun and attempt completed Step4-Step6 after the
WGS marker fix, without repeating Step1-Step3 or creating another Master.

Acceptance:

- [x] Step4 retries the Master-success precondition for at most 600 seconds only
  when Step3 success and the frozen Master identity match.
- [x] Master failure, identity mismatch and timeout remain hard failures.
- [x] A dead failed `step4_publish` worker archives status/worker/log as a new
  retry generation; request drift, active workers and other stages cannot restart.
- [x] Backend restores the known same-attempt control-plane false failure to
  `publishing` with an audit event; Step4 repair accepts canonical bound
  `cce-master-*` evidence without a name-prefix allowlist.
- [x] A subsequent real Step4 terminal failure is projected to biodemo and the
  frontend as `failed` with its evidence message instead of remaining stale at
  `publishing`.
- [x] BS10610 validation passed: runner 28, backend 250, DAG import errors 0,
  Compose/network checks passed.
- [x] Backed up both databases and runtime state, deployed r7, and retried only
  Step4 and downstream in the original DagRun. Step1-Step3 and the Master UID
  did not change; no FASTQ upload or Master submission was repeated.
- [x] The retry crossed the original Master precondition and did not invoke
  CRAM repair.
- [x] WGS producer/consumer marker contract was corrected outside T152; normal
  Step4 then passed with the same frozen run identity and no CRAM repair.
- [x] Step5 resumed from its obsutil checkpoint after the temporary disk-space
  failure, MD5 verification passed, and the original attempt completed Step6
  and finalize successfully.

## T151 - Exclude non-clinical YF samples from T7 intake

Owner: backend/infra/QA/docs

Status: done

Acceptance:

- [x] RED tests prove the old scanner counts complete YF pairs and treats an
  incomplete YF sample as a clinical pair issue.
- [x] Mixed, YF-only and incomplete-YF behavior passes with YF excluded before
  eligible/add-on/pair-issue accounting.
- [x] Fingerprint v3 excludes YF names and accepts the equivalent pre-filter v2
  fingerprint once, avoiding false drift for existing ready rows.
- [x] Focused scanner tests pass 18/18 and full backend tests pass 247 with 1 skip.
- [x] Back up biodemo, deploy a scanner-only immutable release, and verify no
  AnalysisRun, RunAttempt or Airflow DagRun is created or changed.
- [x] Confirm 600-second schedule, auto-dispatch false, read-only T7 mount,
  fixed Docker network and current CCE attempt are unchanged.
- [x] Production 2222 contained 192 YF FASTQ entries (96 pairs) and correctly
  changed from ready/96 to no-new-WGS/0; 2223/2224/2227 remained ready.

## T150 - T7 FASTQ name-level scanner repair

Owner: backend/frontend/infra/QA/docs

Status: done

Acceptance:

- [x] Scanner pairs WGS entries by basename for regular files, hard links,
  valid symlinks and dangling symlinks without resolving or reading targets.
- [x] `-S\d+` add-ons remain excluded; incomplete normal pairs become
  `needs_review`; fingerprint v2 uses sorted eligible names rather than FASTQ
  metadata, target paths or MD5.
- [x] Historical `no_new_wgs` rows can become `ready/needs_review`; old v1
  regular-file `ready` fingerprints upgrade without a false drift alert.
- [x] BS10610 backend suite passed 243 tests with 1 skip; frontend passed 31
  tests and the TypeScript/Vite production build.
- [x] biodemo backup and checksums were recorded before rolling only scanner
  and frontend. AnalysisRun, RunAttempt and Airflow DagRun counts stayed 1/1/1.
- [x] Production scan classified 2227 as ready with 10 pairs, 2222/2223/2224
  as ready with 96/12/8 pairs, and kept 2221/2225 as no-new-WGS.
- [x] API/UI report the 600-second schedule and auto-dispatch disabled;
  scanner has only the read-only T7 mount. Network remains 192.168.199.0/24
  and only frontend publishes 172.17.106.10:12959.
- [x] The active T149 analysis/attempt/DagRun and Step3 stage were unchanged.

## T149 - WGS Step3 monitor protocol repair and in-flight takeover

Owner: airflow/backend/infra/QA/docs

Status: done for Step3; the same Master completed successfully and delivery
continuation is now tracked by T152

Acceptance:

- [x] Reproduced the fixed `.partial` race, backward status transition, generic
  Step3 `running`, hard-coded Master prefix rejection, and HTTP 500 transition.
- [x] Runner uses unique same-directory temporary files, file/directory fsync,
  atomic replace, serialized monotonic status, and publishes `accepted` before
  worker spawn.
- [x] Step3 first `running` and terminal status retain frozen Master identity,
  namespace, parsed status, and monitoring health.
- [x] Backend treats incomplete transitions as HTTP 200/not-ready, validates
  the exact frozen Master/namespace, remains Master-only, and audits same-attempt
  monitor recovery.
- [x] BS10610 tests pass: backend 238, scripts 30, DAG 7; node200 shared-SFS
  concurrent atomic-write smoke completed 200 writes with no partial file.
- [x] Live Rule evidence mismatch was traced to the authoritative CCE
  `run_label`; Step3 now binds the observer to the label from the frozen
  profile only after exact Master/namespace validation, and regression tests
  prove schema-1 JSONL ingestion.
- [x] Public Master projection now keys current workloads by the bound Step3
  event identity, so `cce-master-*` is visible without exposing Worker rows;
  historical `wgs-master-*` rows remain readable.
- [x] Back up databases/runtime, deploy the immutable repair release and node200
  gate, then clear only Step3 and downstream in the original DagRun.
- [x] Verify the same analysis/attempt/run ID/Master continues, Step1/Step2 are
  not retried, and frontend Master/Rule monitoring returns.
- [x] The original DagRun followed the real CCE terminal state into Step4.
  Final Step4-Step6 delivery is separated into T152 because it exposed an
  independent WGS marker contract defect.

## T148 - Prune completed worktrees and branches

Owner: coordinator/docs

Status: done

Acceptance:

- [x] 根worktree已恢复并同步到`main`；T146 worktree保留并同步到合并后的主线。
- [x] 删除7个完成或历史secondary worktree，包括T096、T127、T129和T145系列。
- [x] 删除未注册为worktree的旧T133 staging artifacts目录（30个文件，约2.1 MB）。
- [x] 根据用户明确授权删除T096的4个未提交文件改动和未跟踪PPT目录。
- [x] 删除54个本地历史分支；本地只保留`main`和当前开发T146。
- [x] 删除16个远端历史分支；远端只保留`origin/main`。
- [x] T146 `.artifacts/`、运行状态、服务、数据库和Docker网络均未修改。
- [x] 清理记录经GitHub PR合并，临时T148分支随后删除。

## T147 - Airflow worktree reconciliation and PR workflow

Owner: coordinator/docs

Status: done

Acceptance:

- [x] 已审计全部9个本地worktree的分支、脏文件和相对`origin/main`的提交关系。
- [x] T132、T145干净且提交已在主线中，已用fast-forward同步到`origin/main`。
- [x] T127三个修复分支已通过`git cherry`确认补丁等价，不重复合并。
- [x] T096的5项未提交内容保持原样；T128的旧NIPT扫描提交不进入WGS-only主线。
- [x] T146运行态及`.artifacts/`保持不变；没有执行部署、数据库或流程操作。
- [x] 本条状态更新经GitHub PR合并到`main`。

## T146 - WGS 2499749 / cce-pipeline 0.8.1 manual production run

Owner: airflow/backend/frontend/infra/QA/docs

Status: done; the approved batch completed Step4-Step6 and finalize on the
original analysis, attempt, DagRun and Master

Acceptance:

- [x] 前一轮release曾绑定`wgs-4.1.1-cdee32c`，prepare从分析批次名提取
  `20260825A`并显式传入WGS `--batch`；分析目录仍位于Airflow runtime下的
  `WGS_Clinical/<batch>`。
- [x] BS10610 isolated tests通过：runner 19、backend 227、DAG 10、部署合同5；
  frontend 31 tests和TypeScript/Vite build通过。
- [x] 前一轮只读验收WGS HEAD `cdee32c9...`和cce-pipeline 0.8.1；不把
  cce-pipeline版本变成Airflow gate。
- [x] 已把3对FASTQ软链接复制到Airflow受控intake；源FASTQ未删除。
- [x] 旧批次SFS run/linkage、OBS input/result、已完成CCE维护Job和陈旧batch lock
  已精确清理并验证为空。
- [x] 新release、网络/API/DAG smoke通过；在批准窗口内启用两个runtime gate并完成
  operator手工提交。兼容性失败后两个gate恢复false且DAG重新paused。
- [x] Step3多行stdout解析已修复并部署，失败状态和传输状态可由Run Detail/API查询。
- [x] execution/runtime gate关闭时resume和rerun_failed返回409，不递增attempt或调用
  Airflow；聚焦后端测试14 passed。
- [x] 当前发布更新为`wgs-4.1.1-2499749`；resolved Master digest更新为
  `sha256:965473cf...dab0`，旧0.7.0兼容性阻断已由WGS/runtime发布侧修正。
- [x] 旧analysis业务记录、11个Airflow DagRun、runtime/evidence、SFS/OBS和CCE锁
  已精确清空；清理前分别备份biodemo和Airflow metadata，用户和scanner状态保留。
- [x] 通过前端等价API创建全新analysis`WGS_20260901_031616_C74E6C`并提交；release
  绑定为`wgs-4.1.1-2499749`，validate/prepare成功，Step1上传在运行。
- [x] Step3 observer监控到同一Master真实成功终态，Rules和Master状态已入库。
- [x] WGS marker修复后，原attempt完成普通Step4、Step5校验、Step6物化和finalize；
  最终AnalysisRun与Airflow DagRun均为success，未重复Step1-Step3。

## T145 - WGS scanner sparse persistence and observer lifecycle

Owner: backend/airflow/observer/frontend/infra/QA/docs

Status: done in disabled mode

Acceptance:

- [x] `wgs-intake-scanner`与`wgs-run-observer`独立服务、最小只读挂载和20m x 3日志轮转。
- [x] 无活动任务时 run observer阻塞LISTEN/NOTIFY，无全局扫描和空心跳。
- [x] scanner singleton只保存四个基线字段；首次和第二次生产扫描后均为1830个目录、0条明细。
- [x] 清理前备份、关联分析保护和1830行单事务清理通过。
- [x] Step3 activation/drain、重启恢复、四attempt隔离、精确transfer sync和前端状态合同通过。
- [x] BS10610 disabled release、migration 0012、登录/API/HTTP、DAG pause、三门禁和Docker网络验收通过。
- [ ] 真实Step3/CCE Rule JSONL活动验收仍属于T140，本任务未启动分析。

## T143/T144 T7 scan-only 与 Step4 repair

### T143 - T7 scan-only intake

Owner: backend/observer/frontend/infra/QA/docs

Status: done

Dependencies: T142; WGS release `wgs-4.1.1-1656b5d`

Acceptance:

- [x] 扫描器只读直属文件，支持bootstrap、普通/加测配对、eligible fingerprint、
  漂移阻断、advisory lock和1800秒独立调度。
- [x] API/UI只展示芯片、批次、状态和计数；不展示sample ID、路径或fingerprint。
- [x] `WGS_AUTO_DISPATCH_ENABLED=false`，代码测试断言不创建AnalysisRun/DagRun、
  sampleinfo或分析目录。
- [x] BS10610部署migration 0011和新disabled release。
- [x] 生产bootstrap及两个真实1800秒周期保持幂等，AnalysisRun/DagRun均为零。

### T144 - Step4 CRAM repair

Owner: backend/airflow/observer/frontend/QA/docs

Status: done in disabled mode

Dependencies: cce-pipeline 0.7.1合同；本阶段不安装或升级

Acceptance:

- [x] operator/admin固定cram，服务端从冻结binding生成确认串；viewer拒绝。
- [x] 同attempt、同维护操作幂等；原DagRun等待/失败两种继续语义已测试。
- [x] observer幂等同步维护状态，前端二次确认且不发送任意运行参数。
- [x] 两个execution gate关闭时返回409且不创建DB记录、DagRun或SSH操作。
- [ ] 真实0.7.1 Step4修复需另行审批，不属于本任务完成条件。

## T135-T140 WGS 4.1.1 production integration

### T135 - Contract freeze and security

Owner: coordinator/infra/security/docs
Status: done
Dependencies: WGS commit `3489b3958869e5cfab983aca1eb9c7f158c06dff`

Deliverables:

- Generate a tracked-file allowlist snapshot without host credentials,
  runtime caches or patient data.
- Lock WGS commit, `wgs-4.1.1-r1` profile, Master RepoDigest,
  cce-pipeline 0.5.0 wheel SHA256 and source/build provenance.
- Define node200 protected `--prepare-config`, shared runtime paths and SSH
  config/host-key contracts.
- Record remediation for the tracked sensitive prepare configuration and stale
  Master image labels.

Acceptance:

- [x] Snapshot manifest and source/profile/image/wheel identities are complete.
- [x] Repository/release/snapshot/log secret scans pass.
- [x] No WGS source, OBS object or CCE workload was modified during contract
  freeze.

Rollback: remove only the unreferenced Airflow snapshot/catalog candidate;
never modify or delete the upstream WGS 4.1.1 repository.

### T136 - node200 runner and single Airflow DAG

Owner: airflow/infra/QA
Status: done in disabled mode
Dependencies: T135

Deliverables:

- Replace the 4.1.0 runtime gate with a node200 adapter for WGS prepare and
  generated Step1-Step6 scripts. Airflow uses `ssh -tt -F` with a protected
  configuration, fixed host key and explicit run-local wrapper command.
- Publish only one CCE DAG, `bio_wgs`; keep manual intake, both execution gates
  false and DAG paused.
- Use async start plus five-second reschedule sensors, one OBS transfer lease,
  Airflow CCE pools and durable stage status.
- Keep Step0/Step7/Step8 manual and reject automatic reset of failed Masters.

Acceptance:

- [x] DAG import and task graph match the 4.1.1 design; no FASTQ MD5, upload
  verify, fixed Master slot or old DAG source remains.
- [x] Duplicate start, stale PID, resume, cancel and failed-Master reset gates
  pass synthetic node200 tests.
- [x] No real OBS/CCE action ran during disabled acceptance.

Rollback: restore the prior disabled release/current symlink without deleting
volumes, the external network, WGS sources or runtime data.

### T137 - Backend, observer and terminal reconciliation

Owner: backend/observer/QA
Status: done in disabled mode
Dependencies: T135, T136 internal stage contract

Deliverables:

- Update WGS snapshot, run, transfer, Rule, Master workload and six-column
  delivery-manifest contracts.
- Consume `rule-status/raw/*.jsonl` by event ID/file/byte offset, normalize
  `attempt-<n>` and use the `BATCH_RUNTIME.yaml` run label.
- Persist only deterministic Master Job/Pod evidence and reconcile unfinished
  Rules to `unknown_interrupted`.
- Implement success only after Master, Step4, Step5 and Step6 delivery gates.

Acceptance:

- [x] Partial-line, restart, replay, truncation, duplicate and four-run
  isolation tests pass.
- [x] Master OOM/interruption and logger-degraded behavior are correctly
  projected without false Rule or run success.
- [x] Invalid length/MD5 or missing `MATERIALIZED` blocks success.

Rollback: downgrade application services while leaving additive migration
structures in place; never delete production business data automatically.

### T138 - Frontend and RBAC production alignment

Owner: frontend/backend/QA
Status: done in disabled mode
Dependencies: T137 API contract

Deliverables:

- Keep only WGS login, run list, manual submit, Run Detail and account
  management paths.
- Display project stage, stage-only transfer state, Rule timing, Master-only
  Kubernetes evidence, validation issues, logs and verified artifacts.
- Explicitly show that byte/speed/ETA progress is unavailable rather than
  rendering a false percentage.

Acceptance:

- [x] viewer/operator/admin allow/deny tests pass.
- [x] Active run polling is configured at the documented five-second target.
- [x] Focused frontend tests and production build pass; the fixed build was
  packaged offline on BS10610 and verified by SHA256/HTTP smoke.

Rollback: restore the prior frontend image; backend/API execution gates stay
false throughout rollback.

### T139 - Disabled-mode BS10610 production release

Owner: infra/QA/docs
Status: done
Dependencies: T135-T138

Deliverables:

- Build a new release, migrate biodemo non-destructively and recreate only the
  required application services.
- Preserve administrator/roles; clear auth sessions and all demo run/event/
  transfer/lease/cursor/audit state.
- Remove the three legacy WGS DAG sources and supported Airflow metadata after
  confirming no active run; publish only paused `bio_wgs`.
- Preserve the external `192.168.199.0/24` network and publish only frontend
  `172.17.106.10:12959`.

Acceptance:

- [x] Compose, migration, backend/frontend/DAG, login/API and HTTP smokes pass.
- [x] Both execution flags are false and real submit remains denied.
- [x] Admin login remains available and demo business data/old DAG metadata are
  zero without deleting volumes or production data.

Rollback: atomically restore the prior `current` release before final cleanup;
do not run volume/network/global Docker prune commands.

### T140 - Minimal real batch and production enablement

Owner: airflow/infra/QA
Status: blocked pending separate approval
Dependencies: accepted T139/T141 disabled release and explicit user approval

Deliverables:

- Enable the runtime adapter while keeping `bio_wgs` paused, then submit one
  approved minimal real batch through the API.
- Validate OBS upload, Master/Rule evidence, result publish, download MD5,
  materialization, recovery and four-run launcher isolation.
- Unpause only after all real-runtime acceptance is complete.

Acceptance:

- [ ] Minimal batch reaches success only through the complete Step1-Step6
  contract.
- [ ] Transfer interruption, Master interruption, Rule failure/logger
  degraded, wrong result MD5 and four concurrent launchers are accepted.
- [ ] Old release cleanup occurs only after the production result is accepted.

Rollback: disable both execution gates, pause `bio_wgs`, stop new submissions
and preserve all batch evidence for diagnosis; cleanup remains manual.

### T141 - Master Rule evidence bridge

Owner: airflow/backend/observer/QA
Status: done in disabled mode
Dependencies: T139 and the logger-enabled pinned Master image

Deliverables:

- Normalize the production logger's `attempt-N` identity in observer without
  weakening binding checks.
- During Step3, copy complete records from every Master
  `rule-status/raw/*.jsonl` stream into the shared evidence root using durable
  per-file offsets.
- After Master exit, use one exact reader Job with only the workspace PVC
  mounted read-only, then delete it. Do not expose it or Worker Pods in API/UI.
- Treat bridge failures as degraded monitoring, not WGS analysis failure.

Acceptance:

- [x] Focused observer attempt-label regression passes on BS10610.
- [x] Incremental/partial-line/restart and read-only reader manifest tests pass.
- [x] Both execution gates remain false and `bio_wgs` remains paused.
- [ ] Real running-Master and post-exit reader behavior is accepted in T140.

Rollback: restore the prior disabled application files; do not touch WGS SFS,
OBS, CCE Master Jobs, database volumes or the external Docker network.

## P0 文档和环境探测

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T000 | 初始化仓库文档 | coordinator/docs | none | docs, AGENTS, skills | 文档完整、占位符明确 | done |
| T001 | 探测服务器环境 | infra | T000 | SERVER_INFO.md 更新 | docker/qsub/python/node 状态清楚 | done |
| T002 | 确定部署路径和数据路径 | infra/coordinator | T001 | CURRENT_STATE.md 更新 | 项目路径和 shared 路径确定 | done |
| T003 | 确定 demo 数据策略 | coordinator/snakemake | T000 | mock samples 规范 | 不使用真实患者数据 | todo |
| T004 | fengxian PGT-A demo 测试计划 | coordinator/docs | T000 | docs/18_PGTA_FENGXIAN_TEST_PLAN.md | pgta/bio_pgta 命名、Compose 准入、Level 0-4 验收、BS10610 迁移注意事项明确 | done |
| T005 | 本地 Git/GitHub 和插件工作流文档 | coordinator/docs | T000,T004 | git remote, docs/19, plugin usage docs | 本地 main 仓库指向 GitHub remote；superpowers/GitHub 插件和 fengxian 镜像规则写入文档 | done |

## P1 Airflow Docker 基础部署

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T010 | 创建 docker-compose 基础服务 | infra | T001 | docker-compose.yaml, .env.example | docker compose config 通过 | done |
| T011 | 启动 Airflow/Postgres/Redis | infra | T010 | Airflow UI/API 可访问 | airflow health 正常 | done |
| T012 | 增加 MailHog demo 邮件服务 | infra | T010 | mailhog service | http://host:8025 可访问 | done |
| T013 | 定义 shared volume 目录 | infra | T010 | shared/{uploads,runs,reports,logs} | 容器内路径一致 | done |
| T014 | fengxian 用户级 Docker Compose v2 准入 | infra | T001,T004 | `$HOME/.docker/cli-plugins/docker-compose` | `docker compose version` 输出固定 v2 版本，未做系统级 Docker 升级 | done |
| T125 | BS NIPT-only Docker 网络硬约束文档 | infra/docs | T124,T113 | engineering spec、runbook、security、server inventory、BS deployment contract | 明确 `nipt_analysis_test_net` / `192.168.199.0/24` / `192.168.199.1` 为不可变外部网络约束；记录 BS project root、主备角色和验收/回滚边界 | done |
| T126 | BS NIPT-only Airflow 平台移植 | infra/backend/airflow/frontend/QA | T125,T113 | NIPT-only capability、BS Compose、S9 images、BS10610 primary、BS1069 cold standby | 10/72-sample full runs success；FASTQ unchanged；BS1069 images verified but services stopped | done |
| T127 | BS shared NIPT/WGS Airflow control plane | infra/backend/airflow/snakemake/frontend/QA | T126 | one CeleryExecutor stack; NIPT Docker S9; host WGS S9 over restricted SSH; resource telemetry; BS1069 standby | shared deployment healthy; one-family WGS S9 dry-run; three serial NIPT full validations; no PGT-A or active-active | done |
| T128 | BS NIPT manual FASTQ scan latency repair | backend/frontend/infra/QA | T127 | lazy bounded NIPT directory traversal; BS FQ2026 default scan root; Submit root synchronization | full-root 504 reproduced; targeted scan tests/build pass; BS10610 manual scan returns candidates before nginx timeout; BS1069 remains stopped | in_progress |

## P2 Backend API 和数据库

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T020 | FastAPI 项目骨架 | backend | T010 | backend/app | /health 返回 ok | done |
| T021 | biodemo DB models/migrations | backend | T020 | analysis_run/sample/rule_event/qc/artifact | migration 可重复执行 | done |
| T022 | PGT-A 服务器路径样本发现和项目创建 | backend | T021 | `/api/input/scan`, JSON `/api/runs`, selected manifest | 白名单 rawdata_root 可扫描 R1/R2；创建 `created` run、sample rows、`samples.selected.tsv` 和 `request.json`；不触发 Airflow | done |
| T023 | Airflow API client | backend | T020,T011 | trigger/list/get dag run | mock 或真实 API 测试通过 | done |
| T024 | run 状态 API | backend | T021 | `/api/runs` list/detail/samples endpoints | 可返回 pgta run 列表、detail 和 sample fq1/fq2 路径 | done |
| T025 | logs/artifacts API | backend | T021 | PGT-A v1 log tail + dynamic artifact list | `stdout/stderr/metadata` 可读取；缺失文件返回 `LOG_NOT_FOUND`；路径穿越被拒绝 | done |
| T026 | Snakemake event receiver | backend | T021 | `/api/events/snakemake`, `/api/runs/{analysis_id}/rules` | 可幂等 upsert rule event；PGT-A logger rule 状态可从 API 查询 | done |
| T027 | PGT-A `pgta` Airflow trigger API 支持 | backend | T021,T022,T023,T004 | created run -> Airflow `bio_pgta` trigger | 已创建的 `pgta` metadata run 可通过 submit action 提交为 DAG run；状态推进到 `submitted` 且 `dag_run_id` 非空 | done |
| T090 | sample lifecycle status sync | backend/docs | T024,T027,T025 | submit/sync updates `sample.status` | submit/reanalyze 后 sample 为 `running`；显式 sync 后随 Airflow 变 `success/failed`；远端 backend pytest 48 passed；已同步近期可见 run 的 sample 状态 | done |

## P3 Airflow DAG

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T030 | DAG 公共工具 | airflow | T011,T023 | dags/common | shared-root path check, mkdir, subprocess stdout/stderr helpers added; Dockerized DAG tests and import check passed | done |
| T031 | bio_wes_qsub DAG 骨架 | airflow | T030 | dags/bio_wes_qsub.py | `manual__WES_AIRFLOW_20260705_004506` Airflow smoke success; final summary, qsub logs, and JSONL events generated | done |
| T032 | bio_nipt_qsub DAG 骨架 | airflow | T030 | dags/bio_nipt_qsub.py | dry run/mock run 成功 | todo |
| T033 | bio_nipt_docker DAG 骨架 | airflow | T030 | dags/bio_nipt_docker.py | T101 `bio_nipt_docker` template-run v1 imported cleanly; mount_smoke DAG run `manual__NIPT_20260708_033450_8362A0` reached success | done |
| T034 | email notify task | airflow/backend | T030,T012 | success/fail notify | MailHog 收到邮件 | todo |
| T035 | bio_pgta DAG 骨架 | airflow | T030,T027,T004 | dags/bio_pgta.py, pgta metadata runner | metadata target real-light run 成功，不使用 qsub；`logs/run_metadata.tsv` 生成 | done |
| T036 | PGT-A Airflow-only Snakemake 9 logger DAG | airflow/snakemake | T035,T045 | `bio_pgta_airflow`, repo-local logger plugin | Airflow-only manifest run 使用 Snakemake 9.23.1 `--logger airflow-demo` 成功；生成 events JSONL、summary TSV，并在 Airflow task log/XCom 展示状态 | done |

## P4 Snakemake/qsub 接入

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T040 | WES mock Snakefile | snakemake | T013 | pipelines/wes/workflow | WES mock 两样本 Snakemake dry-run 通过，显示 all/fastp/bwa_mem/markdup/final_summary 共 8 个 jobs | done |
| T041 | qsub submit wrapper | snakemake | T040,T026 | qsub_submit.py | mock mode 可生成 `MOCK-*` qsub_jobid、qsub stdout/stderr 和 JSONL/Backend event；`WES_20260704_180650_MOCK` 已通过 `/rules` 查询 | done |
| T042 | qsub profile | snakemake | T041 | profiles/qsub/config.yaml, snakemake_runner | Dockerized `snakemake-runner` 固定 Snakemake 9.23.1 + `cluster-generic` plugin；`--profile profiles/qsub` 已在 `fengxian` 跑通 WES mock，生成 final summary、qsub stdout/stderr 和 JSONL events | done |
| T043 | rule event logger | snakemake/backend | T026,T036 | PGT-A Snakemake 9 logger POST events | PGT-A rule 状态在 biodemo DB 和 `/api/runs/{analysis_id}/rules` 可见；WES mock qsub job id 路径已由 T041/T042 跑通 | done |
| T044 | resume/rerun 策略 | snakemake/airflow | T031,T040 | WES `new/resume/rerun_rule` -> Snakemake flags; command log artifact | `WES_20260705_162041_2507AF` initial/resume/rerun_rule smoke success；`snakemake.command.txt` contains `--forcerun fastp` and no `--forceall` | done |
| T045 | PGT-A Snakemake runner | snakemake/airflow | T035,T004 | pgta config 生成和 metadata/dry-run runner | metadata runner 已随 T035 通过；Airflow-only Snakemake 9 logger 已随 T036 通过；`dryrun_cnv` 和 `invalid_target` runner 已在 `fengxian` 通过 smoke；输出只写 shared/runs/<analysis_id>，PGT_A 目录只读 | done |
| T085 | PGT-A real target audit | coordinator/airflow | T045,T084 | docs/20 audit, baseline_qc contract | 只读审计确认 `baseline_qc` 存在、需要至少 2 个样本、会触发 mapping+metadata+baseline QC；未运行重任务 | done |
| T086 | PGT-A staged baseline_qc integration | backend/airflow/frontend | T085 | baseline_qc allowlist, build_ref config, frontend target label | API/DAG/frontend 支持 `target=baseline_qc`，创建和 submit 均要求至少 2 样本；远端 Docker 化 backend/frontend/DAG tests 通过；真实 Level 4 smoke 待用户确认 | done |
| T088 | PGT-A Snakemake cache permission fix | airflow/snakemake | T035,T045 | run-local `XDG_CACHE_HOME`, command artifact | `PGTA_20260706_140854_8F2CA4` metadata submit smoke success；stderr 不再出现 `/home/airflow/.cache/snakemake` PermissionError；artifacts include `snakemake_command` | done |
| T089 | demo log/timezone alignment | infra/frontend | T011,T050 | Compose `TZ`, Airflow core/UI timezone, frontend display timezone | `fengxian` containers and Airflow config use `Asia/Shanghai`; frontend renders UTC API timestamps as `Asia/Shanghai`; DB timestamps remain timezone-aware | done |
| T091 | PGT-A 64-core runner and frontend auto-sync | airflow/frontend/docs | T086,T089,T090 | `PGTA_SNAKEMAKE_CORES=64`, PGT-A command artifact, frontend active-run polling | `bio_pgta` and `bio_pgta_airflow` default to `--cores 64` with env override; selected active run auto-calls `sync-airflow` every 15s and stops at terminal state; current running baseline_qc was not interrupted; remote tests/deploy passed at `fb107a4` | done |

## P5 Frontend

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T050 | React 项目骨架 | frontend | T020 | frontend/src | React/Vite app 由 Docker nginx 在 12959 提供访问 | done |
| T051 | Submit Analysis 页面 | frontend | T022,T023 | PGT-A server-path form UI | 填写 rawdata_root、扫描候选样本、勾选后创建 run，并可从 created run 提交 `bio_pgta` metadata | done |
| T052 | Runs Dashboard | frontend | T024 | run list/status cards | 可筛选 pipeline/status | done |
| T053 | Run Detail 页面 | frontend | T024,T026 | overview/airflow/snakemake tabs | 展示 rule 状态 | done |
| T054 | QC 面板 | frontend | T060 | WES mock QC panel | Run detail 显示 WES/PGT-A QC pass/warn/fail/unknown summary 和样本级指标表；frontend Docker test target 14 tests passed | done |
| T055 | Log Viewer | frontend | T025 | stdout/stderr tail | 失败默认显示 stderr | done |
| T056 | Reanalysis UI | frontend/backend | T044 | WES mock create/submit panel plus resume/rerun buttons | 前端 Docker test target 10 tests passed；WES detail can trigger `resume` and `rerun_rule` via backend | done |
| T057 | PGT-A run detail 展示 | frontend | T027,T035,T025 | pgta run overview/sample/rule/log/artifact/sync UI | PGT-A run detail v1 可查看 rules/logs/artifacts；T084 failure smoke 后失败摘要可通过现有 detail/logs API 查看 | done |
| T096 | Frontend platform UI redesign v2 | frontend/docs | T050-T057,T054,T056 | routed app shell, Dashboard/Submit/Runs/Run Detail/Samples/Workflows/Failures/Settings, shared components, design docs | remote frontend Docker test target passed 7 tests; frontend production build passed `tsc -b && vite build`; 12959 HTTP 200; PGT-A/WES backend API spot checks passed | done |
| T097 | PGT-A-only frontend deployment scope | frontend/docs | T096,T027,T087,T092 | Sidebar/Dashboard/Submit/Runs/Samples/Failures scoped to PGT-A; WES/NIPT/WGS hidden from deployable demo; docs/state updated | remote frontend Docker test target passed 5 PGT-A-only tests; frontend build/deploy on 12959 verified; mail notification remains todo and WES qsub historical code remains untouched | done |
| T098 | PGT-A frontend/Airflow data reconciliation | frontend/backend/docs | T097,T090,T087,T092 | active PGT-A detail auto-sync through backend `sync-airflow`; `/api/runs` run-level QC aggregation from samples; docs/state updated | remote backend pytest passed 53 tests; remote frontend Docker test target passed 6 tests; backend/frontend build and redeploy passed; `PGTA_20260706_162150_00C4FD` list/detail/Airflow latest state reconciled as workflow success + QC fail | done |
| T099 | PGT-A Dashboard run tracker and submit handoff | frontend/docs | T098,T097,T027 | Dashboard uses one project/run-centric PGT-A tracker with progress estimate, filters, View/Submit/Sync actions, bottom health panels; Submit Task uses primary create+submit handoff, secondary create-only, and folder-based scan results | remote frontend Docker test target passed 7 tests; frontend production build passed `tsc -b && vite build`; frontend 12959 HTTP 200; PGT-A list/detail spot checks confirmed `PGTA_20260707_182024_8CA2A0` and `PGTA_20260707_182056_39A374` have non-null `dag_run_id` and `status=success` | done |
| T100 | PGT-A submit 后 Airflow 状态自动回写 | frontend/docs | T099,T098,T027 | Submit Task 在 create+submit 后主动调用 `sync-airflow` 并短轮询 handoff 状态；Dashboard 对 active/submitted tracker rows 立即 sync 并每 15 秒 sync；记录 submitted 卡住根因 | red frontend test first failed on missing sync calls; remote frontend Docker test target passed 7 tests; frontend production build/deploy passed; `PGTA_20260708_012630_352915` was reconciled from backend `submitted` to Airflow/backend `success`; submitted PGT-A list returned empty | done |
| T101 | NIPT Docker template-run deployment | backend/airflow/frontend/docs | T033,T071,T072,T099,T100 | `pipeline=nipt_docker` API create/submit, `bio_nipt_docker` DAG, repo-owned Docker runner, NIPT QC/log/artifact integration, PGT-A + NIPT Docker frontend scope, docs/state updates | remote frontend test passed 9 tests; backend targeted tests passed 31 then 17 after artifact fix; NIPT DAG/runner tests passed 9; compose config/build/recreate passed; final smoke `NIPT_20260708_033450_8362A0` reached Airflow/backend success with QC `pass=96` | done |
| T102 | Airflow + Snakemake progress observability | backend/airflow/snakemake/frontend/docs | T099,T100,T101,T026,T043 | `/api/runs/{analysis_id}/progress`, Airflow task-instance client, PGT-A/NIPT runner progress events with JSONL fallback, Dashboard/Run Detail progress UI, docs/state updates | remote backend targeted tests passed 29; Airflow DAG/runner tests passed 35; frontend Docker test target passed 10; deploy/recreate passed; progress smokes `PGTA_20260708_050811_A24E36` and `NIPT_20260708_050843_B3B05E` returned Airflow tasks plus pipeline events | done |
| T103 | PGT-A/NIPT batch scan and auto intake | backend/airflow/frontend/docs | T101,T102,T022,T027 | NIPT Docker server-path scan replaces new run1/run2 submissions; `intake_discovery`; `/api/input/roots`; `/api/intake/status`; `/api/intake/scan-and-submit`; `bio_intake_scan`; Dashboard intake panel; Submit one-run-per-NIPT-batch | remote compose config passed; frontend Docker test passed 10; backend targeted pytest passed 25; Airflow DAG tests passed 4 and NIPT runner/progress tests passed 12; deploy/recreate/migration passed; scanned NIPT smoke `NIPT_20260708_072349_4F942A` reached success; intake bootstrap recorded existing batches without auto-submit | done |
| T104 | Dashboard performance, observability, and intake config | backend/frontend/docs | T103,T102 | `/api/dashboard/overview`; `/api/dashboard/runs`; `/api/system/resources`; `/api/intake/config`; `config/intake.yaml`; Dashboard pipeline selector, charts, paginated Run Tracker, resource tabs, and non-queued intake states | remote frontend Docker test passed 10; backend targeted pytest passed 7; final compose/deploy/runtime curl checks recorded in HANDOFF | done |
| T105 | Intake settings and scanner readiness console | backend/frontend/docs | T104,T103 | `GET /api/intake/scanner-state`; Settings read-only Intake Scanner console; config/status/scanner-state visibility; no unpause/scan-now/full-run frontend actions | remote backend targeted pytest passed 10; frontend Docker test target passed 11; backend/frontend build/recreate passed; `/api/intake/scanner-state` returned `airflow_reachable=true,is_paused=true`; `bio_intake_scan` remained paused | done |
| T106 | Intake dry-run preview and auto-submit gating | backend/frontend/docs | T105,T104,T103 | `POST /api/intake/scan-preview`; `scan-and-submit` obeys global and pipeline `auto_submit.enabled` gates; Settings dry-run preview; default config keeps PGT-A/NIPT auto-submit disabled | remote compose config passed; backend targeted pytest passed 8; frontend Docker test target passed 11; backend/frontend build/recreate passed; preview returned `would_submit=0` and left discovery `21/21` plus NIPT runs `5/5`; `bio_intake_scan` remained paused | done |
| T107 | UI density fix and PGT-A DAG stages | frontend/airflow/backend/docs | T106,T102,T087,T095 | Submit preview definition layout; Samples source-file formatter; QC matrix with search/filter/pagination; PGT-A baseline_qc TaskGroup stages; staged progress weights and artifacts | remote compose config passed; frontend Docker test passed 13; backend targeted pytest passed 19; Airflow DAG/runner unittest passed 27; Airflow import check passed; backend/Airflow/frontend redeployed; `bio_pgta` task tree shows staged TaskGroup; metadata smoke `PGTA_20260708_141653_B57AB6` reached success; no heavy baseline_qc run started | done |
| T108 | Dashboard/Run Detail usability polish and controlled PGT-A rerun | frontend/backend/airflow/docs | T107,T104,T102,T095 | Dashboard sample throughput, table Run Tracker, readable current stage, ETA estimate, compact Intake scanner, Run Detail manifest/QC failure/config polish, controlled PGT-A `rerun_stage` | remote compose config passed; frontend Docker test passed 14; backend targeted pytest passed 25; Airflow DAG/runner unittest passed 28; backend/Airflow/frontend rebuilt and recreated; Dashboard APIs returned sample throughput/current-stage/ETA fields; light PGT-A metadata smoke `PGTA_20260708_160227_EFAD64` reached success; no intake unpause, no heavy baseline_qc, no NIPT full_run | done |
| T109 | PGT-A/NIPT Control Tower frontend polish | frontend/docs | T108,T104,T102 | Control Tower navigation labels, theme tokens, dark sidebar, Dashboard command summary, Submit Run stepper, Run Detail layered timeline, frontend-only stage labels | remote frontend Docker test target passed 14 Vitest tests; compose config passed in deployment dir; frontend image built from clean T109 worktree and 12959 returned HTTP 200; no backend API/DAG/intake/full-run behavior changes | done |
| T110 | Operator Workspace stability and action closure | backend/frontend/docs | T109,T108,T104 | responsive Control Tower; independent Dashboard loading boundaries; paginated Runs/Samples/Failures resources; aggregate failure diagnosis; feature component split | remote backend pytest passed 94; frontend Docker test passed 20; production `tsc -b && vite build` passed; final dashboard median warm response was about 33 ms with no active runs; 24 live-data browser viewport/page combinations passed without document horizontal overflow; backend/frontend redeployed only; intake remained paused and no workflow was triggered | done |
| T111 | Snakemake config editor and runtime profiles | backend/airflow/frontend/docs | T110,T107,T101 | approved PGT-A/NIPT runtime profiles; collapsed validated YAML editor; immutable requested/resolved config provenance; Compose hidden from frontend | remote backend pytest passed 103; Airflow unittest passed 74 with 5 expected skips; frontend Docker test passed 24 and production build passed; final reviewed-profile smokes `PGTA_20260710_110056_DC8A8D` and `NIPT_20260710_110057_79A631` reached success with resolved provenance; browser checks passed at 1440/390; intake remained paused | done |
| T112 | PGT-A Snakemake 9 predict and manifest intake | backend/airflow/snakemake/frontend/docs/qa | T111,T107,T103 | immutable PGT-A S9 release, predict-only profile, TaskGroup stages, rule logger, submitted/progress audit, QC/log index, full-sample and manifest validation | `pgta-s9-v1.4` deployed with full release checksum verification; 2 x 1M, full H3, and full H4/H5 manifest runs passed; READY mutation and crash-window duplication are blocked; scanner/events use service auth; PGT-A intake unpaused while NIPT auto-submit/full-run remain disabled; backend 113, Airflow 79 (5 expected skips), logger 5, frontend 25 tests passed | done |
| T113 | NIPT Snakemake 9 full analysis and live rule observability | backend/airflow/snakemake/frontend/docs/qa | T112,T111,T102 | derivative dual-runtime image; approved full profile; one-slot DAG gate; real-time logger forwarding; phase/rule/sample progress; paginated jobs/logs; 72-sample S7 comparison | 72-sample S9 run completed 591 jobs in about 24.8 minutes with 44.61 GiB observed peak memory; 592 persisted events all terminal success; key outputs byte-identical to S7 baseline; original image/bundle/input unchanged; offline OCI rollback archive generated; NIPT auto intake remains disabled | done |
| T114 | Run status, immutable timing, NIPT QC, and biodemo cleanup | backend/airflow/frontend/docs/qa | T113,T112,T110 | combined workflow/QC status; submit-to-first-finish timing; sample-count ETA; decision-metric QC; prediction output integrity; guarded CLI cleanup | backend 127, Airflow/runner 89 with 5 expected skips, frontend 28 passed; NIPT 72/72 sample QC pass with 504 metrics and 24m37s runtime; biodemo backed up then reduced from 49 to 3 complete runs and 75 samples; workdirs/Airflow history/FASTQ preserved | done |
| T115 | Platform Settings and Discovery Tracker consistency | backend/frontend/docs/qa | T114,T110,T105 | paginated/filterable intake status API; shared Dashboard/Settings discovery table; independent Settings loading states; responsive Settings layout | backend 129 and frontend 36 tests passed; production build and Compose config passed; live Settings had no document overflow at 1440/1280/1024/390; 25 discovery records paginate without changing the retained 3 runs or scanner state | done |
| T116 | Intake and Airflow strict history cleanup | backend/airflow/infra/docs/qa | T115,T114,T113,T112 | exact-snapshot CLI cleanup for discovery and Airflow history; PGT-A-only scheduled intake; legacy DAG deployment ignore; pg_dump-backed remote maintenance | backend 134 and DAG 90 tests passed with 5 expected skips; Airflow retained 2 PGT-A + 1 NIPT full runs and only three deployed DAGs; discovery reduced 25 to 1; scanner restored unpaused and a new PGT-A-only cycle did not recreate old rows | done |
| T117 | Submit semantics, workflow phase visualization, and PGT-A manifest recovery | backend/frontend/infra/docs/qa | T116,T112,T110 | remembered free-text Submitted by ID; low-pass WGS assay labels; bulk workflow summaries; selected/alternate Airflow paths; audited operator correction; recoverable pre-run manifest errors | backend 139, frontend 38, DAG 90 with 5 expected skips, production build and Compose passed; two retained PGT-A operators corrected to jiucheng; project-20260712 created one four-sample run PGTA_20260712_171630_AE8239 and entered Mapping without duplicate submission | done |
| T118 | PGT-A manifest hardening, five-sample auto intake, and scanner retention audit | backend/infra/docs/qa | T117,T116,T112 | ignore blank manifest lines; protect submitted discovery; recover stale state; atomically publish five-sample request; measure scanner growth | backend 141 passed; stale T112 discovery restored; project-20260713-five-samples created only PGTA_20260713_034634_939AFF and entered Mapping; scanner remained unpaused; 30-day scanner retention and Docker log rotation documented for a separate rollout | done |
| T119 | Operations age, Intake archive, and NIPT small-batch validation | backend/frontend/airflow/infra/docs/qa | T118,T115,T113 | terminal relative age; shared operations search; active/archived Intake lifecycle; PGT-A manifest archive; restricted NIPT discovery root; checksum-verified 10/15/20-sample manual full runs | migration applied; 6 completed discoveries archived and active=0; NIPT 10/15/20 runs reached success with 96/136/176 terminal events and all 45 samples QC pass; backend 168, frontend 40, DAG 3, build/Compose/browser checks passed; NIPT auto-submit remains disabled | done |
| T120 | NIPT YAML request parsing and explicit intake trigger | backend/infra/docs/qa | T119,T113 | path-free YAML request contract; approved-root batch resolution; sample selection; stable-scan and explicit-submit gates; request-only archive; dedicated backend inbox mount | parser and intake tests pass remotely; full backend regression and Compose config pass; deployment inbox is empty during acceptance; ordinary NIPT directory auto-submit remains disabled | done |
| T121 | PGT-A Intake error visibility and manifest template correction | backend/frontend/docs/qa | T120,T119,T118 | explicit Intake validation stage; visible `last_error` in shared Dashboard/Settings table; corrected non-trigger PGT-A manifest template | backend 181 and frontend 40 tests pass; production build/Compose/HTTP pass; live API exposes the path error; corrected two-sample `.par.tsv` resolves uniquely without publishing trigger files | done |
| T122 | NIPT Intake completed-run visibility and refresh | frontend/docs/qa | T121,T120,T119 | Dashboard/Settings default All lifecycle; Intake refresh after Airflow sync/submit; display status contract regression | frontend 40 tests and production build pass; deployed Dashboard bundle queries all lifecycle records; latest 72-sample NIPT appears as success/100%/Completed while scanner and backend remain unchanged | done |

## P6 QC/日志/报告/邮件

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T060 | QC parser | backend/snakemake | T021,T040 | WES mock `reports/qc_summary.tsv` + `qc_metric` 写库 + `/api/runs/{analysis_id}/qc` | `WES_20260705_164813_C5561C` sync 后 `/qc` 返回 6 条 pass metrics；重复 sync 幂等；artifacts include `wes_qc_summary` | done |
| T061 | MultiQC/Snakemake report artifact | snakemake/backend | T040,T060 | report link | artifact 表有记录 | todo |
| T062 | PGT-A run-level error summary extractor | backend | T025,T027,T035 | run-level Airflow sync + stderr summary | PGT-A run-level `error_summary` 已完成；rule 状态基础已由 T026/T043 入库，WES mock qsub stdout/stderr 事件路径已由 T041/T042 验证 | done |
| T063 | 邮件模板 | backend/airflow | T034,T060 | success/fail emails | 邮件含 QC 和错误链接 | todo |
| T087 | PGT-A baseline QC artifact/QC visibility | backend/frontend/docs | T086 | baseline QC artifacts + qc_metric import | artifacts 动态发现 `baseline_qc_summary/pass_samples/report`；sync success 后可导入 baseline QC metrics；远端 backend tests 覆盖 parser/import/artifacts；真实 run smoke 待用户确认 | done |

## P7 NIPT 接入

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T070 | NIPT qsub wrapper 设计 | snakemake | T032,T041 | pipelines/nipt_qsub | mock dry-run 通过 | todo |
| T071 | NIPT Docker runner | infra/snakemake | T033 | `dags/nipt_docker_runner.py` scanned-batch v1 with legacy template compatibility | `mount_smoke` executes host Docker through airflow-worker socket, mounts scanned source batch read-only as `/input_batch`, writes command/stdout/stderr, no `down -v` or prune; full_run remains gated and is enabled for supervised manual use by T113 | done |
| T072 | NIPT QC parser | backend/snakemake | T060,T071 | NIPT metrics in `reports/qc_summary.tsv` | `sync-airflow` imports NIPT QC metrics and updates `sample.qc_status`; scanned smoke `NIPT_20260708_072349_4F942A` returned `pass=1` and frontend/API can display NIPT QC | done |

## P8 Demo 验收

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T080 | 端到端 smoke test | qa | T050-T063 | docs/21_DEMO_SMOKE_REPORT.md | PGT-A workflow success/QC fail、WES mock QC success、WES rerun_rule without forceall 均有远端只读证据；未提交新的重型 PGT-A run | done |
| T081 | Demo script | docs/coordinator | T080 | docs/17_DEMO_SCRIPT.md | 10-15 分钟演示脚本已更新，明确普通用户主入口是前端，PGT-A workflow success 与 QC fail 分开讲 | done |
| T082 | 回滚和清理 runbook | infra/docs | T080 | docs/11 更新 | 不删除 volume 的停止流程清楚 | todo |
| T083 | 最终交接 | coordinator | T080-T082 | HANDOFF/CURRENT_STATE | 下一阶段任务明确 | todo |
| T084 | PGT-A Level 0-3 smoke 验收 | qa | T014,T027,T035,T045,T057 | acceptance report | preflight、metadata、dry-run、failure smoke 记录完整；`dryrun_cnv=PGTA_20260703_170917_20E8F2` success，`invalid_target=PGTA_20260703_170957_3DDEC3` failed with error_summary | done |
| T092 | PGT-A baseline_qc 当前 run 收口与 64-core 生效验证 | qa/coordinator | T086,T087,T091 | current baseline_qc terminal sync evidence; 64-core resume command evidence | `PGTA_20260706_162150_00C4FD` final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` reached Airflow/backend `success`; command contains `--cores 64 --rerun-incomplete`, no `--forceall`; artifacts and `/qc` verified; QC decision is sample-level `FAIL`, not workflow failure | done |
| T093 | PGT-A 受控中断与 64-core resume | backend/airflow/frontend/qa | T086,T087,T091,T092 | PGT-A baseline_qc resume API, DAG unlock/rerun-incomplete, frontend resume button, runtime evidence | code/tests passed at `2821a5e`; old `PGTA_20260706_162150_00C4FD` `--cores 1` run was controlled-interrupted and synced failed; first resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z` used `--cores 64 --rerun-incomplete` and no `--forceall` but failed on stale samtools sort tmp BAMs; T094 supersedes runtime recovery | done |
| T094 | PGT-A resume 临时 BAM 清理与再次恢复 | airflow/backend/qa | T093 | run-local cleanup of `mapping/*.sorted.bam.tmp.*.bam`, cleanup artifact, same-workdir resume | code/tests passed at `0a8e756`; cleanup log deleted 16 stale `G11.sorted.bam.tmp.*.bam` files and remaining tmp count is 0; cleanup resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` used `--cores 64 --rerun-incomplete`, no `--forceall`, reached baseline QC, then failed on a new Python library path issue handled by T095; artifacts include `pgta_resume_cleanup` | done |
| T095 | PGT-A baseline QC Python 库路径与 preflight | airflow/backend/qa/docs | T094 | PGT-A subprocess env sets `LD_LIBRARY_PATH` to conda lib, preloads conda `libstdc++.so.6`, uses run-local `MPLCONFIGDIR`, writes `logs/pgta.python_preflight.log`, and resumes same workdir | remote Airflow tests passed; first post-`LD_LIBRARY_PATH` resume still failed preflight, `LD_PRELOAD` fix passed preflight; final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` succeeded and `/qc` imported 14 failed QC metrics | done |

## 任务卡模板

```markdown
### TXXX - <title>

Owner: <agent>
Status: todo
Dependencies: <ids>
Scope:
- 
Out of scope:
- 
Files likely touched:
- 
Acceptance:
- [ ] 
Test commands:
- 
Rollback:
- 
Notes:
```

### T124 - QC formatting, Intake alignment, and tracker ordering

Owner: frontend/backend/docs
Status: done
Dependencies: T123,T119,T114
Scope:
- Normalize PGT-A/NIPT QC display units, sort terminal runs newest-finished
  first, and align Intake project/sample/runtime cells with Run Tracker.
Out of scope:
- DAG/Snakemake changes, database migrations, scanner policy, and new analysis
  execution.
Acceptance:
- [x] Backend ordering and Intake timing tests.
- [x] Frontend QC and shared operations-cell tests.
- [x] Remote production build, deployment, API and browser spot-check.
Rollback:
- Redeploy T123 backend/frontend images; no data rollback is required.

### T123 - Predict path and operations consistency

Owner: platform/frontend/backend/airflow
Status: done
Dependencies: T121,T122
Scope:
- Predict-only PGT-A UI, consistent Run/Intake state, QC/log semantics, live
  workflow catalog, 32-core NIPT default, and scanner-only retention.
Out of scope:
- Build Reference DAG, NIPT auto-submit, WES/WGS, email notifications.
Acceptance:
- [x] Backend tests, frontend tests/build, DAG/config tests, Compose config.
- [x] Deploy and reconcile failed NIPT rule states.
- [x] Complete supervised 32-core NIPT clone acceptance.
Rollback:
- Redeploy prior images; preserve DB, workdirs, FASTQ, logs, and volumes.

### T125 - BS NIPT-only Docker network constraint documentation

Owner: infra/docs
Status: done
Dependencies: T124,T113
Scope:
- Document the immutable external Docker network contract for the BS10610
  primary and BS1069 cold standby NIPT-only deployment.
- Record the fixed project root and Snakemake 9 runtime requirement.
Out of scope:
- Compose implementation, image transfer, remote startup, database migration,
  or analysis execution.
Acceptance:
- [x] Architecture, runbook, security, server inventory, and dedicated BS
  deployment contract use the same network name, subnet, and gateway.
- [x] Documentation explicitly forbids creating, recreating, deleting, or
  substituting the external network.
Rollback:
- Revert the T125 documentation commit; no runtime rollback is required.

### T126 - BS NIPT-only Airflow platform migration

Owner: infra/backend/airflow/frontend/QA
Status: done
Dependencies: T125,T113
Scope:
- Deploy a fresh NIPT-only CeleryExecutor stack to BS10610 and load a stopped
  cold-standby image set on BS1069.
- Keep NIPTPro `1.0.11` for rollback and use the validated Snakemake 9 image as
  `1.1.11` for new full analyses.
- Transfer images only through the local Windows staging directory.
Acceptance:
- [x] Backend, DAG/runner, frontend, nginx, and Compose validation passed.
- [x] BS10610 exposes only `bio_nipt_docker` and paused `bio_intake_scan`.
- [x] 10-sample and 72-sample full analyses completed with all rule events
  terminal, all samples QC pass, and required outputs present.
- [x] 144 FASTQ checksums are identical before and after the 72-sample run.
- [x] BS1069 archives and image IDs are verified; no service is started.
Rollback:
- Pause intake, disable heavy submission, stop BS10610 services without `-v`,
  and select the retained `1.0.11` profile. Never delete the external network,
  databases, workdirs, results, logs, FASTQ, or image archives.

### T127 - BS shared NIPT and WGS Airflow control plane

Owner: infra/backend/airflow/snakemake/frontend/QA
Status: done
Dependencies: T126
Scope:
- Upgrade the existing `airflow-nipt` Compose project into one shared control
  plane for NIPT Docker and host-native WGS; PGT-A is absent on BS.
- Run WGS through restricted `SSHOperator` commands with Snakemake 9.23.1 and
  a 96-core ceiling; validate one family by default.
- Keep NIPT on the accepted Snakemake 9 Docker image and serialize both heavy
  pipelines through the one-slot `bs_heavy_analysis` pool.
- Record rule/sample progress and run resource telemetry; prepare BS1069 as a
  stopped cold standby.
Out of scope:
- PGT-A, WES, active-active scheduling, automatic intake, production workflow
  source modification, and deleting existing databases or results.
Acceptance:
- [x] Shared backend/frontend/Airflow images, API capabilities, three-DAG
  inventory, CeleryExecutor services, network, and pool are deployed.
- [x] WGS Snakemake 9 dry-run selects one family (three new samples) at 96
  cores and links only approved historical batch context.
- [x] `WGS_20260715_062217_351C76` completes an Airflow-managed one-family
  pre-calling dry-run in 12 seconds; all 21 planned jobs are terminal skipped,
  no biological rule runs, and the UI reports QC as not applicable.
- [x] Three 27-sample NIPT full batches run serially and finish success with
  27/27 QC pass and 232/232 terminal-success rule events each.
- [x] BS1069 release/config and image IDs are verified with every service
  stopped.
Rollback:
- Pause intake and stop only recreated application services without `-v`;
  restore the previous shared release/images and keep all volumes/results.

### T128 - BS NIPT manual FASTQ scan latency repair

Owner: backend/frontend/infra/QA
Status: in_progress
Dependencies: T127
Scope:
- Replace eager full-tree NIPT FASTQ discovery with deterministic lazy traversal
  that stops as soon as the requested sample limit is reached.
- Narrow the BS manual-scan default from `/data/nipt-fastq` to
  `/data/nipt-fastq/FQ2026` while preserving the existing read-only mount and
  historical run paths.
- Make Submit Run adopt the backend-provided root instead of retaining a stale
  frontend fallback.
Out of scope:
- Creating or submitting a NIPT run, unpausing Intake, moving/deleting FASTQ,
  database changes, or changing the NIPT workflow.
Acceptance:
- [x] Reproduce nginx 504 on the old full-root scan and verify a specific batch
  remains readable.
- [x] Backend regression test proves scan does not materialize the full tree.
- [ ] Deploy backend/frontend to BS10610 and verify an FQ2026 scan returns
  candidates before the gateway timeout.
- [ ] Load the same release/images on BS1069 while keeping all services stopped.
Rollback:
- Restore the T127 backend/frontend images and release pointer. Do not change
  databases, volumes, FASTQ, results, or the external Docker network.
### T133 - WGS 4.0.1 single-DAG refactor

Owner: airflow/backend/observer/QA

Status: todo (design confirmed; implementation not started)

Dependencies: T132 WGS 4.0.1 baseline

Scope:
- Replace the current paused `bio_wgs_cce`, `bio_wgs_onprem`, and
  `bio_wgs_intake_scan` legacy layout with one CCE-only `bio_wgs` DAG.
- Move the ten-minute automatic scan into `wgs-observer`.
- Remove standalone FASTQ MD5 generation/wait and `verify_input_obs`; Step1
  owns upload completion and Step2 owns its internal launch precondition.
- Replace persistent Master Deployment/fixed-slot assumptions with one
  batch-specific Master Job per analysis.
- Consume native `run-state.json`, `events.ndjson`,
  `RUN_COMPLETE.json`, and `RUN_FAILED.json`; add a separate Snakemake Rule
  logger JSONL because native batch events are not Rule events.
- Keep node005 private OBS transfer separate from BS10610 kubectl/CCE.
- Install/connect the logger only in Master for Rule JSONL; use a BS10610 host
  watcher only for the batch Master Job/Pod. Do not install a logger in every
  Worker Pod and do not continuously project Worker Pod state.
- Keep native `jobs.ndjson` only for administrator diagnostics; no
  Rule-to-Worker-Pod mapping or receipt schema extension is required.
- Do not automate Step7/Step8 cleanup.

Acceptance:
- [x] Target architecture and current legacy status documented consistently.
- [x] 4.0.1 code audit corrected the obsolete FASTQ hash/verify design and
  documented the Rule-first and Master-only monitoring scope.
- [ ] Only `bio_wgs` is loaded in the disabled-mode candidate release.
- [ ] Observer scanner, Master Job adapter, Rule/Master reconciliation, and
  result verification pass synthetic acceptance.
- [ ] Real CCE/OBS execution remains disabled until a separate approval and
  real-runtime acceptance.

Rollback:
- Documentation can be reverted without service or data rollback. Future code
  work must preserve current DAG pause and execution gates until acceptance.

### T131 - WGS cloud data orchestration Phase 1

Owner: platform/backend/airflow/frontend/infra/QA
Status: done
Dependencies: T130
Scope:
- Replace READY/source-path intake with batch number plus controlled FASTQ
  symbolic-link directory.
- Add immutable snapshot, review issues, monitored transfer projection,
  Rule/analysis ETA, paused full DAG topology and Phase-1 mock adapters.
- Deploy on BS10610 only; keep real WGS/CCE/OBS execution disabled.
Acceptance:
- [x] BS10610 Docker backend focused tests: 23 passed.
- [x] Runtime DAG topology: 27 nodes, six reschedule sensors, paused.
- [x] Alembic 0001->0008 test DB and production 0007->0008 migration passed.
- [x] Frontend focused tests 7 passed and production build passed; image runs
  on BS10610 with the new batch/path form.
- [x] Synthetic BS10610 API smoke generated manifest/sampleinfo/config and
  submit returned 409 without starting CCE.
- [x] External network/IP and only-one-published-port contract preserved.
Rollback:
- Repoint `current` to the previous release and recreate application services
  without `-v`; migration 0008 is additive and may remain. Never delete data,
  volumes, network, WGS sources, FASTQ, evidence or results.
