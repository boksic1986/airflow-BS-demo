import {RefreshCw, RotateCw, Play} from "lucide-react";
import {useEffect, useMemo, useState} from "react";
import {useParams} from "react-router-dom";

import type {Artifact, LogStream, RuleEvent, RunDetail, RunLog, RunQc, Sample} from "../api";

import {
  getRunArtifacts,
  getRunDetail,
  getRunLog,
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
import {StatusBadge} from "../components/StatusBadge";
import {WorkflowTimeline} from "../components/WorkflowTimeline";
import {parseErrorSummary} from "../lib/errors";
import {compactPipelineName, formatBytes, formatDate, formatDuration, safeJson} from "../lib/format";
import {errorMessage} from "../lib/errors";
import {isFailedStatus, normalizeStatus} from "../lib/status";

const tabs = ["Overview", "Samples", "Workflow", "QC", "Logs", "Files", "Config"] as const;
type DetailTab = (typeof tabs)[number];

type Bundle = {
  detail: RunDetail | null;
  samples: Sample[];
  rules: RuleEvent[];
  artifacts: Artifact[];
  qc: RunQc | null;
};

const emptyBundle: Bundle = {detail: null, samples: [], rules: [], artifacts: [], qc: null};

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

  async function loadDetail() {
    if (!analysisId) return;
    setLoading(true);
    setError(null);
    try {
      const [detail, samples, rules, artifacts, qc] = await Promise.all([
        getRunDetail(analysisId),
        getRunSamples(analysisId),
        getRunRules(analysisId),
        getRunArtifacts(analysisId),
        getRunQc(analysisId),
      ]);
      setBundle({detail, samples: samples.items, rules: rules.items, artifacts: artifacts.items, qc});
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
  const failedRule = bundle.rules.find((rule) => isFailedStatus(rule.status));
  const diagnosis = parseErrorSummary(detail?.error_summary, failedRule?.rule);
  const workflowSteps = useMemo(() => {
    const airflow = detail
      ? [
          {name: detail.dag_id || "Airflow DAG", status: detail.status, description: detail.dag_run_id || "No DAG run id"},
        ]
      : [];
    return [
      ...airflow,
      ...bundle.rules.slice(0, 10).map((rule) => ({
        name: rule.rule,
        status: rule.status,
        sample: rule.sample_id,
        description: rule.qsub_jobid ? `qsub ${rule.qsub_jobid}` : rule.message || `job ${rule.snakemake_jobid || "not set"}`,
      })),
    ];
  }, [bundle.rules, detail]);

  const canSubmit = detail?.status === "created" && detail.pipeline === "pgta";
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
              {canSubmit ? (
                <button className="button primary" type="button" disabled={acting} onClick={() => void runAction("submit")}>
                  <Play size={15} />
                  Submit to Airflow
                </button>
              ) : null}
              {detail.pipeline === "pgta" ? (
                <button className="button ghost" type="button" disabled={acting || !detail.dag_run_id} onClick={() => void runAction("sync")}>
                  <RefreshCw size={15} />
                  Sync Airflow
                </button>
              ) : null}
              {canResumePgta ? (
                <button className="button ghost" type="button" disabled={acting} onClick={() => void runAction("resume")}>
                  <RotateCw size={15} />
                  Resume with 64 cores
                </button>
              ) : null}
            </div>
          </section>

          {detail.pipeline !== "pgta" ? (
            <section className="panel">
              <div className="section-heading">
                <h2>Current deployment scope</h2>
                <p>This frontend deployment only exposes PGT-A. Historical non-PGT-A runs remain in backend storage but are hidden from the demo workflow.</p>
              </div>
            </section>
          ) : null}

          {detail.pipeline === "pgta" && actionError ? <div className="inline-error" role="alert">{actionError}</div> : null}

          {detail.pipeline === "pgta" ? (
          <>
          <section className="metric-grid" aria-label="Run summary metrics">
            <MetricCard title="Samples" value={bundle.samples.length} status={bundle.samples.length ? "success" : "unknown"} />
            <MetricCard title="Duration" value={formatDuration(detail.started_at, detail.ended_at)} status={detail.status} />
            <MetricCard title="QC fail" value={bundle.qc?.summary.fail ?? 0} status={(bundle.qc?.summary.fail ?? 0) > 0 ? "failed" : "success"} />
            <MetricCard title="Rule events" value={bundle.rules.length} status={failedRule ? "failed" : "success"} />
          </section>

          <ErrorPanel diagnosis={diagnosis} />

          <div className="split-grid">
            <WorkflowTimeline steps={workflowSteps} title="Workflow overview" />
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
            {activeTab === "Workflow" ? <WorkflowTab rules={bundle.rules} /> : null}
            {activeTab === "QC" ? <QcTab qc={bundle.qc} /> : null}
            {activeTab === "Logs" ? <LogViewer stream={logStream} onStreamChange={setLogStream} log={log} error={logError} /> : null}
            {activeTab === "Files" ? <FilesTab artifacts={bundle.artifacts} /> : null}
            {activeTab === "Config" ? <ConfigTab detail={detail} /> : null}
          </section>

          </>
          ) : null}
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

function WorkflowTab({rules}: {rules: RuleEvent[]}) {
  return (
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
          {rules.length === 0 ? <tr><td className="empty-cell" colSpan={7}>No rule events returned.</td></tr> : null}
        </tbody>
      </table>
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
