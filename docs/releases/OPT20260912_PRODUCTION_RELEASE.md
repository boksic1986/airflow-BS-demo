# OPT20260912 production panel promotion

User explicitly authorized the previously tested WGS/GATK panel optimization on BS96 on 2026-09-12. This is not activation of the unimplemented sample-reference/Intake design.

## Verified deployment

- SSH BS96, hostname server96; deployment identity ctapa (UID6801/GID520).
- Source: 4d3d24e6c0308b682a92e2b09824026b7a888818; tracked archive SHA256 8a3401c26caabac5397ef61242778db4a12a831727ed659b55f76062a364347f.
- Current: `/data/airflow-WGS/releases/20260912-panel-opt-4d3d24e6`.
- Predecessor retained: `/data/airflow-WGS/releases/20260912-gatk-81587fcb`.
- Gateway: http://172.17.61.96:12959 .
- Backend 45c880e61e92, observer 410663a6d4b6, frontend cb620c371dde were recreated; all three running, restart count0, no import/traceback markers.
- Eight other Compose service IDs/images/mount sets preserved, including worker/scheduler/API/Postgres/Redis/scanner/metrics/node probe. Scanner's existing disabled/restarting behavior is not changed.
- Production environment and both external env files retained. Shared data mount remains pinned to predecessor/shared. No database migration, data deletion, analysis submission, owner pipeline/private gate change or cloud operation.
- WGS scan/dispatch remain false. Manual GATK configuration retained. Custom project and catalog overrides remain false/false, with empty compatible-runtime declaration.
- Production/main Git checkout was not changed or pushed; this promotion pins the already reviewed development code without merging unrelated commits.

## Acceptance

- Earlier BS10610 targeted backend/review evidence: OPT20260912_TEST_RELEASE.md. BS10610 SSH and current pointer were reachable during this task; user browser login issue was not diagnosed.
- Production cached offline frontend build: 25 test files /93 tests passed, TypeScript and Vite passed. No Docker Hub pull or dependency installation.
- Backend requirements unchanged from deployed predecessor; dependency image retained.
- Frontend image `airflow-demo/frontend:prod-opt-4d3d24e6`, ID sha256:edfafcd273aeaf316fae3c290f1d20d0e81b6efaf15e076c25f2f6299f913221.
- `/api/health` healthy; `/submit` serves `index-_c2zYdoZ.js` / `index-9kcWGY_H.css`, both HTTP200 and matching tested assets.
- Seven business histories, zero active runs, identical before/after analysis-id/status hash 3a9724847becb1ffd786e73fea995d5d948b98028a54d78210b51f4df1e4cbc0. Workspace and Rule GETs passed for all seven; no patient values recorded.
- WGS release wgs-4.2.1-cc9bde3. GATK release runtime_identity response available.
- Heavy available true, used0/limit25, mode idle, timestamp2026-09-12T06:45:07.739367Z. This is telemetry, not saturation or per-rule enforcement acceptance.
- Resource packages unavailable/spool_unavailable. No new billing collector/credentials deployed. Missing historic rule start/QC evidence remains explicit, not fabricated.
- Authenticated browser visual acceptance remains user-facing; no claim that browser login or all visual behavior was verified. No full backend/biological suite rerun on production.

## Operational evidence and rollback

Helper and before/after metadata: `/data/airflow-WGS/candidates/panel-opt-20260912/`; helper `promote96.py`; overlay in candidate `compose.panel-only.json`. Original env files unchanged. Frontend build provenance: candidate `.build/frontend-offline/frontend-image-provenance.json`.

Rollback only after fresh active-state review:

`python3 /data/airflow-WGS/candidates/panel-opt-20260912/promote96.py rollback`

Restores three affected images and original mounts, checks health/protected fingerprints, restores predecessor current pointer. Does not delete data or change gates. Some original binds use current; verify rollback against recorded before.json rather than assuming all old services used identical source snapshots.

Preflight failures: default chenjc could not write ctapa-owned candidates (exit1); sudo unavailable. Verified existing user-provided ctapa key and continued as ctapa, without widening permissions. Helper initially compared ordered mounts and tuple/list serialization, falsely flagging scheduler; diagnostic confirmed same ID/image/mount set. Corrected comparison to sorted JSON-compatible lists; guard passed before any service mutation.
