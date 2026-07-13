import {Link} from "react-router-dom";

import type {IntakeDiscovery} from "../api";

import {compactPipelineName, displayTimeZoneLabel, formatBytes, formatDate} from "../lib/format";
import {intakeDisplay} from "../lib/intake";
import {StatusBadge} from "./StatusBadge";

export function IntakeDiscoveryTable({
  items,
  ariaLabel,
  loading = false,
  error = null,
  emptyMessage = "No intake discovery records yet.",
}: {
  items: IntakeDiscovery[];
  ariaLabel: string;
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
}) {
  return (
    <div className="intake-discovery-surface" aria-busy={loading}>
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {loading && items.length === 0 ? <p className="muted panel-loading">Loading intake records...</p> : null}
      {items.length ? (
        <div className="intake-discovery-table-wrap">
          <table aria-label={ariaLabel} className="intake-discovery-table">
            <thead>
              <tr>
                <th scope="col">Project / Batch</th>
                <th scope="col">Pipeline</th>
                <th scope="col">Status</th>
                <th scope="col">Current stage</th>
                <th scope="col">Progress</th>
                <th scope="col">Samples</th>
                <th scope="col">Started</th>
                <th scope="col">Finished</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const display = intakeDisplay(item);
                return (
                  <tr key={`${item.pipeline}-${item.root_path}-${item.batch_id}`}>
                    <td className="discovery-batch-cell">
                      {item.analysis_id ? (
                        <Link className="tracker-primary-link" to={`/runs/${encodeURIComponent(item.analysis_id)}`}>
                          {item.project_name || item.batch_id}
                        </Link>
                      ) : <strong>{item.batch_id}</strong>}
                      {item.analysis_id ? (
                        <Link className="mono discovery-analysis-link" to={`/runs/${encodeURIComponent(item.analysis_id)}`}>
                          {item.analysis_id}
                        </Link>
                      ) : null}
                      <span className="muted intake-root" title={item.root_path}>{item.root_path}</span>
                    </td>
                    <td>{compactPipelineName(item.pipeline)}</td>
                    <td>
                      {item.analysis_id ? <StatusBadge status={item.display_status || item.analysis_status || "submitted"} /> : (
                        <span className={`intake-state-pill ${display.tone}`}>{display.label}</span>
                      )}
                    </td>
                    <td>
                      <div className="current-stage-cell">
                        <strong>{item.current_stage || discoveryStage(item)}</strong>
                        <span>{item.analysis_id ? "Pipeline state" : `${item.file_count} files / ${formatBytes(item.total_bytes)}`}</span>
                      </div>
                    </td>
                    <td>
                      <div className="intake-progress" aria-label={`${item.batch_id} progress`}>
                        <span>{Math.round(item.progress_percent || 0)}%</span>
                        <div className="intake-progress-track"><i style={{width: `${Math.max(0, Math.min(100, item.progress_percent || 0))}%`}} /></div>
                      </div>
                    </td>
                    <td>{item.sample_count || Math.floor(item.file_count / 2) || "-"}</td>
                    <td title={`Displayed in ${displayTimeZoneLabel()}`}>{item.submitted_at ? formatDate(item.submitted_at) : "Not submitted"}</td>
                    <td title={`Displayed in ${displayTimeZoneLabel()}`}>{item.pipeline_finished_at ? formatDate(item.pipeline_finished_at) : item.analysis_id ? "In progress" : "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : !loading && !error ? <p className="empty-state">{emptyMessage}</p> : null}
    </div>
  );
}

function discoveryStage(item: IntakeDiscovery): string {
  if (item.submit_state === "bootstrap") return "Bootstrap protected";
  if (item.ready_state === "ready") return "Stable ready";
  if (item.ready_state === "error" || item.submit_state === "error") return "Discovery error";
  return `Observed · ${item.stable_observation_count || 0}/2 checks`;
}
