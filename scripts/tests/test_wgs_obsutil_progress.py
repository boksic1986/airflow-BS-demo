from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import hashlib
import importlib.util


SCRIPT = Path(__file__).parents[1] / "wgs_obsutil_progress.py"


def load_wrapper():
    spec = importlib.util.spec_from_file_location("wgs_obsutil_progress_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_node200_wrapper_uses_supported_wgs_python() -> None:
    assert SCRIPT.read_text(encoding="utf-8").splitlines()[0] == (
        "#!/bi/software/mamba/envs/WGS/bin/python3.11"
    )


def test_wrapper_preserves_output_and_writes_redacted_progress(tmp_path: Path) -> None:
    fake = tmp_path / "fake_obsutil.py"
    fake.write_text(
        "import sys, time\n"
        "sys.stdout.write('25.00% 10.00MB/s 25MB/100MB 7s\\r')\n"
        "sys.stdout.flush(); time.sleep(.05)\n"
        "sys.stdout.write('100.00% 20.00MB/s 100MB/100MB 0s\\n')\n",
        encoding="utf-8",
    )
    progress = tmp_path / "progress"
    env = {
        **os.environ,
        "WGS_REAL_OBSUTIL_BIN": sys.executable,
        "WGS_TRANSFER_PROGRESS_ROOT": str(progress),
        "WGS_TRANSFER_ANALYSIS_ID": "WGS_20260902_120000_A1B2C3",
        "WGS_TRANSFER_ATTEMPT": "1",
        "WGS_TRANSFER_STAGE": "step1_upload",
        "WGS_TRANSFER_DIRECTION": "upload",
    }
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(fake), "cp", "/secret/patient.fastq.gz", "obs://secret/prefix"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "25.00%" in completed.stdout
    payloads = [json.loads(path.read_text()) for path in progress.glob("*.json")]
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["schema_version"] == "wgs-runtime.transfer-progress.v1"
    assert payload["state"] == "success"
    assert payload["bytes_done"] == payload["bytes_total"] == 100 * 1024 * 1024
    serialized = json.dumps(payload)
    assert "patient.fastq.gz" not in serialized
    assert "obs://" not in serialized
    assert "/secret" not in serialized


def test_upload_checkpoint_reads_nested_file_size_and_completed_parts(
    tmp_path: Path,
) -> None:
    wrapper = load_wrapper()
    checkpoint = tmp_path / "checkpoint"
    upload = checkpoint / "upload"
    upload.mkdir(parents=True)
    (upload / "upload.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<UploadFileCheckpoint>
  <FileInfo><FileUrl>/secret/S1_R1.fastq.gz</FileUrl><Size>300</Size></FileInfo>
  <UploadParts>
    <UploadPart><PartSize>100</PartSize><IsCompleted>true</IsCompleted></UploadPart>
    <UploadPart><PartSize>100</PartSize><IsCompleted>true</IsCompleted></UploadPart>
    <UploadPart><PartSize>100</PartSize><IsCompleted>false</IsCompleted></UploadPart>
  </UploadParts>
</UploadFileCheckpoint>
""",
        encoding="utf-8",
    )

    assert wrapper._checkpoint_progress(checkpoint, "upload") == (200, 300)


def test_download_checkpoint_reads_object_size_and_inclusive_completed_ranges(
    tmp_path: Path,
) -> None:
    wrapper = load_wrapper()
    checkpoint = tmp_path / "checkpoint"
    download = checkpoint / "download"
    download.mkdir(parents=True)
    (download / "download.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<DownloadFileCheckpoint>
  <ObjectInfo><Size>300</Size></ObjectInfo>
  <DownloadParts>
    <DownloadPart><RangeStart>0</RangeStart><RangeEnd>99</RangeEnd><IsCompleted>true</IsCompleted></DownloadPart>
    <DownloadPart><RangeStart>100</RangeStart><RangeEnd>199</RangeEnd><IsCompleted>true</IsCompleted></DownloadPart>
    <DownloadPart><RangeStart>200</RangeStart><RangeEnd>299</RangeEnd><IsCompleted>false</IsCompleted></DownloadPart>
  </DownloadParts>
</DownloadFileCheckpoint>
""",
        encoding="utf-8",
    )

    assert wrapper._checkpoint_progress(checkpoint, "download") == (200, 300)


def test_partial_checkpoint_is_ignored(tmp_path: Path) -> None:
    wrapper = load_wrapper()
    checkpoint = tmp_path / "checkpoint"
    upload = checkpoint / "upload"
    upload.mkdir(parents=True)
    (upload / "partial.xml").write_text(
        "<UploadFileCheckpoint><FileInfo><Size>300",
        encoding="utf-8",
    )

    assert wrapper._checkpoint_progress(checkpoint, "upload") is None


def test_wrapper_publishes_plan_file_identity_from_checkpoint_without_paths(
    tmp_path: Path,
) -> None:
    fake = tmp_path / "fake_obsutil.py"
    fake.write_text(
        "import pathlib, sys, time\n"
        "cpd = next(a.split('=', 1)[1] for a in sys.argv if a.startswith('-cpd='))\n"
        "folder = pathlib.Path(cpd) / 'upload'; folder.mkdir(parents=True, exist_ok=True)\n"
        "(folder / 'state.xml').write_text('''<UploadFileCheckpoint>"
        "<FileInfo><Size>300</Size></FileInfo><UploadParts>"
        "<UploadPart><PartSize>100</PartSize><IsCompleted>true</IsCompleted></UploadPart>"
        "<UploadPart><PartSize>200</PartSize><IsCompleted>false</IsCompleted></UploadPart>"
        "</UploadParts></UploadFileCheckpoint>''')\n"
        "time.sleep(.2)\n",
        encoding="utf-8",
    )
    relative = "raw/S1_R1.fastq.gz"
    plan = tmp_path / "transfer-plan.json"
    plan.write_text(
        json.dumps({"entries": [{"relative_path": relative, "size_bytes": 300}]}),
        encoding="utf-8",
    )
    progress = tmp_path / "progress"
    checkpoint = tmp_path / "checkpoint"
    env = {
        **os.environ,
        "WGS_REAL_OBSUTIL_BIN": sys.executable,
        "WGS_TRANSFER_PROGRESS_ROOT": str(progress),
        "WGS_TRANSFER_PLAN_PATH": str(plan),
        "WGS_TRANSFER_ANALYSIS_ID": "WGS_20260909_120000_A1B2C3",
        "WGS_TRANSFER_ATTEMPT": "1",
        "WGS_TRANSFER_STAGE": "step1_upload",
        "WGS_TRANSFER_DIRECTION": "upload",
        "WGS_TRANSFER_CHECKPOINT_POLL_SECONDS": "0.02",
    }

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(fake),
            "cp",
            "/secret/batch/raw/S1_R1.fastq.gz",
            "obs://secret/prefix/raw/S1_R1.fastq.gz",
            f"-cpd={checkpoint}",
            "-vmd5",
            "-vlength",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(next(progress.glob("*.json")).read_text(encoding="utf-8"))
    assert payload["file_key"] == hashlib.sha256(relative.encode()).hexdigest()
    assert payload["display_name"] == "S1_R1.fastq.gz"
    assert payload["bytes_total"] == payload["bytes_done"] == 300
    assert payload["checkpoint_observed"] is True
    assert payload["checksum_status"] == "verified"
    serialized = json.dumps(payload)
    assert "obs://" not in serialized
    assert "/secret" not in serialized


def test_wrapper_matches_plan_identity_when_obs_destination_flattens_raw_prefix(
    tmp_path: Path,
) -> None:
    wrapper = load_wrapper()
    relative = "raw/S1_R1.fastq.gz"
    plan = tmp_path / "transfer-plan.json"
    plan.write_text(
        json.dumps({"entries": [{"relative_path": relative, "size_bytes": 300}]}),
        encoding="utf-8",
    )

    public_file = wrapper._public_file(
        [
            "cp",
            "/secret/source.fastq.gz",
            "obs://secret/prefix/S1_R1.fastq.gz",
        ],
        plan,
    )

    assert public_file == {
        "file_key": hashlib.sha256(relative.encode()).hexdigest(),
        "display_name": "S1_R1.fastq.gz",
        "bytes_total": 300,
    }


def test_wrapper_matches_step5_plan_created_after_process_start(tmp_path: Path) -> None:
    plan = tmp_path / "transfer-plan.json"
    checkpoint = tmp_path / "checkpoint"
    fake = tmp_path / "fake_obsutil.py"
    fake.write_text(
        "import json, os, pathlib, sys, time\n"
        "time.sleep(.05)\n"
        "pathlib.Path(os.environ['WGS_TRANSFER_PLAN_PATH']).write_text(json.dumps({"
        "'entries': [{'relative_path': 'cram/S2.cram', 'size_bytes': 300}]}))\n"
        "cpd = next(a.split('=', 1)[1] for a in sys.argv if a.startswith('-cpd='))\n"
        "folder = pathlib.Path(cpd) / 'download'; folder.mkdir(parents=True, exist_ok=True)\n"
        "(folder / 'state.xml').write_text('''<DownloadFileCheckpoint>"
        "<ObjectInfo><Size>300</Size></ObjectInfo><DownloadParts>"
        "<DownloadPart><RangeStart>0</RangeStart><RangeEnd>99</RangeEnd><IsCompleted>true</IsCompleted></DownloadPart>"
        "</DownloadParts></DownloadFileCheckpoint>''')\n"
        "time.sleep(.2)\n",
        encoding="utf-8",
    )
    progress = tmp_path / "progress"
    env = {
        **os.environ,
        "WGS_REAL_OBSUTIL_BIN": sys.executable,
        "WGS_TRANSFER_PROGRESS_ROOT": str(progress),
        "WGS_TRANSFER_PLAN_PATH": str(plan),
        "WGS_TRANSFER_ANALYSIS_ID": "WGS_20260909_120000_A1B2C3",
        "WGS_TRANSFER_ATTEMPT": "1",
        "WGS_TRANSFER_STAGE": "step5_download",
        "WGS_TRANSFER_DIRECTION": "download",
        "WGS_TRANSFER_CHECKPOINT_POLL_SECONDS": "0.02",
    }

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(fake),
            "cp",
            "obs://secret/prefix/cram/S2.cram",
            "/secret/batch/cram/S2.cram.partial",
            f"-cpd={checkpoint}",
            "-vmd5",
            "-vlength",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(next(progress.glob("*.json")).read_text(encoding="utf-8"))
    assert payload["display_name"] == "S2.cram"
    assert payload["source"] == "obsutil-checkpoint"
