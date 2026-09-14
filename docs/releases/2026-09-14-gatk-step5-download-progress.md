# GATK Step5 download progress

## Scope and cause

The restricted GATK gate supplied the obsutil progress environment to Step5 but
only Step1 built a manifest-backed plan and published `progress.json`. The
observer reads stage-level aggregate snapshots, not hashed single-copy files.
Consequently a real download could have no `result_download` API projection.

## Runtime change

- Step5 raw records and transfer plans are isolated by attempt and generation.
- READY must match the frozen project/batch/run identity and manifest MD5.
  Only then are safe, unique manifest payload paths and sizes used for totals.
  Missing/unverified metadata produces no invented denominator.
- Step5 runs its existing frozen script once while publishing aggregate v2
  progress. The existing observer/API/frontend remain unchanged.
- A completed file copy is not whole-stage success. Final progress requires the
  matching successful stage receipt, DOWNLOAD_VERIFIED markers, matching manifest
  identity, and unchanged size/device/inode/mtime from the verified file ledger.
- Final completion uses the receipt's original timestamp; `recorded_at`,
  `receipt_hash`, and `source=verified-download-receipt` identify supplemental
  telemetry. Old flat raw files are never adopted into a new generation.
- Temporary telemetry failures do not stop or restart the real download.

No changes to WGS, pending, Step7, forced-command/environment/credentials, or
BS96 service definitions. No analysis submission or transfer rerun is required.

## Verification

RED on BS96's isolated cache-only test container: 3 expected failures (missing
download plan/aggregator, missing generation directory). Initial GREEN: 23 passed.
Final suite: **24 passed**; additionally checks the metadata-arrival loop launches
one copy and waits for freshly published READY before freezing live totals.
Use image sha256:0e2d6f0cdf4b89b5ade30b3855cdb8593f33e4c23085a0f5adcd644095cf6912,
`--pull=never --network none`; test root:
`/sg2/33.chenjiucheng/WGS_test/cce-evidence/gatk-download-20260914`.

For 20260907A attempt 1 generation 1, read-only verification on node200 passed:
2 files, 11106608093 bytes; original stage completion
2026-09-14T15:00:16.226174+00:00. Existing flat raw progress was not used.

SSH gateway intermittently aborted connection setup before command execution.
Only failed file transfers and isolated checks were retried; no workflow rerun.

## Deployment / rollback

Coordinate with the recovery task before installation. Expected previous gate
SHA256: 759902ff0ed933a9a9d9719d8c5f42b14fdaa17159e914553c536753d8c34f4c.
Install only `/home/ctapa/.config/airflow-gatk/gatk_runtime_gate.py` on node200
after a fresh hash fence, retaining the previous gate and pre-0436dce backup.
Preserve adjacent maintenance/resume gates. No service restart.

After installation, supplement only the already verified 20260907A snapshot and
confirm observer/API `result_download` is success at 100%. No direct SQL update.
Rollback restores the previous gate for subsequent stages; preserve all existing
analysis, receipts, download files and telemetry. Do not rerun successful downloads.

Shared CURRENT_STATE/TASKS/HANDOFF are maintained by the coordinating recovery
task and intentionally excluded from this narrowly staged change.

## Deployment receipt

- Code commit: `b841d2a`; node200 gate SHA256:
  `d82bf7722b80758667a5561f981b01802ad097c4fbfedf5025da6c0b4fb229e2`.
- Fresh previous-hash fence passed; installed atomically with
  `gatk_runtime_gate.py.pre-b841d2a` backup. Existing pre-0436dce retained.
- Adjacent maintenance gate remains
  `15e7e9e8032340670c7c5370a53ae026524a53e25b88902c52dd2affa82d041d`;
  resume helper remains
  `bf6b82a76371415bfd3b1d7045fc4a10e1f3d825dff6806988e6a145d945dd41`.
- Supplemental progress published at 2026-09-14T15:10:53.147354+00:00, preserving
  original verified completion 2026-09-14T15:00:16.226174+00:00.
- The existing adapter `_ingest_gatk_evidence` was invoked for this analysis and
  attempt only, using normal request/generation validation, not SQL corrections.
  API `result_download` now reports success, 100%, 11106608093/11106608093 bytes,
  2/2 files, detailed progress, verification=verified, and the original completion.
  Repeating ingestion kept the same transfer ID/row, totals, and timestamps.
- No BS96 service restart, downloads rerun, Step7 action, or WGS mutation.

Known boundary: this existing download completed before the fix, so its Step5
polling had already ended. The persistent WGS observer does not automatically
ingest new GATK post-terminal transfer evidence; a bounded normal adapter ingest
was necessary. This change fixes future Step5 runtime publication during normal
Airflow polling, not general post-terminal automatic backfill. Future live
incremental-progress validation awaits the next independently authorized GATK run.
The API's legacy `progress_basis` enum remains unchanged; completion evidence is
explicitly identified by the verified source and receipt in the spool.
