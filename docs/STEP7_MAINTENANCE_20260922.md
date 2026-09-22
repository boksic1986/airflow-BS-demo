# WGS Step7 independent maintenance — implementation checkpoint

Status: FOCUSED TESTS PASSED / BS10610 COMPONENTS UPDATED.

Final boundary probe: the actual test worker invoked test forced-command.sh
with a synthetic unregistered Step7 identity. After the existing request
visibility wait it exited 1 with `registered runtime request is missing`;
traceback confirms `/home/ctapa/.config/airflow-wgs-test/wgs_runtime_gate.py`.
This is expected safe rejection, not a cleanup failure or additional passing
test. No cleanup was launched. Source ae416fa and publication record 08696d6
were delivered by bundle to the primary test-branch coordinator; integration
confirmation is tracked separately from the completed BS10610 publication.

## 2026-09-23 authorized test-only publication

User approved correcting only the test wrapper binding. Test wrapper now uses
`/home/ctapa/.config/airflow-wgs-test` for env and runner. Test runtime/request/
evidence roots remain `/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/wgs-runtime`;
analysis root remains `/sg2/50.ctapa/project/HWcloud/WGS_test/WGS_Clinical`.
Wrapper/runner mode700 and runtime.env600, ownerctapa:bioinfo retained.
Exact prior test files backed up under test `backups/step7-ae416fa-20260923`.
The previously effective runtime and its existing local helper dependencies were
copied to the isolated test directory before applying only Step7 runtime deltas;
otherwise fixing the wrapper would activate its obsolete September10 runner.
Production source hashes unchanged. No production env copied or modified.
Node200 lacks Git: staging initially stopped before activation; used installed
patch with dry-run on the private candidate, then syntax-compiled changed files.

Release: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260923-step7-ae416fa`.
Backend/observer are scoped deltas on their distinct actual mounted baselines;
Airflow retains its existing DAGs plus one new maintenance DAG mount.
Compose/rollback: `candidates/step7-ae416fa-control/{compose,rollback}.json`.
Config validation passed; backend, observer, Airflow worker/scheduler/API updated.
Frontend only nginx reload, DB/Redis/probes/collectors unchanged. API healthok;
new DAG registered/unpaused, max_active_runs1 and exactly2tasks confirmed.
No live maintenance action submitted, no real SFS operation or analysis rerun.

Rollback: use this control rollback Compose for those five test components,
then nginx reload. Restore test wrapper/runner backups only if necessary; never
restore the known production-binding wrapper for use. Keep test requests/data.
No main/production merge or BS96 Step7 release authorized.

## 2026-09-23 focused acceptance and deployment gate

User resumed Step7 after checking production WES recovery: running, no new
error, acquire-input slot normally rescheduling. Step7 remains test-only.
BS10610 hostname server10610, actual backend/native-ui-76915d8-r2 and observer/
onprem-main-282dfb0 pins verified. Platform active runs empty, latest WGS/GATK
Airflow runs not active, test runner processes absent; intake/auto flags false.

Candidate: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/step7-maintenance-20260923`.
No live database or network used in tests. Backend cached image
airflow-demo/backend:t235-232154f; Airflow uses actual worker image58195672af68.
Commands: pytest with `-p no:cacheprovider -q` on the four scoped backend/runtime
files below, filtered `-k 'step7 or maintenance'`:29 passed,1 failed,72 deselected.
The failure was container /tmp mounted noexec, so os.access(X_OK) rejected the
synthetic kubectl before its intended assertion. Only that case rerun with
tmpfs exec:1 passed. No production code change or blanket rerun.
`dags/tests/test_wgs_maintenance.py`:9 passed.
`dags/tests/test_wgs_maintenance_integration.py`:1 passed with isolated SQLite
db.initdb and STEP7_ISOLATED_INTEGRATION=1; two upstream OpenLineage deprecation
warnings. No real cleanup targets or biological submissions.
Airflow image lacked pytest; reused cached backend pytest dependencies via a
read-only candidate testdeps mount (including py.py), not package installation.
Early gate probe used two unavailable Settings attributes; corrected to scoped
getattr reads. These setup errors were not business failures or passing tests.

STOP: `/home/ctapa/.config/airflow-wgs-test/forced-command.sh` hardcodes
`config_dir=/home/ctapa/.config/airflow-wgs`, selecting production runtime.env
and runner. Actual test worker points at that wrapper. No deployment may use
this binding. User confirmation requested for a test-only binding correction;
production wrapper/config/code remain untouched. No deployed service changed.
Code/test acceptance is complete, deployment and test-branch integration are
not yet complete. Existing passed cases must not be repeated for deployment.

## Approved scope

Implement the user-approved independent `bio_wgs_maintenance` DAG (one active
maintenance run), reconnect/status reconciliation, maintenance failure sync and
manual retry of exact frozen cleanup targets. Preserve public API shape and
reuse existing action/generation/worker/receipt mechanisms. Do not modify
Step1–6, GATK, images, biological parameters or production.

Only new maintenance actions change route. Existing actions retain their DAG
identity. SSH launch response loss must first reconcile the original operation;
an absent status file alone is not proof that dispatch never occurred. Queries
use bounded 30/60/120-second retry delays, with no nested retry budget. Active
execution reattaches; authoritative completion succeeds; uncertainty blocks
deletion. Confirmed stopped failures use the existing manual retry entry and
inherit, never rediscover, the original target snapshot.

## Source findings and implementation hazards

- `wgs_step7_service` currently submits maintenance to `bio_wgs`, sharing its
  active-run limit. Its retry currently recomputes the snapshot; the new path
  must retain the original target identity.
- Runtime already starts asynchronous cleanup using nohup/setsid/flock and
  writes worker and status sidecars. Reuse these instead of another executor.
- The restricted runner currently has no read-only process-status command.
  Add only a Step7-scoped identity-fenced probe through that existing boundary;
  do not treat a stale shared-filesystem running receipt as proof of a live PID.
- An unavailable binding plus a partially present target currently fails closed.
  Keep that protection unless the frozen evidence proves exact ownership;
  never introduce raw recursive-delete fallback.
- Failure reconciliation must prefer validated runtime evidence over Airflow
  timeout, and reject stale action/attempt/generation callbacks.

## Test/deployment gate observed 2026-09-22

Base: primary test branch `eaed38edafb2e57eee687017d669913635207717`.
Implementation worktree branch: `jiucheng/fix/wgs-step7-maintenance-20260922`.

Successful read-only SSH confirmed `server10610`. Backend actually mounts
`releases/20260917-native-ui-76915d8-r2/backend`; the global current symlink is
older and is not deployment authority. Airflow worker still has individually
pinned DAG/common mounts. Do not replace them with the entire test branch.

Live scoped read-only query found one active analysis:
`GATK_20260922_112207_23AD29`, running `step1_upload`. Environment coordinator
confirms deployment hold remains in force while its separate upload-completion
and cancellation monitor operates. No services, tasks, credentials, leases or
analysis data were changed. No tests or cleanup were executed.

## Resume and single acceptance pass

User subsequently authorized isolated implementation while upload remains
active, then waiting for coordinator release before remote acceptance. The
independent DAG, frozen-target retry, internal context/observation endpoints,
identity-bound probe/start commands and stale observer fence are now drafted.
Tests are prepared, not executed. The user's explicit single-pass instruction
overrides baseline/full-suite and repeated RED/GREEN testing: no local runtime
test is performed.

Deploy only the TEST identity's runner, never the shared production ctapa
script. Compare actual source before applying this Step7-only delta. Existing
forced-command wrapper forwards the new restricted commands unchanged. Preserve
all unrelated deployed features and service mounts.

Queries reuse process identity, launch/worker locks and process-group presence;
no locks are deleted. A binding-less partial remnant stays blocked. Resuming a
still-owned partial target uses the original frozen Step7 command only, never
raw recursive-delete fallback.

Prepared focused tests: backend test_wgs_step7_service.py and
test_wgs_maintenance_observation.py; DAG test_wgs_maintenance.py; runtime
test_wgs_step7_probe.py and existing test_wgs_runtime_gate.py filtered to step7.
Use isolated test dependencies and synthetic data, then one maintenance DAG
integration case with external calls mocked. No biological submission.

Integration: test_wgs_maintenance_integration.py, explicitly gated by
STEP7_ISOLATED_INTEGRATION=1 and an isolated SQLite metadata DB. Initialize that
disposable metadata in a network-disabled test container, not deployed metadata,
then execute this single dag.test scenario. Do not repeat it after activation.

One fresh read-only review found three issues, addressed in source and focused
assertions: missing exact registration command; stale running receipt hiding a
monitoring failure; v1 retry archive counter lost. No repeated broad review or
test cycle. Code remains unaccepted until remote results.

Obtain the coordinator's released deployment gate and current mount fingerprint;
verify no active analysis before updating services. Implement in this isolated
worktree, leaving main/production and other dirty worktrees untouched. Run only
affected tests plus one isolated maintenance-DAG integration scenario on
BS10610 with synthetic targets/mock external failures. Cover analysis slots full,
duplicate launch, lost response, reattach, completed reconciliation, uncertainty,
partial cleanup, ownership/activity guards and stale callbacks. Re-run only a
failed case if needed; no blanket regression or real SFS deletion.

Acceptance, test-branch commit/integration and deployment remain outstanding.
Do not mark this checkpoint as a shipped fix or use it to recover production
0915B/0916R. Rollback must restore only test code/configuration, never remove
results or automatically replay cleanup.
