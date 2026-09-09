# API contract

## T242 WGS 4.2

The release API adds profile identity and cce-pipeline version. Prepare stages
resolve the run-bound catalog release and may import a validated privacy-safe
prepare handoff receipt. Unknown releases and commit mismatches return 409.

## T240 dashboard attention and sample information

- `GET /api/dashboard/overview` adds `attention_items`, an adapter-owned,
  privacy-safe list of actionable conditions. The WGS projector may emit
  workflow/QC failures, add-on exclusions, FASTQ pair issues, reanalysis,
  cross-batch duplicate-family warnings, SFS cleanup overdue after two days,
  and overdue result delivery. A projector runs only when its pipeline is in
  the selected dashboard scope. Legacy overview fields remain available for
  rolling-version compatibility but the T240 dashboard no longer renders the
  duplicate summary cards and trend panels.
- `GET /api/intake/status?pipeline=wgs&view=attention` returns only unlinked
  `ready`, `needs_review`, and linked failed analysis rows. `no_new_wgs`,
  queued/running and successful linked analyses are excluded. The response
  contains controlled batch identity and status only; source paths are not
  returned.
- WGS sample projections may add `order_number_masked`, `test_project`, and an
  optional future `status_reason`. The order value is always `****` plus at
  most the last four source characters; the raw order number is neither stored
  in sample metadata nor returned by the API. An absent db_v2 reason remains
  absent rather than being fabricated.

## Generic platform endpoints

- `GET /api/platform/capabilities` returns `deployed_pipelines` and registry definitions with capabilities and execution targets.
- `GET /api/runs` lists runs, filtered by registered pipeline ID. Each item may include an optional `lifecycle` object projected by that pipeline's registered `project_dashboard_lifecycles` callback; adapters without this projection return `null` rather than inheriting WGS behavior.
- `POST /api/runs` creates through the selected adapter when `submit` is available.
- `GET /api/runs/{analysis_id}` returns the shared run projection plus adapter-owned fields.
- `GET /api/runs/{analysis_id}/samples` returns adapter-projected sample state.
- `GET /api/runs/{analysis_id}/qc` returns safe adapter-projected QC data.
- `GET /api/input/scan`, `/api/input/roots`, and `/api/intake/*` require the corresponding registry capability.
- Aggregate `GET /api/intake/status?pipeline=deployed|all` and `GET /api/intake/scanner-state` enumerate only deployed adapters that declare `intake`; a deployed manual-only adapter does not break another pipeline's scanner projection.
- An explicit `GET /api/intake/status?pipeline=<id>` for an adapter without `intake` still returns `409 PIPELINE_CAPABILITY_UNAVAILABLE`.
- `GET /api/workflows` returns deployed registry entries rather than a hard-coded catalog.
- `GET /api/pipeline-config/template` and `POST /api/pipeline-config/validate` dispatch to the selected adapter.
- `POST /api/runs/{analysis_id}/actions/reanalyze` dispatches only after the adapter capability and its execution/runtime gates pass; a rejected call cannot increment the attempt.

## Stable pipeline errors

```json
{"detail":{"code":"PIPELINE_NOT_REGISTERED","message":"..."}}
```

The other stable codes are `PIPELINE_NOT_AVAILABLE` and `PIPELINE_CAPABILITY_UNAVAILABLE`; clients branch on `code`, not message text.

## WGS extensions

Existing `/api/wgs/*` routes remain supported for WGS submission, intake, evidence, transfers, execution choice, maintenance, and lifecycle functions. They are deliberately namespaced and do not define generic behavior for future adapters.

### T227 transfer and Step7 recovery projections

- `GET /api/runs/{analysis_id}/workspace` returns one `snapshot_at` and the complete `active_transfer`; Current Progress and Transfers must render that same object during Step1 or Step5.
- Transfer percentages are derived from `bytes_transferred / bytes_total`, serialized to one decimal place, and fixed at `100.0` for successful terminal transfers. Per-file rows expose privacy-safe display name, bytes, speed, checksum state, `started_at`, and `ended_at`.
- `GET /api/runs/{analysis_id}/samples` adds `manifest_summary`. It contains only aggregate batch/sample/family/order counts, allowlisted project/method/date/type summaries, delivery status, and a controlled relative project path. It never returns order identifiers or clinical identity fields.
- `GET /api/runs` returns `workflow_status` and `workflow_label` as a stable fallback when detailed stage rail evidence is unavailable.
- `GET /api/runs/{analysis_id}/rules?sort=active_first` orders running/started records before planned and terminal records while retaining server pagination and explicit start/end/elapsed fields.
- `POST /api/runs/{analysis_id}/actions/cleanup-step7` accepts the existing first-run body. A failed-action retry additionally requires `retry_failed=true` and the current `expected_action_id`; stale or non-failed generations return conflict.

### T229 live consistency projections

- `GET /api/dashboard/runs` treats `publishing` and `downloading` as active states for filtering, elapsed/ETA calculations and active-first pagination.
- WGS orchestration stage summaries preserve raw stage rows but project every predecessor as successful once an authoritative later stage has started. This prevents stale Step2 callbacks from contradicting an active Step3-Step6 run.
- `GET /api/transfers/{transfer_id}/files` orders file rows by operational priority: running, accepted/queued, failed, then successful. Pagination and the privacy-safe response fields are unchanged.
- For a verified successful WGS run, Samples and Rules project stale non-terminal rows as successful and use the run finish timestamp. The underlying Rule/Sample evidence is not rewritten.

### T239 lifecycle, QC and grouped-rule evidence

- `GET /api/runs/{analysis_id}/workspace` adds `summary.batch_qc_status`. WGS uses the same controlled `QCstat` projection as the Samples/QC APIs, with the stored sample state only as a fallback: any fail wins, then warning, all pass/success becomes pass, and incomplete or absent evidence remains unknown.
- `GET /api/runs` obtains WGS `qc_status` through the same registry-owned batch QC projector, so Run lifecycle filtering and Run Detail cannot disagree merely because historical `sample.qc_status` rows were not rewritten.
- WGS workflow lifecycle `updated_by` uses the same privacy-safe operator display name as the run projection. Scanner-created runs therefore display `wgs-scanner` instead of an empty operator.
- Step7 eligibility treats a successful master workload as authoritative only for active child workload observations at or before that master success. A newer Pending/Running/Active observation still blocks cleanup, as do the existing transfer lease and Step5/Step6 gates.
- Grouped Snakemake `job_started` events are expanded into one member event per Rule/job identity so future runs can persist starts for rules such as `pre_process_mapping` and `pre_process_Dedup`. Historical starts that were never emitted remain unrecorded and are not fabricated.

### T241 obsutil checkpoint transfer projection

- New WGS Step1 and Step5 transfers use `obsutil`. The restricted runtime
  reconciles one privacy-safe file-keyed child snapshot per payload file with
  the immutable transfer plan and continues to publish
  `wgs-runtime.transfer-progress.v2`.
- `active_transfer.transfer_engine` is `obsutil` when the backend imported the
  controlled checkpoint source marker. The response never exposes the
  checkpoint directory, OBS URI, object prefix, credential or absolute data
  path.
- File rows remain ordered `running`, `accepted`, `failed`, `success` and keep
  their existing exact byte, checksum and timestamp fields. Before obsutil
  creates multipart XML, a planned file is represented as `accepted` with
  zero observed bytes; this is not a sampled zero-percent measurement.
- Historical SDK v2 snapshots and aggregate-only obsutil v1 snapshots remain
  readable. Once file-keyed obsutil rows exist for a frozen plan, they are
  authoritative over a stale SDK snapshot from the same attempt.

## GATK Cloud manual submission

- `GET /api/pipelines/gatk/release` returns the approved profile ID, profile
  revision, fixed `cce` execution target and the current execution-gate state.
  It contains no node path, command, credential or image reference.
- `POST /api/pipelines/gatk/submission-preview` accepts only
  `source_project_dir`. It returns an expiring draft/hash, batch, fixed profile,
  sampleinfo basename, locked SCMC sample IDs, FASTQ count/bytes and safe check
  results.
- `POST /api/runs` confirms GATK with `pipeline=gatk`,
  `execution_mode=cce`, `submission_draft_id` and
  `submission_preview_hash`. Changed inputs return
  `409 GATK_INPUT_CHANGED`; an expired/consumed draft or duplicate batch
  returns `409 GATK_DRAFT_CONFLICT`.
- GATK reuses `/workspace`, `/rules`, `/pods`, `/transfers`, `/logs` and
  `/artifacts`. It deliberately does not expose QC, intake or clone-reanalysis
  capability in v1.

Internal `/api/internal/gatk/runs/{analysis_id}/stages/{stage}` and
`/stage-status` routes require the service token and the fixed
`gatk-runtime-200` adapter identity.

## Privacy

Responses never include patient names, hospitals, credentials, raw absolute storage paths, or arbitrary filesystem content. Artifacts are accessed by controlled keys.
