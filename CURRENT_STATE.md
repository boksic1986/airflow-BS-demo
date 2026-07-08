# CURRENT_STATE.md

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
current_goal_ascii: T108 Dashboard/Run Detail usability polish and controlled PGT-A rerun is validated and deployed on fengxian; automatic intake remains disabled and bio_intake_scan remains paused pending operator approval.
当前阶段: P3/P4/P6 Airflow + Snakemake/qsub mock observability + PGT-A Level 4 staged integration
当前目标: T100 PGT-A submit 后 Airflow 状态自动回写已部署；当前前端展示收敛为 PGT-A-only，Dashboard 以 project/run 为主轴展示 PGT-A 运行状态、进度估算和 Airflow handoff，Submit Task 默认 create+submit 到 Airflow 并主动 sync Airflow 终态。
最近更新时间: 2026-07-08
最后更新 agent: Codex
```

## 2. 服务器信息

详见 `SERVER_INFO.md`。不得在此处写入密码或 token。

```text
server_host: fengxian
deploy_user: jiucheng
project_root: /home/jiucheng/project/airflow-demo
docker_available: true on fengxian read-only preflight
docker_compose_available: true, Docker Compose version v2.24.7 at $HOME/.docker/cli-plugins/docker-compose
qsub_available: false on fengxian read-only probe 2026-07-04; mock qsub wrapper available in repo
snakemake_available: true for PGT-A at /biosoftware/miniconda/envs/snakemake_env/bin/snakemake and /biosoftware/miniconda/envs/snakemake9_env/bin/snakemake
python_version: PGT-A locked python 3.12.2
node_version: <unknown>
```

## 3. 仓库状态

```text
repo_url: git@github.com:boksic1986/airflow-BS-demo.git
main_branch: main
active_branch: codex/frontend/T108-dashboard-run-detail-usability in local worktree; local `main` and `origin/main` have been fast-forwarded to the T108 validated code commit `0857e3d`
last_verified_code_commit: 0857e3d for T108 Dashboard/Run Detail usability polish and controlled PGT-A rerun; remote runtime validation was performed on the same source tree before commit
worktree_strategy: single-worktree for now; fengxian is code mirror only
fengxian_mirror: /home/jiucheng/project/airflow-demo cloned from GitHub; T108 overlay is deployed there and `origin/main` on the mirror has been fetched to `0857e3d`, but the mirror worktree itself remains on its existing dirty deployment branch
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 12959 | running after T108 redeploy | React/Vite PGT-A + NIPT Docker routed UI served by Docker nginx image `airflow-demo/frontend:0.1.0`; Dashboard is pipeline-driven with Sample throughput, compact Intake scanner, 10-row paginated table Run Tracker, readable current stage, runtime/ETA, resource tabs, and workflow activity; Settings includes a read-only Intake Scanner console and dry-run preview for configured roots; Submit Task still uses server-path scan for both PGT-A and NIPT Docker; host 3000 is occupied by non-project next-server |
| backend | 8000 | running, healthy after T108 redeploy | `/api/health`, `/api/health/db`, `/api/input/roots`, `/api/input/scan`, `/api/intake/status`, `/api/intake/config`, `/api/intake/scanner-state`, `/api/intake/scan-preview`, `/api/intake/scan-and-submit`, `/api/dashboard/overview`, `/api/dashboard/runs`, `/api/system/resources`, `/api/runs`, run detail/samples, submit, sync-airflow, controlled PGT-A reanalyze, logs, artifacts, `/api/events/snakemake`, `/api/runs/{analysis_id}/rules`, `/api/runs/{analysis_id}/qc`, and `/api/runs/{analysis_id}/progress` are available; scanner roots and NIPT auto-intake run creation roots come from `config/intake.yaml` with env fallback; default auto-submit gates are disabled; image `airflow-demo/backend:0.1.0`; container `TZ=Asia/Shanghai` |
| airflow web/api | 12958 | running; `PGTA_20260706_162150_00C4FD` final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` ended `success` after T095 `LD_PRELOAD` fix; previous T095-only-`LD_LIBRARY_PATH` attempt `manual__PGTA_20260706_162150_00C4FD__resume__20260707T143132Z` failed preflight | project image `airflow-demo/airflow:0.1.0`; Airflow core/UI timezone is `Asia/Shanghai`; T095 sets run-local `XDG_CACHE_HOME`, `MPLCONFIGDIR`, `LD_LIBRARY_PATH=PGTA_CONDA_LIB`, and `LD_PRELOAD=PGTA_LIBSTDCXX`; `logs/pgta.python_preflight.log` records env header and import versions |
| postgres | internal 5432 | running, healthy | image `postgres:15-alpine`; Airflow metadata initialized; no host port published |
| redis | internal 6379 | running, healthy | image `redis:7-alpine`; no host port published |
| mailhog | 8025 | stopped in T051 smoke | HTTP GET probe passed in earlier smoke; not started for T051 |

## 5. 数据库状态

```text
airflow_metadata_db: initialized by `docker compose -f docker-compose.yaml up airflow-init`; admin user exists, password only in remote .env
biodemo_db: initialized on fengxian by `docker compose -f docker-compose.yaml run --rm biodemo-db-init`
migrations_tool: Alembic
last_migration: 20260708_0002 intake discovery table
core_tables: pipeline, analysis_run, sample, snakemake_rule_event, qc_metric, artifact, run_action, intake_discovery
```

## 6. Pipeline 接入状态

| Pipeline | DAG | Snakemake | qsub | Docker | QC | Status |
|---|---|---|---|---|---|---|
| PGT-A demo | `bio_pgta` metadata/dryrun/failure smoke passed; `bio_pgta_airflow` Airflow-only logger/event POST passed; `baseline_qc` staged real run `PGTA_20260706_162150_00C4FD` completed after controlled interrupt/resume sequence; final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` ended Airflow/backend `success` | direct Snakemake metadata target, `dryrun_cnv`, controlled `invalid_target`, and Level 4 `baseline_qc` smoke in Airflow worker passed; T088 sets `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`; T093 resume runs `--unlock` then `--cores 64 --rerun-incomplete`, no `--forceall`; T094 adds run-local cleanup of `mapping/*.sorted.bam.tmp.*.bam`; T095 sets conda `LD_LIBRARY_PATH`, `LD_PRELOAD=PGTA_LIBSTDCXX`, run-local `MPLCONFIGDIR`, and baseline QC Python preflight; Snakemake 9.23.1 logger plugin writes JSONL, Airflow log/XCom summary, and optional backend rule/job events | not used | server-path project creation, submit, status sync, logs, artifacts, rule event API, PGT-A run detail frontend v1, New PGT-A Run frontend scan/create/submit, active-run auto-sync, failed baseline_qc `Resume with 64 cores`, and QC/artifact panel API are available | baseline_qc parser/artifacts added; `/qc` imports 14 metrics for G10/G11 and both samples have QC decision `FAIL` | `/api/input/scan` and `/api/runs` create `created` run; submit triggers `bio_pgta`; Airflow-only manifest run can POST rule events to biodemo; frontend can create pgta runs for metadata/dryrun/failure/baseline_qc smoke, submit created runs, view run list/detail, samples, rules, logs, artifacts, QC, sync Airflow, and resume failed baseline_qc |
| WES qsub | `bio_wes_qsub` Airflow mock DAG passed with `new/resume/rerun_rule` and QC smoke | WES mock Snakefile dry-run passed; WES mock profile runtime passed in `snakemake-runner`; `bio_wes_qsub` runs Snakemake 9.23.1 inside Airflow worker with `profiles/qsub`, writes command/stdout/stderr/events and `reports/qc_summary.tsv` | mock qsub wrapper direct smoke passed with backend POST; Airflow/API/frontend smoke generated mock qsub job ids, stdout/stderr files, JSONL events, and command log proving `--forcerun fastp` without `--forceall` | `airflow-demo/snakemake-runner:0.1.0` and `airflow-demo/airflow:0.1.0` builds passed | WES mock QC parser and frontend QC panel done; real WES QC and MultiQC not started | T040/T041/T042/T030/T031/T044/T056/T060/T054 done; next step is T034/T063 MailHog notification or T080 smoke report/demo script |
| NIPT qsub | not started | not started | not started | n/a | not started | pending |
| NIPT docker | `bio_nipt_docker` scanned-batch v1 deployed; new submissions use `/api/input/scan` clean FASTQ candidates and no `template_id`; `mount_smoke` `NIPT_20260708_072349_4F942A` passed with `/progress` Airflow tasks plus `nipt_mount_smoke` | Dockerized runner, not qsub; `full_run` remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`; legacy run1/run2 remains compatibility-only | n/a | host Docker via airflow-worker socket; worker has Docker socket group access on `fengxian`; source batch mounted read-only as `/input_batch` | `mount_smoke` QC import passed with 1 pass row for scanned sample `PC-20250103-3.A22`; full-run parser code present but not heavy-runtime accepted | done for scanned-batch `mount_smoke`; auto-intake bootstrap recorded existing batches as `observed/bootstrap`; heavy `full_run` deferred until explicit approval |

## 7. 最近测试结果

```text
last_backend_tests: remote Dockerized pytest on fengxian for T108 passed, 25 tests; covered dashboard sample throughput/current-stage/ETA fields, controlled PGT-A reanalysis validation, progress compatibility, and diagnostics.
last_frontend_tests: remote Dockerized frontend test target on fengxian for T108 passed, 14 Vitest tests; covers Sample throughput, compact Intake scanner, table Run Tracker, clickable Project/Run ID links, readable Current stage, ETA display, Run Detail manifest/QC failure/config views, and controlled Run action modal.
last_dag_import_tests: passed on fengxian for T108; Airflow test image unittest passed 28 tests for `bio_pgta` TaskGroup branching, controlled `rerun_stage`, and PGT-A runner resume/rerun flags.
last_snakemake_dryrun: passed on fengxian; `dryrun_cnv` run `PGTA_20260703_170917_20E8F2` ended Airflow/backend `success`, stdout log size 12677 bytes and recorded 7 dry-run jobs, stderr only had config-extension notice, artifacts returned stdout/stderr/config files
last_compose_config: passed on fengxian for T108 with `docker compose -f docker-compose.yaml config --quiet`; backend, airflow-worker, airflow-scheduler, and frontend images rebuilt; frontend production build ran `tsc -b && vite build`; backend/Airflow/frontend recreated without deleting volumes; `http://127.0.0.1:12959/` returned HTTP 200; `/api/health` ok; `/api/dashboard/overview?pipeline=all&period=7d`, `/api/dashboard/runs?pipeline=all&limit=10&offset=0`, `/api/system/resources`, and `/api/intake/status?limit=5` returned structured data.
last_minimal_smoke: passed on fengxian for postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker, then docker compose down
last_airflow_health: passed on fengxian at http://127.0.0.1:12958/health with healthy metadatabase and scheduler
last_biodemo_migration: `biodemo-db-init` first run created role/database, repeat run succeeded; T103 `alembic upgrade head` applied 20260708_0002 `intake_discovery`
last_backend_airflow_client: mock tests covered health/list/get/trigger; real smoke verified backend `/api/health/airflow` against Airflow `/health`
last_backend_build: backend image built on fengxian using `backend/pip.conf` TUNA PyPI mirror and `/opt/venv`; dependency install step dropped from about 9 minutes to about 11 seconds after mirror config
last_pgta_project_create_smoke: passed on fengxian; scan root `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` returned 5 candidates with `truncated=true`, created `PGTA_20260702_162531_74CE91` with 2 samples, status `created`, `dag_run_id=null`, and generated `samples.selected.tsv` plus `request.json`
last_pgta_submit_metadata_smoke: passed on fengxian for T107; created/submitted `PGTA_20260708_141653_B57AB6`, backend status `success`, `dag_run_id=manual__PGTA_20260708_141653_B57AB6`, progress current_step `metadata`, and the new `bio_pgta` task tree shows both the historical metadata branch and the staged baseline_qc TaskGroup
last_pgta_t108_metadata_smoke: passed on fengxian; created/submitted `PGTA_20260708_160227_EFAD64` with target `metadata`, backend sync returned `success`, `dag_run_id=manual__PGTA_20260708_160227_EFAD64`, progress returned `percent=100`, Airflow task instances, and Snakemake rule event `metadata=success`; no heavy baseline_qc run was started.
last_pgta_diagnostics_smoke: passed on fengxian; `sync-airflow` changed `PGTA_20260702_171533_9A85B1` to `success` with `error_summary=null`, changed historical failed `PGTA_20260702_171200_A68C19` to `failed` with non-null `error_summary`, log API read metadata/stderr, artifact API returned metadata/stdout/stderr/config files, and missing log returned `LOG_NOT_FOUND`
last_pgta_airflow_logger_smoke: passed on fengxian; `bio_pgta_airflow` run `manual__PGTA_AIRFLOW_20260703_054712_501D8B_events` ended `success`, generated `run_metadata.tsv` (11 lines), `snakemake_events.jsonl` (22 lines), `snakemake_rule_summary.tsv` (29 lines), and `/api/runs/PGTA_20260703_054712_501D8B/rules` returned `all=success` and `collect_run_metadata=success`
last_frontend_run_detail_smoke: passed on fengxian at http://127.0.0.1:12959/; React HTML served, `/api/runs?pipeline=pgta` returned existing PGT-A runs, `PGTA_20260703_054712_501D8B` rules returned `all=success` and `collect_run_metadata=success`, metadata log/artifacts/samples APIs returned data, CORS preflight returned 200
last_frontend_submit_smoke: passed on fengxian; frontend HTML served at `http://127.0.0.1:12959/`, API scan of `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` returned 1 candidate with `truncated=true`, created `PGTA_20260703_154341_408A29`, submit returned `dag_run_id=manual__PGTA_20260703_154341_408A29`, sync ended `success`, artifacts returned 5 items, metadata log tail returned 3 lines, and run list contained the new run
last_frontend_submit_workspace_fix: passed on fengxian; red test first failed because `Submit new analysis` region was missing and `New PGT-A Run` lived inside the run-list aside, then frontend Docker test target passed with 12 tests after moving submit panels to main content; `docker compose build frontend` succeeded and `docker compose up -d frontend` redeployed 12959, with HTTP 200 and deployed CSS containing `submit-workspace`
last_pgta_level4_audit: 2026-07-06 read-only audit on fengxian confirmed `/home/jiucheng/pipelines/PGT_A/Snakefile` has real `baseline_qc`, it requires at least 2 baseline/reference samples and emits `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, and `baseline_qc_report.md`; no real Level 4 run executed in this audit
last_pgta_baseline_staged_integration: passed code-level remote validation on fengxian at commit 4cf6f6e; backend/frontend/Airflow images built, backend pytest 48 passed, frontend Vitest 14 passed, DAG unittest 14 passed, Airflow import errors `No data found`, frontend HTTP 200, backend `/api/health` ok, Airflow `/health` healthy after startup; no real baseline_qc run was executed
last_pgta_cache_fix_smoke: passed on fengxian at commit dd5c6e7; tests first failed on missing `workdir/tmp/xdg-cache`, then passed after setting `XDG_CACHE_HOME`; new metadata run `PGTA_20260706_140854_8F2CA4` submitted to `bio_pgta`, sync progressed running -> success, Airflow listed the DAG run as success, `logs/run_metadata.tsv` has 11 lines, artifacts include `snakemake_command`, and stderr no longer contains `/home/airflow/.cache/snakemake` PermissionError
last_timezone_alignment: passed on fengxian at commit f2fdff2; `docker compose config --quiet` rendered `AIRFLOW__CORE__DEFAULT_TIMEZONE=Asia/Shanghai`, `AIRFLOW__WEBSERVER__DEFAULT_UI_TIMEZONE=Asia/Shanghai`, `TZ=Asia/Shanghai`, and frontend build arg `VITE_DISPLAY_TIME_ZONE=Asia/Shanghai`; frontend Docker test target passed 15 tests; backend/frontend/Airflow containers report `date` as `+0800 CST`; Airflow logs show `+0800` and `Configured default timezone Asia/Shanghai`; frontend bundle contains `Asia/Shanghai`
last_sample_status_sync: passed on fengxian at commit 065907c; red backend tests first showed submit/sync left samples `pending`, then implementation passed targeted 3 tests and full backend pytest 48 passed; backend redeployed healthy; explicit sync refreshed visible runs, e.g. `PGTA_20260706_141915_5BE5E2` samples `E2/E3=success`, `PGTA_20260706_140854_8F2CA4` sample `E2=success`, and `WES_20260705_164813_C5561C` samples `S001/S002=success`
last_pgta_64core_autosync: passed on fengxian at commit fb107a4; compose renders `PGTA_SNAKEMAKE_CORES=64`; Airflow image unit tests for `bio_pgta`/`bio_pgta_airflow` command construction passed 4 tests; frontend Docker test target passed 16 Vitest tests including active-run auto sync and terminal stop; Airflow import errors returned `No data found`; frontend image rebuilt/redeployed at 12959 and returned HTTP 200; current baseline_qc run `PGTA_20260706_162150_00C4FD` remained `running` and was not interrupted
last_pgta_baseline_t092_monitor: 2026-07-07 14:11 CST read-only check on fengxian found compose config ok and services running; Airflow `bio_pgta` run `manual__PGTA_20260706_162150_00C4FD` still `running`; task states show `validate_request=success`, `prepare_pgta_config=success`, `run_pgta_target=running`, `collect_pgta_artifact=None`; backend run status and samples G10/G11 are `running`; `logs/snakemake.command.txt` contains `--cores 1` because the run started before T091; G10 mapping is complete with BWA real time 33885.400 sec, G11 BWA log is still updating; no `qc/baseline` files, no `/qc` metrics, and artifacts currently only include command/config; no `sync-airflow`, restart, retry, or new run was executed
last_pgta_t093_resume: 2026-07-07 18:09 CST on fengxian at commit 2821a5e; backend pytest 50 passed, Airflow DAG unittest 43 OK/5 skipped logger-interface-in-this-Python-env, frontend Docker test 17 passed, Airflow import errors `No data found`; old run `manual__PGTA_20260706_162150_00C4FD` was controlled-interrupted from exact matching Snakemake/BWA/Samtools processes and synced to backend `failed` with non-null `error_summary`; new resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z` is running, command contains `--cores 64 --rerun-incomplete`, unlock command contains `--unlock`, no `--forceall`, and active G11 processes show `bwa mem -t 16` plus `samtools sort -@ 16`; no `qc/baseline` terminal files yet
last_pgta_t094_resume_cleanup: 2026-07-07 20:13 CST on fengxian at commit 0a8e756; red tests first failed on missing tmp cleanup and missing cleanup artifact; after fix, compose config passed, backend image rebuilt and full pytest passed 51 tests, Airflow DAG unittest discover passed 44 tests with 5 logger-interface skips, Airflow import errors returned `No data found`; backend and Airflow scheduler/worker were recreated without touching Postgres/Redis/frontend or volumes; pre-resume check found 16 stale `mapping/G11.sorted.bam.tmp.*.bam` files and no matching running processes; resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` started, `logs/pgta.resume.cleanup.tsv` recorded deletion of all 16 tmp BAMs, remaining tmp count is 0, command contains `--cores 64 --rerun-incomplete` and no `--forceall`, artifacts API exposes `pgta_resume_cleanup`, backend sync shows status `running`, and active process currently shows G11 `fastp -w 16`; terminal baseline QC artifacts still pending
last_pgta_t095_python_preflight: 2026-07-07 22:53 CST on fengxian at commit 3bd1270; initial read-only failure check found T094 resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` failed in `baseline_bam_uniformity_qc` with `ImportError: /usr/lib/x86_64-linux-gnu/libstdc++.so.6: version CXXABI_1.3.15 not found`; first T095 commit `966e0d8` added conda `LD_LIBRARY_PATH`, run-local `MPLCONFIGDIR`, and preflight, but Airflow task resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T143132Z` still failed preflight; final fix `3bd1270` adds `LD_PRELOAD=/biosoftware/miniconda/envs/snakemake_env/lib/libstdc++.so.6`, remote DAG unittest passed 47 tests with 5 expected logger-interface skips, `docker compose config --quiet` passed, Airflow import errors returned `No data found`, direct worker preflight logged `matplotlib/numpy/pandas/pysam/scipy` versions, final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` reached Airflow/backend `success`; artifacts include `pgta_python_preflight`, `pgta_baseline_qc_summary`, `pgta_baseline_qc_pass_samples`, `pgta_baseline_qc_report`; `/api/runs/PGTA_20260706_162150_00C4FD/qc` returns `pass=0,warn=0,fail=14,unknown=0`, and samples G10/G11 are workflow `success` with QC status `fail`
last_pgta_frontend_airflow_reconcile: 2026-07-08 on fengxian at commit f64e0d2; T098 deployed backend/frontend only, no new analysis submitted; `/api/health` ok and `/api/health/airflow` healthy; `/api/runs?pipeline=pgta&limit=50&offset=0` returned 17 PGT-A analysis runs and `PGTA_20260706_162150_00C4FD` list item now shows `status=success,qc_status=fail`; detail shows latest `dag_run_id=manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z`; `/qc` returns `pass=0,warn=0,fail=14,unknown=0`; Airflow `bio_pgta` lists 20 DAG runs total, with 5 matching that analysis because of resume history, and the latest matching DAG run is `success`
last_pgta_t099_run_tracker: 2026-07-08 on fengxian; T099 deployed frontend only, no new analysis submitted; frontend bundle contains `PGT-A Run Tracker`; `/api/health` ok and `/api/health/airflow` healthy; `/api/runs?pipeline=pgta&limit=20&offset=0` returned 19 PGT-A analysis runs and includes `PGTA_20260707_182024_8CA2A0` plus `PGTA_20260707_182056_39A374`; both run details return non-null `dag_run_id` (`manual__PGTA_20260707_182024_8CA2A0`, `manual__PGTA_20260707_182056_39A374`) and `status=success`; `PGTA_20260706_162150_00C4FD/qc` remains `pass=0,warn=0,fail=14,unknown=0`
last_pgta_t100_submit_autosync: 2026-07-08 on fengxian; user-reported stuck run `PGTA_20260708_012630_352915` had backend `status=submitted` and `dag_run_id=manual__PGTA_20260708_012630_352915`, while Airflow CLI showed that DAG run had already reached `success` at `2026-07-08T01:26:43.802222+00:00`; a safe manual `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow` reconciled backend status to `success` without rerunning workflow; T100 frontend fix now calls `sync-airflow` after Submit handoff and auto-syncs active Dashboard tracker runs; frontend Docker test target passed 7 tests, compose config/build/recreate passed, frontend 12959 returned HTTP 200, `/api/health` ok, `/api/health/airflow` healthy, and `/api/runs?pipeline=pgta&status=submitted&limit=20&offset=0` returned no stuck submitted PGT-A runs
last_image_check: passed on fengxian; compose external images pulled and backend built with explicit tag
last_image_cleanup: removed 37 dangling <none> images; no docker system prune, no volume prune
last_pgta_failure_smoke: passed on fengxian; `invalid_target` run `PGTA_20260703_170957_3DDEC3` ended Airflow/backend `failed` as expected, stderr log size 1322 bytes, `sync-airflow` wrote non-null `error_summary` containing `stderr_path` and last error lines
last_wes_mock_dryrun: passed on fengxian official mirror at `/home/jiucheng/project/airflow-demo`; Snakemake 8.5.4 dry-run for `pipelines/wes/workflow/Snakefile` showed 8 jobs across all/fastp/bwa_mem/markdup/final_summary
last_mock_qsub_wrapper: passed on fengxian official mirror with backend POST; analysis `WES_20260704_180650_MOCK` generated `MOCK-WES_20260704_180650_MOCK-12-bwa_mem-S001`, qsub stdout/stderr files, submitted/success JSONL events, and `/api/runs/WES_20260704_180650_MOCK/rules` returned `bwa_mem/S001=success`
last_qsub_profile_runtime: passed on fengxian official mirror with `airflow-demo/snakemake-runner:0.1.0`; `WES_PROFILE_20260704_230713` ran `snakemake --profile profiles/qsub`, Snakemake 9.23.1 saw `cluster-generic`, executed 8 WES mock jobs, wrote `reports/final_summary.tsv`, qsub stdout/stderr files, and 14 JSONL events containing `qsub_submitted`/`qsub_success`
last_wes_airflow_qsub_smoke: passed on fengxian official mirror with `airflow-demo/airflow:0.1.0`; `WES_AIRFLOW_20260705_004506` / `manual__WES_AIRFLOW_20260705_004506` ended Airflow `success`, wrote `reports/final_summary.tsv` with `S001/S002 mock_success`, qsub stdout/stderr files, and 14 JSONL events; `collect_wes_artifacts` XCom returned `event_count=14` and `qsub_log_count=14`
last_wes_reanalysis_smoke: passed on fengxian official mirror; API/frontend-created `WES_20260705_162041_2507AF` initial submit, `resume`, and `rerun_rule fastp/S001` all reached Airflow/backend `success`; `/rules` returned 7 rows; `logs/events/snakemake_events.jsonl` has 28 lines; `logs/snakemake.command.txt` contains `--forcerun fastp` and no `--forceall`
last_wes_qc_smoke: passed on fengxian official mirror; API/frontend-created `WES_20260705_164813_C5561C` submitted to `bio_wes_qsub`, sync reached `success`, `/qc` returned `pass=6,warn=0,fail=0,unknown=0` with 6 items, artifacts included `wes_qc_summary`, and `reports/qc_summary.tsv` exists
last_e2e_smoke: T080/T081 read-only demo smoke on fengxian at mirror head 3310134 confirmed frontend HTTP 200, backend health ok, Airflow metadatabase/scheduler healthy; PGT-A `PGTA_20260706_162150_00C4FD` workflow status success with G10/G11 QC status fail and `/qc` summary `pass=0,warn=0,fail=14,unknown=0`; WES QC run `WES_20260705_164813_C5561C` success with `/qc` summary `pass=6,warn=0,fail=0,unknown=0`; WES rerun_rule run `WES_20260705_162041_2507AF` success with command containing `--forcerun fastp` and no `--forceall`; full email/NIPT E2E not run
```

## 8. 已知问题

| ID | Issue | Severity | Owner | Next step |
|---|---|---|---|---|
| K003 | BS10610 与 fengxian 用户和路径不同，不能复用 fengxian 硬编码路径 | medium | infra/coordinator | 迁移前把路径参数化到 `.env` 并重复 Level 0 preflight |
| K004 | 远端直接访问 GitHub release 不稳定 | low | infra | 优先本地 GitHub 下载后 scp 到 fengxian；国内 Docker CE 镜像作为 Compose fallback |
| K005 | fengxian 仍有非 airflow-demo 的 `latest` 镜像和未使用 volumes | low | infra | 未经确认不要删除；本轮只清理 dangling images，不碰非项目镜像和 volume |
| K006 | fengxian 宿主机 3000 已被非项目 `next-server` 占用 | low | infra | airflow-demo frontend 改用 12959；不要停止非项目进程 |

## 9. 当前阻塞

```text
真实部署/启动前阻塞:
- 真实 `qsub/qstat` 在 `fengxian` 仍不可用；当前 WES/NIPT qsub demo 只能使用 mock qsub wrapper，不提交真实集群任务
- PGT-A `baseline_qc` staged real run `PGTA_20260706_162150_00C4FD` 已通过 final resume 成功；当前不是 workflow blocker，但 G10/G11 的 baseline QC decision 均为 `FAIL`，后续若要作为演示成功样本需要评估数据或阈值
```

## 10. 下一步建议

```text
1. 若要正式启用自动扫描，先规划 T107：只在用户明确批准后修改 `config/intake.yaml` gates 并 unpause `bio_intake_scan`，用 before/after run-count 检查收口。
2. 执行 T082：整理回滚/清理 runbook，重点是不删除 volumes、不碰生产 PGT-A/NIPT 源目录、不盲目重跑 baseline_qc 或 NIPT full_run。
3. 执行 T034/T063：补 MailHog success/failure 邮件通知，邮件包含 run detail、QC/report、错误摘要链接。
4. 若演示需要 PGT-A QC pass 样本，先做只读数据/阈值审计，不要盲目重跑 baseline_qc。
```

## 11. T106 Intake dry-run preview and auto-submit gate checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/intake/T106-intake-dry-run-gating` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T106 adds a safety layer before automatic intake is ever unpaused:

- New backend `POST /api/intake/scan-preview` scans configured PGT-A/NIPT roots
  and returns dry-run rows plus summary counts without writing DB state,
  creating runs, or triggering Airflow.
- `POST /api/intake/scan-and-submit` now obeys both
  `defaults.auto_submit` and `pipelines.<name>.auto_submit.enabled` from
  `config/intake.yaml`.
- Default `config/intake.yaml` keeps PGT-A and NIPT Docker automatic
  create+submit disabled.
- Settings shows `Preview configured roots`, a read-only preview panel, and
  blocked-by-config reasons; it still has no unpause, scan-now submit, or
  full-run action.
- NIPT run creation now uses intake config roots with env fallback, so scanner
  and run creation validate against the same configured source roots.

Remote validation on `ssh fengxian`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- backend Docker targeted pytest passed: `8 passed`.
- frontend Docker test target passed: `11 passed`.
- backend/frontend build and recreate passed; frontend production build ran
  `tsc -b && vite build`.
- Frontend `http://127.0.0.1:12959/` returned HTTP 200.
- `/api/health` and `/api/health/airflow` returned healthy payloads.
- `/api/intake/config` showed global and pipeline auto-submit gates disabled.
- `/api/intake/scan-preview` returned `total_batches=21,would_submit=0`.
- Preview did not mutate state: intake discovery count stayed `21/21`, NIPT
  run count stayed `5/5`.
- `bio_intake_scan` remained paused (`airflow dags list` final column `True`).

Known caveat: a future auto-intake enablement task must be explicit and reviewed before changing gates
or unpausing `bio_intake_scan`.

## 12. T107 UI density and PGT-A staged DAG checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T107-ui-pgta-dag-stages` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T107 is implemented and remotely validated. Scope:

- Submit Task preview now uses a definition-style field layout so labels and
  values no longer collide; long scan root and workflow fields wrap on their
  own full-width rows.
- Samples views use `source files` instead of `fastq_path`, showing R1/R2
  basenames and a batch/folder secondary line when `metadata.source_dir` is
  available. Legacy rows show `Path not captured for this run`.
- Run Detail QC uses a compact sample-by-metric matrix with fail/warn-first
  sorting, sample search, status filter, and 20-row pagination.
- PGT-A `baseline_qc` now branches into an Airflow TaskGroup:
  `pgta_pipeline.run_pgta_mapping -> pgta_pipeline.run_pgta_metadata ->
  pgta_pipeline.run_pgta_baseline_qc`.
- PGT-A `metadata`, `dryrun_cnv`, and `invalid_target` continue to use the
  historical `run_pgta_target` task.
- Runner staging writes `logs/snakemake.<stage>.stdout.log`,
  `logs/snakemake.<stage>.stderr.log`, and
  `logs/snakemake.<stage>.command.txt`, plus stage events for Pipeline steps.
- `/api/runs/{analysis_id}/progress` keeps the same response shape but now
  knows T107 PGT-A stage task weights.

Remote validation on `ssh fengxian`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker build --no-cache --target test -f frontend/Dockerfile frontend`:
  passed, 13 Vitest tests.
- backend Docker targeted pytest passed: 19 tests.
- Airflow worker unittest passed: 27 tests for `bio_pgta` DAG and
  `pgta_metadata_runner`.
- Airflow import check returned `No data found`.
- backend, airflow-worker, airflow-scheduler, and frontend images rebuilt and
  recreated without deleting volumes.
- Frontend `http://127.0.0.1:12959/` returned HTTP 200; `/api/health` returned
  ok and `/api/health/airflow` returned healthy metadatabase/scheduler.
- `airflow tasks list bio_pgta --tree` shows the staged TaskGroup plus the
  historical `run_pgta_target` branch.
- Light PGT-A metadata smoke `PGTA_20260708_141653_B57AB6` reached backend and
  Airflow `success`.

Local limitations and deliberate exclusions:

- Local Windows `python` shim was unusable; `py` exists but local backend tests
  lack FastAPI and Airflow dependencies.
- Local runner unittest runs under Windows but existing POSIX path assertions
  fail on backslash paths; remote Linux/container validation was used.
- Local Node/NPM are unavailable, so frontend tests/build ran in the remote
  frontend Docker test target.
- No heavy PGT-A `baseline_qc` run has been started by T107.

## 12. T096 frontend platform redesign checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T096-platform-ui-redesign` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T096 upgrades the frontend from the prior single workspace into a routed bioinformatics operations platform while preserving the existing PGT-A and WES backend API behavior. New documentation is in `DESIGN.md`, `docs/frontend-design-review.md`, and `docs/frontend-spec.md`; `docs/06_FRONTEND_SPEC.md` now points to the v2 structure.

Implemented frontend routes:

```text
/dashboard
/submit
/runs
/runs/:analysisId
/samples
/workflows
/failures
/settings
```

Implemented shared components include `StatusBadge`, `MetricCard`, `PipelineCard`, `RunTable`, `WorkflowTimeline`, `LogViewer`, `SampleSheetUploader`, `PipelineSelector`, `ErrorPanel`, and `QcMetricCard`. Status semantics are centralized in `frontend/src/lib/status.ts`; mock/demo NIPT, WGS, workflow-template, and resource data are isolated in `frontend/src/mocks/platform.ts`.

Remote validation on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, 7 Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 after nginx readiness.
- `GET http://127.0.0.1:8000/api/health`, `/api/health/db`, and `/api/health/airflow`: all returned ok/healthy.
- Existing PGT-A run `PGTA_20260706_162150_00C4FD` detail, samples, and stderr log endpoints returned data.
- Existing WES run `WES_20260705_170904_5D1C74` detail, rules, and QC endpoints returned data.

Local notes: local Windows has no `node`, `npm`, or `docker`; local checks remain git/docs/manifest only. `frontend/package.json` has no `lint` script, so `npm run lint` was not run.

## 12. T097 PGT-A-only frontend deployment scope

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T097-pgta-only` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

The current frontend deployment target is PGT-A-only. This supersedes the T096 visible product surface for demo purposes:

- Sidebar shows Dashboard, Submit Task, Runs, Samples, Failures, and Settings. Workflows is not linked in the sidebar.
- Dashboard, Runs, Samples, and Failures filter to `pipeline=pgta` and do not surface WES/NIPT/WGS demo entries.
- Submit Task only exposes the PGT-A server-path scan/create/submit path.
- Run Detail keeps PGT-A tabs, logs, QC, files, config, sync, and baseline_qc `Resume with 64 cores`.
- Direct `/workflows` navigation remains development-accessible but displays only the PGT-A workflow template.
- Historical WES qsub backend/DAG/Snakemake code is intentionally left in place but is no longer a current deployable frontend entry.
- NIPT/WGS remain hidden from the current frontend demo.
- MailHog/SMTP notification work is not part of T097; `T034` and `T063` remain todo.

Remote validation and deployment on `ssh fengxian`:

- Remote mirror switched to `codex/frontend/T097-pgta-only` at frontend code commit `3119be5`.
- `docker build --no-cache --target test -f frontend/Dockerfile frontend`: passed, `1 test file`, `5 tests`.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only the frontend container.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: returned `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.
- `GET /api/runs/PGTA_20260706_162150_00C4FD`: returned PGT-A detail data.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/qc`: returned `pass=0,warn=0,fail=14,unknown=0`.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/logs?stream=stderr&tail=20`: returned stderr tail lines.

## 13. T099 PGT-A Dashboard run tracker and submit handoff

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T099-pgta-run-tracker` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

The current deployed frontend remains PGT-A-only. T099 changes the main operator experience:

- Dashboard no longer splits recent failed and completed runs into separate blocks. It shows one large `PGT-A Run Tracker` ordered by active, failed/QC failed, created-only, then recent success runs.
- Each tracker row shows project name from `params.project_name` when available, `analysis_id`, workflow status, QC status, current step, progress estimate, progress bar, samples, created/started/duration fields, and View/Submit/Sync actions.
- Tracker filters are All, Running, Submitted / queued, Created only, Failed, QC failed, and Success.
- Created-only runs show `Not in Airflow`; active runs can be synced and are eligible for 15-second Dashboard polling.
- Dashboard bottom panels are now Service health, PGT-A resource overview, and PGT-A workflow.
- Submit Task primary action is `Create and submit to Airflow`; it calls `POST /api/runs`, then `POST /api/runs/{analysis_id}/actions/submit`, then fetches detail and displays `dag_run_id`.
- `Create only` remains available as a secondary action and explicitly warns that the run is not visible in Airflow until submitted.
- Scan results are grouped by source folder, with FASTQ file names behind an expand control and absolute paths hidden by default behind `full path`.

Remote validation and deployment on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, `7` Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only frontend.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: returned `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.

## 14. T104 Dashboard aggregation and intake config checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/dashboard/T104-dashboard-intake-config` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T104 changes the Dashboard from frontend fan-out requests into backend
aggregation:

- New backend APIs: `/api/dashboard/overview`, `/api/dashboard/runs`,
  `/api/system/resources`, and `/api/intake/config`.
- New config file: `config/intake.yaml`; backend reads it through
  `INTAKE_CONFIG_PATH=/app/config/intake.yaml` and keeps env roots as fallback.
- Dashboard first screen uses overview, dashboard/runs, intake/status, and
  system/resources; it does not call run detail, `/progress`, or `/rules` for
  each visible run.
- Run Tracker defaults to 10 rows per page, supports pipeline selector,
  status filter, keyword search, previous/next pagination, progress bar,
  current Airflow task, and current pipeline rule.
- Intake scanner states distinguish `Observed`, `Stable ready`,
  `Auto-submitted`, `Bootstrap observed`, `Disabled`, and `Error`; observed
  bootstrap rows are not displayed as queued workflow execution.
- Bottom Dashboard panels are `Service & Node Health`, `Pipeline Resources`,
  and `Workflow Activity`.

Validation completed so far:

- Local Python syntax check passed for changed backend modules.
- Remote backend Docker targeted pytest passed: 7 tests
  (`test_dashboard_service.py`, `test_intake_config.py`,
  `test_system_resources.py`).
- Remote frontend Docker test target passed: 10 Vitest tests.
- Remote `docker compose -f docker-compose.yaml config --quiet` passed.
- Remote `airflow dags list-import-errors` returned `No data found`.
- Remote build/recreate passed for backend, airflow-worker, airflow-scheduler,
  and frontend; frontend production build ran `tsc -b && vite build`.
- Frontend `http://127.0.0.1:12959/` returned HTTP 200.
- Backend `/api/health` returned ok; `/api/health/airflow` returned healthy
  scheduler and metadatabase.
- Runtime `/api/dashboard/overview?pipeline=all` returned 26 visible PGT-A/NIPT
  runs, 0 running, 8 failed, and intake summary with 21 bootstrap rows.
- Runtime `/api/dashboard/runs?pipeline=all&limit=10&offset=0` returned
  `limit=10`, `items=10`, `total=26`.
- Runtime `/api/system/resources` returned `source=host_proc`, 128 CPU cores,
  and disks `/` plus `/data`.
- Runtime `/api/intake/config` returned `source=/app/config/intake.yaml` with
  pipelines `pgta` and `nipt_docker`.
- Endpoint timing on `fengxian`: dashboard overview about 0.019s; dashboard runs
  first page about 1.641s.
- `bio_intake_scan` remains paused (`airflow dags list` final column `True`).
- `GET /api/runs?pipeline=pgta&limit=20&offset=0`: returned 19 total PGT-A analysis runs, including `PGTA_20260707_182024_8CA2A0` and `PGTA_20260707_182056_39A374`.
- Both July 7 run details returned non-null `dag_run_id` and `status=success`.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/qc`: returned `pass=0,warn=0,fail=14,unknown=0`.

## 14. T100 PGT-A submit/Airflow status auto-sync

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T099-pgta-run-tracker` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T100 addresses the user-reported symptom: after creating and submitting a PGT-A project, the frontend stayed at `submitted` and the operator could not tell whether Airflow had entered the workflow.

Root cause found on `fengxian`:

- `PGTA_20260708_012630_352915` existed in biodemo with `status=submitted`, `dag_run_id=manual__PGTA_20260708_012630_352915`, `started_at=null`, `ended_at=null`, and no rule events.
- Airflow showed the same DAG run had already completed with `state=success`.
- The frontend Submit flow fetched run detail after `/actions/submit`, but did not call `/actions/sync-airflow`; Dashboard also waited for user/manual sync rather than reconciling active tracker rows immediately.
- A manual `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow` reconciled that run to backend `status=success` without creating or rerunning any workflow.

Implemented frontend behavior:

- Dashboard auto-syncs active/submitted PGT-A tracker runs immediately and every 15 seconds through backend `sync-airflow`, then reloads tracker data.
- Submit Task primary `Create and submit to Airflow` now calls `sync-airflow` after a successful Airflow handoff with `dag_run_id`, retrying briefly so fast metadata runs can move from `submitted` to `success` in the handoff summary.
- If Airflow is still running after the brief sync window, the Dashboard tracker continues polling and syncing until terminal state.

Remote validation and deployment on `ssh fengxian`:

- Red frontend test target first failed as expected because Dashboard and Submit did not call `sync-airflow`.
- `docker build --target test -f frontend/Dockerfile frontend`: passed after implementation, `7` Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only frontend.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: returned `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.
- `GET /api/runs/PGTA_20260708_012630_352915`: returned `status=success`, `dag_run_id=manual__PGTA_20260708_012630_352915`, and Airflow start/end timestamps.
- `GET /api/runs?pipeline=pgta&status=submitted&limit=20&offset=0`: returned no stuck submitted PGT-A runs.

Remaining limitation: progress is still a frontend estimate from backend run/rule data. A future backend Airflow task-instance endpoint is needed for authoritative per-task progress and Airflow attempt history.

## 15. T101 NIPT Docker template-run deployment

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/nipt/T101-nipt-docker-demo` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Current deployable frontend surface is now PGT-A + NIPT Docker. WES qsub, NIPT qsub, WGS, and mail notification remain hidden/deferred in the current demo.

Implemented:

- Backend `POST /api/runs` supports `pipeline=nipt_docker` with `template_id=run1|run2`, `run_mode=mount_smoke|full_run`, `cores`, `project_name`, and `note`.
- Backend submit supports `nipt_docker` and triggers Airflow DAG `bio_nipt_docker`.
- `full_run` remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`; default acceptance uses `mount_smoke`.
- Airflow DAG `bio_nipt_docker` has task graph `validate_request -> prepare_nipt_docker_run -> run_nipt_docker -> collect_nipt_artifacts`.
- Runner writes `nipt_run_config.yaml`, `nipt_docker_compose.yml`, `nipt_airflow_request.json`, `nipt_docker.command.txt`, stdout/stderr logs, and `reports/qc_summary.tsv`.
- Airflow worker mounts the NIPT bundle and Docker socket; `group_add=${DOCKER_SOCKET_GID:-114}` is required on `fengxian` for socket access. Scheduler/API server do not mount the Docker socket.
- QC import parses NIPT `reports/qc_summary.tsv`, updates `qc_metric`, and refreshes `sample.qc_status`.
- Artifact API filters pipeline-specific artifacts; NIPT runs expose NIPT artifacts and no longer expose WES `wes_qc_summary`.
- Frontend Dashboard/Submit/Runs/Samples/Workflows/Failures support PGT-A and NIPT Docker only.

Remote validation on `ssh fengxian`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `git diff --check`: passed.
- `docker build --target test -f frontend/Dockerfile frontend`: passed, 9 Vitest tests.
- `docker build -t airflow-demo/backend:t101-test -f backend/Dockerfile backend && docker run --rm airflow-demo/backend:t101-test pytest -q tests/test_nipt_docker_lifecycle.py tests/test_run_creation.py tests/test_run_submit.py tests/test_run_diagnostics.py`: passed, 31 tests.
- After artifact/QC refinement: `pytest -q tests/test_nipt_docker_lifecycle.py tests/test_run_diagnostics.py`: passed, 17 tests.
- `docker run --rm --entrypoint /usr/local/bin/python -v /home/jiucheng/project/airflow-demo/dags:/opt/airflow/dags:ro -w /opt/airflow airflow-demo/airflow:t101-test -m unittest /opt/airflow/dags/tests/test_bio_nipt_docker_dag.py /opt/airflow/dags/tests/test_nipt_docker_runner.py -v`: passed, 9 tests.
- `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend`: passed; frontend build ran `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-api-server airflow-scheduler airflow-worker frontend`: passed.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200.
- `/api/health` and `/api/health/airflow`: healthy after Airflow API server readiness.
- `airflow dags list-import-errors`: `No data found`.
- `airflow dags list` showed `bio_nipt_docker`.
- Initial smoke `NIPT_20260708_032949_C7F56B` failed because worker lacked Docker socket group permission; fixed by adding `DOCKER_SOCKET_GID=114` and worker `group_add`.
- Successful smoke `NIPT_20260708_033128_7B6386` proved Docker execution after socket group fix.
- Final smoke `NIPT_20260708_033450_8362A0` reached Airflow/backend `success`, QC `pass=96,warn=0,fail=0,unknown=0`, run list `qc_status=pass`, stdout `mount_smoke_ok NIPT_20260708_033450_8362A0 260414_TPNB500380AR_1065_AH32CCBGY2`, and artifacts `nipt_qc_summary`, `nipt_docker_compose`, `nipt_run_config`, `nipt_airflow_request`, `nipt_docker_command`.

Known caveats:

- `full_run` was not executed; this remains intentionally blocked unless the user explicitly approves a heavy NIPT batch.
- Historical failed smoke `NIPT_20260708_032949_C7F56B` remains in DB/Airflow history as evidence of the pre-fix Docker socket permission issue.
- T102 supersedes the T101 progress caveat: frontend progress now uses backend `/progress` with Airflow task instances plus runner rule events. Historical runs without captured rule events still show Airflow task progress.

## 16. T102 Airflow + Snakemake progress observability

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/progress/T102-airflow-snakemake-progress` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Implemented:

- Backend endpoint `GET /api/runs/{analysis_id}/progress` combines biodemo run state, Airflow REST task instances, and `snakemake_rule_event` rows.
- `AirflowClient.list_task_instances()` reads `/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances`; no direct Airflow DB reads.
- PGT-A and NIPT Docker submit conf includes `backend_event_url=http://backend:8000/api/events/snakemake`.
- `dags/common/progress_events.py` writes runner events to JSONL and optionally POSTs to backend; POST failure is non-fatal.
- PGT-A runner emits target-level progress events and parses Snakemake stdout/stderr for rule blocks.
- NIPT Docker runner emits `nipt_mount_smoke` events and parses full-run Docker stdout/stderr when heavy mode is enabled.
- `sync-airflow` imports JSONL fallback events on terminal runs.
- Dashboard and Run Detail use `/progress`; Run Detail Workflow tab shows `Airflow tasks` and `Pipeline steps`.

Remote validation on `ssh fengxian`:

- `git diff --check`: passed.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- Backend targeted Docker tests passed: `29 passed`.
- Airflow DAG/runner Docker unittest passed: `35 tests OK`.
- Frontend Docker test target passed: `10` Vitest tests.
- Production build passed for backend, Airflow worker/scheduler/API server, and frontend; frontend build ran `tsc -b && vite build`.
- Recreated backend, Airflow API/scheduler/worker, and frontend without deleting volumes.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200.
- `/api/health`: ok; `/api/health/airflow`: metadatabase and scheduler healthy.
- `airflow dags list-import-errors`: `No data found`.
- Historical `/api/runs/PGTA_20260706_162150_00C4FD/progress` returned Airflow task timeline with `percent=100`.
- Historical `/api/runs/NIPT_20260708_033450_8362A0/progress` returned Airflow task timeline with `percent=100`.
- New PGT-A metadata smoke `PGTA_20260708_050811_A24E36` reached success with Airflow tasks and `metadata=success` pipeline event.
- New NIPT Docker mount smoke `NIPT_20260708_050843_B3B05E` reached success with Airflow tasks and `nipt_mount_smoke=success` pipeline event.

Known caveats:

- Historical runs before T102 cannot reconstruct missing Snakemake/runner events; they still show Airflow task-instance progress.
- NIPT `full_run` was not executed; it remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- Mail notification, WES qsub frontend restore, NIPT qsub, and WGS remain out of current deployable scope.

## 17. T103 PGT-A/NIPT batch scan and auto intake

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/intake/T103-pgta-nipt-auto-scan` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Implemented:

- `POST /api/input/scan` supports `pipeline=pgta|nipt_docker`; `GET /api/input/roots` returns pipeline-specific scan roots.
- NIPT scan discovers chip folders with top-level `*.clean.fastq.gz` R1/R2 pairs and ignores nested adapter FASTQs in v1.
- New NIPT Docker create requests use `rawdata_root` and `selected_samples` from scan results; `template_id` is compatibility-only and no longer exposed in Submit Task.
- NIPT run params include `input_mode=nipt_docker_scan`, `source_batch_dir`, `source_batch_id`, `source_fingerprint`, `input_file_flavor=clean`, `chip_name`, and `selected_count`.
- `bio_nipt_docker` prepares a run-local chip CSV/config/compose and mounts the source batch read-only as `/input_batch`; no large FASTQ copy and no production bundle writes.
- Added `intake_discovery` table plus `/api/intake/status` and `/api/intake/scan-and-submit`.
- Added `bio_intake_scan`, paused on creation by default; bootstrap must record historical batches before unpausing automatic intake.
- Dashboard shows read-only Intake auto scanner status. Submit Task scans PGT-A/NIPT roots and creates one NIPT run per selected chip batch.

Remote validation on `ssh fengxian`:

- `git diff --check`: passed.
- Manifest check: `file_count=179`, listed files `179`, missing `0`.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker build --target test -f frontend/Dockerfile frontend`: passed, 10 Vitest tests.
- Backend Docker targeted pytest passed: 25 tests.
- Airflow DAG tests passed: 4 tests for `bio_intake_scan`/`bio_nipt_docker`; NIPT runner/progress tests passed: 12 tests.
- `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend`: passed; frontend build ran `tsc -b && vite build`.
- Recreated backend, airflow-scheduler, airflow-worker, and frontend without deleting volumes; `alembic upgrade head` applied `20260708_0002`.
- Frontend HTTP 200 on `http://127.0.0.1:12959/`; `/api/health` ok; `/api/health/airflow` scheduler/metadatabase healthy.
- `airflow dags list-import-errors`: `No data found`; `bio_intake_scan` listed paused, `bio_nipt_docker` and `bio_pgta` listed unpaused.
- `/api/input/roots?pipeline=nipt_docker` returned `/opt/pipelines/NIPT/fastq`.
- NIPT scan of `/opt/pipelines/NIPT/fastq` returned clean FASTQ candidates grouped under chip folder `FQ2025/250103_NDX550692_RUO_0044_AH3H37BGYW`.
- Scanned NIPT mount smoke `NIPT_20260708_072349_4F942A` submitted to `manual__NIPT_20260708_072349_4F942A` and reached Airflow/backend `success`.
- `/progress` for that run returned `percent=100`, Airflow task instances, and `nipt_mount_smoke=success` rule event.
- `/qc` returned `pass=1,warn=0,fail=0,unknown=0`; stdout contained `mount_smoke_ok NIPT_20260708_072349_4F942A 250103_NDX550692_RUO_0044_AH3H37BGYW`; artifacts included NIPT QC/config/compose/command entries.
- Intake bootstrap with `bootstrap=true,max_samples=20` recorded existing PGT-A/NIPT batches as `observed/bootstrap`; it did not auto-submit historical batches.

Known caveats:

- `bio_intake_scan` remains paused until explicitly unpaused after bootstrap review.
- NIPT `full_run` was not executed and remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- Auto-intake currently uses PGT-A `metadata` and NIPT `mount_smoke`; production full-run automation needs a separate explicit approval/config gate.
## 2026-07-08 T108 validated

Current branch/worktree:

- Branch: `codex/frontend/T108-dashboard-run-detail-usability`
- Worktree: `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Implemented and deployed:

- Dashboard Run Tracker is now an operator-readable table:
  Project/Run ID links, combined current stage, progress, runtime/ETA, and
  timezone-clean timestamps.
- Dashboard `QC / failure focus` was replaced by `Sample throughput` with
  `24h / 7d / 30d` period selector and sample-level counts.
- Intake scanner display was converted from card wall to compact table
  with discovery state semantics.
- Backend dashboard aggregation exposes sample throughput, sample trend,
  human-readable stage labels, elapsed runtime, and ETA estimate fields.
- Run Detail now renders selected samples as a manifest table, adds QC failure
  summary above the QC matrix, prioritizes Snakemake/NIPT config artifacts, and
  adds a controlled `Run action` modal.
- PGT-A reanalysis now has a controlled `rerun_stage` API path for
  `mapping`, `metadata`, and `baseline_qc`; arbitrary DAG/task trigger remains
  out of scope.

Remote validation:

- `docker compose -f docker-compose.yaml config --quiet` passed.
- Frontend Docker test target passed 14 Vitest tests.
- Backend targeted pytest passed 25 tests.
- Airflow DAG/runner unittest passed 28 tests in `airflow-demo/airflow:t108-test`.
- `docker compose build backend airflow-worker airflow-scheduler frontend` passed, including frontend `tsc -b && vite build`.
- `docker compose up -d --no-deps --force-recreate backend airflow-worker airflow-scheduler frontend` passed.
- Frontend `12959` returned HTTP 200 and backend `/api/health` returned ok.
- Dashboard overview/runs/resource/intake APIs returned T108 fields.
- Light PGT-A metadata smoke `PGTA_20260708_160227_EFAD64` reached backend/Airflow `success`.

Not changed:

- `bio_intake_scan` remains paused.
- Auto-submit remains disabled by default.
- NIPT Docker DAG is not split in this task.
- NIPT `full_run` and heavy PGT-A `baseline_qc` are not run without explicit
  approval.
