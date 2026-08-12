#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行拷贝到新系统目录的操作
用法: python copy_new.py --config config.yaml [--sampleinfo sampleinfo.txt]
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
    # 同前，为独立可执行保留
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

def copy_new(config, metadata, source_path, web_path, batch):
    webPath = os.path.join(web_path, batch)
    os.makedirs(webPath, exist_ok=True)

    batch_files = [
        (f"03_CNV/{batch}.SMA.tsv", webPath),
        (f"03_CNV/heatmap_h.png", os.path.join(webPath, f"{batch}_heatmap_h.png")),
        (f"03_CNV/{batch}.copynumber.txt", webPath),
        (f"03_CNV/{batch}.depth.r2.png", webPath),
        (f"07_QC/{batch}.QCstat.tsv", os.path.join(webPath, f"{batch}.QC.tsv")),
        (f"03_CNV/All.chrom.CN.tsv", os.path.join(webPath, "All.chrom.CN.tsv")),
        (f"03_CNV/heatmap.chrom.CN.png", os.path.join(webPath, "heatmap.chrom.CN.png")),
        (f"07_QC/{batch}.MTQC.txt", os.path.join(webPath, f"{batch}.MTQC.txt")),
        (f"07_QC/{batch}.QC.png", webPath),
        (f"07_QC/{batch}.ped_check.csv", os.path.join(webPath, f"{batch}.peddy.ped_check.csv")),
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
        webPedigreePath = os.path.join(webPath, i)
        os.makedirs(webPedigreePath, exist_ok=True)

        if pedigree in pedigreelist:
            src = os.path.join(source_path, f"01_SNV/{pedigree}.flt.tsv")
            if os.path.exists(src):
                shutil.copy2(src, webPedigreePath)
            else:
                print(f"{src} 不存在")
        if pedigree in coupleList:
            src = os.path.join(source_path, f"01_SNV/{pedigree}.markCS.flt.tsv")
            if os.path.exists(src):
                shutil.copy2(src, webPedigreePath)
            else:
                print(f"{src} 不存在")
        if pedigree in trio2proband:
            proband = trio2proband[pedigree]
            src = os.path.join(source_path, f"10_MIE/{pedigree}.trio.MIE.png")
            dst = os.path.join(webPedigreePath, f"{proband}.MIE.png")
            if os.path.exists(src):
                shutil.copy2(src, dst)
            else:
                print(f"{src} 不存在")
        if pedigree in mtPedigreeList:
            src = os.path.join(source_path, f"11_MT/{pedigree}.mity.flt.txt")
            dst = os.path.join(webPedigreePath, f"{pedigree}.MT.tsv")
            if os.path.exists(src):
                shutil.copy2(src, dst)
            else:
                print(f"{src} 不存在")

        for sample in pedigree2sample.get(pedigree, []):
            sample_files = [
                (f"03_CNV/{sample}.log2r_v.png", f"{sample}.CNV.colorful.png"),
                (f"03_CNV/{sample}.log2r_h.png", f"{sample}.CNV.genome.png"),
                (f"03_CNV/{sample}.chrom.Anno.tsv", f"{sample}.chrom.Anno.tsv"),
                (f"03_CNV/{sample}.ctrl.copynumber.txt", f"{sample}.ctrl.copynumber.txt"),
                (f"03_CNV/{sample}.CNV_VAF.png", f"{sample}.CNV_VAF.png"),
                (f"03_CNV/{sample}.CNV_VAF_noXY.png", f"{sample}.CNV_VAF_noXY.png"),
                (f"03_CNV/Annot/{sample}.CNV.tsv", f"{sample}.CNV.tsv"),
                (f"03_CNV/SMA/{sample}.SMA.tsv", f"{sample}.SMA.tsv"),
                (f"03_CNV/SMA/smn_{sample}.pdf", f"{sample}.SMA.pdf"),
                (f"04_SV/c.sort/{sample}.SV.sort.tsv", f"{sample}.SV.sort.tsv"),
                (f"06_STR/{sample}.expansionHunter.tsv", f"{sample}.expansionHunter.tsv"),
                (f"05_ROH/{sample}.HomRegions.tsv", f"{sample}.HomRegions.tsv"),
                (f"05_ROH/AutoMap/{sample}_ROH_annotataion.txt", f"{sample}_ROH_annotataion.txt"),
                (f"05_ROH/{sample}.vaf.genome.png", f"{sample}.vaf.genome.png"),
                (f"05_ROH/{sample}.vaf.genome.png_noXY.png", f"{sample}.vaf.genome.png_noXY.png"),
                (f"05_ROH/{sample}.vaf.chrs.png", f"{sample}.vaf.chrs.png"),
                (f"09_MEI/{sample}.MEIs.tsv", f"{sample}.MEIs.tsv"),
                (f"07_QC/{sample}.QC.tsv", f"{sample}.QC.tsv"),
                (f"11_MT/{sample}.mity.flt.txt", f"{sample}.MT.txt"),
                (f"01_SNV/{sample}.flt.tsv", f"{sample}.flt.tsv"),
                (f"01_SNV/{sample}.vaf.bedGraph.gz", f"{sample}.vaf.bedGraph.gz"),
                (f"01_SNV/{sample}.vaf.bedGraph.gz.tbi", f"{sample}.vaf.bedGraph.gz.tbi"),
                (f"03_CNV/{sample}.CN.bedGraph.gz", f"{sample}.CN.bedGraph.gz"),
                (f"03_CNV/{sample}.CN.bedGraph.gz.tbi", f"{sample}.CN.bedGraph.gz.tbi"),
                (f"03_CNV/{sample}.segCN.bedGraph.gz", f"{sample}.segCN.bedGraph.gz"),
                (f"03_CNV/{sample}.segCN.bedGraph.gz.tbi", f"{sample}.segCN.bedGraph.gz.tbi"),
                (f"03_CNV/{sample}.SLC25A13.tsv", f"{sample}.SLC25A13.tsv"),
            ]
            for src_rel, dst_name in sample_files:
                src = os.path.join(source_path, src_rel)
                dst = os.path.join(webPedigreePath, dst_name)
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                else:
                    print(f"{src} 不存在")

            # 软链接 cram
            cram_src = os.path.join(source_path, f"00_PreCalling/{sample}.deduped.cram")
            cram_dst = os.path.join(webPedigreePath, f"{sample}.igv.cram")
            if os.path.exists(cram_src):
                if os.path.lexists(cram_dst):
                    os.unlink(cram_dst)
                os.symlink(cram_src, cram_dst)
            else:
                print(f"{cram_src} 不存在")
            crai_src = cram_src + ".crai"
            crai_dst = cram_dst + ".crai"
            if os.path.exists(crai_src):
                if os.path.lexists(crai_dst):
                    os.unlink(crai_dst)
                os.symlink(crai_src, crai_dst)
            else:
                print(f"{crai_src} 不存在")

    # sampleinfo 拷贝（注释状态）
    sampleinfo_src = config.get('raw_sample_info', '').replace('.true', '')
    if not sampleinfo_src or not os.path.exists(sampleinfo_src):
        sampleinfo_src = config.get('new_sample_info', '')
    if sampleinfo_src and os.path.exists(sampleinfo_src):
        newSampleinfoPath = os.path.join(web_path, 'sampleinfo')
        os.makedirs(newSampleinfoPath, exist_ok=True)
        # 原脚本注释了拷贝，这里保留注释
        # shutil.copy2(sampleinfo_src, os.path.join(newSampleinfoPath, f"{batch}.sampleinfo.txt"))
    else:
        print("# 未找到 new_sample_info 文件，跳过 sampleinfo 拷贝")

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
    web_path = config.get('newWebPath2', config.get('webPath', ''))
    batch = config.get('batch', '')
    if not batch:
        sys.exit("config 中缺少 batch")

    copy_new(config, metadata, source_path, web_path, batch)
    print("新系统目录拷贝完成。")

if __name__ == '__main__':
    main()
