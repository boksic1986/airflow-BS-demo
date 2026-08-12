# container: config["containers"]["SNV"]

import re


SNV_TOOLS=config.get("container_tools", {}).get("SNV", {})
PRE_TOOLS=config.get("container_tools", {}).get("pre", {})
CONTAINER_RESOURCES=config.get("container_resources", {})

SentieonPath=PRE_TOOLS["sentieon"]
preBgzip=PRE_TOOLS["bgzip"]
preTabix=PRE_TOOLS["tabix"]

bgzip=SNV_TOOLS["bgzip"]
tabix=SNV_TOOLS["tabix"]
bcftools=SNV_TOOLS["bcftools"]
liftOver=SNV_TOOLS["liftOver"]
vcfannotate=SNV_TOOLS["vcfannotate"]
bedtools=SNV_TOOLS["bedtools"]
VEP=SNV_TOOLS["vep"]
python3Path=SNV_TOOLS["python3"]
perl=SNV_TOOLS["perl"]
slivar=SNV_TOOLS["slivar"]
pandepth=SNV_TOOLS["pandepth"]
snvRust=SNV_TOOLS["snv_cs"]
gnuSort=SNV_TOOLS["gnu_sort"]

slivarJs=CONTAINER_RESOURCES["slivar_js"]
slivarGnomad=CONTAINER_RESOURCES["slivar_gnomad"]

sampleInfoFile=config["sample_info"]
batch=config["batch"]
minDepth=config.get("minDepth", 10)

SAMPLES=config["sample"]
PEDIGREE=config["pedigree"]
BKWSAMPLES=config.get("BKWsampleList",[])
NON_BKW_SAMPLES = [
    sample for sample in config.get("sample", [])
    if sample not in set(BKWSAMPLES)
]

BKWPEDIGREE = config.get("BKWpedigree",[])
NON_BKW_PEDIGREE = [
    pedigree for pedigree in config.get("pedigree", [])
    if pedigree not in set(BKWPEDIGREE)
]


vep_cache=config['biosoft']['vepCache']
vepPlugin=config['biosoft']['vepPlugin']

createPed=config["src"]["createPed"]
slivarPl=config["src"]["slivarPl"]
splitPl=config["src"]["splitPl"]
dpCorrectPy=config["src"]["dpCorrectPy"]
replaceBKW=config["src"]["replaceBKW"]
ruleHelper=config['src']['ruleHelper']
tagCandidateOtherPy=config['src']['tagCandidateOtherPy']
selectModifierPl=config['src']['selectModifierPl']


reference=config["genome"]["fasta"]
dbsnp=config["genome"]["dbsnp"]
known_Mills_indels=config["genome"]["known_Mills_indels"]
known_1000G_indels=config["genome"]["known_1000G_indels"]

genebed=config["bed"]['geneBed']
virtualWESBed=config['bed']['virtualWESBed']

whitelistV1=config["database"]['whitelistV1']
whitelistV1_BKW=config["database"]['whitelistV1_BKW']
whitelistV4=config["database"]['whitelistV4']
blacklist=config["database"]['blacklist']
bkwgenelist=config["database"]['bkwgenelist']
localMaf=config["database"]['localMAF']
spliceai_SNV = config['database']['spliceaiSNV']
spliceai_Indel = config['database']['spliceaiINDEL']
dbNSFP = config['database']['dbNSFP']
dbscSNV = config['database']['dbscSNV']
clinvar = config['database']['clinvar']
HGMD = config['database']['HGMD']
intervar = config['database']['intervar']
LocalVarDB = config['database']['LocalVarDB']
gnomad_exomes = config['database']['gnomadWES']
gnomad_genomes = config['database']['gnomadWGS']
simpleRepeat = config['database']['simpleRepeat']
genmap_100mer = config['database']['mappability']
local_PLP_database=config["database"]['local_PLP_database']
clinvar_PLP_database=config["database"]['clinvar_PLP_database']
exception_database=config["database"]['exception_database']
gnomad_common_database=config["database"]['gnomad_common_database']
local_common_database=config["database"]['local_common_database']
morbid_gene_bed = config['database']['morbidmapBed']


wildcard_constraints:
    sample= '|'.join([re.escape(x) for x in SAMPLES]),
    pedigree= '|'.join([re.escape(x) for x in PEDIGREE])


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
    container:
        runtime_container("SNV_GVCFtyper")
    input:
         expand("00_PreCalling/{sample}.g.vcf.gz", sample=config["sample"])
    output:
         allRawvcf=expand("01_SNV/{batch}.raw.vcf",batch=config["batch"]),
         allRawvcfgz=expand("01_SNV/{batch}.raw.vcf.gz",batch=config["batch"]),
    params:
         sentieonPath = SentieonPath,
         genome = reference,
         parms =" -v ".join(expand("00_PreCalling/{sample}.g.vcf.gz", sample=config["sample"])),
         dbsnp=dbsnp,
         bgzipPath=preBgzip,
         tabixPath=preTabix
    shell:
        """
         export MALLOC_CONF=lg_dirty_mult:-1
        {params.sentieonPath} driver -r {params.genome} -t {threads} --algo GVCFtyper -v {params.parms} -d {params.dbsnp} --emit_conf=10 --call_conf=10 {output.allRawvcf}
        {params.bgzipPath} -@ {threads} -c {output.allRawvcf} > {output.allRawvcfgz}
        {params.tabixPath} -fp vcf {output.allRawvcfgz}
        """

rule NormalizeVcf:
    container:
        runtime_container("SNV_NormalizeVcf")
    input:
        vcf = "01_SNV/{batch}.raw.vcf.gz"
    output:
        tagVcf = temp("01_SNV/{batch}.normalize.tmp.vcf.gz"),
        normVcf = "01_SNV/{batch}.normalize.vcf.gz",
        stage = temp("01_SNV/{batch}.g2.normalize.done"),
    params:
        genome = reference,
        bcftools = bcftools,
        tabix = tabix
    shell:
        """
        {params.bcftools} +fill-tags {input.vcf} -- -t 'FORMAT/ADS:1=int(smpl_sum(FORMAT/AD)-FORMAT/AD[*:0])' | {params.bcftools} view -Oz -o {output.tagVcf}
        {params.bcftools} norm -c w -m -any -f {params.genome} {output.tagVcf} -Oz -o {output.normVcf} --threads {threads} && {params.tabix} -fp vcf {output.normVcf}
        touch {output.stage}
        """

rule regionFlt:
    container:
        runtime_container("SNV_regionFlt")
    input:
        normalizeVcf = "01_SNV/"+batch+".normalize.vcf.gz"
    output:
        vcf = "01_SNV/"+batch+".region.flt.vcf.gz",
        tbi = "01_SNV/"+batch+".region.flt.vcf.gz.tbi"
    params:
        bcftools = bcftools,
        tabix = tabix
    shell:
        """
        {params.bcftools} view -e 'CHROM~"M" || CHROM~"GL" || CHROM~"KI" || CHROM~"HLA" || CHROM~"Un" || CHROM~"alt" ||  CHROM~"random" ' {input.normalizeVcf} -Oz -o {output.vcf} && {params.tabix} -fp vcf {output.vcf}
        """

rule qualityFlt:
    container:
        runtime_container("SNV_qualityFlt")
    input:
        normalizeVcf = "01_SNV/"+batch+".normalize.vcf.gz",
        stage = "01_SNV/"+batch+".g2.normalize.done",
    output:
        qualvcf = "01_SNV/"+batch+".qual.flt.vcf.gz",
        qualTbi = "01_SNV/"+batch+".qual.flt.vcf.gz.tbi",
        lowQualityVcf = "01_SNV/"+batch+".low_qual.vcf.gz",
        lowQualityTbi = "01_SNV/"+batch+".low_qual.vcf.gz.tbi",
        fltLowQualityVcf = "01_SNV/"+batch+".flt_low_qual.vcf.gz",
        fltLowQualityTbi = "01_SNV/"+batch+".flt_low_qual.vcf.gz.tbi"
        stage = temp("01_SNV/"+batch+".g2.quality.done"),
    params:
        bcftools = bcftools,
        minDepth = minDepth,
        whitelistV4 = whitelistV4,
        vcfannotate = vcfannotate,
        genebed = genebed,
        tabix = tabix
    shell:
        """
        {params.bcftools} view -i 'QUAL<20 || MAX(FMT/GQ)<20 || MAX(FMT/DP)<{params.minDepth}' {input.vcf} -Oz -o {output.lowQualityVcf} && {params.tabix} -fp vcf {output.lowQualityVcf}
        {params.bcftools} isec -n~10 -c none -w 1 {output.lowQualityVcf} {params.whitelistV4} -Oz -o {output.fltLowQualityVcf} && {params.tabix} -fp vcf {output.fltLowQualityVcf}
        {params.bcftools} isec -n~10 -c none -w 1 {input.vcf} {output.fltLowQualityVcf} | {params.bcftools} view -e 'CHROM~"M"' | {params.vcfannotate} -b {params.genebed} -k gene /dev/stdin | {params.bgzip} -@ {threads} -c > {output.qualvcf}  && {params.tabix} -fp vcf {output.qualvcf}
        touch {output.stage}
        """

rule virtualWES:
    container:
        runtime_container("SNV_virtualWES")
    input:
        vcf="01_SNV/"+batch+".region.flt.vcf.gz",
        tbi = "01_SNV/"+batch+".region.flt.vcf.gz.tbi"
        stage="01_SNV/"+batch+".g2.quality.done",
    output:
        WESvcf="01_SNV/"+batch+".WES.vcf.gz",
        WEStbi="01_SNV/"+batch+".WES.vcf.gz.tbi",
        outWESvcf="01_SNV/"+batch+".outWES.vcf.gz",
        outWEStbi="01_SNV/"+batch+".outWES.vcf.gz.tbi",
        outWESNotInWhiteV1="01_SNV/"+batch+".outWESNotPLP.vcf.gz",
        outWESNotInWhiteV1tbi="01_SNV/"+batch+".outWESNotPLP.vcf.gz.tbi",
        vcf="01_SNV/"+batch+".WES.flt.vcf.gz",
        tbi="01_SNV/"+batch+".WES.flt.vcf.gz.tbi"
         stage=temp("01_SNV/"+batch+".g2.hts.done"),
    params:
        bedtools = bedtools,
        virtualWESBed = virtualWESBed,
        whitelistV1 = whitelistV1,
        bgzip = bgzip,
        tabix = tabix,
        bcftools = bcftools
    shell:
        """
        {params.bedtools} intersect -a {input.vcf} -b {params.virtualWESBed} -wa -header | {params.bgzip} -@ {threads} > {output.WESvcf} && {params.tabix} -fp vcf {output.WESvcf}  ## call到并且在虚拟WES区域的变异
        {params.bedtools} intersect -a {input.vcf} -b {params.virtualWESBed} -v -wa -header | {params.bgzip} -@ {threads} > {output.outWESvcf} && {params.tabix} -fp vcf {output.outWESvcf} ## call到但是在WES区域外的变异
        {params.bcftools} isec -n 1 -c none -w 1 {output.outWESvcf} {params.whitelistV1} -Oz -o {output.outWESNotInWhiteV1} && {params.tabix} -fp vcf {output.outWESNotInWhiteV1}  # 在WES区域外且不在白名单V1中的变异
        {params.bcftools} isec -n~10 -c none -w 1 {input.vcf} {output.outWESNotInWhiteV1} -Oz -o {output.vcf} && {params.tabix} -fp vcf {output.vcf}
        touch {output.stage}
        """

rule vep:
    container:
        runtime_container("SNV_vep")
    input:
        vcf="01_SNV/"+batch+".WES.flt.vcf.gz",
        tbi="01_SNV/"+batch+".WES.flt.vcf.gz.tbi"
    output:
        vep_vcf = "01_SNV/"+batch+".vep.vcf.gz",
        vep_tbi = "01_SNV/"+batch+".vep.vcf.gz.tbi"
    params:
        genome = reference,
        VEP = VEP,
        vep_cache = vep_cache,
        vepPlugin = vepPlugin,
        spliceai_SNV = spliceai_SNV,
        spliceai_Indel = spliceai_Indel,
        dbNSFP = dbNSFP,
        dbscSNV = dbscSNV,
        clinvar = clinvar,
        HGMD = HGMD,
        intervar = intervar,
        LocalVarDB = LocalVarDB,
        gnomad_exomes = gnomad_exomes,
        gnomad_genomes = gnomad_genomes,
        simpleRepeat = simpleRepeat,
        genmap_100mer = genmap_100mer,
        localMaf = localMaf,
        morbid_gene_bed = morbid_gene_bed,
        tabix = tabix,
        bcftools = bcftools
    shell:
        """
        {params.VEP}/vep -i {input.vcf} -o {output.vep_vcf} --offline --cache --hgvs --hgvsg --symbol --canonical --total_length --force --vcf --compress_output bgzip  --refseq --use_given_ref --assembly GRCh38 --fasta {params.genome} \
        --dir_cache {params.vep_cache} \
        --dir_plugins {params.vepPlugin} \
        --plugin SpliceAI,snv={params.spliceai_SNV},indel={params.spliceai_Indel},cutoff=0.2 \
        --plugin dbNSFP,{params.dbNSFP},SIFT_pred,Polyphen2_HDIV_pred,Polyphen2_HVAR_pred,LRT_pred,AlphaMissense_pred,MutationAssessor_pred,FATHMM_pred,PROVEAN_pred,MetaSVM_pred,MetaLR_pred,REVEL_score \
        --plugin dbscSNV,{params.dbscSNV} \
        --custom {params.clinvar},clinvar,vcf,exact,0,CLNREVSTAT,CLNSIG,ClinicalSignificance,Submitter,CollectionMethod,CLNDN \
        --custom {params.HGMD},HGMD,vcf,exact,0,Rank_Score,Class,Pubmed \
        --custom {params.intervar},intervar,vcf,exact,0,SIG \
        --custom {params.LocalVarDB},local_path,vcf,exact,0,Pathogenicity,EvidenceList,Evidence \
        --custom {params.gnomad_exomes},GnomADExomes,vcf,exact,0,controls_AC,controls_AN,controls_AF,controls_AC_eas,controls_AN_eas,controls_AF_eas,controls_nhomalt,controls_nhomalt_male,controls_nhomalt_female \
        --custom {params.gnomad_genomes},GnomADGenomes,vcf,exact,0,controls_AC,controls_AN,controls_AF,controls_AC_eas,controls_AN_eas,controls_AF_eas,controls_nhomalt,controls_nhomalt_male,controls_nhomalt_female  \
        --custom {params.simpleRepeat},Repeat,bed,overlap,0 \
        --custom {params.genmap_100mer},Mapability,bed,overlap,0 \
        --custom {params.morbid_gene_bed},MorbidGene,bed,overlap,0 \
        --custom {params.localMaf},LocalMAF,vcf,exact,0,AC,AN,AF \
        --fork {threads} --no_escape --xref_refseq --failed 1
        {params.tabix} -fp vcf {output.vep_vcf}
        """

rule vcfTagCandidateOther:
    container:
        runtime_container("SNV_vcfTagCandidateOther")
    input:
        vep_vcf = "01_SNV/"+batch+".vep.vcf.gz",
        vep_tbi = "01_SNV/"+batch+".vep.vcf.gz.tbi"
    output:
        lof_vcf = "01_SNV/"+batch+".lof.vcf.gz",
        lof_tbi = "01_SNV/"+batch+".lof.vcf.gz.tbi",
        dm_vcf = "01_SNV/"+batch+".dm.vcf.gz",
        dm_tbi = "01_SNV/"+batch+".dm.vcf.gz.tbi",
        other_vcf = "01_SNV/"+batch+".other.vcf.gz",
        other_tbi = "01_SNV/"+batch+".other.vcf.gz.tbi"
    params:
        python3Path = python3Path,
        tagCandidateOtherPy = tagCandidateOtherPy,
        bcftools = bcftools,
        tabix = tabix
    # resources:
    #     qsub_vf = 12000
    # threads: 8
    shell:
        """
        {params.python3Path} {params.tagCandidateOtherPy} -i {input.vep_vcf} -lof {output.lof_vcf} -dm {output.dm_vcf} -other {output.other_vcf} --bcftools {params.bcftools} --tabix {params.tabix}
        """

rule vcfTag:
    container:
        runtime_container("SNV_vcfTag")
    input:
        vcf = "01_SNV/"+batch+".vep.vcf.gz",
        tbi = "01_SNV/"+batch+".vep.vcf.gz.tbi",
        lof_vcf = "01_SNV/"+batch+".lof.vcf.gz",
        lof_tbi = "01_SNV/"+batch+".lof.vcf.gz.tbi",
        dm_vcf = "01_SNV/"+batch+".dm.vcf.gz",
        dm_tbi = "01_SNV/"+batch+".dm.vcf.gz.tbi"
    output:
        low_quality_vcf = "01_SNV/"+batch+".low_quality.tmp.vcf.gz",
        low_quality_tbi = "01_SNV/"+batch+".low_quality.tmp.vcf.gz.tbi",
        local_PLP_tag_vcf = "01_SNV/"+batch+".local_PLP_tag.tmp.vcf.gz",
        local_PLP_tag_tbi = "01_SNV/"+batch+".local_PLP_tag.tmp.vcf.gz.tbi",
        clinvar_PLP_tag_vcf = "01_SNV/"+batch+".clinvar_PLP_tag.tmp.vcf.gz",
        clinvar_PLP_tag_tbi = "01_SNV/"+batch+".clinvar_PLP_tag.tmp.vcf.gz.tbi",
        exception_tag_vcf = "01_SNV/"+batch+".exception_tag.tmp.vcf.gz",
        exception_tag_tbi = "01_SNV/"+batch+".exception_tag.tmp.vcf.gz.tbi",
        GnomAD_common_tag_vcf = "01_SNV/"+batch+".gnomad_common_tag.tmp.vcf.gz",
        GnomAD_common_tag_tbi = "01_SNV/"+batch+".gnomad_common_tag.tmp.vcf.gz.tbi",
        local_common_tag_vcf = "01_SNV/"+batch+".local_common_tag.tmp.vcf.gz",
        local_common_tag_tbi = "01_SNV/"+batch+".local_common_tag.tmp.vcf.gz.tbi",
        lof_tag_vcf = "01_SNV/"+batch+".lof_tag.tmp.vcf.gz",
        lof_tag_tbi = "01_SNV/"+batch+".lof_tag.tmp.vcf.gz.tbi",
        dm_tag_vcf = "01_SNV/"+batch+".dm_tag.tmp.vcf.gz",
        dm_tag_tbi = "01_SNV/"+batch+".dm_tag.tmp.vcf.gz.tbi",
        tag_vcf = "01_SNV/"+batch+".tag.vcf.gz",
        tag_tbi = "01_SNV/"+batch+".tag.vcf.gz.tbi"
    params:
        bcftools = bcftools,
        tabix = tabix,
        local_PLP_database = local_PLP_database,
        clinvar_PLP_database = clinvar_PLP_database,
        exception_database = exception_database,
        gnomad_common_database = gnomad_common_database,
        local_common_database = local_common_database
    # resources:
    #     qsub_vf = 12000
    # threads:8
    shell:
        """
        {params.bcftools} annotate -a {params.local_PLP_database} -c INFO/IsLocalPLP -h <(echo '##INFO=<ID=IsLocalPLP,Number=0,Type=Flag,Description="Site present in local_PLP_database">') {input.vcf} -Oz -o {output.local_PLP_tag_vcf} && {params.tabix} -fp vcf {output.local_PLP_tag_vcf}
        {params.bcftools} annotate -a {params.clinvar_PLP_database} -c INFO/IsClinvarPLP -h <(echo '##INFO=<ID=IsClinvarPLP,Number=0,Type=Flag,Description="Site present in clinvar_PLP_database">') {output.local_PLP_tag_vcf} -Oz -o {output.clinvar_PLP_tag_vcf} && {params.tabix} -fp vcf {output.clinvar_PLP_tag_vcf}
        {params.bcftools} annotate -a {params.exception_database} -c INFO/IsException -h <(echo '##INFO=<ID=IsException,Number=0,Type=Flag,Description="Site present in exceptionList">') {output.clinvar_PLP_tag_vcf} -Oz -o {output.exception_tag_vcf} && {params.tabix} -fp vcf {output.exception_tag_vcf}

        {params.bcftools} annotate -a {input.lof_vcf} -c INFO/IsLOF -h <(echo '##INFO=<ID=IsLOF,Number=0,Type=Flag,Description="Site present in LOF">') {output.exception_tag_vcf} -Oz -o {output.lof_tag_vcf} && {params.tabix} -fp vcf {output.lof_tag_vcf}
        {params.bcftools} annotate -a {input.dm_vcf} -c INFO/IsDM -h <(echo '##INFO=<ID=IsDM,Number=0,Type=Flag,Description="Site present in DM">') {output.lof_tag_vcf} -Oz -o {output.dm_tag_vcf} && {params.tabix} -fp vcf {output.dm_tag_vcf}

        {params.bcftools} annotate -a {params.gnomad_common_database} -c INFO/IsGnomADcommon -h <(echo '##INFO=<ID=IsGnomADcommon,Number=0,Type=Flag,Description="Site present in gnomad_common_database">') {output.dm_tag_vcf} -Oz -o {output.GnomAD_common_tag_vcf} && {params.tabix} -fp vcf {output.GnomAD_common_tag_vcf}
        {params.bcftools} annotate -a {params.local_common_database} -c INFO/IsLocalCommon -h <(echo '##INFO=<ID=IsLocalCommon,Number=0,Type=Flag,Description="Site present in local_common_database">') {output.GnomAD_common_tag_vcf} -Oz -o {output.local_common_tag_vcf} && {params.tabix} -fp vcf {output.local_common_tag_vcf}

        {params.bcftools} view -i "QUAL<30 || MAX(FMT/DP)<10 || MAX(FMT/GQ)<20" {input.vcf} -Oz -o {output.low_quality_vcf} && {params.tabix} -fp vcf {output.low_quality_vcf}
        {params.bcftools} annotate -a {output.low_quality_vcf} -c INFO/IsLowQual -h <(echo '##INFO=<ID=IsLowQual,Number=0,Type=Flag,Description="Site is low quality">') {output.local_common_tag_vcf} -Oz -o {output.tag_vcf} && {params.tabix} -fp vcf {output.tag_vcf}
        """

rule select_4tiers:
    container:
        runtime_container("SNV_select_4tiers")
    input:
        vcf = "01_SNV/"+batch+".tag.vcf.gz",
        tbi = "01_SNV/"+batch+".tag.vcf.gz.tbi"
    output:
        vcf = "01_SNV/"+batch+".4tiers.vcf.gz",
        tbi = "01_SNV/"+batch+".4tiers.vcf.gz.tbi"
    params:
        bcftools = bcftools,
        tabix = tabix
    # resources:
    #     qsub_vf = 12000
    # threads:8
    shell:
        """
        {params.bcftools} view -i 'INFO/IsLocalPLP=1 || INFO/IsClinvarPLP=1 || INFO/IsException=1 || (INFO/IsGnomADcommon=0 && INFO/IsLocalCommon=0 && INFO/IsLowQual=0 && (INFO/IsLOF=1 || INFO/IsDM=1))' {input.vcf} -Oz -o {output.vcf} && {params.tabix} -fp vcf {output.vcf}
        """

rule vepPosCorr:
    container:
        runtime_container("SNV_vepPosCorr")
    input:
        vcf="01_SNV/"+batch+".vep.vcf.gz"
    output:
        vcf=temp("01_SNV/{batch}.vepLocation.vcf.gz"),
        tsv="01_SNV/{batch}.vepLocation.tsv"
    params:
        genome = reference,
        VEP = VEP,
        vep_cache = vep_cache,
        tabix = tabix,
        bcftools = bcftools
    # resources:
    #     qsub_vf=10000
    # threads:16
    shell:
        """ 
        {params.VEP} -i {input.vcf} -o {output.vcf} --offline --cache --force --vcf --compress_output bgzip --refseq --use_given_ref --assembly GRCh38 --fasta {params.genome} \
        --dir_cache {params.vep_cache} --fork {threads} --no_escape --xref_refseq --failed 1 --shift_genomic 1 --shift_3prime 1 --fields "Location,Allele,SYMBOL,Consequence,Feature,Gene"
        {params.tabix} -fp vcf {output.vcf}
        {params.bcftools} +split-vep {output.vcf} -f \'%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\n\' -A tab -d > {output.tsv}
        """

rule intergenicFlt:
    container:
        runtime_container("SNV_intergenicFlt")
    input:
        vcf="01_SNV/"+batch+".tag.vcf.gz",
        tbi = "01_SNV/"+batch+".tag.vcf.gz.tbi"
    output:
        lenient = "01_SNV/"+batch+".lenient.flt.vcf.gz",
        lenient_BKW = "01_SNV/"+batch+".lenient.bkw.flt.vcf.gz",
        intergenic = temp("01_SNV/"+batch+".tmp.intergenic.vcf.gz"),
        intergenicTbi = temp("01_SNV/"+batch+".tmp.intergenic.vcf.gz.tbi"),
        intergenicFlt = temp("01_SNV/"+batch+".tmp.intergenicFlt.vcf.gz"),
        intergenicFltTbi = temp("01_SNV/"+batch+".tmp.intergenicFlt.vcf.gz.tbi"),
        intergenicFlt_BKW = temp("01_SNV/"+batch+".tmp.bkw.intergenicFlt.vcf.gz"),
        intergenicFltTbi_BKW = temp("01_SNV/"+batch+".tmp.bkw.intergenicFlt.vcf.gz.tbi")
    params:
        bcftools = bcftools,
        bgzip = bgzip,
        tabix = tabix,
        whitelistV1 = whitelistV1,
        whitelistV1_BKW = whitelistV1_BKW
    # resources:
    #     qsub_vf=10000
    # threads:8
    shell:
        r"""
        {params.bcftools} +split-vep {input.vcf} \
            -f '%CHROM\t%POS\t%ID\t%REF\t%ALT\t%QUAL\t%FILTER\t%CSQ\n' \
            -A tab -s worst -d \
        | awk -F "\t" '$9=="intergenic_variant" || $9=="downstream_gene_variant" || $9=="upstream_gene_variant"' \
        | awk -F "\t" 'BEGIN{{OFS="\t"}}{{print $1,$2,$3,$4,$5,$6,$7,"WORSTIMPACT=intergenic_variant"}}' \
        | sed '1i##fileformat=VCFv4.2\n##INFO=<ID=WORSTIMPACT,Number=.,Type=String,Description="">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO' \
        | {params.bgzip} -@ {threads} -c > {output.intergenic} \
        && {params.tabix} -fp vcf {output.intergenic}

        # 杭检
        {params.bcftools} isec -n~10 -c none -w 1 \
            {output.intergenic} {params.whitelistV1} \
            -Oz -o {output.intergenicFlt} \
        && {params.tabix} -fp vcf {output.intergenicFlt}

        {params.bcftools} isec -n~10 -c none -w 1 \
            {input.vcf} {output.intergenicFlt} \
            -Oz -o {output.lenient} \
        && {params.tabix} -fp vcf {output.lenient}

        # 倍科为
        {params.bcftools} isec -n~10 -c none -w 1 \
            {output.intergenic} {params.whitelistV1_BKW} \
            -Oz -o {output.intergenicFlt_BKW} \
        && {params.tabix} -fp vcf {output.intergenicFlt_BKW}

        {params.bcftools} isec -n~10 -c none -w 1 \
            {input.vcf} {output.intergenicFlt_BKW} \
            -Oz -o {output.lenient_BKW} \
        && {params.tabix} -fp vcf {output.lenient_BKW}
        """



rule blacklistFlt:
    container:
        runtime_container("SNV_blacklistFlt")
    input:
        vcf="01_SNV/"+batch+".tag.vcf.gz",
        tbi = "01_SNV/"+batch+".tag.vcf.gz.tbi",
        keepVcf = "01_SNV/"+batch+".4tiers.vcf.gz",
        keepTbi = "01_SNV/"+batch+".4tiers.vcf.gz.tbi"
    output:
        blackTmpVcf = "01_SNV/"+batch+".blacklist.tmp.vcf.gz",
        blackTmpTbi = "01_SNV/"+batch+".blacklist.tmp.vcf.gz.tbi",
        blackFltVcf = "01_SNV/"+batch+".blacklist.flt.vcf.gz",
        blackFltTbi = "01_SNV/"+batch+".blacklist.flt.vcf.gz.tbi"
    params:
        bcftools = bcftools,
        tabix = tabix,
        blacklist = blacklist
    # resources:
    #     qsub_vf=10000
    # threads:8
    shell:
        """
        {params.bcftools} isec -n~10 -c none -w 1 {params.blacklist} {input.keepVcf} -Oz -o {output.blackTmpVcf} && {params.tabix} -fp vcf {output.blackTmpVcf}
        {params.bcftools} isec -n~10 -c none -w 1 {input.vcf} {output.blackTmpVcf} -Oz -o {output.blackFltVcf} && {params.tabix} -fp vcf {output.blackFltVcf}
        """

rule createPed:
    container:
        runtime_container("SNV_createPed")
    input:
        sampleInfo=sampleInfoFile,
        gender = "07_QC/"+batch+".gender.txt",
    output:
        pedfile = "08_ped/"+batch+".ped",
        sampleRank="08_ped/"+batch+".rank.txt",
        famPed = expand("08_ped/{pedigreeID}.ped",pedigreeID=config["pedigree"]),
        famRank = expand("08_ped/{pedigreeID}.rank.txt",pedigreeID=config["pedigree"])
    params:
        dir='08_ped',
        python3Path=python3Path,
        createPed=createPed,
        batch=batch
    shell:
         "{params.python3Path} {params.createPed} --outpath {params.dir} --outbatch {params.batch} --sampleInfo {input.sampleInfo} --gender {input.gender}"

def get_solo_lenient_vcf(wildcards):
    if wildcards.sample in config.get("BKWsampleList", []):
        return "01_SNV/" + batch + ".lenient.bkw.flt.vcf.gz"
    return "01_SNV/" + batch + ".lenient.flt.vcf.gz"

rule solo_split_lenient:
    container:
        runtime_container("SNV_solo_split_lenient")
    input:
        lenient = get_solo_lenient_vcf,
    output:
        vcf = temp("02_split/{sample}.split.vcf"),
        tsv = "02_split/{sample}.split.tsv"
    params:
        samplename="{sample}",
        splitPl=splitPl,
        bcftools=bcftools,
        whitelistV4 = whitelistV4,
        perl=perl
    shell:
        '{params.perl} {params.splitPl} -i {input.vcf} -o {output.vcf} -tsv {output.tsv} -s {params.samplename} -bcftools {params.bcftools} -whitelist {params.whitelistV4}'

rule solo_split_strict:
    container:
        runtime_container("SNV_solo_split_strict")
    input:
        vcf = "01_SNV/"+batch+".blacklist.flt.vcf.gz"
    output:
        vcf = "02_split/{sample}.split.blacklist.flt.vcf",
        vcfGz = "02_split/{sample}.split.blacklist.flt.vcf.gz",
        vcfTbi = "02_split/{sample}.split.blacklist.flt.vcf.gz.tbi",
        tsv = "02_split/{sample}.split.blacklist.flt.tsv"
    params:
        samplename="{sample}",
        splitPl=splitPl,
        bcftools=bcftools,
        whitelistV4 = whitelistV4,
        bgzip = bgzip,
        tabix = tabix,
        perl=perl
    shell:
        """
        {params.perl} {params.splitPl} -i {input.vcf} -o {output.vcf} -tsv {output.tsv} -s {params.samplename} -bcftools {params.bcftools} -whitelist {params.whitelistV4}
        {params.bgzip} -c {output.vcf} > {output.vcfGz} && {params.tabix} -fp vcf {output.vcfGz}
        """

rule solo_flt_modifier:
    container:
        runtime_container("SNV_solo_flt_modifier")
    input:
        vcfGz = "02_split/{sample}.split.blacklist.flt.vcf.gz",
        vcfTbi = "02_split/{sample}.split.blacklist.flt.vcf.gz.tbi"
    output:
        vcf = "02_split/{sample}.split.flt.vcf",
        tsv = "02_split/{sample}.split.flt.tsv",
        modifierVcf = "02_split/{sample}.modifier.tmp.vcf.gz",
        modifierTbi = "02_split/{sample}.modifier.tmp.vcf.gz.tbi",
        modifierVcf2 = "02_split/{sample}.modifier.tmp2.vcf",
        modifierleft_tsv = "02_split/{sample}.modifier.left.tmp.tsv",
        modifierleftGz = "02_split/{sample}.modifier.left.tmp.vcf.gz",
        modifierleftGzTbi = "02_split/{sample}.modifier.left.tmp.vcf.gz.tbi",
        modifierFltVcfGz = temp("02_split/{sample}.modifier.tmp.flt.vcf.gz"),
        modifierFltTbi = temp("02_split/{sample}.modifier.tmp.flt.vcf.gz.tbi")
    params:
        selectModifierPl = selectModifierPl,
        whitelistV1 = whitelistV1,
        bcftools = bcftools,
        bgzip = bgzip,
        tabix = tabix,
        perl = perl
    # resources:
    #     qsub_vf=12000
    # threads: 8
    shell:
        r"""
        {params.bcftools} +split-vep {input.vcfGz} \
            -f '%CHROM\t%POS\t%ID\t%REF\t%ALT\t%QUAL\t%FILTER\t%CSQ\n' \
            -A tab -s worst -d \
        | awk -F "\t" '$10=="MODIFIER"' \
        | awk -F "\t" 'BEGIN{{OFS="\t"}}{{print $1,$2,$3,$4,$5,$6,$7,"WORSTIMPACT=MODIFIER"}}' \
        | sed '1i##fileformat=VCFv4.2\n##INFO=<ID=WORSTIMPACT,Number=.,Type=String,Description="">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO' \
        | {params.bgzip} -c > {output.modifierVcf} \
        && {params.tabix} -fp vcf {output.modifierVcf}

        # 不在白名单且不在保留规则中的 modifier
        {params.bcftools} isec -n~11 -c none -w 1 \
            {input.vcfGz} {output.modifierVcf} \
            -Ov -o {output.modifierVcf2}

        {params.perl} {params.selectModifierPl} \
            -i {output.modifierVcf2} \
            -sample {wildcards.sample} \
            -tsv {output.modifierleft_tsv} \
            -bcftools {params.bcftools}

        cut -f 1-7 {output.modifierleft_tsv} \
        | uniq \
        | awk -F "\t" 'BEGIN{{OFS="\t"}}{{print $1,$2,$3,$4,$5,$6,$7,"WORSTIMPACT=MODIFIER"}}' \
        | sed '1i##fileformat=VCFv4.2\n##INFO=<ID=WORSTIMPACT,Number=.,Type=String,Description="">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO' \
        | {params.bgzip} -c > {output.modifierleftGz} \
        && {params.tabix} -fp vcf {output.modifierleftGz}

        {params.bcftools} isec -n~100 -c none -w 1 \
            {output.modifierVcf} {params.whitelistV1} {output.modifierleftGz} \
            -Oz -o {output.modifierFltVcfGz} \
        && {params.tabix} -fp vcf {output.modifierFltVcfGz}

        {params.bcftools} isec -n~10 -c none -w 1 \
            {input.vcfGz} {output.modifierFltVcfGz} \
            -Ov -o {output.vcf}

        split_header=$(
            grep '^#CHROM' {output.vcf} \
            | sed -e 's/#//' -e 's/INFO.*//' \
            | tr -d '\n'
        )
        csq_header=$(
            grep '##INFO=<ID=CSQ' {output.vcf} \
            | sed \
                -e 's/##INFO=<ID=CSQ,Number=.,Type=String,Description="Consequence annotations from Ensembl VEP. Format: //' \
                -e 's/|/\t/g' \
                -e 's/">//' \
            | tr -d '\n'
        )
        printf '%s%s\tIsLocalPLP\tIsClinvarPLP\tIsException\tIsLOF\tIsDM\tFORMAT\t%s\n' \
            "$split_header" "$csq_header" "{wildcards.sample}" \
            > {output.tsv}

        {params.bcftools} +split-vep {output.vcf} \
            -f '%CHROM\t%POS\t%ID\t%REF\t%ALT\t%QUAL\t%FILTER\t%CSQ\t%IsLocalPLP\t%IsClinvarPLP\t%IsException\t%IsLOF\t%IsDM\t%FORMAT\n' \
            -A tab -d >> {output.tsv}
        """

rule trio_split:
    container:
        runtime_container("SNV_trio_split")
    input:
        rank = "08_ped/{trioID}.rank.txt",
        vcf = "01_SNV/"+batch+".WES.flt.vcf.gz",
    output:
        vcf = "02_split/{trioID}.split.trio.vcf"
    params:
        trio="{trioID}",
        splitPl=splitPl,
        bcftools=bcftools,
        whitelistV4=whitelistV4,
        perl=perl
    shell:
        """
        {params.perl} {params.splitPl} -rank {input.rank} -i {input.vcf} -o {output.vcf} -s {params.trio}.trio -bcftools {params.bcftools} -whitelist {params.whitelistV4}
        """

def get_fam_lenient_vcf(wildcards):
    if wildcards.pedigree in config.get("BKWpedigree", []):
        return "01_SNV/" + batch + ".lenient.bkw.flt.vcf.gz"
    return "01_SNV/" + batch + ".lenient.flt.vcf.gz"

rule fam_split_lenient:
    container:
        runtime_container("SNV_fam_split_lenient")
    input:
        rank = "08_ped/{pedigree}.rank.txt",
        vcf = get_fam_lenient_vcf
    output:
        vcf = temp("02_split/{pedigree}.split.fam.raw.vcf")
    params:
        splitPl=splitPl,
        bcftools=bcftools,
        whitelistV4=whitelistV4,
        perl=perl
    shell:
        """
        {params.perl} {params.splitPl} -rank {input.rank} -i {input.vcf} -o {output.vcf} -s {wildcards.pedigree}.fam -bcftools {params.bcftools} -whitelist {params.whitelistV4}
        """

rule fam_split_lenient_correct:
    container:
        runtime_container("SNV_fam_split_lenient_correct")
    input:
        vcf = "02_split/{pedigree}.split.fam.raw.vcf",
        cram = expand("00_PreCalling/{sample}.deduped.cram",sample=SAMPLES),
        crai = expand("00_PreCalling/{sample}.deduped.cram.crai",sample=SAMPLES)
    output:
        vcf = "02_split/{pedigree}.split.fam.vcf"
    params:
        cram_dir = '00_PreCalling',
        python3Path = python3Path,
        dpCorrectPy = dpCorrectPy,
        reference = reference,
        bcftools = bcftools,
        pandepth = pandepth
    shell:
        """
        {params.python3Path} {params.dpCorrectPy} -i {input.vcf} -o {output.vcf} -c {params.cram_dir} -r {params.reference} --bcftools {params.bcftools} --pandepth {params.pandepth} --threads {threads}
        """

rule fam_split_strict:
    container:
        runtime_container("SNV_fam_split_strict")
    input:
        rank = "08_ped/{pedigree}.rank.txt",
        vcf = "01_SNV/"+batch+".blacklist.flt.vcf.gz"
    output:
        vcf = "02_split/{pedigree}.split.flt.fam.raw.vcf"
    params:
        splitPl = splitPl,
        bcftools = bcftools,
        whitelistV4 = whitelistV4,
        perl=perl
    shell:
        """
        {params.perl} {params.splitPl} -rank {input.rank} -i {input.vcf} -o {output.vcf} -s {wildcards.pedigree}.fam -bcftools {params.bcftools} -whitelist {params.whitelistV4}
        """

rule fam_split_strict_correct:
    container:
        runtime_container("SNV_fam_split_strict_correct")
    input:
        vcf = "02_split/{pedigree}.split.flt.fam.raw.vcf",
        cram = expand("00_PreCalling/{sample}.deduped.cram",sample=SAMPLES),
        crai = expand("00_PreCalling/{sample}.deduped.cram.crai",sample=SAMPLES)
    output:
        vcf = "02_split/{pedigree}.split.flt.fam.dpCorrected.vcf",
        vcfGz = "02_split/{pedigree}.split.flt.fam.dpCorrected.vcf.gz",
        vcfTbi = "02_split/{pedigree}.split.flt.fam.dpCorrected.vcf.gz.tbi"
    params:
        cram_dir = '00_PreCalling',
        python3Path = python3Path,
        dpCorrectPy = dpCorrectPy,
        reference = reference,
        bcftools = bcftools,
        pandepth = pandepth,
        bgzip = bgzip,
        tabix = tabix
    shell:
        """
        {params.python3Path} {params.dpCorrectPy} -i {input.vcf} -o {output.vcf} -c {params.cram_dir} -r {params.reference} --bcftools {params.bcftools} --pandepth {params.pandepth} --threads {threads}
        {params.bgzip} -c {output.vcf} > {output.vcfGz} && {params.tabix} -fp vcf {output.vcfGz}
        """

rule fam_flt_modifier:
    container:
        runtime_container("SNV_fam_flt_modifier")
    input:
        vcfGz = "02_split/{pedigree}.split.flt.fam.dpCorrected.vcf.gz",
        vcfTbi = "02_split/{pedigree}.split.flt.fam.dpCorrected.vcf.gz.tbi",
        ped = "08_ped/{pedigree}.ped"
    output:
        vcf = "02_split/{pedigree}.split.flt.fam.vcf",
        modifierVcf = "02_split/{pedigree}.modifier.tmp.vcf.gz",
        modifierTbi = "02_split/{pedigree}.modifier.tmp.vcf.gz.tbi",
        modifierVcf2 = "02_split/{pedigree}.modifier.tmp2.vcf",

        modifierleft_tsv = "02_split/{pedigree}.modifier.left.tmp.tsv",
        modifierleftGz = "02_split/{pedigree}.modifier.left.tmp.vcf.gz",
        modifierleftGzTbi = "02_split/{pedigree}.modifier.left.tmp.vcf.gz.tbi",

        modifierFltVcfGz = temp("02_split/{pedigree}.modifier.tmp.flt.vcf.gz"),
        modifierFltTbi = temp("02_split/{pedigree}.modifier.tmp.flt.vcf.gz.tbi")
    params: 
        bcftools = bcftools,
        selectModifierPl = selectModifierPl,
        whitelistV1 = whitelistV1,
        bgzip = bgzip,
        tabix = tabix,
        perl = perl
    # resources:
    #     qsub_vf=12000
    # threads:8
    shell:
        r"""
        {params.bcftools} +split-vep {input.vcfGz} \
            -f '%CHROM\t%POS\t%ID\t%REF\t%ALT\t%QUAL\t%FILTER\t%CSQ\n' \
            -A tab -s worst -d \
        | awk -F "\t" '$10=="MODIFIER"' \
        | awk -F "\t" 'BEGIN{{OFS="\t"}}{{print $1,$2,$3,$4,$5,$6,$7,"WORSTIMPACT=MODIFIER"}}' \
        | sed '1i##fileformat=VCFv4.2\n##INFO=<ID=WORSTIMPACT,Number=.,Type=String,Description="">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO' \
        | {params.bgzip} -c > {output.modifierVcf} \
        && {params.tabix} -fp vcf {output.modifierVcf}

        # 不在白名单且不在保留规则中的 modifier
        {params.bcftools} isec -n~11 -c none -w 1 \
            {input.vcfGz} {output.modifierVcf} \
            -Ov -o {output.modifierVcf2}

        {params.perl} {params.selectModifierPl} \
            -i {output.modifierVcf2} \
            -ped {input.ped} \
            -tsv {output.modifierleft_tsv} \
            -bcftools {params.bcftools}

        cut -f 1-7 {output.modifierleft_tsv} \
        | uniq \
        | awk -F "\t" 'BEGIN{{OFS="\t"}}{{print $1,$2,$3,$4,$5,$6,$7,"WORSTIMPACT=MODIFIER"}}' \
        | sed '1i##fileformat=VCFv4.2\n##INFO=<ID=WORSTIMPACT,Number=.,Type=String,Description="">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO' \
        | {params.bgzip} -c > {output.modifierleftGz} \
        && {params.tabix} -fp vcf {output.modifierleftGz}

        {params.bcftools} isec -n~100 -c none -w 1 \
            {output.modifierVcf} {params.whitelistV1} {output.modifierleftGz} \
            -Oz -o {output.modifierFltVcfGz} \
        && {params.tabix} -fp vcf {output.modifierFltVcfGz}

        {params.bcftools} isec -n~10 -c none -w 1 \
            {input.vcfGz} {output.modifierFltVcfGz} \
            -Ov -o {output.vcf}
        """

rule fam_slivar_lenient:
    container:
        runtime_container("SNV_fam_slivar_lenient")
    input:
        ped = "08_ped/{pedigree}.ped",
        vcf = "02_split/{pedigree}.split.fam.vcf"
    output:
        vcf = "02_split/{pedigree}.slivar.vcf",
        tsv = "02_split/{pedigree}.slivar.tsv"
    params:
        slivarPl = slivarPl,
        bcftools = bcftools,
        slivar = slivar,
        slivarJs = slivarJs,
        slivarGnomad = slivarGnomad,
        perl = perl
    shell:
        "{params.perl} {params.slivarPl} -ped {input.ped} -i {input.vcf} -v {output.vcf} -t {output.tsv} -bcftools {params.bcftools} -slivar {params.slivar} --slivar-js {params.slivarJs} --slivar-gnomad {params.slivarGnomad}"

rule fam_slivar_strict:
    container:
        runtime_container("SNV_fam_slivar_strict")
    input:
        ped = "08_ped/{pedigree}.ped",
        vcf = "02_split/{pedigree}.split.flt.fam.vcf"
    output:
        vcf = "02_split/{pedigree}.flt.slivar.vcf",
        tsv = "02_split/{pedigree}.flt.slivar.tsv"
    params:
        slivarPl = slivarPl,
        bcftools = bcftools,
        slivar = slivar,
        slivarJs = slivarJs,
        slivarGnomad = slivarGnomad,
        perl = perl
    shell:
        "{params.perl} {params.slivarPl} -ped {input.ped} -i {input.vcf} -v {output.vcf} -t {output.tsv} -bcftools {params.bcftools} -slivar {params.slivar} --slivar-js {params.slivarJs} --slivar-gnomad {params.slivarGnomad}"


rule fam_SNVannotation_strict:
    container:
        runtime_container("SNV_fam_SNVannotation_strict")
    input:
        rank = "08_ped/{pedigree}.rank.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.tsv",
        slivar = "02_split/{pedigree}.flt.slivar.tsv"
    output:
        flt = "01_SNV/{pedigree}.raw.flt.tsv"
    params:
        snvRust=snvRust,
        gnuSort=gnuSort,
        liftOver=liftOver
    shell:
        "{params.snvRust} -r {input.rank} -i {input.slivar} -o {output.flt} -v {input.veptsv} --cfg config.yaml --liftover {params.liftOver} --sort {params.gnuSort} --threads {threads}"


rule fam_SNVannotation_lenient:
    container:
        runtime_container("SNV_fam_SNVannotation_lenient")
    input:
        rank = "08_ped/{pedigree}.rank.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.tsv",
        slivar = "02_split/{pedigree}.slivar.tsv"
    output:
        verbose = "01_SNV/{pedigree}.verbose.tsv"
    params:
        snvRust=snvRust,
        gnuSort=gnuSort,
        liftOver=liftOver
    shell:
        "{params.snvRust} -r {input.rank} -i {input.slivar} -o {output.verbose} -v {input.veptsv} --cfg config.yaml --liftover {params.liftOver} --sort {params.gnuSort} --threads {threads}"

rule solo_SNVannotation_strict:
    container:
        runtime_container("SNV_solo_SNVannotation_strict")
    input:
        gender = "07_QC/"+batch+".gender.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.tsv",
        split = "02_split/{sample}.split.flt.tsv"
    output:
        outflt = "01_SNV/{sample}.raw.flt.tsv"
    params:
        sampename="{sample}",
        snvRust=snvRust,
        gnuSort=gnuSort,
        liftOver=liftOver,
        phenotype=lambda wildcards: config["phenotype"].get(wildcards.sample, "")
    shell: # gender要提前获取
        """
        gender=$(awk -F',' -v sample="{params.sampename}" \
        '$1 == sample {{g=$2; sub(/\r$/, "", g); print g; found=1; exit}}
         END {{if (!found) exit 1}}' \
        {input.gender})
        {params.snvRust} -g "$gender" -p {params.phenotype:q} -i {input.split} -o {output.outflt} -v {input.veptsv} --cfg config.yaml --liftover {params.liftOver} --sort {params.gnuSort} --threads {threads}
        """

rule solo_SNVannotation_lenient:
    container:
        runtime_container("SNV_solo_SNVannotation_lenient")
    input:
        gender = "07_QC/"+batch+".gender.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.tsv",
        split = "02_split/{sample}.split.tsv"
    output:
        verbose = "01_SNV/{sample}.verbose.tsv"
    params:
        sampename="{sample}",
        snvRust=snvRust,
        gnuSort=gnuSort,
        liftOver=liftOver,
        phenotype=lambda wildcards: config["phenotype"].get(wildcards.sample, "")
    shell:
        """
        gender=$(awk -F',' -v sample="{params.sampename}" \
        '$1 == sample {{g=$2; sub(/\r$/, "", g); print g; found=1; exit}}
         END {{if (!found) exit 1}}' \
        {input.gender})
        {params.snvRust} -g "$gender" -p {params.phenotype:q} -i {input.split} -o {output.verbose} -v {input.veptsv} --cfg config.yaml --liftover {params.liftOver} --sort {params.gnuSort} --threads {threads}
        """

rule solo_verbose_replace_flt:
    container:
        runtime_container("SNV_solo_verbose_replace_flt")
    input:
        verbose = "01_SNV/{bkwsample}.verbose.tsv",
        rawflt = "01_SNV/{bkwsample}.raw.flt.tsv"
    output:
        flt = "01_SNV/{bkwsample}.flt.tsv"
    params:
        replaceBKW = replaceBKW,
        python3Path = python3Path,
        bkwgenelist = bkwgenelist,
    wildcard_constraints:
        bkwsample="|".join(re.escape(sample) for sample in BKWSAMPLES) or r"(?!)"
    shell:
        """
        {params.python3Path} {params.replaceBKW} -v {input.verbose} -f {input.rawflt} -l {params.bkwgenelist} -o {output.flt}
        """

rule solo_normal_rawflt_to_flt:
    container:
        runtime_container("SNV_solo_normal_rawflt_to_flt")
    input:
        rawflt="01_SNV/{sample}.raw.flt.tsv"
    output:
        flt="01_SNV/{sample}.flt.tsv"
    wildcard_constraints:
        sample="|".join(re.escape(sample) for sample in NON_BKW_SAMPLES) or r"(?!)"
    shell:
        """
        cp {input.rawflt} {output.flt}
        """

rule fam_verbose_replace_flt:
    container:
        runtime_container("SNV_fam_verbose_replace_flt")
    input:
        verbose = "01_SNV/{pedigree}.verbose.tsv",
        rawflt = "01_SNV/{pedigree}.raw.flt.tsv"
    output:
        flt = "01_SNV/{pedigree}.flt.tsv"
    params:
        replaceBKW = replaceBKW,
        python3Path = python3Path,
        bkwgenelist = bkwgenelist,
    wildcard_constraints:
        pedigree="|".join(re.escape(pedigree) for pedigree in BKWPEDIGREE) or r"(?!)"
    shell:
        """
        {params.python3Path} {params.replaceBKW} -v {input.verbose} -f {input.rawflt} -l {params.bkwgenelist} -o {output.flt}
        """

rule fam_normal_rawflt_to_flt:
    container:
        runtime_container("SNV_fam_normal_rawflt_to_flt")
    input:
        rawflt="01_SNV/{pedigree}.raw.flt.tsv"
    output:
        flt="01_SNV/{pedigree}.flt.tsv"
    wildcard_constraints:
        pedigree="|".join(re.escape(pedigree) for pedigree in NON_BKW_PEDIGREE) or r"(?!)"
    shell:
        """
        cp {input.rawflt} {output.flt}
        """


rule batchVcf2Vaf:
    container:
        runtime_container("SNV_batchVcf2Vaf")
    input:
        qualvcf="01_SNV/"+batch+".qual.flt.vcf.gz",
    output:
        vafvcf="01_SNV/"+batch+".vaf.flt.vcf",
        vaf="01_SNV/"+batch+".vaf",
        vafgz="01_SNV/"+batch+".vaf.gz",
    params:
        bcftools=bcftools,
        bgzip = bgzip,
        tabix = tabix
    shell:
        """
        {params.bcftools} view -i  'N_ALT=1 & AVG(FMT/DP)>8 & MIN(FMT/DP)>5 & MIN(FMT/GQ)>15 & QUAL > 30 & MAX(FORMAT/AD[*:1]/FORMAT/DP[*]) > 0.1 ' {input.qualvcf} > {output.vafvcf}
        {params.bcftools} +fill-tags {output.vafvcf} -- -t FORMAT/VAF |{params.bcftools} query -H -f '%CHROM\t%POS\t%END\t%REF/%ALT[\t%VAF]\n' > {output.vaf}
        {params.bgzip} -c -@ {threads} {output.vaf}> {output.vafgz}
        """

rule splitVcf:
    container:
        runtime_container("SNV_splitVcf")
    input:
        qualvcf="01_SNV/"+batch+".qual.flt.vcf.gz",
        normvcf="01_SNV/"+batch+".normalize.vcf.gz",
        vafvcf="01_SNV/"+batch+".vaf.flt.vcf",
    output:
        vcf = "01_SNV/{sample}.vcf",
        rawvcf = "01_SNV/{sample}.raw.vcf.gz",
        vafFltvcf="01_SNV/{sample}.vaf.flt.vcf",
        vaf="01_SNV/{sample}.vaf",
        stage=temp("01_SNV/{sample}.g2.vaf.split.done"),
    params:
        samplename="{sample}",
        bcftools=bcftools,
        tabix = tabix
    shell:
       """
       {params.bcftools} view -s {params.samplename} {input.qualvcf}|{params.bcftools} view -e 'GT=="mis" || GT=="0/0" ||FORMAT/DP<30' > {output.vcf}
       {params.bcftools} view -s {params.samplename} {input.normvcf}|{params.bcftools} view -e 'GT=="mis" || GT=="0/0"' -Oz -o {output.rawvcf} && {params.tabix} -fp vcf {output.rawvcf}
       {params.bcftools} view -s {params.samplename} {input.vafvcf}|{params.bcftools} view -e 'GT=="mis" || GT=="0/0" ||FORMAT/DP<30 ' > {output.vafFltvcf}
       {params.bcftools} +fill-tags {output.vafFltvcf} -- -t FORMAT/VAF |{params.bcftools} query -f '%CHROM\t%POS\t%END\t%REF/%ALT[\t%VAF]\n' > {output.vaf}
       sed -i  '1i\chr\tstart\tend\tallele\t{params.samplename}' {output.vaf}
       touch {output.stage}
       """

rule bedGraphVaf:
    container:
        runtime_container("SNV_bedGraphVaf")
    input:
        vaf="01_SNV/{sample}.vaf",
        stage="01_SNV/{sample}.g2.vaf.split.done",
    output:
        vaf_bedGraph="01_SNV/{sample}.vaf.bedGraph.gz",
        stage=temp("01_SNV/{sample}.g2.vaf.done"),
    benchmark:
        performance_benchmark(config, "SNV_bedGraphVaf", "{sample}")
    params:
        bgzip = bgzip,
        tabix = tabix
    shell:
       """
       awk -F'\\t' 'NR>1 {{OFS="\\t"; print $1, $2, $3, $5}}' {input.vaf} | {params.bgzip} -c -@ {threads} > {output.vaf_bedGraph}
       {params.tabix} -fp bed {output.vaf_bedGraph}
       touch {output.stage}
       """
