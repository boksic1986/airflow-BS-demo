# BS96 Clinical root release, 2026-09-17

Application source: e9a664498438d303936e39c750170dc93f65e3d4, clean server Git
archive, previously synchronized to GitHub main and jiucheng/release/production.
No Local/SGE branch promotion, native prepare change, CCE upgrade or real analysis.

## Deployment

- Source: `/data/airflow-WGS/releases/20260917-clinical-e9a6644`.
- Complete `/app` source mounts: backend, wgs-run-observer, wgs-intake-scanner,
  sample-reference-worker. No per-file backend overlays.
- Frontend image: `airflow-demo/frontend:clinical-e9a6644`,
  `sha256:4ae6428f2a32ffa031b2867790fbd5e0c47e5e003591fb91c53bc38d368ebba9`.
  Cached Node22.23.1 builder, unchanged matching package lock, no network/install.
  Served `index-BB3HH1ey.js`, `index-BFPGoplr.css`.
- Private five-service Compose and exact previous configuration:
  `/data/airflow-WGS/clinical-e9a6644-control/{compose,rollback}.json`.
  Other seven services, Airflow DAG/scheduler/worker, DB and network preserved.
  Global `current` remains a historical multi-service pointer; actual app mounts
  above are authoritative, not that symlink.
- WGS root: `/sg2/50.ctapa/Clinical/WGS_Clinical`.
- GATK result root: `/sg2/50.ctapa/Clinical/WES_Clinical`.
- Scanner samplelist root: `/sg2/50.ctapa/Clinical/WGS_Clinical/HWcloud_Target_Capture`.
  Scanner remains enabled, auto-dispatch false; existing release catalog retained.
- Node200: committed WGS gate, release selector, resume and evidence helper
  installed together. Only WGS output-root and GATK result-root env values changed;
  CCE0.8.5/private release pins untouched. Backup:
  `/home/ctapa/.config/clinical-e9a6644-rollback`.

## Data operations

Shared pending copied byte-identically from old WGS root into new
`prepare/pending_samples.tsv`. No pending business decision or source edit.
Copy only `WES_20260914A_T7_V7.7.0_hg38_GATK` and matching0914B from old WES root
into new WES root. Existing NON-_GATK clinical projects and all old sources remain.
Both copy commands exited0 (14G and51G respectively); no history/DB rewrite.

SFS read-only inventory Job `clinical-sfs-inventory-e9a6644` used only
`biosan-clinical` PVC. Frozen run/linkage paths for WGS0910A,0912D and
GATK0823A,0907A,0914A,0914B were already absent. Only the following inactive
WGS0911A paths were deleted by `clinical-sfs-cleanup-e9a6644` (Job succeeded1):

- `/workspace/wgs/runs/WGS_Clinical/WGS_20260911A_T7Hg38V4.2.1`
- `/workspace/wgs-obs-sync/Project_result/WGS_Clinical/WGS_20260911A_T7Hg38V4.2.1`

Exact task label `cce.biosan.cn/run-id=cce-run-d22d2a1f340ab180` checked before
deletion. Cleanup verifies resolved paths and asserts both absent before success.
No OBS/FASTQ/offline deletion, no DB mutation, no historical Job cleanup.
Two unrelated Pending inspection pods preserved. Operational inventory/cleanup
Jobs use one-hour TTL; their manifests are under
`/sg2/50.ctapa/project/HWcloud/WGS_test/cce-evidence/clinical-e9a6644`.
SFS intermediates are not recoverable via application rollback.

## Minimal acceptance and operational exceptions

No repeated test suite. Necessary production artifact build succeeded; Compose
config check succeeded. Runtime UID6801 write/read/unlink marker verified only
the two new output roots. API still lists seven historical runs. GATK0914A/B
list lifecycle now reports cloud_release success from existing Step7 actions,
matching the previously correct detail endpoint. Downstream remains not_started,
not fabricated completed. Served frontend index matches the built asset names.

First startup found copied public configuration directories masked0700 by private
umask; explicitly corrected ONLY scan-config/ledger-config directory modes0755
(JSON0644; secret Compose/inspection files0600), restarted four affected services.
Then API/roots check passed. Loopback gateway curl403 is the preserved nginx
allowlist; request from172.17.61.96 returned the correct new index.
Transient SSH18 resets were reconnected. Node200 system Python3.6 rejected the
packaging script before mutation; re-executed with existing WGS Python3.11.
Unfiltered historical Job inventory timed out before any cleanup; replaced by
exact-run-label read. Cleanup Job succeeded; subsequent log read returned Pod
NotFound, so no log-completeness claim or destructive retry.

## Rollback

Use private rollback Compose with `config --quiet`, then targeted `up -d
--no-deps --pull never` for the same five services. Restore node private runner
files/env from the recorded backup together. No DB rollback or data deletion.
New copied files may remain; source projects were not modified. Restoring code
does not restore deleted SFS data. Do not re-run0911A as part of rollback.
