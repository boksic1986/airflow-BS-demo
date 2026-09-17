# BS96 QC metric column restoration

User authorized main/production push and BS96 synchronization on2026-09-17.
Code commit0353723a9835ee1e75d06c8f83d822437688a518 is frontend-only plus tests/docs.
Both GitHub refs advanced atomically; normal local production checkout synced.

## Behavior and verification

Restore metric columns/values when judgment is unknown or absent. Preserve
threshold-free headings, source QC aggregate, failure reasons, missing-value
dashes and zero. No frontend threshold recalculation or inferred PASS; raw
diagnostic fields remain hidden. Backend/DB/workflow/runtime unchanged.

BS10610 cached isolated WgsQcTab tests4passed (prior RED3fail/1pass).
BS96 builds its own matching source with cached Node22 builder --network none;
tsc/Vite passed. No full suite or analysis submitted.
Screenshot batch WGS_20260916_180936_43867F read-only API has6samples and
16judgment fields, confirming values were not deleted. Browser visual
confirmation remains for user refresh; served asset verification is not a
claimed browser screenshot test.

## Deployed identity

- SSH BS96, server96, chenjc6708:bioinfo520; control/data/airflow-WGS.
- Source/build: /data/airflow-WGS/releases/20260917-qc-columns-0353723.
- Image: airflow-demo/frontend:qc-columns-0353723,
  sha256:1b7c87c3f21ed6b155a68eafcc8cb9ad98afefa71a6459536644e10ccb11fb83.
- Frontend27a65ebd33c1 ->9402a4fbb41ba4e2cc98d5d5c507e26363c8facf1ea2d2e5b37794ac4d312636.
- JS index-Dl8g1B15.js; CSS index-BFPGoplr.css. Served index/asset/health200.
- Exact old environment, nginx allowlist config mount, entrypoint, port12959
  and existing external network checked against live Docker inspect and retained.
- Other11containers retained IDs, including backend77e65737b68b. No backend,
  Airflow, scanner, observer, collector or database restart; no CCE/node gate edit.

Private frontend-only Compose, rollback and before inventory:
/data/airflow-WGS/qc-columns-0353723-control. Composeconfig --quiet and nginx-t
passed. Orphan warning names intentionally excluded services; none removed.
Global current symlink remains historical; actual container image is authority.

Rollback: validate rollback.json then run docker compose -p airflow-wgs -f
/data/airflow-WGS/qc-columns-0353723-control/rollback.json up -d --no-deps
--pull never frontend-nginx. No data rollback/deletion. Previous image retained.

GATK two-sample smoke remains paused at the user's explicit instruction.
