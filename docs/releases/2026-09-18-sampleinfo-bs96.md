# BS96 same-batch import and Step2 reference publication

User authorized merging main and production and deploying BS96. Application
source9ff67d34157144ac2c942100922b9c3643667187 was fast-forwarded and atomically
pushed to main and jiucheng/release/production; production clone main synced.
The later documentation commit records this release without changing its binary.

## Scope and preflight

- Allow the source analysis batch when the exact target project is absent;
  retain existing-directory/symlink rejection, idempotency and source validation.
- Restore saved use_reference for new/recovered Step2 runs; protect it from
  Step1 defaults and preserve unconfirmed edits across same-value polls.
- server96, configured BS96 owner chenjc6708:bioinfo520. Real backend source was
  ui-4f4d45a, not historical current. Compared full application file sets/bytes:
  only app/wgs_sampleinfo_upload.py changed in the deployed backend.
- 10 runs before cutover:8success,1failed,1cancelled, no active run. Health,
  capabilities, runs and dashboard API requests200 before deployment.
- Only backend/frontend change; no scanner, observer, reference-worker, Airflow,
  PostgreSQL, Redis, metrics/probe restart; no auth/gate/config changes.

## Build and deployment evidence

Release: /data/airflow-WGS/releases/20260918-sampleinfo-9ff67d3.
Private control: /data/airflow-WGS/sampleinfo-9ff67d3-control (2700).
compose.json, rollback.json and before.json are owner-only; never copy to Git.
Source archive SHA256:
5edf9dff0b4eea98a7e392898f94043624903fc9b4b9d9f84488e5e5eb067305.

Prior BS10610 isolated acceptance:16backend,1runtime,10frontend tests and build
passed; retained, not rerun. BS96 used cached Node22 lock35420d5e3ec0 builder
and nginx1.30.3-local-contract runtime. Offline Docker --target build,
--pull=false --network none; TypeScript/Vite and static image build exit0.
Assets index-CRIjUB8d.js/index-UzgQaua7.css match the prior test build.

Frontend image airflow-demo/frontend:sampleinfo-9ff67d3:
sha256:54739d6c9098fa5509070856ad92ebfa89face280813d7648bc02573d77b9fa6.
Backend image unchanged:
sha256:0e2d6f0cdf4b89b5ade30b3855cdb8593f33e4c23085a0f5adcd644095cf6912.

At2026-09-18T08:44:03Z, Compose config/up exit0 and nginx syntax/reload passed.
Backend342e86a9f10c ->e177f1eddc01;
frontendb92af6923f78 ->8bef173a7235. Other10service IDs unchanged.
Compose orphan warning is expected for intentionally isolated two-service
composition; no --remove-orphans or global compose operation was performed.
All environment key/value pairs, command, entrypoint, user, working directory,
restart policy, network names, port bindings and unrelated mounts compare equal.
Global current, gateway config and automatic intake settings unchanged.

## Live acceptance and limits

- Gateway172.17.61.96:12959 index, new JS and CSS200; exact bytes match artifact.
- Live backend module SHA256 matches release:
  6e70c1e7a298ddfc939cab7919629dc468772c8ccfdd29a23d418d239808d9d2.
- Gateway health200/0.011s, capabilities200/0.006s, runs200/5.223s,
  dashboard runs200/0.478s immediately after deployment.
- A separate run WGS_20260918_084442_6317DF was created at08:44:42Z and submitted
  at08:44:43Z, after cutover; post-check counts11with1running. This task sent
  no real import, configuration approval or analysis submission, and did not
  cancel, pause or alter that run. Its origin was not inferred from the count.
- No DB migration/manual writes, biological execution tests, workflow runtime
  update, offline project modification, pending/result/history deletion.
- No browser-driven real submission performed. User may refresh and continue
  intended confirmations; target directory existence still blocks overwrite.

## Rollback

Only if a rollback is required, first recheck current activity/authorization:

```bash
docker compose -p airflow-wgs -f /data/airflow-WGS/sampleinfo-9ff67d3-control/rollback.json config --quiet
docker compose -p airflow-wgs -f /data/airflow-WGS/sampleinfo-9ff67d3-control/rollback.json up -d --no-deps --pull never backend frontend-nginx
docker exec airflow-wgs-frontend-nginx-1 nginx -t
docker exec airflow-wgs-frontend-nginx-1 nginx -s reload
```

Then check real gateway assets/APIs. Do not roll back/delete databases, project
directories or analysis outputs. No cleanup was performed; artifacts and the
stopped build-extraction container remain for bounded release evidence.
