# T240 Dashboard Attention and Sample Information Design

## Goal

Make Command Center an action-oriented operations page: remove duplicate summary widgets, surface only actionable intake rows and operational alerts, and simplify the Samples inventory without exposing raw order identifiers.

## Dashboard information architecture

The pipeline rail remains unchanged. The summary strip, Status distribution, and run-activity chart are removed. Operations overview becomes a two-card responsive section: `Attention required` occupies the larger column and `Sample throughput` occupies the smaller column. Sample throughput shows a prominent `Total N` label plus running, completed, workflow-failed, and QC-failed counts.

Attention items are read-only derived projections. They are ordered by severity and age and link to the related Run Detail where available. Categories are workflow failure, QC failure, excluded add-on pairs, FASTQ pair issues, reanalysis, cross-batch family recurrence, SFS cleanup overdue after 48 hours, and report delivery overdue. Missing evidence produces no alert rather than a fabricated failure. Reanalysis and expected add-on exclusions are informational; workflow/QC failure, pair issues, duplicate families, overdue cleanup, and overdue delivery require attention.

## WGS intake queue

Rename the panel to `WGS Intake Queue`. Remove the Pending/History toggle and request one server-side attention view. `no_new_wgs` is retained as audit evidence but never returned for this view. Rows linked to queued, running, or successful analyses are hidden. The visible set is failed linked analyses, `needs_review`, and unlinked `ready` rows, ordered failed, needs-review, then ready.

The backend joins `wgs_intake_batch.analysis_id` to `analysis_run` and returns `analysis_status` and `display_status`. The browser does not infer workflow state. Auto-dispatch remains paused and the scanner schedule/algorithm remains unchanged.

## Sample Information

Rename the page to `Sample Information` and remove its descriptive subtitle. The table columns are:

1. Sample / family
2. Batch
3. Order
4. Relation / type
5. Project / run
6. Status

Pipeline and FASTQ columns are removed. Batch and Run remain links to Run Detail. For WGS, `Project` is the controlled sampleinfo test project when available, with the analysis project/run as secondary context.

Raw order numbers are never stored or returned. WGS sample synchronization stores only a fixed masked projection (`****` plus the final four characters when at least four exist). Existing rows without the safe metadata display `-`. The existing JSON metadata column is reused, so no database migration or historical backfill is required.

Future db_v2 states may add `status_reason`; T240 tolerates that optional field but does not invent or display a reason when none is recorded.

## Safety and compatibility

- No analysis, scanner, Airflow, OBS, SFS, or lifecycle state is changed.
- No raw order number, patient identity, hospital, clinical note, absolute path, or FASTQ name is added to the public response.
- Existing overview response fields remain for rolling-upgrade compatibility even when the new frontend no longer renders them.
- Alert projection failures are isolated from Run Tracker, intake, and resource panels.
- Production rollout recreates only backend and frontend-nginx after confirming automatic dispatch is still paused and no active WGS run or transfer exists.

## Acceptance

- Status badges are horizontally and vertically centered in Run Tracker.
- Command Center shows Attention required and Sample throughput with a Total label; removed cards and charts are absent.
- Intake shows only failed, needs-review, and unlinked-ready rows and has no Pending/History controls.
- Sample Information has the six approved columns and never returns a raw order number.
- Focused backend/frontend tests and the offline frontend production build pass.
