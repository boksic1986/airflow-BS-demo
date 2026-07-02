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

T022/T024 阶段只创建项目、入库和 selected manifest，不触发 Airflow，不运行 Snakemake。`dag_run_id` 必须为 `null`，状态为 `created`。Airflow trigger 留到 T027/T035 后实现。

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

## 5. 查询任务列表

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

## 6. 查询任务详情

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

## 7. 查询样本

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

## 8. 查询 Snakemake rule 状态

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

## 9. Snakemake event receiver

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

## 10. QC

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

## 11. Logs

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

## 12. Artifacts

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

## 13. Reanalysis

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
