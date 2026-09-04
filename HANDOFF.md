# HANDOFF.md

## 2026-09-04 - Codex - T194-T200 WGS contract v2 and Heavy Slot quota

### Outcome

Implemented option 2 without rewriting the WGS workflow. Airflow remains the
Step1-6 project orchestrator, node200 remains the restricted executor, and
Kubernetes resources, Snakemake events and exact terminal receipts are the
runtime authorities. New contract-v2 runs use append-only stage execution
generations; stale evidence cannot authorize or overwrite a newer generation.

Step1/Step5 now support a Huawei OBS SDK adapter with frozen manifests,
per-file progress and atomic spool events. The browser receives safe file
labels only. The obsutil path remains the explicit rollback adapter. The
vendored Kubernetes executor classifies mapping+Dedup and
Haplotyper+QualCal as high-I/O and acquires one of 25 namespace Lease objects
before creating each heavy Worker Job.

Run Detail now loads `/workspace` first and lazily caches Samples, Rules,
Master, Transfers, Logs and Files. Active workspaces poll by GET every ten
seconds with visibility and in-flight guards; terminal runs do not query
Airflow. Rules and transfer files are SQL-paged. The warm workspace median on
the retained 208-rule run was 90.4 ms over five calls.

### Deployment

The disabled BS10610 release is:

```text
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260904-airflow-demo-c28ad7d-t194-contract-v2-disabled-r2
```

The frontend runtime image is
`airflow-demo/frontend:t194-contract-v2-disabled`. The staged, unused CCE
candidate is
`airflow-demo/wgs-cce-master:contract-v2-32851ba-candidate`, image
`sha256:48e17145...cabfa`; it contains executor `0.6.4+biosan4` and
`cce-pipeline 0.8.1`.

Execution, runtime adapter, contract-v2 activation and automatic dispatch are
all false. `bio_wgs` is paused, the intake scanner is stopped, and both
business/Airflow active-run counts are zero. No analysis was launched.

The dedicated node probe runs as UID 6708 and uses a mode-0600 test identity
outside Git. `.96` and `.97` resource rows are healthy. The approved production
CES read-only configuration now also drives an isolated BS10610 collector at
`/home/hanjj/.config/airflow-wgs-bs10610`. The AK/SK remains only in the
existing mode-0600 node200 credential file. A mode-0644, numeric-only
`cloud.json` crosses the shared runtime boundary; the API reports
`sfs-turbo-clinical` healthy with fresh capacity, read/write bandwidth and IOPS.

The existing shared `nipttest` Python 3.9 environment was reused for transfer
validation instead of creating a duplicate runtime. It now contains
`esdk-obs-python==3.26.6` and `huaweicloudsdkcore==3.1.210`; `ObsClient` and
`BasicCredentials` imports pass from BS10610 and node200. Installation was
performed through writable node005 `/sg2`; BS10610 exposes the same environment
read-only. Evidence is under
`/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/T200-obs-sdk-nipttest-20260904`.
The environment already had unrelated `pip check` findings for missing
`setuptools-scm`, missing `importlib-metadata`, and unsupported `veracitools`;
this task did not alter those packages.

A real standalone OBS SDK canary subsequently transferred 1 MiB and 65 MiB
synthetic files. Upload, download and generation-2 reuse all reached success;
the frozen total remained `69,206,016` bytes and nine partial callback events
were captured. Object size/ETag and downloaded MD5 checks passed. Both exact
test objects returned DELETE 204 and then HEAD 404, and both local payload
directories were removed. Progress evidence contains no bucket, OBS URI,
credential or `/sg2` path. The retained evidence is:

```text
/sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow-wgs/runtime/cce-evidence/T200-obs-sdk-canary/real-canary-20260904T155225Z-84e2670a
```

The canary exposed two SDK 3.26.6 compatibility defects in the adapter. The
SDK notifier can clear its callback before queued progress updates drain, and
`GetObjectMetadataResponse` does not expose custom metadata. The CCE source now
installs a queue-draining notifier and, when metadata is absent, validates a
strict 32-hex single-part ETag after validating object size. Two new regression
tests pass locally and against the deployed node200 adapter. The SDK credential
comes from the existing CCE test Secret, remains mode 0600 on node200, and is
not copied to BS10610, Git, evidence or logs. Production obsutil configuration
was not modified.

A subsequent T201 canary uploaded one real paired-FASTQ validation sample
without starting Airflow, CCE or WGS analysis. The two files totaled
`14,486,007,978` bytes (`13.4911 GiB`) and completed in `152.862` seconds at
`90.38 MiB/s` aggregate. R1 averaged `49.49 MiB/s`; R2 averaged
`47.26 MiB/s`. The frozen denominator did not change. There were 116 safe
progress snapshots, with 68 distinct partial R1 values, 79 partial R2 values
and 111 aggregate partial values.

The real file sizes exposed two additional adapter gaps. More-than-5-GiB
inputs now use resumable 64 MiB multipart upload with four SDK workers,
checkpointing and CRC64. The progress notifier now coalesces burst increments
instead of queueing every SDK chunk, preventing a 30-second shutdown timeout.
Focused adapter tests pass 8/8. Source size and mtime were unchanged, remote
size/CRC64 matched, and both exact objects returned DELETE 204 then HEAD 404.
The retained private evidence is:

```text
/sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow-wgs/runtime/cce-evidence/T201-real-fastq-upload/real-fastq-20260904T164733Z-60498b83
```

This proves per-file and aggregate callback data, not the complete frontend
projection. Contract v2 and the runtime adapter remain disabled; the next gate
is one separately approved Airflow-integrated Step1 canary.

The focused local adapter suite passed 8 tests. A complete local cce-pipeline
collection was also attempted but stopped during collection because the
Windows environment does not provide `kubernetes.config`; the previously
accepted Linux full-suite baseline remains 214 passed. The deployed adapter
itself was exercised by the successful real 13.49 GiB transfer.

### Verification

| Check | Result |
|---|---|
| backend full pytest | `352 passed, 1 skipped` |
| runtime script pytest | `61 passed` |
| `bio_wgs` DAG unittest | `14 passed` |
| frontend Vitest | `49 passed` |
| frontend typecheck/build | passed |
| cce-pipeline full pytest | `214 passed` |
| Compose config | passed |
| frontend and backend health | HTTP 200 / `ok` |
| workspace API | HTTP 200; warm median `90.4 ms` |
| Rules paging | HTTP 200; `1/208`, limit 1 |
| SFS Cloud Eye | healthy; fresh numeric metrics imported from node200 |
| real OBS SDK canary | 2 files / 69,206,016 bytes; upload, download, reuse and cleanup passed |
| OBS SDK adapter regressions | `6 passed` locally; `2 passed` on node200 |
| real paired-FASTQ upload | 13.4911 GiB in 152.862 s; 90.38 MiB/s aggregate |
| real FASTQ progress | 116 snapshots; per-file and aggregate partial progress verified |
| real FASTQ integrity/cleanup | source unchanged; remote CRC64 passed; DELETE 204 then HEAD 404 |
| OBS SDK adapter focused tests | `8 passed` after multipart and callback coalescing fixes |
| network | `192.168.199.0/24`, gateway `192.168.199.1` |

Candidate wheel SHA256:

```text
executor 98ab02fc45247c8cde1b8cde81e5cbb211aff3f82fc3649a503bb5dbca269341
cce      968a3b1a7e2094f82dbfba91b4718ec34bf49274aa348eb939a4f2db0bc3b3d4
```

### Incident And Storage

The first release extraction was blocked by the user's NFS write quota. Only
unmounted airflow-WGS development/build cache was targeted; roughly 1.3 GiB
was freed from `dev`. Current release files, env, databases, evidence, results
and Docker volumes were preserved. Root-owned residual cache was left in
place.

During the retried migration, `docker compose run biodemo-migrate` recreated
the PostgreSQL container because the candidate Compose service hash differed.
This was unintended. The named `airflow-wgs_postgres-data` volume was never
removed, the run inventory remained intact, migration `20260904_0014`
completed, and PostgreSQL is healthy. Subsequent recreation used `--no-deps`.

Validated backups are under:

```text
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/T194-T200-contract-v2-20260904T132157Z
airflow.dump  5b916f2ca95c68a5bc9775aeee794ff57becbef43c5de13f3f219e157cfa7612
biodemo.dump  369f0cef6810f9ee32fff435dbbb2f16cad81e2b320dbccbe36b10d000d98d6a
```

### Remaining Gates

- Verify the actual CCE Master service account, then apply the namespace-only
  Lease RBAC and test Lease CRUD.
- Integrate the now-passing standalone SDK canary with one contract-v2
  Step1/Step5 execution before selecting the SDK adapter as the runtime default.
- Run a controlled WGS batch before selecting the staged CCE image.
- Keep dynamic slot scaling disabled; Cloud Eye is validation and alerting
  evidence only.

### Rollback

Keep all execution gates false, repoint `current` to the T192 release and
recreate only affected application services with `--no-deps`. Migration 0014
is additive and may remain. Do not delete or downgrade PostgreSQL/Redis
volumes, transfer spools, evidence, results or Kubernetes Leases.

## 2026-09-04 - Codex - T192 production Docker cleanup

### Outcome

The `.96` Docker inventory proved there is one WGS Compose project,
`airflow-wgs`; its production topology requires 11 running service containers.
Cleanup therefore retained the whole production stack and exactly one current
Airflow, backend and frontend application image version. Obsolete WGS image
tags, exact unused test/build images and the exited obsolete
`airflow-wgs-biodemo-migrate-1` one-shot container were removed individually.
No prune command was used.

PostgreSQL, Redis, every Docker volume, all current service containers, release
files, analysis data, unrelated workloads and the external Docker network were
preserved. Final inspection found no dangling images. Compose still reports 11
running WGS services; `nipt_analysis_test_net` remains `192.168.199.0/24` with
gateway `192.168.199.1`, and the production frontend returns HTTP 200.

Rollback images were intentionally removed at the operator's request. A prior
release now requires rebuilding its image from the preserved release source
before rollback; current containers are unaffected while running.

## 2026-09-04 - Codex - T191 frontend login recovery

### Outcome

The production login failure was an nginx upstream failure, not invalid user
credentials. After T190 recreated backend, frontend-nginx still sent API
requests to the previous backend address `192.168.199.8:8000`; nginx logged
`connect() failed (111: Connection refused)` and returned 502. Docker DNS and
the backend container both reported the current address `192.168.199.4`.

The explicit WGS production Compose configuration passed. Only
`airflow-wgs-frontend-nginx-1` was restarted so nginx resolved the current
backend. A protected server-local admin login then returned 200 and the same
cookie session returned `/api/auth/me` 200 with username/role admin. No
password, cookie or token was written to output.

No image, application code, account, database, backend, Airflow, scanner,
volume, CCE workload or Docker network was changed. The public endpoint remains
`172.17.61.96:12959`. Future operations that recreate backend must also reload
or restart frontend-nginx until nginx upstream DNS is made dynamic.

## 2026-09-04 - Codex - T190 T7 source-name correction

### Outcome

The operator confirmed the source truth after the initial diagnosis:
`2224th_20260902A_E250197512` and `2225th_20260902B_E250197501` are the newest
directories, but their numeric prefixes should have been 2234/2235.
`2233th_20260901B_E250197502` is historical. Chip number is therefore not a
safe chronological cursor.

The temporary numeric-head reconciliation was removed, while the original
marker/bootstrap protection remains. The application neither renames the
source directories nor displays synthetic 2234/2235 identities. The exact
2233 intake row created by the temporary rule was deleted; its source
directory, successful AnalysisRun `WGS_20260902_181846_20A4D2`, Airflow state
and results were not changed.

One shared `wgs_params_match_batch` function remains as a behavior-preserving
cleanup of the automatic-dispatch duplicate mapping. It accepts the explicit
sequencing/analysis batch and legacy `WGS_<batch>_...` batch number forms.

### Verification

| Check | Result |
|---|---|
| corrected focused intake/dispatch suite | `22 passed` |
| corrected complete `.96` backend suite | `341 passed, 1 skipped` |
| production scan | `created=0`, `updated=2`, `submitted=0` |
| production intake | 2224 and 2225 only |
| `20260901B` run count | one; status `success` |
| network | `192.168.199.0/24`, gateway `192.168.199.1` |
| published endpoint | `172.17.61.96:12959` only |

Production points to
`/data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t190-intake-name-correction-r2`.
Only backend and `wgs-intake-scanner` were recreated. PostgreSQL, Redis,
Airflow, frontend, volumes, CCE workloads and WGS analysis records were not
recreated. No Git commit was created.

One candidate-copy command initially failed because PowerShell expanded remote
shell variables; the corrected stdin-to-Bash form succeeded without mutation.
The first Compose preflight omitted the required production env file and
stopped before switching `current`; the corrected command explicitly used
`/data/airflow-WGS/env/production.env`. An unauthenticated backend health probe
returned the expected 401, and two transient SSH handshakes aborted before the
subsequent verification succeeded.

Rollback is to repoint `current` to T189 and recreate backend plus scanner with
the explicit production Compose file and env file. Do not recreate or delete
the already successful `20260901B` WGS run.

## 2026-09-04 - Codex - T189 Step5 recovery and exact batch QC

### Outcome

`20260902B` is repaired in its original analysis and DagRun:
`WGS_20260903_200310_37E27D` / `WGS_20260903_200310_37E27D-a1`.
Step1-Step4 and retained Master `cce-master-44815ec87b04c2020d77` were not
rerun. Only Step5 and the downstream tail were recovered. Airflow now has one
exact DagRun, all 24 task instances are success, and the terminal time is
2026-09-04 13:23:06 CST. The business run is success/progress 100 with 8/8
samples and 481/481 Rule states successful.

The Step5 deadlock was caused by requiring a local manifest that the Step5
script itself retrieves from OBS. The runtime now launches first, freezes the
manifest-backed plan when visible, preserves retry generation and terminal
transfer detail, and validates completion against exact planned targets. The
recovered plan is 26 files / 447124566023 bytes; `DOWNLOAD_VERIFIED` and
`MATERIALIZED` both report PASS. The same-attempt backend projection now
accepts only an explicit newer retry generation over stale failure and leaves
ordinary terminal monotonicity intact.

The batch contains one aggregate QCstat plus eight per-sample QCstat files.
Both Samples and Files now use one shared selector for the exact aggregate
`07_QC/WGS_20260902B_T7Hg38V4.1.1.QCstat.tsv`. The live privacy-safe projection
returns 8 manifest rows, 8 sample matrices with safe metrics, and QC counts
`pass=2`, `warn=6`; the six warnings are non-empty exception text, not missing
data. Files exposes one `wgs_qcstat` item and no server absolute path.

### Verification

| Check | Result |
|---|---|
| targeted QC production-shape tests | red on aggregate suppression/free-text unknown, then `2 passed` |
| `.96` complete backend suite | `341 passed, 1 skipped, 2 warnings` |
| `.96` runtime script suite | `57 passed, 2 warnings` |
| live Airflow | one exact DagRun; `success=24`; no failed/running task |
| live biodemo | run success; samples `8/8`; Rules `481/481` |
| live API | sample workflow `success=8`; QC `pass=2,warn=6`; safe metrics `8/8` |
| runtime gate | local/release/node200 SHA256 `e3e6f223e9e8f20ceb796a5de57aa667f6c64f8d862f6f693f7012f6f931302f` |
| node200 worker | no matching active `wgs_runtime_gate.py` process |
| deployment health | backend health OK; only backend recreated after QC fix |
| network | `192.168.199.0/24`, gateway `192.168.199.1`; only `172.17.61.96:12959` published |

The first complete-backend verification omitted the `/config` mount and
produced eight environment-only missing-catalog failures; the correctly
mounted rerun passed. One SSH handshake and one node200 request-root lookup
failed transiently before successful exact retries. Later verification
false-starts used an obsolete admin password, expected `curl` in the minimal
backend image, queried a nonexistent `analysis_run.batch` column, and omitted
the required SSH config for `wgs-node200`; none mutated runtime state. The
correct internal-token/API, `params_json`, and `ssh -F` checks all passed.

Production points to
`/data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t189-step5-manifest-r4`.
PostgreSQL, Redis, Airflow services, volumes, CCE Master and the Docker network
were not recreated. No Git commit was created, per operator request.

Rollback is to repoint `current` to T188 and recreate backend plus the runtime
consumers only. Do not roll back the now-correct successful business/Airflow
records, delete the verified batch payload, or recreate the retained Master.

## 2026-09-04 - Codex - T188 Step6 barrier and guarded automatic intake

### Candidate outcome

The WGS DAG now has a real terminal barrier after asynchronous Step6. The new
`wait_step6_materialize` sensor consumes the exact runtime marker before
`finalize_run`, while finalization itself rejects stale attempts, wrong stages,
wrong identities and non-success terminal states.

The run-detail data contract was consolidated in the backend: a privacy-safe
projection reads the frozen sampleinfo, derives a sample analysis matrix from
Sample/RuleState/QCstat, restricts files and logs to registered artifacts and
keeps opaque log keys as the read credential. Names, hospitals, raw sampleinfo
and absolute SFS paths are not returned. New transfers use a pre-transfer
immutable plan so totals cannot grow during upload/download; existing
unplanned transfers remain explicitly legacy estimates.

The T7 scanner has a new authenticated dispatch phase. It first consults the
business database and reconciles deterministic Airflow DagRun identity. A
ready batch already represented by a manual or automatic run in any state is
linked and skipped; failed/cancelled runs are not silently retried. A mandatory
activation timestamp makes all earlier ready discoveries baseline-only.

### Candidate verification

```text
.96 backend candidate: 337 passed, 1 skipped
.96 backend final read-only release: 338 passed
.96 runtime scripts: 47 passed
.96 DAG/deployment: 21 passed
.96 frontend: 47 passed
.96 frontend production build: passed
compose config: passed
network: 192.168.199.0/24, gateway 192.168.199.1
published port: 172.17.61.96:12959 only
```

### Production outcome

Production now points to
`/data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t188-step6-projection-auto-r1`.
The final frontend asset is `index-DZXT7pAH.js`; the node200 runtime gate SHA256
is `2265e99f037e5b6fd32388753f67570ebedc2e9adad1d7c2e3ad81fef81f7794`.
Automatic dispatch was enabled with activation watermark
`2026-09-03T21:36:11Z`. Two scans each examined two ready records, associated
both with their existing manual AnalysisRuns and submitted zero new runs.
AnalysisRun and WGS DagRun counts remained `4` and `10`.

Both exact Step6 success markers were rechecked before recovery.
`20260825A` attempt 7 and `20260902A` attempt 1 completed the newly introduced
`wait_step6_materialize`, then finalized successfully in their original
DagRuns. Their Step6 start tasks remained try 1; no Step1-Step6 stage was
restarted.

The first production recreate exposed a release-permission defect: Airflow
could not initially read the newly mounted DAG, so the active `20260902B`
sensor was marked failed and the all-done cleanup drained its observer. The
CCE Master remained running and unchanged. Read permission was added only to
the application code/config directories; the exact same DagRun tail was
cleared, the DAG reparsed as active/unpaused, the Step3 sensor returned to
`up_for_reschedule`, and the observer was reactivated healthy. Step1, Step2 and
the Step3 start task remain try 1. No replacement Master, AnalysisRun or DagRun
was created.

The production health endpoint is OK. The external network remains
`192.168.199.0/24` with gateway `192.168.199.1`; only
`172.17.61.96:12959` is host-published. PostgreSQL, Redis, their volumes and the
network were not recreated. Backups are under
`/data/airflow-WGS/backups/T188-step6-projection-auto-20260904`.

A redundant final frontend test-image build attempted `npm ci` offline and
failed before running tests because the dependency layer was unavailable. This
does not replace the successful candidate evidence above: all 47 tests passed,
and the final type-corrected production build produced the deployed asset.
No Git commit was created, per operator request.

## 2026-09-04 - Codex - T187 20260902B reset and fresh resubmission

### Outcome and current live state

The operator explicitly waived backups and authorized an exact reset of test
batch `20260902B`. The old run `WGS_20260903_111829_1D58E1`, its seven failed
DagRuns, biodemo dependencies, runner identity, generated sampleinfo and exact
local/SFS batch paths were removed after inactivity checks. Frozen Step0 was
attempted first but failed before mutation on missing orphan worker metadata and
reset tooling, so the exact paths were removed manually. OBS FASTQ, other
batches, PostgreSQL/Redis volumes and the Docker network were untouched.

A first clean preview exposed the real selection defect: 11 family rows became
only two singleton samples because three expanded family members had blank
sequencing-batch values. Production Samplelists prove WGS26080571,
WGS26080572 and WGS26080575 belong to `20260902A`. Updating only those three
rows through the existing global pending recovery contract produced a frozen
selector dry run of 8 kept samples, 3 pending samples and 16 readable FASTQs.

The retained fresh run is `WGS_20260903_200310_37E27D-a1`. Sampleinfo and the
analysis directory were regenerated from scratch; the final database sample
projection contains exactly 8 samples. Both review gates are approved. Airflow
waited without stealing the one-slot OBS lease, then acquired it after the
previous lease expired. Step1 reused the existing FASTQ objects and succeeded,
Step2 succeeded, and Step3 now monitors active Master Job
`cce-master-44815ec87b04c2020d77` in `snakemake-ns`.

Final verification matched the fresh analysis, attempt 1 and stage in the
node200 request/status files and found zero old-analysis runtime paths. The
backend health endpoint returns `ok`; the Docker network remains
`192.168.199.0/24` with gateway `192.168.199.1`, and only
`172.17.61.96:12959` is published. No Git commit was created. This closes the
reset/resubmission task, not the still-running biological workflow.

## 2026-09-04 - Codex - T186 approval sensor transport recovery

### Diagnosis and implementation

- `20260902B` attempt 6 did not fail in Rule monitoring and did not reach
  Step1. Sampleinfo and analysis preparation both succeeded.
- `wait_wgs_execution_approval` failed on
  `socket.gaierror: Temporary failure in name resolution` while resolving the
  internal `backend` service. The execution approval had not been issued.
- `stage_ready` already rescheduled transport-only failures, but the two
  submission approval sensors did not. Both paths now use the same helper:
  transport loss returns not-ready, while HTTP and contract errors still fail.
- The regression test was observed failing for both approval gates before the
  implementation, then the focused pair and all 14 `bio_wgs` unit tests passed
  in the `.96` Airflow image.

### Production outcome

The immutable release is
`/data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t186-approval-sensor-dns-r1`.
Only the three Airflow services were recreated. One initial invocation omitted
`-f docker-compose.wgs.yaml`; the resulting DNS check caught the three Airflow
containers on an unintended empty `172.30.10.0/24` network before any WGS task
advanced. They were immediately recreated with the production Compose file on
`nipt_analysis_test_net`, and the now-empty accidental network was removed.

Final verification found no DAG import errors. Airflow resolves backend,
PostgreSQL and Redis; health returns `ok`; the network remains
`192.168.199.0/24` and only `172.17.61.96:12959` is published. `20260825A`
attempt 7 remains in Step3 with its observer active/healthy and 72 Rule rows.
`20260902B` attempt 6 remains failed at the old execution approval wait with no
approval, upload, CCE Master, observer or Rule rows. The operator owns recovery
and the later execution confirmation.

Rollback is to repoint `current` to T185 and recreate only the Airflow DAG
services. No database, node200 runner, OBS, SFS or CCE rollback is required.

## 2026-09-04 - Codex - T185 retried Rule monitoring repair

### Outcome

- The warning was not caused by a missing or wrong evidence path. Both JSONL
  files and both mirrored `analysis.log` files existed and were readable.
- The installed schema-1 logger writes `attempt-1` for each fresh Master. The
  observer now uses the exact frozen `run_label` as that schema's execution
  identity and stores accepted events under the binding's Airflow attempt.
  The newer `rule-event.v1` contract still requires exact attempt equality.
- Run detail no longer falls back to an observer row from an older attempt.
- Existing evidence was replayed from the unchanged cursor boundary. No WGS
  Rule, CCE Job, transfer or Airflow task was rerun.

### Verification and deployment

```text
TDD red: schema-1 attempt-1 on binding attempt 7 produced errors=1/events=0
TDD red: current attempt 2 returned the old attempt-1 observer warning
focused .96 Docker: 70 passed
isolated complete .96 Docker backend suite: 329 passed, 1 skipped
20260825A attempt 7: observer healthy; 66 events; 20 Rule instances after first recovery poll
20260902B attempt 4: observer stopped/healthy after drain; 20 events; 6 Rule instances
release: /data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t185-rule-attempt-binding-r1
health: http://172.17.61.96:12959/api/health -> {"status":"ok"}
network: nipt_analysis_test_net 192.168.199.0/24; only 172.17.61.96:12959 published
```

Rollback is to repoint `current` to the prior release and recreate backend,
observer and then restart frontend-nginx. Database rollback is not required;
the ingested raw events remain tied to their exact analysis and binding attempt.

## 2026-09-04 - Codex - T184 20260902B clean prepare recovery

### Outcome

- Attempt 5's generated batch directory, including `sampleinfo.tsv`, was moved
  recoverably to
  `/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/.rerun-archive/20260903T171610Z/attempt-5/`.
  The refreshed source `sampleinfo/*.sampleinfo.txt` was retained.
- The root cause was a shared-NFS visibility race: node200 had already published
  a successful prepare status, while `.96` briefly could not see the final
  table. The backend now reports this one condition as an authenticated
  `ready=false`, `artifact_pending=true` transition instead of HTTP 500.
- Attempt 6 regenerated the project directory successfully and is stopped at
  `execution_review`. It contains two current WGS-selected samples from the
  11-row source table; nine rows remain pending under the current WGS logic.
- Execution approval is deliberately absent. Step1/Step2 did not start, the OBS
  lease is empty and there is no CCE Master.

### Verification and deployment

```text
TDD red: ValueError WGS prepare did not publish final sampleinfo.tsv
focused green: 1 passed
backend full on .96 Docker: 328 passed
attempt 6 prepare tasks: prepare_wgs_sampleinfo, wait_prepare_wgs_sampleinfo,
  prepare_wgs_analysis and wait_prepare_wgs_analysis all success/try 1
source/final sample rows: 11 / 2
final sample IDs: WGS26080569, WGS26080573
release: /data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t184-prepare-nfs-race-r1
backup: /data/airflow-WGS/backups/T184-prepare-nfs-race-20260903T172446Z
biodemo dump SHA256: 010962e0da461ddfe16156c6a44a996f6ec267ce2c33adb4d539a7184058ce89
airflow dump SHA256: d8de023653b24e9c250de3dd3a7fa6d20491330fdef7e7ef0a3251317e02152f
health: container-local and 172.17.61.96:12959/api/health both returned ok
network: nipt_analysis_test_net 192.168.199.0/24, gateway 192.168.199.1
```

The first release script stopped before switching because it attempted to
change root-owned frontend test-cache permissions. The first image build also
stopped before switching because the configured registry mirror DNS was
unavailable. Production remained on T183 during both failures. The deployed
backend reuses the already-tested T183 dependency image and bind-mounts the T184
source read-only at `/app`; only backend was recreated.

Rollback is to restore `production.env.before` from the T184 backup, repoint
`current` to T183 and recreate backend only. Do not restore either database
unless an independently verified database rollback is required, and do not
delete the fixed network, volumes, source sampleinfo or recoverable archive.

## 2026-09-03 - Codex - T183 20260902A Rule monitoring recovery

### Outcome

- The current CCE Master was preserved. The original DagRun has
  `submit_step2_master=success/try 1`, `start_step3_monitor=success/try 4`, and
  an active/rescheduling `wait_step3_analysis`; observer state is
  `active/healthy`.
- Rule JSONL was already emitted and bridged. The missing UI data came from a
  transient Step3 control-plane failure plus the logger/business identifier
  difference `WGS26080568-WGS` versus `WGS26080568`.
- The observer now uses only unique registered `sample_id`/`data_id` aliases.
  Current Rules resolve to sample `WGS26080568` and family `JX26G00230117`.
- Every Rule receives the registered opaque Master analysis-log key and the UI
  opens that log without exposing a filesystem path.

### Verification and deployment

```text
DAG TDD: new request-visibility test failed before fix; focused suite 13 passed after fix
backend TDD: nonfailed Rule lacked analysis_log_key before fix; focused test passed after fix
backend full: 327 passed
frontend full: 11 files / 47 tests passed
frontend build: passed, index-C4rdMP4f.js
production API: health OK; Rules 19/19 sample-linked, family-linked and log-linked
production log: opaque index present; the latest 200-line analysis.log read succeeds without path exposure
release: /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t183-rule-log-link-r1
backup: /data/airflow-WGS/backups/20260903T2120-t182
network: nipt_analysis_test_net 192.168.199.0/24, gateway 192.168.199.1
published platform port: 172.17.61.96:12959 only
```

The first backend full-suite command imported the image's `/app` before the
read-only candidate tree and produced three false failures against old code.
Rerunning with `PYTHONPATH=/workspace/backend` exercised the candidate and
passed all 327 tests. No Git commit was created. Rollback is limited to the
saved production env, T182 release pointer and recreation of the same affected
services; do not restore databases unless an independently verified database
rollback is required.

Post-deploy focused backend verification passed 60 tests. A second attempt to
rerun the DAG pytest suite directly from the deployed images was not usable:
the Airflow image's selected Snakemake Python has no pytest, while the backend
test image has no Airflow package. The candidate DAG suite had already passed
13 tests before deployment, and the deployed scheduler independently imports
the expected unpaused `bio_wgs` DAG.

## 2026-09-03 - Codex - T179 transfer units and resource-panel repair

### Outcome

- Byte progress in Current Progress, Run Tracker and the WGS stage graph now
  uses the shared binary unit formatter; raw multi-digit byte counters are no
  longer rendered in those views.
- Analysis Node Health now shows CPU, memory and load bars. Load is normalized
  against the newly collected logical CPU count, the raw 1/5/15 values remain
  right-aligned, and the bar turns green below 70%, amber from 70% to below
  100%, and red at or above 100%.
- Client connections is displayed as one spaced row with its value on the
  right. The SFS I/O graph now has an auto-scaled max/mid/zero Y axis.
- Transfer aggregation gives an active child priority over an old failed child,
  so a multi-command Step1/Step5 transfer is not internally labelled failed
  while bytes are still advancing.

### Verification and production state

```text
TDD red: frontend 5 failed / 13 passed; Python 2 failed / 42 passed
TDD green focused: frontend 18 passed; Python 44 passed
.96 Docker frontend full: 46 passed
.96 Docker frontend build: passed (index-DokJ1IE2.js)
.96 Docker Python full: 374 passed, 1 skipped
node metrics: node-96 and node-97 healthy; logical_cpu_count=128 for both
frontend smoke: HTTP 200
release: /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t179-progress-resource-r1
frontend image: airflow-demo/frontend:t179-progress-resource
node200 gate SHA256: b22edb1e91106a305480a611fe93014c729ae3b192a299f1d8236cff316827ef
network: nipt_analysis_test_net 192.168.199.0/24, gateway 192.168.199.1
published host port: 172.17.61.96:12959 only
```

The first full Python test invocation mounted only the staging tree and failed
six catalog tests because `/workspace/config/wgs_*.yaml` was absent. After the
unchanged production config was mounted into the test tree, the complete suite
passed. During deployment the new node probe initially restarted because the
candidate release parent/group permissions blocked `/app`; group read/execute
was restored and the probe then reported both nodes healthy.

`20260902B` was not missing its upload: it had waited for the one-slot OBS pool,
then started Step1. At the final check its outer status was `running` with
340118460167/510102528323 bytes transferred. Its already-running old worker was
not restarted, so that attempt may retain the obsolete nested child state until
completion; new workers use the corrected aggregator.

Rollback is limited to restoring the previous runner backup
`/home/hanjj/.config/airflow-wgs/wgs_runtime_gate.py.before-t179-20260903`,
repointing `current` to T177 and restoring the backed-up production env before
recreating the same three services. Do not delete databases, volumes, OBS/SFS
data or Airflow task state. No Git commit was created.

## 2026-09-03 - Codex - T178 20260825A analysis-directory reset

### 原因与范围

- `WGS_20260903_062828_0858DC-a4`的sampleinfo阶段成功；真正失败点是
  `prepare_wgs_analysis`拒绝覆盖既有目录。
- 精确目标为
  `/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/WGS_20260825A_T7Hg38V4.1.1`，
  解析路径一致、不是挂载点、约27 MiB；清理前确认批次锁、Master Job和Pod均不存在。

### 操作与恢复

- 先归档再删除唯一目标目录；sampleinfo、Airflow/biodemo失败记录、OBS和SFS未删除。
- 备份：`/data/airflow-WGS/backups/T178-20260825A-analysis-reset-20260903T111511Z`
- archive SHA256：`68f78e3c137ba0a66821fffccc03c98aa1d8f5752f7d6e1cf5521cf6efc3f1a9`
- 恢复时必须先确保该批次无活动任务，再从归档解包；不得覆盖新生成目录。
- 用户在清理期间提交了独立的`20260902A`运行`WGS_20260903_111456_397777-a1`；其prepare
  成功并进入Step1，不使用被删除的`20260825A`目录。Codex未提交、批准或取消该运行。

## 2026-09-03 - Codex - T177 prepare-stage status routing repair

### 失败证据

- `WGS_20260903_062828_0858DC-a2`的`prepare_wgs_sampleinfo`已成功注册；node200状态文件
  是`success`，更新时间`2026-09-03T08:29:28Z`。
- 预期sampleinfo文件存在，共4行（表头加3个样本）。未读取或记录样本隐私字段。
- `wait_prepare_wgs_sampleinfo`第一次查询内部状态接口即收到HTTP 500。后端堆栈指向
  `wgs_observer.py`并报`ValueError: unsupported runtime stage sync`。
- Step1、OBS和CCE均未启动；`release_leases`失败是上游失败后的汇总结果，不是根因。

### 修复与验证

- 将prepare状态阶段与Step1/Step3-Step7 artifact阶段分别定义为唯一集合，再用union做
  接口允许检查，删除函数内重复的阶段集合。
- prepare阶段只读取并验证自己的status；`prepare_sampleinfo`成功后导入安全样本投影，
  `prepare_analysis`仍允许读取冻结binding并导入最终样本。

```text
TDD red: 4 failures, all reproduced unsupported runtime stage sync
TDD green: focused 4 passed
.96 Docker full backend: 326 passed
attempt 2: preserved failed; no task clearing or retry
side effects: no attempt 3, OBS transfer or CCE workload
deployment: /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t177-prepare-stage-sync-r1
backend image: airflow-demo/backend:t177-prepare-stage-sync
backup: /data/airflow-WGS/backups/T177-prepare-stage-sync-20260903T084951+0000
airflow dump SHA256: a94f15108d6364213deee630f87fdee21a29168735a42d287a93e3c8ebf43dcd
biodemo dump SHA256: 14f66ffac044f271d3b61eee034e872ace730359678769bbea2c0747abe4cd3d
smoke: login/capabilities/release/run-list all HTTP 200; WGS runs/attempts remain 2/3
network: nipt_analysis_test_net 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 published
```

### 恢复边界

- 修复部署后由operator再次提交同一批次会创建attempt 3。不要恢复或覆盖attempt 2证据。
- 回滚只切换到T176 release并重建backend；不得清理数据库、Airflow metadata、OBS/SFS、
  volume或固定Docker网络。

## 2026-09-03 - Codex - T176 failed resubmission and Submit refresh repair

### 根因与修复

- `20260825A`再次提交时，后端复用了同一个terminal failed AnalysisRun，并把页面阶段
  改回`preparing_sampleinfo`；但确定性的attempt-1 DagRun已经failed，Airflow幂等接口
  没有启动新任务。前端轮询又只判断`submission_phase`，因此一直显示Preparing。
- 后端现在对active重复请求保持幂等，对success重复请求明确拒绝；对
  `failed/cancelled/unknown_interrupted`使用同一AnalysisRun创建新attempt和
  `<analysis_id>-a<attempt>` DagRun，并清理旧终态、错误和进度字段。
- 前端每5秒轮询保持不变，但在终态失败时立即退出Preparing页面，展示后端错误摘要和
  Run Detail入口。
- 未提交任何生产批次；旧attempt 1及其证据保持不变。
- 已切换`.96`到
  `/data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t176-submit-retry-refresh-r1`，
  backend/frontend镜像分别为`airflow-demo/backend:t176-submit-refresh`和
  `airflow-demo/frontend:t176-submit-refresh`；仅重建这两个服务。

### 验证

```text
TDD red: backend expected attempt 2 but received attempt 1
TDD red: frontend could not find Sample information preparation failed
TDD green: backend focused 1 passed; frontend focused 1 passed
.96 Docker backend: 321 passed, 1 skipped
.96 Docker frontend: 10 files / 44 tests passed
.96 TypeScript/Vite build: passed
Compose config: passed
network guard: nipt_analysis_test_net 192.168.199.0/24, gateway 192.168.199.1
side effects: no new AnalysisRun attempt, DagRun, OBS transfer or CCE job
production API: login/capabilities/release/run-list 200; WGS runs/attempts remain 2/2
backup: /data/airflow-WGS/backups/T176-submit-retry-refresh-20260903T082055+0000
airflow dump SHA256: 2664549667b3bc6ae27c71790a7449fec684c99b67217e66e4e776e745e5be3d
biodemo dump SHA256: 7e7b5bcbe580d000955648448a287aee38b73f27735f7547d90c2a3f136beaac
```

### 当前logger合同

- 已核对当前Master runner：正式`cloud_wgs_all`由
  `/opt/cce-pipeline/scripts/run_cce_master_job.sh`加入`--logger rule-status`。
  WGS profile不应重复添加。下一次新attempt只需验证实际Rule JSONL产物，不再把
  “profile没有logger参数”当成阻塞。

### 回滚

应用回滚仅切换`current`到T175并重建backend/frontend；不得删除旧attempt、数据库、
OBS/SFS、volume或固定Docker网络。

## 2026-09-03 - Codex - T175 resource bars and SFS I/O chart

### 已完成

- Analysis Node Health改为CPU、内存两条可访问的占用条，保留load 1/5/15和96/97切换。
- Cloud Resources根据同一Cloud Eye快照中的`capacity_used_bytes`与
  `capacity_used_percent`显示已用/推导总容量；字段不全时只显示可靠值。
- Node和SFS的Updated移到卡片标题最右侧，字体与副标题一致。
- 删除与Run Tracker重复的Workflow Activity，原位置使用数据库已限制为60点的SFS历史
  绘制读/写带宽趋势，并显示当前IOPS；未增加API、数据库表、采集字段或采集频率。
- 用户要求的前序累计改动已先提交为`5ae0a58`；T175前端改动保持未提交。
- 已切换`.96`到
  `/data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t175-resource-graphs-r1`，
  前端镜像`airflow-demo/frontend:t175-resource-graphs`。只重建`frontend-nginx`。

### 验证

```text
TDD red: focused test failed because utilization progressbars were absent and Workflow Activity remained
TDD green: focused resource panel tests 2 passed
.96 Node Docker frontend: 10 files / 43 tests passed
.96 Node Docker TypeScript/Vite build: passed
production HTTP: fixed-address root probe passed
production assets: SFS I/O present; Workflow Activity absent
preserved: PostgreSQL/Redis IDs, Airflow/scanner/observer/metrics services, volumes and network
API/database/collector: unchanged
```

### 仍需完成

- operator刷新页面检查三个等宽卡片、右侧更新时间和SFS曲线；T175不代替用户提交WGS批次。

### 回滚

回滚只需恢复前一frontend image并把`current`切回T174 release，然后只重建
`frontend-nginx`。不得删除数据库、运行记录、OBS/SFS内容或固定Docker网络。

## 2026-09-03 - Codex - T174 forward-only WGS evidence repair

### 已完成

- 按用户决定不回填历史run。后端统一负责公开Batch投影，Run Tracker、Run Detail和
  Samples只消费同一结果；Samples搜索显式支持sample、family、batch、project和run ID。
- final sampleinfo与Snakemake完整日志共用冻结binding路径解析器，修正此前把分析目录
  错误映射到runtime root的问题；前端不复制路径或批次解析规则。
- Step3终态没有Rule JSONL时标记`monitoring_health=degraded`，不再显示healthy，也不从
  历史analysis.log伪造Rule事件。
- `WGS_20260903_062828_0858DC-a1`的Airflow任务日志证明：SSH认证成功后node200立即退出，
  旧gate未分发`prepare_sampleinfo`。该attempt未生成sampleinfo、未进入OBS/CCE。
- node200旧gate已保留时间戳备份；通过runner测试后原子安装SHA256 `b8d9765...`。
  安全构造检查确认现在调用WGS `prepare_wgs_batch.py sampleinfo`，输出根固定为
  `/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical`。
- Airflow失败摘要同时保留远端stdout和SSH stderr，后续不会再只显示`Connection closed`。
- 已切换`.96`当前release到
  `/data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t174-forward-evidence-r1`，
  前端镜像为`airflow-demo/frontend:t174-forward-evidence`。只重建应用服务，PostgreSQL、
  Redis容器身份和运行时间均保持不变。
- 认证后生产smoke确认capabilities、release、project、run搜索和详情接口均为200；
  `20260825A`搜索及详情均返回公开Batch `20260825A`。唯一`bio_wgs`仍为23任务且未暂停。

### 验证

```text
.96 Docker backend: 320 passed, 1 skipped
.96 Docker runner/evidence/progress: 42 passed
.96 isolated DAG unit tests: 11 passed
.96 Docker frontend: 10 files / 41 tests passed
.96 Docker TypeScript/Vite production build: passed
node200 gate: py_compile passed; installed SHA256 b8d9765...
production release: 20260903-wgs-4.1.1-6c98281-t174-forward-evidence-r1
production authenticated API smoke: passed
backup: /data/airflow-WGS/backups/T174-forward-evidence-20260903T070750+0000
database containers: preserved
side effects: no historical projection/backfill; no retry, OBS transfer or CCE submit
```

### 仍需完成

- 由operator重新提交新批次；检查sample/family入库、Rule JSONL和Snakemake log。若Master
  仍未生成Rule JSONL，应按真实监控降级处理并修正WGS logger启动合同，不能前端造数据。
- 本条当时关于“正式命令没有logger参数”的判断已被后续Master命令证据取代：当前
  `/opt/cce-pipeline/scripts/run_cce_master_job.sh`会为正式`cloud_wgs_all`加入
  `--logger rule-status`，WGS profile无需重复配置。新attempt仍需验证实际Rule JSONL产物。
- 用户随后明确授权先提交当前T168-T174累计改动；本条交接作为该checkpoint的一部分提交。

### 非破坏性失败记录

- 首次完整backend测试因staging未复制`config/wgs_projects.yaml`和`wgs_releases.yaml`
  出现5个FileNotFound；补齐测试夹具后通过。
- 一次测试断言补字段时产生IndentationError，修正后完整backend通过。
- frontend build曾因一次多文件scp把`SamplesPage.tsx`误放到staging `src/`根目录而失败；
  删除该staging-only副本后构建通过，仓库未出现重复页面实现。
- 更新node200 gate时第一次在Airflow容器内chmod root-owned临时文件失败；改由root仅修正
  该临时文件owner后完成传输，生产容器与volume未重建。

### 回滚

node200可恢复`/home/hanjj/.config/airflow-wgs/wgs_runtime_gate.py.before-t174-*`并复核SHA；
应用release回滚只切换`current`并重建应用服务。不得删除失败attempt、生产结果、OBS/SFS、
PostgreSQL/Redis volume或`nipt_analysis_test_net`。

## 2026-09-03 - Codex - T173 staged WGS/SFS production release

### 已完成

- 新提交入口拆成三阶段：WGS sampleinfo完成后查看安全样本/家系投影；确认Reference和
  固定resource set后生成analysis目录；再次确认后才放行Step1-Step6。两个等待点均为
  Airflow reschedule sensor，并有operator/admin RBAC、幂等和RunAction审计。
- 新主流程统一使用`<analysis_id>-a<attempt>`作为Airflow DagRun ID、WGS run ID和
  runtime/evidence身份；旧在途流程和维护DagRun不改名。
- 资源API/前端只展示SFS。Cloud Eye已为`hwybioinfo1`增加独立区域只读组，node200
  周期采集器签名查询返回200并写入共享SFS-only快照；AK/SK仍只在node200的0600文件。
- 核对正式WGS路径对`hanjj`可读、分析根可写、映射Git状态为0条漂移；未改用会产生
  大量tracked drift的`wgs-4.1.1-test`。
- 旧DagRun `manual__WGS_20260902_181846_20A4D2__a1`先达到success，18个旧任务、
  biodemo终态和运行证据均保留；随后原子切换到
  `/data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t173-staged-sfs-r1`。
- 只重建backend、frontend、scanner/observer、metrics和三个Airflow应用服务；PostgreSQL
  与Redis容器启动时间未变化，volume和外部网络未重建。生产DAG现为23任务、未暂停，
  execution/runtime=true、auto-dispatch=false，尚未创建新的三阶段运行。

### 验证

```text
.96 Docker backend: 318 passed, 1 skipped
.96 Docker runner/SFS collector: 38 passed
.96 Docker frontend: 10 files / 40 tests passed
.96 Docker production frontend build: passed
isolated Airflow import: bio_wgs, 23 tasks, no import errors
SFS Cloud Eye: HTTP 200; sfs-turbo-clinical healthy; capacity used 13.86%
production legacy DagRun: success at 2026-09-03T03:08:46Z; all 18 tasks success
production HTTP: root=200; health=200; login/protected API set=200
production assets: three stage labels present; OBS Cloud Eye label absent
production state: AnalysisRun=1/active=0; bio_wgs DagRun=1/active=0
network: 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 published
backup: /data/airflow-WGS/backups/T173-staged-sfs-20260903T052418Z; both dump checksums passed
```

### 未完成及下一步

- 按用户要求未提交Git。第一个新的三阶段生产批次尚未由operator提交，因此canonical
  run ID只完成代码/测试验证，尚无新的真实运行证据；不得为验收自行创建批次。
- node200没有user systemd且PAM禁止`hanjj` crontab；机器重启后需再次运行
  `/home/hanjj/.config/airflow-wgs/start_sfs_cloud_eye_collector.sh`。

### 部署过程中的非破坏性失败

第一次发布脚本把健康探针请求发到`127.0.0.1:12959`，但Nginx按安全合同只绑定
`172.17.61.96:12959`，因此curl返回connection refused。服务实际已正常启动；中止该
等待循环后改用绑定地址复核，root与health均为200，无需回滚且未影响数据库或旧批次。

### 回滚

应用回滚时恢复备份中的`production.env`并把`current`切回T172 release，再只重建应用
服务；数据库仅在确认需要数据回滚时使用两套dump。SFS采集器停止或快照缺失只会让
资源卡degraded，不影响WGS。不得删除旧批次、OBS/SFS对象、PostgreSQL/Redis volume
或固定Docker网络。

## 2026-09-03 - Codex - T172 `.96` frontend request recovery

### 已完成

- 线上Nginx证据表明截图对应的capabilities/resources请求未到服务端，而同一轮其他
  API均为200。根因进一步收敛为Dashboard在capabilities完成前后重复发起
  `deployed`和`wgs`两轮首屏请求，叠加浏览器原生网络/响应体读取失败。
- 前端现在等待单一WGS能力稳定后只加载一次；公共API层仅对GET原生网络错误等待
  250 ms后重试一次，不重试POST、HTTP错误或AbortError。intake列表与scanner状态
  独立收敛，单项失败不再丢掉另一项成功数据。
- WGS Nginx对`index.html`和SPA fallback返回`no-store`，仅内容哈希命名的assets采用
  immutable缓存。依赖在`.96`用官方Node v24.15.0校验包和全新`npm ci`安装，不再
  使用BS10610的`node_modules`或npm缓存。
- 已部署release `20260903-wgs-4.1.1-6c98281-t172-fetch-recovery-r1`和frontend image
  `airflow-demo/frontend:t172-fetch-recovery`。只重建frontend-nginx。

### 验证

```text
.96 server Docker frontend: 10 test files / 40 tests passed
TypeScript + Vite production build: passed
authenticated APIs: capabilities/dashboard/runs/intake/scanner/resources/release/projects = 200
HTTP: root=200; /api/health=200
cache: shell=no-store; fingerprinted asset=immutable
database: AnalysisRun=0; Airflow DagRun=0
WGS result root: /sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/<batch>
network: 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 published
```

### 未完成及下一步

- 用户工作站需要普通刷新一次，确认旧页面状态被新shell替换；若仍复现，按该次时间
  对照Nginx access log，不再从BS10610复制任何前端依赖或构建产物。
- 不提交Git；不提交WGS批次。首个`20260901B`仍由用户在页面手工操作。

## 2026-09-03 - Codex - T171 `.96` manual WGS submission activation

### 已完成

- 把公开WGS提交参数从重复的`Sequencing batch + Analysis batch`收敛为一个`Batch`；
  后端将该值同时传给WGS两个原生参数，并继续由服务端生成完整批次目录名。
- 内部合同升级到`wgs-runtime.request.v4`，分离Airflow控制根与业务分析根。生产
  `--outpath`固定为`/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical`，WGS只在
  后面追加`<batch_no>`，不会少一层或重复一层`WGS_Clinical`。
- 在node200安装`hanjj`受限runner、evidence bridge和透明obsutil进度包装器；
  `cce.yaml`固定WGS 4.1.1仓库、新evidence根和包装器，私有配置保持0600。
- 发布`20260903-wgs-4.1.1-6c98281-t171-manual-ready-r1`，打开两个手工执行门禁并
  unpause唯一`bio_wgs`。scanner继续独立每600秒运行，auto-dispatch和旧draft preview
  均保持false。
- 修复页面中的部署能力`Failed to fetch`后，服务器认证smoke确认capabilities、
  dashboard、runs、intake、release和project接口均为200；工作站root和health也为200。

### 验证

```text
.96 backend + scripts: 356 passed
Airflow DagBag: bio_wgs, 18 tasks, 6 reschedule sensors, import_errors=[]
BS10610 server Docker frontend: 10 test files / 37 tests passed
frontend production build: tsc -b + vite build passed
HTTP: root=200, health=200, login=200, protected API set=200
database after activation: AnalysisRun=0, RunAttempt=0, Airflow DagRun=0
network: 192.168.199.0/24, gateway 192.168.199.1
published: only 172.17.61.96:12959
backup: /data/airflow-WGS/backups/T171-manual-ready-20260902T173927Z
```

### 未完成及下一步

- 按用户要求没有代为提交`20260901B`，也没有启动OBS、CCE、WGS或Step7。用户可在
  Submit Run填写单一Batch=`20260901B`后自行提交并检查首个错误证据。
- 透明传输进度代码和node200配置已接通，但尚无真实Step1/Step5数据证明obsutil当前
  输出格式可被解析；首批运行若只有阶段而无速度，应保留原始退出码并修正解析器，
  不得伪造百分比。
- SFS/OBS Cloud Eye快照仍未配置，Cloud Resources继续显示degraded，但不阻断WGS。
- 本轮按用户要求不commit、不建PR；工作树改动留给用户检查和提交。

### 回滚

使用上述备份恢复`production.env`和前一`current`目标，暂停`bio_wgs`，并把node200
`runtime.env`两个执行开关恢复为false；只滚动重建应用服务。不得删除数据库volume、
固定Docker网络、OBS/SFS对象或WGS结果目录。

## 2026-09-03 - Codex - T169/T170 node metrics and compact health panel

### 已完成

- 修复node spool幂等消费：相同/更旧时间戳不再用原始累计计数覆盖已计算的CPU和速率；
  相同时间戳仅在需要时恢复健康状态，并保留当前值和去重历史。
- `Analysis Node Health`改为`.96/.97`标签切换，默认`.96`且每次只显示一个节点；
  前端移除节点磁盘吞吐、IOPS和网络收发，只保留CPU/load、内存、更新时间和健康度。
- 后端API仍保留原始磁盘/网络字段；未修改数据库结构、公开API或采集探针合同。
- 发布`20260903-wgs-4.1.1-6c98281-t170-node-tabs-r1`；只重建frontend与metrics
  collector，未重建PostgreSQL、Redis、volume或网络。

### 验证

```text
frontend server Docker: 10 test files, 37 tests passed
frontend production build: tsc -b and vite build passed
backend server Docker: 313 passed, 1 skipped
live repeated spool ingestion: node-96 healthy, node-97 healthy, CPU/load/memory retained
HTTP: 172.17.61.96:12959/ -> 200
static asset: node tabs present; node disk/network labels absent
network: 192.168.199.0/24, gateway 192.168.199.1
published: only 172.17.61.96:12959
gates: execution/runtime/preview/auto-dispatch=false; bio_wgs paused
backup: /data/airflow-WGS/backups/T170-node-tabs-20260902T160508Z
```

测试过程中记录三个环境/脚本问题：BS10610无法解析外部Docker镜像源；旧Node v22.4.0
不满足当前lock依赖且缺Rolldown binding；首次完整backend测试把config挂载到`/config`
而测试按仓库结构读取`/app/config`。最终使用官方`SHASUMS256.txt`校验的Node v24.15.0
在服务器Docker完成前端测试/构建，并以双只读config挂载重跑backend全量通过。线上验收
脚本先后因probe函数参数、PostgreSQL JSON引号及JSON/JSONB存在性运算符写错提前退出，
改用真实函数签名与`->> ... IS NOT NULL`查询后完整验收通过；
这些失败没有启动WGS、OBS、CCE或修改业务run。

### 未完成

- Cloud Eye SFS/OBS spool仍未配置，Cloud Resources继续独立显示degraded。
- 当前分支尚未创建PR或合并main；真实WGS执行仍需单独批准。

### 回滚

将`current`恢复到
`/data/airflow-WGS/releases/20260902-wgs-4.1.1-6c98281-t169-node-metrics-r1`，将
`FRONTEND_IMAGE`恢复到前一镜像并仅重建frontend/collector。不得删除数据库、volume、
固定网络或WGS数据。

## 2026-09-02 - Codex - T168 `.96` WGS production disabled deployment

### 已完成

- 在`172.17.61.96`创建独立生产控制面：release根为`/data/airflow-WGS`，当前
  release为`20260902-wgs-4.1.1-6c98281-t168-server96-disabled-r3`。BS10610测试环境
  未停止、未迁移、未删除。
- PostgreSQL使用`.96`本地Docker volume`airflow-wgs_postgres-data`，底层为`/data`
  XFS；没有把PGDATA放到`/sg2`。业务结果和runtime spool使用
  `/sg2/14.hanjingjing/Cloud_WGS_Clinical`下的两个受控根。
- 使用用户提供的`id_rsa_hanjingjing`安装只供Airflow UID 50000读取的node200 SSH
  身份，并固定ED25519 host key；私钥未进入Git、release、镜像、数据库、日志或备份。
- 创建/复用唯一外部网络`nipt_analysis_test_net`：`192.168.199.0/24`、gateway
  `192.168.199.1`；只发布`172.17.61.96:12959`。
- 修复首次上线遗漏的客户端ACL：Nginx日志证明浏览器源地址为`10.10.30.30`，r2因
  `deny all`返回403。r3只新增`10.10.30.0/24`并保留默认拒绝；修复提交为`242f300`。
- 首次scanner bootstrap扫描1843个目录，未写历史明细；`wgs_intake_batch=0`、
  `AnalysisRun=0`、`RunAttempt=0`、Airflow`DagRun=0`。
- node200已存在并验证`hanjj`的正式CCE合同路径：cce-pipeline 0.8.1读取
  `/home/hanjj/.config/wgs/cce.yaml`，其固定kubectl为
  `/bi/BioCodeHub/WGS/kubectl` v1.32.9、kubeconfig为
  `/home/hanjj/bioinfo-cce-kubeconfig.yaml`。context `external`可访问
  `snakemake-ns`并具备所需Job及Pod/log权限；两个私有配置已收紧为0600。
- 从`.96`在线`airflow-scheduler`容器以UID 50000、受保护RSA和严格`known_hosts`
  登录`wgs-node200`后，继续执行只读CCE查询并返回`namespace/snakemake-ns`，证明
  `Airflow -> node200 -> CCE`链路可用；该验证未提交Job或改变执行门禁。

### 验证

```text
backend: 311 passed, 1 skipped
scripts: 40 passed
WGS DAG/deployment focused tests: 20 passed
Airflow: only bio_wgs; paused=true; 18 tasks; import errors=0
HTTP: health=200; anonymous capabilities=401; admin login=200;
      capabilities/release/scanner/runs=200; disabled submit=409
frontend root: server-side 200; nginx config syntax and exact 10.10.30.0/24 ACL pass
services: 10 running; restart count=0; Postgres/Redis healthy
logging: every persistent service max-size=20m, max-file=3
database: alembic 20260901_0013; one admin; zero run state
backup: /data/airflow-WGS/backups/T168-initial-20260902T140812Z
biodemo SHA256: 9f7c6fddae2c945e541b2c5e48ec6feaadf56ec17fc475682da7809cb10a83f7
airflow SHA256: bf5f20298d1f036304b82742c253738585123ffae4b6f0a75b07169bb482764b
```

本轮node200检查中，一次组合验证在`.96`宿主机调用`python`解析Airflow JSON时以
`python: command not found`退出；原因是解析器误放在宿主机而非Airflow容器。未改动
宿主机软件，改用容器内Airflow CLI重跑后确认`bio_wgs`为paused、四个执行/预览/自动
提交开关均为false、固定网络未变，且端到端只读CCE查询成功。

### 门禁与未完成

- `WGS_EXECUTION_ENABLED=false`、`WGS_RUNTIME_ADAPTER_ENABLED=false`、
  `WGS_SUBMISSION_PREVIEW_ENABLED=false`、`WGS_AUTO_DISPATCH_ENABLED=false`；
  `bio_wgs`保持paused。本次未启动OBS、CCE、真实WGS或Step7。
- node200的kubectl/kubeconfig/CCE operator合同已通过验证，但这不等于真实runtime已
  获批；node200 runner联调和一个单独批准的最小真实批次仍是启用前门禁。
- `.96/.97` node exporter端口和Cloud Eye spool尚不可用，资源页会如实显示degraded，
  但不影响当前禁用态控制面。
- 管理员初始密码仅保存在`.96`的`/data/airflow-WGS/env/production.env`，不要复制到
  文档或聊天；`chenjc`已获得该明确文件的只读ACL，实测可读且不可写。该文件还包含
  数据库和内部服务密钥，只能用于受控管理，需要时应优先重置而非复制。

### 回滚

停止`.96`的`airflow-wgs` Compose并将`current`恢复到先前目标即可；不要使用`down -v`，
不要删除`airflow-wgs_postgres-data`、`/sg2`数据、固定Docker网络或BS10610测试环境。

## 2026-09-02 - Codex - T167 `hanjj`运行身份与目录迁移设计

### 已完成

- 只读验证用户提供的新RSA：远端实际账号为`hanjj`，可登录`.96/.97/.200`，三台
  `/proc`均可读；Windows源文件ACL已收紧，私钥内容未输出。
- 核对node200：`/home/hanjj/.obsutilconfig`存在且可读，正式WGS环境中的
  `cce-pipeline`可执行；`hanjj`尚无kubeconfig、kubectl和CCE operator config。
- 用户确认新批次直接写
  `/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/<batch>`，控制文件写
  `/sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow-wgs/runtime`。
- 新增`docs/29_WGS_HANJJ_RUNTIME_IDENTITY_MIGRATION_DESIGN.md`，固定request v4双根、
  单一活动身份、历史只读兼容、`.96/.97`资源监控、Cloud Eye边界、禁用态切换和回滚。

### 未实施

- 未把新私钥复制到BS10610，未创建新目录，未复制或修改OBS/kubeconfig/kubectl/cce
  配置，未修改node200 runner或线上Compose。
- 未运行身份迁移代码、Docker、前端或真实WGS测试；本轮是设计固化。此前针对旧身份
  和单`.96`目标的未提交原型已保存到本地stash，未进入本设计提交，不能作为实现依据。
- 当前线上继续使用`chenjc`和旧runtime；三个执行门禁仍false且`bio_wgs` paused。

### 下一步

用户复核文档29后，编写逐文件实施计划。实施必须先RED测试request v4和双根边界，
再配置node200/BS10610，最后创建disabled release；真实batch需要再次单独批准。

### 回滚

本轮只有文档变更，无运行时回滚。删除或回退文档提交即可；不得删除旧runtime、
数据库、OBS/SFS、结果、volume或固定Docker网络。

## 2026-09-02 - Codex - T166 WGS workflow 与 Rule 投影修复

### 完成

- 新增后端唯一`wgs_stage_contract.py`，Batch Runs和Run Detail均由API返回
  Step1上传、Step2启动、Step3分析、Step4发布、Step5下载、Step6物化；前端不再
  维护第二套六阶段文案或用生物学Rule phase代替项目workflow。
- WGS 4.1.1 Rule统一由`workflow_phases.py`映射为Pre-calling、Variant analysis、
  QC和Cloud delivery。按raw event首次出现顺序生成稳定sequence；只从已登记
  `analysis.log`中按rule/jobid和已登记sample做精确关联，不可唯一匹配的聚合Rule留空。
- 历史run`WGS_20260901_031616_C74E6C` attempt 1完成安全投影回放：208条Rule，
  208条sequence，147条sample关联。`cloud_finalize_delivery`在已验证run success时
  公开投影为success；原始logger事件不修改。
- Message与ETA彻底分列；移除Layer展示与排序。修复WGS stage card不可见的CSS变量。
- 删除未使用的前端mock workflow catalog、PipelineCard和PipelineSelector；移除旧WGS
  task百分比与前后端重复标签。六阶段名称只在后端合同中定义，Rule phase也只在后端
  定义。
- 代码审查后补齐：无阶段证据时按run终态投影pending/failed/canceled；logger提供的
  sample/family必须命中本次分析已登记样本；analysis.log使用有界的字节offset增量索引，
  缓存上下文每轮与当前sample registry重新关联；前端删除残余WGS Airflow task allow-list。

### 发布与验证

```text
commit: 066489d598671bf1f454a44d0dc535542fb88d46
release: 20260902-wgs-4.1.1-6c98281-t166-workflow-rule-r2
frontend: airflow-demo/frontend:t166-workflow-rule-r3
frontend image: sha256:1326a0668703c685f35e5e4dbed82e24242e31d88da7231af13565eda7a08c12
backend image: sha256:49635d01a7e4b55b7ba1ab13888bb18aed0a8b61babab24da6e9c95b92d468a6
BS10610 backend: 312 passed
BS10610 frontend: 9 files / 35 tests passed; TypeScript and Vite build passed
API smoke: Batch/Finished正确；Step1-Step6全部success；四个Rule phase；
           sequence=208，sample-linked=147，ETA text in Message=0，
           cloud_finalize_delivery=success
backup: backups/T166-workflow-rule-20260902T1655+0800
biodemo SHA256: 23980d97a5a4fd3f3bfcc9f8b22eadb80c647dc2aaaa7fbcd8e25a8811e8795b
airflow SHA256: b4706e9838b2672a545cbd3596ba99cc33c12d69c4ffaa335a3b9f122d44e3f6
network: 192.168.199.0/24, gateway 192.168.199.1; only 172.17.106.10:12959 published
gates: execution=false, runtime=false, auto-dispatch=false; bio_wgs paused
review: no remaining Critical, Important or Minor findings
```

内置浏览器因URL安全策略拒绝访问私网HTTP地址，未进行截图验收且未绕过；生产API、
容器HTTP与静态asset已验证。临时rule-reader Job已自动清理，CCE中无残留reader Job。

### 未完成

- Step1/Step5真实速度与ETA仍依赖node200启用Airflow透明obsutil wrapper；本次没有伪造。
- 172.17.61.96/.97与SFS/OBS资源采集的外部监控条件仍未补齐。
- admin Step7尚未获得生产执行批准。
- 聚合/批次Rule没有唯一sample语义时继续留空，这是预期行为，不按行数猜测。

### 回滚

恢复T166备份env并将`current`指回T165 release，只重建backend/frontend/run-observer。
本次无schema迁移；不要删除数据库、volume、OBS/SFS、FASTQ、结果或外部网络。


## 2026-09-02 - Codex - T165 生产前端同步与Run检索/结束时间修复

### 完成

- 对照`docs/28`、合并后的main和T163生产release完成差异审计。线上旧前端确实缺少
  Run Tracker Batch和新版Batch Runs；不是设计未完成，而是完整候选尚未发布。
- `/api/runs`与`/api/dashboard/runs`现显式检索Batch、Sample ID和family ID；run列表
  顶层返回`batch_no`。Run Tracker与Batch Runs均展示Batch和Finished，全局/页面搜索
  提示同步包含batch和sample。
- 新run在finalize写不可变结束时间；历史成功WGS可由`sync-airflow`使用DagRun
  `end_date`补齐。生产run`WGS_20260901_031616_C74E6C`已回填
  `2026-09-02T04:29:44.273615Z`。
- 发布完整生产UI：业务Step1-Step6状态/进度、WGS QC隐藏、Samples/家系安全字段、
  六阶段图、Rule排序与换行、opaque日志、Failure Triage、WGS 4.1.1 Catalog、受控
  Submit表单和admin Step7入口均已同步。登录后capabilities正常加载。
- biodemo升级到`20260901_0013`，创建disabled release
  `20260902-wgs-4.1.1-6c98281-t165-production-ui-r1`。执行/runtime/自动提交均为false，
  `bio_wgs`已paused；T7扫描仍启用且周期600秒。

### 验证与证据

```text
BS10610 backend: 289 passed, 1 skipped
BS10610 scripts: 40 passed
BS10610 DAG: 136 passed, 7 skipped
BS10610 frontend: 9 files / 34 tests passed; Vite build passed
frontend image: sha256:267e5c3ee07de62bcea0c2d1b024a9c88f1f8cba0b25204a4cc27c59dd1e09ff
HTTP: health/login/capabilities 200; Batch/Sample/Family search matched the run;
      Finished returned the authoritative Airflow end; disabled submit returned 409
scanner: scanned=1841, error=false, intake rows=10, 2226 rows=0
backup: backups/T165-production-ui-sync-20260902T135306+0800
biodemo SHA256: d88d55d995c7276d77012adc72297ae8687c84163c4f81c52ee5b1daf8d2811f
airflow SHA256: c7d49bb4b0314fdf563b2f20d6bc8adb881c7576e16f418554bcd1b5e6edf9b3
network: 192.168.199.0/24, gateway 192.168.199.1; only 172.17.106.10:12959 published
```

### 尚未完成

- node200尚未安装/启用Airflow自有obsutil progress wrapper，因此Step1/Step5只能显示
  阶段，不能显示真实速度/ETA；已有终态status不能反推历史速度。
- `.96/.97`的node exporter端口当前拒绝连接，Cloud Eye SFS/OBS spool缺失；资源页已
  上线但如实显示degraded，不回退展示BS10610或伪造云指标。
- admin Step7合同、RBAC和UI存在，但尚未在生产执行；必须另行批准。
- 不实现数百Rule实例的完整动态DAG；当前批准方案是六阶段依赖图加Rule实例表。

### 回滚

先保持`bio_wgs` paused和两个执行门禁false，原子指回T163 release并仅重建应用服务。
数据库0013为加法迁移；不要降级，除非明确接受删除stage/draft/resource数据并设置受控
downgrade开关。不要删除PostgreSQL/Redis volume、OBS/SFS、FASTQ、结果或外部网络。

## 2026-09-02 - Codex - T163 登录、T7发现与在途状态修复

### 完成

- 修复登录前capabilities请求：只有认证Session存在时才挂载capabilities provider；
  登录后建立新provider并加载生产能力，不再保留`AUTH_REQUIRED`兼容视图。
- T7卡片隐藏`BarcodeStat.txt`实现细节，改为产品语义和三个紧凑状态标签；周期继续
  来自API的600秒配置。
- scanner增加`WGS_INTAKE_IGNORED_CHIP_IDS`精确忽略。2226记录删除前确认
  `analysis_id IS NULL`且关联数为0；删除和run状态修正在事务内完成并补充审计。
  立即`--once`重扫后2226仍为0，本轮扫描1841，AnalysisRun/DagRun仍各1。
- 修复相同attempt恢复后的业务投影：只有run仍处于Step4假失败、Step4权威状态文件
  身份匹配且success，Step5注册才可清为downloading；真实Step5失败不会被普通注册
  掩盖。Step4/Step5 start按runner返回的`retry_no`等待新generation可见，不再比较
  BS10610/node200时间，防止sensor读取上一代failed。
- 当前run`WGS_20260901_031616_C74E6C`保持同一DagRun/attempt/Master，普通Step4
  已success。首次Step5在结果archive下载79.86%时因`no space left on device`失败；
  旧worker退出且`df`恢复可用后，runner归档完整证据并以retry-1复用obsutil checkpoint。
  retry-1随后完成，Step5 start/wait均为success，当前正在Step6 materialize；未重跑
  Step1-Step4，最终成功尚未确认。

### 发布与验证

```text
release: 20260902-wgs-4.1.1-2499749-t163-ui-intake-recovery-r4
frontend image: sha256:23f916eb9c60f3dbbf5749e4b34fbc7b29db9d9c5a8eb519f7cc11c09412da57
backend: 252 passed, 1 skipped
bio_wgs: 9 passed; runner: 30 passed; py_compile passed; Airflow import_errors=[]
frontend: 9 files / 32 tests passed; Vite build passed
HTTP: /api/health 200; anonymous /api/platform/capabilities 401 AUTH_REQUIRED
scanner: scanned=1841; 2226 rows=0; no new AnalysisRun or DagRun
network: 192.168.199.0/24, gateway 192.168.199.1
published host ports: only 172.17.106.10:12959
backup: backups/T163-ui-intake-step4-20260902T105843+0800
review backup: backups/T163-review-fix-20260902T115421+0800
Step5 retry backup: backups/T163-step5-retry-20260902T120703+0800
full branch: backend 283 passed/1 skipped; scripts 40 passed; bio_wgs 10 passed;
             frontend 9 files/33 tests and Vite build passed; Compose config passed
```

### 未完成与下一步

- 当前真实batch已通过Step5并进入Step6，仍不能表述为分析成功。保持正常调度即可；
  终态后核对Step6物化和finalize，再暂停DAG并关闭两个执行门禁。
- T159-T161完整新候选仍需单独disabled migration/release；T163线上release是从已运行
  的2499749控制面做的最小兼容修复，没有提前部署migration 0013。

### 回滚

恢复T163备份env并原子指回T152 r8，再只重建应用服务；数据库回滚仅需删除T163审计
并把该run恢复到变更前投影。不要删除volume、OBS/SFS、FASTQ、当前run或外部网络。

## 2026-09-02 - Codex - T161 生产WGS 4.1.1接入纠正（进行中）

### 目标与当前结果

- 用户最终确认生产云端流程继续使用`wgs-4.1.1`，`wgs-4.2.0`仅为测试版本。
- 生产共享仓库只读审计：`dev_CJC_4.1.1_cloud`，commit
  `6c982817614db6a1157b6f287427ddf01ac91827`，版本`V4.1.1`；该commit已支持
  schema-1 JSON `ANALYSIS_COMPLETE`。
- catalog为`wgs-4.1.1-6c98281`，共享路径固定为BS10610
  `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1`和node200
  `/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1`。
- runner分别传递`--batch`和`--analysis-batch`，platform为`T7`，不传4.2.0
  测试参数`--algo`；后端派生`WGS_<analysis_batch>_T7Hg38V4.1.1`。
- WGS仓库未修改；没有部署、OBS、CCE、真实分析或Step7操作。
- PR #6曾按错误理解改到4.2.0测试仓库，但尚未部署；当前纠正PR会回退
  release、runner、API、前端、测试和文档。PR #7已关闭且未合并。
- 生产纠正已通过GitHub PR #8合并：
  `https://github.com/boksic1986/airflow-BS-demo/pull/8`，merge commit
  `6046a280db1271ae41575113cacd431e990a74c2`。root main已ff-only同步；线上
  T152、数据库、OBS、SFS、CCE、Docker服务和网络均未修改。

### 已运行验证

```text
BS10610 Docker focused backend: 43 passed
BS10610 Docker runner: 29 passed
BS10610 Docker full backend: 280 passed, 1 skipped
BS10610 Docker full scripts: 38 passed
Airflow DagBag: import_errors=0, bio_wgs 18 tasks, 6 reschedule sensors, paused=true
PostgreSQL 15 migration: 0001->0013, downgrade 0013->0012, upgrade 0012->0013 passed
BS10610 Docker frontend: 9 files / 32 tests passed
BS10610 Docker Vite build: passed
Compose config: passed
git diff --check and candidate secret scan: passed
network: 192.168.199.0/24, gateway 192.168.199.1
published port: only 172.17.106.10:12959
```

以上backend 280/1、scripts 38、frontend 32/build和DagBag检查已在生产4.1.1
纠正后重新执行；共享仓库HEAD/branch/version及无`--algo`合同也已只读核对。

### 待完成

- 代码、前端和文档已通过GitHub PR #4合并：
  `https://github.com/boksic1986/airflow-BS-demo/pull/4`。
- merge commit为`17c0f97ec5128427d14555f3cab6fc6f6152367a`；root main已
  `pull --ff-only`同步。原T146开发分支已经结束，后续部署应从该main新建分支。
- 下一阶段仍是disabled release/在线暂停切换；需要单独确认后才可修改在线T152、
  安装node200 wrapper或执行真实WGS。

### 回滚

尚未修改在线服务或数据。代码回滚只涉及候选分支；不得删除`.artifacts/`或在线T152状态。

## 2026-09-02 - Codex - T159四项合同修正

### 已完成

- `docs/28_WGS_PRODUCTION_UI_AND_SUBMISSION_DESIGN.md`已按用户确认语义修订，并新增实现计划`docs/superpowers/plans/2026-09-02-wgs-transfer-submit-logs.md`。
- 新增透明`wgs_obsutil_progress.py`。node200 runner对Step1/Step5按5秒聚合请求级JSON，backend直接从stage status同步真实bytes/files/speed/ETA；不再等待cce-pipeline提供进度。
- 新增`POST /api/wgs/runs`和单页Submit表单。浏览器只提交catalog ID及platform/sequencing batch/analysis batch/use_reference；WGS prepare执行sampleinfo→analysis，prepare成功后只导入最终`sampleinfo.tsv`安全字段。
- 失败Rule不再需要log-key到SFS路径registry。backend只读已注册的Master analysis.log最后2MiB，以job ID/rule name截取最多64KiB；Rule表显示摘要，完整日志继续走现有opaque key。
- T160确认opaque key无需人工配置，并把完整日志接口改为从末尾64KiB分块倒读；单次最多8MiB/1000行，返回`file_size/truncated`，大型analysis.log不再整文件载入内存。
- WGS release catalog没有改动，仍为`wgs-4.1.1-2499749`；等待WGS正式更新后再统一审计和改绑。

### 验证

```text
BS10610 backend: 279 passed, 1 skipped
T160 RED evidence: 2 expected failures (whole-file read and missing bounded reader)
T160 focused GREEN: 2 passed
BS10610 runner/adapter/timing/wrapper: 51 passed
BS10610 Docker frontend Vitest: 9 files / 32 tests passed
BS10610 Docker frontend Vite production build: passed
frontend runtime: Node 22.22.2 / npm 10.9.7, container network=none
BS10610 Docker network preflight: nipt_analysis_test_net=192.168.199.0/24, gateway=192.168.199.1, attachments unique/in-range
published host mapping: only frontend 172.17.106.10:12959
Python compile: passed
git diff --check: passed
remote evidence: /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/t159-20260902
```

### 未完成/下一步

- 尚未把wrapper安装到node200，也未修改其受控operator config；因此当前在线Step1/Step5不会突然出现速度。这应在新的disabled release预检中完成，并用mock obsutil及一个单独批准的真实传输验证。
- 尚未部署、迁移或切换`current`；在线T152仍保持execution/runtime=true和DAG unpaused。本轮没有暂停或覆盖它。
- WGS下一个正式HEAD确定后，更新catalog commit/release ID并重新验证prepare CLI、最终sampleinfo路径及`use_reference`枚举，然后再做disabled release。
- 当前worktree包含此前T153-T157大批未提交变更；不要只挑T159文件部署，必须按完整候选release进行迁移/Compose/DAG/network验收。

### 回滚

本轮未触碰生产服务、数据库、OBS、SFS或CCE。代码回滚仅涉及候选worktree；保留`.artifacts/`和在线T152状态。

## 2026-09-02 - Codex - T153-T158生产前端开发检查点

### 已完成

- 新增文档28和迁移`20260901_0013`；实现权威阶段/精确进度、扩展Rule状态、
  安全Samples、opaque日志、WGS Failure Triage、当前Workflow Catalog。
- 前端增加Run Tracker Batch、人性化Step1-Step6、精确进度/不可用态、Samples、
  Rule阶段图与实例表；移除WGS QC和Master image digest。
- 实现受控项目catalog、三步submission draft API/UI、60点资源快照、`.96/.97`
  速率投影、SFS/OBS UI和admin Step7双确认合同。提交和Step7均使用确定性DagRun；
  crash重试不重复创建，Step7内部入口必须携带匹配的admin维护操作ID。
- transfer只接受严格`cce-pipeline.transfer-progress.v1`，terminal stage禁止成功/失败
  互相覆盖；不再用阶段位置生成总体百分比或分析ETA。
- evidence bridge增量同步Rule JSONL及`analysis.log`，终态reader保持SFS只读。

### 验证

```text
BS10610 backend: 298 passed, 1 skipped
BS10610 scripts: 37 passed
BS10610 bio_wgs DAG: 8 passed
temporary PostgreSQL 15: 0013 upgrade/downgrade/upgrade passed
frontend TypeScript/Vite production build: passed（由T159在BS10610无网络Docker容器重新验证；本机Node结果不作为验收）
frontend Vitest: 9 files / 32 tests passed（BS10610 Docker）
BS10610 offline frontend image: airflow-demo/frontend:t153-production-ui-disabled
frontend image digest: sha256:c7e49e0a69d40570dfafd3e20b3a66308f7a6f726ed7623127d004bb3f9ba202
nginx config/static HTTP smoke: passed（无宿主机端口）
Compose config: passed
published ports: only 172.17.106.10:12959
network: 192.168.199.0/24, gateway 192.168.199.1
scanner interval: 600 seconds
independent read-only review: Critical 0 / Important 0 / Minor 0
```

### 未完成和阻塞

- cce-pipeline 0.8.1未提供transfer-progress v1，上传/下载只能显示真实阶段，不能显示
  速度/ETA。
- WGS `sampleinfo`不提供FASTQ配对/pending的只读preview；draft DB/API/UI及最终提交
  幂等测试已完成，`WGS_SUBMISSION_PREVIEW_ENABLED=false`使API/UI fail closed。
- Rule JSONL只有opaque log key，没有受控SFS相对路径registry；目前可读analysis.log和
  stage worker日志，尚未镜像失败Rule stderr尾部，禁止以任意路径读取替代。
  但真实async worker不能安全启用。
- Airflow catalog为`2499749`，共享WGS HEAD已是`6c98281`；未获得版本改绑决定。
- 当前在线T152 env仍是execution/runtime=true且bio_wgs未pause；本轮candidate以四门禁
  false完成Compose验证，但未覆盖在线状态、未迁移生产DB、未部署release、未执行真实
  Step7或Cloud Eye/node exporter采集。

### 下一步和回滚

先冻结WGS preview与transfer-progress合同并确认新release commit，再完成T156/T157远端
验收、生产备份和disabled release。当前改动未部署，回滚只需丢弃本worktree改动；不得
修改现有生产DB、current release、OBS/SFS或运行记录。

## 2026-09-01 - Codex - T152 Step4 race repair and WGS marker blocker

### Completed

- Implemented and deployed Airflow commit
  `29c8378b2b4e5cf860e7978d9e23233f710035af` plus failure-projection commit
  `1bd7530f2a55bab530475fffb48eeabb025fea21` in release
  `20260901-wgs-4.1.1-2499749-t152-step4-recovery-r8`.
- Step4 now waits up to 600 seconds for the exact bound Master after a trusted
  Step3 success. Failed Step4 generations can restart only with the same
  request SHA after the old worker exits; prior status/worker/log are retained
  under `history/step4_publish/retry-N`.
- Backend same-attempt recovery resets only the known Master timing false
  failure to `publishing` and audits `run.step4_publish_recovered`. Repair
  capability uses the canonical Step3 Master event identity rather than a
  `wgs-master-*` prefix.
- A real terminal Step4 failure now updates biodemo/Run Detail to `failed`
  with its evidence message; the production API no longer remains stale at
  `publishing` after the DagRun fails.

### Production recovery and new blocker

- Backed up both databases, the complete attempt sidecars/logs, binding and
  Airflow Task state at
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/T152-step4-recovery-20260901T173906+0800`.
  `biodemo.dump` SHA256 is
  `08af9e4f6a50945affb355380858a4ab11653356dbfa43fa44fdccf6174e6c3e`;
  `airflow.dump` SHA256 is
  `3ac29e63f3dcb4dba401a2490e8485acd6c246550a2b9955e6330790f4da4256`.
- Cleared only Step4 and downstream in the original DagRun. Step1-Step3 stayed
  success; Master `cce-master-79c59ff6401e15d76aa5` retained UID
  `8ef69ad6-96cd-4dd2-a94a-b214287af1d2` and its original Complete timestamp.
  No upload or Master submission was repeated, and CRAM repair was not used.
- The retry crossed the repaired Master gate, then failed at a second,
  independent WGS contract error: `ANALYSIS_COMPLETE is invalid`. The OBS
  object is a valid 149-byte schema-1 JSON identity marker with `status=PASS`,
  while frozen `cce_delivery.py` accepts only the legacy literal
  `status=PASS\n`. This is a producer/consumer mismatch inside WGS 2499749,
  not duplicate `cloud_finalize_delivery` execution.
- Stopped without modifying the WGS repository, frozen bundle, OBS/SFS data or
  marker. The original DagRun is failed at ordinary Step4; Step5-Step6 have not
  run. Do not clear it again until the WGS contract and recovery method are
  explicitly approved.

### Validation and rollback

```text
runner: 28 passed
backend: 250 passed
DAG import errors: 0
Compose config: passed
network: 192.168.199.0/24, gateway 192.168.199.1
published port: only 172.17.106.10:12959
```

Rollback the Airflow fix by restoring the backed-up runner and previous r6
release, then recreating only backend/API/scheduler/worker. Do not restore the
databases merely to roll back code, delete retry evidence, rerun Step1-Step3,
or replace the CCE Master.

## 2026-09-01 - Codex - T151 YF non-clinical scanner exclusion

### Goal and implementation

T7 scanner现在在配对统计前排除sample ID以大写`YF`开头的非临检样本。YF不计入
eligible、add-on或pair issue；YF-only为`no_new_wgs`，YF缺对不触发
`needs_review`。名称fingerprint升为v3，并计算一次旧v2策略摘要，保证已有ready
记录只因YF过滤升级时不会误报输入漂移。数据库/API结构和前端均未修改。
实现提交为`9ab2dd2c95528875b11cf8b82a7e4350eedb08b8`。

### Validation and deployment

```text
TDD RED: 3 YF behavior failures, then 1 v2 migration failure
focused scanner: 18 passed
full backend: 247 passed, 1 skipped
release: 20260901-wgs-4.1.1-2499749-t151-yf-filter-r6
services recreated: wgs-intake-scanner only
2222: 192 YF entries / 96 pairs; ready(96) -> no_new_wgs(0)
2223/2224/2227: remain ready with 12/8/10 pairs
before/after: AnalysisRun 1, RunAttempt 1, Airflow DagRun 1
active run: WGS_20260901_031616_C74E6C, attempt 1, same DagRun, step3_monitor
scanner: 600 seconds, auto dispatch false, 1837 directories, no error
network: 192.168.199.0/24 gateway 192.168.199.1; only frontend publishes 12959
```

部署前biodemo备份为
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/T151-yf-filter-20260901T162127+0800/biodemo.dump`，
SHA256为`ed7dfe046d19a53b6cee0f52da2e0925e5e58e844eeca19d2b37848cb52d0ae3`。

### Remaining work and rollback

自动prepare/dispatch仍关闭；T151未创建分析、上传OBS或启动CCE。当前T149批次继续
由原DagRun监控。回滚只需切回T150 r5并重建scanner；不要恢复数据库、删除intake
记录、重建网络或干预当前CCE批次。

## 2026-09-01 - Codex - T150 T7 FASTQ scanner repair

### Goal and completed work

修复T7 scanner将软链接FASTQ误判为`no_new_wgs`，按目录项名称识别WGS和
R1/R2，不访问链接目标。名称级fingerprint升级为v2；保留旧v1普通文件ready
记录的兼容升级，并允许历史`no_new_wgs`按当前名称重新分类。Dashboard根据API
的`schedule_seconds`显示“每10分钟”，不再硬编码30分钟。

创建并切换到release
`20260901-wgs-4.1.1-2499749-t150-t7-scanner-r5`。只重建
`wgs-intake-scanner`和`frontend-nginx`；PostgreSQL、Redis、Airflow、backend、
run observer、volume、网络和当前CCE Master均未重建。离线frontend镜像为
`airflow-demo/frontend:t150-t7-scanner-10m` / `sha256:cef9e111...e386cdb`，
镜像内只有本次index、CSS和JS，SHA256与本地tested dist一致。

### Validation and production evidence

```text
BS10610 backend: 243 passed, 1 skipped
frontend Vitest: 9 files / 31 tests passed
frontend TypeScript + Vite production build: passed
HTTP: 172.17.106.10:12959 -> 200
scanner: interval 600, auto dispatch false, scanned 1837, errors 0
2227: ready, 10 eligible pairs
2222/2223/2224: ready, 96/12/8 eligible pairs
2221/2225: no_new_wgs
2226: retained pre-existing needs_review state
before/after: AnalysisRun 1, RunAttempt 1, Airflow DagRun 1
active run: WGS_20260901_031616_C74E6C, attempt 1, same DagRun, step3_monitor
network: 192.168.199.0/24 gateway 192.168.199.1; only 172.17.106.10:12959 published
```

备份保存在
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/T150-t7-scanner-20260901T151336+0800`，
`biodemo.dump` SHA256为
`b606f3f284ffc7d72e992cae79534c5d3580f20dcb6890d2902dbdb2f2026380`。

### Deployment incident and correction

测试staging `T150-t7-scanner-red`实际是指向T149 r4的软链接，不是独立副本；早期
测试覆盖因此改写了r4的scanner源码和测试。受控清理的realpath检查阻止了递归
删除。随后从T150直接父提交`ea71adf`归档并恢复r4的两个文件，Git blob分别严格
匹配`4239f157...`和`7eaa5bf9...`；r5文件匹配T150提交`b5afe9c`的
`1ea06387...`和`cfd811dc...`。最后只删除该staging软链接和临时脚本，r4回滚
release、当前r5和生产数据均完整保留。

### Remaining work and rollback

T150没有启用自动prepare/dispatch，也没有创建分析目录、OBS传输或CCE任务。
当前T149批次仍由原DagRun定时监控到真实终态。回滚T150只需切回T149 r4、恢复
frontend tag并重建scanner/frontend；不要恢复数据库、删除intake记录、重建网络或
干预当前CCE批次。名称重新分类是对已有7条scanner记录的正常幂等更新。

## 2026-09-01 - Codex - T149 Step3 repair and in-flight takeover

### Outcome

- Repaired the node200 stage protocol with unique same-directory temporary
  files, file and directory fsync, atomic replace and monotonic
  `accepted -> running -> terminal` transitions. Step3 no longer publishes a
  generic running state without the frozen Master identity.
- Replaced the hard-coded Master prefix check with exact validation against
  `batch-binding.json`; incomplete accepted/running transitions return not-ready
  instead of HTTP 500. Same-attempt registration recovers the monitoring-induced
  business failure and writes one `run.step3_monitor_recovered` audit event.
- Bound Rule evidence to the authoritative frozen CCE run label
  `cce-run-650a0767d41b3157`; public workload projection remains Master-only.
  Progress now falls back to the bound Master Step3 `current_rule` when logger
  projection lags, without fabricating a RuleState row.
- Deployed release
  `20260901-wgs-4.1.1-2499749-t149-step3-recovery-r4` with deployed runtime
  code commit `b7730bc1a09481f67663b2c3d7f37e50b5770b93`.

### In-flight run state

- Preserved `WGS_20260901_031616_C74E6C`, attempt 1, DagRun
  `manual__WGS_20260901_031616_C74E6C__a1` and Master
  `cce-master-79c59ff6401e15d76aa5`.
- Step1 upload and Step2 Master remain `success`, try 1. Step3 launcher is
  `success`, try 2; the sensor is `up_for_reschedule`, try 2. There was no new
  OBS upload or CCE Master submission.
- Business state is running with no terminal timestamp/error; observer is
  active and healthy. Authenticated UI-equivalent API shows current Rule
  `MEI_MEICall`, 41 Rule rows (19 success, 2 running, 20 planned), and the same
  Master in Running phase.
- The original DagRun must continue from the real CCE terminal state into
  Step4-Step6. Do not manually poll continuously; terminal delivery remains the
  only unfinished T149 acceptance item.

### Verification and safety

- Pre-takeover backup:
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/T149-step3-recovery-20260901T132953+0800`;
  all recorded SHA256 checks passed.
- Final canonical isolated backend suite: 238 passed and 1 skipped; final
  focused WGS suite: 48 passed. Runner 30 and DAG 7 passed at the preceding
  T149 checkpoint. Shared-SFS concurrency smoke completed 200 writes with no
  partial file.
- One diagnostic invocation inherited production WGS-only deployment scope and
  therefore exercised legacy PGTA/NIPT tests under the wrong environment. The
  canonical rerun explicitly removed required runtime settings, as those unit
  tests expect, and passed in full.
- Network remains `192.168.199.0/24`, gateway `192.168.199.1`; only
  `172.17.106.10:12959` is published. PostgreSQL, Redis, volumes, OBS/SFS data
  and the CCE Master were not rebuilt or deleted. Scheduler is unpaused.

### Rollback

- Point `current` back to the previous immutable r3 release and recreate only
  backend if the progress projection must be reverted. The runner/database
  repair is separately recoverable from the T149 backup; do not roll back by
  resubmitting Step1 or Step2.

## 2026-09-01 - Codex - T148 prune completed worktrees and branches

### Outcome

- Retained exactly two worktrees: the repository root on `main` and
  `D:/pipeline/airflow-demo-worktrees/T146-wgs-081-manual-run` on the only
  active development branch.
- Deleted seven completed or historical secondary worktrees: T096, four T127
  worktrees, T129 and T145.
- Deleted the unregistered historical `T133-local-staging-artifacts` directory
  after the final directory-level audit (30 files, 4 subdirectories, 2,114,815
  bytes).
- Deleted 54 local historical branches and 16 remote historical branches.
  After the cleanup, local branches are only `main` and
  `jiucheng/platform/T146-wgs-081-manual-run`; the GitHub remote exposes only
  `origin/main` (plus its symbolic `origin/HEAD`).
- Merged this cleanup record through a temporary T148 pull request, then removed
  the temporary local and remote branch so it did not become another stale
  branch.

### Destructive scope and recovery

- Under the user's explicit cleanup authorization, discarded the four tracked
  T096 edits and the untracked `airflow-snakemake-ppt/` directory (308 files,
  29 directories). The working-tree copies are not recoverable.
- T129 removal initially left generated frontend dependencies because Windows
  could not remove a long nested path. Git had already removed its worktree
  registration; the exact residual T129 directory was then removed using its
  verified extended absolute path.
- Deleted branch names can be recreated from known commits while those objects
  remain reachable or in reflogs, but no recovery guarantee is made after Git
  garbage collection. Deleted remote branch refs require recreation and push.

### Runtime boundary and verification

- Preserved the T146 `.artifacts/` directory and did not inspect, restart,
  cancel, pause or otherwise modify its active WGS analysis.
- Did not operate Airflow services, WGS/CCE/OBS, PostgreSQL, Docker volumes or
  the fixed Docker network.
- Final verification requires exactly two registered worktrees, two local
  branches, only `origin/main`, no open PRs, root/main equality and a clean
  tracked T146 worktree apart from its preserved `.artifacts/`.
- No application test suite was run because this task changes repository state
  and Markdown records only.

## 2026-09-01 - Codex - T147 Airflow worktree reconciliation

### Goal and outcome

- Audited all nine local Airflow worktrees against `origin/main` before changing
  any branch.
- Fast-forwarded the clean T132 and T145 worktrees to the current mainline.
- Confirmed with `git cherry` that the T127 dashboard, frontend compatibility,
  review-fix and rule-phase commits are patch-equivalent to changes already in
  main, so they were not merged a second time.
- Preserved the dirty T096 documentation/PPT worktree exactly as found. Its
  tracked edits and untracked presentation directory were not staged, moved or
  overwritten. Preserved the obsolete T128 NIPT scan branch outside the current
  WGS-only mainline.
- Created the T147 reconciliation branch from current main for these state-only
  records and merged it through a GitHub pull request.

### Runtime boundary

- This task changed no backend, frontend, DAG, observer, Compose, migration or
  runtime configuration.
- The active T146 WGS run was not queried repeatedly, restarted, cancelled or
  otherwise altered. Airflow scheduled sensors and the task-scoped observer
  remain responsible for monitoring it.
- Docker network and published-port state were not touched.

### Verification and residual worktrees

- `git diff --check` and worktree/branch reference checks passed for this PR.
- T132 and T145 now point at the pre-PR `origin/main` commit. T146/T147 carries
  the PR commit; other T127 branches remain as historical local branch labels.
- T096 requires an explicit future decision about its five local changes.
  T128 requires an explicit decision to archive or delete; it must not be
  silently merged into the WGS-only product.
- No runtime test suite was run because this PR contains state documentation
  only and does not change executable code.

## 2026-09-01 - Codex - T146 clean replacement run active

### Goal and outcome

- Cleared all workflow evidence and data for the old `20260825A` acceptance
  analysis without touching source FASTQ, WGS source, user accounts, scanner
  state, Docker volumes or the external network.
- Created and submitted a new run through the authenticated frontend-equivalent
  API. The replacement is `WGS_20260901_031616_C74E6C`, attempt 1, bound to
  `wgs-4.1.1-2499749` / commit `2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68`.
- At handoff, validate and prepare are successful and Step1 input upload is
  running. The frontend API reports `15% / input_transfer.wait_step1_upload`.
  Per operator direction, stop manual high-frequency polling; Airflow's
  reschedule sensor and the Step3 event-driven observer remain responsible for
  scheduled monitoring.

### Controlled cleanup

- Before deletion, created mode-0600 PostgreSQL custom dumps:
  - `biodemo-before-20260825A-clean-20260901.dump`, SHA256
    `129f0e1b70fcaa75f9220f63fec755a3f30f3d539ce9707ce734b6973a5a6590`.
  - `airflow-before-20260825A-clean-20260901.dump`, SHA256
    `b13e807f0ba9d423b1616e8028a865ac6943865478c8aca4b41aa105cd49f2ce`.
- Deleted the exact old analysis and cascaded biodemo run/sample/transfer/
  observer/snapshot rows, 11 exact terminal Airflow DagRuns, its Airflow runtime
  and three task-specific evidence directories. Thirteen old run audit events
  were removed; one `run.purge_for_clean_release_reanalysis` audit remains.
- Read-only CCE readers verified SFS run/linkage and OBS FASTQ/result prefixes
  absent. The readers, manifests and helper scripts were then deleted. Exact
  analysis-labelled CCE Job/Pod and the batch lock are absent.
- The first OBS reader attempt failed before container start because Huawei OBS
  CSI rejects a read-only PVC mount. A second reader used the same PVC mount
  mode as production but ran only `test` commands; it made no object changes and
  was deleted after both prefixes were confirmed absent.

### Current safety and next check

- `WGS_EXECUTION_ENABLED=true`, `WGS_RUNTIME_ADAPTER_ENABLED=true`,
  `WGS_AUTO_DISPATCH_ENABLED=false`; `bio_wgs` is unpaused only for the approved
  manual run. Network remains `nipt_analysis_test_net` (`192.168.199.0/24`,
  gateway `.1`) and only `172.17.106.10:12959` is published.
- Do not reset or retry while the replacement run is active. Inspect it through
  Run Detail first. If it fails, capture the exact stage status, Master terminal
  evidence and Rule JSONL health before deciding on recovery.
- Terminal Step4-Step6 acceptance, state-doc finalization and old release cleanup
  remain pending. No terminal success is claimed in this checkpoint.

### Changed files and verification

- Release/config tests: `config/wgs_releases.yaml`,
  `backend/tests/test_wgs_release_catalog.py`,
  `scripts/tests/test_wgs_runtime_gate.py`, and the frontend release fixture.
- Contracts/state: `docs/05_API_CONTRACT.md`, deployment/runtime/design docs,
  `CURRENT_STATE.md`, `TASKS.md`, `SERVER_INFO.md`, and this handoff.
- Fresh BS10610 checks: release catalog `9 passed`, runtime gate `18 passed`,
  Compose config exit 0, fixed network checker exit 0, no Airflow import errors,
  and `/api/health` returned `ok`.
- Supplemental fixed-Node focused frontend run: `WgsProductionUi.test.tsx`
  `4 passed`. `git diff --check` passed.

Not run: the full backend suite, full frontend suite/build and terminal real-WGS
acceptance were not repeated at this checkpoint. Production code did not change
after the previously deployed r3 release; the remaining evidence depends on the
currently active Step1-Step6 run. Do not report this run as successful until its
terminal API, Rule/Master evidence and result-delivery gates are all verified.

## 2026-09-01 - Codex - T146真实运行阻断与安全停用

### Outcome

- T146 release已部署，分析目录确认使用Airflow runtime下的
  `WGS_Clinical/<batch>`；旧`/sg2/.../wgs_test/WGS_Clinical`目录未被使用。
- 修复并部署Step3 stdout解析：kubectl提示可位于JSON前，最后一个合法JSON仍执行
  严格schema校验。BS10610 scripts全量`22 passed`。
- 补齐恢复门禁：execution或runtime adapter关闭时，resume/rerun_failed在修改attempt
  或调用Airflow前返回409；聚焦后端测试`14 passed`。生产HTTP复核返回
  `WGS_EXECUTION_DISABLED`，attempt保持7且没有attempt 8 DagRun。cancel不受影响。
- 真实attempt 7完成prepare、Step1和Step2提交，前端/API最终显示run `failed`；没有
  进入Step4-Step6，也没有发布结果。

### Root cause

node200 operator为cce-pipeline 0.8.1，其Step2在Master START前建立
`run_root/evidence/<run_id>/jobs.ndjson`。冻结profile解析出的Master镜像仍为
cce-pipeline 0.7.0系列；其启动脚本拒绝任何缺少`config/run-id`的既有run目录，
因此立即退出。日志已保存在task-specific、mode 0600 evidence目录；不得复制患者
信息到Git或普通日志。

### Cleanup and current safety state

- 失败Master、只含0字节manifest的精确SFS stub、attempt 7 batch lock和一次性诊断
  Job均已删除；这些空状态不可恢复且无业务结果。
- 已上传OBS FASTQ保留，OBS result为空；源FASTQ和Airflow DB运行/审计记录保留。
- BS10610与node200的`WGS_EXECUTION_ENABLED`、
  `WGS_RUNTIME_ADAPTER_ENABLED`均恢复false；`bio_wgs`重新paused，自动提交仍关闭。
- Docker网络仍是`192.168.199.0/24`、gateway`192.168.199.1`，只有
  `172.17.106.10:12959`发布。

### Next step

先发布或选择与0.8.1 Step2合同一致的Master镜像（或修正Step2在Master写
`run-id`前创建run root的顺序），更新WGS/profile后重新prepare并核对resolved
runtime。完成前不得再次打开gate或恢复批次。Airflow无需改分析目录，也不得在
runtime中热补丁冻结bundle。

## 2026-09-01 - Codex - T146 WGS cdee32c / cce-pipeline 0.8.1 manual run checkpoint

### Goal

将Airflow单一WGS release更新到commit
`cdee32c9d3c689f4af6ea8a0f7a8296f79c10a1d`，适配WGS prepare的普通批次参数，
清理指定旧批次状态，并在禁用态验收后通过前端/API手工提交一次真实CCE分析。

### Completed before deployment

- `wgs_releases.yaml`现只绑定`wgs-4.1.1-cdee32c`。node200只读核对同一WGS
  HEAD、允许的docs-only未跟踪文件和cce-pipeline 0.8.1。
- runtime gate从`WGS_20260825A_T7Hg38V4.1.1`提取`20260825A`作为
  `--batch`，完整值继续作为`--analysis-batch`。`--outpath`未改变，分析目录仍在
  Airflow runtime attempt下的`WGS_Clinical/<batch>`。
- Submit页在两个gate打开时显示生产创建动作；关闭时继续显示禁用提示。未增加版本
  选择器，也未改变create/submit两步权限合同。
- Compose scanner命令不再硬编码1800秒，而是读取受保护环境变量；生产值保持600秒。
- 3对FASTQ软链接已复制到Airflow受控intake，BS10610/node200均能看到6条有效
  链接；源FASTQ未删除。

### Authorized production cleanup

- 只处理`WGS_Clinical/WGS_20260825A_T7Hg38V4.1.1`。清理前Master/目标run
  label的Job和Pod均为0。
- 原Step0因历史bundle缺`jobs.ndjson`而fail closed。对task-specific可写bundle副本
  建立审计mirror前，再次核对目标run Job/Pod=0；原WGS仓库和旧bundle未修改。
- 已精确删除OBS result约173.8 GB和FASTQ约403.9 GB，两个前缀复核均为0 B。
- Step0 reset Job成功；一次性只读验证Job确认SFS run和linkage两个精确目录不存在。
- 同批次已完成的reset/cleanup Job和`run1`陈旧batch lock在核对无活动Pod后删除。
- 旧本地`/sg2/.../wgs_test/WGS_Clinical/<batch>`因NFS服务端拒绝当前客户端写入而
  未能删除；目录仍在但不属于新run输入或输出。Airflow不会读取或重建该路径。
- 删除操作不可恢复；OBS/SFS将由新run重新生成。task-specific清理证据保留在
  `/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/`下。

### Validation

```text
scripts/runner: 19 passed
backend: 227 passed
DAG unittest: 10 passed
Compose/network contract: 5 passed
frontend: 9 files / 31 tests
frontend: TypeScript and Vite production build passed
frontend image: airflow-demo/frontend:t146-wgs-cdee32c
frontend image ID: sha256:e5b2bb307aaa885661a71ff742734da52cf70d642308cfc4bcf893a09b289727
```

BS10610 Docker Hub mirror无法解析，远程多阶段frontend build在拉取
`node:22-bookworm` metadata前失败。改用Codex固定Node运行时、package-lock导入和
相同测试/build命令生成dist，再在BS10610基于已验收T145 nginx镜像无网络封装；
dist与镜像内三个文件SHA256一致。

### Current gate and next step

截至本checkpoint，`current`仍指向T145，两个execution gate仍false，`bio_wgs`
仍paused且尚未创建真实AnalysisRun。下一步是创建T146 release、修正受保护
`CCE_PIPELINE_BIN`、disabled Compose/API/network smoke，随后按已批准范围开启两个
gate并手工create/submit一个run。回滚只切回T145并重建应用服务；不得恢复已清理的
旧OBS/SFS状态、删除volume或重建Docker网络。

## 2026-08-30 - Codex - T145 scanner sparse persistence and observer lifecycle

### Goal

将混合`wgs-observer`拆为稀疏 T7 scanner 和仅对 Step3 活动任务工作的
event-driven observer，清理 demo 生成的 1830 条历史明细，保持所有分析门禁
关闭。

### Completed

- 新增 migration `20260830_0012`，精简 scanner singleton，分离 observer
  lifecycle/health，并增加活动查询索引。
- 新增带精确 confirm 的 cleanup CLI。它在同一事务中先拒绝任何已关联
  AnalysisRun 的 intake，再删除 batch/state。
- scanner 首次只记录基线；后续不保存 missing BarcodeStat、
  `bootstrap_ignored`或`waiting_barcode_stat`，只持久化三种业务状态。
- observer 先 LISTEN 再恢复`active/draining`，空闲时无超时轮询；Step3
  终态和`release_leases`请求最终 drain。Step1/Step5 sensor只同步精确传输文件。
- API/UI 分开 observer lifecycle 和 health，Dashboard 显示本轮目录数但不显示
  历史明细；Settings 也使用 T7 scanner 而不是旧 Airflow scanner DAG 投影。
- Compose 已切换为`wgs-intake-scanner`和`wgs-run-observer`，旧容器已移除；
  最小挂载和20m x 3日志轮转已在运行容器核对。
- 当前 release 通过后，已核对无容器挂载 T142/T143，并用无网络 root
  容器删除这两个旧 release。`releases/`现只保留 T145；该目录删除不可
  就地恢复，但代码可由 Git 提交重建。数据库备份和 Docker 镜像未删除。

### Production data operation

- 清理前查询：`wgs_intake_batch=1830`，linked rows=0，AnalysisRun=0。
- 备份：`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/
  t145-before-sparse-observer-20260830T045310+0800/biodemo.dump`。
- 备份 SHA256：`6cd7026498748c2e6ec231f01ebde7867c5bee3d2e97827d24b3bf36bc11b4e8`。
- cleanup 输出：`deleted_batches=1830`、`deleted_scanner_states=1`。
- 生产首次和第二次 sparse scan 都得到`scanned=1830`、created/updated/errors=0；
  intake details=0、AnalysisRun=0、Airflow DagRun=0。

### Deployment and validation

```text
release: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260830-wgs-4.1.1-observer-lifecycle-disabled-t145
frontend image: airflow-demo/frontend:t145-wgs-observer-lifecycle-disabled
frontend image ID: sha256:21468c83853c873559b4805c65f58b49cf72c86a4aca5f3a2415cea6db95579a
backend: 227 passed on the deployed release
DAG: 7 passed
Compose/network contract: 5 passed
frontend: 9 files / 30 tests; TypeScript and Vite production build passed
PostgreSQL: fresh migration and populated 0011->0012 + 1830-row cleanup passed
PostgreSQL LISTEN/NOTIFY: 4 concurrent attempt notifications arrived with exact identities
HTTP: health, admin login, scanner-state, empty intake and frontend static assets passed
observer idle: 10-minute log bytes=0
```

### Failed commands and correction

- 第一次完整 backend 容器测试将仓库挂在`/workspace`，但镜像的
  `PYTHONPATH=/app`使它误用镜像旧源码。显式设置`PYTHONPATH=/workspace/backend`后
  226 passed / 1 skipped。
- 第一次 populated 临时库 restore 由`airflow`拥有对象，生产应用用户
  `biodemo`无权读 Alembic 表。重建且用`pg_restore --role=biodemo`恢复后通过；
  正式库未受该失败影响。
- 两次远程 here-script 在`docker compose run`后续步骤被它的 stdin 消费；
  将 one-off Compose 命令与后续查询拆成独立 SSH 命令后通过。
- 追加验收时有一次 SSH banner exchange 中断；重新连接后仅执行幂等
  scanner/API 验收并通过。

### Safety and next step

`WGS_EXECUTION_ENABLED=false`、`WGS_RUNTIME_ADAPTER_ENABLED=false`、
`WGS_AUTO_DISPATCH_ENABLED=false`，`bio_wgs` paused。本次没有 OBS、CCE、WGS 分析、
volume 删除或 Docker 网络重建。真实 Step3 notification/Rule JSONL/Master 终态验收
仍属于 T140，需要单独批准。

## 2026-08-29 - Codex - T143/T144 T7 scan-only and Step4 repair

### Goal

Bind Airflow to WGS `V4.1.1` commit
`1656b5d7a6e2f24242c38149f6d1c92ac266cd37`, add a read-only T7 discovery
scanner and the cce-pipeline 0.7.1 Step4 CRAM repair contract, while keeping all
analysis execution and auto-dispatch disabled.

### Completed

- Updated the single release to `wgs-4.1.1-1656b5d`; no WGS source was copied
  or modified and cce-pipeline was not installed or upgraded.
- Added the T7 scanner to `wgs-observer`: exact chip/BarcodeStat/FASTQ pair
  rules, `-S\d+` exclusion, bootstrap protection, eligible fingerprint drift,
  PostgreSQL advisory lock and chip-only public projection. It runs in an
  independent thread on a start-to-start 1800-second clock.
- Added migration `20260829_0011` for nullable intake linkage, scanner state and
  Step4 maintenance actions. The intake foreign key is explicitly
  `ON DELETE SET NULL`.
- Added WGS-only intake/scanner APIs and Dashboard UI. Aggregate aliases
  `deployed`, `all` and omitted pipeline correctly use the T7 table; sample IDs,
  source paths and fingerprints are absent from the intake response.
- Added operator/admin-only, fixed-CRAM Step4 repair. The current attempt must
  have a `wgs-master-*` workload in `Succeeded`, the frozen bundle must declare
  `repair_groups.cram`, and the server derives the confirmation string. The
  same 18-task `bio_wgs` DAG uses maintenance mode without rerunning Step1-Step3.
- Added observer ingestion for Step4 repair status, frontend confirmation and
  disabled-runtime messaging. With either execution gate false, the API returns
  409 before creating a maintenance action, DagRun or SSH operation.
- Created the disabled release
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260829-wgs-4.1.1-t7-scan-disabled-t143`,
  migrated biodemo to 0011 and recreated only application services. Database/
  Redis volumes and the external Docker network were retained.
- Initial production bootstrap created 1817 `bootstrap_ignored` and 11
  `waiting_barcode_stat` rows. A later completed chip without eligible WGS was
  classified `no_new_wgs`. No analysis side effect occurred.

### Validation

```text
BS10610 backend: 217 passed, 1 skipped
BS10610 runner/evidence/logger scripts: 17 passed
WGS Airflow modules: 12 passed, 7 expected logger-interface skips
live Airflow: only paused bio_wgs, 18 tasks, zero import errors and zero DagRuns
frontend: 9 files / 30 tests; TypeScript and Vite build passed
frontend dist: local and deployed JS/CSS/index SHA256 values match
temporary PostgreSQL: 0010 -> 0011 -> 0010 -> 0011 passed
production PostgreSQL: 0011, nullable intake analysis_id, SET NULL foreign key
HTTP: login/release/scanner/intake/default Dashboard projection and static UI pass
network: 192.168.199.0/24, gateway 192.168.199.1; only 172.17.106.10:12959 published
execution: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false,
           WGS_AUTO_DISPATCH_ENABLED=false
```

The first full T7 scan took about 325 seconds because it enumerated all historic
FASTQs. A regression test and implementation change now skip FASTQ enumeration
for permanently `bootstrap_ignored` rows; the stable scan took about 1.4 seconds.
Another regression fixed the interval from “1800 seconds after completion” to
1800 seconds between scan starts.

### Two-cycle acceptance

The corrected observer started its stable baseline scan at
`2026-08-29 10:20:30.971949+00`. The two naturally scheduled cycles advanced to
`10:50:30.972362+00` (516ms) and `11:20:30.972623+00` (1216ms). Both retained
1817 `bootstrap_ignored`, 11 `waiting_barcode_stat` and one `no_new_wgs`, with
business run/attempt/maintenance and Airflow DagRun counts all zero. This gate
passed without reducing the 1800-second interval or manually invoking a scan.

### Corrections and failed commands

- The first observer design ran intake after evidence traversal, delaying
  bootstrap. Root cause: the clocks shared one loop. Intake now has an
  independent thread.
- The first schedule implementation waited 1800 seconds after a 325-second
  scan. Root cause: completion-relative sleep. It now subtracts scan duration.
- A full historical DAG discovery was mistakenly run against the partial T143
  staging tree; 12 missing legacy NIPT/WES files and two unavailable-pytest
  imports failed. The complete new release then passed all four WGS modules.
- One scripts command named a nonexistent old evidence test and ran no tests;
  rerunning the three current files passed 17 tests.
- The first release env update assumed `.env.wgs` lived inside the release and
  stopped before mutation. The protected env was located from Compose labels at
  `airflow-WGS/env/bs10610.wgs.env`, backed up, and safely updated there.

### Safety and rollback

No sampleinfo, analysis directory, OBS transfer, CCE workload or real Step4
repair was started. A pre-migration biodemo dump is retained as
`backups/t143-before-t7-scan-20260829.dump`; the protected env backup is
`env/bs10610.wgs.env.before-t143-20260829`. `current` now points to the T143
release. Roll back by recreating application services from T142 and
restoring its protected env values; do not delete volumes/network or downgrade
0011 after new scanner/maintenance data exists.

## 2026-08-28 - Codex - T142 single-release disabled integration

### Goal

Replace the Airflow-owned WGS candidate snapshot with one release contract that
points to shared WGS 4.1.1 commit
`1778fcabd99b5253aa90cd410112dc2f78e0c51a`, while keeping all execution
disabled.

### Completed

- Implemented the schema-3 single release catalog for
  `wgs-4.1.1-1778fca`. BS10610 and node200 resolve the same shared repository
  commit; the only untracked WGS item is an allowed `docs/` report.
- Changed runtime requests to `wgs-runtime.request.v3`, removed snapshot paths
  and Airflow-side cce-pipeline version/wheel checks, and made prepare validate
  the fixed node200 WGS repository before creating a frozen batch binding.
- Added migration `20260827_0010`, release-bound observer/Rule timing behavior,
  `GET /api/wgs/release`, and read-only release/runtime fields in the frontend.
  Historical ETA selection now filters by release before applying the latest-20
  limit.
- Removed obsolete candidate-copy and snapshot prepare-adapter scripts and
  replaced the stale DAG test with the current 18-task paused `bio_wgs` graph.
- Published
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260828-wgs-4.1.1-single-release-disabled-t142`
  and atomically switched `current`. The external Docker network and database/
  Redis volumes were retained.
- Migrated production biodemo from `20260826_0009` to `20260827_0010`; retained
  one administrator and zero run state. The retained rollback dump is
  `backups/t142-before-single-release-20260828T002349+0800`.
- Packaged the tested frontend dist offline as
  `airflow-demo/frontend:t142-wgs-4.1.1-single-release-disabled` at image ID
  `sha256:59cbfce7c8537c3a943f6c35a1ccea8bcfe6dc2ae1bba02fbe0d6ff6bb8b0903`.
- Diagnosed node200 SSH command hangs to unconditional conda initialization in
  `~/.bashrc`. Backed up the file as
  `~/.bashrc.before-airflow-t142-20260828`, kept the WGS/local/Git PATH
  available, and returned before conda setup for noninteractive shells.
- After final smoke, irreversibly removed only the exact T141 release and the
  redundant failed-attempt T142 backup with no-network root containers.
  `releases/` now contains only T142; `backups/` retains only the successful
  pre-migration dump named above.

### Validation completed

```text
BS10610 isolated backend full suite: 202 passed
BS10610 scripts suite: 16 passed
BS10610 Airflow DAG: 5 unittest tests, py_compile and DagBag all passed;
bio_wgs has 18 tasks and is paused at creation
frontend: 8 files, 27 tests; TypeScript/Vite production build passed
temporary PostgreSQL migration smoke: 20260826_0009 -> 20260827_0010 passed;
the administrator sentinel and migrated release fields were preserved and the
exact temporary database was removed
production migration: revision 20260827_0010; one admin; zero sessions, runs,
attempts, snapshots, issues, transfers, Rule rows, workloads, audit or cursors
HTTP smoke: anonymous release API 401; admin login 200; disabled run create 201;
Run Detail 200 with release 1778fca; submit 409; exact DB/workdir cleanup passed
Airflow live: only paused bio_wgs; no import errors; DagBag 18 tasks, no schedule
node200: hostname t640; fixed repository HEAD 1778fca; allowed docs-only drift;
invalid forced-command returned 1 without timing out or starting a stage
network: external 192.168.199.0/24 retained; only 172.17.106.10:12959 published
```

Initial validation corrections are recorded for reproducibility: the backend
staging container needed the whole repository mounted so it could read the
catalog; the Airflow image has no pytest, so its project tests used unittest,
py_compile and the installed DagBag; the migration smoke inherited the running
backend environment without printing credentials.

### Deployment corrections

- The first deployment attempt migrated successfully but a Bash `sed`
  expression expanded `$#` and failed before changing the frontend env. The
  rollback trap restored T141, downgraded biodemo to 0009, restored its runtime
  gate and recreated services; health and clean DB state were verified before
  the corrected second attempt.
- The HTTP smoke cleanup first stopped on a root-owned synthetic manifest.
  Database/session/audit cleanup had already completed. A no-network root
  container mounted only the exact synthetic directory and removed it; no
  production input or result was touched.
- A supplemental DagBag probe first used the Snakemake venv `python` and then an
  Airflow-version-incompatible `DAG.schedule` attribute. The accepted probe
  used `/home/airflow/.local/bin/python` and `schedule_interval`; live Airflow
  CLI independently showed one paused DAG and zero import errors.

### Safety and rollback

Both execution gates remain false and `bio_wgs` remains paused. No OBS/CCE
operation, WGS source edit or cce-pipeline install/update occurred. Application
rollback is reconstruction from Git plus the retained biodemo dump after the
required single-release cleanup; never downgrade migration 0010 after new
release-bound rows exist.

### Tests not run

No real Step1-Step6, OBS transfer, CCE Master/Worker, Rule evidence bridge,
result delivery or four-run concurrency test ran. Those remain T140 and require
separate approval to enable both gates and submit a minimal real batch.

## 2026-08-27 - Codex - T141 WGS 4.1.1 Master Rule evidence bridge

### Goal

Connect the logger already present in the pinned CCE Master image to the
Airflow observer without changing WGS Rules, cce-pipeline, Worker images or
normal Snakemake logs. Keep real execution disabled.

### Completed

- Confirmed the pinned Master digest runs Snakemake `9.24.0+biosan1`, contains
  `snakemake_logger_plugin_rule_status`, adds it only to formal
  `cloud_wgs_all`, preserves `analysis.log`, and writes schema-1 events with
  `attempt-N` under SFS `rule-status/raw/*.jsonl`.
- Corrected observer validation to accept `attempt-1` while retaining exact
  binding identity checks.
- Added Step3 incremental Rule JSONL transfer through node200 kubectl. It
  mirrors only complete lines, tracks a byte offset per logger stream, and
  writes to the existing shared `cce-evidence/<analysis_id>/attempt-N` spool.
- Because node200 does not mount `/workspace` SFS, added a terminal one-shot
  reader Job. It reuses the pinned Master image and service account, mounts
  only the workspace PVC read-only, copies the final increment, and is then
  deleted. It is not exposed by `/pods`; Worker Pods remain out of scope.
- Bridge failures set `monitoring_health=degraded` without changing the WGS
  exit code. Missing terminal Rule events remain `unknown_interrupted`.
- Published disabled release `20260827-wgs-4.1.1-disabled-t141` on BS10610,
  updated the shared node200 runtime scripts atomically, and recreated only
  backend/observer. `releases/` contains only T141.

### Verification

- BS10610: backend `193 passed, 1 skipped`; bridge/runtime and other script
  tests `17 passed`; no-bytecode source compile `syntax-ok`.
- Local script-only bridge suite: `5 passed`; `git diff --check` passed.
- Pinned Master image `/opt/python/3.11.9/bin/python3 --version`: Python 3.11.9.
- No real OBS transfer, CCE Master, reader Job or WGS analysis was started.
- HTTP health returned `ok`; observer polls with zero errors; release/runtime
  script SHA256 values match; Airflow lists only paused `bio_wgs` with no
  import errors. Both host and node200 execution flags remain false.

The first staging `compileall` check used a read-only bind mount and therefore
failed while trying to create `__pycache__`; this was an invalid write-mode
check, not a syntax failure. Imported pytest suites passed, and the corrected
no-bytecode source compile check returned `syntax-ok`. The first inline form of
that correction was rejected by nested PowerShell/SSH quoting; piping a
CR-safe Python checker over stdin produced the accepted result.

The first deploy one-liner also let local PowerShell expand remote Bash
variables and stopped on its first `mv`; read-only checks confirmed that no
switch or service change occurred. The corrected deployment used the
CRLF-safe stdin Bash pattern. A subsequent audit found that the initial
staging copy had preserved the `current` symlink, so T141 was temporarily a
symlink alias and T139's directory already held the new files. With services
healthy and `current` fixed on the exact T141 name, the alias was removed and
the same directory inode was renamed from T139 to T141. No recursive deletion,
volume, network, database, WGS data, OBS object or CCE workload was involved.

### Changed files

- `backend/app/wgs_observer.py` and its regression tests.
- `scripts/wgs_runtime_gate.py`, `scripts/wgs_evidence_bridge.py` and their
  tests.
- WGS DAG/Snakemake/deployment/integration docs plus `CURRENT_STATE.md`,
  `TASKS.md` and this handoff.

### Tests not run and why

- No live kubectl exec against a running WGS Master and no terminal reader Job
  were run because both execution gates are false and T140 has no separate
  real-batch approval.
- Therefore live retry events, Master OOM/interruption and four-batch evidence
  isolation remain acceptance work, not claimed results.

### Current git status

- Worktree: `D:/pipeline/airflow-demo-worktrees/T129-wgs-only`.
- Branch: `codex/platform/T132-wgs-runtime-integration`.
- On 2026-08-27 the user authorized committing the T135-T141 implementation
  and synchronizing it to `main`; the resulting Git revision is reported in
  the delivery response.

### Remaining gate

T140 still requires separate approval. Its first real batch must prove live
incremental reads, the post-exit reader, retry/terminal Rule events, Master
interruption, degraded monitoring, delivery MD5 and cleanup behavior before
unpausing `bio_wgs`.

### Next recommended task

Obtain explicit T140 approval, keep `bio_wgs` paused, enable the two gates only
for one approved minimal batch, and validate the full Step1-Step6 chain plus
live Rule bridge/reader behavior before considering unpause.

### Rollback

Restore the prior disabled application files and keep both execution flags
false plus `bio_wgs` paused. There is no separate on-host T139 rollback release;
reconstruct application files from the uncommitted worktree and pinned images
if rollback is required. Do not delete WGS SFS/OBS data, CCE workloads,
database volumes or the fixed Docker network.

## 2026-08-26 - Codex - T135-T139 WGS 4.1.1 disabled production release

### Goal

Implement the WGS-only Airflow control plane against the audited WGS 4.1.1
contract, clear the former demo runtime state, and publish a production-shaped
but execution-disabled release on BS10610. Real OBS/CCE execution remains out
of scope until a separate T140 approval.

### Completed

- Frozen the clean WGS source at commit
  `3489b3958869e5cfab983aca1eb9c7f158c06dff` and created snapshot
  `wgs-v4.1.1-candidate-3489b39-64d50022`; its manifest SHA256 is
  `9b1bfe00ebf7e8ed693f1e9eb17ec05174aa43b04900802d67e54f50dc27f52e`.
  Sensitive `prepare/config.yaml` is not in the snapshot.
- Fixed cce-pipeline 0.5.0, wheel/source/profile/Master identities and confirmed
  the formal node200 WGS Python environment owns cce-pipeline. No cce-pipeline
  source was changed by this task.
- Replaced the three old WGS DAG sources with one manual, paused `bio_wgs` DAG
  containing 18 project tasks for prepare and WGS Step1-Step6. There is no
  FASTQ hash task, post-upload FASTQ verify task, fixed Master slot, automatic
  intake, local/SGE execution, Step0, Step7 or Step8.
- Added the WGS 4.1.1 runtime adapter, async stage workers, reschedule sensors,
  transactional OBS transfer lease, Master-only Kubernetes evidence, Rule
  cursor/reconciliation, delivery gates, database migration, compatible APIs
  and observer ingestion.
- Updated the frontend to WGS-only manual submission and 4.1.1 Run Detail.
  Transfers explicitly show stage-only state when byte/speed/ETA detail is not
  available; `/pods` and the UI expose only the Master workload.
- Fixed offline frontend packaging so the release image deletes inherited demo
  static assets before copying the WGS build. The running nginx container now
  contains only the current JS/CSS pair; image ID is
  `sha256:f64b1ed3b2287b5cfa8b12d0a23732339a84a1aeed49a4219de671c2f10a32e6`.
- Per the user's final SSH choice, Airflow directly runs
  `ssh -tt -F /opt/airflow/ssh/config wgs-node200 ...`. The protected config
  fixes host, user, RSA identity, known_hosts and strict verification. The RSA
  key is stored outside release/Git/images at
  `/home/chenjc/.config/airflow-wgs/ssh-node200/id_rsa`, owned by UID 50000 and
  mounted read-only. No server-side authorized_keys forced-command key is used.
- Verified the real shared runtime mapping:
  BS10610 `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime` maps
  to node200 `/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime`.
- Published disabled release `20260826-wgs-4.1.1-disabled-t139` and switched
  `current` to it. Migrated biodemo to `20260826_0009`; preserved one admin,
  cleared sessions and all demo runtime/audit data, cleared Redis, and removed
  old WGS DAG metadata. No database/Redis volume or Docker network was reset.

### Changed areas

- `dags/bio_wgs.py`, retired WGS DAG files and DAG contract tests.
- `scripts/wgs_runtime_gate.py`, runtime/snapshot/evidence helpers and tests.
- `backend/app/`, migration `20260826_0009`, backend tests and release image.
- `frontend/src/`, frontend tests/styles and offline release packaging.
- `docker-compose.wgs.yaml`, `.env.wgs.example`, release Dockerfiles.
- WGS design/API/DB/DAG/frontend/security/deployment docs plus
  `CURRENT_STATE.md`, `TASKS.md` and this handoff.

### Commands and verification evidence

- Backend full suite on BS10610: `193 passed`.
- Node/runtime scripts: `14 passed`.
- Deployment contract: `5 passed`; live Airflow worker DAG contract passed with
  exactly 18 tasks. `airflow dags list` returned only paused `bio_wgs` and
  `airflow dags list-import-errors` returned `[]`.
- Frontend full suite: 8 files, 27 tests; TypeScript and Vite production build
  passed. The deployed offline assets match the tested build SHA256 and passed
  HTTP smoke.
- Airflow worker command
  `ssh -tt -F /opt/airflow/ssh/config wgs-node200 hostname` returned `t640`.
  The pinned ED25519 host fingerprint is
  `SHA256:KKSrhbpZdPlBe7ej63ZaYhvYwWhQpdEnGejD59NGMv4`.
- Disabled synthetic smoke: create returned 201, submit returned 409, only the
  input manifest was created, and no OBS/CCE action ran. Synthetic DB records
  and exact test directories were then removed.
- Compose/network/HTTP/auth checks showed all services healthy, anonymous API
  access denied, external subnet `192.168.199.0/24`, and only
  `172.17.106.10:12959` published.
- Final database checks used `ON_ERROR_STOP=1`: biodemo has one admin, one idle
  OBS lease row, zero sessions/runs/attempts/samples/transfers/Rule events/Rule
  states/workloads/artifacts/QC/audit/cursors/actions/issues/snapshots/intake;
  Airflow has zero DAG runs/task instances.
- Release secret scan found no key/config filename or private-key header and
  confirmed the WGS snapshot has no `prepare/config.yaml`.

### Tests not run and why

- No real WGS, OBS transfer, Master Job, Worker Pod or Step1-Step6 command was
  run because both execution gates remain false and T140 lacks approval.
- No production Rule-event end-to-end test was run because the clean WGS
  4.1.1 source does not yet invoke a Rule JSONL logger.
- BS10610 could not rebuild the frontend test image because its configured
  external Docker mirror DNS was unavailable. The full frontend suite/build
  ran with the bundled local Node runtime, followed by checksum-controlled
  offline packaging and BS10610 HTTP smoke.

### Verification corrections

- Compose validation first failed because the external production env file
  intentionally lacks newly added candidate-only variables. It passed after
  supplying non-secret, test-only placeholders for render validation; running
  services were not recreated by that check.
- The first backend rerun mounted only `backend/`, so one catalog test could
  not find repository-root `config/wgs_releases.yaml`; mounting the whole
  release read-only produced `193 passed`.
- Full scripts testing exposed two stale assertions: the Rule logger test still
  expected an old snapshot suffix, and the DAG contract still expected
  `SSHHook/ssh_conn_id`. Both tests were corrected to the fixed 4.1.1 snapshot
  and direct `ssh -tt -F` contract; final suites passed.
- A broad historical DAG unittest invocation used a fresh image context without
  the running container's installed Airflow environment and included retired
  NIPT/PGTA/WES tests, so it was not a valid WGS-only acceptance. The final
  dynamic check ran inside the actual Airflow worker with its pinned Python.
- Post-frontend-recreate listing initially used unsupported BusyBox `find
  -printf` and a malformed nested quote. The corrected `ls`/`sha256sum`/HTTP
  checks passed and showed only the two current assets.
- The first database-count query lost SQL string quotes in nested shell
  parsing, and psql did not stop by default. The accepted rerun used stdin SQL
  plus `ON_ERROR_STOP=1` and returned the zero-state counts above.

### Current git status

- Worktree: `D:/pipeline/airflow-demo-worktrees/T129-wgs-only`.
- Branch: `codex/platform/T132-wgs-runtime-integration`.
- The implementation remains intentionally uncommitted at the user's request.

### Risks and blockers (superseded by T141 where noted)

- The node200-local Snakemake `9.23.1` observation is not a CCE blocker: formal
  WGS Snakemake runs inside the pinned Master image. T141 confirmed its actual
  version and logger contract.
- The former missing-logger blocker is superseded by T141. Live bridge and
  terminal-reader behavior still require the separately approved T140 batch;
  Airflow must not fabricate Rule success when events are absent.
- Direct SSH with the existing RSA has broader account scope than a dedicated
  authorized_keys forced-command key. Risk is reduced by strict host key,
  protected config/key mounts and the explicit stage gate, but key rotation and
  access audit remain operational responsibilities.

### Final cleanup authorization and scope

The user explicitly required the former demo state to be cleared and only the
latest Airflow WGS release retained. Before deletion, `current` resolved to
`releases/20260826-wgs-4.1.1-disabled-t139`. The following resolved targets are
old Airflow integration artifacts, not production WGS sources, inputs or
results, and are approved for exact removal after final disabled smoke:

- `releases/20260812-wgs-observer-553be3f`
- `releases/20260812-wgs-only-phase1`
- `releases/20260812-wgs-orchestration-t131-candidate`
- `backups/development-wgs-before-wgs-v4.0.1-dev-6cb1255-53453d5d-20260818T161125+0800`
- `backups/t139-before-production-cleanup-20260826T232915+0800`
- `backups/wgs-host.env.before-qc-root-fix.20260715_102200`

Removal is intentional and irreversible. It eliminates old releases, the
pre-cleanup demo database dump and obsolete Airflow integration backups. It
does not authorize volume deletion, Docker prune, network changes, WGS source
deletion, or production data deletion.

Cleanup result: all six exact targets were removed. `releases/` now contains
only `20260826-wgs-4.1.1-disabled-t139`; `backups/` is empty. The first attempt
removed two releases and stopped on a root-owned `.pytest_cache/.gitignore` in
the third release. A second attempt removed that cache but stopped on another
root-owned `index.json`. Read-only checks confirmed that the target was not
`current` and was not mounted by a running container. The final retry mounted
only that exact old release into a no-network, UID-0 container, removed its
remaining children, then removed the empty release directory and the exact
backup targets. No broad prune, wildcard deletion, volume deletion or network
change was used.

### Next recommended task

T140 stays blocked only on separate approval and real-runtime acceptance. Keep
both gates false and `bio_wgs` paused until one minimal batch validates the
running-Master bridge, terminal reader, Rule reconciliation and delivery chain.

### Rollback

Set both gates false and keep `bio_wgs` paused. After final cleanup there is no
on-host old release or demo database backup to restore; reconstruct from Git
and pinned image/snapshot identities if application rollback is required.
Never delete PostgreSQL/Redis volumes, the external network, WGS source,
production inputs or results. The RSA/config can be unmounted and removed from
the exact protected node200 SSH directory without touching other identities.

## 2026-08-26 - Codex - T135 WGS 4.1.1 integration documentation baseline

### Goal

Freeze the audited WGS 4.1.1 Airflow integration design before changing any
DAG, backend, observer, frontend, Compose, database or runtime implementation.
Keep the current BS10610 execution gates and services unchanged.

### Completed

- Added the canonical WGS 4.1.1 integration plan at
  `docs/25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md` using clean WGS commit
  `29388a81b182011a68d400adeb178ed0de147a49`, cce-pipeline 0.5.0 and profile
  `wgs-4.1.1-r1`.
- Documented the target single paused `bio_wgs`, WGS Step1-Step6 mapping,
  node200-only operator boundary, stage-only transfers, Rule JSONL,
  Master-only Kubernetes evidence, delivery gates, RBAC and disabled rollout.
- Replaced the runtime status document with the 2026-08-26 audit: Airflow is
  still a 4.1.0 candidate, BS10610 still loads three paused legacy DAGs, and
  cce-pipeline 0.5.0 is not installed in the formal WGS environment.
- Added T135-T140 task cards and a current-state entry. The sequence covers
  contract/security freeze, runner/DAG, backend/observer, frontend, disabled
  deployment and separately approved real acceptance.
- Marked WGS 4.0.1/4.1.0 sections in the engineering, DB, API, frontend, DAG,
  Snakemake, deployment, Phase 1 and WGS design documents as historical or
  pending replacement, with links to the canonical 4.1.1 plan.
- Recorded the credential externalization/rotation, cce-pipeline provenance
  and Master image provenance issues without recording sensitive values.

### Changed files

- `docs/25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md`
- `docs/24_WGS_RUNTIME_INTEGRATION_DEVELOPMENT_STATUS.md`
- `docs/22_WGS_ONLY_LOCAL_CCE_PLATFORM_DESIGN.md`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/23_WGS_CLOUD_ORCHESTRATION_PHASE1.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run and results

- Read-only WGS 4.1.1/cce-pipeline/profile/Master/Airflow/DB audit was completed
  before this documentation task; no remote mutation was made.
- Full worktree `git diff --check`: PASS.
- New-document trailing-whitespace check: PASS.
- Relative Markdown link target check across all touched documents: PASS.
- Canonical identity and execution-gate token check: PASS.
- Historical-banner/canonical-link check across legacy WGS contract documents:
  PASS.
- Credential-like value scan across new/state/task documents: PASS.

The first documentation check correctly failed on Markdown hard-break trailing
spaces. The spaces were removed without changing content. A second check then
found the runtime adapter gate was described semantically but not written as
the exact token `WGS_RUNTIME_ADAPTER_ENABLED=false`; the canonical plan was
made explicit and the full acceptance check passed.

### Tests not run and why

- Backend pytest, frontend tests/build, DAG import, Compose rendering,
  migrations and runtime adapter tests were not run because this task is
  strictly doc-only and changes no implementation.
- No BS10610 service smoke, node200 package installation, OBS transfer, CCE
  Job/Pod or real WGS workflow was run.

### Current git status

- Worktree: `D:/pipeline/airflow-demo-worktrees/T129-wgs-only`.
- Branch: `codex/platform/T132-wgs-runtime-integration`.
- The worktree already contained broad uncommitted T131-T133 code and document
  changes before this task. This task preserved them and added only Markdown
  changes listed above.
- No Git commit was created, as required.

### Risks

- The current Airflow runtime code and focused tests still encode WGS 4.1.0,
  older cce-pipeline CLI/terminal contracts and an exact 15-task graph.
- The formal node200 WGS environment still lacks cce-pipeline 0.5.0.
- A tracked WGS prepare configuration must be externalized and its credential
  rotated before any snapshot or real run is approved.
- The profile Master RepoDigest requires trusted WGS 4.1.1/runtime provenance
  or a corrected image release before production execution.

### Open questions

No product decision remains open for T135-T139. Fixed choices are manual intake,
stage-only transfer visibility, administrator preservation during demo cleanup,
Master-only Pod visibility and disabled/paused first release. T140 still
requires separate approval for a real batch.

### Next recommended task

Start T135 only: create the allowlist WGS 4.1.1 snapshot and provenance/security
contract in an isolated worktree. Do not start T136 runtime changes until the
snapshot, protected prepare config, wheel provenance and Master image gate are
reviewed.

### Rollback notes

This task changes Markdown only. Revert the T135 documentation hunks and remove
the untracked document 25 if the design is replaced. No service, data, image,
database, network, volume, OBS or CCE rollback is required.

## 2026-08-24 - Codex - T133 Master logger overlay image follow-up

### Goal

Record the remaining cce-pipeline changes, fix the node 200 address, determine
the `wgs-cloud-delivery` boundary, and build an immutable logger overlay on the
confirmed r2 Master image.

### Completed

- Committed doc-only cce-pipeline follow-ups `d830d1f` and `916c7c1` on
  `jiucheng/cce-pipeline-production-contract`. It specifies the two-column
  FASTQ source contract, transfer progress spool, Master logger invocation and
  separate delivery Worker image, then corrects the Master base versions and
  records the logger image digest. No cce runtime code changed.
- Fixed `WGS_RUNNER_200_HOST=172.17.61.200` in the Airflow candidate Compose
  and example environment; execution flags remain false.
- Confirmed `wgs-cloud-delivery@sha256:d6d06ff...` is used only by
  `cloud_stage_cram`, `cloud_package_results` and `cloud_finalize_delivery`.
  It remains unchanged and receives neither cce-pipeline nor the logger.
- Rebased the logger-aware Master runner onto the current cce-pipeline script,
  retaining dynamic storage roots, attempt handling and cce state modules.
- Directly inspected the exact r2 base digest `834b78c5...`: it contains
  Snakemake `9.24.0+biosan1`, Kubernetes Executor `0.6.4+biosan3`,
  cce-pipeline `0.2.0`, and the Master/cleanup/reset lifecycle scripts.
- Revised the Dockerfile/build script so the overlay installs only
  biosan-jsonl 1.0.0 and the logger-aware Master runner; it does not reinstall
  cce-pipeline or replace cleanup/reset.
- Built and pushed on BS10610:
  `wgs-cce-master:cce-pipeline-0.2.0-schema3-20260824-r2-biosan-jsonl-v1`,
  RepoDigest
  `sha256:5d1d977fb21e541582230f31540cc8cd4f7a183e417b41e508162060cfcdf211`.

### Verification

- Red tests first proved the old image contract incorrectly expected biosan4,
  reinstalled cce runtime, and that the old logger runner lacked current cce
  state contracts.
- The pushed tag and RepoDigest both passed container smokes for Snakemake,
  Executor, cce-pipeline, logger plugin registration, lifecycle scripts and
  formal-command logger arguments.
- Build/push provenance, wheel/context SHA256, image inspect, push log and both
  smoke logs are under
  `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/logger-integration/r2-biosan-jsonl-v1`.
- Full WGS worktree suite after the logger-overlay change: 28 PASS.
- cce-pipeline suite at doc-only head `d830d1f`: 65 PASS.
- Master/build shell syntax: PASS.
- Airflow node-address deployment-contract Red/Green tests: 2 PASS; final
  BS10610 containerized deployment-contract suite: 4 PASS using the exact
  running Airflow image ID.
- cce follow-up document `git diff --check` and content gates: PASS before
  commit.

The first remote Airflow test command named the absent generic
`airflow-demo/airflow:0.1.0` tag and Docker attempted an external pull that
timed out. No image was installed or changed. The test was rerun successfully
with the exact image ID used by the running scheduler.

A final cce-pipeline test attempt initially used system Python 3.8 without
`PYTHONPATH=src` and failed during collection. Rerunning the documented command
with `/bi/software/mamba/envs/WGS/bin/python` and `PYTHONPATH=src` passed 65/65.
Two Compose evidence renders also stopped before rendering: first because the
candidate lacked a `validation/` directory, then because the production env
does not define new candidate-only host roots. The final render used explicit
non-secret validation paths, passed, and resolved every runner connection to
`172.17.61.200`.

### Remaining blockers

The image blocker is resolved. Real execution remains blocked by the
cce-pipeline two-column FASTQ manifest mismatch, missing structured transfer
progress spool, profile publication/disabled-mode acceptance, and the explicit
approval gate for a minimal real batch. No profile was activated and no
CCE/OBS run started.

### Rollback

Revert local Airflow candidate edits normally. In the WGS logger worktree,
restore only the uncommitted Master image/runner/test files if the overlay
approach is abandoned. The pushed digest is immutable and can simply remain
unused; do not retag an active profile to it. Revert cce documentation commits
only if their handoff contract is no longer wanted. No running service rollback
is needed.

## 2026-08-24 - Codex - T133 WGS 4.1.0 logger and Airflow implementation

### Goal and scope

Implement the WGS workflow and Airflow portions first: offline CCE Rule logger,
single WGS DAG, node 200 restricted runner, observer/API/frontend projection,
and confirmed cce-pipeline CLI integration. Do not start a real CCE analysis,
modify the confirmed cce-pipeline worktree, recreate BS10610 Compose, reset a
database/volume/network, or enable execution.

### Completed

- Created isolated WGS worktree
  `/mnt/biodevrwbi/33.chenjiucheng/project/worktrees/wgs-4.1.0-airflow-logger`
  from clean base `b72ebea6616f79432c5ee6378f38f80b53575fa1`.
- Implemented `snakemake-logger-plugin-biosan-jsonl` 1.0.0 and connected it
  only to formal CCE `cloud_wgs_all`. Standard stream/`analysis.log`, local,
  SGE, preflight, unlock and final dry-run remain unchanged.
- Produced immutable Airflow snapshot
  `wgs-v4.1.0-candidate-b72ebea-2178aa5b`, manifest SHA256
  `5f3aa5c0496b1224a8ae61799550392d37ff8269a4596cdc2a9a00e80dcc4631`.
  Host-only prepare config and legacy credential/publication helpers were
  excluded.
- Replaced the WGS publication contract with one paused `bio_wgs` DAG and 15
  tasks. Removed old WGS DAG files/mounts, FASTQ MD5 tasks, upload verification,
  fixed Master slot allocation and Worker Pod reconciliation.
- Reworked `wgs-runtime` for node 200 and confirmed cce-pipeline
  `prepare/validate/run` actions using an explicit immutable profile revision.
- Extended observer ingestion for `rule-event.v1`, ISO time, sequence and
  supplied event IDs; added non-fatal logger degraded health; limited evidence
  bridge/API/UI to the batch Master.
- Updated catalog, Compose connection contract, frontend workflow task set,
  state/design/API/DB/frontend/security/deployment documents.

### Confirmed cce-pipeline

Path:
`/mnt/biodevrwbi/33.chenjiucheng/project/worktrees/huawei-cloud-runtime-production-contract`

- Branch: `jiucheng/cce-pipeline-production-contract`
- Clean commit: `02adcecd85cc052b81330181a17d0377a742c39f`
- Profile revision: `revisions/wgs-4.1.0-schema3-20260824`
- Revision digest:
  `2a1bb7ffdc201eefe3b3feb9cd210e4bb118493badcfe673a294cb9997a7a6a3`
- Candidate Master image digest:
  `834b78c5dabd90b2e8f39a569f730fb3b4d0c94c684b9bcb0a1caa938d0f9a90`
- Repository evidence explicitly says `candidate-not-activated`; Airflow does
  not use an active-profile symlink.

### Validation

- WGS isolated worktree: 27/27 unittest PASS; bash syntax and `git diff
  --check` PASS.
- Immutable WGS snapshot: manifest verification PASS; 27/27 tests PASS; no
  private prepare config or HTTP callback token found.
- cce-pipeline: 65/65 unittest PASS from clean commit.
- Backend observer/runtime/catalog/platform focused run: 46 PASS after final
  catalog and WGS-only API changes.
- Node scripts (`prepare`, runtime gate, evidence bridge, transfer wrapper,
  snapshot sync): 12 PASS.
- Airflow image import: DAG ID `bio_wgs`, 15 tasks, paused-on-creation true.
- Compose/DAG publication contract: 4 PASS.
- WGS frontend focused tests: 7 PASS; local `tsc -b` and Vite production build
  PASS. The produced bundle is a compile check only and was not deployed.
- Full backend legacy run: 215 PASS, 30 FAIL, 1 SKIP. Failures are old
  NIPT/PGTA/WES and superseded WGS contracts in the intentionally WGS-only
  branch; do not use it as the focused WGS acceptance result.
- Full legacy frontend capability run still fails old NIPT/multi-product
  assertions that are outside the WGS-only release contract. A remote frontend
  image build was not possible because BS10610 Docker mirror DNS failed to
  resolve `node:22-bookworm`; the existing frontend was not replaced.

### Blocking issues

1. cce-pipeline `02adcecd` requires a four-column
   `source,target,size_bytes,md5` FASTQ manifest, while WGS 4.1.0 emits two
   columns and the approved Airflow design forbids calculating FASTQ MD5. The
   runtime gate intentionally fails rather than reintroducing a hash task.
2. Resolved: candidate cce-pipeline Master digest `834b78c...` intentionally
   provides Snakemake `9.24.0+biosan1`, Executor `0.6.4+biosan3`, and
   cce-pipeline `0.2.0`. Logger overlay digest `5d1d977f...` preserves them.
3. Resolved in the later follow-up above: node 200 is `172.17.61.200` and now
   populates `WGS_RUNNER_200_HOST`.
4. cce-pipeline captures obsutil output internally and currently exposes no
   live progress spool; final action JSON is available, but bytes/speed/ETA
   cannot yet be streamed through the existing transfer UI without a small
   cce-pipeline progress hook.

### Safety/current runtime

`WGS_EXECUTION_ENABLED=false`, `WGS_RUNTIME_ADAPTER_ENABLED=false`, and the
candidate `bio_wgs` is paused. Current BS10610 Compose, PostgreSQL/Redis
volumes, external Docker network and frontend service were not changed. No OBS
object, CCE Job/Pod or production result was created, deleted or modified.

### Next action

Reconcile the remaining cce-pipeline FASTQ manifest interface, add transfer
progress output, publish a new immutable profile revision referencing the
logger overlay, rerun disabled-mode integration, then deploy as a new candidate
release with both execution flags still false. Only after one explicit mock
and one minimal real acceptance may `bio_wgs` be unpaused.

### Rollback

No running service rollback is required. Remove only the new candidate release
or restore the previous `current` symlink if a later deployment is attempted;
the upstream WGS and cce-pipeline worktrees remain intact. The Airflow WGS
snapshot is copy-only and can be removed independently after verifying no run
references it.

## 2026-08-18 - Codex - T133 WGS 4.0.1 flow and monitoring correction

### Goal

Re-read the actual WGS 4.0.1 CCE code, remove the incorrect FASTQ MD5/upload-verification stages from the Airflow design, and document a Rule-first, Master-only Pod monitoring architecture.

### Completed

- Confirmed from `prepare/cce.py` that CCE does not create `FASTQ.MD5SUMS`; Step1 performs its own upload/reuse loop and writes `FASTQ_UPLOAD_COMPLETE`.
- Confirmed that `obsutil cp -vmd5` remains a transfer option for newly uploaded objects, not an Airflow hash task.
- Confirmed that Step2 internally checks the marker and mounted FASTQ before Master start; there is no separate `verify_input_obs` Airflow stage.
- Rewrote the main design around the real Step1-Step6 and Master `cloud_preflight/cloud_wgs_all/final-dryrun` flow.
- Documented Rule monitoring through a Master-only Snakemake logger JSONL and batch Master Job/Pod monitoring through a BS10610 watcher; no logger or continuous watcher is required in Worker Pods.
- Fixed `jobs.ndjson` as administrator-only diagnostic evidence. The platform will not show Worker Pods, so no Rule→Worker Pod mapping or receipt extension is required.
- Recorded the current host mismatch: upstream scripts assume one operator host, while Airflow must keep node005 OBS/SFS credentials separate from BS10610 kubectl/CCE.

### Changed files

- `docs/22_WGS_ONLY_LOCAL_CCE_PLATFORM_DESIGN.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/24_WGS_RUNTIME_INTEGRATION_DEVELOPMENT_STATUS.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

This correction changed only Markdown files; broader uncommitted code changes already exist in the worktree. No Git commit was created.

### Commands and evidence

- Read-only SSH inspection of WGS README/SOP, prepare generator, Step scripts, Master runner, workflow monitor, native state machine, delivery implementation, Master image lock, CCE profile and production evidence.
- Read local logger plugin/tests, evidence bridge, observer ingestion/projection and DB workload contracts.
- One read-only SSH connection attempt was aborted during banner exchange; retry succeeded. No remote mutation occurred.

### Tests not run and why

- No backend/frontend/DAG/Compose/Snakemake/CCE test was run because this correction is doc-only and changes no executable artifact.
- No BS10610 service, Airflow metadata, DAG pause, Docker network, database, CCE resource or OBS object was changed.

### Current state and risk

- `WGS_EXECUTION_ENABLED=false`; current WGS DAGs remain paused.
- Current Master image and command do not include the logger plugin/arguments.
- Current `wgs_evidence_bridge.py` targets a legacy Deployment and cannot be reused unchanged for Rule JSONL retrieval or batch Master monitoring.
- Existing-object FASTQ reuse trusts matching length plus existing remote MD5 metadata; source immutability remains required because no new local FASTQ MD5 is calculated.

### Next recommended task

Implement T133 in disabled mode: simplify the DAG, split node005/BS10610 restricted adapters, install/connect the Master logger, replace the legacy bridge with Rule JSONL retrieval plus Master-only monitoring, then run synthetic failure/retry/interruption acceptance.

### Rollback

Revert only these Markdown changes. No runtime or data rollback is required.

## 2026-08-18 - Codex - T133 WGS 4.0.1 single-DAG documentation

### Goal

Record the confirmed WGS 4.0.1 single-DAG target and separate it from the current three-DAG paused legacy state, without changing or deploying runtime code.

Document baseline: WGS release 4.0.1 at commit `6cb1255fc1b218c9b18fb931eb3b6a172afe907b`.

### Completed

- Documented target DAG `bio_wgs`, CCE-only execution, observer-owned ten-minute scanning, batch-specific Master Job, 4.0.1 native evidence, separate Rule logger JSONL, result verification, and Step7/Step8 exclusion.
- Recorded that current BS10610 still has paused `bio_wgs_cce`, `bio_wgs_onprem`, and `bio_wgs_intake_scan`; these are pending replacement/removal and were not deleted in this task.
- Recorded that deployed `bio_wgs_cce` is still Phase 1 mock and that the un-deployed runtime gate retains obsolete persistent Deployment, fixed Master slot, old Step filename, and old snapshot-name assumptions.
- Fixed the security boundary in the design: node005 handles private OBS only; BS10610 handles kubectl/CCE only.
- Marked T133 implementation as `todo`: design and current-state audit are complete, while DAG refactor, launch adapter, runtime acceptance, and deployment have not started.

### Changed files

- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/22_WGS_ONLY_LOCAL_CCE_PLATFORM_DESIGN.md`
- `docs/24_WGS_RUNTIME_INTEGRATION_DEVELOPMENT_STATUS.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

No non-Markdown file was changed by this doc-only task. No Git commit was created.

### Commands and results

- Read project instructions, current state/task/handoff material, relevant WGS design documents, current worktree status, and existing diffs.
- Ran documentation terminology searches for WGS release/commit/DAG IDs, Master assumptions, evidence files, host boundaries, and implementation-status wording.
- Ran `git diff --check` after the edits.
- One initial PowerShell consistency-check loop failed before execution with `An empty pipe element is not allowed`; the result variable was separated from the formatting pipeline, then the same checks were rerun successfully. The failed command made no file or runtime change.

### Tests not run and why

- Backend pytest, frontend tests/build, DAG import/list, Compose config, Snakemake dry-run, CCE/OBS smoke, and BS10610 service checks were not run because this task is strictly doc-only and changes no executable artifact.
- No process was started, no Airflow metadata was deleted, no service was recreated, and no execution gate or DAG pause was changed.

### Current git status

- Worktree: `D:\pipeline\airflow-demo-worktrees\T129-wgs-only`.
- Branch: `codex/platform/T132-wgs-runtime-integration`.
- The worktree already contains broader uncommitted T131/T132 code and documentation changes. This task only adds Markdown edits and intentionally does not commit.

### Risks and open questions

- Historical sections elsewhere in the repository still mention old DAGs and fixed Master slots. They are audit history, not implementation guidance; the new authoritative sections explicitly label the current legacy state and future target.
- The exact code deletion/migration sequence for old DAG metadata must be planned during T133 implementation; this task does not authorize deletion.

### Next recommended task

Implement T133 in disabled mode: create one `bio_wgs`, move scanning to observer, replace the old runtime gate with the 4.0.1 batch Master Job/evidence adapter, and complete synthetic acceptance before any real execution approval.

### Rollback

Revert only these Markdown edits. No runtime, database, network, workflow, or data rollback is required.

## 2026-08-18 - Codex - WGS 4.0.1 Airflow development copy replaced

- Goal: directly replace the Airflow-owned WGS workflow copy with the now-stable upstream WGS release 4.0.1 while preserving all execution and network gates.
- Source: BS10610 `/mnt/biodevrwbi/33.chenjiucheng/project/wgs`, branch `dev_CXJ_4.0.1_docker`, clean commit `6cb1255fc1b218c9b18fb931eb3b6a172afe907b`, tree `53453d5de867e53261f99c65c492e3e470098d3b`.
- Replacement: atomically replaced `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs` from tracked Git HEAD. The upstream checkout was not modified.
- Snapshot/catalog: `wgs-v4.0.1-dev-6cb1255-53453d5d`; manifest digest `e9ce0f11c8c663ce13e88c7472a67ae36e2666cfba935312275396c3c7f5ce17`; backend and observer both see the updated catalog.
- Security: excluded `prepare/config.yaml`, `cfg/config.mail.ini`, and legacy site upload/archive/mail helpers. A redacted literal-assignment scan found no password, token, access key, or secret key in the Airflow copy. No OBS configuration, kubeconfig, patient data, FASTQ, result, reference, database, or Docker volume was copied or changed.
- Verification: manifest `sha256sum -c` passed; all copied Python files compiled in memory; Huawei Cloud shell scripts passed `bash -n`; native `05-master-job.yaml`, Master Job runner, evidence collector, run-state module, and `cce_delivery.py` are present.
- Runtime safety: no active `bio_wgs_cce` or `bio_wgs_onprem` runs; all three WGS DAGs remain paused; `WGS_EXECUTION_ENABLED=false`; no CCE, SGE, local analysis, upload, or download was started.
- Network safety: `nipt_analysis_test_net` remains at `192.168.199.0/24`, gateway `192.168.199.1`; only frontend publishes `172.17.106.10:12959`; backend has no host port.
- Changed tracked/worktree files: `config/wgs_releases.yaml`, `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`, and `docs/24_WGS_RUNTIME_INTEGRATION_DEVELOPMENT_STATUS.md`. The server-side Airflow workflow copy and current release catalog were updated; no Git commit was created.
- Commands/evidence: read-only Airflow run/pause checks; `git archive` into a guarded staging directory; in-memory Python compilation; `bash -n` for Huawei Cloud shell scripts; `sha256sum -c SNAPSHOT_MANIFEST.sha256`; catalog checks from both backend and observer containers; Docker network/port inspection; upstream `git status`/HEAD recheck. All final verification commands exited 0.
- Benign command failure: two inline PowerShell-to-SSH verification attempts containing remote `$()` were expanded locally and exited 1 before running the remote check. No server mutation occurred. The checks were rerun through the CRLF-safe stdin-to-Bash pattern and passed; final direct manifest/catalog/DAG/source verification exited 0.
- Tests not run: no Snakemake dry-run, CCE Master Job, OBS transfer, result download, full backend/frontend regression, or biological workflow test. This change only refreshes the development workflow baseline, and the execution gate deliberately remains closed.
- Current Git status: the T132 worktree still contains the broader uncommitted backend/DAG/frontend/runtime integration changes requested earlier. This snapshot/catalog update is also uncommitted, consistent with the instruction not to commit before development is finished.
- Risk/open question: the existing runtime gate and observer still encode parts of the pre-`6cb1255` persistent-Master/watcher design. They must be adapted and mock-tested before any execution approval; no additional user decision is required for that safe disabled-mode development.
- Rollback copy: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/development-wgs-before-wgs-v4.0.1-dev-6cb1255-53453d5d-20260818T161125+0800`. Keep it until the new adapter passes mock acceptance, then remove only with an explicit cleanup decision.
- Important design change: 4.0.1 uses a per-batch Master Job and native SFS evidence (`run-state.json`, `events.ndjson`, `jobs.ndjson`, `RUN_COMPLETE.json`, `RUN_FAILED.json`). Do not implement the obsolete four persistent Master Deployment slots or the deleted watcher path.
- Next: update the runtime gate and observer to consume the native evidence contract, then run synthetic prepare/evidence/result tests with all real execution gates still disabled.

## 2026-08-12 - Codex - T130 WGS server-copy observability deployed

- Goal: continue the WGS-only Airflow plan using the current server WGS tree while keeping workflow execution disabled.
- Source boundary: upstream `/mnt/biodevrwbi/33.chenjiucheng/project/wgs` was not modified. Airflow-owned integration is in `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs`; source commit `136da1ad9e45ac1abcbeb3efa40bb2e2269b6ab9`, snapshot-manifest SHA256 `b10cd8af1db19c313e15167c295d007d9eca246d03b2721592c4c0532a05696c`.
- Implemented: logger/evidence adapters in the server copy; local release catalog; Alembic `20260812_0007`; durable observer binding/cursors; Rule and Pod/Job/metrics projections; authenticated API and WGS Run Detail; read-only unprivileged observer Compose service; Docker network preflight.
- Deployed: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current` points to `releases/20260812-wgs-observer-553be3f`. Only backend, observer, and frontend were recreated. PostgreSQL, Redis, Airflow services, volumes, shared network, workflow sources, inputs, results, references, and production evidence were preserved.
- Docker IP contract: `nipt_analysis_test_net`, subnet `192.168.199.0/24`, gateway `192.168.199.1`; only `172.17.106.10:12959` is published. Attachments were recorded before/after; backend/observer dynamically exchanged internal IPs but Compose DNS and health remained correct.
- Verification: backend focused suite 27 passed; WGS frontend 3 passed; TypeScript and Vite build passed; deployment contract 4 passed; Compose config passed; migration head `0007`; all three WGS DAGs paused; login/admin RBAC passed; submission HTTP 409; observer has no ports, host network, privilege, extra caps, kubeconfig, OBS/SSH/Docker credentials.
- Synthetic acceptance: `WGS_SYNTH_T130_553BE3F` consumed one complete Rule record while holding a partial line, then consumed the completed line plus Pod/metrics/Job evidence (4), and a fresh observer container consumed 0 on restart. DB projected `mapping=running`, `mapping-7=Failed`, `OOMKilled`, exit 137, node, 1Gi metrics, and job message. Synthetic DB row and files were deleted afterward.
- Backups: biodemo pre-`0007` dump SHA256 `62831626c2f4142c32f126b6da8ae26304e49a46e5ef6b16c2c8255d3454f110`; prior untracked env copied to `validation/t130-observer/bs10610.wgs.env.before` with mode 600.
- Known limitation: full legacy frontend tests intentionally fail because 40 old NIPT/PGT-A authless/mixed-shell cases conflict with the WGS-only product. No WGS, CCE, SGE, local Snakemake, OBS transfer, or production evidence execution occurred.
- Rollback: restore the saved env, select `releases/20260812-wgs-only-phase1`, recreate only backend/observer/frontend, and restore the biodemo dump only if a DB rollback is required. Do not recreate/delete `nipt_analysis_test_net` or remove volumes.
- Next: T131 refreshes an explicitly accepted WGS snapshot and implements actual execution, OBS `-vmd5`, result reconciliation, four-batch concurrency, and failure acceptance.

## 2026-08-12 - Codex - T129 WGS-only Phase 1 implementation checkpoint

- Goal: implement and deploy the non-workflow portion of the WGS-only platform while the WGS 3.9.3 workflow remains non-final.
- Completed locally: WGS-only request/RBAC APIs; scrypt/HttpOnly/CSRF sessions; audit and account administration; attempts/transfers/rule/Pod/master-slot biodemo models and migration; idempotent read-only observer; WGS-only frontend and five-second active polling; paused CCE/on-prem/intake DAG topology; production Compose contract; design and supporting specifications.
- Safety: `WGS_EXECUTION_ENABLED=false`; backend submit returns 409 and no Airflow trigger; DAG runner tasks fail closed and contain no CCE, OBS, local, or SGE command. No WGS workflow, FASTQ, result, reference, kubeconfig, or OBS credential was changed.
- Verification: remote backend new tests plus compatible lifecycle/intake coverage passed 36 before the stricter Phase 1 submission gate. After the gate, the focused new backend suite passes; four legacy tests expect authless or old WGS submission behavior and are intentionally superseded. WGS DAG/deployment contract scripts passed on BS10610. Focused WGS frontend tests passed 4/4 and `tsc -b && vite build` passed; the old mixed NIPT/PGT-A suite is intentionally incompatible with the WGS-only shell.
- Changed areas: backend auth/models/migration/WGS services/observer, three WGS DAGs and configs, `docker-compose.wgs.yaml`, WGS nginx/frontend pages/tests, docs 04-08 and 11-13, and `docs/22_WGS_ONLY_LOCAL_CCE_PLATFORM_DESIGN.md`.
- Pending: build/reuse deployable images, perform fresh BS10610 migration and live login/RBAC/submit-denial smoke, atomically switch `current`, then remove only exact obsolete Airflow platform state after validation.
- Deployment result: BS10610 `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current` points to `releases/20260812-wgs-only-phase1` from Git `a30dcdb`. Fresh Airflow and biodemo state is running; biodemo is at `20260812_0006`; four master slots exist. All three WGS DAGs are paused and the Airflow pools are `wgs_cce_runs=4` and `wgs_obs_transfer=1`.
- Live smoke: health 200, anonymous runs 401, admin login and account list 200, non-WGS create 422, synthetic controlled WGS request created, and submit 409. No Airflow WGS run was created.
- Permanent cleanup after acceptance: removed `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT`, exact volumes `airflow-nipt_postgres-data` and `airflow-nipt_redis-data`, the orphaned old Airflow volume `4becda9a...`, and every old `/airflow-WGS/releases/*` directory except `20260812-wgs-only-phase1`. These platform states/releases are not recoverable from this host.
- Explicitly preserved: `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-3.9.3-cloud`, `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence`, WGS/NIPT production inputs, workflow sources, references, and result directories.
- Phase 2: pin final WGS 3.9.3, implement node005 OBS transfer, CCE/local/SGE runners, group evidence offsets, logger compatibility, four-run recovery/concurrency, and real acceptance.
- Rollback before old-state removal: keep all DAGs paused, restore the previous `current` link, and recreate only application services. Never delete production inputs, pipeline sources, references, or results.

## 2026-07-15 - Codex - T127 final WGS dry-run and frontend closeout

- Goal: keep WGS validation dry-run only, complete two to three NIPT full
  batches, and make the shared NIPT/WGS frontend report those states without
  PGT-A labels or JSON parsing failures.
- Completed: `WGS_20260715_062217_351C76` used `wgs_stage=precalling` and the
  hard `WGS_ALLOW_EXECUTION=false` gate. Airflow/backend reached success in 12
  seconds. Its 21 Snakemake graph jobs are persisted as terminal `skipped`
  dry-run plans; no WGS rule was executed and no host WGS process remains.
- NIPT evidence: `NIPT_20260715_030032_9A815B`,
  `NIPT_20260715_031706_C435A8`, and `NIPT_20260715_033817_4B4F72` completed
  serially in 858.5, 783.6, and 884.9 seconds. Each has 27/27 QC pass,
  232/232 success rule events, and zero running events.
- Frontend: Dashboard reports the WGS dry-run as Success, Completed, 100%,
  elapsed 12s, and QC not applicable. Workflow Catalog reports `WGS Host
  Dry-run`, `Snakemake 9.23.1 graph validation`, and `21 jobs planned; dry-run
  only`. Submit exposes only NIPT Docker and WGS and states that WGS is dry-run
  validation. Browser console warnings/errors were empty; PGT-A text count was
  zero.
- Runtime verification: BS10610 services are running, backend/API health is
  green, capabilities are exactly `nipt_docker,wgs`, and Airflow lists only
  `bio_nipt_docker`, `bio_wgs`, and paused `bio_intake_scan`. Pools
  `nipt_s9_full` and `bs_heavy_analysis` each have one slot. No NIPT analysis
  container or WGS Snakemake process remains active.
- Tests: backend full pytest `197 passed, 1 skipped`; WGS/NIPT runner and
  deployment contracts `43 passed`; logger tests `6 passed`; frontend Vitest
  `70 passed`; production `tsc -b && vite build`, nginx config, and both BS
  Compose configs passed.
- Images/release: backend `airflow-demo/backend:bs-control-f11ea02`
  (`sha256:221955332609...`, archive SHA256 `48d71ebb...`), frontend
  `airflow-demo/frontend:bs-control-f11ea02` (`sha256:93cf3a076c43...`, archive
  SHA256 `52e98121...`), release archive SHA256 `74ee973c...`. Both BS nodes
  loaded exact image IDs through the required fengxian -> local Windows -> BS
  relay; BS1069 remains stopped.
- Changed closeout files: `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`,
  `SERVER_INFO.md`, and T127 API/frontend/DAG/logger/deployment/acceptance docs.
- Failure note: one final Compose status probe used the wrong relative env
  path and failed before contacting a service; rerunning with the absolute
  `/mnt/.../airflow-NIPT/env/bs10610.env` path passed. An earlier test harness
  mounted only `dags/` and produced six false contract failures; mounting the
  repository root passed all 43 checks. The first BS1069 closeout wrapper used
  `readlink current` after changing into `current`; Compose validation and the
  zero-service check had already passed, and an absolute readlink rerun
  confirmed `releases/f11ea02` plus both final image IDs.
- Not run: no real WGS analysis, no additional NIPT batch, and no Intake scan
  were triggered during final closeout. This matches the revised scope.
- Risk: the NIPT worker still needs the Docker socket for the current nested
  fetal-ratio implementation. Pinned image IDs reduce supply-chain drift but
  do not remove Docker-socket privilege.
- Rollback: keep Intake paused, restore the previous release and
  backend/frontend image tags, and recreate only application services. Never
  use `down -v` or delete databases, workdirs, results, logs, FASTQ, or the
  external network.

## 2026-07-15 - Codex - T127 pre-final shared control-plane checkpoint

This checkpoint is superseded by the final dry-run/frontend closeout above.

- Branch/worktree: `codex/wgs/T127-bs-wgs-s9-platform` in the isolated T096
  worktree. The final compatibility series includes `ed4b501`, `57a7316`,
  `04c182e`, `82be233`, `8b5c62f`, `bdecbfb`, and `fd52f5f`.
- Architecture: BS10610 reuses the existing `airflow-nipt` Compose project and
  one PostgreSQL/Redis/FastAPI/React-nginx/Airflow CeleryExecutor control plane.
  Deployed DAGs are `bio_nipt_docker`, `bio_wgs`, and paused
  `bio_intake_scan`; PGT-A is absent.
- Concurrency: NIPT and WGS share one-slot `bs_heavy_analysis`. NIPT uses 32
  container cores; WGS uses a 96-core host scheduling ceiling. Pool slots
  serialize batches and do not represent CPU cores.
- WGS: Snakemake 9.23.1/Python 3.12 is deployed under the WGS host project and
  invoked through the restricted forced SSH command. The full downstream
  Snakemake 9 dry-run resolved 23 jobs for the selected family. Per the revised
  acceptance scope, the verified process group was intentionally stopped after
  dry-run evidence. `WGS_20260714_180953_9D7981` is therefore terminal failed
  in Airflow and must not be described as a completed analysis or failed
  dry-run. No WGS process remains active.
- Three NIPT full batches completed serially:
  `NIPT_20260715_030032_9A815B` (858s),
  `NIPT_20260715_031706_C435A8` (783s), and
  `NIPT_20260715_033817_4B4F72` (884s). Each has 27/27 sample QC pass,
  232/232 rule events success, and zero running rule events.
- Frontend/backend compatibility: nginx now proxies exact `/api` and `/api/*`
  before SPA fallback; malformed/HTML responses produce readable API errors;
  `DEPLOYED_PIPELINES` scopes Runs/Samples/Failures/Dashboard/Intake; Dashboard
  includes WGS; Workflow Catalog and rule endpoints group all repo-owned WGS
  rules into Pre-calling, Variant analysis, or QC. The WGS `all` target is
  stage-aware, and the intentionally stopped run reports Variant analysis.
- Resource UI labels Docker host-proc RSS as a process-sum upper bound when PSS
  is unavailable. The current NIPT RSS sum double-counts shared pages and must
  not be used as container peak memory; read/write I/O is also zero in this
  collector snapshot.
- Final remote verification: backend image pytest passed 192 tests with the
  repo-owned WGS catalog mounted; frontend Vitest passed 69 tests; `tsc -b &&
  vite build`, nginx config, and both BS Compose configs passed. Live browser
  checks found zero visible PGT-A labels and zero console errors on Dashboard,
  Workflow Catalog, and NIPT Run Detail.
- Fresh close-out verification after the documentation commit passed backend
  pytest with `191 passed, 1 skipped` when only the repo-owned WGS catalog was
  mounted, plus frontend `69 passed` and a successful production build. The
  first close-out backend command mistakenly mounted all `pipelines/`, which
  collected PGT-A NumPy tests that are intentionally outside the BS NIPT/WGS
  backend image and failed during collection; narrowing the mount to
  `pipelines/wgs_s9` restored the intended deployment test contract.
- Fresh live checks found zero active business runs, no WGS host process or
  NIPT/WGS analysis container, scanner paused, nginx config valid, and the
  external network fixed at `192.168.199.0/24` with gateway `192.168.199.1`.
  BS1069 again passed Compose validation with zero running platform services.
- Images: backend/frontend were built on fengxian, downloaded to local Windows,
  uploaded to BS, SHA256 verified, and independently loaded on BS10610 and
  BS1069. Final backend is `bs-control-bdecbfb`
  (`sha256:73c965a2d1ab...`, archive SHA256 `c3fd486d...`) and frontend is
  `bs-control-fd52f5f` (`sha256:cf13aa210ed6...`, archive SHA256
  `8abe269a...`). Direct server-to-server image transfer was not used.
- BS10610 deployment backup:
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT/backups/T127-shared-control-20260715T020518`.
  PostgreSQL/Redis volumes were preserved. Services are healthy on 12959/12958,
  capabilities are exactly `nipt_docker,wgs`, and the external network remains
  `192.168.199.0/24` with gateway `192.168.199.1`.
- BS1069 has the same final backend/frontend images, a complete host-specific
  Compose env, restricted SSH gate, valid external network, and passing Compose
  config. Every service remains stopped; do not run active-active.
- Safety: scanner is paused, auto-submit is disabled, production workflow
  sources and FASTQ are read-only, and no database volume, result, or input was
  deleted. Rollback restores the previous shared release/images without `-v`.
- Failure records: an early WGS `TERM` left an orphaned Snakemake process; the
  exact verified process group was then stopped with `KILL`. Standalone nginx
  validation first failed because Compose DNS names were absent and passed
  with explicit local host mappings. Several PowerShell-to-SSH multiline
  commands carried a trailing CR into the last shell argument; commands were
  rerun as single operations. The first final frontend build wrapper hit the
  outer 120-second timeout after tests/build/nginx passed but before image save;
  image save and checksum were rerun separately. None of these failures changed
  a database, volume, FASTQ, or production workflow source.

## 2026-07-14 T124 QC formatting, Intake alignment, and tracker ordering

- Branch/worktree: `codex/frontend/T124-qc-intake-sort-consistency` in the
  isolated T096 worktree, based on T123 `5d27e6c`.
- Dashboard terminal rows now sort by latest `pipeline_finished_at`/`ended_at`
  after active runs; created-only rows remain last. This fixes old successful
  batches appearing ahead of newly completed runs.
- Run Detail QC now formats count metrics as K/M, NIPT mapping/duplication
  percentage points with a trailing `%`, fetal fraction as a four-decimal
  fraction, and PGT-A continuous metrics with four decimals. Raw backend values
  remain unchanged.
- Intake Scanner reuses Run Tracker project/runtime components, hides root
  paths, uses `N samples`, and receives the same history-based elapsed/ETA
  projection without per-row Airflow requests.
- Test-first evidence: the new backend tests failed on reversed success order
  and missing Intake timing fields; frontend tests failed on raw QC strings and
  missing aligned cells. After implementation, isolated remote backend pytest
  passed 168 and frontend Vitest passed 49.
- Remote acceptance passed: backend `168 passed`; frontend `49 passed`;
  production `tsc -b && vite build`; Compose config; frontend HTTP 200; backend
  health; and API ordering/Intake timing checks. The first returned run is the
  newest completion `NIPT_20260713_162606_5B5B11`.
- Live browser checks confirmed NIPT values such as `72.95%`, `2.30%`, and
  `0.1973`, plus PGT-A `total_counts` as `38.3M`. Intake History has the aligned
  nine-column table, elapsed runtime, and no visible scanner root. Dashboard
  had no document overflow at 1280, 1024, or 390 px.
- Backend/frontend only were rebuilt and recreated. Airflow worker/scheduler,
  DB, scanner policy, workdirs, FASTQ, and results were unchanged. Scanner
  remained unpaused on `*/10`, and the active-run API remained empty.
- Pre-overlay source backup:
  `/home/jiucheng/project/airflow-demo-t121/backups/T124-20260714-1220/pre-overlay-source.tar.gz`
  (`ed1f54f5b9114622604c60e95674c1427b0bb02959cdddebae04168083743666`).
  Rollback is backend/frontend image-only; no DB or analysis data changed.

## 2026-07-14 T123 Predict path and operations consistency

- Branch/worktree: `codex/platform/T123-predict-operations-consistency` in the
  isolated T096 worktree, based on committed T121/T122 baseline `eb5f86f`.
- Dashboard separates pending/error Discovery from linked Intake history and
  marks runs Manual or Intake. PGT-A Run Detail exposes only Predict; skipped
  compatibility branches and the raw rule-job table are hidden.
- Backend QC projection distinguishes pending/unavailable from decision
  pass/warn/fail. Terminal failed parents cancel stale running sibling rule
  events without overwriting true failed rules.
- Workflow Catalog uses `/api/workflows`, limited to PGT-A Predict and NIPT
  Docker Full. NIPT S9 defaults to 32 cores.
- `bio_intake_scan` has scanner-only 30-day retention and Airflow containers
  use 50 MB x 3 json-file rotation. Retention runs only at 03:00 and the final
  propagation task keeps a failed scan from being reported as a successful DAG
  run. Analysis DAG IDs are rejected.
- Remote validation passed: isolated backend `187 passed`; frontend `47 passed`;
  production `tsc -b && vite build`; Intake DAG `6 OK`; config override
  `10 OK`; Compose config; Airflow import with no errors; frontend/backend
  health; and live browser checks.
- Deployment gate passed: `PGTA_20260713_144002_E73F72` is success and the
  active-run query returned no items before service restart.
- Deployment rebuilt and recreated backend, Airflow API/scheduler/worker, and
  frontend from `/home/jiucheng/project/airflow-demo-t121` without recreating
  Postgres, Redis, or volumes. The scanner stayed unpaused on `*/10` and NIPT
  automatic submit stayed disabled. The pre-deploy inventory backup is
  `/home/jiucheng/project/airflow-demo-t121/backups/T123-20260714-0025`.
- Syncing failed run `NIPT_20260713_145457_ACCBDC` preserved the two true
  failed mapping samples `PRO25010003.A42` and `PRO24120586-S1.A24`, changed
  eight stale running sibling events to canceled, and left no running event.
  Run Detail now opens the first failed sample log by default.
- The supervised 32-core clone `NIPT_20260713_162606_5B5B11` used the same
  20-sample source batch as the failed 40-core run and completed success in
  about 14 minutes. All 20 sample QC decisions passed, all 176 rule events are
  success, and every Airflow task is success. Workflow Catalog reports this
  run as the current NIPT Docker Full baseline.
- Browser acceptance confirmed Dashboard Pending/History separation, Manual/
  Intake provenance, PGT-A Predict-only stages with no legacy alternate path,
  no historical baseline action controls, failed-sample-first log selection,
  and live PGT-A/NIPT Workflow Catalog data. A 1280px check found no document
  overflow on the historical PGT-A detail page.
- Independent review found that an `all_done` retention leaf could mask a
  failed scan, the hour-only retention guard ran six times, historical
  baseline actions remained visible, and Workflow Catalog materialized all
  runs. These were fixed before commit: a terminal propagation task preserves
  failure, retention is exactly 03:00, baseline controls are hidden, and the
  Catalog uses fixed-count SQL aggregation plus one latest row per pipeline.
- Final read-only verification first used an inline remote Python JSON summary;
  PowerShell/SSH quote escaping produced `SyntaxError: EOL while scanning string
  literal` after the HTTP health checks. It made no write request. The same API
  responses were then parsed locally with PowerShell and confirmed run success,
  20/20 QC pass, and 176/176 rule events success.
- Running pytest inside the live backend container inherited the deployment
  service token, so 14 legacy internal-endpoint tests returned 401 while 173
  passed. The isolated backend image without deployment secrets then passed
  all 187 tests. The first DAG-test wrapper used the Snakemake venv Python and
  the second hit the Airflow image entrypoint; neither executed a DAG. The
  corrected read-only container command overrode the entrypoint, mounted the
  repository, and passed all 16 Intake/config tests. One earlier local wrapper
  using `$PWD` failed PowerShell parsing before SSH and had no remote effect.
- Rollback preserves DB data, FASTQ, workdirs, logs, results, and volumes.

## 2026-07-13 T122 NIPT Intake completed-run visibility

- Follow-up was implemented in the existing uncommitted
  `codex/frontend/T121-intake-error-visibility` worktree so the deployed T121
  Intake diagnostics remain intact.
- Live diagnosis showed no backend/Airflow mismatch. NIPT run
  `NIPT_20260713_135001_98E375` and its Discovery row are both success with
  72 samples, QC pass, 100% progress, and Completed. The row is archived with
  `workflow_success`, so the old Dashboard `lifecycle=active` query hid it.
- The Dashboard also refreshed only overview/run data after Airflow sync. A
  browser left open during execution retained the earlier submitted Discovery
  payload even after the run reached success.
- Dashboard and Settings now default to `lifecycle=all`. Active-run polling,
  manual Sync, and Submit refresh Intake together with overview/run data
  without a spinner. The Intake heading now states that active and completed
  operations are shown.
- Status semantics are explicit: `submit_state=submitted` is the immutable
  handoff audit state; linked rows render `display_status=success`, 100%, and
  Completed from the business run projection.
- TDD evidence: the new tests first failed because Dashboard made one active-
  only Intake request and Settings selected Active. After the fix, remote
  frontend Vitest passed 40 and production `tsc -b && vite build` passed.
- Deployment rebuilt/recreated frontend only from
  `/home/jiucheng/project/airflow-demo-t121`. Frontend returned HTTP 200 and
  the deployed bundle contains `Active and completed intake operations`.
  Backend, Airflow, scanner, database, FASTQ, workdirs, and pipelines were not
  restarted or modified.
- Rollback: redeploy the pre-T122 frontend image. No data rollback is required.

## 2026-07-13 T121 PGT-A Intake error visibility

- Branch/worktree: `codex/frontend/T121-intake-error-visibility` in the isolated
  T096 worktree, based on T120 commit `3d2c469`.
- Root cause: `project-20260713` never created a run. Its manifest used missing
  `source_batch=2026-06-08/batch01` and unresolved sample IDs `H1/H2`, so Intake
  failed before Airflow/Snakemake. Backend already persisted the reason, but
  the shared frontend table rendered only `Stable check 0`.
- Backend now returns `current_stage=Intake validation failed` for unlinked
  error Discovery rows. Dashboard and Platform Settings show that stage and a
  two-line `last_error` excerpt; the full message remains in the title.
- Corrected the remote non-trigger template to use batch
  `2026-06-08/HZSW-20260602-L-01-2026-06-062220` and samples
  `JZ26117424-H1-H1/JZ26117425-H2-H2`. The original was copied to
  `/home/jiucheng/project/airflow-intack-configs/pgta/backups/T121-20260713`.
  A read-only parser probe resolved two unique R1/R2 pairs with zero errors.
- Safety: the template remains `project-20260713.samples.par.tsv` with
  `project-20260713.par.READY`. No scanner-recognized `.samples.tsv`/`.READY`
  pair was published, no run was created, and scanner stayed unpaused.
- TDD evidence: the backend regression first failed with `Stable check 0`; two
  frontend regressions first failed because `Intake validation failed` was not
  rendered. After implementation, backend full pytest passed 181, frontend
  Vitest passed 40, production `tsc -b && vite build` passed, and Compose config
  passed remotely.
- Deployment: backend/frontend were rebuilt and recreated from
  `/home/jiucheng/project/airflow-demo-t121`. Frontend returned HTTP 200,
  backend health returned ok, and the live error row returns both the explicit
  stage and `source_batch is not a readable directory: 2026-06-08/batch01`.
- Failure record 1: `docker build --target test` was attempted for backend, but
  its Dockerfile has no test target. The isolated full backend image was built
  and pytest was run directly instead.
- Failure record 2: the first inline Python parser probe was broken by
  PowerShell/SSH quote escaping and returned a syntax error. It made no API or
  DB call. A temporary read-only validation script then passed and was removed.
- Failure record 3: one multi-file scp used a temporary `PLACEHOLDER` directory
  and flattened the frontend component path. The intended files were copied to
  exact destinations and only the accidental T121 files/directories were
  removed before testing or deployment.
- Rollback: redeploy T120 backend/frontend images. Restore only the backed-up
  `.par.tsv` if the corrected draft is unwanted. Do not change Discovery, runs,
  FASTQ, workdirs, results, volumes, or scanner pause state.

## 2026-07-13 T120 NIPT YAML request parsing and explicit intake trigger

- Branch/worktree: `codex/intake/T120-nipt-yaml-request` in the isolated T096
  worktree, based on T119 commit `49164e1`. The approved design was committed
  separately as `caccbbc`.
- Added a hardened, path-free NIPT YAML contract. Requests identify a
  `batch_id`; backend resolves exactly one batch below approved NIPT roots,
  validates complete top-level clean FASTQ pairs, and supports `samples: all`
  or a unique sample-ID list.
- Parser rejects files over 64 KiB, unknown/duplicate keys, aliases, anchors,
  custom tags, path-like identifiers, unsupported modes, invalid core counts,
  ambiguous batches, incomplete pairs, and file/request ID mismatch. Files
  ending in `.partial` are ignored.
- Added dedicated trigger inbox mount
  `/home/jiucheng/project/airflow-intake-requests/nipt` ->
  `/data/airflow-intake-requests/nipt`. The operator edit workspace
  `/home/jiucheng/project/airflow-intack-configs/nipt` is not mounted or
  scanned.
- Explicit YAML submission requires two stable scans, `submit: true`, global
  intake permission, `request_submit_enabled=true`, approved runtime Profile,
  and the existing NIPT heavy-run gate. Ordinary NIPT directory Discovery keeps
  `auto_submit.enabled=false` and cannot launch a run.
- Successful request runs archive only the YAML under
  `.archive/YYYY/MM/<request_id>`. NIPT FASTQ remains read-only and is never
  moved or deleted.
- Remote TDD evidence: missing parser module failed collection as expected;
  parser tests then passed 8, with a ninth unsafe-key regression added during
  review. A preview-summary regression test failed with
  `blocked_auto_submit=0` and passed after request-specific blocked reasons
  were included. Final full backend pytest passed 181.
- Deployment: backend was rebuilt/recreated only from
  `/home/jiucheng/project/airflow-demo-t120`; Compose config, health, sanitized
  intake config, request mount, and read-only preview passed. A temporary
  `submit:false` probe resolved all 72 samples in
  `260422_TPNB500380AR_1070_AH33KYBGY2` without DB writes or Airflow submit.
  Final counts remain 8 runs, 0 active NIPT Discovery, and 3 archived NIPT
  Discovery rows. The trigger inbox is empty and scanner was restored unpaused.
- Final backend image is `sha256:d151ecd1...decea135c`. The actual
  `project-20260713.nipt.yaml` in the non-scanned edit workspace was parsed
  read-only and resolves 72 samples with cores 32 and `submit=true`. It was not
  copied to the trigger inbox because publishing it starts a full NIPT run.
- Failure record 1: the first authenticated preview command returned HTTP 422
  because the internal service token header was omitted; no write occurred.
  The command was rerun with the existing untracked `.env` token and returned
  an empty, error-free preview.
- Failure record 2: the first direct parser probe omitted `docker run -i`, so
  Python received no heredoc and emitted no result; it made no API/DB call. The
  corrected read-only probe printed 72 resolved samples.
- Failure record 3: a stdin-delivered final deploy script paused the scanner
  but did not reach its trap-based restore or image rebuild. A direct state
  check caught `is_paused=true` immediately. A short non-nested Compose command
  then built image `sha256:6dbf106d...f169d661`, recreated backend, and restored
  `bio_intake_scan` to `is_paused=false`; health and run/Discovery counts were
  rechecked afterward.
- Failure record 4: a read-only parse of every YAML in the edit workspace found
  an unrelated legacy `project-tmp.nipt.yaml` whose filename does not match its
  internal request ID. The parser rejected it as designed. No file was removed;
  the targeted `project-20260713.nipt.yaml` parse then passed.
- Failure record 5: a final combined PowerShell/SSH verification command was
  rejected locally because PowerShell parsed the embedded Python list
  expression. It executed no remote action. The checks were split into simple
  commands; health, image, scanner state, empty inbox, manifest, and Git checks
  then passed.
- Rollback: pause `bio_intake_scan`, restore the T119 backend image and
  `config/intake.yaml`, remove only the request-inbox bind mount from Compose,
  then restore the prior scanner pause state. Preserve Discovery, runs, FASTQ,
  results, logs, volumes, and pipeline releases.

## 2026-07-13 T119 operations age, Intake archive, and NIPT small batches

- Branch/worktree: `codex/platform/T119-operations-age-intake-archive-nipt-batches`
  in the isolated T096 worktree, based on T118 commit `224a792`.
- Dashboard terminal rows add a locally refreshed relative age and one shared
  Search operations query for Run Tracker and Intake; each table retains its
  own pagination.
- Intake lifecycle migration `20260713_0005` preserves completed records as
  archived audit/idempotency rows. PGT-A manifest/READY publication moves
  atomically to `.archive/YYYY/MM/<request_id>`; NIPT FASTQ is never moved.
- Scheduled NIPT discovery is restricted to `BS_DEMO_20260713` and automatic
  NIPT submission remains disabled. Manual full validation is serialized by
  the existing one-slot pool.
- Safety backup created before migration at
  `/home/jiucheng/project/airflow-demo-backups/T119-20260713T140647` with
  Airflow/biodemo dumps, inventories, PGT-A inbox tar, and SHA256SUMS.
- Deployment is healthy from `/home/jiucheng/project/airflow-demo-t119` and
  Alembic `20260713_0005` is applied. Biodemo now contains 8 successful runs
  and 129 samples. Intake contains 6 archived rows and 0 active rows: three
  completed PGT-A manifests and the three T119 NIPT batches.
- BS transfer produced checksum/gzip/R1-R2 verified synthetic batches with
  10, 15, and 20 samples under the restricted `BS_DEMO_20260713` root. Transfer
  provenance is retained on BS under `result/t119_transfer_20260713` and on
  fengxian beside the intake batches; temporary transfer archives were removed.
- Full NIPT S9 runs completed serially:
  `NIPT_20260713_080217_DEC52B` (10 samples, 96/96 terminal success events,
  10/10 QC pass, 6m57s), `NIPT_20260713_090714_C941EA` (15 samples, 136/136,
  15/15 QC pass), and `NIPT_20260713_095250_374EA9` (20 samples, 176/176,
  20/20 QC pass, 9m13s).
- The 15-sample first attempt exhausted its 60 GiB container cgroup while
  mapping at 40 cores. A controlled same-workdir resume used 32 cores,
  `--rerun-incomplete`, and exact Airflow REST task clearing; no `--forceall`
  or input mutation was used. Its displayed 38m58s includes the failed attempt,
  diagnosis gap, and resume.
- A regression found during that resume allowed stale failed JSONL events to
  overwrite authoritative Airflow success during `sync-airflow`. The sync now
  imports fallback events and then reapplies terminal Airflow state; the new
  regression test and full backend suite pass.
- Engineering signals were present in final artifacts: T13 segment gain
  z-score 8.41, T18 chromosome-18 z-score 7.40, and T21 chromosome-21 z-score
  16.23 with classifier `Trisomy 21`. These are workflow checks, not clinical
  validation claims.
- Final verification: backend full pytest 168 passed; frontend Vitest 40
  passed; production `tsc -b && vite build` passed; Intake DAG tests 3 passed;
  Compose config and HTTP health passed. Live 1280/390 browser checks had no
  document overflow, showed terminal relative ages, and Settings displayed all
  6 archived records.
- Scanner was restored unpaused. Two successful post-rollout cycles left
  active Intake at 0; NIPT auto-submit remains disabled. A first DAG test used
  the image default interpreter and could not import Airflow; rerunning with
  `/home/airflow/.local/bin/python` passed. The first CLI date-based task clear
  selected nothing, so the recovery used the exact official REST endpoint.
- Rollback: pause `bio_intake_scan`, restore prior backend/frontend images and
  config, and preserve databases, FASTQ, workdirs, logs, results, volumes, and
  pipeline releases.

## 2026-07-13 T118 manifest hardening and five-sample auto intake

- Branch/worktree: `codex/intake/T118-manifest-hardening-log-retention` in the
  isolated T096 worktree, based on T117 commit `c69623a`.
- Parser ignores empty/whitespace-only rows but still rejects malformed
  non-empty rows. Later parse errors preserve submitted state and analysis ID;
  restoring the valid request clears the warning.
- Scanner was paused, biodemo backed up, and the legacy T112 false-error
  Discovery was repaired by exact batch/run/status conditions. The next scan
  preserved submitted state; scanner was restored unpaused.
- `project-20260713-five-samples.samples.tsv` contains H1, H2, H6, H8, and H9
  from one 2026-06-08 source batch. Dry-run resolved 5 samples, 10 FASTQ, and
  17.47 GB before manifest and READY were atomically published.
- Two stable scans created/submitted only `PGTA_20260713_034634_939AFF`; a
  third scan stayed idempotent. The run is active in Mapping/fastp_bwa and was
  intentionally not awaited to completion.
- Targeted 17 and full backend 141 tests passed remotely. Backend, scanner,
  and frontend HTTP are healthy.
- 212 scanner runs produced 211 worker task logs totaling about 2.5 MB;
  Airflow DB is 13 MB. At 10-minute cadence this is 52,560 runs/year. Follow
  up with 50 MB x 3 Docker rotation and 30-day scanner-only log/metadata
  retention.
- Backup: `/home/jiucheng/project/airflow-demo-t117/backups/T118-20260713-intake-repair`.
- Rollback: pause scanner and redeploy T117 backend. Restore biodemo only in a
  maintenance window with no newer writes. Never delete FASTQ, workdirs,
  results, or Docker volumes.

## 2026-07-13 T117 Submit semantics, workflow graph, and PGT-A intake recovery

- Branch/worktree: `codex/platform/T117-submit-workflow-intake-fix` in the
  isolated T096 worktree, based on T116 commit `a5bf5d5`.
- Submit: the optional audit field is named `Submitted by` to avoid confusion
  with Airflow task Operators. It is a free-text ID that defaults to
  `jiucheng`, suggests `jiucheng` and `airflow`, and remembers the last
  non-empty value in browser localStorage. Target-capture wording was replaced
  with pipeline-specific low-pass WGS.
- Runs: `/api/runs` returns one-query workflow summaries. Batch Runs renders a
  compact phase rail instead of QC metric lists; Run Detail moves skipped
  Airflow branches to `Alternate paths / Not selected branch`.
- Operator maintenance: exact preview/apply changed the two retained PGT-A
  `codex-validation` labels to `jiucheng` and wrote audited RunAction rows.
- Intake: `project-20260712` contained two space-delimited rows. The parser now
  reports line errors and permits correction only for an error with no run.
  Four FASTQ pairs were unchanged.
- Runtime acceptance: two scans created/submitted only
  `PGTA_20260712_171630_AE8239`; a third scan kept total=1. The run is active
  in `pgta_predict.run_pgta_mapping / fastp_bwa`; terminal completion was not
  required by the approved scope.
- Verification: backend 139, frontend 38, and DAG/runner 90 tests passed with
  5 expected logger skips. Production build, Compose, HTTP health, and browser
  checks at 1280/390 passed without document overflow.
- Backup: `/home/jiucheng/project/airflow-demo-t117/backups/T117-20260713-012000`.
- Rollback: pause scanner, restore biodemo only before accepting newer writes,
  restore the original manifest, and redeploy T116 backend/frontend. Do not
  delete the active run workdir, FASTQ, results, or Docker volumes.

## 2026-07-12 T116 strict Intake and Airflow history cleanup complete

- Goal: retain only the three fully validated analysis runs, remove obsolete
  discovery/Airflow history, and remove legacy WES/PGT-A validation DAGs from
  the deployed Airflow UI without deleting analysis files.
- Branch/worktree: `codex/platform/T116-airflow-intake-history-cleanup` in
  `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`, based on
  T115 commit `69f2b1e`.
- Safety: `bio_intake_scan` was recorded as unpaused, paused for maintenance,
  and restored to unpaused. No active PGT-A/NIPT run existed. Cleanup CLIs
  froze exact snapshots and aborted on count/state/content changes.
- Backup: `/home/jiucheng/project/airflow-demo-t116/backups/T116-20260712-014626`
  contains Airflow and biodemo custom-format dumps, before/after JSON
  inventories, preview/apply output, and verified `SHA256SUMS`.
- Applied: Airflow deleted 107 individual old runs plus the complete metadata
  for `bio_pgta_airflow` and `bio_wes_qsub`; Intake Discovery deleted 24 of 25
  rows. Biodemo remains 3 runs and 75 samples.
- Final Airflow: only `bio_pgta`, `bio_nipt_docker`, and `bio_intake_scan` are
  parsed. PGT-A retains 2 full successful runs, NIPT retains 1 full successful
  run. Scanner retained its maintenance-window latest success and continues to
  produce normal successful scheduled runs after unpause.
- Intake recurrence guard: scheduled intake defaults to PGT-A only. The first
  and subsequent post-cleanup cycles incremented the retained manifest
  observation and left discovery at one row; NIPT manual server
  scanning/submission is unchanged.
- Tests: remote backend pytest passed 134. Full DAG unittest passed 90 with 5
  expected logger-interface skips after supplying the required repo mounts.
  Compose config, DagBag import, backend/frontend HTTP, retained workdirs, and
  post-cleanup API inventories passed.
- Initial DAG test command omitted config/scripts/pipelines mounts and produced
  6 file-not-found errors; rerunning with the documented read-only mounts
  passed. No product code change was needed for those errors.
- Rollback: before any new run, pause scanner and restore both pg_dump files,
  then remove the two `.airflowignore` entries and recreate backend/Airflow
  services. After new runs exist, do not restore whole databases without a new
  coordinated maintenance window.

## 2026-07-12 T115 Platform Settings discovery tracker complete

- Goal: make Platform Settings operationally readable and align Discovery
  records with the dense Run Tracker table/pagination experience.
- Branch/worktree: `codex/platform/T115-settings-discovery-table` in
  `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`, based on
  T114 commit `100dd9d`.
- Backend: `GET /api/intake/status` now supports `pipeline`, composite `state`,
  `keyword`, `limit`, and `offset`, returning `total/limit/offset` while keeping
  the existing `items` contract. No DB migration or intake write path changed.
- Frontend: Dashboard and Settings share `IntakeDiscoveryTable`. Settings
  renders one batch per row, 10 rows per page, pipeline/state/keyword filters,
  Analysis links, independent config/scanner/discovery/preview errors, and a
  corrected six-metric dry-run summary.
- Review hardening: stale discovery/preview responses are ignored, failed
  refreshes clear old rows/results, invalid offsets return to the last valid
  page, and one config failure produces a single live accessibility alert.
- Responsive UI: action controls wrap without escaping the panel; long paths
  truncate with full tooltip text. Browser checks at 1440, 1280, 1024, and 390
  CSS pixels had no document horizontal overflow; only the table container
  scrolls at narrow widths. Browser console had no errors.
- Deployment: `/home/jiucheng/project/airflow-demo-t115`; only backend and
  frontend were recreated. Airflow, Postgres, Redis, volumes, workdirs, and
  pipeline processes were untouched.
- Runtime evidence: frontend returned HTTP 200, backend health returned ok,
  `/api/intake/status` reported 25 records with working ready/pipeline/keyword
  filtering, and the business run list remained the retained 3 successful
  runs. `bio_intake_scan` remained unpaused; PGT-A manifest intake remains
  enabled and NIPT auto intake remains disabled.
- Tests: backend full pytest passed 129; frontend Docker test target passed 36;
  production `tsc -b && vite build` and Compose config passed.
- Startup probe: the curl issued in the same command as the final frontend
  recreate saw one connection reset while nginx workers were starting. Logs
  were clean, Compose reported the container Up, and the condition-based
  follow-up returned HTTP 200 without another rebuild or restart.
- Lint: `frontend/package.json` has no lint script; no synthetic lint command
  was added. TypeScript checking remains part of the production build.
- Rollback: recreate backend/frontend from the T114 images/source. No database
  restore is needed because T115 has no migration or data mutation.

## 2026-07-11 T114 run status, timing, QC, and cleanup complete

- Goal: keep Run Tracker compact, use immutable submit-to-first-finish timing,
  repair NIPT sample QC semantics, validate CNV output completeness, and remove
  obsolete biodemo records without exposing a frontend delete action.
- Branch/worktree: `codex/platform/T114-run-status-timing-qc-repair` in
  `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`, based on
  T113 commit `6d0ad57`.
- Deployment: `/home/jiucheng/project/airflow-demo-t114`; backend, Airflow API,
  scheduler, worker, and frontend were rebuilt/recreated without deleting a
  Docker volume or run workdir.
- UI: Run Tracker now has one combined Status and no sample-QC highlight list.
  Started means Airflow handoff; Finished uses first pipeline completion.
  Terminal success shows Completed. Intake and Tracker share the main-column
  width. Run Detail uses the same timing and sample-level QC summary.
- Timing: migration `20260711_0004` adds immutable
  `analysis_run.pipeline_finished_at`. ETA history accepts only clean,
  successful, same-profile `mode=new` runs and adjusts for sample count.
- NIPT repair: regenerated and re-imported
  `NIPT_20260711_111140_63C5A6/reports/qc_summary.tsv`. The run now has 504
  metrics, 72/72 pass samples, no sample unknown, completion
  `2026-07-11T11:36:18.353341Z`, and runtime 1477 seconds from submission.
- Integrity: PGT-A predict collection checks manifest/status/statistics;
  NIPT full collection checks manifest/mappingQC/model-prediction rows and
  every sample statistics/aberration output.
- Backup: `/home/jiucheng/project/airflow-demo-t114/backups/T114-20260711-2230`.
  The pg_dump SHA256 is
  `55073a1a77b0ad83069a0b66097dea56e1a870949708b341e536a0b48877d776`;
  the run-inventory SHA256 is
  `4ed13baa90a9fe1d57997b5a797d5368478f8a7b4638337aac6a0771ea2f596d`.
- Cleanup: CLI preview and apply both required an exact 49-run snapshot. It
  deleted 46 biodemo runs and retained 3 complete runs / 75 samples. The stale
  WES running mock required an explicit exact-ID override. Airflow metadata,
  workdirs, logs, outputs, FASTQ, pipeline releases, and volumes remain intact.
- Intake: `bio_intake_scan` was paused for backup/cleanup and restored to its
  original unpaused state. PGT-A READY manifest intake remains enabled; NIPT
  automatic intake remains disabled.
- Tests: remote backend full pytest passed 127; Airflow/DAG/runner discovery
  passed 89 with 5 expected logger-interface skips; frontend Vitest passed 28;
  production TypeScript/Vite build and Compose config passed.
- Browser: live Dashboard at 1280/390 and NIPT Run Detail/QC at 390 had no
  document-level horizontal overflow. Tracker/Intake widths matched; wide
  tables scrolled inside their containers; QC rendered 20 rows per page.
- Rollback: code can be rolled back by recreating services from the prior
  image. Deleted biodemo rows require a separately approved, write-stopped
  restore from the T114 dump; do not restore over a live database casually.
- Next: add authenticated/admin audit controls before any UI deletion feature.
  Airflow metadata archival should be a separate task from biodemo retention.

## 2026-07-11 T113 NIPT Snakemake 9 full analysis complete

- Goal: preserve the approved NIPTPro 1.0.11 analysis tools while moving only
  Snakemake scheduling to 9.23.1 and exposing live rule/sample state.
- Branch/worktree: `codex/nipt/T113-nipt-s9-full-run` in
  `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`, based on
  T112 commit `14853ee`.
- Implementation commit: `b859649`.
- Image: `airflow-demo/niptpro:1.0.11-snakemake9.23.1-v1`, image ID
  `sha256:71df36b7f8080762f2db771e13e4daa7f4a666b3e1efc19c3bf12add22187254`.
  `/opt/snakemake9` contains Python 3.12/Snakemake 9.23.1; the original
  `/opt/conda` Snakemake 7.32.4 analysis toolchain is unchanged.
- Full validation: `NIPT_20260711_111140_63C5A6` completed the 72-sample,
  591-job workflow in about 24.8 minutes. The final database contains 592
  successful terminal events including the parent workflow event, with no
  residual running or failed jobs.
- S7 comparison: samplesheet, mapping QC, model prediction, chr21 outputs, and
  four summary CSVs are byte-identical. Observed peak memory was 44.61 GiB;
  source FASTQ and NIPT bundle stat manifests did not change.
- A post-compute permission failure exposed control-directory ownership and
  samplesheet idempotence defects. Both were fixed; exact Airflow task clear
  resumed the existing workdir and Snakemake reused completed outputs instead
  of recomputing the batch.
- Observability: `/progress` returns current phase/rule/sample and rule counts;
  `/rules` supports filters/pagination and phase summaries; relative rule logs
  are safely indexed beneath the run workdir; resume attempts append rather
  than overwrite workflow logs.
- Runtime: `bio_nipt_docker` remains a four-task project DAG, with
  `max_active_runs=1`, pool `nipt_s9_full=1`, and a 90-minute execution timeout.
  Manual Submit defaults to Full analysis with a 40-core/60-GiB confirmation.
  NIPT automatic intake remains disabled.
- Final regression: backend `117 passed`; Airflow/DAG runner `87 passed` with
  5 expected logger-interface skips; frontend `26 passed`; production frontend
  build, Compose config, Airflow import check, backend/Airflow health, and
  frontend HTTP 200 all passed after redeployment.
- Snakemake 9 dry-run expanded the selected 72-sample batch to 591 jobs and
  passed. `--lint` reported only pre-existing style warnings in the read-only
  NIPT workflow (for example missing per-rule log directives); it reported no
  parse or Snakemake 9 migration error.
- Runtime API spot-check: the full run is `success`, progress is 100%, all 592
  events are terminal success, QC exposes 504 metrics, the log index exposes
  227 workflow/rule sources, and a historical PGT-A detail remains `success`.
- The local in-app browser could not route to the private `fengxian` host, so a
  new live visual screenshot was not used as acceptance evidence. Dockerized
  frontend tests, production build, remote HTTP 200, and API spot-checks passed.
- Rollback artifact:
  `/home/jiucheng/pipelines/NIPT/images/niptpro-1.0.11-s9-v1/` contains image
  inspect/checksum files, both runtime package inventories, a version summary,
  and a 1.9-GiB OCI gzip archive with SHA256.
- Safety: this is engineering consistency validation, not clinical validation.
  Roll back by setting `NIPT_ALLOW_HEAVY_RUN=false`, selecting hidden profile
  `niptpro-1.0.11`, and recreating backend/worker/frontend without deleting
  volumes, run workdirs, source FASTQ, or historical records.

## 2026-07-11 T112 PGT-A Snakemake 9 predict and manifest intake complete

- Goal: deploy a separate PGT-A S9 predict workflow, expose rule-level status,
  add safe READY-manifest intake, and improve timing/QC/log observability.
- Branch/worktree: `codex/pgta/T112-pgta-s9-predict-intake` in
  `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`.
- Release: `/home/jiucheng/pipelines/PGT_A_S9/releases/pgta-s9-v1.4`; `current`
  points to the SHA256-verified release. Original `/home/jiucheng/pipelines/PGT_A`
  was not modified.
- Runtime boundary: Airflow uses `CeleryExecutor` for project-level tasks. A
  Celery worker runs Snakemake 9, which schedules rule/sample concurrency inside
  that task; H4 and H5 mapping ran concurrently in one Snakemake execution.
- Validation passed:
  - 2 x 1M paired-read run `PGTA_20260711_061816_F1E358`.
  - Full H3 run `PGTA_20260711_062522_4C4FC2`.
  - Full H4/H5 READY-manifest run `PGTA_20260711_071416_C8C7BA`.
- The full manifest run produced 32 successful terminal events, 20 passing QC
  metrics, complete WisecondorX outputs, and no residual running/failed events.
  A third scanner pass reused the same analysis ID, proving intake idempotency.
- Runtime: migration `20260711_0003`; pool `pgta_s9_full=1`;
  `bio_pgta_airflow` remains deprecated/paused; `bio_intake_scan` is unpaused;
  PGT-A manifest auto-submit is enabled; NIPT auto-submit and full-run remain
  disabled.
- Post-review hardening makes observed READY requests immutable, recovers a run
  committed before the discovery link, authenticates scanner/event service
  calls, verifies every S9 release file, fixes NIPT percentage-point display,
  and exposes the active manifest inbox in read-only Settings.
- Tests: backend 113 passed; Airflow 79 passed with 5 expected environment
  skips; actual Snakemake 9 logger 5 passed; frontend 25 passed; production
  frontend build and Compose config passed.
- Browser: Dashboard, Submit, and the full manifest Run Detail loaded live data
  at 1440 and 390 CSS pixels with no document overflow or error boundary;
  Settings also shows manifest inbox/mode/READY policy at 390 without overflow.
- Safety statement: this is engineering workflow validation, not a claim of
  clinical production validation.
- Rollback: pause `bio_intake_scan`, set PGT-A auto-submit false, point `current`
  and the approved profile to the prior immutable release, then recreate affected
  services. Do not delete historical runs, source FASTQ files, or Docker volumes.

> Agent 交接记录。最新记录放在最上面。

## Handoff Template

```markdown
## <YYYY-MM-DD HH:MM> - <agent name> - <task id/title>

### Goal

### Completed

### Changed files

### Commands run

| Command | Result | Notes |
|---|---|---|
|  |  |  |

### Tests

### Not run / why

### Current git status

### Risks

### Open questions

### Next recommended task

### Rollback notes
```

## Records

## 2026-07-10 18:30 - Codex - T111 Snakemake config editor and runtime profiles

### Goal

Allow PGT-A and NIPT Docker submissions to select approved runtime profiles and
edit only schema-approved Snakemake YAML for the current run, without exposing
Docker Compose or allowing arbitrary images, executables, or host paths.

### Completed

- Added sanitized PGT-A/NIPT profile templates, strict YAML validation, stale
  profile hash protection, and immutable requested/resolved provenance files.
- Added the collapsed Submit Run editor with server validation, reset, changed
  path summary, and create/submit gating.
- Added Run Detail requested/resolved config display and hid Compose artifacts.
- Kept existing DAG IDs, TaskGroups, heavy-run gate, rerun behavior, and intake
  settings unchanged.
- Fixed a deployment issue found by smoke testing: the worker-specific Compose
  volume list overrode the common list and omitted `/opt/airflow/config`. A
  regression test now requires the read-only profile mount in the worker.
- Closed review findings for non-finite numbers, stale validation responses,
  `PROFILE_CHANGED` recovery, config symlinks, PGT-A software-path coverage,
  NIPT profile-root drift, and hidden runtime snapshot provenance.

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote full backend pytest | success | 103 passed |
| remote Airflow unittest discovery | success | 74 passed, 5 expected logger-interface skips |
| remote frontend Docker test target | success | 24 Vitest tests passed |
| remote Compose image build | success | backend, worker, scheduler, frontend; production `tsc -b && vite build` passed |
| remote Compose config and service recreate | success | recreated backend, worker, scheduler, frontend only; no volume deletion |
| Airflow DAG import check | success | `No data found` |
| PGT-A metadata config smoke | success | final profile run `PGTA_20260710_110056_DC8A8D` reached success |
| NIPT config mount smoke | success | final profile run `NIPT_20260710_110057_79A631` reached success |
| approved runtime availability probe | success | PGT-A executable/reference/Snakefile and both NIPT images available in worker |
| browser responsive check | success | Submit/Config at 1440 and 390; no document overflow |
| intake scanner state | success | `airflow_reachable=true`, `is_paused=true` |

### Tests

The first two runtime smokes failed at `validate_request` because the Airflow
worker did not receive the Profile config mount. After the Compose regression
test failed and the explicit worker mount was added, fresh PGT-A/NIPT smoke
runs both succeeded and exposed resolved provenance through the backend API.

### Not run / why

- `npm run lint` is unavailable because the frontend package has no lint script.
- PGT-A `baseline_qc` and NIPT `full_run` were not run because they are heavy.
- `bio_intake_scan` was not unpaused and automatic submission remains disabled.

### Current git status

T111 changes are ready for one final verification pass and commit on
`codex/frontend/T111-snakemake-config-editor`, based on T110 `b56c405`.

### Risks

- Profile IDs/revisions are deployment contracts. Updating an existing profile
  changes its hash and correctly rejects stale Submit pages with
  `PROFILE_CHANGED`; operators must reload defaults.
- Resolved config intentionally includes exact execution paths for run audit;
  the Submit template never returns hidden runtime/profile path data.

### Next recommended task

Add a read-only Runtime Profile catalog and a clone-run-with-config workflow;
keep profile file editing and arbitrary runtime paths outside the frontend.

### Rollback notes

Revert the T111 commit and recreate backend, Airflow worker/scheduler, and
frontend. Do not delete Postgres, Redis, Docker volumes, `shared/runs`, PGT-A
rawdata, or NIPT inputs. The two successful smoke runs and two failed
pre-mount diagnostic runs may remain as immutable audit history.

## 2026-07-10 12:35 - Codex - T110 Operator Workspace stability and action closure

### Goal

Harden the T109 Control Tower for real operator use: remove document-level
horizontal overflow, replace truncated client-side resources with paginated
backend APIs, eliminate Failure Triage N+1 calls, and split oversized frontend
pages while preserving PGT-A and NIPT Docker runtime behavior.

### Completed

- Extended `/api/runs` with keyword, sort, pagination, and `project_name` while
  retaining old call compatibility and page-level sample/QC aggregation.
- Added paginated `/api/samples` and `/api/failures`; sample list paths expose
  only folder/file basenames, and workflow failures remain distinct from QC
  failures.
- Added `pipeline=deployed` for the operator Runs view so historical WES rows
  remain available to compatible API callers but are not shown as deployed.
- Moved resource counting, sorting, and pagination into SQL; Dashboard page
  sample/QC/rule/history data is bulk loaded instead of queried per row.
- Sanitized Failure Triage stderr excerpts for absolute server paths and common
  secret assignments while keeping file basenames and diagnostic text.
- Kept QC alerts as independent issues even when the same run also has a
  workflow failure.
- Changed Dashboard terminal progress to persisted DB/rule state so terminal
  pages do not call Airflow task-instance REST.
- Rebuilt Batch Runs, Sample Matrix, and Failure Triage around URL-backed server
  filters and pagination. Removed unsupported bulk action placeholders.
- Added real global project/run search and changed the demo user control to a
  non-interactive environment label.
- Isolated Dashboard Overview, Tracker, Intake, and Resources loading/errors;
  summary metrics link to the corresponding resource view.
- Split Dashboard, Run Detail, and Failure Triage into feature components.
  Run Detail keeps layered workflow, 96-sample QC matrix, manifest/config, and
  controlled PGT-A actions.
- Fixed responsive layout at 1440, 1280, 1024, and 390 CSS pixels, including
  long run ids, historical manifests, and mobile tracker controls.
- Rebuilt and recreated backend/frontend only. Airflow services were not
  restarted, no workflow was submitted, and `bio_intake_scan` remains paused.
- Independent focused re-review reported no remaining Critical or Important
  issues after the pagination, scope, sanitization, and debounce fixes.

### Changed files

- `backend/app/main.py`, `backend/app/run_service.py`,
  `backend/app/dashboard_service.py`, `backend/app/operator_resources_service.py`
- `backend/tests/test_dashboard_service.py`,
  `backend/tests/test_operator_resources.py`, `backend/tests/test_run_submit.py`
- `frontend/src/api.ts`, `frontend/src/App.test.tsx`, `frontend/src/styles.css`
- `frontend/src/layout/AppShell.tsx`, `frontend/src/components/RunTable.tsx`
- `frontend/src/pages/DashboardPage.tsx`, `RunsPage.tsx`, `SamplesPage.tsx`,
  `FailuresPage.tsx`, `RunDetailPage.tsx`
- `frontend/src/features/dashboard/*`, `features/failures/*`,
  `features/run-detail/*`
- `docs/05_API_CONTRACT.md`, `docs/06_FRONTEND_SPEC.md`, `DESIGN.md`,
  `TASKS.md`, `CURRENT_STATE.md`, `HANDOFF.md`, `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker run --rm airflow-demo/backend:t110-final-review pytest -q` | passed | 94 tests |
| `docker build --target test -f frontend/Dockerfile frontend` | passed | 20 Vitest tests |
| `docker build -f frontend/Dockerfile frontend` | passed | `tsc -b && vite build` |
| `docker compose ... config --quiet` | passed | isolated remote worktree plus deployment env |
| `docker compose ... build backend frontend` | passed | production tags rebuilt |
| `docker compose ... up -d --no-deps --force-recreate backend frontend` | passed | no Airflow/DB/Redis restart |
| five warm `/api/dashboard/runs?pipeline=all&limit=10&offset=0` requests | passed | final median about 33 ms; no active rows |
| browser responsive matrix | passed | 6 pages x 4 viewports, 24/24 no document overflow |

### Tests

- Backend full suite: 94 passed.
- Frontend suite: 20 passed after final review fixes.
- Production TypeScript/Vite build passed.
- Live API checks passed for health, runs, samples, failures, and scanner state.
- Frontend 12959 returned HTTP 200 after final recreate.

### Not run / why

- No PGT-A `baseline_qc`, NIPT `full_run`, or metadata smoke was submitted;
  T110 does not change execution behavior.
- No Airflow DAG test was rerun because T110 changes no DAG or runner files.

### Current git status

Clean after the final T110 task commit on
`codex/frontend/T110-operator-workspace-hardening`.

### Risks

- Sample `report_status` is currently inferred from terminal workflow state;
  a future artifact-aware field can make report availability exact.
- Failure diagnosis suggestions are deterministic operational hints, not a
  replacement for captured stderr review.

### Next recommended task

Add operator authentication/authorization and artifact-aware report status
before enabling automatic intake or broader production access.

### Rollback notes

Redeploy backend/frontend images from T109 commit `bcdc439`. No schema rollback
is required because T110 adds no migration. Do not delete volumes.

## 2026-07-09 02:40 - Codex - T109 PGT-A/NIPT Control Tower frontend polish

### Goal

Apply the frontend-only Control Tower polish from the review doc while keeping
the deployed workflow scope to PGT-A and NIPT Docker. Do not add UI framework
dependencies, do not change backend APIs, do not change DAGs, do not unpause
intake, and do not run NIPT full_run.

### Completed

- Renamed the operator IA to `Command Center`, `Submit Run`, `Batch Runs`,
  `Sample Matrix`, `Workflow Catalog`, `Failure Triage`, and
  `Platform Settings`.
- Added CSS theme tokens, dark sidebar, softer status/progress color palette,
  Dashboard command summary strip, and visual polish for cards/tables.
- Kept Dashboard on aggregate APIs only and preserved 10-row Run Tracker
  pagination; no per-run detail/progress/rules fan-out was reintroduced.
- Converted Submit into a visual four-step flow: pipeline, server batch,
  preview, Airflow handoff, while preserving current PGT-A/NIPT create+submit
  behavior.
- Added frontend-only stage label mapping plus a Run Detail layered timeline:
  Airflow project tasks above Snakemake/runner pipeline steps; raw task/rule ids
  remain available as debug text.
- Updated `DESIGN.md`, `docs/06_FRONTEND_SPEC.md`, `TASKS.md`,
  `CURRENT_STATE.md`, and `MANIFEST.json`.

### Changed files

- `frontend/src/layout/AppShell.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/components/RunTracker.tsx`
- `frontend/src/pages/SubmitPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/RunsPage.tsx`
- `frontend/src/pages/SamplesPage.tsx`
- `frontend/src/pages/FailuresPage.tsx`
- `frontend/src/pages/WorkflowsPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/lib/stageLabels.ts`
- `frontend/src/lib/format.ts`
- `frontend/src/mocks/platform.ts`
- `frontend/src/styles.css`
- `frontend/src/App.test.tsx`
- `DESIGN.md`
- `docs/06_FRONTEND_SPEC.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `MANIFEST.json`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/frontend/T109-control-tower-polish` | success | Created local T109 branch in the T096 worktree |
| local `npm test -- --run` | failed to start | Local Windows environment has no `npm` on PATH and no bundled workspace Node runtime |
| local `git diff --check` | success | No whitespace errors |
| local manifest consistency check | success | `file_count=189`, listed files `189`, missing `0` |
| remote `git worktree add /home/jiucheng/project/airflow-demo-worktrees/T109-control-tower-polish origin/main -b codex/frontend/T109-control-tower-polish-remote` | success | Created a clean remote test worktree; did not mutate the dirty deployment source tree |
| remote `git diff --check` in T109 worktree | success | No whitespace errors |
| remote `docker build --target test -f frontend/Dockerfile frontend` | success after one test-query fix | 14 Vitest tests passed |
| remote `docker compose -f docker-compose.yaml config --quiet` in deployment dir | success | Actual deployment dir has the required `.env`; clean test worktree intentionally does not |
| remote `docker compose --env-file /home/jiucheng/project/airflow-demo/.env -f docker-compose.yaml build frontend` in T109 worktree | success | Frontend production build ran `tsc -b && vite build` |
| remote `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` in deployment dir | success | Recreated only frontend; no volumes deleted |
| remote `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 from nginx |
| remote dashboard runs spot check | success | `/api/dashboard/runs?pipeline=all&limit=10&offset=0` returned JSON items |

### Tests

Remote acceptance passed for the frontend-only change: Dockerized frontend test
target passed 14 Vitest tests, production frontend build passed, frontend
container was recreated, and port `12959` returned HTTP 200.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no lint script.
- Local npm tests/build were not run because Windows has no `npm` on PATH in
  this Codex session.
- Backend, Airflow, and DAG tests were not run because T109 is frontend-only and
  does not change backend contracts, DAGs, runner behavior, or DB schema.
- Heavy PGT-A `baseline_qc`, NIPT `full_run`, and intake auto-submit were not
  run or enabled.

### Current git status

Local worktree is `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`
on `codex/frontend/T109-control-tower-polish` with T109 changes pending commit.
Remote validation used the separate clean worktree
`/home/jiucheng/project/airflow-demo-worktrees/T109-control-tower-polish`.
The existing remote deployment source tree remains on its dirty deployment
branch; only the frontend image/container was updated.

### Risks

- This is visual/information architecture polish; it does not add new backend
  timeline or failure-diagnosis data beyond existing APIs.
- The dark sidebar and command center tokens should be visually reviewed in a
  browser; automated tests cover behavior and text, not full aesthetics.
- Raw task/rule ids are still visible as debug text in Run Detail and Run
  Tracker, which is intentional for operator troubleshooting.

### Open questions

- Whether to add a screenshot-based visual QA pass for desktop and narrow
  widths before committing or merging.
- Whether future T110 should add real backend endpoints for richer failure
  diagnosis/config file content instead of continuing frontend-only polish.

### Next recommended task

Do a browser visual QA pass on the deployed T109 frontend, then commit and push
the T109 branch or fast-forward main according to the user's preferred release
flow.

### Rollback notes

Rebuild/redeploy the previous `airflow-demo/frontend:0.1.0` image from
`origin/main`/T108 and recreate only the frontend service. Do not run
`docker compose down -v`, do not prune volumes, and do not touch shared runs,
PGT-A rawdata, NIPT source folders, Postgres, Redis, or the paused
`bio_intake_scan` state.

## 2026-07-09 00:05 - Codex - T108 Dashboard/Run Detail usability polish and controlled PGT-A rerun

### Goal

Make Dashboard and Run Detail operator-readable for PGT-A/NIPT Docker demo use:
compact Intake scanner, better status/progress colors, sample throughput instead
of vague QC/failure focus, table Run Tracker with readable current stage and
runtime/ETA, Run Detail manifest/QC failure/config views, and a controlled
PGT-A baseline_qc stage rerun path. Do not unpause intake, do not run heavy
PGT-A baseline_qc, and do not run NIPT full_run.

### Completed

- Reworked Dashboard `QC / failure focus` into `Sample throughput` with
  `24h / 7d / 30d` period selector, sample-level totals, stacked distribution,
  and trend bars.
- Replaced Intake scanner card wall with a compact table/list using softer
  status pills for observed/bootstrap/ready/submitted/error states.
- Rebuilt Run Tracker into a dense table: Project and Run ID are links, no
  separate View button, timestamps omit the repeated `Asia/Shanghai` suffix,
  Airflow task and pipeline rule are combined into human-readable Current stage,
  and running rows show elapsed runtime plus ETA when historical average exists.
- Extended dashboard backend aggregation with `sample_summary`,
  `sample_trend`, `current_stage_label`, `current_stage_source`,
  `elapsed_seconds`, `average_duration_seconds`, `estimated_remaining_seconds`,
  and `estimated_finish_at`.
- Updated Run Detail: larger Current progress, selected sample manifest table,
  QC failure summary before the QC matrix, Files tab prioritizing useful
  logs/reports with Advanced files collapsed, and Config tab prioritizing
  Snakemake/NIPT config artifacts.
- Added controlled PGT-A `rerun_stage` reanalysis mode for baseline_qc runs only:
  `mapping`, `metadata`, or `baseline_qc`; arbitrary DAG/task trigger remains
  blocked, active runs are rejected, and runner still avoids `--forceall`.
- Deployed backend, airflow-worker, airflow-scheduler, and frontend on
  `fengxian`; light metadata smoke passed.

### Changed files

- `backend/app/dashboard_service.py`
- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/tests/test_dashboard_service.py`
- `backend/tests/test_pgta_reanalysis.py`
- `dags/bio_pgta.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_bio_pgta_dag.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `frontend/src/api.ts`
- `frontend/src/components/RunProgressBar.tsx`
- `frontend/src/components/RunTracker.tsx`
- `frontend/src/lib/format.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/styles.css`
- `frontend/src/App.test.tsx`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/frontend/T108-dashboard-run-detail-usability` | success | Created local T108 branch in the T096 worktree |
| local `py -m py_compile backend/app/dashboard_service.py backend/app/main.py backend/app/run_service.py dags/bio_pgta.py dags/pgta_metadata_runner.py` | success | Syntax-only local check; local pytest was not used for acceptance |
| local `git diff --check` | success | Whitespace check before remote overlay |
| local manifest/path consistency check | success | `file_count=188`, `missing=0`; first read needed `utf-8-sig` because `MANIFEST.json` has a BOM |
| remote `git diff --check` | success | Only existing CRLF warning for `docs/02_ENGINEERING_SPEC.md` |
| remote `docker compose -f docker-compose.yaml config --quiet` | success | No compose errors |
| remote `docker build --target test -f frontend/Dockerfile frontend` | success | 14 Vitest tests passed |
| remote backend targeted pytest in `airflow-demo/backend:t108-test` | success | 25 passed: dashboard, PGT-A reanalysis, progress, diagnostics |
| remote `docker build -t airflow-demo/airflow:t108-test airflow_image` | success | Built Airflow test image |
| remote Airflow test image unittest | success | 28 passed for `bio_pgta` DAG and PGT-A runner |
| remote `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend` | success | Frontend production build ran `tsc -b && vite build` |
| remote `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-worker airflow-scheduler frontend` | success | Recreated changed services only; did not delete volumes |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 from frontend |
| `GET /api/health` | success | `{"status":"ok"}` |
| `GET /api/dashboard/overview?pipeline=all&period=7d` | success | Returned `sample_summary` and `sample_trend` |
| `GET /api/dashboard/runs?pipeline=all&limit=10&offset=0` | success | Returned tracker rows with readable stage and ETA fields |
| `GET /api/system/resources` | success | Returned host CPU/MEM/disk metrics with `source=host_proc` |
| `GET /api/intake/status?limit=5` | success | Bootstrap/observed entries remained non-queued |
| PGT-A metadata smoke `PGTA_20260708_160227_EFAD64` | success | Create + submit + sync reached backend/Airflow `success`; `/progress` returned Airflow tasks plus `metadata=success` rule event |
| `git commit -m "feat: polish dashboard and controlled pgta rerun"` | success | Created T108 commit `0857e3d` with the validated source tree |
| `git branch -f main codex/frontend/T108-dashboard-run-detail-usability` | success | Fast-forwarded local `main` to T108; `main` was an ancestor |
| `git push origin main` | success | Fast-forwarded `origin/main` from `8b19b0d` to `0857e3d` |
| remote `git fetch origin main` on `fengxian` | success | Updated remote mirror `origin/main` to `0857e3d` without switching branches or overwriting the dirty deployment worktree |

### Tests

Remote acceptance passed on `ssh fengxian`. Frontend test target passed 14
Vitest tests. Backend targeted pytest passed 25 tests. Airflow DAG/runner unit
tests passed 28 tests in the Airflow image. The deployed frontend returned HTTP
200, backend health was ok, dashboard aggregate APIs returned the new T108
fields, and the light PGT-A metadata smoke reached success.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no lint script.
- Local pytest/frontend runtime checks were not used as acceptance evidence
  because AGENTS.md requires runtime validation on `ssh fengxian`.
- Heavy PGT-A `baseline_qc` was not run; T108 only used tests plus a light
  `metadata` smoke.
- NIPT `full_run` was not run and NIPT DAG decomposition was not changed.
- `bio_intake_scan` was not unpaused and no auto-submit was enabled.

### Current git status

Local worktree is `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`
on `codex/frontend/T108-dashboard-run-detail-usability`; T108 source was
committed as `0857e3d` and local/remote `main` were fast-forwarded to that
commit. Remote `/home/jiucheng/project/airflow-demo` has the T108 overlay
deployed for runtime validation and remains an uncommitted deployment mirror on
its existing branch; only its `origin/main` ref was fetched forward.

### Risks

- The remote mirror already had uncommitted overlays before T108. A pre-copy
  tar backup was attempted, but the remote file list had CRLF path endings and
  the backup command emitted missing-file warnings, so do not rely on that tar
  as a complete rollback point.
- ETA is a demo estimate from recent successful runs with the same
  pipeline/target or run_mode; UI labels it as an estimate.
- Controlled `rerun_stage` has unit/API coverage but no heavy baseline_qc
  runtime acceptance in T108.
- `bio_pgta` metadata runs now still show skipped TaskGroup stage tasks because
  the branch keeps metadata on the old `run_pgta_target` path.

### Open questions

- Whether to run a supervised PGT-A staged `baseline_qc` smoke next, or defer
  until the operator wants to validate compute-heavy behavior.
- Whether NIPT should get an Airflow TaskGroup decomposition next, or continue
  relying on runner/Snakemake events until the Docker full-run contract is
  finalized.

### Next recommended task

Do a short operator UI review of the deployed Dashboard and Run Detail, then
choose either T109 visual polish/live browser QA or a separate supervised
baseline_qc stage runtime smoke. Keep intake auto-submit disabled until the
operator explicitly approves unpausing `bio_intake_scan`.

### Rollback notes

Revert the T108 files and recreate backend, airflow-worker, airflow-scheduler,
and frontend. Do not run `docker compose down -v`, do not prune Docker volumes,
and do not delete `shared/runs`, PGT-A rawdata, NIPT source folders, or
Postgres/Redis volumes. If `rerun_stage` behavior is suspect, stop using
`mode=rerun_stage` and keep the existing `resume` path only.

## 2026-07-08 22:19 - Codex - T107 UI density fix and PGT-A DAG stages

### Goal

Fix the dense/awkward frontend surfaces reported by the user and stage only the
PGT-A `baseline_qc` Airflow path so Airflow can show project-level mapping,
metadata, and baseline QC phases. Do not change NIPT DAGs, do not edit the
production PGT-A Snakefile, and do not run a heavy baseline QC acceptance job.

### Completed

- Changed Submit Task `Submit preview` to a definition-style layout with
  consistent label/value spacing and full-width rows for long scan root and
  workflow fields.
- Added shared sample source formatting so Samples and Run Detail show R1/R2
  basenames and batch/folder context instead of raw absolute paths or `not set`.
- Replaced per-sample QC cards in Run Detail with a compact QC matrix table:
  one row per sample, metric columns, fail/warn-first sorting, sample search,
  status filter, and 20-row pagination.
- Staged PGT-A `baseline_qc` in `bio_pgta` with
  `TaskGroup("pgta_pipeline")`: mapping -> metadata -> baseline_qc.
- Preserved the old `run_pgta_target` task for `metadata`, `dryrun_cnv`, and
  `invalid_target` smoke paths.
- Added PGT-A runner stage entrypoints and stage-specific Snakemake
  stdout/stderr/command logs without `--forceall`.
- Updated progress weights and artifact discovery for the new staged PGT-A
  task names while retaining historical `run_pgta_target` compatibility.
- Updated API/frontend/Airflow/QC docs, task/state docs, manifest, and remote
  deployment.

### Changed files

- `frontend/src/lib/sampleFiles.ts`
- `frontend/src/pages/SubmitPage.tsx`
- `frontend/src/pages/SamplesPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/styles.css`
- `frontend/src/App.test.tsx`
- `backend/app/progress_service.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_progress.py`
- `backend/tests/test_run_diagnostics.py`
- `dags/bio_pgta.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_bio_pgta_dag.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `MANIFEST.json`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/frontend/T107-ui-pgta-dag-stages` | success | Created local T107 branch in the T096 worktree |
| `py -m py_compile backend\app\progress_service.py backend\app\diagnostics_service.py dags\pgta_metadata_runner.py` | success | Local syntax-only check |
| `git diff --check` | success | Local whitespace check before remote overlay |
| manifest consistency check | success | `file_count=188`, listed files `188`, missing `0` |
| remote `git diff --check` | success | Only an unrelated CRLF warning was printed |
| remote `docker compose -f docker-compose.yaml config --quiet` | success | No volume deletion or NIPT full-run changes |
| remote `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend` | success | Initial full image build |
| remote `docker compose -f docker-compose.yaml build backend frontend` | success | Rebuilt after final progress/frontend test fixes |
| remote `docker build --no-cache --target test -f frontend/Dockerfile frontend` | success | 13 Vitest tests passed |
| remote backend Docker targeted pytest | success | 19 passed: `test_run_progress.py`, `test_run_diagnostics.py` |
| remote Airflow worker unittest | success | 27 tests passed for `bio_pgta` DAG and PGT-A runner |
| remote `airflow dags list-import-errors` | success | `No data found` |
| remote `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-scheduler airflow-worker frontend` | success | Recreated only changed services; did not delete volumes |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `GET /api/health` and `/api/health/airflow` | success | Backend ok; Airflow metadatabase and scheduler healthy |
| remote `airflow tasks list bio_pgta --tree` | success | Shows `pgta_pipeline.run_pgta_mapping -> run_pgta_metadata -> run_pgta_baseline_qc` and old `run_pgta_target` branch |
| PGT-A metadata smoke | success | `PGTA_20260708_141653_B57AB6` reached backend/Airflow `success`; no heavy baseline QC run |

### Tests

Remote acceptance passed on `ssh fengxian`. The new staged DAG imported, the
frontend production Docker build passed `tsc -b && vite build`, the test target
passed 13 Vitest tests, backend targeted pytest passed, and Airflow worker
unittest passed. A light PGT-A metadata run verified the old non-baseline branch
still works after adding the TaskGroup branch.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no lint script.
- Local pytest/frontend runtime checks were not used as acceptance evidence
  because local Windows lacks the required Python/Node/Airflow dependencies and
  AGENTS.md requires runtime validation on `ssh fengxian`.
- A heavy PGT-A `baseline_qc` run was not started; T107 used DAG/import/unit
  validation for the staged path and a light metadata smoke for runtime safety.
- NIPT DAG decomposition and NIPT `full_run` were not touched.

### Current git status

Local worktree is `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`
on `codex/frontend/T107-ui-pgta-dag-stages` with T107 changes pending commit.
Remote `/home/jiucheng/project/airflow-demo` has the T107 overlay deployed for
runtime validation and still contains the earlier uncommitted deployment overlay.

### Risks

- `bio_pgta` metadata/dryrun branches now show skipped TaskGroup tasks in the
  Airflow task-instance list; this is expected branch behavior and the old
  `run_pgta_target` task remains the successful execution path.
- Stage-specific PGT-A Snakemake logs are exposed through artifacts/files; the
  existing log API stream names were not expanded in this task.
- Staged `baseline_qc` has not been proven with a real heavy run in T107. Run it
  only with explicit operator approval and enough compute/runtime window.
- The remote mirror is still an overlay workspace. Do not use `git reset`,
  `git checkout`, or broad file overwrites there.

### Open questions

- Whether to run a controlled staged `baseline_qc` smoke next, or first inspect
  the Airflow UI graph visually with the current import/unit validation.
- Whether NIPT should be decomposed into Airflow project-level TaskGroups next,
  or whether its exact rule visibility should stay runner-event-only until the
  Docker workflow contract is finalized.

### Next recommended task

Do a visual frontend/Airflow UI review on the deployed T107 build, then plan the
NIPT DAG decomposition separately. Only schedule a real PGT-A staged
`baseline_qc` smoke if the user explicitly approves the heavy runtime.

### Rollback notes

Revert T107 files and recreate backend, airflow-worker, airflow-scheduler, and
frontend. Do not delete Postgres, Docker volumes, `shared/runs`, PGT-A rawdata,
or NIPT source folders. Keep `bio_intake_scan` paused and leave NIPT full-run
disabled.

## 2026-07-08 20:47 - Codex - T106 Intake dry-run preview and auto-submit gating

### Goal

Add a read-only intake dry-run preview and make automatic intake submit obey
explicit config gates before any future `bio_intake_scan` unpause.

### Completed

- Added `POST /api/intake/scan-preview`, which scans configured PGT-A/NIPT roots
  and returns per-batch dry-run decisions without DB writes, run creation, or
  Airflow submit.
- Changed `scan-and-submit` so stable batches only create/submit when
  `defaults.auto_submit=true` and
  `pipelines.<name>.auto_submit.enabled=true`.
- Updated default `config/intake.yaml` so PGT-A and NIPT Docker auto-submit
  gates are explicitly disabled.
- Changed NIPT run creation root validation to read `config/intake.yaml` roots
  with env fallback, matching scanner behavior.
- Added Settings dry-run preview UI and frontend API types while keeping the
  page free of unpause, scan-now-submit, and full-run actions.
- Updated API/frontend/runbook docs, task/state docs, and remote deployment.

### Changed files

- `backend/app/intake_config.py`
- `backend/app/intake_service.py`
- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/tests/test_intake_service.py`
- `config/intake.yaml`
- `frontend/src/api.ts`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/styles.css`
- `frontend/src/App.test.tsx`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/intake/T106-intake-dry-run-gating` | success | Created local T106 branch in the T096 worktree |
| `py -3 -m pytest backend/tests/test_intake_service.py -q` | failed | Local Windows Python lacks `fastapi`; not acceptance evidence |
| `py -3 -m py_compile backend/app/intake_config.py backend/app/intake_service.py backend/app/main.py` | success | Local syntax-only check before remote tests |
| `git diff --check` | success | Local whitespace check before remote deployment |
| remote `docker compose -f docker-compose.yaml config --quiet` | success | No unsafe volume deletion or DAG unpause |
| remote backend Docker targeted pytest | success | 8 passed: `test_intake_service.py`, `test_intake_config.py` |
| remote `docker build --target test -f frontend/Dockerfile frontend` | success | 11 Vitest tests passed |
| remote `docker compose -f docker-compose.yaml build backend frontend` | success | Frontend production build ran `tsc -b && vite build` |
| remote `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend` | success | Recreated only backend and frontend; did not touch volumes or Airflow pause state |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `GET /api/health` and `/api/health/airflow` | success | Backend ok; Airflow metadatabase and scheduler healthy |
| `GET /api/intake/config` | success | Global and PGT-A/NIPT pipeline auto-submit gates disabled |
| `POST /api/intake/scan-preview` | success | `total_batches=21`, `would_submit=0` |
| preview before/after state comparison | success | intake discovery stayed `21/21`; NIPT run total stayed `5/5` |
| `airflow dags list \| grep bio_intake_scan` | success | Final column `True`; DAG remains paused |

### Tests

Remote acceptance passed on `ssh fengxian`. T106 did not submit any new PGT-A or
NIPT run, did not call `/api/intake/scan-and-submit` from the frontend, did not
unpause `bio_intake_scan`, and did not run NIPT `full_run`.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no lint script.
- Local pytest/frontend runtime checks were not used as acceptance evidence
  because local Windows lacks required Python/Node dependencies and AGENTS.md
  requires runtime validation on `ssh fengxian`.
- Airflow DAG import tests were not rerun because T106 did not modify DAG files.
- NIPT `full_run` was not run; it remains guarded by
  `NIPT_ALLOW_HEAVY_RUN=false` and needs explicit approval.

### Current git status

Local worktree is `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`
on `codex/intake/T106-intake-dry-run-gating` with T106 changes pending commit.
Remote `/home/jiucheng/project/airflow-demo` has the T106 overlay deployed for
runtime validation and still contains the earlier uncommitted deployment overlay.

### Risks

- Automatic intake is still disabled by config and `bio_intake_scan` remains
  paused. Enabling it requires a separate explicit T107 rollout.
- `/api/intake/scan-preview` scans real configured source roots; keep
  `max_samples` conservative for operator previews.
- The remote mirror remains an uncommitted overlay branch from prior frontend
  work; avoid `git reset`, `git checkout`, or broad overwrites there.

### Open questions

- Whether T107 should enable only discovery-only scheduled scans first, or
  also enable create+submit for PGT-A metadata / NIPT mount_smoke.
- Whether operators want marker-file ready rules before any production-like
  continuous auto intake.

### Next recommended task

Plan T107 only if the user explicitly approves enabling automatic intake.
Otherwise, T082 rollback/cleanup runbook remains the safest next housekeeping
task.

### Rollback notes

Revert T106 files and recreate backend/frontend. Do not delete Postgres, Docker
volumes, `shared/runs`, PGT-A rawdata, or NIPT source folders. Keep
`bio_intake_scan` paused during rollback unless the user separately approves
automatic intake.

## 2026-07-08 20:12 - Codex - T105 Intake settings and scanner readiness console

### Goal

Add a read-only Settings intake console that shows sanitized `config/intake.yaml`,
bootstrap discovery state, and whether Airflow `bio_intake_scan` is paused,
without exposing unpause, scan-now, or NIPT full-run actions.

### Completed

- Added `AirflowClient.get_dag()` and optional `order_by` for
  `list_dag_runs()`.
- Added `GET /api/intake/scanner-state`, which reads Airflow REST DAG metadata
  and latest DAG run, and returns a degraded payload if Airflow is unavailable.
- Added Settings Intake Scanner console with config summary, scanner DAG state,
  configured PGT-A/NIPT roots, and recent discovery records.
- Extracted intake discovery status display mapping into
  `frontend/src/lib/intake.ts` and reused it from Dashboard/Settings.
- Updated API/frontend/runbook docs, task/state docs, and manifest.

### Changed files

- `backend/app/airflow_client.py`
- `backend/app/main.py`
- `backend/tests/test_airflow_client.py`
- `backend/tests/test_intake_config.py`
- `frontend/src/api.ts`
- `frontend/src/lib/intake.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/styles.css`
- `frontend/src/App.test.tsx`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `MANIFEST.json`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/intake/T105-intake-settings-console` | success | Created local T105 branch in the T096 worktree |
| `python -m pytest ...` | failed | Local `python` is Windows Store shim with no output; not acceptance evidence |
| `py -3 -m pytest backend/tests/test_airflow_client.py backend/tests/test_intake_config.py -q` | failed | Local Python lacks `httpx` and `fastapi`; remote Docker pytest used for acceptance |
| `npm test -- --run src/App.test.tsx -t "read-only intake"` | failed | Local Windows has no `npm`; remote Docker frontend test used for acceptance |
| `py -3 -m py_compile backend/app/airflow_client.py backend/app/main.py` | success | Local syntax-only check |
| `git diff --check` | success | Local whitespace check |
| manifest consistency check | success | `file_count=187`, listed files `187`, missing `0` |
| remote `docker compose -f docker-compose.yaml config --quiet` | success | No compose changes required by T105 |
| remote backend Docker targeted pytest | success | 10 tests passed: `test_airflow_client.py`, `test_intake_config.py` |
| remote `docker build --target test -f frontend/Dockerfile frontend` | success | 11 Vitest tests passed |
| remote `docker compose -f docker-compose.yaml build backend frontend` | success | Frontend production build ran `tsc -b && vite build` |
| remote `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend` | success | Did not touch Postgres, Redis, volumes, Airflow services, or intake pause state |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `GET /api/health` and `/api/health/airflow` | success | Backend ok; Airflow metadatabase and scheduler healthy |
| `GET /api/intake/config` | success | Returned source `/app/config/intake.yaml`, PGT-A and NIPT Docker config |
| `GET /api/intake/status?limit=20` | success | Returned bootstrap observed records; no auto-submit triggered |
| `GET /api/intake/scanner-state` | success | `airflow_reachable=true`, `is_paused=true`, no latest DAG run yet |
| `airflow dags list \| grep bio_intake_scan` | success | Final column `True`; DAG remains paused |

### Tests

Remote acceptance passed on `ssh fengxian`. T105 did not submit any new
analysis run, did not call `/api/intake/scan-and-submit` from the frontend, did
not unpause `bio_intake_scan`, and did not run NIPT `full_run`.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no lint script.
- Local pytest/frontend runtime checks were not used as acceptance evidence
  because local Windows lacks required Python/Node dependencies and AGENTS.md
  requires runtime validation on `ssh fengxian`.
- Airflow DAG import tests were not rerun because T105 did not modify DAG files.
- NIPT `full_run` was not run; it remains guarded by
  `NIPT_ALLOW_HEAVY_RUN=false` and needs explicit approval.

### Current git status

Local worktree is `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`
on `codex/intake/T105-intake-settings-console` with T105 changes pending commit.
Remote `/home/jiucheng/project/airflow-demo` has the T105 overlay deployed for
runtime validation and still contains the earlier uncommitted deployment overlay.

### Risks

- The Settings page is intentionally read-only; enabling automatic intake still
  requires operator review and an explicit Airflow unpause outside the UI.
- `/api/intake/scanner-state` depends on Airflow REST. If Airflow is
  temporarily unavailable, the endpoint returns `airflow_reachable=false` rather
  than failing Settings.
- The remote mirror remains an uncommitted overlay branch from prior frontend
  work; avoid `git reset`, `git checkout`, or broad overwrites there.

### Open questions

- Whether operators want a future authenticated admin-only action to run
  bootstrap or unpause `bio_intake_scan` from the UI.
- Whether to expose Docker container stats to backend, or keep the current
  `host_proc` resource telemetry fallback.

### Next recommended task

Run an operator review of `/settings` and `/api/intake/status`, then either keep
`bio_intake_scan` paused for manual demo mode or plan a separate, explicit
auto-intake enablement task. `T082` rollback/cleanup runbook is also still todo.

### Rollback notes

Revert T105 files and recreate backend/frontend. Do not delete Postgres, Docker
volumes, `shared/runs`, PGT-A rawdata, or NIPT source folders. Keep
`bio_intake_scan` paused during rollback unless the user separately approves
automatic intake.

## 2026-07-08 17:10 - Codex - T104 Dashboard performance, observability, and intake config

### Goal

Replace Dashboard frontend fan-out with backend aggregate APIs, make Run Tracker
pipeline-driven and paginated, display node/resource/intake state clearly, and
move intake scanner roots into `config/intake.yaml`.

### Completed

- Added `/api/dashboard/overview`, `/api/dashboard/runs`,
  `/api/system/resources`, and `/api/intake/config`.
- Added `config/intake.yaml` and `INTAKE_CONFIG_PATH=/app/config/intake.yaml`;
  backend falls back to legacy env roots only if the YAML is missing.
- Added backend resource telemetry from host `/proc` plus Docker stats fallback.
- Changed Dashboard to left-side pipeline selection (`All pipelines`, `PGT-A`,
  `NIPT Docker`), visual status distribution/trend/QC panels, paginated
  10-row Run Tracker, intake scanner cards, and bottom health/resource/activity
  panels.
- Changed Run Tracker to consume `/api/dashboard/runs` rows instead of calling
  run detail/progress/rules for every visible run.
- Fixed intake display semantics so observed/bootstrap rows are not shown as
  queued execution.
- Updated API/frontend/Airflow/NIPT/runbook docs, task/state docs, and manifest.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `config/intake.yaml`
- `backend/app/config.py`
- `backend/app/dashboard_service.py`
- `backend/app/intake_config.py`
- `backend/app/intake_service.py`
- `backend/app/main.py`
- `backend/app/system_resources.py`
- `backend/requirements.txt`
- backend tests for dashboard, intake config, and system resources
- `frontend/src/api.ts`
- `frontend/src/components/RunTracker.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/styles.css`
- `frontend/src/App.test.tsx`
- docs/state/manifest files

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git diff --check` | success | Warning only: `docs/02_ENGINEERING_SPEC.md` CRLF will be normalized next time Git touches it |
| manifest consistency check | success | `file_count=186`, listed files `186`, missing `0` |
| local `py -3 -m py_compile ...` | success | Syntax-only check for changed backend modules |
| `docker compose -f docker-compose.yaml config --quiet` on fengxian | success | Compose rendered with `./config:/app/config:ro` |
| `docker build --target test -f frontend/Dockerfile frontend` on fengxian | success | 10 Vitest tests passed |
| backend Docker targeted pytest | success | 7 tests passed: dashboard, intake config, resources |
| `airflow dags list-import-errors` on fengxian | success | `No data found` |
| `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend` | success | Frontend production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-worker airflow-scheduler frontend` | success | Did not touch Postgres, Redis, volumes, or unpause intake |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `GET /api/health` and `/api/health/airflow` | success | Backend ok; Airflow scheduler/metadatabase healthy |
| `GET /api/dashboard/overview?pipeline=all` | success | `runs=26`, `running=0`, `failed=8`, intake `bootstrap=21` |
| `GET /api/dashboard/runs?pipeline=all&limit=10&offset=0` | success | `total=26`, `items=10`, `limit=10` |
| `GET /api/system/resources` | success | `source=host_proc`, `cores=128`, disks `/` and `/data` |
| `GET /api/intake/config` | success | `source=/app/config/intake.yaml`, pipelines `pgta`, `nipt_docker` |
| endpoint timing on fengxian | success | overview about `0.019s`; runs first page about `1.641s` |
| `airflow dags list | grep bio_intake_scan` | success | Final column `True`; DAG remains paused |

### Tests

Remote acceptance passed on `ssh fengxian`. T104 did not submit new PGT-A/NIPT
runs and did not run NIPT `full_run`.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no lint script.
- NIPT `full_run` was not run because it is a heavy workflow and still requires
  explicit approval plus `NIPT_ALLOW_HEAVY_RUN=true`.
- `bio_intake_scan` was not unpaused; T104 acceptance keeps it paused.

### Current git status

Local worktree is `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`
on `codex/dashboard/T104-dashboard-intake-config` with T104 changes ready to
commit.

### Risks

- `/api/dashboard/runs` still calls live progress for active/failed rows on the
  current page. This is intentionally limited to page size 10, but Airflow REST
  latency can still affect that endpoint.
- `GET /api/system/resources` returns `source=host_proc` on fengxian because
  Docker stats were not available from the backend container; this is an
  expected degraded mode.
- The scanner config is now repo-owned. Operators should review
  `config/intake.yaml` before unpausing `bio_intake_scan`.

### Open questions

- Whether to add a small Settings/Intake admin panel for explicit bootstrap and
  unpause guidance.
- Whether to expose per-container Docker stats by granting backend controlled
  access, or keep host-only resource telemetry.

### Next recommended task

Add an Intake settings page that shows `/api/intake/config`, last scan time,
bootstrap guidance, and an explicit operator checklist before unpausing
`bio_intake_scan`.

### Rollback notes

Revert T104 files and recreate backend/frontend. Do not delete Postgres, Docker
volumes, `shared/runs`, PGT-A rawdata, or NIPT source folders. If rollback is
needed, keep `bio_intake_scan` paused and continue using T103 submit/scan flows.

## 2026-07-08 15:27 - Codex - T103 PGT-A/NIPT batch scan and auto intake

### Goal

Replace new NIPT Docker `run1/run2` template submission with server-path scanned chip batches, add safe PGT-A/NIPT auto-intake discovery, and keep PGT-A/T102 progress behavior intact.

### Completed

- Added NIPT support to `POST /api/input/scan` plus `GET /api/input/roots`.
- Added NIPT clean FASTQ scanner for chip folders with top-level `*.clean.fastq.gz` R1/R2 pairs; nested adapter FASTQs remain out of v1.
- Changed new NIPT Docker run creation to accept `rawdata_root` and scanned `selected_samples`; `template_id` remains compatibility-only.
- Added `intake_discovery` model/migration, `/api/intake/status`, and `/api/intake/scan-and-submit`.
- Added paused-by-default `bio_intake_scan` DAG that calls backend intake endpoint.
- Updated `bio_nipt_docker` runner for scanned batches: run-local chip CSV/config/compose, read-only `/input_batch`, no large FASTQ copy.
- Updated Dashboard with read-only Intake auto scanner panel.
- Updated Submit Task to use one server-path scan UX for PGT-A/NIPT and create one NIPT run per selected chip folder.
- Updated docs/spec/runbook/state/manifest.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `backend/app/config.py`
- `backend/app/input_scanner.py`
- `backend/app/intake_service.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/run_service.py`
- `backend/alembic/versions/20260708_0002_intake_discovery.py`
- backend tests for scanner, scan API, intake, NIPT lifecycle, models
- `dags/bio_intake_scan.py`
- `dags/bio_nipt_docker.py`
- `dags/nipt_docker_runner.py`
- DAG/runner tests for intake and scanned NIPT
- frontend API, Dashboard, Submit, mocks, tests
- docs `02/04/05/06/07/09/11`, `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`, `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git diff --check` | success | Local and remote whitespace checks passed |
| manifest consistency check | success | `file_count=179`, listed files `179`, missing `0` |
| local `py -3.14 -m py_compile ...` | success | Local syntax-only check for changed backend/DAG files |
| `docker compose -f docker-compose.yaml config --quiet` on fengxian | success | Compose rendered after NIPT scan/intake env changes |
| `docker build --target test -f frontend/Dockerfile frontend` on fengxian | success | 10 Vitest tests passed |
| backend Docker targeted pytest | success | 25 tests passed |
| Airflow DAG unittest via `/usr/local/bin/python` | success | 4 tests passed for `bio_intake_scan` and `bio_nipt_docker` |
| NIPT runner/progress unittest via worker venv python | success | 12 tests passed |
| `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend` | success | Frontend build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-scheduler airflow-worker frontend` | success | Recreated services without deleting volumes |
| `docker compose -f docker-compose.yaml exec -T backend alembic upgrade head` | success | Applied `20260708_0002` intake discovery migration |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `/api/health`, `/api/health/airflow` | success | Backend ok; Airflow scheduler/metadatabase healthy |
| `airflow dags list-import-errors` | success | `No data found` |
| `GET /api/input/roots?pipeline=nipt_docker` | success | Returned `/opt/pipelines/NIPT/fastq` |
| `POST /api/input/scan` for NIPT | success | Returned clean FASTQ candidates under chip folder `FQ2025/250103_NDX550692_RUO_0044_AH3H37BGYW` |
| scanned NIPT mount smoke `NIPT_20260708_072349_4F942A` | success | Airflow/backend success, progress 100, `nipt_mount_smoke=success`, QC pass 1 |
| intake bootstrap `POST /api/intake/scan-and-submit` | success | Existing PGT-A/NIPT batches recorded as `observed/bootstrap`; no historical auto-submit |

### Tests

Remote acceptance passed on `ssh fengxian`. The important runtime proof is `NIPT_20260708_072349_4F942A`, created without `template_id` from a scanned NIPT chip folder, submitted to `manual__NIPT_20260708_072349_4F942A`, and completed `success`.

### Not run / why

- NIPT `full_run` was not run because it is a heavy 40-core batch and remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- PGT-A `baseline_qc` was not run in T103; acceptance used scanning/bootstrap and the light NIPT `mount_smoke`.
- `bio_intake_scan` was not unpaused; it is intentionally paused until operators review bootstrap rows and choose to enable automatic intake.

### Current git status

Local worktree: `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign` on `codex/intake/T103-pgta-nipt-auto-scan` with T101/T102/T103 changes pending. Remote `/home/jiucheng/project/airflow-demo` has the same overlay deployed and validated.

### Risks

- `bio_intake_scan` should not be unpaused before reviewing `/api/intake/status`; otherwise future stable changed fingerprints will auto-create/submits runs.
- Backend scans real server paths and records real file paths/metadata in biodemo; do not commit patient-identifying sample metadata beyond minimal path fixtures.
- Airflow worker still has Docker socket access for NIPT Docker; scheduler/API server do not.
- Legacy `template_id` code remains for historical compatibility and tests, but should not be presented as a current Submit entrypoint.

### Open questions

- Whether to unpause `bio_intake_scan` for continuous demo automation after operator review.
- Whether to approve any supervised NIPT `full_run`, with `NIPT_ALLOW_HEAVY_RUN=true` and a defined time/resource window.
- Whether PGT-A auto-intake should use a marker-file ready rule instead of stable two-scan fingerprint.

### Next recommended task

Add a small Settings/Intake admin action for explicit bootstrap and unpause guidance, or add marker-file/DONE-file ready rules before enabling production-like continuous auto intake.

### Rollback notes

Revert T103 files and recreate backend, airflow-scheduler, airflow-worker, and frontend. Do not delete Postgres, Docker volumes, `shared/runs`, or NIPT/PGT-A source data. If needed, keep `bio_intake_scan` paused and stop using `/api/intake/scan-and-submit`; existing `intake_discovery` rows are passive state and do not trigger work unless the endpoint/DAG is called.

## 2026-07-08 13:15 - Codex - T102 Airflow + Snakemake progress observability

### Goal

Expose real "where is the analysis now" progress for Dashboard and Run Detail by combining Airflow task instances with PGT-A/NIPT Docker runner events.

### Completed

- Added backend `GET /api/runs/{analysis_id}/progress`.
- Added `AirflowClient.list_task_instances()` for Airflow REST `/taskInstances`; no Airflow metadata DB reads.
- Added progress calculation for created/submitted/running/success/failed using PGT-A and NIPT Docker task weights.
- Added JSONL + backend POST runner event helper in `dags/common/progress_events.py`.
- Added PGT-A target-level progress events and Snakemake stdout/stderr parsing while preserving resume/preflight/no-`--forceall` behavior.
- Added NIPT Docker `nipt_mount_smoke` events and full-run stdout/stderr rule parsing path.
- Added terminal `sync-airflow` JSONL fallback import.
- Updated Dashboard and Run Detail to use `/progress`; Run Detail Workflow tab now shows `Airflow tasks` and `Pipeline steps`.
- Deployed backend, Airflow API/scheduler/worker, and frontend on `fengxian`.
- Verified light PGT-A metadata and NIPT Docker mount-smoke progress smokes.

### Changed files

- `backend/app/airflow_client.py`
- `backend/app/diagnostics_service.py`
- `backend/app/main.py`
- `backend/app/progress_service.py`
- `backend/app/rule_event_service.py`
- `backend/app/run_service.py`
- `backend/tests/test_airflow_client.py`
- `backend/tests/test_run_progress.py`
- `dags/common/progress_events.py`
- `dags/nipt_docker_runner.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_nipt_docker_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `dags/tests/test_progress_events.py`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/components/RunTracker.tsx`
- `frontend/src/lib/runProgress.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/styles.css`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/09_NIPT_DOCKER_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/progress/T102-airflow-snakemake-progress` | success | Created local T102 branch in `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign` |
| `git diff --check` | success | Local and remote checks passed |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose rendered cleanly |
| `docker build -t airflow-demo/backend:t102-test -f backend/Dockerfile backend && docker run --rm airflow-demo/backend:t102-test pytest -q tests/test_airflow_client.py tests/test_run_progress.py tests/test_snakemake_events_api.py tests/test_nipt_docker_lifecycle.py tests/test_run_diagnostics.py` | success | 29 backend tests passed |
| `docker compose -f docker-compose.yaml build airflow-worker` plus Airflow unittest container | success | 35 DAG/runner tests OK |
| `docker build --target test -f frontend/Dockerfile frontend` | success | 10 Vitest tests passed |
| `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend` | success | Frontend production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-api-server airflow-scheduler airflow-worker frontend` | success | Did not touch Postgres/Redis/volumes |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `curl -fsS http://127.0.0.1:8000/api/health` and `/api/health/airflow` | success | Backend ok; Airflow scheduler/metadatabase healthy |
| `airflow dags list-import-errors` | success | `No data found` |
| `GET /api/runs/PGTA_20260706_162150_00C4FD/progress` | success | Historical PGT-A returned Airflow task timeline, `percent=100`, empty historical rule events |
| `GET /api/runs/NIPT_20260708_033450_8362A0/progress` | success | Historical NIPT returned Airflow task timeline, `percent=100`, empty historical rule events |
| PGT-A metadata smoke `PGTA_20260708_050811_A24E36` | success | `/progress` showed Airflow tasks plus `metadata=success` pipeline event |
| NIPT Docker mount smoke `NIPT_20260708_050843_B3B05E` | success | `/progress` showed Airflow tasks plus `nipt_mount_smoke=success` pipeline event |

### Tests

- Backend targeted tests: 29 passed.
- Airflow DAG/runner tests: 35 passed.
- Frontend Docker test target: 10 tests passed.
- Production build/deploy and runtime health checks passed on `fengxian`.
- Light PGT-A metadata and NIPT Docker mount-smoke progress smokes passed.

### Not run / why

- NIPT `full_run` was not run because it is a heavy batch and remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- PGT-A `baseline_qc` was not run because the T102 acceptance only needed a light metadata progress smoke.
- `npm run lint` was not run because `frontend/package.json` has no lint script.
- Local Node/npm/Docker/Python runtime checks were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`; local Windows lacks Node/npm and uses the Windows Store Python placeholder.

### Current git status

Local worktree has T101/T102 changes pending on `codex/progress/T102-airflow-snakemake-progress`. Remote `/home/jiucheng/project/airflow-demo` has the same source overlay deployed for runtime validation.

### Risks

- Historical runs before T102 cannot reconstruct missing Snakemake/runner events; they still show Airflow task-instance progress.
- Airflow worker retains Docker socket access for NIPT Docker from T101.
- NIPT `full_run` has code-level parsing support but no heavy runtime acceptance in T102.

### Open questions

- Whether to approve and schedule a supervised NIPT Docker `full_run`.
- Whether to add a future Airflow task log endpoint for per-task stdout/stderr inside the same progress panel.

### Next recommended task

Add a small UI affordance on Dashboard/Run Detail to distinguish Airflow task progress from pipeline rule progress, then consider a supervised NIPT `full_run` only if demo needs it.

### Rollback notes

Revert T102 files and recreate backend, Airflow API/scheduler/worker, and frontend. Do not delete `shared/runs`, Postgres volumes, or Docker volumes. Existing T102 smoke runs can remain in history as small metadata/mount-smoke runs.

## 2026-07-08 11:35 - Codex - T101 NIPT Docker template-run deployment

### Goal

Deploy the Dockerized NIPT workflow as the second runnable demo pipeline beside PGT-A, while keeping WES qsub, NIPT qsub, WGS, and mail notification out of the current frontend surface.

### Completed

- Added backend `pipeline=nipt_docker` create support with `template_id=run1|run2`, `run_mode=mount_smoke|full_run`, `cores`, `project_name`, and `note`.
- Added submit support for `nipt_docker` to trigger Airflow DAG `bio_nipt_docker`.
- Added `bio_nipt_docker` DAG and repo-owned `nipt_docker_runner.py`.
- Runner validates request, writes run-local config/compose/request artifacts, executes host Docker with a unique container name, writes stdout/stderr/command logs, and writes NIPT QC summary.
- Kept `full_run` guarded by `NIPT_ALLOW_HEAVY_RUN=false`; acceptance used `mount_smoke`.
- Added NIPT QC parser/import and pipeline-filtered artifacts.
- Added Airflow worker NIPT bundle mount, Docker socket mount, and `group_add=${DOCKER_SOCKET_GID:-114}` for socket access on `fengxian`.
- Updated frontend Dashboard/Submit/Runs/Samples/Workflows/Failures to expose PGT-A and NIPT Docker only.
- Deployed backend, Airflow API/scheduler/worker, and frontend on `fengxian`.
- Verified final smoke `NIPT_20260708_033450_8362A0` reached Airflow/backend success.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/app/qc_service.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_nipt_docker_lifecycle.py`
- `dags/bio_nipt_docker.py`
- `dags/nipt_docker_runner.py`
- `dags/tests/test_bio_nipt_docker_dag.py`
- `dags/tests/test_nipt_docker_runner.py`
- `frontend/src/api.ts`
- `frontend/src/App.test.tsx`
- `frontend/src/layout/AppShell.tsx`
- `frontend/src/mocks/platform.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/SubmitPage.tsx`
- `frontend/src/pages/RunsPage.tsx`
- `frontend/src/pages/SamplesPage.tsx`
- `frontend/src/pages/FailuresPage.tsx`
- `frontend/src/pages/WorkflowsPage.tsx`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/09_NIPT_DOCKER_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/nipt/T101-nipt-docker-demo` | success | Created local T101 branch in `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Re-run after NIPT env/socket changes |
| `git diff --check` local and remote | success | No whitespace errors |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 9 Vitest tests passed |
| `docker build -t airflow-demo/backend:t101-test -f backend/Dockerfile backend && docker run --rm airflow-demo/backend:t101-test pytest -q tests/test_nipt_docker_lifecycle.py tests/test_run_creation.py tests/test_run_submit.py tests/test_run_diagnostics.py` | success | 31 backend tests passed |
| `docker run --rm --entrypoint /usr/local/bin/python -v /home/jiucheng/project/airflow-demo/dags:/opt/airflow/dags:ro -w /opt/airflow airflow-demo/airflow:t101-test -m unittest /opt/airflow/dags/tests/test_bio_nipt_docker_dag.py /opt/airflow/dags/tests/test_nipt_docker_runner.py -v` | success | 9 NIPT DAG/runner tests passed |
| `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend` | success | Frontend production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-api-server airflow-scheduler airflow-worker frontend` | success | Did not touch Postgres/Redis/volumes |
| `curl -fsSI http://127.0.0.1:12959/` | success | HTTP 200 |
| `curl -fsS http://127.0.0.1:8000/api/health` and `/api/health/airflow` | success | Backend ok; Airflow scheduler/metadatabase healthy after API readiness |
| `airflow dags list-import-errors` | success | `No data found` |
| `airflow dags list | grep bio_nipt_docker` | success | DAG visible |
| First NIPT smoke `NIPT_20260708_032949_C7F56B` | failed as expected after diagnosis | Docker socket permission denied before worker `group_add` fix |
| `stat -c '%a %u %g %U %G %n' /var/run/docker.sock` | success | Host socket group id is `114` |
| `docker compose up -d --no-deps --force-recreate airflow-worker` after `group_add` | success | Worker `id` shows groups `0(root),114` |
| Final NIPT smoke `NIPT_20260708_033450_8362A0` | success | Airflow/backend success, QC pass 96, artifacts correct |

### Tests

- Frontend Docker test target: 9 tests passed.
- Backend targeted tests: 31 passed; after artifact/QC refinement, 17 targeted tests passed.
- NIPT DAG/runner tests: 9 passed.
- Compose config and production builds passed.
- Runtime smoke passed on `fengxian` with `NIPT_20260708_033450_8362A0`.

### Not run / why

- NIPT `full_run` was not run because it is a heavy 40-core batch and remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- `npm run lint` was not run because `frontend/package.json` has no lint script.
- Local Node/npm/Docker/Python runtime checks were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`.
- Mail notification, WES qsub frontend restore, NIPT qsub, and WGS were not in scope.

### Current git status

Local worktree has T101 changes pending on `codex/nipt/T101-nipt-docker-demo`. Remote `/home/jiucheng/project/airflow-demo` has the same file overlay deployed for runtime validation, but remains on its existing branch name.

### Risks

- Airflow worker now has Docker socket access for NIPT Docker; this is limited to worker only, but it is still privileged host Docker access.
- The failed permission smoke `NIPT_20260708_032949_C7F56B` remains visible in history.
- `full_run` path is code-level integrated but not runtime-accepted in this task.
- Frontend progress remains an estimate, not authoritative Airflow task-instance progress.

### Open questions

- Whether to run a supervised `full_run` with `NIPT_ALLOW_HEAVY_RUN=true` and what resource/time window to reserve.

### Next recommended task

Add a backend Airflow task-instance/progress endpoint for Dashboard/Run Detail, then optionally schedule a separately approved NIPT Docker full-run acceptance.

### Rollback notes

To rollback the NIPT deployment surface, revert T101 files and recreate backend/airflow-worker/airflow-scheduler/airflow-api-server/frontend. Do not delete `shared/runs/NIPT_*`, Postgres volumes, or Docker volumes. Remove the worker Docker socket mount/group only by reverting `docker-compose.yaml` and recreating `airflow-worker`.

## 2026-07-08 09:38 - Codex - T100 PGT-A submit/Airflow status auto-sync

### Goal

Fix the user-reported PGT-A behavior where a project was created and submitted, but the frontend/backend stayed at `submitted`, making it look like Airflow had not entered the workflow.

### Completed

- Investigated the latest stuck run `PGTA_20260708_012630_352915`.
- Confirmed the run had a backend `dag_run_id=manual__PGTA_20260708_012630_352915` and backend `status=submitted`.
- Confirmed Airflow had actually completed that DAG run with `state=success`; the problem was missing frontend/backend reconciliation, not a missing Airflow handoff.
- Safely reconciled the stuck run by calling backend `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow`; no workflow rerun was submitted.
- Updated Dashboard so active/submitted PGT-A tracker rows call `sync-airflow` immediately and every 15 seconds, then reload tracker data.
- Updated Submit Task so primary `Create and submit to Airflow` calls `sync-airflow` after a successful submit handoff with `dag_run_id`, retrying briefly so fast runs can surface terminal backend status in the handoff summary.
- Added/updated frontend tests for Dashboard active auto-sync and Submit create+submit+sync handoff.
- Rebuilt and redeployed only the frontend container on `fengxian`.
- Updated frontend spec, task state, current state, handoff, and manifest timestamp.

### Changed files

- `frontend/src/App.test.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/SubmitPage.tsx`
- `docs/06_FRONTEND_SPEC.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `GET /api/runs?pipeline=pgta&status=submitted&limit=20&offset=0` on `fengxian` | success | Found user-visible stuck run `PGTA_20260708_012630_352915` before manual sync |
| `GET /api/runs/PGTA_20260708_012630_352915` on `fengxian` | success | Backend showed `status=submitted`, non-null `dag_run_id`, null start/end |
| Airflow CLI DAG-run query on `fengxian` | success | Same DAG run was `success`, with start and end timestamps |
| `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow` on `fengxian` | success | Reconciled backend status to `success`; no new run created |
| remote red frontend test target before implementation | failed as expected | Dashboard and Submit did not call `sync-airflow` |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 7 Vitest tests passed after implementation |
| `docker run --rm <frontend-test-image> npm test -- --run` on `fengxian` | success | Fresh verification after state-doc update: `1 test file`, `7 tests passed` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose rendered cleanly |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | Production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` on `fengxian` | success | Recreated only the frontend container |
| `curl -fsSI http://127.0.0.1:12959/` on `fengxian` | success | HTTP 200 from nginx |
| `GET /api/health` and `GET /api/health/airflow` on `fengxian` | success | Backend ok; Airflow metadatabase and scheduler healthy |
| `GET /api/runs/PGTA_20260708_012630_352915` after sync | success | Returned `status=success`, `dag_run_id`, and Airflow start/end timestamps |
| `GET /api/runs?pipeline=pgta&status=submitted&limit=20&offset=0` after sync | success | Returned no stuck submitted PGT-A runs |

### Tests

- Remote frontend Docker test target passed: `1 test file`, `7 tests`.
- Frontend production build passed through Compose: `tsc -b && vite build`.
- Runtime spot checks passed for frontend HTTP, backend health, Airflow health, reconciled PGT-A detail, and empty submitted PGT-A list.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no `lint` script.
- Local `npm`, `node`, and `docker` were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`.
- No new heavy `baseline_qc` workflow was submitted; the stuck run was reconciled by `sync-airflow` only.
- Backend, DAG, Snakemake, WES qsub, NIPT/WGS, and mail notification code were not changed.

### Current git status

Local worktree has T099/T100 changes pending commit on `codex/frontend/T099-pgta-run-tracker`. The remote service has been updated by syncing frontend source files to `/home/jiucheng/project/airflow-demo` and rebuilding/recreating the frontend container.

### Risks

- Dashboard progress remains an estimate from run status and rule events; authoritative task-level progress still needs a backend Airflow task-instance endpoint.
- Submit's post-handoff sync has a short retry window. Long-running baseline runs will still show active status until Dashboard polling observes terminal state.
- The frontend now masks this specific stale-submitted symptom, but the backend could still benefit from server-side reconciliation after `/actions/submit`.

### Open questions

- Whether to add backend-side sync immediately after submit as a stronger guarantee, or keep this frontend-only reconciliation for the current demo.

### Next recommended task

Add Airflow task-attempt history and authoritative task progress to Run Detail/Dashboard, or implement backend-side post-submit reconciliation. Keep mail notification paused unless the user reopens T034/T063.

### Rollback notes

Revert the T100 frontend changes and redeploy the previous T099 frontend image. No backend migration, Airflow DAG change, shared run directory change, or Docker volume rollback is required.

## 2026-07-08 07:46 - Codex - T099 PGT-A Dashboard run tracker and submit handoff

### Goal

Make the PGT-A-only Dashboard understandable as a project/run tracker and make Submit Task expose whether a run was only created in biodemo or actually handed off to Airflow.

### Completed

- Replaced the Dashboard split `Recent failed runs` / `Recent completed runs` layout with one large `PGT-A Run Tracker`.
- Added tracker ordering for active, failed/QC failed, created-only, and recent success PGT-A runs.
- Added tracker filters: All, Running, Submitted / queued, Created only, Failed, QC failed, Success.
- Added row-level progress estimate, progress bar, current step, project-name display, and View/Submit/Sync actions.
- Moved Service health, PGT-A resource overview, and PGT-A workflow into three equal bottom panels.
- Changed Submit Task primary action to `Create and submit to Airflow`; it now creates the backend run, submits to Airflow, fetches detail, and displays `dag_run_id`.
- Kept `Create only` as a secondary action and made the "not visible in Airflow until submitted" state explicit.
- Reworked scan results into a folder-first view with expandable FASTQ file names and hidden absolute paths.
- Updated frontend spec, task state, current state, handoff, and manifest.

### Changed files

- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/lib/runProgress.ts`
- `frontend/src/components/RunProgressBar.tsx`
- `frontend/src/components/RunTracker.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/SubmitPage.tsx`
- `frontend/src/styles.css`
- `docs/06_FRONTEND_SPEC.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git rev-parse --git-dir`, `git rev-parse --git-common-dir`, `git branch --show-current` | success | Confirmed worktree branch `codex/frontend/T099-pgta-run-tracker` under `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign` |
| remote red frontend test target before implementation | failed as expected | Existing UI lacked `PGT-A Run Tracker`, folder scan, and create+submit handoff behavior |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 7 Vitest tests passed after implementation |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose rendered cleanly |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | Production build ran `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` on `fengxian` | success | Recreated only the frontend container |
| `curl -fsSI http://127.0.0.1:12959/` on `fengxian` | success | HTTP 200 from nginx |
| `GET /api/health` and `GET /api/health/airflow` on `fengxian` | success | Backend ok; Airflow metadatabase and scheduler healthy |
| `GET /api/runs?pipeline=pgta&limit=20&offset=0` on `fengxian` | success | Returned 19 total PGT-A runs and included the two July 7 submitted runs |
| `GET /api/runs/PGTA_20260707_182024_8CA2A0` and `GET /api/runs/PGTA_20260707_182056_39A374` | success | Both returned non-null `dag_run_id` and `status=success` |
| deployed bundle grep for `PGT-A Run Tracker` | success | Confirms deployed frontend contains the new Dashboard tracker UI |

### Tests

- Remote frontend Docker test target passed: `1 test file`, `7 tests`.
- Frontend production build passed through Compose: `tsc -b && vite build`.
- Runtime spot checks passed for frontend HTTP, backend health, Airflow health, PGT-A run list, PGT-A detail handoff, and existing baseline QC evidence.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` has no `lint` script.
- Local `npm`, `node`, and `docker` were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`.
- No new PGT-A workflow was submitted during acceptance; this task used existing runs and UI tests to avoid a heavy `baseline_qc` run.
- Backend, DAG, Snakemake, WES qsub, NIPT/WGS, and mail notification code were not changed.

### Current git status

Local worktree has T099 changes pending commit on `codex/frontend/T099-pgta-run-tracker`. The remote service has been updated by syncing frontend source files to `/home/jiucheng/project/airflow-demo` and rebuilding/recreating the frontend container.

### Risks

- Dashboard progress is an estimate from run status and rule events; true Airflow task progress still needs a backend task-instance endpoint.
- `/api/runs` is analysis-run centric, not raw Airflow DAG-run centric. Resume history still appears as one analysis with the latest `dag_run_id`.
- The two July 7 PGT-A metadata runs are `success` with `qc_status=unknown`; they prove handoff/status flow, not baseline QC.

### Open questions

- Whether to add a backend endpoint for Airflow task instances so Dashboard progress can become authoritative rather than estimated.

### Next recommended task

Add Airflow task-attempt history and real task progress to Run Detail/Dashboard, or continue with T082 rollback/cleanup runbook. Keep mail notification paused unless the user reopens T034/T063.

### Rollback notes

Revert the T099 frontend files and redeploy the previous frontend image. No backend migration, Airflow DAG change, shared run directory change, or Docker volume rollback is required.

## 2026-07-08 02:18 - Codex - T098 PGT-A frontend/Airflow data reconciliation

### Goal

Resolve the apparent frontend/Airflow data mismatch in the PGT-A-only demo without exposing WES/NIPT/WGS or adding mail notification work.

### Completed

- Confirmed the frontend data path is `React -> FastAPI -> Airflow REST API + biodemo DB`; the frontend does not connect directly to Airflow metadata DB.
- Found one real mismatch: `/api/runs` hard-coded `qc_status=unknown`, while `PGTA_20260706_162150_00C4FD/qc` already reported 14 failed PGT-A baseline QC metrics.
- Fixed `/api/runs` to aggregate run-level QC from sample `qc_status` with priority `fail > warn > unknown > pass`.
- Restored active PGT-A Run Detail auto-sync: if the selected PGT-A run has a `dag_run_id` and active status, the page calls backend `sync-airflow` immediately and every 15 seconds until terminal state.
- Rebuilt and redeployed only backend/frontend on `fengxian`.
- Verified `PGTA_20260706_162150_00C4FD` is reconciled: frontend/backend list and detail show workflow `success`, run/sample QC `fail`; latest matching Airflow DAG run is `success`.

### Changed files

- `backend/app/run_service.py`
- `backend/tests/test_run_creation.py`
- `frontend/src/App.test.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| red backend targeted test in temporary clone | failed as expected | `qc_status` was `unknown` instead of expected `fail` |
| red frontend Docker test target in temporary clone | failed as expected | active PGT-A detail did not call `/actions/sync-airflow` |
| green targeted backend test in temporary clone | success | new QC aggregation test passed |
| green frontend Docker test target in temporary clone | success | 6 Vitest tests passed |
| temporary-clone full backend pytest | success | 53 passed |
| temporary-clone frontend production build | success | `tsc -b && vite build` passed |
| `git push -u origin codex/frontend/T098-airflow-data-reconcile` | success | pushed commit `f64e0d2` |
| remote mirror checkout/pull | success | `/home/jiucheng/project/airflow-demo` at `f64e0d2` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | compose config valid |
| `docker run --rm airflow-demo/backend:t098-test pytest -q` on `fengxian` | success | 53 passed |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | cache-hit test target for 6 Vitest tests |
| `docker compose -f docker-compose.yaml build backend frontend` on `fengxian` | success | backend built; frontend build passed `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend` on `fengxian` | success | recreated only backend/frontend; no volumes deleted |
| HTTP/API/Airflow spot check on `fengxian` | success | frontend HTTP 200; backend health ok; Airflow healthy; target PGT-A list/detail/QC/Airflow state reconciled |

### Tests

- Backend full pytest passed remotely: 53 tests.
- Frontend Docker test target passed remotely: 6 Vitest tests.
- Frontend production build passed remotely through Compose.
- Runtime spot check passed: `/api/runs?pipeline=pgta&limit=50&offset=0` returned 17 PGT-A analysis runs, and `PGTA_20260706_162150_00C4FD` now has `qc_status=fail`; Airflow `bio_pgta` has 20 DAG runs total and 5 matching that analysis because of resume history, latest matching run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` is `success`.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` still has no `lint` script.
- No new PGT-A analysis was submitted; this task only reconciled and displayed existing state.
- MailHog/SMTP notification remains out of scope by user request.
- WES qsub UI remains hidden; historical backend/DAG/Snakemake code was not deleted.

### Current git status

At handoff time, code commit `f64e0d2` is pushed and deployed. State-doc updates are pending local commit/push on the same branch.

### Risks

- Frontend analysis-run counts will still differ from raw Airflow DAG-run counts after resumes; this is expected and should be narrated clearly in demos.
- PGT-A `PGTA_20260706_162150_00C4FD` remains workflow success with QC fail, not a QC-pass biological sample.

### Open questions

- Whether the next frontend iteration should show a small "Airflow attempts/resume history" panel for PGT-A run detail to make the 1 analysis / many DAG runs relationship explicit.

### Next recommended task

Add an Airflow attempt history panel in Run Detail, or continue with `T082` rollback/cleanup runbook. Keep mail notifications paused unless the user reopens `T034/T063`.

### Rollback notes

Revert T098 commits and redeploy backend/frontend. No Airflow DAG code, database migration, shared run directory, or Docker volume rollback is required.

## 2026-07-08 01:54 - Codex - T097 PGT-A-only frontend deployment scope

### Goal

Converge the redesigned T096 frontend into a PGT-A-only deployable demo, hide WES/NIPT/WGS frontend entry points, leave historical backend/DAG/Snakemake code untouched, and verify the updated frontend service on port `12959`.

### Completed

- Sidebar now shows Dashboard, Submit Task, Runs, Samples, Failures, and Settings; Workflows is hidden from the main navigation.
- Dashboard, Runs, Samples, and Failures now display PGT-A data only.
- Submit Task now exposes only the PGT-A server-path scan/create/submit flow.
- Run Detail keeps PGT-A Overview/Samples/Workflow/QC/Logs/Files/Config tabs, sync, and baseline_qc `Resume with 64 cores`.
- Direct `/workflows` remains development-accessible but displays only the PGT-A workflow template.
- WES qsub, NIPT qsub, NIPT docker, and WGS are hidden from the current frontend demo. Existing backend/DAG/Snakemake code was not removed.
- Mail notification work was not started; `T034` and `T063` remain todo.
- Frontend container was rebuilt and recreated on `fengxian`; `http://127.0.0.1:12959/` returns HTTP 200.

### Changed files

- `docs/06_FRONTEND_SPEC.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`
- `frontend/src/App.test.tsx`
- `frontend/src/layout/AppShell.tsx`
- `frontend/src/mocks/platform.ts`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/FailuresPage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/RunsPage.tsx`
- `frontend/src/pages/SamplesPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/SubmitPage.tsx`
- `frontend/src/pages/WorkflowsPage.tsx`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git checkout -b codex/frontend/T097-pgta-only` | success | T097 branch created from T096 worktree |
| temporary-clone `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | red/green fix validation; 5 Vitest tests passed |
| temporary-clone `docker build -f frontend/Dockerfile frontend` on `fengxian` | success | production build passed `tsc -b && vite build` |
| `git push -u origin codex/frontend/T097-pgta-only` | success | branch pushed |
| remote mirror `git checkout -b codex/frontend/T097-pgta-only --track origin/codex/frontend/T097-pgta-only` | success | remote mirror at frontend code commit `3119be5` |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | cache-hit preflight before rebuild |
| `docker build --no-cache --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 1 test file, 5 tests passed |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | compose config valid |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | production build passed `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` on `fengxian` | success | recreated only frontend |
| `curl -fsSI http://127.0.0.1:12959/` on `fengxian` | success | HTTP 200 from nginx |
| PGT-A API spot checks on backend port `8000` | success | `/api/health`, `/api/health/airflow`, run detail, QC, and stderr log tail returned data |
| `git diff --check` | success | local non-runtime whitespace check passed before first commit |

### Tests

- Remote frontend Docker test target passed with `--no-cache`: `1 test file`, `5 tests`.
- Remote frontend production build passed through Compose: `tsc -b && vite build`.
- Remote frontend HTTP smoke passed on port `12959`.
- PGT-A backend/API compatibility spot checks passed for `PGTA_20260706_162150_00C4FD`, including detail, QC summary `pass=0,warn=0,fail=14,unknown=0`, and stderr log tail.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` does not define a `lint` script.
- Local `npm`, `node`, and `docker` were not used as acceptance evidence because AGENTS.md requires runtime validation on `ssh fengxian`.
- No new PGT-A run was submitted; spot checks used the existing successful workflow/QC-fail demo run.
- MailHog/SMTP notification was not implemented or tested by user request.

### Current git status

Frontend code commit `3119be5` is pushed to `origin/codex/frontend/T097-pgta-only` and deployed on `fengxian`. This handoff/state/manifest sync is expected to be committed and pushed as a follow-up docs-state commit on the same branch.

### Risks

- PGT-A demo remains workflow success with QC fail for G10/G11; the UI should narrate this as workflow observability plus QC failure diagnosis, not as a QC-pass sample.
- WES qsub code remains in the repository and backend storage may still contain WES historical runs, but current frontend demo intentionally hides those surfaces.
- Direct `/workflows` still resolves for development, but only PGT-A is shown.

### Open questions

- Whether to remove or guard the direct `/workflows` route later, or keep it as a development-only page.

### Next recommended task

Keep the current demo focused on PGT-A. If future scope expands, add one deployable pipeline at a time, starting with a real acceptance plan rather than re-exposing old mock surfaces. Mail notifications remain `T034/T063`.

### Rollback notes

Revert the T097 frontend commit and redeploy the previous T096 frontend image. No backend, DAG, database, shared run directory, or Docker volume rollback is required.

## 2026-07-08 01:30 - Codex - T096 frontend platform UI redesign

### Goal

Redesign the demo frontend into a credible bioinformatics task platform prototype while preserving existing PGT-A and WES API behavior.

### Completed

- Added design/audit/spec documentation before implementation: `DESIGN.md`, `docs/frontend-design-review.md`, and `docs/frontend-spec.md`.
- Replaced the single-page workspace with `react-router-dom` routes and a persistent sidebar/topbar shell.
- Added Dashboard, Submit Task, Runs, Run Detail, Samples, Workflows, Failures, and Settings pages.
- Kept real PGT-A server-path scan/create/submit behavior and real WES mock create/submit/reanalysis behavior.
- Added clearly labeled mock/demo surfaces for NIPT qsub, NIPT docker, WGS, workflow templates, and resource usage.
- Added shared frontend components for status badges, metrics, pipeline cards, run tables, workflow timeline, log viewer, sample sheet validation, pipeline selection, error diagnosis, and QC metric display.
- Centralized status semantics in `frontend/src/lib/status.ts`, formatting helpers in `frontend/src/lib/format.ts`, and demo fixtures in `frontend/src/mocks/platform.ts`.
- Updated `docs/06_FRONTEND_SPEC.md`, `TASKS.md`, `CURRENT_STATE.md`, and `MANIFEST.json`.

### Changed files

- `DESIGN.md`
- `docs/frontend-design-review.md`
- `docs/frontend-spec.md`
- `docs/06_FRONTEND_SPEC.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/styles.css`
- `frontend/src/components/*`
- `frontend/src/layout/AppShell.tsx`
- `frontend/src/lib/*`
- `frontend/src/mocks/platform.ts`
- `frontend/src/pages/*`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git worktree add -b codex/frontend/T096-platform-ui-redesign ../airflow-demo-worktrees/T096-platform-ui-redesign` | success | isolated from dirty root worktree |
| `git status --short --branch` | success | checked local and remote mirror state |
| `ssh fengxian 'cd /home/jiucheng/project/airflow-demo && git pull --ff-only origin codex/frontend/T096-platform-ui-redesign'` | success | remote mirror fast-forwarded to frontend branch |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 7 Vitest tests passed |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | no rendered compose errors |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | ran `npm run build`, including `tsc -b && vite build` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` on `fengxian` | success | recreated only frontend |
| `curl -fsSI http://127.0.0.1:12959/` on `fengxian` | success | first immediate probe reset during nginx readiness; retry returned HTTP 200 |
| backend API spot checks on `http://127.0.0.1:8000/api` | success | health/db/airflow ok; PGT-A detail/samples/stderr and WES detail/rules/QC returned data |

### Tests

- Remote frontend Docker test target passed: `1 test file`, `7 tests`.
- Remote production frontend image build passed: `tsc -b && vite build`.
- Remote frontend HTTP smoke passed on port `12959`.
- Remote PGT-A/WES API compatibility spot checks passed against backend port `8000`.

### Not run / why

- `npm run lint` was not run because `frontend/package.json` does not define a `lint` script.
- Local `npm`, `node`, and `docker` checks were not run because the Windows edit environment does not provide those binaries; runtime acceptance was performed on `ssh fengxian` per AGENTS.md.
- No new PGT-A or WES analysis run was submitted during final acceptance; existing API data was read for compatibility spot checks.

### Current git status

T096 code commits were pushed to `origin/codex/frontend/T096-platform-ui-redesign`; docs/state/manifest updates are pending final commit at this checkpoint.

### Risks

- NIPT/WGS pages are UI/mock surfaces only until backend/DAG tasks exist.
- The frontend nginx still serves only static assets; browser API calls intentionally target backend port `8000` by the existing API base logic.
- Current PGT-A demo evidence remains workflow success with QC fail for G10/G11; UI separates workflow status from QC decision.

### Open questions

- Whether to add a real reverse proxy for `/api` through frontend nginx, or keep the current explicit backend port model.
- Whether NIPT qsub/docker and WGS should be promoted from mock UI fixtures into backend/DAG tasks next.

### Next recommended task

Wire real Airflow/backend contracts for NIPT qsub, NIPT docker, and WGS, or add MailHog success/failure notification links into the redesigned Run Detail.

### Rollback notes

- Revert the T096 frontend branch commits and redeploy the previous frontend image. No database, shared run directory, or Docker volume changes are required.

## 2026-07-07 23:29 - Codex - T080/T081 demo smoke report and script

### Goal

Turn the already verified PGT-A/WES capabilities into a reproducible 10-15 minute demo script and smoke report without submitting new heavy PGT-A work.

### Completed

- Rechecked `fengxian` with read-only commands: frontend HTTP 200, backend `/api/health` ok, Airflow metadatabase and scheduler healthy.
- Verified PGT-A `PGTA_20260706_162150_00C4FD` remains workflow `success`, with G10/G11 sample workflow `success` and QC status `fail`.
- Verified PGT-A `/qc` summary is `pass=0,warn=0,fail=14,unknown=0`, and artifacts include `pgta_python_preflight`, `pgta_baseline_qc_summary`, `pgta_baseline_qc_pass_samples`, `pgta_baseline_qc_report`, and `snakemake_command`.
- Verified WES mock QC run `WES_20260705_164813_C5561C` is `success` with `/qc` summary `pass=6,warn=0,fail=0,unknown=0`.
- Verified WES rerun_rule run `WES_20260705_162041_2507AF` is `success`, has 7 rule rows, and command log contains `--forcerun fastp` without `--forceall`.
- Rewrote `docs/17_DEMO_SCRIPT.md` around the current demo truth and added `docs/21_DEMO_SMOKE_REPORT.md`.
- Updated `TASKS.md`, `CURRENT_STATE.md`, and `MANIFEST.json`.

### Changed files

- `docs/17_DEMO_SCRIPT.md`
- `docs/21_DEMO_SMOKE_REPORT.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | success | local branch clean before edits |
| read-only `fengxian` smoke script | success | no new run submitted; frontend/backend/Airflow and PGT-A/WES evidence checked |
| `curl http://127.0.0.1:12959/` on `fengxian` | HTTP 200 | frontend reachable |
| `GET /api/health` | success | backend returned `{"status":"ok"}` |
| `GET /health` on Airflow | success | metadatabase `healthy`, scheduler `healthy` |
| `GET /api/runs/PGTA_20260706_162150_00C4FD/qc` | success | `pass=0,warn=0,fail=14,unknown=0` |
| `GET /api/runs/WES_20260705_164813_C5561C/qc` | success | `pass=6,warn=0,fail=0,unknown=0` |
| command log grep for `WES_20260705_162041_2507AF` | success | contains `--forcerun fastp`; no `--forceall` |

### Tests

- Runtime validation was read-only and performed on `ssh fengxian`.
- Local static checks passed before commit: `git diff --check` had no whitespace errors, `rg` found the acceptance keywords, and `MANIFEST.json` reports `file_count=135`, `listed=135`, `missing=0`.

### Not run / why

- No backend/frontend/DAG unit tests were run because this is a docs/QA report-only update.
- No new PGT-A baseline_qc run was submitted; current evidence is from the existing successful workflow run.
- MailHog notification was not demonstrated because `T034/T063` is still todo.

### Current git status

Docs/state changes are pending commit at this checkpoint.

### Risks

- PGT-A demo should be narrated as workflow success with QC fail, not as a QC-pass biological sample.
- If a QC-pass PGT-A demo is required, do a read-only candidate data/threshold audit before another heavy baseline_qc run.

### Open questions

- None for T080/T081; QC-pass sample selection remains a future product/demo decision.

### Next recommended task

T082 rollback/cleanup runbook, or T034/T063 MailHog success/failure notification.

### Rollback notes

- Revert the docs-only T080/T081 commit to remove the new smoke report and restore the old demo script. No runtime service rollback is needed.

## 2026-07-07 23:05 - Codex - T095 PGT-A baseline QC preflight final resume

### Goal

Finish T095 by fixing the PGT-A baseline QC Python dynamic-library failure and resuming `PGTA_20260706_162150_00C4FD` in the same workdir without deleting BAM/QC/config data.

### Completed

- Confirmed the previous resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` had reached baseline QC and failed on `matplotlib` import due the system `libstdc++.so.6` lacking `CXXABI_1.3.15`.
- Added PGT-A subprocess env isolation: run-local `XDG_CACHE_HOME`, run-local `MPLCONFIGDIR`, `LD_LIBRARY_PATH=PGTA_CONDA_LIB`, and `LD_PRELOAD=PGTA_LIBSTDCXX`.
- Added `PGTA_LIBSTDCXX` to `.env.example` and Compose Airflow env.
- Added a preflight log header showing command, `LD_LIBRARY_PATH`, `LD_PRELOAD`, `MPLCONFIGDIR`, and `XDG_CACHE_HOME`.
- Deployed commit `3bd1270` to `fengxian` via `git pull --ff-only` and recreated only `airflow-scheduler` / `airflow-worker`.
- Final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` ended Airflow/backend `success`.
- Verified artifacts: `baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, `baseline_qc_report.md`, and `pgta.python_preflight.log`.
- Verified `/api/runs/PGTA_20260706_162150_00C4FD/qc`: 14 metrics imported, all `fail`; samples G10/G11 are workflow `success` with `qc_status=fail`.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | no rendered compose errors |
| `docker compose -f docker-compose.yaml exec -T airflow-worker bash -lc 'python -m unittest discover -s dags/tests -v'` | success | 47 tests OK, 5 expected logger-interface skips |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| direct worker `_run_pgta_python_preflight` in temp workdir | success | logged `matplotlib 3.10.8`, `numpy 1.26.4`, `pandas 2.2.1`, `pysam 0.23.3`, `scipy 1.16.0` |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/reanalyze` | success | created `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/sync-airflow` | success | backend status `success` |
| `GET /api/runs/PGTA_20260706_162150_00C4FD/qc` | success | `pass=0,warn=0,fail=14,unknown=0` |
| `git diff --check` | success | local non-runtime check |

### Tests

- Remote Airflow/DAG tests passed after the `LD_PRELOAD` fix.
- Runtime baseline QC final resume passed and generated terminal baseline QC artifacts.

### Not run / why

- Frontend browser click-through was not repeated; backend APIs and generated artifacts were verified, and frontend consumes the same `/qc`/artifacts endpoints.
- Backend full pytest was not rerun after the second `LD_PRELOAD` commit because no backend code changed after `966e0d8`; previous T095 backend pytest passed 52 tests.

### Current git status

Local branch `codex/airflow/T088-pgta-snakemake-cache` has state-doc updates pending after runtime success evidence.

### Risks

- Workflow success does not mean QC pass: G10/G11 baseline QC decision is `FAIL` (`median_abs_z>1.5;outlier_frac_abs_z_gt_3>0.3`).
- Do not rerun baseline_qc blindly to chase a QC pass; first audit data suitability or thresholds.

### Open questions

- Whether demo narrative should present this as "workflow success with QC fail" or whether another PGT-A input set should be selected for a QC-pass demonstration.

### Next recommended task

T080/T081: build the end-to-end smoke/demo report, explicitly separating workflow status from QC decision. If a QC-pass PGT-A demo is required, do a read-only candidate data/threshold audit first.

### Rollback notes

- To roll back T095 runtime behavior, revert commits `966e0d8`, `fd1f3cd`, and `3bd1270`, pull on `fengxian`, and recreate only Airflow scheduler/worker. Do not delete shared run directories or Docker volumes.

## 2026-07-07 21:35 - Codex - T095 PGT-A baseline QC Python library preflight

### Goal

Fix the second `PGTA_20260706_162150_00C4FD` 64-core resume failure. The T094 cleanup resume reached `baseline_bam_uniformity_qc`, but both G10/G11 rule logs failed while importing `matplotlib` because the task loaded the container system `libstdc++.so.6` without `CXXABI_1.3.15`.

### Completed

- Read-only failure check confirmed latest DAG run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` is `failed`; `run_pgta_target` failed, mapping outputs `G10/G11.sorted.bam(.bai)` exist, `/qc` is empty, and samples are `failed`.
- Added TDD red tests for PGT-A subprocess env and baseline QC preflight; red tests failed on missing `MPLCONFIGDIR`, missing conda-lib `LD_LIBRARY_PATH`, and missing preflight call.
- Updated `bio_pgta` runner env to set `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`, `MPLCONFIGDIR=<workdir>/tmp/matplotlib`, set `LD_LIBRARY_PATH` to `PGTA_CONDA_LIB`, and preload conda `libstdc++.so.6` with `LD_PRELOAD`.
- Added baseline-QC-only Python import preflight for `matplotlib/numpy/pandas/pysam/scipy`, writing `logs/pgta.python_preflight.log`.
- Added dynamic artifact discovery for `pgta_python_preflight`.
- Updated `.env.example`, Compose Airflow env, API/DAG/QC/runbook docs, `SERVER_INFO.md`, `CURRENT_STATE.md`, and `TASKS.md`.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml exec -T airflow-worker python -m unittest dags.tests.test_pgta_metadata_runner.PgtaMetadataRunnerTests -v` on `fengxian` before fix | failed as expected | 4 failures: missing matplotlib dir/env and missing preflight |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q tests/test_run_diagnostics.py::test_list_pgta_artifacts_discovers_python_preflight_log` before fix | failed as expected | `pgta_python_preflight` artifact not discovered |
| targeted Airflow runner test after fix | success | 19 tests OK |
| targeted backend artifact test after fix | success | 1 passed |
| `git diff --check` | success | local non-runtime check |

### Tests

- Red/green targeted Airflow runner tests passed after implementation.
- Red/green backend artifact test passed after implementation.

### Not run / why

- Full backend pytest, full Airflow unittest discovery, Compose config, Airflow import check, and runtime resume are pending after commit/push and clean remote mirror sync.
- Frontend tests not run; no frontend code changed.

### Current git status

Local branch `codex/airflow/T088-pgta-snakemake-cache` has uncommitted T095 changes at this checkpoint.

### Risks

- The next same-workdir resume is a real PGT-A baseline QC run; it may still be long-running or fail later inside QC logic after the Python library path issue is fixed.
- Do not delete existing `mapping/*.sorted.bam(.bai)` outputs or the shared run directory.

### Open questions

- None for the library path fix.

### Next recommended task

Commit/push T095, cleanly fast-forward `fengxian`, rebuild/recreate Airflow scheduler/worker, verify preflight import in worker, then resume `PGTA_20260706_162150_00C4FD` once.

### Rollback notes

- Revert the T095 commit to remove the env/preflight behavior and rebuild/recreate Airflow scheduler/worker if needed.
- Do not use `docker compose down -v`, Docker prune commands, destructive Git commands, or broad file deletion.

## 2026-07-07 20:14 - Codex - T094 PGT-A resume temp BAM cleanup and retry

### Goal

Fix the failed PGT-A `baseline_qc` resume for `PGTA_20260706_162150_00C4FD` where interrupted `samtools sort` temp BAMs caused `File exists`, then safely trigger another same-workdir 64-core resume.

### Completed

- Added red tests first for PGT-A resume cleanup and backend artifact discovery; both failed at the expected missing behavior.
- Added `bio_pgta` resume cleanup after successful Snakemake `--unlock` and before the main resume command.
- Cleanup scope is limited to current `workdir/mapping/*.sorted.bam.tmp.*.bam`; it refuses non run-local workdirs and does not touch final BAM/BAI, FASTQ, QC, logs, config, PGT-A source, or rawdata.
- Wrote cleanup audit artifact `logs/pgta.resume.cleanup.tsv`.
- Added `pgta_resume_cleanup` to dynamic artifact discovery.
- Updated API contract, DAG spec, QC/logging docs, and deployment runbook.
- Rebuilt backend, recreated backend plus Airflow scheduler/worker only; did not touch Postgres/Redis/frontend and did not delete volumes.
- Confirmed before retry: no matching `PGTA_20260706_162150_00C4FD` process was running and 16 stale `G11.sorted.bam.tmp.*.bam` files existed.
- Triggered new resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z`.
- Verified cleanup log records all 16 deleted tmp BAMs, remaining tmp count is 0, command contains `--cores 64 --rerun-incomplete`, and no `--forceall`.
- Explicit `sync-airflow` now shows backend status `running`; active worker process shows G11 running with `fastp -w 16`.

### Changed files

- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git diff --check` | success | local non-runtime static check |
| red Airflow test on `fengxian` | failed as expected | tmp files remained before implementation |
| red backend artifact test on `fengxian` | failed as expected | `pgta_resume_cleanup` not discovered before implementation |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | compose config valid |
| targeted Airflow runner test on `fengxian` | success | new cleanup test passed |
| `docker compose -f docker-compose.yaml build backend && docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 51 passed |
| Airflow unittest discover on `fengxian` | success | 44 tests OK, 5 skipped logger interface unavailable in that Python env |
| `airflow dags list-import-errors` | success | `No data found` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-scheduler airflow-worker` | success | no volumes deleted; Postgres/Redis/frontend left running |
| pre-resume tmp/process checks | success | 16 stale temp BAMs, no matching running processes |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/reanalyze` | success | returned new run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` |
| cleanup/command/artifact checks | success | cleanup log has 16 rows; temp count 0; command has `--cores 64 --rerun-incomplete`; artifact API includes `pgta_resume_cleanup` |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/sync-airflow` | success | backend status `running`, `error_summary=null` for latest DAG run |

### Tests

- Remote backend full pytest passed: 51 passed.
- Remote Airflow DAG unittest discover passed: 44 OK, 5 skipped for logger-interface availability in that Python env.
- Airflow import check passed: `No data found`.
- Runtime cleanup evidence passed: 16 stale temp BAMs were recorded and deleted; remaining tmp count is 0.

### Not run / why

- Did not wait for terminal baseline QC success/failure; the real PGT-A resume is still running.
- Did not run frontend tests; no frontend files changed.
- Did not stop frontend/Postgres/Redis or delete any volume.
- Did not submit a new heavy PGT-A run; only resumed the existing failed workdir.

### Current git status

Code commits `1ce3fa6` and `0a8e756` are pushed to `origin/codex/airflow/T088-pgta-snakemake-cache`. This handoff/status update records runtime evidence after `0a8e756`.

### Risks

- The latest resume is a real baseline QC workload and may still take time. Do not interrupt it unless the user explicitly asks.
- If the latest resume fails, sync Airflow first and inspect `error_summary`, `snakemake.stderr.log`, and rule logs before deciding on another resume.
- The cleanup intentionally deletes only matching samtools sort temp BAMs; do not broaden the pattern without another explicit review.

### Open questions

- None for T094 code. Runtime terminal success/failure remains pending.

### Next recommended task

Continue observing `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z`. If it succeeds, call `sync-airflow` and verify `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, `baseline_qc_report.md`, `/api/runs/{analysis_id}/qc`, artifacts, and frontend QC panel. If it fails, call `sync-airflow`, record `error_summary` and stderr/rule logs, then decide whether another fix is warranted.

### Rollback notes

- Revert commit `0a8e756` to remove cleanup behavior and rebuild/redeploy backend plus recreate Airflow scheduler/worker if needed.
- Do not delete `shared/runs/PGTA_20260706_162150_00C4FD`; it contains the active resumed workdir and logs.
- Do not use `docker compose down -v`, Docker prune commands, destructive Git commands, or broad file deletion.

## 2026-07-07 18:08 - Codex - T093 PGT-A controlled interrupt and 64-core resume

### Goal

Implement and validate a safe resume path for the long-running PGT-A `baseline_qc` run `PGTA_20260706_162150_00C4FD`: add backend/API, Airflow, and frontend support for same-workdir PGT-A resume, then perform one controlled interruption of the old `--cores 1` run and resume it with `--cores 64 --rerun-incomplete`.

### Completed

- Added PGT-A `POST /api/runs/{analysis_id}/actions/reanalyze` support for `pipeline=pgta,target=baseline_qc,mode=resume`.
- Guardrails: PGT-A resume is allowed only for terminal failed/terminated runs; active running/submitted/queued runs, non-`baseline_qc` targets, `rerun_rule`, `clone_new`, rule/sample selectors, and `forceall` are rejected.
- Extended `bio_pgta` resume mode: first runs Snakemake `--unlock`, then runs the main command with `--cores ${PGTA_SNAKEMAKE_CORES:-64} --rerun-incomplete`; no `--forceall`.
- Added command artifacts: `logs/snakemake.unlock.command.txt`, unlock stdout/stderr logs, and updated `logs/snakemake.command.txt`.
- Added frontend `Resume with 64 cores` button for failed/terminated PGT-A `baseline_qc` runs only.
- Deployed backend/frontend and recreated Airflow scheduler/worker after the old run had failed, so the resume run used fresh code.
- Controlled-interrupted only exact matching processes for `PGTA_20260706_162150_00C4FD`; did not touch unrelated host processes.
- Synced the old DAG run to backend `failed`; `error_summary` captured Snakemake interruption and failed `fastp_bwa` context.
- Submitted resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z`.
- Verified resume command artifacts:
  - `snakemake.unlock.command.txt` contains `--cores 64 ... --unlock`.
  - `snakemake.command.txt` contains `--cores 64 ... --rerun-incomplete`.
  - `snakemake.command.txt` does not contain `--forceall`.
- Fresh status at 2026-07-07 18:09 CST: resume DAG run is still `running`, `run_pgta_target=running`; active rule processes show `bwa mem -t 16` and `samtools sort -@ 16`; no `qc/baseline` terminal artifacts yet.

### Changed files

- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/tests/test_pgta_reanalysis.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | success | branch `codex/airflow/T088-pgta-snakemake-cache` |
| red backend/DAG/frontend tests on `fengxian` | failed as expected | backend endpoint only supported WES; DAG had no PGT-A resume/unlock; frontend lacked PGT-A resume button |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | compose config valid |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q tests/test_pgta_reanalysis.py tests/test_wes_run_lifecycle.py` | success | 7 passed |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 50 passed |
| Airflow image unittest discover on `fengxian` | success | 43 tests OK, 5 skipped logger interface unavailable in that Python env |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 17 Vitest tests passed |
| `airflow dags list-import-errors` on `fengxian` | success | `No data found` |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend` | success | backend/frontend redeployed, no volumes deleted |
| `kill -TERM <snakemake pid>` then targeted child TERM if needed | success | only exact `PGTA_20260706_162150_00C4FD` processes were targeted |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/sync-airflow` | success | old run became backend `failed`, samples failed, `error_summary` non-null |
| `POST /api/runs/PGTA_20260706_162150_00C4FD/actions/reanalyze` | success | returned `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z`, status `submitted` |
| final read-only monitor at 18:09 CST | success | resume run still `running`; command has 64 cores/rerun-incomplete; G11 BWA/Samtools active; no baseline QC files yet |

### Tests

- Remote backend full pytest passed: 50 passed.
- Remote Airflow DAG unittest discover passed: 43 OK, 5 skipped for logger-interface availability in that Python env.
- Remote frontend Docker test target passed: 17 Vitest tests.
- Airflow import check passed: `No data found`.
- Runtime command evidence passed: `--unlock`, `--cores 64`, `--rerun-incomplete`, and no `--forceall`.

### Not run / why

- Did not call final `sync-airflow` for the resume DAG run because it is still running.
- Did not verify `baseline_qc_summary.tsv`, `/qc`, or frontend QC panel because `qc/baseline` outputs do not exist yet.
- Did not submit any additional heavy PGT-A run.
- Did not use `docker compose down -v`, `docker system prune`, or `docker volume prune`.

### Current git status

Code commits `6f9d617` and `2821a5e` are pushed to `origin/codex/airflow/T088-pgta-snakemake-cache`. This handoff/status update records runtime evidence after `2821a5e`.

### Risks

- The resumed baseline QC is still a real mapping/QC workload and may run for a while. Do not interrupt it again unless the user explicitly asks.
- Backend status may remain `submitted/running` until the frontend auto-sync or manual `sync-airflow` runs; the terminal truth is Airflow.
- If the resume run fails, sync first and inspect `error_summary`, `snakemake.stderr.log`, and rule logs before deciding on another action.

### Open questions

- None for code capability. Runtime success/failure of the resumed baseline QC is still pending.

### Next recommended task

Continue monitoring `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z`. If it reaches `success`, call `sync-airflow` and verify `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, `baseline_qc_report.md`, `/api/runs/{analysis_id}/qc`, artifacts, and frontend QC panel. If it reaches `failed`, call `sync-airflow`, record `error_summary` and stderr/rule logs, then decide whether another resume is warranted.

### Rollback notes

- Revert commit `2821a5e` to remove PGT-A resume support and rebuild/redeploy backend/frontend/Airflow images if needed.
- Do not delete `shared/runs/PGTA_20260706_162150_00C4FD`; it contains the current resumed workdir and logs.
- Use only safe service stops/recreates; never use `down -v`, Docker prune commands, or destructive Git commands.

## 2026-07-07 14:13 - Codex - T092 PGT-A baseline_qc current run monitor

### Goal

Safely monitor and record the current real PGT-A `baseline_qc` run `PGTA_20260706_162150_00C4FD` without stopping, restarting, retrying, or submitting another heavy run. If the run had reached terminal state, sync Airflow and verify QC/artifacts; otherwise leave clear evidence and next steps.

### Completed

- Confirmed `fengxian` services are running and `docker compose -f docker-compose.yaml config --quiet` still passes.
- Confirmed Airflow `bio_pgta` run `manual__PGTA_20260706_162150_00C4FD` is still `running` as of 2026-07-07 14:11 CST.
- Confirmed Airflow task states: `validate_request=success`, `prepare_pgta_config=success`, `run_pgta_target=running`, `collect_pgta_artifact=None`.
- Confirmed backend run detail still reports `status=running`, `target=baseline_qc`, `selected_count=2`, and samples `G10/G11` both `running`.
- Confirmed this historical run still uses `--cores 1` in `logs/snakemake.command.txt`; it started before T091 and cannot prove the new 64-core default.
- Confirmed G10 mapping completed; `logs/bwa/G10.log` reports BWA real time `33885.400 sec`.
- Confirmed G11 BWA is still progressing; `logs/bwa/G11.log` and `mapping/G11.sorted.bam.tmp.*` files are updating.
- Confirmed no terminal baseline QC outputs exist yet: no `qc/baseline` files, `/qc` returns zero metrics, and artifacts currently only include command/config files.
- Did not call `sync-airflow`, because Airflow has not reached `success` or `failed`.
- Did not stop, restart, clear, retry, resume, or submit any PGT-A run.

### Changed files

- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | success | local branch `codex/airflow/T088-pgta-snakemake-cache` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | no compose errors |
| `docker compose -f docker-compose.yaml ps` on `fengxian` | success | backend/frontend/Airflow/Postgres/Redis running |
| `airflow dags list-runs -d bio_pgta --output table` on `fengxian` | success | `PGTA_20260706_162150_00C4FD` still `running` |
| `curl http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD` | success | backend status `running`, target `baseline_qc` |
| `curl http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD/samples` | success | `G10/G11` sample status `running` |
| `curl http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD/qc` | success | `pass=0,warn=0,fail=0,unknown=0` because QC output has not been generated |
| `curl http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD/artifacts` | success | currently command/config artifacts only |
| `airflow tasks states-for-dag-run bio_pgta manual__PGTA_20260706_162150_00C4FD` | success | `run_pgta_target` running, collect task not started |
| `cat shared/runs/PGTA_20260706_162150_00C4FD/logs/snakemake.command.txt` | success | command contains `--cores 1` |
| `tail shared/runs/PGTA_20260706_162150_00C4FD/logs/bwa/G11.log` | success | BWA progress lines still updating |

### Tests

- This task is a live-run monitor/status update, not a code change.
- Remote-only runtime checks above were run on `ssh fengxian`.
- No local Docker/Python/Snakemake/Airflow tests were run or used as acceptance evidence.

### Not run / why

- `sync-airflow` was not run because the Airflow DAG run is still `running`; syncing now would not validate success/failure artifacts.
- The 64-core metadata smoke was not run because the plan requires waiting until the current `baseline_qc` run reaches terminal state first.
- Airflow worker/scheduler were not restarted to avoid perturbing the active `run_pgta_target` task.
- No new heavy `baseline_qc` run was submitted.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. This T092 update only changes state documents; runtime code and services were not modified.

### Risks

- `snakemake.stdout.log` and `snakemake.stderr.log` do not exist while the current Snakemake subprocess is still running; the current runner appears to write captured stdout/stderr only after process exit. Rule logs under `logs/bwa` are the live progress source for this run.
- The current run is using `--cores 1`; allowing it to finish is safe but slow. Switching it to 64 cores would require a separate stop/resume/rerun decision and is not part of T092.
- If the run eventually fails, do not blindly retry; sync Airflow first, inspect `error_summary`, stderr, and rule logs, then decide whether to resume.

### Open questions

- After `PGTA_20260706_162150_00C4FD` reaches terminal state, should Airflow worker/scheduler be safely recreated before the lightweight metadata smoke, or is confirming module reload enough?

### Next recommended task

Wait for `PGTA_20260706_162150_00C4FD` to finish. If it succeeds, call `sync-airflow`, verify `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, `baseline_qc_report.md`, `/qc`, artifacts, and frontend QC panel. If it fails, call `sync-airflow`, record `error_summary` and stderr tail. Only after terminal state, run one lightweight metadata smoke to verify `logs/snakemake.command.txt` contains `--cores 64`.

### Rollback notes

- This turn only updated docs/status files. Revert the T092 docs commit if needed.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, or `git reset --hard`.

## 2026-07-07 11:45 - Codex - T091 PGT-A 64-core runner and frontend auto-sync

### Goal

Make future PGT-A Airflow runs use Snakemake `--cores 64` by default and make the frontend automatically sync selected active runs, without interrupting the already-running `PGTA_20260706_162150_00C4FD` baseline_qc run.

### Completed

- Added `PGTA_SNAKEMAKE_CORES=64` to `.env.example` and Airflow Compose environment.
- Updated `bio_pgta` and `bio_pgta_airflow` runners to read `PGTA_SNAKEMAKE_CORES`, validate it as a positive integer, and write the resulting value to `logs/snakemake.command.txt`.
- Added Airflow runner tests for default `--cores 64` and env override behavior.
- Added frontend selected-run auto sync: active `submitted/running/queued` runs with `dag_run_id` call `sync-airflow` every 15 seconds, refresh run detail/list/samples/rules/artifacts/QC/current log, and stop when terminal.
- Added frontend UI text `Auto sync active` / `Last synced ...`; manual `Sync Airflow` remains.
- Rebuilt and redeployed only the frontend container on `fengxian`; Airflow worker/scheduler/API containers were not recreated.
- Confirmed current run `PGTA_20260706_162150_00C4FD` still reports backend status `running` after the redeploy.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `dags/pgta_metadata_runner.py`
- `dags/pgta_airflow_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `dags/tests/test_pgta_airflow_runner.py`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/styles.css`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `docs/20_PGTA_LEVEL4_AUDIT.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `py -3 -m unittest ...test_pgta_metadata_runner... ...test_pgta_airflow_runner... -v` | success | local development check only, 4 tests OK; not used as acceptance |
| `git diff --check` | success | no whitespace errors |
| `git push origin codex/airflow/T088-pgta-snakemake-cache` | success | pushed code commits `b30be7e`, `fb107a4` |
| `ssh fengxian 'cd /home/jiucheng/project/airflow-demo && git pull --ff-only && docker compose -f docker-compose.yaml config --quiet'` | success | mirror fast-forwarded; Compose config valid |
| `docker run --rm --entrypoint /usr/local/bin/python ... airflow-demo/airflow:0.1.0 -m unittest ... -v` | success | remote Airflow image, 4 tests OK |
| `docker build --target test -f frontend/Dockerfile frontend` | failed then success | first failed because the new test captured Testing Library internal intervals; fixed test and reran, 16 Vitest tests passed |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| `docker compose -f docker-compose.yaml build frontend` | success | production frontend image rebuilt |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend` | success | recreated frontend only; no volumes deleted |
| `curl -fsS http://127.0.0.1:12959/` | success after nginx startup | returned React HTML |
| `docker compose -f docker-compose.yaml config \| grep -n PGTA_SNAKEMAKE_CORES` | success | rendered `PGTA_SNAKEMAKE_CORES: "64"` |
| `curl -fsS http://127.0.0.1:8000/api/runs/PGTA_20260706_162150_00C4FD` | success | run still `status="running"` |

### Tests

- Remote Airflow-image runner tests: 4 passed.
- Remote frontend Docker test target: 16 Vitest tests passed.
- Airflow DAG import check: `No data found`.
- Frontend production build passed and HTTP 12959 returned HTML.

### Not run / why

- Did not submit a new PGT-A `baseline_qc` run because `PGTA_20260706_162150_00C4FD` is still running.
- Did not stop or resume the current baseline_qc run; T091 intentionally only affects future PGT-A task starts.
- Did not recreate Airflow worker/scheduler/API containers to avoid interrupting or perturbing the active baseline_qc run. Code defaults still make future imported runner commands default to 64 cores.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. Runtime validation ran on `fengxian` at commit `fb107a4`; this handoff/status update follows that validation.

### Risks

- An already-running Snakemake process keeps its original `--cores 1` command; to make `PGTA_20260706_162150_00C4FD` use 64 cores, it would need a separate stop/resume or rerun decision.
- Running Airflow worker processes were not recreated. The code default is now 64, but if Airflow keeps a stale imported module in a long-lived worker process, a worker restart after the active run finishes may be prudent before a new heavy baseline_qc run.
- `--cores 64` is Snakemake's available core pool; actual parallelism still depends on the PGT-A Snakefile `threads` declarations and resource rules.

### Open questions

- After the current baseline_qc run finishes, should we run one lightweight metadata smoke to confirm `logs/snakemake.command.txt` contains `--cores 64`, or restart Airflow worker first and then run the next baseline_qc smoke?

### Next recommended task

Wait for `PGTA_20260706_162150_00C4FD` to finish, then sync it from the frontend. If it succeeds, verify baseline QC artifacts/QC panel; if it fails, inspect stderr/error_summary and decide whether to resume with the new 64-core default.

### Rollback notes

- Revert the T091 commits and redeploy frontend if needed.
- To revert only frontend polling, revert `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, and `frontend/src/styles.css`, rebuild frontend, then `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`.
- Do not use `docker compose down -v`, `docker system prune`, or `docker volume prune`.

## 2026-07-06 22:58 - Codex - T090 sample lifecycle status sync

### Goal

Fix the frontend Samples table showing `pending` forever even after a run was submitted or had reached Airflow `success/failed`.

### Completed

- Traced the issue through frontend -> API -> DB and confirmed the frontend was displaying backend data correctly.
- Root cause: `sample.status` was initialized as `pending`, but backend submit/reanalysis/sync paths only updated `analysis_run.status`, never sample lifecycle status.
- Added red backend tests showing:
  - submit left samples as `pending` instead of `running`;
  - sync success left samples as `pending` instead of `success`;
  - sync failed left samples as `pending` instead of `failed`.
- Updated backend submit/reanalyze paths to mark samples `running`.
- Updated explicit `sync-airflow` to map Airflow state back to sample status: `success -> success`, `failed -> failed`, active states to `running`.
- Rebuilt and redeployed backend on `fengxian`.
- Explicitly synced recent visible runs so the live UI no longer shows stale pending values for those runs.

### Changed files

- `backend/app/run_service.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_submit.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| targeted backend tests after test-only commit on `fengxian` | failed as expected | 3 failures showed actual sample status was still `pending` |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q tests/test_run_submit.py::... tests/test_run_diagnostics.py::...` | success | 3 targeted tests passed after implementation |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 48 passed |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend` | success | recreated backend only; no volumes deleted |
| `curl http://127.0.0.1:8000/api/health` | success | `{"status":"ok"}` |
| explicit sync for recent visible runs | success | refreshed sample statuses without submitting new DAG runs |

### Tests

- Red targeted tests failed with `pending != running/success/failed`.
- Green targeted tests passed: 3 passed.
- Full backend pytest passed: 48 passed.
- Runtime API sample checks passed:
  - `PGTA_20260706_141915_5BE5E2`: `E2/E3=success`.
  - `PGTA_20260706_140854_8F2CA4`: `E2=success`.
  - `WES_20260705_164813_C5561C`: `S001/S002=success`.

### Not run / why

- Frontend Docker tests were not rerun because the frontend code was not modified; Samples table already reads `sample.status` from the API.
- No new PGT-A/WES DAG run was submitted. Existing runs were only synced through the existing `sync-airflow` endpoint.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. Runtime validation ran on `fengxian` at commit `065907c`; this handoff/status update follows that validation.

### Risks

- Historical runs not included in the recent visible sync batch may still show old `pending` sample statuses until the user clicks `Sync Airflow` on that run.
- For failed runs, sample status is currently run-level `failed`; fine-grained per-sample failure attribution remains a future rule/qsub enhancement.

### Open questions

- None for this fix.

### Next recommended task

Return to the prior demo roadmap: user-confirmed PGT-A `baseline_qc` Level 4 smoke with at least 2 samples, or T080 demo smoke report/script.

### Rollback notes

- Revert the T090 commits, rebuild/redeploy backend, and re-sync affected runs if needed. Do not delete volumes.

## 2026-07-06 22:40 - Codex - T089 demo log/timezone alignment

### Goal

Fix the user-visible mismatch where demo logs and timestamps did not line up with the `fengxian` host clock.

### Completed

- Confirmed `fengxian` host time is `Asia/Shanghai`, while backend/Airflow containers previously had `TZ=<unset>` and Airflow was configured as `core.default_timezone=utc`, `webserver.default_ui_timezone=UTC`.
- Added Compose timezone defaults: `AIRFLOW_DEMO_TZ=Asia/Shanghai`, `AIRFLOW_DEFAULT_TIMEZONE=Asia/Shanghai`, and `AIRFLOW_DEFAULT_UI_TIMEZONE=Asia/Shanghai`.
- Recreated backend, frontend, and Airflow service containers so their process logs use `+0800 CST`.
- Updated frontend timestamp rendering to convert timezone-aware backend ISO timestamps into fixed `YYYY-MM-DD HH:mm:ss Asia/Shanghai` text.
- Added a frontend test covering UTC API timestamp rendering as Shanghai display time.
- Documented the timezone contract and verification evidence.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `frontend/Dockerfile`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `SERVER_INFO.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Rendered `AIRFLOW__CORE__DEFAULT_TIMEZONE=Asia/Shanghai`, `AIRFLOW__WEBSERVER__DEFAULT_UI_TIMEZONE=Asia/Shanghai`, `TZ=Asia/Shanghai`, and frontend build arg `VITE_DISPLAY_TIME_ZONE=Asia/Shanghai` |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | 15 Vitest tests passed |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success | Production frontend bundle rebuilt with `Asia/Shanghai` display timezone |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend airflow-api-server airflow-scheduler airflow-worker` on `fengxian` | success | Recreated only affected services; no volumes deleted |
| Health probes on `fengxian` | success | backend `/api/health`, Airflow `/health`, and frontend HTTP 200 |
| container date/timezone probe on `fengxian` | success | backend/frontend/Airflow containers report `TZ=Asia/Shanghai` and `date` as `+0800 CST` |
| Airflow timezone/log probe on `fengxian` | success | Airflow config reports core/UI `Asia/Shanghai`; scheduler/webserver logs show `+0800` and `Configured default timezone Asia/Shanghai` |

### Tests

- Remote frontend Docker test target passed: 15 tests.
- Remote Compose config passed.
- Runtime health and timezone probes passed on `fengxian`.

### Not run / why

- No backend pytest or DAG unittest was rerun because this change did not modify backend Python, DAG code, database schema, or Snakemake behavior.
- No new PGT-A or WES run was submitted; this was a display/log timezone fix only.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. Runtime validation ran on `fengxian` at commit `f2fdff2`; this handoff/status update follows that validation.

### Risks

- Airflow `/health` heartbeat and HTTP `Date` headers can still show UTC/GMT by protocol/API convention. Airflow service logs and UI timezone config now use `Asia/Shanghai`.
- Historical DB timestamps remain timezone-aware values and were not rewritten.

### Open questions

- None for this fix.

### Next recommended task

Return to the prior demo roadmap: user-confirmed PGT-A `baseline_qc` Level 4 smoke with at least 2 samples, or T080 demo smoke report/script.

### Rollback notes

- Revert the T089 commits, rebuild/redeploy frontend if needed, and recreate backend/frontend/Airflow services. Do not delete volumes.

## 2026-07-06 22:06 - Codex - T088 PGT-A run-local Snakemake cache fix

### Goal

Fix the PGT-A submit-after-click failure where backend successfully triggered `bio_pgta`, but the DAG failed almost immediately before the user could see a meaningful running state in Airflow.

### Completed

- Investigated latest failed run `PGTA_20260706_135413_598BA1`.
- Confirmed backend submit succeeded and Airflow created `manual__PGTA_20260706_135413_598BA1`.
- Identified root cause in `logs/snakemake.stderr.log`: Snakemake tried to create `/home/airflow/.cache/snakemake` and failed with `PermissionError`.
- Added TDD tests for `run_pgta_target` and `run_snakemake9_with_logger` requiring run-local cache directories and `XDG_CACHE_HOME`.
- Updated `bio_pgta` runner to create `<workdir>/tmp/xdg-cache`, set `XDG_CACHE_HOME`, and write `logs/snakemake.command.txt`.
- Updated `bio_pgta_airflow` Snakemake 9 logger runner with the same run-local cache behavior and command log.
- Verified a new metadata smoke run `PGTA_20260706_140854_8F2CA4` reaches Airflow/backend `success`.

### Changed files

- `dags/pgta_metadata_runner.py`
- `dags/pgta_airflow_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `dags/tests/test_pgta_airflow_runner.py`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker run --rm --entrypoint /usr/local/bin/python ... test_run_pgta_target_metadata... test_run_snakemake9...` on `fengxian` after tests-only commit | failed as expected | both tests failed because `<workdir>/tmp/xdg-cache` did not exist |
| same targeted test command after implementation | success | 2 tests OK |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | no compose errors |
| `docker run --rm --entrypoint /usr/local/bin/python ... -m unittest dags.tests.test_bio_pgta_dag dags.tests.test_pgta_metadata_runner dags.tests.test_pgta_airflow_runner -v` | success | 20 tests OK |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| remote API metadata smoke for `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` | success | created/submitted `PGTA_20260706_140854_8F2CA4`; sync statuses running, running, success |
| `airflow dags list-runs -d bio_pgta | grep PGTA_20260706_140854_8F2CA4` | success | Airflow state `success` |
| service health probes | success | backend `{"status":"ok"}`, frontend HTTP 200, Airflow scheduler/metadatabase healthy |

### Tests

- Red test confirmed the missing cache behavior before implementation.
- Targeted tests passed after implementation.
- Full PGT-A DAG/runner unit suite passed: 20 tests.
- Airflow import check passed.
- Real PGT-A metadata smoke passed and generated:
  - `logs/run_metadata.tsv` with 11 lines.
  - `logs/snakemake.command.txt`.
  - `logs/snakemake.stderr.log` without `/home/airflow/.cache/snakemake` PermissionError.
  - artifacts including `snakemake_command` and `run_metadata`.

### Not run / why

- No real `baseline_qc` Level 4 run was executed; this fix only targets metadata submit failure and Snakemake cache handling.
- No Docker volumes were deleted and no prune commands were run.
- No host `/home/airflow` chmod or PGT-A source directory modification was done.

### Current git status

Work is on branch `codex/airflow/T088-pgta-snakemake-cache`. Code verification passed at commit `dd5c6e7`; this handoff/status update is the final docs batch for the same branch.

### Risks

- Metadata target is fast, so Airflow UI may still show `running` only briefly; the durable evidence is the DAG run final state and frontend/API sync result.
- `baseline_qc` remains heavier than metadata and still needs user-confirmed samples/window before running.

### Open questions

- Which two samples should be used for the first `baseline_qc` Level 4 smoke?

### Next recommended task

Ask the user to open `http://fengxian:12959/`, create a small `metadata smoke` run, submit, and verify the UI can sync to success. Then proceed to user-confirmed `baseline_qc` Level 4 smoke or T080 demo script.

### Rollback notes

- Stop services safely with `docker compose -f docker-compose.yaml down` only.
- Revert T088 commits on `codex/airflow/T088-pgta-snakemake-cache` if needed.
- Do not chmod `/home/airflow`, do not use `down -v`, and do not run Docker prune commands.

## 2026-07-06 21:45 - Codex - T085/T086/T087 PGT-A baseline_qc staged integration

### Goal

Re-center the next development phase on the PGT-A demo path: audit the real PGT-A workflow for a safe Level 4 target, add controlled `baseline_qc` support across backend/Airflow/frontend, expose baseline artifacts/QC, and keep real execution gated until the user confirms samples and runtime window.

### Completed

- Performed a read-only audit of `/home/jiucheng/pipelines/PGT_A` on `fengxian`.
- Confirmed `baseline_qc` exists in the real Snakefile, belongs to `pipeline.mode=build_ref`, requires at least 2 baseline/reference samples, and emits `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, and `baseline_qc_report.md`.
- Added `baseline_qc` to the controlled PGT-A target allowlist.
- Enforced the 2-selected-sample minimum in both run creation and submit validation.
- Extended `bio_pgta` config generation for `baseline_qc` with `pipeline.targets=["mapping","metadata","baseline_qc"]`, `build_reference.groups.demo`, `--cores 1`, and no dry-run flag.
- Added dynamic artifact discovery for PGT-A baseline QC summary/pass-samples/report.
- Added PGT-A baseline QC TSV parsing into existing `qc_metric` and `/api/runs/{analysis_id}/qc`.
- Updated the frontend target selector with `baseline QC smoke`, disabled Create Run until 2 samples are selected, and hid Submit for invalid baseline created runs.
- Rebuilt/redeployed backend, frontend, and Airflow services on `fengxian`.

### Changed files

- `backend/app/run_service.py`
- `backend/app/diagnostics_service.py`
- `backend/app/qc_service.py`
- `backend/tests/test_run_creation.py`
- `backend/tests/test_run_submit.py`
- `backend/tests/test_run_diagnostics.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/17_DEMO_SCRIPT.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `docs/20_PGTA_LEVEL4_AUDIT.md`
- `SERVER_INFO.md`
- `TASKS.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git checkout -b codex/fullstack/T085-pgta-main-demo` | success | local feature branch |
| read-only PGT-A audit via `ssh fengxian` heredoc | success | no remote writes; confirmed `baseline_qc` targets and constraints |
| `git diff --check` | success | only CRLF warning for `MANIFEST.json` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose v2.24.7 |
| `docker compose -f docker-compose.yaml build backend frontend airflow-worker airflow-scheduler airflow-api-server` on `fengxian` | success | frontend production build passed |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` on `fengxian` | success | 48 passed |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | failed first, then success | first failure was an async QC test race; after fixing test wait, 14 passed |
| `docker run --rm --entrypoint /usr/local/bin/python -v /home/jiucheng/project/airflow-demo:/repo:ro -w /repo airflow-demo/airflow:0.1.0 -m unittest dags.tests.test_bio_pgta_dag dags.tests.test_pgta_metadata_runner -v` | success | 14 DAG/runner tests OK |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| `docker compose -f docker-compose.yaml up -d --no-deps backend frontend airflow-api-server airflow-scheduler airflow-worker` | success | recreated only affected services; no volume deletion |
| `curl http://127.0.0.1:8000/api/health` | success | `{"status":"ok"}` |
| `curl http://127.0.0.1:12959/` | success | HTTP 200, title `airflow-demo` |
| `curl http://127.0.0.1:12958/health` | success after startup retry | Airflow scheduler/metadatabase healthy |

### Tests

- Backend Dockerized pytest: 48 passed.
- Frontend Dockerized Vitest target: 14 passed.
- Airflow/DAG unittest: 14 passed.
- Airflow import check: no import errors.
- Service smoke after redeploy: backend health ok, frontend HTTP 200, Airflow health healthy.

### Not run / why

- No real `baseline_qc` run was submitted. Audit showed it triggers mapping + metadata + baseline QC and requires at least 2 samples, so Level 4 execution must wait for user-confirmed sample selection and runtime window.
- No CNV production run, qsub, MailHog email, NIPT, BS10610 migration, or true PGT-A report/MultiQC registration was attempted.

### Current git status

Implementation commit `4cf6f6e` is pushed on branch `codex/fullstack/T085-pgta-main-demo`. This handoff/status update is the final docs batch for the same branch.

### Risks

- `baseline_qc` is not a lightweight single-sample smoke; it may consume meaningful runtime and mapping resources even with `--cores 1`.
- The generated run-local config has not yet been validated by a real `baseline_qc` execution.
- If the real PGT-A workflow writes unexpected relative paths, the Level 4 smoke should stop and preserve logs rather than retrying.

### Open questions

- Which two PGT-A samples should be used for the first Level 4 staged run?
- What runtime window and monitoring expectations are acceptable for that run?
- If `baseline_qc` is too heavy, should we choose a smaller real target after another audit pass?

### Next recommended task

Run a user-confirmed PGT-A Level 4 smoke for `target=baseline_qc` with exactly 2 selected samples, low concurrency, and output isolated under `shared/runs/<analysis_id>`. If that passes, move to T080/T081 demo script/report, then T034/T063 MailHog notifications.

### Rollback notes

- To stop services safely: `docker compose -f docker-compose.yaml down` only.
- Do not use `down -v`, `docker system prune`, or `docker volume prune`.
- To revert this branch before merge, revert the commit(s) on `codex/fullstack/T085-pgta-main-demo`; no production PGT-A directory files were modified.

## 2026-07-06 01:35 - Codex - T051 PGT-A submit workspace usability fix

### Goal

Fix the live frontend usability issue where the PGT-A submit form was cramped inside the left run-list sidebar and looked difficult to submit. Keep the backend/API contract unchanged and do not run PGT-A jobs as part of this UI fix.

### Completed

- Confirmed the backend scan API works for `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28`.
- Added a failing frontend test that requires a main `Submit new analysis` region, keeps `New PGT-A Run` out of the run-list aside, and shows clear Create Run enablement guidance.
- Moved `New PGT-A Run` and `New WES Mock Run` into a main submit workspace above run detail.
- Left sidebar now only contains the run list.
- Added `Select at least one scanned sample to enable Create Run.` guidance and selected-sample count text.
- Updated layout CSS so the PGT-A form uses the main content width and the candidate sample table is no longer squeezed into the side rail.
- Rebuilt and redeployed only the `frontend` service on `fengxian`.

### Modified files

- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/06_FRONTEND_SPEC.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands and results

| Command | Result |
|---|---|
| `git checkout -b codex/frontend/T051-pgta-submit-workspace` | success |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` after test-only commit | failed as expected: 1 failed, 11 passed; missing `Submit new analysis` region and form still inside run-list aside |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` after implementation | success: 12 tests passed |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | success; Vite production build generated `index-BJnogiqz.css` and `index-BYax1L4P.js` |
| `docker compose -f docker-compose.yaml up -d frontend` on `fengxian` | success; recreated only frontend while backend stayed healthy |
| `curl http://100.112.254.72:12959/` | success, HTTP 200 |
| `curl http://100.112.254.72:8000/api/health` | success, HTTP 200 |
| deployed CSS grep for `submit-workspace` | success |

### Not run / why

- No real PGT-A job was submitted; this task only fixed the submit UI layout and guidance.
- Browser automation was attempted but the in-app browser control timed out; verification used Dockerized frontend tests plus live HTTP/CSS checks.
- No backend, DAG, Snakemake, DB migration, or Docker volume operation was needed.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was used.

### Current git status

Work is on branch `codex/frontend/T051-pgta-submit-workspace`. Runtime validation and live frontend deployment ran on the `fengxian` mirror at commit `872d59b`, followed by this docs/status update.

### Risks

- The page is still a single-page workspace, not a fully routed dashboard; this fix makes the existing workflow usable but does not add route-level navigation.
- PGT-A full production flow is still not deployed; this only improves the existing metadata/dry-run/failure-smoke submission UI.

### Next recommended task

Either continue with PGT-A real target staged integration, or add T080 smoke/demo scripting so the current PGT-A/WES demo can be replayed reliably from the UI and API.

### Rollback notes

- Revert the frontend/layout commits with normal `git revert` and rebuild/redeploy `frontend`.
- Stop services, if needed, with `docker compose -f docker-compose.yaml down` only; do not use `down -v`.

## 2026-07-06 00:54 - Codex - T060/T054 WES mock QC parser and panel

### Goal

Add WES mock QC output, parse successful `bio_wes_qsub` run QC into biodemo `qc_metric` through explicit `sync-airflow`, expose `GET /api/runs/{analysis_id}/qc`, and show the QC panel in the React run detail. Keep scope mock-only: no MailHog, NIPT, real qsub, real WES QC, MultiQC, or DB migration.

### Completed

- Added `reports/qc_summary.tsv` generation to the WES mock `final_summary` rule.
- Added backend QC parser/import service, idempotent refresh into `qc_metric`, sample `qc_status` aggregation, and `GET /api/runs/{analysis_id}/qc`.
- Extended `sync-airflow` so successful `wes_qsub` DAG runs import QC after Airflow reaches `success`.
- Extended dynamic artifacts to include `wes_qc_summary`.
- Added frontend API types/client and a run detail QC panel with pass/warn/fail/unknown summary, metric table, and empty state.
- Updated API/frontend/DAG/Snakemake/QC/runbook/testing docs, task status, current state, manifest, and this handoff.

### Modified files

- `backend/app/qc_service.py`
- `backend/app/diagnostics_service.py`
- `backend/app/main.py`
- `backend/tests/test_run_diagnostics.py`
- `dags/wes_qsub_runner.py`
- `dags/tests/test_wes_qsub_runner.py`
- `pipelines/wes/workflow/Snakefile`
- `pipelines/tests/test_wes_mock_contract.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/styles.css`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands and results

| Command | Result |
|---|---|
| `git checkout -b codex/fullstack/T060-T054-wes-qc-panel` | success |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success |
| `docker compose -f docker-compose.yaml build backend frontend airflow-worker airflow-scheduler airflow-api-server` on `fengxian` | success |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` on `fengxian` | success, `43 passed` |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q tests/test_run_diagnostics.py` on `fengxian` | success, `9 passed` |
| Dockerized `python -m unittest pipelines.tests.test_wes_mock_contract -v` on `fengxian` | success, `Ran 7 tests OK` |
| Dockerized `python -m unittest dags.tests.test_bio_wes_qsub_dag dags.tests.test_wes_qsub_runner -v` on `fengxian` | success, `Ran 11 tests OK` |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success, `11 passed` |
| `airflow dags list-import-errors` in Airflow scheduler container | success, `No data found` |
| API/frontend WES QC smoke | success: `WES_20260705_164813_C5561C` reached `success`, `/qc` returned `pass=6,warn=0,fail=0,unknown=0`, artifacts include `wes_qc_summary` |
| `test -s shared/runs/WES_20260705_164813_C5561C/reports/qc_summary.tsv` on `fengxian` | success; TSV contains deterministic rows for `S001/S002` |

### Not run / why

- No MailHog success/failure email was implemented or tested; T034/T063 remain next.
- No NIPT, real qsub, real WES data, real production QC, MultiQC HTML, or artifact table registration was implemented.
- No DB migration was added; existing `qc_metric` and `sample.qc_status` schema was sufficient.
- One smoke shell bundle exited nonzero only because a final `head` check inherited a CRLF path from a PowerShell here-string; the direct follow-up `test -s .../qc_summary.tsv && head ...` passed.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was used.

### Current git status

Work is on branch `codex/fullstack/T060-T054-wes-qc-panel`. Runtime validation ran on the `fengxian` mirror at commit `e22ea41`, followed by this docs/status update.

### Risks

- WES QC values are deterministic mock values for demo display only; they are not valid production WES QC.
- QC import is tied to explicit `sync-airflow`; the frontend must sync after DAG success before QC appears.
- Artifacts are still dynamically discovered; T061 artifact table registration and MultiQC report handling remain open.

### Next recommended task

Proceed to T034/T063: MailHog success/failure notification with QC and error-summary links. T080 smoke script/reporting is also a good next slice now that PGT-A and WES mock visible paths both exist.

### Rollback notes

- Revert repository changes with normal `git revert`.
- Stop services with `docker compose -f docker-compose.yaml down` only; do not use `down -v`.
- The WES smoke workdir `shared/runs/WES_20260705_164813_C5561C` is disposable demo output, but do not delete shared data without explicit user approval.

## 2026-07-06 00:24 - Codex - T044/T056 WES mock resume/rerun lifecycle

### Goal

Expose the WES mock `bio_wes_qsub` path through FastAPI/React and add same-workdir `resume` plus selected-rule `rerun_rule` without real qsub, real WES data, QC, email, NIPT, `clone_new`, or `--forceall`.

### Completed

- Added WES mock `POST /api/runs` creation for fixed samples `S001/S002`.
- Extended submit action to dispatch both `pgta` and `wes_qsub`; WES submit passes `backend_event_url=http://backend:8000/api/events/snakemake`.
- Added `POST /api/runs/{analysis_id}/actions/reanalyze` for WES `resume` and `rerun_rule`.
- Extended `bio_wes_qsub` runner validation and command construction for `new/resume/rerun_rule`.
- Added `logs/snakemake.command.txt` artifact to prove `--forcerun` use and absence of `--forceall`.
- Added frontend WES mock create-and-submit panel and WES detail `Resume` / `Rerun rule` controls.
- Verified full remote WES smoke: `WES_20260705_162041_2507AF` initial submit, resume, and `rerun_rule fastp/S001` all reached success.
- Updated API, frontend, DAG, Snakemake/qsub, logging, runbook, testing, task, current-state, and manifest docs.

### Changed files

- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_wes_run_lifecycle.py`
- `dags/wes_qsub_runner.py`
- `dags/tests/test_wes_qsub_runner.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/styles.css`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| red backend WES lifecycle tests on `fengxian` | failed as expected | WES create returned 422; reanalyze route returned 404 |
| red DAG runner tests on `fengxian` | failed as expected | `resume` rejected; `build_snakemake_command(mode=...)` unsupported |
| red frontend Docker test target on `fengxian` | failed as expected | missing WES panel and reanalysis controls |
| `docker compose -f docker-compose.yaml build backend` | success | Built `airflow-demo/backend:0.1.0` |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 40 tests passed |
| Airflow/DAG unittest in `airflow-demo/airflow:0.1.0` | success | 11 tests OK; used `/tmp/airflow` for logs |
| `docker build --target test -f frontend/Dockerfile frontend` | success | 10 Vitest tests passed |
| `docker compose -f docker-compose.yaml build frontend` | success | TypeScript and Vite production build passed |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend frontend` | success | Applied rebuilt backend/frontend images; no volumes deleted |
| `docker compose -f docker-compose.yaml config --quiet` | success | Latest compose config rendered |
| `docker compose -f docker-compose.yaml exec -T airflow-scheduler airflow dags list-import-errors` | success | `No data found` |
| WES API/Airflow smoke for `WES_20260705_162041_2507AF` | success | new, resume, and rerun_rule all reached success |
| `curl http://127.0.0.1:12959/` and `/api/runs?limit=5` | success | Frontend served; latest run list includes WES smoke run |

### Tests

Remote-only evidence from `fengxian`:

- `WES_20260705_162041_2507AF` initial DAG run `manual__WES_20260705_162041_2507AF` ended `success`.
- Resume DAG run `manual__WES_20260705_162041_2507AF__resume__20260705T162142Z` ended `success`.
- Rerun DAG run `manual__WES_20260705_162041_2507AF__rerun_rule__20260705T162151Z` ended `success`.
- `/api/runs/WES_20260705_162041_2507AF/rules` returned 7 rule rows.
- `shared/runs/WES_20260705_162041_2507AF/logs/events/snakemake_events.jsonl` has 28 lines.
- `shared/runs/WES_20260705_162041_2507AF/logs/snakemake.command.txt` contains `--forcerun fastp` and no `--forceall`.

### Not run / why

- No real qsub/qstat was run; `fengxian` still lacks real qsub and this task is mock-only.
- No QC parser/panel, MailHog notification, NIPT DAG, `rerun_failed`, or `clone_new` was implemented.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was used.

### Current git status

Work is on branch `codex/fullstack/T044-T056-wes-rerun`. Runtime validation ran on the `fengxian` mirror at commit `25c0633`, followed by this docs/status update.

### Risks

- WES remains mock-only and fixed to `S001/S002`; real WES inputs and real qsub require separate planning.
- The latest reanalysis action overwrites `analysis_run.dag_run_id` with the newest DAG run id; prior actions remain in `run_action`.
- Frontend reanalysis is intentionally hidden while a WES run is `submitted/running/queued`.

### Open questions

- Whether `rerun_failed` should be implemented as a real failed-rule selector after a controlled WES failure smoke exists.

### Next recommended task

Proceed to T060/T054: parse WES mock QC/final-summary data into `qc_metric` and add the frontend QC panel. T034/T063 MailHog notification is the other good next slice.

### Rollback notes

- Revert repository changes with normal `git revert`.
- If runtime cleanup is needed, remove only generated WES mock run directories under `shared/runs/WES_*` after path verification.
- Stop services only with `docker compose -f docker-compose.yaml down`; do not use `down -v` or prune commands.

## 2026-07-05 00:52 - Codex - T030/T031 bio_wes_qsub Airflow DAG skeleton

### Goal

Add the WES mock project-level Airflow DAG `bio_wes_qsub`, without FastAPI WES submission, frontend WES pages, QC/reanalysis, or real qsub. The DAG should run the already validated WES mock Snakemake workflow through `profiles/qsub` and the mock qsub wrapper inside the Airflow worker.

### Completed

- Added `dags/common` helpers for shared-root validation, directory creation, subprocess stdout/stderr capture, and small summaries.
- Added `dags/bio_wes_qsub.py` and `dags/wes_qsub_runner.py`.
- Added project Airflow image `airflow-demo/airflow:0.1.0`, based on `apache/airflow:2.9.3-python3.11`, with Snakemake 9.23.1 and `snakemake-executor-plugin-cluster-generic==1.0.9` isolated in `/opt/airflow/snakemake-venv`.
- Updated Compose Airflow services to use the project image and mount `./pipelines`, `./profiles`, and `./shared`.
- Fixed two remote runtime blockers found during smoke:
  - Airflow worker initially ran as uid `50000` and could not create new `shared/runs/WES_*` workdirs; `AIRFLOW_UID` now defaults to `1005` for `fengxian`, and runbook says to set it to `id -u` on new servers.
  - Snakemake tried to write `/home/airflow/.cache/snakemake`; `run_wes_qsub` now sets `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`.
- Verified `bio_wes_qsub` smoke success on `fengxian`: `manual__WES_AIRFLOW_20260705_004506`.
- Updated DAG, qsub, runbook, acceptance, server, task, current-state, handoff, and manifest docs.

### Changed files

- `.env.example`
- `airflow_image/Dockerfile`
- `airflow_image/pip.conf`
- `airflow_image/requirements.txt`
- `dags/common/__init__.py`
- `dags/common/paths.py`
- `dags/common/subprocess_utils.py`
- `dags/bio_wes_qsub.py`
- `dags/wes_qsub_runner.py`
- `dags/tests/test_bio_wes_qsub_dag.py`
- `dags/tests/test_wes_qsub_runner.py`
- `docker-compose.yaml`
- `pipelines/tests/test_wes_mock_contract.py`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote targeted UID contract test after tests-only commit | failed as expected | Compose still rendered `AIRFLOW_UID:-50000` |
| remote targeted cache test after tests-only commit | failed as expected | `XDG_CACHE_HOME` missing from Snakemake subprocess env |
| `docker compose -f docker-compose.yaml config --quiet` | success | Rendered Airflow `user: "1005:0"` after `.env` update |
| `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate airflow-api-server airflow-scheduler airflow-worker` | success | Applied new Airflow uid; no volumes deleted |
| `docker compose -f docker-compose.yaml exec -T airflow-worker id` | success | `uid=1005(default) gid=0(root)` |
| `docker compose -f docker-compose.yaml build airflow-worker airflow-scheduler airflow-api-server` | success | Cached build, image `airflow-demo/airflow:0.1.0` |
| `docker run --rm airflow-demo/airflow:0.1.0 airflow version` | success | `2.9.3` |
| `docker run --rm --entrypoint snakemake airflow-demo/airflow:0.1.0 --version` | success | `9.23.1` |
| `docker run --rm --entrypoint snakemake airflow-demo/airflow:0.1.0 --help \| grep -F cluster-generic` | success | `cluster-generic` executor visible |
| `python -m unittest pipelines.tests.test_wes_mock_contract -v` in backend image | success | 6 tests OK |
| `/usr/local/bin/python -m unittest dags.tests.test_bio_wes_qsub_dag dags.tests.test_wes_qsub_runner -v` in Airflow image | success | 8 tests OK |
| `airflow dags list-import-errors` | success | `No data found` |
| trigger `bio_wes_qsub` with `WES_AIRFLOW_20260705_004506` | success | DAG run ended `success` |

### Tests

Remote-only evidence from `fengxian`:

- `manual__WES_AIRFLOW_20260705_004506` ended Airflow `success`.
- `shared/runs/WES_AIRFLOW_20260705_004506/reports/final_summary.tsv` contains `S001` and `S002` `mock_success`.
- `shared/runs/WES_AIRFLOW_20260705_004506/logs/events/snakemake_events.jsonl` has 14 lines with `qsub_submitted` and `qsub_success`.
- `shared/runs/WES_AIRFLOW_20260705_004506/logs/qsub/*.o/e` exists.
- `collect_wes_artifacts` task log returned XCom summary `event_count=14`, `qsub_log_count=14`.

### Not run / why

- No FastAPI WES create/submit endpoint was added; out of scope for T031.
- No frontend WES page, QC parser, reanalysis UI, MailHog notification, NIPT DAG, or real qsub was run.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was used.

### Current git status

Work is on branch `codex/airflow/T031-wes-qsub-dag`. Runtime validation ran on the `fengxian` mirror at commit `ec5c9e2`, followed by this docs/status update.

### Risks

- `.env` on any new Linux server must set `AIRFLOW_UID=$(id -u)` for the deploy user; otherwise Airflow-only DAGs may fail to create bind-mounted run directories.
- The Airflow image puts `/opt/airflow/snakemake-venv/bin` first on `PATH`; use `/usr/local/bin/python` when running tests that require the base Airflow Python packages.
- WES remains mock-only and does not represent production WES parameters or real cluster scheduling.

### Open questions

- Whether WES should next be exposed through FastAPI/frontend, or whether QC/reanalysis is higher demo priority.

### Next recommended task

Proceed to T044/T056 for resume/rerun behavior on top of `bio_wes_qsub`, or T060/T054 for mock QC parsing and the frontend QC panel.

### Rollback notes

- Revert repository changes with normal `git revert`.
- If runtime cleanup is needed, remove only generated WES mock run directories under `shared/runs/WES_AIRFLOW_*` after path verification.
- Stop services only with `docker compose -f docker-compose.yaml down`; do not use `down -v` or prune commands.

## 2026-07-04 23:11 - Codex - T042 Snakemake cluster-generic profile runtime

### Goal

Unblock T042 by adding an isolated Dockerized Snakemake runtime that can execute the WES mock workflow through `profiles/qsub` and the `cluster-generic` executor, without modifying `/biosoftware/miniconda/envs/*` or calling real qsub.

### Completed

- Added `snakemake_runner/` with `python:3.12-slim`, `snakemake==9.23.1`, `snakemake-executor-plugin-cluster-generic==1.0.9`, and the repo pip mirror config.
- Added run-only Compose service `snakemake-runner` with image `airflow-demo/snakemake-runner:0.1.0`, no exposed ports, read-only repo mount, shared run output mount, and writable tmpfs for `/app/.snakemake`.
- Updated `profiles/qsub/config.yaml` to use `${{AIRFLOW_DEMO_QSUB_PYTHON:-python}} pipelines/common/qsub_submit.py` so Snakemake formatting preserves shell env expansion.
- Added contract tests for the runner Dockerfile, pinned dependencies, Compose service, and mock-safe profile submit command.
- Verified on `fengxian` that `--profile profiles/qsub` drives the mock qsub wrapper through `cluster-generic` and produces final summary, qsub stdout/stderr, and JSONL events.
- Updated qsub, runbook, acceptance, server, task, current-state, handoff, and manifest docs.

### Changed files

- `snakemake_runner/Dockerfile`
- `snakemake_runner/requirements.txt`
- `snakemake_runner/pip.conf`
- `docker-compose.yaml`
- `.env.example`
- `profiles/qsub/config.yaml`
- `pipelines/tests/test_wes_mock_contract.py`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote temp contract tests after tests-only patch | failed as expected | Missing runner Dockerfile/service and old profile Python command |
| remote temp `python -m unittest pipelines.tests.test_wes_mock_contract -v` after implementation | success | 4 tests OK |
| remote profile runtime before env escape fix | failed as expected | Snakemake formatted `${AIRFLOW_DEMO_QSUB_PYTHON:-python}` as an unknown variable |
| remote temp regression test for escaped env expansion | failed as expected | Confirmed profile needed `${{AIRFLOW_DEMO_QSUB_PYTHON:-python}}` |
| remote temp regression test after fix | success | Escaped env expansion contract passed |
| official mirror `git pull --ff-only` | success | `/home/jiucheng/project/airflow-demo` fast-forwarded to `cd22c90` |
| official mirror `docker compose -f docker-compose.yaml config --quiet` | success | Compose rendered with `snakemake-runner` |
| official mirror `docker compose -f docker-compose.yaml build snakemake-runner` | success | Built `airflow-demo/snakemake-runner:0.1.0` |
| official mirror `docker compose -f docker-compose.yaml run --rm snakemake-runner snakemake --version` | success | Returned `9.23.1` |
| official mirror `snakemake --help` inside runner | success | `cluster-generic` executor and `--cluster-generic-submit-cmd` visible |
| official mirror plugin import check | success | Imported `snakemake_executor_plugin_cluster_generic` |
| official mirror Dockerized contract tests | success | `python -m unittest pipelines.tests.test_wes_mock_contract -v`, 4 tests OK |
| official mirror WES profile runtime smoke | success | `WES_PROFILE_20260704_230713` completed 8 WES mock jobs through `--profile profiles/qsub` |

### Tests

Remote-only evidence from `fengxian`:

- Runner build succeeded and produced image `airflow-demo/snakemake-runner:0.1.0`.
- Snakemake version inside runner: `9.23.1`.
- `cluster-generic` executor and settings are visible inside the runner.
- WES profile runtime smoke:
  - `analysis_id=WES_PROFILE_20260704_230713`
  - job stats: `all=1`, `fastp=2`, `bwa_mem=2`, `markdup=2`, `final_summary=1`, `total=8`
  - `shared/runs/WES_PROFILE_20260704_230713/reports/final_summary.tsv` exists with `S001` and `S002` `mock_success`
  - `shared/runs/WES_PROFILE_20260704_230713/logs/qsub/*.o/e` exists
  - `shared/runs/WES_PROFILE_20260704_230713/logs/events/snakemake_events.jsonl` has 14 lines and contains `qsub_submitted`/`qsub_success`

### Not run / why

- Optional DB smoke for `backend_event_url=http://backend:8000/api/events/snakemake` was not repeated in this task; T041 already verified backend POST and `/api/runs/{analysis_id}/rules`, while T042 scope was `cluster-generic` profile runtime.
- Real qsub was not run because `qsub/qstat` remain unavailable on `fengxian` and the demo is intentionally in mock mode.
- No `bio_wes_qsub` DAG, QC parser, frontend QC, or reanalysis UI work was done.

### Current git status

Work is on branch `codex/airflow/T086-pgta-airflow-logger`. Implementation commits `83fa789` and `cd22c90` were pushed and verified on the `fengxian` mirror; this handoff entry records the follow-up docs/status evidence update.

### Risks

- `snakemake-runner` is the supported runtime for this profile on `fengxian`; host Snakemake environments still do not contain `snakemake-executor-plugin-cluster-generic`.
- Generated WES smoke directories remain under `shared/runs/WES_PROFILE_*` on the server as ignored runtime evidence.
- The WES workflow remains mock-only and does not represent production WES parameters or real qsub scheduling.

### Open questions

- None for T042. Real qsub enablement should be separately planned after a server with `qsub/qstat` is available and authorized.

### Next recommended task

Proceed to T031: add a `bio_wes_qsub` Airflow DAG skeleton that invokes the verified `snakemake-runner` + `profiles/qsub` path for WES mock runs.

### Rollback notes

- Revert repository changes with normal `git revert`.
- If cleanup is needed, remove only generated WES mock run directories under `shared/runs/WES_PROFILE_*` after path verification.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-04 18:05 - Codex - T040/T041/T042 WES mock qsub observability

### Goal

Build the first WES mock Snakemake/qsub observability slice: a tiny WES Snakefile, a mock qsub submit wrapper that records qsub job id/stdout/stderr/events, and a qsub profile contract. Do not call real qsub, do not use real WES data, and keep runtime validation on `ssh fengxian`.

### Completed

- Added `pipelines/wes/workflow/Snakefile` with a two-sample mock chain: `fastp -> bwa_mem -> markdup -> final_summary`.
- Added tiny mock inputs and config under `pipelines/wes/`.
- Added `pipelines/common/qsub_submit.py` with `AIRFLOW_DEMO_QSUB_MODE=mock`.
- Mock wrapper reads Snakemake jobscript properties, creates stable `MOCK-*` qsub job ids, writes qsub stdout/stderr, writes JSONL events, optionally POSTs backend events, and records final success/failed status.
- Added `profiles/qsub/config.yaml` with `jobs=2`, `rerun-incomplete=true`, and explicit Snakemake env Python.
- Documented that `fengxian` currently lacks both `qsub/qstat` and `snakemake-executor-plugin-cluster-generic`; therefore direct wrapper smoke passes, while full `--profile profiles/qsub` runtime is blocked.

### Changed files

- `pipelines/common/qsub_submit.py`
- `pipelines/wes/workflow/Snakefile`
- `pipelines/wes/config/mock_config.yaml`
- `pipelines/wes/mock_data/S001.input.txt`
- `pipelines/wes/mock_data/S002.input.txt`
- `profiles/qsub/config.yaml`
- `pipelines/tests/test_qsub_submit.py`
- `pipelines/tests/test_wes_mock_contract.py`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote temp tests after tests-only patch | failed as expected | Missing `pipelines.common`, WES Snakefile, and qsub profile |
| remote temp `python -m unittest pipelines.tests.test_qsub_submit pipelines.tests.test_wes_mock_contract` | success | 5 tests OK |
| remote temp WES Snakemake dry-run | success | Snakemake 8.5.4 showed 8 jobs across all/fastp/bwa_mem/markdup/final_summary |
| remote temp direct mock wrapper smoke | success | Generated `MOCK-WES_20260704_DIRECT-12-bwa_mem-S001`, qsub stdout/stderr, result file, and submitted/success JSONL events |
| `snakemake --profile profiles/qsub` in remote temp | blocked | Snakemake executor choices are local/dryrun/touch; `cluster-generic` plugin missing |
| qsub/qstat probe on `fengxian` | not found | `command -v qsub` and `command -v qstat` returned empty |
| official mirror `git pull --ff-only` | success | `/home/jiucheng/project/airflow-demo` synced to implementation commit `a7f03f3` before runtime smoke |
| official mirror `docker compose -f docker-compose.yaml config --quiet` | success | Compose contract still renders |
| official mirror `docker run --rm airflow-demo/backend:0.1.0 pytest -q` | success | 35 backend tests passed |
| official mirror Dockerized unittest for `pipelines.tests.*` | success | 5 WES/qsub contract tests OK |
| official mirror WES Snakemake dry-run | success | Job stats: all=1, fastp=2, bwa_mem=2, markdup=2, final_summary=1, total=8 |
| official mirror direct wrapper + backend POST | success | `WES_20260704_180650_MOCK` generated `MOCK-WES_20260704_180650_MOCK-12-bwa_mem-S001` |
| `GET /api/runs/WES_20260704_180650_MOCK/rules` | success | Returned `bwa_mem/S001=success`, qsub job id, stdout/stderr paths, and `return_code=0` |

### Tests

Remote-only evidence from `fengxian`:

- Unit/contract tests: `Ran 5 tests OK`.
- Backend image tests: `35 passed`.
- WES mock dry-run on official mirror: passed with 8 jobs.
- Direct mock qsub wrapper on official mirror with backend event POST: passed and wrote:
  - `shared/runs/WES_20260704_180650_MOCK/logs/qsub/bwa_mem.S001.o`
  - `shared/runs/WES_20260704_180650_MOCK/logs/qsub/bwa_mem.S001.e`
  - `shared/runs/WES_20260704_180650_MOCK/logs/events/snakemake_events.jsonl`
  - `shared/runs/WES_20260704_180650_MOCK/mock/result.txt`
- Backend rule query: `/api/runs/WES_20260704_180650_MOCK/rules` returned `bwa_mem/S001=success` with `qsub_jobid`, stdout/stderr paths, and `return_code=0`.

### Not run / why

- Full `--profile profiles/qsub` execution did not pass because neither Snakemake env has `snakemake-executor-plugin-cluster-generic`.
- Real qsub was not run because `qsub/qstat` are absent on `fengxian`.

### Current git status

Work is on branch `codex/airflow/T086-pgta-airflow-logger`. Implementation commit `a7f03f3` was pushed and validated on the `fengxian` mirror; this handoff entry includes the follow-up docs/status evidence update.

### Risks

- T042 should remain blocked until the cluster-generic executor plugin is installed in an isolated environment or added to a runtime image.
- The mock wrapper uses the Snakemake env Python explicitly; running it with system Python 3.6 fails because the script uses modern Python syntax.
- The WES workflow is mock-only and does not represent production WES parameters.

### Open questions

- Whether to unblock T042 by installing the executor plugin in a dedicated container image or by creating a separate Snakemake qsub runner environment on `fengxian`.

### Next recommended task

Unblock T042 by adding `snakemake-executor-plugin-cluster-generic` in an isolated runtime, then run `--profile profiles/qsub` end-to-end. After that, proceed to T031 `bio_wes_qsub` DAG skeleton.

### Rollback notes

- Revert repository changes with normal `git revert`.
- Remove only generated WES mock run directories under `shared/runs/WES_*` if cleanup is needed.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-04 01:18 - Codex - T045/T084 PGT-A dryrun and failure smoke

### Goal

Extend the existing PGT-A create -> submit -> Airflow -> sync chain with two controlled targets: `dryrun_cnv` for Snakemake CNV DAG parsing and `invalid_target` for failure/error-summary smoke. Keep PGT-A source/data mounts read-only, do not run real CNV/baseline_qc/qsub, and keep runtime validation on `ssh fengxian`.

### Completed

- Added controlled backend target support for `metadata`, `dryrun_cnv`, and `invalid_target`.
- Extended `bio_pgta` from metadata-only to target-aware tasks: `validate_request -> prepare_pgta_config -> run_pgta_target -> collect_pgta_artifact`.
- Added frontend target selector and submit support for created `dryrun_cnv` / `invalid_target` runs.
- Fixed `dryrun_cnv` config to use existing read-only WisecondorX XX/XY/gender references under `/data/project/CNV/PGT-A/refactor_validation_20260419/results_build_ref_v2_mask_only/reference`.
- Added dry-run Snakemake flags `--ignore-incomplete --rerun-triggers mtime` to avoid historical incomplete metadata interfering with DAG parsing.
- Updated API/DAG/frontend/runbook/testing/PGT-A plan docs and task/current-state/handoff docs.

### Changed files

- `backend/app/run_service.py`
- `backend/app/diagnostics_service.py`
- `backend/tests/test_run_creation.py`
- `backend/tests/test_run_submit.py`
- `dags/bio_pgta.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_bio_pgta_dag.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote temp backend targeted tests after tests-only patch | failed as expected | metadata-only validation rejected `dryrun_cnv` and `invalid_target` |
| remote temp DAG tests after tests-only patch | failed as expected | target-aware runner/tasks not implemented yet |
| remote temp frontend test after tests-only patch | failed as expected | target selector/submit behavior missing |
| remote temp backend targeted tests after implementation | success | 10 tests passed |
| remote temp DAG tests after implementation | success | 11 tests OK |
| remote temp frontend Docker test after implementation | success | Vitest 7 passed |
| `git pull --ff-only` on `fengxian` | success | Mirror fast-forwarded to `f90b09c` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose still valid |
| `docker run --rm airflow-demo/backend:0.1.0 pytest -q` on `fengxian` | success | 35 tests passed |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | Dockerized frontend test target passed |
| DAG unittest in Airflow image on `fengxian` | success | 11 tests OK |
| Airflow import check | success | `airflow dags list-import-errors` returned `No data found` |
| `docker compose restart airflow-api-server airflow-scheduler airflow-worker` | success | Safe restart only, no volume deletion |
| `dryrun_cnv` API smoke | success | `PGTA_20260703_170917_20E8F2`, Airflow/backend `success`, stdout recorded 7 dry-run jobs |
| `invalid_target` API smoke | success | `PGTA_20260703_170957_3DDEC3`, Airflow/backend `failed` as expected, non-null `error_summary` |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Backend suite: `35 passed`.
- Frontend Dockerized test target: passed.
- DAG tests: `Ran 11 tests OK`.
- `dryrun_cnv` smoke:
  - `analysis_id=PGTA_20260703_170917_20E8F2`
  - `dag_run_id=manual__PGTA_20260703_170917_20E8F2`
  - final status `success`
  - stdout log size 12677 bytes, stderr log size 89 bytes
  - artifact API returned `snakemake_stdout`, `snakemake_stderr`, `pgta_config_yaml`, `pgta_run_config`, `pgta_metadata_config`
- `invalid_target` smoke:
  - `analysis_id=PGTA_20260703_170957_3DDEC3`
  - `dag_run_id=manual__PGTA_20260703_170957_3DDEC3`
  - final status `failed`
  - `error_summary` is non-null and includes stderr path plus last error lines

### Not run / why

- No real CNV, baseline_qc, qsub, or QC parsing was run; out of scope for T045/T084.
- No custom Airflow Web plugin was added; existing FastAPI/frontend logs/artifacts/status APIs cover this smoke.
- No Docker volumes were deleted and no prune commands were run.

### Current git status

Implementation and smoke fix are on branch `codex/airflow/T086-pgta-airflow-logger`; verified code commit is `f90b09c`, followed by this docs/state update.

### Risks

- `invalid_target` currently proves the controlled failure/error-summary path. Snakemake reports the sentinel target in stderr, but the exact traceback shape is a CLI parsing detail and should not be treated as a production failure taxonomy.
- `dryrun_cnv` depends on the existing read-only reference path on `fengxian`; BS10610 migration must parameterize/check this path in Level 0 preflight.
- Services are left running for user review.

### Open questions

- Whether to parameterize the PGT-A demo reference root into `.env` before BS10610 migration, or keep it as a fengxian-only smoke assumption until the migration batch.

### Next recommended task

Run T041/T042 next for qsub submit wrapper/profile and qsub job-id observability, or T054/T056 if the next demo priority is QC/reanalysis UI.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`; do not use `down -v`.
- Revert repository changes with normal `git revert`.
- Do not use `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 23:48 - Codex - T051 PGT-A frontend submission flow

### Goal

Add the first frontend submission path for PGT-A: scan an allowlisted server FASTQ root, select samples, create a `created` run through FastAPI, then submit that run to Airflow from the detail toolbar. Keep the existing two-step create/submit model; do not add login, QC, dry-run/CNV, qsub, or new backend contracts.

### Completed

- Added `New PGT-A Run` panel to the existing single-page React workspace.
- Added form fields for project name, rawdata root, max samples, fixed `target=metadata`, optional email, and note.
- Added scan/create frontend API client functions for `POST /api/input/scan` and JSON `POST /api/runs`.
- Added selectable FASTQ candidate table and truncated-scan warning.
- Added `Submit to Airflow` action for `status=created` + `target=metadata`, using `POST /api/runs/{analysis_id}/actions/submit`.
- Preserved run list/detail, samples, rules, logs, artifacts, and sync UI.
- Updated frontend spec, task table, current state, handoff, and manifest docs.

### Changed files

- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/api.ts`
- `frontend/src/styles.css`
- `docs/06_FRONTEND_SPEC.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| remote temp `docker build --target test -f frontend/Dockerfile frontend` after adding tests only | failed as expected | 3 new tests failed because rawdata/project form and submit button did not exist |
| remote temp `docker build --target test -f frontend/Dockerfile frontend` after implementation | success | Vitest `5 passed` |
| `git diff --check` | success | Local non-runtime check only |
| `git pull --ff-only` on `fengxian` | success | Mirror fast-forwarded to T051 commits |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose still valid |
| `docker compose -f docker-compose.yaml build frontend` on `fengxian` | failed once, then success | First failure was TypeScript test mock inference; fixed in `f5dae66`; production build then passed |
| `docker build --target test -f frontend/Dockerfile frontend` on `fengxian` | success | Vitest `5 passed` |
| `docker compose -f docker-compose.yaml up -d postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker` | success | Frontend recreated with new image; services left running for user review |
| frontend/backend health probes | success | `http://127.0.0.1:12959/` returned React HTML; backend `/api/health` returned ok |
| API T051 smoke | success | Created/submitted `PGTA_20260703_154341_408A29`; sync ended `success`; metadata artifact/log readable |
| run list probe | success | `/api/runs?pipeline=pgta` contains `PGTA_20260703_154341_408A29`; total was 6 |
| final direct frontend test-stage run | success | `docker run --rm b1ffb26d16f7 npm test -- --run`; Vitest `5 passed` |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Frontend production Docker build passed.
- Frontend Dockerized Vitest target passed: `5 passed`; final direct test-stage run also passed `5 passed`.
- Real PGT-A metadata create/submit smoke passed:
  - `analysis_id=PGTA_20260703_154341_408A29`
  - `dag_run_id=manual__PGTA_20260703_154341_408A29`
  - `sync-airflow` status `success`
  - artifact API returned 5 items
  - metadata log tail returned 3 lines
- Frontend page is available at `http://fengxian:12959/`.

### Not run / why

- No browser automation screenshot was run; React behavior is covered by Dockerized Vitest and remote HTTP/API smoke.
- No login was implemented; out of scope.
- No dry-run/CNV/baseline_qc or invalid target failure smoke was run; T045/T084 remain next.
- No qsub wrapper/profile or qsub job-id events were implemented; T041/T042 remain pending.
- No QC panel or reanalysis UI was implemented; T054/T056 remain pending.

### Current git status

T051 code was verified on branch `codex/airflow/T086-pgta-airflow-logger` at `f5dae66`; the final docs/state commit records the smoke evidence.

### Risks

- Services are intentionally left running for user review; stop with `docker compose -f docker-compose.yaml down` only when done.
- The new submit UI triggers real `bio_pgta` metadata runs; it is still limited to `target=metadata`.
- The UI still uses demo-wide CORS and no auth; production-like access control remains future work.

### Open questions

- Whether the next frontend increment should add route-level navigation, or keep the single-page workspace until QC/reanalysis pages are ready.

### Next recommended task

Run T045/T084 next for PGT-A dry-run and invalid-target failure smoke, or T041/T042 if qsub job-id observability is the priority.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`; do not use `down -v`.
- Revert repository changes with normal `git revert`.
- Do not use `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 16:19 - Codex - T050/T057 frontend run detail v1

### Goal

Safely stop the running demo services on `fengxian`, then replace the nginx placeholder with a minimal React frontend for PGT-A run list/detail. The v1 UI must read existing runs, samples, logs, artifacts, Snakemake rule status, and provide a manual Airflow sync button. Do not implement login, sample creation, new DAG triggers, QC panels, or reanalysis.

### Completed

- Stopped current `fengxian` demo services with `docker compose -f docker-compose.yaml down`; `docker compose ps` was empty.
- Added Vite React + TypeScript frontend under `frontend/`.
- Replaced compose `frontend` placeholder with project image `airflow-demo/frontend:0.1.0`, still published on host port `12959`.
- Added frontend run list/detail workspace consuming existing backend APIs: runs, detail, samples, rules, logs, artifacts, and sync-airflow.
- Added backend CORS support via `BACKEND_CORS_ORIGINS`, defaulting to `*` for the demo.
- Added remote Dockerized frontend tests and a backend CORS test.
- Updated frontend, engineering, runbook, task, current state, handoff, and manifest docs.

### Changed files

- `.env.example`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/tests/test_cors.py`
- `docker-compose.yaml`
- `frontend/*`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml down` on `fengxian` | success | Safe stop only; no `down -v` or prune |
| `docker compose -f docker-compose.yaml build backend` before CORS implementation | success | Rebuilt red-test backend image |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_cors.py` before implementation | failed as expected | CORS preflight returned 405 |
| `docker build --target test -f frontend/Dockerfile frontend` before implementation | failed as expected | Missing `src/App.tsx` |
| `docker compose -f docker-compose.yaml config --quiet` | success | Compose rendered frontend build image and ports |
| `docker compose -f docker-compose.yaml build backend frontend` | success | Built `airflow-demo/backend:0.1.0` and `airflow-demo/frontend:0.1.0` |
| `docker build --target test -f frontend/Dockerfile frontend` | success | Vitest `2 passed` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_cors.py` | success | `1 passed` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` | success | `31 passed` |
| service startup on `fengxian` | success | Started postgres, redis, backend, frontend, airflow-api-server, airflow-scheduler, airflow-worker |
| `curl http://127.0.0.1:12959/` | success | Returned React HTML |
| `GET /api/runs?pipeline=pgta` | success | Returned existing PGT-A runs |
| `GET /api/runs/PGTA_20260703_054712_501D8B/rules` | success | Returned `all=success`, `collect_run_metadata=success` |
| metadata log/artifact/sample curls | success | Returned data for `PGTA_20260703_054712_501D8B` |
| Airflow `/health` | success | Metadatabase and scheduler healthy |
| CORS OPTIONS probe | success | HTTP 200, `access-control-allow-origin: *` |
| final `docker compose -f docker-compose.yaml down` | success | Safe stop only; `docker compose ps` empty |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Backend test suite passed: `31 passed`.
- Frontend Dockerized Vitest target passed: `2 passed`.
- Frontend production Docker build passed.
- React page served at `http://127.0.0.1:12959/`.
- Existing run `PGTA_20260703_054712_501D8B` exposed samples, metadata logs, artifacts, and rule statuses through backend APIs.

### Not run / why

- No frontend login was implemented; out of scope for v1.
- No PGT-A scan/create form was implemented; T051 remains next.
- No new PGT-A DAG run, dry-run target, CNV, baseline_qc, or invalid target smoke was run; T045/T084 remain pending.
- No QC panel or reanalysis UI was implemented; T054/T056 remain pending.
- No browser screenshot automation was run; component tests plus served HTML/API smoke were used.

### Current git status

Implementation is on branch `codex/airflow/T086-pgta-airflow-logger`; runtime smoke passed on `fengxian` at commit `403fa68`, followed by this docs/state update batch.

### Risks

- Frontend API base currently points browsers to `http://<host>:8000/api`; if a reverse proxy is later added, set `window.__AIRFLOW_DEMO_CONFIG__.apiBaseUrl` or `VITE_API_BASE_URL`.
- CORS default is `*` for demo ergonomics; tighten it before production-like deployment.
- `PGTA_20260703_054712_501D8B` has rule success rows from the Airflow-only event smoke, while the business run status remains `created` because that smoke did not call `sync-airflow`.

### Open questions

- Whether T051 should live in the same single-page workspace or become a separate `/submit` route once routing is introduced.

### Next recommended task

Run T051 next: add PGT-A server-path scan/create form using `POST /api/input/scan` and JSON `POST /api/runs`, then keep T045/T084 dry-run/failure smoke separate.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 13:49 - Codex - T026/T043 Snakemake event receiver and PGT-A logger POST

### Goal

Implement rule/job event ingestion for Snakemake logger events: FastAPI receives `/api/events/snakemake`, upserts biodemo `snakemake_rule_event`, exposes `/api/runs/{analysis_id}/rules`, and PGT-A Snakemake 9 logger optionally POSTs to backend while retaining JSONL fallback.

### Completed

- Added backend event receiver `POST /api/events/snakemake` with structured `RUN_NOT_FOUND` and validation errors.
- Added `GET /api/runs/{analysis_id}/rules` for frontend-ready rule/job status.
- Added idempotent upsert by `analysis_id/rule/sample_id/snakemake_jobid`; later success/failed events update the existing row.
- Added PGT-A Snakemake 9 logger backend POST via `backend_event_url`, with JSONL fallback on POST failure.
- Fixed logger job context backfill so Snakemake `job_finished/job_error` events without rule fields inherit rule/sample from earlier `job_info`.
- Added Airflow-only DAG conf passthrough for `backend_event_url`.
- Updated API, DB, DAG, Snakemake, logging, runbook, PGT-A plan, task, current state, and manifest docs.

### Changed files

- `backend/app/main.py`
- `backend/app/rule_event_service.py`
- `backend/tests/test_snakemake_events_api.py`
- `dags/pgta_airflow_runner.py`
- `dags/snakemake_logger_plugin_airflow_demo/__init__.py`
- `dags/tests/test_pgta_airflow_runner.py`
- `dags/tests/test_snakemake_logger_plugin.py`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml build backend` on `fengxian` | success | Rebuilt backend image with event tests/code |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_snakemake_events_api.py` before implementation | failed as expected | Missing endpoints returned 404 |
| Airflow runner unittest before implementation | failed as expected | `backend_event_url` not preserved/passed |
| Snakemake 9 plugin unittest before implementation | failed as expected | backend POST not called and fallback marker absent |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_snakemake_events_api.py` | success | `4 passed` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` | success | `30 passed` |
| Snakemake 9 plugin unittest after POST implementation | success | `4 tests OK` before context regression was added |
| T026/T043 first real smoke | partial | `PGTA_20260703_052742_C3A2F5` DAG success, but DB only got `info` rows; exposed missing job context backfill |
| Snakemake 9 plugin context regression before fix | failed as expected | `job_finished` without rule did not POST |
| Snakemake 9 plugin unittest after context fix | success | `5 tests OK` |
| Airflow unittest discover after context fix | success | `18 tests OK`, `5 skipped` in Airflow Python because Snakemake 9 interface is absent there |
| T026/T043 second real smoke | success | `PGTA_20260703_054712_501D8B` / `manual__PGTA_20260703_054712_501D8B_events` ended Airflow `success` |
| `GET /api/runs/PGTA_20260703_054712_501D8B/rules` | success | Returned `all=success`, `collect_run_metadata=success` |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; no `down -v` or prune |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Backend event API tests passed: `4 passed`.
- Full backend test suite passed: `30 passed`.
- Snakemake 9 logger plugin tests passed under `/biosoftware/miniconda/envs/snakemake9_env/bin/python`: `5 tests OK`.
- Airflow DAG/runner tests passed in Airflow Python: `18 tests OK`, `5 skipped`.
- Real PGT-A Airflow-only metadata event smoke passed:
  - `analysis_id=PGTA_20260703_054712_501D8B`
  - `dag_run_id=manual__PGTA_20260703_054712_501D8B_events`
  - Airflow state `success`
  - `run_metadata.tsv`: 11 lines
  - `snakemake_events.jsonl`: 22 lines
  - `snakemake_rule_summary.tsv`: 29 lines
  - rules API returned two success rows.

### Not run / why

- No frontend was implemented or tested; T057 remains next for visible run detail/rule table.
- No PGT-A dry-run/CNV/baseline_qc target was run; T045 remains pending.
- No qsub wrapper/profile was implemented; qsub job id and qsub stdout/stderr fields remain pending T041/T042.
- No DB migration was added; existing `snakemake_rule_event` schema was sufficient.

### Current git status

Implementation is on branch `codex/airflow/T086-pgta-airflow-logger`; code smoke passed on `fengxian` at commit `b917961`, followed by docs/state updates in this handoff batch.

### Risks

- Snakemake 9 emits some useful generic workflow/progress events without rule; backend intentionally ignores those and keeps them only in JSONL/Airflow XCom.
- `start_time` may remain null for some PGT-A rows because Snakemake `job_started` events do not always carry jobid/rule. Terminal success is still captured through `job_info -> job_finished` context backfill.
- `bio_pgta_airflow` is still manifest-only and does not replace the backend-triggered `bio_pgta` submit path.

### Open questions

- Whether `/api/runs/{analysis_id}/actions/submit` should eventually support `bio_pgta_airflow` for backend-created runs, or keep it as a diagnostic Airflow-only DAG.

### Next recommended task

Run T057 next: build PGT-A run detail UI that consumes run detail, samples, logs, artifacts, sync-airflow, and the new rules API. T045 dry-run and T041/T042 qsub wrapper remain separate follow-ups.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 07:56 - Codex - T036 PGT-A Airflow-only Snakemake 9 logger DAG

### Goal

Create an independent PGT-A Airflow-only metadata DAG using Snakemake 9.23.1 and a repo-local logger plugin, without changing the existing backend-triggered `bio_pgta` path or modifying PGT-A production code/environments.

### Completed

- Added DAG `bio_pgta_airflow` with `validate_request -> prepare_pgta_config -> run_snakemake9_with_logger -> collect_snakemake_events -> collect_metadata_artifact`.
- Added `pgta_airflow_runner.py` for manifest-only Airflow conf validation, PGT-A config generation, Snakemake 9 invocation, event JSONL parsing, summary TSV generation, and Airflow log/XCom summary.
- Added repo-local Snakemake logger plugin package `snakemake_logger_plugin_airflow_demo`.
- Added `.airflowignore` so Airflow does not parse DAG test files and create duplicate DAG IDs.
- Added tests for the new DAG, runner, and Snakemake 9 logger plugin.
- Added env knobs `PGTA_SNAKEMAKE9_BIN` and `AIRFLOW_DAGS_ROOT`.
- Updated engineering, DAG, Snakemake, logging, runbook, PGT-A plan, task, state, and manifest docs.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `dags/.airflowignore`
- `dags/bio_pgta_airflow.py`
- `dags/pgta_airflow_runner.py`
- `dags/snakemake_logger_plugin_airflow_demo/__init__.py`
- `dags/tests/test_bio_pgta_airflow_dag.py`
- `dags/tests/test_pgta_airflow_runner.py`
- `dags/tests/test_snakemake_logger_plugin.py`
- `SERVER_INFO.md`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| Airflow unittest before implementation on `fengxian` | failed as expected | Missing `bio_pgta_airflow` and `pgta_airflow_runner` |
| Snakemake 9 plugin test before implementation on `fengxian` | failed as expected | Missing `snakemake_logger_plugin_airflow_demo` |
| Airflow unittest after implementation | success | `13 tests OK`, `2 skipped` in Airflow Python because Snakemake 9 logger interface is not installed there |
| Snakemake 9 plugin unittest | success | `2 tests OK` with `/biosoftware/miniconda/envs/snakemake9_env/bin/python` |
| Snakemake 9 CLI logger help check | success | `--logger-airflow-demo-*` args discovered with `PYTHONPATH` |
| `docker compose -f docker-compose.yaml config --quiet` | success | Compose renders with new env vars |
| `airflow dags list-import-errors` | success | `No data found` after adding `dags/.airflowignore` |
| `airflow dags list | grep bio_pgta_airflow` | success | DAG listed |
| Airflow-only smoke run | success | `manual__PGTA_AIRFLOW_20260703_074844` ended success |
| artifact checks | success | `run_metadata.tsv`, `snakemake_events.jsonl`, and `snakemake_rule_summary.tsv` exist and are non-empty |
| XCom query | success | `snakemake_event_summary` contained `event_count=22`, status counts, and no failed jobs |

### Tests

Remote-only acceptance evidence on `fengxian`:

- DAG/runner unit tests passed in Airflow container.
- Logger plugin tests passed under Snakemake 9 Python.
- Snakemake 9 CLI discovered the repo-local plugin settings via `PYTHONPATH`.
- `bio_pgta_airflow` appeared in Airflow with no import errors.
- Real Airflow-only metadata smoke succeeded:
  - `analysis_id=PGTA_AIRFLOW_20260703_074844`
  - `dag_run_id=manual__PGTA_AIRFLOW_20260703_074844`
  - `run_metadata.tsv`: 11 lines
  - `snakemake_events.jsonl`: 22 lines
  - Airflow task log printed event count and status counts
  - XCom contained `snakemake_event_summary`

### Not run / why

- No frontend was implemented or tested.
- No FastAPI event receiver was implemented; T026 remains todo.
- No biodemo `snakemake_rule_event` writes were implemented; T043 remains todo.
- No PGT-A dry-run/CNV/baseline_qc target was run.
- No custom Airflow Web plugin was implemented; first UI surface is Airflow task log + XCom.

### Current git status

Work is on branch `codex/airflow/T086-pgta-airflow-logger`. Runtime code smoke passed on `fengxian` at commit `a5e6737`; final docs/state commit follows this handoff.

### Risks

- `bio_pgta_airflow` is intentionally manifest-only and does not create biodemo DB records.
- Logger events are currently JSONL + Airflow log/XCom only; backend POST is reserved for T026/T043.
- Snakemake event records expose useful workflow/job messages, but some log events do not include rule/sample fields.
- Airflow CLI `--conf` JSON is painful through Windows SSH quoting; use a temp JSON file plus `scp` for future manual triggers.

### Open questions

- Whether to make `/api/runs/{analysis_id}/actions/submit` optionally trigger `bio_pgta_airflow` after T026/T043, or keep it as a manual Airflow-only diagnostic DAG.

### Next recommended task

Run T026/T043 next: implement FastAPI `/api/events/snakemake` upsert and optionally let the logger plugin POST events while retaining JSONL fallback.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 02:13 - Codex - T025/T062 PGT-A diagnostics API

### Goal

Add backend diagnostics for PGT-A metadata runs: explicit Airflow state sync, fixed PGT-A log tail endpoints, dynamic metadata artifact listing, and run-level error summary extraction. Do not build frontend, dry-run target, Snakemake event receiver, qsub integration, or DB migration.

### Completed

- Added `POST /api/runs/{analysis_id}/actions/sync-airflow`.
- Added `GET /api/runs/{analysis_id}/logs?stream=stdout|stderr|metadata&tail=...`.
- Added `GET /api/runs/{analysis_id}/artifacts`.
- Added path safety checks so logs/artifacts must stay inside `CONTAINER_SHARED_ROOT` and the run `workdir`.
- Added missing log handling with structured `LOG_NOT_FOUND`.
- Added run-level failed DAG summary extraction from `logs/snakemake.stderr.log` into `analysis_run.error_summary`.
- Kept artifact discovery dynamic; no artifact table writes and no Alembic migration.
- Updated API, logging, runbook, task, current state, and manifest docs.

### Changed files

- `backend/app/diagnostics_service.py`
- `backend/app/main.py`
- `backend/tests/test_run_diagnostics.py`
- `docs/05_API_CONTRACT.md`
- `docs/10_QC_LOGGING_REPORTING.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml build backend` on `fengxian` before red test | success | Rebuilt image with red tests |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_run_diagnostics.py` before implementation | failed as expected | 6 failures: missing sync/log/artifact endpoints and structured errors |
| `docker compose -f docker-compose.yaml build backend` after implementation | success | Rebuilt diagnostics implementation |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_run_diagnostics.py` | success | `6 passed in 0.91s` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` | success | `26 passed in 1.56s` |
| `docker compose -f docker-compose.yaml config --quiet` | success | Compose still valid |
| service startup for postgres/redis/backend/Airflow | success | Used existing volumes; no `down -v` |
| `curl /api/health` and Airflow `/health` | success | Backend ok; Airflow metadatabase and scheduler healthy |
| `POST /api/runs/PGTA_20260702_171533_9A85B1/actions/sync-airflow` | success | Returned `status=success`, `error_summary=null` |
| `GET /api/runs/PGTA_20260702_171533_9A85B1/logs?stream=metadata&tail=3` | success | Returned last metadata lines from `run_metadata.tsv` |
| `GET /api/runs/PGTA_20260702_171533_9A85B1/logs?stream=stderr&tail=5` | success | Returned Snakemake stderr tail |
| `GET /api/runs/PGTA_20260702_171533_9A85B1/artifacts` | success | Returned metadata, stdout/stderr, config YAML, metadata config |
| `POST /api/runs/PGTA_20260702_171200_A68C19/actions/sync-airflow` | success | Returned `status=failed`, non-null `error_summary` |
| missing log probe for `PGTA_20260702_162531_74CE91` | success | HTTP 404 with `LOG_NOT_FOUND` |
| DB latest run query | success | success/failed/created states matched expected runs |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; compose ps empty |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Diagnostics unit tests passed: `6 passed`.
- Full backend test suite passed: `26 passed`.
- Real success run synced to `success`; real historical failed run synced to `failed` and wrote `error_summary`.
- Log and artifact APIs returned real files from `shared/runs`.
- Missing log returned structured `LOG_NOT_FOUND`.
- Path traversal/workdir safety is covered by unit test.

### Not run / why

- Frontend was not implemented or tested; this remains T057.
- PGT-A dry-run and invalid target failure smoke were not implemented; this remains T045/T084.
- Snakemake event receiver and rule/qsub-level errors were not implemented; this remains T026/T043.
- Airflow task-log API scraping was not implemented; current summary uses Snakemake stderr only.
- No DB migration was run or needed beyond existing Alembic head.

### Current git status

Implementation is on branch `codex/backend/T025-T062-logs-artifacts-sync` at code commit `25380e3`; final docs/state commit is expected before merging to `main`.

### Risks

- Historical failed run `PGTA_20260702_171200_A68C19` failed because of an Airflow PythonOperator bug, but current run-level summary intentionally reads Snakemake stderr first; it proves summary storage, not full Airflow task root-cause extraction.
- Artifact URLs for config files are reserved future view URLs; current implemented readable log URLs are stdout/stderr/metadata.
- `run_metadata.tsv` still contains tool-version probe errors for samtools/WisecondorX; that comes from the PGT-A metadata rule and was already present in the successful metadata smoke.

### Open questions

- Whether T045 should fix PGT-A metadata provenance/tool-version probes before adding dry-run, or leave that as a separate cleanup.

### Next recommended task

Run T045 next for PGT-A dry-run target, or T057 if the priority is visible demo UI using the newly available log/artifact/status APIs.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 01:19 - Codex - T027/T035 PGT-A submit to bio_pgta metadata

### Goal

Move an existing `pgta` run from `analysis_run.status=created` to the first Airflow executable path: submit it through FastAPI, trigger Airflow DAG `bio_pgta`, generate run-local PGT-A metadata config, and execute only the lightweight metadata target. Do not implement frontend, CNV, dry-run expansion, log API, or failure summary extraction.

### Completed

- Added `POST /api/runs/{analysis_id}/actions/submit`.
- Restricted submit to `pipeline=pgta`, `status=created`, and `target=metadata`.
- Triggered Airflow through the existing `AirflowClient`, with deterministic `dag_run_id=manual__<analysis_id>`.
- Updated biodemo `analysis_run.status` to `submitted`, wrote `dag_run_id`, and recorded a `run_action`.
- Added Airflow DAG `bio_pgta` with `validate_request -> prepare_pgta_config -> run_metadata -> collect_metadata_artifact`.
- Added PGT-A metadata runner that reads `samples.selected.tsv`, writes run-local `config.yaml` and `config/pgta_metadata_config.json`, runs Snakemake from `/opt/pipelines/PGT_A`, and stores stdout/stderr plus `logs/run_metadata.tsv`.
- Made created run workdirs/config dirs group-writable so Airflow UID `50000:0` can write metadata outputs.
- Fixed an Airflow task variable shadowing bug that caused the first DAG smoke to fail after metadata generation.
- Updated API, DAG, runbook, testing, PGT-A plan, task, current state, and handoff docs.

### Changed files

- `backend/app/main.py`
- `backend/app/run_service.py`
- `backend/tests/test_run_creation.py`
- `backend/tests/test_run_submit.py`
- `dags/bio_pgta.py`
- `dags/pgta_metadata_runner.py`
- `dags/tests/test_bio_pgta_dag.py`
- `dags/tests/test_pgta_metadata_runner.py`
- `docs/05_API_CONTRACT.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q tests/test_run_submit.py` before implementation | failed as expected | Submit endpoint did not exist yet, returned 404 |
| `docker compose -f docker-compose.yaml run --rm --no-deps --entrypoint python airflow-scheduler -m unittest discover -s /opt/airflow/dags/tests -v` before implementation | failed as expected | `bio_pgta` and `pgta_metadata_runner` were not importable |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Compose rendered with backend, Airflow, PGT-A read-only mounts |
| `docker compose -f docker-compose.yaml build backend` on `fengxian` | success | Rebuilt backend image |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` on `fengxian` | success | `20 passed in 1.08s` |
| Airflow DAG unittest via `--entrypoint python` on `fengxian` | success | `6 tests OK` after the task shadowing fix |
| Airflow `py_compile` with `PYTHONPYCACHEPREFIX=/tmp/pycache` | success | Needed because mounted DAG directory is read-only for pycache writes |
| Service startup on `fengxian` | success | Started postgres, redis, backend, airflow-api-server, airflow-scheduler, airflow-worker |
| `curl /api/health`, `/api/health/db`, and Airflow `/health` | success | Backend DB and Airflow scheduler/metadatabase healthy |
| `airflow dags list | grep bio_pgta` | success | `bio_pgta` listed and not paused |
| Submit smoke for `PGTA_20260702_171200_A68C19` | Airflow failed | Metadata generated, then `collect_metadata_artifact` failed due PythonOperator variable shadowing |
| Submit smoke for `PGTA_20260702_171533_9A85B1` | success | Airflow run `manual__PGTA_20260702_171533_9A85B1` ended `success` |
| `find shared/runs/PGTA_20260702_171533_9A85B1 -maxdepth 4 -type f` | success | Found `config.yaml`, `config/pgta_metadata_config.json`, selected manifest, Snakemake logs, and `logs/run_metadata.tsv` |
| `head -5 logs/run_metadata.tsv` | success | Metadata file exists; git fields show permission errors but task succeeded |
| biodemo DB latest run query | success | `PGTA_20260702_171533_9A85B1|submitted|t|pgta` |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Backend test suite passed: `20 passed`.
- Airflow DAG tests passed: `6 tests OK`.
- Compose config and DAG py_compile passed.
- `bio_pgta` appeared in Airflow and was unpaused.
- Submit endpoint triggered `manual__PGTA_20260702_171533_9A85B1`.
- Airflow DAG state was `success`.
- `shared/runs/PGTA_20260702_171533_9A85B1/logs/run_metadata.tsv` exists.
- biodemo DB updated the run to `submitted` and `dag_run_id` non-null.

### Not run / why

- Frontend was not implemented or tested; still later T057.
- Backend log/artifact API and error summary extraction were not implemented; still T025/T062.
- PGT-A dry-run target and invalid target failure smoke were not implemented; still T045/T084.
- Airflow success/failed status is not yet written back to biodemo DB; current DB terminal state after submit is `submitted`.
- No `docker compose down -v`, `docker system prune`, or `docker volume prune` was run.

### Current git status

Implementation commits were pushed on `codex/airflow/T027-T035-pgta-submit-metadata`; tested code commit is `9758c7a`. Final state-doc commit is expected before merging to `main`.

### Risks

- `run_metadata.tsv` currently records permission errors for `git_branch` and `git_commit` because the Airflow container environment cannot run the PGT-A metadata rule's git probe cleanly. The metadata target still succeeded; fix provenance separately if needed.
- The first failed smoke run `PGTA_20260702_171200_A68C19` remains in Airflow as failure evidence.
- Submit is intentionally not idempotent for already submitted runs; repeated submit returns validation error because status is no longer `created`.

### Open questions

- Whether to add an Airflow completion callback or polling worker so biodemo DB can move from `submitted` to `success`/`failed`.

### Next recommended task

Run T025/T062 next: implement log/artifact API and error summary extraction, then use that for dry-run/failure smoke and frontend run detail.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repository changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-03 00:28 - Codex - T022/T024 PGT-A server-path project creation

### Goal

Replace the old upload/sample-sheet plan with PGT-A server-path sample discovery: scan existing FASTQ paths under an allowlisted rawdata root, select samples, create a biodemo `analysis_run` and `sample` rows, and write a selected manifest. Do not trigger Airflow, write a DAG, run Snakemake, or build frontend pages.

### Completed

- Added backend `POST /api/input/scan` for `pipeline=pgta`, with `INPUT_SCAN_ROOTS` allowlist enforcement and R1/R2 FASTQ pairing.
- Added JSON `POST /api/runs` for PGT-A `target=metadata`, creating `analysis_run.status=created`, `sample` rows, `samples.selected.tsv`, and `request.json`.
- Added `GET /api/runs`, `GET /api/runs/{analysis_id}`, and `GET /api/runs/{analysis_id}/samples`.
- Kept `dag_run_id=null`; no Airflow DAG run is triggered in this phase.
- Added backend read-only PGT-A data mount and `INPUT_SCAN_ROOTS` env wiring.
- Updated API, architecture, engineering, frontend, DAG, testing, runbook, task, and state docs to use server-path scan instead of sample upload.
- Tightened `.gitignore` so generated `shared/runs/*`, `shared/uploads/*`, `shared/reports/*`, and `shared/logs/*` contents stay untracked while `.gitkeep` remains tracked.

### Changed files

- `.env.example`
- `.gitignore`
- `backend/app/config.py`
- `backend/app/input_scanner.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/run_service.py`
- `backend/tests/test_input_scanner.py`
- `backend/tests/test_input_scan_api.py`
- `backend/tests/test_run_creation.py`
- `docker-compose.yaml`
- `docs/01_SYSTEM_ARCHITECTURE.md`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/03_TASK_DESIGN.md`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/06_FRONTEND_SPEC.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/15_MULTI_AGENT_BOUNDARIES.md`
- `docs/17_DEMO_SCRIPT.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker compose run --rm --no-deps backend pytest -q` on `fengxian` before implementation build | failed as expected | `ModuleNotFoundError: No module named 'app.input_scanner'` |
| `docker compose -f docker-compose.yaml config --quiet` on `fengxian` | success | Rendered backend scan env and PGT-A read-only data mount |
| `docker compose -f docker-compose.yaml build backend` on `fengxian` | success | Rebuilt `airflow-demo/backend:0.1.0` |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` on `fengxian` | success | `17 passed in 0.97s` |
| `docker compose -f docker-compose.yaml up -d postgres` on `fengxian` | success | Postgres healthy |
| `docker compose -f docker-compose.yaml run --rm biodemo-db-init` on `fengxian` | success | Repeat run altered/granted existing role/database |
| `docker compose -f docker-compose.yaml run --rm backend alembic upgrade head` on `fengxian` | success | No pending migration output, schema already at head |
| `docker compose -f docker-compose.yaml up -d backend` on `fengxian` | success | Backend healthy |
| `curl http://127.0.0.1:8000/api/health` and `/api/health/db` | success | Both returned `{"status":"ok"}` |
| API smoke script for `/api/input/scan` and `/api/runs` | API success, shell exit nonzero | API returned scan 5 candidates, `truncated=true`, create 201 for `PGTA_20260702_162531_74CE91`; PowerShell heredoc CRLF caused trailing `NameError: name 'PY' is not defined` after success |
| `curl /api/runs/PGTA_20260702_162531_74CE91` | success | status `created`, `dag_run_id=null`, sample_count 2, input_mode `server_path_scan` |
| `curl /api/runs/PGTA_20260702_162531_74CE91/samples` | success | 2 samples, status `pending`, qc_status `unknown`, fq1/fq2 paths present |
| `psql` latest run query | success | `PGTA_20260702_162531_74CE91|created|t|pgta` |
| `wc -l samples.selected.tsv` and `head -n 1` | success | 3 lines total; header `sample_id R1 R2 source_dir` |
| `test -f request.json` | success | request file exists |
| `docker compose -f docker-compose.yaml ps` before down | success | Only postgres and backend were running; no Airflow services |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; no `-v` or prune |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Dockerized backend tests passed: `17 passed`.
- Compose config passed.
- Backend health and DB health passed.
- `/api/input/scan` found candidates under `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28`.
- `/api/runs` created `PGTA_20260702_162531_74CE91` with 2 selected samples, status `created`, and `dag_run_id=null`.
- DB and generated files were verified; no Airflow containers were started for the smoke.

### Not run / why

- Airflow trigger and `bio_pgta` DAG were not run; this remains T027/T035.
- Snakemake and PGT-A metadata/dry-run/failure smoke were not run; this remains T045/T084.
- Frontend UI was not implemented or tested; this remains T051/T052/T057.
- Local pytest/Docker/Snakemake tests were not run by project rule; local checks were limited to Git, diff, and docs keyword checks.

### Current git status

Implementation commit `9928b9c` passed remote runtime verification on branch `codex/backend/T022-T024-server-path-runs`; final state-doc and `.gitignore` tightening were merged forward to `main`.

### Risks

- The scan algorithm is intentionally conservative and pairs direct-child FASTQ files by R1/R2 naming; unusual PGT-A layouts may need another parser rule after real examples are reviewed.
- Smoke created a persistent biodemo `created` run and shared output under `shared/runs/PGTA_20260702_162531_74CE91`; it is ignored by Git and can be left as smoke evidence.
- `target=metadata` is the only supported create-run target before DAG integration.

### Open questions

- Whether T027 should trigger Airflow from an existing `created` run only, or also allow create-and-trigger in one API call after the safer two-step path is stable.

### Next recommended task

Run T027/T035: trigger Airflow `bio_pgta` from an existing `created` run, generate PGT-A config from `samples.selected.tsv`, and keep execution limited to metadata target.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repo changes with normal `git revert`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-02 23:49 - Codex - T021/T023 biodemo DB and Airflow client foundation

### Goal

Implement the P2 backend foundation only: biodemo SQLAlchemy/Alembic schema, repeatable DB init service, minimal Airflow REST client, and dependency health endpoints. Do not implement PGT-A, DAGs, React pages, or run submission APIs.

### Completed

- Added SQLAlchemy 2.0 models for `pipeline`, `analysis_run`, `sample`, `snakemake_rule_event`, `qc_metric`, `artifact`, and `run_action`.
- Added Alembic environment and initial migration `20260702_0001_initial_biodemo_schema.py`.
- Added repeatable Compose one-shot service `biodemo-db-init` to create/update `BIODEMO_USER` and `BIODEMO_DB`.
- Added backend `AirflowClient` with `health`, `list_dag_runs`, `get_dag_run`, and `trigger_dag_run`.
- Added `GET /api/health/db` and `GET /api/health/airflow`.
- Added `AIRFLOW_API_USERNAME` / `AIRFLOW_API_PASSWORD` env wiring.
- Added `backend/pip.conf` using the TUNA PyPI mirror and changed the backend image to install dependencies into `/opt/venv`.
- Verified on `fengxian`; then stopped services with `docker compose -f docker-compose.yaml down` only.

### Changed files

- `.env.example`
- `backend/Dockerfile`
- `backend/pip.conf`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/20260702_0001_initial_biodemo_schema.py`
- `backend/app/airflow_client.py`
- `backend/app/config.py`
- `backend/app/db.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/requirements.txt`
- `backend/requirements-dev.txt`
- `backend/tests/test_airflow_client.py`
- `backend/tests/test_health_dependencies.py`
- `backend/tests/test_models_metadata.py`
- `docker-compose.yaml`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/04_DATABASE_SCHEMA.md`
- `docs/05_API_CONTRACT.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| red probe importing `app.models` on `fengxian` | failed as expected | `ModuleNotFoundError: No module named 'app.models'` before implementation |
| `docker compose -f docker-compose.yaml config --quiet` | success | Included `biodemo-db-init` service |
| `docker compose -f docker-compose.yaml build backend` | success | After `backend/pip.conf`, pip used `https://pypi.tuna.tsinghua.edu.cn/simple`; install step took about 11s |
| `docker compose -f docker-compose.yaml run --rm --no-deps backend pytest -q` | success | `9 passed` |
| `docker compose -f docker-compose.yaml up -d postgres` | success | Postgres healthy |
| `docker compose -f docker-compose.yaml run --rm biodemo-db-init` | success | First run created role/database; repeat run only altered role/granted schema privileges |
| `docker compose -f docker-compose.yaml run --rm backend alembic upgrade head` | success | Applied revision `20260702_0001`; repeat run succeeded |
| `psql` table list in `biodemo` | success | Found `alembic_version` plus 7 core business tables |
| `docker compose -f docker-compose.yaml up -d redis airflow-api-server airflow-scheduler airflow-worker backend` | success | Started backend and Airflow basics for smoke only |
| `curl http://127.0.0.1:8000/api/health` | success | Returned `{"status":"ok"}` |
| `curl http://127.0.0.1:8000/api/health/db` | success | Returned `{"status":"ok"}` |
| `curl http://127.0.0.1:12958/health` | success | Airflow metadatabase and scheduler healthy |
| `curl http://127.0.0.1:8000/api/health/airflow` | success | Backend returned Airflow health payload |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; no volume deletion |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Dockerized backend tests passed: `9 passed`.
- `biodemo-db-init` and Alembic migration are repeatable.
- `biodemo` contains `pipeline`, `analysis_run`, `sample`, `snakemake_rule_event`, `qc_metric`, `artifact`, and `run_action`.
- Backend health, DB health, direct Airflow health, and backend Airflow health all passed.

### Not run / why

- PGT-A metadata/dry-run/failure smoke was not run; that remains T027/T035/T045/T057/T084.
- No `bio_pgta` DAG was written or imported.
- No React/frontend functional page was implemented.
- No `/api/runs` submission/list/detail logic was implemented.
- No host-level Python dependency install was run; server-side installs remain Dockerized, and any future host Python work must use a venv.

### Current git status

Implementation was verified on task branch `codex/backend/T021-T023-db-airflow-client` at code commit `5e9065d`. This handoff/state-doc update is expected as the final docs commit before merging/pushing `main`.

### Risks

- The backend image currently includes `pytest` and tests because this early demo needs Dockerized remote tests; later production image slimming can split runtime and test targets.
- `AIRFLOW_API_PASSWORD` reuses the demo Airflow admin password in the remote untracked `.env`; do not commit or print it.
- Airflow triggerer remains absent; `/health` reports triggerer null, which is acceptable for current CeleryExecutor smoke.
- The initial schema is now applied in the persistent Postgres volume; use normal Alembic forward migrations for future changes, not destructive resets.

### Open questions

- Whether T024 should expose DB-backed `/api/runs` read endpoints first, or whether T022 upload/parser should land before any run listing UI contract.

### Next recommended task

Run T022 for mock sample upload/parser, then T024 for run list/detail/status APIs. Keep PGT-A DAG work behind T027/T035/T045/T057 after backend run contracts exist.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repo changes with a normal Git revert.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard`, or `git clean -fdx`.

## 2026-07-02 23:03 - Codex - T011 Airflow 12958 smoke

### Goal

Move Airflow host access to port `12958`, move Docker nginx/frontend placeholder to `12959`, initialize Airflow metadata/admin, and verify the base Docker Compose services on `fengxian`.

### Completed

- Updated Compose defaults: `AIRFLOW_PORT=12958`, `FRONTEND_PORT=12959`.
- Added `airflow-init` one-shot service for Airflow DB migration and admin user creation.
- Kept Postgres and Redis internal-only; no `5432:5432` or `6379:6379` host port mapping was added.
- Updated remote `.env` with new non-secret port/admin keys and generated an Airflow admin password without printing it.
- Verified `12958`, `12959`, `8000`, `8025`, `1025`, `5432`, and `6379` were free before smoke; `3000` remains occupied by a non-project next-server.
- Ran `airflow-init`; Airflow metadata migration completed and admin user `admin` was created.
- Started postgres, redis, mailhog, backend, frontend, airflow-api-server, airflow-scheduler, and airflow-worker.
- Verified backend `/api/health`, frontend placeholder, MailHog UI, and Airflow `/health`.
- Stopped services with `docker compose -f docker-compose.yaml down`; no `-v`, prune, or volume deletion was used.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `docs/01_SYSTEM_ARCHITECTURE.md`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git switch -c codex/infra/T011-airflow-12958` | success | Task branch for local edits |
| `docker compose config --quiet` on `fengxian` | success | Rendered Airflow `12958->8080`, frontend `12959->80`, backend `8000->8000`, MailHog `1025/8025` |
| remote port probe with `ss -lnt` | success | `12958/12959/8000/8025/1025/5432/6379` free; `3000` busy by non-project next-server |
| `docker compose -f docker-compose.yaml up airflow-init` | success | Airflow DB migration completed; admin user `admin` created |
| `docker compose -f docker-compose.yaml up -d postgres redis mailhog backend frontend airflow-api-server airflow-scheduler airflow-worker` | success | All base services started |
| `curl http://127.0.0.1:8000/api/health` | success | Returned `{"status":"ok"}` |
| `curl http://127.0.0.1:12959/` | success | Returned `airflow-demo frontend placeholder` |
| `curl http://127.0.0.1:8025/` | success | Returned MailHog HTML page |
| `curl http://127.0.0.1:12958/health` | success | Airflow metadatabase and scheduler healthy |
| `docker compose -f docker-compose.yaml down` | success | Safe stop only; no volume deletion |

### Tests

Remote-only acceptance evidence on `fengxian`:

- Compose config passed for commit `9c640dc`.
- Airflow `/health` passed at `127.0.0.1:12958`.
- Docker nginx/frontend placeholder passed at `127.0.0.1:12959`.
- Backend health and MailHog HTTP GET passed.
- `docker compose ps` after down showed no running airflow-demo services.

### Not run / why

- PGT-A DAG, Snakemake metadata/dry-run, and failure smoke were not run; they remain later T027/T035/T045/T057/T084 work.
- React functional page was not implemented or tested; frontend is still Docker nginx placeholder only.
- biodemo DB migration was not implemented or run; T021 remains next.
- Airflow API client was not implemented; T023 remains next.

### Current git status

Implementation commit `9c640dc` was pushed to `origin/main` and pulled into `fengxian:/home/jiucheng/project/airflow-demo`. A follow-up state-doc commit is expected after this handoff update.

### Risks

- Airflow admin password exists only in the remote untracked `.env`; do not commit or print it.
- The Airflow triggerer is not running, so `/health` reports triggerer status as null; this is acceptable for the current CeleryExecutor smoke.
- Host port `3000` belongs to a non-project next-server and must not be stopped by airflow-demo tasks.
- PowerShell-to-SSH here-strings can introduce CRLF issues; prefer single-line SSH commands or CR-stripped bash scripts for future remote runs.

### Open questions

- Whether to keep Airflow reachable directly on `12958` for the demo, or later hide it behind a Docker nginx reverse proxy after frontend/API auth stabilizes.

### Next recommended task

Run T021 for biodemo DB models/migrations, then T023 for the FastAPI Airflow API client. Do not jump directly to PGT-A metadata smoke until backend DB/API basics are in place.

### Rollback notes

- Stop services with `docker compose -f docker-compose.yaml down`.
- Revert repo changes with a normal Git revert if needed.
- Do not run `docker compose down -v`, `docker system prune`, or `docker volume prune`.

## 2026-07-02 22:38 - Codex - fengxian host nginx inventory

### Goal

Record the existing host-level nginx on `fengxian` as deployment environment information without changing nginx configuration or service state.

### Completed

- Verified `/usr/sbin/nginx` exists and is executable on `fengxian`.
- Recorded host nginx path and version in `SERVER_INFO.md`.
- Added a deployment runbook note that host nginx is only a future reverse-proxy candidate for airflow-demo, not currently configured by this project.

### Changed files

- `SERVER_INFO.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `ssh fengxian '/usr/sbin/nginx -v 2>&1; test -x /usr/sbin/nginx && ls -l /usr/sbin/nginx'` | success | Returned `nginx version: nginx/1.14.0 (Ubuntu)` and executable path metadata |

### Tests

Remote-only read probe passed on `fengxian`; no local runtime test was run.

### Not run / why

- No nginx config test was run because airflow-demo does not yet manage host nginx.
- No nginx reload/restart was run.
- No Docker, Airflow, backend, frontend, DB, or Snakemake runtime test was needed for this documentation-only update.

### Current git status

Documentation changes are pending local commit/push at the time of this handoff entry.

### Risks

- Host nginx exists, but no airflow-demo server block or reverse proxy routing has been designed or applied.
- Future reverse-proxy work must avoid interrupting existing host services.

### Open questions

- Whether T011 or a later infra task should add a dedicated nginx reverse-proxy plan for backend, frontend, Airflow, and MailHog access.

### Next recommended task

Continue with T011 Airflow initialization first; handle host nginx reverse proxy as a separate infra task after service ports and auth behavior are stable.

### Rollback notes

This update is documentation only. Roll back with a normal Git revert if needed; do not edit or reload host nginx as part of rollback.

## 2026-07-02 22:47 - Codex - Docker image cleanup and tag pinning

### Goal

Clean duplicate/dangling `<none>` Docker images on `fengxian`, avoid implicit `latest` for airflow-demo images, and verify required compose images can be pulled or built without starting services.

### Completed

- Inspected running containers, all images, dangling images, compose images, latest-tag images, and Docker disk usage on `fengxian`.
- Removed 37 dangling `<none>:<none>` image IDs using exact `docker image rm` IDs.
- Did not run `docker system prune`, `docker volume prune`, or `docker compose down -v`.
- Did not touch running containers: `cosmetic-db-web` and `yunse-bio`.
- Did not delete non-project `latest` images such as `yunse-bio:latest` or `fischbachlab/*:latest`.
- Added explicit backend image tag `airflow-demo/backend:0.1.0` to compose and `.env.example`.
- Rebuilt backend on `fengxian` with the fixed tag and removed old project tag `airflow-demo-backend:latest`.
- Verified `docker compose config --images` now uses explicit tags and no airflow-demo `latest`.
- Pulled external compose images successfully: Airflow, Postgres, Redis, MailHog, nginx.

### Changed files

- `.env.example`
- `docker-compose.yaml`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `docker ps -a` / `docker images` / `docker images --filter dangling=true` | success | Found 37 dangling images; found project backend image using implicit `latest` |
| `docker image rm <37 dangling ids>` | success | Dangling images reduced to zero; no force used |
| `docker system df` | success | Images count dropped from 54 to 17; no volume cleanup performed |
| `docker compose config --images` | success | Shows `airflow-demo/backend:0.1.0`; no project `latest` image |
| `docker compose build backend` | success | Built/tagged backend as `airflow-demo/backend:0.1.0` using cached layers |
| `docker image rm airflow-demo-backend:latest` | success | Removed old project latest tag only |
| `docker compose pull postgres redis mailhog frontend airflow-api-server airflow-scheduler airflow-worker` | success | Pulled external compose images; scheduler/worker reused Airflow image |
| image inspect loop | success | Verified Airflow, postgres, redis, mailhog, nginx, and backend images exist |
| `docker compose ps` | success | No airflow-demo containers running after checks |

### Tests

Remote-only evidence on `fengxian`:

- Dangling image list is empty after cleanup.
- `docker compose config --quiet` passed.
- Required compose images are present locally.
- `docker images` has no `airflow-demo*:latest`.

### Not run / why

- Airflow containers were not started; this task only checked image availability and cleanup.
- No frontend app container was built; frontend is still nginx placeholder only.
- No database migration was run.
- No volume cleanup was run, by project safety rule.

### Current git status

Code/docs changes for explicit backend image tag are committed and pushed as `07a63fa`; state docs from this cleanup are expected to be committed and pushed next.

### Risks

- Docker still reports reclaimable space from unused non-project images and unused volumes, but those were intentionally left untouched.
- Several non-project `latest` images remain on `fengxian`; deleting or retagging them needs separate owner confirmation.

### Open questions

- Whether airflow-demo should later use an internal registry or image digest pinning for stricter reproducibility.
- Whether to configure Docker registry mirrors for future Airflow/base-image pulls.

### Next recommended task

Proceed to T011: start and initialize Airflow services using the already pulled `apache/airflow:2.9.3-python3.11` image, then verify Airflow `/health`.

### Rollback notes

- The removed dangling images had no tags; rollback would require rebuilding or repulling the workloads that produced them.
- Revert the backend tag change with a normal Git revert if needed; do not force push.

## 2026-07-02 22:24 - Codex - T010/T012/T013/T014/T020 fengxian base skeleton

### Goal

Build the fengxian base runtime surface before PGT-A DAG/frontend work: user-level Docker Compose v2 readiness, GitHub mirror sync, Docker Compose service skeleton, shared directory contract, and minimal FastAPI `/api/health`.

### Completed

- Added minimal FastAPI backend at `backend/app/main.py` with `GET /api/health -> {"status":"ok"}`.
- Added backend Dockerfile and pinned minimal backend requirements.
- Added `docker-compose.yaml` with fixed `172.30.10.0/24` network and services: postgres, redis, mailhog, backend, frontend placeholder, airflow-api-server, airflow-scheduler, airflow-worker.
- Added tracked shared directory placeholders while keeping runtime contents ignored.
- Updated `.env.example`, engineering spec, API contract, deployment runbook, testing rules, agent workflow, and PGT-A plan.
- Added project constraint: local Windows repo is for editing/Git/docs only; runtime tests are remote-only.
- Re-ran fengxian Level 0 preflight: Docker 20.10.21, PGT-A/Snakemake paths readable, `172.30.10.0/24` non-conflicting.
- Installed Docker Compose v2.24.7 as a user-level CLI plugin at `/home/jiucheng/.docker/cli-plugins/docker-compose`.
- After user correction, replaced the plugin using local Windows GitHub Release download plus `scp` to fengxian; final plugin SHA256 is `19c9deb6f4d3915f5c93441b8d2da751a09af82df62d55eab097c2cbfebd519f`.
- Cloned `git@github.com:boksic1986/airflow-BS-demo.git` into empty `fengxian:/home/jiucheng/project/airflow-demo` as a code mirror.
- Created remote ignored `.env` for smoke only; no `.env` committed.

### Changed files

- `.env.example`
- `.gitignore`
- `AGENTS.md`
- `backend/Dockerfile`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/requirements-dev.txt`
- `backend/requirements.txt`
- `backend/tests/test_health.py`
- `dags/.gitkeep`
- `docker-compose.yaml`
- `shared/.gitkeep`
- `shared/uploads/.gitkeep`
- `shared/runs/.gitkeep`
- `shared/reports/.gitkeep`
- `shared/logs/.gitkeep`
- `docs/02_ENGINEERING_SPEC.md`
- `docs/05_API_CONTRACT.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/12_TESTING_ACCEPTANCE.md`
- `docs/14_AGENT_WORKFLOW.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `ssh fengxian` Level 0 preflight | success | Docker 20.10.21/API 1.41, PGT-A path and Snakefile readable, Snakemake 8.5.4, Python 3.12.2, no `172.30.10.0/24` conflict |
| direct `curl` GitHub release on fengxian | timed out | Left a partial plugin file, later replaced |
| TUNA Docker CE focal deb unpack to user plugin | success | Produced `Docker Compose version v2.24.7`; used as fallback path |
| local `curl.exe --proxy socks5h://127.0.0.1:1080` GitHub Release download + `scp` | success | Official `docker-compose-linux-x86_64` downloaded locally and synced to fengxian |
| `docker compose version` on fengxian | success | `Docker Compose version v2.24.7` |
| `git clone git@github.com:boksic1986/airflow-BS-demo.git /home/jiucheng/project/airflow-demo` | success | Directory was empty; mirror is on `main`, clean, commit `dd1d8a7` for tested code |
| `docker compose config --services` | success | Listed postgres, redis, airflow-worker, backend, frontend, mailhog, airflow-api-server, airflow-scheduler |
| `docker compose config --quiet` | success | Re-run after local GitHub plugin replacement also passed |
| `docker compose up -d postgres redis mailhog backend` | success | Built backend image, pulled base images, started minimal services |
| `curl -fsS http://127.0.0.1:8000/api/health` | success | Returned `{"status":"ok"}` |
| `docker compose down` | success | Used safe stop only, no `-v` |
| `curl -fsSI http://127.0.0.1:8025` | failed | MailHog returned 404 for HEAD; not a service failure |
| `curl -fsS http://127.0.0.1:8025/` | success | MailHog GET probe found page content |
| `docker compose ps` after cleanup | success | No running demo containers |

### Tests

Remote-only acceptance evidence:

- `docker compose config --quiet` passed on fengxian with user-level Compose v2.24.7.
- Minimal service smoke passed on fengxian: postgres, redis, mailhog, backend started; backend health returned `{"status":"ok"}`; services were stopped with `docker compose down`.
- MailHog HTTP GET probe passed on fengxian.

Local note: a local pytest/YAML parse check was run before the user clarified the remote-only testing rule. Those local results are not counted as acceptance evidence, and the temporary `.venv` was removed.

### Not run / why

- Airflow web/scheduler/worker startup: out of scope for this batch; T011 remains next.
- Airflow `/health`: not run because Airflow services were not started.
- frontend functional test: out of scope; frontend is only an nginx placeholder.
- biodemo DB migration: not implemented yet.
- PGT-A metadata/dry-run/failure smoke: intentionally deferred to T027/T035/T045/T057/T084.
- Snakemake dry-run: not run in this batch.

### Current git status

Local repo has the implementation commit `dd1d8a7` pushed to `origin/main`; this handoff/state-doc update is expected to be committed and pushed as a follow-up docs/state commit. Fengxian mirror is clean at the tested code commit.

### Risks

- Remote image and pip downloads can be slow; consider adding Docker registry/pip mirror configuration in a later infra task if builds remain slow.
- The current Postgres smoke starts only the default Airflow database; biodemo DB/schema creation is still pending.
- Airflow services are defined but not validated; the Airflow image may still require initialization/user setup in T011.
- The remote `.env` contains local-only demo credentials and is ignored; it must not be committed.

### Open questions

- Whether to keep direct commits to `main` during early bootstrap or switch to task branches/PRs for T011 onward.
- Which migration tool to use first for biodemo DB: Alembic with SQLAlchemy/SQLModel or plain SQL bootstrap.

### Next recommended task

Run T011: initialize and start Airflow web/scheduler/worker, then verify Airflow `/health` and document the minimal Airflow user/auth setup without adding PGT-A DAG yet.

### Rollback notes

- Stop services with `docker compose down` only.
- Remove the user-level Compose plugin with `rm "$HOME/.docker/cli-plugins/docker-compose"` if needed.
- Revert repository changes with a normal `git revert`; do not use `git reset --hard` or force push.

## 2026-07-02 21:16 - Codex - T005/local Git and plugin workflow

### Goal

Initialize `D:\pipeline\airflow-demo` as the local development Git repository, point it at `git@github.com:boksic1986/airflow-BS-demo.git`, and document server mirror, superpowers, and GitHub plugin usage rules.

### Completed

- Added `.gitignore` from the existing template so `.env`, local notes, shared data, FASTQ/BAM/VCF/NPZ, logs, caches, and build outputs stay untracked.
- Added `.gitattributes` to keep text files normalized to LF in the repository.
- Added `docs/19_REPO_AND_PLUGIN_WORKFLOW.md` with GitHub remote, local-vs-server mirror responsibilities, server pull-only rules, superpowers usage, GitHub plugin routing, and repository description.
- Updated `docs/14_AGENT_WORKFLOW.md` to require git status, remote, branch, commit/dirty-state checks and to document superpowers/GitHub plugin routing.
- Updated `docs/16_CODEX_PROMPTS.md` with Git/GitHub, superpowers, and GitHub plugin prompt templates.
- Updated `CURRENT_STATE.md`, `TASKS.md`, and `MANIFEST.json` for the new Git/GitHub workflow.
- Initialized local Git repository on branch `main` and added `origin` remote.

### Changed files

- `.gitignore`
- `.gitattributes`
- `docs/19_REPO_AND_PLUGIN_WORKFLOW.md`
- `docs/14_AGENT_WORKFLOW.md`
- `docs/16_CODEX_PROMPTS.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `MANIFEST.json`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | initially failed before `git init` | Confirmed the directory was not yet a Git repo |
| `gh --version` | success | GitHub CLI available: `2.92.0` |
| `gh auth status` | success | Authenticated as `boksic1986`, SSH git protocol |
| `git init -b main` | success | Created local repository |
| `git remote add origin git@github.com:boksic1986/airflow-BS-demo.git` | success | Added GitHub remote |
| `git status --short --branch` | success | Showed no commits yet on `main` with untracked project files |
| `git remote -v` | success | `origin` fetch/push both point to `git@github.com:boksic1986/airflow-BS-demo.git` |
| `git ls-remote origin HEAD` | success with no output | Remote is reachable; no HEAD advertised, consistent with an empty remote repo |
| `git commit -m "docs: initialize airflow demo planning repo"` | failed | Git author identity was not configured locally; no commit was created |
| `git push -u origin main` | failed | No commit existed yet, so `main` refspec did not exist |
| `git config user.name "boksic1986"` and `git config user.email "boksic1986@users.noreply.github.com"` | success | Set repo-local identity only; did not modify global Git config |
| final manifest/keyword/safety checks | success | Manifest `48/48`, keywords found, no unsafe file candidates |
| `git commit -m "docs: initialize airflow demo planning repo"` | success | Created initial commit `73ca47f` |
| `git push -u origin main` | success | Pushed `main` to `git@github.com:boksic1986/airflow-BS-demo.git` and set upstream |

### Tests

Pending final verification before commit/push:

- Manifest `file_count` and listed files must match.
- Required GitHub/plugin/server mirror keywords must be searchable.
- Git safety check must confirm ignored secrets/data patterns are not staged.
- `git ls-remote origin HEAD` must remain accessible.

### Not run / why

- Docker/Airflow/PGT-A tests were not run; this task only initializes Git and updates documentation.
- GitHub PR creation was not run; the requested flow is initial commit and push to `main`, not a draft PR.

### Current git status

Local repository initialized on `main` with `origin=git@github.com:boksic1986/airflow-BS-demo.git`. Initial commit `73ca47f` was pushed to `origin/main`; a follow-up documentation-state commit records the final status.

### Risks

- If GitHub remote has branch protection or non-empty hidden state, `git push -u origin main` may fail. Do not force push without explicit user approval.
- Server mirror on fengxian has not been cloned or pulled in this task.

### Open questions

- Whether to configure GitHub repository description through the GitHub UI/API after the initial push.
- Whether future implementation should use direct commits on `main` for early bootstrap or task branches with draft PRs.

### Next recommended task

Run the final verification, commit the bootstrap documentation, push `main`, then use T014 for Docker Compose v2 readiness on fengxian.

### Rollback notes

If no push has happened, remove `.git/` and revert the documentation changes. If push succeeds and rollback is needed, use a normal revert commit; do not use `git reset --hard` or force push without explicit approval.

## 2026-07-02 20:51 - Codex - T004/fengxian PGT-A demo 测试计划

### Goal

将用户确认的 fengxian PGT-A demo 测试方案落地为仓库文档，并同步当前状态、任务表和交接记录；不执行服务器安装、部署、容器启动或 PGT-A 流程运行。

### Completed

- 新增 `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`，记录 `pgta` / `bio_pgta` 命名、Snakemake 8.5.4 暂不升级、用户级 Docker Compose v2 plugin 准入、固定 Docker 网段 `172.30.10.0/24`、Level 0-4 测试层级和 BS10610 迁移预检。
- 更新 `SERVER_INFO.md`，记录 fengxian 与 BS10610 的非敏感只读探测快照。
- 更新 `CURRENT_STATE.md`，标记当前仍处 P0，计划已落地但服务未实现/未启动。
- 更新 `TASKS.md`，新增 T004 计划任务并拆出后续 T014/T027/T035/T045/T057/T084。

### Changed files

- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `SERVER_INFO.md`
- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`

### Commands run

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | failed: not a git repository | 当前 `D:\pipeline\airflow-demo` 不是 Git 仓库 |
| `rg -n "PGT|pgta|bio_pgta|fengxian|BS10610|Snakemake 9|docker compose|172\.30\.10"` | success | 修改前仅发现通用 compose 文档，无 PGT-A 计划 |
| `Get-Date -Format 'yyyy-MM-dd HH:mm'` | success | 用于 handoff 时间 |
| PowerShell `ConvertFrom-Json` manifest check | success | `file_count=45`、manifest 列表数 `45`、缺失文件数 `0` |
| old draft identifier and placeholder grep | success: no matches | 无旧草案标识、BS10610 用户名笔误或占位文本 |
| `rg -n "bio_pgta|pipeline=pgta|172\.30\.10\.0/24|v2\.24\.7|Snakemake 8\.5\.4|BS10610|T004|T014|T027|T035|T045|T057|T084" ...` | success | 关键命名、网段、Compose 版本、任务 ID 均可定位 |
| `Select-String ... -Pattern 'docker compose down -v|docker system prune|docker volume prune|baseline_qc|Level 0|metadata|bio_pgta'` | success | 安全禁止项和 Level 0-4 关键测试词均可定位 |

### Tests

文档一致性检查已运行：manifest JSON 可解析且计数匹配；新增计划、任务、状态和交接中可定位 `pgta` / `bio_pgta`、固定网段、Compose 版本、Snakemake 8.5.4、BS10610 和后续任务 ID；旧草案标识和笔误检查无匹配。

### Not run / why

- `docker compose version` / `docker compose config`: 未运行；用户要求本轮不执行服务器变更，且当前本地目录无 compose 文件。
- backend/frontend/DAG/Snakemake tests: 未运行；对应代码尚未实现。
- PGT-A metadata/dry-run smoke: 未运行；本轮只落地计划文档。

### Current git status

不可用。`git status --short --branch` 返回 `fatal: not a git repository (or any of the parent directories): .git`。

### Risks

- `CURRENT_STATE.md` 和 `SERVER_INFO.md` 的服务器信息来自本轮前的只读探测快照，真实执行前仍需重复 Level 0 preflight。
- fengxian 当前没有 Docker Compose v2；后续 T014 必须先解决 Compose 准入。
- BS10610 路径与用户不同，迁移前必须参数化路径，不能复用 fengxian 硬编码路径。

### Open questions

- 是否要把 airflow-demo 初始化为 Git 仓库或从远端仓库重新同步。
- PGT-A Level 4 `baseline_qc` 是否在 Level 1-3 通过后允许运行，以及允许运行的并发上限。

### Next recommended task

执行 T014：在 fengxian 以用户级 Docker CLI plugin 方式安装/启用 Docker Compose v2，并只运行 `docker compose version` 作为准入验收。

### Rollback notes

本轮仅改文档。回滚方式是移除 `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`，并恢复 `SERVER_INFO.md`、`CURRENT_STATE.md`、`TASKS.md`、`HANDOFF.md` 到本轮修改前内容。

### <TO_BE_FILLED>

暂无。
## 2026-07-08 - Codex - T108 Dashboard/Run Detail usability polish

### Goal

Improve Dashboard and Run Detail readability for PGT-A/NIPT operators and add a
controlled PGT-A `baseline_qc` stage rerun path without enabling arbitrary DAG
triggers.

### Completed in working tree

- Dashboard backend aggregation adds sample throughput/trend, readable current
  stage labels, elapsed runtime, matching-history average duration, ETA, and
  estimated finish time.
- Dashboard UI switches `QC / failure focus` to `Sample throughput` with
  `24h / 7d / 30d`, converts Intake scanner to a compact table, and renders Run
  Tracker as a paginated table with Project/Run ID links.
- Run Detail UI renders the selected sample manifest table, QC failure summary,
  config artifacts before raw params, primary/advanced files, larger current
  progress, and a controlled `Run action` modal.
- PGT-A reanalysis supports `mode=rerun_stage` with `stage=mapping|metadata|baseline_qc`
  only for terminal PGT-A `baseline_qc` runs.
- `bio_pgta` can branch into the staged TaskGroup at mapping, metadata, or
  baseline_qc according to `params.rerun_stage`; the runner uses
  `--rerun-incomplete` and no `--forceall`.

### Commands run so far

| Command | Result | Notes |
|---|---|---|
| `git status --short --branch` | passed | On `codex/frontend/T108-dashboard-run-detail-usability` |
| `git diff --check` | passed | No whitespace errors before docs/state finalization |

### Pending validation

- Local feedback checks for backend dashboard/reanalysis tests, DAG/runner
  tests, and frontend Docker/test target.
- Remote `fengxian` acceptance after local feedback passes:
  `docker compose config --quiet`, backend targeted pytest, frontend Docker
  test target, rebuild/recreate backend/airflow-worker/airflow-scheduler/frontend,
  HTTP 200, and a light PGT-A metadata smoke only.

### Not run / why

- Heavy PGT-A `baseline_qc` and NIPT `full_run` are intentionally not run in
  T108 without explicit approval.
- `bio_intake_scan` is not unpaused and auto-submit remains disabled.

### Risks / rollback

- ETA is an estimate from recent successful runs with the same pipeline target
  or run mode; it should not be presented as a scheduler guarantee.
- Controlled PGT-A stage rerun depends on existing run-local workdir and
  outputs. Revert the T108 code changes or stop using `mode=rerun_stage` if a
  staged rerun behaves unexpectedly.

## 2026-07-14 - Codex - T125 BS NIPT-only network constraint documentation

### Goal

Record the BS10610/BS1069 Docker network as a hard deployment constraint before
implementing the NIPT-only Airflow stack.

### Completed

- Added `docs/22_BS_NIPT_DEPLOYMENT.md` with the NIPT-only scope, primary/cold
  standby roles, Snakemake 9 runtime requirement, preflight, acceptance, and
  rollback contract.
- Updated engineering, deployment, security, and server documentation with the
  immutable external network values: `nipt_analysis_test_net`,
  `192.168.199.0/24`, gateway `192.168.199.1`.
- Recorded project root
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT` and prohibited network
  creation, recreation, deletion, IPAM changes, or alternate-subnet fallback.
- Clarified that nginx client CIDR `172.17.61.0/24` does not conflict with the
  Docker subnet, but BS operations also require an explicit
  `172.17.106.0/24`/local-health access path while retaining `deny all`.

### Validation

- Documentation-only consistency checks: exact network tuple, project root,
  task ID, manifest membership/count, JSON parse, and `git diff --check`.
- Read-only `ssh BS10610 printenv SSH_CONNECTION` showed source
  `172.17.61.18`, confirming the current operator path is covered by
  `172.17.61.0/24`; HTTP must still be verified from nginx access logs.

### Changed files

- `docs/02_ENGINEERING_SPEC.md`
- `docs/09_NIPT_DOCKER_SPEC.md`
- `docs/11_DEPLOYMENT_RUNBOOK.md`
- `docs/13_SECURITY_AND_OPERATIONS.md`
- `docs/18_PGTA_FENGXIAN_TEST_PLAN.md`
- `docs/22_BS_NIPT_DEPLOYMENT.md`
- `SERVER_INFO.md`, `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`,
  `MANIFEST.json`

### Not run / why

- No remote Docker, Compose, image transfer, service startup, or NIPT workflow
  command was run; T125 is documentation-only.
- BS10610 and BS1069 both passed a writeability probe through
  `/mnt/biodevrwbi/33.chenjiucheng`; `/bi/biodevrwbi/33.chenjiucheng` is the
  alternate mapping and is not used for deployment writes.

### Risks / next step

- Live network attachments and planned static IPs may change. Re-run
  `docker network inspect nipt_analysis_test_net` immediately before startup.
- Next task should implement a standalone BS NIPT-only Compose stack and stop
  if the network tuple or project-root write probe fails.

### Current git status

Branch `codex/deploy/T125-bs-nipt-network-constraint` contains only the T125
documentation changes and remains uncommitted pending user review.

### Open questions

- Confirm whether any additional client networks beyond the currently observed
  `172.17.61.0/24` and BS operations subnet `172.17.106.0/24` require access.
- Confirm planned static service addresses after the live attachment preflight;
  the subnet and gateway themselves are not negotiable.

### Rollback

Revert the T125 documentation commit. No service or data rollback is required.

## 2026-07-14 - Codex - T126 BS NIPT-only Airflow migration

### Goal

Deploy the existing NIPT Snakemake 9 workflow and Control Tower to BS10610,
prepare BS1069 as a stopped cold standby, and preserve the fixed external
Docker network and legacy NIPT `1.0.11` image.

### Completed

- Added a standalone NIPT-only Compose stack with fresh databases,
  `CeleryExecutor`, one scheduler, one worker, React/nginx gateway, FastAPI,
  and only `bio_nipt_docker` plus `bio_intake_scan`.
- Added backend/frontend deployment capabilities so the BS product exposes
  only NIPT Docker and rejects PGT-A/WES/WGS create, scan, and submit requests.
- Tagged the validated S9 runtime as `niptpro:1.1.11` without changing source
  image ID `sha256:71df36b7f808...22187254`; retained `1.0.11` for rollback.
- Parameterized independent BS workflow, locale, reference, FASTQ, and shared
  roots. Source mounts are read-only and the run workdir is the only writable
  NIPT analysis mount.
- Fixed Airflow task-log 403 by sharing one webserver secret across API,
  scheduler, and worker. Fixed runner prepare so BS FASTQ/locale roots are read
  at task runtime. Added regression coverage.
- Transferred archives only as `fengxian -> D:\pipeline\t126-image-stage -> BS`.
  SHA256 passed locally and on both BS nodes.
- BS10610 is live on `172.17.106.10:12959` and `:12958`. The scanner remains
  paused and automatic NIPT submission remains disabled.
- BS1069 has the verified images loaded and no running platform service.

### Runtime acceptance

- First run `NIPT_20260714_131523_360744` failed in prepare because the runner
  used the old `/opt/nipt/workflow/fastq` default. It is retained for audit.
- Retry `NIPT_20260714_133355_B3081A`: 10 samples, success, 10/10 QC pass,
  96/96 rule events success, required mapping/CNV/prediction/summary outputs.
- Full `NIPT_20260714_140419_F999B0`: 72 samples, success, submitted
  22:04:20 CST, pipeline finished 22:19:43 CST (923 seconds), 72/72 QC pass,
  504 QC metrics, 592/592 rule events success, no running/failed residue.
- Observed peak NIPT container memory was 42.86 GiB against the 60 GiB limit.
  All 144 input FASTQ stat and SHA256 records were identical before/after.
- Mapping QC, all four T21 classifier files, and dynamic-reference summaries
  are byte-identical to the fengxian S9 baseline. Fetal-ratio max absolute
  delta is `4e-6`; other summary floating-point deltas are below `1.5e-11`.
  The old baseline `params.csv` was empty while the BS run records generated
  parameters; this is not a result discrepancy.

### Validation

| Check | Result |
|---|---|
| fengxian backend full pytest | 171 passed |
| fengxian DAG/runner tests before final path regression | 91 passed, 5 skipped, 4 subtests |
| targeted BS path-adapter tests | 18 passed |
| frontend Vitest | 50 passed |
| frontend `tsc -b && vite build` | passed |
| nginx config/version | passed; nginx 1.30.3, Alpine 3.23.5 |
| BS Compose config and external-network preflight | passed |
| Airflow task log after shared-secret fix | HTTP 200 with live phase/rule output |
| BS10610 health/capabilities | healthy; environment BS10610, NIPT only |

The final attempt to run the entire repository DAG suite inside the production
BS image was not accepted as evidence: the deploy release intentionally omits
tests and the production image omits pytest. The authoritative full suite is
the isolated fengxian result above; the only later runner change is covered by
the 18 passing targeted path-adapter tests and both successful BS full runs.

### Failures and fixes

```text
failure: initial 10-sample prepare task rejected /data/nipt-fastq as outside the old root
exit: Airflow task failed
cause: runner path defaults were resolved before BS runtime environment values
fix: read NIPT_FASTQ_CONTAINER_ROOT, NIPT_FASTQ_HOST_ROOT, and NIPT_LOCALE_HOST_ROOT during prepare; regression test added

failure: Airflow task-log REST returned 403
cause: API server and worker generated different webserver secret keys
fix: require AIRFLOW_WEBSERVER_SECRET_KEY in the untracked environment and pass it to all Airflow services

failure: early remote-to-remote archive copy truncated two large files
cause: unsupported direct transfer path
fix: discarded the partial transfer path and used the required local relay with SHA256 at each hop
```

### Current state and risks

- Branch: `codex/deploy/T126-bs-nipt-only-stack`.
- BS10610 volumes are live and must not be deleted. `bio_intake_scan` is
  paused. NIPT heavy manual submission is enabled for the accepted full mode;
  automatic intake is disabled.
- Direct workstation access to `172.17.106.10` timed out because no local route
  was available. Node-local HTTP checks pass; use an SSH tunnel or approved BS
  route for browser access.
- BS1069 must remain stopped. Do not run active-active against shared NFS.

### Rollback

Pause intake, set `NIPT_ALLOW_HEAVY_RUN=false`, stop BS10610 Compose without
`-v`, and select the retained `niptpro:1.0.11` profile. Do not delete or alter
`nipt_analysis_test_net`, PostgreSQL/Redis volumes, workdirs, logs, results,
FASTQ, workflow sources, or image archives.
## 2026-08-12 T131 WGS cloud orchestration Phase 1

Goal: implement and deploy the WGS data orchestration/monitoring layer while
keeping the evolving biological workflow and real cloud execution disabled.

Completed:
- Implemented batch/fq-path create, immutable symlink-target snapshot,
  Airflow-owned sampleinfo/config/MD5, needs-review and revalidation.
- Added migration 0008, full transfer progress/spool ingestion, singleton OBS
  lease, Rule timing/ETA and enriched APIs/UI.
- Replaced the CCE placeholder DAG with the fixed project graph, TaskGroups,
  six reschedule sensors and pools 2/1/4. Mock adapters are double-gated.
- Built backend/frontend release-layer images on BS10610, migrated biodemo and
  recreated application services without deleting volumes or network.

Validation on BS10610:
- backend focused pytest: 23 passed;
- runtime DAG contract/import: PASS, 27 nodes, six reschedule sensors;
- temporary PostgreSQL full migration 0001->0008: passed; production
  0007->0008: passed;
- frontend focused tests: 7 passed; `tsc -b && vite build`: passed; T131 nginx
  image is running;
- Compose config: passed; network `192.168.199.0/24`, gateway `.1`, only
  frontend `12959` published;
- `/api/health`: ok; Airflow import errors: none; all three WGS DAGs paused;
- synthetic API smoke `WGS_20260812_152720_643D8D`: input manifest,
  sampleinfo and config generated; submit HTTP 409; no real CCE/OBS work.

Incident/fix:
- First application recreation failed for backend because read-only `/config`
  overlapped a writable `/config/wgs-bindings` submount. Moved only the
  container mountpoint to `/data/wgs-bindings`; host directory stayed the same.
  Backend/frontend then started and health passed.
- BS10610 could not resolve its configured Docker Hub mirror for the missing
  Node builder. Frontend code was focused-tested and built, then BS10610 built
  a runtime layer from its existing T130 nginx image plus the verified dist.

Remaining Phase 2:
- Copy/pin the then-accepted `/project/wgs` snapshot and implement restricted
  node005 OBS plus BS10610 kubectl/CCE adapters, final logger/result contracts,
  and real failure/concurrency acceptance before enabling either gate.

Rollback: atomically repoint `current` to the previous release and recreate
application services without `-v`. Migration 0008 is additive. Do not delete
the external network, DB/Redis volumes, source workflows, FASTQ, evidence,
results, bindings or transfer spool.
