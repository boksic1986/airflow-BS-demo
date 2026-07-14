import {useEffect, useState} from "react";
import {useSearchParams} from "react-router-dom";

import type {RunListResponse, RunSummary} from "../api";

import {listRuns} from "../api";
import {RunTable} from "../components/RunTable";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {errorMessage} from "../lib/errors";

const pageSize = 20;
const validPipelines = new Set(["all", "pgta", "nipt_docker", "wgs"]);
const validStatuses = new Set(["all", "created", "submitted", "queued", "running", "success", "failed"]);
const validSorts = new Set(["created_desc", "duration_desc", "status"]);

export function RunsPage() {
  const capabilities = usePlatformCapabilities();
  const [searchParams, setSearchParams] = useSearchParams();
  const pipeline = validValue(searchParams.get("pipeline"), validPipelines, "all");
  const status = validValue(searchParams.get("status"), validStatuses, "all");
  const sort = validValue(searchParams.get("sort"), validSorts, "created_desc") as "created_desc" | "duration_desc" | "status";
  const keyword = searchParams.get("keyword") || "";
  const [keywordDraft, setKeywordDraft] = useState(keyword);
  const page = positivePage(searchParams.get("page"));
  const [payload, setPayload] = useState<RunListResponse>({items: [], total: 0});
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
    listRuns({
      pipeline: pipeline === "all" ? "deployed" : pipeline,
      status: status === "all" ? undefined : status,
      keyword: keyword.trim() || undefined,
      sort,
      limit: pageSize,
      offset: (page - 1) * pageSize,
    })
      .then((result) => {
        if (!disposed) setPayload(result);
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
  }, [keyword, page, pipeline, sort, status]);

  function updateFilter(name: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (!value || value === "all" || (name === "sort" && value === "created_desc")) next.delete(name);
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
          <p className="eyebrow">Batch run resource</p>
          <h1>Batch Runs</h1>
          <p>Server-backed deployed runs with durable filters and pagination.</p>
        </div>
      </section>
      <section className="panel">
        <div className="filter-bar resource-filter-bar">
          <label>
            <span>Pipeline</span>
            <select aria-label="Pipeline" value={pipeline} onChange={(event) => updateFilter("pipeline", event.target.value)}>
              <option value="all">All deployed</option>
              {capabilities.isDeployed("pgta") ? <option value="pgta">PGT-A</option> : null}
              {capabilities.isDeployed("nipt_docker") ? <option value="nipt_docker">NIPT Docker</option> : null}
              {capabilities.isDeployed("wgs") ? <option value="wgs">WGS</option> : null}
            </select>
          </label>
          <label>
            <span>Status</span>
            <select aria-label="Status" value={status} onChange={(event) => updateFilter("status", event.target.value)}>
              <option value="all">All</option>
              <option value="created">created</option>
              <option value="submitted">submitted</option>
              <option value="queued">queued</option>
              <option value="running">running</option>
              <option value="success">success</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label>
            <span>Sort</span>
            <select aria-label="Sort" value={sort} onChange={(event) => updateFilter("sort", event.target.value)}>
              <option value="created_desc">Created newest</option>
              <option value="duration_desc">Duration longest</option>
              <option value="status">Status priority</option>
            </select>
          </label>
          <label className="grow">
            <span>Keyword</span>
            <input
              aria-label="Keyword"
              value={keywordDraft}
              placeholder="project or run ID"
              onChange={(event) => setKeywordDraft(event.target.value)}
            />
          </label>
        </div>
        {loading ? <p className="muted">Loading runs...</p> : null}
        {error ? <div className="inline-error" role="alert">{error}</div> : null}
        {!loading && !error ? <RunTable runs={payload.items as RunSummary[]} /> : null}
        <div className="pagination-controls" aria-label="Run pagination">
          <span>{payload.total} runs · page {Math.min(page, pageCount)} / {pageCount}</span>
          <div>
            <button type="button" disabled={page <= 1} onClick={() => goToPage(page - 1)}>Previous</button>
            <button type="button" disabled={page >= pageCount} onClick={() => goToPage(page + 1)}>Next</button>
          </div>
        </div>
      </section>
    </div>
  );
}

function validValue(value: string | null, valid: Set<string>, fallback: string): string {
  return value && valid.has(value) ? value : fallback;
}

function positivePage(value: string | null): number {
  const parsed = Number(value || "1");
  return Number.isFinite(parsed) && parsed >= 1 ? Math.floor(parsed) : 1;
}
