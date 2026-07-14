# T127 BS WGS Snakemake 9 Platform Design

## Goal

Deploy a WGS-only Airflow platform on BS10610 under
`/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS`, while keeping the
existing NIPT platform independent and unchanged. The WGS scheduler uses a
new Snakemake 9 environment created by
`/sg2/33.chenjiucheng/software/miniforge3/condabin/conda`.

The platform also records run-level resource telemetry and uses 4-5
additional NIPT FQ2026 batches to validate the resource collector under real
workload.

## Audit Findings

- The production WGS repository is
  `/mnt/biodevrwsg2/33.chenjiucheng/project/wgs` and is a dirty worktree. It is
  an external read-only dependency; T127 must not modify or commit it.
- `profiles/bs_direct/env.sh` works on `server10610` and currently resolves
  Snakemake 7.32.4 from `/bi/software/Python-3.7.11`.
- The direct profile has no qsub command and is configured for 96 local cores.
- The existing Airflow image is Debian 12. Mounting the host WGS runtime into
  that image fails while importing the Python 3.7 standard library. WGS must
  not run inside the generic Airflow worker process.
- The validated WGS test run has separate pre-calling and downstream
  Snakefiles, 16 sample rows, and explicit final targets. Its comparison step
  deliberately excludes Redis, mail, clinical publishing, and uploads.
- Existing generated launch scripts use Snakemake 7-only flags such as
  `--reason` and `--stats`; the Airflow runner must generate a Snakemake 9
  command instead of executing those scripts verbatim.

## Architecture

### Independent platform

The WGS deployment is a separate Compose project named `airflow-wgs`. It has
fresh Airflow and biodemo databases and does not share PostgreSQL, Redis,
volumes, run history, or scheduler state with `airflow-nipt`.

It reuses the platform code and frontend design but sets:

```text
DEPLOYED_PIPELINES=wgs
PLATFORM_ENVIRONMENT=BS10610-WGS
PROJECT_ROOT=/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS
```

Only `bio_wgs` is deployed initially. WGS automatic intake remains disabled
until the manual validation contract is complete.

Run and intake data use platform-level roots rather than living inside the
Git release tree:

```text
/mnt/biodevrwbi/33.chenjiucheng/airflow-result/wgs/runs
/mnt/biodevrwbi/33.chenjiucheng/airflow-result/nipt/runs
/mnt/biodevrwbi/33.chenjiucheng/airflow-intake-configs/wgs
/mnt/biodevrwbi/33.chenjiucheng/airflow-intake-configs/nipt
```

Existing NIPT run directories are retained at their current location and
mounted read-only for historical detail access. New NIPT runs use the new
result root; no historical result is moved or deleted during T127.

### Snakemake 9 environment

Create a dedicated environment named `wgs-snakemake9` using the approved
Miniforge executable. The environment contains Snakemake 9, the logger
interface, YAML support, and resource collector dependencies.

The runtime profile records the environment prefix, exact package list, and a
SHA256 provenance file. Rule commands continue to use the absolute Python,
R, Perl, Sentieon, VEP, samtools, bcftools, and reference paths already
present in the validated WGS config.

### Snakemake 9 workflow adapter

T127 does not run the Snakemake 7 workflow source unchanged. A versioned
`pipelines/wgs_s9` adapter is maintained in airflow-demo and deployed with the
platform release. The adapter is derived from the audited production
Snakefiles and rules, then changed only where required for Snakemake 9:

- replace removed CLI/config behavior with the Snakemake 9 local executor;
- remove generated Snakemake 7-only flags such as `--reason` and `--stats`;
- make wildcard, resources, shell, log, and target contracts pass S9 lint and
  dry-run;
- add `--logger airflow-demo` with per-rule/per-sample terminal events;
- preserve rule shell commands and approved external tool paths;
- keep Redis, mail, upload, and clinical publishing rules outside accepted
  Airflow target sets.

The original WGS repository remains read-only and is used as provenance and
result-comparison source. Adapter changes are reviewed as explicit diffs and
never written back to that worktree by this task.

### WGS runner isolation

Airflow orchestrates project-level tasks but launches WGS through a dedicated
Ubuntu 20.04-compatible runner. The runner receives only an approved config,
target list, and run workdir. It mounts:

- `/bi/software` read-only.
- `/bi/6.zhangran/software` read-only for the tools referenced by WGS config.
- The WGS repository and WGS-prod environment as separate read-only mounts.
- The dedicated Snakemake 9 conda environment read-only.
- Only the approved source batch or validation FASTQ root selected for the
  current run, read-only.
- The run workdir writable.

The runner never mounts the whole `/bi`, `/sg2`, `/clinical`, or another
user's project tree. Host and container paths are resolved from a repository
owned allowlist. The frontend cannot supply arbitrary Docker mount sources.

The runner hostname is `server10610` so the approved `bs_direct` environment
guard remains effective. No production WGS source file is copied back or
modified.

### DAG

`bio_wgs` exposes operator-readable stages:

```text
validate_request
prepare_wgs_run
wgs_pipeline.pre_calling
wgs_pipeline.variant_analysis
wgs_pipeline.collect_qc
collect_wgs_artifacts
```

The DAG has `max_active_runs=1` and uses a one-slot `wgs_full` pool. Snakemake
rule events provide the detailed sample/rule view; Airflow tasks remain
project-level stages.

Resume uses the same workdir with `--rerun-incomplete`. `--forceall` is
forbidden.

## Input And Validation Contract

The initial WGS Submit surface accepts an approved existing config and target
manifest, not arbitrary production paths. Paths must resolve under configured
WGS test/source roots and pass traversal checks.

Validation proceeds in gates:

1. Snakemake 9 parser/lint and dry-run against a copied run-local config.
2. A small pre-calling target set in a new workdir.
3. A controlled JX25 validation target set using the existing 16-sample test
   contract.
4. Full WGS execution only after the previous gates pass and node resources
   are available.

Redis, mail, clinical/web publication, OSS upload, and production database
writes are excluded from the accepted target list.

## Resource Telemetry

Each runner writes:

```text
logs/resources/resource_samples.jsonl
reports/resource_summary.json
```

Sampling occurs every 5 seconds and records:

- process-tree PSS and RSS from `/proc/*/smaps_rollup`;
- cgroup/container memory current and peak when available;
- CPU time and CPU percentage;
- process and container read/write bytes;
- block I/O and network I/O for Docker-backed runs;
- sample time, source, and collector warnings.

The summary contains peak PSS, peak RSS/cgroup memory, total read/write bytes,
CPU seconds, wall time, sampling interval, and completeness. Missing PSS is
reported as unavailable rather than substituted with RSS.

The backend adds a read-only run resource endpoint. Run Detail displays a
compact Resource Usage section and links to the raw JSONL artifact. The first
version stores telemetry as run artifacts and does not add high-volume time
series rows to PostgreSQL.

## NIPT Validation Batches

Select 4-5 complete NIPTPro batches from
`/sugon01/fq_backup/NIPT_fq_backup/FQ2026`. Require equal non-zero R1/R2 clean
FASTQ counts and exclude the already accepted 72-sample batch.

Runs are submitted manually and serially through the existing one-slot pool.
Stop after the first failed batch. For each run, verify final Airflow/backend
success, terminal rule events, QC import, required outputs, input immutability,
and resource summary completeness.

## Safety And Rollback

- Do not modify the production WGS repository or NIPT workflow source.
- Do not enable WGS or NIPT auto-submit.
- Do not delete Docker networks, volumes, results, logs, or FASTQ.
- Do not run WGS and NIPT heavy workloads concurrently on BS10610.
- Rollback stops only `airflow-wgs` without `-v`, disables WGS capability,
  and retains all run workdirs and provenance.

## Acceptance

- Snakemake 9 environment and package provenance are reproducible.
- WGS dry-run and controlled validation complete from Airflow with terminal
  rule events and no forbidden side effects.
- WGS platform is reachable through its own gateway and shows only WGS.
- Four or five additional NIPT batches run serially or stop safely at the
  first failure.
- Run Detail reports accurate peak PSS/RSS, I/O, CPU, and wall time or an
  explicit unavailable reason.
- Existing NIPT platform and accepted runs remain intact.
