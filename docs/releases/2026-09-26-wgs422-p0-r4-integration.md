# WGS 4.2.2 + P0 R4 test-branch integration

Scope: source integration and candidate version binding for BS10610 only. This
record does not authorize or claim a production merge, BS96 deployment, real
batch submission, or a new WGS/native artifact build.

## Source integration

- Test branch: `jiucheng/test/wgs422-p0-integration-20260926`; base
  `781877e8a862bbe7a4bf2924e817d3657d81468f`.
- `origin/main` and `origin/jiucheng/release/production` were both frozen at
  `43cd0c51a0ff44cc368579a397ba5ddb5ebc611a`, already an ancestor of the
  test base. The Step7 production-equivalent source was already present; it was
  not cherry-picked again.
- Merged the P0 source/documentation tip
  `fd9a008d687dafd56649d1f43a0992019042176e` with two parents into local
  commit `0af836706d77617131f9c5222ddf50fab886ae2d`. No push performed.
- Resolved the two executable conflicts block by block. WGS runtime gate keeps
  Step7 exact-request and stopped-predecessor fences alongside the P0 Step4
  publish guard and restricted recovery/publish commands. WGS runtime receipt
  ingestion keeps a row lock and refresh of the current AnalysisRun for both
  Step7 and P0 projection. Documentation conflicts retain both historical
  Step7 and P0 sections; the coordinator will refresh state/task/handoff tops.
- `git diff --check` passed on the merged range. No local runtime tests were
  run, per this R4 instruction. Original Infra owner reports the agreed
  BS10610 focused set **11/11 PASS** (backend 10, DAG 1; DAG node 2.97 s).
  The exact source archives, container images and command results are in
  `D:/pipeline/task-artifacts/wgs422-p0-integration-20260926/R4_SYNTHETIC_TEST_RECEIPT.md`.
  This is not a local rerun or full P0 suite claim. The first 10-backend run
  omitted `/config` and had 6 pass/2 fail/2 error; the four affected nodes
  passed after the existing config was mounted. The Airflow test container
  received task-local pytest dependency files, not a service/image change.

## Version binding boundary

R1 published asset release `20260926.1-wgs422` PASS/state_verified; R2/R3
delivered cce-pipeline `0.8.6`, WGS Master RepoDigest
`sha256:dc22c919d83ee5354b51b650666c9609ce05dc3ebcfb283acac16a3b3fa62597`,
and inactive external profile `wgs-4.2.2/r2` with SHA256
`4a016a2d0c1006b013a1e66efc147e29275e0ce8dcd2b086f1488bed8c44d6ed`.
The published pipeline and resource digests are recorded in the R1/R2/R3
release documents; no new artifact was built here.

The existing release catalog, singular/list/version-management APIs, and
submission/run-detail panels already expose a selected catalog release and
profile; a new UI or API is unnecessary. The external `wgs-4.2.2/r2` profile
is **not** the platform's generic `wgs-cce-v1` execution-mode selector. The
4.2.2 candidate must be entered in the catalog with verified BS10610 and
node200 WGS repository paths; those paths are not established by the SFS
publication receipt. Do not substitute the old 4.2.1 checkout or the SFS
`/workspace/wgs/pipelines/4.2.2` path for those gateway repositories.

Candidate registration fields known from accepted receipts:

| Field | Value / gate |
| --- | --- |
| WGS platform `release_id`, `version`, `source_commit` | `wgs-4.2.2-3b1dae5`, `V4.2.2`, `3b1dae513dbca1938ed89d982e2c3553856862b3` |
| `rule_event_schema_version` | `1` (existing schema; confirm final immutable source) |
| `profile_id`, `profile_revision`, `profile_sha256` | `wgs-4.2.2`, `r2`, `4a016a2d0c1006b013a1e66efc147e29275e0ce8dcd2b086f1488bed8c44d6ed` |
| `cce_pipeline_version` | `0.8.6` |
| `pipeline_build_sha256`, `resource_manifest_sha256` | `09da0287ba0f9dc600b6c8350a78b2bb65ac410daa2f8aa5246b6d0ebcf76a88`, `67713468626acbcaecf62a1ac23181b487c1074cffc833a10a6889ac8db122e7` |
| `node200_profile_path` | `/bi/biodevrwbi/33.chenjiucheng/project/cce-pipeline-profiles/wgs/wgs-4.2.2-r2.yaml`; node200 direct readability remains an activation gate. |
| `bs10610_repo_path` | `/mnt/biodevrwbi/33.chenjiucheng/project/wgs-releases/20260926.1-wgs422/wgs-4.2.2-3b1dae5` |
| `node200_repo_path` | `/bi/biodevrwbi/33.chenjiucheng/project/wgs-releases/20260926.1-wgs422/wgs-4.2.2-3b1dae5`; node200 direct readability remains an activation gate. |
| CCE asset `release_id`, `asset_manifest_sha256`, status | `20260926.1-wgs422`, `73bca89d28619fb6194233f0bea40ae5f5d8423bd6fab4fdf511a52493eaacd7`, `PASS`, `state_verified=true` |

The versioned non-secret registration body is
[`wgs-4.2.2-3b1dae5-registration.json`](wgs-4.2.2-3b1dae5-registration.json),
using the existing authenticated `POST /api/wgs/releases` contract. Its
canonical `receipt_sha256` is
`fd392fe078d86f3599fe1456693ba46d5276c41ef0f72dbdf85a434c3b288b76`.
Registration itself does not select the candidate.

WGS owner's R4 source receipt at
`D:/pipeline/task-artifacts/wgs-422-update-20260925/R4_WGS_SOURCE_RECEIPT.md`
records an immutable package from the already published SFS payload, all 130
files checked against the frozen manifest, `PIPELINE_READY` source commit
3b1dae5, and `SOURCE_MANIFEST.json` SHA256
`c34dec287983761133d48c1b378420d00e5dee512d36a67db1910447e7c3ff84`.
On BS10610, `/mnt` and `/bi` map to the same inode; release-source directories
have mode 755 and files 644/755. This is publicly readable pipeline source,
not shared run output or a private credential spool. The excluded private
WGS config/mail files are absent. The WGS development worktree is not used.
Node200 has **not** read the path directly: the original Infra owner's route
timed out. Do not convert BS10610 mount equivalence into node200 acceptance.

The actual BS10610 private catalog (backend `/config` mount from
`releases/20260912-opt-4d3d24e6/config`) currently selects
`wgs-4.2.1-34bfcbf` / cce-pipeline `0.8.4`; the repository's example YAML
instead selects `wgs-4.2.1-cc9bde3`. Do **not** replace the private catalog
with the example file, or use the example current value as the activation CAS.
The Airflow `pipeline_profiles.wgs.yaml` is separately file-mounted from
`releases/20260912-gatk-81587fcb/config` and is not the r2 profile selector.
The test current release remains 4.2.1 until the original Infra owner verifies
test mounts and deliberately selects 4.2.2 for **new** test batches. Existing
attempts retain their frozen release/profile. The catalog's authenticated
registration receipt and compare-and-swap activation must not be inferred
from a candidate entry alone. Global automatic recovery/scan/dispatch remain
off unless separately authorized.

The packaged QC policy is audited at 4.2.1 cc9bde3, with only named 4.2.1
equivalent/variant releases. No four-source-blob equivalence or independent
4.2.2 QC policy audit is recorded. Thus 4.2.2 numeric QC judgments remain
unavailable/unknown by design; this integration does not invent a PASS policy.
The submission-options audit is likewise pinned to cc9bde3, so the existing
panel will show 4.2.2's release/profile identity but not claim audited caller
overrides until a separate WGS owner contract is accepted. This does not block
the legacy release-default submission path when its existing gates allow it.

## Pending acceptance

- WGS owner: publish an immutable 3b1dae5 source package and exact BS10610/
  node200 gateway repository paths (delivered). Original Infra owner: obtain
  authorized node200 direct path traversal/read/owner check, including profile
  r2, then verify actual private catalog/mount and receipt before activation.
- The frozen WGS prepare script must retain the existing `--handoff-request`
  and receipt interface. The 4.2.2 platform version gates are being extended
  only after this static contract check and two-node RED→GREEN, so missing
  pending/selected handoff proof cannot be bypassed.

WGS owner subsequently checked the exact frozen 3b1dae5 source: its
`prepare/prepare_wgs_batch.py` exposes `--handoff-request` at line 646,
loads it for sampleinfo/analysis at lines 716–728 (rejecting `all`), emits
sampleinfo receipt v1 at 211–237 and analysis receipt v1 at 306–354 with
final sampleinfo, pending revision/SHA, selected/pending decisions. Both
all-pending and successful branches write that receipt (468, 613).
`prepare/handoff_contract.py` names `stage.receipt.json` (95–96) and writes
atomically with fsync/hardlink/no-overwrite (287–305). This is source-interface
evidence, not a node200 execution or end-to-end test.

The 4.2.2 prepare gate needed a narrow source-binding correction. Test-only
commit `beba26aa171555f0cdcf4bf5553f2fd312717e34` produced the expected
two BS10610 RED results: restricted gate `KeyError` for missing exact
`wgs-4.2.2-3b1dae5` allowlist entry, and backend `artifact_pending=false`
for a successful prepare marker without a handoff receipt. The correction adds
that exact immutable source path and `V4.2.2` to the gate's repository and
handoff version sets, plus the backend's required-receipt version set. Unknown
versions remain rejected. The same two GREEN results are pending; the 11
baseline cases are not rerun.
- Original Infra owner reported 11/11 PASS for the agreed WGS P0/Step7
  backend+DAG nodes with the receipt path above. A separate two-node 4.2.2
  binding GREEN remains pending; it is not part of 11/11.
- No local tests, test-service deployment, profile activation, production
  deployment, real samples, or main/production branch merge is claimed here.
