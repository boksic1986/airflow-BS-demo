if CNV_ENABLED:
    if PREDICT_BY_SEX_ENABLED:
        rule wisecondorx_convert_for_cnv:
            input:
                bam=SORTED_BAM,
                common_binsize=COMMON_REF_BINSIZE,
                metadata=RUN_METADATA
            output:
                npz=CNV_NPZ
            log:
                project_path("logs", "cnv", "{sample}.convert.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                binsize=lambda wildcards, input: read_int_from_file(input.common_binsize)
            threads: 4
            shell:
                r"""
                mkdir -p "$(dirname {output.npz})" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== COMMON BINSIZE ==="
                    cat {input.common_binsize:q}
                    echo "=== COMMAND ==="
                ) > {log:q}
                {params.wise:q} convert {input.bam:q} {output.npz:q} --binsize {params.binsize} >> {log:q} 2>&1
                """

        rule wisecondorx_gender_for_predict:
            input:
                npz=CNV_NPZ,
                ref=GENDER_REF_OUTPUT,
                metadata=RUN_METADATA
            output:
                tsv=CNV_GENDER_TSV
            log:
                project_path("logs", "cnv", "{sample}.gender.log")
            params:
                wise=config["biosoft"]["WisecondorX"]
            threads: 1
            run:
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log
                from scripts.wisecondorx_gender import run_wisecondorx_gender

                write_rule_audit_log(log[0], input.metadata)
                logger = setup_logger("wisecondorx_gender", log[0])
                run_wisecondorx_gender(
                    wisecondorx=params.wise,
                    sample_npz=input.npz,
                    gender_reference=input.ref,
                    output_tsv=output.tsv,
                    sample_id=wildcards.sample,
                    logger=logger,
                )

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
                min_total=CNV_QC_MIN_TOTAL,
                min_nonzero=CNV_QC_MIN_NONZERO,
                max_mad=CNV_QC_MAX_MAD
            threads: 1
            run:
                from scripts.cnv_qc import run_cnv_qc
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log

                write_rule_audit_log(log[0], input.metadata)
                logger = setup_logger("cnv_qc", log[0])
                run_cnv_qc(
                    sample_id=wildcards.sample,
                    npz=input.npz,
                    output_tsv=output.tsv,
                    output_plot=output.plot,
                    pass_marker=output.passed,
                    min_total_counts=params.min_total,
                    min_nonzero_fraction=params.min_nonzero,
                    max_mad_log1p=params.max_mad,
                    logger=logger,
                )

        rule wisecondorx_predict_cnv:
            input:
                npz=CNV_NPZ,
                gender_tsv=CNV_GENDER_TSV,
                qc_report=CNV_QC_TSV,
                qc_pass=CNV_QC_PASS,
                metadata=RUN_METADATA
            output:
                done=CNV_DONE
            log:
                project_path("logs", "cnv", "{sample}.predict.log")
            params:
                wise=config["biosoft"]["WisecondorX"],
                ref=lambda wildcards, input: select_predict_reference(input.gender_tsv),
                gender=lambda wildcards, input: select_predict_gender(input.gender_tsv),
                zscore=CNV_ZSCORE,
                alpha=CNV_ALPHA,
                maskrepeats=CNV_MASKREPEATS,
                minrefbins=CNV_MINREFBINS,
                seed=CNV_SEED,
                output_prefix=lambda wildcards: str(Path(CNV_PREDICT_DIR) / wildcards.sample)
            threads: 2
            shell:
                r"""
                mkdir -p "$(dirname {output.done})" "$(dirname {log})"
                (
                    echo "=== PIPELINE AUDIT ==="
                    cat {input.metadata:q}
                    echo "=== GENDER CALL ==="
                    cat {input.gender_tsv:q}
                    echo "=== QC REPORT ==="
                    cat {input.qc_report:q}
                    echo "=== COMMAND ==="
                ) > {log:q}
                if grep -qx 'PASS' {input.qc_pass:q}; then
                    {params.wise:q} predict {input.npz:q} {params.ref:q} {params.output_prefix:q} \
                        --gender {params.gender} \
                        --bed \
                        --plot \
                        --zscore {params.zscore} \
                        --alpha {params.alpha} \
                        --maskrepeats {params.maskrepeats} \
                        --minrefbins {params.minrefbins} \
                        --seed {params.seed} >> {log:q} 2>&1
                    test -s {params.output_prefix:q}_statistics.txt
                    printf 'completed\n' > {output.done:q}
                else
                    echo 'Prediction skipped because sample QC failed.' >> {log:q}
                    printf 'skipped_qc\n' > {output.done:q}
                fi
                """
    else:
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
                min_total=CNV_QC_MIN_TOTAL,
                min_nonzero=CNV_QC_MIN_NONZERO,
                max_mad=CNV_QC_MAX_MAD
            threads: 1
            run:
                from scripts.cnv_qc import run_cnv_qc
                from scripts.pipeline_logging import setup_logger, write_rule_audit_log

                write_rule_audit_log(log[0], input.metadata)
                logger = setup_logger("cnv_qc", log[0])
                run_cnv_qc(
                    sample_id=wildcards.sample,
                    npz=input.npz,
                    output_tsv=output.tsv,
                    output_plot=output.plot,
                    pass_marker=output.passed,
                    min_total_counts=params.min_total,
                    min_nonzero_fraction=params.min_nonzero,
                    max_mad_log1p=params.max_mad,
                    logger=logger,
                )

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
                seed=CNV_SEED,
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
                if grep -qx 'PASS' {input.qc_pass:q}; then
                    {params.wise:q} predict {input.npz:q} {input.ref:q} {params.output_prefix:q} \
                        --bed \
                        --plot \
                        --zscore {params.zscore} \
                        --alpha {params.alpha} \
                        --maskrepeats {params.maskrepeats} \
                        --minrefbins {params.minrefbins} \
                        --seed {params.seed} >> {log:q} 2>&1
                    test -s {params.output_prefix:q}_statistics.txt
                    printf 'completed\n' > {output.done:q}
                else
                    echo 'Prediction skipped because sample QC failed.' >> {log:q}
                    printf 'skipped_qc\n' > {output.done:q}
                fi
                """

    rule aggregate_pgta_qc:
        input:
            mapping=expand(MAPPING_QC_TSV, sample=SAMPLES),
            cnv=expand(CNV_QC_TSV, sample=SAMPLES),
            status=expand(CNV_QC_PASS, sample=SAMPLES)
        output:
            PGTA_QC_SUMMARY
        log:
            project_path("logs", "qc", "aggregate_pgta_qc.log")
        params:
            python=config["biosoft"]["python"],
            script=SCRIPT_AGGREGATE_PREDICT_QC,
            project_root=str(PROJECT),
            sample_ids=",".join(SAMPLES)
        shell:
            r"""
            mkdir -p "$(dirname {output})" "$(dirname {log})"
            {params.python:q} {params.script:q} qc \
                --project-root {params.project_root:q} \
                --samples {params.sample_ids:q} \
                --output {output:q} > {log:q} 2>&1
            """

    rule aggregate_pgta_prediction_status:
        input:
            expand(CNV_DONE, sample=SAMPLES)
        output:
            PGTA_PREDICTION_SUMMARY
        log:
            project_path("logs", "cnv", "aggregate_prediction_status.log")
        params:
            python=config["biosoft"]["python"],
            script=SCRIPT_AGGREGATE_PREDICT_QC,
            project_root=str(PROJECT),
            sample_ids=",".join(SAMPLES)
        shell:
            r"""
            mkdir -p "$(dirname {output})" "$(dirname {log})"
            {params.python:q} {params.script:q} prediction \
                --project-root {params.project_root:q} \
                --samples {params.sample_ids:q} \
                --output {output:q} > {log:q} 2>&1
            """
