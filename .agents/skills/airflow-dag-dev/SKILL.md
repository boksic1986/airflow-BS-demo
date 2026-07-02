---
name: airflow-dag-dev
description: Develop Airflow DAGs for airflow-demo. Use for bio_wes_qsub, bio_nipt_qsub, bio_nipt_docker DAGs, task graph, conf validation, and notification flow.
---

## Required reading

- `AGENTS.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/05_API_CONTRACT.md`

## Workflow

1. Keep DAG tasks project-level.
2. Validate DAG run conf strictly.
3. Pass large data by file path, not XCom.
4. Generate config files under workdir.
5. Use Snakemake/Docker runner as one project-level task.
6. Add failure summary and email notification.

## Prohibited

- Do not model every Snakemake rule as an Airflow task.
- Do not read/write Airflow metadata DB directly.
- Do not print secrets in task logs.
