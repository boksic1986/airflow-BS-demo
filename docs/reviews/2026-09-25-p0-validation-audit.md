# P0 validation audit — 2026-09-25

## Scope and status

User requested source review for excessive validation and unreasonable decisions,
following the non-root deployment correction. This is a static review, not a
source fix or deployment acceptance. Platform reviewed: `4a4ed3c` (runtime
checkpoint `6f03dd6`); native reviewed: `f44619d` (runtime checkpoint `d84bace`).
Platform root: `D:/pipeline/airflow-demo-worktrees/cce-recovery-impl-20260922`.
Native root: `D:/pipeline/cce-pipeline-worktrees/p02-master-handoff-20260923`.
Below, P means a platform-relative path and N means a native-relative path.

Read-only reviewer work covered the native guard and workload observations;
coordinator traced platform callers and checked the reported source locations.
No tests, SSH, production/database access, builds, installation or permission
changes were performed. Plugin and full workflow behavior are outside this audit.

## Confirmed findings

### V01 — P1: deployment trust incorrectly requires root; approved interpreter links are also rejected

- P `scripts/cce_paired_runtime.py:19-39,53-57`;
  N `src/cce_pipeline/assets/cce_writer_guard.py:17-19,204-217`.
- Fixed UID 0, /etc policy location and every-ancestor ownership conflict with
  user-confirmed chenjc deployment, ctapa execution and chenjx WGS ownership.
  This known defect is already tracked as P0-NONROOT-ENTRY.
- Independently, `lstat` plus regular-file-only validation rejects any interpreter
  symlink, even an explicitly approved link to a trusted executable. This is a
  conditional deployment incompatibility; the actual nipttest link layout was
  not remotely inspected in this audit.
- Direction: implement the role-scoped contract in
  [security policy](../13_SECURITY_AND_OPERATIONS.md), including approved
  canonical interpreter targets. Do not substitute EUID or hardcoded usernames
  for trust, permit arbitrary symlinks, or ask for sudo/chown.

### V02 — P1: cloud-reader's valid PVC/PV reads are rejected by the recovery query allowlist

- N `src/cce_pipeline/assets/cce_writer_guard.py:43-44` calls `_kubectl_json`
  for PVC and PV. N `src/cce_pipeline/assets/cce_batch_runtime.py:105-109`
  routes these through `_recovery_query` when a monitor query owner is present.
- That query accepts only exact Job/ConfigMap or selected Job/Pod lists
  (`143-149`). P `scripts/cce_paired_runtime.py:976-979` supplies this owner.
- Result: cloud-reader + reconnect owner fails locally with `INVALID_QUERY`
  before a Kubernetes request; correcting root ownership alone is insufficient.
- Direction: add the necessary exact read-only PVC/PV queries and validate their
  respective namespace/cluster scopes, kind, name and identity. Keep the query
  owner, finite budgets and restricted transport; do not bypass storage checks.

### V03 — P1: normal workload movement can permanently remove initial automatic recovery eligibility

- P `scripts/cce_recovery_workloads.py:227-230` rejects a terminal Job reclaimed
  between LIST and GET, a Pod reclaimed between two lists, or the same bound
  Worker changing Running to Succeeded between those lists.
- Refusing to act on an unstable observation is appropriate. The defect is
  treating this transient observation as final ineligibility:
  `scripts/cce_paired_runtime.py:488-503` catches the exception and returns no
  recovery evidence; WGS/GATK monitoring exits on FAILED
  (`wgs_runtime_gate.py:2278-2281`, `gatk_runtime_gate.py:1028-1029`).
- `backend/app/cce_recovery_service.py:94-96` requires persisted evidence.
  `scripts/cce_paired_runtime.py:754-757` also requires existing evidence for the
  refresh path. The initial failure therefore requires manual intervention;
  it does not get the bounded re-observation available to an already-reserved
  waiting-worker recovery.
- Direction: distinguish inventory movement from invalid/conflicting evidence;
  allow bounded fresh observation before final eligibility is decided. Retain
  complete inventories, UID/owner binding, terminal proof for absence and fences.

### V04 — P2: one serialized monitor observation creates at least two directory probe Jobs

- P `scripts/cce_paired_runtime.py:1032-1033` validates the writer, then `1115`
  calls decorated native Step3; N `cce_writer_guard.py:291-295,314-315` validates
  again. The observer path similarly validates at P `511` and invokes Step3 at
  `548`. N paths here are under `src/cce_pipeline/assets/`.
- Each cloud validation calls `cloud_storage_identity` (`360-368`). After
  CLEANED, `119-123` creates a fresh probe token/Job, followed by CREATE, exec,
  DELETE (`143,166,195`). This is not just duplicate local hash checking.
- Probe history accumulates in one journal; `116-117` blocks above 1 MiB and no
  automatic archival path was found. No time-to-limit or live cost was measured.
- Direction: reuse fresh directory proof within the same serialized operation,
  retain required identity/lock rechecks, and bound/archive probe history. Do
  not cache mutable storage facts indefinitely across monitoring cycles.
- This does not establish repeated whole-FASTQ/BAM scans. Frozen metadata
  hashing is not equivalent to scanning biological data.

### V05 — P2: ordinary asynchronous probe deletion is classified as identity change

- N `src/cce_pipeline/assets/cce_writer_guard.py:187-200` sends fenced Foreground
  DELETE, then performs one GET; a still-present same-UID Job raises from
  `finally`, overriding successful directory observation.
- On re-entry, `103-109` rejects any deletionTimestamp, including this operation's
  own DELETE_INTENT. After disappearance, `135-139` still raises while finally
  marks CLEANED; another invocation is needed for a fresh probe.
- Result: ordinary cleanup latency causes consecutive false refusals, not a
  demonstrated permanent deadlock.
- Direction: bounded reconciliation of this exact DELETE_INTENT and a distinct
  cleanup-pending result. Keep UID/resourceVersion/spec/token fences; do not
  assume cleanup has completed or accept another object's identity.

### V06 — P2: unrelated batch registration invalidates a current writer

- N `src/cce_pipeline/assets/cce_writer_guard.py:332,360-363` snapshots and
  compares the entire policy dictionary, including every batch binding.
- If another batch is registered after writer construction, the current writer's
  next validate fails even when its own binding, pins and storage are unchanged.
  Per-directory serialization (`377-380`) does not serialize global registrations.
- This is not an immediate background kill; it needs another validate, and a
  newly constructed writer may recover. No production binding writer was found.
- Direction: revalidate global security settings and this batch's unique binding,
  not equality of unrelated registrations. Changes to this batch's authority,
  revocation, pins, storage or frozen inputs must still fail closed.

## Conditional risk, not a measured incident

### V07 — P2: nested probe deadlines conflict with serial historical queries

P `scripts/cce_recovery_workloads.py:164,186-229` performs `2N+4` sequential
queries for N historical Workers using a default 120-second probe budget.
P `dags/cce_worker_wait.py:38-39` allows at most 30 seconds for the complete SSH
call, including startup and evidence reads. A valid 30–120 second probe cannot
deliver a waiting-worker observation; retries restart it until the existing
bounded deadline. An initial >120 second probe can also fall into V03.
Final release repeats the full probe at P `cce_paired_runtime.py:948,954`.

The budgets and query count are verified in code, but actual latency and batch
sizes crossing them were not measured. Align end-to-end finite budgets and reduce
repeated identity-bound queries; neither arbitrary timeout growth nor removing
completeness/absence checks is an adequate correction.

## Checks to retain and acceptance limitations

- Same-directory mutual exclusion, attempt/generation/action/UID fencing,
  exact source pins, immutable CCE attempt input and terminal evidence remain
  necessary. This is not authorization to relax those protections.
- Trusted per-bundle registration is currently consumed from static policy;
  production registration producer was not found in the reviewed native/platform
  sources (tests write bindings manually). Unknown old bundles blocking is an
  explicit rollout boundary, not a newly discovered reason to remove registration.
- Existing fixtures replace root/path/interpreter checks or use mounted mock
  storage. Their prior passing results do not prove the real non-root,
  cloud-reader and reconnect-owner combination works.
- Next work should remain within existing P0 entry/guard/observation paths.
  Prioritize V01–V03, then V04–V06 and V07's budget alignment. Use focused
  synthetic cases on the authorized remote test environment when implementation
  is approved; no full workflow rerun is implied by this audit.

Source fixes and installation/activation acceptance remain open. Existing wheel,
image and TTL receipts remain historical evidence, not proof these defects are
resolved. No new product feature or production action is authorized here.
