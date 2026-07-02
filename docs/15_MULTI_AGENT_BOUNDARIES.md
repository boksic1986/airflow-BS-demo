# 15 多 Agent 分工边界和职责

## 1. 角色总览

| Agent | Primary responsibility | Owns | Must not own |
|---|---|---|---|
| Coordinator | 任务拆分、接口协调、交接质量 | TASKS/CURRENT_STATE/HANDOFF | 大量业务代码 |
| Infra | Docker、部署、路径、服务健康 | docker-compose, env, runbook | Pipeline 算法 |
| Backend | FastAPI、DB、Airflow client、logs/qc API | backend, DB schema, API contract | React UI 细节 |
| Airflow | DAG、Airflow task、通知流程 | dags, DAG docs | Snakemake rule 内部算法 |
| Snakemake/qsub | Snakefile、qsub profile、event wrapper | pipelines, qsub docs | 前端 UI |
| Frontend | React 页面、API client、状态展示 | frontend, UI spec | 后端 DB schema |
| QA | 测试、smoke、验收、失败复现 | tests, acceptance report | 新功能大改 |
| Docs | 文档一致性、demo script | docs | 代码行为改变 |

## 2. 文件所有权

```text
AGENTS.md                    Coordinator + Docs
CURRENT_STATE.md             Coordinator
TASKS.md                     Coordinator
HANDOFF.md                   All agents append, Coordinator maintains quality
SERVER_INFO.md               Infra, non-sensitive only
docker-compose.yaml          Infra
.env.example                 Infra + Backend + Airflow
dags/                        Airflow
backend/                     Backend
frontend/                    Frontend
pipelines/wes/               Snakemake
pipelines/nipt_qsub/         Snakemake
pipelines/nipt_docker/       Snakemake + Infra
docs/04_DATABASE_SCHEMA.md   Backend owns
/docs/05_API_CONTRACT.md     Backend owns, Frontend consumes
/docs/06_FRONTEND_SPEC.md    Frontend owns
/docs/07_AIRFLOW_DAG_SPEC.md Airflow owns
/docs/08_*                   Snakemake owns
```

## 3. RACI 示例

| Decision | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| API field change | Backend | Coordinator | Frontend/Airflow | QA |
| DB schema change | Backend | Coordinator | QA | Frontend |
| DAG task change | Airflow | Coordinator | Backend/Snakemake | QA |
| qsub parameter change | Snakemake | Coordinator | Infra | QA |
| UI layout change | Frontend | Coordinator | Backend | QA |
| server path change | Infra | Coordinator | Snakemake/Airflow | all |

## 4. 并行开发策略

### 可以并行

- Backend API mock 和 Frontend UI mock。
- Airflow DAG skeleton 和 Snakemake mock workflow。
- Infra compose 和 docs/demo script。

### 不建议并行

- 多个 agent 同时改 `docs/05_API_CONTRACT.md`。
- 多个 agent 同时改 DB migration。
- 多个 agent 同时改同一个 DAG。
- 多个 agent 同时改 qsub wrapper。

## 5. 冲突解决

冲突优先级：

```text
用户最新指令
  > AGENTS.md
  > API/DB/DAG contract docs
  > 代码现状
  > agent 自己的推断
```

## 6. 交接质量标准

不合格交接：

```text
"改好了，没测"
"应该可以"
"有问题下个 agent 看"
```

合格交接：

```text
完成了 T021 的 analysis_run/sample/rule_event model。
运行 pytest backend/tests/test_models.py 通过。
未运行 docker compose，因为当前环境没有 docker。
修改文件：...
下一步 T022 可基于 models 实现 upload parser。
风险：migration 未在真实 Postgres 测试。
```

## 7. Coordinator 合并前检查

- `TASKS.md` 状态是否真实。
- `CURRENT_STATE.md` 是否反映当前部署。
- `HANDOFF.md` 是否有最新记录。
- 文档 contract 和代码是否一致。
- 是否存在未解决的 blocking issue。
