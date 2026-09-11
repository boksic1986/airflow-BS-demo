# OPT20260912 Rule/QC source findings

Static inspection only, not a live production diagnosis.

- main.py run_rules query has no attempt argument/default filter; it orders all attempts and paginates. Frontend getRunRules has no attempt option. A route freshness check does not remove historical rows.
- RunWorkflowTab combines sample/family values with OR and uses incomplete row keys (rule/sample/sequence). Separate exact filters and full attempt/instance keys required. Screenshot anomalies may combine these problems; don't claim one root cause without replay fixture.
- Platform logger hashes stream_id into instance identity; observer groups by instance ID. Master and worker descriptions can remain separate. Do NOT simply discard stream_id: job IDs may be local or reused by retries; cross-stream merge requires explicit execution/correlation evidence, otherwise retain separate observed instances with origin.
- Existing logger expands group JOB_STARTED into all members, falsely implying simultaneous child starts; no equivalent exact member terminal propagation. Preserve group execution evidence separately; only actual child execution events can provide child starts. Legacy starts with known group-only provenance must be labelled non-individual, not timed as real rule execution.
- WGS QC endpoint delegates to sample projection. _read_qc currently allowlists5 metrics and trusts aggregate 是否通过质控; no per-value threshold/reason/provenance.
- Owner cc9bde3 policy includes type-specific mapped/GC/SNV/CNV thresholds; item IDs Q0079/Q0080/Q0081/Q0082/Q0088 affect Q30/depth/effectivebases/dup/20X; non-special relative depth30/20; BKW selects different SNV range; F57J/UPC triggers g2-derived bases/depth/Q30/30X/10X/dup checks. fold80/sex/contamination/peddy also affect aggregate. Freeze/version policy rather than use live HEAD for old runs.

Baseline remote tests on unchanged deployed81587fc: tests/test_wgs_timing_service.py tests/test_workflow_phases.py scripts/tests/test_heavy_global_snapshot.py,26 passed in2.84s, cached backend/networknone on BS10610. New regressions still required before fixing.
