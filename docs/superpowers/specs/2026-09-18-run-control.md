# CCE run pause, resume and project deletion

## 2026-09-26 lifecycle revision (current design, not implemented)

The user confirmed the [P0 lifecycle revision](2026-09-17-wgs-gatk-cce-connection-recovery-design.md)
and requested documentation only. Its R1–R7 and the
[new implementation queue](../plans/2026-09-26-p0-lifecycle-correction.md) supersede
conflicting historical scope/permission assumptions below. Pause/delete were
previously design-only; recovery fences are not an implemented pause feature.

- Common lifecycle/control logic is adapter-driven, initially WGS and WES/GATK
  on CCE, without pipeline-name branches. Local/SGE controls are not added.
- Automatic registration precedes Step1. Stable attempt/run ownership is separate
  from stage execution IDs; CLI and platform resolve the same current generation.
  Read-only status does not claim a writer lock; pause retains directory ownership.
- `cleanup_cloud` and `delete_project` are distinct confirmed actions using the
  same control operation protocol. Cloud cleanup alone preserves platform history;
  project deletion additionally handles exact Airflow and business associations.
  Neither operation deletes offline/local data or moves a project directory.
- The user moves/deletes their local directory. A later new submission rejects an
  occupied local target. Once cloud output paths are verifiably cleaned, a fresh
  analysis/run identity can reuse the batch name and paths without manual unlock.
  Retained tombstones and RELEASED legacy guards cannot permanently reserve them.
  Partial/unknown cleanup reports residuals, not a generic stale-lock error.
- Same-attempt resume retains checkpoints/config; same-name new analysis creates
  a new identity. Continuing an old identity at a moved local path is out of scope.
- Business outputs use0755 directories/scripts and0644 regular files. Credentials
  and necessary private control state stay private. Use consistent non-root
  writer identity per storage domain, not mandatory group-write on results.
  No existing-tree chmod/chown or input/source permission migration is authorized.
- Plan one independent durable control-operation record with minimal deletion
  tombstone fields. RunAction is CASCADE-bound to AnalysisRun and cannot be the
  sole surviving audit. Reuse recovery actions/budgets, not another retry engine.

Section6 API proposals remain the selected interface. Preview explicitly selects
cleanup_cloud, delete_project, pause or resume. Accepted/partial/unknown is not
completed. No stop is successful until exact writers are quiescent. Performance
and bounded acceptance follow P0 R7 and plan V1–V6. Remaining sections retain
resource-level safety details. This delivery implements or activates nothing.

Status: design complete; implementation not started. Documentation only.
Original base: `jiucheng/test/wgs-local-main-sync-20260917` at `2d899e5`.
Source work branch: `jiucheng/feature/run-control-20260918` at `1c631b7`.
Consolidated into the primary test documentation queue on 2026-09-18; this did
not add implementation or runtime authority.

## Approved scope

The user explicitly accepted checkpoint resume on 2026-09-18: stop current
computation, retain completed results, then resume the original analysis,
attempt, frozen configuration, release, workdir and runtime run ID. Incomplete
rules may run again. This is not OS-process freezing or restoration of in-memory
algorithm state. A replacement Master UID requires recorded lineage and fences;
it is not a new analysis or permission to run prepare or `--forceall`.

The later scope correction supersedes the earlier development authorization:
this task produces only this design, future task cards and state/handoff notes.
Necessary runtime adaptation is an accepted future option, not permission to
implement or validate it now. No application tests, remote commands, candidate
environment construction, migration, deployment or real task operation belongs
to this delivery. Future implementation and BS10610 acceptance require a new
development instruction. Production release and live pause/resume/delete always
require separate explicit authorization. Existing frozen bundles are not edited.
The source design task left main, production and the primary test branch
untouched; the later consolidation changes only the primary test branch's
planning documents.

Native monitor-only Local/SGE runs remain outside the CCE control adapter. No
offline/local project, result, FASTQ, sampleinfo, pending, evidence, reference or
workflow directory is deleted, including such files on remote/NFS nodes.

## Findings and reuse

- `action_wgs_run(cancel)` records a request and refuses committed CCE work; it
  is not runtime termination. Its ordinary resume increments attempt and must
  not be reused for this new operation.
- WGS `wgs_resume.py` already validates frozen manifests and records strict
  Master replacement. GATK's operator helper is narrower and is not a platform
  pause/resume API.
- Existing Step7 requires verified delivery; it is not failed-project deletion.
- The retained cce-pipeline 0.8.5 source snapshot supports same-run checkpoint
  resume and a separately authorized failed-SFS cleanup path. This is source
  evidence, not proof of every live frozen bundle's capabilities. Capabilities
  must be established for each exact target; no frozen script is rewritten.
- Missing endpoints are implementation gaps, not proof that external package
  upgrades or all-new images are necessary.

## 1. Proposed architecture, not an implemented contract

An authenticated administrator requests a persistent operation, never an
arbitrary command or filesystem path. A separate control DAG transports only
pipeline, analysis ID, attempt and operation identity to the existing restricted
runner. Runtime requests and receipts bind operation generation, frozen binding,
request hash and approved plan hash. Feature enablement defaults off.

Pause first fences new platform and node-side dispatch. It then establishes
exact process/workload ownership, stops the Master from creating more jobs,
converges already dispatched workers/transfers, and verifies quiescence before
reporting `paused`. Unknown PID identity, connection failure or unconfirmed
export completion is a blocker, not a successful pause. Leases stay occupied
until their exact owners have authoritative quiescence evidence. Old callbacks
must not overwrite operator control or report a biological failure solely from
monitor/DagRun failure.

Resume consumes the matching pause receipt and existing checkpoints. It reuses
successful stages and active/completed original execution when appropriate;
replacement requires archived identity/evidence and an explicit new generation.
Repeated clicks and lost responses resolve to the existing operation.

Deletion is preview, explicit confirmation, then durable execution. Targets are
identified by exclusive ownership and exact identity, not batch-name patterns.
Cloud cleanup precedes deletion of the run's Airflow metadata through supported
API calls; business records are deleted last in a transaction. Shared or changed
objects remain protected. Partial cleanup reports each residual and retries
without repeating completed targets. A run-independent tombstone/audit retains
actor, time, approved scope and item outcomes; scanner source identity remains
suppressed after deletion. Successful deletion is never claimed on an ambiguous
cloud result or failed Airflow deletion.

The proposed runtime protocol is `run-control <analysis_id> <attempt> <action_id>
<preview|execute|status>` through a pipeline-fixed gate. Request, plan and receipt
schemas are `run-control.request.v1`, `run-control.plan.v1` and
`run-control.receipt.v1`. Backend/runtime owners must keep exact field contracts
aligned before enabling the control DAG. Public APIs never expose credentials,
clinical payloads or client-selected shell arguments.

## 2. State, identity and concurrency

Execution result, monitoring health and administrative operation state are
separate. Preserve last confirmed execution status when queries fail. A failed
Airflow task or SSH connection alone cannot set a biological failure, release a
lease, or prove runtime quiescence.

Proposed operation transitions:

| Operation | Normal path | Uncertain/failure path |
| --- | --- | --- |
| Pause | previewing -> awaiting_confirmation -> pausing -> paused | blocked before mutation; partial or needs_review after incomplete stop |
| Resume | previewing -> awaiting_confirmation -> resuming -> resumed | preserve paused fence or needs_review; never launch a second execution on timeout |
| Delete | previewing -> awaiting_confirmation -> deleting_cloud -> deleting_airflow -> deleting_database -> deleted | partial with exact residuals; records and fence retained |

These are proposed control-operation states, not changes already made to run
status enums. The UI may derive a paused badge from verified control state;
analysis history retains its real prior outcome.

Operation identity is pipeline + analysis_id + attempt + action_id + generation.
Bind it to frozen release/config/workdir/runtime run ID and each relevant stage
generation/request hash. A new Master has a new Kubernetes UID, explicitly linked
to its predecessor. Original run ID is retained; neither batch nor sample name
is an execution identity.

Use one active control operation per analysis across all attempts, database
locking/uniqueness for platform arbitration, and a restricted-runner lock with a
persistent generation fence for remote side effects. Conflict with submission,
resume-stage, reanalysis, Step7, another control action or automatic dispatch
must reject before starting work. Duplicate idempotency keys with the same
payload return the same operation; different payloads return conflict. A
backend/worker restart reloads the journal instead of generating a new identity.

The plan hash covers semantic scope, exact resource identities, protected items,
expected run revision and policy version. A short preview validity period is a
UX limit, not proof of safety. Execute always rereads ownership and uses UID/RV
or object-version conditions. Newly discovered/changed destructive targets
require a new preview and confirmation; retries cannot silently widen scope.

## 3. Pause and same-attempt recovery by stage

First persist the platform dispatch fence, then publish/acknowledge the node
fence. Both ordinary and recovery stage entry points must check it immediately
before side effects under the same lock. Reconcile in-flight dispatch before
claiming a stop. DagRun cancellation/terminal marking is an orchestration step,
not a substitute for killing detached runtime or cloud workers. Do not pause
the whole shared DAG definition, which would affect other runs.

| Stage/resource | Pause behavior | Resume behavior |
| --- | --- | --- |
| Waiting/queued Airflow work | Stop this run's progression and fence queued retries | New controlled recovery dispatch for the same attempt, only necessary stages |
| Step1 upload / Step5 download | Stop exact owned process tree; preserve checkpoint and successful files | Reattach if alive; otherwise continue the original checkpoint, no full transfer replay |
| Step2 Master creation | Reconcile request/handoff plus deterministic Job identity; an empty read after timeout is insufficient | Reuse existing Master or prove original create never happened before creating |
| Step3 computation | Capture worker inventory/evidence; stop exact Master creator; confirm its Pods stopped; rescan and stop/wait owned Workers | Reuse completed output; explicit replacement lineage when needed, rerun incomplete rules only |
| Step4 publish/export | Block new publish. Reconcile original operation/task ID; safely stop only if supported, otherwise wait for it to finish | Reattach/reconcile original export, do not submit another because response was lost |
| Step6 materialization | Reach an owned safe journal boundary; no arbitrary kill mid-commit | Continue original journal, do not overwrite completed delivery or redownload |

Pause is not successful while an export, materialization commit or unknown
descendant can still mutate data. Show what is waiting and why. A bounded timeout
leaves needs_review/partial; it does not imply quiescence. A task that completes
while pause is being requested remains completed; do not falsify a paused state.

New runtime process receipts need node/boot ID, process start identity, PID/PGID
and request generation. PID alone or matching a command-line substring is not
safe for a historical process. Missing identity on old runs yields unsupported
or manual review, not guessed termination. Master deletion alone does not prove
Worker deletion. Query failures cannot be treated as an empty workload list.

Keep exact transfer and heavy-slot ownership until authoritative stopped/terminal
evidence and compare-and-set permit release. Batch/workdir exclusivity stays
reserved while paused so another run cannot occupy its output path. Resume
reacquires execution capacity rather than assuming an old released slot remains
available. Never remove a lease solely because its heartbeat is old.

Before replacement, retain the prior handoff, terminal markers, worker manifest
and evidence generation as history. New controller events are fenced by the
replacement identity; late old failures must not overwrite current state. Stop
requested by the operator is not a biological rule failure. Frozen config and
prepare outputs remain unchanged. Missing compatible resume primitives is an
explicit capability failure, not permission to patch a frozen bundle.

## 4. Exact deletion plan and protected data

The unit is one analysis project identified by analysis_id, including its known
attempts and recovery descendants. It is not every project sharing a batch or
sample name. Running/unknown work cannot be deleted; require a separate verified
pause or authoritative terminal state and repeat the quiescence check under the
deletion fence. A failed UI badge alone is not evidence of a stopped Master.

| Resource | Planned treatment and required proof |
| --- | --- |
| CCE Jobs/Pods/readers/maintenance jobs | Enumerate all owned generations; namespace + name + UID + run binding; delete only exact confirmed objects, then verify absence of those identities |
| Cloud SFS runtime/results/linkage | Resolve frozen cloud mount/contract root and ownership; reject symlink escape, shared roots and offline NFS equivalents; dedicated cleanup operation, not ordinary successful Step7 invoked without its prerequisites |
| OBS results/staging/log packages | Enumerate exact exclusive prefix/objects and versions; verify no writer remains; use conditional/versioned deletion when available |
| OBS FASTQ inputs | Explicit independent preview category; delete only objects proven exclusive to this analysis and explicitly included in the confirmation; shared/uncertain FASTQ stays protected |
| Exports, transfers and leases | Report operation IDs and liveness; drain/cancel only supported owned operations; exact lease release after quiescence |
| Airflow metadata | Exact original/recovery/analysis-maintenance DagRun IDs owned by the analysis via supported per-DagRun API; task metadata follows supported Airflow semantics; never delete the shared DAG definition |
| biodemo records | Exact run/attempt sample, rule, QC, artifact, stage, observer, workload, transfer, action and private-draft associations; transaction after cloud and Airflow confirmation |
| Audit and intake provenance | Retain independent tombstone/control audit and minimum scanner suppression identity; do not cascade-delete suppression |
| Offline/local data and shared catalogs | Always protected in this feature; project/results/raw FASTQ/sampleinfo/pending/evidence/references/workflows/accounts/pipeline definitions and other runs stay untouched |

Preview classifies every item as delete, retain_shared, protected_offline or
blocked_unknown, with an explicit reason. Cloud SFS/OBS residues must be accounted
for, not silently left while reporting full deletion. Protected objects excluded
from the approved scope are not claimed deleted; unresolved in-scope objects
remain residuals and prevent full success. Source labels and path names alone
do not prove exclusive ownership. An unavailable cloud inventory blocks deletion.

If an OBS API lacks safe object conditions, deletion requires a verified
exclusive namespace/writer fence covering the entire operation. Otherwise report
unsupported and retain the objects. Do not assume ETag alone is a content hash or
proof of current ownership. Capability checks are per frozen runtime/version.

Persist item state before each side effect. If a response is lost, inspect the
same resource identity: confirmed absence of that approved object can complete
its journal entry, but a new object at the same name must never be deleted.
Retry targets only unfinished approved items. A partial cloud cleanup keeps all
business state needed for recovery and forbids resume/new dispatch because some
results may already be gone.

Delete Airflow analysis metadata only after cloud completion; if that fails,
retain biodemo and tombstone journal for retry. The active control DAG cannot
delete itself while authorizing DB finalization. Retain that maintenance run as
explicit audit evidence, or retire it later through a separately authorized
retention policy. Do not imply all Airflow database rows have vanished.

Database deletion is not a blind cascade. Inventory foreign keys and standalone
analysis references, handle non-cascading references explicitly, and preserve
shared input snapshots/lifecycle records or children owned by another run.
Unexpected/shared references block rather than delete other history. Shared
lease slot rows are released by matching owner, not removed. Record deleted row
counts by table with no clinical values. Artifact-row deletion never implies
filesystem deletion. A failed final DB transaction leaves cloud outcomes in the
durable operation and can be retried without repeating cloud deletion.

## 5. Proposed persistence and scanner suppression

Two small additive concepts are planned: a run-control operation and a deletion
tombstone. They must not have a cascading dependency on AnalysisRun. Reuse
existing audit facilities where their uniqueness/locking requirements suffice;
the future implementation must justify any new table in the schema review.

The operation stores actor/action/attempt/generation, idempotency key and request
digest, status/revision, approved plan digest, private target snapshot reference,
item outcomes/residuals, runtime receipt digest, timestamps and source identity.
The tombstone stores the analysis identity, deletion operation, approved scope,
actor/time, completion or partial outcome and privacy-safe source suppression
keys. No patient fields, credentials or raw sample sheets are retained in it.

Install scanner suppression atomically with the deletion intent before cloud
mutation; finalize it with database deletion. Guard both intake discovery and
the final automatic creation/dispatch transaction to close races. Use frozen
project/platform/source identity and sequencing batch/directory identity, not
sample ID. Store the observed source version for audit; touching/copying the same
source or changing its content must not automatically erase suppression. Existing
intake `analysis_id` uses SET NULL, so deleting the run without this guard could
make it look unsubmitted again. Explicit authenticated manual re-submission may
create a fresh analysis after normal target/ownership checks; historical
suppression is not a batch-name ban. It does not clear suppression for autonomous
scanner dispatch. No automatic resurrection or shared pending alteration.

Additive schema changes, migration tests and deployment are future work. Do not
drop historical tables or downgrade by deleting audit. Production schema changes
and an irreversible migration require separate approval before execution.

## 6. Proposed API, orchestration and UI

These names are design proposals only; they are not registered endpoints:

| Interface | Meaning |
| --- | --- |
| POST `/api/runs/{id}/control/preview` | Admin action, expected attempt and idempotency key; create/reuse persistent preview operation |
| GET `/api/run-control/{action_id}` | Authorized operation/plan/item outcome and capability view, including tombstone after run deletion |
| POST `/api/run-control/{action_id}/confirm` | Exact analysis ID text + approved plan hash + revision; reject stale or conflicting approval |
| POST `/api/run-control/{action_id}/retry` | Retry unfinished items of the same approved operation; changed scope requires re-preview |
| POST `/api/internal/run-control/{action_id}/advance` | Service-authenticated phase/dispatch-sequence fence for the dedicated control DAG |

A proposed `bio_run_control` maintenance DAG consumes persistent operation
identity, phase and dispatch sequence. Backend resolves pipeline/analysis/attempt
and authorizes each transition; DAG conf cannot grant permission by supplying a
shell command, root, URL or target. Runtime input is a private request under the
existing pipeline request root, with `request_hash`, frozen binding/hash map and
the approved plan digest. Receipts contain exact identity, quiescence, per-item
outcomes, residuals and Master replacement lineage. A forged or stale receipt
does not advance the operation. No Web background thread is the durable owner.

Keep mutation permissions administrator-only initially, enforced server-side on
every confirmation/retry. Internal tokens authenticate service calls but do not
replace operation authorization. Feature enablement defaults off and CCE
adapter capabilities are explicit. Native Local/SGE pages do not inherit these
buttons. Ordinary pause/resume/delete routes cannot bypass active control fences.

Use the existing run detail action area, without a new navigation page. Running
CCE runs show Pause when supported; verified paused runs show Resume; terminal
or paused projects show Delete after preview. Show unsupported reasons rather
than a working-looking button. Pause copy explains incomplete rules may restart.
Delete confirmation lists cloud, Airflow and database categories, protected
items, blockers and irreversibility, and requires the exact analysis ID rather
than only a reusable batch name. Display ongoing/partial/unknown states and an
explicit retry action. After deletion, navigate away from the ordinary detail
page but retain access to the tombstone/operation result. No fake success toast
on accepted, timed-out or partially completed operations.

## 7. Future task cards and acceptance

| ID / owner | Deliverable | Minimum acceptance |
| --- | --- | --- |
| RC-01 / Workflow | Restricted pause/resume/delete planner and executor, process ownership, node dispatch fence | Exact-identity mismatch has no mutation; pause requires quiescence; original checkpoint preserved; repeated operation idempotent; residual retained |
| RC-02 / Backend | Admin API, durable operation, independent tombstone, pipeline adapter and scanner fence | Unauthorized requests rejected; stale preview rejected; one concurrent operation; no DB deletion before cloud and Airflow completion; tombstone survives run deletion |
| RC-03 / Airflow | Separate operation DAG, original dispatch/terminal fencing and same-attempt recovery | No arbitrary command or pipeline mismatch; transport error preserves execution uncertainty; no prepare/replay of successful stages |
| RC-04 / Frontend | Existing run-page controls, preview/confirmation and partial retry display | Disabled/unsupported cases visible; deletion requires exact confirmation; unknown/partial is not success |
| RC-05 / QA | Isolated BS10610 synthetic contract acceptance | Only affected tests, no live DB/cloud or real workflow submission; report precise unsupported historical cases |

After a separate instruction to begin development, each owner writes a failing focused test, runs RED remotely, implements its
bounded change, and reruns that affected test set. No full pipeline run or broad
regression suite is required. Update API/schema/runtime/DAG/UI/runbook contracts
only where implementation actually changes them; do not document planned APIs
as already available.

The authoritative compact queue is in [`TASKS.md`](../../../TASKS.md); this
design retains the detailed dependencies, risks, rollback and permission gates.
The minimum future failure matrix covers:
repeated clicks, conflicting actions, stale preview, Master/Pod UID reuse,
transfer PID reuse, partial Worker inventory, transport/authorization errors,
lost create/publish/delete responses, stale generation receipts, backend restart,
shared cloud prefixes, changed object versions, cloud partial failure, Airflow
delete failure, DB rollback and scanner rediscovery after deletion. Parameterize
WGS/GATK differences; do not run real analyses or repeat unrelated suites.

This documentation delivery runs only link/scope/task-ID/whitespace checks. No
application test or BS10610 validation has been run or claimed.

## 8. Rollback and authorization gates

Future rollback disables control dispatch and restores code. It must preserve operation
records, tombstones, paused execution evidence and existing data. Code rollback
cannot undo an executed cloud deletion; the preview must say so clearly.

Do not automatically resume paused work as part of code rollback. A control
operation already in flight must remain fenced and be reconciled, not reset to
idle. Releasing a test feature does not authorize production activation, granting
new cloud permissions, changing an external workflow release, or deleting any
real target. Exact host/release/mount/gate checks precede any future remote work.
