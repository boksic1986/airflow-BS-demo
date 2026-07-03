# 04 数据库设计

## 1. 原则

- Airflow metadata DB 仅由 Airflow 使用。
- 业务数据存入 `biodemo` DB。
- 大文件不入库，只存路径和 artifact metadata。
- 事件表允许幂等 upsert，避免重复 POST 造成脏数据。
- 所有时间字段统一使用 timezone-aware timestamp。

## 2. ER 概念

```text
pipeline 1 -> N analysis_run
analysis_run 1 -> N sample
analysis_run 1 -> N snakemake_rule_event
analysis_run 1 -> N qc_metric
analysis_run 1 -> N artifact
analysis_run 1 -> N run_action
```

## 3. 表设计

### pipeline

| Field | Type | Notes |
|---|---|---|
| id | bigserial | primary key |
| name | text | pgta/wes_qsub/nipt_qsub/nipt_docker |
| dag_id | text | Airflow DAG id |
| version | text | pipeline version |
| runner_type | text | qsub/docker/local |
| enabled | bool | |
| created_at | timestamptz | |

### analysis_run

| Field | Type | Notes |
|---|---|---|
| id | bigserial | primary key |
| analysis_id | text unique | PGTA_YYYYMMDD_HHMMSS_<suffix> or WES_YYYYMMDD_000001 |
| pipeline_name | text | denormalized for easy query |
| dag_id | text | |
| dag_run_id | text | Airflow dag run id |
| parent_analysis_id | text nullable | reanalysis source |
| mode | text | new/resume/rerun_failed/rerun_rule/clone_new |
| status | text | created/submitted/running/success/failed/qc_warning |
| sample_sheet_path | text | generated selected manifest path, e.g. shared/runs/<analysis_id>/config/samples.selected.tsv |
| workdir | text | shared/runs/<analysis_id> |
| params_json | jsonb | sanitized params; PGT-A v1 includes rawdata_root, target, input_mode, selected_count |
| airflow_url | text nullable | UI link |
| submitted_by | text nullable | demo user |
| email_to | text nullable | |
| created_at | timestamptz | |
| started_at | timestamptz nullable | |
| ended_at | timestamptz nullable | |
| error_summary | text nullable | last error |

### sample

| Field | Type | Notes |
|---|---|---|
| id | bigserial | primary key |
| analysis_id | text index | |
| sample_id | text | |
| family_id | text nullable | |
| sample_type | text nullable | proband/father/mother/etc |
| sex | text nullable | M/F/unknown |
| fq1 | text nullable | server path to R1; do not copy FASTQ into Git/shared |
| fq2 | text nullable | server path to R2; do not copy FASTQ into Git/shared |
| metadata_json | jsonb | sanitized sample metadata; PGT-A v1 stores source_dir, file size, mtime, discovery_method |
| status | text | pending/running/success/failed |
| qc_status | text | pass/warn/fail/unknown |

### snakemake_rule_event

| Field | Type | Notes |
|---|---|---|
| id | bigserial | primary key |
| analysis_id | text index | |
| rule | text index | |
| sample_id | text nullable index | |
| wildcards_json | jsonb | |
| snakemake_jobid | text nullable | |
| qsub_jobid | text nullable | |
| status | text | planned/submitted/running/success/failed/skipped |
| stdout_path | text nullable | |
| stderr_path | text nullable | |
| message | text nullable | |
| return_code | int nullable | |
| resources_json | jsonb nullable | threads/mem/runtime |
| start_time | timestamptz nullable | |
| end_time | timestamptz nullable | |
| updated_at | timestamptz | |

推荐唯一键：

```text
unique(analysis_id, rule, sample_id, snakemake_jobid)
```

若 sample_id 为空，可使用 wildcards hash。

T026/T043 第一版已复用该表，无新增 migration：FastAPI `/api/events/snakemake` 按 `analysis_id/rule/sample_id/snakemake_jobid` 查询并 upsert；PGT-A Snakemake 9 logger 会把 rule/job 事件写入该表。qsub job id、qsub stdout/stderr 的真实填充留给后续 qsub wrapper。

### qc_metric

| Field | Type | Notes |
|---|---|---|
| id | bigserial | primary key |
| analysis_id | text index | |
| sample_id | text nullable index | |
| metric_name | text | mean_depth/mapping_rate/etc |
| metric_value | text/numeric | demo 可先 text |
| metric_numeric | numeric nullable | 用于排序/阈值 |
| threshold | text nullable | |
| status | text | pass/warn/fail/unknown |
| source_file | text nullable | |
| created_at | timestamptz | |

### artifact

| Field | Type | Notes |
|---|---|---|
| id | bigserial | primary key |
| analysis_id | text index | |
| type | text | multiqc_html/snakemake_report/final_report/qc_tsv/log |
| path | text | shared path |
| label | text | UI display |
| mime_type | text nullable | |
| size_bytes | bigint nullable | |
| created_at | timestamptz | |

### run_action

| Field | Type | Notes |
|---|---|---|
| id | bigserial | primary key |
| analysis_id | text | target run |
| action | text | submit/resume/rerun_failed/rerun_rule/cancel |
| requested_by | text nullable | |
| payload_json | jsonb | |
| created_at | timestamptz | |
| result_status | text | accepted/rejected/success/failed |
| message | text nullable | |

## 4. Alembic 约定

- migration 文件必须可重复部署。
- 禁止无确认 drop table/drop column。
- demo 初期可以允许 `alembic upgrade head`，但不允许在生产数据库上运行。
- 当前初始 migration：`backend/alembic/versions/20260702_0001_initial_biodemo_schema.py`。
- `biodemo` DB/user 由 Compose one-shot `biodemo-db-init` 创建或修正密码；schema 由 backend 容器执行 `alembic upgrade head`。

## 5. 示例状态查询

```sql
select analysis_id, pipeline_name, status, created_at, ended_at
from analysis_run
order by created_at desc
limit 20;
```

```sql
select rule, sample_id, status, qsub_jobid, stderr_path
from snakemake_rule_event
where analysis_id = :analysis_id
order by start_time nulls last, rule;
```
