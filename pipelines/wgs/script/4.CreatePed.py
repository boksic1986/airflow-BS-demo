#!/usr/bin/env python  
# -*- coding:utf-8 _*-
""" 
@author:Rzhang 
@license: Apache Licence 
@file: 4.CreatePed.py
@time: 2022/09/26
@contact: zhiangrian@126.com
@site:  
@software: PyCharm

#家系送检模式分类：
#1. 超过4人，需要手工处理
#2. 3-4人：a. 一家三口，孩子是患者；b. 一家三口，夫妻一方是患者；c. 父母+2个孩子
#3. 2人：a. 夫妻双方，表型均正常；b. 夫妻双方，一方是患者；c. 夫妻双方均是患者
#4. 1人：统一按单先证者模式分析

## V0.1
#### update@zhangran,20230404,解决了家系中存在其它样本表型不一致，所提关键词不一致导致家系分析关键词使用错误，已经合并家系成员关键词分析，家系和单人分析都合并
"""

import argparse
import re
from collections import defaultdict

parser = argparse.ArgumentParser(description = 'generate ped file')
parser.add_argument("--outpath", type = str, default = "08_ped", help = 'split family ped out path')
parser.add_argument("--outbatch", type = str, default = "WGS_20220906_T7", help = 'variants out batch name')
parser.add_argument('--gender', type = str, required = False, help = 'gender file ')
parser.add_argument('--sampleInfo', type = str, required = True, help = 'sample information file')
args = parser.parse_args()


def readSample(sampleinfoFile):
    file = open(sampleinfoFile, 'r', encoding = "utf-8")
    head = file.readline().strip('\r\n')
    ar = head.split('\t')
    trioindex = ar.index('家系编号')
    dataindex = ar.index('数据编号')
    methodindex = ar.index('检测方法')
    sampleBarcodeIndex = ar.index('样本条码')
    pedigreeRelationindex = ar.index('家系关系')
    hpoTermindex = ar.index('英文关键词')
    sampleIDindex = ar.index('样本编号')
    genderIndex = ar.index('性别')
    projectindex = ar.index('检测项目')
    isPatientIndex = ar.index('是否患者')
    hospitalIndex = ar.index('送检医院')
    hospitalBarcodeIndex = ar.index('医院编号')
    file.close()
    fam2proband = {}
    sample2Gender = defaultdict(str)
    sample2relation = defaultdict(dict)
    fam2phenotype = defaultdict(str)
    sample2status = defaultdict(str)
    family2project = defaultdict(str)
    family2panel = defaultdict(str)
    family2hospital = defaultdict(str)
    barcode2sampleID = defaultdict(str)
    family2hospitalSampleID = defaultdict(str)
    with open(sampleinfoFile, 'r', encoding = "utf-8") as hfp:
        next(hfp)
        for term in hfp:
            line = term.strip('\r\n')
            linelist = line.split('\t')
            trioID = linelist[trioindex]
            pedigreeRelation = linelist[pedigreeRelationindex]
            sampleID = linelist[sampleIDindex]
            dataID = linelist[dataindex]
            gender = linelist[genderIndex]
            if gender == '' or gender == '.' or gender == '未知':
                gender = 'ND'
            elif gender == '女':
                gender = 'F'
            elif gender == '男':
                gender = 'M'

            if pedigreeRelation == '先证者':
                if trioID in fam2proband:
                    fam2proband[trioID].append(sampleID)  ## maybe more than one proband in one family
                else:
                    fam2proband[trioID] = [sampleID]
            if args.gender:
                sample2Gender = readGender(args.gender)
            else:
                sample2Gender[dataID] = gender

    with open(sampleinfoFile, 'r', encoding = "utf-8") as Hfp:
        next(Hfp)
        for line in Hfp:
            line = line.strip('\r\n')
            linelist = line.split('\t')
            trioID = linelist[trioindex]
            dataID = linelist[dataindex]
            method = linelist[methodindex]
            isPatient = linelist[isPatientIndex]
            project = linelist[projectindex]
            hospital = linelist[hospitalIndex]
            sampleBarcode = linelist[sampleBarcodeIndex]
            pedigreeRelation = linelist[pedigreeRelationindex]
            hpoTerm = linelist[hpoTermindex]
            sampleID = linelist[sampleIDindex]
            hospitalBarcode = linelist[hospitalBarcodeIndex]
            for proband in fam2proband[trioID]:
                if proband not in sample2relation[trioID]:
                    sample2relation[trioID][proband] = defaultdict(dict)
                if pedigreeRelation != '先证者' or (pedigreeRelation == "先证者" and sampleID == proband):
                    sample2relation[trioID][proband][dataID] = pedigreeRelation
            if trioID in fam2phenotype:

                fam2phenotype[trioID] = fam2phenotype[trioID] + '|' + hpoTerm
                fam2phenotype[trioID] = fam2phenotype[trioID].strip('|')
            else:
                fam2phenotype[trioID] = hpoTerm
            hpotermslist = list(set(fam2phenotype[trioID].split('|')))
            fam2phenotype[trioID] = '|'.join(hpotermslist)
            sample2status[dataID] = isPatient
            family2project[trioID] = project
            family2panel[trioID] = method
            family2hospital[trioID] = hospital
            barcode2sampleID[sampleBarcode] = sampleID
            if hospitalBarcode != '' and hospitalBarcode != '.':
                family2hospitalSampleID[trioID] = hospitalBarcode
            else:
                family2hospitalSampleID[trioID] = '.'
    return fam2proband, sample2Gender, sample2relation, fam2phenotype, sample2status, family2project, family2panel, family2hospital, barcode2sampleID, family2hospitalSampleID


def readGender(genderfile):
    sample2gender = {}
    with open(genderfile, 'r', encoding = "utf-8") as hfp:
        for term in hfp:
            line = term.strip('\r\n')
            linelist = line.split(',')
            dataID = linelist[0]
            gender = linelist[1]
            sample2gender[dataID] = gender
    return sample2gender


if __name__ == '__main__':
    pedigree = defaultdict(dict)
    outPath = args.outpath
    batchPed = outPath + '/' + args.outbatch + '.ped'
    betchRank = outPath + '/' + args.outbatch + '.rank.txt'
    batchPedFile = open(batchPed, 'w')
    batchRankFile = open(betchRank, 'w')
    batchRankFile.write(
        'FamilyID\tProbandID\tDadID/SpouseID\tMomID/KidID\tOtherID\tProband\tDad/Spouse\tMom/Kid\tOther\tProbandGender\tDad/SpouseGender\tMom/KidGender\tOtherGender\tProbandStatus\tDad/SpouseStatus\tMom/KidStatus\tOtherStatus\tPhenotypeKeyWords\tHospital\tHospitalSampleID\n')
    fam2proband, sample2Gender, sample2relation, fam2phenotype, sample2status, family2project, family2panel, family2hospital, barcode2sampleID, family2hospitalSampleID = readSample(args.sampleInfo)

    print(sample2Gender)
    for familyID in sample2relation:
        rankItem = familyID + '\n'
        for proband in sample2relation[familyID]:
            probandID = proband + '-WGS'
            pedOutFile = open(outPath + '/' + familyID + '_' + probandID + '.ped', 'w')
            rankOutFile = open(outPath + '/' + familyID + '_' + probandID + '.rank.txt', 'w')
            samplelist = sample2relation[familyID][proband]
            sampleCount = len(samplelist)
            # print(sampleCount)
            if sampleCount > 4:
                print("the sample size of " + familyID + " is more than 4!\n")
                break
            ifProbandExists = 0
            splitMemberList = []
            pedigree[familyID][proband] = {}
            for sampleID in samplelist:
                relation = sample2relation[familyID][proband][sampleID]
                if relation == '先证者':
                    pedigree[familyID][proband]['0proband'] = sampleID
                elif relation == '父亲':
                    pedigree[familyID][proband]['1dad'] = sampleID
                elif relation == '母亲':
                    pedigree[familyID][proband]['2mom'] = sampleID
                elif relation == '妻子':
                    pedigree[familyID][proband]['3wife'] = sampleID
                elif relation == '丈夫':
                    pedigree[familyID][proband]['4husband'] = sampleID
                elif '哥' in relation or '姐' in relation or '妹' in relation or '弟' in relation or '双胞胎' in relation or '本人' in relation or '组织' in relation or '同胞' in relation:
                    pedigree[familyID][proband]['5sib'] = sampleID
                elif '儿子' in relation or '女儿' in relation or '胎儿' in relation:
                    pedigree[familyID][proband]['6kid'] = sampleID
                else:
                    pedigree[familyID][proband]['7other'] = sampleID
            # print(pedigree)
            if '0proband' in pedigree[familyID][proband]:
                probandID = pedigree[familyID][proband]['0proband']
                ifProbandExists = 1
            relationList = sorted(pedigree[familyID][proband])
            sampleCount = len(relationList)
            for relation in relationList:
                dad = mom = '0'
                sampleid = pedigree[familyID][proband][relation]
                splitMemberList.append(sampleid)
                sample2Gender[sampleid] = re.sub('F', '2', sample2Gender[sampleid])
                sample2Gender[sampleid] = re.sub('M', '1', sample2Gender[sampleid])
                sample2Gender[sampleid] = re.sub('ND', '0', sample2Gender[sampleid])
                sample2status[sampleid] = re.sub('是', '2', sample2status[sampleid])
                sample2status[sampleid] = re.sub('否', '1', sample2status[sampleid])
                # 送样模式：先证者+父亲（患者/正常）+可能有母亲（患者/正常）
                if (relation == '0proband' or relation == '5sib') and '1dad' in pedigree[familyID][proband]:
                    dad = pedigree[familyID][proband]['1dad']
                # 送样模式：先证者+母亲（患者/正常）+可能有父亲（患者/正常）
                if (relation == '0proband' or relation == '5sib') and '2mom' in pedigree[familyID][proband]:
                    mom = pedigree[familyID][proband]['2mom']
                # 送样模式：先证者+妻子+儿子/女儿；以先证者为基础进行分析
                elif relation == '6kid' and '3wife' in pedigree[familyID][proband]:
                    mom = pedigree[familyID][proband]['3wife']
                    dad = pedigree[familyID][proband]['0proband']
                # 送样模式：先证者+丈夫+儿子/女儿；以先证者为基础进行分析
                elif relation == '6kid' and '4husband' in pedigree[familyID][proband]:
                    mom = pedigree[familyID][proband]['0proband']
                    dad = pedigree[familyID][proband]['4husband']
                # 送样模式：先证者(父亲)+儿子/女儿+可能有爷爷奶奶；以先证者为基础进行分析
                elif relation == '6kid' and sample2Gender[probandID] == "1":
                    dad = pedigree[familyID][proband]['0proband']
                # 送样模式：先证者(母亲)+儿子/女儿+可能有外公外婆；以先证者为基础进行分析
                elif relation == '6kid' and sample2Gender[probandID] == "2":
                    mom = pedigree[familyID][proband]['0proband']
                if pedigree[familyID][proband][relation] == probandID:
                    ifProbandExists = 1
                pedItem = familyID + '_' + probandID + '\t' + sampleid + '\t' + dad + '\t' + mom + '\t' + str(sample2Gender[sampleid]) + '\t' + str(sample2status[sampleid])
                batchPedFile.write(pedItem + '\n')
                pedOutFile.write(pedItem + '\n')
            if ifProbandExists == 0:
                print("no proband in " + familyID + '!\n')
            if '1dad' in pedigree[familyID][proband]: dadID = pedigree[familyID][proband]["1dad"]
            if '2mom' in pedigree[familyID][proband]: momID = pedigree[familyID][proband]["2mom"]
            if '3wife' in pedigree[familyID][proband]: wifeID = pedigree[familyID][proband]["3wife"]
            if '4husband' in pedigree[familyID][proband]: husbandID = pedigree[familyID][proband]["4husband"]
            if '5sib' in pedigree[familyID][proband]: sibID = pedigree[familyID][proband]["5sib"]
            if '6kid' in pedigree[familyID][proband]: kidID = pedigree[familyID][proband]["6kid"]
            if '7other' in pedigree[familyID][proband]: otherID = pedigree[familyID][proband]["7other"]
            rank4List = ["3wife", "4husband", "5sib", "6kid", "7other"]

            if sampleCount == 1:
                rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + '.\t.\t.\t0proband\t.\t.\t.\t' + str(sample2Gender[probandID]) + '\t.\t.\t.\t' + str(
                    sample2status[probandID]) + '\t.\t.\t.\t' + str(fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(family2hospitalSampleID[familyID]) + '\n'
            elif sampleCount == 2:
                if '0proband' in pedigree[familyID][proband]:
                    # 先证者+父亲
                    if '1dad' in pedigree[familyID][proband]:
                        rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + dadID + '\t.\t.\t0proband\t1dad\t.\t.\t' + str(sample2Gender[probandID]) + '\t1\t.\t.\t' + str(
                            sample2status[probandID]) + '\t' + str(sample2status[dadID]) + '\t.\t.\t' + str(fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(
                            family2hospitalSampleID[familyID]) + '\n'
                    # 先证者+母亲
                    elif '2mom' in pedigree[familyID][proband]:
                        rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + '.\t' + momID + '\t.\t0proband\t.\t2mom\t.\t' + str(sample2Gender[probandID]) + '\t.\t2\t.\t' + str(
                            sample2status[probandID]) + '\t.\t' + str(sample2status[momID]) + '\t.\t' + str(fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(
                            family2hospitalSampleID[familyID]) + '\n'
                    # 先证者+子女
                    elif '6kid' in pedigree[familyID][proband]:
                        rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + '.\t' + kidID + '\t.\t0proband\t.\t6kid\t.\t' + str(sample2Gender[probandID]) + '\t.\t' + str(
                            sample2Gender[kidID]) + '\t.\t' + str(sample2status[probandID]) + '\t.\t' + str(sample2status[kidID]) + '\t.\t' + str(fam2phenotype[familyID]) + '\t' + str(
                            family2hospital[familyID]) + '\t' + str(family2hospitalSampleID[familyID]) + '\n'
                    for i in rank4List:
                        if i in relationList:
                            if i == '3wife' or i == '4husband':
                                rankItem = familyID + '_' + probandID + '\t' + probandID + '\t[keep]' + str(pedigree[familyID][proband][i]) + '\t.\t.' + '\t0proband\t' + i + '\t.\t.\t' + str(
                                    sample2Gender[probandID]) + '\t' + str(sample2Gender[pedigree[familyID][proband][i]]) + '\t.\t.\t' + str(sample2status[probandID]) + '\t' + str(
                                    sample2status[pedigree[familyID][proband][i]]) + '\t.\t.\t' + str(fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(
                                    family2hospitalSampleID[familyID]) + '\n'
                            else:
                                rankItem = familyID + '_' + probandID + '\t' + probandID + '\t.\t.\t' + str(pedigree[familyID][proband][i]) + '\t0proband\t' + '.\t.\t' + i + '\t' + str(
                                    sample2Gender[probandID]) + '\t.\t.\t' + str(sample2Gender[pedigree[familyID][proband][i]]) + '\t' + str(sample2status[probandID]) + '\t.\t.\t' + str(
                                    sample2status[pedigree[familyID][proband][i]]) + '\t' + str(fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(
                                    family2hospitalSampleID[familyID]) + '\n'
                else:
                    print("no proband in" + familyID + '!\n')
            elif sampleCount == 3:
                if '0proband' in pedigree[familyID][proband]:
                    # 先证者+父+母
                    if '1dad' in pedigree[familyID][proband] and '2mom' in pedigree[familyID][proband]:
                        rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + dadID + '\t' + momID + '\t.\t0proband\t1dad\t2mom\t.\t' + str(sample2Gender[probandID]) + '\t1\t2\t.\t' + \
                                   str(sample2status[probandID]) + '\t' + str(sample2status[dadID]) + '\t' + str(sample2status[momID]) + '\t.\t' + str(fam2phenotype[familyID]) + '\t' + str(
                            family2hospital[familyID]) + '\t' + \
                                   str(family2hospitalSampleID[familyID]) + '\n'

                    elif '3wife' in pedigree[familyID][proband]:
                        # 先证者+妻子+兄弟姐妹
                        if '5sib' in pedigree[familyID][proband]:
                            rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + wifeID + '\t.\t' + sibID + '\t0proband\t3wife\t.\t5sib\t' + str(sample2Gender[probandID]) + '\t2\t.\t' + \
                                       str(sample2Gender[sibID]) + '\t' + str(sample2status[probandID]) + '\t' + str(sample2status[wifeID]) + '\t.\t' + str(sample2status[sibID]) + '\t' + str(
                                fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + family2hospitalSampleID[familyID] + '\n'
                        # 先证者+妻子+子女
                        if '6kid' in pedigree[familyID][proband]:
                            rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + wifeID + '\t' + kidID + '\t.\t0proband\t3wife\t6kid\t.\t' + str(sample2Gender[probandID]) + '\t2\t' + \
                                       str(sample2Gender[kidID]) + '\t.\t' + str(sample2status[probandID]) + '\t' + str(sample2status[wifeID]) + '\t' + str(sample2status[kidID]) + '\t.\t' + str(
                                fam2phenotype[
                                    familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(family2hospitalSampleID[familyID]) + '\n'
                        # 先证者+妻子+其他
                        if '7other' in pedigree[familyID][proband]:
                            rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + wifeID + '\t.\t' + otherID + '\t0proband\t3wife\t.\t7other\t' + str(sample2Gender[probandID]) + '\t2\t.\t' + \
                                       str(sample2Gender[otherID]) + '\t' + str(sample2status[probandID]) + '\t' + str(sample2status[wifeID]) + '\t.\t' + str(sample2status[otherID]) + '\t' + str(
                                fam2phenotype[
                                    familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(family2hospitalSampleID[familyID]) + '\n'
                    elif '4husband' in pedigree[familyID][proband]:
                        # 先证者+丈夫+兄弟姐妹
                        if '5sib' in pedigree[familyID][proband]:
                            rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + husbandID + '\t.\t' + sibID + '\t0proband\t4husband\t.\t5sib\t' + str(
                                sample2Gender[probandID]) + '\t1\t.\t' + \
                                       str(sample2Gender[sibID]) + '\t' + str(sample2status[probandID]) + '\t' + str(sample2status[husbandID]) + '\t.\t' + str(sample2status[sibID]) + '\t' + str(
                                fam2phenotype[
                                    familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(family2hospitalSampleID[familyID]) + '\n'
                        # 先证者+丈夫+子女
                        if '6kid' in pedigree[familyID][proband]:
                            rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + husbandID + '\t' + kidID + '\t.\t0proband\t4husband\t6kid\t.\t' + str(sample2Gender[probandID]) + '\t1\t' + \
                                       str(sample2Gender[kidID]) + '\t.\t' + str(sample2status[probandID]) + '\t' + str(sample2status[husbandID]) + '\t' + str(sample2status[kidID]) + '\t.\t' + str(
                                fam2phenotype[
                                    familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(family2hospitalSampleID[familyID]) + '\n'
                        # 先证者+丈夫+其他
                        if '7other' in pedigree[familyID][proband]:
                            rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + husbandID + '\t.\t' + otherID + '\t0proband\t4husband\t.\t7other\t' + str(sample2Gender[
                                                                                                                                                                          probandID]) + '\t2\t.\t' + str(
                                sample2Gender[otherID]) + '\t' + str(sample2status[probandID]) + '\t' + str(sample2status[husbandID]) + '\t.\t' + str(sample2status[otherID]) + '\t' + \
                                       str(fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(family2hospitalSampleID[familyID]) + '\n'
                    # 先证者+父+wife/husband/sib/kid/other
                    elif '1dad' in pedigree[familyID][proband]:
                        for i in rank4List:
                            if i in relationList:
                                rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + dadID + '\t.\t' + str(pedigree[familyID][proband][i]) + '\t0proband\t1dad\t.\t' + i + '\t' + str(
                                    sample2Gender[
                                        probandID]) + '\t1\t.\t' + str(sample2Gender[pedigree[familyID][proband][i]]) + '\t' + str(sample2status[probandID]) + '\t' + str(
                                    sample2status[dadID]) + '\t.\t' + str(sample2status[pedigree[familyID][proband][i]]) + '\t' + str(fam2phenotype[familyID]) + '\t' + str(
                                    family2hospital[familyID]) + '\t' + \
                                           str(family2hospitalSampleID[familyID]) + '\n'
                    # 先证者+母+wife/husband/sib/kid/other
                    elif '2mom' in pedigree[familyID][proband]:
                        for i in rank4List:
                            if i in relationList:
                                rankItem = familyID + '_' + probandID + '\t' + probandID + '\t.\t' + momID + '\t' + str(pedigree[familyID][proband][i]) + '\t0proband\t.\t2mom\t' + i + '\t' + str(
                                    sample2Gender[
                                        probandID]) + '\t.\t2\t' + str(sample2Gender[pedigree[familyID][proband][i]]) + '\t' + str(sample2status[probandID]) + '\t.\t' + str(
                                    sample2status[momID]) + '\t' + str(sample2status[
                                                                           pedigree[familyID][proband][i]]) + '\t' + str(fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(
                                    family2hospitalSampleID[familyID]) + '\n'
                    # 先证者+子女+sib/other
                    elif '6kid' in pedigree[familyID][proband]:
                        if '5sib' in pedigree[familyID][proband]:
                            rankItem = familyID + '_' + probandID + '\t' + probandID + '\t.\t' + kidID + '\t' + sibID + '\t0proband\t.\t6kid\t5sib\t' + str(sample2Gender[probandID]) + '\t.\t' + \
                                       str(sample2Gender[pedigree[familyID][proband]['6kid']]) + '\t' + str(sample2Gender[sibID]) + '\t' + str(sample2status[probandID]) + '\t.\t' + str(
                                sample2status[kidID]) + '\t' + \
                                       str(sample2status[sibID]) + '\t' + str(fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(family2hospitalSampleID[familyID]) + '\n'
                        elif '7other' in pedigree[familyID][proband]:
                            rankItem = familyID + '_' + probandID + '\t' + probandID + '\t.\t' + kidID + '\t' + otherID + '\t0proband\t.\t6kid\t7other\t' + str(sample2Gender[probandID]) + '\t.\t' + \
                                       str(sample2Gender[pedigree[familyID][proband]['6kid']]) + '\t' + str(sample2Gender[otherID]) + '\t' + str(sample2status[probandID]) + '\t.\t' + str(
                                sample2status[kidID]) + '\t' + \
                                       str(sample2status[otherID]) + '\t' + str(fam2phenotype[familyID]) + '\t' + str(family2hospital[familyID]) + '\t' + str(family2hospitalSampleID[familyID]) + '\n'
            elif sampleCount == 4:
                # 先证者+父+母+sib/kid/other
                if '0proband' in pedigree[familyID][proband] and '1dad' in pedigree[familyID][proband] and '2mom' in pedigree[familyID][proband]:
                    for i in rank4List:
                        if i in relationList:
                            rankItem = familyID + '_' + probandID + '\t' + probandID + '\t' + dadID + '\t' + momID + '\t' + str(pedigree[familyID][proband][i]) + '\t0proband\t1dad\t2mom\t' + i + '\t' + \
                                       str(sample2Gender[probandID]) + '\t1\t2\t' + str(sample2Gender[pedigree[familyID][proband][i]]) + '\t' + str(sample2status[probandID]) + '\t' + str(
                                sample2status[dadID]) + '\t' + \
                                       str(sample2status[momID]) + '\t' + str(sample2status[pedigree[familyID][proband][i]]) + '\t' + str(fam2phenotype[familyID]) + '\t' + str(
                                family2hospital[familyID]) + '\t' + \
                                       str(family2hospitalSampleID[familyID]) + '\n'
            rankOutFile.write(
                'FamilyID\tProbandID\tDadID/SpouseID\tMomID/KidID\tOtherID\tProband\tDad/Spouse\tMom/Kid\tOther\tProbandGender\tDad/SpouseGender\tMom/KidGender\tOtherGender\tProbandStatus\tDad/SpouseStatus\tMom/KidStatus\tOtherStatus\tPhenotypeKeyWords\tHospital\tHospitalSampleID\n')
            rankOutFile.write(rankItem)
            batchRankFile.write(rankItem)
        rankOutFile.close()
        pedOutFile.close()
    batchPedFile.close()
    batchRankFile.close()
