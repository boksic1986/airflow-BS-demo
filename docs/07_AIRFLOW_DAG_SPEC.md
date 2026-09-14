# Airflow DAG specification

GATK production promotion81587fc adds generation-aware terminal reconciliation:
`bio_gatk` reports failed current attempts through the authenticated internal
dag-terminal endpoint. Runtime status transitions preserve attempt/execution
identity; successful workflow stages are not inferred from a failed transport.
Manual GATK inherits global active-run concurrency; WGS pools and automatic scanning policy are
unchanged. Production activation registers/unpauses bio_gatk but submits no run.

## Generic contract

Each deployed adapter declares one DAG ID. FastAPI submits through the adapter and stores the analysis-to-DagRun binding. Airflow coordinates project-level stages; rule/file dependency remains workflow-owned.

Only DAGs for deployed real adapters ship in the active tree. Retired demo DAGs and mock runners are not retained.

## Current WGS DAG

`bio_wgs` remains the current production workflow. It preserves the accepted prepare, execution commit barrier, Step1–Step6, Step6 materialization wait, finalize, and maintenance boundaries. CCE and enabled local targets are mutually exclusive branches. Directional upload/download leases and heavy-slot quotas remain independent scheduling controls.

## GATK Cloud DAG

`bio_gatk` is a manual-only DAG without a DAG-specific `max_active_runs` override.
It inherits `core.max_active_runs_per_dag` (production verified16 on2026-09-14).
Its ordered graph is
Validate, Prepare, Step1 Upload, Step2 Master, Step3 Monitor, Step4 Publish,
Step5 Download, Step6 Materialize and Finalize. It uses the fixed node200
forced-command runtime. Step2 uses `default_pool`, not `gatk_cce_runs`, so
different batches can submit Masters concurrently. Step1/Step5 share the existing
directional OBS pools and leases with WGS; GATK does not consume the WGS heavy
work-pod quota.

Directional `wgs_obs_upload` and `wgs_obs_download` pools remain one-slot;
durable transfer leases enforce the complete transfer lifetime across reschedules.
They do not serialize Step3 cloud analysis. Existing batch-identity guards remain.

Airflow tasks remain project-level. Snakemake rule/sample events come from the
GATK `rule-status` logger and are not expanded into Airflow tasks.

## Failure projection

Terminal Airflow failures must be projected into the business database. An observer or rerun must be able to recover from persisted generation and receipt evidence without launching a duplicate stage.
# GATK success barriers (2026-09-14)

`submit_step2_master` requires both `wait_step1_upload` success and input-slot
release. `materialize_step6_results` requires both `wait_step5_download` success
and result-slot release. Slot releases retain `ALL_DONE` so failures free capacity,
but release success alone must never launch later pipeline work.

GATK release callables reject `retained=true` responses. Already-released leases
remain an idempotent success. Step1/Step5 status polling converges transfer state
from a validated terminal receipt before declaring ready, including replay of an
already-terminal stage after interrupted synchronization.
