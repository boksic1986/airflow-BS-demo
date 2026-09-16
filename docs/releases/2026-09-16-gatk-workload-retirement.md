# GATK workload retirement and Step7 eligibility

## Scope and diagnosis

User approved this fix, main/production Git synchronization and deployment to96.
No analysis rerun, SFS cleanup, project/result deletion or attempt change.
0914A and0914B Master Jobs are Complete, but expired Running Pod observations
(including0914B's temporary evidence reader) block the Step7 action.
Step6 download/materialization had already completed. Step7 is explicit SFS release.

## Minimal correction

Reuse the existing evidence bridge, Kubernetes JSONL/cursor importer and runtime
stage polling; no new API/table/daemon or CCE/image upgrade. For the GATK label,
the existing Pod query reads the namespace inventory and only projects the bound
run. This detects changed labels rather than mistaking a live Pod for deletion.
A complete inventory emits Deleted/PodNotFound for previously observed Pods now
absent. Malformed/incomplete inventories and changed ownership fail closed.
The cursor retires those names; older observations cannot resurrect the row.
Existing terminal Pod success/failure rows remain scientific-history evidence.

Collect once again after terminal reader cleanup and at Step6 completion, because
reader deletion is asynchronous. Step6's existing status poll ingests this final
evidence. Collection failure is monitoring degradation, not delivery failure.
Step7 accepts only terminal or confirmed-absent workloads; unknown/live states
remain blocked. The node's fresh Master UID, live Job/Pod, receipt and exact SFS
target checks remain unchanged, as do administrator confirmation and WGS execution.

## Tests

Only isolated BS10610/server10610 tests; no test service rollout or real analysis.
Base main/production6bd69af; dedicated server repository:
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/gatk-cleanup-20260916`.
Branch `jiucheng/fix/gatk-cleanup-stale-workloads`. Server Git2.49.0 uses the fixed
miniforge3/bin/git, not local Windows Git or nipttest Git.
BS10610 actual application now uses20260916-onprem-review, which belongs to other
work; left untouched. Tests use cached backend image8491604 and network none,
read-only candidate source, disposable container-local synthetic SQLite/tmpfs.

RED:9 failures/3 passes for disappearance, incomplete inventory, changed labels,
unknown-state gate, stale events and final collection;2 additional expected
failures for Step6 refresh. Initial second RED fixture command used the tmpfs
mount itself as pytest basetemp and failed before execution; corrected to its
child `/testwork/tests`. No production changes during testing.
GREEN:76 passed in5.58s across test_gatk_workload_retirement.py,
test_gatk_step7_service.py,test_gatk_runtime_service.py and script tests
test_wgs_evidence_bridge.py,test_gatk_runtime_gate.py. No full regression or reruns.

Other preflight failures: server airflow-demo directory was not a Git repository;
used a new server clone instead. GitHub SSH host trust was unavailable; normal
HTTPS remote verified both refs6bd69af and cloned successfully. No host-key bypass.

## Release boundary

96 current symlink remains20260912-panel-opt-4d3d24e6; actual backend/observer
source before this release is20260915-ui-93069eb. Promote only the three backend
file deltas and two GATK-private scripts. Preserve unrelated source changes,
0914A recovery helper, WGS-private scripts, Airflow processes and all data.
Reload backend only after checking active task continuity. Retain exact backups.
Reconcile the four already-completed GATK runs through the same new collector
and existing evidence importer; never fabricate success or submit cleanup.
Deployment result and rollback receipt will be appended after verification.
