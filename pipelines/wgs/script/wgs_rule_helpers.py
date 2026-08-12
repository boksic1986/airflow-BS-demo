#!/usr/bin/env python3
"""CLI helpers for Python logic moved out of Snakemake ``run:`` rules."""

import argparse
import csv
import json
import os
import subprocess
import sys


def write_fastq_count(inputs, output):
    """Write the legacy CNV read-count table from fastp JSON reports."""
    with open(output, "w", encoding="utf-8") as target:
        for source in inputs:
            basename = os.path.basename(os.fspath(source))
            suffix = ".fastp.json"
            if not basename.endswith(suffix):
                raise ValueError("fastp JSON name must end with " + suffix)
            sample = basename[:-len(suffix)]
            with open(source, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            summary = data["summary"]["before_filtering"]
            for read_number in (1, 2):
                read = data["read{}_before_filtering".format(read_number)]
                total_bases = read["total_bases"]
                q20 = round(read["q20_bases"] / total_bases * 100, 3)
                q30 = round(read["q30_bases"] / total_bases * 100, 3)
                mean_length = summary.get(
                    "read{}_mean_length".format(read_number), 150
                )
                target.write(
                    "{}-R{}.fq.gz\t{}\t{}\t{}\t{}\t{}\n".format(
                        sample,
                        read_number,
                        read["total_reads"],
                        total_bases,
                        mean_length,
                        q20,
                        q30,
                    )
                )


def write_copy_number(sample, input_path, output_path):
    """Extract the fourth CN-bed column for the legacy batch paste step."""
    with open(output_path, "w", encoding="utf-8") as target:
        target.write(sample + "\n")
        with open(input_path, "r", encoding="utf-8") as source:
            for line in source:
                fields = line.strip().split()
                if len(fields) < 4:
                    continue
                try:
                    value = "{:.2f}".format(float(fields[3]))
                except ValueError:
                    value = fields[3]
                target.write(value + "\n")


def run_cnv_annotation(args):
    """Run the pipeline CNV annotation script with explicit CLI arguments."""
    command = [
        sys.executable,
        args.annotation_script,
        "-I",
        args.input,
        "-O",
        args.output,
        "-s",
        args.sample,
        "--hpo",
        args.phenotype or "null",
        "--ped",
        args.pedigree,
        "-cfg",
        args.config,
        "--bedtools",
        args.bedtools,
        "--bcftools",
        args.bcftools,
        "--annotsv",
        args.annotsv,
        "--liftover",
        args.liftover,
    ]
    subprocess.check_call(command)


def read_sample_gender(gender_path, sample):
    """Return one sample's legacy gender code, or ND when it is absent."""
    gender = "ND"
    with open(gender_path, "r", encoding="utf-8", newline="") as source:
        for row in csv.reader(source):
            if len(row) >= 2 and row[0] == sample:
                gender = row[1]
    return gender


def run_solo_annotation(args):
    """Run the SNV annotation Perl script outside a Snakemake run block."""
    command = [
        args.perl,
        args.annotation_script,
        "-g",
        read_sample_gender(args.gender_file, args.sample),
        "-p",
        args.phenotype,
        "-i",
        args.input,
        "-o",
        args.output,
        "-v",
        args.vep,
        "-cfg",
        args.config,
        "-liftover",
        args.liftover,
    ]
    subprocess.check_call(command)


def write_file_list(inputs, output_path):
    """Write one input path per line for tools that consume manifests."""
    with open(output_path, "w", encoding="utf-8") as target:
        for path in inputs:
            target.write(os.fspath(path) + "\n")


def write_bam_list(inputs, output_path):
    """Write one CRAM/BAM path per line for SMN/CYP callers."""
    write_file_list(inputs, output_path)


def write_gender(input_path, output_path):
    """Convert mappingQC.csv to the two-column legacy gender table."""
    with open(input_path, "r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = {"Sample", "Gender"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("mappingQC.csv must contain Sample and Gender columns")
        rows = [
            (row["Sample"].replace("-R1.fq.gz", ""), row["Gender"])
            for row in reader
        ]
    with open(output_path, "w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target, lineterminator="\n")
        writer.writerows(rows)


def split_sma(input_path, output_dir):
    """Split the batch SMN table into one legacy result per sample."""
    os.makedirs(output_dir, exist_ok=True)
    with open(input_path, "r", encoding="utf-8") as source:
        header = source.readline().rstrip("\r\n")
        for line in source:
            fields = line.rstrip("\r\n").split("\t")
            if not fields or not fields[0]:
                continue
            sample = fields[0].split(".")[0]
            output = os.path.join(output_dir, sample + ".SMA.tsv")
            with open(output, "w", encoding="utf-8") as target:
                target.write(header + "\n")
                target.write(sample + "\t" + "\t".join(fields[1:]) + "\n")


def split_cyp2d6(input_path, output_dir):
    """Split the batch CYP2D6 table into one legacy result per sample."""
    os.makedirs(output_dir, exist_ok=True)
    with open(input_path, "r", encoding="utf-8") as source:
        for line in source:
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) < 2 or not fields[0]:
                continue
            sample = fields[0].split(".")[0]
            output = os.path.join(output_dir, sample + ".CYP2D6.tsv")
            with open(output, "w", encoding="utf-8") as target:
                target.write("CYP2D6\t{}\n".format(fields[1]))


def expansionhunter_sex(qc_path):
    """Return ExpansionHunter sex value from a WGS QC table."""
    with open(qc_path, "r", encoding="utf-8", newline="") as source:
        rows = csv.reader(source, delimiter="\t")
        try:
            header = next(rows)
        except StopIteration:
            raise ValueError("QC table is empty")
        candidates = ("\u9884\u6d4b\u6027\u522b", "predicted_gender", "Gender")
        index = next((header.index(name) for name in candidates if name in header), None)
        if index is None:
            raise ValueError("QC table does not contain a predicted-gender column")
        values = [row[index] for row in rows if len(row) > index and row[index].strip()]
    if not values:
        raise ValueError("QC table does not contain a gender value")
    value = values[-1].strip().upper()
    if value == "M":
        return "male"
    if value == "F":
        return "female"
    raise ValueError("sex must be M or F, got: " + value)


def expansionhunter_json_to_text(input_path, output_path):
    """Convert ExpansionHunter JSON loci into the legacy tabular output."""
    with open(input_path, "r", encoding="utf-8") as source:
        data = json.load(source)
    columns = (
        "VariantId ReferenceRegion RepeatUnit Genotype GenotypeConfidenceInterval "
        "CountsOfSpanningReads CountsOfFlankingReads CountsOfInrepeatReads "
        "LocusId AlleleCount Coverage FragmentLength"
    ).split()
    with open(output_path, "w", encoding="utf-8", newline="") as output:
        output.write("\t".join(columns) + "\n")
        for locus_id, locus in data["LocusResults"].items():
            locus_values = [
                locus_id,
                locus["AlleleCount"],
                locus["Coverage"],
                locus["FragmentLength"],
            ]
            for variant in locus["Variants"].values():
                genotype = (
                    "{" + variant["Genotype"] + "}"
                    if "Genotype" in variant
                    else "."
                )
                interval = (
                    "{" + variant["GenotypeConfidenceInterval"] + "}"
                    if "GenotypeConfidenceInterval" in variant
                    else "."
                )
                variant_values = [
                    variant["VariantId"],
                    variant["ReferenceRegion"],
                    variant["RepeatUnit"],
                    genotype,
                    interval,
                    variant["CountsOfSpanningReads"],
                    variant["CountsOfFlankingReads"],
                    variant["CountsOfInrepeatReads"],
                ]
                output.write(
                    "\t".join(str(value) for value in variant_values + locus_values)
                    + "\n"
                )


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fastq_parser = subparsers.add_parser("fastq-count")
    fastq_parser.add_argument("--output", required=True)
    fastq_parser.add_argument("inputs", nargs="+")

    copy_number_parser = subparsers.add_parser("copy-number")
    copy_number_parser.add_argument("--sample", required=True)
    copy_number_parser.add_argument("--input", required=True)
    copy_number_parser.add_argument("--output", required=True)

    cnv_parser = subparsers.add_parser("cnv-annotation")
    for name in (
        "sample", "phenotype", "pedigree", "input", "output",
        "annotation-script", "config", "bedtools", "bcftools", "annotsv",
        "liftover",
    ):
        cnv_parser.add_argument("--" + name, required=True)

    snv_parser = subparsers.add_parser("solo-annotation")
    for name in (
        "sample", "phenotype", "gender-file", "input", "output", "vep",
        "annotation-script", "config", "perl", "liftover",
    ):
        snv_parser.add_argument("--" + name, required=True)

    bam_list_parser = subparsers.add_parser("bam-list")
    bam_list_parser.add_argument("--output", required=True)
    bam_list_parser.add_argument("inputs", nargs="+")

    file_list_parser = subparsers.add_parser("file-list")
    file_list_parser.add_argument("--output", required=True)
    file_list_parser.add_argument("inputs", nargs="+")

    gender_parser = subparsers.add_parser("gender")
    gender_parser.add_argument("--input", required=True)
    gender_parser.add_argument("--output", required=True)

    sma_parser = subparsers.add_parser("sma-split")
    sma_parser.add_argument("--input", required=True)
    sma_parser.add_argument("--output-dir", required=True)

    cyp_parser = subparsers.add_parser("cyp2d6-split")
    cyp_parser.add_argument("--input", required=True)
    cyp_parser.add_argument("--output-dir", required=True)

    sex_parser = subparsers.add_parser("expansionhunter-sex")
    sex_parser.add_argument("--qc", required=True)
    json_parser = subparsers.add_parser("expansionhunter-json")
    json_parser.add_argument("--input", required=True)
    json_parser.add_argument("--output", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "fastq-count":
        write_fastq_count(args.inputs, args.output)
    elif args.command == "copy-number":
        write_copy_number(args.sample, args.input, args.output)
    elif args.command == "cnv-annotation":
        run_cnv_annotation(args)
    elif args.command == "solo-annotation":
        run_solo_annotation(args)
    elif args.command == "bam-list":
        write_bam_list(args.inputs, args.output)
    elif args.command == "file-list":
        write_file_list(args.inputs, args.output)
    elif args.command == "gender":
        write_gender(args.input, args.output)
    elif args.command == "sma-split":
        split_sma(args.input, args.output_dir)
    elif args.command == "cyp2d6-split":
        split_cyp2d6(args.input, args.output_dir)
    elif args.command == "expansionhunter-sex":
        print(expansionhunter_sex(args.qc))
    elif args.command == "expansionhunter-json":
        expansionhunter_json_to_text(args.input, args.output)
    else:
        raise ValueError("unsupported command: " + args.command)


if __name__ == "__main__":
    main()
