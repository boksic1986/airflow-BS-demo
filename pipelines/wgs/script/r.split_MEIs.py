#!/bi/software/Anaconda3/bin/python
# -*- coding: UTF-8 -*-

import pandas as pd
import numpy as np
import re
import argparse
import os, os.path
import subprocess
from io import StringIO
import sys
import yaml

def run_command(cmd):
    print(f"Info: {cmd}")
    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Error: {cmd}, {result.stderr}")
    return result.stdout

def process_rank_file(rank_file):
    rank_dict = dict()
    rank_df = pd.read_csv(rank_file, sep='\t', dtype=str)
    rank_df = rank_df.applymap(lambda x: x.replace('[keep]', '') if isinstance(x, str) and x.startswith('[keep]') else x)
    for _, row in rank_df.iterrows():
        family_id = row['FamilyID']
        rank_dict.setdefault(family_id, {'ProbandID': row['ProbandID'], 'DadID/SpouseID': row['DadID/SpouseID'], 'MomID/KidID': row['MomID/KidID'], 'OtherID': [], 'Role': {row['ProbandID']: row['Proband'], row['DadID/SpouseID']: row['Dad/Spouse'], row['MomID/KidID']: row['Mom/Kid']}})
        rank_dict[family_id]['OtherID'] = [_sample for _sample in (rank_dict[family_id]['OtherID'] + [row['OtherID']]) if re.search('\d+', _sample)]
        rank_dict[family_id]['Role'].update({row['OtherID']: row['Other']})
    return(rank_dict)

def vcf_split_by_sample(vep_vcf: str, sample_id: str, bcftools: str) -> pd.DataFrame:
    header_split = re.split(r'\t', subprocess.check_output(f"zgrep \"^#CHROM\" {vep_vcf} | sed -e 's/#//' -e 's/INFO.*//'", shell=True).decode().strip())
    header_split += re.split(r'\t', subprocess.check_output(f"zgrep \"##INFO=<ID=CSQ\" {vep_vcf} | sed -e 's/##INFO=<ID=CSQ,Number=.,Type=String,Description=\"Consequence annotations from Ensembl VEP. Format: //' -e 's/|/\\t/g' -e 's/\">//'", shell=True).decode().strip())
    header_split += ['FORMAT', sample_id]
    split_cmd = f"{bcftools} view -s {sample_id} {vep_vcf} | {bcftools} view -i 'GT[0]~\"1\"' | {bcftools} +split-vep - -f '%CHROM\\t%POS\\t%ID\\t%REF\\t%ALT\\t%QUAL\\t%FILTER\\t%CSQ\\t%FORMAT\\n' -A tab -d"

    split_stdout = run_command(split_cmd)
    if split_stdout:
        df = pd.read_csv(StringIO(split_stdout), low_memory=False, sep='\t', header=None, names=header_split, dtype=str, encoding='utf-8')
        df['Sample_ID'] = sample_id
    else:
        df = pd.DataFrame()

    return df


def annotate_basic_info(df: pd.DataFrame, mei_raw="") -> pd.DataFrame:
    if not os.path.exists(mei_raw):
        sys.exit(f"Error: {mei_raw} does not exist")
    mei_raw_data = pd.read_csv(mei_raw, sep="\t", na_values=["None Found"], dtype=str, encoding='utf-8')

    df.loc[:, "Insertion"] = df.loc[:, "CHROM"] + ":" + df.loc[:, "POS"]

    df = df.merge(mei_raw_data, on="Insertion", how='left')
    df.loc[:, "EntrezID"] = df.loc[:, "Gene"]
    df.loc[:, "Transcript"] = df.loc[:, "Feature"]
    df.loc[:, "Strand"] = df.loc[:, "Insertion_Direction"].str.replace("Plus", "+").str.replace("Minus", "-")

    df.loc[df.EXON != ".", "Exon/Intron"] = "exon" + df.loc[df.EXON != ".", "EXON"].str.split("/").str[0]
    df.loc[df.INTRON != ".", "Exon/Intron"] = "intron" + df.loc[df.INTRON != ".", "INTRON"].str.split("/").str[0]

    return df


def annotate_hgnc_info(df: pd.DataFrame, hgnc_file="hgnc_complete_set.20230315.txt") -> pd.DataFrame:
    """
        annotate HGNC info
        :param data:
        :param hgnc_file:
        :return: data with HGNC annotation
    """
    hgnc_data = pd.read_csv(hgnc_file, sep="\t", dtype=str)
    entrez2hgnc = dict(zip(hgnc_data.entrez_id, hgnc_data.hgnc_id.str.split(":").str[1]))
    entrez2alias = dict(zip(hgnc_data.entrez_id, hgnc_data.alias_symbol))
    entrez2symbol = dict(zip(hgnc_data.entrez_id, hgnc_data.symbol))
    df.loc[:, "HGNC_ID"] = df.EntrezID.map(lambda x: entrez2hgnc.get(x))
    df.loc[:, "Gene_Alias"] = df.EntrezID.map(lambda x: entrez2alias.get(x))
    df.loc[:, "HGNC_Symbol"] = df.EntrezID.map(lambda x: entrez2symbol.get(x))

    return df


def annotate_omim_info(df: pd.DataFrame, omim_file="OMIM.20241104.txt") -> pd.DataFrame:
    """
        annotate OMIM info
        :param data:
        :param omim_file:
        :return: data with OMIM annotation
    """
    omim_info_data = pd.read_csv(omim_file, sep="\t", dtype=str, usecols=["EntrezID", "OMIM_GeneID", "OMIM_PhenotypeID",
                                                                          "Inheritance", "DiseaseEN", "SynopsisEN",
                                                                          "DiseaseCN", "SynopsisCN"])
    # OMIM_GeneID maybe duplicated
    omim_info_group = (
        omim_info_data.groupby("EntrezID")
        .agg(lambda x: '|'.join(set(map(str, x))))
        .reset_index()
    )
    omim_info_map = omim_info_group.set_index("EntrezID").to_dict(orient="index")
    # 使用 map 映射并设置默认值
    df["Inheritance"] = df["EntrezID"].map(lambda x: omim_info_map.get(x, {}).get("Inheritance", "."))
    df["Disease_CN"] = df["EntrezID"].map(lambda x: omim_info_map.get(x, {}).get("DiseaseCN", "."))
    df["Disease_EN"] = df["EntrezID"].map(lambda x: omim_info_map.get(x, {}).get("DiseaseEN", "."))
    df["Synopsis_CN"] = df["EntrezID"].map(lambda x: omim_info_map.get(x, {}).get("SynopsisCN", "."))
    df["Synopsis_EN"] = df["EntrezID"].map(lambda x: omim_info_map.get(x, {}).get("SynopsisEN", "."))
    df["OMIM_PhenotypeID"] = df["EntrezID"].map(lambda x: omim_info_map.get(x, {}).get("OMIM_PhenotypeID", "."))
    df["OMIM_GeneID"] = df["EntrezID"].map(lambda x: omim_info_map.get(x, {}).get("OMIM_GeneID", "."))
    df.loc[df.EntrezID.isin(omim_info_map.keys()), "OMIM_Gene"] = df.loc[df.EntrezID.isin(omim_info_map.keys()), "HGNC_Symbol"]
    df["OMIM_Gene_Count"] = df["EntrezID"].map(lambda x: 1 if x in omim_info_map.keys() else 0)

    return df

def annotate_chpo_info(df: pd.DataFrame, chpo_file="chpo.20230317.json", chpo_disease_file="chpo.disease.20230317.json", genes_to_phenotype_file="genes_to_phenotype.txt") -> pd.DataFrame:
    # phenotypeID 2 CHPO
    chpo_data = pd.read_json(chpo_file, dtype=str)
    chpo_id2term_map = dict(zip(chpo_data.hpoId, chpo_data.name_cn))

    gene_to_phenotype_data = pd.read_csv(genes_to_phenotype_file, sep="\t", comment="#",
                                         names=["entrez_id", "gene_symbol", "hpo_id", "hpo_term",
                                                "freq", "freq_hpo", "addition_info", "source", "link"])

    # only include OMIM
    gene_to_phenotype_data = gene_to_phenotype_data.loc[gene_to_phenotype_data.link.str.startswith("OMIM"), ]
    gene_to_phenotype_data.loc[:, "OMIM"] = gene_to_phenotype_data.link.str.split(":").str[1]
    gene_to_phenotype_data.loc[:, "hpo_term_cn"] = gene_to_phenotype_data.hpo_id.map(chpo_id2term_map)
    # ignore not translated
    gene_to_phenotype_data = gene_to_phenotype_data.loc[gene_to_phenotype_data.hpo_term_cn.notna(), ]
    mim2phen_map = gene_to_phenotype_data.groupby('OMIM')['hpo_term_cn'].apply(list).to_dict()

    # OMIM phenotype to CHPO
    chpo_disease_data = pd.read_json(chpo_disease_file, dtype=str)
    mim2cn_map = dict(zip(chpo_disease_data.mimNumber, chpo_disease_data.cnTitle))

    def add_chpo_phen_term(row):
        _chpo_phen_terms = []
        _chpo_phen_cn = []
        for mim_id in set(row.OMIM_PhenotypeID.split("|")):
            if mim2phen_map.get(mim_id, []):
                _chpo_phen_terms.append(";".join(mim2phen_map.get(mim_id, [])))
            if mim2cn_map.get(mim_id):
                _chpo_phen_cn.append(mim2cn_map.get(mim_id))
        return "|".join(_chpo_phen_cn), "|".join(_chpo_phen_terms) if len(_chpo_phen_terms) else '.'

    df.loc[:, "Disease_CHPO"] = "."
    df.loc[:, "CHPO表型关键词"] = "."

    if df[df.OMIM_PhenotypeID != "."].shape[0] > 0:
        df.loc[df.OMIM_PhenotypeID != ".", ["Disease_CHPO", "CHPO表型关键词"]] = pd.DataFrame(
            df.loc[df.OMIM_PhenotypeID != "."].apply(add_chpo_phen_term, axis=1).tolist(),
            index=df.loc[df.OMIM_PhenotypeID != "."].index,
            columns=["Disease_CHPO", "CHPO表型关键词"]
        )

    return df

def annotate_genecards_info(df: pd.DataFrame, genecards_file="genecards_summary.20241122.txt") -> pd.DataFrame:
    """
        annotate genecards info
        :param data:
        :param genecards_file:
        :return: data with genecards annotation
    """
    genecards_data = pd.read_csv(genecards_file, sep="\t", dtype=str, usecols=['Gene', 'Genecards_Summary', 'Genecards_Summary_CN'])
    genecards_map = dict(zip(genecards_data.Gene, genecards_data.Genecards_Summary_CN))
    # 使用 map 映射并设置默认值
    df["Genecards_Summary_CN"] = df["HGNC_Symbol"].map(lambda x: genecards_map.get(x))

    return df

def annotate_gnomad_pli_zscore(df: pd.DataFrame, gnomad_pli_zscore_file="gnomad.v2.1.1.PLI_Zscore.txt") -> pd.DataFrame:
    gnomad_pli_zscore_pd = pd.read_csv(gnomad_pli_zscore_file, sep="\t")
    gnomad_zscore_map = dict(zip(gnomad_pli_zscore_pd.TranscriptID.str.split(".").str[0], gnomad_pli_zscore_pd.Zscore))
    gnomad_pli_map = dict(zip(gnomad_pli_zscore_pd.TranscriptID.str.split(".").str[0], gnomad_pli_zscore_pd.PLI))

    df.loc[:, "Zscore"] = df.Transcript.str.split(".").str[0].map(gnomad_zscore_map)
    df.loc[:, "PLI"] = df.Transcript.str.split(".").str[0].map(gnomad_pli_map).round(3)
    return df

def annotate_phenotype_keywords(df: pd.DataFrame, phenotype="", phenotype_keywords_file="phenotype_key_word_gene_list.txt") -> pd.DataFrame:
    df['MatchCount'] = 0
    df['MatchKeyWords'] = ''
    df['TagKeyWords'] = '.'
    phenotype_list = phenotype.split(",")
    if len(phenotype_list) > 0:
        # phenotype_keywords file necessary columns
        # 中文 配置关键词 EntrezID列表
        phen2keywords_data = pd.read_csv(phenotype_keywords_file, sep="\t", usecols=["中文", "配置关键词", "基因列表"])
        phen2keywords_data.columns = ["keyword_zh", "keyword_en", "gene"]
        phen2keywords_data['keyword_show'] = phen2keywords_data.keyword_zh + "(" + phen2keywords_data.keyword_en + ")"

        phen2keywords_data['gene'] = phen2keywords_data['gene'].str.split('|')
        # df_exploded = phen2keywords_data.explode('gene') # 临检pandas版本较低，不支持explode方法
        df_exploded = phen2keywords_data.set_index(["keyword_zh", "keyword_en", "keyword_show"])['gene'].apply(pd.Series).stack().reset_index(level=-1, drop=True).reset_index(name='gene')

        gene2keywords = df_exploded.groupby('gene')['keyword_en'].apply(set).to_dict()

        en2show = dict(zip(phen2keywords_data.keyword_en, phen2keywords_data.keyword_show))

        # Precompute the matches for each SYMBOL
        overlap_dict = {
            gene: gene2keywords.get(gene, set()).intersection(phenotype_list)
            for gene in df['HGNC_Symbol']
        }

        # Now update the columns
        df['MatchCount'] = df['HGNC_Symbol'].map(lambda symbol: len(overlap_dict.get(symbol, set())))
        df['MatchKeyWords'] = df['HGNC_Symbol'].map(
            lambda symbol: '|'.join([en2show[gene] for gene in overlap_dict.get(symbol, set())])
        )
        df.loc[df.MatchCount > 0, 'TagKeyWords'] = "[" + df.loc[df.MatchCount > 0, 'MatchCount'].astype(str) + "/" + \
            str(len(phenotype_list)) + "]" + df.loc[df.MatchCount > 0, 'MatchKeyWords']

    df.loc[df.MatchCount > 0, "keyWordScore"] = 0.3 + 0.01 * df.loc[df.MatchCount > 0, 'MatchCount']
    df.loc[df.OMIM_PhenotypeID == ".", "keyWordScore"] = -0.3
    df.loc[df.keyWordScore.isna(), "keyWordScore"] = 0

    return df

def process_morbidmap(df: pd.DataFrame, morbidmap_file="morbidmap.20250514.txt") -> pd.DataFrame:
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
    df['isMorbid'] = df['HGNC_Symbol'].apply(lambda x: morbidmap_dict.get(x, '.'))
    return df

def annotate_genetic_inheritance(df: pd.DataFrame, rank_file="", mei_raw="", sample_id="") -> pd.DataFrame:
    df.loc[:, "遗传来源"]  = "."
    rank_dict = process_rank_file(rank_file)
    rank_dict = rank_dict[os.path.basename(rank_file).split('.')[0]]
    if sample_id == rank_dict['ProbandID']:
        roles_dict = rank_dict['Role']
        dad_mei_keys, mom_mei_keys = [], []
        if '1dad' in roles_dict.values():
            dad_sample = rank_dict['DadID/SpouseID']
            dad_mei_df = pd.read_csv(mei_raw.replace(sample_id, dad_sample), sep="\t", na_values=["None Found"], dtype=str, encoding='utf-8')
            dad_mei_keys = (dad_mei_df.loc[:, "Insertion"] + ":" + dad_mei_df.loc[:, "MEI_Family"]).tolist()
        if '2mom' in roles_dict.values():
            mom_sample = rank_dict['MomID/KidID']
            mom_mei_df = pd.read_csv(mei_raw.replace(sample_id, mom_sample), sep="\t", na_values=["None Found"], dtype=str, encoding='utf-8')
            mom_mei_keys = (mom_mei_df.loc[:, "Insertion"] + ":" + mom_mei_df.loc[:, "MEI_Family"]).tolist()

        for idx, row in df.iterrows():
            var_id = f"{row['Insertion']}:{row['MEI_Family']}"
            inheritance = []
            if var_id in dad_mei_keys:
                inheritance.append("父源")
            if var_id in mom_mei_keys:
                inheritance.append("母源")
            if inheritance:
                df.at[idx, '遗传来源'] = "和".join(inheritance)

    return df


def liftoverBed(df_before_liftover, sample, liftover, liftoverChain):
    bedFile = f"{sample}.bed"
    bedLiftover = f"{sample}.liftover.bed"
    bedUnmap = f"{sample}.liftover.unmap"
    bed_df = df_before_liftover.copy()
    bed_df[['#chr', 'start']] = bed_df['Insertion'].str.split(':', expand=True)
    bed_df['end'] = bed_df['start'].astype(int) + 1
    bed_df = bed_df[['#chr', 'start', 'end', 'Insertion']]
    bed_df.to_csv(bedFile, sep='\t', index=False)
    cmd = f'{liftover} {bedFile} {liftoverChain} {bedLiftover} {bedUnmap}'
    os.system(cmd)

    lift_df = pd.read_csv(bedLiftover, sep="\t", index_col=False, names=['#chr', 'start', 'end', 'Insertion'])
    lift_df['Insertion_hg19'] = lift_df['#chr'] + ':' + lift_df['start'].astype(str)
    lift_df = lift_df[['Insertion','Insertion_hg19']]
    df_liftover = pd.merge(df_before_liftover, lift_df, on='Insertion', how='left')
    cmd = f'rm {bedFile} {bedUnmap} {bedLiftover}'
    os.system(cmd)

    return df_liftover


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, required=True, help="input scramble vep vcf")
    parser.add_argument('-s', '--sample', type=str, required=True, help='sample name, optional for qual tag')
    parser.add_argument('-a', '--raw_mei_txt', type=str, required=True, help="input scramble_tsv")
    parser.add_argument('-r', '--rank', type=str, required=True, help="input scramble_tsv")
    parser.add_argument('-p', '--phenotype', type=str, required=True, help="input scramble_tsv")
    parser.add_argument('-o', '--output', type=str, required=True, help="output scramble_tsv")
    parser.add_argument('-cfg', '--config_file', type=str, required=True, help="config yaml file")
    parser.add_argument('--bcftools', required=True, help='container bcftools executable')
    parser.add_argument('--liftover', required=True, help='container liftOver executable')
    args = parser.parse_args()

    config = yaml.load(open(args.config_file), Loader=yaml.FullLoader)
    new_name_cols = ["PhenoTypeMatch", "phenoTypeRank", "omimGeneCount", "omimGene", "isMorbid", "omimDiseaseEN", "omimDiseaseCN", "OMIM_PhenotypeID", "Synopsis_CN", "CHPO", "GeneCards", "Inheritance", "Feature", "Exon/Intron", "Sample_ID", "Insertion_hg19", "Insertion_hg38", "MEI_Family", "遗传来源", "本地频率", "Insertion_Direction", "Clipped_Reads_In_Cluster", "Alignment_Score", "Alignment_Percent_Length", "Alignment_Percent_Identity", "Clipped_Sequence", "Clipped_Side", "Start_In_MEI", "Stop_In_MEI", "polyA_Position", "polyA_Seq", "polyA_SupportingReads", "TSD", "TSD_length", "Consequence", "SYMBOL", "PLI"]
    bcftools = args.bcftools
    database = config["database"]
    liftover = args.liftover
    liftoverChain = config["genome"]["hg38ToHg19Chain"]

    df = vcf_split_by_sample(args.input, args.sample, bcftools)
    if not df.empty:
        df = (
            df.pipe(annotate_basic_info, mei_raw=args.raw_mei_txt)
            .pipe(annotate_hgnc_info, hgnc_file=database['hgncFile'])
            .pipe(annotate_omim_info, omim_file=database['omimFile'])
            .pipe(annotate_chpo_info, chpo_file=database['chpoJson'], chpo_disease_file=database['chpoDiseaseJson'], genes_to_phenotype_file=database['hpoFile'])
            .pipe(annotate_genecards_info, genecards_file=database['genecardsFile'])
            .pipe(annotate_gnomad_pli_zscore, gnomad_pli_zscore_file=database['gnomadPLIfile'])
            .pipe(annotate_phenotype_keywords, phenotype=args.phenotype, phenotype_keywords_file=database['keyWords2GeneFile'])
            .pipe(annotate_genetic_inheritance, rank_file=args.rank, mei_raw=args.raw_mei_txt, sample_id=args.sample)
            .pipe(process_morbidmap, morbidmap_file=database['morbidmapFile'])
        )
        df.fillna('.', inplace=True)
        df.CHROM = pd.Categorical(df.CHROM, list(dict.fromkeys([f"chr{i}" for i in range(1, 23)] + ['chrX', 'chrY', 'chrM'] + df.CHROM.unique().tolist())))
        # MT Transcript -> .
        df.loc[df.CHROM == "chrM", "Transcript"] = "."
        df.POS = df.POS.astype(int)
        df.sort_values(by=['MatchCount', 'OMIM_Gene_Count', 'Disease_EN', 'Alignment_Score', 'CHROM', 'POS'], ascending=[False, False, False, False, True, True], na_position="last", inplace=True)

        df_liftover = liftoverBed(df, args.sample, liftover, liftoverChain)
        df_liftover['Insertion_hg38'] = df_liftover['Insertion']
        if "LocalMEI_AF" not in df_liftover.columns:
            local_af_path = database.get('localMeiMafFile')
            if local_af_path and os.path.exists(local_af_path):
                try:
                    af_df = pd.read_csv(local_af_path, sep='\t', dtype=str)
                    af_df['Key'] = af_df['INFO'].str.split(',').str[0]
                    af_map = dict(zip(af_df['Key'].str.upper(), af_df['MAF']))
                    # 当前 df 中的 Insertion 格式也是 CHROM:POS
                    af_keys = df_liftover['Insertion'].str.upper() + '_' + df_liftover['MEI_Family'].str.upper() + '_' + df_liftover['Insertion_Direction'].str.upper()
                    df_liftover['LocalMEI_AF'] = af_keys.map(af_map).fillna('.')
                except Exception as e:
                    print(f"Warning: Failed to load local MEI AF file: {e}")
                    df_liftover.loc[:, "LocalMEI_AF"] = "."
        else:
            df_liftover.loc[:, "LocalMEI_AF"] = "."
        df_liftover = df_liftover[(df_liftover['LocalMEI_AF'] == '.') | (pd.to_numeric(df_liftover['LocalMEI_AF'], errors='coerce') < 0.15)]
        output_cols = ["MatchKeyWords", "MatchCount", "OMIM_Gene_Count", "OMIM_Gene", "isMorbid", "Disease_EN", "Disease_CN", "OMIM_PhenotypeID", "Synopsis_CN", "CHPO表型关键词", "Genecards_Summary_CN", "Inheritance", "Feature", "Exon/Intron", "Sample_ID", "Insertion_hg19", "Insertion_hg38", "MEI_Family", "遗传来源", "LocalMEI_AF", "Insertion_Direction", "Clipped_Reads_In_Cluster", "Alignment_Score", "Alignment_Percent_Length", "Alignment_Percent_Identity", "Clipped_Sequence", "Clipped_Side", "Start_In_MEI", "Stop_In_MEI", "polyA_Position", "polyA_Seq", "polyA_SupportingReads", "TSD", "TSD_length", "Consequence", "HGNC_Symbol", "PLI"]
        df_liftover[output_cols].to_csv(args.output, sep='\t', index=False, header=new_name_cols, chunksize=2000, float_format="%.2f")
    else:
        pd.DataFrame(columns=new_name_cols).to_csv(args.output, sep='\t', index=False, chunksize=2000, float_format="%.2f")
