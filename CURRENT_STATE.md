# CURRENT_STATE.md

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
当前阶段: P0 文档和环境探测
当前目标: 已落地 fengxian PGT-A demo 测试计划；正在初始化本地 Git 仓库和 GitHub/插件工作流文档
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
docker_compose_available: false on fengxian read-only preflight
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
last_commit: pending initial local commit/push
worktree_strategy: single-worktree for now; fengxian is code mirror only
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 3000 | not started | planned Docker service |
| backend | 8000 | not started | planned Docker service |
| airflow web/api | 8080 | not started | planned Docker service |
| postgres | 5432 | not started | internal only preferred |
| redis | 6379 | not started | internal only preferred |
| mailhog | 8025 | not started | demo only |

## 5. 数据库状态

```text
airflow_metadata_db: not started
biodemo_db: not started
migrations_tool: <alembic | sql scripts | unknown>
last_migration: none
```

## 6. Pipeline 接入状态

| Pipeline | DAG | Snakemake | qsub | Docker | QC | Status |
|---|---|---|---|---|---|---|
| PGT-A demo | planned `bio_pgta` | planned metadata/dry-run only | not used | service stack planned | not started | documented in `docs/18_PGTA_FENGXIAN_TEST_PLAN.md` |
| WES qsub | not started | not started | not started | n/a | not started | pending |
| NIPT qsub | not started | not started | not started | n/a | not started | pending |
| NIPT docker | not started | optional | n/a | not started | not started | pending |

## 7. 最近测试结果

```text
last_backend_tests: not run - no backend implementation yet
last_frontend_tests: not run - no frontend implementation yet
last_dag_import_tests: not run - no DAG implementation yet
last_snakemake_dryrun: not run in this task - plan document only
last_e2e_smoke: not run - services not implemented or started
```

## 8. 已知问题

| ID | Issue | Severity | Owner | Next step |
|---|---|---|---|---|
| K001 | airflow-demo 正在初始化 Git/GitHub 工作流 | low | coordinator/infra | 完成 initial commit/push 后更新 handoff |
| K002 | fengxian 已有 Docker 20.10.21，但未安装 Docker Compose v2 | medium | infra | 后续按计划安装用户级 Compose plugin v2.24.7 并验收 |
| K003 | BS10610 与 fengxian 用户和路径不同，不能复用 fengxian 硬编码路径 | medium | infra/coordinator | 迁移前把路径参数化到 `.env` 并重复 Level 0 preflight |

## 9. 当前阻塞

```text
真实部署/启动前阻塞:
- 需要 Docker Compose v2 可用
- 需要创建实际 compose/backend/frontend/airflow 代码
- 需要实现 bio_pgta DAG 和 pgta API/UI 支持
- 需要 initial commit/push 到 `git@github.com:boksic1986/airflow-BS-demo.git`
```

## 10. 下一步建议

```text
1. 执行 T001/T010 前先完成用户级 Docker Compose v2 plugin 准入。
2. 按 `docs/18_PGTA_FENGXIAN_TEST_PLAN.md` 拆分 PGTA-001 到 PGTA-007。
3. 服务器 `/home/jiucheng/project/airflow-demo` 只作为 GitHub 代码镜像，使用 clone/pull 同步。
```
