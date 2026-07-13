# NIPT YAML Intake Request Design

## Goal

Allow an operator to prepare a small NIPT request YAML without knowing or
copying an absolute FASTQ path. The backend resolves the requested sequencing
batch inside approved NIPT FASTQ roots, validates paired clean FASTQ files, and
uses the existing `bio_nipt_docker` create and submit path.

This request flow is separate from directory discovery. NIPT directory
discovery remains read-only because `auto_submit.enabled` stays false.

## Paths

- Operator edit workspace (not scanned):
  `/home/jiucheng/project/airflow-intack-configs/nipt/`
- Scanner trigger inbox (backend mount):
  `/home/jiucheng/project/airflow-intake-requests/nipt/`
- Backend container inbox:
  `/data/airflow-intake-requests/nipt/`
- Completed request archive:
  `/data/airflow-intake-requests/nipt/.archive/YYYY/MM/<request_id>/`
- Approved FASTQ roots come from the existing `nipt_docker.roots` entries in
  `config/intake.yaml`.

The scanner only accepts `*.nipt.yaml`. Operators publish atomically by copying
to `<request_id>.nipt.yaml.partial` and renaming it to
`<request_id>.nipt.yaml`. Partial files and files below `.archive` are ignored.

## Request Contract

```yaml
version: 1
request_id: project-20260713
project_id: NIPT-PROJECT-20260713
batch_id: 260422_TPNB500380AR_1070_AH33KYBGY2
samples: all
submitted_by: jiucheng
runtime_profile_id: niptpro-s9-full-v1
run_mode: full_run
cores: 32
submit: true
```

- `request_id`, `project_id`, and `batch_id` are required identifiers. They do
  not accept path separators.
- `samples` is `all` or a non-empty unique list of sample IDs from the resolved
  batch.
- `runtime_profile_id` must be an approved NIPT profile.
- `run_mode` is `full_run` for this operator-triggered workflow.
- `cores` is between 1 and 40.
- `submit` is an explicit boolean. `false` permits discovery and validation but
  never creates a run.
- Unknown fields, duplicate YAML keys, aliases, custom tags, and documents over
  64 KiB are rejected.
- Absolute paths, Docker image names, Compose options, command lines, volumes,
  networks, and executable paths are not accepted.

The file name stem must equal `request_id` so a copied request cannot silently
change identity.

## Resolution And Idempotency

For each request, the backend searches approved NIPT roots for directories
whose basename exactly equals `batch_id`. A request fails if no directory or
more than one directory matches. The selected directory must contain complete
top-level `*.R1.clean.fastq.gz` and `*.R2.clean.fastq.gz` pairs.

The discovery fingerprint includes the normalized request plus the selected
FASTQ paths, sizes, and modification times. Two stable observations are
required. The discovery key uses the request inbox and `request_id`, while the
run records the resolved source batch and source fingerprint. A previously
observed or archived `request_id` cannot create a second run.

## Submission Gate

Creating and submitting a run requires all of the following:

1. The request has `submit: true`.
2. `nipt_docker.intake.request_submit_enabled` is true.
3. The global intake auto-submit gate is true.
4. The request has passed two stable scans.
5. The runtime profile, heavy-run gate, selected samples, and source paths pass
   the existing NIPT run validation.

The existing `nipt_docker.auto_submit.enabled: false` continues to block
ordinary directory discovery. It does not override an explicit YAML request;
the dedicated `request_submit_enabled` gate controls that path.

## Archiving

After workflow success, only the request YAML is moved to the archive. NIPT
FASTQ data is never moved or deleted. The archived discovery row remains the
idempotency and audit record. Failed workflows remain active for diagnosis.

## Errors And Observability

Malformed request files become structured Intake Discovery errors with the
request ID, source file, and actionable message. One invalid request does not
stop other requests or ordinary NIPT discovery. Preview remains read-only and
reports whether the request is blocked by `submit: false`, server policy, or
stability checks.

## Acceptance

- Parser tests cover valid requests, sample subsets, malformed and unsafe YAML,
  path-free batch resolution, ambiguous batches, and ignored partial files.
- Intake tests prove two-scan stability, explicit submit gating, no accidental
  run for `submit: false`, idempotent recovery, and request-only archiving.
- The deployed trigger inbox is empty except for `.archive` during rollout, so
  acceptance cannot launch a full NIPT analysis.
- Backend tests and Compose config run on `fengxian`; local checks are limited
  to Git and documentation consistency.
