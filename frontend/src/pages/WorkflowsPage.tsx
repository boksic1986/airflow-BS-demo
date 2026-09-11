import {useEffect, useMemo, useState} from "react";
import {Link} from "react-router-dom";

import type {RunSummary} from "../api";
import {listRuns} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {LifecycleStatusBadge} from "../features/run-detail/DataLifecyclePanel";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {useSilentRefresh} from "../lib/useSilentRefresh";
import {formatDate} from "../lib/format";

const PAGE_SIZE = 20;
type LifecycleKey = "cloud_release" | "downstream_release";

export function WorkflowsPage() {
  const capabilities = usePlatformCapabilities();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [pipelineFilter, setPipelineFilter] = useState("all");
  const [cloudFilter, setCloudFilter] = useState("all");
  const [deliveryFilter, setDeliveryFilter] = useState("all");
  const [qcFilter, setQcFilter] = useState("all");
  const [keyword, setKeyword] = useState("");
  const [page, setPage] = useState(0);

  const visibleItems = capabilities.pipelines.filter((pipeline) => capabilities.isDeployed(pipeline.id));
  const visibleIds = visibleItems.map((pipeline) => pipeline.id).join(",");

  const {loading, error} = useSilentRefresh(async ({isCurrent}) => {
    if (!visibleIds) return;
    const payload = await listRuns({pipeline: "deployed", sort: "created_desc", limit: 200});
    if (isCurrent()) setRuns(payload.items);
  }, visibleIds, !capabilities.loading);

  useEffect(() => { setPage(0); }, [pipelineFilter, cloudFilter, deliveryFilter, qcFilter, keyword]);

  const filteredRuns = useMemo(() => runs.filter((run) => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return (pipelineFilter === "all" || run.pipeline === pipelineFilter)
      && (cloudFilter === "all" || lifecycleStatus(run, "cloud_release") === cloudFilter)
      && (deliveryFilter === "all" || lifecycleStatus(run, "downstream_release") === deliveryFilter)
      && (qcFilter === "all" || normalizedQcStatus(run.qc_status) === qcFilter)
      && (!normalizedKeyword || [run.project_name, run.batch_no, run.analysis_id]
        .some((value) => String(value || "").toLowerCase().includes(normalizedKeyword)));
  }), [runs, pipelineFilter, cloudFilter, deliveryFilter, qcFilter, keyword]);
  const pageRuns = filteredRuns.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="page-stack workflow-lifecycle-page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Run status</p>
          <h1>Run lifecycle</h1>
          <p>Workflow, QC, cloud release, and result delivery status for deployed runs.</p>
        </div>
      </section>
      {error ? <div className="inline-error" role="alert">Run lifecycle unavailable: {error}</div> : null}
      {loading ? <p className="muted panel-loading">Loading run lifecycle...</p> : null}
      {!loading && !error && visibleItems.length === 0 ? <p className="empty-state">No deployed run lifecycle is available.</p> : null}
      {visibleItems.length > 0 ? <section className="panel workflow-lifecycle-panel">
        <div className="workflow-lifecycle-filters">
          <label className="field"><span>Pipeline</span><select value={pipelineFilter} onChange={(event) => setPipelineFilter(event.target.value)}><option value="all">All deployed</option>{visibleItems.map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label>
          <LifecycleFilter label="Cloud release status" value={cloudFilter} onChange={setCloudFilter} />
          <LifecycleFilter label="Result delivery status" value={deliveryFilter} onChange={setDeliveryFilter} />
          <QcFilter value={qcFilter} onChange={setQcFilter} />
          <label className="field workflow-lifecycle-keyword"><span>Keyword</span><input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="project, batch, or run ID" /></label>
        </div>
        <div className="table-wrap">
          <table className="data-table workflow-lifecycle-table" aria-label="Run lifecycle">
            <thead><tr><th>Project / batch</th><th>Workflow</th><th>QC</th><th>Cloud release</th><th>Result delivery</th><th>Last updated</th></tr></thead>
            <tbody>
              {pageRuns.map((run) => <tr key={run.analysis_id}>
                <td><Link className="resource-link" to={`/runs/${encodeURIComponent(run.analysis_id)}`}>{run.project_name || run.analysis_id}</Link><Link className="resource-link secondary" to={`/runs/${encodeURIComponent(run.analysis_id)}`}>{run.batch_no || run.analysis_id}</Link></td>
                <td><StatusBadge status={run.workflow_status || run.status} /><span className="workflow-lifecycle-label">{run.workflow_label || run.status}</span></td>
                <td><StatusBadge status={normalizedQcStatus(run.qc_status)} /></td>
                <td><LifecycleBadge run={run} lifecycleKey="cloud_release" successLabel="SFS released" runningLabel="SFS release running" /></td>
                <td><LifecycleBadge run={run} lifecycleKey="downstream_release" successLabel="Delivered" runningLabel="Delivery running" /></td>
                <td>{formatDate(lastLifecycleUpdate(run))}</td>
              </tr>)}
              {pageRuns.length === 0 ? <tr><td colSpan={6} className="empty-cell">No runs match the lifecycle filters.</td></tr> : null}
            </tbody>
          </table>
        </div>
        <div className="pagination-controls"><span>{filteredRuns.length === 0 ? "0-0" : `${page * PAGE_SIZE + 1}-${Math.min((page + 1) * PAGE_SIZE, filteredRuns.length)}`} of {filteredRuns.length}</span><div><button type="button" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>Previous</button><button type="button" disabled={(page + 1) * PAGE_SIZE >= filteredRuns.length} onClick={() => setPage((value) => value + 1)}>Next</button></div></div>
      </section> : null}
    </div>
  );
}

function LifecycleFilter({label, value, onChange}: {label: string; value: string; onChange: (value: string) => void}) {
  return <label className="field"><span>{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}><option value="all">All</option><option value="not_started">Not started</option><option value="pending">Pending</option><option value="running">Running</option><option value="success">Success</option><option value="failed">Failed</option><option value="not_applicable">Not applicable</option><option value="unavailable">Unavailable</option></select></label>;
}

function QcFilter({value, onChange}: {value: string; onChange: (value: string) => void}) {
  return <label className="field"><span>QC status</span><select aria-label="QC status" value={value} onChange={(event) => onChange(event.target.value)}><option value="all">All</option><option value="pass">Pass</option><option value="warn">Warning</option><option value="fail">Fail</option><option value="unknown">Unknown</option></select></label>;
}

function normalizedQcStatus(value: string | null | undefined): string {
  const normalized = String(value || "unknown").toLowerCase();
  if (["success", "passed"].includes(normalized)) return "pass";
  if (normalized === "warning") return "warn";
  if (["failed", "error"].includes(normalized)) return "fail";
  return ["pass", "warn", "fail"].includes(normalized) ? normalized : "unknown";
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
