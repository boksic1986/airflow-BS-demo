# RESOURCE-LOAD-20260915: resource loading and transport

## Cause and scope

The user confirmed metrics eventually appeared. BS96 collectors and the resource
API were healthy: two nodes, SFS and verified Heavy occupancy 0/25. The gateway
sent about 1.88 MB per resource poll without compression (7 days/10,080 SFS points
plus 120 node points). Access logs showed some client transfers lasting 15–22s.
DashboardResourcePanels treated a null first response as missing telemetry.

Changed only the resource panel's initial loading/error display and exact
`/api/platform/resources` nginx location in both templates. Subsequent refresh
errors retain the last snapshot. No history downsampling, fabricated metrics,
API/schema changes, collector changes, workflow or scanner changes.

## Verification

- BS10610/server10610 cached builder:
  `airflow-demo/frontend-builder:node22-lock-35420d5e3ec0`
  (`sha256:25e83a56052d63d900e253c618d342679bb46b66e4566390fa52eb3233702fdf`).
- New loading/error regressions initially failed 2/4 against original source.
- Final focused Vitest: ResourceLoading, DashboardResourcePanels,
  ResourceMonitoring and useSilentRefresh: 14/14 passed. TypeScript/Vite passed.
  An initial build caught nullable timestamps in the new test fixtures; corrected
  fixtures and the final complete test/build command passed.
- Cached network-isolated build; no package or Docker Hub downloads.
- Isolated test nginx: identity 1,798,946 bytes vs gzip 148,553 bytes; both decode
  to three resources and 9,092 historical points. Temporary nginx container removed.
- BS96 pre-fix gzip request still returned 1,879,269 bytes uncompressed, failing
  the real gateway compression check. Post-fix identity 1,879,222 vs gzip 150,596
  bytes (92.0% reduction), identical decoded size and 10,200 historical points.
- Existing live JS/CSS hashes matched a baseline build of recovery HEAD before
  overlay; this prevents reverting unrelated UI changes.
- Browser automation was unavailable (browser inventory connection failure).
  User confirmed slow-load behavior; post-deploy visual/client timing acceptance
  requires user refresh. Server-local request timing is not client WAN timing.

## Deployment and rollback

User-authorized target BS96/server96; applied 2026-09-15 00:46:52 Asia/Shanghai.
Control current remains `/data/airflow-WGS/releases/20260912-panel-opt-4d3d24e6`.
Frontend container `ddba6fa13eed` remains on its existing image. Actual backend
source remains `/data/airflow-WGS/releases/20260914-gatk-recovery-0436dce/backend`.

Overlay: `/data/airflow-WGS/releases/20260915-resource-loading`.
Live nginx file remains the existing frontend bind mount; patch preserved the
live `/23` and exact-host allowlist entries, which differ from the generic template.
Preimage SHA256: `e7efbef7649c4db9fc58ed4a898857e2334e7be6e0bfbcb307fe55d3dc24e7e9`.
Owner/mode checked: `chenjc:bioinfo 0664`. Hash guard before modification.

New JS: `index-DFs-sj5Z.js`, SHA256
`84da2025861d52ebdeea056855f28d8df2991efa598d13784c1d225adb24dacc`.
CSS unchanged: `index-CdK5PwQa.css`. New asset copied first, then atomic index
replacement; old assets remain. `nginx -t` passed before graceful reload.
Before/after container ID lists were identical; no backend/Airflow/collector
restart or scanner/dispatch setting change (observed scan=true, dispatch=false).

Rollback: restore `rollback/nginx.wgs.conf` from the overlay to the existing
nginx bind source, validate `nginx -t`, gracefully reload, and restore
`rollback/index.html` to the frontend document root. No data rollback is needed.
The asset overlay must be incorporated on a future frontend image recreation.

## Handoff

Changed files: frontend resource component/new regression test, both nginx
templates, frontend spec, deployment runbook and this note. Main task owns the
concurrently modified CURRENT_STATE/TASKS/HANDOFF; requested it link this record
instead of staging its unrelated WGS cleanup changes. No analysis tests run:
this change neither invokes nor modifies WGS/GATK runtime behavior.
