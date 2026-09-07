# API contract

## Generic platform endpoints

- `GET /api/platform/capabilities` returns `deployed_pipelines` and registry definitions with capabilities and execution targets.
- `GET /api/runs` lists runs, filtered by registered pipeline ID.
- `POST /api/runs` creates through the selected adapter when `submit` is available.
- `GET /api/runs/{analysis_id}` returns the shared run projection plus adapter-owned fields.
- `GET /api/runs/{analysis_id}/samples` returns adapter-projected sample state.
- `GET /api/runs/{analysis_id}/qc` returns safe adapter-projected QC data.
- `GET /api/input/scan`, `/api/input/roots`, and `/api/intake/*` require the corresponding registry capability.
- `GET /api/workflows` returns deployed registry entries rather than a hard-coded catalog.
- `GET /api/pipeline-config/template` and `POST /api/pipeline-config/validate` dispatch to the selected adapter.
- `POST /api/runs/{analysis_id}/actions/reanalyze` dispatches only after the adapter capability and its execution/runtime gates pass; a rejected call cannot increment the attempt.

## Stable pipeline errors

```json
{"detail":{"code":"PIPELINE_NOT_REGISTERED","message":"..."}}
```

The other stable codes are `PIPELINE_NOT_AVAILABLE` and `PIPELINE_CAPABILITY_UNAVAILABLE`; clients branch on `code`, not message text.

## WGS extensions

Existing `/api/wgs/*` routes remain supported for WGS submission, intake, evidence, transfers, execution choice, maintenance, and lifecycle functions. They are deliberately namespaced and do not define generic behavior for future adapters.

### T227 transfer and Step7 recovery projections

- `GET /api/runs/{analysis_id}/workspace` returns one `snapshot_at` and the complete `active_transfer`; Current Progress and Transfers must render that same object during Step1 or Step5.
- Transfer percentages are derived from `bytes_transferred / bytes_total`, serialized to one decimal place, and fixed at `100.0` for successful terminal transfers. Per-file rows expose privacy-safe display name, bytes, speed, checksum state, `started_at`, and `ended_at`.
- `GET /api/runs/{analysis_id}/samples` adds `manifest_summary`. It contains only aggregate batch/sample/family/order counts, allowlisted project/method/date/type summaries, delivery status, and a controlled relative project path. It never returns order identifiers or clinical identity fields.
- `GET /api/runs` returns `workflow_status` and `workflow_label` as a stable fallback when detailed stage rail evidence is unavailable.
- `GET /api/runs/{analysis_id}/rules?sort=active_first` orders running/started records before planned and terminal records while retaining server pagination and explicit start/end/elapsed fields.
- `POST /api/runs/{analysis_id}/actions/cleanup-step7` accepts the existing first-run body. A failed-action retry additionally requires `retry_failed=true` and the current `expected_action_id`; stale or non-failed generations return conflict.

## Privacy

Responses never include patient names, hospitals, credentials, raw absolute storage paths, or arbitrary filesystem content. Artifacts are accessed by controlled keys.
