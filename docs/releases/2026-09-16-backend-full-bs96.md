# Complete backend production deployment, 2026-09-16

## Authorization and source

User requested production-branch verification and a complete backend release,
stating no tasks were running. Scope is backend only; no frontend, Airflow, worker,
observer, collector, runtime-script, image dependency, database or data rollout.

Production ref verified via GitHub API:
`5cd55427ad5983572ce35f089050af135f6ff601`. Server clean checkout at that commit in
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/gatk-cleanup-20260916`.
Server Git `/sg2/33.chenjiucheng/software/miniforge3/bin/git` exported complete backend.
Archive SHA256: db97a8d7c0e632faae3a017e51198682c8cae0f3b76e0d6aeb92011aef58d0ab.
Normal server ls-remote failed SSL EOF; official authenticated ref API succeeded.
No force fetch/push or credential persistence.

Compared actual deployed93069eb backend (not merely its label): exactly8 app files
differ, matching Git diff. Requirements, Dockerfile and DB models unchanged;
no additional deployed Python files missing. Included changes are existing
GATK batch/workload/Step7 fixes, unfiltered phase summaries, bounded log context,
optional resource history projection and latest sample handoff decisions.
No new implementation or dependency installation was performed.

## Preflight and checks

BS96=server96, uid6708 chenjc:bioinfo520. Control `/data/airflow-WGS`, releases
hanjj:bioinfo2770, existing group ACL retained. Current symlink remains
20260912-panel-opt-4d3d24e6. Before backend was b702a4dc47fb on93069eb plus4overlays.
Airflow REST returned0 running/queued for bio_wgs,bio_gatk,bio_gatk_maintenance;
active business runs0. Intake scantrue, auto-dispatchfalse, GATK executiontrue
observed and retained. No execution gate changed.

BS10610 isolated cached8491604 backend container, networknone, source read-only,
synthetic SQLite setting: imported app.main and checked existing batch helper.
Result: backend import smoke OK,98routes. No production/test application restarted
for that check. Existing targeted regressions reused, no full/redundant suite.
Transferred archive hash verified; Compose config --quiet passed.

## Deployment

Complete source: `/data/airflow-WGS/releases/20260916-backend-full-5cd5542/backend`.
SOURCE_COMMIT marker contains the full Git hash. Switched backend `/app` to this
directory; removed all4 `/app/app/*.py` file mounts. No files were deleted.
Preserved all other mounts, exact image/env/network/ports/restart/health settings.
Private inspected inventory, rollback.json and compose.json:
`/data/airflow-WGS/backend-full-5cd5542-control` (restricted access).

08:08Z command: `docker compose -p airflow-wgs -f /data/airflow-WGS/backend-full-5cd5542-control/compose.json up -d --no-deps --pull never backend`.
Orphan warning lists deliberately excluded services; none removed.
New backend3b66af0a06c77c1b07d5a7aad71bf07747e2526dcb70a3bf1d0c8a4835e06063.
Image sha256:0e2d6f0cdf4b89b5ade30b3855cdb8593f33e4c23085a0f5adcd644095cf6912
and environment unchanged. Other11 container IDs unchanged. No app file overlays.

One post-release check: internal /api/health200; GATK0914A/0914B correct batch
and cleanup available. Initial assertion expecting all4 cleanup actions available
stopped on0907A; a bounded read of the two older records confirmed20260907A and
20260823A analysis success and cleanup_completed with successful action records.
Those pre-existing completed actions are not rollout failures or actions by this
deployment. No task rerun, cleanup request or data mutation was performed.

## Rollback and limitations

Rollback backend only using the recorded former source plus4overlays:
`docker compose -p airflow-wgs -f /data/airflow-WGS/backend-full-5cd5542-control/rollback.json up -d --no-deps --pull never backend`.
No database migration or data rollback. Old release directories retained.
Future backend releases must replace the complete `/app` source, not add file
overrides. Frontend/Airflow/observer remain their own historical pins; do not claim
the entire96 stack equals main. Frontend-only improvements require separate rollout.
