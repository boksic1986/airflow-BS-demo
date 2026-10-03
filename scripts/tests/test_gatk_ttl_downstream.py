"""Synthetic tests for the GATK Step4/Step5 deleted-Master handoff."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import textwrap

import pytest
import yaml


SCRIPTS = Path(__file__).parents[1]
ANALYSIS_ID = "GATK_20260908_120000_A1B2C3"
RUN_ID = f"{ANALYSIS_ID}-a1"
MASTER_UID = "uid-original"


def request_path(stage: str) -> Path:
    return (Path(os.environ["GATK_RUNTIME_REQUEST_ROOT"]) / ANALYSIS_ID
            / "attempt-1" / f"{stage}.request.json")


def request_hash(stage: str) -> str:
    return json.loads(request_path(stage).read_text(encoding="utf-8"))["request_hash"]


def load_downstream(monkeypatch):
    source = SCRIPTS / "gatk_ttl_downstream.py"
    assert source.is_file(), "GATK TTL downstream helper is missing"
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("gatk_ttl_downstream_test", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def attempt(tmp_path: Path, monkeypatch):
    request_root = tmp_path / "requests"
    workdir = tmp_path / "runs" / ANALYSIS_ID / "attempt-1"
    bundle = workdir / "cce"
    bundle.mkdir(parents=True)
    monkeypatch.setenv("GATK_RUNTIME_REQUEST_ROOT", str(request_root))

    for stage in ("step4_publish", "step5_download"):
        request = request_root / ANALYSIS_ID / "attempt-1" / f"{stage}.request.json"
        request.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "analysis_id": ANALYSIS_ID,
            "attempt": 1,
            "stage": stage,
            "generation": 2,
            "orchestration_contract_version": 2,
            "execution_id": f"{ANALYSIS_ID}-a1-{stage}-g2",
            "runtime_workdir": str(workdir),
        }
        payload["request_hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        request.write_text(json.dumps(payload), encoding="utf-8")
    (workdir / "batch-binding.json").write_text(json.dumps({
        "schema_version": "gatk-runtime.batch-binding.v1",
        "analysis_id": ANALYSIS_ID,
        "attempt": 1,
        "run_id": RUN_ID,
        "namespace": "test-ns",
        "master_job": "master-mock",
        "run_label": "cce-run-0123456789abcdef",
        "cce_bundle": str(bundle),
    }), encoding="utf-8")
    contract = {
        "schema_version": 3,
        "identity": {"run_id": RUN_ID, "project": "synthetic", "batch": "mock"},
        "kubernetes": {"namespace": "test-ns", "master_job": "master-mock"},
        "paths": {"run_dir": "/synthetic/run"},
    }
    (bundle / "BATCH_RUNTIME.yaml").write_text(
        yaml.safe_dump(contract), encoding="utf-8"
    )
    (bundle / "master-job.yaml").write_text(yaml.safe_dump({
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": "master-mock",
            "namespace": "test-ns",
            "labels": {"cce.biosan.cn/run-id": "cce-run-0123456789abcdef"},
            "annotations": {"cce-pipeline/handoff-version": "2"},
        },
        "spec": {"template": {"spec": {"containers": [{"name": "master"}]}}},
    }), encoding="utf-8")
    (bundle / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    (bundle / "scenario.json").write_text(json.dumps({
        "query": "absent", "reader": "missing_terminal",
    }), encoding="utf-8")
    (bundle / "cce_batch_runtime.py").write_text(textwrap.dedent('''\
        import json
        from pathlib import Path
        from types import SimpleNamespace

        def _load(bundle, _operator):
            contract = json.loads((Path(bundle) / 'contract.json').read_text())
            return contract, {
                'bundle': str(bundle), 'kubernetes': {'namespace': 'test-ns'},
            }, ()

        def _read_master_handoff(bundle, contract):
            path = Path(bundle) / 'evidence' / contract['identity']['run_id'] / 'MASTER_HANDOFF.json'
            return json.loads(path.read_text())

        def _handoff_binding(bundle, contract):
            return {
                'attempt': 1, 'execution_generation': 1,
                'request_hash': 'b' * 64,
                'config_sha256': 'c' * 64,
                'manifest_sha256': 'd' * 64,
                'files_sha256': {},
            }

        def _batch_lock_name(contract):
            return 'cce-batch-lock-mock'

        def writer_for_bundle(runtime, bundle, contract, config):
            scenario = json.loads((Path(bundle) / 'scenario.json').read_text())
            return {} if scenario.get('protected_writer') else None

        def _recovery_native_success(bundle, contract, job_uid):
            path = Path(bundle) / 'evidence' / contract['identity']['run_id'] / 'mirror' / 'RUN_COMPLETE.json'
            return json.loads(path.read_text()) if path.is_file() else None

        def _inventory_result(config, kind, name, *args, source):
            bundle = Path(config['bundle'])
            assert name == '-l' and len(args) == 2 and args[1] == '--chunk-size=0'
            selector = args[0]
            assert selector in {
                'cce.biosan.cn/run-id=cce-run-0123456789abcdef',
                'cce-pipeline/run-id=' + contract_run_id(bundle),
            }
            if source == 'recovery_query':
                assert selector.startswith('cce.biosan.cn/run-id=')
            queries_path = bundle / 'inventory-queries.json'
            queries = json.loads(queries_path.read_text()) if queries_path.is_file() else []
            queries.append({'kind': kind, 'selector': selector, 'source': source})
            queries_path.write_text(json.dumps(queries))
            scenario = json.loads((bundle / 'scenario.json').read_text())
            if (scenario.get('second_inventory_active') and kind == 'pods'
                    and selector.startswith('cce-pipeline/run-id=')):
                label, value = selector.split('=', 1)
                return {'kind': 'List', 'metadata': {'continue': ''}, 'items': [{
                    'metadata': {
                        'name': 'worker-active', 'namespace': 'test-ns',
                        'uid': 'uid-worker-active', 'labels': {label: value},
                    },
                    'status': {'phase': 'Running'},
                }]}
            return {'kind': 'List', 'metadata': {'continue': ''}, 'items': []}

        def _kubectl_json(config, kind, name, *args, **kwargs):
            raise AssertionError('second-label inventory must use raw complete JSON')

        def _recovery_query(config, kind, name, *args, **kwargs):
            bundle = Path(config['bundle'])
            if kind == 'configmap':
                assert name == 'cce-batch-lock-mock'
                scenario = json.loads((bundle / 'scenario.json').read_text())
                return {'metadata': {'name': name}, 'data': {
                    'project': 'synthetic', 'batch': 'mock',
                    'run_id': scenario.get('lock_run_id', contract_run_id(bundle)),
                }}
            if kind in {'jobs', 'pods'}:
                return _inventory_result(config, kind, name, *args, source='recovery_query')
            assert kind == 'job'
            if name != 'master-mock':
                created_path = bundle / 'reader-created.json'
                if not created_path.is_file():
                    return None
                created = json.loads(created_path.read_text())
                assert name == created['name']
                if (bundle / 'reader-deletions.json').is_file():
                    return None
                (bundle / 'reader-rechecked.json').write_text(json.dumps(created))
                return {
                    'metadata': {**created['document']['metadata'], 'uid': created['uid']},
                    'spec': created['document']['spec'],
                }
            scenario = json.loads((bundle / 'scenario.json').read_text())
            if scenario['query'] == 'api_error':
                raise RuntimeError('Kubernetes API unavailable')
            if scenario['query'] == 'foreign_live_uid':
                return {'metadata': {
                    'name': 'master-mock', 'namespace': 'test-ns',
                    'uid': 'uid-foreign', 'resourceVersion': '10',
                    'labels': {'cce.biosan.cn/run-id': 'cce-run-0123456789abcdef'},
                }, 'status': {
                    'active': 0, 'conditions': [{'type': 'Complete', 'status': 'True'}]}}
            return None

        def _job_flags(job):
            status = job.get('status') or {}
            conditions = status.get('conditions') or []
            active = bool(int(status.get('active') or 0))
            complete = any(row.get('type') == 'Complete' and row.get('status') == 'True'
                           for row in conditions)
            failed = any(row.get('type') == 'Failed' and row.get('status') == 'True'
                         for row in conditions)
            return active, complete, failed

        def _reader_job(bundle, contract):
            return {
                'apiVersion': 'batch/v1', 'kind': 'Job',
                'metadata': {'name': 'reader-template', 'namespace': 'test-ns'},
                'spec': {'template': {'spec': {
                    'restartPolicy': 'Never',
                    'containers': [{'name': 'reader', 'volumeMounts': [
                        {'name': 'workspace', 'mountPath': '/workspace'}]}],
                    'volumes': [{'name': 'workspace', 'persistentVolumeClaim':
                        {'claimName': 'synthetic-pvc'}}],
                }}},
            }

        def _create_job_from_document(config, document):
            bundle = Path(config['bundle'])
            count_path = bundle / 'reader-create-count.txt'
            count = int(count_path.read_text()) if count_path.is_file() else 0
            count_path.write_text(str(count + 1))
            scenario = json.loads((bundle / 'scenario.json').read_text())
            if scenario.get('create') == 'unknown':
                raise RuntimeError('create response unavailable and reader identity unknown')
            created = {
                'name': document['metadata']['name'],
                'uid': 'uid-reader-created',
                'document': document,
            }
            (bundle / 'reader-created.json').write_text(json.dumps(created))
            if scenario.get('create') == 'response_lost':
                raise RuntimeError('create response lost after server accepted reader')
            return {'metadata': {'name': created['name'], 'uid': created['uid']}}

        def _wait_pod(config, name, uid, *args, **kwargs):
            created = json.loads((Path(config['bundle']) / 'reader-created.json').read_text())
            assert (name, uid) == (created['name'], created['uid'])
            return 'pod-reader-created'

        def _workflow_completion_specs(contract):
            return {'RUN_COMPLETE.json': {'required': True}}

        def _read_pod_evidence(config, pod, source, *, completion_specs, include_jobs, timeout):
            bundle = Path(config['bundle'])
            assert pod == 'pod-reader-created'
            assert source == '/synthetic/run/evidence/' + contract_run_id(bundle)
            assert completion_specs and include_jobs is False
            (bundle / 'reader-read.json').write_text(json.dumps({'pod': pod, 'source': source}))
            scenario = json.loads((bundle / 'scenario.json').read_text())
            if scenario['reader'] == 'missing_terminal':
                return {
                    'START_CONFIRMED.json': {'run_id': contract_run_id(bundle)},
                    '_files_present': ['START_CONFIRMED.json'],
                }, None
            assert scenario['reader'] == 'terminal'
            evidence = json.loads((bundle / 'reader-sfs.json').read_text())
            evidence['_files_present'] = sorted(evidence)
            return evidence, None

        def contract_run_id(bundle):
            return json.loads((bundle / 'contract.json').read_text())['identity']['run_id']

        def _write_mirror_evidence(bundle, run_id, evidence, *, project, batch):
            root = Path(bundle) / 'evidence' / run_id / 'mirror'
            root.mkdir(parents=True, exist_ok=True)
            for name, content in evidence.items():
                if name == '_files_present':
                    continue
                (root / name).write_text(json.dumps(content))
            (Path(bundle) / 'reader-wrote.json').write_text(json.dumps({
                'run_id': run_id, 'project': project, 'batch': batch,
                'files': sorted(name for name in evidence if name != '_files_present'),
            }))
            return True

        def _kubectl(config, *args):
            return ['kubectl', str(config['bundle']), *args]

        def _run(command, *, input_bytes=None, check=False, capture=True, timeout=30, **kwargs):
            bundle = Path(command[1])
            if command[2] == 'get':
                assert len(command) == 9 and command[3] in {'jobs', 'pods'}
                assert command[4] == '-l' and command[6:] == ['--chunk-size=0', '-o', 'json']
                assert command[5] == 'cce-pipeline/run-id=' + contract_run_id(bundle)
                assert input_bytes is None and check is False and capture is True and timeout == 30
                listing = _inventory_result(
                    {'bundle': str(bundle)}, command[3], '-l', command[5],
                    '--chunk-size=0', source='raw_get',
                )
                scenario = json.loads((bundle / 'scenario.json').read_text())
                if scenario.get('second_inventory_output') == 'empty':
                    return SimpleNamespace(returncode=0, stdout=b'', stderr=b'')
                if scenario.get('second_inventory_output') == 'incomplete':
                    listing['metadata']['continue'] = 'next-page'
                return SimpleNamespace(
                    returncode=0, stdout=json.dumps(listing).encode('utf-8'), stderr=b'',
                )
            assert command[2] == 'delete' and input_bytes is not None
            path = bundle / 'reader-deletions.json'
            deletions = json.loads(path.read_text()) if path.is_file() else []
            deletions.append({
                'command': command[2:], 'body': json.loads(input_bytes),
                'check': check, 'capture': capture, 'timeout': timeout,
            })
            path.write_text(json.dumps(deletions))
            return SimpleNamespace(returncode=0, stdout='', stderr='')

        def _record(bundle, stage, master_bundle, expected_master_uid):
            terminal = Path(bundle) / 'evidence' / contract_run_id(Path(bundle)) / 'mirror' / 'RUN_COMPLETE.json'
            assert json.loads(terminal.read_text())['job_uid'] == expected_master_uid
            count_path = Path(bundle) / 'native-call-count.txt'
            count = int(count_path.read_text()) if count_path.exists() else 0
            count_path.write_text(str(count + 1))
            (Path(bundle) / 'native-call.json').write_text(json.dumps({
                'stage': stage,
                'master_bundle': str(master_bundle),
                'expected_master_uid': expected_master_uid,
            }))

        def step4(bundle, contract, config, modules, *, args, master_bundle, expected_master_uid):
            _record(bundle, 'step4_publish', master_bundle, expected_master_uid)

        def step5(args, bundle, contract, config, modules, *, master_bundle, expected_master_uid):
            _record(bundle, 'step5_download', master_bundle, expected_master_uid)
    '''), encoding="utf-8")
    evidence = bundle / "evidence" / RUN_ID
    mirror = evidence / "mirror"
    mirror.mkdir(parents=True)
    (evidence / "MASTER_HANDOFF.json").write_text(json.dumps({
        "schema_version": 2,
        "run_id": RUN_ID,
        "job_name": "master-mock",
        "job_uid": MASTER_UID,
        "pod_uid": "uid-master-pod",
        "state": "START_CONFIRMED",
        "attempt": 1,
        "execution_generation": 1,
        "request_hash": "b" * 64,
        "config_sha256": "c" * 64,
        "manifest_sha256": "d" * 64,
        "files_sha256": {},
    }), encoding="utf-8")
    (mirror / "START_CONFIRMED.json").write_text(json.dumps({
        "run_id": RUN_ID, "job_uid": MASTER_UID,
    }), encoding="utf-8")
    (mirror / "RUN_COMPLETE.json").write_text(json.dumps({
        "job_uid": MASTER_UID,
        "state": "SUCCEEDED",
        "exit_codes": {"preflight": 0, "analysis": 0, "final_dryrun": 0},
    }), encoding="utf-8")
    (mirror / "MIRROR_COMPLETE.json").write_text(json.dumps({
        "run_id": RUN_ID, "job_uid": MASTER_UID,
    }), encoding="utf-8")
    (mirror / "workflow-completion.json").write_text(json.dumps({
        "run_id": RUN_ID, "job_uid": MASTER_UID,
    }), encoding="utf-8")
    return bundle


@pytest.mark.parametrize("stage", ("step4_publish", "step5_download"))
def test_ttl_absent_master_runs_exact_frozen_downstream_once(
    attempt: Path, monkeypatch, stage: str
) -> None:
    downstream = load_downstream(monkeypatch)

    assert downstream.run_stage(ANALYSIS_ID, 1, stage, 2, request_hash(stage)) is None
    assert json.loads((attempt / "native-call.json").read_text()) == {
        "stage": stage,
        "master_bundle": str(attempt),
        "expected_master_uid": MASTER_UID,
    }


def test_ttl_downstream_rejects_wrong_request_hash_before_dispatch(
    attempt: Path, monkeypatch
) -> None:
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, "f" * 64)
    assert not (attempt / "native-call.json").exists()


def test_ttl_downstream_rejects_changed_request_body_with_stale_matching_hash(
    attempt: Path, monkeypatch
) -> None:
    request = request_path("step4_publish")
    payload = json.loads(request.read_text(encoding="utf-8"))
    original_hash = payload["request_hash"]
    payload["synthetic_extension"] = "tampered"
    assert hashlib.sha256(json.dumps(
        {key: value for key, value in payload.items() if key != "request_hash"},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest() != original_hash
    request.write_text(json.dumps(payload), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, original_hash)
    assert not (attempt / "native-call.json").exists()


@pytest.mark.parametrize("stage", ("step4_publish", "step5_download"))
@pytest.mark.parametrize("failure", ("missing_terminal", "wrong_terminal_uid", "api_error", "foreign_live_uid"))
def test_ttl_downstream_rejects_unproved_or_conflicting_master(
    attempt: Path, monkeypatch, stage: str, failure: str
) -> None:
    terminal = attempt / "evidence" / RUN_ID / "mirror" / "RUN_COMPLETE.json"
    if failure == "missing_terminal":
        terminal.unlink()
    elif failure == "wrong_terminal_uid":
        value = json.loads(terminal.read_text())
        value["job_uid"] = "uid-foreign"
        terminal.write_text(json.dumps(value), encoding="utf-8")
    else:
        (attempt / "scenario.json").write_text(json.dumps({
            "query": failure, "reader": "missing_terminal",
        }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, stage, 2, request_hash(stage))
    assert not (attempt / "native-call.json").exists()


def test_missing_mirror_reads_uid_bound_sfs_terminal_then_cleans_own_reader(
    attempt: Path, monkeypatch
) -> None:
    mirror = attempt / "evidence" / RUN_ID / "mirror"
    terminal = json.loads((mirror / "RUN_COMPLETE.json").read_text())
    (mirror / "RUN_COMPLETE.json").unlink()
    (attempt / "reader-sfs.json").write_text(json.dumps({
        "START_CONFIRMED.json": {"run_id": RUN_ID, "job_uid": MASTER_UID},
        "RUN_COMPLETE.json": terminal,
        "MIRROR_COMPLETE.json": {"run_id": RUN_ID, "job_uid": MASTER_UID},
        "workflow-completion.json": {"run_id": RUN_ID, "job_uid": MASTER_UID},
    }), encoding="utf-8")
    (attempt / "scenario.json").write_text(json.dumps({
        "query": "absent", "reader": "terminal",
    }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    assert downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, request_hash("step4_publish")) is None
    assert json.loads((mirror / "RUN_COMPLETE.json").read_text()) == terminal
    assert json.loads((attempt / "reader-read.json").read_text())["source"] == (
        f"/synthetic/run/evidence/{RUN_ID}"
    )
    assert json.loads((attempt / "reader-wrote.json").read_text())["files"] == [
        "MIRROR_COMPLETE.json", "RUN_COMPLETE.json", "START_CONFIRMED.json",
        "workflow-completion.json",
    ]
    assert json.loads((attempt / "native-call.json").read_text())["expected_master_uid"] == MASTER_UID
    assert (attempt / "native-call-count.txt").read_text() == "1"
    created = json.loads((attempt / "reader-created.json").read_text())
    assert created["name"] != "master-mock"
    assert created["uid"] == "uid-reader-created"
    reader_mounts = created["document"]["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]
    workspace_mounts = [mount for mount in reader_mounts if mount["name"] == "workspace"]
    assert workspace_mounts and all(mount["readOnly"] is True for mount in workspace_mounts)
    reader_volumes = created["document"]["spec"]["template"]["spec"]["volumes"]
    workspace_volumes = [volume for volume in reader_volumes if volume["name"] == "workspace"]
    assert workspace_volumes and all(
        volume["persistentVolumeClaim"]["readOnly"] is True
        for volume in workspace_volumes
    )
    assert json.loads((attempt / "reader-rechecked.json").read_text())["uid"] == created["uid"]
    deletions = json.loads((attempt / "reader-deletions.json").read_text())
    assert len(deletions) == 1
    assert deletions[0]["command"] == [
        "delete", "--raw", f"/apis/batch/v1/namespaces/test-ns/jobs/{created['name']}",
        "-f", "-",
    ]
    assert deletions[0]["body"]["apiVersion"] == "v1"
    assert deletions[0]["body"]["kind"] == "DeleteOptions"
    assert deletions[0]["body"]["preconditions"]["uid"] == created["uid"]


def test_ttl_downstream_rejects_foreign_batch_lock_owner(
    attempt: Path, monkeypatch
) -> None:
    (attempt / "scenario.json").write_text(json.dumps({
        "query": "absent", "reader": "missing_terminal", "lock_run_id": "foreign-run",
    }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, request_hash("step4_publish"))
    assert not (attempt / "reader-created.json").exists()
    assert not (attempt / "native-call.json").exists()


def test_ttl_downstream_rejects_physical_run_failed_even_with_success_terminal(
    attempt: Path, monkeypatch
) -> None:
    mirror = attempt / "evidence" / RUN_ID / "mirror"
    (mirror / "RUN_FAILED.json").write_text(json.dumps({
        "job_uid": MASTER_UID, "state": "FAILED",
    }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, request_hash("step4_publish"))
    assert not (attempt / "reader-created.json").exists()
    assert not (attempt / "native-call.json").exists()


def test_ttl_downstream_fences_both_run_labels_and_active_second_label_pod(
    attempt: Path, monkeypatch
) -> None:
    (attempt / "scenario.json").write_text(json.dumps({
        "query": "absent", "reader": "missing_terminal",
        "second_inventory_active": True,
    }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, request_hash("step4_publish"))
    queries = json.loads((attempt / "inventory-queries.json").read_text())
    assert {query["selector"] for query in queries} == {
        "cce.biosan.cn/run-id=cce-run-0123456789abcdef",
        f"cce-pipeline/run-id={RUN_ID}",
    }
    assert all(
        query["source"] == "raw_get"
        for query in queries if query["selector"].startswith("cce-pipeline/run-id=")
    )
    assert not (attempt / "reader-created.json").exists()
    assert not (attempt / "native-call.json").exists()


@pytest.mark.parametrize("output", ("empty", "incomplete"))
def test_ttl_downstream_rejects_unproved_raw_second_label_inventory(
    attempt: Path, monkeypatch, output: str
) -> None:
    (attempt / "scenario.json").write_text(json.dumps({
        "query": "absent", "reader": "missing_terminal",
        "second_inventory_output": output,
    }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, request_hash("step4_publish"))
    queries = json.loads((attempt / "inventory-queries.json").read_text())
    assert any(
        query == {"kind": "jobs", "selector": f"cce-pipeline/run-id={RUN_ID}",
                  "source": "raw_get"}
        for query in queries
    )
    assert not (attempt / "reader-created.json").exists()
    assert not (attempt / "native-call.json").exists()


def test_ttl_downstream_rejects_protected_writer_before_reader_or_dispatch(
    attempt: Path, monkeypatch
) -> None:
    (attempt / "scenario.json").write_text(json.dumps({
        "query": "absent", "reader": "missing_terminal", "protected_writer": True,
    }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, request_hash("step4_publish"))
    assert not (attempt / "reader-created.json").exists()
    assert not (attempt / "native-call.json").exists()


def test_ttl_downstream_rejects_physical_sfs_run_failed_even_when_decode_is_none(
    attempt: Path, monkeypatch
) -> None:
    mirror = attempt / "evidence" / RUN_ID / "mirror"
    terminal = json.loads((mirror / "RUN_COMPLETE.json").read_text())
    (mirror / "RUN_COMPLETE.json").unlink()
    (attempt / "reader-sfs.json").write_text(json.dumps({
        "START_CONFIRMED.json": {"run_id": RUN_ID, "job_uid": MASTER_UID},
        "RUN_COMPLETE.json": terminal,
        "workflow-completion.json": {"run_id": RUN_ID, "job_uid": MASTER_UID},
        "RUN_FAILED.json": None,
    }), encoding="utf-8")
    (attempt / "scenario.json").write_text(json.dumps({
        "query": "absent", "reader": "terminal",
    }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, request_hash("step4_publish"))
    assert (attempt / "reader-created.json").exists()
    assert (attempt / "reader-deletions.json").exists()
    assert not (attempt / "reader-wrote.json").exists()
    assert not (attempt / "native-call.json").exists()


def test_ttl_downstream_reconciles_lost_reader_create_response_without_recreate(
    attempt: Path, monkeypatch
) -> None:
    mirror = attempt / "evidence" / RUN_ID / "mirror"
    terminal = json.loads((mirror / "RUN_COMPLETE.json").read_text())
    (mirror / "RUN_COMPLETE.json").unlink()
    (attempt / "reader-sfs.json").write_text(json.dumps({
        "START_CONFIRMED.json": {"run_id": RUN_ID, "job_uid": MASTER_UID},
        "RUN_COMPLETE.json": terminal,
        "workflow-completion.json": {"run_id": RUN_ID, "job_uid": MASTER_UID},
    }), encoding="utf-8")
    (attempt / "scenario.json").write_text(json.dumps({
        "query": "absent", "reader": "terminal", "create": "response_lost",
    }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    assert downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, request_hash("step4_publish")) is None
    assert (attempt / "reader-create-count.txt").read_text() == "1"
    assert (attempt / "native-call-count.txt").read_text() == "1"
    assert len(json.loads((attempt / "reader-deletions.json").read_text())) == 1


def test_ttl_downstream_rejects_unknown_reader_create_result_without_retry(
    attempt: Path, monkeypatch
) -> None:
    (attempt / "evidence" / RUN_ID / "mirror" / "RUN_COMPLETE.json").unlink()
    (attempt / "scenario.json").write_text(json.dumps({
        "query": "absent", "reader": "missing_terminal", "create": "unknown",
    }), encoding="utf-8")
    downstream = load_downstream(monkeypatch)

    with pytest.raises((RuntimeError, ValueError)):
        downstream.run_stage(ANALYSIS_ID, 1, "step4_publish", 2, request_hash("step4_publish"))
    assert (attempt / "reader-create-count.txt").read_text() == "1"
    assert not (attempt / "reader-created.json").exists()
    assert not (attempt / "reader-deletions.json").exists()
    assert not (attempt / "native-call.json").exists()
