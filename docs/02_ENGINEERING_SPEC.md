# Engineering specification

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
