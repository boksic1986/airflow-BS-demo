# Server-Side WGS Copy And Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt the BS10610 Airflow-owned WGS development copy for stable Rule/Pod evidence and complete incremental monitoring through biodemo, FastAPI, and the WGS-only frontend without executing the workflow.

**Architecture:** WGS-specific adapters live only in `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs`. Platform catalog, database, observer, API, frontend, DAG, and Compose changes remain versioned in the local airflow-demo branch and are remotely tested before deployment. Run bindings connect a pinned server snapshot to read-only JSONL evidence; the observer persists byte offsets and projects Rule/Pod state into biodemo.

**Tech Stack:** Snakemake 9 logger plugin API, Python 3.11, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, PyYAML, React 18, TypeScript, Vitest, Docker Compose.

## Global Constraints

- Never modify `/mnt/biodevrwbi/33.chenjiucheng/project/wgs` from airflow-demo work.
- WGS integration edits occur only in `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs`.
- Keep the live `current` release unchanged until all platform-only acceptance checks pass.
- Keep `WGS_EXECUTION_ENABLED=false` and all three WGS DAGs paused.
- Do not run CCE, OBS, SGE, local Snakemake, or the WGS workflow in this delivery.
- Use only synthetic event fixtures shaped from existing evidence contracts.
- Do not give `wgs-observer` kubeconfig, OBS credentials, SSH keys, Docker socket, privileged mode, host network, or a published port.
- Do not delete or rewrite FASTQ, workflow upstream, references, production results, historical evidence, PostgreSQL volumes, or Redis volumes.
- Local worktree changes cover platform code and docs; server WGS copy changes are checksummed and recorded in `HANDOFF.md`.
- Backend/frontend/DAG/Compose runtime verification runs remotely according to repository policy.

---

### Task 1: Server WGS snapshot contract and logger adapter

**Files:**
- Server create: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs/airflow_integration/rule_status_logger.py`
- Server create: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs/airflow_integration/group_evidence_adapter.py`
- Server create: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs/tests/test_airflow_rule_status_contract.py`
- Server modify: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs/SNAPSHOT_MANIFEST.sha256`
- Local create: `config/wgs_releases.yaml`
- Local create: `backend/app/wgs_release_catalog.py`
- Local create: `backend/tests/test_wgs_release_catalog.py`
- Local modify: `backend/app/config.py`
- Local modify: `backend/app/wgs_platform_service.py`

**Interfaces:**
- Logger emits schema-version-1 JSONL events `rule_planned`, `job_info`, `job_started`, `job_finished`, and `job_error`.
- Evidence adapter validates and copies only complete appended records into a run-scoped evidence directory.
- Catalog returns `PipelineSnapshot` from `load_snapshot_catalog(path: Path).default_development()`.
- New run params contain `pipeline_snapshot_id`, `source_commit`, `snapshot_manifest_sha256`, and `rule_event_schema_version`.

- [ ] Write server contract tests first. The tests construct logger callbacks with synthetic Snakemake job metadata, assert literal JSON payload fields, verify append-only per-stream filenames, and prove incomplete trailing JSON is not published by the adapter.
- [ ] Run `python tests/test_airflow_rule_status_contract.py` on BS10610 and confirm RED because `airflow_integration` does not exist.
- [ ] Implement the minimal server logger with deterministic `rule_instance_id=first16(sha256(rule_name + canonical wildcards + canonical output paths))`, UTC epoch timestamps, stream IDs, and atomic append guarded by one process-local lock.
- [ ] Implement the server evidence adapter with a JSON offset state file, binary byte offsets, complete-newline publication, file-identity reset, normalized path checks, and atomic state replacement.
- [ ] Run the server contract tests and confirm GREEN. Rebuild `SNAPSHOT_MANIFEST.sha256`, preserving `SOURCE_PROVENANCE.json` and recording the new manifest hash.
- [ ] Write failing local catalog tests that require a development snapshot rooted at the exact server path, commit `136da1a...`, Rule schema `1`, and `execution_enabled=false`.
- [ ] Run `python -m pytest backend/tests/test_wgs_release_catalog.py -q` remotely and confirm RED because the catalog module is missing.
- [ ] Implement `wgs_release_catalog.py`, `config/wgs_releases.yaml`, settings, and WGS run pinning. Reject unknown snapshot status, path outside `/airflow-WGS/development`, unsupported schema, and any execution-enabled development snapshot.
- [ ] Run catalog and WGS-only platform tests remotely and confirm GREEN; submission must remain HTTP 409.
- [ ] Commit local Task 1 as `feat: register server WGS development snapshot`. Record server file hashes in the commit-adjacent handoff draft.

---

### Task 2: Durable observer cursor schema

**Files:**
- Local create: `backend/alembic/versions/20260812_0007_wgs_observer_cursors.py`
- Local modify: `backend/app/models.py`
- Local modify: `backend/tests/test_models_metadata.py`
- Local modify: `docs/04_DATABASE_SCHEMA.md`

**Interfaces:**
- `EvidenceCursor` unique key: `(analysis_id, attempt, relative_path)`.
- `ObserverRunState` unique key: `(analysis_id, attempt)`.
- `KubernetesWorkload` gains `resource_version`, `observed_at`, `node_name`, `message`, and `job_status_json`.

- [ ] Add failing model metadata tests asserting both new tables, unique constraints, and five Pod enrichment columns.
- [ ] Run `python -m pytest backend/tests/test_models_metadata.py -q` remotely and confirm RED.
- [ ] Add SQLAlchemy models with cursor byte offset, complete line number, file identity, size, mtime, last success, last error, and update time.
- [ ] Add Alembic revision `20260812_0007` after `20260812_0006`; upgrade creates only the two tables and five nullable columns, downgrade removes only those additions.
- [ ] Run metadata tests and migration upgrade/current on a disposable remote database; confirm head `20260812_0007`.
- [ ] Update database documentation and commit as `feat: persist WGS evidence cursors`.

---

### Task 3: Binding validation and incremental Rule ingestion

**Files:**
- Local create: `backend/app/wgs_evidence_binding.py`
- Local modify: `backend/app/wgs_observer.py`
- Local modify: `backend/app/wgs_observer_cli.py`
- Local modify: `backend/tests/test_wgs_observer.py`

**Interfaces:**
- Binding keys: `schema_version`, `analysis_id`, `attempt`, `pipeline_snapshot_id`, `run_label`, `evidence_path`.
- `load_evidence_bindings(binding_root, evidence_root, catalog)` returns valid bindings plus isolated diagnostics.
- `ingest_evidence_once(session_factory, evidence_root, binding_root, catalog_path)` returns counts for bindings, events, files, and errors.

- [ ] Replace the old `analysis.json` fixture with explicit binding JSON and real schema-version-1 Rule events.
- [ ] Add failing tests for incremental append, partial trailing line, observer restart, malformed complete JSON, path escape, unsupported schema, file truncation, file replacement, and unknown analysis/attempt.
- [ ] Run observer tests remotely and confirm failures arise from whole-file scanning and missing cursors.
- [ ] Implement normalized binding validation below `evidence_root`, approved snapshot validation, positive numeric attempt, `^wgs392-[0-9a-f]{16}$` run labels, and matching biodemo attempt.
- [ ] Implement binary complete-line reader. Advance offsets only past newline-terminated UTF-8 JSON objects; reset on identity change or shrink.
- [ ] Generate event identity from snapshot ID plus canonical upstream payload. Persist raw events before rebuilding projections.
- [ ] Rebuild Rule projection in two passes: map `(stream_id, job_id)` from `job_info`, then apply planned/start/finish/error in timestamp order. Prefer Worker evidence when present.
- [ ] Commit each file's raw events, projection, and cursor in one transaction. Preserve a bad-line diagnostic and continue other files.
- [ ] Update CLI with binding/catalog arguments and compact JSON poll results.
- [ ] Run all observer tests remotely and confirm GREEN; commit as `feat: ingest WGS rule evidence incrementally`.

---

### Task 4: Pod normalization, API, frontend, and polling

**Files:**
- Local modify: `backend/app/wgs_observer.py`
- Local modify: `backend/app/main.py`
- Local modify: `backend/tests/test_wgs_observer.py`
- Local modify: `backend/tests/test_wgs_only_platform.py`
- Local modify: `frontend/src/api.ts`
- Local modify: `frontend/src/pages/RunDetailPage.tsx`
- Local modify: `frontend/src/WgsProductionUi.test.tsx`
- Local modify: `docs/05_API_CONTRACT.md`
- Local modify: `docs/06_FRONTEND_SPEC.md`
- Local modify: `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`

**Interfaces:**
- Run detail adds `pipeline_snapshot_id`, `rule_event_schema_version`, and `observer` freshness/error.
- Pod API returns `pod_hash`, `job_name`, `phase`, `reason`, `exit_code`, `node_name`, `message`, `resources`, `observed_at`, and `updated_at`.
- Rules and Pods APIs remain database-only authenticated reads.

- [ ] Add failing observer tests using real-shaped `pod-events.jsonl`, `pod-metrics.jsonl`, and `job-events.jsonl`. Assert numeric resource-version ordering, metrics enrichment without phase regression, and OOMKilled/ImagePullBackOff final detail extraction.
- [ ] Add failing authenticated API tests for snapshot/freshness and actual Pod field names.
- [ ] Add failing frontend tests for snapshot display, observer freshness/error, Rule rows, Pod rows, and five-second active polling.
- [ ] Run focused backend/frontend tests remotely and confirm RED.
- [ ] Implement Pod/Job/metrics normalization keyed by `pod_hash`; use `event_key` identity and numeric `resource_version` ordering.
- [ ] Extend FastAPI serialization without filesystem or Kubernetes access during requests and return 404 for unknown/non-WGS analysis IDs.
- [ ] Update frontend types and render release/freshness plus actual Pod fields. Preserve empty/error states and five-second active polling.
- [ ] Run focused backend tests, focused frontend tests, TypeScript build, and Vite production build remotely; confirm GREEN.
- [ ] Update API/frontend/event documentation and commit as `feat: expose WGS rule and pod monitoring`.

---

### Task 5: Compose isolation, synthetic acceptance, deployment, and handoff

**Files:**
- Local modify: `docker-compose.wgs.yaml`
- Local modify: `.env.wgs.example`
- Local modify: `dags/tests/test_wgs_only_deployment_contract.py`
- Local modify: `docs/11_DEPLOYMENT_RUNBOOK.md`
- Local modify: `docs/22_WGS_ONLY_LOCAL_CCE_PLATFORM_DESIGN.md`
- Local modify: `CURRENT_STATE.md`
- Local modify: `TASKS.md`
- Local modify: `HANDOFF.md`

**Interfaces:**
- Observer mounts release catalog, binding root, and evidence root read-only.
- Deployed platform migration head is `20260812_0007`.
- Live workflow execution remains unavailable.

- [ ] Add failing deployment contract tests asserting observer has no ports/capabilities/host network/credentials and mounts catalog, bindings, and evidence read-only with execution false.
- [ ] Update Compose and `.env.wgs.example`; do not mount the mutable upstream `/project/wgs`. The server development copy is packaged into the candidate release only as a checksummed artifact and is not invoked.
- [ ] Run DAG/deployment contract, Compose config, focused backend suite, focused frontend suite, and frontend build remotely.
- [ ] Create one synthetic WGS run, binding, Rule JSONL, and Pod JSONL in a dedicated platform validation directory. Append events across multiple observer polls, restart observer, and verify cursors, DB, APIs, and frontend. Do not execute a DAG or workflow.
- [ ] Build a new candidate release under `/airflow-WGS/releases/<release-id>`, migrate biodemo, recreate only platform services, verify health/login/RBAC/observer, all DAGs paused, and submission HTTP 409. Atomically repoint `current` only after checks pass.
- [ ] Remove only synthetic validation files and rows created by acceptance. Preserve server development copy, upstream, production inputs/results/references/evidence, and all volumes.
- [ ] Update design/runbook/state/tasks/handoff with exact server WGS hashes, candidate release, Git commit, migration, commands/results, synthetic analysis ID, and rollback instructions.
- [ ] Run `git diff --check`, verify clean worktree, verify deployed `current`, and commit as `docs: hand off WGS observability release`.
