# Active test-branch tasks

Updated 2026-09-18. This file tracks unresolved work for the independent test
branch `jiucheng/test/wgs-local-main-sync-20260917`. Historical tasks are
archived and are not silently reopened or marked complete.

## TEST-VALIDATION-01 — establish the real unfinished test matrix

Owner: coordinator and QA, with each component owner confirming its rows.

- [ ] Reconcile unchecked items from the archived `TASKS.md` with current code,
  current branch history and existing release/test evidence.
- [ ] Classify every still-relevant item as `implementation pending`,
  `test pending`, `operator acceptance pending`, `deferred by scope`, or
  `superseded with evidence`.
- [ ] Create one compact validation matrix containing component, exact source,
  required test, last accepted evidence, current blocker and owner.
- [ ] Run only missing focused tests after the matrix is reviewed; do not repeat
  accepted suites without a matching code change.
- [ ] After branch scope stabilizes, run one combined BS10610 acceptance with
  scanner/automatic dispatch preserved at their approved test settings.

Acceptance: every candidate for later promotion has current, source-matched test
evidence; unfinished or deferred work is explicit; no historical checkbox is
treated as complete merely because it was omitted from the compact queue.

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

## CCE-RECOVERY-01 — approved design, implementation incomplete

Owner: Workflow for adapter/runtime behavior; Airflow/Backend for state
projection; Frontend only for shared stale/monitoring display.

- [ ] Add source-level error classification and bounded runtime reconnect.
- [ ] Separate execution status from monitoring/Airflow status.
- [ ] Add the GATK adapter recovery entry with frozen identity and idempotency.
- [ ] Add shared stale/monitoring display and focused BS10610 tests.

Spec:
`docs/superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md`.
This task does not authorize actual task recovery, automatic Master replacement,
whole-workflow retry, Local/SGE changes, Step7 cleanup or production deployment.

## TEST-ACCEPTANCE-01 — operator-facing verification incomplete

Owner: QA/Frontend.

- [ ] Perform authenticated desktop/narrow no-flicker visual acceptance for the
  current test UI when browser access and a user session are available.
- [ ] Confirm current QC headings and exact rule filtering against deployed API
  values without changing QC policy during verification.
- [ ] Record browser evidence or a precise blocker. Component tests do not
  substitute for this unclaimed visual check.

## TEST-LINEAGE-SYNC-01 — test contains current main and production

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

- Any test-to-main promotion or production deployment. The approved direction
  in this task is main/production history into test only.
- Actual WGS/GATK task recovery, batch reset, rerun or new real analysis.
- BS96 production deployment, scanner/dispatch changes or database mutation.
- Cleanup of offline project/results/FASTQ/sampleinfo/pending/evidence data.

Full historical state:
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`.
