import {Link} from "react-router-dom";

import type {IntakeDiscovery} from "../../api";

import {StatusBadge} from "../../components/StatusBadge";
import {compactPipelineName} from "../../lib/format";
import {intakeDisplay} from "../../lib/intake";

export function IntakeScannerPanel({items, loading, error}: {
  items: IntakeDiscovery[];
  loading: boolean;
  error: string | null;
}) {
  return (
    <section className="panel intake-scanner-panel" aria-busy={loading}>
      <div className="section-heading split">
        <div>
          <h2>Intake scanner</h2>
          <p title="Observed and bootstrap states are discovery records, not queued analysis runs.">Configured root discovery</p>
        </div>
        <StatusBadge status={items.some((item) => item.submit_state === "submitted") ? "success" : "skipped"} />
      </div>
      {error ? <div className="inline-error" role="alert">Intake unavailable: {error}</div> : null}
      {loading && items.length === 0 ? <p className="muted panel-loading">Loading intake records...</p> : null}
      {items.length ? (
        <div className="intake-table-wrap">
          <table className="intake-table">
            <thead><tr><th scope="col">Pipeline</th><th scope="col">Batch</th><th scope="col">Files / Size</th><th scope="col">Discovery state</th><th scope="col">Analysis</th></tr></thead>
            <tbody>
              {items.slice(0, 10).map((item) => {
                const display = intakeDisplay(item);
                return (
                  <tr key={`${item.pipeline}-${item.root_path}-${item.batch_id}`}>
                    <td>{compactPipelineName(item.pipeline)}</td>
                    <td><strong>{item.batch_id}</strong><span className="muted intake-root" title={item.root_path}>{item.root_path}</span></td>
                    <td>{item.file_count} files / {formatBytes(item.total_bytes)}</td>
                    <td><span className={`intake-state-pill ${display.tone}`}>{display.label}</span></td>
                    <td>{item.analysis_id ? <Link to={`/runs/${encodeURIComponent(item.analysis_id)}`}>{item.analysis_id}</Link> : <span className="muted">not submitted</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : !loading && !error ? <p className="empty-state">No intake discovery records yet.</p> : null}
    </section>
  );
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let unitIndex = 0;
  let scaled = value;
  while (scaled >= 1024 && unitIndex < units.length - 1) {
    scaled /= 1024;
    unitIndex += 1;
  }
  return `${scaled >= 10 || unitIndex === 0 ? scaled.toFixed(0) : scaled.toFixed(1)} ${units[unitIndex]}`;
}
