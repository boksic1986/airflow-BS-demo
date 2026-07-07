# 17 Demo 演示脚本

## 1. 演示目标

本 demo 用 10-15 分钟展示 airflow-demo 已经具备的核心能力：

- 前端从服务器路径扫描样本，不上传 5-6G FASTQ。
- FastAPI 创建 run、记录 samples、触发 Airflow DAG。
- Airflow 管项目级生命周期，Snakemake 管 rule/file dependency 和 resume。
- 前端查看 run 状态、samples、logs、artifacts、rules 和 QC。
- WES mock 展示 qsub job id、rule 状态、QC pass 和 rerun rule。
- PGT-A Level 4 展示真实 `baseline_qc` workflow success，同时明确当前 G10/G11 样本 QC decision 为 `FAIL`。

## 2. 演示前准备

- 前端：`http://fengxian:12959/`。
- Airflow 管理 UI：`http://fengxian:12958/`，仅作为管理员调试入口。
- Backend API：`http://fengxian:8000/api`。
- PGT-A demo rawdata root：`/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28`。
- 已验证 run：
  - PGT-A Level 4：`PGTA_20260706_162150_00C4FD`。
  - WES QC success：`WES_20260705_164813_C5561C`。
  - WES rerun rule：`WES_20260705_162041_2507AF`。
- 本轮 MailHog 邮件通知尚未实现，`T034/T063` 仍是后续任务；演示时不要承诺邮件已完成。

## 3. 10-15 分钟流程

### Step 1: 打开任务中心

操作：

- 打开 `http://fengxian:12959/`。
- 展示 run list、pipeline/status 筛选、右侧 run detail。

讲解：

```text
Airflow UI 不是普通用户主入口。前端统一展示 PGT-A 和 WES mock runs，用户通过 FastAPI 获取状态、日志、artifact 和 QC。
```

### Step 2: PGT-A 创建与提交入口

操作：

- 在 `Submit new analysis` 选择 PGT-A。
- 填写项目名和 `rawdata_root`。
- 点击 Scan，展示候选 R1/R2。
- 选择 target：
  - `metadata smoke` 用于轻量新建演示。
  - `baseline QC smoke` 是真实 Level 4，演示时默认只展示历史成功 run，不现场重跑。

讲解：

```text
PGT-A FASTQ 很大，页面不上传文件。后端只扫描白名单服务器路径，保存 R1/R2 路径，生成 analysis_id、workdir 和 selected manifest。创建和提交是两步，避免误触发重任务。
```

### Step 3: 展示 PGT-A metadata smoke

操作：

- 可以现场创建一个 `metadata smoke` run。
- 点击 `Submit to Airflow`。
- 通过 `Sync Airflow` 或自动同步观察状态。
- 展示 metadata log 和 artifacts。

讲解：

```text
metadata smoke 用于证明前端/API/Airflow/Snakemake 的最小闭环。它不会跑 mapping 或 baseline QC。
```

### Step 4: 展示 PGT-A Level 4 baseline_qc

操作：

- 打开历史 run `PGTA_20260706_162150_00C4FD`。
- 展示 run status 为 `success`，dag_run_id 为 `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z`。
- 展示 samples：G10/G11 workflow status 为 `success`，QC status 为 `fail`。
- 展示 artifacts：
  - `pgta_python_preflight`
  - `pgta_baseline_qc_summary`
  - `pgta_baseline_qc_pass_samples`
  - `pgta_baseline_qc_report`
  - `snakemake_command`
- 展示 QC panel：`pass=0,warn=0,fail=14,unknown=0`。

讲解：

```text
这里要区分 workflow status 和 QC decision。Airflow/Snakemake workflow 已经成功完成，baseline QC 文件也已生成并导入数据库；但当前 G10/G11 样本的 QC decision 是 FAIL，这说明数据或阈值不满足 QC，而不是平台执行失败。
```

### Step 5: 展示 Airflow 与 Snakemake 边界

操作：

- 从前端打开 Airflow link，或在 Airflow UI 搜索 `bio_pgta`。
- 展示 task graph：validate、prepare、run、collect。
- 回到前端展示 logs/artifacts/QC。

讲解：

```text
Airflow 管一次分析的项目级生命周期。Snakemake 管具体 rule、文件依赖、跳过已完成输出和 resume。前端不替代 Airflow UI，而是给实验/生信人员一个更直接的操作入口。
```

### Step 6: 展示 WES mock QC success

操作：

- 打开 `WES_20260705_164813_C5561C`。
- 展示 status 为 `success`。
- 展示 QC summary：`pass=6,warn=0,fail=0,unknown=0`。
- 展示 artifacts：`wes_final_summary`、`wes_qc_summary`。

讲解：

```text
WES mock 用轻量数据展示平台能力：qsub wrapper、rule events、QC parser、artifact discovery 和前端 QC panel。它不代表真实 WES 生产参数。
```

### Step 7: 展示 WES resume/rerun rule

操作：

- 打开 `WES_20260705_162041_2507AF`。
- 展示 rules 表中 fastp/bwa_mem/markdup/final_summary 的 success 状态和 mock qsub job id。
- 展示 command log 包含 `--forcerun fastp`，且不包含 `--forceall`。

讲解：

```text
失败或需要局部重分析时，默认不全量重跑。WES mock 的 rerun_rule 只对指定 rule 生效，保留已有 workdir 和成功输出。
```

### Step 8: 结尾与下一步

讲解：

```text
当前 demo 已完成 PGT-A 主链路、WES mock qsub/QC/resume 和前端可视化。下一步是补 MailHog success/failure 邮件通知，整理最终回滚/清理 runbook；如果需要 PGT-A QC pass 演示样本，需要先做只读数据或阈值审计，不盲目重跑 baseline_qc。
```

## 4. 已实测证据

详见 `docs/21_DEMO_SMOKE_REPORT.md`。

关键结论：

- 前端、后端、Airflow 当前在 `fengxian` 可访问。
- PGT-A `baseline_qc` workflow success，但 G10/G11 QC fail。
- WES mock QC success。
- WES mock rerun rule 使用 `--forcerun fastp`，没有 `--forceall`。

## 5. 常见问题回答

### 为什么不用 Airflow 管每个 rule？

生信 rule 和 sample 数会动态变化。Airflow 更适合稳定的项目级 orchestration，Snakemake 更适合文件依赖、rule 并行和断点续跑。

### PGT-A QC fail 是不是流程失败？

不是。`PGTA_20260706_162150_00C4FD` 的 Airflow/backend 状态是 `success`，baseline QC artifacts 已生成并导入 `/qc`。G10/G11 的 QC decision 是样本级 `FAIL`，用于提示数据或阈值问题。

### 失败后会不会全部重跑？

默认不会。Resume 使用同一 workdir 和 Snakemake 文件依赖，只重跑 incomplete/failed 部分；WES mock 的 `rerun_rule` 也明确禁止默认 `--forceall`。

### 这个能上生产吗？

当前是 demo 架构。生产化还需要权限、审计、HTTPS、secrets 管理、稳定部署、数据合规、真实队列资源策略和正式运维流程。
