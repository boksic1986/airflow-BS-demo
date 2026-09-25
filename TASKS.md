# Active test-branch tasks

## 2026-09-26 current slice: R1 SFS publication only

- [x] Resume original WGS owner under explicit step1 authorization and deliver
  accepted0.8.6/Master/r2 binding evidence.
- [ ] Rebind candidate publication metadata, audit ACTIVE_ASSETS compatibility,
  publish independent4.2.2 SFS paths and obtain minimal publication receipt.
- [ ] Review exact manifests/READY/paths and record accepted R1 result.

Do not execute R4, activate profiles on Airflow, merge shared branches or deploy
BS96 in this slice. Runtime-first completion below remains valid.

## 2026-09-25 current slice: runtime installation, image, profile

User confirmed the pause is only WGS/SFS. Runtime-first slice completed2026-09-26;
source/wheel/profile/owner receipt reviewed, with no SFS or platform activation.

- [x] R2a-fix: native owner removes fixed0.8.5 release restriction, retains version
  equality; minimal remote matched/mismatched-version tests, user-selected0.8.6.
- [x] R2a: original native/Infra owner verifies SOP target and installs the fixed
  0.8.6 successor to0.8.5+p02.dev3 without unrelated dependency changes.
- [x] R2b: push the accepted WGS Master to a new SWR tag and record RepoDigest.
- [x] R3a: bind a new immutable inactive WGS4.2.2 profile to the accepted image,
  native version and frozen source/resource contract; record path/SHA.
- [ ] Later: R1 SFS publication, R4 Airflow API/dashboard/test integration, then
  authorized Airflow main/production-branch synchronization and minimal tests.

Latest scope prioritizes the first three items only. Existing R1-first dependency
below is historical and superseded by the latest section in the release plan.
Exact receipts: docs/releases/2026-09-26-cce086-wgs-profile.md. Future SFS release
must rebind manifest/SOURCE_READY to r2; existing r1 readiness does not apply.

## 2026-09-25 new WGS4.2.2 / P0 four-step plan

- [x] Coordinate original WGS/native owners and document exact sequence, baseline
  preservation, permissions, candidate activation and minimal verification.
- [ ] R1: freeze refreshed4.2.2 source/resources (including whitelist/index), audit
  ACTIVE_ASSETS consumers, publish and verify SFS with existing owner.
  Source/manifest refreshed;13 objects and SOURCE_READY uploaded/verified from
  node005. Supported node005 apply delegates kubectl to BS10610, but the
  configured workstation-style alias cannot resolve on node005. User directs
  existing local SSH/direct-IP routes; local BS10610 verified and Infra checks
  existing node005 direct configuration, without adding global SSH aliases.
  No SFS publication yet.
- [ ] R2: compatibility check, exact rollback, nipttest dev3 install and WGS Master
  SWR publication; no GATK or unnecessary rebuild.
- [ ] R3: versioned4.2.2 profile/catalog candidate with frozen hashes/digest.
- [ ] R4: integrate production fixes + deployedae416fa + P0 into test branch,
  preserve both sets of fixes, deploy paired test consumers and verify narrowly.
Plan: docs/superpowers/plans/2026-09-25-wgs422-p0-test-release.md.
This supersedes the directfdace86 rollout sequence below. User authorized execution
on 2026-09-25; R1 is in progress with the original owner; R2–R4 remain pending.

## 2026-09-25 WGS-only rollout continuation

- [x] Record user approval: WGS only, GATK/WES deferred and not a blocker.
- [x] Fresh read-only owner preflight and coordinator source comparison expose
  missing backend P0 APIs and divergent ae416fa/fdace86 baseline; no writes.
- [ ] Confirm bounded test-baseline integration preserving Step7 and transfer
  display fixes; do not deploy fdace86 wholesale or invent a WGS-only API fork.
- [ ] Original native/Infra owner: exact test-consumer and active-use preflight,
  scoped paired installation with rollback, minimum synthetic recovery check.
- [ ] Coordinator: reconcile actual receipt and update installation/acceptance
  status separately; no production or automatic enablement inferred.

## 2026-09-25 authorized validation corrections

- [x] Task1 native/paired trust, cloud query, probe and shared-output corrections.
  Native ae90b65, paired297bcee plus reviewed follow-up; affected111 passed.
- [x] Task2 platform workload observation and finite probe-budget corrections.
  Affected34 plus two fixture-only rechecks passed; DAG8 passed. Review closed.
- [ ] Task3 combined review, affected artifacts and scoped nipttest/paired-test
  continuation with exact preflight and rollback. No production authorization.
  Review and dev3 offline artifacts complete; actual node200 test gate is old.
  Proposed runtime dependency/consumer and test-service rollout scope still need
  closure/confirmation. No installation, SWR push or service switch performed.
  Plan: docs/superpowers/plans/2026-09-25-p0-validation-corrections.md.

## 2026-09-25 P0 validation source review

- [x] P0-VALIDATION-AUDIT: static platform/native call-chain review; findings
  V01–V07 in docs/reviews/2026-09-25-p0-validation-audit.md. No runtime testing.
- [ ] Correct V01–V03 in existing entry/guard/observation paths, then V04–V06;
  align V07 finite query budgets. Source work is not performed by this review.
  Preserve identity, lock, immutable-input and complete-evidence protections.
  Installation/activation acceptance remains open; no new feature or production
  operation is authorized by this audit entry.

## 2026-09-25 non-root deployment audit

- [x] P0-NONROOT-DOC: withdraw root-only ownership and /etc-only activation
  requirements; distinguish chenjc/ctapa/chenjx roles and retain scoped trust
  protections. Audit platform/native checks and the substituted test fixture.
- [ ] P0-NONROOT-ENTRY: platform/native owners adapt existing selectors/guard
  to deployment-managed non-root trust; bounded actual-interpreter checks only.
  No hardcoded username list, policy self-authorization or EUID-only substitute.
  This is an identified source gap, not a request to acquire root privileges.
- [ ] Installation/activation remains separate: agreed nipttest, exact rollback,
  approved paired test scope, unchanged WGS/production. No new service/container.

## 2026-09-25 SWR publication follow-up

- [x] P0-SWR-PUBLISH: two accepted images published with non-overwriting tags;
  coordinator checked registry manifest/config linkage and8 evidence hashes.
- [ ] P0-NIPTTEST-PREFLIGHT: shared install/version observations documented.
  Exact old-package rollback and approved test-isolation/install scope still
  needed. P0-NONROOT-ENTRY must correct the current incompatible selector;
  root-owned interpreter/install authority is no longer a requirement.
  No installation or dependency upgrade.
- [x] P0-TTL-LIVE: exact authorized no-data Jobs reached Complete/exit0 and
  Failed/exit17, then both Jobs/owner Pods auto-removed; no manual cleanup.
  Coordinator inspected originals and15 evidence hashes; no existing changes.
- [ ] P0-OPS-GATES remains open; publication is not activation or cloud acceptance.

## 2026-09-25 items2/3 execution handoff

- [x] P0-FINAL-PLUGIN: owner delivered5ffcb07 /0.6.4+bs8.dev2, actual wheel4 pass;
  record docs/releases/2026-09-25-p0-final-candidates.md. No installation.
- [x] P0-FINAL-NATIVE: d84bace /0.8.5+p02.dev2 plus WGS/GATK Master images;
  TTL3 passed, missing terminal6 passed against final candidate; both smokes pass.
  Receipts, actual hashes and prior failures checked; no installation or push.
- [ ] P0-OPS-GATES: same owner requested read-only environment/capacity/AOM audit;
  exact cloud mutation/notification/activation scope still requires confirmation.

This supersedes the previous turn's "not dispatched" status, not its permission
boundaries. No artifact or live gate is closed merely by dispatching these tasks.

## 2026-09-25 documentation coordination / owner handoff

- [x] Reconcile total ledger, runbook and Task6 source closure; preserve historical
  Task5 acceptance and mark it as pre-Task6, not a final release candidate.
- [x] Record source pins and owner/deliverable/dependency/permission-stop boundaries
  in docs/superpowers/plans/2026-09-22-p0-joint-recovery-progress.md.
- [ ] P0-FINAL-PLUGIN: plugin owner produces successor wheel and provenance.
- [ ] P0-FINAL-NATIVE: cce-pipeline owner produces successor wheel and WGS/GATK
  Master artifacts using the accepted successor plugin; authorized Infra assists.
- [ ] P0-OPS-GATES: release/Infra owner verifies live writer/storage mapping,
  real TTL, capacity, AOM and alerts under confirmed operational scope.

Owner cards are a handoff plan, not dispatched jobs. This turn is local docs/Git
only: no remote preflight, Docker/Compose, build, runtime test, install or rollout.
Permission or environment failures require immediate reporting, not workarounds.

## Task6 source accepted; operational gates open — 2026-09-25

- [x] One fresh whole-plan review: one Important selected terminal conflict,
  no Critical/Minor findings. Native1bc67fd fixes opposite live/persistent
  terminal conditions; RED2, final affected13 pass on BS10610. No second review.
  Source gates complete; historical pending notes below are superseded.
- [ ] Separately authorized release acceptance: final Task6 artifacts and exact
  paired-writer/storage activation, live TTL, Pod capacity and AOM/alerts.
  No production enablement inferred from source/synthetic acceptance.

- [x] PostgreSQL row-lock contention: 10 focused cases on disposable BS10610 PG,
  verified pg_stat_activity lock waits; no service DB connection.
- [x] Automatic/manual lifecycle: 4 WGS/GATK source-level integration cases reach
  Step6 and normal finalize, original attempt and one automatic slot retained.
  Actual DAG/producer/native/consumer code; external transports synthetic.
  Fix same-action reclaimed-Master re-entry and deadline-bearing journal reader.

- [x] Finite query owner wired through real selected WGS/GATK monitors and existing
  status persistence; outer failures retain marker, backend/view distinguish
  unconfirmed execution, callback and periodic Airflow sync cannot mark analysis
  failed from query exhaustion. Native fd43f88; BS10610 regression113 plus final
  affected producer/consumer16 and actual selected-monitor4 pass. Source only.
- [x] Manual reconnect/automatic action boundary: failed observer is not failed
  compute; exact confirmed ended observer can be explicitly handed off under
  the run lock, old action canceled without a terminal-compute claim. Idempotent
  successor retains attempt/budget/deadline; GATK deadline inheritance repaired.
  Existing detail confirmation reused for query attention. BS10610 backend82,
  frontend2 pass (2026-09-25); no production or source-artifact rebuild.
- [x] Final whole-plan fresh review before CR-04/Task6 source closure; operational
  cloud TTL/capacity/AOM acceptance remains separately authorized.
- [x] Inspect Task4/5 producer versus existing automatic-recovery consumer.
- [x] User approved necessary wrapper/logger failure-summary addition before extending
  runtime source; preserve existing biological workflow and accepted artifacts.
- [x] Complete phase-bound logger accounting, final snapshot and real Snakemake
  lifecycle validation; incomplete/mixed failures remain ineligible.
- [x] Bind automatic evidence to schema2 platform/native identities without
  conflating their execution IDs, generations or request hashes.
- [x] Internal due-dispatch adapter: existing automatic reservation -> existing
  Resume dispatcher/adapter registration, durable prepared identity, no duplicate
  slot/POST; crash revalidates source. BS10610 targeted23 GREEN4.68s.
- [x] Default-off new-run policy/budget freeze, first monitor deadline and replay;
  existing authenticated stage POST/Airflow sensor handoff; terminal compute
  lifecycle across two shared slots and old/current DagRun cleanup identity.
  BS10610 backend19 GREEN4.70s + real-Airflow5 GREEN3.00s (2026-09-25).
- [x] Original registered deadline consumed by native replacement and WGS/GATK
  monitor loops; capped handoff, immutable replay, expiry fencing and unchanged
  untagged manual native ABI. BS10610 focused22 GREEN16.25s (2026-09-25).
- [x] Same-owner Worker natural wait via existing durable Airflow action,
  max600s/original deadline, fixed read-only probe, immutable failed receipt,
  nonce/identity/FINAL check, one compute slot and strict native dispatch fence.
  BS10610 final17+2+4 targeted cases GREEN (2026-09-25), source only.
- [x] Exact CREATE storage RPC/peer-reset and mutation Gatekeeper deadline source
  classification; deterministic Job reconciliation, strict typed consumer fields,
  original budgets and default-off policy. BS10610 final30+2 GREEN (2026-09-25).
- [x] Step4 registered original-operation reconciliation wired to existing stage
  routes/runner/reschedule sensor: hashed opt-in marker and original deadline,
  durable begin/check/finish/poll, exact-generation/hash sends, control/manual
  resume fences, normal successful receipt before downstream. BS10610 final
  backend/runtime90 GREEN7.11s + actual-Airflow20 GREEN3.04s (2026-09-25).
- [x] Existing Tracker/detail recovery projection checkpoint: durable waiting,
  uncertain, exact started Master, exhausted/expired, stale and completed-degraded
  labels; retain measured progress without advancing estimates. Real WGS/GATK
  ingestion retains scoped observation. BS10610 backend26/frontend13/build GREEN.
- [x] Finite query-budget prerequisite: max6 retries30/60/120/240/300/300,
  request/original deadline caps, durable callback reservation, interrupted retry
  accounting, strict identity and non-retryable controls. Paired strict native GET
  fixes existing exact ConfigMap ABI and timeout/error classification. BS10610
  native24 + platform17 GREEN0.79s. Wiring accepted in the later checkpoint above;
  deployment/activation remains closed.
- [x] Connect query-only owner to real WGS/GATK selected monitor/status JSON;
  distinguish query exhaustion/control from analysis failure in GATK ingestion,
  callback/periodic projection and existing UI. Do not wrap CREATE/START or an
  entire stage; no second retry budget. Preserve last confirmed progress.
- [x] Focused PostgreSQL contention, full automatic/manual lifecycle and whole-plan
  review completed in the latest source acceptance above. Native/plugin artifacts
  and default-off policy unchanged; this is not rollout approval.
- [ ] Separately authorized live TTL/capacity/AOM/alerts gates remain closed.

Task6 prerequisite accepted: final focused28 GREEN35.59s on BS10610. The selected
monitor and normal immutable receipt reach the existing reservation owner;
source classification/receipt acceptance is not automatic dispatch acceptance.
This prerequisite entry is historical; Task6 source implementation and acceptance
are complete as recorded above. It does not authorize production, installed policy,
real reruns or operational gates.

## Historical Task5 accepted — 2026-09-24 (pre-Task6 artifacts)

- TTL source and targeted BS10610 matrix accepted; distinct offline wheels and
  WGS/GATK Master images built. Actual-wheel13 passed, image smokes2 passed.
  Provenance: docs/releases/2026-09-24-p02-task5-offline-artifacts.md.
  Task6 next; no production activation or live TTL/controller acceptance.

## Historical authoritative status — 2026-09-24 (superseded above)

- [x] P0-2 Task4 manual closure: authenticated service and real DAG methods,
  actual restricted WGS/GATK runtime, fresh-process monitoring and normal Step4–6
  receipts; same attempt/frozen inputs/workdir and no prepare/upload redo.
- [x] Initial interrupted handoff, post-bind crash, direct Step3 recovery and
  original producer identity across new observers; no duplicate CREATE/START.
- [x] Final protected release with sealed historical Worker lineage, complete
  live inventory and inactive dispatchers; unknown/active objects block.
- [x] Final review findings fixed and latest design checked. BS10610 selected41
  passed/1 adapter-inapplicable skip; authenticated full manual flows2 passed.
- [x] Task5: existing Worker/Master/reader generators, compatible pinned artifacts
  and bounded offline TTL-recovery acceptance; no release/production activation.
- [ ] Task6: remaining automatic dispatch/UI/PostgreSQL/operational gates.

The entries below retain checkpoint history; older OPEN wording describes that
checkpoint only. Do not repeat completed slices or treat Task4 as all P0 complete.

- [x] Task4 Step2-selected Master -> fresh Step3 WGS/GATK monitor and rule bridge.
  Native journal/receipt/current lock revalidated; old completion marker ignored;
  reclaimed success/failure bound to the new Master. BS10610 final18 GREEN30.04s,
  affected Step2 replay2/worker disconnect1/unactivated entry2 GREEN. Native903e1af.
  No deployment. Direct Step3/initial-submit paths closed by current acceptance.

- [x] Task4 registered Step2 capability factory and actual WGS/GATK Resume routing.
  Request hash/current bytes, operator binding/storage, exact native old lock
  owner and sibling dispatcher exclusion checked before native replacement.
  BS10610 entry2 RED, real GATK shape1 RED; final14 + affected3 GREEN.
  No activation, policy installation, production or original bundle changes.

- [x] Task4 verified Master metadata through normal WGS/GATK status writers;
  GATK receipt hash covers it, WGS worker failure retains it, JSON cannot grant
  authority, old submit identity is not relabelled as the observing execution.
  BS10610 two RED -> GREEN; affected7 GREEN; final refined receipt2 GREEN.
- [x] Task4: complete direct Step3/initial-submit selection, selected Step4-6
  execution across processes, final protected release and full manual synthetic flow.
  Current full manual acceptance supersedes the earlier in-process checkpoint.

- [x] Activated WGS/GATK Resume without verified capability cannot use legacy
  locking. Follow-up2 RED; final paired-entry12 + existing3 GREEN on BS10610.

- [x] Task4 user-approved cloud reader identity source: read-only workspace only,
  PVC/PV and Job/Pod fences, actual directory resolution, durable one-create and
  safe cleanup replay. BS10610 cloud10 + protected-entry13 GREEN.
- [x] Task4 paired external runtime selection in real WGS/GATK stage builders and
  Resume loaders; GATK custom materialization guarded without changing output.
  New10 + affected existing3 GREEN; no activation policy installed.

- [x] Task4 native selected-Master Step4/5/log-export reader with original delivery
  roots (native08c6cda); BS10610 affected10 passed.
- [x] Task4 WGS/GATK Resume exports validated v2 platform/native binding metadata;
  source identities are not substituted, ready/legacy results not relabelled;6 passed.
- [x] User confirmed CLI Step1–6 scope; native8ec5415 adds source entry guards and
  operator-owned physical mapping/version/binding checks. New12/affected35/legacy3
  BS10610 checks GREEN; no operator configuration or runtime installed.
- [x] Complete
  trusted storage/all-writer and actual restricted-gate receipt forwarding before
  Task4 acceptance. Tasks5/6 remain unstarted, not skipped or marked complete.
- [x] Canonical SFS identity choice confirmed: existing cloud read-only reader,
  no new host mount. Never equate local analysis NFS with cloud SFS.

- [x] Task4 GATK Step1–6 dispatcher launch/worker fence and late-receipt protection;
  BS10610 focused15 passed. This is not the full Task4 manual mock acceptance.

## 2026-09-24 Task4 GATK dispatch checkpoint

- [x] GATK own service registers frozen v2 requests/history in PipelineStageExecution;
  same RunAction/attempt and one durable Airflow POST, not WGS execution internals.
- [x] Existing authenticated endpoint routes by registered adapter; actual
  DagRun/action scope fences registration/acquire/finalize. GATK capability stays off.
- [x] GATK DAG skips prepare/upload/completed stages on Resume; affected isolated tests.
- [x] User confirmed initial Master platform-identity bootstrap source addition.
- [x] Native initial view/Step2 source and separate platform/native binding;
  WGS/GATK Resume identity propagation. BS10610 native41 plus composition2 passed.
- [x] Implement trusted binding writer, all-writer/dispatcher proof and selected-view
  downstream integration. No native/platform request-hash substitution.
- [x] Complete Task4 manual native mock acceptance before Task5, then Task6.

## Historical Task4 WGS dispatch checkpoint (then OPEN; now superseded)

- [x] Existing authenticated WGS Resume: durable POST intent, exact DagRun
  reconciliation, no second POST after uncertain response/404; preserve attempt.
- [x] Actual DagRun identity for recovery stages/acquire/finalize; deny stale
  action/DAG and out-of-scope prepare. Recheck after slot-helper commit.
- [x] Preserve newer running/stop/failure state on late reply; permit finalizing
  already-successful Step6 without rerunning it. BS10610 affected checks/review.
- [x] GATK own authenticated service/DAG/Resume integration.
- [x] Trusted native Master binding writer + canonical/legacy lock mapping,
  paired all-writer compatibility and old dispatcher quiescence proof.
- [x] Selected recovery view carried into monitor and downstream receipt paths;
  parameterized WGS/GATK manual closure before any Task5 TTL activation.

No production, automatic recovery, image/CLI release, main/production merge or
push. This is a Task4 source checkpoint, not whole-task/P0 completion.

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

Task3 DEPENDENCIES ACCEPTED (2026-09-24, explicitly approved): native final
Worker snapshot + independent generation view, current-bound reader, complete
journal/terminal/live inventory validation. BS10610 view6 + final18 + live10 new
cases passed;5 affected checks. Remaining: trusted canonical lock capability,
existing WGS/GATK Resume replacement/journal integration and final composition.
Not Task3 complete; no Task4/TTL/automatic activation or production operation.

Task3 CONFIRMATION/NATIVE SUCCESS CHECKPOINT (2026-09-23): bounded classified
queries, START_CONFIRMED consumer, active GATK v2 reuse and bound native success
reader connected to existing Resume.27 new remote synthetic cases passed with
RED/GREEN. Task3 remains OPEN: final Worker inventory and next-generation view
were missing producer dependencies at that checkpoint; resolved above. Failed v2
replacement blocks before mutation. No lock-v2 activation or Task4/TTL advance.

Task3 IN PROGRESS, first guard checkpoint (2026-09-23): WGS ambiguous CREATE
replay/disappeared replacement cannot create again; pre-delete UID/RV recheck
and durable journal, both adapters reject incomplete Pod pages, GATK missing
archived Worker is unknown not terminal. BS10610:8 new +13 affected tests pass;
includes review-found delayed failed replacement under unresolved submission.
Remaining Task3: verified handoff/native success, persisted terminal+full inventory
reconciliation, trusted canonical-directory/legacy-lock consumers. Task4 remains
authenticated adapter/DAG/all-writer closure; Task5 TTL stays gated.
Deferred separately: same-batch new analysis after Step7/local deletion still
needs platform registration/snapshot lifecycle work. Do not delete history,
change batch uniqueness or claim this behavior is delivered by the new locks.

Task2 SOURCE PRIMITIVES COMPLETE: plugin5b5d7ee (successor source0.6.4+bs8.dev1),
cce-pipeline7926496. Exact Worker terminal publication/query pruning; opt-in
directory owner/generation CAS, legacy guard/snapshot, fenced release.
BS10610:15 +17 new,5 +3 affected legacy tests passed; focused review resolved.
User clarified five reruns are compatibility scope, not operational permission.
Next Task3: trusted canonical-directory/legacy mapping, full inventory verifier,
actual existing journal and Resume consumers; Task4 covers all authenticated
adapter/stage paths. Do not enable v2 with old writers or rewrite frozen bundles.
No production/cloud action, deployment, TTL or automatic policy activation.

P0-2 Task1 SOURCE COMPLETE (2026-09-23): cce-pipeline c33740d from verified
83e7adb, independent `jiucheng/runtime/p02-master-handoff-20260923` branch.
Master confirmation, same-Pod atomic process claim and bound native terminal
records;24 new +18 affected legacy BS10610 tests passed. Producer contract and
plan updated; no deployment/artifact acceptance. Prior SSH/source-pin blockers
below are historical and resolved for this task. Tasks2–6 remain open; next is
Worker terminal and logical-run lock ownership, not TTL/policy activation.

P0-2 revised implementation sequence recorded in
docs/superpowers/plans/2026-09-23-p0-2-master-handoff-ttl-implementation.md.
Design revisions through781877e integrated; P0-2E lock handoff and TTL must ship
together. Planning complete; Task1 source acceptance complete, Tasks2–6 open
(not P0 completion). No local test fallback or production. Task2 still requires
fresh plugin source/ownership verification before its edits.

CR-03 receipt projection subtask complete: WGS stage-status and GATK sync hold
the refreshed current-run lock through execution validation/state projection;
old attempts reject, cached active execution cannot overwrite durable success.
BS10610:8 focused +5 affected legacy cases passed, not a full observer/concurrency
acceptance. Continue existing trusted terminal/binding, dispatch/adapter, other
evidence projection and Step4 work. No production or automatic enablement.

CR-01/03 control inventory + actual bs7 acceptance complete: immutable source
25297f9/wheel2ad4aa737e6f;34 inventory cases and4 hash-pinned real producer
scopes passed on BS10610. Known/null candidate UID retains admitted journal UID,
missing/mixed/conflicting inventory blocks; no fake FAILED submit events.
Plugin owner's guarded offline build completed52 affected actual-wheel tests;
bs6 unchanged. No live terminal evidence/dispatch/policy enablement.
Next: existing runtime query provenance, trusted terminal and adapter/dispatch/
observer/Step4 integration. Prior SSH-blocked checkpoint below is resolved.

Next control-inventory integration started after26d62dd;10test cases drafted
but not run because BS10610 via BS handshake failed on copy and RED invocation.
No inventory implementation/acceptance yet; retain draft and resume at fresh
preflight then RED. No local or production fallback, no extra SSH retry loop.

CR-01/03 2026-09-23 coverage extension: user approved adding current disconnect
types before continuing P0. GATK exact-identity slot acquisition bounded retry
implemented (7 actual DAG checks;2 backend lease checks). Control-read candidate
consumer and single-source stable reader implemented; BS10610 synthetic green.
New plugin artifact and actual fixture/inventory integration pending; preserve
bs6, quota behavior and existing two-recovery budget. D CREATE RPC500 needs
source-call confirmation; generic C/E/WES kubectl errors remain unclassified.
No new audit track, runtime deployment or automatic enablement. Next is actual
contract integration then existing dispatcher/adapter/observer/Step4 work.

CR-03 external cleanup fence complete: WGS/GATK three transfer release stages
and WGS observer deactivate reject stale/missing recovery DagRun identity under
a refreshed run lock. WGS partial release rechecks after the primitive commits;
current cleanup still requires terminal transfer evidence. Actual DAG run_id
propagated, WGS manual recovery identity retained.24 new backend+3 legacy API+7
DAG checks passed on isolated BS10610. No dispatch or policy enablement.
Next: existing dispatcher/adapter continuation and observer projection fences;
trusted terminal, Step4 and PostgreSQL/end-to-end proof remain open.

CR-03 DagRun failure callbacks: WGS/GATK pending-action and exact-current-DagRun
fences implemented; GATK callback/API identity propagated; WGS failure history
dedup now includes DagRun identity. BS1061022 new backend +5 legacy +1 actual
DAG callback checks passed after two scoped RED reproductions. No automatic
dispatch/enablement or service change. Remaining: adapter/dispatch/lease and
observer fences, complete runtime evidence, PostgreSQL concurrency/integration.

CR-02/03 WGS manual service entries: legacy Resume/Rerun failed joined the
existing resume_stage pending-recovery fence under a refreshed run row lock.
22 focused BS10610 checks passed after observed RED bypass; user cancel priority
and completed recovery history preserved. No new route or recovery enablement.
Remaining dispatch/callback/lease and adapter/GATK controls are not complete;
SQLite tests do not establish PostgreSQL concurrency acceptance.

CR-01 bs6 candidate-format acceptance complete: actual wheel-generated WGS/GATK
admission+guard fixtures, raw-file/wheel/provenance SHA pins;14 BS10610 checks
passed0.32s,62 unrelated cases deselected. No existing production behavior change.
No live terminal/recovery acceptance: synthetic terminal scaffolding is not proof
of complete Master history. Continue remaining CR-02/03 control/dispatch/callback
and adapter work under existing scope; do not mark end-to-end P0 complete.

CR-01 bs6 consumer acceptance in progress, not passed: BS10610 preflight blocked
at BS jump host172.17.61.18:22 handshake. Actual producer fixtures requested;
WORKER_SUBMIT_GUARD_FAILED negative test added but not run. Next: fresh test-host
fingerprint, hash-bound actual bs6 fixtures, only affected consumer/inventory
checks. No broader regression, localhost substitute or production mutation.

CR-01 producer update: bs6 candidate0b19bb605cdff619a7f09b34a6fe774e4b43d357
received from owner, including preserved HeavySlotQuota and duplicate-adoption
manifest fix. Owner reports86 source +86 wheel checks. Actual bs6 consumer
acceptance remains pending; no complete terminal producer or deployment implied.
WORKER_SUBMIT_GUARD_FAILED remains outside the automatic allowlist.

2026-09-23 scope correction: no additional Master audit/producer track. The
batch example only checks diagnostic completeness. Continue existing CR-01–05;
next consumer work is remaining control/dispatch/callback fences and adapter
integration using the actual delivered bs6 contract. Preserve the full
HeavySlotQuota behavior in the runtime owner's integration. Do not treat a
candidate, absent log or BackoffLimitExceeded as complete failure proof.
Audit-dependent draft is stashed, not delivered or tested GREEN. Prior audit
implementation instructions below are historical, not current scope.

CR-03 Master observation increment: Job reason (including BackoffLimitExceeded)
and all observed Master Pod/container termination and restart details retained.
34 affected BS10610 checks passed. This is diagnostic evidence, not complete
Master error coverage or automatic eligibility; full producer/footer still pending.

CR-03 next prerequisite: submission journal/checkpoint/candidate/manifest
validation now composes with the UID probe.26 focused BS10610 checks passed,
including actual WGS/GATK producer fixtures. No finality/terminal seal, complete
Master error audit, Worker history proof, dispatch or automatic enablement yet.
Next: trusted producer and terminal integration; do not add unrelated controls.

CR-03 prerequisite slice: UID-bound read-only workload probe implemented;
25 checks passed on BS10610. No old Resume behavior changed and no terminal
seal emitted. Full Master error summary + complete journal/manifest binding,
terminal writer, adapter/dispatch/callback integration remain required.
Shared backend/frontend deployment held for WES UI task; independent tests only.

CR-01 producer-to-consumer compatibility: plugin0d606489 actual WGS/GATK fixture
bytes and wheel hash verified;4 consumer checks passed0.08s on BS10610. This
supersedes pending-fixture notes below, not pending trusted runtime terminal
generation, binding writer or live integration. Automatic policy remains off.

2026-09-23 CR-01/02 slice: internal Master-submit/monitor lineage-to-reservation
bridge implemented;22 focused synthetic checks passed. WGS resume-stage refuses
unfinished automatic recovery before mutation/dispatch;8 entry tests passed.
No trusted binding writer, runtime caller, dispatch or policy enablement yet.
Real producer/wrapper, remaining entry-point fences, callbacks and PostgreSQL
concurrency remain outstanding. This does not complete CR-01 or CR-02.

CR-01 reader slice: controlled fixed-file reader implemented,26 new focused
synthetic checks passed. Still pending actual plugin fixture + trusted terminal
wrapper + Master-submit/monitor lineage; CR-01 is NOT end-to-end complete.
Upload gate released per coordinator; service deployment still needs fresh
active-run/mount verification and serialization with Step7. No P1 scope added.

Draft pure evidence validator passed62 synthetic contract checks; actual producer
fixture and trusted terminal-seal generation remain unverified and unwired.

P0 implementation approved (2026-09-22), including external executor/Master
scope. CR-01–05 remain incomplete. Isolated development/no-network synthetic
tests released while the existing upload runs; formal BS10610 service integration
still awaits the coordinator. Internal CR-02 budget primitive implemented and
54 focused WGS/GATK checks passed; no routes, automatic policy or dispatch enabled.
Producer consumer, dispatch/control fences, adapter/DAG/UI work and concurrent
PostgreSQL acceptance remain; see the P0 progress ledger.
Do not substitute text-based guessing for bound source evidence.

Updated 2026-09-22 after refreshing the authoritative test branch and
reassessing all documented development against current main/production.
Historical tasks are archived and are not silently reopened or marked complete.

## Priority and execution order

| Priority | Track | Why now / entry gate |
| --- | --- | --- |
| P0 | `CCE-RECOVERY-01` / `CR-01`–`CR-05` | Prevent monitoring/infrastructure faults from producing unsafe status or duplicate compute; this is a dependency for run control. |
| P1 | `WGS-SUBMIT2-20260922` | Reduce manual-preparation side effects and confirmation errors; verify the actual runner binding before implementation. |
| P1 | `RUN-CONTROL-20260918` | Operator safety is important, but pause/resume/delete must reuse the reviewed CCE recovery identity, budget and fencing contracts. |
| P2 | `WGS-QC-TWO-SOURCE-20260918` | Bounded supplemental QC projection; ordinary QC remains authoritative, so it follows runtime and submission safety work. |
| P3 | `WGS-CNVPLOT-20260918` | Read-only usability enhancement with no workflow or QC decision effect. |
| P4 | Acceptance, promotion and hygiene | Execute after selected implementation scope stabilizes; hygiene cannot discard unclassified worktrees. |

Do not start two tracks that edit the same Backend/Airflow contracts at once.
Within P1, finish the submission gate/frozen-input contract before beginning
run-control Backend/Airflow integration. The QC and CNV tracks are independent
only after their owner worktrees are isolated from the synchronized baseline.

## WGS-SUBMIT2-20260922 — proposal written; native source confirmed

Spec: `docs/2026-09-22-wgs-two-step-editable-sampleinfo-design.md`.
- [x] Audit approval/cancel boundaries, runtime input/hash and intake deduplication.
- [x] Design two-step confirmation and editable frozen sampleinfo input.
- [x] SUBMIT2-04: incorporate WGS owner native-code confirmation (ebf1f4b/9f4f359).
- [ ] Before implementation/release, verify actual production runner source binding.
- [ ] SUBMIT2-01: final-submit intent/gates and scoped cancelled-draft release.
- [ ] SUBMIT2-02: revisioned editing and frozen runtime input handoff.
- [ ] SUBMIT2-03: two-step frontend and focused BS10610 acceptance.
Implementation not authorized by this documentation-only request.

## TEST-VALIDATION-01 — closed as redundant

- [x] Accept existing release and production-publication evidence for work that
  was already developed, tested and deployed.
- [x] Do not create a branch-wide revalidation matrix or rerun the historical
  missing-`S1` test solely because completed history was synchronized into test.
- [x] Require each newly authorized development track to carry its own focused
  tests and BS10610 acceptance for the source it changes.

Revisit historical evidence only when a new change touches the same path, a
specific inconsistency blocks development, or the user requests a fresh audit.

## RUN-CONTROL-20260918 — design complete, implementation not started

Owner sequence: Workflow -> Backend -> Airflow -> Frontend -> QA/release owner.
Coordinate its execution-state and reconnect contract with `CCE-RECOVERY-01`;
do not build a second, conflicting recovery path.

- [x] Audit existing cancel/resume/Step7 behavior and document exact pause,
  same-attempt recovery and project-deletion semantics.
- [ ] `RC-01` — implement restricted runtime controls, exact ownership checks,
  quiescence evidence, checkpoint recovery and per-object cloud cleanup.
- [ ] `RC-02` — add the durable admin operation, cloud-first deletion journal,
  independent tombstone and scanner suppression fence.
- [ ] `RC-03` — add the dedicated control DAG and generation-fenced dispatch,
  callback and terminal-state handling.
- [ ] `RC-04` — add existing-page controls, destructive preview/confirmation,
  unsupported reasons and partial retry display.
- [ ] `RC-05` — run focused synthetic BS10610 acceptance after separate
  implementation and test authorization.

Spec: `docs/superpowers/specs/2026-09-18-run-control.md`. The task cards retain
their dependencies, exact acceptance, risks and rollback rules in that document.
No code, migration, remote validation, real task action or production activation
is authorized by the design or by this queue entry.

## WGS-QC-TWO-SOURCE-20260918 — design complete, implementation not started

Owner: Backend/QC projection first, then Frontend, with QA covering both.
This work is independent of CCE run control and may be developed separately.

- [x] Document required batch `QCstat.tsv` authority and conditional
  `multi.QCstat.tsv` WgsMetrics evidence for selected `F57J`/`UPC` samples.
- [ ] `QC2-01` — implement exact optional-artifact discovery and a separate
  rare-disease WgsMetrics projection, plus release-pinned applicability/judgment
  and synthetic fixtures.
- [ ] `QC2-02` — update the API contract and Run Detail QC presentation with
  default `常规临检` and conditional `罕见病` tags; each tag reads only its own
  batch-level source.
- [ ] `QC2-03` — verify ordinary-only, complete rare-disease and missing-
  supplemental-evidence cases without changing native QC, pending or DAG logic.

Spec: `docs/2026-09-18-wgs-qc-two-source-contract.md`. Same-named metrics from
the two sources must never overwrite, substitute for or silently validate one
another. No database migration, native workflow change or production publication
is part of the documented scope.

## WGS-CNVPLOT-20260918 — design complete, implementation not started

Owner sequence: Backend restricted file projection, then Frontend, then QA.

- [x] Confirm native per-sample `03_CNV/<sample_id>.CNV_genome.png` naming,
  image dimensions and bounded one-image-at-a-time display strategy.
- [ ] `CNV-01` — add WGS-only selected-sample list and controlled PNG streaming
  from the frozen bound result root; no generic file browser.
- [ ] `CNV-02` — add the WGS Run Detail `CNV plot` tab with left sample selector
  and one lazy-loaded right image pane.
- [ ] `CNV-03` — run synthetic authorization/availability and component tests;
  do not run or download a biological workflow.

Spec: `docs/2026-09-18-wgs-cnv-plot-viewer-design.md`. PNG remains the native
artifact; HTML/SVG redraw, eager batch preload, CNV interpretation and any
workflow/QC change are out of scope.

## CCE-RECOVERY-01 — scope expanded 2026-09-22, revised design awaiting review

Owner: Workflow for adapter/runtime behavior; Airflow/Backend for state
projection; Frontend only for shared stale/monitoring display.

- [x] Revise the design for user-approved0918A Worker creation disconnect and
  0919B Gatekeeper admission timeout; explicitly defer0919C missing-input repair.
- [x] Integrate the four-file document revision with current test-branch designs
  under explicit user submission approval; preserve QC and CNV work unchanged.
- [ ] Review revised policy defaults: at most two automatic same-attempt compute
  recoveries,60/180s waits, original deadline, persistent shared failure budget.
- [ ] CR-01: bind source-level query/Worker-create error evidence to execution
  identity; classify the two allowed causes and reject unknown/mixed failures.
- [ ] CR-02: single recovery decision owner, durable budget/action deduplication,
  user-stop fence and restart-safe accounting using existing records/transactions.
- [ ] CR-03: reuse adapter Resume with old Master/Worker quiescence checks,
  UID lineage and lost-response reconciliation; coordinate DAG/callback/lease
  fences and automatic downstream continuation; include uncertain Step4 dispatch.
- [ ] CR-04: shared Tracker/detail waiting, recovering, exhausted and stale
  evidence presentation without overwriting historical execution outcomes.
- [ ] CR-05: one focused synthetic BS10610 acceptance for changed paths, default-
  off/per-adapter activation and release/rollback record; no real analysis.

Spec:
`docs/superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md`.
Spec section8.1 maps CR-01–05 owners, dependencies and acceptance. Proposed
automatic Master replacement is limited to those two causes and all safety
guards; it is not an available capability or authorization to execute it now.
No missing-input repair, prepare/pending/config changes, whole-workflow retry,
Local/SGE, Step7, implementation, remote tests or production activation now.
Review the revised spec before the code-level execution plan/development.

## TEST-ACCEPTANCE-01 — operator-facing verification incomplete

Owner: QA/Frontend.

- [ ] Perform authenticated desktop/narrow no-flicker visual acceptance for the
  current test UI when browser access and a user session are available.
- [ ] Confirm current QC headings and exact rule filtering against deployed API
  values without changing QC policy during verification.
- [ ] Record browser evidence or a precise blocker. Component tests do not
  substitute for this unclaimed visual check.

## TEST-LINEAGE-SYNC-01 — complete

Owner: coordinator.

- [x] Record the 2026-09-18 main/test topology as inventory only.
- [x] Confirm no merge, rebase, cherry-pick or code port was performed during
  consolidation.
- [x] Port only the user-authorized fixes `e7f0373`, `cb1c3fe` and `347e4ed`,
  adapting the rule-filter query to retain the test branch SQL budget.
- [x] Validate the selective port in an isolated BS10610 candidate: backend
  focused suite 28 passed; frontend changed-scope suite 17 passed; production
  build passed.
- [x] Confirm the remaining full-frontend failure is already present at base
  `f0b07c4` (`starts stage one...` cannot find `S1`); keep it visible rather
  than attributing it to this sync.
- [x] Record the earlier hold and the later user-authorized policy change in
  `docs/TEST_BRANCH_SYNC_HOLD_20260918.md`.
- [x] Commit the three approved fix ports as `8f062f9`.
- [x] Commit the compact test state and repository hygiene record as `91060d0`.
- [x] Merge `origin/main=origin/jiucheng/release/production=1255a06` and prove
  both refs are ancestors of the resulting test tip.
- [x] Run focused backend/frontend/runtime tests on the merged source and push
  the test branch.
- [x] Integrate current `origin/main` and production `9b381eb` into test while
  preserving all test-only designs. `9ff67d3` and `9b381eb` are already released,
  completed work and require no follow-up development card.
- [x] Do not rerun sampleinfo/submission tests merely for this history sync;
  existing production acceptance remains authoritative.
- [ ] After all required testing completes, prepare a test-to-main promotion
  manifest with only validated commits and explicit omissions.
- [ ] Promote to `main` only after separate user approval and current main
  conflict review. Do not reverse-sync main as a test baseline.

## TEST-HYGIENE-01 — retire stale worktrees without losing current work

Owner: coordinator/operations.

- [x] Inventory both local Git common repositories, every registered worktree,
  dirty state and unique commits.
- [x] Remove ten worktrees; retain unique branches/bundles and patch-preserve
  state-only dirty documents before removing their worktree directories.
- [x] Delete fifteen local branches proven contained in `origin/main`; keep
  all remote branches unchanged.
- [x] Move six disk-only legacy directories and nineteen loose packages to the
  recoverable task-artifact archive instead of deleting them.
- [ ] Triage the eight retained dirty worktrees against current main and the
  primary test branch; preserve a patch/bundle before any later removal.
- [ ] Remove a retained dirty worktree only after its source-bearing changes
  have an explicit keep/archive/discard disposition. Never use force cleanup.

Inventory: `docs/REPOSITORY_HYGIENE_20260918.md`.

## Deferred and separately authorized

- Any test-to-main promotion or production deployment. This task only synchronized
  the already completed main/production history into test.
- Actual WGS/GATK task recovery, batch reset, rerun or new real analysis.
- BS96 production deployment, scanner/dispatch changes or database mutation.
- Cleanup of offline project/results/FASTQ/sampleinfo/pending/evidence data.

Full historical state:
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`.
