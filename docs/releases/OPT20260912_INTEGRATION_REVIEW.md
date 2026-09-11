# Whole-branch review — approved after fix wave1

Reviewer integration_review, e107f3b..f08d6b3. No remote runtime commands,
mutations or redundant suite runs. Two Important findings; no other blocker.

1. P1 retained private node gate does not forward new catalog algo options or
   verify effective configuration. Custom-mode disabled alone is insufficient.
   Default-off new catalog contract activation guard must be server-enforced
   and reflected in UI; preserve legacy no-override submissions. Assigned to
   original submission_opt, no owner/privategate change.
2. P2 operational deploy_test.py rollback restored services but not current
   pointer. Root fix validates pointer old/candidate, verifies predecessor
   affected image/source mounts and health, then atomically restores pointer.
   Only7protectedserviceIDs unchanged; no data deletion. Scoped rereview pending.

No cutover before these findings close. Task-specific code reviews remain
accepted; final fix wave must not reopen unrelated code or repeat broad suites.

Scoped final rereview:2addressed,0open,0newblocking. P1closed4d3d24e with
defaultoffflag + exact compatibility declaration + auditedrelease; UIread-only,
inactiveexplicitoverridesreject before creation, legacy/recovery retained.
P2closedafter pointer/image/mount/health validation andatomicrestore;
5syntheticrollback cases passed. Reviewer reran no tests and changed no files.
Approved BS10610 panel-only deployment, not owner/runtime/production activation.
