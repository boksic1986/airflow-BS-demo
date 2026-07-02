# 03 任务设计文档

## 1. 任务拆分原则

- 一个任务只改变一个明确层次：infra/backend/frontend/airflow/snakemake/docs/qa。
- 每个任务必须可验收、可回滚、可交接。
- 任务之间通过文档、API contract、DB schema、文件路径 contract 解耦。
- 优先实现 mock end-to-end，再替换真实 WES/NIPT wrapper。

## 2. 阶段划分

### P0 文档和环境探测

目标：让所有 agent 有统一上下文，服务器信息补齐但不泄密。

交付：

- `SERVER_INFO.md` 补齐非敏感信息。
- `CURRENT_STATE.md` 更新。
- 端口、路径、qsub 限制确定。

### P1 Airflow Docker 基础部署

目标：稳定启动 Airflow/Postgres/Redis/MailHog。

交付：

- `docker-compose.yaml`
- `.env.example`
- health check
- `make up/down/logs` 可选

### P2 Backend

目标：后端可接收任务、入库、触发 Airflow、返回状态。

交付：

- FastAPI app。
- DB model/migration。
- server-path sample discovery and selected manifest creation for PGT-A v1。
- Airflow client。
- run/log/qc/artifact API。

### P3 Airflow DAG

目标：三个 pipeline DAG 骨架跑通。

交付：

- `bio_wes_qsub`
- `bio_nipt_qsub`
- `bio_nipt_docker`
- success/fail email task

### P4 Snakemake/qsub

目标：rule 状态和 qsub job 可观测。

交付：

- WES mock Snakefile。
- qsub profile。
- qsub wrapper。
- event logger。
- resume/rerun mode。

### P5 Frontend

目标：用户能提交、查看、定位失败、触发重分析。

交付：

- Dashboard。
- Submit page。
- Run detail。
- Snakemake rule table。
- QC panel。
- Log viewer。
- Reanalysis actions。

### P6 QC/日志/邮件

目标：报告和错误摘要可用于展示。

交付：

- QC parser。
- artifact registry。
- MultiQC/Snakemake report link。
- email templates。

### P7 NIPT

目标：接入 NIPT qsub 和 Docker 两种运行方式。

交付：

- NIPT qsub wrapper。
- NIPT Docker runner。
- NIPT QC parser。

### P8 Demo 验收

目标：形成 10-15 分钟稳定演示。

交付：

- 成功场景。
- 失败场景。
- resume 场景。
- 演示脚本。
- 最终交接文档。

## 3. 任务验收模板

每个任务的验收必须包含：

```text
功能验收:
  - 用户可观察行为
工程验收:
  - 代码结构/接口/文档是否一致
测试验收:
  - 运行的命令和结果
失败验收:
  - 错误路径是否清晰
回滚验收:
  - 如何撤销改动或停止服务
```

## 4. 依赖约束

- Frontend 不直接依赖 Airflow API；只依赖 backend API。
- Airflow DAG 不直接依赖 frontend。
- Snakemake event logger 不直接依赖 frontend。
- Backend 可以调用 Airflow API 和读 shared filesystem。
- qsub wrapper 可以 POST backend event API；如果 backend 不可用，必须至少写本地 fallback event JSONL。

## 5. 完成定义 Definition of Done

任务只有在以下条件满足时才可标为 done：

- 任务范围内功能完成。
- 相关测试运行并记录。
- 相关文档更新。
- `CURRENT_STATE.md` 更新。
- `HANDOFF.md` 写入交接。
- 没有未说明的失败或跳过测试。
