# GATK Cloud manual Airflow integration

## Scope and frozen releases

T228 adds a manual-only GATK Cloud adapter to the NGS control plane. T232
rebases the implementation onto Airflow production mainline `b2029f6` while
preserving GATK Cloud
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
- every FASTQ symlink target is below an approved FASTQ root. The initial
  roots are `/sg2/T7new/result1/OutputFq` and `/bi/fastq/T7_Fastq`; both are
  mounted read-only into the backend so absolute links under `a.raw` remain
  resolvable without copying FASTQ data;
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

Step1/Step5 terminal status synchronization also converges the exact directional
TransferJob and releases its owned OBS lease. A validated latest-generation
receipt (analysis/attempt/stage/execution/request hash) is required, including
repeat synchronization after a prior DB/release failure. Missing progress rows
can be reconstructed as terminal without inventing byte/file counts. Old or
nonterminal progress cannot reopen a receipt-terminal GATK transfer. Wrong
attempt/generation or another owner's lease is never reclaimed. A retained
release response fails the DAG release task explicitly instead of reporting
success. An unknown outcome stays retained for investigation; age alone is not
permission to release. No TTL-based forced release is added.

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

GATK and WGS share the one-slot directional OBS upload/download pools and leases.
GATK inherits Airflow global active-run concurrency (production16 verified
2026-09-14); Step2 uses the default pool, not an exclusive GATK pool. Multiple
batch Masters can run concurrently; same-batch identity guards are unchanged.
An existing unused `gatk_cce_runs` pool may remain for audit/rollback. GATK rules do
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

1. migration 0019 and the backend/frontend/Airflow release are deployed;
2. the GATK source commit and runtime profile are verified;
3. the node200 forced command, host key and private runtime env are installed;
4. prepare and CCE dry-run evidence pass;
5. a controlled SCMC smoke completes Step1-Step6;
6. only then set `GATK_EXECUTION_ENABLED=true` for manual confirmation.

Rollback sets the gate to false and recreates the control-plane services. It
does not delete database rows, OBS objects, CCE evidence, runtime bundles or
materialized results.
## 2026-09-14 source configuration compatibility

Preview resolves the project V7.6.X or V7.7.X hg38 version and requires its matching
config.V<version>_hg38.yaml rather than hard-coding7.6.0. Existing hg38/SCMC/plain
sampleinfo naming variants are supported in that order; malformed/unsupported
project versions fail closed. This is already deployed behavior, not a new run.
