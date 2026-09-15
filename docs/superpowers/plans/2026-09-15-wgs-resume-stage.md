# WGS interrupted-stage recovery implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan. User limits validation to one necessary targeted RED/GREEN set, no full suite, matrix, production probes or extra canary.

**Goal:** Add a separate resume_stage action that continues WGS interrupted stages without new preparation or changing the frozen analysis identity.

**Architecture:** Reuse RunAction for idempotency, WgsStageExecution generations and current request/receipt state. An explicit resume-stage orchestration path dispatches only the selected and necessary remaining stages. Node200 reuses original frozen bundle/manifest and native checkpoint/journal behavior; a failed Master alone may be replaced with UID protection.

**Tech Stack:** FastAPI, SQLAlchemy, Airflow DAGs, Python node runtime, React.

**Spec:** Coordinator's user-approved WGS interruption recovery sections1–3, reproduced in constraints below. ETA section4 is separately owned and excluded.

## Global Constraints

- Base f241149 from D:/pipeline/airflow-demo-production; worktree wgs-resume-stage-20260915, branch jiucheng/feat/wgs-resume-stage-20260915. No main changes, deployment, production probe or real0911A recovery.
- Keep analysis_id, attempt, release, configuration, image and workdir unchanged; only step generation/retry grows. Same-task old lock can be inherited. No new lock system or full-file hash sweep.
- Only three guard categories: identity/configuration consistency, active-execution deduplication, necessary recovery inputs. Existing security/path permissions remain enforced.
- Step1 resumes existing transfer checkpoint; Step2 queries existing submitted Master before side effects; Step3 reuses active/success Master or replaces only an exact failed Master using original manifest and native resume semantics; Step4/5 reuse delivery capabilities; Step6 resumes existing materialization journal.
- No Step0, prepare, forceall, original prepare edits, pending changes, on-prem deletions, cluster configuration changes, CCE upgrade or requirement that OBS results be empty.
- Read-only stage queries reuse GATK stage_ready GET retry semantics: Airflow retries=6 (initial plus6 retries), retry_delay=30s, retry_exponential_backoff=true, max_retry_delay=5min per delay. No new request timeout/total-budget framework. Retry only408/429/5xx and transient connection failures, never authentication/parameter/business failures. Side effects are not blindly retried: query identity/state first on uncertain responses.
- Retain prior receipts/history, ignore stale generations, reset terminal timestamps only for the actual stage retry. Public source aggregate/history must not be silently overwritten by old failure snapshots.
- Coordinator owns backend/app/wgs_stage_estimates.py, frontend/src/lib/runProgress.ts, RunProgressBar, RunTracker, EstimatedStageProgress and frontend spec. Never edit those. RunDetailPage change restricted to recovery component import/render, no progress transformations.
- One targeted RED/GREEN test set in cached BS10610 environment. No local runtime test, downloads, full suite, repeated matrix or production probes. A single frontend production build is permitted as compile check. Further scope/validation needs user confirmation.

### Task 1: Integrated resume-stage path

**Files:**
- Create focused backend/app/wgs_resume_service.py and scripts/wgs_resume.py (operator/runtime recovery boundary); use existing neighboring modules for query retry if reusable.
- Modify backend/app/main.py, wgs_runtime_adapter.py and stage registration/projection only where needed to carry recovery action identity and generation.
- Modify dags/bio_wgs.py or a bounded resume DAG path to skip prepare and completed predecessors, preserve original attempt, dispatch selected and needed downstream.
- Modify scripts/wgs_runtime_gate.py to invoke the explicit recovery branch with the same request/worker safety model and handle state queries.
- Create frontend/src/features/run-detail/ResumeStagePanel.tsx and one focused test; modify frontend/src/api.ts and only action import/render in RunDetailPage.tsx.
- Tests: backend/tests/test_wgs_resume_stage.py and scripts/tests/test_wgs_resume.py as one bounded regression set; reuse actual current fixtures/SQLAlchemy/API where applicable. Do not construct another biological environment.
- Docs: docs/05_API_CONTRACT.md, docs/07_AIRFLOW_DAG_SPEC.md, docs/08_WORKFLOW_RUNTIME_INTEGRATION.md, docs/11_DEPLOYMENT_RUNBOOK.md for future packaging only, CURRENT_STATE/TASKS/HANDOFF.

**Interface:** proposed public POST `/api/runs/{analysis_id}/actions/resume-stage`, body `{attempt, stage, idempotency_key}`. Only canonical Step1–6 stage codes accepted, not prepare or maintenance. Response `{analysis_id, attempt, stage, generation, action_id, status}`. GET preview may be reused only if already available; do not invent an unrelated service. Use RunAction JSON for persistence, no new schema/lock framework. If existing dispatch needs a separate recovery DagRun identity, preserve original AnalysisRun and its current attempt and explicitly associate recovery action; original active-run observer must not reapply original DagRun failure.

Expected invariants to encode in the targeted test set:

```python
assert resumed.attempt == original.attempt
assert resumed.release == original.release
assert resumed.workdir == original.workdir
assert repeat_with_same_key.action_id == first.action_id
assert resumed.generation > interrupted.generation
assert not prepare_calls and not reset_calls and not upload_calls_for_step3
assert stale_receipt_is_ignored
assert active_master_is_reused_not_deleted
assert replacement_manifest == original_manifest
assert replacement_delete_precondition.uid == expected_failed_uid
assert sensor.retries == 6
assert sensor.retry_delay.total_seconds() == 30
assert sensor.retry_exponential_backoff is True
assert sensor.max_retry_delay.total_seconds() == 300
```

- [x] Read current request/registration/gate/DAG and dispatch contracts; report any necessary interface adjustment before broad edits.
- [x] Write bounded failing tests for action identity/idempotency, failed/active Master choice, transfer/journal reuse, stale receipt fencing and read-query retry budget. Baseline RED observed after documented setup corrections.
- [x] Implement complete vertical slice with existing primitives. Unknown side-effect outcome is queried/reconciled, not blindly resubmitted. Preserve successful outputs and failed evidence.
- [x] Run the same targeted GREEN set plus action UI test/build; fix actual failing assertions without expanding scope.
- [x] Self-review, document actual commands and limits, commit only this task. Parent performs one combined spec/code review; fixes rerun only affected tests.
- [x] Prepare independent scoped commit for coordinator integration with ETA; no merge/push main or deployment.
