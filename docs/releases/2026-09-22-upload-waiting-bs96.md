# BS96 upload queue display release — 2026-09-22

User authorized BS96 deployment, then main/production source synchronization.
Source delta: `1d0e718`; ancestor batch-title fix `f875488` already deployed.

## Scope and deployment

- Host: BS96 / server96; control root `/data/airflow-WGS`.
- Baseline: actual backend mount `releases/20260921-tracker-stage-0119a35/backend`,
  not stale global `current` and not wholesale Git main.
- New source: `releases/20260922-upload-waiting-1d0e718/backend`.
- Only `app/wgs_transfer_projection.py`, `app/wgs_timing_service.py`,
  `app/wgs_workspace_service.py` changed. Preserved all other bytes and live
  active-stage selection; timing import context adapted to retain its existing
  ACTIVE_TRANSFER_STATUSES import.
- Backend image unchanged; app bind read-only. Backend container `abe6560500a8`.
- Private `upload-waiting-1d0e718-control` contains effective/rollback Compose,
  before/after snapshots, exact applied patch and acceptance. Directory0700/files0600.
- At12:33Z only backend recreated with `up -d --no-deps --pull never backend`;
  frontend nginx configuration checked and gracefully reloaded.
- All23other running host container IDs unchanged; frontend stays f875488.
  Environment values, non-app mounts, networks, ports and execution/scan/auto
  gates preserved. No workflow process, database state or input modification.

## Minimal acceptance

Existing BS10610 focused tests:11backend +3frontend passed. No full suite repeated.
New deployed source imports passed in cached image with no network. Compose config
passed before restart. LAN gateway index/health/tracker/workspace allHTTP200.

| Batch | Stage | Stage status | Progress |
| --- | --- | --- | --- |
| 20260921B | Uploading FASTQ | waiting | null; existing UI renders empty bar |
| 20260921E | Uploading FASTQ | waiting | null; existing UI renders empty bar |
| 20260921D | Uploading FASTQ | running | 53.3 to53.5%, transfer continues |

D upload monitor temporarily retried during backend recycle, then returned to
up_for_reschedule at12:35Z; underlying upload not restarted. Do not claim no API
interruption. Gateway probes from Docker bridge/host loopback were denied403 by
existing nginx allowlist; LAN172.17.61.96 probes succeeded without access changes.

## Rollback

Only if subsequently authorized/required for this release:

```bash
docker compose -p airflow-wgs -f /data/airflow-WGS/upload-waiting-1d0e718-control/rollback.json config --quiet
docker compose -p airflow-wgs -f /data/airflow-WGS/upload-waiting-1d0e718-control/rollback.json up -d --no-deps --pull never backend
docker exec airflow-wgs-frontend-nginx-1 nginx -t
docker exec airflow-wgs-frontend-nginx-1 nginx -s reload
```

This restores prior backend source only. Never down the stack, remove orphans,
repoint global current, roll back data or overwrite unrelated services.
