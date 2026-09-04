# 04 数据库设计

## T195/T200 WGS contract-v2 evidence

Migration `20260904_0014` adds two append-only/read-model tables without
changing historical runs:

- `wgs_stage_execution`: immutable execution identity, attempt, stage,
  generation, request hash, release, predecessor receipt, heartbeat, terminal
  evidence, receipt hash, and timestamps. Its unique key is
  `analysis_id + attempt + stage_code + generation`.
- `transfer_file_state`: privacy-safe file key/display name, frozen size,
  completed bytes, speed, checksum state, bounded error, and timestamps for one
  transfer.

`run_stage_state` remains the current projection. It is not retry history and
cannot authorize a downstream contract-v2 stage.

## T188 bounded resource history and WGS projections（无迁移）

本轮不新增表或字段。`platform_resource_snapshot.history_json`仍按资源单行
upsert，但节点和OBS最多保留60点，SFS最多保留10080点，以支持约7天的一分钟
采集历史。WGS样本清单、分析矩阵、受控文件和日志均在API读取时投影；原始
`sampleinfo.tsv`和临床隐私字段不复制到数据库。

## T154-T157 WGS生产投影

迁移`20260901_0013`新增`run_stage_state`（每analysis/attempt/stage一行）、
`wgs_submission_draft`（私有且可过期的提交草稿）和
`platform_resource_snapshot`（每资源一行、最多60点JSON环）。`rule_state`
增加sequence、phase、job、样本/家系、wildcards和日志索引字段。既有QC数据保留，
但WGS前端不再消费。

## T151 YF exclusion fingerprint（无迁移）

T151不增加数据库字段。现有fingerprint值升级为v3并排除`YF*`非临检样本名称；
运行时可识别等价的旧v2摘要并原位升级，避免把策略变化误报为输入漂移。YF不计入
eligible、add-on或pair issue，数据库不单独保存YF数量。

## T150 name-level intake fingerprint（无迁移）

T150不增加字段、不运行Alembic或手工改表。`wgs_intake_batch`现有
`eligible_fingerprint/observed_fingerprint`保存名称级v2摘要；旧v1摘要通过
运行时兼容比较升级。只有`ready`冻结输入名称，历史`no_new_wgs`允许按后续出现的
WGS名称转为`ready/needs_review`。FASTQ目标、大小、mtime和MD5不进入scanner
fingerprint；完整性由后续prepare/上传合同负责。

## T145 migration 0012

`wgs_intake_scanner_state`只保存`first_scan_at`、`last_scan_at`、
`last_scanned_directory_count`、`last_error`。`observer_run_state`将健康度与
`active|draining|stopped`生命周期分离。历史 intake 明细通过有备份和关联
保护的部署 CLI 清理，不混入 Alembic。见[doc 27](27_WGS_SCANNER_OBSERVER_LIFECYCLE.md)。

## T143/T144 migration 0011

Alembic `20260829_0011`扩展`wgs_intake_batch`为可独立于 AnalysisRun 的芯片发现
表，并新增单例`wgs_intake_scanner_state`和幂等`wgs_maintenance_action`。intake
公开投影不得泄露 sample ID、源路径或 fingerprint；nullable `analysis_id`外键用
`ON DELETE SET NULL`保留扫描证据。字段、状态和唯一键见[文档 26](26_WGS_T7_INTAKE_STEP4_REPAIR.md)。

## T142 WGS release identity migration

Alembic `20260827_0010`非破坏性地将
`observer_run_state.pipeline_snapshot_id`重命名为`pipeline_release_id`，并将
残留 WGS `analysis_run.params_json`中的 snapshot/source 字段迁移为
`pipeline_release_id`和`wgs_source_commit`。用户、角色、平台配置及运行大表均
不删除。prepare 后的 cce-pipeline/profile/Master identity 写入
`analysis_run.params_json.resolved_runtime`作为审计信息；Rule 状态、observer
binding 和 ETA 历史按 release ID 隔离。

> **WGS 说明：** biodemo 已迁移到 WGS 4.1.1 revision `20260826_0009`，
> 当前合同依据
> [`25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md`](25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md)
> 和代码模型；以下 T133 projection 仅作历史参考。

## T133 WGS 4.1.0 projection note

No destructive database migration is introduced by T133. Existing
`rule_event_raw`, `rule_state`, `evidence_cursor`, `observer_run_state`,
`kubernetes_workload`, `transfer_job`, `wgs_input_snapshot`, validation issue
and OBS lease tables are reused. `rule_event_raw.payload_json` stores the full
`rule-event.v1` record; `event_id` remains the idempotency key. Observer health
uses the existing status/error columns. Kubernetes rows are now admitted only
for the batch Master Job/Pod. The historical `master_slot` table may remain in
an upgraded database for compatibility but the current code and DAG do not
allocate it; concurrency is controlled by the Airflow pool and CCE quota.

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
| submitted_at | timestamptz nullable | immutable backend-to-Airflow handoff time; created-only runs remain null |
| started_at | timestamptz nullable | latest Airflow DAG run start; task clear/retry may change it |
| ended_at | timestamptz nullable | latest Airflow DAG run end; task clear/retry may change it |
| pipeline_finished_at | timestamptz nullable | first successful terminal pipeline event; immutable once set |
| error_summary | text nullable | last error |

T114 migration `20260711_0004` adds `pipeline_finished_at`. PGT-A predict uses
the project-level `cnv_predict=success` event; NIPT full analysis uses the first
parent `all=success` event. Retry or Airflow task clear must not overwrite this
timestamp. Dashboard runtime is `submitted_at -> pipeline_finished_at` for
terminal runs and `submitted_at -> now` for active runs.

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
| status | text | pending/running/success/failed; created runs start pending, submit/reanalyze marks selected samples running, explicit Airflow sync marks them success/failed/running with the run |
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

## T119 Intake lifecycle fields

`intake_discovery` keeps completed discovery records as an idempotency audit
instead of deleting them. Migration `20260713_0005` adds:

| Field | Type | Meaning |
|---|---|---|
| `state_changed_at` | timestamptz, not null | Last lifecycle transition; backfilled from `last_seen_at`/`first_seen_at` |
| `archived_at` | timestamptz, nullable | Workflow completion time used to leave the active scanner view |
| `archive_reason` | varchar(128), nullable | `workflow_success` or an actionable `archive_error` |
| `archive_path` | text, nullable | PGT-A archived request directory or immutable NIPT source batch path |

Archived rows retain request ID, fingerprint, analysis linkage, and source
audit fields. They are never re-created or re-submitted by scheduled scanning.
NIPT FASTQ directories are not moved; PGT-A manifest and READY files are moved
atomically to the configured inbox `.archive/YYYY/MM/<request_id>` directory.

### intake_discovery

T103 intake scanner state for PGT-A and NIPT Docker batch discovery. This table
prevents repeated auto-submission of the same stable batch fingerprint.

| Field | Type | Notes |
|---|---|---|
| id | bigserial | primary key |
| pipeline_name | text | `pgta` or `nipt_docker` |
| root_path | text | scanned allowlisted root |
| batch_id | text | relative folder id under root |
| fingerprint | text | hash of selected paths, sizes, and mtimes |
| file_count | int | paired FASTQ count times two |
| total_bytes | bigint | summed selected FASTQ bytes |
| max_mtime | timestamptz nullable | latest input mtime |
| ready_state | text | observed/ready |
| analysis_id | text nullable | created run when submitted |
| submit_state | text | not_submitted/bootstrap/created/submitted |
| first_seen_at | timestamptz | |
| last_seen_at | timestamptz | |

Constraints and indexes:

```text
unique(pipeline_name, root_path, batch_id)
index(pipeline_name, ready_state, submit_state)
index(analysis_id)
```

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

## T112 PGT-A S9 operational fields

Migration `20260711_0003` adds `analysis_run.submitted_at`,
`progress_percent`, `current_stage`, and `progress_updated_at`. Created-only
runs keep `submitted_at` null; historical values are backfilled from the first
accepted submit RunAction. Intake discovery adds `source_manifest_path`,
`last_error`, and `stable_observation_count` for READY-manifest audit.
## 2026-08-12 WGS-only extension

Migration `20260812_0006` adds WGS execution mode and attempt tracking plus account, session, audit, transfer, rule, Pod, and four master-slot tables in biodemo. Airflow metadata remains a separate database.

Migration `20260812_0007` adds observer-owned durable state to `biodemo`:

- `evidence_cursor` stores one byte/line cursor per `analysis_id + attempt + relative_path`; observer restarts resume only after the last committed complete JSONL record.
- `observer_run_state` binds one analysis attempt to its immutable pipeline snapshot, run label, and relative evidence directory.
- `kubernetes_workload` additionally stores Kubernetes `resource_version`, observation time, node, message, and raw Job status summary.

Evidence paths are always relative to the configured read-only evidence root. Neither table stores kubeconfig, OBS credentials, or unrestricted host paths.
# T131: WGS input snapshots, validation issues, singleton OBS lease, and full
# transfer progress were added by Alembic `20260812_0008`. Rule timing remains
# derived from `rule_state.started_at/ended_at/layer`.
