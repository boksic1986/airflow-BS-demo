from pathlib import Path

from app.wgs_yaml_intake import scan_wgs_yaml_request_results


def test_wgs_yaml_intake_requires_ready_and_resolves_controlled_files(tmp_path) -> None:
    inbox = tmp_path / "inbox"
    controlled = tmp_path / "controlled"
    fastq = controlled / "fastq"
    inbox.mkdir()
    fastq.mkdir(parents=True)
    sample_info = controlled / "samples.tsv"
    sample_info.write_text("sample_id\tdata_id\nWGS-01\tWGS-01-WGS\n", encoding="utf-8")
    for read in ("R1", "R2"):
        (fastq / f"WGS-01-WGS.{read}.fq.gz").write_bytes(b"synthetic")
    pre = controlled / "pre.yaml"
    down = controlled / "down.yaml"
    config_text = f"sample_info: {sample_info}\nfastqDir: {fastq}\n"
    pre.write_text(config_text, encoding="utf-8")
    down.write_text(config_text, encoding="utf-8")
    targets = controlled / "targets.txt"
    targets.write_text("01_SNV/WGS-01.flt.tsv\n", encoding="utf-8")
    request = inbox / "wgs-jx25.wgs.yaml"
    request.write_text(
        "\n".join([
            "version: 1",
            "request_id: wgs-jx25",
            "project: WGS-JX25",
            "operator: jiucheng",
            f"precalling_config: {pre}",
            f"downstream_config: {down}",
            f"targets: {targets}",
            "stage: full",
            "submit: true",
            "",
        ]),
        encoding="utf-8",
    )

    before_ready = scan_wgs_yaml_request_results(inbox_root=inbox, allowed_roots=[controlled])
    assert before_ready.requests == []
    (inbox / "wgs-jx25.READY").write_text("", encoding="utf-8")

    result = scan_wgs_yaml_request_results(inbox_root=inbox, allowed_roots=[controlled])

    assert result.errors == []
    assert len(result.requests) == 1
    parsed = result.requests[0]
    assert parsed.request_id == "wgs-jx25"
    assert parsed.project == "WGS-JX25"
    assert parsed.operator == "jiucheng"
    assert parsed.stage == "full"
    assert parsed.submit is True
    assert parsed.sample_count == 1
    assert parsed.fastq_file_count == 2
    assert len(parsed.fingerprint) == 64


def test_wgs_yaml_intake_rejects_paths_outside_approved_roots(tmp_path) -> None:
    inbox = tmp_path / "inbox"
    allowed = tmp_path / "allowed"
    inbox.mkdir()
    allowed.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("sample_info: /tmp/nope\nfastqDir: /tmp/nope\n", encoding="utf-8")
    request = inbox / "unsafe.wgs.yaml"
    request.write_text(
        f"version: 1\nrequest_id: unsafe\nproject: unsafe\noperator: airflow\nprecalling_config: {outside}\ndownstream_config: {outside}\ntargets: {outside}\nstage: full\nsubmit: false\n",
        encoding="utf-8",
    )
    (inbox / "unsafe.READY").write_text("", encoding="utf-8")

    result = scan_wgs_yaml_request_results(inbox_root=inbox, allowed_roots=[allowed])

    assert result.requests == []
    assert "outside approved roots" in result.errors[0].message
