# Task2 review at7033185 — fix round1

Independent monitor_review: Spec not compliant, quality needs fixes; no Critical.
Read-only diff/source review; no tests rerun or remote changes. Runtime logger
image activation remains explicitly unverified and outside panel deployment.

## Important findings

1. Required biological phase/group view not implemented. workflow_phases.py:127-143
   changes only unknown fallback; mapping/calling and distinct variant analyses
   remain four coarse WGS phases, no release input; unknown GATK returns GATK at186.
   RunWorkflowTab.tsx:107 expands only opaque group ID, not member rules. Implement
   pinned finer phase mapping and expandable member groups, unknown for both pipelines.
2. QcMetric.tsx:9 colors from source value rather than judgment.status. Unsupported
   policy returns value PASS with judgment unknown (wgs_qc_policy.py:83), rendering
   green PASS. Label source value neutrally and color only from backend judgment;
   DOM regression for unsupported-release PASS.
3. main.py:1770 ignores canceled counts in phase summaries; all canceled and
   completed+canceled phases appear planned. Define terminal/mixed cancellation
   precedence with API/UI tests.

## Minor findings carried into this fix

- wgs_stage_estimates.py:64 overrun remains true for failed/canceled; component
  EstimatedStageProgress.tsx:8 says Still executing. Freeze percent but show terminal
  appropriate wording.
- test_monitor_estimates.py:71-120 GATK lacks explicit mismatched pipeline/release/
  target exclusion and failed/canceled generation followed by retry tests.

## Other disclosed test ownership

Known Dashboard Total ambiguity belongs Task3, cannot claim final frontend green.
Upstream anyio deprecation and preexisting skip remain disclosed; no ignored errors.

## Positive checks

Current/default/history and exact filters, SQL pagination/complete summaries,
no fabricated group starts, audited cc9bde3 numeric bounds and fixed generation
writer estimates verified. Reviewer inspected exact g1/g2/QC.smk Git objects,
observer/WGS/GATK writer callsites and silent-refresh fencing for concrete risks.
