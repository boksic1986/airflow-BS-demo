#!/bi/software/Anaconda3/bin/python

import argparse
import os
import ijson
import pandas as pd
import subprocess
from collections import defaultdict

def parse_arguments():
    parser = argparse.ArgumentParser(description="Process JSON data and generate gene lists.")
    parser.add_argument("-i", required=True, help="Input hp2gene file path")
    parser.add_argument("-hpo", required=True, help="Input HPO file path")  # 新增参数：HPO 输入文件路径
    parser.add_argument("-json", required=True, help="JSON file path of this batch")
    parser.add_argument("-o", required=True, help="Output file")
    parser.add_argument("-help", action="help", help="Show this help message and exit")
    return parser.parse_args()

# 函数：读取胡杭构建的表型-基因列表映射文件并存储在字典中
def load_hpo2gene(hpo2gene_file):
    hpo2genelist = defaultdict(list)
    print(f"Loading gene list from: {hpo2gene_file}")  # Debug: 打印文件路径
    with open(hpo2gene_file, "r") as file:
        next(file)  # 跳过文件的第一行
        for line in file:
            arr = line.strip().split("\t")
            if int(arr[3]) > 0:
                hpo2genelist[arr[0]] = arr[1].split("|")
    print(f"Loaded {len(hpo2genelist)} HPO IDs from gene list.")  # Debug: 输出加载的基因列表数目
    return hpo2genelist

# 函数：从 MongoDB 导出数据到 JSON 文件
def export_mongo_to_json(json_file):
    cmd = [
        "mongoexport",
        "-h", "127.0.0.1:11018",
        "-u", "ddtnReaderWriter",
        "--authenticationDatabase=admin",
        "-p", "ddtn2018",
        "--db=hg19",
        "--collection=hpo",
        "--fields=genelist,ID,nameCN,nameEN",
        "--pretty",
        "-o", json_file
    ]
    print(f"Exporting MongoDB data to JSON file: {json_file}")  # Debug: 输出 MongoDB 导出信息
    subprocess.run(cmd, check=True)
    print("MongoDB data export completed.")  # Debug: 输出导出完成信息

# 函数：处理 JSON 数据并保存到 DataFrame
def process_json_data(json_file, hpo2genelist):
    print(f"Processing JSON data from: {json_file}")  # Debug: 输出 JSON 文件路径
    data = []  # 用于存储处理后的数据
    with open(json_file, "r") as json_f:
        # 逐行解析 JSON 数据
        entries = ijson.items(json_f, '', multiple_values=True)
        entry_count = 0
        for entry in entries:
            entry_count += 1
            nameCN = entry.get("nameCN", ".") or "."
            nameCN = nameCN.replace("\n","")
            nameEN = entry.get("nameEN", ".") or "."
            nameEN = nameEN.replace("\n","")
            nameEN = nameEN.replace("#39;","'")
            nameEN = nameEN.replace(" ", "_").replace(",", "") + ".hpo"
            nameEN = nameEN.replace("hpo.hpo", "hpo")
            genelist = entry.get("genelist", ".") or "."
            genelist = genelist.replace(" ","").replace("\n","")
            ID = entry.get("ID", ".") or "."
            oldMinusNewGeneList = "."
            newMinusOldGeneList = "."
            if ID == "HP:0000001":
                nameEN = "All"
            # panel相关的命名处理
            if isinstance(nameCN, str) and "-panel" in nameCN.lower() and ID.startswith("panel:"):
                nameEN = nameEN.replace("hpo", "panel")
            if nameCN == ".":
                continue
            if genelist == ".":
                continue
            if nameEN == '-':
                continue
            # 合并和比较基因列表
            if ID in hpo2genelist:
                geneArr = genelist.split("|")
                uniq = list(set(geneArr + hpo2genelist[ID]))
                genelist = "|".join(uniq)
                oldMinusNew = list(set(geneArr) - set(hpo2genelist[ID]))
                newMinusOld = list(set(hpo2genelist[ID]) - set(geneArr))
                oldMinusNewGeneList = "|".join(oldMinusNew)
                newMinusOldGeneList = "|".join(newMinusOld)
            # 收集数据到列表中
            data.append([nameCN, '.', nameEN, genelist, ID, oldMinusNewGeneList, newMinusOldGeneList])
        print(f"Processed {entry_count} entries from JSON.")  # Debug: 输出处理条目数

    # 将数据转换为 DataFrame
    df_output = pd.DataFrame(data, columns=["中文", "同义词", "配置关键词", "基因列表", "HPO_id", "旧版独有基因列表", "新版独有基因列表"])
    print(df_output.head())  # Debug: 输出 DataFrame 的前几行
    return df_output

# 函数：处理 HPO 数据
def process_hpo_data(input_file_path):
    df = pd.read_csv(input_file_path, sep="\t", dtype=str)
    # 合并相同 hpo_id 的行，并将 gene_symbol 和 ncbi_gene_id 用 | 分割合并为字符串
    df_grouped = df.groupby(['hpo_id', 'hpo_name'], as_index=False).agg({
        'ncbi_gene_id': lambda x: '|'.join(x.dropna().unique()),  
        'gene_symbol': lambda x: '|'.join(x.dropna().unique())
    })
    df_grouped.loc[df_grouped['hpo_id'] == 'HP:0000001', ['ncbi_gene_id', 'gene_symbol']] = ''
    print(df_grouped.head())  # Debug: 输出 DataFrame 的前几行
    return df_grouped

# 更新函数：修改并合并输出
def modify_and_merge_output(df_output, df_processed):
    # 创建新的配置关键词列，替换下划线为空格，去掉 .hpo，并转换为小写
    df_output['HPO_name'] = df_output['配置关键词'].str.replace('_', ' ').str.replace('.hpo', '', regex=False).str.lower()
    # 将 df_processed 中的 hpo_name 列转换为小写以匹配
    df_processed['hpo_name'] = df_processed['hpo_name'].str.lower()
    # 匹配 HPO_name 并获取 HPO_gene
    df_output = pd.merge(df_output, df_processed, left_on='HPO_name', right_on='hpo_name', how='left', suffixes=('', '_new'))
    # 用空字符串替换所有的空值（NaN）
    df_output = df_output.fillna('')
    # 将基因列表和 gene_symbol 转换为集合并取并集
    df_output['基因列表'] = df_output.apply(
        lambda row: '|'.join(sorted(set(row['基因列表'].split('|')).union(set(row['gene_symbol'].split('|'))))), axis=1
    )
    df_output['基因列表'] = df_output['基因列表'].str.strip('.')
    df_output['基因列表'] = df_output['基因列表'].str.strip('|')
    # 删除多余列并整理
    df_output = df_output.drop(columns=['HPO_name', 'gene_symbol', 'hpo_id', 'hpo_name', 'ncbi_gene_id', "旧版独有基因列表", "新版独有基因列表"])
    df_output = df_output[df_output['中文'] != 'Unknown']
    print(df_output.head())  # Debug: 输出 DataFrame 的前几行
    return df_output

def main():
    args = parse_arguments()
    # 确定 keyword2genes 目录路径
    keyword2genes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    # 载入 HPO 到基因列表的映射
    hpo2genelist = load_hpo2gene(args.i)
    # 从 MongoDB 导出数据
    export_mongo_to_json(args.json)
    # 处理 JSON 数据并保存到 DataFrame
    df_output = process_json_data(args.json, hpo2genelist)
    # 处理 HPO 数据
    df_processed = process_hpo_data(args.hpo)  # 使用传入的 HPO 文件路径参数
    # 修改并合并 DataFrame
    df_modified = modify_and_merge_output(df_output, df_processed)
    # 保存修改后的数据为 Unicode 编码的 TXT 文件
    df_modified.to_csv(args.o, sep="\t", index=False, encoding='utf-8')
    print(f"数据已整理并保存到: {args.o}")

if __name__ == "__main__":
    main()
