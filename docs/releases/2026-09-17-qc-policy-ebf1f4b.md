# WGS QC ebf1f4b policy and original metric presentation

## Production publication completed

User explicitly approved main/production merge and BS96 publication after
candidate acceptance. Commit fcc3fc9 pushed atomically to both GitHub refs;
normal local production main and production branch fast-forwarded. The
candidate-only statements below describe the preceding validation checkpoint.

- BS96/server96, chenjc6708:bioinfo520. No active analysis runs at preflight.
- Exact source release: /data/airflow-WGS/releases/20260917-qc-policy-fcc3fc9.
  Complete backend tree; comparison against the previously mounted application
  found exactly two changed files: wgs_qc_policy.py and its packaged JSON policy.
- Backend77e65737b68b ->8450fcef0b9f; image/dependencies unchanged,
  /app now mounts the new backend release read-only.
- Frontend9402a4fbb41b ->a64a0ab29b10;
  airflow-demo/frontend:qc-policy-fcc3fc9,
  sha256:8574521bdf9c973b618533539cf916eaa7ff36b2d5459d99b7012522149d29fb.
  Served JS index-ijHpYiTo.js, CSS index-BFPGoplr.css.
- Exact environments, other binds, nginx allowlist, ports and networks retained.
  Other10container IDs unchanged. Scantrue, autofalse, contract_v2true,
  GATK profile r2 unchanged. No analysis submitted or resumed.
- BS10610 backend targeted verification rerun32passed. BS96 cached isolated
  frontend build passed without dependency downloads. Compose config and nginx
  syntax checks passed; nginx gracefully reloaded after backend replacement.
- Actual client URL health/index/newJS200; empty login body422. Host-loopback
  gateway curl returned403 (Docker ingress path), so verified through the real
  approved client address instead; no whitelist changed.
- Deployed API:6samples,66pass individual judgments,30unknown only due to
  missing/inapplicable/individual-safe evidence. No unavailable-release reasons.
  All6coverage20X pass. Source aggregate remains5pass/1warn; no metric recompute
  silently promotes that warning. Automated browser visual check not performed.

Private effective Compose, rollback and before inventory:
`/data/airflow-WGS/qc-policy-fcc3fc9-control/{compose,rollback,before}.json`.
Only backend and frontend-nginx were recreated with --no-deps --pull never.
Global current symlink remains historical; actual mounts/images are authority.
Rollback: validate rollback.json, recreate only backend/frontend-nginx, then
nginx reload and real gateway checks. Preserve data and other services.

## Scope and cause

User approved restoring the original QC table while hiding threshold labels,
and completing judgment support for the screenshot's exact WGS release.
No native WGS script, analysis/QC source file, DB, DAG, scanner, pending, CCE or
GATK change. No whole-repository revert. Candidate only, not deployed.

BS96 read-only API for the screenshot run returned six samples:84 judgment
reasons were `Release policy provenance unavailable`,12 were individual-safe-
evidence unavailable. Thus restoring columns alone could not restore judgments.

## Source audit

Read-only BS10610/server10610 repository
`/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0`, Git2.49.0 at the documented
absolute miniforge path. Compared cc9bde3c8ee6ad1cd2f85cf5d2ef49c5611ac081 to
ebf1f4bf2512feecdc3762e463145130192ca8bb.

| File | ebf1f4b blob | Difference from audited base |
| --- | --- | --- |
| cfg/qc_config.json | ed2b6d0444e061192389bdeb9c821dbb4a625243 | None |
| rule/QC.smk | 6ec37ea779e5b3c0927906ccddbd3f9d7cb1a839 | None |
| script/g1.Collect_QC.py | 6f873080049af713f57e7dc993ef391108bcc3e7 | Two added lines in non-special item branch |
| script/g2.Collect_multiqc_QC.py | 10a8ffc543ed537421eb5609d75ba14c61615664 | None |

The g1 delta flags `bam.cov20x_pct <= 90` for non-special projects. Special
items Q0079/Q0080/Q0081/Q0082/Q0088 already had that check. ebf1f4b therefore
requires >90% for both branches. Exact variant metadata reuses unchanged base
criteria and records the changed blob; it is not falsely registered as an
identical release. cc9bde3/34bfcbf and unsupported releases retain old behavior.

## Verification

BS10610 candidate `candidates/qc-policy-20260917` under the Airflow control root.
Actual backend mount remains releases/20260916-onprem-main-d705a46/backend;
backend9943939015f6 unchanged. Executiontrue, scanfalse, autofalse retained.
Cached backend:t235-232154f and frontend-builder:node22-lock-35420d5e3ec0,
disposable --pull never --network none containers, synthetic fixtures only.

- RED: `pytest -q -p no:cacheprovider --tb=short tests/test_monitor_qc.py`:
  6failed/26passed because ebf1f4b remained unknown.
- GREEN: same targeted file32passed; covers90% fail,90.01% pass, missing/NaN,
  historical criteria, unknown release, source aggregate and private conditions.
- Frontend RED3failed/1passed; GREEN targeted WgsQcTab.test.tsx4passed.
  Verifies pass/fail/warn coloring, zero, per-sample judgment and no threshold
  text. `npm run build` passed; JS index-ijHpYiTo.js.
- BS96 read-only shadow evaluation of only the screenshot batch, in a separate
  Python process with candidate code/policy in memory. No service code or files
  replaced, no DB access or mutation. Six unique QC rows;66pass judgments,
  30unknown (12missing values,12inapplicable,6individual-safe-evidence missing).
  All six20X judgments pass;11metric columns have valid judgments. Source
  aggregate statuses and raw metric values unchanged. No clinical rows printed.

BS96 hostname server96, current symlink remains20260912-panel-opt-4d3d24e6;
actual backend77e65737b68b uses releases/20260917-sampleinfo-f72a12e/backend.
Direct SSH handshake failed; configured BS96 route succeeded. No authentication
or network configuration changed. No full suite, biological rerun or additional
batch test. GATK smoke remains explicitly paused.

## Publication and rollback

Not merged, pushed or deployed by this change. BS96 still serves the preceding
frontend/policy. Publication needs both backend policy and frontend together,
not a frontend-only rollout. Preserve other services and active workflows.
Rollback restores these code changes only; never rewrite QC artifacts, DB,
pending or analysis data. Historical aggregate QC remains source-authoritative.
