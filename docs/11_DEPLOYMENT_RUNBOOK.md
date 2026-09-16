# Deployment runbook

## GATK logger settings and proxy verification (2026-09-17)

Latest GATK private effective Compose is gatk-logger924-r2-20260917-control on
both hosts (under candidates on BS10610). It preserves the existing application
source and WGS gates; do not restore an older full Compose merely to change GATK.
After backend recreation, run nginx -t and graceful reload, then check actual
gateway /api/health and an empty-JSON /api/auth/login request (expected422).
HTML or backend-direct health alone will miss nginx caching a retired backend IP.
See [exact settings and rollback](releases/GATK_LOGGER_20260917.md).

## 2026-09-17 WGS sampleinfo/v2 follow-up

Production runs the complete f72a12e backend source, with user-approved
WGS_CONTRACT_V2_ENABLED=true for new WGS tasks. The former false value was legacy
configuration, not evidence that v2 code was absent. Existing tasks retain their
frozen version. See latest HANDOFF and sampleinfo-f72a12e-control private Compose
for exact service restart/rollback scope. Do not disable v2 after new v2 runs
have started without considering their continuation. No native prepare changes.

## 2026-09-17 Clinical release executed

The Git-first checkpoint below is superseded by the approved e9a6644 production
rollout. Use docs/releases/2026-09-17-clinical-roots-bs96.md for exact source,
five-service Compose/rollback, root configuration, data copies and SFS outcomes.
No legacy-root compatibility was added; existing historical frozen request files
were not rewritten. Native prepare defaults and CCE release pins remain intact.

## 2026-09-17 Git-first checkpoint; release not performed

The user requested source synchronization before the remaining production work.
Future complete release must include wgs_release_runtime.py beside the WGS gate,
retain private release runtime/config/profile pins, and preserve existing resume
and test gates. Do not replace the gate with an older live snapshot or add backend
file-overlay mounts. CCE packages/versions are not upgraded by this source sync.
Pending and exact two GATK result copies, Clinical roots, scanner configuration
and verified WGS/GATK SFS cleanup remain pending. No offline/OBS/FASTQ/DB deletion.
Use the latest HANDOFF inventory and refresh live mounts/gates before publishing.

## Latest BS10610 test composition (2026-09-15)

Main359df11 is deployed to all eight running application/DAG/probe/collector
services through `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/
main-359df11-control/compose.json` (join the line; private0600). Actual code
mounts use releases/20260915-main-359df11. Historical current symlink remains
old and is not the active application source. Preserve environment/config/data
mounts, external network, PostgreSQL/Redis and scanfalse/autofalse. Existing
schema0024 is additive and not downgraded during rollback. Use explicit service
names and --no-deps --pull never, never remove-orphans. See
releases/2026-09-15-main-bs10610.md for exact receipt and rollback.json command.

## Latest96 UI composition (2026-09-15)

UI93069eb now supplies backend/observer/frontend through ctapa-private
/data/airflow-WGS/candidates/ui-93069eb-control/compose.json.
Its rollback.json restores only those three services to platform-f69c577.
Airflow API/scheduler/worker still use the preceding f69c577 DAG composition;
do not run generic current or recreate all services to align them.
Use explicit service names with --no-deps --pull never; retain protected services,
environment and data. Health/static/source parity passed,0911A untouched.
See releases/2026-09-15-ui-bs96.md. This supersedes the three app services below,
not the retained DAG/runtime gates or deferred recovery restrictions.

## Current96 application composition (2026-09-15)

Sourcef69c577 is deployed for backend/observer/frontend and bio_wgs only; retained
GATK/common/config and other-service mounts remain pinned. Use ctapa's private
`/data/airflow-WGS/candidates/platform-f69c577-control/compose.json`, not the old
current symlink or a generic mainline Compose. Its rollback.json captures exact
previous six-service images/environment/mounts. Use explicit service names with
`up -d --no-deps --pull never`; never remove orphans. See
releases/2026-09-15-platform-bs96.md. Runtime gates/packages and contractv2 remain
unchanged/disabled; this application rollout does not make old v1 runs compatible
with resume_stage. User explicitly deferred0911A, including recovery operations.

## WGS resume_stage packaging (2026-09-15, not deployed)

Future approved rollout must include backend wgs_resume_service.py, updated
bio_wgs DAG and frontend assets. Install scripts/wgs_resume.py beside the existing
restricted wgs_runtime_gate.py under the same owner/mode/launcher; no original
bundle, native workflow, CCE package or cluster settings are upgraded. Preserve
old gates/releases for rollback and do not restart running executors merely to
change their stage generation. Source0.8.4 compatibility inspection is not live
production acceptance. Validate the actual frozen bundle in a separately approved
production task before executing recovery. No real0911A resume was performed.
Detailed evidence and rollback: releases/2026-09-15-wgs-resume-stage.md.
## CCE 0.8.5 release-management enablement prerequisite (not deployed)

Keep `WGS_RELEASE_MANAGEMENT_ENABLED=false` until a separately authorized
deployment provisions a writable catalog directory and points
`WGS_RELEASE_CATALOG_PATH` at the catalog inside it. Do not chmod or remount the
current read-only `/config`. The same catalog directory must be visible to every
consumer: backend writer plus worker/observer readers. Mount the parent directory,
not the single YAML file, because atomic replacement is not visible through an
old file bind mount. Retain `AUTH_REQUIRED=true` and the existing private internal
service token; never place that token in the receipt or catalog.

Before a future enablement, verify the directory owner/group/mode, sibling lock
creation, atomic replacement visibility from every consumer, schema-3/4 readback,
and keep the feature flag false until those checks pass. Registration accepts a
producer-attested `PASS` receipt; it is not evidence that a node200 wheel was
installed or that a fresh Kubernetes probe ran. Explicit activation changes only
the catalog current pointer and does not enable execution or configuration gates.

An inactive catalog does not make in-place SFS asset replacement safe. Retaining
old releases requires new frozen profile and asset paths, while the existing
active-Master gate remains mandatory. No replace/delete manifest, old-asset
cleanup, package installation, mount change, production activation, or analysis
submission is authorized by this source release. Rollback disables the flag and
restores the prior catalog bytes; retain all release assets and run evidence.

## REL-02 local WGS process timezone (not deployed)

On an explicitly selected96/97 target, the approved local gate initializes
Asia/Shanghai for itself and inherited workers. Its POSIX runtime requires the
host timezone database to provide Asia/Shanghai. Keep system timezone and UTC
receipt/API timestamps unchanged. Do not use timedatectl or change /etc/localtime.

For an authorized direct invocation of original prepare outside the gate, prefix
the existing approved Python command with `TZ=Asia/Shanghai`; retain the exact
original script path and arguments. This is a shell process environment prefix,
not a new prepare argument. Do not generate projects on18 (jump only exceptqsub).
Cloud preparation remains on200; this change neither moves it nor modifies its gate.

User requested no publication: installing this gate on96/97 still requires a
separate rollout and fresh target/identity/active-worker check. No existing worker
needs restarting to change future-launch behavior. Verify a non-workflow clock
probe on the actual selected host before enabling new work; no full prepare or
pending mutation is an acceptance test. Restore the previous gate for rollback.


## Resource response compression (2026-09-15)

Both nginx templates enable gzip only for exact `/api/platform/resources`
responses (JSON, minimum 1024 bytes, level 5, Vary: Accept-Encoding). Auth and
other API routes are unchanged. This does not cache or downsample telemetry.
For an existing gateway, preserve its approved allowlist and apply only this
location block; do not overwrite a live config with a generic template.
Validate `nginx -t` before graceful reload. Frontend assets must be copied before
switching index.html; retain the previous index/assets for rollback. Backend,
collectors, scanner and Airflow need no restart. See the dated resource loading
release note for exact deployment evidence.

## GATK recovery/Step7 candidate (2026-09-14)

Validate the candidate on BS10610 before production. Deploy bio_gatk.py network
polling retries and the independent bio_gatk_maintenance.py to all three Airflow
services. Inspect actual per-file mounts; replacing a host inode alone does not
replace the file already bind-mounted in a running container. Check no executing
Airflow task before a scoped control-plane recreation; retain CCE Masters and
all task/run identities. Existing rescheduled TaskInstances may retain old
max_tries: inspect them and clear only the exact wait task if needed, never
upload/prepare/Master submission just to adopt a polling retry policy.

Backend and observer must consume the same tested registry/reconciliation code.
The observer's GATK overlay sets DEPLOYED_PIPELINES=wgs,gatk explicitly; its
Airflow synchronizer requires DB/Airflow access, not a new GATK filesystem mount.
Install gatk_maintenance_gate.py adjacent to the restricted gatk_runtime_gate.py;
preserve private runtime.env, SSH identity and existing execution gates. Verify
the external forced-command dispatcher accepts the authorized Step7 invocation.

Step7 is an explicit administrator maintenance action, not an ALL_DONE analysis
tail and not a deployment smoke-test deletion. Its approved identity/hashes,
latest Step5/6 receipts, no-live-workload checks and shared maintenance lock must
pass. Unknown runtime status blocks retry; retain local results/OBS/evidence.

For0823A use scripts/gatk_resume.py first without --execute, with freshly read
binding/contract SHA256 and exact failed Master UID. Validate raw Kubernetes
DeleteOptions preconditions against an owned diagnostic Job before execution.
Preserve attempt/workdir/run-id/frozen versions and successful outputs. Never
use Step0, --forceall, arbitrary unlock or an unverified replacement UID.
Record exact runtime and control-plane recovery separately from batch completion.

Rollback restores recorded service source/images and node gate copies only.
Preserve databases, leases, runtime receipts, diagnostic evidence and outputs;
do not roll back a resumed Master by deleting it.

## 2026-09-14 original-file ledger / compact controls

Git promotion does not deploy services. BS96 currently uses backend/source worker
from /data/airflow-WGS/releases/20260914-ledger-c2e491c and frontend controls-20260914.
Use that release/private/compose.json with compose.controls.json for frontend;
the current symlink alone is not the actual service composition. Never remove
orphans. Source registration and identity secret stay server-private, not in Git.
Worker: python -m app.sample_reference_worker; SAMPLE_REFERENCE_ENABLED defaults
false, SAMPLE_REFERENCE_SOURCES_FILE names operator registration, and
SAMPLE_REFERENCE_IDENTITY_SECRET must be stable and private. Only wgs_files is
approved, using registered project_root and optional runtime_root. Polling is
one pass plus60s; no public registration or write endpoint. Preserve scan/dispatch.
See releases/WGS_LEDGER_BS96_20260914.md and UI_CONTROLS_BS96_20260914.md.
Do not restart backend during active GATK waits: outage tolerance/recovery is
deferred. Rollback retains all files, schema and rows. Future formal path reset
requires separate explicit authority.

## GATK terminal transfer recovery (2026-09-14)

After BS10610 targeted backend and DAG tests, compare actual mounted backend
gatk_runtime_service.py/wgs_observer.py and bio_gatk.py against the exact patch.
Check zero executing Airflow tasks; restart only backend to load its GATK
evidence reader, preserving the separate WGS observer release and cloud Masters.
For a prior stuck transfer, call the existing authenticated GATK stage-status
endpoint for its exact attempt/Step1 or Step5. The handler validates latest
receipt identity and repairs/releases idempotently; do not directly update DB
or forcibly clear a lease. Verify successor acquisition and actual upload start.
Rollback copies retained .pre-transfer-terminal-20260914 bytes back to the same
mounted files and reloads backend; retain all receipts, transfer rows and data.

### AF05 scan-only overlay (2026-09-13)

BS96 scanner/backend/frontend use release2121061 with `compose.af05.json`;
BS10610 backend/frontend use the same source with scanner disabled. Existing
current symlinks are not sufficient to recreate these services. Use private
`candidates/af05-scan-20260913/command.json` for the exact Compose file set.
Scanner-only `/af05-config/source.json` fixes discovery to Target_Capture and
does not alter WGS prepare defaults. Keep auto dispatch false. Preserve source
identity path and baseline records on future releases; do not replay old files.
Schema0021 includes inactive0020 prerequisites. Code-only rollback retains the
additive schema/data and disables scan; do not downgrade/drop reference or intake
tables. See [AF05 release ledger](releases/AF05_SCAN_ONLY_20260913.md).

### OPT20260912 retained-gate catalog guard

Keep `WGS_CONFIG_OPTIONS_ENABLED=false` and
`WGS_CONFIG_OPTIONS_RUNTIME_CONTRACT=` in the current candidate deployment.
Compose forwards both to backend, defaulting false/empty. The retained private
node gate lacks the new caller/effective-configuration contract; owner source
drift is not repaired by this release. `WGS_TEST_PROJECT_ENABLED=false` alone
does not guard ordinary catalog overrides.

Only a separately verified paired runtime/owner rollout may declare
`WGS_CONFIG_OPTIONS_RUNTIME_CONTRACT=wgs-submission-options.v1` and enable
`WGS_CONFIG_OPTIONS_ENABLED=true`. Setting the flag alone is insufficient.
This is an explicit operator compatibility declaration, not observed runtime
identity. No node gate, owner, live environment or service change is performed
by the activation-guard patch. Legacy requests without overrides and existing
stored submissions remain usable.

## OPT20260912 test resource producers

Deploy only after current test preflight/review. Do not replace the production
`/home/ctapa/.config/airflow-wgs` launcher or existing SFS Cloud Eye process.
Private test root is `/home/ctapa/.config/airflow-wgs-test` (owner ctapa,0700).
Install script files0700 from the exact reviewed commit:

| Repository file | Private test filename |
| --- | --- |
| scripts/heavy_global_snapshot.py | heavy_global_snapshot.py |
| backend/app/heavy_global_snapshot.py | heavy_snapshot_core.py |
| scripts/start_heavy_slot_collector.sh | start_heavy_slot_collector.sh |
| scripts/collect_bss_resources.py | collect_bss_resources.py |
| backend/app/bss_resource_snapshot.py | bss_resource_snapshot.py |
| scripts/start_bss_resource_collector.sh | start_bss_resource_collector.sh |

Use `config/resource_collectors.test.env.example` as a non-secret variable map.
Export the reviewed variables (`set -a; source <private collector env>; set +a`)
before invoking a launcher; do not overwrite the existing runtime.env.
Required Heavy variables: HEAVY_COLLECTOR_CONFIG_ROOT, WGS_PYTHON,
CCE_OPERATOR_CONFIG, HEAVY_EVIDENCE_ROOT. BSS requires BSS_COLLECTOR_CONFIG_ROOT,
WGS_PYTHON, BSS_EVIDENCE_ROOT. Launchers use flock; no boot service is installed.
Node backend source/collector validation code must match the same commit.

Dedicated BSS credentials are currently **not configured/authorized**. Leave
BSS_READONLY_CREDENTIALS unset; `collect_bss_resources.py --root <test evidence>
--once` publishes not_configured without loading SDK or making a request.
For future separately approved activation, provide an owner-only0600 JSON in
an owner-only0700 directory containing exactly ak, sk, domain_id and
purpose=billing_readonly. Identity requires billing:resourcePackages:view.
Never reuse Cloud Eye regional credentials or copy keys into Git/spool/images.
No endpoint override is supported; HTTPS global bss.myhuaweicloud.com only,
no redirects or environment proxy/netrc forwarding. SDK GlobalCredentials uses
explicit domain and signs only three read-only official routes, never IAM
auto-discovery. The package query covers the official default account scope;
it does not claim enterprise-project aggregation outside that API scope.

Root validation: invoke Heavy `--config <existing private CCE config> --root
<test evidence> --once`; this only queries Leases/Masters and writes telemetry.
Verify actual spool/API field states; do not label enforcement tested.
Start separate launchers only after reviewed install. Preserve SFS producer,
private runtime.env, workloads and scan/dispatchfalse. Backend needs only the
existing read-only evidence mount. Rollback exact collector files/owned process
and application release, retain telemetry/evidence; never reclaim/delete quota.

## OPT20260912 test submission rollout

After fresh BS10610 active-state preflight, deploy matching backend/frontend and
the standalone test node gate. Backend Compose now forwards
`WGS_TEST_PROJECT_ENABLED` (false by default). Test-only activation requires
`PLATFORM_ENVIRONMENT=BS10610-Test` (existing display label; `test` is also
accepted for isolated tests) and `WGS_TEST_PROJECT_ENABLED=true` in backend and
the existing `/home/ctapa/.config/airflow-wgs-test/runtime.env`; retain its test
runtime/request roots and all existing execution gates. Never set these in the
production node gate. Keep scanner/dispatch unchanged.

Review fix requires runtime/root-owned output ancestors and sticky protection
on group-writable parents. The current test WGS_test2770 directory fails closed;
an exact2770→3770 change requires separate user approval and is not performed by
the gate. New target/namespace directories are private0700 with no-follow inode
markers and portable atomic mkdir/flock (compatible with node glibc2.17; no
renameat2 dependency). A mkdir/marker crash gap requires manual audit recovery,
never automatic adoption. Audited prepare/template hashes are verified before
private snapshotting; a changed live configuration needs a reviewed contract.

Backend needs same-path read-only /sg2 and /bi visibility already supplied by
the current test deployment. Do not grant backend write access or silently
change mounts. Node ctapa checks write permission on the requested output's
existing parent; missing/unwritable parents fail explicitly without fallback.
The observer consumes unchanged receipt schemas and needs no new test-mode
environment value or new producer; normal source-version coordination applies.
No Airflow DAG/schema migration is required. Rollback disables the test flag
and restores backend/frontend/test gate; retain drafts, run records and output
for audit. Never rollback by deleting a project or touching formal pending.

## GATK selective promotion, 2026-09-12

Use `docker-compose.gatk.yaml` as an optional overlay on the verified WGS
Compose contract. Configure independent `GATK_RUNTIME_HOST_ROOT`,
`GATK_RUNTIME_NODE200_ROOT`, `GATK_EVIDENCE_HOST_ROOT`, `GATK_RESULT_ROOT`,
`GATK_REPOSITORY_ROOT`, `GATK_OPERATOR_CONFIG` and restricted runner command.
`GATK_SOURCE_POLICY` is restricted by default; this user-approved release sets
unrestricted for explicit valid input projects, never for writable outputs.
`GATK_EXECUTION_ENABLED` remains false until profile, gate, mounts, permissions,
API and DAG import acceptance. GATK inherits global active-run concurrency and
Step2 uses default_pool; no dedicated GATK one-slot pool is required.
Unpause `bio_gatk` at final manual activation. Preserve WGS scan/dispatch.

### GATK concurrency update (2026-09-14)

First run `dags/tests/test_gatk_concurrency.py` in cached BS10610 Airflow using
`/usr/local/bin/python` and fresh processes with global defaults16 and7; run
`test_gatk_success_dependencies.py` too. Do not use the Snakemake venv Python.
Before authorized production switch, verify API-wide running task count is0,
global default, actual DAG mounts, OBS pools both1, and existing Master UID.
Patch only the two concurrency declarations in the actual mounted DAG with
old-content hash guard and retained rollback bytes. Individually bind-mounted
files require preserving inode; do not replace their parent symlink or restart
workers/Masters. Confirm scheduler-parsed DAG reports16 and queued run advances.
Retain OBS pools, durable leases, scan/dispatch settings and all run state.
Rollback restores prior bytes only after another zero-running-task check;
it does not stop existing external workloads or delete any state.

Production may reuse the verified `wgs-node200` SSH host alias with the separate
GATK forced-command path; this avoids editing WGS SSH keys/configuration. The
test environment continues its own `gatk-node200` alias and `airflow-gatk-test`
private directory. No test credentials, results or runtime are promoted.

The normal production clone is `D:/pipeline/airflow-demo-production`.
New development worktrees must branch from the published production main,
inherit research documents and run runtime tests only on BS10610. Original
dirty repositories and historical test refs are retained, not merged wholesale.
See `docs/releases/GATK_PROMOTION_20260912.md` for actual completion and rollback.

For the user-approved 2026-09-11 non-Git exact-source selection/refresh patch, use [release evidence and rollback](selection-refresh-20260911.md). Only backend/observer restarted; frontend updated hashed assets then atomic index; current Worker/scanner/Master must remain untouched. WGS prepare source writable alias verified on BS10610, not node200's read-only /bi mount. No environment variables or public ports added.

Environment selection, host aliases, directory ownership and image-retention
rules are authoritative in `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`.
Dated release sections below are historical evidence. They must not override a
fresh `ssh BS10610` or `ssh BS96` preflight.

## T240 rollout boundary

T240 changes backend projections and frontend presentation only. Validate the
backend through the approved cached image and build the frontend with the T234
offline builder. A production rollout may reuse the currently approved backend
image because application source is bind-mounted, then recreate only `backend`
and `frontend-nginx`. Do not recreate the scanner, observer, Airflow,
PostgreSQL, Redis or telemetry services.

The production environment must retain `WGS_AUTO_DISPATCH_ENABLED=false` in
both backend and scanner. The 30-minute discovery scanner remains enabled and
unchanged. This rollout does not submit a run, retry Step7, release SFS data,
rewrite sample/rule history or migrate the database.

The 2026-09-09 production release is
`/data/airflow-WGS/releases/20260909-t240-dashboard-attention-r1`. Its
`PRODUCTION_COMPOSE_BASE` marker records the approved T239 WGS Compose contract
used for the application-only rollout. Do not satisfy the later mainline
`GATK_RUNTIME_HOST_ROOT` interpolation by inventing a dummy mount: GATK runtime
is outside this WGS release and remains disabled. Only backend and
frontend-nginx are recreated for T240.

## Identity and location

- Project: `ngs-huaweicloud`
- Candidate root: `/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud`
- Production account and secrets are external to Git.

## Offline image policy

Production hosts must not contact Docker Hub. Use an approved cached base image or the internal image registry. The backend uses `python:3.11.9-slim-bookworm`; on BS10610 this short name is tagged locally from the already cached equivalent image before building with `--pull=false`. Never run `docker pull` as part of acceptance.

### Frontend builder bootstrap

The approved T234 builder is:

```text
airflow-demo/frontend-builder:node22-lock-35420d5e3ec0
image ID: sha256:25e83a56052d63d900e253c618d342679bb46b66e4566390fa52eb3233702fdf
package-lock SHA256: 35420d5e3ec0f9555738f61e983cb05de30640db82f034d2659f87fd40a324b1
archive SHA256: b5df43b3e26748d08580464832f7688fa36d67c6b2eb12fe681ce57b7dfde1cc
```

It is already loaded on BS10610 and production `.96`. Do not move a complete
frontend image from fengxian for an ordinary source-only release. From a
candidate release on BS10610 run:

```bash
FRONTEND_SOURCE_COMMIT=<git-sha> \
  scripts/build_frontend_offline.sh airflow-demo/frontend:<release-tag>
```

Each host first binds its approved gateway to the same host-local alias:

```bash
docker tag <approved-current-frontend-image> \
  airflow-demo/frontend-runtime:nginx-1.30.3-local-contract

FRONTEND_SOURCE_COMMIT=<git-sha> \
  scripts/build_frontend_offline.sh airflow-demo/frontend:<release-tag>
```

The script tests and builds with `--network none --pull=false`, and writes
`.build/frontend-offline/frontend-image-provenance.json`. A lock mismatch is a
hard stop. Rebuild the base with `scripts/build_frontend_builder_base.sh` on an
approved connected builder only when `package-lock.json`, Node major or the
approved Node base changes. Export one tar plus provenance and SHA256, relay it
through the local workstation, and load it independently on each target.

## Network policy

Compose joins an existing external network named by `NGS_PLATFORM_NETWORK`. This repository does not create the network, assign its subnet, or open additional ports during validation. Use `--network none` for tests that do not need services.

## Candidate validation

1. Synchronize source to the candidate root without secrets, `.git`, or local dependency caches.
2. Run backend tests in a clean image derived from the approved cached Python base.
3. Run DAG import/contract checks.
4. Run frontend tests and production build using the approved cached Node image.
5. Render Compose configuration without starting services.
6. Run an isolated migration upgrade against a disposable database.
7. Record exact commands and results in `HANDOFF.md`.

Production deployment and restart require separate approval. Candidate validation must not connect to the running CCE task path.

## T227 production runtime requirement

The node200 restricted runtime must define:

```text
WGS_RUNTIME_RUN_ROOT=/sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime/runs
```

Deploy the T227 runtime gate and environment without stopping an active
Step1-Step6 worker. Apply migration `20260908_0018` before exposing the Step7
retry UI, then restart only backend/observer/frontend components required by
the release. Do not restart Airflow scheduler/worker or release an active OBS
lease. Restore failed Step7 generations only after exact target, CCE workload,
and lease identity checks; an absent target may be recorded as
`verified_absent`, while partial or ambiguous remnants remain failed.

## T239 lifecycle/QC frontend and Step7 projection rollout

1. Confirm `WGS_AUTO_DISPATCH_ENABLED=false`, no active AnalysisRun, no active transfer lease and no live CCE workload before switching the release.
2. Build the frontend with the approved lock-bound builder using `--network none` and `--pull=false`; run the targeted backend lifecycle/workspace/Step7 tests and logger tests from the candidate source.
3. Recreate only backend and frontend-nginx. Do not recreate the scanner, observer, Airflow scheduler/worker/API, PostgreSQL, Redis or telemetry services.
4. Verify `/api/health`, `/workflows` static markers, workspace `batch_qc_status`, workflow operator and Step7 eligibility for a completed WGS batch.
5. Do not invoke Step7 as part of deployment. The button only exposes an administrator action that still performs the runtime target, live CCE and lock checks.

Rollback by repointing `current` to the preceding physical release and recreating only backend and frontend-nginx. Preserve the auto-analysis pause, databases, run evidence, OBS/SFS data and all Airflow state.

## T241 obsutil checkpoint rollout

1. Keep `WGS_AUTO_DISPATCH_ENABLED=false` and confirm zero active
   AnalysisRuns, transfer leases and WGS CCE workloads before changing the
   node200 operator configuration. Preserve the existing `bio_wgs` pause state;
   the current production DAG remains available for explicit manual runs.
2. Store all synthetic validation material below
   `/sg2/50.ctapa/project/HWcloud/WGS_test/cce-evidence/T241-obsutil-checkpoint-20260909`.
   Do not use another user's test tree or write evidence below `/tmp`.
3. Run the bounded two-file upload/download canary with the private-line
   `obsutil` identity. Require exact aggregate bytes, observed multipart
   checkpoints, checksum verification, privacy-safe JSON and verified removal
   of both synthetic remote objects.
4. Atomically back up and replace node200
   `wgs_obsutil_progress.py` and `wgs_runtime_gate.py`, then run
   `configure_node200_cce.py` so `obs.transfer_adapter=obsutil` and
   `obs.obsutil_bin` selects the wrapper. No cce-pipeline package or
   Step2/Step3/Step4/Step6 implementation changes are required.

## GATK Cloud disabled rollout

1. Keep `GATK_EXECUTION_ENABLED=false` while applying migration 0019 and
   deploying backend, Airflow and frontend.
2. Install the GATK forced command and runtime gate below the restricted SSH
   account's `.config/airflow-gatk` directory. The wrapper resolves
   `runtime.env` and `gatk_runtime_gate.py` relative to its installed path.
   Create `runtime.env` from
   `config/gatk_runtime.node200.env.example`, add no secrets to the repository,
   and set mode 0600.
3. Verify the GATK repository is exactly the approved release and the pinned
   Master image provides the `rule-status` logger contract.
4. Verify the backend has same-path read-only mounts for every approved FASTQ
   root. The initial deployment requires both `/sg2/T7new/result1/OutputFq`
   and `/bi/fastq/T7_Fastq` because existing `a.raw` links use both spellings.
5. Run preview/prepare, CCE dry-run and logger smoke before any real transfer.
6. Execute one controlled SCMC Step1-Step6 smoke. Confirm source FASTQ hashes,
   terminal rule evidence and the materialized result root.
7. Enable manual confirmation only after the smoke passes. Do not enable an
   intake profile; none exists for GATK v1.

To rollback, set the gate false and recreate only affected control-plane
services. Preserve database/evidence/result state for diagnosis.
# 2026-09-14 Heavy producer compatibility

Keep node200 `/home/ctapa/.config/airflow-wgs/heavy_global_snapshot.py` aligned
with `backend/app/heavy_global_snapshot.py`. Backend-only deployment does not
update this standalone producer. Restart only the verified collector under its
existing lock; validate at least two fresh snapshots. Preserve its code backup.
Do not restart Masters or alter quota Leases to repair telemetry.
