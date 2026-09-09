---
name: airflow-dag-dev
description: Develop the current bio_wgs and bio_gatk Airflow DAGs, project-level stage graphs, run-conf validation and runtime handoff.
---

## Required reading

- `AGENTS.md`
- `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/05_API_CONTRACT.md`

## Workflow

1. Keep DAG tasks project-level.
2. Validate DAG run conf strictly.
3. Pass large data by file path, not XCom.
4. Generate config files under workdir.
5. Dispatch through the registered WGS/GATK runtime contract; do not infer an execution target from the host.
6. Add failure summary and email notification.

## Prohibited

- Do not model every Snakemake rule as an Airflow task.
- Do not read/write Airflow metadata DB directly.
- Do not print secrets in task logs.
- Do not deploy or unpause GATK in production.
