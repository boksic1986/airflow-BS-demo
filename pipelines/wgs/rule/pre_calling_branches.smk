"""Production branches that consume the standard G1 outputs."""

# SCRIPT_DIR = config["execution"]["script_dir"]
from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container

CONTAINER_TOOLS = config["container_tools"]["pre"]
CONTAINER_RESOURCES = config.get("container_resources", {})

covDistR = CONTAINER_TOOLS["covDistR"]
SamtoolsPath = CONTAINER_TOOLS["samtools"]
bamdstPath = CONTAINER_TOOLS["bamdst"]
mityPath = CONTAINER_TOOLS["mity"]

smoovePath = CONTAINER_TOOLS["smoove"]
smooveExclude = CONTAINER_RESOURCES["smoove_exclude"]
clusterIdentifier = CONTAINER_TOOLS["cluster_identifier"]


reference = config["genome"]["fasta"]
cytoband = config["database"]["cytobandTxt"]
mtbed = config["bed"]["MT_bed"]
mtQC = config["src"]["MTQC"]

rule QCStaticPlot:
    container:
        runtime_container("pre_process_QCStaticPlot")
    input:
        cov=lambda wc: f"07_QC/{wc.sample}.deduped.bam.1.cov.bed",
        isize=lambda wc: f"07_QC/{wc.sample}.deduped.bam.1.iSize.tsv",
        chromstat=lambda wc: f"07_QC/{wc.sample}.deduped.bam.1.chromStat.txt",
        depth=lambda wc: f"07_QC/{wc.sample}.deduped.bam.1.depth",
    output:
        covdist="07_QC/{sample}.covDist.png",
        chrdepth="07_QC/{sample}.chrDepth.png",
        chrdist="07_QC/{sample}.chrDist.png",
        isizedist="07_QC/{sample}.isizeDist.png",
    params:
        predix="{sample}",
        covDistR=covDistR,
        cytoband=cytoband,
    shell:
        """
        {params.covDistR} --cov {input.cov} --isize {input.isize} --chromStat {input.chromstat} -d {input.depth} --cytoband {params.cytoband} --outfile {params.predix} --maxDepth 100
        mv {params.predix}.covDist.png {output.covdist}
        mv {params.predix}.chrDepth.png {output.chrdepth}
        mv {params.predix}.chrDist.png {output.chrdist}
        mv {params.predix}.isizeDist.png {output.isizedist}
        """

rule mtQC:
    container:
        runtime_container("pre_process_mtQC")
    input:
        cram=lambda wc: f"00_PreCalling/{wc.sample}.deduped.cram",
        idx=lambda wc: f"00_PreCalling/{wc.sample}.deduped.cram.crai"
    output:
        mtbam='00_PreCalling/{sample}.deduped.chrM.bam',
        mtbamindex='00_PreCalling/{sample}.deduped.chrM.bam.bai',
        mtqc='07_QC/MT/{sample}.MT.QC.txt'
    params:
        predix="{sample}",
        samtoolspath=SamtoolsPath,
        bamdstPath=bamdstPath,
        mtQC=mtQC,
        mtbed=mtbed
    shell:
         """
        {params.samtoolspath} view -b -h -@ {threads} {input.cram} chrM -o {output.mtbam}
        {params.samtoolspath} index -b {output.mtbam}
        mkdir 07_QC/MT/{params.predix}
        {params.bamdstPath} -p {params.mtbed} -f 0 --uncover 20 -o 07_QC/MT/{params.predix} {output.mtbam}
        python3 {params.mtQC} -I 07_QC/MT/ -O {output.mtqc} -s {params.predix}
        """

rule Smooverun:
    container:
        runtime_container("pre_process_Smooverun")
    input:
        Bam=lambda wc: f"00_PreCalling/{wc.sample}.deduped.bam",
        bai=lambda wc: f"00_PreCalling/{wc.sample}.deduped.bam.bai"
    output:
        outfile="00_PreCalling/{sample}-smoove.genotyped.vcf.gz",
        index="00_PreCalling/{sample}-smoove.genotyped.vcf.gz.csi"
    params:
        name="{sample}",
        excludechroms='~^GL,~^HLA,~_random,~^chrUn,~alt,~decoy',
        smoovePath=smoovePath,
        smooveExclude=smooveExclude,
        reference=reference
    shell:
         """
        {params.smoovePath} call -x -d -F --name {params.name} --exclude {params.smooveExclude} --fasta {params.reference} -p {threads} --excludechroms {params.excludechroms} --genotype {input.Bam} --outdir 00_PreCalling/
        """

rule mityCall:
    container:
        runtime_container("pre_process_mityCall")
    input:
         Bam=lambda wc: f"00_PreCalling/{wc.sample}.deduped.bam",
         bai=lambda wc: f"00_PreCalling/{wc.sample}.deduped.bam.bai"
    output:
         gzvcf="00_PreCalling/{sample}.mity.vcf.gz",
    params:
          reference="hg38",
          prefix="{sample}",
          callingdir=directory("00_PreCalling/"),
          mityPath=mityPath
    shell:
          """
          {params.mityPath} call --reference {params.reference} --prefix {params.prefix} --out-folder-path {params.callingdir} --normalise {input.Bam}
          """

rule MEICall:
    container:
        runtime_container("pre_process_MEICall")
    input:
        Bam=lambda wc: f"00_PreCalling/{wc.sample}.deduped.bam",
        bai=lambda wc: f"00_PreCalling/{wc.sample}.deduped.bam.bai"
    output:
        clusters = "00_PreCalling/{sample}.scramble.clusters.txt",
    params:
        clusterIdentifier=clusterIdentifier,
    shell:
        """
        {params.clusterIdentifier} {input.Bam} > {output.clusters}
        """
