# Deployment runbook

Environment selection, host aliases, directory ownership and image-retention
rules are authoritative in `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`.
Dated release sections below are historical evidence. They must not override a
fresh `ssh BS10610` or `ssh BS96` preflight.
## T248 retained-baseline recovery and automatic run

Before retention cleanup, create Airflow and biodemo dumps below an explicit
task evidence directory. Storage cleanup may target only approved SFS and OBS
test prefixes. It must never remove the T7 source FASTQ root or any directory
under the production WGS project-analysis root. Use exact guarded database
transactions and inventory the post-delete retained rows before enabling the
scanner.

For WGS 4.2.0, node200 uses nipttest `cce-pipeline 0.8.3`. MongoDB 4.0 requires
a compatible client; the validated nipttest runtime uses PyMongo 4.9.2. Do not
use this compatibility requirement as authorization to modify or revalidate
pipeline source.

Automatic submissions must run `prepare_sampleinfo` and `prepare_analysis`,
preserve `submission_phase=approved`, and commit execution before Step1. The
generated operator config must omit legacy OBS SDK-only fields because Step1
and Step5 use obsutil. If a failed earlier attempt left an unbound analysis
directory, retain it intact below the new attempt's `history/prepare_analysis`
tree before regeneration; never delete it.

When an obsutil command flattens a transfer-plan directory prefix, the wrapper
may use a unique basename match to emit the same SHA-256 file key. Ambiguous
basenames fail closed to aggregate-only progress. After rollout, verify a
subsequent batch creates file-level rows, not only aggregate bytes.

Enable scanning only after obsolete source directories are listed in
`WGS_INTAKE_IGNORED_CHIP_IDS`. The approved production interval is 1800
seconds. Verify one upload lease, no duplicate dispatch, and no more than 25
Heavy Slots. Monitor each approved analysis through Step6 and stop on an
unresolved execution/evidence mismatch.

## T242 WGS 4.2 activation

Activate only with zero active WGS runs and transfer leases. Keep automatic
dispatch disabled, preserve the 4.1.1 release mapping, and select the validated
nipttest cce-pipeline 0.8.3. Production results remain under the ctapa
WGS_Clinical root. Do not use Step7 or Step8 as an activation probe.

Runtime execution does not invoke Git and does not revalidate pipeline/profile
contents; release replacement and its published evidence are operator-owned.
The gate verifies only that the configured cce-pipeline executable exists and
reports the run-bound adapter version. Existing historical frozen bindings are
reusable, but historical reprepare without a binding is rejected.
## BS10610 test endpoint

BS10610 (`server10610`) is the dedicated test deployment. Its user-facing
frontend endpoint is `http://172.17.106.10:12959`. The address is bound to the
host interface `172.17.106.10/24`; do not shorten it to `172.10.106.10` and do
not use the production `.96` endpoint when validating this environment.

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
4. Verify the backend mounts `/sg2` read-only. GATK Preview may accept projects
   owned by any team; confirmation freezes that project as the runtime request's
   only approved source root. Runtime input selection prefers
   `<batch-prefix>_hg38.sampleinfo.txt`, then the SCMC and legacy sampleinfo
   names. Source project versions may be V7.6.x-V7.7.x, while the execution
   profile remains the separately validated `gatk-scmc-v7.6.0`. Keep FASTQ
   roots read-only for runtime compatibility.
5. Run preview/prepare, CCE dry-run and logger smoke before any real transfer.
6. Execute one controlled SCMC Step1-Step6 smoke. Confirm source FASTQ hashes,
   terminal rule evidence and the materialized result root.
7. Enable manual confirmation only after the smoke passes. Do not enable an
   intake profile; none exists for GATK v1.

To rollback, set the gate false and recreate only affected control-plane
services. Preserve database/evidence/result state for diagnosis.
# GATK Step4 export wait and tail recovery

When a GATK Master is successful but Step4 reports only
`SFS backend export is not ready in OBS; retry Step4`, first verify the frozen
run identity and both OBS terminal markers. Deploy the matching backend and
node200 gate release, then clear `start_step4_publish` and its downstream tasks
for the exact DagRun. Do not clear Prepare or Step1-Step3.

The retried Step4 must register a new generation in the same attempt. Confirm
that the business run reopens from the old terminal projection, then require
Step4, Step5 download, Step6 materialization, finalize, and lease release to
finish in that order. Any different Step4 error is non-retryable and requires
diagnosis rather than another clear.
