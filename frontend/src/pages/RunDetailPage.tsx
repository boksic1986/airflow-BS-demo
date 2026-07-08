import {RefreshCw, RotateCw, Play} from "lucide-react";
import {useEffect, useState} from "react";
import {useParams} from "react-router-dom";

import type {AirflowTaskProgress, Artifact, LogStream, RuleEvent, RunDetail, RunLog, RunProgressResponse, RunQc, Sample} from "../api";

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
import {QcMetricCard} from "../components/QcMetricCard";
import {RunProgressBar} from "../components/RunProgressBar";
import {StatusBadge} from "../components/StatusBadge";
import {parseErrorSummary} from "../lib/errors";
import {compactPipelineName, formatBytes, formatDate, formatDuration, safeJson} from "../lib/format";
import {errorMessage} from "../lib/errors";
import {computeRunProgress, progressFromResponse} from "../lib/runProgress";
import {isActiveStatus, isFailedStatus, normalizeStatus} from "../lib/status";

const tabs = ["Overview", "Samples", "Workflow", "QC", "Logs", "Files", "Config"] as const;
type DetailTab = (typeof tabs)[number];

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

  async function runAction(action: "sync" | "submit" | "resume") {
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
      await loadDetail();
      await loadLog(action === "sync" ? logStream : "stdout");
      if (action !== "sync") setLogStream("stdout");
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
              {canResumePgta ? (
                <button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("resume")}>
                  <RotateCw size={15} />
                  Resume with 64 cores
                </button>
              ) : null}
            </div>
          </section>

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
              {progress ? <RunProgressBar analysisId={detail.analysis_id} progress={progress} /> : null}
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
            {activeTab === "Overview" ? <OverviewTab detail={detail} sampleCount={bundle.samples.length} /> : null}
            {activeTab === "Samples" ? <SamplesTab samples={bundle.samples} /> : null}
            {activeTab === "Workflow" ? <WorkflowTab progress={bundle.progress} rules={bundle.rules} /> : null}
            {activeTab === "QC" ? <QcTab qc={bundle.qc} /> : null}
            {activeTab === "Logs" ? <LogViewer stream={logStream} onStreamChange={setLogStream} log={log} error={logError} /> : null}
            {activeTab === "Files" ? <FilesTab artifacts={bundle.artifacts} /> : null}
            {activeTab === "Config" ? <ConfigTab detail={detail} /> : null}
          </section>

        </>
      ) : null}
    </div>
  );
}

function OverviewTab({detail, sampleCount}: {detail: RunDetail; sampleCount: number}) {
  return (
    <div className="definition-grid">
      <div><dt>Pipeline</dt><dd>{compactPipelineName(detail.pipeline)}</dd></div>
      <div><dt>Status</dt><dd><StatusBadge status={detail.status} /></dd></div>
      <div><dt>DAG run</dt><dd className="path-text">{detail.dag_run_id || "not set"}</dd></div>
      <div><dt>Samples</dt><dd>{sampleCount}</dd></div>
      <div><dt>Created</dt><dd>{formatDate(detail.created_at)}</dd></div>
      <div><dt>Started</dt><dd>{formatDate(detail.started_at)}</dd></div>
      <div><dt>Finished</dt><dd>{formatDate(detail.ended_at)}</dd></div>
      <div><dt>Workdir</dt><dd className="path-text">{detail.workdir || "not set"}</dd></div>
      <div><dt>Manifest</dt><dd className="path-text">{detail.sample_sheet_path || "not set"}</dd></div>
    </div>
  );
}

function SamplesTab({samples}: {samples: Sample[]}) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr><th>sample_id</th><th>family_id</th><th>status</th><th>qc_status</th><th>fastq_path</th></tr>
        </thead>
        <tbody>
          {samples.map((sample) => (
            <tr key={sample.sample_id}>
              <td>{sample.sample_id}</td>
              <td>{sample.family_id || "not set"}</td>
              <td><StatusBadge status={sample.status} /></td>
              <td><StatusBadge status={sample.qc_status || "unknown"} size="sm" /></td>
              <td className="path-text">{sample.fq1 || sample.fq2 || "not set"}</td>
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
  const metrics = qc?.items || [];
  return (
    <div className="card-grid">
      {metrics.map((metric) => <QcMetricCard key={`${metric.sample_id || "project"}-${metric.metric_name}`} metric={metric} />)}
      {metrics.length === 0 ? <p className="empty-state">No QC metrics returned.</p> : null}
    </div>
  );
}

function FilesTab({artifacts}: {artifacts: Artifact[]}) {
  return (
    <div className="artifact-list">
      {artifacts.map((artifact) => (
        <article className="artifact-row" key={artifact.key}>
          <div>
            <strong>{artifact.label}</strong>
            <span>{artifact.type}</span>
            <span className="path-text">{artifact.path}</span>
          </div>
          <span>{formatBytes(artifact.size_bytes)}</span>
        </article>
      ))}
      {artifacts.length === 0 ? <p className="empty-state">No files or artifacts returned.</p> : null}
    </div>
  );
}

function ConfigTab({detail}: {detail: RunDetail}) {
  return (
    <pre className="code-block">{safeJson({
      analysis_id: detail.analysis_id,
      pipeline: detail.pipeline,
      dag_id: detail.dag_id,
      dag_run_id: detail.dag_run_id,
      params: detail.params,
      workdir: detail.workdir,
    })}</pre>
  );
}
