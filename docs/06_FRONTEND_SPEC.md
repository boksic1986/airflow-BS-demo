# Frontend specification

## Registry-driven shell

The navigation, pipeline filters, workflow catalog, and deployment availability consume `/api/platform/capabilities`. The shell must tolerate a rolling upgrade response that contains only `deployed_pipelines` and normalize it into minimal registry definitions.

Current production displays WGS because it is the only deployed registry entry. Future adapters appear without modifying shared navigation or generic API clients.

Submit navigation and dashboard calls-to-action are visible only when a deployed, enabled registry entry declares both `submit_enabled` and the `submit` capability and also has a registered frontend submission adapter. The current staged WGS form is an explicitly namespaced adapter UI; a future submit-capable pipeline without its own UI cannot be routed into the WGS form, and the route fails closed instead of issuing WGS API calls.

## Run views

- Dashboard and Runs display shared run status and adapter-projected stages.
- Run Detail renders shared evidence, progress, samples, QC, logs, artifacts, transfers, and lifecycle sections when capabilities provide them.
- QC and workflow stages are rendered from backend projections; the browser does not parse workflow files.
- Disabled capabilities show an explicit unavailable state rather than a mock action.

### T227 WGS detail refinements

- One visibility-aware five-second workspace poll drives both Current Progress and the active Transfer card. Percent text and progress values use the same one-decimal projection.
- Transfer summaries show progress, aggregate speed, file count, start, finish, and last update. File rows use a short progress bar, start/finish timestamps, checksum badges, and distinct accepted/running styles.
- Overview shows a privacy-safe batch manifest summary. Samples omits the duplicate Data column and remains the sample analysis-state matrix.
- Pipeline evidence is limited to pinned release/runtime identity, execution target, and a controlled relative project path. Current Progress and evidence keep a responsive 2:1 layout without forced equal height.
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

### T232 wide-screen project source alignment

- The Project source row uses an explicit viewport-independent centered flex alignment, so the Intake/Manual badge remains centered on 4K displays as well as at the compact breakpoint.
- T232 does not change the 4K type scale, column widths, or the responsive rules introduced by T230/T231.

### T233 dashboard resource-panel alignment

- The resource-panel grid lives inside the Dashboard main content column below the T7 scanner, so its outer edges align with Run Tracker and the scanner table.
- The grid uses three equal columns on desktop, two columns at 1480 CSS pixels and below with SFS I/O spanning the second row, and one column at 860 CSS pixels and below.
- Analysis Node Health and Cloud Resources share 32px control tokens and a common meter layout with 16px label rows and 7px full-width bars.
- SFS I/O displays Read, Write and Current IOPS only. The redundant Total metric and binary-unit explanatory sentence are omitted.
- The T7 WGS discovery table labels the batch timestamp as `最近检查`. The underlying scanner field, interval and refresh behavior are unchanged.

## Branding

The product label is `NGS Huawei Cloud` with the subtitle `Online analysis platform`. WGS names remain only where they identify the currently deployed workflow or extension.
