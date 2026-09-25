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

- [ ] Fix V01 with external deployment-managed role-scoped bootstrap, not policy
  self-authorization, EUID trust or global username/group allowlist. Permit only
  explicitly approved interpreter link targets and maintain absent-policy legacy.
- [ ] V02: exact PVC/PV read support with correct scope through existing owner.
- [ ] V04/V05: once-per-serialized-operation fresh storage proof; bounded history;
  UID-fenced cleanup reconciliation instead of false identity-change/instant-GC.
- [ ] V06: only relevant policy/binding changes invalidate this writer.
- [ ] Inspect P0 shared journal/lock/receipt/probe output creation, atomic replace,
  umask and reader Job identity; fix only root/private-mode regressions within P0.
- [ ] Minimal RED/GREEN cases for each corrected behavior and affected negatives;
  remote test identity must exercise actual validator, not bypass it. Report source
  commits, exact changed files, test command/results and artifact consumption map.

## Task 2 — platform observation and budgets

Owner: platform runtime implementer after Task1 interface is fixed. Files:
scripts/cce_recovery_workloads.py, cce_recovery_failure.py, cce_paired_runtime.py
automatic failure-evidence path, dags/cce_worker_wait.py and affected tests only;
backend polling only if existing receipt retry path needs a bounded correction.

- [ ] V03: classify transient inventory movement separately from invalid evidence;
  bounded fresh observation before final ineligibility. Do not create authority
  from missing/ambiguous proof or silently extend compute deadlines/budgets.
- [ ] V07: align finite inner/outer probe budgets and reduce duplicate historical
  queries while retaining inventory completeness, UID/owner and absence proof.
- [ ] Focused synthetic tests for same-UID completion/GC, conflicting UID and
  exhausted observation deadline, without full workflow reruns.

## Task 3 — owner rollout continuation

- [ ] Review combined corrections once; resolve consequential findings with only
  affected tests. Keep prior passing plugin/TTL evidence.
- [ ] Native owner packages only changed consumed payload; do not assume both
  Masters consume Operator-only changes. Preserve old tags/hash records.
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

- Preflight: platform4a4ed3c with previous audit docs uncommitted; nativef44619d.
  Existing isolated branches retained. Task1/Task2 share cce_paired_runtime.py,
  therefore sequence code edits rather than simultaneous ownership.
- Task1 produces unchanged public writer/monitor API with corrected deployment
  bootstrap and validation scope. Task2 consumes it; tests must not replace trust
  checks merely to admit fixtures. Task3 consumes accepted exact source/artifacts.
- No implementation or runtime acceptance is implied by this plan entry.
