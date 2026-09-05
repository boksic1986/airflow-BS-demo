# CURRENT_STATE.md

## 2026-09-05 T203 Airflow-integrated Step1 OBS SDK canary

scope: BS10610 test control plane only; `20260902A` was reduced to one sample
and two FASTQ files under
`/sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow_test/WGS_Clinical`. Step2 and
all downstream analysis stages were intentionally unreachable.

runtime: cce-pipeline `0.8.2` was rebuilt from test branch commit
`98ce7bedad573beca9417d1572c6ce40f1fa401c`; wheel SHA256 is
`760ecca73ba0601fc8dccdc3edb8249c9ff28c8f2309b31fa73a8329d29d7cec`.
The isolated wheel is selected with `CCE_PIPELINE_BIN`; the production default
under `/bi/software/mamba/envs/WGS` was not overwritten.

canary: `WGS_20260905_094849_373238` attempt 3 and Airflow DagRun
`WGS_20260905_094849_373238-a3` completed successfully. The frozen denominator
was 2 files and 128,567,092,797 bytes. Both file rows reached 100 percent with
checksum status `verified`; the Step1 execution has a terminal receipt hash and
the run records `validation_result=step1_upload_complete`.

safety: Airflow task `submit_step2_master` and all Step3-Step6 tasks were
skipped. The generated Master name did not exist in Kubernetes. Source file
size, mtime and inode were unchanged after the read-only transfer. The two
exact canary OBS objects were verified absent through the private OBS endpoint;
no unrelated objects were touched. `bio_wgs` is paused, all BS execution,
runtime, contract, canary, dispatch and intake gates are false, and node200 was
restored to its disabled runtime configuration. No production `.96` service or
shared production WGS environment was modified.

diagnostics: attempt 1 exposed an untraceable source checkout; attempt 2 exposed
the WGS production-package root guard. Neither reached Step1. The accepted
attempt used a provenance-bearing wheel and explicit validated CLI. Transfer
preflight currently spends several minutes checksumming both files before SDK
callback progress starts; a future UI should label this state separately.

## 2026-09-05 T194-T200 cce-pipeline 0.8.2 integration refresh

```text
scope: refreshed the existing disabled Step1-6 contract-v2 implementation on the operator-provided cce-pipeline 0.8.2 commit eacef2114cef6581397e9923d9674ab17b92b4df.
cce_code: isolated integration commit e4c0f134bd397fb6113456b18cc148346808388e. The operator config now carries an independent heavy_io limit/mode, frozen Master Jobs receive WGS_HEAVY_SLOT_LIMIT/MODE/STATUS_PATH, and RESOLVED_PROFILE records transfer and heavy quota provenance.
transfer_semantics: upload_parallelism and download_parallelism count concurrent files; obsutil -p=5 counts parts per file; heavy_io.limit=25 counts active high-I/O Kubernetes work pods. These controls do not consume one another.
candidate_image: airflow-demo/wgs-cce-master:contract-v2-cce-0.8.2-e4c0f13-candidate, image sha256:58c2c9acf935f1d06c4b1b60d8bc56ca758d7d9643707b2d9077bc9445c6dae8. Runtime contains cce-pipeline 0.8.2, Snakemake 9.24.0+biosan1 and executor 0.6.4+biosan4.
validation: cce-pipeline full Linux suite 216 passed; backend 352 passed/1 skipped; runtime scripts 67 passed; WGS DAG/topology 16 passed; frontend 49 passed plus typecheck/Vite build; Compose config passed. Wheel SHA256 b2c79df27868d9194097cfa1e28ce73d688e1a107b1ec2643dab82544551d968; package source commit and all four approved heavy rules were verified inside the image.
test_runtime: the shared BS `/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest` environment was explicitly changed from the older project build 0.8.3 to the approved 0.8.2 wheel. The installed-package suite passed 216 tests and `cce-pipeline --version` reports 0.8.2. Numeric version ordering is not release ordering for these two project builds. The expected BS10610 `/mnt/33.chenjiucheng/.../nipttest` mapping was not mounted during verification, so this evidence is from the `/sg2` view on BS.
deployment: disabled release staged at /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260905-airflow-demo-379df64-t194-cce082-disabled. current intentionally remains the prior disabled c28ad7d release. The node200-visible runtime gate was atomically updated to SHA256 cc44aba5...d6f0 with an exact pre-update backup.
activation_blocker: /bi/software/mamba/envs/WGS is owned by chenxj and is not writable by hanjj, so its installed cce-pipeline remains 0.8.1 commit 71952c5.... The verified 0.8.2 and rollback 0.8.1 wheels are both visible from node200; the environment owner must perform the final installation before selecting the new Master image.
safety: candidate remains unselected. WGS execution, runtime adapter, contract-v2 and auto-dispatch gates remain false; bio_wgs is paused, scanner is stopped, and both business/Airflow active-run counts are zero. No WGS run or automatic dispatch was started.
```

## 2026-09-05 T201 real FASTQ OBS SDK upload canary

```text
scope: uploaded one approved validation sample's two real compressed FASTQ files through the standalone Step1 OBS SDK adapter without starting Airflow, CCE or a WGS analysis.
result: 14,486,007,978 bytes (13.4911 GiB) completed in 152.862 seconds at 94,765,457 B/s (90.38 MiB/s) aggregate. R1 completed in 135.842 seconds at 49.49 MiB/s; R2 completed in 150.076 seconds at 47.26 MiB/s.
progress: the frozen denominator never changed. The recorder emitted 116 safe snapshots, including 68 distinct partial R1 values, 79 partial R2 values and 111 aggregate partial values. Per-file and aggregate status, bytes, percentage and speed are observable independently.
integrity: source size and mtime remained unchanged; remote size and CRC64 matched both sources. Both exact canary objects returned DELETE 204 and subsequent HEAD 404. Progress evidence contains only safe aliases and no bucket, OBS URI, credential or source path.
adapter_fix: real 6-7 GiB files exposed two synthetic-canary gaps. Files larger than 5 GiB now use resumable 64 MiB multipart upload with four SDK workers, checkpointing and CRC64. The SDK notifier now coalesces burst byte updates so shutdown cannot be blocked by a per-chunk queue backlog. Focused tests pass 8/8.
evidence: node200 /sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow-wgs/runtime/cce-evidence/T201-real-fastq-upload/real-fastq-20260904T164733Z-60498b83.
safety: WGS execution/runtime/contract-v2/auto-dispatch gates remain false, bio_wgs remains paused and no Airflow run was created. This proves the transfer data path; frontend/API projection still requires one separately approved contract-v2 Step1 integration canary.
```

## 2026-09-04 T194-T200 WGS contract v2 disabled deployment

```text
implementation: Step1-6 now uses versioned stage executions and exact predecessor receipts. OBS SDK transfers freeze manifests and expose aggregate plus per-file progress. Run Detail uses one database-backed workspace request, lazy cached tabs and no browser-side automatic sync. The vendored Kubernetes executor enforces 25 global high-I/O Worker Pod leases for mapping+Dedup and Haplotyper+QualCal.
code: airflow-demo commits 4dc577b, ee237f9, 9ebc475 and c28ad7d on jiucheng/wgs/T194-step1-6-v2; cce-pipeline commits 25884cc, 26befea and 32851ba on jiucheng/wgs/T197-heavy-slot-quota.
validation: backend 352 passed/1 skipped; runtime scripts 61 passed; bio_wgs DAG 14 passed; frontend 49 passed plus tsc/vite build; cce-pipeline 214 passed. Candidate executor/cce wheel SHA256 values are 98ab02fc...9341 and 968a3b1a...3d4.
deployment: current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260904-airflow-demo-c28ad7d-t194-contract-v2-disabled-r2. Frontend image airflow-demo/frontend:t194-contract-v2-disabled is live; CCE image airflow-demo/wgs-cce-master:contract-v2-32851ba-candidate is built but not activated.
safety_state: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false, WGS_AUTO_DISPATCH_ENABLED=false, WGS_CONTRACT_V2_ENABLED=false, bio_wgs paused, intake scanner stopped, and there are zero active business or Airflow runs. No WGS analysis was submitted or resumed.
performance: the deployed workspace endpoint returned a 90.4 ms median over five warm calls; paged Rules returned 1/208 with limit=1.
resources: platform-node-probe runs as host UID 6708 with a dedicated mode-0600 test identity. node-96 and node-97 are healthy. The production CES read-only configuration was cloned into a separate node200 collector at /home/hanjj/.config/airflow-wgs-bs10610 without copying AK/SK to BS or Git. The shared numeric cloud.json is mode 0644 and the live API reports sfs-turbo-clinical healthy with fresh capacity, read/write bandwidth and IOPS values.
obs_sdk_runtime: the shared nipttest Python 3.9 environment now contains esdk-obs-python 3.26.6 and huaweicloudsdkcore 3.1.210. Imports of ObsClient and BasicCredentials pass from both BS10610 and node200. The environment is installed through writable node005 /sg2; BS10610 sees the same path read-only. Existing unrelated pip-check findings for aioeasywebdav, eido and veracitools remain documented and were not changed.
obs_sdk_canary: a standalone 1 MiB + 65 MiB synthetic transfer completed upload, download and generation-2 reuse through the real OBS SDK. Frozen total was 69,206,016 bytes, nine partial callback events were captured, object metadata/ETag and downloaded MD5 checks passed, and progress JSONL contained no OBS URI, bucket, credential or /sg2 path. Both test objects returned DELETE 204 and subsequent HEAD 404; local payloads were removed. Evidence is under node200 `/sg2/14.hanjingjing/Cloud_WGS_Clinical/airflow-wgs/runtime/cce-evidence/T200-obs-sdk-canary/real-canary-20260904T155225Z-84e2670a`.
obs_sdk_compatibility: the canary found and fixed two esdk-obs-python 3.26.6 differences: its notifier cleared callbacks before the queue drained, and its metadata response omitted custom metadata. The adapter now uses a queue-draining notifier and accepts a strict 32-hex single-part ETag fallback after size validation. The SDK credential is sourced from the existing CCE test Secret and remains mode 0600 on node200; production obsutil configuration was not changed.
backup: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/T194-T200-contract-v2-20260904T132157Z. Both pg_dump archives passed pg_restore inventory validation.
deployment_incident: the first migration command allowed Compose to recreate only the PostgreSQL container because its candidate service hash changed. The named airflow-wgs_postgres-data volume was retained, both databases remained intact, migration 0014 completed, and PostgreSQL is healthy. Later service updates used --no-deps. This deviation must remain visible in the handoff.
storage_cleanup: an NFS user write quota initially blocked release extraction. Only unmounted airflow-WGS development/build cache under dev was reduced (about 1.3 GiB freed); current release, env, databases, evidence, runtime results and Docker volumes were preserved. Root-owned residual cache was left untouched.
network: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only frontend 172.17.106.10:12959 is published.
```

## 2026-09-04 T192 production Docker test-artifact cleanup

```text
scope: removed only obsolete airflow-demo backend/frontend tags, exact unused frontend test/build images and the exited airflow-wgs biodemo-migrate one-shot container. No docker prune command was used.
retained_images: airflow-demo/airflow:bs-control-c706548; airflow-demo/backend:t184-prepare-nfs-race; airflow-demo/frontend:t188-step6-projection-auto. These are the sole current WGS application image versions.
preserved: all 11 running airflow-wgs services, PostgreSQL and Redis containers/volumes, current release files, unrelated containers/images, and all analysis data.
verification: no dangling image remains; Compose reports all 11 production services running; http://172.17.61.96:12959/ returns 200.
invariant: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1 and 11 attached WGS services.
```

## 2026-09-04 T191 frontend login reverse-proxy DNS recovery

```text
incident: after the T190 backend container recreate, the browser could load the React shell but `/api/auth/me` and `/api/auth/login` returned nginx 502. This was not an account/password failure.
root_cause: frontend-nginx had resolved backend to the previous container address 192.168.199.8 at startup. Docker DNS correctly resolved the recreated backend as 192.168.199.4, but the running nginx workers retained the stale upstream and logged connection refused.
recovery: production Compose config passed, then only airflow-wgs-frontend-nginx-1 was restarted. No image, credential, database, backend, Airflow, scanner, volume or network change was made.
verification: a server-local login using the protected production admin environment returned HTTP 200, and the resulting authenticated `/api/auth/me` returned admin/admin with HTTP 200. Nginx access logs record both 200 responses; credentials and session token were not printed.
invariant: current remains /data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t190-intake-name-correction-r2; only 172.17.61.96:12959 is published.
```

## 2026-09-04 T190 T7 source-name correction and false backfill rollback

```text
source_truth: the operator confirmed that 2224th_20260902A_E250197512 and 2225th_20260902B_E250197501 are the latest directories; their chip numbers were entered incorrectly and should have been 2234/2235. 2233th_20260901B_E250197502 is an older completed directory. Numeric chip order is therefore not a valid freshness signal.
correction: the temporary numeric-head reconciliation was removed. Scanner freshness remains based on the regular BarcodeStat marker relative to the persisted bootstrap watermark. The source directories are not renamed and the UI continues to show their real on-disk names. The shared backend WGS batch matcher remains only as a no-behavior-change deduplication of automatic-dispatch identity logic.
live_result: the exact false 2233 intake index row created during diagnosis was deleted; its successful AnalysisRun WGS_20260902_181846_20A4D2, source directory and results were preserved. A restarted scanner examined 1845 directories, updated only 2224/2225, created zero rows and submitted zero analyses. Intake again contains exactly 2224 and 2225.
validation: the corrected focused intake/dispatch suite passed 22 tests and the complete `.96` backend suite passed 341 tests with 1 skipped. No active WGS run existed at deployment.
deployment: current -> /data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t190-intake-name-correction-r2. Only backend and scanner were recreated. PostgreSQL, Redis, Airflow, frontend, volumes and CCE were not recreated. nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only 172.17.61.96:12959 is published. Git remains uncommitted by operator request.
```

## 2026-09-04 T189 Step5 recovery and exact batch QC projection

```text
incident: 20260902B completed its 481-rule Master and Step4 publish, but Step5 failed before launch because the local payload manifest was required even though Step5 itself retrieves that manifest from OBS. A later retry also lost retry_no in progress writes, so Airflow could reject a valid retained worker. After Airflow recovered, same-attempt terminal monotonicity left the business run and samples falsely failed.
runtime_fix: Step5 now starts before waiting for the manifest, freezes an immutable plan once it appears, uses exact planned targets/sizes for completion, preserves retry_no and final transfer detail, and fails closed after the bounded post-exit visibility grace. No duplicate worker, DagRun or Master is created.
projection_fix: an explicit positive retry generation may reconcile an older failed RunStageState, while ordinary terminal replay remains monotonic. Airflow success replaces stale failed completion time, finalize_run clears the stale error and synchronizes all samples. The controlled QC selector now chooses only 07_QC/<batch-directory>.QCstat.tsv even when per-sample QCstat files coexist; Yes becomes pass, non-empty exception text becomes warn, and empty stays unknown.
recovery: the original WGS_20260903_200310_37E27D-a1 was retained. Only Step5 and its downstream tail were recovered; Step1-Step4 and Master cce-master-44815ec87b04c2020d77 were not rerun. DOWNLOAD_VERIFIED and MATERIALIZED are PASS. Airflow has one exact DagRun with all 24 tasks success and terminal time 2026-09-04 13:23:06 CST.
live_state: business run success/attempt 1/progress 100/Workflow complete; 8/8 samples success; 481/481 Rule states success; Step5 exact plan 26/26 files and 447124566023/447124566023 bytes. Public sample projection reads the one batch QCstat and returns 2 pass, 6 warn and safe metrics for all 8 samples; Files exposes exactly one wgs_qcstat artifact.
validation: .96 backend 341 passed, 1 skipped; runtime scripts 57 passed. Health is OK. Local/release/node200 gate SHA256 all equal e3e6f223e9e8f20ceb796a5de57aa667f6c64f8d862f6f693f7012f6f931302f. No node200 gate worker remains.
deployment: current -> /data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t189-step5-manifest-r4. Only backend was recreated for the final QC projection. PostgreSQL, Redis, Airflow services, CCE Master, volumes and network were preserved. nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only 172.17.61.96:12959 is published. Git remains uncommitted by operator request.
```

## 2026-09-04 T188 Step6 barrier, unified projection and automatic intake

```text
implementation: bio_wgs now starts asynchronous step6_materialize, waits on wait_step6_materialize, and only then invokes finalize_run. The backend independently validates the exact successful Step6 marker identity, so a start-task success can no longer finalize the business run early.
projection: WGS sample manifest, per-sample Rule/QC matrix, controlled artifact list, log labels and failure excerpts are projected once by the backend. The browser no longer parses sampleinfo, maps Rule states or receives absolute SFS paths. Names and hospitals are excluded.
transfers: new Step1/Step5 workers create an immutable transfer-plan.json before obsutil, freezing file count, byte total and manifest SHA256. Old observations without a plan are labelled legacy_estimate.
resources: the dashboard shows a single selected analysis node with CPU, memory and normalized load bars. Duplicate node identity and client connections are hidden; the SFS resource name is a tag and its I/O history uses 24h/1d/7d views over bounded server history.
automatic_intake: the scanner calls an internal authenticated dispatcher only after a successful scan. biodemo AnalysisRun/input snapshot plus the deterministic Airflow DagRun identity is the duplicate gate. Any batch with an existing manual or automatic run in any status is linked and skipped; terminal failures are never restarted automatically. A required activation watermark prevents historical ready rows from being submitted.
validation: final read-only release tests on .96 passed backend 338 tests, runtime 47 tests and DAG/deployment 21 tests; the earlier frontend run passed 47 tests and the final production build passed. A redundant offline npm image-layer rerun could not reuse the dependency layer and failed in npm ci before tests; the already-built final dist remained the verified index-DZXT7pAH.js. Compose config, subnet 192.168.199.0/24, gateway 192.168.199.1 and the single published 172.17.61.96:12959 port were verified.
deployment: current points to /data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t188-step6-projection-auto-r1. node200 gate SHA256 is 2265e99f037e5b6fd32388753f67570ebedc2e9adad1d7c2e3ad81fef81f7794. Auto dispatch was activated at 2026-09-03T21:36:11Z; two consecutive scans examined the two ready rows, linked both to their existing manual runs, submitted zero, and kept AnalysisRun/DagRun counts at 4/10.
step6_recovery: exact success markers were revalidated for 20260825A attempt 7 and 20260902A attempt 1. Both original DagRuns added wait_step6_materialize=success and then finalized success; materialize_step6_results stayed try 1.
deployment_incident: the first service recreate inherited a release-file permission that prevented Airflow from reading bio_wgs.py. The active 20260902B sensor was control-plane failed and release_leases drained its observer, while CCE Master cce-master-44815ec87b04c2020d77 remained Running and unchanged. Only code-directory read permissions were corrected; the same DagRun tail was cleared, the DAG reparsed active/unpaused, wait_step3_analysis returned to up_for_reschedule, and its observer was explicitly reactivated healthy. Step1/Step2/Step3 start tasks remain try 1 and no new Master or DagRun was created.
```

## 2026-09-04 T187 20260902B exact reset and corrected resubmission

```text
incident: WGS_20260903_111829_1D58E1 attempt 7 failed in prepare_wgs_analysis because the exact batch directory already existed. This was a real backend failure, not a frontend projection; Step1 and a new Master never started.
cleanup: the operator explicitly waived backups for this test batch. Frozen Step0 was attempted but failed before mutation because the orphan bundle had no worker manifest and the reset Job tooling failed. After reconfirming no process, flock, Master, Pod, Job or ConfigMap lock, the exact local batch directory, exact SFS run/linkage path, three generated sampleinfo files, runner requests/bindings/evidence, seven Airflow DagRuns and old biodemo run/dependencies were deleted. OBS FASTQ was not deleted.
selection_root_cause: a clean sampleinfo fetch returned 11 family rows, but final preparation returned only two singleton samples. The current B FASTQ directory has six pairs; expanded family members WGS26080571, WGS26080572 and WGS26080575 are sequenced in 20260902A. Their missing sequencing-batch identity caused WGS to place both otherwise complete families in pending.
selection_recovery: the three exact pending rows were atomically assigned their Samplelist-proven sequencing batch 20260902A. A read-only run of the frozen WGS selector proved 8 kept samples, 3 pending samples and 16 readable FASTQ paths. No final sampleinfo row or FASTQ link was fabricated.
fresh_run: WGS_20260903_200310_37E27D-a1 regenerated source and final sampleinfo, reached execution_review with exactly 8 samples, then received config and execution approval. It waited without stealing the single OBS slot, acquired it after the prior lease expired, reused the existing FASTQ objects, and completed Step1 plus Step2 automatically. It is now running Step3 against active Master Job cce-master-44815ec87b04c2020d77 in snakemake-ns; the runner status identity is the same analysis, attempt 1 and stage.
invariants: the old analysis has no remaining node200 runtime matches; nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only 172.17.61.96:12959 is published. Service volumes were not rebuilt, production WGS remains pinned to V4.1.1 commit 6c982817614db6a1157b6f287427ddf01ac91827, and Git remains uncommitted.
```

## 2026-09-04 T186 approval-sensor backend DNS recovery

```text
incident: 20260902B attempt 6 successfully completed sampleinfo and prepare_analysis, then wait_wgs_execution_approval failed before Step1 when the Airflow worker had one transient Docker DNS failure resolving backend. All later tasks were upstream_failed; no OBS upload, CCE Master or Rule observer was started.
root_cause: stage_ready already converted BackendTransportUnavailable into a five-second sensor reschedule, but submission_gate_ready called the same backend transport without that protection. The approval poll therefore treated infrastructure transport loss as a workflow verdict.
fix: stage and approval sensors now share one _sensor_backend_json helper. URLError and timeout return not-ready and reschedule; HTTP/application errors remain terminal.
tdd: both config and execution gates raised BackendTransportUnavailable against the previous DAG. After the fix, the two focused transport tests and all 14 bio_wgs DAG unit tests pass in the .96 Airflow image.
deployment: current -> /data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t186-approval-sensor-dns-r1. Only airflow-api-server, airflow-scheduler and airflow-worker were recreated. The production Compose file is always selected explicitly with -f docker-compose.wgs.yaml.
deployment_recovery: one initial command omitted the production Compose filename and briefly attached only those three newly recreated Airflow containers to an empty 172.30.10.0/24 network. Verification caught the DNS failure before any WGS work advanced. The services were immediately recreated on nipt_analysis_test_net and the empty accidental network was removed.
live_verification: bio_wgs has no import errors; all three Airflow services resolve backend/PostgreSQL/Redis. 20260825A remains attempt 7 at Step3 with observer active/healthy and 72 Rule rows. 20260902B remains attempt 6 at execution_review with no approval, Step1, Master, observer or Rule rows.
network_invariant: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only 172.17.61.96:12959 is published and /api/health returns ok.
recovery_boundary: 20260902B remains in execution_review with no execution approval. Deploying the DAG fix must not approve it, start Step1, create a Master or activate Rule monitoring.
git: working tree remains uncommitted at the operator's request.
```

## 2026-09-04 T185 retried Rule evidence identity repair

```text
incident: 20260825A attempt 7 and 20260902B attempt 4 both had readable Rule JSONL and analysis.log files, but observer stopped at line 1 with "event attempt does not match binding". The Rule logger emitted schema-1 attempt="attempt-1" for each fresh Master, while the outer Airflow attempts were 7 and 4.
root_cause: schema-1 identifies the frozen execution with exact run_label; its attempt field is Master-local. The observer incorrectly compared that local label to the outer Airflow attempt. Run detail also selected the newest observer row regardless of the current AnalysisRun attempt, so 20260902B attempt 6 displayed attempt 4's warning.
fix: schema-1 keeps strict run_label/role/stream validation and is stored under the frozen binding attempt; rule-event.v1 retains exact analysis/release/attempt validation. Run detail now selects observer state by analysis_id plus the current attempt.
live_recovery: existing cursors resumed without editing evidence. 20260825A attempt 7 consumed 66 events and projected 20 Rule instances on the first recovery poll; 20260902B attempt 4 consumed 20 events and projected 6 Rule instances. Both observer rows became healthy with empty last_error; the terminal attempt-4 observer was then drained to stopped while current attempt 6 remains without an observer until Step3. No Master or analysis task was restarted.
tdd: both regressions failed against the previous implementation, then the focused WGS observer/API suite passed 70 tests. A clean network-isolated .96 Docker run with backend and config mounted read-only passed 329 tests with 1 skipped.
deployment: current -> /data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t185-rule-attempt-binding-r1. Only backend and wgs-run-observer were recreated; frontend-nginx was restarted once to refresh the recreated backend container address. PostgreSQL, Redis, Airflow, scanner, volumes and CCE workloads were unchanged.
network invariant: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only 172.17.61.96:12959 is published and /api/health returns ok.
git: working tree remains uncommitted.
```

## 2026-09-04 T184 20260902B clean prepare recovery

```text
incident: attempt 5 completed remote prepare_analysis, but its success status reached .96 before the final sampleinfo.tsv became visible through the shared NFS mount. The backend raised HTTP 500 and Airflow failed the wait sensor.
cleanup: after confirming attempt 5 and its DagRun were failed, the OBS lease was empty and no CCE Master existed, the generated batch directory was moved to /sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/.rerun-archive/20260903T171610Z/attempt-5/. The refreshed source sampleinfo was retained with 11 rows and SHA256 c685cbb075a0bd4ecd1040bf0009f8e0defd0103de2e1dc5ad86b9c1edade0f7.
fix: a successful prepare marker with an as-yet invisible sample table now returns HTTP 200, ready=false and artifact_pending=true. The five-second Airflow sensor reschedules. Empty tables, invalid sample IDs, unsafe links and identity/schema errors remain hard failures.
tdd: the focused test failed against the prior code with ValueError WGS prepare did not publish final sampleinfo.tsv, then passed after implementation. The complete .96 backend suite passed 328 tests.
deployment: current -> /data/airflow-WGS/releases/20260904-wgs-4.1.1-6c98281-t184-prepare-nfs-race-r1. Only backend was recreated. Because the configured registry mirror DNS was unavailable, the already-tested T183 dependency image was retagged; /app is the read-only T184 release bind mount containing the new source.
backup: /data/airflow-WGS/backups/T184-prepare-nfs-race-20260903T172446Z; biodemo SHA256 010962e0da461ddfe16156c6a44a996f6ec267ce2c33adb4d539a7184058ce89; airflow SHA256 d8de023653b24e9c250de3dd3a7fa6d20491330fdef7e7ef0a3251317e02152f.
attempt6: WGS_20260903_111829_1D58E1-a6 reached execution_review. Source sampleinfo has 11 rows; regenerated final sampleinfo.tsv has two rows: WGS26080569 and WGS26080573. The remaining nine follow the current WGS pending logic.
execution_gate: config is approved, execution_approved_at is empty, Step1 and Step2 task instances have not started, the OBS lease is empty and no CCE Master exists. The operator owns the final execution action.
network invariant: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only 172.17.61.96:12959 is published.
git: working tree remains uncommitted at the operator's request.
```

## 2026-09-03 T183 20260902A Rule monitoring and log access recovery

```text
incident: WGS_20260903_111456_397777-a1 lost Step3 control-plane monitoring after one backend restart timeout; two recovery attempts then failed because node200 briefly could not see the already registered request on shared NFS. The bound CCE Master itself remained Running.
root_causes: Step3 sensors treated transient backend transport failure as terminal; runner launch had no bounded retry for the exact runner-request visibility race; Rule sample context used WGS data_id while the business sample table stored the base sample_id; the documented per-Rule analysis-log link was not rendered.
fix: backend transport outages reschedule the sensor; exact missing runner-request errors retry up to five times; observer accepts only a unique registered sample_id/data_id alias; every projected Rule receives the registered opaque analysis-log key and the Rule table opens that source in Logs.
recovery: the original DagRun and attempt were retained. Only start_step3_monitor and downstream tasks were cleared; submit_step2_master remains success/try 1 and the Master Job cce-master-570b96f972d40847e331 was not recreated.
live_state: start_step3_monitor=success/try 4, wait_step3_analysis=up_for_reschedule, observer=active/healthy. Three current Rule states are linked to sample WGS26080568 and family JX26G00230117; all three expose the same registered analysis-log key.
validation: DAG focused suite 13 passed; backend full suite 327 passed; frontend full suite 47 passed and Vite build passed. The latest production check returned 19 Rule rows, all 19 sample/family/log linked; opaque log read returned the latest 200 lines without a path. Production health, Compose config and fixed network checks passed.
deployment: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t183-rule-log-link-r1; backend image airflow-demo/backend:t183-rule-log; frontend image airflow-demo/frontend:t183-rule-log.
backup: /data/airflow-WGS/backups/20260903T2120-t182 contains mode-0600 Airflow/biodemo dumps, task state and clear dry-run/actual evidence.
network invariant: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only 172.17.61.96:12959 is published by this platform.
git: working tree remains uncommitted at the operator's request.
```

## 2026-09-03 T179 transfer units, load visualization and SFS chart repair

```text
frontend: Current Progress, Run Tracker and the Step1/Step5 workflow cards now share one binary byte formatter and display KiB/MiB/GiB/TiB-sized values instead of raw byte integers.
node_health: CPU, memory and load are separate utilization bars. Load uses max(load1, load5, load15) / logical CPU count, retains the three raw load values on the right and changes green/warning/danger at <70%, 70-<100% and >=100%.
cloud_resources: Client connections is a spaced inline row with the value right-aligned. The SFS read/write chart has a visible max/mid/zero Y axis with automatic KiB/s, MiB/s or GiB/s units.
collector_contract: node metrics now include logical_cpu_count; no database migration or new endpoint was required.
runtime_fix: transfer aggregation now remains running while any child obsutil operation is running, even if an earlier auxiliary child record failed. The node200 gate was atomically updated; already-running workers were not restarted.
validation: .96 Docker frontend 46 tests and build passed; Python 374 tests passed with 1 skipped. Focused red tests reproduced all missing UI fields and the transfer aggregation defect before implementation.
deployment: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t179-progress-resource-r1; frontend image airflow-demo/frontend:t179-progress-resource. Only platform-node-probe, platform-metrics-collector and frontend-nginx were recreated.
live_state: 20260902B had already acquired the single OBS slot and was actively uploading during deployment; its worker PID was preserved. Its outer Step1 status is running, while its old worker can still expose the historical nested failed child until that worker exits.
network invariant: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only 172.17.61.96:12959 is published.
git: working tree remains uncommitted at the operator's request.
```

## 2026-09-03 T178 20260825A analysis-directory reset

```text
trigger: attempt 4 failed in prepare_wgs_analysis because the exact batch analysis directory already existed; sampleinfo preparation had succeeded.
target: /sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/WGS_20260825A_T7Hg38V4.1.1, resolved exactly and confirmed not to be a mountpoint.
precondition: no batch lock, Master Job or matching Master Pod existed; the directory was 27 MiB and contained the failed frozen bundle plus FASTQ symlinks.
action: archived the exact directory to a mode-0700 local backup, verified its SHA256, then removed only that batch directory. The shared sampleinfo file, Airflow/biodemo attempts, OBS and SFS were preserved.
backup: /data/airflow-WGS/backups/T178-20260825A-analysis-reset-20260903T111511Z; archive SHA256 68f78e3c137ba0a66821fffccc03c98aa1d8f5752f7d6e1cf5521cf6efc3f1a9.
concurrent_run: operator submitted the separate 20260902A run WGS_20260903_111456_397777-a1 during the reset. Its prepare stages completed and Step1 subsequently started; it does not use the deleted 20260825A directory. Codex did not submit or approve that run.
```

## 2026-09-03 T177 prepare-stage status routing repair

```text
incident: WGS_20260903_062828_0858DC-a2 reached node200 prepare_sampleinfo success at 2026-09-03T08:29:28Z, and the expected sampleinfo table exists with three data rows. The Airflow wait sensor then received HTTP 500 before sample import.
root_cause: the internal stage-status endpoint unconditionally called sync_runtime_stage_artifacts, whose allow-list covered Step1/Step3-Step7 but omitted prepare, prepare_sampleinfo and prepare_analysis. It raised ValueError unsupported runtime stage sync before the endpoint could import the sample table.
fix: prepare status stages and runtime artifact stages now use two named immutable sets with one supported-stage union. Prepare stages are accepted without pretending they have transfer/observer artifacts; prepare_analysis can still ingest its frozen binding.
tdd: endpoint regression plus all three prepare-stage sync cases failed with the production exception before the change and passed after it.
validation: .96 Docker focused tests 4 passed; full backend suite 326 passed using the complete repository-root mount.
deployment: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t177-prepare-stage-sync-r1; backend image airflow-demo/backend:t177-prepare-stage-sync. Only backend was recreated; frontend, PostgreSQL, Redis, Airflow and monitoring services were preserved.
backup: /data/airflow-WGS/backups/T177-prepare-stage-sync-20260903T084951+0000; airflow dump SHA256 a94f15108d6364213deee630f87fdee21a29168735a42d287a93e3c8ebf43dcd; biodemo dump SHA256 14f66ffac044f271d3b61eee034e872ace730359678769bbea2c0747abe4cd3d.
smoke: login, capabilities, release and run-list APIs returned 200. WGS AnalysisRun/run-attempt counts remain 2/3, the failed attempt 2 remains unchanged, and no attempt 3 was created.
recovery_boundary: attempt 2 remains a preserved failed diagnostic attempt. No task state was cleared and no attempt 3, OBS transfer or CCE workload was started by Codex.
network invariant: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only 172.17.61.96:12959 is published.
```

## 2026-09-03 T176 failed WGS resubmission and Submit refresh repair

```text
root_cause: resubmitting batch 20260825A reused its terminal failed AnalysisRun and deterministic attempt-1 DagRun. The service reset submission_phase to preparing_sampleinfo, but Airflow idempotently returned the already failed DagRun. Submit polling ignored the terminal run status, so the page remained on Preparing sample information.
backend_fix: an active duplicate remains idempotent; a successful duplicate is rejected; a failed/cancelled/unknown_interrupted duplicate creates a new attempt and DagRun ID <analysis_id>-a<attempt>, clears terminal/progress fields, and preserves the AnalysisRun identity.
frontend_fix: the five-second poll now treats failed/cancelled/unknown_interrupted as terminal, leaves the preparation screen, shows the backend error summary, and links to Run Detail.
tdd: focused backend and frontend tests first failed on attempt reuse and the stuck preparation panel, then passed after implementation.
validation: .96 Docker backend full suite 321 passed/1 skipped; frontend full suite 10 files/44 tests passed; TypeScript/Vite build passed; Compose config and fixed-network guard passed.
deployment: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t176-submit-retry-refresh-r1; backend image airflow-demo/backend:t176-submit-refresh; frontend image airflow-demo/frontend:t176-submit-refresh. Only backend and frontend-nginx were recreated.
backup: /data/airflow-WGS/backups/T176-submit-retry-refresh-20260903T082055+0000; airflow dump SHA256 2664549667b3bc6ae27c71790a7449fec684c99b67217e66e4e776e745e5be3d; biodemo dump SHA256 7e7b5bcbe580d000955648448a287aee38b73f27735f7547d90c2a3f136beaac.
smoke: login, capabilities, release and run-list APIs returned 200; the deployed asset contains the terminal sampleinfo failure view. WGS run/attempt counts remain 2/2, bio_wgs remains unpaused with 23 tasks, and no batch was submitted.
side_effects: no production WGS submission, new attempt, OBS transfer, CCE job, database migration or network change was performed during validation.
logger_contract: the current frozen Master image launches formal cloud_wgs_all with --logger rule-status from /opt/cce-pipeline/scripts/run_cce_master_job.sh. WGS profile must not duplicate this parameter; a new batch will verify the resulting Rule JSONL.
network invariant: nipt_analysis_test_net 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 may be published.
```

## 2026-09-03 T175 dashboard resource visualization

```text
scope: frontend-only presentation change; existing /api/platform/resources payload and bounded 60-point history remain authoritative.
layout: three equal cards show Analysis Node Health, SFS capacity, and SFS I/O. Duplicate Workflow Activity is removed because Run Tracker is the workflow activity source.
node: CPU and memory use accessible utilization bars; load 1/5/15 remains numeric; selected-node source time is right-aligned in the heading.
sfs: capacity uses Cloud Eye used bytes and percentage to show used/derived-total plus a utilization bar; missing inputs fall back without inventing capacity. Read/write history uses the existing last 60 samples and current IOPS.
tdd: focused resource-panel test failed on missing bars and the obsolete Workflow Activity card, then passed after implementation.
validation: .96 Node Docker frontend full suite 10 files/43 tests passed; TypeScript/Vite production build passed. Missing utilization data is explicitly tested not to report a false zero value.
deployment: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t175-resource-graphs-r1; frontend image airflow-demo/frontend:t175-resource-graphs, image ID sha256:05f39afb6aa9.... Only frontend-nginx was recreated.
preserved: PostgreSQL and Redis container IDs are unchanged; Airflow, scanner, observer, metrics collector, volumes and database records were not rebuilt or modified.
smoke: fixed-address HTTP probe passed; deployed assets contain SFS I/O and no Workflow Activity label.
pending: operator visual refresh; no Git commit is requested for T175 yet.
network invariant: nipt_analysis_test_net 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 may be published.
```

## 2026-09-03 T174 forward-only evidence repair

```text
scope: fix only future runs; no historical sample/Rule projection, backfill or mutation.
failed_attempt: WGS_20260903_062828_0858DC-a1 failed before sampleinfo. SSH authentication and host-key verification succeeded, but node200 had stale gate SHA256 359c14f... which did not dispatch prepare_sampleinfo; no analysis directory, OBS transfer or CCE workload was started.
node200_fix: backed up the old gate and atomically installed tested SHA256 b8d9765...; safe command construction now resolves the WGS sampleinfo subcommand and fixed analysis root.
backend: public WGS batch is projected once from analysis_batch/sequencing_batch; run/sample search includes batch; sample and analysis-log consumers use one safe frozen-binding path resolver; terminal missing Rule JSONL is degraded.
frontend: Samples search includes family and batch; the former sequencing-batch column is replaced by public Batch with no client-side parsing.
airflow: runner errors preserve remote stdout plus SSH stderr, avoiding the previous misleading Connection closed-only diagnosis.
validation: .96 Docker backend 320 passed/1 skipped; runner/evidence/progress 42 passed; DAG unit tests 11 passed; frontend 10 files/41 tests and production build passed after removing an accidental staging-only duplicate source file.
deployment: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t174-forward-evidence-r1; frontend image airflow-demo/frontend:t174-forward-evidence. Only application services were recreated; PostgreSQL and Redis container identities and uptime were preserved.
backup: /data/airflow-WGS/backups/T174-forward-evidence-20260903T070750+0000; airflow dump SHA256 e0fb7cb0189b5d3cbaf62484627c93ed8757944846e7c2389e625fac88056d77; biodemo dump SHA256 1bd3e95d63ecaa1d4e07a8c0edc0d4c385dcabe24487fb19c7904eb083c252.
smoke: authenticated production capabilities, release, project, run search and run detail APIs returned 200; searching 20260825A returns public batch 20260825A. bio_wgs remains the only DAG, has 23 tasks and is unpaused; execution/runtime remain true and auto-dispatch remains false.
pending: a new operator-submitted attempt. Do not resume attempt 1. The frozen Master runner, rather than the WGS profile, adds --logger rule-status to formal cloud_wgs_all; the new attempt must verify sampleinfo, analysis.log and Rule JSONL without historical projection.
network invariant: nipt_analysis_test_net 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 may be published.
```

## 2026-09-03 T173 staged submission and SFS Cloud Eye production release

```text
source: uncommitted worktree jiucheng/deploy/T168-server96-production; user will review/commit.
release: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t173-staged-sfs-r1; frontend image airflow-demo/frontend:t173-candidate, image ID sha256:954640652cd8....
submission: future WGS runs use one bio_wgs DagRun with sampleinfo review, config approval, analysis prepare and execution approval before Step1-Step6.
identity: future main DagRun ID and WGS run ID are both <analysis_id>-a<attempt>; historical/maintenance IDs remain unchanged.
resources: node200 SFS-only Cloud Eye collector is running with regional CES ReadOnlyAccess; production API returns sfs-turbo-clinical healthy and hides OBS/legacy placeholder resources.
frontend/API: Cloud Resources exposes SFS only; OBS and the obsolete missing-spool placeholder are hidden when the named SFS snapshot exists.
WGS path: production /bi/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1 is readable and clean for hanjj through mapped Git metadata; wgs-4.1.1-test is not used because it fails tracked-drift validation.
validation: .96 Docker backend full suite=318 passed/1 skipped; runner/SFS collector=38 passed; frontend=10 files/40 tests passed; production frontend build passed; deployed DagBag=23 tasks/no import errors; login and protected APIs=200; deployed assets contain all three stages and no OBS Cloud Eye label.
deployment: legacy DagRun manual__WGS_20260902_181846_20A4D2__a1 reached success at 2026-09-03T03:08:46Z before the switch. Its 18 tasks, business success state and evidence were preserved; no new AnalysisRun or DagRun was created.
runtime: execution/runtime remain true for manual submission, auto-dispatch remains false and bio_wgs is unpaused. The first three-stage production submission remains operator-controlled and has not been started.
backup: /data/airflow-WGS/backups/T173-staged-sfs-20260903T052418Z; both pg_dump SHA256 checks passed after deployment.
network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 is published.
```

## 2026-09-03 T172 `.96` frontend request recovery

```text
release: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t172-fetch-recovery-r1; frontend image airflow-demo/frontend:t172-fetch-recovery, image ID sha256:157f5ae08ff0....
cause: Dashboard mounted before deployment capabilities settled, issued duplicate deployed+wgs request waves, and retained native browser Failed to fetch errors even though Nginx recorded successful sibling requests.
fix: wait for the single deployed pipeline before first dashboard load; retry one idempotent GET after a 250 ms native network/body-read failure; keep scanner metadata when discovery-list loading fails; never retry writes or HTTP errors.
cache: index.html and SPA fallback are no-store; fingerprinted /assets files alone use immutable caching. The frontend was installed, tested and built on .96 with an independently downloaded Node v24.15.0 artifact and a fresh npm ci, not BS10610 node_modules/cache.
validation: .96 server-Docker frontend=10 files/40 tests; TypeScript/Vite build passed; authenticated capabilities/dashboard/intake/resources/release/projects all returned 200; root and health returned 200.
data: AnalysisRun=0 and Airflow DagRun=0. No batch, OBS transfer, CCE workload or Step7 was started.
runtime: WGS output root remains exactly /sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/<batch>; execution/runtime=true, auto-dispatch=false, scanner=600 seconds and bio_wgs remains unpaused for user-operated submission.
network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 is published.
```

## 2026-09-03 T171 `.96` manual WGS submission ready

```text
release: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t171-manual-ready-r1; source worktree remains uncommitted by explicit user request.
submission: Submit Run now has one Batch field; batch=20260901B will bind both WGS --batch and --analysis-batch, while the server derives WGS_20260901B_T7Hg38V4.1.1.
paths: analysis output is fixed at /sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/<batch>; Airflow request/status/evidence remains under the separate airflow-wgs/runtime root.
node200: /home/hanjj/.config/airflow-wgs/forced-command.sh, request-v4 runner, evidence bridge and transparent obsutil progress wrapper are installed; cce.yaml uses wgs-4.1.1 and the new evidence root. WGS commit 6c982817... and CCE read permission passed preflight.
gate: WGS_EXECUTION_ENABLED=true and WGS_RUNTIME_ADAPTER_ENABLED=true on both .96 and node200; bio_wgs is unpaused. WGS_SUBMISSION_PREVIEW_ENABLED=false and WGS_AUTO_DISPATCH_ENABLED=false.
scanner: wgs-intake-scanner remains the only automatic discovery mechanism at 600 seconds; it is not an Airflow DAG and cannot create AnalysisRun/DagRun while auto-dispatch is false.
validation: .96 backend+scripts 356 passed; DagBag=18 tasks/6 reschedule sensors/import errors 0; BS10610 server-Docker frontend=10 files/37 tests and production build passed; authenticated dashboard/release/intake/project APIs=200.
safety: activation created no AnalysisRun, RunAttempt or Airflow DagRun and did not start OBS, CCE, WGS or Step7. The user will submit and inspect the first batch.
network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 is published.
backup: /data/airflow-WGS/backups/T171-manual-ready-20260902T173927Z.
remaining: first real batch and real transfer-progress evidence are not yet accepted; SFS/OBS Cloud Eye metrics remain degraded.
```

## 2026-09-03 T169/T170 node metrics and compact health panel

```text
release: current -> /data/airflow-WGS/releases/20260903-wgs-4.1.1-6c98281-t170-node-tabs-r1; control commit f1c5732.
frontend: image airflow-demo/frontend:t170-node-tabs-f1c5732, image ID sha256:4d1892113632...; Analysis Node Health switches between .96/.97 and shows only CPU/load, memory, updated time and health.
collector: repeated or older node spool timestamps no longer overwrite derived CPU/rate fields; two consecutive reads of the same live spool preserved both node snapshots.
live_nodes: node-96 and node-97 are healthy; authenticated storage remains biodemo and Cloud Eye SFS/OBS is still degraded because its spool is not configured.
validation: server Docker frontend 10 files/37 tests and production build passed; backend 313 passed/1 skipped; root HTTP=200 and deployed JS contains node tabs but no node disk/network labels.
deployment: only frontend-nginx and platform-metrics-collector were recreated; PostgreSQL, Redis, volumes and Docker network were not rebuilt.
gate: all four WGS execution/preview/auto-dispatch gates remain false and bio_wgs remains paused.
network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only 172.17.61.96:12959 is published.
backup: /data/airflow-WGS/backups/T170-node-tabs-20260902T160508Z; biodemo SHA256 413e329e7a20...
```

## 2026-09-02 T168 `.96` WGS production control-plane disabled deployment

```text
host: production control plane is deployed on 172.17.61.96 as Linux user hanjj; BS10610 remains the unchanged test control plane.
release: current -> /data/airflow-WGS/releases/20260902-wgs-4.1.1-6c98281-t168-server96-disabled-r3; control commit 242f300.
database: fresh biodemo and Airflow databases use local Docker volume airflow-wgs_postgres-data on /data XFS, not /sg2; schema revision 20260901_0013, one admin, zero AnalysisRun/RunAttempt/Airflow DagRun.
runtime: result/control roots are under /sg2/14.hanjingjing/Cloud_WGS_Clinical; scanner bootstrap counted 1843 chip directories and persisted zero historical intake rows.
services: Postgres, Redis, backend, frontend, scanner, run observer, metrics collector and three Airflow services are running with zero restarts; every persistent service uses max-size=20m/max-file=3 logging.
airflow: only bio_wgs is loaded, paused, with 18 tasks and zero import errors.
smoke: anonymous protected API=401; admin login=200; Production capabilities/release/scanner/runs=200; disabled WGS submit=409; no business run or DagRun was created.
gate: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false, WGS_SUBMISSION_PREVIEW_ENABLED=false and WGS_AUTO_DISPATCH_ENABLED=false. No OBS transfer, CCE Master, WGS analysis or Step7 was started.
network: external nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only frontend is published at 172.17.61.96:12959.
frontend_acl: initial r2 allowed server subnets but rejected the operator workstation source 10.10.30.30 with nginx 403; r3 adds only 10.10.30.0/24 while retaining deny all. Root-page smoke is now mandatory in addition to /api/health.
admin_access: production.env remains owned by hanjj and non-writable by chenjc; an explicit user ACL grants chenjc read-only access for controlled credential retrieval.
node200_cce: hanjj uses cce-pipeline 0.8.1 with /bi/BioCodeHub/WGS/kubectl v1.32.9, /home/hanjj/bioinfo-cce-kubeconfig.yaml and /home/hanjj/.config/wgs/cce.yaml; both private configuration files are mode 0600. Context external can read snakemake-ns and has the required Job and Pod/log permissions.
external_gaps: Cloud Eye metric spool remains unavailable. WGS execution remains disabled until the node200 runner and one separately approved minimal batch are accepted; valid kubectl access alone does not enable either gate.
backup: /data/airflow-WGS/backups/T168-initial-20260902T140812Z; biodemo SHA256 9f7c6fddae2... and Airflow SHA256 bf5f20298d1f....
```

## 2026-09-02 T167 `hanjj`运行身份与目录迁移设计

```text
decision: 新生产运行身份固定为hanjj，使用用户提供的新RSA；不再把hanjingjing当作Linux账号名。生产切换后Airflow不按任务回退chenjc。
paths: 新WGS批次固定写/sg2/14.hanjingjing/Cloud_WGS_Clinical/WGS_Clinical/<batch>；Airflow控制面固定写同空间airflow-wgs/runtime，两个白名单根分离。
probe: 新key已只读验证可登录.96/.97/.200且三台/proc可读；node200的/home/hanjj/.obsutilconfig可读、cce-pipeline 0.8.1可执行，kubectl/kubeconfig/cce.yaml合同已验证并将私有配置权限收紧为0600。
history: 旧/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime只读保留，历史run不改绑、不删除；新request不得再写旧根。
metrics: 前端Analysis Node只展示.96/.97；.200是WGS operator。节点SSH probe与DB collector拆分，OBS/SFS仍需CES只读权限和node200 Cloud Eye spool。
status: docs/29设计已确认；request v4、runner双根、node200配置、BS10610新key安装、禁用态release和真实batch均未实施。
safety: 当前online仍为chenjc+旧runtime；execution/runtime/auto-dispatch=false，bio_wgs paused，网络和唯一12959发布未改变。
```

## 2026-09-02 T166 WGS workflow 与 Rule 投影修复

```text
release: current -> 20260902-wgs-4.1.1-6c98281-t166-workflow-rule-r2；frontend image airflow-demo/frontend:t166-workflow-rule-r3，image ID sha256:1326a0668703...；backend依赖镜像仍为sha256:49635d01a7e4...，应用代码由r2 release只读挂载。
workflow: Batch Runs与Run Detail统一消费后端唯一Step1-Step6合同，不再把Pre-calling/Variant analysis/QC当作项目workflow；历史成功批次六阶段均正确投影为success，未伪造传输速度或ETA。
rules: WGS 4.1.1规则由后端唯一映射到Pre-calling、Variant analysis、QC和Cloud delivery；208/208条Rule已有稳定execution sequence，147条sample-specific Rule从已绑定analysis.log按rule/jobid/已登记sample精确补齐，其余聚合Rule保持空值而不猜测。
terminal: cloud_finalize_delivery缺少旧logger终态事件时，仅在已验证run为success的公开投影中修正为success；原始事件证据不被伪造或覆盖。Message列不再展示No reliable ETA (0/3)，ETA仍是独立字段。
cleanup: 删除前端未使用的旧mock workflow catalog与PipelineCard/PipelineSelector，并移除前后端重复的旧WGS task百分比/标签映射；六个业务阶段文案只定义在backend/app/wgs_stage_contract.py，WGS Rule phase只定义在backend/app/workflow_phases.py。
replay: 历史WGS_20260901_031616_C74E6C attempt 1只重建Rule投影，rules_projected=208、rules_enriched=147；未重跑WGS、未重新传输、未创建Master、未执行Step7。
validation: commit 066489d；BS10610 Docker backend 312 passed；frontend 9 files/35 tests、TypeScript与Vite build通过。代码审查后的阶段fallback、已登记sample边界、analysis.log增量索引/文件替换重置和前端死映射回归均通过，最终复审无剩余发现。登录API smoke确认Batch、ended_at、六阶段、Rule phase/sample/sequence/message与terminal投影。内置浏览器因内网HTTP URL策略无法执行视觉截图验收，未绕过策略。
backup: backups/T166-workflow-rule-20260902T1655+0800；biodemo SHA256 23980d97a5a4...，Airflow SHA256 b4706e9838b2...。
gate: WGS_EXECUTION_ENABLED=false、WGS_RUNTIME_ADAPTER_ENABLED=false、WGS_AUTO_DISPATCH_ENABLED=false；bio_wgs paused。
network: nipt_analysis_test_net仍为192.168.199.0/24、gateway 192.168.199.1；唯一宿主机发布仍为172.17.106.10:12959。
```

## 2026-09-02 T165 生产前端同步、Batch/Sample检索与Finished修复

```text
release: current -> 20260902-wgs-4.1.1-6c98281-t165-production-ui-r1；前端镜像airflow-demo/frontend:t165-production-ui-sync，image ID sha256:267e5c3ee07d...。
frontend: Run Tracker和Batch Runs均显示Batch/Finished；Current stage使用Step1-Step6业务语义和权威阶段进度；WGS QC、Master image digest和旧BS10610资源卡不再展示。Samples安全表、六阶段依赖图、稳定Rule排序/换行、opaque日志、Failure Triage、WGS 4.1.1 Catalog和受控Submit表单已同步上线。
search: /api/runs和/api/dashboard/runs显式检索batch_no、analysis_id、project和Sample.sample_id/family_id；搜索不再依赖params JSON偶然命中。生产batch和sample查询均返回同一个run。
finished: finalize对新run写不可变pipeline_finished_at/ended_at；sync-airflow可用Airflow DagRun end_date补齐历史成功WGS。WGS_20260901_031616_C74E6C已回填2026-09-02T04:29:44.273615Z（北京时间12:29:44）。
database: biodemo非破坏升级到20260901_0013；迁移前biodemo和Airflow metadata备份在backups/T165-production-ui-sync-20260902T135306+0800。
validation: BS10610 Docker backend 289 passed/1 skipped，scripts 40 passed，DAG 136 passed/7 skipped，frontend 9 files/34 tests及Vite build通过；登录、capabilities、Batch/Sample/Family检索、Finished、静态资源和submit=409 smoke通过。
scanner: 继续600秒扫描，scanned=1841、error=false、intake rows=10、2226 rows=0；AnalysisRun仍只有1条且无活动run，自动dispatch=false。
gate: 已按约定关闭WGS_EXECUTION_ENABLED和WGS_RUNTIME_ADAPTER_ENABLED，并暂停bio_wgs；本次未启动OBS、CCE、WGS或Step7。
external_gaps: Step1/Step5透明progress代码已存在，但node200尚未安装/启用wrapper，故当前没有真实速度或ETA；172.17.61.96/.97的9100拒绝连接，Cloud Eye SFS/OBS spool不存在，资源页如实显示degraded；admin Step7合同/UI已实现但尚未进行生产执行验收。
network: nipt_analysis_test_net仍为192.168.199.0/24、gateway 192.168.199.1；唯一宿主机发布仍为172.17.106.10:12959。
```

## 2026-09-02 T163 登录、T7发现与在途状态修复

```text
auth: PlatformCapabilitiesProvider只在SessionProvider确认已登录后挂载；登录页不再提前请求受保护capabilities并缓存AUTH_REQUIRED。生产API在未登录时仍正确返回401，登录后由新provider重新加载。
scanner_ui: Dashboard改为产品语义“自动发现新的测序批次；分析任务需人工确认”，以三个状态标签显示10分钟周期、本轮1841个批次目录和最近更新时间；不再暴露BarcodeStat实现细节。
scanner_data: 2226th_20260830B_E250197447确认无关联AnalysisRun后，在受保护备份后单事务删除；生产env加入精确ignore，立即重扫后该行仍为0。扫描仍计数1841，AnalysisRun=1、Airflow DagRun=1，自动提交仍关闭。
runtime: WGS_20260901_031616_C74E6C同attempt的Step4权威状态已success。首次Step5在结果archive下载79.86%时报`no space left on device`；旧worker退出后以相同request SHA归档为retry-1并保留obsutil checkpoint，未重跑Step1-Step4。retry-1现已success，Airflow Step5 start/wait均success，当前正在Step6 materialize；最终成功尚未确认。
race_guard: 后端只在run仍处于Step4假失败且同identity的Step4成功状态文件存在时允许Step5注册恢复，真实Step5失败不会被普通注册掩盖。Step4/Step5 start均按runner返回的明确`retry_no`等待新generation可见，不比较跨主机时间，也不让sensor读取上一代failed。
release: current -> 20260902-wgs-4.1.1-2499749-t163-ui-intake-recovery-r4；frontend image airflow-demo/frontend:t163-ui-intake-recovery@sha256:23f916eb9c60...。只滚动重建应用/Airflow服务，不迁移DB、不删除volume或网络。
validation: BS10610 backend 252 passed/1 skipped；bio_wgs 9 tests、runner 30 tests、py_compile和import_errors=0；frontend 9 files/32 tests及Vite build通过。health=200，匿名capabilities=401符合安全合同。
branch_validation: 待合并完整候选在BS10610 Docker中为backend 283 passed/1 skipped、scripts 40 passed、bio_wgs 10 passed、frontend 9 files/33 tests及Vite build通过，Compose config和`git diff --check`通过。
network: nipt_analysis_test_net仍为192.168.199.0/24、gateway 192.168.199.1；唯一宿主机发布仍是172.17.106.10:12959。
gate: 当前获批真实batch尚未完成，因此execution/runtime和DAG现状未在本次中途关闭；自动dispatch=false。批次终态后再执行禁用态门禁切换。
```

## 2026-09-02 T161 生产WGS 4.1.1接入与仓库整理

```text
wgs: 用户最终确认生产云端流程继续使用共享仓库wgs-4.1.1；只读审计为dev_CJC_4.1.1_cloud@6c982817614db6a1157b6f287427ddf01ac91827，该提交已统一structured ANALYSIS_COMPLETE合同。wgs-4.2.0只用于测试。
catalog: 生产release为wgs-4.1.1-6c98281；BS10610/node200共享路径分别为/mnt/.../wgs-4.1.1和/bi/.../wgs-4.1.1。生产API不能选择4.2.0。
prepare: platform=T7；sequencing_batch与analysis_batch分别传给--batch/--analysis-batch；4.1.1无--algo参数。服务端派生最终batch_no=WGS_<analysis_batch>_T7Hg38V4.1.1。
frontend: Submit表单展示V4.1.1/6c98281和T7，不显示测试版本或variant caller；此前Batch、业务阶段、精确进度、安全Samples、Rule图、opaque日志与失败诊断修复均保留。
validation: 生产4.1.1纠正后BS10610 Docker backend 280 passed/1 skipped；scripts 38 passed；Airflow DagBag import_errors=0、bio_wgs=18 tasks/6 reschedule sensors/paused-on-creation；frontend 9 files/32 tests及Vite build通过。此前PostgreSQL 15迁移往返、Compose解析和固定网络检查继续通过。
runtime: 未部署、未切current、未启动OBS/CCE/WGS/Step7；在线T152状态未改变。
network: 只读复核nipt_analysis_test_net=192.168.199.0/24、gateway=192.168.199.1；仅frontend发布172.17.106.10:12959。
repository: 主功能PR #4 merge 17c0f97；错误4.2.0路径PR #6未部署并已由生产纠正PR #8完整覆盖。PR #8 merge commit为6046a280db1271ae41575113cacd431e990a74c2，root main已ff-only同步。
```

## 2026-09-02 T159 WGS提交、传输进度与失败日志合同修正

```text
submission: 撤回三步draft preview作为生产入口；新增catalog受控POST /api/wgs/runs。DAG prepare按WGS原生语义执行sampleinfo→analysis，只有batch_root/sampleinfo.tsv中的最终selection.kept会进入公开Samples，FASTQ扫描结果和pending不再预先冒充分析样本。
transfer: 新增Airflow自有透明obsutil wrapper和node200 runner聚合，合同为wgs-runtime.transfer-progress.v1。wrapper保留原命令stdout/stderr/exit code，只写请求级脱敏bytes/files/speed/ETA；解析失败只降级监控，不改变传输结果。cce-pipeline旧v1仅作为读兼容，不再是部署门禁。
logs: 取消失败Rule的SFS路径registry要求；只从已经绑定并镜像的analysis.log最后2MiB按snakemake job ID/rule name生成不超过64KiB摘要，完整日志继续通过后端自动生成的opaque key读取，用户不配置key且logger路径不被信任。T160将日志API改为64KiB分块倒读，单次最多8MiB/1000行并返回file_size/truncated，不再把完整analysis.log载入内存。
release: catalog仍保持wgs-4.1.1-2499749。共享WGS HEAD 6c982817...只作为待审计候选；等待WGS更新完成后再一次性更新commit/release ID，不静默跟随HEAD。
validation: BS10610 backend 279 passed/1 skipped（含T160大日志RED→GREEN）；runner/adapter/timing 51 passed；前端在BS10610无网络Docker容器内使用Node 22.22.2/npm 10.9.7完成Vitest 32 passed及Vite production build；git diff --check和Python compile通过。测试证据在/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/t159-20260902。本机Node结果不作为验收证据。
network: BS10610只读preflight确认外部`nipt_analysis_test_net`仍为`192.168.199.0/24`、gateway `192.168.199.1`，现有容器地址均唯一且在网段内；候选Compose不声明IPAM或静态容器IP，只复用该外部网络。唯一宿主机端口映射仍为前端`172.17.106.10:12959`；测试容器使用`--network none`，未创建或修改Docker网络。
deployment: 本轮未部署、未切current、未修改在线T152开关或DAG pause，未启动OBS/CCE/WGS/Step7。node200仍需在disabled release阶段安装wrapper并把受控operator config的obsutil_bin指向wrapper。
```

## 2026-09-02 T153-T158 WGS生产前端开发检查点

```text
code: migration 20260901_0013、权威stage/Rule状态、安全日志索引、Batch/业务阶段UI、Samples、Rule阶段图、三步draft API/UI、资源快照和admin Step7合同已在T146 worktree实现。独立审查后的提交/DagRun幂等、Step7 action绑定、draft过期/源漂移、严格transfer v1、terminal单调和WGS QC残留均已修正。
logs: node200 evidence bridge现在增量同步Rule JSONL和绑定run的analysis.log，并在Master终态用只读reader补齐。
validation: BS10610 backend 298 passed/1 skipped；scripts 37 passed；bio_wgs DAG 8 passed且DagBag为18 tasks/paused-on-creation/import_errors=0；临时PostgreSQL 15完成0013 upgrade/受控downgrade/upgrade。此前记录的本机Node结果不作为验收证据；T159已在BS10610无网络Docker容器内重新完成32 tests及TypeScript/Vite build。BS10610离线镜像`airflow-demo/frontend:t153-production-ui-disabled`（sha256:c7e49e0a69d40570dfafd3e20b3a66308f7a6f726ed7623127d004bb3f9ba202）的nginx及无端口HTTP smoke通过。独立只读审查最终为Critical/Important/Minor均0。
progress: 没有cce-pipeline.transfer-progress.v1时Step1/Step5明确返回progress_available=false，不伪造速度或ETA；Step3使用结构化completed/total/percent。
blocker_draft: 当前WGS sampleinfo子命令只生成临床metadata，不生成FASTQ配对和pending预览；生产draft worker不得自行复制业务选择逻辑。WGS_SUBMISSION_PREVIEW_ENABLED默认false，API/UI fail closed，等待WGS只读preview合同或批准的adapter。
blocker_rule_stderr: analysis.log和stage worker日志已使用opaque索引；失败Rule stderr仍缺少经审查的log-key到SFS相对路径registry，未开放任意logger路径读取。
blocker_release: catalog仍绑定wgs-4.1.1-2499749；共享WGS仓库当前HEAD为6c982817614db6a1157b6f287427ddf01ac91827。不得静默改绑或启用。
deployment: 本轮尚未迁移生产DB、重建服务或切换current；未启动OBS/CCE/WGS，未执行Step7。当前在线仍为T152 release，旧生产env的execution/runtime=true且现有bio_wgs为unpaused；本轮disabled candidate已用四个门禁显式false解析验证，不擅自覆盖在线状态。
network: Compose解析只发布frontend 172.17.106.10:12959；外部nipt_analysis_test_net实测192.168.199.0/24、gateway 192.168.199.1；scanner默认600秒。
```

## 2026-09-01 T152 - Step4 Master时序修复已部署，当前批次被WGS marker合同阻断

```text
t152_airflow_fix: node200 runner只在Step3已success且Master与冻结binding完全一致时，将"Step4 requires a successful Master Job"作为短暂状态每5秒重试，最长600秒；其他Master错误继续硬失败。
t152_retry_generation: 已退出的failed step4_publish可在相同request SHA下归档status/worker/log到history/step4_publish/retry-N后重启；活动worker、请求漂移和其他stage不允许该行为。
t152_backend: 同attempt重新登记已知Master完成竞争时恢复业务状态为publishing并写run.step4_publish_recovered审计；后续真实Step4 terminal failure会写回biodemo为failed和错误摘要，前端不再滞留publishing；Step4 repair不再依赖wgs-master-*前缀，而使用Step3绑定后生成的canonical event identity。
t152_deployment: current -> 20260901-wgs-4.1.1-2499749-t152-step4-recovery-r8；Airflow实现commit为29c8378b2b4e5cf860e7978d9e23233f710035af和1bd7530f2a55bab530475fffb48eeabb025fea21。backend/API/scheduler/worker和共享runner已更新，数据库、volume、网络、WGS仓库和冻结bundle未修改。
t152_recovery: 原DagRun同attempt只清除了Step4、Step5、Step6、finalize和release_leases。Step1、Step2、Step3仍success；Master仍是cce-master-79c59ff6401e15d76aa5，UID 8ef69ad6-96cd-4dd2-a94a-b214287af1d2，Complete时间08:26:26Z；没有重新上传FASTQ或创建Master。
t152_new_blocker: 普通Step4已经越过Master前置检查，但在OBS交付核验时报ANALYSIS_COMPLETE is invalid。OBS marker是149-byte schema-1 JSON且身份/status=PASS正确；冻结WGS 2499749的cce_delivery.py仍只接受字面量status=PASS\\n。这是WGS内部producer/consumer合同不一致，不是cloud_finalize_delivery重复执行，也不是Airflow Master时序问题。
t152_safety_stop: 按本任务“不修改WGS仓库或冻结bundle、不修改OBS/SFS”边界，未热补丁bundle、未覆盖OBS marker、未使用CRAM repair、未再次清Task。当前DagRun再次failed于普通Step4；Step5-Step6未执行，最终成功尚未达成。
t152_backup: backups/T152-step4-recovery-20260901T173906+0800；biodemo.dump SHA256 08af9e4f6a50945affb355380858a4ab11653356dbfa43fa44fdccf6174e6c3e，airflow.dump SHA256 3ac29e63f3dcb4dba401a2490e8485acd6c246550a2b9955e6330790f4da4256。
t152_validation: runner 28 passed；backend 250 passed；DAG import errors=0；Compose config和network preflight通过；生产API已显示failed/step4_publish及真实错误。网络仍192.168.199.0/24、gateway 192.168.199.1，仅172.17.106.10:12959发布。
```

## 2026-09-01 T151 - exclude YF non-clinical samples

```text
t151_behavior: sample IDs beginning with uppercase YF are ignored before eligible/add-on/pair-issue accounting. YF-only is no_new_wgs and an incomplete YF pair does not trigger needs_review.
t151_fingerprint: name fingerprint is v3 and excludes YF names; an equivalent old v2 fingerprint is accepted once so existing ready rows upgrade without false drift. No DB field or migration was added.
t151_production: 2222 contained 192 YF FASTQ entries (96 pairs) and changed from ready/96 to no_new_wgs/0. 2223/2224/2227 remain ready with 12/8/10 eligible pairs; 2221/2225 remain no_new_wgs and 2226 retains its prior needs_review.
t151_side_effect_gate: AnalysisRun, RunAttempt and Airflow DagRun counts remained 1/1/1. WGS_20260901_031616_C74E6C stayed running in step3_monitor with the same attempt and DagRun.
t151_release: current -> 20260901-wgs-4.1.1-2499749-t151-yf-filter-r6; only wgs-intake-scanner was recreated. The scanner bind-mounts only the release backend and /bi/fastq/T7_Fastq read-only.
t151_source: scanner policy, regression tests and contracts are committed as 9ab2dd2c95528875b11cf8b82a7e4350eedb08b8.
t151_backup: backups/T151-yf-filter-20260901T162127+0800/biodemo.dump SHA256 ed7dfe046d19a53b6cee0f52da2e0925e5e58e844eeca19d2b37848cb52d0ae3.
t151_validation: focused scanner 18 passed; full backend 247 passed / 1 skipped; API reports schedule_seconds=600, auto_dispatch=false and 1837 scanned directories with no scanner error.
t151_network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only frontend publishes 172.17.106.10:12959.
```

## 2026-09-01 T150 - T7 FASTQ scanner repair

```text
t150_behavior: scanner classifies regular files, hard links and symlinks only by the direct entry name; it never resolves or reads FASTQ targets. Fingerprint v2 contains chip/batch/BarcodeStat metadata and sorted eligible names, while add-on -S\d+ samples remain excluded.
t150_production: 2227th_20260830C_E250197831 is ready with 10 complete pairs; 2222/2223/2224 are ready with 96/12/8 pairs; 2221/2225 remain no_new_wgs; 2226 retains its pre-existing needs_review drift state.
t150_side_effect_gate: before and after deployment, AnalysisRun=1, RunAttempt=1 and Airflow DagRun=1. WGS_20260901_031616_C74E6C attempt 1 stayed running in step3_monitor with the same DagRun; no automatic analysis was created.
t150_release: current -> 20260901-wgs-4.1.1-2499749-t150-t7-scanner-r5; only wgs-intake-scanner and frontend-nginx were recreated. Tested frontend image airflow-demo/frontend:t150-t7-scanner-10m is sha256:cef9e1117810e0482b9099281d00dcea329a47e19e838959b004c24a4e386cdb.
t150_source: scanner/frontend implementation is commit b5afe9c0349557ff710e0f1ee6f3bfc49a393d36. The T149 r4 rollback scanner files were restored byte-for-byte from its parent commit after a test staging symlink was detected, and the staging link was removed.
t150_backup: protected biodemo backup is backups/T150-t7-scanner-20260901T151336+0800; biodemo.dump SHA256 b606f3f284ffc7d72e992cae79534c5d3580f20dcb6890d2902dbdb2f2026380.
t150_validation: BS10610 backend 243 passed / 1 skipped; frontend 31 passed plus TypeScript/Vite build; API reports schedule_seconds=600 and auto_dispatch=false. Scanner only mounts /bi/fastq/T7_Fastq read-only.
t150_network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only frontend publishes 172.17.106.10:12959.
```

## 2026-09-01 T149 - Step3 monitor repair and in-flight takeover

```text
t149_run: WGS_20260901_031616_C74E6C attempt 1 remains running in the original DagRun manual__WGS_20260901_031616_C74E6C__a1.
t149_preserved: Step1 upload and Step2 Master remain success/try 1; the existing cce-master-79c59ff6401e15d76aa5 remains Running. No OBS upload, Master Job, analysis ID, attempt or run ID was recreated.
t149_repair: runner status writes are unique-temp/fsync/atomic/monotonic; accepted precedes worker launch; Step3 carries frozen Master identity and cce-pipeline status. Backend validates the exact binding rather than a name prefix, accepts incomplete transitions as not-ready, and recovers the same failed business attempt with an audit event.
t149_evidence: observer is active/healthy on cce-run-650a0767d41b3157. Authenticated API shows current Rule MEI_MEICall, 41 Rule rows (19 success, 2 running, 20 planned), and only the bound Master workload.
t149_airflow: start_step3_monitor is success/try 2 and wait_step3_analysis is up_for_reschedule/try 2. The original DagRun will advance to Step4-Step6 only after the real CCE terminal state; no manual high-frequency polling remains.
t149_release: current -> 20260901-wgs-4.1.1-2499749-t149-step3-recovery-r4; deployed runtime code commit b7730bc1a09481f67663b2c3d7f37e50b5770b93.
t149_backup: pre-takeover biodemo, Airflow metadata, runner state and binding are retained at backups/T149-step3-recovery-20260901T132953+0800 with verified SHA256 checksums.
t149_network: nipt_analysis_test_net remains 192.168.199.0/24, gateway 192.168.199.1; only frontend publishes 172.17.106.10:12959 and the scheduler is not paused.
```

## 2026-09-01 T148 - historical worktree and branch cleanup

```text
t148_worktrees: only the root main worktree and D:/pipeline/airflow-demo-worktrees/T146-wgs-081-manual-run remain; seven completed/historical secondary worktrees and the unregistered T133 staging-artifact directory were deleted.
t148_branches: only local main and jiucheng/platform/T146-wgs-081-manual-run remain; 54 local historical branches and 16 remote historical branches were deleted. GitHub now exposes only origin/main.
t148_discarded: the obsolete T096 root edits, untracked airflow-snakemake-ppt directory and T133 local staging artifacts were explicitly deleted under the user's cleanup authorization and are not recoverable from the working tree; committed history remains in Git objects until normal repository maintenance removes it.
t148_preserved: T146 .artifacts and its active WGS analysis state remain untouched; the T146 worktree is synchronized to the merged main baseline.
t148_runtime: no Airflow, WGS, CCE, OBS, database, Docker service, network or production-run operation was performed.
```

## 2026-09-01 T147 - Airflow worktree reconciliation

```text
t147_main: origin/main is cf9b716bf2b712fc802e9d6d44d500ca998d4773 before this documentation-only PR; it already contains the T146 WGS production checkpoint.
t147_fast_forwarded: clean T132 and T145 worktrees were fast-forwarded to origin/main without rewriting history.
t147_equivalent: T127 dashboard, frontend compatibility, review fixes and WGS rule-phase branches have patch-equivalent commits already present in main; they were not merged again.
t147_preserved: the dirty T096 documentation/PPT worktree and its five local changes were left untouched; the clean T128 NIPT manual-scan branch remains isolated because it is obsolete for the WGS-only platform.
t147_active: T146 production analysis WGS_20260901_031616_C74E6C remains under Airflow scheduled monitoring; this repository reconciliation does not restart, cancel, pause or otherwise alter the run.
t147_scope: no application, DAG, deployment, database, Docker network or runtime configuration changes; only repository state documentation is included in the PR.
```

## 2026-09-01 T146 - WGS 2499749 clean reanalysis（运行中）

```text
t146_release_contract: WGS V4.1.1 commit 2499749ce7fd200d4269d1ee03d7b6a4e8d5bb68，release wgs-4.1.1-2499749；BS10610和node200共享仓库HEAD一致。
t146_cleanup: 旧analysis WGS_20260831_194429_145176的biodemo业务行、11个Airflow DagRun、Airflow runtime、三处task evidence、SFS run/linkage、OBS FASTQ/result和CCE Job/Pod/batch lock均已精确清空；只保留一条受控清理审计。
t146_backups: 清理前biodemo和Airflow metadata均已生成mode 0600 pg_dump备份；不删除用户、scanner singleton、Docker volume或network。
t146_active_run: 前端等价API新建并提交WGS_20260901_031616_C74E6C attempt 1，DagRun manual__WGS_20260901_031616_C74E6C__a1，未复用旧analysis/run-id。
t146_checkpoint: validate和prepare成功，Step1输入上传正在运行；前端/API显示15% input_transfer.wait_step1_upload。用户要求停止人工高频轮询，后续由Airflow 5秒reschedule sensor和Step3按任务激活的observer持续同步。
t146_runtime: node200 cce-pipeline 0.8.1，resolved Master digest sha256:965473cf89539ec67869cb38265f1416de508aa71ab5f35ad9be6a979548dab0。
t146_gates: WGS_EXECUTION_ENABLED=true、WGS_RUNTIME_ADAPTER_ENABLED=true、WGS_AUTO_DISPATCH_ENABLED=false；bio_wgs已unpaused以运行本次手工批次。
t146_network: nipt_analysis_test_net保持192.168.199.0/24、gateway 192.168.199.1，只发布172.17.106.10:12959。
```

## 2026-09-01 T146 - WGS cdee32c / cce-pipeline 0.8.1 manual run（运行时阻断）

```text
t146_release_contract: WGS V4.1.1 commit cdee32c9d3c689f4af6ea8a0f7a8296f79c10a1d, release wgs-4.1.1-cdee32c；BS10610和node200共享同一仓库，只有docs/下允许的未跟踪文档。
t146_runtime: node200 /bi/software/mamba/envs/WGS/bin/cce-pipeline 为0.8.1；Airflow不校验其版本，只记录prepare产生的resolved runtime。
t146_prepare_fix: Airflow从batch_no WGS_20260825A_T7Hg38V4.1.1提取sequencing batch 20260825A并传入--batch；--outpath仍是Airflow attempt runtime下的WGS_Clinical，不重建旧/sg2/.../wgs_test目录。
t146_validation: BS10610 runner 19 passed、backend 227 passed、DAG 10 passed、Compose/network contract 5 passed；frontend 31 passed且TypeScript/Vite build通过；Step3多行stdout解析回归后scripts全量22 passed。
t146_intake: 3对FASTQ软链接已原样复制到Airflow受控intake，两端可见；软链接源文件保持不变。
t146_cleanup: 初始旧批次SFS/OBS和CCE状态已清理；真实attempt 5/7失败后产生的Master、空SFS evidence stub和批次lock也已按精确身份清理。OBS input保留已上传FASTQ，OBS result为空；旧本地分析目录仍保留但从未被新流程读取或重建。
t146_deployment: current已切换到20260901-wgs-4.1.1-cdee32c-t146。真实run保留为attempt 7 failed，前端/API可见；发现兼容性阻断后BS10610和node200两个execution gate已恢复false，bio_wgs已重新paused，自动提交仍false。
t146_airflow_fix: Step3_status.sh允许kubectl提示后最后一行JSON；runtime gate从后向前解析最后一个合法JSON并严格校验。修复后Step3正确报告Master FAILED，不再被JSONDecodeError掩盖。
t146_recovery_gate: backend的resume/rerun_failed现同时检查execution和runtime adapter gate；生产复核HTTP 409、attempt保持7且attempt8 DagRun为0。cancel仍可用。
t146_blocker: node200 cce-pipeline 0.8.1的Step2在START前创建run_root/evidence/<run_id>/jobs.ndjson；当前resolved Master image仍为cce-pipeline 0.7.0系列并拒绝“已有run目录但缺run-id”，Master立即退出。须先发布/选择与0.8.1合同一致的Master镜像或修正该顺序，Airflow不得继续重试。
t146_scanner: Compose命令改为读取WGS_INTAKE_SCAN_INTERVAL_SECONDS；生产受保护值为600秒，保持10分钟扫描且不新增记录膨胀。
t146_network: 必须继续保留nipt_analysis_test_net 192.168.199.0/24、gateway 192.168.199.1，且只发布172.17.106.10:12959。
```

## 2026-08-30 T145 - scanner 稀疏入库与 event-driven observer

```text
t145_release: current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260830-wgs-4.1.1-observer-lifecycle-disabled-t145。
t145_release_cleanup: 验收后已用无网络root容器精确删除T142和T143旧release；releases目录只保留T145。旧release目录删除不可就地恢复，代码仍可从Git重建。
t145_services: 旧wgs-observer已停止并移除；wgs-intake-scanner只读T7根并每1800秒扫描，wgs-run-observer只读evidence并在无active/draining attempt时阻塞PostgreSQL LISTEN/NOTIFY。
t145_sparse_intake: 生产首次和第二次扫描均统计1830个匹配目录，wgs_intake_batch仍为0；bootstrap_ignored和waiting_barcode_stat不再入库。
t145_cleanup: 清理前1830行中关联analysis数为0；受保护单事务删除1830个batch和1个scanner state。清理后AnalysisRun、observer state均为0。
t145_backup: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/backups/t145-before-sparse-observer-20260830T045310+0800/biodemo.dump，SHA256 6cd7026498748c2e6ec231f01ebde7867c5bee3d2e97827d24b3bf36bc11b4e8。
t145_database: biodemo Alembic revision 20260830_0012；populated临时库完成0011->0012、1830行清理和零副作用验收后已删除临时库。
t145_observer_idle: 生产wgs-run-observer启动后无活动分析，10分钟日志字节数为0，不读取binding/runtime/transfer也不输出空心跳。
t145_validation: 当前release在BS10610通过backend 227 tests、DAG 7 tests、Compose/network 5 tests、frontend 30 tests及TypeScript/Vite build；隔离PostgreSQL实测4个attempt通知全部按identity到达；登录、health、scanner-state和intake API HTTP smoke通过。
t145_frontend: airflow-demo/frontend:t145-wgs-observer-lifecycle-disabled -> sha256:21468c83853c873559b4805c65f58b49cf72c86a4aca5f3a2415cea6db95579a；UI包含“本轮扫描”和“CCE监控尚未启动”。
t145_gates: WGS_EXECUTION_ENABLED=false、WGS_RUNTIME_ADAPTER_ENABLED=false、WGS_AUTO_DISPATCH_ENABLED=false，bio_wgs paused且DagRun=0。
t145_network: 外部nipt_analysis_test_net保持192.168.199.0/24、gateway 192.168.199.1；仅frontend发布172.17.106.10:12959。
```

## 2026-08-29 T143/T144 - T7 scan-only 与 Step4 repair

```text
t143_baseline: WGS V4.1.1 commit 1656b5d7a6e2f24242c38149f6d1c92ac266cd37, release wgs-4.1.1-1656b5d; Airflow不安装或校验cce-pipeline 0.7.1。
t143_scanner: wgs-observer独立线程按扫描开始时间每1800秒只读扫描/bi/fastq/T7_Fastq；首次completed目录bootstrap_ignored，未完成目录waiting_barcode_stat；eligible/add-on配对、fingerprint漂移和PostgreSQL advisory lock已实现。永久bootstrap_ignored只更新扫描时间，不再重复枚举FASTQ。
t143_side_effect_gate: WGS_AUTO_DISPATCH_ENABLED=false；scanner不运行sampleinfo、不建分析目录、不创建AnalysisRun/DagRun、不访问OBS/CCE。
t143_data_api_ui: migration 20260829_0011增加nullable intake、scanner singleton和maintenance action；API/UI只暴露芯片、批次、计数和状态，不暴露sample ID、源路径或fingerprint。
t144_repair: operator/admin可请求固定cram Step4维护；后端从冻结binding生成确认串，同bio_wgs和同attempt执行；viewer与任意参数被拒绝，重复点击返回同一操作。
t144_disabled: WGS_EXECUTION_ENABLED=false、WGS_RUNTIME_ADAPTER_ENABLED=false时repair在Airflow/SSH前返回409。真实0.7.1修复未执行。
t143_local_remote_validation: BS10610 backend 217 passed/1 skipped，scripts 17 passed，DAG/Compose合同通过；frontend 30 tests、TypeScript和Vite build通过；临时PostgreSQL 0010->0011->0010->0011迁移往返及SET NULL外键检查通过。
t143_deployment: current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260829-wgs-4.1.1-t7-scan-disabled-t143；biodemo revision 0011。bootstrap得到1817 bootstrap_ignored和11 waiting_barcode_stat，随后新发现1个no_new_wgs。
t143_cycle_acceptance: stable baseline 10:20:30.971949 UTC；cycle1 10:50:30.972362 / 516ms；cycle2 11:20:30.972623 / 1216ms。两次均保持1817 bootstrap_ignored、11 waiting、1 no_new_wgs，business run/attempt/maintenance和Airflow DagRun均为0。
t143_network: 必须保留外部nipt_analysis_test_net 192.168.199.0/24，gateway 192.168.199.1，且只发布172.17.106.10:12959。
```

## 2026-08-28 T142 - single WGS release disabled production deployment

```text
t142_target: replace the Airflow development snapshot catalog with one server-owned WGS release, request v3, release-bound observer/API/UI, and no Airflow cce-pipeline version gate.
t142_baseline: the user approved shared WGS commit 1778fcabd99b5253aa90cd410112dc2f78e0c51a and release wgs-4.1.1-1778fca; BS10610 and node200 resolve the same commit and only docs/WGS_V4.1.1_LOCAL_CCE_RESULT_CONSISTENCY_TEST_REPORT.md is untracked.
t142_release: BS10610 current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260828-wgs-4.1.1-single-release-disabled-t142; schema-3 release wgs-4.1.1-1778fca is the only task binding contract.
t142_implementation: request v3, fixed-repository prepare validation, frozen bundle reuse, migration 0010, release-bound observer/ETA/API/UI and removal of obsolete candidate copy adapters are deployed.
t142_validation: isolated BS10610 backend 202 passed, scripts 16 passed, Airflow focused DAG tests plus py_compile/DagBag passed with only one 18-task paused bio_wgs, frontend 27 tests and production build passed, temporary and production PostgreSQL 0009-to-0010 migrations passed, and disabled HTTP create/detail/submit-409 smoke passed before exact synthetic cleanup.
t142_runtime_ssh: node200 noninteractive SSH was blocked by unconditional conda initialization in ~/.bashrc. A preserved backup was made and a noninteractive early-return guard plus fixed /usr/local/bin PATH restored Airflow command execution; host t640, WGS HEAD 1778fca, allowed docs-only drift and invalid forced-command rejection were verified without running a WGS stage.
t142_platform_state: biodemo revision 20260827_0010; 1 admin and zero sessions/runs/attempts/snapshots/issues/transfers/Rule events/states/workloads/audit/cursors. Airflow has zero DAG runs. Network remains 192.168.199.0/24 and only frontend publishes 172.17.106.10:12959.
t142_frontend: airflow-demo/frontend:t142-wgs-4.1.1-single-release-disabled -> sha256:59cbfce7c8537c3a943f6c35a1ccea8bcfe6dc2ae1bba02fbe0d6ff6bb8b0903; deployed index/CSS/JS SHA256 match the locally tested dist.
t142_cleanup: after all disabled smokes passed, the exact T141 release and the redundant failed-attempt T142 backup were irreversibly removed with no-network root containers; releases contains only T142 and backups retains only t142-before-single-release-20260828T002349+0800.
t142_safety: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false and bio_wgs paused remain mandatory. No OBS transfer, CCE workload, WGS source edit or cce-pipeline install/update is authorized.
```

## 2026-08-27 T141 - WGS 4.1.1 Master Rule evidence bridge

```text
t141_release: BS10610 current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260827-wgs-4.1.1-disabled-t141; releases contains only this directory.
t141_master_runtime: pinned Master digest 815d70a6... contains Snakemake 9.24.0+biosan1 and snakemake_logger_plugin_rule_status; the formal cloud_wgs_all command adds --logger rule-status while preserving analysis.log. node200's local Snakemake is not part of CCE execution.
t141_event_contract: the installed logger writes schema 1 JSONL under <run_root>/evidence/<run_id>/rule-status/raw/*.jsonl and labels attempts as attempt-N. The observer now accepts positive integers, numeric strings and attempt-N without changing the database attempt identity.
t141_bridge: node200 has no direct /workspace SFS mount. Step3 therefore uses kubectl to copy only complete JSONL lines by per-stream byte offset into /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/<analysis_id>/attempt-N. After Master exit, an exact one-shot reader Job mounts only the workspace PVC read-only, copies the final increment and is deleted.
t141_scope: Master Job/Pod remains the only Kubernetes workload exposed by API/UI. The reader is internal transport plumbing; Worker Pods are not enumerated or persisted.
t141_failure_policy: evidence-copy failure marks stage monitoring_health=degraded but does not fail WGS. Missing terminal Rule events remain unknown_interrupted; batch success still depends on WGS and result delivery gates.
t141_validation: BS10610 passed backend 193 passed/1 skipped, scripts 17 passed, no-bytecode syntax check, HTTP health, runtime/release SHA256 equality, observer clean polling, one paused bio_wgs and zero DAG import errors. Master image Python 3.11.9 path smoke passed. Real kubectl reader/Rule ingestion awaits the separately approved T140 batch.
t141_execution_gate: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false and bio_wgs paused remain unchanged.
```

## 2026-08-26 T139 - WGS 4.1.1 disabled production release

```text
t139_release: BS10610 current -> /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260826-wgs-4.1.1-disabled-t139.
t139_wgs_source: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1, clean commit 3489b3958869e5cfab983aca1eb9c7f158c06dff.
t139_snapshot: wgs-v4.1.1-candidate-3489b39-64d50022; manifest SHA256 9b1bfe00ebf7e8ed693f1e9eb17ec05174aa43b04900802d67e54f50dc27f52e; prepare/config.yaml is excluded.
t139_cce_contract: cce-pipeline 0.5.0, source commit 70a9a737c62865f232ed0b49f682aa7c9a69e467, formal wheel SHA256 43a4ab478e8b8810b1691bb755e54336b0bc8fd86a16d4fed9be3783036e1756, profile wgs-4.1.1-r1.
t139_dag: only bio_wgs is loaded; it has 18 Step1-Step6 project tasks, no schedule, and remains paused. The old bio_wgs_cce, bio_wgs_intake_scan and bio_wgs_onprem sources and metadata are removed.
t139_ssh: Airflow runs ssh -tt -F /opt/airflow/ssh/config wgs-node200; the protected config fixes node200 172.17.61.200, user, RSA IdentityFile, known_hosts, BatchMode, IdentitiesOnly and StrictHostKeyChecking. This is direct SSH config login, not an authorized_keys forced-command key.
t139_ssh_key: the user-provided RSA is installed outside the release at /home/chenjc/.config/airflow-wgs/ssh-node200/id_rsa, owned by Airflow UID 50000 and mounted read-only. It is absent from Git, images, releases, databases and logs.
t139_runtime_path: BS10610 /mnt/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime maps to node200 /sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-wgs/runtime; a cross-host marker probe passed.
t139_data: biodemo migration 20260826_0009; one administrator retained; auth sessions and demo run/sample/event/transfer/workload/audit state cleared; Redis state cleared; database and Redis volumes retained.
t139_cleanup: releases contains only 20260826-wgs-4.1.1-disabled-t139 and backups is empty; the removed old releases/demo-state backups are not recoverable on host. Production WGS sources, inputs, results, database/Redis volumes and Docker network were not removed.
t139_network: existing external nipt_analysis_test_net remains 192.168.199.0/24; only frontend publishes 172.17.106.10:12959.
t139_frontend_image: airflow-demo/frontend:t139-wgs-4.1.1-disabled now resolves to sha256:f64b1ed3b2287b5cfa8b12d0a23732339a84a1aeed49a4219de671c2f10a32e6; the image deletes inherited demo assets before copying the fixed WGS build and exposes only the current JS/CSS pair.
t139_final_tests: backend 193 passed; node/runtime scripts 14 passed; deployment contract 5 passed; live Airflow DAG contract passed with 18 tasks and zero import errors; frontend 27 passed plus TypeScript/Vite build; Compose/network/HTTP/auth/DB/SSH/secret checks passed.
t139_execution_gate: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false, bio_wgs paused and real submission denied. No real OBS transfer or CCE WGS batch was started.
t140_blocker: Airflow-side Master Rule evidence integration is implemented in disabled mode, but no real CCE batch has validated kubectl incremental reads, the terminal reader Job, retry events or terminal reconciliation. Keep execution disabled until separately approved T140 acceptance.
```

## 2026-08-26 T135 planning - WGS 4.1.1 Airflow integration baseline

```text
t135_scope: doc-only; no DAG/backend/observer/frontend/Compose/migration/runtime code, BS10610 service, database, Docker network/volume, WGS source, OBS object or CCE workload was changed.
t135_wgs_source: /mnt/biodevrwbi/33.chenjiucheng/project/wgs-4.1.1, branch dev_CJC_4.1.1_cloud, clean commit 29388a81b182011a68d400adeb178ed0de147a49.
t135_cce_contract: WGS-owned cfg/profiles/cce/runtime.yaml, cce-pipeline 0.5.0, profile wgs-4.1.1-r1, WGS_cloud.smk target cloud_wgs_all, normal chain Step1-Step6.
t135_operator_boundary: node200 172.17.61.200 owns WGS prepare, private OBS and kubectl; BS10610 owns Airflow/FastAPI/observer/PostgreSQL/Redis/frontend; CCE never calls the local API.
t135_current_airflow: BS10610 still loads paused bio_wgs_cce, bio_wgs_intake_scan and bio_wgs_onprem; the worktree's uncommitted bio_wgs/T133 implementation is a 4.1.0 candidate and is not deployed 4.1.1 code.
t135_runtime_gap: cce-pipeline 0.5.0 exists only in the temporary nipttest environment; /bi/software/mamba/envs/WGS/bin/cce-pipeline is absent and must not be installed until wheel/source/build provenance is locked.
t135_monitoring: target observer consumes SFS rule-status/raw/*.jsonl, normalizes attempt/run_label from BATCH_RUNTIME.yaml, and stores only deterministic Master Job/Pod evidence; Worker Pods are not continuously monitored.
t135_transfer_decision: first production release exposes reliable stage state only; bytes/speed/ETA remain null with progress_detail_available=false until cce-pipeline publishes a stable machine-readable contract.
t135_intake_decision: first production release accepts manual frontend/API WGS CCE submission only; automatic intake remains disabled.
t135_cleanup_decision: production reset preserves user_account/roles, clears sessions and all demo runtime/audit state, and does not delete database volumes or the fixed Docker network.
t135_security_gate: tracked host prepare configuration and stale Master image labels require secret rotation/externalization and trusted image/build provenance before any real batch; sensitive values are not recorded in repository docs.
t135_execution_gate: WGS_EXECUTION_ENABLED=false, WGS_RUNTIME_ADAPTER_ENABLED=false and target bio_wgs paused remain mandatory through disabled-mode T139 acceptance.
t135_status: WGS 4.1.1 source/runtime audit and decision-complete integration documentation are complete; implementation starts at T135 contract freeze and remains todo.
```

## 2026-08-24 T133 Master logger overlay image follow-up

```text
t133_cce_followup_doc: cce-pipeline branch jiucheng/cce-pipeline-production-contract has doc-only commits d830d1f and 916c7c1 recording the two-column FASTQ manifest, transfer progress spool, Master logger runner, separate wgs-cloud-delivery boundary, and corrected immutable image contract; no cce-pipeline production code was changed.
t133_node200: Airflow runner address is fixed to 172.17.61.200 in Compose/example configuration; it remains a restricted OBS/kubectl runner and does not build images.
t133_delivery_image: wgs-cloud-delivery@sha256:d6d06ff... remains an unchanged Worker image for cloud_stage_cram/cloud_package_results/cloud_finalize_delivery; it receives neither cce-pipeline runtime nor logger plugin.
t133_master_base: direct inspection confirms the approved r2 digest 834b78c5... already contains Snakemake 9.24.0+biosan1, Kubernetes Executor 0.6.4+biosan3, cce-pipeline 0.2.0, and Master/cleanup/reset scripts.
t133_logger_image: BS10610 built and pushed tag cce-pipeline-0.2.0-schema3-20260824-r2-biosan-jsonl-v1 at RepoDigest sha256:5d1d977fb21e541582230f31540cc8cd4f7a183e417b41e508162060cfcdf211. The overlay adds only biosan-jsonl 1.0.0 and the logger-aware Master runner; tag- and digest-based container smokes pass.
```

## 2026-08-24 T133 WGS 4.1.0 logger + single-DAG implementation

```text
t133_wgs_source: isolated worktree /mnt/biodevrwbi/33.chenjiucheng/project/worktrees/wgs-4.1.0-airflow-logger, base commit b72ebea6616f79432c5ee6378f38f80b53575fa1; upstream worktree was not modified.
t133_wgs_snapshot: wgs-v4.1.0-candidate-b72ebea-2178aa5b at /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development, manifest SHA256 5f3aa5c0496b1224a8ae61799550392d37ff8269a4596cdc2a9a00e80dcc4631; execution_enabled=false.
t133_logger: snakemake-logger-plugin-biosan-jsonl 1.0.0 writes SFS rule-event.v1 JSONL only; no HTTP/FastAPI callback; standard analysis.log remains enabled; write failures emit LOGGER_DEGRADED.json without failing WGS.
t133_master_command: only formal cloud_wgs_all receives --logger biosan-jsonl; unlock, cloud_preflight, final dry-run and local/SGE remain unchanged.
t133_airflow: target release now publishes only paused CCE DAG bio_wgs with 15 project tasks; old bio_wgs_cce, bio_wgs_onprem and bio_wgs_intake_scan source/mounts are removed.
t133_runner: restricted wgs-runtime command targets node 200; node 200 is the sole OBS/kubectl operator boundary. WGS_EXECUTION_ENABLED=false and WGS_RUNTIME_ADAPTER_ENABLED=false remain in Compose.
t133_observer: accepts rule-event.v1 incrementally, deduplicates event_id, supports ISO timestamps and sequence, projects Rule state, recognizes LOGGER_DEGRADED.json, and accepts only Master Kubernetes evidence. Frontend tab is Master, not Worker Pods.
t133_cce_pipeline: confirmed clean worktree /mnt/biodevrwbi/33.chenjiucheng/project/worktrees/huawei-cloud-runtime-production-contract at 02adcecd85cc052b81330181a17d0377a742c39f; 65 tests pass; Airflow runner is wired to prepare/validate/run using an explicit immutable revision.
t133_open_contract_1: confirmed cce-pipeline prepare requires source,target,size_bytes,md5, while WGS 4.1.0 emits two-column source,target and the approved Airflow flow must not calculate FASTQ MD5. No FASTQ hash task was reintroduced; real prepare remains blocked until this interface is reconciled.
t133_image_contract: confirmed cce-pipeline Master digest 834b78c... runs Snakemake 9.24.0+biosan1 and Executor 0.6.4+biosan3 as intended; logger overlay digest 5d1d977f... preserves those versions and cce-pipeline 0.2.0.
t133_validation: WGS snapshot 27 tests pass; cce-pipeline 65 tests pass; backend focused 46 tests pass; node scripts 12 tests pass; DAG imports as bio_wgs with exactly 15 paused tasks; Compose/DAG contract 4 tests pass; WGS frontend focused tests 7 pass and local TypeScript/Vite production build passes. Full legacy backend suite is 215 pass/30 fail/1 skip and the legacy multi-product frontend capability tests remain incompatible because this WGS-only worktree intentionally rejects old NIPT/PGTA/WES product contracts.
t133_deployment: code is staged only under WGS_test and Airflow development snapshot; current BS10610 Compose was not recreated and no real OBS/CCE action ran.
```

## 2026-08-18 T133 WGS 4.0.1 code-driven flow correction

```text
t133_fastq_hash: WGS 4.0.1 does not generate/upload FASTQ.MD5SUMS; Airflow must not have start/wait FASTQ MD5 tasks.
t133_fastq_upload: Step1_upload_fastq.sh owns idempotent upload/reuse and writes FASTQ_UPLOAD_COMPLETE; obsutil -vmd5 remains a transfer option, not an Airflow hash stage.
t133_input_verify: no standalone verify_input_obs task; Step2 checks the upload marker and expected mounted FASTQ as an internal launch precondition.
t133_target_chain: validate -> prepare_wgs_batch -> upload -> launch batch Master -> wait/monitor -> publish -> download/result verification -> materialize -> finalize.
t133_rule_monitor: future Master-only Snakemake logger writes SFS Rule JSONL; current Master image/command is not wired yet.
t133_pod_monitor: future BS10610 host watcher monitors only the batch Master Job/Pod; Worker Job/Pod is not continuously collected or shown, and observer remains kubeconfig-free.
t133_correlation_scope: Rule state comes from the Master logger; because Worker Pods are outside the UI scope, no Rule-to-Worker-Pod mapping or jobs.ndjson schema extension is required.
t133_host_gap: upstream assumes one operator host; Airflow must split OBS/SFS actions on node005 from kubectl/CCE actions on BS10610 through restricted adapters.
t133_status: corrected design and read-only code audit complete; implementation and deployment remain not started.
```

## 2026-08-18 T133 WGS 4.0.1 单一 DAG 文档设计

```text
t133_scope: doc-only; no DAG/backend/observer/frontend/Compose/DB/config or BS10610 runtime change was made.
t133_baseline: WGS release 4.0.1 at commit 6cb1255fc1b218c9b18fb931eb3b6a172afe907b.
t133_current_dags: bio_wgs_cce, bio_wgs_onprem, and bio_wgs_intake_scan are current paused legacy DAGs; none has been removed.
t133_target: one CCE-only DAG named bio_wgs; ten-minute automatic scanning moves to wgs-observer.
t133_master: future runs use one batch-specific Master Job per analysis; fixed Master Deployments and PostgreSQL Master slots are pending deletion.
t133_evidence: native events.ndjson is batch state only; Rule state requires a separate Snakemake logger JSONL; run-state.json plus RUN_COMPLETE.json/RUN_FAILED.json and result verification determine terminal outcome.
t133_boundaries: node005 handles private OBS only; BS10610 handles kubectl/CCE only; Step7/Step8 are never automatic.
t133_gate: WGS_EXECUTION_ENABLED=false and all current DAG pauses remain unchanged.
t133_status: design and current-state audit complete; single-DAG implementation, launch adapter, runtime validation, and deployment have not started.
```

## 2026-08-18 T132 WGS 4.0.1 baseline replacement

```text
t132_wgs_source: /mnt/biodevrwbi/33.chenjiucheng/project/wgs, branch dev_CXJ_4.0.1_docker, clean commit 6cb1255fc1b218c9b18fb931eb3b6a172afe907b.
t132_airflow_copy: /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs was atomically replaced from the tracked upstream HEAD; upstream remained unchanged.
t132_snapshot: wgs-v4.0.1-dev-6cb1255-53453d5d; SNAPSHOT_MANIFEST.sha256 digest e9ce0f11c8c663ce13e88c7472a67ae36e2666cfba935312275396c3c7f5ce17.
t132_security: prepare/config.yaml, cfg/config.mail.ini, and legacy site publication/mail helpers were excluded; no literal password/token/access-key/secret-key assignment was found in the Airflow copy.
t132_runtime_gate: no active WGS DAG runs; bio_wgs_cce, bio_wgs_onprem, and bio_wgs_intake_scan remain paused; WGS_EXECUTION_ENABLED=false; no CCE analysis was launched.
t132_network: nipt_analysis_test_net remains 192.168.199.0/24 with gateway 192.168.199.1; only frontend publishes 172.17.106.10:12959.
t132_next: replace the obsolete persistent-Master/group_evidence adapter assumptions with the native 4.0.1 per-batch Master Job and SFS run-state/events/jobs/terminal-marker contracts before mock execution.
```

## 2026-08-12 T130 WGS server-copy observability release

t130_status: deployed on BS10610 as current release `20260812-wgs-observer-553be3f`; WGS execution remains disabled and all three WGS DAGs remain paused.
t130_source: upstream `/mnt/biodevrwbi/33.chenjiucheng/project/wgs` was not modified. Airflow integration lives in `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/development/wgs`, source commit `136da1ad9e45ac1abcbeb3efa40bb2e2269b6ab9`, manifest SHA256 `b10cd8af1db19c313e15167c295d007d9eca246d03b2721592c4c0532a05696c`.
t130_observer: schema `20260812_0007`; binding/catalog validation; durable byte/line cursors; partial-line wait; restart/replacement replay; schema-1 Rule projection; real `pod-events.jsonl`, `pod-metrics.jsonl`, and `job-events.jsonl` normalization.
t130_ui: authenticated Run Detail displays pinned snapshot, observer freshness/errors, Rule state, and Pod phase/reason/exit/node/resources with five-second active polling.
t130_network: immutable external `nipt_analysis_test_net`, subnet `192.168.199.0/24`, gateway `192.168.199.1`; only frontend publishes `172.17.106.10:12959`. Preflight runs before every recreate; service DNS is used because internal container IPs may change within the fixed subnet.
t130_acceptance: backend focused 27 passed; WGS frontend 3 passed plus TypeScript/Vite build; deployment contract 4 passed; synthetic partial append consumed 1 then 4 events and restart consumed 0; OOMKilled/137 and metrics projected; login/RBAC passed; submit HTTP 409; synthetic DB/files removed.
t130_rollback: restore `/airflow-WGS/env/bs10610.wgs.env` from validation backup, recreate only backend/observer/frontend from the prior release, and if necessary restore biodemo from `validation/t130-observer/backups/biodemo-before-0007.dump`. Never recreate the Docker network or delete volumes.

## 2026-08-12 T129 WGS-only Phase 1

```text
t129_goal: deploy the WGS-only control platform on BS10610 while the WGS 3.9.3 workflow remains mutable.
t129_scope: FastAPI/biodemo, RBAC sessions and audit, WGS-only React UI, read-only wgs-observer, paused Airflow CCE/on-prem/intake topologies, and fresh platform state.
t129_execution_gate: WGS_EXECUTION_ENABLED=false; backend submit returns HTTP 409; DAG runner tasks contain no production commands and fail closed.
t129_deferred: WGS Rules/logger changes, node005 OBS transfer, CCE submission, group_evidence integration, four-real-run concurrency, and CCE/SGE/local biological smoke are Phase 2.
t129_safety: no WGS 3.9.3 workflow file, production FASTQ/result/reference directory, kubeconfig, or private OBS credential is modified or copied.
t129_deployment: BS10610 current -> releases/20260812-wgs-only-phase1 (Git a30dcdb); fresh migration 20260812_0006, eight services healthy/running, three WGS DAGs paused, pools 4/1, auth/RBAC smoke passed, synthetic request created, submit returned 409.
t129_cleanup: old airflow-NIPT root, its Postgres/Redis volumes, and all old airflow-WGS releases were permanently removed after acceptance; 20260812-wgs-only-phase1 is the only release. Production WGS 3.9.3, CCE evidence, FASTQ, references, and results were preserved.
t129_status: Phase 1 deployed and accepted. T130 workflow integration remains todo.
```

> 本文件由 Codex/agent 持续维护。每次任务开始前先读，每次任务结束前更新。

## 1. 当前阶段

```text
current_goal_ascii: T128 repairs BS10610 NIPT manual FASTQ discovery latency without submitting analysis; BS1069 remains a stopped cold standby.
t128_root_cause: /api/input/scan eagerly materialized the complete /data/nipt-fastq tree before applying max_samples; the BS root contains hundreds of batches and more than 23,000 clean FASTQ files, so nginx returned 504 after 60 seconds.
t128_change: NIPT discovery now walks newest directories lazily and exits at max_samples; the BS default approved scan root is /data/nipt-fastq/FQ2026 and Submit Run adopts the root returned by /api/input/roots.
t128_safety: the existing /data/nipt-fastq read-only mount and historical run paths are unchanged; no run is created/submitted, bio_intake_scan remains paused, and no FASTQ/database/volume/network mutation is allowed.
t128_status: implementation and isolated backend/frontend tests pass; BS10610 deployment and real FQ2026 latency acceptance remain pending.
t127_architecture: one existing Compose project airflow-nipt; shared PostgreSQL, Redis, FastAPI, React/nginx, Airflow API, scheduler, and Celery worker; deployed DAGs are bio_nipt_docker, bio_wgs, and paused bio_intake_scan; PGT-A is absent.
t127_concurrency: NIPT Docker and host WGS share one-slot bs_heavy_analysis; WGS uses up to 96 host cores and NIPT uses 32 container cores; the two heavy workflows cannot overlap.
t127_wgs_runtime: host Snakemake 9.23.1/Python 3.12 is deployed under /mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS; Airflow invokes a restricted forced wgs-run command through SSHOperator; production WGS sources remain read-only.
t127_validation_scope: WGS acceptance stops at an Airflow-managed Snakemake 9 pre-calling dry-run for one family; WGS_20260715_062217_351C76 completed success in 12 seconds with 21 planned jobs persisted as terminal skipped and no biological rule executed.
t127_active_run: none. The latest accepted WGS dry-run and all three T127 NIPT validations are terminal success; the earlier intentionally stopped WGS_20260714_180953_9D7981 remains a historical failed handoff record.
t127_nipt_validation: NIPT_20260715_030032_9A815B, NIPT_20260715_031706_C435A8, and NIPT_20260715_033817_4B4F72 each completed 27-sample full analysis serially in 858, 783, and 884 seconds; each has 27/27 sample QC pass and 232/232 success rule events with zero running events.
t127_images: BS10610 uses backend bs-control-f11ea02 (sha256:221955332609...) and frontend bs-control-f11ea02 (sha256:93cf3a076c43...); archives moved fengxian -> local Windows -> each BS and passed SHA256. BS1069 loaded the same images and remains stopped.
t127_frontend: live browser acceptance shows one NIPT Docker + WGS control plane, zero visible PGT-A labels, zero console warnings/errors, JSON-safe /api routing, WGS dry-run as success with QC not applicable, and 21 planned dry-run jobs rather than false running rules.
t127_safety: scanner remains paused, automatic NIPT/WGS submission remains disabled, PostgreSQL/Redis volumes were preserved, and no FASTQ/result/workflow source was deleted or modified.
t126_primary: BS10610 runs fresh PostgreSQL/Redis, FastAPI, React/nginx, Airflow CeleryExecutor API/scheduler/worker, bio_nipt_docker, and paused bio_intake_scan under /mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT.
t126_runtime: NIPT_20260714_133355_B3081A (10 samples) and NIPT_20260714_140419_F999B0 (72 samples) completed with 10/10 and 72/72 QC pass; the 72-sample run completed in 923 seconds with 592/592 terminal-success rule events and 42.86 GiB observed peak memory.
t126_integrity: all 144 source FASTQ SHA256 and stat records were identical before/after the 72-sample run; mapping QC, T21 classifier, and dynamic-reference summaries match the fengxian S9 baseline, with fetal-fraction deltas <=4e-6.
t126_images: default 172.17.61.235:2333/niptpro/niptpro:1.1.11 preserves source image ID sha256:71df36b7f8080762f2db771e13e4daa7f4a666b3e1efc19c3bf12add22187254; legacy 1.0.11 remains available and unmodified.
t126_standby: BS1069 receives archives through fengxian -> local Windows -> BS1069 only; checksums pass and images are loaded, while scheduler/worker/frontend/backend remain stopped.
t126_network: external nipt_analysis_test_net remains immutable at 192.168.199.0/24 with gateway 192.168.199.1; only frontend-nginx publishes 172.17.106.10:12959 and :12958.
t126_safety: bio_intake_scan remains paused, NIPT automatic submission remains disabled, FASTQ/workflow/locale mounts are read-only, and no Postgres/Redis volume or historical output was deleted.
t125_network: external network nipt_analysis_test_net, subnet 192.168.199.0/24, gateway 192.168.199.1; deployment must not create, recreate, delete, or alter it.
t125_scope: writable project root /mnt/biodevrwbi/33.chenjiucheng/project/airflow-NIPT; BS10610 primary, BS1069 cold standby; NIPT Snakemake 9 only.
t125_ingress: BS10610 observed the current SSH client as 172.17.61.18, so nginx allowlist 172.17.61.0/24 covers the present operator path; final HTTP source still requires access-log verification.
t125_status: documentation and BS10610/BS1069 project-root write probes completed and were superseded by the accepted T126 runtime deployment.
t124_baseline: T124 QC formatting, Intake alignment, and terminal sorting is deployed and remotely accepted.
t124_code: terminal runs sort by latest pipeline completion; Intake shares project/runtime cells and the success-only ETA model; QC count/rate/fraction formatting is centralized in the frontend.
t124_validation: remote backend pytest passed 168; frontend Vitest passed 49; production tsc/vite build and Compose config passed; backend/frontend were rebuilt and recreated; HTTP/API and live browser checks passed at 1280/1024/390 px.
t124_runtime: latest completed NIPT is first in Run Tracker; linked Intake rows expose elapsed/ETA and hide scan roots; NIPT rate/fetal values and PGT-A count/decimal values render with operator units. Scanner remains unpaused on */10 and no analysis was triggered.
t124_backup: /home/jiucheng/project/airflow-demo-t121/backups/T124-20260714-1220/pre-overlay-source.tar.gz (SHA256 ed1f54f5b9114622604c60e95674c1427b0bb02959cdddebae04168083743666).
t123_baseline: T123 Predict-only operator path and runtime-state consistency is deployed and remotely accepted.
t123_frontend: Dashboard Intake defaults to Pending & errors with History for linked runs; Run Tracker shows Manual/Intake provenance; PGT-A Run Detail shows only Predict and hides historical baseline actions; logs are grouped by failure/current/workflow/other; Workflow Catalog is live.
t123_backend: dashboard exposes run source and QC display semantics; failed parents cancel stale running rule events; workflows aggregate live persisted state; scanner state exposes trigger/retention contracts.
t123_runtime_policy: NIPT S9 default is 32 cores; Airflow json logs rotate at 50 MB x 3; scanner-only DAG history/log retention runs at 03:00, cannot target analysis DAGs, and a terminal propagation task prevents cleanup from masking scan failure.
t123_validation: remote isolated backend pytest 187, frontend Vitest 47, frontend tsc/vite build, Intake DAG unittest 6, config override unittest 10, Compose config, Airflow import, HTTP health, and live browser checks passed.
t123_safety: PGTA_20260713_144002_E73F72 reached success before any worker restart; no active runs were reported at the deployment gate.
t123_runtime: backend, Airflow API/scheduler/worker, and frontend are deployed from /home/jiucheng/project/airflow-demo-t121; scanner remains unpaused on */10, NIPT auto-submit remains disabled, and Airflow/Postgres/Redis volumes were not recreated.
t123_reconciliation: NIPT_20260713_145457_ACCBDC retains two true failed mapping samples while eight stale running siblings are canceled; no rule event remains running, and failed sample logs open first in Run Detail.
t123_nipt_32c: manual clone NIPT_20260713_162606_5B5B11 completed success in about 14 minutes with 20/20 sample QC pass and 176/176 rule events success; Workflow Catalog now reports it as the latest NIPT Full run.
t123_backup: /home/jiucheng/project/airflow-demo-t121/backups/T123-20260714-0025 contains the pre-deploy scanner state/run inventory and SHA256SUMS.
t122_root_cause: NIPT run and Discovery data were already synchronized as success, but successful Discovery rows were archived and hidden by Dashboard lifecycle=active; the Dashboard Intake query also did not refresh after active-run sync, leaving stale submitted rows in an open browser session.
t122_frontend: Dashboard and Platform Settings default to lifecycle=all. Active polling, manual Sync, and Submit refresh Intake with no loading flash. Linked rows use display_status/analysis_status, so submit_state=submitted does not mask workflow success.
t122_live_nipt: NIPT_20260713_135001_98E375 is success, QC pass, 72 samples, progress 100, current stage Completed, and archived with workflow_success. The four NIPT Discovery records are visible through lifecycle=all.
t122_runtime: frontend only was rebuilt/recreated from /home/jiucheng/project/airflow-demo-t121; backend, Airflow services, scanner, DB, FASTQ, workdirs, and pipeline containers were unchanged.
t122_validation: remote frontend Vitest passed 40; production tsc/vite build and Compose config passed; frontend returned HTTP 200 and deployed bundle contains the completed-intake label.
t121_root_cause: project-20260713 failed before run creation because source_batch 2026-06-08/batch01 did not exist and H1/H2 were not resolvable FASTQ sample IDs. This was an Intake manifest error, not a Snakemake config or Airflow DAG failure.
t121_ui: Dashboard and Platform Settings now show Intake validation failed plus the concrete backend last_error in their shared Discovery table.
t121_template: project-20260713.samples.par.tsv now uses source batch 2026-06-08/HZSW-20260602-L-01-2026-06-062220 and samples JZ26117424-H1-H1/JZ26117425-H2-H2. Read-only parsing resolved two unique R1/R2 pairs with no errors.
t121_safety: the files retain non-trigger .par.tsv/.par.READY names; no project-20260713.samples.tsv or project-20260713.READY was published, so no PGT-A run was started. The original template is backed up under /home/jiucheng/project/airflow-intack-configs/pgta/backups/T121-20260713.
t121_runtime: backend/frontend are deployed from /home/jiucheng/project/airflow-demo-t121; health is green, scanner remains unpaused, and the live error row exposes current_stage and last_error.
t121_validation: remote backend pytest passed 181; frontend Vitest passed 40; production tsc/vite build and Compose config passed; frontend returned HTTP 200.
t120_scope: operators edit path-free YAML under /home/jiucheng/project/airflow-intack-configs/nipt and atomically publish final *.nipt.yaml files to /home/jiucheng/project/airflow-intake-requests/nipt.
t120_parser: request_id/project_id/batch_id, all-or-list samples, approved runtime profile, full_run, cores, and explicit submit are validated; batch_id resolves uniquely below approved read-only NIPT FASTQ roots.
t120_gates: two stable scans, submit=true, defaults.auto_submit=true, request_submit_enabled=true, approved profile, and NIPT heavy-run policy are all required. Ordinary NIPT directory auto_submit.enabled remains false.
t120_runtime: backend is deployed from /home/jiucheng/project/airflow-demo-t120; the request inbox mount is active and empty, bio_intake_scan is unpaused, and no run or Discovery row was created during acceptance.
t120_template: project-20260713.nipt.yaml in the non-scanned edit workspace resolves 72 samples from 260422_TPNB500380AR_1070_AH33KYBGY2 with cores=32 and submit=true; publishing it would start a full run, so acceptance did not copy it to the trigger inbox.
t120_validation: remote backend pytest passed 181; Compose config passed; a read-only submit=false probe resolved 72 samples from batch 260422_TPNB500380AR_1070_AH33KYBGY2; API health/config/preview passed.
t119_scope: Dashboard terminal age updates locally every 60 seconds; Search operations drives Run Tracker and Intake; completed Intake records archive while preserving fingerprints and audit history.
t119_intake: scheduled discovery covers PGT-A READY manifests and the restricted NIPT BS_DEMO_20260713 root; NIPT auto-submit remains disabled and full runs are manually serialized.
t119_backup: pre-migration remote backup is /home/jiucheng/project/airflow-demo-backups/T119-20260713T140647 with Airflow/biodemo dumps, inventories, PGT-A inbox archive, and SHA256SUMS.
t119_status: done. T119 is deployed from /home/jiucheng/project/airflow-demo-t119; migration 20260713_0005 is applied; backend/frontend/Airflow health is green.
t119_data: biodemo has 8 successful runs and 129 samples. Intake has 6 archived rows and 0 active rows; the scanner is unpaused, scheduled PGT-A/NIPT discovery is healthy, and NIPT auto-submit remains disabled.
t119_nipt_runs: NIPT_20260713_080217_DEC52B has 10/10 QC pass and 96 terminal events; NIPT_20260713_090714_C941EA has 15/15 QC pass and 136 terminal events after a controlled 32-core same-workdir recovery from a 40-core cgroup OOM; NIPT_20260713_095250_374EA9 has 20/20 QC pass and 176 terminal events.
t119_validation: remote backend pytest 168, frontend Vitest 40, Intake DAG unittest 3, production tsc/vite build, Compose config, health, and live 1280/390 browser checks passed.
t118_intake_fix: blank and whitespace-only manifest lines are ignored; malformed non-empty rows still fail with a line number. Later parse errors cannot downgrade submitted Discovery, and restoring the valid manifest clears the warning.
t118_legacy_repair: t112-pgta-s9-full-h4-h5-20260711 was backed up and restored from false error to submitted for successful run PGTA_20260711_071416_C8C7BA; the next scan preserved the repair.
t118_five_sample: project-20260713-five-samples.samples.tsv and READY contain H1, H2, H6, H8, and H9 from one 2026-06-08 batch. Two scans created only PGTA_20260713_034634_939AFF; a third stayed idempotent. The run is active in Mapping/fastp_bwa and was not awaited to completion.
t118_log_audit: 212 ten-minute scanner runs occupied about 2.5 MB across 211 worker task-log files; Airflow DB was 13 MB and Docker json-file logging had no rotation. Follow up with 50 MB x 3 rotation and 30-day scanner-only retention.
t118_backup: /home/jiucheng/project/airflow-demo-t117/backups/T118-20260713-intake-repair contains the biodemo dump, Discovery snapshots, new manifest/READY, and SHA256 evidence.
t118_validation: remote backend pytest passed 141; dry-run resolved 5 samples, 10 FASTQ, and 17.47 GB; backend/frontend HTTP passed; scanner remains unpaused.
t117_runtime: backend/frontend run from /home/jiucheng/project/airflow-demo-t117. Submit labels submission provenance as Submitted by, defaults manual submissions to jiucheng, accepts arbitrary IDs with jiucheng/airflow suggestions, remembers the last ID in browser storage, describes both deployed assays as low-pass WGS, and Batch Runs renders bulk workflow phase summaries without per-run requests.
t117_workflow_ui: Run Detail separates selected Airflow tasks from skipped alternate branches. Browser checks at 1280 and 390 CSS pixels showed no document overflow; mobile Batch Runs collapses the phase rail to current stage and completed/total count.
t117_operator: PGTA_20260711_062522_4C4FC2 and PGTA_20260711_071416_C8C7BA were changed from codex-validation to jiucheng through an exact-snapshot CLI; each correction has a metadata_correction RunAction. NIPT codex-t113 remains unchanged.
t117_intake: project-20260712 malformed space-delimited rows were corrected to TSV after backup. Three controlled scans produced exactly one run, PGTA_20260712_171630_AE8239, with 4 samples and operator jiucheng; Airflow/backend are running in fastp_bwa Mapping. Acceptance intentionally did not wait for terminal completion.
t117_backup: /home/jiucheng/project/airflow-demo-t117/backups/T117-20260713-012000 contains biodemo dump, original/corrected manifest evidence, operator preview/apply output, before/after inventories, and SHA256SUMS.
t117_validation: backend pytest passed 139; frontend Vitest passed 38; production tsc/vite build passed; DAG unittest passed 90 with 5 expected logger skips; Compose config and HTTP health passed.
t116_runtime: backend and Airflow API/scheduler/worker run from /home/jiucheng/project/airflow-demo-t116; frontend remains healthy on 12959. Postgres, Redis, volumes, workdirs, FASTQ, logs, results, and pipeline releases were not recreated or deleted.
t116_airflow: deployed DAGs are only bio_pgta, bio_nipt_docker, and bio_intake_scan. Airflow retains two complete PGT-A runs and one complete NIPT run; legacy bio_pgta_airflow and bio_wes_qsub metadata were deleted and their source files are excluded by .airflowignore.
t116_intake: discovery was reduced from 25 rows to the submitted PGTA_20260711_071416_C8C7BA manifest row. Scheduled intake defaults to pgta only; manual NIPT server scan/submit remains available. bio_intake_scan was restored unpaused and subsequent successful cycles continue to leave discovery at one row without recreating NIPT/bootstrap rows.
t116_backup: /home/jiucheng/project/airflow-demo-t116/backups/T116-20260712-014626 contains verified Airflow+biodemo pg_dump files, before/after inventories, cleanup preview/apply JSON, and SHA256SUMS.
t116_validation: backend pytest passed 134; DAG unittest passed 90 with 5 expected logger-interface skips; Compose config, DagBag import, backend/frontend health, 3 runs, 75 samples, and retained workdirs were verified.
t115_runtime: backend/frontend are deployed from /home/jiucheng/project/airflow-demo-t115; frontend 12959 and backend 8000 are healthy. Airflow services, Postgres, Redis, volumes, and pipeline runners were not recreated.
t115_intake_ui: Platform Settings and Dashboard share one Discovery Tracker table. Settings uses server-side pipeline/state/keyword filters, 10-row pagination, independent config/scanner/discovery/preview states, and no scan/submit/unpause action.
t115_data_safety: /api/intake/status reported 25 discovery rows and the deployed run list remained exactly 3 retained successful runs. bio_intake_scan remained unpaused, PGT-A manifest intake remained enabled, and NIPT automatic intake remained disabled.
t115_validation: backend pytest passed 129; frontend Vitest passed 36; tsc/vite production build and Compose config passed; live Settings at 1440/1280/1024/390 had no document-level horizontal overflow and only the discovery table scrolled internally.
t114_runtime: services are deployed from /home/jiucheng/project/airflow-demo-t114; frontend 12959 and backend 8000 are healthy; bio_intake_scan was restored to its original unpaused state after maintenance.
t114_data: biodemo was backed up and reduced from 49 runs to PGTA_20260711_062522_4C4FC2, PGTA_20260711_071416_C8C7BA, and NIPT_20260711_111140_63C5A6; 75 samples remain. Airflow metadata, workdirs, logs, outputs, FASTQ, volumes, and pipeline releases were not deleted.
t114_nipt_qc: NIPT_20260711_111140_63C5A6 has 504 metrics, 72/72 sample QC pass, submitted_at 2026-07-11T11:11:40Z, pipeline_finished_at 2026-07-11T11:36:18Z, and runtime 1477 seconds.
t114_backup: /home/jiucheng/project/airflow-demo-t114/backups/T114-20260711-2230 contains the pre-cleanup pg_dump, run inventory, cleanup preview, and applied result.
t113_image: airflow-demo/niptpro:1.0.11-snakemake9.23.1-v1 image sha256:71df36b7f8080762f2db771e13e4daa7f4a666b3e1efc19c3bf12add22187254; original Snakemake 7 image and /opt/conda analysis environment remain unchanged.
t113_validation: 72-sample run NIPT_20260711_111140_63C5A6 completed all 591 Snakemake jobs in about 24.8 minutes; 592 persisted terminal events include the parent workflow event, with no residual running/failed events.
t113_comparison: samplesheet, mapping QC, model prediction, chr21 outputs, and four summary CSVs are byte-identical to the approved Snakemake 7 baseline; observed peak memory was 44.61 GiB and input/bundle stat manifests were unchanged.
t113_runtime: services are deployed from /home/jiucheng/project/airflow-demo-t113; NIPT full analysis uses a one-slot Airflow pool, max_active_runs=1, 90-minute timeout, real-time Snakemake rule/sample events, and paginated phase observability.
t113_gate: manual NIPT full analysis is approved after engineering validation; NIPT automatic intake remains disabled. PGT-A S9 and its manifest intake remain unchanged.
t112_release: pgta-s9-v1.4 is deployed at /home/jiucheng/pipelines/PGT_A_S9/releases/pgta-s9-v1.4; current points to the verified SHA256 release and the original PGT_A directory is unchanged.
t112_validation: small 2 x 1M run PGTA_20260711_061816_F1E358, full H3 run PGTA_20260711_062522_4C4FC2, and full H4/H5 manifest run PGTA_20260711_071416_C8C7BA all reached success with terminal logger events, passing QC, and WisecondorX predict outputs.
t112_runtime: frontend/backend/Airflow services are healthy from isolated /home/jiucheng/project/airflow-demo-t112; Airflow uses CeleryExecutor for project tasks, Snakemake 9 manages rule/sample parallelism inside the worker, internal scanner/event endpoints require a shared service token, and the worker verifies the immutable release manifest before execution.
t112_intake_gate: bio_intake_scan is unpaused after validation; PGT-A READY-manifest auto-submit is enabled and idempotent, NIPT auto-submit remains disabled, and NIPT full-run remains guarded.
last_t111_backend_tests: remote Dockerized full pytest passed 103 tests.
last_t111_airflow_tests: full unittest discovery passed 74 tests with 5 expected logger-interface skips; compose worker profile-mount and approved-runtime availability regressions passed.
last_t111_frontend_tests: remote Dockerized Vitest passed 24 tests; production tsc/vite build passed.
last_t111_runtime_smoke: PGTA_20260710_110056_DC8A8D metadata and NIPT_20260710_110057_79A631 mount_smoke both reached success with final reviewed profiles and resolved config provenance.
last_t111_browser_check: Submit and Run Detail Config passed at 1440 and 390 CSS pixels without document overflow; Compose artifacts remained hidden.
当前阶段: P3/P4/P6 Airflow + Snakemake/qsub mock observability + PGT-A Level 4 staged integration
当前目标: T110 已将 Dashboard、Batch Runs、Sample Matrix、Failure Triage 和 Run Detail 收敛为可分页、可筛选、无 N+1 的 PGT-A/NIPT 操作员工作区；下一步在不启用自动 intake 的前提下继续做正式流程上线前的审计与权限边界。
最近更新时间: 2026-07-10
最后更新 agent: Codex
```

## 2. 服务器信息

详见 `SERVER_INFO.md`。不得在此处写入密码或 token。

```text
server_host: fengxian
deploy_user: jiucheng
project_root: /home/jiucheng/project/airflow-demo
docker_available: true on fengxian read-only preflight
docker_compose_available: true, Docker Compose version v2.24.7 at $HOME/.docker/cli-plugins/docker-compose
qsub_available: false on fengxian read-only probe 2026-07-04; mock qsub wrapper available in repo
snakemake_available: true for PGT-A at /biosoftware/miniconda/envs/snakemake_env/bin/snakemake and /biosoftware/miniconda/envs/snakemake9_env/bin/snakemake
python_version: PGT-A locked python 3.12.2
node_version: <unknown>
```

## 3. 仓库状态

```text
repo_url: git@github.com:boksic1986/airflow-BS-demo.git
main_branch: main
active_branch: codex/platform/T119-operations-age-intake-archive-nipt-batches in isolated local worktree; T118 baseline is `224a792`
last_verified_code_commit: T119 branch is based on `224a792`; verified implementation is recorded by the current T119 branch head
worktree_strategy: single-worktree for now; fengxian is code mirror only
fengxian_mirror: /home/jiucheng/project/airflow-demo cloned from GitHub; T108 overlay is deployed there and `origin/main` on the mirror has been fetched to `0857e3d`, but the mirror worktree itself remains on its existing dirty deployment branch
```

## 4. 服务状态

| Service | Expected port | Status | Notes |
|---|---:|---|---|
| frontend | 12959 | running, healthy from T122 | Intake defaults to active + completed records, refreshes after Airflow sync, and exposes validation reasons |
| backend | 8000 | running, healthy from T121 | Intake error stage semantics, lifecycle/archive, and authoritative terminal Airflow reconciliation are deployed; migration `20260713_0005` is current |
| airflow web/api | 12958 | running, healthy | deployed DAGs remain `bio_pgta`, `bio_nipt_docker`, and `bio_intake_scan`; scanner is unpaused and its latest scheduled run succeeded |
| postgres | internal 5432 | running, healthy | image `postgres:15-alpine`; T119 backup verified; biodemo contains 8 successful runs, 129 samples, 6 archived Intake rows, and 0 active Intake rows |
| redis | internal 6379 | running, healthy | image `redis:7-alpine`; no host port published |
| mailhog | 8025 | stopped in T051 smoke | HTTP GET probe passed in earlier smoke; not started for T051 |

## 5. 数据库状态

```text
airflow_metadata_db: initialized by `docker compose -f docker-compose.yaml up airflow-init`; admin user exists, password only in remote .env
biodemo_db: initialized on fengxian by `docker compose -f docker-compose.yaml run --rm biodemo-db-init`
migrations_tool: Alembic
last_migration: 20260713_0005 Intake lifecycle fields (applied on fengxian during T119 rollout)
core_tables: pipeline, analysis_run, sample, snakemake_rule_event, qc_metric, artifact, run_action, intake_discovery
```

## 6. Pipeline 接入状态

| Pipeline | DAG | Snakemake | qsub | Docker | QC | Status |
|---|---|---|---|---|---|---|
| PGT-A S9 predict | `bio_pgta` stages validate, prepare, mapping, metadata, cnv_qc, cnv_predict, collect; full-run pool has one slot | Snakemake 9.23.1 release `pgta-s9-v1.4`; per-rule/sample logger events; fixed approved hg19 XX/XY/gender references | not used | not used | mapping QC, estimated depth, CNV QC, prediction status; QC fail is separate from workflow fail | engineering validation passed for 2 x 1M, one full H3, and full H4/H5 READY-manifest runs; PGT-A manifest intake enabled; not claimed as clinical validation |
| PGT-A demo | `bio_pgta` metadata/dryrun/failure smoke passed; `bio_pgta_airflow` Airflow-only logger/event POST passed; `baseline_qc` staged real run `PGTA_20260706_162150_00C4FD` completed after controlled interrupt/resume sequence; final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` ended Airflow/backend `success` | direct Snakemake metadata target, `dryrun_cnv`, controlled `invalid_target`, and Level 4 `baseline_qc` smoke in Airflow worker passed; T088 sets `XDG_CACHE_HOME=<workdir>/tmp/xdg-cache`; T093 resume runs `--unlock` then `--cores 64 --rerun-incomplete`, no `--forceall`; T094 adds run-local cleanup of `mapping/*.sorted.bam.tmp.*.bam`; T095 sets conda `LD_LIBRARY_PATH`, `LD_PRELOAD=PGTA_LIBSTDCXX`, run-local `MPLCONFIGDIR`, and baseline QC Python preflight; Snakemake 9.23.1 logger plugin writes JSONL, Airflow log/XCom summary, and optional backend rule/job events | not used | server-path project creation, submit, status sync, logs, artifacts, rule event API, PGT-A run detail frontend v1, New PGT-A Run frontend scan/create/submit, active-run auto-sync, failed baseline_qc `Resume with 64 cores`, and QC/artifact panel API are available | baseline_qc parser/artifacts added; `/qc` imports 14 metrics for G10/G11 and both samples have QC decision `FAIL` | `/api/input/scan` and `/api/runs` create `created` run; submit triggers `bio_pgta`; Airflow-only manifest run can POST rule events to biodemo; frontend can create pgta runs for metadata/dryrun/failure/baseline_qc smoke, submit created runs, view run list/detail, samples, rules, logs, artifacts, QC, sync Airflow, and resume failed baseline_qc |
| WES qsub | `bio_wes_qsub` Airflow mock DAG passed with `new/resume/rerun_rule` and QC smoke | WES mock Snakefile dry-run passed; WES mock profile runtime passed in `snakemake-runner`; `bio_wes_qsub` runs Snakemake 9.23.1 inside Airflow worker with `profiles/qsub`, writes command/stdout/stderr/events and `reports/qc_summary.tsv` | mock qsub wrapper direct smoke passed with backend POST; Airflow/API/frontend smoke generated mock qsub job ids, stdout/stderr files, JSONL events, and command log proving `--forcerun fastp` without `--forceall` | `airflow-demo/snakemake-runner:0.1.0` and `airflow-demo/airflow:0.1.0` builds passed | WES mock QC parser and frontend QC panel done; real WES QC and MultiQC not started | T040/T041/T042/T030/T031/T044/T056/T060/T054 done; next step is T034/T063 MailHog notification or T080 smoke report/demo script |
| NIPT qsub | not started | not started | not started | n/a | not started | pending |
| NIPT Docker S9 | `bio_nipt_docker` keeps validate, prepare, run, collect project tasks; `max_active_runs=1`, pool `nipt_s9_full=1`, timeout 90 minutes | derivative image runs Snakemake 9.23.1/Python 3.12 logger while rules retain the original `/opt/conda` tools; per-rule/sample events are persisted and streamed | n/a | host Docker via Airflow worker socket; clean FASTQ batch is read-only; original NIPT bundle and S7 image are unchanged | reads, Q30, unique mapping, duplication, chrY, gender, fetal ratio, CNV/classifier artifacts | 72-sample baseline plus T119 10/15/20-sample runs passed; 40 cores can exceed the 60 GiB cgroup on heterogeneous mapping, while controlled 32-core recovery/validation passed; NIPT auto-submit remains disabled |

## 7. 最近测试结果

```text
last_backend_tests: remote Dockerized full T121 pytest passed 181 tests, including explicit Intake validation stage semantics.
last_frontend_tests: remote Dockerized T122 Vitest passed 40 tests; production `tsc -b && vite build` passed.
last_dag_import_tests: remote repo-mounted T119 Intake DAG unittest passed 3 tests using `/home/airflow/.local/bin/python`; deployed scanner and analysis DAGs are healthy.
last_snakemake_dryrun: passed on fengxian; `dryrun_cnv` run `PGTA_20260703_170917_20E8F2` ended Airflow/backend `success`, stdout log size 12677 bytes and recorded 7 dry-run jobs, stderr only had config-extension notice, artifacts returned stdout/stderr/config files
last_compose_config: passed on fengxian for T122; frontend only was rebuilt/recreated without changing backend, Airflow services, Postgres/Redis volumes, FASTQ, workdirs, logs, or results.
last_browser_responsive: T119 live Dashboard and Settings passed at 1280/390; document `scrollWidth <= clientWidth`, terminal age rendered from real data, and Archived Intake displayed all 6 records with only its table scrolling internally.
last_minimal_smoke: passed on fengxian for postgres redis backend frontend airflow-api-server airflow-scheduler airflow-worker, then docker compose down
last_airflow_health: passed on fengxian at http://127.0.0.1:12958/health with healthy metadatabase and scheduler
last_biodemo_migration: `biodemo-db-init` first run created role/database, repeat run succeeded; T103 `alembic upgrade head` applied 20260708_0002 `intake_discovery`
last_backend_airflow_client: mock tests covered health/list/get/trigger; real smoke verified backend `/api/health/airflow` against Airflow `/health`
last_backend_build: backend image built on fengxian using `backend/pip.conf` TUNA PyPI mirror and `/opt/venv`; dependency install step dropped from about 9 minutes to about 11 seconds after mirror config
last_pgta_project_create_smoke: passed on fengxian; scan root `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` returned 5 candidates with `truncated=true`, created `PGTA_20260702_162531_74CE91` with 2 samples, status `created`, `dag_run_id=null`, and generated `samples.selected.tsv` plus `request.json`
last_pgta_submit_metadata_smoke: passed on fengxian for T107; created/submitted `PGTA_20260708_141653_B57AB6`, backend status `success`, `dag_run_id=manual__PGTA_20260708_141653_B57AB6`, progress current_step `metadata`, and the new `bio_pgta` task tree shows both the historical metadata branch and the staged baseline_qc TaskGroup
last_pgta_t108_metadata_smoke: passed on fengxian; created/submitted `PGTA_20260708_160227_EFAD64` with target `metadata`, backend sync returned `success`, `dag_run_id=manual__PGTA_20260708_160227_EFAD64`, progress returned `percent=100`, Airflow task instances, and Snakemake rule event `metadata=success`; no heavy baseline_qc run was started.
last_pgta_diagnostics_smoke: passed on fengxian; `sync-airflow` changed `PGTA_20260702_171533_9A85B1` to `success` with `error_summary=null`, changed historical failed `PGTA_20260702_171200_A68C19` to `failed` with non-null `error_summary`, log API read metadata/stderr, artifact API returned metadata/stdout/stderr/config files, and missing log returned `LOG_NOT_FOUND`
last_pgta_airflow_logger_smoke: passed on fengxian; `bio_pgta_airflow` run `manual__PGTA_AIRFLOW_20260703_054712_501D8B_events` ended `success`, generated `run_metadata.tsv` (11 lines), `snakemake_events.jsonl` (22 lines), `snakemake_rule_summary.tsv` (29 lines), and `/api/runs/PGTA_20260703_054712_501D8B/rules` returned `all=success` and `collect_run_metadata=success`
last_frontend_run_detail_smoke: passed on fengxian at http://127.0.0.1:12959/; React HTML served, `/api/runs?pipeline=pgta` returned existing PGT-A runs, `PGTA_20260703_054712_501D8B` rules returned `all=success` and `collect_run_metadata=success`, metadata log/artifacts/samples APIs returned data, CORS preflight returned 200
last_frontend_submit_smoke: passed on fengxian; frontend HTML served at `http://127.0.0.1:12959/`, API scan of `/data/project/CNV/PGT-A/rawdata/lib_test/2026-04-28` returned 1 candidate with `truncated=true`, created `PGTA_20260703_154341_408A29`, submit returned `dag_run_id=manual__PGTA_20260703_154341_408A29`, sync ended `success`, artifacts returned 5 items, metadata log tail returned 3 lines, and run list contained the new run
last_frontend_submit_workspace_fix: passed on fengxian; red test first failed because `Submit new analysis` region was missing and `New PGT-A Run` lived inside the run-list aside, then frontend Docker test target passed with 12 tests after moving submit panels to main content; `docker compose build frontend` succeeded and `docker compose up -d frontend` redeployed 12959, with HTTP 200 and deployed CSS containing `submit-workspace`
last_pgta_level4_audit: 2026-07-06 read-only audit on fengxian confirmed `/home/jiucheng/pipelines/PGT_A/Snakefile` has real `baseline_qc`, it requires at least 2 baseline/reference samples and emits `qc/baseline/baseline_qc_summary.tsv`, `baseline_qc_pass_samples.txt`, and `baseline_qc_report.md`; no real Level 4 run executed in this audit
last_pgta_baseline_staged_integration: passed code-level remote validation on fengxian at commit 4cf6f6e; backend/frontend/Airflow images built, backend pytest 48 passed, frontend Vitest 14 passed, DAG unittest 14 passed, Airflow import errors `No data found`, frontend HTTP 200, backend `/api/health` ok, Airflow `/health` healthy after startup; no real baseline_qc run was executed
last_pgta_cache_fix_smoke: passed on fengxian at commit dd5c6e7; tests first failed on missing `workdir/tmp/xdg-cache`, then passed after setting `XDG_CACHE_HOME`; new metadata run `PGTA_20260706_140854_8F2CA4` submitted to `bio_pgta`, sync progressed running -> success, Airflow listed the DAG run as success, `logs/run_metadata.tsv` has 11 lines, artifacts include `snakemake_command`, and stderr no longer contains `/home/airflow/.cache/snakemake` PermissionError
last_timezone_alignment: passed on fengxian at commit f2fdff2; `docker compose config --quiet` rendered `AIRFLOW__CORE__DEFAULT_TIMEZONE=Asia/Shanghai`, `AIRFLOW__WEBSERVER__DEFAULT_UI_TIMEZONE=Asia/Shanghai`, `TZ=Asia/Shanghai`, and frontend build arg `VITE_DISPLAY_TIME_ZONE=Asia/Shanghai`; frontend Docker test target passed 15 tests; backend/frontend/Airflow containers report `date` as `+0800 CST`; Airflow logs show `+0800` and `Configured default timezone Asia/Shanghai`; frontend bundle contains `Asia/Shanghai`
last_sample_status_sync: passed on fengxian at commit 065907c; red backend tests first showed submit/sync left samples `pending`, then implementation passed targeted 3 tests and full backend pytest 48 passed; backend redeployed healthy; explicit sync refreshed visible runs, e.g. `PGTA_20260706_141915_5BE5E2` samples `E2/E3=success`, `PGTA_20260706_140854_8F2CA4` sample `E2=success`, and `WES_20260705_164813_C5561C` samples `S001/S002=success`
last_pgta_64core_autosync: passed on fengxian at commit fb107a4; compose renders `PGTA_SNAKEMAKE_CORES=64`; Airflow image unit tests for `bio_pgta`/`bio_pgta_airflow` command construction passed 4 tests; frontend Docker test target passed 16 Vitest tests including active-run auto sync and terminal stop; Airflow import errors returned `No data found`; frontend image rebuilt/redeployed at 12959 and returned HTTP 200; current baseline_qc run `PGTA_20260706_162150_00C4FD` remained `running` and was not interrupted
last_pgta_baseline_t092_monitor: 2026-07-07 14:11 CST read-only check on fengxian found compose config ok and services running; Airflow `bio_pgta` run `manual__PGTA_20260706_162150_00C4FD` still `running`; task states show `validate_request=success`, `prepare_pgta_config=success`, `run_pgta_target=running`, `collect_pgta_artifact=None`; backend run status and samples G10/G11 are `running`; `logs/snakemake.command.txt` contains `--cores 1` because the run started before T091; G10 mapping is complete with BWA real time 33885.400 sec, G11 BWA log is still updating; no `qc/baseline` files, no `/qc` metrics, and artifacts currently only include command/config; no `sync-airflow`, restart, retry, or new run was executed
last_pgta_t093_resume: 2026-07-07 18:09 CST on fengxian at commit 2821a5e; backend pytest 50 passed, Airflow DAG unittest 43 OK/5 skipped logger-interface-in-this-Python-env, frontend Docker test 17 passed, Airflow import errors `No data found`; old run `manual__PGTA_20260706_162150_00C4FD` was controlled-interrupted from exact matching Snakemake/BWA/Samtools processes and synced to backend `failed` with non-null `error_summary`; new resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T095201Z` is running, command contains `--cores 64 --rerun-incomplete`, unlock command contains `--unlock`, no `--forceall`, and active G11 processes show `bwa mem -t 16` plus `samtools sort -@ 16`; no `qc/baseline` terminal files yet
last_pgta_t094_resume_cleanup: 2026-07-07 20:13 CST on fengxian at commit 0a8e756; red tests first failed on missing tmp cleanup and missing cleanup artifact; after fix, compose config passed, backend image rebuilt and full pytest passed 51 tests, Airflow DAG unittest discover passed 44 tests with 5 logger-interface skips, Airflow import errors returned `No data found`; backend and Airflow scheduler/worker were recreated without touching Postgres/Redis/frontend or volumes; pre-resume check found 16 stale `mapping/G11.sorted.bam.tmp.*.bam` files and no matching running processes; resume run `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` started, `logs/pgta.resume.cleanup.tsv` recorded deletion of all 16 tmp BAMs, remaining tmp count is 0, command contains `--cores 64 --rerun-incomplete` and no `--forceall`, artifacts API exposes `pgta_resume_cleanup`, backend sync shows status `running`, and active process currently shows G11 `fastp -w 16`; terminal baseline QC artifacts still pending
last_pgta_t095_python_preflight: 2026-07-07 22:53 CST on fengxian at commit 3bd1270; initial read-only failure check found T094 resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T121252Z` failed in `baseline_bam_uniformity_qc` with `ImportError: /usr/lib/x86_64-linux-gnu/libstdc++.so.6: version CXXABI_1.3.15 not found`; first T095 commit `966e0d8` added conda `LD_LIBRARY_PATH`, run-local `MPLCONFIGDIR`, and preflight, but Airflow task resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T143132Z` still failed preflight; final fix `3bd1270` adds `LD_PRELOAD=/biosoftware/miniconda/envs/snakemake_env/lib/libstdc++.so.6`, remote DAG unittest passed 47 tests with 5 expected logger-interface skips, `docker compose config --quiet` passed, Airflow import errors returned `No data found`, direct worker preflight logged `matplotlib/numpy/pandas/pysam/scipy` versions, final resume `manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z` reached Airflow/backend `success`; artifacts include `pgta_python_preflight`, `pgta_baseline_qc_summary`, `pgta_baseline_qc_pass_samples`, `pgta_baseline_qc_report`; `/api/runs/PGTA_20260706_162150_00C4FD/qc` returns `pass=0,warn=0,fail=14,unknown=0`, and samples G10/G11 are workflow `success` with QC status `fail`
last_pgta_frontend_airflow_reconcile: 2026-07-08 on fengxian at commit f64e0d2; T098 deployed backend/frontend only, no new analysis submitted; `/api/health` ok and `/api/health/airflow` healthy; `/api/runs?pipeline=pgta&limit=50&offset=0` returned 17 PGT-A analysis runs and `PGTA_20260706_162150_00C4FD` list item now shows `status=success,qc_status=fail`; detail shows latest `dag_run_id=manual__PGTA_20260706_162150_00C4FD__resume__20260707T144147Z`; `/qc` returns `pass=0,warn=0,fail=14,unknown=0`; Airflow `bio_pgta` lists 20 DAG runs total, with 5 matching that analysis because of resume history, and the latest matching DAG run is `success`
last_pgta_t099_run_tracker: 2026-07-08 on fengxian; T099 deployed frontend only, no new analysis submitted; frontend bundle contains `PGT-A Run Tracker`; `/api/health` ok and `/api/health/airflow` healthy; `/api/runs?pipeline=pgta&limit=20&offset=0` returned 19 PGT-A analysis runs and includes `PGTA_20260707_182024_8CA2A0` plus `PGTA_20260707_182056_39A374`; both run details return non-null `dag_run_id` (`manual__PGTA_20260707_182024_8CA2A0`, `manual__PGTA_20260707_182056_39A374`) and `status=success`; `PGTA_20260706_162150_00C4FD/qc` remains `pass=0,warn=0,fail=14,unknown=0`
last_pgta_t100_submit_autosync: 2026-07-08 on fengxian; user-reported stuck run `PGTA_20260708_012630_352915` had backend `status=submitted` and `dag_run_id=manual__PGTA_20260708_012630_352915`, while Airflow CLI showed that DAG run had already reached `success` at `2026-07-08T01:26:43.802222+00:00`; a safe manual `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow` reconciled backend status to `success` without rerunning workflow; T100 frontend fix now calls `sync-airflow` after Submit handoff and auto-syncs active Dashboard tracker runs; frontend Docker test target passed 7 tests, compose config/build/recreate passed, frontend 12959 returned HTTP 200, `/api/health` ok, `/api/health/airflow` healthy, and `/api/runs?pipeline=pgta&status=submitted&limit=20&offset=0` returned no stuck submitted PGT-A runs
last_image_check: passed on fengxian; compose external images pulled and backend built with explicit tag
last_image_cleanup: removed 37 dangling <none> images; no docker system prune, no volume prune
last_pgta_failure_smoke: passed on fengxian; `invalid_target` run `PGTA_20260703_170957_3DDEC3` ended Airflow/backend `failed` as expected, stderr log size 1322 bytes, `sync-airflow` wrote non-null `error_summary` containing `stderr_path` and last error lines
last_wes_mock_dryrun: passed on fengxian official mirror at `/home/jiucheng/project/airflow-demo`; Snakemake 8.5.4 dry-run for `pipelines/wes/workflow/Snakefile` showed 8 jobs across all/fastp/bwa_mem/markdup/final_summary
last_mock_qsub_wrapper: passed on fengxian official mirror with backend POST; analysis `WES_20260704_180650_MOCK` generated `MOCK-WES_20260704_180650_MOCK-12-bwa_mem-S001`, qsub stdout/stderr files, submitted/success JSONL events, and `/api/runs/WES_20260704_180650_MOCK/rules` returned `bwa_mem/S001=success`
last_qsub_profile_runtime: passed on fengxian official mirror with `airflow-demo/snakemake-runner:0.1.0`; `WES_PROFILE_20260704_230713` ran `snakemake --profile profiles/qsub`, Snakemake 9.23.1 saw `cluster-generic`, executed 8 WES mock jobs, wrote `reports/final_summary.tsv`, qsub stdout/stderr files, and 14 JSONL events containing `qsub_submitted`/`qsub_success`
last_wes_airflow_qsub_smoke: passed on fengxian official mirror with `airflow-demo/airflow:0.1.0`; `WES_AIRFLOW_20260705_004506` / `manual__WES_AIRFLOW_20260705_004506` ended Airflow `success`, wrote `reports/final_summary.tsv` with `S001/S002 mock_success`, qsub stdout/stderr files, and 14 JSONL events; `collect_wes_artifacts` XCom returned `event_count=14` and `qsub_log_count=14`
last_wes_reanalysis_smoke: passed on fengxian official mirror; API/frontend-created `WES_20260705_162041_2507AF` initial submit, `resume`, and `rerun_rule fastp/S001` all reached Airflow/backend `success`; `/rules` returned 7 rows; `logs/events/snakemake_events.jsonl` has 28 lines; `logs/snakemake.command.txt` contains `--forcerun fastp` and no `--forceall`
last_wes_qc_smoke: passed on fengxian official mirror; API/frontend-created `WES_20260705_164813_C5561C` submitted to `bio_wes_qsub`, sync reached `success`, `/qc` returned `pass=6,warn=0,fail=0,unknown=0` with 6 items, artifacts included `wes_qc_summary`, and `reports/qc_summary.tsv` exists
last_e2e_smoke: T080/T081 read-only demo smoke on fengxian at mirror head 3310134 confirmed frontend HTTP 200, backend health ok, Airflow metadatabase/scheduler healthy; PGT-A `PGTA_20260706_162150_00C4FD` workflow status success with G10/G11 QC status fail and `/qc` summary `pass=0,warn=0,fail=14,unknown=0`; WES QC run `WES_20260705_164813_C5561C` success with `/qc` summary `pass=6,warn=0,fail=0,unknown=0`; WES rerun_rule run `WES_20260705_162041_2507AF` success with command containing `--forcerun fastp` and no `--forceall`; full email/NIPT E2E not run
```

## 8. 已知问题

| ID | Issue | Severity | Owner | Next step |
|---|---|---|---|---|
| K003 | BS10610 与 fengxian 用户和路径不同，不能复用 fengxian 硬编码路径 | medium | infra/coordinator | 迁移前把路径参数化到 `.env` 并重复 Level 0 preflight |
| K004 | 远端直接访问 GitHub release 不稳定 | low | infra | 优先本地 GitHub 下载后 scp 到 fengxian；国内 Docker CE 镜像作为 Compose fallback |
| K005 | fengxian 仍有非 airflow-demo 的 `latest` 镜像和未使用 volumes | low | infra | 未经确认不要删除；本轮只清理 dangling images，不碰非项目镜像和 volume |
| K006 | fengxian 宿主机 3000 已被非项目 `next-server` 占用 | low | infra | airflow-demo frontend 改用 12959；不要停止非项目进程 |
| K007 | BS NIPT-only 部署依赖共享外部 Docker 网络，错误 IPAM 或静态 IP 冲突会影响同网段服务 | high | infra | 启动前检查 `nipt_analysis_test_net` 必须为 `192.168.199.0/24`、gateway `192.168.199.1`，并核对当前 attachments；不允许自动修复或替换网段 |

## 9. 当前阻塞

```text
真实部署/启动前阻塞:
- 真实 `qsub/qstat` 在 `fengxian` 仍不可用；当前 WES/NIPT qsub demo 只能使用 mock qsub wrapper，不提交真实集群任务
- PGT-A `baseline_qc` staged real run `PGTA_20260706_162150_00C4FD` 已通过 final resume 成功；当前不是 workflow blocker，但 G10/G11 的 baseline QC decision 均为 `FAIL`，后续若要作为演示成功样本需要评估数据或阈值
```

## 10. 下一步建议

```text
1. 若要正式启用自动扫描，先规划 T107：只在用户明确批准后修改 `config/intake.yaml` gates 并 unpause `bio_intake_scan`，用 before/after run-count 检查收口。
2. 执行 T082：整理回滚/清理 runbook，重点是不删除 volumes、不碰生产 PGT-A/NIPT 源目录、不盲目重跑 baseline_qc 或 NIPT full_run。
3. 执行 T034/T063：补 MailHog success/failure 邮件通知，邮件包含 run detail、QC/report、错误摘要链接。
4. 若演示需要 PGT-A QC pass 样本，先做只读数据/阈值审计，不要盲目重跑 baseline_qc。
```

## 11. T106 Intake dry-run preview and auto-submit gate checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/intake/T106-intake-dry-run-gating` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T106 adds a safety layer before automatic intake is ever unpaused:

- New backend `POST /api/intake/scan-preview` scans configured PGT-A/NIPT roots
  and returns dry-run rows plus summary counts without writing DB state,
  creating runs, or triggering Airflow.
- `POST /api/intake/scan-and-submit` now obeys both
  `defaults.auto_submit` and `pipelines.<name>.auto_submit.enabled` from
  `config/intake.yaml`.
- Default `config/intake.yaml` keeps PGT-A and NIPT Docker automatic
  create+submit disabled.
- Settings shows `Preview configured roots`, a read-only preview panel, and
  blocked-by-config reasons; it still has no unpause, scan-now submit, or
  full-run action.
- NIPT run creation now uses intake config roots with env fallback, so scanner
  and run creation validate against the same configured source roots.

Remote validation on `ssh fengxian`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- backend Docker targeted pytest passed: `8 passed`.
- frontend Docker test target passed: `11 passed`.
- backend/frontend build and recreate passed; frontend production build ran
  `tsc -b && vite build`.
- Frontend `http://127.0.0.1:12959/` returned HTTP 200.
- `/api/health` and `/api/health/airflow` returned healthy payloads.
- `/api/intake/config` showed global and pipeline auto-submit gates disabled.
- `/api/intake/scan-preview` returned `total_batches=21,would_submit=0`.
- Preview did not mutate state: intake discovery count stayed `21/21`, NIPT
  run count stayed `5/5`.
- `bio_intake_scan` remained paused (`airflow dags list` final column `True`).

Known caveat: a future auto-intake enablement task must be explicit and reviewed before changing gates
or unpausing `bio_intake_scan`.

## 12. T107 UI density and PGT-A staged DAG checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T107-ui-pgta-dag-stages` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T107 is implemented and remotely validated. Scope:

- Submit Task preview now uses a definition-style field layout so labels and
  values no longer collide; long scan root and workflow fields wrap on their
  own full-width rows.
- Samples views use `source files` instead of `fastq_path`, showing R1/R2
  basenames and a batch/folder secondary line when `metadata.source_dir` is
  available. Legacy rows show `Path not captured for this run`.
- Run Detail QC uses a compact sample-by-metric matrix with fail/warn-first
  sorting, sample search, status filter, and 20-row pagination.
- PGT-A `baseline_qc` now branches into an Airflow TaskGroup:
  `pgta_pipeline.run_pgta_mapping -> pgta_pipeline.run_pgta_metadata ->
  pgta_pipeline.run_pgta_baseline_qc`.
- PGT-A `metadata`, `dryrun_cnv`, and `invalid_target` continue to use the
  historical `run_pgta_target` task.
- Runner staging writes `logs/snakemake.<stage>.stdout.log`,
  `logs/snakemake.<stage>.stderr.log`, and
  `logs/snakemake.<stage>.command.txt`, plus stage events for Pipeline steps.
- `/api/runs/{analysis_id}/progress` keeps the same response shape but now
  knows T107 PGT-A stage task weights.

Remote validation on `ssh fengxian`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker build --no-cache --target test -f frontend/Dockerfile frontend`:
  passed, 13 Vitest tests.
- backend Docker targeted pytest passed: 19 tests.
- Airflow worker unittest passed: 27 tests for `bio_pgta` DAG and
  `pgta_metadata_runner`.
- Airflow import check returned `No data found`.
- backend, airflow-worker, airflow-scheduler, and frontend images rebuilt and
  recreated without deleting volumes.
- Frontend `http://127.0.0.1:12959/` returned HTTP 200; `/api/health` returned
  ok and `/api/health/airflow` returned healthy metadatabase/scheduler.
- `airflow tasks list bio_pgta --tree` shows the staged TaskGroup plus the
  historical `run_pgta_target` branch.
- Light PGT-A metadata smoke `PGTA_20260708_141653_B57AB6` reached backend and
  Airflow `success`.

Local limitations and deliberate exclusions:

- Local Windows `python` shim was unusable; `py` exists but local backend tests
  lack FastAPI and Airflow dependencies.
- Local runner unittest runs under Windows but existing POSIX path assertions
  fail on backslash paths; remote Linux/container validation was used.
- Local Node/NPM are unavailable, so frontend tests/build ran in the remote
  frontend Docker test target.
- No heavy PGT-A `baseline_qc` run has been started by T107.

## 12. T096 frontend platform redesign checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T096-platform-ui-redesign` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T096 upgrades the frontend from the prior single workspace into a routed bioinformatics operations platform while preserving the existing PGT-A and WES backend API behavior. New documentation is in `DESIGN.md`, `docs/frontend-design-review.md`, and `docs/frontend-spec.md`; `docs/06_FRONTEND_SPEC.md` now points to the v2 structure.

Implemented frontend routes:

```text
/dashboard
/submit
/runs
/runs/:analysisId
/samples
/workflows
/failures
/settings
```

Implemented shared components include `StatusBadge`, `MetricCard`, `PipelineCard`, `RunTable`, `WorkflowTimeline`, `LogViewer`, `SampleSheetUploader`, `PipelineSelector`, `ErrorPanel`, and `QcMetricCard`. Status semantics are centralized in `frontend/src/lib/status.ts`; mock/demo NIPT, WGS, workflow-template, and resource data are isolated in `frontend/src/mocks/platform.ts`.

Remote validation on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, 7 Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 after nginx readiness.
- `GET http://127.0.0.1:8000/api/health`, `/api/health/db`, and `/api/health/airflow`: all returned ok/healthy.
- Existing PGT-A run `PGTA_20260706_162150_00C4FD` detail, samples, and stderr log endpoints returned data.
- Existing WES run `WES_20260705_170904_5D1C74` detail, rules, and QC endpoints returned data.

Local notes: local Windows has no `node`, `npm`, or `docker`; local checks remain git/docs/manifest only. `frontend/package.json` has no `lint` script, so `npm run lint` was not run.

## 12. T097 PGT-A-only frontend deployment scope

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T097-pgta-only` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

The current frontend deployment target is PGT-A-only. This supersedes the T096 visible product surface for demo purposes:

- Sidebar shows Dashboard, Submit Task, Runs, Samples, Failures, and Settings. Workflows is not linked in the sidebar.
- Dashboard, Runs, Samples, and Failures filter to `pipeline=pgta` and do not surface WES/NIPT/WGS demo entries.
- Submit Task only exposes the PGT-A server-path scan/create/submit path.
- Run Detail keeps PGT-A tabs, logs, QC, files, config, sync, and baseline_qc `Resume with 64 cores`.
- Direct `/workflows` navigation remains development-accessible but displays only the PGT-A workflow template.
- Historical WES qsub backend/DAG/Snakemake code is intentionally left in place but is no longer a current deployable frontend entry.
- NIPT/WGS remain hidden from the current frontend demo.
- MailHog/SMTP notification work is not part of T097; `T034` and `T063` remain todo.

Remote validation and deployment on `ssh fengxian`:

- Remote mirror switched to `codex/frontend/T097-pgta-only` at frontend code commit `3119be5`.
- `docker build --no-cache --target test -f frontend/Dockerfile frontend`: passed, `1 test file`, `5 tests`.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only the frontend container.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: returned `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.
- `GET /api/runs/PGTA_20260706_162150_00C4FD`: returned PGT-A detail data.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/qc`: returned `pass=0,warn=0,fail=14,unknown=0`.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/logs?stream=stderr&tail=20`: returned stderr tail lines.

## 13. T099 PGT-A Dashboard run tracker and submit handoff

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T099-pgta-run-tracker` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

The current deployed frontend remains PGT-A-only. T099 changes the main operator experience:

- Dashboard no longer splits recent failed and completed runs into separate blocks. It shows one large `PGT-A Run Tracker` ordered by active, failed/QC failed, created-only, then recent success runs.
- Each tracker row shows project name from `params.project_name` when available, `analysis_id`, workflow status, QC status, current step, progress estimate, progress bar, samples, created/started/duration fields, and View/Submit/Sync actions.
- Tracker filters are All, Running, Submitted / queued, Created only, Failed, QC failed, and Success.
- Created-only runs show `Not in Airflow`; active runs can be synced and are eligible for 15-second Dashboard polling.
- Dashboard bottom panels are now Service health, PGT-A resource overview, and PGT-A workflow.
- Submit Task primary action is `Create and submit to Airflow`; it calls `POST /api/runs`, then `POST /api/runs/{analysis_id}/actions/submit`, then fetches detail and displays `dag_run_id`.
- `Create only` remains available as a secondary action and explicitly warns that the run is not visible in Airflow until submitted.
- Scan results are grouped by source folder, with FASTQ file names behind an expand control and absolute paths hidden by default behind `full path`.

Remote validation and deployment on `ssh fengxian`:

- `docker build --target test -f frontend/Dockerfile frontend`: passed, `7` Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only frontend.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: returned `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.

## 14. T104 Dashboard aggregation and intake config checkpoint

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/dashboard/T104-dashboard-intake-config` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T104 changes the Dashboard from frontend fan-out requests into backend
aggregation:

- New backend APIs: `/api/dashboard/overview`, `/api/dashboard/runs`,
  `/api/system/resources`, and `/api/intake/config`.
- New config file: `config/intake.yaml`; backend reads it through
  `INTAKE_CONFIG_PATH=/app/config/intake.yaml` and keeps env roots as fallback.
- Dashboard first screen uses overview, dashboard/runs, intake/status, and
  system/resources; it does not call run detail, `/progress`, or `/rules` for
  each visible run.
- Run Tracker defaults to 10 rows per page, supports pipeline selector,
  status filter, keyword search, previous/next pagination, progress bar,
  current Airflow task, and current pipeline rule.
- Intake scanner states distinguish `Observed`, `Stable ready`,
  `Auto-submitted`, `Bootstrap observed`, `Disabled`, and `Error`; observed
  bootstrap rows are not displayed as queued workflow execution.
- Bottom Dashboard panels are `Service & Node Health`, `Pipeline Resources`,
  and `Workflow Activity`.

Validation completed so far:

- Local Python syntax check passed for changed backend modules.
- Remote backend Docker targeted pytest passed: 7 tests
  (`test_dashboard_service.py`, `test_intake_config.py`,
  `test_system_resources.py`).
- Remote frontend Docker test target passed: 10 Vitest tests.
- Remote `docker compose -f docker-compose.yaml config --quiet` passed.
- Remote `airflow dags list-import-errors` returned `No data found`.
- Remote build/recreate passed for backend, airflow-worker, airflow-scheduler,
  and frontend; frontend production build ran `tsc -b && vite build`.
- Frontend `http://127.0.0.1:12959/` returned HTTP 200.
- Backend `/api/health` returned ok; `/api/health/airflow` returned healthy
  scheduler and metadatabase.
- Runtime `/api/dashboard/overview?pipeline=all` returned 26 visible PGT-A/NIPT
  runs, 0 running, 8 failed, and intake summary with 21 bootstrap rows.
- Runtime `/api/dashboard/runs?pipeline=all&limit=10&offset=0` returned
  `limit=10`, `items=10`, `total=26`.
- Runtime `/api/system/resources` returned `source=host_proc`, 128 CPU cores,
  and disks `/` plus `/data`.
- Runtime `/api/intake/config` returned `source=/app/config/intake.yaml` with
  pipelines `pgta` and `nipt_docker`.
- Endpoint timing on `fengxian`: dashboard overview about 0.019s; dashboard runs
  first page about 1.641s.
- `bio_intake_scan` remains paused (`airflow dags list` final column `True`).
- `GET /api/runs?pipeline=pgta&limit=20&offset=0`: returned 19 total PGT-A analysis runs, including `PGTA_20260707_182024_8CA2A0` and `PGTA_20260707_182056_39A374`.
- Both July 7 run details returned non-null `dag_run_id` and `status=success`.
- `GET /api/runs/PGTA_20260706_162150_00C4FD/qc`: returned `pass=0,warn=0,fail=14,unknown=0`.

## 14. T100 PGT-A submit/Airflow status auto-sync

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/frontend/T099-pgta-run-tracker` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

T100 addresses the user-reported symptom: after creating and submitting a PGT-A project, the frontend stayed at `submitted` and the operator could not tell whether Airflow had entered the workflow.

Root cause found on `fengxian`:

- `PGTA_20260708_012630_352915` existed in biodemo with `status=submitted`, `dag_run_id=manual__PGTA_20260708_012630_352915`, `started_at=null`, `ended_at=null`, and no rule events.
- Airflow showed the same DAG run had already completed with `state=success`.
- The frontend Submit flow fetched run detail after `/actions/submit`, but did not call `/actions/sync-airflow`; Dashboard also waited for user/manual sync rather than reconciling active tracker rows immediately.
- A manual `POST /api/runs/PGTA_20260708_012630_352915/actions/sync-airflow` reconciled that run to backend `status=success` without creating or rerunning any workflow.

Implemented frontend behavior:

- Dashboard auto-syncs active/submitted PGT-A tracker runs immediately and every 15 seconds through backend `sync-airflow`, then reloads tracker data.
- Submit Task primary `Create and submit to Airflow` now calls `sync-airflow` after a successful Airflow handoff with `dag_run_id`, retrying briefly so fast metadata runs can move from `submitted` to `success` in the handoff summary.
- If Airflow is still running after the brief sync window, the Dashboard tracker continues polling and syncing until terminal state.

Remote validation and deployment on `ssh fengxian`:

- Red frontend test target first failed as expected because Dashboard and Submit did not call `sync-airflow`.
- `docker build --target test -f frontend/Dockerfile frontend`: passed after implementation, `7` Vitest tests.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker compose -f docker-compose.yaml build frontend`: passed, including `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate frontend`: passed, recreated only frontend.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200 from nginx.
- `GET /api/health`: returned `{"status":"ok"}`.
- `GET /api/health/airflow`: metadatabase and scheduler healthy.
- `GET /api/runs/PGTA_20260708_012630_352915`: returned `status=success`, `dag_run_id=manual__PGTA_20260708_012630_352915`, and Airflow start/end timestamps.
- `GET /api/runs?pipeline=pgta&status=submitted&limit=20&offset=0`: returned no stuck submitted PGT-A runs.

Remaining limitation: progress is still a frontend estimate from backend run/rule data. A future backend Airflow task-instance endpoint is needed for authoritative per-task progress and Airflow attempt history.

## 15. T101 NIPT Docker template-run deployment

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/nipt/T101-nipt-docker-demo` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Current deployable frontend surface is now PGT-A + NIPT Docker. WES qsub, NIPT qsub, WGS, and mail notification remain hidden/deferred in the current demo.

Implemented:

- Backend `POST /api/runs` supports `pipeline=nipt_docker` with `template_id=run1|run2`, `run_mode=mount_smoke|full_run`, `cores`, `project_name`, and `note`.
- Backend submit supports `nipt_docker` and triggers Airflow DAG `bio_nipt_docker`.
- `full_run` remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`; default acceptance uses `mount_smoke`.
- Airflow DAG `bio_nipt_docker` has task graph `validate_request -> prepare_nipt_docker_run -> run_nipt_docker -> collect_nipt_artifacts`.
- Runner writes `nipt_run_config.yaml`, `nipt_docker_compose.yml`, `nipt_airflow_request.json`, `nipt_docker.command.txt`, stdout/stderr logs, and `reports/qc_summary.tsv`.
- Airflow worker mounts the NIPT bundle and Docker socket; `group_add=${DOCKER_SOCKET_GID:-114}` is required on `fengxian` for socket access. Scheduler/API server do not mount the Docker socket.
- QC import parses NIPT `reports/qc_summary.tsv`, updates `qc_metric`, and refreshes `sample.qc_status`.
- Artifact API filters pipeline-specific artifacts; NIPT runs expose NIPT artifacts and no longer expose WES `wes_qc_summary`.
- Frontend Dashboard/Submit/Runs/Samples/Workflows/Failures support PGT-A and NIPT Docker only.

Remote validation on `ssh fengxian`:

- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `git diff --check`: passed.
- `docker build --target test -f frontend/Dockerfile frontend`: passed, 9 Vitest tests.
- `docker build -t airflow-demo/backend:t101-test -f backend/Dockerfile backend && docker run --rm airflow-demo/backend:t101-test pytest -q tests/test_nipt_docker_lifecycle.py tests/test_run_creation.py tests/test_run_submit.py tests/test_run_diagnostics.py`: passed, 31 tests.
- After artifact/QC refinement: `pytest -q tests/test_nipt_docker_lifecycle.py tests/test_run_diagnostics.py`: passed, 17 tests.
- `docker run --rm --entrypoint /usr/local/bin/python -v /home/jiucheng/project/airflow-demo/dags:/opt/airflow/dags:ro -w /opt/airflow airflow-demo/airflow:t101-test -m unittest /opt/airflow/dags/tests/test_bio_nipt_docker_dag.py /opt/airflow/dags/tests/test_nipt_docker_runner.py -v`: passed, 9 tests.
- `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler airflow-api-server frontend`: passed; frontend build ran `tsc -b && vite build`.
- `docker compose -f docker-compose.yaml up -d --no-deps --force-recreate backend airflow-api-server airflow-scheduler airflow-worker frontend`: passed.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200.
- `/api/health` and `/api/health/airflow`: healthy after Airflow API server readiness.
- `airflow dags list-import-errors`: `No data found`.
- `airflow dags list` showed `bio_nipt_docker`.
- Initial smoke `NIPT_20260708_032949_C7F56B` failed because worker lacked Docker socket group permission; fixed by adding `DOCKER_SOCKET_GID=114` and worker `group_add`.
- Successful smoke `NIPT_20260708_033128_7B6386` proved Docker execution after socket group fix.
- Final smoke `NIPT_20260708_033450_8362A0` reached Airflow/backend `success`, QC `pass=96,warn=0,fail=0,unknown=0`, run list `qc_status=pass`, stdout `mount_smoke_ok NIPT_20260708_033450_8362A0 260414_TPNB500380AR_1065_AH32CCBGY2`, and artifacts `nipt_qc_summary`, `nipt_docker_compose`, `nipt_run_config`, `nipt_airflow_request`, `nipt_docker_command`.

Known caveats:

- `full_run` was not executed; this remains intentionally blocked unless the user explicitly approves a heavy NIPT batch.
- Historical failed smoke `NIPT_20260708_032949_C7F56B` remains in DB/Airflow history as evidence of the pre-fix Docker socket permission issue.
- T102 supersedes the T101 progress caveat: frontend progress now uses backend `/progress` with Airflow task instances plus runner rule events. Historical runs without captured rule events still show Airflow task progress.

## 16. T102 Airflow + Snakemake progress observability

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/progress/T102-airflow-snakemake-progress` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Implemented:

- Backend endpoint `GET /api/runs/{analysis_id}/progress` combines biodemo run state, Airflow REST task instances, and `snakemake_rule_event` rows.
- `AirflowClient.list_task_instances()` reads `/api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances`; no direct Airflow DB reads.
- PGT-A and NIPT Docker submit conf includes `backend_event_url=http://backend:8000/api/events/snakemake`.
- `dags/common/progress_events.py` writes runner events to JSONL and optionally POSTs to backend; POST failure is non-fatal.
- PGT-A runner emits target-level progress events and parses Snakemake stdout/stderr for rule blocks.
- NIPT Docker runner emits `nipt_mount_smoke` events and parses full-run Docker stdout/stderr when heavy mode is enabled.
- `sync-airflow` imports JSONL fallback events on terminal runs.
- Dashboard and Run Detail use `/progress`; Run Detail Workflow tab shows `Airflow tasks` and `Pipeline steps`.

Remote validation on `ssh fengxian`:

- `git diff --check`: passed.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- Backend targeted Docker tests passed: `29 passed`.
- Airflow DAG/runner Docker unittest passed: `35 tests OK`.
- Frontend Docker test target passed: `10` Vitest tests.
- Production build passed for backend, Airflow worker/scheduler/API server, and frontend; frontend build ran `tsc -b && vite build`.
- Recreated backend, Airflow API/scheduler/worker, and frontend without deleting volumes.
- `curl -fsSI http://127.0.0.1:12959/`: HTTP 200.
- `/api/health`: ok; `/api/health/airflow`: metadatabase and scheduler healthy.
- `airflow dags list-import-errors`: `No data found`.
- Historical `/api/runs/PGTA_20260706_162150_00C4FD/progress` returned Airflow task timeline with `percent=100`.
- Historical `/api/runs/NIPT_20260708_033450_8362A0/progress` returned Airflow task timeline with `percent=100`.
- New PGT-A metadata smoke `PGTA_20260708_050811_A24E36` reached success with Airflow tasks and `metadata=success` pipeline event.
- New NIPT Docker mount smoke `NIPT_20260708_050843_B3B05E` reached success with Airflow tasks and `nipt_mount_smoke=success` pipeline event.

Known caveats:

- Historical runs before T102 cannot reconstruct missing Snakemake/runner events; they still show Airflow task-instance progress.
- NIPT `full_run` was not executed; it remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- Mail notification, WES qsub frontend restore, NIPT qsub, and WGS remain out of current deployable scope.

## 17. T103 PGT-A/NIPT batch scan and auto intake

Date: 2026-07-08
Agent: Codex
Branch/worktree: `codex/intake/T103-pgta-nipt-auto-scan` at `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Implemented:

- `POST /api/input/scan` supports `pipeline=pgta|nipt_docker`; `GET /api/input/roots` returns pipeline-specific scan roots.
- NIPT scan discovers chip folders with top-level `*.clean.fastq.gz` R1/R2 pairs and ignores nested adapter FASTQs in v1.
- New NIPT Docker create requests use `rawdata_root` and `selected_samples` from scan results; `template_id` is compatibility-only and no longer exposed in Submit Task.
- NIPT run params include `input_mode=nipt_docker_scan`, `source_batch_dir`, `source_batch_id`, `source_fingerprint`, `input_file_flavor=clean`, `chip_name`, and `selected_count`.
- `bio_nipt_docker` prepares a run-local chip CSV/config/compose and mounts the source batch read-only as `/input_batch`; no large FASTQ copy and no production bundle writes.
- Added `intake_discovery` table plus `/api/intake/status` and `/api/intake/scan-and-submit`.
- Added `bio_intake_scan`, paused on creation by default; bootstrap must record historical batches before unpausing automatic intake.
- Dashboard shows read-only Intake auto scanner status. Submit Task scans PGT-A/NIPT roots and creates one NIPT run per selected chip batch.

Remote validation on `ssh fengxian`:

- `git diff --check`: passed.
- Manifest check: `file_count=179`, listed files `179`, missing `0`.
- `docker compose -f docker-compose.yaml config --quiet`: passed.
- `docker build --target test -f frontend/Dockerfile frontend`: passed, 10 Vitest tests.
- Backend Docker targeted pytest passed: 25 tests.
- Airflow DAG tests passed: 4 tests for `bio_intake_scan`/`bio_nipt_docker`; NIPT runner/progress tests passed: 12 tests.
- `docker compose -f docker-compose.yaml build backend airflow-worker airflow-scheduler frontend`: passed; frontend build ran `tsc -b && vite build`.
- Recreated backend, airflow-scheduler, airflow-worker, and frontend without deleting volumes; `alembic upgrade head` applied `20260708_0002`.
- Frontend HTTP 200 on `http://127.0.0.1:12959/`; `/api/health` ok; `/api/health/airflow` scheduler/metadatabase healthy.
- `airflow dags list-import-errors`: `No data found`; `bio_intake_scan` listed paused, `bio_nipt_docker` and `bio_pgta` listed unpaused.
- `/api/input/roots?pipeline=nipt_docker` returned `/opt/pipelines/NIPT/fastq`.
- NIPT scan of `/opt/pipelines/NIPT/fastq` returned clean FASTQ candidates grouped under chip folder `FQ2025/250103_NDX550692_RUO_0044_AH3H37BGYW`.
- Scanned NIPT mount smoke `NIPT_20260708_072349_4F942A` submitted to `manual__NIPT_20260708_072349_4F942A` and reached Airflow/backend `success`.
- `/progress` for that run returned `percent=100`, Airflow task instances, and `nipt_mount_smoke=success` rule event.
- `/qc` returned `pass=1,warn=0,fail=0,unknown=0`; stdout contained `mount_smoke_ok NIPT_20260708_072349_4F942A 250103_NDX550692_RUO_0044_AH3H37BGYW`; artifacts included NIPT QC/config/compose/command entries.
- Intake bootstrap with `bootstrap=true,max_samples=20` recorded existing PGT-A/NIPT batches as `observed/bootstrap`; it did not auto-submit historical batches.

Known caveats:

- `bio_intake_scan` remains paused until explicitly unpaused after bootstrap review.
- NIPT `full_run` was not executed and remains guarded by `NIPT_ALLOW_HEAVY_RUN=false`.
- Auto-intake currently uses PGT-A `metadata` and NIPT `mount_smoke`; production full-run automation needs a separate explicit approval/config gate.
## 2026-07-08 T108 validated

Current branch/worktree:

- Branch: `codex/frontend/T108-dashboard-run-detail-usability`
- Worktree: `D:\pipeline\airflow-demo-worktrees\T096-platform-ui-redesign`

Implemented and deployed:

- Dashboard Run Tracker is now an operator-readable table:
  Project/Run ID links, combined current stage, progress, runtime/ETA, and
  timezone-clean timestamps.
- Dashboard `QC / failure focus` was replaced by `Sample throughput` with
  `24h / 7d / 30d` period selector and sample-level counts.
- Intake scanner display was converted from card wall to compact table
  with discovery state semantics.
- Backend dashboard aggregation exposes sample throughput, sample trend,
  human-readable stage labels, elapsed runtime, and ETA estimate fields.
- Run Detail now renders selected samples as a manifest table, adds QC failure
  summary above the QC matrix, prioritizes Snakemake/NIPT config artifacts, and
  adds a controlled `Run action` modal.
- PGT-A reanalysis now has a controlled `rerun_stage` API path for
  `mapping`, `metadata`, and `baseline_qc`; arbitrary DAG/task trigger remains
  out of scope.

Remote validation:

- `docker compose -f docker-compose.yaml config --quiet` passed.
- Frontend Docker test target passed 14 Vitest tests.
- Backend targeted pytest passed 25 tests.
- Airflow DAG/runner unittest passed 28 tests in `airflow-demo/airflow:t108-test`.
- `docker compose build backend airflow-worker airflow-scheduler frontend` passed, including frontend `tsc -b && vite build`.
- `docker compose up -d --no-deps --force-recreate backend airflow-worker airflow-scheduler frontend` passed.
- Frontend `12959` returned HTTP 200 and backend `/api/health` returned ok.
- Dashboard overview/runs/resource/intake APIs returned T108 fields.
- Light PGT-A metadata smoke `PGTA_20260708_160227_EFAD64` reached backend/Airflow `success`.

Not changed:

- `bio_intake_scan` remains paused.
- Auto-submit remains disabled by default.
- NIPT Docker DAG is not split in this task.
- NIPT `full_run` and heavy PGT-A `baseline_qc` are not run without explicit
  approval.
# 2026-08-12 T131 WGS cloud orchestration Phase 1

- BS10610 candidate release:
  `/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/releases/20260812-wgs-orchestration-t131-candidate`.
- Input is now `batch_no + fq_path` with paired FASTQ links; Airflow creates
  manifest, sampleinfo, config and MD5 in its own workdir. READY is obsolete.
- biodemo is at Alembic `20260812_0008`; snapshot, review issue, transfer
  progress and OBS lease structures are live.
- `bio_wgs_cce` has 27 task nodes and six reschedule sensors. All WGS DAGs are
  paused. Pools are hash=2, OBS=1, Master=4.
- Backend/frontend/observer/Airflow run on BS10610. Network remains external
  `192.168.199.0/24`; only `172.17.106.10:12959` is published.
- Both real and mock execution gates are false. Synthetic smoke
  `WGS_20260812_152720_643D8D` created run artifacts and submit returned 409;
  no CCE or OBS command ran.
- Upstream `/mnt/biodevrwbi/33.chenjiucheng/project/wgs` was not modified.
