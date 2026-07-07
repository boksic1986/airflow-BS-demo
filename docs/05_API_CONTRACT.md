# 05 API Contract

## 1. 通用约定

Base URL:

```text
/api
```

错误格式：

```json
{
  "detail": {
    "code": "VALIDATION_ERROR",
    "message": "rawdata_root is outside allowed input roots",
    "details": {}
  }
}
```

## 2. Health

```http
GET /api/health
```

Response:

```json
{
  "status": "ok"
}
```

```http
GET /api/health/db
```

Response:

```json
{
  "status": "ok"
}
```

该接口只验证 biodemo DB 连接，不返回连接串、密码或库内数据。

```http
GET /api/health/airflow
```

Response:

```json
{
  "status": "ok",
  "airflow": {
    "metadatabase": {"status": "healthy"},
    "scheduler": {"status": "healthy"}
  }
}
```

该接口通过 backend 的 `AirflowClient` 访问 Airflow `/health`；第一阶段使用 `.env` 中的 `AIRFLOW_API_USERNAME` / `AIRFLOW_API_PASSWORD`。

## 3. 服务器路径样本发现

```http
POST /api/input/scan
Content-Type: application/json
```

第一版只支持 `pipeline=pgta`。接口不上传 FASTQ，不复制 FASTQ，只扫描 `.env` 中 `INPUT_SCAN_ROOTS` 白名单下的服务器路径并返回可勾选的 R1/R2 候选样本。若候选过多，返回 `truncated=true`，前端要求用户缩小 `rawdata_root`。

Request:

```json
{
  "pipeline": "pgta",
  "rawdata_root": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28",
  "max_samples": 200
}
```

Response:

```json
{
  "pipeline": "pgta",
  "rawdata_root": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28",
  "truncated": false,
  "items": [
    {
      "sample_id": "G1",
      "r1": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R1.fastq.gz",
      "r2": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R2.fastq.gz",
      "source_dir": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28/Sample_DEMO-G1-G1",
      "r1_size": 123456,
      "r2_size": 123450,
      "r1_mtime": 1782810000.0,
      "r2_mtime": 1782810001.0,
      "discovery_method": "server_path_scan"
    }
  ]
}
```

## 4. 创建分析任务

```http
POST /api/runs
Content-Type: application/json
```

创建接口只创建项目、入库和 selected manifest，不触发 Airflow，不运行 Snakemake。`dag_run_id` 必须为 `null`，状态为 `created`。提交到 Airflow 使用后续的 submit action。

PGT-A v1 受控 target：

- `metadata`: 真实执行轻量 metadata target。
- `dryrun_cnv`: 只运行 CNV 配置方向的 Snakemake dry-run。
- `invalid_target`: failure smoke 专用，后续提交到 Airflow 时让 Snakemake 自然失败以验证 stderr/error summary。
- `baseline_qc`: Level 4 staged real target，生成 `pipeline.mode=build_ref`、`pipeline.targets=["mapping","metadata","baseline_qc"]` 的 run-local config。该 target 至少需要 2 个 selected samples，会真实执行 mapping 和 baseline QC；只允许在用户确认的最小样本 smoke 中运行。

Request:

```json
{
  "pipeline": "pgta",
  "project_name": "PGT-A metadata smoke",
  "target": "metadata",
  "rawdata_root": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28",
  "selected_samples": [
    {
      "sample_id": "G1",
      "r1": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R1.fastq.gz",
      "r2": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R2.fastq.gz",
      "source_dir": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28/Sample_DEMO-G1-G1",
      "r1_size": 123456,
      "r2_size": 123450,
      "r1_mtime": 1782810000.0,
      "r2_mtime": 1782810001.0
    }
  ],
  "email_to": "demo@example.com",
  "note": "create only; no DAG trigger"
}
```

Response:

```json
{
  "analysis_id": "PGTA_20260702_120000_A1B2C3",
  "pipeline": "pgta",
  "dag_id": "bio_pgta",
  "dag_run_id": null,
  "status": "created",
  "workdir": "/data/airflow-demo/runs/PGTA_20260702_120000_A1B2C3",
  "sample_count": 1
}
```

生成文件：

```text
shared/runs/<analysis_id>/config/samples.selected.tsv
shared/runs/<analysis_id>/config/request.json
```

WES mock v1 也使用同一 JSON endpoint，但不上传/扫描真实 WES 数据；后端固定创建 mock samples `S001/S002`，只支持 `target=final_summary`。

Request:

```json
{
  "pipeline": "wes_qsub",
  "project_name": "WES mock smoke",
  "target": "final_summary",
  "email_to": null,
  "note": "mock WES only"
}
```

Response:

```json
{
  "analysis_id": "WES_20260705_162041_2507AF",
  "pipeline": "wes_qsub",
  "dag_id": "bio_wes_qsub",
  "dag_run_id": null,
  "status": "created",
  "workdir": "/data/airflow-demo/runs/WES_20260705_162041_2507AF",
  "sample_count": 2
}
```

## 5. 提交已创建任务到 Airflow

```http
POST /api/runs/{analysis_id}/actions/submit
```

T045/T084 阶段支持把已存在的 PGT-A controlled target run 提交到 Airflow；T044/T056 后也支持把 `wes_qsub` created run 提交到 `bio_wes_qsub`。

- `analysis_run.pipeline_name = pgta`
- `analysis_run.status = created`
- `analysis_run.params_json.target` 为 `metadata`、`dryrun_cnv`、`invalid_target` 或 `baseline_qc`
- `baseline_qc` 要求 `selected_count >= 2`
- `sample_sheet_path` 和 `workdir` 必须存在

WES submit 要求：

- `analysis_run.pipeline_name = wes_qsub`
- `analysis_run.status = created`
- `analysis_run.params_json.target = final_summary`
- DAG run conf 包含 `backend_event_url=http://backend:8000/api/events/snakemake`

接口不会重复创建 run 或 sample。成功后会调用 Airflow REST API 触发 `bio_pgta`，写入 `dag_run_id`，并把 `analysis_run.status` 更新为 `submitted`；该 run 下的 `sample.status` 会从 `pending` 更新为 `running`。Airflow DAG 是否最终 success/failed 仍以 Airflow 为准；需要显式调用 `sync-airflow` 回写 biodemo DB。

Response:

```json
{
  "analysis_id": "PGTA_20260702_171533_9A85B1",
  "pipeline": "pgta",
  "dag_id": "bio_pgta",
  "dag_run_id": "manual__PGTA_20260702_171533_9A85B1",
  "status": "submitted",
  "workdir": "/data/airflow-demo/runs/PGTA_20260702_171533_9A85B1",
  "sample_count": 1,
  "mode": "new",
  "sample_sheet_path": "/data/airflow-demo/runs/PGTA_20260702_171533_9A85B1/config/samples.selected.tsv",
  "params": {
    "rawdata_root": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28",
    "target": "metadata",
    "input_mode": "server_path_scan",
    "selected_count": 1
  },
  "airflow_url": null,
  "error_summary": null,
  "email_to": null
}
```

Errors:

- `404 RUN_NOT_FOUND`: `analysis_id` 不存在。
- `400 VALIDATION_ERROR`: pipeline 不是 `pgta/wes_qsub`、状态不是 `created`、target 不在受控白名单内，或 run 缺少必要路径。
- `400 VALIDATION_ERROR`: `baseline_qc` selected samples 少于 2 个。
- `502 AIRFLOW_TRIGGER_FAILED`: backend 调用 Airflow API 失败。

## 6. 同步 Airflow 状态

Sample status sync rule:
- `POST /api/runs/{analysis_id}/actions/submit` sets selected `sample.status` from `pending` to `running`.
- `POST /api/runs/{analysis_id}/actions/reanalyze` sets WES mock and allowed PGT-A resume samples to `running`.
- `sync-airflow` maps Airflow terminal state back to samples: `success -> success`, `failed -> failed`; active states `running/queued/scheduled` display as `running`.

```http
POST /api/runs/{analysis_id}/actions/sync-airflow
```

显式同步 Airflow DAG run 状态到 biodemo DB。读接口不会隐式修改 DB。

行为：

- 要求 run 已有 `dag_id` 和 `dag_run_id`。
- 调用 Airflow REST API 查询 DAG run。
- Airflow `success` / `failed` / `running` / `queued` 映射回 `analysis_run.status`。
- `success` / `failed` 写入 `ended_at`。
- `failed` 时从 `workdir/logs/snakemake.stderr.log` 提取最后 100 行，写入 `analysis_run.error_summary`。
- `wes_qsub` 在 Airflow `success` 时解析 `workdir/reports/qc_summary.tsv`，幂等刷新 `qc_metric`，并更新 `sample.qc_status`。
- `pgta` 且 `target=baseline_qc` 在 Airflow `success` 时解析 `workdir/qc/baseline/baseline_qc_summary.tsv`，导入 `baseline_qc_decision`、`mapped_fragments`、`zero_bin_fraction`、`bin_cv`、`pearson_r`、`median_abs_z`、`gc_signal_slope` 等样本级指标。

Response:

```json
{
  "analysis_id": "PGTA_20260702_171533_9A85B1",
  "pipeline": "pgta",
  "dag_id": "bio_pgta",
  "dag_run_id": "manual__PGTA_20260702_171533_9A85B1",
  "status": "success",
  "workdir": "/data/airflow-demo/runs/PGTA_20260702_171533_9A85B1",
  "mode": "new",
  "error_summary": null,
  "started_at": "2026-07-02T17:15:34.472812+00:00",
  "ended_at": "2026-07-02T17:15:44.620014+00:00"
}
```

Errors:

- `404 RUN_NOT_FOUND`: `analysis_id` 不存在。
- `400 MISSING_DAG_RUN`: run 没有 `dag_id` 或 `dag_run_id`。
- `400 INVALID_RUN_PATH`: run workdir 不在 shared root 内。
- `502 AIRFLOW_SYNC_FAILED`: backend 调用 Airflow API 失败。

## 7. 查询任务列表

```http
GET /api/runs?pipeline=pgta&status=created&limit=50&offset=0
```

Response:

```json
{
  "items": [
    {
      "analysis_id": "PGTA_20260702_120000_A1B2C3",
      "pipeline": "pgta",
      "status": "created",
      "created_at": "2026-07-02T12:00:00+00:00",
      "started_at": null,
      "ended_at": null,
      "sample_count": 1,
      "qc_status": "unknown"
    }
  ],
  "total": 1
}
```

## 8. 查询任务详情

```http
GET /api/runs/{analysis_id}
```

Response:

```json
{
  "analysis_id": "PGTA_20260702_120000_A1B2C3",
  "pipeline": "pgta",
  "status": "created",
  "mode": "new",
  "dag_id": "bio_pgta",
  "dag_run_id": null,
  "airflow_url": null,
  "workdir": "/data/airflow-demo/runs/PGTA_20260702_120000_A1B2C3",
  "sample_sheet_path": "/data/airflow-demo/runs/PGTA_20260702_120000_A1B2C3/config/samples.selected.tsv",
  "params": {
    "rawdata_root": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28",
    "target": "metadata",
    "input_mode": "server_path_scan",
    "selected_count": 1
  },
  "error_summary": null,
  "email_to": "demo@example.com"
}
```

## 9. 查询样本

```http
GET /api/runs/{analysis_id}/samples
```

Response:

```json
{
  "items": [
    {
      "sample_id": "G1",
      "family_id": null,
      "sample_type": null,
      "sex": null,
      "fq1": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R1.fastq.gz",
      "fq2": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28/Sample_DEMO-G1-G1/DEMO-G1-G1_combined_R2.fastq.gz",
      "status": "pending",
      "qc_status": "unknown",
      "metadata": {
        "source_dir": "/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28/Sample_DEMO-G1-G1",
        "discovery_method": "server_path_scan"
      }
    }
  ]
}
```

## 10. 查询 Snakemake rule 状态

```http
GET /api/runs/{analysis_id}/rules
```

返回 biodemo `snakemake_rule_event` 中当前 run 的 rule/job 最新状态。T026/T043 第一版由 PGT-A Snakemake 9 logger 或后续 qsub wrapper 写入；读接口不触发 Airflow 状态同步。

Response:

```json
{
  "items": [
    {
      "rule": "bwa_mem",
      "sample_id": "S001",
      "status": "running",
      "snakemake_jobid": "12",
      "qsub_jobid": "123456",
      "stdout_path": "...",
      "stderr_path": "...",
      "start_time": "2026-07-02T10:12:00-07:00",
      "end_time": null,
      "message": null,
      "return_code": null,
      "wildcards": {"sample": "S001"}
    }
  ]
}
```

Errors:

- `404 RUN_NOT_FOUND`: `analysis_id` 不存在。

## 11. Snakemake event receiver

```http
POST /api/events/snakemake
```

接收 Snakemake/qsub rule/job 级事件并幂等 upsert 到 `snakemake_rule_event`。第一版要求 `rule` 非空；workflow/progress/generic log 仍保留在 JSONL/Airflow XCom 中，不写 DB。

Request:

```json
{
  "analysis_id": "WES_20260702_000001",
  "event": "job_started",
  "rule": "bwa_mem",
  "sample_id": "S001",
  "wildcards": {"sample": "S001"},
  "snakemake_jobid": "12",
  "qsub_jobid": "123456",
  "status": "running",
  "stdout_path": "/data/.../bwa_mem.S001.o",
  "stderr_path": "/data/.../bwa_mem.S001.e",
  "message": null,
  "return_code": null,
  "timestamp": "2026-07-02T10:12:00-07:00"
}
```

Response:

```json
{"status": "ok"}
```

Idempotency:

- Upsert key: `analysis_id/rule/sample_id/snakemake_jobid`。
- 同一 job 的 `job_info/running/success/failed` 会更新同一行的 `status/message/return_code/start_time/end_time/updated_at`。

Errors:

- `404 RUN_NOT_FOUND`: `analysis_id` 不存在。
- `422 VALIDATION_ERROR`: `rule`、`analysis_id`、`event` 或 `status` 缺失。

## 12. QC

```http
GET /api/runs/{analysis_id}/qc
```

T060/T054 v1 已支持 WES mock QC 查询；T087 v1 补充 PGT-A `baseline_qc` summary 查询。QC 导入只发生在显式调用 `sync-airflow` 且 DAG run 为 `success` 时；普通 GET 不修改 DB。

Response:

```json
{
  "summary": {
    "pass": 6,
    "warn": 0,
    "fail": 0,
    "unknown": 0
  },
  "items": [
    {
      "sample_id": "S001",
      "metric_name": "mock_mean_depth",
      "metric_value": "100",
      "metric_numeric": 100.0,
      "threshold": ">=80",
      "status": "pass",
      "source_file": "/data/airflow-demo/runs/WES_20260705_164813_C5561C/reports/qc_summary.tsv"
    }
  ]
}
```

Errors:

- `404 RUN_NOT_FOUND`: `analysis_id` 不存在。

## 13. Logs

```http
GET /api/runs/{analysis_id}/logs?stream=stderr&tail=200
```

PGT-A v1 第一版固定支持 `stream=stdout|stderr|metadata`：

- `stdout`: `workdir/logs/snakemake.stdout.log`
- `stderr`: `workdir/logs/snakemake.stderr.log`
- `metadata`: `workdir/logs/run_metadata.tsv`

`tail` 范围是 `1..1000`，默认 `200`。backend 只读取 `CONTAINER_SHARED_ROOT` 内、且位于该 run `workdir` 内的文件。

Response:

```json
{
  "path": "/data/airflow-demo/runs/PGTA_20260702_171533_9A85B1/logs/snakemake.stderr.log",
  "stream": "stderr",
  "truncated": true,
  "lines": ["last stderr line ..."]
}
```

Errors:

- `404 RUN_NOT_FOUND`: `analysis_id` 不存在。
- `404 LOG_NOT_FOUND`: 对应日志文件不存在。
- `400 INVALID_RUN_PATH`: run workdir 或日志路径越过 shared/workdir 安全边界。

## 14. Artifacts

```http
GET /api/runs/{analysis_id}/artifacts
```

PGT-A v1 第一版动态发现 metadata/dry-run/baseline QC 产物，不写 artifact 表：

- `logs/run_metadata.tsv`
- `logs/snakemake.command.txt`
- `logs/pgta.resume.cleanup.tsv`
- `logs/snakemake.stdout.log`
- `logs/snakemake.stderr.log`
- `config.yaml`
- `config/pgta_run_config.json`
- `config/pgta_metadata_config.json`
- `qc/baseline/baseline_qc_summary.tsv`
- `qc/baseline/baseline_qc_pass_samples.txt`
- `qc/baseline/baseline_qc_report.md`

WES mock v1 也动态发现：

- `reports/final_summary.tsv`
- `reports/qc_summary.tsv`
- `logs/snakemake.command.txt`
- `logs/snakemake.stdout.log`
- `logs/snakemake.stderr.log`
- `logs/events/snakemake_events.jsonl`
- `config/wes_mock_config.yaml`

Response:

```json
{
  "items": [
    {
      "key": "run_metadata",
      "type": "pgta_metadata",
      "label": "PGT-A run metadata",
      "path": "/data/airflow-demo/runs/PGTA_20260702_171533_9A85B1/logs/run_metadata.tsv",
      "size_bytes": 1956,
      "url": "/api/runs/PGTA_20260702_171533_9A85B1/logs?stream=metadata"
    }
  ]
}
```

## 15. Reanalysis

```http
POST /api/runs/{analysis_id}/actions/reanalyze
```

Request:

```json
{
  "mode": "resume",
  "rule": null,
  "sample_id": null,
  "reason": "resume failed run after fixing input path"
}
```

WES mock v1 支持：

- `resume`: 复用同一 `analysis_id/workdir`，提交新的 `bio_wes_qsub` DAG run，Snakemake 依赖已有输出和 `rerun-incomplete` 跳过成功步骤。
- `rerun_rule`: 复用同一 `analysis_id/workdir`，只允许 `fastp`、`bwa_mem`、`markdup`、`final_summary`；样本级 rule 要求 `sample_id=S001/S002`。

PGT-A v1 支持：

- `resume`: only for `pipeline=pgta`, `target=baseline_qc`, and a terminal interrupted/failed run. It reuses the same `analysis_id/workdir`, submits a new `bio_pgta` DAG run with `mode=resume`, and lets Snakemake skip completed outputs with `--rerun-incomplete`.
- PGT-A resume is rejected while the run is active (`submitted/running/queued/scheduled`), for non-`baseline_qc` targets, for `rerun_rule`, `clone_new`, `forceall`, or any explicit rule/sample selector.
- Resume updates `analysis_run.dag_run_id`, sets `analysis_run.status=submitted`, sets existing samples to `running`, and records a `run_action` row.

Response:

```json
{
  "analysis_id": "WES_20260702_000001",
  "new_dag_run_id": "manual__...",
  "mode": "resume",
  "status": "submitted"
}
```

禁止：

- `forceall`
- `clone_new`
- 真实 qsub
- 不在 allowlist 内的 WES rule/sample。
