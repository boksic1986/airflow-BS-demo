# Current state

Updated 2026-09-18 after backlog consolidation and the user-authorized selective
sync of three reviewed fixes from main. The test branch remains independent;
this narrow exception is not a general main synchronization.

## Repository role

- Primary test development worktree:
  `D:/pipeline/airflow-demo-worktrees/wgs-local-main-sync-20260917`.
- Primary test development branch:
  `jiucheng/test/wgs-local-main-sync-20260917`.
- Base source: `f0b07c4`; the current worktree carries the authorized fixes and
  state-document update pending local commit/push disposition.
- This is the only remote branch under `origin/jiucheng/test/*`.

## Main separation rule

The test branch and `main` are intentionally not synchronized as whole branches.
On 2026-09-18 the user explicitly approved one bounded exception: port the
functional changes and focused tests from `e7f0373`, `cb1c3fe` and `347e4ed`.
Their production release records and main-side state files were not imported.
Until the test queue is complete and the user separately approves promotion:

- do not merge, rebase or broadly backport `main` into this test branch;
- do not merge or cherry-pick this test branch into `main`;
- do not treat a newer commit, deployed production state or passing isolated
  test as promotion readiness;
- keep unfinished implementation and acceptance evidence on the test branch.

The refreshed 2026-09-18 comparison (`main=1255a06`, test base `f0b07c4`,
main-only 14, test-only 23) remains inventory evidence, not an integration
plan. All other main-only commits remain held. See
`docs/TEST_BRANCH_SYNC_HOLD_20260918.md`.

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

`TASKS.md` is the authoritative compact queue. The immediate action is to
compare and archive the eight retained dirty worktrees without changing the
primary test branch. The test validation matrix follows that hygiene pass. No
branch synchronization or production work is part of either action.

## Historical evidence

The complete pre-consolidation files are preserved with SHA-256 hashes at
`D:/pipeline/task-artifacts/airflow-test-branch-state-20260918`. Git history and
the existing release/design documents remain evidence; they are not reusable
runtime authorization or proof that every test is complete.
