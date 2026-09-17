import {useEffect, useState} from "react";
import {Link, useSearchParams} from "react-router-dom";
import {listSampleReferences, listSampleReferenceSources, listSamplesResource, type OperatorSampleResponse, type Page, type SampleReference, type SampleReferenceSource} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {deployedPipelineFilter} from "../lib/deployment";
import {useSilentRefresh} from "../lib/useSilentRefresh";

const size = 25;

export function SamplesPage() {
  const [params, setParams] = useSearchParams();
  const view = params.get("view") === "ledger" ? "ledger" : "analysis";
  return <div className="page-stack">
    <section className="page-header"><div><p className="eyebrow">Sample resource</p><h1>Sample Information</h1></div></section>
    <div className="tab-row" role="tablist" aria-label="Sample information views">
      <button role="tab" aria-selected={view === "analysis"} className={view === "analysis" ? "active" : ""} onClick={() => setParams({})}>分析记录</button>
      <button role="tab" aria-selected={view === "ledger"} className={view === "ledger" ? "active" : ""} onClick={() => setParams({view: "ledger"})}>样本流转</button>
    </div>
    {view === "analysis" ? <Analysis /> : <Ledger />}
  </div>;
}

function Analysis() {
  const caps = usePlatformCapabilities();
  const [params, setParams] = useSearchParams();
  const pipeline = deployedPipelineFilter(params.get("pipeline"), caps.deployed_pipelines);
  const status = params.get("status") || "all";
  const keyword = params.get("keyword") || "";
  const page = pageOf(params);
  const [draft, setDraft] = useState(keyword);
  const [data, setData] = useState<OperatorSampleResponse>({items: [], total: 0, limit: size, offset: 0});

  useEffect(() => setDraft(keyword), [keyword]);
  useEffect(() => {
    if (draft === keyword) return;
    const timeout = setTimeout(() => change("keyword", draft.trim(), params, setParams), 300);
    return () => clearTimeout(timeout);
  }, [draft, keyword]);

  const {loading, error} = useSilentRefresh(async ({isCurrent}) => {
    const response = await listSamplesResource({
      pipeline: pipeline === "all" ? "deployed" : pipeline,
      status: status === "all" ? undefined : status,
      keyword: keyword || undefined,
      limit: size,
      offset: (page - 1) * size,
    });
    if (isCurrent()) setData(response);
  }, JSON.stringify([pipeline, status, keyword, page]));

  return <section className="panel">
    <div className="filter-bar resource-filter-bar">
      <label><span>Pipeline</span><select aria-label="Sample pipeline" value={pipeline} onChange={event => change("pipeline", event.target.value, params, setParams)}><option value="all">All deployed</option>{caps.pipelines.filter(item => caps.isDeployed(item.id)).map(item => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label>
      <label><span>Status</span><select aria-label="Sample status" value={status} onChange={event => change("status", event.target.value, params, setParams)}><option value="all">All</option>{["pending", "running", "success", "failed"].map(item => <option key={item}>{item}</option>)}</select></label>
      <label className="grow"><span>Keyword</span><input aria-label="Sample keyword" value={draft} placeholder="sample, family, batch, project or run ID" onChange={event => setDraft(event.target.value)} /></label>
    </div>
    {loading ? <p className="muted">Loading samples...</p> : null}
    {error ? <div className="inline-error" role="alert">{error}</div> : null}
    {!loading ? <div className="table-wrap"><table className="data-table sample-resource-table"><thead><tr><th>Sample / family</th><th>Batch</th><th>Order</th><th>Relation / type</th><th>Project / run</th><th>Status</th></tr></thead><tbody>
      {data.items.map(row => <tr key={`${row.analysis_id}-${row.sample_id}`}><td><strong>{row.sample_id}</strong>{row.family_id ? <small className="block muted">Family {row.family_id}</small> : null}</td><td>{row.batch_no || "-"}</td><td>{row.order_number_masked || "-"}</td><td>{row.family_relation || "-"}<small className="block muted">{[row.sample_type, row.sex].filter(Boolean).join(" / ") || "-"}</small></td><td><Link className="resource-link" to={`/runs/${encodeURIComponent(row.analysis_id)}`}>{row.test_project || row.project_name}</Link><Link className="resource-link secondary mono" to={`/runs/${encodeURIComponent(row.analysis_id)}`}>{row.test_project ? `${row.project_name} · ` : ""}{row.analysis_id}</Link></td><td><StatusBadge status={row.status} />{row.pending_reason || row.status_reason ? <small className="block muted">{row.pending_reason || row.status_reason}</small> : null}</td></tr>)}
      {!data.items.length ? <tr><td className="empty-cell" colSpan={6}>No samples match the current filters.</td></tr> : null}
    </tbody></table></div> : null}
    <Pager label="Sample" total={data.total} page={page} go={next => go(next, params, setParams)} />
  </section>;
}

function Ledger() {
  const [params, setParams] = useSearchParams();
  const page = pageOf(params);
  const historyView = params.get("ledger_scope") === "history";
  const filters = {
    sourceId: params.get("source_id") || "", sampleId: params.get("sample_id") || "",
    familyId: params.get("family_id") || "", originBatch: params.get("origin_batch") || "",
    destinationBatch: historyView ? params.get("destination_batch") || "" : "", pending: historyView ? undefined : true,
    syncError: bool(params.get("sync_error")),
  };
  const [data, setData] = useState<Page<SampleReference>>({items: [], total: 0, limit: size, offset: 0});
  const [sources, setSources] = useState<Page<SampleReferenceSource>>({items: [], total: 0, limit: size, offset: 0});

  const refreshKey = JSON.stringify([filters, page]);
  const {loading, error} = useSilentRefresh(async ({isCurrent}) => {
    const [rows, health] = await Promise.all([
      listSampleReferences({...filters, limit: size, offset: (page - 1) * size}),
      listSampleReferenceSources({syncError: true, limit: 1, offset: 0}),
    ]);
    if (isCurrent()) { setData(rows); setSources(health); }
  }, refreshKey);

  const textFilters = [["source_id", "Source", filters.sourceId], ["sample_id", "Sample", filters.sampleId], ["family_id", "Family", filters.familyId], ["origin_batch", "来源分析批次", filters.originBatch]];
  const visibleRows = historyView ? data.items : data.items.filter(row => row.pending && row.present_in_latest_complete);
  return <>
    <section className="panel ledger-panel">
      <h2>样本流转</h2>
      <div className="tab-row" role="tablist" aria-label="样本流转范围">
        <button role="tab" aria-selected={!historyView} className={!historyView ? "active" : ""} onClick={() => change("ledger_scope", "", params, setParams)}>待纳入</button>
        <button role="tab" aria-selected={historyView} className={historyView ? "active" : ""} onClick={() => change("ledger_scope", "history", params, setParams)}>纳入记录</button>
      </div>
      <div className="filter-bar resource-filter-bar">
        {textFilters.map(([name, label, value]) => <label key={name}><span>{label}</span><input aria-label={label} value={String(value)} onChange={event => change(String(name), event.target.value.trim(), params, setParams)} /></label>)}
        <Choice label="Sync issue" name="sync_error" value={params.get("sync_error") || "all"} onChange={value => change("sync_error", value, params, setParams)} />
      </div>
      {loading ? <p className="muted">Loading ledger...</p> : null}
      {error ? <div className="inline-error" role="alert">Refresh failed; retained last-good ledger. {error}</div> : null}
      {sources.total > 0 || data.items.some(row => row.sync_status === "error") ? <div className="inline-error" role="alert">交接来源同步异常，当前显示最后一次成功同步的数据。</div> : null}
      <div className="table-wrap"><table className="data-table sample-resource-table"><thead><tr><th>Sample / family</th><th>来源分析批次</th><th>Status</th><th>纳入批次</th></tr></thead><tbody>
        {visibleRows.map(row => <FlowRow key={`${row.source_id}:${row.record_key}`} row={row} />)}
        {!visibleRows.length && !loading ? <tr><td colSpan={4} className="empty-cell">{historyView ? "没有匹配的流转记录。" : <>当前没有待纳入样本。<button className="text-button" onClick={() => change("ledger_scope", "history", params, setParams)}>查看纳入记录</button></>}</td></tr> : null}
      </tbody></table></div>
      <Pager label="Ledger" total={data.total} page={page} go={next => go(next, params, setParams)} />
    </section>
  </>;
}

function FlowRow({row}: {row: SampleReference}) {
  const pending = row.pending && row.present_in_latest_complete;
  const recorded = pending ? null : row.latest_decision;
  const label = row.needs_review ? "身份待核对" : pending ? "待纳入" : recorded ? (recorded.role === "consumed" ? "已交接" : "已纳入") : "待关联";
  return <tr>
    <td><strong>{row.sample_id}</strong>{row.family_id ? <small className="block muted">Family {row.family_id}</small> : null}</td>
    <td>{row.origin_batch || "待核对来源批次"}</td>
    <td><StatusBadge status={row.needs_review ? "warning" : pending ? "pending" : recorded ? "accepted" : "unknown"} label={label} /></td>
    <td>{recorded?.destination_batch ? recorded.analysis_id
      ? <Link className="resource-link" to={`/runs/${encodeURIComponent(recorded.analysis_id)}`}>{recorded.destination_batch}</Link>
      : recorded.destination_batch : "-"}</td>
  </tr>;
}

function Choice({label, name, value, onChange}: {label: string; name: string; value: string; onChange: (value: string) => void}) {
  return <label><span>{label}</span><select aria-label={label} value={value} onChange={event => onChange(event.target.value)}><option value="all">All</option><option value="true">{name === "pending" ? "Yes" : "Errors"}</option><option value="false">{name === "pending" ? "No" : "Healthy"}</option></select></label>;
}

function Pager({label, total, page, go}: {label: string; total: number; page: number; go: (page: number) => void}) {
  const pages = Math.max(1, Math.ceil(total / size));
  return <div className="pagination-controls" aria-label={`${label} pagination`}>
    <span>{total} records · page {Math.min(page, pages)} / {pages}</span>
    <div><button type="button" disabled={page <= 1} onClick={() => go(page - 1)}>Previous</button><button type="button" disabled={page >= pages} onClick={() => go(page + 1)}>Next</button></div>
  </div>;
}

type SetParams = ReturnType<typeof useSearchParams>[1];

function pageOf(params: URLSearchParams) {
  const page = Number(params.get("page") || 1);
  return Number.isFinite(page) && page >= 1 ? Math.floor(page) : 1;
}

function bool(value: string | null) {
  return value === "true" ? true : value === "false" ? false : undefined;
}

function change(name: string, value: string, params: URLSearchParams, setParams: SetParams) {
  const next = new URLSearchParams(params);
  if (!value || value === "all") next.delete(name);
  else next.set(name, value);
  next.delete("page");
  setParams(next);
}

function go(page: number, params: URLSearchParams, setParams: SetParams) {
  const next = new URLSearchParams(params);
  if (page <= 1) next.delete("page");
  else next.set("page", String(page));
  setParams(next);
}
