import {Link} from "react-router-dom";

import type {DashboardOverview, DashboardPipeline, DashboardRunTrackerRow, SystemResourcesResponse} from "../../api";

import {StatusBadge} from "../../components/StatusBadge";
import {compactPipelineName} from "../../lib/format";
import {isActiveStatus} from "../../lib/status";

const resourceTabs: DashboardPipeline[] = ["all", "pgta", "nipt_docker", "wgs"];

export function DashboardResourcePanels({resources, resourceTab, overview, rows, loading, error, pipelines, onResourceTabChange}: {
  resources: SystemResourcesResponse | null;
  resourceTab: DashboardPipeline;
  overview: DashboardOverview | null;
  rows: DashboardRunTrackerRow[];
  loading: boolean;
  error: string | null;
  pipelines?: DashboardPipeline[];
  onResourceTabChange: (pipeline: DashboardPipeline) => void;
}) {
  return (
    <section className="dashboard-ops-grid" aria-busy={loading}>
      <ServiceNodeHealth resources={resources} error={error} />
      <PipelineResources resourceTab={resourceTab} resources={resources} error={error} pipelines={pipelines} onResourceTabChange={onResourceTabChange} />
      <WorkflowActivity overview={overview} rows={rows} />
    </section>
  );
}

function ServiceNodeHealth({resources, error}: {resources: SystemResourcesResponse | null; error: string | null}) {
  const disk = resources?.host.disks.find((item) => item.path === "/data") || resources?.host.disks[0];
  const memoryUsed = resources?.host.memory?.used_percent;
  return (
    <div className="panel">
      <div className="section-heading"><h2>Service & Node Health</h2><p>{resources ? `Telemetry: ${resources.source}` : "Node telemetry"}</p></div>
      {error ? <div className="inline-error" role="alert">Resources unavailable: {error}</div> : null}
      <div className="resource-stat-grid">
        <div className="resource-stat"><span>Backend API</span><StatusBadge status={error ? "warning" : "success"} /></div>
        <div className="resource-stat"><span>CPU cores</span><strong>{resources?.host.cpu.cores ?? "not reported"}</strong></div>
        <div className="resource-stat"><span>MEM used</span><strong>{Number.isFinite(memoryUsed) ? `${Number(memoryUsed).toFixed(1)}%` : "not reported"}</strong></div>
        <div className="resource-stat"><span>{disk?.path || "/data"}</span><strong>{disk && Number.isFinite(disk.used_percent) ? `${disk.used_percent.toFixed(1)}% used` : "not reported"}</strong></div>
      </div>
    </div>
  );
}

function PipelineResources({resourceTab, resources, error, pipelines = resourceTabs, onResourceTabChange}: {
  resourceTab: DashboardPipeline;
  resources: SystemResourcesResponse | null;
  error: string | null;
  pipelines?: DashboardPipeline[];
  onResourceTabChange: (pipeline: DashboardPipeline) => void;
}) {
  const loadAverage = resources?.host.cpu.load_average?.[0];
  return (
    <div className="panel">
      <div className="section-heading"><h2>Pipeline Resources</h2><p>Shared execution node</p></div>
      <div className="resource-tabs" aria-label="Pipeline resource tabs">
        {pipelines.map((tab) => (
          <button aria-label={resourceTabLabel(tab)} className={resourceTab === tab ? "active" : ""} key={tab} type="button" onClick={() => onResourceTabChange(tab)}>
            {tab === "all" ? "All" : compactPipelineName(tab)}
          </button>
        ))}
      </div>
      <div className="resource-stat-grid">
        <div className="resource-stat"><span>Context</span><strong>{resourceTab === "all" ? "All workflows" : compactPipelineName(resourceTab)}</strong></div>
        <div className="resource-stat"><span>1m load</span><strong>{loadAverage == null ? "not reported" : loadAverage.toFixed(2)}</strong></div>
        <div className="resource-stat"><span>Containers</span><strong>{resources?.containers.length ?? 0}</strong></div>
        <div className="resource-stat"><span>Block IO</span><strong>{error ? "unavailable" : resources?.containers[0]?.block_io || "not reported"}</strong></div>
      </div>
    </div>
  );
}

function WorkflowActivity({overview, rows}: {overview: DashboardOverview | null; rows: DashboardRunTrackerRow[]}) {
  const activeRows = rows.filter((row) => isActiveStatus(row.status));
  return (
    <div className="panel" title="Airflow tasks show project stages; pipeline events show the current bioinformatics step.">
      <div className="section-heading"><h2>Workflow Activity</h2><p>Active stages and recent failures</p></div>
      <div className="workflow-activity-list">
        {activeRows.slice(0, 4).map((row) => (
          <div key={row.analysis_id}>
            <StatusBadge status={row.status} size="sm" />
            <span>{row.project_name || row.analysis_id}</span>
            <strong>{row.current_stage_label || "Waiting for workflow events"}</strong>
          </div>
        ))}
        {activeRows.length === 0 ? <p className="empty-state">No active workflows on this page.</p> : null}
        {(overview?.failure_summary || []).slice(0, 2).map((failure) => (
          <Link key={failure.analysis_id} to={`/runs/${encodeURIComponent(failure.analysis_id)}`}>{failure.project_name || failure.analysis_id}</Link>
        ))}
      </div>
    </div>
  );
}

function resourceTabLabel(tab: DashboardPipeline): string {
  if (tab === "all") return "All resource telemetry";
  if (tab === "nipt_docker") return "NIPT resource telemetry";
  return `${compactPipelineName(tab)} resource telemetry`;
}
