#!/biosoftware/miniconda/envs/snakemake_env/bin/python
import argparse
import csv
import re
import shlex
import subprocess
from pathlib import Path

from pipeline_logging import setup_logger


def run_command(command, logger):
    logger.info("$ %s", " ".join(shlex.quote(part) for part in command))
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if process.stdout is None:
        raise RuntimeError("Failed to capture command stdout.")

    output_lines = []
    for line in process.stdout:
        line = line.rstrip("\n")
        output_lines.append(line)
        if line:
            logger.info("[cmd] %s", line)

    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    return "\n".join(output_lines)


def parse_gender_output(raw_output):
    matches = re.findall(r"\b(Female|Male|F|M)\b", raw_output, flags=re.IGNORECASE)
    if not matches:
        raise ValueError(f"Unable to parse WisecondorX gender output: {raw_output!r}")

    token = matches[-1].upper()
    wise_gender = "F" if token in {"F", "FEMALE"} else "M"
    sex_call = "XX" if wise_gender == "F" else "XY"
    return sex_call, wise_gender


def write_gender_tsv(output_tsv, sample_id, sex_call, wise_gender, raw_output):
    output_path = Path(output_tsv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    compact_output = re.sub(r"\s+", " ", raw_output).strip()
    with open(output_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["sample_id", "sex_call", "wise_gender", "raw_output"])
        writer.writerow([sample_id, sex_call, wise_gender, compact_output])


def run_wisecondorx_gender(wisecondorx, sample_npz, gender_reference, output_tsv, sample_id, logger):
    raw_output = run_command(
        [
            wisecondorx,
            "gender",
            str(sample_npz),
            str(gender_reference),
        ],
        logger,
    )
    sex_call, wise_gender = parse_gender_output(raw_output)
    write_gender_tsv(output_tsv, sample_id, sex_call, wise_gender, raw_output)
    logger.info("gender call completed: sample=%s sex_call=%s wise_gender=%s", sample_id, sex_call, wise_gender)


def main():
    parser = argparse.ArgumentParser(description="Run WisecondorX gender and write a structured TSV result.")
    parser.add_argument("--wisecondorx", required=True)
    parser.add_argument("--sample-npz", required=True)
    parser.add_argument("--gender-reference", required=True)
    parser.add_argument("--output-tsv", required=True)
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--log", default="", help="Optional log file path")
    args = parser.parse_args()

    logger = setup_logger("wisecondorx_gender", args.log or None)
    run_wisecondorx_gender(
        wisecondorx=args.wisecondorx,
        sample_npz=args.sample_npz,
        gender_reference=args.gender_reference,
        output_tsv=args.output_tsv,
        sample_id=args.sample_id,
        logger=logger,
    )


if __name__ == "__main__":
    main()
