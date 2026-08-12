# container: config["containers"]["CS"]

from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container

CONTAINER_TOOLS=config.get("container_tools", {}).get("CS", {})
CONTAINER_RESOURCES=config.get("container_resources", {})
perl=CONTAINER_TOOLS["perl"]
bcftools=CONTAINER_TOOLS["bcftools"]
slivar=CONTAINER_TOOLS["slivar"]
pandepth=CONTAINER_TOOLS["pandepth"]
python3Path=CONTAINER_TOOLS["python3"]
liftOver=CONTAINER_TOOLS["liftOver"]
bgzip=CONTAINER_TOOLS["bgzip"]
tabix=CONTAINER_TOOLS["tabix"]
snvRust=CONTAINER_TOOLS["snv_cs"]
gnuSort=CONTAINER_TOOLS["gnu_sort"]
slivarJs=CONTAINER_RESOURCES.get("slivar_js", "/opt/wgs/resources/slivar/slivar-functions.V6.3.0.js")
slivarGnomad=CONTAINER_RESOURCES.get("slivar_gnomad", "/opt/wgs/resources/slivar/gnomad.hg38.v2.zip")

import re

csID=config["CS"]
batch=config["batch"]

BKWSAMPLES=config.get("BKWsampleList",[])
BKW_SAMPLE_PATTERN = "|".join(
    re.escape(sample) for sample in BKWSAMPLES
)

BKWCS_PATTERN = (
    rf"[^_]+_(?:{BKW_SAMPLE_PATTERN})(?:_.*)?"
    if BKWSAMPLES
    else r"(?!)"
)

NON_BKW_SAMPLES = [
    sample for sample in config.get("sample", [])
    if sample not in set(BKWSAMPLES)
]
NON_BKW_SAMPLE_PATTERN = "|".join(
    re.escape(sample) for sample in NON_BKW_SAMPLES
)

NON_BKWCS_PATTERN = (
    rf"[^_]+_(?:{NON_BKW_SAMPLE_PATTERN})(?:_.*)?"
    if NON_BKW_SAMPLES
    else r"(?!)"
)

makecsrankPl=config["src"]["makeCSrankPl"]
makecsvcfPl=config["src"]["makeCSvcfPl"]
markcstagPl=config["src"]["markCSTagPl"]
slivarPl=config["src"]["slivarPl"]
splitPl=config["src"]["splitPl"]
createPed=config["src"]["createPed"]
dpCorrectPy=config["src"]["dpCorrectPy"]
replaceBKW=config["src"]["replaceBKW"]
selectModifierPl=config['src']['selectModifierPl']

reference=config["genome"]["fasta"]
whitelistV1=config["database"]['whitelistV1']
whitelistV4=config["database"]["whitelistV4"]
bkwgenelist=config["database"]['bkwgenelist']


rule CSall:
    input:
        "08_ped/"+batch+"-CS.rank.txt",
        "08_ped/"+batch+"-CS.ped",
        expand("08_ped/{csID}-CS.ped",csID=config["CS"]),
        expand("08_ped/{csID}-CS.rank.txt",csID=config["CS"]),
        expand("08_ped/{csID}-CS.rankcs.txt",csID=config["CS"]),
        expand("02_split/{csID}-CS.split.fam.vcf",csID=config["CS"]),
        expand("02_split/{csID}-CS.split.flt.fam.vcf",csID=config["CS"]),
        expand("02_split/{csID}-CS.slivar.tsv",csID=config["CS"]),
        expand("02_split/{csID}-CS.flt.slivar.tsv",csID=config["CS"]),
        expand("01_SNV/{csID}-CS.flt.tsv",csID=config["CS"]),
        expand("01_SNV/{csID}-CS.verbose.tsv",csID=config["CS"]),
        expand("01_SNV/{csID}.markCS.flt.tsv",csID=config["CS"]),
        expand("01_SNV/{csID}.markCS.verbose.tsv",csID=config["CS"])

rule createCSfile:
    container:
        runtime_container("CS_createCSfile")
    input:
        rank ="08_ped/"+batch+".rank.txt",
    output:
        ped = "08_ped/"+batch+"-CS.ped",
        csrank ="08_ped/"+batch+"-CS.rank.txt",
        famPed = expand("08_ped/{csID}-CS.ped",csID=config["CS"]),
        famRank = expand("08_ped/{csID}-CS.rank.txt",csID=config["CS"]),
        famRankcs = expand("08_ped/{csID}-CS.rankcs.txt",csID=config["CS"])
    params:
        makecsrankPl = makecsrankPl,
        perl = perl
    shell:
        "{params.perl} {params.makecsrankPl} -in_rank {input.rank} -out_rank {output.csrank} -ped {output.ped}"

def fam_split_vcf(wildcards):
    csID = wildcards.csID
    sampleid = csID.split("_")[1]
    if sampleid in config.get("BKWsampleList", []):
        return "01_SNV/"+batch+".lenient.bkw.flt.vcf.gz"
    return "01_SNV/"+batch+".lenient.flt.vcf.gz"

rule fam_split_lenient_CS:
    container:
        runtime_container("CS_fam_split_lenient_CS")
    input:
        rank = "08_ped/{csID}-CS.rankcs.txt",
        vcf = fam_split_vcf
    output:
        vcf = temp("02_split/{csID}-CS.split.fam.raw.vcf")
    params:
        splitPl = splitPl,
        bcftools = bcftools,
        whitelistV4 = whitelistV4,
        perl = perl
    shell:
        "{params.perl} {params.splitPl} {params.splitPl} -rank {input.rank} -i {input.vcf} -o {output.vcf} -s {wildcards.csID}-CS.fam -bcftools {params.bcftools} -whitelist {params.whitelistV4}"

rule  fam_split_lenient_CS_correct:
    container:
        runtime_container("CS_fam_split_lenient_CS_correct")
    input:
        vcf = "02_split/{csID}-CS.split.fam.raw.vcf",
        cram = expand("00_PreCalling/{sample}.deduped.cram", sample=config["sample"]),
        crai = expand("00_PreCalling/{sample}.deduped.cram.crai", sample=config["sample"])
    output:
        vcf = "02_split/{csID}-CS.split.fam.vcf"
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

rule fam_split_strict_CS:
    container:
        runtime_container("CS_fam_split_strict_CS")
    input:
        rank = "08_ped/{csID}-CS.rankcs.txt",
        vcf = "01_SNV/"+batch+".blacklist.flt.vcf.gz",
    output:
        vcf = temp("02_split/{csID}-CS.split.flt.fam.raw.vcf")
    params:
        splitPl = splitPl,
        bcftools = bcftools,
        whitelistV4 = whitelistV4,
        perl = perl
    shell:
        "{params.perl} {params.splitPl} -rank {input.rank} -i {input.vcf} -o {output.vcf} -s {wildcards.csID}-CS.fam -bcftools {params.bcftools} -whitelist {params.whitelistV4}"

rule fam_split_strict_CS_correct:
    container:
        runtime_container("CS_fam_split_strict_CS_correct")
    input:
        vcf = "02_split/{csID}-CS.split.flt.fam.raw.vcf",
        cram = expand("00_PreCalling/{sample}.deduped.cram", sample=config["sample"]),
        crai = expand("00_PreCalling/{sample}.deduped.cram.crai", sample=config["sample"])
    output:
        vcf = "02_split/{csID}-CS.split.flt.fam.vcf"
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

rule makecsvcf:
    container:
        runtime_container("CS_makecsvcf")
    input:
        vcf = "02_split/{csID}-CS.split.fam.vcf"
    output:
        vcf = temp("02_split/{csID}-CS.split.vcf")
    params:
        makecsvcfPl=makecsvcfPl,
        perl=perl
    shell:
        "{params.perl} {params.makecsvcfPl} -in_vcf {input.vcf} -out_vcf {output.vcf}"

rule makecsvcf_flt:
    container:
        runtime_container("CS_makecsvcf_flt")
    input:
        vcf = "02_split/{csID}-CS.split.flt.fam.vcf"
    output:
        vcf = temp("02_split/{csID}-CS.split.flt.vcf")
    params:
        makecsvcfPl = makecsvcfPl,
        perl=perl
    shell:
        "{params.perl} {params.makecsvcfPl} -in_vcf {input.vcf} -out_vcf {output.vcf}"

rule CS_flt_modifier:
    container:
        runtime_container("CS_CS_flt_modifier")
    input:
        vcfGz = "02_split/{csID}-CS.split.flt.tmp.vcf.gz",
        vcfTbi = "02_split/{csID}-CS.split.flt.tmp.vcf.gz.tbi",
        ped = "08_ped/{csID}-CS.ped"
    output:
        vcf = "02_split/{csID}-CS.split.flt.vcf",
        modifierVcf = "02_split/{csID}-CS.modifier.tmp.vcf.gz",
        modifierTbi = "02_split/{csID}-CS.modifier.tmp.vcf.gz.tbi",
        modifierVcf2 = "02_split/{csID}-CS.modifier.tmp2.vcf",

        modifierleft_tsv = "02_split/{csID}-CS.modifier.left.tmp.tsv",
        modifierleftGz = "02_split/{csID}-CS.modifier.left.tmp.vcf.gz",
        modifierleftGzTbi = "02_split/{csID}-CS.modifier.left.tmp.vcf.gz.tbi",

        modifierFltVcfGz = temp("02_split/{csID}-CS.modifier.tmp.flt.vcf.gz"),
        modifierFltTbi = temp("02_split/{csID}-CS.modifier.tmp.flt.vcf.gz.tbi")
    # resources:
    #     qsub_vf=12000
    # threads:8
    params:
        bcftools = bcftools,
        selectModifierPl = selectModifierPl,
        whitelistV1 = whitelistV1,
        bgzip = bgzip,
        tabix = tabix,
        perl = perl
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

rule fam_slivar_lenient_CS:
    container:
        runtime_container("CS_fam_slivar_lenient_CS")
    input:
        ped = "08_ped/{csID}-CS.ped",
        flt_vcf = "02_split/{csID}-CS.split.vcf"
    output:
        vcf = "02_split/{csID}-CS.slivar.vcf",
        tsv = "02_split/{csID}-CS.slivar.tsv"
    params:
        slivarPl = slivarPl,
        bcftools = bcftools,
        slivar = slivar,
        slivarJs = slivarJs,
        slivarGnomad = slivarGnomad,
        perl = perl
    shell:
        "{params.perl} {params.slivarPl} -ped {input.ped} -i {input.flt_vcf} -v {output.vcf} -t {output.tsv} -bcftools {params.bcftools} -slivar {params.slivar} --slivar-js {params.slivarJs} --slivar-gnomad {params.slivarGnomad} -type CS"

rule fam_slivar_strict_CS:
    container:
        runtime_container("CS_fam_slivar_strict_CS")
    input:
        ped = "08_ped/{csID}-CS.ped",
        flt_vcf = "02_split/{csID}-CS.split.flt.vcf"
    output:
        vcf = "02_split/{csID}-CS.flt.slivar.vcf",
        tsv = "02_split/{csID}-CS.flt.slivar.tsv"
    params:
        slivarPl = slivarPl,
        bcftools = bcftools,
        slivar = slivar,
        slivarJs = slivarJs,
        slivarGnomad = slivarGnomad,
        perl = perl
    shell:
        "{params.perl} {params.slivarPl} -ped {input.ped} -i {input.flt_vcf} -v {output.vcf} -t {output.tsv} -bcftools {params.bcftools} -slivar {params.slivar} --slivar-js {params.slivarJs} --slivar-gnomad {params.slivarGnomad} -type CS"

rule fam_SNVannotation_strict_CS:
    container:
        runtime_container("CS_fam_SNVannotation_strict_CS")
    input:
        rank = "08_ped/{csID}-CS.rank.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.tsv",
        slivar = "02_split/{csID}-CS.flt.slivar.tsv"
    output:
        flt = "01_SNV/{csID}-CS.raw.flt.tsv"
    params:
        snvRust=snvRust,
        gnuSort=gnuSort,
        liftOver=liftOver
    shell:
        "{params.snvRust} -r {input.rank} -i {input.slivar} -o {output.flt} -v {input.veptsv} --type CS --cfg config.yaml --liftover {params.liftOver} --sort {params.gnuSort} --threads {threads}"


rule fam_SNVannotation_lenient_CS:
    container:
        runtime_container("CS_fam_SNVannotation_lenient_CS")
    input:
        rank = "08_ped/{csID}-CS.rank.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.tsv",
        slivar = "02_split/{csID}-CS.slivar.tsv"
    output:
        verbose = "01_SNV/{csID}-CS.verbose.tsv"
    params:
        snvRust=snvRust,
        gnuSort=gnuSort,
        liftOver=liftOver
    shell:
        "{params.snvRust} -r {input.rank} -i {input.slivar} -o {output.verbose} -v {input.veptsv} --type CS --cfg config.yaml --liftover {params.liftOver} --sort {params.gnuSort} --threads {threads}"


rule cs_verbose_replace_flt:
    container:
        runtime_container("CS_cs_verbose_replace_flt")
    input:
        verbose = "01_SNV/{bkwcs}-CS.verbose.tsv",
        rawflt = "01_SNV/{bkwcs}-CS.raw.flt.tsv"
    output:
        flt = "01_SNV/{bkwcs}-CS.flt.tsv"
    params:
        replaceBKW = replaceBKW,
        python3Path = python3Path,
        bkwgenelist = bkwgenelist,
    wildcard_constraints:
        bkwcs=BKWCS_PATTERN
    shell:
        """
        {params.python3Path} {params.replaceBKW} -v {input.verbose} -f {input.rawflt} -l {params.bkwgenelist} -o {output.flt}
        """


rule cs_normal_rawflt_to_flt:
    container:
        runtime_container("CS_cs_normal_rawflt_to_flt")
    input:
        rawflt="01_SNV/{cs}-CS.raw.flt.tsv"
    output:
        flt="01_SNV/{cs}-CS.flt.tsv"
    wildcard_constraints:
        cs=NON_BKWCS_PATTERN
    shell:
        """
        cp {input.rawflt} {output.flt}
        """


rule markCS_flt:
    container:
        runtime_container("CS_markCS_flt")
    input:
        flt = "01_SNV/{csID}-CS.flt.tsv"
    output:
        markcsflt = "01_SNV/{csID}.markCS.flt.tsv"
    params:
        markcstagPl = markcstagPl,
        perl = perl
    shell:
        "{params.perl} {params.markcstagPl} -i {input.flt} -o {output.markcsflt} -cfg config.yaml"

rule markCS:
    container:
        runtime_container("CS_markCS")
    input:
        verbose = "01_SNV/{csID}-CS.verbose.tsv"
    output:
        markcsverbose = "01_SNV/{csID}.markCS.verbose.tsv"
    params:
        markcstagPl = markcstagPl,
        perl = perl
    shell:
        "{params.perl} {params.markcstagPl} -i {input.verbose} -o {output.markcsverbose} -cfg config.yaml"
