# WGS/GATK platform optimization — approved implementation

## Global constraints

Test only: develop in D:/pipeline/airflow-demo-worktrees/development and run tests/deploy only BS10610. Preserve scan/dispatch switches, active analyses, production, source projects and formal pending. No real batch submission, Docker Hub pull, full WGS rerun, unrelated commits or data deletion. Production release requires separate approval. Starting baseline e107f3b.

## Task 1: Submission and test-project interface

Vertical WGS/GATK selector matching Command Center. WGS two-column grouped input/project/analysis parameter form; responsive single column. Three confirmations retained. Separate pipeline draft recovery. Release-derived actual supported caller, CNV/reference and other supported options chosen at first step, validated/frozen backend and shown in review. Distinguish DNAscope, Sentieon Haplotyper and GATK HaplotypeCaller. GATK release exposes configured versus observed cce-pipeline/profile/Master/check time honestly.

BS10610-only existing WGS sample-list project preview and new independent project submission. Production rejects server-side as well as hides UI. Output root /sg2/50.ctapa/project/HWcloud/WGS_test with custom relative child; fail explicitly if unwritable, never fallback. Exact validated source/frozen samples/FASTQ/config fingerprints, no implicit sample expansion or copied results. No overwriting existing targets, traversal or escaping symlinks. Idempotent new analysis ID. Test-local preparation only, no shared pending access.

## Task 2: Rule/QC/estimated progress

Current attempt default, explicit attempt history, exact sample and separate family filters, stable complete instance keys, no duplicate retry evidence. Release-correct biological phases and expandable execution groups; unknown stays unknown. Never infer individual child start from group start. Missing time stays absent; reconciled success marked inferred. Fix producer/parser/projection where actual evidence exists.

QC follows release-pinned WGS cfg/qc_config.json, script/g1.Collect_QC.py and script/g2.Collect_multiqc_QC.py including conditional thresholds/sample type. Return per-metric units, threshold, status, reason, provenance. Colored abnormal values and Contamination badges; missing is unknown. Do not silently reinterpret history with latest thresholds.

Separate Step4/6 estimated display fields: last20 matching pipeline/release/target successful-stage durations, >=3 complete observations median; fixed baseline per execution. Actual start only, eased monotonic estimate max99 until actual success100. Failure/cancel freezes, retry resets. Queue no growth; history insufficient indeterminate. Real progress takes priority; overrun says still executing. No mutation of true progress or Airflow status.

## Task 3: Resource monitoring

Diagnose heavy implementation, quota, heartbeat, collector/spool/API. Report the actual quota unit: live source inspection established work Job/Pod leases, with rule names classifying a workload; one grouped Job consumes one lease. This explicit correction to the original per-rule assumption is recorded in the execution ledger and was communicated to the user. Do not change executor admission semantics in this panel repair. Occupied/limit/waiting/mode/freshness/reason distinguish idle/stale/error/not-enabled. Never replace unknown with invented0. SFS capacity/read/write/total bandwidth and reliable live CPU/memory separate from resource packages. Official read-only CPU/memory hours, OBS storage and request package balances with total/remaining/unit/expiry/updated. Hourly backend cache; explicit unavailable reason if no permissions/config, no control-console scraping or static screenshot values.

## Task 4: Integration, test and deployment

API additive compatibility and docs05/06/08/11/34 as affected; no destructive migrations. BS10610 cached targeted pytest/Vitest/build. Test submission isolation/idempotency/traversal/draft restoration, rule family/attempt/ordering/missing timestamps, QC boundary/type/missing/history, fake-clock estimates, quota/stale/resource units/cache. Browser verify test UI and no flash. Deploy affected test services only after active-state preflight; preserve workloads/switches. Record exact tested source, services, rollback, unverified cloud permissions/runtime limits separately in state/handoff.
