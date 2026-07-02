# airflow-demo 文档包

本仓库目标是构建一个本地/服务器可部署的 Airflow + Snakemake 生信流程调度 demo，用于展示 WES、NIPT qsub 流程、NIPT Docker 流程的任务提交、状态监控、rule 级日志、QC 展示、失败诊断、邮件通知和断点重分析能力。

## 项目定位

这是一个展示型工程，不直接替代生产报告系统，也不直接改造生产流程核心脚本。第一阶段通过 wrapper、配置文件、共享目录和事件采集，把已有流程接入统一调度与可视化界面。

## 建议目录结构

```text
airflow-demo/
  AGENTS.md
  CURRENT_STATE.md
  TASKS.md
  HANDOFF.md
  SERVER_INFO.md
  docs/
  .agents/skills/
  docker-compose.yaml
  .env.example
  dags/
  backend/
  frontend/
  pipelines/
  shared/
```

## 文档阅读顺序

1. `AGENTS.md`：Codex/agent 必须遵守的项目级规则。
2. `CURRENT_STATE.md`：当前服务器、仓库、部署、测试状态，由 agent 持续维护。
3. `docs/00_PROJECT_BRIEF.md`：业务目标和 demo 边界。
4. `docs/01_SYSTEM_ARCHITECTURE.md`：总体架构。
5. `docs/02_ENGINEERING_SPEC.md`：工程规范。
6. `docs/03_TASK_DESIGN.md`：任务拆解与验收。
7. `docs/15_MULTI_AGENT_BOUNDARIES.md`：多个 agent 的职责边界。
8. `.agents/skills/*/SKILL.md`：Codex 可复用工作流技能。

## 不允许的事情

- 不允许把真实患者隐私数据、真实样本清单、生产数据库账号、SMTP 密码、API key 写入仓库。
- 不允许在未经确认时修改或删除生产 WES/NIPT 目录。
- 不允许让 demo 自动提交大规模 qsub 任务压垮集群。
- 不允许直接读写 Airflow metadata DB 作为业务数据源。
- 不允许把 Airflow task 拆到每个 Snakemake rule；rule 级状态应从 Snakemake 事件或日志采集。

## 推荐开发节奏

```text
P0: 文档和服务器探测
P1: Airflow Docker Compose 基础部署
P2: FastAPI 后端 + biodemo PostgreSQL
P3: Airflow DAG 骨架
P4: Snakemake/qsub 接入和 rule 级事件
P5: React 前端页面
P6: QC、日志、邮件通知
P7: NIPT Docker 流程接入
P8: demo 脚本、验收、交接
```

## 服务器信息

服务器信息先留空，Codex/agent 应在获得授权后补充到 `SERVER_INFO.md`，不要写入密钥。
