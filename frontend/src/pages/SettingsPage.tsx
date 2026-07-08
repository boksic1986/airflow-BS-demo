import {useCallback, useEffect, useState} from "react";
import {Link} from "react-router-dom";

import type {
  IntakeConfigResponse,
  IntakeDiscovery,
  IntakePipelineConfig,
  IntakeScannerStateResponse,
} from "../api";

import {
  getApiBaseUrl,
  getIntakeConfig,
  getIntakeScannerState,
  getIntakeStatus,
} from "../api";
import {StatusBadge} from "../components/StatusBadge";
import {errorMessage} from "../lib/errors";
import {formatDate} from "../lib/format";
import {intakeDisplay} from "../lib/intake";

type IntakeSettingsState = {
  config: IntakeConfigResponse | null;
  discoveries: IntakeDiscovery[];
  scanner: IntakeScannerStateResponse | null;
};

export function SettingsPage() {
  const [state, setState] = useState<IntakeSettingsState>({config: null, discoveries: [], scanner: null});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadIntakeSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [config, status, scanner] = await Promise.all([
        getIntakeConfig(),
        getIntakeStatus({limit: 100}),
        getIntakeScannerState(),
      ]);
      setState({config, discoveries: status.items, scanner});
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([getIntakeConfig(), getIntakeStatus({limit: 100}), getIntakeScannerState()])
      .then(([config, status, scanner]) => {
        if (active) setState({config, discoveries: status.items, scanner});
      })
      .catch((err) => {
        if (active) setError(errorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Demo configuration</p>
          <h1>Settings</h1>
          <p>Non-secret frontend configuration and intake scanner readiness.</p>
        </div>
      </section>

      <section className="panel">
        <div className="definition-grid">
          <div><dt>Environment</dt><dd>Demo / Local</dd></div>
          <div><dt>API base</dt><dd className="path-text">{getApiBaseUrl()}</dd></div>
          <div><dt>Airflow UI</dt><dd>{`${window.location.protocol}//${window.location.hostname}:12958`}</dd></div>
          <div><dt>Secrets</dt><dd>Not displayed in frontend</dd></div>
          <div><dt>Remote acceptance</dt><dd>Runtime validation must run on ssh fengxian</dd></div>
          <div><dt>Deployment scope</dt><dd>Current frontend demo exposes PGT-A and NIPT Docker only.</dd></div>
        </div>
      </section>

      <section className="panel intake-settings-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Read-only operator check</p>
            <h2>Intake Scanner</h2>
            <p>Configuration, bootstrap state, and Airflow scanner DAG status before automatic intake is enabled.</p>
          </div>
          <div className="panel-actions">
            <Link className="button ghost" to="/dashboard">View Dashboard</Link>
            <Link className="button ghost" to="/runs">View Runs</Link>
            <button className="button" type="button" onClick={loadIntakeSettings} aria-label="Refresh intake scanner">
              Refresh
            </button>
          </div>
        </div>

        {loading ? <p className="empty-state">Loading intake scanner settings...</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        {!loading && !error ? <IntakeSettingsContent {...state} /> : null}
      </section>
    </div>
  );
}

function IntakeSettingsContent({config, discoveries, scanner}: IntakeSettingsState) {
  return (
    <div className="intake-settings-stack">
      <div className="intake-settings-grid">
        <ScannerStateCard scanner={scanner} />
        <ConfigSummaryCard config={config} />
      </div>

      <div className="section-heading tight">
        <h3>Configured roots</h3>
        <p>Browser payloads show container paths only; host paths stay out of the frontend.</p>
      </div>
      <div className="settings-root-grid">
        {Object.entries(config?.pipelines || {}).map(([pipeline, pipelineConfig]) => (
          <PipelineRootCard key={pipeline} pipeline={pipeline} config={pipelineConfig} />
        ))}
      </div>

      <div className="section-heading tight">
        <h3>Discovery records</h3>
        <p>Bootstrap and observed records are passive state; they are not queued workflow execution.</p>
      </div>
      <div className="settings-discovery-grid">
        {discoveries.slice(0, 12).map((item) => {
          const display = intakeDisplay(item);
          return (
            <div className="settings-discovery-card" key={`${item.pipeline}-${item.root_path}-${item.batch_id}`}>
              <div>
                <strong>{item.batch_id}</strong>
                <span>{item.pipeline}</span>
              </div>
              <span className={`intake-state-pill ${display.tone}`}>{display.label}</span>
              <p className="path-text">{item.root_path}</p>
              <div className="settings-mini-grid">
                <span>files</span><strong>{item.file_count}</strong>
                <span>last seen</span><strong>{formatDate(item.last_seen_at)}</strong>
              </div>
            </div>
          );
        })}
        {discoveries.length === 0 ? <p className="empty-state">No intake discovery records yet.</p> : null}
      </div>
    </div>
  );
}

function ScannerStateCard({scanner}: {scanner: IntakeScannerStateResponse | null}) {
  const pausedLabel = scanner?.is_paused == null ? "Unknown" : scanner.is_paused ? "Paused" : "Unpaused";
  return (
    <div className="settings-status-card">
      <div className="section-heading tight">
        <h3>Airflow scanner DAG</h3>
        <StatusBadge status={scanner?.airflow_reachable ? "success" : "warning"} size="sm" />
      </div>
      <div className="definition-grid compact">
        <div><dt>DAG</dt><dd>{scanner?.dag_id || "bio_intake_scan"}</dd></div>
        <div><dt>Scheduler state</dt><dd>{pausedLabel}</dd></div>
        <div><dt>Airflow</dt><dd>{scanner?.airflow_reachable ? "Airflow reachable" : "Airflow unavailable"}</dd></div>
        <div><dt>Latest state</dt><dd>{scanner?.latest_dag_run_state ? <StatusBadge status={scanner.latest_dag_run_state} size="sm" /> : "not reported"}</dd></div>
        <div><dt>Latest DAG run</dt><dd className="path-text">{scanner?.latest_dag_run_id || "not reported"}</dd></div>
        <div><dt>Started</dt><dd>{formatDate(scanner?.latest_start_date)}</dd></div>
        <div><dt>Ended</dt><dd>{formatDate(scanner?.latest_end_date)}</dd></div>
        <div><dt>Message</dt><dd>{scanner?.message || "Scanner state loaded"}</dd></div>
      </div>
    </div>
  );
}

function ConfigSummaryCard({config}: {config: IntakeConfigResponse | null}) {
  const defaults = config?.defaults || {};
  return (
    <div className="settings-status-card">
      <div className="section-heading tight">
        <h3>Intake config</h3>
        <StatusBadge status={config ? "success" : "unknown"} size="sm" />
      </div>
      <div className="definition-grid compact">
        <div><dt>Config source</dt><dd className="path-text">{config?.source || "not loaded"}</dd></div>
        <div><dt>Ready rule</dt><dd>{defaults.ready_rule || "not configured"}</dd></div>
        <div><dt>Stability</dt><dd>{defaults.stable_scans == null ? "not configured" : `${defaults.stable_scans} stable scans`}</dd></div>
        <div><dt>Default auto submit</dt><dd>{defaults.auto_submit ? "enabled" : "disabled"}</dd></div>
      </div>
    </div>
  );
}

function PipelineRootCard({pipeline, config}: {pipeline: string; config: IntakePipelineConfig}) {
  return (
    <div className="settings-root-card">
      <div className="section-heading tight">
        <h3>{pipelineLabel(pipeline)}</h3>
        <StatusBadge status={config.enabled ? "success" : "skipped"} size="sm" />
      </div>
      <div className="settings-root-list">
        {config.roots.map((root) => (
          <div key={`${pipeline}-${root.id}-${root.container_path}`}>
            <strong>{root.id}</strong>
            <span className="path-text">{root.container_path}</span>
          </div>
        ))}
      </div>
      <div className="settings-mini-grid">
        <span>file flavor</span><strong>{config.file_flavor || "pipeline default"}</strong>
        <span>R1 pattern</span><strong>{config.r1_pattern || "pipeline default"}</strong>
        <span>R2 pattern</span><strong>{config.r2_pattern || "pipeline default"}</strong>
        <span>ignore</span><strong>{config.ignore_patterns?.join(", ") || "none"}</strong>
        <span>auto submit</span><strong>{formatAutoSubmit(config.auto_submit)}</strong>
      </div>
    </div>
  );
}

function pipelineLabel(pipeline: string): string {
  if (pipeline === "pgta") return "PGT-A";
  if (pipeline === "nipt_docker") return "NIPT Docker";
  return pipeline;
}

function formatAutoSubmit(value?: Record<string, string | number | boolean | null>): string {
  if (!value || Object.keys(value).length === 0) return "not configured";
  return Object.entries(value)
    .map(([key, item]) => `${key}: ${String(item)}`)
    .join(", ");
}
