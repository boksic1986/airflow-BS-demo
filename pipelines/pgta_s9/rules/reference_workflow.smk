REFERENCE_BAMS = [SORTED_BAM.format(sample=sample_id) for sample_id in REF_SAMPLE_IDS]
REFERENCE_SAMPLE_TEXT = "\n".join(REF_SAMPLE_IDS)


if TUNING_ENABLED:
    if BUILD_REF_BY_SEX_ENABLED:
        rule reference_prefilter_xx:
            input:
                bams=[SORTED_BAM.format(sample=sample_id) for sample_id in REF_SAMPLE_IDS_BY_SEX["XX"]],
                metadata=RUN_METADATA
            output:
                qc=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "reference_sample_qc.tsv"),
                plot=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "reference_sample_qc.svg"),
                inliers=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "reference_inlier_samples.txt"),
                summary=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "prefilter_summary.yaml")
            log:
                project_path("logs", "wisecondorx", "reference_prefilter_XX.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=PREFILTER_BINSIZE,
                pca_min=TUNING_PCA_MIN,
                pca_max=TUNING_PCA_MAX,
                min_ref_samples=TUNING_MIN_REF_SAMPLES,
                min_reads=TUNING_MIN_READS,
                min_corr=TUNING_MIN_CORR,
                max_recon_z=TUNING_MAX_RECON_Z,
                max_noise_z=TUNING_MAX_NOISE_Z,
                max_iter=PREFILTER_MAX_ITER,
                workdir=REF_PREFILTER_DIR_BY_SEX["XX"],
                sample_ids=REF_SAMPLE_IDS_BY_SEX["XX"],
                sample_text="\n".join(REF_SAMPLE_IDS_BY_SEX["XX"])
            threads: 4
            run:
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.reference_prefilter_qc import run_reference_prefilter_qc

                write_rule_audit_log(log[0], input.metadata, [("SEX GROUP", "XX"), ("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("reference_prefilter_qc", log[0])
                run_reference_prefilter_qc(
                    wisecondorx=params.wise,
                    bams=input.bams,
                    sample_ids=params.sample_ids,
                    binsize=params.binsize,
                    pca_min_components=params.pca_min,
                    pca_max_components=params.pca_max,
                    min_reference_samples=params.min_ref_samples,
                    min_reads_per_sample=params.min_reads,
                    min_corr_to_median=params.min_corr,
                    max_reconstruction_error_z=params.max_recon_z,
                    max_noise_mad_z=params.max_noise_z,
                    max_iterations=params.max_iter,
                    threads=threads,
                    workdir=params.workdir,
                    qc_output=output.qc,
                    plot_output=output.plot,
                    inlier_samples_output=output.inliers,
                    summary_output=output.summary,
                    logger=logger,
                )

        rule reference_prefilter_xy:
            input:
                bams=[SORTED_BAM.format(sample=sample_id) for sample_id in REF_SAMPLE_IDS_BY_SEX["XY"]],
                metadata=RUN_METADATA
            output:
                qc=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "reference_sample_qc.tsv"),
                plot=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "reference_sample_qc.svg"),
                inliers=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "reference_inlier_samples.txt"),
                summary=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "prefilter_summary.yaml")
            log:
                project_path("logs", "wisecondorx", "reference_prefilter_XY.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=PREFILTER_BINSIZE,
                pca_min=TUNING_PCA_MIN,
                pca_max=TUNING_PCA_MAX,
                min_ref_samples=TUNING_MIN_REF_SAMPLES,
                min_reads=TUNING_MIN_READS,
                min_corr=TUNING_MIN_CORR,
                max_recon_z=TUNING_MAX_RECON_Z,
                max_noise_z=TUNING_MAX_NOISE_Z,
                max_iter=PREFILTER_MAX_ITER,
                workdir=REF_PREFILTER_DIR_BY_SEX["XY"],
                sample_ids=REF_SAMPLE_IDS_BY_SEX["XY"],
                sample_text="\n".join(REF_SAMPLE_IDS_BY_SEX["XY"])
            threads: 4
            run:
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.reference_prefilter_qc import run_reference_prefilter_qc

                write_rule_audit_log(log[0], input.metadata, [("SEX GROUP", "XY"), ("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("reference_prefilter_qc", log[0])
                run_reference_prefilter_qc(
                    wisecondorx=params.wise,
                    bams=input.bams,
                    sample_ids=params.sample_ids,
                    binsize=params.binsize,
                    pca_min_components=params.pca_min,
                    pca_max_components=params.pca_max,
                    min_reference_samples=params.min_ref_samples,
                    min_reads_per_sample=params.min_reads,
                    min_corr_to_median=params.min_corr,
                    max_reconstruction_error_z=params.max_recon_z,
                    max_noise_mad_z=params.max_noise_z,
                    max_iterations=params.max_iter,
                    threads=threads,
                    workdir=params.workdir,
                    qc_output=output.qc,
                    plot_output=output.plot,
                    inlier_samples_output=output.inliers,
                    summary_output=output.summary,
                    logger=logger,
                )

        rule merge_reference_prefilter_inliers:
            input:
                xx_inliers=str(Path(REF_PREFILTER_DIR_BY_SEX["XX"]) / "reference_inlier_samples.txt"),
                xy_inliers=str(Path(REF_PREFILTER_DIR_BY_SEX["XY"]) / "reference_inlier_samples.txt"),
                metadata=RUN_METADATA
            output:
                inliers=REF_PREFILTER_MERGED_INLIERS
            log:
                project_path("logs", "wisecondorx", "reference_prefilter_merge.log")
            threads: 1
            run:
                from pathlib import Path

                from scripts.pipeline_logging import setup_logger, write_rule_audit_log

                write_rule_audit_log(log[0], input.metadata, [("REFERENCE SAMPLES", REFERENCE_SAMPLE_TEXT)])
                logger = setup_logger("merge_reference_prefilter_inliers", log[0])
                merged = []
                for source in [input.xx_inliers, input.xy_inliers]:
                    merged.extend(
                        line.strip()
                        for line in Path(source).read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    )
                merged = sorted(dict.fromkeys(merged))
                output_path = Path(output.inliers)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("".join(f"{sample_id}\n" for sample_id in merged), encoding="utf-8")
                logger.info("merged prefilter inliers: %d samples", len(merged))

        rule tune_wisecondorx_reference_qc:
            input:
                bams=REFERENCE_BAMS,
                prefilter_inliers=REF_PREFILTER_MERGED_INLIERS,
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
                wise=config["biosoft"]["WisecondorX"],
                bin_sizes=",".join(str(item) for item in TUNING_BIN_SIZES),
                sample_ids=REF_SAMPLE_IDS,
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
                reference_output=GENDER_REF_OUTPUT,
                sample_text=REFERENCE_SAMPLE_TEXT
            threads: 4
            run:
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.tune_wisecondorx_bin_pca import run_tune_wisecondorx

                write_rule_audit_log(log[0], input.metadata, [("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("tune_wisecondorx_bin_pca", log[0])
                run_tune_wisecondorx(
                    wisecondorx=params.wise,
                    bams=input.bams,
                    sample_ids=params.sample_ids,
                    allowed_samples_file=input.prefilter_inliers,
                    bin_sizes=params.bin_sizes,
                    pca_min_components=params.pca_min,
                    pca_max_components=params.pca_max,
                    pca_min_explained_variance=params.pca_min_var,
                    min_reference_samples=params.min_ref_samples,
                    max_outlier_fraction=params.max_outlier_fraction,
                    min_reads_per_sample=params.min_reads,
                    min_corr_to_median=params.min_corr,
                    max_reconstruction_error_z=params.max_recon_z,
                    max_noise_mad_z=params.max_noise_z,
                    threads=threads,
                    workdir=params.workdir,
                    summary_output=output.summary,
                    best_output=output.best,
                    qc_output=output.qc,
                    plot_output=output.plot,
                    qc_stats_plot_output=output.qc_plot,
                    inlier_samples_output=output.inliers,
                    reference_output=params.reference_output,
                    skip_build_reference=True,
                    logger=logger,
                )

        rule write_common_reference_binsize_from_tuning:
            input:
                best=TUNING_BEST,
                metadata=RUN_METADATA
            output:
                binsize=COMMON_REF_BINSIZE
            log:
                project_path("logs", "wisecondorx", "reference_common_binsize.log")
            threads: 1
            run:
                from pathlib import Path

                from scripts.build_reference_from_tuning import load_best_binsize
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log

                write_rule_audit_log(log[0], input.metadata)
                logger = setup_logger("write_common_reference_binsize_from_tuning", log[0])
                best_binsize = load_best_binsize(input.best)
                output_path = Path(output.binsize)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(f"{best_binsize}\n", encoding="utf-8")
                logger.info("common reference binsize written: %s -> %s", output.binsize, best_binsize)

        rule build_wisecondorx_reference_from_tuning_xx:
            input:
                best=TUNING_BEST,
                inliers=TUNING_INLIERS,
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUTS_BY_SEX["XX"]
            log:
                project_path("logs", "wisecondorx", "build_reference_XX.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                workdir=TUNING_WORKDIR,
                allowed_samples=",".join(REF_SAMPLE_IDS_BY_SEX["XX"]),
                sample_text="\n".join(REF_SAMPLE_IDS_BY_SEX["XX"])
            threads: 4
            run:
                from scripts.build_reference_from_tuning import build_reference_from_tuning
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log

                write_rule_audit_log(log[0], input.metadata, [("SEX GROUP", "XX"), ("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("build_reference_from_tuning", log[0])
                build_reference_from_tuning(
                    wisecondorx=params.wise,
                    best_yaml=input.best,
                    inlier_samples=input.inliers,
                    allowed_samples=params.allowed_samples,
                    tuning_workdir=params.workdir,
                    reference_output=output.ref,
                    threads=threads,
                    logger=logger,
                )

        rule build_wisecondorx_reference_from_tuning_xy:
            input:
                best=TUNING_BEST,
                inliers=TUNING_INLIERS,
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUTS_BY_SEX["XY"]
            log:
                project_path("logs", "wisecondorx", "build_reference_XY.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                workdir=TUNING_WORKDIR,
                allowed_samples=",".join(REF_SAMPLE_IDS_BY_SEX["XY"]),
                sample_text="\n".join(REF_SAMPLE_IDS_BY_SEX["XY"])
            threads: 4
            run:
                from scripts.build_reference_from_tuning import build_reference_from_tuning
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log

                write_rule_audit_log(log[0], input.metadata, [("SEX GROUP", "XY"), ("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("build_reference_from_tuning", log[0])
                build_reference_from_tuning(
                    wisecondorx=params.wise,
                    best_yaml=input.best,
                    inlier_samples=input.inliers,
                    allowed_samples=params.allowed_samples,
                    tuning_workdir=params.workdir,
                    reference_output=output.ref,
                    threads=threads,
                    logger=logger,
                )

        rule build_wisecondorx_gender_reference_from_tuning:
            input:
                best=TUNING_BEST,
                inliers=TUNING_INLIERS,
                common_binsize=COMMON_REF_BINSIZE,
                metadata=RUN_METADATA
            output:
                ref=GENDER_REF_OUTPUT
            log:
                project_path("logs", "wisecondorx", "build_reference_gender.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                sample_text=REFERENCE_SAMPLE_TEXT
            threads: 4
            run:
                from pathlib import Path

                from scripts.build_reference_from_tuning import (
                    build_reference_from_npz_paths,
                    resolve_inlier_npz_paths,
                )
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log

                write_rule_audit_log(log[0], input.metadata, [("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("build_gender_reference_from_tuning", log[0])
                expected_binsize = int(Path(input.common_binsize).read_text(encoding="utf-8").strip())
                best_binsize, inlier_ids, npz_paths = resolve_inlier_npz_paths(
                    best_yaml=input.best,
                    inlier_samples=input.inliers,
                    tuning_workdir=TUNING_WORKDIR,
                )
                if best_binsize != expected_binsize:
                    raise ValueError(f"Common binsize mismatch: expected={expected_binsize}, best={best_binsize}")
                logger.info("building gender reference from inlier samples=%d", len(inlier_ids))
                build_reference_from_npz_paths(
                    wisecondorx=params.wise,
                    npz_paths=npz_paths,
                    reference_output=output.ref,
                    binsize=expected_binsize,
                    threads=threads,
                    logger=logger,
                )

    else:
        rule reference_prefilter:
            input:
                bams=REFERENCE_BAMS,
                metadata=RUN_METADATA
            output:
                qc=str(Path(REF_PREFILTER_DIR) / "reference_sample_qc.tsv"),
                plot=str(Path(REF_PREFILTER_DIR) / "reference_sample_qc.svg"),
                inliers=str(Path(REF_PREFILTER_DIR) / "reference_inlier_samples.txt"),
                summary=str(Path(REF_PREFILTER_DIR) / "prefilter_summary.yaml")
            log:
                project_path("logs", "wisecondorx", "reference_prefilter.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=PREFILTER_BINSIZE,
                pca_min=TUNING_PCA_MIN,
                pca_max=TUNING_PCA_MAX,
                min_ref_samples=TUNING_MIN_REF_SAMPLES,
                min_reads=TUNING_MIN_READS,
                min_corr=TUNING_MIN_CORR,
                max_recon_z=TUNING_MAX_RECON_Z,
                max_noise_z=TUNING_MAX_NOISE_Z,
                max_iter=PREFILTER_MAX_ITER,
                workdir=REF_PREFILTER_DIR,
                sample_ids=REF_SAMPLE_IDS,
                sample_text=REFERENCE_SAMPLE_TEXT
            threads: 4
            run:
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.reference_prefilter_qc import run_reference_prefilter_qc

                write_rule_audit_log(log[0], input.metadata, [("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("reference_prefilter_qc", log[0])
                run_reference_prefilter_qc(
                    wisecondorx=params.wise,
                    bams=input.bams,
                    sample_ids=params.sample_ids,
                    binsize=params.binsize,
                    pca_min_components=params.pca_min,
                    pca_max_components=params.pca_max,
                    min_reference_samples=params.min_ref_samples,
                    min_reads_per_sample=params.min_reads,
                    min_corr_to_median=params.min_corr,
                    max_reconstruction_error_z=params.max_recon_z,
                    max_noise_mad_z=params.max_noise_z,
                    max_iterations=params.max_iter,
                    threads=threads,
                    workdir=params.workdir,
                    qc_output=output.qc,
                    plot_output=output.plot,
                    inlier_samples_output=output.inliers,
                    summary_output=output.summary,
                    logger=logger,
                )

        rule tune_wisecondorx_reference_qc:
            input:
                bams=REFERENCE_BAMS,
                prefilter_inliers=str(Path(REF_PREFILTER_DIR) / "reference_inlier_samples.txt"),
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
                wise=config["biosoft"]["WisecondorX"],
                bin_sizes=",".join(str(item) for item in TUNING_BIN_SIZES),
                sample_ids=REF_SAMPLE_IDS,
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
                reference_output=REF_OUTPUT,
                sample_text=REFERENCE_SAMPLE_TEXT
            threads: 4
            run:
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.tune_wisecondorx_bin_pca import run_tune_wisecondorx

                write_rule_audit_log(log[0], input.metadata, [("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("tune_wisecondorx_bin_pca", log[0])
                run_tune_wisecondorx(
                    wisecondorx=params.wise,
                    bams=input.bams,
                    sample_ids=params.sample_ids,
                    allowed_samples_file=input.prefilter_inliers,
                    bin_sizes=params.bin_sizes,
                    pca_min_components=params.pca_min,
                    pca_max_components=params.pca_max,
                    pca_min_explained_variance=params.pca_min_var,
                    min_reference_samples=params.min_ref_samples,
                    max_outlier_fraction=params.max_outlier_fraction,
                    min_reads_per_sample=params.min_reads,
                    min_corr_to_median=params.min_corr,
                    max_reconstruction_error_z=params.max_recon_z,
                    max_noise_mad_z=params.max_noise_z,
                    threads=threads,
                    workdir=params.workdir,
                    summary_output=output.summary,
                    best_output=output.best,
                    qc_output=output.qc,
                    plot_output=output.plot,
                    qc_stats_plot_output=output.qc_plot,
                    inlier_samples_output=output.inliers,
                    reference_output=params.reference_output,
                    skip_build_reference=True,
                    logger=logger,
                )

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
                wise=config["biosoft"]["WisecondorX"],
                workdir=TUNING_WORKDIR,
                allowed_samples=",".join(REF_SAMPLE_IDS),
                sample_text=REFERENCE_SAMPLE_TEXT
            threads: 4
            run:
                from scripts.build_reference_from_tuning import build_reference_from_tuning
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log

                write_rule_audit_log(log[0], input.metadata, [("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("build_reference_from_tuning", log[0])
                build_reference_from_tuning(
                    wisecondorx=params.wise,
                    best_yaml=input.best,
                    inlier_samples=input.inliers,
                    allowed_samples=params.allowed_samples,
                    tuning_workdir=params.workdir,
                    reference_output=output.ref,
                    threads=threads,
                    logger=logger,
                )
else:
    if BUILD_REF_BY_SEX_ENABLED:
        rule write_reference_common_binsize_fixed:
            input:
                metadata=RUN_METADATA
            output:
                binsize=COMMON_REF_BINSIZE
            log:
                project_path("logs", "wisecondorx", "reference_common_binsize.log")
            params:
                binsize=WISE_CFG["binsize"]
            threads: 1
            run:
                from pathlib import Path

                from scripts.pipeline_logging import setup_logger, write_rule_audit_log

                write_rule_audit_log(log[0], input.metadata)
                logger = setup_logger("write_reference_common_binsize_fixed", log[0])
                output_path = Path(output.binsize)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(f"{int(params.binsize)}\n", encoding="utf-8")
                logger.info("common reference binsize written: %s -> %s", output.binsize, params.binsize)

        rule build_wisecondorx_reference_fixed_xx:
            input:
                bams=[SORTED_BAM.format(sample=sample_id) for sample_id in REF_SAMPLE_IDS_BY_SEX["XX"]],
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUTS_BY_SEX["XX"]
            log:
                project_path("logs", "wisecondorx", "build_reference_XX.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=WISE_CFG["binsize"],
                converted_dir=project_path("wisecondorx", "converted", "XX"),
                sample_ids=REF_SAMPLE_IDS_BY_SEX["XX"],
                sample_text="\n".join(REF_SAMPLE_IDS_BY_SEX["XX"])
            threads: 4
            run:
                from pathlib import Path

                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.tune_wisecondorx_bin_pca import build_reference, convert_all_bams

                write_rule_audit_log(log[0], input.metadata, [("SEX GROUP", "XX"), ("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("build_wisecondorx_reference_fixed_xx", log[0])
                npz_paths = convert_all_bams(
                    wisecondorx=params.wise,
                    bams=input.bams,
                    sample_ids=params.sample_ids,
                    binsize=params.binsize,
                    output_dir=Path(params.converted_dir),
                    threads=threads,
                    logger=logger,
                )
                build_reference(
                    wisecondorx=params.wise,
                    binsize=params.binsize,
                    npz_paths=npz_paths,
                    reference_output=Path(output.ref),
                    threads=threads,
                    logger=logger,
                )

        rule build_wisecondorx_reference_fixed_xy:
            input:
                bams=[SORTED_BAM.format(sample=sample_id) for sample_id in REF_SAMPLE_IDS_BY_SEX["XY"]],
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUTS_BY_SEX["XY"]
            log:
                project_path("logs", "wisecondorx", "build_reference_XY.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=WISE_CFG["binsize"],
                converted_dir=project_path("wisecondorx", "converted", "XY"),
                sample_ids=REF_SAMPLE_IDS_BY_SEX["XY"],
                sample_text="\n".join(REF_SAMPLE_IDS_BY_SEX["XY"])
            threads: 4
            run:
                from pathlib import Path

                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.tune_wisecondorx_bin_pca import build_reference, convert_all_bams

                write_rule_audit_log(log[0], input.metadata, [("SEX GROUP", "XY"), ("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("build_wisecondorx_reference_fixed_xy", log[0])
                npz_paths = convert_all_bams(
                    wisecondorx=params.wise,
                    bams=input.bams,
                    sample_ids=params.sample_ids,
                    binsize=params.binsize,
                    output_dir=Path(params.converted_dir),
                    threads=threads,
                    logger=logger,
                )
                build_reference(
                    wisecondorx=params.wise,
                    binsize=params.binsize,
                    npz_paths=npz_paths,
                    reference_output=Path(output.ref),
                    threads=threads,
                    logger=logger,
                )

        rule build_wisecondorx_gender_reference_fixed:
            input:
                xx_bams=[SORTED_BAM.format(sample=sample_id) for sample_id in REF_SAMPLE_IDS_BY_SEX["XX"]],
                xy_bams=[SORTED_BAM.format(sample=sample_id) for sample_id in REF_SAMPLE_IDS_BY_SEX["XY"]],
                common_binsize=COMMON_REF_BINSIZE,
                metadata=RUN_METADATA
            output:
                ref=GENDER_REF_OUTPUT
            log:
                project_path("logs", "wisecondorx", "build_reference_gender.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=WISE_CFG["binsize"],
                converted_dir=project_path("wisecondorx", "converted", "gender"),
                sample_ids=REF_SAMPLE_IDS_BY_SEX["XX"] + REF_SAMPLE_IDS_BY_SEX["XY"],
                sample_text=REFERENCE_SAMPLE_TEXT
            threads: 4
            run:
                from pathlib import Path

                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.tune_wisecondorx_bin_pca import build_reference, convert_all_bams

                write_rule_audit_log(log[0], input.metadata, [("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("build_wisecondorx_gender_reference_fixed", log[0])
                expected_binsize = int(Path(input.common_binsize).read_text(encoding="utf-8").strip())
                if int(params.binsize) != expected_binsize:
                    raise ValueError(
                        f"Configured binsize and common binsize mismatch: configured={params.binsize}, common={expected_binsize}"
                    )
                all_bams = list(input.xx_bams) + list(input.xy_bams)
                npz_paths = convert_all_bams(
                    wisecondorx=params.wise,
                    bams=all_bams,
                    sample_ids=params.sample_ids,
                    binsize=expected_binsize,
                    output_dir=Path(params.converted_dir),
                    threads=threads,
                    logger=logger,
                )
                build_reference(
                    wisecondorx=params.wise,
                    binsize=expected_binsize,
                    npz_paths=npz_paths,
                    reference_output=Path(output.ref),
                    threads=threads,
                    logger=logger,
                )

    else:
        rule build_wisecondorx_reference_fixed:
            input:
                bams=REFERENCE_BAMS,
                metadata=RUN_METADATA
            output:
                ref=REF_OUTPUT
            log:
                project_path("logs", "wisecondorx", "build_reference.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=WISE_CFG["binsize"],
                converted_dir=project_path("wisecondorx", "converted"),
                sample_ids=REF_SAMPLE_IDS,
                sample_text=REFERENCE_SAMPLE_TEXT
            threads: 4
            run:
                from pathlib import Path

                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.tune_wisecondorx_bin_pca import build_reference, convert_all_bams

                write_rule_audit_log(log[0], input.metadata, [("REFERENCE SAMPLES", params.sample_text)])
                logger = setup_logger("build_wisecondorx_reference_fixed", log[0])
                npz_paths = convert_all_bams(
                    wisecondorx=params.wise,
                    bams=input.bams,
                    sample_ids=params.sample_ids,
                    binsize=params.binsize,
                    output_dir=Path(params.converted_dir),
                    threads=threads,
                    logger=logger,
                )
                build_reference(
                    wisecondorx=params.wise,
                    binsize=params.binsize,
                    npz_paths=npz_paths,
                    reference_output=Path(output.ref),
                    threads=threads,
                    logger=logger,
                )
