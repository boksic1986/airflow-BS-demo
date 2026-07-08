import {Link} from "react-router-dom";

import type {RuleEvent, RunDetail, RunProgressResponse, RunSummary} from "../api";

import {compactPipelineName, formatDate, formatDuration} from "../lib/format";
import {computeRunProgress, getProjectDisplayName, progressFromResponse} from "../lib/runProgress";
import {isActiveStatus, isFailedStatus, normalizeStatus} from "../lib/status";
import {RunProgressBar} from "./RunProgressBar";
import {StatusBadge} from "./StatusBadge";

export type RunTrackerFilter = "all" | "running" | "submitted" | "created" | "failed" | "qc_failed" | "success";

export type RunTrackerItem = {
  run: RunSummary;
  detail?: RunDetail | null;
  rules: RuleEvent[];
  progress?: RunProgressResponse | null;
};

const filters: Array<{value: RunTrackerFilter; label: string}> = [
  {value: "all", label: "All"},
  {value: "running", label: "Running"},
  {value: "submitted", label: "Submitted / queued"},
  {value: "created", label: "Created only"},
  {value: "failed", label: "Failed"},
  {value: "qc_failed", label: "QC failed"},
  {value: "success", label: "Success"},
];

export function RunTracker({
  items,
  filter,
  onFilterChange,
  onSubmit,
  onSync,
}: {
  items: RunTrackerItem[];
  filter: RunTrackerFilter;
  onFilterChange: (filter: RunTrackerFilter) => void;
  onSubmit: (analysisId: string) => void;
  onSync: (analysisId: string) => void;
}) {
  const visibleItems = sortTrackerItems(items).filter((item) => matchesFilter(item, filter));

  return (
    <section className="panel run-tracker-panel">
      <div className="section-heading split">
        <div>
          <h2>Run Tracker</h2>
          <p>Project-centric view of created, active, failed, QC-failed, and recently completed deployed runs.</p>
        </div>
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
      <div className="run-tracker-list">
        {visibleItems.map((item) => {
          const progress = item.progress ? progressFromResponse(item.progress) : computeRunProgress(item.run, item.detail, item.rules);
          const displayStatus = item.detail?.status || item.run.status;
          const projectName = getProjectDisplayName(item.run, item.detail);
          return (
            <article className="run-tracker-row" key={item.run.analysis_id}>
              <div className="run-tracker-main">
                <div>
                  <strong>{projectName}</strong>
                  {projectName !== item.run.analysis_id ? <span className="mono">{item.run.analysis_id}</span> : null}
                </div>
                <div className="tracker-badges">
                  <StatusBadge status={displayStatus} />
                  <span className="handoff-pill">{compactPipelineName(item.run.pipeline)}</span>
                  <StatusBadge status={item.run.qc_status || "unknown"} size="sm" />
                  {progress.notInAirflow ? <span className="handoff-pill">Not in Airflow</span> : null}
                </div>
              </div>
              <RunProgressBar analysisId={item.run.analysis_id} progress={progress} />
              <dl className="run-tracker-meta">
                <div><dt>samples</dt><dd>{item.run.sample_count ?? 0}</dd></div>
                <div><dt>created</dt><dd>{formatDate(item.run.created_at)}</dd></div>
                <div><dt>started</dt><dd>{formatDate(item.run.started_at)}</dd></div>
                <div><dt>duration</dt><dd>{formatDuration(item.run.started_at, item.run.ended_at)}</dd></div>
              </dl>
              <div className="run-tracker-actions">
                <Link className="button ghost" to={`/runs/${encodeURIComponent(item.run.analysis_id)}`}>View</Link>
                {normalizeStatus(displayStatus) === "created" ? (
                  <button className="button primary" type="button" onClick={() => onSubmit(item.run.analysis_id)}>Submit</button>
                ) : null}
                {isActiveStatus(displayStatus) ? (
                  <button className="button ghost" type="button" onClick={() => onSync(item.run.analysis_id)}>Sync</button>
                ) : null}
              </div>
            </article>
          );
        })}
        {visibleItems.length === 0 ? <p className="empty-state">No deployed runs match this tracker filter.</p> : null}
      </div>
    </section>
  );
}

function matchesFilter(item: RunTrackerItem, filter: RunTrackerFilter): boolean {
  const status = normalizeStatus(item.detail?.status || item.run.status);
  const qcStatus = normalizeStatus(item.run.qc_status);
  if (filter === "all") return true;
  if (filter === "running") return status === "running";
  if (filter === "submitted") return ["submitted", "queued", "scheduled"].includes(status);
  if (filter === "created") return status === "created";
  if (filter === "failed") return isFailedStatus(status);
  if (filter === "qc_failed") return isFailedStatus(qcStatus);
  if (filter === "success") return status === "success";
  return true;
}

function sortTrackerItems(items: RunTrackerItem[]): RunTrackerItem[] {
  return [...items].sort((left, right) => {
    const priorityDelta = trackerPriority(left) - trackerPriority(right);
    if (priorityDelta !== 0) return priorityDelta;
    return Date.parse(right.run.created_at || "") - Date.parse(left.run.created_at || "");
  });
}

function trackerPriority(item: RunTrackerItem): number {
  const status = normalizeStatus(item.detail?.status || item.run.status);
  if (isActiveStatus(status)) return 0;
  if (isFailedStatus(status) || isFailedStatus(item.run.qc_status)) return 1;
  if (status === "created") return 2;
  if (status === "success") return 3;
  return 4;
}
