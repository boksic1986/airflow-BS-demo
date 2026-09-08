# T240 Dashboard Attention and Sample Information Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace duplicate dashboard summaries with actionable attention data, restrict WGS intake to unresolved work, and simplify the Samples inventory with privacy-safe order metadata.

**Architecture:** Keep shared dashboard and sample endpoints registry-driven. Generic failure/reanalysis alerts are projected from business rows; WGS-specific intake/lifecycle alerts are supplied through an adapter callback. The frontend consumes explicit statuses and never infers workflow or privacy-sensitive values.

**Tech Stack:** FastAPI, SQLAlchemy, React, TypeScript, Vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-09-09-dashboard-attention-sample-information-design.md`

## Global Constraints

- Automatic analysis remains paused.
- Do not change scanner timing, Airflow, CCE, OBS, SFS, or workflow execution.
- Never persist or return raw order identifiers.
- Validate runtime behavior remotely with cached images, `--network none`, and `--pull=false`.

---

### Task 1: Privacy-safe sample projection

**Files:**
- Modify: `backend/app/wgs_platform_service.py`
- Modify: `backend/app/pipeline_registry_service.py`
- Modify: `backend/tests/test_wgs_only_platform.py`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/pages/SamplesPage.tsx`
- Test: `frontend/src/WgsProductionUi.test.tsx`

**Interfaces:**
- Produces: `OperatorSample.order_number_masked?: string | null`, `test_project?: string | null`, and optional `status_reason?: string | null`.
- Consumes: existing `Sample.metadata_json` and adapter `project_sample_summary`.

- [x] **Step 1: Add backend and frontend tests for the six-column Sample Information table and masked order output.**
- [x] **Step 2: Run focused tests and confirm failures are caused by the missing projection and old table.**
- [x] **Step 3: Add a pure masking helper and store only `order_number_masked`, plus controlled test project metadata, during WGS sample synchronization.**
- [x] **Step 4: Expose those safe fields through the WGS adapter and render the approved table.**
- [x] **Step 5: Re-run focused tests and confirm raw order values and FASTQ headings are absent.**

### Task 2: Intake attention projection and dashboard alerts

**Files:**
- Modify: `backend/app/pipeline_registry.py`
- Modify: `backend/app/pipeline_registry_service.py`
- Modify: `backend/app/dashboard_service.py`
- Modify: `backend/app/wgs_t7_intake.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_wgs_t7_intake.py`
- Test: `backend/tests/test_dashboard_api.py`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/features/dashboard/DashboardOverview.tsx`
- Modify: `frontend/src/features/dashboard/IntakeScannerPanel.tsx`
- Modify: `frontend/src/components/IntakeDiscoveryTable.tsx`
- Test: `frontend/src/WgsProductionUi.test.tsx`

**Interfaces:**
- Produces: overview `attention_items` with stable category, severity, title, detail, analysis/batch identity, and timestamp.
- Produces: intake `view=attention` rows with backend-projected analysis state.

- [x] **Step 1: Add failing backend tests for intake filtering/status precedence and bounded privacy-safe alerts.**
- [x] **Step 2: Implement the minimal registry-owned projections and retain legacy overview fields for compatibility.**
- [x] **Step 3: Add failing frontend tests for removed widgets, Total label, alert rows, renamed intake panel, and removed view buttons.**
- [x] **Step 4: Implement the two-card overview, single intake queue, and retained-data refresh behavior.**
- [x] **Step 5: Re-run focused backend/frontend tests.**

### Task 3: Centering, documentation, validation, and release

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `docs/04_DATABASE_SCHEMA.md`
- Modify: `docs/05_API_CONTRACT.md`
- Modify: `docs/06_FRONTEND_SPEC.md`
- Modify: `docs/11_DEPLOYMENT_RUNBOOK.md`
- Modify: `CURRENT_STATE.md`
- Modify: `TASKS.md`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: Task 1 and Task 2 response contracts.
- Produces: a validated candidate; production recreation remains separately approved.

- [x] **Step 1: Add a frontend assertion for centered status content, then change the internal badge wrapper to center.**
- [x] **Step 2: Run the complete focused test selection and production TypeScript/Vite build on the approved remote builder.**
- [x] **Step 3: Update contract, frontend, database, deployment, task, state, and handoff documents with exact evidence.**
- [x] **Step 4: Commit and integrate to main. Production release and live verification require separate approval.**
