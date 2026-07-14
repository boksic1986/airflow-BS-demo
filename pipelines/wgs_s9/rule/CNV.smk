"""
@author:Rzhang
@license: Apache Licence
@file: CNV.smk
@time: 2021/10/22
@contact: zhiangrian@126.com
@site:
@software: PyCharm
@version 1.0
CNV bed file annotation by WES CNV annotation pipeline
## V2.0
#### update@zhangran,20221010,修改rule CNVannotation，自动读取config文件中的样本对应家系信息
## V2.1
#### update@zhangran,20221124,rule bam2blockUniq，-b 参数从12 修改到2
#### update@zhangran,20221207, 修改rule CNVcalling 的参数，把--sexCutoff 0.0007 --Disease /bi/8.xuxiong/work/CNVseq/Decipher.bed 去掉
#### update@zhangran,20221212,rule CNVannotation，中phenotype 增加双引号，防止特殊字符（“（”）导致的报错
## V3.0
#### update@zhangran,20230802,更新参考基因组版本为hg38
#### update@zhangran,20230802,更新bam文件为deduped.cram
#### update@zhangran,20230802,修改rule CNVcalling，新增--Disease执行hg38版本的文件
#### update@zhangran,20230802,修改rule CNVannotation，新增--Disease执行hg38版本的文件
#### update@zhangran,20230817,新增rule CNV_VAF_plot
#### update@zhangran,20230824,新增CNVcalling 两个参数，--HLAstart 28510120 --HLAend 33480577
#V3.1
#### update@zhangran,20230824,rule formatCNV 命令由awk更新为XX提供的R
#V3.1.1
#### update@zhangran,20231205,新增rule mergeCNV,修改rule monoExonCNVformat，为单外显子CNV结果添加一列calling method
#### update@zhangran,20231215,CNV的注释脚本改为5.CNV_annotation.py，新增HI、TS、pLI注释
"""

from script.s9_helpers import read_fastp_json
import os
batch=config["batch"]
wkdir=config["fastqDir"]
SAMPLES=config["sample"]
sampleInfoFile=config["sample_info"]
GCcorrectTools=config["Self-built-Tools"]["CNV"]["GCcorrect"]
Rscript=config["bioSoft"]["Rscript"]
bcftoolsPath=config["bioSoft"]["bcftoolsPath"]
bedtools=config["bioSoft"]["bedtools"]
CNVcallingR=config["Self-built-Tools"]["CNV"]["CNV_R"]
cytoband=config["reference"]['hg38']["cytoband"]
polymorphism=config["reference"]['hg38']["polymorphism"]
disease=config["reference"]['hg38']["disease"]
Pathogenic_UPD=config["reference"]['hg38']["Pathogenic_UPDBed"]
cnvAnnotation=config["Self-built-Tools"]["CNV"]["cnvAnnotation"]
LengthDistBatch=config["Self-built-Tools"]["CNV"]["LengthDistBatch"]
LengthDist=config["Self-built-Tools"]["CNV"]["LengthDist"]
WGScript=config["Self-built-Tools"]["SNV_MT"]["WGScript"]
bam2blockUniqTools=config["Self-built-Tools"]["CNV"]["bam2block_uniq"]
BIN2POS=config["reference"]['hg38']["BIN2POS"]
wgEncodeCrgMapability=config["reference"]['hg38']['wgEncodeCrgMapability']
python3=config['bioSoft']['python3']
bgzip=config["bioSoft"]["bgzip"]
tabix=config["bioSoft"]["tabix"]
reference=config["reference"]['hg38']["genome"]
annotSV=config["bioSoft"]["annotSV"]
parbed=config['database']['PARbed']
AnnotationPath=os.path.dirname(polymorphism)
hpoFile=config['database']['HPO_CHPO_gene']
monoExoniCNV=config["Self-built-Tools"]["CNV"]["monoExoniCNV"]
exonIntron=config["reference"]['hg38']["exonIntron"]
geninfo=config['database']['geneInfo']
refCNVdata=config['database']['refCNVdata']
refSexData=config['database']['refSexData']
#monoExoniCNVAnnot=config["Self-built-Tools"]["CNV"]["monoExoniCNVAnnot"]
cnv_vafPlot=config["Self-built-Tools"]["CNV"]['CNV_VAF_plot']
formatCNVDirect=os.path.join(workflow.basedir, "script", "formatCNV_direct.R")
rule CNVall:
    input:
       # expand("03_CNV/{sample}.blk", sample=SAMPLES),
       # expand("03_CNV/{sample}.iSizeFreq.tsv", sample=SAMPLES),
       expand("03_CNV/{sample}_seg.tsv", sample=SAMPLES),
       #expand("03_CNV/Annot/{sample}_segment.bed", sample=SAMPLES),
       expand("03_CNV/Annot/{sample}.CNV.bed", sample=SAMPLES),
       expand("03_CNV/Annot/{sample}.CNVseq.bed", sample=SAMPLES),
       expand("03_CNV/Annot/{sample}.CNV.tsv", sample=SAMPLES),
       expand("03_CNV/{sample}.iSizeFreq.png", sample=SAMPLES),
       expand("03_CNV/{sample}.CNV_VAF.png", sample=SAMPLES),
       expand("03_CNV/{sample}.CN.bedGraph.gz", sample=SAMPLES),
       expand("03_CNV/{sample}.segCN.bedGraph.gz", sample=SAMPLES)
    #    expand("03_CNV/monoExoniCNV/{sample}.seg.merge.bed", sample=SAMPLES),
    #    expand("03_CNV/monoExoniCNV/{sample}.seg.merge.annot.bed", sample=SAMPLES),
    #    expand("03_CNV/monoExoniCNV/{sample}.monoExonic.CNV.bed", sample=SAMPLES),
    #    expand("03_CNV/monoExoniCNV/{sample}.monoExonic.CNV.tsv", sample=SAMPLES),

# rule bam2blockUniq:
#     input:
#         Bam = "00_PreCalling/{sample}.deduped.bam",
#     output:
#         blkout="03_CNV/{sample}.blk",
#         iSizeFreq="03_CNV/{sample}.iSizeFreq.tsv"
#     params:
#         predix="{sample}",
#     log:
#         logfile="03_CNV/{sample}.log"
#     resources:
#         qsub_vf=30000
#     threads:4
#     shell:
#         """
#         {bam2blockUniqTools} -m 36 -U {BIN2POS} -C {wgEncodeCrgMapability} -b 2 -S 1 {input.Bam} -o {params.predix} > {output.blkout} 2> {log.logfile}
#         mv {params.predix}.iSizeFreq.tsv 03_CNV
#         """
rule fastqCount:
    input:
        jsonlist=expand("07_QC/{sample}.template.json", sample=SAMPLES)
    output:
        "03_CNV/fastq_count.tsv",
    params:
        suffix="template.json",
        indir="./"
    resources:
        qsub_vf=30000
    run:
        read_fastp_json(input.jsonlist, params.indir, params.suffix, output[0])
rule GCcorrect:
    input:
        expand("00_PreCalling/{sample}.blk", sample=SAMPLES)
    output:
        "03_CNV/GCcorrected.tsv"
    params:
        inputparms ="  ".join(expand(wkdir+"/00_PreCalling/{sample}.blk", sample=SAMPLES)),
        newout="GCcorrected.tsv"
    threads:24
    resources:
        qsub_vf=30000
    shell:
        """
        cd 03_CNV
        {GCcorrectTools} -o {params.newout}  {params.inputparms}
        cd ../
        """
rule CNVcalling:
     input:
        GCcorrect="03_CNV/GCcorrected.tsv",
        fastqCount="03_CNV/fastq_count.tsv",
        logfiles=expand(wkdir+"/00_PreCalling/{sample}.log", sample=SAMPLES),
        blks=expand(wkdir+"/00_PreCalling/{sample}.blk", sample=SAMPLES)
     output:
        expand("03_CNV/{sample}_seg.tsv", sample=SAMPLES),
        expand("03_CNV/{sample}.normalize.bed", sample=SAMPLES),
        "03_CNV/mappingQC.csv"
     params:
        d=disease,
        newgc="GCcorrected.tsv",
        newfc="fastq_count.tsv",
        cnvControl = f"--refData {refCNVdata} --refSexData {refSexData} --absCtrls" if config["use_reference"] == "ref" else (f"--refData {refCNVdata} --refSexData {refSexData}" if config["use_reference"] == "all" else "")
     threads:8
     resources:
        qsub_vf=32000
     shell:
         """
         cd 03_CNV
         cp {input.logfiles} ./
         cp {input.blks} ./
         {Rscript} {CNVcallingR} --inputBed {params.newgc} --cytoFile {cytoband} --fastqCount {params.newfc} --Disease {disease} --Polymorphism {polymorphism} --axis-y-max 4 --axis-y-min 0 --HLAstart 28510120 --HLAend 33480577 --PAR {parbed} --assembly GRCh38 --chromCN  All.chrom.CN.tsv --sexCutoff 0.0005 {params.cnvControl} --minSamples 20
         cd ../
         """
rule formatCNV:
    input:
         "03_CNV/{sample}_seg.tsv",
    output:
          #"03_CNV/Annot/{sample}_segment.bed",
          "03_CNV/Annot/{sample}.CNVseq.bed"
    threads:1
    resources:
        qsub_vf=100
    shell:
         """
         #awk -F '\t' 'BEGIN{{OFS="\t"}}{{if(NR==1)print $2,$3,$4,$5,$8,$10,$1;else if($1!="ID" && $12>0.3) print $2,$3,$4,$5,$8,$11,$1}}' {input[0]} > {output[0]}
         #cat {output[0]}|sed -e '1d' -e 's/DEL/\-/' -e 's/DUP/\+/'|awk -F "\t" 'BEGIN{{OFS="\t"}} $3-$2>20 {{print $1,$2,$3,$6,"NA",$4}}' > {output[0]}
         {Rscript} {formatCNVDirect} {input[0]} {output[0]}
         """
rule CNV_VAF_plot:
    input:
        cn = "03_CNV/{sample}.normalize.bed",
        vaf = "01_SNV/{sample}.vaf",
        roh = "05_ROH/AutoMap/{sample}/{sample}.HomRegions.tsv"
    output:
        genomePng = "03_CNV/{sample}.CNV.genome.png",
        cnvVafPng = "03_CNV/{sample}.CNV_VAF.png",
        cn_bedGraph = "03_CNV/{sample}.CN.bedGraph.gz",
        cnseg_bedGraph = "03_CNV/{sample}.segCN.bedGraph.gz"
    resources:
        qsub_vf=10000
    params:
        outpath='03_CNV',
        sampleN="{sample}"
    threads:1
    shell:
         """
         cd 03_CNV
         {Rscript} {cnv_vafPlot} --reference-fai {reference}.fai --out-chrom {wkdir}/{params.outpath}/{params.sampleN}_chrom%s.png --out-genome  {wkdir}/{output.genomePng} --input-bed {wkdir}/{input.cn} --vaf-bed {wkdir}/{input.vaf} --roh {wkdir}/{input.roh} --samples {params.sampleN} --cytoband {cytoband} --Polymorphism {polymorphism} --Disease {disease} --UPD {Pathogenic_UPD}
         cd ../
         awk -F'\\t' '{{OFS="\\t"; print $1, $2, $3, $6}}' {input.cn} | {bgzip} -c -@ 8 > {output.cn_bedGraph}
         {tabix} -fp bed {output.cn_bedGraph}
         awk -F'\\t' '{{OFS="\\t"; print $1, $2, $3, $7}}' {input.cn} | {bgzip} -c -@ 8 > {output.cnseg_bedGraph}
         {tabix} -fp bed {output.cnseg_bedGraph}
         """
# rule CNVannotation:
#     input:
#         CNVbed = "03_CNV/Annot/{sample}.CNV.bed",
#         pedfile = expand("08_ped/{pedigree}.ped",pedigree=config["pedigree"]),
#     output:
#         CNV = "03_CNV/Annot/{sample}.CNV.tsv"
#     params:
#         sample="{sample}",
#         outpath='03_CNV/Annot/'
#     resources:
#         qsub_vf=10000
#     threads:1
#     run:
#         phenotype =config["phenotype"][params.sample]
#         pedigreeIDlist = config["sample2pedigree"]
#         for j in pedigreeIDlist:
#             sampleId=j.split(':')[0]
#             if sampleId==params.sample:
#                 pedigreeID=j.split(':')[1]
#         if phenotype=="":
#             phenotype="null"
#         print('perl {cnvAnnotation} -i {wkdir}/{input.CNVbed} -o {wkdir}/{output.CNV}  -hpo "{phenotype}" -ped {wkdir}/08_ped/{pedigreeID}.ped -cfg config.yaml')
#         shell('perl {cnvAnnotation} -i {wkdir}/{input.CNVbed} -o {wkdir}/{output.CNV}  -hpo "{phenotype}" -ped {wkdir}/08_ped/{pedigreeID}.ped -cfg config.yaml')
rule mergeCNV:
    input:
        CNVbed = "03_CNV/Annot/{sample}.CNVseq.bed",
        SVbed="04_SV/{sample}.SV_CNV.bed",
    output:
        mergeCNVtmp = temp("03_CNV/Annot/{sample}.CNV.tmp.bed"),
        mergeCNV = "03_CNV/Annot/{sample}.CNV.bed",
    threads:1
    resources:
        qsub_vf=100
    shell:
         """
         awk '{{print $0"\tCNVseq"}}' {input.CNVbed} > {output.mergeCNVtmp}
         cat {output.mergeCNVtmp} {input.SVbed} |sort -k1,1V -k2,2n -k3,3n >{output.mergeCNV}
         """
rule CNVannotation:
    input:
        CNVbed =expand("03_CNV/Annot/{sample}.CNV.bed", sample=SAMPLES),
        pedfile = "08_ped/"+batch+".ped",
        sampleRank="08_ped/"+batch+".rank.txt"
    output:
        CNV = "03_CNV/Annot/{sample}.CNV.tsv",
    resources:
        qsub_vf=10000
    threads:1
    run:
        sampleid = re.sub(r'.CNV.tsv','',output.CNV)
        sampleid = re.sub(r'03_CNV/Annot/','',sampleid)
        phenotype ='"'+config["phenotype"][sampleid]+'"'
        pedigreeID=''
        pedigreeIDlist = config["sample2pedigree"]
        for j in pedigreeIDlist:
            sampleId=j.split(':')[0]
            if sampleId==sampleid:
                pedigreeID=j.split(':')[1]
        if phenotype=="":
            phenotype="null"
        CNVbedFile=wkdir+'/03_CNV/Annot/'+sampleid+'.CNV.bed'
        outfile=wkdir+'/03_CNV/Annot/'+sampleid+'.CNV.tsv'
        print('{python3}/python {cnvAnnotation} -I '+CNVbedFile+' -O '+outfile+' -s '+sampleid+' --hpo '+phenotype+' --ped 08_ped/'+pedigreeID+'.ped -cfg config.yaml')
        shell('{python3}/python {cnvAnnotation} -I '+CNVbedFile+' -O '+outfile+' -s '+sampleid+' --hpo '+phenotype+' --ped 08_ped/'+pedigreeID+'.ped -cfg config.yaml')
rule insertplot:
    input:
         "00_PreCalling/{sample}.iSizeFreq.tsv"
    output:
          "03_CNV/{sample}.iSizeFreq.png",
    params:
          indir="03_CNV",
          outsuffix="cfDNA_size",
          xmax=500,
          samplesuffix="{sample}.iSizeFreq",
          newinput="{sample}.iSizeFreq.tsv"
    threads:1
    resources:
        qsub_vf=100
    shell:
         """
         cd 03_CNV
         {Rscript} {LengthDistBatch} ../00_PreCalling {params.outsuffix} {params.xmax}
         {Rscript} {LengthDist} {wkdir}/{input[0]} {params.samplesuffix} 500
         cd ../
         """
# rule monoExonCNV:
#     input:
#         expand("07_QC/{sample}.deduped.bam.1.depth", sample=SAMPLES)
#     output:
#          expand("03_CNV/monoExoniCNV/{sample}.seg.merge.bed", sample=SAMPLES)
#     threads:1
#     resources:
#         qsub_vf=100
#     shell:
#         """
#          cd {wkdir}/03_CNV/monoExoniCNV/
#         {Rscript} {monoExoniCNV} --inDir {wkdir}/07_QC --bedFile {exonIntron} --geneInfo {geninfo}  --ctrlDir ss
#         """
# XX script
# rule monoExonCNVAnnot:
#     input:
#          "03_CNV/monoExoniCNV/{sample}.seg.merge.bed"
#     output:
#           "03_CNV/monoExoniCNV/{sample}.seg.merge.annot.bed"
#     threads:1
#     resources:
#         qsub_vf=100
#     params:
#         ref="GRCh38"
#     shell:
#         """
#         cd 03_CNV/monoExoniCNV/
#         {Rscript} {monoExoniCNVAnnot} -i {input[0]} -o {output[0]} --genomeBuild {params.ref}
#         """
# rule monoExonCNVformat:
#     input:
#         "03_CNV/monoExoniCNV/{sample}.seg.merge.bed"
#     output:
#         temp("03_CNV/monoExoniCNV/{sample}.monoExonic.CNV.tmp.bed"),
#         "03_CNV/monoExoniCNV/{sample}.monoExonic.CNV.bed"
#     threads:1
#     resources:
#         qsub_vf=100
#     shell:
#         """
#         #cat {input[0]}|sed -e '1d' -e 's/DEL/\-/' -e 's/DUP/\+/'|awk -F "\t" 'BEGIN{{OFS="\t"}} $3-$2>20 {{print $1,$2,$3,$8,"NA",$4}}' > {output[0]}
#         Rscript -e 'suppressPackageStartupMessages(library(dplyr)); Seg<-read.table("{input[0]}",header=T,sep="\\t",stringsAsFactors=FALSE,check.names=FALSE,encoding="UTF-8") %>% select(chrom,start,end,CN,zScore,type) %>% mutate(type=ifelse(type=="DEL","-","+")); subSeg<-Seg[Seg$end-Seg$start>20,];write.table(subSeg,file="{output[0]}",sep="\\t",quote = FALSE,row.names=F,col.names=F);'
#         sed -i 's/^chr//' {output[0]}
#         awk '{{print $0"\tmonoExonic"}}' {output[0]} >{output[1]}
#         """
# rule monoExonCNVAnnot:
#     input:
#         CNVbed = expand("03_CNV/monoExoniCNV/{sample}.monoExonic.CNV.bed", sample=SAMPLES),
#         pedfile = "08_ped/"+batch+".ped",
#         sampleRank="08_ped/"+batch+".rank.txt"
#     output:
#         CNV = "03_CNV/monoExoniCNV/{sample}.monoExonic.CNV.tsv"
#     resources:
#         qsub_vf=10000
#     threads:1
#     run:
#         sampleid = re.sub(r'.monoExonic.CNV.tsv','',output.CNV)
#         sampleid = re.sub(r'03_CNV/monoExoniCNV/','',sampleid)
#         phenotype ='"'+config["phenotype"][sampleid]+'"'
#         pedigreeIDlist = config["sample2pedigree"]
#         pedigreeID=''
#         for j in pedigreeIDlist:
#             sampleId=j.split(':')[0]
#             if sampleId==sampleid:
#                 pedigreeID=j.split(':')[1]
#         if phenotype=="":
#             phenotype="null"
#         CNVbedFile=wkdir+'/03_CNV/monoExoniCNV/'+sampleid+'.monoExonic.CNV.bed'
#         outfile=wkdir+'/03_CNV/monoExoniCNV/'+sampleid+'.monoExonic.CNV.tsv'
#         print('{python3}/python {cnvAnnotation} -i '+CNVbedFile+' -o '+outfile+'  -hpo '+phenotype+' -ped 08_ped/'+pedigreeID+'.ped -cfg config.yaml')
#         shell('{python3}/python {cnvAnnotation} -I '+CNVbedFile+' -O '+outfile+' -s '+sampleid+' --hpo '+phenotype+' --ped 08_ped/'+pedigreeID+'.ped -cfg config.yaml')
# rule monoExonCNVAnnotE:
#     input:
#         CNVbed = "03_CNV/monoExoniCNV/{sample}.monoExonic.CNV.bed"
#     output:
#         CNV = "03_CNV/monoExoniCNV/{sample}.monoExonic.CNV.tsv"
#     params:
#         sample="{sample}",
#         outpath='03_CNV/monoExoniCNV/'
#     resources:
#         qsub_vf=10000
#     threads:1
#     run:
#         phenotype =config["phenotype"][params.sample]
#         pedigreeIDlist = config["sample2pedigree"]
#         for j in pedigreeIDlist:
#             sampleId=j.split(':')[0]
#             if sampleId==params.sample:
#                 pedigreeID=j.split(':')[1]
#         if phenotype=="":
#             phenotype="null"
#         print('perl {cnvAnnotation} -i {input.CNVbed} -o {output.CNV}  -hpo "{phenotype}" -ped 08_ped/{pedigreeID}.ped -cfg config.yaml')
#         shell('perl {cnvAnnotation} -i {input.CNVbed} -o {output.CNV}  -hpo "{phenotype}" -ped 08_ped/{pedigreeID}.ped -cfg config.yaml')
