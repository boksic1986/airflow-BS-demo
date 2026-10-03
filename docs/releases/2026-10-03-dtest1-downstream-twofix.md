# W423-DTEST1-DOWNSTREAM-20261003

## Scope and authorization

Direct human message `01a10148-9a1d-7462-9faa-beb004464457` authorizes
only trusted evidence-directory lookup and original producer reference fixes.
Latest direct message `01a1016e-a827-7893-bd0b-5a17d81b45f0` stops further
fixture/testing iterations and directs minimal production deployment.

Target: `WGS_20261002_095408_323D3F`, attempt 1, original five samples,
successful Master `cb75dde6-d06c-4f06-a4c3-63db8dc04ca7`, original deadline
`2026-10-07T12:45:38.887362+00:00`. Reuse its results through normal APIs.
Automatic monitoring remains stopped.

## Source change

The paired module derives a fixed recovery root only from the authenticated
registered request. The callback rechecks original bytes, digest and control
directory. Initial submission journals remain in the immutable registered
spool; WGS recovery journals are read only from the authenticated control.
The native guard uses the same pinned callback during factory, validation and
owner resolution. Default single-root and GATK behavior are preserved.

The original Step3 producer is selected by authenticated request-history links,
strictly decreasing generation and unchanged identity/control/deadline. Each
request's original bytes are rechecked. Missing or foreign chain entries fail
closed. The terminal producer supplies the native binding consumed by Step4;
the failed observer does not become the compute producer.

No registration, journal path, public schema, frozen input or receipt is edited.
No new Master or START, compute rerun, reupload, new attempt, UI, DB, Step7 or
data cleanup is part of this release.

## Verification facts

Independent static review accepted paired `415a45be` and native guard `64438f44`.
Native scoped boundary verification: four RED to four GREEN, log SHA256
`6209e76787c11123ec068de07433169a95fc466b44ac5985df3db6db95bde92a`.

The affected split-root/observer-chain combo reproduced the old code failure:
one failed, eight deselected; RED log SHA256
`196f94cda92c8341872dd218534af160e76314e1666fddeab886ac4c4642a815`.
Subsequent combination runs did not reach full GREEN. All raw evidence is kept.
The latest failure was inconsistent synthetic binding/template labels, SHA256
`b23535ffc3b28415162eb52e5c756311a701734f2bcdd696ae02351b51d34cd0`.
The final fixture correction was not executed after the human stopped further
testing. This release does not claim that the affected combo passed.

## Minimal deployment and rollback

| File | Old SHA prefix | New SHA prefix | Owner / mode |
| --- | --- | --- | --- |
| native assets/cce_writer_guard.py | e99378dc | 64438f44 | 6708:520 / 0644 |
| common scripts/cce_paired_runtime.py | 3fc179a9 | 415a45be | 6801:520 / 0644 |
| initial-recover-a2a0bbc-c8d07c21-v2.json | a64b559b | 6c8617a3 | 6801:520 / 0600 |

The policy changes only two hashes. Native runtime `af05ea22`, both bootstrap
documents `b928a9df`, all paths, settings, ACLs and services remain.
Task-private exact old bytes and separate once guards are required. Close the
five existing entries only during a real shared-consumer quiet window; switch
files under their original owners; validate the matching source/policy pair
and restore original entry bytes. No service restart.

Rollback requires the same quiet, closed-entry window and restores exactly
guard e993 / paired 3fc / policy a64 from this task's backups. Keep runtime
af05 and all old/new execution evidence. Do not roll back run generations.

At this source checkpoint production is not yet changed. Operational receipts
will be recorded in CURRENT_STATE, TASKS and HANDOFF after actual deployment.
