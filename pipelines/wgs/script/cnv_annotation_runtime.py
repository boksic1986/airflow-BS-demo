#!/usr/bin/env python3
"""Pure-standard-library runtime helpers for CNV annotation."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _file_facts(paths):
    facts = []
    for raw_path in paths:
        path = Path(raw_path)
        facts.append(
            {
                "path": path.name,
                "bytes": path.stat().st_size if path.exists() else None,
            }
        )
    return facts


def build_first_position_indexes(records):
    """Index positions while preserving the legacy first-match behavior."""
    start_index = {}
    end_index = {}
    for cnv_id, info in records.items():
        start_index.setdefault(info["start"], cnv_id)
        end_index.setdefault(info["end"], cnv_id)
    return start_index, end_index


def compile_phenotype_gene_sets(hash_phenotype):
    """Compile membership sets without changing retained gene-list text."""
    for info in hash_phenotype.values():
        info["_gene_set"] = frozenset(info["genelist"].split("|"))
    return hash_phenotype


def keyword_match_indexed(gene_list, phenotype_list, hash_phenotype):
    """Return legacy-formatted HPO matches using indexed membership tests."""
    genes = gene_list.split(",")
    matches = []
    for keyword in phenotype_list.split(","):
        if keyword not in hash_phenotype:
            print(
                "#Warning: "
                + keyword
                + " is not in phenotype_key_word_gene_list.txt!"
            )
            continue
        info = hash_phenotype[keyword]
        gene_set = info.get("_gene_set")
        if gene_set is None:
            gene_set = frozenset(info["genelist"].split("|"))
        gene_filter = [gene for gene in genes if gene in gene_set]
        if gene_filter:
            phenotype = keyword + "(" + info["phenotype_CN"] + ")"
            matches.append(";".join(gene_filter) + "[" + phenotype + "]")
    return "|".join(matches)


class ScratchWorkspace:
    """Own one automatically cleaned directory below a caller-selected root."""

    def __init__(self, base_dir):
        base_dir = Path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        self._temporary_directory = tempfile.TemporaryDirectory(
            prefix="cnv-annotation-",
            dir=str(base_dir),
        )
        self.root = Path(self._temporary_directory.name)

    def path(self, name):
        """Return an intermediate path without allowing directory escape."""
        path = self.root / name
        if path.parent != self.root:
            raise ValueError("scratch path must be a direct child")
        return path

    def cleanup(self):
        self._temporary_directory.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()


def atomic_publish(staging_path, output_path):
    """Atomically replace output with a staging file on the same filesystem."""
    staging_path = Path(staging_path)
    output_path = Path(output_path)
    if staging_path.parent.resolve() != output_path.parent.resolve():
        raise ValueError("staging and output must be in the same directory")
    os.replace(str(staging_path), str(output_path))


class StageRecorder:
    """Append privacy-safe, exclusive stage timings to one JSONL file."""

    def __init__(self, path):
        self.path = Path(path) if path else None
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def _append(
        self,
        *,
        name,
        started_at,
        ended_at,
        elapsed_seconds,
        exit_status,
        inputs,
        outputs,
    ):
        if self.path is None:
            return
        row = {
            "stage": name,
            "started_at": started_at,
            "ended_at": ended_at,
            "elapsed_seconds": elapsed_seconds,
            "exit_status": exit_status,
            "inputs": _file_facts(inputs),
            "outputs": _file_facts(outputs),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            )

    def start(self, name, inputs=()):
        return {
            "name": name,
            "started_at": _utc_now(),
            "started": time.perf_counter(),
            "inputs": tuple(inputs),
        }

    def finish(self, token, outputs=(), exit_status=0):
        self._append(
            name=token["name"],
            started_at=token["started_at"],
            ended_at=_utc_now(),
            elapsed_seconds=time.perf_counter() - token["started"],
            exit_status=exit_status,
            inputs=token["inputs"],
            outputs=outputs,
        )
    @contextmanager
    def measure(self, name, inputs=(), outputs=()):
        started_at = _utc_now()
        started = time.perf_counter()
        exit_status = 0
        try:
            yield
        except subprocess.CalledProcessError as error:
            exit_status = error.returncode
            raise
        except BaseException:
            exit_status = 1
            raise
        finally:
            self._append(
                name=name,
                started_at=started_at,
                ended_at=_utc_now(),
                elapsed_seconds=time.perf_counter() - started,
                exit_status=exit_status,
                inputs=inputs,
                outputs=outputs,
            )

    def run(
        self,
        name,
        command,
        *,
        shell=False,
        inputs=(),
        outputs=(),
        **kwargs,
    ):
        with self.measure(name, inputs=inputs, outputs=outputs):
            return subprocess.run(
                command,
                shell=shell,
                check=True,
                **kwargs,
            )
