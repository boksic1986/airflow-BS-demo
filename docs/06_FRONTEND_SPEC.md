# Frontend specification

2026-09-11 WGS Logs search is debounced350ms and sent to the registered-log API, not filtered against the last200lines. Query participates in silent refresh identity so old query/source responses cannot win. Keep previous excerpts while searching; label tail truncation and incomplete server scans. Current-attempt declared child logs appear in Other rule logs. No hidden-tab polling or workflow mutation.


Attention title/detail body is a separate grid with6px rowgap and1.45 lineheight, independent of trailing action controls. Deployed index-xQ3eaWmc.js/index-CXQ9-KPd.css.

Run Tracker default excludes cancelled records; 已取消记录 filter opens retained history. Cancellation rows label project sample scope, current stage and progress as 提交已取消 without pending progress/ETA bar. Database audit is not deleted. Deployed index-TVfCIH75.js.

Config-review cancellation: wizard header and incomplete Attention card expose separate Cancel submission control (never nested in resume link). GET server preview before confirmation; explicit red confirm POST includes attempt. Only config_review or cancelling_submission retry shown; no preparation/post-config control. Success removes card and shows cancelled, not preparation failed. Failure retains dialog/error; cancelling tasks remain discoverable. Modal discloses all files/pending retained. Deployed index-BhloDDFv.js supersedes prior bundles below.

2026-09-11 incomplete manual WGS submissions appear in both Submit Run and Dashboard Attention required. Discover server-saved active runs through existing paginated run API and current details; show preparing_sampleinfo/config_review/preparing_analysis/execution_review only, exclude auto_dispatch and terminal/approved runs. Whole card resumes `/submit?pipeline=wgs&analysis_id=...` without creating/approving a run; include batch, phase, attempt and created timestamp. Shared silent refresh retains cards on error and removes them after approval. This is server task discovery, not browser-only draft storage; incomplete actions are not dismissed into ordinary alert history. Production bundle index-DyxeD4eP.js supersedes prior bundle below.

2026-09-11 submission recovery: WGS wizard stores only opaque `analysis_id` and pipeline in URL after successful creation. Reload restores that existing run through GET; missing/error state keeps its link and blocks duplicate creation, without automatically approving configuration or execution. Config review uses existing sample inventory only when selected projection is empty, filters exact analysis_id/current selection_attempt/candidate, paginates all rows and labels candidate (not running). Run Detail remains selected-only. Candidate inventory failure retains last reliable state. Final production bundle index-BsfeK10d.js.

2026-09-12 Attention:14px severity markers; compact independently scrolling list; information entries collapsed under history. Confirm/restore persisted in current browser only, condition ID/detail changes reappear; does not resolve workflow failure or remove audit data. Duplicate-family details identify family and batches. SFS Total shows cloud metric when present, otherwise complete read+write sum labelled “读＋写计算”; absent inputs produce unavailable/gaps, not invented zero. Read/write/Total share scale. Server96 production has no total_bps currently; fallback is not equivalent to console one-minute MAX aggregation.

2026-09-11: shared `useSilentRefresh` replaces page timers: visible10s/hidden60s, foreground immediate, serialized requests, stale scope/attempt response fencing and20/40/60s error backoff. First load only shows loading; subsequent errors retain tables and show lightweight hints. Detail refreshes summary/current tab only; transfer cards/files retain stable keys and expansion. Remove Run Tracker Sync and Run Detail Sync Airflow. Unknown selected scope displays “待确定分析范围”; global pending remains visible with reason. Automated regressions passed; live browser visual acceptance remains open. See [release evidence](selection-refresh-20260911.md).

## T240 attention dashboard and Sample Information

- Command Center removes the duplicate Runs/Samples/QC/Workflow-fails strip,
  Status distribution and 7d run activity. Operations overview contains an
  actionable Attention required list and Sample throughput; the throughput
  card gives `Total` primary visual weight.
- The WGS intake panel is named `WGS Intake Queue`. It has no Pending/History
  switch and renders only unlinked ready batches, failed linked analyses and
  needs-review batches. `no_new_wgs` and linked queued/running/success rows are
  intentionally hidden because their operational state already belongs in Run
  Tracker.
- Run Tracker status badges are centered within the Status column.
- The Samples route is titled `Sample Information`, has no inventory subtitle,
  and uses exactly these columns: Sample / family, Batch, Order, Relation /
  type, Project / run, Status. Order is masked, Pipeline and FASTQ files are
  removed, and an optional backend `status_reason` may appear below Status
  when db_v2 supplies authoritative evidence.
- Background polling preserves the loaded DOM and updates data in place; it
  does not replace the page with a full-screen loading state.

## Registry-driven shell

The navigation, pipeline filters, workflow catalog, and deployment availability consume `/api/platform/capabilities`. The shell must tolerate a rolling upgrade response that contains only `deployed_pipelines` and normalize it into minimal registry definitions.

The T228 candidate displays WGS and GATK Cloud when both registry entries are
deployed. GATK has its own submission adapter; it is never routed into the WGS
form.

T235 uses one always-visible segmented `Pipeline` switch inside the submission
form. WGS and GATK Cloud remain visible without opening a native select.
Selecting a new pipeline updates the URL and remounts the corresponding
adapter, so WGS batch state and GATK project-preview state cannot leak across
workflows.

The GATK form reads `/api/pipelines/gatk/release` and displays the approved
profile, revision and execution state before the operator enters a project.
When execution is disabled, preview remains available but confirmation is
disabled with an explicit environment-state message.

T233 applies the same capability boundary to Command Center intake. The T7
scanner is shown for All pipelines and WGS because WGS declares `intake`; when
GATK Cloud is selected the browser neither requests GATK intake nor renders the
WGS scanner panel. Scanner failures remain isolated from Run Tracker and
resource panels.

Submit navigation and dashboard calls-to-action are visible only when a deployed, enabled registry entry declares both `submit_enabled` and the `submit` capability and also has a registered frontend submission adapter. The current staged WGS form is an explicitly namespaced adapter UI; a future submit-capable pipeline without its own UI cannot be routed into the WGS form, and the route fails closed instead of issuing WGS API calls.

## Run views

- Dashboard and Runs display shared run status and adapter-projected stages.
- Run Detail renders shared evidence, progress, samples, QC, logs, artifacts, transfers, and lifecycle sections when capabilities provide them.
- QC and workflow stages are rendered from backend projections; the browser does not parse workflow files.
- Disabled capabilities show an explicit unavailable state rather than a mock action.
- GATK submission is a two-step manual flow: controlled project path preview,
  then one confirmation. SCMC samples are shown as locked rows. The Run Detail
  hides QC and reanalysis actions that GATK v1 does not provide.

### T227 WGS detail refinements

- One visibility-aware five-second workspace poll drives both Current Progress and the active Transfer card. Percent text and progress values use the same one-decimal projection.
- Transfer summaries show progress, aggregate speed, file count, start, finish, and last update. File rows use a short progress bar, start/finish timestamps, checksum badges, and distinct accepted/running styles.
- Overview shows a privacy-safe batch manifest summary. Samples omits the duplicate Data column and remains the sample analysis-state matrix.
- Pipeline evidence is limited to pinned release/runtime identity, execution target, and a controlled relative project path. Current Progress and evidence keep a responsive 2:1 layout with equal desktop heights and slightly relaxed text spacing; narrow layouts return to natural content height.
- Rules request `active_first`; not-started, running, and terminal timestamps are displayed without inventing missing evidence.
- Batch Runs falls back to `workflow_status`/`workflow_label` when detailed stage rail data is absent.
- Failed Step7 actions keep generation history visible and offer a revision-fenced retry only when the backend reports it safe.

### T229 live refresh and workflow history

- Run Tracker keeps publishing/downloading batches ahead of completed rows. Workflow rails consume the restored adapter projection.
- Step1-Step6 cards use a 2px border: current is blue, success green and failed red.
- Expanded transfer files keep the existing table during five-second refresh; active downloads appear before accepted and completed files.
- Run Detail refreshes workspace plus only the active tab data and never replaces a loaded page with a full-page loading state.
- Workflow Catalog uses the registry display name and shows the five newest run records per deployed pipeline through the generic run-list API. Current production displays `WGS`.

### T230 responsive Run Tracker columns

- At viewports up to 1920 CSS pixels, Run Tracker uses compact widths for Project, Batch, Pipeline, Status, Data lifecycle, Current stage, progress, runtime, Started and Finished while preserving the existing font sizes.
- Wider displays retain the original column widths. Started and Finished headings and values are horizontally and vertically centered, with date and time kept on separate non-breaking lines.

### T231 compact centered Run Tracker cells

- Run Tracker headings and cells are horizontally and vertically centered for consistent row alignment.
- At viewports up to 1920 CSS pixels, Project, Batch, Pipeline, Status, Data lifecycle and Current stage use a smaller responsive type scale; their nested links, badges and secondary text align to the cell center.
- Wider displays retain the existing T230 type scale and column widths.

### T237 workflow lifecycle and operations layout

- Workflow Catalog remains the registry-backed capability view and adds a read-only lifecycle table for Workflow, Cloud release, and Result delivery. Pipeline, cloud status, delivery status, and keyword filters operate over the 200 newest deployed runs with 20 rows per page; a failed lifecycle badge links to Run Detail and does not expose a release action.
- Capability cards show the three newest runs per deployed pipeline. Lifecycle state is consumed only from the generic optional run projection, so adapters without a lifecycle projector display `unavailable`.
- Run Tracker omits the non-actionable Data lifecycle column, restores normal typography, keeps Project metadata left aligned, centers the remaining operational cells, and right-aligns the Stage progress percentage above its bar. Submitted and Started use one text style and line height in Batch Runs.
- Analysis node selectors use the same 32px pill geometry and typography as the SFS resource tag. The three resource panels live inside the Dashboard main column, share height/meter geometry, and SFS I/O shows only Read, Write, and Current IOPS.
- The WGS scanner column says `最近检查`, reflecting that every row in one 30-minute shallow scan shares one observation time.

### T239 Run lifecycle and Run Detail completion

- `/workflows` is a full-page `Run lifecycle` view. The capability catalog header, capability cards and duplicate recent-run list are removed; the sidebar label is also `Run lifecycle`.
- The lifecycle table keeps Pipeline, Cloud release, Result delivery and keyword filters, adds a QC status filter and QC column, and continues to use the generic deployed run-list projection.
- Run Detail adds a fifth Batch QC metric derived by the backend from all sample QC states. Workflow lifecycle shows the run operator's privacy-safe display name.
- Step7 SFS cleanup status and controls live inside the Cloud release lifecycle card. The default view is compact; an administrator expands the action only when a safe first request or revision-fenced retry is available. Exact batch confirmation and destructive-action acknowledgement remain mandatory.
- Current Progress fills the same desktop card height as Pipeline evidence, vertically centers its main content with relaxed spacing, and returns to natural padding on narrow screens.

### T241 obsutil transfer progress

- Transfers identifies the active engine as `obsutil` when the backend exposes
  the controlled checkpoint marker.
- A planned or running file with no checkpoint bytes displays `Waiting for
  checkpoint`. Exact bytes, checksum state, active-file-first sorting and the
  existing no-flash refresh behavior are unchanged.

## Branding

The product label is `NGS Huawei Cloud` with the subtitle `Online analysis platform`. WGS names remain only where they identify the currently deployed workflow or extension.
