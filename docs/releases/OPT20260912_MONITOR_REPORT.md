# OPT20260912 Task2 monitor implementation

Source: development worktree, implementation based on Task1 d5a4e1d plus
coordination-only09efb4f. No Task1 submission/security/config code reverted.
Implementation commit is the commit containing this report; coordinator owns
central state/handoff and subsequent independent review/deployment.

## Delivered

- Rule API current-attempt default, explicit history, ANDed exact sample/family
  filters, projected-status query semantics, stable SQL pagination and complete
  filtered phase summaries. No current-success inference for historical rows.
- Rule UI server filters/history/pagination and full attempt/instance keys;
  stream origin and expandable group evidence; explicitly labelled inferred
  success. Unknown rules remain Unknown rather than Variant analysis.
- Group JOB_STARTED emits descriptive rule_planned members, never child starts.
  Legacy group-only starts have no individual timing; original stream identity
  is preserved. Explicit same-instance restart clears prior terminal/start time.
- Pinned cc9bde3 per-value QC with numeric units, inclusive/strict bounds,
  reasons and source provenance; source aggregate/legacy metrics preserved.
  Special project, relation-dependent depth, sample-type GC/SNV/CNV ranges,
  BKW, effective bases, duplication, coverage, fold80, contamination and
  rare-disease g2 values are represented. Missing conditions/values are unknown.
- WGS and GATK Step4/6 fixed display estimate snapshots in existing execution
  metadata. Writer records baseline on first actual running observation; queued
  and terminal-only events do not invent starts. Latest20 matching successful
  stage durations, minimum3, median, eased max99; actual success100. Terminal
  failure/cancel freezes and a new generation resets. Read APIs are side-effect
  free. Workspace/progress/rail/dashboard display measured progress first.

## Exact owned files

Backend app: main.py, dashboard_service.py, pipeline_registry_service.py,
gatk_runtime_service.py, gatk_workspace_service.py, wgs_observer.py,
wgs_sample_projection.py, wgs_stage_execution_service.py,
wgs_stage_estimates.py, wgs_timing_service.py, wgs_workspace_service.py,
workflow_phases.py, wgs_qc_policy.py, policies/wgs_qc_cc9bde3.json.

Backend tests: test_monitor_rules.py, test_monitor_qc.py,
test_monitor_estimates.py, test_wgs_only_platform.py,
test_wgs_timing_service.py, test_workflow_phases.py.

Logger: dags/snakemake_logger_plugin_airflow_demo/__init__.py and
dags/tests/test_snakemake_logger_plugin.py.

Frontend src: api.ts, styles.css, WgsProductionUi.test.tsx,
components/RunTracker.tsx, components/EstimatedStageProgress.tsx,
features/run-detail/CurrentProgressPanel.tsx and .test.tsx,
features/run-detail/RunWorkflowTab.tsx and .test.tsx,
features/run-detail/QcMetric.tsx and .test.tsx, pages/RunDetailPage.tsx.

Docs:05_API_CONTRACT.md,06_FRONTEND_SPEC.md,
08_WORKFLOW_RUNTIME_INTEGRATION.md and this report.

## Test evidence

Remote target verified server10610, current81587fc, actual backend release
mounts and scanner/dispatchfalse. Only isolated synthetic source/fixtures under
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/OPT20260912-monitor`
were used. No Docker Hub/npm installs, live databases, real submissions,
restricted gate changes, source project edits or service/worker/Master restart.
Cached images: backend:t235-232154f and
frontend-builder:node22-lock-35420d5e3ec0, all docker tests --network none.

Red regressions (exit1, expected): current attempt returned3 rather than2;
missing complete summaries; legacy group start populated child timestamp;
logger group start marked both children running; sample/family exact DOM
controls absent; estimates and pinned-policy modules absent; unknown rule
misclassified Variant analysis; GATK terminal-only status invented start;
same-instance restart retained previous ended_at. Green checks below cover them.

Final backend command, cwd source/backend, PYTHONPATH=/src/backend:/src/dags,
TMPDIR=/src (source is the task evidence mount):

```text
pytest -q tests/test_monitor_estimates.py tests/test_monitor_qc.py tests/test_monitor_rules.py tests/test_gatk_runtime_service.py tests/test_gatk_terminal_reconciliation.py tests/test_workflow_phases.py tests/test_wgs_timing_service.py tests/test_gatk_workspace_api.py ../dags/tests/test_snakemake_logger_plugin.py tests/test_wgs_observer.py tests/test_wgs_only_platform.py -k 'monitor or rules_use_sql or qc or sample_projection or phase or timing or gatk or SnakemakeLogger or observer'
```

Result:129 passed,1 existing skip,54 deselected, one upstream anyio deprecation
warning; exit0 in13.42s. Durable output: backend-final.log in the evidence root.
Earlier full observer file:58 passed. Query-budget regression stays <=8 calls;
complete summaries derive the total, not an extra count query.

Frontend command:

```text
vitest run src/WgsProductionUi.test.tsx src/features/run-detail/RunWorkflowTab.test.tsx src/features/run-detail/CurrentProgressPanel.test.tsx src/features/run-detail/QcMetric.test.tsx src/components/RunTracker.test.tsx
```

Result:32 passed,1 failed (33 tests); exit1. The remaining failure is existing
Dashboard `getByText("Total")` ambiguity owned by Task3, not skipped or fixed
here. All16 focused component tests and16/17 WgsProductionUi tests pass.
The directly affected sample-request assertion now expects visible-tab refresh
for Overview/Samples/QC, not one request across all tab switches.

`npm run build` (tsc -b and Vite) exit0; JS index-Coo9IdRV.js,
CSS index-icRWI_4z.css. Local git diff --check passes; local runtime tests were
not run. Independent pinned-commit review and test UI deployment/browser
acceptance remain coordinator actions, not claimed by this report.

## Policy provenance and honest gaps

Audited source commit cc9bde3c8ee6ad1cd2f85cf5d2ef49c5611ac081; source Git blob
identities are packaged with the policy and policy SHA256 is returned at runtime.
No mutable owner HEAD reads occur in application code. 31de5fb has the same
qc_config blob but different g1 and QC.smk blobs: it deliberately remains
policy-unavailable. Other historical policies need separate audit/registration.

g1 QCstat does not carry standalone SNV/CNV counts or safe peddy decisions;
those individual values remain unknown in real projections unless a future
approved artifact provides them. Sex-match reads only the safe source judgment.
No peddy free-text or patient identity is returned. Rare-disease extra values
require the exact optional sample.multi.QC.tsv; missing artifacts stay unknown.
Incomplete metric projection never recomputes or overrides the source aggregate.

Missing historical child starts cannot be recovered without authentic worker
events. Master/worker descriptions without explicit correlation remain separate
origins. Logger source tests do not prove image activation: existing active
Master/worker images are untouched; future reviewed image/release activation
and controlled synthetic execution acceptance are still required.

Existing running stage generations without a frozen estimate remain
indeterminate; GET never backfills them from later history. No3 matching prior
complete stage executions means no estimate. Real cloud stage acceptance was
not simulated by fabricated runtime evidence.

## Risks and rollback

Additive fields and reserved JSON metadata only; no destructive migration.
Rollback reverts this implementation commit/restores the prior test source
release, retaining raw events, execution records and result files. Do not delete
test/production databases, shared source, pending ledgers or analysis outputs.
Production authorization and deployment are explicitly outside this task.
