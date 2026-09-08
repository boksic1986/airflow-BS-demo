# Workflow engine integration

## Boundary

Airflow schedules pipeline-level stages. A registered adapter selects the workflow runner and execution target. Snakemake or another workflow engine owns rule/file dependencies, incremental execution, and rule logs.

The shared platform does not ship a universal mock runner or a pipeline-name-specific qsub profile. A real adapter that supports SGE must provide and validate its own profile before advertising `sge` as available.

## Evidence contract

Workflow runners publish atomic, generation-fenced evidence. The observer validates identity and receipts before projecting rule, sample, QC, transfer, and terminal state into PostgreSQL. Frontend code consumes only that projection.

## Current WGS adapter

WGS uses its accepted runtime gate, rule-status logger, Step1–Step6 receipts, Step6 materialization barrier, and controlled evidence bridge. CCE is the automated target. Local and SGE availability is declared by adapter capability and deployment gates.

For a large CCE run, the evidence bridge must not list every run-bound Job as one full JSON response. It reads the server-side Job table, projects completed rows from that compact response, and fetches full JSON only for non-terminal Jobs. A transient `kubectl query failed` from Step3 status collection is retried within the existing monitor timeout; it does not by itself prove that the frozen Master or workflow failed. Relaunching the monitor reuses the same Master identity and does not rerun Step1 or Step2.

Resume and rerun operations reuse the existing workdir and completed outputs. They never default to `--forceall`.
