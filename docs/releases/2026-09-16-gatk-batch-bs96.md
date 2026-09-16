# GATK batch fallback selective production release

User authorized96 publication on2026-09-16, including retention of the just-published
workload/Step7 update. This is not a full main/production branch rollout.

Source e583833 adds only `or params.get("batch")` to run_service._public_batch.
Existing WGS field precedence remains unchanged. Prior isolated BS10610 red/green
test accepted (1passed0.36s); no repeated suite or frontend build this release.

Preflight: BS96/server96, chenjc6708:bioinfo520, control/data/airflow-WGS;
current symlink20260912-panel-opt-4d3d24e6, actual backend/app93069eb with three
089dc93 file overlays. Root owner/group/ACL unchanged. Airflow REST reported0
running/queued runs for bio_wgs,bio_gatk,bio_gatk_maintenance; active business0.

Copied deployed run_service.py to
`/data/airflow-WGS/releases/20260916-gatk-batch-e583833/backend/app/run_service.py`;
applied only the committed one-line diff. git apply --check and Compose config
--quiet passed. Reused inspected image/env/network/mounts/health/restart settings;
retained all three089dc93 overlays and added this fourth read-only file overlay.
Private inventory/before/compose/rollback files are under
`/data/airflow-WGS/gatk-batch-e583833-control` with restricted permissions.

At07:55Z ran docker compose up -d --no-deps --pull never backend with that private
compose.json. Orphan warning names intentionally excluded services; none removed.
Backend changed from d4f942288f8f to
b702a4dc47fb41be245231597f4458bb622c0601ee01e881a004357942d8d165.
Other11 container IDs unchanged. Node200 scripts unchanged; no Airflow/Master restart.

One post-release list serializer check returned:

| Run | batch_no |
| --- | --- |
| GATK_20260915_114302_B2BA53 | 20260914A |
| GATK_20260915_102309_7D0AC0 | 20260914B |
| GATK_20260914_045846_789C29 | 20260907A |
| GATK_20260913_155423_30EFFE | 20260823A |

Internal backend /api/health200. No patient/sample details printed, database
mutation, cleanup request or analysis submission. No unrelated UI/DAG changes.

Rollback only backend:
`docker compose -p airflow-wgs -f /data/airflow-WGS/gatk-batch-e583833-control/rollback.json up -d --no-deps --pull never backend`.
This removes only the batch overlay and retains089dc93. No data rollback needed.
