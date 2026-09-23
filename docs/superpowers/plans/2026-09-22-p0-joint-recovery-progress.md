# P0 joint recovery implementation ledger

## 2026-09-24 Task3 source completed; Task4 next

Existing WGS/GATK Resume consumes approved native final inventory, full live
workload reconciliation, trusted directory-lock capability and separate generation
view through existing action journals. No repeated CREATE on uncertain response;
no repeated START after confirmed or lost/regressed handoff; native success
creates nothing. BS10610 capability6, composition29 and affected5 passed;
initial composition10 RED; exact logs and review limitations in latest HANDOFF.
Scoped review has no open Important/Critical. Dependencies platform321b0a1,
producerfa1ac44, Worker5b5d7ee. Task4 authenticated service/DAG/all-writer callback
construction and propagation of returned view remains next; no TTL, production,
images, installed CLI, real reruns, merge or push authorized by this checkpoint.

## 2026-09-24 Task3 approved native dependencies accepted

Final Worker snapshot + independent next-generation view accepted in isolated
native source; original bundle/config/history preserved. Exact native reader,
actual plugin inventory/terminal consumer and complete live reconciliation:
BS10610 view6 + final18 + live10 new cases,5 affected checks passed. Approval
is no longer pending. Task3 still needs existing Resume/lock/action-journal
side-effect wiring and final adapter matrix; Task4/all-writer closure separate.
No artifacts, install, deployment, production or real rerun. See HANDOFF.

## 2026-09-23 Task3 compatible confirmation and native success

27 new synthetic cases RED/GREEN accepted: classified exact query, complete-list
guard, WGS real Task1 handoff composition, GATK active v2 reuse, bound native
success and ambiguous-terminal rejection. Scope confirmation was pending for final
Worker ledger production and next-generation derived view. Full Task3 inventory,
lock callbacks/recycled Master replacement remain open. Failed v2 Master blocks
before deletion, not after destructive handoff. No Task4/5 or production advance.

## 2026-09-23 Task3 first Resume guard checkpoint

Continued existing branch after Task2; production historical reruns remain
discussion only. Implemented guards in existing WGS/GATK Resume, not a second
recovery framework: uncertain CREATE+404 and disappeared replacement do not
reopen submission; exact UID/RV is rechecked before delete; WGS existing journal
is owner-only/exclusive/fsynced and retains intent fields; incomplete Pod pages
and archived GATK Worker NOT_FOUND without terminal evidence block replacement.
BS10610 RED6 failed/1 passed, then7 new and13 affected legacy passed separately.
Review found an unknown submitted Job can appear already Failed: RED1 reproduced;
guard now blocks before deletion/reopening submission. That regression and the
normal failed replacement/replay path GREEN2;8 new accepted cases total.
No local/runtime full suite, shared services, producer install or cloud actions.

Task3 remains in progress: confirmed handoff/native success, durable terminal
readers+complete live/admitted inventories, canonical-directory/legacy lock
callbacks remain. Task4 authenticated adapter/DAG/all-writer closure and Task5
TTL/artifact gates are unchanged. Source hardening must not be presented as
complete cross-Master recovery or readiness of the five old production batches.

Scope ruling: Step7+manual local deletion does not complete same-batch platform
recreation. Existing project/batch registration, frozen snapshot uniqueness and
history reuse still need a separately scoped lifecycle change; no such schema,
registration or deletion change added to this checkpoint. Retain this open
boundary rather than infer success from the directory-lock design.

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

- P0-2 Task2 SOURCE PRIMITIVES COMPLETE: plugin5b5d7ee/0.6.4+bs8.dev1 from
  accepted25297f9; cce-pipeline7926496 after Task1c33740d. Exact Worker terminal
  persistence/cache/query scope and opt-in directory owner/generation CAS,
  legacy lock guard/snapshot, fenced release.15 +17 focused BS10610 tests,
  5 +3 affected legacy checks passed. Review fixes: terminal callbacks before
  quota reads without fabricated release; journal intent retained after unknown
  write; released generation cannot be reopened by old action. One journal
  validation per poll. No full suite/artifacts or producer installation.
- User clarification: five failed runs are a compatibility discussion, not
  permission to inspect/rerun. Preserve immutable inputs/attempt/history;
  legacy mapping + verified quiescence + conditional lock handoff via upgraded
  recovery entry. No bulk migration/delete/prepare. New source primitives are
  not currently called; Task3/4 must provide trusted full inventory, canonical
  directory and paired CLI/platform/downstream wrappers and durable journal.
  Next Task3, no production/main/TTL/automatic enablement.

- P0-2 Task1 SOURCE COMPLETE: producer c33740d, isolated cce-pipeline branch
  jiucheng/runtime/p02-master-handoff-20260923, pinned remote/local83e7adb.
  Verified server10610 mounts/gates; remote prototype untracked audit files kept.
  Schema2 START confirmation, unchanged original deadline, idempotent control
  replay, atomic same-Pod exclusion and native identity-bound terminal records.
  Final24 focused +18 affected legacy synthetic tests passed on BS10610.
  Runtime field mapping: producer docs/architecture/master-handoff-v2.md;
  integration: docs08 and 2026-09-23-p0-2-master-handoff-ttl-implementation.md.
- Review rulings: late controller restart accepts only an originally on-time
  ack; completed Pod uses existing persistent reader; overlapping same-Pod
  invocation must fail before config writes or terminal trap. All3 regressions
  first RED then GREEN. These fixes do not implement Task2 cross-Master locks.
  Native terminal evidence_complete=false is intentional until independent
  Worker/Kubernetes finality is proven. Missing Job/unknown CREATE reconciliation
  remains Task3; no artifact/TTL/automatic recovery completion implied.
  No BS96/services/main/production change, no push or shared installation.
  Earlier blocked planning checkpoint below is historical, now superseded.

- P0-2 revision through781877e integrated from e921e3a. Detailed implementation
  sequence: 2026-09-23-p0-2-master-handoff-ttl-implementation.md. Documentation
  only this turn; Tasks1–6 remain open. Two BS10610 preflights failed SSH exit1
  at jump172.17.61.18 before any remote command. Runtime producer provenance
  and dirty prototype ownership unverified; no local test substitution.
- Pre-flight interfaces: Task1->3 START_CONFIRMED and bound native terminal;
  Task2->3 exact Worker terminal plus inventory and logical-run lock;
  Task3->4 original action/journal and normal stage receipt; Tasks1–4->5
  compatible evidence readers before TTL; Task4->6 existing action/budget/fences.
  Ruling: source field names must be mapped to pinned actual producers before
  edits, not guessed from older1462e9e; cost is deferred implementation until
  source access, avoiding an incompatible duplicate contract.
- Ruling:781877e P0-2E supersedes any older “lock unchanged” ownership wording;
  retain the primitive, add conditional takeover/release and GC independence.
  Task2 must close legacy/CLI lock-domain compatibility before Task5 activation.
  Cost if missed: same-directory double writers or stale-owner unlock; fail
  closed meanwhile. Preserve all earlier accepted evidence; no re-test claimed.

- Fromfdef310: CR-03 runtime receipt projection slice, not a new recovery layer.
  WGS stage-status and GATK sync lock/refresh the current run and refresh stage
  execution state before terminal projection. GATK rejects stale attempts;
  existing generation fences remain. No request/receipt schema or retry change.
  Focused RED4 failures (stale attempt and cached-success overwrite, WGS/GATK),
  GREEN8 passed0.79s;5 affected legacy cases passed0.73s. Initial fixture setup
  omitted required workdir and was corrected before behavioral RED.
- Ruling: this slice covers stage-status receipts only, not all rule/workload/
  transfer projections or trusted-terminal production. SQLite verifies cached
  state behavior, not PostgreSQL lock contention. Cost: full observer/concurrency
  acceptance remains pending with adapter/dispatch and Step4 work.
  Test-only candidate; automatic recovery disabled, no deployment/main/push.

- From26d62dd: resumed at the existing10-case inventory test draft. Fresh test
  preflight succeeded; RED1 failed unsupported control schema. Added exact
  admitted-worker/context/UID control binding without inventing submissions;
  GREEN34 inventory cases0.05s (2 unrelated external fixtures deselected).
  Candidate null UID retains verified journal UID; foreign/missing/unresolved/
  mixed FAILED submissions or unsafe read scopes reject.
- Owner's SSH failed but this task's connection remained available. Reviewed
  owner-provided base/dirty/branch guarded finish/build scripts, executed once:
  plugin25297f971dd463176d5fdc07908a60095ade50ea, clean bs7 branch, bs6 still
  0b19bb605cdff619a7f09b34a6fe774e4b43d357. Offline new wheel SHA256
  2ad4aa737e6f34930b6832e3ce69edd9ee64867cc9c7ce0c1bcb4c455cdbae86;
  52 affected actual-wheel tests passed5.60s, not a rerun of108 source tests.
- Four actual-wheel fixture scopes hash-pinned in new bs7 contract test;
  WGS/GATK successful CREATE then GET failure, lost-response ADOPT then LIST
  failure.4 platform cases passed0.08s, no skips. No terminal produced;
  candidate-only input rejects, positive terminal scaffolding synthetic only.
- Ruling: reuse complete submission inventory instead of writing control faults
  into submit events. Nullable candidate UID can be associated only with a
  unique known admitted UID under the same context and verified manifest;
  unknown/ambiguous identity remains blocked. Cost: incomplete evidence needs
  manual resolution. No new history/audit framework or quota relaxation.
  This closes this source/contract slice, not whole P0. Continue existing query,
  terminal/binding/dispatch/observer/Step4 integration and final acceptance.

- First coverage slice committed26d62dd. Continued next control-inventory test
  draft (10cases), no product change yet. SCP then prepared RED command both
  failed at BS jump172.17.61.18 handshake before remote execution; no remote
  pytest result. Stop retries, preserve draft; resume with fresh BS10610 gate,
  RED and actual bs7 artifacts. Owner-reported108 source tests do not replace
  actual-wheel platform acceptance. No production/local-test fallback.

- From670b50e: user-authorized current-disconnection extension. GATK input/result
  slot gate now retries existing transient backend classifications6 times,
  30s exponential capped5m; request identity/pools/48h timeout preserved. Actual
  DAG7 checks passed on BS10610 after RED;2 lease identity checks confirm lost
  response replay and no other identity takeover. No transfer/SSH stage retry.
- Agreed HEAVY_SLOT_API_UNAVAILABLE candidate is separate from CREATE evidence:
  GET Lease / exact Worker Pod LIST, typed errno111 only. Consumer and reader
  accept only complete matching synthetic terminal scaffolding, never candidate
  alone; mixed files, directory races and schema/file mismatch reject.26 focused
  backend checks passed0.58s; then26 affected reader/security checks passed0.07s
  after a separate filename mismatch RED. Counts overlap; not52 distinct tests.
- Owner implements new bs7 source/artifact; bs6 frozen. Actual plugin acceptance,
  inventory support and trusted terminal integration pending. D archived HTTP500
  Status.message shape obtained but source CREATE chain still needs confirmation.
  E has multiple generations/failure types; known quota Pod LIST is in scope,
  active-old-Worker/Ready timeout/generic kubectl errors are not recategorized.
  WES generic query-error provenance is still lost; no text-based retry bypass.
- Continue the original P0 runtime/query and adapter/dispatch/observer/Step4
  work. No production/main/shared-service mutation or automatic policy enablement;
  this slice does not complete P0 or make current frozen runs recover themselves.

- From3b3e142: CR-03 external lease/observer cleanup fence. Locked current run,
  attempt, DagRun and pending recovery authority before WGS/GATK release stages
  and WGS observer deactivate; DAGs send actual run_id. Partial WGS release
  re-locks before retained-slot projection.24 new backend+3 legacy API+7 actual
  DAG tests passed in isolated BS10610, with RED evidence for stale release,
  missing DAG payload and partial-commit race. No shared service/production change.
- Ruling: retain legacy identity-less no-recovery cleanup and trusted runtime
  terminal ingestion unchanged; guard only external cleanup entry points. Reuse
  existing failure-fence predicate, not a new state/control system. Cost: old
  recovery cleanup without identity requires reconciliation. Partial release
  may finish its already-valid terminal-slot release before a later identity
  recheck fails; it must not overwrite the new run projection. This does not
  replace PostgreSQL concurrency testing or complete dispatch/adapter/observer
  generation/Step4 integration. No extra audit track or automatic enablement.

- From04a2530: CR-03 failure callback fence, both adapters. Stale/identity-less
  recovery callbacks cannot overwrite run/Sample/Rule projections; GATK now
  carries actual DagRun identity. Exact current dispatched replacement can still
  fail. WGS failure history dedup includes DagRun, preserving old end time only
  for replay of the same failure.22 new backend +5 legacy +1 actual DAG case
  passed on BS10610; RED reproduced state overwrite and old timestamp reuse.
- Ruling: legacy identity-less callbacks remain compatible only without current
  automatic-recovery history (existing WGS manual fence still applies). Future
  trusted dispatch must persist target dag_run_id before external submission;
  reserved actions never authorize a failure projection. Cost: missing/malformed
  recovery lineage stays ignored pending reconciliation, not guessed. This is
  callback protection only, not runtime-failure classification or auto-dispatch.
  No extra audit track, production changes or unrelated full-suite rerun.

- Fromddda74e: closed the existing WGS legacy Resume/Rerun failed bypass of
  pending automatic recovery. Shared the resume_stage check, refreshed run row
  lock before decisions; cancel remains outside the retry fence. RED1 failure
  (expected rejection absent), GREEN22 passed1.23s on isolated BS10610. No broad
  suite, service change, policy enablement or main/production operation.
- Ruling: preserve legacy attempt semantics once automatic actions finish; this
  slice only prevents overlapping entry, not redesign manual Resume. Costs:
  full dispatch/callback/adapter/GATK integration and PostgreSQL concurrency still
  required; do not claim all retry/submission entry points are covered.

- Fromb5d8718: SSH restored; fresh Step7 backend mount/gates confirmed and bounded
  readonly nonterminal query returned[]. Actual bs6 WGS/GATK admission+guard
  fixtures received and raw bytes/wheel/provenance hash-pinned.14 focused consumer
  checks passed0.32s,62 unrelated cases deselected, no skips, no plugin suite rerun.
  Candidate-only inputs and guard errors reject; admission draft-contract format
  remains compatible. Production code unchanged; no deployment/policy enablement.
- Ruling: count this as bs6 candidate-format acceptance only, not trusted terminal
  or end-to-end automatic recovery. Positive synthetic terminal remains explicit
  scaffolding. Next: existing control/dispatch/callback fences and adapter wiring;
  do not reintroduce extra audit or relax the complete-evidence gate.

- Next step from930348c: actual bs6 consumer acceptance selected. Single fresh
  BS10610 preflight failed at jump172.17.61.18:22 SSH handshake, before remote
  script execution. No new fingerprint, test, service change or runtime write.
  Actual WGS/GATK admission/guard producer fixtures requested; pending receipt.
  Existing consumer negative matrix has one new guard-category case, unrun.
  Ruling: retain approved remote-only validation; no local/production fallback,
  no whitelist relaxation, no redundant suite. Cost: this acceptance remains
  pending until test-host connectivity and actual fixtures are available.

- bs6 owner handoff received:0b19bb605cdff619a7f09b34a6fe774e4b43d357,
  wheel SHA256 f9671d22ed02ec5a3edf0af861e116c0ea7dc9de816de6e07926fa869e2bb546.
  Preserves biosan5 HeavySlotQuota; duplicate-adoption manifest/receipt fix.
  Owner reports86 source and86 actual-wheel checks; not rerun here. New
  WORKER_SUBMIT_GUARD_FAILED stays UNKNOWN/retryable=false, statically rejected
  by existing consumer allowlist. Actual bs6 consumer fixture acceptance pending;
  no new complete terminal producer or deployment/automatic authority delivered.
  Test baseline now reported ab8695d: recheck live fingerprint before remote work.

- Scope correction after owner coordination: the user's batch example is only
  a Master error-completeness check. Runtime owner confirmed bs6 integration
  preserves all biosan5 HeavySlotQuota behavior and excludes extra Master audit.
  Ruling: stop the additional producer/terminal draft and continue CR-01–05
  against delivered contracts; do not lower the complete-evidence recovery gate.
  Cost: unsupported/incomplete terminal evidence remains manual, not an automatic
  replacement case. No new reason-enumeration or batch-specific track.
- Own unverified draft preserved in stash3c617cbd86a4b3d27309689ecdfd7fc820f73c57;
  RED one missing-module failure, no GREEN or actual producer acceptance. Earlier
  audit-next notes below are superseded. Existing ce9e296 diagnostics unchanged.
  Next work remains consumer/control/dispatch/callback fences and adapter wiring;
  actual bs6 commit/artifact contract is pending. No services or policy changed.

- User clarification afterce9e296:20260921D is only an example for Master error
  completeness, NOT a separate incident or additional development track. Continue
  the existing joint P0 sequence. No further reason enumeration or live-batch action.
  Producer owner resumed minimal Master-side typed-error/cumulative/final-footer
  implementation in an isolated candidate; consumer contract coordination in flight.
  Keep frozen bs5, production and shared services unchanged. Do not claim the
  diagnostic increment completes trusted Master error coverage.

- 2026-09-23 from8439f55: user asked next step plus20260921D BackoffLimitExceeded
  coverage. Existing design already excludes that symptom alone from automatic
  eligibility. Extended existing probe (no new helper service) to preserve exact
  Master condition and all observed Master Pod termination/restart evidence.
  RED KeyError master_job_condition; GREEN34 affected checks passed0.06s. No
  unrelated suites, actual production diagnosis, deployment or recovery action.
- Ruling: retain BackoffLimitExceeded as diagnostic evidence, never infer transport
  or admission root cause from it. Cost: a failure with only that symptom remains
  manual until complete bound root-cause evidence is available. This does not
  complete the trusted Master audit producer/footer or advance automatic enablement.

- 2026-09-23 next slice from22d47cb: complete snapshot inventory validator and
  composed UID probe. RED missing module (exit1), GREEN26 passed0.08s (exit0),
  actual producer WGS/GATK admission fixtures included, no skips. Only new test
  file executed; no shared service/test DB/runtime/production mutation.
- Ruling: chained checkpoint + journal + manifest proves snapshot consistency,
  not finality or writer authentication. Future Master audit/footer must bind final
  raw digests; the composed helper intentionally emits no seal/authority. Missing
  historical admitted-Worker outcome cannot be treated as zero rule failures.
- Plugin owner completed bounded source review without changing bs5: submission
  exception bypasses JOB_ERROR, ERROR is dropped by rule-status, cancellation can
  race with remote polling, logger stop suppresses flush errors. Full source-line
  and hash evidence: plugin-p0-submit-20260922/MASTER_ERROR_PRODUCER_READONLY_REVIEW.md
  under the existing WGS_test/cce-evidence root. Implementation must capture typed
  submission cause before cancellation plus mixed/unknown causes, and explicitly
  finalize after producers stop. No text/class-name whitelist or empty-log seal.
- Next: implement the minimum trusted Master audit/terminal path under the
  approved Master/runtime scope; keep frozen bs5 intact until coordinated change.
  Then adapter binding writer/dispatch/callback fences. This slice does not close
  CR-01 or CR-03; automatic recovery remains off and service window belongs to WES UI.

- Bound workload observation prerequisite: scripts/cce_recovery_workloads.py,
  exact UID/namespace/controller ownership and complete container exits, missing
  Job residual-Pod checks, read-only bounded queries. RED missing module then
  GREEN25 checks0.06s on BS10610. No existing runner caller or seal emission.
- Ruling: do not reuse baseline runtime83e7adb no-active-worker guard as P0 proof;
  it omits exact UID and residual Pod checks. Build the minimal read-only probe
  without changing legacy manual Resume. Cost: trusted inventory binding and
  cumulative Master error-summary producer still required before a terminal seal.
- Fresh BS10610 active_runs=[] and backend mounts/gates unchanged. Shared-service
  window now belongs to WES UI; no deployment here. Only isolated candidate writes.
  Plugin f1d3fa58 /0.6.4+bs5 metadata-only change and new wheel hash verified;
  original fixture/test evidence remains bound to0d606489. No suite rerun/install.

- Actual producer follow-up: plugin0d606489 clean and wheel hash verified;
  original pipeline=synthetic fixture not allowed as WGS/GATK. Owner regenerated
  wgs-admission/gatk-admission through the same candidate wheel.4 hash-pinned
  consumer checks passed0.08s (producer-contract.log): candidate alone rejects,
  actual candidate plus synthetic terminal is compatible. No real terminal seal
  or runtime integration claimed. No code-policy relaxation or plugin-suite rerun.
- Fresh BS10610 mounts/gates unchanged; bounded read-only transaction found
  GATK_20260922_112207_23AD29 in Step1 upload. Only isolated candidate files/
  network-none test container changed; coordinator notified, no shared deployment.
  Pending-fixture notes below are superseded; trusted terminal/binding writers,
  dispatch/fences and actual integration remain pending.

- 2026-09-23: internal DB-lineage bridge now joins current failed Step3 monitor,
  actual Master-submit binding, controlled reader, validator and budget.22 new
  WGS/GATK synthetic checks passed1.04s on BS10610. Stale identities and replaced
  evidence cannot reserve; no production caller or trusted-binding writer yet.
- WGS manual resume-stage fence RED demonstrated bypass of reserved automatic
  action; GREEN8 checks passed1.17s. Reserved/queued/uncertain block before files
  or Airflow; completed automatic history is preserved and permits manual resume.
  Other entries/dispatch/callback/PostgreSQL concurrency remain pending.
- Plugin owner now has actual submission_recovery.py and integration changes in
  its worktree; no final commit/producer fixture accepted yet. Automatic recovery
  remains unwired/off. No deployment, BS96, shared service/database or live-task
  mutation. Earlier draft-only plugin observations below are historical.
- Ruling: reuse existing terminal_payload_json for proposed immutable trusted
  submit/monitor bindings (docs04), no new table/backfill or public input. This
  advances internal integration without inventing evidence for old releases.

- Next slice from73f8d4e: controlled fixed-file reader RED→GREEN26 checks0.09s;
  only new reader tests ran. Descriptor nofollow, file bounds/type/link checks,
  duplicate-key rejection and bound content validation; no runtime route wired.
- Coordinator released the upload gate during this slice. Future deployment
  still requires fresh active-run/mount preflight and agreement with Step7;
  this task did not deploy or modify any shared service/data. Earlier blanket
  hold entries below are historical, superseded by this scoped release.
- Plugin source probed at1ca1e88 with only draft docs/tests; owner explicitly
  asked to finish actual source/tests and report once. Do not count draft fixtures
  as producer integration. Master Step2 submit context and Step3 monitor identity
  must be kept distinct in the future lineage binding, not assumed identical.
- Ruling: current next step closes the controlled-reader boundary while producer
  work proceeds; no permissive entry is added to bridge missing trusted wrapper
  evidence. Cost: automatic dispatch still unavailable until the remaining
  CR-01/03 dependencies are implemented and accepted.

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
