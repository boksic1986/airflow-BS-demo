import {useEffect, useState} from "react";

import {getIntakeScannerState, type IntakeScannerStateResponse} from "../api";
import {usePlatformCapabilities} from "../features/platform/PlatformCapabilitiesContext";
import {errorMessage} from "../lib/errors";
import {formatDate} from "../lib/format";


export function SettingsPage() {
  const platform = usePlatformCapabilities();
  const [scanner, setScanner] = useState<IntakeScannerStateResponse | null>(null);
  const [scannerError, setScannerError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    getIntakeScannerState()
      .then((payload) => { if (!disposed) setScanner(payload); })
      .catch((error) => { if (!disposed) setScannerError(errorMessage(error)); });
    return () => { disposed = true; };
  }, []);

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Platform configuration</p>
          <h1>Settings</h1>
          <p>Registry-backed NGS capabilities and read-only intake health.</p>
        </div>
      </section>

      {platform.error ? <div className="inline-error" role="alert">Capabilities unavailable: {platform.error}</div> : null}
      <section className="panel">
        <div className="section-heading"><h2>Pipeline registry</h2><p>{platform.environment}</p></div>
        <div className="workflow-catalog-grid">
          {platform.pipelines.map((pipeline) => (
            <article className="resource-card" key={pipeline.id}>
              <div className="section-heading split">
                <div><h3>{pipeline.display_name}</h3><p className="mono">{pipeline.id}</p></div>
                <span className={`status-badge ${pipeline.enabled ? "success" : "queued"}`}>{pipeline.enabled ? "deployed" : "disabled"}</span>
              </div>
              <dl className="definition-grid compact">
                <div><dt>DAG</dt><dd>{pipeline.dag_id || "Not configured"}</dd></div>
                <div><dt>Version</dt><dd>{pipeline.version || "Adapter managed"}</dd></div>
                <div><dt>Targets</dt><dd>{pipeline.execution_targets.join(", ") || "None"}</dd></div>
                <div><dt>Capabilities</dt><dd>{pipeline.capabilities.join(", ") || "None"}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="section-heading"><h2>Intake scanner</h2><p>Provided by the deployed pipeline adapter.</p></div>
        {scannerError ? <div className="inline-error" role="alert">{scannerError}</div> : null}
        {!scanner && !scannerError ? <p className="muted">Loading scanner state...</p> : null}
        {scanner ? (
          <dl className="definition-grid compact">
            <div><dt>Scanner</dt><dd>{scanner.scanner || scanner.dag_id || "Registered intake"}</dd></div>
            <div><dt>Status</dt><dd>{scanner.last_status || scanner.latest_dag_run_state || "available"}</dd></div>
            <div><dt>Last completed</dt><dd>{formatDate(scanner.last_scan_completed_at || scanner.latest_end_date)}</dd></div>
            <div><dt>Message</dt><dd>{scanner.last_error || scanner.message || "Scanner state loaded"}</dd></div>
          </dl>
        ) : null}
      </section>
    </div>
  );
}
