# GATK Cloud manual Airflow integration

## Scope and frozen releases

T228 adds a manual-only GATK Cloud adapter to the NGS control plane. The
implementation is based on Airflow `0e2cab3` and GATK Cloud
`bd04f6d6020ec3795268af7bee1265963cc652c4`.

The first release is fixed to:

- pipeline ID `gatk` and DAG ID `bio_gatk`;
- runtime profile `gatk-scmc-v7.6.0`;
- CCE execution and Snakemake target `cloud_gatk_all`;
- SCMC samples selected by the existing GATK builder;
- no automatic intake, sample deselection, config editor, local/SGE target, or
  clone reanalysis.

## Submission contract

An operator enters one directory below `/sg2/21.lijing/WES_Clinical`. The
backend resolves the directory without following it outside the configured
source root and validates:

- `<batch-prefix>.sampleinfo.txt`;
- `config.V7.6.0_hg38.yaml`;
- `sample2hospitalBarCode.txt`;
- one R1/R2 pair for every locked SCMC sample;
- every FASTQ symlink target is below an approved FASTQ root, initially
  `/sg2/T7new/result1/OutputFq`;
- the sampleinfo, SCMC config and barcode sets are identical.

`POST /api/pipelines/gatk/submission-preview` stores a 30-minute immutable
draft and returns only a draft ID, hash, safe basenames, sample IDs, counts,
bytes and validation booleans. It does not return clinical columns or complete
FASTQ paths. `POST /api/runs` re-reads the source, compares the hash and returns
`409 GATK_INPUT_CHANGED` if any protected input changed.

The confirmation transaction locks the draft and takes a PostgreSQL advisory
lock for the batch. Only one GATK run may be created for that batch. A failed
run is retained for evidence and is not replaced by an independent clone.

## Runtime architecture

`bio_gatk` is independent from `bio_wgs` but uses the accepted Step1-Step6
shape:

```text
Validate
  -> Prepare GATK contract
  -> Step1 Upload
  -> Step2 Master
  -> Step3 Monitor
  -> Step4 Publish
  -> Step5 Download
  -> Step6 Materialize
  -> Finalize
```

Airflow calls a fixed OpenSSH alias and forced-command gate on node200. The
gate accepts only a GATK analysis ID, attempt and enumerated stage. It reads
immutable requests below the configured GATK runtime root; no request may
provide an arbitrary command.

The GATK handoff calls the existing builder and cce-pipeline 0.8.2 prepare
logic. Manual GATK CLI behavior remains unchanged. The generated CCE bundle,
request, receipts and evidence remain under
`runtime/gatk/<analysis_id>`. Step6 reuses the frozen bundle's
`cce_delivery.materialize_results()` helper but supplies the approved result
destination:

```text
/sg2/50.ctapa/project/HWcloud/WES_Clinical/<batch>/<analysis_id>
```

The destination must exactly match `GATK_RESULT_ROOT/<batch>/<analysis_id>`;
otherwise the runtime fails closed.

## State and evidence

GATK writes append-only stage attempts to `pipeline_stage_execution`, not
`wgs_stage_execution`. Every stage is fenced by pipeline, analysis, attempt,
stage, generation, request hash and predecessor receipt.

Step3 combines three authorities:

- Kubernetes Master/worker UID, resourceVersion and terminal state;
- `rule-status` JSONL for rule, sample, job ID, timestamps and logs;
- `ANALYSIS_COMPLETE` plus `payload-manifest.tsv` for successful delivery.

The operator phase projection is `FASTQ QC`, `Mapping`, `MarkDuplicates`,
`GATK`, `chrM realignment`, and `Delivery`. Terminal Step3 is rejected when no
logger JSONL exists. The Run Detail workspace, Rules, Master, Transfers, Logs
and Files views use the same database projections as WGS while preserving the
GATK pipeline namespace.

GATK and WGS share the directional OBS upload/download leases. GATK has its
own one-slot `gatk_cce_runs` Airflow pool and `max_active_runs=1`. GATK rules do
not consume the WGS 25-slot heavy-I/O quota until a separate I/O study defines
their classification.

## Configuration and safety gates

`GATK_EXECUTION_ENABLED=false` is the deployment default. The repository
contains `config/gatk_runtime.node200.env.example` without credentials. The
installed private file is read by the forced-command wrapper and must be mode
0600. OBS, CCE and cloud credentials remain in approved node-local files and
must never be copied into Git, API responses or validation logs.

The WGS intake scanner remains WGS-only. GATK has no discovery or scheduled
submission path. Enabling GATK requires all of the following:

1. migration 0018 and the backend/frontend/Airflow release are deployed;
2. the GATK source commit and runtime profile are verified;
3. the node200 forced command, host key and private runtime env are installed;
4. prepare and CCE dry-run evidence pass;
5. a controlled SCMC smoke completes Step1-Step6;
6. only then set `GATK_EXECUTION_ENABLED=true` for manual confirmation.

Rollback sets the gate to false and recreates the control-plane services. It
does not delete database rows, OBS objects, CCE evidence, runtime bundles or
materialized results.

## BS10610 disabled rollout

The control-plane-only T228 release is deployed at
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/6d3bb184c597-t228-gatk-disabled`
with `GATK_EXECUTION_ENABLED=false`. Migration 0018, `bio_gatk`, the frontend
submission form and the one-slot GATK pool are present, but confirmation cannot
create executable work while the gate is false.

`/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud/runtime/gatk*` is read-only and
was not present on BS10610 during rollout. The disabled release uses
project-local `shared/gatk-runtime` and `shared/gatk-evidence` mounts only to
start and validate the control plane. Do not enable execution until the
node200 forced-command runtime and BS10610 resolve the same immutable request,
status, binding and evidence files.

The first live preview probe used the documented 20260816A source and failed
closed because one selected SCMC R1 file was absent. This is expected input
validation, not a platform error. Select a source project with complete current
R1/R2 links before prepare or CCE smoke validation.
