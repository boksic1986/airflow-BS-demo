import os
import re
import argparse
import json
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

import pandas as pd


@dataclass
class ContaminationResult:
    charr: float
    inconsistent_ab_het_rate: float
    level: str  # PASS / WARNING / FAIL


@dataclass
class SexInfo:
    registered_cn: str  # 男/女/其他
    registered: str     # M/F/ND
    predicted: str      # M/F/ND/其他
    match: bool         # True = 性别相符（或不判断）


@dataclass
class SampleMeta:
    sample: str
    name: str
    sampletype: str
    relation: str
    item_id: str
    family_id: str
    family_map: Dict[str, str]      # 数据编号 -> 家系编号
    relation_map: Dict[str, str]    # 数据编号 -> 家系关系
    sex_cn_map: Dict[str, str]      # 数据编号 -> 性别（中文）


@dataclass
class BamMetrics:
    raw_bases: int
    raw_reads: int
    dup_reads: int
    raw_gc_pct: float
    clean_gc_pct: float
    mapped_pct: float
    dup_pct: float
    clean_q30_pct: float
    cov1x_pct: float
    cov10x_pct: float
    cov20x_pct: float
    mean_depth: float
    fold80: float
    mt_depth: float


@dataclass
class ChromStats:
    percents: Dict[str, float]  # "chr1%" -> 1.234
    chrX_total: float
    chrX_chrY: float


@dataclass
class SNVCNV:
    snv_count: int
    cnv_count: int


class SampleQC:

    def __init__(
        self,
        sample: str,
        sample_info_file: str,
        bam_qc_file: str,
        mapping_qc_file: str,
        bam_chrom_file: str,
        contamination_file: str,
        mt_qc_file: str,
        snv_file: str,
        cnv_file: str,
        peddy_file: str,
        qc_config_file: str,
        snv_count_key: str = "SNV_count",
        out_file: Optional[str] = None,
    ):
        self.sample = sample
        self.sample_info_file = sample_info_file
        self.bam_qc_file = bam_qc_file
        self.mapping_qc_file = mapping_qc_file
        self.bam_chrom_file = bam_chrom_file
        self.contamination_file = contamination_file
        self.mt_qc_file = mt_qc_file
        self.snv_file = snv_file
        self.cnv_file = cnv_file
        self.peddy_file = peddy_file
        self.qc_config_file = qc_config_file
        self.snv_count_key = snv_count_key
        self.out_file = out_file

    # ====== Step 1: sample info / meta ======

    def _load_sample_meta(self) -> SampleMeta:
        df = pd.read_csv(self.sample_info_file, sep="\t", dtype=str)

        # 必要列检查一下，避免后面 KeyError
        required_cols = ["数据编号", "性别", "姓名", "家系关系", "项目编号", "家系编号", "样本类型"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"[sampleInfo] 缺少必需列: {col}")

        # 所有样本的 map
        # 去掉家系编号末尾英文
        family_map: Dict[str, str] = {
            data_id: re.sub(r"[A-Za-z]+$", "", fam if pd.notna(fam) else "")
            for data_id, fam in zip(df["数据编号"], df["家系编号"])
        }
        relation_map: Dict[str, str] = dict(zip(df["数据编号"], df["家系关系"]))
        sex_cn_map: Dict[str, str] = dict(zip(df["数据编号"], df["性别"]))

        # 当前样本这一行
        row = df.loc[df["数据编号"] == self.sample]
        if row.empty:
            raise ValueError(f"[sampleInfo] 样本 {self.sample} 未在 {self.sample_info_file} 中找到")

        row = row.iloc[0]
        name = row["姓名"]
        sampletype = row["样本类型"]
        relation = row["家系关系"]
        item_id = row["项目编号"]
        family_id = re.sub(r"[A-Za-z]+$", "", row["家系编号"] if pd.notna(row["家系编号"]) else "")

        return SampleMeta(
            sample=self.sample,
            name=name,
            sampletype=sampletype,
            relation=relation,
            item_id=item_id,
            family_id=family_id,
            family_map=family_map,
            relation_map=relation_map,
            sex_cn_map=sex_cn_map,
        )

    # ====== Step 2: contamination ======

    def _contamination(self) -> ContaminationResult:
        df = pd.read_csv(self.contamination_file, sep="\t", header="infer")
        row = df.loc[df["#SAMPLE"] == self.sample]
        if row.empty:
            raise ValueError(f"[contamination] 样本 {self.sample} 未在 {self.contamination_file} 中找到")

        charr = float(row["CHARR"].iloc[0])
        inconsistent = float(row["INCONSISTENT_AB_HET_RATE"].iloc[0])

        if charr > 0.03 and inconsistent > 0.15:
            level = "FAIL"
        elif charr > 0.02 and inconsistent > 0.1:
            level = "WARNING"
        else:
            level = "PASS"

        return ContaminationResult(
            charr=charr,
            inconsistent_ab_het_rate=inconsistent,
            level=level,
        )

    # ====== Step 3: mapping 性别 & 登记性别比对 ======

    def _mapping_sex(self) -> str:
        df = pd.read_csv(self.mapping_qc_file)
        sample_id = f"{self.sample}"
        print(sample_id)
        row = df.loc[df["Sample"] == sample_id]
        if row.empty:
            raise ValueError(f"[mappingQC] 样本 {sample_id} 未在 {self.mapping_qc_file} 中找到")
        return str(row["Gender"].iloc[0])

    @staticmethod
    def _normalize_sex_cn_to_en(sex_cn: str) -> str:
        if sex_cn == "男":
            return "M"
        if sex_cn == "女":
            return "F"
        return "ND"

    def _sex_info(self, meta: SampleMeta, predicted_sex: str) -> SexInfo:
        """
        对于登记性别为 ND 的样本，不做性别判断，默认性别相符。
        """
        reg_cn = meta.sex_cn_map.get(meta.sample, "")
        reg_en = self._normalize_sex_cn_to_en(reg_cn)

        if reg_en == "ND":
            # 登记性别未知：不做判断，视为相符
            match = True
        else:
            match = (predicted_sex == reg_en)

        return SexInfo(
            registered_cn=reg_cn,
            registered=reg_en,
            predicted=predicted_sex,
            match=match,
        )

    # ====== Step 4: 染色体统计 ======

    def _chrom_stats(self) -> ChromStats:
        df = pd.read_csv(self.bam_chrom_file, sep="\t")
        chrom_order = [
            "chr1", "chr2", "chr3", "chr4", "chr5", "chr6", "chr7", "chr8",
            "chr9", "chr10", "chr11", "chr12", "chr13", "chr14", "chr15",
            "chr16", "chr17", "chr18", "chr19", "chr20", "chr21", "chr22",
            "chrX", "chrY", "chrM",
        ]
        sub = df[df["chrom"].isin(chrom_order)].set_index("chrom")["ReadCount"].astype(float)
        if sub.empty:
            raise ValueError(f"[bamChrom] {self.bam_chrom_file} 中未找到标准染色体")

        total = sub.sum()
        percents: Dict[str, float] = {}
        for chrom in chrom_order:
            rc = float(sub.get(chrom, 0.0))
            percents[f"{chrom}%"] = round(rc / total * 100, 3) if total > 0 else 0.0

        chrX = float(sub.get("chrX", 0.0))
        chrY = float(sub.get("chrY", 0.0))
        chrX_total = chrX / total if total > 0 else 0.0
        chrX_chrY = chrX / chrY if chrY > 0 else float("inf")

        return ChromStats(percents=percents, chrX_total=chrX_total, chrX_chrY=chrX_chrY)

    # ====== Step 5: MT depth ======

    def _mt_depth(self) -> float:
        df = pd.read_csv(self.mt_qc_file, sep="\t", header="infer")
        row = df.loc[df["Sample"] == self.sample]
        if row.empty:
            raise ValueError(f"[MTQC] 样本 {self.sample} 未在 {self.mt_qc_file} 中找到")
        return float(row["Average depth"].iloc[0])

    # ====== Step 6: BAM QC 指标 ======

    def _bam_metrics(self, mt_depth: float) -> Tuple[BamMetrics, pd.Series]:
        df = pd.read_csv(self.bam_qc_file, sep="\t")
        if df.empty:
            raise ValueError(f"[bamQC] 文件 {self.bam_qc_file} 为空")

        row = df.iloc[0].copy()
        # 直接新增一列 MT_Average_Depth
        row["MT_Average_Depth"] = mt_depth

        metrics = BamMetrics(
            raw_bases=int(row["Raw_bases"]),
            raw_reads=int(row["Raw_reads"]),
            dup_reads=int(row["Duplicated_reads"]),
            raw_gc_pct=float(str(row["Raw_GC%"]).replace("%", "")),
            clean_gc_pct=float(str(row["Clean_GC%"]).replace("%", "")),
            mapped_pct=float(str(row["Mapped_Reads%"]).replace("%", "")),
            dup_pct=float(str(row["Duplicated_reads%"]).replace("%", "")),
            clean_q30_pct=float(str(row["Clean_Q30%"]).replace("%", "")),
            cov1x_pct = float(str(row[">=1X"]).replace("%", "")),
            cov10x_pct=float(str(row[">=10X"]).replace("%", "")),
            cov20x_pct=float(str(row[">=20X"]).replace("%", "")),
            mean_depth=float(row["Mean_Depth"]),
            fold80=float(row["FOLD_80_BASE_PENALTY"]),
            mt_depth=mt_depth,
        )
        return metrics, row

    # ====== Step 7: peddy 亲缘关系提示 ======

    def _peddy_notes(self, meta: SampleMeta) -> str:
        if not os.path.exists(self.peddy_file):
            return ""

        df = pd.read_csv(self.peddy_file, sep=",", header="infer")
        if df.empty:
            return ""

        notes: list[str] = []

        # 与本样本有关的所有记录
        sub = df[(df["sample_a"] == self.sample) | (df["sample_b"] == self.sample)]

        # 简单统计：有多少个 rel>=0.1 的不同样本
        high_rel_samples = set()
        for _, r in sub.iterrows():
            rel = float(r["rel"])
            if rel >= 0.1:
                other = r["sample_b"] if r["sample_a"] == self.sample else r["sample_a"]
                high_rel_samples.add(other)
        if len(high_rel_samples) > 5:
            notes.append("提示与多个样本rel系数大于0.1")

        for _, r in sub.iterrows():
            sa = r["sample_a"]
            sb = r["sample_b"]
            rel = float(r["rel"])
            sample_duplication_error = str(r.get("sample_duplication_error", "")).strip()
            pedigree_parents = str(r.get("pedigree_parents", "")).strip()
            predicted_parents = str(r.get("predicted_parents", "")).strip()
            other = sb if sa == self.sample else sa

            rel_a = meta.relation_map.get(sa, "")
            rel_b = meta.relation_map.get(sb, "")
            same_family = meta.family_map.get(sa, "") == meta.family_map.get(sb, "")

            msg = ""

            # 1. 重复样本 / 双胞胎
            if sample_duplication_error == "True" and pedigree_parents == "True":
                msg = f'提示与{other}登记亲子关系, 预测为同一样本或同卵双胞胎'
            elif sample_duplication_error == "True":
                msg = f"提示与{other}为同一样本或同卵双胞胎"

            # 2. 家系登记为亲子但预测不支持
            elif pedigree_parents == "True" and predicted_parents == "False":
                if rel < 0.1:
                    msg = f"提示与{other}家系不符"
                else:
                    msg = f"提示与{other}家系不符但rel系数>=0.1"

            # 3. 家系登记 + 预测都指向亲子，但 rel 略偏离
            elif pedigree_parents == "True" and predicted_parents == "True":
                if rel < 0.46 or rel > 0.535:
                    msg = f"提示与{other}家系相符但rel系数异常"

            # 4. 未登记亲子但预测为亲子（家系内或家系间）
            elif predicted_parents == "True":
                if 0.46 <= rel <= 0.535:
                    msg = f'提示与{other}未登记亲子关系, 预测为亲子关系'
                else:
                    msg = f'提示与{other}未登记亲子关系, 预测为亲子关系但rel系数异常'

            # 5. rel>=0.1 的夫妻关系（粗略判定）
            elif rel >= 0.1 and same_family:
                def is_parent(x: str) -> bool:
                    return "父亲" in x or "母亲" in x

                def is_proband(x: str) -> bool:
                    return "先证者" in x

                def is_spouse(x: str) -> bool:
                    return "妻子" in x or "丈夫" in x

                if (is_parent(rel_a) and is_parent(rel_b)) or (
                    is_proband(rel_a) and is_spouse(rel_b)
                ) or (is_spouse(rel_a) and is_proband(rel_b)):
                    msg = f"提示与{other}夫妻关系但rel系数>=0.1"

            # 6. 登记为兄弟姐妹但 rel<0.1（简化处理）
            elif rel < 0.1 and same_family:
                if ("先证者" in rel_a and any(k in rel_b for k in ["哥", "姐", "弟", "妹", "双胞胎", "同胞"])) or \
                   ("先证者" in rel_b and any(k in rel_a for k in ["哥", "姐", "弟", "妹", "双胞胎", "同胞"])):
                    msg = f"提示与{other}是兄弟姐妹但rel系数小于0.1"

            # 7. 登记为非家系但 rel>=0.1
            elif rel >= 0.1 and not same_family:
                if not "提示与多个样本rel系数大于0.1" in notes:
                    msg = f"提示与{other}未登记亲属关系但rel系数>=0.1"

            if msg and msg not in notes:
                notes.append(msg)

        if not notes:
            return ""
        return ";" + ";".join(notes)
    

    # ====== Step 8: SNV CNV 数量 ======

    def _snv_cnv_counts(self) -> SNVCNV:
        snv_df = pd.read_csv(self.snv_file, sep="\t", dtype=str)
        cnv_df = pd.read_csv(self.cnv_file, sep="\t", dtype=str)
        snv_count = snv_df.shape[0]
        cnv_count = cnv_df.shape[0]
        return SNVCNV(snv_count=snv_count, cnv_count=cnv_count)

    # ====== Step 9: 综合判定 ifPass ======

    def _evaluate_if_pass(
        self,
        meta: SampleMeta,
        bam: BamMetrics,
        sex_info: SexInfo,
        peddy_note: str,
        snv_cnv: SNVCNV,
        contamination: ContaminationResult,
    ) -> str:
        """
        返回“是否通过质控”列的内容：
        - 默认 "Yes"
        - 有任一问题则拼接各种提示（包括污染 WARNING / FAIL）
        """
        issues: list[str] = []

        qc_config = ''
        with open(self.qc_config_file, 'r') as f:
            qc_config = json.load(f)
        
        trans_type = qc_config.get('sampletype_trans').get(meta.sampletype, '其他')


        # 性别：登记为 ND 的已经在 SexInfo 里视为 match=True
        if not sex_info.match:
            issues.append("性别不符")

        # Mapped %
        mapped_threshold = float(qc_config.get('QC_threshold').get('mapped'))
        if bam.mapped_pct < mapped_threshold:
            issues.append(f"比对率<{mapped_threshold}%")
        
        # Raw_GC & Clean_GC
        raw_gc_min = float(qc_config.get('QC_threshold').get('Raw_GC').get(trans_type).get('min'))
        raw_gc_max = float(qc_config.get('QC_threshold').get('Raw_GC').get(trans_type).get('max'))
        if bam.raw_gc_pct < raw_gc_min:
            issues.append(f"Raw_GC偏低")
        if bam.raw_gc_pct > raw_gc_max:
            issues.append(f"Raw_GC偏高")

        clean_gc_min = float(qc_config.get('QC_threshold').get('Clean_GC').get(trans_type).get('min'))
        clean_gc_max = float(qc_config.get('QC_threshold').get('Clean_GC').get(trans_type).get('max'))
        if bam.clean_gc_pct < clean_gc_min:
            issues.append(f"Clean_GC偏低")
        if bam.clean_gc_pct > clean_gc_max:
            issues.append(f"Clean_GC偏高")

        # SNV & CNV 数量
        snv_min = int(qc_config.get('QC_threshold').get(self.snv_count_key).get(trans_type).get('min'))
        snv_max = int(qc_config.get('QC_threshold').get(self.snv_count_key).get(trans_type).get('max'))
        if snv_cnv.snv_count < snv_min:
            issues.append(f"SNV数量({snv_cnv.snv_count})偏低")
        if snv_cnv.snv_count > snv_max:
            issues.append(f"SNV数量({snv_cnv.snv_count})偏高")
        
        cnv_min = int(qc_config.get('QC_threshold').get('CNV_count').get(trans_type).get('min'))
        cnv_max = int(qc_config.get('QC_threshold').get('CNV_count').get(trans_type).get('max'))
        if snv_cnv.cnv_count < cnv_min:
            issues.append(f"CNV数量({snv_cnv.cnv_count})偏低")
        if snv_cnv.cnv_count > cnv_max:
            issues.append(f"CNV数量({snv_cnv.cnv_count})偏高")
        

        # Q30
        if meta.item_id in ["Q0079", "Q0080", "Q0081", "Q0082"]:
            if bam.clean_q30_pct <= 85:
                issues.append("Q30<=85%")
        elif bam.clean_q30_pct < 85:
            issues.append("Q30<85%")

        # 深度
        if meta.item_id in ["Q0079", "Q0080", "Q0081", "Q0082"]:
            if bam.mean_depth < 30:
                issues.append("平均覆盖低于30")
        else:
            if meta.relation == "先证者" and bam.mean_depth < 30:
                issues.append("先证者平均覆盖低于30")
            if meta.relation != "先证者" and bam.mean_depth < 20:
                issues.append("非先证者平均覆盖低于20")

        # fold80
        if bam.fold80 > 2:
            issues.append("fold80大于2")

        # WGS 特定阈值
        if meta.item_id in ["Q0079", "Q0080", "Q0081", "Q0082"]:
            effective_bases = (bam.raw_reads - bam.dup_reads) * 150
            if effective_bases <= 90000000000:
                issues.append("测序数据量<=90G")
            if bam.dup_pct >= 10:
                issues.append("数据冗余度>=10%")
            # if bam.cov10x_pct <= 98:
            #     issues.append("深度10X以上序列占比<=98%")
            if bam.cov20x_pct <= 90:
                issues.append("深度20X以上序列占比<=90%")
        else:
            if bam.raw_bases < 115000000000:
                issues.append("测序数据量<115G")
            if bam.cov1x_pct < 95:
                issues.append("深度1X以上序列占比<95%")

        # 污染 WARNING / FAIL 也要体现在“是否通过质控”
        if contamination.level == "WARNING":
            issues.append("污染WARNING")
        elif contamination.level == "FAIL":
            issues.append("污染FAIL")

        # peddy 提示
        if peddy_note:
            issues.append(peddy_note.lstrip(";"))

        if not issues:
            return "Yes"
        return ";".join(issues)

    # ====== 拼装结果行 ======

    def _build_row(
        self,
        meta: SampleMeta,
        contamination: ContaminationResult,
        sex_info: SexInfo,
        chrom_stats: ChromStats,
        qc_row: pd.Series,
        qc_status: str,
    ) -> Dict[str, object]:
        row: Dict[str, object] = {}

        row["Name"] = meta.name
        row["Sample_ID"] = meta.sample
        row["是否通过质控"] = qc_status

        # 将原始 bamQC 指标中的 "Mean_Depth" 改为 "Average_Depth"
        qc_row_renamed = qc_row.rename({"Mean_Depth": "Average_Depth"})
        # 原 bamQC 指标 + MT_Average_Depth（已经在 qc_row 里）
        for col, val in qc_row_renamed.items():
            row[col] = val

        # 染色体占比（固定顺序）
        for chrom in [
            "chr1","chr2","chr3","chr4","chr5","chr6","chr7","chr8","chr9","chr10",
            "chr11","chr12","chr13","chr14","chr15","chr16","chr17","chr18","chr19",
            "chr20","chr21","chr22","chrX","chrY","chrM"
        ]:
            key = f"{chrom}%"
            row[key] = chrom_stats.percents.get(key, 0.0)

        row["chrX/Total"] = chrom_stats.chrX_total
        row["chrX/chrY"] = chrom_stats.chrX_chrY
        row["预测性别"] = sex_info.predicted
        row["登记性别"] = sex_info.registered
        row["性别是否符合"] = "Yes" if sex_info.match else "No"
        row["CHARR"] = contamination.charr
        row["INCONSISTENT_AB_HET_RATE"] = contamination.inconsistent_ab_het_rate
        row["contamination"] = contamination.level

        return row

    # ====== 对外接口 ======

    def run(self, write_file: bool = True) -> pd.DataFrame:
        """
        执行整个 QC 流程，返回单行 DataFrame。
        如果 write_file=True 且 out_file 不为 None，会写出制表符分隔的文件。
        """
        meta = self._load_sample_meta()
        contamination = self._contamination()
        predicted_sex = self._mapping_sex()
        sex_info = self._sex_info(meta, predicted_sex)
        chrom_stats = self._chrom_stats()
        mt_depth = self._mt_depth()
        bam_metrics, qc_row = self._bam_metrics(mt_depth)
        snv_cnv = self._snv_cnv_counts()
        peddy_note = self._peddy_notes(meta)
        qc_status = self._evaluate_if_pass(
            meta, bam_metrics, sex_info, peddy_note, snv_cnv, contamination
        )

        row_dict = self._build_row(
            meta=meta,
            contamination=contamination,
            sex_info=sex_info,
            chrom_stats=chrom_stats,
            qc_row=qc_row,
            qc_status=qc_status,
        )

        df = pd.DataFrame([row_dict])
        if write_file and self.out_file:
            df.to_csv(self.out_file, sep="\t", index=False)
        return df


def main():
    parser = argparse.ArgumentParser(description="Generate QC report for a sample.")
    parser.add_argument("--sampleN", required=True, help="Sample name")
    parser.add_argument("--bamQCfile", required=True, help="BAM QC file")
    parser.add_argument("--mappingQCFile", required=True, help="Mapping QC file")
    parser.add_argument("--bamchromStat", required=True, help="BAM chromosome statistics file")
    parser.add_argument("--contaminationFile", required=True, help="Contamination file")
    parser.add_argument("--MTQCfile", required=True, help="Mitochondrial QC file")
    parser.add_argument("--outFile", required=True, help="Output QC file")
    parser.add_argument("--sampleInfoFile", required=True, help="Sample information file")
    parser.add_argument("--peddyFile", required=True, help="Peddy information file")
    parser.add_argument("--snvFile", required=True, help="SNV file")
    parser.add_argument("--cnvFile", required=True, help="CNV file")
    parser.add_argument("--snv_count_key",choices=["SNV_count", "SNV_count_bkw"],default="SNV_count", help="Key for SNV count in QC config")
    parser.add_argument("--qc_config_file", required=True, help="QC configuration JSON file")

    args = parser.parse_args()

    qc = SampleQC(
        sample=args.sampleN,
        sample_info_file=args.sampleInfoFile,
        bam_qc_file=args.bamQCfile,
        mapping_qc_file=args.mappingQCFile,
        bam_chrom_file=args.bamchromStat,
        contamination_file=args.contaminationFile,
        mt_qc_file=args.MTQCfile,
        snv_file=args.snvFile,
        cnv_file=args.cnvFile,
        peddy_file=args.peddyFile,
        qc_config_file=args.qc_config_file,
        snv_count_key=args.snv_count_key,
        out_file=args.outFile,
    )
    qc.run(write_file=True)


if __name__ == "__main__":
    main()
