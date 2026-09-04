import importlib.util
import base64
import json
from pathlib import Path


def load_module():
    path = Path(__file__).parents[1] / "wgs_evidence_bridge.py"
    spec = importlib.util.spec_from_file_location("wgs_evidence_bridge", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_pod_snapshot_maps_to_observer_event_without_patient_name() -> None:
    module = load_module()
    pod = {
        "metadata": {"name": "private-pod-name", "resourceVersion": "42", "labels": {"job-name": "job-1"}},
        "spec": {"nodeName": "node-a", "containers": [{"name": "main", "resources": {"requests": {"cpu": "2"}}}]},
        "status": {"phase": "Failed", "containerStatuses": [{"name": "main", "imageID": "sha256:abc", "state": {"terminated": {"reason": "OOMKilled", "exitCode": 137}}}]},
    }
    event = module.pod_event(pod, observed_at="2026-08-13T01:02:03+00:00")
    assert event["event_key"].startswith("pod:")
    assert event["pod_hash"] != "private-pod-name"
    assert "private-pod-name" not in json.dumps(event)
    assert event["phase"] == "Failed"
    assert event["container_status"]["state"]["terminated"]["reason"] == "OOMKilled"
    assert event["resource_version"] == "42"
    assert event["workload_role"] == "master"


def test_job_snapshot_maps_to_observer_event() -> None:
    module = load_module()
    job = {"metadata": {"name": "job-1", "resourceVersion": "17"}, "status": {"failed": 1}}
    event = module.job_event(job, observed_at="2026-08-13T01:02:03+00:00")
    assert event == {
        "event_key": "job:job-1:17",
        "observed_at_utc": "2026-08-13T01:02:03+00:00",
        "job": "job-1",
        "resource_version": "17",
        "workload_role": "master",
        "status": {"failed": 1},
    }


def test_snapshot_projection_keeps_only_the_batch_master(tmp_path: Path) -> None:
    module = load_module()
    discovery = tmp_path / "discovery"
    output = tmp_path / "output"
    (discovery / "pods").mkdir(parents=True)
    (discovery / "jobs").mkdir()
    master_metadata = {"resourceVersion": "1", "labels": {"job-name": "wgs-master-a1"}}
    worker_metadata = {"resourceVersion": "1", "labels": {"job-name": "mapping-7"}}
    (discovery / "pods" / "master.json").write_text(json.dumps({"metadata": {"name": "master-pod", **master_metadata}, "status": {"phase": "Running"}}), encoding="utf-8")
    (discovery / "pods" / "worker.json").write_text(json.dumps({"metadata": {"name": "worker-pod", **worker_metadata}, "status": {"phase": "Running"}}), encoding="utf-8")
    (discovery / "jobs" / "master.json").write_text(json.dumps({"metadata": {"name": "wgs-master-a1", "resourceVersion": "1"}}), encoding="utf-8")
    (discovery / "jobs" / "worker.json").write_text(json.dumps({"metadata": {"name": "mapping-7", "resourceVersion": "1"}}), encoding="utf-8")

    module._project_snapshots(discovery, output, set(), master_job="wgs-master-a1")

    pods = (output / "pod-events.jsonl").read_text(encoding="utf-8")
    jobs = (output / "job-events.jsonl").read_text(encoding="utf-8")
    assert "master-pod" not in pods
    assert "worker-pod" not in pods
    assert "wgs-master-a1" in pods
    assert "mapping-7" not in pods + jobs


def test_rule_chunks_append_complete_lines_per_stream_and_resume(tmp_path: Path) -> None:
    module = load_module()
    output = tmp_path / "evidence"
    cursor = output / ".rule-cursor.json"
    first_line = b'{"event":"job_started"}\n'
    incomplete = b'{"event":"job_finished"}'

    applied = module._apply_rule_chunks(
        output,
        cursor,
        [
            {
                "name": "master-a.jsonl",
                "source_offset": 0,
                "next_offset": len(first_line),
                "data_base64": base64.b64encode(first_line + incomplete).decode(),
            }
        ],
    )

    assert applied == len(first_line)
    target = output / "rule-status" / "raw" / "master-a.jsonl"
    assert target.read_bytes() == first_line
    assert json.loads(cursor.read_text(encoding="utf-8"))["master-a.jsonl"] == len(
        first_line
    )

    second_line = incomplete + b"\n"
    applied = module._apply_rule_chunks(
        output,
        cursor,
        [
            {
                "name": "master-a.jsonl",
                "source_offset": len(first_line),
                "next_offset": len(first_line) + len(second_line),
                "data_base64": base64.b64encode(second_line).decode(),
            }
        ],
    )
    assert applied == len(second_line)
    assert target.read_bytes() == first_line + second_line


def test_analysis_log_chunk_is_incremental_and_resets_after_source_truncation(tmp_path: Path) -> None:
    module = load_module()
    output = tmp_path / "evidence"
    cursor = output / ".analysis-log-cursor.json"

    assert module._apply_file_chunk(
        output,
        cursor,
        {"source_offset": 0, "next_offset": 6, "data_base64": base64.b64encode(b"first\n").decode()},
    ) == 6
    assert module._apply_file_chunk(
        output,
        cursor,
        {"source_offset": 6, "next_offset": 13, "data_base64": base64.b64encode(b"second\n").decode()},
    ) == 7
    target = output / "mirror" / "analysis.log"
    assert target.read_text(encoding="utf-8") == "first\nsecond\n"

    assert module._apply_file_chunk(
        output,
        cursor,
        {"source_offset": 0, "next_offset": 4, "data_base64": base64.b64encode(b"new\n").decode()},
    ) == 4
    assert target.read_text(encoding="utf-8") == "new\n"


def test_analysis_log_source_is_bound_to_the_same_run_evidence_directory() -> None:
    module = load_module()

    source = module.analysis_log_source_for_rule_directory(
        "/workspace/wgs/runs/WGS_Clinical/WGS_batch/evidence/run-a1/rule-status/raw"
    )

    assert source == (
        "/workspace/wgs/runs/WGS_Clinical/WGS_batch/evidence/run-a1/analysis.log"
    )


def test_reader_job_mounts_only_workspace_pvc_read_only() -> None:
    module = load_module()
    master = {
        "spec": {
            "template": {
                "spec": {
                    "serviceAccountName": "cce-pipeline-master-v1",
                    "imagePullSecrets": [{"name": "swr-pull"}],
                    "containers": [
                        {
                            "name": "master",
                            "image": "registry/wgs-master@sha256:abc",
                            "volumeMounts": [
                                {"name": "sfs-workspace", "mountPath": "/workspace"},
                                {"name": "obs-data", "mountPath": "/obs-data"},
                            ],
                        }
                    ],
                    "volumes": [
                        {
                            "name": "sfs-workspace",
                            "persistentVolumeClaim": {"claimName": "biosan-clinical"},
                        },
                        {
                            "name": "obs-data",
                            "persistentVolumeClaim": {"claimName": "pvc-obs"},
                        },
                    ],
                }
            }
        }
    }

    reader = module.build_reader_job(
        master,
        namespace="snakemake-ns",
        reader_name="wgs-rule-reader-abc",
    )

    pod = reader["spec"]["template"]["spec"]
    assert reader["metadata"]["namespace"] == "snakemake-ns"
    assert reader["spec"]["activeDeadlineSeconds"] == 300
    assert pod["restartPolicy"] == "Never"
    assert pod["containers"][0]["image"] == "registry/wgs-master@sha256:abc"
    assert pod["containers"][0]["volumeMounts"] == [
        {"name": "sfs-workspace", "mountPath": "/workspace", "readOnly": True}
    ]
    assert pod["volumes"] == [
        {
            "name": "sfs-workspace",
            "persistentVolumeClaim": {
                "claimName": "biosan-clinical",
                "readOnly": True,
            },
        }
    ]
