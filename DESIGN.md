# Airflow Demo Frontend Design System

## Style

Professional, restrained, high-density, low-noise. The UI should feel like a laboratory production monitoring console, not a marketing dashboard. It should help a bioinformatics operator answer:

```text
What is running?
What failed?
Which sample/rule/log caused it?
Can I resume without rerunning everything?
Which QC metrics need attention?
```

## Layout

- Persistent sidebar: Dashboard, Submit Task, Runs, Samples, Workflows, Failures, Settings.
- Persistent topbar: environment badge, search, user/demo menu, Airflow link.
- Main content uses a constrained readable width for forms and full-width dense tables for operations.
- Cards use radius `8px` or less.
- Avoid cards inside cards; use sections, panels, tables, and tab surfaces.
- Tables are compact, scannable, and horizontally scrollable when necessary.
- Run detail uses a summary header, workflow/QC overview, then tabs.

## Color

Use neutral backgrounds and limited status color:

```text
background: #f5f7fa
surface: #ffffff
border: #d9e2ec
text: #172033
muted text: #637083
accent: #176b87
queued/created/skipped/unknown: neutral gray
running/submitted: blue
success/pass: green
warning/warn: amber
failed/fail/error: red
canceled/terminated: slate
```

Status color is never the only signal; icons and labels are required.

## Components

StatusBadge:

- Handles created, queued, submitted, running, success, failed, warning, canceled, terminated, skipped, pass, warn, fail, unknown.
- Includes icon and text.

MetricCard:

- Props: title, value, unit, trend, description, status.
- Used for dashboard and QC.

PipelineCard:

- Shows pipeline name, summary, version, owner, backend, reference, latest run, success rate, and action.

RunTable:

- Shared list component for Runs and Dashboard summaries.
- Supports search, filter, sort, status badges, and actions.

WorkflowTimeline:

- Stepper/timeline for Airflow tasks, Snakemake rules, and qsub steps.
- Demo v2 is not a DAG graph; the structure must allow future React Flow replacement.

QcMetricCard:

- Highlights pipeline-specific metrics and QC status.

LogViewer:

- Monospace output.
- Streams: metadata, stdout, stderr.
- Search, copy visible excerpt, fixed-height scrolling, missing-log state, error-line highlighting.
- Failed run defaults to stderr.

SampleSheetUploader:

- Supports csv/tsv parsing in-browser for preview.
- Shows row number and field-level validation errors.
- Does not submit invalid rows.

PipelineSelector:

- Clear pipeline choice with WES/PGT-A/NIPT/WGS distinctions and implementation status.

ErrorPanel:

- Shows failed step, exit code, error log path, stderr excerpt, possible reason, suggested action.

## Interaction

- Submitting a task must always have an explicit preview step.
- Reanalysis actions must say whether they reuse the workdir.
- `resume` and `rerun_rule` must never imply `--forceall`.
- Logs must not expand page height without bounds.
- Error panels should point users to the next diagnostic action before suggesting SSH.

## Accessibility

- Statuses include icon plus text.
- Buttons have explicit labels.
- Tables have visible column labels.
- Loading, empty, and error states are textual and screen-reader visible.
- Keyboard navigation must work for sidebar, tabs, filters, and log controls.
