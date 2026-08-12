# container: config["containers"]["MEI"]

from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container

CONTAINER_TOOLS=config.get("container_tools", {}).get("MEI", {})
Rscript=CONTAINER_TOOLS["Rscript"]
scrambleRscript=CONTAINER_TOOLS["scramble_script"]
scrambleInstallDir=CONTAINER_TOOLS["scramble_install_dir"]
samtools=CONTAINER_TOOLS["samtools"]
bcftools=CONTAINER_TOOLS["bcftools"]
bgzip=CONTAINER_TOOLS["bgzip"]
tabix=CONTAINER_TOOLS["tabix"]
VEP=CONTAINER_TOOLS["vep"]
python3Path=CONTAINER_TOOLS["python3"]
liftOver=CONTAINER_TOOLS["liftOver"]

MEI_SAMPLES=config["sample"]

vep_cache=config['biosoft']['vepCache']

reference=config["genome"]["fasta"]

meiSplitPy=config['src']['meiSplitPy']

meiRef=config['database']['meiRef']
geneDisease=config["database"]["geneDisease"]


def build_mei_sample_to_pedigree():
    mapping = {}
    for item in config.get("sample2pedigree", []):
        if ":" not in item:
            raise ValueError("Malformed sample2pedigree entry")
        sample, pedigree = (part.strip() for part in item.split(":", 1))
        if not sample or not pedigree:
            raise ValueError("Malformed sample2pedigree entry")
        if sample in mapping and mapping[sample] != pedigree:
            raise ValueError("A sample is assigned to multiple pedigrees")
        mapping[sample] = pedigree

    if any(sample not in mapping for sample in MEI_SAMPLES):
        raise ValueError(
            "Every configured MEI sample must have a sample2pedigree entry"
        )
    return mapping


MEI_SAMPLE_TO_PEDIGREE = build_mei_sample_to_pedigree()


def mei_family_raw_inputs(wildcards):
    pedigree = MEI_SAMPLE_TO_PEDIGREE[wildcards.sample]
    return [
        f"09_MEI/{sample}.raw.MEIs_MEIs.txt"
        for sample in MEI_SAMPLES
        if (
            sample != wildcards.sample
            and MEI_SAMPLE_TO_PEDIGREE.get(sample) == pedigree
        )
    ]


rule MEIall:
    input:
        expand("09_MEI/{sample}.MEIs.tsv",sample=config["sample"])

rule MEI:
    container:
        runtime_container("MEI_MEI")
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
        p_outprefix = "09_MEI/{sample}.raw.MEIs",
        Rscript = Rscript,
        scrambleRscript = scrambleRscript,
        scrambleInstallDir = scrambleInstallDir,
        samtools = samtools,
        meiRef = meiRef,
        reference = reference,
        bcftools = bcftools,
        tabix = tabix
    shell:
        """
        {params.Rscript} --vanilla {params.scrambleRscript} --install-dir={params.scrambleInstallDir:q} --mei-refs={params.meiRef} --ref={params.reference} --cluster-file={params.p_wkdir}/{input.clusters} --out-name={params.p_wkdir}/{params.p_outprefix} --mei-score=50 --nCluster=5 --eval-meis --threads {threads} --samtools {params.samtools}
        awk 'BEGIN{{OFS="\\t"}} /^##/ {{print; next}} /^#CHROM/ {{print "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">"; print $0 "\\tFORMAT\\t{params.p_s}"; next}} !/^#/ {{print $1,$2,$3,$4,$5,$6,$7,$8,"GT","./1"}}' {output.vcf} | {params.bcftools} view -Oz -o {output.gz} && {params.tabix} -fp vcf {output.gz}
        """

rule MEI_vep:
    container:
        runtime_container("MEI_MEI_vep")
    input:
        gz = "09_MEI/{sample}.raw.MEIs.vcf.gz",
        tbi = "09_MEI/{sample}.raw.MEIs.vcf.gz.tbi",
    output:
        vep_vcf = "09_MEI/{sample}.vep.MEIs.vcf.gz"
    params:
        bcftools = bcftools,
        VEP = VEP,
        vep_cache = vep_cache,
        reference = reference,
    shell:
        """
        {params.VEP} -i {input.gz} -o {output.vep_vcf} --dir_cache {params.vep_cache} --fasta {params.reference} --offline --cache --hgvs --hgvsg --symbol --canonical --total_length --force --force_overwrite --no_stats --vcf --compress_output bgzip --refseq --use_given_ref --assembly GRCh38 --fork {threads} --no_escape --xref_refseq --pick --failed 1 --dont_skip
        """

rule MEI_annotation:
    container:
        runtime_container("MEI_MEI_annotation")
    input:
        vep_vcf = "09_MEI/{sample}.vep.MEIs.vcf.gz",
        mei_raw = "09_MEI/{sample}.raw.MEIs_MEIs.txt",
        rank_file = lambda wildcards: (
            f"08_ped/{MEI_SAMPLE_TO_PEDIGREE[wildcards.sample]}.rank.txt"
        ),
        family_mei_raw = mei_family_raw_inputs
    output:
        mei_tsv = "09_MEI/{sample}.MEIs.tsv"
    params:
        p_s = '{sample}',
        phenotype = lambda wildcards:config["phenotype"][wildcards.sample],
        python3Path = python3Path,
        meiSplitPy = meiSplitPy,
        bcftools = bcftools,
        liftOver = liftOver
    shell:
        """
        {params.python3Path} {params.meiSplitPy} -i {input.vep_vcf} -s {params.p_s} -a {input.mei_raw} -r {input.rank_file} -p "{params.phenotype}" -o {output.mei_tsv} -cfg config.yaml --bcftools {params.bcftools} --liftover {params.liftOver}
        """
