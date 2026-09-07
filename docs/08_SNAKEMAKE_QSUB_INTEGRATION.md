# Workflow engine integration

## Boundary

Airflow schedules pipeline-level stages. A registered adapter selects the workflow runner and execution target. Snakemake or another workflow engine owns rule/file dependencies, incremental execution, and rule logs.

The shared platform does not ship a universal mock runner or a pipeline-name-specific qsub profile. A real adapter that supports SGE must provide and validate its own profile before advertising `sge` as available.

## Evidence contract

Workflow runners publish atomic, generation-fenced evidence. The observer validates identity and receipts before projecting rule, sample, QC, transfer, and terminal state into PostgreSQL. Frontend code consumes only that projection.

## Current WGS adapter

WGS uses its accepted runtime gate, rule-status logger, Step1–Step6 receipts, Step6 materialization barrier, and controlled evidence bridge. CCE is the automated target. Local and SGE availability is declared by adapter capability and deployment gates.

Resume and rerun operations reuse the existing workdir and completed outputs. They never default to `--forceall`.
