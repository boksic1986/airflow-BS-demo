import type {Artifact, RunConfig, RunDetail, WgsManifestSummary, WgsSampleManifestRow} from "../../api";

import {StatusBadge} from "../../components/StatusBadge";
import {compactPipelineName, formatBytes, formatDate, safeJson} from "../../lib/format";

export function RunOverviewTab({detail, samples, sampleCount, manifestSummary}: {detail: RunDetail; samples: WgsSampleManifestRow[]; sampleCount?: number; manifestSummary?: WgsManifestSummary | null}) {
  return (
    <div className="overview-stack">
      <div className="definition-grid">
        <div><dt>Pipeline</dt><dd>{compactPipelineName(detail.pipeline)}</dd></div>
        <div><dt>Batch</dt><dd>{String(detail.params?.batch_no || "not set")}</dd></div>
        <div><dt>WGS release</dt><dd>{detail.pipeline_release_id || "not pinned"}</dd></div>
        <div><dt>Attempt</dt><dd>{String(detail.params?.attempt || "1")}</dd></div>
        <div><dt>Status</dt><dd><StatusBadge status={detail.status} /></dd></div>
        <div><dt>DAG run</dt><dd className="path-text">{detail.dag_run_id || "not set"}</dd></div>
        <div><dt>Samples</dt><dd>{sampleCount ?? samples.length}</dd></div>
        <div><dt>Operator</dt><dd>{detail.submitted_by || "not captured"}</dd></div>
        <div><dt>Created</dt><dd>{formatDate(detail.created_at)}</dd></div>
        <div><dt>Submitted</dt><dd>{formatDate(detail.submitted_at)}</dd></div>
        <div><dt>Airflow started</dt><dd>{formatDate(detail.started_at)}</dd></div>
        <div><dt>Finished</dt><dd>{formatDate(detail.pipeline_finished_at || detail.ended_at)}</dd></div>
      </div>
      <section>
        <div className="section-heading"><h2>Batch manifest summary</h2><p>Privacy-safe aggregates from the frozen sampleinfo.tsv.</p></div>
        <div className="definition-grid manifest-summary-grid">
          <div><dt>Samples / families</dt><dd>{manifestSummary ? `${manifestSummary.sample_count ?? sampleCount ?? samples.length} / ${manifestSummary.family_count ?? "-"}` : "Pending"}</dd></div>
          <div><dt>Orders</dt><dd>{manifestSummary?.order_count ?? "-"}</dd></div>
          <div><dt>Sample types</dt><dd>{manifestSummary?.sample_types?.join(", ") || "-"}</dd></div>
          <div><dt>Received</dt><dd>{dateRange(manifestSummary?.received_date_range)}</dd></div>
          <div><dt>Estimated report</dt><dd>{dateRange(manifestSummary?.estimated_report_date_range)}</dd></div>
          <div><dt>Test project</dt><dd>{manifestSummary?.test_projects?.join(", ") || "-"}</dd></div>
          <div><dt>Method</dt><dd>{manifestSummary?.test_methods?.join(", ") || "-"}</dd></div>
          <div><dt>Result delivery</dt><dd><StatusBadge status={manifestSummary?.result_delivery_status || "not_started"} /></dd></div>
          <div><dt>Project path</dt><dd className="path-text">{manifestSummary?.project_path || "not recorded"}</dd></div>
        </div>
      </section>
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

function dateRange(value?: {start: string; end: string} | null): string {
  if (!value) return "-";
  return value.start === value.end ? value.start : `${value.start} – ${value.end}`;
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
