# P0 Step3 recovery audit — 2026-09-27

Scope: read-only implementation review of Airflow source `744cd22e09127137a55468cad0c9f14760fb6901`, including backend, DAG, restricted gate and existing tests. Main and production point to this source locally. No runtime implementation edits, deployment, database access, batch retry or fault injection. This is not a fresh audit of the remote native/plugin repositories or installed images, and not a runtime acceptance claim.

## Subsequent P1 repair status

After the user requested "先修复P1", F1-F3 below were corrected in source and
verified using bounded BS10610 synthetic tests:34 backend,6 initial-submission
and rejection/replay cases,12 query-reconnect cases. The original findings below
describe the audited744cd22 baseline, not the repaired working tree.

F1 now uses the same configured node attempt scope as the request producer, with
separate platform results storage in the fixture. F2 reuses the original initial
CREATE journal only for a validated schema3 pending owner with successful Step1
and no previous submission; uncertain CREATE is not resent. F3 freezes and starts
the normal observation deadline even with compute recovery disabled, without
changing that authorization or resetting its budget. Historical frozen policies
without a timeout are intentionally unchanged; these are not retroactive repairs
to live requests. No native/plugin or biological workflow change was needed.

No production deployment/retry or new live cloud acceptance occurred. F4/P2 and
the additional legacy/new-attempt and cross-Master live-acceptance boundaries
remain open. Passing these regressions does not close those separate gaps.

## Findings

### F1 / P1 — WGS automatic recovery compares different directory identities

`backend/app/cce_compute_dispatch.py:88-91` compares frozen `control_workdir` with `run.workdir`. Production request creation does not make these equal:

- `wgs_platform_service.py:84-98`: platform results root / runs / analysis ID.
- `wgs_runtime_adapter.py:104-113`: node runtime root / runs / analysis ID / attempt-N.

Even with the same root, the attempt suffix differs. An otherwise eligible WGS Step3 recovery reaches `automatic frozen WGS release or directory differs` before new-stage registration/Airflow dispatch. The reservation has already consumed a budget slot; the poll handler converts this to rejected/needs_attention rather than launching recovery.

Existing dispatch coverage imports `backend/tests/test_wgs_resume_stage.py` whose fixture sets both fields to `/frozen/control`, hiding this producer/consumer mismatch. Validate the frozen node directory against its own trusted runtime scope; do not remove directory identity protection or compare it with platform results storage.

### F2 / P1 — Resumed upload cannot proceed to a first-ever Master submission

`wgs_resume_service.py:123-126` includes unfinished downstream stages in a Step1 resume; `register_recovery_stage` adds the same resume action to each. `scripts/wgs_resume.py:297-308` routes its Step2 to `resume_registered` regardless of whether any Master was ever submitted.

`scripts/cce_paired_runtime.py:560-604,810-819` requires an OWNED directory lock and a unique existing native Master handoff. A batch whose first failure occurred during upload has neither a submitted Master nor its handoff. Initial submission cannot simply be substituted by the caller either: `submit_registered:438-441` rejects requests with a resume action.

Consequently, completing a resumed Step1 can fail at Step2 before reaching analysis. This is a static path finding, not a claim that the currently uploading batch has already reached/faulted at Step2. The implementation must distinguish no submission intent, uncertain initial submission to reconcile, and confirmed old Master to observe/replace; it must not blindly CREATE a second Master.

### F3 / P1 — Monitoring reconnect is accidentally coupled to automatic compute recovery

`cce_recovery_policy.py:29-34` only produces a monitor deadline when automatic recovery is enabled. `wgs_stage_execution_service.py:43-53` therefore omits it for policy-disabled attempts. `scripts/cce_paired_runtime.py:1064-1066` disables the query owner when the deadline is absent.

In the paired Step3 path (`monitor_registered:1034-1052`), this disables both bounded query retry and the unconfirmed-observation marker. A query exception propagates to the generic failed worker; the old text-based query retry in `wgs_runtime_gate.py:2246-2262` is only reached for the non-paired path. Thus opting out of automatic replacement also removes observer resilience for new paired runs. The documented distinction between read-only reconnection and compute restart is not preserved. Use the existing original monitor timeout for observation independently of replacement authorization; do not enable compute recovery merely to repair monitoring.

### F4 / P2 — Manual Resume records can permanently block later automatic recovery

`cce_resume_dispatch.py:144-169` leaves a successfully dispatched manual `resume_stage` action queued so it can authorize downstream stages. `cce_recovery_poll.py:22-25,49-57` marks compute completion only on `cce_compute_recovery` records, not manual resume records.

When a manually resumed attempt later reaches an authoritative Step3 failure eligible for automatic recovery, `cce_recovery_budget.py:176-178` still treats the queued manual action as active and rejects the reservation. Mutual exclusion during an unresolved operation is necessary, but a historical dispatched action is not a perpetual in-flight operation. Distinguish current uncertain dispatch/active computation from confirmed terminal computation, preserving downstream authorization and the original attempt budget. Do not simply mark all queued actions successful or remove user-control fences.

## Additional compatibility boundary

`wgs_platform_service.py:275-296` legacy resume/rerun_failed increments attempt without initializing a policy/budget for that new attempt; reset_execution_dispatch_for_attempt preserves old params. Only new-run creation calls freeze_new_attempt. Step3 checks policy.attempt, so this entry does not automatically inherit working P0 recovery for its new attempt. Same-attempt Resume and new-attempt rerun must remain distinct; never reset an existing attempt's budget as a workaround. Scope/semantics should be explicitly decided before changing this path.

## Historical failure coverage

The consumer allowlist in `backend/app/cce_recovery_evidence.py:16-54,97-154` and restricted evidence producer/inventory include:

| Previous failure | Source category / present handling | Qualification |
| --- | --- | --- |
| 0918A Worker CREATE transport interruption | WORKER_CREATE_TRANSPORT | Complete bound terminal and reconciled Worker inventory required; F1 prevents ordinary WGS automatic dispatch |
| 0919B Gatekeeper admission timeout | WORKER_CREATE_ADMISSION_TIMEOUT | Not arbitrary HTTP500/403/policy denial; same dispatch limitation |
| 0921D CREATE storage RPC unavailable | WORKER_CREATE_STORAGE_RPC_UNAVAILABLE | Exact CREATE/InternalError/transient reason, not generic log matching |
| 0921B/C/E Heavy Slot Lease/Worker Pod read connection refusal | HEAVY_SLOT_API_UNAVAILABLE | Exact operation, bounded retries exhausted and terminal source attribution required |
| WGS/WES active Master but monitoring query disconnected | QueryReconnect | Observation only, no replacement; F3 leaves a policy-disabled gap |
| BackoffLimitExceeded, OOM, SIGKILL, startup before handshake, missing terminal | No unconditional replacement | Job failure alone is not root-cause or Worker-quiescence proof |
| Missing FASTQ, invalid input, checksum/permission or real biological rule failure | Manual correction and controlled resume | Intentionally not treated as transient compute failure |

TTL404 must not be interpreted as success/failure. Evidence-complete reclaimed Master replacement has a code path; missing persistent terminal/inventory still blocks it. `docs/46_JOB_TTL_CROSS_MASTER_RECOVERY_DESIGN.md` records a real cross-Master acceptance gap; this review neither closes that gap nor upgrades previous synthetic/CREATE-response-loss tests into real replacement validation. Historical bundles without new producer evidence are not automatically made compatible by updating the UI/backend.

## Verification and proposed next scope

Commands: git status/HEAD/branch checks, targeted rg/Get-Content across producer, consumer, dispatch, gate, specs and tests; no runtime test commands were executed. Non-runtime `git diff --check` used for review notes. Earlier test counts in HANDOFF are historical, not fresh validation of these findings.

Next, only if implementation is requested: fix F1–F3 first, settle F4's terminal-action lifecycle, and add producer-shaped targeted regressions for each changed boundary on the approved remote test host. No full workflow rerun or additional fault campaign is necessary just to reproduce these code-path mismatches. Native/plugin changes are not assumed necessary by this report.
