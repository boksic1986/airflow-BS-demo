# Completed repairs: main / production Git synchronization

Completed publication: atomic push to both refs succeeded at
`a9c899fb7a69e3a60ec25f7b3c3a8b5bb7257415`. Independent remote read and local
main/production/HEAD matched; checkout clean,12/12 anchors present, application
code identical to tested d774727. This final documentation receipt adds no code.

User authority: publish already completed Airflow repairs to main and production
repository, no omissions. Git-only: no service deployment, restart, CCE upgrade,
batch resume, schema/data/prepare/pending action or offline deletion.

## Exact scope audit

Remote main and jiucheng/release/production were equal at
`f241149bb0fb2217c32ada337a1ad065a9194f64`; production checkout was clean.
Candidate `d774727` is its fast-forward descendant, not a wholesale dirty-worktree
copy. This receipt accompanies normal fast-forward/atomic publication; completion
requires independent `git ls-remote` confirmation of both final refs.

| Repair | Commit | Audited candidate contains |
| --- | --- | --- |
| WGS SSH reconnect | c353ef6 | yes, already main |
| Local process timezone | 76d58d5 | yes, already main |
| Shared Tracker/detail transfer progress | 33598aa | yes, already main |
| Sample-aligned pending ledger | 0860412 | yes, already main |
| Restart projection, audited phases/group UI | 3091b2c | yes, already main |
| GATK recovery/Step7/Sample | 0436dce | yes, already main |
| GATK download progress | b841d2a | yes, already main |
| Linear WGS Step4/6 ETA | f2e0957 | yes, new |
| Same-attempt resume_stage API/DAG/runtime/UI | ead029f | yes, new |
| Online-only deletion boundary | 9b49c08 | yes, new |
| Paginated incomplete submission summaries | 9ace7b7 | yes, new |
| Completion/QC/serialized preparation refresh | d774727 | yes, new |

All entries checked with `git merge-base --is-ancestor`; the delta contains five
commits,49files, with matching API/runtime/UI/plan/state/handoff/test documentation.
Original resume implementation7543827 was integrated/reviewed intoead029f;
do not cherry-pick it again merely because the implementation commit ID differs.

## Verification retained, not redundantly repeated

- ETA: BS10610 backend7/UI4/build, [record](2026-09-15-wgs-linear-eta.md).
- Resume: BS10610 backend4/runtime4/Airflow2/UI1/build,
  [record](2026-09-15-wgs-resume-stage.md).
- Latest slice: BS10610 backend2/UI18/build,
  [record](2026-09-15-platform-followup.md).
- `git diff --check` on the integration delta passed. Fast-forward preserves the
  tested code exactly; this receipt changes documentation only. No new full suite,
  local runtime test or production probe was needed/performed for Git publication.

## Explicitly not delivered / preserved

- CCE managed release API is a separate completed source candidate73aa0ce
  (8fb3529/994a9c2), not part of this five-commit repair delivery. It remains on
  jiucheng/backend/cce-release-085 with its tests/docs; no silent merge or runtime
  activation. Separate integration must retain its default-disabled boundary.
- CCE package52cb638/7fc78ef and wheel are owned by the cce-pipeline repository;
  no package installation or foreign-repository source copied into Airflow.
- Backend preparation minutes-long latency and34bfcbf QC policy audit remain
  unresolved. DISPLAY/RESOURCE/EXEC remainder remains in the dated platform plan.
- Dirty recovery operational records are preserved at their original paths;
  required deletion constraints and the repair plan were already carried over.
  Four untracked .superpowers/platform-followup tar files are generated test
  transfer archives, not missing source. No worktree/branch cleanup.

Production repository is `D:/pipeline/airflow-demo-production`. The running96
release remains unchanged even after Git refs advance. Future rollout needs its
own exact release/affected-service/active-task authorization. Rollback is a source
revert, never data cleanup or force-reset of the running platform.
