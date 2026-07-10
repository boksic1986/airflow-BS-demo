import {Play, RefreshCw, RotateCw} from "lucide-react";
import {useEffect, useState} from "react";
import {useParams} from "react-router-dom";

import type {Artifact, LogStream, RuleEvent, RunDetail, RunLog, RunProgressResponse, RunQc, Sample} from "../api";

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
import {StatusBadge} from "../components/StatusBadge";
import {CurrentProgressPanel} from "../features/run-detail/CurrentProgressPanel";
import {RunActionModal} from "../features/run-detail/RunActionModal";
import {RunQcTab} from "../features/run-detail/RunQcTab";
import {RunConfigTab, RunFilesTab, RunOverviewTab, RunSamplesTab} from "../features/run-detail/RunResourceTabs";
import {RunWorkflowTab} from "../features/run-detail/RunWorkflowTab";
import {errorMessage, parseErrorSummary} from "../lib/errors";
import {compactPipelineName, formatDate, formatDuration} from "../lib/format";
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

  useEffect(() => { void loadDetail(); }, [analysisId]);
  useEffect(() => { void loadLog(logStream); }, [analysisId, logStream]);

  const detail = bundle.detail;

  useEffect(() => {
    if (!analysisId || !detail?.dag_run_id || !isActiveStatus(detail.status)) return;
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
    return () => { stopped = true; window.clearInterval(interval); };
  }, [analysisId, detail?.dag_run_id, detail?.status]);

  const failedRule = bundle.rules.find((rule) => isFailedStatus(rule.status));
  const diagnosis = parseErrorSummary(detail?.error_summary, failedRule?.rule);
  const progress = detail && bundle.progress
    ? progressFromResponse(bundle.progress)
    : detail
      ? computeRunProgress({analysis_id: detail.analysis_id, pipeline: detail.pipeline, status: detail.status, created_at: detail.created_at, started_at: detail.started_at, ended_at: detail.ended_at, sample_count: bundle.samples.length}, detail, bundle.rules)
      : null;
  const canSubmit = detail?.status === "created" && ["pgta", "nipt_docker"].includes(detail.pipeline);
  const canResumePgta = detail?.pipeline === "pgta" && detail.params?.target === "baseline_qc" && Boolean(detail.dag_run_id) && ["failed", "terminated"].includes(normalizeStatus(detail.status));
  const canOpenRunAction = detail?.pipeline === "pgta" && detail.params?.target === "baseline_qc" && Boolean(detail.dag_run_id) && ["failed", "terminated", "success"].includes(normalizeStatus(detail.status));

  async function runAction(action: "sync" | "submit" | "resume" | "rerun_stage", stage?: "mapping" | "metadata" | "baseline_qc") {
    if (!analysisId) return;
    setActing(true);
    setActionError(null);
    try {
      if (action === "sync") await syncAirflow(analysisId);
      if (action === "submit") await submitRun(analysisId);
      if (action === "resume") await reanalyzeRun(analysisId, {mode: "resume", reason: "frontend PGT-A baseline_qc resume"});
      if (action === "rerun_stage") await reanalyzeRun(analysisId, {mode: "rerun_stage", stage, reason: `frontend controlled PGT-A rerun from ${stage}`});
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
    <div className="page-stack run-detail-page">
      {error ? <div className="inline-error" role="alert">{error}</div> : null}
      {detail ? <>
        <section className="run-summary-header">
          <div><p className="eyebrow">Run detail</p><h1>{detail.analysis_id}</h1><p>{compactPipelineName(detail.pipeline)} / {detail.dag_id || "no DAG"} / {detail.mode || "mode not set"}</p></div>
          <div className="summary-actions">
            <StatusBadge status={detail.status} size="lg" />
            {detail.dag_run_id && isActiveStatus(detail.status) ? <span className="muted">{lastAutoSyncedAt ? `Auto sync / ${formatDate(lastAutoSyncedAt)}` : "Auto sync active"}</span> : null}
            {canSubmit ? <button className="button primary" type="button" disabled={acting} onClick={() => void runAction("submit")}><Play size={15} />Submit to Airflow</button> : null}
            <button className="button ghost" type="button" disabled={acting || !detail.dag_run_id} onClick={() => void runAction("sync")}><RefreshCw size={15} />Sync Airflow</button>
            {canOpenRunAction ? <button className="button ghost" type="button" disabled={acting} onClick={() => setRunActionOpen(true)}><RotateCw size={15} />Run action</button> : null}
          </div>
        </section>
        {runActionOpen ? <RunActionModal canResume={canResumePgta} disabled={acting || isActiveStatus(detail.status)} onClose={() => setRunActionOpen(false)} onResume={() => void runAction("resume")} onRerunStage={(stage) => void runAction("rerun_stage", stage)} /> : null}
        {actionError ? <div className="inline-error" role="alert">{actionError}</div> : null}
        <section className="metric-grid" aria-label="Run summary metrics">
          <MetricCard title="Samples" value={bundle.samples.length} />
          <MetricCard title="Duration" value={formatDuration(detail.started_at, detail.ended_at)} status={detail.status} />
          <MetricCard title="QC fail" value={bundle.qc?.summary.fail ?? 0} status={(bundle.qc?.summary.fail ?? 0) > 0 ? "failed" : "success"} />
          <MetricCard title="Rule events" value={bundle.rules.length} status={failedRule ? "failed" : undefined} />
        </section>
        <ErrorPanel diagnosis={diagnosis} />
        <div className="split-grid">
          <CurrentProgressPanel detail={detail} progress={progress} source={bundle.progress?.progress_source} />
          <section className="panel"><div className="section-heading"><h2>QC summary</h2><p>Workflow and sample QC are separate.</p></div><div className="metric-grid compact">{(["pass", "warn", "fail", "unknown"] as const).map((status) => <MetricCard key={status} title={status} value={bundle.qc?.summary[status] ?? 0} status={status} />)}</div></section>
        </div>
        <section className="panel">
          <div className="tabs" role="tablist" aria-label="Run detail tabs">{tabs.map((tab) => <button key={tab} className={activeTab === tab ? "active" : ""} role="tab" type="button" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div>
          {activeTab === "Overview" ? <RunOverviewTab detail={detail} samples={bundle.samples} /> : null}
          {activeTab === "Samples" ? <RunSamplesTab samples={bundle.samples} /> : null}
          {activeTab === "Workflow" ? <RunWorkflowTab progress={bundle.progress} rules={bundle.rules} /> : null}
          {activeTab === "QC" ? <RunQcTab qc={bundle.qc} /> : null}
          {activeTab === "Logs" ? <LogViewer stream={logStream} onStreamChange={setLogStream} log={log} error={logError} /> : null}
          {activeTab === "Files" ? <RunFilesTab artifacts={bundle.artifacts} /> : null}
          {activeTab === "Config" ? <RunConfigTab artifacts={bundle.artifacts} detail={detail} /> : null}
        </section>
      </> : null}
    </div>
  );
}
