"""
@author:Rzhang
@file: WGS_pipeline.Snakefile
@time: 2021/09/08
@contact: zhiangrian@126.com,zhangran@biosan.cn
@site:
@software: PyCharm
@version 1.2.1
A WGS analysis workflow ,including SNV/Indel, CNV,SV,MT,RE calling ,annotation and filtering.
vim config.yaml and set samples list ,extention, hpoID for each sample in the samples list
vim sampleinfo.txt and input sample and trio info
run :snakemake --snakefile  /clinical/zhangran/snamketest/Snakefile --configfile /clinical/zhangran/snamketest/config.yaml  -d "/bi/6.zhangran/WGS_pipeline/ningbo_WGS/newbam20210902/" --singularity-args 'export SENTIEON_LICENSE=/ssd_temp/0.houmin/software/Sentieon/Zhejiang_Biosan_Biotechnology_Co._LTD_cluster.lic; export LD_PRELOAD=/ssd_temp/0.houmin/software/Sentieon/sentieon-genomics-201911/lib/libjemalloc.so;export MALLOC_CONF=lg_dirty_mult:-1' --cores 4
"""

##-----------------------------------------------##
## V1.2.1
#### update@zhangran,20220706,单独为运行fastq-vcf文件创建的文件
## V1.2.2
#### update@zhangran,20220902,解决了0.prefastq2vcf.py脚本中第112行的bug,file变量只是文件名称，没有文件路径，导致会抛出异常
## V3.0
#### update@zhangran,20230725,采用hg38版本，只运行rule/pre_sampleInfo_solo.smk

##-----------------------------------------------##

import os
from os.path import join
shell.executable("/bin/bash")
WDIR = os.getcwd()
workdir: WDIR

include: "rule/pre_sampleInfo_solo.smk"

rule_all=[]
rule_all.append(rules.Preall.input)

rule all:
    input:
        rule_all
