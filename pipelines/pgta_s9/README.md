# PGT-A Snakemake Pipeline

This pipeline is for PGT-A analysis with `fastp + bwa + WisecondorX`.

## 0. Recent updates

- Refactored NPZ parsing to follow official WisecondorX convert format (`binsize + sample + quality`).
- Added reference prefilter robustness: unusable NPZ samples are logged and excluded before model QC.
- Improved `WisecondorX convert` throughput with parallel execution (`--threads`) and per-sample logs.
- Added stricter pipeline reproducibility logs (git branch/commit + tool versions).
- Added repository cleanup guidance and ignore rules for temporary scratch files.

Supported targets:
- `mapping`: fastp + bwa + samtools sort/index
- `reference_qc`: prefilter + bin/pca tuning (when tuning is enabled)
- `reference`: build final reference model
- `cnv_qc`: CNV input QC (when CNV is enabled)
- `cnv`: WisecondorX predict (when CNV is enabled)

## 1. Initialize configs and update reference groups

Entry script: `scripts/init_pgta_project.py`

Available actions:
- `init_config`: initialize project structure and a typed config YAML
- `build_reference_groups`: update `build_reference.groups` from Excel

Recommended config split:
- `build_config.yaml`: used only for `reference_qc` + `reference`
- `predict_samples.yaml`: base config used only for predict samples
- `config_predict.yaml`: generated from `predict_samples.yaml` + built references

### 1.1 Init build-ref config

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/python scripts/init_pgta_project.py \
  --action init_config \
  --config_kind build_ref \
  --project /path/to/project \
  --fq_dir /path/to/fastq \
  --output_config /path/to/project/build_config.yaml \
  --template_snakefile /home/jiucheng/pipelines/PGT_A/Snakefile
```

Optional: init config and fill XX/XY groups from Excel in one step.

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/python scripts/init_pgta_project.py \
  --action init_config \
  --config_kind build_ref \
  --project /path/to/project \
  --fq_dir /path/to/fastq \
  --output_config /path/to/project/build_config.yaml \
  --build_reference_mode excel \
  --sample_info_xlsx /home/jiucheng/pipelines/PGT_A/sample_info/CNV-seq.xlsx \
  --batch2_fq_dir /data/project/CNV/PGT-A/rawdata/lib_test/2026-02-05 \
  --batch3_fq_dir /data/project/CNV/PGT-A/rawdata/lib_test/2026-03-03
```

### 1.2 Init predict-samples config

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/python scripts/init_pgta_project.py \
  --action init_config \
  --config_kind predict_samples \
  --project /path/to/project \
  --fq_dir /path/to/predict_fastq \
  --output_config /path/to/project/predict_samples.yaml \
  --template_snakefile /home/jiucheng/pipelines/PGT_A/Snakefile
```

### 1.3 Update only build_reference groups

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/python scripts/init_pgta_project.py \
  --action build_reference_groups \
  --project /path/to/project \
  --output_config /path/to/project/build_config.yaml \
  --sample_info_xlsx /home/jiucheng/pipelines/PGT_A/sample_info/CNV-seq.xlsx \
  --batch2_fq_dir /data/project/CNV/PGT-A/rawdata/lib_test/2026-02-05 \
  --batch3_fq_dir /data/project/CNV/PGT-A/rawdata/lib_test/2026-03-03
```

Notes:
- `--project` is required for `build_reference_groups`.
- If `--output_config` does not exist, a template config is created automatically.
- `samples` contains all batch2 + batch3 samples.
- `build_reference.groups` is generated from Excel rules.
- `build_config.yaml` writes `pipeline.mode: build_ref`.
- `predict_samples.yaml` writes `pipeline.mode: predict` and does not contain `build_reference.groups`.

## 2. Default key parameters (from init_pgta_project)

- `core.wisecondorx.binsize: 100000`
- `core.wisecondorx.tuning.bin_sizes: [100000, 200000, 300000, 500000, 750000, 1000000]`
- `core.wisecondorx.tuning.pca.min_explained_variance: 0.0`
- `core.wisecondorx.reference_prefilter.binsize: 100000`
- `core.wisecondorx.cnv.convert_binsize: 100000`
- `core.wisecondorx.cnv.zscore: 5`
- `core.wisecondorx.cnv.alpha: 0.001`

## 3. Reference output layout

Default root: `core.wisecondorx.reference_model_root: reference`

- `reference/XX/prefilter/`
- `reference/XX/result/`
- `reference/XY/prefilter/`
- `reference/XY/result/`
- `reference/gender/result/`
- `reference/gender/common_best_binsize.txt`
- `reference/prefilter/reference_inlier_samples.txt`
- `reference/tuning/`

## 4. Run the pipeline

Use Snakemake in your server env:
`/biosoftware/miniconda/envs/snakemake_env/bin/snakemake`

### 4.1 Mapping

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  -s /home/jiucheng/pipelines/PGT_A/Snakefile \
  --configfile /path/to/project/build_config.yaml \
  --cores 32 -p mapping
```

### 4.2 Build reference (global best binsize + sex-specific refs)

Reference build now follows this order:

1. `XX` prefilter on `XX` samples only
2. `XY` prefilter on `XY` samples only
3. merge retained prefilter inliers
4. run one global tuning on merged inliers using autosomes only (`chr1-22`)
5. write one shared `best binsize`
6. build `XX ref`, `XY ref`, and `gender ref` with that same binsize

Run reference QC stage first:

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  -s /home/jiucheng/pipelines/PGT_A/Snakefile \
  --configfile /path/to/project/build_config.yaml \
  --cores 32 -p reference_qc
```

Then build final reference:

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  -s /home/jiucheng/pipelines/PGT_A/Snakefile \
  --configfile /path/to/project/build_config.yaml \
  --cores 32 --rerun-incomplete -p reference
```

Or run all together:

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  -s /home/jiucheng/pipelines/PGT_A/Snakefile \
  --configfile /path/to/project/build_config.yaml \
  --cores 32 --rerun-incomplete -p mapping reference_qc reference
```

### 4.3 CNV

Predict now follows this order in dual-reference mode:

1. `WisecondorX convert` with the shared `best binsize`
2. `WisecondorX gender` with the mixed `gender ref`
3. CNV input QC
4. choose `XX ref` or `XY ref` from the gender result
5. `WisecondorX predict --gender ...`

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  -s /home/jiucheng/pipelines/PGT_A/Snakefile \
  --configfile /path/to/project/config_predict.yaml \
  --cores 32 -p mapping cnv_qc cnv
```

## 5. Main outputs

Reference:
- `reference/{SEX}/prefilter/reference_sample_qc.tsv`
- `reference/{SEX}/prefilter/reference_sample_qc.svg`
- `reference/{SEX}/prefilter/reference_inlier_samples.txt`
- `reference/{SEX}/prefilter/prefilter_summary.yaml`
- `reference/prefilter/reference_inlier_samples.txt`
- `reference/tuning/bin_pca_grid.tsv`
- `reference/tuning/best_params.yaml`
- `reference/tuning/best_bin_pca_elbow.svg`
- `reference/tuning/reference_qc_metrics.svg`
- `reference/tuning/reference_inlier_samples.txt`
- `reference/tuning/bin_*/pca_profile.tsv`
- `reference/XX/result/*.npz`
- `reference/XY/result/*.npz`
- `reference/gender/result/*.npz`
- `reference/gender/common_best_binsize.txt`

CNV:
- `wisecondorx/cnv/gender/{sample}.gender.tsv`
- `wisecondorx/cnv/qc/{sample}.qc.tsv`
- `wisecondorx/cnv/qc/{sample}.qc.svg`
- `wisecondorx/cnv/predict/{sample}*`

## 6. Logs and audit trail

Logs are written to:
- `logs/fastp/`
- `logs/bwa/`
- `logs/metadata/`
- `logs/wisecondorx/`
- `logs/cnv/`

Python scripts now use the `logging` module for pipeline step tracing
(start/end, command execution, sample filtering, QC summaries, and failure reasons).
For key rules, script logging is persisted via `--log` in addition to rule-level shell logs.

Audit metadata in logs includes:
- `git_branch`
- `git_commit`
- tool versions (`fastp`, `bwa`, `samtools`, `WisecondorX`, `python`)

## 7. Performance notes

- `scripts/reference_prefilter_qc.py` and `scripts/tune_wisecondorx_bin_pca.py` now run `WisecondorX convert` in parallel, controlled by `--threads`.
- Each sample convert job writes its own log under `.../converted/convert_logs/`.
- Main pipeline log keeps a compact progress summary for convert start/done events.
- Some repeated list/set traversals were reduced in sample filtering and outlier set construction.
- NPZ parsing now follows official WisecondorX layout: `binsize + sample(dict chr1..24) + quality`, avoiding expensive generic object scans.

## 8. Troubleshooting

### 8.1 IndentationError in Snakefile/pipeline.smk

```bash
cd /home/jiucheng/pipelines/PGT_A
sed -i 's/\r$//' Snakefile rules/pipeline.smk
nl -ba rules/pipeline.smk | sed -n '70,90p;240,260p'
```

### 8.2 WisecondorX convert argument error

`WisecondorX convert` in this pipeline no longer uses `--cpus` because some versions do not support it.

### 8.3 `No usable numeric arrays found in .../*.npz`

`reference_prefilter_qc.py` now auto-drops unusable NPZ samples and records them in log/summary.
NPZ parsing follows official WisecondorX convert output layout:
- `binsize`
- `sample` (dict with chromosome keys `1..24`)
- `quality`

If remaining usable samples are fewer than `--min-reference-samples`, the rule still fails by design.
In that case:
- check sample-level convert logs under `reference/{SEX}/prefilter/converted/convert_logs/`
- remove problematic BAM/NPZ from reference groups or regenerate those BAM files
- rerun `reference_qc`

### 8.4 Repository temporary files

Temporary files (for ad-hoc debugging/source lookups) are not part of the pipeline and should not remain in repo root.
Ignored by default:
- `tmp_*`
- `*.tmp`

## 9. Workflow structure (modularized)

The workflow is now organized into modular rule files:

- `Snakefile`: config loading, target assembly, top-level entry rules, and includes
- `rules/common_preprocess.smk`: shared preprocessing (`collect_run_metadata`, `fastp_bwa`)
- `rules/reference_workflow.smk`: reference-only stages (prefilter, tuning, reference build)
- `rules/predict_workflow.smk`: predict-only stages (`convert`, CNV QC, CNV predict)

This keeps common preprocessing and downstream analysis modes separated while preserving existing rule names, outputs, and DAG behavior.

## 10. Config entry points

The workflow now uses two config types:

- `build_config.yaml`
  - `pipeline.mode: build_ref`
  - used only for `reference_qc` and `reference`
  - contains `build_reference.groups`
- `predict_samples.yaml`
  - `pipeline.mode: predict`
  - used only as the base sample config for prediction
  - must not contain `build_reference.groups`
- `config_predict.yaml`
  - generated from `predict_samples.yaml`
  - contains built ref paths:
    - `reference_output_by_sex.XX`
    - `reference_output_by_sex.XY`
    - `gender_reference_output`
    - `common_reference_binsize_output`

Run examples:

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  -s /home/jiucheng/pipelines/PGT_A/Snakefile \
  --configfile /path/to/project/build_config.yaml \
  --cores 32 -p
```

```bash
/biosoftware/miniconda/envs/snakemake_env/bin/snakemake \
  -s /home/jiucheng/pipelines/PGT_A/Snakefile \
  --configfile /path/to/project/config_predict.yaml \
  --cores 32 -p
```

## 11. PGT-A algorithm notes

This section explains algorithm concepts only. Runtime behavior, thresholds, QC logic, CNV logic, mosaic logic, sex logic, and output schema are still defined by code/config.

### 11.1 End-to-end stages

1. Raw data preprocessing
- FASTQ input
- FASTQ QC (`fastp`)
- mapping (`bwa`) + BAM sort/index (`samtools`)

2. Bin-level signal construction
- convert aligned reads into fixed-size genomic bin signals

3. Reference building
- estimate normal-background distributions on reference samples
- optional prefilter and tuning before final reference model generation

4. Predict
- process test sample with reference-consistent settings
- quantify deviation from reference
- call CNV results

### 11.2 Notation

- `X_ij`: raw count/signal of sample `i` at bin `j`
- `X~_ij`: normalized/corrected bin signal
- `mu_j`, `sigma_j`: reference mean/std at bin `j`
- `Z_j`: per-bin z-score for test sample

### 11.3 Typical formulas

Library-size normalization:

`X_norm_ij = X_ij / sum_j X_ij`

z-score:

`Z_j = (X~_tj - mu_j) / sigma_j`

Optional floor-stabilized form:

`Z_j = (X~_tj - mu_j) / max(sigma_j, sigma_min)`

If log-ratio is used by a specific implementation path:

`R_j = log2((X~_tj + eps) / (mu_j + eps))`

### 11.4 PCA / denoising intuition

Reference matrix (sample x bin) can be centered and projected to principal components to capture systematic technical variance (for example GC/batch/amplification effects). Tuning determines suitable bin size / PCA dimension combinations. In this pipeline, this behavior is implemented by tuning scripts and WisecondorX-driven workflows.

### 11.5 Segmentation note

CNV inference commonly performs segmentation over ordered bin signals. Exact segmentation internals are tool-implementation specific; this pipeline delegates core prediction behavior to `WisecondorX predict`.

## 12. Current workflow logic

### 12.1 Build reference

Current reference logic is:

1. shared preprocessing: `fastp + bwa + samtools`
2. `XX` reference prefilter on `XX` samples only
3. `XY` reference prefilter on `XY` samples only
4. merge the retained reference samples from both groups
5. run one global tuning on the merged reference set
6. compute one shared `best binsize` from autosomes only (`chr1-22`)
7. build:
   - `XX ref`
   - `XY ref`
   - `gender ref`
   all with that same shared binsize

This means:
- reference sample QC is sex-specific
- best binsize selection is global
- best binsize is not influenced by chrX/chrY
- final reference models remain sex-specific where they should be

### 12.2 Predict

Current predict logic is:

1. convert sample BAM to NPZ using the shared `best binsize`
2. run `WisecondorX gender` using the mixed `gender ref`
3. run CNV input QC
4. read `gender.tsv`
5. select `XX ref` or `XY ref`
6. run `WisecondorX predict --gender ...`

This keeps gender calling and sex-specific reference selection explicit and reproducible.

## 13. Reference QC metrics

Reference QC is used only in the `build ref` flow. It does not replace WisecondorX core calling logic. Its role is to remove poor reference samples and choose a stable shared binsize.

### 13.1 Prefilter metrics

Implemented in `scripts/reference_prefilter_qc.py`.

Main metrics:

- `reads`
  - total aligned bin counts for the sample
  - used to flag low-depth reference samples
- `corr_to_median`
  - correlation between the sample profile and the cohort median profile
  - low values indicate strong deviation from the reference cohort
- `noise_mad`
  - median absolute deviation of residual signal relative to the cohort median
  - reflects bin-to-bin noise
- `noise_mad_z`
  - robust z-score of `noise_mad`
  - flags unusually noisy samples
- `reconstruction_error`
  - PCA reconstruction error
  - measures how poorly the sample fits the cohort structure
- `reconstruction_error_z`
  - robust z-score of `reconstruction_error`
  - flags PCA-space outliers

Sample outlier labels:

- `low_reads`
- `low_corr`
- `high_recon_z`
- `high_noise_z`

### 13.2 Tuning metrics

Implemented in `scripts/tune_wisecondorx_bin_pca.py`.

For each candidate binsize, the workflow evaluates:

- `pca_components`
  - PCA dimension actually evaluated for the current `(binsize, pca_components)` pair
- `selected_pca`
  - heuristic recommended PCA dimension for the current binsize
  - kept as a reference value and compatibility field
- `elbow_pca`
  - PCA elbow point from cumulative explained variance
- `cum_explained_variance`
  - cumulative explained variance at the evaluated `pca_components`
- `component_explained_variance`
  - explained variance ratio of the evaluated PCA component itself
- `component_cum_explained_variance`
  - same cumulative explained variance value as `cum_explained_variance`, written explicitly for the evaluated component
- `is_selected_pca`
  - whether the evaluated `pca_components` matches the heuristic `selected_pca`
- `pca_profile_tsv`
  - per-binsize detailed PCA profile with `component`, `explained_variance_ratio`, `cumulative_explained_variance_ratio`
- `cv_reconstruction_mse`
  - cross-validated reconstruction error
  - lower is better
- `inliers`
  - number of retained reference samples
- `outliers`
  - number of rejected samples
- `outlier_fraction`
  - rejected fraction
- `samples`
  - usable sample count
- `features`
  - usable aligned autosomal bins
- `status`
  - binsize pass/fail state

Important:

- `reference/tuning/bin_pca_grid.tsv` is a two-dimensional tuning grid, one row per `(binsize, pca_components)` pair.
- `selected_pca`, `elbow_pca`, and the cumulative explained variance threshold are reference signals only.
- Final `best_binsize` and `best_pca_components` are selected from the full `(binsize, pca_components)` search space, not from a single heuristic PCA per binsize.
- To verify monotonic cumulative explained variance within one binsize, inspect the corresponding `reference/tuning/bin_*/pca_profile.tsv`.

Typical binsize failure states:

- `FAIL_USABLE_SAMPLE_COUNT`
- `INVALID_PCA_COMPONENTS`
- `FAIL_INLIER_COUNT`
- `FAIL_OUTLIER_FRACTION`
- `FAIL_CV`

### 13.3 What defines the current optimum

In practice, the current optimum is chosen by combining:

- sample-level stability:
  - `corr_to_median`
  - `noise_mad_z`
  - `reconstruction_error_z`
- binsize-level quality:
  - `cv_reconstruction_mse`
  - `outlier_fraction`
  - `inliers`

The selected `best binsize` is then reused consistently by:

- `XX ref`
- `XY ref`
- `gender ref`
- `predict convert`

## 14. Implementation mapping

| Module | Rule / Script | Purpose | Main input | Main output |
|---|---|---|---|---|
| metadata | `collect_run_metadata` / `scripts/collect_run_metadata.py` | collect run/tool metadata | project + tool paths | `logs/run_metadata.tsv` |
| preprocess | `fastp_bwa` | fastq QC + mapping | sample R1/R2 | cleaned FASTQ, sorted BAM/BAI |
| reference prefilter | `reference_prefilter_xx` / `reference_prefilter_xy` / `scripts/reference_prefilter_qc.py` | remove unusable/outlier reference samples inside each sex group | reference BAMs | prefilter QC/report/inlier list |
| reference prefilter merge | `merge_reference_prefilter_inliers` | merge `XX/XY` retained samples for global tuning | sex-specific prefilter inliers | merged inlier list |
| reference tuning | `tune_wisecondorx_reference_qc` / `scripts/tune_wisecondorx_bin_pca.py` | choose one shared binsize on autosomes | merged inliers + BAMs | tuning summary/best params/inliers |
| shared binsize | `write_common_reference_binsize_from_tuning` | persist the best binsize for downstream reuse | `best_params.yaml` | `common_best_binsize.txt` |
| reference build | `build_wisecondorx_reference_from_tuning_xx` / `build_wisecondorx_reference_from_tuning_xy` / `scripts/build_reference_from_tuning.py` | generate sex-specific final references | tuning outputs + sex-specific sample filters | `XX/XY reference .npz` |
| gender reference build | `build_wisecondorx_gender_reference_from_tuning` | generate mixed-sex reference for `WisecondorX gender` | tuning outputs | `gender reference .npz` |
| predict convert | `wisecondorx_convert_for_cnv` | convert BAM to CNV NPZ | sample BAM | CNV NPZ |
| predict gender | `wisecondorx_gender_for_predict` / `scripts/wisecondorx_gender.py` | infer sample sex before predict | sample NPZ + gender ref | `gender.tsv` |
| predict QC | `wisecondorx_qc_for_predict` / `scripts/cnv_qc.py` | per-sample CNV input QC | CNV NPZ | QC TSV/SVG/pass marker |
| predict | `wisecondorx_predict_cnv` | CNV calling with sex-matched reference | sample NPZ + gender result + sex-specific ref | predict outputs + done marker |
