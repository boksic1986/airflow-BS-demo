# UE-05 source handoff cross-consumer review

Date: 2026-09-30. Current verdict: **UE05 source/scoped acceptance complete;
two findings closed, AF03bab6c/native7172573 final pairing confirmed**.
No UE06, merge, installation or production activation follows this acceptance.

## Correction and evidence closeout

Correction commit: `03bab6c768a2c84537ee4e4a6189072256841b63`, based on
`a9a326d`. Nine paths only: two existing consumers, two existing fixtures,
docs05/08 and three state documents. Coordinator reviewed that correction delta,
not a second full audit; the original findings below remain as historical evidence.

- Important1 closed: entry stage/generation remains distinct from the actual
  Step3 registration; frozen request, predecessor lineage, action and native
  terminal are bound together. The existing WGS parameter exercises the real
  Step2-entry API (generation2) through registered Step3 (generation3), with
  wrong identity rejection, original budget and downstream authorization retained.
- Important2 closed: verified source-monitor terminal permission persists only
  on the exact existing reservation and original caller/evidence/monitor identity.
  Its real second backend request, without native snapshot, consumes the separate
  Worker nonce proof; superseded monitor is refused, budget/deadlines unchanged.

Original BS10610 logs confirm14 unique passing behavior cases: R2 two, R4 one,
shared SSH nine, thin WGS/GATK callback wiring two. Exact bio_wgs/bio_gatk files
import with empty DagBag errors. First combined run had two R2 passes and one R4
fixture failure: the fixture counted a retained airflow_dag_failed audit action
as a recovery action. Only its count filter changed to cce_compute_recovery;
only R4 was rerun and passed. The consumer source and R2 fixture were unchanged.
This initial failure is retained, not concealed or represented as an all-green run.

Evidence directory in owner checkout: `.codex-artifacts/ue05-review/`;
remote origin: approved BS10610 `WGS_test/cce-evidence/ue05-native-consumers-20260930-continue/review-20260930`.
Coordinator verified18 manifest entries and11 source/test input Git blobs against
03bab6c; correction diff-check passed. Final tested source tar SHA256:
`c9170c42bc2adf4f17ee7f3b94c55bdd18520df2001b580aeaaf8c476dc6fa07`.
Backend raw log/XML and final R4 log/XML, SSH/callback/DagBag logs and manifests
remain in that evidence directory; exact hashes and commands are in owner HANDOFF.
Runtime tests used isolated synthetic containers; UID50000:GID0 matches the
existing Airflow Worker, not UID0. No dependency/permission/service changes.

No tests, SSH, production reads or product edits were repeated by this closeout.
Accepted UE01-04/F7/final-release evidence is reused. Thin callback tests are
wiring evidence, not independent native terminal validation; manual Step1/GATK
Step1-2 matrix and installed behavior are not newly claimed.

The original native owner confirmed final pairing against accepted7172573, using
the earlier native source/evidence and the current AF commit, without SSH/tests:
bio_wgs:563-582 and bio_gatk:259-278 convert uncertain transport/results to
DispatchUncertain; common/stage_execution:178-187 observes the original full ref,
not a new generation or replay. Budget:35-224 and poll:53-100 preserve the frozen
entry/Step3/receipt binding. Budget:258-353,393-475 preserves unknown/cleanup
refusal, with schema2 selected-Master/Worker quiet proof independent at356-390.
The second Worker POST still sends only its own evidence; the exact stored source
permit cannot authorize another monitor or replace nonce/deadline validation.
No native adapter, paired-runtime or query-primitive expansion is required.

This closes the planned final-source pairing and UE05 source/scoped acceptance.
Actual installed runner/wheel/PATH/selector and production pins remain outside
this review and belong to UE06. AF state-only a0666e5 changes no tested source.
No UE06 operation was started. Rollback remains non-promotion.

## Original review verdict

Initial verdict at8617dfa/a9a326d: changes required; no UE05 acceptance then.
One read-only review, with coordinator verification of the two actionable
findings. No Critical, two Important, no additional Minor findings.

## Scope and verified input

- Owner: original Airflow thread `01a0e728-4c99-71d0-87e9-987b311022c9`.
- Checkout: `C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo`;
  branch `jiucheng/airflow/UE05-native-recovery-consumers`.
- Source range: `06bf30a..8617dfa26b53d8371567fd1000a6a598ab87deff`;
  `a9a326d5cdd74d6f32684759f3c693261f88cec4` changes only state documents.
  Existing shared SSH source at `06bf30a` was read for caller semantics.
- Approved scope: [UE-05 plan](../superpowers/plans/2026-09-28-unified-stage-execution.md),
  R2 current recovery action/compute-terminal consumption, R4 six-stage
  failure/cleanup fences, existing authenticated snapshot producers and SSH.
- Accepted UE04 `a6c31d1` and `7976f25` remain ancestors. All19 source/doc manifest
  hashes match the checkout; source tar and manifest file hashes match handoff.
  Tracked tree is clean, only existing `.codex-artifacts/` untracked.

This review does not resume old WES/Step1 repairs or change the approved plan.
The implementation strengthens real consumer paths, but two supported positive
paths remain blocked. Correcting these is UE05 completion, not legacy compatibility.

## Important 1: recovery entry stage is mistaken for compute stage

Source: `backend/app/cce_recovery_budget.py:47,58,75` and
`backend/app/cce_recovery_poll.py:77` at the source checkpoint above.

`bound_compute_terminal` requires both `action.payload_json.stage` and
`conf.resume_stage` to be `step3_monitor`, and uses the action's entry generation
to select the Step3 row. Current manual recovery supports Step1/2 entry as well.
WGS `wgs_resume_service.py:29-80,142-157` and GATK
`gatk_runtime_service.py:137-147,316-336` register subsequent Step3 under the same
authorized action without changing its entry stage/generation.

Consequently a supported Step2-entry recovery reaching a genuine Step3 failure
cannot settle its queued computation fence even with matching frozen/native
terminal evidence and remaining budget. Poll returns `needs_attention`.

Required narrow correction: resolve the actual frozen Step3 registration and
identity/generation authorized by the current action and DagRun. Preserve the
entry stage meaning, current/latest identity check, downstream scope, original
budget and deadline. Do not simply remove stage checks or rewrite entry identity.
Extend the existing R2 fixture with one Step2-entry to Step3-terminal case and its
identity rejection assertion; no pipeline-by-stage matrix.

## Important 2: initial native terminal permission is lost before Worker follow-up

Source: `backend/app/cce_recovery_poll.py:60-76` and
`dags/cce_worker_wait.py:57-60` at the same checkpoint.

For an initial DagRun with `resume_action_id=None`, the failed current Step3 can
still contain an obsolete reconnect/query-unconfirmed flag. A first POST with
fresh matching native failed evidence correctly crosses this fence and reserves
an action with a Worker challenge. Its `initial_native_exact` permission exists
only in that call. The second POST correctly removes native observation and sends
the independent nonce-bound Worker proof; however the early query-unconfirmed
guard returns `needs_attention` before pending/_worker_wait can consume it.
The supported recovery remains blocked despite the valid first observation.

Required narrow correction: persist the verified source-monitor terminal permit
on the existing reservation/evidence identity and allow only the exact current
reservation/challenge continuation to reuse it. Keep the Worker nonce proof
independent, preserve the original deadline/budget, reject unknown initial proof
and superseded monitors. Do not copy Worker evidence into native evidence, trust
an arbitrary saved terminal flag, or bypass the guard for every pending action.

The R4 fixture currently checks only first `waiting` at
`backend/tests/test_cce_recovery_cleanup_fence.py:420-426`. The thin DAG bridge
stubs the second response as `delegated` at
`dags/tests/test_native_callback_observation.py:91-96`; that is wiring evidence,
not proof of the real backend continuation. Extend this same synthetic scenario
through one real backend follow-up, asserting nonce/identity and no second budget
reservation. No new test framework or full recovery suite is needed.

## Preserved strengths and review limits

Both DAG producers, authenticated internal APIs, service consumers and UE04
validator are genuinely wired. Identity/hash/action binding is stronger; cleanup
selects a stage from trusted run/route state rather than accepting an arbitrary
snapshot stage. Step2 handoff alone does not authorize global cleanup. Worker
proof remains separate. SSH keeps a single budget, a strict pre-session retry
predicate, and uncertain dispatch observation rather than command replay.

Declined to judge, with coordinator agreement:

- Final-source GREEN/two-file DagBag import and installed behavior: not run and
  explicitly missing in handoff; source review cannot replace them.
- Accepted UE01-04/F7/final-release runtime evidence and production/cloud state:
  unchanged acceptance is reused; no duplicate operational inspection authorized.
- Native internal terminal generation: belongs to the native owner's paired
  review, not a second platform implementation or test campaign.

Coordinator verified only actionable lines and handoff artifacts after the single
review, not a second full review. Source remains unmerged and undeployed. Original
owner should fix only these two issues, supply the precise delta, then complete
the already planned unique BS10610 checks after fresh boundary/interpreter
preflight. Recent successful WGS document access on BS10610 is connectivity
evidence, not Airflow runtime preflight or GREEN. No dependency install, local or
production test substitute, data operation or UE06 activation is authorized.
