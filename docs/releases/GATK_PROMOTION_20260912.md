# GATK promotion execution record

Status: in progress; not published/deployed.

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
- [ ] GATK selective port and unrestricted-source tests.
- [ ] Test acceptance and review.
- [ ] main publication and development worktree.
- [ ] Test/production deploy and manual GATK capability verification.

Task/source sharing review: GATK port and deployment intersect only config/runtime interfaces; production WGS fixes must remain. Git layout and code port use the same independent clone but only coordinator changes Git refs. No other development worktree is modified.
