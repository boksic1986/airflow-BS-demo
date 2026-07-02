# TASKS.md

任务状态：`todo` / `in_progress` / `blocked` / `review` / `done`。

## P0 文档和环境探测

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T000 | 初始化仓库文档 | coordinator/docs | none | docs, AGENTS, skills | 文档完整、占位符明确 | done |
| T001 | 探测服务器环境 | infra | T000 | SERVER_INFO.md 更新 | docker/qsub/python/node 状态清楚 | done |
| T002 | 确定部署路径和数据路径 | infra/coordinator | T001 | CURRENT_STATE.md 更新 | 项目路径和 shared 路径确定 | done |
| T003 | 确定 demo 数据策略 | coordinator/snakemake | T000 | mock samples 规范 | 不使用真实患者数据 | todo |
| T004 | fengxian PGT-A demo 测试计划 | coordinator/docs | T000 | docs/18_PGTA_FENGXIAN_TEST_PLAN.md | pgta/bio_pgta 命名、Compose 准入、Level 0-4 验收、BS10610 迁移注意事项明确 | done |
| T005 | 本地 Git/GitHub 和插件工作流文档 | coordinator/docs | T000,T004 | git remote, docs/19, plugin usage docs | 本地 main 仓库指向 GitHub remote；superpowers/GitHub 插件和 fengxian 镜像规则写入文档 | done |

## P1 Airflow Docker 基础部署

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T010 | 创建 docker-compose 基础服务 | infra | T001 | docker-compose.yaml, .env.example | docker compose config 通过 | done |
| T011 | 启动 Airflow/Postgres/Redis | infra | T010 | Airflow UI/API 可访问 | airflow health 正常 | done |
| T012 | 增加 MailHog demo 邮件服务 | infra | T010 | mailhog service | http://host:8025 可访问 | done |
| T013 | 定义 shared volume 目录 | infra | T010 | shared/{uploads,runs,reports,logs} | 容器内路径一致 | done |
| T014 | fengxian 用户级 Docker Compose v2 准入 | infra | T001,T004 | `$HOME/.docker/cli-plugins/docker-compose` | `docker compose version` 输出固定 v2 版本，未做系统级 Docker 升级 | done |

## P2 Backend API 和数据库

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T020 | FastAPI 项目骨架 | backend | T010 | backend/app | /health 返回 ok | done |
| T021 | biodemo DB models/migrations | backend | T020 | analysis_run/sample/rule_event/qc/artifact | migration 可重复执行 | todo |
| T022 | 文件上传和样本表解析 | backend | T021 | upload API/parser | csv/tsv/xlsx mock 样本可解析 | todo |
| T023 | Airflow API client | backend | T020,T011 | trigger/list/get dag run | mock 或真实 API 测试通过 | todo |
| T024 | run 状态 API | backend | T021 | /runs endpoints | 可返回列表和 detail | todo |
| T025 | logs/artifacts API | backend | T021 | tail log/artifact link | 缺失文件返回明确错误 | todo |
| T026 | Snakemake event receiver | backend | T021 | /events/snakemake | 可幂等 upsert rule event | todo |
| T027 | PGT-A `pgta` pipeline API 支持 | backend | T021,T023,T004 | `/api/runs` 支持 pipeline=pgta 和 target 参数 | 可提交 metadata/dryrun/invalid target 测试 run | todo |

## P3 Airflow DAG

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T030 | DAG 公共工具 | airflow | T011,T023 | dags/common | import check 通过 | todo |
| T031 | bio_wes_qsub DAG 骨架 | airflow | T030 | dags/bio_wes_qsub.py | dry run/mock run 成功 | todo |
| T032 | bio_nipt_qsub DAG 骨架 | airflow | T030 | dags/bio_nipt_qsub.py | dry run/mock run 成功 | todo |
| T033 | bio_nipt_docker DAG 骨架 | airflow | T030 | dags/bio_nipt_docker.py | dry run/mock run 成功 | todo |
| T034 | email notify task | airflow/backend | T030,T012 | success/fail notify | MailHog 收到邮件 | todo |
| T035 | bio_pgta DAG 骨架 | airflow | T030,T027,T004 | dags/bio_pgta.py | metadata target mock/real-light run 成功，不使用 qsub | todo |

## P4 Snakemake/qsub 接入

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T040 | WES mock Snakefile | snakemake | T013 | pipelines/wes/workflow | snakemake -n 通过 | todo |
| T041 | qsub submit wrapper | snakemake | T040,T026 | qsub_submit.py | 能记录 qsub jobid 或 mock jobid | todo |
| T042 | qsub profile | snakemake | T041 | profiles/qsub/config.yaml | demo 限额生效 | todo |
| T043 | rule event logger | snakemake/backend | T026,T040 | logger/POST events | 前端/DB 可见 rule 状态 | todo |
| T044 | resume/rerun 策略 | snakemake/airflow | T031,T040 | mode -> snakemake flags | 不默认 forceall | todo |
| T045 | PGT-A Snakemake runner | snakemake/airflow | T035,T004 | pgta config 生成和 metadata/dry-run runner | 输出只写 shared/runs/<analysis_id>，PGT_A 目录只读 | todo |

## P5 Frontend

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T050 | React 项目骨架 | frontend | T020 | frontend/src | 首页可访问 | todo |
| T051 | Submit Analysis 页面 | frontend | T022,T023 | upload/form UI | 提交后生成 run | todo |
| T052 | Runs Dashboard | frontend | T024 | run list/status cards | 可筛选 pipeline/status | todo |
| T053 | Run Detail 页面 | frontend | T024,T026 | overview/airflow/snakemake tabs | 展示 rule 状态 | todo |
| T054 | QC 面板 | frontend | T060 | QC table/MultiQC link | pass/warn/fail 可见 | todo |
| T055 | Log Viewer | frontend | T025 | stdout/stderr tail | 失败默认显示 stderr | todo |
| T056 | Reanalysis UI | frontend/backend | T044 | resume/rerun buttons | 后端触发正确 mode | todo |
| T057 | PGT-A run detail 展示 | frontend | T027,T035,T025 | pgta run overview/log/artifact UI | metadata 成功和非法 target 失败均可定位日志 | todo |

## P6 QC/日志/报告/邮件

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T060 | QC parser | backend/snakemake | T021,T040 | qc_metric 写库 | mock QC 指标展示 | todo |
| T061 | MultiQC/Snakemake report artifact | snakemake/backend | T040,T060 | report link | artifact 表有记录 | todo |
| T062 | error summary extractor | backend | T025,T026 | last error summary | 失败页显示核心错误 | todo |
| T063 | 邮件模板 | backend/airflow | T034,T060 | success/fail emails | 邮件含 QC 和错误链接 | todo |

## P7 NIPT 接入

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T070 | NIPT qsub wrapper 设计 | snakemake | T032,T041 | pipelines/nipt_qsub | mock dry-run 通过 | todo |
| T071 | NIPT Docker runner | infra/snakemake | T033 | pipelines/nipt_docker | docker mock run 通过 | todo |
| T072 | NIPT QC parser | backend/snakemake | T060,T070 | nipt metrics | 前端可见 NIPT QC | todo |

## P8 Demo 验收

| ID | Task | Owner agent | Dependencies | Deliverables | Acceptance | Status |
|---|---|---|---|---|---|---|
| T080 | 端到端 smoke test | qa | T050-T063 | smoke script/report | WES mock 成功+失败场景 | todo |
| T081 | Demo script | docs/coordinator | T080 | docs/17_DEMO_SCRIPT.md | 10-15 分钟可演示 | todo |
| T082 | 回滚和清理 runbook | infra/docs | T080 | docs/11 更新 | 不删除 volume 的停止流程清楚 | todo |
| T083 | 最终交接 | coordinator | T080-T082 | HANDOFF/CURRENT_STATE | 下一阶段任务明确 | todo |
| T084 | PGT-A Level 0-3 smoke 验收 | qa | T014,T027,T035,T045,T057 | acceptance report | preflight、metadata、dry-run、failure smoke 记录完整 | todo |

## 任务卡模板

```markdown
### TXXX - <title>

Owner: <agent>
Status: todo
Dependencies: <ids>
Scope:
- 
Out of scope:
- 
Files likely touched:
- 
Acceptance:
- [ ] 
Test commands:
- 
Rollback:
- 
Notes:
```
