# cce-pipeline 0.8.6 / WGS Master / inactive profile

Scope: user-approved runtime-first slice. WGS/SFS publication remains paused.
No Airflow/BS96 deployment, clinical submission, automatic enablement or main
merge is included. Original native/Infra owner executes, platform records evidence.

## Runtime

- Source: `dcc1698fb5da955d2c481a735021f0cfac2b8119`, branch
  `jiucheng/release/p0-validation-20260925`.
- Version: `0.8.6`; wheel SHA256
  `3e77f7b4892a086b977e7ff072860f70a9344160be1949b413a12f6228b843da`.
- Install target: `/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest`.
- Only fixed `0.8.5` release restriction removed; catalog/actual version equality,
  source/profile/resource hashes, asset PASS and authentication retained.
- Receipt records RED reproduced the fixed-version refusal, then GREEN3/3 for
  matching version, mismatched version refusal and canonical receipt digest.
- Receipt records pip exit0 and CLI0.8.6; installed release.py SHA256
  `a403d72a67690b51bb4e70b24b72bd7783eb0536f178c4cf32ecd57319fa4212`.
- No separate installed-package backup: owner records the user's direct-install
  instruction. Old dev3 wheel remains available, not an exact old-environment backup.

## WGS Master and profile

- Reused accepted image config ID
  `sha256:05888c3ac82e1a9b149c2bbd42788d227269787d5042c1af3287daa6d16be367`.
  Source comparison confirms no embedded runtime asset change versus45323e4;
  no unnecessary Master rebuild for the client-only release validation fix.
- SWR tag: `swr.cn-east-3.myhuaweicloud.com/biosanwgs/wgs-cce-master:wgs422-p02-20260926-45323e4-5ffcb07`.
- RepoDigest: `sha256:dc22c919d83ee5354b51b650666c9609ce05dc3ebcfb283acac16a3b3fa62597`.
- Profile: `wgs-4.2.2/r2`; remote path
  `/mnt/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs/wgs-4.2.2-r2.yaml`.
- Profile SHA256: `4a016a2d0c1006b013a1e66efc147e29275e0ce8dcd2b086f1488bed8c44d6ed`.
  Local copy read/hash verified by coordinator; owner reports profile validate exit0.
- Pipeline payload SHA `09da0287ba0f9dc600b6c8350a78b2bb65ac410daa2f8aa5246b6d0ebcf76a88`,
  resource manifest SHA `67713468626acbcaecf62a1ac23181b487c1074cffc833a10a6889ac8db122e7`.
  Targets remain `/workspace/wgs/pipelines/4.2.2` and resource set `wgs-4.2.2-r1`.
- r2 differs from staged r1 only by revision and Master digest. Existing Workers,
  namespace/service accounts/PVC, resource limits and bioinfo permissions remain.

## Not activated / next boundary

The previous R1 asset manifest binds the old profile bytes. A future authorized
WGS/SFS publication must generate corresponding manifest/SOURCE_READY metadata;
old readiness is not proof that r2 is ready. No OBS candidate is overwritten in
this slice. SFS paths, production selection and frozen attempts are unchanged.

Profile schema has no client-version field; this companion record binds the
installed client0.8.6 without adding an unsupported YAML key.

## Evidence review completed

Unified owner receipt (including RED/GREEN, build/install and push/validate
transcript results) read and hashed:
`D:/pipeline/task-artifacts/p0-final-native-ops-20260925/R2_R3_086_EXECUTION_RECEIPT.md`,
SHA256 `a9e378835d1cb5c5d792e4f361b16a1f52801633b687f89130aa2bd332dd6d8e`.
Coordinator independently checked commit diff/clean status, downloaded only the
119603-byte wheel from the exact task evidence path, and inspected ZIP metadata,
wheel/release.py/runtime/guard SHA256 values; all match the receipt. This was
static artifact inspection, not local runtime testing. Profile bytes/hash and
all binding fields also checked. No duplicate tests/builds/live cloud canaries.

R2 client install/image publication and R3 inactive profile binding are complete.
SFS publication, Airflow API/dashboard integration and main/production-branch
synchronization are not complete and are not inferred from these receipts.
