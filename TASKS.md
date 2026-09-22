# Active test-branch tasks

## 2026-09-23 BS10610 integration gate

- [x] Reconcile stale test GATK `GATK_20260922_112207_23AD29-a1` as a
  user-cancelled Step1 run and release only its input-transfer lease.
- [x] Verify zero matching node200 processes, no Step2 execution and no other
  active BS10610 analysis; preserve all uploaded and local data.
- [ ] Allow P0 and Step7 remote integration only in separate service-ownership
  windows, with a fresh active-run and actual-mount preflight before mutation.


Updated 2026-09-22 after refreshing the authoritative test branch and
reassessing all documented development against current main/production.
Historical tasks are archived and are not silently reopened or marked complete.

## Priority and execution order

| Priority | Track | Why now / entry gate |
| --- | --- | --- |
| P0 | `CCE-RECOVERY-01` / `CR-01`–`CR-05` | Prevent monitoring/infrastructure faults from producing unsafe status or duplicate compute; this is a dependency for run control. |
| P1 | `WGS-SUBMIT2-20260922` | Reduce manual-preparation side effects and confirmation errors; verify the actual runner binding before implementation. |
| P1 | `RUN-CONTROL-20260918` | Operator safety is important, but pause/resume/delete must reuse the reviewed CCE recovery identity, budget and fencing contracts. |
| P2 | `WGS-QC-TWO-SOURCE-20260918` | Bounded supplemental QC projection; ordinary QC remains authoritative, so it follows runtime and submission safety work. |
| P3 | `WGS-CNVPLOT-20260918` | Read-only usability enhancement with no workflow or QC decision effect. |
| P4 | Acceptance, promotion and hygiene | Execute after selected implementation scope stabilizes; hygiene cannot discard unclassified worktrees. |

Do not start two tracks that edit the same Backend/Airflow contracts at once.
Within P1, finish the submission gate/frozen-input contract before beginning
run-control Backend/Airflow integration. The QC and CNV tracks are independent
only after their owner worktrees are isolated from the synchronized baseline.

## WGS-SUBMIT2-20260922 — proposal written; native source confirmed

Spec: `docs/2026-09-22-wgs-two-step-editable-sampleinfo-design.md`.
- [x] Audit approval/cancel boundaries, runtime input/hash and intake deduplication.
- [x] Design two-step confirmation and editable frozen sampleinfo input.
- [x] SUBMIT2-04: incorporate WGS owner native-code confirmation (ebf1f4b/9f4f359).
- [ ] Before implementation/release, verify actual production runner source binding.
- [ ] SUBMIT2-01: final-submit intent/gates and scoped cancelled-draft release.
- [ ] SUBMIT2-02: revisioned editing and frozen runtime input handoff.
- [ ] SUBMIT2-03: two-step frontend and focused BS10610 acceptance.
Implementation not authorized by this documentation-only request.

## TEST-VALIDATION-01 — closed as redundant

- [x] Accept existing release and production-publication evidence for work that
  was already developed, tested and deployed.
- [x] Do not create a branch-wide revalidation matrix or rerun the historical
  missing-`S1` test solely because completed history was synchronized into test.
- [x] Require each newly authorized development track to carry its own focused
  tests and BS10610 acceptance for the source it changes.

Revisit historical evidence only when a new change touches the same path, a
specific inconsistency blocks development, or the user requests a fresh audit.

## RUN-CONTROL-20260918 — design complete, implementation not started

Owner sequence: Workflow -> Backend -> Airflow -> Frontend -> QA/release owner.
Coordinate its execution-state and reconnect contract with `CCE-RECOVERY-01`;
do not build a second, conflicting recovery path.

- [x] Audit existing cancel/resume/Step7 behavior and document exact pause,
  same-attempt recovery and project-deletion semantics.
- [ ] `RC-01` — implement restricted runtime controls, exact ownership checks,
  quiescence evidence, checkpoint recovery and per-object cloud cleanup.
- [ ] `RC-02` — add the durable admin operation, cloud-first deletion journal,
  independent tombstone and scanner suppression fence.
- [ ] `RC-03` — add the dedicated control DAG and generation-fenced dispatch,
  callback and terminal-state handling.
- [ ] `RC-04` — add existing-page controls, destructive preview/confirmation,
  unsupported reasons and partial retry display.
- [ ] `RC-05` — run focused synthetic BS10610 acceptance after separate
  implementation and test authorization.

Spec: `docs/superpowers/specs/2026-09-18-run-control.md`. The task cards retain
their dependencies, exact acceptance, risks and rollback rules in that document.
No code, migration, remote validation, real task action or production activation
is authorized by the design or by this queue entry.

## WGS-QC-TWO-SOURCE-20260918 — design complete, implementation not started

Owner: Backend/QC projection first, then Frontend, with QA covering both.
This work is independent of CCE run control and may be developed separately.

- [x] Document required batch `QCstat.tsv` authority and conditional
  `multi.QCstat.tsv` WgsMetrics evidence for selected `F57J`/`UPC` samples.
- [ ] `QC2-01` — implement exact optional-artifact discovery and a separate
  rare-disease WgsMetrics projection, plus release-pinned applicability/judgment
  and synthetic fixtures.
- [ ] `QC2-02` — update the API contract and Run Detail QC presentation with
  default `常规临检` and conditional `罕见病` tags; each tag reads only its own
  batch-level source.
- [ ] `QC2-03` — verify ordinary-only, complete rare-disease and missing-
  supplemental-evidence cases without changing native QC, pending or DAG logic.

Spec: `docs/2026-09-18-wgs-qc-two-source-contract.md`. Same-named metrics from
the two sources must never overwrite, substitute for or silently validate one
another. No database migration, native workflow change or production publication
is part of the documented scope.

## WGS-CNVPLOT-20260918 — design complete, implementation not started

Owner sequence: Backend restricted file projection, then Frontend, then QA.

- [x] Confirm native per-sample `03_CNV/<sample_id>.CNV_genome.png` naming,
  image dimensions and bounded one-image-at-a-time display strategy.
- [ ] `CNV-01` — add WGS-only selected-sample list and controlled PNG streaming
  from the frozen bound result root; no generic file browser.
- [ ] `CNV-02` — add the WGS Run Detail `CNV plot` tab with left sample selector
  and one lazy-loaded right image pane.
- [ ] `CNV-03` — run synthetic authorization/availability and component tests;
  do not run or download a biological workflow.

Spec: `docs/2026-09-18-wgs-cnv-plot-viewer-design.md`. PNG remains the native
artifact; HTML/SVG redraw, eager batch preload, CNV interpretation and any
workflow/QC change are out of scope.

## CCE-RECOVERY-01 — scope expanded 2026-09-22, revised design awaiting review

Owner: Workflow for adapter/runtime behavior; Airflow/Backend for state
projection; Frontend only for shared stale/monitoring display.

- [x] Revise the design for user-approved0918A Worker creation disconnect and
  0919B Gatekeeper admission timeout; explicitly defer0919C missing-input repair.
- [x] Integrate the four-file document revision with current test-branch designs
  under explicit user submission approval; preserve QC and CNV work unchanged.
- [ ] Review revised policy defaults: at most two automatic same-attempt compute
  recoveries,60/180s waits, original deadline, persistent shared failure budget.
- [ ] CR-01: bind source-level query/Worker-create error evidence to execution
  identity; classify the two allowed causes and reject unknown/mixed failures.
- [ ] CR-02: single recovery decision owner, durable budget/action deduplication,
  user-stop fence and restart-safe accounting using existing records/transactions.
- [ ] CR-03: reuse adapter Resume with old Master/Worker quiescence checks,
  UID lineage and lost-response reconciliation; coordinate DAG/callback/lease
  fences and automatic downstream continuation; include uncertain Step4 dispatch.
- [ ] CR-04: shared Tracker/detail waiting, recovering, exhausted and stale
  evidence presentation without overwriting historical execution outcomes.
- [ ] CR-05: one focused synthetic BS10610 acceptance for changed paths, default-
  off/per-adapter activation and release/rollback record; no real analysis.

Spec:
`docs/superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md`.
Spec section8.1 maps CR-01–05 owners, dependencies and acceptance. Proposed
automatic Master replacement is limited to those two causes and all safety
guards; it is not an available capability or authorization to execute it now.
No missing-input repair, prepare/pending/config changes, whole-workflow retry,
Local/SGE, Step7, implementation, remote tests or production activation now.
Review the revised spec before the code-level execution plan/development.

## TEST-ACCEPTANCE-01 — operator-facing verification incomplete

Owner: QA/Frontend.

- [ ] Perform authenticated desktop/narrow no-flicker visual acceptance for the
  current test UI when browser access and a user session are available.
- [ ] Confirm current QC headings and exact rule filtering against deployed API
  values without changing QC policy during verification.
- [ ] Record browser evidence or a precise blocker. Component tests do not
  substitute for this unclaimed visual check.

## TEST-LINEAGE-SYNC-01 — complete

Owner: coordinator.

- [x] Record the 2026-09-18 main/test topology as inventory only.
- [x] Confirm no merge, rebase, cherry-pick or code port was performed during
  consolidation.
- [x] Port only the user-authorized fixes `e7f0373`, `cb1c3fe` and `347e4ed`,
  adapting the rule-filter query to retain the test branch SQL budget.
- [x] Validate the selective port in an isolated BS10610 candidate: backend
  focused suite 28 passed; frontend changed-scope suite 17 passed; production
  build passed.
- [x] Confirm the remaining full-frontend failure is already present at base
  `f0b07c4` (`starts stage one...` cannot find `S1`); keep it visible rather
  than attributing it to this sync.
- [x] Record the earlier hold and the later user-authorized policy change in
  `docs/TEST_BRANCH_SYNC_HOLD_20260918.md`.
- [x] Commit the three approved fix ports as `8f062f9`.
- [x] Commit the compact test state and repository hygiene record as `91060d0`.
- [x] Merge `origin/main=origin/jiucheng/release/production=1255a06` and prove
  both refs are ancestors of the resulting test tip.
- [x] Run focused backend/frontend/runtime tests on the merged source and push
  the test branch.
- [x] Integrate current `origin/main` and production `9b381eb` into test while
  preserving all test-only designs. `9ff67d3` and `9b381eb` are already released,
  completed work and require no follow-up development card.
- [x] Do not rerun sampleinfo/submission tests merely for this history sync;
  existing production acceptance remains authoritative.
- [ ] After all required testing completes, prepare a test-to-main promotion
  manifest with only validated commits and explicit omissions.
- [ ] Promote to `main` only after separate user approval and current main
  conflict review. Do not reverse-sync main as a test baseline.

## TEST-HYGIENE-01 — retire stale worktrees without losing current work

Owner: coordinator/operations.

- [x] Inventory both local Git common repositories, every registered worktree,
  dirty state and unique commits.
- [x] Remove ten worktrees; retain unique branches/bundles and patch-preserve
  state-only dirty documents before removing their worktree directories.
- [x] Delete fifteen local branches proven contained in `origin/main`; keep
  all remote branches unchanged.
- [x] Move six disk-only legacy directories and nineteen loose packages to the
  recoverable task-artifact archive instead of deleting them.
- [ ] Triage the eight retained dirty worktrees against current main and the
  primary test branch; preserve a patch/bundle before any later removal.
- [ ] Remove a retained dirty worktree only after its source-bearing changes
  have an explicit keep/archive/discard disposition. Never use force cleanup.

Inventory: `docs/REPOSITORY_HYGIENE_20260918.md`.

## Deferred and separately authorized

- Any test-to-main promotion or production deployment. This task only synchronized
  the already completed main/production history into test.
- Actual WGS/GATK task recovery, batch reset, rerun or new real analysis.
- BS96 production deployment, scanner/dispatch changes or database mutation.
- Cleanup of offline project/results/FASTQ/sampleinfo/pending/evidence data.

Full historical state:
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`.
