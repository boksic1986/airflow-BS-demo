"""
@author:Rzhang
@license: Apache Licence
@file: WGS_MT.smk
@time: 2021/09/08
@contact: zhiangrian@126.com
@site:
@software: PyCharm
@version 1.0
A WGS MT analysis workflow using mity calling and annotation from clean fastq files
## V1.1
#### update@zhangran,20221120,vt normalize 增加
## V1.2
#### update@zhangran,20230801,更新参考基因组版本为hg38
#### update@zhangran,20230801,更新bam文件为deduped.bam
#### update@zhangran,20230802,跟新mity call reference为hg38
#### update@zhangran,20230802,vcf 的normalize 从vt软件改成bcftools norm
#### update@zhangran,20231220,增加rule mergeMTQC，实现MT QC批次结果的合并
"""

SAMPLES=config["sample"]
SentieonPath=config["bioSoft"]["SentieonPath"]
MTreference=config["reference"]["MTreference"]
reference=config["reference"]["hg38"]["genome"]
mityPath=config["bioSoft"]["mitypath"]
MTAnnotaPath=config["Self-built-Tools"]["SNV_MT"]["MTAnnotaPath"]
bcftoolsPath=config["bioSoft"]["bcftoolsPath"]
vtPath=config["bioSoft"]["vt"]
micomapCfm=config["database"]["micomapCfm"]
MTclinvar=config["database"]["MTclinvar"]
mitomapDisease=config["database"]["mitomapDisease"]
mitomapSNP=config["database"]["mitomapSNP"]
MitImpact=config["database"]["MitImpact"]
mitotip=config["database"]["mitotip"]
MTlocal=config["database"]["MTlocal"]
MTgnomad=config["database"]["MTgnomad"]
MTlocalFreq=config["database"]["MTlocalFreq"]

hmtnotepath=config["bioSoft"]["hmtnote"]
WGScript=config["Self-built-Tools"]["SNV_MT"]["WGScript"]
MTannotationPy=config["Self-built-Tools"]["SNV_MT"]["MTannotationPy"]
mtCombinePl=config["Self-built-Tools"]["SNV_MT"]["mtCombinePl"]
python3Path=config['bioSoft']['python3']
bgzip=config["bioSoft"]["bgzip"]
tabix=config["bioSoft"]["tabix"]
batch=config["batch"]

rule MTall:
    input:
         expand("11_MT/{sample}.mity.flt.vcf.gz", sample=SAMPLES),
         expand("11_MT/{sample}.mity.vt.vcf",sample=SAMPLES),
         expand("11_MT/{sample}.annotated_variants.csv",sample=SAMPLES),
         expand("11_MT/{sample}.hmnote.csv",sample=SAMPLES),
         expand("11_MT/{sample}.mity.flt.txt",sample=SAMPLES),
         expand("11_MT/{mtPedigreeID}.mity.flt.txt", mtPedigreeID=config["mtPedigreeList"]),
         "07_QC/"+batch+".MTQC.txt"
rule mityCallflt:
    input:
         gzvcf="00_PreCalling/{sample}.mity.vcf.gz",
    output:
         fltvcf="11_MT/{sample}.mity.flt.vcf.gz"
    params:
          reference="hg38",
          prefix="{sample}",
    threads:1
    resources:
        qsub_vf=32000
    shell:
          """
          {bcftoolsPath} view -e 'FMT/VAF<0.04' {input.gzvcf}  -Oz -o {output.fltvcf}
          {tabix} -p vcf {output.fltvcf}
          """

rule NorVcf:
    input:
        fltvcf="11_MT/{sample}.mity.flt.vcf.gz",
    output:
        vtvcf="11_MT/{sample}.mity.vt.vcf"
    params:
        genome = reference,
    resources:
        qsub_vf=10000
    threads:4
    shell:
        """
        {bcftoolsPath} norm -c w -m -any -f {params.genome} {input.fltvcf} -Ov -o {output.vtvcf} --threads {threads}
        {bgzip} -c {output.vtvcf} > {output.vtvcf}.gz && {tabix} -p vcf {output.vtvcf}.gz
        """
rule mergeMTQC:
    input:
        expand("07_QC/MT/{sample}.MT.QC.txt", sample=SAMPLES)
    output:
        batchQC="07_QC/"+batch+".MTQC.txt",
    params:
        allQCfiles ="  ".join(expand("07_QC/MT/{sample}.MT.QC.txt", sample=SAMPLES)),
    resources:
        qsub_vf=1000
    threads:1
    shell:
         """
         cat {params.allQCfiles}|awk '!x[$0]++' > {output.batchQC}
         """

rule mityreport:
    input:
        vtvcf="11_MT/{sample}.mity.vt.vcf",
    output:
        mityReportOut="11_MT/{sample}.annotated_variants.csv",
        mityReadme = temp("11_MT/{sample}.annotated_variants.xlsx")
    params:
        mitypath=mityPath,
        prefix="{sample}",
        dir = directory("11_MT/"),
    threads:1
    resources:
        qsub_vf=100000
    shell:
        "{params.mitypath}/mity report --prefix {params.prefix} --out-folder-path {params.dir} {input.vtvcf}.gz"

rule mtAnnot:
    input:
        vtvcf="11_MT/{sample}.mity.vt.vcf",
    output:
        clinvarVcf = temp("11_MT/{sample}.clinvar.vcf.gz"),
        clinvarVcfCsi = temp("11_MT/{sample}.clinvar.vcf.gz.csi"),
        mitomapVcf = temp("11_MT/{sample}.clinvar.mitomap.vcf.gz"),
        mitomapVcfCsi = temp("11_MT/{sample}.clinvar.mitomap.vcf.gz.csi"),
        snpVcf = temp("11_MT/{sample}.clinvar.mitomap.snp.vcf.gz"),
        snpVcfCsi = temp("11_MT/{sample}.clinvar.mitomap.snp.vcf.gz.csi"),
        mitimpactVcf = temp("11_MT/{sample}.clinvar.mitomap.snp.MitImpact.vcf.gz"),
        mitimpactVcfCsi = temp("11_MT/{sample}.clinvar.mitomap.snp.MitImpact.vcf.gz.csi"),
        mitotipVcf = temp("11_MT/{sample}.clinvar.mitomap.snp.MitImpact.mitotip.vcf.gz"),
        mitotipVcfCsi = temp("11_MT/{sample}.clinvar.mitomap.snp.MitImpact.mitotip.vcf.gz.csi"),
        localVcf = temp("11_MT/{sample}.clinvar.mitomap.snp.MitImpact.mitotip.local.vcf.gz"),
        localVcfCsi = temp("11_MT/{sample}.clinvar.mitomap.snp.MitImpact.mitotip.local.vcf.gz.csi"),
        gnomadVcf = temp("11_MT/{sample}.gnomAD.vcf.gz"),
        gnomadVcfCsi = temp("11_MT/{sample}.gnomAD.vcf.gz.csi"),
        localFreqVcf = temp("11_MT/{sample}.localFreq.vcf"),
        hmtnoteVcf = temp("11_MT/{sample}.hmnote.vcf"),
        hmtnoteCsv = "11_MT/{sample}.hmnote.csv"
    threads:1
    resources:
        qsub_vf=100000
    shell:
        """
        {bcftoolsPath} annotate -c 'INFO/CLNREVSTAT,INFO/CLNSIG,INFO/CLNDN,INFO/ClinvarID' -a {MTclinvar} {input.vtvcf}.gz -Oz -o {output.clinvarVcf} && {bcftoolsPath} index {output.clinvarVcf}
        {bcftoolsPath} annotate -c 'INFO/PubmedIDs,INFO/aachange,INFO/Disease,INFO/DiseaseStatus,INFO/HGFL' -a {mitomapDisease} {output.clinvarVcf} -Oz -o {output.mitomapVcf} && {bcftoolsPath} index {output.mitomapVcf}
        {bcftoolsPath} annotate -c 'INFO/AF' -a {mitomapSNP} {output.mitomapVcf} -Oz -o {output.snpVcf} && {bcftoolsPath} index {output.snpVcf}
        {bcftoolsPath} annotate -c 'INFO/APOGEE_score,INFO/APOGEE' -a {MitImpact} {output.snpVcf} -Oz -o {output.mitimpactVcf} && {bcftoolsPath} index {output.mitimpactVcf}
        {bcftoolsPath} annotate -c 'INFO/MitotipScore,INFO/MitotipQuartile' -a {mitotip} {output.mitimpactVcf} -Oz -o {output.mitotipVcf} && {bcftoolsPath} index {output.mitotipVcf}
        {bcftoolsPath} annotate -c 'INFO/LocalSig,INFO/EvidenceList,INFO/Evidence' -a {MTlocal} {output.mitotipVcf} -Oz -o {output.localVcf} && {bcftoolsPath} index {output.localVcf}
        {bcftoolsPath} annotate -c 'INFO/AN,INFO/AC_het,INFO/AC_hom' -a {MTgnomad} {output.localVcf} -Oz -o {output.gnomadVcf} && {bcftoolsPath} index {output.gnomadVcf}
        {bcftoolsPath} annotate -c 'INFO/FreqHet,INFO/FreqHom' -a {MTlocalFreq} {output.gnomadVcf} -Ov -o {output.localFreqVcf}
        {hmtnotepath} annotate {output.localFreqVcf} {output.hmtnoteVcf} --offline --csv
        """

rule mtFlt:
    input:
        hmtnoteCsv="11_MT/{sample}.hmnote.csv",
        mityReportOut="11_MT/{sample}.annotated_variants.csv"
    output:
        mtFlt="11_MT/{sample}.mity.flt.txt"
    threads:1
    resources:
        qsub_vf=100000
    shell:
        "{python3Path}/python3 {MTannotationPy} --cfrmFile {micomapCfm} --hmtnoteCsv {input.hmtnoteCsv} --mityCsv {input.mityReportOut} --output {output.mtFlt}"

rule mtCombine:
    input:
        mt = expand("11_MT/{sample}.mity.flt.txt", sample=config["sample"]),
        rank = expand("08_ped/{batch}.rank.txt", batch=config["batch"])
    output:
        expand("11_MT/{mtPedigreeID}.mity.flt.txt", mtPedigreeID=config["mtPedigreeList"])
    threads:1
    resources:
        qsub_vf=10000
    shell:
        "perl {mtCombinePl} -rank {input.rank}"
