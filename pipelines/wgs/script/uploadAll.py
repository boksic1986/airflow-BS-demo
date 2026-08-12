#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
uploadAll.py - 主控脚本
- 读取 config.yaml，构建元数据
- 生成 copy_clinical.sh, copy_oldmaster.sh, copy_newmaster.sh（包装脚本，调用对应的 Python 可执行脚本）
- 生成 upload_redis.sh（包含所有 perl 上传命令，直接可执行）
- 生成 scp_sendmail.sh 和 format_special.sh（与原来相同）
- 生成 Step2_upload.sh 调度所有这些 .sh

用法: python uploadAll.py --config config.yaml [--sampleinfo sampleinfo.txt] [--test]
"""
import argparse
import os
import sys
import yaml
import pandas as pd
import re
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

# ---------- 生成 upload_redis.sh（包含所有 perl 命令） ----------
def build_upload_lines(sampleinfo_path: str, config: dict) -> list:
    """从 sampleinfo 生成上传条目列表"""
    df = pd.read_csv(sampleinfo_path, sep="\t", dtype=str).fillna("")
    fam2proband = defaultdict(list)
    fam2count = defaultdict(list)
    for _, row in df.iterrows():
        trio_id = row["家系编号"]
        if not trio_id:
            continue
        if row["家系关系"] == "先证者":
            fam2proband[trio_id].append(row["数据编号"])
        fam2count[trio_id].append(row["数据编号"])
    for trio_id, members in fam2count.items():
        if trio_id not in fam2proband and members:
            fam2proband[trio_id].append(members[0])
    upload_lines = []
    pedigree_hash = defaultdict(list)
    member_hash = defaultdict(list)
    trio2proband = {}
    for _, row in df.iterrows():
        trio_id = row["家系编号"]
        data_id = row["数据编号"]
        sample_id = row["样本编号"]
        count_str = row["家系人数"]
        count = int(count_str) if count_str.isdigit() else 1
        relation = row["家系关系"]
        if not trio_id:
            continue
        upload_lines.append(("cnv", f"03_CNV/Annot/{data_id}.CNV.tsv", sample_id))
        upload_lines.append(("sv", f"04_SV/c.sort/{data_id}.SV.sort.tsv", sample_id))
        if count == 1:
            upload_lines.append(("snv", f"01_SNV/{data_id}.flt.tsv", sample_id))
            upload_lines.append(("mt", f"11_MT/{data_id}.mity.flt.txt", sample_id))
        elif count > 1 and relation == "先证者" and not re.search(r"[A-Z]$", trio_id):
            upload_lines.append(("snv", f"01_SNV/{trio_id}_{data_id}.flt.tsv", sample_id))
        else:
            upload_lines.append(("snv", f"01_SNV/{data_id}.flt.tsv", sample_id))
        for proband in fam2proband[trio_id]:
            if relation != "先证者" or data_id == proband:
                pedigree_id = trio_id + "_" + proband
                pedigree_hash[pedigree_id].append(data_id)
                member_hash[pedigree_id].append(relation)
                if relation == "先证者" and data_id == proband:
                    trio2proband[pedigree_id] = data_id
    for pedigree_id, members in pedigree_hash.items():
        if len(members) <= 1:
            continue
        proband_data = trio2proband.get(pedigree_id, "")
        proband_ID = proband_data.replace('-WGS','')
        relations = set(member_hash[pedigree_id])
        if "先证者" in relations and ({"母亲", "丈夫", "妻子"} & relations):
            upload_lines.append(("mt", f"11_MT/{pedigree_id}.mity.flt.txt", proband_ID))
        elif "先证者" in relations:
            upload_lines.append(("mt", f"11_MT/{proband_data}.mity.flt.txt", proband_ID))
        has_spouse = bool({"丈夫", "妻子"} & relations)
        has_trio = {"先证者", "父亲", "母亲"}.issubset(relations)
        if "先证者" in relations and has_spouse:
            upload_lines.append(("cs", f"01_SNV/{pedigree_id}.markCS.flt.tsv", proband_ID))
        if has_trio and not has_spouse:
            upload_lines.append(("cs", f"01_SNV/{pedigree_id}.markCS.flt.tsv", proband_ID))
    return upload_lines

def generate_upload_redis(config, source_path, sampleinfo_path, test_flag):
    """生成 upload_redis.sh 内容，包含每个样本每种类型的单独上传命令"""
    upload_lines = build_upload_lines(sampleinfo_path, config)
    tools = config.get('src', {})
    upload_pl = tools.get('uploadPl')
    if test_flag:
        upload_pl = tools.get('uploadPltest')
    perl = config.get('biosoft', {}).get('perl', '/usr/bin/perl')
    if not upload_pl:
        return "#!/bin/bash\n# 警告: uploadPl未配置，跳过 Redis 上传\necho 'uploadPl未配置，跳过上传'"

    lines = ["#!/bin/bash", "# 每个样本每种类型的单独上传命令", "# 由 uploadAll.py 自动生成", ""]
    for kind, file_path, sample_id in upload_lines:
        if kind in ["snv", "cnv", "sv", "cs", "mt"]:
            full_path = os.path.join(source_path, file_path)
            cmd = f"{perl} {upload_pl} -{kind} {full_path} -ID {sample_id}"
            # lines.append(f"# {kind} 类型, 样本 {sample_id}")
            lines.append(cmd)
    lines.append("")
    lines.append("echo 'Redis 上传完成。'")
    return '\n'.join(lines)

# ---------- 生成 scp_sendmail.sh ----------
def generate_scp_sendmail(config, metadata, sampleinfo_df, source_path, batch, batch_split, test_flag):
    lines = ["#!/bin/bash", "# 各单位邮件发送脚本汇总", "# 标注单位，便于维护", ""]
    python = config.get('biosoft', {}).get(
        'python', '/bi/software/Python-3.7.11/bin/python3'
    )
    mail_cfg = config.get('mail_cfg', '')
    tools = config.get('src', {})

    if metadata.get('SHHCsampleList') or metadata.get('SHXHsampleList') or metadata.get('SHEYsampleList'):
        SHHCmail = tools.get('SHHCmail', '')
        if SHHCmail:
            BeiKangbatchPath = os.path.join(source_path, "BeiKang")
            shhc_file = os.path.join(source_path, f'{batch}.sampleinfo.Beikang_Send.txt')
            lines.append("# ---- 单位: 贝康（上海汉春、上海新华、上海儿科研究所） (SHHC) ----")
            lines.append(f"{python} {SHHCmail} {batch} {BeiKangbatchPath} {config.get('SHHCPath', '')}/{batch} {mail_cfg} {shhc_file}")

    if metadata.get('ZDFSsampleList'):
        ZDFSmail = tools.get('ZDFSmail', '')
        if ZDFSmail:
            ZDFSbatchPath = os.path.join(source_path, "ZDFS")
            samplefZDFS = os.path.join(source_path, '..', 'sampleinfo', batch + '.sampleinfo.郑大附三.txt')
            lines.append("# ---- 单位: 郑大附三 (ZDFS) ----")
            lines.append(f"{python} {ZDFSmail} {batch} {ZDFSbatchPath} {mail_cfg} {samplefZDFS}")

    if metadata.get('BJXHsampleList'):
        BJXHmail = tools.get('BJXHmail', '')
        if BJXHmail:
            BJXHbatchPath = os.path.join(source_path, "BJXH")
            bjxh_file = os.path.join(BJXHbatchPath, f'{batch_split}.sampleinfo.协和医院.tsv')
            lines.append("# ---- 单位: 北京协和 (BJXH) ----")
            lines.append(f"{python} {BJXHmail} {batch} {BJXHbatchPath} {mail_cfg} {bjxh_file}")

    if metadata.get('SDSZsampleList'):
        SDSZmail = tools.get('SDSZmail', '')
        if SDSZmail:
            SDSZbatchPath = os.path.join(source_path, "SDSZ")
            sdsz_xlsx = os.path.join(source_path, f'{batch}.sampleinfo.山东山大附属生殖医院有限公司.xlsx')
            test_flag_str = "-t" if test_flag else ""
            lines.append("# ---- 单位: 山东山大附属生殖 (SDSZ) ----")
            lines.append(f"{python} {SDSZmail} -b {batch} -i {SDSZbatchPath} -c {mail_cfg} -s {sdsz_xlsx} {test_flag_str}")

    BKWsolosampleList = metadata.get('BKWsampleList', [])
    BKWpedigree = metadata.get('BKWpedigree', [])
    BKWprobandonly = metadata.get('BKWprobandonly', [])
    BKWsampleList = BKWsolosampleList + BKWpedigree + BKWprobandonly
    if BKWsampleList:
        BKWmail = tools.get('BKWmail', '')
        if BKWmail:
            BKWbatchPath = os.path.join(source_path, "BJJY")
            bkw_file = os.path.join(source_path, 'BJJY', f'{batch_split}_data.sampleinfo.tsv')
            test_flag_str = "-t" if test_flag else ""
            lines.append("# ---- 单位: 北京金域 (BKW) ----")
            lines.append(f"{python} {BKWmail} -b {batch} -i {BKWbatchPath} -c {mail_cfg} -s {bkw_file} {test_flag_str}")

    lines.append("")
    # lines.append("echo '所有邮件发送脚本执行完成。'")
    return '\n'.join(lines)

# ---------- 生成 format_special.sh ----------
def generate_format_special(config, metadata, source_path, batch, sampleinfo_df):
    lines = ["#!/bin/bash", "# 特殊医院格式化脚本（调用 format_special.py）", "# 标注各特殊医院（中文名称），便于识别", ""]

    hospitals = []
    if metadata.get('SHEYsampleList'):
        hospitals.append('SHEY')
    if metadata.get('BKWsampleList') or metadata.get('BKWpedigree') or metadata.get('BKWprobandonly'):
        hospitals.append('BKW')
    if metadata.get('SDSZsampleList'):
        hospitals.append('SDSZ')
    if metadata.get('BJXHsampleList'):
        hospitals.append('BJXH')
    if metadata.get('SHHCsampleList') or metadata.get('SHXHsampleList') or metadata.get('SHEYsampleList'):
        hospitals.append('SHHC')
    if metadata.get('ZDFSsampleList'):
        hospitals.append('ZDFS')
    python = config.get('biosoft', {}).get(
        'python', '/bi/software/Python-3.7.11/bin/python3'
    )
    tools = config.get('src', {})
    format_special = tools.get('format_special', '')

    # ---- 生成 sampleList.txt（协和罕见病） ----
    if '项目编号' in sampleinfo_df.columns and '样本编号' in sampleinfo_df.columns:
        target_projects = ["Q0079", "Q0080", "Q0081", "Q0082"]
        filtered = sampleinfo_df[sampleinfo_df['项目编号'].isin(target_projects)]
        XHHJBSampleList = filtered['样本编号'].tolist()
        if XHHJBSampleList:
            samplelist_path = os.path.join(source_path, 'sampleList.txt')
            with open(samplelist_path, 'w') as f:
                for sid in XHHJBSampleList:
                    f.write(sid + '\n')
            print(f"生成 XHHJBSampleList 到 {samplelist_path}，共 {len(XHHJBSampleList)} 个样本")

            # 若配置了 BJXHformat，则在脚本中追加执行命令
            BJXHformat = tools.get('BJXHformat', '')
            if BJXHformat:
                sampleinfo_file = config.get('raw_sample_info') or config.get('sample_info') or config.get('new_sample_info') or ''
                lines.append("# ---- 单位: 协和罕见病 (XHHJB) ----")
                lines.append(f"{python} {BJXHformat} -i {sampleinfo_file} -l sampleList.txt")

    if not hospitals and len(XHHJBSampleList) == 0:
        lines.append("# 无特殊医院需要格式化")
        return '\n'.join(lines)

    python = config.get('biosoft', {}).get(
        'python', '/bi/software/Python-3.7.11/bin/python3'
    )
    tools = config.get('src', {})
    format_special = tools.get('format_special', '')
    if not format_special:
        lines.append("# 警告: format_special 未配置，跳过格式化")
        return '\n'.join(lines)

    hosp_name_map = {
        'SHEY': '上海儿科研究所',
        'BKW': '北京金域',
        'SDSZ': '山东山大附属生殖',
        'BJXH': '北京协和',
        'SHHC': '贝康（上海汉春、上海新华、上海儿科研究所）',
        'ZDFS': '郑大附三',
    }

    sampleinfo_file = config.get('raw_sample_info') or config.get('sample_info') or config.get('new_sample_info', '')
    config_file = os.path.join(source_path, 'config.yaml')
    for hosp in hospitals:
        chinese_name = hosp_name_map.get(hosp, hosp)
        lines.append(f"# ---- 医院: {chinese_name} ({hosp}) ----")
        cmd = f"{python} {format_special} --hospital {hosp} --batch {batch} --sourcePath {source_path} --sampleinfo {sampleinfo_file} --config {config_file}"
        lines.append(cmd)

    lines.append("")
    lines.append("echo '特殊医院格式化完成。'")
    return '\n'.join(lines)

# ---------- 生成 Step2_upload.sh ----------
def generate_step2_upload():
    lines = [
        "#!/bin/bash",
        "# 主控脚本，按顺序执行数据读取、拷贝、格式化、邮件发送",
        "set -e",
        "",
        "echo '=== 1. 读取数据并上传 Redis (reads) ==='",
        "bash upload_redis.sh",
        "",
        "echo '=== 2. 拷贝到域中备份 ==='",
        "bash copy_clinical.sh",
        "",
        "echo '=== 3. 拷贝到旧系统目录（自动清洗 _hg38 列名） ==='",
        "bash copy_oldmaster.sh",
        "",
        "echo '=== 4. 拷贝到新系统目录 ==='",
        "bash copy_newmaster.sh",
        "",
        "echo '=== 5. 特殊医院格式化 ==='",
        "bash format_special.sh",
        "",
        "echo '=== 6. 邮件发送 ==='",
        "bash scp_sendmail.sh",
        "",
        "echo '=== 所有步骤完成 ==='"
    ]
    return '\n'.join(lines)

# ---------- 主函数 ----------
def main():
    parser = argparse.ArgumentParser(description="生成部署脚本")
    parser.add_argument('--config', required=True, help='config.yaml 路径')
    parser.add_argument('--sampleinfo', help='sampleinfo 文件路径（可选）')
    parser.add_argument('--test', action='store_true', help='测试模式（传递给 upload_redis.sh）')
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
    batch = config.get('batch', '')
    if not batch:
        sys.exit("config 中缺少 batch")
    batch_split = '_'.join(batch.split('_')[:2])
    web_path = config.get('webPath', '')
    clinical_path = config.get('clinicalPath', '')

    python = config.get('biosoft', {}).get(
        'python', '/bi/software/Python-3.7.11/bin/python3'
    )
    tools = config.get('src', {})
    copy_clinical_py = tools.get('gen_copy_clinica', '')
    copy_old_py = tools.get('gen_copy_oldmaster', '')
    copy_new_py = tools.get('gen_copy_newmaster', '')
    print(copy_clinical_py)

    for py_script in [copy_clinical_py, copy_old_py, copy_new_py]:
        if not os.path.exists(py_script):
            sys.exit(f"未找到可执行脚本: {py_script}")

    # 1. 生成 copy_clinical.sh（包装脚本）
    content = f"""#!/bin/bash
# 包装脚本，调用 copy_clinical.py
{python} {copy_clinical_py} --config {args.config} --sampleinfo {sampleinfo_path}
"""
    with open(os.path.join(source_path, 'copy_clinical.sh'), 'w') as f:
        f.write(content)
    os.chmod(os.path.join(source_path, 'copy_clinical.sh'), 0o755)

    # 2. copy_oldmaster.sh
    content = f"""#!/bin/bash
# 包装脚本，调用 copy_oldmaster.py
{python} {copy_old_py} --config {args.config} --sampleinfo {sampleinfo_path}
"""
    with open(os.path.join(source_path, 'copy_oldmaster.sh'), 'w') as f:
        f.write(content)
    os.chmod(os.path.join(source_path, 'copy_oldmaster.sh'), 0o755)

    # 3. copy_newmaster.sh
    content = f"""#!/bin/bash
# 包装脚本，调用 copy_newmaster.py
{python} {copy_new_py} --config {args.config} --sampleinfo {sampleinfo_path}
"""
    with open(os.path.join(source_path, 'copy_newmaster.sh'), 'w') as f:
        f.write(content)
    os.chmod(os.path.join(source_path, 'copy_newmaster.sh'), 0o755)

    # 4. upload_redis.sh（直接包含所有 perl 命令）
    upload_redis_content = generate_upload_redis(config, source_path, sampleinfo_path, args.test)
    with open(os.path.join(source_path, 'upload_redis.sh'), 'w') as f:
        f.write(upload_redis_content)
    os.chmod(os.path.join(source_path, 'upload_redis.sh'), 0o755)

    # 5. scp_sendmail.sh
    scp_content = generate_scp_sendmail(config, metadata, sampleinfo_df, source_path, batch, batch_split, args.test)
    with open(os.path.join(source_path, 'scp_sendmail.sh'), 'w') as f:
        f.write(scp_content)
    os.chmod(os.path.join(source_path, 'scp_sendmail.sh'), 0o755)

    # 6. format_special.sh
    format_content = generate_format_special(config, metadata, source_path, batch, sampleinfo_df)
    with open(os.path.join(source_path, 'format_special.sh'), 'w') as f:
        f.write(format_content)
    os.chmod(os.path.join(source_path, 'format_special.sh'), 0o755)

    # 7. Step2_upload.sh
    step2_content = generate_step2_upload()
    with open(os.path.join(source_path, 'Step2_upload.sh'), 'w') as f:
        f.write(step2_content)
    os.chmod(os.path.join(source_path, 'Step2_upload.sh'), 0o755)

    print(f"所有脚本已生成在 {source_path}")
    print("请确认无误后执行: bash Step2_upload.sh")

if __name__ == '__main__':
    main()
