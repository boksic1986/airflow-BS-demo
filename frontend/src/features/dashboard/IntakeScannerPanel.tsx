import type {IntakeDiscovery} from "../../api";

import {IntakeDiscoveryTable} from "../../components/IntakeDiscoveryTable";
import {StatusBadge} from "../../components/StatusBadge";

export function IntakeScannerPanel({items, total, limit, offset, loading, error, onPageChange}: {
  items: IntakeDiscovery[];
  total: number;
  limit: number;
  offset: number;
  loading: boolean;
  error: string | null;
  onPageChange: (offset: number) => void;
}) {
  const pageStart = total === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + limit, total);
  return (
    <section className="panel intake-scanner-panel" aria-busy={loading}>
      <div className="section-heading split">
        <div>
          <h2>Intake scanner</h2>
          <p title="Observed and bootstrap states are discovery records, not queued analysis runs.">Configured root discovery</p>
        </div>
        <StatusBadge status={items.some((item) => item.submit_state === "submitted") ? "success" : "skipped"} />
      </div>
      <IntakeDiscoveryTable
        ariaLabel="Intake discovery records"
        error={error ? `Intake unavailable: ${error}` : null}
        items={items}
        loading={loading}
      />
      <div className="pagination-controls" aria-label="Intake scanner pagination">
        <span>{pageStart}-{pageEnd} of {total}</span>
        <div>
          <button aria-label="Previous intake page" disabled={offset === 0 || loading} type="button" onClick={() => onPageChange(Math.max(0, offset - limit))}>Previous intake</button>
          <button aria-label="Next intake page" disabled={offset + limit >= total || loading} type="button" onClick={() => onPageChange(offset + limit)}>Next intake</button>
        </div>
      </div>
    </section>
  );
}
