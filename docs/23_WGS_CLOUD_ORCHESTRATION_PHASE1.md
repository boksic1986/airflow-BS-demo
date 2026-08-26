# WGS cloud orchestration Phase 1

> **历史 Phase 1 文档。** 本文描述 2026-08-12 demo mock/orchestration 基线，
> 不是 WGS 4.1.1 生产合同。当前设计见
> [`25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md`](25_WGS_4_1_1_AIRFLOW_INTEGRATION_PLAN.md)。

## Scope and gates

Phase 1 implements data orchestration, immutable FASTQ snapshots, structured
review, transfer progress, Rule timing/ETA, UI, and a paused Airflow graph. It
does not run the changing WGS Rules, CCE, kubectl, or private OBS transfer.
`WGS_EXECUTION_ENABLED=false` makes public submit return HTTP 409 and
`WGS_PHASE1_MOCK_ENABLED=false` disables synthetic stage endpoints. Enabling
the real flag alone still cannot run WGS because no real adapter exists here.

## Input and snapshot

WGS creation accepts `pipeline=wgs`, `execution_mode=cce`, `project_name`,
`batch_no`, and `fq_path`. The controlled directory contains paired FASTQ
symbolic links; `READY`, sampleinfo, config and MD5 are no longer inputs.
Resolved targets must stay under `WGS_FASTQ_ROOTS`. Airflow's run workdir gets
`input-manifest.json`, `sampleinfo.tsv`, `config.yaml`, and later
`FASTQ.MD5SUMS`. The snapshot records device, inode, size and nanosecond mtime.

Broken/out-of-policy links, missing pairs or later source identity changes
create `run_validation_issue` rows and `needs_review`. Operators correct data
upstream and revalidate; the UI cannot edit sampleinfo. An already valid
snapshot cannot be silently replaced after mutation.

## DAG and concurrency

`bio_wgs_cce` is paused and has 27 unique Airflow nodes; two logical OBS lease
steps live in separate input/result TaskGroups. It covers validation, snapshot,
metadata/config, two-process-limited MD5, snapshot recheck, serialized upload,
Master lease/preflight, workflow/reconciliation, linkage publish, serialized
download, result MD5, atomic promotion, finalization and all-done lease release.
All six waits use `reschedule`. Pools are `wgs_input_hash=2`,
`wgs_obs_transfer=1`, and `wgs_cce_runs=4`.

## Transfer and observer

The future restricted node005 wrapper writes one atomically replaced
`progress.json` per registered transfer: bytes/files, percent, smoothed speed,
ETA, current file, checkpoint reference, heartbeat, verification and sanitized
error. Observer reads the spool, ignores stale heartbeats and idempotently
writes biodemo. No OBS credential is accepted or stored. The parser supports
obsutil carriage-return and newline refresh. Real node005 commands remain
Phase 2.

## ETA and API

Rule rows expose elapsed time, historical median, remaining estimate, history
count and model. Only the latest 20 successful CCE runs with the same pipeline
snapshot are comparable; fewer than three returns `insufficient_history` and
no hard ETA. Progress uses the approved stage bands and separately reports the
current Rule.

Alembic `20260812_0008` adds `wgs_input_snapshot`,
`run_validation_issue`, singleton `obs_transfer_lease`, and complete transfer
progress fields. New public endpoints are `GET /validation-issues` and
operator-only `POST /actions/revalidate`; `/transfers`, `/rules`, and
`/progress` are enriched. Internal mock endpoints require service token plus
the mock gate.

## Security, deployment, Phase 2

The external network remains `nipt_analysis_test_net`, `192.168.199.0/24`,
gateway `192.168.199.1`; only `172.17.106.10:12959` is published. Containers
have no Docker socket, kubeconfig or OBS config. The upstream
`/mnt/biodevrwbi/33.chenjiucheng/project/wgs` remains unchanged.

Phase 2 must pin an accepted WGS snapshot, implement restricted node005
upload/download and BS10610 kubectl launch, wire final logger/result contracts,
and pass minimal real, resume, OOM, Rule failure, Master interruption, corrupt
MD5 and four-batch acceptance before changing either runtime gate.
