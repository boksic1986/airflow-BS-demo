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
