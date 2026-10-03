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

## Single read-only path probe

Coordinator accepted one existing-reader/exec probe after native confirmed no
known persistent utility-log entry. Only biosan-clinical PVC and /workspace
mount were read-only; original e481 image/UID/GID10001, supplemental groups520
and10001, no fsGroup/env/init/OBS, backoff0/deadline180s. A short sleep kept the
container alive while one exact owned Running/Ready Pod exec synchronously
captured stdout/stderr into private node evidence. No mkdir/chmod or Resume.

23:08:38.559019Z CREATE returned0, Job UID
`369a0b24-3450-4d56-8171-17c58e85b75c`, document SHA
`408cd3515d48fe3d1cedc9c6c591990f5fa5c29bae9f64d7e66faf1cbdc7b33a`.
Pod UID `71bf8d89-655d-401f-b92b-260ec869c737` exec returned0 at23:09:03.848060Z;
stdout SHA `840b70095839ed6241c6ea185fcf25eec7a5aa16dad8a161e421a51111dddb7a`,
stderr empty. The top-level workDir matched the frozen run/work and yaml import
was available. Run/config/work were real same-device directories10001:520/2775;
tmp existed10001:10001/2775. The probe identity was10001:10001/groups520,10001.
No unrelated configuration values or recursive content were retained.

This resolves current path attributes only: original utility exit cause and
creation actor remain unknown. Its extra GID520 assertion is not a frozen
Master requirement. Existing tmp must not be changed to satisfy that assertion.
Both probe guards are consumed; no third utility or additional exec. Results were
handed to coordinator for the next recovery decision. No new action/generation
or attempt has been registered; automatic monitoring remains stopped.

## Same-attempt Resume stopped at native final-evidence validation

Coordinator accepted current tmp attributes without further mutation. One normal
same-attempt Step3 Resume returned200/queued23:14:24.043870Z, action
`resume_ab7c8b403a0d60aa7f371012`, Step3generation2/execution
`wse_acb2905b05475cf607ecaffd`, request hash
`4fbaed1bcad243d400d50a95fb8c763dea798a98c37fa3ee1432c44efd370a03`.
Original deadline2026-10-07T12:45:38.887362Z, release3f/attempt1/five inputs and
successful Step2gen2 predecessor remained unchanged. The exclusive Resume guard
is consumed; no repeat POST or new attempt.

Native business failed23:15:34.119625Z, SHA
`f41604d4d8c25b2454ae307dfa0fc08a863e32022457e73046dfec5562294967`;
terminal `e9be230fe07342588be832a9044c5d5a9ddc034cb1e6d47198fb5d78c41f2ffb`
confirmed failed with matching business hash and current identity. Airflow start
task succeeded23:15:00, wait failed23:15:38; Dag and platform were both failed.
Start-task success is not a native START receipt.

The4755-byte private worker log SHA
`bce0416eba8c1af3c0aba5ab5df4a70eed4693bbe9bc4d4e6740e748e196a5f7`
ends at paired prepare_monitor_registered1255/resume_registered1161, native
_recovery_final_evidence1877/require1865. Static source SHA
`bfa1e15f75f83ebe816897e1e454225ca2f78128b1761a2212230d033cd3c3d1`
confirmed RuntimeError literal: `native final recovery evidence is incomplete or inconsistent`.
Specific missing evidence has not been established. Current tmp existence is
still confirmed; this is not proof of another missing-tmp error. All recovery
writes remain stopped pending coordinator's precise direction. No native/core,
receipt/lock, directory or permission edits, extra utility, test or installation.
Automatic monitoring stays stopped; original inputs, successful outputs and both
utility resources/evidence remain protected. No Step7 or cleanup.

## Exact recovery evidence gap

Actual bfa1 native1877 checks `isinstance(values,dict)` after handoff schema2,
job/pod UID and recovery-context checks have already passed. Values come from
the selected source mirror with require_terminal=True/require_worker_manifest=False.
The confirmed initial journal SHA863b41eb binds source to the submission-wse_c67
view and old Master UIDeb02fef8. Its mirror marker SHA
`4f0dcae47260afd8185b9ed15fc5310241e91358b4d2f37553e69e4d8e2258e8`
is COMPLETE with matching run ID, but mtime2026-10-02T15:56:21Z. It lists only
jobs.ndjson0B, analysis.log760828B, START_CONFIRMED.json1683B and master-job.json6150B;
all four listed sizes/hashes match. No terminal marker is listed.

The initial diagnostic name whitelist omitted START_CONFIRMED; its early
unknown-name stop was a method limitation, not a native rejection. Actual native
EVIDENCE_FILES was read and the full list verified; final diagnosis uses the
unchanged native pure reader. At23:32:56.705407Z, marker SHA unchanged before/after:
require_terminal=False returned dict, True returned None; RUN_FAILED/RUN_COMPLETE
decoded as None, native_has_terminal_evidence=False/analysis_complete_marker=None.
The gap is terminal evidence handoff into the selected old mirror, not corrupt
files or tmp permissions. Presence of terminal data on SFS was not established.

Actual normal producer is native Step3 collector3016 then mirror writer3066;
the failed Resume stops before that evidence refresh. Coordinator accepted the
precise diagnosis and delegated the existing trusted collection contract to the
native owner. No collector, new cloud query/utility or mirror write was invoked
by this diagnostic. Recovery writes stay stopped; no use of False to proceed,
fabricated terminal, repeated Resume or lock/receipt/core edits. Automatic
monitoring remains stopped. Node private evidence files:
current-source-mirror-field.complete.safe.json and native-mirror-terminal-contract.safe.json
under the same operator-evidence task root. No Step7 or cleanup.

## Final blocked scope and version correction

This dated stop was superseded only by direct human message
01a0ffab-054f-7170-a502-864619e930a6 authorizing the existing trusted SFS
reader and normal original-attempt rerun. No source, tests or deployment followed.
At03:13Z one narrowed readonly native reader retrieved alias and original UID
archive separately. Both contain identical RUN_FAILED e6245528, START8da61764
and FINAL65691ba7 for eb02/cf2/nativegen1. Actual native final validation passed,
and native writer published mirror2f83a6cc; the full old4f0d mirror is preserved
privately. The reader was retired with exact UID/RV and03:16 readback confirmed
Job absent/Pods0. Thus SFS did emit the failure receipt; the previous local mirror
had missed its terminal refresh. At03:17:19Z one normal same-a1 Step3 request
returned200/queued: action4d7613, generation3, executionwse_a8c703f0c3c1e6491e74cad8,
hashfd1b03b8, original deadline unchanged. START is still pending verification.
Automatic monitoring remains stopped; no repeated POST or new attempt is allowed.

The single request later failed at03:19:52Z with exact actual bfa1447
`Master confirmation identity mismatch` (messageSHA39f39516), not the previous
final-evidence check. The append-only worker log keeps both old and current
traces; current final trace reaches paired1217/native2219/1420/1447. AF and
platform are failed. The03:22/24 START_SENT journal readings were after this
failure and are stale control observations. A scoped read at03:29 proves new
Mastercb75/Pod6714 still active/Running while host1303859 is absent. At03:30:56
the exact owned Pod's real START24a224a6 matches every expected identity key,
nativegen2/platformgen3/wsea8c/hashfd1b/action4d. Its confirmed epoch is
03:20:10.599824Z, within its handoff deadline and18.326s after the host failure.
Cloud START is real; platform recovery and full workflow completion are not.
An old-alias handshake race is a supported inference; the bytes observed at the
failure instant were not recorded. No automatic attachment, new request, code,
deployment, marker/status/lock change or workload deletion followed. Further
writes are stopped pending a precise direction; automatic monitoring stays off.

Coordinator's native contract conclusion: bfa has an internal SFS reader through
_collect_step3_evidence(require_terminal=True). Public CLI has no force-refresh;
ordinary Status/Resume may reuse a complete, nonterminal mirror when the Job is
absent. Internal collection creates/deletes a reader and reads run-level aliases,
so precise original Master UID and trusted source identity must be verified.
This is a new evidence retrieval/possible source repair scope. Coordinator will
explain it to the human and obtain new authorization. No internal producer,
collector, evidence refresh or Resume is authorized by this handoff.

Actual paired source remains981e7e82/line1161 and native source bfa1e15f. The
native-owner contract referenced paired66f; coordinator requested correction to
the installed981 baseline. That reference is not deployment evidence or an
operating path. The actual pure-reader terminal gap evidence remains valid.

Current identity remains original323D3F/attempt1/actionab7/Step3generation2,
wse_acb2905b05475cf607ecaffd/hash4fba, native/Airflow/platform failed. Last live
evidence23:32:56.705407Z; this final update is documentation only, with no SSH,
cloud/API operation, test, installation or new production change. Keep writes
stopped, monitoring stopped and all original successful outputs/input bindings,
deadline, utility resources and private evidence. Do not fabricate terminal
markers, use require_terminal=False to proceed, change locks/receipts or create
another generation/attempt. Native owner supplies the corrected existing trusted
collection contract; coordinator owns the new authorization and review boundary.
