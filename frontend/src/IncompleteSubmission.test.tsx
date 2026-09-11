import '@testing-library/jest-dom/vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import App from './App';

afterEach(() => {cleanup();vi.unstubAllGlobals();window.history.pushState({},'', '/');});
function fixture() {
  let phase='config_review';let unavailable=false;let posts=0;
  const json=(value:unknown)=>Promise.resolve(new Response(JSON.stringify(value),{status:200,headers:{'Content-Type':'application/json'}}));
  vi.stubGlobal('fetch',vi.fn((input:RequestInfo|URL,init?:RequestInit)=>{
    const u=new URL(String(input),'http://localhost');const p=u.pathname;
    if(init?.method==='POST'){
      posts++;
      if(new Headers(init.headers).get('Content-Type')!=='application/json')return Promise.resolve(new Response(JSON.stringify({detail:'JSON body required'}),{status:422}));
      phase='cancelled';return json({status:'cancelled'});
    }
    if(p.endsWith('/submission-cancel-preview'))return json({analysis_id:'SAVED',attempt:1,effects:['保留样本表，不修改 pending。']});
    if(p==='/api/auth/me')return json({username:'operator',role:'operator'});
    if(p==='/api/platform/capabilities')return json({environment:'test',deployed_pipelines:['wgs'],pipelines:[{id:'wgs',display_name:'WGS',dag_id:'bio_wgs',enabled:true,submit_enabled:true,capabilities:['submit'],execution_targets:['cce']}]});
    if(p==='/api/wgs/release')return json({source_commit:'mock',version:'4.2.0',execution_enabled:true,runtime_adapter_enabled:true});
    if(p==='/api/wgs/projects')return json({items:[]});
    if(p==='/api/runs'){
      if(unavailable)return Promise.resolve(new Response('{}',{status:503}));
      return json({items:u.searchParams.get('status')==='running'?['SAVED','AUTO','APPROVED'].map(id=>({analysis_id:id,pipeline:'wgs',status:'running'})):[],total:u.searchParams.get('status')==='running'?3:0});
    }
    if(/^\/api\/runs\/(SAVED|AUTO|APPROVED)$/.test(p)){
      const id=p.split('/').pop();return json({analysis_id:id,pipeline:'wgs',attempt:1,status:'running',created_at:'2026-09-11T01:00:00Z',params:{sequencing_batch:id==='SAVED'?'MOCK_BATCH':id,submission_phase:id==='APPROVED'?'approved':phase,submission_mode:id==='AUTO'?'auto_dispatch':'manual'}});
    }
    if(p==='/api/dashboard/overview')return json({pipeline:'wgs',attention_items:[],totals:{},sample_summary:{total:0,running:0,workflow_failed:0,qc_failed:0,completed:0}});
    return json({items:[],total:0});
  }));
  return {phase:(next:string)=>{phase=next;},fail:()=>{unavailable=true;},posts:()=>posts};
}

it('finds the server saved submission from plain Submit Run and continues without creating another run',async()=>{
  window.history.pushState({},'','/submit');const f=fixture();render(<App/>);
  const link=await screen.findByRole('link',{name:/MOCK_BATCH.*继续提交/});
  expect(link).toHaveAttribute('href','/submit?pipeline=wgs&analysis_id=SAVED');
  expect(screen.queryByRole('link',{name:/AUTO.*继续提交/})).not.toBeInTheDocument();
  expect(screen.queryByRole('link',{name:/APPROVED.*继续提交/})).not.toBeInTheDocument();
  fireEvent.click(link);
  expect(await screen.findByRole('button',{name:'Confirm configuration'})).toBeInTheDocument();
  expect(f.posts()).toBe(0);
  cleanup();window.history.pushState({},'','/submit');render(<App/>);
  expect(await screen.findByRole('link',{name:/MOCK_BATCH.*继续提交/})).toBeInTheDocument();
});

it('offers cancellation outside the resume link and requires an explicit confirmation',async()=>{
  window.history.pushState({},'','/submit');const f=fixture();render(<App/>);
  const button=await screen.findByRole('button',{name:'取消提交'});
  expect(button.closest('a')).toBeNull();
  fireEvent.click(button);
  expect(await screen.findByRole('dialog',{name:'取消提交确认'})).toBeInTheDocument();
  expect(f.posts()).toBe(0);
  await waitFor(()=>expect(screen.getByRole('button',{name:'返回'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'返回'}));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(f.posts()).toBe(0);
});

it('cancels the original attempt only after confirmation and removes the card',async()=>{
  window.history.pushState({},'','/submit');const f=fixture();render(<App/>);
  fireEvent.click(await screen.findByRole('button',{name:'取消提交'}));
  const confirm=await screen.findByRole('button',{name:'确认取消提交'});
  await waitFor(()=>expect(confirm).toBeEnabled());expect(f.posts()).toBe(0);
  fireEvent.click(confirm);
  await waitFor(()=>expect(screen.queryByRole('link',{name:/MOCK_BATCH.*继续提交/})).not.toBeInTheDocument());
  expect(f.posts()).toBe(1);
  const calls=vi.mocked(fetch).mock.calls.filter(([,init])=>init?.method==='POST');
  expect(String(calls[0][0])).toContain('/runs/SAVED/actions/cancel-submission');
  expect(JSON.parse(String(calls[0][1]?.body))).toEqual({attempt:1});
});

it('does not offer pre-configuration cancellation after configuration approval',async()=>{
  window.history.pushState({},'','/submit');const f=fixture();f.phase('execution_review');render(<App/>);
  await screen.findByRole('link',{name:/MOCK_BATCH.*继续提交/});
  expect(screen.queryByRole('button',{name:'取消提交'})).not.toBeInTheDocument();
});

it('shows a clickable incomplete submission in Attention required and removes it after approval',async()=>{
  const f=fixture();render(<App/>);
  const link=await screen.findByRole('link',{name:/MOCK_BATCH.*继续提交/});
  expect(link.closest('.attention-card')).not.toBeNull();
  expect(screen.getByLabelText('1 attention items')).toBeInTheDocument();
  f.phase('approved');fireEvent.focus(window);
  await waitFor(()=>expect(screen.queryByRole('link',{name:/MOCK_BATCH.*继续提交/})).not.toBeInTheDocument());
  expect(f.posts()).toBe(0);
});

it('keeps the saved submission visible during a failed background refresh',async()=>{
  window.history.pushState({},'','/submit');const f=fixture();render(<App/>);
  const link=await screen.findByRole('link',{name:/MOCK_BATCH.*继续提交/});
  f.fail();fireEvent.focus(window);
  expect(await screen.findByText(/未完成提交刷新失败/)).toBeInTheDocument();
  expect(screen.getByRole('link',{name:/MOCK_BATCH.*继续提交/})).toBe(link);
});
