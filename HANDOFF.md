# Handoff

## 2026-09-25 Task6 continuation / finite query-budget prerequisite

Goal: continue original Task6/CR-04, BASE04a1a04 platform and BASEd7bd741 native,
same isolated branches. Scope is query-only budget and strict native read ABI,
not new recovery policy/state machine for compute, public endpoints or controls.
Paired native source committed90cae30; plugin remains81132cf, artifacts unchanged.

Completed: scripts/cce_query_reconnect.py consumes caller-owned current scope and
original deadline, one typed read-only GET at a time. Max6 retries with delays
30/60/120/240/300/300, capped request30s/original deadline, persist before retry,
crash consumes in-flight slot, failed persistence cannot authorize another call.
Partial GET success retains outage count; explicit authoritative observation is
needed to clear it. Exhausted/blocked/foreign/corrupt state fails closed. Tests
use actual strict native GET + fake subprocess transport and synthetic JSON;
the runtime persistence callback itself is NOT wired to real monitor status yet.

Native prerequisite: platform selected observer calls _recovery_query(configmap)
but native only accepted Job, so real directory-lock read failed INVALID_QUERY.
Added exact ConfigMap under same identity envelope. Missing/denied command and
auth/certificate failures no longer map to transport; generic unable-to-connect
is unknown, not auto-retryable. Positive caller timeout may shorten existing30s.
No legacy _kubectl_json, Snakemake workflow/plugin, CREATE/START or installed CLI
changes. Files: platform helper/test + docs08/plan/state/tasks/handoff; native
cce_batch_runtime.py/test_recovery_query.py/HANDOFF. Native source commit is paired,
not contained in accepted Task5 wheels/images. Do not rebuild/activate implicitly.

Validation: task6.ps1 preflight verified ssh BS10610 -> server10610; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current remains
releases/20260912-opt-4d3d24e6, backend36ff21f87356 expected /app and /config RO
mounts, scanner/auto-dispatch false, uid6708; no services changed. Same cached
backend a0112f0b8ef0 with network-none/read-only root and scoped scratch.
Evidence root: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Command: task6.ps1 -Mode test -Test '/task/native/tests/test_recovery_query.py
/task/platform/scripts/tests/test_cce_query_reconnect.py' -Log query-reconnect-final.
Initial RED: collection missing new module (exit1), query-reconnect-red.log.
Budget-corruption RED: three expected failures (a waiting count6 could exceed its
limit; healthy nonzero count and bool attempt accepted), one passed;
query-reconnect-fence-red.log. Fixed input-state validation, no runtime workaround.
Final41 passed0.79s (native24 + platform17), exit0, query-reconnect-final.log.
No local runtime tests, broad suites, frontend/DAG reruns or real K8s operations.

Remaining/next: wire this owner only to paired selected monitor GETs, with current
worker identity and existing status JSON atomic persistence; preserve reconnect
fields through outer handlers. GATK currently can mark query error as analysis
failed; that consumer and DagRun callback/periodic failure projection need the
same explicit unconfirmed marker before UI integration acceptance. No retries
around prepare_monitor_registered, Resume mutation or whole stage. No authority
from cached progress. Then focused PG/final automatic lifecycle + whole-plan
review. Task6 and CR-04 remain OPEN; no production/push/main merge/deployment.
Rollback: revert paired source commits; no installed state to restore.

## 2026-09-25 Task6 continuation / existing recovery UI

Goal: CR-04 existing Tracker/RunDetail projection, BASE5257b77 on isolated
jiucheng/runtime/CR01-cce-recovery-20260922. No new pages, controls, retry policy,
native/plugin changes, production access, merge/push or artifact rebuild.

Completed: shared read-only recovery_views bulk-reads current-attempt actions and
latest stage generation. It projects waiting/checking/recovering/needs_attention/
stale/completed_degraded with allowlisted messages, due time and last healthy
observation time; no raw path/error/action conf exposed. Queued/running controller
alone cannot imply started Master; schema2 platform identity, native Job/Pod UID
and action match are required. Old attempt/generation/manual-action/user-stop
fences apply. The successful run can retain a Step3 log-health warning after
finalize. Historical workflow/action status and budgets are never changed by GET.

Real-consumer check found running binding/health were not retained. Added a small
UI-only cce_monitor_observation in existing execution JSON after existing identity
gates; no terminal receipt/hash is invented. WGS/GATK preserve newer observations
against old healthy replays. Snapshot contains only time/health and reduced binding.
CurrentProgressPanel/RunTracker reuse existing bars, retain measured values and
disable estimated advancement/live speed/ETA for uncertain or stopped recovery.
Healthy reattachment removes the overlay; actual started recovery uses normal
progress. The old failure remains history, not rewritten to success/running.

Files: new backend cce_recovery_projection/cce_monitor_observation and projection
tests; existing dashboard_service/run_service and WGS/GATK status ingestion;
frontend API types, shared RecoveryNotice, RunTracker/CurrentProgressPanel and
their tests; docs04/05/06 and state/plan/handoff. No runtime producer or DAG edits.

Validation: BS10610 preflight server10610; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current -> releases/20260912-opt-4d3d24e6;
backend36ff21f87356 /app and /config RO mounts unchanged, scan/dispatch disabled.
Task-specific evidence under
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached backend image a0112f0b8ef0 and frontend builder25e83a56052d; network-none,
read-only root, uid6708, isolated scratch only; no service changes/dependency download.
RED: projection16 failures before implementation; UI3 expected failures; actual
ingestion2 failures after correcting fixture's required v2 envelope. GREEN:
pytest test_cce_recovery_projection.py test_cce_recovery_receipt_projection.py
26 passed3.03s (ui-projection-final2.log); vitest RunTracker/CurrentProgressPanel
13 passed6.17s (ui-components-final.log); npm run build (tsc -b + vite) exit0
(ui-build-final.log). One intermediate frontend test failed because a loose text
selector matched label and explanation; narrowed selector, no product workaround.
No local runtime tests/full-suite repetition/browser or live synthetic run.

Remaining: CR-04 finite-reconnect versus exhausted producer-to-UI distinction
must be verified in final integration. This checkpoint only projects actual
persisted health/actions; degraded alone does not prove an active reconnect loop.
Next focused PG contention and full automatic lifecycle integration, then one
fresh whole-plan review. Separately authorized live TTL/capacity/AOM/alerts gates
remain closed; Task6/P0 are NOT fully complete or production-ready.
Rollback: revert this source checkpoint; optional response/snapshot fields are
additive with no migration. Original native d7bd741/plugin81132cf unchanged.

## 2026-09-25 Task6 continuation / Step4 actual caller

Goal: connect the accepted Step4 probe/budget to existing WGS/GATK registration,
runner and sensor. BASE29aae91, isolated jiucheng/runtime/CR01-cce-recovery-20260922.
User requested continuation with no scope expansion or redundant tests. No BS96,
production DB, analysis submission, shared installation, image rebuild or push.

Completed: first opted-in Step4 freezes hashed marker1/original stage deadline;
both adapters preserve execution identity on lost registration replies, including
terminal failures. Existing authenticated stage route accepts begin/poll/check/
finish and commits intent/challenge before SSH. Actual DagRun/recovery identity,
pending control/maintenance, latest generation/hash and frozen request are checked.
Manual Resume cannot race an unresolved publish action; stop paths remain allowed.
Existing Airflow Step4 runner sends once via fixed --publish-dispatch, capped by
120s/original deadline, and acknowledges only that exact local process exit.
Timeout/nonzero enters existing sensor reconciliation. A crashed caller retains
in-flight ambiguity. Sensor makes at most one probe per poke and sends only the
backend-authorized same identity; success still requires normal stage receipt.
Default-off policy, DAG graph/pools/task retries and compute budget unchanged.

Files: backend cce_publish_recovery/cce_recovery_budget, main existing schemas/
routes, WGS registration and GATK runtime service; dags cce_publish_dispatch and
both existing DAG modules; scripts cce_publish_recovery and both runtime gates;
two new caller test files plus original Step4 probe tests. Docs04/05/07/08,
Task6 plan and state/task/handoff/ignored ledger aligned. No frontend/native/plugin
changes. Needed ancillary fix: main.py used Any in the previous Worker observation
schema without importing it; actual route import reproduced NameError, now fixed.

Validation: only ignored task6.ps1 runner, BS10610 synthetic/cached containers.
- step4-caller-red12 failures: absent registration marker / missing control caller.
- step4-airflow-red10 failed4 passed: absent actual DagRun field/automatic stop
  handling. Strengthened probe test to assert it actually made both control calls.
- step4-registration-check6 failed8 passed: GATK filename suffix mismatch in new
  caller plus not-yet-implemented exact send; use actual .request.json convention.
- step4-send-deadline-red2 failures reproduced sends after expired deadline.
- step4-caller-fences-red8 failed12 passed: absent manual/stale-caller fences,
  repeated terminal registration generatedg2, and prior Any import failure.
- step4-caller-boundary-green1 failed88 passed: package import of WGS release
  selector failed; corrected package/standalone import as existing gates require.
- FINAL -Mode test -Test '/task/platform/backend/tests/test_cce_publish_caller.py
  /task/platform/scripts/tests/test_cce_publish_probe.py
  /task/platform/backend/tests/test_cce_publish_recovery.py
  /task/platform/scripts/tests/test_gatk_dispatcher_fence.py::test_ambiguous_spawn_does_not_launch_again'
  -Log step4-caller-final:90 passed7.11s, exit0.
- FINAL -Mode dag -Test /task/platform/dags/tests/test_cce_publish_caller.py
  -Log step4-airflow-final:20 passed3.04s, exit0; actual Airflow DAG imports/callables,
  only external HTTP/SSH substituted. No local runtime tests or broad suite rerun.
- Tests use real SQLAlchemy temporary SQLite transactions/files/locks/request
  registration, not production DB. PG contention and whole automatic integration
  remain planned; this is not a PostgreSQL or cloud-operation acceptance claim.

Each invocation verified test BS10610/server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current
releases/20260912-opt-4d3d24e6 and backend36ff21f87356 actual RO mounts:
/app from20260923-step7-ae416fa/backend/backend, /config from current. Scanner/
auto-dispatch false; UID6708 evidence under
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached network-none RO1CPU/1GiB containers with task scratch RW. Existing kernel
swap-limit warning only. All services/current/rollback pointers preserved.

Task6 OPEN. Next existing UI projections, focused PG contention/final automatic
integration, then whole-plan review. Separately authorized live TTL/capacity/AOM/
alerts still required; no production readiness claim. Rollback is source revert
only; preserve state/receipts/history and accepted artifact pins. No cleanup.

## 2026-09-25 Task6 continuation / Step4 original operation and durable budget

Goal: next approved Step4 slice, source development only, minimal targeted tests.
BASE platform a53aabd; branch jiucheng/runtime/CR01-cce-recovery-20260922 in the
existing isolated worktree. Native d7bd741/plugin81132cf unchanged. No production
access, push/merge, new artifact build, install, automatic enablement or real run.

Completed: scripts/cce_publish_recovery.py validates the original registered
Step4 operation and lock/process/receipt evidence; both restricted gates expose
fixed --publish-probe. New hashed request marker publish_dispatch_version=1 is
mandatory, never inferred for legacy requests. WGS opted-in async launch refuses
repeat Popen after uncertain intent; GATK's existing intent fence is unchanged.
Only absence of records under free launch/worker locks yields not_started;
unknown/foreign/malformed evidence cannot authorize replay. Existing terminal
receipts are read, not synthesized; no native publish record reconstruction or
output scanning. No automatic caller or new registered marker is enabled yet.

backend/app/cce_publish_recovery.py uses existing RunAction and refreshed run/
latest execution locks: one initial sequence0, max2 same-operation redispatches
60/180; original stage deadline, identity, release and workdir retained. Separate
from compute budget. Initial intent must commit before SSH; exact local SSH exit
acknowledges its sequence, process death leaves in_flight unresolved. Negative
proof cannot override in-flight; dispatch requires a challenge issued at/after
due time. Consumed duplicates/stale identity cannot spend another slot. Started
once never returns to not-started eligibility, and success survives later expiry.
Stop/expiry blocks unsent work. Service does not commit or perform external I/O.

Changed files: two new cce_publish_recovery.py modules, both existing runtime
gates, backend/tests/test_cce_publish_recovery.py and scripts/tests/test_cce_publish_probe.py.
Docs04/05/08, plan Task6, CURRENT_STATE/TASKS/HANDOFF updated. No schema migration,
public route, DAG node, frontend, native or biological workflow changes.

Tests via ignored .superpowers/sdd/2026-09-23-p0-2-master-handoff-ttl-implementation/task6.ps1:
- step4-probe-red:27 failed/1 passed (missing probe and WGS ambiguous launch fence;
  removed the irrelevant GATK no-op parameter before GREEN), then27 GREEN1.30s.
- step4-budget-red:22 failed (missing budget service). Initial budget/command
  boundary32 GREEN2.22s. Additional freshness/started-once/terminal boundary6 RED.
- Final -Mode test -Test '/task/platform/backend/tests/test_cce_publish_recovery.py
  /task/platform/scripts/tests/test_cce_publish_probe.py
  /task/platform/scripts/tests/test_gatk_dispatcher_fence.py::test_ambiguous_spawn_does_not_launch_again'
  -Log step4-contract-final:64 passed3.73s, exit0. Real locks, request files,
  SQLAlchemy transactions and gate loaders; only external Popen replaced.
- git diff --check: clean. No full suite, local runtime tests, PG contention,
  Airflow integration or live publish: deferred until the actual caller is wired.
  Docker reports existing kernel swap-limit warning; no test failure.

Every invocation verified BS10610/server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current release
releases/20260912-opt-4d3d24e6 and backend36ff21f87356 actual RO mounts:
/app from20260923-step7-ae416fa/backend/backend, /config from current. Scanner/
auto-dispatch false. UID6708 task evidence path:
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached network-none/read-only1CPU/1GiB container, source RO/task scratch RW.
Services and current/rollback pointers preserved, no deployment/cleanup.

Next: existing stage registration freezes this marker/deadline, and existing
Step4 runner/reschedule sensor uses begin/finish/poll plus restricted probe. Send
only original hash-pinned identity, commit/recheck controls before SSH; confirm
normal authoritative stage receipt before downstream, do not fabricate success
from the budget alone. Wire recovery-action/control fencing there. No retries=2
on the whole side-effectful task, no new DAG nodes. PG contention/full automatic
integration, existing UI and separately authorized cloud gates still OPEN.
Risk: source contracts alone cannot repair a production SSH timeout. Ambiguous
caller crash deliberately needs reconciliation, not guessed re-dispatch. Rollback
by reverting this source checkpoint; no running service rollback needed.

## 2026-09-25 Task6 continuation / exact CREATE failure classes

Goal: continue the approved next slice without widening retries or redundant
tests. BASE platform898db80/plugin c0b266b/native d7bd741. Plugin checkpoint now
81132cf on jiucheng/runtime/p02-worker-terminal-20260923. Platform changes stay
on jiucheng/runtime/CR01-cce-recovery-20260922; native clean/unchanged. No production,
push, main/production merge, build, install, activation, real rerun or service change.

Completed: plugin recognizes exact CREATE Status500 RPC Unavailable/peer-reset;
reconciles deterministic original Job first (PRESENT adopts, UNKNOWN blocks,
ABSENT uses existing bounded submission retries). New category carries only four
fixed typed fields, independently checked by inventory and backend before existing
ABSENT/exhaustion/fatal-cause/terminal gates. mutation.gatekeeper.sh exact500
context-deadline now recognized; policy denial/generic500/missing Status rejected.
Legacy Gatekeeper classes, budgets and default-off policy unchanged. Task5 frozen
wheel/images are not rebuilt and do not include this successor source checkpoint.

Files: backend/app/cce_recovery_evidence.py, scripts/cce_recovery_inventory.py;
new backend/tests/test_cce_rpc_evidence.py; existing scripts/tests/test_p02_failure_evidence.py
uses actual plugin/logger/native FINAL and normal platform receipt/reservation.
Plugin submission_recovery.py, new test_storage_rpc_submission.py and HANDOFF.
Docs08/10, design section3.1, Task6 plan, CURRENT_STATE/TASKS/HANDOFF synchronized.
No public API, DB schema, DAG, frontend or biological workflow change.

Validation via ignored .superpowers/sdd/2026-09-23-p0-2-master-handoff-ttl-implementation/task6.ps1:
initial exact-create-red4 failed/20 passed (missing classes/validator), then24 GREEN.
Mutation strict-boundary4 RED caught legacy over-broad recognition; narrowed new
mutation path, preserving old validation/check-ignore-label rules. Final commands:

- -Mode test -Test '/task/plugin/tests/test_storage_rpc_submission.py
  /task/platform/backend/tests/test_cce_rpc_evidence.py
  /task/plugin/tests/test_submission_recovery.py::test_admission_timeout_has_three_requests_with_30_60_backoff
  /task/plugin/tests/test_submission_recovery.py::test_lost_response_is_adopted_by_exact_name_without_second_post'
  -Log exact-create-final:30 passed2.34s, exit0.
- -Mode test -Test '/task/platform/scripts/tests/test_p02_failure_evidence.py::test_schema2_evidence_through_normal_receipt_and_reservation
  -k storage_rpc' -Log storage-rpc-chain:2 passed/4 deselected3.00s, exit0.

Both WGS/GATK chains accepted one idempotent reservation with distinct native/
platform identity. No full suite or repeated accepted Task1–5 tests. Local runtime,
real cluster, PG contention and deployment tests not run: outside this source slice.
One documentation read used a nonexistent docs/10_ERROR_LOGGING.md filename;
resolved with rg to docs/10_QC_LOGGING_REPORTING.md, no runtime side effect.

Each remote invocation verified BS10610/server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS and current release
releases/20260912-opt-4d3d24e6. Backend36ff21f87356 RO/app from
20260923-step7-ae416fa/backend/backend; RO/config from current; scanner/dispatch false.
Evidence uid6708 confined to /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached network-none/read-only synthetic container, source RO/scratch RW,1CPU/1GiB.
Live services and current/rollback release pointers untouched. This does not
replay archived production failures or authorize activation of new artifacts.

Task6 OPEN. Next Step4 ambiguous SSH dispatch: reconcile original operation,
at most two same-operation redispatches60/180 only with proven not-started and no
in-flight process; separate budget. Then existing UI/PG/final integration and
separately authorized operational gates. Rollback: revert this paired source
checkpoint before any future artifact build; no live rollback currently needed.

## 2026-09-25 Task6 continuation / bounded natural Worker wait

User: continue the next approved Task6 step, preserve scope and avoid redundant
tests. BASE platform7d9f1f8/native d7bd741/plugin c0b266b. Only the existing platform
branch jiucheng/runtime/CR01-cce-recovery-20260922 changed. Native/plugin trees
remain clean; Task5 artifacts unchanged. No push, merge, build, installed policy,
production access, real rerun, deployment or service/scan/dispatch changes.

Completed within this slice: existing automatic RunAction persists worker_wait
start/deadline/state and one nonce-bound monitor probe. It consumes one existing
compute slot and caps wait at min600s/original deadline. Duplicate consumed replies
cannot clear the next challenge. Direct due-dispatch cannot bypass waiting;
stop/expiry/changed proof rejects an untransmitted action. Failed monitor receipts
and FINAL are immutable. Existing Step3 sensors call one fixed read-only restricted
probe per poke; timeout/nonzero/malformed response only reschedules. The restricted
reader rechecks registered request, exact failed receipt, selected native producer,
operator writer/directory owner, retained lineage and complete live inventories.
Only active counts may change. Normal native replacement remains strict and does
its own fresh quiescence check before side effects. No automatic kill.

Files: backend cce_recovery_{evidence,service,poll}, cce_compute_dispatch, existing
main.py internal request/route; dags/cce_worker_wait.py plus existing bio_wgs/gatk;
scripts/cce_recovery_workloads/failure, cce_paired_runtime and both restricted
gate entries. New backend waiting test and focused existing runtime/DAG fixtures.
Docs04/05/07/08, implementation plan, CURRENT_STATE/TASKS and this handoff updated.
No new DB table/migration, public route, scheduler, DAG node, frontend or native code.

Validation: backend new10 RED (missing worker_observation) ->10 GREEN3.17s.
One attempted runtime selection ran ZERO tests because the runner splits arguments
and the quoted '-k A or B' expression was split; no source defect or side effect.
Corrected to exact node IDs/single-token filter, not a broad rerun. Runtime strict
Master/active-worker checks7 GREEN5.09s; actual failed-monitor/probe2 GREEN5.43s;
real Airflow six scoped cases GREEN3.05s. After the final nonce replay/direct
dispatch/entry guards, final commands via ignored task6.ps1 were:

- -Mode test -Test '/task/platform/backend/tests/test_cce_worker_wait.py
  /task/platform/backend/tests/test_cce_recovery_dispatch.py::test_due_action_keeps_single_budget_and_uses_existing_resume_generation
  /task/platform/backend/tests/test_cce_recovery_dispatch.py::test_uncertain_post_is_get_only_even_after_deadline_and_stop
  /task/platform/scripts/tests/test_p02_failure_evidence.py::test_final_active_worker_is_wait_only_then_fresh_terminal_proof'
  -Log worker-wait-backend-final:17 passed5.52s.
- -Mode test -Test '/task/platform/scripts/tests/test_p02_selected_monitor.py
  -k recoverable_failure' -Log worker-wait-entry-final:2 passed5.27s.
- -Mode dag -Test '/task/platform/dags/tests/test_cce_recovery_poll.py::test_existing_sensor_runs_one_bounded_read_only_probe'
  -Log worker-wait-airflow-final:4 passed3.03s.

Every remote invocation verified BS10610/server10610 and existing control/current
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260912-opt-4d3d24e6;
backend36ff21f87356 RO/app from20260923-step7-ae416fa/backend/backend, RO/config from
current, scanner/automatic dispatch false. Evidence uid6708 confined to
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925. Containers
cached only, network none, source RO, task scratch RW,1CPU/1GiB. Live services and
release/rollback pointers untouched. No local runtime tests, full suite, real
Kubernetes/SSH probe execution against a run, PostgreSQL contention or TTL test;
those require the remaining Task6/separate activation gates, not this checkpoint.

Known boundary: a reclaimed Worker without exact persisted terminal proof remains
ineligible, even if it might have completed. Query/unknown evidence never authorizes
replacement; persisted wait eventually exhausts to manual review. No claims of
whole Task6/P0 completion or end-to-end production readiness. Next: exact remaining
failure classifications then Step4 uncertain-SSH same-operation reconciliation,
CR04 existing UI and PG/final integration per plan. Rollback source checkpoint by
reviewed revert before activation; no data/service rollback needed for this turn.

## 2026-09-25 Task6 continuation / original controller deadline

User: next approved Task6 step, no expanded scope/redundant tests. BASE platform
72809ac / nativeffe51d4; original isolated branches retained. No production,
real rerun, main merge, push, installed policy, image/wheel build or activation.
Native source committed as d7bd741; plugin remains c0b266b. First native commit
failed because user identity was unset; command-local git -c used the existing
verified platform/history identity, without changing global Git configuration.

Changes: scripts/cce_recovery_deadline.py parses authenticated absolute deadline
and bounds poll sleeps; cce_paired_runtime validates before active-Master handoff
and passes the epoch via RecoveryCapability. Both Resume adapters pass the new
native keyword only when tagged, preserving the accepted Task5 manual ABI.
Native cce_batch_runtime._advance_recovery_view binds compute_deadline in its
existing journal and gates replacement entry/DELETE/CREATE/handoff, capping
handoff by the original budget. WGS/GATK Step3 loops no longer grant a fresh
budget after process restart. Focused new test file plus docs08/plan/state/task.

RED:11 tests exposed unconsumed deadline/absent helper, then11 GREEN6.33s.
Boundary/real-monitor checks18 GREEN12.91s. Active-Master entry2 RED showed the
deadline check must precede the reuse/handoff path (not just replacement).
Fixed that ordering;20 GREEN14.22s. Review retained old native call signature
for untagged manual Resume. Final exact selection22 passed16.25s:
task6.ps1 -Mode test -Test '/task/platform/scripts/tests/test_p02_compute_deadline.py
/task/platform/scripts/tests/test_p02_selected_monitor.py::test_direct_step3_replacement_and_observation'
-Log compute-deadline-final. These are scoped remote synthetic cases, no full
suite/local runtime tests. Duplicate final log name contains latest22 result.

Each remote run verified ssh BS10610 -> server10610; control/current still
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260912-opt-4d3d24e6;
backend36ff21f87356 RO/app from20260923-step7-ae416fa/backend/backend and RO/config
from current release, scanner/auto-dispatch false. UID6708 evidence confined to
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Cached imagea0112f0b, network none/read-only/nonroot/1CPU/1GiB. No service changes.

Deadline is controller/monitor budget: no Master/Worker kill or Job native
activeDeadlineSeconds change. Existing bounded query may return after deadline;
no subsequent recovery operation/poll receives a renewed budget. Timeout may
retain an existing intent/Job and must go to reconciliation, not auto-cleanup.
Tagged recovery requires the paired updated native source; old/default-off
manual paths remain compatible. Revert these two source commits together to
rollback development; no runtime rollback needed. Task5 artifacts/plugin remain
unchanged. Task6 OPEN: next implement max600s/original-deadline natural Worker
wait via existing Airflow persistent actions, not a gate-owned retry engine;
then exact remaining classes, Step4, UI, PG/final integration and authorized
live cloud gates. No repeated Task1–5 validation.

## 2026-09-25 Task6 continuation / frozen policy and sensor handoff

User: continue the approved P0 Task6, narrow scope and minimal tests. BASEf5c82e0
on jiucheng/runtime/CR01-cce-recovery-20260922; nativeffe51d4 and pluginc0b266b
unchanged. No production/real rerun/installation/build/main merge/push authorization
used. Original workspace and Task5 offline artifacts preserved.

Added cce_recovery_policy.py and cce_recovery_poll.py. New-run creation freezes
default-off per-adapter policy/budget; first monitor fixes the absolute deadline.
WGS duplicate registration carries that same deadline into its hash. Historical
missing policy or legacy manual next-attempt state is not backfilled; it cannot
receive automatic quota but does not block the manual registration path.
Existing internal stage POST authenticates actual DagRun/action and reuses the
due dispatcher. Existing Step3 sensors reschedule waiting/uncertain and skip old
chains after delegation, including lost-response replay when GET sees the new
monitor. Current exact monitor generation alone sets compute_terminal; preserve
queued authorization for downstream, but end the active compute fence. Second
failure uses the same two-slot journal. GATK cleanup forwards its action identity.

Changed scope: backend policy/poll/config, creation and registration services,
shared budget lifecycle and existing main routes; existing WGS/GATK DAG sensors;
focused tests and docs02/04/05/07/08/11 plus plan/state/task/handoff.
No DB migration/public endpoint/new DAG node/independent retry daemon.

RED: policy3 and poll4 initially missing modules; internal route2 and real sensor2
then exposed missing caller wiring. Second-failure2 reproduced completed-history
cleanup incorrectly blocked as pending. Fixed that shared fence. First monitor
hash replay, duplicate creation, actual GATK creation/registration, old manual
attempt compatibility and current/old cleanup identity covered by final selection.
BS10610 final backend19 passed4.70s (policy-poll-final.log), real-Airflow5
passed3.00s (policy-poll-dag-final.log). Commands: task6.ps1 -Mode test with new
policy/poll files, affected GATK confirm and two budget cases; -Mode dag with new
sensor file, WGS transport classifier and two GATK default-off sensor cases.
No redundant full suite. git diff --check passed. Preliminary RED/missing-path
discovery outputs are not acceptance; tests ran only remotely.

Fresh preflight each run: server10610; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current ->
releases/20260912-opt-4d3d24e6; backend36ff21f87356 has RO/app from
20260923-step7-ae416fa/backend/backend and RO/config from current release;
scan/auto-dispatch false. Evidence/task files confined to uid6708-owned
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925.
Offline cached containers, network none, read-only source, nonroot,1CPU/1GiB.
Master test image a0112f0b8ef003dd488c6c6ee2f13ca760c116d703e9ff7a83083e2857ce143e;
Airflow test image58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b.
Existing kernel swap-limit warning does not remove the1GiB memory limit.

Ruling: only existing sensor rescheduling/control POST owns automatic waiting;
stage-status GET stays read-only. An old sensor must reconcile even when the
latest monitor looks running, or a lost response could advance the wrong chain.
compute_terminal is separate from dispatch result_status because downstream still
needs the same action's authority. No manual Resume call is nested into auto.

OPEN/NEXT: native consumption/enforcement of original cce_recovery_deadline,
bounded natural Worker wait, exact CREATE transport/storage classification,
Step4 uncertain operation reconciliation, CR04 projection, PG contention and
final automatic integration. No complete Task6/P0 or whole-plan review claim.
Both new env switches stay false; do not activate while these gates are open.
Rollback: revert this isolated platform checkpoint; no live service/data rollback
needed. No failed biological runs were restarted.

## 2026-09-25 Task6 continuation / internal due dispatch

Same user authorization and three isolated branches as the entry below. Completed
prerequisite commits: platform abdba43/native ffe51d4/plugin c0b266b. Preserved
Task5 artifacts, installed CLI/images and unrelated original workspace edits.

Added backend/app/cce_compute_dispatch.py and focused test. Reuses existing
cce_compute_recovery RunAction, budget validator, adapter-specific registration
and cce_resume_dispatch; shared stage authorization now recognizes that same
automatic action. No new table/public route/loop/manual action. Deadline field
is preserved in WGS/GATK recovery requests. Prepared identity commits before
request writes; replay rechecks current source proof and current action under
run/action locks. Missing/changed evidence, stopped state and expiry block first
dispatch. Once POST intent exists, reconcile by GET only even after expiry/stop;
late replies do not reset the user's state. Runtime live quiescence/owner guards
remain Task4's responsibility and are not replaced by a client-provided flag.

Tests: same BS10610 offline/non-root/read-only environment and exact fresh
fingerprint below. task6.ps1 test_cce_recovery_dispatch.py:12 RED (missing service)
then12 GREEN3.50s. Two prepared-crash cases RED (proof not rechecked), fixed by
reloading action under run lock and validating original failed receipt again.
Final explicit changed-boundary selection:23 passed4.68s, log dispatch-final.log
under p02-task6-20260925 (14 new +9 affected manual Resume cases). git diff --check
passed. No full unrelated suite, local runtime tests or production database.
The kernel swap-limit warning is unchanged; container memory limit remains1GiB.

Ruling: split durable preparation from external dispatch using the same action,
not a new scheduler or a nested manual Resume call (which correctly fences a
pending automatic action). Cost if interrupted between filesystem and database
writes: adapter mismatch remains fail-closed, never an invented new generation.

OPEN: automatic Airflow polling entry point, default-off new-attempt policy/
budget freeze, native original-deadline enforcement, terminal action lifecycle,
bounded natural Worker wait, exact CREATE transport/storage classes, Step4,
UI/PG/final integration. No task-wide/final reviewer claim. This checkpoint does
not activate recovery or complete Task6/P0. Next work stays within Task6; real
TTL/capacity/AOM/alerts, installation and production require separate gates.
Rollback: revert this platform source checkpoint; no live service/data rollback
needed. Native/plugin have no changes after their prerequisite commits.

## 2026-09-25 Task6 approved prerequisite / source acceptance

Authorization: user “补齐，然后继续” approves the prior bounded Master wrapper/
logger and schema2 bridge prerequisite. No repeat approval needed. BASE platform
da6626b/native770934c/pluginb6d1fb8; existing three isolated branches unchanged.

Completed: privacy-safe complete Master error accounting and real Snakemake
lifecycle validation; handoff-v2 preflight logger; optional native FINAL phase
summary binding; restricted current-Master native FINAL + retained/live Worker
reconciliation; immutable normal receipt evidence; schema2 backend reservation
with distinct platform/native identities. Later observer generations may retain
an older verified producer, not spend another budget or relabel its native hash.
Missing/unfinished/mixed evidence and active/unknown work stay ineligible. Normal
manual monitoring still reports failures even when automatic proof is unavailable.

Files: plugin failure_summary.py, logger __init__, two focused tests; native
run_cce_master_job.sh, cce_batch_runtime.py and two existing fixture/test files;
platform cce_recovery_failure.py, cce_paired_runtime.py, cce_recovery_inventory.py,
backend cce_recovery_evidence/service.py, source/monitor tests and state/runtime docs.
No public API, table, UI, biological rule or installed configuration changed.

Test environment only: ssh BS10610 -> server10610, uid6708/gid520. Each remote
runner rechecked control `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`,
current releases/20260912-opt-4d3d24e6, backend36ff21f87356 /app read-only at
20260923-step7-ae416fa/backend/backend and /config read-only at current/config;
WGS_INTAKE_SCAN_ENABLED=false, WGS_AUTO_DISPATCH_ENABLED=false. All preserved.
New owned evidence root (no /tmp):
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925`.
Offline non-root read-only cached Master container a0112f0b, network none,
one CPU/1GiB, own writable scratch; actual Snakemake9.24.0+biosan1. Existing
Task4 backend dependency cache read-only; temporary synthetic SQLite only.

Commands: ignored task6.ps1 uploads scoped source and runs `python -m pytest -q
-p no:cacheprovider --tb=short` on the explicit selected files/nodes recorded in
prerequisite-final.log. RED/GREEN: logger4 RED/1 existing pass ->5 GREEN; native
summary3 RED->3 GREEN; preflight logger2 RED; actual Snakemake control lifecycle1
RED (two redundant shutdown ERRORs) with submission/rule2 already GREEN;
source classifier6 RED->6 GREEN; schema2 receipt/reservation2 RED->2 GREEN;
older Step3 producer observer2 RED->2 GREEN; genuine fresh monitor2 RED->2 GREEN.
Final changed-boundary suite **28 passed35.59s**, including normal receipt2 and
three real Snakemake lifecycle cases. No full Task1–5 suite or local runtime tests.

Diagnostic failures (not acceptance): initial real lifecycle fixture hit read-only
cache and missing passwd UID; fixed only synthetic XDG_CACHE_HOME/USER/LOGNAME.
Probe initially imported old testdeps Snakemake, then corrected image site-packages
precedence; two probe syntax/import mistakes corrected without production effect.
An incorrect -k selected zero tests (exit5); replaced with exact nodes. Some local
rg wildcard/nonexistent path guesses were replaced with scoped file discovery.
No unresolved test failures. git diff --check is the local non-runtime check.

Ruling: use existing verified normal status receipts for schema2 evidence instead
of adding a backend cloud reader/service or flattening native IDs. The restricted
reader already owns authenticated source/lock mapping and cloud queries. This
keeps the original plan's single budget owner; failure cost is fail-closed/manual,
never automatic authorization from arbitrary receipt JSON.

Next: continue Task6 actual due dispatch through the shared Resume dispatcher,
frozen new-attempt policy/budget, bounded worker wait, Step4 uncertain dispatch,
existing UI projection and focused PG/final acceptance. This prerequisite is not
whole Task6/P0 completion. Exact CREATE transport/storage eligibility must be
checked against the existing producer contract; no new broad retry classes.
No merge/push, production, real rerun, CLI/image installation or live cloud
TTL/capacity/AOM/alerts acceptance. Task5 accepted artifacts remain immutable;
new source needs distinct version/pins/artifacts before activation. Rollback is
source revert only; no data/evidence cleanup and no services to roll back.

## 2026-09-24 Task6 preflight / failure-summary scope confirmation

Goal: continue the approved Task6 after Task5, without repeating accepted tests
or expanding operational scope. Inspected platform83528cf/native770934c/plugin
b6d1fb8 source. Only planning/state documents changed in this checkpoint.

Verified interface gaps:

1. `backend/app/cce_recovery_service.py:reserve_monitored_recovery` expects
   `{workdir, context, evidence_scope}` and equates the candidate context to the
   platform submit execution. Actual Task4 `cce_master_binding` is schema2 with
   `platform_execution`, `native`, `source_bundle`, `selected_bundle`.
   `scripts/cce_paired_runtime.py:_exported_master` and
   `scripts/cce_recovery_inventory.py:RecoveryCapability.export_result` are the
   actual producers. Native phase execution IDs/hashes/generations must remain
   distinct from platform submit and monitor identities.
2. `cce_recovery_reader.py` consumes `master-terminal.json`; the validator demands
   authoritative fatal_source and cumulative rule/other failure counts. Scoped
   source search found no current runtime producer of that terminal contract.
   Native `_bind_master_terminal` binds RUN_FAILED/RUN_COMPLETE to a final
   submission snapshot, sets evidence_complete=false and records stage/exit code;
   `_submission_final_snapshot` explicitly does not grant automatic recovery.
   `_recovery_phase_finished` captures context and exit code, not a cumulative
   classifier proving a whitelist failure is the sole fatal cause. Worker
   inventory completeness does not prove absence of mixed local rule/other errors.
3. The existing automatic service remains an internal reservation bridge, not a
   caller/dispatcher. Policy/budget freeze, due dispatch, Step4 reconciliation,
   UI projection and PostgreSQL contention remain pending as already planned.

Ruling: preserve fail-closed behavior. Do not manufacture a terminal seal,
infer zero failures from absent events, relabel native identity, or wire generic
manual Resume as automatic authorization. Cost: automatic dispatch remains off
until the producer/consumer contract is complete; manual Task4 acceptance stands.

Proposed necessary addition, awaiting user scope confirmation: in the existing
isolated Master wrapper/logger path, capture a complete bound fatal-cause summary
that distinguishes allowlisted executor faults from mixed rule/other failures;
consume it through the existing trusted reader/monitor/reservation path. No new
service/table, biological rule change or broader retry category. Missing/incomplete
or conflicting evidence stays ineligible. New source changes would require new
artifact pins; do not overwrite or reuse Task5 accepted artifact evidence.

Checks: git status/log and scoped rg/Get-Content inspection only. No pytest,
Docker/build, SSH or remote runtime commands executed in this checkpoint, hence
no fresh hostname/current/mount/permission validation or remote test claim.
Target for eventual minimal RED/GREEN verification remains BS10610 test only;
fresh environment gate first. No local runtime substitute. No services, production,
CLI/operator policy, frozen bundles, samples or recovery budgets changed.

Files: CURRENT_STATE.md, TASKS.md, HANDOFF.md and the existing P0-2 implementation
plan; ignored plan ledger records the same finding. No unresolved command/test
failure: PowerShell rg wildcard arguments were rejected locally and replaced by
directory searches with -g; no remote retry attempted. Next: obtain bounded
producer-scope confirmation, then add targeted real-producer/consumer tests before
implementation. Rollback is a docs-only revert; preserve all source/evidence.

## 2026-09-24 Task5 closed / Task6 next

Source commits platform074dc55/native7232f57/pluginfdf1520 on the existing three
isolated branches. Details, exact wheel hashes, local image IDs, commands/results,
scope review, failure records and rollback:
docs/releases/2026-09-24-p02-task5-offline-artifacts.md.
Task5 only: generators6 RED->GREEN, affected matrix15 GREEN, packaging1 RED->GREEN;
distinct offline wheels2 and Master images2 built, actual-wheel acceptance13 GREEN
14.57s and image smokes2 passed. Snakemake9.24.0+biosan1 unchanged in both images.
Retained original evidence and accepted bs7 bytes; no old bundle/template rewrite.
All service/current/mount and scan/dispatch gates unchanged. No production, real
Jobs/data/rerun, install, push/merge, new framework or Task6 implementation.
Final current requirement/scope review found no further Important Task5 defect;
full Task4/budget/callback tests deliberately not repeated. Author scope review
does not replace the eventual whole-plan review. Next Task6 automatic recovery,
still using existing reservations/budgets/receipts. Live TTL/AOM/alerts/capacity
are separately authorized operational gates, not claimed from synthetic tests.

## 2026-09-24 Task5 source checkpoint / offline artifacts next

Existing isolated baselines platformde3b5a5/nativebd41f87/plugin5b5d7ee.
New Worker/Master/evidence readers TTL100, no Pod TTL, frozen-bundle, deadline,
restart/resource, cleanup, Step7/maintenance changes. Native test0.8.5+p02.dev1;
Master Dockerfile now includes existing sibling guard, after packaging RED.

BS10610 server10610 current20260912-opt-4d3d24e6; backend36ff21f87356 /app
20260923-step7-ae416fa/backend/backend RO, /config20260912-opt-4d3d24e6/config RO;
intake/auto_dispatch=false, uid6708. Evidence WGS_test/cce-evidence/p02-task5-20260924.
Ignored task5.ps1 uses cached network-none/read-only containers and own scratch.
Generators6 RED then6 GREEN; affected matrix15 GREEN19.76s; packaging1 RED then
1 GREEN0.22s. No unaffected budget/callback/full suite or local runtime tests.
Slow read-only cache listing stopped by exact own-process match; targeted bs7
build directory supplied cached poetry-core1.9.1, read-only. No chmod/removal.
Both cached Master bases have Snakemake9.24.0+biosan1, verified without testdeps
metadata shadowing. Distinct wheels/images and provenance remain next.
No real Jobs, service/CLI/policy install, main/production merge/push, database,
automatic recovery or real rerun. Pre-deploy rollback source revert only.

## 2026-09-24 Task4 manual closure accepted / latest requirements checked

Goal and scope: inspect existing code, finish only P0-2 Task4, then compare with
the latest approved spec and Task4 plan. No Task5 TTL/artifact or Task6 automatic
work, no production deployment, real batches, database/data edits, new API/table
or second retry engine. Existing isolated platform branch
jiucheng/runtime/CR01-cce-recovery-20260922, baseline42edd35; Task4 basef93ba00.
Native counterpart bd41f87 on jiucheng/runtime/p02-master-handoff-20260923;
plugin5b5d7ee unchanged. Commit containing this entry is the platform closure.

Completed:
- cce_paired_runtime.py: initial registered submission and interrupted original
  handoff reconciliation; active reconnect, direct Step3 replacement and post-CAS
  crash replay; authenticated producer/archive selection; actual child-process
  Step4–6 command/receipt reconstruction and final directory release.
- cce_recovery_inventory.py + existing WGS/GATK Resume: separate immutable origin
  and selected source, preserve registered lineage and original producer identity;
  sealed ancestor Worker snapshots participate in complete live reconciliation.
- Existing runtime gates: selected initial/monitor/downstream routing and WGS
  actual reattach revalidation before receipt archival. Generic JSON cannot mint
  VerifiedMasterResult. GATK approved materialization target is unchanged.
- Native cce_batch_runtime.py: generation-local final manifest projection and
  shared-history digest; no shared manifest or original bundle rewrite.
- tests/test_p02_selected_monitor.py plus new test_p02_manual_flow.py and
  p02_dag_transport.py: existing authenticated API/service, actual DAG methods in
  a separate Airflow subprocess, restricted native source, normal receipts and
  downstream success. Same attempt/action/config/workdir; one lost-response POST;
  no prepare/upload rerun. This is synthetic transport, not live scheduling.
- CURRENT_STATE/TASKS/docs08/Task4 implementation plan/P0 progress consolidated;
  old checkpoint OPEN text is historical, not current unfinished work.

Final independent code review: no Critical, three Important findings (initial
interrupted handoff, retained old Workers at release, WGS reattach receipt fields).
Five behavioral cases RED; fixed with the existing journal/evidence contracts.
First fix run3 passed/1 skipped/2 failed: remaining failure was a synthetic test
label mismatch (display label overwrote native inventory identity), corrected in
fixture without relaxing production checks; retained-Worker2 then passed7.32s.
No repeated reviewer or broad test suite. Earlier recorded service/DAG/lock tests
are reused, not rerun. Requirement-by-requirement result is in Task4's plan table.

Environment checked before each remote action: ssh BS10610, hostname server10610;
control root /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current points to
releases/20260912-opt-4d3d24e6; backend36ff21f87356 /app mounted read-only from
releases/20260923-step7-ae416fa/backend/backend, /config read-only from
releases/20260912-opt-4d3d24e6/config. scan=false/auto_dispatch=false unchanged.
Cached containers --network none --read-only --cpus1 --memory1g; candidate/native/
plugin mounts read-only, only task synthetic scratch writable. No services changed.

Final commands (PowerShell runner under ignored
.superpowers/sdd/2026-09-23-p0-2-master-handoff-ttl-implementation/selected-test.ps1):
- -Log task4-selected-final: test_p02_selected_monitor.py **41 passed,1 skipped
  in76.91s**. Skip = GATK has no separate WGS reattach-worker entry; its own actual
  recovery path is tested. Includes real forked selected monitor/downstream.
- -Integration -Test scripts/tests/test_p02_manual_flow.py -Log task4-manual-final:
  **2 passed41.32s**, dependency-only AnyIO/Starlette deprecation warning.
- Local git diff --check only (non-runtime); no local pytest or compile substitute.

Evidence root /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/
p02-task4-20260924/: task4-selected-final.log, task4-manual-final.log,
review-boundaries-red.log, review-boundaries-green.log,
review-retained-workers-green.log. Earlier implementation RED/GREEN logs retained,
including replay-chain-{red,green}, reattach-chain-red and initial-resume-green4.
Initial manual fixture/environment failures were not acceptance: missing cached
dependencies/permissions, incomplete registry fixtures, global mock sleep and
missing normal gate receipt. Corrected only isolated runner/fixtures; no install.

Test provenance: native image a0112f0b8ef003dd488c6c6ee2f13ca760c116d703e9ff7a83083e2857ce143e,
integration Airflow58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b.
Integration uses offline selected dependencies exported from cached backend
8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed and native image;
export hashes/image IDs in downstream-scratch/backend-deps/{provenance,native-provenance}.json.
Airflow subprocess retains its SQLAlchemy1.4 environment; backend uses temporary
SQLite/SQLAlchemy2, no live PostgreSQL or credentials. No wheel/image built.

Not run / remaining gates: full suites (user explicitly asked minimal affected
tests), live scheduler/SSH/native cloud operations, PostgreSQL contention, actual
TTL/AOM/capacity/notifications (Tasks5/6 and separately authorized operational work).
Task4 is manual source accepted, NOT all P0, artifact release or production-ready.
No open Task4 Important/Critical finding; unknown/legacy evidence remains blocked
by design. Production five old failed batches are not migrated or restarted.

Next: Task5 existing TTL generators and pinned artifact acceptance, then Task6;
do not enable installed GATK resume capability or operator policy automatically.
Branches/worktrees retained, no merge/push. Native commit initially failed because
its repo lacked author config; retried with per-command identity matching existing
commits, no global configuration change. Before deployment rollback is paired
source revert only; preserve records, bindings and data. After future TTL activation,
never revert to a reader requiring already-reclaimed objects.

## 2026-09-24 Task4 selected Master -> actual Step3 monitor checkpoint

BS10610 SSH restored; hostname server10610. Each isolated run rechecked current
20260912-opt-4d3d24e6, backend36ff21f87356 /app20260923-step7-ae416fa/backend/backend
RO and /config20260912-opt-4d3d24e6 RO; scanner/auto dispatch false. Same offline
image a0112f0b8ef0, user6708:520, network none, source/producer RO, task scratch
only. No service, DB, real workload, credential, policy or production change.

Scope: finish the interrupted cross-process selected-monitor slice, not all
Task4. Native903e1af adds UID/Pod/generation/platform-bound Step3 evidence from
the selected view. Platform cce_paired_runtime.py reconstructs authority from
registered producer/current request, receipt digest, native journal/handoff and
current directory lock under writer serialization. Actual WGS/GATK gate loops
use it; rule bridge gets a copied selected bundle binding. wgs_resume routes
paired Step3 into that monitor instead of the Step2-only replacement factory.
Original bundle bytes remain unchanged; no extra CREATE/START on observation.

Remote tests (scripts/tests/test_p02_selected_monitor.py; genuine os.fork):
- Prior missing-entry2 RED. Resumed draft10 cases:2 failed/8 passed. Diagnostic
  isolated missing START_CONFIRMED because the test Pod omitted Ready=True;
  corrected the transport fixture, normal2 GREEN4.13s, no relaxed identity gate.
- Actual WGS/GATK gate entry2 RED (Step2-only factory); connected monitoring.
  Fixture used invalid display run label and caught its own stop sentinel as
  workflow failure; corrected those test boundaries, gate2 GREEN4.27s.
- Old ANALYSIS_COMPLETE wrongly yielded success; reclaimed failure was routed
  to success-only reader. New terminal matrix4 RED/2 GREEN, then6 GREEN11.96s.
  Native monitor ignores run-id-only completion absent a verified new terminal,
  uses sealed final failure after Job reclaim and refuses unproven completion.
- Final focused18 GREEN30.04s. Affected registered Step2 replay2 GREEN3.99s;
  legacy worker disconnect1 GREEN1.99s; unactivated entry2 GREEN0.26s. No broad
  suites or local runtime tests. Docker swap-limit warning only.

Evidence: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/
p02-task4-20260924/{selected-monitor-final,selected-gates-red,selected-gates-green,
selected-terminal-red,selected-terminal-green,selected-registered-affected,
selected-disconnect-affected,selected-legacy-affected}.log.
Reusable scoped runner is in the ignored plan workspace selected-test.ps1.
Changed platform: cce_paired_runtime.py, wgs_runtime_gate.py, gatk_runtime_gate.py,
wgs_resume.py, new test_p02_selected_monitor.py and state/contract/plan docs.
Native changes only cce_batch_runtime.py. git diff --check passed.

Remaining Task4: direct Step3 replacement and initial-submit view selection,
selected Step4-6 execution across processes, final protected release and actual
authenticated service/DAG/native manual synthetic closure. Current monitor
requires its successful registered Step2 predecessor, otherwise fails closed.
GATK registry capability/policy not activated; no Tasks5/6 advancement. Rollback
is source revert only; there is no deployed service or data rollback to perform.

## 2026-09-24 Task4 fresh-process monitor — unverified working-tree draft

Goal: continue the existing Task4 cross-process selected-Master handoff, not TTL
or automatic activation. Last accepted platform caf87e4, native1c8fca7.
Changed scripts/cce_paired_runtime.py, added scripts/tests/test_p02_selected_monitor.py;
native p02-master-handoff-20260923/src/cce_pipeline/assets/cce_batch_runtime.py.
State/task/runtime docs and ignored progress ledger updated. All remain
uncommitted; no branch push, merge or production changes.

First BS10610 offline pytest test_p02_selected_monitor.py -k None --tb=short:
2 RED/8 deselected4.56s, missing monitor_registered. Genuine os.fork means only
registered JSON crosses the process boundary. Evidence: WGS_test/cce-evidence/
p02-task4-20260924/selected-monitor-red.log. Successful preflight: server10610,
current20260912-opt-4d3d24e6, backend36ff21f87356 /app20260923-step7-ae416fa/
backend/backend RO, /config20260912-opt-4d3d24e6 RO, scan/dispatch false.
Cached image a0112f0b8ef0, network none, user6708:520, source/producer RO and
task-specific synthetic scratch only. No runtime services changed.

Draft implementation: shared registered-request check; Step3 reads successful
Step2's registered producer, verifies raw WGS or canonical GATK receipt hash;
derives recovery journal/view rather than trusting a supplied path. Checks
journal context/platform identity, frozen hashes, native handoff and current
directory owner under writer serialization. Native Step3 optional selected-view
arguments fence Job UID/recovery context, Pod UID and startup/terminal identity,
and write only the selected mirror. No gate loop wired yet. Direct Step3 Resume,
missing-Job failure/success acceptance, downstream execution and final release
still require work; do not claim this draft is a complete consumer.

GREEN command attempted same isolated runner with this one test file (10 cases),
but SSH exit1: kex_exchange_identification read Connection reset by
172.17.61.18 port22, then UNKNOWN port65535. No preflight, source sync or test ran.
Diagnostic ssh -G BS10610 confirms host172.17.106.10/userchenjc/ProxyJumpBS;
ssh -o BatchMode=yes -o ConnectTimeout=15 BS hostname also exit1, same jump
handshake reset. No blind retries, local tests or BS96 substitution. The earlier
preflight above is not a current availability claim. git diff --check passed
both source worktrees (only CRLF warnings).

Next: after access returns, rerun only this focused file with both platform and
native runtime source synchronized; fix any real failures before actual gate
wiring, then cover the existing service/DAG path. Do not rerun accepted suites.
Rollback: only uncommitted task-owned draft hunks if necessary, preserving other
work; no data, frozen bundle, service or operator policy rollback is required.
Task4 remains OPEN. No Task5/6 advancement or production authority inferred.

## 2026-09-24 Task4 registered Step2 recovery — source checkpoint

Network restored. BS returned node005; BS10610 preflight returned server10610,
current20260912-opt-4d3d24e6, backend36ff21f87356 /app from
20260923-step7-ae416fa/backend/backend RO and /config20260912-opt-4d3d24e6 RO.
Scanner and automatic dispatch remain false. No service restart/config write.

Goal: connect registered request to the existing verified Resume capability.
Implemented in scripts/cce_paired_runtime.py, wgs_resume.py and
gatk_runtime_gate.py. Native cce_writer_guard.py validate now returns the
already-validated physical mapping (no new probe/activation mechanism).
The existing authenticated spool is the trust boundary; canonical hashes detect
changes, not authentication. Recheck request bytes before native actions/export.
Use the fixed pinned runtime and operator-approved per-run frozen registration;
do not synthesize a binding from batch name. Hold shared writer serialization,
all stage launch locks and other worker locks. The invoking restricted gate
already holds its own worker lock. Free/dead dispatcher alone does not prove
quiescence: existing state must have a matching terminal receipt. Match the old
native owner before takeover; blank new-owner binding and live replacement UID
are fenced. Missing/foreign/legacy-only lock cannot authorize this new path.
Repeated action goes through existing one-CREATE/START journal, not a new retry
engine. Original frozen files unchanged. Normal receipt carries verified result.

Validation, only BS10610 offline cached Docker image a0112f0b8ef0, network none,
read-only candidate/producer, synthetic scratch and fake Kubernetes transport:
- Initial draft6 failed/4 passed exposed GATK fixture import error as well as
  missing routing. Fixed test import path/alias, then actual entry2 RED2.87s.
- Factory/routing first10 GREEN10.76s. Real backend request review found GATK
  does not have WGS control_workdir: corrected fixture, reproduced1 RED1.90s,
  then limited that field check to WGS. No backend request schema change.
- Final pytest scripts/tests/test_p02_registered_recovery.py:14 GREEN13.78s,
  includes repeat, changed request, occupied/uncertain dispatcher, foreign or
  missing lock and absent operator registration for both pipelines.
- Existing test_unactivated_entries_preserve_old_bundle (2 cases) and
  test_wgs_resume_worker_retains_binding_when_monitor_disconnects:3 GREEN2.17s.
Evidence root /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/
p02-task4-20260924: registered-entry-red.log, registered-gatk-shape-red.log,
registered-recovery-green.log, registered-recovery-affected.log.
One green-run SSH command exited1 during jump handshake (Connection aborted),
before preflight/test. Direct BS hostname then succeeded; bounded retry ran the
test. No blind repeated launch or environment substitution.

Docs: CURRENT_STATE/TASKS/HANDOFF, docs08, Task4 plan and ignored SDD ledger.
No new public API/table; no BS96, DB, image/CLI upgrade, live workload, operator
policy installation, actual batch rerun, main/production merge or push.
Task4 OPEN: current slice is Step2 only; paired Step3 replacement explicitly
refuses until verified selected-view cross-process continuation is connected.
Still need native Step3-6 use of selected view, final protected lock release,
full authenticated service/DAG/native manual flow. Then Tasks5/6 in order.
Rollback: revert this isolated source checkpoint with its native guard return;
no deployed state or original project needs restoration. Do not enable policy
or GATK resume registry before the remaining Task4 gates pass.

## 2026-09-24 Task4 registered-entry continuation blocked before RED

Latest user-reported network restoration recheck: the same BS10610 test runner
still failed at SSH banner exchange (exit1); a single direct BS hostname probe
failed TCP connect172.17.61.18:22 (exit1). Read-only Find-NetRoute selects local
Ethernet192.168.1.144 via default gateway192.168.1.1. This locates the currently
unavailable hop, not a proven server/VPN root cause. Target health remains
unknown. No remote preflight or test ran, and no network settings were changed.

Goal: existing Task4 registered request -> verified capability -> own adapter
Resume; no extra feature, new retry mechanism, Task5/6 or production change.
Prepared WIP scripts/tests/test_p02_registered_recovery.py using existing native
adapter fixtures and real physical mapping/lock CAS, with external transport
substituted. This test draft is unverified; do not treat it as accepted coverage.
No production implementation file changed. Last accepted commit685c5b2.

Attempted command: existing gated BS10610 offline runner selecting
pytest -q -p no:cacheprovider scripts/tests/test_p02_registered_recovery.py.
Transport: ssh -o BatchMode=yes -o ConnectTimeout=15 BS10610 with the existing
base64 command/data transfer. Two attempts, both exit1 at banner exchange:
Connection timed out during banner exchange; Connection to UNKNOWN port65535
timed out. Neither reached remote preflight, sync, container or test execution.
Likely SSH transport/jump availability; no evidence of a test/code failure.
Local read-only ssh -G confirmed BS10610=172.17.106.10 via BS=172.17.61.18.
One diagnostic ssh -o BatchMode=yes -o ConnectTimeout=10 BS hostname also failed
before remote execution: connect to host172.17.61.18 port22: Connection timed
out (exit1). Thus the jump is currently unreachable; target health is unknown.
No alternate environment, credential, production host, mount or service change.

Changed only test draft and CURRENT_STATE/TASKS/HANDOFF plus ignored SDD ledger.
No source checkpoint committed while RED cannot run. Next: restore test SSH,
rerun this single draft selection, correct fixture issues if any, implement only
planned registered entry, then minimal affected checks. Do not reuse the earlier
receipt tests as proof of this new capability. Task4 remains OPEN.

## 2026-09-24 Task4 normal-receipt identity checkpoint

Goal: continue the existing Task4 route only; no new functionality, automatic
recovery, UI, public API, database table or production changes.

Completed: RecoveryCapability returns a JSON-compatible internal verified result
with an independent receipt snapshot. Both normal status writers preserve its
Master binding and submit execution ID; GATK signs them in its existing receipt
hash. Generic progress JSON cannot inject those fields. WGS Resume attaches the
result to the in-memory worker payload so terminal failure/success cannot drop
the binding. GATK return wrapping no longer discards the verified result type.
Package/standalone imports work through the same module convention. An older
successful Master's submit identity is not replaced by a new observer identity.

Changed source: scripts/cce_recovery_inventory.py, wgs_resume.py, gatk_resume.py,
wgs_runtime_gate.py, gatk_runtime_gate.py, tests/test_p02_resume_final.py.
Updated runtime contract, plan, current state, tasks and SDD ledger.

Validation: BS10610/server10610, existing control/current and actual RO app/config
mounts checked before each call; intake scan and auto dispatch remain false.
Offline read-only source containers, network none; no local runtime tests.
pytest test_p02_resume_final.py::test_verified_master_binding_survives_normal_stage_receipts:
two RED (missing field). First GREEN attempt exposed GATK result type lost in its
dict wrapper (one failure); repaired wrapper, two GREEN. Affected selection:
that pair + WGS disconnect worker + prior binding-export pair + existing WGS
status monotonicity/retry preservation = seven GREEN7.62s. Inspection then caught
observer vs submit identity distinction; refined it and reran only receipt pair,
two GREEN3.51s. git diff --check passed. No redundant whole-suite run.
Logs: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task4-20260924/
normal-receipts-{red,green,affected,observer-green}.log.

Remaining/next: trusted per-run registration/capability factory, actual GATK
Resume routing, cross-process selected-view reconstruction and native Step3-6
entry, verified final lock release, full authenticated service/DAG/native mock.
This commit only closes the in-process normal-receipt seam, not all Task4.
Tasks5/6 remain unstarted. No capability policy installed or branch merged.
Rollback: revert this source checkpoint before activation; nothing deployed.

## 2026-09-24 Task4 cloud identity and actual entry selection checkpoint

Committed source: native7026528 and platformc3cf3c2. Post-checkpoint scope check
found activated Resume could still fall through to the legacy two-argument lock
when no RecoveryCapability was constructed. Both adapter entries now reject that
path before runtime effects; the operator loader tags its validated module only
internally (not a payload field). Two adapter cases RED, final12 paired cases +3
existing result-root cases GREEN0.99s, paired-resume-denied-{red,green}.log. This
is a fail-closed checkpoint, not a completed capability factory or full Task4.

Goal: implement the approved read-only cloud directory identity source and wire
paired runtime selection without changing frozen projects or production.
Native guard/source checkpoint: readonly PVC-only reader from existing generator,
bound PVC/PV/Job/Pod UIDs, cloud symlink resolution, persisted one-CREATE intent,
uncertain-response reconciliation and conditional cleanup. Replayed foreign UID
cannot be deleted; completed cleanup does not reuse stale directory evidence.
Factory rejects bad frozen registration before any probe. Cloud10 + writer13
GREEN2.23s; details and source commit in native HANDOFF/history.

Platform adds scripts/cce_paired_runtime.py and its focused tests; actual WGS/GATK
stage command builders and Resume loaders select the operator-pinned external
runtime, preserving --bundle. Fixed policy, source hashes and root ownership;
guard sibling is pinned before importing native code. No payload/env runtime
selector and no invalid-policy fallback. GATK's direct materialization now enters
the protected writer while retaining its original approved result-root validation.
Existing prepare/Step7/maintenance mechanisms stay outside this source change.

Validation: BS10610/server10610, current20260912-opt-4d3d24e6,
backend36ff21f87356 mounts backend20260923-step7-ae416fa and config20260912-opt;
both RO, scanner/auto dispatch false. Cached imagea0112f0b8ef0 offline readonly
candidate/producer/plugin/dependencies; only synthetic scratch RW. New loader7
RED missing module -> GREEN, unactivated compatibility2 GREEN, custom GATK guard
1 RED -> GREEN; final10 new +3 existing result-root cases GREEN0.82s. Evidence:
WGS_test/cce-evidence/p02-task4-20260924/paired-{loader,materialize,entry}-*.log.
Two individual SSH jump handshake failures had bounded successful retries.
No local runtime tests/full-suite reruns; no real cloud/DB/analysis/deployment.

Task4 OPEN: this is selection/entry fencing, not automatic registration or full
Resume capability construction. Normal selected-view receipts/backend binding,
final Step6 release and real service->DAG->native synthetic closure still pending.
GATK resume registry remains disabled. Tasks5/6 not started; no TTL/capacity claim.
Next continue those existing Task4 seams, not another storage choice. Rollback:
revert isolated source commits; no deployed release/policy or data to roll back.
Docs08/02/11 and plan/ledger updated; no API/schema change in this checkpoint.

## 2026-09-24 Task4 cloud-reader identity authorization

User agreed to reuse the existing cloud read-only reader for actual SFS directory
identity, with no new host mount. Continue isolated source + BS10610 offline
synthetic verification only. This supersedes the pending mapping-choice question,
not the production rollout gates. No real reader Job, production query, CLI/image
upgrade, frozen bundle edit or deployment is authorized by this confirmation.

## 2026-09-24 Task4 CLI compatibility authorization

Latest: protected stage actual arguments now bind to original bundle/contract/
config; wrong Step6 output root rejects before side effects. New targeted RED,
final13 writer cases GREEN0.51s, protected-target-{red,green}.log. Native source
has a follow-up commit after8ec5415; no production artifacts were built/installed.

Asked user for the one remaining mapping choice before actual gate activation:
reuse existing cloud read-only reader to obtain canonical SFS identity (preferred,
no new mount), or provide an existing actual SFS mount on CLI nodes. Current host
mapping code requires that mount; BS/NFS paths are NOT proof of cloud SFS access.
No mount, new cloud probe, operator policy or real production query was performed.
Execution-plan boundary: do not silently add storage infrastructure or treat a
local NFS path as cloud evidence. Task4 OPEN; Task5/6 must not start prematurely.

User confirmed extending isolated cce-pipeline CLI Step1–Step6 protected entries,
trusted storage mapping and paired CLI/platform version checks. Authorization is
source development and BS10610 synthetic validation only. No production CLI,
image, configuration, old frozen bundle, real Job or data changes are authorized.
Task4 remains open until actual restricted gates and normal receipts are wired.

Native checkpoint8ec5415 implements the protected-entry capability and fixed
operator-owned activation reader. Source checks pins/namespace, actual mounted
symlinks+root inode/filesystem identity, frozen bundle/config hashes; shared
journal flock and existing CAS enforce entry/early-release fences. Explicit old
binding required; missing proof fails closed. No policy or mount created. This
does not prove the production all-writer inventory or complete gate wiring.
BS10610 first jump handshake reset, bounded retry passed. New9 RED -> GREEN;
actual CLI bypass1 RED -> GREEN; programmatic sibling import1 RED -> GREEN.
Final new12 GREEN0.53s, affected35 GREEN5.78s, oldStep4/5 threeGREEN0.17s.
Evidence p02-task4-20260924/protected-*.log under WGS_test/cce-evidence. Runtime
imagea0112f0b8ef0 offline/RO source; existing swap-limit warning only. No full
suite rerun, no local tests or production activity. Pending exact normal platform
registration/entry, final release, selected-view receipts and manual closure.

## 2026-09-24 Task4 selected downstream and validated binding export

Native08c6cda adds optional selected-Master bundle/UID to Step4/5/log export.
Real native completion readers validate immutable inputs and selected UID even
when TTL removed the Job; conflicting active/foreign Job blocks. All result/log
paths stay under the ORIGINAL bundle, not the independently derived Master view.
Step6 path semantics/default CLI unchanged. Native tests: five RED, then10 focused
GREEN in5.09s. Scope/details in native HANDOFF; no new templates/TTL enabled.

Platform RecoveryCapability.export_result validates native handoff and exact
platform execution before returning cce_master_binding (schema_version2) and
cce_master_submit_execution_id. Native hash/generation/UIDs and platform hash/
generation are separate fields. WGS/GATK actual Resume functions call this writer.
Dry-run readiness and unbound historical results gain no fabricated binding.
This is NOT yet connected to backend reservation or the normal restricted gate;
the older draft automatic reader still expects a different terminal schema.

BS10610 preflight unchanged server10610/current20260912-opt-4d3d24e6/backend36ff21f87356,
scan/auto disabled. Cached imagea0112f0b8ef0 offline, sources/plugin/testdeps RO,
synthetic scratch only. Binding export2 behavioral RED, then6 affected GREEN
in7.11s (24 unrelated parameter cases deselected). Initial import collection error
used an incomplete fresh source root; corrected to existing p02-resume-20260923
source, not a runtime/code fix. Evidence in WGS_test/cce-evidence/p02-task4-20260924/
binding-export-{red,affected}.log and downstream-{red,affected}.log.

Remaining Task4 boundary: actual CLI Step1/2 still call old two-argument batch lock;
Step4–6 lack v2 entry protection. Trusted actual-storage alias mapping/all-writer
version enforcement plus selected-view/receipt forwarding are required, not a
boolean from an API request. Asked user to confirm extending those CLI protected
entry points in isolated source. Do NOT activate recovery/TTL or advance Task5/6
on the strength of helper tests alone. No production data/services touched.
Rollback source commits only; preserve all original bundles and evidence.

## 2026-09-24 Task4 GATK dispatcher fence

Continue remaining Tasks4→5→6 without production changes. Added launch and worker
flocks, durable launch intent/process identity, full receipt identity and late-write
guard in scripts/gatk_runtime_gate.py. Step1–6 only; no Prepare/Step7 rewrite.
Unknown launch outcome, dead parent without terminal evidence and identity-incomplete
legacy status fail closed. A completed generation permits a registered successor;
same-generation terminal receipts never execute again.

BS10610 fingerprint: server10610 uid6708; control current remains20260912-opt-4d3d24e6,
backend36ff21f87356 mounts20260923-step7-ae416fa/backend/backend read-only, scan/auto
dispatch false. Cached image8491604ee01d, network none/read-only, synthetic scratch.
New test_dispatcher cases first failed5; then15 focused checks passed in2.77s.
Evidence: WGS_test/cce-evidence/p02-task4-20260924/gatk-dispatcher-{red,affected}.log.
One intermediate fork test hung because its fake spawn inherited the launch FD;
fixed fixture to match real Popen(close_fds=True), after inspecting/stopping only
our test container ec2f88a8e757. No data removed; live service containers untouched.
Initial SSH preflight reset once; subsequent verified connection succeeded.

Files: gate, scripts/tests/test_gatk_dispatcher_fence.py, existing terminal fixture,
runtime contract and progress documents. No full suite/local tests/production calls.
Still open: trusted native binding writer, canonical storage/paired all-writer
activation and selected-view downstream before Task4 acceptance; then Tasks5/6.
Rollback by reverting source checkpoint only; no deployment to undo.

## 2026-09-24 Task4 authorized initial Master binding source checkpoint

User explicitly confirmed adding initial Master platform execution binding, without
old bundle edits or production CLI/image changes. Native isolated worktree provides
generation-one submission view and optional internal Step2 arguments; existing
native locking/START confirmation remains. Platform and native hashes/generations
are distinct. Startup and terminal evidence bind platform identity; a bound-source
replacement requires a fresh identity, and the existing action journal pins it.

Platform changes: cce_recovery_inventory.py capability plus wgs_resume.py and
gatk_resume.py forward the new identity; test_p02_resume_final.py covers both actual
adapters/native producer, lost CREATE and unchanged one-START replay. Runtime
contract, state/task/plan/ledger notes updated. No public interface or gate enabled.

Preflight BS10610 server10610 uid6708, current20260912-opt-4d3d24e6, backend36ff21f87356
RO app20260923-step7-ae416fa/backend/backend, scan/dispatch false. No live services,
database, CCE calls or production operations. Tests in --network none/read-only
cached8491604 backend and a0112f0b Master images, synthetic scratch only.
Native new10 RED missing function and Step2 case RED missing argument; final
affected native41 passed20.59s. Two setup issues (scratch/import path) corrected
before behavioral RED. Adapter new2 RED missing propagated identity, GREEN2 in3.40s.
Evidence approved WGS_test/cce-evidence/p02-master-handoff-20260923/submission-native-final.log
and p02-resume-20260923/resume-platform-green.log. No redundant full suites/local tests.

Remaining Task4: trusted writer/canonical storage and paired-all-writer proof,
dispatcher quiescence and selected-view normal downstream receipts. Do not claim
full Task4/TTL/automatic recovery acceptance. Rollback isolated source commits only;
frozen projects, successful outputs, histories and evidence remain protected.

## 2026-09-24 Task4 GATK own service/DAG/HTTP source checkpoint

Goal: sequential remaining Tasks4–6 with minimum affected tests. Same isolated
platform worktree/branch, base373da98. Producer32aa7fb and Worker5b5d7ee unchanged.

Implemented GATK own same-attempt Resume registration, exact canonical frozen
request validation, history and PipelineStageExecution generation. Extracted
existing durable RunAction dispatch/action authorization without changing WGS
execution guard. Existing operator/CSRF endpoint routes registered adapters.
GATK stage API requires actual DagRun/action/scope and rejects old registrations;
acquire rechecks after committed lease; finalize rechecks after evidence ingestion.
GATK DAG skips prepare/upload/completed stages. No registry capability enabled.

Files: cce_resume_dispatch.py, gatk_runtime_service.py, wgs_resume_service.py,
pipeline_registry.py/pipeline_registry_service.py, main.py, bio_gatk.py, two focused
GATK tests, API/DAG contracts, plan/CURRENT_STATE/TASKS/HANDOFF. No runtime producer,
frontend, normal workflow or frozen project files changed.

Remote preflight: BS10610 server10610 uid6708; current still20260912-opt-4d3d24e6;
backend36ff21f87356 /app RO20260923-step7-ae416fa/backend/backend, /config RO current.
WGS_INTAKE_SCAN_ENABLED=false and WGS_AUTO_DISPATCH_ENABLED=false. Used only isolated
offline read-only cached-image containers, synthetic in-memory SQLite, source RO,
scratch RW; no live DB/service or cloud access. Evidence under
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task4-20260924.

Tests: new service5 RED missing entry; DAG RED missing skip result, then GREEN.
Initial service GREEN found SQLAlchemy mutable JSON alias omitted conf; copy before
assignment fixed. pytest test_gatk_resume_stage.py test_wgs_resume_stage.py
test_gatk_runtime_service.py:39 passed in5.90s (gatk-dispatch-regression.log).
Actual HTTP adapter/scope test RED WGS-only gate, then GREEN (gatk-route-green.log);
the paired WGS HTTP check passed before GATK fixture-thread correction. New finalize
control race RED then GREEN (gatk-finalize-red/green.log). Real Airflow unittest
test_gatk_resume_stage:1 passed (gatk-dag-green.log). Setup-only failures (missing
registry fixture/SQLite thread pool and initial DAG mock return) were corrected;
not counted as behavioral RED. No full-suite repetition or local runtime tests.

Open/blocking decision: initial native Master lacks recovery_context whereas the
replacement view has one. Native handoff request_hash is a bundle/manifest digest,
not the platform stage request_hash. Asked user to allow necessary isolated
cce-pipeline initial-submission platform identity binding; not yet implemented.
Do not fabricate binding metadata from arbitrary receipts. Continue Task4 trusted
writer/canonical mapping, paired all-writer+old dispatcher proof and selected-view
normal downstream receipt after that confirmation. Task5/6 not started. Existing
historical batches without evidence remain manual; no rerun authorization implied.

Risk/rollback: source-only staged capability; revert this checkpoint if needed.
No deployment/push/main merge/image/CLI changes, no data cleanup. Task4 is not
complete and this does not authorize TTL or automatic recovery activation.

## 2026-09-24 Task4 checkpoint: authenticated WGS Resume/DagRun dispatch

Goal: continue approved P0-2 Task4, starting with actual WGS service/DAG dispatch
identity, not another recovery engine. Worktree cce-recovery-impl-20260922,
branch jiucheng/runtime/CR01-cce-recovery-20260922, base f93ba00. Producer32aa7fb
and Worker5b5d7ee unchanged. Original dirty worktree/frozen projects untouched.

Completed: RunAction not_started/post_intent/confirmed journal, commit before
POST; uncertain transmitted POST or legacy missing journal uses GET only even
after404. Exact DagRun ID AND conf confirmation. Fresh run/action lock checks;
late responses cannot erase running/stop state or current-DAG failure audit.
Recovery stage/acquire/finalize calls carry actual DagRun ID and require current
action/attempt/scope/control. Slot helper commits, so handler re-locks/rechecks
before projecting acquired; already committed lease remains on refusal. Finalize
may reuse successful Step6 and retains existing receipt validation. Auth/CSRF/
role checks tested through actual FastAPI middleware with synthetic session auth.

Changed: backend/app/wgs_resume_service.py, main.py; dags/bio_wgs.py; their two
test_wgs_resume_stage.py files; docs04/05/07, implementation plan and state docs.
No new public API, DB migration, runtime capability writer or activation flag.

Environment: fresh BS10610 server10610 uid6708. Control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current symlink remains
releases/20260912-opt-4d3d24e6. backend36ff21f87356 running; /app RO from
release20260923-step7-ae416fa/backend/backend, /config RO current/config;
scan=false/auto_dispatch=false. No service mounts/data/credentials used for tests.
Test sources/results only under
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task4-20260924.
HEAD tracked backend/config/dags archived, extracted to own source, changed files
overlaid byte-for-byte. Docker --rm --pull never --network none --read-only,
1CPU/1GiB, user6708, source RO and own scratch RW. No /tmp task writes.

Commands/results, all in that evidence root (counts overlap; no full suite):
- backend cached8491604ee01d: python -m pytest -q -p no:cacheprovider --tb=short
  backend/tests/test_wgs_resume_stage.py. Initial dispatch-red.log:16 failed,
  8 passed. Five failures reached missing catalog fixture rather than the
  expected rejection; do not count those as clean product RED evidence.
- dispatch-green-attempt1.log:19 passed,7 failed only because tests expected409
  instead of existing internal400. Corrected assertions, no API workaround.
- same file -k 'old_dag or stage_handler': stage-fence-green.log,7 passed,
  19 deselected. All original26 cases thereby passed across affected groups.
- Scoped review found newer DAG failure erased, post-commit acquire race,
  reused-Step6 finalization rejection. Added5 cases before fixes; same file
  -k 'reconciliation_preserves or slot_commit or finalize_reused':
  review-boundaries-red.log,5 failed/26 deselected, then implemented fixes.
- -k 'reconciliation_preserves or slot_commit or finalize_reused or
  same_attempt_action or lost_airflow_post': review-boundaries-green.log,
  7 passed/24 deselected in2.05s. Includes5 new plus2 affected existing cases.
- Real cached Airflow58195672af68: /usr/local/bin/python -m unittest -q
  test_wgs_resume_stage. Final dag-identity-green-deps.log:3 passed; same new
  method against baseline f93ba00: dag-identity-red-deps.log,1 expected failure
  (actual DagRun ID missing). Covers actual DAG registration and existing skip
  preparation/upload behavior. No Airflow service or metadata connection.
- Initial DAG commands failed import (not application RED): image PATH picks
  Snakemake venv; /usr/local/bin/python also needs explicit
  /home/airflow/.local/lib/python3.11/site-packages in PYTHONPATH under uid6708
  and isolated HOME=/scratch. Read-only image inspection confirmed dependency
  path. Corrected test environment only; failure logs retained.

SSH intermittently reset at jump172.17.61.18:22 (mkdir/scp exit1 before action);
one initial PowerShell quote error also did not execute source sync. Switched
to literal script/base64 JSON stdin for bounded sync+test; recovered. Kernel
swap-limit warning and existing anyio deprecation only. No local runtime tests,
full regression suite, actual PostgreSQL contention, service restart, production
access, real analysis, image build, CLI installation, automatic/TTL enablement,
main/production merge or push. Scoped reviewer rechecked3 fixes with no open
Important/Critical. git diff --check passed before documentation closure.

Task4 remains OPEN: GATK own authenticated service/DAG path; trusted native
binding writer/canonical mapping and all-writer/dispatcher exclusion; propagation
of selected recovery view into monitor/downstream receipts. Do not reuse mocked
proof callbacks as a production capability or advance Task5 TTL. Next continue
these integration items under the existing plan. PostgreSQL contention remains
later acceptance; SQLite checks are deterministic boundary tests, not lock proof.

Rollback: revert this source checkpoint only. No deployed release changed, no
data/history/evidence deleted. Existing running recovery DAG code omitting ID
would be rejected after future backend rollout; backend+DAG must be paired and
old dispatchers quiesced under Task4 activation gates, not deployed separately.

## 2026-09-24 Task3 source acceptance: existing Resume + native view/lock

Native handoff/Resume primitive committed32aa7fb on its isolated source branch;
use that source together with this platform checkpoint (not installed CLI).

Verified dependency commits: platform321b0a1, producerfa1ac44, Worker5b5d7ee.
Existing WGS/GATK Resume now consumes verified final inventory, trusted lock
capability, native generation view and original adapter journals. BS10610:
capability6 GREEN; initial composition10 RED; expanded composition29 GREEN;
5 affected legacy checks GREEN. Scoped review: no open Important/Critical.
SSH recovered; latest source synced and validated, see HANDOFF for evidence.
Task3 source complete; Task4 authenticated service/DAG/all-writer construction
and selected-view propagation remain next. No automatic/TTL activation, images,
CLI install, production changes, real reruns, main/production merge or push.

Files: scripts/cce_recovery_inventory.py, wgs_resume.py, gatk_resume.py;
tests/test_p02_final_inventory.py and new test_p02_resume_final.py; runtime
contract, implementation/progress plan and state/handoff docs. Producer changes:
cce_batch_runtime.py and test_recovery_view.py, native HANDOFF. Original dirty
worktree and frozen project bundles/config/history unchanged.

BS10610 handshake initially reset at jump172.17.61.18:22 (ssh/scp exit1, no
remote action); later hostname succeeded. Fresh preflight server10610 uid6708,
control current releases/20260912-opt-4d3d24e6, backend36ff21f87356 /app RO
release20260923-step7-ae416fa, /config RO current/config, both scan/dispatch false.
Latest selected source synchronized into existing isolated cce-evidence sources.
Pinned no-network/read-only cached Docker image a0112f0b8ef0, actual producer
and plugin source, synthetic temporary files only. No service or real-data mounts.

Evidence root /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-resume-20260923:
- recovery-capability-green.log:6 passed (earlier RED6).
- recovery-resume-final-red.log: initial10 failed before implementation.
- recovery-resume-composition-attempt1.log: expanded29 passed in28.30s.
- resume-final-affected-green.log:5 passed,47 deselected in0.66s.
No full-suite or repeated GREEN run. Review-found cases authored before fixes;
SSH outage prevented their separate RED execution, disclosed rather than claimed.
Final scoped reviewer found no open Important/Critical. Static diff check passed.

Coverage includes both adapters' failed/reclaimed Master, native success create0,
unknown404 no newCREATE, foreignUID, survivingPod, unknownWorker, partialpage,
missingterminal, lostCREATE replay exactlyoneCREATE/START, actual directory CAS,
frozenbytes unchanged, missing/regressed handoff, ambiguousComplete, GATK replay
maintenance. Started journal stays monotonic and cannot reconstruct confirmation.
No production/default CLI capability construction; authenticated callbacks,
all-writer exclusion and downstream selected-view routing belong to Task4.
Rollback: revert this isolated source commit only; no runtime rollback needed.
Next: Task4 under the existing plan; Task5 TTL and real five-batch reruns remain
gated and unauthorized by this development acceptance.

## 2026-09-24 Task3 native dependency acceptance; side-effect closure still open

User approved final Worker snapshot and independent replacement-generation view
in isolated cce-pipeline, only BS10610 synthetic. Platform branch base707533b,
producer branch base7926496, pinned Worker source5b5d7ee. Original dirty worktree
untouched. Query/confirmation/native-success guards connected to current Resume;
v2 failed/missing replacement still safely blocks until verified view/lock wiring.
New final submission content validator consumes actual plugin bytes, including
empty completed phases, exact terminals and candidates; full run-label + exact
Job/Pod probe rejects unknown/active/reclaimed-without-proof/partial inventories.
Native producer captures final phase snapshot, independent hash-checked view and
current-bound reader. No public API, DB, DAG, installation, image or service changes.

Fresh BS10610 preflight same as previous entry: server10610 uid6708, control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS,current releases/20260912-opt-4d3d24e6;
backend36ff21f87356 /app RO releases/20260923-step7-ae416fa/backend/backend,
/config RO current/config, scanner=false,auto_dispatch=false; candidate writable.
Intermittent jump172.17.61.18 SSH handshake failures ran no remote commands;
bounded later retries succeeded. No BS96/production, DB or real reruns.

Evidence WGS_test/cce-evidence/p02-resume-20260923 under /mnt/biodevrwsg2/33.chenjiucheng.
Docker --rm --pull=never --network none --read-only --user6708:520 --cpus1 --memory1g,
source mounts RO, synthetic evidence/tmp RW, no secrets/live data. Cached image
8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed for lightweight checks;
a0112f0b8ef003dd488c6c6ee2f13ca760c116d703e9ff7a83083e2857ce143e for actual plugin source
composition with existing pytest pure deps RO. CCE_PIPELINE_SOURCE=/producer,
CCE_PLUGIN_SOURCE=/plugin; PYTHONDONTWRITEBYTECODE=1; pytest -q -p no:cacheprovider.

Accepted targeted evidence (not full-suite):
- resume-confirmation-red/green:15 new; resume-native-success-red/green:9 new;
  resume-ambiguous-terminal-red/green:3 new. Combined affected run31 passed.
- resume-v2-replay-red:2 failed; resume-review-red:2 failed. Replay guards,
  GATK ownership-before-START and malformed RUN_FAILED presence fixed;
  resume-review-green:5 passed including1 affected positive.
- recovery-view-red/green:6 new.
- recovery-final-red-implementation:5 missing helper errors; final producer GREEN5
  after correcting fixture namespace. Initial fixture-only failures not acceptance.
- recovery-final-consumer-red:10 new failures; missing decode field found during
  first attempted green; recovery-final-consumer-shell-green:17 passed including
  original5 +reader/content10 +shipped shell2. Shell uses actual plugin manager,
  not a full real Snakemake CLI no-op acceptance. Cached source read establishes
  Executor initialization before no-op return (snakemake-noop-*-source.log).
- recovery-live-inventory-red/green:10 new.
- review empty candidate RED1, fixed presence-based validation; review-affected
  GREEN6 =1 new +5 affected (legacy inventory/control +native shell success/failure).
Focused same reviewer found only that Important for new dependency code; fixed.
Changed files: wgs_resume/gatk_resume and tests, cce_recovery_inventory/workloads,
new p02_resume_handoff/p02_final_inventory tests, current/task/runtime/plan/handoff docs.
No full suite/local runtime test, artifact build, real cluster or deployment.

Remaining Task3: verified internal canonical-storage/dispatcher/lock capability,
existing Resume next-view/submit/START journal integration and WGS/GATK matrix.
Task4 authenticated all-writer entry points remain separate; Task5 TTL disabled.
Do not turn process-only evidence or caller-provided JSON into launch authority.
Rollback isolated commits only; nothing deployed, no data rollback needed.

## 2026-09-23 Task3 Resume guard checkpoint; consumer closure still pending

Goal: continue P0 after Task2 without operating the five failed production runs.
Existing isolated branch jiucheng/runtime/CR01-cce-recovery-20260922, base bfff46c;
original dirty D:/pipeline/airflow-demo and both producer worktrees untouched.

Implemented in scripts/wgs_resume.py, scripts/gatk_resume.py and their existing
test files: WGS unknown CREATE outcome followed by404 never issues a second
CREATE; acknowledged replacement disappearance blocks instead of recreating;
recheck exact UID/resourceVersion and frozen manifest immediately before DELETE;
owner-only O_EXCL/O_NOFOLLOW journal, file+directory fsync, preserve prior fields;
bounded delete timeout. Both adapters request unchunked Master Pod lists and
reject incomplete pages/malformed lists. GATK archived Worker NOT_FOUND no
longer grants replacement permission; compatible persisted terminal consumption
is still required later. No new API, DB, DAG, service or producer source change.

Remote validation only. Initial ssh BS10610 full preflight exit1:
kex_exchange_identification reset at jump172.17.61.18; no remote command ran.
After local test authoring, hostname retry succeeded. Fresh full preflight:
server10610 uid6708, control /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS,
current releases/20260912-opt-4d3d24e6; backend36ff21f87356 image8491604ee01d,
actual /app releases/20260923-step7-ae416fa/backend/backend ro, /config current
config ro; scanner=false/auto_dispatch=false; candidate writable. Intermittent
later test/scp SSH invocations also failed at handshake before remote execution;
bounded retries succeeded. Required source sync succeeded before each test.
No repeated cloud side effects, production fallback or local tests.

Evidence /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-resume-20260923.
Archived HEAD scripts to new source directory then copied only this task's
modified files. Docker --rm --pull=never --network none --read-only --user
6708:520 --cpus1 --memory1g, source ro, evidence/tmp rw, no credentials or live
data mounts. Cached sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed.
Command python -m pytest -q -p no:cacheprovider scripts/tests/test_wgs_resume.py
scripts/tests/test_gatk_resume.py -k 'lost_create or missing_started or
resource_version_change_during or paginated_empty or reclaimed_historical'
--tb=short: RED6 failed/1 passed, then GREEN7 passed/13 deselected0.70s.
Same two modules with negated selection:13 passed/7 deselected1.53s. Logs:
resume-guards-red.log, resume-guards-green.log, resume-guards-compat.log.
Focused reviewer found delayed-visible Failed replacement could reopen a
submitting journal. Added test RED1 then block before archival/delete. Regression
plus normal replacement/replay path GREEN2/19 deselected0.28s in
resume-delayed-red.log / resume-delayed-green.log. Total8 new +13 affected cases
accepted across these runs. Reviewer rechecked fix: no remaining important
findings for checkpoint, not Task3/production acceptance. Minor journal crash
fault injection not added; no such fault-injection acceptance claimed. Remaining
full inventory/hand-off/lock/adapter work deliberately remains open below.
No full suite or other accepted Task1/2 tests rerun. Local git diff --check only.

Remaining / next: Task3 not complete. Connect trusted START_CONFIRMED/native
terminal success, exact persisted terminals with complete submission/live
Job+Pod inventories, safe unknown-CREATE adoption, and canonical directory/legacy
lock callbacks. Task4 then covers authenticated WGS/GATK adapter/DAG/all-writer
closure. Keep frozen bundles intact. Task1 v2 writer intentionally rejects a
different Job UID in an existing handoff record: the recovery wrapper must
preserve old evidence and bind the next owner explicitly, not overwrite the
record or silently reuse old generation/digests. TTL/automatic gates stay off.

Separately recorded prior user question: Step7+local project deletion alone does
not implement platform same-batch recreation; existing project/batch dispatch and
snapshot uniqueness/reuse are still a blocker. Do not mutate DB/history or add
that lifecycle feature silently to Task3. User has not asked to execute deletion.

Risk: reclaimed Workers with no exact terminal evidence now explicitly block,
by design; no extra acceptance implied for current production. Rollback is source
revert of this checkpoint, not lock/evidence/data deletion. No push, merge main/
production, BS96 access, cloud writes, deployment or real analysis performed.

## 2026-09-23 Task2 source acceptance; five reruns are compatibility only

User corrected the previous detour: discuss how new locks support five frozen
reruns, do NOT rerun/inspect production now; continue approved P0 development.
This supersedes the prior checkpoint's request for an operational choice.
No BS96, DB, cloud Job/lock, frozen project, main/production or service mutation.

Source commits (local isolated branches, not pushed):
- Plugin5b5d7ee631cb45bf4e14877e483ec24adedd6de4,
  jiucheng/runtime/p02-worker-terminal-20260923 at canonical plugin/.worktrees/
  p02-worker-terminal-20260923. Distinct successor0.6.4+bs8.dev1, no built artifact.
- cce-pipeline7926496ea80dab9371885215bdaca81b8ccaddc2,
  jiucheng/runtime/p02-master-handoff-20260923 in its existing isolated worktree.

Worker: journal-derived exact UID/context terminal publication before callbacks;
explicit Job conditions only, unknown404 preserved; exact replay skips status
queries. Single validated journal view per poll. Cached callbacks precede quota
reads; claims remain for existing conservative reconciliation, not fake release.
Lock: optional internal extension of existing helpers, directory/logical identity,
generation/action/Master owner, journal intent before UID/RV CAS, response-loss
reconciliation, pending UID bind, conditional RELEASED record, stale-generation
fence, positively mapped legacy-key snapshot/guard before directory acquisition.
Frozen/v1 callers remain unchanged; no consumer currently opts into new locks.

Compatibility answer: keep old analysis_id/attempt/config/workdir/history and
success outputs. Future upgraded recovery entry verifies old mapping and full
quiescence then performs audited conditional handoff, not lock deletion/prepare.
Unknown mapping stops for verification. All writers for the directory must
upgrade together, including downstream stages; a legacy guard is not enough
against an old CLI using a different batch key. Actual canonical storage alias
validation, evidence verifier, existing durable journal callbacks and compatible
frozen-runtime wrappers remain Tasks3/4. No operational eligibility of any of
the five runs was determined this turn; no recent production snapshot relied on.

Preflight ssh BS10610 confirmed server10610 uid6708/gid520, control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS current
releases/20260912-opt-4d3d24e6, backend36ff21f87356 image8491604ee01d,
actual /app releases/20260923-step7-ae416fa/backend/backend ro; /config
current/config ro; scanner=false/auto_dispatch=false. Candidate and evidence
writable. No services changed, current/rollback release untouched.

Remote synthetic tests only, task source mounted ro, evidence rw, user6708:520,
--pull=never --network none --read-only --cpus1 --memory1g, no /tmp evidence:
- Plugin evidence /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/
  smk-k8s-group/p02-worker-terminal-20260923; cached imagea0112f0b8ef0,
  Python3.11 and existing pytest deps ro. `pytest -q -p no:cacheprovider
  tests/test_worker_terminal.py --tb=short`:15 passed2.20s worker-final-green.log.
  `tests/test_heavy_io_quota.py tests/test_heavy_submission_recovery.py -k
  'real_status_coroutine or container_exit_before_job_terminal or completed_p0_worker_preserves or repeated_adoption'`:
  5 passed/25 deselected1.09s worker-compat-green.log.
- Runtime evidence same WGS_test/cce-evidence/p02-master-handoff-20260923,
  cached backend image8491604ee01d. `pytest -q -p no:cacheprovider
  tests/test_directory_lock.py --tb=short`:17 passed0.29s lock-final-green.log.
  `tests/test_batch_runtime_boundaries.py -k 'batch_lock or release_lock_requires_matching'`:
  3 passed/38 deselected0.14s lock-compat-green.log.
Initial13 Worker and13 lock RED; review regressions1 Worker +2 lock RED then
GREEN. Initial namespace error was an incomplete synthetic API object, fixed
fixture without relaxing real identity. SSH/scp twice failed handshake exit1 at
jump172.17.61.18 before remote execution; after local work bounded retry succeeded,
source synced before GREEN. No local test fallback. One focused read-only reviewer
confirmed corrected cached quota callback, uncertain-write journal retention and
retired-generation fence; no remaining important findings in this bounded scope.

Changed Airflow docs only: CURRENT_STATE, TASKS, HANDOFF, docs08, docs46,
P0-2 implementation plan and existing progress ledger. No API/DB/DAG change.
Not run: full suites, minikube/live CCE, build/install, real batch reruns. These
are outside source-level Task2; artifact/TTL acceptance remains Task5. State and
runtime documents updated with source IDs and remaining activation gates.
Next Task3 trusted runtime Resume/inventory/legacy mapping, then Task4 all manual
adapter paths. Task2 SOURCE PRIMITIVES complete, not P0/production-ready rerun.
Rollback: revert isolated commits only; no service rollback or data restore.

## 2026-09-23 Task2 RED checkpoint; five legacy failed-run question

User requested next step. Read current plan/spec/runtime and canonical plugin
AGENTS/skill; isolated source edits, synthetic BS10610 only. Fresh preflight:
server10610 uid6708, current releases/20260912-opt-4d3d24e6, backend36ff21f87356
image8491604ee01d and /app releases/20260923-step7-ae416fa/backend/backend ro;
/config current/config ro; scanner=false and auto_dispatch=false. Candidate
writable. No services changed; no production/cloud/DB/real-data action.

Remote plugin worktree snakemake-kubernetes-bs6-heavy-p0-20260923 is clean
25297f971dd463176d5fdc07908a60095ade50ea, branch bs7-control-reconnect.
Read source HANDOFF (no AGENTS there); exported exact HEAD bundle, fetched into
canonical D:/pipeline/snakemake-executor-plugin-kubernetes without checkout changes,
then created its .worktrees/p02-worker-terminal-20260923 on independent
jiucheng/runtime/p02-worker-terminal-20260923. Native worktree tool cannot target
the other repository, so Git fallback used after ignored-directory check.
Original canonical detached8a6187d and other worktrees remain untouched.

New tests/test_worker_terminal.py only,13 tests exercising real submission journal
and status coroutine with synthetic Kubernetes transport. BS10610 command:
python -m pytest -q -p no:cacheprovider tests/test_worker_terminal.py --tb=short,
inside cached Master a0112f0b8ef003dd488c6c6ee2f13ca760c116d703e9ff7a83083e2857ce143e,
--rm --pull=never --network none --read-only --user6708:520 --cpus1 --memory1g,
read-only source and existing pytest deps mounts, TMPDIR task evidence.
Result13 expected behavioral failures2.53s (worker-red.log); missing durable
terminal before callbacks, false success without final Job condition,404 failure
instead of unknown, no restart reuse/identity/conflict/write-failure safeguards.
No implementation or GREEN yet; do not mark Worker half or Task2 complete.
Evidence /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/smk-k8s-group/p02-worker-terminal-20260923.
No full suite, wheel/image build/install or live CCE tests (plan forbids them now).

Asked user: enable new directory/generation-aware locks only with CLI/platform
co-upgrade and keep unknown legacy locks, versus retain legacy same-name mutex.
User replied with five failed runs requiring rerun, not a choice or authorization
to modify them. Read original workspace HANDOFF/OPS_P0_1_PREFLIGHT_20260923.md
and OPS_RECOVERY_AUDIT_20260923.md without editing their dirty files. Thread
read tool returned empty items, so it supplied no current operational facts.
Latest documented snapshot12:04UTC: WGS0921D Master Complete, four others absent;
B/E journal/handoff mismatch; C/WES no current final evidence; native manifests
empty. This is historical, not this turn's live cloud state or rerun approval.
Advice: prioritize D final-result/downstream reconciliation, then resolve exact
legacy identity/Worker evidence for B/E/C/WES; keep attempts/inputs/successful
stages, no forceall/frozen-bundle rewriting/fabricated evidence. New lock rollout
must not be a prerequisite or silent migration of these historical tasks.

Next: answer user's legacy-run question and obtain the needed operational/lock
choice; continue from the13 RED tests, do not redo Task1/bs7 suites. Runtime
lock source unchanged. Rollback draft: remove only own test through normal Git
editing if abandoned; no live rollback needed. No main/production merge or push.

## 2026-09-23 P0-2 Task1 Master producer completed, source only

Goal: user said complete Task1 first and briefly explain completion/method.
Used existing implementation plan, runtime/planning, TDD, focused code review,
verification and handoff skills. No automatic-policy/Task2 scope expansion.

Producer: cce-pipeline c33740dea3a94e8ee3633592aba1b111948171b3, base83e7adbff9e94b99da34f687903cb4ee9df9f996,
branch jiucheng/runtime/p02-master-handoff-20260923,
worktree D:/pipeline/cce-pipeline-worktrees/p02-master-handoff-20260923.
Remote original source was verified tracked-clean; its two untracked audit
files preserved, independent branch created and operations owner informed.
Changes: existing runtime handoff/reader; master manifest identities; Master
entrypoint confirmation/terminal trap/process claim; Dockerfile helper copy;
targeted tests, two downward-env fixture assertions and producer contract doc.
Airflow changes this turn are six documentation files only: STATE/TASKS/HANDOFF,
docs08, existing P0 progress ledger and P0-2 implementation plan. No API/DB/DAG.

Handoff schema2 binds frozen run/attempt/generation, exact Job/Pod UID and
request/config/metadata/manifest digests. START_SENT persists before send;
Master verifies inputs and confirms before Snakemake. No ack means structured
handoff_timeout, not rule failure or permission to restart. Lost-response replay
does not resend; original timely ack is usable after controller restart/deadline.
Completed Pod reads use existing persistent reader. Same-Pod O_EXCL claim runs
before setup/failure trap. Native success checks preserved; trusted catchable
setup/analysis failures recorded, pre-trust/hard-kill cases remain unknown.
Terminal process evidence_complete=false; it is not a Worker-finality seal.

Environment: ssh BS10610, hostname server10610, uid6708/gid520. Control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current release
releases/20260912-opt-4d3d24e6. Actual backend36ff21f87356 /app read-only mount
releases/20260923-step7-ae416fa/backend/backend; /config current/config read-only.
Scanner=false, auto_dispatch=false. Task candidate and evidence writable.
No services changed; no release switch, rollback release change or DB access.
Cached image sha256:8491604ee01d9b3a84d74e7edf233a9d5dd20ddbf14f8a646c25c05f8729efed
ran isolated --network=none --read-only, uid6708:520, source/candidate read-only,
task tmp as /evidence with TMPDIR there,1CPU/1GiB, no image pull.

Evidence root /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-master-handoff-20260923.
Final commands/results (full invocation also in producer HANDOFF):
- pytest -q -p no:cacheprovider tests/test_master_handoff.py --tb=short:
  24 passed16.76s, task1-final-green.log.
- Targeted test_batch_runtime_boundaries, test_analysis_complete_contract and
  test_prepare_bundle schema3 case, -k step2/handoff/wait_pod/AnalysisComplete/
  schema_three/reader_job/pod_evidence/mirror/evidence_is_persisted:
  18 passed32 deselected0.92s, task1-compat-final-green.log.
Behavioral RED captured before each narrow implementation; fixture CRLF issue
corrected before counting Master behavior RED. Focused review's3 findings got
RED/GREEN: expired control restart, terminal-Pod reader and atomic process claim.
Later intermittent scp/SSH attempts failed exit1 at jump172.17.61.18 handshake
(reset/aborted), no remote execution; after static/doc work bounded attempts
succeeded, final exact sources recopied and tested. No local-test substitution.

Not run: full suites, image/wheel build/install, real Kubernetes or biology,
shared test service deployment, production. These remain future compatibility/
artifact/authorized operational gates, not required Task1 source tests.
Next planned Task2 verifies plugin25297f9 ownership, implements Worker terminal
and logical-run lock handoff. Tasks3–4 adapters/manual recovery, Task5 artifacts/
TTL and Task6 automatic remainder stay open. Old bundles untouched, TTL unchanged.
Risks: source requires paired controller/new Master image before promotion;
unknown CREATE/missing Job still fail closed. Rollback isolated commits only;
no live resources/data need rollback. Both branches committed locally, no push.

## 2026-09-23 P0-2 plan and lock-contract integration; blocked before code

Goal: user requested development steps and execution of latest P0 changes.
Used writing-plans/executing-plans and runtime/planning/handoff skills. Existing
CR01 worktree at e921e3a retained; original dirty operations worktree untouched.
Integrated design revisions a1af96a/729564c/781877e selectively, preserving this
branch's existing quota/RPC coverage. Added docs46 TTL companion and P0-2 plan;
updated original spec, STATE/TASKS and existing progress ledger (seven docs).
Plan explicitly requires producer-first manual closure, P0-2E conditional lock
handoff and compatible consumers before TTL; automatic P0 remains subsequent.

Target test only, ssh BS10610. Both bounded read-only preflights failed exit1:
first Python stdin preflight and later `ssh -o BatchMode=yes -o
ConnectionAttempts=1 -o ConnectTimeout=10 BS10610 hostname` returned
`kex_exchange_identification: read: Connection reset`, jump172.17.61.18:22.
No remote command executed; no fresh hostname/current/mount/permission evidence.
Do not reuse earlier successful fingerprints as this turn's verification.
Operations task supplied prior runtime path
/mnt/biodevrwbi/33.chenjiucheng/project/worktrees/huawei-cloud-runtime-master-errors-20260923,
HEAD83e7adb with uncommitted prototype, and plugin25297f9 path. These snapshots
are not current ownership/provenance acceptance. Preserve all existing work.

No product code or new tests written/run. Task1 targeted runtime tests and all
later implementation checks NOT RUN: remote gate unavailable and producer
baseline unverified. No local runtime fallback, production connection, real data,
cloud resource mutation, service change, image install or policy activation.
Planning/static document checks do not establish functional acceptance.
Static checks: `git diff --check` passed; relative Markdown links in the new
plan, updated spec and docs46 resolved; changed-path review contains only the
seven intended Markdown documents. No implementation acceptance claimed.
Next: restore BS10610 access, inspect exact source status/remotes/HANDOFF and
prototype ownership, pin source, run Task1 RED then implement in that scope.
Risk: short TTL before evidence/lock consumers would destroy recovery inputs;
do not activate it. Rollback: revert this documentation commit only; no runtime
rollback/data recovery required. Independent branch commit only, no shared push.

## 2026-09-23 next step: current-attempt stage receipt projection

Goal: continue existing CR-03 observer/receipt fences fromfdef310. Used backend,
runtime, executing-plans/TDD/verification and handoff skills. No scope expansion,
local runtime testing, deployment, shared service/DB access or production action.
Changed backend/app/{wgs_observer,gatk_runtime_service}.py and new
backend/tests/test_cce_recovery_receipt_projection.py. Updated STATE/TASKS,
runtime contract and existing P0 ledger. API/DB schema unchanged.

Both stage-status paths now hold refreshed AnalysisRun lock through validation
and projection, refresh execution state and reject old attempt/generation.
GATK obtains lock after its separate evidence sessions to avoid nesting those
sessions under this new lock. Existing current terminal transitions preserved.
Scope is receipt projection only: rule/workload/transfer paths, trusted terminal
writers, binding/dispatch/adapters, Step4 and real concurrency remain pending.

Fresh test preflight: ssh BS10610 ->server10610 uid6708; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current20260912-opt-4d3d24e6;
backend36ff21f87356 image8491604ee01d; actual /app readonly
releases/20260923-step7-ae416fa/backend/backend and /config readonlycurrent/config.
scan=false/auto_dispatch=false; own candidate writable, no permission changes.
C=control/candidates/p0-airflow-recovery-20260922. Only exact changed source/test
files copied. Tests run cached backend image network-none/read-only1CPU1GiB
with64MiB tmpfs and C/backend plus stage YAML readonly. All services preserved.

Commands/results (python -m pytest -q -p no:cacheprovider ... --tb=short):
- backend/tests/test_cce_recovery_receipt_projection.py: first fixture attempt
  failed setup because required synthetic workdir was omitted; fixed fixture.
  Behavioral RED4 failed/4 passed0.70s; C/receipt-projection-red.log.
  GREEN8 passed0.79s; C/receipt-projection-green.log.
- backend/tests/test_gatk_runtime_service.py plus
  test_wgs_observer.py::test_step3_terminal_execution_freezes_dry_run_master_identity
  and ::test_step3_retry_generation_replaces_prior_failed_projection:
  GREEN5 passed0.73s; C/receipt-projection-compat.log.
- git diff --check passed. Only expected kernel swap-limit warning.

No full suite (user requests targeted tests); no PostgreSQL concurrency test or
end-to-end recovery claimed. This does not enable recovery or complete P0.
Next: existing trusted runtime terminal/binding and automatic dispatch/adapter
integration; retain remaining evidence-projection/Step4 checks. Independent
CR01 branch only, no push/main/production merge. Rollback is source revert;
no runtime rollback, data restore or service restart needed.

## 2026-09-23 next step completed: control inventory + bs7 actual fixtures

User requested next step; resumed26d62dd and the10 drafted inventory cases,
no scope expansion. Used runtime, executing-plans/TDD/verification and handoff
skills. Original ops workspace untouched. No local runtime tests or production
commands. Existing independent CR01 branch retained; no merge/push/deployment.

Changed scripts/cce_recovery_inventory.py and its test: recognize agreed control
candidate separately; all referenced Workers must already be CREATED/ADOPTED
under bound context, UID from journal matches complete schema2 manifest. A null
control UID retains the known journal UID; foreign UID or missing Worker cannot
be inferred away. Reject any mixed FAILED submission and unresolved inventory.
No fake INTENT/FAILED entries or control-based release. Count cumulative control
faults as executor_failure_count. Inventory remains snapshot-only, not finality.
Added backend/tests/test_cce_recovery_bs7_contract.py with immutable hashes for
four real-wheel-generated fixture scopes; terminal positives synthetic only.
Updated runtime contract, STATE/TASKS and P0 ledger; design scope unchanged.

Fresh preflight ssh BS10610: server10610 uid6708; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current20260912-opt-4d3d24e6;
backend36ff21f87356 image8491604ee01d, /app readonly20260923-step7-ae416fa/backend/backend,
/config readonlycurrent/config. scan=false/dispatch=false. Own C writable,
C=control-root/candidates/p0-airflow-recovery-20260922; no permissions changed.
Only exact source/tests copied to C; isolated cached containers network-none,
readonly root/mounts,1CPU/1GiB, tmpfs. Shared services/data unchanged.

Test commands use cached backend image python -m pytest -q -p no:cacheprovider,
PYTHONPATH=/candidate/backend:/candidate, C/backend and C/scripts readonly:
- scripts/tests/test_cce_recovery_inventory.py -k control_candidate --maxfail=1
  --tb=short: RED1 failed/26 deselected0.05s, unsupported schema as expected;
  C/control-inventory-red.log.
- Same file -k 'not actual_bs5' --tb=short: GREEN34 passed/2 deselected0.05s;
  C/control-inventory-green.log. Covers10 new plus24 affected existing cases.
- backend/tests/test_cce_recovery_bs7_contract.py --tb=short with bs7 wheel and
  fixture root readonly mounted: GREEN4 passed0.08s, no skips;
  C/bs7-contract-green.log. No redundant plugin full suite or DB tests.
- git diff --check passed. Expected container kernel swap warning only.

Plugin owner requested help executing its already-reviewed guarded finish/build
because its SSH handshake failed while ours worked. Read local finish-candidate.sh
and remote build-candidate.sh completely; executed once after hostname/uid/base/
branch/dirty whitelist guards. No source edits by this task in plugin repo.
Finish source: D:/pipeline/task-artifacts/plugin-bs7-control-reconnect-20260923/finish-candidate.sh.
Remote worktree: /mnt/biodevrwbi/33.chenjiucheng/project/worktrees/snakemake-kubernetes-bs6-heavy-p0-20260923.
New commit25297f971dd463176d5fdc07908a60095ade50ea (11files); clean
jiucheng/plugin-bs7-control-reconnect-20260923. bs6 ref remains
0b19bb605cdff619a7f09b34a6fe774e4b43d357. Owner owns final producer handoff.
Build ran offline with fixed cached image;52 affected actual-wheel tests passed
5.60s (test_control_recovery.py,test_heavy_io_quota.py,test_heavy_submission_recovery.py).
No runtime install, image replacement, registry push, live cluster or bs6 overwrite.

E=/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-bs7-control-reconnect-20260923.
Artifact E/build-25297f971dd463176d5fdc07908a60095ade50ea/wheel/snakemake_executor_plugin_kubernetes-0.6.4+bs7-py3-none-any.whl
SHA256=2ad4aa737e6f34930b6832e3ce69edd9ee64867cc9c7ce0c1bcb4c455cdbae86.
Fixtures E/consumer-fixtures-v1: wgs-get-lease,wgs-list-pod,gatk-get-lease,gatk-list-pod;
20 fixture files checksum OK. SHA256SUMS hash
de1b3ab20d888f9660c38b8dce037333ce3ce3b0b81b66fbf79563832b780296;
fixture-provenance.json hash74102da1e10cab3728bed6f1caf31eb4bf1a0d08ed42c6002b01d1048041f83f.
E/build.log, build-<commit>/wheel-tests.log and consumer-fixtures-generation.log
retain provenance. CREATE/ADOPT fixtures use real plugin paths with synthetic
external API, no clinical data. No terminal seal generated.

Remaining: D RPC500 source-call confirmation, structured query failure (generic
kubectl still unknown), complete trusted terminal closure, binding/dispatch,
observer generation, Step4 and PostgreSQL/end-to-end acceptance. No new audit
track or weakened proof. Automatic recovery stays disabled; P0 NOT complete.
Rollback: revert this source slice; no service/data rollback needed. Plugin
artifact is isolated and uninstalled; keep bs6 unchanged. Next task resumes the
existing P0 integration from these pinned contracts, not another fixture rebuild.

## 2026-09-23 next control-inventory slice: remote preflight/transfer blocked

Completed first slice is commit26d62dd. Continued existing P0 control-inventory
integration while owner builds bs7; added10 synthetic cases to
scripts/tests/test_cce_recovery_inventory.py (known/null candidate UID retains
admitted journal UID; foreign/missing/unresolved/mixed inventory and broad/write
query rejection). This next slice has NOT run RED/GREEN and no inventory product
code changed. Test draft retained in worktree, not counted as accepted.

SCP of this single test to the same isolated BS10610 C/scripts/tests failed at
jump172.17.61.18:22: kex_exchange_identification/banner Connection aborted,
exit1. The following already-composed isolated RED command also failed before
remote execution at the same handshake, exit1; no pytest result or new remote
log. Stopped further attempts, no local/BS96 substitute or SSH config edits.
No evidence that source was copied or remote environment changed. Resume with
fresh BS10610 preflight, copy test then observe RED before inventory implementation.
Plugin owner reports108 source tests passed (86baseline+22new), but actual bs7
wheel/fixture handoff remains pending and those results are not our acceptance.
No change to26d62dd verified claims, no production/service actions or deployment.

## 2026-09-23 current disconnect types: first bounded implementation slice

User requested adding today's WGS B/C/D/E and WES disconnect gaps, then
continuing P0. Base670b50e, independent CR01 worktree/branch. Runtime, scoped
planning, TDD/verification and handoff practices used; no production authority
inferred. Original airflow-demo dirty ops workspace preserved.

Completed: bio_gatk input/result slot sensors retry only the existing transient
backend classifications, six retries30s exponential capped5m. Original48h
timeout and exact analysis/attempt/transfer request retained. The existing
backend acquisition primitive is already idempotent; no primitive change.
Other stage POST/SSH/upload/CREATE/publish/release/finalize retries unchanged.
Tests cover actual DAG settings/request bytes/permanent401/403/409 rejection,
and same-identity lost-response reacquire/no other-owner slot takeover.

Added separate agreed executor-control-failure.v1 validation in existing
cce_recovery_evidence.py and fixed-path reader. HEAVY_SLOT_API_UNAVAILABLE
accepts only exact Lease GET or Worker Pod LIST, phase heavy_slot_refresh,
typed CONNECTION_REFUSED enum, integer1..3 original-operation attempts,
retry_scope same_operation, retryable/exhausted true, creation_state UNKNOWN.
UNKNOWN never means absent. Existing complete terminal/UID/zero-active-work
requirements remain; control fatal_source is executor_control. Mixed candidate
files, filename/schema mismatch and directory changes during read reject.
No route, binding, dispatcher or automatic enablement added. New test file
backend/tests/test_cce_recovery_control_evidence.py uses explicitly synthetic
terminal scaffolding, not evidence of an actual producer terminal.

Failure evidence clarification from existing authorized ops owners only (no
production queries by this task): B/C were quota GET Lease errno111; one E
failure was quota release -> _finished -> exact Worker Pod LIST errno111.
Other E generations had old-active-Worker guard, Ready wait and unclassified
kubectl failures; C later generation and WES also have swallowed query reasons.
D archived HTTP500 Status.message is a string containing RPC Unavailable and
peer reset; exact CREATE source chain still needs verification. Do not convert
all failures in one batch or generic500 into one automatic category.

Plugin owner WGS-cloud-plugins task019f9d79-be3f-7701-af33-3595d72bbfac received
confirmed control schema and is implementing a distinct bs7 source/artifact.
bs6/wheel/86-test results remain immutable. Requested actual producer-generated
GET/LIST fixtures with admitted Worker journal/checkpoint/manifest. No fake
control INTENT/FAILED submission events. Existing inventory helper STILL rejects
control schema; actual artifact and inventory integration are the next slice.
WES gate generic kubectl error still cannot classify transient vs permanent;
cce-pipeline structured-query producer ownership/baseline remains to be resolved.
No extra Master audit framework, no frozen runtime edits or relaxed quota.

Test environment: fresh ssh BS10610 hostname server10610 uid6708; control
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current release
20260912-opt-4d3d24e6. Backend36ff21f87356 image8491604ee01d mounts readonly
/app from20260923-step7-ae416fa/backend/backend and /config from current/config;
scan=false, auto_dispatch=false. Own candidate writable; unchanged permissions.
C=control-root/candidates/p0-airflow-recovery-20260922. Only changed source/tests
copied there; Docker network=none, readonly mounts/rootfs,1CPU/1GiB, tmpfs.
No shared DB/service/restart, production access or live analysis mutation.

Commands/results (logs in C; counts overlap, not an aggregate unique total):
- Cached Airflow58195672af68 image, /usr/local/bin/python
  /candidate/dags/tests/test_gatk_network_retry.py: RED7 methods/1failure0.878s
  (gate retries0), GREEN7 passed0.869s; gatk-slot-{red,green}.log.
- Cached backend8491604ee01d, python -m pytest -q -p no:cacheprovider
  backend/tests/test_cce_recovery_control_evidence.py --tb=short --maxfail=1:
  RED1 failed0.07s (unsupported schema), control-evidence-red.log.
- Control file plus test_cce_recovery_reader.py and test_wgs_transfer_lease.py,
  -k 'control or fixed_bound_pair or lost_acquire_response or cannot_replace_directional':
  GREEN26 passed/31 deselected0.58s; control-evidence-green.log.
- New -k masquerade --maxfail=1: RED1 failed/22 deselected0.12s,
  control-schema-red.log; filename/schema mismatch was not rejected.
- After fix, control + reader files -k 'masquerade or single_stable or symlink
  or nonregular or traversal': GREEN26 passed/24 deselected0.07s,
  control-reader-green.log. Expected container kernel swap-limit warning only.
- git diff --check passed. No local runtime tests, full regression, real cluster
  canary, PostgreSQL concurrency or actual new-plugin acceptance run: excluded
  to keep scope bounded; new artifact is not yet delivered.

Docs changed: design, DAG/runtime contracts, P0 ledger, STATE/TASKS/HANDOFF.
Next: actual bs7 evidence+inventory integration; existing query/dispatch/adapter/
observer-generation/Step4 work and focused remote acceptance. P0 NOT complete.
Automatic policy stays disabled until complete trusted runtime proof and wiring.
Rollback: revert this isolated source commit; no deployed release or data rollback
needed. No main/production merge/push/deploy in this slice.

## 2026-09-23 CR-03 old DagRun cleanup protection

User next step; base3b3e142, independent jiucheng/runtime/CR01-cce-recovery-20260922.
Coordinator confirmed no overlapping ownership and approved isolated synthetic
validation only. Used existing execution plan, backend/runtime/DAG and handoff
skills. Changed cce_recovery_budget.py, main.py cleanup request/handlers only,
bio_wgs.py and bio_gatk.py cleanup payloads; added backend cleanup fence tests,
actual DAG identity tests, updated four affected legacy WGS DAG tests. Updated
API/DAG/runtime docs plus CURRENT_STATE/TASKS/this HANDOFF/P0 progress ledger.

Current pipeline/attempt + refreshed AnalysisRun FOR UPDATE precedes external
cleanup. Shared failure-fence predicate rejects superseded ID, missing identity
with current recovery history, ambiguous/reserved/unbound action. Queued or
uncertain exact current target may clean up; WGS manual resume_action_id is
also required. No new table, policy or graph changes. Transfer must still be
terminal; current ID does not grant early release. Runtime receipt ingestion,
lease primitive, activation and Local/SGE launchers unchanged.

Found partial release primitive commits before retained-slot projection. A
focused forced-interleaving test reproduced stale current_stage overwrite;
WGS now re-locks/rechecks after that partial commit before further mutation.
Earlier valid terminal-slot release is not rolled back if later identity
changed. Separate observer request checks identity again. These tests are not
PostgreSQL serialization proof. No full-scope completion claim.

Fresh test preflight: ssh BS10610 -> server10610 uid6708, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current20260912-opt-4d3d24e6.
Backend36ff21f87356 image8491604ee01d actual /app readonly from
releases/20260923-step7-ae416fa/backend/backend; /config current/config readonly.
scan=false/dispatch=false. Own candidate writable; no permission changes.
No shared services, databases, live runtime or BS96 accessed/mutated. No active
run query needed for network-none isolated containers, no shared deployment.
Candidate C=control-root/candidates/p0-airflow-recovery-20260922.

Backend command: docker run --rm --pull=never --network=none --read-only
--cpus=1 --memory=1g --tmpfs /tmp:rw,size=64m, readonly C/backend and stage YAML,
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/candidate/backend; cached backend image,
python -m pytest -q -p no:cacheprovider <selection> --tb=short.
- test_cce_recovery_cleanup_fence.py --maxfail=1 initial setup ERROR1: synthetic
  fixture omitted required workdir, corrected fixture only; cleanup-fence-red.log.
- Same selection RED1 failed1.22s: stale cleanup not rejected;
  cleanup-fence-red1.log. GREEN23 passed1.67s; cleanup-fence-green.log.
- Added only test_partial_release_rechecks_identity_before_changing_run_projection:
  RED1 failed1.27s, GREEN1 passed1.26s; cleanup-partial-{red,green}.log.
  Only affected case rerun for that fix, not the whole 23-case matrix.
- Extended the existing manual-identity test for an unbound target: both request
  and current dag_run_id absent must not compare equal and authorize drain.
  RED1 failed1.48s; added explicit nonempty ID requirement. Only this case and
  legacy-no-recovery compatibility rerun: GREEN2 passed,22 deselected0.98s;
  cleanup-manual-unbound-{red,green}.log. No additional callback semantics changed.
- test_wgs_only_platform.py -k 'test_internal_runtime_uses_4_1_1_stages_and_releases_transfer_lease
  or test_final_lease_cleanup_does_not_release_another_active_run
  or test_internal_step3_observer_activation_and_drain_are_exposed_in_run_detail'
  GREEN3 passed,62 deselected2.28s; cleanup-legacy-green.log. Existing anyio
  BlockingPortal deprecation warning; all docker runs show kernel swap warning.

DAG command: same isolated limits, tmpfs128MiB, C/dags readonly, AIRFLOW_HOME
and SQLite metadata in tmpfs; cached58195672af68 image entrypoint
/usr/local/bin/python /candidate/dags/tests/<file>. No live credentials/DB.
- test_cleanup_dag_identity.py initial ERROR: candidate missing bio_wgs.py;
  copied unchanged source. Next run incomplete synthetic conf lacked resume_stages
  (3errors+3failures); corrected fixture, no product workaround. Clean RED:6
  subcase failures across2 methods,3 methods total2.798s (missing actual run_id).
  Logs cleanup-dag-red.log, cleanup-dag-red1.log, cleanup-dag-red2.log.
- GREEN3 methods2.952s, then final lease payload coverage added: GREEN3 methods
  2.812s (cleanup-dag-green.log / cleanup-dag-green-final.log).
- test_bio_wgs_dag.py BioWgsDagTests.test_step3_terminal_status_requests_observer_drain
  BioWgsDagTests.test_release_leases_always_requests_final_observer_drain
  BioWgsDagTests.test_release_leases_fails_closed_when_backend_retains_a_lease
  BioWgsDagTests.test_directional_release_task_fails_closed_when_evidence_is_not_terminal:
  GREEN4 passed (cleanup-dag-legacy-green.log). Fixtures now have actual run_id;
  old release-before-drain ordering assertion aligned to existing safe ordering.

Unique24 new backend+3 legacy endpoint+7 DAG tests. No full suite, local runtime,
PostgreSQL concurrency, plugin suite or live recovery: user requests scoped
minimum verification. No push/merge/deployment. Future approved release must put
backend API before DAGs. Rollback source commit only; no data/service rollback.
Next: dispatcher/adapter continuation and observer generation projection under
existing CR-03, trusted terminal closure/Step4/concurrency/end-to-end still open.
Automatic recovery stays off. No extra Master audit track added.

## 2026-09-23 CR-03 old DagRun failure callback protection

User next step; base04a2530, independent CR01 branch. Used executing-plans,
backend/DAG and handoff skills for the already approved callback fence. Coordinator
confirmed these narrow files unowned and Step7 test window released; no shared
service change requested/performed. Changes: cce_recovery_budget shared guard,
wgs_submission_service and gatk_runtime_service terminal entries; main.py only
GATK request field/forwarding; bio_gatk only callback run_id. Two test files plus
API/DB/DAG and progress/state docs. No Step7/observer/lease/runtime/clinical code.

Callback takes refreshed AnalysisRun FOR UPDATE. Superseded DagRun, ambiguous
action attempt, identity-less recovery callback or pending unbound action returns
ignored without state/history/timestamp mutation. reserved never authorizes a
new failure; queued/uncertain with exact action target and current DagRun retains
prior terminal behavior. Completed recovery history still requires callback ID;
unrelated attempts and legacy callbacks retain behavior. WGS manual recovery
action check unchanged. This does not classify generic monitor failure or complete
automatic dispatch. Future dispatcher must freeze target dag_run_id before POST.

Focused review reproduced a related WGS bug: same-attempt/task failure in a new
DagRun deduplicated against old failure and reused old end time. Added DagRun to
the existing failure payload/dedup; historical actions stay intact, no backfill.

Fresh BS10610/server10610 uid6708; control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current20260912-opt-4d3d24e6.
Backend36ff21f87356 image8491604ee01d, actual /app readonly from
releases/20260923-step7-ae416fa/backend/backend, /config current/config readonly;
scan/dispatch=false. Own candidate writable. No active-run query: only isolated
network-none synthetic tests, no shared DB/config/runtime mounted or mutated.
Candidate C=control-root/candidates/p0-airflow-recovery-20260922. Backend test
container --rm --pull=never --network=none --read-only,1CPU/1GiB,/tmp64MiB;
C/backend and exact stage YAML readonly. No permissions changes or BS96 access.

Commands/evidence (PYTHONPATH=/candidate/backend, python -m pytest -q -p no:cacheprovider):
- test_cce_recovery_callback_fence.py --maxfail=1 --tb=short:
  RED1 failed1.04s, missing ignored and real WGS state overwrite; callback-fence-red.log.
- Same file without maxfail: GREEN21 passed1.64s, callback-fence-green.log.
- test_wgs_submission_service.py test_gatk_terminal_reconciliation.py
  test_wgs_resume_stage.py -k dag_failure --tb=short:
  GREEN5 passed,23 deselected0.87s; callback-fence-regression.log.
- Added exact test_new_dag_failure_is_not_deduplicated_against_old_dag_end_time:
  RED1 failed0.60s (old2020 end time reused), GREEN1 passed0.48s;
  callback-history-red.log / callback-history-green.log.
- After small dedup fix, only three affected legacy WGS dag_failure cases rerun
  =>3 passed,14 deselected0.60s (callback-history-regression.log); no full previous
  matrix/budget/plugin suite. Initial SSH invocation aborted before remote execution
  at BS172.17.61.18:22 handshake, exit1. Diagnostic ssh BS hostname succeeded
  (node005); one bounded retry reached BS10610 and produced that GREEN result.

Actual Airflow image58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b
from worker641409cf1cf9; standalone network-none/read-only1CPU/1GiB container,
tmpfs128MiB, own C/dags readonly, isolated AIRFLOW_HOME and SQLite path in /tmp,
no live service credentials, network or database. First --entrypoint python failed
ModuleNotFoundError airflow (callback-dag-identity.log), not application RED.
Read-only worker env showed PATH starts /opt/airflow/snakemake-venv/bin: wrong
interpreter selected. Changed only test invocation to /usr/local/bin/python;
actual DAG import/callback test passed1/1 in2.764s (callback-dag-identity-green.log).
No source workaround or dependency install; kernel swap-limit warning unchanged.

Unique tested cases22 new backend+5 affected legacy+1 real DAG. SQLite does not
prove PostgreSQL concurrency. No full suite, local runtime tests, deployment,
push or main/production/shared-test merge. Next remains dispatcher/adapter/lease
and observer fences plus trusted terminal closure and end-to-end acceptance;
automatic policy stays off. Rollback this source commit only; no data/runtime
rollback needed. Any future deploy: backend API before new GATK callback/DAG.

## 2026-09-23 WGS legacy manual retry fence

User next step; basedddda74e, same isolated P0 branch. Found action_wgs_run legacy
Resume/Rerun failed could increase attempt/dispatch while automatic reservation
pending, unlike resume_stage. Added shared require_no_pending_compute_recovery
in existing cce_recovery_budget; both service entries use it after refreshed
AnalysisRun FOR UPDATE. Guard before release lookup/attempt mutations. Keeps
completed history, treats missing/ill-typed attempt as ambiguous. Cancel bypasses
retry guard but retains prior CCE cancellation restriction. No main.py/Step7/
observer/DAG/runtime changes, no new routes/DB schema/recovery permission.

Fresh preflight: BS10610/server10610 uid6708; current20260912-opt-4d3d24e6;
backend36ff21f87356 image8491604ee01d, /app readonly20260923-step7-ae416fa/backend/backend;
/config current/config readonly; test,scan=false,dispatch=false; own candidate
writable. No fresh active-run DB query needed for network-none synthetic-only
tests and no shared mutation; prior [] is not presented as current evidence.
First scp and subsequent test SSH each aborted at BS172.17.61.18:22 handshake,
exit1; no remote test executed. Diagnostic ssh -v BS exit confirmed public-key
login/exit0, then bounded copy/test retry succeeded. No SSH config change.

New test_cce_recovery_manual_fence.py substitutes external release catalog and
uses existing synthetic Airflow fixture; real SQLite service/dispatch/action
paths. Covers reserved/queued/uncertain, ambiguous attempt identity, finished
history, cancel priority and stale-session attempt refresh. Tests do not prove
PostgreSQL locking/concurrency. Unchanged automatic budget suite not rerun.
Candidate C=control-root/candidates/p0-airflow-recovery-20260922. Cached image
8491604ee01d, --pull=never --network=none --read-only,1CPU/1GiB,/tmp64MiB.
Own backend and exact wgs_stage_contract.yaml mounted readonly; no DB, real
runtime, credentials or kubeconfig. Only C test/module/config files changed.
RED: PYTHONPATH=/candidate/backend python -m pytest -q -p no:cacheprovider
backend/tests/test_cce_recovery_manual_fence.py --tb=short --maxfail=1
=>1 failed0.65s exit1: DID NOT RAISE ValueError, legacy pending reservation bypass.
GREEN: same command without --maxfail=1, plus backend/tests/test_wgs_resume_stage.py
=>22 passed1.23s exit0 (14 new+8 affected), no skips. Logs manual-fence-red.log,
manual-fence-green.log. Kernel swap-capability warning unchanged. git diff --check.
No redundant full suite/local runtime tests/shared service change/deploy/BS96.

Updated API/DB documentation for service guard semantics, TASKS/CURRENT_STATE
and P0 ledger. Remaining: dispatch/callback/lease/adapter integration and terminal
evidence gaps, GATK path, PostgreSQL concurrency. Automatic policy remains off.
Do not count these WGS entries as every resubmission path. Rollback source commit
only; no runtime data/schema/production rollback needed.

## 2026-09-23 bs6 actual producer-to-consumer acceptance

User requested next step; sourceb5d8718 on existing isolated P0 branch. Prior SSH
blocker cleared on the first user-requested fresh attempt. Used runtime/backend
and handoff skills for remote-only scoped acceptance, not shared deployment.
Only two test files and related state/runtime/progress docs changed; no production
implementation or recovery policy change. Existing guard negative matrix extended
by one parameter (WGS/GATK); new opt-in actual bs6 contract file adds12 checks.
This is compatibility validation of existing behavior, not a RED/GREEN claim for
a new production implementation. No broad suite or plugin86-test rerun.

Fresh BS10610/server10610 uid6708; current resolves20260912-opt-4d3d24e6.
Backend36ff21f87356 /app readonly from
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260923-step7-ae416fa/backend/backend;
/config readonly from current release; image8491604ee01d. EnvironmentBS10610-Test,
scan/dispatch=false. Own candidate writable, no permission changes. A bounded
readonly test DB transaction (5s statement timeout) returned nonterminal_runs=[];
rolled back, no clinical fields queried. No shared service restart/changes or
BS96 access. Existing Step7 services and all runtime inputs/results preserved.

Producer fixture root E:
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-bs6-heavy-p0-20260923/consumer-fixtures-v1
Four scopes: wgs-admission/gatk-admission/wgs-guard/gatk-guard. Each contains actual
context.json, submit-events.ndjson, journal-state.json, executor-failure.json and
explicit empty jobs.ndjson. No admitted Workers or producer terminal seal.
Owner uses real bs6 SubmissionManager and Executor quota guard with synthetic
external API/quota responses/clock. Independently read/verified provenance and
checksum pins, then test checked all20 raw-file hashes and actual wheel bytes.
SHA256SUMS SHA a22a6d55de4947f0884c16c21d102222cd41c9c3f6a59159a4a9bd6c392fb038;
fixture-provenance.json SHA b36fab5298a58bc8e749a82a35ccc37816ebda485a3757f91ead68afbf73ce9d;
wheel SHA f9671d22ed02ec5a3edf0af861e116c0ea7dc9de816de6e07926fa869e2bb546.
Generator SHA in pinned provenance4e5fd7e63bcc6e715ef757f30b634e4a2e6c861cd6e7d4a812c52bb46a811783.
No old fixture relabeling or producer-byte rewriting.

Candidate C: control-root/candidates/p0-airflow-recovery-20260922. Copied only
current consumer/probe modules and selected tests into C. Ran cached image
8491604ee01d with --pull=never --network=none --read-only,1CPU/1GiB,/tmp64MiB;
only C/backend,C/scripts,E,wheel mounted readonly, no DB/env credentials/kubeconfig.
PYTHONPATH=/candidate:/candidate/backend CCE_BS6_FIXTURE_ROOT=/producer:
`python -m pytest -q -p no:cacheprovider backend/tests/test_cce_recovery_bs6_contract.py backend/tests/test_cce_recovery_evidence.py -k 'bs6 or WORKER_SUBMIT_GUARD_FAILED' --tb=short`
Result14 passed,62 deselected0.32s exit0, no skips. Log C/bs6-consumer-contract.log.
Kernel swap-limit warning unchanged; tests otherwise clean. git diff --check.

Scope of result: admission candidate/inventory format compatible; guard unknown
rejects; all candidate-only inputs reject. Synthetic terminal scaffolding cannot
prove a live complete Master terminal or enable recovery. Remaining existing
control/dispatch/callback/adapter and terminal-evidence gaps stay open. No actual
analysis, automatic enablement, publish/install/merge/production mutation.
Rollback source test/docs commit only; no runtime data rollback needed.

## 2026-09-23 next slice: bs6 consumer acceptance blocked before remote access

Source930348c, same isolated branch. User requested next step. Scope is actual
bs6 admission/guard-failure contract acceptance using readonly producer fixtures,
not a new terminal producer or shared-service integration. Requested existing
or minimal actual-wheel synthetic fixtures from plugin owner (WGS/GATK); no
rerun of its86-test suite. Fixture delivery/byte hashes remain pending.

Failed command: a readonly Python fingerprint script piped to
`ssh -o BatchMode=yes -o ConnectTimeout=12 BS10610 'python3 -'`.
Wrapper exit1; stderr `kex_exchange_identification: read: Connection reset`,
`Connection reset by 172.17.61.18 port 22`, then proxy connection closed.
Local `ssh -G` confirms BS10610 is chenjc@172.17.106.10 via BS, and BS is
chenjc@172.17.61.18. Failure is at the jump-host handshake, not evidence of a
backend, fixture or test failure. One attempt only; no blind retries or bypass.
No verified new hostname/mount/gates/active-runs; no remote writes or services
changed, no local runtime/production fallback. Coordinator and owner notified.

Prepared one extra parameter in backend/tests/test_cce_recovery_evidence.py:
WORKER_SUBMIT_GUARD_FAILED with otherwise qualifying synthetic values must still
be refused solely because its category is not allowlisted. Existing UNKNOWN/
retryable=false checks remain. Test is unrun, not GREEN; production code unchanged.
Planned remote command after preflight: selected guard parameter in that test
plus actual bs6 producer contract tests once hash-pinned fixtures are received,
inside the existing isolated cached-image network-none candidate only.
Do not count old-bs5 fixtures as bs6 acceptance. git diff --check passes locally;
runtime validation waits for approved test connectivity. Test edit remains
uncommitted pending validation; docs-only blocker record committed separately.
Rollback: remove that own one-line test addition or revert docs commit; no data
or runtime rollback required. Next condition is restored BS10610 access.

## 2026-09-23 bs6 producer handoff received

Owner: WGS-cloud-plugins task019f9d79-be3f-7701-af33-3595d72bbfac.
Branch jiucheng/plugin-bs6-heavy-p0-20260923; commit
0b19bb605cdff619a7f09b34a6fe774e4b43d357, reported clean. Combines full biosan5
5dd176a baseline with P0 0d606489. Wheel version0.6.4+bs6, SHA256
f9671d22ed02ec5a3edf0af861e116c0ea7dc9de816de6e07926fa869e2bb546.
Evidence root:
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-bs6-heavy-p0-20260923
Report HANDOFF_BS6.md; wheel below build-0b19bb605cdff619a7f09b34a6fe774e4b43d357/wheel/.
Owner reports baseline24 passed, source86 passed7.38s, actual wheel86 passed7.01s;
not independently rerun here. Duplicate adoption now emits one manifest entry
and permits actual quota receipt release in success/lost-response tests.

Static consumer inspection: cce_recovery_evidence.CATEGORIES remains the two
approved transport/admission categories; WORKER_SUBMIT_GUARD_FAILED with UNKNOWN
and retryable=false cannot pass it. No code or allowlist change. No new complete
Master terminal producer/seal; no automatic recovery enablement. Candidate was
not installed, deployed or promoted. Future consumer acceptance must use actual
bs6 fixtures, not relabel previous wheel evidence. Coordinator reports BS10610
test branch ab8695d/Step7 deployed; P0 not deployed. Revalidate live mounts and
active runs before remote work. This update only records owner handoff; local
git diff --check, no redundant runtime tests. Revert docs to roll back this note.

## 2026-09-23 user scope correction and producer alignment

User: MasterPod failure example requests a completeness check; continue original
P0 plan. WGS owner confirmed its latest authorization: biosan5 plus existing P0
into bs6, all HeavySlotQuota behavior preserved, no additional Master audit.
Plugin owner stopped its separate uncommitted audit candidate. This task stopped
the dependent terminal draft; no source hooks/launcher/RUN_FAILED extension or
producer fixture is considered delivered. Original CR-01–05 scope remains.

Preserved only our uncommitted scripts/cce_master_terminal.py, its test, and the
additional worker_pods probe projection in Git stash
3c617cbd86a4b3d27309689ecdfd7fc820f73c57. No user changes discarded or data removed.
The existing committed Master diagnostic increment ce9e296 remains unchanged.
Draft RED on BS10610 was one ModuleNotFoundError, exit1, master-terminal-red.log;
GREEN intentionally not run after scope correction. Do not count draft coverage.
No new remote actions, shared-service changes, installs, BS96 access or deployment
in this scope correction. Production and automatic policy remain untouched/off.

Changed state/task/spec/progress documents only after shelving draft code.
Verify with git diff --check and explicit diff/status review; no runtime regression
for these documentation edits. Next: existing consumer/control/callback work,
actual bs6 contract handoff and adapter integration. Missing trusted complete
Master/Worker terminal evidence still rejects automatic recovery; do not weaken
that gate or restore the extra audit draft without explicit scope approval.
Rollback: revert this documentation commit; stash retains unverified draft only.

## 2026-09-23 Master BackoffLimitExceeded coverage increment

User requested next step and whether reported20260921D Master BackoffLimitExceeded
is covered. Source8439f55; same isolated P0 branch. Design section3.1 already
explicitly denies recovery based on this symptom alone. Existing P0 probe dropped
reason detail: now retains master_job_condition and all observed Master Pod
main/init/ephemeral exits/reasons/signals/restarts/last termination. Keeps fixed
safe reason codes, omits messages, retains missing values as null, rejects invalid
history/ambiguous failure condition. No new recovery category, seal or permission.
Only scripts/cce_recovery_workloads.py, new focused tests and related state/spec/docs
files changed. No live caller/API/DB projection or production workflow changed.

Fresh test fingerprint: BS10610/server10610 uid6708; control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current20260912-opt-4d3d24e6;
actual backend/app20260917-native-ui-76915d8-r2/backend and config from current,
read-only; image8491604ee01d; PLATFORM_ENVIRONMENT=BS10610-Test, scan/dispatch=false.
Own candidate writable, no permission changes. No active-run query needed for this
network-none synthetic check; no shared-service change (window still not acquired).

Under candidates/p0-airflow-recovery-20260922, cached image with --pull=never,
--network=none --read-only,1CPU/1GiB, only own scripts mounted read-only; no DB,
kubeconfig/live runtime or credentials. PYTHONPATH=/candidate:
`python -m pytest -q -p no:cacheprovider scripts/tests/test_cce_master_failure_observation.py --tb=short --maxfail=1`
RED1 failed0.04s exit1: KeyError master_job_condition, expected missing feature.
GREEN command removed --maxfail=1 and additionally selected affected
scripts/tests/test_cce_recovery_workloads.py and
scripts/tests/test_cce_recovery_inventory.py::test_validated_inventory_drives_every_exact_worker_query.
Result34 passed0.06s exit0 (7 new,25 affected probe,2 composition), no skips.
Logs master-observation-red.log/master-observation-green.log. Swap-limit warning
unchanged. No unrelated suites/local runtime tests. git diff --check required.

No BS96/real cluster query;20260921D root cause and current production DB evidence
NOT confirmed. User report is not classified as eligible. Kubernetes official Job
docs confirm backoff terminal semantics; implementation coverage checked from repo.
Remaining: full trusted Master audit/final footer and complete Worker historical
outcomes, then adapter/dispatch/fences. lastState is not complete restart history.
No shared deploy, bs5 replacement, automatic enablement, cleanup or resume.
Rollback this source commit only; no runtime data/state changed.

## 2026-09-23 next step: submission inventory to UID probe

User: 继续下一步. Source22d47cb, isolated P0 branch/worktree unchanged. Added
scripts/cce_recovery_inventory.py and its new test file only; no existing runtime
entry changed. Joined complete bound journal/checkpoint/candidate/admitted-manifest
snapshot validation to prior read-only UID probe. All intents feed probe queries;
missing/extra/partial/conflicting evidence rejects. No terminal seal or automatic
authorization; internally consistent stale snapshots are not finality proof.
Updated docs08, CURRENT_STATE, TASKS and existing P0 progress ledger. Runtime and
handoff skills kept this slice test-only; no new plan or unrelated feature added.

Fresh gate: ssh BS10610 -> server10610; control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; current -> releases/20260912-opt-4d3d24e6;
actual backend/app -> releases/20260917-native-ui-76915d8-r2/backend, config from
current release, image8491604ee01d; test environment, scan/dispatch=false.
Bounded read-only test DB transaction active_runs=[]. Existing candidate/evidence
access used; no permission change. Shared backend/frontend window belongs to WES
UI task. All shared services, workflows, inputs/results, bs5 artifact and BS96
preserved; no install/deploy/deletion/analysis submission/database write.

Candidate C: control-root/candidates/p0-airflow-recovery-20260922.
Fixture E: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-p0-submit-20260922/fixtures.
Command (scripts mounted at /candidate/scripts:ro, E at /producer:ro):
`PYTHONPATH=/candidate CCE_PRODUCER_FIXTURE_ROOT=/producer python -m pytest -q -p no:cacheprovider scripts/tests/test_cce_recovery_inventory.py --tb=short`
RED with --maxfail=1: ModuleNotFoundError scripts.cce_recovery_inventory,
1 failed0.04s, exit1, C/inventory-red.log. Expected missing implementation, not
an environment problem; implemented then GREEN26 passed0.08s, exit0,
C/inventory-green.log. All tests ran, including both actual producer fixtures.
Cached image8491604ee01d, --pull=never --network=none --read-only,1CPU/1GiB,
ephemeral /tmp scratch only, no DB/kubeconfig/live runtime mounts. Kernel swap
limit warning unchanged. Two composition tests use prior synthetic subprocess
fixture, not repeated prior test cases. No old suites or local runtime tests run.

Plugin-owner read-only source report inspected locally at
D:/pipeline/task-artifacts/plugin-p0-submit-20260922/MASTER_ERROR_PRODUCER_READONLY_REVIEW.md;
remote same basename under E parent. Frozen cached Master490153a56b64,
Snakemake9.24.0+biosan1: SubmissionFailure reaches CLI ERROR without mandatory
JOB_ERROR; rule-status excludes ERROR; cancellation/monitor callback races and
swallowed logger flush errors prevent completeness inference. Need typed origin
binding, cumulative mixed/unknown error accounting and explicit healthy final
footer. Admitted Worker historical outcomes must also be accounted for; no-active
observations and404 are not proof of zero historical rule failure. Report is source
review, not producer implementation/acceptance. bs5 remains unchanged.

Next: trusted Master audit/terminal producer plus final snapshot and Worker
history binding, then adapter writer, dispatch/callback/control fences. CR-01–05
not complete. Live cluster/PostgreSQL concurrency/full integration not run because
not implemented in this slice and shared-service window is unavailable; obtain
fresh gate and coordinated window before service acceptance. No runtime rollback
needed; reverting this source-only commit removes helpers with no data effect.

## 2026-09-23 next step: bound workload observation prerequisite

User: 下一步. Source branch unchanged fromd9bd2a7. Used runtime/planning and inline
execution skills, preserved existing scope/ledger; no per-slice agent dispatch.
Added scripts/cce_recovery_workloads.py and scripts/tests/test_cce_recovery_workloads.py.
No existing runtime/Resume entry or workflow changed. Probe binds exact Master/
Worker UIDs, namespace and Pod controller ownership; rejects active/terminating,
missing/paged Pod inventories or incomplete main/init/ephemeral container exits.
Missing Job still queries residual Pods. Bounded read-only kubectl commands only.
It cannot prove input-list completeness or classify errors; deliberately no seal,
automatic permission, backend caller or deployment. Updated docs08/state/tasks/ledger.

Fresh BS10610 preflight: server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current20260912-opt-4d3d24e6;
actual backend/app20260917-native-ui-76915d8-r2/backend, cached image8491604ee01d,
scanner/dispatch false. Bounded read-only test DB transaction returned active_runs=[].
Coordinator then assigned shared-service window to WES UI task: no backend/frontend
mutation or deploy. Only own candidates/p0-airflow-recovery-20260922 used here.

Synthetic command (PYTHONPATH=/candidate; own scripts mounted read-only there):
`python -m pytest -q -p no:cacheprovider scripts/tests/test_cce_recovery_workloads.py --tb=short`
RED with --maxfail=1: missing module,1 failed0.04s,exit1. GREEN25 passed0.06s,exit0.
Logs workloads-red.log/workloads-green.log in own candidate. Cached backend image,
network none/read-only/1CPU/1GiB, no DB/kubeconfig/live runtime mounts. Tests replace
only subprocess boundary, exercising actual object/UID/state validation. No prior
helper, plugin suite, unrelated test, local runtime or actual cluster check rerun.
Initial scp failed exit1 because candidate scripts/tests did not exist; created
only that exact candidate subdirectory and copied successfully. No files deleted.
Kernel swap-limit warning unchanged. No permissions broadened or shared install.

Read-only source findings: huawei-cloud-runtime source83e7adb (untracked historical
asset backup left untouched). Native no-active-worker guard only checks states
from manifest, not exact UID/residual Pods. Master RUN_FAILED is generic and current
rule-status logger filters events/no complete classified error footer. These cannot
authorize recovery. Next: complete submit journal/admitted-manifest reader + trusted
Master error summary/writer, then adapter binding/dispatch/callback fences. Do not
write a positive terminal seal from zero observed rule errors alone.

Plugin version update verified: f1d3fa58a5075387500dd72620c03affe49b48e7 is metadata/
version only, recovery.py bytes identical to0d606489 and worktree clean. New
0.6.4+bs5 wheel SHA256 independently checked:
8ab618cb46d9e8d06ed0063096b30d9ffad3c3c41c7ba25f101ad6903165a26b.
Path: plugin-p0-submit-20260922/build-f1d3fa58a5075387500dd72620c03affe49b48e7/wheel/
snakemake_executor_plugin_kubernetes-0.6.4+bs5-py3-none-any.whl under the same evidence
root in preceding entry. No install or producer-suite rerun; old hash-pinned fixtures
retain old wheel provenance. No BS96/production/data mutation. Rollback source
commit only; no runtime data state to undo. CR-01–05 not complete.

## 2026-09-23 actual candidate producer/consumer contract check

After f73e284, plugin owner delivered commit
0d60648922b27aee25eda3ea7900f50467fbe0d9, version0.6.4+biosan4.p0.1.
Verified clean source worktree at
/mnt/biodevrwbi/33.chenjiucheng/project/worktrees/snakemake-kubernetes-p0-submit-20260922.
Evidence root E:
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/plugin-p0-submit-20260922.
Actual wheel SHA256 independently verified:
520914e26ced796b70805f2daf35e027c00fa1e985aadb855d72807c6aef844b.
Wheel: E/build-0d60648922b27aee25eda3ea7900f50467fbe0d9/wheel/
snakemake_executor_plugin_kubernetes-0.6.4+biosan4.p0.1-py3-none-any.whl.
Owner's source/wheel56-test results were read in E/HANDOFF.md, not rerun here.

Original admission fixture uses pipeline=synthetic, correctly outside consumer
allowlist. Requested regeneration, not edited JSON or a permissive production
change. Owner generated E/fixtures/wgs-admission and gatk-admission through that
wheel and synthetic API; generation1, explicit Master-submit execution identities.
Raw context/candidate SHA256 pins are in the new opt-in test file. Generator and
provenance: E/generate-pipeline-fixtures.py and E/pipeline-fixtures.log.

Added backend/tests/test_cce_recovery_producer_contract.py only; no production
code changed in this follow-up. With E/fixtures mounted read-only at /producer:
`CCE_PRODUCER_FIXTURE_ROOT=/producer python -m pytest -q -p no:cacheprovider tests/test_cce_recovery_producer_contract.py --tb=short`
Result4 passed0.08s, exit0; own candidate producer-contract.log. Same cached
backend image8491604ee01d, network none/read-only/1CPU/1GiB, no live DB mount.
Candidate-alone rejection plus synthetic-terminal compatibility tested for both
adapters. The terminal is test scaffolding, NOT real runtime evidence or a seal.
No extra RED/implementation cycle: this is contract acceptance of existing code.
Missing external fixture env explicitly skips opt-in tests, never counts as pass.

Fresh preflight: server10610; current and actual backend mounts unchanged from
preceding entry; scan/dispatch false. Read-only bounded test DB transaction found
GATK_20260922_112207_23AD29 attempt1 running/step1_upload; coordinator notified.
No shared service, that run, BS96, database write, install, image deploy or cleanup.
Updated state/tasks/runtime/prerequisite/ledger docs. Working branch unchanged.
Next: trusted Master terminal/Worker quiescence writer and adapter binding,
then dispatch/callback/control fences. CR-01–05 incomplete, policy unwired/off.
Rollback this test/docs commit only; source evidence and real data untouched.

## 2026-09-23 P0 evidence-to-action bridge and manual resume fence

Goal: user requested next step of existing P0, not P1 pause/delete. Continued in
isolated jiucheng/runtime/CR01-cce-recovery-20260922 from7bfa967. Original dirty
ops workspace and Step7-owned main.py/wgs_step7_service.py/wgs_observer.py untouched.

Added backend/app/cce_recovery_service.py and its synthetic test file: current
failed Step3 monitor explicitly binds to actual Master-submit execution; frozen
release/workdir/hash/generation and controlled evidence validated before reserve.
RunAction stores both identities and sealed-content binding; replay cannot replace
evidence. No status mutation, external dispatch, public endpoint or auto enablement.
Updated wgs_resume_service.py and test_wgs_resume_stage.py: unfinished same-attempt
automatic recovery blocks manual Resume before frozen files or Airflow change;
terminal automatic history stays intact. Updated docs04/05/08, state/tasks/ledger.

BS10610 read-only fingerprint in this turn: server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current20260912-opt-4d3d24e6,
actual backend mount releases/20260917-native-ui-76915d8-r2/backend; cached image
8491604ee01d. Test environment and scan/dispatch false. Only own candidate files
changed: candidates/p0-airflow-recovery-20260922. No service or deployment change,
so no rollback release selected. Shared database/runtime paths were not mounted.

Commands in cached image, network none/read-only/1CPU/1GiB, synthetic SQLite:
- python -m pytest -q -p no:cacheprovider tests/test_cce_recovery_service.py
  RED missing module; GREEN22 passed1.04s, service-red.log/service-green.log.
- python -m pytest -q -p no:cacheprovider tests/test_wgs_resume_stage.py
  RED selected pending guard failed DID NOT RAISE, exit1; GREEN whole affected
  file8 passed1.17s, exit0; resume-fence-red.log/resume-fence-green.log.
  Only tracked wgs_stage_contract.yaml additionally mounted read-only at /config.
Kernel swap-limit warning unchanged. No unchanged helper suite/local runtime
tests, live Postgres, Kubernetes or browser checks were run: none needed for this
internal slice; concurrency/actual producer integration remain required later.

Producer worktree now has submission_recovery.py plus plugin/init/tests changes;
owner still active, no final commit/producer fixture accepted. Proposed binding
writer and terminal wrapper remain missing. Do not deploy or enable automatic
recovery from these synthetic results. Before future shared-service work, recheck
active runs and mounts and coordinate Step7. Next: actual producer/wrapper-bound
adapter handoff, dispatch and remaining control/callback fences. Rollback this
source commit; no production/data state to undo. P0 remains incomplete.

## P0 next step: controlled evidence reader (test only)

User: continue next step. Worktree/branch unchanged from73f8d4e, original dirty
ops worktree untouched. Applied runtime/planning/execution skills; no expanded
pause/delete scope. Read-only BS10610 probe confirmed server10610, current
20260912-opt-4d3d24e6, actual backend20260917-native-ui-76915d8-r2/backend,
image8491604ee01d, test environment with scanner/dispatch disabled. Coordinator
subsequently released upload gate, but this slice did not deploy or mutate any
shared service/run/lease/database. Step7-owned shared files remain untouched.

Changed backend/app/cce_recovery_reader.py and tests/test_cce_recovery_reader.py;
updated docs08, CURRENT_STATE, TASKS and P0 ledger. Reader uses controlled fixed
file names, no-follow descriptor traversal, size/type/link and JSON guards,
pair stability checks, then existing bound validator. No public request accepts
root/scope/context. Actual adapter binding and trusted writer remain prerequisites.
Master Step2 creation identity is not interchangeable with Step3 monitor identity.

Remote candidate candidates/p0-airflow-recovery-20260922; cached backend image,
network none, read-only,1CPU/1GiB, no live mounts. Command:
`python -m pytest -q -p no:cacheprovider tests/test_cce_recovery_reader.py`.
RED: missing module (exit1). GREEN:26 passed0.09s (exit0), recorded as
reader-red.log/reader-green.log. Kernel no-swap-limit warning unchanged.
No repeat of unchanged budget/evidence suites, no local runtime tests.

Pending: plugin real producer fixture, authoritative terminal wrapper, current
Master/monitor lineage binding, reservation-to-dispatch/control fences, DAG/UI
and PostgreSQL concurrency. These tests are not real Master integration or P0
completion. Continue from plugin owner's final artifact; no additional authority
is implied. Rollback: revert unreferenced reader/tests; no data state to undo.

## 2026-09-22 P0 draft evidence validator checkpoint

Added backend/app/cce_recovery_evidence.py and its synthetic test file. Existing
candidate/image/limits used; RED missing module, GREEN62 passed0.13s. Logs are
evidence-red.log/evidence-green.log in the same P0 test candidate. Only this test
file ran; budget was not rerun after unrelated pure validator additions.
Plugin owner confirmed no completed producer fixture yet. Terminal seal is a
proposed trusted-wrapper contract, documented in docs08 and code, not a browser
API or authenticated signature. Exact identities, digest, complete cumulative
failure summary and all-intent/all-manifest quiescence are mandatory. Unknown
creation outcome stays rejected even after GET404. No producer/runtime integration,
new endpoint, image release or automatic policy enablement is claimed.
Continue with real producer fixture and authoritative wrapper support before
connecting reservation or dispatch; CR-01/02 remain partial. Scope and rollback
unchanged: unreferenced helpers only, no shared or production data changes.

## 2026-09-22 P0 continued under isolated-test release

Authority: user requested code and partial tests during remaining upload;
coordinator explicitly released only separate candidate/network-none containers.
SSH BS10610 succeeded (server10610). Current symlink remains 20260912-opt-4d3d24e6;
actual backend mount is 20260917-native-ui-76915d8-r2/backend, image8491604ee01d,
PLATFORM_ENVIRONMENT=BS10610-Test, intake scan and auto dispatch false.

Implemented backend/app/cce_recovery_budget.py with focused synthetic tests:
same-attempt max2, 60/180s, deadline/journal consistency, replay without double
spend, stop/control/Step7 fences, no commit inside helper. Missing initialized
budget rejects rather than assuming historical count0. No API or runtime caller,
no dispatch, policy enablement or default changes. Existing state retained.

Remote candidate: candidates/p0-airflow-recovery-20260922 under test control root.
Cached backend image; docker run --rm --pull=never --network=none --read-only,
1 CPU/1GiB, candidate /app read-only; synthetic SQLite only, no live mounts/DB.
`python -m pytest -q -p no:cacheprovider tests/test_cce_recovery_budget.py`:
RED missing module (exit1); GREEN54 passed1.89s (exit0), budget-red/green.log.
Kernel warns no swap limit support; memory limit applied, no swap-limit claim.

Changed code/test above, P0 ledger, prerequisite/status/task/handoff docs. No
service restart, upload/monitor/lease/task mutation, production access or deploy.
PostgreSQL concurrency and endpoint/DAG/runtime integration NOT tested. Shared
control locking at dispatch is still required; reservation is not authorization
to launch. Step7 owner is editing main.py/wgs_step7_service.py/wgs_observer.py;
leave these paths untouched until coordinated. Plugin owner preparing candidate
evidence schema. Next: validated consumer then adapter/fence integration; do not
claim entire P0 complete. Rollback: remove unreferenced module, no data rollback.

## 2026-09-22 P0 approved — remote acceptance blocked by baseline decision

User approved full joint implementation restricted to BS10610 testing. Agreed
versioned plugin context/failure interface with the user-selected plugin task;
wrote `backend/tests/test_cce_recovery_budget.py` and the P0 progress ledger.
Tests are not run and application code is not implemented. No completion claim.
Coordinator `01a0b254-07b5-7352-99aa-871b117459ad` explicitly paused all BS10610
deployment/acceptance while user chooses selective versus full test baseline;
the plugin owner was informed. No deployment/restart, real analysis, production
access or shared package installation occurred. Local `git diff --check` passed.
Next: resolve baseline through coordinator, receive actual fingerprint, run RED
then implement and verify the focused two-stage plan. Preserve these uncommitted
preparations and the separate original worktree's operational records.

## 2026-09-22 P0 prerequisite review — awaiting external scope confirmation

User requested P0 implementation. Isolated branch
`jiucheng/runtime/CR01-cce-recovery-20260922` starts from test `1da45f3`.
Reviewed GATK monitor/resume and read-only BS10610 executor source (`1ca1e88`);
the inspected producer lacks the required bound Worker-create fatal evidence.
Exact frozen Master artifact binding is not yet verified. No application edits,
runtime tests, real analysis, production access or deployment occurred.

Changed only this entry, CURRENT_STATE, TASKS and
`docs/P0_RECOVERY_PREREQUISITE_20260922.md`; the latter records exact paths,
commands/failures, evidence, risk and next decision. `git diff --check` is the
documentation check. Next: obtain scoped external producer/artifact confirmation,
then CR-01–05 and focused synthetic BS10610 acceptance. No tests are claimed.
Rollback is document-only; no task state or analysis data was changed. Existing
dirty operational documents in the original worktree were left untouched.

## 2026-09-22 remove redundant blanket validation gate

The user determined that `TEST-VALIDATION-01` would duplicate testing already
completed before production publication. The queue now accepts existing release
evidence for completed work and requires focused tests only for newly authorized
changes. No standalone missing-`S1` rerun or branch-wide validation matrix is a
prerequisite.

The next priority is P0 `CCE-RECOVERY-01`: review the proposed bounded recovery
policy for the known 0918A/0919B failure causes, then implement `CR-01`–`CR-05`
under a separate development instruction. P1 remains two-step WGS submission
followed by run control. This update changes only `CURRENT_STATE.md`, `TASKS.md`
and `HANDOFF.md`; it performs no application test, SSH, runtime, database,
analysis, deployment or data action. Rollback is a documentation-only revert.

## 2026-09-22 completed production commits synchronized into test

### Goal and authorization

The user clarified that `9ff67d3` and `9b381eb` should be included directly in
the primary test branch. Both are already completed and deployed production work;
they must not be represented as future development.

### Result and scope

- Target: local Git primary test worktree/branch
  `jiucheng/test/wgs-local-main-sync-20260917`.
- Verified `origin/main` and `origin/jiucheng/release/production` both at
  `9b381eb`; pre-merge divergence was `2 35`.
- Merged `origin/main` normally, preserving the complete `9ff67d3` application
  fix and `9b381eb` BS96 release record plus all test-only history.
- Resolved documentation conflicts by retaining the compact test backlog and
  adding the production feature, server, release and rollback facts. No
  application behavior was rewritten during conflict resolution.
- `TEST-LINEAGE-SYNC-01` is complete. These commits add no development card.
  The later priority correction above closes redundant `TEST-VALIDATION-01`.

### Checks, environment and rollback

This repository synchronization performs no SSH, Docker, database, runtime,
analysis, gate or data operation. The production release's existing acceptance
evidence is retained in `docs/releases/2026-09-18-sampleinfo-bs96.md`; local
runtime tests are not used as a substitute for BS10610. Checks are limited to
merge ancestry, exact file scope, conflict-marker/link/task consistency and
`git diff --check`. Rollback, if explicitly requested before further work, is a
normal Git revert of the merge; it must not alter BS96, BS10610 or analysis data.

## 2026-09-22 development backlog refresh and priority decision

### Goal

Refresh the authoritative test-branch planning state after new CCE recovery,
WGS submission and display designs were added, then assign a dependency- and
risk-based implementation order. This is planning only.

### Current source and lineage evidence

- Fast-forwarded the clean primary test worktree from `cd7771b` to remote
  `e44dc3e`; no local change was overwritten.
- Current `origin/main` and production both equal `9b381eb` and are not ancestors
  of test. Before this planning commit,
  `git rev-list --left-right --count origin/main...HEAD` was `2 33`; the
  documentation commit only increases the test-only side.
- The two absent main commits are `9ff67d3` (same-batch import and saved-review
  fix) and `9b381eb` (its BS96 release record). They are already released work,
  not new development, but must be reviewed into the test baseline before coding.
- The separate `D:/pipeline/airflow-demo` operations worktree has three user-
  owned dirty state documents for the completed 0919B manual rollback. They were
  inspected as operational evidence and left untouched.

### Reorganized priority

1. P0 — restore main/production ancestry in test and finish
   `TEST-VALIDATION-01`, including a fresh classification of missing `S1` after
   the submission-page main fix is present.
2. P1 — `CCE-RECOVERY-01`: review the two-recovery/60–180 second policy, then
   implement `CR-01` through `CR-05`. This addresses known 0918A/0919B failure
   modes and defines the identity/fencing contract required by run control.
3. P2 — `WGS-SUBMIT2-20260922`, then `RUN-CONTROL-20260918`. Submission work
   first reduces pre-analysis side effects; run control must reuse CCE recovery
   rather than introduce a competing recovery path.
4. P3 — `WGS-QC-TWO-SOURCE-20260918`; it adds source-qualified supplemental
   evidence while preserving ordinary QC authority.
5. P4 — `WGS-CNVPLOT-20260918`; it is a bounded read-only viewer.
6. P5 — operator acceptance, combined BS10610 evidence, promotion manifest and
   protected worktree hygiene after the selected feature scope stabilizes.

No two tracks may edit the same Backend/Airflow contracts concurrently. QC/CNV
can use independent owner worktrees only after the P0 baseline is fixed.

### Modified files and checks

- `TASKS.md`: added the priority table, dependency rule, current lineage refresh
  items and missing-`S1` reclassification gate.
- `CURRENT_STATE.md`: recorded current commits/divergence, new designs and the
  priority rationale.
- `HANDOFF.md`: this entry.

Validation is limited to branch/ref inventory, task/spec link and ID checks,
the three-file Markdown whitelist and `git diff --check`. No application tests,
SSH, Docker, database, runtime, real analysis or deployment action belongs to
this planning pass.

The target of this pass is local Git documentation at source `e44dc3e`; future
runtime acceptance remains BS10610. No SSH alias/hostname fingerprint, current
or rollback release path, mount/permission check, service state, scanner gate or
dispatch setting was inspected or changed because no remote action was in scope.

### Next action, risk and rollback

Next action is the P0 reviewed main-to-test refresh, not feature implementation.
Do not assume the production runner binding for editable sampleinfo until its
future preflight. Do not enable automatic CCE recovery before policy review and
focused BS10610 synthetic evidence. Rollback of this pass is a documentation-
only revert; it does not alter runtime or data.

Open questions are whether the revised two-recovery policy is accepted, whether
missing `S1` remains after the main refresh, and which exact production runner
SHA will be the future two-step-submission release target.

## 2026-09-22 submit recovery documents to the pending-development branch

User now authorizes submitting the documentation to primary test branch
`jiucheng/test/wgs-local-main-sync-20260917`. Remote advanced from9333160 to
cd7771b with QC presentation and CNV viewer designs; preserve both unchanged.
Integrate6540982 with that tip; resolve only competing TASKS/HANDOFF insertions,
retaining both sets of entries. Delta against remote is limited to the same
four recovery documentation files. No application, main/production or runtime
changes; application tests remain inapplicable.

GitHub port22 timed out;443 worked with StrictHostKeyChecking=yes and existing
github.com HostKeyAlias after the separate443 host alias was unknown. No host
key checks disabled, credentials exposed or persistent SSH config changed.
Verify exact file scope, whitespace, no conflict markers and preserved remote
designs before a normal fast-forward push; do not force-push on remote races.

## 2026-09-22 CCE recovery redesign — documentation only

### Goal and authority

User requests a revised development design covering0918A Worker-create transport
disconnect and0919B Gatekeeper admission timeout. Missing-input repair (0919C)
is deferred. This authorizes document changes, not application implementation,
real recovery, remote validation, production deployment or branch promotion.

Native isolated worktree is based on local test tracking ref9333160; branch
`jiucheng/docs/cce-recovery-design-20260922`. Existing dirty operations worktrees
remain untouched. No dependency installation or application baseline tests:
this is Markdown-only work under the project's local-editing boundary.

### Revised scope and files

- `docs/superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md`:
  replace blanket automatic-Master exclusion with two source-bound allowlisted
  failure classes; keep ordinary500, unknown causes, real rule errors and
  input defects excluded. Add persistent two-recovery budget,60/180s proposed
  waits, original deadline, old Worker quiescence, exact UID lineage, safe
  replay/reconciliation, user-stop priority, adapter gates and state display.
  Include0918A Step4 uncertain dispatch without blind publish replay.
- `TASKS.md`: CR-01–05 future delivery/acceptance cards; implementation unchecked.
- `CURRENT_STATE.md`: revised scope, proposal/review status and exact branch base.
- `HANDOFF.md`: this scope, evidence and handoff record.

Two/60/180 values are design defaults proposed for review, not previously
approved operational settings. Query retries remain separate from compute
recovery; both must be bounded and cannot reset silently. Resume reuses frozen
inputs/attempt/workdir and existing outputs; incomplete rules may execute again.

### Checks and intentionally unrun work

Read the current test-ref spec/task queue and bounded local resume source;
checked the design link, CR-01–05 in spec and task queue, contradictory exclusions
and exact four-file whitelist with Git diff/status. `git diff --check` passed;
`git diff --exit-code -- backend frontend dags scripts config` returned0 with
no output. These are document checks, not application validation. No
SSH/API/DB/Docker/workflow command was run.
Do not run pytest/npm/DAG import checks for this document-only delta. Future
application tests require development authorization and BS10610 isolation.

### Remaining work, risks and rollback

Written-spec review precedes a detailed execution plan and coding. Runtime
error evidence availability, existing Worker quiescence primitives, GATK
capability and atomic control fences must be demonstrated in CR-01–03; fail
closed if an old bundle cannot support them. Necessary external source/release,
image/schema/permission changes need explicit scope review, not implicit uplift.
No automatic kill of Workers, data cleanup, inputs/receipts repair or prepare.
No test/main/production merge or push is part of this document revision.
Rollback is a documentation revert only; no runtime or data state changed.

## 2026-09-18 WGS CNV plot viewer design

Documented a narrow WGS-only `CNV plot` Run Detail tab. It resolves only
selected-sample native PNGs from the frozen bound `03_CNV` directory, lists
sample IDs at left and lazily streams one image at right. The observed V4.2.1
plots are 4800x1200 PNGs at about 0.4 MiB each, so PNG is retained; HTML/SVG
redraw and eager batch preload are excluded. No code, synthetic fixture,
runtime/data operation, workflow change or deployment occurred. Future work is
`CNV-01` through `CNV-03` in the new design document.

## 2026-09-18 QC two-source presentation simplification

The approved presentation direction supersedes the prior expandable
supplemental-row idea: Run Detail QC uses default **常规临检** for batch
`QCstat.tsv` and conditional **罕见病** for batch `multi.QCstat.tsv`. The latter
is hidden when no `F57J`/`UPC` sample applies and contains only applicable
samples. This keeps identically named metrics apart without a wide table or
ordinary-row placeholders. Documentation/task cards only; no code, test,
runtime, data or deployment change.

## 2026-09-22 submission design queued for development

User authorized completing the combined development document and committing it
to the pending-development test branch. Incorporated WGS owner source evidence,
two-step final-submit boundary, editable input/revision/hash contract, automatic
intake deduplication and narrow cancellation semantics. Only four documentation
files are included. Preserve newer test-branch CCE recovery design updates;
main/production and existing operations-worktree changes are excluded.
Validation: document links, task identifiers and git diff --check only; no
application tests, server operations or deployment are necessary for this change.


## 2026-09-22 WGS two-step submission and editable sampleinfo proposal

User requested combined assessment and updated design only. New isolated docs
worktree wgs-submission-design-20260922 branches from local test9333160; main
inspection baseline9b381eb. No remote production command, source implementation,
test execution, merge or push performed. Existing0919B operational changes stay
in their original worktree. New design and CURRENT_STATE/TASKS/HANDOFF only.

Confirmed current approval2 starts analysis and can mutate pending; cancellation
works at config_review before approval, not after. Proposed final submission
defers analysis side effects until one explicit decision. Editing uses a private
working copy, revision and hash frozen before analysis, rather than modifying
an existing frozen source/receipt. Runtime already handles existing sampleinfo
with valid receipt reuse or missing-receipt archive/regeneration. Auto-dispatch
may instead be blocked by a retained manual task: narrowly release explicitly
cancelled uncommitted drafts, never all terminal tasks.

WGS-pipeline thread01a09149-ad9d-7e92-b98a-16d9cae075e2 was explicitly asked
to confirm current native source/commit, file-exists behavior and --sampleinfo
handoff effects. Its returned server-source audit is incorporated: server10610
wgs-4.2.0 HEAD ebf1f4b, prepare script last change9f4f359. Native sampleinfo/all
refuse existing files; analysis accepts valid edited copy, with updated source
hash/request for handoff. Source is not rewritten; final sampleinfo is derived.
Pending mutation precedes final directory rename, including zero-selected cases.
Actual production runner binding remains unverified; check once before rollout.
No native source edit or overwrite switch is proposed.
Document links and scope checked locally; no runtime test is appropriate for
this proposal. Rollback removes this proposal only, without service/data effects.


## 2026-09-18 consolidate new development documents into the primary test branch

### Goal and source selection

Make the primary test branch the single authoritative place for current planned
development. The two Git common repositories and their worktrees/refs were
inventoried after a remote fetch. Only two commits newer than test tip `2d899e5`
were documentation-only development proposals:

- `1c631b7` on `jiucheng/feature/run-control-20260918`;
- `53fc860` on `jiucheng/docs/wgs-qc-two-source-20260918`.

Older feature, fix, release and operations branches were not treated as new
development merely because they contain Markdown. Their historical deployment
or handoff notes remain evidence, not active queue entries.

### Consolidated content

- Added `docs/superpowers/specs/2026-09-18-run-control.md` unchanged in meaning:
  proposed CCE pause, same-attempt checkpoint recovery, exact cloud/Airflow/
  biodemo deletion, residual handling, tombstone, scanner fence and permissions.
- Added `docs/2026-09-18-wgs-qc-two-source-contract.md` unchanged in meaning:
  ordinary batch QC remains authoritative while applicable `F57J`/`UPC` samples
  receive separately labelled WgsMetrics supplemental evidence.
- Rewrote the source branches' task snippets into the current compact
  `TASKS.md`: `RC-01` through `RC-05` and `QC2-01` through `QC2-03`, with owner,
  sequence, dependency, scope and authorization boundaries.
- Updated `CURRENT_STATE.md` so both designs are visible beside the existing
  `CCE-RECOVERY-01` track without claiming any implementation or validation.

The source branches had different bases: run control was based directly on
`2d899e5`, while the QC document was based on main `1255a06`. Their full commits
and inherited state files were therefore not merged or cherry-picked. Only the
two specs and reconciled current-branch state were retained.

### Scope and validation

This was documentation and Git inventory only. No backend, frontend, DAG,
runtime, migration, application test, SSH, Docker, database, analysis, service
or production operation was performed. The designs do not register APIs, change
QC policy at runtime or authorize pause/resume/delete of a real task.

Validation covers the exact five-file documentation delta, local Markdown link
resolution, task-ID/spec consistency, source-spec comparison, `git diff --check`,
and proof that `backend`, `dags`, `scripts`, `frontend`, migrations and runtime
configuration did not change. No application test is applicable to this
documentation-only consolidation.

### Next action and rollback

Review `TEST-VALIDATION-01`, then select a documented development track under a
new implementation instruction. Coordinate run control with CCE recovery before
coding; the two-source QC work is independent. Production activation, test-to-
main promotion and live task/data actions remain separately authorized.

Rollback is a single documentation revert. The two source branches remain
available as provenance until repository hygiene separately classifies them;
this consolidation does not authorize deleting their worktrees or branches.

## 2026-09-18 test-branch backlog consolidation and synchronization hold

### Goal

Maintain one authoritative test development branch, preserve historical state
and make unfinished testing visible without synchronizing with `main`.

### Completed

- Confirmed the primary test worktree is
  `D:/pipeline/airflow-demo-worktrees/wgs-local-main-sync-20260917` on
  `jiucheng/test/wgs-local-main-sync-20260917` at `f0b07c4`.
- Refreshed origin and confirmed this is the only remote
  `origin/jiucheng/test/*` branch.
- Recorded, for inventory only, `origin/main=1e512e1`, main-only 13, test-only 23
  and merge base `c6ac6ce66df7f1636cc82376f5b2c113ecd457ed`.
- After user correction, replaced the proposed main-delta integration queue
  with `docs/TEST_BRANCH_SYNC_HOLD_20260918.md`. All main-only and legacy-branch
  changes are held while testing is incomplete.
- Replaced historical narrative in `CURRENT_STATE.md`, `TASKS.md` and this file
  with a compact snapshot, unfinished-test workflow and authorization gates.
- No merge, rebase, cherry-pick, code port, commit, push, source-code change,
  runtime action, analysis, database change or production action was performed.

### Preserved history

Original pre-consolidation files were copied to
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`:

- `CURRENT_STATE.md`: 356710 bytes,
  SHA-256 `13C1EE3C6D5CB0D7323111FBAD9E58E6F88DB0C5D08FE2CD360BA64DE99BF60E`.
- `TASKS.md`: 204039 bytes,
  SHA-256 `C5FBA92467D1D692CFE5DBB6240D36FCFB2790023D74E3A1F3A3621FD59B049C`.
- `HANDOFF.md`: 857955 bytes,
  SHA-256 `80470E265EC9AB9CF2F1F3807AD0F433FC7190817CE713D29AE60954CCA39817`.

Git history and detailed release/design records remain available. Archived
historical instructions are evidence, not current authority.

### Modified files

- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `docs/TEST_BRANCH_SYNC_HOLD_20260918.md`

### Commands and validation

- `git fetch --prune origin`: passed; refreshed the branch inventory.
- `git rev-list --left-right --count origin/main...HEAD`: `13 23`.
- Per-worktree ancestry and unique-commit inspection: completed for inventory;
  no integration performed.
- Documentation reference checks passed for the environment boundary, CCE
  recovery spec and synchronization-hold record.
- `git diff --check`: passed with exit code 0.
- Archive SHA-256 values were recomputed and match the recorded originals.
- Stale instructions to integrate/port main into the test branch were searched
  across all four changed documents and were absent.
- The compact queue has 17 intentionally open validation, implementation,
  acceptance, future-promotion and hygiene items.

No backend, frontend, DAG or workflow test is claimed by this documentation-
only consolidation. No BS10610 live preflight was run because no runtime action
was requested.

### Next action

Execute `TEST-VALIDATION-01`: reconcile archived unchecked items with current
source and evidence, then produce the unfinished-test matrix. Do not synchronize
with `main` while building or executing that matrix.

### Risks and rollback

- The test branch is not promotion-ready merely because prior focused tests or
  deployments exist; evidence must match the final candidate source.
- Counts are tied to the recorded commits and may change after future fetches,
  but divergence is not itself a defect to repair.
- Restore the three archived state files or revert this documentation change to
  undo the consolidation. No runtime/data rollback is needed.

## 2026-09-18 selective main-fix port to the test branch

### Goal

Apply only the three fixes explicitly approved by the user—`e7f0373`,
`cb1c3fe` and `347e4ed`—without synchronizing the rest of main or overwriting
test-branch Native/Local/SGE work.

### Completed

- Registered the audited `wgs-4.2.1-ebf1f4b` rule-to-phase inventory while
  retaining Unknown behavior for unreviewed releases.
- Made file-ledger reconciliation wait for an unpublished receipt and ignore a
  self-consistent foreign project root without deleting imported history.
- Added authenticated run-detail sample fields only for participating Sample
  IDs; global sample/QC/workspace projections remain privacy-safe.
- Added whole-attempt exact Rule filter options and full phase choices. The
  test-branch adaptation combines summary/filter/attempt rows into one SQL
  query so the existing `<=8` query budget remains satisfied.
- Simplified WGS Overview/Samples/Ledger presentation, added searchable exact
  Sample/Family selection and removed the Files tab request. Existing Native
  execution views were preserved.
- Updated API/frontend contracts and the synchronization-hold record. Main-side
  release documents and state files were not copied.

### Validation

- Local: Python compile passed; phase policy JSON parsed; `git diff --check`
  passed.
- BS10610 isolated candidate:
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/three-fix-sync-20260918`.
- Backend focused tests: 28 passed, 1 dependency warning.
- Frontend changed-scope tests: 17 passed.
- Frontend `npm run build`: passed; generated
  `index-D2PoeP0p.js` and `index-D4g5ndFq.css` in the isolated build image.
- Full frontend suite: 133 passed, 1 failed. The same failure reproduces on the
  pre-port `f0b07c4` baseline in the same image: `starts stage one without
  accepting runtime configuration` times out finding `S1`. It is therefore a
  pre-existing test-branch blocker, not accepted as green.

### Runtime impact and rollback

No BS10610 service, database, workflow, gate or running analysis was changed;
BS96 was not contacted. Roll back by reverting this selective local port. The
isolated candidate directory and build image contain no runtime authorization.

## 2026-09-18 local repository hygiene pass

### Goal

Remove provably stale local worktree/branch clutter while preserving the
primary test branch and every uncommitted or unique change set.

### Completed

- Refreshed both local Git common repositories and fast-forwarded only their
  clean `main` checkouts to `1255a06`; the test branch remained at `f0b07c4`.
- Reduced registered worktrees from 20 to 10. Removed five clean merged
  worktrees with their branches and three clean unique worktrees while retaining
  those branches and creating recovery bundles.
- Deleted nine additional unattached local branches proven to be ancestors of
  `origin/main`. No remote branch was deleted.
- Patch-preserved and removed two state-doc-only dirty worktrees. The merged
  GATK logger branch was deleted; the unique T242 branch and bundle were kept.
- Moved six nonregistered legacy directories and nineteen loose packages from
  the worktree root to
  `D:/pipeline/task-artifacts/airflow-repo-hygiene-20260918`.
- Preserved all eight source/test-bearing dirty worktrees. The primary test worktree retained its
  original 27 modified/untracked paths before this documentation update.

### Validation

- Both `D:/pipeline/airflow-demo` and
  `D:/pipeline/airflow-demo-production` are clean on `main` at `1255a06`.
- The remaining worktree root contains only ten registered dirty worktrees and
  no loose archive files or nonregistered legacy directories.
- Recovery bundles were created for the three removed unique worktrees and
  hashed; see `docs/REPOSITORY_HYGIENE_20260918.md` and the archive manifest.
- T197's historical bundle passed `git bundle verify` as complete before its
  broken-link disk remnants were archived.
- No source test was run because this pass changed repository organization and
  documentation only. No runtime host was contacted.

### Remaining work

Content-triage the eight retained dirty worktrees. Compare each change set with
current main and the primary test branch, preserve a patch or bundle, and obtain
an explicit keep/archive/discard disposition before removing any dirty
worktree. Then resume `TEST-VALIDATION-01`.

### Recovery

The three unique branches remain local and have standalone bundles. Moved disk
remnants and packages can be restored from the task-artifact archive. Deleted
local merged branches are recoverable from `origin/main` or reflogs. No runtime
or data rollback is required.

## 2026-09-18 main/production lineage merge into test

### Goal

Establish the user-requested relationship in which current main and production
are ancestors of the primary test branch, while preserving all test-only
commits and Native/Local/SGE adaptations.

### Completed before merge verification

- Committed the three approved fix ports as `8f062f9`.
- Committed compact state and repository hygiene records as `91060d0`.
- Confirmed live remote refs `main` and `jiucheng/release/production` both point
  to `1255a06`; no second production merge is required.
- Merged `origin/main` with explicit conflict review. Duplicate three-fix
  conflicts retain the test SQL budget, Native status choices and CCE log
  archive UI. WGS prepare-recovery source/tests from `1255a06` are included.
- Combined test and production environment/runbook observations; compact test
  state remains the current queue.

### Verification and publication

- Merge commit: `e8ce35a`; pushed to
  `origin/jiucheng/test/wgs-local-main-sync-20260917`.
- `origin/main` and `origin/jiucheng/release/production` are both ancestors;
  each reports `0` commits absent from test and test reports `26` additional
  commits at the merge tip.
- BS10610 isolated source candidate:
  `candidates/lineage-sync-e8ce35a`; no service deployment or restart.
- Existing backend Docker image, network disabled and source mounted read-only:
  the exact three-fix plus prepare-recovery set passed `36` tests.
- A broader backend set passed `94` and failed `6`. All six failing node IDs
  fail identically on first-parent baseline `91060d0` in the same image, so
  they remain pre-existing test-branch contract drift rather than merge
  regressions.
- Existing frontend build image, network disabled and candidate copied to
  tmpfs: selected tests passed `32` and failed the already recorded
  `starts stage one...`/missing `S1` case. Production build passed and emitted
  `index-D2PoeP0p.js` plus `index-D4g5ndFq.css`.
- Local checks were limited to Python compilation, policy JSON parsing and
  `git diff --check`; no local dependency environment was created.

No runtime host, analysis, database or production deployment is authorized by
this Git-only merge.
