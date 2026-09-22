# Airflow DAG specification

## WGS independent Step7 maintenance (2026-09-22 candidate)

New requests use bio_wgs_maintenance (max_active_runs=1), with only
step7_cleanup and wait_step7_cleanup. No analysis or transfer pool is used.
Existing maintenance run IDs retain their old DAG route. Task retries are zero;
read-only reconnection delays are30/60/120 seconds. An ambiguous launch response
is reconciled before at most one identical resend, allowed only if not_started.
Running/success attaches, unknown stops, failed deletion needs manual retry.
Failure callbacks affect only the maintenance action. Test acceptance pending.

## R2-3 isolated native monitoring candidate (2026-09-15)

New bio_wgs_native_monitor deliberately leaves the existing bio_wgs CCE graph
unchanged. One PythonSensor observe_native_execution uses reschedule every30s,
timeout24h and3 transport-task retries with30s exponential backoff. Paused on
creation, no schedule, default-off WGS_ONPREM_MONITOR_ENABLED. Strict conf contains
pipeline=wgs, monitor_only=true, analysis_id, execution_id, attempt, generation.
It only calls the internal native observation endpoint, checking response identity.
No prepare, launcher, SSH, qsub, transfer pool, cleanup or business-failure callback.
Sensor timeout/API failure must not mark the native analysis failed or retry work.
It does not interpret a native .exitcode alone as controller termination. Candidate
attachment now uses fixed native__execution_id and exact monitor-only conf; only
the validated direct-child wait receipt closes the observed execution. No deployment.

## REL-01 WGS pre-execution SSH reconnect

`run_stage_on_200` reuses one stage registration and identical SSH command for
up to two reconnects (5s,10s) after allowlisted OpenSSH pre-session failures.
Return255 alone is insufficient; nonempty stdout or unrecognized diagnostics
disable reconnect. Authentication, host-key and business failures do not retry.
The connection budget is shared across the existing request-visibility loop,
not reset by it. Task retries/generation creation remain unchanged. Ambiguous
disconnects retain the existing bounded, generation-aware terminal-status check,
then fail without replay; this does not promise automatic recovery of a running
remote process. GATK and local execution paths are unchanged in REL-01.


## Explicit GATK Step7 maintenance

`bio_gatk_maintenance` is a separate admin-requested DAG containing
`step7_cleanup -> wait_step7_cleanup`. No destructive ALL_DONE tail is added to
`bio_gatk`. Conf binds pipeline, analysis, current attempt and maintenance action.
Its failure callback changes only the corresponding maintenance action, never
analysis or Sample success. Node-side generation/receipt and maintenance flock
guards make repeated dispatch safe; status polling tolerates transient outages.

GATK production promotion81587fc adds generation-aware terminal reconciliation:
`bio_gatk` reports failed current attempts through the authenticated internal
dag-terminal endpoint. Runtime status transitions preserve attempt/execution
identity; successful workflow stages are not inferred from a failed transport.
Manual GATK inherits global active-run concurrency; WGS pools and automatic scanning policy are
unchanged. Production activation registers/unpauses bio_gatk but submits no run.

## Generic contract

Each deployed adapter declares one DAG ID. FastAPI submits through the adapter and stores the analysis-to-DagRun binding. Airflow coordinates project-level stages; rule/file dependency remains workflow-owned.

Only DAGs for deployed real adapters ship in the active tree. Retired demo DAGs and mock runners are not retained.

## Current WGS DAG

Source-only resume_stage binds resume_action_id and ordered resume_stages.
Existing task callables bypass prepare, approvals, target commit and completed
stages, retaining frozen CCE target and attempt. Only selected/necessary stages
register recovery requests; transfer leases apply only to selected transfers.
Finalize and transfer success dependencies are preserved. Old DagRun lease
cleanup must pass the action fence before deactivating the current observer.

Canonical WGS CCE Step1–6 status GET sensors use six retries after the initial
query:30s delay, exponential backoff, max_retry_delay300s per delay. HTTP408/429/
5xx and transient connection interruptions retry. Authentication, business,
malformed payload and terminal failures use AirflowFailException. A failed
observer-deactivation POST is not retried by the sensor. Preparation, Step7,
GATK/local sensors and side-effect task retry settings are unchanged.

`bio_wgs` remains the current production workflow. It preserves the accepted prepare, execution commit barrier, Step1–Step6, Step6 materialization wait, finalize, and maintenance boundaries. CCE and enabled local targets are mutually exclusive branches. Directional upload/download leases and heavy-slot quotas remain independent scheduling controls.

## GATK Cloud DAG

`bio_gatk` is a manual-only DAG without a DAG-specific `max_active_runs` override.
It inherits `core.max_active_runs_per_dag` (production verified16 on2026-09-14).
Its ordered graph is
Validate, Prepare, Step1 Upload, Step2 Master, Step3 Monitor, Step4 Publish,
Step5 Download, Step6 Materialize and Finalize. It uses the fixed node200
forced-command runtime. Step2 uses `default_pool`, not `gatk_cce_runs`, so
different batches can submit Masters concurrently. Step1/Step5 share the existing
directional OBS pools and leases with WGS; GATK does not consume the WGS heavy
work-pod quota.

Directional `wgs_obs_upload` and `wgs_obs_download` pools remain one-slot;
durable transfer leases enforce the complete transfer lifetime across reschedules.
They do not serialize Step3 cloud analysis. Existing batch-identity guards remain.

Airflow tasks remain project-level. Snakemake rule/sample events come from the
GATK `rule-status` logger and are not expanded into Airflow tasks.

## Failure projection

Terminal Airflow failures must be projected into the business database. An observer or rerun must be able to recover from persisted generation and receipt evidence without launching a duplicate stage.
# GATK success barriers (2026-09-14)

## Bounded GATK observation retries (2026-09-14)

Only the `stage_ready` GET sensors retry transient backend failures: connection
refusal/reset, read timeout/disconnect/incomplete response, or HTTP408/429/500/
502/503/504. Airflow allows six retries, starting at30 seconds with exponential
backoff and a five-minute maximum delay. Existing reschedule mode and stage
timeouts remain in force. Retry counts belong to the Airflow task `try_number`,
not to the analysis attempt or runtime generation. Exhaustion reports an
orchestration failure; it is not permission to terminate or delete cloud work.

Non-transient HTTP responses, malformed JSON/non-object payloads and explicit
terminal failed stage receipts use `AirflowFailException` and bypass remaining
retries. HTTP error bodies and transport details are not copied into task logs.
Stage registration, SSH dispatch, transfer acquire/release and finalization
retain zero automatic task retries: they cannot be blindly replayed after an
ambiguous POST/SSH response. This patch does not rebuild Masters, change frozen
attempt identity, release a live transfer lease or rerun biological computation.

## Success dependencies

`submit_step2_master` requires both `wait_step1_upload` success and input-slot
release. `materialize_step6_results` requires both `wait_step5_download` success
and result-slot release. Slot releases retain `ALL_DONE` so failures free capacity,
but release success alone must never launch later pipeline work.

GATK release callables reject `retained=true` responses. Already-released leases
remain an idempotent success. Step1/Step5 status polling converges transfer state
from a validated terminal receipt before declaring ready, including replay of an
already-terminal stage after interrupted synchronization.
