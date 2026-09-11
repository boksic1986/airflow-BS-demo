from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisRun, Base, PipelineStageExecution, PipelineSubmissionDraft, Sample
from app.gatk_submission_service import (
    GatkInputChanged,
    _batch_lock_key,
    confirm_gatk_submission,
    create_gatk_submission_preview,
)


class RecordingAirflow:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def trigger_dag_run(self, dag_id, *, dag_run_id=None, conf=None):
        self.calls.append({"dag_id": dag_id, "dag_run_id": dag_run_id, "conf": conf})
        return self.calls[-1]

    def get_dag_run(self, dag_id, dag_run_id):
        return next(
            (
                item
                for item in self.calls
                if item["dag_id"] == dag_id and item["dag_run_id"] == dag_run_id
            ),
            None,
        )


def _settings(tmp_path: Path, source_root: Path, fastq_root: Path):
    return SimpleNamespace(
        gatk_execution_enabled=True,
        gatk_source_policy="restricted",
        gatk_source_roots=[str(source_root)],
        gatk_fastq_roots=[str(fastq_root)],
        gatk_submission_draft_ttl_minutes=30,
        gatk_runtime_profile_id="gatk-scmc-v7.6.0",
        gatk_runtime_profile_revision="bd04f6d",
        gatk_runtime_request_root=str(tmp_path / "runtime" / "requests"),
        gatk_runtime_node200_root="/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud/runtime/gatk",
        gatk_transfer_spool_root=str(tmp_path / "runtime" / "transfer-progress"),
        gatk_result_root="/sg2/50.ctapa/project/HWcloud/WES_Clinical",
        gatk_repository_root="/bi/biodevrwbi/33.chenjiucheng/project/gatk-cloud",
        gatk_operator_config="/home/ctapa/.config/cce-pipeline/operator.yaml",
        gatk_profile_file="profiles/cce-pipeline/gatk.yaml",
        gatk_runtime_file="profiles/cce/runtime.yaml",
        gatk_pipeline_root="/workspace/gatk-cloud/pipelines/7.6.0",
        gatk_cce_pipeline="/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/bin/cce-pipeline",
    )


def test_preview_rejects_source_outside_configured_roots_by_default(tmp_path: Path) -> None:
    _, source, fastq_root = _source_fixture(tmp_path)
    different_root = tmp_path / "different-root"
    different_root.mkdir()
    different_fastq_root = tmp_path / "different-fastq-root"
    different_fastq_root.mkdir()
    settings = _settings(tmp_path, different_root, different_fastq_root)

    with _sessions()() as session, pytest.raises(
        ValueError, match="outside every approved root"
    ):
        create_gatk_submission_preview(
            session=session,
            settings=settings,
            source_project_dir=str(source),
            owner_username="operator",
        )


def test_unrestricted_policy_accepts_explicit_valid_project_and_freezes_exact_path(
    tmp_path: Path,
) -> None:
    _, source, _ = _source_fixture(tmp_path)
    different_root = tmp_path / "different-root"
    different_root.mkdir()
    different_fastq_root = tmp_path / "different-fastq-root"
    different_fastq_root.mkdir()
    settings = _settings(tmp_path, different_root, different_fastq_root)
    settings.gatk_source_policy = "unrestricted"

    with _sessions()() as session:
        preview = create_gatk_submission_preview(
            session=session,
            settings=settings,
            source_project_dir=str(source),
            owner_username="operator",
        )
        draft = session.scalar(select(PipelineSubmissionDraft))

    assert preview["validation"]["paths_approved"] is True
    assert draft is not None
    assert draft.input_root == str(source.resolve(strict=True))


def test_invalid_source_policy_fails_closed(tmp_path: Path) -> None:
    allowed_source, source, fastq_root = _source_fixture(tmp_path)
    settings = _settings(tmp_path, allowed_source, fastq_root)
    settings.gatk_source_policy = "anything"

    with _sessions()() as session, pytest.raises(
        ValueError, match="source policy is invalid"
    ):
        create_gatk_submission_preview(
            session=session,
            settings=settings,
            source_project_dir=str(source),
            owner_username="operator",
        )


def _source_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    allowed_source = tmp_path / "WES_Clinical"
    allowed_source.mkdir()
    source = allowed_source / "WES_20260908A_T7_V7.6.0_hg38"
    raw = source / "a.raw"
    raw.mkdir(parents=True)
    fastq_root = tmp_path / "OutputFq"
    fastq_root.mkdir()
    samples = ["SCMC001", "SCMC002"]
    sampleinfo = source / "WES_20260908A_T7.sampleinfo.txt"
    sampleinfo.write_text(
        "\u6570\u636e\u7f16\u53f7\t\u9001\u68c0\u533b\u9662\n"
        + "\n".join(
            f"{sample}\t\u4e0a\u6d77\u4ea4\u901a\u5927\u5b66\u533b\u5b66\u9662\u9644\u5c5e\u4e0a\u6d77\u513f\u7ae5\u533b\u5b66\u4e2d\u5fc3"
            for sample in samples
        )
        + "\n",
        encoding="utf-8",
    )
    config = {
        "SCMC": samples,
        "sample2hospitalBarCode": {"SCMC001": "B001", "SCMC002": "B002"},
    }
    (source / "config.V7.6.0_hg38.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True), encoding="utf-8"
    )
    (source / "sample2hospitalBarCode.txt").write_text(
        "SCMC001\tB001\nSCMC002\tB002\n", encoding="utf-8"
    )
    for sample in samples:
        for read in ("R1", "R2"):
            target = fastq_root / f"{sample}.{read}.fq.gz"
            target.write_bytes((sample + read).encode("ascii"))
            (raw / target.name).symlink_to(target)
    return allowed_source, source, fastq_root


def _sessions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_preview_is_private_locked_and_scmc_only(tmp_path: Path) -> None:
    allowed_source, source, fastq_root = _source_fixture(tmp_path)
    sessions = _sessions()

    with sessions() as session:
        preview = create_gatk_submission_preview(
            session=session,
            settings=_settings(tmp_path, allowed_source, fastq_root),
            source_project_dir=str(source),
            owner_username="operator",
        )

    assert preview["pipeline"] == "gatk"
    assert preview["batch"] == "20260908A"
    assert preview["profile_id"] == "gatk-scmc-v7.6.0"
    assert preview["sampleinfo_name"] == "WES_20260908A_T7.sampleinfo.txt"
    assert preview["sample_count"] == 2
    assert preview["fastq_file_count"] == 4
    assert preview["validation"]["sample_sets_match"] is True
    assert "source_project_dir" not in preview
    assert str(fastq_root) not in str(preview)
    with sessions() as session:
        row = session.scalar(select(PipelineSubmissionDraft))
        assert row is not None
        assert row.pipeline_name == "gatk"
        assert row.owner_username == "operator"


def test_confirm_rechecks_hash_and_submits_independent_dag(tmp_path: Path) -> None:
    allowed_source, source, fastq_root = _source_fixture(tmp_path)
    sessions = _sessions()
    airflow = RecordingAirflow()
    settings = _settings(tmp_path, allowed_source, fastq_root)
    with sessions() as session:
        preview = create_gatk_submission_preview(
            session=session,
            settings=settings,
            source_project_dir=str(source),
            owner_username="operator",
        )
        result = confirm_gatk_submission(
            session=session,
            settings=settings,
            airflow_client=airflow,
            draft_id=preview["draft_id"],
            preview_hash=preview["preview_hash"],
            project_name="WES_Clinical",
            submitted_by="operator",
        )

    assert result["pipeline"] == "gatk"
    assert result["status"] == "submitted"
    assert airflow.calls[0]["dag_id"] == "bio_gatk"
    assert airflow.calls[0]["conf"]["pipeline"] == "gatk"
    with sessions() as session:
        run = session.scalar(select(AnalysisRun))
        assert run is not None
        assert run.pipeline_name == "gatk"
        assert run.params_json["pipeline_release_id"] == "gatk-scmc-v7.6.0@bd04f6d"
        assert "source_project_dir" not in run.params_json
        assert run.params_json["source_project_name"] == source.name
        assert len(session.scalars(select(Sample)).all()) == 2
        request_path = (
            Path(settings.gatk_runtime_request_root)
            / run.analysis_id
            / "attempt-1"
            / "prepare.request.json"
        )
        request = __import__("json").loads(request_path.read_text(encoding="utf-8"))
        assert request["approved_output_roots"] == [
            "/sg2/50.ctapa/project/HWcloud/ngs-huaweicloud/runtime/gatk/runs"
        ]
        assert request["result_project_name"] == f"{source.name}_GATK"
        assert request["result_root"] == (
            "/sg2/50.ctapa/project/HWcloud/WES_Clinical/"
            f"{source.name}_GATK"
        )


def test_confirm_rejects_input_changed_after_preview(tmp_path: Path) -> None:
    allowed_source, source, fastq_root = _source_fixture(tmp_path)
    sessions = _sessions()
    settings = _settings(tmp_path, allowed_source, fastq_root)
    with sessions() as session:
        preview = create_gatk_submission_preview(
            session=session,
            settings=settings,
            source_project_dir=str(source),
            owner_username="operator",
        )
    (source / "sample2hospitalBarCode.txt").write_text(
        "SCMC001\tB001\nSCMC002\tCHANGED\n", encoding="utf-8"
    )
    with sessions() as session, pytest.raises(GatkInputChanged):
        confirm_gatk_submission(
            session=session,
            settings=settings,
            airflow_client=RecordingAirflow(),
            draft_id=preview["draft_id"],
            preview_hash=preview["preview_hash"],
            project_name="WES_Clinical",
            submitted_by="operator",
        )


def test_gatk_stage_execution_uses_pipeline_namespace(tmp_path: Path) -> None:
    sessions = _sessions()
    with sessions() as session:
        session.add(
            AnalysisRun(
                analysis_id="GATK_20260908_120000_A1B2C3",
                pipeline_name="gatk",
                dag_id="bio_gatk",
                workdir="/runtime/gatk/GATK_20260908_120000_A1B2C3",
                params_json={},
            )
        )
        session.add(
            PipelineStageExecution(
                execution_id="gatk-step1-a1-g1",
                pipeline_name="gatk",
                analysis_id="GATK_20260908_120000_A1B2C3",
                attempt=1,
                stage_code="step1_upload",
                generation=1,
                status="accepted",
                request_hash="a" * 64,
                release_id="gatk-scmc-v7.6.0@bd04f6d",
            )
        )
        session.commit()
        row = session.scalar(select(PipelineStageExecution))

    assert row is not None
    assert row.pipeline_name == "gatk"


def test_gatk_batch_advisory_lock_key_is_stable_and_batch_specific() -> None:
    assert _batch_lock_key("20260908A") == _batch_lock_key("20260908A")
    assert _batch_lock_key("20260908A") != _batch_lock_key("20260908B")
