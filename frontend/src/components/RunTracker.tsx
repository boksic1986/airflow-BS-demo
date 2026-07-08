import {Link} from "react-router-dom";

import type {DashboardRunTrackerRow} from "../api";

import {compactPipelineName, formatDate, formatDuration} from "../lib/format";
import {isActiveStatus, normalizeStatus} from "../lib/status";
import {RunProgressBar} from "./RunProgressBar";
import {StatusBadge} from "./StatusBadge";

export type RunTrackerFilter = "all" | "active" | "created" | "failed" | "success";

const filters: Array<{value: RunTrackerFilter; label: string}> = [
  {value: "all", label: "All"},
  {value: "active", label: "Running"},
  {value: "created", label: "Created only"},
  {value: "failed", label: "Failed"},
  {value: "success", label: "Success"},
];

export function RunTracker({
  rows,
  total,
  limit,
  offset,
  filter,
  keyword,
  onFilterChange,
  onKeywordChange,
  onPageChange,
  onSubmit,
  onSync,
}: {
  rows: DashboardRunTrackerRow[];
  total: number;
  limit: number;
  offset: number;
  filter: RunTrackerFilter;
  keyword: string;
  onFilterChange: (filter: RunTrackerFilter) => void;
  onKeywordChange: (keyword: string) => void;
  onPageChange: (offset: number) => void;
  onSubmit: (analysisId: string) => void;
  onSync: (analysisId: string) => void;
}) {
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + limit, total);
  const canGoPrevious = offset > 0;
  const canGoNext = offset + limit < total;

  return (
    <section className="panel run-tracker-panel">
      <div className="section-heading split">
        <div>
          <h2>Run Tracker</h2>
          <p>Current pipeline context, one page at a time. Active runs stay first; terminal runs are ordered by recency.</p>
        </div>
        <div className="tracker-controls">
          <label className="tracker-search">
            <span>Search tracker</span>
            <input
              aria-label="Search tracker"
              onChange={(event) => onKeywordChange(event.target.value)}
              placeholder="project or run id"
              type="search"
              value={keyword}
            />
          </label>
          <div className="tracker-filters" aria-label="Run tracker filters">
            {filters.map((option) => (
              <button
                className={filter === option.value ? "active" : ""}
                key={option.value}
                type="button"
                onClick={() => onFilterChange(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="run-tracker-list">
        {rows.map((row) => (
          <RunTrackerRow
            key={row.analysis_id}
            onSubmit={onSubmit}
            onSync={onSync}
            row={row}
          />
        ))}
        {rows.length === 0 ? <p className="empty-state">No runs match the current pipeline and status filter.</p> : null}
      </div>
      <div className="pagination-controls" aria-label="Run tracker pagination">
        <span>{pageStart}-{pageEnd} of {total}</span>
        <div>
          <button disabled={!canGoPrevious} type="button" onClick={() => onPageChange(Math.max(0, offset - limit))}>
            Previous page
          </button>
          <button disabled={!canGoNext} type="button" onClick={() => onPageChange(offset + limit)}>
            Next page
          </button>
        </div>
      </div>
    </section>
  );
}

function RunTrackerRow({
  row,
  onSubmit,
  onSync,
}: {
  row: DashboardRunTrackerRow;
  onSubmit: (analysisId: string) => void;
  onSync: (analysisId: string) => void;
}) {
  const status = normalizeStatus(row.status);
  const currentStep = row.current_pipeline_rule || row.current_airflow_task || (row.not_in_airflow ? "Created only" : "No rule events captured");
  const note = row.note || progressNote(row);
  return (
    <article className="run-tracker-row">
      <div className="run-tracker-main">
        <div>
          <strong>{row.project_name || row.analysis_id}</strong>
          <span className="mono">{row.analysis_id}</span>
        </div>
        <div className="tracker-badges">
          <StatusBadge status={row.status} />
          <span className="handoff-pill neutral">{compactPipelineName(row.pipeline)}</span>
          <StatusBadge status={row.qc_status || "unknown"} size="sm" />
          {row.not_in_airflow ? <span className="handoff-pill">Not in Airflow</span> : null}
        </div>
      </div>
      <RunProgressBar
        analysisId={row.analysis_id}
        progress={{
          percent: row.percent,
          label: `${Math.round(row.percent)}%`,
          currentStep,
          note,
          notInAirflow: row.not_in_airflow,
        }}
      />
      <dl className="run-tracker-meta">
        <div><dt>samples</dt><dd>{row.sample_count ?? 0}</dd></div>
        <div><dt>created</dt><dd>{formatDate(row.created_at)}</dd></div>
        <div><dt>started</dt><dd>{formatDate(row.started_at)}</dd></div>
        <div><dt>duration</dt><dd>{formatDuration(row.started_at, row.ended_at)}</dd></div>
        <div><dt>Airflow task</dt><dd>{row.current_airflow_task || "not reported"}</dd></div>
        <div><dt>Pipeline rule</dt><dd>{row.current_pipeline_rule || "not captured"}</dd></div>
      </dl>
      <div className="run-tracker-actions">
        <Link className="button ghost" to={`/runs/${encodeURIComponent(row.analysis_id)}`}>View</Link>
        {status === "created" ? (
          <button className="button primary" type="button" onClick={() => onSubmit(row.analysis_id)}>Submit</button>
        ) : null}
        {isActiveStatus(status) ? (
          <button className="button ghost" type="button" onClick={() => onSync(row.analysis_id)}>Sync</button>
        ) : null}
      </div>
    </article>
  );
}

function progressNote(row: DashboardRunTrackerRow): string {
  if (row.not_in_airflow) return "Created in backend only";
  if (row.current_pipeline_rule) return `Pipeline event: ${row.current_pipeline_rule}`;
  if (row.current_airflow_task) return `Airflow task: ${row.current_airflow_task}`;
  return row.progress_source === "estimate" ? "Demo progress estimate" : `Progress source: ${row.progress_source}`;
}
