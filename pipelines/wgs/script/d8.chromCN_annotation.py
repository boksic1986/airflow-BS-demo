#!/bi/software/micromamba/bin/python
# -*- coding: UTF-8 -*-
"""
染色体拷贝数异常注释脚本。
读取样本染色体拷贝数文件，结合家系信息和chromCN.info.tsv阳性列表，
对常染色体和性染色体的非整倍体进行注释，输出注释结果TSV。
"""
import argparse
import os
import sys
from pathlib import Path
import pandas as pd
from dataclasses import dataclass

DELTA_NORMAL = 0.10
DELTA_FULL   = 0.95


@dataclass
class ChromCNanno:
    """染色体拷贝数注释结果数据类，字段对应输出TSV的15列"""
    pathogenicity: str = "."
    chromosome: str = "."
    var_type: str = "."
    proband_result: str = "."
    proband_mosaic_ratio: str = "."
    proband_cn: str = "."
    dad_result: str = "."
    dad_mosaic_ratio: str = "."
    dad_cn: str = "."
    mom_result: str = "."
    mom_mosaic_ratio: str = "."
    mom_cn: str = "."
    inheritance: str = "."
    disease: str = "."
    omim: str = "."

    def to_dict(self, fill_na=".") -> dict:
        """将数据类转换为字典，输出到TSV时使用中文列名"""
        def fmt(val):
            if val is None or val == "":
                return fill_na
            return str(val)

        return {
            "致病性等级": fmt(self.pathogenicity),
            "染色体": fmt(self.chromosome),
            "变异类型": fmt(self.var_type),
            "先证者结果": fmt(self.proband_result),
            "先证者嵌合比例": fmt(self.proband_mosaic_ratio),
            "先证者拷贝数": fmt(self.proband_cn),
            "父亲结果": fmt(self.dad_result),
            "父亲嵌合比例": fmt(self.dad_mosaic_ratio),
            "父亲拷贝数": fmt(self.dad_cn),
            "母亲结果": fmt(self.mom_result),
            "母亲嵌合比例": fmt(self.mom_mosaic_ratio),
            "母亲拷贝数": fmt(self.mom_cn),
            "变异来源": fmt(self.inheritance),
            "相关疾病": fmt(self.disease),
            "OMIM": fmt(self.omim),
        }


def load_info(info_file):
    """加载chromCN.info.tsv文件
    返回:
        info: dict, key=(染色体, 变异类型), value={致病性等级, 相关疾病, OMIM}
        sex_lookup: dict, key=(X拷贝数, Y拷贝数), value=核型字符串(如'47,XXY')
    """
    df = pd.read_csv(info_file, sep='\t', dtype=str)
    info = {}
    sex_lookup = {}
    for _, row in df.iterrows():
        chroms_str = str(row['染色体']).strip()
        var_type = str(row['变异类型']).strip()
        disease = str(row['相关疾病']).strip()
        omim = str(row['OMIM']).strip()
        entry = {
            'pathogenicity': str(row['致病性等级']).strip(),
            'disease': disease if disease else ".",
            'omim': omim if omim else ".",
        }
        for chrom in chroms_str.split(','):
            chrom = chrom.strip()
            info[(chrom, var_type)] = entry
        if chroms_str == 'X,Y':
            x_count = var_type.count('X')
            y_count = var_type.count('Y')
            sex_lookup[(x_count, y_count)] = var_type
    return info, sex_lookup


def parse_ped(ped_file, sample_id):
    """解析PED文件，提取先证者及父母的样本ID和性别"""
    if not os.path.exists(ped_file):
        sys.exit(f"Error: PED file not found: {ped_file}")

    ped_df = pd.read_csv(ped_file, sep='\t', header=None,
                         names=['FamilyID', 'SampleID', 'DadID', 'MomID', 'Gender', 'Status'])

    if not ped_df.empty:
        sample_row = ped_df[ped_df.SampleID == sample_id].iloc[0]
        family_info = {
            'proband': sample_row['SampleID'],
            'proband_gender': int(sample_row['Gender']),
            'dad': sample_row['DadID'] if str(sample_row['DadID']) != '0' else None,
            'mom': sample_row['MomID'] if str(sample_row['MomID']) != '0' else None,
        }
        return family_info
    else:
        return {'proband': None, 'dad': None, 'mom': None, 'proband_gender': 0}


def read_cnv_file(file_path):
    """读取染色体拷贝数文件，返回{chrN: CopyNumber}字典"""
    if not file_path or not Path(file_path).exists():
        return None
    df = pd.read_csv(file_path, sep='\t')
    df['CopyNumber'] = pd.to_numeric(df['CopyNumber'], errors='coerce')
    return dict(zip(df['chrom'], df['CopyNumber']))


def get_base_cn(chrom, gender):
    """返回指定染色体和性别下的期望基础拷贝数"""
    if chrom == 'X':
        return 1 if gender == 1 else 2
    if chrom == 'Y':
        return 1 if gender == 1 else 0
    return 2


def analyze_chromosome(cn, chrom, gender):
    """基于绝对偏差阈值分析单个染色体的拷贝数异常
    返回: (is_positive, is_gain, is_mosaic, mosaic_ratio_float)
    mosaic_ratio 为 |CN - CN_ref| * 100 的浮点数，整倍异常时返回 0.0
    """
    if cn is None or pd.isna(cn):
        return False, False, False, 0.0
    if chrom == 'Y' and gender == 2:
        return False, False, False, 0.0
    base_cn = get_base_cn(chrom, gender)
    if base_cn == 0:
        return False, False, False, 0.0

    delta = cn - base_cn
    abs_delta = abs(delta)

    if abs_delta < DELTA_NORMAL:
        return False, False, False, 0.0

    is_gain = delta > 0
    is_mos  = abs_delta < DELTA_FULL
    ratio   = round(abs_delta * 100, 1) if is_mos else 0.0

    return True, is_gain, is_mos, ratio


def format_ratio(val):
    """格式化嵌合比例: 浮点数→'35%' 字符串，整倍异常或空值返回 '.'"""
    if val is None or val == "" or val == 0.0:
        return "."
    return f"{val:.0f}%"


def get_autosome_var_type(is_gain):
    """常染色体变异类型：增益→三体，缺失→单体"""
    return "三体" if is_gain else "单体"


def match_sex_karyotype(x_cn, y_cn, x_pos, y_pos, x_gain, y_gain, gender, sex_lookup):
    """根据X和Y拷贝数候选搜索匹配性染色体核型
    按染色体异常方向生成候选拷贝数列表，遍历sex_lookup找到第一个
    能匹配的核型字符串（如'47,XXY'）。找不到匹配则返回None。
    """
    if x_cn is None or pd.isna(x_cn) or y_cn is None or pd.isna(y_cn):
        return None
    if not x_pos and not y_pos:
        return None

    nx = 1 if gender == 1 else 2
    ny = 1 if gender == 1 else 0

    if x_pos:
        if x_gain:
            x_candidates = sorted([v for v in range(nx + 1, 6)], key=lambda v: abs(v - x_cn))
        else:
            x_candidates = sorted([v for v in range(0, nx)], key=lambda v: abs(v - x_cn))
    else:
        x_candidates = [nx]

    if y_pos:
        if y_gain:
            y_candidates = sorted([v for v in range(ny + 1, 3)], key=lambda v: abs(v - y_cn))
        else:
            y_candidates = sorted([v for v in range(0, ny)], key=lambda v: abs(v - y_cn))
    else:
        y_candidates = [ny]

    for xc in x_candidates:
        for yc in y_candidates:
            if xc == nx and yc == ny:
                continue
            vt = sex_lookup.get((xc, yc))
            if vt:
                return vt

    return None


def check_parent(cn, chrom, proband_is_gain, parent_gender):
    """常染色体父母异常检验：检测父母染色体是否存在与先证者同方向的异常"""
    is_pos, is_gain, is_mos, ratio = analyze_chromosome(cn, chrom, parent_gender)
    if is_pos and is_gain == proband_is_gain:
        return True, is_mos, ratio
    return False, False, 0.0


def check_parent_sex(cn, expected_count):
    """性染色体父母异常检验：取整后的拷贝数与先证者期望拷贝数一致则为异常"""
    if cn is None or pd.isna(cn):
        return False, "", ""
    return round(cn) == expected_count, "", ""


def determine_inheritance(d_pos, m_pos):
    """根据父母检测结果判定遗传来源"""
    if d_pos and m_pos:
        return "父母双亲遗传"
    elif d_pos:
        return "父源"
    elif m_pos:
        return "母源"
    else:
        return "."


def build_parent_fields(parent_cnv, chrom, result_str, ratio_val):
    """构造父母各字段值：结果、嵌合比例、拷贝数
    若父母数据存在则填充实际值，否则返回'.'
    ratio_val 为浮点数或空字符串，内部用 format_ratio 格式化
    """
    if parent_cnv is not None:
        cn_val = parent_cnv.get(chrom)
        return result_str, format_ratio(ratio_val), cn_val if cn_val is not None and not pd.isna(cn_val) else "."
    return ".", ".", "."


def main():
    """主函数：解析参数，加载数据，逐染色体/性染色体分析并输出注释结果"""
    parser = argparse.ArgumentParser(description="染色体级拷贝数变异注释")
    parser.add_argument('-i', '--input', type=str, required=True, help='先证者 chrom.CN.tsv 文件路径')
    parser.add_argument('-s', '--sample', type=str, required=True, help='先证者样本ID')
    parser.add_argument('-p', '--ped', type=str, required=True, help='PED文件路径')
    parser.add_argument('--info', type=str, required=True, help='chromCN.info.tsv 文件路径')
    parser.add_argument('-o', '--output', type=str, required=True, help='输出TSV文件路径')
    args = parser.parse_args()

    info, sex_lookup = load_info(args.info)

    fam_info = parse_ped(args.ped, args.sample)
    proband_id = args.sample
    dad_id = fam_info['dad']
    mom_id = fam_info['mom']
    proband_gender = fam_info['proband_gender']

    cnv_dir = str(Path(args.input).parent)

    proband_cnv = read_cnv_file(args.input)
    dad_cnv = read_cnv_file(Path(cnv_dir) / f"{dad_id}.chrom.CN.tsv") if dad_id else None
    mom_cnv = read_cnv_file(Path(cnv_dir) / f"{mom_id}.chrom.CN.tsv") if mom_id else None

    if not proband_cnv:
        print(f"Error: cannot find proband {proband_id} CN file")
        return

    results = []

    # --- 常染色体分析 ---
    for i in range(1, 23):
        chrom = f"chr{i}"
        p_cn = proband_cnv.get(chrom)

        is_pos, is_gain, is_mos, p_ratio = analyze_chromosome(p_cn, chrom, proband_gender)
        if not is_pos:
            continue

        base_var = get_autosome_var_type(is_gain)
        entry = info.get((str(i), base_var))

        if entry:
            display_var = base_var
            chrom_out = str(i)
        else:
            entry = {'pathogenicity': '.', 'disease': '.', 'omim': '.'}
            display_var = "."
            chrom_out = "."

        d_cn = dad_cnv.get(chrom) if dad_cnv else None
        m_cn = mom_cnv.get(chrom) if mom_cnv else None

        d_pos, _, d_ratio = check_parent(d_cn, chrom, is_gain, 1)
        m_pos, _, m_ratio = check_parent(m_cn, chrom, is_gain, 2)
        inheritance = determine_inheritance(d_pos, m_pos)

        dad_res, dad_rat, dad_cn_val = build_parent_fields(dad_cnv, chrom,
                                                           "提示" if d_pos else "未提示", d_ratio)
        mom_res, mom_rat, mom_cn_val = build_parent_fields(mom_cnv, chrom,
                                                           "提示" if m_pos else "未提示", m_ratio)

        anno = ChromCNanno(
            pathogenicity=entry['pathogenicity'],
            chromosome=chrom_out,
            var_type=display_var,
            proband_result="提示",
            proband_mosaic_ratio=format_ratio(p_ratio),
            proband_cn=p_cn if p_cn is not None and not pd.isna(p_cn) else ".",
            dad_result=dad_res,
            dad_mosaic_ratio=dad_rat,
            dad_cn=dad_cn_val,
            mom_result=mom_res,
            mom_mosaic_ratio=mom_rat,
            mom_cn=mom_cn_val,
            inheritance=inheritance,
            disease=entry['disease'],
            omim=entry['omim'],
        )
        results.append(anno)

    # --- 性染色体分析 ---
    x_cn = proband_cnv.get('chrX')
    y_cn = proband_cnv.get('chrY')

    x_pos, x_gain, x_mos, x_ratio = analyze_chromosome(x_cn, 'X', proband_gender)
    y_pos, y_gain, y_mos, y_ratio = analyze_chromosome(y_cn, 'Y', proband_gender)

    if x_pos or y_pos:
        var_type = match_sex_karyotype(x_cn, y_cn, x_pos, y_pos, x_gain, y_gain, proband_gender, sex_lookup)

        if var_type:
            entry = info.get(('X', var_type)) or info.get(('Y', var_type))
        else:
            entry = None

        if entry:
            display_var = var_type
        else:
            entry = {'pathogenicity': '.', 'disease': '.', 'omim': '.'}
            display_var = "."

        x_round = int(round(x_cn)) if x_cn is not None and not pd.isna(x_cn) else None
        y_round = int(round(y_cn)) if y_cn is not None and not pd.isna(y_cn) else None

        dad_x_cn = dad_cnv.get('chrX') if dad_cnv else None
        mom_x_cn = mom_cnv.get('chrX') if mom_cnv else None
        dad_y_cn = dad_cnv.get('chrY') if dad_cnv else None
        mom_y_cn = mom_cnv.get('chrY') if mom_cnv else None

        # X 染色体行
        if x_pos and x_round is not None:
            x_d_pos, _, x_d_ratio = check_parent_sex(dad_x_cn, x_round)
            x_m_pos, _, x_m_ratio = check_parent_sex(mom_x_cn, x_round)
        else:
            x_d_pos, x_d_ratio = False, ""
            x_m_pos, x_m_ratio = False, ""
        x_inh = determine_inheritance(x_d_pos, x_m_pos)

        x_dad_res, x_dad_rat, x_dad_cn_val = build_parent_fields(
            dad_cnv, 'chrX', "提示" if x_d_pos else "未提示", x_d_ratio)
        x_mom_res, x_mom_rat, x_mom_cn_val = build_parent_fields(
            mom_cnv, 'chrX', "提示" if x_m_pos else "未提示", x_m_ratio)

        x_chrom = "X" if var_type else "."
        results.append(ChromCNanno(
            pathogenicity=entry['pathogenicity'],
            chromosome=x_chrom,
            var_type=display_var if x_pos else ".",
            proband_result="提示" if x_pos else "未提示",
            proband_mosaic_ratio=format_ratio(x_ratio),
            proband_cn=x_cn if x_cn is not None and not pd.isna(x_cn) else ".",
            dad_result=x_dad_res,
            dad_mosaic_ratio=x_dad_rat,
            dad_cn=x_dad_cn_val,
            mom_result=x_mom_res,
            mom_mosaic_ratio=x_mom_rat,
            mom_cn=x_mom_cn_val,
            inheritance=x_inh,
            disease=entry['disease'],
            omim=entry['omim'],
        ))

        # Y 染色体行
        if y_pos and y_round is not None:
            y_d_pos, _, y_d_ratio = check_parent_sex(dad_y_cn, y_round)
            y_m_pos, _, y_m_ratio = check_parent_sex(mom_y_cn, y_round)
        else:
            y_d_pos, y_d_ratio = False, ""
            y_m_pos, y_m_ratio = False, ""
        y_inh = determine_inheritance(y_d_pos, y_m_pos)

        y_dad_res, y_dad_rat, y_dad_cn_val = build_parent_fields(
            dad_cnv, 'chrY', "提示" if y_d_pos else "未提示", y_d_ratio)
        y_mom_res, y_mom_rat, y_mom_cn_val = build_parent_fields(
            mom_cnv, 'chrY', "提示" if y_m_pos else "未提示", y_m_ratio)

        y_chrom = "Y" if var_type else "."
        results.append(ChromCNanno(
            pathogenicity=entry['pathogenicity'],
            chromosome=y_chrom,
            var_type=display_var if y_pos else ".",
            proband_result="提示" if y_pos else "未提示",
            proband_mosaic_ratio=format_ratio(y_ratio),
            proband_cn=y_cn if y_cn is not None and not pd.isna(y_cn) else ".",
            dad_result=y_dad_res,
            dad_mosaic_ratio=y_dad_rat,
            dad_cn=y_dad_cn_val,
            mom_result=y_mom_res,
            mom_mosaic_ratio=y_mom_rat,
            mom_cn=y_mom_cn_val,
            inheritance=y_inh,
            disease=entry['disease'],
            omim=entry['omim'],
        ))

    # --- 输出 ---
    if results:
        df_out = pd.DataFrame([r.to_dict() for r in results])
        df_out.to_csv(args.output, sep='\t', index=False)
        print(f"Successfully generated: {args.output}")
    else:
        empty_anno = ChromCNanno().to_dict()
        pd.DataFrame(columns=list(empty_anno.keys())).to_csv(args.output, sep='\t', index=False)
        print("No positive aneuploidy detected.")


if __name__ == '__main__':
    main()
