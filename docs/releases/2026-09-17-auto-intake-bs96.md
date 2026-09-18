# BS96 automatic WGS intake activation

User authorized this configuration-only change on2026-09-17. No source release
promotion or Local/SGE test branch integration.

- Samplelist source: `/sg2/50.ctapa/Clinical/WGS_Clinical/HWcloud_Target_Capture`.
- Schedule:600 seconds (10 minutes); scheduled scanning and automatic dispatch true.
- Existing ready-at activation watermark:2026-09-17T09:34:19.655673Z.
- Workflow output remains `/sg2/50.ctapa/Clinical/WGS_Clinical`.
- Backend source stays qc-all-counts-4e9196d; scanner stays sampleinfo-f72a12e.
- New container IDs: backend1dc96daabc2d, scanner b4a90d98aebe.
- Ten other Airflow project service IDs, DAGs, runtime images and network unchanged.

Public configuration is `/data/airflow-WGS/auto-intake-20260917-config` (0755,
JSON0644). Private Compose, exact prior configuration and inventory are in
`/data/airflow-WGS/auto-intake-20260917-control` (0700, files0600). Only the
backend/scanner `/af05-config` mount changes; Samplelist and FASTQ remain read-only.
The saved active per-service Compose files were updated. The historical `current`
symlink is not the source of service truth and was not changed.

The deployed policy parser validated600/auto-enabled before startup; Compose
config and nginx validation succeeded. Authenticated scanner API confirms the
effective settings. First scan09:34:41Z:1 file,1 new batch,0 errors; the provided
Samplelist_20260917-145653.txt yielded20260917A. Intake32 waits for its matching
sequencing directory under `/bi/fastq/T7_Fastq`; it is not yet an AnalysisRun.
Auto dispatcher submitted0 and preserved the already linked0910A history.
Readiness checks and deduplication are unchanged. Later scans can submit once
the sequencing directory, BarcodeStat and eligible FASTQ checks succeed.

Rollback uses private rollback.json for backend and scanner only with Compose
config validation and targeted up --no-deps --pull never, then gateway nginx
reload. Preserve data and current analysis; disabling auto dispatch does not
cancel a run already submitted. No database/pending edits or deletion performed.
