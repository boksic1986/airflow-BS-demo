"""Synthetic runtime-boundary tests; no CCE, OBS or real sample access."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import yaml


class ResumeTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('gatk_resume', Path(__file__).parents[1]/'gatk_resume.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.aid = 'GATK_20260914_000000_AAAAAA'
        self.request_root = root/'requests'
        self.request_dir = self.request_root/self.aid/'attempt-1'
        self.request_dir.mkdir(parents=True)
        self.bundle = root/'runs'/self.aid/'attempt-1'/'cce'
        self.bundle.mkdir(parents=True)
        self.contract = {'schema_version':3,'identity':{'run_id':self.aid+'-a1','project':'synthetic','batch':'mock'},'kubernetes':{'namespace':'mock','master_job':'master-mock','cleanup_job':'cleanup-mock','reset_job':'reset-mock','repair_job':'repair-mock'},'paths':{'fastq_upload_uri':'mock-input','result_upload_uri':'mock-output'}}
        self.manifest = {'apiVersion':'batch/v1','kind':'Job','metadata':{'name':'master-mock','namespace':'mock','labels':{'cce.biosan.cn/run-id':'cce-run-0123456789abcdef'}},'spec':{'template':{'spec':{'containers':[{'name':'master','image':'mock@sha256:'+'a'*64}]}}}}
        self.job = copy.deepcopy(self.manifest)
        self.job['metadata'].update(uid='old-uid',resourceVersion='10')
        self.job['status'] = {'active':0,'conditions':[{'type':'Failed','status':'True'}]}
        binding = {'schema_version':'gatk-runtime.batch-binding.v1','analysis_id':self.aid,'attempt':1,'run_id':self.aid+'-a1','namespace':'mock','master_job':'master-mock','run_label':'cce-run-0123456789abcdef','cce_bundle':str(self.bundle)}
        (self.bundle.parent/'batch-binding.json').write_text(json.dumps(binding))
        (self.bundle/'BATCH_RUNTIME.yaml').write_text(yaml.safe_dump(self.contract))
        (self.bundle/'master-job.yaml').write_text(yaml.safe_dump(self.manifest))
        self.calls=[]
        self.obs_count=0
        self.workers_active=False
        self.race=False
        self.query_count=0
        self.other_job=None
        def query(cfg, kind, *args):
            if kind=='pods': return {'items':[]}
            if args[0]!='master-mock': return self.other_job
            self.query_count+=1
            result=copy.deepcopy(self.job)
            if self.race and self.query_count>1 and result:
                result['metadata']['resourceVersion']='11'
            return result
        def workers(*a,**kw):
            if self.workers_active: raise RuntimeError('active worker')
        def step2(*a):
            self.calls.append('step2')
            self.job=copy.deepcopy(self.manifest)
            self.job['metadata'].update(uid='new-uid',resourceVersion='20')
        self.runtime=SimpleNamespace(_load=lambda *a:(self.contract,{'obs':{'obsutil_bin':'mock','config_file':'private'}},(SimpleNamespace(inspect_reset_obs=lambda **kw:{'result_count':self.obs_count}),)),_kubectl_json=query,_require_no_active_workers=workers,_claim_batch_lock=lambda *a:self.calls.append('claim'),_kubectl=lambda cfg,*a:['kubectl',*a],step2=step2)
        self.params={'analysis_id':self.aid,'attempt':1,'expected_job_uid':'old-uid','expected_binding_sha256':hashlib.sha256((self.bundle.parent/'batch-binding.json').read_bytes()).hexdigest(),'expected_contract_sha256':hashlib.sha256((self.bundle/'BATCH_RUNTIME.yaml').read_bytes()).hexdigest(),'runtime':self.runtime}
        self.env=patch.dict(os.environ,{'GATK_RUNTIME_REQUEST_ROOT':str(self.request_root)})
        self.env.start(); self.addCleanup(self.env.stop)
        self.process=patch.object(self.module.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'{"kind":"List","items":[]}'))
        self.process.start(); self.addCleanup(self.process.stop)
        self.sleep=patch.object(self.module.time,'sleep',return_value=None)
        self.sleep.start(); self.addCleanup(self.sleep.stop)

    def invoke(self, execute=False):
        return self.module.resume(**self.params,execute=execute)

    def delete(self,command,**kwargs):
        if 'get' in command:
            return SimpleNamespace(returncode=0,stdout=b'{"kind":"List","items":[]}')
        self.calls.append(('delete',command,json.loads(kwargs['input'])))
        self.job=None
        return SimpleNamespace(returncode=0)

    def test_dry_run_never_mutates_cloud(self):
        self.assertEqual(self.invoke()['status'],'ready')
        self.assertEqual(self.calls,[])

    def test_execute_deletes_uid_rv_then_reuses_step2_and_replay_is_read_only(self):
        with patch.object(self.module.subprocess,'run',side_effect=self.delete):
            result=self.invoke(True)
        self.assertEqual(result['replacement_job_uid'],'new-uid')
        deleted=next(x for x in self.calls if isinstance(x,tuple))
        self.assertEqual(deleted[2]['preconditions'],{'uid':'old-uid','resourceVersion':'10'})
        self.assertIn('/apis/batch/v1/namespaces/mock/jobs/master-mock',deleted[1])
        self.assertEqual(deleted[2]['propagationPolicy'],'Foreground')
        before=copy.deepcopy(self.calls)
        self.assertEqual(self.invoke(True)['status'],'completed')
        self.assertEqual(self.calls,before)

    def test_wrong_uid_active_worker_nonempty_obs_and_changed_manifest_fail_closed(self):
        for field in ('uid','workers','obs','image'):
            with self.subTest(field=field):
                saved=copy.deepcopy(self.job)
                if field=='uid':self.job['metadata']['uid']='foreign'
                if field=='workers':self.workers_active=True
                if field=='obs':self.obs_count=1
                if field=='image':self.job['spec']['template']['spec']['containers'][0]['image']='foreign'
                with self.assertRaises((ValueError,RuntimeError)):self.invoke(True)
                self.assertEqual(self.calls,[])
                self.job=saved;self.workers_active=False;self.obs_count=0

    def test_resource_version_race_prevents_delete(self):
        self.race=True
        with patch.object(self.module.subprocess,'run',side_effect=self.delete):
            with self.assertRaises(RuntimeError):self.invoke(True)
        self.assertFalse(any(isinstance(x,tuple) for x in self.calls))

    def test_active_maintenance_job_prevents_resume(self):
        self.other_job={'status':{'active':1}}
        with self.assertRaises(RuntimeError):self.invoke(True)
        self.assertEqual(self.calls,[])

    def test_ambiguous_new_uid_is_never_deleted(self):
        with patch.object(self.module.subprocess,'run',side_effect=self.delete):
            self.invoke(True)
        self.job['metadata']['uid']='unknown-replacement'
        with patch.object(self.module.subprocess,'run',side_effect=AssertionError('unsafe delete')):
            with self.assertRaises(RuntimeError):self.invoke(True)

    def test_cached_historical_worker_is_checked_after_native_refresh(self):
        archive=self.request_dir/'resume-old-uid-jobs.ndjson'
        archive.write_text('{"external_jobid":"historical-worker"}\n')
        self.runtime._parse_jobs_ndjson=lambda text,**kw:[json.loads(text)]
        self.runtime._query_worker_states=lambda cfg,records:[{'state':'ACTIVE'}]
        with self.assertRaises(RuntimeError):self.invoke(True)
        self.assertEqual(self.calls,[])

    def test_explicit_empty_pod_list_is_safe_even_when_native_helper_returns_none(self):
        original=self.runtime._kubectl_json
        self.runtime._kubectl_json=lambda cfg,kind,*args: None if kind=='pods' else original(cfg,kind,*args)
        requests=[]
        def inventory(command,**kwargs):
            requests.append(command)
            return SimpleNamespace(returncode=0,stdout=b'{"kind":"List","items":[]}')
        with patch.object(self.module.subprocess,'run',side_effect=inventory):
            self.assertEqual(self.invoke()['status'],'ready')
        self.assertTrue(requests)
        self.assertEqual(requests[0],['kubectl','get','pods','-l','job-name=master-mock','-o','json'])

    def test_empty_invalid_or_failed_pod_inventory_never_authorizes_resume(self):
        import subprocess
        for response in (b'',b'{}',b'{"items":null}',b'{"items":{}}',b'invalid',b'{"items":[null]}'):
            with self.subTest(response=response):
                with patch.object(self.module.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=response)):
                    with self.assertRaises(RuntimeError):self.invoke(True)
                self.assertEqual(self.calls,[])
        with patch.object(self.module.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['kubectl'])):
            with self.assertRaises(RuntimeError):self.invoke(True)
        self.assertEqual(self.calls,[])


class ExternalResumeTests(ResumeTests):
    def external_setup(self):
        self.job = None
        self.params['externally_removed_master'] = True
        mirror = self.bundle/'evidence'/('mock')/'mirror'
        mirror.mkdir(parents=True)
        self.runtime._mirror_dir = lambda *a: mirror
        (mirror.parent/'MASTER_HANDOFF.json').write_text(json.dumps({
            'run_id': self.aid+'-a1', 'job_name': 'master-mock',
            'job_uid': 'old-uid', 'project': 'synthetic', 'batch': 'mock'}))
        return mirror

    def test_absent_master_default_still_rejected(self):
        self.job = None
        with self.assertRaises(self.module.ResumeGuardError): self.invoke(True)
        self.assertEqual(self.calls, [])

    def test_external_removal_recreates_without_delete_and_replays(self):
        self.external_setup()
        result = self.invoke(True)
        self.assertEqual(result['replacement_job_uid'], 'new-uid')
        self.assertEqual(result['origin'], 'operator_confirmed_external_removal')
        self.assertNotIn('expected_resource_version', result)
        self.assertEqual(self.calls, ['claim','step2'])
        self.invoke(True)
        self.assertEqual(self.calls, ['claim','step2'])

    def test_external_removal_wrong_binding_blocked(self):
        mirror = self.external_setup()
        path = mirror.parent/'MASTER_HANDOFF.json'
        d=json.loads(path.read_text());d['job_uid']='foreign';path.write_text(json.dumps(d))
        with self.assertRaises(self.module.ResumeGuardError): self.invoke(True)
        self.assertEqual(self.calls, [])

    def test_external_removal_inventory_unknown_or_active_blocks(self):
        self.external_setup()
        for response in (b'{"kind":"List","metadata":{"continue":"next"},"items":[]}',
                         b'{"kind":"List","items":[{"kind":"Pod","status":{"phase":"Running"}}]}',
                         b'{"kind":"List","items":[{"kind":"Job","status":{"active":1}}]}'):
            with self.subTest(response=response), patch.object(self.module.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=response)):
                with self.assertRaises(self.module.ResumeGuardError): self.invoke(True)
                self.assertEqual(self.calls, [])

    def test_external_removal_native_guard_retained(self):
        self.external_setup();self.workers_active=True
        with self.assertRaises(RuntimeError): self.invoke(True)
        self.assertEqual(self.calls, [])

    def test_external_removal_live_dispatch_lock_blocks(self):
        import fcntl
        self.external_setup()
        with (self.request_dir/'step3_monitor.request.worker.lock').open('a+') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises((RuntimeError,BlockingIOError)): self.invoke(True)
        self.assertEqual(self.calls, [])


if __name__=='__main__':unittest.main()
