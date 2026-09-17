# BS96 UI, Phase and ledger publication

User explicitly requested production deployment and diagnosis of simultaneous
dashboard Failed to fetch warnings. Source4f4d45a56ad19e09597b175ec33183df7a9648cb
was already verified/pushed to main and jiucheng/release/production. Application
changes remain the previously approved UI fields/filters, exact Phase mappings,
child timing projection and ledger receipt reader; no new application patch.

## Preflight and scope

- server96, configured BS96 owner chenjc6708:bioinfo520. Historical ctapa login
  cannot read owner-only control files; correct configured owner can. No access
  widening, credential copying or Docker-based permission bypass.
- /data/airflow-WGS and releases hanjj:bioinfo2770; control0700/data0600.
  New release0755, files0644; temporary exact write/read/remove probe passed.
- Actual backend was qc-all-counts-4e9196d; worker sampleinfo-f72a12e. Verified
  source differences, per-service environments, commands, entrypoints, mounts,
  images and networks against original readable private Compose files.
-0915B/WGS_20260917_144921_6CC4BB success; Airflow success and all tasks
  success/skipped. Platform had9runs, no active run at cutover.
- Backend receives7approved changed application files. Reference worker clones
  its own prior source and replaces ONLY app/wgs_file_reference.py. No observer,
  Airflow, scanner, metrics, probe, database or Redis restart.

## Deployment

Release: /data/airflow-WGS/releases/20260918-ui-4f4d45a.
Private composition/rollback/inventory: /data/airflow-WGS/ui-4f4d45a-control.
Backend1dc96daabc2d ->342e86a9f10c; frontend721f3e76239e ->b92af6923f78;
reference-worker3a490c0d1d53 ->deb7a4d5b7aa. Other9containers retained IDs.
Source/dependencies/images for backend/worker unchanged except approved mounts.
Frontend imageb77dc1142fbe097ac9a8e05bf368528c835c91accfb4b4e2c7d782d7e30349d3.

Production offline Docker build used cached Node22 lock35420d5e3ec0 builder,
--target build (TypeScript/Vite), --network none and --pull=false; cached nginx
1.30.3-local-contract runtime. No dependency upgrades/downloads or full-suite
rerun. Prior BS10610 focused acceptance is recorded with source promotion.
Compose config --quiet passed; up --no-deps --pull never only3named services.
Nginx syntax check and graceful reload passed. Global current not repointed.

## Live acceptance and screenshot diagnosis

- Real gateway172.17.61.96:12959 health/index/newJS/newCSS200.
- Dashboard runs200/0.094s, intake200/0.014s, resources200/0.220s.
- All390Rule rows mapped across19known phases; no Unknown. Exact filter options
  returned.6selected manifest rows have all requested Name/hospital/order/test
  project/sample-type fields; only counts/field names inspected in evidence.
- Reference source ready with no sync_reason; pending0; no history deletion or
  pending edits.0915B remained success. Automatic scan/dispatch and activation
  watermark unchanged; scanner remains600seconds.
- BEFORE publication APIs were already200/0.019-0.145s; real client access logs
  also200. Prior2h gateway logs contained no499/502/503/504/upstream timeout.
  The screenshot failure is not reproduced; a transient client-to-service issue
  is possible, not proven. No speculative code/network/authentication fix.
- Host loopback gateway request403 is existing Docker source/ACL behavior;
  real gateway IP200. Allowlist unchanged. No clinical data in Git artifacts.

Rollback validates rollback.json and restores only these3services, then nginx
reload and gateway checks; never rollback/delete database or workflow outputs.
Unused extraction container/source archives remain for bounded release evidence;
no broad image/container cleanup. No real workflow test or analysis submission.
