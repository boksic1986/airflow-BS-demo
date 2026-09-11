# OPT20260912 Task3 resource monitoring

Implementation based on accepted Task2 d9543a0. Coordination-only a538883 is
also in branch history. Exact implementation source is the commit containing
this report; parent coordinator owns central TASKS/CURRENT_STATE/HANDOFF,
independent review and deployment. No Task1/Task2 code was reverted.

## Delivered and boundaries

- Complete namespace named Lease inventory remains authoritative for reserved
  Heavy work Jobs.11/25 synthetic holders survive missing waiting evidence;
  old holders count, grouped Job consumes one lease. No acquire/release/reclaim.
- Per-field availability, oldest waiting-source timestamp, mode, safe reasons,
  freshness, last-known stale values and full-availability compatibility flag.
  Business Pod rows/configuration never invent occupancy/limit/waiting.
- Canonical Heavy backend module with standalone entry point and explicit test
  launcher environment. No production hardcoded output or duplicate algorithm.
- Separate BSS hourly collector: bounded complete package pages,100-ID usage
  batches, official unit dictionary, exact Decimal strings, quota cycle/reset
  basis/current period/expiry. Opaque keys and safe numeric-only public spool.
- Fixed global HTTPS BSS host/three read-only routes, GlobalCredentials with
  explicit domain, no redirects, no proxy/netrc forwarding, no IAM discovery.
  Dedicated owner-only credential contract, lazy SDK imports on node only.
- Atomic publication after complete validation; failed/incomplete403/429/timeout
  refresh preserves last-good values and time, with stale/safe reason. Hourly
  checked_at also throttles failed attempts. GET reads spool only, no cloud call.
- Missing spool is unavailable, not proof of missing credentials. Running
  collector without dedicated credentials publishes not_configured explicitly,
  without constructing an SDK client. Real dedicated billing identity absent.
- Dashboard Heavy independent of SFS; runtime/package balances separated;
  unknown/stale shown honestly. Existing SFS read/write/total and source labels
  preserved. Cloud CPU/memory realtime explicitly unreported: no verified live
  cloud telemetry source exists; local node CPU and allowance hours are not substitutes.
- Fixed the baseline WgsProductionUi Total ambiguity by scoping to the Sample
  throughput section. Did not remove or skip the test. Retained SFS Total label.

## Owned files

Backend app: heavy_global_snapshot.py, bss_resource_snapshot.py,
platform_resources_service.py. Backend tests: test_platform_resources_service.py,
test_resource_package_projection.py.

Scripts: heavy_global_snapshot.py, start_heavy_slot_collector.sh,
collect_bss_resources.py, start_bss_resource_collector.sh,
tests/test_resource_monitoring.py, tests/bss_signed_transport_probe.py.
Config: resource_collectors.test.env.example (non-secret test paths only).

Frontend: api.ts, styles.css, WgsProductionUi.test.tsx,
features/dashboard/DashboardResourcePanels.tsx and its existing test,
features/dashboard/ResourceMonitoring.test.tsx.
Docs:02/05/06/08/11 and this report. Root's TEST_RELEASE/progress/review/state
documents are deliberately excluded from this implementation commit.

## Remote validation provenance

Read-only preflight confirmed ssh BS10610 hostname server10610, control root
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS, current release
releases/20260912-gatk-81587fcb. Actual backend /app and /config point to that
release read-only; /data/wgs-evidence is test airflow-ctapa/wgs-runtime/cce-evidence
read-only; /sg2 and /bi read-only. Scanner and dispatchfalse rechecked.
No existing service, private config, actual workload or production changed.

Synthetic source and test output root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/OPT20260912-resources`.
Source archive extracted to source; TMPDIR=/src uses that task mount, not /tmp.
Cached images backend:t235-232154f and
frontend-builder:node22-lock-35420d5e3ec0; every test uses --network none.
No Docker Hub/npm/package installation, live database or billing calls.

Red (exit1, expected):

- red-heavy.log: missing Master waiting raised and discarded known11/25;
  stale snapshot discarded last-known occupancy; initial collector absent.
- red-bss.log: dedicated BSS module absent for pagination/Decimal/cache tests.
- red-ui.log: Heavy hidden without SFS and baseline global Total ambiguous;
 2 failed,16 passed.
- red-edges.log: duplicate Lease inventory accepted past quota validation and
  waiting timestamp incorrectly refreshed by unrelated Lease query;2 failed,8 passed.
- red-api-missing.log: unavailable API incorrectly implied missing billing
  credentials;1 failed,2 passed. Repaired to cache_not_reported.
- red-spool-missing.log: missing spool incorrectly implied absent credential;
 1 failed. Now spool_unavailable; collector alone reports not_configured.
- red-heavy-validation.log: malformed reasons/raw timestamp caused exception;
1 failed. Public projection now rejects malformed timestamps/reasons safely.
- red-obs-category.log: dictionary GB flow dimension did not classify a genuine
  OBS storage allowance;1 failed. Classification now also requires internal
  usage semantics; quantity alone does not imply OBS requests. Unknown stays other.

Backend command (cwd source/backend, PYTHONPATH=/src/backend, TMPDIR=/src):

```text
pytest -q ../scripts/tests/test_resource_monitoring.py ../scripts/tests/test_heavy_global_snapshot.py tests/test_resource_package_projection.py tests/test_platform_resources_service.py ../scripts/tests/test_sfs_cloud_eye_collector.py ../scripts/tests/test_sfs_cloud_eye_launcher.py
```

Earlier complete run:36 passed in92.34s, including10080-point SFS retention
(green-backend-final.log). Latest focused run after added malformed-payload
regression:36 passed,1 deselected in2.17s (green-backend-latest.log); only already
passed expensive seven-day retention excluded on that iteration. Final complete
green-backend-complete.log:37 passed in94.20s, exit0, no deselections/skips.
Then the added OBS usage-semantic regression and all new collector/projection
tests passed18/18 in1.72s (green-validation-final.log). No transport function
change; only OBS display classification changed after the37-test full run.

Frontend command inside cached /app with current source copied into image:
`vitest run && npm run build`. Final green-ui-final.log:25 files,92 tests pass,
no skips/failures; TypeScript/Vite build exit0. Built assets index-CHnQnHfa.js
and index-9kcWGY_H.css. This is a build artifact, not proof of deployment.
Earlier missing within import/heading Updated ambiguity failed during editing;
fixed imports/heading scope, then full suite passed (not hidden).

## Node SDK compatibility and actual telemetry

Coordinator ran the original fake-signing probe on t640 Python3.9,
huaweicloudsdkcore3.1.210: exit0,4 synthetic signed requests,0 network connections.
It validates actual GlobalCredentials domain header/signature, fixed GET route,
redirect rejection and safe302/403/429 mapping. Source collector SHA256
3dba4573e1589bbca5505184c810de047a76c3d3743e050aff793656e8184fb1.
Original contract b047d2e36c47efac06dd238c26b33381372faf23cf6e27db1ecf625afd614b4d;
later pure-reader change distinguishes missing spool from missing credential.
Original probe a740637eb045157b28f72ce08e228a011ada111b5bfcfcceb37be8388c6e0127.
Final probe now additionally covers both POST routes and exact signed/transmitted
serialized body (6 calls); coordinator must run it against final committed files.
Transport itself has not changed since the successful node probe.

Actual node writable probe root was
/sg2/biodevrwsg2/33.chenjiucheng/WGS_test/airflow-ctapa/wgs-runtime/cce-evidence/OPT20260912-bss-node-probe.
First alias test-d failed; direct /sg2/33... mkdir denied with no directory
created. Coordinator then used the known test runtime child, no chmod widening.

Prior coordinator read-only live evidence:25 Leases/11 reserved holders,
one active Master enforce25, waiting snapshot missing. Implementation agent
did not query live cloud, launch collectors or verify fresh deployed telemetry.
These are observation counts, **not a new enforcement/saturation test**.
No Master image/executor admission changes or real job launches performed.

Dedicated billing credential/permission and real package balances remain
**not configured / not verified**. Backend lacks SDK; node core exists but BSS
bindings absent, which this standalone core-signing design does not require.
No cloud realtime CPU/memory verified. UI/browser/no-flash/runtime acceptance
after deployment remains coordinator's test-only responsibility.

## Deployment manifest, next step and rollback

Use document11's exact six-file standalone manifest. Install canonical Heavy
backend module as heavy_snapshot_core.py beside scripts/heavy_global_snapshot.py;
install canonical bss_resource_snapshot.py beside collect_bss_resources.py.
Test private root /home/ctapa/.config/airflow-wgs-test remains owner0700,
scripts0700. Preserve existing runtime.env, SFS collector/config, production
airflow-wgs launcher/process and existing workload state.

Coordinator: review commit, final no-network node POST signing probe, read-only
Heavy --once with existing CCE_OPERATOR_CONFIG and explicit test evidence root,
unconfigured BSS --once, then approved independent launcher activation/backend
and UI test deployment. Validate returned field states, not fabricated totals.
Rollback only owned scripts/process/application release; preserve quota holders,
database/results/evidence/source data. No production change is authorized here.
