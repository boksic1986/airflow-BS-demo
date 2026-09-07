# System architecture

```text
React UI
   |
FastAPI generic API ---- Pipeline Registry ---- Adapter
   |                                         |-- WGS extension
PostgreSQL                                  |-- future WES/GATK
   |
Airflow DAG ---- execution target ---- CCE / local / future SGE
   |
validated receipts, rule events, QC and controlled artifacts
```

## Pipeline registry

`config/pipelines.yaml` declares pipeline identity, display name, DAG, adapter, deployment state, submission state, capabilities, and supported execution targets. `backend/app/pipeline_registry.py` validates the declaration and exposes a stable public projection.

Shared services ask the registry whether a capability exists. They do not test for `wgs`, `wes`, `gatk`, or retired pipeline names. An adapter owns request validation and workflow-specific projections. The adapter contract includes create/submit/reanalysis, run detail, dashboard/progress, sample/failure summaries, Rule phase, logs/artifacts, workflow summary, QC, intake, scan and configuration hooks; missing hooks fail closed.

## State ownership

- PostgreSQL is the operator-facing source of truth for runs, samples, QC, rules, artifacts, dispatch choices, and lifecycle projections.
- Airflow owns orchestration state.
- Workflow evidence files remain immutable/replayable inputs to the observer.
- The observer validates generation, receipt, and identity before updating the business database.
- Frontend code renders backend projections and does not parse workflow evidence.

## WGS extension

The WGS adapter retains its namespaced Step1–Step7 APIs, evidence bridge, directional transfer leases, execution commit barrier, heavy-slot quota, and QC projection. These are adapter features, not generic platform assumptions.
