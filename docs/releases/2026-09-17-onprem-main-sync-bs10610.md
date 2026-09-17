# BS10610 production-code + native monitoring synchronization

User requests latest production application fixes on the test panel while keeping
the accepted WGS Local/SGE registration/monitoring APIs. This is test deployment
authority only, not Local/SGE promotion into main/production or real analysis.

## Source and boundary

- Integration branch: jiucheng/test/wgs-local-main-sync-20260917.
- Production/main base c6ac6ce (application QC counts4e9196d).
- Native source cb84ec2 from the authoritative BS10610 development Git branch,
  including accepted d705a46 native deployment. Original dirty Windows feature
  worktree and server untracked review archives are preserved.
- Resolve sampleinfo-path conflicts using main's readable-source semantics;
  preserve native prepare-target freezing and conditional CCE arguments, alongside
  main's release/runtime pins and exact prepare-check overrides.
- Keep both dated documentation histories. No new feature or native WGS script
  modification. No patient data or runtime configuration enters Git.

Preflight: server10610, control root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`. Backend/observer actually
mount onprem-main-d705a46; frontend mounts onprem-review/frontend-dist. Current
symlink is historical. Five business records are terminal, including the paused
failed GATK smoke. Native registration/launch/monitor true; scan/dispatch false;
native webpage-prepare gate false. Keep all these flags and test roots unchanged.

## Verification and deployment

Cached BS10610 targeted backend/native/QC/submission/runtime checks:100 passed,
1 opt-in WGS-owner controller test skipped (owner source not mounted). Existing
synthetic controller acceptance is retained, not repeated as a real analysis.
Frontend NativeExecutionPanel/WgsQcTab/SubmissionOptions:13 passed; TypeScript/Vite
build passed, assets index-t9Ucf9lx.js and index-BFPGoplr.css. No dependency pulls.
The first backend test container lacked repository /config and13 sampleinfo tests
failed with FileNotFoundError; mounting read-only repository config resolved all.
Application code was unchanged by that harness correction.

## Published test application

Application commit282dfb09a950496a6e998ec797f913923db41e65 is deployed under
`releases/20260917-onprem-main-282dfb0`. Backend82958ac39f8a and
observerde8573f1b972 mount its complete backend; frontend31d12b50e275 mounts
its frontend-dist. Native schema/mounted DAG files compare identical, so no
Airflow restart or migration. Other7 container IDs, all environment key-values,
image IDs, non-code mounts, network and ports are unchanged.

Private composition/rollback/inventory:
`candidates/onprem-main-282dfb0-control`. Compose config passed; only backend,
wgs-run-observer, frontend-nginx recreated with --no-deps --pull never. The
orphan warning refers to preserved other services; no --remove-orphans used.
Nginx configuration/reload passed. Actual gateway /api/health and JS return200;
empty login request422 proves API proxy routing. Internal health/db/Airflow200,
scheduler and metadatabase healthy; optional triggerer/dag-processor remain null.

Authenticated native route inventory and existing synthetic native-view GET200:
2 executions retained, current wse_7dce0d6aef85f76d2206983d,1 rule. Existing5 run
records remain4success/1failed; GATK smoke remains paused, no new run. Registration,
launch and monitor flags true, platform instance bs10610-onprem-review; native
webpage prepare remains false, scan/auto-dispatch false. Approved project roots
and snapshots unchanged. This proves API readiness, not new real Local/SGE compute.

Rollout helper initially used str.removeprefix unsupported by host Python; fixed
the helper only before any service mutation. Post-check initially requested
authenticated OpenAPI anonymously (401), then succeeded with existing in-memory
internal token. Environment list order changed in Compose; comparison by actual
key/value confirmed no setting changed. No credentials were printed or copied.

Neither main/production ref nor BS96 service was modified by this publication.
No DB migration is expected: accepted native schema0026 already exists. Do not
copy production DB, Clinical paths, credentials or scanner configuration.

## Rollback

Retain preceding code and exact private service composition. Use private
rollback.json with explicit backend wgs-run-observer frontend-nginx only,
--no-deps --pull never, followed by nginx reload. Rollback changes
application source/static assets only; preserve DB, snapshots, pending, projects,
GATK smoke pause and existing runtime/image/environment pins.
