# Handoff

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
