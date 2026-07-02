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

## 5. 提交已创建任务到 Airflow

```http
POST /api/runs/{analysis_id}/actions/submit
```

T027/T035 阶段只支持把已存在的 PGT-A metadata run 提交到 Airflow：

- `analysis_run.pipeline_name = pgta`
- `analysis_run.status = created`
- `analysis_run.params_json.target = metadata`
- `sample_sheet_path` 和 `workdir` 必须存在

接口不会重复创建 run 或 sample。成功后会调用 Airflow REST API 触发 `bio_pgta`，写入 `dag_run_id`，并把 `analysis_run.status` 更新为 `submitted`。Airflow DAG 是否最终 success 仍以 Airflow 为准；本阶段还没有后台回写 success/failed 到 biodemo DB。

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
- `400 VALIDATION_ERROR`: pipeline 不是 `pgta`、状态不是 `created`、target 不是 `metadata`，或 run 缺少必要路径。
- `502 AIRFLOW_TRIGGER_FAILED`: backend 调用 Airflow API 失败。

## 6. 同步 Airflow 状态

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
      "message": null
    }
  ]
}
```

## 11. Snakemake event receiver

```http
POST /api/events/snakemake
```

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

- Same `analysis_id/rule/sample_id/snakemake_jobid/status` may be posted more than once.
- Backend must upsert or ignore duplicates.

## 12. QC

```http
GET /api/runs/{analysis_id}/qc
```

Response:

```json
{
  "summary": {
    "pass": 10,
    "warn": 1,
    "fail": 0
  },
  "items": [
    {
      "sample_id": "S001",
      "metric_name": "mean_depth",
      "metric_value": "128.3",
      "threshold": ">=80",
      "status": "pass"
    }
  ]
}
```

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

PGT-A v1 第一版动态发现 metadata 产物，不写 artifact 表：

- `logs/run_metadata.tsv`
- `logs/snakemake.stdout.log`
- `logs/snakemake.stderr.log`
- `config.yaml`
- `config/pgta_metadata_config.json`

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

Response:

```json
{
  "analysis_id": "WES_20260702_000001",
  "new_dag_run_id": "manual__...",
  "mode": "resume",
  "status": "submitted"
}
```
