# container: config["containers"]["ROH"]

from script.runtime_overlay import RuntimeContract
_RUNTIME_CONTRACT = RuntimeContract(config)
runtime_container = _RUNTIME_CONTRACT.container

CONTAINER_TOOLS=config.get("container_tools", {}).get("ROH", {})
CONTAINER_RESOURCES=config.get("container_resources", {})
bcftoolsPath=CONTAINER_TOOLS["bcftools"]
bedtools=CONTAINER_TOOLS["bedtools"]
automap=CONTAINER_TOOLS["automap"]
Rscript=CONTAINER_TOOLS["Rscript"]
python3Path=CONTAINER_TOOLS["python3"]
slivarPath=CONTAINER_TOOLS["slivar"]
liftOver=CONTAINER_TOOLS["liftOver"]
slivarJs=CONTAINER_RESOURCES.get("slivar_js", "/opt/wgs/resources/slivar/slivar-functions.V6.3.0.js")
slivarGnomad=CONTAINER_RESOURCES.get("slivar_gnomad", "/opt/wgs/resources/slivar/gnomad.hg38.v2.zip")

SAMPLES=config["sample"]

imprintRegion=config["src"]["imprintRegion"]

vafR=config["src"]["vafPlotRscript"]
MIEPlotR=config["src"]["mieRohPlotRcript"]
ROHannotationPy = config["src"]['ROHannotationPy']

cytoband=config["database"]["cytobandTxt"]
imprint_gene_bed=config["database"]["imprint_gene_bed"]
Pathogenic_UPD_bed=config["database"]["pathogenicUPD"]
wgEncodeCrgMapability100mer=config["database"]["mappability100mer"]
Pathogenic_UPD=config["database"]["pathogenicUPD"]

trio2proband = dict(item.split(":", 1) for item in config.get("trioPair", []))


rule ROHall:
    input:
       expand("05_ROH/AutoMap/{sample}_ROH_annotataion.txt", sample=SAMPLES),
       expand("05_ROH/{sample}.HomRegions.tsv", sample=SAMPLES),
       expand("05_ROH/{sample}.vaf.genome.png", sample=SAMPLES),
       expand("10_MIE/{trioID}.trio.slivar.vcf",trioID=config["trio"]),
       expand("10_MIE/{trioID}.trio.MIE.png", trioID=config["trio"]),

rule ROHcalling:
    container:
        runtime_container("ROH_ROHcalling")
    input:
        vcf = "01_SNV/{sample}.vcf"
    output:
        # CNVannotation consumes this file in the later CNV phase. Keep it
        # persistent so splitting ROH and CNV does not rerun full-genome AutoMap.
        ROHtsvTmp="05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv",
        ROHtsv = "05_ROH/{sample}.HomRegions.tsv"
    params:
        samplename="{sample}",
        dp=15,
        minsize=1,
        dir=directory("05_ROH/AutoMap/"),
        automap=automap,
        ROHannotationPy = ROHannotationPy,
        python3Path = python3Path,
        bedtools = bedtools,
        liftOver = liftOver
    shell:
        """
        AUTOMAP_REPEATS_HG38={config[container_resources][automap_repeats_hg38]} {params.automap} --vcf {input[0]} --genome hg38 --out {params.dir} --multivcf --chrX --DP {params.dp} --percaltlow 0.25 --percalthigh 0.75 --minsize {params.minsize}
        {params.python3Path} {params.ROHannotationPy} -i {output.ROHtsvTmp} -o {output.ROHtsv} --config config.yaml --bedtools {params.bedtools} --liftover {params.liftOver}
        """

rule vafplot:
    container:
        runtime_container("ROH_vafplot")
    input:
        vaf = "01_SNV/{sample}.vaf",
        roh = "05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv"
    output:
          genome="05_ROH/{sample}.vaf.genome.png",
          chrom = "05_ROH/{sample}.vaf.chrs.png",
          density = "05_ROH/{sample}.vaf.density.png"
    params:
        cytoband=cytoband,
        parainput="{sample}.Platypus.flt.vaf",
        Rscript=Rscript,
        vafR=vafR,
        Pathogenic_UPD=Pathogenic_UPD
    shell:
         """
        {params.Rscript} {params.vafR} --vaf {input.vaf} --roh {input.roh} --genome {output.genome} --chrs {output.chrom} --density {output.density} --UPD {params.Pathogenic_UPD} --cytoband {params.cytoband}
         """

rule format:
    container:
        runtime_container("ROH_format")
    input:
        "05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv"
    output:
          bedfile="05_ROH/AutoMap/{sample}.bed",
    params:
          cytoband=cytoband,
          bedtools=bedtools
    shell:
        """
        awk -F '\t' '{{if (substr($1,1,2)!="##") print $0}}' {input} | {params.bedtools} intersect -a - -b {params.cytoband} -wao|sort -k1,1V -k8,8n|awk -F '\t' '{{t=$1"\t"$2"\t"$3"\t"$4"\t"$5"\t"$6;a[t]=a[t]","$10}}END{{for(i in a)print i"\t"substr(a[i],2)}}' >{output.bedfile}
        """

rule imprintRegionR:
    container:
        runtime_container("ROH_imprintRegionR")
    input:
        bedfile="05_ROH/AutoMap/{sample}.bed",
    output:
        result="05_ROH/AutoMap/{sample}_ROH_region.bed",
        final="05_ROH/AutoMap/{sample}_ROH_annotataion.txt"
    params:
        python3Path=python3Path,
        bedtools=bedtools,
        imprint_gene_bed=imprint_gene_bed
    shell:
         """
         {params.python3Path} {params.imprintRegion} {input.bedfile} {output.result}
         {params.bedtools} intersect -a {output.result} -b {params.imprint_gene_bed} -wao|awk -F '\t' '{{t=$1"\t"$2"\t"$3"\t"$4"\t"$5"\t"$6"\t"$7"\t"$8;a[t]=a[t]"|"$12;b[t]=b[t]"|"$13;c[t]=c[t]"|"$14;d[t]=d[t]"|"$15;f[t]=f[t]"||"$16}}END{{for(i in a)print i"\t"substr(a[i],2)"\t"substr(b[i],2)"\t"substr(c[i],2)"\t"substr(d[i],2)"\t"substr(f[i],3)}}' |awk -F '\t' '{{print $0"\t""http://172.17.61.169:10000/CNV/ROH?chr="substr($1,4)"&start="$2"&end="$3}}'|sed '1i\#Chr\tBegin\tEnd\tSize(Mb)\tNb_variants\tPercentage_homozygosity\tCytoband\tImprint_region\tImprint_genes\tImprint_genes ID\tstatus\texpression_allele\tpubmed\tCNVSeq_Web link' >{output.final}
         """

rule MIE:
    container:
        runtime_container("ROH_MIE")
    input:
        ped = "08_ped/{trioID}.ped",
        vcf = "02_split/{trioID}.split.trio.vcf"
    output:
        tmpVcf=temp("10_MIE/{trioID}.trio.slivar.tmp.vcf"),
        vcf = "10_MIE/{trioID}.trio.slivar.vcf"
    params:
        slivarJs=slivarJs,
        slivarGnomad=slivarGnomad,
        bcftoolsPath=bcftoolsPath
    shell:
        """
        slivar expr --js {params.slivarJs} -g {params.slivarGnomad} --vcf {input.vcf} --ped {input.ped} -o {output.tmpVcf} --trio "iUPD_Pa:hq(kid, mom, dad) && (variant.CHROM != 'chrX' && ((mom.alts==2 && dad.alts==1 && kid.alts==0) || (mom.alts==0 && dad.alts==1 && kid.alts==2)) || variant.CHROM == 'chrX' && kid.sex == 'female' && ((mom.alts==2 && dad.alts==0 && kid.alts==0) || (mom.alts==0 && dad.alts==2 && kid.alts==2)))" --trio "iUPD_Ma:hq(kid, mom, dad) && (variant.CHROM != 'chrX' && ((mom.alts==1 && dad.alts==2 && kid.alts==0) || (mom.alts==1 && dad.alts==0 && kid.alts==2)) || variant.CHROM == 'chrX' && kid.sex == 'female' && ((mom.alts==1 && dad.alts==2 && kid.alts==0) || (mom.alts==1 && dad.alts==0 && kid.alts==2)))" --trio "UPD_Pa:hq(kid, mom, dad) && (hasSample(INFO,'iUPD_Pa', kid.id) || (variant.CHROM != 'chrX' && ((mom.alts==2 && dad.alts==0 && kid.alts==0) || (mom.alts==0 && dad.alts==2 && kid.alts==2))))" --trio "UPD_Ma:hq(kid, mom, dad) && (hasSample(INFO,'iUPD_Ma', kid.id) || (variant.CHROM != 'chrX' && ((mom.alts==2 && dad.alts==0 && kid.alts==2) || (mom.alts==0 && dad.alts==2 && kid.alts==0)) || variant.CHROM == 'chrX' && kid.sex == 'female' && ((mom.alts==2 && dad.alts==0 && kid.alts==2) || (mom.alts==0 && dad.alts==2 && kid.alts==0))))" --trio "Duo_Del:hq(kid, mom, dad) && (mom.alts==2 && dad.alts==2 && kid.alts<2)" --trio "DeNovo:hq(kid, mom, dad) && ((mom.alts==0 && dad.alts==0 && kid.alts>0) || (variant.CHROM == 'chrX' && kid.sex == 'male' && mom.alts==0 && dad.alts==2 && kid.alts==2))" --trio "MIE: hasSample(INFO,'DeNovo', kid.id) || hasSample(INFO,'iUPD_Pa', kid.id) || hasSample(INFO,'iUPD_Ma', kid.id) || hasSample(INFO,'UPD_Pa', kid.id) || hasSample(INFO,'UPD_Ma', kid.id) || hasSample(INFO,'Duo_Del', kid.id) || (hq(kid, mom, dad) && variant.CHROM == 'chrX' && kid.sex == 'male' && mom.alts==2 && dad.alts==0 && kid.alts==0)"
        {params.bcftoolsPath} view -e 'CHROM~"M"' {output.tmpVcf} -Ov -o {output.vcf}
        """

rule MIE_ROH_plot:
    container:
        runtime_container("ROH_MIE_ROH_plot")
    input:
        mie = "10_MIE/{trioID}.trio.slivar.vcf",
        roh=expand("05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv", sample=SAMPLES)
    output:
        png = "10_MIE/{trioID}.trio.MIE.png"
    params:
        trio = '{trioID}',
        roh=lambda wildcards: "05_ROH/AutoMap/{0}/{0}.HomRegions.tsv".format(trio2proband[wildcards.trioID]),
        Rscript=Rscript,
        MIEPlotR=MIEPlotR,
        cytoband=cytoband,
        Pathogenic_UPD_bed=Pathogenic_UPD_bed,
        wgEncodeCrgMapability100mer=wgEncodeCrgMapability100mer
    shell:
        "{params.Rscript} {params.MIEPlotR} --mie {input.mie} --roh {params.roh} --outfile {output.png} --cytoband {params.cytoband} --UPD {params.Pathogenic_UPD_bed} --mappability {params.wgEncodeCrgMapability100mer}"

