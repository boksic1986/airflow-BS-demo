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

Pending source parity, bounded test-only service rollout and post-release checks.
No DB migration is expected: accepted native schema0026 already exists. Do not
copy production DB, Clinical paths, credentials or scanner configuration.

## Rollback

Retain preceding code and exact private service composition. Rollback changes
application source/static assets only; preserve DB, snapshots, pending, projects,
GATK smoke pause and existing runtime/image/environment pins.
