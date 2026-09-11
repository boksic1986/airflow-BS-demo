import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch, MagicMock

spec = importlib.util.spec_from_file_location('gate', pathlib.Path(__file__).resolve().parents[1] / 'wgs_runtime_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class HandoffIdentityTest(unittest.TestCase):
    def test_request_open_retries_transient_missing_file(self):
        path=MagicMock();path.is_file.return_value=True;path.is_symlink.return_value=False
        value=dict(schema_version='wgs-runtime.request.v4',analysis_id='WGS_MOCK',attempt=1,stage='step6_materialize')
        path.read_text.side_effect=[FileNotFoundError('NFS visibility'),json.dumps(value)]
        with patch.object(gate,'_request_path',return_value=path),patch.object(gate.time,'sleep') as sleep:
            self.assertEqual(gate.load_request('WGS_MOCK',1,'step6_materialize'),value)
            sleep.assert_called_once_with(5)

    def test_request_identity_errors_do_not_retry(self):
        path=MagicMock();path.is_file.return_value=True;path.is_symlink.return_value=False
        path.read_text.return_value=json.dumps(dict(schema_version='wgs-runtime.request.v4',analysis_id='OTHER',attempt=1,stage='step6_materialize'))
        with patch.object(gate,'_request_path',return_value=path),patch.object(gate.time,'sleep') as sleep:
            with self.assertRaisesRegex(ValueError,'identity mismatch'):gate.load_request('WGS_MOCK',1,'step6_materialize')
            sleep.assert_not_called()

    def fixture(self, root):
        artifact = root / 'sample.tsv'
        artifact.write_text('synthetic\n')
        request = dict(analysis_id='WGS_MOCK', attempt=1, execution_id='WGS_MOCK-a1', generation=2, request_hash='abc', release_id='mock-release', artifact_root=str(root), artifact_keys={'sampleinfo': 'sample.tsv'})
        receipt = {**request, 'schema_version': 'wgs.prepare-sampleinfo.receipt.v1', 'safe_candidates': [], 'sampleinfo': {'artifact_key': 'sample.tsv', 'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(), 'row_count': 0}}
        req = root / 'request.json'; req.write_text(json.dumps(request))
        out = root / 'prepare_sampleinfo.receipt.json'; out.write_text(json.dumps(receipt))
        return req, out, request

    def test_projection_keeps_validated_identity_without_private_descriptors(self):
        with tempfile.TemporaryDirectory() as d:
            req, _, identity = self.fixture(pathlib.Path(d))
            result = gate._validated_prepare_receipt({'stage': 'prepare_sampleinfo'}, req)
            for key in ('analysis_id', 'attempt', 'execution_id', 'generation', 'request_hash', 'release_id'):
                self.assertEqual(result.get(key), identity[key], key)
            self.assertNotIn('sampleinfo', result)
            self.assertNotIn('artifact_root', result)

    def test_wrong_attempt_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            req, out, _ = self.fixture(pathlib.Path(d)); r=json.loads(out.read_text());r['attempt']=3;out.write_text(json.dumps(r))
            with self.assertRaisesRegex(RuntimeError, 'attempt mismatch'):
                gate._validated_prepare_receipt({'stage':'prepare_sampleinfo'}, req)


if __name__ == '__main__':unittest.main()
