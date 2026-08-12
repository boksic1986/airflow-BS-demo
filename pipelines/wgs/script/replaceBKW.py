#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from typing import Set

import pandas as pd


REQUIRED_COLUMNS = [
    "Gene",
    "GeneRankScore",
    "VarRankScore",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "从 raw.flt.tsv 中删除指定基因的记录，再从 verbose.tsv 中提取这些基因的记录，"
            "合并后按照 GeneRankScore 和 VarRankScore 降序排列。"
        )
    )

    parser.add_argument(
        "-v",
        "--verbose",
        required=True,
        help="输入 verbose TSV 文件",
    )

    parser.add_argument(
        "-f",
        "--rawflt",
        required=True,
        help="输入 raw flt TSV 文件",
    )

    parser.add_argument(
        "-l",
        "--genelist",
        required=True,
        help="BKW 基因列表文件，每行一个基因名",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="输出 flt TSV 文件",
    )

    return parser.parse_args()


def check_input_file(path, description):
    if not os.path.isfile(path):
        raise FileNotFoundError(
            "{}不存在：{}".format(description, path)
        )

    if os.path.getsize(path) == 0:
        raise ValueError(
            "{}为空：{}".format(description, path)
        )

def read_tsv(path):
    return pd.read_csv(
        path,
        sep="\t",
        dtype=str,
        keep_default_na=False,
        low_memory=False,
    )


def check_required_columns(df, path):
    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "文件 {} 缺少必要列：{}".format(
                path,
                ", ".join(missing_columns),
            )
        )


def check_same_columns(rawflt_df, verbose_df, rawflt_path, verbose_path):
    rawflt_columns = list(rawflt_df.columns)
    verbose_columns = list(verbose_df.columns)

    if rawflt_columns != verbose_columns:
        raise ValueError(
            "raw flt 和 verbose 文件的表头或列顺序不一致。\n"
            "raw flt 文件：{}\n"
            "raw flt 表头：{}\n"
            "verbose 文件：{}\n"
            "verbose 表头：{}".format(
                rawflt_path,
                rawflt_columns,
                verbose_path,
                verbose_columns,
            )
        )


def sort_result(result_df):
    """
    按 GeneRankScore 和 VarRankScore 数值降序排列。

    无法转换为数值或为空的分数排在最后。
    """
    result_df = result_df.copy()

    result_df["_GeneRankScore_sort"] = pd.to_numeric(
        result_df["GeneRankScore"],
        errors="coerce",
    )

    result_df["_VarRankScore_sort"] = pd.to_numeric(
        result_df["VarRankScore"],
        errors="coerce",
    )

    result_df = result_df.sort_values(
        by=[
            "_GeneRankScore_sort",
            "_VarRankScore_sort",
        ],
        ascending=[
            False,
            False,
        ],
        na_position="last",
        kind="mergesort",
    )

    result_df = result_df.drop(
        columns=[
            "_GeneRankScore_sort",
            "_VarRankScore_sort",
        ]
    )

    return result_df.reset_index(drop=True)


def main():
    args = parse_args()

    check_input_file(args.verbose, "verbose 文件")
    check_input_file(args.rawflt, "raw flt 文件")
    check_input_file(args.genelist, "基因列表文件")

    bkw_df = pd.read_csv(args.genelist, sep='\t')
    bkw_genes = bkw_df['entrez_id'].astype(str).str.strip().tolist()
    rawflt_df = read_tsv(args.rawflt)
    verbose_df = read_tsv(args.verbose)

    check_required_columns(rawflt_df, args.rawflt)
    check_required_columns(verbose_df, args.verbose)

    check_same_columns(
        rawflt_df=rawflt_df,
        verbose_df=verbose_df,
        rawflt_path=args.rawflt,
        verbose_path=args.verbose,
    )

    rawflt_bkw_mask = rawflt_df["EntrezID"].isin(bkw_genes)
    verbose_bkw_mask = verbose_df["EntrezID"].isin(bkw_genes)
    # 删除 raw flt 中基因位于 BKW genelist 的记录
    rawflt_remaining_df = rawflt_df.loc[
        ~rawflt_bkw_mask
    ].copy()

    # 提取 verbose 中基因位于 BKW genelist 的记录
    verbose_bkw_df = verbose_df.loc[
        verbose_bkw_mask
    ].copy()
    verbose_bkw_df["Variant_Priority_Group"] = "HEMD"

    # 按照 raw flt 原始列顺序合并
    result_df = pd.concat(
        [
            rawflt_remaining_df,
            verbose_bkw_df,
        ],
        axis=0,
        ignore_index=True,
        sort=False,
    )

    result_df = result_df[list(rawflt_df.columns)]

    result_df = sort_result(result_df)

    output_dir = os.path.dirname(
        os.path.abspath(args.output)
    )

    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    result_df.to_csv(
        args.output,
        sep="\t",
        index=False,
    )

    rawflt_removed_count = int(rawflt_bkw_mask.sum())
    verbose_added_count = int(verbose_bkw_mask.sum())

    print(
        "BKW基因数量：{}".format(len(bkw_genes)),
        file=sys.stderr,
    )
    print(
        "raw flt 原始记录数：{}".format(len(rawflt_df)),
        file=sys.stderr,
    )
    print(
        "从 raw flt 删除的记录数：{}".format(
            rawflt_removed_count
        ),
        file=sys.stderr,
    )
    print(
        "从 verbose 加入的记录数：{}".format(
            verbose_added_count
        ),
        file=sys.stderr,
    )
    print(
        "最终输出记录数：{}".format(len(result_df)),
        file=sys.stderr,
    )
    print(
        "输出文件：{}".format(args.output),
        file=sys.stderr,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            "Error: {}".format(error),
            file=sys.stderr,
        )
        sys.exit(1)