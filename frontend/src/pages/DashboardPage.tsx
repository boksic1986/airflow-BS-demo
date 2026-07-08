import {useCallback, useEffect, useMemo, useState} from "react";
import {Link} from "react-router-dom";

import type {
  DashboardOverview,
  DashboardPipeline,
  DashboardRunsResponse,
  IntakeDiscovery,
  SystemResourcesResponse,
} from "../api";
import type {RunTrackerFilter} from "../components/RunTracker";

import {
  getDashboardOverview,
  getDashboardRuns,
  getIntakeStatus,
  getSystemResources,
  submitRun,
  syncAirflow,
} from "../api";
import {RunTracker} from "../components/RunTracker";
import {StatusBadge} from "../components/StatusBadge";
import {compactPipelineName} from "../lib/format";
import {errorMessage} from "../lib/errors";
import {isActiveStatus} from "../lib/status";

const dashboardPipelines: Array<{value: DashboardPipeline; label: string; description: string}> = [
  {value: "all", label: "All pipelines", description: "PGT-A + NIPT Docker"},
  {value: "pgta", label: "PGT-A", description: "Embryo CNV workflow"},
  {value: "nipt_docker", label: "NIPT Docker", description: "Scanned FASTQ chip batches"},
];

const resourceTabs: DashboardPipeline[] = ["all", "pgta", "nipt_docker"];
const trackerLimit = 10;

export function DashboardPage() {
  const [pipeline, setPipeline] = useState<DashboardPipeline>("all");
  const [period] = useState<"7d">("7d");
  const [trackerFilter, setTrackerFilter] = useState<RunTrackerFilter>("all");
  const [trackerKeyword, setTrackerKeyword] = useState("");
  const [trackerOffset, setTrackerOffset] = useState(0);
  const [resourceTab, setResourceTab] = useState<DashboardPipeline>("all");
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [trackerPayload, setTrackerPayload] = useState<DashboardRunsResponse | null>(null);
  const [resources, setResources] = useState<SystemResourcesResponse | null>(null);
  const [intakeItems, setIntakeItems] = useState<IntakeDiscovery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadDashboard = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    setError(null);
    try {
      const [overviewPayload, runsPayload, intakePayload, resourcePayload] = await Promise.all([
        getDashboardOverview({pipeline, period}),
        getDashboardRuns({
          pipeline,
          status: trackerStatusParam(trackerFilter),
          keyword: trackerKeyword.trim() || undefined,
          limit: trackerLimit,
          offset: trackerOffset,
        }),
        getIntakeStatus(pipeline === "all" ? {limit: 20} : {pipeline, limit: 20}).catch(() => ({items: []})),
        getSystemResources().catch(() => null),
      ]);
      setOverview(overviewPayload);
      setTrackerPayload(runsPayload);
      setIntakeItems(intakePayload.items);
      setResources(resourcePayload);
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      if (showSpinner) setLoading(false);
    }
  }, [period, pipeline, trackerFilter, trackerKeyword, trackerOffset]);

  useEffect(() => {
    let disposed = false;
    async function guardedLoad() {
      if (!disposed) await loadDashboard();
    }
    void guardedLoad();
    return () => {
      disposed = true;
    };
  }, [loadDashboard]);

  const activeRunIds = useMemo(
    () => [
      ...new Set(
        (trackerPayload?.items || [])
          .filter((row) => isActiveStatus(row.status))
          .map((row) => row.analysis_id),
      ),
    ],
    [trackerPayload],
  );
  const activeRunKey = activeRunIds.join("|");

  useEffect(() => {
    if (!activeRunKey) return undefined;
    const ids = activeRunKey.split("|");
    let disposed = false;
    async function syncActiveRuns() {
      await Promise.all(ids.map((analysisId) => syncAirflow(analysisId).catch(() => null)));
      if (!disposed) await loadDashboard(false);
    }
    void syncActiveRuns();
    const timer = window.setInterval(() => {
      void syncActiveRuns();
    }, 15000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [activeRunKey, loadDashboard]);

  function handlePipelineChange(nextPipeline: DashboardPipeline) {
    setPipeline(nextPipeline);
    setResourceTab(nextPipeline);
    setTrackerFilter("all");
    setTrackerKeyword("");
    setTrackerOffset(0);
  }

  function handleFilterChange(nextFilter: RunTrackerFilter) {
    setTrackerFilter(nextFilter);
    setTrackerOffset(0);
  }

  function handleKeywordChange(nextKeyword: string) {
    setTrackerKeyword(nextKeyword);
    setTrackerOffset(0);
  }

  async function handleTrackerSubmit(analysisId: string) {
    setActionMessage(null);
    setError(null);
    try {
      const submitted = await submitRun(analysisId);
      setActionMessage(`Submitted ${analysisId} to Airflow${submitted.dag_run_id ? ` as ${submitted.dag_run_id}` : ""}.`);
      await loadDashboard(false);
    } catch (submitError) {
      setError(errorMessage(submitError));
    }
  }

  async function handleTrackerSync(analysisId: string) {
    setActionMessage(null);
    setError(null);
    try {
      await syncAirflow(analysisId);
      setActionMessage(`Synced ${analysisId} from Airflow.`);
      await loadDashboard(false);
    } catch (syncError) {
      setError(errorMessage(syncError));
    }
  }

  const selectedPipeline = dashboardPipelines.find((item) => item.value === pipeline) || dashboardPipelines[0];
  const trackerRows = trackerPayload?.items || [];

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Production task observability</p>
          <h1>Dashboard</h1>
          <p>Pipeline command center for run status, rule-level progress, scanner readiness, and node health.</p>
        </div>
        <Link className="button primary" to="/submit">Submit task</Link>
      </section>

      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {actionMessage ? <div className="success-note" role="status">{actionMessage}</div> : null}
      {loading ? <p className="muted">Loading dashboard...</p> : null}

      <section className="dashboard-command-grid">
        <aside className="pipeline-rail" aria-label="Pipeline selector">
          {dashboardPipelines.map((item) => (
            <button
              aria-label={item.label}
              className={pipeline === item.value ? "active" : ""}
              key={item.value}
              type="button"
              onClick={() => handlePipelineChange(item.value)}
            >
              <strong>{item.label}</strong>
              <span>{item.description}</span>
            </button>
          ))}
        </aside>

        <div className="dashboard-main-column">
          <section className="panel">
            <div className="section-heading split">
              <div>
                <h2>{selectedPipeline.label} status</h2>
                <p>Aggregated by backend; the first screen no longer expands every run into detail/progress calls.</p>
              </div>
              <StatusBadge status={(overview?.totals.failed || 0) > 0 ? "warning" : "success"} />
            </div>
            <div className="dashboard-insight-grid">
              <StatusDistribution overview={overview} />
              <RunTrend overview={overview} />
              <QcFailureSummary overview={overview} />
            </div>
          </section>

          <RunTracker
            filter={trackerFilter}
            keyword={trackerKeyword}
            limit={trackerPayload?.limit || trackerLimit}
            offset={trackerPayload?.offset || trackerOffset}
            rows={trackerRows}
            total={trackerPayload?.total || 0}
            onFilterChange={handleFilterChange}
            onKeywordChange={handleKeywordChange}
            onPageChange={setTrackerOffset}
            onSubmit={(analysisId) => void handleTrackerSubmit(analysisId)}
            onSync={(analysisId) => void handleTrackerSync(analysisId)}
          />
        </div>
      </section>

      <section className="panel">
        <div className="section-heading split">
          <div>
            <h2>Intake scanner</h2>
            <p>Discovery state for configured PGT-A and NIPT Docker roots. Observed/bootstrap is not the same as queued execution.</p>
          </div>
          <StatusBadge status={intakeItems.some((item) => item.submit_state === "submitted") ? "success" : "skipped"} />
        </div>
        <div className="intake-grid">
          {intakeItems.slice(0, 10).map((item) => {
            const display = intakeDisplay(item);
            return (
              <div className="intake-card" key={`${item.pipeline}-${item.root_path}-${item.batch_id}`}>
                <div>
                  <strong>{item.batch_id}</strong>
                  <span>{compactPipelineName(item.pipeline)} / {item.file_count} files / {formatBytes(item.total_bytes)}</span>
                </div>
                <span className={`intake-state-pill ${display.tone}`}>{display.label}</span>
                {item.analysis_id ? <Link to={`/runs/${encodeURIComponent(item.analysis_id)}`}>{item.analysis_id}</Link> : <span className="muted">not submitted</span>}
              </div>
            );
          })}
          {intakeItems.length === 0 ? (
            <p className="empty-state">No intake discovery records yet. Run bootstrap first; keep the Airflow intake DAG paused until roots are reviewed.</p>
          ) : null}
        </div>
      </section>

      <section className="dashboard-ops-grid">
        <ServiceNodeHealth resources={resources} />
        <PipelineResources resourceTab={resourceTab} resources={resources} onResourceTabChange={setResourceTab} />
        <WorkflowActivity overview={overview} rows={trackerRows} />
      </section>
    </div>
  );
}

function trackerStatusParam(filter: RunTrackerFilter): string | undefined {
  if (filter === "all") return undefined;
  if (filter === "active") return "active";
  return filter;
}

function StatusDistribution({overview}: {overview: DashboardOverview | null}) {
  const distribution = overview?.status_distribution || {};
  const segments = [
    {key: "running", label: "Running", tone: "info"},
    {key: "created", label: "Created", tone: "neutral"},
    {key: "success", label: "Success", tone: "success"},
    {key: "failed", label: "Failed", tone: "danger"},
  ];
  const total = Math.max(1, segments.reduce((sum, item) => sum + (distribution[item.key] || 0), 0));
  return (
    <article className="insight-card">
      <div>
        <h3>Status distribution</h3>
        <p>{overview?.totals.runs ?? 0} runs in current context</p>
      </div>
      <div className="status-distribution" aria-label="Status distribution">
        {segments.map((segment) => (
          <span
            className={`segment ${segment.tone}`}
            key={segment.key}
            style={{width: `${Math.max(0, ((distribution[segment.key] || 0) / total) * 100)}%`}}
            title={`${segment.label}: ${distribution[segment.key] || 0}`}
          />
        ))}
      </div>
      <div className="distribution-legend">
        {segments.map((segment) => (
          <span key={segment.key}><i className={segment.tone} />{segment.label}: {distribution[segment.key] || 0}</span>
        ))}
      </div>
    </article>
  );
}

function RunTrend({overview}: {overview: DashboardOverview | null}) {
  const trend = overview?.trend || [];
  const maxRuns = Math.max(1, ...trend.map((item) => item.runs));
  const points = trend.map((item, index) => {
    const x = trend.length <= 1 ? 50 : (index / (trend.length - 1)) * 100;
    const y = 44 - (item.runs / maxRuns) * 34;
    return `${x},${y}`;
  }).join(" ");
  return (
    <article className="insight-card">
      <div>
        <h3>7-day activity</h3>
        <p>Created runs, with failures called out below</p>
      </div>
      <svg aria-label="7-day activity" className="sparkline" preserveAspectRatio="none" viewBox="0 0 100 50">
        <polyline fill="none" points={points || "0,44 100,44"} stroke="#176b87" strokeWidth="3" />
        {trend.map((item, index) => {
          const x = trend.length <= 1 ? 50 : (index / (trend.length - 1)) * 100;
          const y = 44 - (item.runs / maxRuns) * 34;
          return <circle cx={x} cy={y} fill={item.failed ? "#b42318" : "#176b87"} key={item.date} r="2.6" />;
        })}
      </svg>
      <div className="mini-bars">
        {trend.map((item) => (
          <span key={item.date} style={{height: `${Math.max(8, (item.runs / maxRuns) * 42)}px`}} title={`${item.date}: ${item.runs}`} />
        ))}
      </div>
    </article>
  );
}

function QcFailureSummary({overview}: {overview: DashboardOverview | null}) {
  const qc = overview?.qc_summary || {};
  const failures = overview?.failure_summary || [];
  return (
    <article className="insight-card alert-card">
      <div>
        <h3>QC / failure focus</h3>
        <p>{failures.length ? `${failures.length} failed run needs review` : "No failed runs in this view"}</p>
      </div>
      <div className="qc-mini-grid">
        <span>QC pass <strong>{qc.pass || 0}</strong></span>
        <span>QC fail <strong>{qc.fail || 0}</strong></span>
        <span>Unknown <strong>{qc.unknown || 0}</strong></span>
      </div>
      {failures[0] ? (
        <Link className="failure-link" to={`/runs/${encodeURIComponent(failures[0].analysis_id)}`}>
          {failures[0].project_name || failures[0].analysis_id}
        </Link>
      ) : null}
    </article>
  );
}

function ServiceNodeHealth({resources}: {resources: SystemResourcesResponse | null}) {
  const disk = resources?.host.disks.find((item) => item.path === "/data") || resources?.host.disks[0];
  return (
    <div className="panel">
      <div className="section-heading">
        <h2>Service & Node Health</h2>
        <p>{resources ? `Telemetry source: ${resources.source}` : "Resource endpoint unavailable"}</p>
      </div>
      <div className="resource-stat-grid">
        <div className="resource-stat"><span>Backend API</span><StatusBadge status="success" /></div>
        <div className="resource-stat"><span>CPU cores</span><strong>{resources?.host.cpu.cores ?? "not reported"}</strong></div>
        <div className="resource-stat"><span>MEM used</span><strong>{resources ? `${resources.host.memory.used_percent.toFixed(1)}%` : "not reported"}</strong></div>
        <div className="resource-stat"><span>{disk?.path || "/data"}</span><strong>{disk ? `${disk.used_percent.toFixed(1)}% used` : "not reported"}</strong></div>
      </div>
    </div>
  );
}

function PipelineResources({
  resourceTab,
  resources,
  onResourceTabChange,
}: {
  resourceTab: DashboardPipeline;
  resources: SystemResourcesResponse | null;
  onResourceTabChange: (pipeline: DashboardPipeline) => void;
}) {
  const loadAverage = resources?.host.cpu.load_average?.[0];
  const containerCount = resources?.containers.length ?? 0;
  return (
    <div className="panel">
      <div className="section-heading">
        <h2>Pipeline Resources</h2>
        <p>Shared node resources, viewed through the selected workflow context.</p>
      </div>
      <div className="resource-tabs" aria-label="Pipeline resource tabs">
        {resourceTabs.map((tab) => (
          <button
            aria-label={resourceTabLabel(tab)}
            className={resourceTab === tab ? "active" : ""}
            key={tab}
            type="button"
            onClick={() => onResourceTabChange(tab)}
          >
            {tab === "all" ? "All resources" : `${compactPipelineName(tab)} resources`}
          </button>
        ))}
      </div>
      <div className="resource-stat-grid">
        <div className="resource-stat"><span>Context</span><strong>{resourceTab === "all" ? "All workflows" : compactPipelineName(resourceTab)}</strong></div>
        <div className="resource-stat"><span>1m load</span><strong>{loadAverage == null ? "not reported" : loadAverage.toFixed(2)}</strong></div>
        <div className="resource-stat"><span>Containers</span><strong>{containerCount}</strong></div>
        <div className="resource-stat"><span>Block IO</span><strong>{resources?.containers[0]?.block_io || "not reported"}</strong></div>
      </div>
    </div>
  );
}

function resourceTabLabel(tab: DashboardPipeline): string {
  if (tab === "all") return "All resource telemetry";
  if (tab === "nipt_docker") return "NIPT resource telemetry";
  return `${compactPipelineName(tab)} resource telemetry`;
}

function WorkflowActivity({overview, rows}: {overview: DashboardOverview | null; rows: Array<{status: string; current_airflow_task?: string | null; current_pipeline_rule?: string | null}>}) {
  const activeRows = rows.filter((row) => isActiveStatus(row.status));
  return (
    <div className="panel">
      <div className="section-heading">
        <h2>Workflow Activity</h2>
        <p>Airflow stays project-level; Snakemake/runner events show the current bioinformatics rule.</p>
      </div>
      <div className="workflow-activity-list">
        {activeRows.slice(0, 4).map((row, index) => (
          <div key={`${row.current_airflow_task}-${row.current_pipeline_rule}-${index}`}>
            <StatusBadge status={row.status} size="sm" />
            <span>{row.current_airflow_task || "Airflow task pending"}</span>
            <strong>{row.current_pipeline_rule || "No rule events captured"}</strong>
          </div>
        ))}
        {activeRows.length === 0 ? <p className="empty-state">No active workflow tasks in this page.</p> : null}
        {(overview?.failure_summary || []).slice(0, 2).map((failure) => (
          <Link key={failure.analysis_id} to={`/runs/${encodeURIComponent(failure.analysis_id)}`}>
            {failure.project_name || failure.analysis_id}
          </Link>
        ))}
      </div>
    </div>
  );
}

function intakeDisplay(item: IntakeDiscovery): {label: string; tone: "neutral" | "success" | "warning" | "danger" | "muted"} {
  const ready = item.ready_state.toLowerCase();
  const submit = item.submit_state.toLowerCase();
  if (ready === "disabled" || submit === "disabled") return {label: "Disabled", tone: "muted"};
  if (ready === "error" || submit === "error") return {label: "Error", tone: "danger"};
  if (submit === "submitted") return {label: "Auto-submitted", tone: "success"};
  if (submit === "bootstrap") return {label: "Bootstrap observed", tone: "neutral"};
  if (ready === "ready") return {label: "Stable ready", tone: "warning"};
  if (ready === "observed") return {label: "Observed", tone: "neutral"};
  return {label: `${ready || submit || "Unknown"}`, tone: "neutral"};
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let unitIndex = 0;
  let scaled = value;
  while (scaled >= 1024 && unitIndex < units.length - 1) {
    scaled /= 1024;
    unitIndex += 1;
  }
  return `${scaled >= 10 || unitIndex === 0 ? scaled.toFixed(0) : scaled.toFixed(1)} ${units[unitIndex]}`;
}
