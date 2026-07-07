# CURRENT_STATE.md

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
当前阶段: P3/P4/P6 Airflow + Snakemake/qsub mock observability + PGT-A Level 4 staged integration
当前目标: T096 frontend platform redesign 已完成并远端验证；PGT-A `PGTA_20260706_162150_00C4FD` 可展示 workflow success + QC fail，WES mock 可展示 QC pass 和 rerun_rule without forceall，NIPT/WGS 仍是 demo/mock UI。
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
active_branch: codex/frontend/T096-platform-ui-redesign for frontend redesign worktree; previous PGT-A runtime baseline remains documented in T095/T080/T081
last_verified_code_commit: 3310134 for T095 runtime; T080/T081 is docs-only and used read-only runtime validation before the report update
worktree_strategy: single-worktree for now; fengxian is code mirror only
fengxian_mirror: /home/jiucheng/project/airflow-demo cloned from GitHub; T080/T081 used read-only runtime validation on mirror at 3310134 before docs update
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 12959 | running after T091 auto-sync redeploy | React/Vite PGT-A + WES mock workspace served by Docker nginx image `airflow-demo/frontend:0.1.0`; run timestamps render as `Asia/Shanghai`; active selected runs auto-sync Airflow every 15 seconds; `Submit new analysis` is in the main content area, target selector includes `baseline QC smoke`, and host 3000 is occupied by non-project next-server |
| backend | 8000 | running, healthy after T090 sample-status redeploy | `/api/health`, `/api/health/db`, `/api/input/scan`, `/api/runs`, run detail/samples, submit, sync-airflow, logs, artifacts, `/api/events/snakemake`, `/api/runs/{analysis_id}/rules`, `/api/runs/{analysis_id}/qc`, and PGT-A baseline_qc parser/artifacts are available; submit/reanalyze now sets sample.status to `running`, and sync-airflow maps samples to `success/failed`; image `airflow-demo/backend:0.1.0`; container `TZ=Asia/Shanghai` |
| airflow web/api | 12958 | running; `PGTA_20260706_162150_00C4FD` final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` ended `success` after T095 `LD_PRELOAD` fix; previous T095-only-`LD_LIBRARY_PATH` attempt `manual__PGTA_20260706_162150_00C4FD__resume__20260707T143132Z` failed preflight | project image `airflow-demo/airflow:0.1.0`; Airflow core/UI timezone is `Asia/Shanghai`; T095 sets run-local `XDG_CACHE_HOME`, `MPLCONFIGDIR`, `LD_LIBRARY_PATH=PGTA_CONDA_LIB`, and `LD_PRELOAD=PGTA_LIBSTDCXX`; `logs/pgta.python_preflight.log` records env header and import versions |
| postgres | internal 5432 | running, healthy | image `postgres:15-alpine`; Airflow metadata initialized; no host port published |
| redis | internal 6379 | running, healthy | image `redis:7-alpine`; no host port published |
| mailhog | 8025 | stopped in T051 smoke | HTTP GET probe passed in earlier smoke; not started for T051 |

## 5. 数据库状态

```text
airflow_metadata_db: initialized by `docker compose -f docker-compose.yaml up airflow-init`; admin user exists, password only in remote .env
biodemo_db: initialized on fengxian by `docker compose -f docker-compose.yaml run --rm biodemo-db-init`
migrations_tool: Alembic
last_migration: 20260702_0001 initial biodemo schema
core_tables: pipeline, analysis_run, sample, snakemake_rule_event, qc_metric, artifact, run_action
```

## 6. Pipeline 接入状态

| Pipeline | DAG | Snakemake | qsub | Docker | QC | Status |
|---|---|---|---|---|---|---|
| PGT-A demo | `bio_pgta` metadata/dryrun/failure smoke passed; `bio_pgta_airflow` Airflow-only logger/event POST passed; `baseline_qc` staged real run `PGTA_20260706_162150_00C4FD` completed after controlled interrupt/resume sequence; final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` ended Airflow/backend `success` | direct Snakemake metadata target, `dryrun_cnv`, controlled `invalid_target`, and Level 4 `baseline_qc` smoke in Airflow worker passed; T088 sets `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`; T093 resume runs `--unlock` then `--cores 64 --rerun-incomplete`, no `--forceall`; T094 adds run-local cleanup of `mapping/*.sorted.bam.tmp.*.bam`; T095 sets conda `LD_LIBRARY_PATH`, `LD_PRELOAD=PGTA_LIBSTDCXX`, run-local `MPLCONFIGDIR`, and baseline QC Python preflight; Snakemake 9.23.1 logger plugin writes JSONL, Airflow log/XCom summary, and optional backend rule/job events | not used | server-path project creation, submit, status sync, logs, artifacts, rule event API, PGT-A run detail frontend v1, New PGT-A Run frontend scan/create/submit, active-run auto-sync, failed baseline_qc `Resume with 64 cores`, and QC/artifact panel API are available | baseline_qc parser/artifacts added; `/qc` imports 14 metrics for G10/G11 and both samples have QC decision `FAIL` | `/api/input/scan` and `/api/runs` create `created` run; submit triggers `bio_pgta`; Airflow-only manifest run can POST rule events to biodemo; frontend can create pgta runs for metadata/dryrun/failure/baseline_qc smoke, submit created runs, view run list/detail, samples, rules, logs, artifacts, QC, sync Airflow, and resume failed baseline_qc |
| WES qsub | `bio_wes_qsub` Airflow mock DAG passed with `new/resume/rerun_rule` and QC smoke | WES mock Snakefile dry-run passed; WES mock profile runtime passed in `snakemake-runner`; `bio_wes_qsub` runs Snakemake 9.23.1 inside Airflow worker with `profiles/qsub`, writes command/stdout/stderr/events and `reports/qc_summary.tsv` | mock qsub wrapper direct smoke passed with backend POST; Airflow/API/frontend smoke generated mock qsub job ids, stdout/stderr files, JSONL events, and command log proving `--forcerun fastp` without `--forceall` | `airflow-demo/snakemake-runner:0.1.0` and `airflow-demo/airflow:0.1.0` builds passed | WES mock QC parser and frontend QC panel done; real WES QC and MultiQC not started | T040/T041/T042/T030/T031/T044/T056/T060/T054 done; next step is T034/T063 MailHog notification or T080 smoke report/demo script |
| NIPT qsub | not started | not started | not started | n/a | not started | pending |
| NIPT docker | not started | optional | n/a | not started | not started | pending |

## 7. 最近测试结果

```text
last_backend_tests: remote Dockerized pytest on fengxian at commit 065907c passed, 48 tests; includes PGT-A baseline_qc target validation, submit two-sample guard, sample lifecycle status sync, artifact discovery, baseline QC parser/import, diagnostics/event tests, and WES lifecycle/QC tests
last_frontend_tests: remote Dockerized frontend test target on fengxian at commit 3b230cd passed, 7 Vitest tests; T096 covers routed shell, Dashboard, Runs, Run Detail, Submit validation, PGT-A create/submit compatibility, WES create/submit/rerun compatibility, mock NIPT/WGS labels, LogViewer, QC and failure displays
last_dag_import_tests: passed on fengxian at commit dd5c6e7; Airflow image unittest for `test_bio_pgta_dag.py`, `test_pgta_metadata_runner.py`, and `test_pgta_airflow_runner.py` returned 20 tests OK; Airflow scheduler `dags list-import-errors` returned `No data found`
last_snakemake_dryrun: passed on fengxian; `dryrun_cnv` run `PGTA_20260703_170917_20E8F2` ended Airflow/backend `success`, stdout log size 12677 bytes and recorded 7 dry-run jobs, stderr only had config-extension notice, artifacts returned stdout/stderr/config files
last_compose_config: passed on fengxian for T096 branch with `docker compose -f docker-compose.yaml config --quiet`; frontend production build passed `tsc -b && vite build`; frontend container recreated and `http://127.0.0.1:12959/` returned HTTP 200 after nginx readiness
last_minimal_smoke: passed on fengxian for postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker, then docker compose down
last_airflow_health: passed on fengxian at http://127.0.0.1:12958/health with healthy metadatabase and scheduler
last_biodemo_migration: `biodemo-db-init` first run created role/database, repeat run succeeded; `alembic upgrade head` applied 20260702_0001 and repeat run succeeded
last_backend_airflow_client: mock tests covered health/list/get/trigger; real smoke verified backend `/api/health/airflow` against Airflow `/health`
last_backend_build: backend image built on fengxian using `backend/pip.conf` TUNA PyPI mirror and `/opt/venv`; dependency install step dropped from about 9 minutes to about 11 seconds after mirror config
last_pgta_project_create_smoke: passed on fengxian; scan root `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` returned 5 candidates with `truncated=true`, created `PGTA_20260702_162531_74CE91` with 2 samples, status `created`, `dag_run_id=null`, and generated `samples.selected.tsv` plus `request.json`
last_pgta_submit_metadata_smoke: passed on fengxian; created/submitted `PGTA_20260702_171533_9A85B1`, backend status `submitted`, `dag_run_id=manual__PGTA_20260702_171533_9A85B1`, Airflow state `success`, and artifact `shared/runs/PGTA_20260702_171533_9A85B1/logs/run_metadata.tsv` exists
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
1. 执行 T082：整理回滚/清理 runbook，重点是不删除 volumes、不碰生产 PGT-A 目录、不盲目重跑 baseline_qc。
2. 执行 T034/T063：补 MailHog success/failure 邮件通知，邮件包含 run detail、QC/report、错误摘要链接。
3. 若演示需要 PGT-A QC pass 样本，先做只读数据/阈值审计，不要盲目重跑 baseline_qc。
4. 迁移 BS10610 前继续把 PGT-A 路径、数据根目录、`/biosoftware`、shared root 全部参数化到 `.env`。
```

## 11. T096 frontend platform redesign checkpoint

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
