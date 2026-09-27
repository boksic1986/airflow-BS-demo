# WGS SSH banner retry correction — BS96, 2026-09-27

User authorized continuing the diagnosed narrow correction and recovering the
original run. Functional source commit `e307328`; only `dags/bio_wgs.py` changed
in production. Companion timeout stderr is now an accepted trailer, not an
independent proof of pre-execution failure. Existing budgets and fail-closed
ambiguous-execution handling remain intact.

## Verification

BS10610 isolated candidate at
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/ssh-banner-20260927`.
Cached Airflow image `sha256:58195672af685cfa6551cfc44b37b6218bd2039c44b717163a6e8072f78dfd2b`,
`docker run --rm --network none`, source mounted read-only, no credentials/data.
`python /case/dags/tests/test_wgs_ssh_retry.py`: old source6 tests/1 expected
failure on two-line timeout; corrected source6 tests passed. Cases preserve
refusal of trailer-only, remote stdout and mixed traceback, and reconnect budget.
No full suite, fault injection or unrelated runtime test was performed.

## Deployment

Production `server96`/chenjc, control `/data/airflow-WGS`. Immediately before
switch, no active Airflow DAG/task. Immutable DAG source:
`/data/airflow-WGS/releases/20260927-ssh-banner/dags/bio_wgs.py`, SHA256
`991317e511d35925b9def3c6addf04464b9607cda54e93ecf8bc7e7f131d925c`.
New directories0755/file0644; existing runtime permissions unchanged.

Private `/data/airflow-WGS/ssh-banner-20260927-control/{compose,rollback}.json`
retain exact three-service settings and prior file mounts. Both compositions
validated. Only `airflow-api-server`, `airflow-scheduler`, `airflow-worker`
recreated using `up -d --no-deps --pull never`; only bio_wgs.py bind changed.
IDs now `e7fbfd700517`, `c3a82b9c35a3`, `e3d9ac3dbdbf` respectively. All running,
zero restarts; all three DAG hashes match. Remaining9 services retain their
container IDs. Scanner/dispatch flags, DB, runtime, images and WGS source unchanged.
Scoped composition emits expected unrelated-container warning; no orphan removal.
Airflow `dags list-import-errors --output json` returned `[]`.

Rollback only after an idle check: use rollback.json with the same three explicit
services and --no-deps/--pull never. Do not reset task states or delete outputs.

## Original task recovery

One authenticated platform POST to
`/api/runs/WGS_20260927_090701_56DC81/actions/resume` returned submitted/attempt2,
DagRun `WGS_20260927_090701_56DC81-a2`. Uses existing internal-service API auth;
no credential output, direct DB edit, hand-created DAG or new analysis ID.
Batch remains20260919A-test. Existing three-stage semantics preserve history and
require fresh user configuration/execution approvals.

At17:26:59 CST `prepare_wgs_sampleinfo` succeeded (exit0), execution
`wse_9e948608dd668b7af65a884d`, generation1. API confirms `config_review` and both
approval timestamps null. User can continue normal configuration review; no
configuration/execution approval or cloud analysis was performed by this repair.
This recovery connected successfully; the two-line retry path is established
by the bounded regression, not an injected production failure.
