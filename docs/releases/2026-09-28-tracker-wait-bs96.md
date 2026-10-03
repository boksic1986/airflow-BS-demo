# BS96 WGS Tracker and GATK waiting display release — 2026-09-28

This record is based on the coordinator's completed production preflight,
limited switch and readback. Source is `a8ae5fe040e4e6a1a7b3522cc0fcc9de7475379a`.
This documentation pass did not contact BS96, run tests or change a service.

## Target and source binding

- `ssh BS96` resolved to `server96`; account `chenjc` was `6708:520`.
- Effective application base remained `84510df` with its prior overlays.
  The historical `current` symlink was not moved.
- New release: `/data/airflow-WGS/releases/20260928-tracker-wait-a8ae5fe`.
  Private control: `/data/airflow-WGS/tracker-wait-a8ae5fe-control`.
  `rollback.json` there retains complete prior backend and observer Compose
  configurations, including private environment values. Its contents are not
  reproduced in Git.
- Private control `compose.json` added only read-only file overlays: backend receives
  `gatk_workspace_service.py`, `pipeline_registry_service.py`,
  `diagnostics_service.py`, `wgs_observer.py`; observer receives only
  `diagnostics_service.py` and `wgs_observer.py`. The already-active Step3
  `main.py` lock fix was not copied again. Effective environment, mount and
  Compose structure comparisons passed; `docker compose config -q` passed.

| Overlay | SHA-256 |
| --- | --- |
| `gatk_workspace_service.py` | `85016ffa445714f551478be2a1ba59bbb008a165747b60ac0b093754739f6953` |
| `pipeline_registry_service.py` | `3a58c412e4cade8e0583092b33c6f7c39c55a1de1f01291cbff22e7a23299978` |
| `diagnostics_service.py` | `d6f177a0a5b18386a0ceefcf6b35816238faa7a65f8b7ea90cfb733ead0dde20` |
| `wgs_observer.py` | `74cda4e3d1b33ac0c4c048abcb876ba8285c798c980fd1f94d0464b374fa3cb7` |

## Service switch and readback

`up --no-deps --pull never backend wgs-run-observer` completed. Backend
container changed `0d69172001b2 -> 6718484b355c`; observer changed
`442874a2b576 -> 4d27b967e20d`. Both use the same image ID prefix
`0e2d6f0c`, have zero restarts, and all other container IDs were retained.
Nginx configuration check and graceful reload passed. LAN port 12959
`/api/health` returned 200. Scanner remained enabled and auto-dispatch
remained disabled; pool, tasks, uploads and cloud resources were not changed.

The coordinator used the normal stage-status API to import only C's existing
attempt-1 PREPARE generation-2 success receipt: `success`, `ready=true`,
`artifact_pending=false`. Tracker showed C `running` / `Uploading FASTQ` /
`waiting` / percent null, with 11 samples; A showed the same waiting display.
WES `GATK_20260928_105710_C05CE4` showed `running` / `Uploading FASTQ` /
`waiting` / percent null, with 43 samples. These are display and receipt
observations, not a new batch or transfer acceptance. D displayed 100% while
still `running`; no terminal completion is claimed.

## Limit, probe issue and rollback

C's historical `pipeline_finished_at=13:10:00.716975Z` remains stale. C was
already running, so the failed-to-running cleanup condition did not fire.
No synthetic status or direct production DB update was made; this needs a
separate scoped decision. A read-only review probe first used unsupported
`limit=100`, received HTTP 422 and then a local `KeyError`; using the documented
limit 50 succeeded. This was not a production service failure.

No redundant runtime suite was run. Prior BS10610 synthetic acceptance is
retained: two WGS Tracker projection cases and four GATK wait cases passed.
For a reviewed rollback, use the private control's `rollback.json` with Compose
project `airflow-wgs` to recreate only backend and wgs-run-observer, then
gracefully reload nginx. Preserve active batches and all other services;
neither the release nor this note authorizes data cleanup.
