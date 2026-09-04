import {useEffect, useState} from "react";

import type {DashboardRunTrackerRow} from "../api";

import {compactPipelineName, displayTimeZoneLabel, formatBytes, formatDate, formatProgressUnits, formatRelativeAge, formatSecondsDuration} from "../lib/format";
import {isActiveStatus, normalizeStatus} from "../lib/status";
import {RunProgressBar} from "./RunProgressBar";
import {StatusBadge} from "./StatusBadge";
import {OperationProjectCell, OperationRuntimeCell} from "./OperationCells";

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
  const [relativeNow, setRelativeNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setRelativeNow(new Date()), 60000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section className="panel run-tracker-panel">
      <div className="section-heading split">
        <div>
          <h2>Run Tracker</h2>
          <p>Current pipeline context, 10 runs per page. Active progress ranks first; equal progress uses the oldest submission first.</p>
        </div>
        <div className="tracker-controls">
          <label className="tracker-search">
            <span>Search operations</span>
            <input
              aria-label="Search operations"
              onChange={(event) => onKeywordChange(event.target.value)}
              placeholder="project, batch, sample, family, or run ID"
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
      {rows.length ? (
        <div className="run-tracker-table-wrap">
          <table className="run-tracker-table">
            <thead>
              <tr>
                <th scope="col">Project</th>
                <th scope="col">Batch</th>
                <th scope="col">Pipeline</th>
                <th scope="col">Status</th>
                <th scope="col">Current stage</th>
                <th scope="col">Stage progress</th>
                <th scope="col">Runtime / ETA</th>
                <th scope="col">Started</th>
                <th scope="col">Finished</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <RunTrackerRow
                  key={row.analysis_id}
                  onSubmit={onSubmit}
                  onSync={onSync}
                  row={row}
                  relativeNow={relativeNow}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty-state">No runs match the current pipeline and status filter.</p>
      )}
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
  relativeNow,
}: {
  row: DashboardRunTrackerRow;
  onSubmit: (analysisId: string) => void;
  onSync: (analysisId: string) => void;
  relativeNow: Date;
}) {
  const status = normalizeStatus(row.status);
  const currentStep = row.current_stage_label || (row.not_in_airflow ? "Preparing WGS batch" : "WGS stage unavailable");
  const note = row.note || progressNote(row);
  const terminalAt = row.pipeline_finished_at || row.ended_at;
  const terminalAge = ["success", "failed", "terminated"].includes(status)
    ? formatRelativeAge(terminalAt, relativeNow)
    : null;
  return (
    <tr className={isActiveStatus(status) ? "run-tracker-row active" : "run-tracker-row"}>
      <td>
        <OperationProjectCell analysisId={row.analysis_id} fallbackId={row.analysis_id} projectName={row.project_name} sampleCount={row.sample_count ?? 0} source={row.run_source || "manual"} sourceBatchId={row.source_batch_id} submittedBy={row.submitted_by} />
      </td>
      <td><strong>{row.batch_no || row.source_batch_id || "-"}</strong></td>
      <td>{compactPipelineName(row.pipeline)}</td>
      <td>
        <div className="tracker-badges stacked">
          <StatusBadge status={row.display_status || normalizeStatus(row.status)} />
          {row.not_in_airflow ? <span className="handoff-pill">Not in Airflow</span> : null}
          {status === "created" ? (
            <button className="mini-action" type="button" onClick={() => onSubmit(row.analysis_id)}>Submit</button>
          ) : null}
          {isActiveStatus(status) ? (
            <button className="mini-action" type="button" onClick={() => onSync(row.analysis_id)}>Sync</button>
          ) : null}
        </div>
      </td>
      <td>
        <div className="current-stage-cell">
          <strong>{currentStep}</strong>
          {terminalAge ? (
            <span className="terminal-age" title={`${formatDate(terminalAt)} ${displayTimeZoneLabel()}`}>{terminalAge}</span>
          ) : <span>{row.stage_status || row.status}</span>}
        </div>
      </td>
      <td className="tracker-progress-cell">
        <RunProgressBar analysisId={row.analysis_id} compact progress={{percent: row.stage_progress?.percent ?? row.percent ?? 0, available: row.stage_progress?.available ?? row.progress_available ?? false, label: row.stage_progress?.percent == null ? "Detailed progress unavailable" : `${Math.round(row.stage_progress.percent)}%`, currentStep, note, notInAirflow: row.not_in_airflow}} />
        {row.stage_progress?.available ? <small>{formatProgressUnits(row.stage_progress.completed_units, row.stage_progress.total_units, row.stage_progress.unit)}{row.stage_progress.speed_bps ? ` · ${formatBytes(row.stage_progress.speed_bps)}/s` : ""}{row.stage_progress.eta_seconds != null ? ` · ETA ${formatSecondsDuration(row.stage_progress.eta_seconds)}` : ""}</small> : null}
      </td>
      <td>
        <OperationRuntimeCell elapsedSeconds={row.elapsed_seconds} estimatedRemainingSeconds={row.estimated_remaining_seconds} status={row.status} submitted={Boolean(row.submitted_at)} />
      </td>
      <td title={`Airflow handoff time, displayed in ${displayTimeZoneLabel()}`}>{row.submitted_at ? formatDate(row.submitted_at) : "Not submitted"}</td>
      <td title={`Pipeline completion time, displayed in ${displayTimeZoneLabel()}`}>{finishedLabel(row)}</td>
    </tr>
  );
}

function progressNote(row: DashboardRunTrackerRow): string {
  if (row.not_in_airflow) return "Created in backend only";
  if (row.stage_progress?.current_item) return row.stage_progress.current_item;
  return row.stage_progress?.available ? `Progress source: ${row.stage_progress.source || row.progress_source}` : "The runtime has not supplied exact progress for this stage.";
}

function finishedLabel(row: DashboardRunTrackerRow): string {
  const finishedAt = row.pipeline_finished_at || row.ended_at;
  if (finishedAt) return formatDate(finishedAt);
  if (isActiveStatus(normalizeStatus(row.status))) return "In progress";
  return "Not captured";
}
