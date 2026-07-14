

SAMPLES=config["sample"]
sampleInfoFile=config["sample_info"]
batch=config["batch"]

sceVCFPath=config["bioSoft"]["sceVCF"]
Rscript=config["bioSoft"]["Rscript"]
plotQC=config["Self-built-Tools"]["other"]["plotQC"]
peddy=config['bioSoft']['peddy']
collectQCPy = config["Self-built-Tools"]['other']['collectQCPy']
python3Path=config['bioSoft']['python3']
qc_config=config["qc_cfg"]


rule QCall:
    input:
        expand("07_QC/{sample}.QC.tsv",sample=SAMPLES),
        "07_QC/"+batch+".sceVCF_result.txt",
        "07_QC/"+batch+".QCstat.tsv",
        "07_QC/"+batch+".gender.txt",
        "07_QC/"+batch+".QC.png",
        "07_QC/"+batch+".ped_check.csv",


rule PeddyC:
    input:
        ped = "08_ped/"+batch+".ped",
        vcf = "01_SNV/"+batch+".qual.flt.vcf.gz",
    output:
        ped_check = "07_QC/"+batch+".ped_check.csv"
    resources:
        qsub_vf=10000
    threads:4
    shell:
        "{peddy} -p {threads} --prefix 07_QC/{batch} {input.vcf} {input.ped} --sites hg38"

rule sceVCF:
    input:
        batchVcf="01_SNV/{batch}.normalize.vcf.gz"
    output:
        sceVCFResult="07_QC/{batch}.sceVCF_result.txt"
    params:
        lowDepth=5,
        hightDepth=50
    resources:
        qsub_vf=1000
    threads:1
    shell:
        """
        {sceVCFPath} -d {params.lowDepth},{params.hightDepth} {input.batchVcf} >{output.sceVCFResult}
        """

rule gender:
    input:
        mappingQCFile="03_CNV/mappingQC.csv",
    output:
        gender="07_QC/"+batch+".gender.txt",
    resources:
        qsub_vf=100
    threads:1
    run:
        import pandas as pd

        df = pd.read_csv(input.mappingQCFile, usecols=['Sample', 'Gender'])
        df['Sample'] = df['Sample'].str.replace('-R1.fq.gz','')
        df.to_csv(output.gender, index=False, header=False)


rule SingleQC_merge:
    input:
        QC="07_QC/{sample}.deduped.bam.1.QCstat.tsv",
        mappingQCFile="03_CNV/mappingQC.csv",
        bamchromStat="07_QC/{sample}.deduped.bam.1.chromStat.txt",
        contaminationFile="07_QC/"+batch+".sceVCF_result.txt",
        MTQC="07_QC/MT/{sample}.MT.QC.txt",
        peddyFile="07_QC/"+batch+".ped_check.csv",
        snvFile="01_SNV/{sample}.flt.tsv",
        cnvFile="03_CNV/Annot/{sample}.CNV.tsv",
    output:
          "07_QC/{sample}.QC.tsv"
    resources:
        qsub_vf=100
    threads:1
    shell:
        """
        {python3Path}/python3 {collectQCPy} --sampleInfoFile {sampleInfoFile} --peddyFile {input.peddyFile} --sampleN {wildcards.sample} \
        --bamQCfile {input.QC} --mappingQCFile {input.mappingQCFile} --bamchromStat {input.bamchromStat} \
        --contaminationFile {input.contaminationFile} --MTQCfile {input.MTQC} --outFile {output} \
        --snvFile {input.snvFile} --cnvFile {input.cnvFile} --qc_config {qc_config}
        """

rule mergeQC:
    input:
        expand("07_QC/{sample}.QC.tsv", sample=SAMPLES)
    output:
        batchQC="07_QC/"+batch+".QCstat.tsv",
    params:
        allQCfiles ="  ".join(expand("07_QC/{sample}.QC.tsv", sample=SAMPLES)),
    resources:
        qsub_vf=1000
    threads:1
    shell:
         """
         cat {params.allQCfiles}|awk '!x[$0]++' > {output.batchQC}
         """

rule plotQC:
    input:
        batchQC="07_QC/"+batch+".QCstat.tsv",
    output:
        batchQCpng = "07_QC/"+batch+".QC.png"
    resources:
        qsub_vf=10000
    threads:1
    shell:
        "{Rscript} {plotQC} --infile {input.batchQC} --outfile {output.batchQCpng}"
