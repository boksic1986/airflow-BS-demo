import '@testing-library/jest-dom/vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, expect, it, vi} from 'vitest';
import App from './App';

it('ignores a delayed preview after edits and resets stale release options from the contract', async()=>{
  window.history.pushState({},'','/submit');
  sessionStorage.setItem('submission-v1:tester:wgs:options-release',JSON.stringify('old-release'));
  sessionStorage.setItem('submission-v1:tester:wgs:algo',JSON.stringify('DNAscope'));
  sessionStorage.setItem('submission-v1:tester:wgs:reference',JSON.stringify('all'));
  let resolvePreview:(value:Response)=>void=()=>{};
  const posts:Record<string,unknown>[]=[];
  vi.stubGlobal('fetch',vi.fn((input:RequestInfo|URL,init?:RequestInit)=>{
    const url=String(input);
    if(url.endsWith('/preview')) {posts.push(JSON.parse(String(init?.body)));return new Promise<Response>(resolve=>{resolvePreview=resolve;});}
    const data=url.endsWith('/auth/me')?{username:'tester',role:'operator'}
      :url.endsWith('/platform/capabilities')?{environment:'test',deployed_pipelines:['wgs'],pipelines:[{id:'wgs',display_name:'WGS',dag_id:'bio_wgs',enabled:true,submit_enabled:true,capabilities:['submit'],execution_targets:['cce']}]}
      :url.endsWith('/wgs/release')?{release_id:'new-release',source_commit:'cc9bde3',execution_enabled:true,runtime_adapter_enabled:true,test_project_enabled:true,submission_options:{defaults:{algo:'Haplotyper',use_reference:'ref'},callers:[{value:'DNAscope',label:'DNAscope'},{value:'Haplotyper',label:'Haplotyper'}],reference_values:['all','ref','no']}}
      :{items:[],total:0};
    return Promise.resolve(new Response(JSON.stringify(data),{status:200}));
  }));
  render(<App/>);
  fireEvent.change(await screen.findByLabelText('Input mode'),{target:{value:'test'}});
  expect(screen.getByLabelText('Variant caller')).toHaveValue('Haplotyper');
  expect(screen.getByLabelText('Use reference')).toHaveValue('ref');
  fireEvent.change(screen.getByLabelText('Existing WGS project'),{target:{value:'/source-A'}});
  fireEvent.change(screen.getByLabelText('New relative output directory'),{target:{value:'test-A'}});
  fireEvent.click(screen.getByRole('button',{name:'Preview exact test project'}));
  await waitFor(()=>expect(posts).toHaveLength(1));
  fireEvent.change(screen.getByLabelText('Existing WGS project'),{target:{value:'/source-B'}});
  fireEvent.change(screen.getByLabelText('Variant caller'),{target:{value:'DNAscope'}});
  resolvePreview(new Response(JSON.stringify({draft_id:'stale',source_project_dir:'/source-A',preview_hash:'a',samples:[],sample_count:0,fastq_file_count:0,algo:'Haplotyper',use_reference:'ref'}),{status:200}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Preview exact test project'})).not.toBeDisabled());
  expect(screen.queryByRole('button',{name:'Confirm test source and prepare'})).not.toBeInTheDocument();
  expect(screen.getByLabelText('Existing WGS project')).toHaveValue('/source-B');
});

afterEach(() => {cleanup(); vi.unstubAllGlobals(); sessionStorage.clear();});
it('recovers separate WGS and GATK inputs while switching pipeline', async () => {
  window.history.pushState({}, '', '/submit');
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    const data = url.endsWith('/auth/me') ? {username:'tester',role:'operator'}
      : url.endsWith('/platform/capabilities') ? {environment:'test',deployed_pipelines:['wgs','gatk'],pipelines:['wgs','gatk'].map(id=>({id,display_name:id.toUpperCase(),dag_id:`bio_${id}`,enabled:true,submit_enabled:true,capabilities:['submit'],execution_targets:['cce']}))}
      : url.endsWith('/wgs/release') ? {source_commit:'cc9bde3',execution_enabled:true,runtime_adapter_enabled:true,submission_options:{defaults:{algo:'DNAscope',use_reference:'all'},callers:[{value:'DNAscope',label:'Sentieon DNAscope'},{value:'Haplotyper',label:'Sentieon Haplotyper'}],reference_values:['all','ref','no']}}
      : url.endsWith('/wgs/projects') ? {items:[{project_id:'WGS_Clinical',display_name:'WGS',platforms:[{platform_id:'T7',display_name:'T7'}],fastq_roots:[{root_id:'T7_Fastq',display_name:'T7'}]}]}
      : {items:[],total:0};
    return Promise.resolve(new Response(JSON.stringify(data),{status:200}));
  }));
  render(<App/>);
  fireEvent.change(await screen.findByLabelText('Batch'),{target:{value:'20260912A'}});
  fireEvent.click(screen.getByRole('tab',{name:'GATK'}));
  fireEvent.change(await screen.findByLabelText('WES project directory'),{target:{value:'/synthetic/WES'}});
  fireEvent.click(screen.getByRole('tab',{name:'WGS'}));
  expect(await screen.findByLabelText('Batch')).toHaveValue('20260912A');
  expect(await screen.findByLabelText('Variant caller')).toHaveValue('DNAscope');
  fireEvent.click(screen.getByRole('tab',{name:'GATK'}));
  expect(await screen.findByLabelText('WES project directory')).toHaveValue('/synthetic/WES');
});

it('previews exact test input, invalidates changed options, then confirms a server draft',async()=>{
  window.history.pushState({},'','/submit');
  const posts:{url:string;body:Record<string,unknown>}[]=[];
  const draft={draft_id:'wgs-test-synthetic',preview_hash:'a'.repeat(64),samples:['SYNTH1'],batch:'20260912A',output_child:'independent',sample_count:1,fastq_file_count:2,algo:'Haplotyper',use_reference:'all',release_id:'wgs-4.2.1-cc9bde3',write_check:'Node checks writes',expires_at:'2099-01-01'};
  const detail={analysis_id:'WGS_SYNTHETIC',pipeline:'wgs',attempt:1,status:'running',params:{submission_phase:'preparing_sampleinfo'}};
  vi.stubGlobal('fetch',vi.fn((input:RequestInfo|URL,init?:RequestInit)=>{
    const url=String(input);
    if(init?.method==='POST')posts.push({url,body:JSON.parse(String(init.body))});
    const data=url.endsWith('/auth/me')?{username:'tester',role:'operator'}
      :url.endsWith('/platform/capabilities')?{environment:'BS10610-Test',deployed_pipelines:['wgs'],pipelines:[{id:'wgs',display_name:'WGS',dag_id:'bio_wgs',enabled:true,submit_enabled:true,capabilities:['submit'],execution_targets:['cce']}]}
      :url.endsWith('/wgs/release')?{source_commit:'cc9bde3',execution_enabled:true,runtime_adapter_enabled:true,test_project_enabled:true,submission_options:{defaults:{algo:'DNAscope',use_reference:'all'},callers:[{value:'DNAscope',label:'Sentieon DNAscope'},{value:'Haplotyper',label:'Sentieon Haplotyper'}],reference_values:['all','ref','no']}}
      :url.endsWith('/preview')?draft:url.endsWith('/confirm')||url.endsWith('/runs/WGS_SYNTHETIC')?detail:{items:[],total:0};
    return Promise.resolve(new Response(JSON.stringify(data),{status:200}));
  }));
  render(<App/>);
  fireEvent.change(await screen.findByLabelText('Input mode'),{target:{value:'test'}});
  fireEvent.change(screen.getByLabelText('Existing WGS project'),{target:{value:'/sg2/50.ctapa/project/HWcloud/WGS_test/source'}});
  fireEvent.change(screen.getByLabelText('New relative output directory'),{target:{value:'independent'}});
  fireEvent.click(screen.getByRole('button',{name:'Preview exact test project'}));
  expect(await screen.findByRole('heading',{name:'Review frozen source scope'})).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Variant caller'),{target:{value:'Haplotyper'}});
  expect(screen.queryByRole('button',{name:'Confirm test source and prepare'})).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Preview exact test project'}));
  fireEvent.click(await screen.findByRole('button',{name:'Confirm test source and prepare'}));
  await waitFor(()=>expect(window.location.search).toContain('analysis_id=WGS_SYNTHETIC'));
  expect(posts[1].body.algo).toBe('Haplotyper');
  expect(posts.filter(item=>item.url.endsWith('/confirm'))).toHaveLength(1);
  expect(posts[2].body).toEqual({preview_hash:'a'.repeat(64)});
});
