# Native monitoring display parity — BS10610 only

Approved scope: short batch/mode label, native dashboard progress/time/count,
expanded shared Rule table and less dense native details, current snapshot sample
listing. Keep preparation, pending, execution identity and running analysis unchanged.

## Root cause and changes

Backend test-gatk-phases update omitted the approved registration root, making
existing readable logs fail the project-root validator. This is collection failure,
not evidence of analysis failure. Preserve the GATK r2/r3 phase update while adding
the root to the live backend and its saved deployment configuration.

Sample scope was already stored in execution snapshots, but dashboard and /samples
used only Sample rows. Current-execution SQL union fixes that without duplicating
Sample records. Both SQLite fixture tests and a read-only actual PostgreSQL query
confirm3native samples, short batch and retained GATK page behavior.

One exact native log reader supplies Rules and progress. Actual test log showed
208total jobs, initially3running declarations and subsequently4/208done (1.92%).
These are observations, not fixed UI values or completion claims. No new logger
package or workflow image is required for these existing Local log records.

## Verification

BS10610 cached tests: 22 backend (native views/monitor/selection scope), 15 frontend
(native panel/shared rules/tracker), TypeScript/Vite build passed. Tests first
reproduced absent progress and wrong native dashboard batch/count. Initial new
fixture expectation confused data_id with sample_id; corrected to the established
fixture mapping. Initial UI icon text interfered with exact rule-name queries;
name and icon now separate elements. Required notInAirflow field added after
TypeScript caught the omission. No complete WGS run, new batch, Docker Hub pull,
production check or production DB operation performed.

Bounded review found stale prior-execution timing/status on resume. A failing
regression reproduced it; dashboard and progress now resolve the exact current
WgsStageExecution. No lifecycle behavior or registration contract changed.

Read-only actual PostgreSQL probe used SET TRANSACTION READ ONLY and temporary
in-process candidate imports; no persistent settings or native project changes.
Initial frozen Settings assignment failed before DB access; dataclasses.replace
used for the isolated approved-root check. SSH via18/direct10610 was intermittent;
BS96 was used only as an SSH transport to server10610, not as an execution target.

## Publication and rollback

Test branch jiucheng/test/wgs-local-main-sync-20260917; main and production excluded.
Publication outcome and exact source/service identities are recorded in HANDOFF.
Rollback restores only backend/frontend source and private composition; retain
project binding, operation ID, database, samples, pending, logs and active workloads.
No auto-registration, launch, rerun or reprepare is part of this change.
