# 2026-10-03 repository integration and cleanup

## Current authorization and owners

The human requests commit/merge/push of completed work, then cleanup of unused
branches/worktrees. This authorizes Git management, not deployment, installation,
batch recovery, clinical-data deletion or implementing pending features.

| Repository | Requested target | Sole product Git owner |
| --- | --- | --- |
| WGS | `dev_CJC_4.2.3_cloud` | WGS-pipeline |
| cce-pipeline | `main` | WGS-cloud-plugins |
| k8s plugin | `main` | WGS-cloud-plugins |
| Airflow | `main`, existing production and test branches | airflow-agent |

Coordinator preserves its mixed old source edits and only commits named
documentation. Its worktree now uses `jiucheng/docs/coordination-snapshot-20261003`,
freeing the actual test branch for the Airflow owner. Never merge this old
product tree wholesale over the accepted current implementation.

## Integration acceptance

- Record actual repositories, target names, source/target SHAs and normal push
  readback. Reuse prior runtime acceptance; do not claim a new test or deployment.
- Preserve target-specific configuration and independent unfinished commits.
- Pending QC4.2.x, compact Submit Step2, merge prepare and delivery controls remain
  pending; documentation is not their implementation. D-test1 recovery is complete.
- Update current state with the integrated result and point to original release
  evidence. Long historical cards are audit records, not a queue to replay.

## Cleanup gate

Record exact targets before removal. Preserve main/production/test/WGS target,
active owner/coordinator worktrees, dirty trees, unique commits and any ignored
evidence/configuration not separately preserved. Prove containment in retained
targets and recheck status immediately before removal. Use App archive for
attached managed worktrees and non-forced Git removal for confirmed CLI trees.
No broad recursive delete, force branch delete or deletion of clinical resources.

Initial local candidates are not deletion results: `cce-recovery-design-20260922`,
`gatk-slot-retry`, `wgs-submission-design` are clean with no ignored files. Other
clean trees with ignored `.codex-runtime`/`.superpowers` remain protected until
their contents are preserved. Actual removals and archive IDs must be appended.

### Exact authorized cleanup targets (before action)

Fresh local checks: every HEAD below is contained in main, production and test;
tracked/untracked status and ignored inventory are empty. Current owner routes
do not use them; their completed design/fix history is retained in target Git.
Authorization is the human's unused branch/worktree cleanup request, not data cleanup.

| Workspace | Branch | HEAD | Method |
| --- | --- | --- | --- |
| `C:/Users/11217/.codex/worktrees/cce-recovery-design-20260922/airflow-demo` | `jiucheng/docs/cce-recovery-design-20260922` | `0e5ea914e179eb0ec565f93704d7358c1def6891` | App archive, then safe local branch deletion |
| `C:/Users/11217/.codex/worktrees/gatk-slot-retry/airflow-demo` | `jiucheng/fix/gatk-slot-retry-20260923` | `43cd0c51a0ff44cc368579a397ba5ddb5ebc611a` | Non-forced Git worktree removal, safe local branch deletion |
| `D:/pipeline/airflow-demo-worktrees/wgs-submission-design-20260922` | `jiucheng/docs/wgs-submission-design-20260922` | `e44dc3efa7e0d87dd631cb674919434dae17a451` | Non-forced Git worktree removal, safe local branch deletion |

These are code workspaces, not clinical resources. No batch directory, FASTQ,
runtime evidence, database, release artifact or protected target branch is a target.
If final checks or removal refuse, retain the workspace; no force fallback.

## Handoff simplification candidates (do not delete automatically)

- Old UE-01-only/"not implemented" headers: superseded by later UE delivery
  records and the current native/platform release. Keep dated provenance.
- D-test1 intermediate Step3/5 snapshots: superseded operationally by the
  2026-10-03 final Step1–6 success entry; retain failure/rollback audit evidence.
- Prior per-patch QC registration design: superseded by the human's 4.2.x family
  decision. The latest QC2 contract is authoritative; implementation is pending.
- Repeated historical status paragraphs can later become links to dated records;
  current task does not delete them or assert that historical failures disappeared.

## Results

- WGS owner reports fresh HTTP remote before/after and normal push RC0/up to
  date: `dev_CJC_4.2.3_cloud = 581f4f0c62594170b10d92988ef6c7d1ffd2c26c`.
  Completed business source is clean; nine unfinished/private docs remain untouched.
  Evidence: WGS_test/cce-evidence/wgs423-git-closeout-20261003/HANDOFF.md on BS10610.
- Native owner reports main pushed/read back at
  `96278362dae9fc412a87906f267efd13ec2c80c1`, including completed e0202c5 code
  and documentation. k8s main pushed/read back at
  `43e4a6cf74c48f98771c1f3828349a3de0c06c2a`; accepted source5ffcb07 was already
  included, new closeout is documentation only. No runtime install/deployment.
- Airflow integration remains in progress; record final three target refs below.
- Coordinator archived `cce-recovery-design-20260922` through App; archived
  artifact `01a10215-968d-70b2-844e-c1bbd3174caa` is visible and path removed.
  Its local branch was safely deleted; original commit remains in retained refs
  and the App archive supports restoration.
- `gatk-slot-retry` and `wgs-submission-design-20260922` were removed using
  non-forced Git commands; their local branches safely deleted. Fresh postcheck
  confirms absent paths/branches. Their tracked contents remain in retained target
  commits; they had no uncommitted or ignored files. No independent file backup
  was created or needed. No remote branches deleted.
- Preserve active, dirty, unique-commit and ignored-evidence trees. Native0.8.8
  transport/selected-terminal legacy differences are not fully proven replaced;
  retain the old branch rather than silently reintroduce or discard it.

## Airflow source integration checkpoint

- Owner completed source/history `e65834e` (parent `cd6f2ab`) is in main.
  Exact accepted frontend legacy Resume hunks were absorbed as `ab29e46`; this
  reused the recorded acceptance and did not change paused English candidates.
- Coordinator 26-doc whitelist `bf5f177` became `9e2a6f4`, resolving eight
  conflicts with current contracts, actual release chronology and planned-only
  QC4.2.x/compact Step2 requirements. Cleanup ledger updates `0586aec`/`e32358a`
  became `0290daa`/`75f90d3`. Canonical governance files come from `e1fe6cd`.
- The existing test target keeps `5c29d86`/`257931c` ancestry. Its F1 runtime-root
  and F3 independent monitor-timeout fixes are common P0 semantics, not private
  environment configuration. They are not equivalent to current UE paths and
  have not been approved for promotion into main/production in this task.
  Preserve them on test and flag the follow-up decision; do not restore old F2
  over the accepted strict first-Master implementation.
- No runtime tests or deployment were run. Prior test evidence is historical;
  the old P1 fixture is preserved without claiming it passes against new gates.
  Three target push/readback and final exact cleanup are pending below.
