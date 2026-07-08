import {RefreshCw, RotateCw, Play} from "lucide-react";
import {useEffect, useState} from "react";
import {useParams} from "react-router-dom";

import type {AirflowTaskProgress, Artifact, LogStream, QcMetric, RuleEvent, RunDetail, RunLog, RunProgressResponse, RunQc, Sample} from "../api";

import {
  getRunArtifacts,
  getRunDetail,
  getRunLog,
  getRunProgress,
  getRunQc,
  getRunRules,
  getRunSamples,
  reanalyzeRun,
  submitRun,
  syncAirflow,
} from "../api";
import {ErrorPanel} from "../components/ErrorPanel";
import {LogViewer} from "../components/LogViewer";
import {MetricCard} from "../components/MetricCard";
import {RunProgressBar} from "../components/RunProgressBar";
import {StatusBadge} from "../components/StatusBadge";
import {parseErrorSummary} from "../lib/errors";
import {compactPipelineName, formatBytes, formatDate, formatDuration, safeJson} from "../lib/format";
import {errorMessage} from "../lib/errors";
import {computeRunProgress, progressFromResponse} from "../lib/runProgress";
import {sampleSourceDisplay} from "../lib/sampleFiles";
import {isActiveStatus, isFailedStatus, normalizeStatus} from "../lib/status";

const tabs = ["Overview", "Samples", "Workflow", "QC", "Logs", "Files", "Config"] as const;
type DetailTab = (typeof tabs)[number];
const qcPageSize = 20;
const qcMetricPriority = [
  "qc_decision",
  "mapped_fragments",
  "zero_bin_fraction",
  "bin_cv",
  "pearson_r",
  "median_abs_z",
  "gc_signal_slope",
  "nipt_mount_smoke",
  "read_count",
  "Q30",
  "unique_mapping_rate",
  "pcr_duplication_rate",
  "chrY_percent",
  "gender",
  "fetal_fraction",
];

type Bundle = {
  detail: RunDetail | null;
  samples: Sample[];
  rules: RuleEvent[];
  artifacts: Artifact[];
  qc: RunQc | null;
  progress: RunProgressResponse | null;
};

const emptyBundle: Bundle = {detail: null, samples: [], rules: [], artifacts: [], qc: null, progress: null};

export function RunDetailPage() {
  const {analysisId = ""} = useParams();
  const [bundle, setBundle] = useState<Bundle>(emptyBundle);
  const [log, setLog] = useState<RunLog | null>(null);
  const [logStream, setLogStream] = useState<LogStream>("metadata");
  const [activeTab, setActiveTab] = useState<DetailTab>("Overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logError, setLogError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [lastAutoSyncedAt, setLastAutoSyncedAt] = useState<string | null>(null);
  const [runActionOpen, setRunActionOpen] = useState(false);

  async function loadDetail() {
    if (!analysisId) return;
    setLoading(true);
    setError(null);
    try {
      const [detail, samples, rules, progress, artifacts, qc] = await Promise.all([
        getRunDetail(analysisId),
        getRunSamples(analysisId),
        getRunRules(analysisId),
        getRunProgress(analysisId).catch(() => null),
        getRunArtifacts(analysisId),
        getRunQc(analysisId),
      ]);
      setBundle({detail, samples: samples.items, rules: progress?.rule_events || rules.items, progress, artifacts: artifacts.items, qc});
      if (isFailedStatus(detail.status)) setLogStream("stderr");
    } catch (loadError) {
      setBundle(emptyBundle);
      setError(errorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }

  async function loadLog(stream: LogStream) {
    if (!analysisId) return;
    setLog(null);
    setLogError(null);
    try {
      setLog(await getRunLog(analysisId, stream));
    } catch (loadError) {
      setLogError(errorMessage(loadError));
    }
  }

  useEffect(() => {
    void loadDetail();
  }, [analysisId]);

  useEffect(() => {
    void loadLog(logStream);
  }, [analysisId, logStream]);

  const detail = bundle.detail;

  useEffect(() => {
    if (!analysisId || !detail || !detail.dag_run_id || !isActiveStatus(detail.status)) return;

    let stopped = false;
    const refreshFromAirflow = async () => {
      try {
        await syncAirflow(analysisId);
        if (stopped) return;
        setLastAutoSyncedAt(new Date().toISOString());
        await loadDetail();
      } catch (syncError) {
        if (!stopped) setActionError(errorMessage(syncError));
      }
    };

    void refreshFromAirflow();
    const interval = window.setInterval(() => void refreshFromAirflow(), 15000);
    return () => {
      stopped = true;
      window.clearInterval(interval);
    };
  }, [analysisId, detail?.dag_run_id, detail?.status]);

  const failedRule = bundle.rules.find((rule) => isFailedStatus(rule.status));
  const diagnosis = parseErrorSummary(detail?.error_summary, failedRule?.rule);
  const progress = detail && bundle.progress
    ? progressFromResponse(bundle.progress)
    : detail
      ? computeRunProgress(
          {
            analysis_id: detail.analysis_id,
            pipeline: detail.pipeline,
            status: detail.status,
            created_at: detail.created_at,
            started_at: detail.started_at,
            ended_at: detail.ended_at,
            sample_count: bundle.samples.length,
          },
          detail,
          bundle.rules,
        )
      : null;
  const canSubmit = detail?.status === "created" && ["pgta", "nipt_docker"].includes(detail.pipeline);
  const canResumePgta =
    detail?.pipeline === "pgta" &&
    detail.params?.target === "baseline_qc" &&
    Boolean(detail.dag_run_id) &&
    ["failed", "terminated"].includes(normalizeStatus(detail.status));
  const canOpenRunAction =
    detail?.pipeline === "pgta" &&
    detail.params?.target === "baseline_qc" &&
    Boolean(detail.dag_run_id) &&
    ["failed", "terminated", "success"].includes(normalizeStatus(detail.status));

  async function runAction(action: "sync" | "submit" | "resume" | "rerun_stage", stage?: "mapping" | "metadata" | "baseline_qc") {
    if (!analysisId) return;
    setActing(true);
    setActionError(null);
    try {
      if (action === "sync") await syncAirflow(analysisId);
      if (action === "submit") await submitRun(analysisId);
      if (action === "resume") {
        await reanalyzeRun(analysisId, {
          mode: "resume",
          reason: detail?.pipeline === "pgta" ? "frontend PGT-A baseline_qc 64-core resume" : "frontend resume",
        });
      }
      if (action === "rerun_stage") {
        await reanalyzeRun(analysisId, {
          mode: "rerun_stage",
          stage,
          reason: `frontend controlled PGT-A rerun from ${stage}`,
        });
      }
      await loadDetail();
      await loadLog(action === "sync" ? logStream : "stdout");
      if (action !== "sync") setLogStream("stdout");
      setRunActionOpen(false);
    } catch (actionFailure) {
      setActionError(errorMessage(actionFailure));
    } finally {
      setActing(false);
    }
  }

  if (loading && !detail) return <p className="muted">Loading run detail...</p>;

  return (
    <div className="page-stack">
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {detail ? (
        <>
          <section className="run-summary-header">
            <div>
              <p className="eyebrow">Run detail</p>
              <h1>{detail.analysis_id}</h1>
              <p>{compactPipelineName(detail.pipeline)} · {detail.dag_id || "no DAG"} · {detail.mode || "mode not set"}</p>
            </div>
            <div className="summary-actions">
              <StatusBadge status={detail.status} size="lg" />
              {detail.dag_run_id && isActiveStatus(detail.status) ? (
                <span className="muted">{lastAutoSyncedAt ? `Auto sync active · ${formatDate(lastAutoSyncedAt)}` : "Auto sync active"}</span>
              ) : null}
              {canSubmit ? (
                <button className="button primary" type="button" disabled={acting} onClick={() => void runAction("submit")}>
                  <Play size={15} />
                  Submit to Airflow
                </button>
              ) : null}
              <button className="button ghost" type="button" disabled={acting || !detail.dag_run_id} onClick={() => void runAction("sync")}>
                <RefreshCw size={15} />
                Sync Airflow
              </button>
              {canOpenRunAction ? (
                <button className="button ghost" type="button" disabled={acting} onClick={() => setRunActionOpen(true)}>
                  <RotateCw size={15} />
                  Run action
                </button>
              ) : null}
            </div>
          </section>
          {runActionOpen ? (
            <RunActionModal
              canResume={canResumePgta}
              disabled={acting || isActiveStatus(detail.status)}
              onClose={() => setRunActionOpen(false)}
              onResume={() => void runAction("resume")}
              onRerunStage={(stage) => void runAction("rerun_stage", stage)}
            />
          ) : null}

          {actionError ? <div className="inline-error" role="alert">{actionError}</div> : null}
          <section className="metric-grid" aria-label="Run summary metrics">
            <MetricCard title="Samples" value={bundle.samples.length} status={bundle.samples.length ? "success" : "unknown"} />
            <MetricCard title="Duration" value={formatDuration(detail.started_at, detail.ended_at)} status={detail.status} />
            <MetricCard title="QC fail" value={bundle.qc?.summary.fail ?? 0} status={(bundle.qc?.summary.fail ?? 0) > 0 ? "failed" : "success"} />
            <MetricCard title="Rule events" value={bundle.rules.length} status={failedRule ? "failed" : "success"} />
          </section>

          <ErrorPanel diagnosis={diagnosis} />

          <div className="split-grid">
            <section className="panel">
              <div className="section-heading">
                <h2>Current progress</h2>
                <p>{bundle.progress?.progress_source ? `Source: ${bundle.progress.progress_source}` : "Fallback progress estimate"}</p>
              </div>
              {progress ? (
                <div className="current-progress-hero">
                  <strong>{progress.currentStep}</strong>
                  <span>{Math.round(progress.percent)}% complete</span>
                  <small>
                    Elapsed {formatDuration(detail.started_at, detail.ended_at)}
                    {isActiveStatus(detail.status) ? " · ETA uses recent successful runs on the Dashboard" : ""}
                  </small>
                  <RunProgressBar analysisId={detail.analysis_id} progress={progress} />
                </div>
              ) : null}
            </section>
            <section className="panel">
              <div className="section-heading">
                <h2>QC summary</h2>
                <p>Workflow success and QC decision are shown separately.</p>
              </div>
              <div className="metric-grid compact">
                {(["pass", "warn", "fail", "unknown"] as const).map((status) => (
                  <MetricCard key={status} title={status} value={bundle.qc?.summary[status] ?? 0} status={status} />
                ))}
              </div>
            </section>
          </div>

          <section className="panel">
            <div className="tabs" role="tablist" aria-label="Run detail tabs">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  className={activeTab === tab ? "active" : ""}
                  role="tab"
                  type="button"
                  aria-selected={activeTab === tab}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>
            {activeTab === "Overview" ? <OverviewTab detail={detail} samples={bundle.samples} /> : null}
            {activeTab === "Samples" ? <SamplesTab samples={bundle.samples} /> : null}
            {activeTab === "Workflow" ? <WorkflowTab progress={bundle.progress} rules={bundle.rules} /> : null}
            {activeTab === "QC" ? <QcTab qc={bundle.qc} /> : null}
            {activeTab === "Logs" ? <LogViewer stream={logStream} onStreamChange={setLogStream} log={log} error={logError} /> : null}
            {activeTab === "Files" ? <FilesTab artifacts={bundle.artifacts} /> : null}
            {activeTab === "Config" ? <ConfigTab artifacts={bundle.artifacts} detail={detail} /> : null}
          </section>

        </>
      ) : null}
    </div>
  );
}

function RunActionModal({
  canResume,
  disabled,
  onClose,
  onResume,
  onRerunStage,
}: {
  canResume: boolean;
  disabled: boolean;
  onClose: () => void;
  onResume: () => void;
  onRerunStage: (stage: "mapping" | "metadata" | "baseline_qc") => void;
}) {
  return (
    <div className="modal-backdrop">
      <section aria-modal="true" className="modal-panel run-action-modal" role="dialog" aria-label="Run action">
        <div className="section-heading split">
          <div>
            <h2>Run action</h2>
            <p>Controlled PGT-A baseline_qc actions only. This does not expose arbitrary Airflow DAG/task triggers.</p>
          </div>
          <button className="button ghost" type="button" onClick={onClose}>Close</button>
        </div>
        <div className="run-action-list">
          <button disabled={disabled || !canResume} type="button" onClick={onResume}>
            <strong>Resume failed baseline_qc</strong>
            <span>Reuse the same workdir and resume incomplete outputs.</span>
          </button>
          <button disabled={disabled} type="button" onClick={() => onRerunStage("mapping")}>
            <strong>Rerun mapping stage</strong>
            <span>Start from mapping, then continue metadata and baseline QC.</span>
          </button>
          <button disabled={disabled} type="button" onClick={() => onRerunStage("metadata")}>
            <strong>Rerun metadata stage</strong>
            <span>Skip mapping and continue metadata plus baseline QC.</span>
          </button>
          <button disabled={disabled} type="button" onClick={() => onRerunStage("baseline_qc")}>
            <strong>Rerun baseline QC stage</strong>
            <span>Recompute baseline QC only from existing mapping and metadata outputs.</span>
          </button>
        </div>
      </section>
    </div>
  );
}

function OverviewTab({detail, samples}: {detail: RunDetail; samples: Sample[]}) {
  return (
    <div className="overview-stack">
      <div className="definition-grid">
        <div><dt>Pipeline</dt><dd>{compactPipelineName(detail.pipeline)}</dd></div>
        <div><dt>Status</dt><dd><StatusBadge status={detail.status} /></dd></div>
        <div><dt>DAG run</dt><dd className="path-text">{detail.dag_run_id || "not set"}</dd></div>
        <div><dt>Samples</dt><dd>{samples.length}</dd></div>
        <div><dt>Created</dt><dd>{formatDate(detail.created_at)}</dd></div>
        <div><dt>Started</dt><dd>{formatDate(detail.started_at)}</dd></div>
        <div><dt>Finished</dt><dd>{formatDate(detail.ended_at)}</dd></div>
        <div><dt>Workdir</dt><dd className="path-text">{detail.workdir || "not set"}</dd></div>
      </div>
      <section>
        <div className="section-heading">
          <h2>Selected samples manifest</h2>
          <p>Manifest content rendered as sample rows instead of a raw server path.</p>
        </div>
        <SamplesManifestTable samples={samples} />
      </section>
    </div>
  );
}

function SamplesManifestTable({samples}: {samples: Sample[]}) {
  return (
    <div className="table-wrap">
      <table className="data-table compact manifest-table">
        <thead>
          <tr><th>sample_id</th><th>source folder</th><th>R1</th><th>R2</th><th>status</th><th>QC</th></tr>
        </thead>
        <tbody>
          {samples.map((sample) => {
            const display = sampleSourceDisplay(sample);
            return (
              <tr key={sample.sample_id}>
                <td>{sample.sample_id}</td>
                <td>{display.primary}</td>
                <td>{basename(sample.fq1)}</td>
                <td>{basename(sample.fq2)}</td>
                <td><StatusBadge status={sample.status} size="sm" /></td>
                <td><StatusBadge status={sample.qc_status || "unknown"} size="sm" /></td>
              </tr>
            );
          })}
          {samples.length === 0 ? <tr><td className="empty-cell" colSpan={6}>No selected samples returned.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}

function SamplesTab({samples}: {samples: Sample[]}) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr><th>sample_id</th><th>family_id</th><th>status</th><th>qc_status</th><th>source files</th></tr>
        </thead>
        <tbody>
          {samples.map((sample) => (
            <tr key={sample.sample_id}>
              <td>{sample.sample_id}</td>
              <td>{sample.family_id || "not set"}</td>
              <td><StatusBadge status={sample.status} /></td>
              <td><StatusBadge status={sample.qc_status || "unknown"} size="sm" /></td>
              <td><SourceFilesCell sample={sample} /></td>
            </tr>
          ))}
          {samples.length === 0 ? <tr><td className="empty-cell" colSpan={5}>No samples returned.</td></tr> : null}
        </tbody>
      </table>
    </div>
  );
}

function WorkflowTab({progress, rules}: {progress: RunProgressResponse | null; rules: RuleEvent[]}) {
  const airflowTasks = progress?.airflow_tasks || [];
  return (
    <div className="workflow-tab-stack">
      <section>
        <div className="section-heading">
          <h2>Airflow tasks</h2>
          <p>Project-level DAG task instances from the Airflow REST API.</p>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>task</th><th>state</th><th>operator</th><th>try</th><th>started</th><th>ended</th><th>duration</th></tr>
            </thead>
            <tbody>
              {airflowTasks.map((task: AirflowTaskProgress) => (
                <tr key={`${task.task_id}-${task.try_number || "try"}`}>
                  <td>{task.task_id}</td>
                  <td><StatusBadge status={task.state} /></td>
                  <td>{task.operator || "not set"}</td>
                  <td>{task.try_number ?? "not set"}</td>
                  <td>{formatDate(task.start_date)}</td>
                  <td>{formatDate(task.end_date)}</td>
                  <td>{task.duration ?? "not set"}</td>
                </tr>
              ))}
              {airflowTasks.length === 0 ? <tr><td className="empty-cell" colSpan={7}>No Airflow task instances returned yet.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
      <section>
        <div className="section-heading">
          <h2>Pipeline steps</h2>
          <p>Snakemake or runner-level events captured from JSONL/backend event posts.</p>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>rule</th><th>sample</th><th>status</th><th>snakemake jobid</th><th>qsub jobid</th><th>return</th><th>message</th></tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={`${rule.rule}-${rule.sample_id || "project"}-${rule.snakemake_jobid || "none"}`}>
                  <td>{rule.rule}</td>
                  <td>{rule.sample_id || "project"}</td>
                  <td><StatusBadge status={rule.status} /></td>
                  <td>{rule.snakemake_jobid || "not set"}</td>
                  <td>{rule.qsub_jobid || "not set"}</td>
                  <td>{rule.return_code ?? "not set"}</td>
                  <td>{rule.message || "not set"}</td>
                </tr>
              ))}
              {rules.length === 0 ? <tr><td className="empty-cell" colSpan={7}>No rule events captured. Airflow task progress is still available above.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function QcTab({qc}: {qc: RunQc | null}) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(0);
  const metrics = qc?.items || [];
  const matrix = buildQcMatrix(metrics);
  const filteredRows = matrix.rows.filter((row) => {
    const matchesQuery = !query.trim() || row.sampleId.toLowerCase().includes(query.trim().toLowerCase());
    const matchesStatus = statusFilter === "all" || qcFilterBucket(row.status) === statusFilter;
    return matchesQuery && matchesStatus;
  });
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / qcPageSize));
  const safePage = Math.min(page, pageCount - 1);
  const visibleRows = filteredRows.slice(safePage * qcPageSize, safePage * qcPageSize + qcPageSize);
  const failureRows = qcFailureRows(metrics);

  return (
    <div className="qc-tab-stack">
      <div className="metric-grid compact qc-summary-grid">
        {(["pass", "warn", "fail", "unknown"] as const).map((status) => (
          <MetricCard key={status} title={status} value={qc?.summary[status] ?? 0} status={status} />
        ))}
      </div>
      <section className="qc-failure-summary">
        <div className="section-heading">
          <h2>QC failures</h2>
          <p>Fail/warn metrics sorted before the full matrix so problematic samples are visible without scanning 96 cards.</p>
        </div>
        {failureRows.length ? (
          <div className="table-wrap">
            <table className="data-table compact">
              <thead>
                <tr><th>sample</th><th>metric</th><th>value</th><th>threshold</th><th>reason</th></tr>
              </thead>
              <tbody>
                {failureRows.slice(0, 12).map((row) => (
                  <tr key={`${row.sampleId}-${row.metric}-${row.value}`}>
                    <td>{row.sampleId}</td>
                    <td>{row.metric}</td>
                    <td>{row.value}</td>
                    <td>{row.threshold}</td>
                    <td>{row.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty-state">No failed or warning QC metrics returned.</p>
        )}
      </section>
      {metrics.length > 0 ? (
        <>
          <div className="qc-toolbar">
            <label>
              <span>Sample search</span>
              <input
                type="search"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(0);
                }}
                placeholder="sample_id"
              />
            </label>
            <div className="segmented-control" aria-label="QC status filter">
              {["all", "fail", "warn", "pass", "unknown"].map((status) => (
                <button
                  key={status}
                  className={statusFilter === status ? "active" : ""}
                  type="button"
                  onClick={() => {
                    setStatusFilter(status);
                    setPage(0);
                  }}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>
          <div className="table-wrap qc-matrix-wrap">
            <table className="data-table compact qc-matrix-table">
              <thead>
                <tr>
                  <th>sample_id</th>
                  <th>qc_status</th>
                  {matrix.columns.map((column) => <th key={column}>{column}</th>)}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => (
                  <tr key={row.sampleId}>
                    <td className="qc-sample-cell">{row.sampleId}</td>
                    <td><StatusBadge status={row.status} size="sm" /></td>
                    {matrix.columns.map((column) => {
                      const metric = row.metrics[column];
                      return (
                        <td key={`${row.sampleId}-${column}`} className={metric ? `qc-status-${normalizeStatus(metric.status)}` : ""}>
                          {metric ? metricValue(metric) : "-"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
                {visibleRows.length === 0 ? <tr><td className="empty-cell" colSpan={matrix.columns.length + 2}>No QC samples match the current filter.</td></tr> : null}
              </tbody>
            </table>
          </div>
          <div className="pagination-row">
            <span>{filteredRows.length} sample rows · page {safePage + 1} / {pageCount}</span>
            <div>
              <button className="button ghost" type="button" disabled={safePage === 0} onClick={() => setPage((current) => Math.max(0, current - 1))}>Previous</button>
              <button className="button ghost" type="button" disabled={safePage >= pageCount - 1} onClick={() => setPage((current) => Math.min(pageCount - 1, current + 1))}>Next</button>
            </div>
          </div>
        </>
      ) : <p className="empty-state">No QC metrics returned.</p>}
    </div>
  );
}

function qcFailureRows(metrics: QcMetric[]): Array<{sampleId: string; metric: string; value: string; threshold: string; reason: string}> {
  return metrics
    .filter((metric) => ["failed", "fail", "error", "warning", "warn", "qc_warning"].includes(normalizeStatus(metric.status)))
    .map((metric) => ({
      sampleId: metric.sample_id || "project",
      metric: metric.metric_name,
      value: metricValue(metric),
      threshold: metric.threshold || "not set",
      reason: qcFailureReason(metric),
    }));
}

function qcFailureReason(metric: QcMetric): string {
  if (metric.metric_name === "qc_decision") return `QC decision is ${metric.metric_value || metric.status}`;
  if (metric.threshold) return `Outside threshold ${metric.threshold}`;
  return `Metric status is ${metric.status}`;
}

function SourceFilesCell({sample}: {sample: Sample}) {
  const display = sampleSourceDisplay(sample);
  return (
    <div className={display.missing ? "source-files missing" : "source-files"}>
      <span>{display.primary}</span>
      {display.secondary ? <small>{display.secondary}</small> : null}
    </div>
  );
}

type QcMatrixRow = {
  sampleId: string;
  status: string;
  metrics: Record<string, QcMetric>;
};

function buildQcMatrix(metrics: QcMetric[]): {columns: string[]; rows: QcMatrixRow[]} {
  const columns = Array.from(new Set(metrics.map((metric) => metric.metric_name))).sort((left, right) => {
    const leftPriority = qcMetricPriority.indexOf(left);
    const rightPriority = qcMetricPriority.indexOf(right);
    if (leftPriority >= 0 || rightPriority >= 0) {
      return (leftPriority >= 0 ? leftPriority : 999) - (rightPriority >= 0 ? rightPriority : 999);
    }
    return left.localeCompare(right);
  });
  const rowsBySample = new Map<string, QcMatrixRow>();
  for (const metric of metrics) {
    const sampleId = metric.sample_id || "project";
    const row = rowsBySample.get(sampleId) || {sampleId, status: "pass", metrics: {}};
    row.metrics[metric.metric_name] = metric;
    row.status = worstQcStatus(row.status, metric.status);
    rowsBySample.set(sampleId, row);
  }
  const rows = Array.from(rowsBySample.values()).sort((left, right) => {
    const rankDiff = qcStatusRank(left.status) - qcStatusRank(right.status);
    return rankDiff || left.sampleId.localeCompare(right.sampleId);
  });
  return {columns, rows};
}

function worstQcStatus(current: string, incoming: string): string {
  return qcStatusRank(incoming) < qcStatusRank(current) ? normalizeStatus(incoming) : normalizeStatus(current);
}

function qcStatusRank(status: string): number {
  const normalized = normalizeStatus(status);
  if (["failed", "fail", "error"].includes(normalized)) return 0;
  if (["warning", "warn", "qc_warning"].includes(normalized)) return 1;
  if (normalized === "unknown") return 2;
  if (["success", "pass"].includes(normalized)) return 3;
  return 4;
}

function metricValue(metric: QcMetric): string {
  if (metric.metric_value !== null && metric.metric_value !== undefined && metric.metric_value !== "") return String(metric.metric_value);
  if (metric.metric_numeric !== null && metric.metric_numeric !== undefined) return String(metric.metric_numeric);
  return "-";
}

function qcFilterBucket(status: string): string {
  const normalized = normalizeStatus(status);
  if (["failed", "fail", "error"].includes(normalized)) return "fail";
  if (["warning", "warn", "qc_warning"].includes(normalized)) return "warn";
  if (["success", "pass"].includes(normalized)) return "pass";
  return "unknown";
}

function FilesTab({artifacts}: {artifacts: Artifact[]}) {
  const primary = artifacts.filter(isPrimaryArtifact);
  const advanced = artifacts.filter((artifact) => !isPrimaryArtifact(artifact));
  return (
    <div className="artifact-list">
      {(primary.length ? primary : artifacts).map((artifact) => (
        <article className="artifact-row" key={artifact.key}>
          <div>
            <strong>{artifact.label}</strong>
            <span>{artifact.type}</span>
            <span className="path-text">{artifact.path}</span>
          </div>
          <span>{formatBytes(artifact.size_bytes)}</span>
        </article>
      ))}
      {advanced.length ? (
        <details className="advanced-files">
          <summary>Advanced files</summary>
          {advanced.map((artifact) => (
            <article className="artifact-row" key={artifact.key}>
              <div>
                <strong>{artifact.label}</strong>
                <span>{artifact.type}</span>
                <span className="path-text">{artifact.path}</span>
              </div>
              <span>{formatBytes(artifact.size_bytes)}</span>
            </article>
          ))}
        </details>
      ) : null}
      {artifacts.length === 0 ? <p className="empty-state">No files or artifacts returned.</p> : null}
    </div>
  );
}

function ConfigTab({detail, artifacts}: {detail: RunDetail; artifacts: Artifact[]}) {
  const configArtifacts = artifacts.filter(isConfigArtifact);
  return (
    <div className="config-tab-stack">
      <section>
        <div className="section-heading">
          <h2>Snakemake run config</h2>
          <p>Config artifacts first. Raw params remain below as an advanced backend payload.</p>
        </div>
        {configArtifacts.length ? (
          <div className="artifact-list">
            {configArtifacts.map((artifact) => (
              <article className="artifact-row" key={artifact.key}>
                <div>
                  <strong>{artifact.label}</strong>
                  <span>{artifact.type}</span>
                  <span className="path-text">{artifact.path}</span>
                </div>
                <span>{formatBytes(artifact.size_bytes)}</span>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">No run-local config artifact has been registered yet.</p>
        )}
      </section>
      <details className="advanced-files">
        <summary>Backend request params</summary>
        <pre className="code-block">{safeJson({
          analysis_id: detail.analysis_id,
          pipeline: detail.pipeline,
          dag_id: detail.dag_id,
          dag_run_id: detail.dag_run_id,
          params: detail.params,
        })}</pre>
      </details>
    </div>
  );
}

function isPrimaryArtifact(artifact: Artifact): boolean {
  const text = `${artifact.key} ${artifact.type} ${artifact.label} ${artifact.path}`.toLowerCase();
  return text.includes("log") || text.includes("report") || text.includes("qc") || text.includes("summary");
}

function isConfigArtifact(artifact: Artifact): boolean {
  const text = `${artifact.key} ${artifact.type} ${artifact.label} ${artifact.path}`.toLowerCase();
  return text.includes("config") || text.endsWith(".yaml") || text.endsWith(".yml") || text.endsWith(".json");
}

function basename(value?: string | null): string {
  if (!value) return "Path not captured for this run";
  return value.split(/[\\/]/).filter(Boolean).pop() || value;
}
