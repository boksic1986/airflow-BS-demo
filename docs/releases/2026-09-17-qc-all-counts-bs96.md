# Complete QC metrics and SNV/CNV counts published to BS96

User explicitly authorized merging main/production and BS96 publication.
Code4e9196d was pushed atomically to both refs; normal production main and
production branch fast-forwarded. No unrelated development commits included.

## Verification

- BS96/server96, chenjc6708:bioinfo520. Preflight7success/1failed, no active runs.
- Compared exact live Compose environments/mounts/commands/images/networks;
  full backend app comparison found only wgs_sample_projection.py changed.
- BS10610 cached isolated targeted test34passed. BS96 isolated source-build
  Vitest4passed and TypeScript/Vite passed. No dependency download or Docker Hub
  pull; no biological run or DB migration.
- Compose config and nginx syntax passed. Only backend/frontend-nginx recreated,
  followed by nginx graceful reload. Other10containers retained IDs.
- Actual client gateway health/index/newJS200; empty login validation422.
- Deployed requested-sample API now returns SNV count above its upper bound
  with fail, CNV count within bounds with pass; provenance hashes are present.
  Source aggregate warn preserved. Values match independently read native input
  counts. No clinical records copied to repository or fixtures.
- Frontend has all22 criterion columns, missing/inapplicable markers, no
  threshold labels. Served asset verified; no automated browser visual login.

## Active release

Source: /data/airflow-WGS/releases/20260917-qc-all-counts-4e9196d.
Backend8450fcef0b9f ->2950f374ab8a; dependencies/image unchanged,
read-only /app mount now uses the new complete backend source.
Frontend a64a0ab29b10 ->721f3e76239e;
airflow-demo/frontend:qc-all-counts-4e9196d,
sha256:0ac25241b52174e0bbf6840d1ab33ff1637c0fde025ab0c76e320c3062840e96.
JS index-B9fxb3fV.js, CSS index-BFPGoplr.css.

Scantrue, autofalse, WGS contract_v2true and GATK profile r2 preserved along with
all other environment values, mounts, gateway allowlist, ports and networks.
GATK smoke remains paused. No native WGS changes, reruns, pending or result writes.
The global current symlink remains historical; actual mounts/images are authority.

Private paired Compose/rollback/before inventory:
/data/airflow-WGS/qc-all-counts-4e9196d-control/{compose,rollback,before}.json.
Rollback: validate rollback.json and recreate only backend/frontend-nginx with
--no-deps --pull never, reload nginx, check real gateway. Do not revert data.

One direct SSH deployment attempt failed at handshake(exit255), before executing
any command. Configured BS96 route succeeded; old IDs were confirmed before
cutover. BS10610 verification used BS96 as SSH transport only. No security or
access-control changes, no destructive cleanup. A docs-only completion commit
follows the verified code release and does not change its application content.
