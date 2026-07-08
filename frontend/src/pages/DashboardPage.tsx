import {useCallback, useEffect, useMemo, useState} from "react";
import {Link} from "react-router-dom";

import type {HealthResponse, IntakeDiscovery, RunSummary} from "../api";
import type {RunTrackerFilter, RunTrackerItem} from "../components/RunTracker";

import {getAirflowHealth, getDbHealth, getHealth, getIntakeStatus, getRunDetail, getRunProgress, getRunRules, listRuns, submitRun, syncAirflow} from "../api";
import {MetricCard} from "../components/MetricCard";
import {RunTracker} from "../components/RunTracker";
import {StatusBadge} from "../components/StatusBadge";
import {compactPipelineName} from "../lib/format";
import {errorMessage} from "../lib/errors";
import {isActiveStatus, normalizeStatus, statusPriority} from "../lib/status";
import {deployedWorkflowTemplates, resourceOverview} from "../mocks/platform";

type HealthState = {
  backend: HealthResponse | null;
  db: HealthResponse | null;
  airflow: HealthResponse | null;
};
const visiblePipelines = new Set<string>(deployedWorkflowTemplates.map((pipeline) => pipeline.id));

export function DashboardPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [trackerItems, setTrackerItems] = useState<RunTrackerItem[]>([]);
  const [intakeItems, setIntakeItems] = useState<IntakeDiscovery[]>([]);
  const [health, setHealth] = useState<HealthState>({backend: null, db: null, airflow: null});
  const [trackerFilter, setTrackerFilter] = useState<RunTrackerFilter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadDashboard = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoading(true);
    setError(null);
    try {
      const [runPayload, backend, db, airflow, intake] = await Promise.all([
        listRuns({limit: 50, offset: 0}),
        getHealth().catch(() => null),
        getDbHealth().catch(() => null),
        getAirflowHealth().catch(() => null),
        getIntakeStatus({limit: 20}).catch(() => ({items: []})),
      ]);
      const deployedRuns = runPayload.items.filter((run) => visiblePipelines.has(run.pipeline));
      const enriched = await Promise.all(
        deployedRuns.slice(0, 20).map(async (run) => {
          const [detail, progress, rulesPayload] = await Promise.all([
            getRunDetail(run.analysis_id).catch(() => null),
            getRunProgress(run.analysis_id).catch(() => null),
            getRunRules(run.analysis_id).catch(() => ({items: []})),
          ]);
          return {run, detail, progress, rules: progress?.rule_events || rulesPayload.items};
        }),
      );
      setRuns(deployedRuns);
      setTrackerItems(enriched);
      setIntakeItems(intake.items);
      setHealth({backend, db, airflow});
    } catch (loadError) {
      setError(errorMessage(loadError));
    } finally {
      if (showSpinner) setLoading(false);
    }
  }, []);

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
        trackerItems
          .filter((item) => isActiveStatus(item.detail?.status || item.run.status))
          .map((item) => item.run.analysis_id),
      ),
    ],
    [trackerItems],
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

  const deployedRuns = useMemo(() => runs.filter((run) => visiblePipelines.has(run.pipeline)), [runs]);

  const counts = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    return {
      today: deployedRuns.filter((run) => (run.created_at || "").slice(0, 10) === today).length,
      running: deployedRuns.filter((run) => ["running", "submitted", "queued", "scheduled"].includes(normalizeStatus(run.status))).length,
      failed: deployedRuns.filter((run) => normalizeStatus(run.status) === "failed").length,
      success: deployedRuns.filter((run) => normalizeStatus(run.status) === "success").length,
      queued: deployedRuns.filter((run) => normalizeStatus(run.status) === "queued").length,
    };
  }, [deployedRuns]);

  const pipelineCounts = deployedWorkflowTemplates.map((template) => {
    const pipelineRuns = deployedRuns.filter((run) => run.pipeline === template.id);
    return {
      ...template,
      status: pipelineRuns.sort((a, b) => statusPriority(a.status) - statusPriority(b.status))[0]?.status || template.implementationStatus,
      total: pipelineRuns.length,
    };
  });

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Production task observability</p>
          <h1>Dashboard</h1>
          <p>PGT-A and NIPT Docker runs, failures, QC alerts, and service health for the current demo deployment.</p>
        </div>
        <Link className="button primary" to="/submit">Submit task</Link>
      </section>

      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {actionMessage ? <div className="success-note" role="status">{actionMessage}</div> : null}
      {loading ? <p className="muted">Loading dashboard...</p> : null}

      <section className="metric-grid" aria-label="Run status summary">
        <MetricCard title="Today submitted" value={counts.today} status="created" description="Runs created today in displayed timezone" />
        <MetricCard title="Running" value={counts.running} status="running" description="submitted/running/queued" />
        <MetricCard title="Failed runs" value={counts.failed} status={counts.failed ? "failed" : "success"} description="Needs diagnostic review" />
        <MetricCard title="Success" value={counts.success} status="success" description="Completed workflow status" />
        <MetricCard title="Queued" value={counts.queued} status="queued" description="Waiting for execution" />
      </section>

      <RunTracker
        filter={trackerFilter}
        items={trackerItems}
        onFilterChange={setTrackerFilter}
        onSubmit={(analysisId) => void handleTrackerSubmit(analysisId)}
        onSync={(analysisId) => void handleTrackerSync(analysisId)}
      />

      <section className="panel">
        <div className="section-heading split">
          <div>
            <h2>Intake auto scanner</h2>
            <p>Read-only discovery status for PGT-A and NIPT Docker batch roots. Automatic submit is handled by the Airflow intake DAG.</p>
          </div>
          <StatusBadge status={intakeItems.some((item) => item.submit_state === "submitted") ? "success" : "queued"} />
        </div>
        <div className="pipeline-status-grid">
          {intakeItems.slice(0, 8).map((item) => (
            <div className="pipeline-status-row intake-status-row" key={`${item.pipeline}-${item.root_path}-${item.batch_id}`}>
              <strong>{compactPipelineName(item.pipeline)}</strong>
              <span>{item.batch_id}</span>
              <span>{item.file_count} files / {formatBytes(item.total_bytes)}</span>
              <StatusBadge status={intakeStatusBadge(item)} />
              {item.analysis_id ? <Link to={`/runs/${encodeURIComponent(item.analysis_id)}`}>{item.analysis_id}</Link> : <span>not submitted</span>}
            </div>
          ))}
          {intakeItems.length === 0 ? (
            <p className="empty-state">No intake discovery records yet. Run bootstrap, then enable the Airflow scanner DAG after existing batches are observed.</p>
          ) : null}
        </div>
      </section>

      <section className="dashboard-bottom-grid">
        <div className="panel">
          <div className="section-heading">
            <h2>Service health</h2>
          </div>
          <div className="health-list">
            <div><span>Backend API</span><StatusBadge status={health.backend?.status || "unknown"} /></div>
            <div><span>Biodemo database</span><StatusBadge status={health.db?.status || "unknown"} /></div>
            <div><span>Airflow scheduler</span><StatusBadge status={health.airflow?.airflow?.scheduler?.status || "unknown"} /></div>
            <div><span>Airflow metadatabase</span><StatusBadge status={health.airflow?.airflow?.metadatabase?.status || "unknown"} /></div>
          </div>
        </div>
        <div className="panel">
          <div className="section-heading">
            <h2>PGT-A / NIPT resource overview</h2>
            <p>Displayed as demo telemetry until real scheduler/resource APIs exist.</p>
          </div>
          <div className="metric-grid compact">
            {resourceOverview.map((metric) => (
              <MetricCard key={metric.title} {...metric} />
            ))}
          </div>
        </div>
        <div className="panel">
          <div className="section-heading">
            <h2>Deployed workflows</h2>
            <p>Current deployment scope includes PGT-A and NIPT Docker.</p>
          </div>
          <div className="pipeline-status-grid">
            {pipelineCounts.map((pipeline) => (
              <div className="pipeline-status-row" key={pipeline.id}>
                <strong>{compactPipelineName(pipeline.id)}</strong>
                <span>{pipeline.total} visible runs</span>
                <StatusBadge status={pipeline.status} />
              </div>
            ))}
          </div>
          <div className="workflow-step-list">
            {deployedWorkflowTemplates.map((pipeline) => (
              <div key={pipeline.id}>
                <strong>{pipeline.name}</strong>
                <span>{pipeline.dagId} · {pipeline.version}</span>
                <ol>
                  {pipeline.steps.map((step) => (
                    <li key={step.name}>
                      <span>{step.name}</span>
                      <StatusBadge status={step.status} size="sm" />
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function intakeStatusBadge(item: IntakeDiscovery): string {
  if (item.submit_state === "submitted") return "success";
  if (item.ready_state === "ready") return "warning";
  if (item.ready_state === "observed") return "queued";
  return item.submit_state || item.ready_state || "unknown";
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
