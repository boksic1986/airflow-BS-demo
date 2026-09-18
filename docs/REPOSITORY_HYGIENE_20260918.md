# Repository hygiene inventory — 2026-09-18

## Scope and safety rule

This pass organized local Git worktrees, local branches and disk-only remnants.
It did not merge or rebase the primary test branch, discard an uncommitted
change, delete a remote branch, touch runtime data, or contact BS96/BS10610.

Two Git common repositories exist locally:

- canonical main checkout: `D:/pipeline/airflow-demo`;
- secondary common repository owning the primary test worktree:
  `D:/pipeline/airflow-demo-production`.

Both clean `main` checkouts now point to `1255a06`. The primary test worktree
remains at `f0b07c4` with its existing uncommitted selective-sync and state-file
changes. Updating the two main checkouts did not update the test branch.

## Completed cleanup

Registered worktrees were reduced from 20 to 10.

Five clean worktrees whose branches were ancestors of `origin/main` were
removed together with their local branches:

- `cce-release-085`;
- `qc-columns-20260917`;
- `wgs-auto-intake-20260917`;
- `production-release`;
- `wgs-resume-eta-20260915`.

Three clean worktrees with commits outside `origin/main` were removed, while
their branches were retained and backed up as Git bundles:

| Retained branch | Bundle SHA-256 |
| --- | --- |
| `jiucheng/docs/wgs-local-sge-20260915` | `E96DA1D8B9273D773BBC2788D7B3048763B53F6470C02A87E69A0738482BE81A` |
| `jiucheng/feat/wgs-resume-stage-20260915` | `A2290603EDD463623F5E4E6D0EC6D38FE6D33446226B0127888D47919B241E4E` |
| `jiucheng/ops/T263-gatk-test-output-cleanup` | `45F3C65FA20770197371C1879175429EEEC963F2122DA8545AA4FF340FEA2635` |

Nine additional unattached local branches already contained in
`origin/main` were deleted with ordinary `git branch -d`. No remote branch was
deleted.

Two worktrees whose only dirty paths were `CURRENT_STATE.md`, `TASKS.md` and
`HANDOFF.md` were patch-preserved and removed:

- `gatk-logger-release-20260917`: patch preserved; its merged local branch was
  deleted;
- `T220-main-sync`: patch and branch bundle preserved; its eight-patch T242
  branch remains local.

The hygiene pass therefore removed ten worktrees and fifteen local branches in
total.

Six nonregistered legacy directories and 19 root-level deployment/source
packages were moved out of the worktree root into the recoverable archive:

`D:/pipeline/task-artifacts/airflow-repo-hygiene-20260918`

The moved directories are T146, both T197 remnants, T214, `T220 rectify` and
T227. The T197 bundle was verified as complete before the move. File hashes and
directory counts are recorded in the archive `MANIFEST.md`.

## Retained dirty worktrees

Every remaining worktree with source, test, deployment-support or untracked
changes was preserved:

| Worktree | Branch | Dirty paths at inventory |
| --- | --- | ---: |
| `development` | `jiucheng/fix/production-panel-20260913` | 21 |
| `recovery-20260914` | `jiucheng/ops/recovery-20260914` | 13 |
| `T264-gatk-queue-diagnostic` | `jiucheng/ops/T264-test-proxy-preflight` | 4 |
| `wgs-eta-production-20260915` | `jiucheng/fix/pod-exit-evidence-race` | 9 |
| `wgs-evidence-repair-20260915` | `jiucheng/fix/wgs-evidence-20260915` | 23 |
| `wgs-local-main-sync-20260917` | `jiucheng/test/wgs-local-main-sync-20260917` | 27 |
| `wgs-local-sge-20260915` | `jiucheng/feat/wgs-local-sge-20260915` | 58 |
| `wgs421-production-20260916` | `jiucheng/release/wgs421-production-20260916` | 10 |

These are not all active branches. They are a protected review queue until
each uncommitted change set is compared with current main and the primary test
branch, then committed, archived or explicitly discarded. Worktree removal
must not use `--force`.

Second-pass content classification:

| Worktree | Current reason to retain |
| --- | --- |
| `development` | 21 source/config/test/document paths differ from both current main and test. |
| `recovery-20260914` | Recovery scripts, evidence packages and reliability documents require archive review. |
| `T264-gatk-queue-diagnostic` | Contains an untracked test-proxy deployment definition. |
| `wgs-eta-production-20260915` | Contains GATK resume source/tests plus local release artifacts. |
| `wgs-evidence-repair-20260915` | Contains backend/frontend QC and rule-display source/tests. |
| `wgs-local-main-sync-20260917` | Authoritative primary test development worktree. |
| `wgs-local-sge-20260915` | 34 changed files exactly match the primary test tree; 22 paths still differ and need semantic review before retirement. |
| `wgs421-production-20260916` | Contains release-runtime source/tests and release configuration. |

## Remaining local layout

- `D:/pipeline/airflow-demo`: clean canonical `main` at `1255a06`.
- `D:/pipeline/airflow-demo-production`: clean secondary `main` at `1255a06`.
- `D:/pipeline/airflow-demo-worktrees`: eight dirty, registered worktrees only;
  no loose package files and no nonregistered legacy directories remain.

The next hygiene pass is content triage of the eight retained dirty worktrees.
The primary test worktree remains the authoritative place for unfinished test
development; no old branch is a merge source merely because it is retained.
