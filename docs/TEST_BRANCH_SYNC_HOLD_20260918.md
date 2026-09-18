# Test branch synchronization hold — 2026-09-18

## Decision

`jiucheng/test/wgs-local-main-sync-20260917` is the single primary test
development branch, but it is not ready to synchronize with `main`. Some
implementation and acceptance work remains incomplete. The branch stays
independent until the test validation matrix is complete and the user separately
approves a test-to-main promotion scope.

The user approved one narrow exception on 2026-09-18: port the functional code,
tests and current API/frontend contract for `e7f0373`, `cb1c3fe` and `347e4ed`.
This was adapted onto the test branch without importing main release records,
production observations or main-side `CURRENT_STATE.md`/`TASKS.md`/`HANDOFF.md`.

Outside that exception, this hold prohibits:

- merging, rebasing or broadly backporting `main` into the test branch;
- merging or cherry-picking the test branch into `main`;
- using production deployment state as test completion evidence;
- importing an old worktree branch merely because it contains unique commits.

## Inventory evidence

After the latest `git fetch --prune origin` on 2026-09-18:

- test branch: `f0b07c4`;
- `origin/main`: `1255a06`;
- merge base: `c6ac6ce66df7f1636cc82376f5b2c113ecd457ed`;
- main-only commits: 14;
- test-only commits: 23;
- remote `origin/jiucheng/test/*` branches: one, the current test branch.

The counts document divergence only. They are not a request to reduce the
divergence.

## Main-only commit disposition during the hold

| Commits | Hold disposition |
| --- | --- |
| `e7f0373` | User-authorized port completed: exact `ebf1f4b` phase inventory and regression coverage. |
| `cb1c3fe` | User-authorized port completed: ledger history receipt/project-root filtering and regression coverage. |
| `347e4ed` | User-authorized port completed and adapted: batch/sample presentation and exact Rule filters, preserving Native views and the test branch SQL query budget. |
| `0b384cc` | Equivalent GATK behavior already exists on the test branch; no action. |
| `1255a06` | Main-side WGS prepare recovery fix; held pending its own test-branch review and not imported by repository cleanup. |
| `1e512e1`, `4f4d45a`, `dfd95b3`, `dfd0b7d`, `9ed3b49`, `636324c`, `941f5cf`, `e66a2f4`, `2a73023` | Production/history/release observations; no test-branch synchronization. |

## Other branch disposition during the hold

- `jiucheng/docs/wgs-local-sge-20260915` and
  `jiucheng/feat/wgs-resume-stage-20260915` have unique commit identities, but
  their spec/plan and implementation files are already represented on the test
  branch. Do not merge them.
- `jiucheng/fix/production-panel-20260913` has 29 unique commits on an older,
  cross-subsystem baseline. Do not merge or mine it while the current validation
  scope is unresolved.
- cce-release-085, gatk-logger-release, qc-columns, recovery-20260914,
  pod-exit-evidence-race, wgs-evidence, wgs-local-sge and wgs421-production are
  already ancestors of the test branch. Do not merge them again.

These branches may be reviewed for later cleanup only after dirty-state,
recoverability and unique-work checks. This document authorizes no deletion.

## Release of the hold

The hold can be released only when all of the following are true:

1. `TEST-VALIDATION-01` identifies every still-relevant unfinished item.
2. Required implementation and focused tests are complete on the test branch.
3. Combined BS10610 acceptance is current for the exact candidate source.
4. Operator-facing checks are complete or explicitly accepted as deferred.
5. A test-to-main promotion manifest lists exact commits, exclusions, conflicts,
   test evidence and rollback.
6. The user explicitly approves that promotion scope.

Even after release, promotion direction is test to main. The three recorded
fixes are a specific exception, not precedent for automatic reverse sync.
