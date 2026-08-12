#!/bi/software/Anaconda3/bin/python
# -*- coding: UTF-8 -*-
import os
import shutil
import sys
import re
import subprocess
import yaml
import json
import argparse
from io import StringIO
import numpy as np
import pandas as pd


def run_command(cmd):
    print(f"# CMD: {cmd}")
    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Error: {cmd}, {result.stderr}")
    return result.stdout

def liftoverBed(df_before_liftover, samplePrefix, liftover, liftoverChain):
    bedFile = f"{samplePrefix}.bed"
    bedLiftover = f"{samplePrefix}.liftover.bed"
    bedUnmap = f"{samplePrefix}.liftover.unmap"
    bed_df = df_before_liftover.copy()
    bed_df['location'] = bed_df['#Chr'] + ':' + bed_df['Begin'].astype(str) + '-' + bed_df['End'].astype(str)
    df_before_liftover['location']=bed_df['location']
    bed_df = bed_df[['#Chr', 'Begin', 'End', 'location']]
    bed_df.to_csv(bedFile, sep='\t', index=False)
    cmd = f'{liftover} {bedFile} {liftoverChain} {bedLiftover} {bedUnmap}'
    os.system(cmd)

    lift_df = pd.read_csv(bedLiftover, sep="\t", index_col=False, names=['#Chr', 'Begin', 'End', 'location'])
    lift_df['位置_hg19'] = lift_df['#Chr'].str.replace("chr", "") + ':' + lift_df['Begin'].astype(str) + '-' + lift_df['End'].astype(str)
    lift_df = lift_df[['location','位置_hg19']]
    df_liftover = pd.merge(df_before_liftover, lift_df, on='location', how='left')
    cmd = f'rm {bedFile} {bedUnmap} {bedLiftover}'
    os.system(cmd)

    return df_liftover

def cytoband_annotation(cytoband_bed, roh_bed):
    if not os.path.exists(cytoband_bed):
        sys.exit(f"Error: The file {cytoband_bed} was not found")
    cmd = f"awk -F'\\t' 'BEGIN{{OFS=\"\\t\"}}{{print $1,$2,$2,$3}}' {roh_bed} | {bedtools} intersect -a stdin -b {cytoband_bed} -wa -wb"
    start_cytoband_stdout = run_command(cmd)
    if start_cytoband_stdout:
        start_cytoband_df = pd.read_csv(StringIO(start_cytoband_stdout), sep='\t', header=None, names=['Chr', 'Start', '_Start', 'End', 'cytobandChr', 'cytobandStart', 'cytobandEnd', 'startCytoband'], dtype=str, encoding='utf-8')
        start_cytoband_df = start_cytoband_df[['Chr', 'Start', 'End', 'startCytoband']]
    else:
        print(f"Warning: startPos未注释上cytoband")
        start_cytoband_df = pd.DataFrame(columns=['Chr', 'Start', 'End', 'startCytoband'], dtype=str, encoding='utf-8')
    cmd = f"awk -F'\\t' 'BEGIN{{OFS=\"\\t\"}}{{print $1,$3,$3,$2}}' {roh_bed} | {bedtools} intersect -a stdin -b {cytoband_bed} -wa -wb"
    end_cytoband_stdout = run_command(cmd)
    if end_cytoband_stdout:
        end_cytoband_df = pd.read_csv(StringIO(end_cytoband_stdout), sep='\t', header=None, names=['Chr', 'End', '_End', 'Start', 'cytobandChr', 'cytobandStart', 'cytobandEnd', 'endCytoband'], dtype=str, encoding='utf-8')
        end_cytoband_df = end_cytoband_df[['Chr', 'Start', 'End', 'endCytoband']]
    else:
        print(f"Warning: endPos未注释上cytoband")
        end_cytoband_df = pd.DataFrame(columns=['Chr', 'Start', 'End', 'endCytoband'], dtype=str, encoding='utf-8')
    cytoband_df = start_cytoband_df.merge(end_cytoband_df, on=['Chr', 'Start', 'End'], how='outer')
    cytoband_df.fillna(value={'startCytoband': '', 'endCytoband': ''}, inplace=True)
    cytoband_df['cytoband'] = cytoband_df.apply(lambda row: f"{row['Chr']}{row['startCytoband']}" if row['startCytoband'] == row['endCytoband'] else f"{row['Chr']}{row['startCytoband']}{row['endCytoband']}", axis=1)
    cytoband_df = cytoband_df[['Chr', 'Start', 'End', 'cytoband']]
    return(cytoband_df)


def roh_annotation(
    roh_input_file, roh_output_file, config_file,
    bedtools_command, liftover_command,
):
    global project_dir, work_dir, bedtools
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    work_dir = os.path.abspath(os.getcwd())
    tplDict = dict()
    with open(config_file, 'r') as tpl:
        tplDict = yaml.safe_load(tpl)
    # biosoftware
    bedtools = bedtools_command
    cytoband_bed = tplDict['database']['cytobandBed']
    liftover = liftover_command
    liftoverChain = tplDict["genome"]["hg38ToHg19Chain"]
    samplePrefix = roh_input_file.replace("tsv", "bed")
    roh_raw_df = pd.read_csv(roh_input_file, sep='\t', names=["#Chr", "Begin", "End", "Size(Mb)", "Nb_variants", "Percentage_homozygosity"], dtype=str, comment="#", index_col=False, encoding='utf-8')

    df_liftover = liftoverBed(roh_raw_df, samplePrefix, liftover, liftoverChain)
    if not df_liftover.empty:
        df_liftover["#Chr"] = df_liftover["#Chr"].str.replace("chr", "")
        # ---------- 新增：构造 hg38 位置（格式与 hg19 相同） ----------
        df_liftover['位置_hg38'] = df_liftover['#Chr'] + ':' + df_liftover['Begin'].astype(str) + '-' + df_liftover['End'].astype(str)
        #
        roh_bed_file = f"{roh_output_file}.bed"
        roh_bed_df = df_liftover[["#Chr", "Begin", "End"]]
        roh_bed_df[["#Chr", "Begin", "End"]].to_csv(roh_bed_file, sep='\t', index=False, header=False, encoding='utf-8')
        cytoband_df = cytoband_annotation(cytoband_bed, roh_bed_file)
        cytoband_df.columns = ["#Chr", "Begin", "End", "Cytoband"]
        #
        df_liftover = df_liftover.merge(cytoband_df, on=["#Chr", "Begin", "End"], how='left')
        df_liftover.fillna('.', inplace=True)
        df_liftover['#Chr'] = "chr" + df_liftover['#Chr']
        # ---------- 调整输出列顺序：位置_hg19 后紧跟 位置_hg38 ----------
        output_cols = ['#Chr', 'Begin', 'End', 'Size(Mb)', 'Nb_variants', 'Percentage_homozygosity', 'Cytoband', '位置_hg19', '位置_hg38']
        df_liftover[output_cols].to_csv(roh_output_file, sep='\t', index=False, encoding='utf-8')
        os.system(f"rm -f {roh_bed_file}")
    else:
        # ---------- 新增：即使 liftover 失败，也生成包含所有列的输出 ----------
        df_fail = roh_raw_df.copy()
        # 统一染色体格式：去掉 "chr" 前缀，与成功分支保持一致
        df_fail["#Chr"] = df_fail["#Chr"].str.replace("chr", "")
        # 构造 hg38 位置（基于原始坐标）
        df_fail['位置_hg38'] = df_fail['#Chr'] + ':' + df_fail['Begin'].astype(str) + '-' + df_fail['End'].astype(str)
        # 无法获得 hg19 坐标，置为缺失
        df_fail['位置_hg19'] = '.'
        df_fail['Cytoband'] = '.'
        # 恢复 chr 前缀用于输出（与成功分支一致）
        df_fail['#Chr'] = "chr" + df_fail['#Chr']
        output_cols = ['#Chr', 'Begin', 'End', 'Size(Mb)', 'Nb_variants', 'Percentage_homozygosity', 'Cytoband', '位置_hg19', '位置_hg38']
        df_fail[output_cols].to_csv(roh_output_file, sep='\t', index=False, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Process CNV data.')
    parser.add_argument('-i', '--input', required=True, type=str, help='Input file, eg. WES2001-HE.HomRegions.tsv')
    parser.add_argument('-o', '--output', required=True, type=str, help='Output file, eg. WES2001-HE.HomRegions.tsv')
    parser.add_argument('--config', required=True, type=str, help='Config file, eg. config.yaml')
    parser.add_argument('--bedtools', required=True, help='container bedtools executable')
    parser.add_argument('--liftover', required=True, help='container liftOver executable')
    args = parser.parse_args()
    roh_input_file = os.path.abspath(args.input)
    roh_output_file = os.path.abspath(args.output)
    roh_annotation(
        roh_input_file, roh_output_file, args.config,
        args.bedtools, args.liftover,
    )

if __name__ == '__main__':
     main()
