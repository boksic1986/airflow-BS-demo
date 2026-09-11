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

## Review fix round1 (base7033185, coordination parent760dbd0)

All three Important findings and both carried Minor findings are addressed.
Fine phases now use exact rule inventories, including prefixed aliases actually
declared by WGS_pipe.smk, rather than accepting arbitrary module prefixes.
The packaged WGS phase catalog records source blob IDs at cc9bde3 for each
module and cloud wrapper. GATK uses bd04f6d:workflow/SCMC_GATK.smk,
blob0ee4e0033a1d5e0dbf0e62c0264136749173304a. APIs, registry progress,
observer projections and sample current-stage labels pass the run release.
Unsupported/missing release or unlisted rule returns Unknown. No current
owner source was modified or read via mutable HEAD.

Group events now carry full member rule/job-ID inventories, and the UI expands
those names even across Rule API page boundaries. Stream-scoped group identity
and group-only/no-child-start semantics remain intact. Legacy missing inventory
is explicitly unavailable; neither a synthetic member list nor child times are
inferred. QC source PASS with unknown judgment has no successful green badge.
Phase precedence is failure > running > unresolved planned > terminal canceled
> success (possibly with skipped) > all skipped. Terminal estimates retain the
frozen percentage with terminal wording rather than Still executing.

Red evidence: fix-red-backend.log has17 failed/3 passed (new release argument
absent and Mapping phase filter returned0); fix-red-ui.log has3 failed/10 passed
(member expansion, unknown PASS color and terminal wording). The initial UI
cancel assertion matched a table header and was tightened to assert the status
badge before final green; API mixed terminal coverage checks the returned status.
First green:45 passed/1 existing skip backend,13 passed UI. Extended regression
then exposed one obsolete historical phase-order assertion:82 passed/1 failed/
1 skip. Its historical1656b5d fixture now explicitly expects Unknown, consistent
with the release audit boundary, and was rerun successfully.

Final backend command (same isolated cached environment as above):

```text
pytest -q tests/test_monitor_phases.py tests/test_monitor_rules.py tests/test_monitor_estimates.py tests/test_monitor_qc.py tests/test_workflow_phases.py tests/test_gatk_evidence_projection.py tests/test_gatk_workspace_api.py tests/test_gatk_runtime_service.py tests/test_wgs_timing_service.py tests/test_wgs_only_platform.py::test_wgs_rules_use_sql_pagination_and_batched_eta_queries tests/test_wgs_only_platform.py::test_wgs_detail_rules_and_pods_are_database_only_authenticated_reads tests/test_wgs_observer.py::test_master_rule_status_uses_binding_attempt_for_logger_local_attempt ../dags/tests/test_snakemake_logger_plugin.py
```

Result83 passed/1 preexisting skip, one upstream anyio deprecation, exit0
(fix-final-backend.log). Includes explicit GATK mismatched pipeline/release/
target exclusions; failed and canceled generations freeze at62.6%, late old
evidence cannot mutate retry, and newly running retry starts at0%. SQL query
budget and current/history inference remain green. No full WGS suite was run.

Final UI: vitest run QcMetric, RunWorkflowTab, EstimatedStageProgress,
CurrentProgressPanel and RunTracker test files:20 passed, exit0
(fix-final-ui.log). npm run build: tsc/Vite exit0 (fix-build.log),
JS index-BWshhGpf.js and CSS index-icRWI_4z.css. Task3's previously disclosed
Dashboard ambiguity is outside this focused run and is not claimed fixed.

Additional owned paths: policies/wgs_phases_cc9bde3.json,
test_monitor_phases.py, test_gatk_workspace_api.py, test_wgs_observer.py,
EstimatedStageProgress.test.tsx, plus amended Task2 files listed above.
Local git diff --check passes. Runtime preflight again verified server10610,
current81587fc, actual backend source mount and scan/dispatchfalse. An initial
read-only inspect used the wrong container name and returned No such object;
the actual airflow-wgs-backend-1 was then verified before tests. No deployment,
worker/Master restart, shared WGS edit, live database or real job occurred.
Producer image activation and historical evidence gaps remain unchanged;
coordinator owns scoped re-review, central state and test-panel deployment.
