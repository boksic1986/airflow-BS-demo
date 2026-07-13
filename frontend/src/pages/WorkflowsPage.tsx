import {useEffect, useState} from "react";
import {Link} from "react-router-dom";

import type {WorkflowCatalogItem} from "../api";
import {getWorkflowCatalog} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {WorkflowStageRail} from "../components/WorkflowStageRail";
import {errorMessage} from "../lib/errors";
import {formatDate} from "../lib/format";

export function WorkflowsPage() {
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

  return (
    <div className="page-stack workflow-catalog-page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Live workflow status</p>
          <h1>Workflow Catalog</h1>
          <p>Only the deployed PGT-A Predict and NIPT Docker Full analysis paths are shown.</p>
        </div>
      </section>
      {error ? <div className="inline-error" role="alert">Workflow catalog unavailable: {error}</div> : null}
      {loading ? <p className="muted panel-loading">Loading deployed workflows...</p> : null}
      <section className="workflow-catalog-grid">
        {items.map((workflow) => <WorkflowCatalogCard key={workflow.pipeline} workflow={workflow} />)}
      </section>
      {!loading && !error && items.length === 0 ? <p className="empty-state">No deployed workflow state is available.</p> : null}
    </div>
  );
}

function WorkflowCatalogCard({workflow}: {workflow: WorkflowCatalogItem}) {
  const latest = workflow.latest_run;
  return (
    <article className="panel workflow-catalog-card">
      <div className="section-heading split">
        <div><p className="eyebrow">{workflow.dag_id}</p><h2>{workflow.name}</h2><p>{workflow.runtime}</p></div>
        <StatusBadge status={latest?.status || "queued"} />
      </div>
      <WorkflowStageRail analysisId={latest?.analysis_id || workflow.pipeline} pipeline={workflow.pipeline} stages={workflow.stages} />
      <dl className="definition-grid compact">
        <div><dt>Runtime profile</dt><dd>{workflow.runtime_profile_id}</dd></div>
        <div><dt>Validated runs</dt><dd>{workflow.run_count}</dd></div>
        <div><dt>Success rate</dt><dd>{workflow.success_rate == null ? "No history" : `${Math.round(workflow.success_rate * 100)}%`}</dd></div>
        <div><dt>Current stage</dt><dd>{latest?.current_stage || "No run history"}</dd></div>
      </dl>
      {latest ? (
        <div className="workflow-latest-run">
          <span>Latest run</span>
          <Link className="mono" to={`/runs/${encodeURIComponent(latest.analysis_id)}`}>{latest.analysis_id}</Link>
          <small>{latest.project_name} / {formatDate(latest.finished_at || latest.submitted_at)}</small>
        </div>
      ) : null}
    </article>
  );
}
