# CCE0.8.5 / Airflow API integration — 2026-09-15

Scope: user confirms CCE development complete and requests continuation; finish
the paired API integration and prior requested Git synchronization. No production
installation/deployment/activation is authorized or performed by this action.

## Source and compatibility

- Main baseline5241068 contains all previously audited12 repair anchors.
- Merge original Airflow branch73aa0ce, implementation8fb3529+994a9c2; preserve
  both Git histories. Backend changes merge cleanly; five additive doc conflicts
  resolved by retaining both sections, not replacing the newer repair history.
- The wire contract remains cce-release.v1: inactive/idempotent registration,
  explicit receipt-bound compare-and-swap activation, retained historical release
  and frozen CCE recovery parameters. No changes to current attempts or workdirs.
- Existing resume_stage independent same-attempt path remains unchanged; legacy
  CCE recovery now retains the recorded catalog release. Local/SGE behavior is
  unchanged. No new DB table, workflow lock, stage, frontend component or migration.

Latest local artifact:
`C:/Users/11217/Downloads/cce-pipeline-0.8.5-52cb638/cce_pipeline-0.8.5-py3-none-any.whl`

Wheel SHA256: `4104572b9e3c3f73bfb3118962bcd974a5e04edd3cd9bf95651a2fa52141c097`.
Read-only ZIP hashing, no extraction/installation/runtime execution:

| Module | SHA256, equal to reviewed producer source |
| --- | --- |
| release.py | 0872c3b42ed6ab78a640995fb0023a5b914454de47957f4fec43cd0b80b74dbc |
| cli.py | 8769b7f8425ae13be1f3f038f88272d0c3f1e60ed2a21665394453de03f6af3e |

Therefore retain the original one synthetic built-wheel→FastAPI integration
record; the later single-MD5 change did not change release producer/client code.
No fresh full CCE suite, wheel build or duplicate cross-component smoke.

## Matching merged-source test

Fresh read-only BS10610 fingerprint: server10610, control root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`, current20260912-opt-4d3d24e6,
actual backend20260913-panel-1fb971b, worker20260912-gatk-81587fcb; scanfalse,
autofalse, executiontrue. Running services untouched.
Candidate source under `candidates/platform-followup-20260915/cce-api-integration-source`.
Cached backend:t235-232154f; network none, candidate read-only, disposable scratch
tmpfs. No credentials, live catalog, database or scientific files mounted.

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/candidate/backend TMPDIR=/scratch
python -m pytest -q -p no:cacheprovider --tb=short tests/test_wgs_release_management.py tests/test_wgs_resume_stage.py
```

11passed (API7/resume4),1.64s. One known Starlette/anyio deprecation warning,
no dependency changes. UI/DAG/runtime source unaffected by this integration;
retain existing matching evidence, do not rerun full suites/builds. Static diff
and conflict-marker checks are Git/editor checks, not local runtime testing.

## Remaining production boundary

`WGS_RELEASE_MANAGEMENT_ENABLED` remains false by default. Production enablement
still needs approved catalog parent-directory mounts for atomic replacement,
owner/permissions, matched reader paths and approved package/asset selection.
No live mount/env/catalog/asset/attempt/source script/pending change here.
Publishing a new candidate does not itself activate it or update running batches.
Future operator deployment uses existing release publish/register/activate flow;
no need for manual application-code edits per WGS version, but explicit activation
and frozen historical versions remain part of the approved contract.

Git publication targets main and jiucheng/release/production atomically; verify
matching remote refs and clean production clone. Rollback source with a scoped
revert, not branch reset, package removal, catalog deletion or workflow cleanup.
Other outstanding platform performance/QC/display/resource work is unaffected.
