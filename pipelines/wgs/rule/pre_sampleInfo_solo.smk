# container: config["containers"]["pre"]


import os
CONTAINER_TOOLS=config.get("container_tools", {}).get("pre", {})
from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container


fastpPath=CONTAINER_TOOLS["fastp"]
SentieonPath=CONTAINER_TOOLS["sentieon"]
bam2bedGraphWGS=CONTAINER_TOOLS["bam2bedGraphWGS"]


SAMPLES=config["sample"]
extension=config["extension"]
PATTERN_R1 = extension
PATTERN_R2 = extension.replace("R1", "R2")
fastqfilePath=config["fastqDir"]

bam2blockUniqTools=config["src"]["bam2block_uniq"]
mtQC=config["src"]['MTQC']

mtbed=config["bed"]['MT_bed']
bedfile=config['bed']['QC_bed']

reference=config["genome"]["fasta"]
dbsnp=config["genome"]["dbsnp"]
known_Mills_indels=config["genome"]["known_Mills_indels"]
known_1000G_snps=config["genome"]["known_1000G_snps"]
known_1000G_indels=config["genome"]["known_1000G_indels"]


BIN2POS=config["database"]["BIN2POS"]
wgEncodeCrgMapability=config["database"]['mappability36mer']



rule Preall:
    input:
         expand("00_PreCalling/{sample}.deduped.cram", sample=SAMPLES),
         expand("00_PreCalling/{sample}.blk", sample=SAMPLES),
         expand("00_PreCalling/{sample}.iSizeFreq.tsv", sample=SAMPLES),
         expand("07_QC/{sample}.deduped.bam.1.QCstat.tsv",sample=SAMPLES),
         expand("07_QC/MT/{sample}.MT.QC.txt",sample=SAMPLES),
         expand("00_PreCalling/{sample}.g.vcf.gz", sample=SAMPLES),
         expand("00_PreCalling/{sample}-smoove.genotyped.vcf.gz", sample=SAMPLES),
         expand("00_PreCalling/{sample}.mity.vcf.gz", sample=SAMPLES),
         expand("00_PreCalling/{sample}.scramble.clusters.txt",sample=SAMPLES),

rule cleanFastq:
    container:
        runtime_container("pre_process_cleanFastq")
    input:
          fastq_1=fastqfilePath+"/{sample}"+ PATTERN_R1,
          fastq_2=fastqfilePath+"/{sample}"+ PATTERN_R2
    output:
          clean_fastq_1=temp("00_PreCalling/{sample}.clean.R1.fq.gz"),
          clean_fastq_2=temp("00_PreCalling/{sample}.clean.R2.fq.gz"),
          json="07_QC/{sample}.fastp.json",
          html="07_QC/{sample}.fastp.html"
    log:
          "07_QC/{sample}.fastp.log"
    params:
        fastpPath=fastpPath
    shell:
        "{params.fastpPath} -i {input.fastq_1} -o {output.clean_fastq_1} -I {input.fastq_2} -O {output.clean_fastq_2} -w {threads} -n 15 -l 30 -c -g -z 1 -h {output.html} -j {output.json} > {log} 2>&1"

rule mapping:
    container:
        runtime_container("pre_process_mapping")
    input:
         clean_fastq_1="00_PreCalling/{sample}.clean.R1.fq.gz",
         clean_fastq_2="00_PreCalling/{sample}.clean.R2.fq.gz"
    output:
         sorbam = temp("00_PreCalling/{sample}.sorted.bam"),
         sorbai = temp("00_PreCalling/{sample}.sorted.bam.bai"),
         stage = temp("00_PreCalling/{sample}.g1.mapping.done"),
    params:
        bwa_R=r"'@RG\tID:{sample}\tLB:{sample}\tSM:{sample}\tPL:ILLUMINA'",
        SentieonPath=SentieonPath,
        reference=reference
    shell:
         """
         export MALLOC_CONF=lg_dirty_mult:-1
         {params.SentieonPath} bwa mem -M -Y -R {params.bwa_R} -t {threads} -K 10000000  {params.reference} {input.clean_fastq_1} {input.clean_fastq_2}| {params.SentieonPath} util sort  -r {params.reference} -o {output.sorbam} -t {threads} --bam_compression 1 --sam2bam -i -
         touch {output.stage}
         """

rule Dedup:
    container:
        runtime_container("pre_process_Dedup")
    input:
         sortbam = "00_PreCalling/{sample}.sorted.bam",
         sortbai = "00_PreCalling/{sample}.sorted.bam.bai",
         stage = "00_PreCalling/{sample}.g1.mapping.done",
    output:
          scoreFile=temp("00_PreCalling/{sample}.score.txt.gz"),
          scoreFileTBI=temp("00_PreCalling/{sample}.score.txt.gz.tbi"),
          metricsFile=temp("00_PreCalling/{sample}.dedup_metrics.txt"),
          dupbamFile="00_PreCalling/{sample}.deduped.bam",
          bai="00_PreCalling/{sample}.deduped.bam.bai",
          stage="00_PreCalling/{sample}.g1.dedup.done",
    params:
        SentieonPath=SentieonPath,
        reference=reference
    shell:
        """
         export MALLOC_CONF=lg_dirty_mult:-1
         {params.SentieonPath} driver -r {params.reference} -t {threads} -i {input.sortbam} --algo LocusCollector --fun score_info {output.scoreFile}
         {params.SentieonPath} driver -r {params.reference} -t {threads} -i {input.sortbam} --algo Dedup --score_info {output.scoreFile} --metrics {output.metricsFile}  {output.dupbamFile}
         touch {output.stage}
         """

rule SentieonQCCram:
    container:
        runtime_container("pre_process_SentieonQCCram")
    input:
          dupbamFile="00_PreCalling/{sample}.deduped.bam",
          bai="00_PreCalling/{sample}.deduped.bam.bai",
          stage="00_PreCalling/{sample}.g1.bam2block.done",
    output:
         cram="00_PreCalling/{sample}.deduped.cram",
         idx="00_PreCalling/{sample}.deduped.cram.crai",
         wgs="07_QC/{sample}.wgs_metrics.txt",
         insert_metrics="07_QC/{sample}.insert_size_metrics.txt",
         insert_pdf="07_QC/{sample}.insert_size_histogram.pdf",
         alignment="07_QC/{sample}.alignment_summary_metrics.txt",
         gc_metrics="07_QC/{sample}.gc_metrics.txt",
         gc_summary="07_QC/{sample}.gc_summary.txt",
         stage="00_PreCalling/{sample}.g1.done",
    params:
         reference=reference,
         SentieonPath=SentieonPath,
    shell:
         """
         export MALLOC_CONF=lg_dirty_mult:-1
         {params.SentieonPath} driver -r {params.reference} -t {threads} -i {input.dupbamFile} --algo ReadWriter {output.cram} --algo WgsMetricsAlgo {output.wgs} --algo InsertSizeMetricAlgo {output.insert_metrics} --algo AlignmentStat {output.alignment} --algo GCBias --summary {output.gc_summary} {output.gc_metrics}
         {params.SentieonPath} util index -r {params.reference} {output.cram}
         {params.SentieonPath} plot InsertSizeMetricAlgo -o {output.insert_pdf} {output.insert_metrics}
         touch {output.stage}
         """

rule QualCal:
    container:
        runtime_container("pre_process_QualCal")
    input:
          dupbamFile="00_PreCalling/{sample}.deduped.bam",
          bai="00_PreCalling/{sample}.deduped.bam.bai",
          stage="00_PreCalling/{sample}.g1.dedup.done",
    output:
          recalTalble="00_PreCalling/{sample}.recal_data.table",
          stage=temp("00_PreCalling/{sample}.g1.qualcal.done"),
    params:
        SentieonPath=SentieonPath,
        reference=reference,
        dbsnp=dbsnp,
        known_Mills_indels=known_Mills_indels,
        known_1000G_indels=known_1000G_indels
    shell:
         """
         export MALLOC_CONF=lg_dirty_mult:-1
         {params.SentieonPath} driver -r {params.reference} -t {threads} -i {input.dupbamFile} --algo QualCal -k {params.dbsnp} -k {params.known_Mills_indels} -k {params.known_1000G_indels} {output.recalTalble}
         touch {output.stage}
         """

rule QCStatic:
    container:
        runtime_container("pre_process_QCStatic")
    input:
        dupbamFile="00_PreCalling/{sample}.deduped.bam",
        bai="00_PreCalling/{sample}.deduped.bam.bai",
        json="07_QC/{sample}.fastp.json",
        stage="00_PreCalling/{sample}.g1.dedup.done",
    output:
        qcstat="07_QC/{sample}.deduped.bam.1.QCstat.tsv",
        cov="07_QC/{sample}.deduped.bam.1.cov.bed",
        isize="07_QC/{sample}.deduped.bam.1.iSize.tsv",
        chromstat="07_QC/{sample}.deduped.bam.1.chromStat.txt",
        depth="07_QC/{sample}.deduped.bam.1.depth",
        stage=temp("00_PreCalling/{sample}.g1.qcstatic.done"),
    params:
        predix="{sample}",
        mvfile="{sample}.deduped.bam.1.",
        bam2bedGraphWGS=bam2bedGraphWGS,
        reference=reference,
        bedfile=bedfile
    shell:
        """
        {params.bam2bedGraphWGS} -j {input.json} -w 20000 -@ {threads} -b {params.bedfile} -o {params.predix} {input.dupbamFile} -R {params.reference} -G -L 2948627755
        mv {params.mvfile}* 07_QC
        touch {output.stage}
        """

rule Haplotyper:
    container:
        runtime_container("pre_process_Haplotyper")
    input:
        dupbamFile="00_PreCalling/{sample}.deduped.bam",
        crai="00_PreCalling/{sample}.deduped.bam.bai",
        recalTalble="00_PreCalling/{sample}.recal_data.table",
        stage="00_PreCalling/{sample}.g1.qualcal.done",
    output:
          gvcf="00_PreCalling/{sample}.g.vcf.gz",
          stage=temp("00_PreCalling/{sample}.g1.haplotyper.done"),
    params:
          sentieonPath = SentieonPath,
          genome = reference,
          dbsnp=dbsnp,
    shell:
         """
         export MALLOC_CONF=lg_dirty_mult:-1
        {params.sentieonPath} driver -r {params.genome} -t {threads} -i {input.dupbamFile} -q {input.recalTalble} --algo Haplotyper -d {params.dbsnp} --genotype_model multinomial --emit_mode gvcf {output.gvcf}
        touch {output.stage}
        """

rule bam2blockUniq:
    container:
        runtime_container("pre_process_bam2blockUniq")
    input:
        Bam = "00_PreCalling/{sample}.deduped.bam",
        bai="00_PreCalling/{sample}.deduped.bam.bai",
        stage="00_PreCalling/{sample}.g1.qcstatic.done",
    output:
        blkout="00_PreCalling/{sample}.blk",
        iSizeFreq="00_PreCalling/{sample}.iSizeFreq.tsv",
        logfile="00_PreCalling/{sample}.log",
        stage=temp("00_PreCalling/{sample}.g1.bam2block.done"),
    params:
        predix="{sample}",
        bam2blockUniqTools=bam2blockUniqTools,
        BIN2POS=BIN2POS,
        wgEncodeCrgMapability=wgEncodeCrgMapability
    shell:
        """
        {params.bam2blockUniqTools} -m 36 -U {params.BIN2POS} -C {params.wgEncodeCrgMapability} -b 2 -S 1 -@ {threads} {input.Bam} -o {params.predix} > {output.blkout} 2> {output.logfile}
        mv {params.predix}.iSizeFreq.tsv 00_PreCalling
        touch {output.stage}
        """
