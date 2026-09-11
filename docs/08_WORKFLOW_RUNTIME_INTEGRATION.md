# Workflow runtime integration

WGS4.2.1 uses the existing prepare request/receipt v1 schema and generation fence,
like4.2.0. Release cc9bde3 maps to the existing directory named wgs-4.2.0 (name is
not version authority), with templateV4.2.1 and separate wgs-4.2.1-r1 profile.
Catalog constructs versioned analysis/sampleinfo names from release.version.
Old profiles and frozen attempt bindings remain unchanged. cce-pipeline0.8.4,
Master Heavy25/enforce and the WGS-prepare/nipttest-monitor interpreter split stay.


2026-09-11 Step7 accepts the global approved operator configuration or the exact current attempt's `release-runtime/cce-operator.yaml`. The latter must equal the prepare transformation of the approved configuration (allowlisted release repository and obsolete transfer fields removed). Foreign attempt paths, symlinks, absent files and changed config remain rejected. Cleanup never rewrites the frozen config or widens SFS target scope.


2026-09-11 Step6 repair: normalization applies only to current validated materialization journal's published top-level result entries (directory or regular file) and the new completion marker. Batch runtime/config/cache entries are outside delivery ownership; shared group/mode contract is not relaxed. Resuming a prepared+committed journal does not download or extract again. Original delivery identity guards remain. Node200 request reader tolerates FileNotFound visibility races for at most30seconds per invocation; malformed/foreign identity and symlink errors are not retried. Legacy0909B terminal Step6 sidecar retained in scoped history under worker/status locks before same-attempt Airflow recovery. No broad reset or status fabrication.

2026-09-11 prepare handoff updates local pending ledger for cloud as well as standalone/SGE, before success receipt. Common path uses exclusive flock/read latest/merge/fsync/atomic replace, preserves full/extra columns and removes only selected exact identity (order/task group+sample+batch+data identity). Conflicting nonempty source fields fail needs review; no mtime arbitration or family-wide deletion. Private artifact may carry full unresolved ledger; safe receipt decisions describe only current selection. Observer adds independent attempt-fenced10s Airflow status loop while retaining evidence cadence; network errors preserve last authoritative run state. See [release evidence](selection-refresh-20260911.md).

Heavy global display producer (2026-09-11): `heavy_global_snapshot.py` runs
read-only kubectl queries every60s on node200/t640 with existing nipttest and
CCE config. Atomic snapshot goes to the approved runtime/cce-evidence root.
It neither acquires/releases Leases nor restarts workloads. Startup launcher
`/home/ctapa/.config/airflow-wgs/start_heavy_slot_collector.sh` uses flock to
avoid duplicate collectors. This is a detached process, not a boot service;
after execution-host reboot run this launcher again. Failure/absence becomes
unavailable; it does not block analysis. Backend deployed module and standalone
collector must remain identical when changing snapshot validation.

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
# Prepare interpreter boundary (2026-09-11 production update)

The restricted gate invokes WGS `prepare_wgs_batch.py` sampleinfo/analysis/all
with `/bi/software/mamba/envs/WGS/bin/python`. This does not change the gate's
`WGS_PYTHON` launcher or evidence-bridge interpreter, `CCE_PIPELINE_BIN`, or
Cloud Eye collectors, which retain the approved nipttest environment. CCE
bundle generation receives the explicit CLI path and preserves its associated
interpreter. Do not replace global PATH or reinterpret existing frozen bundles.
