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
## Deployment receipt

Server code089dc93 committed on2026-09-16, main and jiucheng/release/production
fast-forwarded from6bd69af and pushed atomically. No unrelated dirty work included.
Review found no must-fix issues. No additional test suite after76-pass result.

At07:36Z, installed the two GATK-private scripts on ctapa/t640 (node200), with
original-hash guards, mode preservation, exact backups and atomic replacement:

| File | Previous SHA256 | Installed SHA256 |
| --- | --- | --- |
| gatk_runtime_gate.py | e67f461c721344005205477929e62969ade064f054231d033596cd63de8d9f29 | b3230de8fcdba8806a91e247679c38d40ae57cd8b02280276e64f33e6f88ec0f |
| wgs_evidence_bridge.py | 9bf5ad6a47074caab187eedca1137fa8b81f32df525dca83cb082774b5f362ac | 1b1a05b96bc3e50edc01d50d26a31e313dd67d8c3320d24d480f2066cf4eaaf6 |

Private backups: `/home/ctapa/.config/airflow-gatk-workloads-089dc93/rollback`.
No runtime process restart; WGS-private bridge not modified.

On96, copied the three backend files from its actual deployed93069eb source and
applied only the server-exported089dc93 diff (git apply --check succeeded).
Files reside at `/data/airflow-WGS/releases/20260916-gatk-workloads-089dc93/backend/app`:
gatk_step7_service.py, gatk_runtime_service.py, wgs_observer.py.
Existing image/environment/network/mounts retained; only these files overlay /app.
Private Compose `/data/airflow-WGS/gatk-workloads-089dc93-control/compose.json`
passed config --quiet; deployed with up -d --no-deps --pull never backend.
Compose orphan warning refers to deliberately excluded services; none removed.
Old backendc1be8d79ea43 replaced byd4f942288f8f600a7c518e7f53e8d23b6c09de8464fbd46f4d00342205b4d5cf.
Other11 container IDs unchanged. Before release, existing Airflow REST queries
returned zero running/queued runs for bio_gatk,bio_wgs,bio_gatk_maintenance.

One collector-only workload snapshot (no reader Job/log sync) and existing bound
evidence import for each completed run restored Step7 capability:

| Run | New workload events | Capability | Analysis / attempt |
| --- | --- | --- | --- |
| GATK_20260915_114302_B2BA53 | 2 | available | success / 1 |
| GATK_20260915_102309_7D0AC0 | 2 | available | success / 1 |
| GATK_20260914_045846_789C29 | 1 | available | success / 1 |
| GATK_20260913_155423_30EFFE | 2 | available | success / 1 |

No cleanup request, analysis rerun, job deletion or result mutation performed.
Backend internal `/api/health` returned200. Initial host-loopback nginx12959 health
request returned403 under its access policy; internal backend check confirmed
health without changing the access policy. Earlier SSH18 disconnects were retried;
Git fetch transport stalled but normal authenticated HTTPS atomic push succeeded.

## Rollback

On96: `docker compose -p airflow-wgs -f /data/airflow-WGS/gatk-workloads-089dc93-control/rollback.json up -d --no-deps --pull never backend`.
On node200 restore only the two saved private scripts from the rollback directory
to `/home/ctapa/.config/airflow-gatk`, preserving modes with atomic replacement.
Do not restart Airflow/Masters, reset task state or remove analysis/evidence data.
Confirmed-absence observations remain valid historical evidence after rollback.
