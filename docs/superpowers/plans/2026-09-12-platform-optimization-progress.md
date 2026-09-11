# Execution ledger — 2026-09-12-platform-optimization.md

Baseline e107f3b, clean isolated jiucheng/development/next. User execution request supersedes copied planning-only sentence; only BS10610 deployment authorized.

| Boundary | Producer / consumer | Finding |
| --- | --- | --- |
| Task1 / Task2 | submission frozen config → rule/QC release selection | Preserve release and attempt identity; task2 consumes task1 contract. |
| Task1 / Task3 | release/runtime version → resources | Configured versus observed versions separate. |
| Task2 / Task3 | workspace timing and heavy projections | Sequential implementation avoids shared-file conflicts. |
| Task1 internal | custom paths vs existing security policy | Test-only explicit root exception, production remains closed. |
| Task2 internal | inferred estimates vs true runtime | Add separate display fields; do not modify execution evidence. |
| Task3 internal | quotas vs instantaneous usage | Separate resource packages and runtime metrics. |
| Task4 internal | test acceptance vs production | No production deployment authorized. |

- Task1 implementation a5aedc9: submission_opt delivered141 backend/gate passes plus separate PostgreSQL concurrency1pass;15 scoped UI passes, TypeScript/Vite build. Independent submission_review pending; task not yet accepted/deployed.
- Task2 implementation started from d5a4e1d by monitor_opt; brief OPT20260912_TASK2_BRIEF.md. Sequential ownership excludes submission/resources; no deployment or real analysis permitted.
- Task3 pending.
- Task4 pending.

## Read-only test preflight

2026-09-12 workstation / remote UTC2026-09-11: BS10610 hostname server10610, current release20260912-gatk-81587fcb. Backend8eca1592b509, frontend e90c834e3fa6, observer add051b157d5, metrics5629edc808c8. WGS/GATK DAG imports healthy, no active runs (0 WGS histories,3 GATK histories); scan/dispatch bothfalse. Cached backend t235-232154f and Node22 lock35420d5e3ec0 present.

Backend environment BS10610-Test, UID6801/GID520. /sg2 and /bi are readonly NFS mounts. /sg2/50.ctapa/project/HWcloud/WGS_test exists2770 owner6801/group520 but os.access(W_OK)=false; no permission/mount changes performed. Alternative /mnt/biodevrwsg2/50.ctapa/... does not exist, must not substitute.

Heavy resource API returns availablefalse with null counters. Expected /data/wgs-evidence/heavy-slot-global.json is absent. Existing repository collector launcher hardcodes production node/config/output path. SFS/node numeric spools are present and current, so Heavy failure is independent of general resource collection. No production or cloud workload check yet.

Research owners (read-only): resource_research official resource-package API and quota unit; rule_qc_research event/filter/QC source tracing. Root owns environment and integration evidence. Task1 exact owner cc9bde3 caller choices are DNAscope/Haplotyper; do not advertise unsupported GATK HaplotypeCaller for WGS.

Ruling: Task3 exposes the actual heavy_work_job/work_pod quota unit, with rule-name classification, rather than falsely labelling existing grouped Job leases as per-rule counters. Reviewed executor acquire identity is run_label:job_name. Changing executor admission semantics/image is outside this display/collector repair. Cost if user requires truly independent per-rule quota: separate executor/pipeline change and runtime acceptance. User notified during implementation.

Task3 official API and minimal privilege research saved in OPT20260912_RESOURCE_RESEARCH.md. No billing requests or permission changes performed.

Task1 isolation review in implementation found that owner prepare derives cloud project from output basename and cloud batch from source table. A unique local parent alone does not prove cloud identity isolation. Implementer must verify/freeze distinct test cloud project and batch/lock/result identity without editing source table or formal pending. Actual controlled output child is displayed in preview; no silent fallback. This is an acceptance requirement, not permission to submit a real batch.

Installed cce-pipeline0.8.4 read-only AST confirms lock key hashes project/batch; owner cc9bde3 uses the same namespace suffix for cloud storage. Task1 freezes unique WGS_TEST_<token> basename while retaining source sampleinfo bytes/batch. Two-project namespace test is included. Independent review must still validate complete handoff/cleanup scope.

Task1 two preexisting WgsProductionUi full-file assertions (resource request count, duplicate dashboard totals) remain explicitly failed and are carried into Task2/3/final integration; do not report full frontend green yet.

Task1 fix round1/5 started:3 open Important findings (descendant symlink/write race, actual effective configuration freeze, delayed obsolete preview); review at a5aedc9, root docs commit0de0c5f unchanged implementation. Full findings in OPT20260912_SUBMISSION_REVIEW.md. Resume submission_opt, covering focused gate/config and delayed UI regressions before scoped re-review. Task2 remains pending until these are resolved.

Task1 fix round1/5 closed:3 addressed,0 open, fix d5a4e1d;97 backend/gate passed1optionalPGskip,UI16passed/tsc. Scoped submission_review approved the original findings and found no new Important/Critical. Task1: complete code (e107f3b..d5a4e1d, review clean); activation still requires sticky permission and matching audited owner source/config. No test deployment yet.

Fresh owner-source preflight: shared node repository HEAD is now68f5dcc, not catalog cc9bde3; prepare/config.yaml modified and both prepare/template hashes differ from audited pins. Do not reset/downgrade/patch that shared WGS repository. Test custom feature remains gated until an approved aligned immutable owner release is selected. Task2/3 development and other panel deployment may proceed independently.

Task2 intermediate implementation evidence (not acceptance): SQLite API reproduced3 rows instead of2 before current-attempt fence; explicit history/status filtering and complete filtered phase summaries implemented. Exact sample/family DOM6 passed after red reproduction. Logger/observer legacy group-member start regression and focused API tests23 passed. Generation-frozen estimate fake-time15 passed via existing writer transition, no DAG activation dependency. QC and shared display propagation still in progress; full scoped review pending.

Task2 submitted7033185:129 backend/logger/observer passed1preexisting skip54deselected,32 frontendpassed1remaining baseline Dashboard Total failure (Task3), fresh tsc/Vite build passed. Report OPT20260912_MONITOR_REPORT.md. Independent monitor_review dispatched with09efb4f..7033185 diff; task not accepted or deployed yet. WGS and GATK writer estimates included. cc9bde3 policy is audited; unmatched historical versions and missing numeric source remain explicitly unavailable. Existing active Master logger is not updated by panel source changes.

Task2 fix round1/5 opened at7033185:3 Important (fine release phases/group members missing, unsupportedQC PASS green, canceled phases planned) plus terminal overrun text and explicit GATK history/retry edge tests. Findings OPT20260912_MONITOR_REVIEW.md. Resume monitor_opt; no Task3 implementation until scoped fixes approved. Runtime logger activation remains a separate external requirement, not a missing panel deployment claim.

Task2 fix1 intermediate:45 backendpassed1existing skip,UI13passed. Covers pinned WGS/GATK phases, complete canceled summaries, group-member display, unknown PASS neutral, terminal estimate freeze and mismatched GATK history/retry. Serialization/alias integration and final build still pending; not review acceptance.

Task2 fix1 submitted d9543a0:83 backendpassed1preexisting skip,20focusedUIpassed,tsc/Vitegreen. Exact WGS cc9bde3/GATK bd04f6d phase inventories, full stream-scoped group members, neutral unknownPASS, canceled terminal precedence and GATK retry/history cases. Scoped monitor_review resumed7033185..d9543a0; awaiting verdict, Task3 still pending.

Task 2: complete (commits09efb4f..d9543a0, review clean). Fix round1/5 closed5findings,0open; monitor_review found no new Critical/Important. Existing Dashboard Total failure owned by Task3; upstream anyio warning/skip disclosed. Producer activation/historical missing evidence still external acceptance. Task3 begins fromd9543a0.

Task3 intermediate tests:full backend resource/SFS36passed including seven-day10080-point retention; later focused36passed1retentiondeselected (earlier full run retained). Full UI90passed/build;2additional edge cases await final rerun. Node synthetic SDK GET signing4calls passed,0network; probe extended to both POST routes, finalnodeverification pending. Task3 not yet committed/reviewed/deployed.

Task3 submitted f08d6b3:full backend37passed plus final collector/projection18passed,
fullUI92passed25files/buildgreen. Independent resource_review dispatched with
d9543a0..f08d6b3 scoped package. Final node SDK probe6synthetic calls/0network
passed. Review and deployment still pending; no protected service changed.

Task3: complete code f08d6b3, resource_review approved with0findings. Full-branch
integration_review dispatched e107f3b..f08d6b3. Candidate staged immutably at
releases/20260912-opt-f08d6b3a, archive SHA256
e719603ffea014a5cb6098d8c54c5b3edb48ec8dd7d04d8b519986baf47cf54a.
Cached offline full frontend92passed/buildgreen; image13dc750988a7.
Compose guard verified only panel source/image changes, existing shared mount
and7protectedserviceIDs preserved. No service cutover or collector install yet.

Final review fixwave1: P1ordinarycataloggateactivation (submission_opt4d3d24e)
and P2operationalrollbackpointer (roothelper) closed byoriginalintegration_review;
2addressed0open0newblocking. No repeatedwholebranchreview. FinalUI93passed/build,
guard29backend/10UI,rollback5syntheticpasses. Task3collectorinstalledtestprivate
with existinggate/runtime/SFShashesunchanged; live0/25fresh,enforce,waitingunknown.

Task4 paneldeployment complete at4d3d24e, source/archive/image/serviceIDs and
rollback inOPT20260912_TEST_RELEASE. Health/staticassets/APIsverified,3historic
GATKsuccessrecords retained,0activeDAGs,scan/dispatchfalse,7protectedIDsunchanged.
Conditional acceptance stillopen: userloginbrowservisual, customsticky/ownergate
alignment, actualproducer/enforcement/billingtelemetry. No productionpush/merge,
realrun or data deletion. Existingdevelopmentworktree retained.
