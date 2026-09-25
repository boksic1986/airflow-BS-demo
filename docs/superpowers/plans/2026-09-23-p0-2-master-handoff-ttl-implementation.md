# P0-2 Master handoff and TTL-safe recovery implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Preserve existing CR01 work; do not start a second recovery implementation.

**Goal:** Deliver authenticated manual WGS/GATK recovery across interrupted Master handoff and terminal Job reclamation, before completing automatic dispatch.

**Architecture:** Extend existing cce-pipeline handoff/terminal records, bs7 Worker inventory and Airflow Resume adapters. Producers persist identity-bound evidence before consumers use it; TTL cannot replace finality or ownership checks. Keep existing budget, actions, locks and generation fences.

**Tech Stack:** Python, shell Master entrypoint, Snakemake Kubernetes plugin, existing FastAPI/SQLAlchemy and Airflow DAGs.

**Spec:** [P0 section1.0](../specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md), [TTL companion](../../46_JOB_TTL_CROSS_MASTER_RECOVERY_DESIGN.md), source revisions a1af96a/729564c/781877e. P0-2E lock handoff is mandatory alongside TTL, not a later optional task.

## Global constraints

- Airflow branch `jiucheng/runtime/CR01-cce-recovery-20260922`, baseline e921e3a. Preserve original dirty operations workspace.
- Reuse plugin25297f9/bs7 and unchanged acceptance; no Snakemake core or Worker biological image changes.
- No production/main merge, BS96 access, cloud writes, real analysis, shared installation or automatic policy enablement.
- BS10610 isolated synthetic validation only; local Windows is editing/Git/docs only. If remote preflight fails, stop runtime validation, not substitute local tests.
- No prepare/pending/config/input changes, forceall, new service/DB table, historical bundle rewrite or bulk historical TTL patch.
- New Worker/Master/reader Job templates: spec.ttlSecondsAfterFinished=100. Activate only after evidence and compatible consumer acceptance. Master backoffLimit=0/restartPolicy=Never, original deadlines/resources unchanged.
- Manual recovery preserves analysis_id/attempt/workdir/release/config; automatic recovery remains off and keeps two shared60/180-second slots and original deadline.
- Unknown/contradictory evidence, active Workers, incomplete inventory, uncertain writes or foreign identity block replacement. User stop wins over undispatched recovery.
- AOM/alerts/capacity and live TTL checks are production acceptance gates requiring separate authorization, not code-test side effects.

## Baseline and ownership checkpoint

- [x] Verify clean isolated Airflow e921e3a and remote test design729564c.
- [x] Bring only new P0-2 priority section and TTL companion into CR01; preserve existing September23 quota/RPC coverage and implementation ledger.
- [x] Integrate781877e P0-2E: logical-run ownership, conditional generation takeover/release, TTL-independent lock lifetime and legacy lock-domain compatibility.
- [x] Verify authoritative cce-pipeline source before editing it. BS10610 remote source and local object both resolve83e7adbff9e94b99da34f687903cb4ee9df9f996; created independent `D:/pipeline/cce-pipeline-worktrees/p02-master-handoff-20260923`, branch `jiucheng/runtime/p02-master-handoff-20260923`. Earlier1462e9e snapshot superseded by this fresh check.
- [x] Read remote source instructions/HANDOFF, branch/status/remotes and prototype scope. `/mnt/biodevrwbi/33.chenjiucheng/project/worktrees/huawei-cloud-runtime-master-errors-20260923` has no AGENTS, clean tracked83e7adb, two untracked audit files (`scripts/cce_master_error_audit.py`, `tests/test_master_error_audit.py`). Preserved the source/prototype; informed operations owner of isolated scope.
- [x] Verify plugin25297f9 source status and establish isolated successor source5b5d7ee/0.6.4+bs8.dev1. No accepted bs7 bytes replaced. The later Task5 entry records fdf1520 and its built artifact pins.
- [x] Fresh BS10610 preflight succeeded: server10610, control/current/mount fingerprint recorded in HANDOFF; scanner and auto-dispatch false, task-specific candidate/evidence writable. Intermittent later SSH handshake failures did not trigger local-test fallback or service changes.

One writer owns each source worktree. This plan's coordinator owns Airflow changes; cross-repo ownership must be resolved before touching dirty producer code. No implicit delegation to another task.

## Review focus

1. START sent but confirmation missing: never report started or resend metadata after possible execution; Task1 tests lost response/restart.
2. Master disappears after TTL with stale or absent terminal: no inference from404; Task3 tests valid/absent/conflicting evidence.
3. Worker completes after Master death or while inventory is read: generation cannot stop writes; Task2/3 require complete inventory and dispatch-time recheck.
4. Old owner releases a same-directory lock after replacement: new generation must remain protected; Task2 tests conditional takeover/release against781877e, including lost update response and legacy/CLI lock domains.
5. Restored control process sees old terminal cache/action: preserve original deadline/action and existing callback fences; Task4 exercises actual adapter path, not only validator functions.

## Task1 — Master handoff confirmation and source terminal records

**Files (relative to verified cce-pipeline source):**
- Modify `src/cce_pipeline/assets/cce_batch_runtime.py`, `src/cce_pipeline/master_job.py`, `scripts/run_cce_master_job.sh`.
- Tests: affected cases in `tests/test_batch_runtime_boundaries.py`, `tests/test_master_run_mode.py`, `tests/test_analysis_complete_contract.py`.
- Airflow consumer follow-on: `scripts/wgs_resume.py::_finish_handoff`, `scripts/gatk_resume.py::resume` (after producer contract exists).

**Interfaces:** Reuse `_write_master_handoff`, `_read_master_handoff`, `_wait_pod`, `step2`, existing MASTER_HANDOFF and RUN_COMPLETE/RUN_FAILED records. Map existing names to run/attempt, execution generation, request/config digests, Master Job/Pod UID and original handoff deadline once. Do not create a second competing identity source. A Master record is process evidence; runtime still independently proves Kubernetes finality/Worker quiescence before recovery authorization.

- [x] Pin producer source and field mapping in cce-pipeline `docs/architecture/master-handoff-v2.md`. Schema2 declared by Master manifest/env; old bundles stay legacy. Compatible image/controller release remains Task5.
- [x] Add failing cases for START_SENT without confirmation, foreign UID/config/generation, partial metadata, lost START response and control restart retaining original deadline.

```python
# Add to the existing runtime fixture tests using the real step2/handoff path.
# Expected observations, not a new public API:
assert starts_after_lost_response == 1
assert replacement_jobs == 0
assert restarted_handoff_deadline == first_handoff_deadline
assert state_without_confirmation != "START_CONFIRMED"
```

- [x] Targeted behavioral RED recorded in the pinned BS10610 isolated container, followed by implementation. Synthetic shell fixture normalizes the baseline classifier CRLF before execution; fixture errors were not treated as behavioral RED.
- [x] Persist START intent before transmission. Master validates complete metadata and identity, writes atomic persistent START_CONFIRMED before Snakemake. Controller queries original UID and confirmation, retains original deadline, and records structured handoff_timeout without converting it to rule failure.
- [x] Extend existing terminal writer for normal success and catchable startup/execution failures. Install the writer only after trusted identity and atomic same-Pod process claim; earlier failures and SIGKILL/OOM remain unknown. Retain native success criteria, mark process evidence_complete=false; no Worker-finality seal invented.
- [x] BS10610 Task1 final GREEN:24 targeted cases. Includes review corrections: accept original on-time confirmation after controller restart/deadline, read durable evidence after Pod completion, and reject overlapping same-Pod entrypoint before config mutation/failure trap. Source/provenance committed on independent branches only; no image build/install or full recovery claim. Artifact acceptance remains Task5.

Task1 does not implement cross-Master lock takeover, Worker finality, missing-Job
recovery, unknown CREATE reconciliation or the Airflow Resume consumer. Those
remain Tasks2–4; TTL and automatic recovery are not activated.
Producer commit: `c33740dea3a94e8ee3633592aba1b111948171b3`.
Final affected legacy checks:18 passed /32 deselected; no full-suite rerun.

## Task2 — Worker terminal persistence, bounded query scope and directory ownership

**Files:** In verified bs7 source, extend existing executor Job status handling and submission recovery module (exact paths resolved from pinned25297f9 tree); in cce-pipeline extend existing `_claim_batch_lock` and its release/active-worker checks. No new lock service or per-Worker logger package.

**Interfaces:** `worker-terminal/<job_uid>.json`, schema_version1; run_id, attempt, execution_generation, master_uid, job_name, job_uid, submission_identity, terminal_state SUCCEEDED|FAILED, reason, observed_at. Submission identity must derive from the existing bs7 journal, not another random identifier. Existing ConfigMap lock identity binds canonical directory/pipeline/analysis_id/attempt; owner fields include generation/action/Master UID/config digest. Use resourceVersion-conditional updates with a durable handoff intent; never delete then recreate to take ownership. Map legacy keys before enabling so CLI and platform cannot acquire independent locks for one directory.

- [x] Write failing tests around actual executor terminal handling: persistence before success/failure callback, duplicate identical record, conflicting record, write failure,404 with/without exact record, restart retaining the admitted inventory.

```python
assert callback_before_atomic_terminal_write is False
assert result_for_404_without_terminal == "UNKNOWN"
assert confirmed_terminal_uid not in next_poll_uids
assert old_owner_release_removed_current_lock is False
```

- [x] RED remotely, then same-directory atomic/fsynced Worker publication and exact record replay.15 final cases GREEN. Verified per-poll journal view; cached callbacks before quota/control queries, retained conservative quota claims. Missing file/404 is unknown.
- [x] Extend original lock primitives with opt-in logical identity, generation/action owner, pending UID binding and verified quiescence callback; stale release rejects, no GC ownerReference. Actual trusted callback/consumer integration is Task3/4 and not enabled by these source helpers.
- [x] Synthetic CAS tests cover lost response/replay, one-winner contention, same-name/different-directory, shared-directory exclusion, unknown legacy mapping rejection, guard before directory key and downstream hold. Review added retained-intent and released-old-generation RED/GREEN. Final17 lock cases GREEN. No transfer/heavy budget or real-lock change.
- [x] Commit source5b5d7ee (plugin) /7926496 (cce-pipeline), plus5 +3 affected legacy tests. No full suite, new wheel/image, deployment or replacement bs7 bytes.

### Historical-run compatibility and activation boundary

User explicitly clarified that the five pending reruns are a compatibility
discussion, not operational authorization. Their frozen analysis_id/attempt,
release/config/workdir/history are retained. The future authenticated recovery
adapter maps old owner/directory using existing immutable inputs and journals,
proves old dispatcher/Master/Workers inactive, and conditionally fences the old
project/batch key with its original snapshot retained before acquiring a v2 key.
Then reserve generation+1 and bind the confirmed Master; do not prepare again,
rewrite bundles, forceall or delete old locks. Unknown/conflicting evidence blocks
only that recovery until verified, not automatic adoption of arbitrary history.

Old CLI cannot safely coexist with a directory-aware lock under arbitrary batch
keys. Activation therefore requires all same-directory CLI/platform and downstream
writers to use compatible wrappers. Guard markers reject old CLI same-key reuse,
but do not replace this paired-entry gate. Canonical storage mapping must be
verified on actual mounted storage, not guessed by the control host. Existing
v1 callers stay unchanged until that gate passes; no live migration performed.

Task2 accepts source primitives, not operational rerun closure. Task3 must wire
trusted mapping/inventory and existing serialized/fsynced recovery journal;
Task4 must exercise authenticated WGS/GATK plus protected downstream stage
claim/release paths without rewriting frozen files. Task5 cannot activate TTL
or artifacts before this legacy/all-writer matrix passes.

## Task3 — TTL-safe runtime reconciliation through existing Resume

2026-09-24 SOURCE ACCEPTED: capability6 GREEN; first adapter composition10 RED,
expanded29 GREEN;5 affected legacy checks GREEN. Prior guard/reader matrices
remain accepted below. Existing Resume journals now consume full final evidence,
Task2 lock CAS and separate next-generation handoff without mutating old inputs.
Scoped review closed all Important/Critical; HANDOFF lists exact logs and SSH
interruption. No service/DAG activation: authenticated callback construction and
propagation of returned view through stage monitoring/receipts are Task4.

2026-09-23 follow-up:27 new cases accepted on BS10610 (15 query/confirmation,
9 native success,3 terminal ambiguity), each RED then GREEN. Compatible query
and Task1 confirmation/native success connect to existing WGS/GATK entry points.
Full Task3 matrix below remains OPEN, not a completed Resume capability.

2026-09-24 approved dependencies accepted in isolated source: independent view6,
final plugin inventory/native reader/shell/review18, full live inventory10 new
BS10610 cases;5 affected checks. Producer/read-only consumer acceptance only;
existing Resume/lock side-effect wiring and final matrix still open.

Dependency found: `_bind_master_terminal` sets evidence_complete=false and does
not bind final submit journal/manifest; Master wrapper lacks plugin submit
context injection. V2 MASTER_HANDOFF refuses another UID in the frozen generation.
Blind consumption would delete the failed Master then fail handoff, or trust
non-final inventory. Guard now blocks that path BEFORE mutation. User approved
on2026-09-24 final inventory production and explicit derived next-generation
recovery view outside the original bundle, preserving history/config/input.
Complete live inventories + trusted storage/lock callbacks must consume those
records; this does not replace Task4 authenticated binding/all-writer closure.

2026-09-23 first safety checkpoint complete, Task3 remains open: unknown WGS
CREATE/404 replay and missing acknowledged replacement cannot POST again;
pre-delete exact UID/RV recheck, durable preserving journal; both adapters reject
incomplete Pod pages; archived GATK Worker NOT_FOUND without evidence blocks.
BS10610 RED6 failed/1 passed then GREEN7 new +13 affected legacy cases. Focused
review added delayed failed replacement RED1; fix and affected normal path GREEN2,
bringing new accepted cases to8. No important checkpoint review findings remain. This
does not cover the full matrix below; handoff/native terminal/evidence/lock
consumers remain outstanding. No full-suite rerun or production action.

**Files:** `scripts/wgs_resume.py`, `scripts/gatk_resume.py`, `scripts/cce_recovery_workloads.py`, `scripts/cce_recovery_inventory.py`, `scripts/wgs_runtime_gate.py`, `scripts/gatk_runtime_gate.py`; corresponding `scripts/tests/test_*` files. cce-pipeline structured query/terminal readers remain in their original runtime module.

**Interfaces:** Preserve `resume_master`, `fence_master_status`, GATK `resume` and recovery journal identity. Add optional verified evidence capability only for compatible runtime; no raw browser-provided terminal acceptance. Existing exact-name query, submit journal and UID/RV delete preconditions remain authoritative.

- [x] Test both adapters for live active Master, native successful terminal, allowed failed terminal, recycled Master with valid evidence,404 without evidence, foreign UID, surviving Pod, unknown Worker, incomplete page and lost CREATE response.

```python
assert active_master_result["mode"] == "reused"
assert create_count_after_successful_terminal == 0
assert create_count_after_unknown_404 == 0
assert create_count_after_replayed_action == 1
assert delete_options["preconditions"] == {"uid": old_uid, "resourceVersion": old_rv}
```

- [x] Run initial new cases RED (review expansion separate RED blocked by SSH, disclosed). Distinguish query transport/service errors,403,404 and invalid responses in source, retaining safe summaries; never map query failure to absent object.
- [x] Read full submission and live Job/Pod inventories, including pagination. For reclaimed Workers require exact persisted terminal evidence. Probe failure or incomplete inventory blocks replacement. Recheck immediately before side effects.
- [x] Reconcile existing journal states before creating/retransmitting. Unknown CREATE outcome must not turn a subsequent404 into permission to issue a new random request. Resume existing handoff using Task1 confirmation, never bare START existence.
- [x] Only a verified native success returns succeeded to downstream caller; failed evidence remains history. GREEN parameterized WGS/GATK cases, code/runtime contract. Authenticated stage routing remains Task4.

## Task4 — Authenticated manual adapter closure before automatic dispatch

**Accepted 2026-09-24: manual source/synthetic scope complete.** Native bd41f87,
plugin5b5d7ee (unchanged), platform commit containing this acceptance entry.
The checkpoints below are historical; their OPEN statements are superseded here.
At Task4 closure Tasks5/6 were unstarted; the later Task5 acceptance below now
supersedes that status. Deployment/automatic/live TTL gates remain closed.

Latest-design verification (not a new feature plan):

| Requirement | Implemented evidence / acceptance |
| --- | --- |
| Existing authenticated manual entry, same RunAction/attempt/config/workdir | Existing WGS/GATK services and real DAG methods; final manual flows2 passed; no prepare/upload rerun or forceall |
| Active Master reattach; initial interrupted handoff and CAS replay | Exact native journal/view/UID, original deadline, one CREATE/START; focused initial/direct/reconnect cases |
| Native success only, selected Master through normal downstream | Fresh-process Step3 and Step4–6 reconstruct native authority and normal predecessor receipts; both adapters pass |
| Old writers stopped and complete evidence before replace/release | Existing shared directory/dispatcher locks, sealed current and historical Worker inventories, full live lists; unknown/active/unbound objects block |
| Original producer distinct from new observer | Archived authenticated request and native binding revalidation, including actual WGS reattach worker; normal receipt digests retained |
| No earlier release during downstream / no old bundle mutation | Step6 materialized + native success + final quiescence + CAS release; RELEASED replay does not rewrite; frozen bundle byte assertions |
| No scope expansion or production activation | No new API/schema/retry engine, no Task5/6 changes, no images/CLI/policy install, main/production merge or real reruns |

One final review found three Important boundaries: interrupted initial handoff,
retained previous-generation Workers at final release, and WGS reattach receipt
authority. Five behavioral regressions reproduced RED; repaired. Final BS10610
selected41 passed/1 skip76.91s (GATK has no WGS-specific reattach worker), manual
authenticated flows2 passed41.32s. Review fix pass only; no repeated review/full
suite. Latest logs and limitations are in HANDOFF. This is Task4 acceptance, not
live scheduler/PostgreSQL/TTL/AOM or full automatic P0 acceptance.

2026-09-24 registered Step2 source checkpoint: trusted factory now reads existing
authenticated spool, verifies its adapter-specific hash, operator frozen binding,
physical directory and exact native old owner, excludes sibling dispatchers and
holds shared directory serialization through existing WGS/GATK Resume. Actual
Step2 writes verified binding receipt and repeated request reuses native journal.
BS10610 entry2 RED, real GATK request-shape1 RED; final14 GREEN13.78s and affected3
GREEN2.17s. No policy installation/activation. Step3 replacement remains fail-closed
until selected-view cross-process continuation is connected. Native Step3-6,
final protected release and full authenticated manual flow remain OPEN; no Task5/6.

2026-09-24 normal-receipt checkpoint: internal native-verified result now survives
both status writers and GATK terminal receipt hashing; WGS worker disconnect
preserves it. Caller JSON cannot mint authority, and a new observer does not
relabel the Master submit identity. Two RED, affected7 GREEN7.62s; final observer
refinement receipt2 GREEN3.51s on BS10610 offline. This is in-process forwarding
only. Trusted factory, actual GATK routing, cross-process selected-view/native
Step3-6 execution, final release and full manual flow remain OPEN. No Task5/6.

2026-09-24 checkpoint: user-approved existing cloud reader now resolves SFS
identity without a host mount; exact volume/Job/Pod fences and durable one-create
cleanup validated (cloud10 + protected-entry13 GREEN). Actual WGS/GATK stage
builders/Resume loaders select the paired operator runtime, and GATK custom
materialization preserves its output-root checks under the writer (new10 +3
affected GREEN). No activation policy installed. Per-run trusted registration,
selected-view receipts, recovery capability/final release and full manual flow
remain unchecked; these helper/entry checks do not open Tasks5/6.

2026-09-24 additional source checkpoint: GATK own registration/history, existing
adapter endpoint and DAG selection implemented; shared module contains only the
accepted durable dispatch/action fences.39 affected backend cases plus two new
HTTP/finalize cases passed, and one real-Airflow GATK DAG case passed. Shipped GATK
registry still lacks resume capability. Native end-to-end acceptance remains open.
User approved initial Master platform binding in isolated source, using an
independent submission view without modifying old bundles. Do not
equate native bundle request_hash with the platform stage request_hash. This is
not permission to advance TTL or automatic activation before the remaining gates.
Native initial-view/Step2 source now binds both identities through confirmation
and terminal evidence; existing WGS/GATK Resume propagates new platform identity
into the view/journal. BS10610 native41 and new adapter composition2 passed.
Trusted writer/storage/all-writer/downstream activation remains open.

2026-09-24 source checkpoint accepted: WGS authenticated dispatch/DagRun boundary.
Existing Resume now journals POST intent and reconciles exact DagRun identity;
all recovery registrations carry and validate actual DagRun ID and stage scope.
No new recovery engine or public endpoint. This is the first Task4 slice only:
GATK own-service/DAG routing, trusted native binding writer/canonical mapping,
paired all-writer activation/quiescence and selected-view downstream receipts
remain OPEN. Do not mark Task4 complete or advance Task5 TTL based on this slice.
BS10610 selected tests covered31 backend cases and3 real-Airflow DAG methods,
without full-suite repetition. Review found3 Important edges;5 new regression
cases RED, then those5 plus2 affected service checks GREEN. Scoped re-review
has no remaining Important/Critical. Full authenticated WGS/GATK/native mock
closure below remains unchecked; this checkpoint is not that acceptance.

**Files:** `backend/app/wgs_resume_service.py`, `backend/app/gatk_runtime_service.py`, existing adapter/route registrations in `backend/app/main.py`, `dags/bio_wgs.py`, `dags/bio_gatk.py`; `backend/app/cce_recovery_service.py` for trusted binding writer consumption. Update docs05/07/08 if behavior/contracts change; no new public API/table.

**Interfaces:** Existing authenticated recovery request -> same RunAction/idempotency key -> frozen stage execution/generation -> restricted runtime Resume -> normal stage receipt. Preserve `cce_master_binding` and `cce_master_submit_execution_id` semantics, populate only from validated runtime evidence, never arbitrary receipt JSON.

2026-09-24 additional checkpoints: native08c6cda selected-Master Step4/5/log export
keeps original output roots;10 focused checks passed. Actual WGS/GATK Resume
exports v2 binding from validated handoff with separate native/platform hashes;
6 affected checks passed. Backend/gate receipt forwarding is NOT yet closed.
CLI Step1–6 protected-entry compatibility scope was confirmed. Native8ec5415
adds protected stage/CLI entry, paired source pins, physical mapping, registered
frozen binding and shared journal serialization. New12/affected35/legacy3 checks
passed on BS10610. Actual gate registration, final release and all-writer rollout
proof remain pending; no policy or mount installed.
Tasks5/6 remain gated, no TTL/default CLI behavior enabled by these checkpoints.

2026-09-24 checkpoint: GATK restricted Step1–6 launcher/worker now has durable
intent and flock/PID identity fencing, including late receipt protection. BS10610
five RED then15 focused GREEN checks. No gate activation; storage/all-writer and
selected-view binding/downstream integration below remain open.

- [x] Add failing parameterized adapter tests using the actual service and existing DAG path. Cover repeat request, old terminal, success->downstream, current-attempt preservation, explicit legacy rejection and pending automatic/manual control exclusion.

```python
assert resumed_run.attempt == original_attempt
assert prepare_calls == upload_calls == 0
assert airflow_posts_for_replayed_action == 1
assert persisted_dag_id == confirmed_dag_id
```

- [x] Run RED on BS10610; route GATK via its own existing restricted runtime, not by removing the WGS pipeline guard and applying WGS internals unchanged.
- [x] Persist binding/generation/action before external dispatch; exact DagRun lost-response reconciliation. Keep automatic recovery disabled. This task ends at manual Step2/3 handoff/recovery and normal downstream continuation, not complete automatic P0.
- [x] GREEN affected service/DAG cases; one focused parameterized manual mock flow, no service deployment. Commit contracts and progress.

## Task5 — TTL generators and integrated artifact acceptance

Task5 source/offline artifacts accepted2026-09-24 after Task4 compatibility.
Exact pins, bounded tests, scope review and build caveats are recorded in
[Task5 provenance](../../releases/2026-09-24-p02-task5-offline-artifacts.md).
Production/live TTL gates remain closed; this is not automatic P0 completion.

**Files:** Plugin existing Worker Job generator; cce-pipeline `src/cce_pipeline/master_job.py` and Master template source used by it; Airflow `scripts/wgs_evidence_bridge.py::build_reader_job`. Preserve Step7/maintenance templates outside this scope.

**Interfaces:** Existing generators used by CLI, WGS/GATK and resume must generate Job.spec TTL, not Pod.spec TTL. Do not patch frozen generated bundles.

- [x] After Tasks1–4 consumer compatibility passes, add focused generator assertions to existing tests, including normal/resume entry paths.

```python
assert job["spec"]["ttlSecondsAfterFinished"] == 100
assert "ttlSecondsAfterFinished" not in job["spec"]["template"]["spec"]
assert master["spec"]["backoffLimit"] == 0
assert master["spec"]["template"]["spec"]["restartPolicy"] == "Never"
```

- [x] RED then modify only three generator families. Existing reader timeout/read-only mounts/active cleanup remain; TTL is fallback, not evidence acknowledgment.
- [x] Build distinct pinned test artifacts offline only after approved build environment/source ownership checks. Record producer commit, wheel SHA256, local Master image IDs (not registry manifest digests), cce-pipeline version and consumer commit. Never overwrite accepted artifact identities.
- [x] One affected mock matrix: TTL missing-object branches, actual producer records consumed by actual runtime/adapter, lost response and original deadline. Actual-wheel acceptance13 passed; no unaffected budget/callback suites. A mock cannot validate cloud TTL controllers.
- [x] Commit source/artifact provenance and Task5 scope review results. Whole-plan review follows Task6; production deployment remains separate.

## Task6 — Remaining P0 and separately authorized operational gates

- [x] Source preflight (2026-09-24): verify Task4 schema2 Master binding against
  the old flat automatic-reservation contract. Native FINAL seals submission
  inventory, not complete fatal-cause classification; the old
  `master-terminal.json` consumer has no corresponding runtime producer.
- [x] 2026-09-25 user approved the necessary existing Master wrapper/logger addition.
- [x] Complete the existing Master wrapper/logger fatal
  summary plus schema2 trusted-reader adaptation before actual automatic dispatch.
  Never invent zero mixed-rule/other failures or conflate platform/native identity.
  This is an identified prerequisite, not a reason to repeat Task4/5 acceptance.
  Accepted 2026-09-25: actual logger/native FINAL, schema2 selected monitor,
  immutable receipt and existing budget reservation; final focused28 GREEN.
  Native and platform IDs/hashes remain distinct, including observer-only reattach.
- [x] Internal due-dispatch service reuses existing reservation, adapter stage
  registration and shared durable Resume dispatch. Prepared crash rechecks proof;
  POST uncertainty is GET-only. Targeted23 GREEN on BS10610 (2026-09-25).
- [x] Freeze new-run per-adapter default-off policy/budget and initial Step3
  deadline; wire existing authenticated stage POST and existing Airflow sensors.
  Repeated/lost replies reuse one action; delegation skips the old chain.
  Exact current compute terminal lifecycle permits the second shared slot and
  current cleanup without releasing stale DagRun authority. BS10610 backend19
  GREEN4.70s and actual-Airflow5 GREEN3.00s (2026-09-25).
- [x] Consume the registered original deadline in native replacement and both
  Step3 monitors. Persist it in the recovery journal, cap handoff without reset,
  refuse further replacement/start after expiry, preserve untagged manual ABI.
  BS10610 focused22 GREEN16.25s (2026-09-25). Controller deadline only: no kill,
  Job native-deadline mutation, Task5 artifact rebuild or production activation.
- [x] Bounded same-owner Worker natural wait in the existing Airflow action:
  immutable start/deadline (min600s/original deadline), current-monitor challenge,
  fixed read-only restricted probe and exact FINAL/producer revalidation. One
  action/slot across retries; no kill, receipt rewrite, new scheduler or public API.
  Native replacement keeps strict fresh quiescence. BS10610 final17+2+4 targeted
  cases GREEN (2026-09-25). Reclaimed-without-proof stays blocked; no activation.
- [x] Exact CREATE source classes (2026-09-25): storage RPC Unavailable/peer-reset
  Status500 and mutation Gatekeeper context-deadline. RPC reconciles original Job
  before retry; UNKNOWN stops. Inventory/backend require typed CREATE evidence,
  ABSENT and existing fatal-cause/terminal gates. Existing budgets/default-off
  policy unchanged. BS10610 source/consumer30 plus actual FINAL/reservation2 GREEN.
  Source only; Task5 frozen artifacts not rebuilt or activated.
- [x] Continue CR-02/03 actual automatic dispatch using existing reservations,
  two shared slots60/180s, control fences and Step4 uncertain-dispatch reconciliation.
  2026-09-25 Step4 producer/budget checkpoint accepted64 targeted BS10610 cases:
  fixed original-operation probe, guarded WGS ambiguous spawn and separate
  persistent sequence0/1/2 in existing RunAction; fresh post-delay evidence,
  in-flight/stop/expiry/stale/started-once fences, original deadline preserved.
  Superseded by 2026-09-25 caller checkpoint: existing registration/runner/sensor
  now wired with frozen marker/deadline, committed intents and hash-pinned sends.
  BS10610 backend/runtime90 and actual-Airflow20 pass. No enabled deployment.
  Superseded by 2026-09-25 lifecycle acceptance: WGS/GATK automatic and manual
  cases4 pass through actual fatal evidence, durable dispatch, DAG registration,
  restricted replacement, reclaimed-Master monitor, Step4–6 and normal finalize.
  HTTP/SSH/cloud transports remain synthetic. Final review completed; the one
  Important native terminal conflict is fixed in1bc67fd, affected13 pass.
- [x] CR-04 reuses existing Tracker/detail waiting/recovering/exhausted/stale fields; no new page.
  2026-09-25 projection checkpoint: common read-only action/current-generation
  view and existing UI connected; running binding/health retained by real WGS/GATK
  consumers. Pending display freezes measured progress/estimates; exact Master
  proof required for recovering, completed log-health warning retained.
  BS10610 backend26/frontend13/build GREEN. Finite-reconnect producer-to-UI
  distinction remains for final integration; do not claim a retry from degraded
  health alone. No new business status, page, control or policy activation.
  2026-09-25 query prerequisite: internal typed GET budget core (max6 bounded
  retries with durable JSON callbacks, original deadline/identity and crash
  reservation fences); native exact ConfigMap ABI and error/timeout fix.
  BS10610 native24/platform17 GREEN0.79s. Not yet wired to monitor producers;
  next integrate under current worker identity, preserve status through outer
  failure handlers, then distinguish monitor/controller failure in backend/UI.
  Do not mark CR-04 closed or add retries around mutation/whole-stage calls.
  Superseded by producer/consumer wiring checkpoint (2026-09-25): selected native
  GETs share one existing-stage-JSON owner, with before-retry fsync and scope/status
  fences. Outer failure status preserves marker; real ingestion, read-only view,
  callback and periodic DagRun projection distinguish monitor from analysis.
  Native fd43f88; BS10610 regression113 plus final affected16/selected4 pass.
  No new controls/statuses; verify manual reconnect versus pending automatic
  action and full lifecycle in final integration before closing CR-04.
- [x] CR-05 focused PostgreSQL contention: disposable BS10610 PostgreSQL10 pass,
  actual pg_stat_activity lock waits prove serialization. Automatic/manual
  WGS/GATK lifecycle4 pass (94.49s), no real biological analysis or activation.
  Full-plan final review remains a separate source closure gate.
- [x] Manual/automatic observer handoff checkpoint (2026-09-25): query-only
  monitor failure never settles compute; existing explicit Step3 Resume retires
  only exact confirmed ended observer authority and commits its successor under
  the run lock. Pending/uncertain/active/foreign/stopped gates remain. Repeated
  keys/clicks reuse one action; same attempt/budget/deadline and old failed history
  retained. GATK manual deadline inheritance repaired. Existing detail panel
  serves query attention, no new page/endpoint. BS10610 backend82/frontend2 pass;
  source only. PG contention/full automatic lifecycle/final review remain OPEN.
  Superseded by final source acceptance2026-09-25: PG10, lifecycle4 and final
  review correction13 pass. No unresolved Critical/Important source finding;
  operational gates below remain open and are not replaced by mock evidence.
- [x] One whole-plan fresh review and one bounded fix pass: reject contradictory
  live/persistent selected terminal states, behavioral RED2 -> affected GREEN13.
  Native1bc67fd, platform runtime6f03dd6, plugin81132cf. No second reviewer or
  redundant unaffected suite. Declined-to-judge rulings recorded in HANDOFF.
- [ ] Separate production authorization: real synthetic Complete/Failed TTL checks, all-entry Pod capacity accounting, AOM data freshness and alert notification record. Missing evidence keeps production gate closed; no invented managed metrics or self-hosted monitoring service.

## Progress / current status

2026-09-25 coordination: source closure, historical Task5 artifacts, final-artifact
handoff and live gates are tracked separately in the
[current total ledger](2026-09-22-p0-joint-recovery-progress.md).
Successor wheel/Master work belongs to corresponding repository agents. After
documentation checkpointcbb74e7, items2/3 were dispatched to the plugin/native
owners. Final plugin/native/Master candidates accepted with exact provenance;
TTL3 and corrected final-image terminal6 checks plus two image smokes passed.
Earlier skipped coverage/import failure retained; no rebuild or broad rerun.
Read-only operational preflight is partial; live gates remain open. Exact status:
[candidate record](../../releases/2026-09-25-p0-final-candidates.md).
No install or cloud/service change is implied. Permission or environment
failures must be reported, never bypassed with another Docker/Compose invocation.

2026-09-25 current checkpoint: platform6f03dd6 / native1bc67fd / plugin81132cf.
Tasks1–5 retain their accepted scope. Task6 automatic/manual lifecycle4,
PostgreSQL contention10 and selected-monitor deadline/owner denial4 have passed
on BS10610. Final fresh review found one Important terminal-conflict issue,
fixed native1bc67fd with behavioral RED2 and affected GREEN13. Source closure is
complete; no second review or broad rerun. Older "next" notes below are
historical. Task5 artifacts pin earlier source and do not contain Task6 additions;
they must not be presented as final P0 release artifacts. Live TTL, capacity and
AOM/alert acceptance remain separately authorized operational gates.

2026-09-24: Tasks1–5 accepted in isolated source with bounded BS10610 synthetic
and offline artifact evidence. Current acceptance supersedes prior interrupted/
partial entries. Task6 source preflight is complete; implementation awaits the
bounded producer-scope confirmation recorded in HANDOFF. Superseded 2026-09-25:
user approved “补齐，然后继续”; prerequisite implementation is underway, no
new permission needed for that bounded addition. No production activation; retain all
branches/evidence. Next is Task6, not a repeat of Task4/5 or a full P0 claim.

### Historical initial interruption

2026-09-23: plan written after user explicitly requested planning and implementation.
Design integration including781877e completed; executable Tasks1–6 remain open. Two bounded remote preflight attempts
returned SSH exit1: kex_exchange_identification connection reset at172.17.61.18;
no hostname/mount validation or tests ran. Source ownership question sent to
existing operations task, which supplied an earlier dirty prototype snapshot,
not current authoritative verification. No local test substitution or producer
edits. Resume at baseline source/preflight gates, then Task1 RED, not at TTL.

Rollback before deployment is source revert only; never delete history, data or
evidence. After TTL activation, old objects cannot be recovered by reverting code;
compatible evidence readers must remain available.
