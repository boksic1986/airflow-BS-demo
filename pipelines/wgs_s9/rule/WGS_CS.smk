"""
@file: WGS_CS.smk
@time: 2024/04/03
@version 1.0
WGS SNV CS pipeline from gvcf file for couple samples
"""
import os
import re
import pandas as pd
sampleInfoFile=config["sample_info"]
csID=config["CS"]
batch=config["batch"]

SNVannotation=config["Self-built-Tools"]["SNV_MT"]["SNVannotation"]
makecsrankPl=config["Self-built-Tools"]["SNV_MT"]["makeCSrankPl"]
makecsvcfPl=config["Self-built-Tools"]["SNV_MT"]["makeCSvcfPl"]
markcstagPl=config["Self-built-Tools"]["SNV_MT"]["markCSTagPl"]
slivarPl=config["Self-built-Tools"]["SNV_MT"]["slivarPl"]
splitPl=config["Self-built-Tools"]["SNV_MT"]["splitPl"]
createPed=config["Self-built-Tools"]["SNV_MT"]["createPed"]
dpCorrectPy=config["Self-built-Tools"]["SNV_MT"]["dpCorrectPy"]
bcftools=config["bioSoft"]["bcftoolsPath"]
slivar=config["bioSoft"]["slivar"]
pandepth=config["bioSoft"]["pandepth"]
python3Path=config['bioSoft']['python3']
reference=config["reference"]['hg38']["genome"]
#bcftoolsPath=os.path.dirname(bcftools)
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
		expand("01_SNV/{csID}-CS.markCS.flt.tsv",csID=config["CS"]),
		expand("01_SNV/{csID}-CS.markCS.verbose.tsv",csID=config["CS"])

rule createCSfile:
	input:
		rank ="08_ped/"+batch+".rank.txt",
	output:
		ped = "08_ped/"+batch+"-CS.ped",
		csrank ="08_ped/"+batch+"-CS.rank.txt",
		famPed = expand("08_ped/{csID}-CS.ped",csID=config["CS"]),
		famRank = expand("08_ped/{csID}-CS.rank.txt",csID=config["CS"]),
		famRankcs = expand("08_ped/{csID}-CS.rankcs.txt",csID=config["CS"])
	resources:
		qsub_vf=100
	threads:1
	shell:
		"perl {makecsrankPl} -in_rank {input.rank} -out_rank {output.csrank} -ped {output.ped}"

rule fam_split_lenient_CS:
    input:
        rank = "08_ped/{csID}-CS.rankcs.txt",
        vcf = "01_SNV/"+batch+".lenient.flt.vcf"
    output:
        vcf = temp("02_split/{csID}-CS.split.fam.raw.vcf")
    resources:
        qsub_vf=10000
    threads:1
    run:
        import re
        famPrefix = re.sub(r'.split.fam.raw.vcf','',output.vcf)
        famPrefix = re.sub(r'02_split/','',famPrefix)
        fprefix = famPrefix + '.fam'
        shell('perl {splitPl} -rank {input.rank} -vcf {input.vcf} -i {fprefix} -bcftools {bcftools}')

rule  fam_split_lenient_CS_correct:
    input:
        vcf = "02_split/{csID}-CS.split.fam.raw.vcf",
        cram = expand("00_PreCalling/{sample}.deduped.cram",sample=config["sample"]),
        crai = expand("00_PreCalling/{sample}.deduped.cram.crai",sample=config["sample"])
    output:
        vcf = "02_split/{csID}-CS.split.fam.vcf"
    resources:
        qsub_vf=20000
    threads:8
    params:
        cram_dir = '00_PreCalling'
    shell:
        """
        {python3Path}/python3 {dpCorrectPy} -i {input.vcf} -o {output.vcf} -c {params.cram_dir} -r {reference} --bcftools {bcftools} --pandepth {pandepth}
        """

rule fam_split_strict_CS:
    input:
        rank = "08_ped/{csID}-CS.rankcs.txt",
        vcf = "01_SNV/"+batch+".flt.vcf",
    output:
        vcf = temp("02_split/{csID}-CS.split.flt.fam.raw.vcf")
    resources:
        qsub_vf = 10000
    threads:1
    run:
        import re
        famPrefix = re.sub(r'.split.flt.fam.raw.vcf','',output.vcf)
        famPrefix = re.sub(r'02_split/','',famPrefix)
        faprefix = famPrefix + '.fam'
        shell('perl {splitPl} -rank {input.rank} -vcf {input.vcf} -i {faprefix} -bcftools {bcftools}')

rule fam_split_strict_CS_correct:
    input:
        vcf = "02_split/{csID}-CS.split.flt.fam.raw.vcf",
        cram = expand("00_PreCalling/{sample}.deduped.cram",sample=SAMPLES),
        crai = expand("00_PreCalling/{sample}.deduped.cram.crai",sample=SAMPLES)
    output:
        vcf = "02_split/{csID}-CS.split.flt.fam.vcf"
    resources:
        qsub_vf=20000
    threads:8
    params:
        cram_dir = '00_PreCalling'
    shell:
        """
        {python3Path}/python3 {dpCorrectPy} -i {input.vcf} -o {output.vcf} -c {params.cram_dir} -r {reference} --bcftools {bcftools} --pandepth {pandepth}
        """

rule makecsvcf:
	input:
		vcf = "02_split/{csID}-CS.split.fam.vcf"
	output:
		vcf = temp("02_split/{csID}-CS.split.vcf")
	resources:
		qsub_vf=10000
	threads:1
	run:
		shell('perl {makecsvcfPl} -in_vcf {input.vcf} -out_vcf {output.vcf}')

rule makecsvcf_flt:
	input:
		vcf = "02_split/{csID}-CS.split.flt.fam.vcf"
	output:
		vcf = temp("02_split/{csID}-CS.split.flt.vcf")
	resources:
		qsub_vf = 10000
	threads:1
	run:
		shell('perl {makecsvcfPl} -in_vcf {input.vcf} -out_vcf {output.vcf}')

rule fam_slivar_lenient_CS:
    input:
        ped = "08_ped/{csID}-CS.ped",
        flt_vcf = "02_split/{csID}-CS.split.vcf"
    output:
        vcf = "02_split/{csID}-CS.slivar.vcf",
        tsv = "02_split/{csID}-CS.slivar.tsv"
    resources:
        qsub_vf=10000
    threads:1
    shell:
        "perl {slivarPl} -ped {input.ped} -i {input.flt_vcf} -v {output.vcf} -t {output.tsv} -bcftools {bcftools} -slivar {slivar} -type CS"

rule fam_slivar_strict_CS:
    input:
        ped = "08_ped/{csID}-CS.ped",
        flt_vcf = "02_split/{csID}-CS.split.flt.vcf"
    output:
        vcf = "02_split/{csID}-CS.flt.slivar.vcf",
        tsv = "02_split/{csID}-CS.flt.slivar.tsv"
    resources:
        qsub_vf=10000
    threads:1
    shell:
        "perl {slivarPl} -ped {input.ped} -i {input.flt_vcf} -v {output.vcf} -t {output.tsv} -bcftools {bcftools} -slivar {slivar} -type CS"

rule fam_SNVannotation_strict_CS:
    input:
        rank = "08_ped/{csID}-CS.rank.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.flt.tsv",
        slivar = "02_split/{csID}-CS.flt.slivar.tsv"
    output:
        flt = "01_SNV/{csID}-CS.flt.tsv"
    resources:
        qsub_vf=10000
    params: SNVannotation=SNVannotation
    threads:1
    shell:
        "perl {params.SNVannotation} -rank {input.rank} -i {input.slivar} -o {output.flt} -type CS -cfg config.yaml"

rule fam_SNVannotation_lenient_CS:
    input:
        rank = "08_ped/{csID}-CS.rank.txt",
        veptsv = "01_SNV/"+batch+".vepLocation.lenient.flt.tsv",
        slivar = "02_split/{csID}-CS.slivar.tsv"
    output:
        verbose = "01_SNV/{csID}-CS.verbose.tsv"
    resources:
        qsub_vf=10000
    threads:1
    params: SNVannotation=SNVannotation
    shell:
        "perl {params.SNVannotation} -rank {input.rank} -i {input.slivar} -o {output.verbose} -type CS -cfg config.yaml"


rule markCS_flt:
	input:
		flt = "01_SNV/{csID}-CS.flt.tsv"
	output:
		markcsflt = "01_SNV/{csID}-CS.markCS.flt.tsv"
	resources:
		qsub_vf=10000
	threads:1
	shell:
		"perl {markcstagPl} -i {input.flt} -o {output.markcsflt} -cfg config.yaml"

rule markCS:
	input:
		verbose = "01_SNV/{csID}-CS.verbose.tsv"
	output:
		markcsverbose = "01_SNV/{csID}-CS.markCS.verbose.tsv"
	resources:
		qsub_vf=10000
	threads:1
	shell:
		"perl {markcstagPl} -i {input.verbose} -o {output.markcsverbose} -cfg config.yaml"
