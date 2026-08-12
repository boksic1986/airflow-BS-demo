#!/usr/bin/env python  
# -*- coding:utf-8 _*-
""" 
@author:Rzhang 
@license: Apache Licence 
@file: upload.web.py
@time: 2022/10/12
@contact: zhiangrian@126.com
@site:  
@software: PyCharm
## V1.1
#### update@zhangran,20221019,增加拷贝SV的结果到webPath目录下
## V1.2
#### update@zhangran,20230321,增加拷贝SMA的结果到webPath和batchPath目录下
# V1.3
#### updatee@zhangran,20230427,修改script/upload.web.py脚本，新增SMA批次结果和样本结果上传代码
# V3.5.0
#### updat by yuli,20250225,修改script/upload.web.py脚本，新增上海汉春医疗科技有限公司WGS 的verbose的SNV结果按照批次上次到贝康WES的域中上传代码
"""
import argparse
import yaml
import os
import glob
import pandas as pd
import re
parser = argparse.ArgumentParser()
parser.add_argument("--sourcePath", help = "source file path", required = True)
parser.add_argument("--webPath", help = "source file of webpath", default = "/data/MASTER_WEB", required = True)
args = parser.parse_args()


def readYaml(yamlFile):
    with open(yamlFile, 'r', encoding = "utf-8") as f:
        result = yaml.load(f.read(), Loader = yaml.FullLoader)
    return result


if __name__ == '__main__':
    webPath = args.webPath
    sourcePath = args.sourcePath + '/'
    configfile = sourcePath + '/config.yaml'
    configDict = readYaml(configfile)
    pedigreelist = configDict['pedigree']
    coupleList = configDict['CS']
    mtPedigreeList = configDict['mtPedigreeList']
    batch = configDict['batch']
    batch_split = '_'.join(batch.split('_')[:2])
    fastqPath = configDict['fastqPath']
    newSampleinfoPath = webPath + '/sampleinfo'
    batchPath = webPath + '/' + batch
    sourceSamplefile = configDict['new_sample_info']
    if not os.path.exists(sourceSamplefile):
        sourceSamplefile = configDict['new_sample_info'].replace('.true','')
    if not os.path.exists(batchPath):
        os.makedirs(batchPath)
    os.system('cp ' + sourcePath + '03_CNV/'+batch+'.SMA.tsv ' + batchPath)
    os.system('cp ' + sourcePath + '03_CNV/heatmap_h.png ' + batchPath + '/' + batch + '_heatmap_h.png')
    os.system('cp ' + sourcePath + '03_CNV/'+batch+'.copynumber.txt ' + batchPath)
    os.system('cp ' + sourcePath + '03_CNV/'+batch+'.depth.r2.png ' + batchPath)
    # os.system('cp ' + sourcePath + '03_CNV/All.join.log2r.bed.gz ' + batchPath + '/' + batch + '_log2ratio.bed.gz')
    # os.system('cp ' + sourcePath + '03_CNV/All.join.log2r.bed.gz.tbi ' + batchPath + '/' + batch + '_log2ratio.bed.gz.tbi')
    os.system('cp ' + sourcePath + '07_QC/' + batch + '.QCstat.tsv ' + batchPath + '/' + batch + '.QC.tsv')
    os.system('cp ' + sourcePath + '03_CNV/All.chrom.CN.tsv ' + batchPath + '/All.chrom.CN.tsv')
    os.system('cp ' + sourcePath + '03_CNV/heatmap.chrom.CN.png ' + batchPath + '/heatmap.chrom.CN.png')
    os.system('cp ' + sourcePath + '07_QC/' + batch + '.MTQC.txt ' + batchPath + '/' + batch + '.MTQC.txt')
    os.system('cp ' + sourcePath + '07_QC/' + batch + '.QC.png ' + batchPath)
    os.system("cp " + sourcePath + "07_QC/" +  batch + '.ped_check.csv ' + batchPath + '/' + batch + '.peddy.ped_check.csv')

    Allpedigreelist = []
    sample2pedigreeList = configDict['sample2pedigree']
    trioPairList = configDict['trioPair']
    trio2ProbandDict = {}
    if len(trioPairList) != 0:
        for term in trioPairList:
            trioID = term.split(':')[0]
            proband = term.split(':')[1]
            trio2ProbandDict[trioID] = proband
    pedigree2sampleDict = {}
    for j in sample2pedigreeList:
        sample = j.split(':')[0]
        pedigree = j.split(':')[1]
        if pedigree in pedigree2sampleDict:
            pedigree2sampleDict[pedigree].append(sample)
        else:
            pedigree2sampleDict[pedigree] = [sample]
        Allpedigreelist.append(pedigree)
    for value in list(set(Allpedigreelist)):
        i = re.sub(r'[A-Za-z]+$', '',value.split('_')[0])
        pedigreePath = batchPath + '/' + i
        if not os.path.exists(pedigreePath):
            os.makedirs(pedigreePath)
        if value in pedigreelist:
            os.system("cp " + sourcePath + "01_SNV/" + value + '.flt.tsv  ' + pedigreePath)
        if value in coupleList:
            os.system("cp " + sourcePath + "01_SNV/" + value + '.markCS.flt.tsv ' + pedigreePath)
        if value in trio2ProbandDict:
            probandID = trio2ProbandDict[value]
            os.system("cp " + sourcePath + "10_MIE/" + value + '.trio.MIE.png  ' + pedigreePath + '/' + probandID + ".MIE.png")
        if value in mtPedigreeList:
            os.system("cp " + sourcePath + "11_MT/" + value + '.mity.flt.txt ' + pedigreePath+ '/' + value + ".MT.tsv")
        for j in list(set(pedigree2sampleDict[value])):
            os.system("cp " + sourcePath + "03_CNV/" + j + '.log2r_v.png ' + pedigreePath + '/' + j + ".CNV.colorful.png")
            os.system("cp " + sourcePath + "03_CNV/" + j + '.log2r_h.png ' + pedigreePath + '/' + j + ".CNV.genome.png")
            os.system("cp " + sourcePath + "03_CNV/" + j + '.chrom.Anno.tsv ' + pedigreePath)
            os.system("cp " + sourcePath + "03_CNV/" + j + '.ctrl.copynumber.txt ' + pedigreePath)
            os.system("cp " + sourcePath + "03_CNV/" + j + '.CNV_VAF.png ' + pedigreePath + '/' + j + ".CNV_VAF.png")
            os.system("cp " + sourcePath + "03_CNV/" + j + '.CNV_VAF_noXY.png ' + pedigreePath + '/' + j + ".CNV_VAF_noXY.png")
            os.system("cp " + sourcePath + "03_CNV/Annot/" + j + '.CNV.tsv ' + pedigreePath + '/' + j + ".CNV.tsv")
            os.system("cp " + sourcePath + "03_CNV/SMA/" + j + '.SMA.tsv ' + pedigreePath + '/' + j + ".SMA.tsv")
            os.system("cp " + sourcePath + "03_CNV/SMA/smn_" + j + '.pdf ' + pedigreePath + '/' + j + ".SMA.pdf")
            os.system("cp " + sourcePath + "04_SV/c.sort/" + j + '.SV.sort.tsv ' + pedigreePath + '/' + j + ".SV.sort.tsv")
            os.system("cp " + sourcePath + "06_STR/" + j + '.expansionHunter.tsv ' + pedigreePath)
            os.system("cp " + sourcePath + "05_ROH/" + j + '.HomRegions.tsv ' + pedigreePath)
            os.system("cp " + sourcePath + "05_ROH/AutoMap/" + j + '_ROH_annotataion.txt ' + pedigreePath)
            os.system("cp " + sourcePath + "05_ROH/" + j + '.vaf.genome.png ' + pedigreePath)
            os.system("cp " + sourcePath + "05_ROH/" + j + '.vaf.genome.png_noXY.png ' + pedigreePath)
            os.system("cp " + sourcePath + "05_ROH/" + j + '.vaf.chrs.png ' + pedigreePath)
            os.system("cp " + sourcePath + "09_MEI/" + j + '.MEIs.tsv ' + pedigreePath)
            os.system("ln -s -f " + sourcePath + "00_PreCalling/" + j + ".deduped.cram " + pedigreePath + '/' + j + '.igv.cram')
            os.system("ln -s -f " + sourcePath + "00_PreCalling/" + j + ".deduped.cram.crai " + pedigreePath + '/' + j + '.igv.cram.crai')
            os.system("cp " + sourcePath + "01_SNV/" + j + '.vaf.bedGraph.gz ' + pedigreePath)
            os.system("cp " + sourcePath + "01_SNV/" + j + '.vaf.bedGraph.gz.tbi ' + pedigreePath)
            os.system("cp " + sourcePath + "03_CNV/" + j + '.CN.bedGraph.gz ' + pedigreePath)
            os.system("cp " + sourcePath + "03_CNV/" + j + '.CN.bedGraph.gz.tbi ' + pedigreePath)
            os.system("cp " + sourcePath + "03_CNV/" + j + '.segCN.bedGraph.gz ' + pedigreePath)
            os.system("cp " + sourcePath + "03_CNV/" + j + '.segCN.bedGraph.gz.tbi ' + pedigreePath)
            os.system("cp " + sourcePath + "03_CNV/" + j + '.SLC25A13.tsv ' + pedigreePath)
            os.system("cp " + sourcePath + "07_QC/" + j + '.QC.tsv  ' + pedigreePath)
            os.system("cp " + sourcePath + "11_MT/" + j + '.mity.flt.txt  ' + pedigreePath+ '/' + j + '.MT.txt')
            os.system("cp " + sourcePath + "01_SNV/" + j + '.flt.tsv  ' + pedigreePath)

    print('cp ' + sourceSamplefile + " " + newSampleinfoPath + '/' + batch + '.sampleinfo.txt')
    # os.system('cp ' + sourceSamplefile + " " + newSampleinfoPath + '/' + batch + '.sampleinfo.txt')
