# Run Tracker rule progress and WGS 4.2.2 phase restoration

Scope: presentation evidence only, no new recovery policy or analysis actions.

## Causes and correction

- Run Tracker preferred the stored manual-resume entry `step2_master` over the
  current DagRun's `wait_step3_analysis`. Prefer a recognized current Airflow task
  when the progress source is Airflow; preserve existing fallbacks otherwise.
- Query-reconnect status saves retained generic counters but dropped WGS nested
  `master` and its `master_job`, `namespace`, `run_label`. Preserve these from the
  exact registered current status. Unconfirmed observations remain fenced by the
  existing reconnect phase; retaining data is not authority to claim fresh progress.
- Production phase fixes were already present. Exact release
  `wgs-4.2.2-441d5e7` was not registered, so rules correctly failed closed to Unknown.

## Source audit

Read-only Git inspection on server10610:
`/bi/biodevrwbi/33.chenjiucheng/project/wgs-4.2.0`, commit
`441d5e7e78e00baed084479b50041bf917ff0b6f` versus audited `ebf1f4b`.
Of the14 pinned source files, only3 changed; existing rule names/module imports
remain, with six added concatSpecialSNV annotation rules in WGS_CS and WGS_SNV.
SMA edits change no rule names. Retained ROH override comes from ebf1f4b.
Record the four changed blobs relative to the base catalog in
`backend/app/policies/wgs_phases_cc9bde3.json`; additions apply only to441d5e7.
No arbitrary4.2.2 prefix fallback and no biological-equivalence claim.

## Verification / rollout boundary

BS10610 synthetic red/green: backend27 and monitor13 tests pass. No cloud test
Jobs, business-data tests or native package install. These tests were not repeated
during deployment. No commit/push in this deployment turn.

## Authorized production rollout

User confirmed BS96 deployment and node200 monitor/pin synchronization. Backend
only recreated, exact existing environment/image retained plus three RO overlays.
Active Compose and backend-only rollback under
`/data/airflow-WGS/tracker-rule-phase-20260928-control/` (private environment files).
Source release `/data/airflow-WGS/releases/20260928-tracker-rule-phase`.
All other service IDs unchanged; nginx config passed and graceful reload served200.

Node200 module change verified against deployed file: exactly six added lines.
Module SHA41782f6e2272c8c7e0e45b3bbc4429927e0dfaa9b9d11f80e4dcfc7851d34015,
policy SHAfd12f79b7f687de9c86c2f29270f1e0f9d2975e906241ad642613066c9786509.
Only platform source pin changed. Original private600/ctapa:bioinfo preserved;
no business permissions changed. Before files and worker/status evidence under
runtime/repair-backups/tracker-rule-phase-20260928.

Observer23305 (flock parent23127) refreshed only at no-child idle select(0) sleep,
not during evidence collection. Existing registered Step3 entry created observer
parent108152 with same execution9cd7cef, generation1, request hash7886a61f and
Step2 actionb694a889. Step2 action matched, so prepare_monitor_registered returns
without Master replacement. No Step1/2 rerun or attempt/input changes. Fresh
monitor binding retains Master UID50e76a69/generation2 and pod UIDff25f1a7.

Live API acceptance: dashboard current stage WGS workflow running, status running,
4/275 rules with current pre_process_mapping. Phase values from actual rule rows:
cloud_preflight->Preflight, cleanFastq->FASTQ QC, mapping->Mapping,
Dedup->Duplicate marking. Backend health and gateway200. Browser screenshot not
captured; acceptance is the live data contract consumed by existing Run Tracker.
Unrelated stale finished timestamp remains outside this scoped fix.
