#!/usr/bin/env python  
# -*- coding:utf-8 _*-
""" 
@author:Rzhang 
@license: Apache Licence 
@file: SV_annot_sort.py 
@time: 2023/08/17
@contact: zhiangrian@126.com
@site:  
@software: PyCharm 
 ### update@zhangran,20231215,新增gnomAD,PGGSV,遗传来源的注释,pLI注释,BND两个断点合并,调整注释结果格式
 ### update@zhangran,20231218,新增cytoband信息，过滤掉不在常规染色体中的变异
 ### update@zhangran,20260615,新增hg19坐标liftover
"""
import argparse
import subprocess
import string
from collections import defaultdict
from collections import OrderedDict
import pandas as pd
import os
import vcf
import re
import yaml
import tempfile

def fromArraytoStr(combinedlist):
    diseaseEN = ''
    diseaseCN = ''
    inhertanceType = ''
    for i in combinedlist:
        diseaseEN = diseaseEN + '; ' + i[2] + '(' + i[1] + ':' + i[0] + ')'
        diseaseCN = diseaseCN + '; ' + i[3] + '(' + i[1] + ':' + i[0] + ')'
        inhertanceType = inhertanceType + '; ' + i[1]
    diseaseEN = diseaseEN.lstrip('; ').replace('.(.:.)', '.')
    diseaseCN = diseaseCN.lstrip('; ').replace('.(.:.)', '.')
    inhertanceType = inhertanceType.lstrip('; ')
    return diseaseEN, diseaseCN, inhertanceType


def getVEPseverity(file):
    with open(file, 'r', encoding = "utf-8") as hfp:
        highList, moderateList, lowList, modifierList = [[] for i in range(4)]
        for term in hfp:
            line = term.strip('\r\n')
            linelist = line.split('\t')
            term = linelist[0].lower()
            impact = linelist[1]
            if impact == "HIGH":
                highList.append(term)
            elif impact == "MODERATE":
                moderateList.append(term)
            elif impact == "LOW":
                lowList.append(term)
            else:
                modifierList.append(term)
    return highList, moderateList, lowList, modifierList


def keyword_match(gene, hpolist, phenotypeHash):
    outInfo = ''
    count = 0
    if hpolist == '.':
        outInfo = ''
    else:
        for i in hpolist.split(','):
            if i in phenotypeHash:
                genelist = phenotypeHash[i]['genes'].split('|')
                translation = '.'
                if gene in genelist and gene != '.':
                    translation = phenotypeHash[i]['phenotype_CN']
                    outInfo = outInfo + '|' + gene + '[' + i + '(' + translation + ')]'
            else:
                print("#Warining: " + i + " is not in phenotype_key_word_gene_list.txt!")
        outInfo = outInfo.lstrip('|')
    count = 0 if outInfo == '' else len(outInfo.split('|'))
    return outInfo, count


def getGeneHITS(HIfile):
    gene2HITS = defaultdict(dict)
    with open(HIfile, "r") as hiFile:
        geneHITS = ['geneName', 'geneID', 'cytoBand', 'location', 'HIscore', 'TSscore']
        for line in hiFile:
            line = line.strip()
            arr = line.split("\t")
            h = dict(zip(geneHITS, arr))
            geneName = h['geneName']
            HIscore = h['HIscore']
            TSscore = h['TSscore']
            gene2HITS[geneName]['HI'] = HIscore
            gene2HITS[geneName]['TS'] = TSscore
    return gene2HITS


def getPGGSV(pggsvfile):
    pggSV = defaultdict(dict)
    with open(pggsvfile, "r") as svFile:
        pggsv = ['version', 'chr', 'svId', 'URL', 'start', 'end', 'svType', 'svSize', 'alleleCount', 'alleleFreq']
        for line in svFile:
            line = line.strip()
            arr = line.split("\t")
            h = dict(zip(pggsv, arr))
            CHR = h['chr']
            SVID = h['svId']
            URL = h['URL']
            START = h['start']
            END = h['end']
            SVtype = h['svType']
            SIZE = h['svSize']
            AC = h['alleleCount']
            AF = h['alleleFreq']
            ID = ''
            if SVtype == 'INS':
                ID = CHR + '-' + str(START) + '-' + str(SIZE) + '-INS'
            if SVtype == 'INV':
                ID = CHR + '-' + str(START) + '-' + str(END) + '-INV'
            pggSV[ID]['CHR'] = CHR
            pggSV[ID]['START'] = START
            pggSV[ID]['END'] = END
            pggSV[ID]['SVtype'] = SVtype
            pggSV[ID]['SVID'] = SVID
            pggSV[ID]['URL'] = URL
            pggSV[ID]['SIZE'] = SIZE
            pggSV[ID]['AC'] = AC
            pggSV[ID]['AF'] = AF
    return pggSV


def getLocalSample(localSVsample):
    LocalSampleInfo = defaultdict(dict)
    with open(localSVsample, "r") as localSample:
        localSamples = ['CHROM1', 'START1', 'END1', 'CHROM2', 'START2', 'END2', 'SVtype', 'Strand', 'SampleInfo']
        for line in localSample:
            line = line.strip()
            if 'CHROM1' in line:
                continue
            arr = line.split("\t")
            h = dict(zip(localSamples, arr))
            CHR1 = h['CHROM1']
            CHR2 = h['CHROM2']
            START = h['START1']
            END = h['END2']
            SVtype = h['SVtype']
            SVstrand = h['Strand']
            sample = h['SampleInfo']
            SIZE = 0
            if SVtype != 'BND':
                SIZE = int(h['END2']) - int(h['START1']) + 1
            svID = ''
            if SVtype == 'INS':
                svID = CHR1 + '_' + str(START) + '_' + str(SIZE) + '_INS' + '_' + SVstrand
            if SVtype == 'INV':
                svID = CHR1 + '_' + str(START) + '_' + str(END) + '_INV' + '_' + SVstrand
            if SVtype == 'BND':
                svID = CHR1 + '_' + str(START) + '_' + CHR2 + '_' + str(END) + '_BND' + '_' + SVstrand
            LocalSampleInfo[svID] = sample
    return LocalSampleInfo


def getLocalSV(localsvfile,inputfile,bedtools,localSVsample):
    LocalSampleInfo = getLocalSample(localSVsample)
    localSVtmp = inputfile.replace('vep.tsv', 'localSV.bed')
    quaryINVtmp = inputfile.replace('vep.tsv', 'quaryINV.bed')
    qINV = open(quaryINVtmp, 'w')
    quaryBNDtmp = inputfile.replace('vep.tsv', 'quaryBND.bed')
    qBND = open(quaryBNDtmp, 'w')
    VCF = open(inputfile, 'r')
    for line in VCF:
        line = line.strip()
        if not re.findall('^chr',line):
            continue
        # print(line)
        arr = line.split('\t')
        SVchr = arr[0]
        SVchr2 = SVchr
        SVstart = arr[1]
        SVstart2 = SVstart
        SVend = SVstart
        SVend2 = SVend
        SVtype = arr[7]
        SVlen = arr[8]
        if SVlen == ".":
            SVlen = 0
        if SVtype == 'INV':
            SVend = arr[9]
            SVend2 = SVend
        if SVtype == 'INS':
            SVend = int(SVstart) + int(SVlen) - 1
            SVend2 = SVend
        if SVtype in ['DUP','DEL', 'DUP:TANDEM']:
            continue
        if SVtype == 'BND' and re.findall('chr',arr[4]):
            results = re.findall(r'([0-9XYchr\.]+):(\d+)',arr[4])
            for result in results:
             SVchr2 = result[0]
             SVstart2 = result[1]
             SVend2 = result[1]
        elif SVtype == 'BND' and not re.findall('chr',arr[4]):
             continue
        if SVtype == 'BND':
            lostart = int(SVstart) - 50
            loend = int(SVend) + 51
            qBND.write( SVchr + "\t" + str(lostart) + "\t" + str(loend) + "\n")
        if SVtype == 'INV' or SVtype == 'INS':
            qINV.write( SVchr + "\t" + str(SVstart) + "\t" + str(int(SVend)+1) + "\n")
    qINV.close()
    qBND.close()
    localInfo = pd.read_csv(localsvfile, sep="\t", encoding="utf-8")
    localINVtemp = inputfile.replace('vep.tsv', 'localINV.bed')
    localInfo1 = localInfo[(localInfo['SVtype'] == 'INV') | (localInfo['SVtype'] == 'INS')]
    localInfo1['END1'] = localInfo1['END1'] + 1
    localInfo1.to_csv(localINVtemp, header=False, index=False, encoding='utf-8', sep="\t")
    localBNDtemp = inputfile.replace('vep.tsv', 'localBND.bed')
    localInfo2 = localInfo[localInfo['SVtype'] == 'BND']
    localInfo2['END1'] = localInfo2['END1'] + 1
    localInfo2.to_csv(localBNDtemp, header=False, index=False, encoding='utf-8', sep="\t")
    # BND
    cmd = f"{bedtools} intersect -a {quaryBNDtmp} -b {localBNDtemp} -wa -wb | {bedtools} overlap -i stdin -cols 2,3,5,6 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $18/($6-$5)==1' > {localSVtmp}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    # INV INS
    cmd = f"{bedtools} intersect -a {quaryINVtmp} -b {localINVtemp} -wa -wb | {bedtools} overlap -i stdin -cols 2,3,5,6 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $18/($3-$2+1)>=0.9 && $18/($6-$5+1)>=0.9' >> {localSVtmp}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    localSV = defaultdict(dict)
    with open(localSVtmp, "r") as svFile:
        localsv = ['CHROM', 'START', 'END', 'CHROM1', 'START1', 'END1', 'CHROM2', 'START2', 'END2', 'SVtype', 'FreqInfo', 'Strand', 'AN', 'AC', 'N_Het', 'N_Hom', 'N_HomRef', 'Overlap']
        for line in svFile:
            line = line.strip()
            # print(line)
            if 'CHROM1' in line:
                continue
            arr = line.split("\t")
            h = dict(zip(localsv, arr))
            CHR1 = h['CHROM1']
            CHR2 = h['CHROM2']
            START = h['START1']
            END = h['END2']
            SVtype = h['SVtype']
            SVstrand = h['Strand']
            AC = h['AC']
            AN = h['AN']
            AF = round(int(AC)/int(AN),6)
            SIZE = 0
            if SVtype != 'BND':
                SIZE = int(h['END2']) - int(h['START1']) + 1
            ID = ''
            if SVtype == 'INS':
                ID = CHR1 + '_' + str(START) + '_' + str(SIZE) + '_INS' + '_' + SVstrand
            if SVtype == 'INV':
                ID = CHR1 + '_' + str(START) + '_' + str(END) + '_INV' + '_' + SVstrand
            if SVtype == 'BND':
                ID = CHR1 + '_' + str(START) + '_' + CHR2 + '_' + str(END) + '_BND' + '_' + SVstrand
            AFInfo = h['FreqInfo'] + ':' + LocalSampleInfo[ID]
            localSV[ID]['CHR1'] = CHR1
            localSV[ID]['START'] = START
            localSV[ID]['CHR2'] = CHR2
            localSV[ID]['END'] = END
            localSV[ID]['SVtype'] = SVtype
            localSV[ID]['SIZE'] = SIZE
            localSV[ID]['STRANDS'] = SVstrand
            localSV[ID]['AC/AN'] = str(AC) + '/' + str(AN)
            localSV[ID]['AF'] = AF
            localSV[ID]['AFInfo'] = AFInfo
    cmd = f'rm {localSVtmp} {quaryINVtmp} {quaryBNDtmp} {localINVtemp} {localBNDtemp}'
    subprocess.run(cmd, shell = True, check = True)
    return localSV


def mergeBND(term1, term2, count1, count2):
    if count1 != 0 and count2 != 0:
        mergePhe = term1 + '|' + term2
        allphelist = mergePhe.split('|')
        phenmatchlist = list(OrderedDict.fromkeys(allphelist))
        newphecount = len(phenmatchlist)
        newPhenoTypeMatch = '|'.join(phenmatchlist)
    elif count1 != 0 and count2 == 0:
        newphecount = count1
        newPhenoTypeMatch = term1
    elif count1 == 0 and count2 != 0:
        newphecount = count2
        newPhenoTypeMatch = term2
    else:
        newPhenoTypeMatch = '.'
        newphecount = 0
    return newPhenoTypeMatch, newphecount


def BNDbp2(ALT):
    Bp2 = ''
    BP2chrome = ''
    if ']' in ALT:
        result = re.search(r'\](.*?)\]', ALT)
        if result:
            BP2chrome = result.group(1).split(':')[0]
            Bp2 = result.group(1).split(':')[1]
        else:
            print("No match found.")
    elif '[' in ALT:
        result = re.search(r'\[(.*?)\[', ALT)
        if result:
            BP2chrome = result.group(1).split(':')[0]
            Bp2 = result.group(1).split(':')[1]
        else:
            print("No match found.")
    else:
        print(ALT, 'BND format with wrong format！')
    return BP2chrome, Bp2


def INVoverlap(qustart, quend, dbstart, dbend):
    qulen = int(quend) - int(qustart) + 1
    dblen = int(dbend) - int(dbstart) + 1
    startmax = max(int(qustart), int(dbstart))
    endmin = min(int(quend), int(dbend))
    overlap = endmin - startmax + 1
    quoverlap = overlap / qulen
    dboverlap = overlap / dblen
    return quoverlap, dboverlap


def inheritanceSource(partent_reader, CHROM, Bp1region, BP2chrome, Bp2region, partnerSource, SVTY):
    # 父母样本中的变异
    if partnerSource == 'father':
        source = 'Paternal'
    else:
        source = 'Maternal'
    partentInfo = ''
    if SVTY == 'BND':
        records = partent_reader.fetch(CHROM, Bp1region[0], Bp1region[1])
        for record in records:
            chromosome = record.CHROM
            position = int(record.POS)
            reference = record.REF
            alternate = str(record.ALT[0])
            svtype = record.INFO['SVTYPE']
            # print(alternate,svtype)
            if svtype == 'BND':
                chrome2, Bp2 = BNDbp2(alternate)  # 父母变异的断点2
                if position in range(Bp1region[0], Bp1region[1] + 1) and chrome2 == BP2chrome and int(Bp2) in range(Bp2region[0], Bp2region[1] + 1):
                    # print(source,CHROM,Bp1region,BP2chrome,Bp2region,chromosome,position,chrome2,Bp2)
                    partentInfo = source + '(' + chromosome + ':' + str(position) + '_' + chrome2 + ':' + str(Bp2) + ')'
                    break
    if SVTY == 'INV':
        records = partent_reader.fetch(CHROM, Bp1region[0], Bp2region[1])
        for record in records:
            chromosome = record.CHROM
            position = int(record.POS)
            reference = record.REF
            alternate = record.ALT
            svtype = record.INFO['SVTYPE']
            if svtype == 'INV':
                if 'END' not in record.INFO:
                    dbend = position
                else:
                    dbend = int(record.INFO['END'])
                quoverlap, dboverlap = INVoverlap(Bp1region[0], Bp2region[1], position, dbend)
                if quoverlap >= 0.9 and dboverlap >= 0.9:
                    partentInfo = source + '(' + chromosome + ':' + str(position) + '_' + str(dbend) + '_' + str(quoverlap) + '_' + str(dboverlap) + ')'
                    break
    if SVTY == 'INS':
        END = Bp2region[0]
        POS = Bp1region[0]
        SVLEN = int(Bp2region[1])
        records = partent_reader.fetch(CHROM, POS)
        for record in records:
            chromosome = record.CHROM
            position = int(record.POS)
            reference = record.REF
            alternate = record.ALT
            svtype = record.INFO['SVTYPE']
            if svtype == 'INS':
                if 'END' not in record.INFO:
                    dbend = position
                else:
                    dbend = int(record.INFO['END'])
                if 'SVLEN' not in record.INFO:
                    svlen = 1
                else:
                    svlen = record.INFO['SVLEN']
                if position == POS and SVLEN == svlen:
                    partentInfo = source + '(' + chromosome + ':' + str(position) + '_' + str(dbend) + '_' + str(svlen) + ')'
                    break
    return partentInfo


def getCytoband(cytobandBed, CHROM, POS, CHROM2, POS2):
    df = pd.read_csv(cytobandBed, sep = '\t', names = ['chrome', 'start', 'end', 'cytoband'], header = None)
    # print(df)
    cytoInfo, cytoStart, cytoEND = '.', '.', '.'
    chrom = CHROM.replace('chr', '', 1)
    chrom2 = CHROM2.replace('chr', '', 1)
    # print(CHROM,POS,CHROM2,POS2)
    start = df.loc[(df['chrome'] == chrom) & (int(POS) >= df['start']) & (int(POS) <= df['end']), 'cytoband'].tolist()
    end = df.loc[(df['chrome'] == chrom2) & (int(POS2) >= df['start']) & (int(POS2) <= df['end']), 'cytoband'].tolist()
    if len(start) >= 1: cytoStart = start[0]
    if len(end) >= 1: cytoEND = end[0]
    cytoInfo = chrom + cytoStart + '-' + chrom2 + cytoEND
    return cytoInfo


# ========== 新增：批量 liftover 函数 ==========
def batch_liftover_to_hg19(regions, liftover_cmd, chain_file, temp_dir='.'):
    """
    批量将 hg38 坐标 liftover 到 hg19
    :param regions: list of (region_id, chrom, start, end)  1-based inclusive
    :param liftover_cmd: liftOver 可执行文件路径
    :param chain_file: hg38ToHg19.over.chain.gz
    :param temp_dir: 临时目录
    :return: dict {region_id: hg19_coord_str}  coord_str 格式 "chr:start-end"
    """
    if not regions:
        return {}
    # 创建临时 BED 文件 (0-based start, 1-based end)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bed', dir=temp_dir, delete=False) as f_in:
        bed_input = f_in.name
        for rid, chrom, start, end in regions:
            start_0based = start - 1
            f_in.write(f"{chrom}\t{start_0based}\t{end}\t{rid}\t0\t+\n")
    bed_output = tempfile.NamedTemporaryFile(suffix='.bed', dir=temp_dir, delete=False).name
    unmap_file = tempfile.NamedTemporaryFile(suffix='.unmap', dir=temp_dir, delete=False).name

    try:
        cmd = f"{liftover_cmd} {bed_input} {chain_file} {bed_output} {unmap_file}"
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)

        result = {}
        if os.path.exists(bed_output) and os.path.getsize(bed_output) > 0:
            with open(bed_output, 'r') as f_out:
                for line in f_out:
                    parts = line.strip().split('\t')
                    if len(parts) < 4:
                        continue
                    chrom_hg19 = parts[0]
                    start_0based = int(parts[1])
                    end_1based = int(parts[2])
                    rid = parts[3]
                    start_hg19 = start_0based + 1
                    coord = f"{chrom_hg19}:{start_hg19}-{end_1based}"
                    result[rid] = coord   # 若一个区域映射成多个片段，取第一个（实际很少见）
        # 未成功映射的给空字符串
        for rid, _, _, _ in regions:
            if rid not in result:
                result[rid] = ''
        return result
    finally:
        for f in [bed_input, bed_output, unmap_file]:
            if os.path.exists(f):
                os.unlink(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class = argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample", help = "sample ID", required = True, type = str)
    parser.add_argument("--input", help = "input vep tsv", required = True, type = str)
    parser.add_argument('--hpoterm', help = "input hpo terms", required = True, type = str)
    parser.add_argument('--HPOfile', help = "input phenotype gene file ", default = "phenotype_key_word_gene_list.txt", type = str)
    parser.add_argument('--omimFile', help = "input OMIM gene  file ", default = "gene_MIMnumber.V20220707.bed", type = str)
    parser.add_argument('--diseaseFile', help = "input gene and disease file ", default = "gene_disease.V20220707.bed", type = str)
    parser.add_argument('--VEPseverity', help = "input VEPseverity file ", default = "VEPseverity_plus.txt", type = str)
    parser.add_argument('--ped', type = str, required = True, help = 'ped file path')
    parser.add_argument('--outfile', default = "test.tsv", type = str)
    parser.add_argument("--cfg", help = 'config file path', default = "config.yaml", type = str)
    parser.add_argument('--bedtools', required = True, help = 'container bedtools executable')
    parser.add_argument('--liftover', required = True, help = 'container liftOver executable')
    args = parser.parse_args()
    inputfile = args.input
    inputpath = os.path.dirname(inputfile)
    pedFile = args.ped
    OutFile = open(args.outfile, 'w')
    sampleID = args.sample
    hpotermPD = args.hpoterm
    HPO_CHPO_gene = args.HPOfile
    geneDiseaseBed = args.diseaseFile
    geneMIM = args.omimFile
    configTpl = args.cfg
    tplDict = {}
    with open(configTpl, 'r') as tpl:
        tplDict = yaml.safe_load(tpl)

    # 读取 liftover 配置
    liftover_cmd = args.liftover
    liftover_chain = tplDict["genome"]["hg38ToHg19Chain"]

    hashPhenotype = defaultdict(dict)
    gene2Disease = defaultdict(dict)
    gene2MIM = defaultdict(dict)
    gene2pLI = defaultdict(dict)
    dirpath = os.path.dirname(geneMIM)
    HI_TS = tplDict['database']['HI_TS']
    pggsv = tplDict['database']['PGGSV']
    gnomad_sv = tplDict['database']['gnomadSvVcf']
    localSV = tplDict['database']['localSVDB']
    localSVsample = tplDict['database']['localSVsampleDB']
    cytobandBed = tplDict['database']['cytobandBed']
    bedtools = args.bedtools
    vcf_reader = vcf.Reader(filename = gnomad_sv)
    gene2HITS = defaultdict(dict)
    gene2HITS = getGeneHITS(HI_TS)
    PGGSV = getPGGSV(pggsv)
    localSVInfo = getLocalSV(localSV,inputfile,bedtools,localSVsample)
    pedTitle = ['pedID', 'sampleID', 'dadID', 'momID', 'gender', 'status']
    gender = None
    fatherVcf = motherVcf = ''
    if os.path.exists(pedFile):
        with open(pedFile, 'r') as PED:
            for line in PED:
                arr = line.rstrip('\n').split('\t')
                h = dict(zip(pedTitle, arr))
                if h['sampleID'] == sampleID and h['status'] == '2':
                    if h['gender'] == '2':
                        gender = 'F'
                    if h['dadID'] != '0':
                        fatherVcf = f"{inputpath}/{h['dadID']}.vep.vcf.gz"
                        print(fatherVcf)
                    if h['momID'] != '0':
                        motherVcf = f"{inputpath}/{h['momID']}.vep.vcf.gz"
                        print(motherVcf)
    if fatherVcf != '':
        if os.path.exists(fatherVcf):
            father_reader = vcf.Reader(filename = fatherVcf)
        else:
            print(fatherVcf + '文件不存在,请确认输入文件路径,遗传来源列将不会被正确注释')
    if motherVcf != '':
        if os.path.exists(motherVcf):
            mother_reader = vcf.Reader(filename = motherVcf)
        else:
            print(motherVcf + '文件不存在,请确认输入文件路径,遗传来源列将不会被正确注释')

    with open(HPO_CHPO_gene, 'r', encoding = "utf-8") as Hfp:
        next(Hfp)
        for line in Hfp:
            line = line.strip('\r\n')
            linelist = line.split('\t')
            hashPhenotype[linelist[2]]['genes'] = linelist[3]
            hashPhenotype[linelist[2]]['phenotype_CN'] = linelist[0]
    with open(geneDiseaseBed, 'r', encoding = "utf-8") as hfp:
        for line in hfp:
            line = line.strip('\r\n')
            linelist = line.split('\t')
            combined = zip(linelist[4].split('|'), linelist[5].split('|'), linelist[6].split('|'), linelist[7].split('|'))
            combined_list = list(combined)
            gene2Disease[linelist[3]] = combined_list
    with open(geneMIM, 'r', encoding = "utf-8") as hFp:
        for line in hFp:
            line = line.strip('\r\n')
            linelist = line.split('\t')
            gene2MIM[linelist[3]] = linelist[4]
            if linelist[9] != '.':
                gene2pLI[linelist[3]] = linelist[9]
    highList, moderateList, lowList, modifierList = getVEPseverity(args.VEPseverity)
    file = open(inputfile, 'r')
    head = file.readline().strip('\r\n')
    ar = head.split('\t')
    Consequenceindex = ar.index('Consequence')
    IMPACTindex = ar.index('IMPACT')
    symbolindex = ar.index('SYMBOL')
    geneidindex = ar.index('Gene')
    chromeindex = ar.index('CHROM')
    posindex = ar.index('POS')
    idindex = ar.index('ID')
    altindex = ar.index('ALT')
    svtypeindex = ar.index('SVTYPE')
    lenindex = ar.index('SVLEN')
    endindex = ar.index('END')
    strandindex = ar.index('STRANDS')
    qualindex = ar.index('QUAL')
    chromelist = ['chr1', 'chr2', 'chr3', 'chr4', 'chr5', 'chr6', 'chr7', 'chr8', 'chr9', 'chr10', 'chr11', 'chr12', 'chr13', 'chr14', 'chr15', 'chr16', 'chr17', 'chr18', 'chr19', 'chr20', 'chr21',
                  'chr22', 'chrX', 'chrY']

    # ========== 新增：先收集所有需要 liftover 的区域 ==========
    # 第一遍读取：收集所有 ID 及其坐标信息，用于批量 liftover
    sv_regions_for_lift = []   # (id, chrom, start, end)
    id_to_svtype = {}
    id_to_pos2 = {}   # 对于 BND，还需要第二个断点坐标 (chrom2, pos2)
    with open(inputfile, 'r', encoding = "utf-8") as hfp:
        next(hfp)
        for term in hfp:
            line = term.strip('\r\n')
            linelist = line.split('\t')
            ID = linelist[idindex]
            SVTYPE = linelist[svtypeindex]
            CHROM = linelist[chromeindex]
            POS = int(linelist[posindex])
            END = int(linelist[endindex]) if linelist[endindex] != '' else POS
            SVLEN = linelist[lenindex]
            ALT = linelist[altindex]
            id_to_svtype[ID] = SVTYPE
            if SVTYPE == 'BND':
                # BND 有两个断点：第一个断点 (CHROM, POS)
                sv_regions_for_lift.append((ID + "_bp1", CHROM, POS, POS))
                # 解析第二个断点
                BP2chrome, Bp2 = BNDbp2(ALT)
                if BP2chrome in chromelist:
                    sv_regions_for_lift.append((ID + "_bp2", BP2chrome, int(Bp2), int(Bp2)))
                    id_to_pos2[ID] = (BP2chrome, int(Bp2))
                else:
                    id_to_pos2[ID] = (None, None)
            elif SVTYPE == 'INV':
                sv_regions_for_lift.append((ID, CHROM, POS, END))
            elif SVTYPE == 'INS':
                # INS 的 END 列可能是插入位置，SVLEN 是插入长度，区间为 [POS, POS+SVLEN-1]
                if SVLEN != '.':
                    ins_end = POS + int(SVLEN) - 1
                    sv_regions_for_lift.append((ID, CHROM, POS, ins_end))
                else:
                    sv_regions_for_lift.append((ID, CHROM, POS, POS))
            # 其他类型（如 DUP、DEL）通常不在此脚本处理，但如果有需要也可添加
    # 批量 liftover
    hg19_map = batch_liftover_to_hg19(sv_regions_for_lift, liftover_cmd, liftover_chain)
    # ========================================================

    # 第二遍读取：构建 hash 并同时填充 hg19 坐标
    hash = defaultdict(dict)
    with open(inputfile, 'r', encoding = "utf-8") as hfp:
        next(hfp)
        for term in hfp:
            line = term.strip('\r\n')
            linelist = line.split('\t')
            Consequence = linelist[Consequenceindex].lower()
            IMPACT = linelist[IMPACTindex]
            SYMBOL = linelist[symbolindex]
            GENEID = linelist[geneidindex]
            Feature_type = linelist[geneidindex + 1]
            Feature = linelist[geneidindex + 2]
            BIOTYPE = linelist[geneidindex + 3]
            EXON = linelist[geneidindex + 4]
            INTRON = linelist[geneidindex + 5]
            HGVSc = linelist[geneidindex + 6]
            HGVSp = linelist[geneidindex + 7]
            cDNA_position = linelist[geneidindex + 8]
            CDS_position = linelist[geneidindex + 9]
            Protein_position = linelist[geneidindex + 10]
            Amino_acids = linelist[geneidindex + 11]
            Codons = linelist[geneidindex + 12]
            DISTANCE = linelist[geneidindex + 14]
            STRAND = linelist[geneidindex + 15]
            CANONICAL = linelist[geneidindex + 19]
            CHROM = linelist[chromeindex]
            POS = linelist[posindex]
            ID = linelist[idindex]
            ALT = linelist[altindex]
            SVTYPE = linelist[svtypeindex]
            SVLEN = linelist[lenindex]
            END = linelist[endindex]
            SVstrand = linelist[strandindex].split(':')[0]
            QUAL = linelist[qualindex]
            gnomAD_SV_info = ''
            pggSV_info = ''
            local_info = ''
            local_acan = ''
            local_af = ''
            pLI = ''
            if SYMBOL in gene2pLI:
                pLI = gene2pLI[SYMBOL]
            if CHROM in chromelist:
                # 获取 hg19 坐标
                hg19_pos_str = ''
                if SVTYPE == 'BND':
                    bp1_hg19 = hg19_map.get(ID + "_bp1", '')
                    bp2_hg19 = hg19_map.get(ID + "_bp2", '')
                else:
                    bp1_hg19 = hg19_map.get(ID, '')
                    bp2_hg19 = ''
                hash[ID] = {
                    "PhenoTypeMatch": '',
                    "phenoTypeRank": 0,
                    "omimGeneCount": 0,
                    "omimGene": '',
                    "pLI": pLI,
                    "omimDiseaseEN": '',
                    "omimDiseaseCN": '',
                    "ARAD": '.',
                    "POS1": CHROM + ':' + POS + '-' + END,
                    "cytoBand": '.',
                    "POS2": '.',
                    "ID": ID,
                    "QUAL": QUAL,
                    "SVTYPE": SVTYPE,
                    "impactScore": '.',
                    "Consequence": Consequence,
                    "IMPACT": IMPACT,
                    "inheritance": '.',  # 遗传来源
                    "gnomAD_SV": '',
                    "local_acan": '',
                    "local_af": '',
                    "local_info": '',
                    "PGGSV": '',
                    "SYMBOL": SYMBOL,
                    "geneID": GENEID,
                    "Feature_type": Feature_type,
                    "Feature": Feature,
                    "BIOTYPE": BIOTYPE,
                    "EXON": EXON,
                    "INTRON": INTRON,
                    "HGVSc": HGVSc,
                    "HGVSp": HGVSp,
                    "cDNA_position": cDNA_position,
                    "CDS_position": CDS_position,
                    "Protein_position": Protein_position,
                    "Amino_acids": Amino_acids,
                    "Codons": Codons,
                    "DISTANCE": DISTANCE,
                    "STRAND": STRAND,
                    "CANONICAL": CANONICAL,
                    "hg19_pos": bp1_hg19,      # 第一个断点的 hg19 坐标
                    "hg19_pos2": bp2_hg19      # 第二个断点的 hg19 坐标（非BND为空）
                }
                partnerSource = ''
                if SVTYPE == 'BND':
                    Bp1region = (int(POS) - 50, int(POS) + 50)
                    Bp2 = POS
                    BP2chrome = CHROM
                    # get BND breakpoint 2
                    BP2chrome, Bp2 = BNDbp2(ALT)
                    if CHROM in chromelist and BP2chrome in chromelist:
                        Bp2region = (int(Bp2) - 50, int(Bp2) + 50)
                        hash[ID]['POS2'] = BP2chrome + ':' + str(Bp2) + '-' + str(Bp2)
                        # gnomAD annotation
                        records = vcf_reader.fetch(CHROM, Bp1region[0], Bp1region[1])
                        for record in records:
                            chromosome = record.CHROM
                            position = record.POS
                            reference = record.REF
                            alternate = record.ALT
                            gnomadID = record.ID
                            dbend = record.INFO['END']
                            if 'BND' in gnomadID:
                                dbchr2 = ''
                                dbend2 = 0
                                if 'CHR2' in record.INFO: dbchr2 = record.INFO['CHR2']
                                if 'END2' in record.INFO: dbend2 = record.INFO['END2']
                                ac = record.INFO['AC'][0]
                                af = record.INFO['AF'][0]
                                an = record.INFO['AN']
                                if position in range(Bp1region[0], Bp1region[1] + 1) and dbchr2 == BP2chrome and dbend2 in range(Bp2region[0], Bp2region[1] + 1):
                                    gnomAD_SV_info = gnomAD_SV_info + ';' + str(ac) + '/' + str(an) + ':' + str(af) + '(' + gnomadID + '=' + chromosome + ':' + str(
                                        position) + '-' + dbchr2 + ':' + str(dbend2)
                        # localDB annotation
                        for localid in localSVInfo:
                            if localSVInfo[localid]['SVtype'] == 'BND' and localSVInfo[localid]['STRANDS'] == SVstrand:
                                CHR1 = localSVInfo[localid]['CHR1']
                                loSTART = localSVInfo[localid]['START']
                                CHR2 = localSVInfo[localid]['CHR2']
                                loEND = localSVInfo[localid]['END']
                                if CHR1 == CHROM and CHR2 == BP2chrome:
                                    qoverlap1, poverlap1 = INVoverlap(Bp1region[0], Bp1region[1], loSTART, loSTART)
                                    qoverlap2, poverlap2 = INVoverlap(Bp2region[0], Bp2region[1], loEND, loEND)
                                    if poverlap1 == 1 and poverlap2 == 1:
                                        local_info = local_info + ';' + localSVInfo[localid]['AFInfo']
                                        local_acan = local_acan + ';' + localSVInfo[localid]['AC/AN']
                                        local_af = str(local_af) + ';' + str(localSVInfo[localid]['AF'])
                        if fatherVcf != '' and os.path.exists(fatherVcf):
                            partnerSource = partnerSource + ';' + inheritanceSource(father_reader, CHROM, Bp1region, BP2chrome, Bp2region, 'father', 'BND')
                        if motherVcf != '' and os.path.exists(motherVcf):
                            if CHROM != 'chrY' and BP2chrome != 'chrY':
                                partnerSource = partnerSource + ';' + inheritanceSource(mother_reader, CHROM, Bp1region, BP2chrome, Bp2region, 'mother', 'BND')
                elif SVTYPE == 'INV':
                    Bp1region = (int(POS), int(POS))
                    Bp2region = (int(END), int(END))
                    records = vcf_reader.fetch(CHROM, Bp1region[0], Bp2region[1])
                    for record in records:
                        chromosome = record.CHROM
                        position = record.POS
                        reference = record.REF
                        alternate = record.ALT
                        dbend = record.INFO['END']
                        gnomadID = record.ID
                        ac = record.INFO['AC'][0]
                        af = record.INFO['AF'][0]
                        an = record.INFO['AN']
                        if 'INV' in gnomadID:
                            quoverlap, dboverlap = INVoverlap(POS, END, position, dbend)
                            if quoverlap >= 0.9 and dboverlap >= 0.9:
                                gnomAD_SV_info = gnomAD_SV_info + ';' + str(ac) + '/' + str(an) + ':' + str(af) + '(' + gnomadID + '=' + chromosome + ':' + str(position) + '-' + str(
                                    dbend) + '_' + str(quoverlap) + '_' + str(dboverlap) + ')'
                    for pggsvid in PGGSV:
                        if PGGSV[pggsvid]['SVtype'] == 'INV':
                            CHR = PGGSV[pggsvid]['CHR']
                            pgSTART = PGGSV[pggsvid]['START']
                            pgEND = PGGSV[pggsvid]['END']
                            if CHR == CHROM:
                                qoverlap, poverlap = INVoverlap(POS, END, pgSTART, pgEND)
                                if qoverlap >= 0.9 and poverlap >= 0.9:
                                    pggSV_info = pggSV_info + ';' + str(PGGSV[pggsvid]['AC']) + ':' + str(PGGSV[pggsvid]['AF']) + '(' + PGGSV[pggsvid]['SVID'] + ' ' + PGGSV[pggsvid][
                                        'URL'] + ' ' + str(qoverlap) + '_' + str(poverlap) + ')'
                    for localid in localSVInfo:
                        if localSVInfo[localid]['SVtype'] == 'INV' and localSVInfo[localid]['STRANDS'] == SVstrand:
                            CHR = localSVInfo[localid]['CHR1']
                            loSTART = localSVInfo[localid]['START']
                            loEND = localSVInfo[localid]['END']
                            if CHR == CHROM:
                                qoverlap, poverlap = INVoverlap(POS, END, loSTART, loEND)
                                if qoverlap >= 0.9 and poverlap >= 0.9:
                                    local_info = local_info + ';' + localSVInfo[localid]['AFInfo']
                                    local_acan = local_acan + ';' + localSVInfo[localid]['AC/AN']
                                    local_af = str(local_af) + ';' + str(localSVInfo[localid]['AF'])
                    if os.path.exists(fatherVcf):
                        partnerSource = partnerSource + ';' + inheritanceSource(father_reader, CHROM, Bp1region, CHROM, Bp2region, 'father', 'INV')
                    if os.path.exists(motherVcf):
                        if CHROM != 'chrY':
                            partnerSource = partnerSource + ';' + inheritanceSource(mother_reader, CHROM, Bp1region, CHROM, Bp2region, 'mother', 'INV')
                elif SVTYPE == 'INS':
                    Bp1region = (int(POS), int(POS))
                    Bp2region = (int(END), SVLEN)
                    records = vcf_reader.fetch(CHROM, int(POS))
                    for record in records:
                        chromosome = record.CHROM
                        position = record.POS
                        reference = record.REF
                        alternate = record.ALT
                        dbend = record.INFO['END']
                        gnomadID = record.ID
                        svlen = record.INFO['SVLEN']
                        ac = record.INFO['AC'][0]
                        af = record.INFO['AF'][0]
                        an = record.INFO['AN']
                        if 'INS' in gnomadID and position == POS and SVLEN == svlen:
                            gnomAD_SV_info = gnomAD_SV_info + ';' + str(ac) + '/' + str(an) + ':' + str(af) + '(' + gnomadID + '=' + chromosome + ':' + str(position) + '-' + str(dbend) + ')'
                    insID = CHROM + ':' + POS + '-' + END + '-INS'
                    if insID in PGGSV:
                        pggSV_info = pggSV_info + ';' + str(PGGSV[insID]['AC']) + ':' + str(PGGSV[insID]['AF']) + '(' + PGGSV[insID]['SVID'] + PGGSV[insID]['URL'] + ')'
                    if insID in localSVInfo:
                        local_info = local_info + ';' + localSVInfo[insID]['AFInfo']
                        local_acan = local_acan + ';' + localSVInfo[insID]['AC/AN']
                        local_af = local_af + ';' + localSVInfo[insID]['AF']
                    if os.path.exists(fatherVcf):
                        partnerSource = partnerSource + ';' + inheritanceSource(father_reader, CHROM, Bp1region, CHROM, Bp2region, 'father', 'INS')
                    if os.path.exists(motherVcf):
                        if CHROM != 'chrY':
                            partnerSource = partnerSource + ';' + inheritanceSource(mother_reader, CHROM, Bp1region, CHROM, Bp2region, 'mother', 'INS')
                else:
                    pass
                localSamples = ''
                localaf = ''
                localacan = ''
                localac = 0
                localan = 0
                localSamplesList = []
                if local_info:
                    local_infos = local_info.lstrip(';').split(';')
                    for sub_local_info in local_infos:
                        samplestr1 = sub_local_info.split(':')[2]
                        subSamplesList = samplestr1.split(',')
                        for subSamples in subSamplesList:
                            localSamplesList.append(subSamples)
                if local_af:
                    localan = local_acan.lstrip(';').split(';')[0].split('/')[1]
                    localSamplesSetList = list(set(localSamplesList))
                    for sample in localSamplesSetList:
                        if 'Het' in sample:
                            localac += 1
                        if 'Hom' in sample:
                            localac += 2
                if localan != 0:
                    localaf = round(int(localac)/int(localan),6)
                    localacan = str(localac) + '/' + str(localan)
                if len(localSamplesList) > 0:
                    localSamplesList = list(set(localSamplesList))
                    localSamplesList.sort(reverse=True)
                    if len(localSamplesList) > 10:
                        localSamples = ','.join(localSamplesList[:10])
                    else:
                        localSamples = ','.join(localSamplesList)
                hash[ID]['gnomAD_SV'] = gnomAD_SV_info.lstrip(';')
                hash[ID]['PGGSV'] = pggSV_info.lstrip(';')
                hash[ID]['local_acan'] = localacan
                hash[ID]['local_af'] = str(localaf)
                hash[ID]['local_info'] = localSamples
                newIMPACT = IMPACT
                impactScore = 0
                if '&' in Consequence:
                    Consequencelist = Consequence.split('&')
                    if len(list(set(Consequencelist) & set(highList))) > 0:
                        newIMPACT = "HIGH"
                        impactScore = 100
                    elif len(list(set(Consequencelist) & set(moderateList))) > 0:
                        newIMPACT = "MODERATE"
                        impactScore = 50
                    elif len(list(set(Consequencelist) & set(lowList))) > 0:
                        newIMPACT = "LOW"
                        impactScore = 10
                    else:
                        newIMPACT = "MODIFIER"
                        impactScore = 1
                else:
                    if IMPACT == 'HIGH':
                        impactScore = 100
                    elif IMPACT == 'MODERATE':
                        impactScore = 50
                    elif IMPACT == 'LOW':
                        impactScore = 10
                    else:
                        impactScore = 1
                if SYMBOL in gene2MIM:
                    omimGeneCount = 1
                    omimGene = SYMBOL
                else:
                    omimGeneCount = 0
                    omimGene = '.'
                if SYMBOL in gene2Disease:
                    omimDiseaseEN = fromArraytoStr(gene2Disease[SYMBOL])[0]
                    omimDiseaseCN = fromArraytoStr(gene2Disease[SYMBOL])[1]
                    inhertanceType = fromArraytoStr(gene2Disease[SYMBOL])[2]
                else:
                    omimDiseaseEN = '.'
                    omimDiseaseCN = '.'
                    inhertanceType = '.'
                keywordInfo, keywordcount = keyword_match(SYMBOL, hpotermPD, hashPhenotype)
                cytobandInfo = getCytoband(cytobandBed, CHROM, POS, CHROM, END)
                hash[ID]['PhenoTypeMatch'] = keywordInfo
                hash[ID]['phenoTypeRank'] = keywordcount
                hash[ID]['omimGeneCount'] = omimGeneCount
                hash[ID]['omimGene'] = omimGene
                hash[ID]['omimDiseaseEN'] = omimDiseaseEN
                hash[ID]['omimDiseaseCN'] = omimDiseaseCN
                hash[ID]['impactScore'] = str(impactScore)
                hash[ID]['cytoBand'] = cytobandInfo
                hash[ID]['IMPACT'] = newIMPACT
                hash[ID]['ARAD'] = inhertanceType.replace(".|.", '.')
                if partnerSource == ';;':
                    hash[ID]['inheritance'] = ''
                else:
                    hash[ID]['inheritance'] = partnerSource.strip(';')

    # 修改输出表头，增加“染色体位置_hg19”
    OutFile.write(
        "主|次|其他" + "\t" + "初审结论" + "\t" + "复审结论" + "\t" + "PhenoTypeMatch" + "\t" + "PhenoTypeRank" + "\t" + "OMIMGeneCount" + "\t" + "OMIMGene" + "\t" + "pLI" + "\t" + "OMIM_Disease" + "\t" + "OMIM_Disease翻译" + "\t" + "遗传模式" + "\t" + "染色体位置" + "\t染色体位置2" + "\t" + "染色体位置_hg19" + "\t" + "染色体位置2_hg19"+"\tCytoband\t" + "ID" + "\t" + "QUAL" + "\t" + "SVTYPE" + "\t" + "impactScore" + "\t" + "Consequence" + "\t" + "IMPACT" + "\t" + "遗传来源" + "\t" + "gnomADV4_SV" + "\t" + "本地AC/AN" + "\t" + "本地频率" + "\t" + "LocalInfo" + "\t" + "PGGSV" + "\t" + "SYMBOL" + "\t" + "GeneID" + "\t" + "Feature_type" + "\t" + "Feature" + "\t" + "BIOTYPE" + "\t" + "EXON" + "\t" + "INTRON" + "\t" + "HGVSc" + "\t" + "HGVSp" + "\t" + "cDNA_position" + "\t" + "CDS_position" + "\t" + "Protein_position" + "\t" + "Amino_acids" + "\t" + "Codons" + "\t" + "DISTANCE" + "\t" + "STRAND" + "\t" + "CANONICAL" + "\n")

    # 输出每一行，增加 hg19_pos 字段
    for id in sorted(hash.keys()):
        svtype = hash[id]['SVTYPE']
        newPhenoTypeMatch = '.'
        newphecount = 0
        if svtype == 'BND' and '_1' in id:
            id2 = id.replace('_1', '_2', 1)
            if id2 in hash:
                newPhenoTypeMatch, newphecount = mergeBND(hash[id]['PhenoTypeMatch'], hash[id2]['PhenoTypeMatch'], hash[id]['phenoTypeRank'], hash[id2]['phenoTypeRank'])
                newOMIMgene, newcount = mergeBND(hash[id]['omimGene'], hash[id2]['omimGene'], hash[id]['omimGeneCount'], hash[id2]['omimGeneCount'])
                if hash[id2]['pLI'] != '':
                    if hash[id]['pLI'] != '':
                        newpLI = max(float(hash[id]['pLI']), float(hash[id2]['pLI']))
                    else:
                        newpLI = hash[id2]['pLI']
                else:
                    newpLI = hash[id]['pLI']
                if hash[id2]['omimDiseaseEN'] != '.':
                    newomimDiseaseEN = hash[id]['omimDiseaseEN'] + '|' + hash[id2]['omimDiseaseEN']
                else:
                    newomimDiseaseEN = hash[id]['omimDiseaseEN']
                if hash[id2]['omimDiseaseCN'] != '.':
                    newomimDiseaseCN = hash[id]['omimDiseaseCN'] + '|' + hash[id2]['omimDiseaseCN']
                else:
                    newomimDiseaseCN = hash[id]['omimDiseaseCN']
                if hash[id2]['ARAD'] != '':
                    newARAD = (hash[id]['ARAD'] + '|' + hash[id2]['ARAD']).replace(".|.", '.')
                else:
                    newARAD = (hash[id]['ARAD']).replace(".|.", '.')
                newQUAL = hash[id]['QUAL'] + '|' + hash[id2]['QUAL']
                newConsequence = hash[id]['Consequence'] + '|' + hash[id2]['Consequence']
                NewIMPNACT = hash[id]['IMPACT'] + '|' + hash[id2]['IMPACT']
                newgnomAD_SV = hash[id]['gnomAD_SV']
                if hash[id2]['impactScore'] != '':
                    newimpactScore = hash[id]['impactScore'] + '|' + hash[id2]['impactScore']
                else:
                    newimpactScore = hash[id]['impactScore']
                if hash[id2]['SYMBOL'] != '.':
                    newSYMBOL = hash[id]['SYMBOL'] + '|' + hash[id2]['SYMBOL']
                else:
                    newSYMBOL = hash[id]['SYMBOL']
                if hash[id2]['geneID'] != '.':
                    newgeneID = hash[id]['geneID'] + '|' + hash[id2]['geneID']
                else:
                    newgeneID = hash[id]['geneID']
                if hash[id2]['Feature_type'] != '.':
                    newFeature_type = hash[id]['Feature_type'] + '|' + hash[id2]['Feature_type']
                else:
                    newFeature_type = hash[id]['Feature_type']
                if hash[id2]['Feature'] != '.':
                    newFeature = hash[id]['Feature'] + '|' + hash[id2]['Feature']
                else:
                    newFeature = hash[id]['Feature']
                newBIOTYPE = (hash[id]['BIOTYPE'] + '|' + hash[id2]['BIOTYPE']).replace(".|.", '.')
                newEXON = (hash[id]['EXON'] + '|' + hash[id2]['EXON']).replace(".|.", '.')
                newINTRON = (hash[id]['INTRON'] + '|' + hash[id2]['INTRON']).replace(".|.", '.')
                newHGVSc = (hash[id]['HGVSc'] + '|' + hash[id2]['HGVSc']).replace(".|.", '.')
                newHGVSp = (hash[id]['HGVSp'] + '|' + hash[id2]['HGVSp']).replace(".|.", '.')
                newcDNA_position = (hash[id]['cDNA_position'] + '|' + hash[id2]['cDNA_position']).replace(".|.", '.')
                newCDS_position = (hash[id]['CDS_position'] + '|' + hash[id2]['CDS_position']).replace(".|.", '.')
                newProtein_position = (hash[id]['Protein_position'] + '|' + hash[id2]['Protein_position']).replace(".|.", '.')
                newAmino_acids = (hash[id]['Amino_acids'] + '|' + hash[id2]['Amino_acids']).replace(".|.", '.')
                newCodons = (hash[id]['Codons'] + '|' + hash[id2]['Codons']).replace(".|.", '.')
                newDISTANCE = (hash[id]['DISTANCE'] + '|' + hash[id2]['DISTANCE']).replace(".|.", '.')
                newSTRAND = (hash[id]['STRAND'] + '|' + hash[id2]['STRAND']).replace(".|.", '.')
                newCANONICAL = (hash[id]['CANONICAL'] + '|' + hash[id2]['CANONICAL']).replace(".|.", '.')
                newCytoband = hash[id]['cytoBand'] + '|' + hash[id2]['cytoBand']
                # 合并 hg19 坐标
                new_hg19_pos = hash[id].get('hg19_pos', '')      # id 的第一个断点
                new_hg19_pos2 = hash[id2].get('hg19_pos', '')   # id2 的第一个断点即原第二个断点
                OutFile.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(
                '', '', '', newPhenoTypeMatch, str(newphecount), str(newcount), newOMIMgene, newpLI, newomimDiseaseEN,
                newomimDiseaseCN, newARAD, hash[id]['POS1'], hash[id]['POS2'], new_hg19_pos, new_hg19_pos2, newCytoband, hash[id]['ID'], hash[id]['QUAL'], hash[id]['SVTYPE'], newimpactScore, newConsequence, NewIMPNACT,
                hash[id]['inheritance'], newgnomAD_SV, hash[id]['local_acan'], hash[id]['local_af'], hash[id]['local_info'], hash[id]['PGGSV'], newSYMBOL, newgeneID, newFeature_type, newFeature, newBIOTYPE, newEXON, newINTRON, newHGVSc, newHGVSp, newcDNA_position,
                newCDS_position, newProtein_position, newAmino_acids, newCodons, newDISTANCE, newSTRAND, newCANONICAL))
            else:
                print("Warning:BND类型变异", id, "其中一个断点在contig染色体")
        elif svtype != 'BND':
            if hash[id]['PhenoTypeMatch'] == '':
                newPhenoTypeMatch = hash[id]['PhenoTypeMatch'].replace('', '.')
            else:
                newPhenoTypeMatch = hash[id]['PhenoTypeMatch']
            OutFile.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(
                '', '', '',newPhenoTypeMatch,str(hash[id]['phenoTypeRank']),str(hash[id]['omimGeneCount']),hash[id]['omimGene'],hash[id]['pLI'],hash[id]['omimDiseaseEN'],hash[id]['omimDiseaseCN'],hash[id]['ARAD'],hash[id]['POS1'],hash[id]['POS2'], hash[id].get('hg19_pos', ''), hash[id].get('hg19_pos2', ''),hash[id]['cytoBand'],hash[id]['ID'],hash[id]['QUAL'],hash[id]['SVTYPE'],hash[id]['impactScore'],hash[id]['Consequence'],hash[id]['IMPACT'],hash[id]['inheritance'],hash[id]['gnomAD_SV'], hash[id]['local_acan'], hash[id]['local_af'], hash[id]['local_info'],hash[id]['PGGSV'],hash[id]['SYMBOL'],hash[id]['geneID'],hash[id]['Feature_type'],hash[id]['Feature'],hash[id]['BIOTYPE'],hash[id]['EXON'],hash[id]['INTRON'],hash[id]['HGVSc'],hash[id]['HGVSp'],hash[id]['cDNA_position'],hash[id]['CDS_position'],hash[id]['Protein_position'],hash[id]['Amino_acids'],hash[id]['Codons'],hash[id]['DISTANCE'],hash[id]['STRAND'],hash[id]['CANONICAL']))
    OutFile.close()
