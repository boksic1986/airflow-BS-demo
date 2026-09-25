# Airflow DAG specification

## Task6 existing Step4 runner/sensor (2026-09-25, source only)

For an enabled frozen current-attempt policy, start_step4_publish registers the
original operation, obtains the committed begin permit, rechecks check, invokes
fixed --publish-dispatch ANALYSIS_ID ATTEMPT GENERATION REQUEST_HASH and reports
finish only after that local SSH invocation exits. SSH timeout/nonzero is an
uncertain outcome, not another send. Process death/lost API reply retains durable
in-flight ambiguity. SSH dispatch is capped at120s and the original stage deadline.

wait_step4_publish performs at most one read-only --publish-probe per poke (30s /
remaining deadline), echoes exact identity+nonce on the existing stage route,
and sends only when the backend grants that same-operation redispatch. Failure to
observe never grants dispatch. Persisted60/180 waits and two-slot dispatch budget
remain backend-owned; no sensor sleep loop. Expired/exhausted/stopped/failed ends
automatic reconciliation. Success additionally requires the existing stage-status
normal receipt before downstream. Default-off/legacy behavior, DAG graph, pools,
task retries and the compute budget are unchanged. No production activation.

## Task6 natural Worker wait (2026-09-25, source only)

The same WGS/GATK Step3 sensor performs at most one fixed read-only SSH probe per
poke when compute_recovery returns a Worker challenge. Existing runner alias,
SSH config and restricted wrapper are reused; probe timeout is at most150s and
capped by the returned wait deadline (2026-09-25 V07 correction). The inner
workload probe retains its120s budget; a result arriving after the persisted wait
deadline is not submitted. The backend owns the persistent action,
600s/original-deadline limit and compute budget, not the sensor or SSH process.
Successful observation is returned to that same POST; SSH timeout/nonzero/invalid
response reschedules without another local retry. Delegation still skips the
old chain before observer deactivation. No DAG nodes/pools/retry counts changed.

## Task6 automatic sensor handoff (2026-09-25, source only)

WGS/GATK existing Step3 reschedule sensors call compute_recovery only when their
frozen conf policy is enabled for that exact attempt. The POST uses actual
context.dag_run.run_id, not a conf-supplied identity. Poll even when the latest
monitor is running: a lost POST reply may mean that row belongs to the replacement.
waiting/uncertain returns false; delegated/superseded raises AirflowSkipException
before WGS observer deactivation and before downstream execution. Only the current
DagRun may settle its registered compute action and advance after success.

No DAG nodes, stage ordering, pools or retry counts changed. WGS idempotent
recovery reconciliation shares its existing bounded stage-query transport retry
classification; GATK uses its existing backend transport classification. Default-off,
legacy and mismatched-attempt policies do not call the automatic operation.
Native deadline enforcement and bounded Worker wait are covered by subsequent
checkpoints. Step4 and remaining Task6 integration remain open; this sensor wiring
is not whole Task6 acceptance or rollout authorization.

## P0-2 GATK manual recovery selection (2026-09-24, source only)

bio_gatk uses the persisted resume_stages list: skipped runner/sensor/transfer
boundaries succeed without preparing, uploading, registering or dispatching SSH.
Finalization and final lease cleanup remain in the original graph. Selected
registrations send actual dag_run.run_id and resume_action_id, never a conf-supplied
DagRun ID. The backend independently checks scope/current identity/control state.
No graph order, pool, timeout or retry-budget changes. GATK Resume capability stays
disabled pending the restricted native integration and Task4 full acceptance.

## P0 old cleanup request protection (2026-09-23, source only)

WGS/GATK directional/final lease cleanup sends actual dag_run.run_id, never the
original conf value. WGS Step3 terminal drain and final observer drain carry
that ID plus resume_action_id. Failed release/retained lease prevents final
drain; the backend independently checks each request under the refreshed run
lock. No task graph/order/pool/retry/limit changes; Local/SGE DAGs unchanged.
No automatic dispatch enabled. Backend API must precede DAG rollout.
Remaining observer generation projection and recovery dispatch are not covered
by this external-cleanup fence; PostgreSQL concurrency remains unverified.

## P0-2 WGS manual recovery identity (2026-09-24, source only)

For resume_action_id runs, register_stage sends actual dag_run.run_id on EVERY
registration, including acquire/finalize, never conf.dag_run_id. Existing stage
selection still skips prepare/upload/completed stages for Step3 Resume.
The backend validates current action, attempt, DagRun and selected stage before
mutating generation/leases/run. Ordinary non-recovery registration is unchanged.
No new DAG/task/order/pool/retry policy or automatic activation. Roll out this DAG
payload and the matching backend together; no deployment is part of Task4 work.
GATK authenticated Resume and native selected-view propagation remain open.

## P0 old failure callback protection (2026-09-23, source only)

GATK report_dag_failure now sends actual dag_run.run_id with its existing attempt
and failed task list; WGS already does. Backend rejects superseded/pending/unbound
recovery callbacks before projection while allowing the exact current dispatched
recovery DagRun's failure. No DAG graph, retries, pools or task ordering changed.
This is not yet observer/lease fencing or generic Airflow/runtime failure separation.
The internal API addition must precede the DAG update in a future approved deploy.

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

The `stage_ready` GET sensors and idempotent input/result slot-acquisition
sensors retry transient backend failures: connection
refusal/reset, read timeout/disconnect/incomplete response, or HTTP408/429/500/
502/503/504. Airflow allows six retries, starting at30 seconds with exponential
backoff and a five-minute maximum delay. Existing reschedule mode and stage
timeouts remain in force. Retry counts belong to the Airflow task `try_number`,
not to the analysis attempt or runtime generation. Exhaustion reports an
orchestration failure; it is not permission to terminate or delete cloud work.

Non-transient HTTP responses, malformed JSON/non-object payloads and explicit
terminal failed stage receipts use `AirflowFailException` and bypass remaining
retries. HTTP error bodies and transport details are not copied into task logs.
Slot acquisition replays the exact analysis/attempt/directional transfer identity;
the existing lease primitive returns its already-owned slot, never steals another
identity or dispatches transfer work. Response loss after commit is safe to replay.
The48-hour acquisition timeout and directional pools are unchanged. This addition
was verified on BS10610 with synthetic requests, not deployed to current runs.

Other stage registration, SSH dispatch, transfer release and finalization
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
