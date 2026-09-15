# Prior repairs: Git synchronization, 2026-09-15

## Scope

Latest user approval: synchronize prior repairs to main and production repository.
No deployment, restart or analysis operation. Normal production checkout:
`D:/pipeline/airflow-demo-production`; release branch `jiucheng/release/production`.
Keep other worktrees, dirty operational notes and CCE0.8.5 development unchanged.

Starting main/production/origin refs:93ad66c. Recovery0860412 contains four repairs
not yet on main:c353ef6 SSH reconnect,76d58d5 local runtime timezone,33598aa shared
transfer progress,0860412 ledger presentation/current membership. Evidence3091b2c
adds verified same-attempt transfer restart projection and audited WGS34bfcbf phases,
plus shared group table/diagnostics. Earlier GATK/download/resource fixes are
already ancestors of main. Preserve main's extra documentation commit93ad66c.
No scientific pipeline/prepare/pending selection code is changed by integration.

## Fresh verification

BS10610/server10610 preflight: current release20260912-opt-4d3d24e6; actual backend
mount20260913-panel-1fb971b, worker20260912-gatk-81587fcb; scan/auto bothfalse.
No active service mount edited. Isolated candidate:
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/git-sync-20260915`.
Git staged tree198bb7a519f644a2d68a092e49dd187081143812 archive SHA256
27e84a911556da6582bd6c9857e0a7f68e19b04d2aad56b6decd55576e0f706e matched remotely.
Later integration changes only documentation, verified by Git source diff.

All containers use `--rm --network none --pull never`; no runtime credentials or
clinical sources. Cached backend:t235-232154f, frontend lock-bound Node22
builder35420d5e3ec0, real Airflow:bs-control-841eb55. Tests:

- Backend `python -m pytest -q -p no:cacheprovider`: test_wgs_legacy_transfer_restart,
  test_wgs_observer, test_wgs_phase_release_34bfcbf, test_monitor_rules,
  test_wgs_timing_service, test_wgs_shared_transfer_progress,
  test_wgs_transfer_projection, test_monitor_estimates, test_wgs_file_reference,
  and scripts/tests/test_wgs_local_runtime_gate:136 passed in15.11s.
  Existing Starlette/AnyIO deprecation warning only.
- Real Airflow `python -m unittest test_bio_wgs_dag test_wgs_only_dags
  test_wgs_cloud_orchestration_contract test_wgs_ssh_retry`:40 passed.
- `npm test -- --run src/features/run-detail/RunWorkflowTab.test.tsx
  src/pages/SamplesLedger.test.tsx`:16 passed.
- `npm run build`: TypeScript/Vite1852 modules passed; JS index-CJCGiVTD.js,
  unchanged CSS index-CdK5PwQa.css.

Broader DAG discovery ran68 checks with one failure/two errors. Two deployment
contract assertions fail identically on an independently archived unchanged
main93ad66c: config/intake.wgs.yaml expects scan=false though baseline saystrue;
docker-compose.wgs.yaml lacks asserted GATK_FASTQ_ROOTS. The third is absent pytest
in the cached Airflow image while importing test_wgs_host_runner. They are not
new regressions and were not changed/hidden to turn the suite green. Integration
has targeted acceptance only; full suite and real workflow acceptance not claimed.
No dependency download, real analysis or production configuration change.

## Publication and rollback

Merge on the repair branch, preserving both state-document histories. Fast-forward
normal production main and local production release branch to the reviewed merge.
Use `git push --atomic origin main jiucheng/release/production` without force;
verify both remote SHAs with ls-remote and a clean production checkout afterward.
Publication result is reported in the task; runtime deployment remains separate.
Retain all pending, receipts, database history, outputs and active tasks. Revert
code through an explicitly reviewed commit if needed; no data/worktree deletion.
