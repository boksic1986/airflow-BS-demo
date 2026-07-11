if "baseline_qc" in REQUESTED_TARGETS:
    rule baseline_bam_uniformity_qc:
        input:
            target_bam=SORTED_BAM,
            ref_bams=lambda wildcards: [SORTED_BAM.format(sample=sample_id) for sample_id in BASELINE_SAMPLE_IDS if sample_id != wildcards.sample],
            metadata=RUN_METADATA
        output:
            tsv=BASELINE_QC_TSV,
            profile=BASELINE_QC_PROFILE_TSV,
            ref_summary=BASELINE_QC_REF_SUMMARY_TSV,
            plot=BASELINE_QC_PLOT,
            gc_plot=BASELINE_QC_GC_PLOT
        log:
            project_path("logs", "qc", "baseline", "{sample}.log")
        params:
            python_bin=config["biosoft"]["python"],
            script=SCRIPT_BAM_UNIFORMITY_QC,
            outdir=lambda wildcards: str(Path(BASELINE_QC_DIR) / wildcards.sample),
            reference_fasta=config["core"]["reference_genome"]
        threads: 4
        shell:
            r"""
            mkdir -p "{params.outdir}" "$(dirname {log})"
            (
                echo "=== PIPELINE AUDIT ==="
                cat {input.metadata:q}
                echo "=== COMMAND ==="
            ) > {log:q}
            {params.python_bin:q} {params.script:q} \
                --target-bam {input.target_bam:q} \
                --ref-bams {input.ref_bams:q} \
                --reference-fasta {params.reference_fasta:q} \
                --threads {threads} \
                --outdir {params.outdir:q} \
                --log {log:q} \
                >> {log:q} 2>&1
            """

    rule aggregate_baseline_qc:
        input:
            qc_tsvs=expand(BASELINE_QC_TSV, sample=BASELINE_SAMPLE_IDS),
            metadata=RUN_METADATA
        output:
            summary=BASELINE_QC_SUMMARY,
            passed=BASELINE_QC_PASS_SAMPLES,
            report=BASELINE_QC_REPORT_MD
        log:
            project_path("logs", "qc", "baseline", "aggregate.log")
        params:
            python_bin=config["biosoft"]["python"],
            script=SCRIPT_AGGREGATE_BASELINE_QC
        threads: 1
        shell:
            r"""
            mkdir -p "$(dirname {output.summary})" "$(dirname {log})"
            (
                echo "=== PIPELINE AUDIT ==="
                cat {input.metadata:q}
                echo "=== COMMAND ==="
            ) > {log:q}
            {params.python_bin:q} {params.script:q} \
                --qc-tsvs {input.qc_tsvs:q} \
                --summary-output {output.summary:q} \
                --pass-samples-output {output.passed:q} \
                --report-output {output.report:q} \
                --log {log:q} \
                >> {log:q} 2>&1
            """
