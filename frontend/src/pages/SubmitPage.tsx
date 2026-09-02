import {useEffect, useMemo, useState, type FormEvent} from "react";
import {Link} from "react-router-dom";
import {createCatalogWgsRun, getWgsProjects, getWgsRelease, type RunDetail, type WgsProjectCatalog, type WgsRelease} from "../api";
import {errorMessage} from "../lib/errors";

export function SubmitPage() {
  const [release, setRelease] = useState<WgsRelease | null>(null);
  const [catalog, setCatalog] = useState<WgsProjectCatalog | null>(null);
  const [projectId, setProjectId] = useState("WGS_Clinical");
  const [platform, setPlatform] = useState("T7");
  const [sequencingBatch, setSequencingBatch] = useState("");
  const [analysisBatch, setAnalysisBatch] = useState("");
  const [fastqRootId, setFastqRootId] = useState("T7_Fastq");
  const [useReference, setUseReference] = useState<"all" | "ref" | "no">("all");
  const [algo, setAlgo] = useState<"DNAscope" | "Haplotyper">("DNAscope");
  const [created, setCreated] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => { Promise.all([getWgsRelease(), getWgsProjects()]).then(([nextRelease, nextCatalog]) => { setRelease(nextRelease); setCatalog(nextCatalog); }).catch((loadError) => setError(errorMessage(loadError))); }, []);
  const project = useMemo(() => catalog?.items.find((item) => item.project_id === projectId) || catalog?.items[0], [catalog, projectId]);
  const executionEnabled = Boolean(release?.execution_enabled && release.runtime_adapter_enabled);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setError(null);
    try { setCreated(await createCatalogWgsRun({project_id: projectId, platform, sequencing_batch: sequencingBatch, analysis_batch: analysisBatch, fastq_root_id: fastqRootId, use_reference: useReference, algo})); }
    catch (submitError) { setError(errorMessage(submitError)); }
    finally { setSubmitting(false); }
  }
  return <div className="page-stack submit-wizard">
    <section className="page-header"><div><p className="eyebrow">WGS production</p><h1>Submit run</h1><p>Submit one catalog-controlled WGS batch. The DAG runs native WGS sampleinfo and analysis preparation, then Step1-Step6.</p></div></section>
    <section className="panel"><div className="definition-grid"><div><dt>Current WGS release</dt><dd>{release ? `WGS ${release.version} / ${release.source_commit.slice(0, 7)}` : "Loading release..."}</dd></div><div><dt>Release ID</dt><dd>{release?.release_id || "-"}</dd></div><div><dt>Execution</dt><dd>{executionEnabled ? "Enabled" : "Disabled"}</dd></div></div></section>
    <section className="panel"><form className="form-grid" onSubmit={submit}>
      <label className="field"><span>Project</span><select aria-label="Project" value={projectId} onChange={(event) => setProjectId(event.target.value)}>{catalog?.items.map((item) => <option value={item.project_id} key={item.project_id}>{item.display_name}</option>)}</select></label>
      <label className="field"><span>Platform</span><select aria-label="Platform" value={platform} onChange={(event) => setPlatform(event.target.value)}>{project?.platforms.map((item) => <option value={item.platform_id} key={item.platform_id}>{item.display_name}</option>)}</select></label>
      <label className="field"><span>Sequencing batch</span><input aria-label="Sequencing batch" placeholder="20260902A" value={sequencingBatch} onChange={(event) => setSequencingBatch(event.target.value)} /></label>
      <label className="field"><span>Analysis batch</span><input aria-label="Analysis batch" placeholder="20260902A" value={analysisBatch} onChange={(event) => setAnalysisBatch(event.target.value)} /></label>
      <label className="field"><span>FASTQ root</span><select aria-label="FASTQ root" value={fastqRootId} onChange={(event) => setFastqRootId(event.target.value)}>{project?.fastq_roots.map((item) => <option value={item.root_id} key={item.root_id}>{item.display_name}</option>)}</select></label>
      <label className="field"><span>Reference selection</span><select aria-label="Use reference" value={useReference} onChange={(event) => setUseReference(event.target.value as "all" | "ref" | "no")}><option value="all">All</option><option value="ref">Reference only</option><option value="no">No reference</option></select></label>
      <label className="field"><span>Variant caller</span><select aria-label="Variant caller" value={algo} onChange={(event) => setAlgo(event.target.value as "DNAscope" | "Haplotyper")}><option value="DNAscope">DNAscope</option><option value="Haplotyper">Haplotyper</option></select></label>
      <p className="field-help">WGS first generates sampleinfo, then analysis resolves eligible and pending inputs and creates the project directory. Intermediate files are not edited here. Samples appear only after prepare succeeds and only include the final analysis selection.</p>
      <button className="button primary" type="submit" disabled={!executionEnabled || !projectId || !platform || !sequencingBatch || !analysisBatch || !fastqRootId || submitting}>{submitting ? "Submitting..." : "Submit WGS analysis"}</button>
      {!executionEnabled ? <p className="inline-error" role="note">Execution is disabled. No AnalysisRun, OBS transfer or CCE task can start.</p> : null}
    </form></section>
    {error ? <div className="inline-error" role="alert">{error}</div> : null}
    {created ? <p className="success-note">Submitted <Link to={`/runs/${created.analysis_id}`}>{created.analysis_id}</Link>.</p> : null}
  </div>;
}
