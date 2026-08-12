container: config["containers"]["QC"]

PERFORMANCE_RULE_THREADS=config.get("performance", {}).get("rule_threads", {})

def performance_threads(rule_name, default):
    value=int(PERFORMANCE_RULE_THREADS.get(rule_name, default))
    return value if value > 0 else default

QC_TOOLS=config.get("container_tools", {}).get("QC", {})
PRE_TOOLS=config.get("container_tools", {}).get("pre", {})

sceVCFPath=QC_TOOLS["sceVCF"]
Rscript=QC_TOOLS["Rscript"]
peddy=QC_TOOLS["peddy"]
python3Path=QC_TOOLS["python3"]
multiqc=QC_TOOLS["multiqc"]
SentieonPath=PRE_TOOLS["sentieon"]

SAMPLES=config["sample"]
sampleInfoFile=config["sample_info"]
batch=config["batch"]


ruleHelper=config['src']['ruleHelper']
plotQC=config["src"]["plotQC"]
collectQCPy = config["src"]['collectQCPy']

reference=config["genome"]["fasta"]

qc_config=config["qc_cfg"]


rule QCall:
    input:
        expand("07_QC/{sample}.QC.tsv",sample=SAMPLES),
        "07_QC/"+batch+".sceVCF_result.txt",
        "07_QC/"+batch+".QCstat.tsv",
        "07_QC/"+batch+".gender.txt",
        "07_QC/"+batch+".QC.png",
        "07_QC/"+batch+".ped_check.csv",
        expand("07_QC/{sample}.alignment_summary_metrics.txt",sample=SAMPLES),
        expand("07_QC/{sample}.wgs_metrics.txt",sample=SAMPLES),
        expand("07_QC/{sample}.insert_size_metrics.txt",sample=SAMPLES),
        expand("07_QC/{sample}.insert_size_histogram.pdf",sample=SAMPLES),
        "07_QC/multiqc_report.html"


rule PeddyC:
    container:
        runtime_container("QC_PeddyC")
    input:
        ped = "08_ped/"+batch+".ped",
        vcf = "01_SNV/"+batch+".qual.flt.vcf.gz",
        vcfTbi = "01_SNV/"+batch+".qual.flt.vcf.gz.tbi",
    output:
        ped_check = "07_QC/"+batch+".ped_check.csv"
    params:
        peddy=peddy,
        batch=batch
    shell:
        "{params.peddy} -p {threads} --prefix 07_QC/{params.batch} {input.vcf} {input.ped} --sites hg38"

rule sceVCF:
    container:
        runtime_container("QC_sceVCF")
    input:
        batchVcf="01_SNV/{batch}.normalize.vcf.gz"
    output:
        sceVCFResult="07_QC/{batch}.sceVCF_result.txt"
    params:
        lowDepth=5,
        hightDepth=50,
        sceVCFPath=sceVCFPath
    shell:
        """
        {params.sceVCFPath} -d {params.lowDepth},{params.hightDepth} {input.batchVcf} >{output.sceVCFResult}
        """

rule gender:
    container:
        runtime_container("QC_gender")
    input:
        mappingQCFile="03_CNV/mappingQC.csv",
    output:
        gender="07_QC/"+batch+".gender.txt",
    params:
        helper=ruleHelper,
        python3Path=python3Path
    shell:
        "{params.python3Path} {params.helper} gender --input {input.mappingQCFile} --output {output.gender}"


rule SingleQC_merge:
    container:
        runtime_container("QC_SingleQC_merge")
    input:
        QC=lambda wc: f"07_QC/{wc.sample}.deduped.bam.1.QCstat.tsv",
        mappingQCFile="03_CNV/mappingQC.csv",
        bamchromStat=lambda wc: f"07_QC/{wc.sample}.deduped.bam.1.chromStat.txt",
        contaminationFile="07_QC/"+batch+".sceVCF_result.txt",
        MTQC="07_QC/MT/{sample}.MT.QC.txt",
        peddyFile="07_QC/"+batch+".ped_check.csv",
        snvFile="01_SNV/{sample}.flt.tsv",
        cnvFile="03_CNV/Annot/{sample}.CNV.tsv",
    output:
          "07_QC/{sample}.QC.tsv"
    params:
        python3Path=python3Path,
        collectQCPy=collectQCPy,
        sampleInfoFile=sampleInfoFile,
        qc_config=qc_config,
        snv_count_key=lambda wildcards: (
            "SNV_count_bkw"
            if wildcards.sample in config.get("BKWsampleList", [])
            else "SNV_count"
        )
    shell:
        """
        {params.python3Path} {params.collectQCPy} --sampleInfoFile {params.sampleInfoFile} --peddyFile {input.peddyFile} --sampleN {wildcards.sample} \
        --bamQCfile {input.QC} --mappingQCFile {input.mappingQCFile} --bamchromStat {input.bamchromStat} \
        --contaminationFile {input.contaminationFile} --MTQCfile {input.MTQC} --outFile {output} \
        --snvFile {input.snvFile} --cnvFile {input.cnvFile} --qc_config_file {params.qc_config} \
        --snv_count_key {params.snv_count_key}
        """

rule mergeQC:
    container:
        runtime_container("QC_mergeQC")
    input:
        expand("07_QC/{sample}.QC.tsv", sample=SAMPLES)
    output:
        batchQC="07_QC/"+batch+".QCstat.tsv",
    params:
        allQCfiles ="  ".join(expand("07_QC/{sample}.QC.tsv", sample=SAMPLES)),
    shell:
         """
         cat {params.allQCfiles}|awk '!x[$0]++' > {output.batchQC}
         """

rule plotQC:
    container:
        runtime_container("QC_plotQC")
    input:
        batchQC="07_QC/"+batch+".QCstat.tsv",
    output:
        batchQCpng = "07_QC/"+batch+".QC.png"
    params:
        Rscript=Rscript,
        plotQC=plotQC
    shell:
        "{params.Rscript} {params.plotQC} --infile {input.batchQC} --outfile {output.batchQCpng}"

rule multiqc_qc:
    container:
        runtime_container("QC_multiqc_qc")
    input:
        fastp = expand("07_QC/{sample}.fastp.json", sample=config["sample"]),
        aln_metrics = expand("07_QC/{sample}.alignment_summary_metrics.txt", sample=config["sample"]),
        wgs_metrics = expand("07_QC/{sample}.wgs_metrics.txt", sample=config["sample"]),
        cis_metrics = expand("07_QC/{sample}.insert_size_metrics.txt", sample=config["sample"]),
        gc_metrics = expand("07_QC/{sample}.gc_metrics.txt", sample=config["sample"])
    output:
        report = "07_QC/multiqc_report.html",
        data_dir = directory("07_QC/multiqc_data")
    params:
        multiqc = multiqc,
        outdir = "07_QC",
        filelist = "07_QC/multiqc_input_files.txt",
        helper = ruleHelper,
        python3Path = python3Path
    shell:
        """
        {params.python3Path} {params.helper} file-list --output {params.filelist} {input}
        {params.multiqc} -f -o {params.outdir} --file-list {params.filelist}
        """
