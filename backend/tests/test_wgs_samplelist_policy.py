from pathlib import Path
import yaml
import pytest

from app.wgs_project_catalog import load_wgs_intake_policy


def policy_files(tmp_path, **overrides):
    catalog = tmp_path / "projects.yaml"
    catalog.write_text(yaml.safe_dump({"schema_version": 1, "projects": [{
        "project_id": "SYN-PROJECT", "platforms": [{"platform_id": "T7"}],
        "fastq_roots": [{"root_id": "SYN-ROOT", "node200_path": "/synthetic/fastq", "control_plane_path": "/synthetic/fastq"}]}]}))
    config = tmp_path / "prepare.yaml"
    config.write_text("defaults:\n  samplelist_dir: /synthetic/samplelists\n")
    intake = tmp_path / "intake.yaml"
    intake.write_text(yaml.safe_dump({"pipelines": {"wgs": {"enabled": True, "intake": {
        "mode": "samplelist_batches", "project_id": "SYN-PROJECT", "platform_id": "T7",
        "root_id": "SYN-ROOT", "interval_seconds": 600, "scheduled_scan_enabled": True,
        "auto_dispatch_enabled": False, "prepare_config_path": str(config), **overrides}}}}))
    return dict(intake_path=intake, project_catalog_path=catalog)


def test_samplelist_policy_reads_declared_prepare_source(tmp_path):
    policy = load_wgs_intake_policy(**policy_files(tmp_path))
    assert policy.mode == "samplelist_batches"
    assert policy.samplelist_root == "/synthetic/samplelists"
    assert policy.platform_id == "T7"


@pytest.mark.parametrize("overrides", [{"mode": "typo"}, {"prepare_config_path": "relative.yaml"}, {"prepare_config_path": None}, {"platform_id": "UNKNOWN"}])
def test_invalid_samplelist_policy_rejected(tmp_path, overrides):
    with pytest.raises(ValueError):
        load_wgs_intake_policy(**policy_files(tmp_path, **overrides))


def test_explicit_mount_mapping_requires_exact_declared_source(tmp_path):
    policy = load_wgs_intake_policy(**policy_files(tmp_path, samplelist_mount={"source": "/synthetic/samplelists", "target": "/mounted/samplelists"}))
    assert policy.samplelist_root == "/mounted/samplelists"
    with pytest.raises(ValueError):
        load_wgs_intake_policy(**policy_files(tmp_path, samplelist_mount={"source": "/different", "target": "/mounted/samplelists"}))


def test_policy_dispatch_registers_content_batches_not_historical_chips(tmp_path):
    from app.wgs_intake_scanner_cli import scan_intake_policy
    from app.models import WgsIntakeBatch
    from sqlalchemy import select
    from test_wgs_t7_intake import make_sessionmaker
    from test_wgs_samplelist_intake import export
    root, source = tmp_path / "fastq", tmp_path / "lists"
    root.mkdir(); source.mkdir()
    policy = load_wgs_intake_policy(**policy_files(tmp_path, samplelist_mount={"source": "/synthetic/samplelists", "target": str(source)}))
    sessions = make_sessionmaker()
    def scan():
        return scan_intake_policy(policy=policy, session_factory=sessions, root=root, scan_enabled=True)
    scan()
    export(source / "Samplelist_new.txt", "20990101A")
    scan(); scan()
    with sessions() as session:
        row, = session.scalars(select(WgsIntakeBatch)).all()
        assert (row.sequencing_batch, row.state) == ("20990101A", "waiting_sequencing")


def test_declared_source_change_with_same_mount_target_has_independent_baseline(tmp_path):
    from app.wgs_intake_scanner_cli import scan_intake_policy
    from app.models import WgsIntakeBatch, WgsSamplelistSource
    from sqlalchemy import select
    from test_wgs_t7_intake import make_sessionmaker
    from test_wgs_samplelist_intake import export
    root, mounted = tmp_path / "fastq", tmp_path / "mounted"
    root.mkdir(); mounted.mkdir()
    paths = policy_files(tmp_path, samplelist_mount={"source": "/synthetic/samplelists", "target": str(mounted)})
    sessions = make_sessionmaker()
    def scan():
        return scan_intake_policy(policy=load_wgs_intake_policy(**paths), session_factory=sessions, root=root, scan_enabled=True)
    scan()
    # The container mount point is reused for another approved declared source.
    (tmp_path / "prepare.yaml").write_text("defaults:\n  samplelist_dir: /synthetic/source-B\n")
    payload = yaml.safe_load(paths["intake_path"].read_text())
    payload["pipelines"]["wgs"]["intake"]["samplelist_mount"]["source"] = "/synthetic/source-B"
    paths["intake_path"].write_text(yaml.safe_dump(payload))
    export(mounted / "Samplelist_existing_on_B.txt", "20990101A")
    scan(); scan(); scan()
    with sessions() as session:
        assert session.scalars(select(WgsIntakeBatch)).all() == []
        assert len(session.scalars(select(WgsSamplelistSource)).all()) == 2
