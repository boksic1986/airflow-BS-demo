import {useEffect, useState} from "react";
import {useSearchParams} from "react-router-dom";

import type {FailureItem, FailureListResponse} from "../api";

import {listFailures} from "../api";
import {FailureWorkspace} from "../features/failures/FailureWorkspace";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {errorMessage} from "../lib/errors";

const pageSize = 20;

export function FailuresPage() {
  const capabilities = usePlatformCapabilities();
  const [searchParams, setSearchParams] = useSearchParams();
  const pipeline = searchParams.get("pipeline") || "all";
  const kind = (searchParams.get("kind") || "all") as "all" | "workflow" | "qc";
  const period = (searchParams.get("period") || "7d") as "24h" | "7d" | "30d";
  const layer = searchParams.get("layer") || "all";
  const keyword = searchParams.get("keyword") || "";
  const [keywordDraft, setKeywordDraft] = useState(keyword);
  const page = positivePage(searchParams.get("page"));
  const [payload, setPayload] = useState<FailureListResponse>({items: [], total: 0, limit: pageSize, offset: 0});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    let disposed = false;
    setLoading(true);
    setError(null);
    listFailures({
      pipeline,
      kind,
      period,
      layer: layer === "all" ? undefined : layer,
      keyword: keyword.trim() || undefined,
      limit: pageSize,
      offset: (page - 1) * pageSize,
    })
      .then((result) => {
        if (disposed) return;
        setPayload(result);
        setSelectedId(result.items.length ? failureKey(result.items[0]) : null);
      })
      .catch((loadError) => {
        if (!disposed) setError(errorMessage(loadError));
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [keyword, kind, layer, page, period, pipeline]);

  function updateFilter(name: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (!value || value === "all" || (name === "period" && value === "7d")) next.delete(name);
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
          <p className="eyebrow">Operations workspace</p>
          <h1>Failure Triage</h1>
          <p>Workflow failures and QC alerts remain distinct while sharing one investigation queue.</p>
        </div>
      </section>
      <section className="panel failure-filter-panel">
        <div className="segmented-control" aria-label="Issue kind">
          <button className={kind === "all" ? "active" : ""} type="button" onClick={() => updateFilter("kind", "all")}>All issues</button>
          <button className={kind === "workflow" ? "active" : ""} type="button" onClick={() => updateFilter("kind", "workflow")}>Workflow failures</button>
          <button className={kind === "qc" ? "active" : ""} type="button" onClick={() => updateFilter("kind", "qc")}>QC alerts</button>
        </div>
        <div className="filter-bar resource-filter-bar">
          <label>
            <span>Pipeline</span>
            <select aria-label="Failure pipeline" value={pipeline} onChange={(event) => updateFilter("pipeline", event.target.value)}>
              <option value="all">All deployed</option>
              {capabilities.isDeployed("pgta") ? <option value="pgta">PGT-A</option> : null}
              {capabilities.isDeployed("nipt_docker") ? <option value="nipt_docker">NIPT Docker</option> : null}
            </select>
          </label>
          <label>
            <span>Period</span>
            <select aria-label="Failure period" value={period} onChange={(event) => updateFilter("period", event.target.value)}>
              <option value="24h">24h</option>
              <option value="7d">7d</option>
              <option value="30d">30d</option>
            </select>
          </label>
          <label>
            <span>Layer</span>
            <select aria-label="Failure layer" value={layer} onChange={(event) => updateFilter("layer", event.target.value)}>
              <option value="all">All layers</option>
              <option value="airflow">Airflow task</option>
              <option value="runner">Runner</option>
              <option value="pipeline_rule">Pipeline rule</option>
              <option value="qc">Sample QC</option>
            </select>
          </label>
          <label className="grow">
            <span>Keyword</span>
            <input aria-label="Failure keyword" value={keywordDraft} placeholder="project, run, sample or step" onChange={(event) => setKeywordDraft(event.target.value)} />
          </label>
        </div>
      </section>
      {loading ? <p className="muted">Loading issue queue...</p> : null}
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {!loading && !error ? <FailureWorkspace items={payload.items} selectedId={selectedId} onSelect={setSelectedId} /> : null}
      <div className="pagination-controls" aria-label="Failure pagination">
        <span>{payload.total} issues · page {Math.min(page, pageCount)} / {pageCount}</span>
        <div>
          <button type="button" disabled={page <= 1} onClick={() => goToPage(page - 1)}>Previous</button>
          <button type="button" disabled={page >= pageCount} onClick={() => goToPage(page + 1)}>Next</button>
        </div>
      </div>
    </div>
  );
}

function failureKey(item: FailureItem): string {
  return `${item.failure_kind}:${item.analysis_id}:${item.sample_id || "project"}:${item.failed_step}`;
}

function positivePage(value: string | null): number {
  const parsed = Number(value || "1");
  return Number.isFinite(parsed) && parsed >= 1 ? Math.floor(parsed) : 1;
}
