import {Link} from "react-router-dom";

import type {RunSummary} from "../api";

import {compactPipelineName, formatDate, formatDuration} from "../lib/format";
import {StatusBadge} from "./StatusBadge";

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
            <th>run_id</th>
            <th>pipeline</th>
            <th>samples</th>
            <th>status</th>
            <th>qc</th>
            <th>created_at</th>
            <th>duration</th>
            <th>action</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.analysis_id}>
              <td className="mono path-text">{run.analysis_id}</td>
              <td>{compactPipelineName(run.pipeline)}</td>
              <td>{run.sample_count ?? 0}</td>
              <td>
                <StatusBadge status={run.status} />
              </td>
              <td>
                <StatusBadge status={run.qc_status || "unknown"} size="sm" />
              </td>
              <td>{formatDate(run.created_at)}</td>
              <td>{formatDuration(run.started_at, run.ended_at)}</td>
              <td>
                <Link className="button ghost" to={`/runs/${encodeURIComponent(run.analysis_id)}`}>
                  View
                </Link>
              </td>
            </tr>
          ))}
          {runs.length === 0 ? (
            <tr>
              <td colSpan={8} className="empty-cell">
                {emptyLabel}
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
