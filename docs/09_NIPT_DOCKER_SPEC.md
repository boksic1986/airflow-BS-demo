# 09 NIPT Docker Integration Spec

## T114 QC normalization and completion contract

- Mapping QC percentage strings accept leading/trailing `%` and are stored as
  percentage points.
- Fetal-ratio percentage output is normalized to a 0-1 fraction.
- Informational read count, chrY, and gender values do not participate in the
  sample decision; missing thresholded fetal ratio remains unknown.
- A full run is collectable only when manifest, mapping QC, prediction rows,
  statistics files, and aberration files contain the same sample set.
- The first parent `all=success` logger event is the immutable pipeline finish
  timestamp used by Dashboard and Run Detail.

## T113 approved full-analysis runtime

- Default approved profile: `niptpro-s9-full-v1`.
- Scheduling runtime: Python 3.12 and Snakemake 9.23.1 in `/opt/snakemake9`.
- Rule tools: unchanged NIPTPro 1.0.11 `/opt/conda` environment.
- Resources: 40 cores, one Airflow pool slot, 90-minute timeout, expected
  operator estimate 25-35 minutes and memory ceiling 60 GiB.
- Inputs: selected top-level paired `*.clean.fastq.gz` files mounted read-only.
- Outputs: run-local workdir only; no source FASTQ or production bundle writes.
- Automatic NIPT intake: disabled. Full analysis is manually scanned,
  reviewed, confirmed, and submitted.

The 72-sample engineering acceptance run completed 591 Snakemake jobs in about
24.8 minutes with observed peak memory 44.61 GiB. Key summaries, mapping QC,
model predictions, and chr21 outputs were byte-identical to the S7 baseline.
This validates engineering consistency only, not clinical performance.

## T111 NIPT editable config boundary

The initial NIPT profile exposes `sexcutoff`, random seed, mapping/AneuScreen
threads, mapper workers, worker auto max, and pipe buffer size. Backend
validation applies numeric limits and ensures thread/worker values do not
exceed requested NIPT cores.

Database/model paths, `soft`, `input`, chip name, Redis, mapper manager/work
paths, image, network, owner, mounts, entrypoint, and Docker Compose remain
locked. The approved profile selects the NIPT and fetal-ratio images internally.
Airflow `validate_request` inspects both approved images and reports which
profile image is unavailable before the prepare or runner stage starts.
The prepare stage reads the NIPT base config from the profile-selected pipeline
root, so config and mounted pipeline versions cannot drift apart.
The frontend never displays `nipt_docker_compose.yml`, although the backend
keeps it as an audit artifact. `NIPT_ALLOW_HEAVY_RUN` remains authoritative:
the repository/env-example safety default is `false`; the T113 `fengxian`
deployment is explicitly `true` only after full engineering acceptance.

## 1. Scope

T103 keeps `nipt_docker` as the second deployable demo pipeline, but changes the
new submission path from fixed `run1/run2` templates to server-path scanned NIPT
chip batches.

Current v1 scope:

- Input mode: `nipt_docker_scan`.
- Scan root: `NIPT_INPUT_SCAN_ROOTS`, default container path `/opt/pipelines/NIPT/fastq`.
- Accepted FASTQ flavor: top-level `*.clean.fastq.gz` R1/R2 pairs in one chip folder.
- Default runtime after T113 acceptance: `run_mode=full_run`; `mount_smoke` is
  retained as a hidden engineering validation mode.
- Heavy runtime: `run_mode=full_run`, guarded by `NIPT_ALLOW_HEAVY_RUN=true`.
- Airflow DAG: `bio_nipt_docker`.
- Auto intake DAG: `bio_intake_scan`, paused on creation until bootstrap is complete.
- Frontend: Submit Task, Dashboard tracker, intake scanner panel, Runs/Samples/Failures filters, Run Detail QC/logs/files/config.

Out of scope:

- NIPT qsub.
- WES qsub deployment surface.
- WGS.
- Mail notification.
- Nested `002/*.adapter.fastq.gz` input.
- NIPT automatic intake or unsupervised full-batch submission.

Historical `template_id=run1|run2` runs remain readable and runnable for
compatibility tests, but the Submit Task UI and new API examples no longer
expose them.

## 2. Scanned Batch Contract

The scanner treats a folder such as:

```text
/opt/pipelines/NIPT/fastq/FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2
```

as one chip batch when it contains paired files like:

```text
NIPT26040207.A06.R1.clean.fastq.gz
NIPT26040207.A06.R2.clean.fastq.gz
```

The backend creates:

```text
workdir/config/samples.selected.tsv
workdir/config/request.json
```

Scan manifest columns:

```text
sample_id
library
index
R1
R2
source_dir
comment
```

`library` and `index` are derived from `sample_id` when it follows
`<library>.<index>`.

## 3. Airflow Runner

Task graph:

```text
validate_request
  -> prepare_nipt_docker_run
  -> run_nipt_docker
  -> collect_nipt_artifacts
```

`prepare_nipt_docker_run` writes:

```text
workdir/<chip_name>.csv
workdir/config/nipt_run_config.yaml
workdir/config/nipt_docker_compose.yml
workdir/config/nipt_airflow_request.json
```

The runner generates a run-local NIPT samplesheet/config and mounts the source
batch read-only as `/input_batch`. Large FASTQ files are not copied and the
external NIPT bundle is not modified.

The generated container name must be unique:

```text
NIPTPro_<analysis_id>
```

It must not reuse external container names such as `NIPTPro_runner`.

## 4. Deployment Contract

Required environment:

```text
NIPT_PIPELINE_ROOT=/home/jiucheng/pipelines/NIPT
NIPT_CONTAINER_ROOT=/opt/pipelines/NIPT
NIPT_INPUT_SCAN_ROOTS=/opt/pipelines/NIPT/fastq
HOST_SHARED_ROOT=/home/jiucheng/project/airflow-demo/shared
NIPT_DOCKER_IMAGE=172.17.61.235:2333/niptpro/niptpro:1.0.11
NIPT_FETAL_IMAGE=172.17.61.235:2333/niptpro/pytorch:biosan
NIPT_DOCKER_NETWORK=nipt_analysis_test_net
NIPT_DOCKER_CORES=40
NIPT_DOCKER_OWNER=6708:520
NIPT_ALLOW_HEAVY_RUN=false
DOCKER_SOCKET_GID=114
BACKEND_BASE_URL=http://backend:8000
```

The block above is the safe fallback/env-example contract. For profile-aware
T113 submissions, `niptpro-s9-full-v1` selects the derivative image internally;
the validated live deployment overrides only `NIPT_ALLOW_HEAVY_RUN=true`.
Arbitrary request-supplied image values remain prohibited.

Only `airflow-worker` mounts the Docker socket:

```text
/var/run/docker.sock:/var/run/docker.sock
```

Backend mounts only the NIPT fastq root read-only for scanning:

```text
${NIPT_PIPELINE_ROOT}/fastq:${NIPT_CONTAINER_ROOT}/fastq:ro
```

Forbidden runtime operations:

- `docker compose down -v`
- `docker volume prune`
- `docker system prune`
- Deleting host NIPT bundle or shared run roots

## 5. Auto Intake

`bio_intake_scan` calls:

```text
POST /api/intake/scan-and-submit
```

Default behavior:

- First sighting of a batch records `ready_state=observed`.
- A second scan with unchanged file count, size, mtime, and paths marks it
  `ready` and creates/submits one run.
- `bootstrap=true` records existing batches as bootstrap so historical data is
  not automatically re-run during deployment.
- PGT-A auto intake uses target `metadata`.
- NIPT Docker auto intake uses `mount_smoke`.

Operational sequence:

1. Deploy backend and migration.
2. Review `config/intake.yaml` and `GET /api/intake/config`.
3. Run a bootstrap scan against existing PGT-A/NIPT roots.
4. Confirm `/api/intake/status` shows expected observed/bootstrap rows.
5. Unpause `bio_intake_scan` if automatic intake should run.

T104 scanner configuration:

- NIPT Docker roots come from `config/intake.yaml` first.
- `NIPT_INPUT_SCAN_ROOTS` remains only a fallback for missing config files.
- New NIPT intake uses `file_flavor=clean_fastq`, `r1_pattern=*.R1.clean.fastq.gz`,
  `r2_pattern=*.R2.clean.fastq.gz`, and ignores `002/*.adapter.fastq.gz`.
- The default ready rule is `stable_fingerprint` with `stable_scans=2`.

## 6. QC, Logs, And Artifacts

Standard logs:

```text
workdir/logs/snakemake.stdout.log
workdir/logs/snakemake.stderr.log
workdir/logs/nipt_docker.command.txt
workdir/logs/events/snakemake_events.jsonl
```

Standard QC:

```text
workdir/reports/qc_summary.tsv
```

`mount_smoke` writes one `nipt_mount_smoke=pass` row per selected scanned
sample. Full-run parsing reads outputs such as `mappingQC.csv` and
`*.model.predict.csv` and maps them into platform metrics:

- `read_count`
- `Q30`
- `unique_mapping_rate`
- `pcr_duplication_rate`
- `chrY_percent`
- `gender`
- `fetal_fraction`

Progress events:

- `mount_smoke` emits `nipt_mount_smoke` `running/success/failed` events.
- Every event is written to `workdir/logs/events/snakemake_events.jsonl`.
- If `backend_event_url=http://backend:8000/api/events/snakemake` is present in
  DAG conf, the runner also POSTs to FastAPI.
- Backend POST failure is non-fatal and is written locally as
  `backend_post_error`.
- `full_run` parses Docker stdout/stderr for Snakemake rule blocks when the
  heavy path is explicitly enabled.

Artifacts exposed for `pipeline=nipt_docker`:

- `snakemake_stdout`
- `snakemake_stderr`
- `nipt_qc_summary`
- `nipt_docker_compose`
- `nipt_run_config`
- `nipt_airflow_request`
- `nipt_docker_command`
