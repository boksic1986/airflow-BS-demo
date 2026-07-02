---
name: snakemake-qsub-dev
description: Develop Snakemake and qsub integration for airflow-demo. Use for Snakefiles, qsub profiles, submit wrappers, event logging, logs, and resume/rerun behavior.
---

## Required reading

- `AGENTS.md`
- `docs/08_SNAKEMAKE_QSUB_INTEGRATION.md`
- `SERVER_INFO.md`

## Workflow

1. Start with Snakemake dry-run.
2. Use mock qsub before real qsub.
3. Ensure every rule has input/output/log.
4. Redirect stdout/stderr explicitly.
5. Send events to backend; fallback to JSONL if backend unavailable.
6. Do not default to `--forceall`.

## Required event fields

- analysis_id
- rule
- sample_id or wildcards
- snakemake_jobid
- qsub_jobid if available
- status
- stdout_path
- stderr_path
- timestamp
