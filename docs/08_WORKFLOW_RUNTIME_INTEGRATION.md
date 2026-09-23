# Workflow runtime integration

## Task4 selected Master downstream and binding export (source only, 2026-09-24)

Native08c6cda internal Step4/Step5/download_snakemake_logs accept the selected
Master bundle and expected UID together. Original input hashes must match, native
success must validate, and any live Master must be the same inactive successful
UID. Missing Job alone is never success. Log export rechecks after reading.
Publication, cloud_delivery and log archives retain the original bundle root;
Step6 keeps its original result location. Defaults and CLI flags are unchanged.

WGS/GATK Resume internal return metadata now includes cce_master_binding schema2
only after validated native handoff. It contains platform_execution separately
from native fields (native request_hash/execution_generation, Job/Pod UID, run and
input hashes), plus source_bundle/selected_bundle. cce_master_submit_execution_id
comes from that validated platform identity. It is not copied from browser JSON,
is not an inactivity seal, and does not activate the older draft automatic reader.
Normal gate persistence/forwarding and trusted all-writer/storage closure remain
required before manual acceptance and TTL artifacts. No public API/schema change.

## Task4 GATK dispatcher fence (isolated source, 2026-09-24)

Step1–6 use request-adjacent .launch.lock, .worker.lock and .worker.state.json.
The existing restricted start/worker entry persists an intent before Popen and
serializes worker execution; same identity reattaches or returns its terminal.
Dispatcher identity includes analysis/attempt/stage/generation/execution/hash;
process identity includes PID, boot ID and start time. Stale generation cannot
publish success/failure over a changed request. Unknown spawn, stopped parent
without final receipt, and incomplete legacy identity require reconciliation;
none authorizes a new writer. No public API/schema or Prepare/Step7 changes.
This supplies process exclusion only, not storage/all-writer activation proof.

## Task4 initial Master identity binding (isolated source, 2026-09-24)

User-approved native Step2 addition accepts an internal platform_execution and an
independent submission_view. It neither mutates frozen bundles nor grants launch
authority. Platform identity contains pipeline, analysis_id, attempt, execution_id,
stage, generation and request_hash; initial stage must be step2_master. The native
generation remains1 even if the platform stage generation differs. Its native
request_hash includes the platform identity, but is NOT the platform request hash.
Validated startup/terminal evidence carries both; Worker phase context continues
using the native digest and phase-suffixed execution_id.

Existing WGS/GATK Resume capabilities now forward an optional explicit new platform
identity into the native replacement view and action journal. A platform-bound
source requires it; replay with another identity is rejected. Unbound old evidence
is never retroactively attributed. No public API, default CLI, image or production
gate is changed. Trusted writer/storage/all-writer/downstream activation remains
Task4 work, so this is not full manual/automatic recovery acceptance.

## Task3 internal Resume capability (source accepted, 2026-09-24)

Optional internal RecoveryCapability validates native final bytes, both full
inventories and an authenticated caller-supplied canonical-directory mapping;
writers_protocol=2 and inactive dispatcher are required. It feeds original
directory-lock CAS and adapter journals, not a public request or new CLI flag.
Native _advance_recovery_view preserves original bundle and CREATE intent,
returns the derived bundle for the caller, and retains the original deadline.
Started journal requires START_CONFIRMED; missing created/started handoff or
regressed started evidence blocks. GATK rechecks maintenance/OBS before handoff.
Task4 must supply authenticated callbacks and propagate the selected view through
the service/stage paths. No production/default CLI caller is enabled here.
Source wiring passed29 BS10610 synthetic composition cases and5 affected
checks; capability6 passed separately. Task3 source acceptance does not enable
production or replace the remaining Task4 authenticated integration gate.

## P0-2 Task3 final-inventory/view contracts (2026-09-24, source only)

Approved native `_prepare_recovery_view` derives a separate manifest with next
generation and request-hashed recovery_context; original payload/config/bundle
bytes are unchanged. View receipt verifies input/derived hashes and action on
replay; its MASTER_HANDOFF owns a separate UID/deadline. Not launch authority.
Master wraps preflight and analysis with distinct plugin execution contexts;
post-child snapshot `recovery-final.json` includes both phase journals/checkpoints,
exact Worker terminal records/candidates and final jobs.ndjson. RUN terminal binds
submission_snapshot_sha256 and submission_inventory_complete; evidence_complete
remains false (process evidence cannot prove live Pods/other dispatchers inactive).
`_recovery_final_evidence` validates current handoff, confirmation, terminal,
snapshot hash and native phase exit agreement from an existing mirror; no helper
Job. `validate_final_submission_snapshot` consumes actual producer records and
allows zero submissions only inside this final scope, rejecting malformed present
candidates. `probe_final_workloads` checks full run-label lists plus exact names;
missing Workers need exact persisted terminal, surviving/unbound work and partial
pages block. These read-only helpers do not authorize dispatch or replace Task4
trusted canonical storage/legacy mapping/all-writer binding. Resume side-effect
integration remains Task3 work; no production/default CLI activation.

## P0-2 Task3 compatible readers (2026-09-23, development only)

Resume may use `_recovery_query(config, *arguments)` from compatible runtime:
successful exact-name empty GET means absent; failed GET raises a privacy-safe
classification; incomplete lists never mean empty. Frozen bundles stay intact.
WGS v2 uses `_finish_master_handoff` and the original confirmation deadline.
GATK reuses its own validated active v2 Master through the same native primitive.
Live Complete alone is insufficient: `_recovery_native_success(bundle, contract,
job_uid)` reads an existing hash-checked mirror, matches handoff/digests/UID,
START_CONFIRMED, RUN_COMPLETE, native stage exits and workflow completion.
It creates no helper Job and does not prove complete Worker/dispatcher finality.

Failed v2 replacement blocks before mutation pending final submission inventory
and a next-generation derived recovery view. Directory-lock-v2 is not connected;
full inventory/storage/legacy mapping and Task4 authenticated/all-writer closure
remain required. No TTL, automatic policy or production activation.

## P0-2 Task3 guard checkpoint (2026-09-23; consumer closure pending)

WGS existing recovery journal no longer grants a second CREATE after
`submitting`, `created` or `started` when the Master is absent. Only fresh Step2
or the matching pre-submission deletion states retain existing creation behavior;
unknown transmission+404 requires reconciliation, not a new submission. This
also blocks deletion/recreation when that unknown submission later appears Failed.
No new same-action generation is inferred from the delayed failure. This
does not yet accept durable terminal evidence for reclaimed Masters. A fresh
exact Master UID/resourceVersion read precedes UID/RV-conditional DELETE.
Journal updates preserve existing fields and fsync the owner-only exclusive
partial file, replacement and parent directory; stale partial files fail closed.

Both existing Resume helpers request unchunked Master Pod lists and reject
continuation tokens/nonzero remainingItemCount or malformed lists rather than
treat an incomplete empty page as no active Pods. GATK archived Worker queries
accept only explicit SUCCEEDED/FAILED, no longer NOT_FOUND. Task2 persisted
Worker terminals are not consumed here yet, so absent archived Workers remain
blocked until the compatible identity-bound evidence reader is connected.
These are source guard fixes, not a complete inventory/finality proof.

No API/DB/DAG changes, automatic enablement, bundle edits or deployment. The
remaining Task3/4 work must connect START_CONFIRMED, trusted native success,
complete Worker/live inventories and directory-lock callbacks. Step7 cleanup
and local directory removal alone still do not implement platform same-batch
recreation; registration/snapshot uniqueness and history reuse need separate
scoped work. Do not remove audit history or infer unlocked state from absence.

## P0-2 Task2 source primitives (2026-09-23; consumers not yet enabled)

Plugin5b5d7ee/0.6.4+bs8.dev1 extends accepted bs7 journal admission with atomic
`worker-terminal/<job_uid>.json` before Snakemake terminal callbacks. Schema1
binds context_sha256, run_id, attempt, execution_generation, master_uid,
namespace, job_name/job_uid/job_attempt, existing submission_identity,
terminal_state, safe reason and observed_at epoch. Exact Complete/Failed Job
condition required; bare counters/Pod exit/404 cannot prove terminal. Foreign,
conflicting or partially published records block. One validated journal view
per poll; cached terminals are reported before quota/control queries. Quota
claims are not released from this evidence alone; existing quota checks remain.
This does not seal orphan-Pod/whole-run quiescence or enable another Executor.

cce-pipeline7926496 adds optional internal lock_context/journal/save_journal/
verify arguments to original claim/release helpers. V2 directory key protects
same-path writers regardless of batch/entry; logical identity includes pipeline,
analysis_id/attempt/run_id/config digest. Generation/action/Master UID is current
ownership, including pending UID and its one confirmed binding. Existing journal
stores immutable CAS intent before writes, carrying UID/resourceVersion. Release
sets a fenced RELEASED record, not delete/recreate; same logical run requires
next generation, and no Master ownerReference can trigger GC unlocking.

For historical reruns, preserve frozen config/project/history. Trusted recovery
code must map the old lock to the original directory/owner and prove stopped
dispatch/Master/Workers, then CAS its legacy key into a snapshot-preserving guard
before acquiring the v2 directory key. Unmodified CLI sees a foreign guard owner
and cannot inherit/release it. Unknown mapping remains blocked. This is not a
complete mixed-version solution: **all** writers for the directory must use
compatible entry and release paths, including downstream stages. The internal
writers_protocol2 capability is not a browser override or rollout authorization.
Actual mounted storage alias resolution, verifier, fsynced existing journal
callbacks and frozen-runtime wrappers remain Tasks3/4. No current caller opts
in; artifacts/TTL remain Task5. No API/DB/DAG or clinical workflow change here.

Producer details: plugin docs/P02_WORKER_TERMINAL.md and cce-pipeline
docs/architecture/directory-lock-v2.md. BS10610:15 Worker +17 lock tests and
5 +3 affected legacy cases passed; no production rerun/lock migration performed.

## P0-2 Task1 Master producer (2026-09-23, source only)

Pinned cce-pipeline83e7adb successor source on
`jiucheng/runtime/p02-master-handoff-20260923` extends existing MASTER_HANDOFF
and native terminal files. Mapping is documented in that source's
`docs/architecture/master-handoff-v2.md`; manifest handoff-version2 is explicit.
Binding: frozen project/batch/run_id, attempt, generation, exact Job/Pod UID,
request/config/manifest/metadata digests, and one persistent600-second deadline.
START_SENT is possible execution, not acknowledged start. The Master validates
input, atomically excludes a second same-Pod process and writes START_CONFIRMED
before Snakemake. Lost response/control restart reads evidence without another
START or metadata transmission; on-time ack remains valid after the deadline.
Completed Pods use the existing persistent reader. Missing confirmation is
handoff_timeout, not biological rule failure or permission to replace a Master.

Trusted catchable setup/analysis failure and native success use the original
terminal writer and success criteria, now with UID/generation/hash/root-cause
binding and per-Master archive. Process evidence_complete=false intentionally;
Worker quiescence, Kubernetes finality and directory ownership are not proven.
Failures before trusted identity, hard kill/OOM and missing evidence remain
unknown. No Airflow API/DB/DAG change in this task; authenticated Resume consumers
remain Tasks3–4. Old bundles are not rewritten. Paired image/controller artifact
validation and TTL remain Task5; no shared install or automatic activation.

## P0 runtime receipt projection fence (2026-09-23, source only)

WGS stage-status ingestion holds a refreshed AnalysisRun FOR UPDATE lock from
active-attempt validation through stage transition and projection. It refreshes
the matched execution before applying the existing terminal transition rules.
GATK stage-status sync takes the same refreshed run lock after its separate
evidence ingestion sessions, refuses a non-current attempt, and refreshes the
latest execution. A caller's cached running object cannot replace a durable
success with a late failure. Older-generation receipts still do not project.
No schema, API shape, generation allocation, lease policy or retry change.
BS10610 synthetic tests cover stale identity-map state, old attempt/generation
and current failure. PostgreSQL concurrency, other observer evidence paths and
automatic adapter/dispatch integration remain unaccepted; policy stays off.

## bs7 control inventory acceptance (2026-09-23, source only)

Control candidates now reconcile against the existing submission journal,
checkpoint and admitted schema2 manifest. Each referenced Worker must have a
unique successful CREATED/ADOPTED UID under the same frozen context. A null
candidate UID does not erase that proven UID; a conflicting UID rejects.
Missing/unresolved submissions, missing manifest membership or any simultaneous
FAILED submission reject. No control fault is written as a fake submit event.
The inventory's executor_failure_count counts candidate faults, not fabricated
submission failures. This snapshot still proves neither finality nor full history.

Actual plugin0.6.4+bs7 source25297f971dd463176d5fdc07908a60095ade50ea,
wheel SHA256 2ad4aa737e6f34930b6832e3ce69edd9ee64867cc9c7ce0c1bcb4c455cdbae86,
generated four WGS/GATK GET Lease/Pod LIST fixture scopes. GET follows successful
CREATE; LIST follows lost-response ADOPT; each retains one manifest Worker and
the unchanged real producer submission records. Platform acceptance pins the
fixture manifest/provenance hashes in test_cce_recovery_bs7_contract.py.
BS10610:34 targeted inventory checks and4 actual-fixture checks passed. Separate
actual-wheel build validation passed52 affected plugin checks. bs6 unchanged.

No terminal seal was generated. Candidate-only consumption still rejects;
positive terminal tests are synthetic scaffolding. Trusted terminal closure,
binding, dispatch, observation projection and Step4 acceptance remain pending.
No policy enablement, production deployment or installation into active images.

## P0 quota-read candidate contract (2026-09-23, isolated source only)

Agreed plugin contract adds executor-control-failure.json with schema
snakemake.kubernetes.executor-control-failure.v1, the same ten frozen identity
fields, observed_epoch, automatic_recovery_allowed=false,
requires_master_terminal=true and cumulative nonempty failures. This is a
candidate, not an audit/footer, finality seal or permission to restart.

Each failure uses HEAVY_SLOT_API_UNAVAILABLE, phase=heavy_slot_refresh,
transient_reason=CONNECTION_REFUSED, retry_scope=same_operation,
operation_attempts integer1..3, retryable/exhausted=true, creation_state=UNKNOWN,
exact worker_name and explicitly nullable worker_uid. Supported reads only:
read_namespaced_lease with kind Lease, exact resource_name and null selector;
list_namespaced_pod with kind Pod, null resource_name and exact
job-name=<worker_name> selector. No writes, broad namespace list or generic500.
UNKNOWN is not a submission failure or evidence that the Worker is absent.

The internal consumer validates these fields separately from CREATE failures.
Its still-draft terminal contract requires fatal_source=executor_control and
the same cumulative executor_failure_count, bound candidate digest, complete
failure/Worker accounting and zero active/unresolved work. A candidate alone,
unknown inventory or mixed fatal sources never authorizes recovery. The bounded
reader requires exactly one candidate file, checks its filename/schema pairing
and directory stability as well as existing nofollow/file fingerprints.

The initial slice had synthetic-only acceptance; actual bs7 artifact/fixtures
and control inventory compatibility are now covered by the acceptance above.
Trusted terminal closure, binding and dispatch remain unconnected.
No adapter/API/DB wiring or policy enablement. bs6 remains immutable. All allowed
future categories share the existing two60/180-second attempt reservations.

## P0 Airflow cleanup fence (2026-09-23, source only)

External DagRun release/deactivate requests now use the same current recovery
authority as failure callbacks, under a refreshed AnalysisRun lock. This does
not alter runtime receipts, observer ingestion, OBS terminal evidence, slot
counts or the release primitive. No workflow source/image/plugin change.
Partial WGS release commits inside the existing primitive, so its follow-on run
projection obtains a fresh lock and repeats the identity check. Observer drain
is independently fenced even if release previously succeeded. Synthetic tests
prove endpoint behavior and forced interleaving, not PostgreSQL concurrency or
trusted runtime terminal closure; automatic policy remains disabled.

## bs6 candidate compatibility (2026-09-23, isolated acceptance)

Actual plugin0.6.4+bs6 commit0b19bb605cdff619a7f09b34a6fe774e4b43d357 keeps
submit-context.v1, submit-event.v1 and executor-failure.v1. New category
WORKER_SUBMIT_GUARD_FAILED is UNKNOWN/retryable=false, not a recovery allowlist
entry. Existing consumer and inventory validators reject it without code changes.
WGS/GATK admission candidates remain compatible with the draft consumer contract.
Four actual-wheel-generated fixture scopes and two category-only negative checks
passed14 tests on BS10610. Wheel, fixture checksum manifest and provenance are
pinned in backend/tests/test_cce_recovery_bs6_contract.py; source bytes untouched.

Candidate-only inputs reject. Positive tests use explicitly synthetic terminal
objects solely to isolate contract compatibility, not to attest Master termination,
complete failure history or eligibility. No new terminal producer was delivered;
earlier proposed extra Master audit implementation below is not current approved
scope. Missing complete trusted evidence still refuses automatic recovery. No
service deployment, API/DB change, plugin installation or automatic enablement.

## P0 Master failure detail (source only, 2026-09-23)

The UID-bound workload probe now adds `master_job_condition` (type/reason) and
`master_pods` keyed by each observed owned Pod UID. Each Pod contains its name,
phase/reason and main/init/ephemeral container exit code, reason, signal,
restart_count and last terminated state. Existing bound Master exit-code output
is preserved. Missing fields remain null; unknown reason strings become Unknown.
Only fixed Kubernetes reason codes are retained, never message/stderr/credentials.
Conflicting Failed conditions or invalid restart/termination data reject.

BackoffLimitExceeded is a Job-controller terminal symptom, NOT the underlying
cause and NOT a third recovery allowlist entry. Pod OOMKilled/Error evidence may
coexist and must remain visible. Restart counts/lastState are observations only:
lastState is not a full restart history, and deleted/TTL Pods are not reconstructed.
The eventual Master audit/terminal writer still must prove complete cause coverage;
these fields neither emit a seal nor permit recovery. No API/DB projection or
production deployment is included.34 affected synthetic checks passed on BS10610.

## P0 submission inventory and workload reconciliation (source only)

`scripts.cce_recovery_inventory.validate_submission_inventory` consumes trusted
bound bytes for submit-events.ndjson, journal-state.json, executor-failure.json
and the schema2 admitted Worker manifest. It checks exact context/types, complete
NDJSON records, duplicate JSON keys, producer chained hash/byte/record checkpoint,
one intent per Worker, monotonic bounded requests, frozen token/spec/job-attempt,
admission UID, and one-to-one cumulative failure/manifest membership. Partial,
unknown, conflicting or extra/missing evidence fails closed. Repeated manifest
entries currently reject rather than silently deduplicate.

`probe_submission_inventory` derives every Worker identity from that validated
snapshot and calls the existing UID-bound read-only probe. No arbitrary Worker
subset parameter, writes, delete, seal or recovery authorization. Raw-byte hashes
returned here are snapshot bindings, distinct from the canonical candidate JSON
digest used by the backend terminal validator. A future trusted terminal writer
must bind the FINAL snapshot plus Master error audit; checksums are neither
writer authentication nor proof that an earlier consistent snapshot is final.
No current restricted-runner/adapter entry invokes the composed helper yet.

Missing/terminal workloads establish no-active-work observations only, not zero
historical rule failures. Every admitted Worker needs trustworthy terminal/history
accounting before a positive recovery seal; TTL/deletion and missing evidence
remain unknown. Cached Master source review (Snakemake9.24.0+biosan1) confirmed
SubmissionFailure can bypass JOB_ERROR; rule-status drops ERROR and logger close
can suppress write/flush failures. Existing generic RUN_FAILED is insufficient.
Trusted Master audit producer/footer and explicit source coverage remain pending.
26 focused BS10610 checks passed, including two real producer-generated synthetic
fixture scopes and subprocess-boundary composition. No live cluster acceptance.

## P0 internal recovery budget (2026-09-22, source only)

`app.cce_recovery_budget.reserve_compute_recovery` reserves within the caller's
transaction using the existing AnalysisRun row lock/RunAction JSON. It has no
public endpoint, network call or dispatch. Version1 policy and an initialized
`cce_recovery_budget` (attempt, count0, original_deadline) must be frozen for new
attempts only. Missing state rejects; no migration/default enables old attempts.
Two ordinal reservations share the attempt budget, waiting60/180s without
extending the original deadline. Replays do not spend again; counter/journal
disagreement, user stop and active resume/maintenance block new reservations.

The producer consumer must first validate bound complete fatal evidence, exact
terminal Master and Worker quiescence. Dispatch must commit reservation first
and then recheck shared control/maintenance fences under the same run lock.
Neither consumer nor dispatch is wired by this initial budget change. Existing
manual/Step7 entry points are not yet a fully shared P0 fence; keep policy off.
54 isolated BS10610 SQLite checks passed; PostgreSQL concurrency and integration
remain unverified. No table/column/API or workflow behavior change.

### Draft producer/terminal-seal validation (not connected)

`app.cce_recovery_evidence.validate_recovery_evidence` compares frozen
`snakemake.kubernetes.submit-context.v1`, plugin candidate
`snakemake.kubernetes.executor-failure.v1` and proposed trusted-runtime
`cce.master-terminal.v1`. Each carries pipeline, analysis_id, attempt (canonical
positive decimal string), execution_id, generation (integer), request_hash,
run_id, namespace, master_job_uid, master_pod_uid. The terminal document binds
the candidate by canonical sorted compact UTF-8 JSON SHA256 (ensure_ascii=false,
allow_nan=false); this digest binds contents, not caller authorization.

Proposed terminal fields: sealed/complete=true, master_state=failed,
master_pod_state=terminated, exit_code>0, fatal_source=executor_submission,
executor_failure_count matching the nonempty candidate list,
rule_failure_count/other_failure_count=0, worker_inventory_complete=true,
worker_ownership_verified=true, submissions_reconciled=true,
active_worker_jobs/active_worker_pods/unresolved_submissions=0. Boolean values
are not integers. Completeness must cover cumulative Master failures, all
submission intents and admitted manifests, not only failed entries or a single
empty API list. The future runtime reader must verify controlled paths and
frozen identity; arbitrary browser/uploaded JSON is never accepted as a seal.

Every failure must be exhausted, retryable, ABSENT with no worker UID, and one
of WORKER_CREATE_TRANSPORT / WORKER_CREATE_ADMISSION_TIMEOUT; mixed root causes,
UNKNOWN/CONFLICT/manifest failure/missing FASTQ and absent evidence reject.
Transport followed by a GET404 remains UNKNOWN, not proof of absence. This
conservative draft does not yet enable the 0918A recovery path: actual producer
fixtures, authoritative wrapper generation and all-intent reconciliation remain
required. Existing releases without them stay disabled. Dispatch must recheck
live fences/identity/quiescence; validated metadata alone is not permission.
62 focused synthetic draft-contract checks passed on BS10610; NOT producer or
Master integration acceptance. No current image is claimed to emit the seal.

### Controlled recovery evidence reader (source only)

`app.cce_recovery_reader.read_recovery_evidence` reads only
`executor-failure.json` and `master-terminal.json` in an adapter-selected scope.
It walks the configured absolute root and relative components using no-follow
directory descriptors, rejects symlinks/hardlinks/nonregular files, limits each
file to1MiB, rejects duplicate JSON keys/nonfinite values, and verifies file
metadata stayed stable across the pair read. It calls the existing evidence
validator and returns only bound metadata plus a relative evidence key.

The root, scope and expected context MUST be supplied by the trusted adapter's
frozen binding, never a browser or the evidence being read. This protects reads;
it does not authenticate a writer or prove Kubernetes quiescence. No adapter or
public route is connected yet. Original Master context belongs to its actual
Step2 submission; it must not be equated to a later Step3 monitoring execution.
Recovery must preserve explicit Master-submit/monitor lineage.26 isolated
BS10610 synthetic reader checks passed; current producer/wrapper integration
and dispatch remain pending. No existing budget/evidence suite rerun.

### Current lineage to reservation bridge (2026-09-23, internal only)

Actual producer compatibility update: plugin commit0d606489, candidate wheel
0.6.4+biosan4.p0.1, generated WGS/GATK admission fixtures under synthetic API.
Four opt-in consumer checks passed on BS10610, hash-pinned original files:
candidate alone is rejected; candidate plus a deliberately synthetic terminal
is compatible. No consumer policy was relaxed for pipeline=synthetic. This
supersedes "no producer fixture" observations, not the missing real terminal
writer/adapter/runtime acceptance. Neither artifact is an authorization seal.

`app.cce_recovery_service.reserve_monitored_recovery` binds the current failed
Step3 monitor to its explicit, current Master-submit execution (original Step2
or a replacement submitted by Step3). It checks frozen release/workdir, attempt,
generation and request hash, invokes the controlled reader, then reserves under
the existing attempt budget. The persisted action binds both execution identities
and evidence contents; repeated callbacks cannot swap evidence or spend twice.
See docs04 for the proposed trusted binding JSON fields. Missing historical
bindings reject rather than manufacturing lineage. Caller owns rollback/commit.

This bridge does not populate bindings, initialize policy, change run status,
dispatch, or expose an endpoint. It has no production caller. Actual producer
fixtures and trusted terminal wrapper remain outstanding. Automatic policy stays
off; dispatch still needs fresh control/quiescence checks and callback fencing.
22 focused WGS/GATK synthetic checks passed on BS10610, using real reader,
validator and budget with synthetic files/SQLite, not live Kubernetes or DB.

WGS `request_resume_stage` now refuses unfinished same-attempt compute-recovery
actions under the same AnalysisRun row lock, before frozen-request mutation or
Airflow calls. Terminal automatic history remains intact and manual resume is
still allowed afterward. Eight tests of this existing entry passed on BS10610.
This is one entry-point fence, not completion of generic resume, GATK, Step7,
dispatch or PostgreSQL concurrency acceptance. No unrelated regression rerun.

### Bound workload observations (2026-09-23, not a terminal seal)

`scripts/cce_recovery_workloads.py:probe_bound_workloads` issues read-only
exact-name Job and job-name-selected Pod queries through the frozen runtime's
kubectl command builder. Configured namespace must match the frozen binding.
The exact Master Job UID must be Failed/inactive, and the bound Master Pod UID
must appear among terminated, correctly owned Pods. Worker UIDs are exact;
missing Jobs still require querying their residual Pods. An expected absent
Worker with no known UID cannot adopt an unexpected Job/Pod.

All main/init/ephemeral container status inventories must match Pod specs and
show terminated exit codes. Active/deleting/foreign/ambiguous objects, missing
Pod lists, pagination, failed queries and changed identities reject. Only a
successful exact-name --ignore-not-found query may represent an absent Job.
Each command has at most30s and the caller's overall budget at most300s (default
120s). No Kubernetes writes, deletion, file mutation or status changes occur.

Caller MUST first bind a complete submission journal and admitted Worker
manifest to the frozen Master context; an arbitrary list is not complete proof.
Return values are observations only: no sealed/complete/inventory-complete or
automatic-recovery permission. Multiple queries are not an atomic snapshot;
dispatch must recheck current identity and quiescence under its control fence.
No current adapter calls this probe yet.25 synthetic boundary checks passed on
BS10610, not a real cluster or terminal-writer acceptance.

Source83e7adb's `_require_no_active_workers` and generic RUN_FAILED marker cannot
replace this boundary or the missing complete Master error summary. Do not
derive rule_failure_count=0 from an empty/partial logger stream. The existing
rule-status logger filters events and has no complete classified fatal footer;
trusted producer/wrapper work remains necessary before sealing/auto-enabling.

## Native UI evidence adapter (2026-09-17 test)

Native monitor and native-view share a bounded reader of
log/step1.<analysis_id>-a<attempt>-g<generation>-<execution_id>.log.
Snakemake Job stats total and explicit completed-step lines supply real progress;
timestamped rule/job blocks supply observed starts, explicit job completion/failure
supplies states. Unobserved times remain absent; group status is not propagated.
This is a platform reader only: no prepare, Local/SGE launch, logger, config,
pending or workflow changes. Controller receipts still determine run termination.

## WGS analysis preparation diagnostics and recovery (2026-09-18)

The private runner retains native analysis preparation stdout/stderr under the
attempt control workdir as `prepare_analysis.generation-N.log` (`0600`).
Generations remain separate. On subprocess failure, status carries the exit code
and private log basename, not the full command that hides the cause in Airflow's
truncated SSH error. Raw clinical output stays private; no new public log
endpoint. Native prepare arguments, receipts, pending selection and stage
execution fences remain unchanged. This does not enable automatic retries or
downstream CCE execution.

On an explicitly registered retry, the most recent earlier handoff request is
used even if an intermediate generation failed before creating its request.
Existing valid receipts supply pending output as before; missing receipts supply
the original verified frozen input. Identity/source/manifest/payload checks
remain in force and invalid existing receipts are never treated as absent. No
success receipt is fabricated and no shared pending file is rewritten by the
recovery.
## GATK logger release (2026-09-17)

New GATK prepares use profile r2 and an independent SFS root, pinned
Master/Worker Snakemake9.24/logger images. Existing bundles retain their own
images and root; no automatic migration on resume. All GATK groups share the
gatk_worker image; gatk_sentieon is bound to the same digest. WGS unchanged.
See [release evidence](releases/GATK_LOGGER_20260917.md).

## Existing production runtime reconciliation (2026-09-17, Git only)

The stored request is validated before wgs_release_runtime selects a server-pinned
interpreter/CCE CLI. Exact release/version pins are private configuration, not
request-supplied paths. Re-exec preserves arguments and repeats request validation.
Unmapped releases retain their existing runtime. Prepare config/profile source
hashes remain release-pinned; rendered profile revisions use that CCE version's
canonical digest. The operator skip-check policy matches exact release+batch;
normal batches do not skip checks. No prepare_wgs_batch.py interface change.

Private pending output can contain earlier batches. Validate its actual row count
and current source identity instead of equating all shared rows with this batch's
pending decisions. Preserve the original WGS selection and private artifacts.
Source synchronization is not deployment; existing resume/test gates stay intact.

## WGS custom-batch sampleinfo import (2026-09-16 candidate)

An additive `sampleinfo_upload` descriptor carries checksum, source checksum and
row count, not the uploaded text. The private request spool stores the uploaded
copy after replacement of only its analysis-batch column. `prepare_sampleinfo`
imports that copy into the standard `sampleinfo/<batch_no>.sampleinfo.txt`,
using the existing handoff receipt; it does not query/regenerate metadata or
touch pending. Repeated import requires matching bytes, and an existing batch
directory is rejected. The catalog project identity and configured analysis root
remain unchanged; no isolated namespace, marker hierarchy or alternate root.

After confirmation, the unchanged native `prepare_wgs_batch.py analysis
--sampleinfo ... --outpath ... --run-mode cce` path determines selection,
family/basecount and pending behavior. No exact-selection test-project fence is
applied. This mode is CCE-only and retains the existing split prepare/execution
confirmations, runtime execution gates and stage records. No native workflow
script, DAG, release, lock system or database schema is modified.

Final input interface: the backend reads `sampleinfo_path` under configured WGS
roots into that private copy, so the runtime does not need arbitrary file-read
commands. The original file is never modified. User explicitly declined a
no-pending option: existing pending and native selection behavior remains in
force during analysis preparation. Import-time preview and final selected samples
remain separate confirmations. No additional owner-script capability is needed.

Review hardening: analysis preparation compares the imported source copy with
its post-batch-replacement SHA256 before creating/reusing the handoff request.
Preview/config approval never rewrites this copy. Native analysis reads it and
writes selected/final tables elsewhere; those outputs are not compared with the
import checksum. Imports and their receipt artifacts use fsynced temporary files
and atomic no-overwrite publication, so interrupted writes do not expose partial
final inputs. Native prepare/pending code remains untouched.

## Native read-only view evidence (2026-09-16 candidate)

No WGS prepare/runtime/profile/logger changes for these views. Native main log:
log/step1.{analysis_id}-a{attempt}-g{generation}-{execution_id}.log. Only selected
execution is read; shared child logs and prepare projection.jsonl are not runtime
Rule evidence. Parse explicit rule/job/sample wildcard/completion facts within
bounded text; no complete DAG, timestamps or success inferred from group/exit0.
History configuration reads hash-verified private snapshots, not mutable config.

User explicitly wants one latest QC per run, not per-execution QC. Original
QC.smk mergeQC uses config.batch; read current config.yaml and exact
07_QC/{batch}.QCstat.tsv, not project basename or newest glob match. Validate
project binding/path, reject symlink escape, cap reads, require complete header/
rows/newline and stable read. Preserve previous normalized cache on failure.
QC mtime describes source freshness only. No new archive protocol, pending
selection, cleanup, sample rename mapping, observer-side rerun or file writes.

## Controller completion and monitor attachment (2026-09-16 candidate)

This checkpoint supersedes the terminal/attachment limitations below. The WGS
owner679a3e thin supervisor waits for original foreground Step1 to exit and
publishes controller-exit.json once. Platform validates fixed path, complete
identity and frozen manifest hash before terminal projection. Raw native result
markers still do not prove cleanup/controller completion. Success is for the
requested command, not proof of full QC/sample completion. Signal exit or failed
SGE controller keeps relaunch blocked pending remaining-job review.

The helper attaches bio_wgs_native_monitor after spawning. Personal-session
monitor API is idempotent by execution ID and fixed conf; network retry performs
attachment only. No prepare/claim/launch replay. Generic/WGS Airflow status sync
does not derive analysis status from this monitor DAG. Contract:
[controller exit and monitor attachment](superpowers/specs/2026-09-15-wgs-onprem-execution-contract.md).
BS1061018backend+2DAG checks, including actual owner synthetic receipt consumed
against a real platform snapshot. Candidate default off, no live deployment.
Execution-scoped rule/sample/QC/log/history views remain pending.

## Native observation checkpoint (2026-09-15)

Generation-fenced observation reads only exact registered native metadata/result
files, never launches or signals work. New monitor-only DAG is isolated from CCE.
Raw .exitcode/finished_at are recorded as native_result_reported, not controller
termination: original Step1 cleanup follows them. No terminal permission release
or automatic monitor attachment until the final controller-exit adapter is agreed.
The independent WGS helper still acknowledges only its background parent. No PID
reuse/liveness inference or command replay. Current started/status projection is
implemented; per-execution rule/QC/history views remain pending.

WGS tests now use deployed34bfcbf plus thin hooks (b07bbc4); newer ba7b272-based
code retained but excluded. Owner and platform verified native runtime/sampleinfo/
profiles unchanged. Six-file snapshot contract remains applicable to this baseline.

## R2-3 one-shot claim checkpoint (2026-09-15, disabled candidate)

Personal-session POST /api/wgs/onprem/executions/{execution_id}/claim grants
one automatic launch attempt using a conditional accepted→launching transition.
It starts no process or DAG. Separate WGS_ONPREM_LAUNCH_ENABLED defaults false.
Current native mode's config.yaml/runtime.yaml profile bytes join the existing
four input refs; runtime.yaml is prepare provenance, not re-applied at startup.
Exact [execution/claim contract](superpowers/specs/2026-09-15-wgs-onprem-execution-contract.md).
BS10610:25 targeted claim/execution checks passed. WGS owner confirmed standard
profile layout is project-local. Thin caller and observer/DAG integration remain
pending; keep gates off.

## R2-1/2 checkpoint (2026-09-15, source only)

WGS owner reports thin hook commit5485c8a31795cba17291698903b2388f3ad8d700,
task branchjiucheng/wgs-onprem-registration-r2; not merged/pushed/deployed. It adds
only optional analysis/local|sge registration, stable binding and register-only
retry; native algorithms/pending/profile/Step1 unchanged. Owner reports32 matched
synthetic checks. Platform candidate execution registration separately passed11
execution/8 registration checks. These are not a joint live-system acceptance.
Execution uses config.sample data IDs as configured scope, not metadata rows.
[R2-2 contract](superpowers/specs/2026-09-15-wgs-onprem-execution-contract.md)
preserves same-run generations and private inputs; launch_allowed=false.
No monitored script, launch claim, argv forwarding, terminal observer or
execution-scoped Sample/QC UI yet. Older snapshot launcher below remains inactive.

## Earlier R2-1 thin-hook checkpoint (superseded by source checkpoint above)

WGS owner confirmed optional analysis-only post-success registration, with no
project/registration when native selection is empty. Stable project UUID and
initial summary survive failed registration; retry only the HTTP registration,
not prepare or pending. Current platform candidate accepts personal-session
project registration with11 matched checks passed, but WGS hook is not implemented.
No monitored launch script may bypass the still-pending execution API. Native
mv may require user repair of original absolute paths; platform does not rewrite
Step1/profile. [Exact schema](superpowers/specs/2026-09-15-wgs-onprem-registration-contract.md).

## R2 existing native launcher correction (2026-09-15, tested source only)

The launcher now requests identity/target/entry/profile binding validation without
requiring mutable config/sample files to match prepare hashes. Default prepare
validation is unchanged. Before native launch, executions/<execution_id>/snapshot
stores current config and its actual sample_info/new_sample_info files, generated
argv and effective Linux uid/user; private permissions, exclusive creation and
manifest-last writes preserve earlier executions. Same-execution replay refuses
launch, rather than overwriting evidence. Invalid current mode/missing samples or
changed entry/profile remain errors. No sample selection or pending write occurs.

13 matched BS10610 cached synthetic checks and syntax checks passed. This does
not deliver the R2 project registry, movable project identity, user-supplied argv
forwarding, Sample/DB history projection or monitor-only DAG. Existing prepared
payload is still required; feature remains off. Earlier R1 notes below are history.

## Local/SGE R2 planning override (2026-09-15, not implemented)

[R2 design](superpowers/specs/2026-09-15-wgs-local-sge-platform-integration.md)
supersedes the old fixed-prepare-input assumption for the new optional monitor
entry. Native sampleinfo stays unchanged; analysis may opt into post-prepare
project registration. The original Step1/profile and pending decisions remain
native. First CLI launch and every resume register then run locally, while
Airflow only monitors/collects. No web prerequisite or repeated prepare.

Each execution snapshots actual config, referenced samples and argv; edits are
allowed before start/resume. Hashes verify snapshot integrity, not equality to
prepare. Identity/target/access checks remain. Stable project binding survives mv;
old-path reuse gets a new project identity; history cannot read a different
project at the old path. These changes require R2 implementation; the strict
binding code described below is still R1 candidate code and must stay inactive.

## Native launcher source checkpoint (2026-09-15, unverified)

New scripts/wgs_onprem_runtime.py shares direct native Step1 invocation for
Local/SGE without changing config/profile or resource arguments. The existing
Local gate uses it only for native frozen requests; legacy conversion is retained.
Native execution/generation gets its own WGS_ATTEMPT_ID and evidence directory;
controller exit0 alone is insufficient without matching native exitcode/metadata.
Shared validation loads the sibling wgs_runtime_gate.py for its existing binding
checks; both scripts must be installed together, without copying WGS private config.
SGE restricted runner/DAG, node mapping, observer stream discovery and monitored
command-line entry are not yet wired. Source awaits BS10610 GREEN after SSH failure;
do not activate merely because the library accepts SGE fixtures.

## Local/SGE implementation checkpoint (2026-09-15, not enabled)

Native interface candidate `ba7b272` is confirmed by WGS-pipeline; no release
catalog update or WGS script change. Preparation-target freeze foundation is
implemented but not activated by submission creation. Existing CCE prepare and
legacy Local conversion remain unchanged. Native mode argv and non-CCE prepare
binding are now implemented; shared monitored wrapper, SGE controller and CLI resume remain pending under
`WGS-LOCAL-SGE-20260915`; do not infer end-to-end support from the freeze tests.

Native prepare uses the existing staged sampleinfo/analysis handoff and WGS
receipt validator. It passes `--run-mode local|sge` without `--run-id`, CCE
operator/config/CLI/from-zero arguments. It never rewrites config, Step1 or raw
links, never generates a CCE bundle, and never reselects samples.

`batch-binding.v2` native bindings contain `prepare_execution`, native mode/target
in `resolved_runtime`, and hashes of only four small prepared artifacts:
config.yaml, Step1_run.sh, the chosen profile config and the final sampleinfo.
The final sampleinfo must match the validated WGS receipt. No whole-project,
FASTQ or result hashing; no CCE identities invented. Binding load rejects changed
artifacts, outside paths, different attempts/releases/targets and CCE/native mixing.

Retry reuses the exact validated receipt and binding. A lost binding may be
rebuilt from an intact project plus the exact receipt; an unidentified existing
directory, absent selected output, or missing/wrong receipt fails without rerunning
prepare or changing pending. Completed all-pending receipts are reused without
creating a binding or repeating preparation. These tests use synthetic native
artifacts, not a real WGS or node96/97/18 run. Observer native projection belongs
to Task2 and is not yet enabled.
## GATK workload retirement (2026-09-16)

The common bridge's GATK label path uses complete namespace Pod inventory to
distinguish disappearance from changed labels. Previously observed absent Pods
emit existing pod-events with phaseDeleted/reasonPodNotFound; incomplete queries
and identity drift cannot retire them. GATK importer rejects older observed
snapshots. WGS's scoped polling and execution behavior are unchanged.
Final reader collection and Step6 delivery refresh workload evidence once;
Step6 stage-status ingests it using the existing cursor importer. Reader cleanup
stays asynchronous, collection failure cannot fail successful delivery, and
Step7 still checks current runtime Jobs/Pods/UID and verified delivery before
the administrator-authorized destructive action. No new API/table/daemon.

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
