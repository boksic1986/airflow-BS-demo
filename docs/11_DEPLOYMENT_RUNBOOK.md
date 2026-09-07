# Deployment runbook

## Identity and location

- Project: `ngs-huaweicloud`
- Candidate root: `/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud`
- Production account and secrets are external to Git.

## Offline image policy

Production hosts must not contact Docker Hub. Use an approved cached base image or the internal image registry. The backend uses `python:3.11.9-slim-bookworm`; on BS10610 this short name is tagged locally from the already cached equivalent image before building with `--pull=false`. Never run `docker pull` as part of acceptance.

## Network policy

Compose joins an existing external network named by `NGS_PLATFORM_NETWORK`. This repository does not create the network, assign its subnet, or open additional ports during validation. Use `--network none` for tests that do not need services.

## Candidate validation

1. Synchronize source to the candidate root without secrets, `.git`, or local dependency caches.
2. Run backend tests in a clean image derived from the approved cached Python base.
3. Run DAG import/contract checks.
4. Run frontend tests and production build using the approved cached Node image.
5. Render Compose configuration without starting services.
6. Run an isolated migration upgrade against a disposable database.
7. Record exact commands and results in `HANDOFF.md`.

Production deployment and restart require separate approval. Candidate validation must not connect to the running CCE task path.

## T227 production runtime requirement

The node200 restricted runtime must define:

```text
WGS_RUNTIME_RUN_ROOT=/sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime/runs
```

Deploy the T227 runtime gate and environment without stopping an active
Step1-Step6 worker. Apply migration `20260908_0018` before exposing the Step7
retry UI, then restart only backend/observer/frontend components required by
the release. Do not restart Airflow scheduler/worker or release an active OBS
lease. Restore failed Step7 generations only after exact target, CCE workload,
and lease identity checks; an absent target may be recorded as
`verified_absent`, while partial or ambiguous remnants remain failed.
