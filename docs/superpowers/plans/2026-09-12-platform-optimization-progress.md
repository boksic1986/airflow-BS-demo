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
- Task2 pending.
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
