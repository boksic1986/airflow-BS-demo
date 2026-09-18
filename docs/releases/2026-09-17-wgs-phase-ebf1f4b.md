# WGS ebf1f4b Phase mapping

Source promotion completed: both remote main and jiucheng/release/production
verified at e7f0373918cabea10c6ea68b73662f63795599a4. The documentation-only
completion commit follows it; no additional application changes or deployment.

Scope: user requested fixing Unknown Phase and promoting code to main and
jiucheng/release/production. This is source-only; no BS96 deployment, restart,
database update, workflow run or WGS script modification in this task.

## Cause and audit

The exact-release Phase catalog includes cc9bde3 and34bfcbf, but omits
wgs-4.2.1-ebf1f4b. The cleanFastq rule mapping already exists; the unsupported
release therefore returns Unknown for all its rules. Do not replace this with
a guessed prefix mapping or alter rule event status/timing.

Read-only source audit on server10610 using Git2.49.0 at
/sg2/33.chenjiucheng/software/miniforge3/bin/git and repository
/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0 compared all14 catalog source
blobs against ebf1f4bf2512feecdc3762e463145130192ca8bb. Twelve blobs are identical.
The two differences preserve their full rule-name inventories and phases:

| Source | New blob | Reviewed difference |
| --- | --- | --- |
| rule/ROH.smk | 764355f20b21a05e1d184f707c2396d74bfffaae | MIE selects dedicated slivarjs_MIE config keys;7rule names unchanged |
| rule/WGS_SNV.smk | 8a027c7556d72a418631dc99da4faa5ef84841a1 | vep adds two gnomAD annotation fields;36rule names unchanged |

The policy records both overrides beside the exact release opt-in. Phase
equivalence does not claim byte-identical scientific behavior or QC thresholds.
No rule catalog is duplicated; unknown releases and unlisted rules stay Unknown.

## Validation

BS10610 isolated candidates/wgs-phase-ebf1f4b under the approved control root.
Live backend c497d821b719/native-ui-76915d8-r2 remains untouched. Cached image
8491604ee01d,network none,read-only source/root,nonroot6708:520,tmpfs/testwork;
no package downloads, production data or additional analysis batches.

- RED: test_wgs_phase_release_34bfcbf.py:1failed/6passed; exact ebf1f4b API
  returned Unknown for cleanFastq/mapping/Dedup as in the screenshot.
- GREEN: same file plus test_monitor_phases.py and test_monitor_rules.py:
  30passed in5.97s. Covers rule list, Phase filtering, complete phase summary,
  phase definitions, old releases, unknown release/rule and existing GATK rules.
- One pre-existing Starlette/anyio deprecation warning; no test errors.
- Initial SCP through18 reset pre-auth; direct BS10610 SCP succeeded. No SSH
  configuration, host trust, credentials or permissions changed.

Full workflow/full suite omitted per user's bounded-testing request. Source
fix requires a later approved backend/observer rollout before BS96 UI changes;
the existing deferred ledger heartbeat remains restricted to the ledger patch.
Rollback restores the phase policy/module only; no event or analysis data edits.
