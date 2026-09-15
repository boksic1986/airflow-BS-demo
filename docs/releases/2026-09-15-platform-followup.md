# Platform follow-up — source delivery, 2026-09-15

Base: `ead029f8f9955d487a62fc9b966882271320e0d4`, branch
`jiucheng/fix/wgs-eta-20260915`. No main merge, push or production deployment.

## Delivered

- TRACKER-01: overall success uses common Completed, not pipeline-specific text.
- QC-01 display: compact five key metrics, one sample detail with friendly labels,
  Chinese known reasons and original diagnostics; source QC/judgments unchanged.
- SUBMIT-01 UI: reuse single-flight refresh, prepare2s/normal10s/hidden60s,
  stale route/attempt/phase/action fencing and preserved unconfirmed choices.
- LIST-01: database-filtered summary pagination, no per-run hydration.100 cards
  need one list request instead of105;101 cards require two requests.
- Explicit online-only deletion boundary and tracking of the original plan.

No prepare_wgs_batch.py, pending, local/SGE, runtime/DAG, release policy threshold,
database schema, CCE installation, active executor or data changes in this slice.

## Environment and bounded verification

Fresh BS10610 fingerprint: server10610; control root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`; current release
`20260912-opt-4d3d24e6`. Actual backend mount is20260913-panel-1fb971b; worker
file mounts include20260912-gatk-81587fcb. Scanner/auto false, execution true.
Those running services and mounts were inspected, not changed or used for tests.

Candidate: `<control-root>/candidates/platform-followup-20260915/source`.
Source came from git archive plus exact edited-file overlays; no private data.
Cached images backend:t235-232154f and frontend-builder:node22-lock-35420d5e3ec0.
All tests used ephemeral `docker run --rm --pull never --network none` with only
candidate source mounted read-only; frontend copies source into its disposable
/app containing cached node_modules. No downloads, production mounts or secrets.

Commands inside isolated containers:

```text
python -m pytest -q -p no:cacheprovider --tb=short tests/test_wgs_incomplete_submissions.py
npm test -- --run src/components/RunCompletion.test.tsx src/SubmissionRefresh.test.tsx src/lib/useSilentRefresh.test.tsx
npm test -- --run src/IncompleteSubmissionApi.test.ts src/IncompleteSubmission.test.tsx src/features/run-detail/QcMetric.test.tsx src/features/run-detail/WgsQcTab.test.tsx
npm run build
```

Results: backend2; UI completion2, refresh1, shared-hook3, listAPI1, saved-card6,
QcMetric3, WgsQcTab2 =18 unique frontend tests passed. Build TypeScript/Vite passed;
final JS `index-3IjEWu6r.js`, CSS `index-CdK5PwQa.css` (unchanged).
RED demonstrated old completion label, overlapping refresh, missing summary
function/new endpoint consumer and nested QC layout. A review found reference
choice overwritten by polling; expanded the existing refresh test, observed
expected `no`/actual `ref`, fixed one-time restoration, then only that1test/build
reran and passed. No full suite or unchanged resume/ETA regression rerun.
Bounded independent LIST-01 code review found no concrete defects; parent
reviewed the QC extraction and matched it to the actual Run detail entry point.

Setup failures: initial SQLite fixture omitted mandatory workdir; fixed synthetic
workdir before valid RED. Completion selector initially matched both heading and
progress label; narrowed to heading. One SSH banner failure retried successfully.
No runtime operation was retried or executed for these failures.

## Unresolved / not claimed

- SUBMIT-01 <=60s backend acceptance: prior0912D receipt reported377.539s total,
  artifact_write373.282s; task534.4s. These are historical observations, not a new
  production profile. UI polling cannot remove that artifact-generation cost.
- 34bfcbf has no audited QC policy mapping; cc9bde3 rule-phase equivalence does
  not prove QC threshold equivalence. Keep unknown with a readable reason.
- Remaining DISPLAY/RESOURCE/EXEC plan items and separate CCE release-API
  integration are not included. CCE52cb638 wheel is not installed by this task.
- API-route deployment/auth integration and production visual/latency validation
  were not exercised: this is candidate source verification, not live acceptance.

Next steps must retain user scope: no native prepare interface changes, pending
mutation, automatic new analysis or offline deletion. Production rollout/recovery
needs separate authorization. Future release must provide the summary backend
before/together with its consumer. Rollback these source changes only; no DB
migration or data restoration is required.
