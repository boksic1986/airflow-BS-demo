"""
@author:Rzhang
@license: Apache Licence
@file: MEI.smk
@time: 2022/09/14
@contact: zhiangrian@126.com
@site:
@software: PyCharm
@version 1.0

#### update@zhangran,20221014, rule MEI添加awk -F '\t' '{{sub(/:0\t/,":1\t"); print $0 }}' {output.clustersTmp} > {output.clusters}代码修改cluster文件，WGS 的结果中会出现chr*:0的情况，调用scramble 中的make.vcf.R时会报错
## V2.0
#### update@zhangran,20230801,更新参考基因组版本为hg38
#### update@zhangran,20230801,更新bam文件为deduped.bam
#### update@zhangran,20230801,更新VEP注释参考基因组版本为GRCh38
#### update@zhangran,20230801,指定HPOfile为批次最新文件
## V2.1
#### update@zhangran,20230920,把动态突变的calling 移到pre_sampleInfo_solo.smk中
"""
import os
clusterIdentifier=config["bioSoft"]["clusterIdentifier"]
Rscript=config["bioSoft"]["Rscript"]
scrambleRscript=config["bioSoft"]["scrambleRscript"]
scrambleDir=config["bioSoft"]["scrambleDir"]
meiRef=config["reference"]["hg38"]["meiRef"]
reference=config["reference"]['hg38']["genome"]
bgzip=config["bioSoft"]["bgzip"]
tabix=config["bioSoft"]["tabix"]
bcftools=config["bioSoft"]["bcftoolsPath"]
VEP=config['bioSoft']['VEP']
vep_cache=config['database']['vepcache']
meiSplitPy=config['Self-built-Tools']['SNV_MT']['meiSplitPy']
python3Path=config['bioSoft']['python3']
geneDisease=config["reference"]["hg38"]["geneDisease"]
geneMIMnumber=config["reference"]["hg38"]["gene_MIMnumber"]
hpoFile=config['database']['HPO_CHPO_gene']
localMeiMaf=config['database']['localMeiMafFile']

rule MEIall:
    input:
        expand("09_MEI/{sample}.MEIs.tsv",sample=config["sample"])

rule MEI:
    input:
        clusters = "00_PreCalling/{sample}.scramble.clusters.txt"
    output:
        txt = "09_MEI/{sample}.raw.MEIs_MEIs.txt",
        vcf = temp("09_MEI/{sample}.raw.MEIs.vcf"),
        gz = "09_MEI/{sample}.raw.MEIs.vcf.gz",
        tbi = "09_MEI/{sample}.raw.MEIs.vcf.gz.tbi"
    params:
        p_s = '{sample}',
        p_wkdir = os.getcwd(),
        p_outprefix = "09_MEI/{sample}.raw.MEIs"
    resources:
        qsub_vf=10000
    threads:8
    shell:
        """
        {Rscript} --vanilla {scrambleRscript} --install-dir={scrambleDir} --mei-refs={meiRef} --ref={reference} --cluster-file={params.p_wkdir}/{input.clusters} --out-name={params.p_wkdir}/{params.p_outprefix} --mei-score=50 --nCluster=5 --eval-meis
        awk 'BEGIN{{OFS="\\t"}} /^##/ {{print; next}} /^#CHROM/ {{print "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">"; print $0 "\\tFORMAT\\t{params.p_s}"; next}} !/^#/ {{print $1,$2,$3,$4,$5,$6,$7,$8,"GT","./1"}}' {output.vcf} | {bcftools} view -Oz -o {output.gz} && tabix -fp vcf {output.gz}
        """

rule MEI_vep:
    input:
        gz = expand("09_MEI/{sample}.raw.MEIs.vcf.gz", sample=config["sample"]),
        tbi = expand("09_MEI/{sample}.raw.MEIs.vcf.gz.tbi", sample=config["sample"])
    output:
        flt_vcf = expand("09_MEI/{batch}.flt.MEIs.vcf.gz", batch=config["batch"]),
        vep_vcf = expand("09_MEI/{batch}.vep.MEIs.vcf.gz", batch=config["batch"])
    resources:
        qsub_vf=20000
    threads:10
    params:
        p1 = "CHROM~\"_\" || CHROM~\"\.\" || (N_SAMPLES>=12 && COUNT(FMT/GT~\"1\")/N_SAMPLES>=0.5) || (N_SAMPLES>=30 && COUNT(FMT/GT~\"1\")/N_SAMPLES>=0.3) || (N_SAMPLES>=100 && COUNT(FMT/GT~\"1\")/N_SAMPLES>=0.15)",
        merge_cmd = lambda wildcards, input: f"{bcftools} merge -m id {input.gz} |" if len(config["sample"]) > 1 else "",
        input_cmd = lambda wildcards, input: f"{input.gz}" if len(config["sample"]) == 1 else ""
    shell:
        """
        {params.merge_cmd} {bcftools} view -e '{params.p1}' -Oz -o {output.flt_vcf} {params.input_cmd}
        {VEP}/vep -i {output.flt_vcf} -o {output.vep_vcf} --dir_cache {vep_cache} --fasta {reference} --custom {localMeiMaf},LocalMEI,vcf,exact,0,AC,AN,AF --offline --cache --hgvs --hgvsg --symbol --canonical --total_length --force --force_overwrite --no_stats --vcf --compress_output bgzip --refseq --use_given_ref --assembly GRCh38 --fork {threads} --no_escape --xref_refseq --pick --failed 1 --dont_skip
        """

rule MEI_annotation:
    input:
        vep_vcf = expand("09_MEI/{batch}.vep.MEIs.vcf.gz", batch=config["batch"]),
        mei_raw = "09_MEI/{sample}.raw.MEIs_MEIs.txt",
        pedfile = expand("08_ped/{batch}.ped", batch=config["batch"]),
        sampleRank=expand("08_ped/{batch}.rank.txt", batch=config["batch"])
    output:
        mei_tsv = "09_MEI/{sample}.MEIs.tsv"
    resources:
        qsub_vf=20000
    threads:8
    params:
        p_s = '{sample}',
        phenotype = lambda wildcards:config["phenotype"][wildcards.sample],
        pedigreeID = lambda wildcards: {item[0]: item[1] for item in [(_k.split(':')) for _k in config["sample2pedigree"]]}[wildcards.sample]
    shell:
        """
        {python3Path}/python3 {meiSplitPy} -i {input.vep_vcf} -s {params.p_s} -a {input.mei_raw} -r 08_ped/{params.pedigreeID}.rank.txt -p "{params.phenotype}" -o {output.mei_tsv} -cfg config.yaml
        """
