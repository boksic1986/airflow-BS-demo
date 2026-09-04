# WGS Step1-6 Orchestration Contract v2

## Decision

The platform keeps one `bio_wgs` DAG and the existing `cce-pipeline` execution
surface. Airflow owns project-level orchestration, node200 owns restricted
execution, and runtime truth comes from Kubernetes resources, Snakemake logger
events, and immutable terminal markers. The browser and Airflow metadata DB are
not runtime truth sources.

This is the approved option 2 architecture. It does not rewrite the WGS
workflow or turn individual Snakemake jobs into Airflow tasks.

## Audit Findings

- Step4, Step5, and Step6 previously depended on mutable latest-stage state and
  retry sidecars. A late status could be mistaken for the current execution.
- `RunStageState` was asked to be both current UI state and retry history.
- Run Detail fetched most resources eagerly and repeated status synchronization
  from the browser.
- Transfer progress was aggregate-only and the obsutil adapter inferred totals
  while the transfer was already changing.
- `wgs_cce_runs` was attached to the Step3 sensor, which obscured that it only
  controls Master handoff and cannot limit Worker Pods.
- Resource panels had no live node spool or Cloud Eye spool in the deployed
  environment, so the UI correctly showed `not reported`.

## Stage Contract

`config/wgs_stage_contract.yaml` is the versioned execution contract. New runs
carry `orchestration_contract_version=2`; contract-v1 runs remain readable.

| Stage | Runtime truth | Success evidence |
|---|---|---|
| Step1 upload | OBS SDK callback | frozen input manifest plus transfer receipt |
| Step2 Master | Kubernetes API | UID and resourceVersion recorded |
| Step3 analysis | Kubernetes API and Snakemake logger | Master terminal marker agrees with K8s terminal state |
| Step4 publish | fixed result manifest | exact generation publish receipt |
| Step5 download | OBS SDK callback | every frozen manifest file verified |
| Step6 materialize | local atomic operation | marker and manifest hash agree |

`wgs_stage_execution` is append-only by
`analysis_id + attempt + stage + generation`. Status transitions are limited to
`accepted -> running -> success|failed|canceled`. A retry creates a new
generation. A complete reanalysis creates a new attempt. Late evidence from an
older generation is ignored and cannot overwrite the current projection.

`RunStageState` remains the latest read model only. It is not retry history and
cannot authorize a downstream stage. Contract v2 does not use the historical
Step4 repair route; a failed stage is retried with a new exact generation and
predecessor receipt.

## Transfer Contract

New runs use the Huawei OBS SDK adapter. Step1 freezes all input files before
upload. Step4 freezes the publish manifest and Step5 downloads only that exact
manifest. Each transfer writes an atomic aggregate snapshot and append-only
JSONL events. Callbacks emit at least once per second or every 64 MiB, while
file start, success, and failure emit immediately.

`transfer_file_state` stores privacy-safe file labels, sizes, bytes completed,
speed, checksum state, and bounded errors. Public APIs never return credentials,
full OBS URIs, checkpoint directories, or unrestricted server paths. The
obsutil adapter remains a controlled rollback path.

One database-backed `wgs_obs_transfer` lease serializes Step1 and Step5 across
runs. This is independent from the high-I/O Worker Pod quota.

## Heavy I/O Quota

`wgs-heavy-io` means 25 concurrently running high-I/O **Worker Pods**, not CPU
cores, Airflow tasks, DAG runs, or Masters. Initial evidence-backed groups are:

- `pre_process_mapping + pre_process_Dedup`
- `pre_process_Haplotyper + pre_process_QualCal`

The vendored Kubernetes executor acquires one of 25 namespaced Kubernetes
Lease objects before creating a heavy Job. It heartbeats every 60 seconds and
only reclaims a lease after ten minutes when both the referenced Job and Pods
are absent. Waiting work does not create a duplicate Job.

The production contract defaults to `enforce`. Existing operator configs that
omit `heavy_io` remain `monitor-only` for backward compatibility and must be
updated explicitly after RBAC validation. The Role is limited to Lease access
in `snakemake-ns`; the RoleBinding service account must match the frozen CCE
profile before apply.

Cloud Eye SFS bandwidth is measured in bytes per second and rendered with IEC
units such as GiB/s. It validates classification and raises alerts only; it
does not automatically change the 25-slot limit in this release.

The first transfer-adapter validation reuses the shared Python 3.9 environment
at `/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest`, with
`esdk-obs-python==3.26.6` and `huaweicloudsdkcore==3.1.210`. The environment is
writable from node005 and read-only from BS10610; both BS10610 and node200 must
pass `ObsClient` imports before a synthetic transfer is attempted. Credentials
remain outside the Conda environment and release.

## Read Model And Frontend

`GET /api/runs/{analysis_id}/workspace` is the Run Detail first-paint resource.
It returns run identity, project stages, current rule, active transfer,
validation issues, and slot use from database snapshots. Samples, Rules, Logs,
Files, Pods, and transfer files load once when their tab opens.

Active Run Detail reads workspace every ten seconds with an in-flight lock and
pauses while the page is hidden. Dashboard resources refresh independently
every 60 seconds. Browser timers never POST `sync-airflow`; the observer owns
state projection. Terminal progress never calls Airflow REST.

Rules are filtered and paged in SQL, default 50. Transfer files have a separate
paged endpoint. Stage/rule ETA history is loaded in one query rather than per
row.

## Resource Collection

`platform-node-probe` uses a dedicated read-only SSH configuration for
`172.17.61.96` and `.97`, writes one atomic node spool, owns no DB credential,
and publishes no port. `platform-metrics-collector` reads node and Cloud Eye
spools and writes resource snapshots. Last-good values remain visible with an
explicit stale/degraded state.

Cloud Eye collection runs outside the Docker control plane because its
read-only credential stays on the approved host. The spool contains only
numeric SFS capacity/read/write/total-I/O/IOPS values and timestamps.

## Rollout Gates

1. Keep WGS execution and auto-dispatch disabled.
2. Verify database backups and confirm no active WGS run.
3. Run backend, DAG, runtime-gate, CCE plugin, frontend, migration, nginx, and
   Compose checks from the candidate release.
4. Apply the Lease RBAC only after checking the frozen Master service account.
5. Install the tested CCE wheel and SDK runtime without credentials in images.
6. Start node/resource collectors and verify fresh data before enabling alerts.
7. Enable contract v2 and SDK transfer for a synthetic transfer acceptance.
8. Enable heavy-slot enforcement for a controlled WGS batch and verify no more
   than 25 heavy Worker Pods exist.

Do not enable execution merely because unit tests pass. Do not restart an
active Worker or Master, directly edit Airflow metadata, place credentials in
Git, or write validation evidence under `/tmp`.
