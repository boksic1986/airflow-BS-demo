# API contract

## WGS ebf1f4b Phase mapping (2026-09-18, test sync)

The exact release `wgs-4.2.1-ebf1f4b` uses the audited fine-phase inventory:
`pre_process_cleanFastq` is FASTQ QC, `pre_process_mapping` is Mapping, and
`pre_process_Dedup` is Duplicate marking. Rules, phase filters, phase summaries
and phase definitions share the existing projector. This is rule-to-phase
equivalence, not biological or QC equivalence: two changed source blobs are
recorded in policy metadata. Unknown releases/rules still return Unknown; no
version-prefix fallback is allowed.

## File-ledger history discovery (2026-09-18, test sync)

The shared runtime may retain receipts for multiple project roots. The file
reference reconciler validates request/receipt identity and the binding's own
root/batch/control-path consistency before ignoring a different project root.
It never opens that foreign project root or deletes previously imported DB
history. A generation without a published `prepare_analysis` receipt is not a
completed selection and is revisited on later passes. Existing invalid receipts,
inconsistent bindings and missing/hash-mismatched published artifacts still
report synchronization errors. No endpoint, schema or source identity changes.

## Existing Step5 log package download (2026-09-17 test branch)

`GET /api/runs/{analysis_id}/logs/index` adds `archive` for WGS/GATK adapters:
`{available, key?, filename?, size_bytes?, reason?}`. No host path is exposed.
The optional adapter resolver locates only the current attempt's bound CCE run.
`GET /api/runs/{analysis_id}/logs/archive?key=<32-hex>` uses normal platform
authentication and streams the existing package as an attachment (`application/gzip`,
private/no-store). Unknown, changed or unavailable packages return 404
`LOG_ARCHIVE_UNAVAILABLE`; unauthenticated requests return 401.

Only Step5 `cce/logs/<bound-run-id>/cce-log-*.tar.gz` packages with matching
checksum and manifest identity are served. Partial/unreadable/unsafe packages
remain unavailable. The key fences run, attempt and package version; clients
cannot specify filesystem paths. Validation is cached by file version.
This read-only endpoint does not execute Step5, create reader Jobs, collect new
logs or change run state. Native log reading is unchanged.

Native tracker rows now carry `execution_target`; their display project is
`WGS_Clinical`. Registered node-96/node-97 targets render node96/node97; SGE
remains SGE. Stored execution modes and project bindings do not change.

## Native monitoring display parity (BS10610 test, 2026-09-17)

native-view additionally returns progress (available, percent, completed_units,
total_units, observed_rules, source=native_step1_log). Rules and progress share
the exact execution-specific Step1 log, streaming complete lines and retaining
the last complete progress measurement. rule_status/phase/sample_id/family_id filters run before25-row
paging. Rule rows add stable line identity, phase, native-local timestamps and
timing provenance; missing evidence stays unknown and group declarations do not
establish child start/completion. No new workflow logger or native command.

native-view rules includes phase_summaries over all observed rules before filters
and paging. Logs selects a unique `.snakemake/log/*.snakemake.log` timestamped
within the execution's recorded start/end interval (current time for active runs).
The execution-specific metadata start must match the registered stage start.
Existing project binding/path checks remain; ambiguous, missing or unreadable
logs return log_error and no content, never an arbitrary newest file. Log tail,
search context and sanitization remain shared. No history deletion or DB change.

Dashboard native rows expose native_monitor_only/execution_mode, use snapshot
sample count and actual native start time, and use monitor-cached progress without
calling CCE/Airflow progress. Generated WGS_<batch>_T7Hg38V<version> names are
normalized for display only; registration requests, UUIDs and paths stay unchanged.

/samples includes current native snapshot identities via a SQL-paged union with
ordinary Sample rows. Native items carry data_id/execution_id/execution_mode and
configured_scope_only=true; status is the owning run status, not proof each rule
ran. Previous execution scopes remain accessible via native-view only. No Sample
inserts, schema migration or pending edits; unknown native per-sample QC is not pass.


## WGS SNV/CNV count evidence (2026-09-17 candidate)

When the selected batch QCstat omits SNV_count/CNV_count, WGS sample projection
counts data rows in the same inputs used by SingleQC_merge:
01_SNV/<data_id>.flt.tsv and03_CNV/Annot/<data_id>.CNV.tsv. Header excluded,
blank lines ignored, quoted multiline records counted once. Explicit QCstat
counts take precedence. Both counts enter qc_metrics and the existing pinned
qc_judgments policy; no threshold or aggregate-source change.

Fallback judgments name the relative source_artifact, source_sha256 and row-count
source_field. Full variant contents never enter the API. Missing/unreadable/
outside-project/changing inputs stay unknown, never zero; a header-only table
legitimately counts as zero. File-version-keyed bounded caching avoids repeated
reads on unchanged polls. No new API endpoint or DB schema is introduced.
All22 criterion columns remain visible in the UI, even unknown/inapplicable ones;
this supersedes the prior pass/fail/warn-only presentation statements below.

## GATK lifecycle list parity (2026-09-17, source only)

Existing run/dashboard list lifecycle uses the same payload as GATK detail.
Cloud release is projected from the latest generation of gatk_cleanup_step7_sfs
for the current attempt: requested/queued=pending, success=SFS released. Missing
action is not_started, not success inferred from workflow completion. No new
endpoint, schema or cleanup operation. Backup/downstream status retains the
existing detail semantics; materialization is not downstream confirmation.

## WGS server sampleinfo path (2026-09-16 candidate, not deployed)

`POST /api/wgs/runs` accepts optional `sampleinfo_path` (absolute server TSV/TXT
path, UTF-8 file at most 512 KiB). Existing `batch` is the custom analysis batch; safe letters,
digits, underscores, dots and hyphens are allowed in this mode. Catalog mode
retains YYYYMMDDX validation. Project/platform/FASTQ choices and authentication
are unchanged. No output-directory API field or new endpoint is introduced.

The private input copy changes only its analysis-batch column to `batch`; original
sequencing batches and all other field values are preserved. The original file
is untouched. The requested batch may equal the source analysis batch; a new
submission is allowed only if its destination project does not exist. Source rows
must still contain one non-empty analysis batch. Exact repeat requests reuse the same submission;
different content/options/owner at that identity are rejected. The existing
catalog creation lock is reused. Imported text lives only in the private runtime
request spool, not DB params, DAG conf, audit logs or browser draft storage.
Read access has no WGS source-directory allowlist (2026-09-17). Absolute TSV/TXT
paths may refer to any ordinary file visible/readable to the backend, including
resolved symlink targets. Node analysis paths retain existing container mapping.
Invalid path syntax, unavailable/nonregular files and oversized inputs are rejected.
No OS permission, mount or output-root constraint changes. `sampleinfo_source_path` and
`prepared_project_path` in run params support the existing second-stage review.
The unpublished text-upload request field is replaced, not another public mode.

Import validates the native 31 required columns (the trailing analysisTaskId,
taskSampleId and version remain optional); it never manufactures missing clinical
values. Private files are published atomically without overwriting a different
existing input. The normalized analysis-batch copy is the frozen checksum input.

The existing three-stage confirmation protocol remains: import sampleinfo,
review configuration/native analysis preparation, then confirm CCE execution.
There are no schema migrations. The user's final decision explicitly retains
native pending read/write/recovery and selection rules; preview candidates are
not a guarantee of the final analysis set. The third confirmation shows the final
selected set. No exact-file or no-pending mode is introduced.

## Native RunDetail view (2026-09-16 enabled on BS10610 only)

Authenticated GET `/api/runs/{analysis_id}/native-view` only supports WGS
native_monitor_only runs. It never launches, changes pending, or calls CCE.
Query: execution_id optional (default current); section samples|rules|logs|qc
(default samples); offset>=0; limit1..100 default25; history_offset>=0 (50 choices
per page); query max256 (literal case-insensitive main-log search);
match_index>=0 default0 selects the match with surrounding log context, not
filtered isolated lines. Unknown run
or foreign execution gives404 NATIVE_EXECUTION_NOT_FOUND under existing auth.

Response: current_execution_id, selected, executions/history_total/history_offset,
configuration (hash-checked allowlisted frozen parameters, mode/target/Linux user),
samples/sample_total, rules/rule_total/rules_incomplete, log, qc, evidence_health,
monitoring, configured_scope_only=true. Samples/Rules paginate, log tails200 lines
within1MiB or searches8MiB max200 matches, Rules scan8MiB and mark incomplete.
Missing evidence remains unavailable; Rule declarations alone do not prove start.

QC scope is run_latest, independent of execution_id: items, sha256, updated_at
(file time, not execution provenance), health available|stale|unavailable. Only
samples/QC requests refresh the one last-good allowlisted cache in run.params;
this internal GET-side cache update never alters WGS files or execution status.
Read exact current config.batch QC after project binding validation; invalid or
partially written source retains last reliable result. No historical QC API.
Current run/workspace native projection skips CCE lifecycle/transfer projections.
Run lists count the exact current execution snapshot's configured scope in bulk;
registration does not create candidate Sample rows or cloud phase projections.

## Native monitor attachment and final observation (2026-09-16 candidate)

POST /api/wgs/onprem/executions/{execution_id}/monitor uses original personal
owner/session/CSRF and the four claim identity fields, with monitor gate enabled.
Returns wgs.onprem-monitor-attachment.v1 and fixed native__execution_id DagRun.
Conflicts409, owner403, transport503 (retry monitor only, never launch). Existing
Airflow409 is reconciled only on exact ID+conf match. Binding persists per stage.
The internal observe response now reports done=true only after validated direct
child-wait receipt, or an already persisted terminal state. Result includes
wait_returncode, completion_scope=requested_command, relaunch_eligible and waited
times; no patient/input/credential payload. Signal/SGE-nonzero completion does not
permit automatic relaunch. No new signal/cancel/review API. See the
[terminal/attachment contract](superpowers/specs/2026-09-15-wgs-onprem-execution-contract.md).

## Native observation candidate (2026-09-15, disabled)

POST /api/internal/wgs/onprem/runs/{analysis_id}/executions/{execution_id}/observe
requires a configured internal token and WGS_ONPREM_MONITOR_ENABLED. Body contains
strict positive integer attempt/generation only. Current project/run/execution
identity mismatch409; missing/wrong token401, unconfigured token403, schema422.
HTTP200 summary includes identity, status, done, observation, checked_at,
monitoring_health/error_code and optional native_started_at/native_finished_at/
native_exitcode. Raw metadata command, hostname, filesystem paths and contents are
not exposed. This POST performs only bounded file observation and DB projection.

Observation is awaiting_claim/awaiting_start/running/native_result_reported.
Missing/invalid evidence preserves last reliable run state, reports degraded,
and never triggers or fails native analysis. Native result markers do not prove
wrapper exit, so done=false without the direct-child wait receipt added2026-09-16.
Repeated polling does not prove process liveness. Attachment is a separate call.

## R2-3 one-shot native launch claim (2026-09-15, candidate only)

POST /api/wgs/onprem/executions/{execution_id}/claim requires original personal
owner/session/CSRF, operation_id, generation, manifest_sha256 and platform_instance_id.
Separate launch gate defaults false. Checks registered/current identities and
file hashes before conditional accepted→launching. HTTP200 grants one automatic
launch attempt; replay/unknown result must never cause another grant or process.
Registration receipts remain idempotent and launch_allowed=false; they are not
launch permissions. No process, Airflow dispatch, real started time or run success
is emitted by this API. [Exact claim contract](superpowers/specs/2026-09-15-wgs-onprem-execution-contract.md).

## R2-2 native execution registration (2026-09-15, candidate only)

POST /api/wgs/onprem/projects/{project_uuid}/executions registers immutable current
inputs with an operation UUID under the original personal owner. Same operation
is idempotent; new operation creates a new execution/generation, same analysis_id
and attempt, only after prior execution is terminal. Location changes verify
binding and reject duplicate copies. It never starts a controller/Airflow task.
Receipt explicitly returns launch_allowed=false until R2-3 integration exists.
[Exact execution request/response and errors](superpowers/specs/2026-09-15-wgs-onprem-execution-contract.md).
11 execution +8 registration checks passed; no enabled endpoint or launch claim.

## R2-1 native project registration (2026-09-15, tested candidate, not deployed)

POST /api/wgs/onprem/projects now exists in candidate source only. Requires a
personal operator/admin session cookie wgs_session + X-CSRF-Token; internal-service
or disabled-auth compatibility actors are rejected. Creates UUID-keyed project
records in created state, without Sample, stage execution, prepare or Airflow work.
Default off. Same UUID/owner/initial payload yields the same HTTP200 registration
receipt; changed payload409, different owner403. New UUID at same path is distinct.
Full field/error/auth and initial-summary semantics:
[R2-1 contract](superpowers/specs/2026-09-15-wgs-onprem-registration-contract.md).
After8 RED failures, GREEN now passed8 registration,1 migration and2 related
submission checks on BS10610. Python syntax checks passed. Not an enabled API.

## Local/SGE R2 planning override (2026-09-15, not implemented)

Existing-source correction checkpoint: native runner now produces private
per-execution snapshots and returns an internal execution_snapshot reference.
13 matched tests passed; no new public registration, auth or history endpoint
is implemented, and no credentials/clinical snapshot content is added to APIs.

[R2 design](superpowers/specs/2026-09-15-wgs-local-sge-platform-integration.md)
adds optional first-time backend project registration after native analysis prepare,
without a web-created run. Registration uses project UUID, not batch/path matching.
Each start/resume registers current config/sample/argv snapshot and actors under
the same analysis_id/attempt but a new execution_id/generation; request retries
remain idempotent. CLI-origin first launch and resume are monitor-only in Airflow.
These are planned semantics, not new callable endpoints. Auth, routes and field
contracts must be confirmed in R2-1 before implementation. Existing clients and
CCE contracts remain unchanged. R1 freeze notes below describe current candidate
source, not a restriction on editing inputs in the planned native monitor path.

## WGS native preparation freeze foundation (2026-09-15, inactive)

Submission state adds nullable `prepare_execution` with `attempt`, `mode`,
`target`, `revision`. For a run carrying internal `native_prepare_contract=1`,
configuration approval freezes the current dispatch choice in the existing
locked transaction. Repeated approval returns the same snapshot; a later
execution-choice change raises `PREPARE_EXECUTION_FROZEN`, and `allow_switch`
is false. This does not reserve resources or start analysis. Historical runs
without the marker retain their contract. Creation endpoints leave the marker
unset by default; opt-in creation wiring below is source-only and unverified.
Native launch integration must be completed before activation.

Native runtime request transport is now implemented: `wgs-runtime.request.v4`
carries a copy of `prepare_execution`; attempt/mode/target/revision are validated.
Local/SGE preparation omits CCE profile/CLI metadata and Heavy slot requirements.
The backend rejects requests for CCE stages using a native frozen target.
Creation wiring is implemented in unverified source behind the default-off
WGS_NATIVE_PREPARE_ENABLED flag (requires contractv2); only new normal catalog
runs receive the marker. Automatic runs freeze CCE before submission; historical
runs are not upgraded. No deployment/activation or new public execution endpoint.
## GATK Batch Runs batch display (2026-09-16)

Public run batch projection keeps analysis_batch → sequencing_batch → batch_no
priority and adds params.batch as the final fallback for GATK/WES. Batch Runs
continues consuming the existing batch_no response field. No schema/data change.

## Resource history projection (2026-09-15, source only)

`GET /api/platform/resources?history_period=1h|24h|7d` returns the selected
SFS chart window, plus `history_period` in the response. Other values fail
parameter validation. Omitting the parameter preserves the original response.
The window retains the existing chart's UTC tick alignment and latest-sample
anchor (15-minute, 6-hour, 1-day ticks respectively). SFS history includes only
`at`, `read_bps`, `write_bps`, `total_bps`; missing values remain null. At most
600 evenly spaced original observations are returned, including first/last.
This is a sampled trend, not an exhaustive peak report; no averages are invented.
Non-SFS history is empty in this projection; all current/freshness/heavy-slot
fields remain unchanged. Collector retention and stored seven-day history are
untouched. This reduces response serialization/transfer, not DB JSON loading.

## Log search navigation (2026-09-15, source only)

GET /api/runs/{id}/logs supports query and nonnegative match_index (default0)
for registered WGS and GATK opaque log keys. Search returns a continuous window
around the indexed matching line, not a concatenation of matching-only lines.
match_count counts matching lines (not occurrences); match_index is zero-based,
and nullable match_line is the zero-based selected row within lines. No match
or an index no longer present returns initial context with match_line=null.
Normal requests without query retain the existing tail behavior.

Window is bounded by tail (frontend200) and1MiB serialized JSON (including
escaped text and reserved metadata overhead); literal
case-insensitive scanning retains the existing64MiB/64KiB-line safety limits.
search_complete=false explicitly reports incomplete scanning; counts are partial
in that case. Search does not promise coverage beyond the scan cap. Existing
registered-key authorization/path checks remain; no arbitrary path, DB schema,
search service or persistent index. Added fields are optional for old clients.

## QC/ledger follow-up (2026-09-15, source only)

GET /api/sample-references adds nullable latest_decision:
role(selected|consumed),destination_batch,operation_id,analysis_id.
One page-scoped query matches source plus exact record_key/resolved_key,
chooses the latest known decision by operation sequence/history ID, and reuses
the operations endpoint's history-start boundary. No fuzzy sample matching or
data mutation. Null means no exact recorded decision found, not no receiving
batch exists. Current pending flags and source aggregate remain authoritative.
Selection does not prove consumption, completed analysis or QC.
QC thresholds remain in API/backend policy but are entirely hidden by the UI.

## UI-SIMPLIFY-20260915 (source only)

WGS orchestration stage entries add nullable started_at/ended_at from the
existing stage row. Run success does not fabricate missing stage timestamps.
Rules UI sends status=running,limit=20,sort=active_first by default; the API
default and optional all-status/history queries are unchanged.

For audited WGS releases, qc_judgments.contamination.status uses both finite
QCstat measurements: CHARR>0.03 AND INCONSISTENT_AB_HET_RATE>0.15 =>fail,
otherwise CHARR>0.02 AND INCONSISTENT_AB_HET_RATE>0.1 =>warn, otherwise pass.
Missing/nonfinite input or unaudited release =>unknown. Value now contains the
CHARR/AB numeric pair rather than the source PASS text. Additive source_status
retains the original label; measurements retains both named numeric values.
Existing computed_status/provenance and qc_metrics/source aggregate remain.
No DB schema change, workflow threshold change or source QC aggregate rewrite.

## Incomplete WGS submission summaries (2026-09-15, source only)

`GET /api/wgs/submissions/incomplete?limit=100&offset=0` uses existing session
authentication and deployed-WGS guard, with the same read visibility as runs.
Limit is 1–200 (default100); offset is nonnegative. Returns `items,total,limit,offset`.
Each item contains `analysis_id,pipeline,status,attempt,created_at,params` only.
Params are allowlisted scalar `sequencing_batch,analysis_batch,batch_no,
submission_phase,submission_mode,config_approved_at`; no paths, clinical fields,
samples, logs or hydrated run details are returned.

SQL filters WGS statuses created/submitted/queued/running/cancel_requested and
phases preparing_sampleinfo/config_review/preparing_analysis/execution_review/
cancelling_submission, excluding auto_dispatch, before count and pagination.
Order is created_at descending then analysis_id descending. Count and page use
two database queries, with no per-item Airflow/filesystem/runtime query. This is
offset pagination, not a frozen cross-page snapshot; clients deduplicate IDs.
Opening a selected submission still fetches its existing run/sample snapshot.
No creation, cancellation, prepare, attempt, pending or schema behavior changes.
Deploy backend endpoint before or together with its frontend consumer; API
failure is visible and retains the last card snapshot, not an N+1 fallback.

## WGS Step4/6 linear display estimates (source only)

Existing StageEstimate fields remain display-only and never replace measured
runtime progress or status. WGS uses `estimate_model=stage_median_linear_v1`:
elapsed/baseline *100, capped99 until current-stage success100. Baseline selection
and generation-scoped storage are unchanged. Missing baseline/start stays null.
Optional `estimate_elapsed_seconds` and `estimate_remaining_seconds` are shared
by progress/workspace and dashboard stage_progress; remaining clamps to zero at
overrun. Failed/canceled execution freezes the estimate. GATK retains its existing
model. No migration, new endpoint, runtime request or producer change.

## WGS evidence projection repair (2026-09-15, not deployed)

Legacy Step1/5 same-attempt recovery may use matching registered request SHA and
worker launch identity/time when retry_no is zero. Only a verified launch after
the failed stage can reopen its projection; stale and cross-attempt evidence
cannot, and success remains monotonic. Reopened transfer/stage start reflects
that launch, old end fields clear. Progress alone is not restart authority.
No new endpoint, schema, execution authorization or source receipt mutation.
Fine phases additionally support wgs-4.2.1-34bfcbf through verified identical
source blobs; unregistered releases and rules still return Unknown.


## LEDGER-01 current pending presentation (not deployed)

GET /api/sample-references with pending=true now requires
present_in_latest_complete=true before counting/pagination. Omitting pending
retains the historical/all-record API; no reference/sample deletion occurs.
For wgs_files current membership, origin_batch is explicit source_analysis_batch
or the row's analysis_batch, never sequencing_batch. This is applied by normal
worker sync, not a DB migration/backfill. Historical operation payload/identity
and request/receipt validation remain unchanged; UI does not present legacy
operation origin_batch as source analysis provenance.

## CCE 0.8.5 managed WGS release API (2026-09-15, inactive)

`POST /api/wgs/releases` accepts only `cce-release.v1`: a complete managed
`release`, its verified `assets` record (`status=PASS`, `state_verified=true`),
and `receipt_sha256`, the SHA-256 of canonical JSON without that digest field.
Profile/source/build/resource fields must match across both components. The WGS
`release.release_id` and CCE asset-transaction `assets.release_id` are independent
namespaces and are both retained in the receipt.
Registration is an authenticated deployment attestation: it adds an inactive
candidate, is idempotent for an identical receipt, conflicts for changed content,
and performs no Kubernetes, node200, package-installation, or cloud operation.

`GET /api/wgs/releases` returns `current_release_id`, `current`, and inactive
`candidates`, including the registered receipt digest. `POST
/api/wgs/releases/{release_id}/activate` accepts only `receipt_sha256` and
`expected_current_release_id`; both the registered receipt and compare-and-swap
current value must match. Activation changes only catalog current selection.
It never rewrites runs, attempts, queued requests, configuration capabilities,
or runtime gates. Existing singular `GET /api/wgs/release` remains unchanged.

Both writes require an admin identity, `AUTH_REQUIRED=true`, and
`WGS_RELEASE_MANAGEMENT_ENABLED=true`. Browser sessions retain the existing CSRF
requirement; the existing `X-Airflow-Demo-Token` internal identity is accepted by
the unchanged authentication middleware. CCE recovery validates and retains its
recorded catalog release and frozen params; a missing/unknown recorded release
fails closed. Existing local/SGE refresh behavior is unchanged.

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
over every rule in the selected attempt, independent of status, rule, phase,
sample_id, family_id, sort and pagination. Only items and total apply those row
filters; an empty filtered page still carries the full attempt summary.
Status filtering and summaries use the
same current-attempt success reconciliation as serialized rows. Historical
attempts never inherit current run success. Rows add status_inferred, origin
(role plus opaque stream hash), execution_group and timing_provenance.
Unknown rule names remain Unknown. Stream identities are not merged without
cross-stream execution correlation. Missing individual starts remain null.

WGS sample/QC projection preserves qc_status and qc_metrics and adds
qc_judgments: numeric/status value, unit, threshold bounds and inclusivity,
status, reason, release/source Git blob identity, policy SHA256 and controlled
artifact provenance. Audited wgs-4.2.1-cc9bde3 and exact source-equivalent
wgs-4.2.1-34bfcbf have numeric policy support. The latter records its actual
source_commit and additive policy_source_commit (the original audited commit).
All four QC source blobs were verified identical; qc_config alone is insufficient.
The exact wgs-4.2.1-ebf1f4b variant is separately audited: g1 adds coverage
>=20X >90% for other project items; all other audited QC source content is
unchanged. Its provenance records the actual g1 blob and source commit, not
source equivalence. Historical cc9bde3/34bfcbf keep their conditional rule.
Other releases remain unknown, with no latest-version fallback. Conditional
item/type/relation/BKW inputs are private. Missing metrics/conditions are unknown,
not passed; source aggregate is never recomputed from this partial display.
The API retains unavailable/unknown diagnostics; WGS UI only presents available
source-derived pass/fail/warn judgments, without altering this contract.
Audit: releases/2026-09-15-wgs-qc-policy.md.
Current variant: releases/2026-09-17-qc-policy-ebf1f4b.md.

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
  in sample metadata nor returned by global APIs. The explicitly approved
  run-detail exception is documented below. An absent db_v2 reason remains
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
- `GET /api/runs/{analysis_id}/samples` adds `manifest_summary`. That summary contains only aggregate batch/sample/family/order counts, allowlisted project/method/date/type summaries, delivery status, and a controlled relative project path. The run-detail exception below permits selected sample identity fields, never in the summary.
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

Except for the explicitly approved WGS run-detail sample fields below, responses exclude patient names and hospitals. Credentials, raw absolute storage paths and arbitrary filesystem content remain excluded. Artifacts are accessed by controlled keys.
# WGS recovery approval semantics (2026-09-11)

## Same-attempt stage recovery (2026-09-15, source only)

Operator POST `/api/runs/{analysis_id}/actions/resume-stage` accepts
`{attempt, stage, idempotency_key}`. Stage is exactly step1_upload, step2_master,
step3_monitor, step4_publish, step5_download or step6_materialize. WGS CCE and
contract-v2 execution gates, frozen request identity and current attempt must
match. Preparation/maintenance and client-supplied paths/commands are rejected.
Response is `{analysis_id, attempt, stage, generation, action_id, status}`.

RunAction retains original and deterministic recovery DagRun identities.
Analysis, attempt, release and workdir are preserved. Repeated keys and identical
active operations dedupe; different active stages conflict. An uncertain dispatch
stays visibly recoverable and reconciles the same DagRun before any new POST.
Auth/parameter rejection is explicit, retained and never treated as transient.
Internal stage registration adds resume_action_id; dag-terminal adds dag_run_id
and resume_action_id. Original callbacks cannot close current recovery, while
identity-matching recovery failures propagate. Generic resume/rerun_failed retain
their existing new-attempt semantics below.

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
# GATK workload retirement (2026-09-16)

No endpoint change. The existing Step7 capability accepts terminal workloads
or a collector-confirmed Deleted/PodNotFound projection. Unknown, live or
unconfirmed deletion records remain blocked as cce_workload_active. Read-time
eligibility does not replace node-side fresh workload/UID/target validation.
The existing GATK Step6 status poll ingests final workload evidence; no browser
Kubernetes access, cleanup-on-read or automatic destructive action is added.
# Worker child timing projection (2026-09-17)

Rule responses retain recorded individual start/elapsed when the matching instance
has explicit worker job_info with group_member=false, even if that event omits
status. Unnamed job_started is already joined by stream/job in RuleState. Neither
group inventory nor an individual declaration without recorded start creates time.
# Native log progress and phase display (2026-09-17)

Native rule/progress parsing streams complete lines beyond 8 MiB; progress remains
available from the latest complete measurement despite an unfinished final line.
The native-only phase label falls back to the shared exact-name WGS catalog if
registration has no cloud pipeline_release_id. This classifies displayed modules;
it does not attest the native source version or change execution/selection logic.

## Run-detail presentation fields (2026-09-18, test sync)

Authenticated `GET /api/runs/{analysis_id}/samples` may return WGS manifest
`name`, `hospital`, `order_number` and `test_project`, alongside existing
sample type/dates/family fields. These values are allowlisted from the bound
frozen sampleinfo and only returned for participating Sample IDs. They are not
newly persisted. The opt-in exists only at this run-detail endpoint; global
sample search, workspace and QC responses keep privacy-safe projections.
Missing values remain null and arbitrary clinical columns are not exposed.

`GET /api/runs/{analysis_id}/rules` adds `filter_options.sample_ids` and
`filter_options.family_ids`: sorted distinct identities for the selected
attempt, plus participating samples for the current attempt. They do not
depend on row filters, limit or offset. Historical attempts do not inherit
current Sample rows. Existing `phases` supplies the full pinned phase catalog.
