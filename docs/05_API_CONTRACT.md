# 05 API Contract

## 1. 通用约定

Base URL:

```text
/api
```

错误格式：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "sample_sheet is missing required column sample_id",
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

## 3. 创建分析任务

```http
POST /api/runs
Content-Type: multipart/form-data
```

Fields:

```text
pipeline: wes_qsub | nipt_qsub | nipt_docker
mode: new | resume | rerun_failed | rerun_rule | clone_new
sample_sheet: file optional
form_json: stringified JSON optional
email_to: string optional
params_json: stringified JSON
```

Response:

```json
{
  "analysis_id": "WES_20260702_000001",
  "dag_id": "bio_wes_qsub",
  "dag_run_id": "manual__2026-07-02T10:00:00+00:00",
  "status": "submitted",
  "workdir": "/data/airflow-demo/runs/WES_20260702_000001"
}
```

## 4. 查询任务列表

```http
GET /api/runs?pipeline=wes_qsub&status=running&limit=50&offset=0
```

Response:

```json
{
  "items": [
    {
      "analysis_id": "WES_20260702_000001",
      "pipeline": "wes_qsub",
      "status": "running",
      "created_at": "2026-07-02T10:00:00-07:00",
      "started_at": "2026-07-02T10:01:00-07:00",
      "ended_at": null,
      "sample_count": 12,
      "qc_status": "unknown"
    }
  ],
  "total": 1
}
```

## 5. 查询任务详情

```http
GET /api/runs/{analysis_id}
```

Response:

```json
{
  "analysis_id": "WES_20260702_000001",
  "pipeline": "wes_qsub",
  "status": "running",
  "mode": "new",
  "dag_id": "bio_wes_qsub",
  "dag_run_id": "...",
  "airflow_url": "http://...",
  "workdir": "/data/airflow-demo/runs/WES_20260702_000001",
  "params": {},
  "error_summary": null
}
```

## 6. 查询样本

```http
GET /api/runs/{analysis_id}/samples
```

Response:

```json
{
  "items": [
    {
      "sample_id": "S001",
      "family_id": "F001",
      "sample_type": "proband",
      "status": "running",
      "qc_status": "unknown"
    }
  ]
}
```

## 7. 查询 Snakemake rule 状态

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

## 8. Snakemake event receiver

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

## 9. QC

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

## 10. Logs

```http
GET /api/runs/{analysis_id}/logs?rule=bwa_mem&sample_id=S001&stream=stderr&tail=200
```

Response:

```json
{
  "path": "/data/.../bwa_mem.S001.stderr.log",
  "stream": "stderr",
  "truncated": true,
  "lines": ["last line ..."]
}
```

必须防止路径穿越：backend 只能读取 `SHARED_ROOT` 内文件。

## 11. Artifacts

```http
GET /api/runs/{analysis_id}/artifacts
```

Response:

```json
{
  "items": [
    {
      "type": "multiqc_html",
      "label": "MultiQC report",
      "url": "/api/artifacts/123/view"
    }
  ]
}
```

## 12. Reanalysis

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
