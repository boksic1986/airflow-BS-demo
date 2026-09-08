# Security and operations boundaries

## Platform scope

`ngs-huaweicloud` is a general NGS control plane. Shared services discover
pipelines through `config/pipelines.yaml` and call registered adapter
capabilities. A deployment may enable WGS, WES, GATK, or another reviewed
adapter without adding pipeline-name branches to shared authentication,
navigation, run, sample, workflow, or capability endpoints.

The current production configuration deploys only WGS. WGS Step1-Step7,
execution-choice, evidence, directional transfer leases, Heavy Slot and
QCstat behavior remain WGS extension contracts and do not grant equivalent
authority to future adapters.

## Authentication and audit

- Capability discovery and all operational APIs require authentication.
- Submit and reanalysis require operator access. Account and lifecycle status
  changes require administrator access where documented.
- Adapter submit and reanalysis hooks must check their deployment/runtime
  execution gates before changing an attempt or calling Airflow.
- Audit records keep the original account identity even when the UI uses a
  friendlier display name.
- Registry validation fails closed for unknown adapters, malformed types,
  disabled deployments, unsupported capabilities, and unknown execution
  targets.

## Secrets and privacy

Never commit or publish:

```text
.env
private keys
password or token files
SMTP/database/Airflow credentials
OBS credentials or bucket/object identities
kubeconfig
patient names, hospitals or clinical identifiers
```

Production credentials remain owner-only and outside release trees and Docker
images. The browser never supplies a repository path, executable, shell
command, profile path, storage path, credential, or Kubernetes identity.
Public logs and artifacts use controlled keys and privacy-safe relative paths;
they never fall back to arbitrary host paths.

## Filesystem and execution authority

- The active project root is `/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud`.
- Runtime adapters accept only registered `analysis_id + attempt + stage`
  identities and fixed server-side allowlists.
- FASTQ roots and analysis roots are separate configured authorities. Do not
  broaden either to `/sg2` or infer a sibling path.
- Workflow evidence is immutable/replayable. The observer validates attempt,
  generation, request hash and receipt identity before database projection.
- CCE, local-node and future SGE credentials are isolated by adapter and
  execution target. A capability declaration alone does not enable execution.
- Step7 deletes only the frozen WGS SFS analysis/linkage scope and never OBS
  input data or retained evidence.

## Docker and network

- Production Compose attaches to an existing external network supplied by
  `NGS_PLATFORM_NETWORK`; the repository does not prescribe, create, delete,
  recreate, or repair a subnet.
- Only explicitly approved frontend ports may be published. Backend, Airflow,
  PostgreSQL, Redis, observers and collectors remain internal.
- Docker socket access is host-equivalent privilege and is limited to reviewed
  services.
- Candidate verification uses `--network none` wherever possible. A disposable
  database may use the default bridge or container network namespace and must
  be removed after migration testing.
- Restricted servers must build from preloaded, approved images with
  `--pull=false`. Current backend validation uses the locally cached
  `python:3.11.9-slim-bookworm`; no Docker Hub access is required.
- Frontend source releases use the preloaded lockfile-bound Node builder and a
  host-local nginx runtime contract. Target-host builds use `--network none`
  and never run `docker pull` or `npm ci`. Builder archives move only through
  the approved local relay with SHA256 verification at every hop.
- Never run volume/system prune or `docker compose down -v` as part of a
  release.

## Current WGS extension boundaries

- Automatic intake selects CCE only and respects activation watermark and
  batch/attempt deduplication.
- CCE Step1 commit freezes the execution target. Local node97 is manual and
  gated; node96 and SGE remain unavailable until separately accepted.
- Upload and download use independent, direction-specific leases. Ownership
  does not expire on a fixed TTL; a matching terminal receipt is required for
  release.
- Step1-Step6 hand off atomic files/receipts from remote systems. The observer
  projects verified state into PostgreSQL, which is the UI source of truth.
- `wait_step6_materialize` must succeed before `finalize_run`.
- Cloud release, raw FASTQ backup and result delivery are independent lifecycle
  states and do not overwrite workflow success.
- Cloud Eye and node metrics contain numeric measurements and timestamps only.
  Missing or stale evidence is displayed as unavailable/degraded, never
  fabricated.

## Backup, recovery and cleanup

- Business database dumps and controlled evidence are recovery assets; raw
  FASTQ backup is a separate lifecycle operation.
- Reanalysis defaults to resume/rerun-failed semantics. Never default to
  `--forceall`.
- Cleanup operations must resolve exact targets, preserve audit/evidence roots,
  and report terminal state. Production data deletion requires explicit user
  authority and a reviewed target list.
- A source-only release rolls back by reverting the integration commit. A
  runtime release uses its documented immutable release pointer and does not
  recreate databases, volumes, networks, or active CCE jobs.
