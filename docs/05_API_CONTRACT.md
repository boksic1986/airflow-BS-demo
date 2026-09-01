# 05 API Contract

## T149 Step3 internal status and recovery contract

The public API and database schema are unchanged. The internal
`GET /api/internal/wgs/runs/{analysis_id}/stage-status` endpoint accepts an
`accepted` or an early `running` Step3 status without Master details as a valid
transition: it returns HTTP 200 with `ready=false` and does not create a
Kubernetes workload. A terminal Step3 success must include Master evidence.

Once Master details are present, the backend reads the immutable
`runs/<analysis_id>/attempt-N/batch-binding.json` and requires exact equality
for `analysis_id`, `attempt`, `master_job`, and `namespace`. `master_job` is
validated as a Kubernetes DNS label; no `wgs-master-*` or `cce-master-*`
prefix is trusted independently of the frozen binding. Only that bound Master
is projected through `/pods`; Worker Pods remain outside the API.

Schema-1 Rule events use the CCE runtime label (`cce-run-<16 hex>`), not the
Airflow `analysis_id-aN` run ID. The node200 monitor reads that label from the
frozen `RESOLVED_PROFILE.yaml` and includes it in each complete Step3 status.
Only after the exact Master and namespace checks pass may the backend bind the
observer to that CCE label. A later attempt to change an already bound CCE
label is rejected, preventing Rule JSONL from another Master from being mixed
into the attempt.

`GET /api/runs/{analysis_id}/pods` selects the workload created by the bound
Step3 status (`event_id=step3:<master_job>`), regardless of whether the current
name starts with `cce-master-` or the historical `wgs-master-`. The legacy
prefix is retained only for already persisted pre-Step3-protocol Master rows;
arbitrary Worker workload rows remain hidden.

Re-registering Step3 for the same active attempt after a control-plane monitor
failure restores the business run to `running`, clears the monitor-generated
terminal timestamps and error summary, and writes the internal audit action
`run.step3_monitor_recovered`. It does not create a new attempt or authorize a
new Step2 submission. The resumed sensor still reports the real CCE terminal
state and does not convert an actual Master failure to success.

## T146 current WGS release

`POST /api/runs`仍只接受`project_name + batch_no + fq_path`，服务端自动绑定
`wgs-4.1.1-2499749`。客户端不能指定cce-pipeline版本；node200当前0.8.1只在
prepare后的`resolved_runtime`中审计展示。创建和提交仍是两个operator操作；
两个execution gate关闭时submit返回409。

`POST /api/runs/{analysis_id}/actions/resume`和`rerun_failed`同样必须在修改
attempt或调用Airflow前检查两个门禁。execution关闭返回HTTP 409和
`WGS_EXECUTION_DISABLED`；execution开启但runtime adapter关闭返回HTTP 409和
`WGS_RUNTIME_DISABLED`。两种拒绝均不得改变原attempt/status或Airflow DagRun；
`cancel`保持可用，以便停止已经活动的任务。

## T145 sparse intake 与 observer lifecycle API

`GET /api/intake/scanner-state`持久层只返回首次/最近扫描、本轮目录数和
错误；开关、间隔、根目录和 auto-dispatch 从运行配置补充。WGS intake
列表只包含`ready|needs_review|no_new_wgs`。内部 Step3 activate/deactivate 按
`analysis_id + attempt`幂等；Run Detail 分别返回`lifecycle_status`和
`monitoring_health`。详见[doc 27](27_WGS_SCANNER_OBSERVER_LIFECYCLE.md)。

## T143/T144 T7 intake 与 Step4 repair API

- `GET /api/intake/status?pipeline=wgs`返回芯片、上机批次、状态和三类计数，支持
  分页/状态过滤；不返回样本编号、源路径或 fingerprint。
- WGS-only部署中，`pipeline=deployed|all`和省略pipeline与显式`pipeline=wgs`
  使用同一T7投影，保证Dashboard默认筛选不会回落到历史intake表。
- `GET /api/intake/scanner-state`返回 bootstrap、最近/下次扫描、1800秒间隔和
  `auto_dispatch_enabled=false`。
- `GET /api/runs/{analysis_id}`增加`step4_repair`能力和最近维护操作。
- `POST /api/runs/{analysis_id}/actions/repair-step4`只允许 operator/admin，固定
  cram。服务端生成确认串；任意客户端 path/group/confirm字段均不属于合同。
- 两个执行门禁关闭时 repair返回409，且不创建维护记录、不触发 Airflow/SSH。

详细状态与继续语义见[文档 26](26_WGS_T7_INTAKE_STEP4_REPAIR.md)。当前发布自动
绑定`wgs-4.1.1-1656b5d`。

## T142 单一 WGS release API（历史基线）

- `GET /api/wgs/release`返回当前 `release_id`、`version`、完整 source commit 和
  两个 execution gate；除 health/login 外仍需登录。
- `POST /api/runs`只接受 WGS CCE 的 `project_name + batch_no + fq_path`；未知
  字段被拒绝，客户端不能指定 release、commit、snapshot path 或 cce-pipeline
  version。后端自动绑定 `wgs-4.1.1-1778fca`。
- `GET /api/runs/{analysis_id}`返回`pipeline_release_id`、`wgs_version`、
  `wgs_source_commit`和 prepare 后的`resolved_runtime`。
- 内部 stage request 是`wgs-runtime.request.v3`，不包含 snapshot/repository
  path 或 cce-pipeline wheel/profile/image 门禁。原 release 不可用时 prepare
  返回 HTTP 409 / `WGS_RELEASE_UNAVAILABLE`，不得自动改绑。

> **历史说明：** WGS 4.1.1 API 已随 T139 禁用态 release 发布。当前唯一设计依据为
> [`25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md`](25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md)；
> 第一版只承诺传输阶段状态，精确字节、速度和 ETA 不可用。

## T133 WGS 4.1.0 current contract

`POST /api/runs` accepts only WGS CCE requests with `project_name`, `batch_no`
and an approved `fq_path`. It does not accept `READY` or `FASTQ.MD5SUMS` as
request fields. `/rules` projects offline `rule-event.v1`; `/pods` returns only
the batch Master; `/transfers` keeps bytes/files/speed/ETA/heartbeat fields;
run detail exposes observer health and reports `degraded` when
`LOGGER_DEGRADED.json` is present. Internal stage writes require the internal
service token and accept adapter identity `wgs-runtime-200`. Public submit
continues to return HTTP 409 while `WGS_EXECUTION_ENABLED=false`.

## Historical WGS-only Phase 1 profile

The production profile accepts only `pipeline=wgs` with `project_name`, `execution_mode=cce|sge|local`, and an approved `source_path` containing the manifest, `FASTQ.MD5SUMS`, and `READY`. Login/session/user administration and WGS families, rules, pods, transfers, artifacts, and logs are exposed through FastAPI. Mutations require CSRF and role authorization. Phase 1 returns HTTP 409 for submit.

## T127 shared NIPT and WGS platform capabilities

`GET /api/platform/capabilities` is a read-only deployment contract endpoint.
The BS10610 stack returns `environment=BS10610`,
`deployed_pipelines=["nipt_docker","wgs"]`, and the public Airflow URL.
PGT-A and WES remain rejected on this deployment; frontend navigation and
filters derive from this response.

`DEPLOYED_PIPELINES` is the source of truth for aggregate resource scope. For
`GET /api/runs`, `GET /api/samples`, `GET /api/failures`,
`GET /api/dashboard/overview`, `GET /api/dashboard/runs`, and
`GET /api/intake/status`, omitted
`pipeline`, `pipeline=all`, and `pipeline=deployed` mean exactly the deployed
pipeline list. On BS this is `nipt_docker,wgs`: PGT-A is never included in the
total, page ordering, or paginated result set. Named pipeline requests remain
validated against the same deployment list. Dashboard `all`/`deployed` also
applies this scope to `qc_summary`, `sample_summary`, `sample_trend`,
`failure_summary`, and `intake_summary`.

`GET /api/dashboard/runs` uses persisted terminal state for successful and
failed WGS rows and does not request Airflow task instances for either state.
The returned page uses bulk sample, rule-event, timing, and QC queries rather
than per-run queries. WGS rule events group real workflow rules into
`Pre-calling`, `Variant analysis`, and `QC`; examples include `Preall`,
`Dedup`, and `QualCal` in Pre-calling. The top-level WGS `all` target is
contextual: `wgs_stage=precalling` maps it to Pre-calling, while full mode maps
it to QC.

The frontend nginx gateway proxies both the exact `/api` path and `/api/` path
to FastAPI before the SPA fallback in generic and BS configurations. API error
responses therefore remain JSON-compatible with the existing client error
handling instead of returning the frontend document.

`POST /api/runs` supports WGS controlled requests with
`wgs_precalling_config_path`, `wgs_downstream_config_path`,
`wgs_targets_path`, and `wgs_stage=precalling|full`. Run-local copies and
SHA256 values are immutable. The WGS run sample set is the pre-calling YAML
`sample` subset, while additional downstream sample rows are batch context.
`POST /api/runs/{analysis_id}/actions/submit` triggers `bio_wgs`.

On BS10610, WGS requests are hard-gated to dry-run. Run params expose
`wgs_dry_run=true`; the backend, scheduler, worker, and host gate all require
`WGS_ALLOW_EXECUTION=false`. Successful dry-run rows return
`display_status=success` and `qc_display_status=not_applicable` rather than
`QC pending`. Planned Snakemake jobs are stored as terminal `skipped` events
with dry-run metadata, so `/rules` and `/progress` never leave graph-only jobs
in a false running state.

Run-detail endpoints validate the requested run pipeline against
`DEPLOYED_PIPELINES` before issuing child detail/QC/log requests. The BS
frontend therefore cannot fan out historical PGT-A detail calls.

`GET /api/runs/{analysis_id}/resources` returns wall time, CPU seconds, peak
PSS/RSS, read/write I/O, collection completeness, stage summaries, and an
opaque raw JSONL artifact path. Existing NIPT contracts remain compatible.
For `source=docker_container_host_procfs`, a null PSS plus non-null RSS means
RSS is a process-tree sum and may double-count shared pages; clients must label
it as an upper bound rather than a container memory peak.

## T124 Intake timing projection and tracker ordering

`GET /api/intake/status` adds linked-run timing metadata without changing its
existing filters or pagination:

- `submitted_by`, `run_source`, and `source_batch_id`
- `elapsed_seconds`, `average_duration_seconds`
- `eta_history_count`, `eta_model`
- `estimated_remaining_seconds`, `estimated_finish_at`

Pending discoveries return null timing values. Linked discoveries use the same
success-only, pipeline/target-or-mode/profile/sample-count history model as
`GET /api/dashboard/runs`; no per-row Airflow request is introduced.

`GET /api/dashboard/runs` remains response-compatible. Active rows sort by
progress descending and oldest submission first on ties. Terminal rows then
sort by `pipeline_finished_at DESC`, falling back to `ended_at`; created-only
rows are last and newest first.

## T122 Intake lifecycle status projection

`submit_state` records Intake handoff state and intentionally remains
`submitted` after a linked workflow completes. Clients must use the joined run
projection for operator-facing state:

- `analysis_status`: the linked business run status
- `display_status`: the status shown in Dashboard/Settings
- `progress_percent` and `current_stage`: the persisted workflow progress
- `archived_at`: the time a successful Intake record left the active queue

For example, a completed NIPT request may correctly return
`submit_state=submitted`, `analysis_status=success`,
`display_status=success`, and `current_stage=Completed`.

## T121 Intake validation diagnostics

`GET /api/intake/status` keeps the existing response shape and makes pre-run
validation failures operator-readable. A Discovery row with `ready_state=error`
or `submit_state=error` and no linked run returns:

- `display_status: "error"`
- `current_stage: "Intake validation failed"`
- `last_error`: the concrete manifest, path, sample-pair, or scanner validation
  reason

These fields describe an Intake failure before Airflow handoff. They must not be
presented as a Snakemake rule failure, and the row has no Run Detail link until
an `analysis_id` exists.

## T119 Intake operation lifecycle

`GET /api/intake/status` supports the additive lifecycle query:

```http
GET /api/intake/status?pipeline=nipt_docker&lifecycle=active&keyword=NIPT-BS&limit=10&offset=0
```

`lifecycle` is `active` (default), `archived`, or `all`. Keyword matching
covers batch ID, analysis ID, and project name. Each item additionally returns
`project_name`, `analysis_status`, `display_status`, `sample_count`,
`progress_percent`, `current_stage`, `submitted_at`, `pipeline_finished_at`,
`state_changed_at`, `archived_at`, `archive_reason`, and `archive_path`.

The endpoint uses joined run/sample aggregates and does not fetch Airflow per
row. Completed workflow records, including workflow success plus sample QC
failure, are archived. Workflow failed/terminated records remain active for
triage. An archive filesystem error remains active with `archive_error` and is
safe to retry.

When `sync-airflow` replays the run-local JSONL fallback, terminal Airflow
state remains authoritative: fallback event import is completed first, then the
terminal DAG state and sample states are reapplied. This prevents a stale
failed runner event from downgrading a successfully resumed Airflow DAG run.

## T118 PGT-A manifest hardening

- PGT-A `*.samples.tsv` parsing ignores empty and whitespace-only lines while
  continuing to reject non-empty rows that do not contain exactly four
  tab-separated columns.
- A validation error discovered after a request has already been submitted
  does not downgrade its Discovery state or detach its analysis ID. The error
  remains a warning until the original valid manifest is restored.
- A stale submitted Discovery may recover only when its valid fingerprint
  matches an existing submitted run; recovery never creates another run.

## T117 run workflow summaries and operator semantics

`GET /api/runs` keeps all existing fields and adds `workflow_summary` to each
item. It is built with one bulk rule-event query for the returned page and
contains `key`, `label`, `status`, `completed_jobs`, and `total_jobs`.

PGT-A exposes Mapping, Metadata, CNV QC, and CNV prediction. NIPT Docker
exposes Input QC, Mapping, CNV, T21 classifier, Fetal fraction, and Final QC.
`submitted_by` remains a nullable audit label; it is not an Airflow RBAC user.
The T117 operator correction is CLI-only and adds no public metadata editing
endpoint.

## T114 run status, timing, and sample QC

`GET /api/dashboard/runs` adds `display_status`, `pipeline_finished_at`,
`eta_history_count`, and `eta_model`. `display_status` combines the workflow
and sample decision without changing the raw `status` and `qc_status` fields:

- workflow failure -> `failed`
- workflow success plus QC failure -> `qc_failed`
- workflow success plus QC warning -> `qc_warning`
- workflow success plus unknown sample QC -> `qc_pending`
- clean workflow/sample success -> `success`

The `failed` filter includes workflow failures and QC failures; the `success`
filter excludes QC failures. Terminal success rows report `Completed` instead
of a stale last rule. Runtime starts at immutable `submitted_at` and ends at
`pipeline_finished_at` when available.

ETA history accepts only clean `mode=new` successful runs with the same
pipeline, target/run mode, and runtime profile. Failed, resumed, smoke,
QC-failed, or incomplete timing records are excluded. Exact sample-count
history uses a median; multiple sample sizes use a nonnegative overhead plus
per-sample fit; a single size uses a bounded 0.5x-2x proportional estimate.

`GET /api/runs/{analysis_id}/qc` preserves metric-level `summary` and adds
sample-level `sample_summary`. Each item adds `decision_metric`. Informational
read count, chrY, and gender fields do not lower sample QC status. Q30, unique
mapping, duplication, fetal fraction, and other thresholded fields are
decision metrics.

## T113 NIPT rule observability

`GET /api/runs/{analysis_id}/progress` adds `current_phase`, `current_rule`,
`current_sample`, and `rule_counts`. For an active NIPT full run, persisted
logger events refine the 15-90 percent execution interval. Progress never moves
backwards when retry/resume events are imported.

`GET /api/runs/{analysis_id}/rules` accepts optional `status`, `rule`,
`sample_id`, `limit`, and `offset`. Its response keeps `items` and adds
`total`, `limit`, `offset`, and a status/phase `summary`. Default calls remain
compatible with existing clients.

`GET /api/runs/{analysis_id}/logs/index` resolves absolute or run-relative
event log paths only when the resolved file stays beneath that run's approved
workdir. It exposes workflow logs plus available current/failed rule logs
without returning arbitrary host files.

## T111 Snakemake config profiles

T111 adds run-scoped, immutable Snakemake configuration for the deployed
`pgta` and `nipt_docker` pipelines. Runtime executable paths, Docker images,
mounts, commands, and Compose content are never returned by the public profile
API.

```text
GET  /api/pipeline-config/template?pipeline=pgta&target=metadata&profile_id=pgta-current
POST /api/pipeline-config/validate
GET  /api/runs/{analysis_id}/config
```

The template response contains sanitized profile labels/versions, a profile
hash, and the editable default YAML. Validation accepts
`pipeline`, `target`, `run_mode`, `cores`, `runtime_profile_id`,
`config_template_hash`, and `snakemake_config_yaml`; it returns normalized YAML
and changed paths. Invalid YAML, protected/unknown fields, duplicate keys,
anchors/aliases/tags, type/range errors, and payloads over 64 KiB return
`400 CONFIG_VALIDATION_ERROR`; numeric values must also be finite. A stale profile hash returns
`409 PROFILE_CHANGED`.

`POST /api/runs` accepts the following three fields together for PGT-A/NIPT:

```json
{
  "runtime_profile_id": "pgta-current",
  "config_template_hash": "sha256",
  "snakemake_config_yaml": "core:\n  wisecondorx: ...\n"
}
```

The backend stores the requested YAML and provenance in the run workdir. The
provenance file includes the approved runtime snapshot for server-side audit,
but the API never returns that hidden snapshot. The Airflow prepare task writes
the resolved YAML. `/config` rejects symlinked config files and returns only requested
and resolved Snakemake configuration plus sanitized profile provenance; it does
not return Docker Compose. Legacy clients may omit all three create fields and
legacy runs return `state=legacy` when no requested config was captured.

## 1. 通用约定

Base URL:

```text
/api
```

## T108 Dashboard Samples and Controlled PGT-A Rerun

T108 extends the existing Dashboard and reanalysis contracts without adding a
database migration.

### Dashboard overview additions

`GET /api/dashboard/overview?pipeline=all|pgta|nipt_docker&period=24h|7d|30d`
now also returns sample-level throughput fields:

```json
{
  "sample_summary": {
    "total": 112,
    "running": 2,
    "workflow_failed": 1,
    "qc_failed": 2,
    "completed": 107
  },
  "sample_trend": [
    {
      "date": "2026-07-08",
      "total": 56,
      "running": 0,
      "workflow_failed": 0,
      "qc_failed": 0,
      "completed": 56
    }
  ]
}
```

### Dashboard runs additions

`GET /api/dashboard/runs` preserves the raw progress fields and adds
operator-readable fields:

```json
{
  "current_stage_label": "Baseline BAM uniformity QC",
  "current_stage_source": "Snakemake rule event",
  "elapsed_seconds": 870,
  "average_duration_seconds": 7200,
  "estimated_remaining_seconds": 6330,
  "estimated_finish_at": "2026-07-08T04:16:30+00:00"
}
```

ETA is an estimate only. It is calculated from recent successful runs with the
same `pipeline + target/run_mode`; if there is not enough history the fields are
`null`.

### Controlled PGT-A stage rerun

`POST /api/runs/{analysis_id}/actions/reanalyze` still supports PGT-A
`resume`, and now supports a controlled stage rerun:

```json
{
  "mode": "rerun_stage",
  "stage": "metadata",
  "reason": "operator requested metadata refresh"
}
```

Rules:

- only `pipeline=pgta`
- only `target=baseline_qc`
- only terminal `failed`, `terminated`, or `success` runs
- stage must be one of `mapping`, `metadata`, or `baseline_qc`
- active runs, arbitrary DAG ids, arbitrary Airflow tasks, rule/sample
  selection, and `--forceall` are rejected

The endpoint records the previous and new DAG run ids in `run_action.payload_json`
and submits `bio_pgta` with `params.rerun_stage`.

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

T103 update: `POST /api/input/scan` supports `pipeline=pgta` and
`pipeline=nipt_docker`. PGT-A roots come from `PGTA_INPUT_SCAN_ROOTS` with
legacy `INPUT_SCAN_ROOTS` fallback. NIPT roots come from `NIPT_INPUT_SCAN_ROOTS`.
NIPT scanning returns chip-folder grouped `*.clean.fastq.gz` R1/R2 pairs;
nested adapter FASTQ files are ignored in v1.

T128 BS contract: the approved manual NIPT scan root is
`/data/nipt-fastq/FQ2026`. Discovery traverses candidate batch directories in
descending name order and stops after `max_samples`; it must not materialize
the complete FASTQ tree before applying the limit. The read-only
`/data/nipt-fastq` mount remains available for historical run compatibility.

```http
GET /api/input/roots?pipeline=pgta
GET /api/input/roots?pipeline=nipt_docker
```

Response:

```json
{
  "pipeline": "nipt_docker",
  "roots": ["/data/nipt-fastq/FQ2026"]
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

T103 changes the current deployable NIPT Docker entrypoint from fixed
`run1/run2` templates to server-path scanned chip batches. New create requests
must pass `rawdata_root` and `selected_samples` returned by
`POST /api/input/scan`. Historical `template_id` runs remain readable for
compatibility, but the frontend no longer exposes `run1/run2`.

Request:

```json
{
  "pipeline": "nipt_docker",
  "project_name": "NIPT docker scanned chip smoke",
  "rawdata_root": "/opt/pipelines/NIPT/fastq",
  "selected_samples": [
    {
      "sample_id": "NIPT26040207.A06",
      "r1": "/opt/pipelines/NIPT/fastq/FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2/NIPT26040207.A06.R1.clean.fastq.gz",
      "r2": "/opt/pipelines/NIPT/fastq/FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2/NIPT26040207.A06.R2.clean.fastq.gz",
      "source_dir": "/opt/pipelines/NIPT/fastq/FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2",
      "discovery_method": "nipt_docker_clean_scan"
    }
  ],
  "run_mode": "mount_smoke",
  "cores": 40,
  "email_to": null,
  "note": "scanned batch smoke only"
}
```

Rules:

- `rawdata_root` must be under `NIPT_INPUT_SCAN_ROOTS`.
- `selected_samples` must all come from exactly one NIPT chip folder; if the
  UI selects multiple chip folders it creates one run per batch.
- NIPT v1 only accepts top-level `*.clean.fastq.gz` R1/R2 pairs from the chip
  folder.
- `run_mode` must be `mount_smoke` or `full_run`.
- `full_run` is rejected unless `NIPT_ALLOW_HEAVY_RUN=true`; the default deployed acceptance mode is `mount_smoke`.
- `cores` must be between 1 and 40.

Response:

```json
{
  "analysis_id": "NIPT_20260708_033450_8362A0",
  "pipeline": "nipt_docker",
  "dag_id": "bio_nipt_docker",
  "dag_run_id": null,
  "status": "created",
  "workdir": "/data/airflow-demo/runs/NIPT_20260708_033450_8362A0",
  "sample_count": 1
}
```

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

T045/T084 阶段支持把已存在的 PGT-A controlled target run 提交到 Airflow；T044/T056 后也支持把 `wes_qsub` created run 提交到 `bio_wes_qsub`。T101 supports submitting `nipt_docker` created runs to `bio_nipt_docker`.

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

NIPT Docker submit requires:

- `analysis_run.pipeline_name = nipt_docker`
- `analysis_run.status = created`
- `analysis_run.params_json.input_mode = nipt_docker_scan`
- `analysis_run.params_json.source_batch_dir` is present
- `analysis_run.params_json.run_mode` is `mount_smoke` unless `NIPT_ALLOW_HEAVY_RUN=true`
- `sample_sheet_path` and `workdir` must exist
- DAG id is `bio_nipt_docker`

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
- `400 VALIDATION_ERROR`: pipeline 不是当前允许提交的 `pgta/wes_qsub/nipt_docker`、状态不是 `created`、target/template 不在受控白名单内，或 run 缺少必要路径。
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
- `nipt_docker` 在 Airflow `success` 时解析 `workdir/reports/qc_summary.tsv`，幂等刷新 `qc_metric`，并更新 `sample.qc_status`。`mount_smoke` mode writes one `nipt_mount_smoke=pass` row per template sample.

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

## 6.1 Progress

```http
GET /api/runs/{analysis_id}/progress
```

T102 adds a read-only progress endpoint for Dashboard and Run Detail. The endpoint does not read the Airflow metadata database directly. It combines:

- biodemo `analysis_run` state.
- Airflow REST task instances from `/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances`.
- biodemo `snakemake_rule_event` rows written by PGT-A and NIPT Docker runner events.

Response:

```json
{
  "analysis_id": "NIPT_20260708_050843_B3B05E",
  "pipeline": "nipt_docker",
  "status": "success",
  "dag_id": "bio_nipt_docker",
  "dag_run_id": "manual__NIPT_20260708_050843_B3B05E",
  "percent": 100,
  "current_step": "nipt_mount_smoke",
  "current_source": "snakemake_events",
  "note": "Airflow task run_nipt_docker; pipeline rule events captured",
  "not_in_airflow": false,
  "progress_source": "snakemake_events",
  "airflow_tasks": [
    {
      "task_id": "run_nipt_docker",
      "state": "success",
      "start_date": "2026-07-08T05:08:46.578757+00:00",
      "end_date": "2026-07-08T05:08:48.884719+00:00",
      "duration": 2.305962,
      "try_number": 1,
      "operator": "PythonOperator"
    }
  ],
  "rule_events": [
    {
      "rule": "nipt_mount_smoke",
      "sample_id": null,
      "status": "success",
      "snakemake_jobid": null,
      "qsub_jobid": null,
      "stdout_path": "/data/airflow-demo/runs/NIPT_20260708_050843_B3B05E/logs/snakemake.stdout.log",
      "stderr_path": "/data/airflow-demo/runs/NIPT_20260708_050843_B3B05E/logs/snakemake.stderr.log",
      "start_time": "2026-07-08T05:08:46.989216+00:00",
      "end_time": "2026-07-08T05:08:48.800137+00:00",
      "message": "NIPT Docker mount_smoke completed.",
      "return_code": 0,
      "wildcards": {}
    }
  ]
}
```

Progress rules:

- `created`: `0%`, `current_step=Created only`, `not_in_airflow=true`.
- `submitted/queued/scheduled`: `5-10%`, current step from the latest Airflow handoff task if available.
- `bio_pgta` task weights after T107: `validate_request=5`, `prepare_pgta_config=10`, `choose_pgta_path=10`, `pgta_pipeline.run_pgta_mapping=55`, `pgta_pipeline.run_pgta_metadata=70`, `pgta_pipeline.run_pgta_baseline_qc=90`, historical `run_pgta_target=90`, `collect_pgta_artifact=100`.
- `bio_nipt_docker` task weights: `validate_request=5`, `prepare_nipt_docker_run=15`, `run_nipt_docker=90`, `collect_nipt_artifacts=100`.
- While the run task is active, rule events refine the 15-90% interval and set `progress_source=snakemake_events`.
- Historical runs without rule events still return Airflow task timelines; `rule_events=[]` means no pipeline-level events were captured for that run.

T107 keeps the response shape unchanged. The only contract change is semantic:
new PGT-A `baseline_qc` DAG runs can expose the staged Airflow task ids above,
while existing metadata/dryrun/failure runs and historical baseline runs may
still expose `run_pgta_target`.

Errors:

- `404 RUN_NOT_FOUND`: `analysis_id` does not exist.
- `502 AIRFLOW_PROGRESS_FAILED`: backend could not read Airflow task instances.

## 7. 查询任务列表

```http
GET /api/runs?pipeline=pgta&status=created&limit=50&offset=0
```

`qc_status` 是 run-level 展示字段，由该 run 下 `sample.qc_status` 聚合得到，不直接查询 Airflow metadata DB，也不在普通 GET 中隐式解析 QC 文件。聚合优先级为 `fail > warn > unknown > pass`：

- 任一样本 `fail/failed/error` => `fail`。
- 否则任一样本 `warn/warning/qc_warning` => `warn`。
- 全部样本 `pass/success` => `pass`。
- 无样本、未导入 QC、或混合未知状态 => `unknown`。

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
- `logs/pgta.python_preflight.log`
- `logs/snakemake.stdout.log`
- `logs/snakemake.stderr.log`
- `logs/snakemake.mapping.command.txt`
- `logs/snakemake.mapping.stdout.log`
- `logs/snakemake.mapping.stderr.log`
- `logs/snakemake.metadata.command.txt`
- `logs/snakemake.metadata.stdout.log`
- `logs/snakemake.metadata.stderr.log`
- `logs/snakemake.baseline_qc.command.txt`
- `logs/snakemake.baseline_qc.stdout.log`
- `logs/snakemake.baseline_qc.stderr.log`
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

NIPT Docker v1 dynamically discovers only NIPT/generic artifacts for `pipeline=nipt_docker`:

- `logs/snakemake.stdout.log`
- `logs/snakemake.stderr.log`
- `reports/qc_summary.tsv`
- `config/nipt_docker_compose.yml`
- `config/nipt_run_config.yaml`
- `config/nipt_airflow_request.json`
- `logs/nipt_docker.command.txt`

Pipeline-specific artifact keys are filtered by pipeline, so a NIPT Docker run must not expose `wes_qc_summary` or PGT-A-only artifacts even if the relative path overlaps.

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
## T103 Intake Scanner APIs

### Read Discovery Status

```http
GET /api/intake/status?pipeline=nipt_docker&state=submitted&keyword=NIPT_2026&limit=10&offset=0
```

All query parameters are optional. `pipeline` may be `pgta` or
`nipt_docker`; `state` may be `bootstrap`, `observed`, `ready`, `submitted`,
`error`, or `disabled`. `keyword` matches `batch_id` or `analysis_id`
case-insensitively; SQL wildcard characters are treated as literal input.
Results sort by `last_seen_at DESC, id DESC`.

The state filter is a product-level projection of `ready_state` and
`submit_state`. Error and disabled states take precedence, followed by
submitted/bootstrap, then ready/observed. Discovery state is never converted
to an Airflow `queued` run status.

```json
{
  "items": [
    {
      "pipeline": "nipt_docker",
      "root_path": "/opt/pipelines/NIPT/fastq",
      "batch_id": "FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2",
      "fingerprint": "sha256...",
      "file_count": 192,
      "total_bytes": 1234567890,
      "ready_state": "ready",
      "analysis_id": "NIPT_20260708_120000_A1B2C3",
      "submit_state": "submitted",
      "last_seen_at": "2026-07-08T12:00:00+00:00"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

Existing clients that only read `items` remain compatible. The endpoint is
read-only and does not scan roots, mutate discovery rows, create runs, or
submit Airflow DAGs.

### Scan And Submit Stable Batches

```http
POST /api/intake/scan-and-submit
Content-Type: application/json
```

```json
{
  "pipelines": ["pgta", "nipt_docker"],
  "bootstrap": false,
  "max_samples": 200
}
```

Rules:

- First sighting of a batch records `ready_state=observed` and does not submit.
- A second scan with the same fingerprint marks the batch `ready`.
- Automatic create+submit only happens when `config/intake.yaml` has both
  `defaults.auto_submit=true` and the matching
  `pipelines.<name>.auto_submit.enabled=true`.
- When auto-submit is disabled, the endpoint may update discovery state but
  must not create an `analysis_run` or trigger Airflow.
- `bootstrap=true` records existing batches as observed/bootstrap so historical
  data is not automatically re-run during deployment.
- PGT-A auto intake uses target `metadata`; NIPT Docker auto intake uses
  `mount_smoke` unless future production settings explicitly opt into heavy
  full-run mode.

#### NIPT YAML Request Intake

T120 adds an explicit request mode to the same endpoint. The backend scans only
the configured `nipt_docker.intake.request_inbox` for final `*.nipt.yaml`
files. A request contains `request_id`, `project_id`, `batch_id`, `samples`,
`submitted_by`, `runtime_profile_id`, `run_mode`, `cores`, and `submit`.

The request never contains a FASTQ path. `batch_id` is resolved uniquely below
the approved NIPT roots, and only complete top-level
`*.R1.clean.fastq.gz`/`*.R2.clean.fastq.gz` pairs are accepted. `samples` is
either `all` or a unique list of resolved sample IDs.

Run creation and Airflow submission require two stable observations,
`submit: true`, `defaults.auto_submit=true`, and
`nipt_docker.intake.request_submit_enabled=true`. The ordinary
`nipt_docker.auto_submit.enabled=false` directory-discovery gate remains
unchanged. Therefore a discovered FASTQ folder cannot launch a run without an
explicit YAML request.

Unknown keys, duplicate YAML keys, aliases, custom tags, unsafe identifiers,
unsupported profiles/modes, and files over 64 KiB are rejected as structured
Discovery errors. Files ending in `.partial` are ignored. After workflow
success, only the request YAML moves to `.archive/YYYY/MM/<request_id>`; FASTQ
is never moved or deleted.

## T104 Dashboard, Resource, And Intake Config APIs

### Dashboard Overview

```http
GET /api/dashboard/overview?pipeline=all&period=7d
```

`pipeline` may be `all`, `pgta`, or `nipt_docker`. `period` may be `24h`,
`7d`, or `30d`. This endpoint is a backend aggregation endpoint for the
Dashboard first screen. It must not call per-run detail, per-run progress, or
Airflow task-instance APIs.

Response shape:

```json
{
  "pipeline": "all",
  "period": "7d",
  "totals": {"runs": 12, "running": 1, "failed": 1, "success": 8, "created": 2},
  "status_distribution": {"created": 2, "submitted": 0, "queued": 0, "running": 1, "success": 8, "failed": 1, "other": 0},
  "pipeline_breakdown": {
    "pgta": {"runs": 11, "running": 1, "failed": 1, "success": 8},
    "nipt_docker": {"runs": 1, "running": 0, "failed": 0, "success": 0}
  },
  "trend": [{"date": "2026-07-08", "runs": 7, "failed": 0, "success": 5}],
  "qc_summary": {"pass": 8, "warn": 0, "fail": 1, "unknown": 3},
  "failure_summary": [],
  "intake_summary": {"observed": 1, "ready": 0, "submitted": 1, "bootstrap": 1, "error": 0, "disabled": 0}
}
```

### Dashboard Run Tracker Page

```http
GET /api/dashboard/runs?pipeline=all&status=active&keyword=PGTA&limit=10&offset=0
```

`status` is optional. Supported values are `active`, `created`, `failed`, and
`success`. The endpoint returns one page of tracker rows. Active and failed rows
may call `/progress` internally to read Airflow task instances. Created rows and
terminal success rows are resolved from biodemo DB/rule events to avoid
unnecessary Airflow REST calls.

Response shape:

```json
{
  "items": [
    {
      "project_name": "Fresh transfer 2-sample QC",
      "analysis_id": "PGTA_20260708_103000_ACTIVE",
      "pipeline": "pgta",
      "status": "running",
      "qc_status": "unknown",
      "sample_count": 2,
      "created_at": "2026-07-08T10:30:00+08:00",
      "started_at": "2026-07-08T10:31:00+08:00",
      "ended_at": null,
      "dag_id": "bio_pgta",
      "dag_run_id": "manual__PGTA_20260708_103000_ACTIVE",
      "percent": 52,
      "current_airflow_task": "run_pgta_target",
      "current_pipeline_rule": "baseline_bam_uniformity_qc",
      "progress_source": "snakemake_events",
      "not_in_airflow": false,
      "note": "Airflow task run_pgta_target; pipeline rule events captured"
    }
  ],
  "total": 12,
  "limit": 10,
  "offset": 0,
  "pipeline": "all"
}
```

### System Resources

```http
GET /api/system/resources
```

Returns host resource telemetry from `/proc` plus Docker container stats when
available. If Docker stats cannot be read, the endpoint returns
`source=host_proc` and an empty `containers` array instead of failing the
Dashboard.

### Intake Config

```http
GET /api/intake/config
```

Returns the sanitized `config/intake.yaml` state. `host_path` is not returned to
the browser. Environment scan roots are fallback only when `INTAKE_CONFIG_PATH`
is missing or unreadable.

### Intake Scanner State

```http
GET /api/intake/scanner-state
```

T105 adds a read-only scanner readiness endpoint for Settings. It reads Airflow
through the REST API, not the Airflow metadata DB, and reports whether
`bio_intake_scan` is paused plus the latest scanner DAG run.

Response:

```json
{
  "dag_id": "bio_intake_scan",
  "airflow_reachable": true,
  "is_paused": true,
  "latest_dag_run_id": "scheduled__2026-07-08T17:00:00+08:00",
  "latest_dag_run_state": "success",
  "latest_start_date": "2026-07-08T17:00:01+08:00",
  "latest_end_date": "2026-07-08T17:00:05+08:00",
  "message": null
}
```

If Airflow is unavailable, this endpoint still returns HTTP 200 with a degraded
payload so the Settings page can render the rest of intake configuration:

```json
{
  "dag_id": "bio_intake_scan",
  "airflow_reachable": false,
  "is_paused": null,
  "latest_dag_run_id": null,
  "latest_dag_run_state": null,
  "latest_start_date": null,
  "latest_end_date": null,
  "message": "Airflow scanner state unavailable"
}
```

### Intake Scan Preview

```http
POST /api/intake/scan-preview
Content-Type: application/json
```

T106 adds a dry-run scanner preview for operator review before unpausing
`bio_intake_scan`. It scans configured roots and compares the result with
`intake_discovery`, but it must not write discovery rows, create runs, or call
Airflow.

Request:

```json
{
  "pipelines": ["pgta", "nipt_docker"],
  "bootstrap": false,
  "max_samples": 200
}
```

Response:

```json
{
  "summary": {
    "total_batches": 2,
    "new_observed": 0,
    "stable_ready": 1,
    "bootstrap_protected": 1,
    "would_create": 0,
    "would_submit": 0,
    "blocked_auto_submit": 1,
    "errors": 0
  },
  "items": [
    {
      "pipeline": "nipt_docker",
      "root_path": "/opt/pipelines/NIPT/fastq",
      "batch_id": "FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2",
      "source_dir": "/opt/pipelines/NIPT/fastq/FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2",
      "fingerprint": "sha256...",
      "file_count": 4,
      "total_bytes": 402,
      "existing_ready_state": "observed",
      "existing_submit_state": "not_submitted",
      "existing_analysis_id": null,
      "would_transition_to": "ready",
      "would_create_run": false,
      "would_submit": false,
      "auto_submit_enabled": false,
      "reason": "auto_submit_disabled"
    }
  ]
}
```

## T110 Operator Resource APIs

T110 adds paginated operator resources without changing run creation, Airflow
submission, DAG behavior, or the database schema.

### Batch Runs

```http
GET /api/runs?pipeline=pgta&status=failed&keyword=project-a&sort=created_desc&limit=20&offset=0
```

Optional filters are `pipeline`, `status`, `keyword`, and `sort`. Supported sort
values are `created_desc`, `duration_desc`, and `status`. Each list item retains
the existing fields and adds `project_name`. Existing calls without the new
parameters remain valid. The operator UI sends `pipeline=deployed` for its
`All deployed` choice. Aggregate callers that omit `pipeline` or send
`pipeline=all` use the configured `DEPLOYED_PIPELINES` list; named-pipeline
filters retain their single-pipeline compatibility. Intake applies that
configured scope before counting, ordering, and paginating rows.

### Sample Matrix

```http
GET /api/samples?pipeline=nipt_docker&status=success&qc_status=pass&keyword=A06&limit=25&offset=0
```

The response contains `analysis_id`, `project_name`, `pipeline`, `sample_id`,
`family_id`, `status`, `qc_status`, `source_folder`, `r1_name`, `r2_name`, and
`report_status`, plus top-level `total`, `limit`, and `offset`. Full FASTQ server
paths are never returned by this list endpoint.

### Failure Triage

```http
GET /api/failures?pipeline=all&kind=workflow&period=7d&layer=pipeline_rule&keyword=samtools&limit=20&offset=0
```

`kind` is `all`, `workflow`, or `qc`. A workflow-success run with failed sample
QC is returned only as `failure_kind=qc`; it is not mislabeled as a workflow
failure. Items include the failure layer, failed step and readable label,
sample id, return code, stderr excerpt, possible reason, suggested action code,
and guarded PGT-A recovery flags. NIPT Docker items do not advertise unsupported
resume or rerun actions. `stderr_excerpt` replaces absolute server path prefixes
with `<server-path>/` and redacts common `password`, `token`, `secret`, and API
key assignments. File basenames and error text remain available for diagnosis.

Workflow and QC issues are item-level categories. A workflow-failed run may also
produce a separate QC item when a captured sample QC status is failed; the QC
item is never mislabeled as a workflow failure.

### Dashboard Performance Boundary

`GET /api/dashboard/runs` continues to return the T108 response contract. T110
bulk-loads page-level sample/QC/rule data and calls Airflow task-instance REST
only for active rows. Terminal rows use persisted business/rule state, so a
terminal-only page does not fan out to Airflow.

## T112 PGT-A S9 predict operations

- `POST /api/runs` accepts PGT-A `target=predict` and optional `submitted_by`.
- Run list/detail responses add `submitted_at` and `submitted_by`.
- Runs and Dashboard rows include pipeline-specific `qc_highlights`.
- `GET /api/runs/{analysis_id}/logs/index` returns opaque stage/rule log keys;
  pass a key to the existing `/logs` endpoint. Legacy streams remain valid.
- PGT-A auto intake reads `<request_id>.samples.tsv` only with a matching READY
  marker. Required columns are `project_id`, `source_batch`, `sample_id`, and
  `operator`; invalid manifests are audited and never submitted.
- `POST /api/intake/scan-and-submit` and `POST /api/events/snakemake` require
  `X-Airflow-Demo-Token` when `INTERNAL_SERVICE_TOKEN` is configured. The token
  is for Airflow/backend service calls and is not a frontend credential.
- An observed READY request is immutable. A changed manifest or resolved FASTQ
  fingerprint is recorded as `error`; operators must create a new request ID.
- Auto-intake stores `intake_request_id` and `intake_fingerprint` in run params
  so a run committed before a worker crash can be recovered without duplication.
# T123 Operations consistency APIs

- `GET /api/intake/status` accepts `view=pending|history|all`. `pending`
  returns Discovery records without an `analysis_id`; `history` returns linked
  runs; `all` is intended for the Settings audit view.
- `GET /api/dashboard/runs` adds `run_source`, `source_batch_id`,
  `qc_display_status`, and `qc_display_note`. Intake provenance is identified
  by the immutable `params.intake_request_id`; a manual server scan remains a
  manual run.
- `GET /api/workflows` returns only the deployed `PGT-A Predict` and
  `NIPT Docker Full` workflows with live latest-run state, success rate, and
  persisted stage summaries. It does not query Airflow once per run.
- `GET /api/intake/scanner-state` also returns the schedule, next run,
  trigger contracts, and scanner-only retention policy.
- `POST /api/intake/retention` is an internal-token endpoint restricted to
  terminal `bio_intake_scan` DAG runs older than 30 days. Analysis DAG IDs are
  rejected.

QC projection uses `pending` before QC, `unavailable` when a failed workflow
never produced decision metrics, and pass/warn/fail only from decision metrics.
Informational values such as read count, gender, and chrY do not create an
unknown sample decision.

## Historical T130 WGS monitoring reads

This section records the retired snapshot-era API. The current WGS 4.1.1
release-bound contract is defined in the T142 section above and uses
`pipeline_release_id`.

All endpoints below require an authenticated session and read biodemo only.
They do not access Kubernetes, SFS, or evidence files during a request.

- `GET /api/runs/{analysis_id}` adds `pipeline_snapshot_id`,
  `rule_event_schema_version`, and an optional `observer` object containing
  `status`, `last_success_at`, `last_error`, and `updated_at`.
- `GET /api/runs/{analysis_id}/rules` returns projected WGS Rule rows with
  attempt, stable Rule instance ID, name, sample, layer, terminal state, and
  timestamps.
- `GET /api/runs/{analysis_id}/pods` returns `pod_hash`, `job_name`, phase,
  reason, exit code, image ID, node, message, resource summary, observation
  time, and database update time.

Unknown or non-WGS analysis IDs return HTTP 404 for Rule/Pod reads.
# T131: WGS create uses `batch_no + fq_path`; validation-issues and operator
# revalidate endpoints were added. Transfers, Rules and progress expose full
# progress and ETA fields from `23_WGS_CLOUD_ORCHESTRATION_PHASE1.md`.
