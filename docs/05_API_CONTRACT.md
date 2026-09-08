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

## GATK Cloud manual submission

- `POST /api/pipelines/gatk/submission-preview` accepts only
  `source_project_dir`. It returns an expiring draft/hash, batch, fixed profile,
  sampleinfo basename, locked SCMC sample IDs, FASTQ count/bytes and safe check
  results.
- `POST /api/runs` confirms GATK with `pipeline=gatk`,
  `execution_mode=cce`, `submission_draft_id` and
  `submission_preview_hash`. Changed inputs return
  `409 GATK_INPUT_CHANGED`; an expired/consumed draft or duplicate batch
  returns `409 GATK_DRAFT_CONFLICT`.
- GATK reuses `/workspace`, `/rules`, `/pods`, `/transfers`, `/logs` and
  `/artifacts`. It deliberately does not expose QC, intake or clone-reanalysis
  capability in v1.

Internal `/api/internal/gatk/runs/{analysis_id}/stages/{stage}` and
`/stage-status` routes require the service token and the fixed
`gatk-runtime-200` adapter identity.

## Privacy

Responses never include patient names, hospitals, credentials, raw absolute storage paths, or arbitrary filesystem content. Artifacts are accessed by controlled keys.
