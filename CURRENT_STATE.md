# CURRENT_STATE.md

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
当前阶段: P6 日志和错误诊断基础
当前目标: T025/T062 已为 PGT-A metadata run 增加 Airflow 状态同步、日志读取、动态 artifact 列表和 run-level error_summary；后续补前端、dry-run/failure smoke、rule/qsub 级事件
最近更新时间: 2026-07-03
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
qsub_available: <unknown>
snakemake_available: true for PGT-A at /biosoftware/miniconda/envs/snakemake_env/bin/snakemake
python_version: PGT-A locked python 3.12.2
node_version: <unknown>
```

## 3. 仓库状态

```text
repo_url: git@github.com:boksic1986/airflow-BS-demo.git
main_branch: main
active_branch: main
last_verified_code_commit: 25380e3
worktree_strategy: single-worktree for now; fengxian is code mirror only
fengxian_mirror: /home/jiucheng/project/airflow-demo cloned from GitHub; T025/T062 verified on origin/codex/backend/T025-T062-logs-artifacts-sync and ready to sync from origin/main after merge
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 12959 | stopped after successful smoke | Docker nginx placeholder returned `airflow-demo frontend placeholder`; host 3000 is occupied by non-project next-server |
| backend | 8000 | stopped after successful smoke | `/api/health`, `/api/health/db`, `/api/input/scan`, `/api/runs`, run detail/samples, submit, sync-airflow, logs, and artifacts passed on fengxian; image `airflow-demo/backend:0.1.0` |
| airflow web/api | 12958 | stopped after successful smoke | `/health` returned healthy metadatabase and scheduler; `bio_pgta` DAG run `manual__PGTA_20260702_171533_9A85B1` succeeded |
| postgres | internal 5432 | stopped after successful smoke | image `postgres:15-alpine`; Airflow metadata initialized; no host port published |
| redis | internal 6379 | stopped after successful smoke | image `redis:7-alpine`; no host port published |
| mailhog | 8025 | stopped after successful smoke | HTTP GET probe passed |

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
| PGT-A demo | `bio_pgta` metadata v1 passed | direct Snakemake metadata target in Airflow worker passed; dry-run not implemented | not used | server-path project creation, submit, status sync, logs and artifacts passed | not started | `/api/input/scan` and `/api/runs` create `created` run; submit triggers Airflow; sync/log/artifact APIs expose metadata run diagnostics; frontend not yet implemented |
| WES qsub | not started | not started | not started | n/a | not started | pending |
| NIPT qsub | not started | not started | not started | n/a | not started | pending |
| NIPT docker | not started | optional | n/a | not started | not started | pending |

## 7. 最近测试结果

```text
last_backend_tests: remote Dockerized pytest on fengxian passed, 26 tests; `GET /api/health`, `/api/health/db`, `/api/input/scan`, JSON `POST /api/runs`, run detail/samples, submit, sync-airflow, logs, artifacts, missing-log, and path safety tests passed
last_frontend_tests: not run - no frontend implementation yet
last_dag_import_tests: passed on fengxian; `py_compile` with `PYTHONPYCACHEPREFIX=/tmp/pycache`, Airflow unittest discover returned 6 tests OK, and `airflow dags list` showed `bio_pgta` unpaused
last_snakemake_dryrun: not run - only PGT-A metadata target was executed; dry-run remains a later task
last_compose_config: passed on fengxian with Docker Compose v2.24.7 for commit 25380e3; backend now renders `INPUT_SCAN_ROOTS`, read-only PGT-A mounts, DAG files, and diagnostics endpoints
last_minimal_smoke: passed on fengxian for postgres redis mailhog backend frontend airflow-api-server airflow-scheduler airflow-worker, then docker compose down
last_airflow_health: passed on fengxian at http://127.0.0.1:12958/health with healthy metadatabase and scheduler
last_biodemo_migration: `biodemo-db-init` first run created role/database, repeat run succeeded; `alembic upgrade head` applied 20260702_0001 and repeat run succeeded
last_backend_airflow_client: mock tests covered health/list/get/trigger; real smoke verified backend `/api/health/airflow` against Airflow `/health`
last_backend_build: backend image built on fengxian using `backend/pip.conf` TUNA PyPI mirror and `/opt/venv`; dependency install step dropped from about 9 minutes to about 11 seconds after mirror config
last_pgta_project_create_smoke: passed on fengxian; scan root `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` returned 5 candidates with `truncated=true`, created `PGTA_20260702_162531_74CE91` with 2 samples, status `created`, `dag_run_id=null`, and generated `samples.selected.tsv` plus `request.json`
last_pgta_submit_metadata_smoke: passed on fengxian; created/submitted `PGTA_20260702_171533_9A85B1`, backend status `submitted`, `dag_run_id=manual__PGTA_20260702_171533_9A85B1`, Airflow state `success`, and artifact `shared/runs/PGTA_20260702_171533_9A85B1/logs/run_metadata.tsv` exists
last_pgta_diagnostics_smoke: passed on fengxian; `sync-airflow` changed `PGTA_20260702_171533_9A85B1` to `success` with `error_summary=null`, changed historical failed `PGTA_20260702_171200_A68C19` to `failed` with non-null `error_summary`, log API read metadata/stderr, artifact API returned metadata/stdout/stderr/config files, and missing log returned `LOG_NOT_FOUND`
last_frontend_placeholder: passed on fengxian at http://127.0.0.1:12959/ using Docker nginx placeholder
last_image_check: passed on fengxian; compose external images pulled and backend built with explicit tag
last_image_cleanup: removed 37 dangling <none> images; no docker system prune, no volume prune
last_e2e_smoke: partial PGT-A backend-to-Airflow metadata smoke passed; full frontend/log/QC/email E2E not run
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
- 需要实现 pgta UI 支持
- 需要实现 frontend 功能页面
- 需要实现 PGT-A dry-run target 和非法 target failure smoke
- 需要实现 Snakemake rule/qsub event receiver，才能提供 rule/sample/qsub 级错误摘要
```

## 10. 下一步建议

```text
1. 执行 T045 后续范围：扩展 PGT-A dry-run target，并保留 metadata runner 当前隔离写入策略。
2. 执行 T057：做 PGT-A run detail 前端展示，直接消费现有 run/detail/log/artifact/sync API。
3. 执行 T026/T043：补 Snakemake event receiver 和 rule/qsub 级事件，为更细失败摘要铺路。
```
