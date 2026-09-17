# Engineering specification

## WGS deployed runtime pins recorded in source (2026-09-17)

Administrator-only WGS_RELEASE_RUNTIMES_JSON maps release ID to python,
cce_pipeline and version; WGS_RELEASE_RUNTIME_ROOT confines those executables.
WGS_RELEASE_PREPARE_CONFIGS_JSON maps release ID to config path+sha256 under
WGS_PREPARE_CONFIG_ROOT. WGS_PREPARE_CHECK_OVERRIDES_JSON maps exact release:batch
to boolean. These existing production settings are retained, not activated or
copied from test. No values/credentials belong in Git. Runtime contract: docs08.
## Native monitor switch (2026-09-15, candidate)

WGS_ONPREM_MONITOR_ENABLED defaults false in backend and the native monitor DAG.
It is independent of registration/launch gates: stopping new launches must not
require stopping an already accepted monitor. Configured INTERNAL_SERVICE_TOKEN
is mandatory for the new observer route. No new port/container/Compose mounts;
activation is not part of this checkpoint.2026-09-16 adds personal-session
idempotent monitor attachment using the existing Airflow client, no new service.

## R2-3 launch claim gate (2026-09-15, inactive)

WGS_ONPREM_LAUNCH_ENABLED defaults false, separate from project registration.
When explicitly enabled in a later approved installation, the one-shot claim API
validates the registered native inputs and consumes permission accepted→launching.
It never launches a process or marks the run started; no new service/port/lease
or database migration. Keep false until the caller and observer integration is
accepted. Lost/ambiguous claim replies must not automatically repeat a native call.

## R2-2 private execution snapshot root (2026-09-15, inactive)

WGS_ONPREM_SNAPSHOT_ROOT defaults empty. Execution registration requires an
existing0700 directory outside the mutable project, writable by backend; each
snapshot directory0700/files0600. It stores small config/sample/Step1 inputs only.
No new daemon, port, account impersonation or scheduling service. Requires existing
R2-1 registration gates and later authorized migration/permissions deployment.
Unset configuration fails closed; no fallback into the project or production root.

## R2-1 registry settings (2026-09-15, unverified candidate only)

WGS_ONPREM_REGISTRATION_ENABLED defaults false; WGS_PLATFORM_INSTANCE_ID defaults
empty; WGS_ONPREM_PROJECT_ROOTS defaults empty (comma-separated absolute roots).
All must be explicitly configured before registration. They do not enable native
execution, scanning or dispatch and are separate from WGS_NATIVE_PREPARE_ENABLED.
Existing personal sessions are reused; no new auth service or port. Suggested WGS
client private config and transport rules are in the
[registration contract](superpowers/specs/2026-09-15-wgs-onprem-registration-contract.md).
No deployed configuration was changed; candidate registration/migration/submission
checks now pass11 cases after SSH recovery, with WGS integration still pending.

## Local/SGE R2 planning status (2026-09-15)

The [R2 design](superpowers/specs/2026-09-15-wgs-local-sge-platform-integration.md)
requires optional backend-first registration and per-execution editable-input
snapshots. The flag below only describes existing unverified R1 source; it does
not provide R2 CLI registration/authentication. No service, port, credential or
environment setting is added/changed by this documentation revision.

## Native preparation rollout flag (2026-09-15, unverified source)

`WGS_NATIVE_PREPARE_ENABLED=false` by default. Explicit enablement with
`WGS_CONTRACT_V2_ENABLED=true` lets new normal catalog submissions pin the native
prepare contract; existing runs and independent test/canary paths are unchanged.
Keep disabled until Local/SGE launch/monitor integration is accepted. This flag
does not toggle scanning/auto dispatch or override any execution permission.

## CCE 0.8.5 release catalog consumer (inactive by default)

The backend consumes the exact `cce-release.v1` producer receipt and keeps
managed receipts in the same schema-4 YAML entry as each release. Registration
upgrades schema 3 to 4 while preserving historical releases and unknown root or
entry metadata. Writers serialize through a sibling Linux file lock, validate
the old and replacement catalogs, fsync a same-directory temporary file, preserve
the catalog mode, atomically replace it, and fsync the parent directory. The
catalog path comes only from `WGS_RELEASE_CATALOG_PATH`; requests cannot select a
filesystem or network target.

`WGS_RELEASE_MANAGEMENT_ENABLED` defaults false. Registration never changes the
current release; activation is a separate receipt-bound compare-and-swap. The API
attests the supplied verified receipt and deliberately does not probe CCE, install
a wheel, write SFS assets, or infer that `APPLIED` is ready. CCE recovery resolves
the attempt's recorded release with `by_id` and retains its original params even
after another candidate becomes current.

Local WGS runtime uses the fixed process environment `TZ=Asia/Shanghai` before
worker preparation and for analysis descendants. This is not a host timezone
change or a user-overridable workflow parameter. API/status timestamps retain UTC.
Deployment remains pending for REL-02; see its dated release note.

## OPT20260912 resource collection

Heavy and BSS are standalone read-only node producers. The existing backend
evidence mount reads `heavy-slot-global.json` and `bss-resources.json`; no DB
migration, public port, package installation, frontend cloud polling or SDK
import in backend is added. Separate BSS hourly collection uses node's existing
core SDK/requests, dedicated private GlobalCredentials and numeric-only spool.
Launcher environment and standalone packaging are specified in document11.
Existing SFS Cloud Eye/node producers, executor admission and Master remain unchanged.

## OPT20260912 submission

New catalog caller/configuration overrides have an independent default-off
`WGS_CONFIG_OPTIONS_ENABLED` switch and empty-default
`WGS_CONFIG_OPTIONS_RUNTIME_CONTRACT`. Activation requires both the switch and
the exact reviewed compatibility declaration `wgs-submission-options.v1`, plus
an audited release. The declaration is operator configuration, not a live probe.
The test-project switch does not activate ordinary catalog options.

`WGS_TEST_PROJECT_ENABLED` defaults false. It enables existing-project preview
and independent test submission only together with the explicit environment
allowlist `PLATFORM_ENVIRONMENT=BS10610-Test` or `test`.
Backend source access remains read-only; the restricted test node owns output
creation. No new service, public port, dependency or migration is introduced.

Manual GATK deployment may layer `docker-compose.gatk.yaml` over the verified
WGS Compose contract. GATK has separate host/node runtime, evidence, result,
repository and private operator configuration. `GATK_SOURCE_POLICY` is
restricted by default; the approved production configuration uses unrestricted
explicit input selection with read-only storage and frozen identity validation.
No new public port or service is introduced. See the deployment runbook and
GATK_PROMOTION_20260912 release ledger for active paths and gate settings.

## Repository layout

- `backend/`: FastAPI, database projections, registry, adapters, observers.
- `frontend/`: registry-driven React control plane.
- `dags/`: Airflow orchestration and workflow runners.
- `config/pipelines.yaml`: deployed pipeline registry.
- `docker-compose.wgs.yaml`: current WGS control plane composition and the
  disabled-by-default GATK Cloud adapter.
- `docs/`: current contracts plus retained historical WGS decisions.

## Registry rules

Every pipeline definition must declare a unique ID, adapter, DAG ID, deployed/submittable flags, capabilities, and execution targets. `DEPLOYED_PIPELINES` must contain registered IDs; it is deployment configuration, not a source-code allowlist.

Stable errors are:

- `404 PIPELINE_NOT_REGISTERED`
- `409 PIPELINE_NOT_AVAILABLE`
- `409 PIPELINE_CAPABILITY_UNAVAILABLE`

## Implementation rules

- Generic endpoints dispatch through the registry.
- Workflow-specific validation and projections stay in an adapter.
- New adapters must not require edits to generic navigation or shared status maps.
- Public paths are controlled relative paths or opaque artifact keys.
- Database migrations are append-only and retained even when a legacy runtime is removed.
- Production images are built from pre-approved cached or internal-registry bases; validation must not depend on Docker Hub.

## GATK adapter boundary

GATK uses an independent `bio_gatk` DAG and `pipeline_stage_execution`
namespace. It may reuse generic status projections and WGS's directional OBS
leases, but it must not write WGS stage history or enter the WGS intake
scanner. The node200 handoff is an immutable file/receipt protocol behind a
forced-command SSH boundary; node200 does not connect to the biodemo database.
The backend reads the selected project's `sampleinfo.txt` and follows its
project-local `a.raw` FASTQ links. Every absolute link target must remain below
an explicit approved root, and each approved host root must be mounted
read-only at the same absolute path inside backend. Equivalent storage aliases
do not replace that same-path mount requirement.

## Testing

Runtime tests execute on approved remote hosts. Offline validation uses cached images with `--network none` where possible. A test run must not create Docker networks, publish ports, or contact production execution services.

## Reusable frontend builder

Frontend source-only releases use a two-image offline contract:

- `airflow-demo/frontend-builder:node22-lock-<lock-sha-prefix>` contains Node
  and the exact `npm ci` dependency tree. Labels record the complete
  `package-lock.json` SHA256 and Node major.
- A host-local `airflow-demo/frontend-runtime:*` image contains the approved
  nginx version and deployment-specific gateway configuration.

`scripts/build_frontend_offline.sh` verifies both local images, runs tests and
the TypeScript/Vite build with Docker networking disabled, extracts only
`dist`, removes the prior static assets, and layers the new bundle onto the
runtime image. It does not run `npm ci`, pull an image, or contact a registry.
Changing the lockfile, Node major, nginx contract or approved base is an image
contract change and requires a newly identified base rather than silently
reusing an incompatible cache.
# 2026-09-14 independent ledger projection

The standalone app.sample_reference_worker synchronizes registered original WGS
files into the business ledger, separate from Airflow/scanner execution. It uses
a dedicated bounded DB pool and pass-plus60s polling; prepare offers only a
nonblocking hint. No new published port. Operator configuration and rollback are
documented in docs/11_DEPLOYMENT_RUNBOOK.md. No WGS writer or local/SGE changes.
