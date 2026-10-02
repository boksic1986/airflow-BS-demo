# Workflow runtime integration

## A468E9 initial submission recovery — authorized candidate, not deployed

The shared WGS/GATK stage adapter freezes old initial Step2 sender evidence in
the existing native worker-command callback, after native old closure checks
and before shared dispatch replacement/log append/new launch. Native holds the
launch lock; the callback acquires the worker lock nonblocking and releases it
before returning. Contention rejects launch, never waits in the reverse order.
It revalidates the old immutable registration, terminal and business receipt,
matching finished dispatch and process-group quiescence, then publishes private
immutable snapshots of old dispatch, business receipt and stderr. Publication
is byte-idempotent; changed bytes or conflicting snapshots reject. This grants
no initial-abort, compute FINAL, owner transition or Master CREATE authority.

The frozen native consumer contract uses exactly eight flat trusted locators:
registration_path, terminal_path, dispatch_path, business_receipt_path,
stderr_path, paired_source_path, native_source_path and executor_source_path.
Requests and environment values cannot choose them. The three fixed old source
snapshots are data under the new operator-trusted closure's initial-abort-sources
directory; they are never imported. Native independently re-reads and validates
their SHA and the precise old failure/control-flow identity. Initial abort and
INITIAL_ABORTED takeover remain distinct from compute FAILED/FINAL; the normal
recovery API, same attempt and old evidence are retained. Full native/consumer
integration and deployment acceptance are pending. No source GREEN implies
current-run recovery. See the existing incident/recovery review note.

## 2026-10-01 final423 candidate preserves production safeguards

Step4 registration retains the deployed exact exception for a confirmed queued
resume audit row whose same-attempt failed DagRun precedes the validated current
successor. The old row stays queued; this grants no remote termination evidence.
Other active controls still block dispatch. The unified frozen-request digest
checks remain in place for initial and recovery WGS requests.

Forced WGS generation registration ingests existing runtime status before the
AnalysisRun lock. It must not invoke that ingestion again while holding the run
lock, because the observer opens its own session and locks the same row. Current
attempt/recovery identity and orchestration-contract checks remain under the
registration lock. These preserve deployed safeguards without API/DB migration.

## W423-R1 exact version compatibility (2026-10-01, source only)

`V4.2.3` uses the existing `prepare_sampleinfo`/`prepare_analysis` generation-
scoped handoff request and receipt contracts. Repository preparability and
the backend required-receipt check recognize this exact version. Successful
stage status without the required receipt remains artifact_pending and not
ready; valid receipts follow the existing selection and submission-phase
projection. Repository allowlist/root, source/profile/config/receipt hashes
and execution identity/generation validation remain mandatory. Unsupported
versions are not accepted by prefix or wildcard.

BS10610 focused synthetic validation passed26 cases after five expected423
RED failures. This source addition does not install native089, register a
final423 release or activate TEST/production. See the
[W423-R1 evidence](releases/2026-10-01-w423-group-test-consumer-audit.md#w423-r1-exact-version-compatibility-addendum).

## GATK terminal Master TTL and downstream stages (2026-09-29 scoped production repair)

WES/GATK `20260927B` (`GATK_20260929_024231_F246CD`, attempt 1) completed
Step3; Step4 then reported `Step4 requires a successful Master Job`. The
frozen Master has a 100-second terminal TTL and was absent at inspection.
An earlier run-scoped reader found the original UID's successful native
`RUN_COMPLETE.json` on SFS; the deletion event itself was not observed.
Before the repair, the local mirror lacked the terminal record. Airflow Step3
success or Job absence alone cannot authorize publish.

For an unregistered legacy GATK run, Step4/5 may use a restricted fallback
only after the gate recomputes the canonical request hash and checks the exact
attempt/generation, frozen handoff and UID, batch-lock owner and terminal
inventories under both existing run labels. A same-request reader may refresh
native evidence with only a read-only SFS mount and scratch volume; its UID is
verified for cleanup. The frozen `_recovery_native_success` then must verify
the complete UID-bound terminal and workflow marker before the original Step4
or Step5 function runs. The existing paired `stage_command` route takes
precedence; active/invalid writer policy, query uncertainty or contradictory
evidence never falls back. No Master replacement, analysis rerun, TTL change
or new API/schema is introduced. BS10610 passed 45 synthetic tests for the
original gate candidate and 21 TTL-specific tests after current-main
integration. A subsequent complete-response bytes regression was 2 RED and
then 5 GREEN (17 deselected) after the parsing fix.

Production node200 `t640` now runs only the private gate/helper update: its
old private gate received the focused patch from `4870e2b` + `eb1b8aa`,
while the helper matches current-main candidate `5945f26` + `22e5535`.
BS96 backend and worker containers/mounts did not
change. On the original attempt-1 DagRun, the Airflow 2.9.3 API dry-run
selected 10 Step4-and-downstream task instances and the exact clear returned
HTTP 200, excluding Step1–3. The constrained reader verified the original
Master UID `faecf4ae-562d-42f9-a449-18bf50b90c9c`: native `RUN_COMPLETE`
is `SUCCEEDED`, `preflight`/`analysis`/`final_dryrun` exits are 0,
`START_CONFIRMED` has the same UID, `workflow-completion` is present, and
`RUN_FAILED` is absent. Its temporary Job/Pod were gone after the read.
Step4 generation 2 and `wait_step4_publish` succeeded; Step5 awaited the
result transfer slot and Step6 had not started at this checkpoint. This older run has no
`publish_deadline`, and the generic GATK resume capability is disabled in
production; its recovery used only the exact original DagRun task clear.
See the [release evidence](releases/2026-09-29-gatk-ttl-downstream-bs96.md).

## WGS PREPARE recovery projection (2026-09-28 candidate)

The backend observer retains append-only contract-v2 PREPARE execution history.
After validating the current attempt, execution ID, generation, and request
hash, a newer generation's accepted/running/success status may replace an old
failed `run_stage_state` display row. The display row alone never authorizes a
stage transition; the current execution transition and its terminal receipt
remain authoritative. Stale/foreign generations and terminal regressions stay
rejected. The runtime request and receipt formats are unchanged.

## UE-05 bound terminal consumers (2026-09-30, source only)

The shared UE-04 native terminal validator now accepts an explicitly expected
failed/canceled terminal as well as succeeded; the success-only finalization
wrapper keeps its existing contract. R2 uses a complete current native Step3
snapshot, the frozen version-correct request and business receipt to bind the
queued action's compute terminal. Its action/DagRun/attempt/execution identity
is retained for budget arbitration without removing downstream authorization.
Manual Resume Step1/2 retains its entry stage in action metadata; the actual
compute terminal binds the current Step3 registration and frozen/native identity
authorized by that same action. The entry stage is not rewritten to Step3.
Fresh polling still requires the latest monitor execution; old durable bindings
can settle their original historical action but cannot settle a replacement.

The first exact native `failed` terminal for the source monitor persists a permit
bound to that reservation, monitor and original caller. It allows the same
caller to reach Worker waiting despite stale UI `query_unconfirmed`. An active
wait becomes ready only after a later POST with an independently validated nonce
Worker probe. Worker quiet, the original wait deadline and recovery budget remain
separate checks. The permit does not settle a replacement monitor.

R4 failure and cleanup consume the same full native snapshot through the existing
authenticated internal request channel. The backend chooses the protected stage
from trusted run/route state, not from the supplied snapshot's stage. Unknown,
missing or stale observations preserve state and ownership. A fresh matching
failed receipt can project the real failure despite an old UI-only reconnect
diagnostic. Cleanup retains transfer receipts, lease ownership and Worker quiet
requirements; a failed monitor process is not proof that Workers stopped, and
a successful Step2 handoff is not a completed analysis.

## UE-05 Airflow SSH transport boundary (2026-09-30; source only)

Airflow's WGS/GATK current Step1-6 and P0 dispatch/observe callers share one
OpenSSH connection layer. It keeps the registered command and restricted
identity fixed, uses a 30-second handshake with OpenSSH internal attempts
disabled, and allows at most three pre-session connection attempts with
5/10-second backoff within the original single call budget. A separate WGS
request-visibility business retry retains that same failure count and deadline.
Only fully recognized
pre-session exit-255 failures with empty stdout can be reconnected. A mixed,
authenticated, post-session or timed-out command does not qualify for write
replay. The P0 Step4 120-second dispatch, 30-second read probe and Step3
150-second Worker probe limits retain any earlier frozen deadline. One
logical probe may reconnect its SSH session, but its nonce, backend decision
and Worker quiescence budget are unchanged.

Transport outcomes are not native stage terminals. Ambiguous marked submits
are reconciled through the UE-04 exact `execution_ref` observation; an unknown
snapshot cannot permit a second launch, downstream transition or release.
The connection layer cannot create an attempt/generation, run biological work
for the duration of a stage, spend a recovery budget or grant P0 redispatch.
No native SSH retry engine or production runtime installation is included.

## UE-05 final writer query window (2026-09-30; source pairing in progress)

The registered Step6 final writer now creates one local monotonic 120-second
read window. Both full native workload inventories, including the fresh CAS
proof, and the paired native directory-lock release receive the same absolute
deadline. Each workload query remains at most 30 seconds. Only typed native
`TRANSPORT` and `SERVICE` failures reconnect that read-only query with
deadline-bound backoff, starting at 2 seconds and capped at 5 seconds.
Malformed, incomplete, conflicting or active inventories still fail closed.
The query retry sits inside the final inventory call, so it
does not rerun Step6 materialization or repeat the release write. The Step3
compute deadline and Step4 publish deadline do not govern later Step6 release.

The platform delta was exercised with a pinned native read-only query and a
stubbed lock release callback. It proves the platform deadline propagation
and fresh inventory calls, not the paired native lock signature, actual CAS,
installed wheel or live cloud behavior. The native owner validates the lock
path separately before paired delivery. Missing lock/journal without trusted
release proof remains an unknown outcome; the platform does not reconstruct a
lock or infer release from a missing Job.


## UE-04 receipt and native terminal convergence (2026-09-30; source only)

WGS normal and P0 recovery Step3 registration require the latest successful
Step2 receipt and bind its execution ID, generation and receipt hash. A late
Step2 sidecar is ingested once after the first registration transaction releases
its run lock; the caller then rechecks the current attempt, DagRun, recovery
action and stop state under a new lock. Reused Step3 registrations and frozen
recovery requests must still match the current predecessor tuple. This does not
launch Step2 again or authorize a new Master.

For a newly marked WGS/GATK Step6, the existing business status receipt alone
does not prove native completion. The finalizer checks the latest registered
Step6 generation and exact receipt digest, then requires a fresh complete
`cce.stage-execution.snapshot.v1` from the fixed read-only native observation:
`state=succeeded`, matching execution ref and `evidence_ref`. Observation
health remains an independent field; `unknown` cannot finalize. WGS uses the
SHA-256 of the exact status sidecar bytes, while GATK retains its canonical
receipt hash. Neither Airflow task success nor a private control receipt by
itself substitutes for both matching pieces of evidence. Legacy unmarked
requests keep their historical receipt behavior. These source changes have not
been deployed to node200 or a production environment.

The WGS frozen request digest is rechecked against the current execution before
choosing the marked or unmarked Step6 finalization path. The original producer
hash excludes the six execution-envelope fields, and excludes the later-added
v2 version for initial dispatch; recovery retains the v2 version in its hash.
Removing a marker or changing the version therefore cannot downgrade a current
marked execution into receipt-only completion.

For Master TTL handoff, platform registered Step4/5 already pass the selected
Master bundle and exact UID to the pinned native entry; native commit `4fa85874`
adds a separate ordinary v2 Step4/5 fallback to the persisted handoff after a
valid terminal. The existing platform selected-Master test stubs log download,
and the native ordinary-path test directly covers Step4/log export but not a
direct Step5 invocation. Source call-chain inspection does not prove an active
deployed policy pin or full paired TTL acceptance.

## UE-03 shared workload inventory (2026-09-29; source only)

The native query source at commit `6f5c120` accepts fixed, read-only
`_recovery_query(config, "jobs", "--chunk-size=0", timeout=...)` and the
corresponding `pods` form. It retains typed query errors, the 4 MiB response
limit, and rejection of incomplete or paginated lists. Platform workload
observation now uses this interface only; it does not construct a second
kubectl/subprocess path.

Each proof reads complete run-label Job and Pod lists, complete namespace Job
and Pod lists, and the exact current Master Job. A shared in-memory index
compares the two lists by frozen name, UID, run label, Pod owner, terminal state
and container exits. A namespace object from another run is ignored unless its
name, UID, label or owner conflicts with the bound run. A missing Worker
requires its validated persisted terminal and no residual Pods; 404 alone is
insufficient. A changed but individually valid inventory raises
`InventoryMoved`; an identity or terminal conflict fails closed. Active
Workers can be counted for observation but cannot satisfy recovery or final
writer release. Release and lock CAS take fresh proof rather than reusing a
previous list. Total query budget is at most 120 seconds and each native query
at most 30 seconds; the original compute deadline further bounds recovery
inspection when one was frozen.

`probe_bound_workloads` uses the same index. Its run label comes from the
native `master_job.run_label` transformation of the validated submission
context's raw `run_id`; the raw ID is never used as a Kubernetes label. This
helper still requires the exact failed Master and its terminal Pod because
that earlier submission snapshot does not contain a sufficient persisted
replacement for the Pod diagnostics. The final recovery path accepts TTL
reclamation only with complete persisted native FINAL and Worker terminals.
These are observations, not dispatch or deletion authority.

The Heavy global collector excludes only Jobs with the explicit native
`cce-pipeline/action=evidence-reader` annotation. Native evidence-reader and
directory-probe helpers carry this annotation even when copied from the
Master template. Unmarked WGS Masters with missing Heavy configuration still
produce `master_configuration_inconsistent`; GATK Masters keep their existing
quota separation. The source change does not alter any production Job or
snapshot. Native directory-probe retry and original stage deadline handling
are tracked separately by the native UE-03 owner.

The only current platform writer entry with an applicable frozen absolute
deadline is registered Step2/3 compute recovery: `resume_registered` validates
the exact request, checks `cce_recovery_deadline`, and passes that same epoch
to the native writer's optional internal probe limit. Without that field it
uses the existing writer call. Ordinary Step3 observation skips writer
validation. Step4's `publish_deadline` applies to fresh dispatch only;
reattachment and an already started business worker must not inherit it as a
probe or stage-completion deadline. Ordinary Step1/4/6 have no applicable
frozen absolute deadline. The native directory probe retains its own bounded
read-only operation budget, without creating a new stage lifetime.

## UE-02 native gate wiring (2026-09-29; source only)

Native cce-pipeline source `6c0aee2` permits an absolute, generation-private
`status_path` outside the request/dispatch directory and exposes
`writer_quiescent(ref, locks_held=True)` for callers holding both exact stage
locks. `scripts/cce_stage_execution_adapter.py` binds only the already
registered WGS or GATK Step1–Step6 request to one native `StageExecutor`.
The selected gate, paths, worker command and business handler are deployment
owned; request fields cannot select a module, path or command. An explicit
invalid or null `stage_execution` marker fails closed. Unmarked frozen requests
retain their legacy gate path.

The adapter atomically freezes exact request bytes, the selected batch binding
and native ref in a private 0700 directory with 0600 files before native submit.
Each generation has a distinct private terminal control receipt. The handler
continues to write the existing shared business `.status.json`; after it
finishes, the adapter validates exact identity, WGS/GATK schema, terminal state
and GATK receipt hash before publishing the matching private control receipt.
The reader checks that receipt against the frozen registration and, while the
generation is current, the business status. An older ref resolves from its
immutable private registration, with any available backend request history
checked for equality. A valid older shared dispatch may precede a new
generation's first freeze; native submit still requires its terminal receipt
and quiescent process group. Missing, conflicting or legacy evidence remains
closed. `compute_identity` is currently null; it is not inferred from business
status.

WGS and GATK new-marker gate entries submit to the shared native executor;
their existing business stage functions remain the handlers. Old worker CLI
entries reject a new marker. WGS retains the native-open `.worker.log` while
archiving the prior generation's shared status, so a new live log is not moved
into history. The paired recovery and final writer call native
`writer_quiescent` while holding both stage locks, and reject missing request
files if a WGS `<stage>.json` or GATK `<stage>.request.json` still has private
registration or terminal evidence.

Step4's explicit publish-dispatch path retains registered request/hash checks.
For an opted-in publish deadline, a **fresh** native launch checks it under the
native launch lock; a duplicate may reattach after expiry. Ordinary Step4
requests without the publish opt-in use their existing business handler and
stage timer, with no invented publish deadline. Native Step4 observation uses
the exact private dispatch/terminal binding; unknown evidence is uncertain.

This slice changes source only. DAG/backend acceptance of asynchronous native
launches, shared observation and recovery transition policy belong to UE-04.
GATK `resume` is not activated in the shipped registry. If a backend overwrites
an active old request before it can publish its terminal, the result stays
unknown pending reconciliation; no receipt is fabricated. No wheel was
installed, and no node200 or production state changed. The BS10610 synthetic
candidate ran the four focused platform files against native source `6c0aee2`:
30 passed; independent four-item delta review reported Ready with no remaining
Critical or Important finding. Exact log, JUnit and input hashes are in the
latest `HANDOFF.md`.

## Unified stage execution v1: UE-01 contract (2026-09-28)

New WGS and GATK Step1–Step6 stage requests freeze the top-level extension
`stage_execution: {"protocol":"cce.stage-execution.v1"}` before computing their
existing `request_hash`. The platform `orchestration_contract_version=2` remains
unchanged. Existing frozen requests retain their original bytes and hashes;
legacy WGS re-entry returns the matching registration without adding the marker,
and the immutable GATK prepare request remains outside this stage protocol.

The pathless `ExecutionRef` carries `protocol`, registry-key `pipeline`,
`analysis_id`, `attempt`, `stage`, `execution_id`, `stage_generation`,
`request_hash`, and `registration_sha256`. Platform `generation` maps to
`stage_generation` only at the adapter boundary; the existing seven-key
`platform_execution` object is unchanged. Identity tokens use 1–256 ASCII
characters, beginning with an alphanumeric and continuing with alphanumerics,
underscore, dot, colon or hyphen; attempt and generation are positive integers
(not booleans). The registration digest is SHA-256 of canonical UTF-8 JSON
using sorted keys, compact separators, `ensure_ascii=False`,
`allow_nan=False`, and no trailing newline. Its envelope contains the eight ref
identity fields other than `registration_sha256`, plus the trusted frozen
`runtime_binding`. Mutable state, runtime evidence and post-registration CREATE
deadlines are excluded. A deadline already frozen in the request is covered by
its `request_hash`; deadlines remain governed by their original stage-specific
source and timer. The public ref has no deadline, filesystem path, command or
module field.

`ExecutionSnapshot` uses schema `cce.stage-execution.snapshot.v1` and carries the
complete `execution_ref`, state, opaque `evidence_ref`, nullable process
`runtime_identity`, separate nullable CCE `compute_identity`, and independent
`observation_health`. States are `accepted`, `running`, `succeeded`, `failed`,
`canceled`, and `unknown`. Platform `success` maps to native `succeeded`; `failed`
and `canceled` retain their meanings. `unknown` must be marked degraded and does
not overwrite the last confirmed platform state. It never authorizes another
dispatch, stage advancement, lock release, or recovery. Read-only `canceled` adds
no cancellation API and does not prove remote compute quiescence.

The node200 gate/operator Python owns the deployment-fixed resolver and
`(pipeline, stage)` handler registry. Unknown or disabled registry keys fail
closed. The Airflow container does not import the native wheel or accept a
request-selected path or command. UE-01 adds the contract mapping and request
marker only; later lifecycle work remains separately gated. The sole platform
fixture is
`scripts/tests/test_cce_stage_execution_contract.py::test_current_execution_contract`,
run on BS10610's synthetic test environment.

UE-04 source gate bridge: marked WGS/GATK Step1–Step6 submit commands serialize
the complete native `ExecutionSnapshot.to_dict()` result, preserving its exact
execution ref, native state, evidence ref and independent observation health.
They do not infer business success from an accepted launch or SSH exit code.
The restricted GATK `--native-observe` command requires the current frozen
analysis, attempt, stage, execution ID, generation and request hash, then calls
the shared adapter's read-only `observe(ref)`; WGS uses its corresponding fixed
command. Marked DAG dispatch uses the fixed restricted `--native-submit` with
the same six identity fields and rejects a superseded generation or hash
before any native submit; the adapter independently rechecks frozen bytes
under its launch fence. The old `wgs-runtime`/`gatk-runtime` CLI shape rejects
marked requests, while unmarked frozen requests retain their existing path.
Step4's separately authorized `--publish-dispatch` keeps its exact hash fence.
`unknown` is returned as evidence for same-ref reconciliation and never
authorizes another launch. This source bridge is not deployed to node200.

## Paired request validation (2026-09-27)

WGS initial dispatch hashes the body before adding the v2 execution envelope,
including `orchestration_contract_version`. Same-attempt recovery retains version2
in its frozen body before hashing; `resume_action_id` selects that existing producer
contract. The paired consumer preserves both contracts without rewriting requests.
GATK digest coverage is unchanged. Request/public equality, execution identity,
predecessor and v2 entry checks remain mandatory.

WGS requests live in REQUEST_ROOT, not in the runtime control directory. Validate
control_workdir through the gate and require the exact configured
RUNTIME_RUN_ROOT/analysis_id/attempt-N path. Do not equate it with request.parent,
allow an arbitrary directory, or move the existing request/journal evidence.
Producer-derived synthetic regression: scripts/tests/test_paired_request_contract.py.

Configuration-only release identity (2026-09-27): runtime stage requests preserve
the catalog's optional safe configuration qualifier after the source commit prefix.
No stage, workflow rule, request hash, frozen profile or execution approval behavior
changes. Legacy release identities remain valid; old requests are not rewritten.

## Operator schema compatibility (2026-09-27)

The WGS gate uses one release transformation for prepare materialization and
Step7 frozen-config comparison. Native Operator schema3 may omit legacy `paths`;
the gate must not inject a dummy section. Legacy configs still require a mapping
and receive the allowlisted release repository override. A present malformed
`paths` remains rejected. Obsolete OBS fields are removed identically in both
paths. Native schema validation, release validation, exact attempt path and
frozen-content checks remain in force; this does not change workflow execution.

## Resume feasibility clarification (2026-09-27, source audit only)

Preserving Step2 WAITING/START/START_CONFIRMED and Snakemake checkpoints does
NOT preserve a requirement for the old Master Pod to stay alive. Reconnection
adopts the active UID/generation; terminal replacement uses a new UID and the
next compute generation, preserving analysis/attempt/config/workdir/results.
The paired Resume path calls native `_advance_recovery_view`; it permits an
absent old Job only with bound final evidence and complete writer exclusion.
Legacy non-paired recovery is not proof of TTL compatibility. Missing FINAL,
submission snapshot or Worker terminal proof blocks replacement, including hard
crashes that cannot seal them; a basic FAILED display is not recovery authority.
Current FAULT01 proves only same-UID CREATE reconciliation, not replacement or
skipping successful rules. The cross-Master live acceptance remains open; this
audit neither launches it nor changes the authorized smoke budget. See
[current feasibility review](46_JOB_TTL_CROSS_MASTER_RECOVERY_DESIGN.md).

## P0 normal-path convergence (2026-09-27, approved; implementation pending)

The user retains timely Master/Worker cleanup (TTL100) and the production
Step1–7 business flow. Directory fencing protects concurrent writers even under
one account; it is not user authentication. A new probe Job on every write is
not required by the contract: prefer existing trusted storage/current-Master
access, with a bounded read-only helper only when no valid route exists.
Keep current owner/generation/CAS and fresh storage identity checks; no stale
probe cache or assumed node200 NFS/cloud-SFS equivalence may authorize writes.

Verified read-only helper cleanup delay is a separate operational condition,
not analysis failure; exact UID/RV cleanup, durable journal and bounded residual
count remain mandatory. Unconfirmed identity still blocks. This approved change
supersedes the historical requirement below that helper absence must always be
confirmed before business work. Actual source/test completion is recorded later.
Preserve startup diagnostics before short TTL where possible; missing evidence
remains UNKNOWN and never authorizes replacement. Reuse the two approved smoke
cases and existing budget. Candidate version remains0.8.7; rebuilt artifacts need
new hashes/digests and matched consumers even when their version/tag is unchanged.

For cloud-only access, the existing per-run helper journal may reuse its one
still-Running read-only helper. Each use verifies exact Job/Pod UID, volume
binding and non-deleting state before/after executing a NEW probe; never return
the journal's old result as fresh proof. Its original600s active deadline is not
extended; terminal TTL remains100s. Final Step6, business failure or switching
to a trusted Master initiates precise cleanup. A pending old deletion must be
reconciled before another helper CREATE; no persistent helper service is added.
This bounded reuse matters because ordinary Step1/2 precede a running Master
and Step4–6 follow its termination; a Running-Master fast path alone would not
remove those normal-path helper creations. Acceptance records actual counts.

## P0 normal-path internal contract (2026-09-26, implementation in progress)

This slice preserves automatic Step1–6, frozen preparation inputs and the existing
recovery policy/budget. It adds no public API, database table, pause/delete operation
or manual binding step. Source/test changes are not deployment acceptance.

The existing static deployment policy remains schema2 with the same trusted source,
interpreter, storage and journal-root fields. New per-run registrations are schema3
records beneath that controlled `journal_root`, not new entries in its global
`bindings` array. Historical schema2 bindings remain an explicit compatibility path.
`writer_for_bundle` exposes the validated `registration_schema_version`:3 requires
the shared current-owner resolver;2 retains the historical platform receipt,
journal and exact ConfigMap owner checks. An absent/invalid dynamic registration
does not silently become a legacy registration, and action-name prefixes are not
used to infer protocol versions.

The pinned native runtime directly exports these internal functions (the native
guard implements them); request data cannot choose their executable or location:

- `register_bundle(runtime, bundle, contract, config, *, identity, control_root)`:
  `identity` has exactly `pipeline`, `analysis_id`, integer `attempt`; `control_root`
  comes from the validated gate request path's parent. The restricted Step1 path
  registers after successful prepare, before its first protected operation. Native
  frozen hashes, resource identity and the fixed control root are persisted
  idempotently; conflicting registration is rejected rather than overwritten.
- `initial_owner_action(*, pipeline, analysis_id, attempt, run_id)` returns
  `initial-` plus the first32 hexadecimal SHA256 characters of the canonical stable
  identity. It exists before Step2; the later stage `execution_id` remains separate
  in authenticated requests, submission journals and handoff receipts.
- `_prepare_submission_view(..., owner_action=writer.context['action'])` propagates
  that stable initial owner. Native Step2's second view preparation uses the same
  owner action; acquiring a Master UID conditionally binds the initial lock without
  changing its generation/action or rewriting the original bundle.
- `resolve_current_owner(runtime, bundle, contract, config, *, selected_bundle=None,
  expected_master_uid=None, read_only=True)` returns `selected_bundle` (Path),
  `expected_master_uid`, `context`, `platform_execution` and `record`. It scans at
  most4096 existing submission/recovery/resume journals only under the registered
  control root, validates frozen inputs/handoff/lineage and matches the exact current
  ConfigMap owner. Zero/multiple matches and symlinked/foreign state reject; mtime is
  not authority. Supplied platform selection is checked, not trusted as a bypass.

Step1 has no selected Master and does not call current-owner resolution. Ordinary
CLI status resolution neither claims a writer lock nor creates a cloud reader.
The subsequent Step3 observation may retain its existing identity-bound evidence
reader with read-only storage mounts and observation cache; this is distinct from
a writer storage-identity probe. Platform calls native Step3 with `read_only=True`
to skip the protected writer claim while retaining call-scope validation.
Platform receipt/predecessor validation is retained in addition to native current
owner validation. TTL-absent Jobs require identity-bound durable native terminal
evidence; absence alone never means success. New business outputs/directories use
0644/0755; secrets and necessary private control state retain their private modes.
No historical input/result permission migration is included.

GATK prepare retains its immutable `gatk-airflow-prepare` request format. Only its
in-memory dispatcher identity projects `stage=prepare` and the existing generation
execution ID. It reuses the existing launch/worker locks and dispatcher sidecar,
including the actual process identity at termination. Final release/recovery checks
validate the unchanged request hash, exact terminal receipt and ended process;
a successful receipt or free flock alone is insufficient. A prepare retry may use
CLI generation2 while the immutable request remains generation1: launch authorization
records the exact new generation only after the previous dispatcher/receipt agree
on terminal identity and its process has ended. Terminal checks project that
authorized sidecar/receipt generation, not the immutable request's original one,
and reject a missing process identity. The explicit legacy no-sidecar prepare
launch remains supported without inventing old completion evidence. Step7 is unchanged.

## WGS 4.2.2 frozen prepare binding (R4, 2026-09-26)

The existing WGS restricted gate allowlists only the exact
`wgs-4.2.2-3b1dae5` immutable source under
`/bi/biodevrwbi/33.chenjiucheng/project/wgs-releases/20260926.1-wgs422/`.
Version `V4.2.2` uses the same generation-scoped prepare handoff request and
validated receipt path as 4.2.0/4.2.1. Backend stage-status must keep
`prepare_sampleinfo`/`prepare_analysis` artifact-pending until that receipt
exists; unknown versions remain rejected by the gate. Candidate registration
alone neither activates the release nor proves node200 can read the source.
See [R4 integration receipt](releases/2026-09-26-wgs422-p0-r4-integration.md).

## Step7 restricted reconciliation (2026-09-22 test candidate)

The existing runner accepts wgs-step7-status and wgs-step7-start followed by
analysis_id, attempt, maintenance_action_id and step7_generation. Both must match
the registered Step7 request. Probe does not execute cleanup, change locks or
rewrite receipts. It checks existing launch/worker locks, PID/boot/start identity,
orphan process group and exact status evidence. Missing or conflicting proof
fails closed. Start rechecks the registered identity under the existing launch
lock and uses the existing nohup/setsid executor. Old delayed requests cannot
start a newer action. Existing bare wgs-runtime commands remain supported.
Frozen cleanup target equality is checked on registration; retries preserve
the original target. Unowned partial remnants remain blocked. No new delete
implementation or changes to Step1–6/GATK/bioinformatics scripts.

### Step7 producer protocol scope correction (2026-10-02; deployed)

The shared WGS/GATK backend freezer marks new requests only when their actual
`stage` is `step1_upload`, `step2_master`, `step3_monitor`, `step4_publish`,
`step5_download` or `step6_materialize`. Step7 retains the legacy execution path
and its frozen cleanup bundle; GATK's independent cleanup registration also
remains unmarked. An explicit `stage_execution` must match both the supported
protocol and stage: null, malformed or unsupported-stage markers fail closed.
Matching existing unmarked registrations reuse their request bodies and hashes
without adding a marker or rewriting that historical identity.

This correction does not patch an existing marked Step7 request or sidecar.
A later retry needs explicit user authorization and follows the existing
maintenance context/probe/`stopped` flow: exact proof that the prior executor
stopped closes its stage as failed before a new unmarked generation is
registered. The prior database request/hash identity remains unchanged; the
existing runner can reuse the per-stage request filename when retry is
authorized, so preservation of that file's old bytes is not promised. A late
accepted sidecar cannot revive the closed generation. Retry and cleanup
scope remain subject to the
[test/production and data boundaries](34_TEST_PRODUCTION_RELEASE_BOUNDARY.md).

If a failed maintenance action already has a concrete error, a later empty or
default monitor failure callback retains that error. An exact successful runtime
receipt still takes precedence. Source `fd855934` is deployed on BS10610 and
BS96 after focused synthetic acceptance and both coordinator review gates;
see the [release record](releases/2026-10-02-step7-run-pages-fix.md).
The original failed Step7 action was not retried and no actual cleanup was
performed during this release.

## P0 correction interface (2026-09-25, isolated source accepted)

Checkpoint297bcee replaces UID-0 selection with fixed code-adjacent
`cce-paired-deployment-v1.json` beside the platform entry and installed native
guard. Deployment, not a business request/environment override, declares the
policy and per-component maintainer UID/GID roots plus the approved canonical
interpreter. Schema2 source pins and per-directory execution binding remain.
Absence of the bootstrap retains legacy selection; a present invalid deployment
does not silently fall back. Native/platform bootstrap contents must agree.

Shared P0 directories/files use collaborator permissions; private plugin live
claim/journal state is exported by the same Master as shared final evidence.
No historical project permission migration is implied. Native ae90b65 and the
paired follow-up close interpreter-target ancestry, owner authority and existing
legacy-directory compatibility findings. The original registered compute deadline
bounds at most three fresh observations of typed same-identity inventory movement;
UID/owner/run-label/terminal conflicts remain immediate refusal. Present Worker
Jobs reuse the complete Job LIST, but exact missing-Job GETs and every job-name
Pod LIST remain. This is source acceptance, not installation/activation. The older
UID-0 source-gap entry below is historical.

## P0 non-root entry correction (2026-09-25, documentation contract)

The user-confirmed multi-account deployment does not require root-owned Python,
scripts, policy or identical ancestry owners. `operator-owned` below means the
approved maintainer for that component, not UID 0. Fixed `/etc`-only activation
is also withdrawn as a deployment requirement. Preserve the existing `nipttest`
Operator test environment and separate control/source/execution roles.
See [authority, retained protections and bounded follow-up](13_SECURITY_AND_OPERATIONS.md#p0-non-root-deployment-correction-2026-09-25-user-confirmed).
Both the platform selector and native writer guard still implement the conflicting
UID-0 checks; `P0-NONROOT-ENTRY` is open. Historical source/synthetic acceptance
below is not proof of real multi-account activation. No runtime was changed by
this documentation correction.

## Selected Step3 terminal conflict fence (2026-09-25, source only)

The identity-bound native terminal must not contradict the current live Master
Job terminal: Failed/native success and Complete/native failure both reject
before a terminal status is emitted. The paired monitor's existing query owner
marks the control observation unconfirmed, not compute failed/succeeded. Matching
terminal conditions and TTL-absent Jobs with valid native evidence retain the
existing behavior. Native1bc67fd; BS10610 affected monitor/downstream13 pass.

## Task6 confirmed Step3 re-entry (2026-09-25, source only)

An exact current Step3 action whose native recovery journal is already started
reconstructs its selected Master through the existing read-only validator.
It does not require a reclaimed Job to reappear or retry replacement/START.
The journal is only a locator: registered source hash, complete native handoff,
frozen inputs, original producer compute deadline and current directory owner
must all agree. The subsequent ordinary monitor still verifies terminal evidence;
absent Job/FINAL is not success. Partial/uncertain handoffs retain the existing
reconciliation path. No untrusted journal grants a new owner or resets deadline.

## Task6 manual observer boundary (2026-09-25, source only)

Failed query observers do not settle automatic compute actions. Explicit existing
Step3 Resume may hand off their exact confirmed current controller after a scoped
blocked/exhausted observation; it still uses existing frozen-request validation
and runtime active/terminal/quiescence checks. Only observer authority is retired.
No new compute permission, CREATE/START retry or history rewrite. Same attempt,
compute budget and original deadline persist; GATK manual Step3 registration now
copies that deadline instead of silently dropping the selected query contract.
Historical untagged requests do not gain an automatic policy/deadline.

## Task6 selected-monitor finite reconnect wiring (2026-09-25, source only)

Supersedes the unwired prerequisite below. monitor_registered builds one owner
only for the operator-selected v2 Step3 with a registered original deadline.
Its in-memory native _monitor_query_runner hook is internal, not a request option
or new executable selector. Strict GET and selected legacy JSON GET share it;
list reads request all items. No hook on _run, CREATE, START, transfers or whole
stages. Unmarked legacy monitors retain their ABI/behavior.

Existing worker lock and stage status JSON own monitor_reconnect. Every load/save
revalidates registered request bytes/hash and exact typed execution/generation;
status must exist and be accepted/running. A missing, foreign or terminal sidecar
cannot start a fresh budget. Reservations are durable before requests; the GATK
path additionally fsyncs file and parent. ProtectedWriter still compares exact
config: a stable closure preserves one owner through its config deepcopy.

Only a complete selected-Master observation calls confirmed(). Query exhaustion,
permission/auth/invalid response or selected identity/control error stops without
replaying the monitor or inferring remote failure. Outer worker failure writers
preserve the marker. True returned terminal workload evidence retains its usual
failure/recovery path. The existing backend consumers retain the reduced scoped
observation and suppress fresh analysis/stage failure projection while the query
is unconfirmed; callbacks and periodic DagRun sync use the same fence. This is
negative evidence only, never automatic compute permission or terminal success.

BS10610 source checks: regression113, final affected producer/consumer16 and
actual protected selected new/legacy monitors4 pass. Paired native fd43f88;
no Task5 artifacts rebuilt or production/runtime activation. Final automatic
lifecycle/manual reconnect and PG/whole-plan acceptance remain open.

## Task6 finite query owner prerequisite (2026-09-25, not yet wired)

Internal scripts/cce_query_reconnect.py accepts only a trusted typed read-only
GET callback plus current scope (pipeline/analysis_id/attempt/stage/execution_id/
generation/request_hash) and original absolute deadline. No runtime dispatch,
new table, public route or native activation is added. Its load/save callbacks
are reserved for the current monitor's existing stage JSON under its existing
exclusive execution lock; the actual WGS/GATK wiring is still outstanding.

First call + max6 retries use30/60/120/240/300/300s. Query timeouts are <=30s and
remaining original deadline; late success is not accepted. Save reservation
before request, fail closed on failed persistence, retain consumed in-flight
retry on restart. Stored phase: healthy/waiting/querying/observing/blocked/exhausted;
scope/deadline/retries/first_error/last_error/last_success/next_retry/reason remain
internal query-control fields, not workflow statuses or terminal proof. A partial
GET only reaches observing; caller-confirmed complete authoritative observation
is necessary to clear the outage. Exhausted/blocked replay cannot self-reset.

Paired native _recovery_query supports exact Job and ConfigMap GET and complete
Job/Pod lists, with typed errors and a caller-shortened positive timeout <=30s.
ConfigMap support repairs the selected observer's existing directory-lock call.
Only known transport or server failures are retry candidates; generic connection
text, auth/certificate, permission, local command or malformed response is not.
No raw diagnostics enter the budget. Legacy _kubectl_json behavior is unchanged.

BS10610 isolated native24/platform17 tests pass. Neither monitor has activated
the helper yet; CR-04 still requires producer/status/consumer integration and
must not infer reconnecting from degraded health alone. No Task5 artifact refresh.

## Task6 Step4 hash-pinned dispatch caller (2026-09-25, source only)

Supersedes the unwired observation checkpoint below. First eligible registration
hashes publish_dispatch_version=1 and publish_deadline. The existing stage-control
route/runner/sensor consumes begin/check/finish/poll; no new execution is created
for same-operation redispatch. Fixed --publish-dispatch ANALYSIS_ID ATTEMPT
GENERATION REQUEST_HASH accepts only the registered Step4 request. WGS validates
the loaded payload again under the existing launch lock; GATK checks the supplied
hash under that lock before any intent/spawn. Both reject an expired original
deadline. Existing duplicate/ambiguous launch guards and WGS release-runtime pins
remain in force. Ordinary unmarked native invocation is unchanged.

Lost response means reconcile, not replay. Normal stage receipt is still the
sole success authority for subsequent stages; no native publish-record synthesis
or output scan. Tests are synthetic on BS10610; wrappers are source-only, neither
shared installation nor native/plugin/image artifacts were updated or activated.

## Task6 original Step4 observation (2026-09-25, source only)

Both restricted wrappers accept fixed --publish-probe ANALYSIS_ID ATTEMPT
GENERATION REQUEST_HASH NONCE. The registered contract-v2 Step4 request must
explicitly carry integer publish_dispatch_version=1 in its canonical hash.
Legacy/unmarked requests cannot obtain negative launch evidence. No arbitrary
paths, commands, publish, archive, hash sweep or cloud I/O is performed. Probe
may create/acquire only existing request-adjacent lock files; JSON evidence is
unchanged. Output binds the nonce and exact original operation identity.

Under the launch lock, validate current request bytes and matching worker/status
records. Existing success/failure receipts are authoritative (including GATK
receipt digest); exact live process identity reports running. Lock contention,
dead parent without terminal evidence, accepted intent without PID or incomplete
records remains uncertain. Malformed/foreign evidence rejects the query. Only
no records AND free launch/worker locks reports not_started at that observation;
that is not a standalone retry permission and must be rechecked at dispatch.

Opted-in WGS start_async_stage revalidates the registered request under its
launch lock and refuses repeat spawn after ambiguous intent. Existing GATK
intent/worker fencing is unchanged. No original failed receipt is rewritten.
Backend RunAction budget additionally requires no in-flight SSH, fresh post-delay
proof, current identity/control state and the original deadline; max2 retries
60/180 independent of compute budget. Caller crash retains in-flight ambiguity.
No automatic marker producer or Airflow caller is enabled yet: wiring/fenced
original-identity sends are the next Task6 slice, before any activation.

## Task6 exact CREATE classifications (2026-09-25, source only)

The plugin adds WORKER_CREATE_STORAGE_RPC_UNAVAILABLE from exact CREATE Status500
RPC Unavailable/peer-reset failures, projecting to worker_create_storage_rpc_unavailable.
Both inventory and backend validate fixed operation=create_namespaced_job,
integer http_status=500, status_reason=InternalError and
transient_reason=STORAGE_RPC_UNAVAILABLE_PEER_RESET. The original deterministic
Job is reconciled first: PRESENT adopts, UNKNOWN blocks replay, ABSENT may use
the existing bounded submission budget. Exhaustion, complete single-cause evidence,
Master terminal and fresh quiescence remain required for platform reservation.
mutation.gatekeeper.sh Status500 context-deadline now shares admission timeout;
policy denial/generic500/missing Status are not eligible. No new API or budget.
Task5 frozen artifacts unchanged; source validation is not production activation.

## Task6 fresh Worker wait observations (2026-09-25, source only)

The automatic failure collector may report known same-owner active Worker
Job/Pod counts from complete live inventories alongside the original native FINAL.
This is wait evidence only: the normal replacement probe remains strict and still
rejects active workloads, unknown ownership, pagination, changed UIDs or missing
terminal proof. The Master and its Pods must already be terminal.

Both restricted wrappers recognize the fixed command:
`--recovery-probe ANALYSIS_ID ATTEMPT GENERATION REQUEST_HASH NONCE`.
It reads the current registered failed Step3 request/receipt, validates the
operator-pinned runtime, selected native producer, directory owner, retained
lineage and complete fresh Job/Pod inventory. It returns only the bound challenge
and verified failure evidence. It does not call Step3 execution, touch START,
create/delete Jobs, rewrite the failed receipt/FINAL or register a generation.

Existing Airflow action persists wait start/deadline and probe nonce; zero-active
evidence alone is insufficient if FINAL/candidate/producer changed. Wait is at
most600s and never exceeds the original compute deadline. No automatic Worker
kill or new scheduler. If a Worker disappears without its persisted terminal
proof, observation remains ineligible even if it may have finished successfully.
Production wrappers/policies and accepted Task5 artifacts are NOT updated here.
BS10610 final focused17 backend/producer +2 restricted entries +4 Airflow cases
passed; full Task6 and live rollout gates remain open.

## Task6 original deadline consumption (2026-09-25, source only)

The authenticated `cce_recovery_deadline` is now consumed by both restricted
Step3 monitor loops and passed through the internal RecoveryCapability to native
replacement. It is a timezone-aware absolute timestamp, never initialized or
extended by a controller restart. Invalid present values fail closed; absent
values preserve historical/default-off manual behavior, including the accepted
Task5 native call signature.

Native recovery journals bind `compute_deadline` separately from the handoff
deadline. Replacement entry, old-Master DELETE, new CREATE and handoff check the
remaining budget. The original handoff deadline is capped at the lesser of its
600-second allowance and the original compute deadline; journal replay cannot
change either. WGS/GATK poll sleeps use only remaining time and restart does not
grant a fresh timeout. Existing individual query timeouts remain in effect; no
new asynchronous interruption or kill is introduced.

This is a controller/monitor deadline, not a new Kubernetes cleanup policy:
expiry raises a manual-reconciliation failure, retaining journals/evidence and
any already-created Job. It does not kill Master/Worker, patch Job native
activeDeadlineSeconds, alter frozen biological inputs or enable recovery policy.
Bounded natural Worker wait is covered by the subsequent checkpoint above;
active/uncertain Workers still prohibit replacement.
BS10610 targeted22 GREEN16.25s; Task5 artifacts remain unchanged.

## Task6 initial deadline registration (2026-09-25, source only)

Enabled new CCE runs freeze the monitor timeout at creation and set matching
policy/budget original_deadline on their first Step3 registration. Its registered
request includes cce_recovery_deadline in the canonical hash. WGS replay inserts
the same field before hashing; GATK replay keeps its existing registered request.
Legacy/manual different-attempt registrations receive no fresh automatic budget.
The deadline is carried to replacement requests and consumed as described above.
Caller wiring must not be treated as permission to enable automatic recovery.

## Task6 due-dispatch source boundary (2026-09-25)

Internal cce_compute_dispatch consumes an already validated/reserved schema2
action. Before due time it does not rewrite the request; at due time it rechecks
policy/budget/control/current evidence, freezes the existing Step3 request and
reuses adapter registration plus shared Resume dispatch. Only Step3 and needed
downstream stages are selected; same attempt/config/directory/output preserved.
One cce_compute_recovery action owns both reservation and dispatch (not a nested
resume_stage action). A prepared crash must revalidate its source receipt.
WGS/GATK recovery requests carry cce_recovery_deadline from original_deadline.
Subsequent Task6 checkpoints added native deadline consumption and Airflow
polling/policy freeze; no installed runtime/automatic capability is enabled here.

## Task5 accepted offline Job TTL contract (2026-09-24)

New Worker/Master and existing evidence-reader Job.spec TTL100, never Pod TTL.
Derived initial/resume manifests preserve it without rewriting frozen bundles.
Master backoff0/restartNever/deadline259200s, reader timeouts/cleanup/mounts and
maintenance/Step7 remain unchanged. Missing Job alone never proves terminality;
durable identity-bound evidence remains required, otherwise UNKNOWN/fail-closed.
Only isolated test artifacts accepted; no production CLI/policy/image activation.
Exact paired pins and actual-wheel/image evidence:
[Task5 provenance](releases/2026-09-24-p02-task5-offline-artifacts.md).

## Task4 accepted manual continuation contract (2026-09-24, source only)

This section supersedes the limited-entry/open statements in older checkpoints
below. It uses existing authenticated services, DAGs, request spool, RunAction
and receipts; no new public API/table, retry framework or automatic activation.

- Registered Step2 initial submission uses its own derived view and durable
  submission journal. Uncertain CREATE is queried by exact identity; a subsequent
  manual observer reconciles the original view and deadline. Confirmed native
  handoff and pending-to-UID CAS can be replayed after a controller crash.
- Registered Step2/Step3 Resume resolves the exact current directory owner from
  native journals, not latest mtime/status. Active Master is observed; failed
  Master replacement needs native final evidence and full writer exclusion.
  `registered_source` retains generation lineage; original frozen bundle and
  delivery roots do not change. Missing legacy identity stays fail-closed.
- Every new process revalidates current request, adapter-specific digest,
  original producer registration (including archived generation), native view,
  frozen hashes and exact directory owner. An observer does not become the
  submitting producer. `VerifiedMasterResult` is rebuilt only after validation;
  WGS reattach does this before archiving the old terminal receipt.
- Step4–6 use the registered predecessor's normal success receipt/hash and
  selected native success. Child command carries registered IDs, not arbitrary
  paths or serialized capabilities. GATK retains its approved materialization
  root. Step6 releases only after materialization and verified all-writer
  quiescence; an already RELEASED replay rechecks evidence without rewriting.
- Native bd41f87 seals only this generation's manifest rows plus the unmodified
  shared-history digest. Platform `lineage_workers` validates registered ancestor
  terminal snapshots and reconciles all bound Workers against complete live
  Job/Pod lists for replacement/final release. Retained terminal Workers are not
  confused with unknown Workers; unknown, active or conflicting objects block.

BS10610 actual-source synthetic checks: selected41 passed/1 WGS-only skip,
authenticated service/real DAG/native/normal-receipt flows2 passed. Only external
HTTP/SSH/Kubernetes/OBS transport and temporary SQLite are simulated; this is not
live Airflow scheduling, PostgreSQL contention or cloud TTL verification.
Operator-owned policy/source pins, mapped storage and per-run bindings remain
mandatory and uninstalled. Pair native/platform consumers before Task5 activation;
no image/wheel/CLI deployment, old bundle migration, TTL or automatic enablement.

## Task4 fresh-process selected monitor (source only, 2026-09-24)

The internal monitor_registered resolves only the successful
registered Step2 producer of a Step3 request. It recomputes existing adapter
request/receipt digests, derives the native view from the recovery journal and
checks frozen hashes, handoff, producer identity and exact v2 directory owner.
Receipt JSON alone never restores VerifiedMasterResult authority. Native Step3
uses the selected mirror, filters current Master UID/Pod UID and fences native
startup/terminal identities; run_id-only legacy run-state cannot decide the new
Master's status. No original bundle rewrite, replacement or lock takeover.

Actual WGS/GATK polling loops consume this reader and pass a copied selected
binding to the existing rule-evidence bridge, without redirecting the original
delivery root. Successful registered Step2 identity remains distinct from the
observing Step3 execution. Old workflow completion markers alone never prove
replacement success. Job disappearance requires bound native success or sealed
failure evidence; it does not authorize another CREATE or release the lock.

BS10610 focused18 and affected5 checks passed with native903e1af. No deployment
or paired policy installed. Direct Step3 replacement, initial submission-view
selection, Step4-6 reconstruction/final release and manual end-to-end acceptance
remain open; Tasks5/6 are not enabled by this source checkpoint.

## Task4 registered Step2 recovery entry (source only, 2026-09-24)

Internal resume_registered composes the existing paired runtime, operator
per-bundle registration and RecoveryCapability; it is not an API or retry
engine. WGS hashes the registered body excluding its six execution metadata
keys, GATK excluding request_hash only, matching their existing registration
services. Request bytes must still match the restricted worker payload and
remain unchanged before native actions/export. Hashes are integrity checks;
the authenticated spool and operator-owned pinned policy provide authority.

The restricted gate already holds its current worker lock. Factory additionally
holds all launch locks, sibling worker locks and shared directory serialization
through existing Resume. Previous dispatchers require identity-matching terminal
receipts; unknown evidence or an active writer blocks replacement. Operator
registration must match native old generation/action/UID and actual canonical
storage. Missing or legacy-only directory locks are not automatically adopted.
Native final snapshot/live Worker checks and durable one-CREATE/START remain
inside existing RecoveryCapability/native recovery. No old project is edited.

Normal WGS/GATK Step2 status preserves the verified result. This source slice
does not enable GATK registry capability or install bindings. Activated Step3
replacement still fails closed pending selected-view cross-process continuation,
Step3-6/final release and full authenticated manual-flow acceptance. No automatic
recovery/TTL release enabled by this checkpoint.

## Task4 verified normal stage receipts (source only, 2026-09-24)

RecoveryCapability.export_result returns the same JSON fields in an internal
VerifiedMasterResult. Existing WGS/GATK status writers copy its separately stored
verified binding into normal running/terminal receipts. GATK's existing receipt
hash includes those fields. WGS Resume stores the result only in its in-process
worker payload, preserving it if monitoring later fails. No new API/schema.

The verified submission identity remains separate from both native identity and
the current observing platform execution. A successful historical Master is not
relabelled. Generic progress kwargs cannot inject cce_master_binding or
cce_master_submit_execution_id. Deserializing JSON never restores the internal
authority: each subsequent process must revalidate the selected native evidence.
This forwarding does not authorize directory writes, select a runtime path, or
replace the pending registered capability factory/cross-process stage closure.
Unactivated legacy status writes do not import or require the new result path.

## Task4 approved cloud identity and paired entry source (2026-09-24)

An operator-selected paired runtime may not enter legacy Resume locking without
an internal verified RecoveryCapability. The incomplete factory cannot silently
fall back to an old lock; operator activation remains gated until Task4 closure.

Operator storage mode `cloud-reader` uses native_root/canonical_root and exact
pvc_name/pvc_uid/pv_name/pv_uid. Resolve native run_dir inside the existing reader
generator with only that PVC mounted read-only. Remove other volumes, env and
automatic service-account-token mounting. Verify live volume binding and exact
reader Job/Pod identity before/after the probe. Fsync CREATE intent; reconcile
uncertain CREATE, never issue a second POST for the same intent. Clean up only
the bound UID/resourceVersion; cleanup replay cannot authorize a stage from old
probe results. No local NFS-to-SFS equivalence or new host mount.

The fixed writers-v2 policy additionally pins `runtime_guard` (path/sha256 for
the CLI source's sibling cce_writer_guard.py), and `operator_python` selects the
deployment-maintained executable for external stage commands. `writers.platform`
pins scripts/cce_paired_runtime.py. The original implementation required UID 0
and no group/world write throughout ancestry; that ownership assumption is
superseded by the non-root contract above, with source adaptation still pending.
No request field/environment flag can bypass bad policy.
Actual WGS/GATK Step1–6 builders and Resume loaders select the external runtime
only when this policy exists. GATK custom delivery also enters its writer and
keeps the original approved result root. Unactivated old behavior is unchanged.

Per-run bindings still require exact frozen registration; this checkpoint does
not install or automatically generate those bindings. Selected-view receipts,
recovery capability construction and final-release closure remain Task4 gates.

## Task4 protected writer entry (source only, 2026-09-24)

Native8ec5415 exports ProtectedWriter for Step1–Step6 and bundles its guard module.
At this historical checkpoint CLI main reads /etc/cce-pipeline/writers-v2.json;
the fixed-location/UID-0 requirement is superseded by the non-root contract above.
No browser or untrusted environment opt-out. When activated, require paired source pins, namespace,
physical shared-storage mapping and exact registered immutable bundle/config.
Unknown legacy identity fails closed. Shared journal flock serializes the stage;
CAS intents retain existing fsync semantics. Legacy failure cleanup inside a
protected stage cannot release the v2 lifecycle lock. Release after Step6 still
requires separately verified downstream/quiescence proof and is not yet wired.

No operator policy is installed by source development. Paired writer inventory
and access-path fencing are rollout conditions, not implied by a source hash.
Actual platform registration/gate construction and selected-view normal receipt
forwarding remain Task4 work. No API, DB, production or TTL activation changed.

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

2026-10-02 source correction: the registered initial Step2 CREATE wrapper must
read native `_master_create_intent(selected, contract)` and inherit its validated
deadline for the platform journal/handoff. Missing or mismatched intent rejects
before CREATE; a second clock-derived deadline is forbidden. Strict native
identity/deadline guards and unknown-outcome single-CREATE semantics stay intact.
This source fix is not a deployed release or recovery authorization for an old
created/unconfirmed Master that is absent. That state still needs separately
reviewed initial-submission reconciliation; no fabricated START/native FINAL,
historical deadline rewrite, intent deletion or manual lock release is permitted.
See [A468E9 incident and bounded design](reviews/2026-10-02-wgs-a468e9-step2-deadline.md).

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

### Bound workload observations (2026-09-23 baseline, superseded query mechanics)

`scripts/cce_recovery_workloads.py:probe_bound_workloads` originally issued
per-Worker exact-name Job and job-name-selected Pod queries. UE-03 replaces
those query mechanics with the shared five-query native inventory above.
Configured namespace must match the frozen binding.
The exact Master Job UID must be Failed/inactive, and the bound Master Pod UID
must appear among terminated, correctly owned Pods. Worker UIDs are exact;
missing Jobs still require checking their residual Pods. An expected absent
Worker with no known UID cannot adopt an unexpected Job/Pod.

All main/init/ephemeral container status inventories must match Pod specs and
show terminated exit codes. Active/deleting/foreign/ambiguous objects, missing
Pod lists, pagination, failed queries and changed identities reject. Only a
complete namespace list can now establish absence, with the separate exact
Master read checked for movement. Each command has at most 30 seconds and the
overall query budget at most 120 seconds. No Kubernetes writes, deletion, file
mutation or status changes occur.

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
# Task6 Master failure accounting / schema2 evidence (2026-09-25)

Source-only, default activation unchanged. In an existing handoff-v2 submission
phase, Master rule-status emits private `failure-summary.json` with schema
`cce.master-failure-summary.v1`, exact submit-context, closed/complete flags,
workflow-start count, cumulative submission/control/rule/other counts and separate
upstream scheduler/workflow shutdown-notice counts. No error message or clinical
payload is persisted. Missing start, duplicate start, logger write errors or an
unclosed process cannot prove zero failures. Worker logger ignores this audit.
Handoff-v2 preflight and analysis both use the logger; legacy preflight is unchanged.

Native FINAL includes each present summary under `phases.<phase>.failure_summary`;
identity mismatch invalidates the snapshot. Optional absence preserves manual
historical recovery but is never sufficient for automatic recovery. The restricted
selected-Master reader authenticates native FINAL and registered producer lineage,
then verifies every phase and full live Job/Pod inventory including retained
ancestors. Mixed/unknown failures, active work and incomplete reads remain blocked.

Existing `VerifiedMasterResult` captures optional `cce_recovery_evidence` in its
immutable receipt bytes. Only the same Step3 observation can forward it; generic
progress kwargs, a plain deserialized result or another stage cannot supply it.
Envelope schema2 contains the verified Master binding, failed phase, plugin
candidate and `cce.master-terminal.v1` classification seal. This is the trusted
producer of the earlier seal contract, not a frontend endpoint or recovery grant.
Business reservation checks the original platform producer row and the latest
monitor separately; native generation/request hash/phase execution ID are derived
from `binding.native`, never substituted with platform fields. A newer observer
may retain the older producer only through an identical verified native binding.
Existing policy/budget/control and subsequent dispatch checks remain mandatory.
No database table, public API, rule event schema, pipeline logic or live gate changes.

## Initial Master CREATE response-loss reconciliation (2026-09-27)

Scoped native correction, test candidate only until execution evidence is recorded.
Handoff-v2 Step2 persists `MASTER_CREATE_INTENT.json` before its initial CREATE.
Intent schema1 binds the current handoff binding (including frozen manifest/input
hashes), exact Job name and original600-second deadline. Atomic file and directory
fsync precede submission; new exported evidence retains0644/business parents0755.

If CREATE succeeded remotely but the client lost its response, re-entry with a
valid intent queries the existing Job and verifies the frozen manifest fields,
nonempty UID and absence of deletion before writing the genuine UID handoff.
Handoff continues with the intent's original deadline. It never adopts by name
alone, invents terminal success, sends a second CREATE for an existing intent,
or resets the deadline. An absent Job or changed intent/manifest fails closed.
Historical Job-without-intent-and-without-handoff is not automatically adopted.
Existing handoff replay and v1 remain supported; no Master/plugin protocol change,
Airflow retry-budget change or new public API is introduced. This initial-submit
reconciliation is distinct from failed-Master replacement and its FINAL evidence.

## Cloud-reader cleanup confirmation window (2026-09-27)

Native candidate `4488d10` extends only the cloud-reader Foreground cleanup wait
from 30 to 90 seconds. The prior window overlapped the Pod default 30-second
termination grace and left no controller/confirmation margin. Delayed Job absence
was observed in the isolated smoke; the earlier transport error is not attributed
to this timeout without further evidence. No global query timeout is changed.
UID/resourceVersion delete preconditions, exact manifest/token checks, bounded
polling and fail-closed DELETE_INTENT reconciliation remain unchanged. Cleanup
must be confirmed before a storage identity probe authorizes the actual stage.
This candidate does not imply shared installation or live smoke acceptance.
