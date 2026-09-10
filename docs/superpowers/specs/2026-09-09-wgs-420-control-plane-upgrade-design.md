# WGS 4.2.0 Control-plane Upgrade Design

## Goal

Make WGS 4.2.0 the release used for new submissions while preserving read and
controlled retry compatibility for historical 4.1.1 runs. Complete the
platform-side prepare handoff introduced by 4.2.0 and expose enough immutable
release evidence for operators to confirm what will run.

No formal batch is submitted by this change. Automatic WGS dispatch remains
disabled and Step7/Step8 remain manual.

## Frozen release identity

- Current release: `wgs-4.2.0-b067c72`, version `V4.2.0`, source commit
  `b067c72eed795e59b724b13324b0d380ae8b7e94`.
- CCE profile: `wgs-4.2.0` revision `r1`, SHA-256
  `c6dea31fb06f8a1c0ac242cea8fa990486d631f877d64a6f8d25b67dadfa8511`.
- Pipeline build SHA-256:
  `71695b2a3ab1d83bab68454b1785d2b6791b26c6f57f5ecceda465975788b7f6`.
- Resource manifest SHA-256:
  `89ea4f38df122f33013c8c04a660671d67e996f7b074cc65bccbfa9ff72a4e95`.
- Required platform CLI: `cce-pipeline 0.8.3`.

The deployment must re-read and verify these values from the repository and
profile before activation. Sensitive operator configuration is not copied into
the application repository or evidence.

## Release catalog

`config/wgs_releases.yaml` advances to schema 4. It contains a
`current_release_id` and an allowlisted `releases` collection. New runs use the
current entry; an existing run resolves its own release by the immutable
`pipeline_release_id` stored in `params_json`.

This avoids making historical 4.1.1 runs unreadable or incorrectly preparing
them with 4.2.0. Unknown releases fail closed.

## Prepare handoff

For 4.2.0 `prepare_sampleinfo` and `prepare_analysis`, the platform runtime gate
creates an immutable generation-scoped `wgs.prepare-handoff.request.v1` under
the run control directory and invokes WGS only through `--handoff-request`.

- The request binds analysis, attempt, execution, generation, request hash and
  release identity.
- `prepare_sampleinfo` publishes a hashed sampleinfo snapshot and a privacy-safe
  candidate receipt.
- `prepare_analysis` binds the source sampleinfo SHA-256 and a frozen pending
  manifest. The first generation starts with an empty pending set; later
  generations may consume the preceding private pending artifact after hash and
  identity validation.
- The gate validates the receipt identity, schema, hashes and artifact paths
  before reporting stage success.
- The backend imports only the safe decision rows. Pending reasons are stored in
  the existing sample metadata projection; clinical fields and raw order values
  are not imported.

4.1.1 retains its legacy file-mode prepare path for compatibility.

## Runtime selection

Node200 keeps an allowlisted release-id-to-repository mapping. The request never
selects an arbitrary repository path. Repository commit and tracked runtime
cleanliness are checked before every prepare stage. Each release uses its own
`prepare/config.yaml` without printing or copying that file.

The 0.8.3 CLI is installed as a versioned ctapa-owned executable with its hash
recorded. The previous 0.8.2 executable and configuration are retained for
rollback. The WGS operator config points to the 4.2.0 repository and r1 profile,
while retaining the approved obsutil transfer adapter.

## QC and UI compatibility

The WGS 4.2.0 QC threshold file is byte-identical to 4.1.1. The existing exact
`<batch>.QCstat.tsv` remains the authoritative batch/sample projection; a new
`<batch>.multi.QCstat.tsv` must not shadow it. The release API and registry show
4.2.0 plus controlled profile/CLI evidence; historical run detail continues to
show its frozen release.

## Activation and rollback

Activation requires zero active WGS runs and zero transfer leases. Backend,
observer, scanner and Airflow components that cache release/runtime code are
recreated from the same immutable application release; the frontend is rebuilt
only if its release-contract code changes. PostgreSQL/Redis volumes and WGS data
are untouched.

Rollback restores the previous application pointer, node200 runtime env,
operator config and versioned CLI selection. It does not delete either WGS
repository or any run data.
