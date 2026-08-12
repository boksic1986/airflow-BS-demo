import os
import gzip
import pandas as pd
import argparse

# /bi/software/micromamba/bin/python /bi/26.zengkexin/WGS/wgs/script/z2.BJXH.format.py -i /bi/26.zengkexin/WGS/V3.6.7/sampleinfo/WGS_20250730_T7Hg38V3.6.6.1.sampleinfo.txt -l sampleList.txt 

def get_options():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-i', '--info', required=True, type=str)
    parser.add_argument('-l', '--list', required=True, type=str) 
    return parser.parse_args()

def main():
    args=get_options()
    outdir = os.path.abspath(os.getcwd())
    batch = os.path.basename(os.getcwd())
       
    xiehe_dir = os.path.join(outdir, batch)  
    os.makedirs(xiehe_dir,exist_ok=True)
    df = pd.read_csv(args.info, sep='\t').set_index('样本编号')

    with open(args.list) as f:
        for line in f:
            sample = line.strip()
            barcode = df.at[sample, '样本条码']
            barcode_WGS = f"{barcode}-WGS"
            raw_vcf =f"01_SNV/{sample}-WGS.raw.vcf.gz"
            if not os.path.exists(raw_vcf):
                print(f"{raw_vcf} 不存在，请核查！")
                continue
            new_lines = []
            with gzip.open(raw_vcf, 'rt') as files:
                for file in files:
                    if file.startswith("##bcftools") or file.startswith("##SentieonCommandLine"): 
                        continue
                    if file.startswith("#CHROM"):
                        file = file.replace(file.split()[-1], barcode_WGS) 
                    new_lines.append(file)

            out_file = os.path.join(xiehe_dir, f"{barcode}-WGS.final.vcf.gz")
            with gzip.open(out_file, 'wt') as fo:
                fo.writelines(new_lines)


if __name__ == '__main__':
    main()