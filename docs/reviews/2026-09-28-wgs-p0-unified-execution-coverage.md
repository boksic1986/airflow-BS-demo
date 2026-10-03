# WGS incidents / P0 / unified execution coverage review

Date: 2026-09-28. Scope: source and document review, not implementation or deployment.

Latest coordination: user has now assigned Airflow/native implementation with
a preceding GATK-PROD-COMPAT gate; native target is release0.8.9. Follow the
current plan's owners/review gates. Findings below remain audit evidence, not
claims that a compatibility patch, UE implementation or deployment is complete.
The limited GATK gate has since closed without patch because the deployed gate
does not select the affected paired paths. UE-01 is authorized/in progress;
the findings and later-stage acceptance below remain open, not newly retested.

Subsequent documentation update (2026-09-28): the user approved incorporating
R1–R4 into the linked design and implementation queue. Spec3.3/3.4/4.1/5 and
UE-03/04/05 now name the consumers and minimal acceptance assertions; UE-06
requires matched evidence. This closes the documentation gap only. Source defects
and runtime acceptance remain pending; the original review below is preserved.

## Conclusion and evidence boundary

The [unified executor design](../superpowers/specs/2026-09-28-unified-stage-execution-design.md)
can address the main execution-contract failures without rewriting biological
rules or restarting completed work. It is not yet a complete repair: UE-01–06 are
pending, two platform defects remain visible, and the implementation plan needs
explicit consumer/acceptance coverage described below. Making stages asynchronous
alone does not repair evidence ingestion, controller lifecycle or workload queries.

Reviewed local branch `jiucheng/test/wgs-local-main-sync-20260917`, HEAD
`257931c9b6cb157f7de29c45b0b73a30b0a85dfa`, including existing uncommitted fixes.
The native probe assessment uses the previous installed-0.8.8 inspection recorded
in HANDOFF; native repositories, current installations and production were not
freshly checked in this review. No SSH, database access, tests, retries or mutations
of a batch were performed. Test results elsewhere are historical, not new evidence.

The latest recorded outcome for `WGS_20260927_141652_146B51`, attempt1,
`20260919A-test`, is success at 2026-09-28 05:16:10Z. Step3 completed275/275;
Step5 verified14/14 files; Step6 generation4 and final Airflow tasks succeeded.
This demonstrates that repaired paths completed that batch, not that all P0 fault
scenarios, GATK or the proposed executor have been accepted.

## Incident-to-plan coverage

| Issue and present evidence | P0 impact | Ownership / planned coverage |
| --- | --- | --- |
| Step1 digest counted a later envelope field; runtime request/control roots were confused. Existing platform corrections are present. | Valid work rejected before execution or recovery. | UE-01 producer/consumer contract; keep exact legacy hash rules and canonical control identity. Do not relax validation or rewrite old requests. |
| Upload resume routed a first-ever Master submission into replacement; native/platform CREATE deadlines differed. Bounded initial-submit and original-intent deadline corrections are present. | Step2 blocked after successful upload; ambiguous CREATE must not produce another Master. | UE-01/02/04 preserve initial intent, idempotency and original deadline; distinguish never submitted, uncertain submission and confirmed old Master. |
| Recovery Step2 success can exist on the node but not in the platform predecessor row. Source omission remains. | Step3 registration fails even though startup succeeded. | UE-04 must include predecessor ingestion, not only waiting for native START. See R1. |
| Step3 query reconnect had depended on automatic replacement opt-in; progress overwrites lost Master identity. Existing corrections are present. | A read failure becomes apparent compute failure; rule progress disappears. | UE-01/04/05 retain independent observation deadline, identity and progress projection. Never restart computation just because a query failed. |
| Step4 was blocked by historical queued manual actions and retired-generation sidecars. Bounded Step4 fixes exist. | Completed compute cannot publish; newer request can be confused with older execution. | UE-05 common identity/old-generation handling; retain legacy reader. Step4 fix does not close R2. |
| Native directory probe used one30s kubectl exec; transient failure stopped Step4/6. Previously inspected native path has no bounded retry. | Infrastructure read error aborts a writing stage before it can safely proceed. | UE-03 native read-only bounded retry, same UID/storage and original time budget. Not an Airflow-only fix. |
| Step6 final release required async worker metadata from synchronous WGS Step2/6. Existing legacy evidence check fixed this batch. | Materialization can finish but finalization still fails. | UE-02/04/05 shared executor for new executions; retain authenticated synchronous terminal reader for old ones. Do not fabricate worker.json. |
| Step6 queried each of275 reclaimed Workers and exhausted120s. Current bulk optimization opts in only for successful WGS final release. | Same scaling issue remains possible during Step3 failure recovery or GATK final release. | UE-03 common native query interface and all consumers; see R3. Do not widen timeouts or infer empty inventory from failed queries. |
| Run Tracker used the recovery entry stage over live progress; WGS release-specific rule/phase mappings were incomplete. Platform fixes exist. | Frontend can show completed startup rather than active rules, or Unknown phase. | Preserve platform timing/phase changes; UE-04 receipt compatibility check. These mappings do not belong in cce-pipeline. |

## Required implementation / acceptance clarifications

These fit the existing six tasks; this review does not authorize code changes or
add another feature stream. [Implementation queue](../superpowers/plans/2026-09-28-unified-stage-execution.md).

### R1 — Current defect: recovery registration bypasses predecessor ingestion

`backend/app/main.py:2150` returns through `register_recovery_stage` before the
normal `step3_monitor` branch at2616 calls `sync_runtime_stage_artifacts` for
Step2. `backend/app/wgs_resume_service.py:29` does not perform that ingestion;
`wgs_stage_execution_service.py` requires a successful predecessor row/receipt hash.
HANDOFF records the operational workaround of reading stage status before retrying
the existing downstream task. That is not a permanent source fix.

UE-04 should name the existing registration/ingestion consumer in its file map.
The common Step2 await must produce platform-visible, identity-matched predecessor
success before Step3 registration, including manual/automatic recovery. Reuse the
existing ingestion service; account for session refresh/transaction boundaries.
Do not rely on frontend polling, synthesize success or mint a replacement generation
to solve delayed receipt ingestion.

Minimal assertion: real Step2 success receipt with stale DB predecessor permits
the same authorized Step3 registration after ingestion; absent/wrong-generation
receipt still refuses. Parameterize normal/recovery paths rather than duplicate suites.

### R2 — Current P2: manual queued action can block Step3 automatic recovery

`backend/app/cce_recovery_budget.py:176` treats a nonterminal manual control action
as active. `cce_recovery_poll.py:22` selects only automatic `cce_compute_recovery`
actions; its compute-terminal reconciliation does not finish a manual Resume's
in-flight role. The Step4-specific correction in `cce_publish_recovery.py:42`
does not change Step3 reservation behavior. This remains F4 of the
[previous audit](2026-09-27-p0-step3-recovery-audit.md).

UE-05 needs `cce_recovery_budget.py` and `cce_recovery_poll.py` in the consumer map.
Separate dispatch status, computation terminal evidence and downstream authorization.
Only authoritative terminal evidence for the exact current execution may retire
the in-flight fence; preserve action authority for permitted downstream work and
preserve attempt budget. Do not globally mark queued actions successful or remove
mutual exclusion.

Minimal assertion: manual resume followed by a qualifying authoritative Step3
failure can reserve one permitted recovery; uncertain dispatch, active computation,
wrong generation and pause/delete requests remain fenced.

### R3 — Incomplete current fix: bulk queries must cover failure consumers too

`scripts/cce_paired_runtime.py:1248` enables bulk inventory only for WGS success.
`cce_recovery_inventory.py:504` and `cce_recovery_failure.py:89` still use the
default per-Worker path. `probe_bound_workloads` also needs its exact Master/Pod
diagnostics preserved when its query strategy is changed. The current platform
namespace-list helper calls private native `_run/_kubectl`; the planned native
query interface should replace that bypass.

UE-03 already specifies success, failure and active-wait coverage, but its file
map must explicitly include the failure collector and bound-workload consumer.
Use the same complete-list index for WGS/GATK recovery/final release, with fresh
proof at CAS boundaries. Retain UID/owner checks, bounded bytes/time, partial-query
rejection and live-worker waiting. Do not reuse a stale pre-CAS observation.

Minimal assertion: existing275-Worker fixture parameterized across success,
failure/replacement and active-wait entry points; query count does not grow per
Worker, while active/unknown resources never authorize replacement or release.

### R4 — Migration risk: unknown observation must be fenced for all stages

Current `cce_recovery_budget.py:33` has an explicit unconfirmed-observation guard
only for Step3; `require_current_dag_cleanup` also consumes that guard. New shared
Step1–6 snapshots introduce the same unknown-vs-failed distinction elsewhere.
This is a migration review requirement, not evidence that a current production
lease was released incorrectly.

UE-04/05 must check failure callbacks, stage projection and cleanup consumers for
all six stages. An observer timeout is not a business failure or proof that cloud
writers stopped. Conversely, an exact authoritative stage failure must still be
shown as failed. Unknown must retain the necessary execution/lease fences without
inventing indefinite business success.

Reuse parameterized consumer tests for unknown, terminal failure and superseded
identity; explicitly assert no premature lease release or replacement dispatch.

## Compatibility requirements not to lose during convergence

- Preserve current normal Step2 START_CONFIRMED handshake, WGS pool occupancy,
  transfer leases, Step6 completion requirements and native stage business order.
- Preserve attempt, config/output checkpoints, original deadline, budget, CAS,
  UID/generation and immutable evidence. No forceall or budget refresh on polling.
- Historical missing policy/deadline is not permission to enable recovery. Current
  policy/poll/evidence consumers contain WGS/GATK-specific selection; UE-05's third
  synthetic adapter claim must include these consumers, or be explicitly limited
  to executor reuse. Do not turn unsupported adapters into implicitly enabled P0.
- Pre-START replacement currently has a narrow WGS Step2 generation1 path with
  exact failed/reclaimed Master proof. Do not advertise it as arbitrary GATK or
  START_SENT recovery; capabilities and ambiguous-start rejection must be explicit.
- Keep production progress/phase fixes: nested Master identity, current stage and
  rule counts must survive the new snapshot projection; release-specific phase
  mappings stay in the platform. Reuse existing focused timing/phase assertions.
- Keep legacy synchronous evidence readers for frozen old runs. No active-run
  migration, request rehashing or fabricated asynchronous process metadata.
- Keep approved WGS output modes2775/0664/0775 and existing service identities;
  shared execution must not introduce root ownership or private0600 output modes.
  Private credentials/control files retain their separate restrictions.

## Previous Step3 errors and limits of the repair

Current evidence consumer explicitly recognizes Worker CREATE transport errors
(0918A), Gatekeeper admission timeout (0919B), CREATE storage RPC unavailable
(0921D), and exact HeavySlot/Worker-Pod read API unavailability (0921B/C/E).
These remain conditional on frozen opt-in, budget/deadline, matching durable
terminal evidence and reconciled writers. Read-only monitoring disconnection is
handled separately from replacement. R1–R3 can otherwise prevent permitted
recovery from completing even when the error category is already recognized.

BackoffLimitExceeded alone is not a recoverable cause. OOM/SIGKILL, uncertain START,
or a TTL-reclaimed Job with missing durable terminal/worker evidence is not made
safe by the shared executor. Missing FASTQ, checksum/config/permission errors and
biological rule failures still require correction before controlled resume.
PVC loss is a storage repair, not a retry category. Do not automatically recreate
storage bindings or reinterpret NotFound as success.

Keep TTL100 as proposed: terminal evidence must not depend on the old Pod staying
alive. Extending Master retention would only widen diagnostics; it does not repair
the contracts above. Real pause/delete/recreate controls and full cloud acceptance
remain outside this implementation queue's synthetic/interface acceptance.

## Validation and next step

Read-only source searches, diffs and incident records only. Local diff/new-file
whitespace checks passed and all3 document links resolve; no local or remote
runtime tests were run.
Before implementing UE-01, incorporate R1–R4 into the existing file map and minimal
acceptance cases. Then follow UE-01–06 in order with the original native/platform
ownership split. The current review must not be reported as a deployed fix or as
proof that every historical failure will automatically recover.

## Subsequent proportionality review — tests and validation

Historical review below; its recommendations were subsequently applied to the
design/plan under the user's narrower scope, as recorded at the end of this file.
User requested a document review, not another implementation or test run.
The design/plan were read against existing consumer and synthetic test source.
Recommendations below are not yet edits to the approved design/plan, and do not
claim that redundant tests have actually been executed.

### Findings / recommended narrowing

1. **Validation scope wording is too broad.** Spec section5 says unknown objects
   reject, while the query includes the entire namespace. Restrict that rejection
   to objects claiming this run or conflicting with bound names/UIDs/owners;
   unrelated workloads must not block the batch. Existing
   `test_present_terminal_worker_and_unrelated_workload` already asserts this.
   The same section's required Master Pod diagnostics must not mean a live old
   Pod is required after TTL. Persisted, bound, sufficient failure evidence is
   valid; missing required evidence still blocks. Existing
   `test_final_inventory_reconciles_live_or_reclaimed_terminal_work` covers the
   reclaimed case. Clarify the wording rather than add new permission bypasses.

2. **UE-06 can be read as repeating UE-04/05.** Plan line69 says not to rerun
   unchanged checks, but the UE-06 six-stage synthetic-chain item at211 can be
   read as another complete acceptance round. Reuse matched UE-04/05 evidence;
   UE-06 should check the installed candidate/pins/entry-point wiring and only
   uncovered or changed boundaries. Native source and built/installed artifact
   checks are different boundaries, but a second full fault matrix is not needed.

3. **Successful predecessor fast path is unspecified.** Spec3.3 requires the
   ingestion process for every registration without distinguishing an already
   verified exact predecessor from stale/missing state. Recommend using an
   already verified, current identity-bound receipt directly; ingest when it is
   absent/stale, then refresh under the registration lock. Keep that final
   recheck to prevent stale authorization. Do not turn this into repeated remote
   cloud checks or recalculate historical request hashes. This is a recommended
   trigger clarification, not a confirmed additional runtime defect.

4. **Test selection has limited room for reduction, not grounds to discard P0
   guards.** The Phase command runs all releases including unchanged4.2.0/4.2.1
   rejection cases; select the affected4.2.2 projection/isolation checks when
   phase policy itself has not changed. Small whole-file tests are not inherently
   excessive: the manual/automatic flow files each have one two-pipeline test,
   and cleanup tests exercise materially changed fences. Keep these when affected.
   Do not build pipeline x stage x recovery-mode x fault cartesian products.
   Third synthetic adapter/control-hook checks can share one small fixture;
   actual pause/resume checkpoint fault testing stays with the separate RC work.

### Necessary checks / not redundant

- Request authentication and frozen scope checks at entry, followed by current
  identity recheck after ingestion or immediately before CAS: these protect
  different trust/time boundaries, not duplicated assertions to remove.
- attempt/generation/UID/hash matching, idempotent dispatch, current-action budget
  and deadline, complete predecessor/terminal evidence, active-writer exclusion.
- State projection and external cleanup tests for unknown: one checks what the
  user sees, the other prevents unsafe release. Reuse parameterized data, but
  retain both distinct assertions.
- The275-Worker case is in-memory synthetic data to catch linear query growth,
  not275 cloud Jobs; fake query clocks must avoid real120s/30s waits. Keep the
  native probe's bounded retry and exact UID checks; do not remove them as noise.

Suggested validation placement: parse/verify immutable registered content at its
trust boundary; use the validated reference within that operation. Recheck mutable
ownership/live-work facts when authorizing a write, takeover or release. Ordinary
progress observation should not acquire a new full-cloud-inventory or helper-Job
requirement. This clarifies when checks run, without permitting stale CAS proof.

Review validation: local source/document reads only; no pytest collection or
runtime execution, no SSH, no native install, no cloud resources, no design/code
change. No test-duration or percentage-reduction claim can be made from this review.

## Applied scope correction — user confirmed, documentation only

The current design/plan now supersede the earlier legacy-reader and symmetric
WGS/GATK migration proposals. Reuse GATK's proven async dispatcher, retain its
submit/wait DAG and business handlers, and focus changes on WGS Step2/6 plus
current P0 defects. GATK changes are limited to shared-function extraction and
necessary thin bindings; larger semantic changes must be reported first.
Retired Resume/old synchronous execution compatibility and replay tests are
excluded. Current P0 same-attempt stage resume is not removed. Historical
records/evidence remain untouched; active incompatible execution blocks a
future cutover instead of requiring a newly developed compatibility layer.

All four review corrections are applied: reuse accepted results and remove the
second UE-06 chain; scope unknown-object rejection to this run/conflicting bound
identity and allow sufficient durable proof after TTL; reuse verified current
predecessors with ingestion only for missing/stale state and a final locked
recheck; select uncovered directly changed assertions instead of historical
phase/full P0 suites or cartesian matrices. Accepted project evidence remains
valid across unrelated source/SHA changes. UE-06 checks artifact/pin/entry wiring,
not another full fault campaign. Future control handlers, their new test suite,
CLI redesign and third-adapter demonstration are also outside this iteration.

Implementation UE-01–06 remains pending. This records document changes only,
not a source repair, new runtime verification, installation or deployment.

## Step2 decision reassessed — minimal change is not immutability

The user clarified that minimizing simultaneous rewrites must not forbid necessary
GATK Step2 changes. The previous "GATK DAG defaults to unchanged" restriction was
too strong and has been removed from the current spec/plan. Read-only source
inspection found GATK's split submit/reschedule-wait graph and WGS's single Step2
runner with wgs_cce_runs pool. GATK run_stage still treats SSH nonzero as an error
and returns accepted on zero rather than consuming the proposed shared snapshot;
this is a contract-integration gap, not a newly observed production incident.

Spec3.2 now compares both-inline-wait, both-split-wait and shared lifecycle with
thin scheduling wrappers. Recommend the third: no extra blocking wait for GATK,
no new cross-task startup quota system for WGS, but BOTH callable paths use a
common dispatch/observe/identity/uncertainty client. WGS's inline wait reuses that
client and must not own a second lifecycle/retry policy. Its existing worker-slot
cost is acknowledged, not declared optimal forever. Necessary GATK callable/Step2
changes are included in UE-04; a local graph change is allowed when a concrete
control defect warrants it. Unchanged business handlers remain outside the rewrite.

Future controls attach to durable execution identity, current arbitration,
actual local/cloud workload quiescence and checkpoint evidence, never task names.
Shared async dispatch alone does not guarantee recovery of every historical error;
R1–R4/native probe/query corrections and current policy/evidence boundaries remain.
No runtime tests, installed code verification, production action or source edits.
