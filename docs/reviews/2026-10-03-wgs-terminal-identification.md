# W423-TMP-CONSUME-323D3F-20261003

Scope: human consent `01a0fe87-4404-7453-aff6-4fe9931d893f`, existing
`WGS_20261002_095408_323D3F` attempt 1 only. Automatic monitoring remains stopped.
No direct production database access, new route/table, native change or release swap.

## Diagnostic checkpoint

Existing authenticated HTTP detail returns `recovery=null`. The precise failed
predicate is unknown; workspace Step2 projection is not proof of row selection.
An independent-process handler hook was rejected by the coordinator and was never run.

The single backend module adds allowlisted rejection logs only. Original stage
selection, return values and terminal validation remain unchanged. No observation,
request, params, patient field or raw exception is logged. Final source SHA:
`90bb1f19c34b642bf1592d55d5c82b736c9b45fbe3b41775afaa3ad357d1eb58`.

BS10610 isolated network-none backend image `8ba8858e3bf3`:

- Original source: 1 RED (missing diagnostic), 0.59 s, raw SHA `30400ce880fac2a00d86d4904289ac23f1c0c4b38f030f50775509e71c89ffe5`.
- Candidate: 1 GREEN, 0.53 s, raw SHA `386b90d6b428d160c8a2f51306c47f8dd115e138872daacb5eae18ff5d0f828b`.
- Independent review requested one equivalent log for the no-row symlink rejection;
  it was added without changing `(False, None)`. Coordinator accepted final SHA,
  explicitly requiring no duplicate test.

Raw/XML: `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/wgs323d3f-terminal-fence-20261003`.

## Production deployment preconditions and rollback

Actual target:
`/data/airflow-WGS/step7-perf-20261002-fd85593-control/merged/backend/cce_recovery_budget.py`.
Original SHA `77c8879fe0c694ef9ff367f36032074b313b7f36c7849ffb0a66553661320ebb`,
UID 6708/GID 520/mode 0644. Existing backend a705/image0e2d, current release
`releases/20260912-panel-opt-4d3d24e6`; all service mounts/images unchanged.
Uvicorn has no reload; only backend restart is needed. Worker/scheduler/observer/
frontend/native, environment and gates are preserved. No uninstalled 4fc progress
patch or other source is packaged.

21:52:18Z UTC actual effective auth=true, scan=true, automatic dispatch=false.
Raw environment flags are combined with intake policy. Two failed preflight
methods asserted raw auto-dispatch=false or effective scan=false; both stopped
before writes. They were incorrect probe assumptions, not production drift.
Airflow running counts were zero for bio_wgs, bio_gatk, native monitor and both
maintenance DAGs (each total_entries=0).

Coordinator pre-approved this exact single-module diagnostic activation after the
above conditions. Planned private control directory:
`/data/airflow-WGS/wgs323d3f-terminal-fence-20261003-control`, mode 0700.
Preserve original bytes in `cce_recovery_budget.before.py` before installation,
verify original SHA, and preserve source UID/GID/mode. Rollback restores those
exact bytes atomically and restarts only backend. API interruption is limited to
the backend restart; no compute/transfer is restarted. Each deployment and the
single diagnostic POST uses a new exclusive intent, preserving the consumed
original 21:08 POST guard. The diagnostic response may be ignored or may project
normally; record its real outcome.

## Current status

Diagnostic module90bb installed21:56:47Z UTC; only backend restarted21:56:50Z.
Private control directory actually2700 due to inherited SGID (permission bits700).
An initial full-mode0700 assertion stopped before backups/guards/module writes;
readback confirmed2700, after which the secure permission-bit check proceeded.

21:58:10Z the new exclusive diagnostic POST returned200/ignored. Actual log:
current_stage=selected_stage=step2_master, generation2, executionwse_c67b,
statussuccess/receipt1ffdff22; predicate=native_stage_terminal;
validator_reason=native stage success execution identity differs. This proves
stale run progress selected Step2 while validating the real Step3 failure.

## Minimal cause repair

Only normal selection now uses the latest current-attempt native registration
by database ID, preserving explicit cleanup and all original validation. It
does not trust caller stage, reuse old saved compute binding, change run progress
manually or introduce automatic-recovery eligibility for a business rule failure.
Final candidate module SHA:
`55cb60deeed2d029561f64e559b541aedb7d1e1b0feb6488a767bc2b96bd594a`.
The SQLite regression reproduces actual Step2gen2/Step3gen1 registration order;
shared negative variants cover execution/generation/hash/receipt/state/old Dag,
newer generation and downstream stage, retaining explicit cleanup selection.
On installed diagnostic baseline: 1 RED/9 passed,1.60s, raw SHA
`4e312325d1b869891eea6539f95c7df234984316a951fac630ff68c80f32bab2`.

The initial selector candidate passed its 10 selected cases (1.75 s, raw SHA
`8ee7a582b70b7c7f14ae9c07e20a2497ad250071629b09011f17c5ae6f53d9d3`).
Coordinator review identified one settings-absent legacy path: a selected Step3
with unconfirmed query could return legacy `None` while lagging run progress was
Step2. The added single negative reproduced this (1 RED, 0.51 s, raw SHA
`9011814c1add9c8e803e5c88e2a376d88dc330143eec8feebc067ea0ff051790`).
Legacy `None` now requires run progress already Step3; the lagging case takes the
existing settings-unavailable rejection. The original Step3 diagnostic remains.

The existing cleanup fixture accumulated downstream registrations before its
separate Step3 checks. Only synthetic Step4–6 rows are removed at that context
boundary; Step1–3, Worker quiet, nonce and generation checks are preserved.
The new downstream-stage negative still rejects an old Step3 snapshot.

Final minimal acceptance uses the existing BS10610 backend image `8491604ee01d`,
network none: new group 11 plus existing `test_unknown_stage_cannot_fail_or_release`,
**12 GREEN**, 3.13 s, raw SHA
`bd8bc7a467131d0b0551cf79db69015b691cd5e9290449b4ab08e0a242653eb3`.
Files `final-green2.log` / `final-green2.xml` under the evidence root above.
The first combined attempt used image8ba without FastAPI and stopped at
collection (exit4, raw SHA `4d5f807d8483517a66cd62d8a13ca758af25029a40bcd37af4d12191fce99078`);
it is not counted as acceptance. No broad suite or clinical canary was run.

Cause repair activation must compare actual installed diagnostic SHA90bb, save
those exact bytes as the immediate rollback, atomically replace only this module
and restart only backend. The original77c backup remains preserved. Production
cause repair is pending coordinator final diff/GREEN/target/rollback approval.

Repair activation, tmp creation and same-attempt Step3 Resume remain pending.
All original successful outputs and evidence are protected. No Step7 or cleanup.

## Accepted production repair

Coordinator final GO followed source/actual RED/GREEN review. Precise source,
tests and documentation commit: `edbe381ad91a838be66e5d1f8c7ede8db1def9c6`.
22:19:57.761677Z UTC actual90bb→55cb atomic replacement completed; only backend
restarted22:20:00.536410Z. Service IDs/images/mounts/env and gates remained.
Actual SHA/metadata and `/api/health`200 read back22:21:54Z. The initial wrong
`/health` path returned404 before creation of any projection guard or POST.
22:21:55.647937Z the new exclusive normal dag-terminal POST returned200,
ignored=false/status=failed for original323D3F/a1. Old guards were not replayed.
Immediate rollback is the saved90bb diagnostic module, alongside preserved77c.
Tmp creation and normal same-attempt Step3 Resume remain pending. Monitoring
remains stopped; no new attempt, release change, Step7 or cleanup.

## Original-attempt restoration remains incomplete

The normal platform failure projection succeeded; restoration then stopped at
the authorized exact tmp utility. No existing node mount matched the actual SFS
PV export. Coordinator accepted one existing native reader-generator utility,
with only biosan-clinical PVC and original image/UID/GID, no fsGroup mutation,
backoff0 and180s deadline. Actual create22:42:42Z returned0; Job UID
`afdd48e4-2907-4371-93ca-897743e1a872`, document SHA
`05a83e8004d9be96d1d7cf93bff1aa9d236d4da7aca987a4f4c899072338460f`.
It failed22:43:12Z/BackoffLimitExceeded. Exact Pod GET confirmed absence of UID
`857cfb34-a097-4815-92dc-1da2007e32f3`; this is not a label-selector omission.
Scoped Events prove volume mount/image pull/container start22:43:09Z, but no
container exit message or deletion actor. Effective workDir value and tmp
creation are unknown. No second helper, Resume or new execution was dispatched.
Private original evidence is retained under the node operator-evidence task
directory; existing durable cloud logs are the next evidence route to assess.
Automatic monitoring remains stopped. No inputs/results, locks or old resources
were deleted; no Step7 was run.
