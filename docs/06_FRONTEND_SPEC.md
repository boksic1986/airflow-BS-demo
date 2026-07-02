# 06 前端设计

## 1. 页面结构

```text
/dashboard
/runs
/runs/:analysis_id
/submit
/settings/demo
```

## 2. Dashboard

展示卡片：

- Today submitted。
- Running。
- Failed。
- QC warning。
- qsub running jobs。
- Airflow health。

Pipeline cards：

```text
WES qsub: running/success/failed
NIPT qsub: running/success/failed
NIPT docker: running/success/failed
```

## 3. Submit 页面

字段：

```text
Pipeline:
  - WES qsub
  - NIPT qsub
  - NIPT docker
Input mode:
  - upload sample sheet
  - manual form
Sample sheet:
  - csv/tsv/xlsx
Params:
  - genome
  - queue
  - max_jobs
  - email_to
  - analysis_mode
```

提交后跳转：

```text
/runs/<analysis_id>
```

## 4. Runs 列表

列：

```text
analysis_id
pipeline
status
samples
qc
created_at
runtime
actions
```

Actions：

```text
View
Resume
Clone
```

## 5. Run Detail Tabs

### Overview

- analysis_id。
- pipeline。
- mode。
- status。
- sample count。
- workdir。
- submit time/start/end/runtime。
- Airflow link。
- error summary。

### Airflow

- DAG run id。
- Task list。
- Task status。
- Link to Airflow UI。

### Snakemake

组件：

- Rule status summary。
- Rule table。
- Per sample progress。
- qsub job id。
- stdout/stderr button。

Rule table columns：

```text
rule
sample_id
status
snakemake_jobid
qsub_jobid
runtime
log actions
```

### QC

- QC summary：pass/warn/fail。
- Sample QC table。
- MultiQC report link/iframe。
- Snakemake report link。

### Logs

- stream selector：Airflow/Snakemake/rule/qsub。
- rule selector。
- sample selector。
- stdout/stderr selector。
- tail lines selector。
- refresh button。

### Reanalysis

- Resume failed run。
- Rerun failed/incomplete。
- Rerun selected rule/sample。
- Clone as new analysis。

必须显示提示：

```text
Resume 会复用当前 workdir，不默认重新分析已成功输出。
Clone 会创建新 analysis_id 和新 workdir。
```

## 6. 状态颜色

| Status | Color semantic |
|---|---|
| success/pass | green |
| running/submitted | blue |
| failed/fail | red |
| warn/qc_warning | orange |
| skipped/cached | gray |
| unknown | neutral |

具体颜色由 UI 框架实现，不写死在业务逻辑。

## 7. 前端容错

- API 失败时显示错误 message，不吞掉。
- 日志文件不存在时显示“尚未生成或路径不可访问”。
- 长日志默认只显示 tail。
- 刷新状态使用 polling；后续可升级 SSE/WebSocket。

## 8. Demo 优先级

MVP 必须完成：

1. Submit。
2. Runs list。
3. Run detail overview。
4. Snakemake rule table。
5. Log viewer。
6. QC table。
7. Resume button。

可后置：

- fancy rule graph。
- auth。
- dark mode。
- WebSocket 实时推送。
