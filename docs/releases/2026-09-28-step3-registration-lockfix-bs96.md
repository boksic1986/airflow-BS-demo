# BS96 WGS Step3 registration lock fix — 2026-09-28

## Scope and cause

User authorized production diagnosis/repair, prioritizing20260927B.
Run `WGS_20260928_101112_11111E`, attempt1, original `bio_wgs` DagRun `-a1`.
Upload succeeded374121176904bytes and Step2 succeeded. Master was already
computing; registering Step3 locked AnalysisRun, then an independent receipt
ingester session waited for that same row. Airflow timed out after15seconds.

Fix only transaction ordering in backend main.py: synchronize validated receipt
before taking registration's run-row lock; reread/revalidate under the original
lock. Preserve attempt, recovery identity, generation and Step7 authorization.
No native WGS/cce-pipeline, DAG, database model or timeout policy change.

## Source and minimal validation

- Source branch: `jiucheng/backend/20260928-step3-registration-lockfix`, base84510df.
- Code/test commit: `a2d0eeffa6781f06f178040b513435cba9326cee`; owner docs:b3e1e40.
- Final main.py SHA256: `975e1504441784162420691528ca3afbaa3fb6d0980f8b5b217b1d2e2d582ba5`.
- BS10610 `test_runtime_stage_sync_does_not_self_lock_run_row`:2passed in1.89s,
  one existing Starlette warning. Two parameter cases cover ordinary Step3
  receipt import and forced Step2 new generation with a terminal receipt.
- Actual imported candidate path/SHA printed. Initial fixture status/auth/import
  errors were corrected; old-source lock failures are not candidate acceptance.
- Independent reviewer caught empty-string recovery-ID semantics and local-import
  shadowing; both corrected before GREEN and production activation.
- No local pytest, whole suite, cloud synthetic jobs or repeated batch analysis.

## Deployment and rollback

Verified server96/chenjc; node200=t640/ctapa. Current symlink is historical;
actual container mounts were used. Backend only changed from e66622e215f1 to
0d69172001b2. New read-only mount:

`/data/airflow-WGS/releases/20260928-step3-stage-lockfix/main.py -> /app/app/main.py`.

Private control directory `/data/airflow-WGS/stage-lockfix-20260928-control`:
`rollback.json` copies the previous active backend composition; its environment
must not be printed or committed. Overlay `compose.override.yaml` adds only the
main.py mount. Structured config comparison preserved all existing backend
image/env/mounts and other services. Compose config passed before backend-only
`up -d --no-deps --pull never backend`; never remove orphan services.

Nginx syntax/reload passed; LAN172.17.61.96:12959/api/health200. Initial localhost
health probe403 was the unchanged allowlist, not backend failure. No access
control weakening. Final loaded file SHA matches above, restart count0, all
other Compose container IDs unchanged.

Rollback: apply only this control's rollback.json with projectairflow-wgs,
backend-only up, then nginx syntax/reload and LAN health check. It restores
prior code but not the old deadlocked transactions. Do not repeat task recovery
or alter active runtime work merely to roll back code.

## Recovery and result

Authenticated Airflow clearTaskInstances dry-run selected14 exact failed or
upstream_failed tasks in this DagRun. Executed once after deployment, with
reset_dag_runs=true and all upstream/downstream/future/past expansion disabled.
Tasks: start_step3_monitor, wait_step3_analysis, choose_after_step3,
finalize_step3_dryrun, start_step4_publish, wait_step4_publish,
result_transfer.acquire_obs_transfer_slot, result_transfer.start_step5_download,
result_transfer.wait_step5_download, materialize_step6_results,
wait_step6_materialize, finalize_run, result_transfer.release_obs_transfer_slot,
release_leases. No successful upload/Step2 task selected.

At12:59Z DagRun running, Step3 launcher success/try2, sensor up_for_reschedule;
upload and Step2 remain success/try1. New ordinary monitor execution
`wse_787c83953461d24db93f7fde` generation1 attaches to existing Master Job
`cce-master-a54badae71070e65fd4a`, UID `3cbf6f23-8334-4e46-a0e0-bbc9dbdc0a99`.
No new Master, attempt, request input, prepare or upload. Native receipt healthy,
RUNNING/normal,3/223rules; Tracker Step3/running,3/223, currentpre_process_mapping.
Native1.3% is rendered as integer1% by existing UI. First rule-evidence bridge
took about4minutes and then completed; no additional timeout patch needed.
Per-rule event count remains0 in progress API; this release does not claim the
Rules table is populated or analysis completed.

Preserved all offline directories, FASTQ, results, sampleinfo, pending, evidence,
native runtime0.8.8, permissions, production gates and unrelated worktree edits.
No direct production DB access/write, Step7 or cleanup. A SSH-prepare recovery
remains separate; D/WES were normal upload/shared-slot waiting observations.
