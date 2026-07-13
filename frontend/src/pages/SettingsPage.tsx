import {useCallback, useEffect, useRef, useState} from "react";
import {Link} from "react-router-dom";

import type {
  IntakeConfigResponse,
  IntakeDiscovery,
  IntakeDiscoveryState,
  IntakeLifecycle,
  IntakePipelineConfig,
  IntakeScanPreviewResponse,
  IntakeScannerStateResponse,
} from "../api";

import {
  getApiBaseUrl,
  getIntakeConfig,
  getIntakeScannerState,
  getIntakeStatus,
  previewIntakeScan,
} from "../api";
import {IntakeDiscoveryTable} from "../components/IntakeDiscoveryTable";
import {StatusBadge} from "../components/StatusBadge";
import {errorMessage} from "../lib/errors";
import {formatDate} from "../lib/format";

const discoveryPageSize = 10;

type DiscoveryPipeline = "all" | "pgta" | "nipt_docker";
type DiscoveryStateFilter = "all" | IntakeDiscoveryState;

export function SettingsPage() {
  const [config, setConfig] = useState<IntakeConfigResponse | null>(null);
  const [scanner, setScanner] = useState<IntakeScannerStateResponse | null>(null);
  const [discoveries, setDiscoveries] = useState<IntakeDiscovery[]>([]);
  const [discoveryTotal, setDiscoveryTotal] = useState(0);
  const [discoveryPipeline, setDiscoveryPipeline] = useState<DiscoveryPipeline>("all");
  const [discoveryState, setDiscoveryState] = useState<DiscoveryStateFilter>("all");
  const [discoveryLifecycle, setDiscoveryLifecycle] = useState<IntakeLifecycle>("all");
  const [discoveryKeyword, setDiscoveryKeyword] = useState("");
  const [discoveryOffset, setDiscoveryOffset] = useState(0);
  const [preview, setPreview] = useState<IntakeScanPreviewResponse | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [scannerLoading, setScannerLoading] = useState(true);
  const [discoveryLoading, setDiscoveryLoading] = useState(true);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [scannerError, setScannerError] = useState<string | null>(null);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const configRequest = useRef(0);
  const scannerRequest = useRef(0);
  const discoveryRequest = useRef(0);
  const previewRequest = useRef(0);

  const loadConfig = useCallback(async () => {
    const requestId = ++configRequest.current;
    setConfigLoading(true);
    setConfigError(null);
    try {
      const payload = await getIntakeConfig();
      if (requestId === configRequest.current) setConfig(payload);
    } catch (err) {
      if (requestId === configRequest.current) setConfigError(errorMessage(err));
    } finally {
      if (requestId === configRequest.current) setConfigLoading(false);
    }
  }, []);

  const loadScanner = useCallback(async () => {
    const requestId = ++scannerRequest.current;
    setScannerLoading(true);
    setScannerError(null);
    try {
      const payload = await getIntakeScannerState();
      if (requestId === scannerRequest.current) setScanner(payload);
    } catch (err) {
      if (requestId === scannerRequest.current) setScannerError(errorMessage(err));
    } finally {
      if (requestId === scannerRequest.current) setScannerLoading(false);
    }
  }, []);

  const loadDiscoveries = useCallback(async () => {
    const requestId = ++discoveryRequest.current;
    setDiscoveryLoading(true);
    setDiscoveryError(null);
    setDiscoveries([]);
    setDiscoveryTotal(0);
    try {
      const payload = await getIntakeStatus({
        pipeline: discoveryPipeline === "all" ? undefined : discoveryPipeline,
        state: discoveryState === "all" ? undefined : discoveryState,
        lifecycle: discoveryLifecycle,
        keyword: discoveryKeyword.trim() || undefined,
        limit: discoveryPageSize,
        offset: discoveryOffset,
      });
      if (requestId !== discoveryRequest.current) return;
      const total = payload.total ?? payload.items.length;
      if (discoveryOffset > 0 && discoveryOffset >= total) {
        const validOffset = total === 0 ? 0 : Math.floor((total - 1) / discoveryPageSize) * discoveryPageSize;
        setDiscoveryOffset(validOffset);
        return;
      }
      setDiscoveries(payload.items);
      setDiscoveryTotal(total);
    } catch (err) {
      if (requestId === discoveryRequest.current) setDiscoveryError(errorMessage(err));
    } finally {
      if (requestId === discoveryRequest.current) setDiscoveryLoading(false);
    }
  }, [discoveryKeyword, discoveryLifecycle, discoveryOffset, discoveryPipeline, discoveryState]);

  const loadPreview = useCallback(async () => {
    const requestId = ++previewRequest.current;
    setPreviewLoading(true);
    setPreviewError(null);
    setPreview(null);
    try {
      const payload = await previewIntakeScan({pipelines: ["pgta", "nipt_docker"], max_samples: 200});
      if (requestId === previewRequest.current) setPreview(payload);
    } catch (err) {
      if (requestId === previewRequest.current) setPreviewError(errorMessage(err));
    } finally {
      if (requestId === previewRequest.current) setPreviewLoading(false);
    }
  }, []);

  useEffect(() => { void loadConfig(); }, [loadConfig]);
  useEffect(() => { void loadScanner(); }, [loadScanner]);
  useEffect(() => { void loadDiscoveries(); }, [loadDiscoveries]);

  function updateDiscoveryPipeline(value: DiscoveryPipeline) {
    setDiscoveryPipeline(value);
    setDiscoveryOffset(0);
  }

  function updateDiscoveryState(value: DiscoveryStateFilter) {
    setDiscoveryState(value);
    setDiscoveryOffset(0);
  }

  function updateDiscoveryLifecycle(value: IntakeLifecycle) {
    setDiscoveryLifecycle(value);
    setDiscoveryOffset(0);
  }

  function updateDiscoveryKeyword(value: string) {
    setDiscoveryKeyword(value);
    setDiscoveryOffset(0);
  }

  function refreshSettings() {
    void loadConfig();
    void loadScanner();
    void loadDiscoveries();
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Demo configuration</p>
          <h1>Platform Settings</h1>
          <p>Non-secret frontend configuration and intake scanner readiness.</p>
        </div>
      </section>

      <section className="panel platform-settings-summary">
        <dl className="definition-grid">
          <div><dt>Environment</dt><dd>Demo / Local</dd></div>
          <div><dt>API base</dt><dd className="path-text">{getApiBaseUrl()}</dd></div>
          <div><dt>Airflow UI</dt><dd>{`${window.location.protocol}//${window.location.hostname}:12958`}</dd></div>
          <div><dt>Secrets</dt><dd>Not displayed in frontend</dd></div>
          <div><dt>Remote acceptance</dt><dd>Runtime validation must run on ssh fengxian</dd></div>
          <div><dt>Deployment scope</dt><dd>Current frontend demo exposes PGT-A and NIPT Docker only.</dd></div>
        </dl>
      </section>

      <section className="panel intake-settings-panel">
        <div className="section-heading split intake-settings-heading">
          <div>
            <p className="eyebrow">Read-only operator check</p>
            <h2>Intake Scanner</h2>
            <p>Active intake policy, manifest inbox, discovery state, and Airflow scanner DAG status.</p>
          </div>
          <div className="panel-actions">
            <Link className="button ghost" to="/dashboard">View Dashboard</Link>
            <Link className="button ghost" to="/runs">View Runs</Link>
            <button className="button ghost" type="button" onClick={loadPreview} aria-label="Preview configured intake roots">
              Preview configured roots
            </button>
            <button className="button" type="button" onClick={refreshSettings} aria-label="Refresh intake scanner">
              Refresh
            </button>
          </div>
        </div>

        <IntakeSettingsContent
          config={config}
          configError={configError}
          configLoading={configLoading}
          discoveries={discoveries}
          discoveryError={discoveryError}
          discoveryKeyword={discoveryKeyword}
          discoveryLifecycle={discoveryLifecycle}
          discoveryLoading={discoveryLoading}
          discoveryOffset={discoveryOffset}
          discoveryPipeline={discoveryPipeline}
          discoveryState={discoveryState}
          discoveryTotal={discoveryTotal}
          onDiscoveryKeywordChange={updateDiscoveryKeyword}
          onDiscoveryLifecycleChange={updateDiscoveryLifecycle}
          onDiscoveryOffsetChange={setDiscoveryOffset}
          onDiscoveryPipelineChange={updateDiscoveryPipeline}
          onDiscoveryStateChange={updateDiscoveryState}
          preview={preview}
          previewError={previewError}
          previewLoading={previewLoading}
          scanner={scanner}
          scannerError={scannerError}
          scannerLoading={scannerLoading}
        />
      </section>
    </div>
  );
}

function IntakeSettingsContent({
  config,
  discoveries,
  scanner,
  configLoading,
  configError,
  scannerLoading,
  scannerError,
  discoveryLoading,
  discoveryError,
  discoveryTotal,
  discoveryOffset,
  discoveryPipeline,
  discoveryState,
  discoveryKeyword,
  discoveryLifecycle,
  onDiscoveryPipelineChange,
  onDiscoveryStateChange,
  onDiscoveryKeywordChange,
  onDiscoveryLifecycleChange,
  onDiscoveryOffsetChange,
  preview,
  previewLoading,
  previewError,
}: {
  config: IntakeConfigResponse | null;
  discoveries: IntakeDiscovery[];
  scanner: IntakeScannerStateResponse | null;
  configLoading: boolean;
  configError: string | null;
  scannerLoading: boolean;
  scannerError: string | null;
  discoveryLoading: boolean;
  discoveryError: string | null;
  discoveryTotal: number;
  discoveryOffset: number;
  discoveryPipeline: DiscoveryPipeline;
  discoveryState: DiscoveryStateFilter;
  discoveryKeyword: string;
  discoveryLifecycle: IntakeLifecycle;
  onDiscoveryPipelineChange: (value: DiscoveryPipeline) => void;
  onDiscoveryStateChange: (value: DiscoveryStateFilter) => void;
  onDiscoveryKeywordChange: (value: string) => void;
  onDiscoveryLifecycleChange: (value: IntakeLifecycle) => void;
  onDiscoveryOffsetChange: (value: number) => void;
  preview: IntakeScanPreviewResponse | null;
  previewLoading: boolean;
  previewError: string | null;
}) {
  const pageStart = discoveryTotal === 0 ? 0 : discoveryOffset + 1;
  const pageEnd = Math.min(discoveryOffset + discoveryPageSize, discoveryTotal);
  return (
    <div className="intake-settings-stack">
      <div className="intake-settings-grid">
        <ScannerStateCard error={scannerError} loading={scannerLoading} scanner={scanner} />
        <ConfigSummaryCard config={config} error={configError} loading={configLoading} />
      </div>

      <PreviewCard preview={preview} loading={previewLoading} error={previewError} />

      <div className="section-heading tight">
        <h3>Configured roots</h3>
        <p>Browser payloads show container paths only; host paths stay out of the frontend.</p>
      </div>
      {configLoading ? <p className="empty-state">Loading configured roots...</p> : null}
      {configError ? <p className="error-text">Configured roots unavailable: {configError}</p> : null}
      {!configLoading && !configError ? (
        <div className="settings-root-grid">
          {Object.entries(config?.pipelines || {}).map(([pipeline, pipelineConfig]) => (
            <PipelineRootCard key={pipeline} pipeline={pipeline} config={pipelineConfig} />
          ))}
        </div>
      ) : null}

      <div className="settings-discovery-section">
        <div className="section-heading tight">
          <h3>Discovery records</h3>
          <p>One row per discovered batch. Bootstrap and observed records are passive state, not queued workflow execution.</p>
        </div>
        <div className="filter-bar resource-filter-bar discovery-controls">
          <label>
            <span>Lifecycle</span>
            <select
              aria-label="Discovery lifecycle"
              value={discoveryLifecycle}
              onChange={(event) => onDiscoveryLifecycleChange(event.target.value as IntakeLifecycle)}
            >
              <option value="active">Active</option>
              <option value="archived">Archived</option>
              <option value="all">All</option>
            </select>
          </label>
          <label>
            <span>Pipeline</span>
            <select
              aria-label="Discovery pipeline"
              value={discoveryPipeline}
              onChange={(event) => onDiscoveryPipelineChange(event.target.value as DiscoveryPipeline)}
            >
              <option value="all">All deployed</option>
              <option value="pgta">PGT-A</option>
              <option value="nipt_docker">NIPT Docker</option>
            </select>
          </label>
          <label>
            <span>Discovery state</span>
            <select
              aria-label="Discovery state"
              value={discoveryState}
              onChange={(event) => onDiscoveryStateChange(event.target.value as DiscoveryStateFilter)}
            >
              <option value="all">All states</option>
              <option value="bootstrap">Bootstrap observed</option>
              <option value="observed">Observed</option>
              <option value="ready">Stable ready</option>
              <option value="submitted">Auto-submitted</option>
              <option value="error">Error</option>
              <option value="disabled">Disabled</option>
            </select>
          </label>
          <label className="grow">
            <span>Search</span>
            <input
              aria-label="Search discovery records"
              onChange={(event) => onDiscoveryKeywordChange(event.target.value)}
              placeholder="batch or analysis ID"
              type="search"
              value={discoveryKeyword}
            />
          </label>
        </div>
        <IntakeDiscoveryTable
          ariaLabel="Discovery records"
          emptyMessage="No discovery records match the current filters."
          error={discoveryError ? `Discovery records unavailable: ${discoveryError}` : null}
          items={discoveries}
          loading={discoveryLoading}
        />
        <div className="pagination-controls" aria-label="Discovery pagination">
          <span>{pageStart}-{pageEnd} of {discoveryTotal}</span>
          <div>
            <button
              aria-label="Previous discovery page"
              disabled={discoveryOffset === 0 || discoveryLoading}
              type="button"
              onClick={() => onDiscoveryOffsetChange(Math.max(0, discoveryOffset - discoveryPageSize))}
            >
              Previous page
            </button>
            <button
              aria-label="Next discovery page"
              disabled={discoveryOffset + discoveryPageSize >= discoveryTotal || discoveryLoading}
              type="button"
              onClick={() => onDiscoveryOffsetChange(discoveryOffset + discoveryPageSize)}
            >
              Next page
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function PreviewCard({preview, loading, error}: {preview: IntakeScanPreviewResponse | null; loading: boolean; error: string | null}) {
  const summary = preview?.summary;
  const metrics = summary ? [
    {label: "Batches", value: summary.total_batches},
    {label: "Stable ready", value: summary.stable_ready},
    {label: "Would create", value: summary.would_create},
    {label: "Would submit", value: summary.would_submit},
    {label: "Blocked by config", value: summary.blocked_auto_submit},
    {label: "Bootstrap protected", value: summary.bootstrap_protected},
  ] : [];
  return (
    <div className="settings-status-card intake-preview-card">
      <div className="section-heading tight">
        <div>
          <h3>Dry-run scan preview</h3>
          <p>Read-only preview: no DB writes, no run creation, and no Airflow submit.</p>
        </div>
        <StatusBadge status={error ? "warning" : summary?.would_submit ? "warning" : summary ? "success" : "unknown"} size="sm" />
      </div>
      {loading ? <p className="empty-state">Previewing configured roots...</p> : null}
      {error ? <p className="error-text" role="alert">{error}</p> : null}
      {!loading && !error && !preview ? (
        <p className="empty-state">Use Preview configured roots to review discovery behavior before changing intake policy.</p>
      ) : null}
      {summary ? (
        <>
          <div className="settings-preview-summary" aria-label="Intake preview summary">
            {metrics.map((metric) => (
              <div key={metric.label}>
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>
          <div className="settings-preview-list">
            {preview.items.slice(0, 8).map((item) => (
              <div className="settings-preview-row" key={`${item.pipeline}-${item.root_path}-${item.batch_id}`}>
                <div>
                  <strong>{item.batch_id}</strong>
                  <span>{pipelineLabel(item.pipeline)} · {reasonLabel(item.reason)}</span>
                </div>
                <div className="settings-preview-flags">
                  <span>{item.would_transition_to}</span>
                  <span>{item.would_create_run ? "would create" : "no create"}</span>
                  <span>{item.would_submit ? "would submit" : "no submit"}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

function ScannerStateCard({
  scanner,
  loading,
  error,
}: {
  scanner: IntakeScannerStateResponse | null;
  loading: boolean;
  error: string | null;
}) {
  const pausedLabel = scanner?.is_paused == null ? "Unknown" : scanner.is_paused ? "Paused" : "Unpaused";
  return (
    <div className="settings-status-card">
      <div className="section-heading tight">
        <h3>Airflow scanner DAG</h3>
        <StatusBadge status={error ? "warning" : loading ? "running" : scanner?.airflow_reachable ? "success" : "warning"} size="sm" />
      </div>
      {loading ? <p className="empty-state">Loading scanner DAG state...</p> : null}
      {error ? <p className="error-text" role="alert">Scanner state unavailable: {error}</p> : null}
      {!loading && !error ? (
        <dl className="definition-grid compact">
          <div><dt>DAG</dt><dd>{scanner?.dag_id || "bio_intake_scan"}</dd></div>
          <div><dt>Scheduler state</dt><dd>{pausedLabel}</dd></div>
          <div><dt>Airflow</dt><dd>{scanner?.airflow_reachable ? "Airflow reachable" : "Airflow unavailable"}</dd></div>
          <div><dt>Latest state</dt><dd>{scanner?.latest_dag_run_state ? <StatusBadge status={scanner.latest_dag_run_state} size="sm" /> : "not reported"}</dd></div>
          <div><dt>Latest DAG run</dt><dd className="path-text" title={scanner?.latest_dag_run_id || undefined}>{scanner?.latest_dag_run_id || "not reported"}</dd></div>
          <div><dt>Started</dt><dd>{formatDate(scanner?.latest_start_date)}</dd></div>
          <div><dt>Ended</dt><dd>{formatDate(scanner?.latest_end_date)}</dd></div>
          <div><dt>Message</dt><dd>{scanner?.message || "Scanner state loaded"}</dd></div>
        </dl>
      ) : null}
    </div>
  );
}

function ConfigSummaryCard({
  config,
  loading,
  error,
}: {
  config: IntakeConfigResponse | null;
  loading: boolean;
  error: string | null;
}) {
  const defaults = config?.defaults || {};
  return (
    <div className="settings-status-card">
      <div className="section-heading tight">
        <h3>Intake config</h3>
        <StatusBadge status={error ? "warning" : loading ? "running" : config ? "success" : "unknown"} size="sm" />
      </div>
      {loading ? <p className="empty-state">Loading intake configuration...</p> : null}
      {error ? <p className="error-text" role="alert">Intake configuration unavailable: {error}</p> : null}
      {!loading && !error ? (
        <dl className="definition-grid compact">
          <div><dt>Config source</dt><dd className="path-text" title={config?.source || undefined}>{config?.source || "not loaded"}</dd></div>
          <div><dt>Ready rule</dt><dd>{defaults.ready_rule || "not configured"}</dd></div>
          <div><dt>Stability</dt><dd>{defaults.stable_scans == null ? "not configured" : `${defaults.stable_scans} stable scans`}</dd></div>
          <div><dt>Default auto submit</dt><dd>{defaults.auto_submit ? "enabled" : "disabled"}</dd></div>
        </dl>
      ) : null}
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
            <span className="path-text" title={root.container_path}>{root.container_path}</span>
          </div>
        ))}
      </div>
      <div className="settings-mini-grid">
        {config.intake?.mode ? (
          <>
            <span>intake mode</span><strong>{config.intake.mode || "not configured"}</strong>
            <span>manifest inbox</span><strong className="path-text">{config.intake.inbox_root || "not configured"}</strong>
            <span>data root</span><strong className="path-text">{config.intake.data_root || "not configured"}</strong>
            <span>manifest pattern</span><strong>{config.intake.manifest_glob || "not configured"}</strong>
            <span>READY marker</span><strong>{config.intake.ready_suffix || "not configured"}</strong>
            <span>intake stability</span><strong>{config.intake.stable_scans == null ? "pipeline default" : `${config.intake.stable_scans} scans`}</strong>
          </>
        ) : null}
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

function reasonLabel(reason: string): string {
  const labels: Record<string, string> = {
    new_batch_observed: "new batch would be observed",
    fingerprint_changed: "fingerprint changed; would observe again",
    manifest_changed_after_observation: "READY manifest changed; manual review required",
    bootstrap_protected: "bootstrap protected",
    already_submitted: "already auto-submitted",
    auto_submit_enabled: "auto-submit enabled",
    auto_submit_disabled: "auto-submit disabled by config",
  };
  return labels[reason] || reason;
}
