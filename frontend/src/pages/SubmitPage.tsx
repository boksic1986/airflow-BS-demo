import {useEffect, useState, type FormEvent} from "react";
import {Link} from "react-router-dom";

import {createRun, getWgsRelease, type RunDetail, type WgsRelease} from "../api";
import {errorMessage} from "../lib/errors";

export function SubmitPage() {
  const [projectName, setProjectName] = useState("");
  const [batchNo, setBatchNo] = useState("");
  const [fqPath, setFqPath] = useState("");
  const [created, setCreated] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [release, setRelease] = useState<WgsRelease | null>(null);

  useEffect(() => {
    getWgsRelease().then(setRelease).catch((loadError) => setError(errorMessage(loadError)));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const run = await createRun({
        pipeline: "wgs",
        project_name: projectName,
        execution_mode: "cce",
        batch_no: batchNo,
        fq_path: fqPath,
      });
      setCreated(run);
    } catch (submitError) {
      setError(errorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  const valid = Boolean(projectName && batchNo && fqPath);
  return <div className="page-stack"><section className="page-header"><div><p className="eyebrow">WGS production</p><h1>Submit WGS run</h1><p>Register a confirmed CCE batch from its controlled FASTQ link directory. Airflow creates metadata and manifests in its own workdir.</p></div></section><section className="panel"><div className="definition-grid"><div><dt>Current WGS release</dt><dd>{release ? `WGS ${release.version} / ${release.source_commit.slice(0, 7)}` : "Loading release..."}</dd></div><div><dt>Release ID</dt><dd className="path-text">{release?.release_id || "-"}</dd></div></div><form className="form-grid" onSubmit={submit}><label className="field"><span>Project name</span><input aria-label="Project name" value={projectName} onChange={(event) => setProjectName(event.target.value)} /></label><label className="field"><span>Batch number</span><input aria-label="Batch number" value={batchNo} onChange={(event) => setBatchNo(event.target.value)} /></label><label className="field"><span>Controlled FASTQ link directory</span><input aria-label="Controlled FASTQ link directory" value={fqPath} onChange={(event) => setFqPath(event.target.value)} placeholder="/data/wgs-intake/BATCH-001" /></label><div className="inline-error" role="note">Phase 1 only records and validates the request. It will not start CCE or use OBS credentials.</div>{error ? <div className="inline-error" role="alert">{error}</div> : null}<button className="button primary" type="submit" disabled={!valid || submitting || !release}>{submitting ? "Saving..." : "Create disabled WGS request"}</button></form>{created ? <p className="success-note">Created disabled request <Link to={`/runs/${created.analysis_id}`}>{created.analysis_id}</Link>.</p> : null}</section></div>;
}
