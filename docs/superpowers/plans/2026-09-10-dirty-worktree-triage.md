# Dirty Worktree Triage

## Goal

Continue T250 by removing worktrees whose only uncommitted content is disposable
local packaging/test artifacts, while preserving every source-bearing change and
every branch with commits not represented by `origin/main`.

## Completed Classification

The following worktrees contained only untracked local artifacts and were
removed from Git registration:

| Worktree | Dirty content | Branch action |
| --- | --- | --- |
| T146 WGS manual run | `.artifacts/` bundles, helper copies and packaged tools | merged branch deleted |
| T194 Step1-6 v2 | two `.artifacts/*.tar` source bundles | merged branch deleted |
| T203 Step1 canary | `.codex-artifacts/` bundles and deployment helpers | merged branch deleted |
| T209 execution target | two `.artifacts/*.tar.gz` test bundles | unique branch retained |
| T219 terminal sync | three root-level T219 source bundles | merged branch deleted |

Registered worktrees decreased from 11 to 6. Remote T194 and T203 branches were
also deleted after ancestry checks. No SFS, OBS, server, database, workflow or
clinical data was touched.

## Retained Source-Bearing Worktrees

| Priority | Branch/worktree | Evidence | Required disposition |
| --- | --- | --- | --- |
| P0 | `jiucheng/frontend/T193-step7-resource-ui` in repository root | 15 dirty paths; 11 modified tracked files plus Step7 UI/test and audit files | review as the likely focused Step7 UI candidate; separate unrelated T244 bundle before PR |
| P0 | `jiucheng/wgs/T213-step1-6-dispatch-lease-integration` | 19 dirty paths spanning backend, DAG, frontend, tests and docs | compare feature intent with T193 before selecting a canonical Step7 implementation |
| P1 | `jiucheng/wgs/T210-transfer-lease-lifetime` | 80 dirty paths; staged migration/API/lease work, unstaged state docs and many artifacts; branch also has one unique commit | split source changes from artifacts, audit migration ordering, then rebase and test as a dedicated PR |
| P1 | `jiucheng/platform/T242-wgs-420-control-plane` | four unique commits, two modified runtime-gate files and 13 operator scratch scripts | retain code/test changes; move reviewed reusable scripts into a scoped task or discard scratch files explicitly |
| P2 | `jiucheng/wgs/T222-prepare-handoff-v2` | two unique commits and four modified handoff/database documents | reconcile the document contract with current main, then open a docs-only PR or archive the branch |

T193 and T213 overlap on 11 dirty paths, and none of those resulting file
contents are identical. Neither worktree may be removed as a duplicate without
a functional diff and an owner decision.

## Residual Directories

Four paths are no longer registered worktrees but remain on disk after Windows
refused complete removal of caches, artifacts or locked files:

- `D:/pipeline/airflow-demo-worktrees/T146-wgs-081-manual-run`
- `D:/pipeline/airflow-demo-worktrees/T227-progress-step7-console-fix`
- `D:/pipeline/airflow-demo-worktrees/T214-t213-node97-integration`
- `D:/pipeline/airflow-demo-worktrees/T248-gatk-finalize-terminal`

They are disk-only cleanup candidates. Close holding processes and reverify each
absolute path before deletion. Their absence from `git worktree list` must be
confirmed again at deletion time.

## Next Task

Perform a read-only functional diff between T193 and T213 and choose one Step7
candidate. Do not merge either directly into main. The chosen candidate must be
rebased onto current main, have unrelated artifacts removed from its change set,
and pass the scoped backend/frontend/DAG tests on BS10610 before PR review.
