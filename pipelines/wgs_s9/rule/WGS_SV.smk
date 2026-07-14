"""
@author:Rzhang
@license: Apache Licence
@file: WGS_SV.smk
@time: 2021/09/08
@contact: zhiangrian@126.com
@site:
@software: PyCharm
@version 1.0
A WGS SV analysis workflow using lumpy,manta,AnnotSV.
vim config.yaml and set samples list ,extention, hpoID for each sample in the samples list

#V2.0
 ### update@zhangran,增加smmove 运行前 export PATH={lumpyPath}:{params.htslibpath}:{svtyper}:{params.samtoolspath}:$PATH，解决不同运行环境软件不兼容问题
##V3.0
### update@zhangran,202301205,SV的结果进行拆分。SV 注释脚本的使用更新
"""
import re
import os
HPO_CHPO_gene=config["database"]["HPO_CHPO_gene"]
sampleInfoFile=config["sample_info"]
reference=config["reference"]['hg38']["genome"]
smoovePath=config["bioSoft"]["smoovePath"]
SAMPLES=config["sample"]
bgzip=config["bioSoft"]["bgzip"]
tabix=config["bioSoft"]["tabix"]
htslib=os.path.dirname(bgzip).rstrip('/')
svtyper=config["bioSoft"]["svtyperPath"]
samtools=config["bioSoft"]["SamtoolsPath"]
lumpyPath=config["bioSoft"]["lumpyPath"]+"/bin"
VEP104=config['bioSoft']['VEP104']
vep_cache104=config['database']['vepcache104']
annotSV=config["bioSoft"]["annotSV"]
annotsvpath=re.sub(r"bin", "", annotSV)
WGScript=config["Self-built-Tools"]["SNV_MT"]["WGScript"]
bcftoolsPath=config["bioSoft"]["bcftoolsPath"]
bedtools=config["bioSoft"]["bedtools"]
python3Path=config['bioSoft']['python3']
VEPseverity=config['database']['VEPseverityPlus']
geneDisease=config["reference"]["hg38"]["geneDisease"]
geneMIMnumber=config["reference"]["hg38"]["gene_MIMnumber"]
hpoFile=config['database']['HPO_CHPO_gene']
SVsort=config["Self-built-Tools"]["CNV"]["SVsort"]

def get_HPOID():
    term_ID={}
    with open(HPO_CHPO_gene,'r') as Hfp:
        next(Hfp)
        for line in Hfp :
            line = line.strip('\r\n')
            linelist = line.split('\t')
            term=linelist[2]
            id=linelist[4]
            if term in term_ID:
                term_ID[term]=term_ID[term]+","+id
            else:
                term_ID[term]=id
    return term_ID
def get_hpoterm(samplename):
    term_id = get_HPOID()
    HPOlist=[]
    file = open(sampleInfoFile, 'r', encoding='utf-8')
    head = file.readline().strip('\r\n')
    ar = head.split('\t')
    dataindex = ar.index('数据编号')
    hpotermindex = ar.index('英文关键词')
    file.close()
    with open(sampleInfoFile, 'r') as fp:
        next(fp)
        for line in fp:
            line = line.strip('\r\n')
            linelist = line.split('\t')
            sample=linelist[dataindex]
            if linelist[hpotermindex]=="":
                hpoterms=""
            else:
                hpoterm=linelist[hpotermindex].split('|')
                if sample==samplename:
                    for i in hpoterm:
                        if i in term_id:
                            HPOlist.append(term_id[i])
                else:
                    continue
                hpoterms=",".join(HPOlist)
    return hpoterms

rule SVall:
    input:
        #expand("04_SV/a.calling/{sample}-smoove.genotyped.vcf.gz", sample=SAMPLES),
        expand("04_SV/{sample}.SV_CNV.bed", sample=SAMPLES),
        expand("04_SV/{sample}.SV.vcf", sample=SAMPLES),
        expand("04_SV/b.VEP/{sample}.vep.vcf", sample=SAMPLES),
        expand("04_SV/b.VEP/{sample}.vep.tsv", sample=SAMPLES),
        expand("04_SV/c.sort/{sample}.SV.sort.tsv", sample=SAMPLES),

# rule Smooverun:
#     input:
#         Bam = "00_PreCalling/{sample}.deduped.bam",
#     output:
#         outfile="04_SV/a.calling/{sample}-smoove.genotyped.vcf.gz"
#     params:
#         name="{sample}",
#         excludechroms='~^GL,~^HLA,~_random,~^chrUn,~alt,~decoy',
#         htslibpath=htslib,
#         samtoolspath=samtools
#     threads: 1
#     resources:
#         qsub_vf=10000
#     shell:
#          """
#          export PATH={lumpyPath}:{params.htslibpath}:{svtyper}:{params.samtoolspath}:$PATH
#         {smoovePath}/smoove call -x -d -F --name {params.name} --exclude {smoovePath}/exclude.cnvnator_100bp.GRCh38.20170403.bed --fasta {reference} -p {threads} --excludechroms {params.excludechroms} --genotype {input.Bam} --outdir 04_SV/a.calling/
#         """
rule splitCNV:
    input:
        vcf="00_PreCalling/{sample}-smoove.genotyped.vcf.gz"
    output:
        CNVbed="04_SV/{sample}.SV_CNV.bed",
        SVvcf="04_SV/{sample}.SV.vcf",
    threads: 1
    resources:
        qsub_vf=10000
    shell:
        """
        {bcftoolsPath} view -r chr1,chr2,chr3,chr4,chr5,chr6,chr7,chr8,chr9,chr10,chr11,chr12,chr13,chr14,chr15,chr16,chr17,chr18,chr19,chr20,chr21,chr22,chrX,chrY {input.vcf}|{bcftoolsPath} view -i 'ALT="<DUP>"||ALT="<DEL>"||ALT="<DUP:TANDEM>"' | {bcftoolsPath} query -f '%CHROM\t%POS\t%INFO/END\t.\t%INFO/SR\t%INFO/SVTYPE\tLumpy\n' | awk -F '\t' '{{gsub("chr", "", $1); gsub("DUP", "+", $6); gsub("DEL", "-", $6);print $1"\t"$2"\t"$3"\t"$4"\t"$5"\t"$6"\t"$7}}'> {output.CNVbed}
        {bcftoolsPath} view -e 'ALT="<DUP>"||ALT="<DEL>"||ALT="<DUP:TANDEM>"' {input.vcf} > {output.SVvcf}
        """
rule svVep:
    input:
        vcf="04_SV/{sample}.SV.vcf",
    output:
        vepVcf="04_SV/b.VEP/{sample}.vep.vcf",
    threads: 1
    resources:
        qsub_vf=10000
    shell:
        """
        {VEP104}/vep  -i {input.vcf} -o {output.vepVcf} --dir_cache {vep_cache104} --fasta {reference} --buffer_size 5000 --offline --cache  --symbol --canonical --total_length --force --force_overwrite --no_stats --vcf --refseq --use_given_ref --assembly GRCh38 --fork 10 --total_length --no_escape --xref_refseq --pick --failed 1 --gene_phenotype --pubmed  --overlaps --format vcf
        """

rule SVtsv:
    input:
        vepVcf="04_SV/b.VEP/{sample}.vep.vcf",
    output:
        vepTsv="04_SV/b.VEP/{sample}.vep.tsv",
    threads: 1
    resources:
        qsub_vf=10000
    shell:
        """
        bgzip -c {input.vepVcf} >{input.vepVcf}.gz
        tabix -fp vcf {input.vepVcf}.gz
        vcfheader="CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tSVTYPE\tSVLEN\tEND\tSTRANDS"
        header=`grep "##INFO=<ID=CSQ" {input.vepVcf} | sed -e 's/##INFO=<ID=CSQ,Number=.,Type=String,Description=\"Consequence annotations from Ensembl VEP. Format: //' -e 's/|/\t/g' -e 's/\">//'`
        {bcftoolsPath} +split-vep {input.vepVcf} -f '%CHROM\t%POS\t%ID\t%REF\t%ALT\t%QUAL\t%FILTER\t%SVTYPE\t%SVLEN\t%END\t%STRANDS\t%CSQ\t%FORMAT\n' -A tab -d >{output.vepTsv}
        sed -i "1iCHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tSVTYPE\tSVLEN\tEND\tSTRANDS\t $header \tFORMAT\tsample" {output.vepTsv}
        """

# rule SVannotation:
#     input:
#         vepVcf="04_SV/b.VEP/{sample}.vep.vcf",
#     output:
#         annot = "04_SV/c.Annot/{sample}.tsv"
#     params:
#         sample="{sample}",
#         outpath='04_SV/c.Annot',
#         hpo= lambda wildcards : get_hpoterm(wildcards.sample)
#     resources:
#         qsub_vf=10000
#     threads:1
#     shell:
#          """
#         export ANNOTSV={annotsvpath} && {annotSV}/AnnotSV -SVinputFile {input.vepVcf} -genomeBuild GRCh38 -annotationMode full -rankFiltering 3,4,5 -hpo \"{params.hpo}\" -outputFile {output.annot} -outputDir {params.outpath} -bcftools {bcftoolsPath} -bedtools {bedtools}
#         """

rule SVsort:
    input:
         vepTsv="04_SV/b.VEP/{sample}.vep.tsv",
         pedfiles=expand("08_ped/{pedigreeID}.ped",pedigreeID=config["pedigree"])
    output:
         annoSV="04_SV/c.sort/{sample}.SV.anno.tsv",
         sortTsv="04_SV/c.sort/{sample}.SV.sort.tsv"
    resources:
        qsub_vf=10000
    threads:1
    params:
        sample="{sample}",
        phenotype=lambda wildcards:config["phenotype"][wildcards.sample],
        pedigreeID=lambda wildcards: {item[0]: item[1] for item in [(_k.split(':')) for _k in config["sample2pedigree"]]}[wildcards.sample]
    shell:
        """
        {python3Path}/python3 {SVsort} --input {input.vepTsv} --hpoterm "{params.phenotype}" --HPOfile {hpoFile}  --omimFile {geneMIMnumber} --diseaseFile {geneDisease} --VEPseverity {VEPseverity} --outfile {output.annoSV} --sample {params.sample} --ped 08_ped/{params.pedigreeID}.ped --cfg config.yaml
        head -n 1 {output.annoSV}>{output.sortTsv}
        tail -n +2 {output.annoSV} |sort -t $'\\t' -k5,5nr -k6,6nr>> {output.sortTsv}
        """
