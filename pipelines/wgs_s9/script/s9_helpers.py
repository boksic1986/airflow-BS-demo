from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def read_fastp_json(input_paths: Iterable[str], input_dir: str, suffix: str, output_path: str) -> None:
    """Write the legacy WGS fastp count table without importing the old Python 3.7 helper stack."""
    root = Path(input_dir)
    with Path(output_path).open("w", encoding="utf-8") as output:
        for raw_path in input_paths:
            relative_path = str(raw_path)
            if not relative_path.endswith(suffix):
                continue
            sample_name = relative_path.replace(".template.json", "").replace("07_QC/", "")
            with (root / relative_path).open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            summary = payload["summary"]["before_filtering"]
            for read_number in (1, 2):
                metrics = payload[f"read{read_number}_before_filtering"]
                total_bases = metrics["total_bases"]
                q20 = round(metrics["q20_bases"] / total_bases * 100, 3)
                q30 = round(metrics["q30_bases"] / total_bases * 100, 3)
                mean_length = summary.get(f"read{read_number}_mean_length", 150)
                output.write(
                    "\t".join(
                        [
                            f"{sample_name}-R{read_number}.fq.gz",
                            str(metrics["total_reads"]),
                            str(total_bases),
                            str(mean_length),
                            str(q20),
                            str(q30),
                        ]
                    )
                    + "\n"
                )
