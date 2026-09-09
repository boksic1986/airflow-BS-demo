# Git Worktree And Branch Cleanup Plan

## Goal

Reduce local worktrees and local/remote task branches without losing uncommitted
changes or commits that are not represented by `origin/main`.

## Safety Classification

1. Preserve every worktree with tracked or untracked changes.
2. Remove a clean worktree whose HEAD is an ancestor of `origin/main`, then
   delete its local branch with ordinary `git branch -d`.
3. For a clean worktree with commits outside `origin/main`, remove only the
   worktree and retain the branch.
4. Delete an unattached local branch only after `git merge-base --is-ancestor`
   proves it is contained in `origin/main`.
5. Delete a remote task branch only when it is contained in `origin/main`, is
   not attached to a preserved dirty worktree, or its GitHub PR is confirmed
   merged.
6. Never use `git branch -D`, `git reset --hard`, `git clean -fdx`, or force
   removal of a worktree with uncommitted changes.

## Executed Result

- Merged T249 through PR 15; `origin/main` advanced to `fed0348`.
- Reduced registered worktrees from 23 to 11.
- Removed 28 local branches already contained in `origin/main`.
- Removed 17 remote task branches already contained in `origin/main` and not
  needed by a preserved dirty worktree.
- Removed seven clean worktrees with unmerged commits while retaining all seven
  branches.
- Preserved ten dirty worktrees for explicit owner review.
- Preserved every remaining branch with a unique patch relative to
  `origin/main`.

## Residual Review Queue

Three paths are no longer registered as Git worktrees but remain on disk because
Windows refused complete removal of ignored/cache files or held a file lock:

- `D:/pipeline/airflow-demo-worktrees/T227-progress-step7-console-fix`
- `D:/pipeline/airflow-demo-worktrees/T214-t213-node97-integration`
- `D:/pipeline/airflow-demo-worktrees/T248-gatk-finalize-terminal`

They contain no active Git worktree registration. Delete them only after closing
processes that may hold files and confirming the paths again. The retained
branches for T219 and T248 still preserve their unique commits.

## Next Pass

Review the ten dirty worktrees one by one with their owners. Commit and open a
PR, archive a patch, or explicitly discard each change set. After that decision,
remove the worktree and use ordinary branch deletion wherever possible.
