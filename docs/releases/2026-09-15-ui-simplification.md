# UI-SIMPLIFY-20260915 — source only

Base:16cc5c48175f4f8cde9cca906cec68f23242284a.
Editing worktree:D:/pipeline/airflow-demo-worktrees/wgs-eta-production-20260915.
No production deployment or0911A recovery in this task.

## Delivered scope

- WGS QC: all available pass/fail/warn metrics are columns in one horizontally
  scrollable table; actual threshold in heading. Different sample criteria use
  “按样本” heading and the specific threshold alongside each value. Reason is
  last and explains failed/warning metrics. Missing judgments stay omitted,
  source aggregate retained; no raw JSON, provenance or nested review table.
- Contamination source audit: BS10610 read-only fixed Git executable
  /sg2/33.chenjiucheng/software/miniforge3/bin/git in
  /bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0;
  git show34bfcbf:script/g1.Collect_QC.py lines174–190 confirms strict
  CHARR>0.03 AND AB>0.15 fail, otherwise CHARR>0.02 AND AB>0.1 warn,
  otherwise pass. Lines535–539/586–588 include this in native QC output.
  Platform now computes the metric judgment from both finite values and shows
  CHARR/AB, not a bare source PASS string. Missing values cannot pass.
  Source status remains diagnostic evidence, not an override of numeric criteria.
  This was a code audit, not re-reading the screenshot sample's private values.
- Logs: literal case-insensitive matches marked without interpreting HTML;
  server results highlight their returned query, avoiding stale-query mismatch.
- Rules: shared default running/20/active_first, reset offset on filters;
  selectable other statuses and server pagination retained. Group inventory
  and opaque master origin removed from display, not from stored/API evidence.
- Stage graph: no Step4/6 estimate/missing-history text; hover shows recorded
  started_at/ended_at, missing timestamps explicitly unrecorded. Shared estimates
  in RunTracker/Current Progress unchanged; no second formula.

## Bounded evidence

BS10610 hostname server10610; control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS.
Current release remains releases/20260912-opt-4d3d24e6; actual backend378bd2b8eb10
mount is releases/20260913-panel-1fb971b/backend. Existing execution gate true,
scan/auto false were inspected before tests; no service/gate mutation.
Task candidate:candidates/platform-followup-20260915; only task-local source
files copied. Production BS96 was not contacted; existing releasef69c577 retained.

Red: targeted new backend cases7 failed; frontend new contracts8 failed/3 passed.
Green: offline ephemeral containers, --pull never --network none:

- backend image airflow-demo/backend:t235-232154f, tmpfs/synthetic fixtures:
  python -m pytest -q -p no:cacheprovider --tb=short
  tests/test_monitor_qc.py
  tests/test_wgs_timing_service.py::test_orchestration_hover_times_use_recorded_stage_times_not_run_success
  =>27 passed.
- frontend image airflow-demo/frontend-builder:node22-lock-35420d5e3ec0:
  npm test -- --run src/features/run-detail/WgsQcTab.test.tsx
  src/features/run-detail/RunWorkflowTab.test.tsx src/components/LogViewer.test.tsx
  src/components/WgsEstimatedProgress.test.tsx =>14 passed.
- npm run build =>tsc+Vite passed;
  JS index-D0dEP3V_.js, CSS index-BKKZXC-a.css. Not deployed assets.

No full/redundant suite or live workflow/browser test. No DB/schema changes,
DAG/runtime/prepare/pending/CCE changes, node activation, data deletion or
0911A action. New production publication is a separate authorization.
Rollback source by reverting this slice; no production rollback needed.
