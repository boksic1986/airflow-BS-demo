# Current state

## 2026-09-23 actual plugin candidate contract accepted (not end-to-end)

Verified plugin0d606489 clean worktree and candidate wheel SHA256. Original
pipeline=synthetic fixture was not relaxed into the WGS/GATK allowlist; producer
owner regenerated both adapters' fixtures from the same wheel. Four opt-in
consumer checks passed0.08s on BS10610: candidate alone rejects; actual producer
candidate plus an explicitly synthetic terminal matches the draft contract.
Input bytes are hash-pinned. No runtime seal or live recovery acceptance implied.
No plugin-suite rerun, package install, shared deploy or automatic enablement.
Fresh read-only test DB snapshot still had GATK_20260922_112207_23AD29 running
Step1 upload; only own isolated candidate and network-none container were used.
Next: trusted runtime terminal writer and adapter binding/dispatch/callback fences.

## 2026-09-23 P0 internal reservation bridge and WGS manual fence

Implemented current Master-submit/Step3-monitor lineage binding to the existing
reader, evidence validator and reservation budget.22 focused WGS/GATK synthetic
checks passed (1.04s). Added the WGS resume-stage guard against unfinished
automatic recovery; RED reproduced bypass, GREEN8 checks passed (1.17s).
Tests ran only in the BS10610 isolated network-none cached-image candidate.
No shared service, database, live task, BS96 or main/production change.

The proposed trusted binding fields have no adapter writer/caller yet. Producer
source now exists in its independent worktree but no final producer fixture or
terminal-wrapper acceptance was supplied. Automatic recovery remains unwired/off.
Next: actual producer/wrapper binding, reservation dispatch and remaining control/
callback fences; CR-01–05 are not complete. No repeated unchanged helper suites.

## P0 next slice: controlled reader complete, producer integration pending

Added `cce_recovery_reader.py`;26 focused checks passed on BS10610 in the same
network-none read-only synthetic container. Only the new test file ran. No public
route, adapter, auto policy, recovery dispatch or service deploy changed.
Coordinator reports upload gate released; before any future service mutation,
recheck active runs/mounts and coordinate Step7. Test gate release is not approval
to include P1 pause/delete or production work. Plugin owner continues actual
producer implementation; do not claim draft-fixture tests as producer acceptance.

Draft pure `cce_recovery_evidence` validator additionally completed: exact context
binding, candidate digest, complete terminal summary and quiescence required.
BS10610 RED then GREEN62 checks passed0.13s. This is a proposed wrapper contract,
not evidence that today's plugin/Master emits it; no runtime reader or entry wired.

## 2026-09-22 P0 isolated development released; first budget checks passed

User released code development and partial synthetic testing while BS10610's
existing upload completes. Coordinator confirmed separate candidate/no-network
containers only; shared services, jobs, leases, databases and production remain
untouched. Formal deployment and service integration still await its gate.

Implemented internal `cce_recovery_budget.py`: existing AnalysisRun row lock and
RunAction journal, two reservations per frozen attempt, 60/180s waits, immutable
deadline, replay, transaction rollback and stop/control/maintenance checks.
Both frozen policy and initialized budget are mandatory. No public route, policy
initializer or dispatch is wired: this is NOT enabled automatic recovery.
BS10610 isolated RED observed missing module; GREEN: 54 parameterized WGS/GATK
synthetic checks passed in 1.89s. SQLite checks do not prove PostgreSQL concurrent
serialization or live DAG/runtime behavior. CR-01–05 remain incomplete.
Next: bound producer consumer, shared dispatch fences and adapter/DAG integration;
coordinate Step7-owned files before modifying shared paths. See P0 ledger.

## 2026-09-22 P0 implementation prerequisite

The user approved joint plugin/Master/runtime/Airflow implementation, resolving
the external-scope hold. Producer context/failure schema was agreed with the
plugin owner, and attempt-budget tests were prepared locally but not run.
BS10610 deployment and acceptance are paused by the environment coordinator:
the choice between selective production-fix sync and full test-branch deployment
is still pending. No application implementation or passing acceptance is claimed.
See `docs/superpowers/plans/2026-09-22-p0-joint-recovery-progress.md`.
No production, real-task operation or runtime test was performed.

## 2026-09-22 redundant blanket validation removed

The user confirmed that work already developed, tested and published to
production must retain its existing acceptance evidence and must not be put
through a new branch-wide validation cycle merely because its Git history was
synchronized into test. `TEST-VALIDATION-01` is therefore closed as redundant.
The earlier missing-`S1` test is not rerun as a standalone gate; revisit it only
if a newly authorized change touches that path or it blocks that change's focused
acceptance.

The next development priority is now P0 `CCE-RECOVERY-01`: review the bounded
0918A/0919B recovery policy, then implement `CR-01` through `CR-05` with tests
scoped to those new changes. No remote test or runtime action is authorized by
this planning correction.

## 2026-09-22 completed production fixes synchronized into test

The primary test branch now includes production-completed commits `9ff67d3`
(same-batch sampleinfo import and saved Step2 reference restoration) and
`9b381eb` (the corresponding BS96 release record) through an explicit history
merge. These two commits are completed release work, not pending development,
and add no follow-up implementation task. `main` and production remain at
`9b381eb`; test retains its additional test-only history and planning documents.

No runtime environment was changed by this repository sync. The production
release evidence remains in `docs/releases/2026-09-18-sampleinfo-bs96.md`.

## 2026-09-22 prioritized development backlog refresh

The priority audit originally used test tip `e44dc3e`. Current `origin/main` and
`origin/jiucheng/release/production` both point to `9b381eb`; their two later
production-completed commits are now included in test. They must not be counted
as new development or reopened in the backlog.

The current development order is:

1. P0: review and implement the bounded CCE recovery contract (`CR-01`–`CR-05`).
2. P1: implement two-step WGS submission/editable frozen input, then run control
   on top of the reviewed CCE identity/fencing contract.
3. P2/P3: add two-source supplemental QC, then the read-only CNV plot viewer.
4. P4: operator acceptance, combined BS10610 validation, promotion planning and
   non-destructive repository hygiene after the selected scope stabilizes.

This ordering reflects recent operational evidence: 0918A/0919B recovery gaps
affect execution correctness, while the 0919B manual-preparation rollback shows
why submission side effects should move behind final confirmation. The QC change
is supplemental to existing ordinary QC, and CNV viewing is a read-only usability
feature. This planning refresh changes no application code, runtime, database,
remote environment or real task.

## 2026-09-22 CCE recovery design revision only

Follow-up user instruction authorizes submission to the pending-development
test branch. Integration retains remote cd7771b QC/CNV designs and adds only
the four recovery document changes; main/production and runtime stay untouched.
This supersedes the original no-test-merge boundary below, not the no-code gate.

User confirmed inclusion of0918A Worker-creation transport disconnect and0919B
Gatekeeper admission timeout in future automatic checkpoint recovery;0919C
missing FASTQ/input repair remains excluded. The design now proposes two
same-attempt automatic recoveries (60/180s waits), persistent budget/original
deadline, exact failed Master and inactive Worker checks, shared manual/control
fences, UID lineage, automatic downstream progression and truthful shared UI.
The0918A Step4 dispatch timeout retains query-before-replay semantics.

Only the existing connection-recovery spec and CURRENT_STATE/TASKS/HANDOFF
are changed. CR-01–05 are future work; policy details await written review.
No application code, tests, runtime/environment, real task or data changes.
Worktree: `C:/Users/11217/.codex/worktrees/cce-recovery-design-20260922/airflow-demo`;
branch `jiucheng/docs/cce-recovery-design-20260922`, based on local tracking ref
`origin/jiucheng/test/wgs-local-main-sync-20260917=9333160`. This is an isolated
documentation revision, not a primary-test/main/production merge or deployment.
The older repository/deployment observations below remain dated history.

## 2026-09-22 WGS submission simplification proposal

Documentation-only proposal in
`docs/2026-09-22-wgs-two-step-editable-sampleinfo-design.md`: two user steps,
editable per-run sampleinfo before final submit, unchanged native selection,
and narrow automatic-intake release for cancelled uncommitted manual drafts.
Airflow main9b381eb source was inspected. Current native prepare confirmation
was requested from WGS-pipeline thread01a09149-ad9d-7e92-b98a-16d9cae075e2;
its answer confirms native sampleinfo/all refuse existing files, whereas
analysis accepts a valid frozen copy. Native server HEAD ebf1f4b, script last
change9f4f359; actual production runner binding remains unverified. No production
inspection, implementation or tests.
Work branch jiucheng/docs/wgs-submission-design-20260922 is based on test9333160;
the existing0919B operations worktree and its uncommitted records are untouched.


Updated 2026-09-18 after the user authorized a complete Git lineage sync from
current main/production into the primary test branch. Test-only development
remains on the test branch; main and production are now required ancestors.

## Repository role

- Primary test development worktree:
  `D:/pipeline/airflow-demo-worktrees/wgs-local-main-sync-20260917`.
- Primary test development branch:
  `jiucheng/test/wgs-local-main-sync-20260917`.
- Pre-sync test tip: `f0b07c4`. The approved three-fix integration is committed
  as `8f062f9`; repository-state consolidation is `91060d0`.
- This is the only remote branch under `origin/jiucheng/test/*`.

## Branch relationship rule

Current `origin/main` and `origin/jiucheng/release/production` both point to
`9b381eb`. Test now includes that history, including the completed same-batch /
Step2 fix and its production release record. The branch relationship remains:

- current main and production are ancestors of the test branch;
- test may retain additional test-only implementation and evidence;
- test-to-main promotion remains a separate reviewed and authorized action;
- old worktree/patch branches are not merge sources unless separately selected.

The two former main-only commits `9ff67d3` and `9b381eb` are completed work and
must not create new development cards. Calculate divergence from live refs
because planning documentation itself advances test; do not rebase or discard
test commits.
See `docs/TEST_BRANCH_SYNC_HOLD_20260918.md` for the original decision transition.

## Consolidated development designs

The primary test branch owns the current documentation-only development queue.
Its consolidated designs include:

- Run control from `jiucheng/feature/run-control-20260918` commit `1c631b7`:
  controlled CCE pause, same-attempt checkpoint recovery and exact online
  project deletion. See
  `docs/superpowers/specs/2026-09-18-run-control.md` and `RC-01` through `RC-05`.
- WGS two-source QC from `jiucheng/docs/wgs-qc-two-source-20260918` commit
  `53fc860`: required ordinary `QCstat.tsv` plus conditional source-qualified
  `multi.QCstat.tsv` evidence for `F57J`/`UPC` samples. See
  `docs/2026-09-18-wgs-qc-two-source-contract.md` and `QC2-01` through `QC2-03`.
- WGS CNV plot viewer design: a WGS-only Run Detail tab lists selected sample
  IDs and streams one native bound `03_CNV/<sample_id>.CNV_genome.png` at a
  time. It is not implemented; no generic artifact reader, image conversion,
  workflow/QC change, test run or deployment is authorized. See
  `docs/2026-09-18-wgs-cnv-plot-viewer-design.md` and `CNV-01` through `CNV-03`.
- Bounded CCE recovery for the approved 0918A Worker-create disconnect and
  0919B Gatekeeper timeout causes, explicitly excluding 0919C input repair. See
  `docs/superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md`
  and `CR-01` through `CR-05`.
- Two-step WGS submission and revisioned editable frozen sampleinfo, with final
  submit before analysis side effects. See
  `docs/2026-09-22-wgs-two-step-editable-sampleinfo-design.md` and
  `SUBMIT2-01` through `SUBMIT2-04`.

These designs are documented and their implementation has not started; the
revised CCE policy still awaits review. They are proposals, not available APIs
or runtime capabilities. This consolidation did
not authorize code, schema, application tests, remote validation, deployment or
real task/data operations. Existing `CCE-RECOVERY-01` remains a separate but
prerequisite-aligned implementation track; run control must reuse its execution
versus monitoring-state contract instead of creating a competing path.

## Test environment and readiness

The target is BS10610/server10610 test. Runtime roots, gates and release
fingerprints remain governed by
`docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`. Selective-sync validation used an
isolated candidate under the BS10610 control root; no service was deployed or
restarted, no analysis was submitted and no execution gate changed.

The branch contains recorded Local/SGE integration, native execution views,
CCE log-package download, native labels, GATK phase projection and worker-child
timing work. It is not declared fully tested or ready for main. Remaining work
includes reconciling the archived open checklist against current code/evidence,
the revised CCE recovery implementation, two-step submission, run control,
two-source QC, CNV viewing, operator-facing visual acceptance and one final
combined BS10610 acceptance after the branch scope stabilizes.

## Repository hygiene

The user reprioritized repository cleanup before the validation matrix. The
2026-09-18 safe pass removed ten worktrees and fifteen local branches. Unique
branches or state-only dirty documents were bundle/patch-preserved before their
worktrees were removed.
Six nonregistered legacy directories and nineteen loose packages were moved to
`D:/pipeline/task-artifacts/airflow-repo-hygiene-20260918` rather than deleted.

Eight dirty worktrees remain registered and protected, including the primary
test worktree. Their content must be triaged before any further removal. See
`docs/REPOSITORY_HYGIENE_20260918.md`.

## Open work

`TASKS.md` is the authoritative compact queue. Continue the remaining dirty-
worktree triage and test validation matrix; begin any documented development
track only after a separate implementation instruction. No production
deployment or live data operation is authorized.

## Historical evidence

The complete pre-consolidation files are preserved with SHA-256 hashes at
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`. Git history and
the existing release/design documents remain evidence; they are not reusable
runtime authorization or proof that every test is complete.
