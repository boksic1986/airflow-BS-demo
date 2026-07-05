# CURRENT_STATE.md

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
当前阶段: P3/P4/P6 Airflow + Snakemake/qsub mock observability + WES mock QC
当前目标: T060/T054 已完成；WES mock success run 可通过显式 `sync-airflow` 导入 `qc_summary.tsv` 到 `qc_metric`，并在 React run detail 显示 QC panel
最近更新时间: 2026-07-06
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
active_branch: codex/fullstack/T060-T054-wes-qc-panel
last_verified_code_commit: e22ea41 for T060/T054 WES mock QC parser/panel smoke before docs/status update
worktree_strategy: single-worktree for now; fengxian is code mirror only
fengxian_mirror: /home/jiucheng/project/airflow-demo cloned from GitHub; runtime validation for T060/T054 ran on origin/codex/fullstack/T060-T054-wes-qc-panel at e22ea41, followed by docs/status evidence update
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 12959 | running after T060/T054 smoke | React/Vite PGT-A + WES mock workspace served by Docker nginx image `airflow-demo/frontend:0.1.0`; WES run detail QC panel smoke passed; host 3000 is occupied by non-project next-server |
| backend | 8000 | running, healthy | `/api/health`, `/api/health/db`, `/api/input/scan`, `/api/runs`, run detail/samples, submit, sync-airflow, logs, artifacts, `/api/events/snakemake`, `/api/runs/{analysis_id}/rules`, `/api/runs/{analysis_id}/qc`, and frontend CORS preflight passed on fengxian; image `airflow-demo/backend:0.1.0` |
| airflow web/api | 12958 | running after T060/T054 smoke | project image `airflow-demo/airflow:0.1.0`; `/health` returned healthy earlier; `bio_pgta` dryrun/failure smoke passed; `bio_pgta_airflow` event POST smoke passed; `bio_wes_qsub` WES QC smoke run `manual__WES_20260705_164813_C5561C` succeeded |
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
| PGT-A demo | `bio_pgta` metadata/dryrun/failure smoke passed; `bio_pgta_airflow` Airflow-only logger/event POST passed | direct Snakemake metadata target, `dryrun_cnv`, and controlled `invalid_target` smoke in Airflow worker passed; Snakemake 9.23.1 logger plugin writes JSONL, Airflow log/XCom summary, and optional backend rule/job events | not used | server-path project creation, submit, status sync, logs, artifacts, rule event API, PGT-A run detail frontend v1, and New PGT-A Run frontend scan/create/submit passed | not started | `/api/input/scan` and `/api/runs` create `created` run; submit triggers `bio_pgta`; Airflow-only manifest run can POST rule events to biodemo; frontend can create pgta runs for metadata/dryrun/failure smoke, submit created runs, view run list/detail, samples, rules, logs, artifacts, and sync Airflow |
| WES qsub | `bio_wes_qsub` Airflow mock DAG passed with `new/resume/rerun_rule` and QC smoke | WES mock Snakefile dry-run passed; WES mock profile runtime passed in `snakemake-runner`; `bio_wes_qsub` runs Snakemake 9.23.1 inside Airflow worker with `profiles/qsub`, writes command/stdout/stderr/events and `reports/qc_summary.tsv` | mock qsub wrapper direct smoke passed with backend POST; Airflow/API/frontend smoke generated mock qsub job ids, stdout/stderr files, JSONL events, and command log proving `--forcerun fastp` without `--forceall` | `airflow-demo/snakemake-runner:0.1.0` and `airflow-demo/airflow:0.1.0` builds passed | WES mock QC parser and frontend QC panel done; real WES QC and MultiQC not started | T040/T041/T042/T030/T031/T044/T056/T060/T054 done; next step is T034/T063 MailHog notification or T080 smoke report/demo script |
| NIPT qsub | not started | not started | not started | n/a | not started | pending |
| NIPT docker | not started | optional | n/a | not started | not started | pending |

## 7. 最近测试结果

```text
last_backend_tests: remote Dockerized pytest on fengxian passed, 43 tests; includes QC TSV parser, `/api/runs/{analysis_id}/qc`, sync-airflow QC import idempotency, sample qc_status update, diagnostics/event tests, and WES create/submit/reanalyze tests
last_frontend_tests: remote Dockerized frontend test target passed on fengxian, 11 Vitest tests; production frontend image `airflow-demo/frontend:0.1.0` built after WES mock QC panel changes
last_dag_import_tests: passed on fengxian; Airflow DAG/runner unittest for `test_bio_wes_qsub_dag.py` and `test_wes_qsub_runner.py` returned 11 tests OK; Airflow import errors returned `No data found`; `bio_wes_qsub` listed
last_snakemake_dryrun: passed on fengxian; `dryrun_cnv` run `PGTA_20260703_170917_20E8F2` ended Airflow/backend `success`, stdout log size 12677 bytes and recorded 7 dry-run jobs, stderr only had config-extension notice, artifacts returned stdout/stderr/config files
last_compose_config: passed on fengxian with Docker Compose v2.24.7 for commit 403fa68; compose now renders backend image `airflow-demo/backend:0.1.0`, frontend image `airflow-demo/frontend:0.1.0`, CORS env, read-only PGT-A mounts, DAG files, and frontend build service
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
last_image_check: passed on fengxian; compose external images pulled and backend built with explicit tag
last_image_cleanup: removed 37 dangling <none> images; no docker system prune, no volume prune
last_pgta_failure_smoke: passed on fengxian; `invalid_target` run `PGTA_20260703_170957_3DDEC3` ended Airflow/backend `failed` as expected, stderr log size 1322 bytes, `sync-airflow` wrote non-null `error_summary` containing `stderr_path` and last error lines
last_wes_mock_dryrun: passed on fengxian official mirror at `/home/jiucheng/project/airflow-demo`; Snakemake 8.5.4 dry-run for `pipelines/wes/workflow/Snakefile` showed 8 jobs across all/fastp/bwa_mem/markdup/final_summary
last_mock_qsub_wrapper: passed on fengxian official mirror with backend POST; analysis `WES_20260704_180650_MOCK` generated `MOCK-WES_20260704_180650_MOCK-12-bwa_mem-S001`, qsub stdout/stderr files, submitted/success JSONL events, and `/api/runs/WES_20260704_180650_MOCK/rules` returned `bwa_mem/S001=success`
last_qsub_profile_runtime: passed on fengxian official mirror with `airflow-demo/snakemake-runner:0.1.0`; `WES_PROFILE_20260704_230713` ran `snakemake --profile profiles/qsub`, Snakemake 9.23.1 saw `cluster-generic`, executed 8 WES mock jobs, wrote `reports/final_summary.tsv`, qsub stdout/stderr files, and 14 JSONL events containing `qsub_submitted`/`qsub_success`
last_wes_airflow_qsub_smoke: passed on fengxian official mirror with `airflow-demo/airflow:0.1.0`; `WES_AIRFLOW_20260705_004506` / `manual__WES_AIRFLOW_20260705_004506` ended Airflow `success`, wrote `reports/final_summary.tsv` with `S001/S002 mock_success`, qsub stdout/stderr files, and 14 JSONL events; `collect_wes_artifacts` XCom returned `event_count=14` and `qsub_log_count=14`
last_wes_reanalysis_smoke: passed on fengxian official mirror; API/frontend-created `WES_20260705_162041_2507AF` initial submit, `resume`, and `rerun_rule fastp/S001` all reached Airflow/backend `success`; `/rules` returned 7 rows; `logs/events/snakemake_events.jsonl` has 28 lines; `logs/snakemake.command.txt` contains `--forcerun fastp` and no `--forceall`
last_wes_qc_smoke: passed on fengxian official mirror; API/frontend-created `WES_20260705_164813_C5561C` submitted to `bio_wes_qsub`, sync reached `success`, `/qc` returned `pass=6,warn=0,fail=0,unknown=0` with 6 items, artifacts included `wes_qc_summary`, and `reports/qc_summary.tsv` exists
last_e2e_smoke: PGT-A Level 0-3 demo smoke passed for preflight/config, metadata create-submit-success, dryrun_cnv success, and invalid_target failure/error_summary; WES mock create-submit-sync-QC passed; full email/NIPT E2E not run
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
```

## 10. 下一步建议

```text
1. 执行 T034/T063：补 MailHog success/failure 邮件通知，邮件包含 QC 链接和错误摘要链接。
2. 执行 T080：整理 WES/PGT-A 端到端 smoke 脚本和 demo 验收报告。
3. 执行 T061：补 MultiQC/Snakemake report artifact 登记和前端链接。
```
