#!/usr/bin/env python  
# -*- coding:utf-8 _*-
""" 
@author:Rzhang 
@license: Apache Licence 
@file: CNV_annotation.py
@time: 2023/11/27
@contact: zhiangrian@126.com
@site:  
@software: PyCharm 
example run:  /bi/software/Python-3.7.11/bin/python3 /sg2/19.yuli/13WGS/WGS/script/5.CNV_annotation.py -I 03_CNV/Annot/WGS25020010-WGS.CNV.bed -O 03_CNV/Annot/WGS25020010-WGS.CNV.tsv -s WGS25020010-WGS --hpo "microphthalmia.hpo,Unilateral_microphthalmos.hpo,torticollis.hpo,global_developmental_delay.hpo,Immune-System.hpo,cryptorchidism.hpo,Bilateral_cryptorchidism.hpo,abnormality_of_the_penis.hpo,hearing_abnormality.hpo,hearing_impairment.hpo,Severe_hearing_impairment.hpo,report_HL.hpo,Morphological_abnormality_of_the_semicircular_canal.hpo,hypoplasia_of_the_semicircular_canal.hpo,Dilated_vestibule_of_the_inner_ear.hpo,Narrow_internal_auditory_canal.hpo,Abnormality_of_the_cochlear_nerve.hpo,Abnormality_of_the_vestibulocochlear_nerve.hpo,mastoiditis.hpo,cognitive_impairment.hpo,delayed_speech_and_language_development.hpo,expressive_language_delay.hpo,poor_eye_contact.hpo,motor_delay.hpo,delayed_gross_motor_development.hpo,Delayed_ability_to_stand.hpo,delayed_social_development.hpo,intellectual_disability.hpo,delayed_fine_motor_development.hpo,short_attention_span.hpo,incoordination.hpo,abnormal_central_motor_function.hpo,Mood_swings.hpo,sleep_disturbance.hpo" --ped 08_ped/JX25G00170222_WGS25020010.ped -cfg config.yaml
/bi/software/Python-3.7.11/bin//python /bi/19.yuli/git/wgs/script/5.CNV_annotation.py -I /sg2/19.yuli/13WGS/WGS_test/WGS_20250702_T7Hg38V3.6.6/03_CNV/Annot/WGS25060150-WGS.CNV.bed -O /sg2/19.yuli/13WGS/WGS_test/WGS_20250702_T7Hg38V3.6.6/03_CNV/Annot/WGS25060150-WGS.CNV.tsv -s WGS25060150-WGS --hpo "polyuria.hpo,myalgia.hpo" --ped 08_ped/JXF57J019158_WGS25060149.ped -cfg config.yaml
"""

import subprocess
from collections import defaultdict

import argparse
import os
import re
import yaml
import pandas as pd
from io import StringIO


def getHpo(keywordFile, patientHPO):
    hashPhenotype = {}
    keywordopen = open(keywordFile, 'r')
    head = keywordopen.readline().strip('\r\n')
    ar = head.split('\t')
    CHPOindex = ar.index('中文')
    termindex = ar.index('配置关键词')
    geneindex = ar.index('基因列表')
    hpoidindex = ar.index('HPO_id')
    keywordopen.close()
    keywordList = patientHPO.split(',')
    hpoIdList = ''
    with open(keywordFile, 'r') as WORD:
        next(WORD)
        for word in WORD:
            word = word.strip()
            arr = word.split('\t')
            hashPhenotype[arr[termindex]] = {"genelist": arr[geneindex], "phenotype_CN": arr[CHPOindex]}
            if arr[termindex] in keywordList and bool(re.search(r'HP:\d+', arr[hpoidindex])):
                hpoIdList += arr[hpoidindex] + ","
    hpoIdList = hpoIdList.rstrip(',')
    return hashPhenotype, hpoIdList


def keyword_match(geneList, phenotypeList, hashPhenotype):
    count = 0
    out_info = ""
    genes = geneList.split(",")  # CNV include genes
    keyWords = phenotypeList.split(",")  # sample hpo terms

    for keyword in keyWords:
        gene_filter = []
        if keyword in hashPhenotype:
            gene_list = hashPhenotype[keyword]["genelist"].split("|")
            for gene in genes:
                if gene in gene_list:
                    gene_filter.append(gene)  # CNV include gene and sample hpo genes
        else:
            print("#Warning: " + keyword + " is not in phenotype_key_word_gene_list.txt!")

        if len(gene_filter) != 0:
            count += 1
            if keyword in hashPhenotype:
                str1 = keyword + "(" + hashPhenotype[keyword]["phenotype_CN"] + ")"
            else:
                str1 = keyword + "(.)"
            str2 = ";".join(gene_filter) + "[" + str1 + "]" + "|"
            out_info += str2

    out_info = out_info[:-1] if out_info else ""
    return out_info


def dropfile(*files):
    for file in files:
        print(file)
        if os.path.exists(file):
            os.unlink(file)


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


def maxValue(hlist):
    if '3' in hlist:
        maxvalue = '3'
    elif '2' in hlist:
        maxvalue = '2'
    elif '1' in hlist:
        maxvalue = '1'
    else:
        maxvalue = '.'
    return maxvalue


def process_morbidmap(morbidmap_file):
    with open(morbidmap_file, "r") as file:
        lines = [line for line in file.readlines() if not ((line.startswith('#') or line.startswith('"#')))]
    morbidmap_df = pd.read_csv(StringIO(''.join(lines)), sep='\t', dtype=str, comment="#", header=None)
    morbidmap_df.columns = ['Phenotype', 'Gene/Locus And Other Related Symbols', 'MIM Number', 'Cyto Location']
    morbidmap_dict = dict()
    for _, row in morbidmap_df.iterrows():
        _gene_list = row['Gene/Locus And Other Related Symbols'].split(',')
        for _gene in _gene_list:
            _gene = _gene.strip()
            morbidmap_dict.setdefault(_gene, 'morbid')
    return(morbidmap_dict)


def process_gene2disease(omimFile):
    disease_df = pd.read_csv(omimFile, sep='\t', dtype=str, encoding='utf-8')
    disease_df = disease_df[['Gene', 'OMIM_PhenotypeID', 'Inheritance', 'DiseaseEN', 'DiseaseCN']]
    gene2disease_dict = dict()
    for _, row in disease_df.iterrows():
        if not re.search(r'\d', row['OMIM_PhenotypeID']):
            continue
        gene = row['Gene']
        disease_en = [f"{_phenotype}({_inheritance}:{_mim_number})" for (_phenotype, _inheritance, _mim_number) in zip(str(row['DiseaseEN']).split('|'), str(row['Inheritance']).split('|'), str(row['OMIM_PhenotypeID']).split('|'))]
        disease_cn = [f"{_phenotype}({_inheritance}:{_mim_number})" for (_phenotype, _inheritance, _mim_number) in zip(str(row['DiseaseCN']).split('|'), str(row['Inheritance']).split('|'), str(row['OMIM_PhenotypeID']).split('|'))]
        gene2disease_dict.setdefault(gene, dict({'Inheritance': '', 'gene2DiseaseEN': '', 'gene2DiseaseCN': ''}))
        gene2disease_dict[gene].update({'Inheritance': '|'.join(list(set([_inheritance.strip() for _inheritance in re.split(r';|\|', row['Inheritance']) if _inheritance.strip() not in ['', '.']])))})
        gene2disease_dict[gene].update({'gene2DiseaseEN': '; '.join(disease_en)})
        gene2disease_dict[gene].update({'gene2DiseaseCN': '; '.join(disease_cn)})
    return(gene2disease_dict)


def getLocalSample(localCNVsamplebed):
    LocalSampleInfo = defaultdict(dict)
    with open(localCNVsamplebed, "r") as localSample:
        localSamples = ['Chrom', 'Start', 'End', 'Type', 'Sample', 'Strand']
        for line in localSample:
            line = line.strip()
            arr = line.split("\t")
            h = dict(zip(localSamples, arr))
            cnvID = h['Chrom'] + ':' + h['Start'] + '-' + h['End'] + ':' + h['Type']
            sample = h['Sample']
            LocalSampleInfo[cnvID] = sample
    return LocalSampleInfo


def localCNVanno(region,LocalSampleInfo):
    region = region.strip()
    arr = region.split('\t')
    h = {dbTitle[i]: arr[i] for i in range(len(arr))}
    id = h['Chr'] + ':' + h['Start'] + '-' + h['End'] + ':' + h['Type']
    chrs = h['chrList'].split(',')
    starts = h['startList'].split(',')
    ends = h['endList'].split(',')
    CNVTypes = h['CNVType'].split(',')
    freqs = h['freq'].split(',')
    sampleCount_CNVseq = 0
    sampleCount_Lumpy = 0
    ANcount = 0
    local_info_CNVseq = []
    local_info_Lumpy = []
    local_sample_CNVseq = ''
    local_sample_Lumpy = ''
    freq_CNVseq = ''
    freq_Lumpy = ''
    ACAN_CNVseq = ''
    ACAN_Lumpy = ''
    for i in range(len(chrs)):
        subCNVid = chrs[i] + ':' + starts[i] + '-' + ends[i] + ':' + CNVTypes[i]
        ani = (freqs[i].split(':')[0]).split('/')[1]
        ANcount = int(ani)
        subfreqs = freqs[i].split(':')
        if 'CNVseq' in CNVTypes[i]:
            samples_CNVseq = LocalSampleInfo[subCNVid].split('&')
            for subsample_CNVseq in samples_CNVseq:
                local_info_CNVseq.append(subsample_CNVseq)
        if 'Lumpy' in CNVTypes[i]:
            samples_Lumpy = LocalSampleInfo[subCNVid].split('&')
            for subsample_Lumpy in samples_Lumpy:
                local_info_Lumpy.append(subsample_Lumpy)
    local_info_CNVseq = list(set(local_info_CNVseq))
    sampleCount_CNVseq = len(local_info_CNVseq)
    if ANcount != 0:
        freq_CNVseq = round(sampleCount_CNVseq/ANcount,6)
        ACAN_CNVseq = str(sampleCount_CNVseq) + '/' + str(ANcount)
    local_info_CNVseq.sort(reverse=True)
    if sampleCount_CNVseq > 10:
        local_sample_CNVseq = ','.join(local_info_CNVseq[:10])
    else:
        local_sample_CNVseq = ','.join(local_info_CNVseq)
    local_info_Lumpy = list(set(local_info_Lumpy))
    sampleCount_Lumpy = len(local_info_Lumpy)
    if ANcount != 0:
        freq_Lumpy = round(sampleCount_Lumpy/ANcount,6)
        ACAN_Lumpy = str(sampleCount_Lumpy) + '/' + str(ANcount)
    local_info_Lumpy.sort(reverse=True)
    if sampleCount_Lumpy > 10:
        local_sample_Lumpy = ','.join(local_info_Lumpy[:10])
    else:
        local_sample_Lumpy = ','.join(local_info_Lumpy)
    return local_sample_CNVseq,local_sample_Lumpy,ACAN_CNVseq,ACAN_Lumpy,freq_CNVseq,freq_Lumpy,id


def liftover_cnv_to_hg19(regions, liftover_cmd, chain_file, temp_dir='.'):
    """
    批量将CNV区域从hg38 liftOver到hg19
    :param regions: list of (cnv_id, chrom, start, end)  坐标均为1-based inclusive
    :param liftover_cmd: liftOver可执行文件路径
    :param chain_file: hg38ToHg19.over.chain.gz
    :param temp_dir: 临时文件目录
    :return: dict {cnv_id: hg19_coord_str}  coord_str格式: "chr1:100-200;chr2:300-400"
    """
    if not regions:
        return {}
    
    import tempfile
    import subprocess
    import os
    
    # 创建临时BED文件（0-based start, 1-based end）
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bed', dir=temp_dir, delete=False) as f_in:
        bed_input = f_in.name
        for cnv_id, chrom, start, end in regions:
            start_0based = start - 1
            f_in.write(f"{chrom}\t{start_0based}\t{end}\t{cnv_id}\t0\t+\n")
    
    bed_output = tempfile.NamedTemporaryFile(suffix='.bed', dir=temp_dir, delete=False).name
    unmap_file = tempfile.NamedTemporaryFile(suffix='.unmap', dir=temp_dir, delete=False).name
    
    try:
        cmd = f"{liftover_cmd} {bed_input} {chain_file} {bed_output} {unmap_file}"
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        
        # 解析输出BED
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
                    cnv_id = parts[3]
                    # 转换回1-based inclusive
                    start_hg19 = start_0based + 1
                    coord = f"{chrom_hg19}:{start_hg19}-{end_1based}"
                    if cnv_id not in result:
                        result[cnv_id] = []
                    result[cnv_id].append(coord)
        
        # 合并同一个CNV的多个片段
        hg19_map = {}
        for cnv_id, coord_list in result.items():
            hg19_map[cnv_id] = ';'.join(coord_list)
        
        # 未成功映射的CNV给空字符串
        for cnv_id, _, _, _ in regions:
            if cnv_id not in hg19_map:
                hg19_map[cnv_id] = ''
        
        return hg19_map
    finally:
        for f in [bed_input, bed_output, unmap_file]:
            if os.path.exists(f):
                os.unlink(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'CNV bed file annotation ')
    parser.add_argument("-I", '--input', type = str, required = True, default = "test.CNV.bed", help = 'input file path')
    parser.add_argument("-O", '--output', type = str, default = "test.tsv", required = True, help = 'output file path')
    parser.add_argument("-s", '--sample', type = str, required = True, help = 'sample id')
    parser.add_argument('--ped', type = str, required = True, help = 'ped file path')
    parser.add_argument("-cfg", '--config', type = str, help = 'config file path')
    parser.add_argument('--hpo', type = str, help = 'hpo term list')
    parser.add_argument('--bedtools', required = True, help = 'container bedtools executable')
    parser.add_argument('--bcftools', required = True, help = 'container bcftools executable')
    parser.add_argument('--annotsv', required = True, help = 'container AnnotSV executable')
    parser.add_argument('--liftover', required = True, help = 'container liftOver executable')
    args = parser.parse_args()
    output = args.output
    input = args.input
    projectDir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    configTpl = args.config
    tplDict = {}
    with open(configTpl, 'r') as tpl:
        tplDict = yaml.safe_load(tpl)
    bedtools = args.bedtools
    bcftools = args.bcftools
    annotsv = args.annotsv
    keywordFile = tplDict['database']['keyWords2GeneFile']
    dgvBed = tplDict['database']['dgvBed']
    gnomadBed = tplDict['database']['gnomadBed']
    localCNVbed = tplDict['database']['localCNVDB']
    localCNVsamplebed = tplDict['database']['localCNVsampleDB']
    decipherPatientBed = tplDict['database']['decipherPatientBed']
    transcriptExonIntron = tplDict['database']['transcriptExonIntron']
    gene2MimNumBed = tplDict['database']['gene_MIMnumber']
    cytobandBed = tplDict['database']['cytobandBed']
    HI_TS = tplDict['database']['HI_TS']
    morbidmap_file = tplDict['database']['morbidmapFile']
    omimFile = tplDict['database']['omimFile']
    pedFile = args.ped
    work_dir = os.getcwd()
    phenotypeList = args.hpo
    hashPhenotype = defaultdict(dict)
    gene2HITS = defaultdict(dict)
    hpoIdList = ''
    hashPhenotype, hpoIdList = getHpo(keywordFile, phenotypeList)
    gene2HITS = getGeneHITS(HI_TS)
    morbidmap_dict = process_morbidmap(morbidmap_file)
    gene2disease_dict = process_gene2disease(omimFile)

    # print(gene2DiseaseCN, gene2DiseaseEN, gene2Inheritance)
    tmp_output = re.sub(r"tsv", "tmp.tsv", output)
    tmp_file = open(tmp_output, "w")
    tmp_file.write(
        "6000" + "\t" + "主|次|其他" + "\t" + "初审结论" + "\t" + "复审结论" + "\t" + "AnnotSV_Ranking" + "\t" + "表型关键词匹配" + "\t" + "染色体位置_hg38" + "\t" + "染色体位置_hg19" + "\t" + "变异类型" + "\t" + "区带" + "\t" + "大小" + "\t" + "拷贝数" + "\t" + "遗传来源" + "\t" + "本地AC/AN" + "\t" + "本地频率" + "\t" + "LocalSample" + "\t" + "本地AC/AN_P" + "\t" + "本地频率_P" + "\t" + "LocalSample_P" + "\t" + "本地AC/AN_B" + "\t" + "本地频率_B" + "\t" + "LocalSample_B" + "\t" + "DGV" + "\t" + "gnomAD_SV" + "\t" + "Decipher" + "\t" + "SNV提示" + "\t" + "总基因数目" + "\t" + "morbid基因数目" + "\t" + "morbid基因列表" + "\t" + "OMIM_Disease" + "\t" + "OMIM_Disease翻译" + "\t" + "遗传模式" + "\t" + "CNV所在Exons" + "\t" + "印记基因" + "\t" + "HI_Score" + "\t" + "TS_Score" + "\t" + "pLI" + "\t" + "method" + "\n")
    match_result = re.match(r"(.*)/(.*)\.CNV\.bed", input)
    if match_result:
        cnvDir = match_result.group(1)
    else:
        cnvDir = ''
    basename = os.path.basename(input)
    # print(basename)
    sampleID = args.sample
    # print(sampleID)
    basename = basename.replace(sampleID, "")

    annotDir = f'{cnvDir}/{sampleID}'
    if not os.path.exists(annotDir):
        os.makedirs(annotDir, exist_ok=True)
    pa_bed = f"{cnvDir}/{sampleID}.CNV.pa.tmp.bed"
    ma_bed = f"{cnvDir}/{sampleID}.CNV.ma.tmp.bed"
    dgvAnno = f"{cnvDir}/{sampleID}.CNV.DGV.tmp.bed"
    gnomadAnno = f"{cnvDir}/{sampleID}.CNV.GnomAD.tmp.bed"
    localAnnoP = f"{cnvDir}/{sampleID}.CNV.Local_P.tmp.bed"
    localAnnoB = f"{cnvDir}/{sampleID}.CNV.Local_B.tmp.bed"
    localAnnoV = f"{cnvDir}/{sampleID}.CNV.Local_V.tmp.bed"
    decipherPatientsAnno = f"{cnvDir}/{sampleID}.CNV.Decipher.Patients.tmp.bed"
    decipherSyndromeAnnoTmp1 = f"{cnvDir}/{sampleID}.CNV.Decipher.Syndrome.Tmp1.tmp.bed"
    decipherSyndromeAnnoTmp2 = f"{cnvDir}/{sampleID}.CNV.Decipher.Syndrome.Tmp2.tmp.bed"
    decipherSyndromeAnno = f"{cnvDir}/{sampleID}.CNV.Decipher.Syndrome.tmp.bed"
    startExonIntron = f"{cnvDir}/{sampleID}.CNV.start.ExonIntron.tmp.bed"
    endExonIntron = f"{cnvDir}/{sampleID}.CNV.end.ExonIntron.tmp.bed"
    startCytobandAnno = f"{cnvDir}/{sampleID}.CNV.start.cytoband.tmp.bed"
    endCytobandAnno = f"{cnvDir}/{sampleID}.CNV.end.cytoband.tmp.bed"
    cytobandAnno = f"{cnvDir}/{sampleID}.CNV.cytoband.tmp.bed"
    geneAnno = f"{cnvDir}/{sampleID}.CNV.gene.tmp.bed"
    cnvBed = f"{cnvDir}/{sampleID}.CNV.tmp.bed"
    annotsvTsv = f"{annotDir}/{sampleID}.CNV.AnnotSV.tmp.tsv"
    inputTmp = f"{input}.bed"
    # input tmpfile for annotion
    cmd = f"cut -f 1-6 {input} > {inputTmp}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    # DGV
    cmd = f"{bedtools} intersect -a {inputTmp} -b {dgvBed} -s -wa -wb | {bedtools} overlap -i stdin -cols 2,3,8,9 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $13/($3-$2)>0.7' | {bedtools} groupby -i stdin -g 1-6 -c 7,8,9,10,11 -o collapse > {dgvAnno}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    # GnomAD
    cmd = f"{bedtools} intersect -a {inputTmp} -b {gnomadBed} -s -wa -wb | {bedtools} overlap -i stdin -cols 2,3,8,9 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $13/($3-$2)>0.7' | {bedtools} groupby -i stdin -g 1-6 -c 7,8,9,10,11 -o collapse > {gnomadAnno}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    # Local 作为致病数据库 
    cmd = f"{bedtools} intersect -a {inputTmp} -b {localCNVbed} -s -wa -wb | {bedtools} overlap -i stdin -cols 2,3,8,9 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $13/($9-$8)>0.7' | {bedtools} groupby -i stdin -g 1-6 -c 7,8,9,10,11 -o collapse > {localAnnoP}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    # Local 作为良性数据库 
    cmd = f"{bedtools} intersect -a {inputTmp} -b {localCNVbed} -s -wa -wb | {bedtools} overlap -i stdin -cols 2,3,8,9 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $13/($3-$2)>0.7' | {bedtools} groupby -i stdin -g 1-6 -c 7,8,9,10,11 -o collapse > {localAnnoB}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    # Local 作为检出数据库，结构相似即可
    cmd = f"{bedtools} intersect -a {inputTmp} -b {localCNVbed} -s -wa -wb | {bedtools} overlap -i stdin -cols 2,3,8,9 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $13/($3-$2)>0.7 && $13/($9-$8)>0.7' | {bedtools} groupby -i stdin -g 1-6 -c 7,8,9,10,11 -o collapse > {localAnnoV}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    # Decipher
    cmd = f"{bedtools} intersect -a {inputTmp} -b {decipherPatientBed} -s -wa -wb | {bedtools} overlap -i stdin -cols 2,3,8,9 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $13/($9-$8)>0.7' | {bedtools} groupby -i stdin -g 1-6 -c 7,8,9,10,11 -o collapse > {decipherPatientsAnno}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    # Start Exon/Intron
    cmd = f"cat {inputTmp} | awk -F'\t' 'BEGIN{{OFS=\"\t\"}}{{print $1,$2,$2}}' | {bedtools} intersect -a stdin -b {transcriptExonIntron} -wa -wb > {startExonIntron}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)

    # End Exon/Intron
    cmd = f"cat {inputTmp} | awk -F'\t' 'BEGIN{{OFS=\"\t\"}}{{print $1,$3,$3}}' | {bedtools} intersect -a stdin -b {transcriptExonIntron} -wa -wb > {endExonIntron}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)

    # Gene annotation
    cmd = f"{bedtools} intersect -a {inputTmp} -b {gene2MimNumBed} -wa -wb | {bedtools} groupby -i stdin -g 1-6 -c 10,11,12,13,14,15,16,17,18 -o collapse > {geneAnno}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)

    # Cytoband
    cmd = f"cat {inputTmp} | awk -F'\t' 'BEGIN{{OFS=\"\t\"}}{{print $1,$2,$2}}' | {bedtools} intersect -a stdin -b {cytobandBed} -wa -wb > {startCytobandAnno}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)

    cmd = f"cat {inputTmp} | awk -F'\t' 'BEGIN{{OFS=\"\t\"}}{{print $1,$3,$3}}' | {bedtools} intersect -a stdin -b {cytobandBed} -wa -wb > {endCytobandAnno}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)

    cmd = f"paste {startCytobandAnno} {endCytobandAnno} | awk -F'\t' 'BEGIN{{OFS=\"\t\"}}{{print $1,$2,$9,($7==$14?$1$7:$1$7$14)}}' > {cytobandAnno}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)

    # AnnotSV
    cmd = f"cat {inputTmp} | awk -F'\t' 'BEGIN{{OFS=\"\t\"}}{{print $1,$2,$3,($6==\"+\"?\"DUP\":\"DEL\"),$4,$5}}' > {cnvBed}"
    print("# " + cmd)
    subprocess.run(cmd, shell = True, check = True)
    cmd = f"{annotsv} -SVinputFile {cnvBed} -genomeBuild GRCh38 -outputFile {annotsvTsv} -annotationMode full -outputDir {annotDir}/ -svtBEDcol 4 -bcftools {bcftools} -bedtools {bedtools} -hpo {hpoIdList}"
    if hpoIdList == '':
        cmd = f"{annotsv} -SVinputFile {cnvBed} -genomeBuild GRCh38 -outputFile {annotsvTsv} -annotationMode full -outputDir {annotDir}/ -svtBEDcol 4 -bcftools {bcftools} -bedtools {bedtools}"
    print("# " + cmd)
    subprocess.run(cmd, shell=True, check=True)

    pedTitle = ['pedID', 'sampleID', 'dadID', 'momID', 'gender', 'status']
    gender = None

    if pedFile:
        with open(pedFile, 'r') as PED:
            for line in PED:
                arr = line.rstrip('\n').split('\t')
                h = dict(zip(pedTitle, arr))
                if h['sampleID'] == sampleID and h['status'] == '2':
                    if h['gender'] == '2':
                        gender = 'F'
                    if h['dadID'] != '0':
                        fatherBed = f"{cnvDir}/{h['dadID']}{basename}"
                        # cmd = f"{bedtools} annotate -s -i {inputTmp} -files {fatherBed} > {pa_bed}"
                        cmd = f"{bedtools} intersect -a {inputTmp} -b {fatherBed} -s -wa -wb | {bedtools} overlap -i stdin -cols 2,3,8,9 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $14/($3-$2)>0.7 && $14/($9-$8)>0.7' > {pa_bed}"
                        print(f"# {cmd}")
                        subprocess.run(cmd, shell = True, check = True)
                    if h['momID'] != '0':
                        motherBed = f"{cnvDir}/{h['momID']}{basename}"
                        # cmd = f"{bedtools} annotate -s -i {inputTmp} -files {motherBed} > {ma_bed}"
                        cmd = f"{bedtools} intersect -a {inputTmp} -b {motherBed} -s -wa -wb | {bedtools} overlap -i stdin -cols 2,3,8,9 | awk -F '\t' 'BEGIN{{OFS=\"\t\"}} $14/($3-$2)>0.7 && $14/($9-$8)>0.7' > {ma_bed}"
                        print(f"# {cmd}")
                        subprocess.run(cmd, shell = True, check = True)

    hash = defaultdict(dict)
    with open(cytobandAnno, 'r') as BAND:
        bands = BAND.readlines()
        bands = [band.strip() for band in bands]
    cnvTitle = ['Chr', 'Start', 'End', 'CN', 'zscore', 'Type', 'method']
    with open(input, 'r') as CNV:
        n = 0
        for region in CNV:
            arr = region.strip().split('\t')
            h = dict(zip(cnvTitle, arr))
            id = h['Chr'] + ":" + h['Start'] + "-" + h['End'] + ":" + h['Type']
            hash[id] = {
                "CN": h['CN'],
                "depth": h['zscore'],
                "start": h['Chr'] + ":" + h['Start'],
                "end": h['Chr'] + ":" + h['End'],
                "cytoband": bands[n].split('\t')[3],
                "method": h['method'],
                "start_exonIntron": '.',
                "end_exonIntron": '.',
                "phenotype": '',
                "diseaeCN": '',
                "inheritance": '',
                "gene": '',
                "phenotypeInfo": '',
                "imprint": '',
                "allGeneCount": '',
                "geneCount": '',
                "HI": '.',
                "TS": '.',
                "PLI": '.',
                "geneType": '',
                "DGV": '.',
                "gnomad": '.',
                "LocalSample": '.',
                "本地AC/AN": '.',
                "本地频率": '.',
                "LocalSample_P": '.',
                "本地AC/AN_P": '.',
                "本地频率_P": '.',
                "LocalSample_B": '.',
                "本地AC/AN_B": '.',
                "本地频率_B": '.',
                "patient": '.',
                "class": '',
                "rank": 0,
                "parent": '.',
                "syndrome": '.',
                "snv": '.'
            }
            n += 1
    # print(hash)
    
     # ========== 新增：批量 liftover 到 hg19 ==========
    # 收集所有CNV的坐标（此时hash已构建好）
    regions_for_lift = []
    for cnv_id, info in hash.items():
        # cnv_id 格式: "chr:start-end:type"
        # 需要解析出chrom, start, end
        m = re.match(r'(?:chr)?(\w+):(\d+)-(\d+):', cnv_id)
        if m:
            chrom = m.group(1)
            # 统一染色体格式
            if not chrom.startswith('chr'):
                chrom = 'chr' + chrom
            start = int(m.group(2))
            end = int(m.group(3))
            regions_for_lift.append((cnv_id, chrom, start, end))
        else:
            print(f"警告：无法解析 CNV ID: {cnv_id}")
    print(f"共收集 {len(regions_for_lift)} 个区域用于 liftover")
    # 调用 liftover
    liftover_cmd = args.liftover
    liftover_chain = tplDict["genome"]["hg38ToHg19Chain"]
    hg19_coord_map = liftover_cnv_to_hg19(regions_for_lift, liftover_cmd, liftover_chain, work_dir)
    
    # 将hg19坐标存入hash
    for cnv_id, hg19_str in hg19_coord_map.items():
        if cnv_id in hash:
            hash[cnv_id]['hg19_pos'] = hg19_str
    # ==============================================
    
    regionTitle = ['Chr', 'Start', 'End', 'chr', 'start', 'end', 'geneRegion']
    with open(startExonIntron, 'r') as START:
        for region in START:
            region = region.strip()
            arr = region.split('\t')
            h = {regionTitle[i]: arr[i] for i in range(len(arr))}
            startPos = h['Chr'] + ':' + h['Start']
            for id in hash.keys():
                if startPos == hash[id]['start']:
                    hash[id]['start_exonIntron'] = h['geneRegion']
                    break

    with open(endExonIntron, 'r') as END:
        for region in END:
            region = region.strip()
            arr = region.split('\t')
            h = {regionTitle[i]: arr[i] for i in range(len(arr))}
            endPos = h['Chr'] + ':' + h['Start']
            for id in hash.keys():
                if endPos == hash[id]['end']:
                    hash[id]['end_exonIntron'] = h['geneRegion']
                    break

    # read gene annotation info
    geneTitle = ['Chr', 'Start', 'End', 'CN', 'zscore', 'Type', 'omimGeneList', 'mimNumList', 'inheritance', 'phenotype', 'phenotypeCN', 'HI', 'PLI', 'imprint', 'geneType']
    with open(geneAnno, 'r') as GENEAN:
        for line in GENEAN:
            arr = line.strip().split('\t')
            h = dict(zip(geneTitle, arr))
            # id = h["Chr"] + "_" + h["Start"] + "_" + h["End"] + "_" + h["Type"]
            id = h["Chr"] + ":" + h["Start"] + "-" + h["End"] + ":" + h["Type"]
            arrGene = h['omimGeneList'].split(',')
            arrImprint = h['imprint'].split(',')
            arrGeneType = h['geneType'].split(',')
            plilist = []
            mimGeneCount = 0
            allGeneCount = 0

            hash[id]['phenotypeInfo'] = keyword_match(h['omimGeneList'], phenotypeList, hashPhenotype)
            if hash[id]['phenotypeInfo'] == '':
                keyword_count = 0
            else:
                keyword_count = len(hash[id]['phenotypeInfo'].split('|'))
            # print(id, " :", hash[id]['phenotypeInfo'], "  ", keyword_count)
            hash[id]['rank'] = 0
            if keyword_count > 0:
                hash[id]['rank'] = 10
            hash[id]['imprint'] = ''
            hilist = []
            tslist = []
            for i in range(len(arrGene)):
                if arrGene[i] in gene2HITS:
                    hilist.append(gene2HITS[arrGene[i]]['HI'])
                    if gene2HITS[arrGene[i]]['TS'] != 'Not yet evaluated':
                        tslist.append(gene2HITS[arrGene[i]]['TS'])
                if arrGene[i] in morbidmap_dict.keys():
                    mimGeneCount += 1
                    if hash[id]['gene'] != '':
                        hash[id]['gene'] += arrGene[i] + ' | '
                    else:
                        hash[id]['gene'] = arrGene[i] + ' | '
                if arrGene[i] in gene2disease_dict.keys():
                    if hash[id]['phenotype'] != '':
                        hash[id]['phenotype'] += gene2disease_dict[arrGene[i]]['gene2DiseaseEN'] + ' | '
                    else:
                        hash[id]['phenotype'] = gene2disease_dict[arrGene[i]]['gene2DiseaseEN'] + ' | '
                    if hash[id]['diseaeCN'] != '':
                        hash[id]['diseaeCN'] += gene2disease_dict[arrGene[i]]['gene2DiseaseCN'] + ' | '
                    else:
                        hash[id]['diseaeCN'] = gene2disease_dict[arrGene[i]]['gene2DiseaseCN'] + ' | '
                    if hash[id]['inheritance'] != '':
                        hash[id]['inheritance'] = hash[id]['inheritance'] + ' | ' + gene2disease_dict[arrGene[i]]['Inheritance']
                    else:
                        hash[id]['inheritance'] = gene2disease_dict[arrGene[i]]['Inheritance']
                if arrGeneType[i] == 'protein-coding' or arrGene[i] in morbidmap_dict.keys():
                    allGeneCount += 1
                if arrImprint[i] != '.':
                    hash[id]['imprint'] = arrGene[i] + '(' + arrImprint[i] + ') | '
            himax_value = maxValue(hilist)
            tsmax_value = maxValue(tslist)
            hash[id]['HI'] = str(himax_value)
            hash[id]['TS'] = str(tsmax_value)
            hash[id]['phenotype'] = hash[id]['phenotype'].rstrip(' | ')
            hash[id]['diseaeCN'] = hash[id]['diseaeCN'].rstrip(' | ')
            hash[id]['phenotype'] = hash[id]['phenotype'].replace('.(..:.) ', '')
            hash[id]['diseaeCN'] = hash[id]['diseaeCN'].replace('.(..:.) ', '')

            if not re.search(r'\d', hash[id]['phenotype']):
                hash[id]['phenotype'] = '.'
                hash[id]['diseaeCN'] = '.'

            # inheritance = set(hash[id]['inheritance'].split('|'))
            inheritance = hash[id]['inheritance'].lstrip("|").replace('.|', '').replace('|.', '')
            # hash[id]['inheritance'] = ('|'.join(inheritance)).lstrip("|")
            # hash[id]['inheritance'] = hash[id]['inheritance'].replace('.|', '')
            # hash[id]['inheritance'] = hash[id]['inheritance'].replace('|.', '')
            # hash[id]['inheritance'] = '.' if hash[id]['inheritance'] == '' else hash[id]['inheritance']
            hash[id]['inheritance'] = '.' if inheritance == '' else inheritance

            hash[id]['gene'] = hash[id]['gene'].rstrip(' | ')
            hash[id]['geneCount'] = mimGeneCount
            hash[id]['allGeneCount'] = allGeneCount
            # hash[id]['HI'] = h['HI']
            plilist = h['PLI'].split(',')
            lst_without_commas = [x for x in plilist if x != ',']
            max_value = max(lst_without_commas)  # 取出最大值
            hash[id]['PLI'] = str(max_value)
            hash[id]['imprint'] = hash[id]['imprint'].rstrip(' | ')
            hash[id]['geneType'] = h['geneType']
    # read DGV  annotation info
    dbTitle = ['Chr', 'Start', 'End', 'CN', 'zscore', 'Type', 'chrList', 'startList', 'endList', 'dbID', 'freq']
    with open(dgvAnno, 'r') as DGVAnno:
        for region in DGVAnno:
            region = region.strip()
            arr = region.split('\t')
            h = {dbTitle[i]: arr[i] for i in range(len(arr))}
            id = h['Chr'] + ':' + h['Start'] + '-' + h['End'] + ':' + h['Type']
            chrs = h['chrList'].split(',')
            starts = h['startList'].split(',')
            ends = h['endList'].split(',')
            dgvIDs = h['dbID'].split(',')
            freqs = h['freq'].split(',')
            dgv_info = ''
            for i in range(len(chrs)):
                dgv_info += freqs[i] + '(' + dgvIDs[i] + '=chr' + chrs[i] + ':' + starts[i] + '-' + ends[i] + ');'
            dgv_info = dgv_info.rstrip(';')
            hash[id]['DGV'] = dgv_info

    # read gnomad annotation info
    with open(gnomadAnno, 'r') as GNOMADAnno:
        for region in GNOMADAnno:
            region = region.strip()
            arr = region.split('\t')
            h = {dbTitle[i]: arr[i] for i in range(len(arr))}
            id = h['Chr'] + ':' + h['Start'] + '-' + h['End'] + ':' + h['Type']
            chrs = h['chrList'].split(',')
            starts = h['startList'].split(',')
            ends = h['endList'].split(',')
            gnomadIDs = h['dbID'].split(',')
            freqs = h['freq'].split(',')
            gnomadInfo = ''
            for i in range(len(chrs)):
                gnomadInfo += freqs[i] + '(' + gnomadIDs[i] + '=chr' + chrs[i] + ':' + starts[i] + '-' + ends[i] + ');'
            gnomadInfo = gnomadInfo.rstrip(';')
            hash[id]['gnomad'] = gnomadInfo

    LocalSampleInfo = getLocalSample(localCNVsamplebed)
    # read Local annotation info
    dbTitle = ['Chr', 'Start', 'End', 'CN', 'zscore', 'Type', 'chrList', 'startList', 'endList', 'CNVType', 'freq']
    with open(localAnnoP, 'r') as LOCALAnnoP:
        for region in LOCALAnnoP:
            local_sample_CNVseq,local_sample_Lumpy,ACAN_CNVseq,ACAN_Lumpy,freq_CNVseq,freq_Lumpy,id = localCNVanno(region,LocalSampleInfo)
            hash[id]['LocalSample_P'] = f'{local_sample_CNVseq};{local_sample_Lumpy}'
            hash[id]['本地AC/AN_P'] = f'{ACAN_CNVseq};{ACAN_Lumpy}'
            hash[id]['本地频率_P'] = f'{freq_CNVseq};{freq_Lumpy}'
    with open(localAnnoB, 'r') as LOCALAnnoB:
        for region in LOCALAnnoB:
            local_sample_CNVseq,local_sample_Lumpy,ACAN_CNVseq,ACAN_Lumpy,freq_CNVseq,freq_Lumpy,id = localCNVanno(region,LocalSampleInfo)
            hash[id]['LocalSample_B'] = f'{local_sample_CNVseq};{local_sample_Lumpy}'
            hash[id]['本地AC/AN_B'] = f'{ACAN_CNVseq};{ACAN_Lumpy}'
            hash[id]['本地频率_B'] = f'{freq_CNVseq};{freq_Lumpy}'
    with open(localAnnoV, 'r') as LOCALAnnoV:
        for region in LOCALAnnoV:
            local_sample_CNVseq,local_sample_Lumpy,ACAN_CNVseq,ACAN_Lumpy,freq_CNVseq,freq_Lumpy,id = localCNVanno(region,LocalSampleInfo)
            hash[id]['LocalSample'] = f'{local_sample_CNVseq};{local_sample_Lumpy}'
            hash[id]['本地AC/AN'] = f'{ACAN_CNVseq};{ACAN_Lumpy}'
            hash[id]['本地频率'] = f'{freq_CNVseq};{freq_Lumpy}'

    # read decipher annotation info
    decipherTitle = ['Chr', 'Start', 'End', 'CN', 'zscore', 'Type', 'chrList', 'startList', 'endList', 'phenotype', 'significance/syndrome']
    with open(decipherPatientsAnno, 'r') as decipherSAnno:
        for region in decipherSAnno:
            region = region.strip()
            arr = region.split('\t')
            h = {decipherTitle[i]: arr[i] for i in range(len(arr))}
            id = h['Chr'] + ':' + h['Start'] + '-' + h['End'] + ':' + h['Type']
            hash[id]['patient'] = ''
            chrs = h['chrList'].split(',')
            starts = h['startList'].split(',')
            ends = h['endList'].split(',')
            decipherPhenotypes = h['phenotype'].split(',')
            sigs = h['significance/syndrome'].split(',')

            P_count, LP_count, VUS_count, B_count, LB_count = 0, 0, 0, 0, 0
            P_phenotype, LP_phenotype, VUS_phenotype, B_phenotype, LB_phenotype, syndrome, patientInfo = '', '', '', '', '', '.', ''

            for i in range(len(chrs)):
                if 'Pathogenic' in sigs[i]:
                    P_count += 1
                    P_phenotype += decipherPhenotypes[i] + '; '
                elif 'pathogenic' in sigs[i]:
                    LP_count += 1
                    LP_phenotype += decipherPhenotypes[i] + '; '
                elif 'Benign' in sigs[i]:
                    B_count += 1
                    B_phenotype += decipherPhenotypes[i] + '; '
                elif 'benign' in sigs[i]:
                    LB_count += 1
                    LB_phenotype += decipherPhenotypes[i] + '; '
                elif 'Unknown' in sigs[i] or 'Uncertain' in sigs[i]:
                    VUS_count += 1
                    VUS_phenotype += decipherPhenotypes[i] + '; '
                else:
                    syndrome += sigs[i] + '(' + chrs[i] + ':' + starts[i] + '-' + ends[i] + ')' + decipherPhenotypes[i] + '; '

            P_phenotype = P_phenotype.rstrip('; ')
            LP_phenotype = LP_phenotype.rstrip('; ')
            B_phenotype = B_phenotype.rstrip('; ')
            LB_phenotype = LB_phenotype.rstrip('; ')
            VUS_phenotype = VUS_phenotype.rstrip('; ')
            syndrome = syndrome.rstrip('; ')

            patientInfo = syndrome + ' | ' + 'P:' + str(P_count) + ':' + P_phenotype + ' | ' + 'LP:' + str(LP_count) + ':' + LP_phenotype + ' | ' + 'VUS:' + str(
                VUS_count) + ':' + VUS_phenotype + ' | ' + 'LB:' + str(LB_count) + ':' + LB_phenotype + ' | ' + 'B:' + str(B_count) + ':' + B_phenotype
            patientInfo = patientInfo.replace('&_', ', ')
            hash[id]['patient'] = patientInfo

    # read annotSV annotation info
    with open(annotsvTsv, 'r') as annot:
        next(annot)
        for region in annot:
            arr = region.strip().split("\t")
            arr[5] = arr[5].replace("DUP", "+")
            arr[5] = arr[5].replace("DEL", "-")
            id_ = str(arr[1]) + ':' + str(int(arr[2]) - 1) + '-' + str(arr[3]) + ':' + arr[5]
            hash[id_]["class"] = arr[-1]
            if hash[id_]["class"] == "5":
                hash[id_]["rank"] += 50
            elif hash[id_]["class"] == "4":
                hash[id_]["rank"] += 40
            elif hash[id_]["class"] == "3":
                hash[id_]["rank"] += 3
            elif hash[id_]["class"] == "2":
                hash[id_]["rank"] += 2
            elif hash[id_]["class"] == "1":
                hash[id_]["rank"] += 1
    # read patient info
    parentTitle = ['Chr', 'Start', 'End', 'CN', 'zscore', 'Type', 'Chrp', 'Startp', 'Endp', 'CNp', 'zscorep', 'Typep', 'method', 'overlaplen']
    if os.path.exists(pa_bed):
        with open(pa_bed, 'r') as PABED:
            for region in PABED:
                region = region.strip()
                arr = region.split('\t')
                h = {parentTitle[i]: arr[i] for i in range(len(arr))}
                id = h['Chr'] + ':' + h['Start'] + '-' + h['End'] + ':' + h['Type']
                if hash[id]['method'] == h['method']:
                    if hash[id]['parent'] == '.':
                        hash[id]['parent'] = 'Paternal;'
                    elif 'Paternal' not in hash[id]['parent']:
                        hash[id]['parent'] += 'Paternal;'

    if os.path.exists(ma_bed):
        with open(ma_bed, 'r') as MABED:
            for region in MABED:
                region = region.strip()
                arr = region.split('\t')
                h = {parentTitle[i]: arr[i] for i in range(len(arr))}
                id = h['Chr'] + ':' + h['Start'] + '-' + h['End'] + ':' + h['Type']
                if hash[id]['method'] == h['method']:
                    if hash[id]['parent'] == '.':
                        hash[id]['parent'] = 'Maternal;'
                    elif 'Maternal' not in hash[id]['parent']:
                        hash[id]['parent'] += 'Maternal;'

    for id in sorted(hash.keys()):
        chr, start, end, type = re.match(r'(.*?):(\d+)-(\d+):(.*)', id).groups()
        type = type.replace('+', 'DUP')
        type = type.replace('-', 'DEL')
        if gender == 'F' and chr == 'Y':
            continue
        length = int(end) - int(start) + 1
        # if length >= 1000000:
        #     length = '{:.2f}Mb'.format(length / 1000000)
        # elif length >= 1000:
        #     length = '{:.2f}Kb'.format(length / 1000)
        # else:
        #     length = '{}bp'.format(length)

        if hash[id]['start_exonIntron'] == hash[id]['end_exonIntron']:
            exon_intron = hash[id]['start_exonIntron']
        else:
            exon_intron = hash[id]['start_exonIntron'] + '_' + hash[id]['end_exonIntron']
        exon_intron = re.sub(r'^_$', '', exon_intron)
        if 'class' in hash[id]:
            source = hash[id]['parent']
            if hash[id]['parent'] != '.':
                source = hash[id]['parent'].rstrip(';')
            localACAN = '.'
            localFreq = '.'
            localSample = '.'
            localACANP = '.'
            localFreqP = '.'
            localSampleP = '.'
            localACANB = '.'
            localFreqB = '.'
            localSampleB = '.'
            if hash[id]['本地AC/AN'] != '.' and hash[id]['method'] == "CNVseq":
                localACAN = hash[id]['本地AC/AN'].split(';')[0]
            elif hash[id]['本地AC/AN'] != '.' and hash[id]['method'] == "Lumpy":
                localACAN = hash[id]['本地AC/AN'].split(';')[1]
            if hash[id]['本地频率'] != '.' and hash[id]['method'] == "CNVseq":
                localFreq = hash[id]['本地频率'].split(';')[0]
            elif hash[id]['本地频率'] != '.' and hash[id]['method'] == "Lumpy":
                localFreq = hash[id]['本地频率'].split(';')[1]
            if hash[id]['LocalSample'] != '.' and hash[id]['method'] == "CNVseq":
                localSample = hash[id]['LocalSample'].split(';')[0]
            elif hash[id]['LocalSample'] != '.' and hash[id]['method'] == "Lumpy":
                localSample = hash[id]['LocalSample'].split(';')[1]
            if hash[id]['本地AC/AN_P'] != '.' and hash[id]['method'] == "CNVseq":
                localACANP = hash[id]['本地AC/AN_P'].split(';')[0]
            elif hash[id]['本地AC/AN_P'] != '.' and hash[id]['method'] == "Lumpy":
                localACANP = hash[id]['本地AC/AN_P'].split(';')[1]
            if hash[id]['本地频率_P'] != '.' and hash[id]['method'] == "CNVseq":
                localFreqP = hash[id]['本地频率_P'].split(';')[0]
            elif hash[id]['本地频率_P'] != '.' and hash[id]['method'] == "Lumpy":
                localFreqP = hash[id]['本地频率_P'].split(';')[1]
            if hash[id]['LocalSample_P'] != '.' and hash[id]['method'] == "CNVseq":
                localSampleP = hash[id]['LocalSample_P'].split(';')[0]
            elif hash[id]['LocalSample_P'] != '.' and hash[id]['method'] == "Lumpy":
                localSampleP = hash[id]['LocalSample_P'].split(';')[1]
            if hash[id]['本地AC/AN_B'] != '.' and hash[id]['method'] == "CNVseq":
                localACANB = hash[id]['本地AC/AN_B'].split(';')[0]
            elif hash[id]['本地AC/AN_B'] != '.' and hash[id]['method'] == "Lumpy":
                localACANB = hash[id]['本地AC/AN_B'].split(';')[1]
            if hash[id]['本地频率_B'] != '.' and hash[id]['method'] == "CNVseq":
                localFreqB = hash[id]['本地频率_B'].split(';')[0]
            elif hash[id]['本地频率_B'] != '.' and hash[id]['method'] == "Lumpy":
                localFreqB = hash[id]['本地频率_B'].split(';')[1]
            if hash[id]['LocalSample_B'] != '.' and hash[id]['method'] == "CNVseq":
                localSampleB = hash[id]['LocalSample_B'].split(';')[0]
            elif hash[id]['LocalSample_B'] != '.' and hash[id]['method'] == "Lumpy":
                localSampleB = hash[id]['LocalSample_B'].split(';')[1]
            
            tmp_file.write('{}\t{}\t{}\t{}\t{}\t{}\tchr{}:{}-{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(
                hash[id]['rank'], '', '', '', hash[id]['class'], hash[id]['phenotypeInfo'], chr, start, end, hash[id].get('hg19_pos', ''), type,
                hash[id]['cytoband'], length, hash[id]['CN'], source, localACAN, localFreq, localSample, localACANP, localFreqP, localSampleP,
                localACANB, localFreqB, localSampleB, hash[id]['DGV'], hash[id]['gnomad'], hash[id]['patient'], hash[id]['snv'],
                hash[id]['allGeneCount'], hash[id]['geneCount'], hash[id]['gene'], hash[id]['phenotype'], hash[id]['diseaeCN'],
                hash[id]['inheritance'], exon_intron, hash[id]['imprint'], hash[id]['HI'], hash[id]['TS'], hash[id]['PLI'], hash[id]['method']))

    tmp_file.close()
    os.system("{ head -n 1 " + tmp_output + ";  tail -n +2 " + tmp_output + "|sort -k1nr; } |cut -f 2-38 >" + output)
    dropfile(tmp_output, pa_bed, dgvAnno, gnomadAnno, localAnnoB, localAnnoP, localAnnoV, decipherPatientsAnno, decipherSyndromeAnno, startExonIntron, endExonIntron, startCytobandAnno, endCytobandAnno, cytobandAnno, geneAnno, cnvBed,annotsvTsv)
    os.rmdir(annotDir)
