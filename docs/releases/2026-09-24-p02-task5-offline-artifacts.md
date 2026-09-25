# P0-2 Task5 — offline source/artifact acceptance

> 2026-09-25 coordination note: this is an immutable historical acceptance record.
> These artifacts predate Task6 and are not final P0 candidates. Successor wheel
> and Master work is assigned by repository ownership in the
> [current ledger](../superpowers/plans/2026-09-22-p0-joint-recovery-progress.md),
> not yet dispatched by this documentation turn. No build/install permission is
> granted by the commands or prior environment observations below.

2026-09-24. **Accepted for isolated development only, not production.**
Task4 manual acceptance remains intact. Task6 automatic dispatch and operational
gates are not closed by this record. No live Kubernetes TTL controller was tested.

## Exact source and artifact pins

| Component | Source commit | Candidate |
| --- | --- | --- |
| Platform consumer/reader | `074dc55399d43209e5e749e55aaff489f0ae8d75` | CR01 isolated branch |
| Native runtime/Master | `7232f57a5dd5bf0bbfe9c5e4c8a3637122db5029` | `0.8.5+p02.dev1` |
| Worker executor/logger package | `fdf1520839ef870ed55c4ad8af01badac02527fd` | `0.6.4+bs8.dev1` |

Existing branches respectively: `jiucheng/runtime/CR01-cce-recovery-20260922`,
`jiucheng/runtime/p02-master-handoff-20260923`,
`jiucheng/runtime/p02-worker-terminal-20260923`. Accepted bs7 bytes are untouched.
This record's later documentation commit does not change consumer runtime bytes.

Wheel SHA256:

- `cce_pipeline-0.8.5+p02.dev1-py3-none-any.whl`:
  `e307da829c241128b8badea12d5839a5948fa5ce3907b8044ba03fb24b7409f5`
- `snakemake_executor_plugin_kubernetes-0.6.4+bs8.dev1-py3-none-any.whl`:
  `df2698769fc772e347299643c9f35fe269efeb4e9204ad89693044751521cfae`

Local test images (these are **image config IDs**, not published registry manifest
digests and not deployable SWR `@sha256` release pins):

- `p02-master-wgs:7232f57-fdf1520`:
  `sha256:d7158a3c4e80ac1dec2a65278ea57d47df9aa3ae15827cd96cd41edb83721108`
- `p02-master-gatk:7232f57-fdf1520`:
  `sha256:a77136990ea24e201619ef525c9de2b48b6876958ba5cc01ce84220e678eee38`

Both retain the base's `Snakemake 9.24.0+biosan1`; no core/Worker biological
image upgrade. Base images were already cached:

- WGS `swr.cn-east-3.myhuaweicloud.com/biosanwgs/wgs-cce-master@sha256:f3c197d7ba30bec6c8318c80a949cb278d146ce6be783660e2b71e0b714df458`,
  local ID `sha256:a0112f0b8ef003dd488c6c6ee2f13ca760c116d703e9ff7a83083e2857ce143e`.
- GATK `swr.cn-east-3.myhuaweicloud.com/biosanwgs/wgs-cce-master@sha256:ee93eaf24505af753e853aa6c0786a67c3a6896d65539de39cfb3a74075bad5a`,
  local ID `sha256:490153a56b64e811bc72b099b6375ac0beb1132516785029a6b88bb175e6ceae`.

Both images' standalone assets were loaded and compared to source bytes:
`cce_batch_runtime.py` SHA256 `08c8bd12259b709ef1275c2023fb72a34d35a581c02fd4b2f9c1f28302262a3d`;
`cce_writer_guard.py` SHA256 `f86945588e3649171325f164d2be65f50915763631e3ed3584f04f10bbdde400`.
No operator `cce_pipeline` package remains in the images.

## Scope / review decisions

Only new Job generators set `spec.ttlSecondsAfterFinished=100`: actual plugin
Worker, native Master template, existing platform rule-reader and native evidence
reader. No Pod TTL. WGS/GATK initial and recovery views retain generated settings
without rewriting original bundles. Master remains backoff0/restartNever with
259200s deadline. Platform reader retains300s/RO workspace/no OBS mount; native
reader retains600s and existing cleanup. TTL is fallback, not evidence acknowledgment.

Ruling: native `_reader_job` belongs to the existing reader family, so its60s TTL
also becomes100s. Asset-release Jobs/readers and Step7 maintenance are untouched.
Maintenance explicitly retains604800s for cleanup/repair and86400s for reset;
changing the shared Master template does not override those explicit settings.
Cost of this ruling: terminal evidence reader retention increases40s only.

Necessary packaging correction: copy the already-developed writer guard beside
the standalone Master runtime. A real subprocess loading only Dockerfile-copied
assets reproduced the missing-file error before this one-line COPY fix. No new
runtime behavior, dependency or framework. Native version is a distinct test
artifact label, not a production version/install change.

Scoped diff review covered these production lines, image COPY dependencies,
normal/recovery generator consumers and untouched maintenance overrides. No
additional Important finding. This is an author scope review, not a repeated
Task4 independent review or a whole-P0 final review; Task6 remains open.

## Validation / environment

Only `ssh BS10610`, hostname `server10610`, task owner6708/gid520. Control root
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`; current resolves to
`releases/20260912-opt-4d3d24e6`. Backend36ff21f87356 actual `/app` is
`releases/20260923-step7-ae416fa/backend/backend` RO and `/config` is
`releases/20260912-opt-4d3d24e6/config` RO. Intake scanner/auto-dispatch remainfalse.
No service replacement/restart, production/BS96/database access or active-run changes.

Evidence root:
`/mnt/biodevrwsg2/33.chenjiucheng/WGS_test/cce-evidence/p02-task5-20260924`.
Wheels, build logs, image smoke logs and full `provenance.json` are beneath
`artifacts-7232f57-fdf1520/`; immutable wheel hashes were checked before acceptance.
Build uses cached poetry-core1.9.1 (prior bs7 deps RO), setuptools80.10.2 and
wheel0.47.0 from existing test deps. No dependency download/shared installation.
Containers: networknone, pullnever, source/deps RO and task-specific scratch RW.
Docker builds: pullfalse, RUN networknone, verified cached base repository digest.

| Bounded check | Result | Evidence |
| --- | --- | --- |
| Actual Worker/Master/readers and derived views | 6 RED -> 6 GREEN | `generators-red.log`, `generators-green.log` |
| Missing Job/terminal; current producer evidence; WGS/GATK reclaimed success/failure; lost response/original deadline | 15 passed,19.76s | `ttl-affected-matrix.log` |
| Dockerfile standalone helper load | 1 RED -> 1 GREEN | `packaging-red.log`, `packaging-green.log` |
| Both built image helper/package/version/hash checks | 2 image smokes passed | `artifacts-7232f57-fdf1520/*-image-smoke.log` |
| Actual wheel import paths, generators6, reclaimed WGS/GATK4, lost response2, original deadline1 | 13 passed,14.57s | `artifact-acceptance.log` |

Actual-wheel checks remove source package paths from PYTHONPATH, verify imports
come from `wheel-site`, and execute real producer records through native/platform
consumers with synthetic external transport. No biological workflow or live cluster.
Existing Task4 full/manual matrices and unrelated budget/callback suites were not
repeated. Local Windows was edit/Git/docs only. Live Complete/Failed TTL timing,
cluster-wide capacity, AOM/alerts and production activation need separate authorization.

Recorded build failures: first Dockerfile FROM received a local config ID, which
BuildKit interpreted as a repository name and attempted metadata DNS resolution;
it failed before any pull/build. Corrected only the build invocation to the verified
cached repository digest; subsequent offline builds passed. Slow broad read-only
poetry-cache search was stopped by exact own-process match; targeted prior bs7
build path resolved the dependency. No cache deletion or permission broadening.

## Next / rollback

Task5 source and offline artifact acceptance are complete. Next: Task6 existing
automatic recovery reservations/dispatch and remaining integration gates; do not
enable production, install paired CLI/policy or rerun real failed batches implicitly.
Before deployment rollback is source revert and not selecting these test artifacts;
no data restoration needed because no data changed. Once TTL is activated later,
code rollback cannot restore already-reclaimed Kubernetes objects.
