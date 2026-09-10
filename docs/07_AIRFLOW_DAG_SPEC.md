# Airflow DAG specification

## T248 automatic WGS 4.2 prepare path

`auto_dispatch` uses the same staged 4.2 prepare sequence as `three_stage`:
`prepare_sampleinfo`, `prepare_analysis`, execution commit and Step1. The UI
approval sensors remain automatic for this mode. Backend prepare artifact
projection must preserve `submission_phase=approved`; only interactive
`three_stage` submissions transition to `config_review` and
`execution_review`.

Step1's predecessor is `prepare_analysis` for both staged modes. Legacy modes
retain the single `prepare` predecessor. Directional transfer leases still
serialize Step1/Step5 independently from the 25-workload CCE Heavy Slot quota.

## T242 WGS 4.2 prepare boundary

The DAG shape is unchanged. New 4.2 prepare stages use generation-scoped
handoff requests and validate receipt identity, artifact keys, and hashes.
Historical 4.1.1 runs continue from an existing frozen binding; unfrozen
historical reprepare is rejected. The adapter does not inspect Git or validate
pipeline/profile contents at runtime.

## Generic contract

Each deployed adapter declares one DAG ID. FastAPI submits through the adapter and stores the analysis-to-DagRun binding. Airflow coordinates project-level stages; rule/file dependency remains workflow-owned.

Only DAGs for deployed real adapters ship in the active tree. Retired demo DAGs and mock runners are not retained.

## Current WGS DAG

`bio_wgs` remains the current production workflow. It preserves the accepted prepare, execution commit barrier, Step1–Step6, Step6 materialization wait, finalize, and maintenance boundaries. CCE and enabled local targets are mutually exclusive branches. Directional upload/download leases and heavy-slot quotas remain independent scheduling controls.

## GATK Cloud DAG

`bio_gatk` is a manual-only DAG with `max_active_runs=1`. Its ordered graph is
Validate, Prepare, Step1 Upload, Step2 Master, Step3 Monitor, Step4 Publish,
Step5 Download, Step6 Materialize and Finalize. It uses the fixed node200
forced-command runtime and `gatk_cce_runs` pool. Step1/Step5 share the existing
directional OBS pools and leases with WGS; GATK does not consume the WGS heavy
work-pod quota.

Each runner task passes the stage generation returned by the backend to the
forced-command runtime. Prepare retries reuse the immutable generation-1 input
request but write a new generation-specific status; older failed sidecars cannot
satisfy the sensor. Child-process stderr/stdout tails are retained in the stage
status for operator diagnosis.

Step3 accepts the legacy JSON status and the cce-pipeline 0.8.3 key/value
status. Both formats must provide an authoritative Master terminal/running
state; completed/total rule counts and the current rule group are projected
when present. Format parsing does not replace the Kubernetes API source used by
cce-pipeline or the independent logger evidence bridge.

Airflow tasks remain project-level. Snakemake rule/sample events come from the
GATK `rule-status` logger and are not expanded into Airflow tasks.

The DAG-level failure callback reports the attempt and failed task IDs to the
internal GATK terminal endpoint. Callback delivery is best effort so a backend
outage cannot conceal the original Airflow failure. Backend reconciliation is
idempotent and uses the failed runtime stage as the rule/sample terminal-state
authority.

## Failure projection

Terminal Airflow failures must be projected into the business database. An observer or rerun must be able to recover from persisted generation and receipt evidence without launching a duplicate stage.
