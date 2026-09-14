# GATK Git synchronization, 2026-09-14

Source fix: development e5b9325, selectively replayed on main as ddf062a.
Scope: GATK concurrency and success dependencies, transfer lease terminal
reconciliation, waiting/progress display, rule sample enrichment/filter layout,
and explicit nonparticipating GATK Master exclusion from WGS Heavy validation.
No WGS prepare/ledger development commits or private runtime configuration.

## Verification

BS96 hostname server96, current /data/airflow-WGS/releases/20260912-panel-opt-4d3d24e6;
actual backend app /data/airflow-WGS/releases/20260913-panel-1fb971b/backend.
Tests used isolated /sg2/33.chenjiucheng/WGS_test/cce-evidence/gatk-git-sync-20260914,
not the live mount or database. Cached images, --pull=never, --network none:

- Backend pytest: progress_refresh, rule_sample_enrichment, transfer_terminal,
  transfer_wait, heavy_gatk_scope, runtime_service: 31 passed in 2.08 seconds.
- /usr/local/bin/python standalone DAG contracts: concurrency, release_failure,
  success_dependencies: all passed using real Airflow imports.
- Frontend npm run build: TypeScript and Vite succeeded.

Airflow image lacks pytest, so its test modules were executed through their
assertion-based __main__ entrypoints. No packages installed or environment changed.
Candidate application source matches the resulting main application source.

## Branches and boundaries

The older production branch is reconciled to the approved main tree with both
branch histories retained. This does not merge the development branch or publish
its unfinished WGS features. Normal atomic push updates main and production.
No services restarted and no running task changed. Existing CSS live overlay
must be included when deployment images are rebuilt; this task is Git archival.
Rollback uses a reviewed Git revert, never data/receipt/pending deletion.
