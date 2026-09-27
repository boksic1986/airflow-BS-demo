# WES cloud cleanup — 2026-09-27

User explicitly authorized clearing WES cloud batch data including 20260921B.
No database deletions, offline deletions or multipart-upload retries authorized
by this operation. No backups created; recovery is not guaranteed.

Preflight: BS96/server96 active backend source remains
`/data/airflow-WGS/releases/20260927-p0-local-84510df/backend`; all five GATK
analysis records are success; no queued/running Airflow DAGs. CCE has no running
analysis Pods. Two old pending GATK helpers do not target these directories and
are left untouched. SFS maintenance runs as 10001:10001, not root, without chmod.

## Exact authorized SFS targets (pre-action inventory)

- /workspace/gatk-cloud/runs/WES_Clinical/20260816A
- /workspace/gatk-cloud/runs/WES_Clinical/20260907B
- /workspace/gatk-cloud/runs/WES_Clinical/20260917S
- /workspace/gatk-cloud/runs/WES_Clinical/20260921B
- /workspace/wgs-obs-sync/Project_result/WES_Clinical/20260816A
- /workspace/wgs-obs-sync/Project_result/WES_Clinical/20260907B
- /workspace/wgs-obs-sync/Project_result/WES_Clinical/20260917S
- /workspace/wgs-obs-sync/Project_result/WES_Clinical/20260921B

## Exact authorized OBS prefixes (pre-action inventory)

- obs://obs-biosan-bioinfo/Project_fastq/WES_Clinical/20260917S/
- obs://obs-biosan-bioinfo/Project_fastq/WES_Clinical/20260921B/
- obs://obs-biosan-bioinfo/Project_result/WES_Clinical/20260823A/
- obs://obs-biosan-bioinfo/Project_result/WES_Clinical/20260907A/
- obs://obs-biosan-bioinfo/Project_result/WES_Clinical/20260914A/
- obs://obs-biosan-bioinfo/Project_result/WES_Clinical/20260914B/
- obs://obs-biosan-bioinfo/Project_result/WES_Clinical/20260917S/
- obs://obs-biosan-bioinfo/Project_result/WES_Clinical/20260921B/

Protect all offline data, pending, WES database records, cloud parent directories,
shared resources/pipelines/evidence, personal/test trees and P0SMOKE20260927.
No business tests or deployment changes.

## Results

All eight exact SFS paths above individually returned removed=true; both parent
inventories are empty. OBS results below each returned failed count0:

| Prefix relative to bucket | Removed objects | Receipt task ID |
| --- | ---: | --- |
| Project_fastq/WES_Clinical/20260917S/ | 6 | 6afc8671-30c7-4cf8-87c0-5e442db20289 |
| Project_fastq/WES_Clinical/20260921B/ | 88 | e4996909-6631-4e88-8182-79631b593994 |
| Project_result/WES_Clinical/20260823A/ | 6 | abf808c5-65be-4271-8c48-43ddb3c7197c |
| Project_result/WES_Clinical/20260907A/ | 7 | 9dbb7e01-57cd-4bcc-b788-db946cb82d77 |
| Project_result/WES_Clinical/20260914A/ | 7 | 0225750b-5da8-4c39-8b83-36103ca3a5c9 |
| Project_result/WES_Clinical/20260914B/ | 7 | e8aee387-fd10-44ee-9d7a-28948743d2ea |
| Project_result/WES_Clinical/20260917S/ | 6 | 2f1e22a0-dbd6-48da-9a33-8fe54e937a88 |
| Project_result/WES_Clinical/20260921B/ | 7 | efcfc4e7-536d-486a-b6de-24940fae113d |

Total134 OBS objects removed; each WES parent now reports0 files/0B, with only
its empty parent marker retained. No version purge or multipart actions.
OBS receipts remain privately on node005 at
`/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/cleanup-wes-bs96-20260927/obs-records`.
Dedicated maintenance Job deleted after completion. No local/offline or DB writes.
