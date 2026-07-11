#!/biosoftware/miniconda/envs/snakemake_env/bin/python
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pipeline_logging import setup_logger


def run_text(command, cwd=None):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = (result.stdout or "").strip()
        if not output:
            output = f"<empty> (exit={result.returncode})"
        return output.replace("\n", " | ")
    except Exception as exc:
        return f"<error: {exc}>"


def collect_run_metadata(output, project_root, fastp, bwa, samtools, wisecondorx, python_bin, logger):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    project_root = Path(project_root)
    logger.info("collecting run metadata under %s", project_root)

    rows = []
    rows.append(("generated_utc", datetime.now(timezone.utc).isoformat()))
    rows.append(("project_root", str(project_root.resolve())))
    rows.append(("git_branch", run_text(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_root)))
    rows.append(("git_commit", run_text(["git", "rev-parse", "HEAD"], cwd=project_root)))
    rows.append(("git_status_short", run_text(["git", "status", "--short"], cwd=project_root)))
    rows.append(("fastp_version", run_text([str(fastp), "--version"])))
    rows.append(("bwa_version", run_text([str(bwa)], cwd=project_root)))
    rows.append(("samtools_version", run_text([str(samtools), "--version"])))
    rows.append(("wisecondorx_version", run_text([str(wisecondorx), "--version"])))
    rows.append(("python_version", run_text([str(python_bin), "--version"])))

    with open(output, "w", encoding="utf-8") as handle:
        handle.write("key\tvalue\n")
        for key, value in rows:
            handle.write(f"{key}\t{value}\n")
    logger.info("metadata written: %s (%d rows)", output, len(rows))


def main():
    parser = argparse.ArgumentParser(description="Collect reproducibility metadata for pipeline runs.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--fastp", required=True)
    parser.add_argument("--bwa", required=True)
    parser.add_argument("--samtools", required=True)
    parser.add_argument("--wisecondorx", required=True)
    parser.add_argument("--python-bin", required=True)
    parser.add_argument("--log", default="", help="Optional log file path")
    args = parser.parse_args()
    logger = setup_logger("collect_run_metadata", args.log or None)
    collect_run_metadata(
        output=args.output,
        project_root=args.project_root,
        fastp=args.fastp,
        bwa=args.bwa,
        samtools=args.samtools,
        wisecondorx=args.wisecondorx,
        python_bin=args.python_bin,
        logger=logger,
    )


if __name__ == "__main__":
    main()
