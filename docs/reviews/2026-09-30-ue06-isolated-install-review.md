# UE-06 isolated installation and pairing review

## Scope and current verdict

User authorized checking the accepted UE05 handoff and proceeding. Original
owners carry out BS10610 isolated installation/loading only. Coordinator reviews
their raw evidence locally; no coordinator SSH, runtime tests or product edits.
UE01-05 behavior acceptance is reused, not rerun. See the
[plan](../superpowers/plans/2026-09-28-unified-stage-execution.md) and
[UE05 source closeout](2026-09-30-ue05-source-handoff-review.md).

Native packaging/install and real trust/policy/module loading are accepted.
AF real ordinary/P0/SSH entry checks are also accepted from original exit0 logs.
Final platform state-only3c094fc and28-file evidence manifest are verified;
UE06 isolated-install acceptance and paired handoff are closed. No production,
activation, cloud workflow or
operational old-policy rollback claim is made by these checks.

## Fixed combination

| Item | Evidence |
| --- | --- |
| Native source | `7172573223308f1ca89616a5f81d14fec995a659` |
| AF product source | `03bab6c768a2c84537ee4e4a6189072256841b63`; state-only `a0666e58d342f914bc9db54cae5fab4444132462` |
| Native wheel | `cce_pipeline-0.8.9-py3-none-any.whl`, 153323 bytes; SHA256 `bda21dd22fd5fbcea23c40ae5ed9e3fc324b41ff2f56bf31c59022acacd8f6d4` |
| Native runtime asset | SHA256 `c2988621e4552f4240f3f8c2254d99be315ad1633ed51b8f712bf310acced7c7` |
| Native guard | SHA256 `e99378dcb1a0f71d3561c6705f4b5fe2f9886bc9e0307b5dc7c1b822de6e6d0f` |
| AF paired loader | SHA256 `fdc23a33f0d805bd923b6a31d5f70a381164f5b2a523160c621167aaf3d285ab` |
| Shared candidate policy | SHA256 `458472513c5ee071b6f7fa755911df3229c84504581149beb872bb4c3eee674e` |
| Both code-adjacent trust documents | Identical bytes; SHA256 `8e47ad3f5d456a31b617d183f0b5421525e0169f835c145c9f25d30b6d495706` |

Native root (`N`):
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue06-native-089-20260930`.
Wheel is `N/wheel`; installed package is `N/install/site/cce_pipeline`.
AF candidate (`P`):
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ue06-platform-03bab6c-20260930`.
Platform writer is `P/source/scripts/cce_paired_runtime.py`; policy is
`P/policy/cce-paired-writers-v2.json`. AF evidence root (`A`):
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/ue06-platform-03bab6c-20260930`.

Approved Python is `/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/bin/python`
(canonical `python3.9`). Only explicit isolated module paths select0.8.9.
Shared site-packages remain0.8.8. Policy namespace `ue06-install-only` with
`bindings: []` is for loader inspection, not a clinical/storage binding.

## Original evidence reviewed

- `A/preflight.log`, SHA256 `cf964f280478081c3f600143d53edfa7de28e5db2c19797b113166b907991d69`:
  server10610/chenjc6708:520, actual mounted service sources independently read,
  scan/auto-dispatch off, nonterminal analysis/transfer/DagRun/TI counts all0.
  Worker image `58195672af68...`, UID50000:GID0; no active service replacement.
- Native `build-install.log`, SHA256 `a3f96dea102be5513ff429f781527b8f0bca2cc29f02ffca76098a457a2ce789`;
  `candidate-install.json`, SHA256 `23ca20847028ee20f18e6f6945a3ff23c28c5679ece69b5d4b48d95d9e603129`.
  Read their full producer scripts: fixed commit archive plus build-commit
  injection, no-index/no-deps build/install, all30 package files compared against
  wheel, fixed source and installation. Runtime-info identifies the real isolated
  package/version/commit, not just an expected constant.
- Native shared package/dependency inventories before/after are identical SHA256
  `0d3541a45b15764e55693c946293214d0b37c029664a6db3143bbe9bc7cc1aab`;
  shared runtime-info before/after identical SHA256
  `78059919fedec016265909e2cb380138752808a9940884418aaf647c3652f791`.
- `A/pair-policy.log` and original policy/bootstrap inspected; native bootstrap
  and AF bootstrap match bytes, owner6708:520, files644/roots755 and no extra
  writable ACL. The schema remains strict five bootstrap keys; no trust bypass.
- Native `provenance/native-loader-pass.json`, SHA256
  `ffa9626e72166e3ece2ecce5add09c760502e7b85012dc72b9a96f5f2b293b3f`, stderr0B:
  actual installed trust/policy loaders and Step3/runtime/guard/public executor
  sources checked, stage_calls0/cloud_calls0. Original inspection script reviewed.
- AF combined `run-loaders-v2-output.log`, SHA256
  `657ac6e86c51544d70e216bdac2aef92c444f09f4c3946a9b8151e09163b3579`:
  PLATFORM_LOADER_EXIT0 and AIRFLOW_LOADER_EXIT0. Both real ordinary command
  builders select the same pinned interpreter/asset; commands are not executed.
  The real P0 entry loads that asset and refuses absent task-owned registration
  before a stage/writer call. Selected Step4/5 business and guard sources match.
  Airflow image58195672af68/UID50000:0/network-none imports candidate WGS/GATK,
  Worker-wait and publish-dispatch callers; each shares the identical candidate
  `common.ssh_transport.run_ssh` object. No SSH connection, dispatch or DagBag run.
  Full loader and command scripts read; no validator or loader monkeypatch.
  Component log hashes reported in that original output: platform-loader-v2.log
  `fc2663557ace419167304ddec1427cf5e5003177598450a661ae3cf8f1e4ce49`,
  airflow-loader.log `d4f0aa94ce3ecd2d154ac1ee9fc5744fd1f584d5ac9f2f4f0a38d246eb5fd7d2`.
  Their subsequently exported original files were independently hash-checked and
  match, including first-failure log `c0384f8433d842e0da72d58877c965f5fcbd7df0969fab501b9c022c05681db6`.
- `retained-state-comparison.log`, SHA256
  `9e2a190d3fe2671b7fa91a93454fbbd4ee02107e9553a4abfc042523493c8c9b`:
  compares original AF preflight with native post-install evidence, without new
  remote runtime checks. All10 service identities, backend/DAG/common source
  mounts, current link and disabled scan/dispatch gates match; shared package and
  runtime inventories match. Native final inventory also matches the initial one.

Raw local exports are under native owner's
`D:/pipeline/WGS-noncoding-model/.codex-artifacts/ue06-native-089-20260930`
and AF owner's
`C:/Users/11217/.codex/worktrees/gatk-prod-compat/airflow-demo/.codex-artifacts/ue06-platform`.
They are evidence artifacts, not files to commit or public release content.

Final AF commit `3c094fc4c8789444abbbd3aa939955d73c98fbe3` changes only
CURRENT_STATE/TASKS/HANDOFF/SERVER_INFO versus accepted03bab6c; tracked tree
clean and diff-check passes. Complete final HANDOFF read, SHA256
`4624a5556760025ae6a184becf2252cd0526a2d87d7d72a681e71faab5f25c57`.
`final-evidence.sha256` SHA256
`65079407accc11536b6f50d7c6794172561fd74ada059bc56adf3beeffc79b74`;
all28 indexed original files locally hash-verified. This final review adds no
remote check, test replay or operational activation.

## Inspection failures retained, not product changes

Native's first inspection used a nonexistent runtime `step3_status` attribute
instead of real `step3`; its original AttributeError is retained. Only that
inspection lookup changed; no wheel rebuild or behavior suite was required.
AF's first inspection assumed wrapped Step4/5 source must be the runtime file.
Original wrapper inspection instead shows the selected `cce_writer_guard.py`,
with unwrapped business source in selected `cce_batch_runtime.py`. Corrected v2
inspection verifies both identities without calling unwrapped business functions
or changing product code. Original failure and subsequent exit0 are both retained.

## Rollback and release boundary

Exact readable shared0.8.8 rollback wheel:
`/mnt/biodevrwbi/33.chenjiucheng/wgs_test/cce-runtime-info-088-20260927/wheel-417de59/cce_pipeline-0.8.8-py3-none-any.whl`,
SHA256 `45c99c0c8fb2d39442088d5c5ee7ad6c7be004d2c30495d80d96a4e8a20672c8`.
Every package file matches the actual shared installation; source is
`417de597fe3e83cc42160cf14102ad78db789bf8`.

The old shared bootstrap is preserved/readable, but its old policy and platform
writer under `/home/ctapa/.config/airflow-wgs-test` are absent on this host
(ENOENT2; owner namei shows `/home/ctapa` absent). Original
`existing-configs-readability.json` records `all_readable: false`; not a permission
failure. No directory recreation, access change or old-policy repair is approved.

For this isolated install, rollback is leaving the candidate unselected and
preserving existing services, package and pins. This does not prove a working
old paired-policy switch. Actual activation must first resolve the correct
environment-owned rollback configuration and obtain separate authorization.
Production0.8.8, existing batches, WGS/Master/plugin assets and W423 implementation
remain untouched. No stage/cloud/clinical tests, deletion or database mutation.
