# Workflow runtime integration

## Boundary

Airflow schedules pipeline-level stages. A registered adapter selects the
workflow runner and execution target. Snakemake or another workflow engine owns
rule/file dependencies, incremental execution and rule logs.

The current adapters are WGS and test-only GATK. WGS production uses the
approved CCE runtime; local targets remain explicit, gated capabilities. GATK
does not acquire production authority merely because its adapter exists in the
repository.

## Evidence contract

Workflow runners publish atomic, generation-fenced evidence. The observer
validates identity and receipts before projecting rule, sample, QC, transfer
and terminal state into PostgreSQL. Frontend code consumes only that projection.

For large CCE runs, the evidence bridge reads compact server-side Job state,
projects completed rows and fetches full JSON only for non-terminal Jobs. A
transient Kubernetes query failure does not by itself prove workflow failure.
Relaunching a monitor reuses the same Master identity and does not rerun Step1
or Step2.

Resume and rerun operations reuse the existing workdir and completed outputs.
They never default to `--forceall`.

Environment, path, identity and release selection follow
`docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`.
