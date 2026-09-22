# Handoff

## 2026-09-22 development backlog refresh and priority decision

### Goal

Refresh the authoritative test-branch planning state after new CCE recovery,
WGS submission and display designs were added, then assign a dependency- and
risk-based implementation order. This is planning only.

### Current source and lineage evidence

- Fast-forwarded the clean primary test worktree from `cd7771b` to remote
  `e44dc3e`; no local change was overwritten.
- Current `origin/main` and production both equal `9b381eb` and are not ancestors
  of test. Before this planning commit,
  `git rev-list --left-right --count origin/main...HEAD` was `2 33`; the
  documentation commit only increases the test-only side.
- The two absent main commits are `9ff67d3` (same-batch import and saved-review
  fix) and `9b381eb` (its BS96 release record). They are already released work,
  not new development, but must be reviewed into the test baseline before coding.
- The separate `D:/pipeline/airflow-demo` operations worktree has three user-
  owned dirty state documents for the completed 0919B manual rollback. They were
  inspected as operational evidence and left untouched.

### Reorganized priority

1. P0 — restore main/production ancestry in test and finish
   `TEST-VALIDATION-01`, including a fresh classification of missing `S1` after
   the submission-page main fix is present.
2. P1 — `CCE-RECOVERY-01`: review the two-recovery/60–180 second policy, then
   implement `CR-01` through `CR-05`. This addresses known 0918A/0919B failure
   modes and defines the identity/fencing contract required by run control.
3. P2 — `WGS-SUBMIT2-20260922`, then `RUN-CONTROL-20260918`. Submission work
   first reduces pre-analysis side effects; run control must reuse CCE recovery
   rather than introduce a competing recovery path.
4. P3 — `WGS-QC-TWO-SOURCE-20260918`; it adds source-qualified supplemental
   evidence while preserving ordinary QC authority.
5. P4 — `WGS-CNVPLOT-20260918`; it is a bounded read-only viewer.
6. P5 — operator acceptance, combined BS10610 evidence, promotion manifest and
   protected worktree hygiene after the selected feature scope stabilizes.

No two tracks may edit the same Backend/Airflow contracts concurrently. QC/CNV
can use independent owner worktrees only after the P0 baseline is fixed.

### Modified files and checks

- `TASKS.md`: added the priority table, dependency rule, current lineage refresh
  items and missing-`S1` reclassification gate.
- `CURRENT_STATE.md`: recorded current commits/divergence, new designs and the
  priority rationale.
- `HANDOFF.md`: this entry.

Validation is limited to branch/ref inventory, task/spec link and ID checks,
the three-file Markdown whitelist and `git diff --check`. No application tests,
SSH, Docker, database, runtime, real analysis or deployment action belongs to
this planning pass.

The target of this pass is local Git documentation at source `e44dc3e`; future
runtime acceptance remains BS10610. No SSH alias/hostname fingerprint, current
or rollback release path, mount/permission check, service state, scanner gate or
dispatch setting was inspected or changed because no remote action was in scope.

### Next action, risk and rollback

Next action is the P0 reviewed main-to-test refresh, not feature implementation.
Do not assume the production runner binding for editable sampleinfo until its
future preflight. Do not enable automatic CCE recovery before policy review and
focused BS10610 synthetic evidence. Rollback of this pass is a documentation-
only revert; it does not alter runtime or data.

Open questions are whether the revised two-recovery policy is accepted, whether
missing `S1` remains after the main refresh, and which exact production runner
SHA will be the future two-step-submission release target.

## 2026-09-22 submit recovery documents to the pending-development branch

User now authorizes submitting the documentation to primary test branch
`jiucheng/test/wgs-local-main-sync-20260917`. Remote advanced from9333160 to
cd7771b with QC presentation and CNV viewer designs; preserve both unchanged.
Integrate6540982 with that tip; resolve only competing TASKS/HANDOFF insertions,
retaining both sets of entries. Delta against remote is limited to the same
four recovery documentation files. No application, main/production or runtime
changes; application tests remain inapplicable.

GitHub port22 timed out;443 worked with StrictHostKeyChecking=yes and existing
github.com HostKeyAlias after the separate443 host alias was unknown. No host
key checks disabled, credentials exposed or persistent SSH config changed.
Verify exact file scope, whitespace, no conflict markers and preserved remote
designs before a normal fast-forward push; do not force-push on remote races.

## 2026-09-22 CCE recovery redesign — documentation only

### Goal and authority

User requests a revised development design covering0918A Worker-create transport
disconnect and0919B Gatekeeper admission timeout. Missing-input repair (0919C)
is deferred. This authorizes document changes, not application implementation,
real recovery, remote validation, production deployment or branch promotion.

Native isolated worktree is based on local test tracking ref9333160; branch
`jiucheng/docs/cce-recovery-design-20260922`. Existing dirty operations worktrees
remain untouched. No dependency installation or application baseline tests:
this is Markdown-only work under the project's local-editing boundary.

### Revised scope and files

- `docs/superpowers/specs/2026-09-17-wgs-gatk-cce-connection-recovery-design.md`:
  replace blanket automatic-Master exclusion with two source-bound allowlisted
  failure classes; keep ordinary500, unknown causes, real rule errors and
  input defects excluded. Add persistent two-recovery budget,60/180s proposed
  waits, original deadline, old Worker quiescence, exact UID lineage, safe
  replay/reconciliation, user-stop priority, adapter gates and state display.
  Include0918A Step4 uncertain dispatch without blind publish replay.
- `TASKS.md`: CR-01–05 future delivery/acceptance cards; implementation unchecked.
- `CURRENT_STATE.md`: revised scope, proposal/review status and exact branch base.
- `HANDOFF.md`: this scope, evidence and handoff record.

Two/60/180 values are design defaults proposed for review, not previously
approved operational settings. Query retries remain separate from compute
recovery; both must be bounded and cannot reset silently. Resume reuses frozen
inputs/attempt/workdir and existing outputs; incomplete rules may execute again.

### Checks and intentionally unrun work

Read the current test-ref spec/task queue and bounded local resume source;
checked the design link, CR-01–05 in spec and task queue, contradictory exclusions
and exact four-file whitelist with Git diff/status. `git diff --check` passed;
`git diff --exit-code -- backend frontend dags scripts config` returned0 with
no output. These are document checks, not application validation. No
SSH/API/DB/Docker/workflow command was run.
Do not run pytest/npm/DAG import checks for this document-only delta. Future
application tests require development authorization and BS10610 isolation.

### Remaining work, risks and rollback

Written-spec review precedes a detailed execution plan and coding. Runtime
error evidence availability, existing Worker quiescence primitives, GATK
capability and atomic control fences must be demonstrated in CR-01–03; fail
closed if an old bundle cannot support them. Necessary external source/release,
image/schema/permission changes need explicit scope review, not implicit uplift.
No automatic kill of Workers, data cleanup, inputs/receipts repair or prepare.
No test/main/production merge or push is part of this document revision.
Rollback is a documentation revert only; no runtime or data state changed.

## 2026-09-18 WGS CNV plot viewer design

Documented a narrow WGS-only `CNV plot` Run Detail tab. It resolves only
selected-sample native PNGs from the frozen bound `03_CNV` directory, lists
sample IDs at left and lazily streams one image at right. The observed V4.2.1
plots are 4800x1200 PNGs at about 0.4 MiB each, so PNG is retained; HTML/SVG
redraw and eager batch preload are excluded. No code, synthetic fixture,
runtime/data operation, workflow change or deployment occurred. Future work is
`CNV-01` through `CNV-03` in the new design document.

## 2026-09-18 QC two-source presentation simplification

The approved presentation direction supersedes the prior expandable
supplemental-row idea: Run Detail QC uses default **常规临检** for batch
`QCstat.tsv` and conditional **罕见病** for batch `multi.QCstat.tsv`. The latter
is hidden when no `F57J`/`UPC` sample applies and contains only applicable
samples. This keeps identically named metrics apart without a wide table or
ordinary-row placeholders. Documentation/task cards only; no code, test,
runtime, data or deployment change.

## 2026-09-22 submission design queued for development

User authorized completing the combined development document and committing it
to the pending-development test branch. Incorporated WGS owner source evidence,
two-step final-submit boundary, editable input/revision/hash contract, automatic
intake deduplication and narrow cancellation semantics. Only four documentation
files are included. Preserve newer test-branch CCE recovery design updates;
main/production and existing operations-worktree changes are excluded.
Validation: document links, task identifiers and git diff --check only; no
application tests, server operations or deployment are necessary for this change.


## 2026-09-22 WGS two-step submission and editable sampleinfo proposal

User requested combined assessment and updated design only. New isolated docs
worktree wgs-submission-design-20260922 branches from local test9333160; main
inspection baseline9b381eb. No remote production command, source implementation,
test execution, merge or push performed. Existing0919B operational changes stay
in their original worktree. New design and CURRENT_STATE/TASKS/HANDOFF only.

Confirmed current approval2 starts analysis and can mutate pending; cancellation
works at config_review before approval, not after. Proposed final submission
defers analysis side effects until one explicit decision. Editing uses a private
working copy, revision and hash frozen before analysis, rather than modifying
an existing frozen source/receipt. Runtime already handles existing sampleinfo
with valid receipt reuse or missing-receipt archive/regeneration. Auto-dispatch
may instead be blocked by a retained manual task: narrowly release explicitly
cancelled uncommitted drafts, never all terminal tasks.

WGS-pipeline thread01a09149-ad9d-7e92-b98a-16d9cae075e2 was explicitly asked
to confirm current native source/commit, file-exists behavior and --sampleinfo
handoff effects. Its returned server-source audit is incorporated: server10610
wgs-4.2.0 HEAD ebf1f4b, prepare script last change9f4f359. Native sampleinfo/all
refuse existing files; analysis accepts valid edited copy, with updated source
hash/request for handoff. Source is not rewritten; final sampleinfo is derived.
Pending mutation precedes final directory rename, including zero-selected cases.
Actual production runner binding remains unverified; check once before rollout.
No native source edit or overwrite switch is proposed.
Document links and scope checked locally; no runtime test is appropriate for
this proposal. Rollback removes this proposal only, without service/data effects.


## 2026-09-18 consolidate new development documents into the primary test branch

### Goal and source selection

Make the primary test branch the single authoritative place for current planned
development. The two Git common repositories and their worktrees/refs were
inventoried after a remote fetch. Only two commits newer than test tip `2d899e5`
were documentation-only development proposals:

- `1c631b7` on `jiucheng/feature/run-control-20260918`;
- `53fc860` on `jiucheng/docs/wgs-qc-two-source-20260918`.

Older feature, fix, release and operations branches were not treated as new
development merely because they contain Markdown. Their historical deployment
or handoff notes remain evidence, not active queue entries.

### Consolidated content

- Added `docs/superpowers/specs/2026-09-18-run-control.md` unchanged in meaning:
  proposed CCE pause, same-attempt checkpoint recovery, exact cloud/Airflow/
  biodemo deletion, residual handling, tombstone, scanner fence and permissions.
- Added `docs/2026-09-18-wgs-qc-two-source-contract.md` unchanged in meaning:
  ordinary batch QC remains authoritative while applicable `F57J`/`UPC` samples
  receive separately labelled WgsMetrics supplemental evidence.
- Rewrote the source branches' task snippets into the current compact
  `TASKS.md`: `RC-01` through `RC-05` and `QC2-01` through `QC2-03`, with owner,
  sequence, dependency, scope and authorization boundaries.
- Updated `CURRENT_STATE.md` so both designs are visible beside the existing
  `CCE-RECOVERY-01` track without claiming any implementation or validation.

The source branches had different bases: run control was based directly on
`2d899e5`, while the QC document was based on main `1255a06`. Their full commits
and inherited state files were therefore not merged or cherry-picked. Only the
two specs and reconciled current-branch state were retained.

### Scope and validation

This was documentation and Git inventory only. No backend, frontend, DAG,
runtime, migration, application test, SSH, Docker, database, analysis, service
or production operation was performed. The designs do not register APIs, change
QC policy at runtime or authorize pause/resume/delete of a real task.

Validation covers the exact five-file documentation delta, local Markdown link
resolution, task-ID/spec consistency, source-spec comparison, `git diff --check`,
and proof that `backend`, `dags`, `scripts`, `frontend`, migrations and runtime
configuration did not change. No application test is applicable to this
documentation-only consolidation.

### Next action and rollback

Review `TEST-VALIDATION-01`, then select a documented development track under a
new implementation instruction. Coordinate run control with CCE recovery before
coding; the two-source QC work is independent. Production activation, test-to-
main promotion and live task/data actions remain separately authorized.

Rollback is a single documentation revert. The two source branches remain
available as provenance until repository hygiene separately classifies them;
this consolidation does not authorize deleting their worktrees or branches.

## 2026-09-18 test-branch backlog consolidation and synchronization hold

### Goal

Maintain one authoritative test development branch, preserve historical state
and make unfinished testing visible without synchronizing with `main`.

### Completed

- Confirmed the primary test worktree is
  `D:/pipeline/airflow-demo-worktrees/wgs-local-main-sync-20260917` on
  `jiucheng/test/wgs-local-main-sync-20260917` at `f0b07c4`.
- Refreshed origin and confirmed this is the only remote
  `origin/jiucheng/test/*` branch.
- Recorded, for inventory only, `origin/main=1e512e1`, main-only 13, test-only 23
  and merge base `c6ac6ce66df7f1636cc82376f5b2c113ecd457ed`.
- After user correction, replaced the proposed main-delta integration queue
  with `docs/TEST_BRANCH_SYNC_HOLD_20260918.md`. All main-only and legacy-branch
  changes are held while testing is incomplete.
- Replaced historical narrative in `CURRENT_STATE.md`, `TASKS.md` and this file
  with a compact snapshot, unfinished-test workflow and authorization gates.
- No merge, rebase, cherry-pick, code port, commit, push, source-code change,
  runtime action, analysis, database change or production action was performed.

### Preserved history

Original pre-consolidation files were copied to
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`:

- `CURRENT_STATE.md`: 356710 bytes,
  SHA-256 `13C1EE3C6D5CB0D7323111FBAD9E58E6F88DB0C5D08FE2CD360BA64DE99BF60E`.
- `TASKS.md`: 204039 bytes,
  SHA-256 `C5FBA92467D1D692CFE5DBB6240D36FCFB2790023D74E3A1F3A3621FD59B049C`.
- `HANDOFF.md`: 857955 bytes,
  SHA-256 `80470E265EC9AB9CF2F1F3807AD0F433FC7190817CE713D29AE60954CCA39817`.

Git history and detailed release/design records remain available. Archived
historical instructions are evidence, not current authority.

### Modified files

- `CURRENT_STATE.md`
- `TASKS.md`
- `HANDOFF.md`
- `docs/TEST_BRANCH_SYNC_HOLD_20260918.md`

### Commands and validation

- `git fetch --prune origin`: passed; refreshed the branch inventory.
- `git rev-list --left-right --count origin/main...HEAD`: `13 23`.
- Per-worktree ancestry and unique-commit inspection: completed for inventory;
  no integration performed.
- Documentation reference checks passed for the environment boundary, CCE
  recovery spec and synchronization-hold record.
- `git diff --check`: passed with exit code 0.
- Archive SHA-256 values were recomputed and match the recorded originals.
- Stale instructions to integrate/port main into the test branch were searched
  across all four changed documents and were absent.
- The compact queue has 17 intentionally open validation, implementation,
  acceptance, future-promotion and hygiene items.

No backend, frontend, DAG or workflow test is claimed by this documentation-
only consolidation. No BS10610 live preflight was run because no runtime action
was requested.

### Next action

Execute `TEST-VALIDATION-01`: reconcile archived unchecked items with current
source and evidence, then produce the unfinished-test matrix. Do not synchronize
with `main` while building or executing that matrix.

### Risks and rollback

- The test branch is not promotion-ready merely because prior focused tests or
  deployments exist; evidence must match the final candidate source.
- Counts are tied to the recorded commits and may change after future fetches,
  but divergence is not itself a defect to repair.
- Restore the three archived state files or revert this documentation change to
  undo the consolidation. No runtime/data rollback is needed.

## 2026-09-18 selective main-fix port to the test branch

### Goal

Apply only the three fixes explicitly approved by the user—`e7f0373`,
`cb1c3fe` and `347e4ed`—without synchronizing the rest of main or overwriting
test-branch Native/Local/SGE work.

### Completed

- Registered the audited `wgs-4.2.1-ebf1f4b` rule-to-phase inventory while
  retaining Unknown behavior for unreviewed releases.
- Made file-ledger reconciliation wait for an unpublished receipt and ignore a
  self-consistent foreign project root without deleting imported history.
- Added authenticated run-detail sample fields only for participating Sample
  IDs; global sample/QC/workspace projections remain privacy-safe.
- Added whole-attempt exact Rule filter options and full phase choices. The
  test-branch adaptation combines summary/filter/attempt rows into one SQL
  query so the existing `<=8` query budget remains satisfied.
- Simplified WGS Overview/Samples/Ledger presentation, added searchable exact
  Sample/Family selection and removed the Files tab request. Existing Native
  execution views were preserved.
- Updated API/frontend contracts and the synchronization-hold record. Main-side
  release documents and state files were not copied.

### Validation

- Local: Python compile passed; phase policy JSON parsed; `git diff --check`
  passed.
- BS10610 isolated candidate:
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates/three-fix-sync-20260918`.
- Backend focused tests: 28 passed, 1 dependency warning.
- Frontend changed-scope tests: 17 passed.
- Frontend `npm run build`: passed; generated
  `index-D2PoeP0p.js` and `index-D4g5ndFq.css` in the isolated build image.
- Full frontend suite: 133 passed, 1 failed. The same failure reproduces on the
  pre-port `f0b07c4` baseline in the same image: `starts stage one without
  accepting runtime configuration` times out finding `S1`. It is therefore a
  pre-existing test-branch blocker, not accepted as green.

### Runtime impact and rollback

No BS10610 service, database, workflow, gate or running analysis was changed;
BS96 was not contacted. Roll back by reverting this selective local port. The
isolated candidate directory and build image contain no runtime authorization.

## 2026-09-18 local repository hygiene pass

### Goal

Remove provably stale local worktree/branch clutter while preserving the
primary test branch and every uncommitted or unique change set.

### Completed

- Refreshed both local Git common repositories and fast-forwarded only their
  clean `main` checkouts to `1255a06`; the test branch remained at `f0b07c4`.
- Reduced registered worktrees from 20 to 10. Removed five clean merged
  worktrees with their branches and three clean unique worktrees while retaining
  those branches and creating recovery bundles.
- Deleted nine additional unattached local branches proven to be ancestors of
  `origin/main`. No remote branch was deleted.
- Patch-preserved and removed two state-doc-only dirty worktrees. The merged
  GATK logger branch was deleted; the unique T242 branch and bundle were kept.
- Moved six nonregistered legacy directories and nineteen loose packages from
  the worktree root to
  `D:/pipeline/task-artifacts/airflow-repo-hygiene-20260918`.
- Preserved all eight source/test-bearing dirty worktrees. The primary test worktree retained its
  original 27 modified/untracked paths before this documentation update.

### Validation

- Both `D:/pipeline/airflow-demo` and
  `D:/pipeline/airflow-demo-production` are clean on `main` at `1255a06`.
- The remaining worktree root contains only ten registered dirty worktrees and
  no loose archive files or nonregistered legacy directories.
- Recovery bundles were created for the three removed unique worktrees and
  hashed; see `docs/REPOSITORY_HYGIENE_20260918.md` and the archive manifest.
- T197's historical bundle passed `git bundle verify` as complete before its
  broken-link disk remnants were archived.
- No source test was run because this pass changed repository organization and
  documentation only. No runtime host was contacted.

### Remaining work

Content-triage the eight retained dirty worktrees. Compare each change set with
current main and the primary test branch, preserve a patch or bundle, and obtain
an explicit keep/archive/discard disposition before removing any dirty
worktree. Then resume `TEST-VALIDATION-01`.

### Recovery

The three unique branches remain local and have standalone bundles. Moved disk
remnants and packages can be restored from the task-artifact archive. Deleted
local merged branches are recoverable from `origin/main` or reflogs. No runtime
or data rollback is required.

## 2026-09-18 main/production lineage merge into test

### Goal

Establish the user-requested relationship in which current main and production
are ancestors of the primary test branch, while preserving all test-only
commits and Native/Local/SGE adaptations.

### Completed before merge verification

- Committed the three approved fix ports as `8f062f9`.
- Committed compact state and repository hygiene records as `91060d0`.
- Confirmed live remote refs `main` and `jiucheng/release/production` both point
  to `1255a06`; no second production merge is required.
- Merged `origin/main` with explicit conflict review. Duplicate three-fix
  conflicts retain the test SQL budget, Native status choices and CCE log
  archive UI. WGS prepare-recovery source/tests from `1255a06` are included.
- Combined test and production environment/runbook observations; compact test
  state remains the current queue.

### Verification and publication

- Merge commit: `e8ce35a`; pushed to
  `origin/jiucheng/test/wgs-local-main-sync-20260917`.
- `origin/main` and `origin/jiucheng/release/production` are both ancestors;
  each reports `0` commits absent from test and test reports `26` additional
  commits at the merge tip.
- BS10610 isolated source candidate:
  `candidates/lineage-sync-e8ce35a`; no service deployment or restart.
- Existing backend Docker image, network disabled and source mounted read-only:
  the exact three-fix plus prepare-recovery set passed `36` tests.
- A broader backend set passed `94` and failed `6`. All six failing node IDs
  fail identically on first-parent baseline `91060d0` in the same image, so
  they remain pre-existing test-branch contract drift rather than merge
  regressions.
- Existing frontend build image, network disabled and candidate copied to
  tmpfs: selected tests passed `32` and failed the already recorded
  `starts stage one...`/missing `S1` case. Production build passed and emitted
  `index-D2PoeP0p.js` plus `index-D4g5ndFq.css`.
- Local checks were limited to Python compilation, policy JSON parsing and
  `git diff --check`; no local dependency environment was created.

No runtime host, analysis, database or production deployment is authorized by
this Git-only merge.
