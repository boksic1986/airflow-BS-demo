# API contract

## GATK selective production promotion (2026-09-12)

Manual GATK preview/confirmation retains the existing authenticated API. The
server-side `GATK_SOURCE_POLICY` defaults to `restricted`; explicitly configured
`unrestricted` accepts valid source projects and their resolved regular FASTQ
files without business-root whitelists. Preview freezes source identity and
input fingerprint; confirmation rechecks the owner-bound, expiring draft and
unchanged files. This setting does not enable execution by itself.

The internal authenticated POST
`/api/internal/gatk/runs/{analysis_id}/dag-terminal` accepts the current
attempt and terminal DAG evidence. Identity conflicts return 409 and cannot
mark a later attempt failed. GATK progress projection reads persisted stage
state rather than inheriting WGS stage labels. See the request model in
`backend/app/main.py` and adapter in `gatk_runtime_service.py` for fields.

WGS4.2.1 uses the existing GET /api/wgs/release catalog response; new requests
read the current configured release, not a frontend literal or live Git HEAD.
Existing run details retain frozen version identity. Internal prepare stage-status
for4.2.0 and4.2.1 waits for the validated handoff receipt before becoming ready.
This does not add endpoints, schema fields or automatically upgrade old attempts.


2026-09-11 WGS `/api/runs/{analysis_id}/logs`: optional `query` (max256 characters) performs case-insensitive literal content search from file start through at most64MiB, returning at most `tail` matched excerpts. Response adds `query`, `match_count`, `search_complete`; `truncated` also covers response/scan limits. Oversized lines mark results incomplete. Empty query retains bounded tail behavior. Existing opaque key validation remains mandatory; no client filesystem paths. WGS log index additionally registers existing `.log/.out/.err` files explicitly declared by current-attempt Master `log:` lines, under the bound batch only, without symlinks/traversal. Index parses at most8MiB/2000 files; unavailable/unreferenced child logs are not fabricated. Other adapters retain existing tail-only search UI.


Dashboard attention excludes cancelled/canceled runs before sample, QC, duplicate-family, reanalysis and overdue projection. Intake alerts linked to cancelled runs are excluded; unlinked intake warnings remain. This is read-only projection, not audit deletion; cancel_requested is not treated as confirmed cancellation.

Dashboard runs: omitted status or `all` now excludes cancelled/canceled before total/count/pagination. Explicit `status=cancelled` or `canceled` retrieves both spellings; other run APIs and database records unchanged.

## Config-review submission cancellation

- Operator-authenticated GET `/api/runs/{analysis_id}/submission-cancel-preview?attempt=N`: checks current attempt/manual phase and Airflow preparation boundary; returns analysis_id,attempt,submission_phase,effects.409 when unsafe,503 when Airflow unavailable; no changes.
- Operator-authenticated POST `/api/runs/{analysis_id}/actions/cancel-submission` with `{ "attempt": N }`: supports config_review only, plus same cancellation retry. Serializes with approval; commits cancellation fence before stopping original DAG through Airflow PATCH failed. Returns status cancelled only when verified.409 unsafe/stale identity,503 unconfirmed transport failure; retry same attempt, never new submission.
- Audit and files retained. Current candidate statuses cancelled; pending and prior-attempt participation preserved. Cancellation requested after preparation/config approval is rejected. Generic `/actions/cancel` remains separate.

2026-09-11 handoff repair: restricted gate's safe prepare receipt projection preserves already-validated analysis_id, attempt, execution_id, generation, request_hash and release_id with schema/decisions. It does not expose private artifact descriptors. Original request/receipt identity, schema and artifact SHA checks remain mandatory. Existing global `/api/samples` supports configuration candidate preview filtered by exact returned analysis_id and selection_attempt; `/api/runs/{id}/samples` remains selected-only. No new endpoint/table or direct production DB operation.

2026-09-12 attention IDs include attempt; duplicate-family IDs also include family identity to avoid collisions across identical batch sets. Family alert detail includes family and batch codes for authenticated operator use. No new API/mutation endpoint; acknowledgement is browser-local only. SFS total_bps remains optional, with explicitly labelled frontend fallback when both read/write values are available.

2026-09-11 additive sample scope: run payloads expose `sample_scope_status` (`preparing`, `ready`, `legacy`); existing `sample_count` is current-attempt selected count. Sample projections add `selection_decision`, `selection_attempt`, `pending_reason`. Global `/api/samples?status=pending` retains nonparticipating rows/reasons; run Samples and QC denominator use selected only. Synchronization endpoints remain compatible for operations, but UI no longer invokes manual Sync. See [release evidence](selection-refresh-20260911.md).

Heavy telemetry (2026-09-11): `/api/platform/resources.heavy_slot` now reads
`heavy-slot-global.json` schema `wgs-heavy-global.v1`. Complete namespace Lease
inventory supplies used/limit; fresh snapshots for every nonterminal,
nonsuspended Master supply waiting_jobs and attest mode/limit. Count reserved
holders even if old; only executor may reclaim them. Freshness max180s, future
clock tolerance10s. Incomplete/invalid/stale data returns available=false and
nullable metrics, never synthetic0/25. Available responses add updated_at.
With no active Masters and no holders mode is idle. No database migration.

## T255 unavailable global Heavy I/O telemetry

Until an authoritative namespace-global producer is available, WGS global slot projection returns `available:false` with `used`, `limit`, `waiting`, and `mode` null (pool remains wgs-heavy-io). Configured limits, empty evidence directories, database rule labels and individual Master snapshots do not establish global occupancy. Consumers must display unavailable rather than0/25; runtime Lease enforcement is independent of this display contract.

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
# WGS recovery approval semantics (2026-09-11)

For `three_stage` runs, `actions/resume` and `actions/rerun_failed` create a
new attempt with `submission_phase=preparing_sampleinfo` and clear
`config_approved_at`/`execution_approved_at`. Current-attempt preparation and
normal config/execution approval endpoints must complete before execution
commit. Analysis parameters remain unchanged; prior approvals do not bypass
new-attempt gates. Legacy-mode behavior is unchanged.
