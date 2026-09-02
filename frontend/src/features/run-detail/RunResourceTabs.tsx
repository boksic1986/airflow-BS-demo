import type {Artifact, RunConfig, RunDetail, Sample} from "../../api";

import {StatusBadge} from "../../components/StatusBadge";
import {compactPipelineName, formatBytes, formatDate, safeJson} from "../../lib/format";

export function RunOverviewTab({detail, samples}: {detail: RunDetail; samples: Sample[]}) {
  return (
    <div className="overview-stack">
      <div className="definition-grid">
        <div><dt>Pipeline</dt><dd>{compactPipelineName(detail.pipeline)}</dd></div>
        <div><dt>Batch</dt><dd>{String(detail.params?.batch_no || "not set")}</dd></div>
        <div><dt>WGS release</dt><dd>{detail.pipeline_release_id || "not pinned"}</dd></div>
        <div><dt>Attempt</dt><dd>{String(detail.params?.attempt || "1")}</dd></div>
        <div><dt>Status</dt><dd><StatusBadge status={detail.status} /></dd></div>
        <div><dt>DAG run</dt><dd className="path-text">{detail.dag_run_id || "not set"}</dd></div>
        <div><dt>Samples</dt><dd>{samples.length}</dd></div>
        <div><dt>Operator</dt><dd>{detail.submitted_by || "not captured"}</dd></div>
        <div><dt>Created</dt><dd>{formatDate(detail.created_at)}</dd></div>
        <div><dt>Submitted</dt><dd>{formatDate(detail.submitted_at)}</dd></div>
        <div><dt>Airflow started</dt><dd>{formatDate(detail.started_at)}</dd></div>
        <div><dt>Finished</dt><dd>{formatDate(detail.pipeline_finished_at || detail.ended_at)}</dd></div>
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
        <thead><tr><th>sample_id</th><th>family_id</th><th>relation</th><th>status</th><th>R1 / R2</th></tr></thead>
        <tbody>
          {samples.map((sample) => (
            <tr key={sample.sample_id}>
              <td>{sample.sample_id}</td><td>{sample.family_id || "not set"}</td>
              <td>{sample.family_relation || "not set"}</td><td><StatusBadge status={sample.status} /></td>
              <td>{sample.r1_filename || "-"} / {sample.r2_filename || "-"}</td>
            </tr>
          ))}
          {samples.length === 0 ? <tr><td className="empty-cell" colSpan={5}>No samples returned.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}

export function RunFilesTab({artifacts}: {artifacts: Artifact[]}) {
  const visibleArtifacts = artifacts.filter((artifact) => !isComposeArtifact(artifact));
  const primary = visibleArtifacts.filter(isPrimaryArtifact);
  const advanced = visibleArtifacts.filter((artifact) => !isPrimaryArtifact(artifact));
  return (
    <div className="artifact-list">
      {(primary.length ? primary : visibleArtifacts).map((artifact) => <ArtifactRow artifact={artifact} key={artifact.key} />)}
      {advanced.length ? <details className="advanced-files"><summary>Advanced files</summary>{advanced.map((artifact) => <ArtifactRow artifact={artifact} key={artifact.key} />)}</details> : null}
      {visibleArtifacts.length === 0 ? <p className="empty-state">No files or artifacts returned.</p> : null}
    </div>
  );
}

export function RunConfigTab({detail, artifacts, config}: {detail: RunDetail; artifacts: Artifact[]; config: RunConfig | null}) {
  const configArtifacts = artifacts.filter((artifact) => isConfigArtifact(artifact) && !isComposeArtifact(artifact));
  return (
    <div className="config-tab-stack">
      <section>
        <div className="section-heading"><h2>Snakemake run config</h2><p>Immutable requested and resolved configuration for this run.</p></div>
        {config?.profile ? (
          <div className="runtime-profile-summary">
            <div><span>Runtime profile</span><strong>{config.profile.label}</strong></div>
            <div><span>Pipeline version</span><strong>{config.profile.pipeline_version}</strong></div>
            <div><span>Config revision</span><strong>{config.profile.config_version}</strong></div>
            <div><span>Modified fields</span><strong>{config.changed_paths.length}</strong></div>
          </div>
        ) : null}
        {config?.changed_paths.length ? <p className="config-changed-paths">{config.changed_paths.join(" · ")}</p> : null}
      </section>
      <section className="run-config-section">
        <div className="section-heading"><h3>Requested config</h3><p>Editable Snakemake fields captured at run creation.</p></div>
        {config?.requested_yaml ? <pre className="code-block config-code-block">{config.requested_yaml}</pre> : <p className="empty-state">No requested override was captured for this legacy run.</p>}
      </section>
      <section className="run-config-section">
        <div className="section-heading"><h3>Resolved config</h3><p>The exact Snakemake YAML produced by the Airflow prepare task.</p></div>
        {config?.resolved_yaml ? <pre className="code-block config-code-block">{config.resolved_yaml}</pre> : <p className="empty-state">{config?.state === "waiting_for_prepare" ? "Waiting for prepare task" : "No resolved Snakemake config captured."}</p>}
      </section>
      {!config && configArtifacts.length ? <section><div className="artifact-list">{configArtifacts.map((artifact) => <ArtifactRow artifact={artifact} key={artifact.key} />)}</div></section> : null}
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
        <thead><tr><th>sample/data</th><th>family</th><th>relation</th><th>R1</th><th>R2</th><th>status</th></tr></thead>
        <tbody>
          {samples.map((sample) => <tr key={sample.sample_id}><td>{sample.data_id || sample.sample_id}</td><td>{sample.family_id || "-"}</td><td>{sample.family_relation || "-"}</td><td>{sample.r1_filename || "-"}</td><td>{sample.r2_filename || "-"}</td><td><StatusBadge status={sample.status} size="sm" /></td></tr>)}
          {samples.length === 0 ? <tr><td className="empty-cell" colSpan={6}>No selected samples returned.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
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

function isComposeArtifact(artifact: Artifact): boolean {
  const text = `${artifact.key} ${artifact.type} ${artifact.label} ${artifact.path}`.toLowerCase();
  return text.includes("docker_compose") || text.includes("docker compose") || /compose\.ya?ml/.test(text);
}
