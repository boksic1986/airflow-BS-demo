# P0 validation corrections and blocked rollout continuation

User authorized fixing audit V01–V07 and continuing the previously blocked step.
Additional requirement: output must not be forced to root ownership or mode0600.
This is bounded correction of existing P0, not new workflow functionality.

Spec: docs/reviews/2026-09-25-p0-validation-audit.md and
docs/13_SECURITY_AND_OPERATIONS.md non-root correction; environment authority
is docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md.

## Constraints and ownership

- Keep existing platform/native isolated branches. No main/production merge or
  deployment, existing-run change, workflow-core change, new service/Compose,
  sudo/chown, new live canary, or plugin rebuild.
- User roles: chenjc deployment, ctapa analysis, chenjx WGS maintainer; live UIDs
  and access must be checked, not inferred from these labels.
- Native/Infra owner owns native source, affected artifacts and the agreed
  nipttest continuation; coordinator does not perform wheel/Master operations.
- Output directories must remain traversable and writable for intended runtime
  collaborators using approved group/default ACLs. Shared non-secret files must
  retain the needed group/ACL access through atomic replacement. Do not force
  root ownership or0600/0700 on shared output. Secrets stay owner-only; do not
  relax credentials or blanket chmod existing directories.
- Preserve exact identity/attempt/generation/UID, lock, pin, immutable CCE input,
  complete terminal evidence, bounded retry and default-off protections.
- Local workspace is editing/Git only. Use authorized remote synthetic testing;
  no full suite reruns, redundant image/TTL tests or unapproved Docker Compose.
- Environment/permission failure: stop the affected operation and report; never
  route around it. Installation uses nipttest, not WGS; capture exact rollback
  first, no Python/dependency upgrades. Shared write authorization must be
  confirmed against the exact plan before mutation.

## Task 1 — native/paired entry corrections

Owner: existing huawei-cloude native/Infra task. Files: native
src/cce_pipeline/assets/cce_writer_guard.py and cce_batch_runtime.py; platform
scripts/cce_paired_runtime.py selector/guard integration only, plus affected tests.

- [x] Fix V01 with external deployment-managed role-scoped bootstrap, not policy
  self-authorization, EUID trust or global username/group allowlist. Permit only
  explicitly approved interpreter link targets and maintain absent-policy legacy.
- [x] V02: exact PVC/PV read support with correct scope through existing owner.
- [x] V04/V05: once-per-serialized-operation fresh storage proof; bounded history;
  UID-fenced cleanup reconciliation instead of false identity-change/instant-GC.
- [x] V06: only relevant policy/binding changes invalidate this writer.
- [x] Inspect P0 shared journal/lock/receipt/probe output creation, atomic replace,
  umask and reader Job identity; fix only root/private-mode regressions within P0.
- [x] Minimal RED/GREEN cases for each corrected behavior and affected negatives;
  remote test identity must exercise actual validator, not bypass it. Report source
  commits, exact changed files, test command/results and artifact consumption map.

## Task 2 — platform observation and budgets

Owner: platform runtime implementer after Task1 interface is fixed. Files:
scripts/cce_recovery_workloads.py, cce_recovery_failure.py, cce_paired_runtime.py
automatic failure-evidence path, dags/cce_worker_wait.py and affected tests only;
backend polling only if existing receipt retry path needs a bounded correction.

- [x] V03: classify transient inventory movement separately from invalid evidence;
  bounded fresh observation before final ineligibility. Do not create authority
  from missing/ambiguous proof or silently extend compute deadlines/budgets.
- Implementation boundary: at most three complete workload observations for
  typed same-UID movement; each starts from fresh lists. The original absolute
  compute deadline comes from `deadline_epoch(payload)` and hashed registered
  `cce_recovery_deadline`, not the native Master handoff deadline. Conflicting
  UID/owner, pagination and absent-without-terminal remain immediate refusal.
- [x] V07: align finite inner/outer probe budgets and reduce duplicate historical
  queries while retaining inventory completeness, UID/owner and absence proof.
- Keep direct workload probe budget120s; outer Worker SSH is min(150s, remaining
  persisted worker_wait_deadline). Present Workers may use the complete validated
  Job LIST; missing names still require exact GET, and each bound Job retains a
  job-name Pod LIST to detect residual/unlabelled Pods. Late results reject.
  The six-argument restricted command is unchanged; Airflow enforces the shorter
  Worker wait deadline. Initial monitor uses existing QueryReconnect under the
  original compute deadline, not a claimed new120s wall-clock cap. No query-owner
  bypass or new state/hook API. Extremely large inventories may still exceed
  finite budgets; that must not authorize recovery with incomplete proof.
- [x] Focused synthetic tests for same-UID completion/GC, conflicting UID and
  exhausted observation deadline, without full workflow reruns.

## Task 3 — owner rollout continuation

Latest user decision: WGS-only test rollout and minimum recovery validation are
approved. Defer GATK/WES testing/entry discovery, not WGS completion. Use existing
BS10610 services, node200 WGS test gate and agreed nipttest; first establish exact
consumer/mount/active-use and rollback facts. Shared GATK helper imports may be
required by WGS's module closure but do not authorize GATK deployment or testing.
Do not repeat accepted source/TTL suites or activate global automatic recovery.

Preflight exposed divergent current test releaseae416fa versus P0fdace86:
old backend lacks P0 APIs, but direct replacement removes newer maintenance/
transfer display fixes. Environment writes are held. Proposed prerequisite is
bounded integration preserving both sets of accepted changes, not new recovery
functionality or a separate WGS-only API implementation; await user direction.

- [x] Review combined corrections once; resolve consequential findings with only
  affected tests. Keep prior passing plugin/TTL evidence.
- [x] Native owner packages only changed consumed payload; do not assume both
  Masters consume Operator-only changes. Preserve old tags/hash records.
  Dev3 consumption verified: both Masters copy the changed standalone assets;
  one wheel/two images built from45323e4, plugin/Worker/WGS rules unchanged.
- [ ] Fresh exact nipttest/paired test preflight and rollback inventory. Report
  installation/activation plan and any remaining authority/environment gaps.
- [ ] Resume the approved blocked step when prerequisites and scope are explicit;
  no production activation, new cloud resources, AOM charges or notifications
  inferred. Installation, activation and acceptance reported separately.

## Review focus

Approved different maintainers and interpreter symlinks; unrelated registrations;
cloud-reader plus reconnect owner; same-UID cleanup/completion races; atomic
outputs retaining intended group/default ACL access without changing secrets.

## Execution ledger

- Source acceptance: native ae90b654, paired base297bcee plus the follow-up in
  this platform commit. Three Task1 review findings and two Task2 conflict
  boundaries were fixed and individually reviewed, not a repeated whole-P0 audit.
  Native final affected111 passed; platform final affected34 passed/two fixture
  errors, then only those two passed after the new synthetic shared parent was
  aligned. DAG8 passed. Coordinator read original logs; native final SHA256
  877ee284ab54c18c3a3f075deb9f657b053e0bbd4c88feff7a0cc30bcc9fbee3 matched.
  Source/static review acceptance does not close Task3 deployment gates.

- Preflight: platform4a4ed3c with previous audit docs uncommitted; nativef44619d.
  Existing isolated branches retained. Task1/Task2 share cce_paired_runtime.py,
  therefore sequence code edits rather than simultaneous ownership.
- Task1 produces unchanged public writer/monitor API with corrected deployment
  bootstrap and validation scope. Task2 consumes it; tests must not replace trust
  checks merely to admit fixtures. Task3 consumes accepted exact source/artifacts.
- No implementation or runtime acceptance is implied by this plan entry.
- Permission integration finding: plugin `submission/<phase>` is a private
  live-process spool (executor claim, submission journal/checkpoint and phase
  markers), not the cross-account output contract. Native exports its bound
  final snapshot to shared `recovery-final.json`; platform/replacement Master
  consume that snapshot, not the private spool. Keep this internal spool0700/
  0600 without weakening the plugin; shared output remains2770/0660. First
  Task2 RED stopped during fixture setup after shared-mode changes reached this
  private directory. Native owner corrected the split; affected GREEN is pending.
- Task2 read-only call-chain preparation complete. Decision: retain120s inner and
  give150s outer startup/receipt allowance rather than shrinking every probe to15s;
  shrinking would make large valid histories less likely to complete. Existing
  persisted deadlines remain the upper bound; no compute retry budget increase.
- Execution refinement: Task2 may implement its independent workloads/failure/
  DAG files while the existing native owner completes Task1. Paired-runtime file
  ownership stays exclusively Task1 until an explicit handoff; Task2 only wires
  that entry after release. This reduces idle time without overlapping edits or
  changing either task's behavior, tests or final review gate.
