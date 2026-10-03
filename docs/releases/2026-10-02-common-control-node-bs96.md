# BS96 paired WGS/GATK control-node configuration

Task: `W423-COMMON-NODE-CONFIG-20261002`. Times are UTC on 2026-10-02.
Production owner: Airflow thread `01a0e728-4c99-71d0-87e9-987b311022c9`.
Coordinator: `019fa8d1-0d81-7e92-abee-8154dd1cf0a7`.

## Direction and actual outcome

Human message `01a0fcd4-a575-7e53-bde4-6bef27dd82b0` explicitly selected the
node-switch consistency work and stopped the progress rollback investigation.
The existing mode remains default200; when200 is slow, WGS and GATK use96
together temporarily.97 is not an alternative. Node choice does not change the
frontend, workflow logic or accepted versions. The coordinator reviewed the
actual packet and active-run boundary before the bounded production window.

At14:15:14 the existing worker and scheduler both selected
`WGS_RUNNER_200_ALIAS=GATK_RUNNER_200_ALIAS=wgs-cce-node96`.
Actual SSH resolution was172.17.61.96 / ctapa / strict host checking.
Each pipeline retained its original restricted command:

- WGS: `/home/ctapa/.config/airflow-wgs/forced-command.sh`.
- GATK: `/home/ctapa/.config/airflow-gatk/forced-command.sh`.

| Service | Previous container | Actual container |
| --- | --- | --- |
| airflow-worker | acb2289ecb7589597e4eb6b9aea29c4a19309c95f7df1917d4ad935a8cdea33f | c92ad8fe4b2b1bc9e197fca8f47da90b59638d6b9266bd97c705758584021342 |
| airflow-scheduler | d206c0bf14881a4501f5d8c152b63ce3e574dc65d378458d95f7ec192df2b70b | 24301f4b730fa65a42018d3477444ee8bbe356bb613f5b1b0ac68ba082d7e0a4 |

## Exact packet

Only each service's existing `GATK_RUNNER_200_ALIAS` changed fromwgs-node200 to
wgs-cce-node96. Restoring that field in each candidate reproduces the original
Compose structure. Both Compose config checks returned0 before activation.

| Service | Original Compose SHA256 | Candidate SHA256 |
| --- | --- | --- |
| worker | 621f8cb73edaf3f05a3a60218b0654af14f58604849a216dd2798b493d95ed98 | 48956e5bdc11c10214d055fae842907e8aa532448083f725ce24cd845c978b2f |
| scheduler | 66eed642ec616b566224ef5b2b3f7693dba36dfdce96cfb567b3eaabe519cada | 064316a920616166da489ed8d5689ae9984be099e8e3f2c12b692339e11567b5 |

Actual current config files:
`/data/airflow-WGS/w423-common-node-20261002-control/airflow-worker.node96.private.json`
and `airflow-scheduler.node96.private.json`. The directory is0700; original
Compose copies, container snapshots, manifest and operation receipts are0600.
The original project working directory remains
`/data/airflow-WGS/ssh-banner-20260927-control`.

Image58195672, all other environment values, mounts, user, command and entrypoint
matched their actual originals. Other service IDs were identical. SSH config
SHA `df94468ad8cb7bbc03e16327d9accdbbe259d6d29c3a2c96a1072f47303e5370`
and the original200 Host stanza were unchanged. Backend, observer, frontend,
DAG source, native/shared bootstrap and accepted Step2 pair981e/ec6f were not
modified. No image build/pull, profile installation or progress patch occurred.

## Changed connection and active-run boundary

At13:49 the actual worker SSH key and existing strict96 pin reached the GATK
restricted entry. A deliberately incomplete `--native-observe` returned the
expected GATK invalid-arity rejection before loading a request. This verifies
the changed restricted connection path; it does not claim a new GATK analysis
or native workflow canary. Native observe/submit and cloud calls were zero.
The13:19 GATK96 paths and original shared pin evidence were reused.

Current WGS analysis `WGS_20261002_095408_323D3F`, attempt1, action
`resume_c17cd7cf8b3ab245ae80304d` remained on96. Its Step3 execution was
`wse_b7f6bc858e2a3284ed0c01a0`, generation1, request hash
`744d85bdf5b47002a834c16022e628ff8b83ea2ba1448d0454f7e007fff4d8b1`.
The original background process remained PID/PGID/SID944075, boot
`ef1fa37a-19b6-4f56-82e0-84495779f6ec`, starttime ticks4483218750.
The process was outside the worker cgroup and matched before and after changes.

Admission into the window required current queued/running TI0, actual worker
active/reserved/scheduled all empty, and the same native identity. Scheduling
was stopped before worker recreation; no active task was killed. Worker and
scheduler were each recreated exactly once, using no-deps/no-build/pull-never.
There was no POST, task clear, rerun or duplicate native dispatch.

## Failed maintenance methods and recovery

Original evidence and consumed guards remain intact:

1. Packet output used a duplicateutc argument after saving valid scope evidence;
   only the local helper output method failed. A narrowed reader used the saved
   scope without repeating preparation/connection.
2. The first worker inspector used system Python, which lacked Airflow before
   RPC. The actual CLI interpreter `/home/airflow/.local/bin/python` was used.
3. An inline PowerShell SSH test expanded hostname locally and was rejected;
   all subsequent remote actions used saved scripts through CR stripping.
4. The14:04 window stopped at an extra passive broker-method failure. It had not
   recreated a service, and restored the original scheduler at14:04:25. Original
   child stderr was not saved; later minimal classification found ChannelError
   from the extra passive method while all worker task counts were zero. The
   coordinator explicitly returned to the originally accepted TI/three-empty/
   native conditions. The old guard was preserved and a new window used a new
   intent. The extra investigation did not alter product code or broker data.
5. Window2 changed the worker at14:10:17, then its immediate startup inspection
   lacked a reply. Accurate stderr was saved. At14:12 the worker was running,
   logs showed ready with no traceback/error, and native identity still matched.
   Only the previously unexecuted scheduler action continued after actual new
   worker active/reserved/scheduled all empty at14:15:07. Worker recreation was
   not replayed.

Scheduling pauses were14:04:08–14:04:25, then14:09:56–14:15:10 (about5m14s for
the second window, extended by startup verification). Remote monitoring and
analysis continued with the same process identity. These were not zero-pause
service changes.

## Natural handoff and future paired switch

At14:17:56 public workspace, Airflow DagRun and native status were running in
the same Step3 tuple. The original startStep3 task remained successful at12:45;
waitStep3 naturally poked14:17:51–14:17:53 and became up_for_reschedule.
Five selected samples remained. The status at this read was a confirmation
withoutmaster counters; the known progress-display behavior was unchanged.
Step1–6/final-result completion has not been declared.

Use the existing configuration choices as a pair:

| Mode | WGS_RUNNER_200_ALIAS | GATK_RUNNER_200_ALIAS |
| --- | --- | --- |
| default200 | wgs-node200 | wgs-node200 |
| temporary96 | wgs-cce-node96 | wgs-cce-node96 |

Keep separate restricted commands and existing adapter/input/profile checks.
Prepare both actual service candidates together and compare every other field.
Editing Compose or usingrestart does not update the live environment; applying
the accepted pair requires the controlled service recreation boundary. Do not
change the meaning ofwgs-node200 in SSH configuration. Do not migrate an active
execution or return this current run to200. The target's accepted pair must be
verified before a future switch;200's current981e compatibility was not validated
by this release. A switch is not permission to downgrade/install runtime code.

The original Compose copies provide a configuration rollback source, not a
whole analysis backup. A rollback must use current service/source CAS and known
active-run facts. If no new GATK execution has started, only the changed services
can restore their saved configuration; WGS remains96. If state is unknown or a
new execution exists, read back and coordinate instead of replaying guards or
migrating its identity. No rollback was performed after successful completion.

## Evidence and seven-field closeout

Private local directory: `.codex-artifacts/wgs-gatk-common-node-20261002/`.
Primary records: `packet-preflight.safe.jsonl`, `native-worker-separation.safe.jsonl`,
`activation-once.safe.jsonl`, `activation-window2-once.safe.jsonl`,
`window2-partial-readback.safe.jsonl`, `finish-scheduler-once.safe.jsonl`,
`natural-monitor-handoff.safe.jsonl`. Remote final receipt:
`/data/airflow-WGS/w423-common-node-20261002-control/finish-scheduler.completed.private.json`.

| Field | Result |
| --- | --- |
| Task/scope | common-node configuration consistency completed |
| Workspace/version | gatk-prod-compat; accepted sourceb861/paired981e retained |
| Implementation | two existing GATKalias env fields; operation docs only, no product-code patch |
| Acceptance | exact config/changed restricted connection/active-window and real post-change continuity evidence |
| Deployment | two actual services above; all unrelated differences0 |
| Evidence | original failed/success receipts and safe records preserved |
| Remaining | sole hourly monitor follows current WGS Step3–6; full workflow still incomplete |

All input FASTQ/OBS/sampleinfo/pending/reference/history/results/evidence and
other batches remain protected. No Step7 or data cleanup occurred.
