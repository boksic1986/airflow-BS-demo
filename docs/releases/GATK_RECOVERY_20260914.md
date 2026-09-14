# GATK recovery, polling retries and guarded Step7

Code:0436dce56252a7b3764c2d77b2b3ce341feeef4c. User approved plan1/2,
Step7 parity and Sample repair. No WGS historical deletion/new batch, automatic
release upgrades, scientific-rule change or automatic SFS cleanup performed.

## Verification

BS10610 isolated cached images, network none/pull never:55 focused backend/gate/
resume tests and42 existing runtime/registry/transfer/workspace tests passed.
Frontend27files/99tests passed; TypeScript/Vite build1852modules passed. Actual
Airflow network6tests plus concurrency, successful-stage dependency and independent
maintenance DAG contracts passed. Review fixed stale-success Sample projection,
cleanup target hash freezing, active-generation retry protection, strict PodList
queries, receipt/hash validation and lifecycle display without Step7 capability.

Early failures:missing PYTHONPATH for a standalone DAG test, two nonexistent test
filenames, frontend lifecycle condition/new test origin expectation; corrected
and rerun. Read-only pytest mount emitted cache warnings, not test failures.
Isolated airflow dags list was not accepted without a disposable metadata DB;
real production DAG import/API checks succeeded after deployment. No authenticated
browser visual test or actual Step7 deletion is claimed.

## Production release

Hostserver96, release `/data/airflow-WGS/releases/20260914-gatk-recovery-0436dce`.
Source archive SHA2569a239bd8631d286b270296d15063f360a90fcdbdb1facc6dc19f3bf03c020c7c.
Actual source mounts verified, not inferred from the unchanged historical current
symlink. Existing private environments and all non-target mounts preserved.

| Service | New container | Change |
| --- | --- | --- |
| backend | 8388a8e8b600 | new release /app |
| wgs-run-observer | 05aa580c5932 | same /app, DEPLOYED_PIPELINES=wgs,gatk |
| airflow-scheduler | b0501dadc048 | bio_gatk and new maintenance DAG mounts |
| airflow-worker | f1ac3a1df310 | same DAG mounts |
| airflow-api-server | 773850a151d2 | same DAG mounts |
| frontend-nginx | ddba6fa13eed | coherent frontend build |

Backend/observer image0e2d6f0cdf4b; Airflow58195672af68. Frontend image
`airflow-demo/frontend:gatk-recovery-0436dce`,
sha256:0c5ddd4f0f4bf61b961c1a1bac08fe4738cfa37b6428af93d31612046c4dcece.
Production rebuilt its own source using the approved cached Node22 builder;
99tests/build passed again. Served JSindex-D_WTIAF6.js SHA256
8dfe4ae24d88aa3e2352d57e1ca5075ade4ccd1de89d7809893a5adeab71ca45 and
CSSindex-CdK5PwQa.css SHA256
ed4e11e3c3bbbbdecbf78a0107bb9800b332d9045c640d464f777348ec5cf291.
No additional rule-layout stylesheet link remains. Existing nginx /23 office
allowlist includes172.20.9.143 and was preserved. Gateway/API health200 via
172.17.61.96; localhost Docker-NAT request403 is not the approved gateway test.

Private compositions/rollback inventories (credentials stay server-local):

- ctapa:`/data/airflow-WGS/candidates/gatk-recovery-0436dce-control/{compose,rollback,before}.json`
- chenjc:`/home/chenjc/.config/airflow-gatk-recovery-0436dce/{compose,rollback,before}.json`

Use the matching identity, `docker compose -p airflow-wgs -f <compose.json>` and
only explicitly selected services with `up -d --no-deps --pull never`. Do not
remove orphans. The chenjc candidate-root permission failure was resolved by
using its existing account-private configuration directory, not widening ACLs.
Compose render and exact live-environment comparisons passed before recreation.

Temporarily paused bio_gatk with0running/queued tasks, replaced only six services,
then restored unpaused. Both DAGs have no import errors. API confirms waitStep3
retries6. Scanner2a2823d4abbe, ledger worker061ff3623876, probes89787f5a7003/
0f5bce482234, Postgres957f05931b74 and Redis8b60aeff5e06 retained IDs. Scantrue,
autodispatchfalse preserved. WGS8records/0active; latest0910A remains success.

Node200t640/ctapa gate matched old main before guarded install. New hashes:

- gatk_runtime_gate.py:759902ff0ed933a9a9d9719d8c5f42b14fdaa17159e914553c536753d8c34f4c
- gatk_maintenance_gate.py:15e7e9e8032340670c7c5370a53ae026524a53e25b88902c52dd2affa82d041d
- gatk_resume.py:bf6b82a76371415bfd3b1d7045fc4a10e1f3d825dff6806988e6a145d945dd41

Installed adjacent to existing private forced command; Python3.9 compile passed.
Original gate preserved as gatk_runtime_gate.py.pre-0436dce. Existing runtime.env,
SSH keys, output permissions and long-running monitor processes preserved.

## Recovery evidence

0823A:GATK_20260913_155423_30EFFE attempt1. Original finalizer worker failed;
its detailed stderr had expired. Scoped fsync/readback and synthetic tar--zstd
probes passed; probe files removed, two terminal diagnostic Jobs retain TTL86400.
Wrong-UID raw DELETE precondition rejected the request and preserved diagnostic
Job. Real dry-run required existing runtime.env; an outside-env OBS wrapper
check exited127, not an authorization/data failure. Strict PodList, terminal
identity, all Worker checks and OBS result protection then passed.

Old failed MasterUID18282066-de80-4f8c-87ef-d1226a837a12/RV39482764 conditionally
deleted. Original frozen Step2 created UID52fbf32c-d474-4a63-b5c7-a862cb69f167 at
14:21:00Z and completed native START handoff. Same attempt/run-id/workdir/versions;
no Step0, upload, forceall, OBS/result deletion or successful-rule reset. Private
UID-keyed journal records completed and the execution log retains native output.
Replacement Master completed; generation3 monitor verified Master/logger success.
Dry-run then exact12-task Airflow clear reopened startStep3 and downstream only;
all preceding task states/try numbers preserved. Step3/4 succeeded, Step5 downloading
at22:37CST checkpoint. Full Step5/6/batch completion still pending at this checkpoint.

0907A:GATK_20260914_045846_789C29 attempt1/gen1, original Master/monitor retained.
Cleared only waitStep3 after dry-run to adopt retry policy. Other task states and
try numbers unchanged. Still processing finalizer at the same checkpoint.

Both business runs and all28Sample rows now running, confirmed through API.
Step7 panel is deployed but blocked until latest Step5/6 verified success and no
active workloads/leases. Cleanup remains a separate explicit administrator action;
it does not turn a successful analysis/Sample into failure or run automatically.

## Rollback and remaining work

Restore selected service images/mounts from each private rollback.json after
fresh active-task check; restore the backed-up node gate if required. Never
rollback the recovered Master by deleting it or clear uploads/Step2. Retain DBs,
receipts, outputs, leases and new helper audit files. Do not restore stale failed
Sample rows. Broader release auto-discovery, unified cross-runtime locks and WGS
historical cleanup/new batches remain separate follow-up work.
