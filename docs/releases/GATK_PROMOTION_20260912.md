# GATK promotion execution record

Status: published and deployed; manual GATK enabled in both environments. No real analysis submitted.

User authorization: GATK manual production enablement on BS96, result root `/sg2/50.ctapa/project/HWcloud/WES_Clinical`, no input business-root whitelist, selective promotion to main and test synchronization. No analysis submissions or deletion authorized.

Baseline: production source4c194cd plus documentation8e982c9; old main0350536; GATK donor4013f93. Original `D:/pipeline/airflow-demo` dirty changes preserved untouched. Independent normal clone created at `D:/pipeline/airflow-demo-production` to avoid moving a live/dirty parent repository and invalidating its other worktrees.

Initial live read: BS10610 hostname server10610 current20260910-t258-cce084-r1; production ctapa hostname server96 current20260910-t260-recovery-runtime-r1. Actual mounts and safe gate fields inspected. Production WGS API4.2.1/cc9bde3/cce0.8.4; test GATK three terminal successful runs. Both Airflow environments had zero active runs; production has no bio_gatk DAG yet. Production backend start time matches the previous patch record, not unexplained drift. WGS scan and dispatch remain false.

Node t640 is reached as ctapa through NGS; direct workstation-to-node SSH timed out. Existing GATK test private configuration is isolated under `/home/ctapa/.config/airflow-gatk-test`; production will use a separate sibling. WES_Clinical exists and is ctapa-owned/writable. Immutable GATK source is release81f347e-airflow-t259 with the tested latency overlay; no workflow core change planned.

Concurrent external worktree cleanup removed the old donor directory while this task was running. Neither coordinator nor implementer removed it. Donor4013f93 objects are preserved in the independent production clone; the port uses pinned object reads. Original dirty repository remains untouched.

Independent review found and is checking bounded Step1 retry generation and raw
evidence identity fixes. Test and production Compose overlays both rendered
successfully against their own private environment files; execution remained
disabled during rendering. Test uses env/bs10610.wgs.env, production uses
env/production.env. Production reuses verified wgs-node200 SSH alias with a
separate GATK command (private SSH directory cannot be read by ctapa directly,
but the existing worker connection succeeds and returns t640).

Frontend acceptance: original unchanged source77 tests,75 pass/2 fail. Failures
are WgsProductionUi.test.tsx:314 (old one-request expectation sees3 after silent
refresh) and:580 (Total now exists in both throughput and SFS bandwidth panels).
No test assertion or unrelated WGS UI code changed to mask these failures.
TypeScript/Vite production build passed. JS index-bc6dsZAw.js SHA256
3ad713bc8580128ae277c2ec9b00bcbb2a9f659629365a0be8797ecebeb4961a and CSS
index-CXQ9-KPd.css SHA2569e1d530d7e7f9d36a5dde6d6f1e426023e7ca6b54677c14646023060552f273e
match actual production assets byte-for-byte. Thus no production frontend
replacement is needed; test has a freshly packaged cached-runtime image
airflow-demo/frontend:gatk-promotion-20260912 (ba282860cddd).

Progress:
- [x] Commit design/review docs and create independent production clone.
- [x] GATK selective port and unrestricted-source tests.
- [x] Targeted test acceptance and independent review; baseline regression failures documented above.
- [x] main publication and development worktree.
- [x] Test/production deploy and manual GATK capability verification.

Task/source sharing review: GATK port and deployment intersect only config/runtime interfaces; production WGS fixes must remain. Git layout and code port use the same independent clone but only coordinator changes Git refs. No other development worktree is modified.

## Final acceptance

- Published code commit81587fcbd34d7882772b659381bb06d3bcafa637, normal forward
  child of prior remote main0350536; exact tree equals reviewed production
  candidateb0dfafb. No whole test branch merge or force push.
- Ordinary production clone D:/pipeline/airflow-demo-production has `.git`
  directory and git-common-dir `.git`. Development worktree
  D:/pipeline/airflow-demo-worktrees/development, branch
  jiucheng/development/next, inherits production code and design documents.
- Root independently reran the fixed commit's GATK backend/gate/materializer/DAG
  tests in BS10610 cached image:40 passed,1 upstream deprecation warning.
- Both current releases end in releases/20260912-gatk-81587fcb. Test and
  production private extra environment files are env/gatk-81587fcb.env; always
  pass BOTH the existing environment file and this overlay when deploying.
- Both release APIs report GATK execution_enabled=true; both bio_gatk DAGs are
  active, unpaused and import-error-free, with pool gatk_cce_runs=1. No active
  runs or new submissions. Test keeps3 historical GATK runs; production keeps7
  business runs and24 historical WGS Airflow runs,0 GATK runs.
- Production migration0018->0019 added only2 generic GATK tables/indexes;
  test was already0019. Existing analysis/sample rows retained.
- Production output WES_Clinical; test output WES_test/WES_Clinical. Runtime
  write/read/removal probes passed as backend UID6801. Separate node GATK
  gate/private configs, gate source SHA25633eb4f3e5e31cde89c7e9c7bda036c22654fe2cdc0b19c6fe1564cc76d383210.
- WGS API remains4.2.1/cc9bde3/cce0.8.4; scan=false and dispatch=false in both
  backends. Production observer/frontend/Postgres/Redis container IDs preserved.
  Backend and Airflow API/scheduler/worker recreated for new DAG/env; nginx
  gracefully reloaded. Test also refreshed observer/probes/metrics/frontend.
- Public /api/health is OK on both gateways when checked on their hosts;
  Windows can reach production, but direct Windows-to-test12959 timed out.
  That route limitation is not claimed fixed. No authenticated browser click
  submission or real-cloud end-to-end run was performed.

## Rollback and retained state

Production previous release20260910-t260-recovery-runtime-r1; test previous
release20260910-t258-cce084-r1. Per-release DEPLOYMENT_BEFORE/AFTER.json,
ROLLBACK_RELEASE and COMPOSE_ENV_FILES preserve operational provenance outside
Git. Restore previous Compose/source/env and affected services only. Test gate
rollback: airflow-gatk-test/gatk_runtime_gate.py.pre-81587fc. Production GATK
can be disabled without deleting its new directories. Keep migration0019
tables on rollback: downgrade would destroy GATK audit state. Never delete
original repositories, databases, pending files, FASTQ, SFS/OBS or results.

Remaining non-release scope:3 known WGS backend assertions and2 existing WGS
frontend assertions are not green; no WGS changes were added to this GATK
promotion to conceal them. The broader pending/Samplelist research remains
documentation only, ready for development from the new test worktree.
