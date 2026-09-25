# Current state

## 2026-09-25 Task6 manual monitor handoff checkpoint

Automatic polling no longer treats a failed query-only observer as terminal
compute or releases its action fence. Existing authenticated same-attempt Resume
can hand off an exact ended observer (scoped blocked/exhausted query marker,
confirmed dispatch, current action/DagRun/generation) to one new monitor action.
The prior action is canceled as superseded, NOT compute-failed; history remains.
Registration and retirement commit together under the existing run lock; old
DagRun authority is fenced. Reserved/uncertain dispatch, active reconnect,
foreign identity and user stops are not bypassed. Repeated requests reuse the
same action. GATK now preserves the original Step3 deadline on manual recovery.
No attempt/automatic-budget/deadline reset or unconditional Master replacement.

Existing detail Resume confirmation is reused as "恢复监控" for WGS/GATK query
attention, behind adapter capability/operator gates. No new page/public route.
BS10610 backend82 pass15.32s; frontend2 pass3.15s; TypeScript/Vite build passed.
Native fd43f88/plugin81132cf unchanged. No production, merge/push, images,
installed CLI/runtime updates or live workflows. Task6 remains OPEN: focused
PostgreSQL contention, full automatic lifecycle and one final whole-plan review.

## 2026-09-25 Task6 finite reconnect producer/consumer wiring

Supersedes the unwired prerequisite below. Paired WGS/GATK selected monitors now
attach one query-only owner to strict native GETs (including legacy JSON reads).
Existing current-generation status JSON persists reservations before retry,
retains measured progress, checks registration on every load/save and fsyncs the
GATK reservation. Missing/foreign/terminal status cannot silently reset a budget.
No whole-monitor, CREATE/START, transfer or biological-workflow retry was added.

Outer failed monitor status preserves the query marker. Real WGS/GATK ingestion
retains last confirmed analysis/stage state; the existing recovery view shows
checking or needs_attention, limit6, and explicitly unconfirmed execution after
exhaustion/control errors. Failure callbacks AND periodic DagRun reconciliation
share the current monitor fence. A healthy complete observation clears the
query overlay, not the attempt-level compute budget.

BS10610: affected query/backend regression113 pass8.29s; after final missing-status
guard, producer/consumer16 pass3.63s and actual selected-monitor new/legacy4
pass6.43s. Native source fd43f88, plugin81132cf unchanged. No local runtime tests,
production, push/merge/deploy, activation or artifact rebuild.
Task6/CR-04 remain OPEN pending the final automatic lifecycle/manual reconnect
interaction, focused PostgreSQL contention and whole-plan fresh review. Existing
manual controls and compute-action lifecycle were not expanded in this checkpoint.

## 2026-09-25 Task6 finite query-budget prerequisite

Added the internal query-only budget core: initial GET plus max6 retries at
30/60/120/240/300/300s, each request capped30s and by the original absolute
deadline. Existing-stage-JSON load/save callbacks retain identity, first error,
consumed retries, due time and last confirmed observation. Reservation is saved
before retry; interrupted in-flight calls consume their slot. Partial GET success
cannot reset the outage; only caller-confirmed complete observation can reset it.
Foreign/corrupt state and permission/auth/unknown errors stop without replay.

Paired native strict GET now accepts the exact directory-lock ConfigMap that the
platform already queries, supplies a shorter bounded timeout and separates local/
auth errors from temporary transport errors. Legacy readers are unchanged.
BS10610 native24 + platform17 targeted tests passed0.79s. No production, installed
CLI, images, workflow, service or policy activation; source-only checkpoint.

Important: the budget helper is NOT YET WIRED to the WGS/GATK monitor. Next is its
current-generation status persistence/producer integration and backend/UI outcome
distinction (including GATK/callback/periodic failure projection). Task6/CR-04
remain OPEN, followed by focused PG and final automatic lifecycle/review gates.

## 2026-09-25 Task6 recovery UI checkpoint

Existing Tracker and RunDetail now consume the same optional read-only recovery
projection: waiting/checking/recovering/needs_attention/stale/completed_degraded.
Accepted/queued dispatch is not proof of a started replacement Master. Exact
current monitor schema2 identity plus Job/Pod UID and recovery action are required.
Existing status history/budgets remain unchanged. Pending/uncertain display keeps
last measured progress, disables time-based estimates/ETA and never fills a failed
or complete bar without evidence. No new page, control action or scheduler.

The existing WGS/GATK status consumers retain an allowlisted current-monitor
observation in existing execution JSON; newer degraded evidence cannot be cleared
by an older healthy replay. This closes the real running-evidence ingestion gap,
not only a fixture-only UI path. No schema migration or producer changes.
BS10610 final backend26 GREEN3.03s, frontend13 GREEN6.17s and tsc/Vite build GREEN.
Source-only, original P0 branch; no production, merge/push, image build or activation.
Task6 remains OPEN: finite-reconnect producer-to-UI distinctions, focused PG
contention, final automatic lifecycle integration and whole-plan review. An absent
explicit reconnect signal remains state-unconfirmed, never an invented retry.

## 2026-09-25 Task6 Step4 caller checkpoint

The existing WGS/GATK Step4 runner and reschedule sensor now consume the original
operation probe/budget. First opted-in registration hashes marker1 and freezes
the stage deadline (WGS contract timeout / GATK existing48h). Existing authenticated
stage routes commit begin/poll intents before SSH, check current controls again
at send, and acknowledge only the exact exited local invocation. Timeout/nonzero
SSH hands off to reconciliation, not a task-wide retry or a new generation.
Fixed --publish-dispatch pins generation/hash; both launch gates enforce the
original deadline. Probe success still requires the normal successful stage
receipt before Step5. Default-off/legacy paths and DAG graph are unchanged.

BS10610 final scoped backend/runtime90 GREEN7.11s, real-Airflow20 GREEN3.04s.
No native/plugin change, artifact rebuild, service activation or production access.
Task6 remains OPEN: existing UI projections, focused PG contention and final
automatic integration/whole-plan review next; separately authorized live gates
remain closed. This is caller acceptance, not production readiness.

## 2026-09-25 Task6 Step4 operation/budget checkpoint

Step4 now has a fixed restricted original-operation probe and a separate durable
dispatch budget in the existing RunAction. Probe validates registered identity,
launch/worker locks and exact receipts/process records; missing or ambiguous
evidence does not imply a failed publish. Opted-in WGS Step4 refuses a second
spawn after an uncertain first spawn; GATK's existing intent fence is retained.
Budget keeps the same execution/generation/hash and original stage deadline,
at most two redispatches60/180, with fresh post-delay proof and no in-flight SSH.
It never consumes/resets the Master recovery budget or rewrites stage receipts.
BS10610 final64 targeted cases GREEN3.73s; no native/plugin or service changes.

This is the Step4 source contract, NOT an active automatic caller. Next wire the
existing stage registration and Airflow Step4 runner/sensor to these functions,
freeze the opt-in request marker/deadline there and commit intent before SSH.
No new DAG node/public route; real PG contention/full integration still pending.
Task6 OPEN; no main/production merge, push, deployment or artifact rebuild.

## 2026-09-25 Task6 exact CREATE classification checkpoint

Plugin source now classifies exact Worker CREATE storage RPC Unavailable/peer-reset
HTTP500 and mutation.gatekeeper.sh context-deadline failures. Original Job is
reconciled first; RPC UNKNOWN cannot replay. Backend and inventory independently
require fixed typed CREATE fields, ABSENT, exhausted budget and existing complete
fatal-cause/terminal evidence. No generic500 or policy-denial automatic permission.
BS10610 focused30 source/consumer +2 actual producer/FINAL/reservation cases passed.
Task5 artifacts, native d7bd741, services and default-off policy unchanged.
Source commits only, no production/push/build/activation. Task6 remains OPEN:
next Step4 same-operation reconciliation, then existing UI/PG/final integration
and separately authorized operational gates. See latest HANDOFF for provenance.

## 2026-09-25 Task6 bounded Worker wait checkpoint

Known same-owner active Workers now produce a waiting candidate, not replacement
authority. The existing Airflow recovery action persists wait start/deadline
(max600s capped by original compute deadline), one slot and current-monitor nonce.
Existing sensors call a fixed restricted read-only probe and return its evidence
to the existing internal POST. Only unchanged FINAL/producer/cause plus fresh
zero-active evidence clears waiting; native replacement independently rechecks.
Stop, expiry or changed evidence blocks dispatch. No Worker kill or failed receipt
rewrite; missing terminal evidence after reclamation remains blocked.

BS10610 final focused17 backend/producer (5.52s),2 restricted entry (5.27s),4 real
Airflow sensor cases (3.03s) passed. Boundary preflight unchanged; no service changes.
Platform isolated branch only; native d7bd741/plugin c0b266b and Task5 artifacts
unchanged. No main/production merge, push, build, install, activation or real rerun.
Task6 still OPEN: remaining exact failure classes, Step4 reconciliation, existing
UI projections, PG/final integration and separately authorized live cloud gates.

## 2026-09-25 Task6 controller deadline checkpoint

Original registered Step3 deadline now reaches native replacement and both
WGS/GATK monitor loops. Native journal identity retains the absolute deadline;
DELETE/CREATE/handoff check remaining time and handoff is capped by it. Monitor
restart/replay cannot extend the deadline. Invalid present values fail closed;
absent values retain historical/default-off behavior and Task5 native ABI.
Expiry preserves all evidence and Jobs for reconciliation; no workload kill or
Job activeDeadlineSeconds change, biological change or frozen bundle rewrite.

BS10610 offline focused22 passed16.25s, compute-deadline-final.log. Existing
control/current/RO mounts and disabled scanner/dispatcher preflight passed.
Only original platform/native isolated branches changed (natived7bd741); pluginc0b266b and
Task5 artifacts preserved. No push/main merge/install/build/production/rerun.
Task6 remains OPEN. Next: Airflow-owned persistent bounded Worker wait, then
remaining exact failure classes, Step4 reconciliation, existing UI, PG/final
integration and separate authorized live cloud gates.

## 2026-09-25 Task6 policy and Airflow polling checkpoint

New WGS/GATK CCE creation now freezes its own default-off policy/zero budget.
First Step3 registration fixes the original deadline; duplicate registration
preserves request hash/generation. Historical or legacy manual next-attempt
flows gain no new automatic quota and remain manually executable.
Existing authenticated stage POST and existing Step3 sensors call the due owner;
waiting reschedules, confirmed delegation skips the old chain before observer
deactivation/downstream. Lost responses do not create another action/POST.
Exact current compute terminal evidence releases the active compute fence while
retaining downstream authorization. Two failures consume shared slots60/180s;
older completed compute history no longer blocks current cleanup.

BS10610 offline targeted backend19 GREEN4.70s and real-Airflow5 GREEN3.00s.
No full-suite repetition, local runtime test, production, deployment, main merge,
push or real rerun. Default-off settings are source only and must NOT be enabled.
Task6 remains open: native deadline enforcement, bounded Worker wait, remaining
exact failure classes, Step4 reconciliation, UI, PG and final integration.
Task5 artifacts and native/plugin source pins remain unchanged this checkpoint.

## 2026-09-25 Task6 internal due-dispatch checkpoint

Prerequisite source committed: platform abdba43, native ffe51d4, plugin c0b266b.
Existing reserved automatic actions now have an internal due-dispatch service:
wait without writing requests, revalidate original schema2 proof and budget,
persist the same action/DagRun before writes, then use existing adapter stage
registration and shared Resume POST-intent/GET-only reconciliation. No second
manual action, new attempt, prepare/upload or independent retry engine.
After a prepared-intent crash the original failed receipt is revalidated again.
Late reconciliation cannot overwrite a user stop; missing policy/evidence fails
closed. The frozen original deadline is carried into recovery stage requests.

BS10610 targeted23 GREEN4.68s (14 new cases plus9 affected manual cases).
This is internal source acceptance only: no Airflow automatic caller, new-attempt
policy freeze/enablement or runtime deadline consumption is wired yet. Bounded
Worker wait, remaining exact error classes, Step4 reconciliation, UI, PG and
whole Task6 integration still open. No deployment/main merge/push/real rerun.

## 2026-09-25 Task6 prerequisite accepted — bound failure accounting

User approved “补齐，然后继续”. Existing Master rule-status logger now counts
typed submission/control failures, rule/group failures and unstructured errors;
private phase summary becomes complete only on normal logger close after exactly
one workflow start. Real Snakemake9.24 shutdown notices are separately accounted
for by exact source/function/message, never by text alone. Worker mode is unchanged.
Native handoff-v2 preflight also enables this logger; FINAL binds the optional
summary without inventing completeness for old/missing audits.

The restricted selected-Master monitor verifies native FINAL, all phase audits,
retained Worker lineage and fresh complete Job/Pod inventory before attaching
`cce_recovery_evidence` to the existing immutable verified receipt. Backend
reservation consumes schema2 with distinct platform and native identities,
including a later observer retaining an older Step3 producer. Missing/mixed/
active/unclassified evidence remains ineligible; no automatic dispatch occurs.

BS10610 offline final focused28 passed35.59s. This closes the approved producer/
schema2 prerequisite only; Task6 dispatch, policy freeze, Step4 reconciliation,
UI/PG/final integration and separately authorized operational gates remain open.
No installed CLI/image/policy, production, main merge, push or real rerun changes.
Task5 artifacts retain their original bytes and do not contain this new source.

## 2026-09-24 Task6 preflight — automatic evidence producer gap

Task6 started with source/interface inspection at platform83528cf,
native770934c and pluginb6d1fb8. No implementation, runtime test or activation
in this checkpoint. Tasks1–5 acceptance is unchanged.

The automatic reservation bridge still expects the earlier flat Master binding
and `master-terminal.json` contract. Task4 exports schema2 with separate platform
and native identities; native FINAL proves process exit and submission inventory,
not the complete fatal-cause classification required for automatic recovery.
Do not relabel native IDs as platform IDs or synthesize zero rule/other failures.
Proposed next scope confirmation: complete the existing Master wrapper/logger
failure summary and adapt the existing reader/reservation bridge, then dispatch.
See latest HANDOFF for exact producers/consumers and remaining Task6 gates.

## 2026-09-24 Task5 source and offline artifacts accepted

Task5 only: Worker/Master/evidence-reader TTL100. Generators6 RED then6 GREEN;
affected missing-object/lost-response/deadline15 GREEN; image sibling1 RED then
1 GREEN. All BS10610 offline. Distinct native/plugin wheels and WGS/GATK Master
test images built; actual-wheel acceptance13 passed and both image smokes passed.
Pins: native7232f57, pluginfdf1520, platform consumer074dc55. Full provenance and
scope review: docs/releases/2026-09-24-p02-task5-offline-artifacts.md.
Task6 automatic recovery is next; live TTL/capacity/AOM/alerts remain separate gates.
No Task6, production, installed CLI/policy, old-bundle or service changes.

## 2026-09-24 Task4 manual source acceptance complete

Historical Task4 closure: Tasks1–4 source acceptance complete; the newer Task5
entry above supersedes its then-unstarted TTL/artifact status. Task6 remains open. Earlier
dated checkpoints below describe their then-open slices, not current blockers.

Existing authenticated WGS/GATK manual Resume now reaches the original restricted
adapter/native recovery, fresh-process selected-Master monitoring and normal
Step4–6 receipts. Same attempt/config/workdir; no prepare/upload redo or forceall.
Active Master reattaches, native success continues downstream, unknown evidence
blocks. Initial CREATE/handoff interruption and post-bind crash reconcile the
same UID/action/deadline without a second CREATE. WGS reattach revalidates receipt
authority before archival instead of copying raw binding fields.

Final Step6 release requires materialization, native success, registered generation
lineage, complete live inventories and inactive sibling dispatchers. Retained old
terminal Workers are verified; unknown/active Workers still prevent release.
Native bd41f87 projects generation-local final manifest while preserving shared
history. Plugin5b5d7ee unchanged. Original bundles/output roots remain unchanged.

Latest-requirements cross-check and review: three Important findings reproduced
RED and fixed; final BS10610 selected41 passed/1 skipped76.91s, authenticated
manual WGS/GATK2 passed41.32s. The skip is the WGS-only reattach-worker case for
GATK, not a missing GATK recovery test. See HANDOFF and the Task4 plan checklist.
No local runtime/full-suite tests, images/CLI/policy installation, automatic
enablement, main/production merge/push, production DB/data or real rerun changes.

## 2026-09-24 Task4 selected-Master Step3 checkpoint

BS10610 validation resumed. A fresh WGS/GATK monitor reconstructs the selected
Master from registered Step2 request/receipt, native journal/handoff, frozen
inputs and the exact directory owner. Actual gate polling and rule-log bridge
now use that verified view, preserving the original bundle and producer identity.
Old run-id-only completion markers cannot report a new Master successful.
Reclaimed Job success/failure requires matching native terminal evidence.

Focused selected-monitor tests18 GREEN30.04s; affected Step2 replay2, worker
disconnect1 and unactivated entry2 also GREEN. Native903e1af; no production,
deployment, policy installation, new Job, local tests or full-suite repetition.
Task4 remains OPEN: direct Step3 replacement/initial-submit paths, selected
Step4-6 reconstruction/execution, final protected release and authenticated
service/DAG/native manual flow. Tasks5/6 remain unstarted. This checkpoint does
not authorize activation or represent whole Task4 acceptance.

## 2026-09-24 Task4 registered Step2 recovery checkpoint

BS10610 SSH restored; isolated offline validation resumed. Existing paired
runtime now constructs RecoveryCapability from the registered stage request,
operator-approved frozen binding, physical directory identity and exact native
old owner. Holds shared directory serialization and other dispatcher/launch
locks throughout existing Resume. Missing/foreign locks, changed request and
uncertain dispatcher evidence refuse replacement. WGS/GATK actual Step2 entries
retain verified native/platform identity in normal status receipts; replay
creates/starts only once and preserves frozen inputs.

BS10610: actual entry2 RED; corrected real GATK request shape1 RED; final14
GREEN13.78s and affected legacy/receipt3 GREEN2.17s. No broad suite, local tests,
activation, live cloud workload, production service or DB change.
Task4 remains OPEN: selected-view reconstruction across processes, native
Step3-6 execution, final protected release and authenticated service/DAG/native
manual flow. Activated Step3 replacement fails closed until that continuation
is connected. Operator bindings are not automatically generated/installed.
Tasks5/6 remain unstarted.

## 2026-09-24 Task4 verified normal-receipt checkpoint

WGS/GATK status writers now carry native-verified Master binding metadata from
an internal result, including running/success/failed receipts; GATK receipt hash
covers the metadata. WGS Resume worker retains it when monitoring disconnects.
JSON round trips and generic progress kwargs cannot supply verified authority.
Master submit identity stays distinct from the current observing execution.
BS10610 offline: two receipt cases RED then GREEN; seven affected checks GREEN
7.62s; final observer-identity refinement two GREEN3.51s. No full suite or live
runtime tests. No production, deployment, activation, DB or frozen bundle change.

Task4 remains OPEN: trusted per-run factory, actual GATK Resume routing,
cross-process selected-view reconstruction/Step3-6 execution, final lock release
and one authenticated service/DAG/native manual flow. The status-writer slice
is not cross-process closure. Tasks5/6 remain unstarted.

## 2026-09-24 Task4 cloud identity and paired entry checkpoints

Source commits: native7026528, platformc3cf3c2. Follow-up closes a fallback edge:
activated Resume without verified RecoveryCapability rejects before entering the
legacy lock path. Two adapter cases RED; final12 new +3 affected GREEN0.99s.

User approved the existing cloud read-only reader, not a new SFS host mount.
Native source now validates PVC/PV/Job/Pod identities and resolves directory
aliases in that reader, with durable one-create/reconciled cleanup and no foreign
UID deletion. Frozen binding validation precedes the probe. Cloud10 plus affected
protected-entry13 passed on BS10610 offline synthetic (23 GREEN2.23s).

Platform WGS/GATK stage command and Resume runtime selection now honor fixed
operator-owned paired pins, including the sibling guard; invalid activation
never falls back to old frozen code. GATK custom result-root materialization
enters the same writer without changing its approved output location. New10 and
three existing GATK result-root checks passed (13 GREEN0.82s).

These are source checkpoints, not Task4 acceptance or deployment. Actual trusted
per-run registration/recovery capability, selected-view normal receipts, final
lock release and full service/DAG/native manual closure remain OPEN. Tasks5/6
remain unstarted. No policy, cloud Job, CLI/image or production service changed.

## 2026-09-24 Task4 CLI protected-entry checkpoint (native8ec5415)

Follow-up binds actual stage arguments to the original bundle/contract/config;
new13 checks passed. Historical mapping question (resolved above): reuse the
existing cloud read-only reader (recommended) vs an already mounted SFS path.
No verified local SFS mapping exists in this task; do not substitute local NFS or
create new mounts. The user subsequently approved the cloud reader.

User approved CLI Step1–Step6 compatibility scope. Isolated native source now
guards every stage, preserves v2 locks on early failure, checks operator-owned
paired source pins/physical storage mapping/exact frozen binding at CLI entry,
and serializes shared journal writes. No old bundle/config/policy was installed.
BS10610 new12 GREEN, affected lock/downstream35 GREEN, legacy Step4/5 three GREEN.
Task4 remains OPEN: actual platform registration/gates, selected-view receipts,
final downstream release and complete WGS/GATK manual flow are still pending.
Tasks5/6 unstarted; no production/CLI/image/TTL/automatic activation.

## 2026-09-24 Task4 downstream/binding checkpoints; CLI entry scope confirmation

Native isolated commit08c6cda accepts selected-Master evidence for Step4/5/log
export while keeping delivery/log/output roots under the original bundle. Missing
TTL-reclaimed Job needs validated native success; active/foreign Job blocks.
WGS/GATK Resume now export v2 Master bindings from validated handoff bytes, with
platform identity separate from native generation/hash and no legacy relabelling.
BS10610 offline downstream10 and adapter binding6 affected checks passed.

Task4 is NOT complete: restricted entry selected-view persistence/forwarding,
canonical storage mapping and paired all-writer activation remain open. The CLI
scope was subsequently approved and the source entry checkpoint above supersedes
the missing-entry observation. Actual paired activation remains unproven.
No production changes; Task5/6 have not been started.

## 2026-09-24 Task4 GATK dispatcher fencing checkpoint

GATK Step1–6 now serialize launch/worker ownership, persist a pre-spawn intent
and PID/boot/start identity, and reject unknown or superseded execution writers.
Terminal receipts require full execution identity; ambiguous/dead legacy dispatchers
are not automatically replaced. Prepare and Step7 retain their existing mechanisms.
BS10610 offline synthetic: five behavioral RED cases, then15 affected checks GREEN,
including real fork/lock handoff. No live service or gate changes. Task4 remains
OPEN for trusted storage/all-writer activation, binding and selected-view downstream.

## 2026-09-24 Task4 initial Master binding source checkpoint

User approved initial Master platform identity binding. Native isolated source now
provides an independent initial submission view and internal Step2 opt-in; frozen
inputs/default CLI are unchanged. Platform and native generation/request hashes
remain separate and bound through Master confirmation and terminal evidence.
WGS/GATK Resume forward a fresh platform identity into existing replacement journals.
BS10610 affected native41 passed; actual adapter/producer composition2 passed.
No deployment, image/CLI install or automatic activation. Task4 still requires
trusted binding writer/storage mapping, paired writers/dispatcher proof and normal
downstream selected-view acceptance; Tasks5/6 remain gated by that closure.

## 2026-09-24 Task4 GATK service/DAG checkpoint; native activation still blocked

GATK now has its own frozen-request Resume registration using
PipelineStageExecution, original attempt/profile/bundle, preserved request history,
and the existing RunAction journal. WGS/GATK share only durable Airflow dispatch
and action authorization. The existing operator/CSRF endpoint selects the adapter;
GATK `resume` capability is NOT enabled in the shipped registry. Its DAG skips
prepare/upload/completed stages and carries actual DagRun/action identity.
Registration, slot acquisition and finalization reject superseded/control states.

BS10610 isolated checks:39 affected backend cases passed; the added HTTP routing
and finalize-control cases passed separately; one real-Airflow GATK DAG case
passed. No full suite or local runtime tests; no service/production/CLI/image change.

Task4 is not complete. A concrete producer gap needs confirmation: replacement
Master gets recovery_context, but initial Master submission does not yet bind
platform execution identity. Native handoff request_hash and platform stage
request_hash are DIFFERENT digests and must not be treated as interchangeable.
User asked to authorize this necessary initial-submission source addition; no
such producer edit performed. Trusted binding writer/all-writer proof/selected
view downstream remain open; Task5 TTL and Task6 auto dispatch remain gated.

## 2026-09-24 Task4 checkpoint: WGS authenticated dispatch fence accepted

Task4 STARTED, not complete. Existing WGS Resume journals POST intent before
Airflow, reconciles exact DagRun ID/conf by GET after uncertain POST, and keeps
late replies from clearing newer controls/current-DAG failure. Recovery DAG
registrations now carry actual DagRun ID; scope/control checks cover stages,
slot acquire (recheck after helper commit) and finalize with reused Step6.
No new endpoint/table or recovery engine. BS10610 isolated synthetic acceptance:
31 backend cases covered across affected groups;3 real-Airflow DAG tests passed.
One scoped review,3 Important fixed and rechecked; no open Important/Critical.
No full suite, local runtime tests, production/service/CLI/image changes or push.

Platform base f93ba00; producer32aa7fb and Worker5b5d7ee unchanged. Remaining
Task4: GATK own-service/DAG routing; trusted native binding/canonical lock mapping;
paired all-writer/dispatcher exclusion; selected-view propagation into monitoring
and downstream receipts. Do not advance Task5 TTL or automatic recovery yet.
See HANDOFF for commands, source boundaries and isolated evidence path.

## 2026-09-24 Task3 source implementation accepted

Verified dependency commits: platform321b0a1, producerfa1ac44, Worker5b5d7ee.
Existing WGS/GATK Resume now consumes verified final inventory, trusted lock
capability, native generation view and original adapter journals. BS10610:
capability6 GREEN; initial composition10 RED; expanded composition29 GREEN;
5 affected legacy checks GREEN. Scoped review: no open Important/Critical.
SSH recovered; latest source synced and validated, see HANDOFF for evidence.
Task3 source complete; Task4 authenticated service/DAG/all-writer construction
and selected-view propagation remain next. No automatic/TTL activation, images,
CLI install, production changes, real reruns, main/production merge or push.

## 2026-09-24 Task3 approved snapshot/view dependencies accepted

User approved isolated native final Worker snapshot + independent next-generation
view. Implemented without changing original bundle/config/history. Master seals
completed plugin phase journals/checkpoints/Worker terminals/manifest; this is
NOT an all-writer recovery seal. Current-bound native reader and complete live
run-label/exact Job/Pod reconciliation reject incomplete, unknown or contradictory
evidence. BS10610 synthetic: view6 + final18 + live10 new cases passed;5 affected
checks. Prior query/confirmation/native success checkpoint27 + replay/review4 also
passed. See HANDOFF for individual logs, not a full-suite claim.
Task3 still OPEN: trusted lock capability and existing WGS/GATK Resume side-effect
journal wiring/final matrix. Task4 authenticated all-writer closure stays separate.
No local runtime tests, installs, images, services, production or real reruns.

## 2026-09-23 Task3 confirmation/native success consumers; producer gap identified

Compatible Resume queries use a bounded, classified producer reader; errors are
never absence and incomplete pages block. WGS v2 handoff consumes actual Task1
START_CONFIRMED (original deadline, no repeated START); GATK can reconcile its
same active v2 Master. Native success requires matching handoff, confirmation,
RUN_COMPLETE, three zero stage exit codes and workflow completion, not just a
Job Complete condition. Contradictory/active terminals block continuation.

Task3 is NOT complete. Failed v2 Master replacement blocks BEFORE mutation:
Task1 cannot accept another UID in its frozen generation. Final submission
inventory is not sealed by the Master (evidence_complete=false; submit-context
injection absent at that historical checkpoint). Approval and implementation
above supersede the then-pending scope question for final inventory and
explicit next-generation recovery view in isolated producer source. Do not
rewrite frozen bundles or treat process-only evidence as a full seal. Complete
live inventories/canonical lock callbacks remain open, then Task4.

BS10610 synthetic: RED15 -> GREEN15 query/confirmation; RED9 -> GREEN9 native
success; RED3 -> GREEN3 terminal ambiguity. No local tests, production actions,
install, artifact build, TTL or automatic activation. HANDOFF records provenance.

## 2026-09-23 P0-2 Task3 first guard checkpoint (Task3 still in progress)

Existing WGS Resume no longer submits again after unknown CREATE followed by404,
or after an acknowledged replacement disappears. Recheck exact Master UID/RV
before DELETE; journal writes are exclusive/owner-only, file+directory fsynced,
and preserve existing fields. WGS/GATK reject incomplete Pod inventories;
GATK archived Worker NOT_FOUND without terminal proof now blocks before claim.
BS10610 synthetic RED6 failed/1 passed, GREEN7 new +13 directly affected legacy
passed. Review added delayed-visible failed replacement RED1; fixed guard and
that case + affected normal replacement GREEN2. Eight new cases accepted total.
No full suite, local tests, image/install, service or production changes.

This is a bounded safety checkpoint, NOT Task3/Resume consumer completion.
Next: compatible START_CONFIRMED/native terminal consumption, complete admitted
Worker/live inventories and trusted directory-lock callbacks through existing
Resume; then Task4 authenticated adapter/all-writer closure. No TTL/automatic
enablement. Old frozen bundles remain unchanged; unknown outcomes stay blocked.
Step7 plus manual local deletion does not yet permit platform same-batch
recreation: batch/snapshot uniqueness and old record reuse remain a separate
unimplemented boundary, not fixed by directory lock primitives alone.

## 2026-09-23 P0-2 Task2 source primitives accepted; no production rerun

User clarified the five historical reruns are a lock-compatibility discussion,
not an operational request. Continue the approved P0 plan, no BS96 actions.
Plugin5b5d7ee (0.6.4+bs8.dev1 successor source) persists exact admitted Worker
terminal evidence before callbacks; known terminals avoid status queries,
unknown404 stays unknown. Quota claims remain conservatively managed.
cce-pipeline7926496 adds opt-in directory ownership, journal-before-CAS handoff,
conditional release, stale-generation protection and explicit legacy guard.
Existing two-argument/frozen callers unchanged; no current consumer opts in.
BS10610:15 Worker +17 lock cases;5 +3 affected legacy cases passed. Focused
review issues fixed and rechecked. No full suite, image/wheel or installation.

Five legacy runs will retain analysis_id/attempt/config/workdir/history. The
upgraded recovery entry must verify exact legacy mapping/quiescence, preserve
the old lock snapshot, then conditionally reserve/bind the new generation.
Unknown mappings stop for verification, not automatic lock deletion. Canonical
storage resolution and paired CLI/platform/stage writers are mandatory before
activation; frozen bundles must not be rewritten. These trusted consumers and
end-to-end manual recovery are Tasks3/4, not complete yet. Next: Task3.
All changes on isolated development branches only; no main/production merge,
push, deployment, real batch action, TTL activation or automatic enablement.

## 2026-09-23 P0-2 Task1 source acceptance complete

User requested Task1 only. cce-pipeline source c33740d on independent branch
`jiucheng/runtime/p02-master-handoff-20260923`, verified base83e7adb.
Existing handoff now requires identity-bound persistent Master confirmation;
lost START response/restart reconciles without another START or deadline reset.
Trusted native setup/execution terminal records retain original success checks;
same-Pod atomic claim prevents duplicate entrypoint/config/terminal writes.
BS10610 final24 targeted +18 affected legacy tests passed, synthetic only.
Fresh server10610/current/mount/gates/permissions verified; initial connection
blocker is resolved, though intermittent jump SSH failures were observed.
No product deployment, image build/install, BS96/main/production or frozen-project
changes. Process terminal evidence is not a Worker-finality/recovery seal.
Docs and field mapping updated. Task1 done at source level; Tasks2–6 remain open.
Next planned Task2: Worker terminal persistence and logical-run lock ownership.
TTL remains unchanged; automatic recovery stays disabled.

## 2026-09-23 P0-2 implementation plan integrated; execution blocked

User requested planning and implementation of the latest P0 revision. Integrated
a1af96a/729564c/781877e into the existing CR01 design, retaining prior quota/RPC
coverage and accepted work. Plan: docs/superpowers/plans/2026-09-23-p0-2-master-handoff-ttl-implementation.md.
Order: Master handoff/terminal producer; Worker terminal and P0-2E logical-run
lock handoff; TTL-safe runtime Resume; authenticated manual adapters; compatible
TTL generators/artifact checks; remaining automatic P0 and operational gates.
No product code changed this turn. BS10610 preflight failed twice at BS jump
172.17.61.18 SSH handshake (exit1); host/mounts/permissions not freshly verified.
Producer source ownership also requires verification: reported83e7adb prototype
has uncommitted work, not a verified authoritative baseline. No local tests,
deployment, BS96/main/production writes or policy activation. Tasks1–6 remain
open; resume with fresh test preflight and producer provenance, then Task1 RED.

## 2026-09-23 current-attempt receipt projection refreshed (source only)

WGS runtime stage-status ingestion and GATK stage-status sync now lock and
refresh AnalysisRun before validating/projecting a receipt. GATK refuses old
attempts; both refresh cached execution state so a late failure cannot replace
a durable terminal success. Existing generation rejection remains intact.
BS10610 isolated checks:8 focused cases after4 expected failures, plus5 affected
legacy cases passed. No PostgreSQL concurrency or end-to-end recovery claimed.
Committed on the independent CR01 branch only; no services/BS96/main changes.
Trusted terminal/binding writers, dispatch/adapters, other observer evidence
paths and Step4 reconciliation remain; automatic recovery stays disabled.

## 2026-09-23 bs7 inventory and actual producer acceptance completed

BS10610 connectivity restored; fresh host/mount/gates match the prior test
fingerprint. Control inventory now binds exact existing CREATED/ADOPTED Worker
UIDs and complete manifest; null control UID never means absent, mixed submit
failure or incomplete inventory rejects.34 focused tests passed after RED.
bs7 actual-wheel-generated four WGS/GATK GET/LIST fixtures passed4 platform
checks; no missing-fixture skips. Plugin25297f9 built offline through owner's
guarded script,52 actual-wheel checks passed; bs6 remains0b19bb6 unchanged.
Source/artifact compatibility only, not terminal/automatic recovery acceptance.
Continue existing trusted runtime/query, dispatcher/adapter/observer/Step4 work.
No services, production/main changes or automatic recovery enablement.

### Previous paused checkpoint (resolved above)

First current-disconnection slice committed26d62dd. Follow-on control inventory
test draft added (10cases), unrun: SCP and remote RED command both stopped at
BS jump172.17.61.18 SSH handshake before remote execution. No inventory code
changed or local/production testing substituted. Next: fresh BS10610 preflight,
test RED, inventory adaptation and actual bs7 fixture acceptance. Owner-reported
108 plugin source tests are not platform artifact acceptance; artifact pending.

## 2026-09-23 requested disconnection coverage additions (source only)

GATK idempotent input/result transfer-slot sensors now use the existing bounded
backend transient retry rules. Same identity reacquisition cannot steal a slot;
transfer/SSH/CREATE/publish/release tasks are not newly retried. BS10610 actual
DAG7 checks passed after RED; two backend lease identity checks passed.

Agreed separate HEAVY_SLOT_API_UNAVAILABLE control candidate supports exact
GET Lease / Worker Pod LIST errno111 failures. Internal consumer and controlled
reader implemented and synthetic tests passed; generic500/writes/mixed files/
active Workers/incomplete terminal refuse. Plugin owner is implementing a new
bs7 artifact; actual-source fixture and inventory integration remain pending.
D RPC500 source classification and WES generic kubectl query failure remain open,
not falsely classified from summary text. No production/main/service changes.
P0 is still incomplete and automatic recovery remains disabled. Continue existing
runtime contract, dispatcher/adapter/observer/Step4 and remote acceptance work.

## 2026-09-23 old DagRun cleanup fence completed (source only)

CR-03 WGS/GATK transfer-release endpoints and WGS observer deactivation now
check refreshed current attempt/DagRun/recovery identity under the run row lock.
Old or unbound recovery cleanup cannot release even a terminal transfer or drain
the replacement observer. Current cleanup retains existing terminal-only lease
release. Partial WGS release re-locks before retained-slot state projection.
DAG cleanup callers send actual run_id; no graph/runtime/Step7 changes.
BS10610:24 new backend cases,3 affected legacy endpoint cases and7 actual DAG
tests passed (targeted runs only). Source and progress docs on the independent
CR01 branch; no push/merge/deployment, production or shared-service mutation.
Remaining: dispatcher/adapter wiring, observer generation projection, trusted
terminal closure, Step4 reconciliation and PostgreSQL/end-to-end acceptance.
Automatic recovery remains disabled; P0 is not complete.

## 2026-09-23 old DagRun failure callback fence completed

WGS/GATK failure projection now refreshes the locked run and refuses stale
DagRun identity or an unresolved automatic-recovery reservation. GATK callback
passes actual dag_run.run_id through its existing internal API. Exact current
queued/uncertain replacement may report failure; terminal behavior is retained.
WGS failure deduplication includes DagRun identity so a new failure cannot reuse
the old end time. No history rewritten, no new table, dispatch or policy enable.
BS10610:22 new backend cases,5 affected legacy cases and1 actual Airflow DAG
callback check passed; two observed RED failures. Only affected cases rerun for
the small dedup fix. No shared services/main/production change or deployment.
Remaining CR-03: dispatch/adapter/lease and observer fences, trusted terminal
closure, PostgreSQL concurrency and end-to-end acceptance; P0 is not complete.

## 2026-09-23 existing WGS manual-retry fence completed

Legacy Resume/Rerun failed now take/refresh the AnalysisRun row lock and reject
pending current-attempt automatic recovery before release lookup, attempt/state
mutation or dispatch. Existing resume_stage shares the same check. Missing or
ill-typed action attempt identity blocks; finished automatic history is retained
and permits manual retry. Cancel keeps priority and its existing CCE restrictions.
BS10610 RED reproduced bypass; GREEN22 focused checks passed1.23s (14 new plus
8 affected resume-stage checks). No shared service, production, policy or DB change.
This closes these WGS service entry points only; dispatch/callback/adapter/GATK
integration and PostgreSQL concurrency acceptance remain pending.

## 2026-09-23 bs6 consumer contract acceptance passed

SSH restored. Actual hash-pinned bs6 wheel generated WGS/GATK admission and guard
fixtures; consumer and inventory checks passed14/14 on BS10610 (0.32s,62 unrelated
cases deselected). Guard category alone also rejects with otherwise qualifying
synthetic values. Candidate without terminal rejects for all four scopes.
No production code, allowlist, API/DB, service or automatic-policy change.

This closes bs6 candidate-format compatibility only. Positive terminal objects
in tests are explicitly synthetic, not runtime evidence; complete Master/Worker
terminal support and recovery dispatch/adapter/callback integration remain open.
Next: remaining existing control/dispatch/callback fences and adapter integration,
without restoring the extra audit track or enabling recovery on incomplete proof.
Fresh test backend36ff21f87356 mounts20260923-step7-ae416fa/backend/backend;
test gates scan/dispatch=false, readonly nonterminal-run query returned[].

## 2026-09-23 bs6 consumer acceptance started; SSH preflight blocked

User requested next step. Selected actual bs6 consumer contract acceptance only,
not deployment. One BS10610 preflight failed during ProxyJump BS handshake:
172.17.61.18:22 connection reset, before reaching server10610. No fresh remote
mount/active-run fingerprint, remote writes or tests. Existing results do not
establish current connectivity. Producer owner asked for actual wheel-generated
WGS/GATK admission and quota-guard fixtures; receipt is pending.
Added an unrun guard-category negative case to the existing synthetic consumer
test; no production code/allowlist changed. Resume this exact acceptance after
test-host access is restored; do not substitute local or production execution.

## 2026-09-23 bs6 candidate handoff received (not deployed)

Plugin owner reports clean commit0b19bb605cdff619a7f09b34a6fe774e4b43d357,
0.6.4+bs6 combining biosan5 quota behavior and P0. Source and wheel each passed
86 checks according to owner evidence, not rerun here. New
WORKER_SUBMIT_GUARD_FAILED is UNKNOWN/retryable=false; current consumer's two
category allowlist already rejects it. No policy change needed. No new trusted
terminal producer was delivered; end-to-end automatic recovery remains unready.
Coordinator reports test baseline ab8695d after Step7; fresh mounts/active-run
preflight is required before the next remote action, not the old fingerprint.

## 2026-09-23 P0 scope correction: continue the existing plan

User clarified that the Master failure example is a completeness check, not a
new incident/development track. Runtime owner confirmed its current scope is
bs6 integration on biosan5 with full HeavySlotQuota behavior preserved, without
the additional Master audit producer. Earlier audit-next-step notes below are
superseded. No source hooks/launcher/receipt extension will be assumed available.
The unverified terminal-audit consumer draft is preserved in Git stash
3c617cbd86a4b3d27309689ecdfd7fc820f73c57, excluded from the implementation branch.

Continue CR-01 through CR-05 against the delivered, version-bound producer
contract: consumer/control fences, adapters and DAG continuation. Candidate
evidence alone still cannot authorize replacement; incomplete Master/Worker
proof remains manual. No automatic enablement, production change or extra suite.
Actual bs6 delivery and end-to-end recovery acceptance remain outstanding.

## 2026-09-23 P0 Master failure observations

Extended the existing UID probe to retain the Master Job failure reason and all
observed Master Pod main/init/ephemeral termination reasons/codes/signals and
restart/last-termination evidence. BackoffLimitExceeded is recorded as a terminal
symptom, not an automatic-recovery category; no messages/private stderr returned.
BS10610:34 affected checks passed0.06s. No production query/change/deployment.
20260921D is user-reported context only; its actual root cause and persisted
production record were not examined here. The full trusted Master error audit,
final footer and recovery integration remain pending; no seal/permission emitted.

## 2026-09-23 P0 submission inventory joined to workload probe

Added `scripts/cce_recovery_inventory.py`: verifies bound context, producer
checkpoint/hash chain, every submit intent/result, cumulative failure candidate,
and admitted Worker manifest. The composed probe derives all Worker identities
from that snapshot, not a caller-supplied subset. BS10610:26 focused checks passed
in0.08s, including actual WGS/GATK producer fixtures and the probe connection.
No previous suite rerun, service change, BS96, deployment or policy enablement.

This proves snapshot consistency and current workload observations only. Final
Master audit/digest binding and admitted Worker historical outcomes are still
required; a stale valid snapshot or absent Job cannot establish zero rule failures.
Source review found submission exceptions bypass JOB_ERROR and existing logger
omits ERROR; do not build a positive seal from empty rule errors. Next is the
trusted Master audit producer/terminal integration, then dispatch and fences.
CR-01–05 remain incomplete; shared-service window remains reserved for WES UI.

## 2026-09-23 P0 bound workload probe

Added runtime-side read-only Master/Worker probe with exact UID, namespace,
controller-owner and complete container termination checks, including Pods left
after a Job disappears.25 focused synthetic checks passed0.06s on BS10610.
It observes only caller-bound identities, not submission inventory completeness;
it does NOT issue a terminal seal or authorize recovery. No existing runner,
workflow, shared service or automatic policy changed.

Source review confirmed baseline runtime83e7adb's no-active-worker guard is not
sufficient for P0 (no exact Worker UID/residual Pod checks); RUN_FAILED and the
current logger lack a complete classified Master failure summary. Next: trusted
summary plus full submission journal/manifest binding, then terminal writer and
dispatch fencing. Shared service window is held by the WES UI task; no deploy.
Plugin rename f1d3fa58 /0.6.4+bs5 verified metadata-only and recovery source bytes
unchanged; new wheel hash recorded in HANDOFF. Original fixture provenance retained.

## 2026-09-23 actual plugin candidate contract accepted (not end-to-end)

Verified plugin0d606489 clean worktree and candidate wheel SHA256. Original
pipeline=synthetic fixture was not relaxed into the WGS/GATK allowlist; producer
owner regenerated both adapters' fixtures from the same wheel. Four opt-in
consumer checks passed0.08s on BS10610: candidate alone rejects; actual producer
candidate plus an explicitly synthetic terminal matches the draft contract.
Input bytes are hash-pinned. No runtime seal or live recovery acceptance implied.
No plugin-suite rerun, package install, shared deploy or automatic enablement.
Fresh read-only test DB snapshot still had GATK_20260922_112207_23AD29 running
Step1 upload; only own isolated candidate and network-none container were used.
Next: trusted runtime terminal writer and adapter binding/dispatch/callback fences.

## 2026-09-23 P0 internal reservation bridge and WGS manual fence

Implemented current Master-submit/Step3-monitor lineage binding to the existing
reader, evidence validator and reservation budget.22 focused WGS/GATK synthetic
checks passed (1.04s). Added the WGS resume-stage guard against unfinished
automatic recovery; RED reproduced bypass, GREEN8 checks passed (1.17s).
Tests ran only in the BS10610 isolated network-none cached-image candidate.
No shared service, database, live task, BS96 or main/production change.

The proposed trusted binding fields have no adapter writer/caller yet. Producer
source now exists in its independent worktree but no final producer fixture or
terminal-wrapper acceptance was supplied. Automatic recovery remains unwired/off.
Next: actual producer/wrapper binding, reservation dispatch and remaining control/
callback fences; CR-01–05 are not complete. No repeated unchanged helper suites.

## P0 next slice: controlled reader complete, producer integration pending

Added `cce_recovery_reader.py`;26 focused checks passed on BS10610 in the same
network-none read-only synthetic container. Only the new test file ran. No public
route, adapter, auto policy, recovery dispatch or service deploy changed.
Coordinator reports upload gate released; before any future service mutation,
recheck active runs/mounts and coordinate Step7. Test gate release is not approval
to include P1 pause/delete or production work. Plugin owner continues actual
producer implementation; do not claim draft-fixture tests as producer acceptance.

Draft pure `cce_recovery_evidence` validator additionally completed: exact context
binding, candidate digest, complete terminal summary and quiescence required.
BS10610 RED then GREEN62 checks passed0.13s. This is a proposed wrapper contract,
not evidence that today's plugin/Master emits it; no runtime reader or entry wired.

## 2026-09-22 P0 isolated development released; first budget checks passed

User released code development and partial synthetic testing while BS10610's
existing upload completes. Coordinator confirmed separate candidate/no-network
containers only; shared services, jobs, leases, databases and production remain
untouched. Formal deployment and service integration still await its gate.

Implemented internal `cce_recovery_budget.py`: existing AnalysisRun row lock and
RunAction journal, two reservations per frozen attempt, 60/180s waits, immutable
deadline, replay, transaction rollback and stop/control/maintenance checks.
Both frozen policy and initialized budget are mandatory. No public route, policy
initializer or dispatch is wired: this is NOT enabled automatic recovery.
BS10610 isolated RED observed missing module; GREEN: 54 parameterized WGS/GATK
synthetic checks passed in 1.89s. SQLite checks do not prove PostgreSQL concurrent
serialization or live DAG/runtime behavior. CR-01–05 remain incomplete.
Next: bound producer consumer, shared dispatch fences and adapter/DAG integration;
coordinate Step7-owned files before modifying shared paths. See P0 ledger.

## 2026-09-22 P0 implementation prerequisite

The user approved joint plugin/Master/runtime/Airflow implementation, resolving
the external-scope hold. Producer context/failure schema was agreed with the
plugin owner, and attempt-budget tests were prepared locally but not run.
BS10610 deployment and acceptance are paused by the environment coordinator:
the choice between selective production-fix sync and full test-branch deployment
is still pending. No application implementation or passing acceptance is claimed.
See `docs/superpowers/plans/2026-09-22-p0-joint-recovery-progress.md`.
No production, real-task operation or runtime test was performed.

## 2026-09-22 redundant blanket validation removed

The user confirmed that work already developed, tested and published to
production must retain its existing acceptance evidence and must not be put
through a new branch-wide validation cycle merely because its Git history was
synchronized into test. `TEST-VALIDATION-01` is therefore closed as redundant.
The earlier missing-`S1` test is not rerun as a standalone gate; revisit it only
if a newly authorized change touches that path or it blocks that change's focused
acceptance.

The next development priority is now P0 `CCE-RECOVERY-01`: review the bounded
0918A/0919B recovery policy, then implement `CR-01` through `CR-05` with tests
scoped to those new changes. No remote test or runtime action is authorized by
this planning correction.

## 2026-09-22 completed production fixes synchronized into test

The primary test branch now includes production-completed commits `9ff67d3`
(same-batch sampleinfo import and saved Step2 reference restoration) and
`9b381eb` (the corresponding BS96 release record) through an explicit history
merge. These two commits are completed release work, not pending development,
and add no follow-up implementation task. `main` and production remain at
`9b381eb`; test retains its additional test-only history and planning documents.

No runtime environment was changed by this repository sync. The production
release evidence remains in `docs/releases/2026-09-18-sampleinfo-bs96.md`.

## 2026-09-22 prioritized development backlog refresh

The priority audit originally used test tip `e44dc3e`. Current `origin/main` and
`origin/jiucheng/release/production` both point to `9b381eb`; their two later
production-completed commits are now included in test. They must not be counted
as new development or reopened in the backlog.

The current development order is:

1. P0: review and implement the bounded CCE recovery contract (`CR-01`–`CR-05`).
2. P1: implement two-step WGS submission/editable frozen input, then run control
   on top of the reviewed CCE identity/fencing contract.
3. P2/P3: add two-source supplemental QC, then the read-only CNV plot viewer.
4. P4: operator acceptance, combined BS10610 validation, promotion planning and
   non-destructive repository hygiene after the selected scope stabilizes.

This ordering reflects recent operational evidence: 0918A/0919B recovery gaps
affect execution correctness, while the 0919B manual-preparation rollback shows
why submission side effects should move behind final confirmation. The QC change
is supplemental to existing ordinary QC, and CNV viewing is a read-only usability
feature. This planning refresh changes no application code, runtime, database,
remote environment or real task.

## 2026-09-22 CCE recovery design revision only

Follow-up user instruction authorizes submission to the pending-development
test branch. Integration retains remote cd7771b QC/CNV designs and adds only
the four recovery document changes; main/production and runtime stay untouched.
This supersedes the original no-test-merge boundary below, not the no-code gate.

User confirmed inclusion of0918A Worker-creation transport disconnect and0919B
Gatekeeper admission timeout in future automatic checkpoint recovery;0919C
missing FASTQ/input repair remains excluded. The design now proposes two
same-attempt automatic recoveries (60/180s waits), persistent budget/original
deadline, exact failed Master and inactive Worker checks, shared manual/control
fences, UID lineage, automatic downstream progression and truthful shared UI.
The0918A Step4 dispatch timeout retains query-before-replay semantics.

Only the existing connection-recovery spec and CURRENT_STATE/TASKS/HANDOFF
are changed. CR-01–05 are future work; policy details await written review.
No application code, tests, runtime/environment, real task or data changes.
Worktree: `C:/Users/11217/.codex/worktrees/cce-recovery-design-20260922/airflow-demo`;
branch `jiucheng/docs/cce-recovery-design-20260922`, based on local tracking ref
`origin/jiucheng/test/wgs-local-main-sync-20260917=9333160`. This is an isolated
documentation revision, not a primary-test/main/production merge or deployment.
The older repository/deployment observations below remain dated history.

## 2026-09-22 WGS submission simplification proposal

Documentation-only proposal in
`docs/2026-09-22-wgs-two-step-editable-sampleinfo-design.md`: two user steps,
editable per-run sampleinfo before final submit, unchanged native selection,
and narrow automatic-intake release for cancelled uncommitted manual drafts.
Airflow main9b381eb source was inspected. Current native prepare confirmation
was requested from WGS-pipeline thread01a09149-ad9d-7e92-b98a-16d9cae075e2;
its answer confirms native sampleinfo/all refuse existing files, whereas
analysis accepts a valid frozen copy. Native server HEAD ebf1f4b, script last
change9f4f359; actual production runner binding remains unverified. No production
inspection, implementation or tests.
Work branch jiucheng/docs/wgs-submission-design-20260922 is based on test9333160;
the existing0919B operations worktree and its uncommitted records are untouched.


Updated 2026-09-18 after the user authorized a complete Git lineage sync from
current main/production into the primary test branch. Test-only development
remains on the test branch; main and production are now required ancestors.

## Repository role

- Primary test development worktree:
  `D:/pipeline/airflow-demo-worktrees/wgs-local-main-sync-20260917`.
- Primary test development branch:
  `jiucheng/test/wgs-local-main-sync-20260917`.
- Pre-sync test tip: `f0b07c4`. The approved three-fix integration is committed
  as `8f062f9`; repository-state consolidation is `91060d0`.
- This is the only remote branch under `origin/jiucheng/test/*`.

## Branch relationship rule

Current `origin/main` and `origin/jiucheng/release/production` both point to
`9b381eb`. Test now includes that history, including the completed same-batch /
Step2 fix and its production release record. The branch relationship remains:

- current main and production are ancestors of the test branch;
- test may retain additional test-only implementation and evidence;
- test-to-main promotion remains a separate reviewed and authorized action;
- old worktree/patch branches are not merge sources unless separately selected.

The two former main-only commits `9ff67d3` and `9b381eb` are completed work and
must not create new development cards. Calculate divergence from live refs
because planning documentation itself advances test; do not rebase or discard
test commits.
See `docs/TEST_BRANCH_SYNC_HOLD_20260918.md` for the original decision transition.

## Consolidated development designs

The primary test branch owns the current documentation-only development queue.
Its consolidated designs include:

- Run control from `jiucheng/feature/run-control-20260918` commit `1c631b7`:
  controlled CCE pause, same-attempt checkpoint recovery and exact online
  project deletion. See
  `docs/superpowers/specs/2026-09-18-run-control.md` and `RC-01` through `RC-05`.
- WGS two-source QC from `jiucheng/docs/wgs-qc-two-source-20260918` commit
  `53fc860`: required ordinary `QCstat.tsv` plus conditional source-qualified
  `multi.QCstat.tsv` evidence for `F57J`/`UPC` samples. See
  `docs/2026-09-18-wgs-qc-two-source-contract.md` and `QC2-01` through `QC2-03`.
- WGS CNV plot viewer design: a WGS-only Run Detail tab lists selected sample
  IDs and streams one native bound `03_CNV/<sample_id>.CNV_genome.png` at a
  time. It is not implemented; no generic artifact reader, image conversion,
  workflow/QC change, test run or deployment is authorized. See
  `docs/2026-09-18-wgs-cnv-plot-viewer-design.md` and `CNV-01` through `CNV-03`.
- Bounded CCE recovery for the approved 0918A Worker-create disconnect and
  0919B Gatekeeper timeout causes, explicitly excluding 0919C input repair. See
  `docs/superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md`
  and `CR-01` through `CR-05`.
- Two-step WGS submission and revisioned editable frozen sampleinfo, with final
  submit before analysis side effects. See
  `docs/2026-09-22-wgs-two-step-editable-sampleinfo-design.md` and
  `SUBMIT2-01` through `SUBMIT2-04`.

These designs are documented and their implementation has not started; the
revised CCE policy still awaits review. They are proposals, not available APIs
or runtime capabilities. This consolidation did
not authorize code, schema, application tests, remote validation, deployment or
real task/data operations. Existing `CCE-RECOVERY-01` remains a separate but
prerequisite-aligned implementation track; run control must reuse its execution
versus monitoring-state contract instead of creating a competing path.

## Test environment and readiness

The target is BS10610/server10610 test. Runtime roots, gates and release
fingerprints remain governed by
`docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`. Selective-sync validation used an
isolated candidate under the BS10610 control root; no service was deployed or
restarted, no analysis was submitted and no execution gate changed.

The branch contains recorded Local/SGE integration, native execution views,
CCE log-package download, native labels, GATK phase projection and worker-child
timing work. It is not declared fully tested or ready for main. Remaining work
includes reconciling the archived open checklist against current code/evidence,
the revised CCE recovery implementation, two-step submission, run control,
two-source QC, CNV viewing, operator-facing visual acceptance and one final
combined BS10610 acceptance after the branch scope stabilizes.

## Repository hygiene

The user reprioritized repository cleanup before the validation matrix. The
2026-09-18 safe pass removed ten worktrees and fifteen local branches. Unique
branches or state-only dirty documents were bundle/patch-preserved before their
worktrees were removed.
Six nonregistered legacy directories and nineteen loose packages were moved to
`D:/pipeline/task-artifacts/airflow-repo-hygiene-20260918` rather than deleted.

Eight dirty worktrees remain registered and protected, including the primary
test worktree. Their content must be triaged before any further removal. See
`docs/REPOSITORY_HYGIENE_20260918.md`.

## Open work

`TASKS.md` is the authoritative compact queue. Continue the remaining dirty-
worktree triage and test validation matrix; begin any documented development
track only after a separate implementation instruction. No production
deployment or live data operation is authorized.

## Historical evidence

The complete pre-consolidation files are preserved with SHA-256 hashes at
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`. Git history and
the existing release/design documents remain evidence; they are not reusable
runtime authorization or proof that every test is complete.
