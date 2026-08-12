import os
import subprocess
import argparse
import sys
import pandas as pd

def main(bam, region, out):
    sample_id = os.path.basename(bam).split(".")[0]
    data = {
        "Sample": [sample_id],
        "IVS16ins3kb(ref;alt)": [],
        "IVS4ins6kb(ref;alt)": [],
        "result": []
    }
    
    IVS16ins3kb_ref = int(subprocess.check_output(f"{samtools} view {bam} {region} --reference {reference} | grep 'CAAACTGGGGTGAGGATCGAAATACACGAGCTTTAAAAAAATGGAGAAATCACAGA' | wc -l", shell=True).decode().strip())
    IVS16ins3kb_alt = int(subprocess.check_output(f"{samtools} view {bam} {region} --reference {reference} | grep 'CAAACTGGGGTGAGGATCGAAATACACGAGCTTTAAAAAAATGGAGAAATCGGGGG' | wc -l", shell=True).decode().strip())
    
    IVS4ins6kb_ref = int(subprocess.check_output(f"{samtools} view {bam} {region} --reference {reference} | grep 'CTGAAAAGAGAAAAGACAGGTTGATTAAAACAAAGTAAATGAAGTTCTT' | wc -l", shell=True).decode().strip())
    IVS4ins6kb_alt = int(subprocess.check_output(f"{samtools} view {bam} {region} --reference {reference} | grep 'CTGAAAAGAGAAAAGACGAGACTGGCGGGGGAGGAGCCAAGATGGCCGA' | wc -l", shell=True).decode().strip())

    data["IVS16ins3kb(ref;alt)"].append(f"{IVS16ins3kb_ref};{IVS16ins3kb_alt}")
    data["IVS4ins6kb(ref;alt)"].append(f"{IVS4ins6kb_ref};{IVS4ins6kb_alt}")
    
    if IVS16ins3kb_alt == 0 and IVS4ins6kb_alt == 0:
        data["result"].append(".")
    elif IVS16ins3kb_alt>0 and IVS4ins6kb_alt == 0:
        data["result"].append("IVS16ins3kb")
    elif IVS16ins3kb_alt == 0 and IVS4ins6kb_alt>0:
        data["result"].append("IVS4ins6kb")
    else:
        data["result"].append("IVS16ins3kb;IVS4ins6kb")
    df = pd.DataFrame(data)
    df.to_csv(out, sep="\t", index=False)
    os.system(f"ls {out}")
    return()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copyright: Biosan Dx")
    parser.add_argument("-bam", required=True, type=str, help="<bam/cram_file> input bam/cram file")
    parser.add_argument("--samtools", help="samtools", type=str, required=True)
    parser.add_argument("--reference", help="reference", type=str, required=True)
    parser.add_argument("-r", "--region", required=True, type=str, help="<region> chr7:95750500-95838500")
    parser.add_argument("-o", "--out", required=True, type=str, help="<output_file> sample.SLC25A13.txt")
    args = parser.parse_args()
    global projectDir, samtools, reference
    projectDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samtools = args.samtools
    reference = args.reference
    if os.path.exists(args.bam):
        main(args.bam, args.region, args.out)
    else:
        sys.exit(0)