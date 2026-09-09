# Airflow DAG specification

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

Airflow tasks remain project-level. Snakemake rule/sample events come from the
GATK `rule-status` logger and are not expanded into Airflow tasks.

## Failure projection

Terminal Airflow failures must be projected into the business database. An observer or rerun must be able to recover from persisted generation and receipt evidence without launching a duplicate stage.
