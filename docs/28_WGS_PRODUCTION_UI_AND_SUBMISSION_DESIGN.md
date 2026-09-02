# WGS production UI, monitoring, and submission design

Status: approved implementation contract for T153-T158.

Current candidate baseline (2026-09-02): WGS `dev_CJC_4.2.0_cloud`, version
`V4.2.0`, commit `78797181ee0582bea3167385c243616017f092ce`, release ID
`wgs-4.2.0-7879718`. The shared repository paths are
`/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0` on BS10610 and
`/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0` on node200. This is a
source-contract update only and does not enable or deploy a real run.

This document supersedes the WGS user-interface, progress, submission, log,
resource, and Step7-cleanup portions of documents 25-27. The WGS execution
contract remains Step1-Step6 in the single `bio_wgs` DAG. It does not authorize
a real batch, automatic intake dispatch, or modification of the WGS repository.

## 1. Product boundary

- The product exposes WGS only. A run is bound by the server to the current WGS
  release and the client cannot select a commit, image, profile, or repository.
- Dashboard and Run Detail show the analysis `batch_no` as a first-class field.
- User-facing stages are Prepare, Step1 through Step6, and Final. Raw Airflow
  task IDs remain audit data and are not the primary UI label.
- WGS QC widgets are removed from the UI. Existing QC tables and endpoints are
  retained for compatibility and are not destructively migrated.
- The browser never accepts arbitrary server paths, YAML, shell arguments,
  linkage groups, Kubernetes identities, OBS URIs, SFS paths, or cleanup
  confirmation strings.
- The current WGS `ANALYSIS_COMPLETE` producer/consumer mismatch remains a WGS
  runtime blocker. Control-plane presentation must not hide it or infer success.

## 2. Authoritative stage and progress contract

`run_stage_state` is keyed by `analysis_id + attempt + stage_code`. It stores a
single current projection for each stage:

```text
stage_code, step_number, stage_label, stage_status
progress_available, progress_percent
completed_units, total_units, unit
current_item, speed_bps, eta_seconds
progress_source, message, evidence_key
started_at, ended_at, updated_at
```

The fixed labels are:

| Code | Label |
|---|---|
| `prepare` | Preparing WGS batch |
| `step1_upload` | Uploading FASTQ |
| `step2_master` | Starting WGS workflow |
| `step3_monitor` | WGS workflow running |
| `step4_publish` | Publishing WGS results |
| `step5_download` | Downloading WGS results |
| `step6_materialize` | Materializing local results |
| `final` | WGS workflow completed |

`GET /api/runs/{analysis_id}/progress` returns the fields above. Compatibility
fields remain for one release, but the WGS frontend must not derive progress
from Airflow task counts.

- Step1 and Step5 consume validated `wgs-runtime.transfer-progress.v1` records
  produced by an Airflow-owned transparent `obsutil` wrapper on node200. The
  wrapper delegates the original command and preserves stdout, stderr and exit
  code, while parsing each process's CR/LF progress stream into an atomic,
  request-scoped JSON file. The runner aggregates these records every five
  seconds. Progress instrumentation failure never changes the transfer exit
  code; it sets monitoring health to degraded and exposes detailed progress as
  unavailable.
- Step3 consumes the bound Step3 status values `completed`, `total`, `percent`,
  and `current_rule` after identity validation.
- Step2, Step4, and Step6 use an indeterminate active state unless their runtime
  contracts later provide exact units.
- A stage label is not a whole-analysis percentage. The API does not expose a
  coarse Step1-Step6 `overall_progress_percent`, and does not derive an analysis
  ETA from stage position. `analysis_eta_seconds` remains null until runtime
  provides an exact model; stage-local `eta_seconds` remains available.
- A terminal stage is monotonic. A later stale status cannot overwrite it, and
  success and failure cannot replace one another.
- Step3 succeeds only when the bound Master is Complete and the Snakemake
  terminal markers agree. During cloud delivery, Step4 is waiting/publishing.
  The known Master-completion race is retried for the bounded grace period;
  timeout, identity mismatch, or a real failure enters Failure Diagnosis.

## 3. Rules and logs

`rule_state` is extended with `sequence`, `phase`, `snakemake_jobid`,
`family_id`, `wildcards_json`, `message`, and `log_paths_json`. Logger fields are
optional so older schema-1 evidence remains ingestible. The observer may enrich
sample and family identity only by an unambiguous match to registered samples.

Rules are sorted by `phase_order`, `layer`, `sequence`, and `sample_id`. Run
Detail renders a small phase dependency graph followed by a filterable Rule
instance table. It does not attempt to draw every dynamic Snakemake job as a
full DAG.

The evidence bridge mirrors the bound Master `analysis.log` incrementally.
There is no per-Rule SFS path registry. For a failed Rule, the backend derives a
bounded diagnostic excerpt from the already registered `analysis.log`, using
the exact Snakemake job ID and Rule name as anchors. The Rule table links to the
same analysis log through its existing opaque key. This keeps the server-side
path boundary small and avoids trusting logger-provided paths. If the event
cannot be matched, the UI shows the Rule message and a link to the analysis-log
tail instead of reading an arbitrary file.

The backend log index uses opaque keys and resolves every currently available
file under registered evidence/run roots. Client paths and traversal
components are rejected. Failure Triage uses `rule_state`, `run_stage_state`,
Master evidence, and indexed logs; it does not use the retired WGS
`snakemake_rule_event` projection.
WGS log reads without a registered opaque key return 404; they never fall back
to legacy fixed `logs/snakemake.*` paths when the index is empty.
Opaque keys are generated by the backend and require no operator setting. Log
tail requests read backwards in 64 KiB chunks, return at most 1000 lines, and
stop after 8 MiB; the response reports total file size and whether it was
truncated, so a large Master `analysis.log` is never loaded in full.

## 4. Safe Samples projection

The public WGS sample projection contains only:

```text
sample_id, data_id, family_id, family_relation, sample_type, sex,
sequencing_batch, r1_filename, r2_filename, status,
pending_source, pending_reason
```

Names, birth dates, hospital, doctor, clinical complaint, keywords, and other
clinical fields from raw `sampleinfo.tsv` must not enter public API responses,
logs, frontend bundles, tests, or Git fixtures.

## 5. Submission and WGS prepare semantics

Submission is one server-controlled action, not a pre-analysis preview wizard.
`POST /api/wgs/runs` accepts only catalog IDs and WGS prepare parameters:

```text
project_id, platform, sequencing_batch, analysis_batch,
fastq_root_id, use_reference, algo
```

The backend resolves the project and FASTQ root from the server catalog, binds
the current WGS release, creates exactly one AnalysisRun, and submits the single
`bio_wgs` DAG idempotently. The browser cannot submit an arbitrary path or
version.

For WGS 4.2.0, `platform=T7`; `sequencing_batch` and `analysis_batch` use the
WGS batch token such as `20260902A`. WGS itself derives the authoritative
directory/OBS batch name `WGS_<analysis_batch>_T7Hg38V4.2.0`. `algo` is limited
to `DNAscope|Haplotyper` and defaults to `DNAscope`.

The DAG then follows the WGS repository's existing behavior in the protected
analysis work area:

```text
sampleinfo
→ confirm that sampleinfo contains candidate samples
→ analysis selects eligible and pending samples
→ create the project/batch analysis directory and frozen bundle
→ Step1-Step6
```

The frontend does not preview or edit the intermediate sampleinfo, eligible or
pending sets. The Samples page remains empty while prepare is running and, once
prepare has completed, shows only the final samples selected by WGS analysis.
Projects and FASTQ roots remain server catalog entries. `use_reference` is a
  WGS contract value; only `use_reference` and `algo` are editable. Resolved profile, resources, images and internal paths are
read-only. No raw YAML endpoint is provided.

## 6. Step7 SFS cleanup

Step7 is not part of `bio_wgs`. It is available only to an administrator after
run success, Step5 verification, Step6 materialization, and proof that no CCE
workload is active for the attempt.

The UI requires two confirmations and typing the displayed batch. It submits
only the batch text. The backend loads the frozen binding and generates the
real `DELETE-SFS:<project>/<batch>/<run-id>` confirmation. The maintenance
operation is asynchronous and idempotent, uses the existing audit model, and
records status/evidence without exposing a server path or confirmation string.
Viewer and operator requests are forbidden.

## 7. Platform resources

`platform-metrics-collector` is independent of the task-scoped CCE observer.
It collects:

- CPU, memory, load, disk capacity, disk read/write bytes per second, IOPS, and
  network for `172.17.61.96` and `172.17.61.97` through internal-only node
  exporter endpoints.
- SFS Turbo used capacity/percent, read/write/total bandwidth, and IOPS through
  Cloud Eye.
- OBS used capacity, object count, and source timestamp. OBS has no fixed
  remaining-capacity value and the UI must not invent one.

node200 is only the restricted cloud operator and credential boundary; it is
not a monitored compute node. Airflow, FastAPI, and the browser hold no cloud
credential. `platform_resource_snapshot` upserts one row per resource with a
current payload and a maximum 60-point JSON ring. Collection failure marks the
resource stale/degraded and never changes a WGS run.

`GET /api/platform/resources` is the WGS frontend contract. The historical
`GET /api/system/resources` remains available for compatibility but is no
longer called by the WGS UI.

## 8. Frontend behavior

- Run Tracker columns are Project, Batch, Pipeline, Status, Current stage,
  Stage progress, Runtime, Started, and Finished. QC state is absent.
- Overview shows Batch, release, attempt, Master identity, sample count, and
  family count. It hides Master image digest and WGS QC cards/tabs.
- `Families` is renamed `Samples` and uses only the safe projection.
- Step4 CRAM repair is rendered only when `available=true` or an existing
  repair operation is active. Raw capability reasons are mapped to operator
  language and are not shown as a permanent error panel.
- Workflow Catalog describes WGS 4.2.0, `bio_wgs`, and Step1-Step6, and uses the
  same authoritative progress contract as Run Tracker.
- Missing exact progress is explicitly shown as “Detailed progress
  unavailable”; it never falls back to DAG task percentage.

## 9. Security, deployment, and acceptance

- Docker continues to use external network `192.168.199.0/24`; only
  `172.17.106.10:12959` is published.
- PostgreSQL, Redis, backend, Airflow, observers, collectors, exporters, and
  cloud collection endpoints remain internal.
- Docker logs use rotation. Normal collectors do not emit per-sample, per-file,
  or per-poll logs.
- Deployment backs up biodemo and Airflow metadata and does not delete current
  runs, OBS/SFS data, Docker volumes, or the network.
- Migration `20260901_0013` downgrade is destructive and is fail-closed unless
  an approved rollback explicitly sets `ALLOW_WGS_PRODUCTION_UI_DOWNGRADE=true`.
- T153-T155的禁用态代码已实现并完成现有可运行测试；T156的draft
  preview设计已撤回，改为由DAG执行WGS原生sampleinfo/analysis语义；T157只完成资源快照、
  UI和Step7控制合同，实际node exporter/Cloud Eye采集及Step7运行尚未验收。
- T158不得发布当前worktree，直到上述外部合同、WGS release漂移和BS10610 Docker
  frontend production build均完成验收；本机Node测试不计入验收。真实WGS批次仍需要单独批准。

## 10. Implementation checkpoint (2026-09-01)

Migration `20260901_0013`, stage/Rule projection, safe log index, production UI,
project catalog, platform resource snapshots, and the admin Step7 maintenance
contract are implemented in the T146 worktree. The draft preview implementation
is historical candidate code and must not be exposed by the production UI. The
node200 evidence bridge increments both Rule JSONL and the frozen run's
`analysis.log`, including a read-only terminal reader pass.

Two implementation items are now owned by Airflow and are not external WGS or
cce-pipeline contracts:

- the node200 `obsutil` wrapper and runner aggregation produce
  `wgs-runtime.transfer-progress.v1` without changing cce-pipeline;
- submission runs WGS `sampleinfo` followed by `analysis` inside normal DAG
  prepare and publishes only the final selected samples after prepare.

The candidate catalog is explicitly bound to `wgs-4.2.0-7879718`; it does not
silently follow repository HEAD. Compatibility audit confirmed structured
`ANALYSIS_COMPLETE` support and the new prepare `--algo` option. Execution and
deployment remain separately gated.

The evidence bridge mirrors the bound `analysis.log` and stage worker logs.
Failed-Rule diagnostics use a bounded excerpt of that registered analysis log;
arbitrary logger paths are never made readable and no additional SFS path
registry is required.
