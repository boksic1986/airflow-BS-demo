---
name: wgs-gatk-runtime-dev
description: Develop and validate current WGS/GATK runtime integration, including Step1-Step7, CCE/local targets, receipts, rule evidence and restricted host gates.
---

## Required reading

- `AGENTS.md`
- `docs/34_TEST_PRODUCTION_RELEASE_BOUNDARY.md`
- `docs/08_WORKFLOW_RUNTIME_INTEGRATION.md`
- `docs/07_AIRFLOW_DAG_SPEC.md`
- `docs/13_SECURITY_AND_OPERATIONS.md`

## Environment gate

1. Declare `test` or `production` before running remote commands.
2. Verify SSH alias, hostname, control root, current release and actual service
   mounts against the boundary document.
3. Verify runtime/result/evidence permissions through the effective runtime
   identity. Do not broaden permissions to make a test pass.
4. Stop on environment drift. Test acceptance never authorizes production.

## Runtime rules

- Airflow owns project-level orchestration; the workflow engine owns rule/file
  dependencies.
- Use generation-fenced requests, receipts, logger events and terminal markers.
- Keep node200 database-independent and never expose credentials or clinical
  payloads in evidence.
- Preserve successful work on retry and never default to `--forceall`.
- Keep test and production runtime, evidence, results and identities separate.

## Validation

- Prefer mock/dry-run and bounded canaries.
- Check exact analysis ID, attempt, generation, runtime identity, rule evidence,
  terminal marker and result root.
- Record services changed and preserved, active-run continuity and rollback.
