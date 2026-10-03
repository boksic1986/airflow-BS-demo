# Airflow DAG specification

## UE-05 native callback and cleanup bridge (2026-09-30, source only)

Current WGS/GATK failure callbacks and transfer/global cleanup use the shared
native callback reader. The graph's latest started stage selects an existing
stage-status GET; that response supplies the current registration for a fixed
read-only native observe. The full snapshot is validated before it is passed as
`native_stage_observation` on the existing authenticated POST. Task state and
submit XCom never substitute for native terminal evidence. The backend checks
its own current/latest row again under the run lock, so a stale callback cannot
select an older successful execution to release current ownership.

Input/result slot cleanup reads Step1/Step5 respectively; global cleanup reads
the graph's current native stage. WGS observer drain uses a separate exact Step3
observation, including after later stages finish. Observation transport failure
does not send a fabricated terminal or release request. Unknown remains unknown
and is rejected by the backend permit fence.

Step3 recovery polling receives this invocation's exact native snapshot before
settling the current queued action. If a Worker challenge follows, its second
POST carries only the separate nonce-bound `worker_observation`, preserving the
existing Worker deadline and persisted stage-terminal binding.

## UE-05 shared SSH connection layer (2026-09-30; source only)

The current WGS/GATK Step1-6 restricted node200 commands and P0 Step4
dispatch/read probe and Step3 Worker read probe use one OpenSSH transport
implementation. It preserves each caller's fixed command, SSH config, exact
registered execution/generation/hash, original deadline and backend permit.
OpenSSH has a 30-second connection/handshake setting and
`ConnectionAttempts=1`; the transport permits at most three pre-session
connection attempts with 5/10-second backoff inside one caller budget. The
existing WGS request-visibility business retry may make a separate connection
after a connected response, while retaining that failure count and deadline.
Short dispatch is capped at
120 seconds. Existing Step4 read probe remains capped at 30 seconds, Step3
Worker probe at 150 seconds, and either is further capped by its original
persisted deadline. No stage lifetime is invented where no absolute deadline
was frozen.

Only exit 255 with empty stdout and wholly recognized pre-session diagnostics
may reconnect. Authentication/host-key failure, mixed/unknown output, command
timeout and post-session ambiguity are never replayed as SSH writes. An
uncertain marked dispatch uses the UE-04 exact native observation; `unknown`
cannot authorize a resend, later stage or cleanup. The transport cannot
register a new execution, consume a recovery budget or grant P0 redispatch.
The WGS request-visibility loop shares the connection-failure count and total
budget across its invocations. DAG task retry counts, pools and leases remain
unchanged. The node97 local path, Step7 and maintenance DAGs are outside this
connection change.

## WGS 4.2.3 prepare extension (2026-09-30; planned)

The 2026-09-30 plan observed synchronous `prepare_analysis`; an existing wait
task does not by itself make the node handler asynchronous. The deferred
W423-03 extension proposes the shared executor's trusted prepare registration
and short submit/current-execution observation described in
[design section4](superpowers/specs/2026-09-30-wgs423-upgrade-integration-design.md).
In that proposed contract, frozen preparation inputs authorize prepare before
the final batch binding exists, and successful final outputs produce the
binding. Step1 would wait for all merge/selection/bundle/receipt completion.
Normal prepare deadlines would remain; merge-enabled new requests would freeze
a configurable24h default business deadline independently of SSH budgets.
Observation timeout is not proof of background failure or permission to
dispatch again. This is a deferred design, not a change to the current DAG or
its frozen requests; this documentation merge authorizes no implementation.

## SSH banner timeout trailer (2026-09-27)

The earlier WGS pre-execution reconnect accepted the OpenSSH companion line
`Connection to <host> port <port> timed out` only alongside a recognized
pre-session error. The trailer alone remains insufficient. Exit255, empty
stdout and fully recognized stderr are still required; remote/business or
ambiguous post-execution output is never automatically replayed. Existing
three-invocation limit,5s/10s delays and original registration/generation remain
under the shared connection layer above.

## UE-04 unified stage client (2026-09-30, source only)

Newly marked WGS/GATK Step1–Step6 registrations return the exact frozen
execution ID, generation, request hash and `stage_execution` marker. The DAGs
obtain the full native ref by the fixed read-only `--native-observe` command,
compare it with that registration, and use the fixed `--native-submit` command
with the same ref. A marked submit makes one logical SSH dispatch per task
invocation, with only proven pre-session connection retries inside that call;
an uncertain response is reconciled by observing that ref. Airflow task retries
reuse the same registration and rely on the native launch fence to attach to
an existing dispatch or start a first dispatch that never happened. A native
`unknown` result never advances a stage or authorizes a second launch within
the same invocation. Older unmarked frozen requests retain their prior gate
path.

WGS Step2 keeps its existing `submit_step2_master` task and `wgs_cce_runs`
pool, holding the task until a matching native terminal result; no additional
Step2 sensor or shared stage deadline is introduced. Step6 still requires
`wait_step6_materialize` before `finalize_run`; native success and the current
business receipt must both be visible. GATK keeps its submit/wait task graph
and evaluates both tasks through the same client. The original task/sensor
timeouts and the separate Step4 publish recovery authorization remain in
force. This candidate has not been installed on node200 or deployed.

At finalization the WGS and GATK DAGs query current Step6 stage status and
perform a fresh fixed native observation, including when a recovery DagRun
reuses a successful Step6 and its submit task has no XCom. They pass the full
snapshot to the existing internal finalize POST. The backend ties the native
terminal to the exact current registered business receipt before committing
success. Older unmarked Step6 requests keep the receipt-only finalization.
For any newly marked Step1–Step6 whose submit XCom is absent, a stage sensor
uses the current backend registration to make a fresh exact native observation
before accepting the business-ready receipt. Missing, stale or unknown native
evidence cannot advance the sensor; older unmarked registrations retain their
existing sensor path.
An Airflow administrator marking a DagRun successful cannot by itself project
WGS/GATK business success; the guarded finalizer is authoritative. WGS canary
and local validation scopes retain their existing success projection because
they do not execute the full CCE Step6 path. GATK reconciliation recognizes an
explicitly authorized current same-attempt recovery DagRun, not an arbitrary
run-ID suffix; reconciliation also compares its Airflow `conf` with the frozen
authorized action before projecting a state.

## DAG discovery isolation (2026-09-27 test branch)

`bio_wgs_native_monitor`, `bio_wgs_maintenance` and
`bio_gatk_maintenance` retain their existing DAG IDs, tasks and runtime API
calls. They load helpers from `bio_wgs` or `bio_gatk` only when a task executes,
not at module import time. This keeps Airflow's DAG-folder scan from registering
the main `bio_wgs`/`bio_gatk` DAG a second time from an auxiliary file. A real
DagBag discovery test requires zero import errors and the main DAGs' own files
as their discovery owners. This does not change execution gates or authorize a
business run.

## WGS independent Step7 maintenance (2026-09-22 candidate)

New requests use bio_wgs_maintenance (max_active_runs=1), with only
step7_cleanup and wait_step7_cleanup. No analysis or transfer pool is used.
Existing maintenance run IDs retain their old DAG route. Task retries are zero;
read-only reconnection delays are30/60/120 seconds. An ambiguous launch response
is reconciled before at most one identical resend, allowed only if not_started.
Running/success attaches, unknown stops, failed deletion needs manual retry.
Failure callbacks affect only the maintenance action. Test acceptance pending.

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
