# Production frontend publication, 2026-09-16

User approved frontend publication. Source production5cd55427ad5983572ce35f089050af135f6ff601
verified by GitHub ref API. c281876 sample-flow UI is its ancestor, not an unmerged
change. Frontend tree e6a3dbceeb6fc8372162196876ee7cbdd74a5d25 equals359df11,
whose BS10610 acceptance is reused. No extra feature changes or full test suite.

Server Git archive frontend SHA256:
f77c4d8cd210eadb2a526174a8242f9e1f827b37e0d6bb856d7a7cc81d21addf.
96 source/build directory `/data/airflow-WGS/releases/20260916-frontend-full-5cd5542`.
Verified server96/chenjc6708:bioinfo520, release parent permissions unchanged.
Lock35420d5e3ec0f9555738f61e983cb05de30640db82f034d2659f87fd40a324b1;
Node22 cached builder25e83a56052d63d900e253c618d342679bb46b66e4566390fa52eb3233702fdf.

Used Dockerfile.offline-build target build only (--pull=false --network none);
npm run build (tsc/vite) succeeded. Skipped redundant target test per user scope.
Build image7c739130501e94d0ab76e09ce496d01be75179eff8515a54233e488e614d1119.
Copied dist with one stopped artifact container, then removed only that container.
Initial runtime-overlay FROM bare sha256 ID was interpreted as image repository;
metadata DNS failed before deployment. Corrected to the existing verified local
airflow-demo/frontend:ui-93069eb tag (same image2ffba073caa3), no base upgrade.
Runtime build replaced only image static files, not host data or nginx configuration.

New tag airflow-demo/frontend:full-5cd5542, image
52d8afab851c17202d39a8e9fcedc6da309ae21955df242940852f91338e6a9a.
Private inspect inventory, rollback.json and compose.json:
`/data/airflow-WGS/frontend-full-5cd5542-control` (restricted permissions).
Compose config --quiet passed; up -d --no-deps --pull never frontend-nginx at08:32Z.
Only frontend changed121e64a9e5f4 to5041172f8f5edf9277ed0ba58fcbd948538cf26ac81f2143ba38be55f03e5adc.
Other11 IDs unchanged, including full backend3b66af0a06c7. Environment, port12959,
external network and original nginx.wgs.conf mount retained. No analysis actions.

One served-resource check via http://172.17.61.96:12959:
index200; /assets/index-BQVVDtTK.js200; /assets/index-BFPGoplr.css200; /api/health200.
JS contains 样本流转,待纳入,纳入记录,纳入批次; old tab label absent.
This verifies the actual served bundle, not merely repository source. No browser
visual test or repeated suites. Main frontend includes the prior rule/log/resource
UI changes as well; corresponding backend is already full5cd5542.

Rollback only frontend:
`docker compose -p airflow-wgs -f /data/airflow-WGS/frontend-full-5cd5542-control/rollback.json up -d --no-deps --pull never frontend-nginx`.
Old image/source retained. No backend restart, DB/state/data rollback or cleanup.
