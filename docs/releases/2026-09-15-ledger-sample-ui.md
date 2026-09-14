# LEDGER-01: Sample-aligned handoff ledger (not published)

## Delivered scope

- Reuse Sample data-table/sample-resource-table, StatusBadge, filters and pager;
  no new CSS or overlay. Current pending is the default; separate history view
  retains access to all rows and on-demand member receipts.
- Current pending filtering includes present_in_latest_complete before database
  pagination/count. Client also prevents old history rows flashing in current view.
- Current membership origin uses source_analysis_batch, falling back to the row's
  analysis_batch; never sequencing_batch. Existing full identity/HMAC is unchanged.
- Status and finite Chinese reason replace origin arrows/sync columns. Native
  missing-sequencing-batch wording maps to an existing safe code without copying
  free text. Unknown reasons display a verification-needed label.
- Sync diagnostics move to details; source/row sync errors remain visible.
- Selected evidence displays included-in batch, consumed evidence with destination
  displays handed-off-to batch; missing evidence never fabricates a destination.
  Receipt selection and handoff do not claim analysis/QC success.

Immutable historical selection projection/hash remains unchanged. Its legacy
origin_batch wire semantics are documented but not rendered as a source arrow.
No original WGS script, pending file, patient data, analysis/sample deletion,
DB schema, runtime preparation or automatic dispatch change.

## Checks

Test target BS10610/server10610, backend mount panel1fb971b and historical current
opt4d3d24e6 verified. Isolated candidate:
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ledger-ui-20260915.
Cached backend:t235-232154f and lock-bound Node22 builder35420d5e3ec0; all containers
--network none --pull never. Source read-only; no active service source modified.

RED: old source fails origin assertions and UI current-pending/style/history tests.
Pagination fixture initially omitted required content_version/last_good_at;
fixed fixture after reading model requirements, no product schema modification.
GREEN: test_wgs_file_reference.py9 passed; SamplesLedger.test.tsx5 passed;
TypeScript/Vite build passed1852modules. Cases cover source fallback/explicit source,
stable identity/unchanged selected projection, original file bytes unchanged,
server pagination, current/history UI, selected-vs-consumed and sync/unknown reasons.
Final CSS remains index-CdK5PwQa.css; JS build index-wx5Mpa0a.js. No live-browser
visual acceptance claimed. Final upload hit one pre-session SSH abort; retried
before final test/build. No full biological or production tests.

Commands: isolated backend python -m pytest -q -p no:cacheprovider on the one test
file; isolated builder npm test -- --run src/pages/SamplesLedger.test.tsx followed
by npm run build. Local git diff --check verifies text hygiene only.

## Deployment / rollback

Publication remains deferred. Later rollout must pair backend API, reference
worker projector and frontend from the reviewed source; their live mounts can
be pinned to different releases. Normal worker sync updates current origins;
do not rewrite immutable receipts, manually patch DB, or replay prepare.
Existing last-good rows stay visible with error warning if source is unavailable.
Do not force historical six-row membership to match an old screenshot after real
handoffs. No Airflow scheduler/worker or current analysis needs restarting for
this UI/projection change. Preserve nginx allowlist, pending and retained runs.
Rollback the corresponding application/worker source and frontend only; never
restore stale pending, remove sample history or clear current analysis tasks.
