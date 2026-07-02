# 00 项目任务设计说明

## 1. 背景

实验部门完成上机后，会把样本清单放到服务器路径。当前生信人员通常需要手动解析样本表、补充家系/样本信息、调用 WES 或 NIPT 脚本、通过 qstat/qstate 查看任务状态，并在失败时手动查找日志。该 demo 的目标是展示 Airflow + Snakemake 如何把这些步骤变成可提交、可追踪、可监控、可断点续跑的工程化流程。

## 2. Demo 范围

### 包含

- WES qsub 流程接入。
- NIPT qsub 流程接入。
- NIPT Docker 版本接入。
- 样本表上传/填写。
- Airflow DAG 触发与状态监控。
- Snakemake rule 级状态展示。
- qsub job id、stdout、stderr 记录。
- QC 指标和报告展示。
- 成功/失败邮件提醒。
- 失败后 resume/rerun failed/rerun selected rule。

### 不包含

- 不替代正式 LIMS。
- 不替代最终临床报告系统。
- 不直接改造生产报告解读系统。
- 不接入真实患者数据。
- 不实现复杂权限系统；demo 可先使用单用户或简单登录。

## 3. 目标用户

- 生信开发人员：看任务状态、查失败日志、复跑部分步骤。
- 实验/运营展示对象：看样本提交、整体进度、QC 结果。
- 管理层/技术评审：理解 Airflow/Snakemake 对生产流程可观测性和可维护性的价值。

## 4. 核心演示故事线

```text
上传样本表
  -> 后端解析并生成 analysis_id
  -> Airflow DAG run 创建
  -> Snakemake 根据样本表构建 rule DAG
  -> qsub 并行执行 rule
  -> 前端展示 DAG 和 rule 状态
  -> 失败时定位 rule/sample/qsub/stderr
  -> 修复后 resume，不重复成功步骤
  -> 收集 QC 和 report
  -> 邮件通知完成
```

## 5. 成功标准

- 用户可以通过前端提交 WES mock 任务。
- Airflow UI 和前端都能看到任务运行。
- 前端能显示 Snakemake rule 状态。
- 任意一个 mock rule 失败后，前端能显示 stderr 摘要。
- 点击 resume 后，不重新跑已成功 rule。
- 完成后生成 QC 表格和报告链接。
- MailHog 或 SMTP 能收到成功/失败邮件。

## 6. 技术原则

- Airflow 管项目级流程，不管理每个生信 rule。
- Snakemake 管 rule/file dependency 和断点续跑。
- qsub 只作为计算资源提交层。
- FastAPI/React 提供对非 Airflow 用户友好的操作界面。
- PostgreSQL 业务库保存 demo 状态和可观测数据。
- 所有大文件、日志、报告留在 shared filesystem，不进 DB。
