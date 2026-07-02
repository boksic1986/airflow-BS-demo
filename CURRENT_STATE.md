# CURRENT_STATE.md

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
当前阶段: P1 基础部署准入和最小服务骨架
当前目标: fengxian 用户级 Compose v2、服务器镜像、Compose config、backend health smoke 已通过；下一步是 Airflow 初始化和 biodemo DB 基础
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
last_verified_code_commit: dd1d8a7
worktree_strategy: single-worktree for now; fengxian is code mirror only
fengxian_mirror: /home/jiucheng/project/airflow-demo cloned from origin/main, clean after local .env ignored
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 3000 | not started | nginx placeholder service defined, not part of current smoke |
| backend | 8000 | stopped after successful smoke | `/api/health` returned `{"status":"ok"}` on fengxian |
| airflow web/api | 8080 | not started | service skeleton defined, Airflow initialization pending |
| postgres | 5432 | stopped after successful smoke | container starts; no biodemo migration yet |
| redis | 6379 | stopped after successful smoke | container starts |
| mailhog | 8025 | stopped after successful smoke | HTTP GET probe passed |

## 5. 数据库状态

```text
airflow_metadata_db: postgres container starts, Airflow metadata initialization not run
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
last_compose_config: passed on fengxian with Docker Compose v2.24.7
last_minimal_smoke: passed on fengxian for postgres redis mailhog backend, then docker compose down
last_e2e_smoke: not run - Airflow/DAG/frontend functional path not implemented
```

## 8. 已知问题

| ID | Issue | Severity | Owner | Next step |
|---|---|---|---|---|
| K003 | BS10610 与 fengxian 用户和路径不同，不能复用 fengxian 硬编码路径 | medium | infra/coordinator | 迁移前把路径参数化到 `.env` 并重复 Level 0 preflight |
| K004 | 远端直接访问 GitHub release 不稳定 | low | infra | 优先本地 GitHub 下载后 scp 到 fengxian；国内 Docker CE 镜像作为 Compose fallback |

## 9. 当前阻塞

```text
真实部署/启动前阻塞:
- 需要初始化 Airflow metadata 和管理员用户
- 需要实现 biodemo DB migration
- 需要实现 bio_pgta DAG 和 pgta API/UI 支持
- 需要实现 frontend 功能页面
```

## 10. 下一步建议

```text
1. 执行 T011：初始化并启动 Airflow web/scheduler/worker，验证 `/health`。
2. 执行 T021/T023 前先确定 biodemo migration 工具和 Airflow API auth。
3. PGT-A 接入仍从 T027/T035/T045/T057/T084 开始，不直接跳到 metadata smoke。
```
