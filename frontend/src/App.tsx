import {
  Activity,
  AlertTriangle,
  Archive,
  Database,
  FileText,
  ListChecks,
  RefreshCw,
  RotateCw,
} from "lucide-react";
import {useEffect, useMemo, useState} from "react";

import {
  ApiError,
  Artifact,
  LogStream,
  RuleEvent,
  RunDetail,
  RunLog,
  RunSummary,
  Sample,
  getRunArtifacts,
  getRunDetail,
  getRunLog,
  getRunRules,
  getRunSamples,
  listRuns,
  syncAirflow,
} from "./api";

type RunBundle = {
  detail: RunDetail | null;
  samples: Sample[];
  rules: RuleEvent[];
  artifacts: Artifact[];
};

const emptyBundle: RunBundle = {
  detail: null,
  samples: [],
  rules: [],
  artifacts: [],
};

function statusClass(status?: string | null): string {
  const normalized = (status || "unknown").toLowerCase();
  if (["success", "pass"].includes(normalized)) return "status-success";
  if (["failed", "fail", "error"].includes(normalized)) return "status-failed";
  if (["running", "submitted", "queued"].includes(normalized)) return "status-running";
  if (["warn", "warning", "qc_warning"].includes(normalized)) return "status-warn";
  return "status-neutral";
}

function formatDate(value?: string | null): string {
  if (!value) return "not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.code ? `${error.code}: ${error.message}` : error.message;
  }
  if (error instanceof Error) return error.message;
  return "Request failed";
}

export default function App() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [bundle, setBundle] = useState<RunBundle>(emptyBundle);
  const [logStream, setLogStream] = useState<LogStream>("metadata");
  const [runLog, setRunLog] = useState<RunLog | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [logError, setLogError] = useState<string | null>(null);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const selectedRun = useMemo(
    () => runs.find((run) => run.analysis_id === selectedId) || null,
    [runs, selectedId],
  );

  async function refreshRuns(preferredId?: string | null) {
    setLoadingRuns(true);
    setListError(null);
    try {
      const payload = await listRuns();
      setRuns(payload.items);
      const nextId =
        preferredId && payload.items.some((run) => run.analysis_id === preferredId)
          ? preferredId
          : payload.items[0]?.analysis_id || null;
      setSelectedId(nextId);
    } catch (error) {
      setListError(errorMessage(error));
    } finally {
      setLoadingRuns(false);
    }
  }

  async function refreshDetail(analysisId: string) {
    setLoadingDetail(true);
    setDetailError(null);
    try {
      const [detail, samples, rules, artifacts] = await Promise.all([
        getRunDetail(analysisId),
        getRunSamples(analysisId),
        getRunRules(analysisId),
        getRunArtifacts(analysisId),
      ]);
      setBundle({
        detail,
        samples: samples.items,
        rules: rules.items,
        artifacts: artifacts.items,
      });
    } catch (error) {
      setBundle(emptyBundle);
      setDetailError(errorMessage(error));
    } finally {
      setLoadingDetail(false);
    }
  }

  async function refreshLog(analysisId: string, stream: LogStream) {
    setLogError(null);
    setRunLog(null);
    try {
      setRunLog(await getRunLog(analysisId, stream));
    } catch (error) {
      setLogError(errorMessage(error));
    }
  }

  async function handleSync() {
    if (!selectedId) return;
    setSyncing(true);
    setDetailError(null);
    try {
      await syncAirflow(selectedId);
      await Promise.all([refreshRuns(selectedId), refreshDetail(selectedId), refreshLog(selectedId, logStream)]);
    } catch (error) {
      setDetailError(errorMessage(error));
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => {
    void refreshRuns(null);
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setBundle(emptyBundle);
      setRunLog(null);
      return;
    }
    void refreshDetail(selectedId);
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    void refreshLog(selectedId, logStream);
  }, [selectedId, logStream]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">airflow-demo</p>
          <h1>PGT-A Runs</h1>
        </div>
        <div className="topbar-actions">
          <a className="secondary-link" href={`${window.location.protocol}//${window.location.hostname}:12958`}>
            Airflow 12958
          </a>
          <button className="icon-button" type="button" onClick={() => void refreshRuns(selectedId)} disabled={loadingRuns}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </header>

      <main className="workspace">
        <aside className="run-list" aria-label="PGT-A run list">
          <div className="pane-title">
            <Activity size={17} />
            <span>Runs</span>
            <span className="count">{runs.length}</span>
          </div>
          {listError ? <ErrorBanner message={listError} /> : null}
          {runs.length === 0 && !loadingRuns ? <p className="empty">No PGT-A runs returned.</p> : null}
          <div className="run-items">
            {runs.map((run) => (
              <button
                key={run.analysis_id}
                className={`run-row ${run.analysis_id === selectedId ? "selected" : ""}`}
                type="button"
                onClick={() => setSelectedId(run.analysis_id)}
              >
                <span className="run-id">{run.analysis_id}</span>
                <span className={`status-pill ${statusClass(run.status)}`}>{run.status}</span>
                <span className="run-meta">
                  {run.sample_count ?? 0} samples · {formatDate(run.created_at)}
                </span>
              </button>
            ))}
          </div>
        </aside>

        <section className="detail-pane" aria-label="Run detail">
          {selectedRun ? (
            <>
              <div className="detail-header">
                <div>
                  <p className="eyebrow">Selected Run</p>
                  <h2>{selectedRun.pipeline.toUpperCase()}</h2>
                  <p className="subtle">Analysis ID: {selectedRun.analysis_id}</p>
                </div>
                <div className="detail-status">
                  <span className={`status-pill large ${statusClass(bundle.detail?.status || selectedRun.status)}`}>
                    {bundle.detail?.status || selectedRun.status}
                  </span>
                </div>
              </div>

              <div className="toolbar" role="toolbar" aria-label="Run actions">
                <button className="icon-button" type="button" onClick={handleSync} disabled={syncing || !bundle.detail?.dag_run_id}>
                  <RotateCw size={16} />
                  Sync Airflow
                </button>
                <button
                  className="icon-button"
                  type="button"
                  onClick={() => selectedId && void refreshDetail(selectedId)}
                  disabled={loadingDetail}
                >
                  <RefreshCw size={16} />
                  Refresh Detail
                </button>
              </div>

              {detailError ? <ErrorBanner message={detailError} /> : null}
              {bundle.detail ? <Overview detail={bundle.detail} sampleCount={bundle.samples.length} /> : null}

              <div className="detail-grid">
                <SamplesTable samples={bundle.samples} />
                <RulesTable rules={bundle.rules} />
              </div>

              <div className="lower-grid">
                <LogPanel
                  stream={logStream}
                  onStreamChange={setLogStream}
                  log={runLog}
                  error={logError}
                />
                <ArtifactsList artifacts={bundle.artifacts} />
              </div>
            </>
          ) : (
            <div className="blank-state">
              <Database size={30} />
              <p>Select a run to inspect its samples, logs, artifacts, and rule status.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function ErrorBanner({message}: {message: string}) {
  return (
    <div className="error-banner" role="alert">
      <AlertTriangle size={16} />
      <span>{message}</span>
    </div>
  );
}

function Overview({detail, sampleCount}: {detail: RunDetail; sampleCount: number}) {
  const rows = [
    ["DAG", detail.dag_id || "not set"],
    ["DAG run", detail.dag_run_id || "not set"],
    ["Mode", detail.mode || "not set"],
    ["Samples", String(sampleCount)],
    ["Workdir", detail.workdir || "not set"],
    ["Manifest", detail.sample_sheet_path || "not set"],
    ["Started", formatDate(detail.started_at)],
    ["Ended", formatDate(detail.ended_at)],
  ];
  return (
    <section className="section-band">
      <div className="section-title">
        <FileText size={17} />
        <h3>Overview</h3>
      </div>
      <div className="kv-grid">
        {rows.map(([label, value]) => (
          <div className="kv-row" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      {detail.params ? (
        <pre className="params-block">{JSON.stringify(detail.params, null, 2)}</pre>
      ) : null}
      {detail.error_summary ? <ErrorBanner message={detail.error_summary} /> : null}
    </section>
  );
}

function SamplesTable({samples}: {samples: Sample[]}) {
  return (
    <section className="section-band">
      <div className="section-title">
        <Database size={17} />
        <h3>Samples</h3>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>sample</th>
              <th>status</th>
              <th>R1</th>
              <th>R2</th>
            </tr>
          </thead>
          <tbody>
            {samples.map((sample) => (
              <tr key={sample.sample_id}>
                <td>{sample.sample_id}</td>
                <td>
                  <span className={`status-pill ${statusClass(sample.status)}`}>{sample.status || "unknown"}</span>
                </td>
                <td className="path-cell">{sample.fq1 || "not set"}</td>
                <td className="path-cell">{sample.fq2 || "not set"}</td>
              </tr>
            ))}
            {samples.length === 0 ? (
              <tr>
                <td colSpan={4} className="empty-cell">
                  No samples returned.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function RulesTable({rules}: {rules: RuleEvent[]}) {
  return (
    <section className="section-band">
      <div className="section-title">
        <ListChecks size={17} />
        <h3>Snakemake Rules</h3>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>rule</th>
              <th>sample</th>
              <th>status</th>
              <th>jobid</th>
              <th>return</th>
              <th>message</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={`${rule.rule}-${rule.sample_id || "project"}-${rule.snakemake_jobid || "none"}`}>
                <td>{rule.rule}</td>
                <td>{rule.sample_id || "project"}</td>
                <td>
                  <span className={`status-pill ${statusClass(rule.status)}`}>{rule.status}</span>
                </td>
                <td>{rule.snakemake_jobid || "not set"}</td>
                <td>{rule.return_code ?? "not set"}</td>
                <td>{rule.message || "not set"}</td>
              </tr>
            ))}
            {rules.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty-cell">
                  No rule events returned.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LogPanel({
  stream,
  onStreamChange,
  log,
  error,
}: {
  stream: LogStream;
  onStreamChange: (stream: LogStream) => void;
  log: RunLog | null;
  error: string | null;
}) {
  const streams: LogStream[] = ["metadata", "stdout", "stderr"];
  return (
    <section className="section-band">
      <div className="section-title">
        <FileText size={17} />
        <h3>Logs</h3>
      </div>
      <div className="segmented" role="tablist" aria-label="Log stream">
        {streams.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={stream === item}
            className={stream === item ? "active" : ""}
            onClick={() => onStreamChange(item)}
          >
            {item}
          </button>
        ))}
      </div>
      {error ? <ErrorBanner message={error} /> : null}
      <div className="log-box" aria-label={`${stream} log`}>
        {log?.lines.length ? (
          log.lines.map((line, index) => (
            <div key={`${line}-${index}`} className="log-line">
              {line}
            </div>
          ))
        ) : (
          <span className="empty">No log lines returned.</span>
        )}
      </div>
      {log ? <p className="subtle">Path: {log.path}</p> : null}
    </section>
  );
}

function ArtifactsList({artifacts}: {artifacts: Artifact[]}) {
  return (
    <section className="section-band">
      <div className="section-title">
        <Archive size={17} />
        <h3>Artifacts</h3>
      </div>
      <div className="artifact-list">
        {artifacts.map((artifact) => (
          <div className="artifact-row" key={artifact.key}>
            <div>
              <strong>{artifact.label}</strong>
              <span>{artifact.type}</span>
            </div>
            <span>{formatBytes(artifact.size_bytes)}</span>
          </div>
        ))}
        {artifacts.length === 0 ? <p className="empty">No artifacts returned.</p> : null}
      </div>
    </section>
  );
}
