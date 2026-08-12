# WGS 3.9.3 Release Registration And Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register the already frozen WGS 3.9.3 release and make its existing Rule and Pod JSONL evidence incrementally visible through biodemo, FastAPI, and the WGS-only UI without running or modifying the workflow.

**Architecture:** A versioned YAML catalog pins each run to an approved pipeline release. Platform-owned JSON binding files map biodemo attempts to exact read-only evidence directories. `wgs-observer` persists byte cursors in biodemo, normalizes upstream schema version 1 events into Rule and Pod projections, and serves only committed database state through existing APIs.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, PyYAML, React 18, TypeScript, Vitest, Docker Compose.

## Global Constraints

- Do not modify, republish, revalidate, or execute `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-3.9.3-cloud`.
- Keep `WGS_EXECUTION_ENABLED=false`; keep `bio_wgs_cce`, `bio_wgs_onprem`, and `bio_wgs_intake_scan` paused.
- Use only synthetic fixtures shaped from previously completed evidence; do not invoke CCE, OBS, SGE, local Snakemake, or result transfer.
- Keep the observer mount read-only and do not provide kubeconfig, OBS credentials, SSH keys, Docker socket, or a published port.
- Keep private OBS configuration only on node005.
- Do not delete or rewrite FASTQ, workflow sources, references, results, historical evidence, PostgreSQL volumes, or Redis volumes.
- Run backend, frontend, migration, and Compose acceptance on the remote node; local checks are limited to Git, static text, and plan/document inspection.

## File structure

- `config/wgs_releases.yaml`: versioned release catalog and selected default.
- `backend/app/wgs_release_catalog.py`: catalog parsing, validation, and approved release selection.
- `backend/app/wgs_evidence_binding.py`: binding-file parsing and evidence-root containment.
- `backend/app/wgs_observer.py`: incremental JSONL reader, Rule reconciliation, Pod enrichment, and observer status.
- `backend/app/wgs_observer_cli.py`: observer CLI arguments and structured error logging.
- `backend/app/models.py`: cursor and observer-state records plus Pod ordering/enrichment fields.
- `backend/alembic/versions/20260812_0007_wgs_observer_cursors.py`: durable database migration.
- `backend/app/wgs_platform_service.py`: pin the default release into every new run.
- `backend/app/main.py`: expose monitoring projections and freshness.
- `backend/tests/test_wgs_release_catalog.py`: catalog and run-pinning contracts.
- `backend/tests/test_wgs_observer.py`: incremental cursor, Rule, Pod, and recovery contracts.
- `backend/tests/test_wgs_only_platform.py`: authenticated monitoring API contracts and execution denial.
- `frontend/src/api.ts`: typed Rule/Pod/observer response fields.
- `frontend/src/pages/RunDetailPage.tsx`: release/freshness display and real Pod field mapping.
- `frontend/src/WgsProductionUi.test.tsx`: release, Rule, Pod, and polling UI contract.
- `docker-compose.wgs.yaml`, `.env.wgs.example`: catalog/binding mounts and observer isolation.
- `docs/04_DATABASE_SCHEMA.md`, `docs/05_API_CONTRACT.md`, `docs/06_FRONTEND_SPEC.md`, `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`, `docs/11_DEPLOYMENT_RUNBOOK.md`, `docs/22_WGS_ONLY_LOCAL_CCE_PLATFORM_DESIGN.md`: durable contracts and runbook.
- `CURRENT_STATE.md`, `TASKS.md`, `HANDOFF.md`: task state and deployment evidence.

---

### Task 1: Release catalog and immutable run pinning

**Files:**
- Create: `config/wgs_releases.yaml`
- Create: `backend/app/wgs_release_catalog.py`
- Create: `backend/tests/test_wgs_release_catalog.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/wgs_platform_service.py`
- Modify: `docker-compose.wgs.yaml`
- Modify: `.env.wgs.example`

**Interfaces:**
- Produces: `PipelineRelease`, `ReleaseCatalog`, `load_release_catalog(path: Path) -> ReleaseCatalog`, and `ReleaseCatalog.default_approved() -> PipelineRelease`.
- Produces: run parameters `pipeline_release_id`, `upstream_release_name`, and `rule_event_schema_version`.
- Consumes: `WGS_RELEASE_CATALOG_PATH`, defaulting to `/config/wgs_releases.yaml` in Compose.

- [ ] **Step 1: Write failing catalog tests**

```python
def test_catalog_selects_the_approved_frozen_wgs393_release(tmp_path: Path) -> None:
    catalog = load_release_catalog(write_catalog(tmp_path))
    release = catalog.default_approved()
    assert release.release_id == "wgs-3.9.3-cloud-r38f2d5e"
    assert release.upstream_release_name == "release-38f2d5e-publishdirect-27e6daf20d34"
    assert release.rule_event_schema_version == "1"
    assert release.execution_enabled is False


def test_catalog_rejects_unknown_or_retired_default(tmp_path: Path) -> None:
    path = write_catalog(tmp_path, default_release_id="missing")
    with pytest.raises(ValueError, match="default release"):
        load_release_catalog(path)
```

- [ ] **Step 2: Run the focused tests remotely and confirm RED**

Run on the remote checkout:

```bash
python -m pytest backend/tests/test_wgs_release_catalog.py -q
```

Expected: collection fails because `app.wgs_release_catalog` does not exist.

- [ ] **Step 3: Implement the typed catalog parser and approved default selection**

```python
@dataclass(frozen=True)
class PipelineRelease:
    release_id: str
    pipeline: str
    version: str
    upstream_release_name: str
    source_root: str
    sfs_release_root: str
    ready_marker: str
    manifest_reference: str
    rule_event_schema_version: str
    execution_modes: tuple[str, ...]
    lifecycle: str
    execution_enabled: bool


@dataclass(frozen=True)
class ReleaseCatalog:
    default_release_id: str
    releases: tuple[PipelineRelease, ...]

    def default_approved(self) -> PipelineRelease:
        matches = [item for item in self.releases if item.release_id == self.default_release_id]
        if len(matches) != 1 or matches[0].lifecycle != "approved":
            raise ValueError("default release must identify one approved release")
        return matches[0]
```

Validate WGS-only pipeline, schema version `1`, normalized absolute roots, unique release IDs, allowed modes `cce|sge|local`, and `execution_enabled=false` for this delivery.

- [ ] **Step 4: Add the frozen release catalog entry**

```yaml
schema_version: "1"
default_release_id: wgs-3.9.3-cloud-r38f2d5e
releases:
  - release_id: wgs-3.9.3-cloud-r38f2d5e
    pipeline: wgs
    version: 3.9.3
    upstream_release_name: release-38f2d5e-publishdirect-27e6daf20d34
    source_root: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-3.9.3-cloud
    sfs_release_root: /workspace/33.chenjiucheng/wgs-pipelines/3.9.3/release-38f2d5e-publishdirect-27e6daf20d34
    ready_marker: PIPELINE_READY
    manifest_reference: PIPELINE_MANIFEST.sha256
    rule_event_schema_version: "1"
    execution_modes: [cce, sge, local]
    lifecycle: approved
    execution_enabled: false
```

- [ ] **Step 5: Pin new WGS runs to the catalog default**

Load the catalog inside `create_wgs_platform_run` and add exactly these immutable parameters:

```python
release = load_release_catalog(Path(settings.wgs_release_catalog_path)).default_approved()
params_json.update({
    "pipeline_release_id": release.release_id,
    "upstream_release_name": release.upstream_release_name,
    "rule_event_schema_version": release.rule_event_schema_version,
})
```

Mount `config/wgs_releases.yaml` read-only into backend and observer; do not add it to Airflow execution until the later runner task.

- [ ] **Step 6: Run focused tests remotely and confirm GREEN**

```bash
python -m pytest backend/tests/test_wgs_release_catalog.py backend/tests/test_wgs_only_platform.py -q
```

Expected: catalog tests pass; WGS create responses contain the pinned release; submission remains HTTP 409.

- [ ] **Step 7: Commit Task 1**

```bash
git add config/wgs_releases.yaml backend/app/wgs_release_catalog.py backend/app/config.py backend/app/wgs_platform_service.py backend/tests/test_wgs_release_catalog.py backend/tests/test_wgs_only_platform.py docker-compose.wgs.yaml .env.wgs.example
git commit -m "feat: register frozen WGS 3.9.3 release"
```

---

### Task 2: Durable observer cursor and monitoring schema

**Files:**
- Create: `backend/alembic/versions/20260812_0007_wgs_observer_cursors.py`
- Modify: `backend/app/models.py`
- Modify: `backend/tests/test_models_metadata.py`
- Modify: `docs/04_DATABASE_SCHEMA.md`

**Interfaces:**
- Produces: `EvidenceCursor`, keyed by `(analysis_id, attempt, relative_path)`.
- Produces: `ObserverRunState`, keyed by `(analysis_id, attempt)`.
- Extends: `KubernetesWorkload` with `resource_version`, `observed_at`, `node_name`, `message`, and `job_status_json`.

- [ ] **Step 1: Write failing metadata tests**

```python
def test_wgs_observer_cursor_models_are_registered() -> None:
    assert EvidenceCursor.__tablename__ == "evidence_cursor"
    assert ObserverRunState.__tablename__ == "observer_run_state"
    assert {"resource_version", "observed_at", "node_name", "message", "job_status_json"} <= set(KubernetesWorkload.__table__.columns.keys())
```

- [ ] **Step 2: Run the metadata test remotely and confirm RED**

```bash
python -m pytest backend/tests/test_models_metadata.py -q
```

Expected: import or assertion failure for the new models/columns.

- [ ] **Step 3: Add SQLAlchemy models**

```python
class EvidenceCursor(Base):
    __tablename__ = "evidence_cursor"
    __table_args__ = (UniqueConstraint("analysis_id", "attempt", "relative_path", name="uq_evidence_cursor_file"),)
    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analysis_run.analysis_id", ondelete="CASCADE"), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_identity: Mapped[str | None] = mapped_column(String(256))
    byte_offset: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    line_number: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    observed_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    observed_mtime_ns: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
```

`ObserverRunState` stores release ID, run label, relative evidence root, status, last success time, last error, and update time.

- [ ] **Step 4: Add Alembic revision `20260812_0007`**

Create both tables, their unique/index constraints, and the five nullable Kubernetes enrichment columns. The downgrade drops the two new tables first and then the five columns; it must not touch Phase 1 data.

- [ ] **Step 5: Run migration and metadata tests remotely**

```bash
python -m pytest backend/tests/test_models_metadata.py -q
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini current
```

Expected: tests pass and current revision is `20260812_0007` on the disposable test database. Do not migrate production in this task.

- [ ] **Step 6: Document tables and commit Task 2**

```bash
git add backend/app/models.py backend/alembic/versions/20260812_0007_wgs_observer_cursors.py backend/tests/test_models_metadata.py docs/04_DATABASE_SCHEMA.md
git commit -m "feat: persist WGS evidence cursors"
```

---

### Task 3: Explicit bindings and incremental Rule ingestion

**Files:**
- Create: `backend/app/wgs_evidence_binding.py`
- Modify: `backend/app/wgs_observer.py`
- Modify: `backend/app/wgs_observer_cli.py`
- Rewrite focused cases in: `backend/tests/test_wgs_observer.py`

**Interfaces:**
- Produces: `EvidenceBinding`, `load_evidence_bindings(binding_root: Path, evidence_root: Path, catalog: ReleaseCatalog) -> tuple[list[EvidenceBinding], list[BindingError]]`.
- Produces: `read_complete_jsonl(path: Path, cursor: EvidenceCursor) -> JsonlReadResult`.
- Produces: `ingest_evidence_once(*, session_factory, evidence_root: Path, binding_root: Path, catalog_path: Path) -> dict[str, int]`.
- Consumes binding JSON keys: `schema_version`, `analysis_id`, `attempt`, `pipeline_release_id`, `run_label`, and `evidence_path`.

- [ ] **Step 1: Replace the observer fixture with a real-format binding and write failing cursor tests**

```python
def write_binding(root: Path, analysis_id: str, evidence_path: str) -> None:
    (root / f"{analysis_id}.attempt-1.json").write_text(json.dumps({
        "schema_version": "1",
        "analysis_id": analysis_id,
        "attempt": 1,
        "pipeline_release_id": "wgs-3.9.3-cloud-r38f2d5e",
        "run_label": "wgs392-5cfe2e4a6aba7488",
        "evidence_path": evidence_path,
    }) + "\n", encoding="utf-8")


def test_partial_line_waits_then_incrementally_commits(tmp_path: Path) -> None:
    append_rule_jsonl(rule_file, planned_event, newline=True)
    append_rule_jsonl(rule_file, started_event, newline=False)
    first = ingest_once(tmp_path)
    assert first["events_ingested"] == 1
    append_bytes(rule_file, b"\n")
    second = ingest_once(tmp_path)
    assert second["events_ingested"] == 1
    assert cursor.byte_offset == rule_file.stat().st_size
```

Add cases for restart, append, malformed complete JSON, path escape, unsupported schema, file truncation, and file replacement.

- [ ] **Step 2: Run observer tests remotely and confirm RED**

```bash
python -m pytest backend/tests/test_wgs_observer.py -q
```

Expected: failures because the current observer scans `analysis.json`, rereads complete files, and lacks persisted cursors.

- [ ] **Step 3: Implement binding validation**

```python
@dataclass(frozen=True)
class EvidenceBinding:
    analysis_id: str
    attempt: int
    pipeline_release_id: str
    run_label: str
    evidence_path: Path
    relative_evidence_path: str
```

Require binding schema `1`, a known approved release, run label matching `^wgs392-[0-9a-f]{16}$`, positive numeric attempt, existing biodemo run/attempt at ingestion time, and a resolved evidence directory below `evidence_root`.

- [ ] **Step 4: Implement complete-line cursor reading**

Read in binary mode from `byte_offset`. Advance only for newline-terminated UTF-8 JSON objects. Return parsed `(payload, line_number, end_offset)` records plus a partial-line flag or a malformed-record error. Derive file identity as `st_dev:st_ino`; reset to zero when identity changes or size is smaller than the committed offset.

- [ ] **Step 5: Implement stable Rule identity and two-pass reconciliation**

```python
def upstream_event_id(release_id: str, payload: dict) -> str:
    material = {
        "release_id": release_id,
        "run_label": payload.get("run_label"),
        "stream_id": payload.get("stream_id"),
        "event": payload.get("event"),
        "timestamp": payload.get("timestamp"),
        "job_id": payload.get("job_id"),
        "rule_instance_id": payload.get("rule_instance_id"),
        "payload": payload,
    }
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
```

Preserve raw events first. Rebuild the attempt projection in two passes: collect `job_info` mappings and metadata, then apply planned/start/finish/error events by timestamp. Prefer Worker lifecycle events when a Rule instance has Worker evidence. Reconcile `rule-status-summary.json` when present.

- [ ] **Step 6: Make file ingestion transactional**

For each source file, write raw events, projections, and cursor offset in one database transaction. On malformed JSON, commit valid records before the bad line, leave the cursor at the bad line, set `last_error`, and continue with other files. Update `ObserverRunState` after each bound attempt.

- [ ] **Step 7: Update the CLI**

Add `--binding-root` defaulting from `WGS_OBSERVER_BINDING_ROOT=/data/wgs-observer-bindings` and `--catalog` defaulting from `WGS_RELEASE_CATALOG_PATH=/config/wgs_releases.yaml`. Log one compact JSON result per polling pass and log binding/file diagnostics without exiting the daemon.

- [ ] **Step 8: Run Rule observer tests remotely and confirm GREEN**

```bash
python -m pytest backend/tests/test_wgs_observer.py -q
```

Expected: all binding, cursor, recovery, schema, and Rule projection tests pass.

- [ ] **Step 9: Commit Task 3**

```bash
git add backend/app/wgs_evidence_binding.py backend/app/wgs_observer.py backend/app/wgs_observer_cli.py backend/tests/test_wgs_observer.py
git commit -m "feat: ingest WGS rule evidence incrementally"
```

---

### Task 4: Pod normalization, monitoring API, and WGS UI

**Files:**
- Modify: `backend/app/wgs_observer.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_wgs_observer.py`
- Modify: `backend/tests/test_wgs_only_platform.py`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/pages/RunDetailPage.tsx`
- Modify: `frontend/src/WgsProductionUi.test.tsx`
- Modify: `docs/05_API_CONTRACT.md`
- Modify: `docs/06_FRONTEND_SPEC.md`
- Modify: `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`

**Interfaces:**
- Extends `GET /api/runs/{analysis_id}` with `pipeline_release_id`, `rule_event_schema_version`, and `observer`.
- Keeps `GET /api/runs/{analysis_id}/rules` and `/pods` as database-only reads.
- Defines `WgsPod` fields `pod_hash`, `job_name`, `phase`, `reason`, `exit_code`, `node_name`, `message`, `resources`, `observed_at`, and `updated_at`.

- [ ] **Step 1: Write failing real-format Pod observer tests**

```python
def test_pod_phase_and_metrics_are_merged_by_pod_hash(tmp_path: Path) -> None:
    append_jsonl(pod_events, {
        "event_key": "pod-a:19033956", "job": "snakejob-a",
        "phase": "Running", "pod_hash": "5832d6c49930b334",
        "resource_version": "19033956", "observed_at_utc": "2026-08-10T00:48:47+00:00",
    })
    append_jsonl(pod_metrics, {
        "event_key": "pod-a:metrics", "pod_hash": "5832d6c49930b334",
        "observed_at_utc": "2026-08-10T00:49:59+00:00",
        "metrics": {"containers": [{"usage": {"cpu": "6405877524n", "memory": "1447372Ki"}}]},
    })
    ingest_once(tmp_path)
    assert pod.phase == "Running"
    assert pod.resources_json["containers"][0]["usage"]["memory"] == "1447372Ki"
```

Add tests proving older `resource_version` cannot overwrite a newer phase and a final Pod snapshot extracts reason, exit code, image, node, OOMKilled, and ImagePullBackOff fields.

- [ ] **Step 2: Write failing authenticated API and frontend tests**

Backend assertions:

```python
assert detail["pipeline_release_id"] == "wgs-3.9.3-cloud-r38f2d5e"
assert detail["observer"]["status"] == "healthy"
assert pods[0]["job_name"] == "snakejob-a"
assert pods[0]["reason"] == "OOMKilled"
```

Frontend assertions:

```tsx
expect(await screen.findByText("wgs-3.9.3-cloud-r38f2d5e")).toBeInTheDocument();
await user.click(screen.getByRole("tab", {name: "Pods"}));
expect(screen.getByText("snakejob-a")).toBeInTheDocument();
expect(screen.getByText("OOMKilled")).toBeInTheDocument();
```

- [ ] **Step 3: Run focused backend and frontend tests remotely and confirm RED**

```bash
python -m pytest backend/tests/test_wgs_observer.py backend/tests/test_wgs_only_platform.py -q
cd frontend && npm test -- --run src/WgsProductionUi.test.tsx
```

- [ ] **Step 4: Implement Pod/Job/metrics normalization**

Use `event_key` as event identity, `pod_hash` as projection identity, and numeric `resource_version` ordering. Metrics update `resources_json` only. Job events update `job_status_json`. Final Pod JSON extracts `status.phase`, waiting/terminated reasons, exit code, image ID, node name, and the most actionable message.

- [ ] **Step 5: Return monitoring fields from FastAPI**

The run detail handler reads `ObserverRunState` and run params after `get_run_detail`. The Rule and Pod endpoints verify the WGS run exists, return only the requested analysis, and serialize timestamps safely. They perform no filesystem or Kubernetes reads.

- [ ] **Step 6: Update typed frontend rendering**

Display the release ID and observer freshness/error in the WGS overview. Change the Pods table to use `job_name`, `phase`, `reason`, `exit_code`, `node_name`, and `message` from the actual backend contract. Preserve five-second polling for active statuses.

- [ ] **Step 7: Run focused backend/frontend tests and build remotely**

```bash
python -m pytest backend/tests/test_wgs_release_catalog.py backend/tests/test_wgs_observer.py backend/tests/test_wgs_only_platform.py backend/tests/test_models_metadata.py -q
cd frontend && npm test -- --run src/WgsProductionUi.test.tsx src/WgsOnlyShell.test.tsx
cd frontend && npm run build
```

Expected: all focused tests and the production build pass.

- [ ] **Step 8: Update API/event/frontend documents and commit Task 4**

```bash
git add backend/app/wgs_observer.py backend/app/main.py backend/tests/test_wgs_observer.py backend/tests/test_wgs_only_platform.py frontend/src/api.ts frontend/src/pages/RunDetailPage.tsx frontend/src/WgsProductionUi.test.tsx docs/05_API_CONTRACT.md docs/06_FRONTEND_SPEC.md docs/08_SNAKEMAKE_QSUB_INTEGRATION.md
git commit -m "feat: expose WGS rule and pod monitoring"
```

---

### Task 5: Compose isolation, remote synthetic acceptance, deployment, and handoff

**Files:**
- Modify: `docker-compose.wgs.yaml`
- Modify: `.env.wgs.example`
- Modify: `docs/11_DEPLOYMENT_RUNBOOK.md`
- Modify: `docs/22_WGS_ONLY_LOCAL_CCE_PLATFORM_DESIGN.md`
- Modify: `CURRENT_STATE.md`
- Modify: `TASKS.md`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: `/config/wgs_releases.yaml`, `/data/wgs-observer-bindings:ro`, and `/data/wgs-evidence:ro`.
- Produces: a BS10610 WGS-only platform release with migration `20260812_0007`, observer health evidence, and unchanged disabled execution gates.

- [ ] **Step 1: Add Compose contract assertions**

Extend `dags/tests/test_wgs_only_deployment_contract.py` to assert:

```python
observer = compose["services"]["wgs-observer"]
assert "ports" not in observer
assert observer["environment"]["WGS_EXECUTION_ENABLED"] == "false"
assert any(volume.endswith(":/data/wgs-evidence:ro") for volume in observer["volumes"])
assert any(volume.endswith(":/data/wgs-observer-bindings:ro") for volume in observer["volumes"])
assert not any(token in str(observer).lower() for token in ("kubeconfig", "obsutil", "docker.sock", ".ssh"))
```

- [ ] **Step 2: Update Compose mounts and observer command**

Mount `./config/wgs_releases.yaml:/config/wgs_releases.yaml:ro` and `${WGS_OBSERVER_BINDING_HOST_ROOT}:/data/wgs-observer-bindings:ro`. Set `WGS_RELEASE_CATALOG_PATH`, `WGS_OBSERVER_BINDING_ROOT`, and `WGS_EXECUTION_ENABLED=false`. Do not add capabilities, host networking, privileged mode, ports, or credentials.

- [ ] **Step 3: Run remote static and full focused verification**

```bash
python dags/tests/test_wgs_only_deployment_contract.py
docker compose --env-file .env.wgs.example -f docker-compose.wgs.yaml config --quiet
python -m pytest backend/tests/test_wgs_release_catalog.py backend/tests/test_wgs_observer.py backend/tests/test_wgs_only_platform.py backend/tests/test_models_metadata.py -q
cd frontend && npm test -- --run src/WgsProductionUi.test.tsx src/WgsOnlyShell.test.tsx
cd frontend && npm run build
```

Expected: all commands pass. No workflow command appears in service logs.

- [ ] **Step 4: Run synthetic end-to-end monitoring acceptance**

Create one mock WGS run in biodemo, one platform binding JSON, and synthetic Rule/Pod JSONL under a dedicated platform acceptance directory. Append planned/running/success and Pending/Running/Succeeded records across separate observer polls. Verify database cursor offsets, API responses, frontend rendering, and observer restart. Remove only the synthetic binding/evidence files and mock database rows created by this test.

- [ ] **Step 5: Deploy a new BS10610 platform release**

Copy the committed source to `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/<release-id>`, validate resolved paths, build/recreate only platform services, run `biodemo-migrate`, and confirm revision `20260812_0007`. Verify health, login/RBAC, release detail, Rule/Pod API, observer freshness, paused DAGs, and HTTP 409 submission. Then atomically repoint `current`.

Do not run `docker compose down -v`, volume prune, system prune, recursive workflow/evidence deletion, CCE commands, OBS commands, or Snakemake.

- [ ] **Step 6: Update durable state documents**

Record exact release ID, Git commit, migration revision, commands/results, synthetic analysis ID, Compose services, execution-denial result, preserved data boundaries, rollback steps, and any remaining deferred T130 items in `CURRENT_STATE.md`, `TASKS.md`, and the newest `HANDOFF.md` entry.

- [ ] **Step 7: Run final repository checks and commit Task 5**

```bash
git diff --check
git status --short
git add docker-compose.wgs.yaml .env.wgs.example dags/tests/test_wgs_only_deployment_contract.py docs/11_DEPLOYMENT_RUNBOOK.md docs/22_WGS_ONLY_LOCAL_CCE_PLATFORM_DESIGN.md CURRENT_STATE.md TASKS.md HANDOFF.md
git commit -m "docs: hand off WGS observability release"
```

- [ ] **Step 8: Verify the committed deployment matches the branch**

```bash
git status --short
git rev-parse HEAD
ssh BS10610 'readlink -f /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current'
```

Expected: the worktree is clean, `current` resolves to the new release, production services are healthy, execution remains disabled, and no workflow/data directories were modified.
