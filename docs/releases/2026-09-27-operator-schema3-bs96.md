# Operator schema3 preparation compatibility — 2026-09-27

## Scope and authorization

User requested: fix, commit code, retry the failed second preparation step.
Run `WGS_20260927_090701_56DC81`, batch `20260919A-test`, attempt2 failed
`prepare_wgs_analysis` before WGS prepare. This is not native Step2 Master startup.
Native0.8.7 Operator schema3 validates without `paths`; the platform gate still
required legacy `paths.repository_root`. Source fix `a1c5387` uses a shared
transformation in preparation and Step7 frozen-config comparison. No native
CLI, image, profile, WGS rule, reference data or credential change.

## Verification

BS10610/server10610 isolated cached backend image, `--network none`, synthetic
fixtures only, readonly candidate scripts mount. Focused pytest selection:
`schema3_operator_without_paths or operator_config_rejects_missing or
materialized_release_operator or step7_cleanup_sanitizes`.
Result: **6 passed,77 deselected**. Both new compatibility cases first reproduced
the mismatch. Existing fixture loader was corrected to register its module in
`sys.modules`; unchanged paired helper included in the isolated test snapshot.
No full suite, production runtime test or extra cloud Job was launched.

## Deployment

- BS96/server96 control root `/data/airflow-WGS`; backend mount remains
  `/data/airflow-WGS/releases/20260927-p0-local-84510df/backend`.
- SSH through BS with `id_rsa_ctapa` to node200/t640, uid6801/gid520.
- Only `/home/ctapa/.config/airflow-wgs/wgs_runtime_gate.py` atomically replaced.
- Before SHA256: `60ef3d78497347565d061491abf19176fd8a8dd9012685b7ead0ed841e53796e`.
- After SHA256: `08c236984cc64d1bd209468e92d88828abb11998ded8a66d641c64218422eefd`.
- Exact rollback copy:
  `/home/ctapa/.config/airflow-wgs/.operator-schema3-20260927/wgs_runtime_gate.before.py`.
- Existing private script owner/mode preserved (ctapa,0600). Business output
  permissions unchanged. No service restart; scanner/dispatch flags unchanged.
- Paired helper and both policy hashes verified unchanged before/after.

Rollback only with no operation in flight: atomically restore the exact backup
with its original owner/mode; this restores the known schema3 incompatibility.

## Original-run retry

Supported API `POST /api/runs/WGS_20260927_090701_56DC81/actions/resume` called
once after verifying failed attempt2 and existing config approval. Accepted
attempt3, DAG run `WGS_20260927_090701_56DC81-a3`; no new analysis ID or batch.
The previous approved configuration is `use_reference=all,resource_set=default`,
release `wgs-4.2.2-d38322e`. Retry is limited to preparation with these same values;
final execution approval remains with user. No direct database edits or deletion.

### Live outcome: separate WGS permission mismatch

Attempt3 reached config review, then `approve-wgs-config` with the same all/default
values resumed preparation. At17:45:58 CST `prepare_wgs_analysis` failed, native
prepare exit2. The private generation1 log reports:

`WGS CCE permissions must be bioinfo/520 with 2775/0664/0775 modes`.

Immutable WGS source `prepare/cce_pipeline_adapter.py:338-348` hardcodes these old
modes. Profile `/bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs/wgs-4.2.2-r3.yaml`
correctly contains bioinfo/520 and0755/0644/0755. Its SHA remains the registered
`5e83e5ed63300fd26de51e84dea137fdd3f3413f3bb15651862563719335aad6`.
Attempt3 frozen `release-runtime/cce-operator.yaml` exists with schema3 and no
paths; original gate error no longer occurs. Target
`/sg2/50.ctapa/Clinical/WGS_Clinical/WGS_20260919A-test_T7Hg38V4.2.2` remains absent.
Final API:failed,attempt3,execution_approved_at null. No cloud execution launched.

Required next action is a WGS source compatibility correction plus coordinated
matching release, not a production chmod or in-place immutable code edit. This
was diagnosed only and awaits scope confirmation; no further retry performed.
