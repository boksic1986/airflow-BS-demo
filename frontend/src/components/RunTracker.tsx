import {useEffect, useState} from "react";
import {Link} from "react-router-dom";

import type {DashboardRunTrackerRow} from "../api";

import {compactPipelineName, displayTimeZoneLabel, formatDate, formatRelativeAge, formatSecondsDuration} from "../lib/format";
import {humanStageLabel, stageDebugLabel} from "../lib/stageLabels";
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
              placeholder="project, run, or intake batch"
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
                <th scope="col">Pipeline</th>
                <th scope="col">Status</th>
                <th scope="col">Current stage</th>
                <th scope="col">Progress</th>
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
  const rawStep = status === "success" ? null : row.current_pipeline_rule || row.current_airflow_task;
  const currentStep = status === "success" ? "Completed" : row.current_stage_label || (rawStep ? humanStageLabel(rawStep) : row.not_in_airflow ? "Created only" : "No rule events captured");
  const debugStep = stageDebugLabel(rawStep);
  const note = row.note || progressNote(row);
  const terminalAt = row.pipeline_finished_at || row.ended_at;
  const terminalAge = ["success", "failed", "terminated"].includes(status)
    ? formatRelativeAge(terminalAt, relativeNow)
    : null;
  return (
    <tr className={isActiveStatus(status) ? "run-tracker-row active" : "run-tracker-row"}>
      <td>
        <Link className="tracker-primary-link" to={`/runs/${encodeURIComponent(row.analysis_id)}`}>
          {row.project_name || row.analysis_id}
        </Link>
        <Link className="mono tracker-run-link" to={`/runs/${encodeURIComponent(row.analysis_id)}`}>
          {row.analysis_id}
        </Link>
        <span className="muted">Operator {row.submitted_by || "not captured"} / {row.sample_count ?? 0} samples</span>
      </td>
      <td>{compactPipelineName(row.pipeline)}</td>
      <td>
        <div className="tracker-badges stacked">
          <StatusBadge status={row.display_status || compositeStatus(row.status, row.qc_status)} />
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
          ) : <span>{row.current_stage_source || sourceFromRow(row)}</span>}
          {debugStep ? <small title="Raw Airflow task or pipeline event id">{debugStep}</small> : null}
          {row.current_airflow_task === "run_pgta_target" ? (
            <small>Legacy PGT-A single Airflow task; Snakemake carries the detailed rule progress.</small>
          ) : null}
        </div>
      </td>
      <td className="tracker-progress-cell">
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
      </td>
      <td>
        <div className={isActiveStatus(status) ? "runtime-cell active" : "runtime-cell"}>
          <strong>Elapsed {formatSecondsDuration(row.elapsed_seconds)}</strong>
          <span>{etaLabel(row)}</span>
        </div>
      </td>
      <td title={`Airflow handoff time, displayed in ${displayTimeZoneLabel()}`}>{row.submitted_at ? formatDate(row.submitted_at) : "Not submitted"}</td>
      <td title={`Pipeline completion time, displayed in ${displayTimeZoneLabel()}`}>{finishedLabel(row)}</td>
    </tr>
  );
}

function compositeStatus(runStatus: string, qcStatus: string): string {
  const workflow = normalizeStatus(runStatus);
  const qc = normalizeStatus(qcStatus);
  if (workflow !== "success") return workflow;
  if (["fail", "failed", "error"].includes(qc)) return "qc_failed";
  if (["warn", "warning"].includes(qc)) return "qc_warning";
  if (qc === "unknown") return "qc_pending";
  return "success";
}

function progressNote(row: DashboardRunTrackerRow): string {
  if (row.not_in_airflow) return "Created in backend only";
  if (row.current_pipeline_rule) return `Pipeline event: ${row.current_pipeline_rule}`;
  if (row.current_airflow_task) return `Airflow task: ${row.current_airflow_task}`;
  return row.progress_source === "estimate" ? "Demo progress estimate" : `Progress source: ${row.progress_source}`;
}

function sourceFromRow(row: DashboardRunTrackerRow): string {
  if (row.not_in_airflow) return "Backend state";
  if (row.current_pipeline_rule) return row.current_pipeline_rule === "nipt_mount_smoke" ? "Runner event" : "Snakemake rule event";
  if (row.current_airflow_task) return "Airflow project task";
  return "Backend state";
}

function etaLabel(row: DashboardRunTrackerRow): string {
  if (!isActiveStatus(normalizeStatus(row.status))) {
    return row.elapsed_seconds == null ? "Runtime not captured" : "Finished";
  }
  if (row.estimated_remaining_seconds == null) return "ETA needs history";
  return `ETA ~${formatSecondsDuration(row.estimated_remaining_seconds)}`;
}

function finishedLabel(row: DashboardRunTrackerRow): string {
  const finishedAt = row.pipeline_finished_at || row.ended_at;
  if (finishedAt) return formatDate(finishedAt);
  if (isActiveStatus(normalizeStatus(row.status))) return "In progress";
  return "Not captured";
}
