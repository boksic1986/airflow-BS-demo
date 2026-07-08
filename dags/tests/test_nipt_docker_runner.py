import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import nipt_docker_runner
from nipt_docker_runner import (
    collect_nipt_artifacts,
    generate_nipt_compose,
    prepare_nipt_docker_run,
    run_nipt_docker,
    validate_nipt_conf,
    write_nipt_qc_summary_from_outputs,
)


class NiptDockerRunnerTests(unittest.TestCase):
    def _valid_conf(self, workdir: Path) -> dict:
        return {
            "analysis_id": "NIPT_20260708_120000_TEST01",
            "pipeline": "nipt_docker",
            "mode": "new",
            "workdir": str(workdir),
            "sample_sheet_path": str(workdir / "config" / "samples.selected.tsv"),
            "params": {
                "template_id": "run1",
                "run_mode": "mount_smoke",
                "chip_name": "260414_TPNB500380AR_1065_AH32CCBGY2",
                "cores": 40,
            },
        }

    def _scan_conf(self, workdir: Path, source_batch_dir: Path) -> dict:
        return {
            "analysis_id": "NIPT_20260708_120000_SCAN01",
            "pipeline": "nipt_docker",
            "mode": "new",
            "workdir": str(workdir),
            "sample_sheet_path": str(workdir / "config" / "samples.selected.tsv"),
            "params": {
                "input_mode": "nipt_docker_scan",
                "source_batch_dir": str(source_batch_dir),
                "chip_name": "260414_TPNB500380AR_1065_AH32CCBGY2",
                "run_mode": "mount_smoke",
                "cores": 40,
                "selected_count": 1,
            },
        }

    def test_validate_nipt_conf_accepts_template_mount_smoke_only_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            workdir = shared_root / "runs" / "NIPT_20260708_120000_TEST01"
            (workdir / "config").mkdir(parents=True)
            (workdir / "config" / "samples.selected.tsv").write_text("sample_id\tlibrary\tindex\tcomment\n", encoding="utf-8")

            conf = validate_nipt_conf(self._valid_conf(workdir), shared_root=shared_root, allow_heavy_run=False)

        self.assertEqual(conf["pipeline"], "nipt_docker")
        self.assertEqual(conf["params"]["template_id"], "run1")
        self.assertEqual(conf["params"]["run_mode"], "mount_smoke")
        self.assertEqual(conf["params"]["cores"], 40)

    def test_validate_nipt_conf_accepts_scanned_batch_without_template_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            source_batch_dir = shared_root / "input" / "FQ2026" / "260414_TPNB500380AR_1065_AH32CCBGY2"
            source_batch_dir.mkdir(parents=True)
            workdir = shared_root / "runs" / "NIPT_20260708_120000_SCAN01"
            (workdir / "config").mkdir(parents=True)
            (workdir / "config" / "samples.selected.tsv").write_text(
                "sample_id\tlibrary\tindex\tR1\tR2\tsource_dir\tcomment\n"
                f"NIPT26040207.A06\tNIPT26040207\tA06\t{source_batch_dir / 'NIPT26040207.A06.R1.clean.fastq.gz'}\t{source_batch_dir / 'NIPT26040207.A06.R2.clean.fastq.gz'}\t{source_batch_dir}\tNIPT\n",
                encoding="utf-8",
            )

            conf = validate_nipt_conf(self._scan_conf(workdir, source_batch_dir), shared_root=shared_root, allow_heavy_run=False)

        self.assertEqual(conf["params"]["input_mode"], "nipt_docker_scan")
        self.assertEqual(conf["params"]["source_batch_dir"], str(source_batch_dir))
        self.assertNotIn("template_id", conf["params"])

    def test_validate_nipt_conf_rejects_unknown_template_and_guarded_full_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            workdir = shared_root / "runs" / "NIPT_20260708_120000_TEST01"
            (workdir / "config").mkdir(parents=True)
            (workdir / "config" / "samples.selected.tsv").write_text("sample_id\tlibrary\tindex\tcomment\n", encoding="utf-8")

            bad_template = self._valid_conf(workdir)
            bad_template["params"]["template_id"] = "run3"
            with self.assertRaisesRegex(ValueError, "Unsupported NIPT template"):
                validate_nipt_conf(bad_template, shared_root=shared_root, allow_heavy_run=False)

            full_run = self._valid_conf(workdir)
            full_run["params"]["run_mode"] = "full_run"
            with self.assertRaisesRegex(ValueError, "NIPT full_run is disabled"):
                validate_nipt_conf(full_run, shared_root=shared_root, allow_heavy_run=False)

    def test_prepare_nipt_docker_run_writes_request_and_compose(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            host_shared_root = Path(tmpdir) / "host-shared"
            nipt_root = Path(tmpdir) / "NIPT"
            _write_nipt_template_root(nipt_root)
            workdir = shared_root / "runs" / "NIPT_20260708_120000_TEST01"
            (workdir / "config").mkdir(parents=True)
            (workdir / "config" / "samples.selected.tsv").write_text(
                "sample_id\tlibrary\tindex\tcomment\nNC-20260414.A01\tNC-20260414\tA01\tNIPT\n",
                encoding="utf-8",
            )
            conf = validate_nipt_conf(self._valid_conf(workdir), shared_root=shared_root, allow_heavy_run=False)

            prepared = prepare_nipt_docker_run(
                conf,
                nipt_pipeline_root=nipt_root,
                host_nipt_pipeline_root=Path("/home/jiucheng/pipelines/NIPT"),
                host_shared_root=host_shared_root,
                docker_image="172.17.61.235:2333/niptpro/niptpro:1.0.11",
                fetal_image="172.17.61.235:2333/niptpro/pytorch:biosan",
                docker_network="nipt_analysis_test_net",
                owner="6708:520",
            )

            compose = yaml.safe_load(Path(prepared["compose_path"]).read_text(encoding="utf-8"))
            request = json.loads((workdir / "config" / "nipt_airflow_request.json").read_text(encoding="utf-8"))

        self.assertEqual(prepared["analysis_id"], "NIPT_20260708_120000_TEST01")
        self.assertEqual(request["params"]["template_id"], "run1")
        self.assertEqual(compose["services"]["runner"]["container_name"], "NIPTPro_NIPT_20260708_120000_TEST01")
        self.assertIn("/var/run/docker.sock:/var/run/docker.sock", compose["services"]["runner"]["volumes"])
        self.assertNotIn("NIPTPro_runner", json.dumps(compose))

    def test_prepare_nipt_docker_run_mounts_scanned_batch_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            host_shared_root = Path(tmpdir) / "host-shared"
            nipt_root = Path(tmpdir) / "NIPT"
            _write_nipt_template_root(nipt_root)
            source_batch_dir = nipt_root / "fastq" / "FQ2026" / "260414_TPNB500380AR_1065_AH32CCBGY2"
            source_batch_dir.mkdir(parents=True)
            (source_batch_dir / "NIPT26040207.A06.R1.clean.fastq.gz").write_text("r1\n", encoding="utf-8")
            (source_batch_dir / "NIPT26040207.A06.R2.clean.fastq.gz").write_text("r2\n", encoding="utf-8")
            workdir = shared_root / "runs" / "NIPT_20260708_120000_SCAN01"
            (workdir / "config").mkdir(parents=True)
            (workdir / "config" / "samples.selected.tsv").write_text(
                "sample_id\tlibrary\tindex\tR1\tR2\tsource_dir\tcomment\n"
                f"NIPT26040207.A06\tNIPT26040207\tA06\t{source_batch_dir / 'NIPT26040207.A06.R1.clean.fastq.gz'}\t{source_batch_dir / 'NIPT26040207.A06.R2.clean.fastq.gz'}\t{source_batch_dir}\tNIPT\n",
                encoding="utf-8",
            )
            conf = validate_nipt_conf(self._scan_conf(workdir, source_batch_dir), shared_root=shared_root, allow_heavy_run=False)

            prepared = prepare_nipt_docker_run(
                conf,
                nipt_pipeline_root=nipt_root,
                host_nipt_pipeline_root=Path("/home/jiucheng/pipelines/NIPT"),
                host_shared_root=host_shared_root,
                docker_image="172.17.61.235:2333/niptpro/niptpro:1.0.11",
                fetal_image="172.17.61.235:2333/niptpro/pytorch:biosan",
                docker_network="nipt_analysis_test_net",
                owner="6708:520",
            )

            compose = yaml.safe_load(Path(prepared["compose_path"]).read_text(encoding="utf-8"))
            run_config = yaml.safe_load(Path(prepared["run_config_path"]).read_text(encoding="utf-8"))

        volumes = compose["services"]["runner"]["volumes"]
        self.assertIn("/home/jiucheng/pipelines/NIPT/fastq/FQ2026/260414_TPNB500380AR_1065_AH32CCBGY2:/input_batch:ro", volumes)
        self.assertEqual(run_config["input_mode"], "nipt_docker_scan")
        self.assertEqual(run_config["source_batch_dir"], str(source_batch_dir))

    def test_generate_nipt_compose_uses_unique_names_and_no_destructive_commands(self) -> None:
        compose = generate_nipt_compose(
            analysis_id="NIPT_20260708_120000_TEST01",
            run_mode="mount_smoke",
            workdir=Path("/data/airflow-demo/runs/NIPT_20260708_120000_TEST01"),
            host_workdir=Path("/home/jiucheng/project/airflow-demo/shared/runs/NIPT_20260708_120000_TEST01"),
            nipt_pipeline_root=Path("/opt/pipelines/NIPT"),
            host_nipt_pipeline_root=Path("/home/jiucheng/pipelines/NIPT"),
            chip_name="260414_TPNB500380AR_1065_AH32CCBGY2",
            template_id="run1",
            cores=40,
            docker_image="172.17.61.235:2333/niptpro/niptpro:1.0.11",
            fetal_image="172.17.61.235:2333/niptpro/pytorch:biosan",
            docker_network="nipt_analysis_test_net",
            owner="6708:520",
        )
        rendered = yaml.safe_dump(compose)

        self.assertIn("NIPTPro_NIPT_20260708_120000_TEST01", rendered)
        self.assertIn("nipt_analysis_test_net", rendered)
        self.assertNotIn("down -v", rendered)
        self.assertNotIn("volume prune", rendered)
        self.assertNotIn("system prune", rendered)

    def test_run_nipt_docker_mount_smoke_writes_standard_logs_and_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "NIPT_20260708_120000_TEST01"
            (workdir / "config").mkdir(parents=True)
            compose_path = workdir / "config" / "nipt_docker_compose.yml"
            sample_sheet_path = workdir / "config" / "samples.selected.tsv"
            sample_sheet_path.write_text(
                "sample_id\tlibrary\tindex\tcomment\nNC-20260414.A01\tNC-20260414\tA01\tNIPT\n",
                encoding="utf-8",
            )
            compose_path.write_text(
                yaml.safe_dump(
                    {
                        "services": {
                            "runner": {
                                "image": "172.17.61.235:2333/niptpro/niptpro:1.0.11",
                                "container_name": "NIPTPro_NIPT_20260708_120000_TEST01",
                                "working_dir": "/code/NIPTPro_pipeline/niptplus",
                                "user": "0:0",
                                "environment": {"AIRFLOW_DEMO_ANALYSIS_ID": "NIPT_20260708_120000_TEST01"},
                                "volumes": ["/host/workdir:/workdir"],
                                "entrypoint": "/bin/bash",
                                "command": ["-lc", "echo mount_smoke_ok"],
                                "networks": ["nipt_analysis_test_net"],
                            }
                        },
                        "networks": {"nipt_analysis_test_net": {"external": True}},
                    }
                ),
                encoding="utf-8",
            )
            captured: dict[str, object] = {}
            captured_events: list[tuple[str, str]] = []

            original_runner = nipt_docker_runner.run_command_to_logs
            original_emit = nipt_docker_runner.emit_progress_event

            def fake_run_command_to_logs(command, cwd, stdout_path, stderr_path, env):  # type: ignore[no-untyped-def]
                captured["command"] = command
                captured["stdout_path"] = stdout_path
                captured["stderr_path"] = stderr_path
                return {"exit_code": 0}

            def fake_emit_progress_event(**kwargs):  # type: ignore[no-untyped-def]
                captured_events.append((kwargs["rule"], kwargs["status"]))
                return workdir / "logs" / "events" / "snakemake_events.jsonl"

            nipt_docker_runner.run_command_to_logs = fake_run_command_to_logs
            nipt_docker_runner.emit_progress_event = fake_emit_progress_event
            try:
                run_nipt_docker(
                    {
                        "analysis_id": "NIPT_20260708_120000_TEST01",
                        "workdir": str(workdir),
                        "compose_path": str(compose_path),
                        "sample_sheet_path": str(sample_sheet_path),
                        "backend_event_url": "http://backend:8000/api/events/snakemake",
                        "params": {"run_mode": "mount_smoke"},
                    }
                )
            finally:
                nipt_docker_runner.run_command_to_logs = original_runner
                nipt_docker_runner.emit_progress_event = original_emit

        self.assertEqual(captured["stdout_path"], workdir / "logs" / "snakemake.stdout.log")
        self.assertEqual(captured["stderr_path"], workdir / "logs" / "snakemake.stderr.log")
        self.assertEqual(captured["command"][0:2], ["docker", "run"])
        self.assertIn("--rm", captured["command"])
        self.assertIn("NIPTPro_NIPT_20260708_120000_TEST01", captured["command"])
        self.assertNotIn("down", captured["command"])
        self.assertNotIn("compose", captured["command"])
        self.assertIn("nipt_docker.command.txt", str(workdir / "logs" / "nipt_docker.command.txt"))
        self.assertEqual(captured_events, [("nipt_mount_smoke", "running"), ("nipt_mount_smoke", "success")])

    def test_collect_nipt_artifacts_requires_qc_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "NIPT_20260708_120000_TEST01"
            (workdir / "reports").mkdir(parents=True)
            (workdir / "logs").mkdir(parents=True)
            (workdir / "config").mkdir(parents=True)
            (workdir / "reports" / "qc_summary.tsv").write_text(
                "sample_id\tmetric_name\tmetric_value\tmetric_numeric\tthreshold\tstatus\n"
                "NC-20260414.A01\tQ30\t93.2\t93.2\t>=85\tpass\n",
                encoding="utf-8",
            )
            (workdir / "config" / "nipt_docker_compose.yml").write_text("services: {}\n", encoding="utf-8")
            (workdir / "config" / "nipt_run_config.yaml").write_text("chip_name: demo\n", encoding="utf-8")

            artifact = collect_nipt_artifacts({"analysis_id": "NIPT_20260708_120000_TEST01", "workdir": str(workdir)})

        self.assertEqual(artifact["type"], "nipt_docker_summary")
        self.assertEqual(artifact["qc_metric_count"], 1)
        self.assertTrue(artifact["qc_path"].endswith("reports/qc_summary.tsv"))

    def test_write_nipt_qc_summary_from_mapping_qc_and_fetal_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir) / "runs" / "NIPT_20260708_120000_TEST01"
            cnv_dir = workdir / "CNV"
            cnv_dir.mkdir(parents=True)
            (cnv_dir / "mappingQC.csv").write_text(
                "Sample,read_count,base_count,Q20,Q30,PCRdup%,uniqueMappedRC,uniqueMappedRC%,chrY%,Gender\n"
                "NC-20260414.A01.R1.clean.fastq.gz,100000,5000000,97.1,93.2,5.1,87500,87.5,0.31,Female\n",
                encoding="utf-8",
            )
            (workdir / "NC-20260414.model.predict.csv").write_text(
                "fetal_ratio,sample\n0.083,NC-20260414.A01.R1.clean.fastq.gz\n",
                encoding="utf-8",
            )

            qc_path = write_nipt_qc_summary_from_outputs(workdir)
            lines = qc_path.read_text(encoding="utf-8").splitlines()

        self.assertIn("NC-20260414.A01\tQ30\t93.2\t93.2\t>=85\tpass", lines)
        self.assertIn("NC-20260414.A01\tunique_mapping_rate\t87.5\t87.5\t>=70\tpass", lines)
        self.assertIn("NC-20260414.A01\tpcr_duplication_rate\t5.1\t5.1\t<=20\tpass", lines)
        self.assertIn("NC-20260414.A01\tfetal_fraction\t0.083\t0.083\t>=0.04\tpass", lines)


def _write_nipt_template_root(root: Path) -> None:
    run_dir = root / "nipt_docker_test_run1"
    run_dir.mkdir(parents=True)
    (run_dir / "config.yaml").write_text("chip_name: demo\n", encoding="utf-8")
    (run_dir / "260414_TPNB500380AR_1065_AH32CCBGY2.csv").write_text(
        "library,index,comment\nNC-20260414,A01,NIPT\n",
        encoding="utf-8",
    )
    (root / "niptplus" / "scripts").mkdir(parents=True)


if __name__ == "__main__":
    unittest.main()
