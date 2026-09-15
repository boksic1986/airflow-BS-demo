import {useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode} from "react";
import {Link, useSearchParams} from "react-router-dom";
import {approveWgsConfig, createCatalogWgsRun, createRun, getGatkRelease, getRunDetail, getRunSamples, getWgsProjects, getWgsRelease, previewGatkSubmission, startWgsExecution, updateWgsExecutionChoice, type GatkRelease, type GatkSubmissionPreview, type PipelineCapability, type RunDetail, type Sample, type WgsExecutionChoiceRequest, type WgsProjectCatalog, type WgsRelease} from "../api";
import {ExecutionTargetSelector} from "../features/wgs/ExecutionTargetSelector";
import {StatusBadge} from "../components/StatusBadge";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {hasRegisteredSubmissionUi} from "../features/platform/submissionUiRegistry";
import {errorMessage} from "../lib/errors";
import {useSilentRefresh} from "../lib/useSilentRefresh";
import {getWgsSubmissionSnapshot} from "../api";
import {IncompleteSubmissionsPanel} from "../features/wgs/IncompleteSubmissions";
import {CancelSubmission} from "../features/wgs/CancelSubmission";
import {useSubmissionDraft} from "../features/platform/useSubmissionDraft";
import {previewWgsTestProject, confirmWgsTestProject, type WgsTestPreview} from '../api';

export function SubmitPage() {
  const capabilities = usePlatformCapabilities();
  const [searchParams, setSearchParams] = useSearchParams();
  const available = capabilities.pipelines.filter((pipeline) => (
    hasRegisteredSubmissionUi(pipeline, capabilities.isDeployed)
  ));
  const requested = searchParams.get("pipeline");
  const selected = available.find((pipeline) => pipeline.id === requested) || available[0];
  if (capabilities.loading) {
    return <div className="page-stack"><section className="panel"><p>Loading submission capabilities...</p></section></div>;
  }
  if (!selected) {
    return <div className="page-stack"><section className="panel"><h1>Submission unavailable</h1><p>No deployed pipeline has a registered submission interface.</p></section></div>;
  }
  const pipelineSelector = <SubmissionPipelineField
    pipelines={available}
    selectedId={selected.id}
    onChange={(pipelineId) => setSearchParams({pipeline: pipelineId})}
  />;
  return <div className="submission-layout">{pipelineSelector}<div className="submission-main">{selected.id === "gatk"
    ? <GatkSubmitForm pipelineSelector={null} />
    : <WgsSubmitForm pipelineSelector={null} />}</div></div>;
}

function SubmissionPipelineField({pipelines, selectedId, onChange}: {pipelines: PipelineCapability[]; selectedId: string; onChange: (pipelineId: string) => void}) {
  return <aside className="pipeline-rail submission-pipeline-field" role="tablist" aria-orientation="vertical" aria-label="Submission pipeline">{pipelines.map((pipeline) => <button aria-label={pipeline.display_name} className={pipeline.id === selectedId ? "active" : ""} type="button" role="tab" aria-selected={pipeline.id === selectedId} key={pipeline.id} onClick={() => onChange(pipeline.id)}><strong>{pipeline.display_name}</strong><span>{pipeline.dag_id}</span></button>)}</aside>;
}

function WgsSubmitForm({pipelineSelector}: {pipelineSelector: ReactNode}) {
  const capabilities = usePlatformCapabilities();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedRun = searchParams.get("analysis_id");
  const [release, setRelease] = useState<WgsRelease | null>(null);
  const [catalog, setCatalog] = useState<WgsProjectCatalog | null>(null);
  const [projectId, setProjectId] = useSubmissionDraft("wgs", "project", "WGS_Clinical");
  const [platform, setPlatform] = useSubmissionDraft("wgs", "platform", "T7");
  const [batch, setBatch] = useSubmissionDraft("wgs", "batch", "");
  const [fastqRootId, setFastqRootId] = useSubmissionDraft("wgs", "fastq", "T7_Fastq");
  const [useReference, setUseReference] = useSubmissionDraft("wgs", "reference", "");
  const [algo, setAlgo] = useSubmissionDraft("wgs", "algo", "");
  const [optionsRelease, setOptionsRelease] = useSubmissionDraft('wgs','options-release','');
  const [testSource, setTestSource] = useSubmissionDraft('wgs','test-source','');
  const [testChild, setTestChild] = useSubmissionDraft('wgs','test-child','');
  const [inputMode, setInputMode] = useSubmissionDraft('wgs','input-mode','catalog');
  const [testPreview, setTestPreview] = useState<WgsTestPreview | null>(null);
  const previewInputs=JSON.stringify([inputMode,testSource,testChild,algo,useReference,release?.release_id]);
  const currentPreviewInputs=useRef(previewInputs);
  currentPreviewInputs.current=previewInputs;
  const acceptedPreviewInputs=useRef<string|null>(null);
  const previewGeneration=useRef(0);
  useEffect(()=>()=>{previewGeneration.current+=1;},[]);
  useEffect(()=>{
    const contract=release?.submission_options;
    if (!release || requestedRun) return;
    const identity=release.release_id || release.source_commit;
    const valid=contract?.defaults && contract.callers.some(item=>item.value===contract.defaults?.algo) && contract.reference_values.includes(contract.defaults.use_reference);
    if(!valid){setAlgo('');setUseReference('');return;}
    if(optionsRelease!==identity || !contract.callers.some(item=>item.value===algo) || !contract.reference_values.includes(useReference)){
      setAlgo(contract.defaults!.algo);setUseReference(contract.defaults!.use_reference);setOptionsRelease(identity);
      setTestPreview(null);
    }
  },[release,requestedRun,optionsRelease,algo,useReference]);
  useEffect(()=>{if(release && !release.test_project_enabled && inputMode!=='catalog')setInputMode('catalog');},[release,inputMode,setInputMode]);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [created, setCreated] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [restoring, setRestoring] = useState(Boolean(requestedRun));
  useEffect(() => {
    if (!requestedRun) { setCreated(null); setSamples([]); setRestoring(false); return; }
    setRestoring(true); setError(null);
    setCreated((current) => current?.analysis_id === requestedRun ? current : null);
    setSamples([]);
  }, [requestedRun]);
  const wgsDefinition = capabilities.pipelines.find((item) => (
    item.id === "wgs" && capabilities.isDeployed(item.id)
  ));
  const wgsSubmissionAvailable = Boolean(
    wgsDefinition?.enabled
    && wgsDefinition.submit_enabled
    && wgsDefinition.capabilities.includes("submit")
  );
  useEffect(() => {
    if (capabilities.loading || !wgsSubmissionAvailable) return;
    Promise.all([getWgsRelease(), getWgsProjects()])
      .then(([nextRelease, nextCatalog]) => { setRelease(nextRelease); setCatalog(nextCatalog); })
      .catch((loadError) => setError(errorMessage(loadError)));
  }, [capabilities.loading, wgsSubmissionAvailable]);
  const project = useMemo(() => catalog?.items.find((item) => item.project_id === projectId) || catalog?.items[0], [catalog, projectId]);
  const executionEnabled = Boolean(release?.execution_enabled && release.runtime_adapter_enabled);
  const phase = String(created?.params?.submission_phase || "select");
  const currentStep = restoring || (requestedRun && !created) || ['cancelled', 'cancelling_submission'].includes(phase)
    ? 0 : ['config_review', 'preparing_analysis'].includes(phase) ? 2
    : ['execution_review', 'approved'].includes(phase) ? 3 : 1;
  const frozenParameters = created?.params?.submission_options ? <section className="panel"><h3>Frozen analysis parameters</h3><p>Caller: Sentieon {String(created.params.algo)} · Reference: {String(created.params.use_reference)} · Release: {String(created.params.pipeline_release_id)}</p><p>These options were fixed at the first confirmation. The following review cannot change them.</p>{created.params.test_project ? <p>Frozen release configuration: {JSON.stringify((created.params.test_project as Record<string,unknown>).effective_config)}</p> : null}</section> : null;
  const preparationFailed = Boolean(created && ["failed", "unknown_interrupted"].includes(created.status));
  const refreshId = requestedRun || created?.analysis_id;
  const refreshEnabled = Boolean(refreshId && !submitting && (!created || created.analysis_id !== refreshId ||
    (!preparationFailed && !["success", "failed", "cancelled", "canceled"].includes(created.status) && phase !== "approved")));
  const preparationRefresh = useSilentRefresh(async ({isCurrent}) => {
    if (!refreshId) return;
    try {
      const {detail, items} = await getWgsSubmissionSnapshot(refreshId);
      if (!isCurrent()) return;
      setCreated(detail); setSamples(items);
      const reference = detail.params?.use_reference;
      // Restore saved choices once; background status refresh must not overwrite
      // an operator's unconfirmed selection in configuration review.
      if ((!created || created.analysis_id !== detail.analysis_id) &&
        (reference === "all" || reference === "ref" || reference === "no")) setUseReference(reference);
    } finally {
      if (isCurrent()) setRestoring(false);
    }
  }, `${refreshId || "none"}:${created?.attempt || 0}:${phase}`, refreshEnabled,
  ["select", "preparing_sampleinfo", "preparing_analysis"].includes(phase) ? 2000 : 10000);
  async function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setError(null);
    try {
      if (inputMode==='test' && release?.test_project_enabled) {
        const generation=++previewGeneration.current;
        const snapshot=previewInputs;
        const result=await previewWgsTestProject({source_project_dir:testSource,output_child:testChild,algo,use_reference:useReference});
        if(generation===previewGeneration.current && currentPreviewInputs.current===snapshot){acceptedPreviewInputs.current=snapshot;setTestPreview(result);}
        return;
      }
      const detail = await createCatalogWgsRun({project_id: projectId, platform, batch, fastq_root_id: fastqRootId, ...(release?.config_options_enabled && release.submission_options?.defaults && algo && ['all','ref','no'].includes(useReference) ? {algo, use_reference: useReference as 'all'|'ref'|'no'} : {})});
      setCreated(detail);
      setSearchParams({pipeline: "wgs", analysis_id: detail.analysis_id}, {replace: true});
    }
    catch (submitError) { setError(errorMessage(submitError)); }
    finally { setSubmitting(false); }
  }
  async function confirmTestSource() {
    if (!testPreview || acceptedPreviewInputs.current!==currentPreviewInputs.current) return;
    setSubmitting(true);setError(null);
    try {
      const detail=await confirmWgsTestProject(testPreview);
      setCreated(detail);setSearchParams({pipeline:'wgs',analysis_id:detail.analysis_id},{replace:true});
    } catch (failure) {setError(errorMessage(failure));} finally {setSubmitting(false);}
  }
  async function confirmConfiguration() {
    if (!created) return;
    setSubmitting(true); setError(null);
    try {
      if(!['all','ref','no'].includes(useReference))throw new Error('No audited or frozen reference selection is available');
      await approveWgsConfig(created.analysis_id, {use_reference: useReference as 'all'|'ref'|'no', resource_set: "default"});
      setCreated({...created, params: {...created.params, submission_phase: "preparing_analysis", use_reference: useReference, resource_set: "default"}});
    } catch (submitError) { setError(errorMessage(submitError)); }
    finally { setSubmitting(false); }
  }
  async function startExecution() {
    if (!created) return;
    setSubmitting(true); setError(null);
    try {
      await startWgsExecution(created.analysis_id);
      setCreated({...created, params: {...created.params, submission_phase: "approved"}});
    } catch (submitError) { setError(errorMessage(submitError)); }
    finally { setSubmitting(false); }
  }
  async function switchExecutionTarget(payload: WgsExecutionChoiceRequest) {
    if (!created) return;
    await updateWgsExecutionChoice(created.analysis_id, payload);
    setCreated(await getRunDetail(created.analysis_id));
  }
  if (!wgsSubmissionAvailable) {
    return <div className="page-stack"><section className="panel"><h1>Submission unavailable</h1><p>No deployed pipeline has a registered submission interface.</p></section></div>;
  }
  return <div className="page-stack submit-wizard">
    {!requestedRun ? <IncompleteSubmissionsPanel /> : null}
    <section className="page-header"><div><p className="eyebrow">WGS production</p><h1>Submit run</h1><p>Submit one catalog-controlled WGS batch. The DAG runs native WGS sampleinfo and analysis preparation, then Step1-Step6.</p></div>{created?<CancelSubmission key={`${created.analysis_id}-${created.attempt}`} run={created} onCancelled={()=>setCreated({...created,status:"cancelled",params:{...created.params,submission_phase:"cancelled"}})} />:null}</section>
    <section className="panel"><div className="definition-grid"><div><dt>Current WGS release</dt><dd>{release ? `WGS ${release.version} / ${release.source_commit.slice(0, 7)}` : "Loading release..."}</dd></div><div><dt>Release ID</dt><dd>{release?.release_id || "-"}</dd></div><div><dt>CCE profile</dt><dd>{release?.profile_id ? `${release.profile_id}/${release.profile_revision || "-"}` : "-"}</dd></div><div><dt>cce-pipeline</dt><dd>{release?.cce_pipeline_version || "-"}</dd></div><div><dt>Execution</dt><dd>{executionEnabled ? "Enabled" : "Disabled"}</dd></div></div></section>
    {phase === "cancelled" ? <section className="panel" role="status"><h2>提交已取消</h2><p>样本表和回执已保留作审计；未修改 pending 或删除分析数据。</p></section> : null}
    {phase === "cancelling_submission" ? <section className="panel" role="status"><h2>取消尚未确认</h2><p>已禁止继续确认配置。请使用右上角“重试取消提交”完成停止确认。</p></section> : null}
    {requestedRun ? <section className="panel"><Link to={`/runs/${requestedRun}`}>View existing run</Link>{restoring ? <p>Restoring submission...</p> : null}{!restoring && !created ? <p>The existing run could not be loaded. Refresh to retry; no new run has been submitted.</p> : null}</section> : null}
    <ol className="wizard-steps" aria-label="WGS 提交步骤">
    <SubmissionStep number={1} current={currentStep} title="选择批次与参数" description="选择输入来源和批次，生成样本预览；此时不会启动云上分析。" summary={created ? `已保存提交 · ${String(created.params?.sequencing_batch || created.params?.batch || created.analysis_id)}` : undefined}>
    {!created && !requestedRun ? <section className="panel"><form className="form-grid wgs-grouped-form" onSubmit={prepare}>
      {pipelineSelector}
      <fieldset><legend>Input and project</legend>
      {release?.test_project_enabled ? <label className="field"><span>Input mode</span><select aria-label="Input mode" value={inputMode} onChange={event=>{setInputMode(event.target.value);setTestPreview(null);}}><option value="catalog">Catalog batch</option><option value="test">Existing project → independent test project</option></select></label> : null}
      {inputMode==='test' && release?.test_project_enabled ? <>
      <label className="field"><span>Existing WGS project</span><input aria-label="Existing WGS project" value={testSource} onChange={event=>{setTestSource(event.target.value);setTestPreview(null);}} /></label>
      <label className="field"><span>New relative output directory</span><input aria-label="New relative output directory" value={testChild} onChange={event=>{setTestChild(event.target.value);setTestPreview(null);}} /></label>
      <p className="field-help">Test only: /sg2/50.ctapa/project/HWcloud/WGS_test. Source sampleinfo.tsv/config.yaml and exact raw FASTQ pairs are frozen; existing results and formal pending are never copied.</p>
      </> : <>
      <label className="field"><span>Project</span><select aria-label="Project" value={projectId} onChange={(event) => setProjectId(event.target.value)}>{catalog?.items.map((item) => <option value={item.project_id} key={item.project_id}>{item.display_name}</option>)}</select></label>
      <label className="field"><span>Platform</span><select aria-label="Platform" value={platform} onChange={(event) => setPlatform(event.target.value)}>{project?.platforms.map((item) => <option value={item.platform_id} key={item.platform_id}>{item.display_name.replace(/\s*\/\s*WGS\s+V?\d+(?:\.\d+)+(?:[-\w.]*)?\s*$/i, '')}</option>)}</select><small className="field-help">流程版本见上方 Current WGS release；平台仅表示测序平台与参考组。</small></label>
      <label className="field"><span>Batch</span><input aria-label="Batch" placeholder="20260901B" value={batch} onChange={(event) => setBatch(event.target.value)} /></label>
      <label className="field"><span>FASTQ root</span><select aria-label="FASTQ root" value={fastqRootId} onChange={(event) => setFastqRootId(event.target.value)}>{project?.fastq_roots.map((item) => <option value={item.root_id} key={item.root_id}>{item.display_name}</option>)}</select></label>
      </>}
      </fieldset><fieldset disabled={inputMode==='catalog' && !release?.config_options_enabled}><legend>Analysis parameters</legend>
      {inputMode==='catalog' && !release?.config_options_enabled ? <p role="note">Configuration options are not activated. The values below describe the audited release only; legacy runtime defaults will be used, without explicit overrides.</p> : null}
      <label className="field"><span>Variant caller</span><select aria-label="Variant caller" value={algo} onChange={event=>{setAlgo(event.target.value);setTestPreview(null);}} disabled={!release?.submission_options?.defaults}><option value="" disabled>Release defaults unavailable</option>{release?.submission_options?.defaults && release.submission_options.callers.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
      <label className="field"><span>Reference selection</span><select aria-label="Use reference" value={useReference} disabled={!release?.submission_options?.defaults} onChange={event=>{setUseReference(event.target.value);setTestPreview(null);}}><option value="" disabled>Release defaults unavailable</option>{release?.submission_options?.defaults && release.submission_options.reference_values.map(value=><option key={value} value={value}>{value}</option>)}</select></label>
      <p className="field-help">Genome: {release?.submission_options?.reference_genome || 'Release default'}. {release?.submission_options?.cnv || 'CNV configuration is fixed by the release.'}</p>
      {!release?.submission_options?.callers.length ? <p className="field-help">Caller options unavailable for this release; legacy release defaults apply.</p> : null}
      </fieldset>
      <p className="field-help">WGS first generates sampleinfo. Analysis and cloud execution start only after the following confirmations.</p>
      <button className="button primary" type="submit" disabled={!executionEnabled || (inputMode==='test' ? !testSource || !testChild : !projectId || !platform || !batch || !fastqRootId) || submitting}>{submitting ? "Preparing..." : inputMode==='test' ? 'Preview exact test project' : "Prepare sample information"}</button>
      {!executionEnabled ? <p className="inline-error" role="note">Execution is disabled. No AnalysisRun, OBS transfer or CCE task can start.</p> : null}
    </form></section> : null}
    {!created && testPreview && inputMode==='test' && acceptedPreviewInputs.current===previewInputs ? <section className="panel"><h2>Review frozen source scope</h2><p>Source: {testPreview.source_project_dir}</p><p>{testPreview.sample_count} samples · {testPreview.fastq_file_count} FASTQ files · {testPreview.release_id} · Sentieon {testPreview.algo} · Reference {testPreview.use_reference}</p><p>Output: {testPreview.output_child}. {testPreview.write_check}</p><p>Frozen release configuration: {JSON.stringify(testPreview.effective_config)}</p><p>{testPreview.samples.join(', ')}</p><button type="button" className="button primary" disabled={submitting} onClick={()=>void confirmTestSource()}>Confirm test source and prepare</button></section> : null}
    {created && !preparationFailed && phase === "preparing_sampleinfo" ? <section className="panel"><h2>Preparing sample information</h2><p>The WGS sampleinfo task is running. This page refreshes automatically.</p></section> : null}
    </SubmissionStep>
    <SubmissionStep number={2} current={currentStep} title="复核样本与配置" description="核对样本范围及最终配置，确认后准备分析目录。" summary="配置已确认；已冻结的提交不会在此重复创建。">
    {frozenParameters}
    {created && phase === "config_review" ? <section className="panel"><h3>Review samples and configuration</h3><SamplePreview samples={samples} /><div className="form-grid"><label className="field"><span>Reference selection</span><select aria-label="Use reference" disabled={Boolean(created.params?.submission_options) || !release?.submission_options?.defaults} value={useReference} onChange={(event) => setUseReference(event.target.value)}>{(release?.submission_options?.defaults ? release.submission_options.reference_values : [useReference]).map(value=><option key={value} value={value}>{value || 'Frozen selection unavailable'}</option>)}</select></label><label className="field"><span>Resource set</span><select aria-label="Resource set" value="default" disabled><option value="default">WGS release default</option></select></label><button className="button primary" type="button" disabled={submitting} onClick={() => void confirmConfiguration()}>Confirm configuration</button></div></section> : null}
    {created && phase === "preparing_analysis" ? <section className="panel"><h2>Preparing analysis directory</h2><p>WGS is resolving eligible and pending samples and freezing the CCE bundle.</p></section> : null}
    </SubmissionStep>
    <SubmissionStep number={3} current={currentStep} approved={phase === 'approved'} title="确认并启动分析" description="最终确认入选样本和执行目标，提交后才启动分析。">
    {frozenParameters}
    {created && phase === "execution_review" ? <section className="panel"><h2>Confirm WGS execution</h2><SamplePreview samples={samples} />{created.execution_dispatch ? <ExecutionTargetSelector attempt={created.attempt || 1} batch={batch || String(created.params?.batch || created.params?.sequencing_batch || "-")} sampleCount={samples.length} dispatch={created.execution_dispatch} onSwitch={switchExecutionTarget} onRefresh={async () => setCreated(await getRunDetail(created.analysis_id))} /> : null}<p>Review the final selected samples before starting the selected execution backend.</p><button className="button primary" type="button" disabled={submitting || samples.length === 0} onClick={() => void startExecution()}>Start WGS workflow</button></section> : null}
    {created && phase === "approved" ? <>{created.execution_dispatch ? <ExecutionTargetSelector attempt={created.attempt || 1} batch={batch || String(created.params?.batch || created.params?.sequencing_batch || "-")} sampleCount={samples.length} dispatch={created.execution_dispatch} onSwitch={switchExecutionTarget} onRefresh={async () => setCreated(await getRunDetail(created.analysis_id))} /> : null}<p className="success-note">WGS execution approved: <Link to={`/runs/${created.analysis_id}`}>{created.analysis_id}</Link>.</p></> : null}
    </SubmissionStep>
    </ol>
    {created && preparationFailed ? <section className="panel" role="alert"><h2>Sample information preparation failed</h2><p>{created.error_summary || "The preparation task failed before sample information became available."}</p><Link className="button primary" to={`/runs/${created.analysis_id}`}>View failure details</Link></section> : null}
    {error || preparationRefresh.error ? <div className="inline-error" role="alert">{error || preparationRefresh.error}</div> : null}
  </div>;
}

function SubmissionStep({number, current, title, description, summary, approved = false, children}: {
  number: number; current: number; title: string; description: string; summary?: string; approved?: boolean; children: ReactNode;
}) {
  const active = number === current && !approved;
  const completed = current > number || approved;
  const state = completed ? 'completed' : active ? 'active' : 'pending';
  return <li className={`submission-step ${state}`} aria-current={active ? 'step' : undefined} aria-disabled={!active && !completed ? true : undefined}>
    <header className="submission-step-heading">
      <span className="submission-step-number" aria-hidden="true">{completed ? '✓' : String(number).padStart(2, '0')}</span>
      <div className="submission-step-text"><h2>{title}</h2><p>{description}</p></div>
      <span className="submission-step-status">{approved ? '已提交' : completed ? '已完成' : active ? '当前步骤' : current === 0 ? '暂不可操作' : number === 3 ? '尚未提交' : '待完成上一步'}</span>
    </header>
    {active || approved ? <div className="submission-step-content">{children}</div> : completed && summary ? <p className="submission-step-summary">{summary}</p> : null}
  </li>;
}

function GatkSubmitForm({pipelineSelector}: {pipelineSelector: ReactNode}) {
  const [release, setRelease] = useState<GatkRelease | null>(null);
  const [sourceProjectDir, setSourceProjectDir] = useSubmissionDraft("gatk", "source", "");
  const [preview, setPreview] = useState<GatkSubmissionPreview | null>(null);
  const [created, setCreated] = useState<RunDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const executionEnabled = Boolean(release?.execution_enabled);

  useEffect(() => {
    getGatkRelease()
      .then(setRelease)
      .catch((loadError) => setError(errorMessage(loadError)));
  }, []);

  async function loadPreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setCreated(null);
    try {
      setPreview(await previewGatkSubmission(sourceProjectDir.trim()));
    } catch (submitError) {
      setPreview(null);
      setError(errorMessage(submitError));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      setCreated(await createRun({
        pipeline: "gatk",
        project_name: "WES_Clinical",
        execution_mode: "cce",
        batch_no: preview.batch,
        submission_draft_id: preview.draft_id,
        submission_preview_hash: preview.preview_hash,
      }));
    } catch (submitError) {
      setError(errorMessage(submitError));
    } finally {
      setBusy(false);
    }
  }

  return <div className="page-stack submit-wizard">
    <section className="page-header"><div><p className="eyebrow">GATK V7.6.0 · CCE</p><h1>Submit GATK Cloud</h1><p>Select one controlled WES project, review its locked SCMC sample set, then submit the Step1-Step6 workflow.</p></div></section>
    <section className="panel">
      <dl className="definition-grid"><div><dt>Runtime profile</dt><dd>{release?.profile_id || "Loading profile..."}</dd></div><div><dt>Revision</dt><dd>{release?.profile_revision || "-"}</dd></div><div><dt>Execution</dt><dd>{release ? (executionEnabled ? "Enabled" : "Disabled") : "Loading..."}</dd></div></dl>
      <p>Caller: {release?.caller || 'GATK HaplotypeCaller'}. Profile above is configured, not an observed Master identity.</p>
      <dl className="definition-grid"><div><dt>Observed cce-pipeline</dt><dd>{release?.runtime_identity?.observed.cce_pipeline_version || 'Not observed'}</dd></div><div><dt>Observed profile</dt><dd>{release?.runtime_identity?.observed.profile_id || 'Not observed'}</dd></div><div><dt>Observed Master</dt><dd>{release?.runtime_identity?.observed.master || 'Not observed'}</dd></div><div><dt>Runtime checked at</dt><dd>{release?.runtime_identity?.observed.checked_at || 'Not recorded'}</dd></div></dl>
      {release?.runtime_identity?.reason ? <p className="field-help">{release.runtime_identity.reason}</p> : null}
      {release && !executionEnabled ? <p className="inline-error" role="note">GATK execution is disabled in this environment. Preview remains read-only.</p> : null}
    </section>
    <section className="panel">
      <form className="form-grid gatk-submit-form" onSubmit={loadPreview}>
        {pipelineSelector}
        <label className="field full"><span>WES project directory</span><input aria-label="WES project directory" value={sourceProjectDir} placeholder="/sg2/21.lijing/WES_Clinical/WES_YYYYMMDDX_T7_V7.6.0_hg38" onChange={(event) => { setSourceProjectDir(event.target.value); setPreview(null); }} /></label>
        <p className="field-help field full">SCMC samples are selected from sampleinfo and locked to the source configuration and barcode set.</p>
        <button className="button primary" type="submit" disabled={busy || !sourceProjectDir.trim()}>{busy ? "Checking..." : "Preview project"}</button>
      </form>
    </section>
    {preview ? <section className="panel">
      <div className="panel-heading"><div><h2>Submission preview</h2><p>Read-only source validation. No run exists until confirmation.</p></div></div>
      <dl className="definition-grid gatk-preview-grid">
        <div><dt>Batch</dt><dd>{preview.batch}</dd></div>
        <div><dt>Runtime profile</dt><dd>{preview.profile_id}</dd></div>
        <div><dt>Sampleinfo</dt><dd>{preview.sampleinfo_name}</dd></div>
        <div><dt>SCMC samples</dt><dd>{preview.sample_count}</dd></div>
        <div><dt>FASTQ</dt><dd>{preview.fastq_file_count} files · {formatBytes(preview.fastq_total_bytes)}</dd></div>
        <div><dt>Input checks</dt><dd>{Object.values(preview.validation).every(Boolean) ? "Passed" : "Needs attention"}</dd></div>
      </dl>
      <div className="table-wrap"><table className="data-table compact"><thead><tr><th>SCMC sample</th><th>Selection</th></tr></thead><tbody>{preview.samples.map((sample) => <tr key={sample}><td>{sample}</td><td><StatusBadge status="locked" size="sm" /></td></tr>)}</tbody></table></div>
      <div className="panel-actions"><button className="button primary" type="button" disabled={busy || Boolean(created) || !executionEnabled} onClick={() => void confirm()}>{busy ? "Submitting..." : "Confirm and submit"}</button></div>
    </section> : null}
    {created ? <p className="success-note">GATK Cloud submitted: <Link to={`/runs/${created.analysis_id}`}>{created.analysis_id}</Link>.</p> : null}
    {error ? <div className="inline-error" role="alert">{error}</div> : null}
  </div>;
}

function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / (1024 ** index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function SamplePreview({samples}: {samples: Sample[]}) {
  return <div className="table-wrap"><table className="data-table compact"><thead><tr><th>Sample</th><th>Family</th><th>Relation</th><th>Sequencing batch</th><th>Status</th></tr></thead><tbody>{samples.map((sample) => <tr key={sample.sample_id}><td>{sample.sample_id}</td><td>{sample.family_id || "-"}</td><td>{sample.family_relation || "-"}</td><td>{sample.sequencing_batch || "-"}</td><td>{sample.status || "pending"}</td></tr>)}{samples.length === 0 ? <tr><td colSpan={5}>No prepared samples are available yet.</td></tr> : null}</tbody></table></div>;
}
