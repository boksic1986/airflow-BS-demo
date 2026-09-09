# WGS obsutil Checkpoint Progress Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Switch new WGS Step1/Step5 transfers to obsutil while retaining exact per-file progress in the current Transfers UI.

**Architecture:** The Airflow-owned obsutil wrapper parses request-scoped multipart checkpoints and publishes privacy-safe file-keyed child snapshots. The runtime gate reconciles those snapshots with its immutable transfer plan and emits the existing v2 aggregate/file contract consumed by the observer, database, API and React table. CCE orchestration and non-transfer stages do not change.

**Tech Stack:** Python 3.11, pytest, React/TypeScript, Vitest, FastAPI observer projection, Huawei obsutil checkpoint XML.

---

### Task 1: Lock the checkpoint and configuration contracts with failing tests

**Files:**
- Modify: `scripts/tests/test_wgs_obsutil_progress.py`
- Modify: `scripts/tests/test_wgs_runtime_gate.py`

1. Add upload/download XML fixtures covering correct nested size paths, completed parts and a partial XML read.
2. Add a wrapper test proving output contains a plan-derived file key/name but no source path or OBS URI.
3. Add gate tests proving file-keyed child rows become v2 rows, unstarted plan files remain accepted, and exact Step5 local files become success.
4. Add a configuration test requiring `transfer_adapter=obsutil`.
5. Run the focused tests on the approved remote development host and confirm they fail for the missing behavior.

### Task 2: Parse checkpoints and publish file-keyed obsutil snapshots

**Files:**
- Modify: `scripts/wgs_obsutil_progress.py`
- Modify: `scripts/configure_node200_cce.py`

1. Parse `-cpd` safely and read upload/download checkpoint XML without following evidence outside that directory.
2. Match the active command to a frozen plan entry and emit only its SHA-256 key and basename.
3. Prefer monotonic checkpoint bytes, retain stdout fallback, and keep transfer execution independent from monitoring failures.
4. Record start/end timestamps and verified terminal state.
5. Set the node200 transfer adapter to obsutil.

### Task 3: Aggregate obsutil file evidence into transfer-progress v2

**Files:**
- Modify: `scripts/wgs_runtime_gate.py`

1. Pass the stable transfer-plan path to every wrapped obsutil process.
2. Build file states from the frozen plan and file-keyed child rows.
3. Mark exact existing Step5 payloads complete without counting unrelated control objects.
4. Recompute aggregate totals/status/current file from file rows and preserve the old aggregate-only fallback.

### Task 4: Clarify the Transfers UI

**Files:**
- Modify: `frontend/src/features/run-detail/WgsTransfersTab.tsx`
- Modify: `frontend/src/features/run-detail/WgsTransfersTab.test.tsx`

1. Show `obsutil` as the transfer engine when the progress source identifies it.
2. Render pre-checkpoint accepted/running rows as `Waiting for checkpoint`.
3. Preserve the current exact byte display, file sorting and no-flash refresh behavior.

### Task 5: Update contracts and repository state

**Files:**
- Modify: `docs/05_API_CONTRACT.md`
- Modify: `docs/06_FRONTEND_SPEC.md`
- Modify: `docs/30_WGS_STEP1_6_CONTRACT_V2.md`
- Modify: `TASKS.md`
- Modify: `CURRENT_STATE.md`
- Modify: `HANDOFF.md`

Document obsutil as the selected transfer adapter, the checkpoint-derived v2
contract, unchanged CCE/stage boundaries, validation evidence and rollback.

### Task 6: Validate candidate and gate production activation

1. Run focused script tests, backend observer tests, frontend Vitest and the offline production build on the approved remote host.
2. Run a bounded multi-file obsutil upload/download canary below `/sg2/50.ctapa/project/HWcloud/WGS_test/cce-evidence/T241-obsutil-checkpoint-20260909` without exposing private configuration.
3. Verify exact bytes/files, active-file ordering, terminal verification and cleanup.
4. Only after all gates pass, synchronize the wrapper/config/runtime source and activate the new adapter; keep automatic dispatch paused and verify non-target services are unchanged.
