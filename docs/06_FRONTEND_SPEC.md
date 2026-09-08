# Frontend specification

## Registry-driven shell

The navigation, pipeline filters, workflow catalog, and deployment availability consume `/api/platform/capabilities`. The shell must tolerate a rolling upgrade response that contains only `deployed_pipelines` and normalize it into minimal registry definitions.

The T228 candidate displays WGS and GATK Cloud when both registry entries are
deployed. GATK has its own submission adapter; it is never routed into the WGS
form.

T232 uses one `Pipeline` select as the workflow switch inside the submission
form. It replaces the duplicate page-level segmented control. Selecting a new
pipeline updates the URL and remounts the corresponding adapter, so WGS batch
state and GATK project-preview state cannot leak across workflows.

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

## Branding

The product label is `NGS Huawei Cloud` with the subtitle `Online analysis platform`. WGS names remain only where they identify the currently deployed workflow or extension.
