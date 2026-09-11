# Production release branch

Branch: `jiucheng/release/production`.

This branch records the WGS production control plane separately from the
WGS/GATK test integration on `main`. It is not an automatic deployment branch.
Creating, committing, or pushing it must never trigger analysis or recreate services.

## Reconstructed baseline: 2026-09-11

- Git ancestry starts at the available production-work branch `bd7849e`.
- Observed server96 release: `20260910-t260-recovery-runtime-r1`.
- Its `SOURCE_COMMIT` is `5bb9e3f075f80a2a0104bf1d48fdc2b163249269`.
  That object is unavailable locally and origin rejected a fetch by that SHA.
  It is an observed marker, NOT a claim that this tree descends from that commit.
- Backend, DAG, runtime helper and configuration files were captured by an
  explicit source allowlist from production. Hashes are in the adjacent manifest.
- The active node200 restricted gate supersedes the stale release-directory
  gate. Its verified bytes are stored at `scripts/wgs_runtime_gate.py`.
- Heavy collector scripts match the active node200 installation.
- Production nginx serves compiled assets, not the stale release-directory
  frontend source. The branch uses the local source that produced the latest
  deployed assets. Rebuilding those assets is a mandatory acceptance check.
- Generic GATK code already in the production tree is retained. WGS-only
  deployment is enforced by `docker-compose.wgs.yaml` / `DEPLOYED_PIPELINES=wgs`;
  do not use the generic Compose file as a production entry point.

## Included production repairs

- Current-attempt selected sample scope and pending status separation.
- Backend observer synchronization and shared silent frontend refresh.
- Heavy slot telemetry collector and truthful unavailable-state handling.
- Config-review cancellation with attempt fencing, retained audit and safe retry.
- Saved submission discovery and URL restoration; no duplicate submission.
- Cancelled-run history filter and cancellation-aware Attention projection.
- Attention layout and SFS bandwidth presentation.
- Restricted-gate handoff identity preservation and bounded request visibility retry.

No clinical records, real receipts, DB dumps, keys, environment files, runtime
evidence, build directories or local operational scratch files are included.
Tests newly collected for this branch use synthetic data.

## External runtime ownership and unresolved items

The WGS workflow, prepare/pending implementation, cce-pipeline package, Master
image, profiles and credentials remain owned outside this repository. Their
observed hashes/versions are dependencies, not copied workflow implementations.
In particular, the installed cce-pipeline 0.8.4 delivery helper has a scoped
permission-normalization hotpatch; version `0.8.4` alone is insufficient provenance.

Known issues are not disguised as baseline acceptance: pending identity
reconciliation and missing group-member start events require owner work;
post-config cancellation is not implemented. No historical progress is fabricated.
The profile catalog hash and current external profile bytes are recorded
separately; reconcile their semantic/version contract before a new deployment.

## Future release procedure

1. Create a small work branch from this production branch. Selectively port
   reviewed fixes; never blindly merge the complete test `main`.
2. Update tests, API/runtime docs and an explicit source/dependency manifest.
3. Test on BS10610 using cached images with no Docker Hub access and no real
   automatic analysis. Local Windows is editing/Git only.
4. Review the diff and secrets/privacy scan; commit only allowlisted source.
5. Obtain explicit deployment approval. Read-only fingerprint server96 again,
   verify source hashes, current attempts, mounts, gates and rollback assets.
6. Build from that commit; promote only affected services/assets. No Git pull
   on production. Do not restart worker/Master/analysis Pods as a side effect.
7. After actual successful deployment, tag that commit `production-YYYYMMDD-rN`
   and record runtime evidence. A reconstruction snapshot is not a new release
   and receives no misleading deployed-release tag.

Rollback restores code and static entry points only. Never roll back by deleting
pending ledgers, samples, audit rows, shared data or workflow results.
