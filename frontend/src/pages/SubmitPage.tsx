import {useState, type FormEvent} from "react";
import {Link} from "react-router-dom";

import {createRun, type RunDetail} from "../api";
import {errorMessage} from "../lib/errors";

export function SubmitPage() {
  const [projectName, setProjectName] = useState("");
  const [executionMode, setExecutionMode] = useState<"cce" | "sge" | "local">("cce");
  const [sourcePath, setSourcePath] = useState("");
  const [created, setCreated] = useState<RunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const run = await createRun({
        pipeline: "wgs",
        project_name: projectName,
        execution_mode: executionMode,
        source_path: sourcePath,
      });
      setCreated(run);
    } catch (submitError) {
      setError(errorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  const valid = Boolean(projectName && sourcePath);
  return <div className="page-stack"><section className="page-header"><div><p className="eyebrow">WGS production</p><h1>Submit WGS run</h1><p>Record an approved whole-genome sequencing request. Execution remains disabled until the Phase 2 capability is enabled.</p></div></section><section className="panel"><form className="form-grid" onSubmit={submit}><label className="field"><span>Project name</span><input value={projectName} onChange={(event) => setProjectName(event.target.value)} /></label><label className="field"><span>Execution mode</span><select aria-label="Execution mode" value={executionMode} onChange={(event) => setExecutionMode(event.target.value as "cce" | "sge" | "local")}><option value="cce">CCE (configured, disabled)</option><option value="sge">SGE (configured, disabled)</option><option value="local">Local (configured, disabled)</option></select></label><label className="field"><span>Controlled batch directory</span><input value={sourcePath} onChange={(event) => setSourcePath(event.target.value)} placeholder="Approved path containing manifest, FASTQ.MD5SUMS and READY" /></label><div className="inline-error" role="note">Execution is configured but disabled. This request will not start CCE, SGE, or local WGS work.</div>{error ? <div className="inline-error" role="alert">{error}</div> : null}<button className="button primary" type="submit" disabled={!valid || submitting}>{submitting ? "Saving..." : "Create disabled WGS request"}</button></form>{created ? <p className="success-note">Created disabled request <Link to={`/runs/${created.analysis_id}`}>{created.analysis_id}</Link>.</p> : null}</section></div>;
}
