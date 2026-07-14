"""
@author:Rzhang
@file: WGS_pipeline.Snakefile
@time: 2021/09/08
@contact: zhiangrian@126.com,zhangran@biosan.cn
@site:
@software: PyCharm
@version 1.0
A WGS analysis workflow ,including SNV/Indel, CNV,SV,MT,RE calling ,annotation and filtering.
vim config.yaml and set samples list ,extention, hpoID for each sample in the samples list
vim sampleinfo.txt and input sample and trio info
run :snakemake --snakefile  /clinical/zhangran/snamketest/Snakefile --configfile /clinical/zhangran/snamketest/config.yaml  -d "/bi/6.zhangran/WGS_pipeline/ningbo_WGS/newbam20210902/" --singularity-args 'export SENTIEON_LICENSE=/ssd_temp/0.houmin/software/Sentieon/Zhejiang_Biosan_Biotechnology_Co._LTD_cluster.lic; export LD_PRELOAD=/ssd_temp/0.houmin/software/Sentieon/sentieon-genomics-201911/lib/libjemalloc.so;export MALLOC_CONF=lg_dirty_mult:-1' --cores 4
"""

##-----------------------------------------------##
## V1.1.0
#### update@zhangran,20220218,构建完成本地人群频率库，包含141个WGS样本
#### update@zhangran,20220406,添加ExpansionHunter的注释,升级ExpansionHunter从v4.0.2到5.0.0
#### update@zhangran,20220412,QC结果添加预测和判断性别，并把同一个批次的所有样本QC结果进行合并
#### update@zhangran,20220415,去掉CNVCalling.Snakefile中的CNVmapping 过程，在CNV.smk中增加bam2blockUniq调用许老师的/bi/8.xuxiong/work/CNVseq/bam2block_uniq流程直接从bam文件中提取depth信息生成blk文件
#### update@zhangran,20220415,去掉0.Config.V1.0.2.py中生成CNVmapping的snakemake命令
#### update@zhangran,20220418,添加SV流程call到的CNV的分离和注释流程，CNV.smk中的rule splitSVCNV和rule SVoutannotation
#### update@zhangran,20220420,WGS_SNV.smk中添加peddy判断家系关系是否相符
#### update@zhangran,20220421,添加MIE分析绘图,把WES流程中的perl脚本改成适用于WGS目录结构的python脚本，trio_MIE.py
#### update@zhangran,20220429,把待注释的vcf文件分成是否已经注释过的，只对未注释过的变异进行注释，然后再合并，这部分嵌套到2.Filter.V6.0.5.pl脚本中
#### update@zhangran,20220524,CNV.smk中的CNVcalling运行一次即可生成所有样本的seg.tsv文件，原来错误的每个样本都运行一遍，更改为 output改成list
#### update@zhangran,20220601,移动rule peddy判断家系关系是否相符到ROH.smk中
## V1.2.0
#### update@zhangran,20220616,ROH.smk中rule vcf2vaf修改vcf2vaf的工具，原来的C版本有bug,改成bcftools进行处理
#### update@zhangran,20220616,修改0.Config.V1.0.2.py文件中的bcftools的版本从/bi/software/bcftools 到 bi/software/bcftools-1.15.1
#### update@zhangran,20220616,ROH.smk中rule vcf2vaf中的rule vcfflt修改ROH vcf过滤的参数，由原来的FMT/NR[0:0]>=20 更新为FMT/NR[0:0]>=20 & QUAL>=30 & GT[0:0]!="RR" & GT[0:0]!="AA" & GT[0:0]!="mis",保留高质量的点
## V1.2.1
#### update@zhangran,20220706,新增WGS_pipeline_fastq2vcf.Snakefile,rule/pre_calling_solo.smk, script/0.pre_fastq2vcf.py,script/1.Config_fastq2vcf.V1.0.2.py文件，解决自动扫描下机表目录并对满足分析要的要求生成配置文件和运行命令的功能，即不依赖样本信息把先运行fastq到gvcf这一步功能
#### update@zhangran,20220706,单独为运行fastq-vcf文件创建的文件
## V1.2.2
#### update@zhangran,20220902,解决了0.prefastq2vcf.py脚本中第112行的bug,file变量只是文件名称，没有文件路径，导致会抛出异常
#### update@zhangran,20220907,修改该文件加载的rule，去掉precalling的rule
## V2.0
####updata@zhangran,20240423,新增夫妻配对分析模块CSis=variantIs["CS"],include: "rule/WGS_CS.smk",if CSis=="YES":rule_all.append(rules.CSall.input)


##-----------------------------------------------##

import os
from os.path import join
shell.executable("/bin/bash")
WDIR = os.getcwd()
workdir: WDIR
#print("The current working directory is " + WDIR)
variantIs=config["VariantTypeSet"]
SNVis=variantIs["SNV"]
CNVis=variantIs["CNV"]
SVis=variantIs["SV"]
MTis=variantIs["MT"]
ROHis=variantIs["ROH"]
REis=variantIs["RE"]
MEIis=variantIs["MEI"]
CSis=variantIs["CS"]
#print ("SNVis:" +SNVis+"\t"+"CNVis:"+CNVis+"\t"+"SVis: "+SVis+"\t"+"REis:"+REis+"\t"+"ROHis:"+ROHis+"\t"+"MTis:"+MTis)
#gvcfParam=""
#for smp in SAMPLES:
    #print("Sample " + smp + " will be processed")
#gvcfs = list(map("-v {}.g.vcf".format, SAMPLES))

include: "rule/WGS_SNV.smk"
include: "rule/WGS_SV.smk"
include: "rule/WGS_MT.smk"
include: "rule/WGS_RE.smk"
include: "rule/ROH.smk"
include: "rule/CNV.smk"
include: "rule/MEI.smk"
include: "rule/SMA.smk"
include: "rule/WGS_CS.smk"
include: "rule/QC.smk"

rule_all=[]
if SNVis=="YES":rule_all.append(rules.SNVall.input)
if REis=="YES":rule_all.append(rules.REall.input)
if CNVis=="YES":
    rule_all.append(rules.CNVall.input)
if SVis=="YES":
    rule_all.append(rules.SVall.input)
if ROHis=="YES":rule_all.append(rules.ROHall.input)
if MTis=="YES":
    rule_all.append(rules.MTall.input)
if MEIis=="YES":rule_all.append(rules.MEIall.input)
if CSis=="YES":rule_all.append(rules.CSall.input)
#print(rule_all)
rule_all.append(rules.SMAall.input)
rule_all.append(rules.QCall.input)

#print(rule_all)
rule all:
    input:
        rule_all
