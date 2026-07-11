REQUESTED_TARGETS = set(PIPELINE_TARGETS)
AVAILABLE_TARGETS = {"mapping", "metadata", "reference"}
if TUNING_ENABLED: AVAILABLE_TARGETS.add("reference_qc")
if CNV_ENABLED: AVAILABLE_TARGETS.update({"cnv_qc", "cnv"})

UNKNOWN_TARGETS = sorted(REQUESTED_TARGETS - AVAILABLE_TARGETS)
if UNKNOWN_TARGETS: raise ValueError(
    "Unsupported pipeline targets: "
    + ",".join(UNKNOWN_TARGETS)
    + f". Available: {','.join(sorted(AVAILABLE_TARGETS))}"
)

ALL_TARGET_FILES = []
REFERENCE_QC_TARGET_FILES = []
if "mapping" in REQUESTED_TARGETS: ALL_TARGET_FILES += expand(SORTED_BAM, sample=SAMPLES) + expand(SORTED_BAI, sample=SAMPLES)
if "metadata" in REQUESTED_TARGETS: ALL_TARGET_FILES.append(RUN_METADATA)
if "reference_qc" in REQUESTED_TARGETS and TUNING_ENABLED: REFERENCE_QC_TARGET_FILES += (
    [
        p
        for sex in REF_SEXES
        for prefilter_dir in [REF_PREFILTER_DIR_BY_SEX[sex]]
        for tuning_dir in [REF_TUNING_DIR_BY_SEX[sex]]
        for p in [
            str(Path(prefilter_dir) / "reference_sample_qc.tsv"),
            str(Path(prefilter_dir) / "reference_sample_qc.svg"),
            str(Path(prefilter_dir) / "reference_inlier_samples.txt"),
            str(Path(prefilter_dir) / "prefilter_summary.yaml"),
            str(Path(tuning_dir) / "bin_pca_grid.tsv"),
            str(Path(tuning_dir) / "best_params.yaml"),
            str(Path(tuning_dir) / "reference_sample_qc.tsv"),
            str(Path(tuning_dir) / "best_bin_pca_elbow.svg"),
            str(Path(tuning_dir) / "reference_qc_metrics.svg"),
            str(Path(tuning_dir) / "reference_inlier_samples.txt"),
        ]
    ] if REF_SEXES else [TUNING_SUMMARY, TUNING_BEST, TUNING_QC, TUNING_PLOT, TUNING_QC_STATS_PLOT, TUNING_INLIERS]
); ALL_TARGET_FILES += REFERENCE_QC_TARGET_FILES
if "reference" in REQUESTED_TARGETS: ALL_TARGET_FILES += REF_TARGET_FILES
if "cnv_qc" in REQUESTED_TARGETS and CNV_ENABLED: ALL_TARGET_FILES += expand(CNV_QC_TSV, sample=SAMPLES) + expand(CNV_QC_PLOT, sample=SAMPLES)
if "cnv" in REQUESTED_TARGETS and CNV_ENABLED: ALL_TARGET_FILES += expand(CNV_DONE, sample=SAMPLES)


rule all:
    input:
        ALL_TARGET_FILES


rule mapping:
    input:
        expand(SORTED_BAM, sample=SAMPLES),
        expand(SORTED_BAI, sample=SAMPLES)


rule reference:
    input:
        REF_TARGET_FILES


rule reference_qc:
    input:
        REFERENCE_QC_TARGET_FILES


rule cnv:
    input:
        expand(CNV_DONE, sample=SAMPLES) if CNV_ENABLED else []


rule collect_run_metadata:
    output:
        RUN_METADATA
    log:
        project_path("logs", "metadata", "collect_run_metadata.log")
    params:
        python_bin=config["biosoft"]["python"],
        fastp=config["biosoft"]["fastp"],
        bwa=config["biosoft"]["bwa"],
        samtools=config["biosoft"]["samtools"],
        wise=config["biosoft"]["WisecondorX"],
        project_root=str(Path.cwd())
    shell:
        r"""
        mkdir -p "$(dirname {output})" "$(dirname {log})"
        {params.python_bin:q} {SCRIPT_COLLECT_RUN_METADATA:q} \
            --output {output:q} \
            --project-root {params.project_root:q} \
            --fastp {params.fastp:q} \
            --bwa {params.bwa:q} \
            --samtools {params.samtools:q} \
            --wisecondorx {params.wise:q} \
            --python-bin {params.python_bin:q} \
            --log {log:q}
        """


rule fastp_bwa:
    input:
        r1=lambda wildcards: config["samples"][wildcards.sample]["R1"],
        r2=lambda wildcards: config["samples"][wildcards.sample]["R2"]
    output:
        clean_r1=FASTP_R1,
        clean_r2=FASTP_R2,
        html=FASTP_HTML,
        json=FASTP_JSON,
        bam=SORTED_BAM,
        bai=SORTED_BAI
    log:
        fastp=project_path("logs", "fastp", "{sample}.log"),
        bwa=project_path("logs", "bwa", "{sample}.log")
    threads: 8
    params:
        fastp=config["biosoft"]["fastp"],
        bwa=config["biosoft"]["bwa"],
        samtools=config["biosoft"]["samtools"],
        reference=config["core"]["reference_genome"]
    shell:
        r"""
        mkdir -p "$(dirname {output.clean_r1})" "$(dirname {output.bam})" "$(dirname {log.fastp})" "$(dirname {log.bwa})"
        (
            echo "=== PIPELINE AUDIT ==="
            echo "git_branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
            echo "git_commit: $(git rev-parse HEAD 2>/dev/null || true)"
            echo "fastp_version: $({params.fastp:q} --version 2>&1 | head -n 1 || true)"
            echo "=== COMMAND ==="
        ) > {log.fastp:q}
        {params.fastp:q} \
            -i {input.r1:q} -I {input.r2:q} \
            -o {output.clean_r1:q} -O {output.clean_r2:q} \
            -h {output.html:q} -j {output.json:q} \
            -w {threads} \
            >> {log.fastp:q} 2>&1
        (
            echo "=== PIPELINE AUDIT ==="
            echo "git_branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
            echo "git_commit: $(git rev-parse HEAD 2>/dev/null || true)"
            echo "bwa_version: $({params.bwa:q} 2>&1 | head -n 1 || true)"
            echo "samtools_version: $({params.samtools:q} --version 2>&1 | head -n 1 || true)"
            echo "=== COMMAND ==="
        ) > {log.bwa:q}
        {params.bwa:q} mem -t {threads} {params.reference:q} {output.clean_r1:q} {output.clean_r2:q} 2>> {log.bwa:q} \
            | {params.samtools:q} sort -@ {threads} -o {output.bam:q}
        {params.samtools:q} index {output.bam:q}
        """


if TUNING_ENABLED:
    pass
    if "XX" in REF_SEXES:
        pass
        rule reference_prefilter_xx:
            input:
                bams=[SORTED_BAM.format(sample=s) for s in REF_SAMPLE_IDS_BY_SEX["XX"]],
                metadata=RUN_METADATA
            output:
                qc=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "reference_sample_qc.tsv"),
                plot=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "reference_sample_qc.svg"),
                inliers=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "reference_inlier_samples.txt"),
                summary=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "prefilter_summary.yaml")
            log:
                project_path("logs", "wisecondorx", "reference_prefilter_XX.log")
            params:
                python_bin=config["biosoft"]["python"],
                wise=config["biosoft"]["WisecondorX"],
                sample_ids=REF_SAMPLE_IDS_BY_SEX["XX"],
                binsize=PREFILTER_BINSIZE,
                pca_min=TUNING_PCA_MIN,
                pca_max=TUNING_PCA_MAX,
                min_ref_samples=TUNING_MIN_REF_SAMPLES,
                min_reads=TUNING_MIN_READS,
                min_corr=TUNING_MIN_CORR,
                max_recon_z=TUNING_MAX_RECON_Z,
                max_noise_z=TUNING_MAX_NOISE_Z,
                max_iter=PREFILTER_MAX_ITER,
                workdir=REF_PREFILTER_DIR_BY_SEX["XX"]
            threads: 4
            shell:
                r"""
                mkdir -p "{params.workdir}" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== SEX GROUP ==="
                    echo "XX"
                    echo "=== COMMAND ==="
                ) > {log:q}
                {params.python_bin:q} {SCRIPT_REFERENCE_PREFILTER_QC:q} \
                    --wisecondorx {params.wise:q} \
                    --bams {input.bams:q} \
                    --sample-ids {params.sample_ids:q} \
                    --binsize {params.binsize} \
                    --pca-min-components {params.pca_min} \
                    --pca-max-components {params.pca_max} \
                    --min-reference-samples {params.min_ref_samples} \
                    --min-reads-per-sample {params.min_reads} \
                    --min-corr-to-median {params.min_corr} \
                    --max-reconstruction-error-z {params.max_recon_z} \
                    --max-noise-mad-z {params.max_noise_z} \
                    --max-iterations {params.max_iter} \
                    --threads {threads} \
                    --workdir {params.workdir:q} \
                    --qc-output {output.qc:q} \
                    --plot-output {output.plot:q} \
                    --inlier-samples-output {output.inliers:q} \
                    --summary-output {output.summary:q} \
                    --log {log:q}
                """

        rule tune_wisecondorx_reference_qc_xx:
            input:
                bams=[SORTED_BAM.format(sample=s) for s in REF_SAMPLE_IDS_BY_SEX["XX"]],
                prefilter_inliers=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "reference_inlier_samples.txt"),
                metadata=RUN_METADATA
            output:
                summary=str(Path(REF_TUNING_DIR_BY_SEX["XX"]) / "bin_pca_grid.tsv"),
                best=str(Path(REF_TUNING_DIR_BY_SEX["XX"]) / "best_params.yaml"),
                qc=str(Path(REF_TUNING_DIR_BY_SEX["XX"]) / "reference_sample_qc.tsv"),
                plot=str(Path(REF_TUNING_DIR_BY_SEX["XX"]) / "best_bin_pca_elbow.svg"),
                qc_plot=str(Path(REF_TUNING_DIR_BY_SEX["XX"]) / "reference_qc_metrics.svg"),
                inliers=str(Path(REF_TUNING_DIR_BY_SEX["XX"]) / "reference_inlier_samples.txt")
            log:
                project_path("logs", "wisecondorx", "tuning_XX.log")
            params:
                python_bin=config["biosoft"]["python"],
                wise=config["biosoft"]["WisecondorX"],
                bin_sizes=",".join(str(item) for item in TUNING_BIN_SIZES),
                sample_ids=REF_SAMPLE_IDS_BY_SEX["XX"],
                pca_min=TUNING_PCA_MIN,
                pca_max=TUNING_PCA_MAX,
                pca_min_var=TUNING_MIN_VAR,
                min_ref_samples=TUNING_MIN_REF_SAMPLES,
                max_outlier_fraction=TUNING_MAX_OUTLIER_FRAC,
                min_reads=TUNING_MIN_READS,
                min_corr=TUNING_MIN_CORR,
                max_recon_z=TUNING_MAX_RECON_Z,
                max_noise_z=TUNING_MAX_NOISE_Z,
                workdir=REF_TUNING_DIR_BY_SEX["XX"],
                reference_output=REF_OUTPUTS_BY_SEX["XX"]
            threads: 4
            shell:
                r"""
                mkdir -p "{params.workdir}" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== SEX GROUP ==="
                    echo "XX"
                    echo "=== COMMAND ==="
                ) > {log:q}
                {params.python_bin:q} {SCRIPT_TUNE_WISECONDORX:q} \
                    --wisecondorx {params.wise:q} \
                    --bams {input.bams:q} \
                    --sample-ids {params.sample_ids:q} \
                    --allowed-samples-file {input.prefilter_inliers:q} \
                    --bin-sizes {params.bin_sizes} \
                    --pca-min-components {params.pca_min} \
                    --pca-max-components {params.pca_max} \
                    --pca-min-explained-variance {params.pca_min_var} \
                    --min-reference-samples {params.min_ref_samples} \
                    --max-outlier-fraction {params.max_outlier_fraction} \
                    --min-reads-per-sample {params.min_reads} \
                    --min-corr-to-median {params.min_corr} \
                    --max-reconstruction-error-z {params.max_recon_z} \
                    --max-noise-mad-z {params.max_noise_z} \
                    --threads {threads} \
                    --workdir {params.workdir:q} \
                    --summary-output {output.summary:q} \
                    --best-output {output.best:q} \
                    --qc-output {output.qc:q} \
                    --plot-output {output.plot:q} \
                    --qc-stats-plot-output {output.qc_plot:q} \
                    --inlier-samples-output {output.inliers:q} \
                    --reference-output {params.reference_output:q} \
                    --skip-build-reference \
                    --log {log:q}
                """

        rule build_wisecondorx_reference_from_tuning_xx:
            input:
                best=str(Path(REF_TUNING_DIR_BY_SEX["XX"]) / "best_params.yaml"),
                inliers=str(Path(REF_TUNING_DIR_BY_SEX["XX"]) / "reference_inlier_samples.txt"),
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUTS_BY_SEX["XX"]
            log:
                project_path("logs", "wisecondorx", "build_reference_XX.log")
            params:
                python_bin=config["biosoft"]["python"],
                wise=config["biosoft"]["WisecondorX"],
                workdir=REF_TUNING_DIR_BY_SEX["XX"],
                allowed_samples=",".join(REF_SAMPLE_IDS_BY_SEX["XX"])
            threads: 4
            shell:
                r"""
                mkdir -p "$(dirname {output.ref})" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== SEX GROUP ==="
                    echo "XX"
                    echo "=== COMMAND ==="
                ) > {log:q}
                {params.python_bin:q} {SCRIPT_BUILD_REF_FROM_TUNING:q} \
                    --wisecondorx {params.wise:q} \
                    --best-yaml {input.best:q} \
                    --inlier-samples {input.inliers:q} \
                    --allowed-samples {params.allowed_samples:q} \
                    --tuning-workdir {params.workdir:q} \
                    --reference-output {output.ref:q} \
                    --threads {threads} \
                    --log {log:q}
                """

    if "XY" in REF_SEXES:
        pass
        rule reference_prefilter_xy:
            input:
                bams=[SORTED_BAM.format(sample=s) for s in REF_SAMPLE_IDS_BY_SEX["XY"]],
                metadata=RUN_METADATA
            output:
                qc=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "reference_sample_qc.tsv"),
                plot=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "reference_sample_qc.svg"),
                inliers=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "reference_inlier_samples.txt"),
                summary=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "prefilter_summary.yaml")
            log:
                project_path("logs", "wisecondorx", "reference_prefilter_XY.log")
            params:
                python_bin=config["biosoft"]["python"],
                wise=config["biosoft"]["WisecondorX"],
                sample_ids=REF_SAMPLE_IDS_BY_SEX["XY"],
                binsize=PREFILTER_BINSIZE,
                pca_min=TUNING_PCA_MIN,
                pca_max=TUNING_PCA_MAX,
                min_ref_samples=TUNING_MIN_REF_SAMPLES,
                min_reads=TUNING_MIN_READS,
                min_corr=TUNING_MIN_CORR,
                max_recon_z=TUNING_MAX_RECON_Z,
                max_noise_z=TUNING_MAX_NOISE_Z,
                max_iter=PREFILTER_MAX_ITER,
                workdir=REF_PREFILTER_DIR_BY_SEX["XY"]
            threads: 4
            shell:
                r"""
                mkdir -p "{params.workdir}" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== SEX GROUP ==="
                    echo "XY"
                    echo "=== COMMAND ==="
                ) > {log:q}
                {params.python_bin:q} {SCRIPT_REFERENCE_PREFILTER_QC:q} \
                    --wisecondorx {params.wise:q} \
                    --bams {input.bams:q} \
                    --sample-ids {params.sample_ids:q} \
                    --binsize {params.binsize} \
                    --pca-min-components {params.pca_min} \
                    --pca-max-components {params.pca_max} \
                    --min-reference-samples {params.min_ref_samples} \
                    --min-reads-per-sample {params.min_reads} \
                    --min-corr-to-median {params.min_corr} \
                    --max-reconstruction-error-z {params.max_recon_z} \
                    --max-noise-mad-z {params.max_noise_z} \
                    --max-iterations {params.max_iter} \
                    --threads {threads} \
                    --workdir {params.workdir:q} \
                    --qc-output {output.qc:q} \
                    --plot-output {output.plot:q} \
                    --inlier-samples-output {output.inliers:q} \
                    --summary-output {output.summary:q} \
                    --log {log:q}
                """

        rule tune_wisecondorx_reference_qc_xy:
            input:
                bams=[SORTED_BAM.format(sample=s) for s in REF_SAMPLE_IDS_BY_SEX["XY"]],
                prefilter_inliers=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "reference_inlier_samples.txt"),
                metadata=RUN_METADATA
            output:
                summary=str(Path(REF_TUNING_DIR_BY_SEX["XY"]) / "bin_pca_grid.tsv"),
                best=str(Path(REF_TUNING_DIR_BY_SEX["XY"]) / "best_params.yaml"),
                qc=str(Path(REF_TUNING_DIR_BY_SEX["XY"]) / "reference_sample_qc.tsv"),
                plot=str(Path(REF_TUNING_DIR_BY_SEX["XY"]) / "best_bin_pca_elbow.svg"),
                qc_plot=str(Path(REF_TUNING_DIR_BY_SEX["XY"]) / "reference_qc_metrics.svg"),
                inliers=str(Path(REF_TUNING_DIR_BY_SEX["XY"]) / "reference_inlier_samples.txt")
            log:
                project_path("logs", "wisecondorx", "tuning_XY.log")
            params:
                python_bin=config["biosoft"]["python"],
                wise=config["biosoft"]["WisecondorX"],
                bin_sizes=",".join(str(item) for item in TUNING_BIN_SIZES),
                sample_ids=REF_SAMPLE_IDS_BY_SEX["XY"],
                pca_min=TUNING_PCA_MIN,
                pca_max=TUNING_PCA_MAX,
                pca_min_var=TUNING_MIN_VAR,
                min_ref_samples=TUNING_MIN_REF_SAMPLES,
                max_outlier_fraction=TUNING_MAX_OUTLIER_FRAC,
                min_reads=TUNING_MIN_READS,
                min_corr=TUNING_MIN_CORR,
                max_recon_z=TUNING_MAX_RECON_Z,
                max_noise_z=TUNING_MAX_NOISE_Z,
                workdir=REF_TUNING_DIR_BY_SEX["XY"],
                reference_output=REF_OUTPUTS_BY_SEX["XY"]
            threads: 4
            shell:
                r"""
                mkdir -p "{params.workdir}" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== SEX GROUP ==="
                    echo "XY"
                    echo "=== COMMAND ==="
                ) > {log:q}
                {params.python_bin:q} {SCRIPT_TUNE_WISECONDORX:q} \
                    --wisecondorx {params.wise:q} \
                    --bams {input.bams:q} \
                    --sample-ids {params.sample_ids:q} \
                    --allowed-samples-file {input.prefilter_inliers:q} \
                    --bin-sizes {params.bin_sizes} \
                    --pca-min-components {params.pca_min} \
                    --pca-max-components {params.pca_max} \
                    --pca-min-explained-variance {params.pca_min_var} \
                    --min-reference-samples {params.min_ref_samples} \
                    --max-outlier-fraction {params.max_outlier_fraction} \
                    --min-reads-per-sample {params.min_reads} \
                    --min-corr-to-median {params.min_corr} \
                    --max-reconstruction-error-z {params.max_recon_z} \
                    --max-noise-mad-z {params.max_noise_z} \
                    --threads {threads} \
                    --workdir {params.workdir:q} \
                    --summary-output {output.summary:q} \
                    --best-output {output.best:q} \
                    --qc-output {output.qc:q} \
                    --plot-output {output.plot:q} \
                    --qc-stats-plot-output {output.qc_plot:q} \
                    --inlier-samples-output {output.inliers:q} \
                    --reference-output {params.reference_output:q} \
                    --skip-build-reference \
                    --log {log:q}
                """

        rule build_wisecondorx_reference_from_tuning_xy:
            input:
                best=str(Path(REF_TUNING_DIR_BY_SEX["XY"]) / "best_params.yaml"),
                inliers=str(Path(REF_TUNING_DIR_BY_SEX["XY"]) / "reference_inlier_samples.txt"),
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUTS_BY_SEX["XY"]
            log:
                project_path("logs", "wisecondorx", "build_reference_XY.log")
            params:
                python_bin=config["biosoft"]["python"],
                wise=config["biosoft"]["WisecondorX"],
                workdir=REF_TUNING_DIR_BY_SEX["XY"],
                allowed_samples=",".join(REF_SAMPLE_IDS_BY_SEX["XY"])
            threads: 4
            shell:
                r"""
                mkdir -p "$(dirname {output.ref})" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== SEX GROUP ==="
                    echo "XY"
                    echo "=== COMMAND ==="
                ) > {log:q}
                {params.python_bin:q} {SCRIPT_BUILD_REF_FROM_TUNING:q} \
                    --wisecondorx {params.wise:q} \
                    --best-yaml {input.best:q} \
                    --inlier-samples {input.inliers:q} \
                    --allowed-samples {params.allowed_samples:q} \
                    --tuning-workdir {params.workdir:q} \
                    --reference-output {output.ref:q} \
                    --threads {threads} \
                    --log {log:q}
                """

    if not REF_SEXES:
        pass
        rule tune_wisecondorx_reference_qc:
            input:
                bams=expand(SORTED_BAM, sample=SAMPLES),
                metadata=RUN_METADATA
            output:
                summary=TUNING_SUMMARY,
                best=TUNING_BEST,
                qc=TUNING_QC,
                plot=TUNING_PLOT,
                qc_plot=TUNING_QC_STATS_PLOT,
                inliers=TUNING_INLIERS
            log:
                project_path("logs", "wisecondorx", "tuning.log")
            params:
                python_bin=config["biosoft"]["python"],
                wise=config["biosoft"]["WisecondorX"],
                bin_sizes=",".join(str(item) for item in TUNING_BIN_SIZES),
                sample_ids=SAMPLES,
                pca_min=TUNING_PCA_MIN,
                pca_max=TUNING_PCA_MAX,
                pca_min_var=TUNING_MIN_VAR,
                min_ref_samples=TUNING_MIN_REF_SAMPLES,
                max_outlier_fraction=TUNING_MAX_OUTLIER_FRAC,
                min_reads=TUNING_MIN_READS,
                min_corr=TUNING_MIN_CORR,
                max_recon_z=TUNING_MAX_RECON_Z,
                max_noise_z=TUNING_MAX_NOISE_Z,
                workdir=TUNING_WORKDIR,
                reference_output=REF_OUTPUT
            threads: 4
            shell:
                r"""
                mkdir -p "$(dirname {output.summary})" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== COMMAND ==="
                ) > {log:q}
                {params.python_bin:q} {SCRIPT_TUNE_WISECONDORX:q} \
                    --wisecondorx {params.wise:q} \
                    --bams {input.bams:q} \
                    --sample-ids {params.sample_ids:q} \
                    --bin-sizes {params.bin_sizes} \
                    --pca-min-components {params.pca_min} \
                    --pca-max-components {params.pca_max} \
                    --pca-min-explained-variance {params.pca_min_var} \
                    --min-reference-samples {params.min_ref_samples} \
                    --max-outlier-fraction {params.max_outlier_fraction} \
                    --min-reads-per-sample {params.min_reads} \
                    --min-corr-to-median {params.min_corr} \
                    --max-reconstruction-error-z {params.max_recon_z} \
                    --max-noise-mad-z {params.max_noise_z} \
                    --threads {threads} \
                    --workdir {params.workdir:q} \
                    --summary-output {output.summary:q} \
                    --best-output {output.best:q} \
                    --qc-output {output.qc:q} \
                    --plot-output {output.plot:q} \
                    --qc-stats-plot-output {output.qc_plot:q} \
                    --inlier-samples-output {output.inliers:q} \
                    --reference-output {params.reference_output:q} \
                    --skip-build-reference \
                    --log {log:q}
                """

        rule build_wisecondorx_reference_from_tuning:
            input:
                best=TUNING_BEST,
                inliers=TUNING_INLIERS,
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUT
            log:
                project_path("logs", "wisecondorx", "build_reference.log")
            params:
                python_bin=config["biosoft"]["python"],
                wise=config["biosoft"]["WisecondorX"],
                workdir=TUNING_WORKDIR
            threads: 4
            shell:
                r"""
                mkdir -p "$(dirname {output.ref})" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== COMMAND ==="
                ) > {log:q}
                {params.python_bin:q} {SCRIPT_BUILD_REF_FROM_TUNING:q} \
                    --wisecondorx {params.wise:q} \
                    --best-yaml {input.best:q} \
                    --inlier-samples {input.inliers:q} \
                    --tuning-workdir {params.workdir:q} \
                    --reference-output {output.ref:q} \
                    --threads {threads} \
                    --log {log:q}
                """
else:
    pass
    if "XX" in REF_SEXES:
        pass
        rule build_wisecondorx_reference_fixed_xx:
            input:
                bams=[SORTED_BAM.format(sample=s) for s in REF_SAMPLE_IDS_BY_SEX["XX"]],
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUTS_BY_SEX["XX"]
            log:
                project_path("logs", "wisecondorx", "build_reference_XX.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=WISE_CFG["binsize"],
                converted_dir=project_path("wisecondorx", "converted", "XX")
            threads: 4
            shell:
                r"""
                mkdir -p "{params.converted_dir}" "$(dirname {output.ref})" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== SEX GROUP ==="
                    echo "XX"
                    echo "=== COMMAND ==="
                ) > {log:q}
                for bam in {input.bams:q}; do
                    sample=$(basename "$bam" .sorted.bam)
                    npz="{params.converted_dir}/${{sample}}.npz"
                    {params.wise:q} convert "$bam" "$npz" --binsize {params.binsize} >> {log:q} 2>&1
                done
                {params.wise:q} newref {params.converted_dir:q}/*.npz {output.ref:q} --binsize {params.binsize} --cpus {threads} >> {log:q} 2>&1
                """

    if "XY" in REF_SEXES:
        pass
        rule build_wisecondorx_reference_fixed_xy:
            input:
                bams=[SORTED_BAM.format(sample=s) for s in REF_SAMPLE_IDS_BY_SEX["XY"]],
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUTS_BY_SEX["XY"]
            log:
                project_path("logs", "wisecondorx", "build_reference_XY.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=WISE_CFG["binsize"],
                converted_dir=project_path("wisecondorx", "converted", "XY")
            threads: 4
            shell:
                r"""
                mkdir -p "{params.converted_dir}" "$(dirname {output.ref})" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== SEX GROUP ==="
                    echo "XY"
                    echo "=== COMMAND ==="
                ) > {log:q}
                for bam in {input.bams:q}; do
                    sample=$(basename "$bam" .sorted.bam)
                    npz="{params.converted_dir}/${{sample}}.npz"
                    {params.wise:q} convert "$bam" "$npz" --binsize {params.binsize} >> {log:q} 2>&1
                done
                {params.wise:q} newref {params.converted_dir:q}/*.npz {output.ref:q} --binsize {params.binsize} --cpus {threads} >> {log:q} 2>&1
                """
    if not REF_SEXES:
        pass
        rule build_wisecondorx_reference_fixed:
            input:
                bams=expand(SORTED_BAM, sample=SAMPLES),
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUT
            log:
                project_path("logs", "wisecondorx", "build_reference.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=WISE_CFG["binsize"],
                converted_dir=project_path("wisecondorx", "converted")
            threads: 4
            shell:
                r"""
                mkdir -p "{params.converted_dir}" "$(dirname {output.ref})" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== COMMAND ==="
                ) > {log:q}
                for bam in {input.bams:q}; do
                    sample=$(basename "$bam" .sorted.bam)
                    npz="{params.converted_dir}/${{sample}}.npz"
                    {params.wise:q} convert "$bam" "$npz" --binsize {params.binsize} >> {log:q} 2>&1
                done
                {params.wise:q} newref {params.converted_dir:q}/*.npz {output.ref:q} --binsize {params.binsize} --cpus {threads} >> {log:q} 2>&1
                """


if CNV_ENABLED:
    pass
    rule wisecondorx_convert_for_cnv:
        input:
            bam=SORTED_BAM,
            metadata=RUN_METADATA
        output:
            npz=CNV_NPZ
        log:
            project_path("logs", "cnv", "{sample}.convert.log")
        params:
            wise=config["biosoft"]["WisecondorX"],
            binsize=CNV_CONVERT_BINSIZE
        threads: 4
        shell:
            r"""
            mkdir -p "$(dirname {output.npz})" "$(dirname {log})"
            (
                echo "=== PIPELINE AUDIT ==="
                cat {input.metadata:q}
                echo "=== COMMAND ==="
            ) > {log:q}
            {params.wise:q} convert {input.bam:q} {output.npz:q} --binsize {params.binsize} >> {log:q} 2>&1
            """

    rule wisecondorx_qc_for_predict:
        input:
            npz=CNV_NPZ,
            metadata=RUN_METADATA
        output:
            tsv=CNV_QC_TSV,
            plot=CNV_QC_PLOT,
            passed=CNV_QC_PASS
        log:
            project_path("logs", "cnv", "{sample}.qc.log")
        params:
            python_bin=config["biosoft"]["python"],
            min_total=CNV_QC_MIN_TOTAL,
            min_nonzero=CNV_QC_MIN_NONZERO,
            max_mad=CNV_QC_MAX_MAD
        threads: 1
        shell:
            r"""
            mkdir -p "$(dirname {output.tsv})" "$(dirname {log})"
            (
                echo "=== PIPELINE AUDIT ==="
                cat {input.metadata:q}
                echo "=== COMMAND ==="
            ) > {log:q}
            {params.python_bin:q} {SCRIPT_CNV_QC:q} \
                --sample-id {wildcards.sample:q} \
                --npz {input.npz:q} \
                --output-tsv {output.tsv:q} \
                --output-plot {output.plot:q} \
                --pass-marker {output.passed:q} \
                --min-total-counts {params.min_total} \
                --min-nonzero-fraction {params.min_nonzero} \
                --max-mad-log1p {params.max_mad} \
                --log {log:q} \
                >> {log:q} 2>&1
            """

    rule wisecondorx_predict_cnv:
        input:
            npz=CNV_NPZ,
            ref=REF_OUTPUT,
            qc_report=CNV_QC_TSV,
            qc_pass=CNV_QC_PASS,
            metadata=RUN_METADATA
        output:
            done=CNV_DONE
        log:
            project_path("logs", "cnv", "{sample}.predict.log")
        params:
            wise=config["biosoft"]["WisecondorX"],
            zscore=CNV_ZSCORE,
            alpha=CNV_ALPHA,
            maskrepeats=CNV_MASKREPEATS,
            minrefbins=CNV_MINREFBINS,
            output_prefix=lambda wildcards: str(Path(CNV_PREDICT_DIR) / wildcards.sample)
        threads: 2
        shell:
            r"""
            mkdir -p "$(dirname {output.done})" "$(dirname {log})"
            (
                echo "=== PIPELINE AUDIT ==="
                cat {input.metadata:q}
                echo "=== QC REPORT ==="
                cat {input.qc_report:q}
                echo "=== COMMAND ==="
            ) > {log:q}
            {params.wise:q} predict {input.npz:q} {input.ref:q} {params.output_prefix:q} \
                --zscore {params.zscore} \
                --alpha {params.alpha} \
                --maskrepeats {params.maskrepeats} \
                --minrefbins {params.minrefbins} \
                --cpus {threads} >> {log:q} 2>&1
            touch {output.done:q}
            """
