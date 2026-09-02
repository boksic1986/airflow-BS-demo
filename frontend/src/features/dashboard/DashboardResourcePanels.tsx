import {useState} from "react";
import {Link} from "react-router-dom";

import type {DashboardOverview, DashboardPipeline, DashboardRunTrackerRow, PlatformResourceSnapshot, PlatformResourcesResponse} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {formatBytes, formatDate} from "../../lib/format";
import {isActiveStatus} from "../../lib/status";

export function DashboardResourcePanels({resources, overview, rows, loading, error}: {
  resources: PlatformResourcesResponse | null;
  resourceTab: DashboardPipeline;
  overview: DashboardOverview | null;
  rows: DashboardRunTrackerRow[];
  loading: boolean;
  error: string | null;
  pipelines?: DashboardPipeline[];
  onResourceTabChange: (pipeline: DashboardPipeline) => void;
}) {
  const nodes = (resources?.items.filter((item) => item.resource_type === "node") || [])
    .sort((left, right) => left.resource_key.localeCompare(right.resource_key));
  const cloud = resources?.items.filter((item) => item.resource_type !== "node") || [];
  const [selectedNodeKey, setSelectedNodeKey] = useState("node-96");
  const selectedNode = nodes.find((node) => node.resource_key === selectedNodeKey)
    || nodes.find((node) => node.resource_key === "node-96")
    || nodes[0];
  return <section className="dashboard-ops-grid" aria-busy={loading}>
    <section className="panel"><div className="section-heading"><h2>Analysis Node Health</h2><p>172.17.61.96 and 172.17.61.97</p></div>{nodes.length > 0 ? <div className="resource-tabs" role="tablist" aria-label="Analysis node">{nodes.map((node) => <button key={node.resource_key} type="button" role="tab" aria-selected={selectedNode?.resource_key === node.resource_key} className={selectedNode?.resource_key === node.resource_key ? "active" : ""} onClick={() => setSelectedNodeKey(node.resource_key)}>{nodeTabLabel(node)}</button>)}</div> : null}{error ? <div className="inline-error" role="alert">Resources unavailable: {error}</div> : null}<div className="resource-card-list">{selectedNode ? <NodeResource item={selectedNode} /> : <p className="empty-state">Node metrics are not available yet.</p>}</div></section>
    <section className="panel"><div className="section-heading"><h2>Cloud Resources</h2><p>SFS I/O/capacity and OBS usage snapshots</p></div><div className="resource-card-list">{cloud.map((item) => <CloudResource key={item.resource_key} item={item} />)}{cloud.length === 0 ? <p className="empty-state">Cloud metrics are not available yet. WGS execution is unaffected.</p> : null}</div></section>
    <WorkflowActivity overview={overview} rows={rows} />
  </section>;
}

function NodeResource({item}: {item: PlatformResourceSnapshot}) {
  const value = item.current;
  const total = Number(value.node_memory_MemTotal_bytes || 0);
  const available = Number(value.node_memory_MemAvailable_bytes || 0);
  const memory = total > 0 ? ((total - available) / total) * 100 : null;
  return <article className="resource-snapshot"><div><strong>{item.display_name}</strong><StatusBadge status={item.status} size="sm" /></div><dl><div><dt>CPU / load 1/5/15</dt><dd>{metric(value.cpu_used_percent, "%")} / {metric(value.node_load1)} / {metric(value.node_load5)} / {metric(value.node_load15)}</dd></div><div><dt>Memory</dt><dd>{memory == null ? "not reported" : `${memory.toFixed(1)}% used`}</dd></div><div><dt>Updated</dt><dd>{formatDate(item.source_updated_at)}</dd></div></dl>{item.error_message ? <p className="inline-error">{item.error_message}</p> : null}</article>;
}

function nodeTabLabel(item: PlatformResourceSnapshot): string {
  const suffix = item.resource_key.match(/(\d+)$/)?.[1];
  return suffix ? `.${suffix}` : item.display_name;
}

function CloudResource({item}: {item: PlatformResourceSnapshot}) {
  const value = item.current;
  return <article className="resource-snapshot"><div><strong>{item.display_name}</strong><StatusBadge status={item.status} size="sm" /></div><dl>{item.resource_type === "obs" ? <><div><dt>Used capacity</dt><dd>{formatBytes(Number(value.used_bytes || 0))}</dd></div><div><dt>Objects</dt><dd>{metric(value.object_count)}</dd></div></> : <><div><dt>Capacity used</dt><dd>{metric(value.capacity_used_percent, "%")}</dd></div><div><dt>Read / write bandwidth</dt><dd>{formatBytes(Number(value.read_bps || 0))}/s / {formatBytes(Number(value.write_bps || 0))}/s</dd></div><div><dt>IOPS</dt><dd>{metric(value.iops)}</dd></div></>}<div><dt>Updated</dt><dd>{formatDate(item.source_updated_at)}</dd></div></dl></article>;
}

function WorkflowActivity({overview, rows}: {overview: DashboardOverview | null; rows: DashboardRunTrackerRow[]}) {
  const activeRows = rows.filter((row) => isActiveStatus(row.status));
  return <div className="panel"><div className="section-heading"><h2>Workflow Activity</h2><p>Active WGS stages and recent failures</p></div><div className="workflow-activity-list">{activeRows.slice(0, 4).map((row) => <div key={row.analysis_id}><StatusBadge status={row.status} size="sm" /><span>{row.batch_no || row.project_name || row.analysis_id}</span><strong>{row.current_stage_label || "WGS stage unavailable"}</strong></div>)}{activeRows.length === 0 ? <p className="empty-state">No active workflows on this page.</p> : null}{(overview?.failure_summary || []).slice(0, 2).map((failure) => <Link key={failure.analysis_id} to={`/runs/${encodeURIComponent(failure.analysis_id)}`}>{failure.project_name || failure.analysis_id}</Link>)}</div></div>;
}

function metric(value: unknown, unit = ""): string {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(number % 1 ? 1 : 0)}${unit}` : "not reported";
}
