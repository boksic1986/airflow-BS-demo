# Independent GATK selective-port review — 2026-09-12

## Scope and readiness

Reviewed the uncommitted selective GATK changes against production baseline
`8e982c9d534ff82c97ca87eba8a033f5b4135b86` in the independent production clone.
Donor identity: `4013f93414ba21e24ec5f6a101d373e0297bd66c`.
This is source inspection, not production or runtime acceptance.

Final source-review verdict: **R1-R4 resolved; no remaining new P1/P2 found in
the reviewed diff**. This is approval of the bounded code changes, not a claim
of deployment or real-workload acceptance. Initial and intermediate findings
below are retained for the review audit trail; the final checkpoint supersedes
their open status.

## Findings

### P2 R1 — failed Step1 cannot start a new generation

Location: `scripts/gatk_runtime_gate.py:397-409`, in conjunction with
`_transfer_progress_root` at lines 355-369 and
`backend/app/gatk_runtime_service.py:116-122` (initial reviewed line anchors).

The transfer-plan path includes analysis, attempt and stage but no generation.
After Step1 generation 1 creates its plan and fails, backend registration creates
generation 2 with a new execution ID. `_create_step1_transfer_plan` finds the
generation-1 plan, rejects its different execution ID, and raises before the
upload command runs. Thus the newly supported same-attempt stage retry cannot
recover an ordinary failed upload without manual evidence removal.

Required correction: preserve old evidence while giving the new generation its
own valid plan and raw records. Preserve the aggregate path consumed by the
existing observer. Regression: create a g1 plan, fail, register/start g2 and prove
the new upload can proceed without deleting the g1 artifacts; same-generation
replay remains idempotent.

### P2 R2 — raw transfer rows can be relabeled as current-generation evidence

Location: `scripts/gatk_runtime_gate.py:449-470` and lines 531-539
(initial reviewed line anchors).

The new aggregator accepts v1 rows using analysis/attempt/stage/file key only,
then stamps the resulting v2 aggregate with the current execution ID,
generation and request hash. A foreign-generation or foreign-request row in the
shared stage spool is therefore promoted into apparently current evidence.
An old success row can show 100% upload for the current execution. Backend
validation cannot recover the lost provenance after this relabeling.

Required correction: fence raw records by producer-supported identity, or use
a generation-isolated raw spool if the upstream v1 producer does not emit those
fields. Do not merely loosen the existing-plan check from R1. Regressions must
cover old-generation, wrong-execution and wrong-request evidence as supported
by the producer contract, and verify unchanged observer discovery of the
stage-level aggregate. This finding concerns progress correctness; it does not
claim that an old progress row alone causes Step2 submission.

## Other review observations

- Shared `main.py` changes are limited to the GATK import, request model and
  internal-token-protected terminal endpoint. Registry changes add only the
  GATK progress projector and its adapter hook. No WGS execution logic or WGS
  tests were included in the inspected code diff.
- The explicit unrestricted input setting matches the approved business-root
  policy change; restricted remains the default and invalid values fail closed.
  Owner-bound preview, fingerprints, source structure and frozen resolved input
  authority remain. Actual read-only host/container visibility requires the
  coordinator's deployment validation; source inspection cannot prove it.
- Result naming is constrained by the frozen source project plus `_GATK`, with
  containment under configured delivery root and fallback for legacy requests.
- DAG failure reporting is internal-token-protected and attempt-scoped. The
  all-done release task now propagates upstream failure rather than hiding it.
  The callback remains best-effort; this is not a guarantee of reconciliation
  during an unavailable backend.
- Optional `docker-compose.gatk.yaml` adds no ports, declares input visibility
  read-only, and defaults execution off. It must be rendered with the actual
  environment's verified base Compose: private SSH mounts, other inherited
  overlapping mounts, worker identity, pool availability and node runner are
  deployment prerequisites, not established by this review.
- The three broader WGS failures listed in the port report are reported
  baseline exclusions, not newly reproduced or attributed to this GATK diff by
  the reviewer. Do not describe the whole regression suite as passing.

## Validation and handoff

### Final follow-up checkpoint

Reviewed the final gate changes and regression sources after the implementer
reported **21 passed** for the full GATK gate suite plus backend evidence tests
in the isolated BS10610 container. Local `git diff --check` passed again.

- R1: Step1 private plan/raw directories are generation-scoped, prior artifacts
  are retained and exact same-generation plan replay is checked.
- R2: the actual repository `wgs_obsutil_progress.py` producer does not emit the
  optional execution/generation/hash fields. The corrected aggregator accepts
  absent fields only inside its generation-private directory and rejects present
  mismatches or invalid generations. This is the selected isolation alternative
  from the initial review, not reliance on a fabricated producer schema.
- R3: Step5 retains the existing stage-level producer path, preserving the
  unchanged observer's `*/progress.json` discovery contract.
- R4: one exclusive `.progress.lock` serializes the public read/check/write;
  current request identity must match and a higher published generation cannot
  be replaced by an older one. The new test checks a late g1 against an already
  replaced g2 request while retaining g1's private evidence.

Concurrency precision: the backend request writer does not use the progress
publisher's lock. A g1 publisher that read its request just before g2 registration
can still publish a transient g1 snapshot before g2's first publication. It
cannot overwrite an already-published g2 snapshot because both publishers use
the same lock and the public generation is monotonic. The backend rejects the
failed/canceled g1 execution in the normal retry path. This is not an assertion
of a transactional lock shared between database registration and filesystem
publication; no such broader guarantee is required or claimed by this review.

Final readiness: bounded source changes accepted, subject to coordinator-owned
rendered Compose, effective permissions/mounts, installed producer/runner pins,
Airflow import/pools, services and disabled-until-approved execution gates.
No real workload or deployment acceptance was performed by the reviewer.

### First follow-up checkpoint

The first repair resolves R1 with generation-scoped plans and R2 with exact raw
execution/generation/hash checks. The implementer reports 19 isolated BS10610
gate/evidence tests passing; source review confirms the corresponding checks.
Two repair edge cases still require correction before final approval:

- **P2 R3:** `_transfer_environment` also moves Step5 into `generation-N`, but
  only Step1 publishes the legacy stage-level aggregate. The bound GATK observer
  scans `attempt_root.glob("*/progress.json")` at
  `backend/app/wgs_observer.py:2274`, so nested Step5 progress becomes invisible.
  Preserve Step5's producer/consumer path contract or add its explicit publisher.
- **P2 R4:** the stage-level Step1 aggregate is still written unconditionally.
  A late g1 aggregator can overwrite g2's public progress, making the current
  snapshot unavailable. Atomic replacement alone does not serialize competing
  writers or enforce generation authority. Require monotonic, locked publication
  (or an equivalent current-request fence) and a g2-then-late-g1 regression.

Consumer defense, verified by source: old attempts are rejected in
`_ingest_transfer_progress`; GATK `_current_execution_from_payload` checks exact
execution/generation/request hash plus accepted/running/success status. Normal
retried g1 is failed/canceled, so its late progress is rejected rather than
projected as g2. The baseline GATK query does not explicitly select the maximum
generation; do not claim an unconditional latest-generation check. R4 is still
a publication/availability defect, not proof of incorrect g2 database values.

Verdict at this checkpoint remains **changes requested** pending R3/R4 and
confirmation that the deployed upstream raw v1 producer emits the required
identity fields. No new runtime operations were performed by the reviewer.

Read the repository instructions, release boundary, latest state/task/handoff
sections and relevant runtime/DAG/security contracts. Used local Git diff,
status and targeted source/test inspection; `git diff --check` passed at the
initial review checkpoint. Two optional searches used nonexistent/glob paths
and were corrected with the real observer file; neither executed runtime code.

No SSH, pytest, Airflow import, container changes, database access, real source
preview, analysis submission, cloud operation, implementation edit or commit
was performed by this reviewer. Remote test numbers in the port report belong
to the implementer and are not independent executions by the reviewer.

Changed file: this review report only. Coordinator owns CURRENT_STATE, TASKS,
HANDOFF and deployment evidence consolidation. Runtime hostname, release,
rollback, mount and permission checks remain coordinator-owned. Rollback of
this review artifact is its removal; no runtime rollback or data deletion is
involved. Next step is the bounded R1/R2 fix, remote synthetic acceptance and
follow-up source review before declaring the candidate ready.
