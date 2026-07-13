from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nipt_docker_runner import prepare_nipt_docker_run
from pgta_metadata_runner import build_pgta_config
from common.pipeline_profiles import (
    ResolvedRuntimeProfile,
    _verify_pgta_release_integrity,
    validate_runtime_profile_availability,
)


class ConfigOverrideRunnerTests(unittest.TestCase):
    def test_repository_nipt_s9_profile_is_default_and_keeps_s7_rollback(self) -> None:
        profile_path = Path(__file__).resolve().parents[2] / "config" / "pipeline_profiles.yaml"
        payload = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        nipt = payload["pipelines"]["nipt_docker"]
        profile = nipt["profiles"]["niptpro-s9-full-v1"]
        rollback = nipt["profiles"]["niptpro-1.0.11"]

        self.assertEqual(nipt["default_profile"], "niptpro-s9-full-v1")
        self.assertEqual(profile["runtime"]["docker_image"], "airflow-demo/niptpro:1.0.11-snakemake9.23.1-v1")
        self.assertEqual(profile["runtime"]["snakemake_version"], "9.23.1")
        self.assertEqual(profile["runtime"]["cores"], 32)
        self.assertTrue(profile["submit_visible"])
        self.assertFalse(rollback["submit_visible"])

    def test_repository_pgta_s9_profile_exposes_only_predict_parameters(self) -> None:
        profile_path = Path(__file__).resolve().parents[2] / "config" / "pipeline_profiles.yaml"
        payload = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        pgta = payload["pipelines"]["pgta"]
        profile = pgta["profiles"]["pgta-s9-predict-v1"]

        self.assertEqual(pgta["default_profile"], "pgta-s9-predict-v1")
        self.assertEqual(profile["pipeline_version"], "pgta-s9-v1.4")
        self.assertTrue(profile["submit_visible"])
        self.assertEqual(
            set(profile["editable_schema"]),
            {
                "core.wisecondorx.cnv.zscore",
                "core.wisecondorx.cnv.alpha",
                "core.wisecondorx.cnv.maskrepeats",
                "core.wisecondorx.cnv.minrefbins",
                "core.wisecondorx.cnv.qc.min_total_counts",
                "core.wisecondorx.cnv.qc.min_nonzero_fraction",
                "core.wisecondorx.cnv.qc.max_mad_log1p",
            },
        )
        self.assertNotIn("build_reference", profile["editable_defaults"])
        self.assertNotIn("reference_output", profile["editable_defaults"])
        self.assertEqual(
            profile["runtime"]["rscript_bin"],
            "/biosoftware/miniconda/envs/wise_env/bin/Rscript",
        )

    def test_airflow_worker_mounts_pipeline_profile_config(self) -> None:
        compose = (Path(__file__).resolve().parents[2] / "docker-compose.yaml").read_text(
            encoding="utf-8"
        )
        worker_section = compose.split("  airflow-worker:\n", 1)[1].split(
            "\nvolumes:\n", 1
        )[0]

        self.assertIn("./config:/opt/airflow/config:ro", worker_section)

    def test_airflow_services_use_bounded_docker_logs(self) -> None:
        compose = (Path(__file__).resolve().parents[2] / "docker-compose.yaml").read_text(encoding="utf-8")

        self.assertIn('max-size: "50m"', compose)
        self.assertIn('max-file: "3"', compose)
        self.assertIn("logging: *airflow-logging", compose)

    def test_runtime_profile_availability_rejects_missing_pgta_executable(self) -> None:
        profile = ResolvedRuntimeProfile(
            profile_id="pgta-current",
            template_hash="hash",
            runtime={"snakemake_bin": "/missing/approved/snakemake"},
            editable_config={},
            editable_schema={},
        )

        with self.assertRaisesRegex(ValueError, "snakemake_bin"):
            validate_runtime_profile_availability(profile, pipeline="pgta")

    def test_pgta_release_integrity_rejects_modified_release_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            release = Path(tmpdir)
            snakefile = release / "Snakefile"
            snakefile.write_text("rule all:\n    input: []\n", encoding="utf-8")
            original_hash = hashlib.sha256(snakefile.read_bytes()).hexdigest()
            manifest = release / "SHA256SUMS"
            manifest.write_text(f"{original_hash}  ./Snakefile\n", encoding="utf-8")
            manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
            snakefile.write_text("rule changed:\n    input: []\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "release file checksum"):
                _verify_pgta_release_integrity(
                    {
                        "pipeline_root": str(release),
                        "release_manifest": str(manifest),
                        "release_manifest_sha256": manifest_hash,
                    }
                )

    def test_runtime_profile_availability_rejects_missing_nipt_image(self) -> None:
        profile = ResolvedRuntimeProfile(
            profile_id="niptpro-1.0.11",
            template_hash="hash",
            runtime={"docker_image": "approved/niptpro:1.0.11"},
            editable_config={},
            editable_schema={},
        )

        with self.assertRaisesRegex(ValueError, "docker_image"):
            validate_runtime_profile_availability(
                profile,
                pipeline="nipt_docker",
                docker_executable="/usr/bin/docker",
                command_runner=lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr="No such image"),
            )

    def test_pgta_prepare_merges_requested_yaml_and_records_resolved_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workdir = root / "shared" / "runs" / "PGTA_CONFIG_TEST"
            data_root = root / "pgta-data"
            sample_dir = data_root / "rawdata" / "batch"
            sample_dir.mkdir(parents=True)
            r1 = sample_dir / "G1_R1.fastq.gz"
            r2 = sample_dir / "G1_R2.fastq.gz"
            r1.write_text("r1\n", encoding="utf-8")
            r2.write_text("r2\n", encoding="utf-8")
            config_dir = workdir / "config"
            config_dir.mkdir(parents=True)
            manifest = config_dir / "samples.selected.tsv"
            manifest.write_text(
                "sample_id\tR1\tR2\tsource_dir\n"
                f"G1\t{r1}\t{r2}\t{sample_dir}\n",
                encoding="utf-8",
            )
            profile_path, profile_hash = _write_profiles(root, "pgta-current")
            requested = (
                "core:\n"
                "  wisecondorx:\n"
                "    reference_prefilter:\n"
                "      max_iterations: 5\n"
            )
            (config_dir / "snakemake.user.yaml").write_text(requested, encoding="utf-8")
            _write_waiting_provenance(config_dir, "pgta-current", profile_hash, requested)
            conf = {
                "analysis_id": "PGTA_CONFIG_TEST",
                "pipeline": "pgta",
                "mode": "new",
                "workdir": str(workdir),
                "sample_sheet_path": str(manifest),
                "params": _config_params("pgta-current", profile_hash, requested, target="metadata"),
            }

            with patch.dict("os.environ", {"PIPELINE_PROFILE_CONFIG_PATH": str(profile_path)}):
                config_path = build_pgta_config(
                    conf,
                    pgta_pipeline_root=root / "PGT_A",
                    pgta_data_root=data_root,
                    samtools_bin=root / "bin" / "samtools",
                    samtools_library_path=None,
                    reference_genome=root / "references" / "hg19.fa",
            )

            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            resolved_path = config_dir / "snakemake.resolved.yaml"
            self.assertTrue(resolved_path.is_file())
            resolved = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
            provenance = json.loads((config_dir / "config_provenance.json").read_text(encoding="utf-8"))

        self.assertEqual(config["core"]["wisecondorx"]["reference_prefilter"]["max_iterations"], 5)
        self.assertEqual(config["biosoft"]["fastp"], "/approved/fastp")
        self.assertEqual(config["biosoft"]["bwa"], "/approved/bwa")
        self.assertEqual(config["biosoft"]["WisecondorX"], "/approved/WisecondorX")
        self.assertEqual(config["biosoft"]["python"], "/approved/python")
        self.assertEqual(resolved, config)
        self.assertEqual(provenance["state"], "resolved")
        self.assertTrue(provenance["resolved_config_hash"])

    def test_nipt_prepare_uses_approved_image_and_merges_requested_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workdir = root / "shared" / "runs" / "NIPT_CONFIG_TEST"
            config_dir = workdir / "config"
            config_dir.mkdir(parents=True)
            nipt_root = root / "NIPT"
            (nipt_root / "niptplus").mkdir(parents=True)
            (nipt_root / "niptplus" / "config.yaml").write_text(
                "database:\n"
                "  marker: profile-root\n"
                "params:\n"
                "  sexcutoff: 0.00007\n"
                "  seed: 9696\n"
                "  map_threads: 4\n"
                "  aneuscreen_threads: 10\n"
                "mapper_v2:\n"
                "  workers: 4\n"
                "  worker_auto_max: 4\n"
                "  pipe_buffer_bytes: 4194304\n",
                encoding="utf-8",
            )
            source_batch = nipt_root / "fastq" / "batch1"
            source_batch.mkdir(parents=True)
            r1 = source_batch / "NIPT1.A01.R1.clean.fastq.gz"
            r2 = source_batch / "NIPT1.A01.R2.clean.fastq.gz"
            r1.write_text("r1\n", encoding="utf-8")
            r2.write_text("r2\n", encoding="utf-8")
            manifest = config_dir / "samples.selected.tsv"
            manifest.write_text(
                "sample_id\tlibrary\tindex\tR1\tR2\tsource_dir\tcomment\n"
                f"NIPT1.A01\tNIPT1\tA01\t{r1}\t{r2}\t{source_batch}\tNIPT\n",
                encoding="utf-8",
            )
            profile_path, profile_hash = _write_profiles(root, "niptpro-1.0.11")
            requested = "params:\n  sexcutoff: 0.00008\n  map_threads: 6\n"
            (config_dir / "snakemake.user.yaml").write_text(requested, encoding="utf-8")
            _write_waiting_provenance(config_dir, "niptpro-1.0.11", profile_hash, requested)
            conf = {
                "analysis_id": "NIPT_CONFIG_TEST",
                "pipeline": "nipt_docker",
                "mode": "new",
                "workdir": str(workdir),
                "sample_sheet_path": str(manifest),
                "params": {
                    **_config_params("niptpro-1.0.11", profile_hash, requested),
                    "input_mode": "nipt_docker_scan",
                    "source_batch_dir": str(source_batch),
                    "chip_name": "batch1",
                    "run_mode": "mount_smoke",
                    "cores": 40,
                },
            }

            with patch.dict("os.environ", {"PIPELINE_PROFILE_CONFIG_PATH": str(profile_path)}):
                prepared = prepare_nipt_docker_run(
                    conf,
                    nipt_pipeline_root=nipt_root,
                    host_nipt_pipeline_root=Path("/host/NIPT"),
                    host_shared_root=Path("/host/shared"),
                    docker_image="unapproved/image:latest",
                    fetal_image="unapproved/fetal:latest",
                    docker_network="nipt_analysis_test_net",
                    owner="6708:520",
                )

            run_config = yaml.safe_load(Path(prepared["run_config_path"]).read_text(encoding="utf-8"))
            compose = yaml.safe_load(Path(prepared["compose_path"]).read_text(encoding="utf-8"))
            resolved_path = config_dir / "snakemake.resolved.yaml"
            self.assertTrue(resolved_path.is_file())
            resolved = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))

        self.assertEqual(run_config["params"]["sexcutoff"], 0.00008)
        self.assertEqual(run_config["params"]["map_threads"], 6)
        self.assertEqual(run_config["database"]["marker"], "profile-root")
        self.assertEqual(resolved, run_config)
        self.assertEqual(compose["services"]["runner"]["image"], "approved/niptpro:1.0.11")

    def test_prepare_rejects_tampered_requested_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workdir = root / "shared" / "runs" / "PGTA_TAMPER_TEST"
            data_root = root / "pgta-data"
            sample_dir = data_root / "rawdata" / "batch"
            sample_dir.mkdir(parents=True)
            r1 = sample_dir / "G1_R1.fastq.gz"
            r2 = sample_dir / "G1_R2.fastq.gz"
            r1.write_text("r1\n", encoding="utf-8")
            r2.write_text("r2\n", encoding="utf-8")
            config_dir = workdir / "config"
            config_dir.mkdir(parents=True)
            manifest = config_dir / "samples.selected.tsv"
            manifest.write_text(
                "sample_id\tR1\tR2\tsource_dir\n"
                f"G1\t{r1}\t{r2}\t{sample_dir}\n",
                encoding="utf-8",
            )
            profile_path, profile_hash = _write_profiles(root, "pgta-current")
            original = "core:\n  wisecondorx:\n    reference_prefilter:\n      max_iterations: 5\n"
            tampered = "biosoft:\n  python: /tmp/unsafe\n"
            (config_dir / "snakemake.user.yaml").write_text(tampered, encoding="utf-8")
            conf = {
                "analysis_id": "PGTA_TAMPER_TEST",
                "pipeline": "pgta",
                "mode": "new",
                "workdir": str(workdir),
                "sample_sheet_path": str(manifest),
                "params": _config_params("pgta-current", profile_hash, original, target="metadata"),
            }

            with patch.dict("os.environ", {"PIPELINE_PROFILE_CONFIG_PATH": str(profile_path)}):
                with self.assertRaisesRegex(ValueError, "requested config hash"):
                    build_pgta_config(
                        conf,
                        pgta_pipeline_root=root / "PGT_A",
                        pgta_data_root=data_root,
                        samtools_bin=root / "bin" / "samtools",
                        samtools_library_path=None,
                        reference_genome=root / "references" / "hg19.fa",
                    )


def _write_profiles(root: Path, requested_profile: str) -> tuple[Path, str]:
    pgta_profile = {
        "label": "PGT-A current",
        "pipeline_version": "current",
        "config_version": "1",
        "runtime": {
            "snakemake_bin": "/approved/snakemake",
            "python_bin": "/approved/python",
            "fastp_bin": "/approved/fastp",
            "bwa_bin": "/approved/bwa",
            "wisecondorx_bin": "/approved/WisecondorX",
        },
        "editable_defaults": {
            "core": {"wisecondorx": {"reference_prefilter": {"max_iterations": 3}}}
        },
        "editable_schema": {
            "core.wisecondorx.reference_prefilter.max_iterations": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
            }
        },
    }
    nipt_profile = {
        "label": "NIPTPro 1.0.11",
        "pipeline_version": "1.0.11",
        "config_version": "v3.2.5.1",
        "runtime": {
            "docker_image": "approved/niptpro:1.0.11",
            "fetal_image": "approved/fetal:biosan",
            "pipeline_root": str(root / "NIPT"),
        },
        "editable_defaults": {
            "params": {"sexcutoff": 0.00007, "map_threads": 4}
        },
        "editable_schema": {
            "params.sexcutoff": {"type": "number", "minimum": 0, "maximum": 0.01},
            "params.map_threads": {"type": "integer", "minimum": 1, "maximum": 40},
        },
    }
    payload = {
        "version": 1,
        "pipelines": {
            "pgta": {"default_profile": "pgta-current", "profiles": {"pgta-current": pgta_profile}},
            "nipt_docker": {
                "default_profile": "niptpro-1.0.11",
                "profiles": {"niptpro-1.0.11": nipt_profile},
            },
        },
    }
    path = root / "pipeline_profiles.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    pipeline = "nipt_docker" if requested_profile.startswith("nipt") else "pgta"
    profile = payload["pipelines"][pipeline]["profiles"][requested_profile]
    return path, _profile_hash(requested_profile, profile)


def _profile_hash(profile_id: str, profile: dict) -> str:
    canonical = json.dumps(
        {"id": profile_id, "profile": profile},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _config_params(profile_id: str, profile_hash: str, requested: str, **extra) -> dict:
    return {
        **extra,
        "runtime_profile_id": profile_id,
        "config_template_hash": profile_hash,
        "config_requested_hash": hashlib.sha256(requested.encode("utf-8")).hexdigest(),
    }


def _write_waiting_provenance(config_dir: Path, profile_id: str, profile_hash: str, requested: str) -> None:
    (config_dir / "config_provenance.json").write_text(
        json.dumps(
            {
                "state": "waiting_for_prepare",
                "runtime_profile_id": profile_id,
                "config_template_hash": profile_hash,
                "config_requested_hash": hashlib.sha256(requested.encode("utf-8")).hexdigest(),
                "resolved_config_hash": None,
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
