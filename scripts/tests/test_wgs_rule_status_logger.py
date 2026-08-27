import importlib.util
import json
import logging
from pathlib import Path


def load_module():
    path = Path(__file__).parents[1] / "wgs_rule_status_logger.py"
    spec = importlib.util.spec_from_file_location("wgs_rule_status_logger", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_logger_writes_observer_schema_without_backend_callback(tmp_path: Path) -> None:
    module = load_module()
    handler = module.WgsRuleStatusHandler(
        analysis_id="WGS_20260813_010203_A1B2C3",
        attempt=1,
        pipeline_release_id="wgs-4.1.1-1778fca",
        run_label="wgs401-0123456789abcdef",
        events_path=tmp_path / "raw" / "master.jsonl",
        role="master",
        stream_id="master",
    )
    record = logging.LogRecord("snakemake", logging.INFO, "Snakefile", 1, "start", (), None)
    record.event = "job_started"
    record.rule = "pre_process_mapping"
    record.job_id = 7
    record.wildcards = {"sample": "S1"}
    handler.emit(record)
    payload = json.loads((tmp_path / "raw" / "master.jsonl").read_text().strip())
    assert payload["schema_version"] == "1"
    assert payload["analysis_id"] == "WGS_20260813_010203_A1B2C3"
    assert payload["attempt"] == 1
    assert (
        payload["pipeline_release_id"] == "wgs-4.1.1-1778fca"
    )
    assert payload["run_label"] == "wgs401-0123456789abcdef"
    assert payload["rule_name"] == "pre_process_mapping"
    assert payload["rule_instance_id"]
    assert payload["status"] == "running"
