import {useEffect, useMemo, useState, type FormEvent, type ReactNode} from "react";
import {Link, useSearchParams} from "react-router-dom";
import {approveWgsConfig, createCatalogWgsRun, createRun, getGatkRelease, getRunDetail, getRunSamples, getWgsProjects, getWgsRelease, previewGatkSubmission, startWgsExecution, updateWgsExecutionChoice, type GatkRelease, type GatkSubmissionPreview, type PipelineCapability, type RunDetail, type Sample, type WgsExecutionChoiceRequest, type WgsProjectCatalog, type WgsRelease} from "../api";
import {ExecutionTargetSelector} from "../features/wgs/ExecutionTargetSelector";
import {StatusBadge} from "../components/StatusBadge";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {hasRegisteredSubmissionUi} from "../features/platform/submissionUiRegistry";
import {errorMessage} from "../lib/errors";
import {getWgsSubmissionSnapshot} from "../api";
import {IncompleteSubmissionsPanel} from "../features/wgs/IncompleteSubmissions";
import {CancelSubmission} from "../features/wgs/CancelSubmission";

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
  return selected.id === "gatk"
    ? <GatkSubmitForm pipelineSelector={pipelineSelector} />
    : <WgsSubmitForm pipelineSelector={pipelineSelector} />;
}

function SubmissionPipelineField({pipelines, selectedId, onChange}: {pipelines: PipelineCapability[]; selectedId: string; onChange: (pipelineId: string) => void}) {
  return <div className="field submission-pipeline-field"><span>Pipeline</span><div className="segmented-control submission-pipeline-switcher" role="tablist" aria-label="Submission pipeline">{pipelines.map((pipeline) => <button className={pipeline.id === selectedId ? "active" : ""} type="button" role="tab" aria-selected={pipeline.id === selectedId} key={pipeline.id} onClick={() => onChange(pipeline.id)}>{pipeline.display_name}</button>)}</div></div>;
}

function WgsSubmitForm({pipelineSelector}: {pipelineSelector: ReactNode}) {
  const capabilities = usePlatformCapabilities();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedRun = searchParams.get("analysis_id");
  const [release, setRelease] = useState<WgsRelease | null>(null);
  const [catalog, setCatalog] = useState<WgsProjectCatalog | null>(null);
  const [projectId, setProjectId] = useState("WGS_Clinical");
  const [platform, setPlatform] = useState("T7");
  const [batch, setBatch] = useState("");
  const [fastqRootId, setFastqRootId] = useState("T7_Fastq");
  const [useReference, setUseReference] = useState<"all" | "ref" | "no">("all");
  const [samples, setSamples] = useState<Sample[]>([]);
  const [created, setCreated] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [restoring, setRestoring] = useState(Boolean(requestedRun));
  useEffect(() => {
    if (!requestedRun) { setCreated(null); setSamples([]); setRestoring(false); return; }
    let stopped = false;
    setRestoring(true); setError(null);
    setCreated((current) => current?.analysis_id === requestedRun ? current : null);
    setSamples([]);
    getWgsSubmissionSnapshot(requestedRun).then(({detail, items}) => {
      if (stopped) return;
      setCreated(detail);
      setSamples(items);
      const reference = detail.params?.use_reference;
      if (reference === "all" || reference === "ref" || reference === "no") setUseReference(reference);
    }).catch((loadError) => { if (!stopped) setError(errorMessage(loadError)); })
      .finally(() => { if (!stopped) setRestoring(false); });
    return () => { stopped = true; };
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
  const preparationFailed = Boolean(created && ["failed", "unknown_interrupted"].includes(created.status));
  useEffect(() => {
    if (!created?.analysis_id || preparationFailed || ["success", "failed", "cancelled"].includes(created.status)) return;
    let stopped = false;
    const refresh = async () => {
      try {
        const {detail, items} = await getWgsSubmissionSnapshot(created.analysis_id);
        if (!stopped) { setCreated(detail); setSamples(items); }
      } catch (loadError) {
        if (!stopped) setError(errorMessage(loadError));
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [created?.analysis_id, phase, preparationFailed]);
  async function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setError(null);
    try {
      const detail = await createCatalogWgsRun({project_id: projectId, platform, batch, fastq_root_id: fastqRootId});
      setCreated(detail);
      setSearchParams({pipeline: "wgs", analysis_id: detail.analysis_id}, {replace: true});
    }
    catch (submitError) { setError(errorMessage(submitError)); }
    finally { setSubmitting(false); }
  }
  async function confirmConfiguration() {
    if (!created) return;
    setSubmitting(true); setError(null);
    try {
      await approveWgsConfig(created.analysis_id, {use_reference: useReference, resource_set: "default"});
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
    <ol className="wizard-steps"><li className={phase === "select" || phase === "preparing_sampleinfo" ? "active" : ""}>1. Select batch</li><li className={phase === "config_review" || phase === "preparing_analysis" ? "active" : ""}>2. Review samples and configuration</li><li className={phase === "execution_review" || phase === "approved" ? "active" : ""}>3. Confirm execution</li></ol>
    {phase === "cancelled" ? <section className="panel" role="status"><h2>提交已取消</h2><p>样本表和回执已保留作审计；未修改 pending 或删除分析数据。</p></section> : null}
    {phase === "cancelling_submission" ? <section className="panel" role="status"><h2>取消尚未确认</h2><p>已禁止继续确认配置。请使用右上角“重试取消提交”完成停止确认。</p></section> : null}
    {requestedRun ? <section className="panel"><Link to={`/runs/${requestedRun}`}>View existing run</Link>{restoring ? <p>Restoring submission...</p> : null}{!restoring && !created ? <p>The existing run could not be loaded. Refresh to retry; no new run has been submitted.</p> : null}</section> : null}
    {!created && !requestedRun ? <section className="panel"><form className="form-grid" onSubmit={prepare}>
      {pipelineSelector}
      <label className="field"><span>Project</span><select aria-label="Project" value={projectId} onChange={(event) => setProjectId(event.target.value)}>{catalog?.items.map((item) => <option value={item.project_id} key={item.project_id}>{item.display_name}</option>)}</select></label>
      <label className="field"><span>Platform</span><select aria-label="Platform" value={platform} onChange={(event) => setPlatform(event.target.value)}>{project?.platforms.map((item) => <option value={item.platform_id} key={item.platform_id}>{item.display_name}</option>)}</select></label>
      <label className="field"><span>Batch</span><input aria-label="Batch" placeholder="20260901B" value={batch} onChange={(event) => setBatch(event.target.value)} /></label>
      <label className="field"><span>FASTQ root</span><select aria-label="FASTQ root" value={fastqRootId} onChange={(event) => setFastqRootId(event.target.value)}>{project?.fastq_roots.map((item) => <option value={item.root_id} key={item.root_id}>{item.display_name}</option>)}</select></label>
      <p className="field-help">WGS first generates sampleinfo. Analysis and cloud execution start only after the following confirmations.</p>
      <button className="button primary" type="submit" disabled={!executionEnabled || !projectId || !platform || !batch || !fastqRootId || submitting}>{submitting ? "Preparing..." : "Prepare sample information"}</button>
      {!executionEnabled ? <p className="inline-error" role="note">Execution is disabled. No AnalysisRun, OBS transfer or CCE task can start.</p> : null}
    </form></section> : null}
    {created && preparationFailed ? <section className="panel" role="alert"><h2>Sample information preparation failed</h2><p>{created.error_summary || "The preparation task failed before sample information became available."}</p><Link className="button primary" to={`/runs/${created.analysis_id}`}>View failure details</Link></section> : null}
    {created && !preparationFailed && phase === "preparing_sampleinfo" ? <section className="panel"><h2>Preparing sample information</h2><p>The WGS sampleinfo task is running. This page refreshes automatically.</p></section> : null}
    {created && phase === "config_review" ? <section className="panel"><h2>Review samples and configuration</h2><SamplePreview samples={samples} /><div className="form-grid"><label className="field"><span>Reference selection</span><select aria-label="Use reference" value={useReference} onChange={(event) => setUseReference(event.target.value as "all" | "ref" | "no")}><option value="all">All</option><option value="ref">Reference only</option><option value="no">No reference</option></select></label><label className="field"><span>Resource set</span><select aria-label="Resource set" value="default" disabled><option value="default">WGS release default</option></select></label><button className="button primary" type="button" disabled={submitting} onClick={() => void confirmConfiguration()}>Confirm configuration</button></div></section> : null}
    {created && phase === "preparing_analysis" ? <section className="panel"><h2>Preparing analysis directory</h2><p>WGS is resolving eligible and pending samples and freezing the CCE bundle.</p></section> : null}
    {created && phase === "execution_review" ? <section className="panel"><h2>Confirm WGS execution</h2><SamplePreview samples={samples} />{created.execution_dispatch ? <ExecutionTargetSelector attempt={created.attempt || 1} batch={batch || String(created.params?.batch || created.params?.sequencing_batch || "-")} sampleCount={samples.length} dispatch={created.execution_dispatch} onSwitch={switchExecutionTarget} onRefresh={async () => setCreated(await getRunDetail(created.analysis_id))} /> : null}<p>Review the final selected samples before starting the selected execution backend.</p><button className="button primary" type="button" disabled={submitting || samples.length === 0} onClick={() => void startExecution()}>Start WGS workflow</button></section> : null}
    {created && phase === "approved" ? <>{created.execution_dispatch ? <ExecutionTargetSelector attempt={created.attempt || 1} batch={batch || String(created.params?.batch || created.params?.sequencing_batch || "-")} sampleCount={samples.length} dispatch={created.execution_dispatch} onSwitch={switchExecutionTarget} onRefresh={async () => setCreated(await getRunDetail(created.analysis_id))} /> : null}<p className="success-note">WGS execution approved: <Link to={`/runs/${created.analysis_id}`}>{created.analysis_id}</Link>.</p></> : null}
    {error ? <div className="inline-error" role="alert">{error}</div> : null}
  </div>;
}

function GatkSubmitForm({pipelineSelector}: {pipelineSelector: ReactNode}) {
  const [release, setRelease] = useState<GatkRelease | null>(null);
  const [sourceProjectDir, setSourceProjectDir] = useState("");
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
