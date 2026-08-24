# WGS Airflow Demo Clean Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Irreversibly remove the BS10610 WGS demo control-plane state and leave PostgreSQL/Redis ready but the old application stack stopped, without touching WGS/CCE source or production biological data.

**Architecture:** A repository-owned reset utility first produces a non-secret inventory and validates an exact allowlist. A separately confirmed apply mode stops only the six application services, recreates the `airflow` and `biodemo` logical databases, flushes the dedicated Redis instance, and deletes only resolved demo platform paths. PostgreSQL and Redis containers, the external Docker network, WGS/CCE sources, FASTQ, references, SFS/OBS, images and production results remain intact.

**Tech Stack:** Python 3.12, pytest, Docker Compose, PostgreSQL 15, Redis 7, PowerShell-to-SSH Bash-safe execution.

**Spec:** `docs/superpowers/specs/2026-08-24-wgs-airflow-production-control-plane-design.md`

## Global Constraints

- Target host is exactly `server10610`; Compose project is exactly `airflow-wgs`.
- External network `nipt_analysis_test_net` must remain `192.168.199.0/24`, gateway `192.168.199.1`.
- Do not use `docker compose down -v`, `docker system prune`, `docker volume prune`, `git reset --hard` or `git clean`.
- Preserve volume `airflow-wgs_postgres-data`; recreate only logical databases `airflow` and `biodemo`.
- Preserve WGS/cce-pipeline source, FASTQ, references, images, SFS/OBS and production result paths.
- Do not restart the old T131 application services after reset.
- Do not print or copy passwords, tokens, SSH private keys, OBS configuration, kubeconfig or patient data.
- The reset is irreversible and intentionally does not create a demo-data backup.

---

### Task 1: Add an allowlisted reset utility

**Files:**
- Create: `scripts/wgs_control_plane_reset.py`
- Create: `scripts/tests/test_wgs_control_plane_reset.py`

**Interfaces:**
- Consumes: `docker` executable, exact BS10610 platform paths and `--mode plan|apply`.
- Produces: `main(argv: list[str] | None = None) -> int`, a JSON inventory receipt, and an apply receipt with database and path postconditions.

- [ ] **Step 1: Write failing target-boundary tests**

```python
def test_targets_are_exact_and_never_include_biological_roots():
    targets = reset.control_plane_targets()
    assert targets.hostname == "server10610"
    assert targets.databases == ("airflow", "biodemo")
    assert targets.volume == "airflow-wgs_postgres-data"
    assert "/mnt/biodevrwbi/33.chenjiucheng/project/wgs" not in targets.delete_paths
    assert all("FASTQ" not in path and "Project_result" not in path for path in targets.delete_paths)


def test_apply_requires_exact_confirmation():
    with pytest.raises(ValueError, match="confirmation"):
        reset.validate_confirmation("RESET")
    reset.validate_confirmation("RESET-WGS-DEMO-CONTROL-PLANE:server10610:20260824")
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run on BS10610 in the existing backend test image:

```bash
docker run --rm \
  -v /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs-control-plane-reset-20260824:/workspace:ro \
  -w /workspace \
  airflow-demo/backend:t131-phase1 \
  python -m pytest -q -p no:cacheprovider scripts/tests/test_wgs_control_plane_reset.py
```

Expected: FAIL because `scripts/wgs_control_plane_reset.py` does not exist.

- [ ] **Step 3: Implement exact target and inventory types**

Implement immutable types and constants:

```python
CONFIRMATION = "RESET-WGS-DEMO-CONTROL-PLANE:server10610:20260824"
APPLICATION_SERVICES = (
    "frontend-nginx", "backend", "wgs-observer",
    "airflow-scheduler", "airflow-api-server", "airflow-worker",
)
DATABASES = ("airflow", "biodemo")
PRESERVED_VOLUME = "airflow-wgs_postgres-data"
PRESERVED_NETWORK = "nipt_analysis_test_net"
PLATFORM_ROOT = Path("/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS")
AIRFLOW_TEST_ROOT = Path("/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs")
```

The delete allowlist must contain only:

```text
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/runtime/intake/*
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/runtime/mock-fastq/*
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/runtime/results/runs/*
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/runtime/transfer-spool/*
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/bindings/*
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/staging/*
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/validation/*
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260812-wgs-observer-553be3f
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260812-wgs-only-phase1
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/env/wgs-host.env.before-1b1169c
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/env/wgs-host.env.pre-a9ea4bf
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/env/platform-admin.initial-password
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/shared/ssh
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/T133-candidate
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/T133-final-20260824
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/T134-disabled-dev
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/T133-final-docs2.tar.gz
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/T133-final-sync.tar.gz
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/T133-node200-sync.tar.gz
```

Preserve explicitly:

```text
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/current
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260812-wgs-orchestration-t131-candidate
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/envs
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/env/bs10610.wgs.env
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/env/wgs-host.env
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/logger-integration
```

Resolve every existing target with `Path.resolve(strict=True)` and reject it unless it is exactly an allowlisted target or a direct child of one of the four allowlisted emptyable roots. Reject symlinked directories and mountpoints. The inventory JSON records realpath, type, entry count and byte count but no file content.

- [ ] **Step 4: Add command-runner and dry-run tests**

```python
def test_plan_mode_never_invokes_mutating_commands(fake_runner, tmp_path):
    receipt = reset.execute(reset.control_plane_targets(), mode="plan", runner=fake_runner)
    assert receipt["mode"] == "plan"
    assert not any("DROP DATABASE" in command for command in fake_runner.commands)
    assert not any("FLUSHALL" in command for command in fake_runner.commands)


def test_apply_stops_only_application_services_and_preserves_infra(fake_runner):
    reset.execute(
        reset.control_plane_targets(), mode="apply", runner=fake_runner,
        confirmation=reset.CONFIRMATION,
    )
    stop = next(command for command in fake_runner.commands if command[:3] == ["docker", "compose", "stop"])
    assert "postgres" not in stop and "redis" not in stop
    assert set(stop[3:]) == set(reset.APPLICATION_SERVICES)
```

- [ ] **Step 5: Implement plan/apply execution**

Apply mode performs these exact operations:

1. Verify `hostname == server10610`.
2. Verify all Airflow DAG runs are inactive and both execution flags in the active environment are false.
3. Verify the external network tuple and preserved volume.
4. Atomically write the pre-reset inventory receipt below `airflow-WGS/audit/production-reset-20260824/`.
5. Run `docker compose ... stop` for `APPLICATION_SERVICES` only.
6. Recheck no application container is running.
7. Use the existing PostgreSQL container to terminate connections, drop and recreate `airflow` and `biodemo` with their existing owners.
8. Run `redis-cli FLUSHALL` against the dedicated `airflow-wgs-redis-1` container.
9. Delete only validated allowlist entries using Python `Path.unlink()` and bottom-up `Path.rmdir()`; never follow symlinks.
10. Write an apply receipt and a post-reset verification receipt.

Database SQL must be static and name-bound:

```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname IN ('airflow', 'biodemo') AND pid <> pg_backend_pid();
DROP DATABASE airflow;
DROP DATABASE biodemo;
CREATE DATABASE airflow OWNER airflow;
CREATE DATABASE biodemo OWNER biodemo;
```

- [ ] **Step 6: Run focused tests and static safety scans**

Run:

```bash
python -m pytest -q scripts/tests/test_wgs_control_plane_reset.py
rg -n "docker (system|volume) prune|down -v|rm -rf|/project/wgs|FASTQ|Project_result" \
  scripts/wgs_control_plane_reset.py
python -m py_compile scripts/wgs_control_plane_reset.py
```

Expected: tests PASS; prohibited destructive commands absent; biological roots appear only in negative tests or preservation checks.

- [ ] **Step 7: Commit the reset utility**

```bash
git add scripts/wgs_control_plane_reset.py scripts/tests/test_wgs_control_plane_reset.py
git commit -m "ops: add allowlisted WGS demo control-plane reset"
```

### Task 2: Run remote plan mode and review the exact receipt

**Files:**
- Create remotely: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/audit/production-reset-20260824/pre-reset-inventory.json`
- Modify: none

**Interfaces:**
- Consumes: Task 1 reset utility and current BS10610 state.
- Produces: a plan-mode receipt whose targets exactly match this plan.

- [ ] **Step 1: Copy only the reset utility to a task-specific staging directory**

Use:

```text
/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs-control-plane-reset-20260824
```

Do not copy `.env`, credentials, private keys, WGS source or patient data.

- [ ] **Step 2: Execute plan mode**

Run through the PowerShell-to-SSH Bash-safe pattern:

```bash
python3 wgs_control_plane_reset.py --mode plan \
  --receipt-root /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/audit/production-reset-20260824
```

Expected: exit 0; no service, DB, Redis or path mutation.

- [ ] **Step 3: Validate plan receipt**

Assert:

```text
hostname=server10610
active_dag_runs=0
airflow dag_run=0
airflow task_instance=0
airflow dag=3
biodemo analysis_run=2
biodemo user_account=1
redis keys=3
preserved volume=airflow-wgs_postgres-data
preserved network=192.168.199.0/24, gateway 192.168.199.1
```

If live counts have changed, stop and regenerate the inventory rather than weakening the checks.

### Task 3: Apply the irreversible control-plane reset

**Files:**
- Create remotely: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/audit/production-reset-20260824/apply-receipt.json`
- Create remotely: `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/audit/production-reset-20260824/post-reset-verification.json`

**Interfaces:**
- Consumes: reviewed plan receipt from Task 2 and exact confirmation string.
- Produces: stopped old application stack, empty recreated logical databases, empty Redis and cleared demo paths.

- [ ] **Step 1: Re-run preflight immediately before apply**

Expected: all values still match Task 2 and no active DAG run exists.

- [ ] **Step 2: Apply with the exact confirmation**

```bash
python3 wgs_control_plane_reset.py --mode apply \
  --confirm RESET-WGS-DEMO-CONTROL-PLANE:server10610:20260824 \
  --receipt-root /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/audit/production-reset-20260824
```

- [ ] **Step 3: Verify services and infrastructure**

Expected:

```text
frontend-nginx/backend/wgs-observer/airflow-scheduler/airflow-api-server/airflow-worker = stopped
postgres = healthy
redis = running
airflow-wgs_postgres-data = present
nipt_analysis_test_net = 192.168.199.0/24, gateway 192.168.199.1
```

- [ ] **Step 4: Verify clean logical state**

Expected:

```text
airflow database exists with zero user tables before migration
biodemo database exists with zero user tables before migration
redis DBSIZE = 0
all allowlisted demo paths absent or empty
all preserved paths still resolve to their original targets
```

- [ ] **Step 5: Record unrecoverable deletions**

The receipt and handoff must explicitly state that demo DB records, test files, old inactive releases, old environment backups and the obsolete shared SSH key were deleted without a data backup and cannot be recovered from this platform.

### Task 4: Record clean-reset state and handoff

**Files:**
- Modify: `CURRENT_STATE.md`
- Modify: `TASKS.md`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: Task 3 receipts.
- Produces: authoritative state that the old platform is intentionally stopped and the next task is the Airflow-only production release.

- [ ] **Step 1: Add T135 clean-reset status**

Record exact deleted and preserved targets, database/Redis counts before and after, stopped services, network/volume checks and receipt paths.

- [ ] **Step 2: Mark the next implementation boundary**

State that no frontend/backend/Airflow application is live after reset. The next plan must build and validate the minimal Airflow-only release, run migrations, create the new admin and then update `current`. cce-pipeline and WGS execution remain out of scope.

- [ ] **Step 3: Validate documentation and commit**

Run:

```bash
git diff --check
rg -n "T135|production-reset-20260824|airflow-wgs_postgres-data|nipt_analysis_test_net" \
  CURRENT_STATE.md TASKS.md HANDOFF.md
git add CURRENT_STATE.md TASKS.md HANDOFF.md
git commit -m "docs: record WGS demo control-plane reset"
```
