# WGS obsutil Checkpoint Progress Design

## Goal

Restore `obsutil` as the Step1 upload and Step5 download engine without losing
the exact, privacy-safe file progress already exposed by the Transfers UI.
Step2, Step3, Step4, Step6 and the `cce-pipeline` package remain unchanged.

## Runtime boundary

The existing CCE 0.8.2 runtime already launches one `obsutil cp` process per
payload file with a request-scoped `-cpd` directory. Airflow continues to own
the transparent wrapper and the frozen transfer plan. The wrapper must never
write OBS URIs, credentials, absolute filesystem paths or unrestricted command
arguments to progress evidence.

`scripts/configure_node200_cce.py` selects `transfer_adapter=obsutil` and keeps
the wrapper as `obsutil_bin`. No CCE source or workflow topology change is
required.

## Progress contract

The wrapper reads checkpoint XML while the child process is running:

- upload total bytes come from `FileInfo/Size`; completed bytes are the sum of
  completed `UploadParts/UploadPart/PartSize` values;
- download total bytes come from `ObjectInfo/Size`; completed bytes are the sum
  of inclusive ranges for completed `DownloadParts/DownloadPart` values;
- malformed or partially written XML is ignored for that poll and the last
  valid monotonic value is retained;
- stdout progress remains a fallback for small transfers that never create a
  multipart checkpoint.

The wrapper may read the Airflow-owned transfer plan to match a command to one
approved relative file. It emits only the SHA-256 file key, basename and
numeric/status evidence. Auxiliary marker and manifest copies remain aggregate
v1 rows and are excluded from frozen payload totals.

The runtime gate detects file-keyed obsutil rows and projects the entire frozen
plan as `wgs-runtime.transfer-progress.v2`. Files without a child row are
`accepted`; the active file is `running`; verified terminal files are
`success`. Reused Step5 files with exact frozen sizes are also `success`.
Aggregate totals are always recomputed from the projected file rows. Older
aggregate-only wrapper output retains the existing v1 compatibility path.

## UI behavior

The existing Transfers table remains the public representation. It displays
the adapter as `obsutil`, sorts active and accepted files before successful
files through the existing API order, and renders an accepted or running file
without a checkpoint as `Waiting for checkpoint` instead of implying a sampled
zero-percent measurement. Refreshes preserve the loaded table.

## Safety and rollout

Configuration and wrapper changes are tested without credentials. Before a
production switch, a bounded multi-file upload and multi-file download canary
must demonstrate checkpoint parsing, v2 aggregation, terminal verification and
cleanup. Automatic analysis remains paused during validation. A failed canary
leaves the production adapter unchanged.

Synthetic inputs, progress snapshots and the validation summary are stored
below `/sg2/50.ctapa/project/HWcloud/WGS_test/cce-evidence/T241-obsutil-checkpoint-20260909`
under the ctapa identity.
