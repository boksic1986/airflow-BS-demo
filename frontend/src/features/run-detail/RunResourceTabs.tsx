import type {Artifact, RunDetail, Sample} from "../../api";

import {StatusBadge} from "../../components/StatusBadge";
import {compactPipelineName, formatBytes, formatDate, safeJson} from "../../lib/format";
import {sampleSourceDisplay} from "../../lib/sampleFiles";

export function RunOverviewTab({detail, samples}: {detail: RunDetail; samples: Sample[]}) {
  return (
    <div className="overview-stack">
      <div className="definition-grid">
        <div><dt>Pipeline</dt><dd>{compactPipelineName(detail.pipeline)}</dd></div>
        <div><dt>Status</dt><dd><StatusBadge status={detail.status} /></dd></div>
        <div><dt>DAG run</dt><dd className="path-text">{detail.dag_run_id || "not set"}</dd></div>
        <div><dt>Samples</dt><dd>{samples.length}</dd></div>
        <div><dt>Created</dt><dd>{formatDate(detail.created_at)}</dd></div>
        <div><dt>Started</dt><dd>{formatDate(detail.started_at)}</dd></div>
        <div><dt>Finished</dt><dd>{formatDate(detail.ended_at)}</dd></div>
        <div><dt>Workdir</dt><dd className="path-text">{detail.workdir || "not set"}</dd></div>
      </div>
      <section>
        <div className="section-heading"><h2>Selected samples manifest</h2><p>Samples and captured source file names</p></div>
        <SamplesManifestTable samples={samples} />
      </section>
    </div>
  );
}

export function RunSamplesTab({samples}: {samples: Sample[]}) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th>sample_id</th><th>family_id</th><th>status</th><th>qc_status</th><th>source files</th></tr></thead>
        <tbody>
          {samples.map((sample) => (
            <tr key={sample.sample_id}>
              <td>{sample.sample_id}</td><td>{sample.family_id || "not set"}</td>
              <td><StatusBadge status={sample.status} /></td><td><StatusBadge status={sample.qc_status || "unknown"} size="sm" /></td>
              <td><SourceFilesCell sample={sample} /></td>
            </tr>
          ))}
          {samples.length === 0 ? <tr><td className="empty-cell" colSpan={5}>No samples returned.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}

export function RunFilesTab({artifacts}: {artifacts: Artifact[]}) {
  const primary = artifacts.filter(isPrimaryArtifact);
  const advanced = artifacts.filter((artifact) => !isPrimaryArtifact(artifact));
  return (
    <div className="artifact-list">
      {(primary.length ? primary : artifacts).map((artifact) => <ArtifactRow artifact={artifact} key={artifact.key} />)}
      {advanced.length ? <details className="advanced-files"><summary>Advanced files</summary>{advanced.map((artifact) => <ArtifactRow artifact={artifact} key={artifact.key} />)}</details> : null}
      {artifacts.length === 0 ? <p className="empty-state">No files or artifacts returned.</p> : null}
    </div>
  );
}

export function RunConfigTab({detail, artifacts}: {detail: RunDetail; artifacts: Artifact[]}) {
  const configArtifacts = artifacts.filter(isConfigArtifact);
  return (
    <div className="config-tab-stack">
      <section>
        <div className="section-heading"><h2>Snakemake run config</h2><p>Run-local Snakemake or NIPT configuration</p></div>
        {configArtifacts.length ? <div className="artifact-list">{configArtifacts.map((artifact) => <ArtifactRow artifact={artifact} key={artifact.key} />)}</div> : <p className="empty-state">No run-local config artifact has been registered yet.</p>}
      </section>
      <details className="advanced-files">
        <summary>Backend request params</summary>
        <pre className="code-block">{safeJson({analysis_id: detail.analysis_id, pipeline: detail.pipeline, dag_id: detail.dag_id, dag_run_id: detail.dag_run_id, params: detail.params})}</pre>
      </details>
    </div>
  );
}

function SamplesManifestTable({samples}: {samples: Sample[]}) {
  return (
    <div className="table-wrap">
      <table className="data-table compact manifest-table">
        <thead><tr><th>sample_id</th><th>source folder</th><th>R1</th><th>R2</th><th>status</th><th>QC</th></tr></thead>
        <tbody>
          {samples.map((sample) => {
            const display = sampleSourceDisplay(sample);
            return <tr key={sample.sample_id}><td>{sample.sample_id}</td><td>{display.primary}</td><td>{basename(sample.fq1)}</td><td>{basename(sample.fq2)}</td><td><StatusBadge status={sample.status} size="sm" /></td><td><StatusBadge status={sample.qc_status || "unknown"} size="sm" /></td></tr>;
          })}
          {samples.length === 0 ? <tr><td className="empty-cell" colSpan={6}>No selected samples returned.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}

function SourceFilesCell({sample}: {sample: Sample}) {
  const display = sampleSourceDisplay(sample);
  return <div className={display.missing ? "source-files missing" : "source-files"}><span>{display.primary}</span>{display.secondary ? <small>{display.secondary}</small> : null}</div>;
}

function ArtifactRow({artifact}: {artifact: Artifact}) {
  return <article className="artifact-row"><div><strong>{artifact.label}</strong><span>{artifact.type}</span><span className="path-text">{artifact.path}</span></div><span>{formatBytes(artifact.size_bytes)}</span></article>;
}

function isPrimaryArtifact(artifact: Artifact): boolean {
  const text = `${artifact.key} ${artifact.type} ${artifact.label} ${artifact.path}`.toLowerCase();
  return text.includes("log") || text.includes("report") || text.includes("qc") || text.includes("summary");
}

function isConfigArtifact(artifact: Artifact): boolean {
  const text = `${artifact.key} ${artifact.type} ${artifact.label} ${artifact.path}`.toLowerCase();
  return text.includes("config") || text.endsWith(".yaml") || text.endsWith(".yml") || text.endsWith(".json");
}

function basename(value?: string | null): string {
  if (!value) return "Path not captured for this run";
  return value.split(/[\\/]/).filter(Boolean).pop() || value;
}
