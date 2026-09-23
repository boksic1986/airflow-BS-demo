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
        self.assertEqual(requests[0],['kubectl','get','pods','-l','job-name=master-mock','--chunk-size=0','-o','json'])

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

    def test_paginated_empty_master_pods_do_not_authorize_replacement(self):
        response=b'{"kind":"PodList","metadata":{"continue":"next-page"},"items":[]}'
        with patch.object(self.module.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=response)):
            with self.assertRaises(RuntimeError):self.invoke()
        self.assertEqual(self.calls,[])

    def test_reclaimed_historical_worker_without_terminal_evidence_blocks_resume(self):
        archive=self.request_dir/'resume-old-uid-jobs.ndjson'
        archive.write_text('{"external_jobid":"historical-worker"}\n')
        self.runtime._parse_jobs_ndjson=lambda text,**kw:[json.loads(text)]
        self.runtime._query_worker_states=lambda cfg,records:[{'state':'NOT_FOUND'}]
        with self.assertRaises(RuntimeError):self.invoke(True)
        self.assertEqual(self.calls,[])

    def test_lost_create_then_absent_master_never_posts_a_second_create(self):
        def uncertain_create(*args):
            self.calls.append('step2')
            raise self.module.subprocess.TimeoutExpired('synthetic-create',1)
        self.runtime.step2=uncertain_create
        with patch.object(self.module.subprocess,'run',side_effect=self.delete):
            with self.assertRaises(self.module.subprocess.TimeoutExpired):self.invoke(True)
            with self.assertRaises(RuntimeError):self.invoke(True)
        self.assertEqual(self.calls.count('step2'),1)

    def v2_master(self):
        annotations={'cce-pipeline/handoff-version':'2'}
        self.manifest['metadata']['annotations']=annotations
        self.job['metadata']['annotations']=annotations.copy()
        (self.bundle/'master-job.yaml').write_text(yaml.safe_dump(self.manifest))
        self.runtime._finish_master_handoff=lambda *a:self.calls.append('confirmed')

    def test_v2_active_master_reconciles_confirmation_without_replacement(self):
        self.v2_master()
        self.job['status']={'active':1}
        self.assertEqual(self.invoke(True)['status'],'reused')
        self.assertEqual(self.calls,['claim','confirmed'])

    def test_v2_prestart_master_checks_ownership_before_sending_start(self):
        self.v2_master()
        self.job['status']={'active':1}
        def denied(*a):
            raise RuntimeError('another owner')
        self.runtime._claim_batch_lock=denied
        with self.assertRaises(RuntimeError):self.invoke(True)
        self.assertEqual(self.calls,[])

    def test_v2_failed_master_requires_new_generation_view_before_delete(self):
        self.v2_master()
        with patch.object(self.module.subprocess,'run',side_effect=self.delete):
            with self.assertRaisesRegex(RuntimeError,'recovery view'):
                self.invoke(True)
        self.assertEqual(self.calls,[])
        self.assertFalse((self.request_dir/'resume-old-uid.json').exists())

    def test_v2_complete_master_requires_native_success_before_resume_advances(self):
        self.v2_master()
        self.job['status']={'conditions':[{'type':'Complete','status':'True'}]}
        self.runtime._recovery_native_success=lambda *a:{'state':'SUCCEEDED','job_uid':'old-uid'}
        self.assertEqual(self.invoke(True)['status'],'succeeded')
        self.assertEqual(self.calls,[])
        self.runtime._recovery_native_success=lambda *a:(_ for _ in ()).throw(RuntimeError('unverified'))
        with self.assertRaises(RuntimeError):self.invoke(True)
        self.assertEqual(self.calls,[])

    def test_v2_success_with_active_or_deleting_master_never_advances(self):
        self.v2_master()
        self.runtime._recovery_native_success=lambda *a:{'state':'SUCCEEDED','job_uid':'old-uid'}
        for change in ('active','deleting'):
            with self.subTest(change=change):
                self.job['status']={'conditions':[{'type':'Complete','status':'True'}]}
                if change=='active':self.job['status']['active']=1
                else:self.job['metadata']['deletionTimestamp']='synthetic'
                with self.assertRaises(RuntimeError):self.invoke(True)
                self.assertEqual(self.calls,[])

    def test_v2_completed_journal_does_not_bypass_new_uid_confirmation(self):
        self.v2_master()
        self.job['metadata']['uid']='new-uid'
        value={'analysis_id':self.aid,'attempt':1,'run_id':self.aid+'-a1',
               'expected_job_uid':'old-uid','binding_sha256':self.params['expected_binding_sha256'],
               'contract_sha256':self.params['expected_contract_sha256'],
               'manifest_sha256':hashlib.sha256((self.bundle/'master-job.yaml').read_bytes()).hexdigest(),
               'status':'completed','replacement_job_uid':'new-uid'}
        (self.request_dir/'resume-old-uid.json').write_text(json.dumps(value))
        with self.assertRaises(RuntimeError):self.invoke(True)
        self.assertEqual(self.calls,[])


if __name__=='__main__':unittest.main()
