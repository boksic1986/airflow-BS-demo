# T127 BS Shared NIPT and WGS Control Plane Design

## Goal

Upgrade the accepted BS10610 NIPT deployment into one shared Airflow control
plane for NIPT Docker and host-native WGS. PGT-A is not deployed on BS.

The existing Compose project, PostgreSQL/Redis volumes, frontend gateway, and
Airflow CeleryExecutor services are reused. T127 must not create a second WGS
Compose stack, second scheduler, or second business database.

## Runtime Architecture

The shared Compose project is `airflow-nipt` and runs:

- one React/nginx gateway;
- one FastAPI backend;
- one PostgreSQL instance with separate Airflow and biodemo databases;
- one Redis broker;
- one Airflow API server, scheduler, and Celery worker.

Only these DAGs are deployed:

```text
bio_nipt_docker
bio_wgs
bio_intake_scan  # paused until explicit intake acceptance
```

Both analysis DAGs use the one-slot `bs_heavy_analysis` pool. The slot limits
concurrent batches, not CPU cores. NIPT uses 32 cores inside its container;
WGS uses up to 96 host cores. NIPT and WGS heavy runs therefore never overlap.

The existing gateway remains the only published service:

```text
172.17.106.10:12959 -> frontend and /api
172.17.106.10:12958 -> Airflow through nginx
```

The external Docker network is immutable:

```text
nipt_analysis_test_net
subnet 192.168.199.0/24
gateway 192.168.199.1
```

## NIPT Docker

NIPT continues to run in the validated Snakemake 9 image
`172.17.61.235:2333/niptpro/niptpro:1.1.11`. The legacy `1.0.11` image is kept
for rollback. Input FASTQ and workflow/locale sources are read-only; output is
written below `/mnt/biodevrwbi/33.chenjiucheng/airflow-result/nipt/runs`.

## WGS Host Runtime

WGS does not run in Docker. Airflow uses `SSHOperator` to invoke the exact
forced command `wgs-run <analysis_id> <stage>` on BS10610. The key has no PTY
or forwarding rights and cannot execute arbitrary shell commands.

Host assets live under:

```text
/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS
```

The dedicated scheduler environment is created with
`/sg2/33.chenjiucheng/software/miniforge3/condabin/conda` and pins Snakemake
9.23.1 with Python 3.12. Rule tools continue to come from the approved WGS
environment script. The production WGS repository is a read-only dependency.

The generated host command uses:

```text
--executor local --cores 96 --rerun-incomplete --keep-going
--printshellcmds --show-failed-logs --logger airflow-demo
```

`--forceall` is forbidden. Historical pre-calling context is linked read-only
from exact approved roots; broad `/bi` and `/sg2` allowlists are forbidden.

## WGS DAG

`bio_wgs` exposes project-level stages:

```text
validate_request
  -> prepare_wgs_run
  -> wgs_pipeline.pre_calling
  -> choose_wgs_path
     -> collect_wgs_artifacts                         # pre-calling only
     -> wgs_pipeline.variant_analysis
        -> wgs_pipeline.collect_qc
        -> collect_wgs_artifacts                      # full
```

Snakemake logger events provide rule/sample progress. Airflow tasks remain
project-level stages and do not expand every sample job into the DAG graph.

## Inputs, Outputs, and Intake

WGS run configuration and intake requests are stored below
`/mnt/biodevrwbi/33.chenjiucheng/airflow-intake-configs/wgs`. NIPT requests
remain below the sibling `nipt` directory. Results are written to:

```text
/mnt/biodevrwbi/33.chenjiucheng/airflow-result/wgs/runs
/mnt/biodevrwbi/33.chenjiucheng/airflow-result/nipt/runs
```

The shared `bio_intake_scan` understands both request contracts, but remains
paused during T127. Neither pipeline is automatically submitted.

## Validation Scope

WGS acceptance is intentionally bounded to one family by default, with a
second family allowed only if the first result requires comparison. One family
contains three pre-calling samples in the approved validation contract.
It runs with a 96-core ceiling and does not execute the original 16-sample
cohort as new input.

After WGS reaches a terminal state, up to five NIPT batches may run serially.
Stop immediately at the first failed batch. WGS and NIPT must never overlap.

For each run verify Airflow/backend status, terminal logger events, required
outputs, input immutability, and resource telemetry including wall time, CPU,
peak PSS/RSS, and read/write I/O when available.

## Safety and Rollback

- Do not modify production WGS or NIPT workflow sources.
- Do not enable automatic intake during T127.
- Do not delete Docker networks, volumes, databases, results, logs, or FASTQ.
- Image movement is fengxian to local Windows to BS; direct server-to-server
  transfer is prohibited.
- BS1069 is a stopped cold standby and must not run active-active with BS10610.
- Roll back by pausing intake, stopping only recreated application services
  without `-v`, and restoring the previous shared release/images. Keep the
  existing `airflow-nipt` project and its PostgreSQL/Redis volumes.

## Acceptance

- `/api/platform/capabilities` exposes only `nipt_docker,wgs`.
- Airflow lists only `bio_nipt_docker`, `bio_wgs`, and `bio_intake_scan`.
- One shared CeleryExecutor control plane and one heavy-analysis pool are used.
- WGS Snakemake 9 dry-run and one-family full validation complete with logger
  events and no forbidden side effects.
- NIPT remains compatible with the accepted S9 runtime and additional batches
  run serially only after WGS is terminal.
- BS1069 has matching release/images and remains stopped.
