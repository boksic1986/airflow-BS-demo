# PGT-A Snakemake 9 runtime

This directory contains the sample-free source used by the airflow-demo PGT-A `predict` profile. Release `pgta-s9-v1.4` also locks the CBS seed, supplies the approved R runtime, and verifies WisecondorX prediction output instead of trusting its exit code alone.

- Deploy immutable releases with `scripts/deploy_pgta_s9_release.sh`.
- Production runs use the fixed XX, XY, and gender reference assets from `config/pipeline_profiles.yaml`.
- Airflow exposes project stages; the `airflow-demo` Snakemake logger emits rule and sample events.
- CNV QC failure writes `skipped_qc` for prediction and remains distinct from workflow failure.
- Reference-building inputs and sample groups are intentionally excluded from the normal submit profile.

The original `/home/jiucheng/pipelines/PGT_A` installation is not modified by this release workflow.
