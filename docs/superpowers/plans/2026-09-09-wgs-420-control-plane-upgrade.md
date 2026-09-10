# WGS 4.2.0 Control-plane Upgrade Implementation Plan

1. Add failing catalog tests for schema 4, current-release selection,
   historical lookup and release evidence; implement the catalog and update the
   WGS/pipeline configs.
2. Add failing runtime-gate tests for allowlisted per-release repositories,
   4.2.0 handoff request generation, receipt validation and 4.1.1 legacy
   compatibility; implement the gate changes.
3. Add failing backend tests for resolving historical run releases and importing
   privacy-safe candidate/selected/pending receipt rows; implement without a DB
   migration.
4. Add QC regression coverage proving the exact batch QC file outranks the new
   multi-QC companion file.
5. Update API, database, Airflow, frontend and deployment documentation plus
   CURRENT_STATE/TASKS/HANDOFF.
6. Run focused red/green tests and the broader backend, DAG, script and frontend
   regression suites on the remote development node using cached images only.
7. Build and verify `cce-pipeline 0.8.3` in
   `/sg2/50.ctapa/project/HWcloud/WGS_test`, then atomically update node200 with
   rollback copies.
8. With automatic dispatch still false and zero active runs/leases, deploy the
   immutable application release, recreate only code-caching services and verify
   health, release evidence, UI assets, container stability and unchanged run
   counts.

Formal WGS batches, Step7 cleanup and Step8 delivery are explicitly outside this
plan.
