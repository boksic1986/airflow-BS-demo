# Tracker / Run detail shared transfer progress (not deployed)

User requests reuse rather than duplicated implementation. RunProgressBar was
already shared in frontend; the mismatch originated in backend projections.
Tracker used integer RunStageState progress while Run detail used the existing
serialize_transfer_job byte-based one-decimal projection.

Reuse wgs_transfer_projection for active snapshot selection and stage-field
mapping in both wgs_timing_service and wgs_workspace_service. Existing
transfer_progress_percent remains the only percentage formula. Select current
analysis/attempt and upload/download direction; retain existing active statuses.
Bytes, percent, speed, ETA and heartbeat share a snapshot. No detailed evidence
or no matching active transfer yields unavailable values, not an old percentage.
No frontend component, refresh interval, API endpoint, table, producer or
runtime change; two independently timed HTTP requests can still observe
different natural upload instants, not conflicting calculation rules.

## Verification

Test only BS10610/server10610, actual backend mount panel1fb971b and historical
current opt4d3d24e6 verified. Isolated candidate shared-transfer-20260915 under
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS/candidates.
Cached backend:t235-232154f, --network none --pull never, candidate read-only,
PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=/work, explicit --workdir /work.

Initial run accidentally imported the image's older /app due to default working
directory; discarded as acceptance. Corrected working directory and verified
baseline from committed source: four parity tests fail. Final candidate:
`python -m pytest -q -p no:cacheprovider tests/test_wgs_shared_transfer_progress.py tests/test_wgs_transfer_projection.py tests/test_wgs_timing_service.py tests/test_monitor_estimates.py`
28 passed in1.60s. Six parity cases cover upload/download, trusted/untrusted/missing
detail and exclude newer opposite-direction/old-attempt transfers. Existing
serializer, timing and estimate regression tests retained. Baseline archive
uploads hit two SSH pre-session aborts; retried without runtime actions.

No frontend test/build: frontend unchanged and existing number formatter accepts
decimal percentages. No production tests or publication per user deferral.
No analysis, pending, queue, database or live service changes. Rollback this
code commit only; leave stored stage/transfer evidence and ongoing work intact.
