import {useEffect, useRef, useState} from "react";
import {Link, useSearchParams} from "react-router-dom";
import {listSampleReferenceOperations, listSampleReferences, listSampleReferenceSources, listSamplesResource, type OperatorSampleResponse, type Page, type SampleReference, type SampleReferenceOperation, type SampleReferenceSource} from "../api";
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
      <button role="tab" aria-selected={view === "ledger"} className={view === "ledger" ? "active" : ""} onClick={() => setParams({view: "ledger"})}>样本资料／交接台账</button>
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
  const [sourcePage, setSourcePage] = useState(1);
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [history, setHistory] = useState<Record<string, Page<SampleReferenceOperation>>>({});
  const [historyPage, setHistoryPage] = useState<Record<string, number>>({});
  const [historyErrors, setHistoryErrors] = useState<Record<string, string>>({});
  const historyRequests = useRef<Record<string, number>>({});
  const historyGenerations = useRef<Record<string, number | null | undefined>>({});
  const historyPending = useRef<Record<string, {generation: number | null | undefined; page: number}>>({});
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  useEffect(() => setSourcePage(1), [filters.syncError]);

  const refreshKey = JSON.stringify([filters, page, sourcePage]);
  const {loading, error} = useSilentRefresh(async ({isCurrent}) => {
    const [rows, health] = await Promise.all([
      listSampleReferences({...filters, limit: size, offset: (page - 1) * size}),
      listSampleReferenceSources({syncError: filters.syncError, limit: size, offset: (sourcePage - 1) * size}),
    ]);
    if (isCurrent()) { setData(rows); setSources(health); }
  }, refreshKey);

  useEffect(() => {
    for (const row of data.items) {
      const key = `${row.source_id}:${row.record_key}`;
      const pending = historyPending.current[key];
      if (open[key] && historyGenerations.current[key] !== row.last_good_generation &&
          !(pending && pending.generation === row.last_good_generation && pending.page === (historyPage[key] || 1))) {
        void loadHistory(row, historyPage[key] || 1);
      }
    }
  }, [data]);

  async function loadHistory(row: SampleReference, nextPage: number) {
    const key = `${row.source_id}:${row.record_key}`;
    const request = (historyRequests.current[key] || 0) + 1;
    historyRequests.current[key] = request;
    historyPending.current[key] = {generation: row.last_good_generation, page: nextPage};
    setHistoryPage(value => ({...value, [key]: nextPage}));
    try {
      const result = await listSampleReferenceOperations({sourceId: row.source_id, recordKey: row.record_key, limit: size, offset: (nextPage - 1) * size});
      if (!mounted.current || historyRequests.current[key] !== request) return;
      historyGenerations.current[key] = row.last_good_generation;
      setHistory(value => ({...value, [key]: result}));
      setHistoryErrors(value => ({...value, [key]: ""}));
    } catch (failure) {
      if (!mounted.current || historyRequests.current[key] !== request) return;
      setHistoryErrors(value => ({...value, [key]: failure instanceof Error ? failure.message : String(failure)}));
    } finally {
      if (historyRequests.current[key] === request) delete historyPending.current[key];
    }
  }

  function toggle(row: SampleReference) {
    const key = `${row.source_id}:${row.record_key}`;
    if (open[key]) {
      historyRequests.current[key] = (historyRequests.current[key] || 0) + 1;
      delete historyPending.current[key];
    }
    setOpen(value => ({...value, [key]: !value[key]}));
    // Reopening revalidates even cached history; keep last-good content visible.
    if (!open[key]) void loadHistory(row, historyPage[key] || 1);
  }

  const textFilters = [["source_id", "Source", filters.sourceId], ["sample_id", "Sample", filters.sampleId], ["family_id", "Family", filters.familyId], ["origin_batch", "来源分析批次", filters.originBatch]];
  const visibleRows = historyView ? data.items : data.items.filter(row => row.pending && row.present_in_latest_complete);
  return <>
    <section className="panel">
      <h2>交接台账</h2>
      <p className="muted">当前待交接仅显示共享 pending 中的样本；捞回后保留历史，不代表分析或 QC 已完成。此处不修改 pending 文件。</p>
      <div className="tab-row" role="tablist" aria-label="交接台账范围">
        <button role="tab" aria-selected={!historyView} className={!historyView ? "active" : ""} onClick={() => change("ledger_scope", "", params, setParams)}>当前待交接</button>
        <button role="tab" aria-selected={historyView} className={historyView ? "active" : ""} onClick={() => change("ledger_scope", "history", params, setParams)}>历史记录</button>
      </div>
      {historyView ? <p className="muted">包含当前与已移出记录；查看详情可核对已记录的交接凭据。</p> : null}
      <div className="filter-bar resource-filter-bar">
        {textFilters.map(([name, label, value]) => <label key={name}><span>{label}</span><input aria-label={label} value={String(value)} onChange={event => change(String(name), event.target.value.trim(), params, setParams)} /></label>)}
        <Choice label="Sync issue" name="sync_error" value={params.get("sync_error") || "all"} onChange={value => change("sync_error", value, params, setParams)} />
      </div>
      {loading ? <p className="muted">Loading ledger...</p> : null}
      {error ? <div className="inline-error" role="alert">Refresh failed; retained last-good ledger. {error}</div> : null}
      {sources.items.some(source => source.sync_status === "error") || data.items.some(row => row.sync_status === "error") ? <div className="inline-error" role="alert">交接来源同步异常，当前显示最后一次成功同步的数据，请查看同步详情。</div> : null}
      <div className="table-wrap"><table className="data-table sample-resource-table"><thead><tr><th>Sample / family</th><th>来源分析批次</th><th>Status</th><th>详情</th></tr></thead><tbody>
        {visibleRows.map(row => { const key = `${row.source_id}:${row.record_key}`; return <Rows key={key} row={row} open={Boolean(open[key])} operations={history[key]} page={historyPage[key] || 1} error={historyErrors[key]} toggle={() => toggle(row)} go={next => void loadHistory(row, next)} />; })}
        {!visibleRows.length && !loading ? <tr><td colSpan={4} className="empty-cell">{historyView ? "没有匹配的台账记录。" : <>当前没有待交接样本。<button className="text-button" onClick={() => change("ledger_scope", "history", params, setParams)}>查看历史记录</button></>}</td></tr> : null}
      </tbody></table></div>
      <Pager label="Ledger" total={data.total} page={page} go={next => go(next, params, setParams)} />
    </section>
    <section className="panel"><details><summary>同步详情</summary>
      {sources.items.map(source => <p key={source.source_id}><strong>{source.source_id}</strong> · {source.sync_status}{source.sync_reason ? ` · ${source.sync_reason}` : ""} · last good generation {source.last_good_generation ?? "-"} at {source.last_good_at || "-"}</p>)}
      {!sources.items.length ? <p className="muted">No registered sources match the sync filter.</p> : null}
      <Pager label="Source health" total={sources.total} page={sourcePage} go={setSourcePage} />
    </details></section>
  </>;
}

function Rows({row, open, operations, page, error, toggle, go}: {row: SampleReference; open: boolean; operations?: Page<SampleReferenceOperation>; page: number; error?: string; toggle: () => void; go: (page: number) => void}) {
  const recorded = row.latest_decision || operations?.items.flatMap(operation => operation.links).find(link =>
    (link.record_key === row.record_key || link.resolved_key === row.record_key) &&
    (link.role === "consumed" || link.role === "selected") && link.destination_batch);
  return <>
    <tr>
      <td><strong>{row.sample_id}</strong>{row.family_id ? <small className="block muted">Family {row.family_id}</small> : null}</td>
      <td>{row.origin_batch || "待核对来源批次"}</td>
      <td><StatusBadge status={row.pending && row.present_in_latest_complete ? "pending" : recorded ? "accepted" : "unknown"} label={row.pending && row.present_in_latest_complete ? undefined : recorded ? `${recorded.role === "consumed" ? "已交接至" : "已纳入"} ${recorded.destination_batch}` : "历史身份待关联"} /><small className="block muted">{row.pending && row.present_in_latest_complete ? pendingReason(row.reason_codes, row.reason_code) : recorded ? "当前不在 pending；纳入或交接不代表分析或 QC 完成" : "当前不在 pending；未找到精确关联凭据"}</small>
        {row.needs_review ? <strong className="block inline-error">样本身份需核对</strong> : null}
      </td>
      <td><button type="button" className="button ghost" aria-expanded={open} onClick={toggle}>{open ? "收起详情" : "查看详情"}</button></td>
    </tr>
    {open ? <tr><td colSpan={4}><section className="panel ledger-history-panel" aria-label={`${row.sample_id} 交接详情`}>
      <p className="muted">来源：{row.source_id} · 同步：{row.sync_status}{row.sync_reason ? ` · ${row.sync_reason}` : ""} · generation {row.last_good_generation ?? "-"} · {row.last_good_at || "未记录"}</p>
      {error ? <div className="inline-error" role="alert">History refresh failed; retained last-good history. {error}</div> : null}
      {!operations ? <span className="muted">Loading history...</span> : <>
        {operations.items.length ? operations.items.map(operation => <div className="ledger-operation" key={operation.operation_id}>
          <strong>#{operation.sequence} · {operation.mode}</strong>
          <small className="block muted">Logical transaction time: {operation.logical_transaction_at || "unknown"} · {operation.logical_transaction_time_semantics || "unknown legacy provenance"}</small>
          {operation.observed_at ? <small className="block muted">Collection observed: {operation.observed_at}</small> : null}
          {operation.analysis_id ? <> · <Link to={`/runs/${encodeURIComponent(operation.analysis_id)}`}>{operation.analysis_id}</Link></> : " · no analysis run"}
          {operation.links.filter(link => link.record_key === row.record_key || link.resolved_key === row.record_key).map((link, index) => <div key={`${link.role}-${index}`}>
            <span>{link.role === "consumed" && link.destination_batch ? `已交接至 ${link.destination_batch}` : link.role === "selected" && link.destination_batch ? `已纳入 ${link.destination_batch}` : link.role === "pending" ? "仍待交接" : "未记录接收决定"}</span>
            {link.resolved_key && link.resolved_key !== link.record_key ? <small className="block muted">Alias lineage: {link.record_key} → {link.resolved_key}</small> : null}
            {link.reason_codes.length ? <small className="block muted">{pendingReason(link.reason_codes)}</small> : null}
            {link.role === "consumed" ? <small className="block muted">Consumed by this handoff; does not establish analysis success or QC.</small> : null}
          </div>)}
          {!operation.links.some(link => link.record_key === row.record_key || link.resolved_key === row.record_key) ? <small className="block muted">{operation.links_truncated ? "Member decisions unavailable in this truncated response." : "Snapshot observation only; no selected, pending or consumed decision for this member."}</small> : null}
          {operation.links_truncated ? <small className="block muted">Showing {operation.links.length} of {operation.links_total} links; use exact member filtering.</small> : null}
        </div>) : <span className="muted">No recorded operations.</span>}
        <Pager label={`${row.sample_id} history`} total={operations.total} page={page} go={go} />
      </>}
    </section></td></tr> : null}
  </>;
}
const pendingReasons: Record<string, string> = {
  sequencing_batch_missing: "缺少上机批次", samplelist_sample_missing: "样本清单中缺少样本",
  fastq_ready_missing: "FASTQ 尚未就绪", target_base_invalid: "目标数据量需核对",
  basecount_missing: "缺少数据量统计", basecount_parse_error: "数据量统计解析失败",
  sample_not_in_basecount: "数据量统计中缺少样本", basecount_below_minimum: "数据量未达到要求",
  pending_reason_unclassified: "待核对原因",
};
function pendingReason(codes: string[] = [], code?: string | null) {
  const values = codes.length ? codes : code ? [code] : ["pending_reason_unclassified"];
  return [...new Set(values.map(value => pendingReasons[value] || "待核对原因"))].join("；");
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
