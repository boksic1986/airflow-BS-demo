# BS96 authorized cleanup — 2026-09-27

User requests removal of failed WGS 20260921B/C/D/E analysis history and
associated samples, preserving pending flow records; corresponding SFS and OBS
FASTQ/results; additionally cloud batch data dated strictly before20260921.
Older DB records are not included. WES cloud scope awaiting separate reply.
The target plan below was recorded before deletion. Completed outcomes follow.
No data backup created/verified; deleted data is not claimed recoverable.

## Exact database targets

| Batch | Analysis ID | Samples |
|---|---|---:|
|20260921B|WGS_20260922_102447_8F03CA|1|
|20260921C|WGS_20260922_075550_FC9C3E|6|
|20260921D|WGS_20260922_090448_074B86|15|
|20260921E|WGS_20260922_080037_13013D|9|

Each is failed; business/Airflow active runs and occupied OBS leases are zero.
Delete these run-owned rows by exact analysis IDs, never by sample name.
Keep sample_reference, sample_reference_history, sample_reference_operation;
only the four nullable operation.analysis_id links must be detached before
deleting parents. Compare ledger content hashes (excluding this nullable link)
inside the same transaction. Keep other analysis records and their sample rows.
Delete associated submission drafts, intake_discovery and run audit records;
FK CASCADE removes run-owned events/QC/transfers/attempts/evidence projections.
No on-disk evidence or original data is included.

Scanner ownership for B/D would otherwise re-submit after FK SET NULL. Retain
dedup bookkeeping and add two exact chips to the existing ignore setting:
2280th_20260921B_E250209557 and2282th_20260921D_E250209574. Existing ignored chips,
dispatch/scan flags and watermark remain unchanged. Only scanner is recreated.
No new feature or runtime code change. Original service config retained privately.

## Exact cloud target names

OBS bucket obs-biosan-bioinfo. For EACH name below, delete BOTH exact prefixes
Project_fastq/WGS_Clinical/{name}/ and Project_result/WGS_Clinical/{name}/.
Trailing slash is mandatory. No bucket/root-prefix delete, no version purge.

1. WGS_20260911A_T7Hg38V4.2.1
2. WGS_20260912C-6-samples_T7Hg38V4.2.1
3. WGS_20260912D_T7Hg38V4.2.1
4. WGS_20260915B_T7Hg38V4.2.1
5. WGS_20260916R_T7Hg38V4.2.1
6. WGS_20260917A_T7Hg38V4.2.1
7. WGS_20260918A_T7Hg38V4.2.1
8. WGS_20260919A_T7Hg38V4.2.1
9. WGS_20260919B_T7Hg38V4.2.1
10. WGS_20260919C_T7Hg38V4.2.1
11. WGS_20260920A_T7Hg38V4.2.1
12. WGS_20260920B_T7Hg38V4.2.1
13. WGS_20260920C_T7Hg38V4.2.1
14. WGS_20260921B_T7Hg38V4.2.1
15. WGS_20260921C_T7Hg38V4.2.1
16. WGS_20260921D_T7Hg38V4.2.1
17. WGS_20260921E_T7Hg38V4.2.1

SFS volume37cacd44-60ad-41ef-9df2-f93b3dca7095, PVC biosan-clinical.
For names4 and7–17 above (12 names), both exact directories exist under
/workspace/wgs/runs/WGS_Clinical/ and
/workspace/wgs-obs-sync/Project_result/WGS_Clinical/; delete those24 trees.
Also one old misspelled project remains, exact directory
/workspace/wgs/runs/WGS_Clincal/WGS_20260907C_T7Hg38V4.2.0.
All target roots were lstat-confirmed directories, not symlinks. Recursive deletion
must not traverse symlinks. No broad parent-directory removal.

SFS operations use a temporary non-root10001/group10001+520 maintenance Job
bs96-batch-cleanup-20260927, no service-account token, existing final Master image,
deadline1800/TTL100. It runs no workflow. Exact helper is removed after completion.
There are no live WGS Jobs/Pods. Two unrelated old GATK image-pull-failing helpers
and terminal Jobs are not authorized deletion targets and remain untouched.

## Protected/recovery boundary

Additional observed expired OBS multipart targets, before abort (no current
writers): Project_fastq/WGS_Clinical/WGS_20260903A_STEP1_SDK_CANARY_T7Hg38V4.1.1/
(two uploads), WGS_20260906B_T7Hg38V4.1.1/ (two uploads), and
WGS_20260912C-6-samples_T7Hg38V4.2.1/ (one upload). The five exact upload IDs
are used for abort, not an unbounded recursive bucket abort. Result multipart0.

Database transaction committed: four AnalysisRuns and31 Samples removed.
Run-owned counts before cascade: rule_event_raw4571, rule_state1260,
kubernetes_workload898, transfer_file_state62, wgs_stage_execution30,
run_stage_state20, run_action18, evidence_cursor16, run_attempt4,
observer_run_state4, transfer_job4, wgs_execution_dispatch4, wgs_input_snapshot4,
audit_log2. Four nullable ledger links detached. All targeted analysis_id counts
then zero. Pending content verified unchanged: sample_reference23,
sample_reference_history162, sample_reference_operation20. No other sample-name
matching used. Full control log remains on BS96, no clinical payload in Git.
Scanner guard recreated only scanner using cleanup-20260927-control/scanner.json,
existing flags/ignore entries preserved; two exact B/D chips added. No database
backup taken, deletion is not claimed recoverable.

Preserve all offline /sg2,/bi projects, local results/FASTQ/sampleinfo/pending,
node/runtime evidence, SFS reference/pipeline/assets/evidence/test trees, OBS
P0SMOKE20260927, any other/newer batch. Pending DB ledger content stays intact.
No root/chmod/chown, no clinical files into Git, no test execution. OBS versioning
and recoverability not yet established; no guarantee of recovery after deletion.

Preflight command errors (read-only, no mutations): guessed intake batch_no/status
columns were corrected to sequencing_batch/state from models; draft state corrected
to status; default kubectl PATH and kubeconfig absent, switched to established
/home/chenjc/.local/bin/kubectl + .kube/bioinfo-cce.yaml; default OBS config empty,
switched to runtime-declared /bi/BioCodeHub/WGS/obs.config on node005. No credentials
printed/copied. Local PowerShell rg glob paths corrected to -g selectors.

## Actual outcomes

| Batch/project suffix | SFS run directory | SFS result linkage | OBS FASTQ prefix | OBS result prefix |
|---|---|---|---|---|
|20260911A / T7Hg38V4.2.1|absent before|absent before|deleted|deleted|
|20260912C-6-samples / T7Hg38V4.2.1|absent before|absent before|deleted|deleted|
|20260912D / T7Hg38V4.2.1|absent before|absent before|deleted|deleted|
|20260915B / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260916R / T7Hg38V4.2.1|absent before|absent before|deleted|deleted|
|20260917A / T7Hg38V4.2.1|absent before|absent before|deleted|deleted|
|20260918A / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260919A / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260919B / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260919C / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260920A / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260920B / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260920C / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260921B / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260921C / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260921D / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260921E / T7Hg38V4.2.1|deleted|deleted|deleted|deleted|
|20260907C / T7Hg38V4.2.0 (WGS_Clincal)|deleted|not present|not present|not present|

All25 SFS target removals returned success. Final directory enumeration empty
for the three exact WGS parents listed above. All34 OBS removals exited0; final
delimiter listing has only each empty WGS_Clinical parent marker, no child prefix
or complete file. Actual per-prefix obsutil deletion records are retained under
node005 /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/cleanup-bs96-20260927/
(BS10610 /mnt/biodevrwsg2 view). Initial evidence-root guard wrongly used the
BS10610 view on node005 and exited1 BEFORE deletion; corrected only to verified
node005 view. No data-target change or blind retry.

Multipart abort of exact first upload000001A07210C96581AA2723CDD314BB returned
403 AccessDenied, request000001A0E1F2A2DD83E8531E70B87EEE. Stopped immediately;
other four aborts were not attempted. All5 incomplete uploads remain unresolved,
not included in completed-file deletion. Requires an authorized identity with
AbortMultipartUpload capability; do not borrow another key or weaken IAM.

Final DB read: target runs0, other WGS runs15; pending counts23/162/20 retained.
Two scanner bookkeeping rows remain needs_review with null analysis_id and are
excluded by exact chip IDs; this prevents automatic recreation, not manual
submission. Only scanner service changed; other controls unchanged. Temporary
maintenance Job and owned Pod deleted successfully. No workflow/test submitted.

Older WES cloud batches20260823A/20260907A/20260914A/B/20260917S are untouched,
awaiting the user's explicit answer to the cross-pipeline scope question.
WES20260921B, smoke assets and every offline path remain protected. No Airflow
metadata DAG history was deleted: requested analysis DB is biodemo. The user
may delete local prepared projects separately if wishing to reuse the same path;
this cleanup does not authorize that deletion or bypass existing-directory guards.
