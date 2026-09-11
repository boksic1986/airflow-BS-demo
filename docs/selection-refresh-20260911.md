# Selection, pending and silent refresh release

## Scope and evidence

Authorized production exact-source patch, not a Git release. Production root is `/data/airflow-WGS/releases/20260910-t260-recovery-runtime-r1`. The tested candidate is `.codex-runtime/selection-release` locally and `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/test-candidates/selection-refresh` on BS10610. The local checkout contains older production differences: do not copy it wholesale to production.

Backend changed modules: main, dashboard_service, diagnostics_service, operator_resources_service, pipeline_registry_service, run_service, wgs_observer_cli, wgs_platform_service, wgs_sample_projection, wgs_workspace_service; new sample_selection_scope, sample_selection_repair, observer_airflow_sync. SHA256 before/after inventory is `backend-manifest.json` in the candidate and `/data/airflow-WGS/candidates/selection-refresh`. Frontend candidate source is `frontend-src`, production dist is `dist`; shared `lib/useSilentRefresh.ts` covers dashboard/list/detail pages and transfer files. WGS changes only `prepare/pending.py` and `prepare/prepare_wgs_batch.py`; manifest is `wgs-manifest.json`.

No new DB tables. Current-attempt receipt decisions are stored separately from execution status in existing metadata. Run Detail and run/dashboard counts use selected only; global Samples retains pending/reason. Legacy records without scope evidence retain legacy behavior. Unknown new-attempt scope is not a candidate count masquerading as an analysis count.

Remote targeted acceptance:13 backend pytest cases,6 pending unittest cases,10 Vitest cases; TypeScript check and one Vite production build. Cached images only, no Docker Hub, no real analysis submission. Backend command: `docker exec -w /opt/selection-refresh -e PYTHONPATH=/opt/selection-refresh airflow-wgs-backend-1 python -m pytest -p no:cacheprovider /opt/selection-refresh/tests -q`. Frontend uses cached `airflow-demo/frontend-build-test:node22-lock-35420d5e3ec0` with `--pull=never --network=none`. Pending uses BS10610 WGS Python/unittest and synthetic records.

## Production verification

0907C a3 selected6/pending6;0907D a5 selected10/pending6;0908A a5 selected3/pending4;0908B a6 selected5/pending4;0909B a1 selected5. Legacy0906B9 unchanged. API0907C sample_count6/sample_scope_status ready, pending filter total20; pending remains pending despite parent failed/running status. No audit rows deleted.

Private historical TSVs stayed remote. Full columns, descriptor SHA256, row counts and receipt identity validated before locked merge. Existing local ledger6->26, preserving earlier6 and adding20. Do not reconstruct full TSVs from redacted receipts. The runtime gate currently supplies prior-generation private payload or an empty header; prepare merges that input with the latest local ledger. Full-record database exports, when supplied as pending input, use the same conflict-aware merge; this change does not introduce a new private-data DB export API.

Health `/api/health` ok; index references `index-DJFx-BjS.js` and `index-GaK031bY.css`. Three active Master UIDs retained; Worker/scheduler/scanner container IDs/start times/mount sets unchanged. Observer event ingestion advances with errors0. Browser bridge failed during visual acceptance; automatic no-flicker regressions pass but continuous live-browser observation remains outstanding.

## Deployment and rollback

Backend patched by before/after SHA256 guard then restarted only backend and wgs-run-observer. Old source in `<release>/rollback/selection-refresh-20260911/backend`. Frontend old index at sibling `frontend-index.html`; old hashed assets retained. Restore backed-up index to roll back frontend; restore exact backend files and restart only affected services for code rollback. New helper modules may remain unused after code rollback.

WGS node200 exposes source read-only. Applied through verified BS10610 writable alias `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0`; no chmod/remount. WGS two-file backups at BS10610 candidate `rollback/prepare`. The node-side controlled candidate path is `/sg2/50.ctapa/project/HWcloud/WGS_test/cce-evidence/selection-refresh-20260911`; historical backfill tool lives there. Restoring code must not delete or replace pending ledger, sample audit rows, receipts or analysis data. Do not roll back clinical computation or rerun0908B.

Operational scripts retained locally: `.codex-runtime/selection_deploy.sh`, `selection_deploy_ui.sh`, `selection_repair_apply.sh`, `selection_verify.sh`. Deployment first stopped safely at read-only WGS source after backend files were written; UI/backend restart completed separately and prepare was applied through BS10610. Do not blindly replay deploy scripts over later source changes.
