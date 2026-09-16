# Workflow runtime integration

## Pod-exit log collection race (2026-09-16, source only)

The common wgs_evidence_bridge reads directly from a Running Master. If exec
fails, it queries Pod status once. A confirmed absent Pod or the same Pod in
Succeeded/Failed permits the existing read-only reader Job for terminal calls;
nonterminal calls defer to subsequent status/terminal polling. Active/unknown or
different Pods, malformed inventories and lookup failures retain the error.
Only a complete read applies log/rule chunks and advances incremental cursors.
Reader timeout, mount permissions and cleanup are unchanged.

gatk_runtime_gate still requires the runtime's authoritative Master SUCCEEDED
result and existing request/generation validation. Terminal collection failure
or missing rule logs no longer converts that success to failure: existing status
and terminal records retain monitoring_health=degraded, monitoring_error and
message "分析完成，日志采集异常". Healthy collection records healthy monitoring.
Real Master failure or unconfirmed/invalid runtime identity/state remains failure.
No API/schema change, WGS scheduling change or automatic analysis restart.
Validation: BS10610 offline isolated targeted tests, 48 passed. Not deployed.

## WGS resume_stage (2026-09-15, source only)

Backend reserves only the actual stage's new generation, retains old execution/
receipt rows and request-history, and resets that stage's terminal timing.
Subsequent necessary stages register at dispatch. Frozen requests carry
resume_action_id and exact resume_previous_execution. Stale generations cannot
finish or overwrite the current stage projection.

Sibling wgs_resume.py reuses Step1/5 transfer checkpoints, Step4 publishing and
Step6 materialization journals. A live executor keeps its existing worker lock.
Async recovery records a follower inside existing worker.json, waits for that
lock, then archives/translates only the exact original terminal receipt.
Synchronous recovery waits on the same lock. No terminal receipt means explicit
failure. Dead executors archive old sidecars before the recovery branch executes.

Step2/3 query and compare the frozen Master manifest/image. Active/successful
Masters are reused; failed replacement requires inactive exact-owner Pods and
native worker/lock checks. Old evidence is retained before native refresh.
DeleteOptions pins observed UID/resourceVersion. The frozen runtime's low-level
create submits original master-job.yaml and reconciles uncertain responses by
query. Native payload/START handoff is completed idempotently for pre-start Jobs.
Step3 current Master UID fences old failure mirrors. Runtime primitive
availability is checked before replacement.

No Step0, prepare, forceall, OBS-empty precondition, original workflow edit,
on-prem output deletion, pending edit or CCE upgrade. Source inspection used
retained candidate0.8.4, not an asserted live0911A bundle. Production compatibility
and actual recovery require separate approval. Validation:
`releases/2026-09-15-wgs-resume-stage.md`.

WGS-EVIDENCE-20260915 (source only): the observer can recognize a legacy
same-attempt Step1/5 restart from the existing registered request and worker
launch sidecar, including retry_no0. Exact identity/hash and a launch after the
failed projection are required; old status/progress cannot reopen success.
This is read-model recovery only: no gate, receipt format, prepare, pending,
Master or CCE producer changes. Current API group-only evidence with an empty
member inventory remains explicitly unavailable rather than fabricated.


REL-02 (2026-09-15, source only): `wgs_local_runtime_gate.py` initializes
`TZ=Asia/Shanghai` and calls POSIX `time.tzset()` before local dispatch/worker
entry. Background workers inherit it; local analysis subprocess environments
explicitly enforce it. This applies wherever the approved local gate is installed
on selected96/97; it does not enable an unavailable target or redirect preparation.
UTC status timestamps, node200 cloud gate and original WGS scripts are unchanged.


REL-01 (2026-09-15): WGS node200 dispatch reconnects only for proven SSH
pre-execution transport failures, within the original registration/generation.
No node runner, original prepare interface, request/receipt format or pending
behavior changes. Unknown post-dispatch outcomes are synchronized by the
existing terminal-status query and never automatically re-executed. See DAG spec.


GATK September14 status projection preserves measured Step1/Step5 progress and
reconciles only identity-validated latest terminal receipts. Bound rule evidence
uses registered log enrichment for sample identity. No pipeline selection or
local/SGE execution behavior changes. Details: 33_GATK_CLOUD_AIRFLOW_INTEGRATION.md.

## OPT20260912 read-only resource evidence

Heavy v2 snapshot `complete` means complete named Lease inventory, not complete
waiting evidence. Per-Master fresh waiting snapshots must match active Master
mode/limit/run identity; their oldest timestamp is retained independently.
Missing waiting does not discard authoritative reserved holders, including old
holders. Only executor owns acquire/release/reclaim. No executor/Master rebuild,
per-rule admission change or live quota enforcement test is part of this task.
Refresh failure retains last-known snapshot with refresh_failed; API marks it
stale. The canonical backend heavy module is packaged beside the standalone
entry point as heavy_snapshot_core.py to avoid two divergent implementations.

BSS uses a separate hourly daemon and validated numeric JSON spool. The
canonical backend bss_resource_snapshot.py is also packaged beside the BSS
collector. It contains no SDK dependencies. Atomic publication occurs only
after bounded complete pagination,100-ID usage batches and dictionary/Decimal
validation. Empty/malformed/incomplete refreshes cannot erase last-good rows.
Legitimate complete empty package inventory is reported healthy with no rows,
not as zero CPU/OBS allowance. No runtime execution or SFS collector change.

## OPT20260912 monitoring evidence

Logger group starts retain stream-local identity and emit rule_planned member
descriptions with group_member, timing_provenance=group_only and an opaque
execution_group. They do not authorize child starts or terminal propagation.
Observer ignores legacy group-only starts for timing and clears prior
start/end when an explicit same-instance retry starts after a terminal event.
Raw events remain retained. Origin is exposed as role plus opaque stream hash;
no ambiguous Master/worker job-ID merge was introduced. The logger plugin
source is tested but active Master/worker images are not rebuilt or restarted.

WgsStageExecution and GATK PipelineStageExecution retain a reserved
terminal_payload_json._display_estimate_v1 snapshot, written by existing
backend/observer stage transitions only on first running observation. It is
not a receipt or runtime progress measurement and is preserved beside terminal
evidence. Snapshot includes baseline/history execution IDs and generation.
Terminal-only observations never fabricate a start. Same-generation terminal
GATK replay no longer advances terminal time. No migration/DAG change needed;
old executions without a snapshot remain indeterminate on read.

WGS QC display policy is packaged at app/policies/wgs_qc_cc9bde3.json, with
source commit and cfg/g1/g2/QC.smk Git blob hashes. Policy selection never reads
runtime Git or mutable latest source. The same frozen batch supplies QCstat,
private sampleinfo conditions and optional sample.multi.QC.tsv; responses carry
hashes and allowlisted judgments, not private condition rows or peddy identities.
Source aggregate remains unchanged. Historical31de5fb differs in g1/rule code
and intentionally has no inferred current-policy numeric judgments.

## OPT20260912 submission

The additive `test_project` request descriptor freezes original sampleinfo/config
SHA256, ordered sample IDs and FASTQ resolved-path/size/mtime_ns fingerprints.
The test node checks source identity and exclusively creates a relative child
under WGS_test, marked with analysis identity; source results are never copied.
prepare_sampleinfo copies only the frozen table and emits the existing v1
handoff receipt, without metadata lookup or family expansion. Owner analysis
uses this independent outpath, so its prepare/pending_samples.tsv is test-local.
The gate requires exact final selected IDs with no pending/excluded entries,
matches prepared FASTQ targets, and checks generated caller/reference options
before binding Step1-Step6. It retains the standard request v4, prepare receipt
v1, stage-generation and execution-approval contracts. Test mode is CCE-only;
target switching into non-isolated local/SGE gates is server-rejected.
No owner core, formal pending or production workflow is modified.

The requested child contains a frozen `WGS_TEST_<16 hex>` project namespace.
Its basename is the owner-generated cloud project identity; the original batch
and sample table bytes are retained. Owner cc9bde3 uses `project/batch` for OBS,
SFS and linkage suffixes; installed cce-pipeline 0.8.4 derives its batch lock
from SHA256 of that same identity. Thus two tests of the same source do not
share results or locks. Existing Step7 frozen-binding targeting remains intact.

GATK81587fc: Step1 transfer plans/raw evidence are scoped to generation-specific
directories. Explicit foreign execution/generation/hash fields are rejected;
identity-less obsutil rows are accepted only from the generation-private spool.
The legacy current progress publication uses a lock and monotonic generation
check so a late older writer cannot replace an already-published newer one.
Step5 retains its observer-visible legacy progress path. Exact limitations and
regression evidence are in GATK_REVIEW_20260912 and GATK_PORT_REPORT_20260912.
GATK pending OBS export polling and terminal callbacks are confined to its
adapter; no WGS workflow/core rule change is part of this promotion.

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
unavailable; it does not block analysis. OPT20260912 supersedes the duplicate
module packaging with one canonical core and a thin standalone entry point.

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

## OPT20260912 monitoring review corrections

The logger records the full group's rule-name/job-ID inventory as
`execution_group_members` on every group-only descriptive member event. This
supports expansion across paginated Rule API results without inventing child
starts or merging master/worker streams. Existing images do not gain these
fields until separately reviewed activation; historical inventory remains
unavailable. WGS phase inventory pins cc9bde3 rule/*.smk, WGS_pipe.smk and
WGS_cloud.smk source blob IDs in policies/wgs_phases_cc9bde3.json. GATK pins
bd04f6d workflow/SCMC_GATK.smk blob0ee4e0033a1d5e0dbf0e62c0264136749173304a.
The catalogs are display classifications, not scheduling/dependency graphs.
# 2026-09-14 original-file ledger consumer

This release only projects the existing shared pending and retained original
prepare request/receipt/final-sampleinfo files. WGS owns file selection/handoff;
local/SGE behavior and existing execution flow are unchanged. No new lock,
producer journal, binding or real_prepare_only protocol is enabled. Dormant
reader dependencies retained from the deployed package are not rollout approval.
Use docs/WGS_FILE_REFERENCE_MINIMAL.md; register only the approved wgs_files source.
# GATK guarded recovery and maintenance (2026-09-14)

`scripts/gatk_resume.py` is an operator-only same-attempt helper, dry-run by
default. It validates analysis/attempt, explicit binding/contract SHA256,
immutable Master manifest, failed Job UID/resourceVersion and inactive current
and archived Workers/maintenance Jobs. It shares the attempt request directory's
`.maintenance.lock` with Step7. Local pre-refresh evidence and a fsynced recovery
journal precede a Kubernetes DeleteOptions UID/RV-preconditioned replacement.
It invokes the frozen native Step2 (metadata handoff, not FASTQ re-upload), never
Step0 or forceall. Native pre-start rollback semantics remain unchanged.
An unproven replacement UID after a lost response requires reconciliation;
repeating the command never deletes that new UID. Frozen versions are retained.
Control-plane Step3 generation reopening and exact downstream Airflow recovery
are separate actions after the replacement is verified.

GATK `step7_cleanup` is explicit independent maintenance. Its request freezes
the exact binding SHA and latest successful Step6 execution/generation/receipt.
The node gate validates the standard request hash, safe exact attempt paths,
native Master handoff UID, terminal Jobs/Pods and frozen cleanup image/command/
SFS targets. Native Step7 again requires DOWNLOAD_VERIFIED, MATERIALIZED and
no active historical Workers. Unverified cleanup is never enabled. It deletes
only frozen SFS run/linkage and their terminal job/batch-lock resources;
approved local delivery, local evidence, OBS input, release and references remain.
