# Handoff

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
