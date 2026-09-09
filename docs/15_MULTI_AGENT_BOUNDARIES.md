# Development ownership boundaries

Every agent reads `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md` before remote
work and records whether its target is test or production.

- Coordinator: scope, sequencing, integration, and state documents.
- Backend: registry, adapters, APIs, business database, evidence projection.
- Airflow: DAG structure, target dispatch, task terminal projection.
- Workflow: Snakemake, CCE/local runners, execution profiles, receipts and rule evidence.
- Frontend: registry-driven pages and API consumption.
- Infrastructure: offline images, Compose, remote paths, permissions, image retention and release validation.
- QA: isolated tests, migration checks, and acceptance evidence.

Workflow-specific code belongs to its adapter/runtime owner. Shared platform code must not acquire pipeline-name branches during integration.
