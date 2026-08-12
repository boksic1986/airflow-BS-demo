#!/usr/bin/env python  
# -*- coding:utf-8 _*-
""" 
@author:Rzhang 
@license: Apache Licence 
@file: 6.MT_QC.py
@time: 2023/12/19
@contact: zhiangrian@126.com
@site:  
@software: PyCharm 
"""
import argparse
import os


def readCoverage(coverageFile):
    rawReads = rawData = rawbases = mappedReads = mappedReadsrate = pcrdupRate = targetReads = targetReadsRate = meanDepth = 0
    with open(coverageFile, 'r') as coverage:
        for line in coverage:
            if line.startswith('##'):
                pass
            else:
                title, value = line.strip().split('\t')[0:2]
                # print(title, value)
                if title == '[Total] Raw Reads (All reads)':
                    rawReads = value
                    rawbases = int(rawReads) * 150
                elif title == '[Total] Raw Data(Mb)':
                    rawData = value
                elif title == '[Total] Mapped Reads':
                    mappedReads = value
                elif title == '[Total] Fraction of Mapped Reads':
                    mappedReadsrate = value
                elif title == '[Total] Fraction of PCR duplicate reads':
                    pcrdupRate = value
                elif title == '[Target] Target Reads':
                    targetReads = value
                elif title == '[Target] Fraction of Target Reads in all reads':
                    targetReadsRate = value
                elif title == '[Target] Average depth':
                    meanDepth = value
    return rawReads, rawData, rawbases, mappedReads, mappedReadsrate, pcrdupRate, targetReads, targetReadsRate, meanDepth


def readInsert(insertSizeFile):
    num_ins100 = num_ins150 = num_ins200 = num_ins250 = num_ins300 = num_ins400 = num_ins500 = num_insmax = total = 0
    fraction_of_insert100 = fraction_of_insert150 = fraction_of_insert200 = fraction_of_insert250 = fraction_of_insert300 = fraction_of_insert400 = fraction_of_insert500 = fraction_of_insertmax = 0
    with open(insertSizeFile, 'r') as insert_file:
        for line in insert_file:
            size, num = line.strip().split('\t')[0:2]
            total += int(num)
            size = int(size)
            if size <= 100:
                num_ins100 += int(num)
            elif 100 < size <= 150:
                num_ins150 += int(num)
            elif 150 < size <= 200:
                num_ins200 += int(num)
            elif 200 < size <= 250:
                num_ins250 += int(num)
            elif 250 < size <= 300:
                num_ins300 += int(num)
            elif 300 < size <= 400:
                num_ins400 += int(num)
            elif 400 < size <= 500:
                num_ins500 += int(num)
            elif size > 500:
                num_insmax += int(num)

    fraction_of_insert100 = round(num_ins100 / total * 100, 2)
    fraction_of_insert150 = round(num_ins150 / total * 100, 2)
    fraction_of_insert200 = round(num_ins200 / total * 100, 2)
    fraction_of_insert250 = round(num_ins250 / total * 100, 2)
    fraction_of_insert300 = round(num_ins300 / total * 100, 2)
    fraction_of_insert400 = round(num_ins400 / total * 100, 2)
    fraction_of_insert500 = round(num_ins500 / total * 100, 2)
    fraction_of_insertmax = round(num_insmax / total * 100, 2)

    return fraction_of_insert100, fraction_of_insert150, fraction_of_insert200, fraction_of_insert250, fraction_of_insert300, fraction_of_insert400, fraction_of_insert500, fraction_of_insertmax


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'CNV bed file annotation ')
    parser.add_argument("-I", '--inputPath', type = str, required = True, default = "07_QC/MT", help = 'input file path')
    parser.add_argument("-O", '--output', type = str, default = "test.tsv", required = True, help = 'output file path')
    parser.add_argument("-s", '--sample', type = str, required = True, help = 'sample id')
    args = parser.parse_args()
    bamdst_result_dir = args.inputPath
    sample = args.sample
    OutFile = open(args.output, 'w')
    OutFile.write(
        "Sample\tRaw_reads" + "\t" + "Raw Data(Mb)" + "\t" + "Raw_bases" + "\t" + "Mapped Reads" + "\t" + "Fraction of Mapped Reads" + "\t" + "Fraction of PCR duplicate" + "\t" + "<=100insert_Reads%" + "\t" + "(100,150]insert_Reads%" + "\t" + "(150,200]insert_Reads%" + "\t" + "(200,250]insert_Reads%" + "\t" + "(250,300]insert_Reads%" + "\t" + "(300,400]insert_Reads%" + "\t(400,500]insert_Reads%\t>500insert_Reads%\t" + "Target Reads" + "\t" + "On_Target_Reads%" + "\t" + "Average depth" + "\n")
    insert_size_filename = bamdst_result_dir + '/' + sample + '/insertsize.plot'
    fraction_of_insert100, fraction_of_insert150, fraction_of_insert200, fraction_of_insert250, fraction_of_insert300, fraction_of_insert400, fraction_of_insert500, fraction_of_insertmax = readInsert(
        insert_size_filename)
    coverageFile = bamdst_result_dir + '/' + sample + '/coverage.report'
    rawReads, rawData, rawbases, mappedReads, mappedReadsrate, pcrdupRate, targetReads, targetReadsRate, meanDepth = readCoverage(coverageFile)
    OutFile.write(sample + '\t' + str(rawReads) + '\t' + str(rawData) + '\t' + str(rawbases) + '\t' + str(mappedReads) + '\t' + str(mappedReadsrate) + '\t' + str(pcrdupRate) + '\t' + str(
        fraction_of_insert100) + '%\t' + str(fraction_of_insert150) + '%\t' + str(fraction_of_insert200) + '%\t' + str(fraction_of_insert250) + '%\t' + str(fraction_of_insert300) + '%\t' + str(
        fraction_of_insert400) + '%\t' + str(fraction_of_insert500) + '%\t' + str(fraction_of_insertmax) + '%\t' + str(targetReads) + '\t' + str(targetReadsRate) + '\t' + str(meanDepth) + '\n')
    OutFile.close()
