# 09 NIPT Docker Integration Spec

## 1. Scope

T103 keeps `nipt_docker` as the second deployable demo pipeline, but changes the
new submission path from fixed `run1/run2` templates to server-path scanned NIPT
chip batches.

Current v1 scope:

- Input mode: `nipt_docker_scan`.
- Scan root: `NIPT_INPUT_SCAN_ROOTS`, default container path `/opt/pipelines/NIPT/fastq`.
- Accepted FASTQ flavor: top-level `*.clean.fastq.gz` R1/R2 pairs in one chip folder.
- Default runtime: `run_mode=mount_smoke`.
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
- Re-running a full 40-core production NIPT batch during default acceptance.

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
