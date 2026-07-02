# CURRENT_STATE.md

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
当前阶段: P1 基础部署准入和最小服务骨架
当前目标: fengxian Airflow/Postgres/Redis/MailHog/backend/frontend placeholder smoke 已通过；下一步是 biodemo DB migration 和 Airflow API client
最近更新时间: 2026-07-02
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
last_verified_code_commit: 9c640dc
worktree_strategy: single-worktree for now; fengxian is code mirror only
fengxian_mirror: /home/jiucheng/project/airflow-demo cloned from origin/main, clean after local .env ignored
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 12959 | stopped after successful smoke | Docker nginx placeholder returned `airflow-demo frontend placeholder`; host 3000 is occupied by non-project next-server |
| backend | 8000 | stopped after successful smoke | `/api/health` returned `{"status":"ok"}` on fengxian; image `airflow-demo/backend:0.1.0` built |
| airflow web/api | 12958 | stopped after successful smoke | `/health` returned healthy metadatabase and scheduler after `airflow-init` |
| postgres | internal 5432 | stopped after successful smoke | image `postgres:15-alpine`; Airflow metadata initialized; no host port published |
| redis | internal 6379 | stopped after successful smoke | image `redis:7-alpine`; no host port published |
| mailhog | 8025 | stopped after successful smoke | HTTP GET probe passed |

## 5. 数据库状态

```text
airflow_metadata_db: initialized by `docker compose -f docker-compose.yaml up airflow-init`; admin user exists, password only in remote .env
biodemo_db: not migrated or initialized
migrations_tool: <alembic | sql scripts | unknown>
last_migration: none
```

## 6. Pipeline 接入状态

| Pipeline | DAG | Snakemake | qsub | Docker | QC | Status |
|---|---|---|---|---|---|---|
| PGT-A demo | planned `bio_pgta` | planned metadata/dry-run only | not used | base service stack config passed | not started | documented in `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`; no PGT-A run yet |
| WES qsub | not started | not started | not started | n/a | not started | pending |
| NIPT qsub | not started | not started | not started | n/a | not started | pending |
| NIPT docker | not started | optional | n/a | not started | not started | pending |

## 7. 最近测试结果

```text
last_backend_tests: remote smoke on fengxian passed for GET /api/health returning {"status":"ok"}
last_frontend_tests: not run - no frontend implementation yet
last_dag_import_tests: not run - no DAG implementation yet
last_snakemake_dryrun: not run - PGT-A integration intentionally out of scope
last_compose_config: passed on fengxian with Docker Compose v2.24.7 for commit 9c640dc; Airflow host port 12958 and frontend host port 12959 rendered correctly
last_minimal_smoke: passed on fengxian for postgres redis mailhog backend frontend airflow-api-server airflow-scheduler airflow-worker, then docker compose down
last_airflow_health: passed on fengxian at http://127.0.0.1:12958/health with healthy metadatabase and scheduler
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
- 需要实现 biodemo DB migration
- 需要实现 bio_pgta DAG 和 pgta API/UI 支持
- 需要实现 frontend 功能页面
```

## 10. 下一步建议

```text
1. 执行 T021：确定并实现 biodemo DB migration 工具和基础表。
2. 执行 T023：实现 FastAPI Airflow API client，使用容器内 `http://airflow-api-server:8080`。
3. PGT-A 接入仍从 T027/T035/T045/T057/T084 开始，不直接跳到 metadata smoke。
```
