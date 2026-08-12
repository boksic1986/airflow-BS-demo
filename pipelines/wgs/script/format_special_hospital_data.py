#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
format_special.py - 处理特殊医院数据格式化
支持医院: SHEY, BKW, SDSZ, BJXH, SHHC
用法: python format_special.py --hospital <HOSP> --batch BATCH --sourcePath PATH --sampleinfo FILE --config FILE
"""

import os, sys, glob, argparse, yaml, re
import pandas as pd
from collections import defaultdict

# ---------- 上海儿科医学研究所 ----------
def format_SHEY(sample_list, sampleinfo_df, source_path, batch_split,
                all_pedigrees, pedigree2sample, pedigreelist, coupleList,
                trio2proband, mtPedigreeList, fastqPath, samtoolsPath,
                genome, bgzip, tabix):
    SHEYbatchPath = os.path.join(source_path, batch_split + '_ShanghaiErkeYanjiusuo')
    os.makedirs(SHEYbatchPath, exist_ok=True)
    os.makedirs(os.path.join(SHEYbatchPath, 'Bam'), exist_ok=True)
    os.makedirs(os.path.join(SHEYbatchPath, 'Fastq'), exist_ok=True)
    os.makedirs(os.path.join(SHEYbatchPath, 'Result'), exist_ok=True)

    # ---------- 新增：打开 BAM 和 MD5 脚本文件 ----------
    SHEY_bam_sh = os.path.join(source_path, "ShanghaiErkeYanjiusuo_bam.sh")
    SHEY_bam = open(SHEY_bam_sh, 'w')
    SHEY_md5_sh = os.path.join(source_path, "ShanghaiErkeYanjiusuo_md5.sh")
    SHEY_md5 = open(SHEY_md5_sh, 'w')
    # --------------------------------------------------

    sample2barcode = dict(zip(sampleinfo_df['样本编号'], sampleinfo_df['医院条码号']))
    data2barcode = dict(zip(sampleinfo_df['数据编号'], sampleinfo_df['医院条码号']))
    family2barcode = dict(zip(sampleinfo_df[sampleinfo_df['家系关系']=='先证者']['家系编号'],
                             'JX'+sampleinfo_df[sampleinfo_df['家系关系']=='先证者']['医院条码号']))

    df_out = sampleinfo_df[sampleinfo_df['数据编号'].isin(sample_list)][['医院条码号','家系编号','家系名','姓名']]
    df_out.rename(columns={'医院条码号':'样本编号'}, inplace=True)
    df_out['家系编号'] = df_out['家系编号'].map(family2barcode)
    df_out.to_csv(os.path.join(SHEYbatchPath, f'{batch_split}_data.sample.txt'), sep='\t', index=False)

    SNVcols_to_drop = ['Variant_Priority_Group','inheritanceScore','pathogenicityScore','mafScore','keyWordScore','qualScore']
    CScols_to_drop = ['Variant_Priority_Group','CS_Class','inheritanceScore','pathogenicityScore','mafScore','keyWordScore','qualScore']
    CNVcols_to_drop = ['本地AC/AN','本地频率','LocalSample','本地AC/AN_P','本地频率_P','LocalSample_P','本地AC/AN_B','本地频率_B','LocalSample_B']
    SVcols_to_drop = ['本地AC/AN','本地频率','LocalInfo']

    for value in all_pedigrees:
        if value not in sample_list: continue
        sampleID = value.split('_')[1].replace('-WGS','')
        jxPath = os.path.join(SHEYbatchPath, 'Result', 'JX' + sample2barcode.get(sampleID, ''))
        os.makedirs(jxPath, exist_ok=True)
        jxName = 'JX' + sample2barcode.get(sampleID, '') + '_' + sample2barcode.get(sampleID, '')
        if value in pedigreelist:
            df = pd.read_csv(os.path.join(source_path, '01_SNV', value+'.flt.tsv'), sep='\t', on_bad_lines='skip')
            df.drop(columns=SNVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, jxName+'.flt.tsv'), sep='\t', index=False)
        if value in coupleList:
            df = pd.read_csv(os.path.join(source_path, '01_SNV', value+'.markCS.flt.tsv'), sep='\t', on_bad_lines='skip')
            df.drop(columns=CScols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, jxName+'.markCS.flt.tsv'), sep='\t', index=False)
            if os.path.exists(os.path.join(source_path, '01_SNV', value+'_1.markCS.flt.tsv')):
                df1 = pd.read_csv(os.path.join(source_path, '01_SNV', value+'_1.markCS.flt.tsv'), sep='\t', on_bad_lines='skip')
                df1.drop(columns=CScols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, jxName+'_1.markCS.flt.tsv'), sep='\t', index=False)
        if value in trio2proband:
            os.system(f'cp {source_path}/10_MIE/{value}.trio.MIE.png {jxPath}/{jxName}.trio.MIE.png')
        if value in mtPedigreeList:
            os.system(f'cp {source_path}/11_MT/{value}.mity.flt.txt {jxPath}/{jxName}.mity.flt.txt')

        for sample in pedigree2sample.get(value, []):
            if sample not in sample_list: continue
            dataName = data2barcode.get(sample, '') + '-WGS'
            sampleName = data2barcode.get(sample, '')
            os.system(f'cp {source_path}/03_CNV/SMA/{sample}.SMA.tsv {jxPath}/{dataName}.SMA.tsv')
            os.system(f'sed -i "s/{sample}/{sampleName}/g" {jxPath}/{dataName}.SMA.tsv')
            df_cnv = pd.read_csv(os.path.join(source_path, '03_CNV/Annot', sample+'.CNV.tsv'), sep='\t', on_bad_lines='skip')
            df_cnv.drop(columns=CNVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, dataName+'.CNV.tsv'), sep='\t', index=False)
            df_sv = pd.read_csv(os.path.join(source_path, '04_SV/c.sort', sample+'.SV.sort.tsv'), sep='\t', on_bad_lines='skip')
            df_sv.drop(columns=SVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, dataName+'.SV.tsv'), sep='\t', index=False)
            os.system(f'cp {source_path}/06_STR/{sample}.expansionHunter.tsv {jxPath}/{dataName}.expansionHunter.tsv')
            os.system(f'cp {source_path}/05_ROH/{sample}.HomRegions.tsv {jxPath}/{dataName}.HomRegions.tsv')
            os.system(f'cp {source_path}/09_MEI/{sample}.MEIs.tsv {jxPath}/{dataName}.MEIs.tsv')
            os.system(f'sed -i "s/{sample}/{sampleName}/g" {jxPath}/{dataName}.MEIs.tsv')
            qc = pd.read_csv(os.path.join(source_path, '07_QC', sample+'.QC.tsv'), sep='\t')
            qc = qc[['Name','Sample_ID','Raw_reads','Clean_reads','Raw_bases','Clean_bases','Raw_Q30%','Clean_Q30%','Raw_GC%','Clean_GC%','Duplicated_reads','Duplicated_reads%','Mapped_Reads','Mapped_Reads%','Unique_Mapped_Reads','Unique_Mapped_Reads%','Average_Depth','>=1X','>=20X','MT_Average_Depth']]
            qc['Sample_ID'] = qc['Sample_ID'].map(data2barcode)
            qc.to_csv(os.path.join(jxPath, dataName+'.QC.tsv'), sep='\t', index=False)
            os.system(f'cp {source_path}/11_MT/{sample}.mity.flt.txt {jxPath}/{dataName}.mity.flt.txt')
            df_flt = pd.read_csv(os.path.join(source_path, '01_SNV', sample+'.flt.tsv'), sep='\t', on_bad_lines='skip')
            df_flt.drop(columns=SNVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, dataName+'.flt.tsv'), sep='\t', index=False)
            df_verbose = pd.read_csv(os.path.join(source_path, '01_SNV', sample+'.verbose.tsv'), sep='\t', on_bad_lines='skip')
            df_verbose.drop(columns=SNVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, dataName+'.verbose.tsv'), sep='\t', index=False)
            os.system(f'zcat {source_path}/01_SNV/{sample}.raw.vcf.gz | grep -v -P "Command|bcftools" | sed "s/{sample}/{dataName}/g" | {bgzip} -c > {jxPath}/{dataName}.raw.vcf.gz && {tabix} -fp vcf {jxPath}/{dataName}.raw.vcf.gz')

            # ---------- 替换直接执行为写入脚本文件 ----------
            bam_dir = os.path.join(SHEYbatchPath, 'Bam')
            # 写入 BAM 转换命令
            print(f'{samtoolsPath}/samtools view -b -T {genome} -@8 -o {bam_dir}/{dataName}.bam {source_path}/00_PreCalling/{sample}.deduped.cram && {samtoolsPath}/samtools index -b -@8 {bam_dir}/{dataName}.bam', file=SHEY_bam)
            # --------------------------------------------------

            sampleID_j = sample.replace('-WGS','')
            fastq_dir = os.path.join(SHEYbatchPath, 'Fastq')
            fastqs = glob.glob(f'{fastqPath}/*/*{sampleID_j}*-WGS.*.fq.gz')
            for fq in fastqs:
                if '.R1.fq.gz' in fq:
                    os.symlink(fq, os.path.join(fastq_dir, dataName+'.R1.fq.gz'))
                elif '.R2.fq.gz' in fq:
                    os.symlink(fq, os.path.join(fastq_dir, dataName+'.R2.fq.gz'))
            # 写入 MD5 校验命令
            print(f'md5sum {fastq_dir}/{dataName}.R1.fq.gz > {fastq_dir}/{dataName}.R1.fq.gz.md5', file=SHEY_md5)
            print(f'md5sum {fastq_dir}/{dataName}.R2.fq.gz > {fastq_dir}/{dataName}.R2.fq.gz.md5', file=SHEY_md5)
            # --------------------------------------------------

    # ---------- 关闭 BAM 和 MD5 脚本文件 ----------
    SHEY_bam.close()
    SHEY_md5.close()
    # ----------------------------------------------

# ---------- 北京金域 ----------
def format_BKW(sample_list, sampleinfo_df, source_path, all_pedigrees, pedigree2sample,
               pedigreelist, coupleList, trio2proband, mtPedigreeList, fastqPath,
               samtoolsPath, genome, bgzip, tabix, batch_split):
    BKWbatchPath = os.path.join(source_path, 'BJJY')
    os.makedirs(BKWbatchPath, exist_ok=True)
    df_BKW = sampleinfo_df[sampleinfo_df['数据编号'].isin(sample_list)]
    df_BKW = df_BKW[['医院条码号','家系编号','家系名','姓名']]
    df_BKW.rename(columns={'医院条码号':'数据编号'}, inplace=True)
    bkw_file = os.path.join(source_path, 'BJJY', f'{batch_split}_data.sampleinfo.tsv')
    df_BKW.to_csv(bkw_file, sep='\t', index=False)

    sample2barcode = dict(zip(sampleinfo_df['样本编号'], sampleinfo_df['医院条码号']))
    data2barcode = dict(zip(sampleinfo_df['数据编号'], sampleinfo_df['医院条码号']))
    family2barcode = dict(zip(sampleinfo_df[sampleinfo_df['家系关系']=='先证者']['家系编号'],
                             'JX'+sampleinfo_df[sampleinfo_df['家系关系']=='先证者']['医院条码号']))

    # BKW 专用删除列
    SNVcols_to_drop = ['Variant_Priority_Group','Synopsis_CN','Pathogenicity','Evidence_List','Evidence','inheritanceScore','pathogenicityScore','mafScore','keyWordScore','qualScore']
    CScols_to_drop = ['Variant_Priority_Group','CS_Class', 'Synopsis_CN', 'Pathogenicity','Evidence_List','Evidence','inheritanceScore','pathogenicityScore','mafScore','keyWordScore','qualScore']
    CNVcols_to_drop = ['本地AC/AN','本地频率','LocalSample','本地AC/AN_P','本地频率_P','LocalSample_P','本地AC/AN_B','本地频率_B','LocalSample_B']
    SVcols_to_drop = ['本地AC/AN','本地频率','LocalInfo']

    for value in all_pedigrees:
        if value not in sample_list: continue
        sampleID = value.split('_')[1].replace('-WGS','')
        jxPath = os.path.join(BKWbatchPath, sample2barcode.get(sampleID, ''))
        os.makedirs(jxPath, exist_ok=True)
        jxName = value.split('_')[0] + '_' + sample2barcode.get(sampleID, '')

        if value in pedigreelist:
            dfflt = pd.read_csv(os.path.join(source_path, '01_SNV', value+'.flt.tsv'), sep='\t', on_bad_lines='skip')
            dfflt.drop(columns=SNVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, jxName+'.flt.tsv'), sep='\t', index=False)
            dfverbose = pd.read_csv(os.path.join(source_path, '01_SNV', value+'.verbose.tsv'), sep='\t', on_bad_lines='skip')
            dfverbose.drop(columns=SNVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, jxName+'.verbose.tsv'), sep='\t', index=False)
        if value in coupleList:
            dfflt = pd.read_csv(os.path.join(source_path, '01_SNV', value+'.markCS.flt.tsv'), sep='\t', on_bad_lines='skip')
            dfflt.drop(columns=CScols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, jxName+'.markCS.flt.tsv'), sep='\t', index=False)
            if os.path.exists(os.path.join(source_path, '01_SNV', value+'_1.markCS.flt.tsv')):
                dfflt1 = pd.read_csv(os.path.join(source_path, '01_SNV', value+'_1.markCS.flt.tsv'), sep='\t', on_bad_lines='skip')
                dfflt1.drop(columns=CScols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, jxName+'_1.markCS.flt.tsv'), sep='\t', index=False)
            dfverbose = pd.read_csv(os.path.join(source_path, '01_SNV', value+'.markCS.verbose.tsv'), sep='\t', on_bad_lines='skip')
            dfverbose.drop(columns=CScols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, jxName+'.markCS.verbose.tsv'), sep='\t', index=False)
            if os.path.exists(os.path.join(source_path, '01_SNV', value+'_1.markCS.verbose.tsv')):
                dfverbose1 = pd.read_csv(os.path.join(source_path, '01_SNV', value+'_1.markCS.verbose.tsv'), sep='\t', on_bad_lines='skip')
                dfverbose1.drop(columns=CScols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, jxName+'_1.markCS.verbose.tsv'), sep='\t', index=False)
        if value in trio2proband:
            os.system(f'cp {source_path}/10_MIE/{value}.trio.MIE.png {jxPath}/{jxName}.trio.MIE.png')
        if value in mtPedigreeList:
            os.system(f'cp {source_path}/11_MT/{value}.mity.flt.txt {jxPath}/{jxName}.mity.flt.txt')

        for sample in pedigree2sample.get(value, []):
            if sample not in sample_list: continue
            dataName = data2barcode.get(sample, '') + '-WGS'
            sampleName = data2barcode.get(sample, '')
            os.system(f'cp {source_path}/03_CNV/SMA/{sample}.SMA.tsv {jxPath}/{dataName}.SMA.tsv')
            os.system(f'sed -i "s/{sample}/{sampleName}/g" {jxPath}/{dataName}.SMA.tsv')
            df_cnv = pd.read_csv(os.path.join(source_path, '03_CNV/Annot', sample+'.CNV.tsv'), sep='\t', on_bad_lines='skip')
            df_cnv.drop(columns=CNVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, dataName+'.CNV.tsv'), sep='\t', index=False)
            df_sv = pd.read_csv(os.path.join(source_path, '04_SV/c.sort', sample+'.SV.sort.tsv'), sep='\t', on_bad_lines='skip')
            df_sv.drop(columns=SVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, dataName+'.SV.tsv'), sep='\t', index=False)
            os.system(f'cp {source_path}/06_STR/{sample}.expansionHunter.tsv {jxPath}/{dataName}.expansionHunter.tsv')
            os.system(f'cp {source_path}/05_ROH/{sample}.HomRegions.tsv {jxPath}/{dataName}.HomRegions.tsv')
            os.system(f'cp {source_path}/09_MEI/{sample}.MEIs.tsv {jxPath}/{dataName}.MEIs.tsv')
            os.system(f'sed -i "s/{sample}/{sampleName}/g" {jxPath}/{dataName}.MEIs.tsv')
            qc = pd.read_csv(os.path.join(source_path, '07_QC', sample+'.QC.tsv'), sep='\t')
            qc = qc[['Name', 'Sample_ID', 'Raw_reads', 'Clean_reads', 'Raw_bases', 'Clean_bases', 'Raw_Q30%', 'Clean_Q30%', 'Raw_GC%', 'Clean_GC%', 'Average_Depth']]
            qc['Sample_ID'] = qc['Sample_ID'].map(data2barcode)
            qc.to_csv(os.path.join(jxPath, dataName+'.QC.tsv'), sep='\t', index=False)
            os.system(f'cp {source_path}/11_MT/{sample}.mity.flt.txt {jxPath}/{dataName}.mity.flt.txt')
            df_flt = pd.read_csv(os.path.join(source_path, '01_SNV', sample+'.flt.tsv'), sep='\t', on_bad_lines='skip')
            df_flt.drop(columns=SNVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, dataName+'.flt.tsv'), sep='\t', index=False)
            df_verbose = pd.read_csv(os.path.join(source_path, '01_SNV', sample+'.verbose.tsv'), sep='\t', on_bad_lines='skip')
            df_verbose.drop(columns=SNVcols_to_drop, errors='ignore').to_csv(os.path.join(jxPath, dataName+'.verbose.tsv'), sep='\t', index=False)
            os.system(f'zcat {source_path}/01_SNV/{sample}.raw.vcf.gz | grep -v -P "Command|bcftools" | sed "s/{sample}/{dataName}/g" | {bgzip} -c > {jxPath}/{dataName}.raw.vcf.gz && {tabix} -fp vcf {jxPath}/{dataName}.raw.vcf.gz')
            sampleID_j = sample.replace('-WGS','')
            BKWfastq = glob.glob(f"{fastqPath}/*/*{sampleID_j}*-WGS.*.fq.gz")
            BKWfastq = list(set(BKWfastq))
            if len(BKWfastq)>1:
                for fastq_file in BKWfastq:
                    if ".R1.fq.gz" in os.path.basename(fastq_file):
                        link_name = os.path.join(jxPath, dataName + ".R1.fq.gz")
                    if ".R2.fq.gz" in os.path.basename(fastq_file):
                        link_name = os.path.join(jxPath, dataName + ".R2.fq.gz")
                    os.system(f"ln -s -f {fastq_file} {link_name}")
                    md5_file = link_name + ".md5"
                    if not os.path.exists(md5_file):
                        # print(f"md5sum {link_name} > {md5_file}")
                        os.system(f"md5sum {link_name} > {md5_file}")
            else:
                print(f"{sampleID_j}'s fastq not fount")

# ---------- 山大生殖 ----------
def format_SDSZ(sample_list, sampleinfo_df, source_path, batch, pedigreelist):
    SDSZbatchPath = os.path.join(source_path, 'SDSZ')
    os.makedirs(SDSZbatchPath, exist_ok=True)
    df = sampleinfo_df[sampleinfo_df['数据编号'].isin(sample_list)].copy()
    df_out = df[['样本条码','家系编号','家系名','姓名']]
    df_out.to_excel(os.path.join(source_path, f'{batch}.sampleinfo.山东山大附属生殖医院有限公司.xlsx'), index=False, engine='openpyxl')
    sample2barcode = dict(zip(df['数据编号'], df['样本条码']))
    for value in set(pedigreelist):
        if value in sample_list:
            family = value.split('_')[0]
            sample_id = value.split('_')[1]
            barcode = sample2barcode.get(sample_id, '')
            src_file = os.path.join(source_path, '01_SNV', f'{value}.flt.tsv')
            dst_file = os.path.join(SDSZbatchPath, f'{family}_{barcode}.SNV.tsv')
            df_tsv = pd.read_csv(src_file, sep='\t')
            if 'Variant_Priority_Group' in df_tsv.columns:
                df_tsv = df_tsv.drop(columns=['Variant_Priority_Group'])
                df_tsv.to_csv(dst_file, sep='\t', index=False)
    
    for sample in sample_list:
        if 'JX' not in sample:
            barcode = sample2barcode.get(sample, '')
            src_file = os.path.join(source_path, '01_SNV', f'{sample}.flt.tsv')
            dst_file = os.path.join(SDSZbatchPath, f'{barcode}.SNV.tsv')
            df_tsv = pd.read_csv(src_file, sep='\t')
            if 'Variant_Priority_Group' in df_tsv.columns:
                df_tsv = df_tsv.drop(columns=['Variant_Priority_Group'])
                df_tsv.to_csv(dst_file, sep='\t', index=False)

# ---------- 协和医院 ----------
def format_BJXH(sample_list, sampleinfo_df, source_path, batch_split, fastqPath):
    BJXHbatchPath = os.path.join(source_path, 'BJXH')
    os.makedirs(BJXHbatchPath, exist_ok=True)
    df = sampleinfo_df[sampleinfo_df['数据编号'].isin(sample_list)]
    df = df[['样本条码','家系编号','姓名','数据编号']]
    df['家系编号'] = df['家系编号'].apply(lambda x: re.sub(r'[A-Za-z]+$', '', x))
    df['家系编号'] = df['家系编号'].apply(lambda x: re.sub(r'R[\d]+$', '', x))
    df.to_csv(os.path.join(BJXHbatchPath, f'{batch_split}.sampleinfo.协和医院.tsv'), sep='\t', index=False)
    for sample in sample_list:
        fastqs = glob.glob(f'{fastqPath}/*/*{sample}*.fq.gz')
        for fq in fastqs:
            link = os.path.join(BJXHbatchPath, os.path.basename(fq))
            os.system(f'ln -sf {fq} {link}')
            if not os.path.exists(link+'.md5'):
                #print(f'md5sum {link} > {link}.md5')
                os.system(f'md5sum {link} > {link}.md5')

# ---------- 贝康（上海汉春/新华/儿研所） ----------
def format_SHHC(sample_list, sampleinfo_df, source_path, batch, BeiKangbatchPath, pedigreelist, pedigree2sample):
    # 生成 sampleinfo 文件
    df = sampleinfo_df[sampleinfo_df['数据编号'].isin(sample_list)]
    df = df[['样本条码','家系编号','家系名','姓名','数据编号','送检医院']]
    df.to_csv(os.path.join(source_path, f'{batch}.sampleinfo.Beikang_Send.txt'), sep='\t', index=False)

    # 创建贝康输出目录
    os.makedirs(BeiKangbatchPath, exist_ok=True)

    # 复制家系级别 SNV（如果家系在 sample_list 中）
    for value in set(pedigreelist):
        if value in sample_list:
            src_file = os.path.join(source_path, '01_SNV', f'{value}.flt.tsv')
            dst_file = os.path.join(BeiKangbatchPath, f'{value}.flt.tsv')
            df_tsv = pd.read_csv(src_file, sep='\t')
            if 'Variant_Priority_Group' in df_tsv.columns:
                df_tsv = df_tsv.drop(columns=['Variant_Priority_Group'])
                df_tsv.to_csv(dst_file, sep='\t', index=False)

    # 复制样本级别 SNV（包括家系内成员和单样本）
    for sample in sample_list:
        if 'JX' not in sample:
            src_file = os.path.join(source_path, '01_SNV', f'{sample}.flt.tsv')
            dst_file = os.path.join(BeiKangbatchPath, f'{sample}.flt.tsv')
            df_tsv = pd.read_csv(src_file, sep='\t')
            if 'Variant_Priority_Group' in df_tsv.columns:
                df_tsv = df_tsv.drop(columns=['Variant_Priority_Group'])
                df_tsv.to_csv(dst_file, sep='\t', index=False)

def format_ZDFS(sample_list, sampleinfo_df, source_path, batch, ZDFSbatchPath, pedigreelist, pedigree2sample):
    # 创建郑大附三输出目录
    os.makedirs(ZDFSbatchPath, exist_ok=True)

    # 复制家系级别 SNV（如果家系在 sample_list 中）
    for value in set(pedigreelist):
        if value in sample_list:
            src_file = os.path.join(source_path, '01_SNV', f'{value}.flt.tsv')
            dst_file = os.path.join(ZDFSbatchPath, f'{value}.flt.tsv')
            df_tsv = pd.read_csv(src_file, sep='\t')
            if 'Variant_Priority_Group' in df_tsv.columns:
                df_tsv = df_tsv.drop(columns=['Variant_Priority_Group'])
                df_tsv.to_csv(dst_file, sep='\t', index=False)

    # 复制样本级别 SNV
    for sample in sample_list:
        if 'JX' not in sample:
            src_file = os.path.join(source_path, '01_SNV', f'{sample}.flt.tsv')
            dst_file = os.path.join(ZDFSbatchPath, f'{sample}.flt.tsv')
            df_tsv = pd.read_csv(src_file, sep='\t')
            if 'Variant_Priority_Group' in df_tsv.columns:
                df_tsv = df_tsv.drop(columns=['Variant_Priority_Group'])
                df_tsv.to_csv(dst_file, sep='\t', index=False)

# ---------- 主函数 ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hospital', required=True, help='SHEY, BKW, SDSZ, BJXH, SHHC, ZDFS')
    parser.add_argument('--batch', required=True)
    parser.add_argument('--sourcePath', required=True)
    parser.add_argument('--sampleinfo', required=True)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    df = pd.read_csv(args.sampleinfo, sep='\t', dtype=str).fillna('')

    pedigreelist = config.get('pedigree', [])
    coupleList = set(config.get('CS', []))
    mtPedigreeList = set(config.get('mtPedigreeList', []))
    trioPair = config.get('trioPair', [])
    trio2proband = {}
    for term in trioPair:
        if ':' in term:
            trio, proband = term.split(':', 1)
            trio2proband[trio] = proband
    sample2pedigree = config.get('sample2pedigree', [])
    pedigree2sample = defaultdict(list)
    for entry in sample2pedigree:
        if ':' in entry:
            s, p = entry.split(':', 1)
            pedigree2sample[p].append(s)
    all_pedigrees = set(pedigreelist)
    all_pedigrees.update(pedigree2sample.keys())

    bioSoft = config.get('bioSoft', {})
    samtoolsPath = bioSoft.get('SamtoolsPath', '/bi/software/samtools-1.9/bin')
    genome = config.get('reference', {}).get('hg38', {}).get('genome', '/bi/ref/hg38/hg38.fa')
    bgzip = bioSoft.get('bgzip', '/bi/software/htslib-1.9/bin/bgzip')
    tabix = bioSoft.get('tabix', '/bi/software/htslib-1.9/bin/tabix')
    fastqPath = config.get('fastqPath', '/bi/fastq/T7_Fastq')
    batch_split = '_'.join(args.batch.split('_')[:2])

    if args.hospital == 'SHEY':
        sample_list = config.get('SHEYsampleList', [])
        format_SHEY(sample_list, df, args.sourcePath, batch_split,
                    all_pedigrees, pedigree2sample, pedigreelist, coupleList,
                    trio2proband, mtPedigreeList, fastqPath, samtoolsPath,
                    genome, bgzip, tabix)
    elif args.hospital == 'BKW':
        sample_list = config.get('BKWsampleList', []) + config.get('BKWpedigree', []) + config.get('BKWprobandonly', [])
        format_BKW(sample_list, df, args.sourcePath, all_pedigrees, pedigree2sample,
                   pedigreelist, coupleList, trio2proband, mtPedigreeList, fastqPath,
                   samtoolsPath, genome, bgzip, tabix, batch_split)
    elif args.hospital == 'SDSZ':
        sample_list = config.get('SDSZsampleList', [])
        format_SDSZ(sample_list, df, args.sourcePath, args.batch, pedigreelist)
    elif args.hospital == 'BJXH':
        sample_list = config.get('BJXHsampleList', [])
        format_BJXH(sample_list, df, args.sourcePath, batch_split, fastqPath)
    elif args.hospital  == 'SHHC':
        SHHCsampleList = config.get('SHHCsampleList', [])
        SHXHsampleList = config.get('SHXHsampleList', [])
        SHEYsampleList = config.get('SHEYsampleList', [])
        sample_list = SHHCsampleList + SHXHsampleList + SHEYsampleList
        BeiKangbatchPath = os.path.join(args.sourcePath, 'BeiKang')
        format_SHHC(sample_list, df, args.sourcePath, args.batch, BeiKangbatchPath, pedigreelist, pedigree2sample)
    elif args.hospital == 'ZDFS':
        sample_list = config.get('ZDFSsampleList', [])
        ZDFSbatchPath = os.path.join(args.sourcePath, 'ZDFS')
        format_ZDFS(sample_list, df, args.sourcePath, args.batch, ZDFSbatchPath, pedigreelist, pedigree2sample)
    else:
        print(f'未知医院: {args.hospital}')
        sys.exit(1)

if __name__ == '__main__':
    main()