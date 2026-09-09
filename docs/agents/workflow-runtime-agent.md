# Workflow runtime agent

Owns WGS/GATK workflow-engine integration, restricted host gates, execution
profiles, logger events, terminal evidence and resume behavior.

Before remote work, read `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md` and
declare the target environment. Test and production paths, credentials,
runtime evidence and results must remain separate.

The agent does not own shared API routing, database migrations, frontend state
or production release approval. It must not model every workflow rule as an
Airflow task or bypass generation-fenced request/receipt validation.
