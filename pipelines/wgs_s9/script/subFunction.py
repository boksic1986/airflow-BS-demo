#!/usr/bin/env python
# -*- coding:utf-8 _*-
"""
@author:Rzhang
@license: Apache Licence
@file: subFunction.py.py
@time: 2021/09/08
@contact: zhiangrian@126.com
@site:
@software: PyCharm
"""
import json
import sys
import argparse
import subprocess
import os
import datetime
from multiprocessing import Process, Manager
import math
import vcf
from pandas.core.frame import DataFrame
import pandas as pd
from sklearn.preprocessing import StandardScaler
import shutil
import re
import pysam
from pysam import VariantFile


def lumpy_vcf_rank(inputvcf, sortvcf):
    myvcf = vcf.Reader(open(inputvcf, 'r'))
    recordDict = {}
    for record in myvcf:
        indexs = []
        CHROM = record.CHROM
        POS = record.POS
        REF = record.REF
        ALT = str(record.ALT)
        SVTYPE = record.INFO['SVTYPE']
        ID = record.ID
        QUAL = float(record.QUAL)
        DP = int(record.samples[0]['DP'])
        QD = float(QUAL / DP)
        GT = str(record.samples[0]['GT'])
        AB = float(record.samples[0]['AB'])
        AS = int(record.samples[0]['AS'])
        ASC = int(record.samples[0]['ASC'])
        AP = int(record.samples[0]['AP'])
        Alt = math.log(int(AS + ASC + AP), math.e)
        indexs = [CHROM, POS, REF, ALT, SVTYPE, QUAL, DP, GT, AB, AS, ASC, AP, Alt, QD]
        recordDict[ID] = indexs
    # vcf record convert to dataFrame
    df = pd.DataFrame(recordDict).T.apply(pd.to_numeric, errors = 'ignore')
    df.columns = ['CHROM', 'POS', 'REF', 'ALT', 'SVTYPE', 'QUAL', 'DP', 'GT', 'AB', 'AS', 'ASC', 'AP', 'Alt', 'QD']
    df = df.reset_index().rename(columns = {'index': 'id'})
    # add column for sorting
    ss = StandardScaler()
    AAAscale_features = ['Alt']
    AAA_zscore = ss.fit_transform(df[AAAscale_features])
    df['AAAzscore'] = AAA_zscore

    scale_features = ['QD']
    QD_zscore = ss.fit_transform(df[scale_features])
    df['QDzcore'] = QD_zscore

    # GT&AB sort
    het_subdata = df[df['GT'] == '0/1']
    hom_subdata = df[df['GT'] == '1/1']

    het_min = het_subdata.describe()['AB']['min']
    het_quarter25 = het_subdata.describe()['AB']['25%']
    het_median = het_subdata.describe()['AB']['50%']
    het_quarter75 = het_subdata.describe()['AB']['75%']
    het_max = het_subdata.describe()['AB']['max']

    hom_min = hom_subdata.describe()['AB']['min']
    hom_quarter25 = hom_subdata.describe()['AB']['25%']
    hom_median = hom_subdata.describe()['AB']['50%']
    hom_quarter75 = hom_subdata.describe()['AB']['75%']
    hom_max = hom_subdata.describe()['AB']['max']

    df['GT_AB_score'] = 0
    df['sumScore'] = 0
    df['id_index'] = ''
    for i in range(0, len(df)):
        if (df.loc[i, 'GT'] == '1/1'):
            if (df.loc[i, 'AB'] >= hom_quarter75):
                df.loc[i, 'GT_AB_score'] = 5
            elif (df.loc[i, 'AB'] < hom_quarter75 and df.loc[i, 'AB'] >= hom_median):
                df.loc[i, 'GT_AB_score'] = 4
            elif (df.loc[i, 'AB'] < hom_median and df.loc[i, 'AB'] >= hom_quarter25):
                df.loc[i, 'GT_AB_score'] = 3
            else:
                df.loc[i, 'GT_AB_score'] = 2
        else:
            if (df.loc[i, 'AB'] >= het_quarter75):
                df.loc[i, 'GT_AB_score'] = 5
            elif (df.loc[i, 'AB'] < het_quarter75 and df.loc[i, 'AB'] >= het_median):
                df.loc[i, 'GT_AB_score'] = 4
            elif (df.loc[i, 'AB'] < het_median and df.loc[i, 'AB'] >= het_quarter25):
                df.loc[i, 'GT_AB_score'] = 3
            else:
                df.loc[i, 'GT_AB_score'] = 2
        df.loc[i, 'id_index'] = df.loc[i, 'id'].split('_')[0]
    df['sumScore'] = df['AAAzscore'] + df['QDzcore'] + df['GT_AB_score']
    df_sort = df.sort_values(by = ['sumScore', 'id_index'], ascending = (False, True))
    # df_sort.to_csv("sortlog.txt", sep='\t', index=False)

    outlist = {}
    newReader = vcf.Reader(open(inputvcf, 'r'))
    vcf_W = vcf.Writer(open(sortvcf, 'w'), newReader)
    idlist = list(df_sort["id"])
    for record in newReader:
        ID = record.ID
        p = idlist.index(ID)
        outlist[p] = record
    for i in range(0, len(outlist)):
        vcf_W.write_record(outlist[i])
    vcf_W.close()


def manta_vcf_rank(inputvcf, sortvcf):
    # read record from vcf file
    myvcf = vcf.Reader(open(inputvcf, 'r'))
    recordDict = {}
    for record in myvcf:
        indexs = []
        CHROM = record.CHROM
        POS = record.POS
        REF = record.REF
        ALT = str(record.ALT)
        SVTYPE = record.INFO['SVTYPE']
        ID = record.ID
        QUAL = float(record.QUAL)
        # AB=float(record.samples[0]['AB']) manta not include this column
        if 'PR' in record.FORMAT.split(':'):
            PR = int(record.samples[0]['PR'][1])
        indexs = [CHROM, POS, REF, ALT, SVTYPE, QUAL, PR]
        recordDict[ID] = indexs
    # vcf record convert to dataFrame
    df = pd.DataFrame(recordDict).T.apply(pd.to_numeric, errors = 'ignore')
    df.columns = ['CHROM', 'POS', 'REF', 'ALT', 'SVTYPE', 'QUAL', 'PR']
    df = df.reset_index().rename(columns = {'index': 'id'})
    # add column for sorting
    ss = StandardScaler()
    AAAscale_features = ['QUAL']
    AAA_zscore = ss.fit_transform(df[AAAscale_features])
    df['QUALzscore'] = AAA_zscore

    scale_features = ['PR']
    QD_zscore = ss.fit_transform(df[scale_features])
    df['PRzcore'] = QD_zscore
    for i in range(0, len(df)):
        df.loc[i, 'id_index'] = df.loc[i, 'id'][0:-2]
    df['sumScore'] = df['QUALzscore'] + df['PRzcore']
    df_sort = df.sort_values(by = ['sumScore', 'id_index'], ascending = (False, True))
    # df_sort.to_csv("sortlog.txt", sep='\t', index=False)

    outlist = {}
    newReader = vcf.Reader(open(inputvcf, 'r'))
    vcf_W = vcf.Writer(open(sortvcf, 'w'), newReader)
    idlist = list(df_sort["id"])
    for record in newReader:
        ID = record.ID
        p = idlist.index(ID)
        outlist[p] = record
    for i in range(0, len(outlist)):
        vcf_W.write_record(outlist[i])
    vcf_W.close()


def readvcfrank(RankVcfFile):
    IDRankDict = {}
    POSrankDict = {}
    i = 1
    with open(RankVcfFile, 'rb') as fp:
        for line in fp:
            line = line.decode('utf-8')
            line = line.strip('\r\n')
            if line.startswith('##'):
                pass
            elif line.startswith('#CHROM'):
                line = line.strip('\n')
                arhead = line.split('\t')
                idindex = arhead.index('ID')
                chromeindex = arhead.index('#CHROM')
                posindex = arhead.index('POS')
            else:
                listinfo = line.split('\t')
                ID = listinfo[idindex]
                chrome = listinfo[chromeindex]
                pos = listinfo[posindex]
                POS = chrome + "_" + pos
                IDRankDict[ID] = i
                POSrankDict[POS] = i
                i = i + 1
    return IDRankDict, POSrankDict


def mergeResult_rank(mergevcf, lumpysortvcf, mantasortvcf, outvcf):
    myvcf = vcf.Reader(open(mergevcf, 'r'))
    recordDict = {}
    for record in myvcf:
        indexs = []
        CHROM = record.CHROM
        POS = record.POS
        REF = record.REF
        ALT = str(record.ALT)
        ID = record.ID
        QUAL = float(record.QUAL)
        suppCount = int(record.INFO['SUPP'])
        GT_manta = str(record.samples[0]['GT'])
        mantaID = str(record.samples[0]['ID'])
        mantaCO = str(record.samples[0]['CO'])
        GT_lumpy = str(record.samples[1]['GT'])
        lumpy_ID = str(record.samples[1]['ID'])
        lumpyCO = str(record.samples[1]['CO'])
        indexs = [CHROM, POS, REF, ALT, ID, QUAL, suppCount, GT_manta, mantaID, mantaCO, GT_lumpy, lumpy_ID, lumpyCO]
        recordDict[ID] = indexs
    df = pd.DataFrame(recordDict).T.apply(pd.to_numeric, errors = 'ignore')
    df.columns = ['CHROM', 'POS', 'REF', 'ALT', 'ID', 'QUAL', 'suppCount', 'GT_manta', 'mantaID', 'mantaCO', 'GT_lumpy', 'lumpy_ID', 'lumpyCO']
    df = df.reset_index().rename(columns = {'index': 'id'})

    lumpyIDdict, lumpyPosdict = readvcfrank(lumpysortvcf)
    mantaIDdict, mantaPosdict = readvcfrank(mantasortvcf)

    df['Order'] = ''
    df['class'] = ''
    for i in range(0, len(df)):
        Order = ""
        Class = ''
        orderlist = []
        # print(i)
        if (df.loc[i, 'suppCount'] == 2):
            if (df.loc[i, 'id'].startswith("Manta")):
                idOrder = lumpyIDdict[df.loc[i, 'lumpy_ID']]
                lumpypos = df.loc[i, 'lumpyCO']
                orderlist.append(idOrder)
                for j in lumpypos.split(','):
                    orderlist.append(lumpyPosdict[j.split('-')[0]])
                Order = min(orderlist)
            else:
                idOrder = lumpyIDdict[df.loc[i, 'id']]
                pos = df.loc[i, 'CHROM'] + "_" + str(df.loc[i, 'POS'])
                posOrder = lumpyPosdict[pos]
                Order = min(idOrder, posOrder)
            # Order="1_Lumpy_Two_"+str(Order)
            Class = '1'
        else:
            if (df.loc[i, 'id'].startswith("Manta")):
                idOrder = mantaIDdict[df.loc[i, 'id']]
                pos = df.loc[i, 'CHROM'] + "_" + str(df.loc[i, 'POS'])
                posOrder = mantaPosdict[pos]
                Order = min(idOrder, posOrder)
                # Order="3_Manta_One_"+str(Order)
                Class = '3'
            else:
                idOrder = lumpyIDdict[df.loc[i, 'id']]
                pos = df.loc[i, 'CHROM'] + "_" + str(df.loc[i, 'POS'])
                posOrder = lumpyPosdict[pos]
                Order = min(idOrder, posOrder)
                # Order="2_Lumpy_One_"+str(Order)
                Class = '2'
        df.loc[i, 'class'] = Class
        df.loc[i, 'Order'] = Order
    df_sort = df.sort_values(by = ['class', 'Order'], ascending = (True, True))
    # df_sort.to_csv("sortlog.txt", sep='\t', index=False)

    outlist = {}
    newReader = vcf.Reader(open(mergevcf, 'r'))
    vcf_W = vcf.Writer(open(outvcf, 'w'), newReader)
    idlist = list(df_sort["id"])
    for record in newReader:
        ID = record.ID
        p = idlist.index(ID)
        outlist[p] = record
    for i in range(0, len(outlist)):
        vcf_W.write_record(outlist[i])
    vcf_W.close()


def read_rankVcf(rankvcf):
    rankdict = {}
    i = 1
    with open(rankvcf, 'rb') as fp:
        for line in fp:
            line = line.decode('utf-8')
            line = line.strip('\r\n')
            if line.startswith('##'):
                pass
            elif line.startswith('#CHROM'):
                line = line.strip('\n')
                arhead = line.split('\t')
                idindex = arhead.index('ID')
            else:
                listinfo = line.split('\t')
                rankdict[i] = listinfo[idindex]
                i = i + 1
    return rankdict


def SV_filter(annotSVfile, geneLoF, Blacklist, Repeat):
    temporarylist = []
    temporaryID = ""
    deleteID = []
    wholeID = []
    outlist = []
    keepList = []
    with open(annotSVfile, 'rb') as fp:
        for line in fp:
            finalList = ""
            flag = 0
            line = line.decode('utf-8')
            line = line.strip('\r\n')
            if line.startswith('AnnotSV_ID'):
                head = line
                line = line.strip('\n')
                arhead = line.split('\t')
                SV_type = arhead.index('SV_type')
                IDindex = arhead.index('ID')
                modeindex = arhead.index('Annotation_mode')
                Gene_name = arhead.index('Gene_name')
                gene_Count = arhead.index('Gene_count')
                ENCODE_blacklist_left = arhead.index('ENCODE_blacklist_left')
                ENCODE_blacklist_right = arhead.index('ENCODE_blacklist_right')
                Repeat_coord_left = arhead.index('Repeat_coord_left')
                Repeat_coord_right = arhead.index('Repeat_coord_right')
            else:
                arvar = line.split('\t')
                SVtype = arvar[SV_type]
                ID = arvar[IDindex]
                gene = arvar[Gene_name]
                geneCount = int(arvar[gene_Count]) if arvar[gene_Count] != '' else 1
                Annotation_mode = arvar[modeindex]
                encodeLeft = arvar[ENCODE_blacklist_left]
                encodeRight = arvar[ENCODE_blacklist_right]
                repeatleft = arvar[Repeat_coord_left]
                repeatright = arvar[Repeat_coord_right]
                wholeID.append(ID)

                if Annotation_mode == "full" and geneCount == 1:
                    temporarylist = arvar
                    temporaryID = ID
                elif Annotation_mode == "split" and temporaryID != "":
                    for i in range(0, len(temporarylist)):
                        temporarylist[i] = temporarylist[i] if temporarylist[i] != "" else arvar[i]
                    finalList = '\t'.join(temporarylist)
                    temporarylist = []
                    temporaryID = ""
                elif Annotation_mode == "full" and geneCount == 0:
                    finalList = line
                elif Annotation_mode == "full" and geneCount > 1:
                    finalList = line
                else:
                    finalList = line
                if finalList != "":
                    outlist.append(finalList)
                if geneLoF == "ON":
                    if geneCount == 0:
                        deleteID.append(ID)
                if Blacklist == "ON":
                    if encodeLeft != "" or encodeRight != "":
                        deleteID.append(ID)
                        deleteID.append(ID.replace("_1", "_2"))
                        deleteID.append(ID.replace("_2", "_1"))
                        deleteID.append(ID[::-1].replace('0', '1', 1)[::-1])
                        deleteID.append(ID[::-1].replace('1', '0', 1)[::-1])
                if Repeat == "ON":
                    if repeatleft != "" or repeatright != "":
                        deleteID.append(ID)
                        deleteID.append(ID.replace("_1", "_2"))
                        deleteID.append(ID.replace("_2", "_1"))
                        deleteID.append(ID[::-1].replace('0', '1', 1)[::-1])
                        deleteID.append(ID[::-1].replace('1', '0', 1)[::-1])
    deleteID = list(set(deleteID))
    # print(deleteID)
    for i in outlist:
        svtype = i.split('\t')[5]
        recordID = i.split('\t')[7]
        if svtype == "INV":
            if recordID not in deleteID:
                keepList.append(i)

        if svtype == "TRA":
            if '_' in recordID:
                recordID_index = recordID.split('_')[0]
                recordID1 = recordID_index + "_1"
                recordID2 = recordID_index + "_2"
                if (recordID1 not in deleteID) or (recordID2 not in deleteID):
                    keepList.append(i)
            elif 'Manta' in recordID:
                idlist = recordID.split(':')
                recordID1 = ':'.join(idlist[0:len(idlist) - 1]) + ":0"
                recordID2 = ':'.join(idlist[0:len(idlist) - 1]) + ":1"
                if recordID1 in wholeID and recordID2 in wholeID:
                    if (recordID1 not in deleteID) or (recordID2 not in deleteID):
                        keepList.append(i)
                else:
                    if recordID not in deleteID:
                        keepList.append(i)
            else:
                if recordID not in deleteID:
                    keepList.append(i)
    return keepList, head


def annot_filter(AnnotSVresult, inputvcf, geneLOF, blacklist, repeat, outresult):
    SVannotationFile = AnnotSVresult
    f2 = open(outresult, 'w')
    VcfrankDict = read_rankVcf(inputvcf)
    KeepList, Head = SV_filter(SVannotationFile, geneLOF, blacklist, repeat)
    f2.write(Head + "\n")
    for i in range(1, len(VcfrankDict) + 1):
        vcfID = VcfrankDict[i]
        for j in KeepList:
            iD = j.split('\t')[7]
            if vcfID == iD:
                f2.write(j + "\n")
    f2.close()


def appendAPI(file, Errorstring):
    outfile = open(file, 'a')
    outfile.write(Errorstring + "\n")
    outfile.close()


def removeTempFolder(tempFolderPath):
    shutil.rmtree(tempFolderPath)


def imprintRegion(inputfile, outfile):
    imprintRegion = ["6q24.2", "7q32.2", "11p15", "14q32.2", "15q11.2", "15q12", "15q13.1", "15q13.2", "15q13.3", "20q11.1", "20q11.21", "20q11.22", "20q11.23", "20q12", "20q13.11", "20q13.12",
                     "20q13.13", "20q13.2", "20q13.31", "20q13.32", "20q13.33"]
    f2 = open(outfile, 'w')
    with open(inputfile, 'rb') as fp:
        for line in fp:
            line = line.decode('utf-8')
            line = line.strip('\r\n')
            arhead = line.split('\t')
            cytobandlist = []
            chr = arhead[0].replace("chr", "")
            cytoband = arhead[6]
            if "," in cytoband:
                cytobandlist = cytoband.split(",")
                chrlist = [chr for x in range(0, len(cytobandlist))]
                newlist = list(map(Areplace, chrlist, cytobandlist))
                interlist = sorted(list(set(newlist).intersection(set(imprintRegion))))
                newcytoband = cytobandlist[0] + "-" + cytobandlist[-1]

            else:
                cytobandlist.append(cytoband)
                chrlist = [chr for x in range(0, len(cytobandlist))]
                newlist = list(map(Areplace, chrlist, cytobandlist))
                interlist = list(set(newlist).intersection(set(imprintRegion)))
                newcytoband = cytoband
            if (len(interlist) > 0):
                f2.write("\t".join(arhead[0:6]) + "\t" + newcytoband + '\t' + ','.join(interlist) + '\n')
            else:
                f2.write("\t".join(arhead[0:6]) + "\t" + newcytoband + '\t' + "NO" + '\n')
    f2.close()


def Areplace(str, old):
    return str + old


def readfastpJson(inputlist, indir, suffix, outfile):
    f2 = open(outfile, 'w')
    # filenames = os.listdir(indir)
    filenames = inputlist
    for i in filenames:
        if i.endswith(suffix):
            sampleName = i.replace(".template.json", "").replace('07_QC/', '')
            i = indir + '/' + i
            with open(i, 'r')as fp:
                d = json.load(fp)
                read1_total_reads = d["read1_before_filtering"]["total_reads"]
                read1_total_bases = d["read1_before_filtering"]["total_bases"]
                read1_q20_bases = d["read1_before_filtering"]["q20_bases"]
                read1_q30_bases = d["read1_before_filtering"]["q30_bases"]
                read1_Q20 = round(read1_q20_bases / read1_total_bases * 100, 3)
                read1_Q30 = round(read1_q30_bases / read1_total_bases * 100, 3)

                read2_total_reads = d["read2_before_filtering"]["total_reads"]
                read2_total_bases = d["read2_before_filtering"]["total_bases"]
                read2_q20_bases = d["read2_before_filtering"]["q20_bases"]
                read2_q30_bases = d["read2_before_filtering"]["q30_bases"]
                read2_Q20 = round(read2_q20_bases / read2_total_bases * 100, 3)
                read2_Q30 = round(read2_q30_bases / read2_total_bases * 100, 3)
                read1Name = sampleName + "-R1.fq.gz"
                read2Name = sampleName + "-R2.fq.gz"
                print(d["summary"]["before_filtering"])
                if 'read1_mean_length' not in d["summary"]["before_filtering"]:
                    read1_mean_length = '150'
                    read2_mean_length = '150'
                else:
                    read1_mean_length = d["summary"]["before_filtering"]["read1_mean_length"]
                    read2_mean_length = d["summary"]["before_filtering"]["read2_mean_length"]
                f2.write(read1Name + "\t" + str(read1_total_reads) + "\t" + str(read1_total_bases) + "\t" + str(read1_mean_length) + "\t" + str(read1_Q20) + "\t" + str(read1_Q30) + "\n")
                f2.write(read2Name + "\t" + str(read2_total_reads) + "\t" + str(read2_total_bases) + "\t" + str(read2_mean_length) + "\t" + str(read2_Q20) + "\t" + str(read2_Q30) + "\n")
    f2.close()


def adjust_SVformat(inputfile, outfile):
    f2 = open(outfile, 'w')
    with open(inputfile, 'rb') as fp:
        for line in fp:
            line = line.decode('utf-8')
            line = line.strip('\r\n')
            if line.startswith('##'):
                pass
            elif line.startswith('#CHROM'):
                line = line.strip('\n')
                arhead = line.split('\t')
                idindex = arhead.index('ID')
            else:
                listinfo = line.split('\t')
                i = i + 1
    f2.close()


def getIDgroup(inputbamfile):
    cSample = ''
    cReadGroupID = ''
    cRead = ''
    bamfile = pysam.AlignmentFile(inputbamfile, "rb")
    if 'SM' in bamfile.header['RG'][0]:
        cSample = bamfile.header['RG'][0]['SM']
    if 'ID' in bamfile.header['RG'][0]:
        cReadGroupID = str(bamfile.header['RG'][0]['ID'])
    if 'LB' in bamfile.header['RG'][0]:
        cRead = bamfile.header['RG'][0]['LB']
    return cSample, cReadGroupID, cRead


def mergeBed_Vcf(inputvcf, gnomadBed, dbvarBed, decipherbed, outVcf):
    vcf2 = VariantFile(inputvcf, "r")
    comm = '##FILTER=<ID=PASS,Description="Variant passing in at least one of the samples, see FT">'
    command = '##INFO=<ID=gnomad_ov_id,Number=1,Type=String,Description="gnomad variant ID from gnomad_v2.1_sv.sites.bed.gz file">'
    command2 = '##INFO=<ID=gnomad_ac,Number=1,Type=String,Description="Population variant allele count from gnomad v2.1 sv">'
    command3 = '##INFO=<ID=gnomad_af,Number=1,Type=String,Description="Population variant allele frequency from gnomad v2.1 sv">'
    command4 = '##INFO=<ID=dbvar_ov_id,Number=1,Type=String,Description="dbvar variant ID with overlap more than 70%">'
    command5 = '##INFO=<ID=decipher_ov_id,Number=1,Type=String,Description="decipher variant ID with overlap more than 70%">'
    vcf2.header.add_line(comm)
    vcf2.header.add_line(command)
    vcf2.header.add_line(command2)
    vcf2.header.add_line(command3)
    vcf2.header.add_line(command4)
    vcf2.header.add_line(command5)
    # print(vcf2.header)
    # vcf_out = VariantFile(outVcf, "w", header = vcf2.header)
    vcf_out = open(outVcf, "w")
    vcf_out.write(str(vcf2.header))
    gnomeAD_dict = {}
    dbvar_dict = {}
    decipher_dict = {}
    with open(gnomadBed, 'rb') as fp:
        for line in fp:
            line = line.decode('utf-8')
            line = line.strip('\r\n')
            linelist = line.split('\t')
            varintID = '+'.join(linelist[1].split('+')[0:4])
            gnomadID = linelist[2]
            gnomadAC = linelist[4]
            gnomadAF = linelist[5]
            gnomeAD_dict[varintID] = gnomadID + '\t' + gnomadAC + '\t' + gnomadAF
    with open(dbvarBed, 'rb') as fp:
        for line in fp:
            line = line.decode('utf-8')
            line = line.strip('\r\n')
            linelist = line.split('\t')
            varintID = '+'.join(linelist[1].split('+')[0:4])
            ID = linelist[2]
            dbvar_dict[varintID] = ID
    with open(decipherbed, 'rb') as fp:
        for line in fp:
            line = line.decode('utf-8')
            line = line.strip('\r\n')
            linelist = line.split('\t')
            varintID = '+'.join(linelist[1].split('+')[0:4])
            ID = linelist[2]
            decipher_dict[varintID] = ID
    for rec in vcf2.fetch():
        chrome = rec.chrom
        start = int(rec.start) + 1
        info = rec.info
        end = int(rec.stop)
        type = info["SVTYPE"]
        if 'LOCATION' in info:
            location = info["LOCATION"]
            if len(location) == 1 and '-' in location[0]:
                newend = int(location[0].split('-')[1])
                if newend != end:
                    end = newend
        # print(str(start) + ' ' + str(end))
        if start == end and type == 'BND':
            end = '.'
        id = str(rec.id)
        # gt=info["GT"]
        vcfid = chrome + '+' + str(start) + '+' + str(end) + '+' + type
        # print(vcfid)
        if vcfid in gnomeAD_dict:
            infolist = gnomeAD_dict[vcfid].split('\t')
            gnomAD_id = infolist[0]
            gnomAD_ac = infolist[1]
            gnomAD_af = infolist[2]
            rec.info['gnomad_ov_id'] = gnomAD_id
            rec.info['gnomad_ac'] = gnomAD_ac
            rec.info['gnomad_af'] = gnomAD_af

        if vcfid in dbvar_dict:
            dbvarID = dbvar_dict[vcfid]
            rec.info['dbvar_ov_id'] = dbvarID
        if vcfid in decipher_dict:
            decipherID = decipher_dict[vcfid]
            rec.info['decipher_ov_id'] = decipherID
        # print(rec)
        vcf_out.write(str(rec))

    vcf_out.close()


def SVvcf2bed(inputvcf, outbed, sample):
    import pysam
    vcf_file = inputvcf
    vcf_index = vcf_file + '.tbi'
    vcf2 = pysam.TabixFile(vcf_file, "r", None, vcf_index)
    f2 = open(outbed, 'w')
    f2.write("chrom\tloc.start\tloc.end\tType\tlength\tCopyNumber\tID\tTools\n")
    bed_list = []
    vcf_list = []
    chromosomes = [str(x) for x in range(1, 23)] + ['X', 'Y', 'MT']
    for chrom in chromosomes:
        CNV = []
        stored_CNVs = []
        if chrom in vcf2.contigs:
            for i in vcf2.fetch(chrom):
                i = i.split('\t')
                # print(i)
                infoDict = {}
                chrome = i[0]
                start = int(i[1])
                end = start + 1
                info = i[7]
                # print(info)
                infolist = info.split(";")
                for j in infolist:
                    if '=' in j:
                        name = j.split('=')[0]
                        value = j.split('=')[1]
                    else:
                        name = j
                        value = j
                    infoDict[name] = value
                if 'END' in infoDict:
                    end = int(infoDict['END'])
                if 'SVTYPE' in infoDict:
                    svtype = infoDict['SVTYPE']
                if 'TOOL' in infoDict:
                    tools = infoDict['TOOL']
                if (svtype == "DUP" or svtype == "DEL"):
                    if (isinstance(tools, tuple)):
                        tool = ";".join(list(tools))
                    else:
                        tool = tools
                    newRecord = [chrome, start, end, svtype, tool]
                    CNV.append(newRecord)
        CNV.sort(key = lambda x: (x[1], x[2]))
        # print(CNV)
        for stored_CNV in CNV:
            length = int(stored_CNV[2]) - int(stored_CNV[1])
            out = stored_CNV[0] + '\t' + str(stored_CNV[1]) + '\t' + str(stored_CNV[2]) + '\t' + stored_CNV[3] + '\t' + str(length) + '\t \t' + sample + '\t' + stored_CNV[4] + '\n'
            f2.write(out)
    f2.close()

# mergeBed_Vcf("/bi/6.zhangran/toolsTest/merge_CNV/WGS21060009-WGS.MQ20.OpreProc.f1.lumpy_manta.DGV.GC.SEGD.KDB.1kG.ENS.qsCNV.vcf", "/bi/6.zhangran/toolsTest/merge_CNV/WGS21060009.SV.gnomad.0.7.overlap.same.bed","/bi/6.zhangran/toolsTest/merge_CNV/WGS21060009.SV.dbvar.0.7.overlap.same.bed","/bi/6.zhangran/toolsTest/merge_CNV/WGS21060009.SV.decipher.0.7.overlap.same.bed","/bi/6.zhangran/toolsTest/merge_CNV/new3.vcf")
