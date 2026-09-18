# Current state

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
`1255a06`. The user explicitly authorized merging that complete history into
the primary test branch after committing the three reviewed fix ports. The
resulting invariant is:

- main and production must be ancestors of the test branch;
- test may retain additional test-only implementation and evidence;
- test-to-main promotion remains a separate reviewed and authorized action;
- old worktree/patch branches are not merge sources unless separately selected.

The historical `14` main-only / `23` test-only divergence is closed by a merge,
not by rebasing or discarding test commits. See
`docs/TEST_BRANCH_SYNC_HOLD_20260918.md` for the decision transition.

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
the deferred CCE recovery implementation, operator-facing visual acceptance and
one final combined BS10610 acceptance after the branch scope stabilizes.

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

`TASKS.md` is the authoritative compact queue. After verifying and pushing the
lineage merge, compare/archive the remaining old dirty worktrees and continue
the test validation matrix. No production deployment is authorized.

## Historical evidence

The complete pre-consolidation files are preserved with SHA-256 hashes at
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`. Git history and
the existing release/design documents remain evidence; they are not reusable
runtime authorization or proof that every test is complete.
