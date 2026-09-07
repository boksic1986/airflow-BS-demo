# Airflow DAG specification

## Generic contract

Each deployed adapter declares one DAG ID. FastAPI submits through the adapter and stores the analysis-to-DagRun binding. Airflow coordinates project-level stages; rule/file dependency remains workflow-owned.

Only DAGs for deployed real adapters ship in the active tree. Retired demo DAGs and mock runners are not retained.

## Current WGS DAG

`bio_wgs` remains the current production workflow. It preserves the accepted prepare, execution commit barrier, Step1–Step6, Step6 materialization wait, finalize, and maintenance boundaries. CCE and enabled local targets are mutually exclusive branches. Directional upload/download leases and heavy-slot quotas remain independent scheduling controls.

## Failure projection

Terminal Airflow failures must be projected into the business database. An observer or rerun must be able to recover from persisted generation and receipt evidence without launching a duplicate stage.
