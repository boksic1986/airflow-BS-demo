# P0 platform V03/V07 correction result — source and focused test handoff

Scope: Task2 of `docs/superpowers/plans/2026-09-25-p0-validation-corrections.md`.
This is an isolated platform source/test handoff, not a release or activation.

## Scope and environment

- Target: BS10610 test (`server10610`), not production. Existing cached, offline,
  non-root, read-only test-container path only; no Compose, live workload or service
  mutation.
- Existing `task6.ps1 -Mode inventory` preflight passed: expected control/current
  release, backend `/app` and `/config` read-only mounts, disabled scan/dispatch,
  UID 6708.
- Existing ignored runner:
  `.superpowers/sdd/2026-09-23-p0-2-master-handoff-ttl-implementation/task6.ps1`
  with `-Mode test` or `-Mode dag`, explicit `-Test` nodes and the evidence root
  below. It snapshots source into its own test directory and uses cached
  `--network none --read-only` containers; no local runtime test was run.
- All logs below are under
  `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task6-20260925/platform-v03-v07-20260925/`.
- Exact raw log copies are available locally at
  `D:/pipeline/airflow-demo-worktrees/cce-recovery-impl-20260922/.superpowers/sdd/2026-09-25-p0-validation-corrections/task2-logs/`.
  These ignored task artifacts are not staged for Git.

## Source correction in this worktree

- `scripts/cce_recovery_workloads.py`: type only validated cross-query inventory
  movement, reuse complete run-label Job LIST entries for present Workers,
  retain exact Master/missing-Job GET and each job-name Pod LIST, pass per-query
  remaining timeout and refuse late probe results. Identity, ownership,
  pagination and absent-without-terminal guards remain. All Pods in both lists
  must retain the exact run label. Same-UID active-to-terminal or GC movement is
  transient; changed terminal exits or terminal-to-active regression is not.
- `scripts/cce_recovery_failure.py`: at most three complete fresh observations
  for that typed movement, with the original absolute compute deadline checked
  before/after each round; no deadline means previous one-shot behavior.
- `scripts/cce_paired_runtime.py`: only `_automatic_failure_evidence` passes
  `deadline_epoch(payload)` to the collector. The hashed registered Step3 field
  is the source, not native handoff deadline. Other uncommitted top-of-file
  trust changes belong to native owner and must not be staged as this task.
- `dags/cce_worker_wait.py`: SSH outer timeout is
  `min(150s, remaining persisted worker_wait_deadline)` and a response arriving
  after that deadline is discarded. Six-argument restricted command unchanged.
  Initial monitor still uses existing QueryReconnect and original deadline;
  this does not claim a hard 120s wall limit for that owner.

## Focused RED/GREEN evidence

Each invocation repeated the test preflight. `-Mode dag -Test
dags/tests/test_cce_recovery_poll.py::test_worker_probe_allows_inner_budget_plus_ssh_startup_but_not_late_result`
failed as expected with outer timeout 30 (`platform-v07-dag-red.log`). The
late-response node failed with an extra backend POST
(`platform-v07-late-red.log`). After the DAG correction, `-Mode dag -Test
dags/tests/test_cce_recovery_poll.py` passed **8/8** in 3.14s
(`platform-v07-dag-green.log`).

The first `-Mode test` RED of four selected V03 nodes was blocked in native/
plugin fixture setup: private submission evidence directory not owner-only
(`platform-v03-red.log`); no new assertion ran. Native owner subsequently
corrected the private-spool/shared-export boundary; without a bypass,
the same four nodes failed for their intended reasons: duplicate present-Worker
GET, absent `InventoryMoved`, absent collector deadline argument and a test
clock patch typo (`platform-v03-red2.log`). The clock patch was corrected.
After platform correction, **4/4** passed (`platform-v03-green1.log`).

The paired deadline-inheritance node failed with `None` evidence while that
small paired hunk was temporarily absent (`platform-v03-paired-red.log`), then
passed **1/1** with it restored (`platform-v03-paired-green.log`). The same-UID
GC and three-round cap nodes failed when collector re-observation was
temporarily disabled (`platform-v03-gc-limit-red.log`), then passed **2/2**
with it restored (`platform-v03-gc-limit-green.log`).

Read-only review found one additional hard-conflict boundary: a same-UID Pod
could change state while its run label disappeared or changed, and the initial
code classified that as transient. Four focused negatives (missing/wrong label,
changed terminal exit, terminal-to-active regression) failed as intended in
`platform-v03-conflicts-red.log`. The final workload classifier now rejects
those directly, while still allowing validated active-to-terminal movement.

`git diff --check` on Task2 source/tests passed locally (non-runtime check).

## Final affected verification and environment gate

An earlier affected script sweep (`-Mode test` selecting
`test_p02_final_inventory.py`, six targeted collector cases, existing native
identity negatives and one normal resume receipt case) exited 1 with **32
setup errors**, all before Task2 assertions: native
`_ensure_shared_directory(destination, require_existing_collaboration=True)`
now rejects the synthetic parent as lacking group/setgid collaborator access.
This occurred during a concurrent native guard/fixture revision; Task2 did not
change or bypass native permissions. Log: `platform-v03-affected-green.log`.
Native owner then froze commit `ae90b654b0fa297c5102b2f696990ed75b0b4d74`
with its own independent affected fixture GREEN; Task2 did not repeat it.

Against that frozen native commit, the identical Task2 affected selection
reached all assertions: **34 passed, 2 failed** in 22.67s
(`platform-v03-final-affected-green.log`). The only two failures were the WGS/GATK
variants of an existing platform synthetic Resume fixture. It created its own
view parent without the native contract's setgid/group-access mode. The fixture
now sets `2770` on only those freshly created synthetic parents, retaining the
real native guard. Rerunning **only those two nodes** passed **2/2** in 3.25s
(`platform-v03-resume-fixture-green.log`). No real directory permission was
changed. The already passing 34 nodes were not rerun after a test-fixture-only
change. DAG affected file separately passed 8/8 as noted above.

No commit, push, installation, deployment, production action or whole-P0
acceptance is claimed. The native/private fixture correction and later
shared-parent fixture correction were separate gates; neither authorizes
changing real permissions or deleting data. The initial monitor still may
spend time inside existing QueryReconnect sleeps up to the original compute
deadline; no new 120s hard wall or query-owner bypass is claimed.
