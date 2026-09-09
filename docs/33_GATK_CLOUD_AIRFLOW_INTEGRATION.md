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

An operator enters an absolute WES project directory visible on `/sg2`. The
backend resolves the directory and applies the deliberately small Preview
contract:

- the project name contains one `YYYYMMDDX` batch identity;
- the exact `<batch-prefix>.sampleinfo.SCMC.txt` exists as a regular,
  non-symlink file and is readable;
- the file contains the `data ID` column and at least one non-empty, unique
  sample ID.

The backend mounts `/sg2` read-only so projects owned by different teams can
be previewed without adding one Compose mount per owner. Preview does not
require the source config, barcode sidecar or directly named R1/R2 links.
Those workflow-specific checks remain in the existing GATK builder/prepare
runtime after submission.

`POST /api/pipelines/gatk/submission-preview` stores a 30-minute immutable
draft and returns only a draft ID, hash, safe basenames, sample IDs, counts and
validation booleans. It does not return clinical columns or complete FASTQ
paths. The fingerprint covers the resolved project identity, batch, SCMC
sampleinfo SHA256 and selected sample IDs. `POST /api/runs` re-reads those
inputs, compares the hash and returns `409 GATK_INPUT_CHANGED` if they changed.
The immutable runtime request narrows `approved_source_roots` to the exact
selected project directory.

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

The GATK handoff calls the existing builder and the shared nipttest
cce-pipeline 0.8.3 prepare logic. Manual GATK CLI behavior remains unchanged.
The generated CCE bundle,
request, receipts and evidence remain under
`runtime/gatk/<analysis_id>`. Step6 reuses the frozen bundle's
`cce_delivery.materialize_results()` helper but supplies the approved result
destination:

```text
/sg2/50.ctapa/project/HWcloud/WES_Clinical/<batch>/<analysis_id>
```

The destination must exactly match `GATK_RESULT_ROOT/<batch>/<analysis_id>`;
otherwise the runtime fails closed.

For `backend_auto_export`, Step4 may reach OBS before the CCE export backend
has made `payload-manifest.tsv` and `ANALYSIS_COMPLETE` visible. The node200
gate treats only the exact `SFS backend export is not ready in OBS; retry
Step4` result as transient. It polls every 30 seconds for at most two hours by
default (`GATK_PUBLISH_POLL_SECONDS` and `GATK_PUBLISH_WAIT_SECONDS`). All
other Step4 errors fail immediately with captured stdout/stderr. A failed
stage retry creates a new fenced generation in the same analysis attempt; it
does not rerun Step1 upload, Step2 Master creation, or Step3 analysis.
If shared-storage caching briefly exposes a sidecar from the previous
generation, the backend returns pending until the current generation is
visible. It never imports that stale terminal state. A same-generation hash or
execution mismatch, or any future generation, remains a hard identity error.

The final `release_leases` task uses `all_done` so cleanup always runs, then
checks all upstream task instances and fails itself if any upstream task is
failed or upstream-failed. This prevents a successful cleanup leaf from
incorrectly making a failed GATK DagRun appear successful.

The CCE profile sets `latency-wait: 180` because final marker files are written
through shared SFS. This changes only Snakemake's output visibility window; it
does not retry or alter `cloud_gatk_finalize`, relax marker validation, or hide
a genuinely missing output.

When a runtime sidecar becomes terminal without progress fields, the backend
retains the latest valid counters and current rule from logger evidence. The
DagRun failure callback then closes the business projection: the matching
failed rule remains failed, unfinished siblings become canceled, samples
become failed, and terminal Run Tracker rows retain the same stage progress as
Run Detail. A previously successful run is never downgraded by the callback.

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

1. migration 0019 and the backend/frontend/Airflow release are deployed;
2. the GATK source commit and runtime profile are verified;
3. the node200 forced command, host key and private runtime env are installed;
4. prepare and CCE dry-run evidence pass;
5. a controlled SCMC smoke completes Step1-Step6;
6. only then set `GATK_EXECUTION_ENABLED=true` for manual confirmation.

Rollback sets the gate to false and recreates the control-plane services. It
does not delete database rows, OBS objects, CCE evidence, runtime bundles or
materialized results.
