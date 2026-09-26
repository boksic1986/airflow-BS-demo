# P0 smoke entry check — 2026-09-26

## Source correction verified — 2026-09-27

Native `ed39d21` / runtime SHA256
`71d7c041943607e112713b75732e4ba5ade1bf63354b5620d635c1f4dd1998a1`.
Two files only: cce_batch_runtime.py and tests/test_master_handoff.py. Coordinator
reviewed full diff; no blocking finding in the scoped correction. Native owner
reports3 RED reproductions then selected16 GREEN on node200/nipttest; copied
JUnit was independently read:16tests/0failures/0errors/0skipped, duration7.834s.
The3 new tests cover lost response/sameUID, foreign identity rejection and absent
Job/no-second-CREATE. Existing normal, START response-loss and original-deadline
tests provide compatibility checks. Live normal/fault smoke still pending; no
global install, image rebuild or production release is represented by this PASS.

## Resumed authorization — 2026-09-27

User explicitly confirmed continuing smoke and allowing the original runtime
owner to fix only the initial-CREATE response-loss gap. This supersedes the
install-only conflict recorded below. Required correction: persist bound intent
before CREATE, preserve original deadline and validate observed Job identity/
manifest before adopting its UID. No adoption by name alone, duplicate CREATE,
fabricated success or unrelated feature work. Minimal remote regression precedes
the same two native smoke cases; no production deployment or WGS rule change.
Existing Master/profile/shared assets stay unchanged unless an actual dependency
is identified and separately scoped. Execution outcomes remain pending.

Owner's scoped correction: only native `cce_batch_runtime.py` and its existing
`tests/test_master_handoff.py`. V2 stores fsynced `MASTER_CREATE_INTENT` with
binding, frozen manifest hash and original deadline before its sole CREATE.
Re-entry with intent queries the exact Job, verifies the frozen manifest and
identity, persists the actual UID handoff and continues on that deadline. Absent
or foreign Job fails closed without another CREATE. V1 and existing handoff
replay remain unchanged. Only task-local client runtime bytes require staging;
installed0.8.7 and existing Master are not globally upgraded by this test.

## Latest checkpoint — 2026-09-27 00:22+08

**Normal smoke NOT RUN; fault injection NOT RUN; fixture incomplete.**
Owner reports a newer direct user instruction, "直接安装即可，不要做其他不必要的动作",
in a turn started2026-09-27 00:22:08+08, later than this smoke authorization.
Independent message timestamp/ID was unavailable; treat the conflict as unresolved
and stop new mutations pending user clarification, not as completion.

Actual writes reported by the owner:
- BS task evidence root
  `/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p0-native-smoke-20260927`
  containing setup-job.yaml/setup_dirs.sh;
- approved node200 task control directory stated below;
- the three necessary new SFS ancestors and the approved task child stated below;
- setup Job #1 only, no Master/Worker analysis or OBS/result-prefix write.

Setup Job last observed Running0/1. Inspected local manifest uses sleep1200s,
activeDeadlineSeconds1800, no TTL; no automatic cleanup or deletion is claimed.
Source defect in initial-CREATE response-loss reconciliation is confirmed below;
no product correction is authorized yet. Only local documentation diff checks
were run by the coordinator; no local runtime test or production action occurred.

## 2026-09-27 authorized bounded implementation

User approved the independent fixture/fault/test-configuration proposal. The
selected minimal implementation is a separate **runtime smoke deployment**, not
a new product adapter and not a tiny-input full WGS run. It must retain the same
native source bytes and Master image. A task-local policy may explicitly pin a
test producer and its isolated bootstrap/journal; the existing platform policy,
shared release assets, production code and namespace-wide behavior stay intact.
This is a separately identified test producer, not the deployed WGS prepare
producer. Do not falsify caller filenames, bypass guards or author fake WGS
prepare/terminal receipts to bridge that distinction.

Runtime owner must first prove the existing registration/submission/recovery
primitives can generate their own genuine journals under this deployment. If
that requires changing product source, stop and identify the exact call boundary.
No new UI/API/DB behavior is authorized. Keep web/automatic recovery flags off
when this native fixture does not consume them.

| Scenario | Required runtime evidence |
| --- | --- |
| Normal | Actual small input transfer, initial owner, Master/Worker success, automatic test-driver Step1–6 sequence, materialized result hash and755/644 |
| Lost CREATE response | Forward one real Master CREATE successfully, retain its actual UID, return one client-side transport error; normal native re-entry must adopt that same UID without a second CREATE and then produce genuine terminal/delivery evidence |

The fault is one-shot and scoped to the fault-run's exact Master CREATE.
No cluster network/webhook/service disruption, generic Master kill, false seal,
forced success or hidden resets of retry budgets. Record Job/Pod UIDs, native
attempt/generation and actual commands/exit statuses, with source/image pins.
If not exercised, backend automatic budget/dispatch, live Airflow scheduling,
frontend and official WGS biology remain explicitly unaccepted by this test.

Concrete owner proposal accepted: two unique runs, sequential, maximum one
Master and one Worker concurrently. Initial coordinator estimate of eight total
Jobs proved too small at static preflight: protected Step1/2/4/5/6 each require
a fresh cloud-reader, plus Master/Worker/log export and one fixture setup Job.
Owner stopped before mutation. Coordinator explicitly adjusted the cumulative
CREATE cap to20, still the same two cases, including fault re-entry helpers.
Track every name/UID; helpers serial/minimal resources; stop at the cap. Do not
bypass storage checks or reuse stale proofs to reduce the count.
Use a task-local `api_export` profile and native
completion contract for genuine small rule-generated outputs. Same-UID CREATE
reconciliation is the single fault scenario; it does not prove failed-Master
replacement, plugin fatal classification, skipping previous rule outputs or
backend automatic retry budgets. Do not synthesize failure FINAL for this case.

Proposed control root (must be checked before use):
`/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/wgs-runtime/cce-evidence/p0-native-smoke-20260927`.
Proposed isolated cloud asset root:
`/workspace/33.chenjiucheng/WGS_test/cce-evidence/p0-native-smoke-20260927`.
Live preflight disproved the assumed host SFS mapping: the candidate ordinary
NFS mounts lack the verified published marker. Use the exact PVC/PV-backed
volume in one task-only setup Job instead; never substitute ordinary NFS as
mounted storage identity. Setup writes only this new task subtree using an
approved non-root identity and755/644, never existing paths/shared releases.
OBS test project/batch components must be unique and recorded by the owner.

Pre-submit scope clarification: two unrelated active Jobs were observed; this
test must not launch, restart or alter other batches. It does not require global
namespace idleness or pausing production scheduling. Check available quota and
keep the bounded test identities/resources separate. BS10610's ordinary NFS
mount rejected the test-directory write despite reporting `rw`; use the approved
node200 writer for the same verified test root, without remount/permission changes.

## Scope

### Fault preflight result — native defect, injection NOT RUN

Coordinator and native owner independently traced `e2962a2`:
`cce_batch_runtime.py::step2` calls `_create_job_from_path` before persisting
`JOB_CREATED`. A successful server-side CREATE with a lost client response raises
before that handoff exists. Re-entry observes the Job but `_finish_master_handoff`
requires an existing schema2 handoff with the matching UID, so it rejects with
`Master handoff identity unavailable`. The CREATE helper has no reconciliation.
The recovery replacement entry has separate prerequisites and is not a valid
substitute for this initial submission case. Do not fabricate handoff/FINAL.
The planned fault run is withheld, not PASS or a live failed-test result. Normal
smoke may proceed; product correction needs an explicitly scoped follow-up.

Setup Job #1 `cce-p0-smoke-setup-20260927`, UID
`9c2889e8-2583-42e4-a24f-e849db159a84`, verified the real PVC-backed volume as
non-root10001:520 and found the official pipeline marker. The required test path
ancestors did not exist. Coordinator confirmed creating only the three necessary
0755 ancestors (`/workspace/33.chenjiucheng`, its `WGS_test`, then `cce-evidence`)
and the approved task child. No existing path ownership/mode or `/workspace/wgs`
mutation is permitted.

Normal-run delivery uses the existing export target, not a new export service:
project `P0SMOKE20260927`, batch `NORMAL01`; SFS linkage is exactly
`/workspace/wgs-obs-sync/Project_result/P0SMOKE20260927/NORMAL01` and OBS uses
the corresponding unique project/batch input and result prefixes. Check absence
before writing; stop if existing data are found, never clear/overwrite to reuse.
Pipeline/config/run test assets remain in the approved WGS_test subtree. This
resolves the export service's fixed source-root contract without changing it.
Only a scoped initial-CREATE product fix has been asked of the user separately;
no such correction is authorized or implemented at this checkpoint.

User requests isolated P0 normal/recovery acceptance, not biological WGS QC.
No BS96 action, historical-batch operation, shared release/profile mutation,
production-data change or repeated full synthetic suite.

## Fresh read-only deployment check

`ssh -o BatchMode=yes -o ConnectTimeout=12 BS10610` reached `server10610`,
user `chenjc` UID6708/GID520. The historical `current` link remains
`releases/20260912-opt-4d3d24e6`; actual mounts are authoritative.

Executed the existing inspected script:

```text
python3 /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/native-p0-20260926/verify_p0_test_readiness.py
```

Exit0: five service source/mount checks, restricted catalog RW/RO checks,
expected flags, gateway health200 and current release/receipt all passed.
Current release `wgs-4.2.2-3b1dae5`, receipt SHA256
`220c51d3499fabc0c550204bfa254d1bf993797d86d6768a5c5b10465ca0162a`.
This is readiness evidence, not a running smoke batch.

Only allowlisted non-secret backend environment values were printed:

| Flag | Actual value |
| --- | --- |
| PLATFORM_ENVIRONMENT | BS10610-Test |
| WGS_EXECUTION_ENABLED | true |
| WGS_RUNTIME_ADAPTER_ENABLED | true |
| WGS_TEST_PROJECT_ENABLED | false |
| WGS_CCE_RECOVERY_ENABLED | unset; config.py default false |
| GATK_CCE_RECOVERY_ENABLED | unset; config.py default false |

## Entry constraints

- `scripts/bs10610_wgs_phase1_smoke.py` creates placeholder text, not valid
  compressed FASTQ, and expects submit409. Do not execute it as P0 acceptance.
- Existing selected-monitor normal/recovery tests simulate external transport.
  Their earlier PASS is retained, not relabeled live-cloud acceptance.
- `scripts/wgs_runtime_gate.py::_validate_test_project` requires the disabled
  independent-test gate and exact approved test source/output identities.
- `_test_validate_prepared_config` binds the WGS release's generated config,
  including `WGS_pipe.smk` and target `all`; a tiny arbitrary Snakefile is not
  interchangeable with the current WGS release.

## Concluded gap

Native/Infra owner and QA independently confirm these entry constraints. No
existing real fault-injection command was found in the inspected platform/native
entry paths. The selected-monitor recovery test uses `seal(False)`, synthetic
TTL disappearance and replacement transport, not an actual cloud fault hook.
`scripts/cce_recovery_failure.py::collect_failure_evidence` requires fully bound,
closed pure executor submission/control failure evidence; arbitrary rule failure
or killing a Master does not provide that evidence. The generic native prepare
entry does not itself supply platform preparation receipts/trusted registration.

Thus tiny-file workflow submission plus real recovery is not immediately
available simply by generating FASTQ or opening one flag. A separately scoped
test-only fixture/entry and supported fault method are required. Do not broaden
this into shared release mutation, fake registration or weakened classifiers.
If implementing it requires product/API/runtime behavior changes, ask before
those changes. Normal WGS biological input would exercise a different scope.

No smoke batch or fault injection started; no gate enabled, immutable input,
runtime pin or success receipt changed. New result is deployment readiness PASS
only. Earlier unchanged synthetic results are retained, not rerun or relabeled.
