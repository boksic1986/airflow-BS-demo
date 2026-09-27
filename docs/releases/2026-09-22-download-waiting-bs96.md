# Download waiting display — BS96, 2026-09-22

User approved matching upload queue UI and BS96/main/production rollout.
Source `4b09b7b` adds read-only current-DAG queue projection. No scheduling,
lease, continuation, database/schema or frontend application change.

## Verification

- BS10610 isolated candidate `candidates/download-waiting-20260922` under test
  control root. Synthetic SQLite, no real data or service DB, network none.
- RED: actual Step4 instead of expected Step5. GREEN: shared-transfer test file
  **22 passed in1.35s**, including absent/failed queue evidence, HTTP failure,
  old attempt, actual started/failed/completed download and upload regressions.
- No full suite or frontend build repeated, per scoped minimal verification.

## Production

- BS96 hostname server96; root `/data/airflow-WGS`.
- Baseline actual app bind `releases/20260922-upload-waiting-1d0e718/backend`.
- New bind `releases/20260922-download-waiting-4b09b7b/backend`, read-only.
- Only main.py, wgs_transfer_projection.py, wgs_timing_service.py and
  wgs_workspace_service.py differ. Live timing import/active-stage fixes preserved.
- Patch check, import/main syntax and Compose config passed before restart13:18Z.
- Backend `0efb49677e24`; image unchanged; frontend nginx graceful reload.
  **23 other running container IDs unchanged**, gates and unrelated mounts retained.
- LAN gateway health/tracker/workspace200. C/E/B upload waits unchanged;
  D upload79.4->79.5%. No current live download-wait case; synthetic verification
  is not presented as live queue acceptance. No workflow restarted or data edited.

## Rollback

Private control `download-waiting-4b09b7b-control` contains before/after snapshots,
applied patch, effective Compose, rollback and acceptance (directory0700/files0600).

```bash
docker compose -p airflow-wgs -f /data/airflow-WGS/download-waiting-4b09b7b-control/rollback.json config --quiet
docker compose -p airflow-wgs -f /data/airflow-WGS/download-waiting-4b09b7b-control/rollback.json up -d --no-deps --pull never backend
docker exec airflow-wgs-frontend-nginx-1 nginx -t
docker exec airflow-wgs-frontend-nginx-1 nginx -s reload
```

Restore backend source only if required. No stack teardown, current symlink switch,
data rollback, container orphan removal or change to other service compositions.
