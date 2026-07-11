import {Link} from "react-router-dom";

import type {IntakeDiscovery} from "../api";

import {compactPipelineName, formatBytes, formatDate} from "../lib/format";
import {intakeDisplay} from "../lib/intake";

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
                <th scope="col">Batch</th>
                <th scope="col">Pipeline</th>
                <th scope="col">Discovery status</th>
                <th scope="col">Files / Size</th>
                <th scope="col">Last seen</th>
                <th scope="col">Analysis</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const display = intakeDisplay(item);
                return (
                  <tr key={`${item.pipeline}-${item.root_path}-${item.batch_id}`}>
                    <td className="discovery-batch-cell">
                      <strong>{item.batch_id}</strong>
                      <span className="muted intake-root" title={item.root_path}>{item.root_path}</span>
                    </td>
                    <td>{compactPipelineName(item.pipeline)}</td>
                    <td><span className={`intake-state-pill ${display.tone}`}>{display.label}</span></td>
                    <td>{item.file_count} files / {formatBytes(item.total_bytes)}</td>
                    <td>{formatDate(item.last_seen_at)}</td>
                    <td>
                      {item.analysis_id ? (
                        <Link className="mono discovery-analysis-link" to={`/runs/${encodeURIComponent(item.analysis_id)}`}>
                          {item.analysis_id}
                        </Link>
                      ) : <span className="muted">Not submitted</span>}
                    </td>
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
