import type {IntakeDiscovery} from "../../api";

import {IntakeDiscoveryTable} from "../../components/IntakeDiscoveryTable";
import {StatusBadge} from "../../components/StatusBadge";

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
      <IntakeDiscoveryTable
        ariaLabel="Intake discovery records"
        error={error ? `Intake unavailable: ${error}` : null}
        items={items.slice(0, 10)}
        loading={loading}
      />
    </section>
  );
}
