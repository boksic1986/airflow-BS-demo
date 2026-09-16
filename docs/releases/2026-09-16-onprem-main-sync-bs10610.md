# Main integration and BS10610 test publication

User requested main -> Local/SGE test branch, then test deployment. This does not
authorize feature -> main/production merge,96 rollout, data reset or real compute.

## Source preservation and merge

Original Windows worktree `D:/pipeline/airflow-demo-worktrees/wgs-local-sge-20260915`
was e34bc45 with58 modified/untracked source/docs files. Preserved unchanged.
Imported its two feature commits after4b5234e through Git bundle, then saved dirty
source in server commit cfe822f5757ebeb09689d6ee3b371c5604f5394c. No Windows commit.
Authoritative worktree:
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs-local-sge-20260915`.
Branch `jiucheng/feat/wgs-local-sge-20260915`; fixed miniforge3/bin/git.

Merged main d3a031a (production application5cd5542 plus pending deployment-only
records) into feature as d705a46914204426399cec98e5b70322297d33cc. No main ref changed.
One code conflict in RunDetailPage refresh condition: keep native_monitor_only
exclusion alongside main log context/navigation. Eight docs conflicts preserve
both independent dated contracts/history. No new functionality introduced.

## Minimal verification and deployment

Live host BS10610/server10610 uid6708:bioinfo520. Existing application
20260916-onprem-review already packaged main359df11/e583833 plus Local/SGE work.
Actual comparison against merged source found only3 backend app changes:
gatk_runtime_service.py,gatk_step7_service.py,wgs_observer.py. Frontend/src and
alembic files identical; no repeat frontend build, migration or service expansion.

Before release:0 active/queued bio_wgs,bio_gatk,bio_wgs_native_monitor; active
business0; schema20260915_0026. Native registration/launch/monitor true;
intake scanfalse/auto-dispatchfalse. Existing project/snapshot mounts retained.

One isolated cached backend8491604, --network none, read-only source and tmpfs:
pytest tests/test_gatk_workload_retirement.py tests/test_wgs_onprem_airflow_sync.py
with --basetemp=/testwork/tests -p no:cacheprovider:16passed3.01s. One existing
Starlette/AnyIO deprecation warning. No full regression or real/synthetic workflow
submission. No production/test database backup or reset.

Archived committed source into releases/20260916-onprem-main-d705a46. SOURCE_COMMIT
records full hash. Private inspect inventory/compose/rollback:
`candidates/onprem-main-d705a46-control` under the test control root.
Compose config --quiet passed. At17:20+08 ran up -d --no-deps --pull never backend
wgs-run-observer. Changed only their /app source to complete merged backend.
Original images/env/remaining mounts/network/ports/health/restart retained.

Backend294cb11c1731f20e130cf63d9217e98a5372e4ee5848da2e852420fa12d6c400;
observer0e425a5aecea388814a60799d890189798d4dea9710a3f52028b11d9a5600f9a.
Other8 container IDs unchanged; Airflow native DAG/frontend remain accepted source.
Post-release internal health200; schema0026; existing synthetic native run
WGS_20260915_171640_A550DB stillsuccess/attempt1 with2 execution snapshots.
Native route and configured gates preserved. First SSH post-check reset at18
before executing; one reconnect recovered. No data or task-state manipulation.

## Rollback and follow-up

Rollback only two services with private rollback.json, --no-deps --pull never;
retain schema0026, all records/snapshots/results and native DAG. Old release retained.
External compute-node private scripts were not installed/restarted by this
BS10610 application rollout. Windows pre-merge editing copy remains preserved;
continue from authoritative server branch, not by copying that old tree over it.
