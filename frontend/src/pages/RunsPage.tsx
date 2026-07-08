import {useEffect, useMemo, useState} from "react";

import type {RunSummary} from "../api";

import {listRuns} from "../api";
import {RunTable} from "../components/RunTable";
import {errorMessage} from "../lib/errors";
import {statusPriority, normalizeStatus} from "../lib/status";
import {deployedWorkflowTemplates} from "../mocks/platform";

const deployedPipelineIds = deployedWorkflowTemplates.map((pipeline) => pipeline.id);
const visiblePipelines = new Set<string>(deployedPipelineIds);

export function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [pipeline, setPipeline] = useState("all");
  const [status, setStatus] = useState("all");
  const [keyword, setKeyword] = useState("");
  const [sort, setSort] = useState("created_desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    async function loadRuns() {
      setLoading(true);
      setError(null);
      try {
        const payload = await listRuns();
        if (!disposed) setRuns(payload.items);
      } catch (loadError) {
        if (!disposed) setError(errorMessage(loadError));
      } finally {
        if (!disposed) setLoading(false);
      }
    }
    void loadRuns();
    return () => {
      disposed = true;
    };
  }, []);

  const filteredRuns = useMemo(() => {
    const needle = keyword.toLowerCase();
    return runs
      .filter((run) => visiblePipelines.has(run.pipeline))
      .filter((run) => pipeline === "all" || run.pipeline === pipeline)
      .filter((run) => status === "all" || normalizeStatus(run.status) === status)
      .filter((run) => !needle || `${run.analysis_id} ${run.pipeline} ${run.status}`.toLowerCase().includes(needle))
      .sort((a, b) => {
        if (sort === "duration") {
          const duration = (run: RunSummary) =>
            run.started_at ? new Date(run.ended_at || Date.now()).getTime() - new Date(run.started_at).getTime() : 0;
          return duration(b) - duration(a);
        }
        if (sort === "status") return statusPriority(a.status) - statusPriority(b.status);
        return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
      });
  }, [keyword, pipeline, runs, sort, status]);

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Run resource</p>
          <h1>Runs</h1>
          <p>Filter, sort, and inspect deployed PGT-A and NIPT Docker runs.</p>
        </div>
      </section>
      <section className="panel">
        <div className="filter-bar">
          <label>
            <span>Pipeline</span>
            <select aria-label="Pipeline" value={pipeline} onChange={(event) => setPipeline(event.target.value)}>
              <option value="all">All deployed</option>
              <option value="pgta">PGT-A</option>
              <option value="nipt_docker">NIPT Docker</option>
            </select>
          </label>
          <label>
            <span>Status</span>
            <select aria-label="Status" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="all">All</option>
              <option value="created">created</option>
              <option value="submitted">submitted</option>
              <option value="running">running</option>
              <option value="success">success</option>
              <option value="failed">failed</option>
              <option value="queued">queued</option>
            </select>
          </label>
          <label>
            <span>Sort</span>
            <select aria-label="Sort" value={sort} onChange={(event) => setSort(event.target.value)}>
              <option value="created_desc">Created newest</option>
              <option value="duration">Duration</option>
              <option value="status">Status severity</option>
            </select>
          </label>
          <label className="grow">
            <span>Keyword</span>
            <input aria-label="Keyword" value={keyword} placeholder="run_id, pipeline, status" onChange={(event) => setKeyword(event.target.value)} />
          </label>
        </div>
        <div className="bulk-actions" aria-label="Batch actions">
          <button className="button ghost" type="button" disabled>Retry selected</button>
          <button className="button ghost" type="button" disabled>Cancel selected</button>
          <button className="button ghost" type="button" disabled>Archive selected</button>
          <span className="muted">Batch actions are UI placeholders; PGT-A resume is available from run detail when backend guardrails allow it.</span>
        </div>
        {loading ? <p className="muted">Loading runs...</p> : null}
        {error ? <div className="inline-error" role="alert">{error}</div> : null}
        <RunTable runs={filteredRuns} />
      </section>
    </div>
  );
}
