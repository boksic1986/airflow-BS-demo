# A468E9 Step2 deadline incident and recovery boundary

Task: W423-A468E9-HOURLY-20261002; owner: Airflow thread
01a0e728-4c99-71d0-87e9-987b311022c9. Snapshot:2026-10-02 07:20 onward,
Asia/Shanghai. Current operation and minimum platform repair only. This note
records the original diagnosis and the subsequent scoped authorization below.

## 2026-10-02 authorization update

Direct human message01a0fa57-9513-7c20-a09b-b100f8d2066a in coordinator
thread019fa8d1-0d81-7e92-abee-8154dd1cf0a7 says "修复后 rerun" after its
bounded initial-submit reconciliation proposal. Airflow owner directly verified
the message. The prior design-only/human hold in this historical note is
superseded for W423-A468E9-INITIAL-RECOVER: native minimum recovery branch,
thin platform consumer, affected BS10610 validation and reviewed controlled
activation/normal same-attempt Step2 continuation. All preservation and evidence
requirements below remain mandatory. No implementation/deployment/recovery
success is implied; coordinator candidate/deployment review is still required.
Other batches, permissions, inputs, deletion, Step7 and old completed scopes
remain outside this authorization. Keep the unique hourly monitor read-only
during the owned implementation so it does not dispatch duplicate work.

## Live observation

Only run WGS_20261001_210659_A468E9/20260927D-test1/current attempt1.
BS96/server96/control root/actual mounts and gates matched before diagnosis.
Node200/t640/ctapa6801:520 matched. Backend fd85593 and unified089 worker are
unchanged; deployed platform script raw SHA is fdc23a33f0d805bd923b6a31d5f70a381164f5b2a523160c621167aaf3d285ab.

- Step1 successful10/10,522508028738/522508028738bytes, ended06:48:47Shanghai.
  Execution wse_ec58be0b95c3e84d357d60e5/gen1/hash
  f0486b753e23f7a523e728a4d5df989589b6d84e9ed6c1aaae62ba573e0ef8be;
  exact native receipt ed0959d70f4d8c81ac1f8871285b5b22d7f929c59e82949c02a8061b6d476088.
- Step2 failed06:52:32Shanghai; wse_1fd307e0dd889fecc284a93a/gen1/hash
  c0bc4e601f8a8f367cd928b5138dc6ce20adacc153b01a518ed38a1106b7f5d0;
  failed receipt228a420ee742554b50fd41d591009a055e39d62f3ead5ac6b15671596d073cb2.
- Native worker stderr2374bytes/SHA
  3edcaa1b141e0ec6611cef0647e2ff77616b7563b163e7a28d0eb9572cd96bb8:
  paired.submit_registered:655 -> native guarded step2:2659 ->
  _write_master_handoff:1299 -> `Master original handoff deadline changed`.
- Master cce-master-656840c907ccbff7d8b7 was created with UID
  88dcdfa3-bbcb-4e91-aa64-f51299f3275a. Journal remains created; handoff JOB_CREATED,
  no Pod UID. Exact Job absent; exact Pod and frozen run-label Job/Pod lists empty,
  successful complete queries. No local analysis process. Selected evidence
  contains only intent/handoff; START intent/confirmation and RUN_FAILED/COMPLETE
  final proof are absent there. Absence is not native compute-final evidence.
- Directory CM cce-batch-lock-v2-1cd228d7a6f6ba224175a003cd45bef2 is OWNED by
  initial-c1e8a352e4e4a23ad54e5c3e4b021d6e/gen1/Master UID empty. Untouched.
- Airflow/platform failed; Step3–6 upstream_failed. Input upload slot release TI
  success is separate from final release_leases HTTP400. Original400 response
  body was not logged. Exact deployed guard dry reproduction returns
  `DagRun cleanup rejected: native_stage_unconfirmed`: Step2 handoff alone
  cannot prove compute stopped. No cleanup POST/direct SQL was used; current
  OBS slot holder is not independently verified or presumed retained.

## Root cause and minimum source correction

Exact native cce_batch_runtime.py SHA:
c2988621e4552f4240f3f8c2254d99be315ad1633ed51b8f712bf310acced7c7.
Native CREATE intent freezes deadline1790895698.794229 before CREATE. The
platform wrapper independently sampled time again and persisted
1790895698.8144848 in journal/handoff. Native writes the original intent
deadline after CREATE; its strict equality guard correctly rejects20.2558ms
drift. JSON serialization/type conversion is not the cause.

The candidate changes only initial wrapper deadline selection:

```python
intent = runtime._master_create_intent(selected, contract)
if intent is None:
    raise RuntimeError('initial CREATE requires a persisted native intent')
journal.update(identity=identity, state='submitting',
               deadline_epoch=intent['deadline_epoch'])
```

Native reader validates schema/binding/Job name/finite positive deadline. Journal
is still durable before CREATE; unknown outcome observes once without another
CREATE. No tolerance, extension, old evidence rewrite or native core change.
Candidate platform raw SHA:
a3b27c204772326363d43b3cddb98f9f145d704b652ca51e52969d961a4a353c.
Independent final read-only source review and coordinator acceptance passed
for candidate1c6b274; source is ready. Integration/activation and current-run
recovery remain pending separate decisions. Shared wrapper tests include GATK,
but no GATK operational task was started.

## Minimum BS10610 validation

Fresh preflight verified server10610/test control root/actual mounts, scan and
auto disabled. No service changes. A cached exact WGS Master image
sha256:8ba8858e3bf3b86caaf1821bdcebd18b4f5f6d1238067b223cd287a4a6663a67
ran Python3.11.9, non-root6708:520, `--network none`, source mounts readonly.
Native source runtime SHA matched production c2988621. Real native
persist/CREATE/handoff code ran; Kubernetes/OBS transport was synthetic. No
biological run or native implementation stub replaced the relevant code.

Selected function:
`scripts/tests/test_p02_selected_monitor.py::test_registered_initial_submission_selects_its_view`.
Test fixture aligns existing WGS canonical digest/control root, and advances
the clock20.2558ms after real native intent persistence. It requires three
deadlines identical and two executions to produce only one CREATE/START.
Negative cases remove or corrupt the actual synthetic persisted intent,
requiring zeroCREATE/START, absent submission journal and unchanged prepared
bundle bytes. Synthetic test files are separate from every real run.

Remote evidence root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/wgs-step2-deadline-20261002-0719`.
Exact reusable command is preserved in the private local
`.codex-artifacts/wgs-6c78d5-prepare-20261002/step2-test-runner.sh`:
Docker image above; PYTHONPATH=/platform:/native/src:/native/tests,
CCE_PLUGIN_SOURCE=/plugin, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1,
PYTHONDONTWRITEBYTECODE=1; pytest with `-q --tb=short -p no:cacheprovider` and
unique --basetemp/JUnit paths under this evidence root. No /tmp evidence.

| Result | Selection | Raw log SHA256 |
| --- | --- | --- |
| RED2failed with exact native deadline error | advancing_clock, WGS/GATK | b3104505521e709ebd3c909018d1cea8c95e41e2a9afc9e5dfccf43566bacbf2 |
| GREEN19passed/1intentional skip,34deselected | existing initial-submission cases plus advancing_clock | 16dd986ca41f51f772757d4f15c70cb33d6d8609d51ba03670b58dc715f5d056 |
| GREEN4passed,54deselected | actual-file missing/tampered intent | bc87a91bbe35efbc2f9a282fb1f982857644278ddfdf8fe977cc164a8be4e2f6 |

The skip is the existing GATK-specific exclusion for WGS reattach-worker entry.
Earlier environment/setup failures are preserved separately: Python3.9 plugin
typing.Self collection incompatibility; fixture requires `/platform` trust root;
old fixture WGS hashing included a now-excluded initial orchestration version.
These were not valid RED. Final RED uses the current real native source and
fails at the same lines as production. Full suites and unrelated tests not run.

## Rollout scope and rollback proposal — not executed

Before activation recheck actual host/mounts/gates and all writer consumers,
including WGS/GATK shared paired entry, trusted policies/bootstraps and current
owner identities. Preserve old immutable closure and both prior bootstrap bytes.
Current identical bootstraps are platform
`/home/ctapa/.config/airflow-common/releases/unified089-0afd253/scripts/cce-paired-deployment-v1.json`
and native `.../nipttest/lib/python3.9/site-packages/cce_pipeline/assets/cce-paired-deployment-v1.json`,
SHA9e36cdef574e2e5a3af6a0bb6d36f5989be10e7f94dfce99d04ceacb7b6452f9.
They select policy `/home/ctapa/.config/airflow-common/policies/unified089-v2.json`
and the old platform writer
`/home/ctapa/.config/airflow-common/releases/unified089-0afd253/scripts/cce_paired_runtime.py`.
Prepare a separate immutable platform closure containing this one corrected
script; regenerate exact writer path/hash attestations using the existing
operator installation mechanism. Both platform and native-side trust selectors
must agree; editing the old file in place alone is not a valid deployment.
Retain native package/image/source/profile/frozen input identities. No backend,
DAG, Compose, permission, profile/catalog, image or WGS core behavior change is
required by this platform source correction itself.

Do not switch while a trusted writer is active or ownership is ambiguous.
Rollback restores only exact previous selectors/attestations after the same
idle/owner checks; never delete journals or revert current stage evidence. Source
rollback can revert this isolated change before activation. This source fix
prevents new initial submissions; it cannot repair A468E9's old mismatched state.

## Required new decision: bounded initial-submit reconciliation, design only

Ordinary same-attempt Step2 resume-stage would reach
_reconcile_initial_intent -> _initial_job_uid and reject absent Job; created
journal cannot be promoted to confirmed. Ordinary replacement requires native
START/terminal/final snapshot, which this pre-start state lacks. No resume POST,
new generation/attempt, manual lock release or fabricated receipt was performed.

Proposed separate contract for native/coordination/human review:

1. Add an explicit initial-submission-abort evidence type, separate from compute
   FINAL and START confirmation. Never declare computation complete or started.
2. Under existing dispatcher/launch/writer serialization, validate exact frozen
   request, selected manifest, intent, journal, handoff, original UID/generation
   and both old deadline values. Preserve the mismatch as historical evidence.
   Require durable proof START_SENT was never reached; missing/ambiguous evidence
   blocks, and local marker absence alone is not sufficient authority.
3. Query exact original Job UID, associated/orphan Pods and all matching Workers
   with complete lists; verify storage/run input and all writer consumers/leases.
   Reject any active, unknown, partial or conflicting observation. No helper
   workload or lease/lock deletion is implied by diagnosis.
4. Retain every old file/input/Step1 receipt. Through the normal API register
   a same-attempt new stage generation/action and independent view/CREATE intent;
   CAS transition only the exact old pending owner, rather than deleting it.
5. New generation has its own deadline; old deadlines are immutable. Existing
   compute budget must not be reset or extended; exhausted budget blocks.
6. Verify unknown CREATE, duplicate API calls, concurrency, late old Job/Pod,
   unexpected START/Worker, changed inputs/owner and rollback behavior before
   any production activation. Then normal API recovery preserves Step1.

This is a new native recovery behavior requiring human authorization, not a
branch allowing CREATE whenever a Job disappears. Coordinator will obtain the
decision. Until then A468E9/a1 remains failed, monitoring ACTIVE, source candidate
not deployed, and Step1/all data/other runs/original5035B0 protected.
