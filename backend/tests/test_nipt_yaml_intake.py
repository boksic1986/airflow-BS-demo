from __future__ import annotations

from pathlib import Path

import pytest

from app.nipt_yaml_intake import scan_nipt_yaml_request_results


def write_pair(batch: Path, sample_id: str) -> None:
    batch.mkdir(parents=True, exist_ok=True)
    (batch / f"{sample_id}.R1.clean.fastq.gz").write_bytes(b"r1")
    (batch / f"{sample_id}.R2.clean.fastq.gz").write_bytes(b"r2")


def write_request(
    inbox: Path,
    *,
    request_id: str = "project-20260713",
    batch_id: str = "batch-001",
    samples: str = "all",
    submit: str = "true",
) -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / f"{request_id}.nipt.yaml"
    path.write_text(
        "\n".join(
            [
                "version: 1",
                f"request_id: {request_id}",
                "project_id: NIPT-PROJECT-20260713",
                f"batch_id: {batch_id}",
                f"samples: {samples}",
                "submitted_by: jiucheng",
                "runtime_profile_id: niptpro-s9-full-v1",
                "run_mode: full_run",
                "cores: 32",
                f"submit: {submit}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_request_resolves_batch_without_fastq_path_and_ignores_partial_files(tmp_path) -> None:
    root = tmp_path / "fastq"
    batch = root / "FQ2026" / "batch-001"
    write_pair(batch, "S1.A01")
    write_pair(batch, "S2.A02")
    inbox = tmp_path / "requests"
    request_path = write_request(inbox)
    (inbox / "unpublished.nipt.yaml.partial").write_text("not: yaml: yet", encoding="utf-8")

    result = scan_nipt_yaml_request_results(
        inbox_root=inbox,
        allowed_roots=[root],
        max_samples=200,
    )

    assert result.errors == []
    assert len(result.requests) == 1
    request = result.requests[0]
    assert request.request_id == "project-20260713"
    assert request.project_id == "NIPT-PROJECT-20260713"
    assert request.batch_id == "batch-001"
    assert request.source_dir == str(batch.resolve())
    assert request.rawdata_root == str(root.resolve())
    assert request.manifest_path == str(request_path.resolve())
    assert request.submitted_by == "jiucheng"
    assert request.runtime_profile_id == "niptpro-s9-full-v1"
    assert request.run_mode == "full_run"
    assert request.cores == 32
    assert request.submit is True
    assert [sample.sample_id for sample in request.samples] == ["S1.A01", "S2.A02"]
    assert len(request.fingerprint) == 64


def test_request_can_select_a_sample_subset(tmp_path) -> None:
    root = tmp_path / "fastq"
    batch = root / "batch-001"
    write_pair(batch, "S1.A01")
    write_pair(batch, "S2.A02")
    inbox = tmp_path / "requests"
    write_request(inbox, samples="[S2.A02]")

    result = scan_nipt_yaml_request_results(inbox_root=inbox, allowed_roots=[root], max_samples=200)

    assert result.errors == []
    assert [sample.sample_id for sample in result.requests[0].samples] == ["S2.A02"]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (
            "version: 1\nrequest_id: duplicate\nrequest_id: duplicate\n",
            "Duplicate YAML key",
        ),
        (
            "version: 1\nrequest_id: alias\nproject_id: &project NIPT\nbatch_id: batch-001\n"
            "samples: *project\nsubmitted_by: jiucheng\nruntime_profile_id: niptpro-s9-full-v1\n"
            "run_mode: full_run\ncores: 32\nsubmit: true\n",
            "YAML aliases",
        ),
        (
            "version: 1\nrequest_id: tagged\nproject_id: !unsafe NIPT\n",
            "custom YAML tags",
        ),
        (
            "version: 1\nrequest_id: escaped\nproject_id: NIPT\nbatch_id: ../outside\n"
            "samples: all\nsubmitted_by: jiucheng\nruntime_profile_id: niptpro-s9-full-v1\n"
            "run_mode: full_run\ncores: 32\nsubmit: true\n",
            "batch_id",
        ),
        (
            "version: 1\nrequest_id: unknown\nproject_id: NIPT\nbatch_id: batch-001\n"
            "samples: all\nsubmitted_by: jiucheng\nruntime_profile_id: niptpro-s9-full-v1\n"
            "run_mode: full_run\ncores: 32\nsubmit: true\ndocker_image: unsafe\n",
            "unknown fields",
        ),
        (
            "? [unsafe, key]\n: value\n",
            "mapping keys must be strings",
        ),
    ],
)
def test_request_rejects_unsafe_yaml(tmp_path, body: str, message: str) -> None:
    root = tmp_path / "fastq"
    write_pair(root / "batch-001", "S1.A01")
    inbox = tmp_path / "requests"
    inbox.mkdir()
    request_id = (
        "duplicate"
        if "duplicate" in body
        else "alias"
        if "alias" in body
        else "tagged"
        if "tagged" in body
        else "escaped"
        if "escaped" in body
        else "unknown"
        if "unknown" in body
        else "unsafe-key"
    )
    (inbox / f"{request_id}.nipt.yaml").write_text(body, encoding="utf-8")

    result = scan_nipt_yaml_request_results(inbox_root=inbox, allowed_roots=[root], max_samples=200)

    assert result.requests == []
    assert len(result.errors) == 1
    assert message in result.errors[0].message


def test_request_rejects_ambiguous_batch_names_across_allowed_roots(tmp_path) -> None:
    root_a = tmp_path / "fastq-a"
    root_b = tmp_path / "fastq-b"
    write_pair(root_a / "FQ2025" / "batch-001", "S1.A01")
    write_pair(root_b / "FQ2026" / "batch-001", "S2.A02")
    inbox = tmp_path / "requests"
    write_request(inbox)

    result = scan_nipt_yaml_request_results(
        inbox_root=inbox,
        allowed_roots=[root_a, root_b],
        max_samples=200,
    )

    assert result.requests == []
    assert len(result.errors) == 1
    assert "matches more than one approved NIPT batch" in result.errors[0].message
