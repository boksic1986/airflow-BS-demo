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
- [x] Verify plugin25297f9 source status and establish isolated successor source5b5d7ee/0.6.4+bs8.dev1. No accepted bs7 bytes replaced. Wheel/image build and artifact provenance remain Task5, not yet performed.
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
Task5/6 remain unstarted and deployment/automatic/TTL gates remain closed.

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

Task4 manual source dependency accepted 2026-09-24 as recorded above. Task5 is
the next planned task, not implemented or activated by this Task4 closure. The
separate build-environment/source-ownership and production gates still apply.

**Files:** Plugin existing Worker Job generator; cce-pipeline `src/cce_pipeline/master_job.py` and Master template source used by it; Airflow `scripts/wgs_evidence_bridge.py::build_reader_job`. Preserve Step7/maintenance templates outside this scope.

**Interfaces:** Existing generators used by CLI, WGS/GATK and resume must generate Job.spec TTL, not Pod.spec TTL. Do not patch frozen generated bundles.

- [ ] After Tasks1–4 consumer compatibility passes, add focused generator assertions to existing tests, including normal/resume entry paths.

```python
assert job["spec"]["ttlSecondsAfterFinished"] == 100
assert "ttlSecondsAfterFinished" not in job["spec"]["template"]["spec"]
assert master["spec"]["backoffLimit"] == 0
assert master["spec"]["template"]["spec"]["restartPolicy"] == "Never"
```

- [ ] RED then modify only three generator families. Existing reader timeout/read-only mounts/active cleanup remain; TTL is fallback, not evidence acknowledgment.
- [ ] Build distinct pinned test artifacts offline only after approved build environment/source ownership checks. Record producer commit, wheel SHA256, Master digest, cce-pipeline version and consumer commit. Never overwrite accepted artifact identities.
- [ ] One affected mock matrix: TTL missing-object branches, actual producer records consumed by actual runtime/adapter, lost response and original deadline. Do not rerun unaffected budget/callback suites. A mock cannot validate cloud TTL controllers.
- [ ] Commit source/artifact provenance and final review results. Production deployment remains separate.

## Task6 — Remaining P0 and separately authorized operational gates

- [ ] Continue CR-02/03 actual automatic dispatch using existing reservations, two shared slots60/180s, original deadline, control fences and Step4 uncertain-dispatch reconciliation. Do not count manual P0-2 closure as automatic completion.
- [ ] CR-04 reuses existing Tracker/detail waiting/recovering/exhausted/stale fields; no new page.
- [ ] CR-05 focused PostgreSQL contention and final integration tests, no real biological analysis. Respect WGS/GATK per-adapter enablement.
- [ ] Separate production authorization: real synthetic Complete/Failed TTL checks, all-entry Pod capacity accounting, AOM data freshness and alert notification record. Missing evidence keeps production gate closed; no invented managed metrics or self-hosted monitoring service.

## Progress / current status

2026-09-24: Tasks1–4 accepted in isolated source with bounded BS10610 synthetic
evidence. Task4 acceptance above supersedes prior interrupted/partial entries.
Tasks5/6 remain unstarted. No production activation; retain all source branches
and evidence. Next is Task5, not a repeat of the Task4 helpers or full P0 claim.

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
