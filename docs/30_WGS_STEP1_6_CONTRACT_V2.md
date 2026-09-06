# WGS Step1-6 Orchestration Contract v2

## T213 T208/T209 and directional-lease integration

The merged contract keeps T208's accepted Step1-Step6 semantics as the stage
authority and inserts only T209's pre-Step1 database commit barrier. New work
uses independent, non-expiring upload and download leases. Observer-imported
terminal transfer evidence releases the exact matching direction; Airflow
cannot release on timeout, transient backend/NFS failure or unknown remote
state. Step5 retains the frozen manifest denominator and configured concurrent
file downloads. Step6 remains one batch-level atomic materialization followed
by `wait_step6_materialize`; it is not converted into sample-parallel work.

The 25-Worker-Pod Heavy Slot contract remains independent of both directions.
Local and SGE branches remain disabled placeholders and cannot enter the CCE
or OBS task graph. T213 validates the unified T208 SDK/Step3 behavior from
clean cce-pipeline source `b5696065bc24ab2049e46dc3c1b9594771bfce28`;
old T197 branch behavior is not merged separately.

## T208 full contract acceptance

The option-2 contract is now accepted end to end on the BS10610 test control
plane. Analysis `WGS_20260906_075824_E4D23E`, attempt 4, completed Step1-Step6
and finalization with exact generation and predecessor receipts. Step1 verified
6 files / 403,858,510,658 bytes; Step5 verified 11 files /
173,827,124,513 bytes; Step6 materialized the identical manifest MD5
`8f15230d744c54f846dfc9173c234796`.

The real Master logger emitted 707 JSONL events and the observer projected all
209 scheduled jobs as terminal success. The accepted workload used three
Heavy Slot holders and released all of them. The earlier independent quota
test remains the capacity proof: 25 holders acquired, contender 26 waited, and
all holders were released.

Acceptance required fixes to exact retry-generation synchronization, sensor
handling of temporary backend 5xx, transfer-file accumulation and idempotent
same-generation Rule projection repair. These fixes preserve all fencing:
older generations, wrong executions, wrong releases and mismatched markers
still fail closed.

After closeout, `bio_wgs` is paused and all BS10610/node200 execution,
auto-dispatch, scheduled-scan and canary gates are false. This completes the
test acceptance only; production activation remains a separate reviewed
rollout.

No additional full workflow is required to reproduce routine release
acceptance. T209 will add a hidden 60-120 second Step3/Step4 contract Rule that
emits normal logger evidence and publishes a tiny frozen artifact. Full WGS is
reserved for first-time contract acceptance or a material change to analysis,
transfer-manifest or materialization semantics.
## T209 pre-Step1 execution commit

T209 adds a database-backed commit barrier after preparation and approval but
before Step1. It does not alter the Step1-Step6 evidence chain described below.
CCE remains the only Phase-1 runner; the commit atomically owns the existing
OBS upload lease and then routes into the unchanged CCE graph. Local and SGE
do not become available until separate runner acceptances. The full target
state, admission and rollout contract is in
[document 31](31_WGS_EXECUTION_TARGET_SWITCH.md).

## Post-T206 configuration audit and Step4-Step6 admission

The T206 acceptance proves Step2 identity, Step3 dry-run evidence and the
25-holder Lease mechanism. It does not authorize Step4-Step6 or prove that the
disabled runtime configuration has one authoritative source.

A read-only audit of the deployed BS10610 test control plane found that the
control plane is disabled and `bio_wgs` is paused, while node200's restored
pre-T206 runtime baseline still enables execution, the runtime adapter and the
Step3 dry-run canary. This split state is operationally closed only because the
upstream controls are currently false. Step4-Step6 acceptance requires both
sides to be explicitly disabled before and after the maintenance window.

T207 must converge these configuration contracts before a real run:

- Scanner behavior defaults to disabled and is loaded from one versioned
  intake policy; a missing environment file cannot start the scanner.
- Heavy Slot limit, mode, heartbeat, reclaim interval and rule groups come from
  `config/wgs_stage_contract.yaml`; startup rejects conflicting overrides.
- Approved data roots explicitly map the BS/container/node200 views. Runtime
  binding location is configured directly rather than inferred from a sibling
  directory.
- Platform and Airflow administrator initialization is create-only; credential
  rotation is an explicit operation and startup does not swallow arbitrary
  failures.
- Backend, Airflow and frontend deployment artifacts are tied to one release
  revision and digest manifest.

The repository implementation now enforces these contracts. Scanner startup
requires both the default-off environment gate and
`scheduled_scan_enabled` from `config/intake.wgs.yaml`; the service is isolated
behind the Compose `intake` profile. FASTQ roots resolve through explicit
control-plane/node200 catalog paths, and runtime bindings use an independent
`WGS_RUNTIME_RUN_ROOT`. Heavy Slot `25/enforce` comes from this stage contract,
is copied into each contract-v2 stage request, and must match the frozen CCE
profile. Administrator bootstraps no longer overwrite existing accounts or
swallow Airflow initialization errors.

The BS10610 disabled rollout was release
`20260906-airflow-demo-841eb55-t207-disabled`. Its control-plane gates are
closed, DAG paused and scanner absent. Registry DNS prevented a clean rebuild,
so the release inventory truthfully records reused verified runtime image IDs
plus exact read-only source revision `841eb55`; it does not claim a rebuilt
image. The owner-side gate was subsequently installed and verified before
T208.

After T207 passed, T208 ran one approved small-family canary through the normal
contract-v2 path. Step4 consumed the exact successful Step3 execution; Step5
consumed the exact Step4 generation manifest; Step6 atomically materialized
that same manifest hash. Scanner and auto-dispatch stayed disabled, and the
canary did not run on `.96` production.

## T206 Step2/Step3 dry-run validation

Contract v2 adds a default-off `step3_dryrun` validation scope for one bounded
control-plane canary. It uses the real Step1 receipt, Step2 Master identity,
Kubernetes status, Snakemake logger, and Step3 terminal evidence, but freezes
the generated batch contract to dry-run before submission. A verified run exits
after Step3 and cannot authorize Step4, Step5, or Step6.

The independent Heavy Slot acceptance uses the executor's real Kubernetes
Lease implementation with 26 no-compute contenders. The quota unit remains one
active high-I/O Worker Pod: 25 holders may acquire a slot and the 26th waits.
This probe validates coordination only and does not create an analysis Job.

Acceptance completed on BS10610 with DagRun
`WGS_20260905_210104_739143-a8`. The exact Master planned 210 Snakemake jobs in
dry-run mode, emitted logger planning evidence, and created no Worker Job or
Pod. Step4-Step6 were unreachable. The independent 26-contender probe acquired
all 25 fixed slots, left one contender waiting, then released every holder.
The 25 Leases are pre-created and `cce-pipeline-master-v1` can only get/update
those exact names; list/create/patch are denied. This least-privilege RBAC is a
contract-v2 deployment dependency.

The canary's tiny Step1 setup used the obsutil rollback adapter and is not the
SDK callback acceptance. T205 remains authoritative for frozen byte totals and
per-file SDK progress. T206 proves the Step2 identity, Step3 runtime truth,
dry-run branch fencing, and Heavy Slot coordination.
The finalizer also fences Step3 to the latest successful Step2 receipt, frozen
release and run-local batch binding; terminal evidence from a stale generation
or mismatched Master cannot authorize validation success.

## T205 direct-upload startup

The default Step1 SDK path starts network transfer after freezing the manifest
and filesystem identity. It does not calculate a full-file MD5 and deliberately
omits the OBS SDK multipart `checkSum` option, because SDK 3.26.6 implements
that option as a complete SHA256 read before initiating upload.

This startup change does not weaken the terminal receipt. Multipart uploads
retain attached per-part CRC64; completion requires response/object CRC64,
Content-Length, and frozen source device/inode/size/mtime to agree. Missing or
mismatched CRC64 fails closed. The obsutil rollback adapter retains its existing
`-vmd5/-vlength` semantics and is not the default for new contract-v2 runs.

The Airflow-integrated canary `WGS_20260905_154825_E39C58-a1` froze two files
and 113,993,536,856 bytes. Its first non-zero callback arrived about 32 seconds
after task start, and the transfer interval completed in 866.58 seconds at
125.45 MiB/s effective throughput. Both files ended success/verified and Step2
was skipped. Exact-prefix cleanup removed the two objects and marker; no object
or multipart upload remains.

Terminal stage evidence is allowed to complete its embedded file rows. If a
terminal progress snapshot arrives with an older heartbeat, it may only
backfill nonterminal rows after exact execution, generation, terminal status,
file-count and byte-total checks. This repairs event-order races without
letting stale evidence regress the aggregate execution.

## T203 Airflow integration canary

Contract v2 now has a fail-closed `step1_only` validation scope. It is an
admin-only API field, disabled by default, and not rendered in Submit Run.
The ordinary DAG path is unchanged. After the frozen Step1 transfer receipt,
the validation branch records `Step1 validation passed`, marks later public
stages skipped, releases leases, and cannot call Step2. Both the API and DAG
reject this scope unless the dedicated canary gate and contract v2 are enabled.

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

New runs use the Huawei OBS SDK adapter. Step1 freezes file identity and size,
then starts upload without an additional full-file checksum pass. Step4 freezes
the publish manifest and Step5 downloads only that exact
manifest. Each transfer writes an atomic aggregate snapshot and append-only
JSONL events. Callbacks emit at least once per second or every 64 MiB, while
file start, success, and failure emit immediately.

`transfer_file_state` stores privacy-safe file labels, sizes, bytes completed,
speed, checksum state, and bounded errors. Public APIs never return credentials,
full OBS URIs, checkpoint directories, or unrestricted server paths. The
obsutil adapter remains a controlled rollback path.

Two database-backed leases serialize transfers by direction:
`wgs-obs-upload-01` for Step1 and `wgs-obs-download-01` for Step5. They have no
fixed TTL, and only exact terminal evidence permits release. Upload and
download may overlap; two transfers in the same direction may not. This is
independent from the high-I/O Worker Pod quota.

The CCE 0.8.2 integration freezes three separate transfer controls. Operator
config `obs.upload_parallelism` is the number of Step1 files uploaded at once,
`obs.download_parallelism` is the number of Step5 files downloaded at once,
and obsutil uses five parts for each file. None of these values consumes or
changes the 25-work-pod heavy-I/O quota. The resolved values are retained in
`RESOLVED_PROFILE.yaml` and copied into the run binding as audit-only
provenance; Airflow does not duplicate them as a version gate.

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

### Real SDK canary

The standalone T200 canary uses two synthetic files, 1 MiB and 65 MiB, so the
larger file crosses the 64 MiB callback threshold. It must verify upload,
download, downloaded MD5, frozen aggregate bytes, generation reuse, progress
redaction and exact remote deletion. The accepted canary completed all checks
with a frozen total of 69,206,016 bytes and nine partial callback events.

`esdk-obs-python==3.26.6` requires two compatibility guards. Its built-in
progress notifier may clear the callback before queued updates drain, so the
adapter installs a queue-draining notifier. Its metadata response omits custom
metadata, so reuse first checks object size and then permits only a strict
32-hex single-part ETag fallback. Multipart ETags are not accepted as MD5.

The test credential is read from the existing CCE test Secret into a mode-0600
node200-only runtime file. Bucket names, object prefixes, credentials, full OBS
URIs and server paths are excluded from progress evidence and public APIs.

### Real FASTQ upload canary

T201 tested one approved validation sample as a real R1/R2 pair. The frozen
manifest contained `14,486,007,978` bytes (`13.4911 GiB`). Parallel upload
finished in `152.862` seconds at an aggregate `90.38 MiB/s`; R1 averaged
`49.49 MiB/s` and R2 averaged `47.26 MiB/s`.

The callback recorder produced 116 privacy-safe snapshots. It captured 68
distinct partial values for R1, 79 for R2 and 111 for the aggregate, while the
total denominator remained constant. This is sufficient for independent file
rows and a stable overall progress bar. A sample-level grouping can be derived
from its frozen R1/R2 manifest; the public response must continue to use safe
labels rather than source paths.

Real 6-7 GiB inputs require the resumable SDK API. Files larger than 5 GiB use
64 MiB multipart parts, four SDK workers per file, checkpointing and attached
CRC64. Burst callback increments are coalesced before JSONL writes so the SDK
cannot leave a large per-chunk callback backlog at shutdown. The accepted run
verified source immutability and remote size/CRC64, then deleted both exact
objects and confirmed HEAD 404.

This remains a standalone Step1 data-path canary. It does not enable contract
v2 or prove the browser/database projection until a separately approved
Airflow-integrated Step1 canary is completed.

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
7. Complete the standalone SDK synthetic transfer acceptance, then enable
   contract v2 only for one controlled Step1/Step5 integration canary.
8. Enable heavy-slot enforcement for a controlled WGS batch and verify no more
   than 25 heavy Worker Pods exist.

The current disabled candidate is based on cce-pipeline 0.8.2 source commit
`eacef2114cef6581397e9923d9674ab17b92b4df` plus the contract-v2 integration
commit `e4c0f134bd397fb6113456b18cc148346808388e`. Its Master image is
`airflow-demo/wgs-cce-master:contract-v2-cce-0.8.2-e4c0f13-candidate` with
image ID `sha256:58c2c9acf935f1d06c4b1b60d8bc56ca758d7d9643707b2d9077bc9445c6dae8`.
It remains unselected until an approved Airflow-integrated canary passes.

Do not enable execution merely because unit tests pass. Do not restart an
active Worker or Master, directly edit Airflow metadata, place credentials in
Git, or write validation evidence under `/tmp`.
