# P0 joint recovery implementation ledger

Baseline: airflow test `1da45f3`; isolated branch
`jiucheng/runtime/CR01-cce-recovery-20260922`.
Authority: user-approved two-stage implementation in the current conversation.
This supersedes the earlier external-scope hold, not the production boundary.

## Execution sequence

1. Plugin owner: submit intent, exact-name reconciliation, bounded create,
   sealed failure evidence, Master/runtime contract and test-only artifact.
2. Airflow owner: validated evidence consumer, durable attempt budget, adapters,
   DAG/callback/lease fences, Step4 reconciliation and shared status projection.
3. Focused synthetic BS10610 Airflow acceptance; automatic policy remains off.

No main/production updates, BS96 access, real analysis or shared install.
No unrelated regression suite. Preserve the original worktree's dirty files.

## Current progress

- Draft consumer RED/GREEN:62 checks passed0.13s in the same BS10610 isolated
  candidate; no existing budget retest. No actual producer fixture yet. Proposed
  terminal seal contract is documented in docs08; not wired or claimed emitted
  by current images. Producer owner explicitly confirmed candidate is not auth.
- Ruling: keep UNKNOWN creation outcomes fail-closed, including transport+404;
  trusted all-intent reconciliation/producer support is a prerequisite, not
  inferred from zero active pods. Cost: some0918A cases still require manual
  handling until CR-03 supplies sufficient evidence; automatic enablement stays off.

- 2026-09-22 continuation: user and coordinator released isolated development
  and network-disabled ephemeral-container synthetic tests during the existing
  upload. Formal service deployment/integration remains gated. No shared service,
  upload, maintenance monitor, lease, database or production mutation is allowed.
- Fresh fingerprint: server10610, unchanged backend mount
  `releases/20260917-native-ui-76915d8-r2/backend`, cached image `8491604ee01d`;
  test environment, intake scan and auto dispatch false. Separate candidate:
  `candidates/p0-airflow-recovery-20260922` (not the coordinator's r2 candidate).
- Budget RED ran there in a read-only, network-none container (1 CPU / 1 GiB):
  expected ModuleNotFoundError for app.cce_recovery_budget, one failure. No live
  DB mounted; tests use in-memory synthetic SQLite. Implementation now in progress.
- Ruling: keep the existing tracked progress ledger as the durable plan record;
  skill scratch workspace points to it. Do not replace this interrupted plan
  with duplicate tasks. Cost: task bookkeeping is explicit rather than generated.
- Ruling: require both frozen policy and explicitly initialized budget; missing
  counter/journal state fails closed, never resets historical recovery allowance.
  Cost: enabling code must initialize both for new attempts only.
- Budget primitive GREEN:54 checks passed1.89s in the same isolated image; tested
  policy, journal/deadline consistency, two slots, replay, rollback and existing
  control/maintenance records. PostgreSQL concurrency not claimed. CR-02 is only
  partially complete: source validator, reservation/dispatch wiring and shared
  critical-section fences remain. No shared module or main.py changed.

- Plugin implementation requested from the user-selected WGS-cloud-plugins task
  `019f9d79-be3f-7701-af33-3595d72bbfac`; producer schema alignment pending.
- BS10610 read-only fingerprint: server10610; worker DAG mounts still from
  `20260915-main-359df11`, backend from `20260917-native-ui-76915d8-r2`.
- Coordination task `01a0b254-07b5-7352-99aa-871b117459ad` is updating the test
  baseline. Remote deployment/testing is paused until its new fingerprint arrives;
  plugin owner notified. No services changed by this task.
- Wrote attempt-budget test cases, not yet run. No implementation or passing
  test claimed. RED/GREEN must run on BS10610, not local Windows.

## Interface decisions

- Runtime validates producer evidence against frozen identity before the backend
  reserves an action. Reservation is internal, not a browser-authorized payload.
- Reuse RunAction JSON plus AnalysisRun row lock. Frozen attempt policy and
  original deadline are mandatory; missing historical policy is disabled.
- Plugin context agreed: schema `snakemake.kubernetes.submit-context.v1`,
  pipeline/analysis_id/attempt/execution_id/generation/request_hash/run_id/
  namespace/master_job_uid/master_pod_uid. Context file is injected by the
  authoritative Master wrapper, not supplied by a browser.
- `snakemake.kubernetes.executor-failure.v1` is a candidate only, with
  automatic_recovery_allowed=false and requires_master_terminal=true. Consumer
  must separately validate the sealed complete Master terminal and Worker
  quiescence; absence of rule events is not proof of no rule failure.
- The requested focused testing overrides skill defaults requesting whole-suite
  runs. Remote tests wait for the coordinated environment rather than using a
  substitute local runtime.

## Environment hold confirmed

Coordinator confirmed baseline deployment has not happened. Main/production
`9b381eb` is contained in test `1da45f3`, which has 37 additional commits.
User choice of selective production-fix sync versus full test deployment is
pending in that task. Do not deploy or run remote acceptance until it releases
the hold with a verified fingerprint. Existing tests have not been executed;
there is no green result and no enabled automatic recovery.
