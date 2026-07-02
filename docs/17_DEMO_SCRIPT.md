# 17 Demo 演示脚本

## 1. 演示目标

向团队展示 Airflow + Snakemake 对 WES/NIPT 生信流程的帮助：

- 从手工提交变成网页提交。
- 从 qstat 手动查看变成 DAG + rule 级监控。
- 从翻服务器日志变成按 sample/rule 查看 stderr。
- 从失败后不确定如何续跑变成 resume/rerun。
- 从流程完成后人工通知变成邮件和报告链接。

## 2. 准备

- 服务已启动。
- 前端可访问。
- Airflow UI 可访问。
- MailHog 可访问。
- PGT-A demo rawdata_root 已在 `INPUT_SCAN_ROOTS` 白名单内。
- 成功场景和失败场景都已 smoke test。

## 3. 10-15 分钟流程

### Step 1: 展示 Dashboard

说明：

```text
这里是生信任务中心，可以看到 PGT-A、WES、NIPT qsub、NIPT Docker 的运行状态。
```

### Step 2: 创建 PGT-A 项目

操作：

- 打开 Submit。
- 选择 PGT-A。
- 填写项目名和服务器 `rawdata_root`。
- 点击 Scan。
- 勾选 1-2 个候选样本。
- 目标选择 metadata。
- 填写 email_to。
- 点击 Create。

说明：

```text
FASTQ 通常有 5-6G，不通过网页上传。后端只扫描白名单服务器路径，保存 R1/R2 路径，生成 analysis_id、workdir 和 selected manifest。当前 PGT-A v1 采用两步模式：先创建项目，再单独 submit 到 Airflow。
```

### Step 3: 提交到 Airflow metadata DAG

操作：

- 在 Run Detail 点击 Submit。
- 确认状态从 created 变成 submitted。
- 打开 Airflow link。

说明：

```text
submit action 只允许 pgta + metadata + created run。Airflow 执行 bio_pgta 的四个项目级步骤，并由 Snakemake 在隔离 workdir 里生成 logs/run_metadata.tsv。
```

### Step 4: 展示 Airflow DAG

操作：

- 打开 Run Detail -> Airflow tab。
- 点击 Airflow link。

说明：

```text
Airflow 管的是项目级步骤，不拆每个 rule，这样 DAG 更稳定、可读。
```

### Step 5: 展示 Snakemake rule 状态

操作：

- 打开 Snakemake tab。
- 展示 rule/sample/qsub job id/status。

说明：

```text
rule 级状态来自 Snakemake/qsub event，失败时可以定位到具体 rule、sample、qsub job 和日志。
```

### Step 6: 展示失败场景

操作：

- 提交或打开一个 mock failed run。
- 展示 failed rule。
- 点击 stderr。

说明：

```text
以前需要登录服务器找日志，现在页面直接给出失败 rule 和最后错误。
```

### Step 7: Resume

操作：

- 点击 Resume failed run。
- 展示已成功 rule skipped/cached，失败 rule 重跑。

说明：

```text
Snakemake 根据文件依赖和 incomplete 状态决定重跑，不需要全量重新分析。
```

### Step 8: QC 和邮件

操作：

- 打开 QC tab。
- 打开 MultiQC/report artifact。
- 打开 MailHog 邮件。

说明：

```text
完成后自动收集 QC，登记 report，并发送成功或失败通知。
```

## 4. 演示中的重点话术

```text
Airflow 不是替代 Snakemake，而是管理一次分析任务的生命周期。
Snakemake 不负责用户提交界面，但非常适合生信 rule 依赖和断点续跑。
前端不是重做 Airflow UI，而是提供实验/生信人员更容易理解的入口。
```

## 5. 常见问题回答

### 为什么不用 Airflow 管每个 rule？

因为生信 rule 数量和 sample 数量会动态变化。Airflow 更适合稳定的项目级 orchestration，Snakemake 更适合文件依赖和 rule 并行。

### 失败后会不会全部重跑？

默认不会。Resume 使用已有 workdir 和 Snakemake 文件依赖，只重跑 incomplete/failed 部分。

### 能接真实流程吗？

可以，但建议先通过 wrapper 接入，不直接重写生产脚本。先让日志、QC、事件、路径规范统一。

### 这个能上生产吗？

当前是 demo 架构。生产化需要补充权限、审计、HTTPS、secrets 管理、稳定部署和数据合规。
