# container: config["containers"]["CNV"]


from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container


CONTAINER_TOOLS=config.get("container_tools", {}).get("CNV", {})
CONTAINER_RESOURCES=config.get("container_resources", {})
Rscript=CONTAINER_TOOLS["Rscript"]
bcftoolsPath=CONTAINER_TOOLS["bcftools"]
bedtools=CONTAINER_TOOLS["bedtools"]
python3=CONTAINER_TOOLS["python3"]
bgzip=CONTAINER_TOOLS["bgzip"]
tabix=CONTAINER_TOOLS["tabix"]
annotSV=CONTAINER_TOOLS["AnnotSV"]
liftOver=CONTAINER_TOOLS["liftOver"]

annotSVDataRoot=CONTAINER_RESOURCES["annotsv_data_root"]

SAMPLES=config["sample"]
batch=config["batch"]

GCcorrectTools=config["src"]["GCcorrect"]
CNVcallingR=config["src"]["CNV_R"]
cnvAnnotation=config["src"]["CNVannotationPy"]
LengthDistBatch=config["src"]["LengthDistBatch"]
LengthDist=config["src"]["LengthDist"]
correlation=config["src"]["correlation"]
chromCNannotationPy = config["src"]["chromCNannotationPy"]
ruleHelper=config['src']['ruleHelper']
CNV_NATIVE_PREPARE_TOOL=config["cnv_native"]["cnv_native_prepare"]
CNV_NATIVE_PUBLISH_TOOL=config["cnv_native"]["cnv_native_publish"]

reference=config["genome"]["fasta"]

cytoband=config["database"]["cytobandTxt"]
polymorphism=config["database"]["CNVPolymorphism"]
disease=config["database"]["disease"]
Pathogenic_UPD=config["database"]["pathogenicUPD"]
parbed=config['database']['parBed']
refCNVdata=config['database']['refCNVdata']
refSexData=config['database']['refSexData']
cnv_vafPlot=config["src"]['CNV_VAF_plot']
chromCNinfo=config["database"]["chromCNinfo"]
WGS_CNVbed_ExonIntron=config['database']['WGS_CNVbed_ExonIntron']

CNV_NATIVE_REFERENCE_DEPTH=config["cnv_native"]["reference_depth"]
CNV_NATIVE_REFERENCE_METADATA=config["cnv_native"]["reference_metadata"]
CNV_NATIVE_REFERENCE_SEX=config["cnv_native"]["reference_sex"]
CNV_NATIVE_CYTOBAND=config["cnv_native"]["cytoband"]
CNV_NATIVE_PAR=config["cnv_native"]["par"]
CNV_NATIVE_GENE_ANNOTATION=config["cnv_native"]["gene_annotation"]
CNV_SCRATCH_ROOT=config["runtime"]["scratch_root"]

_CNV_EXECUTOR=str(config.get("execution", {}).get("executor", "")).lower()
if _CNV_EXECUTOR in {"cce", "k8s", "cce_kubernetes"}:
    CNV_MANIFEST_ROOT=config["runtime"]["workspace_root"]
    for _cnv_path in (
        config["cloud"]["run_root"],
        config["cloud"]["resources_root"],
    ):
        if os.path.commonpath([CNV_MANIFEST_ROOT, _cnv_path]) != CNV_MANIFEST_ROOT:
            raise ValueError("CNV path must remain inside runtime.workspace_root")
else:
    # The native manifest stores paths relative to this root.  Local/SGE data
    # and immutable resources can live on separate approved mounts, so use the
    # filesystem root rather than imposing the single-PVC CCE layout.
    CNV_MANIFEST_ROOT="/"

# 将 config 中的 sample2pedigree 列表转换为字典
def build_sample2pedigree_dict():
    raw = config.get("sample2pedigree", [])
    mapping = {}
    for item in raw:
        if ':' in item:
            sample, pedigree = item.split(':', 1)
            mapping[sample.strip()] = pedigree.strip()
    return mapping
sample2pedigree = build_sample2pedigree_dict()

CNV_SAMPLE_STATE_ARGS=" ".join(
    "--sample-state {}".format(
        shlex.quote("{}=samples/{}/sample-result.json".format(sample, sample))
    )
    for sample in SAMPLES
)
CNV_PEDIGREE_ARGS=" ".join(
    "--pedigree {}".format(
        shlex.quote("{}={}".format(sample, sample2pedigree[sample]))
    )
    for sample in SAMPLES
)
CNV_SAMPLE_ARGS=" ".join(
    "--sample {}".format(shlex.quote(sample)) for sample in SAMPLES
)


rule CNVall:
    input:
        expand("03_CNV/{sample}_seg.tsv", sample=SAMPLES),
        expand("03_CNV/Annot/{sample}.CNV.bed", sample=SAMPLES),
        expand("03_CNV/Annot/{sample}.CNVseq.bed", sample=SAMPLES),
        expand("03_CNV/Annot/{sample}.CNV.tsv", sample=SAMPLES),
        expand("03_CNV/{sample}.iSizeFreq.png", sample=SAMPLES),
        expand("03_CNV/{sample}.CNV_VAF.png", sample=SAMPLES),
        expand("03_CNV/{sample}.CN.bedGraph.gz", sample=SAMPLES),
        expand("03_CNV/{sample}.segCN.bedGraph.gz", sample=SAMPLES),
        expand("03_CNV/{batch}.depth.r2.png",batch=config["batch"]),
        expand("03_CNV/{batch}.copynumber.txt",batch=config["batch"]),
        "03_CNV/All.chrom.CN.tsv",
        expand("03_CNV/{sample}.cnvRef.RData", sample=SAMPLES),
        expand("03_CNV/{sample}.ctrl.norm.RData", sample=SAMPLES),
        expand("03_CNV/{sample}.CN.bed", sample=SAMPLES),
        expand("03_CNV/{sample}_ploidy.tsv", sample=SAMPLES),
        expand("03_CNV/{sample}.log2r.mapd.tsv", sample=SAMPLES),
        expand("03_CNV/{sample}.ctrl.copynumber.txt", sample=SAMPLES),
        expand("03_CNV/{sample}.chrom.Anno.tsv", sample=SAMPLES)
        "03_CNV/native-publish.json"


rule fastqCount:
    container:
        runtime_container("CNV_fastqCount")
    input:
        jsonlist=expand("07_QC/{sample}.fastp.json", sample=config["sample"])
    output:
        "03_CNV/fastq_count.tsv",
    params:
        suffix="fastp.json",
        indir="./",
        helper=ruleHelper,
        python3=python3
    shell:
        "{params.python3} {params.helper} fastq-count --output {output[0]} {input.jsonlist}"

rule GCcorrect:
    container:
        runtime_container("CNV_GCcorrect")
    input:
        blocks=expand("00_PreCalling/{sample}.blk", sample=config["sample"]),
        fastq_count="03_CNV/fastq_count.tsv",
    output:
        corrected="03_CNV/GCcorrected.tsv",
        scatterplots=expand("03_CNV/{sample}_scatterplot.png", sample=SAMPLES),
    params:
        newout="03_CNV/GCcorrected.tsv",
        scatterplot_sources=" ".join(
            expand("{sample}_scatterplot.png", sample=SAMPLES)
        ),
        GCcorrectTools=GCcorrectTools
    shell:
        """
        {params.GCcorrectTools} -t {threads} -o {params.newout} {input.blocks}
        for plot in {params.scatterplot_sources}; do
          test -s "${{plot}}"
          mv "${{plot}}" "03_CNV/${{plot}}"
        done
        """

rule prepare:
    container:
        runtime_container("CNV_prepare")
    input:
        depth="03_CNV/GCcorrected.tsv",
        fastq_count="03_CNV/fastq_count.tsv",
        logs=expand("00_PreCalling/{sample}.log", sample=config["sample"]),
        reference_depth=CNV_NATIVE_REFERENCE_DEPTH,
        reference_metadata=CNV_NATIVE_REFERENCE_METADATA,
        reference_sex=CNV_NATIVE_REFERENCE_SEX,
        cytoband=CNV_NATIVE_CYTOBAND,
        par=CNV_NATIVE_PAR,
        gene_annotation=CNV_NATIVE_GENE_ANNOTATION,
    output:
        manifest="cnv-prepare-input.json",
        prepare_dir=directory("03_CNV/native/prepare"),
    params:
        tool=CNV_NATIVE_PREPARE_TOOL,
        logs_dir="00_PreCalling",
        manifest_root=CNV_MANIFEST_ROOT,
    shell:
        r"""
        set -euo pipefail
        mkdir -p 03_CNV/native
        manifest_root={params.manifest_root:q}
        to_manifest_relative() {{
          local raw="$1"
          local resolved=""
          if [[ "$raw" = /* ]]; then
            resolved=$(realpath -e -- "$raw")
          else
            resolved=$(realpath -e -- "$PWD/$raw")
          fi
          case "$resolved" in
            "$manifest_root"/*) ;;
            *) echo "CNV input escapes approved SFS root" >&2; return 2 ;;
          esac
          realpath --relative-to="$manifest_root" -- "$resolved"
        }}
        output_abs=$(realpath -m -- "$PWD/{output.manifest}")
        case "$output_abs" in
          "$manifest_root"/*) ;;
          *) echo "CNV output escapes approved SFS root" >&2; exit 2 ;;
        esac
        python3 {params.tool:q} \
          --root "$manifest_root" \
          --depth "$(to_manifest_relative {input.depth:q})" \
          --fastq-count "$(to_manifest_relative {input.fastq_count:q})" \
          --logs-dir "$(to_manifest_relative {params.logs_dir:q})" \
          --cytoband "$(to_manifest_relative {input.cytoband:q})" \
          --par "$(to_manifest_relative {input.par:q})" \
          --gene-annotation "$(to_manifest_relative {input.gene_annotation:q})" \
          --reference-depth "$(to_manifest_relative {input.reference_depth:q})" \
          --reference-metadata "$(to_manifest_relative {input.reference_metadata:q})" \
          --reference-sex "$(to_manifest_relative {input.reference_sex:q})" \
          --output "$(realpath --relative-to="$manifest_root" -- "$output_abs")"
        python3 -c 'from pathlib import Path; import sys; from cnvcompat.prepare import run_prepare; run_prepare(Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3]), repository_root=Path(sys.argv[4]))' \
          {output.manifest:q} \
          {threads} \
          {output.prepare_dir:q} \
          "$manifest_root"
        """


rule call_sample:
    container:
        runtime_container("CNV_call_sample")
    input:
        prepare_dir=rules.prepare.output.prepare_dir,
    output:
        sample_dir=directory("03_CNV/native/samples/{sample}"),
    params:
        scratch_root=CNV_SCRATCH_ROOT,
    shell:
        r"""
        set -euo pipefail
        mkdir -p 03_CNV/native/samples
        scratch_root={params.scratch_root:q}
        sample_tmp=$(mktemp -d "$scratch_root/cnv-call-{wildcards.sample}.XXXXXX")
        publish_tmp={output.sample_dir:q}.staging.$$
        trap 'rm -rf -- "$sample_tmp" "$publish_tmp"' EXIT
        test ! -e {output.sample_dir:q}
        test ! -e "$publish_tmp"
        python3 -m cnvcompat.call_sample \
          --prepare {input.prepare_dir:q}/prepare-manifest.json \
          --sample {wildcards.sample:q} \
          --threads {threads} \
          --outdir "$sample_tmp/results"
        test -d "$sample_tmp/results"
        cp -a "$sample_tmp/results" "$publish_tmp"
        mv "$publish_tmp" {output.sample_dir:q}
        """


rule formatCNV:
    container:
        runtime_container("CNV_formatCNV")
    input:
        sample_dir=rules.call_sample.output.sample_dir,
    output:
        "03_CNV/Annot/{sample}.CNVseq.bed",
    params:
        tool=CNV_NATIVE_PUBLISH_TOOL,
    shell:
        r"""
        python3 {params.tool:q} format-segments \
          --input {input.sample_dir:q}/{wildcards.sample}_seg.tsv \
          --output {output[0]:q} \
          --mos-ratio-min 0.3
        """


rule finalize:
    container:
        runtime_container("CNV_finalize")
    input:
        prepare_dir=rules.prepare.output.prepare_dir,
        sample_dirs=expand("03_CNV/native/samples/{sample}", sample=SAMPLES),
    output:
        sample_results="03_CNV/native/sample-results.json",
        finalize_dir=directory("03_CNV/native/finalize"),
    params:
        tool=CNV_NATIVE_PUBLISH_TOOL,
        sample_state_args=CNV_SAMPLE_STATE_ARGS,
        pedigree_args=CNV_PEDIGREE_ARGS,
    shell:
        r"""
        set -euo pipefail
        python3 {params.tool:q} build-results \
          --root 03_CNV/native \
          {params.sample_state_args} \
          {params.pedigree_args} \
          --output {output.sample_results:q}
        python3 -m cnvcompat.finalize \
          --prepare {input.prepare_dir:q}/prepare-manifest.json \
          --sample-results {output.sample_results:q} \
          --threads {threads} \
          --outdir {output.finalize_dir:q}
        """


rule publish:
    container:
        runtime_container("CNV_publish")
    input:
        prepare_dir=rules.prepare.output.prepare_dir,
        sample_dirs=expand("03_CNV/native/samples/{sample}", sample=SAMPLES),
        finalize_dir=rules.finalize.output.finalize_dir,
    output:
        mapping_qc="03_CNV/mappingQC.csv",
        correlation_matrix="03_CNV/corrQC.matridx.csv",
        correlation_qc="03_CNV/corrQC.tsv",
        segments=expand("03_CNV/{sample}_seg.tsv", sample=SAMPLES),
        normalized=expand("03_CNV/{sample}.normalize.bed", sample=SAMPLES),
        copy_number=expand("03_CNV/{sample}.CN.bed", sample=SAMPLES),
        ploidy=expand("03_CNV/{sample}_ploidy.tsv", sample=SAMPLES),
        mapd=expand("03_CNV/{sample}.log2r.mapd.tsv", sample=SAMPLES),
        mapd_summary=expand(
            "03_CNV/{sample}.log2r.mapd.summary.tsv", sample=SAMPLES
        ),
        controls=expand(
            "03_CNV/{sample}.ctrl.copynumber.txt", sample=SAMPLES
        ),
        all_chrom="03_CNV/All.chrom.CN.tsv",
        merge_bed="03_CNV/merge.bed",
        log2r="03_CNV/All.join.log2r.bed.gz",
        log2r_tbi="03_CNV/All.join.log2r.bed.gz.tbi",
        log2r_chr="03_CNV/All.join.log2r.with_chr.bed.gz",
        log2r_chr_tbi="03_CNV/All.join.log2r.with_chr.bed.gz.tbi",
        state="03_CNV/native-publish.json",
    params:
        tool=CNV_NATIVE_PUBLISH_TOOL,
        sample_args=CNV_SAMPLE_ARGS,
    shell:
        r"""
        python3 {params.tool:q} publish \
          --prepare-dir {input.prepare_dir:q} \
          --samples-root 03_CNV/native/samples \
          --finalize-dir {input.finalize_dir:q} \
          {params.sample_args} \
          --output-root 03_CNV
        """

rule correlation:
    container:
        runtime_container("CNV_correlation")
    input:
        corr="03_CNV/corrQC.matridx.csv"
    output:
        png=expand("03_CNV/{batch}.depth.r2.png",batch=config["batch"])
    params:
        python3=python3,
        correlation=correlation,
    shell:
        """
        {params.python3} {params.correlation} -i {input.corr} -o {output.png}
        """

rule annotate_chrom_CN:
    container:
        runtime_container("CNV_annotate_chrom_CN")
    input:
        cn=expand("03_CNV/{sample}_ploidy.tsv", sample=SAMPLES),
        pedfile = "08_ped/"+batch+".ped",
        sampleRank="08_ped/"+batch+".rank.txt"
    output:
        anno = "03_CNV/{sample}.chrom.Anno.tsv"
    params:
        python3=python3,
        chromCNannotationPy=chromCNannotationPy,
        pedigreeID = lambda wildcards: sample2pedigree[wildcards.sample],
        chromCNinfo = chromCNinfo,
    shell:
        '{params.python3} {params.chromCNannotationPy} -i 03_CNV/{wildcards.sample}_ploidy.tsv -s {wildcards.sample} -p 08_ped/{params.pedigreeID}.ped --info {params.chromCNinfo} -o {output.anno}'

rule CNV_VAF_plot:
    container:
        runtime_container("CNV_CNV_VAF_plot")
    input:
        cn = "03_CNV/{sample}.normalize.bed",
        vaf = "01_SNV/{sample}.vaf",
        roh = "05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv"
    output:
        genomePng = "03_CNV/{sample}.CNV.genome.png",
        cnvVafPng = "03_CNV/{sample}.CNV_VAF.png",
        cn_bedGraph = "03_CNV/{sample}.CN.bedGraph.gz",
        cnseg_bedGraph = "03_CNV/{sample}.segCN.bedGraph.gz"
    params:
        sampleN="{sample}",
        Rscript=Rscript,
        cnv_vafPlot=cnv_vafPlot,
        reference=reference,
        cytoband=cytoband,
        polymorphism=polymorphism,
        disease=disease,
        Pathogenic_UPD=Pathogenic_UPD,
        tabix=tabix,
        bgzip=bgzip
    shell:
         """
         {params.Rscript} {params.cnv_vafPlot} --reference-fai {params.reference}.fai --out-chrom 03_CNV/{params.sampleN}_chrom%s.png --out-genome  {output.genomePng} --input-bed {input.cn} --vaf-bed {input.vaf} --roh {input.roh} --samples {params.sampleN} --cytoband {params.cytoband} --Polymorphism {params.polymorphism} --Disease {params.disease} --UPD {params.Pathogenic_UPD}
         awk -F'\\t' '{{OFS="\\t"; print $1, $2, $3, $6}}' {input.cn} | {params.bgzip} -c -@ {threads} > {output.cn_bedGraph}
         {params.tabix} -fp bed {output.cn_bedGraph}
         awk -F'\\t' '{{OFS="\\t"; print $1, $2, $3, $7}}' {input.cn} | {params.bgzip} -c -@ {threads} > {output.cnseg_bedGraph}
         {params.tabix} -fp bed {output.cnseg_bedGraph}
         """

rule getCopyNumber:
    container:
        runtime_container("CNV_getCopyNumber")
    input:
        bed = "03_CNV/{sample}.CN.bed"
    output:
        CN = temp("03_CNV/{sample}.copynumber.txt")
    params:
        helper=ruleHelper,
        sample="{sample}",
        python3=python3
    shell:
        "{params.python3} {params.helper} copy-number --sample {params.sample} --input {input.bed} --output {output.CN}"

rule pasteCopyNumber:
    container:
        runtime_container("CNV_pasteCopyNumber")
    input:
        expand("03_CNV/{sample}.copynumber.txt", sample=SAMPLES)
    output:
        expand("03_CNV/{batch}.copynumber.txt",batch=config["batch"])
    params:
        bed=WGS_CNVbed_ExonIntron,
        inputs=" ".join(expand("03_CNV/{sample}.copynumber.txt", sample=SAMPLES))
    shell:
        "paste {params.bed} {params.inputs} > {output}"

rule mergeCNV:
    container:
        runtime_container("CNV_mergeCNV")
    input:
        CNVbed = "03_CNV/Annot/{sample}.CNVseq.bed",
        SVbed="04_SV/{sample}.SV_CNV.bed",
    output:
        mergeCNVtmp = temp("03_CNV/Annot/{sample}.CNV.tmp.bed"),
        mergeCNV = "03_CNV/Annot/{sample}.CNV.bed",
    shell:
         """
         awk '{{print $0"\tCNVseq"}}' {input.CNVbed} > {output.mergeCNVtmp}
         cat {output.mergeCNVtmp} {input.SVbed} |sort -k1,1V -k2,2n -k3,3n >{output.mergeCNV}
         """

rule CNVannotation:
    container:
        runtime_container("CNV_CNVannotation")
    input:
        CNVbed = "03_CNV/Annot/{sample}.CNV.bed",
        pedfile = "08_ped/"+batch+".ped",
        sampleRank="08_ped/"+batch+".rank.txt"
    output:
        CNV = "03_CNV/Annot/{sample}.CNV.tsv",
    params:
        cnvAnnotation=cnvAnnotation,
        python3=python3,
        helper=ruleHelper,
        sample="{sample}",
        phenotype=lambda wildcards: config["phenotype"].get(wildcards.sample, "") or "null",
        pedigree=lambda wildcards: "08_ped/"+sample2pedigree[wildcards.sample]+".ped",
        bedtools=bedtools,
        bcftoolsPath=bcftoolsPath,
        annotSV=annotSV,
        liftOver=liftOver,
        annotSVDataRoot=annotSVDataRoot
    # CCE: keep AnnotSV databases on SFS and pass the directory explicitly to the worker helper.
    shell:
        "ANNOTSV_DATA_ROOT={params.annotSVDataRoot:q} {params.python3} {params.helper} cnv-annotation --sample {params.sample} --phenotype {params.phenotype:q} --pedigree {params.pedigree} --input {input.CNVbed} --output {output.CNV} --annotation-script {params.cnvAnnotation} --config config.yaml --bedtools {params.bedtools} --bcftools {params.bcftoolsPath} --annotsv {params.annotSV} --annotsv-annotations-dir {params.annotSVDataRoot:q} --liftover {params.liftOver} --threads {threads}"

rule insertplot:
    container:
        runtime_container("CNV_insertplot")
    input:
        lambda wc: f"00_PreCalling/{wc.sample}.iSizeFreq.tsv"
    output:
        "03_CNV/{sample}.iSizeFreq.png",
    params:
        outsuffix="cfDNA_size",
        xmax=500,
        samplesuffix="{sample}.iSizeFreq",
        newinput="{sample}.iSizeFreq.tsv",
        Rscript=Rscript,
        LengthDistBatch=LengthDistBatch,
        LengthDist=LengthDist
    shell:
         """
         {params.Rscript} {params.LengthDistBatch} 00_PreCalling 03_CNV/{params.outsuffix} {params.xmax}
         {params.Rscript} {params.LengthDist} {input[0]} 03_CNV/{params.samplesuffix} 500
         """