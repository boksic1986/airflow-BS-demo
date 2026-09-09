# Obsolete Airflow-Demo Worktree Retirement

## Decision

The user confirmed that the old work should be deleted and specifically noted
that T193 was developed against the wrong project direction. The current local
airflow-demo workspace therefore retains only:

- `D:/pipeline/airflow-demo` as the canonical checkout of `main`;
- `D:/pipeline/airflow-demo-worktrees/T220-main-sync` for the actively changing
  `jiucheng/platform/T242-wgs-420-control-plane` task.

## Removed Work

- Discarded the T193 tracked and untracked Step7 changes with an exact path
  allowlist, switched the repository root back to `main`, and deleted the T193
  branch.
- Removed T210, T213 and T222 worktrees and deleted their old local branches.
  T210 and T222 had commits outside main; their deletion is covered by the
  user's explicit retirement decision.
- Removed the clean linked main worktree previously stored under the T249 task
  path because the repository root now owns `main` again.
- Deleted all 20 remaining unattached local task branches. None had a worktree
  or open GitHub PR.
- Deleted remote T236 after proving its only patch was equivalent to main.
- Removed empty residual directories T166, T211 and T248.

## Retained Recovery Boundaries

Remote branches with unique patches remain temporarily available. They are not
active airflow-demo development branches and should be deleted only after the
corresponding WGS/GATK/cce-pipeline owner repository confirms it contains the
needed history.

The following nonregistered directories were not treated as airflow-demo
worktrees:

- `T197-cce-pipeline-repo` is a valid clean cce-pipeline repository whose origin
  is a local bundle.
- `T244-gatk-scmc-runtime` is a valid clean GATK repository whose origin is a
  local bundle.
- T197 linked-copy remnants, T146/T214/T227 file-lock remnants and `T220 rectify`
  require a separate disk-only review.

## Safety

No remote host, Docker service, SFS, OBS, database, workflow, original data or
project result was touched. The only discarded source changes were in the four
local worktrees explicitly retired by the user. T242 remained untouched while
its dirty-file count continued to change during the audit, confirming it is
active work.
