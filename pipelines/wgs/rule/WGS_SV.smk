# container: config["containers"]["SV"]

from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container

CONTAINER_TOOLS=config.get("container_tools", {}).get("SV", {})
bgzip=CONTAINER_TOOLS["bgzip"]
tabix=CONTAINER_TOOLS["tabix"]
bcftoolsPath=CONTAINER_TOOLS["bcftools"]
bedtools=CONTAINER_TOOLS["bedtools"]
liftOver=CONTAINER_TOOLS["liftOver"]
VEP104=CONTAINER_TOOLS["vep"]
vepPerl=CONTAINER_TOOLS["perl"]
python3Path=CONTAINER_TOOLS["python3"]

SAMPLES=config["sample"]

vep_cache104=config['biosoft']['vepCache104']

SVsort=config["src"]["SVsort"]

reference=config["genome"]["fasta"]

VEPseverity=config['database']['VEPseverityPlus']
geneDisease=config["database"]["geneDisease"]
geneMIMnumber=config["database"]["gene_MIMnumber"]
hpoFile=config['database']['keyWords2GeneFile']


rule SVall:
    input:
        #expand("04_SV/a.calling/{sample}-smoove.genotyped.vcf.gz", sample=SAMPLES),
        expand("04_SV/{sample}.SV_CNV.bed", sample=SAMPLES),
        expand("04_SV/{sample}.SV.vcf", sample=SAMPLES),
        expand("04_SV/b.VEP/{sample}.vep.vcf", sample=SAMPLES),
        expand("04_SV/b.VEP/{sample}.vep.tsv", sample=SAMPLES),
        expand("04_SV/c.sort/{sample}.SV.sort.tsv", sample=SAMPLES),


rule splitCNV:
    container:
        runtime_container("SV_splitCNV")
    input:
        vcf="00_PreCalling/{sample}-smoove.genotyped.vcf.gz",
        index="00_PreCalling/{sample}-smoove.genotyped.vcf.gz.csi",
    output:
        cnv_bed="04_SV/{sample}.SV_CNV.bed",
        sv_vcf="04_SV/{sample}.SV.vcf",
    params:
        bcftools=bcftoolsPath,
    shell:
        r"""
        set -euo pipefail
        mkdir -p 04_SV
        {params.bcftools:q} view \
          -r chr1,chr2,chr3,chr4,chr5,chr6,chr7,chr8,chr9,chr10,chr11,chr12,chr13,chr14,chr15,chr16,chr17,chr18,chr19,chr20,chr21,chr22,chrX,chrY \
          {input.vcf:q} |
          {params.bcftools:q} view \
            -i 'ALT="<DUP>"||ALT="<DEL>"||ALT="<DUP:TANDEM>"' |
          {params.bcftools:q} query \
            -f '%CHROM\t%POS\t%INFO/END\t.\t%INFO/SR\t%INFO/SVTYPE\tLumpy\n' |
          awk -F '\t' '{{gsub("chr", "", $1); gsub("DUP", "+", $6); gsub("DEL", "-", $6); print $1"\t"$2"\t"$3"\t"$4"\t"$5"\t"$6"\t"$7}}' \
          > {output.cnv_bed:q}
        {params.bcftools:q} view \
          -e 'ALT="<DUP>"||ALT="<DEL>"||ALT="<DUP:TANDEM>"' \
          {input.vcf:q} > {output.sv_vcf:q}
        """

rule svVep:
    input:
        vcf=rules.splitCNV.output.sv_vcf,
        cache_info=(
            f"{vep_cache104}/homo_sapiens_refseq/104_GRCh38/info.txt"
        ),
        reference=reference,
        reference_fai=f"{reference}.fai",
    output:
        vep_vcf="04_SV/b.VEP/{sample}.vep.vcf",
    params:
        vep=VEP104,
        cache=vep_cache104,
    container:
        runtime_container("SV_svVep")
    shell:
        r"""
        set -euo pipefail
        mkdir -p 04_SV/b.VEP
        {params.vep:q}/vep \
          -i {input.vcf:q} \
          -o {output.vep_vcf:q} \
          --dir_cache {params.cache:q} \
          --fasta {input.reference:q} \
          --buffer_size 5000 \
          --offline \
          --cache \
          --symbol \
          --canonical \
          --total_length \
          --force \
          --force_overwrite \
          --no_stats \
          --vcf \
          --refseq \
          --use_given_ref \
          --assembly GRCh38 \
          --fork {threads} \
          --no_escape \
          --xref_refseq \
          --pick \
          --failed 1 \
          --gene_phenotype \
          --pubmed \
          --overlaps \
          --format vcf
        """

rule SVtsv:
    container:
        runtime_container("SV_SVtsv")
    input:
        vep_vcf=rules.svVep.output.vep_vcf,
    output:
        vep_tsv="04_SV/b.VEP/{sample}.vep.tsv",
    params:
        bcftools=BCFTOOLS,
    shell:
        r"""
        set -euo pipefail
        bgzip -f -c {input.vep_vcf:q} > {input.vep_vcf:q}.gz
        tabix -f -p vcf {input.vep_vcf:q}.gz
        header="$(grep '##INFO=<ID=CSQ' {input.vep_vcf:q} |
          sed -e 's/##INFO=<ID=CSQ,Number=.,Type=String,Description="Consequence annotations from Ensembl VEP. Format: //' \
              -e 's/|/\t/g' \
              -e 's/">//')"
        {params.bcftools:q} +split-vep {input.vep_vcf:q} \
          -f '%CHROM\t%POS\t%ID\t%REF\t%ALT\t%QUAL\t%FILTER\t%SVTYPE\t%SVLEN\t%END\t%STRANDS\t%CSQ\t%FORMAT\n' \
          -A tab -d > {output.vep_tsv:q}
        sed -i "1iCHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tSVTYPE\tSVLEN\tEND\tSTRANDS\t${{header}}\tFORMAT\tsample" \
          {output.vep_tsv:q}
        """

rule SVsort:
    input:
        vep_tsv=rules.SVtsv.output.vep_tsv,
        ped=lambda wildcards: (
            f"08_ped/{SAMPLE_TO_PEDIGREE[wildcards.sample]}.ped"
        ),
        script=SV_SORT,
        hpo=config["database"]["HPO_CHPO_gene"],
        omim=config["reference"]["hg38"]["gene_MIMnumber"],
        disease=config["reference"]["hg38"]["geneDisease"],
        severity=config["database"]["VEPseverityPlus"],
        chain=config["reference"]["hg38"]["hg38ToHg19Chain"],
        gnomad_sv=config["database"]["gnomadSvVcf"],
        pggsv=config["database"]["PGGSV"],
        hi_ts=config["database"]["HI_TS"],
        local_sv=config["database"]["localSVDB"],
        local_sv_sample=config["database"]["localSVsampleDB"],
        cytoband=config["database"]["cytobandBed"],
    output:
        anno_sv="04_SV/c.sort/{sample}.SV.anno.tsv",
        sort_tsv="04_SV/c.sort/{sample}.SV.sort.tsv",
    params:
        sample="{sample}",
        config_path="config.yaml",
        bedtools=bedtools,
        liftover=liftOver,
    container:
        runtime_container("SV_SVsort")
    shell:
        r"""
        set -euo pipefail
        mkdir -p 04_SV/c.sort
        phenotype="$(
          python3.7 - {params.sample:q} {params.config_path:q} <<'PY'
import sys
import yaml

sample = sys.argv[1]
with open(sys.argv[2], encoding="utf-8") as handle:
    data = yaml.safe_load(handle)
sys.stdout.write(data["phenotype"][sample])
PY
        )"
        python3.7 {input.script:q} \
          --input {input.vep_tsv:q} \
          --hpoterm "${{phenotype}}" \
          --HPOfile {input.hpo:q} \
          --omimFile {input.omim:q} \
          --diseaseFile {input.disease:q} \
          --VEPseverity {input.severity:q} \
          --outfile {output.anno_sv:q} \
          --sample {params.sample:q} \
          --ped {input.ped:q} \
          --cfg {params.config_path:q} \
          --bedtools {params.bedtools:q} \
          --liftover {params.liftover:q}
        head -n 1 {output.anno_sv:q} > {output.sort_tsv:q}
        tail -n +2 {output.anno_sv:q} |
          sort -t $'\t' -k5,5nr -k6,6nr >> {output.sort_tsv:q}
        """
