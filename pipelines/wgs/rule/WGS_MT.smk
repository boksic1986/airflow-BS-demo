container: config["containers"]["MT"]

from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container

CONTAINER_TOOLS=config.get("container_tools", {}).get("MT", {})
PERFORMANCE_RULE_THREADS=config.get("performance", {}).get("rule_threads", {})
mityPath=CONTAINER_TOOLS["mity"]
bcftoolsPath=CONTAINER_TOOLS["bcftools"]
hmtnotepath=CONTAINER_TOOLS["hmtnote"]
python3Path=CONTAINER_TOOLS["python3"]
bgzip=CONTAINER_TOOLS["bgzip"]
tabix=CONTAINER_TOOLS["tabix"]
perl=CONTAINER_TOOLS["perl"]

SAMPLES=config["sample"]
batch=config["batch"]

MTannotationPy=config["src"]["mtAnnotationPy"]
mtCombinePl=config["src"]["mtCombinePl"]

reference=config["genome"]["fasta"]

micomapCfm=config["database"]["micomapCfm"]
MTclinvar=config["database"]["MTclinvar"]
mitomapDisease=config["database"]["mitomapDisease"]
mitomapSNP=config["database"]["mitomapSNP"]
MitImpact=config["database"]["MitImpact"]
mitotip=config["database"]["mitotip"]
MTlocal=config["database"]["MTlocal"]
MTgnomad=config["database"]["MTgnomad"]
MTlocalFreq=config["database"]["MTlocalFreq"]


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
    container:
        runtime_container("MT_mityCallflt")
    input:
        gzvcf="00_PreCalling/{sample}.mity.vcf.gz",
    output:
        fltvcf="11_MT/{sample}.mity.flt.vcf.gz"
    params:
        prefix="{sample}",
        bcftoolsPath=bcftoolsPath,
        tabix=tabix
    shell:
        """
        {params.bcftoolsPath} view -e 'FMT/VAF<0.04' {input.gzvcf}  -Oz -o {output.fltvcf}
        {params.tabix} -p vcf {output.fltvcf}
        """

rule NorVcf:
    container:
        runtime_container("MT_NorVcf")
    input:
        fltvcf="11_MT/{sample}.mity.flt.vcf.gz",
    output:
        vtvcf="11_MT/{sample}.mity.vt.vcf"
    params:
        genome = reference,
        bcftoolsPath=bcftoolsPath,
        bgzip=bgzip,
        tabix=tabix
    shell:
        """
        {params.bcftoolsPath} norm -c w -m -any -f {params.genome} {input.fltvcf} -Ov -o {output.vtvcf} --threads {threads}
        {params.bgzip} -c {output.vtvcf} > {output.vtvcf}.gz && {params.tabix} -p vcf {output.vtvcf}.gz
        """

rule mergeMTQC:
    container:
        runtime_container("MT_mergeMTQC")
    input:
        expand("07_QC/MT/{sample}.MT.QC.txt", sample=SAMPLES)
    output:
        batchQC="07_QC/"+batch+".MTQC.txt",
    params:
        allQCfiles ="  ".join(expand("07_QC/MT/{sample}.MT.QC.txt", sample=SAMPLES)),
    shell:
         """
         cat {params.allQCfiles}|awk '!x[$0]++' > {output.batchQC}
         """

rule mityreport:
    container:
        runtime_container("MT_mityreport")
    input:
        vtvcf="11_MT/{sample}.mity.vt.vcf",
    output:
        mityReportOut="11_MT/{sample}.annotated_variants.csv",
        mityReadme = temp("11_MT/{sample}.annotated_variants.xlsx")
    params:
        mitypath=mityPath,
        prefix="{sample}",
        dir = "11_MT",
    shell:
        "{params.mitypath} report --prefix {params.prefix} --out-folder-path {params.dir} {input.vtvcf}.gz"

rule mtAnnot:
    container:
        runtime_container("MT_mtAnnot")
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
    params:
        MTclinvar=MTclinvar,
        mitomapDisease=mitomapDisease,
        mitomapSNP=mitomapSNP,
        MitImpact=MitImpact,
        mitotip=mitotip,
        MTlocal=MTlocal,
        MTgnomad=MTgnomad,
        MTlocalFreq=MTlocalFreq,
        hmtnotepath=hmtnotepath,
        bcftoolsPath=bcftoolsPath
    shell:
        """
        {params.bcftoolsPath} annotate -c 'INFO/CLNREVSTAT,INFO/CLNSIG,INFO/CLNDN,INFO/ClinvarID' -a {params.MTclinvar} {input.vtvcf}.gz -Oz -o {output.clinvarVcf} && {params.bcftoolsPath} index {output.clinvarVcf}
        {params.bcftoolsPath} annotate -c 'INFO/PubmedIDs,INFO/aachange,INFO/Disease,INFO/DiseaseStatus,INFO/HGFL' -a {params.mitomapDisease} {output.clinvarVcf} -Oz -o {output.mitomapVcf} && {params.bcftoolsPath} index {output.mitomapVcf}
        {params.bcftoolsPath} annotate -c 'INFO/AF' -a {params.mitomapSNP} {output.mitomapVcf} -Oz -o {output.snpVcf} && {params.bcftoolsPath} index {output.snpVcf}
        {params.bcftoolsPath} annotate -c 'INFO/APOGEE_score,INFO/APOGEE' -a {params.MitImpact} {output.snpVcf} -Oz -o {output.mitimpactVcf} && {params.bcftoolsPath} index {output.mitimpactVcf}
        {params.bcftoolsPath} annotate -c 'INFO/MitotipScore,INFO/MitotipQuartile' -a {params.mitotip} {output.mitimpactVcf} -Oz -o {output.mitotipVcf} && {params.bcftoolsPath} index {output.mitotipVcf}
        {params.bcftoolsPath} annotate -c 'INFO/LocalSig,INFO/EvidenceList,INFO/Evidence' -a {params.MTlocal} {output.mitotipVcf} -Oz -o {output.localVcf} && {params.bcftoolsPath} index {output.localVcf}
        {params.bcftoolsPath} annotate -c 'INFO/AN,INFO/AC_het,INFO/AC_hom' -a {params.MTgnomad} {output.localVcf} -Oz -o {output.gnomadVcf} && {params.bcftoolsPath} index {output.gnomadVcf}
        {params.bcftoolsPath} annotate -c 'INFO/FreqHet,INFO/FreqHom' -a {params.MTlocalFreq} {output.gnomadVcf} -Ov -o {output.localFreqVcf}
        {params.hmtnotepath} annotate {output.localFreqVcf} {output.hmtnoteVcf} --offline --csv
        """

rule mtFlt:
    container:
        runtime_container("MT_mtFlt")
    input:
        hmtnoteCsv="11_MT/{sample}.hmnote.csv",
        mityReportOut="11_MT/{sample}.annotated_variants.csv"
    output:
        mtFlt="11_MT/{sample}.mity.flt.txt"
    params:
        python3Path=python3Path,
        MTannotationPy=MTannotationPy,
        micomapCfm=micomapCfm
    shell:
        "{params.python3Path} {params.MTannotationPy} --cfrmFile {params.micomapCfm} --hmtnoteCsv {input.hmtnoteCsv} --mityCsv {input.mityReportOut} --output {output.mtFlt}"

rule mtCombine:
    container:
        runtime_container("MT_mtCombine")
    input:
        mt = expand("11_MT/{sample}.mity.flt.txt", sample=config["sample"]),
        rank = expand("08_ped/{batch}.rank.txt", batch=config["batch"])
    output:
        expand("11_MT/{mtPedigreeID}.mity.flt.txt", mtPedigreeID=config["mtPedigreeList"])
    params:
        mtCombinePl=mtCombinePl,
        perl=perl
    shell:
        "{params.perl} {params.mtCombinePl} -rank {input.rank}"
