"""
@author:Rzhang
@license: Apache Licence
@file: ROH.smk
@time: 2021/10/22
@contact: zhiangrian@126.com
@site:
@software: PyCharm
@version 1.0
## V2.0
#### update@zhangran,20220914,vafplot rule 修改了输入输出文件和shell 命令
#### update@zhangran,20221009,ROH.smk中rule vcf2vaf中的rule vcfflt修改ROH vcf过滤的参数，修改为FILTER=="PASS" & FMT/NR[0:0]>=25 & QUAL>=60 & FMT/GQ>60 & GT!="mis"
#### update@zhangran,20221009,ROH.smk中去掉Platypus calling过程，使用SNV calling 并过滤后的vcf文件进行automap
#### update@zhangran,20221009,ROH.smk中去掉rule vcfflt ,rule vcf2vaf ,rule AutoMap
#### update@zhangran,20221009,ROH.smk中添加rule MIE 和rule MIE_ROH_plot ，进行MIE 识别和画图

## V3.0
#### update@zhangran,20230802更新参考基因组版本为hg38
#### update@zhangran,20230802,更新automap参考基因组版本为hg38
#### update@zhangran,20230802,更新rule MIE,slivar-functions.js ,原来是slivar-functions.V6.2.0.js，更新参考基因组为hg38版本
#### update@zhangran,20230802,修改 rule MIE_ROH_plot,新增--cytoband --UPD --mappability 三个参数，指定hg38版本文件
#### update@zhangran,20230810,更新rule MIE,增加{bcftoolsPath} view -e 'CHROM~"chrM"' {output.tmpVcf} -Ov -o {output.vcf},过滤掉vcf中的chrM上的位点
"""
SAMPLES=config["sample"]
wkdir=config["fastqDir"]
reference=config["reference"]['hg38']["genome"]
commonSNP=config["reference"]['hg38']["commonSNP"]
Platypus=config["bioSoft"]["Platypus"]
Formatgenotype=config["Self-built-Tools"]["CNV"]["Formatgenotype"]
WGScript=config["Self-built-Tools"]["SNV_MT"]["WGScript"]
bcftoolsPath=config["bioSoft"]["bcftoolsPath"]
bedtools=config["bioSoft"]["bedtools"]
vcf2vafTools=config["bioSoft"]["vcf2vaf"]
automap=config["bioSoft"]["automap"]
Rscript=config["bioSoft"]["Rscript"]
vafR=config["Self-built-Tools"]["CNV"]["vafR"]
cytoband=config["reference"]['hg38']["cytoband"]
imprint_gene_bed=config["reference"]['hg38']["imprint_gene_bed"]
Pathogenic_UPD_bed=config["reference"]['hg38']["Pathogenic_UPDBed"]
batchPath=config['fastqDir']
batchName=config['batch']
sampleInfoFile=config["sample_info"]
Pedigree=config["pedigree"]
trio=config["trio"]
peddyPath=config['bioSoft']['peddy']
python2Path=config['bioSoft']['python2']
python3Path=config['bioSoft']['python3']
bgzip=config["bioSoft"]["bgzip"]
tabix=config["bioSoft"]["tabix"]
slivarPath=config["bioSoft"]["slivar"]
MIEpl=config["Self-built-Tools"]["other"]["MIEpl"]
MIEPlotR=config["Self-built-Tools"]["other"]["mieRohPlotRcript"]
wgEncodeCrgMapability100mer=config["reference"]['hg38']["wgEncodeCrgMapability100mer"]
Pathogenic_UPD=config["reference"]['hg38']["Pathogenic_UPDBed"]
ROHannotationPy = config["Self-built-Tools"]["other"]['ROHannotationPy']

rule ROHall:
    input:
       expand("05_ROH/AutoMap/{sample}_ROH_annotataion.txt", sample=SAMPLES),
       expand("05_ROH/{sample}.HomRegions.tsv", sample=SAMPLES),
       expand("05_ROH/{sample}.vaf.genome.png", sample=SAMPLES),
       expand("10_MIE/{trioID}.trio.slivar.vcf",trioID=config["trio"]),
       expand("10_MIE/{trioID}.trio.MIE.png", trioID=config["trio"]),

rule ROHcalling:
    input:
        vcf = "01_SNV/{sample}.vcf"
    output:
        ROHtsvTmp=temp("05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv"),
        ROHtsv = "05_ROH/{sample}.HomRegions.tsv"
    params:
        samplename="{sample}",
        dp=15,
        minsize=1,
        dir=directory("05_ROH/AutoMap/")
    threads:1
    resources:
        qsub_vf=10000
    shell:
        """
        bash {automap} --vcf {input[0]} --genome hg38 --out {params.dir} --multivcf --chrX --DP {params.dp} --percaltlow 0.25 --percalthigh 0.75 --minsize {params.minsize}
        {python3Path}/python3 {ROHannotationPy} -i {output.ROHtsvTmp} -o {output.ROHtsv} --config config.yaml
        """
rule vafplot:
    input:
        vaf = "01_SNV/{sample}.vaf",
        roh = "05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv"
    output:
          genome="05_ROH/{sample}.vaf.genome.png",
          chrom = "05_ROH/{sample}.vaf.chrs.png",
          density = "05_ROH/{sample}.vaf.density.png"
    params:
        cytoband=cytoband,
        dir=directory("./"),
        parainput="{sample}.Platypus.flt.vaf"
    threads:1
    resources:
        qsub_vf=10000
    shell:
         """
        {Rscript} {vafR} --vaf {input.vaf} --roh {input.roh} --genome {output.genome} --chrs {output.chrom} --density {output.density} --UPD {Pathogenic_UPD}
         """
rule format:
    input:
        "05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv"
    output:
          bedfile="05_ROH/AutoMap/{sample}.bed",
    params:
          cytoband = cytoband
    threads:1
    resources:
        qsub_vf=10000
    shell:
        """
        awk -F '\t' '{{if (substr($1,1,2)!="##") print $0}}' {input} | {bedtools} intersect -a - -b {params.cytoband} -wao|sort -k1,1V -k8,8n|awk -F '\t' '{{t=$1"\t"$2"\t"$3"\t"$4"\t"$5"\t"$6;a[t]=a[t]","$10}}END{{for(i in a)print i"\t"substr(a[i],2)}}' >{output.bedfile}
        #awk -F '\t' '{{if (substr($1,1,2)!="##") print $0}}' {input} | {bedtools} intersect -a - -b {params.cytoband} -wao|sort -k1,1V -k8,8n|bedtools groupby -i stdin -g 1-6 -c 10 -o collapse>{output.bedfile}# same as command at line 24
        """
rule imprintRegionR:
    input:
        bedfile="05_ROH/AutoMap/{sample}.bed",
    output:
        result="05_ROH/AutoMap/{sample}_ROH_region.bed",
        final="05_ROH/AutoMap/{sample}_ROH_annotataion.txt"
    threads:1
    resources:
        qsub_vf=10000
    shell:
         """
         {python3Path}/python3 {WGScript}/imprintRegion.py {input.bedfile} {output.result}
         {bedtools} intersect -a {output.result} -b {imprint_gene_bed} -wao|awk -F '\t' '{{t=$1"\t"$2"\t"$3"\t"$4"\t"$5"\t"$6"\t"$7"\t"$8;a[t]=a[t]"|"$12;b[t]=b[t]"|"$13;c[t]=c[t]"|"$14;d[t]=d[t]"|"$15;f[t]=f[t]"||"$16}}END{{for(i in a)print i"\t"substr(a[i],2)"\t"substr(b[i],2)"\t"substr(c[i],2)"\t"substr(d[i],2)"\t"substr(f[i],3)}}' |awk -F '\t' '{{print $0"\t""http://172.17.61.169:10000/CNV/ROH?chr="substr($1,4)"&start="$2"&end="$3}}'|sed '1i\#Chr\tBegin\tEnd\tSize(Mb)\tNb_variants\tPercentage_homozygosity\tCytoband\tImprint_region\tImprint_genes\tImprint_genes ID\tstatus\texpression_allele\tpubmed\tCNVSeq_Web link' >{output.final}
         """
rule MIE:
    input:
        ped = "08_ped/{trioID}.ped",
        vcf = "02_split/{trioID}.split.trio.vcf"
    output:
        tmpVcf=temp("10_MIE/{trioID}.trio.slivar.tmp.vcf"),
        vcf = "10_MIE/{trioID}.trio.slivar.vcf"
    resources:
        qsub_vf=10000
    threads:1
    shell:
        """
        {slivarPath}/slivar expr --js {slivarPath}/js/slivar-functions.js -g {slivarPath}/gnomad.hg38.v2.zip --vcf {input.vcf} --ped {input.ped} -o {output.tmpVcf} --trio "iUPD_Pa:hq(kid, mom, dad) && (variant.CHROM != 'chrX' && ((mom.alts==2 && dad.alts==1 && kid.alts==0) || (mom.alts==0 && dad.alts==1 && kid.alts==2)) || variant.CHROM == 'chrX' && kid.sex == 'female' && ((mom.alts==2 && dad.alts==0 && kid.alts==0) || (mom.alts==0 && dad.alts==2 && kid.alts==2)))" --trio "iUPD_Ma:hq(kid, mom, dad) && (variant.CHROM != 'chrX' && ((mom.alts==1 && dad.alts==2 && kid.alts==0) || (mom.alts==1 && dad.alts==0 && kid.alts==2)) || variant.CHROM == 'chrX' && kid.sex == 'female' && ((mom.alts==1 && dad.alts==2 && kid.alts==0) || (mom.alts==1 && dad.alts==0 && kid.alts==2)))" --trio "UPD_Pa:hq(kid, mom, dad) && (hasSample(INFO,'iUPD_Pa', kid.id) || (variant.CHROM != 'chrX' && ((mom.alts==2 && dad.alts==0 && kid.alts==0) || (mom.alts==0 && dad.alts==2 && kid.alts==2))))" --trio "UPD_Ma:hq(kid, mom, dad) && (hasSample(INFO,'iUPD_Ma', kid.id) || (variant.CHROM != 'chrX' && ((mom.alts==2 && dad.alts==0 && kid.alts==2) || (mom.alts==0 && dad.alts==2 && kid.alts==0)) || variant.CHROM == 'chrX' && kid.sex == 'female' && ((mom.alts==2 && dad.alts==0 && kid.alts==2) || (mom.alts==0 && dad.alts==2 && kid.alts==0))))" --trio "Duo_Del:hq(kid, mom, dad) && (mom.alts==2 && dad.alts==2 && kid.alts<2)" --trio "DeNovo:hq(kid, mom, dad) && ((mom.alts==0 && dad.alts==0 && kid.alts>0) || (variant.CHROM == 'chrX' && kid.sex == 'male' && mom.alts==0 && dad.alts==2 && kid.alts==2))" --trio "MIE: hasSample(INFO,'DeNovo', kid.id) || hasSample(INFO,'iUPD_Pa', kid.id) || hasSample(INFO,'iUPD_Ma', kid.id) || hasSample(INFO,'UPD_Pa', kid.id) || hasSample(INFO,'UPD_Ma', kid.id) || hasSample(INFO,'Duo_Del', kid.id) || (hq(kid, mom, dad) && variant.CHROM == 'chrX' && kid.sex == 'male' && mom.alts==2 && dad.alts==0 && kid.alts==0)"
        {bcftoolsPath} view -e 'CHROM~"M"' {output.tmpVcf} -Ov -o {output.vcf}
        """
rule MIE_ROH_plot:
    input:
        mie = "10_MIE/{trioID}.trio.slivar.vcf",
        roh=expand("05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv", sample=SAMPLES)
    output:
        png = "10_MIE/{trioID}.trio.MIE.png"
    params:
        trio = '{trioID}'
    resources:
        qsub_vf=10000
    threads:1
    run:
        trioPairList=config["trioPair"]
        for i in trioPairList:
            trioID=i.split(":")[0]
            if trioID==params.trio:
                proband=i.split(":")[1]
        rohFile = '05_ROH/AutoMap/'+proband+'/' + proband + '.HomRegions.tsv'
        shell("{Rscript} {MIEPlotR} --mie {wkdir}/{input.mie} --roh {wkdir}/{rohFile} --outfile {wkdir}/{output.png} --cytoband {cytoband} --UPD {Pathogenic_UPD_bed} --mappability {wgEncodeCrgMapability100mer}")
