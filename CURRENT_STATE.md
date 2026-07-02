# CURRENT_STATE.md

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
当前阶段: P2 Backend API 和数据库基础
当前目标: T022/T024 已改为 PGT-A 服务器路径扫描、样本勾选、创建 run 和 run 查询；已在 fengxian 远端验收
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
active_branch: codex/backend/T022-T024-server-path-runs
last_verified_code_commit: 9928b9c
worktree_strategy: single-worktree for now; fengxian is code mirror only
fengxian_mirror: /home/jiucheng/project/airflow-demo cloned from GitHub; T022/T024 verified on origin/codex/backend/T022-T024-server-path-runs; server smoke created untracked shared/runs output only
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 12959 | stopped after successful smoke | Docker nginx placeholder returned `airflow-demo frontend placeholder`; host 3000 is occupied by non-project next-server |
| backend | 8000 | stopped after successful smoke | `/api/health`, `/api/health/db`, `/api/input/scan`, `/api/runs`, run detail and samples passed on fengxian; image `airflow-demo/backend:0.1.0` |
| airflow web/api | 12958 | stopped after successful smoke | `/health` returned healthy metadatabase and scheduler after `airflow-init` |
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
| PGT-A demo | planned `bio_pgta` | planned metadata/dry-run only | not used | server-path project creation passed | not started | `/api/input/scan` and `/api/runs` can create `pgta` run in `created` state; no Airflow trigger or PGT-A execution yet |
| WES qsub | not started | not started | not started | n/a | not started | pending |
| NIPT qsub | not started | not started | not started | n/a | not started | pending |
| NIPT docker | not started | optional | n/a | not started | not started | pending |

## 7. 最近测试结果

```text
last_backend_tests: remote Dockerized pytest on fengxian passed, 17 tests; `GET /api/health`, `/api/health/db`, `/api/input/scan`, JSON `POST /api/runs`, run detail and samples smoke passed
last_frontend_tests: not run - no frontend implementation yet
last_dag_import_tests: not run - no DAG implementation yet
last_snakemake_dryrun: not run - PGT-A integration intentionally out of scope
last_compose_config: passed on fengxian with Docker Compose v2.24.7 for commit 9928b9c; backend now renders `INPUT_SCAN_ROOTS` and read-only PGT-A data mount
last_minimal_smoke: passed on fengxian for postgres redis mailhog backend frontend airflow-api-server airflow-scheduler airflow-worker, then docker compose down
last_airflow_health: passed on fengxian at http://127.0.0.1:12958/health with healthy metadatabase and scheduler
last_biodemo_migration: `biodemo-db-init` first run created role/database, repeat run succeeded; `alembic upgrade head` applied 20260702_0001 and repeat run succeeded
last_backend_airflow_client: mock tests covered health/list/get/trigger; real smoke verified backend `/api/health/airflow` against Airflow `/health`
last_backend_build: backend image built on fengxian using `backend/pip.conf` TUNA PyPI mirror and `/opt/venv`; dependency install step dropped from about 9 minutes to about 11 seconds after mirror config
last_pgta_project_create_smoke: passed on fengxian; scan root `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` returned 5 candidates with `truncated=true`, created `PGTA_20260702_162531_74CE91` with 2 samples, status `created`, `dag_run_id=null`, and generated `samples.selected.tsv` plus `request.json`
last_frontend_placeholder: passed on fengxian at http://127.0.0.1:12959/ using Docker nginx placeholder
last_image_check: passed on fengxian; compose external images pulled and backend built with explicit tag
last_image_cleanup: removed 37 dangling <none> images; no docker system prune, no volume prune
last_e2e_smoke: not run - Airflow/DAG/frontend functional path not implemented
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
- 需要实现从 `created` run 触发 Airflow DAG 的后续 API/服务层
- 需要实现 bio_pgta DAG trigger、PGT-A config generation 和 execution runner
- 需要实现 pgta UI 支持
- 需要实现 frontend 功能页面
```

## 10. 下一步建议

```text
1. 执行 T027/T035 前置设计：把已创建的 `pgta` run 转为 Airflow `bio_pgta` DAG trigger，仍只允许 `target=metadata`。
2. 执行 T045：为 PGT-A 生成隔离 config 和 metadata runner，输出只写 `shared/runs/<analysis_id>`。
3. 再执行 T057/T084：前端展示和 Level 0-3 smoke 验收。
```
