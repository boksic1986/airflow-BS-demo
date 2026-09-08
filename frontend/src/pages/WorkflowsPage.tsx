import {useEffect, useState} from "react";
import type {RunSummary, WorkflowCatalogItem} from "../api";
import {getWorkflowCatalog, listRuns} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {errorMessage} from "../lib/errors";
import {formatDate} from "../lib/format";

export function WorkflowsPage() {
  const capabilities = usePlatformCapabilities();
  const [items, setItems] = useState<WorkflowCatalogItem[]>([]);
  const [recentRuns, setRecentRuns] = useState<Record<string, RunSummary[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    Promise.all(visibleItems.map(async (workflow) => [
      workflow.id,
      (await listRuns({pipeline: workflow.id, sort: "created_desc", limit: 5})).items,
    ] as const))
      .then((entries) => { if (!disposed) setRecentRuns(Object.fromEntries(entries)); })
      .catch((loadError) => { if (!disposed) setError(errorMessage(loadError)); });
    return () => { disposed = true; };
  }, [visibleIds]);

  return (
    <div className="page-stack workflow-catalog-page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Live workflow status</p>
          <h1>Workflow Catalog</h1>
          <p>Only workflows deployed in the current environment are shown.</p>
        </div>
      </section>
      {error ? <div className="inline-error" role="alert">Workflow catalog unavailable: {error}</div> : null}
      {loading ? <p className="muted panel-loading">Loading deployed workflows...</p> : null}
      <section className="workflow-catalog-grid">
        {visibleItems.map((workflow) => <WorkflowCatalogCard key={workflow.id} workflow={workflow} recentRuns={recentRuns[workflow.id] || []} />)}
      </section>
      {!loading && !error && visibleItems.length === 0 ? <p className="empty-state">No deployed workflow state is available.</p> : null}
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
