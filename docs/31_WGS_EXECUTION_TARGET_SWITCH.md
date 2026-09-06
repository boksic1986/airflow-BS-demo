# WGS execution target switching

## Purpose

T209 separates WGS preparation from the irreversible execution commit. A run
keeps one `analysis_id`, Airflow DagRun ID and attempt while it is preparing or
waiting for a resource. Before commit, an operator may change the desired
target between CCE, Local `.97`, Local `.96` and SGE. The automatic intake path
always creates `cce/cce`; it never selects a local node or SGE.

The execution claim is unique by `project_id + batch`. Existing manual,
running, successful or failed runs therefore prevent automatic resubmission.
The activation watermark remains mandatory for automatic intake, so rows that
were already ready before activation are only the scanner baseline.

## State machine and concurrency

`wgs_execution_dispatch` is the authoritative batch claim. Its states are:

```text
preparing -> waiting_resource -> committed -> running -> terminal
                                      `-----------> needs_recovery
```

`dispatch_revision` is optimistic concurrency for the browser. Target changes
and scheduler commit both lock the `AnalysisRun`, current `RunAttempt` and the
same dispatch row. Only one transaction can win. Once `committed_at` is set,
the target is immutable for that attempt. A CCE commit also atomically acquires
the dedicated OBS upload lease immediately before Step1 becomes reachable.
Step5 later uses a separate download lease, so a different completed batch may
download while this batch uploads. Neither direction expires by wall-clock
time; only matching terminal transfer evidence releases it.

Local target slots are represented by `wgs_execution_target_slot`, one row for
each of `node-97` and `node-96`. They are batch-exclusive and are released at a
terminal state. Local admission requires a healthy metric snapshot no older
than three minutes, at least 96 logical CPUs, no other committed local WGS run,
and three consecutive one-minute points where CPU and normalized Load1 are
both below 25 percent. Memory at or above 75 percent is a warning, not a hard
block.

## DAG behavior

`bio_wgs` keeps the existing preparation and Step1-Step6 CCE tasks. After
sampleinfo and analysis preparation plus execution approval it adds:

```text
wait_wgs_execution_approval
  -> wait_execution_commit
  -> choose_execution_target
       |-> input_transfer (CCE Step1-Step6)
       |-> local_execution
       `-> sge_execution
```

`wait_execution_commit` is a reschedule sensor and reads the current database
choice on every poke. `choose_execution_target` reads the already committed
choice; it does not trust DagRun conf as the current target. Local and SGE
branches are fail-closed placeholders in Phase 1.

## Frontend and API

Submit Run stage 3 and WGS Run Detail render the same segmented selector. The
confirmation displays batch, sample count, attempt and the server-projected
node snapshot. The browser sends the revision and an audit reason to:

```text
POST /api/wgs/runs/{analysis_id}/execution-choice
```

The server returns `TARGET_UNAVAILABLE`, `STALE_EXECUTION_CHOICE` or
`EXECUTION_ALREADY_COMMITTED` as HTTP 409 without changing the attempt. Run
Detail returns `execution_dispatch` with the current target, lock state,
revision, target availability and admission metrics. After a CCE commit the
selector is read-only and ordinary Cancel is unavailable.

## Rollout gates

Phase 1 ships the schema, CCE commit barrier, API and UI with all alternative
capabilities false:

```text
WGS_LOCAL_NODE97_ENABLED=false
WGS_LOCAL_NODE96_ENABLED=false
WGS_SGE_ENABLED=false
```

Phase 2 may enable `.97` only after the fixed `--cores 96` runner and recovery
path pass a separate acceptance. Phase 3 independently accepts `.96` and SGE.
The DAG placeholders deliberately fail if a capability is enabled without its
accepted runner. No T209 source validation requires a production deployment or
changes an in-flight CCE Master.
