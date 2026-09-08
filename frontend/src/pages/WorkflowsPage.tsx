import {useEffect, useMemo, useState} from "react";
import {Link} from "react-router-dom";

import type {RunSummary, WorkflowCatalogItem} from "../api";
import {getWorkflowCatalog, listRuns} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {LifecycleStatusBadge} from "../features/run-detail/DataLifecyclePanel";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {errorMessage} from "../lib/errors";
import {formatDate} from "../lib/format";

const PAGE_SIZE = 20;
type LifecycleKey = "cloud_release" | "downstream_release";

export function WorkflowsPage() {
  const capabilities = usePlatformCapabilities();
  const [items, setItems] = useState<WorkflowCatalogItem[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pipelineFilter, setPipelineFilter] = useState("all");
  const [cloudFilter, setCloudFilter] = useState("all");
  const [deliveryFilter, setDeliveryFilter] = useState("all");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    let disposed = false;
    getWorkflowCatalog()
      .then((payload) => { if (!disposed) setItems(payload.items); })
      .catch((loadError) => { if (!disposed) setError(errorMessage(loadError)); })
      .finally(() => { if (!disposed) setLoading(false); });
    return () => { disposed = true; };
  }, []);

  const visibleItems = items.filter((workflow) => capabilities.isDeployed(workflow.id));
  const visibleIds = visibleItems.map((workflow) => workflow.id).join(",");

  useEffect(() => {
    if (!visibleIds) return;
    let disposed = false;
    listRuns({pipeline: "deployed", sort: "created_desc", limit: 200})
      .then((payload) => { if (!disposed) setRuns(payload.items); })
      .catch((loadError) => { if (!disposed) setError(errorMessage(loadError)); });
    return () => { disposed = true; };
  }, [visibleIds]);

  useEffect(() => { setPage(0); }, [pipelineFilter, cloudFilter, deliveryFilter, keyword]);

  const filteredRuns = useMemo(() => runs.filter((run) => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return (pipelineFilter === "all" || run.pipeline === pipelineFilter)
      && (cloudFilter === "all" || lifecycleStatus(run, "cloud_release") === cloudFilter)
      && (deliveryFilter === "all" || lifecycleStatus(run, "downstream_release") === deliveryFilter)
      && (!normalizedKeyword || [run.project_name, run.batch_no, run.analysis_id]
        .some((value) => String(value || "").toLowerCase().includes(normalizedKeyword)));
  }), [runs, pipelineFilter, cloudFilter, deliveryFilter, keyword]);
  const pageRuns = filteredRuns.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="page-stack workflow-catalog-page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Live workflow status</p>
          <h1>Workflow Catalog</h1>
          <p>Deployed pipeline capabilities and recent workflow, cloud release, and delivery state.</p>
        </div>
      </section>
      {error ? <div className="inline-error" role="alert">Workflow catalog unavailable: {error}</div> : null}
      {loading ? <p className="muted panel-loading">Loading deployed workflows...</p> : null}
      <section className="workflow-catalog-grid">
        {visibleItems.map((workflow) => <WorkflowCatalogCard key={workflow.id} workflow={workflow} recentRuns={runs.filter((run) => run.pipeline === workflow.id).slice(0, 3)} />)}
      </section>
      {!loading && !error && visibleItems.length === 0 ? <p className="empty-state">No deployed workflow state is available.</p> : null}
      {visibleItems.length > 0 ? <section className="panel workflow-lifecycle-panel">
        <div className="section-heading">
          <h2>Run lifecycle</h2>
          <p>Read-only status for workflow completion, cloud release, and result delivery.</p>
        </div>
        <div className="workflow-lifecycle-filters">
          <label className="field"><span>Pipeline</span><select value={pipelineFilter} onChange={(event) => setPipelineFilter(event.target.value)}><option value="all">All deployed</option>{visibleItems.map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label>
          <LifecycleFilter label="Cloud release status" value={cloudFilter} onChange={setCloudFilter} />
          <LifecycleFilter label="Result delivery status" value={deliveryFilter} onChange={setDeliveryFilter} />
          <label className="field workflow-lifecycle-keyword"><span>Keyword</span><input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="project, batch, or run ID" /></label>
        </div>
        <div className="table-wrap">
          <table className="data-table workflow-lifecycle-table" aria-label="Run lifecycle">
            <thead><tr><th>Project / batch</th><th>Workflow</th><th>Cloud release</th><th>Result delivery</th><th>Last updated</th></tr></thead>
            <tbody>
              {pageRuns.map((run) => <tr key={run.analysis_id}>
                <td><Link className="resource-link" to={`/runs/${encodeURIComponent(run.analysis_id)}`}>{run.project_name || run.analysis_id}</Link><Link className="resource-link secondary" to={`/runs/${encodeURIComponent(run.analysis_id)}`}>{run.batch_no || run.analysis_id}</Link></td>
                <td><StatusBadge status={run.workflow_status || run.status} /><span className="workflow-lifecycle-label">{run.workflow_label || run.status}</span></td>
                <td><LifecycleBadge run={run} lifecycleKey="cloud_release" successLabel="SFS released" runningLabel="SFS release running" /></td>
                <td><LifecycleBadge run={run} lifecycleKey="downstream_release" successLabel="Delivered" runningLabel="Delivery running" /></td>
                <td>{formatDate(lastLifecycleUpdate(run))}</td>
              </tr>)}
              {pageRuns.length === 0 ? <tr><td colSpan={5} className="empty-cell">No runs match the lifecycle filters.</td></tr> : null}
            </tbody>
          </table>
        </div>
        <div className="pagination-controls"><span>{filteredRuns.length === 0 ? "0-0" : `${page * PAGE_SIZE + 1}-${Math.min((page + 1) * PAGE_SIZE, filteredRuns.length)}`} of {filteredRuns.length}</span><div><button type="button" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>Previous</button><button type="button" disabled={(page + 1) * PAGE_SIZE >= filteredRuns.length} onClick={() => setPage((value) => value + 1)}>Next</button></div></div>
      </section> : null}
    </div>
  );
}

function WorkflowCatalogCard({workflow, recentRuns}: {workflow: WorkflowCatalogItem; recentRuns: RunSummary[]}) {
  return (
    <article className="panel workflow-catalog-card">
      <div className="section-heading split">
        <div><p className="eyebrow">{workflow.dag_id}</p><h2>{workflow.display_name}</h2><p>{workflow.version ? `Version ${workflow.version}` : "Version managed by adapter"}</p></div>
        <StatusBadge status={workflow.submit_enabled ? "available" : "disabled"} />
      </div>
      <dl className="definition-grid compact">
        <div><dt>Pipeline ID</dt><dd>{workflow.id}</dd></div>
        <div><dt>Execution targets</dt><dd>{workflow.execution_targets.join(", ") || "Not declared"}</dd></div>
        <div><dt>Capabilities</dt><dd>{workflow.capabilities.join(", ") || "None"}</dd></div>
        <div><dt>Submission</dt><dd>{workflow.submit_enabled ? "Available" : "Unavailable"}</dd></div>
      </dl>
      <div className="workflow-recent-runs">
        <h3>Recent runs</h3>
        {recentRuns.map((run) => <div className="workflow-recent-run" key={run.analysis_id}>
          <div><strong>{run.batch_no || run.analysis_id}</strong><small>{run.project_name || run.analysis_id}</small></div>
          <div><StatusBadge status={run.workflow_status || run.status} /><span>{run.workflow_label || run.status}</span></div>
          <time dateTime={run.created_at || undefined}>{formatDate(run.created_at)}</time>
        </div>)}
        {recentRuns.length === 0 ? <p className="empty-state">No recent run records.</p> : null}
      </div>
    </article>
  );
}

function LifecycleFilter({label, value, onChange}: {label: string; value: string; onChange: (value: string) => void}) {
  return <label className="field"><span>{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}><option value="all">All</option><option value="not_started">Not started</option><option value="pending">Pending</option><option value="running">Running</option><option value="success">Success</option><option value="failed">Failed</option><option value="not_applicable">Not applicable</option><option value="unavailable">Unavailable</option></select></label>;
}

function LifecycleBadge({run, lifecycleKey, successLabel, runningLabel}: {run: RunSummary; lifecycleKey: LifecycleKey; successLabel: string; runningLabel: string}) {
  const item = run.lifecycle?.[lifecycleKey];
  const badge = item ? <LifecycleStatusBadge item={item} successLabel={successLabel} runningLabel={runningLabel} /> : <StatusBadge status="unavailable" />;
  return item?.status === "failed" ? <Link className="lifecycle-failed-link" to={`/runs/${encodeURIComponent(run.analysis_id)}`} aria-label={`Open ${run.batch_no || run.analysis_id} failure`}>{badge}</Link> : badge;
}

function lifecycleStatus(run: RunSummary, key: LifecycleKey): string {
  return run.lifecycle?.[key]?.status || "unavailable";
}

function lastLifecycleUpdate(run: RunSummary): string | null {
  const candidates = [run.lifecycle?.cloud_release.updated_at, run.lifecycle?.downstream_release.updated_at, run.pipeline_finished_at, run.ended_at, run.started_at, run.submitted_at, run.created_at].filter(Boolean) as string[];
  return candidates.sort((left, right) => Date.parse(right) - Date.parse(left))[0] || null;
}
