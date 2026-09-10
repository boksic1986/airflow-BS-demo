# Workflow runtime integration

## T255 Heavy I/O producer and release binding

WGS profile r2 selects reviewed CCE0.8.3.post1 and executor0.6.4+biosan5 Master by immutable SWR digest. Optional profile heavy_io limit1..25/mode propagates into the frozen audit contract `{limit,mode,unit:work_pod}` and Master capability1 gate. Enforce mode admits heavy work Jobs through named namespace Leases wgs-heavy-io-00..24; saturation queues without blocking active-job monitoring. Grouped heavy rules count once per work Job. Lease ownership/acquire generation uses resourceVersion CAS; TTL alone never proves a running holder free. Terminal cleanup waits for safe release; receipt recovery binds exact submitted UID/attempt/manifest and requires Job404 and zero Pods.

Master evidence is `<run_root>/evidence/<run_id>/heavy-slot-status.json` with schema wgs-heavy-slot-status.v1. It is per-Master evidence, not an authoritative namespace aggregate. Preserve old frozen profiles/bundles on upgrade. New future prepare uses the independent ctapa CLI interpreter; changing the CLI selection must not replace nipttest or restart a running upload worker. Detailed source/digest/test and paused-production release provenance is recorded under T255 in HANDOFF.

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
