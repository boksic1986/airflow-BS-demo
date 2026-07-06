# 06 前端设计

## 0. Current T050/T051/T054/T056/T057 v1

第一版前端已经从 nginx placeholder 替换为 Vite React + TypeScript app，由 Docker nginx 镜像服务静态文件，宿主机端口保持 `12959`。

已实现范围：

- 首页即 analysis submit/list/detail workspace，当前可展示 `pgta` 和 `wes_qsub`。
- 主内容顶部 `Submit new analysis` 工作区包含 `New PGT-A Run` 和 `New WES Mock Run`；左侧只保留 run list，避免提交表单被挤在窄侧栏。
- `New PGT-A Run` 面板支持 `project_name`、`rawdata_root`、`max_samples`、`target` 下拉、可选 `email_to` 和备注；target 下拉使用可读标签：metadata smoke、CNV dry-run、failure smoke、baseline QC smoke。
- `Scan` 调用 `POST /api/input/scan`，展示服务器路径 FASTQ 候选样本，支持勾选样本；`truncated=true` 时显示收窄路径提示。
- 未勾选样本时 `Create Run` 禁用，并显示 `Select at least one scanned sample to enable Create Run.` 提示；`baseline_qc` 少于 2 个样本时继续禁用，并显示 `Baseline QC smoke requires at least 2 selected samples.`。
- `Create Run` 调用 JSON `POST /api/runs`，创建成功后自动选中新 run 并展示 detail。
- 对 `status=created` 且 `target` 为 `metadata`、`dryrun_cnv`、`invalid_target` 或 `baseline_qc` 的 run，detail toolbar 显示 `Submit to Airflow`，调用 `POST /api/runs/{analysis_id}/actions/submit`。
- 左侧 `New WES Mock Run` 面板可一键创建 `pipeline=wes_qsub,target=final_summary` run 并提交到 `bio_wes_qsub`。
- `GET /api/runs?limit=50&offset=0` 展示 run 列表。
- run detail 展示 overview、samples、Snakemake rules、metadata/stdout/stderr logs、artifacts。
- WES mock run detail 展示 QC panel：pass/warn/fail/unknown summary 和样本级 mock QC 指标表。
- 手动同步按钮调用 `POST /api/runs/{analysis_id}/actions/sync-airflow`。
- 对已有 `wes_qsub` DAG run，detail toolbar 显示 `Resume` 和 `Rerun rule` 控件；`Rerun rule` 支持 `fastp/bwa_mem/markdup/final_summary`，样本级 rule 可选 `S001/S002`。
- API base 默认按浏览器当前 host 推导为 `http://<host>:8000/api`，可通过 `window.__AIRFLOW_DEMO_CONFIG__.apiBaseUrl` 或 `VITE_API_BASE_URL` 覆盖。

未实现范围：

- 登录系统。
- 独立日志查看页、MultiQC iframe/report viewer。
- 自定义 Airflow Web 插件或 Airflow task log API 抓取。

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
PGT-A: created/running/success/failed
WES qsub: running/success/failed
NIPT qsub: running/success/failed
NIPT docker: running/success/failed
```

## 3. Submit 页面

字段：

```text
Pipeline:
  - PGT-A
  - WES qsub
  - NIPT qsub
  - NIPT docker
Input mode:
  - server path scan
PGT-A v1 fields:
  - project_name
  - rawdata_root
  - scan button
  - candidate sample checkbox table
  - target: metadata / dryrun_cnv / invalid_target / baseline_qc
  - email_to
  - note
Params:
  - genome
  - queue
  - max_jobs
  - email_to
  - analysis_mode
```

PGT-A v1 不上传 FASTQ 或 sample sheet。前端调用 `POST /api/input/scan` 扫描白名单服务器路径下已有 FASTQ，用户勾选样本后用 JSON 调用 `POST /api/runs`。提交成功后状态为 `created`，不会立即出现 Airflow DAG run。

T051/T045 v1 已在当前单页 workspace 中实现该表单，不引入路由库。T051 usability fix 后，表单位于主内容顶部的 `Submit new analysis` 区域，candidate table 使用主内容宽度，run list 不再混入创建表单。创建 run 和提交执行保持两步模式：创建后先进入 `created`，用户在 run detail toolbar 点击 `Submit to Airflow` 后才触发 `bio_pgta`。默认 target 是 `metadata`；`dryrun_cnv` 用于 Snakemake dry-run smoke，`invalid_target` 仅用于失败摘要 smoke，`baseline_qc` 是 Level 4 staged real smoke，要求至少 2 个 selected samples。

WES mock v1 不上传或扫描数据。前端 `New WES Mock Run` 直接调用 JSON `POST /api/runs` 创建固定 `S001/S002` mock run，然后调用 `POST /api/runs/{analysis_id}/actions/submit` 提交 `bio_wes_qsub`。

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

- T054 v1 已实现 WES mock QC panel，调用 `GET /api/runs/{analysis_id}/qc`；T087 v1 复用同一 panel 展示 PGT-A `baseline_qc` summary 导入后的样本级指标。
- QC summary：pass/warn/fail/unknown。
- Sample QC table：sample_id、metric_name、metric_value、threshold、status。
- 没有 QC 时显示空状态，不影响 rules/logs/artifacts。
- MultiQC report link/iframe 和 Snakemake report link 留给 T061/T063 后续。

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

T056 v1 已完成 WES mock 最小入口：

- `Resume` 调用 `POST /api/runs/{analysis_id}/actions/reanalyze`，payload `{"mode":"resume"}`。
- `Rerun rule` 调用同一 endpoint，payload `{"mode":"rerun_rule","rule":"fastp","sample_id":"S001"}`。
- `clone_new`、`rerun_failed` 和 PGT-A 重分析仍后置。

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
