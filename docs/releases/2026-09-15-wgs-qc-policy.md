# WGS QC policy completion — 2026-09-15

Source-only scope: exact release mapping and WGS QC metric visibility. No CCE
upgrade, DAG change, native threshold change, prepare/pending change or deployment.

## Source evidence

Read-only BS10610 (`server10610`) repository
`/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0` (historical directory name).
Git `/sg2/33.chenjiucheng/software/miniforge3/bin/git`, version2.49.0.
Compared `git rev-parse` and `git ls-tree <commit> -- <four paths>` at:

- Original audited: `cc9bde3c8ee6ad1cd2f85cf5d2ef49c5611ac081`.
- Current exact release: `34bfcbf82238af684d005314360c9c9739377351`.

Identical blobs at both commits, also matching packaged policy provenance:

| Path | Git blob |
| --- | --- |
| cfg/qc_config.json | ed2b6d0444e061192389bdeb9c821dbb4a625243 |
| rule/QC.smk | 6ec37ea779e5b3c0927906ccddbd3f9d7cb1a839 |
| script/g1.Collect_QC.py | 4ab43e7f93b7ade84fd79cdc8232e61800e8fcc9 |
| script/g2.Collect_multiqc_QC.py | 10a8ffc543ed537421eb5609d75ba14c61615664 |

This is QC-specific evidence, not inference from the prior phase-map audit.
`wgs-4.2.1-34bfcbf` is an exact metadata allowlist entry. Judgments record its
actual source_commit, original policy_source_commit, unchanged source blobs and
current packaged-policy SHA256. No latest/prefix fallback; unknown releases or
missing inputs stay unknown in API. Source aggregate remains authoritative.

## Presentation

Reuse WgsQcTab/QcMetric/data-table/StatusBadge. Main key columns and detailed
metrics show only existing pass/fail/warn judgments with finite numeric or
nonempty string values. Zero and source-produced status results remain visible.
Entries without a judgment, or with unknown, missing or inapplicable data, are omitted, including
the optional raw diagnostic disclosure. Entire absent key columns disappear;
mixed-sample missing cells use a dash. Empty detail says
`暂无可展示的质控判定指标`. No frontend thresholds or aggregate calculation.
The backend retains all diagnostics; missing UI data never implies QC success.

## Bounded verification

BS10610 current20260912-opt-4d3d24e6; actual backend mount20260913-panel-1fb971b,
executiontrue/scanfalse/autofalse preserved. Candidates under
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/platform-followup-20260915`.
No live container modified. Cached backend:t235-232154f and
frontend-builder:node22-lock-35420d5e3ec0 ran disposable `--network none` containers
with read-only candidate sources; backend scratch tmpfs, no production DB/data.

- Backend RED new release tests:2failed/1passed/17deselected, expected unknown.
- UI RED:3failed, expected old unfiltered behavior.
- `pytest -q -p no:cacheprovider --tb=short tests/test_monitor_qc.py`:20passed.
- `npm test -- --run src/features/run-detail/WgsQcTab.test.tsx`:3passed.
- `npm run build`:TypeScript and Vite passed.

No full suite or unrelated resume/ETA tests, native execution or visual browser
deployment check. Source Git synchronization is separate from96 deployment.
Rollback only these source changes; preserve DB, catalogs, pending and results.
