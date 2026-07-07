import {useEffect, useMemo, useState} from "react";
import {Link} from "react-router-dom";

import type {HealthResponse, RunSummary} from "../api";

import {getAirflowHealth, getDbHealth, getHealth, listRuns} from "../api";
import {MetricCard} from "../components/MetricCard";
import {PipelineCard} from "../components/PipelineCard";
import {RunTable} from "../components/RunTable";
import {StatusBadge} from "../components/StatusBadge";
import {compactPipelineName} from "../lib/format";
import {errorMessage} from "../lib/errors";
import {normalizeStatus, statusPriority} from "../lib/status";
import {resourceOverview, workflowTemplates} from "../mocks/platform";

type HealthState = {
  backend: HealthResponse | null;
  db: HealthResponse | null;
  airflow: HealthResponse | null;
};

export function DashboardPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [health, setHealth] = useState<HealthState>({backend: null, db: null, airflow: null});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    async function loadDashboard() {
      setLoading(true);
      setError(null);
      try {
        const [runPayload, backend, db, airflow] = await Promise.all([
          listRuns(),
          getHealth().catch(() => null),
          getDbHealth().catch(() => null),
          getAirflowHealth().catch(() => null),
        ]);
        if (disposed) return;
        setRuns(runPayload.items);
        setHealth({backend, db, airflow});
      } catch (loadError) {
        if (!disposed) setError(errorMessage(loadError));
      } finally {
        if (!disposed) setLoading(false);
      }
    }
    void loadDashboard();
    return () => {
      disposed = true;
    };
  }, []);

  const counts = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    return {
      today: runs.filter((run) => (run.created_at || "").slice(0, 10) === today).length,
      running: runs.filter((run) => ["running", "submitted", "queued", "scheduled"].includes(normalizeStatus(run.status))).length,
      failed: runs.filter((run) => normalizeStatus(run.status) === "failed").length,
      success: runs.filter((run) => normalizeStatus(run.status) === "success").length,
      queued: runs.filter((run) => normalizeStatus(run.status) === "queued").length,
    };
  }, [runs]);
  const failedRuns = runs.filter((run) => normalizeStatus(run.status) === "failed").slice(0, 5);
  const completedRuns = runs.filter((run) => normalizeStatus(run.status) === "success").slice(0, 5);

  const pipelineCounts = workflowTemplates.map((template) => {
    const pipelineRuns = runs.filter((run) => run.pipeline === template.id);
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
          <p>Runs, failures, queue pressure, QC alerts, and service health for the demo platform.</p>
        </div>
        <Link className="button primary" to="/submit">Submit task</Link>
      </section>

      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {loading ? <p className="muted">Loading dashboard...</p> : null}

      <section className="metric-grid" aria-label="Run status summary">
        <MetricCard title="Today submitted" value={counts.today} status="created" description="Runs created today in displayed timezone" />
        <MetricCard title="Running" value={counts.running} status="running" description="submitted/running/queued" />
        <MetricCard title="Failed runs" value={counts.failed} status={counts.failed ? "failed" : "success"} description="Needs diagnostic review" />
        <MetricCard title="Success" value={counts.success} status="success" description="Completed workflow status" />
        <MetricCard title="Queued" value={counts.queued} status="queued" description="Waiting for execution" />
      </section>

      <section className="split-grid">
        <div className="panel">
          <div className="section-heading split">
            <h2>Recent failed runs</h2>
            <Link to="/failures">View failures</Link>
          </div>
          <RunTable runs={failedRuns} compact emptyLabel="No failed runs in the current API response." />
        </div>
        <div className="panel">
          <div className="section-heading split">
            <h2>Recent completed runs</h2>
            <Link to="/runs">View runs</Link>
          </div>
          <RunTable runs={completedRuns} compact emptyLabel="No completed runs in the current API response." />
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Pipeline operating state</h2>
          <p>Live backend runs are mixed with clearly labeled demo/mock workflow templates.</p>
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
      </section>

      <section className="split-grid">
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
            <h2>Mock resource overview</h2>
            <p>Displayed as demo telemetry until real scheduler/resource APIs exist.</p>
          </div>
          <div className="metric-grid compact">
            {resourceOverview.map((metric) => (
              <MetricCard key={metric.title} {...metric} />
            ))}
          </div>
        </div>
      </section>

      <section className="card-grid">
        {workflowTemplates.slice(0, 3).map((pipeline) => (
          <PipelineCard key={pipeline.id} pipeline={pipeline} />
        ))}
      </section>
    </div>
  );
}
