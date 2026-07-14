"""
@author:Rzhang
@license: Apache Licence
@file: WGS_SV.smk
@time: 2021/09/08
@contact: zhiangrian@126.com
@site:
@software: PyCharm
@version 1.0
WGS SNV pipeline from gvcf file for multiple samples or single sample

## V2.0
#### update@zhangran,20220920,在VEP注释之前增加了虚拟WES区域的过滤，滤掉深内含子区域的变异
#### update@zhangran,20220920,rule Haplotyper移到pre_sampleinfo_solo.smk中执行
#### update@zhangran,20220921,在VEP注释之前增加了区域过滤使VEP注释的变异数据大大减少，固把VEP注释过程中只注释本批次新出现的变异集再与之前批次已经注释过的变异集合并的代码去掉
#### update@zhangran,20220922,修改rule\WGS_SNV.smk,在rule all 之前添加wildcard_constraints，解决pedigree和sample注释过滤结果不能都以flt.tsv结尾的问题
#### update@zhangran,20221008,把i.CreatePed.V6.2.0.pl改写成适用于WGS样本的脚本4.CreatePed.py，并修改rule createPed中调用的脚本
#### update@zhangran,20221009,增加rule splitVcf,结果用于ROH calling 和ROH画图
## V2.1
#### update@zhangran,20221212,rule solo_SNVannotation_strict，rule solo_SNVannotation_lenient中phenotype 增加双引号，防止特殊字符（“（”）导致的报错
## V2.2
#### update@zhangran,20230210,增加SMA的分析模块,未上临检
## V2.3
#### update@zhangran,20230424,删掉rule SMA
#### update@zhangran ,20230428 add NormalizeVcf ,delete rule vtNormalize
## V3.0
#### update@zhangran,20230726更新bcftools norm 命令，添加-c w
#### update@zhangran,20230731,更新rule qualityFlt，防止漏掉白名单中的位点
## V3.1
#### update@zhangran,20230925,VEP 注释参数--mane --mane_select  --variant_class --gene_phenotype --pubmed去掉
##V3.1.2
#### update@zhangran,20240102,peddy增加参数 --sites hg38
#### update@zhangran,20240102, QC中增加chrM所占比例指标
#### update@zhangran,20240131, 新增{bcftools} view -e 'CHROM~"M" 防止白名单中的MT的变异被捞回来
#### update@zhangran,20240201, WGS_SNV.smk 中rule vep 中spliceAI 文件替换，cutoff由0.5 变成0.2

"""
import os
import re
import pandas as pd
sampleInfoFile=config["sample_info"]
SAMPLES=config["sample"]
PEDIGREE=config["pedigree"]
batch=config["batch"]
#software
WGScript=config["Self-built-Tools"]["SNV_MT"]["WGScript"]
Rscript=config["bioSoft"]["Rscript"]
SentieonPath=config["bioSoft"]["SentieonPath"]
bgzip=config["bioSoft"]["bgzip"]
tabix=config["bioSoft"]["tabix"]
bcftools=config["bioSoft"]["bcftoolsPath"]
bcftoolsPath=os.path.dirname(bcftools)
sceVCFPath=config["bioSoft"]["sceVCF"]
vcfannotate=config["bioSoft"]["vcfannotate"]
plotQC=config["Self-built-Tools"]["other"]["plotQC"]
bedtools=config['bioSoft']['bedtools']
VEP=config['bioSoft']['VEP']
vep_cache=config['database']['vepcache']
vepPlugin=config['database']['vepPlugin']
python3Path=config['bioSoft']['python3']
peddy=config['bioSoft']['peddy']
slivar=config['bioSoft']['slivar']
pandepth=config["bioSoft"]["pandepth"]
#self-built
createPed=config["Self-built-Tools"]["SNV_MT"]["createPed"]
slivarPl=config["Self-built-Tools"]["SNV_MT"]["slivarPl"]
splitPl=config["Self-built-Tools"]["SNV_MT"]["splitPl"]
SNVannotation=config["Self-built-Tools"]["SNV_MT"]["SNVannotation"]
dpCorrectPy=config["Self-built-Tools"]["SNV_MT"]["dpCorrectPy"]
#dataset
reference=config["reference"]['hg38']["genome"]
known_Mills_indels=config["reference"]['hg38']["known_Mills_indels"]
known_1000G_indels=config["reference"]['hg38']["known_1000G_indels"]
dbsnp=config["reference"]['hg38']["dbsnp"]
genebed=config["reference"]['hg38']['geneBed']
virtualWESBed=config['reference']['hg38']['virtualWESBed']
whitelistV1=config["reference"]['hg38']['whitelistV1']
whitelistV4=config["reference"]['hg38']['whitelistV4']
blacklist=config["reference"]['hg38']['blacklist']
localMaf=config["reference"]['hg38']['localMaf']
spliceai_SNV = config['database']['spliceai_SNV']
spliceai_Indel = config['database']['spliceai_Indel']
dbNSFP = config['database']['dbNSFP']
dbscSNV = config['database']['dbscSNV']
clinvar = config['database']['clinvar']
HGMD = config['database']['HGMD']
intervar = config['database']['intervar']
LocalVarDB = config['database']['LocalVarDB']
gnomad_exomes = config['database']['gnomad_exomes']
gnomad_genomes = config['database']['gnomad_genomes']
simpleRepeat = config['database']['simpleRepeat']
genmap_100mer = config['database']['genmap_100mer']


wildcard_constraints:
    sample= '|'.join([re.escape(x) for x in SAMPLES]),
    pedigree= '|'.join([re.escape(x) for x in PEDIGREE])

def getsampleqc(sampleN,bamQCfile,mappingQCFile,bamchromStat,contaminationFile,MTQCfile,outFile):
    sceVCFO=pd.read_csv(contaminationFile,sep='\t',header='infer')
    sampleCHARR=sceVCFO.loc[sceVCFO['#SAMPLE']==sampleN,'CHARR'].tolist()[0]
    sampleINCONSISTENT=sceVCFO.loc[sceVCFO['#SAMPLE']==sampleN,'INCONSISTENT_AB_HET_RATE'].tolist()[0]
    if sampleCHARR>0.03 and sampleINCONSISTENT>0.15 :
        contamination='FAIL'
    elif sampleCHARR>0.02 and sampleINCONSISTENT>0.1 :
        contamination='WARNING'
    else:
        contamination='PASS'
    mappingQC = pd.read_csv(mappingQCFile)
    sampleid=sampleN+'-R1.fq.gz'
    print(sampleid)
    SEX1=mappingQC.loc[mappingQC['Sample']==sampleid,'Gender'].tolist()[0]
    tsv_file = pd.read_csv(bamchromStat,sep='\t')
    chromeList=['chrM','chr1','chr2','chr3','chr4','chr5','chr6','chr7','chr8','chr9','chr10','chr11','chr12','chr13','chr14','chr15','chr16','chr17','chr18','chr19','chr20','chr21','chr22','chrX','chrY']
    chromeReadlist=tsv_file.loc[tsv_file['chrom'].isin(chromeList),]['ReadCount'].tolist()
    sumreadsCount=sum(chromeReadlist)
    chromeRatio='\t'.join(str(round(i/sumreadsCount*100,3)) for i in tsv_file.loc[tsv_file['chrom'].isin(chromeList),]['ReadCount'].tolist())
    chrXReadCount=tsv_file.loc[tsv_file['chrom']=='chrX','ReadCount'].tolist()[0]
    chrYReadcount=tsv_file.loc[tsv_file['chrom']=='chrY','ReadCount'].tolist()[0]
    chrX_chrY=int(chrXReadCount)/int(chrYReadcount)
    chrX_total=float(chrXReadCount)/float(sumreadsCount)
    ## read sample sex info from sampleinfo.txt input by user
    sampleSex={}
    sampleName={}
    ifPass="Yes"
    file = open(sampleInfoFile, 'r', encoding='utf-8')
    head = file.readline().strip('\r\n')
    ar = head.split('\t')
    dataindex = ar.index('数据编号')
    sexindex = ar.index('性别')
    nameindex = ar.index('姓名')
    relationindex = ar.index('家系关系')
    itemindex = ar.index('项目编号')
    file.close()
    with open(sampleInfoFile, 'r', encoding = "utf-8") as Hfp:
        next(Hfp)
        for line in Hfp:
            line = line.strip('\r\n')
            linelist = line.split('\t')
            dataID=linelist[dataindex]
            sex = linelist[sexindex]
            name = linelist[nameindex]
            relation = linelist[relationindex]
            itemID = linelist[itemindex]
            if dataID==sampleN:
                break
            sampleSex[dataID]=sex
            sampleName[dataID]=name
    SEX=sex
    if SEX=='男': newSEX='M'
    elif SEX=='女': newSEX='F'
    else : newSEX='ND'
    equal="Yes"
    if SEX1!=newSEX: equal='No'
    MTQC=pd.read_csv(MTQCfile,sep='\t',header='infer')
    MTdepth=MTQC.loc[MTQC['Sample']==sampleN,'Average depth'].tolist()[0]
    qcstatf= pd.read_csv(bamQCfile,sep='\t')
    qcstatf.insert(qcstatf.columns.get_loc('Mean_Depth')+1, 'MT_Average_Depth', MTdepth)
    column_names = qcstatf.columns.tolist()
    qcvaluelist=qcstatf.iloc[0].tolist()
    qchead= '\t'.join(column_names)
    qcvalue= '\t'.join(str(x) for x in qcvaluelist)
    rawReadCount=qcstatf.loc[0, 'Raw_reads']
    dupReadCount=qcstatf.loc[0, 'Duplicated_reads']
    duplicated=re.sub(r'%', '',qcstatf.loc[0, 'Duplicated_reads%'])
    cleanQ30=re.sub(r'%', '',qcstatf.loc[0, 'Clean_Q30%'])
    cov10X=re.sub(r'%', '',qcstatf.loc[0, '>=10X'])
    cov20X=re.sub(r'%', '',qcstatf.loc[0, '>=20X'])
    meanDepth=qcstatf.loc[0, 'Mean_Depth']
    fold80=qcstatf.loc[0, 'FOLD_80_BASE_PENALTY']
    if equal=='No':ifPass="性别不符"
    if itemID in ['Q0079','Q0080','Q0081','Q0082'] and float(cleanQ30)<=85:
        ifPass=ifPass+';Q30<=85%'
    elif float(cleanQ30)<85:
        ifPass=ifPass+';Q30<85%'
    if itemID in ['Q0079','Q0080','Q0081','Q0082'] and float(meanDepth)<30:
        ifPass=ifPass+';平均覆盖低于30'
    if itemID not in ['Q0079','Q0080','Q0081','Q0082'] and relation=="先证者" and float(meanDepth)<30:
        ifPass=ifPass+';先证者平均覆盖低于30'
    if itemID not in ['Q0079','Q0080','Q0081','Q0082'] and relation!="先证者" and float(meanDepth)<20:
        ifPass=ifPass+';非先证者平均覆盖低于20'
    if float(fold80)>2:
        ifPass=ifPass+';fold80大于2'
    if itemID in ['Q0079','Q0080','Q0081','Q0082']:
        if (int(rawReadCount) - int(dupReadCount))*150 <= 90000000000:ifPass=ifPass+'测序数据量<=90G'
        if float(duplicated)>=10:ifPass=ifPass+';数据冗余度>=10%'
        if float(cov10X)<=98:ifPass=ifPass+';深度10X以上序列占比<=98%'
        if float(cov20X)<=90:ifPass=ifPass+';深度20X以上序列占比<=90%'
    ifPass=ifPass.lstrip(';')
    f2 = open(outFile, 'w')
    f2.write('Name\tSample_ID\t是否通过质控\t'+qchead+'\t'+'chr1%\tchr2%\tchr3%\tchr4%\tchr5%\tchr6%\tchr7%\tchr8%\tchr9%\tchr10%\tchr11%\tchr12%\tchr13%\tchr14%\tchr15%\tchr16%\tchr17%\tchr18%\tchr19%\tchr20%\tchr21%\tchr22%\tchrX%\tchrY%\tchrM%\tchrX/Total\tchrX/chrY\t预测性别\t登记性别\t性别是否符合\tCHARR\tINCONSISTENT_AB_HET_RATE\tcontamination\n')
    f2.write(name+'\t'+sampleN+'\t'+ifPass+'\t'+qcvalue+'\t'+chromeRatio+'\t'+str(chrX_total)+'\t'+str(chrX_chrY)+'\t'+SEX1+'\t'+newSEX+'\t'+equal+'\t'+str(sampleCHARR)+'\t'+str(sampleINCONSISTENT)+'\t'+contamination+'\n')

rule SNVall:
    input:
        "01_SNV/"+batch+".raw.vcf",
        "01_SNV/"+batch+".raw.vcf.gz",
        "01_SNV/"+batch+".normalize.vcf.gz",
        "01_SNV/"+batch+".qual.flt.vcf.gz",
        "01_SNV/"+batch+".region.flt.vcf",
        "01_SNV/"+batch+".region.flt.vcf.gz",
        "01_SNV/"+batch+".vaf.flt.vcf",
        "01_SNV/"+batch+".vaf.gz",
        "01_SNV/"+batch+".vep.vcf.gz",
        "01_SNV/"+batch+".lenient.flt.vcf",
        "01_SNV/"+batch+".flt.vcf",
        "01_SNV/"+batch+".vepLocation.lenient.flt.vcf.gz",
        "01_SNV/"+batch+".vepLocation.lenient.flt.tsv",
        "01_SNV/"+batch+".vepLocation.flt.vcf.gz",
        "01_SNV/"+batch+".vepLocation.flt.tsv",
        "08_ped/"+batch+".ped",
        "08_ped/"+batch+".rank.txt",
        expand("01_SNV/{sample}.vcf",sample=SAMPLES),
        expand("01_SNV/{sample}.raw.vcf.gz",sample=SAMPLES),
        expand("01_SNV/{sample}.vaf",sample=SAMPLES),
        expand("01_SNV/{sample}.vaf.bedGraph.gz",sample=SAMPLES),
        expand("08_ped/{pedigree}.ped",pedigree=config["pedigree"]),
        expand("08_ped/{pedigree}.rank.txt",pedigree=config["pedigree"]),
        expand("02_split/{sample}.split.tsv",sample=SAMPLES),
        expand("02_split/{sample}.split.flt.tsv",sample=SAMPLES),
        expand("02_split/{trioID}.split.trio.vcf",trioID=config["trio"]),
        expand("02_split/{pedigree}.split.fam.vcf",pedigree=config["pedigree"]),
        expand("02_split/{pedigree}.split.flt.fam.vcf",pedigree=config["pedigree"]),
        expand("02_split/{pedigree}.slivar.tsv",pedigree=config["pedigree"]),
        expand("02_split/{pedigree}.flt.slivar.tsv",pedigree=config["pedigree"]),
        expand("01_SNV/{pedigree}.flt.tsv",pedigree=config["pedigree"]),
        expand("01_SNV/{sample}.flt.tsv",sample=SAMPLES),
        expand("01_SNV/{pedigree}.verbose.tsv",pedigree=config["pedigree"]),
        expand("01_SNV/{sample}.verbose.tsv",sample=SAMPLES),

rule GVCFtyper:
    input:
         expand("00_PreCalling/{sample}.g.vcf.gz", sample=SAMPLES)
    output:
         allRawvcf=expand("01_SNV/{batch}.raw.vcf",batch=config["batch"]),
         allRawvcfgz=expand("01_SNV/{batch}.raw.vcf.gz",batch=config["batch"]),
    params:
         sentieonPath = SentieonPath,
         genome = reference,
         parms =" -v ".join(expand("00_PreCalling/{sample}.g.vcf.gz", sample=SAMPLES)),
         dbsnp=dbsnp,
         bgzipPath=bgzip,
         tabixPath=tabix
    resources:
        qsub_vf=10000
    threads:8
    shell:
        """
         export SENTIEON_LICENSE=/bi/software/Sentieon/Zhejiang_Biosan_Biotechnology_Co._LTD_cluster.lic
         export MALLOC_CONF=lg_dirty_mult:-1
        {params.sentieonPath}/sentieon driver -r {params.genome} -t {threads} --algo GVCFtyper -v {params.parms} -d {params.dbsnp} --emit_conf=10 --call_conf=10 {output.allRawvcf}
        {params.bgzipPath} -@ 8 -c {output.allRawvcf} > {output.allRawvcfgz}
        {params.tabixPath} -fp vcf {output.allRawvcfgz}
        """

rule NormalizeVcf:
    input:
        vcf = "01_SNV/{batch}.raw.vcf.gz"
    output:
        tagVcf = temp("01_SNV/{batch}.normalize.tmp.vcf.gz"),
        normVcf = "01_SNV/{batch}.normalize.vcf.gz"
    params:
        genome = reference,
    resources:
        qsub_vf=20000
    threads:12
    shell:
        """
        {bcftools} +fill-tags {input.vcf} -- -t 'FORMAT/ADS:1=int(smpl_sum(FORMAT/AD)-FORMAT/AD[*:0])' | {bcftools} view -Oz -o {output.tagVcf}
        {bcftools} norm -c w -m -any -f {params.genome} {output.tagVcf} -Oz -o {output.normVcf} --threads {threads} && tabix -fp vcf {output.normVcf}
        """

rule qualityFlt:
    input:
        normalizeVcf = "01_SNV/"+batch+".normalize.vcf.gz"
    output:
        qualvcfgz="01_SNV/"+batch+".qual.flt.vcf.gz",
        lowQualityVcf = "01_SNV/"+batch+".low_qual.vcf.gz",
        fltLowQualityVcf = "01_SNV/"+batch+".flt_low_qual.vcf.gz"
    resources:
        qsub_vf=10000
    threads:8
    shell:
        """
        {bcftools} view -i 'CHROM~"M" || CHROM~"GL" || CHROM~"HLA" || CHROM~"Un" || CHROM~"alt" ||  CHROM~"random" || QUAL<20 || MAX(FMT/GQ)<20 || MAX(FMT/DP)<5 || AVG(FMT/DP)<3' {input.normalizeVcf} -Oz -o {output.lowQualityVcf} && tabix -fp vcf {output.lowQualityVcf}
        {bcftools} isec -n~10 -c none -w 1 {output.lowQualityVcf} {whitelistV4} -Oz -o {output.fltLowQualityVcf} && tabix -fp vcf {output.fltLowQualityVcf}
        {bcftools} isec -n~10 -c none -w 1 {input.normalizeVcf} {output.fltLowQualityVcf} | {bcftools} view -e 'CHROM~"M"' | {vcfannotate} -b {genebed} -k gene /dev/stdin | bgzip -@ 8 -c > {output.qualvcfgz}  && tabix -fp vcf {output.qualvcfgz}
        """

rule virtualWES:
    input:qualvcf="01_SNV/"+batch+".qual.flt.vcf.gz"
    output:
         region=temp("01_SNV/"+batch+".WESregion.vcf"),
         regiongz=temp("01_SNV/"+batch+".WESregion.vcf.gz"),
         outsideRegion=temp("01_SNV/"+batch+".withOutRegion.vcf"),
         outsideRegiongz=temp("01_SNV/"+batch+".withOutRegion.vcf.gz"),
         outsideWhite=temp("01_SNV/"+batch+".withOutRegionInWhite.vcf.gz"),
         regionFlt="01_SNV/"+batch+".region.flt.vcf",
         regionFltgz="01_SNV/"+batch+".region.flt.vcf.gz",
    resources:
        qsub_vf=10000
    threads:8
    shell:
        """
        {bedtools} intersect -a {input.qualvcf} -b {virtualWESBed} -wa -header >{output.region} && {bgzip} -@ 8 -c {output.region} > {output.regiongz} && {tabix} -fp vcf {output.regiongz}  ## call到并且在虚拟WES区域的变异
        {bedtools} intersect -a {input.qualvcf} -b {virtualWESBed} -v -wa -header >{output.outsideRegion} &&  {bgzip} -@ 8  -c {output.outsideRegion} > {output.outsideRegiongz} && {tabix} -fp vcf {output.outsideRegiongz} ## call到但是在区域外的变异
        {bcftools} isec -n 2 -c none -w 1 {output.outsideRegiongz} {whitelistV1} -Oz -o {output.outsideWhite} && tabix -fp vcf {output.outsideWhite}  # 在区域外但是在白名单中的变异
        {bcftools} concat {output.regiongz} {output.outsideWhite} -a -Ov -o {output.regionFlt}
        {bgzip} -@ 8 -c {output.regionFlt} > {output.regionFltgz} && {tabix} -fp vcf {output.regionFltgz}
        """

rule vep:
    input:
        regionFlt="01_SNV/"+batch+".region.flt.vcf",
    output:
        vepVcfGz="01_SNV/{batch}.vep.vcf.gz",
    params:
        genome = reference,
    resources:
        qsub_vf=10000
    threads:1
    shell:
        """
        {VEP}/vep  -i {input.regionFlt} -o {output.vepVcfGz} --offline --cache --hgvs --hgvsg --symbol --canonical --total_length --force --vcf --compress_output bgzip  --refseq --use_given_ref --assembly GRCh38 --fasta {params.genome} \
        --dir_cache {vep_cache} \
        --dir_plugins {vepPlugin} \
        --plugin SpliceAI,snv={spliceai_SNV},indel={spliceai_Indel},cutoff=0.2 \
        --plugin dbNSFP,{dbNSFP},SIFT_pred,Polyphen2_HDIV_pred,Polyphen2_HVAR_pred,LRT_pred,AlphaMissense_pred,MutationAssessor_pred,FATHMM_pred,PROVEAN_pred,MetaSVM_pred,MetaLR_pred,REVEL_score \
        --plugin dbscSNV,{dbscSNV} \
        --custom {clinvar},clinvar,vcf,exact,0,CLNREVSTAT,CLNSIG,ClinicalSignificance,Submitter,CollectionMethod,CLNDN \
        --custom {HGMD},HGMD,vcf,exact,0,Rank_Score,Class,Pubmed \
        --custom {intervar},intervar,vcf,exact,0,SIG \
        --custom {LocalVarDB},local_path,vcf,exact,0,Pathogenicity,EvidenceList,Evidence \
        --custom {gnomad_exomes},GnomADExomes,vcf,exact,0,controls_AC,controls_AN,controls_AF,controls_AC_eas,controls_AN_eas,controls_AF_eas,controls_nhomalt,controls_nhomalt_male,controls_nhomalt_female \
        --custom {gnomad_genomes},GnomADGenomes,vcf,exact,0,controls_AC,controls_AN,controls_AF,controls_AC_eas,controls_AN_eas,controls_AF_eas,controls_nhomalt,controls_nhomalt_male,controls_nhomalt_female  \
        --custom {simpleRepeat},Repeat,bed,overlap,0 \
        --custom {genmap_100mer},Mapability,bed,overlap,0 \
        --custom {localMaf},LocalMAF,vcf,exact,0,AC,AN,AF \
        --fork 16 --no_escape --xref_refseq --failed 1
        {tabix} -fp vcf {output.vepVcfGz}
        """

rule intergenicFlt:
    input:
        vepVcfGz="01_SNV/"+batch+".vep.vcf.gz",
    output:
        lenient = "01_SNV/"+batch+".lenient.flt.vcf",
        intergenic = temp("01_SNV/"+batch+".tmp.intergenic.vcf.gz"),
        intergenicTbi = temp("01_SNV/"+batch+".tmp.intergenic.vcf.gz.tbi"),
        intergenic_flt = temp("01_SNV/"+batch+".tmp.intergenicFlt.vcf.gz"),
        intergenicFltTbi = temp("01_SNV/"+batch+".tmp.intergenicFlt.vcf.gz.tbi")
    resources:
        qsub_vf=10000
    threads:8
    run:
        shell('{bcftools} +split-vep {input.vepVcfGz} -f \'%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\n\' -A tab -s worst -d | awk -F "\\t" \'$9==\"intergenic_variant\" || $9==\"downstream_gene_variant\" || $9==\"upstream_gene_variant\"\' | awk -F "\\t" \'BEGIN{{OFS=\"\\t\"}}{{print $1,$2,$3,$4,$5,$6,$7,\"WORSTIMPACT=intergenic_variant\"}}\'| sed \'1i##fileformat=VCFv4.2\\n##INFO=<ID=WORSTIMPACT,Number=.,Type=String,Description=\"\">\\n#CHROM\\tPOS\\tID\\tREF\\tALT\\tQUAL\\tFILTER\\tINFO\' | {bgzip} -@ {threads} -c > {output.intergenic} && {tabix} -fp vcf {output.intergenic}')
        shell('{bcftools} isec -n~10 -c none -w 1 {output.intergenic} {whitelistV1} -Oz -o {output.intergenic_flt} && tabix -fp vcf {output.intergenic_flt}')
        shell('{bcftools} isec -n~10 -c none -w 1 {input.vepVcfGz} {output.intergenic_flt} -Ov -o {output.lenient}')

rule vepLenient:
    input:
        lenient = "01_SNV/"+batch+".lenient.flt.vcf"
    output:
        vepLenientgz="01_SNV/{batch}.vepLocation.lenient.flt.vcf.gz",
        vepLenienttsv="01_SNV/{batch}.vepLocation.lenient.flt.tsv"
    params:
        genome = reference,
    resources:
        qsub_vf=10000
    threads:1
    shell:
        """
        {VEP}/vep  -i {input.lenient} -o {output.vepLenientgz} --offline --cache --force --vcf --compress_output bgzip --refseq --use_given_ref --assembly GRCh38 --fasta {params.genome} \
        --dir_cache {vep_cache} --fork 16 --no_escape --xref_refseq --failed 1 --shift_genomic 1 --shift_3prime 1 --fields "Location,Allele,SYMBOL,Consequence,Feature,Gene"
        {tabix} -fp vcf {output.vepLenientgz}
        {bcftools} +split-vep {output.vepLenientgz} -f \'%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\n\' -A tab -d > {output.vepLenienttsv}
        """

rule blacklistCsqFlt:
    input:
        vepvcfGz="01_SNV/"+batch+".vep.vcf.gz",
    output:
        strictFlt = "01_SNV/"+batch+".flt.vcf",
        blacklistFltVcf = temp("01_SNV/"+batch+".tmp.blacklist.flt.vcf"),
        blacklistFltVcfGz = temp("01_SNV/"+batch+".tmp.blacklist.flt.vcf.gz"),
        blacklistFltTbi = temp("01_SNV/"+batch+".tmp.blacklist.flt.vcf.gz.tbi"),
        modifierVcfGz = temp("01_SNV/"+batch+".tmp.modifier.vcf.gz"),
        modifierTbi = temp("01_SNV/"+batch+".tmp.modifier.vcf.gz.tbi"),
        modifierFltVcfGz = temp("01_SNV/"+batch+".tmp.modifier.flt.vcf.gz"),
        modifierFltTbi = temp("01_SNV/"+batch+".tmp.modifier.flt.vcf.gz.tbi")
    resources:
        qsub_vf=10000
    threads:1
    run:
        shell('{bcftools} isec -n~10 -c none -w 1 {input.vepvcfGz} {blacklist} -Ov -o {output.blacklistFltVcf} && {bgzip} -c {output.blacklistFltVcf} > {output.blacklistFltVcfGz} && {tabix} -fp vcf {output.blacklistFltVcfGz}')  ##去掉黑名单
        shell('{bcftools} +split-vep {input.vepvcfGz} -f \'%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\n\' -A tab -s worst -d | awk -F "\\t" \'$10==\"MODIFIER\"\' | awk -F \"\\t\" \'BEGIN{{OFS=\"\\t\"}}{{print $1,$2,$3,$4,$5,$6,$7,\"WORSTIMPACT=MODIFIER\"}}\' | sed \'1i##fileformat=VCFv4.2\\n##INFO=<ID=WORSTIMPACT,Number=.,Type=String,Description=\"\">\\n#CHROM\\tPOS\\tID\\tREF\\tALT\\tQUAL\\tFILTER\\tINFO\' | {bgzip} -c > {output.modifierVcfGz} && {tabix} -fp vcf {output.modifierVcfGz}')
        #不在白名单中的modifier
        shell('{bcftools} isec -n~10 -c none -w 1 {output.modifierVcfGz} {whitelistV1} -Oz -o {output.modifierFltVcfGz} && tabix -fp vcf {output.modifierFltVcfGz}')
        shell('{bcftools} isec -n~10 -c none -w 1 {output.blacklistFltVcfGz} {output.modifierFltVcfGz} -Ov -o {output.strictFlt}')

rule vepFlt:
    input:
        flt = "01_SNV/"+batch+".flt.vcf"
    output:
        vepFltgz="01_SNV/{batch}.vepLocation.flt.vcf.gz",
        vepFlttsv="01_SNV/{batch}.vepLocation.flt.tsv"
    params:
        genome = reference,
    resources:
        qsub_vf=10000
    threads:1
    shell:
        """
        {VEP}/vep  -i {input.flt} -o {output.vepFltgz} --offline --cache --force --vcf --compress_output bgzip --refseq --use_given_ref --assembly GRCh38 --fasta {params.genome} \
        --dir_cache {vep_cache} --fork 16 --no_escape --xref_refseq --failed 1 --shift_genomic 1 --shift_3prime 1 --fields "Location,Allele,SYMBOL,Consequence,Feature,Gene"
        {tabix} -fp vcf {output.vepFltgz}
        {bcftools} +split-vep {output.vepFltgz} -f \'%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\n\' -A tab -d > {output.vepFlttsv}
        """

rule createPed:
    input:
        sampleInfo=sampleInfoFile,
        gender = "07_QC/"+batch+".gender.txt",
    output:
          pedfile = "08_ped/"+batch+".ped",
          sampleRank="08_ped/"+batch+".rank.txt",
          famPed = expand("08_ped/{pedigreeID}.ped",pedigreeID=config["pedigree"]),
          famRank = expand("08_ped/{pedigreeID}.rank.txt",pedigreeID=config["pedigree"])
    params:
          dir='08_ped'
    resources:
        qsub_vf=100
    threads:1
    shell:
         "{python3Path}/python3 {createPed} --outpath {params.dir} --outbatch {batch} --sampleInfo {input.sampleInfo} --gender {input.gender}"

rule solo_split_lenient:
    input:
        lenient = "01_SNV/"+batch+".lenient.flt.vcf",
    output:
        tsv = "02_split/{sample}.split.tsv"
    resources:
        qsub_vf=10000
    threads:1
    params: samplename="{sample}"
    shell:
        'perl {splitPl} -vcf {input.lenient} -i {params.samplename} -bcftools {bcftools}'

rule solo_split_strict:
    input:
        vcf = "01_SNV/"+batch+".flt.vcf",
    output:
        tsv = "02_split/{sample}.split.flt.tsv"
    resources:
        qsub_vf=10000
    threads:1
    params: samplename="{sample}"
    shell:
        'perl {splitPl} -vcf {input.vcf} -i {params.samplename} -bcftools {bcftools}'

rule trio_split:
    input:
        rank = "08_ped/{trioID}.rank.txt",
        vcf = "01_SNV/"+batch+".region.flt.vcf",
    output:
        vcf = "02_split/{trioID}.split.trio.vcf"
    resources:
        qsub_vf=10000
    threads:1
    params: trio="{trioID}"
    run:
        prefix = params.trio+'.trio'
        shell('perl {splitPl} -rank {input.rank} -vcf {input.vcf} -i {prefix} -bcftools {bcftools}')

rule fam_split_lenient:
    input:
        rank = "08_ped/{pedigree}.rank.txt",
        vcf = "01_SNV/"+batch+".lenient.flt.vcf"
    output:
        vcf = temp("02_split/{pedigree}.split.fam.raw.vcf")
    resources:
        qsub_vf=10000
    threads:1
    run:
        import re
        famPrefix = re.sub(r'.split.fam.raw.vcf','',output.vcf)
        famPrefix = re.sub(r'02_split/','',famPrefix)
        fprefix = famPrefix + '.fam'
        shell('perl {splitPl} -rank {input.rank} -vcf {input.vcf} -i {fprefix} -bcftools {bcftools}')

rule fam_split_lenient_correct:
    input:
        vcf = "02_split/{pedigree}.split.fam.raw.vcf",
        cram = expand("00_PreCalling/{sample}.deduped.cram",sample=SAMPLES),
        crai = expand("00_PreCalling/{sample}.deduped.cram.crai",sample=SAMPLES)
    output:
        vcf = "02_split/{pedigree}.split.fam.vcf"
    resources:
        qsub_vf=20000
    threads:8
    params:
        cram_dir = '00_PreCalling'
    shell:
        """
        {python3Path}/python3 {dpCorrectPy} -i {input.vcf} -o {output.vcf} -c {params.cram_dir} -r {reference} --bcftools {bcftools} --pandepth {pandepth}
        """

rule fam_split_strict:
    input:
        rank = "08_ped/{pedigree}.rank.txt",
        vcf = "01_SNV/"+batch+".flt.vcf",
    output:
        vcf = temp("02_split/{pedigree}.split.flt.fam.raw.vcf")
    resources:
        qsub_vf = 10000
    threads:1
    run:
        import re
        famPrefix = re.sub(r'.split.flt.fam.raw.vcf','',output.vcf)
        famPrefix = re.sub(r'02_split/','',famPrefix)
        faprefix = famPrefix + '.fam'
        shell('perl {splitPl} -rank {input.rank} -vcf {input.vcf} -i {faprefix} -bcftools {bcftools}')

rule fam_split_strict_correct:
    input:
        vcf = "02_split/{pedigree}.split.flt.fam.raw.vcf",
        cram = expand("00_PreCalling/{sample}.deduped.cram",sample=SAMPLES),
        crai = expand("00_PreCalling/{sample}.deduped.cram.crai",sample=SAMPLES)
    output:
        vcf = "02_split/{pedigree}.split.flt.fam.vcf"
    resources:
        qsub_vf=20000
    threads:8
    params:
        cram_dir = '00_PreCalling'
    shell:
        """
        {python3Path}/python3 {dpCorrectPy} -i {input.vcf} -o {output.vcf} -c {params.cram_dir} -r {reference} --bcftools {bcftools} --pandepth {pandepth}
        """

rule fam_slivar_lenient:
    input:
        ped = "08_ped/{pedigree}.ped",
        flt_vcf = "02_split/{pedigree}.split.fam.vcf"
    output:
        vcf = "02_split/{pedigree}.slivar.vcf",
        tsv = "02_split/{pedigree}.slivar.tsv"
    resources:
        qsub_vf=10000
    threads:1
    shell:
        "perl {slivarPl} -ped {input.ped} -i {input.flt_vcf} -v {output.vcf} -t {output.tsv} -bcftools {bcftools} -slivar {slivar}"

rule fam_slivar_strict:
    input:
        ped = "08_ped/{pedigree}.ped",
        flt_vcf = "02_split/{pedigree}.split.flt.fam.vcf"
    output:
        vcf = "02_split/{pedigree}.flt.slivar.vcf",
        tsv = "02_split/{pedigree}.flt.slivar.tsv"
    resources:
        qsub_vf=10000
    threads:1
    shell:
        "perl {slivarPl} -ped {input.ped} -i {input.flt_vcf} -v {output.vcf} -t {output.tsv} -bcftools {bcftools} -slivar {slivar}"


rule fam_SNVannotation_strict:
    input:
        rank = "08_ped/{pedigree}.rank.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.flt.tsv",
        slivar = "02_split/{pedigree}.flt.slivar.tsv"
    output:
        flt = "01_SNV/{pedigree}.flt.tsv"
    resources:
        qsub_vf=10000
    params: SNVannotation=SNVannotation
    threads:1
    shell:
        "perl {params.SNVannotation} -rank {input.rank} -i {input.slivar} -o {output.flt} -cfg config.yaml"

rule fam_SNVannotation_lenient:
    input:
        rank = "08_ped/{pedigree}.rank.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.lenient.flt.tsv",
        slivar = "02_split/{pedigree}.slivar.tsv"
    output:
        verbose = "01_SNV/{pedigree}.verbose.tsv"
    resources:
        qsub_vf=10000
    threads:1
    params: SNVannotation=SNVannotation
    shell:
        "perl {params.SNVannotation} -rank {input.rank} -i {input.slivar} -o {output.verbose} -cfg config.yaml"

rule solo_SNVannotation_strict:
    input:
        gender = "07_QC/"+batch+".gender.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.flt.tsv",
        split = "02_split/{sample}.split.flt.tsv"
    output:
        outflt = "01_SNV/{sample}.flt.tsv"
    resources:
        qsub_vf=10000
    params:
        sampename="{sample}",
        SNVannotation=SNVannotation
    threads:1
    run:
        samplePrefix = params.sampename
        print(samplePrefix)
        phenotype =config["phenotype"][samplePrefix]
        infile = open(input.gender, "r")
        filelines = infile.readlines()
        sample2gender = {}
        gender = 'ND'
        for line in filelines:
            line = line.strip()
            sample2gender[line.split(',')[0]]=line.split(',')[1]
        print(sample2gender)
        if samplePrefix in sample2gender:
            gender = sample2gender[samplePrefix]
        print('perl {params.SNVannotation} -g {gender} -p "{phenotype}" -i {input.split} -o {output.outflt} -cfg config.yaml')
        shell('perl {params.SNVannotation} -g {gender} -p "{phenotype}" -i {input.split} -o {output.outflt} -cfg config.yaml')

rule solo_SNVannotation_lenient:
    input:
        gender = "07_QC/"+batch+".gender.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.lenient.flt.tsv",
        split = "02_split/{sample}.split.tsv"
    output:
        verbose = "01_SNV/{sample}.verbose.tsv"
    params:
        sampename="{sample}",
        SNVannotation=SNVannotation
    resources:
        qsub_vf=10000
    threads:1
    run:
        samplePrefix = params.sampename
        phenotype =config["phenotype"][samplePrefix]
        infile = open(input.gender, "r")
        filelines = infile.readlines()
        sample2gender = {}
        gender = 'ND'
        for line in filelines:
            line = line.strip()
            sample2gender[line.split(',')[0]]=line.split(',')[1]
        if samplePrefix in sample2gender:
            gender = sample2gender[samplePrefix]
        print('perl {params.SNVannotation} -g {gender} -p "{phenotype}" -i {input.split} -o {output.verbose} -cfg config.yaml')
        shell('perl {params.SNVannotation} -g {gender} -p "{phenotype}" -i {input.split} -o {output.verbose} -cfg config.yaml')

rule batchVcf2Vaf:
    input:
        qualvcf="01_SNV/"+batch+".qual.flt.vcf.gz",
    output:
        vafvcf="01_SNV/"+batch+".vaf.flt.vcf",
        vaf="01_SNV/"+batch+".vaf",
        vafgz="01_SNV/"+batch+".vaf.gz",
    resources:
        qsub_vf=10000
    threads:8
    params:
        bcftoolsdir=bcftoolsPath
    shell:
        """
        {bcftools} view -i  'N_ALT=1 & AVG(FMT/DP)>8 & MIN(FMT/DP)>5 & MIN(FMT/GQ)>15 & QUAL > 30 & MAX(FORMAT/AD[*:1]/FORMAT/DP[*]) > 0.1 ' {input.qualvcf} > {output.vafvcf}
        export BCFTOOLS_PLUGINS={params.bcftoolsdir}/plugins
        {bcftools} +fill-tags {output.vafvcf} -- -t FORMAT/VAF |{bcftools} query -H -f '%CHROM\t%POS\t%END\t%REF/%ALT[\t%VAF]\n' > {output.vaf}
        {bgzip} -c -@ 8 {output.vaf}> {output.vafgz}
        """

rule splitVcf:
    input:
        qualvcf="01_SNV/"+batch+".qual.flt.vcf.gz",
        normvcf="01_SNV/"+batch+".normalize.vcf.gz",
        vafvcf="01_SNV/"+batch+".vaf.flt.vcf",
    output:
        vcf = "01_SNV/{sample}.vcf",
        rawvcf = "01_SNV/{sample}.raw.vcf.gz",
        vafFltvcf="01_SNV/{sample}.vaf.flt.vcf",
        vaf="01_SNV/{sample}.vaf",
    resources:
        qsub_vf=10000,

    threads:1
    params: samplename="{sample}",
     bcftoolsdir=bcftoolsPath
    shell:
       """
       {bcftools} view -s {params.samplename} {input.qualvcf}|{bcftools} view -e 'GT=="mis" || GT=="0/0" ||FORMAT/DP<30' > {output.vcf}
       {bcftools} view -s {params.samplename} {input.normvcf}|{bcftools} view -e 'GT=="mis" || GT=="0/0"' -Oz -o {output.rawvcf} && {tabix} -fp vcf {output.rawvcf}
       {bcftools} view -s {params.samplename} {input.vafvcf}|{bcftools} view -e 'GT=="mis" || GT=="0/0" ||FORMAT/DP<30 ' > {output.vafFltvcf}
       export BCFTOOLS_PLUGINS={params.bcftoolsdir}/plugins
       {bcftools} +fill-tags {output.vafFltvcf} -- -t FORMAT/VAF |{bcftools} query -f '%CHROM\t%POS\t%END\t%REF/%ALT[\t%VAF]\n' > {output.vaf}
       sed -i  '1i\chr\tstart\tend\tallele\t{params.samplename}' {output.vaf}
       """

rule bedGraphVaf:
    input:
        vaf="01_SNV/{sample}.vaf"
    output:
        vaf_bedGraph="01_SNV/{sample}.vaf.bedGraph.gz"
    resources:
        qsub_vf=10000
    threads:1
    shell:
       """
       awk -F'\\t' 'NR>1 {{OFS="\\t"; print $1, $2, $3, $5}}' {input.vaf} | {bgzip} -c -@ 8 > {output.vaf_bedGraph}
       {tabix} -fp bed {output.vaf_bedGraph}
       """
