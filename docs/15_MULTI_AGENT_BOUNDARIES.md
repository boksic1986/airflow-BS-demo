# Development ownership boundaries

- Coordinator: scope, sequencing, integration, and state documents.
- Backend: registry, adapters, APIs, business database, evidence projection.
- Airflow: DAG structure, target dispatch, task terminal projection.
- Workflow: Snakemake, runners, execution profiles, rule evidence.
- Frontend: registry-driven pages and API consumption.
- Infrastructure: offline images, Compose, remote paths, release validation.
- QA: isolated tests, migration checks, and acceptance evidence.

Workflow-specific code belongs to its adapter/runtime owner. Shared platform code must not acquire pipeline-name branches during integration.
