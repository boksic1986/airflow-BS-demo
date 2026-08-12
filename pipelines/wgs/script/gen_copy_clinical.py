#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实际执行拷贝到临床目录的操作
用法: python copy_clinical.py --config config.yaml [--sampleinfo sampleinfo.txt]
"""
import argparse
import os
import sys
import yaml
import pandas as pd
import re
import shutil
from collections import defaultdict

def read_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def load_sampleinfo(path):
    return pd.read_csv(path, sep='\t', dtype=str).fillna('')

def build_metadata(config, sampleinfo_df):
    metadata = {}
    for key in ['pedigree', 'CS', 'mtPedigreeList', 'SHHCsampleList', 'ZDFSsampleList',
                'BJXHsampleList', 'SHEYsampleList', 'SHXHsampleList', 'SDSZsampleList',
                'BKWsampleList', 'BKWpedigree', 'BKWprobandonly']:
        metadata[key] = config.get(key, [])
    sample2pedigree = config.get('sample2pedigree', [])
    pedigree2sample = defaultdict(list)
    for entry in sample2pedigree:
        if ':' in entry:
            sample, pedigree = entry.split(':', 1)
            pedigree2sample[pedigree].append(sample)
    metadata['pedigree2sample'] = dict(pedigree2sample)
    trio_pair = config.get('trioPair', [])
    trio2proband = {}
    for term in trio_pair:
        if ':' in term:
            trio, proband = term.split(':', 1)
            trio2proband[trio] = proband
    metadata['trio2proband'] = trio2proband
    all_pedigrees = set(metadata['pedigree'])
    all_pedigrees.update(pedigree2sample.keys())
    metadata['all_pedigrees'] = sorted(set(all_pedigrees))
    if not sampleinfo_df.empty:
        sample2barcode = dict(zip(sampleinfo_df['样本编号'], sampleinfo_df['医院条码号']))
        data2barcode = dict(zip(sampleinfo_df['数据编号'], sampleinfo_df['医院条码号']))
        proband_df = sampleinfo_df[sampleinfo_df['家系关系'] == '先证者']
        family2barcode = {}
        for _, row in proband_df.iterrows():
            family = row['家系编号']
            barcode = row['医院条码号']
            if family and barcode:
                family2barcode[family] = 'JX' + barcode
        metadata['sample2barcode'] = sample2barcode
        metadata['data2barcode'] = data2barcode
        metadata['family2barcode'] = family2barcode
    return metadata

def copy_clinical(config, metadata, source_path, clinical_path, batch):
    clinicalPath = os.path.join(clinical_path, batch)
    os.makedirs(clinicalPath, exist_ok=True)

    batch_files = [
        (f"03_CNV/{batch}.SMA.tsv", clinicalPath),
        (f"03_CNV/heatmap_h.png", os.path.join(clinicalPath, f"{batch}_heatmap_h.png")),
        (f"07_QC/{batch}.QCstat.tsv", os.path.join(clinicalPath, f"{batch}.QC.tsv")),
        (f"03_CNV/All.chrom.CN.tsv", os.path.join(clinicalPath, "All.chrom.CN.tsv")),
        (f"03_CNV/heatmap.chrom.CN.png", os.path.join(clinicalPath, "heatmap.chrom.CN.png")),
        (f"07_QC/{batch}.MTQC.txt", os.path.join(clinicalPath, f"{batch}.MTQC.txt")),
        (f"07_QC/{batch}.QC.png", clinicalPath),
        (f"07_QC/{batch}.ped_check.csv", clinicalPath),
        (f"07_QC/multiqc_report.html", os.path.join(clinicalPath, f"{batch}.multiqc_report.html")),
        (f"03_CNV/All.join.log2r.bed.gz", os.path.join(clinicalPath, f"{batch}_log2ratio.bed.gz")),
        (f"03_CNV/All.join.log2r.bed.gz.tbi", os.path.join(clinicalPath, f"{batch}_log2ratio.bed.gz.tbi")),
    ]
    for src_rel, dst in batch_files:
        src = os.path.join(source_path, src_rel)
        if os.path.exists(src):
            shutil.copy2(src, dst)
        else:
            print(f"{src} 不存在")

    all_pedigrees = metadata.get('all_pedigrees', [])
    pedigree2sample = metadata.get('pedigree2sample', {})
    pedigreelist = set(metadata.get('pedigree', []))
    coupleList = set(metadata.get('CS', []))
    trio2proband = metadata.get('trio2proband', {})
    mtPedigreeList = set(metadata.get('mtPedigreeList', []))

    for pedigree in all_pedigrees:
        i = pedigree.split('_')[0]
        i = re.sub(r'[A-Za-z]+$', '', i)
        i = re.split(r'R\d{1,2}$', i)[0]
        clinicalPedigreeP = os.path.join(clinicalPath, i)
        os.makedirs(clinicalPedigreeP, exist_ok=True)

        if pedigree in pedigreelist:
            for ext in ['.verbose.tsv', '.flt.tsv']:
                src = os.path.join(source_path, f"01_SNV/{pedigree}{ext}")
                if os.path.exists(src):
                    shutil.copy2(src, clinicalPedigreeP)
                else:
                    print(f"{src} 不存在")
        if pedigree in coupleList:
            for ext in ['.markCS.verbose.tsv', '.markCS.flt.tsv']:
                src = os.path.join(source_path, f"01_SNV/{pedigree}{ext}")
                if os.path.exists(src):
                    shutil.copy2(src, clinicalPedigreeP)
                else:
                    print(f"{src} 不存在")
            src1v = os.path.join(source_path, f"01_SNV/{pedigree}_1.markCS.verbose.tsv")
            src1f = os.path.join(source_path, f"01_SNV/{pedigree}_1.markCS.flt.tsv")
            if os.path.exists(src1v):
                shutil.copy2(src1v, clinicalPedigreeP)
            if os.path.exists(src1f):
                shutil.copy2(src1f, clinicalPedigreeP)
        if pedigree in trio2proband:
            src = os.path.join(source_path, f"10_MIE/{pedigree}.trio.MIE.png")
            if os.path.exists(src):
                shutil.copy2(src, clinicalPedigreeP)
            else:
                print(f"{src} 不存在")
        if pedigree in mtPedigreeList:
            src = os.path.join(source_path, f"11_MT/{pedigree}.mity.flt.txt")
            if os.path.exists(src):
                shutil.copy2(src, clinicalPedigreeP)
            else:
                print(f"{src} 不存在")

        for sample in pedigree2sample.get(pedigree, []):
            sample_files = [
                (f"03_CNV/{sample}.log2r_v.png", f"{sample}.CNV.colorful.png"),
                (f"03_CNV/{sample}.log2r_h.png", f"{sample}.CNV.genome.png"),
                (f"03_CNV/{sample}.CNV_VAF.png", f"{sample}.CNV_VAF.png"),
                (f"03_CNV/{sample}.CNV_VAF_noXY.png", f"{sample}.CNV_VAF_noXY.png"),
                (f"03_CNV/SMA/{sample}.SMA.tsv", f"{sample}.SMA.tsv"),
                (f"03_CNV/SMA/smn_{sample}.pdf", f"{sample}.SMA.pdf"),
                (f"04_SV/c.sort/{sample}.SV.sort.tsv", f"{sample}.SV.tsv"),
                (f"03_CNV/Annot/{sample}.CNV.tsv", f"{sample}.CNV.tsv"),
                (f"06_STR/{sample}.expansionHunter.tsv", f"{sample}.expansionHunter.tsv"),
                (f"01_SNV/{sample}.flt.tsv", f"{sample}.flt.tsv"),
                (f"01_SNV/{sample}.verbose.tsv", f"{sample}.verbose.tsv"),
                (f"05_ROH/{sample}.HomRegions.tsv", f"{sample}.HomRegions.tsv"),
                (f"09_MEI/{sample}.MEIs.tsv", f"{sample}.MEIs.tsv"),
                (f"05_ROH/{sample}.vaf.chrs.png", f"{sample}.vaf.chrs.png"),
                (f"05_ROH/{sample}.vaf.genome.png", f"{sample}.vaf.genome.png"),
                (f"05_ROH/{sample}.vaf.genome.png_noXY.png", f"{sample}.vaf.genome.png_noXY.png"),
                (f"07_QC/{sample}.QC.tsv", f"{sample}.QC.tsv"),
                (f"11_MT/{sample}.mity.flt.txt", f"{sample}.mity.flt.txt"),
            ]
            for src_rel, dst_name in sample_files:
                src = os.path.join(source_path, src_rel)
                dst = os.path.join(clinicalPedigreeP, dst_name)
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                else:
                    print(f"{src} 不存在")

    # 拷贝 sampleinfo
    sampleinfo_src = config.get('raw_sample_info', '').replace('.true', '')
    if not sampleinfo_src or not os.path.exists(sampleinfo_src):
        sampleinfo_src = config.get('sample_info', config.get('new_sample_info', ''))
    if sampleinfo_src and os.path.exists(sampleinfo_src):
        shutil.copy2(sampleinfo_src, os.path.join(clinicalPath, f"{batch}.sampleinfo.txt"))
    else:
        print("# 未找到 sample_info 文件，跳过 sampleinfo 拷贝")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--sampleinfo', help='可选')
    args = parser.parse_args()

    config = read_yaml(args.config)
    if not config:
        sys.exit("无法加载 config.yaml")
    sampleinfo_path = args.sampleinfo or config.get('sample_info') or config.get('raw_sample_info')
    if not sampleinfo_path or not os.path.exists(sampleinfo_path):
        sys.exit("未找到 sampleinfo 文件")
    sampleinfo_df = load_sampleinfo(sampleinfo_path)
    metadata = build_metadata(config, sampleinfo_df)

    source_path = config.get('workDir', '')
    clinical_path = config.get('clinicalPath', '')
    batch = config.get('batch', '')
    if not batch:
        sys.exit("config 中缺少 batch")

    copy_clinical(config, metadata, source_path, clinical_path, batch)
    print("临床目录拷贝完成。")

if __name__ == '__main__':
    main()
