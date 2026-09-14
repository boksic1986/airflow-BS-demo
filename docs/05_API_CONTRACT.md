# API contract

## LEDGER-01 current pending presentation (not deployed)

GET /api/sample-references with pending=true now requires
present_in_latest_complete=true before counting/pagination. Omitting pending
retains the historical/all-record API; no reference/sample deletion occurs.
For wgs_files current membership, origin_batch is explicit source_analysis_batch
or the row's analysis_batch, never sequencing_batch. This is applied by normal
worker sync, not a DB migration/backfill. Historical operation payload/identity
and request/receipt validation remain unchanged; UI does not present legacy
operation origin_batch as source analysis provenance.


## Shared WGS transfer progress (2026-09-15, not deployed)

Tracker stage_progress and Run detail workspace progress reuse the existing
transfer serializer and one stage-field mapping for Step1 upload/Step5 download.
Active transfer selection filters analysis, current attempt and stage direction.
Percent retains the serializer's one decimal; bytes, speed, ETA, current item and
heartbeat come from that same snapshot. No detailed/current transfer means
unavailable numeric progress, not fallback to stale integer stage progress.
No endpoint/schema/DB migration or workflow state mutation is introduced.


## GATK recovery and explicit Step7 (2026-09-14)

The existing sync-airflow operation dispatches through the GATK adapter.
Background synchronization is opt-in through each adapter's declared observed
states. GATK checks the exact current DagRun identity and latest generation of
each runtime stage before restoring a failed orchestration projection. A live
DagRun cannot override a failed runtime receipt. Actual recovery resets failed
run timestamps and selected Sample status and records one reconciliation audit;
successful DAG plus successful materialization are needed for terminal success.
No new sample table or frontend-only status override is introduced.

The admin-only existing `POST /api/runs/{analysis_id}/actions/cleanup-step7`
dispatches via the registered adapter callback. GATK requires typed batch
confirmation, successful current attempt, latest Step5/6 receipts, no active
transfer leases/workloads and frozen binding identity. Failed-action retry needs
`retry_failed=true` and `expected_action_id`; a new generation preserves history.
Run detail supplies `step7_cleanup` eligibility/history and independent
`lifecycle.cloud_release`. Local materialization is not proof of downstream
delivery or raw FASTQ backup. Cleanup never changes scientific Sample/run state.

Service-token-only GATK maintenance routes are POST/GET
`/api/internal/gatk/runs/{analysis_id}/maintenance/{action_id}` and POST of its
`/failed` suffix. They fence current attempt, action and request identity; the
fixed `gatk-runtime-200` adapter applies. No client command or storage path is
accepted. Network failures must not authorize deletion or release a live lock.

## Original-file ledger promotion (2026-09-14)

Authenticated read-only GET `/api/sample-references`, `/api/sample-references/sources`
and `/api/sample-references/operations` expose paginated safe ledger/source/history
projections. See `app/sample_reference_api.py` for exact query filters and
`docs/WGS_FILE_REFERENCE_MINIMAL.md` for current pending versus selected history.
No mutable pending endpoint, DB-to-file writes or analysis submission is added.
Successful original prepare emits a best-effort nonblocking sync hint; the
independent worker provides recovery. Operator history-start settings optionally
bound visible history by retained analysis/attempt, never current pending.
This promotion preserves existing prepare/sample APIs; experimental preparation
preview and immutable-attempt selection replacement are not activated here.

GATK acquire-slot polling now persists queued Step1/Step5 presentation, with
stage_label `等待上传`/`等待下载`, progress_available=false, and current_item
distinguishing waiting capacity from acquired-but-not-started. Run status stays
running; real stage registration resets the standard stage label. This is based
on actual acquire calls, not guessed from elapsed time or missing telemetry.

## GATK terminal transfer convergence (2026-09-14)

Existing internal GATK stage-status polling now idempotently reconciles the
current Step1/Step5 terminal receipt into its TransferJob and releases only the
matching directional lease. Response schema is unchanged. Receipt identity must
match the latest generation/current attempt; missing or ambiguous evidence is
not a release authorization. Transfer status/progress completion may be backed
by the stage receipt while measured byte/file counts remain unchanged, with an
explicit reconciliation message. This is not a checksum verification claim.

## AF-05 candidate: preregistered WGS batches

Authenticated existing `GET /api/intake/status?pipeline=wgs` additionally returns
`intake_id`, `discovery_mode`, `project_id`, `platform_id`, `reason_code` and
`source_version`. New Samplelist rows have `discovery_mode=samplelist_batches`,
full content `sequencing_batch`, nullable `chip_id/analysis_id`, and stable
`batch_id=intake:<id>` before and after binding. Legacy rows retain chip batch IDs.
`source_version` is a 64-hex content digest, never a filename or source path.

The normal/pending view includes `waiting_sequencing` (no directory yet) and
`waiting_data` (bound directory awaiting BarcodeStat). Pair counts are null while
waiting, not zero. Existing ready/needs_review/no_new_wgs semantics remain.
The Intake attention view, used by the Dashboard queue, also includes unlinked
waiting rows; this does not turn waiting into a global Attention alert.
`last_seen_at` remains the latest directory observation time.
No sample IDs, TSV content, source paths or raw parser errors enter this response.
Safe reasons include `sequencing_directory_pending`, `barcode_pending`,
`ambiguous_sequencing_directory`, `bound_directory_unavailable`,
`directory_owned_by_other_intake`, `source_context_conflict`,
`unsafe_barcode_marker`, `bound_data_changed`, `input_readiness_conflict` and
`ambiguous_analysis_owner` and `incompatible_analysis_owner`. Discovery does not
create Sample or AnalysisRun rows. An existing automatic run with a different
frozen root or another Intake owner remains unsubmitted and requires review;
already linked failed/canceled runs retain their identity.

### OPT20260912 catalog option activation

`GET /api/wgs/release` separates informational `submission_options` from
`config_options_enabled` and `config_options_reason`. When inactive, explicit
`algo` or `use_reference` in `POST /api/wgs/runs` fails with a clear validation
error before any run creation/submission. Omitting both preserves the legacy
catalog path. Existing stored run recovery/configuration/execution approvals
retain their original contracts. Visible audited enums are not evidence that
the retained node gate implements them.

## OPT20260912 resources

`GET /api/platform/resources` adds `resource_packages` with status, safe reason,
source, updated_at, checked_at, interval_seconds=3600 and items. Each item has
an opaque key, category (cpu_hours/memory_hours/obs_storage/obs_requests/other),
Decimal-string total/remaining, dictionary unit, period_start/period_end,
expires_at, cycle and cycle_type. Never sum units or reset cycles. Refresh
failure retains last-good rows and original timestamp with stale/reason;
source older than90 minutes is stale. Missing spool is unavailable; only the
collector can establish not_configured/dedicated_billing_credentials_missing.
No order/resource/account identifiers, raw errors, credentials or network call
are returned or executed by this GET. API projects allowlisted fields only.

`heavy_slot` retains nullable used/limit/waiting/mode/available and adds
unit=heavy_work_job, updated_at and per-field status/reason/updated_at.
`available` is true only when all fields are fresh. A complete Lease inventory
can provide fresh used/limit while waiting is unavailable. Stale last-known
values are retained with stale metadata, not promoted to current readings.
Configured frontend/backend limits and business Pod rows are never used as
namespace occupancy. One grouped work Job uses one lease; not per-rule quota.

## OPT20260912 Rule/QC/display estimates

`GET /api/runs/{id}/rules` defaults to the current attempt; optional positive
`attempt=N` selects history. Exact sample_id and family_id filters are ANDed.
Response adds attempt, current_attempt, attempts and phase_summaries computed
over the complete filtered query before pagination. Status filtering uses the
same current-attempt success reconciliation as serialized rows. Historical
attempts never inherit current run success. Rows add status_inferred, origin
(role plus opaque stream hash), execution_group and timing_provenance.
Unknown rule names remain Unknown. Stream identities are not merged without
cross-stream execution correlation. Missing individual starts remain null.

WGS sample/QC projection preserves qc_status and qc_metrics and adds
qc_judgments: numeric/status value, unit, threshold bounds and inclusivity,
status, reason, release/source Git blob identity, policy SHA256 and controlled
artifact provenance. Only audited wgs-4.2.1-cc9bde3 has numeric policy support;
other releases remain unknown, even if their qc_config is identical. Conditional
item/type/relation/BKW inputs are private. Missing metrics/conditions are unknown,
not passed; source aggregate is never recomputed from this partial display.

WGS and GATK Step4/6 add display-only estimated_progress_percent,
estimate_baseline_seconds, estimate_history_count/model/execution_id/generation
and estimate_overrun to workspace/progress stage and orchestration rail, and
dashboard stage_progress. Exact observed progress wins in UI. A baseline is
persisted on the first actual running observation, from the latest20 successful
same pipeline/release/execution target stages ending before that start; at least
3 complete positive durations are required. Accepted/queued stages do not grow.
Estimate is eased, capped99 until observed success100; failure/cancellation
freezes at terminal time and a new execution generation resets it. GET is read-only.
Existing already-running rows without a persisted baseline stay indeterminate.

OPT20260912 review fix: WGS submission_options now supplies audited defaults
and effective_config hashes. Test preview returns source_project_dir and the
safe effective_config manifest; these are frozen in the saved descriptor and
review. Source config is not a source of executable defaults. Unknown contracts
do not receive frontend fallback enums/defaults. Old test drafts without this
manifest require a new preview, not a silent upgrade.

## OPT20260912 submission

- WGS release adds release-audited `submission_options` (caller enum, reference
  enum, fixed genome/CNV description/provenance) and `test_project_enabled`.
  Unknown releases expose no invented options. POST `/api/wgs/runs` accepts
  optional `algo` and `use_reference`; explicit choices are frozen at stage 1,
  checked in configuration approval and propagated to the owner CLI. Old
  requests without options retain legacy defaults.
- GATK release adds `caller` and `runtime_identity.configured/observed/reason`.
  No release-wide runtime probe exists: observed version/profile/Master/check
  time remain null, never copied from configured profile values.
- Authenticated operator POST `/api/wgs/test-projects/preview` accepts
  `source_project_dir`, `output_child`, `algo`, `use_reference`. Source is an
  existing WGS `sampleinfo.tsv`, `config.yaml`, `raw/<data_id>.R{1,2}.fq.gz`
  project inside the approved WGS_test root. It returns draft/hash, exact safe
  sample IDs, input counts and frozen choices, not FASTQ paths or raw rows.
- POST `/api/wgs/test-projects/{draft_id}/confirm` accepts `preview_hash`.
  Owner, expiry, current release and exact source fingerprint are rechecked;
  one locked draft creates one independent AnalysisRun and deterministic
  DagRun. PostgreSQL advisory locking serializes competing output identities.
  The gate creates the output only on the restricted test node. Configuration
  and execution still require the existing second and third confirmations.
- Production rejects this mode in service and node gate, even if the feature
  flag is erroneously true. Errors are `WGS_TEST_PROJECT_INVALID` (400),
  `WGS_TEST_PROJECT_CONFLICT` (409), or existing execution/registry errors.
  Target existence/traversal/symlinks are rejected; no output fallback exists.

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

Historical Heavy telemetry (2026-09-11; superseded by OPT20260912 above): `/api/platform/resources.heavy_slot` reads
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
- `GET /api/intake/status?pipeline=wgs&view=attention` returns unlinked
  `ready`/`waiting_sequencing`/`waiting_data`, `needs_review`, and linked failed analysis rows. `no_new_wgs`,
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
- Grouped starts now emit descriptive `rule_planned` members with group-only provenance, not individual running events. Legacy group_member starts are ignored for individual timing. Producer/image activation is independent of backend deployment.

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

## OPT20260912 monitoring review corrections

Fine biological phases use exact release catalogs: WGS `wgs-4.2.1-cc9bde3`
and GATK `gatk-scmc-v7.6.0@bd04f6d`. Unknown/missing releases and unlisted
rules return `Unknown`; module prefixes alone are not evidence. Rules, filters,
complete phase summaries, registry progress, observer and sample projections
share this policy. Legacy coarse helper defaults are not used by run APIs.
Phase precedence: failure, active running, unresolved planned, terminal canceled,
success (including success+skipped), all-skipped. Cancellation aliases include
cancelled/terminated. An incomplete canceled+planned phase remains planned.

Rule items add `execution_group_members: [{rule, snakemake_jobid}]` from the
same event's source inventory, including members outside the current page.
Missing historical inventory is `[]`, not guessed across unrelated streams.
Stage estimates add `estimate_frozen` for terminal display; baseline and percent
remain unchanged. No measured-progress or execution authority is added.
# 2026-09-14 transfer projection clarification

GATK Step1/Step5 status-only running updates retain measured stage progress for
the same execution. Generation reopen clears prior measurements. WGS Heavy
quota excludes explicit nonparticipating GATK Masters; idle WGS counts do not
describe GATK compute utilization. Unknown telemetry is not converted to zero.
