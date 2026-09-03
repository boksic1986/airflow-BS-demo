import {useEffect, useMemo, useState, type FormEvent} from "react";
import {Link} from "react-router-dom";
import {approveWgsConfig, createCatalogWgsRun, getRunDetail, getRunSamples, getWgsProjects, getWgsRelease, startWgsExecution, type RunDetail, type Sample, type WgsProjectCatalog, type WgsRelease} from "../api";
import {errorMessage} from "../lib/errors";

export function SubmitPage() {
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
  useEffect(() => { Promise.all([getWgsRelease(), getWgsProjects()]).then(([nextRelease, nextCatalog]) => { setRelease(nextRelease); setCatalog(nextCatalog); }).catch((loadError) => setError(errorMessage(loadError))); }, []);
  const project = useMemo(() => catalog?.items.find((item) => item.project_id === projectId) || catalog?.items[0], [catalog, projectId]);
  const executionEnabled = Boolean(release?.execution_enabled && release.runtime_adapter_enabled);
  const phase = String(created?.params?.submission_phase || "select");
  useEffect(() => {
    if (!created?.analysis_id || phase === "approved") return;
    let stopped = false;
    const refresh = async () => {
      try {
        const [detail, samplePayload] = await Promise.all([
          getRunDetail(created.analysis_id),
          getRunSamples(created.analysis_id),
        ]);
        if (!stopped) { setCreated(detail); setSamples(samplePayload.items); }
      } catch (loadError) {
        if (!stopped) setError(errorMessage(loadError));
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [created?.analysis_id, phase]);
  async function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setError(null);
    try { setCreated(await createCatalogWgsRun({project_id: projectId, platform, batch, fastq_root_id: fastqRootId})); }
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
  return <div className="page-stack submit-wizard">
    <section className="page-header"><div><p className="eyebrow">WGS production</p><h1>Submit run</h1><p>Submit one catalog-controlled WGS batch. The DAG runs native WGS sampleinfo and analysis preparation, then Step1-Step6.</p></div></section>
    <section className="panel"><div className="definition-grid"><div><dt>Current WGS release</dt><dd>{release ? `WGS ${release.version} / ${release.source_commit.slice(0, 7)}` : "Loading release..."}</dd></div><div><dt>Release ID</dt><dd>{release?.release_id || "-"}</dd></div><div><dt>Execution</dt><dd>{executionEnabled ? "Enabled" : "Disabled"}</dd></div></div></section>
    <ol className="wizard-steps"><li className={phase === "select" || phase === "preparing_sampleinfo" ? "active" : ""}>1. Select batch</li><li className={phase === "config_review" || phase === "preparing_analysis" ? "active" : ""}>2. Review samples and configuration</li><li className={phase === "execution_review" || phase === "approved" ? "active" : ""}>3. Confirm execution</li></ol>
    {!created ? <section className="panel"><form className="form-grid" onSubmit={prepare}>
      <label className="field"><span>Pipeline</span><select aria-label="Pipeline" value="wgs" disabled><option value="wgs">WGS</option><option value="wes" disabled>WES (not available)</option></select></label>
      <label className="field"><span>Project</span><select aria-label="Project" value={projectId} onChange={(event) => setProjectId(event.target.value)}>{catalog?.items.map((item) => <option value={item.project_id} key={item.project_id}>{item.display_name}</option>)}</select></label>
      <label className="field"><span>Platform</span><select aria-label="Platform" value={platform} onChange={(event) => setPlatform(event.target.value)}>{project?.platforms.map((item) => <option value={item.platform_id} key={item.platform_id}>{item.display_name}</option>)}</select></label>
      <label className="field"><span>Batch</span><input aria-label="Batch" placeholder="20260901B" value={batch} onChange={(event) => setBatch(event.target.value)} /></label>
      <label className="field"><span>FASTQ root</span><select aria-label="FASTQ root" value={fastqRootId} onChange={(event) => setFastqRootId(event.target.value)}>{project?.fastq_roots.map((item) => <option value={item.root_id} key={item.root_id}>{item.display_name}</option>)}</select></label>
      <p className="field-help">WGS first generates sampleinfo. Analysis and cloud execution start only after the following confirmations.</p>
      <button className="button primary" type="submit" disabled={!executionEnabled || !projectId || !platform || !batch || !fastqRootId || submitting}>{submitting ? "Preparing..." : "Prepare sample information"}</button>
      {!executionEnabled ? <p className="inline-error" role="note">Execution is disabled. No AnalysisRun, OBS transfer or CCE task can start.</p> : null}
    </form></section> : null}
    {created && phase === "preparing_sampleinfo" ? <section className="panel"><h2>Preparing sample information</h2><p>The WGS sampleinfo task is running. This page refreshes automatically.</p></section> : null}
    {created && phase === "config_review" ? <section className="panel"><h2>Review samples and configuration</h2><SamplePreview samples={samples} /><div className="form-grid"><label className="field"><span>Reference selection</span><select aria-label="Use reference" value={useReference} onChange={(event) => setUseReference(event.target.value as "all" | "ref" | "no")}><option value="all">All</option><option value="ref">Reference only</option><option value="no">No reference</option></select></label><label className="field"><span>Resource set</span><select aria-label="Resource set" value="default" disabled><option value="default">WGS release default</option></select></label><button className="button primary" type="button" disabled={submitting} onClick={() => void confirmConfiguration()}>Confirm configuration</button></div></section> : null}
    {created && phase === "preparing_analysis" ? <section className="panel"><h2>Preparing analysis directory</h2><p>WGS is resolving eligible and pending samples and freezing the CCE bundle.</p></section> : null}
    {created && phase === "execution_review" ? <section className="panel"><h2>Confirm WGS execution</h2><SamplePreview samples={samples} /><p>Review the final selected samples before starting Step1 upload through Step6 materialization.</p><button className="button primary" type="button" disabled={submitting || samples.length === 0} onClick={() => void startExecution()}>Start WGS workflow</button></section> : null}
    {created && phase === "approved" ? <p className="success-note">WGS execution started: <Link to={`/runs/${created.analysis_id}`}>{created.analysis_id}</Link>.</p> : null}
    {error ? <div className="inline-error" role="alert">{error}</div> : null}
  </div>;
}

function SamplePreview({samples}: {samples: Sample[]}) {
  return <div className="table-wrap"><table className="data-table compact"><thead><tr><th>Sample</th><th>Family</th><th>Relation</th><th>Sequencing batch</th><th>Status</th></tr></thead><tbody>{samples.map((sample) => <tr key={sample.sample_id}><td>{sample.sample_id}</td><td>{sample.family_id || "-"}</td><td>{sample.family_relation || "-"}</td><td>{sample.sequencing_batch || "-"}</td><td>{sample.status || "pending"}</td></tr>)}{samples.length === 0 ? <tr><td colSpan={5}>No prepared samples are available yet.</td></tr> : null}</tbody></table></div>;
}
