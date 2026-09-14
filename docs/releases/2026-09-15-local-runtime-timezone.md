# REL-02 local runtime timezone — implemented, not published

User explicitly requested second fix without publishing to96. Scope: local gate
process timezone, not system timezone, original WGS scripts or node selection.
The entry initializes TZ=Asia/Shanghai/time.tzset before preparation/worker work;
its detached worker inherits TZ, and analysis/smoke child env explicitly fixes TZ.
Existing datetime.now(timezone.utc) status publication stays UTC. No cloud gate,
DAG, prepare_wgs_batch.py interface, pending or scientific configuration changes.

## Verification

BS10610/server10610, chenjc, test only. Verified historical current and actual
backend source mounts before creating isolated candidate:
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/rel02-20260915.
Cached airflow-demo/backend:t235-232154f, --network none --pull never,
read-only candidate, PYTHONDONTWRITEBYTECODE=1. Command:
`python -m pytest -q -p no:cacheprovider /work/scripts/tests/test_wgs_local_runtime_gate.py`.
RED2 failed/10 passed: inherited UTC and direct worker UTC reproduced.
GREEN12 passed in0.18s. Real nested Python processes verified Shanghai local
clock from UTC parent; direct worker entry verified initialization before work;
existing terminal identity test also verifies UTC updated_at. No real workflow.
Uploaded and local gate SHA256 match:
7be889d217ac775a041c2955a7f7525900e4e9eaba4a94b39e3e07fb8a1d5146.

## Boundaries / next step

No production read/write/restart, no analysis submission or queued-task changes.
No on-host96/97 acceptance claimed: gate installation and a small child clock
probe await separate publication approval. The script retains existing local97
capability validation; no new96 capability is enabled by a timezone fix.
Direct original prepare invocations outside this gate must use the runbook's
process TZ prefix. No new launcher/service/configuration framework is introduced.
Rollback the gate code for future launches; preserve running workers, DB,
original script, pending and outputs. First fix REL-01 also remains unpublished.
