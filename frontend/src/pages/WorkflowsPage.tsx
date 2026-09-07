import {useEffect, useState} from "react";
import type {WorkflowCatalogItem} from "../api";
import {getWorkflowCatalog} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {errorMessage} from "../lib/errors";

export function WorkflowsPage() {
  const capabilities = usePlatformCapabilities();
  const [items, setItems] = useState<WorkflowCatalogItem[]>([]);
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
        {visibleItems.map((workflow) => <WorkflowCatalogCard key={workflow.id} workflow={workflow} />)}
      </section>
      {!loading && !error && visibleItems.length === 0 ? <p className="empty-state">No deployed workflow state is available.</p> : null}
    </div>
  );
}

function WorkflowCatalogCard({workflow}: {workflow: WorkflowCatalogItem}) {
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
    </article>
  );
}
