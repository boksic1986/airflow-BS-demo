# Frontend v2 Spec

## Page Structure

The frontend uses Vite React with `react-router-dom` and a persistent shell:

```text
/
/dashboard
/submit
/runs
/runs/:analysisId
/samples
/workflows
/failures
/settings
```

The sidebar contains Dashboard, Submit Task, Runs, Samples, Workflows, Failures, and Settings. The topbar contains environment badge, search, API/Airflow links, and user/demo context.

## Resource Model

Runs are the primary resource and map to backend `analysis_run`.

Run fields shown in lists:

```text
run_id, pipeline, sample_count, status, submitted_by, created_at,
started_at, finished_at, duration, failed_step, qc_status, action
```

Sample fields:

```text
sample_id, family_id, pipeline, status, fastq_path, qc_status,
report_status, error_summary, action
```

Workflow fields:

```text
pipeline, dag_id, version, owner, execution_backend, reference,
required_inputs, outputs, last_successful_run, failure_rate, implementation_status
```

## Status Machine

Canonical statuses:

```text
created -> submitted -> queued -> running -> success
created -> submitted -> queued -> running -> failed
failed -> submitted (resume/reanalyze)
running -> canceled
running -> terminated
```

Additional display statuses:

```text
pass, warn, fail, unknown, skipped
```

Every status must render with icon and text, not color alone.

## Pipeline Differences

WES qsub:

- Uses mock WES Snakefile and mock qsub wrapper today.
- Shows family/sample-friendly fields, qsub job ids, stdout/stderr paths, QC depth metrics, and rerun rule/sample controls.

PGT-A:

- Uses server-path scan and controlled targets: metadata, dryrun_cnv, invalid_target, baseline_qc.
- Must distinguish workflow `success` from baseline QC `fail`.
- Shows PGT-A baseline QC metrics and generated QC artifacts.

NIPT qsub:

- Demo/mock surface only until DAG/Snakemake tasks exist.
- Expected fields include fetal fraction, chr13/18/21 z-scores, GC bias, and mapping rate.

NIPT docker:

- Images are preloaded but runner is not implemented.
- UI can show readiness and required inputs, but submit must be disabled or marked mock.

WGS:

- UI surface is roadmap/demo only.
- Expected fields include reference, variant calling target, coverage, contamination, and report artifacts.

## Page States

Every page supports:

- Loading: skeleton/card/table placeholder with clear text.
- Empty: explains what is missing and what action creates data.
- Error: error panel with backend code/message when available.
- Success: shows current data with timestamp and action affordances.

## Run Detail

Run detail layout:

- Summary header: run id, pipeline, status, duration, sample count, created time, owner/demo user, action buttons.
- Workflow overview: Airflow DAG state and Snakemake/qsub rule timeline.
- QC summary: professional metric cards with pass/warn/fail/unknown counts and pipeline-specific metrics.
- Tabs: Overview, Samples, Workflow, QC, Logs, Files, Config.

Logs tab:

- Supports metadata/stdout/stderr streams.
- Failed runs default to stderr.
- Supports search, copy visible excerpt, fixed-height scroll, and highlighted error-ish lines.
- Missing logs show a clear empty state.

Failure diagnosis:

```text
failed_step, exit_code, error_log_path, stderr_excerpt, possible_reason, suggested_action
```

## Submission

Task submission supports:

- Pipeline selector: WES, PGT-A, NIPT qsub, NIPT docker, WGS.
- Input mode: server path scan for PGT-A, WES mock creation, sample sheet/manual preview for planned pipelines.
- Parameters: reference genome, panel/capture kit, priority, run mode, notification email, dry-run/production-run.
- Preview before submit with sample id, family id, fastq path, sex, project, pipeline, estimated workflow.

Validation:

- Missing `sample_id`, `fastq_path`, or `pipeline` blocks submit.
- Duplicate `sample_id` blocks submit.
- Invalid path-like fields show row/field feedback.
- `baseline_qc` requires at least two selected PGT-A samples.

Unsupported pipelines:

- NIPT/WGS use mock previews only; real submit is disabled until backend/API tasks exist.
