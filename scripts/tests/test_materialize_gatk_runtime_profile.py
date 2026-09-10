from pathlib import Path
import json

import pytest
import yaml

from scripts.materialize_gatk_runtime_profile import materialize_profile


def test_materializes_airflow_overlay_without_changing_gatk_profile(tmp_path: Path) -> None:
    source = tmp_path / "gatk-config.yaml"
    source.write_text(
        yaml.safe_dump(
            {
                "executor": "kubernetes",
                "jobs": 200,
                "retries": 1,
                "default-resources": ["mem_mb=32768"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    original = source.read_bytes()
    overlay = tmp_path / "airflow-overlay.yaml"
    overlay.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "snakemake_profile": {"latency-wait": 180},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "release" / "profiles" / "cce" / "config.yaml"
    provenance = tmp_path / "release" / "airflow-profile-provenance.json"

    result = materialize_profile(
        source=source,
        overlay=overlay,
        output=output,
        provenance=provenance,
        source_commit="12170a7",
    )

    assert source.read_bytes() == original
    assert yaml.safe_load(output.read_text(encoding="utf-8"))["latency-wait"] == 180
    saved = json.loads(provenance.read_text(encoding="utf-8"))
    assert saved == result
    assert saved["source_commit"] == "12170a7"
    assert saved["overrides"] == {"latency-wait": 180}
    assert len(saved["source_sha256"]) == 64
    assert len(saved["overlay_sha256"]) == 64
    assert len(saved["output_sha256"]) == 64


def test_rejects_non_runtime_overlay_keys(tmp_path: Path) -> None:
    source = tmp_path / "gatk-config.yaml"
    source.write_text("executor: kubernetes\n", encoding="utf-8")
    overlay = tmp_path / "airflow-overlay.yaml"
    overlay.write_text(
        "schema_version: 1\nsnakemake_profile:\n  retries: 99\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported key"):
        materialize_profile(
            source=source,
            overlay=overlay,
            output=tmp_path / "output.yaml",
            provenance=tmp_path / "provenance.json",
            source_commit="12170a7",
        )
