# NGS Huawei Cloud

`ngs-huaweicloud` is an online NGS analysis control plane for Huawei Cloud CCE and local execution targets. Airflow coordinates pipeline-level work, adapters integrate workflow-specific behavior, FastAPI owns the business state, and React presents submission, monitoring, QC, logs, artifacts, and lifecycle state.

The current production registry enables only the WGS adapter. WES, GATK, or another NGS workflow is added by registering an adapter and deployment capabilities; the platform core does not branch on pipeline names.

## Start here

1. `AGENTS.md` — repository safety and development rules.
2. `CURRENT_STATE.md` — current implementation and deployment state.
3. `TASKS.md` — tracked work and acceptance state.
4. `docs/01_SYSTEM_ARCHITECTURE.md` — registry and adapter boundaries.
5. `docs/05_API_CONTRACT.md` — generic and WGS extension APIs.
6. `docs/11_DEPLOYMENT_RUNBOOK.md` — offline-capable deployment rules.

## Core boundaries

- React talks only to FastAPI.
- FastAPI owns business records and dispatches generic operations through the pipeline registry.
- Airflow owns run-level orchestration; Snakemake owns rule and file dependencies.
- Workflow-specific behavior stays inside adapters or namespaced extension APIs.
- Remote files and receipts are replayable evidence; the UI reads validated database projections.
- Secrets, patient data, FASTQ, BAM, VCF, and reference data are never committed.

## Deployment identity

- Project name: `ngs-huaweicloud`
- Server project root: `/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud`
- Network: an existing external Docker network supplied with `NGS_PLATFORM_NETWORK`; this repository does not create or prescribe a subnet.
- Production currently publishes only the approved frontend endpoint.

The old PGTA/NIPT demo runtimes and the WES mock implementation have been retired. Historical database migrations and state/audit documents remain intact.
