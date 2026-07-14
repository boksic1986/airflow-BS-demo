"""
@author:Rzhang
@license: Apache Licence
@file: WGS_MT.smk
@time: 2021/09/08
@contact: zhiangrian@126.com
@site:
@software: PyCharm
@version 1.0
WGS pipeline before calling from fastq to bam and vcf file
#### update@zhangran,rule sexPredict ，女性chrX/chrY的阈值从20改为17，因为临检的样本出现过几次这个值小于20的情况

V3.0
#### update@zhangran ,20230523 delete rule Realigner and rule Sam2Cram and rule recalibration
#### update@zhangran ,20230826,mapping 参数，sort 参数增加 -t 4 --block_size 16G, delete

V3.1.1
#### update@zhangran ,20231019,rule smoove 新增export {smoovePath}

V3.1.2
#### update@zhangran ,20231219,新增rule mtQC ,统计线粒体的质控指标
#### update@zhangran,20240102,bam2bedGraphWGS增加参数设置  -L 2948627755
"""

##-----------------------------------------------##
## Working directory                             ##
## set by "-d" params                           ##
##-----------------------------------------------##
import os
import sys
fastpPath=config["bioSoft"]["fastpPath"]
SentieonPath=config["bioSoft"]["SentieonPath"]
reference=config["reference"]['hg38']["genome"]
known_Mills_indels=config["reference"]['hg38']["known_Mills_indels"]
known_1000G_snps=config["reference"]['hg38']["known_1000G_snps"]
known_1000G_indels=config["reference"]['hg38']["known_1000G_indels"]
dbsnp=config["reference"]['hg38']["dbsnp"]
cytoband=config["reference"]['hg38']["cytoband"]
bedfile=config['reference']['hg38']['QC_bed']
bam2bedGraph3Path=config["bioSoft"]["bam2bedGraph3Path"]
SamtoolsPath=config["bioSoft"]["SamtoolsPath"]
WGScript= sys.path[0].replace("rule", "script")
sampleInfoFile=config["sample_info"]
SAMPLES=config["sample"]
extension=config["extension"]
PATTERN_R1 = extension
PATTERN_R2 = extension.replace("R1", "R2")
batch=config["batch"]
fastqfilePath=config["fastqDir"]
Rscript=config["bioSoft"]["Rscript"]
#CNV software
bam2blockUniqTools=config["Self-built-Tools"]["CNV"]["bam2block_uniq"]
BIN2POS=config["reference"]['hg38']["BIN2POS"]
wgEncodeCrgMapability=config["reference"]['hg38']['wgEncodeCrgMapability']
#SV software
bgzip=config["bioSoft"]["bgzip"]
tabix=config["bioSoft"]["tabix"]
htslib=os.path.dirname(bgzip).rstrip('/')
lumpyPath=config["bioSoft"]["lumpyPath"]+"/bin"
svtyper=config["bioSoft"]["svtyperPath"]
smoovePath=config["bioSoft"]["smoovePath"]
# MT
mityPath=config["bioSoft"]["mitypath"]
bamdstPath=config["bioSoft"]["bamdst"]
mtbed=config["reference"]['hg38']["MTbed"]
mtQC=config["Self-built-Tools"]['SNV_MT']['MTQC']
# MEI
clusterIdentifier=config["bioSoft"]["clusterIdentifier"]
#STR
ExpansionHunterPath=config["bioSoft"]["ExpansionHunterPath"]
ExpansionHunterDatabase=config["reference"]['hg38']["ExpansionHunterDatabase"]
REjson=config["reference"]['hg38']["REjson"]
rule Preall:
    input:
         expand("00_PreCalling/{sample}.deduped.bam", sample=SAMPLES),
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
    input:
          fastq_1=fastqfilePath+"/{sample}"+ PATTERN_R1,
          fastq_2=fastqfilePath+"/{sample}"+ PATTERN_R2
    output:
          clean_fastq_1=temp("00_PreCalling/{sample}.clean.R1.fq.gz"),
          clean_fastq_2=temp("00_PreCalling/{sample}.clean.R2.fq.gz"),
          json="07_QC/{sample}.template.json",
          html="07_QC/{sample}.template.html",
          logfile="07_QC/{sample}.fastp.log"
    threads: 8
    resources:
        qsub_vf=30000
    shell:
        "{fastpPath}/fastp -i {input.fastq_1} -o {output.clean_fastq_1} -I {input.fastq_2} -O {output.clean_fastq_2} -w {threads} -n 15 -l 30 -c -g -z 1 -h {output.html} -j {output.json} > {output.logfile} 2>&1"
rule mapping:
    input:
         clean_fastq_1="00_PreCalling/{sample}.clean.R1.fq.gz",
         clean_fastq_2="00_PreCalling/{sample}.clean.R2.fq.gz"
    output:
         sorbam = temp("00_PreCalling/{sample}.sorted.bam"),
         sorbai = temp("00_PreCalling/{sample}.sorted.bam.bai"),
    params:
          bwa_R=r"'@RG\tID:{sample}\tLB:{sample}\tSM:{sample}\tPL:ILLUMINA'"
    threads:12
    resources:
        qsub_vf=30000
    shell:
         """
         export SENTIEON_LICENSE=/bi/software/Sentieon/Zhejiang_Biosan_Biotechnology_Co._LTD_cluster.lic
         export MALLOC_CONF=lg_dirty_mult:-1
         {SentieonPath}/sentieon bwa mem -M -Y -R {params.bwa_R} -t {threads} -K 10000000  {reference} {input.clean_fastq_1} {input.clean_fastq_2}| {SentieonPath}/sentieon util sort  -r {reference} -o {output.sorbam} -t {threads} --bam_compression 1 --sam2bam -i -
         """
rule Dedup:
    input:
         sortbam = "00_PreCalling/{sample}.sorted.bam",
         sortbai = "00_PreCalling/{sample}.sorted.bam.bai",
    output:
          scoreFile=temp("00_PreCalling/{sample}.score.txt.gz"),
          scoreFileTBI=temp("00_PreCalling/{sample}.score.txt.gz.tbi"),
          metricsFile=temp("00_PreCalling/{sample}.dedup_metrics.txt"),
          dupbamFile=temp("00_PreCalling/{sample}.deduped.bam"),
          bai=temp("00_PreCalling/{sample}.deduped.bam.bai"),
    threads:8
    resources:
        qsub_vf=32000
    shell:
        """
         export SENTIEON_LICENSE=/bi/software/Sentieon/Zhejiang_Biosan_Biotechnology_Co._LTD_cluster.lic
         export MALLOC_CONF=lg_dirty_mult:-1
         {SentieonPath}/sentieon driver -r {reference} -t {threads} -i {input.sortbam} --algo LocusCollector --fun score_info {output.scoreFile}
         {SentieonPath}/sentieon driver -r {reference} -t {threads} -i {input.sortbam} --algo Dedup --score_info {output.scoreFile} --metrics {output.metricsFile}  {output.dupbamFile}
         """
rule Sam2Cram:
    input:
          dupbamFile="00_PreCalling/{sample}.deduped.bam",
          bai="00_PreCalling/{sample}.deduped.bam.bai",
    output:
         cram = "00_PreCalling/{sample}.deduped.cram",
         idx = "00_PreCalling/{sample}.deduped.cram.crai"
    params:
         genome = reference,
         samtoolspath=SamtoolsPath,
    threads:8
    resources:
        qsub_vf=10000
    shell:
         """
        {params.samtoolspath}/samtools view -@ {threads} -C -T {params.genome} {input.dupbamFile} -o {output.cram}
        {params.samtoolspath}/samtools  index -@ {threads} {output.cram}
         """
rule QualCal:
    input:
          dupbamFile="00_PreCalling/{sample}.deduped.bam",
          bai="00_PreCalling/{sample}.deduped.bam.bai",
    output:
          recalTalble="00_PreCalling/{sample}.recal_data.table"
    threads:8
    resources:
        qsub_vf=32000
    shell:
         """
         export SENTIEON_LICENSE=/bi/software/Sentieon/Zhejiang_Biosan_Biotechnology_Co._LTD_cluster.lic
         export MALLOC_CONF=lg_dirty_mult:-1
         {SentieonPath}/sentieon driver -r {reference} -t {threads} -i {input.dupbamFile} --algo QualCal -k {dbsnp} -k {known_Mills_indels} -k {known_1000G_indels} {output.recalTalble}
         """
rule QCStatic:
    input:
        dupbamFile="00_PreCalling/{sample}.deduped.bam",
        bai="00_PreCalling/{sample}.deduped.bam.bai",
        json="07_QC/{sample}.template.json"
    output:
        "07_QC/{sample}.deduped.bam.1.QCstat.tsv",
        "07_QC/{sample}.deduped.bam.1.cov.bed",
        "07_QC/{sample}.deduped.bam.1.iSize.tsv",
        "07_QC/{sample}.deduped.bam.1.chromStat.txt",
        "07_QC/{sample}.deduped.bam.1.depth",
    params:
        predix="{sample}",
        mvfile="{sample}.deduped.bam.1.",
    threads:8
    resources:
        qsub_vf=30000
    shell:
        """
        {bam2bedGraph3Path}/bam2bedGraphWGS -j {input.json} -w 20000 -@ {threads} -b {bedfile} -o {params.predix}  {input.dupbamFile} -R  {reference} -G  -L 2948627755
        mv {params.mvfile}* 07_QC
        {Rscript} {bam2bedGraph3Path}/covDist.R --cov {output[1]} --isize {output[2]} --chromStat {output[3]} -d {output[4]} --cytoband {cytoband} --outfile {params.predix} --maxDepth 100
        mv {params.predix}.covDist.png {params.predix}.chrDepth.png {params.predix}.chrDist.png {params.predix}.isizeDist.png 07_QC
        """
rule mtQC:
    input:
        cram = "00_PreCalling/{sample}.deduped.cram",
        idx = "00_PreCalling/{sample}.deduped.cram.crai"
    output:
        mtbam='00_PreCalling/{sample}.deduped.chrM.bam',
        mtbamindex='00_PreCalling/{sample}.deduped.chrM.bam.bai',
        mtqc='07_QC/MT/{sample}.MT.QC.txt'
    params:
        predix="{sample}",
        samtoolspath=SamtoolsPath,
    threads:4
    resources:
        qsub_vf=30000
    shell:
         """
        {params.samtoolspath}/samtools view -b -h -@ {threads} {input.cram} chrM -o {output.mtbam}
        {params.samtoolspath}/samtools index -b {output.mtbam}
        mkdir 07_QC/MT/{params.predix}
        {bamdstPath} -p {mtbed} -f 0 --uncover 20 -o 07_QC/MT/{params.predix} {output.mtbam}
        python3 {mtQC} -I 07_QC/MT/ -O {output.mtqc} -s {params.predix}
        """
rule Haplotyper:
    input:
        dupbamFile="00_PreCalling/{sample}.deduped.bam",
        crai="00_PreCalling/{sample}.deduped.bam.bai",
        recalTalble="00_PreCalling/{sample}.recal_data.table"
    output:
          gvcf="00_PreCalling/{sample}.g.vcf.gz"
    params:
          sentieonPath = SentieonPath,
          genome = reference,
          dbsnp=dbsnp,
    threads:8
    resources:
        qsub_vf=32000
    shell:
         """
         export SENTIEON_LICENSE=/bi/software/Sentieon/Zhejiang_Biosan_Biotechnology_Co._LTD_cluster.lic
         export MALLOC_CONF=lg_dirty_mult:-1
        {params.sentieonPath}/sentieon driver -r {params.genome} -t {threads} -i {input.dupbamFile} -q {input.recalTalble} --algo Haplotyper -d {params.dbsnp} --genotype_model multinomial --emit_mode gvcf {output.gvcf}
        """
rule bam2blockUniq:
    input:
        Bam = "00_PreCalling/{sample}.deduped.bam",
        bai="00_PreCalling/{sample}.deduped.bam.bai"
    output:
        blkout="00_PreCalling/{sample}.blk",
        iSizeFreq="00_PreCalling/{sample}.iSizeFreq.tsv",
        logfile="00_PreCalling/{sample}.log"
    params:
        predix="{sample}",
    resources:
        qsub_vf=30000
    threads:4
    shell:
        """
        {bam2blockUniqTools} -m 36 -U {BIN2POS} -C {wgEncodeCrgMapability} -b 2 -S 1 -@ {threads} {input.Bam} -o {params.predix} > {output.blkout} 2> {output.logfile}
        mv {params.predix}.iSizeFreq.tsv 00_PreCalling
        """
rule Smooverun:
    input:
        Bam = "00_PreCalling/{sample}.deduped.bam",
        bai="00_PreCalling/{sample}.deduped.bam.bai"
    output:
        outfile="00_PreCalling/{sample}-smoove.genotyped.vcf.gz"
    params:
        name="{sample}",
        excludechroms='~^GL,~^HLA,~_random,~^chrUn,~alt,~decoy',
        htslibpath=htslib,
        samtoolspath=SamtoolsPath
    threads: 1
    resources:
        qsub_vf=10000
    shell:
         """
         export PATH={lumpyPath}:{params.htslibpath}:{svtyper}:{params.samtoolspath}:{smoovePath}:$PATH
        {smoovePath}/smoove call -x -d -F --name {params.name} --exclude {smoovePath}/exclude.cnvnator_100bp.GRCh38.20170403.bed --fasta {reference} -p {threads} --excludechroms {params.excludechroms} --genotype {input.Bam} --outdir 00_PreCalling/
        """
rule mityCall:
    input:
         Bam = "00_PreCalling/{sample}.deduped.bam",
         bai="00_PreCalling/{sample}.deduped.bam.bai"
    output:
         gzvcf="00_PreCalling/{sample}.mity.vcf.gz",
    params:
          reference="hg38",
          prefix="{sample}",
          callingdir=directory("00_PreCalling/"),
    threads:1
    resources:
        qsub_vf=32000
    shell:
          """
          {mityPath}/mity call --reference {params.reference} --prefix {params.prefix} --out-folder-path {params.callingdir} --normalise {input.Bam}
          """
rule MEICall:
    input:
        Bam = "00_PreCalling/{sample}.deduped.bam",
        bai="00_PreCalling/{sample}.deduped.bam.bai"
    output:
        clusters = "00_PreCalling/{sample}.scramble.clusters.txt",
    resources:
        qsub_vf=10000
    threads:1
    shell:
        """
        {clusterIdentifier} {input.Bam} > {output.clusters}
        """
