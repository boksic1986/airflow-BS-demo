import {useState} from "react";

import type {DashboardOverview, DashboardPipeline, DashboardRunTrackerRow, PlatformResourceSnapshot, PlatformResourcesResponse} from "../../api";
import {StatusBadge} from "../../components/StatusBadge";
import {formatBytes, formatDate} from "../../lib/format";

export function DashboardResourcePanels({resources, loading, error}: {
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
  const cloud = resources?.items.filter((item) => item.resource_type === "sfs") || [];
  const [selectedNodeKey, setSelectedNodeKey] = useState("node-96");
  const selectedNode = nodes.find((node) => node.resource_key === selectedNodeKey)
    || nodes.find((node) => node.resource_key === "node-96")
    || nodes[0];
  const selectedSfs = cloud[0];
  return <section className="dashboard-ops-grid" aria-busy={loading}>
    <section className="panel"><ResourceHeading title="Analysis Node Health" updatedAt={selectedNode?.source_updated_at} />{nodes.length > 0 ? <div className="resource-tabs" role="tablist" aria-label="Analysis node">{nodes.map((node) => <button key={node.resource_key} type="button" role="tab" aria-selected={selectedNode?.resource_key === node.resource_key} className={selectedNode?.resource_key === node.resource_key ? "active" : ""} onClick={() => setSelectedNodeKey(node.resource_key)}>{nodeTabLabel(node)}</button>)}</div> : null}{error ? <div className="inline-error" role="alert">Resources unavailable: {error}</div> : null}<div className="resource-card-list">{selectedNode ? <NodeResource item={selectedNode} /> : <p className="empty-state">Node metrics are not available yet.</p>}</div></section>
    <section className="panel"><ResourceHeading title="Cloud Resources" updatedAt={selectedSfs?.source_updated_at} /><div className="resource-card-list">{cloud.map((item) => <CloudResource key={item.resource_key} item={item} />)}{cloud.length === 0 ? <p className="empty-state">SFS metrics are not available yet. WGS execution is unaffected.</p> : null}</div></section>
    <SfsIoPanel item={selectedSfs} />
  </section>;
}

function ResourceHeading({title, subtitle, updatedAt}: {title: string; subtitle?: string; updatedAt?: string | null}) {
  return <div className="section-heading split resource-panel-heading"><div><h2>{title}</h2>{subtitle ? <p>{subtitle}</p> : null}</div><p className="resource-updated">Updated<br />{formatDate(updatedAt)}</p></div>;
}

function NodeResource({item}: {item: PlatformResourceSnapshot}) {
  const value = item.current;
  const total = Number(value.node_memory_MemTotal_bytes || 0);
  const available = Number(value.node_memory_MemAvailable_bytes || 0);
  const memory = total > 0 ? ((total - available) / total) * 100 : null;
  const cpu = numeric(value.cpu_used_percent);
  const cpuCount = numeric(value.logical_cpu_count);
  const loads = [numeric(value.node_load1), numeric(value.node_load5), numeric(value.node_load15)];
  const loadPercent = cpuCount && loads.every((load) => load != null)
    ? (Math.max(...loads as number[]) / cpuCount) * 100
    : null;
  const loadDetail = loads.map((load) => load == null ? "not reported" : metric(load)).join(" / ");
  return <article className="resource-snapshot"><div className="resource-status-row"><span /><StatusBadge status={item.status} size="sm" /></div><div className="resource-meter-stack"><UtilizationBar label="CPU utilization" percent={cpu} detail={cpu == null ? "not reported" : `${cpu.toFixed(1)}%`} /><UtilizationBar label="Memory utilization" percent={memory} detail={memory == null ? "not reported" : `${memory.toFixed(1)}%`} /><UtilizationBar label="Load 1 / 5 / 15" percent={loadPercent} detail={loadDetail} tone={loadTone(loadPercent)} /></div>{item.error_message ? <p className="inline-error">{item.error_message}</p> : null}</article>;
}

function nodeTabLabel(item: PlatformResourceSnapshot): string {
  const suffix = item.resource_key.match(/(\d+)$/)?.[1];
  return suffix ? `172.17.61.${suffix}` : item.display_name;
}

function CloudResource({item}: {item: PlatformResourceSnapshot}) {
  const value = item.current;
  const percent = numeric(value.capacity_used_percent);
  const used = numeric(value.capacity_used_bytes);
  const total = percent != null && percent > 0 && used != null ? used / (percent / 100) : null;
  const detail = used != null && total != null
    ? `${formatBytes(used)} / ${formatBytes(total)}`
    : percent == null ? "not reported" : `${percent.toFixed(1)}% used`;
  return <article className="resource-snapshot"><div><strong className="resource-tag">{item.display_name}</strong><StatusBadge status={item.status} size="sm" /></div><div className="resource-meter-stack"><UtilizationBar label="SFS capacity utilization" percent={percent} detail={detail} /></div><div className="heavy-slot-reserved" aria-hidden="true" /></article>;
}

function UtilizationBar({label, percent, detail, tone = "healthy"}: {label: string; percent: number | null; detail: string; tone?: "healthy" | "warning" | "danger"}) {
  const normalized = percent == null ? 0 : Math.max(0, Math.min(100, percent));
  return <div className="resource-meter-row"><div><span>{label.replace(" utilization", "")}</span><strong>{detail}</strong></div><div className={`resource-meter ${tone}`} role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent == null ? undefined : Math.round(normalized)} aria-valuetext={detail}><span style={{width: `${normalized}%`}} /></div></div>;
}

function loadTone(percent: number | null): "healthy" | "warning" | "danger" {
  if (percent == null || percent < 70) return "healthy";
  if (percent < 100) return "warning";
  return "danger";
}

function SfsIoPanel({item}: {item?: PlatformResourceSnapshot}) {
  const [period, setPeriod] = useState<"1h" | "24h" | "7d">("24h");
  const allPoints = (item?.history || []).map((point) => ({
    at: String(point.at || ""),
    read: numeric(point.read_bps) || 0,
    write: numeric(point.write_bps) || 0,
  }));
  const latestAt = Math.max(0, ...allPoints.map((point) => Date.parse(point.at)).filter(Number.isFinite));
  const hours = period === "7d" ? 7 * 24 : period === "1h" ? 1 : 24;
  const points = allPoints.filter((point) => {
    const observedAt = Date.parse(point.at);
    return !latestAt || !Number.isFinite(observedAt) || observedAt >= latestAt - hours * 60 * 60 * 1000;
  });
  const current = item?.current || {};
  return <section className="panel"><div className="section-heading split"><h2>SFS I/O</h2><div className="period-selector compact-period-selector" role="tablist" aria-label="SFS I/O period">{(["1h", "24h", "7d"] as const).map((value) => <button key={value} type="button" role="tab" aria-selected={period === value} className={period === value ? "active" : ""} onClick={() => setPeriod(value)}>{value}</button>)}</div></div>{points.length > 1 ? <BandwidthChart points={points} /> : <p className="empty-state">SFS I/O history is not available yet.</p>}<div className="sfs-io-current"><span><i className="sfs-read-dot" />Read <strong>{formatRate(current.read_bps)}</strong></span><span><i className="sfs-write-dot" />Write <strong>{formatRate(current.write_bps)}</strong></span><span>Total <strong>{formatRate(current.total_bps)}</strong></span><span>Current IOPS <strong>{metric(current.iops)}</strong></span></div><p className="resource-unit-note">Bandwidth uses binary units (GiB/s).</p></section>;
}

function BandwidthChart({points}: {points: Array<{at: string; read: number; write: number}>}) {
  const maximum = Math.max(1, ...points.flatMap((point) => [point.read, point.write]));
  const coordinates = (key: "read" | "write") => points.map((point, index) => {
    const x = points.length === 1 ? 0 : (index / (points.length - 1)) * 300;
    const y = 92 - (point[key] / maximum) * 82;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return <div className="sfs-chart-layout"><div className="sfs-chart-y-axis" aria-label="SFS bandwidth Y axis"><span>{formatRate(maximum)}</span><span>{formatRate(maximum / 2)}</span><span>{formatRate(0)}</span></div><svg className="sfs-io-chart" viewBox="0 0 300 100" role="img" aria-label="SFS read and write bandwidth history" preserveAspectRatio="none"><line x1="0" y1="92" x2="300" y2="92" className="sfs-chart-axis" /><line x1="0" y1="51" x2="300" y2="51" className="sfs-chart-grid" /><line x1="0" y1="10" x2="300" y2="10" className="sfs-chart-grid" /><polyline points={coordinates("read")} className="sfs-chart-read" /><polyline points={coordinates("write")} className="sfs-chart-write" /></svg></div>;
}

function formatRate(value: unknown): string {
  const number = numeric(value);
  return number == null ? "not reported" : `${formatBytes(number)}/s`;
}

function numeric(value: unknown): number | null {
  const number = Number(value);
  return value !== null && value !== "" && Number.isFinite(number) ? number : null;
}

function metric(value: unknown, unit = ""): string {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(number % 1 ? 1 : 0)}${unit}` : "not reported";
}
