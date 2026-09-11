import {useEffect, useState} from "react";
import {Link, useSearchParams} from "react-router-dom";

import type {OperatorSampleResponse} from "../api";

import {listSamplesResource} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {deployedPipelineFilter} from "../lib/deployment";
import {useSilentRefresh} from "../lib/useSilentRefresh";

const pageSize = 25;

export function SamplesPage() {
  const capabilities = usePlatformCapabilities();
  const [searchParams, setSearchParams] = useSearchParams();
  const pipeline = deployedPipelineFilter(searchParams.get("pipeline"), capabilities.deployed_pipelines);
  const status = searchParams.get("status") || "all";
  const keyword = searchParams.get("keyword") || "";
  const [keywordDraft, setKeywordDraft] = useState(keyword);
  const page = positivePage(searchParams.get("page"));
  const [payload, setPayload] = useState<OperatorSampleResponse>({items: [], total: 0, limit: pageSize, offset: 0});

  useEffect(() => { setKeywordDraft(keyword); }, [keyword]);
  useEffect(() => {
    if (keywordDraft === keyword) return undefined;
    const timer = window.setTimeout(() => {
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        if (keywordDraft.trim()) next.set("keyword", keywordDraft);
        else next.delete("keyword");
        next.delete("page");
        return next;
      }, {replace: true});
    }, 300);
    return () => window.clearTimeout(timer);
  }, [keyword, keywordDraft, setSearchParams]);

  const {loading, error} = useSilentRefresh(async ({isCurrent}) => {
    const result = await listSamplesResource({
      pipeline: pipeline === "all" ? "deployed" : pipeline,
      status: status === "all" ? undefined : status,
      keyword: keyword.trim() || undefined,
      limit: pageSize,
      offset: (page - 1) * pageSize,
    });
    if (isCurrent()) setPayload(result);
  }, JSON.stringify([keyword, page, pipeline, status]));

  function updateFilter(name: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (!value || value === "all") next.delete(name);
    else next.set(name, value);
    next.delete("page");
    setSearchParams(next);
  }

  function goToPage(nextPage: number) {
    const next = new URLSearchParams(searchParams);
    if (nextPage <= 1) next.delete("page");
    else next.set("page", String(nextPage));
    setSearchParams(next);
  }

  const pageCount = Math.max(1, Math.ceil(payload.total / pageSize));

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Sample resource</p>
          <h1>Sample Information</h1>
        </div>
      </section>
      <section className="panel">
        <div className="filter-bar resource-filter-bar">
          <label>
            <span>Pipeline</span>
            <select aria-label="Sample pipeline" value={pipeline} onChange={(event) => updateFilter("pipeline", event.target.value)}>
              <option value="all">All deployed</option>
              {capabilities.pipelines.filter((item) => capabilities.isDeployed(item.id)).map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}
            </select>
          </label>
          <label>
            <span>Status</span>
            <select aria-label="Sample status" value={status} onChange={(event) => updateFilter("status", event.target.value)}>
              <option value="all">All</option>
              <option value="pending">pending</option>
              <option value="running">running</option>
              <option value="success">success</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label className="grow">
            <span>Keyword</span>
            <input aria-label="Sample keyword" value={keywordDraft} placeholder="sample, family, batch, project or run ID" onChange={(event) => setKeywordDraft(event.target.value)} />
          </label>
        </div>
        {loading ? <p className="muted">Loading samples...</p> : null}
        {error ? <div className="inline-error" role="alert">{error}</div> : null}
        {!loading ? (
          <div className="table-wrap">
            <table className="data-table sample-resource-table">
              <thead>
                <tr><th>Sample / family</th><th>Batch</th><th>Order</th><th>Relation / type</th><th>Project / run</th><th>Status</th></tr>
              </thead>
              <tbody>
                {payload.items.map((row) => (
                  <tr key={`${row.analysis_id}-${row.sample_id}`}>
                    <td><strong>{row.sample_id}</strong>{row.family_id ? <small className="block muted">Family {row.family_id}</small> : null}</td>
                    <td>{row.batch_no || "-"}</td>
                    <td>{row.order_number_masked || "-"}</td>
                    <td>{row.family_relation || "-"}<small className="block muted">{[row.sample_type, row.sex].filter(Boolean).join(" / ") || "-"}</small></td>
                    <td>
                      <Link className="resource-link" to={`/runs/${encodeURIComponent(row.analysis_id)}`}>{row.test_project || row.project_name}</Link>
                      <Link className="resource-link secondary mono" to={`/runs/${encodeURIComponent(row.analysis_id)}`}>{row.test_project ? `${row.project_name} · ` : ""}{row.analysis_id}</Link>
                    </td>
                    <td>
                      <StatusBadge status={row.status} />
                      {row.pending_reason || row.status_reason ? <small className="block muted">{row.pending_reason || row.status_reason}</small> : null}
                    </td>
                  </tr>
                ))}
                {payload.items.length === 0 ? <tr><td className="empty-cell" colSpan={6}>No samples match the current filters.</td></tr> : null}
              </tbody>
            </table>
          </div>
        ) : null}
        <div className="pagination-controls" aria-label="Sample pagination">
          <span>{payload.total} samples · page {Math.min(page, pageCount)} / {pageCount}</span>
          <div>
            <button type="button" disabled={page <= 1} onClick={() => goToPage(page - 1)}>Previous</button>
            <button type="button" disabled={page >= pageCount} onClick={() => goToPage(page + 1)}>Next</button>
          </div>
        </div>
      </section>
    </div>
  );
}

function positivePage(value: string | null): number {
  const parsed = Number(value || "1");
  return Number.isFinite(parsed) && parsed >= 1 ? Math.floor(parsed) : 1;
}
