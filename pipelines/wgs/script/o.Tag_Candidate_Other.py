#!/bi/software/micromamba/bin/python

import pandas as pd
import argparse
import subprocess
import os
import tempfile
import sys
from typing import Dict, List, Tuple, Set
import gzip

def extract_vep_tsv(vcf_file: str, bcftools: str) -> pd.DataFrame:
    # 提取CSQ字段名
    cmd_csq_header = f"zgrep '##INFO=<ID=CSQ' {vcf_file} | sed -e 's/##INFO=<ID=CSQ,Number=.,Type=String,Description=\"Consequence annotations from Ensembl VEP. Format: //' -e 's/|/\\t/g' -e 's/\">//'"
    csq_header = subprocess.check_output(cmd_csq_header, shell=True, text=True).strip()
    
    # 创建临时TSV文件
    tsv_file = tempfile.NamedTemporaryFile(suffix='.tsv', mode='w', delete=False)
    tsv_file.write(f"CHROM\tPOS\tID\tREF\tALT\t{csq_header}\n")
    tsv_file.close()
    
    # 提取数据
    cmd_extract = f"{bcftools} +split-vep {vcf_file} -f '%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%CSQ\\n' -A tab -d >> {tsv_file.name}"
    subprocess.check_call(cmd_extract, shell=True, executable='/bin/bash')
    
    # 读取TSV文件
    df = pd.read_csv(tsv_file.name, sep='\t', dtype=str, keep_default_na=False)
    #os.remove(tsv_file.name)

    return df

def classify_variant_group(group_df: pd.DataFrame) -> str:
    # 检查是否有任何转录本是morbid基因 (MorbidGene字段不为空且不为'.')
    has_morbid = any(
        group_df['MorbidGene'].notna() & 
        (group_df['MorbidGene'] != '') & 
        (group_df['MorbidGene'] != '.')
    )
    
    lof_conditions = []
    damaging_conditions = []
    
    for idx, row in group_df.iterrows():
        impact = row.get('IMPACT', '')
        spliceai_cutoff = row.get('SpliceAI_cutoff', '')
        consequence = row.get('Consequence', '')
        revel_score_str = row.get('REVEL_score', '')
        clinical_sig = row.get('clinvar_ClinicalSignificance', '')
        
        # 处理REVEL_score
        revel_score = 0.0
        if revel_score_str and revel_score_str != '.':
            try:
                revel_score = float(revel_score_str)
            except ValueError:
                pass
        
        # LoF条件：morbid基因 && (HIGH impact || SpliceAI_cutoff PASS)
        if has_morbid and (impact == 'HIGH' or spliceai_cutoff == 'PASS'):
            lof_conditions.append(True)
        
        # Damaging条件2：morbid基因 && missense && REVEL_score >= 0.6
        if has_morbid and 'missense' in consequence and revel_score >= 0.6:
            damaging_conditions.append(True)
        
        # Damaging条件3：morbid基因 && inframe
        if has_morbid and 'inframe' in consequence:
            damaging_conditions.append(True)
        
        # Damaging条件1：ClinicalSignificance包含Pathogenic或Likely_pathogenic
        if clinical_sig and clinical_sig != '.':
            if 'Pathogenic' in clinical_sig or 'Likely_pathogenic' in clinical_sig:
                damaging_conditions.append(True)
    
    # 优先匹配LoF
    if any(lof_conditions):
        return 'Candidate_LoF'
    
    # 然后匹配Damaging
    if any(damaging_conditions):
        return 'Candidate_Damaging'
    
    # 否则为Other
    return 'Other'

def get_variant_key(row: pd.Series) -> Tuple[str, str, str, str]:
    return (row['CHROM'], row['POS'], row['REF'], row['ALT'])

def process_variants(df: pd.DataFrame) -> Dict[str, Set[Tuple[str, str, str, str]]]:
    categories = {
        'Candidate_LoF': set(),
        'Candidate_Damaging': set(),
        'Other': set()
    }
    
    grouped = df.groupby(['CHROM', 'POS', 'REF', 'ALT'])
    total_variants = len(grouped)
    print(f"Classifying {total_variants} unique variants...")
    
    for (chrom, pos, ref, alt), group in grouped:
        variant_key = (chrom, pos, ref, alt)
        category = classify_variant_group(group)
        categories[category].add(variant_key)
    
    for category, variants in categories.items():
        print(f"{category}: {len(variants)} variants")
    
    return categories

def split_vcf_by_category(input_vcf: str, categories: Dict[str, Set[Tuple[str, str, str, str]]], output_lof: str, output_damaging: str, output_other: str, bcftools: str, tabix: str) -> None:
    output_files = {
        'Candidate_LoF': output_lof,
        'Candidate_Damaging': output_damaging,
        'Other': output_other
    }
    
    # 为每个类别创建临时VCF文件
    temp_vcfs = {}
    for category, output_file in output_files.items():
        temp_vcfs[category] = tempfile.NamedTemporaryFile(suffix='.vcf', mode='w', delete=False)
        # 写入头部
        cmd_header = f"{bcftools} view -h {input_vcf}"
        header = subprocess.check_output(cmd_header, shell=True, text=True)
        temp_vcfs[category].write(header)
        temp_vcfs[category].close()
    
    # 读取输入VCF并分类写入
    cmd_view = f"{bcftools} view {input_vcf}"
    process = subprocess.Popen(cmd_view, shell=True, stdout=subprocess.PIPE, text=True)
    
    total_processed = 0
    for line in process.stdout:
        if line.startswith('#'):
            continue
        fields = line.strip().split('\t')
        chrom = fields[0]
        pos = fields[1]
        ref = fields[3]
        alt = fields[4]
        
        variant_key = (chrom, pos, ref, alt)
        
        # 确定类别
        category = 'Other'
        if variant_key in categories['Candidate_LoF']:
            category = 'Candidate_LoF'
        elif variant_key in categories['Candidate_Damaging']:
            category = 'Candidate_Damaging'
        
        # 写入对应的临时文件
        if category in temp_vcfs:
            with open(temp_vcfs[category].name, 'a') as f:
                f.write(line)
            total_processed += 1
    
    process.wait()
    
    for category, temp_file in temp_vcfs.items():
        output_file = output_files[category]
        
        cmd_compress = f"bgzip -c {temp_file.name} > {output_file} && {tabix} -fp vcf {output_file}"
        subprocess.check_call(cmd_compress, shell=True, executable='/bin/bash')
        
        # 删除临时文件
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)
        
        print(f"Created {output_file} with {total_processed} total variants")
    
    print(f"Total variants processed: {total_processed}")


def main():
    parser = argparse.ArgumentParser(description='Classify VCF variants into three categories')
    parser.add_argument('-i', '--input', required=True, help='Input VCF file (compressed with .vcf.gz)')
    parser.add_argument('-lof', '--output_lof', required=True, help='Output VCF for Candidate_LoF variants (.vcf.gz)')
    parser.add_argument('-dm', '--output_damaging', required=True, help='Output VCF for Candidate_Damaging variants (.vcf.gz)')
    parser.add_argument('-other', '--output_other', required=True, help='Output VCF for Other variants (.vcf.gz)')
    parser.add_argument('-b', '--bcftools', default='bcftools', help='Path to bcftools')
    parser.add_argument('-t', '--tabix', default='tabix', help='Path to tabix')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    
    # 创建输出目录
    for output_file in [args.output_lof, args.output_damaging, args.output_other]:
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
    
    # 1. 提取VEP注释
    df = extract_vep_tsv(args.input, args.bcftools)

    # 2. 分类变异
    categories = process_variants(df)
    
    # 3. 分割VCF文件
    split_vcf_by_category(args.input, categories, args.output_lof, args.output_damaging, args.output_other, args.bcftools, args.tabix)

if __name__ == "__main__":
    main()