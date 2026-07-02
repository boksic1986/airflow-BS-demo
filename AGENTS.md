# AGENTS.md

本文件是 airflow-demo 仓库的 Codex/agent 项目指令。任何 agent 在执行任务前必须先阅读本文件、`CURRENT_STATE.md`、`TASKS.md`、相关 `docs/` 文档和最近的 `HANDOFF.md`。

## 1. 项目目标

构建一个可在服务器本地部署的 Airflow demo，用于展示：

- 前端提交 WES / NIPT 分析任务。
- 上传或填写样本清单。
- Airflow 负责项目级 DAG 调度、状态追踪、邮件通知。
- Snakemake 负责 rule/file dependency、qsub 并行、断点续跑。
- qsub 流程能够记录 job id、stdout、stderr。
- 前端展示 Airflow DAG 状态、Snakemake rule 状态、QC 指标、正常日志和失败错误日志。
- 支持失败后 resume 或针对部分 rule/sample 重分析，默认不重新跑全部流程。

## 2. 架构边界

### Airflow 负责

- 接收一次分析请求并创建 DAG run。
- 执行项目级步骤：校验、准备目录、生成配置、运行 pipeline、收集 QC、发送通知。
- 管理重试、状态、任务日志、邮件通知。

### Snakemake 负责

- 管理生信流程 rule、文件依赖和并行。
- 根据已有输出决定跳过已完成步骤。
- 使用 qsub profile 提交集群任务。
- 生成 rule/job 级日志和事件。

### FastAPI 后端负责

- 上传样本清单。
- 解析样本表并生成 analysis_id。
- 写入业务数据库 biodemo。
- 调用 Airflow REST API 触发 DAG run。
- 提供 runs、samples、rule_events、qc、logs、artifacts API。
- 接收 Snakemake/qsub wrapper 事件。

### React 前端负责

- 提供提交页面、任务列表、run detail、QC 面板、日志查看、重分析入口。
- 不直接连接 Airflow DB 或业务 DB。
- 所有数据通过 FastAPI 获取。

### PostgreSQL 负责

- Airflow metadata DB：Airflow 自己使用。
- biodemo DB：业务状态、样本、QC、artifact、Snakemake rule 事件。
- 两者可以共用同一个 Postgres 实例，但必须使用不同 database/schema。

## 3. 强制安全规则

agent 不得执行以下操作，除非用户明确授权且已在 `HANDOFF.md` 记录原因：

- `rm -rf` 删除项目根目录、shared 数据、生产流程目录、参考基因组目录。
- `docker system prune -a`、`docker volume prune`、`docker compose down -v`。
- `git reset --hard`、`git clean -fdx`。
- 修改生产 WES/NIPT 核心脚本行为。
- 直接连接或修改生产数据库。
- 提交超过 demo 限额的 qsub 任务。
- 将 `.env`、密码、token、SMTP 密码、数据库密码、患者信息提交到 Git。

## 4. 数据和隐私规则

- demo 样本表必须使用 mock/sample 数据。
- 真实路径可以写成占位符或写入本地未跟踪的 `SERVER_INFO.local.md`。
- 真实患者姓名、证件号、手机号、家系隐私、临床诊断信息不得进入仓库。
- 测试数据只保留最小 FASTQ/mock FASTQ 或 synthetic records。
- 大型参考文件、BAM、VCF、FASTQ 不进入 Git。

## 5. 开发流程

每个 agent 开始任务时必须：

1. 读取 `CURRENT_STATE.md`。
2. 读取 `TASKS.md`，确认任务 ID、范围、依赖。
3. 读取本任务相关文档。
4. 检查当前 Git 状态。
5. 在自己的分支或 worktree 工作。
6. 只修改任务范围内文件。
7. 运行与改动匹配的最小测试。
8. 更新 `CURRENT_STATE.md`、`TASKS.md`、`HANDOFF.md`。

推荐分支命名：

```text
codex/<area>/<task-id>-<short-name>
```

示例：

```text
codex/backend/T020-run-api
codex/airflow/T030-wes-dag
codex/frontend/T050-run-detail-page
```

## 6. 工作粒度

每个任务应该尽量小：

- 一个 PR/branch 只解决一个明确目标。
- 不要同时改 backend、frontend、DAG、Snakemake，除非任务明确要求端到端联调。
- 修改接口时必须同步更新 `docs/05_API_CONTRACT.md`。
- 修改数据库模型时必须同步更新 `docs/04_DATABASE_SCHEMA.md`。
- 修改 DAG 时必须同步更新 `docs/07_AIRFLOW_DAG_SPEC.md`。
- 修改 Snakemake/qsub 行为时必须同步更新 `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`。

## 7. 测试要求

根据改动类型执行：

```text
后端改动: pytest backend/tests
前端改动: npm test 或 npm run lint
DAG 改动: python -m py_compile dags/*.py + airflow dags list/import check
Docker 改动: docker compose config
Snakemake 改动: snakemake -n --printshellcmds 或 mock profile dry-run
文档改动: 检查链接、路径、任务 ID 和验收标准是否一致
```

如果某个测试不能运行，必须在 `HANDOFF.md` 说明：

- 未运行的命令。
- 未运行原因。
- 需要下一位 agent 或用户补充的环境条件。

## 8. 命令约定

后续实现中建议提供以下 Make targets：

```bash
make env-check        # 检查 docker、python、node、airflow env
make compose-config   # docker compose config
make up               # 启动 demo 服务
make down             # 仅停止服务，不删除 volume
make test-backend
make test-frontend
make test-dags
make smoke            # 端到端 mock run
make logs             # 查看关键服务日志
```

agent 不得假设这些命令已经存在；如果不存在，应按任务设计补充。

## 9. 失败处理

遇到失败时不要盲目重试。必须先记录：

```text
失败命令:
退出码:
stderr 摘要:
可能原因:
已尝试修复:
下一步建议:
```

对于 qsub/Snakemake 失败，必须尽量定位到：

```text
analysis_id
rule
sample_id
snakemake jobid
qsub jobid
stdout path
stderr path
最后 100 行错误摘要
```

## 10. 重分析默认策略

默认优先级：

1. `resume`: 同一 workdir，使用已有输出和 incomplete 标记，不重新分析成功步骤。
2. `rerun_failed`: 只重跑失败或 incomplete rule。
3. `rerun_rule`: 指定 rule/sample/target。
4. `clone_new`: 新 analysis_id，新 workdir，用于参数变化。
5. 禁止默认使用 `--forceall`。

## 11. 文档维护规则

任何实现差异必须及时写回文档：

- 新增服务、端口、环境变量：更新 `docs/02_ENGINEERING_SPEC.md` 和 `docs/11_DEPLOYMENT_RUNBOOK.md`。
- 新增 API：更新 `docs/05_API_CONTRACT.md`。
- 新增 DB 表/字段：更新 `docs/04_DATABASE_SCHEMA.md`。
- 新增 DAG task：更新 `docs/07_AIRFLOW_DAG_SPEC.md`。
- 新增 rule 事件字段：更新 `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`。
- 新增前端页面：更新 `docs/06_FRONTEND_SPEC.md`。

## 12. 交接要求

每次 agent 结束任务必须更新 `HANDOFF.md` 最新条目，包含：

- 本次目标。
- 已完成内容。
- 修改文件。
- 运行命令和结果。
- 未解决问题。
- 下一步建议。
- 风险和回滚方式。

## 13. 多 agent 协作约定

- Coordinator agent 负责拆任务和合并交接，不直接大改代码。
- Infra agent 负责 Docker、部署、服务器路径。
- Backend agent 负责 FastAPI、DB、Airflow client。
- Airflow agent 负责 DAG 和 Airflow 配置。
- Snakemake agent 负责 Snakefile、qsub profile、logger/qsub wrapper。
- Frontend agent 负责 React 页面和 API client。
- QA agent 负责测试、smoke、验收和失败复现。
- Docs agent 负责文档一致性。

冲突时优先遵守：用户明确要求 > 本 AGENTS.md > 相关 docs > 代码现状。
