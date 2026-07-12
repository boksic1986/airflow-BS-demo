import {Link} from "react-router-dom";

import type {RunSummary} from "../api";

import {compactPipelineName, formatDate, formatDuration} from "../lib/format";
import {StatusBadge} from "./StatusBadge";
import {WorkflowStageRail} from "./WorkflowStageRail";

export function RunTable({
  runs,
  compact = false,
  emptyLabel = "No runs match the current filters.",
}: {
  runs: RunSummary[];
  compact?: boolean;
  emptyLabel?: string;
}) {
  return (
    <div className="table-wrap">
      <table className={compact ? "data-table compact" : "data-table"}>
        <thead>
          <tr>
            <th>project</th>
            <th>pipeline</th>
            <th>samples</th>
            <th>status</th>
            <th>workflow</th>
            <th>submitted / started</th>
            <th>duration</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.analysis_id}>
              <td>
                <Link className="resource-link" to={`/runs/${encodeURIComponent(run.analysis_id)}`}>
                  {run.project_name || run.analysis_id}
                </Link>
                <Link className="resource-link secondary" to={`/runs/${encodeURIComponent(run.analysis_id)}`}>
                  {run.analysis_id}
                </Link>
                <small className="muted">Operator {run.submitted_by || "not captured"}</small>
              </td>
              <td>{compactPipelineName(run.pipeline)}</td>
              <td>{run.sample_count ?? 0}</td>
              <td>
                <StatusBadge status={run.status} />
              </td>
              <td>
                <WorkflowStageRail analysisId={run.analysis_id} pipeline={run.pipeline} stages={run.workflow_summary} />
              </td>
              <td><span className="block">Submitted {formatDate(run.submitted_at)}</span><small>Started {formatDate(run.started_at)}</small></td>
              <td>{formatDuration(run.started_at, run.ended_at)}</td>
            </tr>
          ))}
          {runs.length === 0 ? (
            <tr>
              <td colSpan={7} className="empty-cell">
                {emptyLabel}
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
