import os
import sys
import pandas as pd
import numpy as np
import subprocess
import argparse
from cyvcf2 import VCF, Writer
from io import StringIO
import time
from datetime import datetime


def run_command(cmd):
    print(f"Info: {cmd}")
    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Error: {cmd}, {result.stderr}")
    return result.stdout


class DepthCorrect(object):
    def __init__(self, in_file, cram_dir, output_file, ref_fa, bcftools, pandepth, threads = 8, min_mapping_quality = 20):
        self.in_file = in_file
        self.cram_dir = cram_dir
        self.output_tmp_file = output_file.replace('.vcf', '.tmp.vcf')
        self.output_file = output_file
        self.ref_fa = ref_fa
        self.bcftools = bcftools
        self.pandepth = pandepth
        self.VCF = VCF(self.in_file)
        self.samples = self.VCF.samples
        self.threads = threads
        self.min_mapping_quality = min_mapping_quality
        self.time_tag = datetime.now().strftime("%Y%m%d%H%M%S%f")

    def process_file(self, file):
        timeout = 60
        start_time = time.time()
        while True:
            if os.path.exists(file):
                break
            if time.time() - start_time > timeout:
                break
            time.sleep(1)

    def get_wildTypeLocus_depth(self) -> dict:
        wildTypeLocus_depth_dict = {}
        for _sample in self.samples:
            _vcf_bed_cmd = f"{self.bcftools} view -s {_sample} {self.in_file} | {self.bcftools} view -e 'CHROM~\"M\" || CHROM~\"_\"' | {self.bcftools} view -i 'GT[0]=\"0/0\" & ADS[0]=0' | {self.bcftools} query -f '%CHROM\\t%POS\\t%POS\\t%CHROM-%POS-%REF-%ALT\\n'"
            _vcf_bed_df = run_command(_vcf_bed_cmd)
            if not _vcf_bed_df:
                continue
            _bed_file = os.path.join(self.cram_dir, f"{_sample}.wildType.getDP.{self.time_tag}.bed")
            _vcf_bed_df = pd.read_csv(StringIO(_vcf_bed_df), low_memory=False, sep='\t', header=None, names=['CHROM', 'POS', 'END', 'VarID'], dtype=str, encoding='utf-8')
            with open(_bed_file, 'w', encoding='utf-8') as f:
                _vcf_bed_df.to_csv(f, index=False, header=False, sep='\t', encoding='utf-8')
                f.flush()
                os.fsync(f.fileno())
            self.process_file(_bed_file)
            # get depth
            _cram_file = os.path.join(self.cram_dir, f"{_sample}.deduped.cram")
            if not os.path.exists(_cram_file):
                sys.exit(f"Error: {_cram_file} not found")
            _depth_file = os.path.join(self.cram_dir, f"{_sample}.{self.time_tag}.bed.stat.gz")
            _wildTypeLocus_depth_cmd = f"{self.pandepth} -i {_cram_file} -b {_bed_file} -t {self.threads} -q {self.min_mapping_quality} -r {self.ref_fa} -o {_depth_file.replace(r'.bed.stat.gz', '')}"
            run_command(_wildTypeLocus_depth_cmd)
            print(f"Info: Get {_depth_file} done", flush=True)
            self.process_file(_depth_file)
            _depth_df = pd.read_csv(_depth_file, low_memory=False, sep='\t', dtype=str, encoding='utf-8')
            _depth_df = _depth_df[_depth_df['#Chr'].str.startswith('chr')]
            _depth_df['TotalDepth'] = _depth_df['TotalDepth'].astype(int)
            for gene_id, depth in zip(_depth_df['GeneID'], _depth_df['TotalDepth']):
                wildTypeLocus_depth_dict.setdefault(gene_id, {})[_sample] = depth
            run_command(f"rm -f {_bed_file} {_depth_file}")
        return wildTypeLocus_depth_dict

    def get_ad_dp(self, record, _depth_dict):
        dp_arr = record.format('DP').copy()
        ad_arr = record.format('AD').copy()
        sample_index = {s: i for i, s in enumerate(self.samples)}
        for sample, depth_val in _depth_dict.items():
            if sample in sample_index:
                idx = sample_index[sample]
                dp_arr[idx] = [depth_val]
                ad_arr[idx] = [depth_val, 0]
        record.set_format('DP', dp_arr)
        record.set_format('AD', ad_arr)
        return record

    def process_depth_correct(self):
        wildTypeLocus_depth_dict = self.get_wildTypeLocus_depth()
        w = Writer(self.output_tmp_file, self.VCF)
        for v in self.VCF:
            record = self.get_ad_dp(v, wildTypeLocus_depth_dict.get(f"{v.CHROM}-{v.POS}-{v.REF}-{v.ALT[0]}", {}))
            w.write_record(record)
        w.close()
        self.VCF.close()
        rm_cmd = f"{self.bcftools} annotate -x FORMAT/ADS {self.output_tmp_file} -o {self.output_file} && rm -f {self.output_tmp_file}"
        run_command(rm_cmd)

def main():
    global project_dir
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description='Process VCF data.')
    parser.add_argument("-i", "--input", help="input fam vcf path", type=str, required=True)
    parser.add_argument("-o", "--output", help="output fam vcf path", type=str, required=True)
    parser.add_argument("-c", "--cram-dir", help="input cram dir", type=str, required=True)
    parser.add_argument("-r", "--ref-fa", help="input genome fasta path", type=str, required=True)
    parser.add_argument("--bcftools", help="input bcftools path", type=str, required=True)
    parser.add_argument("--pandepth", help="input pandepth path", type=str, required=True)
    parser.add_argument("--threads", type=int, default=8)
    args = parser.parse_args()
    DepthCorrect(
        args.input,
        args.cram_dir,
        args.output,
        args.ref_fa,
        args.bcftools,
        args.pandepth,
        args.threads,
    ).process_depth_correct()


if __name__=='__main__':
    main()
